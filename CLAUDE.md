# CLAUDE.md

## Project
Voice-controlled drone middleware for GPS-denied environments (mining, search & rescue).
University project (Uppsala, 1DT350). Client: Amkvo AB. 6-person team.

## Stack
- **Sim container**: ArduPilot SITL + Gazebo Harmonic + mavlink-router (Ubuntu 22.04)
- **Logic Engine container**: Python 3.11 + MAVSDK (slim image)
- **Protocol**: MAVLink over UDP (routed by mavlink-router)
- **Orchestration**: Docker Compose
- **GCS**: QGroundControl (installed natively on host, not in Docker)

## Architecture
```
Gazebo (physics/sensors) ←JSON/UDP→ ArduPilot SITL ←TCP:5760→ mavlink-router
                                                        ├─UDP:14550→ QGC (host)
                                                        └─UDP:14540→ Logic Engine
```

## Key Paths
```
docker-compose.yml          # Container orchestration
sim/Dockerfile              # SITL + Gazebo + mavlink-router build
sim/entrypoint.sh           # Starts Gazebo → SITL → mavlink-router
sim/mavlink-router.conf     # Routes MAVLink to QGC + Logic Engine
logic-engine/Dockerfile     # Python + MAVSDK
logic-engine/main.py        # Entry point for all application code
worlds/                     # Custom Gazebo .sdf world files (mounted volume)
models/                     # Custom drone/environment models (mounted volume)
```

## Commands
```bash
docker compose up              # Start everything
docker compose up sim          # Start sim only
docker compose build sim       # Rebuild sim (only needed if Dockerfile changes)
docker compose logs -f sim     # View sim logs
docker compose exec sim bash   # Shell into sim container
docker compose down            # Stop everything
```

## Rules
- Never modify lines 1-68 of `sim/Dockerfile` without good reason — those are cached heavy compile steps (ArduPilot + Gazebo + plugin). Changes there trigger 30+ min rebuilds.
- All Logic Engine code goes in `logic-engine/`. This container rebuilds in seconds.
- World/model files go in `worlds/` and `models/` — these are mounted volumes, no rebuild needed.
- MAVSDK is async (`asyncio`). All drone interaction code must be async.
- Use `udpin://0.0.0.0:14540` to connect MAVSDK in the Logic Engine (incoming UDP, not deprecated `udp://`).
- ArduPilot parameters are set via QGC or MAVLink, not in code.
- The sim container runs headless (no GUI). Gazebo GUI requires X11 forwarding.

## MAVSDK Patterns
```python
from mavsdk import System
drone = System()
await drone.connect(system_address="udp://0.0.0.0:14540")

# Telemetry (async generators)
async for position in drone.telemetry.position():
    ...

# Actions
await drone.action.arm()
await drone.action.takeoff()
await drone.action.land()

# Offboard velocity control
from mavsdk.offboard import VelocityBodyYawspeed
await drone.offboard.set_velocity_body(VelocityBodyYawspeed(forward, right, down, yaw))
await drone.offboard.start()
```

## GPS-Denied Config (not yet enabled)
Set via ArduPilot params: `EK3_SRC1_POSXY`, `EK3_SRC1_VELXY`, `EK3_SRC1_POSZ`.
Disable GPS requirement, use optical flow or visual odometry instead.

## LiDAR (not yet added)
Add sensor block to drone model SDF in `models/`. ArduPilot receives data as `OBSTACLE_DISTANCE` MAVLink messages. Safety layer in Logic Engine subscribes to these.

## Future: Swarm
Add more SITL instances with unique `SYSID_THISMAV` values. Each gets its own mavlink-router endpoint.

## Style
- Python: async/await, type hints, docstrings on public functions
- Commits: imperative mood, short first line ("Add LiDAR sensor to Iris model")
- Branches: `feature/`, `fix/`, `docs/` prefixes
