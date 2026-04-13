import sys
import sys
import json
import asyncio
import os
import string
import re

#tanken är att vi ska importa 
#OBS MAN MÅSTE VA INNE I BUILD 
#./bin/whisper-stream -m ../models/ggml-base.en.bin --step 500 --length 5000 | python3 ../../logic-engine/VTT.py
#så att den körs när man kör main, så börjar den lyssna direkt
#man kan inte säga move to the left, edgecase

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

# This function checks for valid action and directions with regard to the
def parse_and_validate(text):
    text = text.lower()
    
    # Identify the action
    action = None
    if "move" in text or "fly" in text: action = "move"
    elif "rotate" in text or "turn" in text: action = "rotate"
    elif "land" in text: action = "land"
    elif "stop" in text or "halt" in text: action = "stop"
    
    # Identify the direction
    direction = None
    directions = ["forward", "backward", "left", "right", "up", "down", "clockwise", "counter-clockwise"]
    for d in directions:
        if d in text:
            direction = d
            break

    # Validation check
    # Check if the action exists and if the direction is valid for that specific action
    if action in VALID_FLIGHT_COMMANDS:
        allowed_directions = VALID_FLIGHT_COMMANDS[action]
        
        if direction in allowed_directions:
            return {
                "action": action,
                "direction": direction
            }
            
    # If the combination is invalid or action is missing, return None
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
def get_int(cmd):
    words = cmd.lower().split()
    words = [w.strip(string.punctuation) for w in words]
    
    for word in words:
        if word in WORD_TO_DIGIT:
            return WORD_TO_DIGIT[word]
        if word.isdigit():
            return int(word)

# --- RETRIEVE UNIT LOOP ---            
def get_unit(cmd):
    words = cmd.lower().split()
    
    cleaned_words = [w.strip(string.punctuation) for w in words]

    for i in range(len(cleaned_words) - 1):
        word = cleaned_words[i]
        print(cleaned_words[i])
        if word.isdigit() or word in WORD_TO_DIGIT:
            next_word = cleaned_words[i + 1]
            if next_word in VALID_UNITS:
                return next_word
        else:
            i = i + 1
            continue # ska vi ha en default?

# --- CLEAN UP THE TEXT ---
def clean_text(text):
    return text.lower().strip()

# --- ONLY SEND THE COMMAND AND NOT DRONE&OVER ---
def remove_triggers(text):
    return re.sub(r'\b(drone|over)\b', '', text, flags=re.IGNORECASE).strip()

# --- MAIN STREAMING LOOP ---
# USES A COMMAND BUFFER --> LIKE A WALKIE TALKIE
async def main():
    command_buffer = []
    is_active = False

    for cmd in sys.stdin:
        cmd = clean_text(cmd)
        if not cmd:
            continue
    
        if "stop." in cmd.lower():
            is_active = False

        if "drone" in cmd.lower() and not is_active:
            print(">>> Listening: ")
            print(cmd)
            if "stop." in cmd.lower():
                is_active = False
            else:
                is_active = True
                command_buffer = []
        
        if is_active:
            cleaned = remove_triggers(cmd)
            if cleaned:
                command_buffer.append(cleaned)
            
            
            if re.search(r'\bover\b', cmd.lower().strip(string.punctuation)):
                full_command = " ".join(command_buffer)
                structured_json = parse_and_validate(full_command)
                print(structured_json)
                
                if structured_json:
                    # If valid, convert to string and proceed to MAVSDK
                    print(cmd)
                    integer = get_int(full_command)
                    unit = get_unit(full_command)
                        
                    if integer is None or unit is None:
                        print("DEBUG: Invalid command, no integer or unit in command")
                        continue
                    else:
                        structured_json.update({
                            "integer": integer,
                            "unit": unit
                        })
                        print("nu skriver vi till json filen")
                        write_json(structured_json)
                        # Here you would call your MAVSDK function:
                        # execute_mavlink_command(structured_json)
                else:
                    print("DEBUG: Invalid command combination detected, skipping...")
                print(">>> Stopped Listening")
                is_active = False
                command_buffer = []
            else:
                print("Did not detect 'over'")
        else:
            print(">>> Stopped Listening")

           
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass