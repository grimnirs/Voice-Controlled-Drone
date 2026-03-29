# Voice-Controlled Drone — Simulation Baseline

GPS-denied drone simulation environment.
ArduPilot SITL + Gazebo Harmonic, orchestrated with Docker Compose.

## Prerequisites

- **Docker Desktop** — [download](https://www.docker.com/products/docker-desktop/)
- **QGroundControl** — [download](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html) (install natively on host)
- **~10 GB free disk space** (for Docker images)

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

Wait for the `READY` message, then connect QGroundControl:
1. Open QGC → **Q icon** → **Application Settings** → **Comm Links**
2. **Add** → Type: **TCP**, Host: `127.0.0.1`, Port: `5760`
3. Click **Connect**

You should see a drone at Ballarat, Australia with live telemetry.

## Test Logic Engine Connection

In a separate terminal (while sim is running):

```bash
docker compose run logic-engine
```

You should see telemetry streaming from SITL, confirming the
Logic Engine can communicate with the simulation over the Docker network.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  sim container                                  │
│                                                 │
│  ┌──────────────┐    JSON/UDP    ┌───────────┐  │
│  │ ArduPilot    │◄──────────────►│  Gazebo   │  │
│  │ SITL         │  (localhost)   │  Harmonic  │  │
│  │ (ArduCopter) │               │  (headless)│  │
│  └──────┬───────┘               └───────────┘  │
│         │ MAVLink TCP :5760                     │
├─────────┼───────────────────────────────────────┤
│         │                                       │
│         ├──────────► QGC (on host)              │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐                               │
│  │ Logic Engine │  (Docker network)             │
│  │ Python/MAVSDK│                               │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

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

To load a custom world:
```bash
GZ_WORLD=my_mine.sdf docker compose up sim
```

Or change the default in `docker-compose.yml`:
```yaml
environment:
  - GZ_WORLD=my_mine.sdf
```

## Key Configuration Points

| What                  | Where / How                                        |
|-----------------------|----------------------------------------------------|
| GPS-denied mode       | Set EKF parameters (`EK3_SRC1_POSXY` etc.) via QGC |
| Add LiDAR             | Add sensor block to drone model SDF                |
| Change drone model    | Edit `-f` flag in `entrypoint.sh`                  |
| ArduPilot version     | Change `ARDUPILOT_TAG` build arg in `sim/Dockerfile` |
| Simultaneous clients  | Add `mavlink-router` to sim container              |
| Swarm (multi-drone)   | Add more SITL containers with unique `SYSID_THISMAV` |

## Build Notes — Issues Resolved During Initial Setup

These issues were encountered and fixed during the first successful build.
They are already resolved in the current Dockerfiles, but documented here
so the team understands why certain lines exist.

### 1. The "Invisible User" Crash (sim/Dockerfile, Step 8)

ArduPilot's `install-prereqs-ubuntu.sh` script assumes it's being run by
a human. It tries to add `$USER` to the `dialout` permissions group for
USB flight controllers. Inside a Docker build, `$USER` is blank, causing
the command to fail with `Usage: usermod [options] LOGIN`.

**Fix:** We explicitly set a temporary user for that step:
```dockerfile
# Before (crashes):
RUN Tools/environment_install/install-prereqs-ubuntu.sh -y
# After (works):
RUN USER=root Tools/environment_install/install-prereqs-ubuntu.sh -y
```

### 2. Missing OpenCV Libraries (sim/Dockerfile, Step 1)

The `ardupilot_gazebo` plugin requires OpenCV development headers to
compile its camera simulation features. The base Ubuntu image doesn't
include them, causing: `CMake Error: Could not find a package
configuration file provided by "OpenCV"`.

**Fix:** Added `libopencv-dev` to the `apt-get install` command in Step 1.

### 3. Missing GStreamer Libraries (sim/Dockerfile, Step 1)

Alongside OpenCV, the plugin requires GStreamer for video streaming.
Without the headers, CMake fails with `No package 'gstreamer-1.0' found`.
Without the runtime plugins, Gazebo would crash when rendering cameras.

**Fix:** Added to Step 1:
- Headers: `libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev`
- Runtime: `gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl`

### 4. The "Connection Refused" Race Condition (logic-engine/main.py)

The Logic Engine container boots in under a second, while the sim container
takes 15+ seconds to initialize Gazebo and ArduPilot. The Python script
tried to connect immediately, hit a closed port, and MAVSDK's internal
engine crashed fatally instead of retrying. Additionally, the MAVSDK
address scheme needed `tcpout://` rather than the deprecated `tcp://`.

**Fix:** Rewrote `main.py` with:
- A 15-second startup delay before attempting any connection
- A retry loop with `try/except` that waits 3 seconds between attempts
- Corrected address scheme (`tcpout://sim:5760`)

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