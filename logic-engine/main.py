"""
Logic Engine — Connection Test Stub

Connects to ArduPilot SITL via MAVSDK through mavlink-router.
mavlink-router pushes MAVLink over UDP to this container on port 14540.

This can now run simultaneously with QGC — no more fighting
over a single TCP port.

Usage:
    docker compose up    # starts both sim and logic-engine together
"""
import asyncio
import os
from mavsdk import System


async def run():
    address = os.getenv("SITL_ADDRESS", "tcpout://sim:5790")

    print("Logic Engine Booting Up...")
    print("Waiting 20 seconds for Gazebo + ArduPilot + MAVLink Router...")

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

    # Print flight mode changes
    asyncio.ensure_future(print_flight_mode(drone))

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