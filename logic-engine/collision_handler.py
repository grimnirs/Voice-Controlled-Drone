import json
import asyncio
from colorama import Fore, Back, Style, init
from collections import deque


DISTANCES_FILE = "/shared/distances.json"
COLLISION_THRESHOLD = 2.0  # meters

SENSORS_ENABLED = False

def enable_sensors():
    global SENSORS_ENABLED
    SENSORS_ENABLED = True

def disable_sensors():
    global SENSORS_ENABLED
    SENSORS_ENABLED = False

def avg_readings(readings_buffer: deque):
    if not readings_buffer:
        return None
    median = sum(readings_buffer)/len(readings_buffer)
    return median

#----------------------- FORWARD SENSOR -------------------------#
async def watch_distance_fwd():
    print("Starting collision handler (fwd)...")
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

        except Exception:
            pass  # file might not exist yet

        await asyncio.sleep(0.5)

def get_forward_distance():
    try:
        with open(DISTANCES_FILE, 'r') as f:
            distances = json.load(f)
        return distances.get("forward")
    except:
        return None

def is_obstacle_forward():
    dist_fwd = get_forward_distance()
    return dist_fwd is not None and dist_fwd < COLLISION_THRESHOLD

#----------------------- UP SENSOR -------------------------#
async def watch_distance_up():
    print("Starting collision handler (up)...")
    while True:
        try:
            with open(DISTANCES_FILE, 'r') as f:
                distances = json.load(f)

            up = distances.get("up")
            if up is not None:
                if up <= 3.0:
                    print(f'{Style.BRIGHT}{Fore.MAGENTA} "BEWARE! Up distance at: {up:.2}m"')
                else:
                    print(f'{Style.BRIGHT}{Fore.CYAN}"Up distance at: {up:.2f}m"')

        except Exception:
            pass  # file might not exist yet

        await asyncio.sleep(1)

def get_up_distance():
    try:
        with open(DISTANCES_FILE, 'r') as f:
            distances = json.load(f)
        return distances.get("up")
    except:
        return None

def is_obstacle_up():
    dist_up = get_up_distance()
    return dist_up is not None and dist_up < COLLISION_THRESHOLD


#----------------------- DOWN SENSOR -------------------------#
async def watch_distance_down():
    print("Starting collision handler (down)...")
    while True:
        try:
            if SENSORS_ENABLED:
                with open(DISTANCES_FILE, 'r') as f:
                    distances = json.load(f)

                down = distances.get("down")
                if down is not None:
                    if down <= 2.0:
                        print(f'{Style.BRIGHT}{Fore.YELLOW} "BEWARE! Down distance at: {down:.2}m"')
                    else:
                        print(f'{Style.BRIGHT}{Fore.BLUE}"Down distance at: {down:.2f}m"')

        except Exception:
            pass  # file might not exist yet

        await asyncio.sleep(1)

def get_down_distance():
    try:
        with open(DISTANCES_FILE, 'r') as f:
            distances = json.load(f)
        return distances.get("down")
    except:
        return None

def is_obstacle_down():
    dist_down = get_down_distance()
    return dist_down is not None and dist_down < COLLISION_THRESHOLD