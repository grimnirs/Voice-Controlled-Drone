# Voice-Controlled Drone — Simulation Baseline

GPS-denied drone simulation environment.
ArduPilot SITL + Gazebo Harmonic, orchestrated with Docker Compose.

## Quick Start

```bash
# Clone the repo
git clone <your-repo-url>
cd <repo-name>

# Build images (first time takes 20-40 min)
docker compose build

# Start simulation
docker compose up sim
```

## Test Logic Engine Connection

In a separate terminal (while sim is running):

```bash
docker compose run logic-engine
```

You should see telemetry streaming from SITL, confirming the
Logic Engine can communicate with the simulation over the Docker network.

**Note:** SITL's TCP port 5760 accepts one connection at a time.
Run QGC and the Logic Engine separately, not simultaneously.
To support simultaneous connections, add `mavlink-router` to the
sim container (documented as a future enhancement).

## Project Structure

```
├── docker-compose.yml      # Orchestrates all containers
├── sim/
│   ├── Dockerfile          # ArduPilot SITL + Gazebo Harmonic
│   └── entrypoint.sh       # Starts Gazebo then SITL
├── logic-engine/
│   ├── Dockerfile          # Python + MAVSDK
│   └── main.py             # Connection test stub
├── worlds/                 # Custom Gazebo world files (.sdf)
│   └── .gitkeep
├── models/                 # Custom drone/environment models
│   └── .gitkeep
└── README.md
```

## Custom Worlds & Models

Drop `.sdf` files into `worlds/` or `models/`. These directories
are mounted into the sim container automatically.


## Key Configuration Points

| What                  | Where / How                                        |
|-----------------------|----------------------------------------------------|
| GPS-denied mode       | Set EKF parameters (`EK3_SRC1_POSXY` etc.) via QGC |
| Add LiDAR             | Add sensor block to drone model SDF                |
| Change drone model    | Edit `-f` flag in `entrypoint.sh`                  |
| ArduPilot version     | Change `ARDUPILOT_TAG` build arg in `sim/Dockerfile` |
| Simultaneous clients  | Add `mavlink-router` to sim container              |
| Swarm (multi-drone)   | Add more SITL containers with unique `SYSID_THISMAV` |
## Useful Commands

```bash
# Rebuild after Dockerfile changes
docker compose build sim

# View sim logs
docker compose logs -f sim

# Shell into sim container
docker compose exec sim bash

# Stop everything
docker compose down

# Clean up all images (reclaim disk space)
docker system prune -a
```
