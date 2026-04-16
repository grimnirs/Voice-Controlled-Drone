import asyncio
import time
from typing import Optional, TypedDict
from mavsdk.offboard import VelocityNedYaw


class DroneCommand(TypedDict, total=False):
    action: str
    direction: Optional[str]
    integer: Optional[int]
    unit: Optional[str]


async def cmd_arm(drone, command: DroneCommand):
    async for health in drone.telemetry.health():
        if health.is_armable:
            print("Drone is armable!")
            break
        print("Health not ready...")
        await asyncio.sleep(2)

    print("-- Arming motors --")
    while True:
        try:
            await drone.action.arm()
            print("Armed!")
            break
        except Exception as e:
            print(f"Arming failed: {e}")
            await asyncio.sleep(3)


async def cmd_takeoff(drone, command: DroneCommand):
    async for is_armed in drone.telemetry.armed():
        if not is_armed:
            raise RuntimeError("Drone not armed")
        break

    print("-- Takeoff --")
    await drone.action.set_takeoff_altitude(3.0)
    await drone.action.takeoff()

async def txt_to_cmd(drone, text: str):
    command = text.lower().strip()
    if "arm" in command:
        await drone.action.arm()
    
    elif "takeoff" in command:
        try: 
            await drone.action.set_takeoff_altitude(3.0)

            print("Arming...")
            try:
                await drone.action.arm()
            except Exception as e:
                print(f"Failed: {e}")
                raise e
            print("Successfully armed!")

            await asyncio.sleep(5)

            print("Taking off...")
            await drone.action.takeoff()
            print("Successfully took off!")

        except Exception as e:
            print(f"Failed: {e}")
            raise
        
    elif "land" in command: 
        await drone.action.land()

    elif "fly forward north" in command:
        try:
            await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
        
            try: 
                await drone.offboard.start()
            except Exception as e:
                print(f"Offboard FAILED: {e}")
                raise e
        
            await drone.offboard.set_velocity_ned(VelocityNedYaw(3.0, 0.0, 0.0, 0.0))

            await asyncio.sleep(10)
        
            await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
            await drone.offboard.stop()

        except Exception as e:
            print(f"Failed flying forward: {e}")
            raise
    
    else:
        print("Unknown command", {command})
        

async def _track_ground_distance(drone, shared_state: dict):
    """
    Keep latest downward rangefinder reading in meters.
    """
    async for sample in drone.telemetry.distance_sensor():
        shared_state["ground_distance_m"] = sample.current_distance_m


async def _estimate_speed_ned(drone, shared_state: dict):
    """
    Estimate horizontal speed in m/s from NED velocity telemetry.
    In GPS-denied mode this comes from EKF sources (optical flow + rangefinder).
    """
    async for pv in drone.telemetry.position_velocity_ned():
        vn = pv.velocity.north_m_s
        ve = pv.velocity.east_m_s
        shared_state["speed_m_s"] = (vn * vn + ve * ve) ** 0.5
        shared_state["north_m"] = pv.position.north_m
        shared_state["east_m"] = pv.position.east_m


