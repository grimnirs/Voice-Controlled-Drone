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

WORKDIR /app
COPY . .

CMD ["python3", "main.py"]
