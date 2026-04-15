from pymavlink import mavutil
import asyncio




print("nu är vi inne i camera_sensor")
print("Connecting to MAVLink...")

while True:
    try:
        master = mavutil.mavlink_connection("udpin:0.0.0.0:14551")
        master.wait_heartbeat(timeout=10)
        msg = master.recv_match(blocking=True)
        print(msg)
        print("✅ Connected to MAVLink")
        print(master)
        break
    except Exception as e:
        print("Waiting for MAVLink...", e)
        asyncio.sleep(1)