# Voice-Controlled Drone 

GPS-denied drone simulation environment.

## QGroundControl setup
Use UDP to connect to the simulator:

- Q (top left) -> Application Settings -> Comm Links
- Add
- Type: `UDP`
- Listening Port: `14550`

Note: `TCP 5760` is internal between SITL and `mavlink-router` inside the container.

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

## Optical Flow Quick Test (QGroundControl)

`sim/entrypoint.sh` starts SITL with simulated optical flow + rangefinder:

- `SIM_FLOW_ENABLE=1`
- `FLOW_TYPE=10` (SITL optical flow)
- `RNGFND1_*` enabled
- `EK3_SRC1_VELXY=5` and `EK3_SRC1_POSXY=0` (optical-flow based XY estimate)
- `SR0_EXTRA1=10` (higher telemetry stream rate for easier inspection in QGC)

To verify in QGroundControl:

1. Start sim: `docker compose up --build`
2. Connect QGC to UDP `14550`
3. Open MAVLink Inspector
4. Confirm `OPTICAL_FLOW` is updating
5. Arm and move/tilt the drone in flight, then verify `OPTICAL_FLOW` values change over time

If `OPTICAL_FLOW` does not appear directly:

1. Open Analyze Tools -> MAVLink Inspector
2. Search for `OPTICAL_FLOW` and `OPTICAL_FLOW_RAD`
3. Let SITL run 10-20 seconds and check again

Important architecture note:

- `models/downward_camera/model.sdf` is currently a standalone Gazebo camera model.
- It is **not** attached to the `gazebo-iris` drone used by SITL in this setup.
- The optical flow you see in QGC right now comes from SITL's built-in optical flow simulation (this is a good first step and usually the easiest way to validate the pipeline).
- Next step (after this works): attach a real camera + optical-flow plugin directly in the drone model used by Gazebo/PX4 or switch to a full PX4 Gazebo model pipeline.
