import sys
import json
import asyncio
import os
import string
import re
import subprocess
import time
from nlp.model import predict
from nlp.intent_map import map_intent

# BASE PATHS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHISPER_BIN = os.environ.get("WHISPER_BIN", "/Users/feliciafalldin/Kanden/Voice-Controlled-Drone/whisper.cpp/build/bin/whisper-stream")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "/Users/feliciafalldin/Kanden/Voice-Controlled-Drone/whisper.cpp/models/ggml-base.en.bin")
COMMANDS_FILE = os.path.join(BASE_DIR, "commands.json")

RE_OVER = re.compile(r'\bover\b', re.IGNORECASE)
RE_TRIGGERS = re.compile(r'\b(drone|over)\b', re.IGNORECASE)

VALID_FLIGHT_COMMANDS = {
    "fly": ["forward", "backward", "left", "right", "up", "down", "north", "south", "east", "west"],
    "rotate": ["clockwise", "counter clockwise"],
    "land": [None],
    "take off": [None],
    "takeoff": [None],
    "stop": [None],
    "arm": [None]
}

# SYNONYM_MAP = {
#     "go": "fly", "move": "fly", "travel": "fly",
#     "turn": "rotate", "spin": "rotate",
#     "halt": "stop", "kill": "stop",
#     "ascend": "up", "descend": "down",
#     "forwards": "forward", "backwards": "backward",
#     "clockwise": "clockwise", "counter-clockwise": "counter clockwise"
# }

CMD = {
    "go", "move", "head", "drift", "travel",
    "turn", "spin",
    "halt", "kill",
    "ascend", "descend", "rise", "climb", "lower", "drop",
    "forwards", "backwards", "back", "reverse", "ahead", "straight",
    "launch", "lift", "takeoff", "initialize", "start",
    "touch", "come", "set", "please", "now", "immediately",
    "emergency", "motors", "the", "to",
    "take", "off", "takeoff",
    "north", "south", "east", "west", "airborne", "clockwise",
    "counter", "counterclockwise", "onwards", "counter clockwise",
    "higher", "lower", "up", "down", "above", "below",
    "faster", "slower", "further", "closer",
}

WORD_TO_DIGIT = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

VALID_UNITS = ["millimeters", "centimeters", "meters", "meter"]

COMMAND_WORDS = set()
for action, directions in VALID_FLIGHT_COMMANDS.items():
    for word in action.split(): COMMAND_WORDS.add(word)
    for d in (directions or []):
        if d:
            for word in d.split(): COMMAND_WORDS.add(word)

# COMMAND_WORDS |= set(SYNONYM_MAP.keys())
COMMAND_WORDS |= CMD
COMMAND_WORDS |= set(WORD_TO_DIGIT.keys())
COMMAND_WORDS |= {"drone", "over", "stop", "meters", "meter", "centimeters", "millimeters", "take", "off", "takeoff"}
COMMAND_WORDS |= {str(i) for i in range(100)}

NOISE_PATTERNS = [
    r'\[blank_audio\]', r'\[inaudible\]', r'\[laughter\]',
    r'\[applause\]', r'crowd\s*\w*', r'non-english',
    r'foreign language', r'blank_audio'
]
RE_NOISE = re.compile('|'.join(NOISE_PATTERNS), re.IGNORECASE)

_command_log = []

def parse_and_validate(text):
    text = text.lower()
    # action = None
    # if "move" in text or "fly" in text: action = "fly"
    # elif "rotate" in text or "turn" in text: action = "rotate"
    # elif "land" in text: action = "land"
    # elif "stop" in text or "halt" in text: action = "stop"
    # elif "take off" in text: action = "take off"
    # elif "arm" in text: action = "arm"
    
    # direction = None
    # if action in ["fly", "rotate"]:
    #     directions = ["forward", "backward", "left", "right", "up", "down", "clockwise", "counter clockwise"]
    #     for d in directions:
    #         if d in text:
    #             direction = d
    #             break
    
    action, direction = map_intent(text)

    if action in VALID_FLIGHT_COMMANDS:
        allowed_directions = VALID_FLIGHT_COMMANDS[action]
        if action in ["arm", "take off", "land", "stop", "takeoff" ]:
            return {"action": action, "direction": None}
        if direction in allowed_directions:
            return {"action": action, "direction": direction}
    return None

def get_int(words):
    for word in words:
        if word in WORD_TO_DIGIT: return WORD_TO_DIGIT[word]
        if word.isdigit(): return int(word)
    return None