async def fly_forward_distance(
    drone,
    target_distance_m: float = 10.0,
    command_speed_m_s: float = 2.0,
    distance_scale_a: float = 1.0,
    distance_bias_b: float = 0.0,
    brake_accel_m_s2: float = 1.2,
    safety_margin_m: float = 0.25,
    slow_zone_ratio: float = 0.30,
    slow_speed_m_s: float = 0.8,
    flow_state: Optional[dict] = None,
):
    """
    Fly forward (north) a target distance in GPS-denied environment.
    Distance is estimated by integrating real-time speed estimate.
    """
    if target_distance_m <= 0:
        raise ValueError("target_distance_m must be > 0")
    if command_speed_m_s <= 0:
        raise ValueError("command_speed_m_s must be > 0")
    if distance_scale_a <= 0:
        raise ValueError("distance_scale_a must be > 0")
    if brake_accel_m_s2 <= 0:
        raise ValueError("brake_accel_m_s2 must be > 0")
    if safety_margin_m < 0:
        raise ValueError("safety_margin_m must be >= 0")
    if slow_zone_ratio < 0:
        raise ValueError("slow_zone_ratio must be >= 0")
    if slow_speed_m_s <= 0:
        raise ValueError("slow_speed_m_s must be > 0")

    shared_state = {
        "ground_distance_m": None,
        "speed_m_s": 0.0,
        "north_m": None,
        "east_m": None,
    }

    print(
        f"Starting distance move: target={target_distance_m:.2f} m, "
        f"cmd_speed={command_speed_m_s:.2f} m/s, "
        f"distance_model={distance_scale_a:.3f}*NED + {distance_bias_b:.3f}, "
        f"brake_accel={brake_accel_m_s2:.2f} m/s^2, "
        f"safety_margin={safety_margin_m:.2f} m, "
        f"slow_zone_ratio={slow_zone_ratio:.2f}, "
        f"slow_speed={slow_speed_m_s:.2f} m/s"
    )

    ground_task = asyncio.create_task(_track_ground_distance(drone, shared_state))
    speed_task = asyncio.create_task(_estimate_speed_ned(drone, shared_state))

    distance_travelled_m = 0.0
    flow_distance_m = 0.0
    last_t = asyncio.get_running_loop().time()
    previous_print_bucket = -1
    start_north = None
    start_east = None

    try:
        await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()
        current_cmd_speed = command_speed_m_s
        await drone.offboard.set_velocity_ned(VelocityNedYaw(current_cmd_speed, 0.0, 0.0, 0.0))

        while True:
            await asyncio.sleep(0.05)
            now = asyncio.get_running_loop().time()
            dt = now - last_t
            last_t = now

            # Default fallback speed from EKF velocity
            speed_m_s = max(0.0, float(shared_state["speed_m_s"]))
            flow_comp_x_m_s = None
            flow_age_s = None
            use_flow_source = False

            if flow_state is not None:
                ts = flow_state.get("timestamp_s")
                if ts is not None:
                    flow_age_s = time.time() - ts
                    if flow_age_s < 1.0:
                        flow_comp_x_m_s = float(flow_state.get("flow_comp_m_x", 0.0))
                        # Forward progress estimate along optical-flow x component.
                        speed_m_s = max(0.0, flow_comp_x_m_s)
                        use_flow_source = True

            distance_travelled_m += speed_m_s * dt  # integration from active speed source
            if use_flow_source:
                flow_distance_m += speed_m_s * dt

            north = shared_state["north_m"]
            east = shared_state["east_m"]
            if north is not None and east is not None and start_north is None:
                start_north = north
                start_east = east
                print(
                    f"NED start locked: north={start_north:.2f} m, east={start_east:.2f} m"
                )

            ned_distance_m = 0.0
            if start_north is not None and north is not None:
                dn = north - start_north
                de = east - start_east
                ned_distance_m = (dn * dn + de * de) ** 0.5

            raw_distance_for_model_m = flow_distance_m if use_flow_source else ned_distance_m
            corrected_distance_m = max(
                0.0, (distance_scale_a * raw_distance_for_model_m) + distance_bias_b
            )
            remaining_m = max(0.0, target_distance_m - corrected_distance_m)
            brake_distance_m = (speed_m_s * speed_m_s) / (2.0 * brake_accel_m_s2)

            # Ramp down speed near the end to reduce overshoot.
            slow_zone_m = target_distance_m * slow_zone_ratio
            desired_speed = slow_speed_m_s if remaining_m <= slow_zone_m else command_speed_m_s
            if abs(desired_speed - current_cmd_speed) > 1e-3:
                current_cmd_speed = desired_speed
                await drone.offboard.set_velocity_ned(
                    VelocityNedYaw(current_cmd_speed, 0.0, 0.0, 0.0)
                )

            # Stop when remaining distance is smaller than estimated stopping distance.
            if remaining_m <= (brake_distance_m + safety_margin_m):
                break

            progress_bucket = int(corrected_distance_m * 2)  # print every ~0.5 m
            if progress_bucket != previous_print_bucket:
                previous_print_bucket = progress_bucket
                gd = shared_state["ground_distance_m"]
                gd_text = f"{gd:.2f} m" if gd is not None else "N/A"
                print(
                    f"Travelled(Corr)={corrected_distance_m:.2f} m, "
                    f"Travelled(FlowInt)={flow_distance_m:.2f} m, "
                    f"Travelled(NED)={ned_distance_m:.2f} m, "
                    f"Travelled(Int)={distance_travelled_m:.2f} m, "
                    f"speed={speed_m_s:.2f} m/s, "
                    f"speed_src={'FLOW' if use_flow_source else 'NED'}, "
                    f"flow_x={flow_comp_x_m_s if flow_comp_x_m_s is not None else float('nan'):.2f} m/s, "
                    f"flow_age={flow_age_s if flow_age_s is not None else float('nan'):.2f} s, "
                    f"cmd_speed={current_cmd_speed:.2f} m/s, "
                    f"brake_dist={brake_distance_m:.2f} m, "
                    f"remaining={remaining_m:.2f} m, "
                    f"ground_distance={gd_text}"
                )

        await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
        await asyncio.sleep(0.3)
        await drone.offboard.stop()
        print(
            f"Distance move complete. "
            f"Corrected distance target {target_distance_m:.2f} m reached."
        )
    except Exception as e:
        print(f"Failed distance move: {e}")
        try:
            await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
            await drone.offboard.stop()
        except Exception:
            pass
        raise
    finally:
        ground_task.cancel()
        speed_task.cancel()
        await asyncio.gather(ground_task, speed_task, return_exceptions=True)


async def fly_forward_10m(
    drone,
    target_distance_m: float = 10.0,
    distance_scale_a: float = 1.0,
    distance_bias_b: float = 0.0,
    brake_accel_m_s2: float = 1.2,
    safety_margin_m: float = 0.25,
    slow_zone_ratio: float = 0.30,
    slow_speed_m_s: float = 0.8,
    flow_state: Optional[dict] = None,
):
    """
    Simple wrapper requested for test flow.
    Uses optical-flow-based NED speed estimate + rangefinder stream.
    """
    await fly_forward_distance(
        drone,
        target_distance_m=target_distance_m,
        command_speed_m_s=2.0,
        distance_scale_a=distance_scale_a,
        distance_bias_b=distance_bias_b,
        brake_accel_m_s2=brake_accel_m_s2,
        safety_margin_m=safety_margin_m,
        slow_zone_ratio=slow_zone_ratio,
        slow_speed_m_s=slow_speed_m_s,
        flow_state=flow_state,
    )
