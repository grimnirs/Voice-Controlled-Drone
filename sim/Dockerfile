# ============================================================
# Simulation Container: ArduPilot SITL + Gazebo Harmonic
# ============================================================
# Builds ArduPilot from source, installs Gazebo Harmonic,
# and compiles the ardupilot_gazebo bridge plugin.
#
# First build takes ~20-40 min. Subsequent builds are cached.
# ============================================================
FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ── 1. System packages ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget gnupg lsb-release software-properties-common \
    git sudo tzdata \
    build-essential cmake pkg-config g++ \
    libopencv-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
    python3 python3-pip python3-dev python3-venv python3-setuptools \
    && rm -rf /var/lib/apt/lists/*

# ── 2. Gazebo Harmonic from OSRF repository ─────────────────
RUN wget https://packages.osrfoundation.org/gazebo.gpg \
        -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
    http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/gazebo-stable.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    gz-harmonic \
    libgz-sim8-dev \
    rapidjson-dev \
    && rm -rf /var/lib/apt/lists/*

# ── 3. Create non-root user (ArduPilot build scripts need sudo) ──
RUN useradd -m -s /bin/bash ardupilot && \
    echo "ardupilot ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER ardupilot
WORKDIR /home/ardupilot

# ── 4. Clone ArduPilot ──────────────────────────────────────
# Pin to a stable release tag for reproducibility.
# Change the tag to upgrade ArduPilot version.
ARG ARDUPILOT_TAG=master
RUN git clone --recurse-submodules --depth 1 --branch ${ARDUPILOT_TAG} \
    https://github.com/ArduPilot/ardupilot.git /home/ardupilot/ardupilot

# ── 5. Install ArduPilot prerequisites ──────────────────────
WORKDIR /home/ardupilot/ardupilot
RUN USER=root Tools/environment_install/install-prereqs-ubuntu.sh -y

# Make sure pip-installed tools are on PATH
ENV PATH="/home/ardupilot/.local/bin:${PATH}"

# ── 6. Build ArduCopter for SITL ────────────────────────────
RUN modules/waf/waf-light configure --board sitl && \
    modules/waf/waf-light build --target bin/arducopter

# ── 7. Clone and build ardupilot_gazebo plugin ──────────────
RUN git clone --depth 1 \
    https://github.com/ArduPilot/ardupilot_gazebo.git \
    /home/ardupilot/ardupilot_gazebo

WORKDIR /home/ardupilot/ardupilot_gazebo
ENV GZ_VERSION=harmonic
RUN mkdir build && cd build && cmake .. && make -j$(nproc)

# ── 8. Environment variables for Gazebo ─────────────────────
ENV GZ_SIM_SYSTEM_PLUGIN_PATH=/home/ardupilot/ardupilot_gazebo/build
ENV GZ_SIM_RESOURCE_PATH=/home/ardupilot/ardupilot_gazebo/models:/home/ardupilot/ardupilot_gazebo/worlds

# ── 9. Entrypoint ───────────────────────────────────────────
COPY --chown=ardupilot:ardupilot entrypoint.sh /home/ardupilot/entrypoint.sh
RUN chmod +x /home/ardupilot/entrypoint.sh

EXPOSE 5760

ENTRYPOINT ["/home/ardupilot/entrypoint.sh"]
