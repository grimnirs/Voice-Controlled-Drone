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

<<<<<<< HEAD
# ── Start ArduPilot SITL FIRST ──────────────────────────────
# Starting SITL before Gazebo avoids a race where Gazebo's
# ArduPilotPlugin opens UDP 9002/9003 and immediately times out
# because SITL isn't yet running, producing endless
# "Broken ArduPilot connection, resetting motor control" warnings.
=======
# solves plug-in problems:
export GZ_SIM_SYSTEM_PLUGIN_PATH=/home/ardupilot/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH}
export GZ_SIM_RESOURCE_PATH=/home/ardupilot/ardupilot_gazebo/models:/home/ardupilot/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH}

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
>>>>>>> origin/erika_testing
echo "============================================"
echo "  Starting ArduPilot SITL"
echo "============================================"
cd "${ARDUPILOT_HOME}"

# SITL runs with --no-mavproxy, exposing TCP 5760 internally.
# mavlink-router will connect to this and fan out to QGC + Logic Engine.
<<<<<<< HEAD
# NOTE: do not put inline `#` comments after a trailing `\` — bash treats
# the comment as a separate command and silently drops the rest of the args.
python3 Tools/autotest/sim_vehicle.py \
    -v ArduCopter \
    -f gazebo-iris \
    --model JSON \
    -N \
    --no-mavproxy \
    -I0 \
    --param EK3_SRC1_POSXY=6 \
    --param EK3_SRC1_VELXY=6 \
    --param EK3_SRC1_POSZ=1 \
    --param VISO_TYPE=1 \
    --param RNGFND1_TYPE=10 \
    --param RNGFND1_MIN_CM=10 \
    --param RNGFND1_MAX_CM=3000 \
    --param PRX1_TYPE=4 \
    --param PRX1_MAX=20 &
=======
./build/sitl/bin/arducopter \
    --model JSON \
    --home 59.840406,17.64578,20,0 \
    --speedup 1 \
    --instance 0 \
    --sim-address=127.0.0.1 \
    --defaults Tools/autotest/default_params/copter.parm,Tools/autotest/default_params/gazebo-iris.parm &

>>>>>>> origin/erika_testing
SITL_PID=$!

echo "SITL starting (PID: ${SITL_PID})"

# Wait for SITL's MAVLink TCP port (5760) to be ready before Gazebo.
# Retry loop avoids racing Gazebo against a half-booted SITL.
echo "Waiting for SITL TCP port 5760..."
for i in $(seq 1 60); do
    if bash -c '</dev/tcp/127.0.0.1/5760' 2>/dev/null; then
        echo "SITL TCP 5760 is up (after ${i}s)."
        break
    fi
    if ! kill -0 $SITL_PID 2>/dev/null; then
        echo "ERROR: SITL exited before binding TCP 5760."
        exit 1
    fi
    sleep 1
done

# ── Start Gazebo server (headless) ───────────────────────────
echo "============================================"
echo "  Starting Gazebo server (headless)"
echo "  World: ${WORLD_PATH}"
echo "============================================"
gz sim -s -r "${WORLD_PATH}" -v 2 &
GZ_PID=$!

echo "Waiting for Gazebo to initialize..."
sleep 10

if ! kill -0 $GZ_PID 2>/dev/null; then
    echo "ERROR: Gazebo failed to start."
    exit 1
fi
echo "Gazebo server running (PID: ${GZ_PID})"

# ── Start MAVLink Router ────────────────────────────────────
# mavlink-router only accepts raw IPs, so resolve hostnames first

# Resolve host.docker.internal for QGC
HOST_IP=$(getent hosts host.docker.internal | awk '{print $1}' || echo "")
if [ -z "${HOST_IP}" ]; then
    # Fallback: get the default gateway IP (Docker host)
    HOST_IP=$(ip route | grep default | awk '{print $3}' || echo "")
fi
if [ -n "${HOST_IP}" ]; then
    sed -i "s/host.docker.internal/${HOST_IP}/" /home/ardupilot/mavlink-router.conf
    echo "Host (QGC) resolved to: ${HOST_IP}"
else
    echo "WARNING: Could not resolve host IP for QGC."
    sed -i '/\[UdpEndpoint qgc\]/,/^$/d' /home/ardupilot/mavlink-router.conf
fi


echo "============================================"
echo "  Starting MAVLink Router"
echo "  SITL (TCP:5760) → QGC (UDP:14550)"
echo "                   → Logic Engine (TCP:5790)"
echo "============================================"
mavlink-routerd -c /home/ardupilot/mavlink-router.conf &
ROUTER_PID=$!

echo ""
echo "============================================"
echo "  READY — All services running"
echo "  QGC:          UDP 14550 (auto-connect)"
echo "  Logic Engine: TCP 5790 (Docker network)"
echo "============================================"

mkdir -p /shared && chmod 777 /shared
echo "Starting sensor bridge..."
python3 /home/ardupilot/sensor_bridge.py &
SENSOR_PID=$!

# Wait for any process to exit
wait -n $GZ_PID $SITL_PID $ROUTER_PID $SENSOR_PID
echo "A process exited. Shutting down..."
kill $GZ_PID $SITL_PID $ROUTER_PID $SENSOR_PID 2>/dev/null
wait