from shared_variables import latest_distance, avoid_collision

async def watch_distance(drone):
    global latest_distance
    print("Starting distance sensor...")
    try:
        async for distance in drone.telemetry.distance_sensor():
            avoid_collision = False
            print(f"SENSORDATA: Obstacle at: {latest_distance:.2f}m")

            if distance.orientation == 0:
                latest_distance = distance.current_distance_m

                if latest_distance <= 1.0: 
                    avoid_collision = True

    except Exception as e:
        print(f"Sensor-error: {e}")