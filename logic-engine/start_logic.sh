#!/bin/bash

echo "Starting Voice-to-Text Listener (Whisper.cpp)..."

# VTT.py manages whisper-stream internally via subprocess — just run it
python3 VTT.py &

sleep 2
#RUN chmod +x ./start_logic.sh
echo "Starting Main Drone Controller (MAVSDK)..."
python3 main.py