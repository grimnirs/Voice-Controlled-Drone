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
echo "============================================"
cd "${ARDUPILOT_HOME}"

# SITL runs with --no-mavproxy, exposing TCP 5760 internally.
# mavlink-router will connect to this and fan out to QGC + Logic Engine.
python3 Tools/autotest/sim_vehicle.py \
    -v ArduCopter \
    -f gazebo-iris \
    --model JSON \
    -N \
    --no-mavproxy \
    -I0 \
    --param SIM_FLOW_ENABLE=1 \
    --param FLOW_ENABLE = 1 \
    --param FLOW_TYPE=10 \
    --param RNGFND1_TYPE=1 \
    --param RNGFND1_PIN=0 \
    --param RNGFND1_MIN_CM=20 \
    --param RNGFND1_MAX_CM=700 \
    --param EK3_SRC1_POSXY=0 \
    --param EK3_SRC1_VELXY=5 \
    --param EK3_SRC1_POSZ=1 \
    --param EK3_SRC1_VELZ=0 \
    --param EK3_SRC1_YAW=1 \
    --param EK3_SRC_OPTIONS=0 \
    --param SR0_EXTRA1=10 &
SITL_PID=$!

echo "SITL starting (PID: ${SITL_PID})"

# Wait for SITL to open its TCP port
echo "Waiting for SITL TCP port..."
sleep 5

# ── Start MAVLink Router ────────────────────────────────────
# mavlink-router only accepts raw IPs, so resolve hostnames first

# Resolve host.docker.internal for QGC
# HOST_IP=$(getent hosts host.docker.internal | awk '{print $1}' || echo "")
#tries to find the IP add of host.docker.internal (the host machine inside docker)
#used so a container can talk back to a service running on the host, 
#like forwarding traffic to a ROS master, a display server, or a Gazebo instance running outside the container.
HOST_IP=$(getent ahostsv4 host.docker.internal 2>/dev/null | awk 'NR==1 {print $1}' || echo "")
if [ -z "${HOST_IP}" ]; then
    # Fallback: get the default gateway IP (Docker host)
    # HOST_IP=$(ip route | grep default | awk '{print $3}' || echo "")
    HOST_IP=$(ip -4 route show default 2>/dev/null | awk 'NR==1 {print $3}' || echo "")
fi
if [ -n "${HOST_IP}" ]; then
    sed -i "s/host.docker.internal/${HOST_IP}/" /home/ardupilot/mavlink-router.conf
    # echo "Host (QGC) resolved to: ${HOST_IP}"
    echo "Host (QGC) resolved to IPv4: ${HOST_IP}"
else
    # echo "WARNING: Could not resolve host IP for QGC."
    echo "WARNING: Could not resolve host IPv4 for QGC."
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

# Wait for any process to exit
wait -n $GZ_PID $SITL_PID $ROUTER_PID
echo "A process exited. Shutting down..."
kill $GZ_PID $SITL_PID $ROUTER_PID 2>/dev/null
wait