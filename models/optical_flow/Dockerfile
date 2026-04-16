FROM python:3.11-slim

RUN pip install pymavlink

WORKDIR /app/models/optical_flow/

COPY camera_sensor.py .

EXPOSE 14551

CMD ["python", "camera_sensor.py"]
