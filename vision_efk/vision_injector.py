import asyncio
import os
from mavsdk import System
from mavsdk.mocap import VisionPositionEstimate, Quaternion, PositionBody, AngleBody

async def run():
    drone = System()
    # Vi använder tcpout mot sim:5760 för att matcha din docker-compose
    address = os.getenv("SITL_ADDRESS", "tcpin://sim:5790")
    print(f"Vision Injector: Försöker ansluta till {address}...")

    # --- Stabil anslutningsloop (Retry) ---
    connected = False
    while not connected:
        try:
            await drone.connect(system_address=address)
            print("Vision Injector: Väntar på att simulatorn ska svara...")
            
            # Kolla om vi faktiskt får kontakt
            async for state in drone.core.connection_state():
                if state.is_connected:
                    print("Vision Injector: Connected!")
                    connected = True
                    break
        except Exception as e:
            print(f"Vision Injector: Anslutning misslyckades: {e}. Försöker igen om 2s...")
            await asyncio.sleep(2)

    print("Vision Injector: Startar injection loop (20Hz)...")
    
    # --- Injection Loop ---
    # Vi hämtar Ground Truth från telemetrin och skickar tillbaka som Vision
    async for nav in drone.telemetry.position_velocity_ned():
        try:
            vpe = VisionPositionEstimate(
                0, # Timestamp 0 låter ArduPilot sätta tiden själv
                PositionBody(
                    nav.position.north_m,
                    nav.position.east_m,
                    nav.position.down_m
                ),
                AngleBody(0.0, 0.0, 0.0), 
                Quaternion(1.0, 0.0, 0.0, 0.0),
                [0.05, 0.05, 0.05] # Varians (lågt värde = hög tillit)
            )

            await drone.mocap.set_vision_position_estimate(vpe)
            
        except Exception as e:
            print(f"Injection Error: {e}")
        
        await asyncio.sleep(0.05) # 20Hz

if __name__ == "__main__":
    asyncio.run(run())