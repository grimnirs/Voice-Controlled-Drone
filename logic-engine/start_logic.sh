# #!/bin/bash
# # start_logic.sh

# # Start the VTT listener in the background or as a pipe
# echo "Starting Voice-to-Text Listener..."

# # This command runs the whisper stream and pipes the output into your VTT.py script
# ./bin/whisper-stream -m ../models/ggml-base.en.bin --step 500 --length 5000 | python3 VTT.py &

# # Now start the main drone control script
# echo "Starting Main Drone Controller..."
# python3 main.py

#!/bin/bash

echo "Starting Voice-to-Text Listener (Whisper.cpp)..."

# Step out of logic-engine to the root, then into whisper.cpp
# We pipe the output directly into VTT.py
../whisper.cpp/bin/whisper-stream -m ../whisper.cpp/models/ggml-base.en.bin --step 500 --length 5000 | python3 VTT.py &

# Give Whisper a moment to initialize the hardware
sleep 2

echo "Starting Main Drone Controller (MAVSDK)..."
python3 main.py