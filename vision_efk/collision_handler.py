import shared_variables
from mavsdk import System
import os
from pymavlink import mavutil
import time
import asyncio

drone = System()

addr = os.getenv("PYMAVLINK_ADDRESS", "udpout:sim:14552")
master = mavutil.mavlink_connection(addr)

async def watch_distance(drone):
    print("Starting distance sensor...")
    try:
        async for distance in drone.telemetry.distance_sensor():  
            shared_variables.avoid_collision_forward = False
            shared_variables.avoid_collision_up = False

            dist_val = distance.current_distance_m
            
            print(f"Orientation<: {distance.orientation}")
            orientation_deg = distance.orientation.pitch_deg

            # RAW DEBUG — remove once sensors confirmed working
            print(f"RAW SENSOR: pitch={orientation_deg:.1f}° dist={dist_val:.2f}m")

            # Guard against uninitialized sensor reads (0.0 is almost certainly bad data)
            if dist_val <= 0.0:
                print(f"  -> Skipping invalid reading (dist=0.0)")
                continue
            
            if abs(orientation_deg - 0) < 5: 
                shared_variables.latest_distance_forward = dist_val
                shared_variables.avoid_collision_forward = (dist_val <= 1.0)
                print(f"SENSORDATA (fwd): {dist_val:.2f}m | collision={shared_variables.avoid_collision_forward}")


            elif abs(orientation_deg - 270) < 5:
                shared_variables.latest_distance_up = dist_val
                shared_variables.avoid_collision_up = (dist_val <= 1.0)
                print(f"SENSORDATA (up):  {dist_val:.2f}m | collision={shared_variables.avoid_collision_up}")

            elif abs(orientation_deg - 90) < 5:    # Down (RNGFND1, orient=25 → pitch 90°)
                shared_variables.latest_distance_down = dist_val

            else:
                print(f"  -> Unknown orientation pitch={orientation_deg:.1f}°, skipping")

    except Exception as e:
        print(f"Sensor-error: {e}")







