import sys
import json
import asyncio
import os
import string
import re
import subprocess
import time


#tanken är att vi ska importa 
#OBS MAN MÅSTE VA INNE I BUILD 
#./bin/whisper-stream -m ../models/ggml-base.en.bin --step 500 --length 5000 | python3 ../../logic-engine/VTT.py
#så att den körs när man kör main, så börjar den lyssna direkt
#man kan inte säga move to the left, edgecase

#Nästa steg: "move to the left 10 meters and then move to the left 5 meters and then move up 3 meters..."
#Förbättra hanteringen av kommandon, just nu krävs en del timeing med samplingen
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHISPER_BIN = os.environ.get("WHISPER_BIN", "/Users/feliciafalldin/Kanden/Voice-Controlled-Drone/logic-engine/whisper.cpp/build/bin/stream")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "/Users/feliciafalldin/Kanden/Voice-Controlled-Drone/logic-engine/whisper.cpp/models/ggml-base.en.bin")
COMMANDS_FILE = os.path.join(BASE_DIR, "commands.json")

RE_OVER = re.compile(r'\bover\b', re.IGNORECASE)
RE_TRIGGERS = re.compile(r'\b(drone|over)\b', re.IGNORECASE)

# A dictionary of valid Action -> Direction pairs
VALID_FLIGHT_COMMANDS = {
    "fly": ["forward", "backward", "left", "right", "up", "down"],
    "rotate": ["clockwise", "counter clockwise"],
    "land": [None],      # Land doesn't need a direction
    "take off": [None],   # Takeoff doesn't need a direction
    "stop": [None],
    "arm": [None]
}
SYNONYM_MAP = {
    "go": "fly",
    "move": "fly",
    "travel": "fly",
    "turn": "rotate",
    "spin": "rotate",
    "halt": "stop",
    "kill": "stop",
    "ascend": "up",
    "descend": "down",
    "forwards": "forward",
    "backwards": "backward",
    "clockwise": "clockwise",
    "counter-clockwise": "counter clockwise"
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

COMMAND_WORDS = set()
for action, directions in VALID_FLIGHT_COMMANDS.items():
    for word in action.split():
        COMMAND_WORDS.add(word)
    for d in (directions or []):
        if d:
            for word in d.split():
                COMMAND_WORDS.add(word)

COMMAND_WORDS |= set(SYNONYM_MAP.keys())
COMMAND_WORDS |= set(WORD_TO_DIGIT.keys())
COMMAND_WORDS |= {"drone", "over", "stop", "meters", "meter", "centimeters", "millimeters"}
COMMAND_WORDS |= {str(i) for i in range(100)}

NOISE_PATTERNS = [
    r'\[blank_audio\]', r'\[inaudible\]', r'\[laughter\]',
    r'\[applause\]', r'crowd\s*\w*', r'non-english',
    r'foreign language', r'blank_audio'
]
RE_NOISE = re.compile('|'.join(NOISE_PATTERNS), re.IGNORECASE)

_command_log = []

# This function checks for valid action and directions with regard to the
def parse_and_validate(text):
    text = text.lower()
    
    # Identify the action
    action = None
    if "move" in text or "fly" in text: action = "fly"
    elif "rotate" in text or "turn" in text: action = "rotate"
    elif "land" in text: action = "land"
    elif "stop" in text or "halt" in text: action = "stop"
    elif "take off" in text: action = "take off"
    elif "arm" in text: action = "arm"
    
    # Identify the direction
    direction = None
    if action in ["fly", "rotate"]:
        directions = ["forward", "backward", "left", "right", "up", "down", "clockwise", "counter clockwise"]
        for d in directions:
            if d in text:
                direction = d
                break

    # Validation check
    # Check if the action exists and if the direction is valid for that specific action
    if action in VALID_FLIGHT_COMMANDS:
        allowed_directions = VALID_FLIGHT_COMMANDS[action]
        
        if action in ["arm", "take off", "land", "stop"]:
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

# -- synonyms ---
def normalize_text(words):
    """Replaces synonyms with formal command keys."""
    return [SYNONYM_MAP.get(w, w) for w in words]

# --- MAIN STREAMING LOOP ---
# USES A COMMAND BUFFER --> LIKE A WALKIE TALKIE

def main():
    command_buffer = []
    is_active = False
    rolling_buffer = ""  

    # Create a whitelist for the iterative discard logic
    WHITELIST = set(VALID_FLIGHT_COMMANDS.keys()) | set(SYNONYM_MAP.keys()) | \
                {"drone", "over", "meters", "meter", "centimeters", "millimeters"}

    proc = subprocess.Popen(
        [WHISPER_BIN, "-m", WHISPER_MODEL, 
         "--step", "500", "--length", "5000",
         "--keep", "0", # Set to 0 to prevent audio ghosting/repetition in noise
         "-t", "8"],
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        bufsize=1,
        cwd=os.path.dirname(WHISPER_BIN)
    )

    try:
        for raw_line in proc.stdout:
            chunk = raw_line.lower().strip()
            if not chunk:
                continue

            # 1. Strip noise patterns from chunk
            chunk = RE_NOISE.sub('', chunk).strip()
            if not chunk:
                continue

            # 2. Normalize synonyms
            chunk_words = [w.strip(string.punctuation) for w in chunk.split()]
            chunk_words = normalize_text(chunk_words)
            chunk = " ".join(chunk_words)

            # 3. Append to buffer
            rolling_buffer += " " + chunk
            rolling_buffer = rolling_buffer.strip()

            # 4. Continuously prune buffer to only valid command words
            filtered_words = [
                w for w in rolling_buffer.split()
                if w.strip(string.punctuation) in COMMAND_WORDS
            ]
            rolling_buffer = " ".join(filtered_words)

            has_drone = "drone" in rolling_buffer and not is_active
            has_over  = bool(RE_OVER.search(rolling_buffer))
            has_stop  = "stop" in rolling_buffer

            if has_stop and not is_active:
                # Ignore "stop" outside active session
                pass

            if has_stop and is_active:
                is_active = False
                rolling_buffer = ""
                print(">>> Force stopped")
                continue

            if has_drone and not is_active:
                print(">>> Activated, listening...")
                is_active = True
                rolling_buffer = "drone"  # Hard reset, no noise carried forward

            if is_active:
                cleaned = RE_TRIGGERS.sub('', rolling_buffer).strip()
                print(f"DEBUG heard: '{rolling_buffer}'")
                print(f"DEBUG cleaned: '{cleaned}'")

                if has_over:
                    structured = parse_and_validate(cleaned)
                    if structured:
                        action = structured["action"]
                        if action in ["arm", "take off", "land", "stop", "rotate"]:
                            structured.update({"integer": None, "unit": None})
                            append_command(structured)
                        else:
                            words = [w.strip(string.punctuation) for w in cleaned.split()]
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

                    is_active = False
                    rolling_buffer = ""

    except KeyboardInterrupt:
        proc.terminate()
        flush_to_disk()
        print("Exited cleanly")


if __name__ == "__main__":
    main()