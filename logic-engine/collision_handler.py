import json
import asyncio
from colorama import Fore, Back, Style, init
from numpy import mean
from collections import deque

DISTANCES_FILE = "/shared/distances.json"
COLLISION_THRESHOLD = 2.5  # meters

SENSORS_ENABLED = False

def enable_sensors():
    global SENSORS_ENABLED
    SENSORS_ENABLED = True

def disable_sensors():
    global SENSORS_ENABLED
    SENSORS_ENABLED = False

fwd_buffer = deque(maxlen=3)
up_buffer = deque(maxlen=3)
down_buffer = deque(maxlen=3)

def avg_readings(readings_buffer: deque):
    if not readings_buffer:
        return None
    mean_buffer = mean(readings_buffer)
    return mean_buffer


def stopping_distance(current_velocity: float, direction: str) -> float:
    DECELERATION = {
        "forward":  1.0,   # was 3.0 - too optimistic
        "up":       1.2,   # was 2.0 - gravity makes this much harder
        "down":     1.2,   # was 1.5 - gravity actively assists descent
    }
    SAFETY_MARGIN = {
        "forward":  1.5,   # was 0.3
        "up":       1.5,   # was 0.5 - needs much more room
        "down":     1.5,   # was 0.7
    }

    a = DECELERATION[direction]
    d = (current_velocity ** 2) / (2 * a)
    return d + SAFETY_MARGIN[direction]


#----------------------- FORWARD SENSOR -------------------------#
def get_forward_distance():
    try:
        with open(DISTANCES_FILE, 'r') as f:
            distances = json.load(f)
        forward = distances.get("forward")
        if forward is not None:
            fwd_buffer.append(forward)
        forward_readings = avg_readings(fwd_buffer)
        return forward_readings
    except:
        return None
    
async def watch_distance_fwd():
    print("Starting collision handler (fwd)...")
    while True:
        try:
            forward_readings = get_forward_distance()

            if forward_readings is not None:
                if forward_readings <= 3.0:
                    print(f'{Style.BRIGHT}{Fore.RED} "BEWARE! Forward distance at: {forward_readings:.2}m"')
                else:
                    print(f'{Style.BRIGHT}{Fore.GREEN}"Forward distance at: {forward_readings:.2f}m"')
                await asyncio.sleep(2)
            
        except Exception as e:
            pass  # file might not exist yet
        await asyncio.sleep(0.05)

def is_obstacle_forward(current_velocity: float):
    # dist_fwd = get_forward_distance()
    # return dist_fwd is not None and dist_fwd <= COLLISION_THRESHOLD
    dist = get_forward_distance()
    if dist is None:
        return False
    return dist < stopping_distance(current_velocity, "forward")

#----------------------- UP SENSOR -------------------------#
def get_up_distance():
    try:
        with open(DISTANCES_FILE, 'r') as f:
            distances = json.load(f)
        up = distances.get("up")
        if up is not None:
            up_buffer.append(up)
        up_readings = avg_readings(up_buffer)
        return up_readings
    except:
        return None

async def watch_distance_up():
    print("Starting collision handler (up)...")
    while True:
        try:
            up_readings = get_up_distance()
            
            if up_readings is not None:
                if up_readings <= 3.0:
                    print(f'{Style.BRIGHT}{Fore.MAGENTA} "BEWARE! Up distance at: {up_readings:.2}m"')
                else:
                    print(f'{Style.BRIGHT}{Fore.CYAN}"Up distance at: {up_readings:.2f}m"')
                await asyncio.sleep(2)
            
        except Exception as e:
            pass  # file might not exist yet
        
        await asyncio.sleep(0.05)

def is_obstacle_up(current_velocity: float):
    # dist_up = get_up_distance()
    # return dist_up is not None and dist_up <= COLLISION_THRESHOLD
    dist = get_up_distance()
    if dist is None:
        return False
    return dist < stopping_distance(current_velocity, "up")

#----------------------- DOWN SENSOR -------------------------#
def get_down_distance():
    try:
        with open(DISTANCES_FILE, 'r') as f:
            distances = json.load(f)
        down = distances.get("down")
        if down is not None:
            down_buffer.append(down)
        down_readings = avg_readings(down_buffer)
        return down_readings
    except:
        return None

async def watch_distance_down():
    print("Starting collision handler (down)...")
    while True:
        try:
                down_readings = get_down_distance()
                if down_readings is not None:
                    if down_readings <= 2.0:
                        print(f'{Style.BRIGHT}{Fore.LIGHTBLUE_EX} "BEWARE! Down distance at: {down_readings:.2}m"')
                    else:
                        print(f'{Style.BRIGHT}{Fore.BLUE}"Down distance at: {down_readings:.2f}m"')
                    await asyncio.sleep(2)
            
        except Exception as e:
            pass  # file might not exist yet
        
        await asyncio.sleep(0.05)

def is_obstacle_down(current_velocity: float):
    # dist_down = get_down_distance()
    # return dist_down is not None and dist_down <= COLLISION_THRESHOLD
    dist = get_down_distance()
    if dist is None:
        return False
    return dist < stopping_distance(current_velocity, "down")