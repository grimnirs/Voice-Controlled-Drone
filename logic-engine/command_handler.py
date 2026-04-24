
from mavsdk.offboard import VelocityBodyYawspeed
import math
from typing import TypedDict, Optional
import asyncio
 

class DroneCommand(TypedDict, total=False):
        action: str
        direction: Optional[str]
        integer: Optional[int]
        unit: Optional[str]

ACTIONS = {
    "arm":str,
    "start":str,
    "takeoff":str,
    "land":str,
    "fly":str,
}

#NED - North, East, Down
DIRECTIONS = {
    "forward":              (1, 0, 0, 0),   # om problem ändra till (1, 0, 0)
    "backward":             (-1, 0, 0, 0),  
    "right":                (0, 1, 0, 0),   
    "left":                 (0, -1, 0, 0),   
    "up":                   (0, 0, -1, 0), 
    "down":                 (0, 0, 1, 0),  
    "clockwise":            (0, 0, 0, 1),
    "counter-clockwise":    (0, 0, 0, -1)
}

async def cmd_arm(drone, command: DroneCommand):
    # --- Health check START ---
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print(f"Drone is armable!")
            break
        else:
            print("Health not ready...")
            await asyncio.sleep(2)

    print("-- Arming motors --")
    while True:
        try:
            await drone.action.arm()
            break
        except Exception as e:
            print(f"Arming failed: {e}")
            await asyncio.sleep(3)

async def cmd_takeoff(drone, command: DroneCommand):
    async for is_armed in drone.telemetry.armed():
        if not is_armed:
            print("Drone not armed")
            return
        break

    print("-- Takeoff --")
    try:
        await drone.action.set_takeoff_altitude(3.0)
        await drone.action.takeoff()
        print("Airborne!")
        await asyncio.sleep(8)  # wait for drone to reach 3m
    except Exception as e:
        print(f"Takeoff failed: {e}")

async def cmd_land(drone, command: DroneCommand):
    print("-- Landing --")
    while True:
        try:
            await drone.action.land()
        except Exception as e:
            print(f"Landing failed: {e}")
            return

async def cmd_fly(drone, command:DroneCommand):
    async for in_air in drone.telemetry.in_air():
        if not in_air:
            print("Action denied! Drone not in air!")
            return
        break
    
    print("-- Initializing movement sequence --")
    
    direction_key = command.get("direction")
    integer = float(command.get("integer")) 
    unit = command.get("unit")
    velocity = 3 
    duration = integer / velocity
    
    if direction_key is None or integer is None or unit is None:
        print(f"Action requires direction, integer and unit!") 
        return 
    
    if direction_key not in DIRECTIONS:
        print("Direction not found")
        return
  
    direction_vector = DIRECTIONS.get(direction_key)

    fwd = direction_vector[0] * velocity
    right = direction_vector[1] * velocity
    down = direction_vector[2] * velocity

    try:
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()

        start = asyncio.get_event_loop().time()   
        while asyncio.get_event_loop().time() - start < duration: 
            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(fwd, right, down, 0.0))
            await asyncio.sleep(0.1)

        # Stop after duration
        while True:
            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
            await asyncio.sleep(1)
            #await drone.action.hold()
            print("Flight complete!")

    except Exception as e:
        print(f"Failed to fly: {e}")
 

async def cmd_rotate(drone, command: DroneCommand):
    #if avoid_collision:
        #return # what should happen when stopping?
    
    rotation = command.get("direction")

    if rotation is None:
        print(f"Action requires rotation!") 
        return 
    
    if rotation not in DIRECTIONS:
        print("Direction not found")
        return
    
    degree = 45.0
    speed = 30.0
    target_heading = 0.0
    direction_mult = 0.0
    current_heading = 0.0
    duration = 1

    start_yaw = 0.0
    async for heading in drone.telemetry.heading():
        start_yaw = heading.heading_deg
        break
        
    if rotation == "clockwise":
        target_heading = (start_yaw + degree) % 360
        direction_mult = 1
    elif rotation == "counter-clockwise":
        target_heading = (start_yaw - degree) % 360
        direction_mult = -1
    else: 
        print(f"Not a valid rotation")
        return

    try: 
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()    

        while True:
            async for h in drone.telemetry.heading():
                current_heading = h.heading_deg
                break
        
            diff_from_target_degree = (target_heading - current_heading + 180) % 360 - 180

            if abs(diff_from_target_degree) < 1.0:
                break 

            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, (direction_mult * speed)))
            await asyncio.sleep(duration)

        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        await asyncio.sleep(duration)
        #await drone.action.hold()
        print("Rotation complete")
        
    except Exception as e:
        print(f"Failed to rotate: {e}")

async def cmd_stop(drone, command: DroneCommand):
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
    await asyncio.sleep(1)
    await drone.offboard.stop()

async def txt_to_cmd(drone, command: DroneCommand):
    action = command.get("action") 
    if action is None or  action not in ACTIONS:
        print(f"Unknown action '{action}'")
    
    elif action == "arm" or action == "start":
        await cmd_arm(drone, command)

    elif action == "takeoff":
       await cmd_takeoff(drone, command)

    elif action == "fly":
        await cmd_fly(drone, command)

    elif action == "land":
        await cmd_land(drone, command)

    elif action == "rotate":
        await cmd_rotate(drone, command)
    
    elif action == "stop":
        await cmd_stop(drone, command)

    else:
        print("Unknown command", {command})
    
