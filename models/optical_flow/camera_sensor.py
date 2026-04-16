from pymavlink import mavutil
import time

print("camera_sensor started")
print("Connecting to MAVLink...")

while True:
    try:
        master = mavutil.mavlink_connection("udpin:0.0.0.0:14551")

        print("Waiting for heartbeat...")
        master.wait_heartbeat(timeout=10)
        print("✅ Connected to MAVLink")

        while True:
            msg = master.recv_match(type=["OPTICAL_FLOW", "OPTICAL_FLOW_RAD"], blocking=True)

            if not msg:
                continue

            flow_x = getattr(msg, "flow_x", None)
            flow_y = getattr(msg, "flow_y", None)
            print(f"OPTICAL FLOW → X: {flow_x}, Y: {flow_y}")

    except Exception as e:
        print("❌ Connection lost, retrying...", e)
        time.sleep(2)