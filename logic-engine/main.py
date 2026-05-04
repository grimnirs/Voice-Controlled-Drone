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
import json
import asyncio
from mavsdk import System
from command_handler import txt_to_cmd, DroneCommand
from vision_efk.collision_handler import watch_distance 


async def run():
    address = os.getenv("SITL_ADDRESS", "tcpout://sim:5790")

    print("Logic Engine Booting Up...")

    for i in range(30, 0, -1):
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

    asyncio.create_task(watch_distance(drone))

    command_file = 'commands.json'
    
    async def cmd_handler(drone):
        print("> > > Waiting for voice command")
        last_idx = -1

        while True:
            if os.path.exists(command_file):
                try:
                    v_commands = []
                    # 1. Open in 'read and write' mode to lock briefly
                    with open(command_file, 'r+') as f:
                        v_commands = json.load(f)
                        
                        if v_commands:
                            # 2. Clear the file immediately after reading
                            f.seek(0)
                            f.truncate()
                            json.dump([], f) 
                            print("> > > Commands cleared from file.")

                    # 3. Process the commands we just grabbed
                    for command in v_commands:
                        print(f"> > > Processing Voice Command: {command}")
                        await txt_to_cmd(drone, command)

                except json.JSONDecodeError:
                    # This happens if the file is being written to at the exact same time
                    pass 
                except Exception as e:
                    print(f"Error handling commands: {e}")
            await asyncio.sleep(0.5)

    await asyncio.sleep(15)
        
        # # Landa efter flygningen
        # await asyncio.sleep(5)
        # print("Uppdrag slutfört, landar...")
        # await txt_to_cmd(drone, "land")
            
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