"""
Logic Engine — Connection Test Stub

Connects to ArduPilot SITL via MAVSDK and prints live telemetry.
This validates that the Logic Engine container can communicate
with the simulation container over the Docker network.

Usage:
    docker compose up sim              # start simulation first
    docker compose run logic-engine    # then run this
"""
import asyncio
import os
from mavsdk import System

async def run():
    sitl_address = os.getenv("SITL_ADDRESS", "tcpout://sim:5760")
    sitl_address = sitl_address.replace("tcp://", "tcpout://")

    print("Logic Engine Booting Up...")
    print("Waiting 15 seconds for the Simulator and ArduPilot to fully load...")
    
    # Tvinga Python att vänta tills simulatorn är redo
    for i in range(15, 0, -1):
        print(f"Connecting in {i} seconds...")
        await asyncio.sleep(1)

    drone = System()
    print(f"\nTargeting MAVLink address: {sitl_address}")
    print("Attempting to connect to the simulator...")
    
    # Nu är porten öppen, så vi ansluter!
    await drone.connect(system_address=sitl_address)
    print("Socket opened. Waiting for ArduPilot heartbeat...")

    # Vänta på det officiella "handslaget"
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("\n" + "="*40)
            print("✅ CONNECTED TO DRONE MAVLINK!")
            print("="*40 + "\n")
            break # Bryt loopen när vi är anslutna

    # --- Håll skriptet igång ---
    print("Logic Engine successfully bridged to Simulation! Standing by for commands.")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run())