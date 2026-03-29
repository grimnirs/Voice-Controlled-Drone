# Conventions

## Python

- Python 3.11, async/await everywhere for drone interaction
- All MAVSDK calls are async — never use `time.sleep()`, use `await asyncio.sleep()`
- Type hints on function signatures
- Docstrings on public functions (Google style)
- No global state — pass drone system object explicitly
- f-strings for formatting

## Error Handling

- MAVSDK connections can drop — always handle `mavsdk.action.ActionError`
- Wrap telemetry streams in try/except for `_MultiThreadedRendezvous` errors
- Log errors, don't crash — the Logic Engine should be resilient

## Docker

- Never edit sim/Dockerfile steps 1-7 unless absolutely necessary (triggers full rebuild)
- Add new system packages to step 1 only
- Logic Engine Dockerfile changes are cheap — iterate freely
- Test with `docker compose up --build` after Dockerfile changes
- Use `docker compose up -d` for background, `docker compose logs -f` to watch

## Git

- Branch naming: `feature/thing`, `fix/thing`, `docs/thing`
- Never push directly to `main` — use pull requests
- One approval required per PR
- Commit messages: imperative mood, max 50 char first line
- Tag releases: `v0.1-baseline`, `v0.2-lidar`, etc.

## File Placement

| What you're adding | Where it goes | Rebuild? |
|---|---|---|
| Python application code | `logic-engine/` | Seconds |
| New Python dependency | `logic-engine/Dockerfile` | Seconds |
| Gazebo world file | `worlds/` | None |
| Drone/environment model | `models/` | None |
| ArduPilot config change | Via QGC parameters | None |
| New system-level tool in sim | `sim/Dockerfile` | 30+ min |
