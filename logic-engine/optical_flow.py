# optical_flow.py

#-------
#    flow_engine = OpticalFlowProcessor(drone)
    
    # Run it as a background task
#    asyncio.create_task(flow_engine.start_processing())
#-------- detta ska in i main

import cv2
import asyncio

video_uri = "udp://sim:5760"

class OpticalFlowManager:
    def __init__(self, drone):
        self.drone = drone
        self.prev_frame = None
        self.current_altitude = 0.1 
        self.focal_length = 75.6    

    async def update_altitude(self):
        try:
            async for distance in self.drone.telemetry.distance_sensor():
                self.current_altitude = distance.current_distance_m
        except Exception as e:
            print(f"[Altitude task error]: {e}")

    async def run_vision_loop(self):
            # Start altitude monitoring in the background
            asyncio.create_task(self.update_altitude())
            
            cap = cv2.VideoCapture(video_uri, cv2.CAP_FFMPEG)
            
            if not cap.isOpened():
                print(f"Error: Unable to connect to {video_uri}")
                return
            
            import time
            last_time = time.time()

            try:
                while True:
                    # Read frame without blocking the rest of the async loop
                    ret, frame = await asyncio.to_thread(cap.read)
                    
                    if ret:
                        # Calculate actual dt for better Optical Flow accuracy
                        now = time.time()
                        actual_dt = now - last_time
                        last_time = now

                        # Process using the live telemetry altitude
                        await self.process_frame(frame, self.current_altitude, dt=actual_dt)
                        
                        cv2.imshow('Optical Flow Feed', frame)
                    
                    # Standard OpenCV break key
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    
                    # Brief sleep to let the altitude task run
                    await asyncio.sleep(0.001) 
            
            finally:
                # Ensures cleanup happens even if the code crashes
                cap.release()
                cv2.destroyAllWindows()
            
    async def process_frame(self, frame, altitude, dt):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.prev_frame is None:
            self.prev_frame = gray
            return

        flow = cv2.calcOpticalFlowFarneback(
        self.prev_frame, gray, None,
        0.5, 3, 15, 3, 5, 1.2, 0
        )
        self.prev_frame = gray

        # Compute mean flow in pixels/frame
        flow_x = float(flow[..., 0].mean())
        flow_y = float(flow[..., 1].mean())

        # Convert pixel flow → body-frame rad/s
        focal_length_px = 57.6  # match your SDF FOV + image size
        flow_comp_m_x = (flow_x / focal_length_px) * (altitude / dt)
        flow_comp_m_y = (flow_y / focal_length_px) * (altitude / dt)

        # Send MAVLink OPTICAL_FLOW message via pymavlink
        self.mavlink_conn.mav.optical_flow_send(
            int(asyncio.get_event_loop().time() * 1e6),  # time_usec
            0,           # sensor_id
            int(flow_x), # flow_x (pixels)
            int(flow_y), # flow_y (pixels)
            flow_comp_m_x,  # flow_comp_m_x (m/s)
            flow_comp_m_y,  # flow_comp_m_y (m/s)
            255,         # quality (0-255)
            altitude,    # ground_distance (m)
            )