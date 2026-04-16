# from pymavlink import mavutil
# import asyncio

# print("nu är vi inne i camera_sensor")



# while True:
#     try:
#         mav = mavutil.mavlink_connection("udpin:0.0.0.0:14551")
#         mav.wait_heartbeat(timeout=10)
#         msg = mav.recv_match(blocking=True)
#         msg = mav.recv_match(type='OPTICAL_FLOW', blocking=True)
#         print(msg.flow_x, msg.flow_y, msg.quality)

#         # Local position (GPS-denied friendly)
#         msg = mav.recv_match(type='LOCAL_POSITION_NED', blocking=True)
#         print(msg.x, msg.y, msg.z)

#         # Attitude
#         msg = mav.recv_match(type='ATTITUDE', blocking=True)
#         print(msg.roll, msg.pitch, msg.yaw)

#         # Multiple types at once
#         msg = mav.recv_match(type=['OPTICAL_FLOW', 'ATTITUDE', 'LOCAL_POSITION_NED'], blocking=True)
#         print(msg.get_type(), msg.to_dict())


#         print("Connecting to MAVLink...")
#         print(msg)
#         print("✅ Connected to MAVLink")
#         print(mav)
#         print(msg.flow_x, msg.flow_y, msg.flow_comp_m_x,msg.flow_comp_m_y)
#     except Exception as e:
#             print("Waiting for MAVLink...", e)
#             asyncio.sleep(1)

from pymavlink import mavutil
import time

print("nu är vi inne i camera_sensor")

def connect_mavlink():
    while True:
        try:
            mav = mavutil.mavlink_connection("udpin:0.0.0.0:14551")
            mav.wait_heartbeat(timeout=10)
            print("✅ Connected to MAVLink")
            print(f"System: {mav.target_system} Component: {mav.target_component}")
            return mav
        except Exception as e:
            print("Waiting for MAVLink...", e)
            time.sleep(1)

def request_optical_flow(mav):
    print("Requesting OPTICAL_FLOW stream...")
    message = mav.mav.command_long_encode(
        mav.target_system,
        mav.target_component,
        mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
        0,
        mavutil.mavlink.MAVLINK_MSG_ID_OPTICAL_FLOW,  # OPTICAL_FLOW message
        100000,  # 100ms = 10Hz
        0, 0, 0, 0, 0
    )
    mav.mav.send(message)

    response = mav.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
    if response and response.command == mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL:
        if response.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("✅ OPTICAL_FLOW stream accepted")
        else:
            print(f"❌ Command rejected, result: {response.result}")
    else:
        print("❌ No ACK received")

mav = connect_mavlink()
request_optical_flow(mav)

print("Listening for messages...")

while True:
    msg = mav.recv_match(blocking=True, timeout=5)
    if msg is None:
        print("timeout - no message received")
        continue

    msg_type = msg.get_type()
    print(f"GOT: {msg_type}")

    if msg_type == 'OPTICAL_FLOW':
        print(f"Flow X: {msg.flow_x}, Flow Y: {msg.flow_y}, Quality: {msg.quality}")

    elif msg_type == 'LOCAL_POSITION_NED':
        print(f"Pos X: {msg.x}, Y: {msg.y}, Z: {msg.z}")

    elif msg_type == 'ATTITUDE':
        print(f"Roll: {msg.roll}, Pitch: {msg.pitch}, Yaw: {msg.yaw}")