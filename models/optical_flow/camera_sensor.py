from pymavlink import mavutil
import time
import math
import os
import json

position_x = 0.0
position_y = 0.0
last_time = None
current_yaw = 0.0  # radians

def rotate_body_to_world(vx_body, vy_body, yaw_rad):
    vx_world = vx_body * math.cos(yaw_rad) - vy_body * math.sin(yaw_rad)
    vy_world = vx_body * math.sin(yaw_rad) + vy_body * math.cos(yaw_rad)
    return vx_world, vy_world

def get_current_pos():
    return position_x, position_y

def save_position():
    with open("position.json", "w") as f:
        json.dump({
            "x": position_x,
            "y": position_y,
            "distance": math.sqrt(position_x**2 + position_y**2)
        }, f)

def on_optical_flow(msg, yaw_rad):
    global position_x, position_y, last_time

    now = time.time()

    if last_time is None:
        last_time = now
        return

    dt = now - last_time
    last_time = now
    quality = getattr(msg, "quality", 0)
    if quality < 50:
        print(f" Low quality ({quality}), skipping")
        return

    vx_body = msg.flow_comp_m_x
    vy_body = msg.flow_comp_m_y

    vx_world, vy_world = rotate_body_to_world(vx_body, vy_body, yaw_rad)

    position_x += vx_world * dt
    position_y += vy_world * dt

    distance = math.sqrt(position_x**2 + position_y**2)
    print(
        f"  Flow → vx:{vx_body:.3f} vy:{vy_body:.3f} m/s | "
        f"Pos: ({position_x:.2f}, {position_y:.2f}) m | "
        f"Distance travelled: {distance:.2f} m | Q:{quality}"
    )

    save_position()


if __name__ == "__main__":
    print("camera_sensor started")

    while True:
        try:
            print("Connecting to MAVLink...")
            addr = os.getenv('SITL_ADDRESS', 'udpin:0.0.0.0:14551')
            master = mavutil.mavlink_connection(addr)

            print("Waiting for heartbeat... (camera)")
            master.wait_heartbeat(timeout=10)
            print("✅ Connected")

            master.mav.request_data_stream_send(
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,
                20, 1
            )
            master.mav.request_data_stream_send(
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_EXTRA3,
                10, 1
            )

            while True:
                msg = master.recv_match(
                    type=["OPTICAL_FLOW", "ATTITUDE"],
                    blocking=True,
                    timeout=5
                )

                if msg is None:
                    print("No message received (timeout)")
                    continue

                msg_type = msg.get_type()

                if msg_type == "ATTITUDE":
                    current_yaw = msg.yaw

                elif msg_type == "OPTICAL_FLOW":
                    print(f"OPTICAL_FLOW raw → x:{msg.flow_x} y:{msg.flow_y} px/s")
                    print(f"GROUND DISTANCE: {msg.ground_distance}")
                    on_optical_flow(msg, current_yaw)

        except Exception as e:
            print(f"Connection lost, retrying in 2s... ({e})")
            last_time = None
            time.sleep(2)