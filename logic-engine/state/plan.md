# State Machine Integration Plan

## Goal
Wire the `StateMachine` from [machine.py](machine.py) into the existing command pipeline in [command_handler.py](../command_handler.py) so that every command passes through a single gate before reaching MAVSDK. Add the one piece of real-time plumbing we can't avoid: an event-driven `LANDING → GROUNDED` transition.

Keep it minimal. Only build what's needed to make the current debug sequence work with state enforcement. Defer anything we don't have an actual symptom for.

## Scope
**In scope:**
- Single state-machine gate at the `txt_to_cmd` dispatcher
- Landing watcher so `LANDING → GROUNDED` actually happens
- Rename command keys in `ALLOWED_COMMANDS` to match real actions

**Deferred (not a symptom yet):**
- `asyncio.Lock` around `sm` — asyncio is single-threaded and the critical section has no `await`, so there's no race to protect against today
- Task cancellation for overlapping commands — current debug harness runs commands sequentially with `await`. Revisit when voice input introduces real concurrency
- Return-value refactor (`True`/`False` from every `cmd_*`) — treat "returned without exception" as success. If silent MAVSDK failures cause state drift, add it then
- Emergency stop state — will be needed, but no benefit to scaffolding it before we know how it gets triggered (voice keyword? hardware button? RC failsafe?)

