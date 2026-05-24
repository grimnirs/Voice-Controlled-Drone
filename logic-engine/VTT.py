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

#Imports & config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHISPER_BIN = "/Users/emmi/Documents/UU/kandidat/Voice-Controlled-Drone/whisper.cpp/build/bin/whisper-stream"
WHISPER_MODEL = "/Users/emmi/Documents/UU/kandidat/Voice-Controlled-Drone/whisper.cpp/models/ggml-base.en.bin"
COMMANDS_FILE = os.path.join(BASE_DIR, "commands.json")

#regex constants, detects end-of-command signal
RE_OVER = re.compile(r'\bover\b', re.IGNORECASE)
RE_TRIGGERS = re.compile(r'\b(drone|over)\b', re.IGNORECASE)

#used for validation after the model predicts an intent
VALID_FLIGHT_COMMANDS = {
    "fly": ["forward", "backward", "left", "right", "up", "down", "north", "south", "east", "west"],
    "rotate": ["clockwise", "counter clockwise", "counterclockwise"],
    "land": [None],
    "take off": [None],
    "takeoff": [None],
    "stop": [None],
    "arm": [None]
}

SYNONYM_ACTION_WORDS = {
    "go", "move", "head", "drift", "travel",
    "turn", "spin",
    "ascend", "descend", "rise", "climb", "lower", "drop",
}

ACTION_WORDS = {
    action.split()[0]
    for action in VALID_FLIGHT_COMMANDS
} | SYNONYM_ACTION_WORDS

#detects where a new command starts
# ACTION_WORDS = {
#     action.split()[0]
#     for action in VALID_FLIGHT_COMMANDS
# }

#vocabulary of what words are allowed through commands_words filter
#strips non-command words
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
    "counter", "counterclockwise", "onwards", "counter clockwise", "clockwise", "counter-clockwise",
    "higher", "lower", "up", "down", "above", "below",
    "faster", "slower", "further", "closer",
}

WORD_TO_DIGIT = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

VALID_UNITS = ["millimeters", "centimeters", "meters", "meter"]

COMMAND_WORDS = set()
# filters the rolling buffer
# built from VALID_FLIGHT_COMMANDS + CMD + WORD_TO_DIGIT + digits 0-99

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

FILLER = re.compile(r'\b(can you|please|to the |the|a|an)\b', re.IGNORECASE)

def clean_segment(text):
    return FILLER.sub('', text).strip()

def dedupe_phrases(words, max_phrase_len=3):
    i = 0
    result = []

    while i < len(words):
        repeated = False

        for size in range(max_phrase_len, 0, -1):

            if i + 2 * size <= len(words):
                first = words[i:i+size]
                second = words[i+size:i+2*size]

                if first == second:
                    result.extend(first)
                    i += 2 * size
                    repeated = True
                    break

        if not repeated:
            result.append(words[i])
            i += 1

    return result

def dedupe_commands(commands):
    seen = set()
    result = []
    for cmd in commands:
        key = (cmd["action"], cmd["direction"], cmd["integer"])
        if key not in seen:
            seen.add(key)
            result.append(cmd)
    return result

def normalize_distance(text):
    # collapse repeated digits: "5 5 5" → "5"
    text = re.sub(r'(\b\d+\b)(\s+\1)+', r'\1', text)
    
    # collapse repeated units: "meters meters meters" → "meters"
    text = re.sub(r'(\bmeters?\b)(\s+\1)+', r'\1', text)
    
    # collapse mixed digit/word repetitions: "3 three three 3" → "3"
    text = re.sub(
        r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b'
        r'(\s+\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b)+',
        lambda m: m.group(1),
        text
    )
    
    # collapse units again after number normalization
    text = re.sub(r'(\bmeters?\b)(\s+\1)+', r'\1', text)
    
    return text

