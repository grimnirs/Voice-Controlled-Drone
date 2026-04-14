import asyncio
from mavsdk.offboard import VelocityNedYaw

async def txt_to_cmd(drone, text: str):
    command = text.lower().strip()
    if "arm" in command:
        await drone.action.arm()
    
    elif "takeoff" in command:
        try: 
            await drone.action.set_takeoff_altitude(3.0)

            print("Arming...")
            try:
                await drone.action.arm()
            except Exception as e:
                print(f"Failed: {e}")
                raise e
            print("Successfully armed!")

            await asyncio.sleep(5)

            print("Taking off...")
            await drone.action.takeoff()
            print("Successfully took off!")

        except Exception as e:
            print(f"Failed: {e}")
            return 
        
    elif "land" in command: 
        await drone.action.land()

    elif "fly forward north" in command:
        try:
            await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
        
            try: 
                await drone.offboard.start()
            except Exception as e:
                print(f"Offboard FAILED: {e}")
                raise e
        
            await drone.offboard.set_velocity_ned(VelocityNedYaw(3.0, 0.0, 0.0, 0.0))

            await asyncio.sleep(10)
        
            await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
            await drone.offboard.stop()

        except Exception as e:
            print(f"Failed flying forward: {e}")
            return
    
    else:
        print("Unknown command", {command})
    