**Out of scope but flagged — pre-existing bugs that will block end-to-end testing:**
- [command_handler.py:78](../command_handler.py#L78) — `cmd_land` has a `while True:` around `drone.action.land()` with no break. Will spam land calls forever and prevent the landing watcher from ever seeing a clean transition
- [command_handler.py:53-59](../command_handler.py#L53-L59) — `cmd_arm` infinite retry loop with no exit on repeated failure
- [command_handler.py:20-26](../command_handler.py#L20-L26) — `ACTIONS` dict is missing `rotate` and `stop`, so those commands get rejected as "unknown action" before reaching dispatch

---

## Decisions (from discussion)
1. **Scope:** commands only — `main.py`'s hardcoded sequence is a debug driver, no voice/text frontend yet
2. **Where `sm` lives:** `shared_variables.py` — already the cross-module state holder (`latest_odom`), avoids creating a new import target
3. **Rejection behavior:** print and return. Matches existing style in command_handler and is easy to read in logs
4. **Emergency stop:** deferred entirely until we know what triggers it

---

## Step 1 — Rename command keys in machine.py

**File:** [machine.py:17-22](machine.py#L17-L22)

`ALLOWED_COMMANDS` uses placeholder names from the original spec. Update to match the real actions in [command_handler.py:20-26](../command_handler.py#L20-L26):

```python
ALLOWED_COMMANDS = {
    DroneState.GROUNDED: ["arm"],
    DroneState.ARMED:    ["takeoff"],
    DroneState.AIRBORNE: ["land", "fly", "rotate", "stop"],
    DroneState.LANDING:  [],
}
```

Note: `start` is an alias for `arm` (see [command_handler.py:249](../command_handler.py#L249)). The gate handles that by normalizing `start → arm` before checking, so `ALLOWED_COMMANDS` only needs the canonical name.

---

## Step 2 — Add `sm` to shared_variables.py

**File:** [shared_variables.py](../shared_variables.py)

```python
from state.machine import StateMachine

latest_odom = None
sm = StateMachine()
```

That's it. No lock, no task tracking — just the singleton.

---

## Step 3 — Add the gate at `txt_to_cmd`

**File:** [command_handler.py:244-269](../command_handler.py#L244-L269)

Single gate at the dispatcher. The existing `elif` chain stays untouched — we just wrap it.

```python
import shared_variables
from state.machine import DroneState

COMMAND_TO_STATE = {
    "arm":     DroneState.ARMED,
    "takeoff": DroneState.AIRBORNE,
    "land":    DroneState.LANDING,
}

async def txt_to_cmd(drone, command: DroneCommand):
    action = command.get("action")
    if action == "start":
        action = "arm"

    if action is None or action not in ACTIONS:
        print(f"[CMD] Unknown action '{action}'")
        return

    sm = shared_variables.sm
    target = COMMAND_TO_STATE.get(action)

    # --- GATE ---
    if target is not None:
        if not sm.can_transition(target):
            print(f"[STATE] Rejected '{action}': drone is {sm.get_state().value}")
            return
    else:
        if not sm.can_execute(action):
            print(f"[STATE] Rejected '{action}': drone is {sm.get_state().value}")
            return

    # --- DISPATCH (existing if/elif chain) ---
    if action == "arm":
        await cmd_arm(drone, command)
    elif action == "takeoff":
        await cmd_takeoff(drone, command)
    elif action == "fly":
        await cmd_fly(drone, command)
    elif action == "land":
        await cmd_land(drone, command)
    elif action == "rotate":
        await cmd_rotate(drone, command)
    elif action == "stop":
        await cmd_stop(drone, command)

    # --- COMMIT TRANSITION ---
    if target is not None:
        sm.transition(target)
        print(f"[STATE] → {sm.get_state().value}")
```

**Trade-off we're accepting:** if a `cmd_*` fails silently (returns without exception but didn't actually do the thing), state will advance incorrectly. Recovery: the next command gets rejected by the gate and the user retries. Good enough for a debug harness. Upgrade to return-value checking only if we see this happen in practice.

---

## Step 4 — Landing watcher

**File:** [main.py](../main.py), add alongside `odometry_watcher` at [main.py:64-68](../main.py#L64-L68)

`LANDING → GROUNDED` is the one transition that *must* be event-driven — no command triggers it, the drone triggers it by actually touching down.

```python
from mavsdk.telemetry import LandedState
from state.machine import DroneState

async def landed_state_watcher(drone):
    async for landed in drone.telemetry.landed_state():
        if landed != LandedState.ON_GROUND:
            continue
        if shared_variables.sm.get_state() == DroneState.LANDING:
            shared_variables.sm.transition(DroneState.GROUNDED)
            print("[STATE] Landing complete → grounded")
```

Register it next to `odometry_watcher`:

```python
asyncio.create_task(odometry_watcher(drone))
asyncio.create_task(landed_state_watcher(drone))
```

Why gated on `== LANDING`: `landed_state()` also emits `ON_GROUND` before takeoff and between arm/disarm cycles. We only want the transition when we were *expecting* to land.

---

## Implementation order
1. Step 1 — rename `ALLOWED_COMMANDS` (trivial, unblocks the gate)
2. Step 2 — add `sm` to `shared_variables` (plumbing, no behavior change)
3. Step 3 — gate + commit in `txt_to_cmd` (main integration, testable immediately)
4. Step 4 — landing watcher (needed for end-to-end, but `cmd_land` bug will block full test)

## Test plan
The existing debug sequence in [main.py:85-108](../main.py#L85-L108) (`arm → takeoff → fly`) is already a good smoke test. After Step 3, logs should show:
```
[STATE] → armed
[STATE] → airborne
```

**Manual rejection test:** send `fly` while GROUNDED. Expect `[STATE] Rejected 'fly': drone is grounded` with no MAVSDK call.

**Landing test (after cmd_land bug is fixed):** append a `land` command after the fly. Expect `[STATE] → landing` from the command path, then `[STATE] Landing complete → grounded` from the watcher a few seconds later.

## What this plan deliberately does not solve
- **Concurrent commands stepping on each other** — ArduPilot handles last-command-wins on the wire; our Python side only has a problem if two `cmd_*` coroutines run simultaneously, which the current harness never does. Add cancellation when the symptom appears.
- **State drift from silent failures** — hasn't been observed. Add return-value checking when it is.
- **Thread-safe transitions** — single asyncio loop, no preemption inside the non-awaiting critical sections. Not an issue today.
- **Emergency stop** — reserved for later; the trigger mechanism shapes the implementation and we don't have one yet.

Every deferred item has a clear "add when X happens" trigger, so this plan isn't leaving problems hidden — it's leaving them sized to the smallest solution that will actually match the eventual symptom.
