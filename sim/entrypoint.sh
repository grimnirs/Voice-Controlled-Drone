#!/bin/bash
set -e

# ── Configuration ────────────────────────────────────────────
WORLD=${GZ_WORLD:-iris_runway.sdf}
ARDUPILOT_HOME=/home/ardupilot/ardupilot
GAZEBO_WORLDS=/home/ardupilot/ardupilot_gazebo/worlds
CUSTOM_WORLDS=/home/ardupilot/custom_worlds

# Resolve world file path: check custom worlds first, then built-in
if [ -f "${CUSTOM_WORLDS}/${WORLD}" ]; then
    WORLD_PATH="${CUSTOM_WORLDS}/${WORLD}"
    echo "Using custom world: ${WORLD}"
elif [ -f "${GAZEBO_WORLDS}/${WORLD}" ]; then
    WORLD_PATH="${GAZEBO_WORLDS}/${WORLD}"
    echo "Using built-in world: ${WORLD}"
else
    echo "ERROR: World file '${WORLD}' not found."
    echo "Available built-in worlds:"
    ls "${GAZEBO_WORLDS}"/*.sdf 2>/dev/null || echo "  (none)"
    echo "Custom worlds directory:"
    ls "${CUSTOM_WORLDS}"/*.sdf 2>/dev/null || echo "  (none)"
    exit 1
fi

# Extend resource path with custom models
if [ -d "${CUSTOM_WORLDS}" ]; then
    export GZ_SIM_RESOURCE_PATH="${CUSTOM_WORLDS}:${GZ_SIM_RESOURCE_PATH}"
fi
if [ -d "/home/ardupilot/custom_models" ]; then
    export GZ_SIM_RESOURCE_PATH="/home/ardupilot/custom_models:${GZ_SIM_RESOURCE_PATH}"
fi

# ── Start Gazebo server (headless) ───────────────────────────
echo "============================================"
echo "  Starting Gazebo server (headless)"
echo "  World: ${WORLD_PATH}"
echo "============================================"
gz sim -s -r "${WORLD_PATH}" -v 2 &
GZ_PID=$!

# Wait for Gazebo to initialize
echo "Waiting for Gazebo to initialize..."
sleep 10

# Verify Gazebo is running
if ! kill -0 $GZ_PID 2>/dev/null; then
    echo "ERROR: Gazebo failed to start."
    exit 1
fi
echo "Gazebo server running (PID: ${GZ_PID})"

# ── Start ArduPilot SITL ────────────────────────────────────
echo "============================================"
echo "  Starting ArduPilot SITL"
echo "  MAVLink on TCP port 5760"
echo "============================================"
cd "${ARDUPILOT_HOME}"

# -v ArduCopter      : Vehicle type
# -f gazebo-iris     : Frame (Iris quad for Gazebo)
# --model JSON       : Use JSON protocol to connect to Gazebo
# -N                 : Skip rebuild (already compiled)
# --no-mavproxy      : Run SITL binary directly (TCP 5760)
# -I0                : Instance 0
python3 Tools/autotest/sim_vehicle.py \
    -v ArduCopter \
    -f gazebo-iris \
    --model JSON \
    -N \
    --no-mavproxy \
    -I0 &
SITL_PID=$!

echo "SITL starting (PID: ${SITL_PID})"
echo ""
echo "============================================"
echo "  READY"
echo "  Connect QGC → TCP 127.0.0.1:5760"
echo "============================================"

# Wait for either process to exit
wait -n $GZ_PID $SITL_PID
echo "A process exited. Shutting down..."
kill $GZ_PID $SITL_PID 2>/dev/null
wait
