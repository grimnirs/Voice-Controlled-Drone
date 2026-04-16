from pymavlink import mavutil

# Connect to MAVLink Router output
master = mavutil.mavlink_connection("udp:127.0.0.1:14551")

print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Connected!")

while True:
    msg = master.recv_match(blocking=True)
    if msg:
        print(msg.get_type(), msg.to_dict())