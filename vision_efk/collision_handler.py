import shared_variables
from mavsdk import System
import os
from pymavlink import mavutil
import time
import asyncio

drone = System()

#addr = os.getenv("SITL_ADDRESS", "udpin:0.0.0.0:14552")
addr = os.getenv("PYMAVLINK_ADDRESS", "udpout:sim:14552")
master = mavutil.mavlink_connection(addr)

async def watch_distance(drone):
    print("Starting distance sensor...")
    asyncio.create_task(send_sensor_data())
    try:
        async for distance in drone.telemetry.distance_sensor():  
            shared_variables.avoid_collision_forward = False
            shared_variables.avoid_collision_up = False

            # if distance.current_distance_m < 0.05:
            #     continue
            
            print(f"Orientation<: {distance.orientation}")
            orientation_deg = distance.orientation.pitch_deg
            
            if abs(orientation_deg - 0) < 5: 
                shared_variables.latest_distance_forward = distance.current_distance_m
                print(f"SENSORDATA: Obstacle at (forward): {shared_variables.latest_distance_forward}m")
                shared_variables.avoid_collision_forward = (distance.current_distance_m <= 1.0)

            elif abs(orientation_deg - 270) < 5:
                shared_variables.latest_distance_up = distance.current_distance_m
                print(f"SENSORDATA: Obstacle at (up): {shared_variables.latest_distance_up}m")
                shared_variables.avoid_collision_up = (distance.current_distance_m <= 1.0)

            else:
                print("Failed orientation check forward and up!")

    except Exception as e:
        print(f"Sensor-error: {e}")


async def send_sensor_data():
    while True:
        try: 
            dist_fwd = shared_variables.latest_distance_forward if shared_variables.latest_distance_forward is not None else 2.0
            dist_up = shared_variables.latest_distance_up if shared_variables.latest_distance_up is not None else 2.0

            master.mav.distance_sensor_send(
                0, 5, 4000, 
                int(dist_up * 100), 
                10, 1, 24, 0
            )

            master.mav.distance_sensor_send(
                0, 5, 4000, 
                int(dist_fwd * 100), 
                10, 0, 0, 0  
            )

        except Exception as e:
            print(f"Couldn't send sensor data {e}")
        
        await asyncio.sleep(0.1)




