import sys
import json
import asyncio
import os
import string
import re
import subprocess


#tanken är att vi ska importa 
#OBS MAN MÅSTE VA INNE I BUILD 
#./bin/whisper-stream -m ../models/ggml-base.en.bin --step 500 --length 5000 | python3 ../../logic-engine/VTT.py
#så att den körs när man kör main, så börjar den lyssna direkt
#man kan inte säga move to the left, edgecase

#Nästa steg: "move to the left 10 meters and then move to the left 5 meters and then move up 3 meters..."
#Förbättra hanteringen av kommandon, just nu krävs en del timeing med samplingen
###### FIXA NLP
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# WHISPER_BIN = os.path.join(BASE_DIR, "../whisper.cpp/build/bin/whisper-cli")
WHISPER_MODEL = os.path.join(BASE_DIR, "../whisper.cpp/models/ggml-base.en.bin")
WHISPER_BIN = os.path.join(BASE_DIR, "whisper.cpp/build/bin/whisper-cli")

WHISPER_MODEL = os.path.join(BASE_DIR, "whisper.cpp/models/ggml-base.en.bin")
COMMANDS_FILE = os.path.join(BASE_DIR, 'commands.json')

RE_OVER = re.compile(r'\bover\b', re.IGNORECASE)
RE_TRIGGERS = re.compile(r'\b(drone|over)\b', re.IGNORECASE)

# A dictionary of valid Action -> Direction pairs
VALID_FLIGHT_COMMANDS = {
    "move": ["forward", "backward", "left", "right", "up", "down"],
    "rotate": ["clockwise", "counter-clockwise"],
    "land": [None],      # Land doesn't need a direction
    "takeoff": [None],   # Takeoff doesn't need a direction
    "stop": [None]
}

# A dictionary for word to integer transcribing, since whisper.cpp sometimes writes
# 2 as "two"
WORD_TO_DIGIT = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10
}

# A list of valid units to use in commands
VALID_UNITS = ["millimeters", "centimeters", "meters", "meter"]

_command_log = []

# This function checks for valid action and directions with regard to the
def parse_and_validate(text):
    text = text.lower()
    
    # Identify the action
    action = None
    if "move" in text or "fly" in text: action = "move"
    elif "rotate" in text or "turn" in text: action = "rotate"
    elif "land" in text: action = "land"
    elif "stop" in text or "halt" in text: action = "stop"
    elif "arm" in text: action = "arm"
    
    # Identify the direction
    direction = None
    if action in ["move", "rotate"]:
        directions = ["forward", "backward", "left", "right", "up", "down", "clockwise", "counter-clockwise"]
        for d in directions:
            if d in text:
                direction = d
                break

    # Validation check
    # Check if the action exists and if the direction is valid for that specific action
    if action in VALID_FLIGHT_COMMANDS:
        allowed_directions = VALID_FLIGHT_COMMANDS[action]
        
        if action in ["arm", "takeoff", "land", "stop"]:
            return {
                "action":action,
                "direction": None
            }
        
        if direction in allowed_directions:
            return {
                "action": action,
                "direction": direction
            }
            
    return None

# --- WRITE TO JSON FILE ---
def write_json(new_data, filename='../../logic-engine/commands.json'):
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            json.dump([], file)

    with open(filename, 'r+') as file:
        try:
            file_data = json.load(file)
        except json.JSONDecodeError:
            file_data = []

        print("Written to JSON file")
        file_data.append(new_data)
        file.seek(0)
        file.truncate()
        json.dump(file_data, file, indent=4)

# --- RETRIEVE INTEGER LOOP ---
def get_int(words):
    for word in words:
        if word in WORD_TO_DIGIT:
            return WORD_TO_DIGIT[word]
        if word.isdigit():
            return int(word)

def get_unit(words):
    for i in range(len(words) - 1):
        word = words[i]
        if word.isdigit() or word in WORD_TO_DIGIT:
            next_word = words[i + 1]
            if next_word in VALID_UNITS:
                return next_word

# --- CLEAN UP THE TEXT ---
def clean_text(text):
    return text.lower().strip()

# --- ONLY SEND THE COMMAND AND NOT DRONE&OVER ---
def remove_triggers(text):
    return re.sub(r'\b(drone|over)\b', '', text, flags=re.IGNORECASE).strip()

def flush_to_disk():
    with open(COMMANDS_FILE, 'w') as f:
        json.dump(_command_log, f, indent=4)
    print(f"Flushed {len(_command_log)} commands to disk")

def append_command(data):
    _command_log.append(data)
    flush_to_disk()

# --- MAIN STREAMING LOOP ---
# USES A COMMAND BUFFER --> LIKE A WALKIE TALKIE



def main():
    command_buffer = []
    is_active = False
    rolling_buffer = ""  

    proc = subprocess.Popen(
        [WHISPER_BIN, "-m", WHISPER_MODEL, "--step", "500", "--length", "5000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  
        text=True,
        bufsize=1  
    )

    try:
        for raw_line in proc.stdout:
            chunk = raw_line.lower().strip()
            if not chunk:
                continue

            rolling_buffer += " " + chunk
            rolling_buffer = rolling_buffer.strip()

            has_drone = "drone" in rolling_buffer and not is_active
            has_over  = bool(RE_OVER.search(rolling_buffer))
            has_stop  = "stop." in rolling_buffer

            if has_stop:
                is_active = False
                rolling_buffer = ""
                command_buffer = []
                print(">>> Force stopped")
                break

            if has_drone and not is_active:
                print(">>> Activated, listening...")
                is_active = True
                command_buffer = []
                # Trim everything before "drone" so we don't carry old noise
                drone_idx = rolling_buffer.index("drone")
                rolling_buffer = rolling_buffer[drone_idx:]

            if is_active:
                cleaned = RE_TRIGGERS.sub('', rolling_buffer).strip()

                if has_over:
                    full_command = " ".join(command_buffer) + " " + cleaned
                    full_command = full_command.strip()

                    structured = parse_and_validate(full_command)
                    if structured:
                        action = structured["action"]
                        if action in ["arm", "takeoff", "land", "stop"]:
                            structured.update(
                                {
                                    "integer" : None,
                                    "unit": None
                                }
                            )
                        else:
                            words = [w.strip(string.punctuation) for w in full_command.split()]
                            integer = get_int(words)
                            unit = get_unit(words)
                        

                            if integer and unit:
                                structured.update({"integer": integer, "unit": unit})
                                append_command(structured)
                                print(f"✓ Command: {structured}")
                            else:
                                print("DEBUG: Missing integer or unit")
                    else:
                        print("DEBUG: Invalid command")

                    # Reset everything after a completed command
                    is_active = False
                    command_buffer = []
                    rolling_buffer = ""  # Fresh start after "over"
                else:
                    if cleaned:
                        command_buffer.append(cleaned)
                    words = rolling_buffer.split()
                    if len(words) > 20:
                        rolling_buffer = " ".join(words[-20:])

    except KeyboardInterrupt:
        proc.terminate()
        flush_to_disk()
        print("Exited cleanly")

if __name__ == "__main__":
    main()