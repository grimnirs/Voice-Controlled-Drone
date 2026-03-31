# Voice-Controlled Drone 

GPS-denied drone simulation environment.

## QGroundControl setup
> Press the Q in the upper left corner
> Application settings
> Comm links
> Press 'add' under Links
> Type:TCP   Server Address:127.0.0.1  Port:5760

## Quick Start

```bash
cd <Voice-Controlled-Drone>
docker compose build 
```

**ELLER**
Detta kommer ta kanske 10min och ca 8-10gb minne
```bash
git clone https://github.com/grimnirs/Voice-Controlled-Drone.git
cd <repo>
docker compose pull
docker compose up
```

## Project Structure-ish

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
