from enum import Enum, auto
import asyncio


class State(Enum):
    DISARMED = auto()
    ARMED = auto()
    TAKEOFF = auto()
    HOVERING = auto()
    FLYING = auto()
    EMERGENCY = auto()
    LANDING = auto()
    KILL = auto()


# Normal flow. KILL transitions are NOT here — they go through force_kill().
ALLOWED_TRANSITIONS: dict[State, set[State]] = {
    State.DISARMED:  {State.ARMED},
    State.ARMED:     {State.DISARMED, State.TAKEOFF},
    State.TAKEOFF:   {State.HOVERING},
    State.HOVERING:  {State.FLYING, State.LANDING},
    State.FLYING:    {State.HOVERING, State.EMERGENCY},
    State.EMERGENCY: {State.HOVERING},
    State.LANDING:   {State.DISARMED},
    State.KILL:      {State.DISARMED},
}

# States from which a kill makes sense (motors are spinning).
# Calling force_kill() from any other state is a no-op.
KILL_REACHABLE_FROM: set[State] = {
    State.TAKEOFF,
    State.HOVERING,
    State.FLYING,
    State.LANDING,
    State.EMERGENCY,
}


class IllegalTransition(Exception):
    pass


_current_state: State = State.DISARMED
_lock = asyncio.Lock()


def current() -> State:
    return _current_state


def can_transition_to(new_state: State) -> bool:
    return new_state in ALLOWED_TRANSITIONS.get(_current_state, set())


async def transition_to(new_state: State) -> None:
    global _current_state
    async with _lock:
        allowed = ALLOWED_TRANSITIONS.get(_current_state, set())
        if new_state not in allowed:
            raise IllegalTransition(
                f"Cannot transition from {_current_state.name} to {new_state.name}. "
                f"Allowed: {sorted(s.name for s in allowed)}"
            )
        print(f"[STATE] {_current_state.name} -> {new_state.name}")
        _current_state = new_state


async def force_kill() -> None:
    global _current_state
    async with _lock:
        if _current_state not in KILL_REACHABLE_FROM:
            print(f"[STATE] kill ignored: {_current_state.name} (motors not running)")
            return
        print(f"[STATE] FORCE KILL from {_current_state.name}")
        _current_state = State.KILL