def parse_multi_command(text):
    words = dedupe_phrases(text.split())
    text = normalize_distance(" ".join(words))
    segments = split_commands(text)
    segments = filter_partial_commands(segments)
    segments = list(dict.fromkeys(segments))
    print(segments)
    commands = []
    for segment in segments:
        cleaned_segment = clean_segment(segment)
        print(f"DEBUG segment: '{cleaned_segment}'")

        intent, confidence = predict(cleaned_segment)
        print(f"DEBUG intent: {intent} ({confidence:.2f})")

        if confidence < 0.6:
            print(f"DEBUG: Low confidence for segment '{cleaned_segment}'")
            continue

        # parse label into action + direction
        parts = intent.replace("_", " ").split()
        action = parts[0]
        direction = " ".join(parts[1:]) if len(parts) > 1 else None

        # validate action
        if action not in VALID_FLIGHT_COMMANDS:
            print(f"DEBUG: Unknown action '{action}'")
            continue

        allowed = VALID_FLIGHT_COMMANDS[action]

        if allowed == [None]:
            direction = None
        elif direction not in allowed:
            print(f"DEBUG: Invalid direction '{direction}' for '{action}'")
            continue

        # parse distance from original segment (still has numbers)
        words = [w.strip(string.punctuation) for w in segment.split()]
        integer = get_int(words)
        unit = get_unit(words)

        # fly requires a distance
        if action == "fly" and not (integer and unit):
            print(f"DEBUG: Missing distance/unit for fly command in '{segment}'")
            continue

        commands.append({
            "action": action,
            "direction": direction,
            "integer": integer,
            "unit": unit
        })

    return dedupe_commands(commands)

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

SPLIT_PATTERNS = re.compile(
    r'\b(and then|then|after that|followed by|and)\b', 
    re.IGNORECASE
)

def split_commands(text):
    parts = SPLIT_PATTERNS.split(text)
    parts = [p.strip() for p in parts if p.strip() and not SPLIT_PATTERNS.fullmatch(p.strip())]
    result = []
    current = []
    words = text.split()
    for word in words:
        if word in ACTION_WORDS and current and any(w in ACTION_WORDS for w in current):
            result.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        result.append(" ".join(current))

    return result if result else [text]


def flush_to_disk():
    with open(COMMANDS_FILE, 'w') as f:
        json.dump(_command_log, f, indent=4)
    print(f"Flushed {len(_command_log)} commands to disk")

def append_command(data):
    _command_log.append(data)
    flush_to_disk()
    
def filter_partial_commands(segments):
    kept = []

    for seg in segments:
        skip = False

        for other in segments:
            if seg == other:
                continue
            if seg in other and len(other) > len(seg):
                skip = True
                break

        if not skip:
            kept.append(seg)

    return kept

def main():
    is_active = False
    rolling_buffer = ""

    proc = subprocess.Popen(
        [WHISPER_BIN,
         "-m",
         WHISPER_MODEL,
         "--step", "1000",
         "--length", "5000",
         "--keep", "200",
         "-t", "8"],
        stdout=subprocess.PIPE, stderr=None, text=True, bufsize=1, cwd=os.path.dirname(WHISPER_BIN)
    )

    try:
        for raw_line in proc.stdout:
            chunk = raw_line.lower().strip()
            if not chunk or not (chunk := RE_NOISE.sub('', chunk).strip()):
                continue

            chunk_words = [w.strip(string.punctuation) for w in chunk.split()]
            rolling_buffer = (rolling_buffer + " " + " ".join(chunk_words)).strip()

            filtered_words = [w for w in rolling_buffer.split() if w.strip(string.punctuation) in COMMAND_WORDS]
            rolling_buffer = " ".join(filtered_words)

            WAKE_WORDS = {"drone", "jerome", "jeroam", "joe", "your own", "drove", "draw", "jones"}
            has_drone = any(w in rolling_buffer.split() for w in WAKE_WORDS) and not is_active
            has_over  = bool(RE_OVER.search(rolling_buffer))
            has_stop  = bool(re.search(r'\bstop\b', rolling_buffer))

            if has_stop and is_active:
                is_active, rolling_buffer = False, ""
                print(">>> Force stopped")
                continue

            if has_drone and not is_active:
                print(">>> Activated, listening...")
                is_active, rolling_buffer = True, ""
                continue

            if is_active and has_over:
                t_start = time.time()
                cleaned = RE_TRIGGERS.sub('', rolling_buffer).strip()
                print(f"DEBUG predict input: '{cleaned}'")

                commands = parse_multi_command(cleaned)

                if commands:

                    _command_log.clear()

                    for structured in commands:
                        append_command(structured)
                        print(f"✓ Command: {structured}")
                else:
                    print(f"DEBUG: No valid commands parsed from '{cleaned}'")

                print(f"LATENCY: {(time.time() - t_start) * 1000:.1f}ms")
                is_active, rolling_buffer = False, ""

    except KeyboardInterrupt:
        proc.terminate()
        flush_to_disk()
        print("Exited cleanly")

if __name__ == "__main__":
    main()