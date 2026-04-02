# Architecture

## Container Communication

```
┌─────────────────────────────────────────────────────────────┐
│  sim container (Ubuntu 22.04)                               │
│                                                             │
│  Gazebo Harmonic ──JSON/UDP──► ArduPilot SITL (ArduCopter) │
│  (gzserver)                    │                            │
│  Port: internal only           TCP:5760 (internal only)     │
│                                │                            │
│                          mavlink-router                     │
│                           ├─ UDP:14550 → host (QGC)        │
│                           └─ UDP:14540 → logic-engine      │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. Gazebo runs physics simulation, generates sensor data (IMU, GPS, LiDAR)
2. Gazebo sends sensor state to ArduPilot via JSON-over-UDP (localhost)
3. ArduPilot runs flight controller firmware, outputs motor commands back to Gazebo
4. ArduPilot exposes MAVLink on TCP:5760
5. mavlink-router connects to TCP:5760, fans out to UDP:14550 (QGC) and UDP:14540 (Logic Engine)
6. Logic Engine sends commands via MAVSDK → mavlink-router → ArduPilot

## MAVLink Message Types We Care About

| Message | Direction | Purpose |
|---|---|---|
| HEARTBEAT | SITL → out | Connection keepalive |
| GLOBAL_POSITION_INT | SITL → out | Drone position |
| ATTITUDE | SITL → out | Roll/pitch/yaw |
| OBSTACLE_DISTANCE | SITL → out | LiDAR data (when added) |
| COMMAND_LONG | in → SITL | Arm, takeoff, mode change |
| SET_POSITION_TARGET_LOCAL_NED | in → SITL | Position/velocity commands |

## ArduPilot Flight Modes (relevant subset)

| Mode | Use |
|---|---|
| STABILIZE | Manual control, default on boot |
| GUIDED | Accepts programmatic position/velocity commands |
| LOITER | Hold position (GPS required) |
| LAND | Automated landing |
| RTL | Return to launch |

Logic Engine should use GUIDED mode for all autonomous navigation.

## Port Map

| Port | Protocol | From | To | Purpose |
|---|---|---|---|---|
| 5760 | TCP | mavlink-router | SITL | MAVLink upstream (internal) |
| 14550 | UDP | sim container | host | QGC telemetry + commands |
| 14540 | UDP | sim container | logic-engine | Logic Engine telemetry + commands |

## Docker Volume Mounts

| Host Path | Container Path | Purpose |
|---|---|---|
| `./worlds/` | `/home/ardupilot/custom_worlds` | Custom Gazebo world SDF files |
| `./models/` | `/home/ardupilot/custom_models` | Custom drone/environment models |

## Module Boundaries (planned)

```
logic-engine/
├── main.py              # Entry point, asyncio event loop
├── voice/               # STT + NLP intent parsing
├── safety/              # LiDAR obstacle avoidance layer
├── navigation/          # MAVSDK command translation
└── dashboard/           # Ground control UI
```

Each module runs as an asyncio task in a single event loop.
Safety layer has veto authority over navigation commands.
