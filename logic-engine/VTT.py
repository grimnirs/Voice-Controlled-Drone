import sys
import json
import asyncio
import os
import string
import re
import subprocess
import requests

# tanken är att vi ska importa 
# OBS MAN MÅSTE VA INNE I BUILD 
# ./bin/whisper-stream -m ../models/ggml-base.en.bin --step 500 --length 5000 | python3 ../../logic-engine/VTT.py
# så att den körs när man kör main, så börjar den lyssna direkt
# man kan inte säga move to the left, edgecase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHISPER_BIN = os.environ.get(
    "WHISPER_BIN",
    "/Users/feliciafalldin/Kanden/Voice-Controlled-Drone/logic-engine/whisper.cpp/build/bin/stream"
)
WHISPER_MODEL = os.environ.get(
    "WHISPER_MODEL",
    "/Users/feliciafalldin/Kanden/Voice-Controlled-Drone/logic-engine/whisper.cpp/models/ggml-base.en.bin"
)

COMMANDS_FILE = os.path.join(BASE_DIR, "commands.json")

RE_OVER = re.compile(r'\bover\b', re.IGNORECASE)
RE_TRIGGERS = re.compile(r'\b(drone|over)\b', re.IGNORECASE)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# A dictionary of valid Action -> Direction pairs
VALID_FLIGHT_COMMANDS = {
    "fly": ["forward", "backward", "left", "right", "up", "down"],
    "rotate": ["clockwise", "counter clockwise"],
    "land": [None],
    "take off": [None],
    "stop": [None],
    "arm": [None]
}

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

VALID_UNITS = ["millimeters", "centimeters", "meters", "meter"]

_command_log = []


def gemma_parse(text):
    prompt = f"""
Return ONLY valid JSON. No text before or after.

Schema:
{{
  "action": "fly|rotate|land|take off|stop|arm",
  "direction": "forward|backward|left|right|up|down|clockwise|counter clockwise|null",
  "integer": number|null,
  "unit": "meters|centimeters|millimeters|null"
}}

Rules:
- If missing → use null
- No explanations
- No extra keys
- No comments
- go, move, head, west all mean fly
- turn means rotate
- halt means stop

Input: "{text}"
"""

    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": "gemma4:e4b",
            "prompt": prompt,
            "stream": False
        }
    )

    print(response.status_code)
    print(response.json())

    raw = response.json()["response"]

    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)
    except Exception:
        print("DEBUG: invalid JSON from Gemma:", raw)
        return None


# def write_json(new_data, filename="../../logic-engine/commands.json"):
#     if not os.path.exists(filename):
#         with open(filename, "w") as file:
#             json.dump([], file)

#     with open(filename, "r+") as file:
#         try:
#             file_data = json.load(file)
#         except json.JSONDecodeError:
#             file_data = []

#         print("Written to JSON file")
#         file_data.append(new_data)
#         file.seek(0)
#         json.dump(file_data, file, indent=4)


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


def clean_text(text):
    return text.lower().strip()


def remove_triggers(text):
    return re.sub(r'\b(drone|over)\b', '', text, flags=re.IGNORECASE).strip()


def flush_to_disk():
    with open(COMMANDS_FILE, "w") as f:
        json.dump(_command_log, f, indent=4)
    print(f"Flushed {len(_command_log)} commands to disk")


def append_command(data):
    _command_log.append(data)
    flush_to_disk()


def validate_gemma(result):
    if not result:
        return False

    action = result.get("action")
    direction = result.get("direction")

    if action not in VALID_FLIGHT_COMMANDS:
        print(f"DEBUG: invalid action '{action}'")
        return False

    allowed = VALID_FLIGHT_COMMANDS[action]

    if allowed == [None]:
        return True

    if direction not in allowed:
        print(f"DEBUG: invalid direction '{direction}' for '{action}'")
        return False

    return True