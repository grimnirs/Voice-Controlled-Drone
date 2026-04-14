FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install mavsdk

CMD ["python", "vision_injector.py"]