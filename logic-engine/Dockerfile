# ============================================================
# Logic Engine Container: Python + MAVSDK
# ============================================================
# This is where all team application code lives:
# - Voice command processing (NLP)
# - Safety layer (obstacle avoidance)
# - MAVLink command translation
# - Ground control dashboard
# ============================================================
# FROM python:3.11-slim

# RUN pip install --no-cache-dir \
#     mavsdk \
#     asyncio \
#     pymavlink

# WORKDIR /app
# COPY . .

# CMD ["python3", "main.py"]

# ============================================================
# Logic Engine Container: Python + MAVSDK + Whisper Audio
# ============================================================
FROM python:3.11-slim

# Install system dependencies for audio and microphone access
RUN apt-get update && apt-get install -y \
    libasound2 \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    mavsdk \
    asyncio \
    pymavlink

WORKDIR /app
COPY . .

# Ensure the startup script is executable
RUN chmod +x start_logic.sh

# Change the command to run the shell script instead of just main.py
CMD ["./start_logic.sh"]