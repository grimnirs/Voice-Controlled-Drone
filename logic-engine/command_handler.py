<<<<<<< HEAD
import shared_variables
=======
>>>>>>> origin/erika_testing
from mavsdk.offboard import VelocityBodyYawspeed
import math
from typing import TypedDict, Optional
import asyncio
from collision_handler import is_obstacle_forward, get_forward_distance
 
_hover_task: Optional[asyncio.Task] = None

class DroneCommand(TypedDict, total=False):
        action: str
        direction: Optional[str]
        integer: Optional[int]
        unit: Optional[str]
 
ACTIONS = {
    "arm":str,
    "start":str,
    "take off":str,
    "land":str,
    "fly":str,
    "rotate":str,
    "stop":str,
<<<<<<< HEAD
}

# Commands that trigger a state transition when they succeed.
# Commands NOT in this dict are in-state actions (checked with can_execute).
COMMAND_TO_STATE = {
    "arm":     DroneState.ARMED,
    "takeoff": DroneState.AIRBORNE,
    "land":    DroneState.LANDING,
=======
    "stop_hover":str,
>>>>>>> origin/erika_testing
}

#NED - North, East, Down
DIRECTIONS = {
    "forward":              (1, 0, 0, 0),   # om problem Ãndra till (1, 0, 0)
    "backward":             (-1, 0, 0, 0),  
    "right":                (0, 1, 0, 0),   
    "left":                 (0, -1, 0, 0),   
    "up":                   (0, 0, -1, 0), 
    "down":                 (0, 0, 1, 0),  
    "clockwise":            (0, 0, 0, 1),
    "counter clockwise":    (0, 0, 0, -1)
}

async def cmd_arm(drone, command: DroneCommand):
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("Drone is armable!")
            break
        else:
            print("Health not ready...")
            await asyncio.sleep(2)

    print("-- Arming motors --")
    while True:
        try:
            await drone.action.arm()
            print("✅ Armed!")
            break
        except Exception as e:
            print(f"Arming failed: {e}")
            await asyncio.sleep(3)


async def cmd_takeoff(drone, command: DroneCommand):
    print("-- Waiting for armed state --")
    async for is_armed in drone.telemetry.armed():
        if is_armed:
            print("Drone is armed, taking off!")
            break
        else:
            print("Waiting for arm...")
            await asyncio.sleep(1)

    print("-- Takeoff --")
    try:
        await drone.action.set_takeoff_altitude(3.0)
        await drone.action.takeoff()
        print("Airborne!")
        await asyncio.sleep(8)
    except Exception as e:
        print(f"Takeoff failed: {e}")


async def cmd_land(drone, command: DroneCommand):
    print("-- Landing --")
    try:
        await drone.action.land()
    except Exception as e:
        print(f"Landing failed: {e}")
        return


async def hold_position(drone):
    """Continuously sends zero velocity to hold position in offboard mode."""
    try:
        while True:
            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass  


async def start_hover(drone):
    global _hover_task
    await stop_hover()  
    _hover_task = asyncio.create_task(hold_position(drone))


async def stop_hover():
    global _hover_task
    if _hover_task and not _hover_task.done():
        _hover_task.cancel()
        await asyncio.sleep(0.05) 


async def get_local_xyz_m(drone):
    async for pos_vel in drone.telemetry.position_velocity_ned():
        return (pos_vel.position.north_m,
                pos_vel.position.east_m,
                pos_vel.position.down_m)
    return None


async def cmd_fly(drone, command:DroneCommand):
    await stop_hover()

    async for in_air in drone.telemetry.in_air():
        if not in_air:
            print("Action denied! Drone not in air!")
            return
        break
    
    print("-- Initializing movement sequence --")
    
    direction_key = command.get("direction")
    integer = float(command.get("integer")) 
    unit = command.get("unit")
    velocity = 2  
    MIN_ALTITUDE = 0.5
    MAX_ALTITUDE = 10.0
    
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

    start_xyz = await get_local_xyz_m(drone)
    current_altitude = -start_xyz[2]
    
    try:
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start() 

        while True: 
            if direction_key == "forward" and is_obstacle_forward():
                print(f"EMERGENCY STOPPING! Drone is {get_forward_distance():.2f}m from an obstacle!")
                break
            
            current_xyz = await get_local_xyz_m(drone)
            if current_xyz is not None:
                if command.get("direction") == "up":
                    travelled = abs(current_xyz[2] - start_xyz[2])

                elif command.get("direction") == "down":
                    travelled = abs(current_xyz[2] - start_xyz[2])
                
                else:
                    travelled = math.sqrt(
                        (current_xyz[0] - start_xyz[0]) ** 2 +
                        (current_xyz[1] - start_xyz[1]) ** 2 
                    )
            if travelled >= (integer - velocity):
                break

            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(fwd, right, down, 0.0))
            await asyncio.sleep(0.1)

        # Hold hover briefly, then return so next command can run.
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        await asyncio.sleep(0.5)
        print("Flight complete!")
        await start_hover(drone)
        return
            
    except Exception as e:
        print(f"Failed to fly: {e}")

async def cmd_rotate(drone, command: DroneCommand):
    await stop_hover()
    
    rotation = command.get("direction")

    if rotation is None:
        print(f"Action requires rotation!") 
        return 
    
    if rotation not in DIRECTIONS:
        print("Direction not found")
        return
    
    degree = 90.0
    speed = 20.0
    target_heading = 0.0
    direction_mult = 0.0
    current_heading = 0.0

    start_yaw = 0.0

    async for heading in drone.telemetry.heading():
        start_yaw = heading.heading_deg
        break
        
    if rotation == "clockwise":
        target_heading = (start_yaw + degree) % 360
        direction_mult = 1
    elif rotation == "counter clockwise":
        target_heading = (start_yaw - degree) % 360
        direction_mult = -1
    else: 
        print(f"Not a valid rotation")
        return

    try: 
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()    
     
        async for h in drone.telemetry.heading():
            current_heading = h.heading_deg
        
            diff_from_target_degree = (target_heading - current_heading + 180) % 360 - 180

            if abs(diff_from_target_degree) < 5.0:  # helst 2 men 5 om datorn är långsam när testerna körs
                print(f"Target reached at {current_heading:.1f}!")
                break

            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, (direction_mult * speed)))
            await asyncio.sleep(0.05)

        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        await asyncio.sleep(0.05)
        print(f"Rotation complete, diff from target degree: {diff_from_target_degree}")
        await start_hover(drone)
        return
        
    except Exception as e:
        print(f"Failed to rotate: {e}")

async def cmd_stop(drone, command: DroneCommand):
    await stop_hover()
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
    await asyncio.sleep(1)
    await drone.offboard.stop()

async def cmd_stop_hover(drone, command: DroneCommand):
    await stop_hover()
    print("Hover stopped")

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

    elif action == "take off":
       await cmd_takeoff(drone, command)

    elif action == "fly":
        await cmd_fly(drone, command)
    elif action == "land":
        await cmd_land(drone, command)
    elif action == "rotate":
        await cmd_rotate(drone, command)
    elif action == "stop":
        await cmd_stop(drone, command)

<<<<<<< HEAD
    # --- COMMIT TRANSITION ON SUCCESS ---
    # Only reached if dispatch returned without raising. State transitions
    # happen AFTER the MAVSDK call so a failed command leaves state untouched.
    if target is not None:
        sm.transition(target)
        print(f"[STATE] → {sm.get_state().value}")

=======
    elif action == "stop_hover":
        await cmd_stop_hover(drone, command)

    else:
        print("Unknown command", {command})
        return