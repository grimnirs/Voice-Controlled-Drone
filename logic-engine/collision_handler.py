import json
import asyncio
from colorama import Fore, Back, Style, init


DISTANCES_FILE = "/shared/distances.json"
COLLISION_THRESHOLD = 1.0  # meters

async def watch_distance():
    print("Starting collision handler...")
    while True:
        try:
            with open(DISTANCES_FILE, 'r') as f:
                distances = json.load(f)
            
            forward = distances.get("forward")
            if forward is not None:
                if forward <= 3.0:
                    print(f'{Style.BRIGHT}{Fore.RED} "BEWARE! Forward distance at: {forward:.2}m"')
                else:
                    print(f'{Style.BRIGHT}{Fore.GREEN}"Forward distance at: {forward:.2f}m"')
                await asyncio.sleep(1)
            
        except Exception as e:
            pass  # file might not exist yet
        
        await asyncio.sleep(0.1)

def get_forward_distance():
    try:
        with open(DISTANCES_FILE, 'r') as f:
            distances = json.load(f)
        return distances.get("forward")
    except:
        return None

def is_obstacle_forward():
    dist = get_forward_distance()
    return dist is not None and dist < COLLISION_THRESHOLD