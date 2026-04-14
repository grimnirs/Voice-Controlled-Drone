import shared_variables
from mavsdk.offboard import VelocityBodyYawspeed
import math
from typing import TypedDict, Optional
import asyncio
from state.machine import DroneState
 
# TODO

# 1. Make better command handler
# 2. Make move function work better, ex fly 10 m (now it doesn't have time and fly only 3)
# 3. Integrate in main with VTT
# 4. Make velocity function (utökning om vi har tid sen)

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
    "rotate":str,
    "stop":str,
}

# Commands that trigger a state transition when they succeed.
# Commands NOT in this dict are in-state actions (checked with can_execute).
COMMAND_TO_STATE = {
    "arm":     DroneState.ARMED,
    "takeoff": DroneState.AIRBORNE,
    "land":    DroneState.LANDING,
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
        #if health.is_global_position_ok and health.is_home_position_ok:
        if health.is_armable:
            #print("Drone Health ok!")
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
    except Exception as e:
        print(f"Takeoff failed: {e}")
        return

async def cmd_land(drone, command: DroneCommand):
    print("-- Landing --")
    while True:
        try:
            await drone.action.land()
        except Exception as e:
            print(f"Landing failed: {e}")
            return

async def cmd_fly(drone, command:DroneCommand):
    print("-- Initializing movement sequence --")
    direction_key = command.get("direction")
    integer = float(command.get("integer")) 
    unit = command.get("unit")

    velocity = 3 # make a set_velocity func or have velocity as a parameter in the command handler
    # time = integer / velocity

    if direction_key is None or integer is None or unit is None:
        print(f"Action requires direction, integer and unit!") 
        return 
    
    if direction_key not in DIRECTIONS:
        print("Direction not found")
        return
    
    # drone_odometry = drone.telemetry.odometry()

    # async for drone_odom in drone_odometry:
    #     start_x = drone_odom.position_body.x_m
    #     start_y = drone_odom.position_body.y_m
    #     start_z = drone_odom.position_body.z_m
    #     break

    # try:
    #     start_pos = await anext(drone_odometry)
    # except Exception as e:
    #     print(f"Failed to get odometry!: {e}")
    #     start_pos = await anext(drone.telemetry.posititon())

    # DEBUG PRINT
    print(f"DEBUG: checking odom... Current value: {shared_variables.latest_odom}")

    # Om den är None, vänta, men printa varje sekund så vi ser om den ändras
    timeout_counter = 0
    while shared_variables.latest_odom is None:
        if timeout_counter % 10 == 0: # Varje sekund
            print("Still waiting for odom data from shared_variables...")
        await asyncio.sleep(0.1)
        timeout_counter += 1
        if timeout_counter > 50: # Efter 5 sekunder, ge upp
            print("TIMEOUT: Never received odom. Check if odometry_watcher is running!")
            return

    while shared_variables.latest_odom is None:
        await asyncio.sleep(0.1)
    start_pos = shared_variables.latest_odom

    start_y = start_pos.position_body.y_m
    start_z = start_pos.position_body.z_m
    start_x = start_pos.position_body.x_m
    
    direction_vector = DIRECTIONS.get(direction_key)

    fwd = direction_vector[0] * velocity
    right = direction_vector[1] * velocity
    down = direction_vector[2] * velocity

    try: 
        await drone.offboard.start()  
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        # await drone.offboard.set_velocity_body(VelocityBodyYawspeed(fwd, right, down, 0.0))

        distance_traveled = 0.0
        # async for current_pos in drone_odometry:
        while distance_traveled < integer:
            print(f"Distance travelled: {distance_traveled}") # fel-sök bara
            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(fwd, right, down, 0.0))

            if shared_variables.latest_odom is None:
                print("No odometry yet!")
                await asyncio.sleep(0.05)
                continue

            #current_pos = await anext(drone_odometry)
            current_pos = shared_variables.latest_odom
            current_x = current_pos.position_body.x_m
            current_y = current_pos.position_body.y_m
            current_z = current_pos.position_body.z_m
            distance_traveled = math.sqrt((current_x - start_x)**2 + 
                                          (current_y - start_y)**2 + 
                                          (current_z - start_z)**2)
            print(f"Dist: {distance_traveled:.2f} | x:{current_x:.2f} y:{current_y:.2f}")
            
            await asyncio.sleep(0.05)
    
    except Exception as e:
        print(f"Failed to fly: {e}")

    finally:
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        await asyncio.sleep(1)
        await drone.offboard.stop()
        #print("Move complete")
        print("Reached end of cmd_fly code!")  

async def cmd_rotate(drone, command: DroneCommand):
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
        print("Rotation complete")
        
    except Exception as e:
        print(f"Failed to rotate: {e}")

async def cmd_stop(drone, command: DroneCommand):
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
    await asyncio.sleep(1)
    await drone.offboard.stop()

async def txt_to_cmd(drone, command: DroneCommand):
    action = command.get("action")

    # Normalize aliases before any permission check so ALLOWED_COMMANDS
    # and COMMAND_TO_STATE only need to know the canonical name.
    if action == "start":
        action = "arm"

    if action is None or action not in ACTIONS:
        print(f"[CMD] Unknown action '{action}'")
        return

    sm = shared_variables.sm
    target = COMMAND_TO_STATE.get(action)

    # --- GATE ---
    # State-changing command: check if the transition is allowed.
    # In-state command: check if the action is allowed in the current state.
    if target is not None:
        if not sm.can_transition(target):
            print(f"[STATE] Rejected '{action}': drone is {sm.get_state().value}")
            return
    else:
        if not sm.can_execute(action):
            print(f"[STATE] Rejected '{action}': drone is {sm.get_state().value}")
            return

    # --- DISPATCH ---
    if action == "arm":
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

    # --- COMMIT TRANSITION ON SUCCESS ---
    # Only reached if dispatch returned without raising. State transitions
    # happen AFTER the MAVSDK call so a failed command leaves state untouched.
    if target is not None:
        sm.transition(target)
        print(f"[STATE] → {sm.get_state().value}")

