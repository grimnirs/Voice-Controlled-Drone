from pymavlink import mavutil
import time
import asyncio

class VisionEstimator:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0
        self.last = time.time()

    def update(self, vx, vy, vz):
        now = time.time()
        dt = now - self.last
        self.last = now

        self.x += vx * dt
        self.y += vy * dt
        self.z += vz * dt

        return self.x, self.y, self.z


#master = mavutil.mavlink_connection("tcp:127.0.0.1:5760")
#master = mavutil.mavlink_connection("tcp:sim:5760")

while True:
    try:
        master = mavutil.mavlink_connection("tcp:sim:5790")
        master.wait_heartbeat(timeout=10)
        print("Connected to  Mavlink")
        break
    except Exception as e:
        print(f"Connection to  Mavlink failed: {e}")
        time.sleep(2)

vision = VisionEstimator()

boot_time = int(time.time() * 1_000_000)

def send_vision(x, y, z):
    master.mav.vision_position_estimate_send(
        boot_time,
        float(x), float(y), float(z),
        0.0, 0.0, 0.0
    )

async def loop():
    vx, vy, vz = 1.0, 0.0, 0.0  # fake forward motion

    while True:
        x, y, z = vision.update(vx, vy, vz)
        send_vision(x, y, z)

        print(f"VISION -> {x:.2f}, {y:.2f}, {z:.2f}")

        await asyncio.sleep(0.5)

asyncio.run(loop())