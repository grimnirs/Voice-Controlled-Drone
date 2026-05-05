# ============================================================
# Logic Engine Container: Python + MAVSDK
# ============================================================
# This is where all team application code lives:
# - Voice command processing (NLP)
# - Safety layer (obstacle avoidance)
# - MAVLink command translation
# - Ground control dashboard
# ============================================================
FROM python:3.11-slim

# System dependencies (all in one layer)
RUN apt-get update && apt-get install -y \
    git build-essential cmake curl \
    libasound2 libasound2-dev \
    portaudio19-dev libportaudio2 libportaudiocpp0 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
RUN pip install --no-cache-dir \
    mavsdk \
    asyncio \
    pymavlink \
    sounddevice \
    pytest \
    pytest-asyncio \
    colorama

WORKDIR /app
COPY . .
RUN chmod +x start_logic.sh

RUN git clone https://github.com/ggerganov/whisper.cpp /opt/whisper.cpp && \
    cd /opt/whisper.cpp && \
    cmake -B build -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --config Release -j$(nproc)

RUN cd /opt/whisper.cpp && bash ./models/download-ggml-model.sh base.en

CMD ["./start_logic.sh"]