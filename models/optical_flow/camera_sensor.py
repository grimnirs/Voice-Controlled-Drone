from pymavlink import mavutil
import time
import math
import os

print("camera_sensor started")

position_x = 0.0
position_y = 0.0
last_time = None
current_yaw = 0.0  # radians

#översätter body-fixed velocities till world-fixed
#dvs fram kan vara norr eller syd beroende på hur kroppen är riktad
def rotate_body_to_world(vx_body, vy_body, yaw_rad):
    vx_world = vx_body * math.cos(yaw_rad) - vy_body * math.sin(yaw_rad)
    vy_world = vx_body * math.sin(yaw_rad) + vy_body * math.cos(yaw_rad)
    return vx_world, vy_world #säkerställer att kroppen alltid är samma norr/öst position

#msg: sensor data
#yaw_rad: drönarens nuvarande rotation/kurs i radianer
def on_optical_flow(msg, yaw_rad):
    global position_x, position_y, last_time #global för att vi vill ändra på de globala variablerna

    now = time.time() 

    if last_time is None: #för att kunna räkna på tidsskillnaden --> safety check
        last_time = now
        return

    dt = now - last_time #skillnaden sen vi mätte tiden senast
    last_time = now
    quality = getattr(msg, "quality", 0)
    if quality < 50:
        print(f" Low quality ({quality}), skipping")
        return #ifall ngt saknas i meddelandet vill vi inte använda det

    vx_body = msg.flow_comp_m_x  # m/s in drone body X
    vy_body = msg.flow_comp_m_y  # m/s in drone body Y

    vx_world, vy_world = rotate_body_to_world(vx_body, vy_body, yaw_rad) #rotera den rätt

    position_x += vx_world * dt #åker vi med en hastighet och har rört oss dt 
    position_y += vy_world * dt

    distance = math.sqrt(position_x**2 + position_y**2) #hur långt vi åkt
    print(
        f"  Flow → vx:{vx_body:.3f} vy:{vy_body:.3f} m/s | "
        f"Pos: ({position_x:.2f}, {position_y:.2f}) m | "
        f"Dist: {distance:.2f} m | Q:{quality}"
    )

# --- Main retry loop ---
while True:
    try:
        print("Connecting to MAVLink...")
        # master = mavutil.mavlink_connection("udpin:0.0.0.0:14551")
        addr = os.getenv('SITL_ADDRESS', 'udpin:0.0.0.0:14551')
        master = mavutil.mavlink_connection(addr)

        print("Waiting for heartbeat...")
        master.wait_heartbeat(timeout=10)
        print("✅ Connected")

        master.mav.request_data_stream_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,  # ATTITUDE
            20, 1
        ) #skicka yaw 20 gånger i sekunden
        master.mav.request_data_stream_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_EXTRA3,  # OPTICAL_FLOW
            10, 1
        ) #skicka optical flow 10 gånger i sekunden

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
                current_yaw = msg.yaw  #spara nuvarande kurs --> för att veta vilket håll hastigheten pekar åt

            elif msg_type == "OPTICAL_FLOW":
                print(f"OPTICAL_FLOW raw → x:{msg.flow_x} y:{msg.flow_y} px/s")
                on_optical_flow(msg, current_yaw) #för att beräkna positionen

    except Exception as e:
        print(f"Connection lost, retrying in 2s... ({e})")
        last_time = None  # reset timer so dt doesn't blow up on reconnect
        time.sleep(2)