import subprocess
import json
import re
import time

TOPIC = "/world/iris_warehouse/model/iris_with_gimbal/link/lidar_forward_link/sensor/lidar_forward/scan"
OUTPUT = "/shared/distances.json"

def read_sensor():
    proc = subprocess.Popen(
        ["gz", "topic", "--echo", "--topic", TOPIC],
        stdout=subprocess.PIPE,
        text=True
    )
    
    distances = {"forward": None}
    
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("ranges:"):
            try:
                val = float(line.split(":")[1].strip())
                if val > 0.0:
                    distances["forward"] = val
                    with open(OUTPUT, 'w') as f:
                        json.dump(distances, f)
            except:
                pass

if __name__ == "__main__":
    print("Sensor bridge starting...")
    read_sensor()