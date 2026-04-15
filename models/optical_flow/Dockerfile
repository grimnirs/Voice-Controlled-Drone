FROM python:3.11-slim

RUN pip install pymavlink

WORKDIR /app/models/optical_flow/

COPY camera_sensor.py .


CMD ["python", "camera_sensor.py"]
