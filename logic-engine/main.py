import os
import asyncio
from mavsdk import System
from command_handler import txt_to_cmd, DroneCommand, stop_hover
from drone_connection import connect_and_wait_for_ready
import json
from collision_handler import watch_distance_fwd, watch_distance_up, watch_distance_down

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
command_file = os.path.join(BASE_DIR, 'commands.json')

async def cmd_handler(drone):
    print("> > > Waiting for voice command")
    last_idx = -1

    # Clear stale commands on startup
    with open(command_file, 'w') as f:
        json.dump([], f)
    print("Cleared stale commands from previous run")

    while True:
        if os.path.exists(command_file):
            try:
                with open(command_file, 'r') as f:
                    v_commands = json.load(f)

                if len(v_commands) > last_idx + 1:
                    new_commands = v_commands[last_idx + 1:]
                    last_idx = len(v_commands) - 1
                    for command in new_commands:
                        print(f"> > > New Voice Command: {command}")
                        await txt_to_cmd(drone, command)

            except (json.JSONDecodeError, Exception) as e:
                print(f"Error reading commands: {e}")

        await asyncio.sleep(0.5)

# async def run():
#     address = os.getenv("SITL_ADDRESS", "tcpout://sim:5790")

#     print("Logic Engine Booting Up...")
#     for i in range(20, 0, -1):
#         print(f"Connecting in {i} seconds...")
#         await asyncio.sleep(1)

#     drone = await connect_and_wait_for_ready(address)

#     asyncio.create_task(watch_distance_fwd())
#     asyncio.create_task(watch_distance_up())
#     asyncio.create_task(watch_distance_down())

#     asyncio.ensure_future(print_flight_mode(drone))
#     asyncio.ensure_future(cmd_handler(drone))

#     print("Streaming telemetry (Ctrl+C to stop):\n")
#     async for position in drone.telemetry.position():
#         print(
#             f"  Lat: {position.latitude_deg:11.6f}  "
#             f"Lon: {position.longitude_deg:11.6f}  "
#             f"Alt: {position.relative_altitude_m:6.2f} m",
#             end="\r",
#         )

async def run():
    address = os.getenv("SITL_ADDRESS", "tcpout://sim:5790")

    print("Logic Engine Booting Up...")
    for i in range(20, 0, -1):
        print(f"Connecting in {i} seconds...")
        await asyncio.sleep(1)

    drone = await connect_and_wait_for_ready(address)

    asyncio.create_task(watch_distance_fwd())
    asyncio.create_task(watch_distance_up())
    asyncio.create_task(watch_distance_down())

    asyncio.ensure_future(print_flight_mode(drone))
    asyncio.ensure_future(cmd_handler(drone))

    print("Streaming telemetry (Ctrl+C to stop):\n")
    while True:
        try:
            async for position in drone.telemetry.position():
                print(
                    f"  Lat: {position.latitude_deg:11.6f}  "
                    f"Lon: {position.longitude_deg:11.6f}  "
                    f"Alt: {position.relative_altitude_m:6.2f} m",
                    end="\r",
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"\nTelemetry lost: {e}")
            print("Reconnecting in 3s...")
            await asyncio.sleep(3)

# async def print_flight_mode(drone):
#     async for mode in drone.telemetry.flight_mode():
#         print(f"\n  Flight mode: {mode}")

async def print_flight_mode(drone):
    while True:
        try:
            async for mode in drone.telemetry.flight_mode():
                print(f"  Flight mode: {mode}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Flight mode stream lost: {e}")
            await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nDisconnected.")