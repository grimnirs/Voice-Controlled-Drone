import subprocess
import json
import re
import time
import threading

TOPIC_FORWARD = "/world/iris_warehouse/model/iris_with_gimbal/link/lidar_forward_link/sensor/lidar_forward/scan"
TOPIC_UP = "/world/iris_warehouse/model/iris_with_gimbal/link/lidar_up_link/sensor/lidar_up/scan"
TOPIC_DOWN = "/world/iris_warehouse/model/iris_with_gimbal/link/lidar_down_link/sensor/lidar_down/scan"
OUTPUT = "/shared/distances.json"

distances = {"forward": None, "up": None, "down": None}
lock = threading.Lock()

def write_distances():
    with lock:
        with open(OUTPUT, 'w') as f:
            json.dump(distances, f)

def read_sensor_fwd():
    proc = subprocess.Popen(
        ["gz", "topic", "--echo", "--topic", TOPIC_FORWARD],
        stdout=subprocess.PIPE,
        text=True
    )
    
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("ranges:"):
            try:
                val = float(line.split(":")[1].strip())
                if val > 0.0:
                    with lock:
                        distances["forward"] = val
                    write_distances()
            except:
                pass

def read_sensor_up():
    proc = subprocess.Popen(
        ["gz", "topic", "--echo", "--topic", TOPIC_UP],
        stdout=subprocess.PIPE,
        text=True
    )
    
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("ranges:"):
            try:
                val = float(line.split(":")[1].strip())
                if val > 0.0:
                    with lock:
                        distances["up"] = val
                    write_distances()
            except:
                pass

def read_sensor_down():
    proc = subprocess.Popen(
        ["gz", "topic", "--echo", "--topic", TOPIC_DOWN],
        stdout=subprocess.PIPE,
        text=True
    )
    
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("ranges:"):
            try:
                val = float(line.split(":")[1].strip())
                if val > 0.0:
                    with lock:
                        distances["down"] = val
                    write_distances()
            except:
                pass

if __name__ == "__main__":
    print("Sensor bridge starting...")
    t1 = threading.Thread(target=read_sensor_fwd, daemon=True)
    t2 = threading.Thread(target=read_sensor_up, daemon=True)
    t3 = threading.Thread(target=read_sensor_down, daemon=True)
    t1.start()
    t2.start()
    t3.start()
    t1.join()
    t2.join()
    t3.join()