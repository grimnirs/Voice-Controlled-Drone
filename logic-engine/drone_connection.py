import asyncio
from mavsdk import System


async def connect_and_wait_for_ready(address: str):
    drone = System()
    print(f"\nConnecting to MAVLink router at: {address}")
    await drone.connect(system_address=address)
    
    print("Waiting for ArduPilot heartbeat...")
    # Vänta på anslutning
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("\n" + "=" * 40)
            print("✅ CONNECTED TO DRONE MAVLINK!")
            print("=" * 40 + "\n")
            break


    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("✅ DRONE READY")
            break
        print("Waiting for armable state (Health not ready)...")
        await asyncio.sleep(1)
    
    return drone
