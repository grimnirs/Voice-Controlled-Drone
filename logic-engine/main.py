"""
Logic Engine — Connection Test Stub

Connects to ArduPilot SITL via MAVSDK through mavlink-router.
mavlink-router pushes MAVLink over UDP to this container on port 14540.

This can now run simultaneously with QGC — no more fighting
over a single TCP port.

Usage:
    docker compose up    # starts both sim and logic-engine together
"""

import shared_variables
import os
import asyncio
from mavsdk import System
from command_handler import txt_to_cmd, DroneCommand


latest_distance = 100.0 # Global variabel

# async def watch_distance(drone):
#     global latest_distance
#     print("Startar avståndssensor...")
#     try:
#         async for distance in drone.telemetry.distance_sensor():
#             # MAVSDK använder .current_distance_m
#             latest_distance = distance.current_distance_m
#             if latest_distance < 2.0:
#                 print(f"SENSORDATA: Hinder på {latest_distance:.2f}m")
#     except Exception as e:
#         print(f"Sensor-error: {e}")

async def run():
    address = os.getenv("SITL_ADDRESS", "tcpout://sim:5790")

    print("Logic Engine Booting Up...")

    for i in range(20, 0, -1):
        print(f"Connecting in {i} seconds...")
        await asyncio.sleep(1)

    drone = System()
    print(f"\nConnecting to MAVLink router at: {address}")
    await drone.connect(system_address=address)
    print("Waiting for ArduPilot heartbeat...")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("\n" + "=" * 40)
            print("✅ CONNECTED TO DRONE MAVLINK!")
            print("=" * 40 + "\n")
            break

    async def wait_until_ready(drone):
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("Drone ready!")
                break
    
    await wait_until_ready(drone)

    async def odometry_watcher(drone):
        async for odom in drone.telemetry.odometry():
            shared_variables.latest_odom = odom
    
    asyncio.create_task(odometry_watcher(drone))

    arm_cmd: DroneCommand = {
        "action": "arm"
    }
    
    takeoff_cmd: DroneCommand = {
        "action": "takeoff"
    }

    fly_cmd: DroneCommand = {
        "action": "fly",
        "direction": "forward",
        "integer": 10,
        "unit": "meters"
    }  
    
    async def cmd_handler(drone):
        # asyncio.create_task(watch_distance(drone))
        # await asyncio.sleep(40)
        print("Arming...")
        await txt_to_cmd(drone, arm_cmd)
        await asyncio.sleep(15) 

        # Lyft (bara en gång)
        print("Taking off...")
        await txt_to_cmd(drone, takeoff_cmd)
        
        # Vänta tills den nått höjd
        await asyncio.sleep(15) 
        
        # Flyg framåt
        print("Flying...")
        await txt_to_cmd(drone, fly_cmd)

        await asyncio.sleep(15)
        
        # # Landa efter flygningen
        # await asyncio.sleep(5)
        # print("Uppdrag slutfört, landar...")
        # await txt_to_cmd(drone, "land")
            
    # Print flight mode changes
    #asyncio.create_task(optical_flow_watcher())
    asyncio.ensure_future(print_flight_mode(drone))
    asyncio.ensure_future(cmd_handler(drone))
    #await cmd_handler(drone)

    # Stream position telemetry
    print("Streaming telemetry (Ctrl+C to stop):\n")
    async for position in drone.telemetry.position():
        print(
            f"  Lat: {position.latitude_deg:11.6f}  "
            f"Lon: {position.longitude_deg:11.6f}  "
            f"Alt: {position.relative_altitude_m:6.2f} m",
            end="\r",
        )
# async def optical_flow_watcher():
#     print("Starting optical flow listener...")

#     master = mavutil.mavlink_connection("udpin:0.0.0.0:14552")

#     # Non-blocking heartbeat wait
#     while True:
#         msg = master.recv_match(type="HEARTBEAT", blocking=False)
#         if msg:
#             print("Optical flow connected!")
#             break
#         await asyncio.sleep(0.1)

#     while True:
#         msg = master.recv_match(
#             type=["OPTICAL_FLOW", "OPTICAL_FLOW_RAD"],
#             blocking=False
#         )

#         if msg:
#             flow_x = getattr(msg, "flow_x", None)
#             flow_y = getattr(msg, "flow_y", None)

#             print(f"\nOPTICAL FLOW → X: {flow_x}, Y: {flow_y}")

#         await asyncio.sleep(0.01)


async def print_flight_mode(drone):
    async for mode in drone.telemetry.flight_mode():
        print(f"\n  Flight mode: {mode}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nDisconnected.")