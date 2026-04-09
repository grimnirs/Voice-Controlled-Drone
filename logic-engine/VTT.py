import sys
import sys
import json
import asyncio
import os
import string

#tanken är att vi ska importa 
#OBS MAN MÅSTE VA INNE I BUILD 
#./bin/whisper-stream -m ../models/ggml-base.en.bin --step 500 --length 5000 | python3 ../../logic-engine/VTT.py
#så att den körs när man kör main, så börjar den lyssna direkt


# A dictionary of valid Action -> Direction pairs
VALID_FLIGHT_COMMANDS = {
    "move": ["forward", "backward", "left", "right", "up", "down"],
    "rotate": ["clockwise", "counter-clockwise"],
    "land": [None],      # Land doesn't need a direction
    "takeoff": [None],   # Takeoff doesn't need a direction
    "stop": [None]
}

VALID_UNITS = ["millimeters", "centimeters", "meters"]

def parse_and_validate(text):
    text = text.lower()
    
    # 1. Identify the Action
    action = None
    if "move" in text or "fly" in text: action = "move"
    elif "rotate" in text or "turn" in text: action = "rotate"
    elif "land" in text: action = "land"
    elif "stop" in text or "halt" in text: action = "stop"
    
    # 2. Identify the Direction
    direction = None
    directions = ["forward", "backward", "left", "right", "up", "down", "clockwise", "counter-clockwise"]
    for d in directions:
        if d in text:
            direction = d
            break

    # 3. Validation Check
    # Check if the action exists and if the direction is valid for that specific action
    if action in VALID_FLIGHT_COMMANDS:
        allowed_directions = VALID_FLIGHT_COMMANDS[action]
        
        if direction in allowed_directions:
            # SUCCESS: The combination is valid
            return {
                "action": action,
                "direction": direction
            }
            
    # If the combination is invalid or action is missing, return None
    return None

# --- WRITE TO JSON FILE ---
def write_json(new_data, filename='../../logic-engine/commands.json'):
    # If file doesn't exist, create it as an empty list
    print("nu är vi inne i write_json")
    if not os.path.exists(filename):
        print("vi hittar inte filen")
        with open(filename, 'w') as file:
            json.dump([], file)

    with open(filename, 'r+') as file:
        try:
            print("nu är vi inne i try")
            file_data = json.load(file)
        except json.JSONDecodeError:
            print("oj nu har vi hittat något fel")
            file_data = []

        # Append new command dictionary
        print("yes nu lägger vi till i filen")
        file_data.append(new_data)

        # Go back to start, truncate, and save
        file.seek(0)
        file.truncate()
        json.dump(file_data, file, indent=4)

# --- RETRIEVE INTEGER LOOP ---
def get_int(cmd):
    print("nu är vi inne i get int")
    words = cmd.lower().split()
    i = 0
    while i < len(words):
        if words[i].isdigit():
            dist = int(words[i])
            return dist
        else:
            i = i + 1
            continue #ska vi ha en default distans den flyttar framåt?
            
# # --- RETRIEVE UNIT LOOP ---
# def get_unit(cmd):
#     print("nu är vi inne i get unit")
#     words = cmd.lower().split()
#     i = 0
#     while i < len(words):
#         print("nu är vi inne i unit loop")
#         print("why is it empty", words[i])
#         break
#         if words[i].isdigit():
#             if words[i + 1] in VALID_UNITS:
#                 unit = words[i + 1]
#                 print("nu returnerar vi unit")
#                 return unit
#         else:
#             i = i + 1
#             continue # ska vi ha en default?

def get_unit(cmd):
    print("nu är vi inne i get unit")
    # split() handles spaces, but we need to remove punctuation like '.' or ','
    words = cmd.lower().split()
    
    # Clean the words (removes dots, commas, etc.)
    cleaned_words = [w.strip(string.punctuation) for w in words]
    print(f"Cleaned words for unit search: {cleaned_words}")

    for i in range(len(cleaned_words) - 1):
        if cleaned_words[i].isdigit():
            next_word = cleaned_words[i + 1]
            print("vi hittar ingen unit")
            if next_word in VALID_UNITS:
                print(f"Hittade unit: {next_word}")
                return next_word
        else:
            i = i + 1
            continue # ska vi ha en default?


# --- MAIN STREAMING LOOP ---
async def main():
    print("vi är inne i main loopen")
    for cmd in sys.stdin:
        cmd = cmd.strip()
        if not cmd:
            continue
        
        print("got cmd:", cmd)
        if "stop." in cmd.lower():
            #sys.stdin.close()
            break
        print("vart fan är vi")        
        if "drone" in cmd.lower():   
            print("yes vi har detected drone")
            structured_json = parse_and_validate(cmd)
            if structured_json:
                print("yes vi har hittat ett bra kommando")
                # If valid, convert to string and proceed to MAVSDK
                print(cmd)
                #sys.stdin.close()
                integer = get_int(cmd)
                unit = get_unit(cmd)
                    
                structured_json.update({
                    "integer": integer,
                    "unit": unit
                })
                if integer is None or unit is None:
                    print("DEBUG: Invalid command, no integer or unit in command")
                    break
                print(structured_json)
                write_json(structured_json)
                print("nu ska vi ha skrivit till json filen")
                # print("VALID COMMAND FOUND:", json.dumps(structured_json))
                # Here you would call your MAVSDK function:
                # execute_mavlink_command(structured_json)
                
            else:
                # If invalid, the script naturally "continues" to the next cmd of text
                print("DEBUG: Invalid command combination detected, skipping...")
                # continue
            
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass