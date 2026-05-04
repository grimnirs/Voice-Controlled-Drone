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

RUN pip install --no-cache-dir \
    mavsdk \
    asyncio \
    pymavlink

# RUN apt-get update && apt-get install -y \
#     cmake \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install pytest pytest-asyncio
COPY . .
# RUN cmake -B /app/whisper.cpp/build /app/whisper.cpp && \
#     cmake --build /app/whisper.cpp/build --config Release
# RUN chmod +x /app/start_logic.sh

#CMD ["python3", "start_logic.sh"]
# CMD ["./start_logic.sh"]
# Inside your Dockerfile
# This takes the file from your Mac and puts it in the container's system path

CMD ["sh", "./start_logic.sh"]