def get_unit(words):
    for i in range(len(words) - 1):
        word = words[i]
        if word.isdigit() or word in WORD_TO_DIGIT:
            next_word = words[i + 1]
            if next_word in VALID_UNITS: return next_word
    return None

def flush_to_disk():
    with open(COMMANDS_FILE, 'w') as f:
        json.dump(_command_log, f, indent=4)
    print(f"Flushed {len(_command_log)} commands to disk")

def append_command(data):
    _command_log.append(data)
    flush_to_disk()

# def normalize_text(words):
#     return [SYNONYM_MAP.get(w, w) for w in words]

def main():
    is_active = False
    rolling_buffer = ""  

    proc = subprocess.Popen(
        [WHISPER_BIN, 
         "-m", 
         WHISPER_MODEL, 
         "--step", "1000", #how often whisper processes words
         "--length", "5000", #audio window
         "--keep", "200", #how much audio to keep from earlier window
         "-t", "8"], #number of cpu threads
        stdout=subprocess.PIPE, stderr=None, text=True, bufsize=1, cwd=os.path.dirname(WHISPER_BIN)
    )

    try:
        for raw_line in proc.stdout:
            chunk = raw_line.lower().strip()
            if not chunk or not (chunk := RE_NOISE.sub('', chunk).strip()): continue

            chunk_words = [w.strip(string.punctuation) for w in chunk.split()]
            # chunk_words = normalize_text(chunk_words)
            rolling_buffer = (rolling_buffer + " " + " ".join(chunk_words)).strip()

            filtered_words = [w for w in rolling_buffer.split() if w.strip(string.punctuation) in COMMAND_WORDS]
            rolling_buffer = " ".join(filtered_words)

            has_drone = "drone" in rolling_buffer and not is_active
            has_over  = bool(RE_OVER.search(rolling_buffer))
            has_stop = bool(re.search(r'\bstop\b', rolling_buffer))


            if has_stop and is_active:
                is_active, rolling_buffer = False, ""
                print(">>> Force stopped")
                continue

            if has_drone and not is_active:
                print(">>> Activated, listening...")
                is_active, rolling_buffer = True, "drone"
                continue

            if is_active:
                cleaned = RE_TRIGGERS.sub('', rolling_buffer).strip()
                if has_over:
                    t_start = time.time()
                    print(f"DEBUG predict input: '{cleaned}'")
                    #train_data = map_intent(cleaned)
                    print(rolling_buffer)
                    intent, confidence = predict(cleaned)
                    print(f"DEBUG intent: {intent}, confidence: {confidence:.2f}")
                    if confidence >= 0.6:
                        # structured = parse_and_validate(intent)
                        action, direction = map_intent(intent)

                        if action not in VALID_FLIGHT_COMMANDS:
                            print(f"DEBUG: Invalid action '{action}'")
                            continue

                        if direction not in VALID_FLIGHT_COMMANDS[action]:
                            print(f"DEBUG: Invalid direction '{direction}' for '{action}'")
                            continue
                        
                        structured = {
                            "action": action,
                            "direction": direction
                        }

                        if structured is not None:
                            # action = structured["action"]
                            
                            if action in ["arm", "take off", "land", "stop", "takeoff"]:
                                structured.update({"integer": None, "unit": None})
                                append_command(structured)
                                print(f"✓ Command: {structured}")
                                t_end = time.time()
                                print(f"LATENCY: {(t_end - t_start) * 1000:.1f}ms")
                            
                            else:
                                words = [w.strip(string.punctuation) for w in cleaned.split()]
                                integer = get_int(words)
                                unit = get_unit(words)
                                
                                if action == "rotate" or (integer and unit):
                                    structured.update({"integer": integer, "unit": unit})     
                                    append_command(structured)
                                    print(f"✓ Command: {structured}")
                                    t_end = time.time()
                                    print(f"LATENCY: {(t_end - t_start) * 1000:.1f}ms")
                                else:
                                    print(f"DEBUG: Missing distance or unit for '{action}'")
                        else:
                            print(f"DEBUG: Regex validation failed for '{cleaned}'")
                    else:
                        print(f"DEBUG: Low confidence ({confidence:.2f})")

                    is_active, rolling_buffer = False, ""

    except KeyboardInterrupt:
        proc.terminate()
        flush_to_disk()
        print("Exited cleanly")

if __name__ == "__main__":
    main()