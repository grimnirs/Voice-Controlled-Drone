import sys

cmd = ""

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    print("got line:", line)
    if "stop." in line.lower():
        #sys.stdin.close()
        break
    cmd += line    
print("got cmd:", cmd)

#tanken är att vi ska importa 
#./bin/whisper-stream -m ../models/ggml-base.en.bin --step 500 --length 5000 | python3 ../../logic-engine/VTT.py
#så att den körs när man kör main, så börjar den lyssna direkt

