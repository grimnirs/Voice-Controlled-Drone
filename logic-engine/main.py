"""
Logic Engine — Connection Test Stub

Connects to ArduPilot SITL via MAVSDK through mavlink-router.
mavlink-router pushes MAVLink over UDP to this container on port 14540.

This can now run simultaneously with QGC — no more fighting
over a single TCP port.

Usage:
    docker compose up    # starts both sim and logic-engine together
"""

import os
import asyncio
from mavsdk import System
from command_handler import txt_to_cmd, DroneCommand, stop_hover
from drone_connection import connect_and_wait_for_ready
import json
#import sounddevice as sd
#import whisper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
command_file = os.path.join(BASE_DIR, 'commands.json')

# latest_distance = 100.0 # Global variable

# async def watch_distance(drone):
#     global latest_distance
#     print("Startar avståndssensor...")
#     try:
#         async for distance in drone.telemetry.distance_sensor():
#             latest_distance = distance.current_distance_m
#             if latest_distance < 2.0:
#                 print(f"SENSORDATA: Hinder på {latest_distance:.2f}m")
#     except Exception as e:
#         print(f"Sensor-error: {e}")

async def run():
    address = os.getenv("SITL_ADDRESS", "tcpout://sim:5790")

    print("Logic Engine Booting Up...")

    for i in range(30, 0, -1):
        print(f"Connecting in {i} seconds...")
        await asyncio.sleep(1)

    drone = await connect_and_wait_for_ready(address)



    # arm_cmd: DroneCommand = {
    #     "action": "arm"
    # }
    
    # takeoff_cmd: DroneCommand = {
    #     "action": "takeoff"
    # }

    # fly_cmd: DroneCommand = {
    #     "action": "fly",
    #     "direction": "forward",
    #     "integer": 10,
    #     "unit": "meters"
    # }  

    # fly_cmd_right: DroneCommand = {
    #     "action": "fly",
    #     "direction": "right",
    #     "integer": 10,
    #     "unit": "meters"
    # }

    # fly_cmd_left: DroneCommand = {
    #     "action": "fly",
    #     "direction": "left",
    #     "integer": 10,
    #     "unit": "meters"
    # }

    # rotate_clockwise_cmd: DroneCommand = {
    #     "action": "rotate",
    #     "direction": "clockwise",
    # }

    # rotate_counter_clockwise_cmd: DroneCommand = {
    #     "action": "rotate",
    #     "direction": "counter-clockwise",
    # }

    #command_file = 'commands.json'

    async def cmd_handler(drone):
        print("> > > Waiting for voice command")
        last_idx = -1
        
        last_idx = -1
    if os.path.exists(command_file):
        with open(command_file, 'r') as f:
            existing = json.load(f)
        last_idx = len(existing) - 1  # skip all old commands
        print(f"Skipping {last_idx + 1} stale commands from previous run")

        while True:
            if os.path.exists(command_file):
                try:
                    with open(command_file, 'r') as f:
                        v_commands = json.load(f)
                    
                    if len(v_commands) > 0 and (len(v_commands) - 1) > last_idx:
                        latest_command = v_commands[-1]
                        last_idx = len(v_commands) - 1
                        print(f"> > > New Voice Command: {latest_command}")
                    
                        await txt_to_cmd(drone, latest_command)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Error reading commands: {e}")
            await asyncio.sleep(0.5)

    await asyncio.sleep(15)
        # print("Arming...")
        # await txt_to_cmd(drone, arm_cmd)
        # await asyncio.sleep(3) 

        # # Lyft (bara en gång)
        # print("Taking off...")
        # await txt_to_cmd(drone, takeoff_cmd)
        # await asyncio.sleep(3) 
        
        # # Flyg framåt
        # print("Flying...")
        # await txt_to_cmd(drone, fly_cmd)
        # await asyncio.sleep(3)

        # # Rotate
        # print("Rotating...")
        # await txt_to_cmd(drone, rotate_counter_clockwise_cmd)
        # await asyncio.sleep(3)

        # print("Flying...")
        # await txt_to_cmd(drone, fly_cmd)
        # await asyncio.sleep(3)
            
    # Print flight mode changes
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

async def print_flight_mode(drone):
    async for mode in drone.telemetry.flight_mode():
        print(f"\n  Flight mode: {mode}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nDisconnected.")