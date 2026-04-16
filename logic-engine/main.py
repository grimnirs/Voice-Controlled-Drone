"""
Logic Engine — Connection Test Stub

Connects to ArduPilot SITL via MAVSDK through mavlink-router.
mavlink-router pushes MAVLink over UDP to this container on port 14540.

This can now run simultaneously with QGC — no more fighting
over a single TCP port.

Usage:
    docker compose up    # starts both sim and logic-engine together
"""
import asyncio
import os
import threading
import time
from typing import Optional
from mavsdk import System
from mock_mavlink import cmd_arm, cmd_takeoff, fly_forward_10m
import grpc
from pymavlink import mavutil


async def countdown(seconds: int, message: str):
    for i in range(seconds, 0, -1):
        print(f"{message} {i} s...")
        await asyncio.sleep(1)


def is_transport_error(exc: Exception) -> bool:
    return isinstance(exc, grpc.aio.AioRpcError) and exc.code() == grpc.StatusCode.UNAVAILABLE


def tcpout_to_pymavlink(address: str) -> str:
    # MAVSDK: tcpout://sim:5790 -> pymavlink: tcp:sim:5790
    if address.startswith("tcpout://"):
        return "tcp:" + address[len("tcpout://") :]
    return address


def run_raw_flow_listener(mavlink_endpoint: str, shared_state: dict, stop_event: threading.Event):
    while not stop_event.is_set():
        conn = None
        try:
            print(f"[FLOW] Connecting raw MAVLink listener at {mavlink_endpoint}")
            conn = mavutil.mavlink_connection(mavlink_endpoint, source_system=245, autoreconnect=True)
            conn.wait_heartbeat(timeout=15)
            print("[FLOW] Heartbeat received. Listening for OPTICAL_FLOW(_RAD)...")

            while not stop_event.is_set():
                msg = conn.recv_match(
                    type=["OPTICAL_FLOW", "OPTICAL_FLOW_RAD", "DISTANCE_SENSOR"],
                    blocking=True,
                    timeout=1,
                )
                if msg is None:
                    continue

                msg_type = msg.get_type()
                now_s = time.time()

                if msg_type == "OPTICAL_FLOW":
                    shared_state["timestamp_s"] = now_s
                    shared_state["flow_x"] = float(getattr(msg, "flow_x", 0.0))
                    shared_state["flow_y"] = float(getattr(msg, "flow_y", 0.0))
                    shared_state["flow_comp_m_x"] = float(getattr(msg, "flow_comp_m_x", 0.0))
                    shared_state["flow_comp_m_y"] = float(getattr(msg, "flow_comp_m_y", 0.0))
                elif msg_type == "OPTICAL_FLOW_RAD":
                    dt_s = float(getattr(msg, "integration_time_us", 0.0)) / 1_000_000.0
                    shared_state["timestamp_s"] = now_s
                    if dt_s > 0:
                        shared_state["flow_comp_m_x"] = float(getattr(msg, "integrated_x", 0.0)) / dt_s
                        shared_state["flow_comp_m_y"] = float(getattr(msg, "integrated_y", 0.0)) / dt_s
                    else:
                        shared_state["flow_comp_m_x"] = 0.0
                        shared_state["flow_comp_m_y"] = 0.0
                elif msg_type == "DISTANCE_SENSOR":
                    shared_state["distance_sensor_m"] = float(getattr(msg, "current_distance", 0.0)) / 100.0
        except Exception as e:
            print(f"[FLOW] Listener error: {e}. Reconnecting in 2 seconds...")
            time.sleep(2)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass


async def stream_position(drone):
    while True:
        try:
            async for position in drone.telemetry.position():
                print(
                    f"  Lat: {position.latitude_deg:11.6f}  "
                    f"Lon: {position.longitude_deg:11.6f}  "
                    f"Alt: {position.relative_altitude_m:6.2f} m",
                    end="\r",
                )
        except Exception as e:
            if is_transport_error(e):
                print("\nTelemetry stream disconnected (position).")
                return
            print(f"\nPosition stream error: {e}")
            return


async def print_flight_mode(drone):
    last_mode = None
    while True:
        try:
            async for mode in drone.telemetry.flight_mode():
                if mode != last_mode:
                    print(f"\n  Flight mode: {mode}")
                    last_mode = mode
        except Exception as e:
            if is_transport_error(e):
                print("\nTelemetry stream disconnected (flight_mode).")
                return
            print(f"\nFlight mode stream error: {e}")
            return

async def run():
    address = os.getenv("SITL_ADDRESS", "tcpout://sim:5790")
    wait_for_qgc_s = int(os.getenv("WAIT_FOR_QGC_SECONDS", "20"))
    target_distance_m = float(os.getenv("TARGET_DISTANCE_M", "10.0"))
    distance_scale_a = float(os.getenv("DISTANCE_SCALE_A", "1.0"))
    distance_bias_b = float(os.getenv("DISTANCE_BIAS_B", "0.0"))
    brake_accel_m_s2 = float(os.getenv("BRAKE_ACCEL_M_S2", "1.2"))
    safety_margin_m = float(os.getenv("SAFETY_MARGIN_M", "0.25"))
    slow_zone_ratio = float(os.getenv("SLOW_ZONE_RATIO", "0.30"))
    slow_speed_m_s = float(os.getenv("SLOW_SPEED_M_S", "0.8"))
    use_raw_flow = os.getenv("USE_RAW_FLOW", "1").lower() in ("1", "true", "yes", "on")

    print("Logic Engine Booting Up...")
    print("Waiting 20 seconds for Gazebo + ArduPilot + MAVLink Router...")

    for i in range(20, 0, -1):
        print(f"Connecting in {i} seconds...")
        await asyncio.sleep(1)

    async def connect_and_wait_ready() -> System:
        drone = System()
        print(f"\nConnecting to MAVLink router at: {address}")
        await drone.connect(system_address=address)
        print("Waiting for ArduPilot heartbeat...")

        async for state in drone.core.connection_state():
            if state.is_connected:
                print("\n" + "=" * 40)
                print("✅ CONNECTED TO DRONE MAVLINK!")
                print("=" * 40 + "\n")
                break

        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("Drone ready!")
                break
        return drone

    print("\n========================================")
    print("QGC TEST FLOW")
    print("1) Open QGroundControl")
    print("2) Connect via UDP 14550")
    print("3) Keep vehicle in GUIDED mode")
    print("========================================")
    await countdown(wait_for_qgc_s, "Waiting for QGC/operator")

    did_takeoff = False
    flow_state: Optional[dict] = None
    flow_stop_event: Optional[threading.Event] = None
    flow_task = None

    if use_raw_flow:
        flow_state = {
            "timestamp_s": None,
            "flow_x": 0.0,
            "flow_y": 0.0,
            "flow_comp_m_x": 0.0,
            "flow_comp_m_y": 0.0,
            "distance_sensor_m": None,
        }
        flow_stop_event = threading.Event()
        flow_endpoint = tcpout_to_pymavlink(address)
        flow_task = asyncio.create_task(
            asyncio.to_thread(run_raw_flow_listener, flow_endpoint, flow_state, flow_stop_event)
        )

    try:
        while True:
            drone = await connect_and_wait_ready()
            flight_mode_task = asyncio.create_task(print_flight_mode(drone))
            telemetry_task = asyncio.create_task(stream_position(drone))

            try:
                if not did_takeoff:
                    print("\nStarting autonomous test sequence...")
                    await cmd_arm(drone, {"action": "arm"})
                    await cmd_takeoff(drone, {"action": "takeoff"})
                    async for position in drone.telemetry.position():
                        if position.relative_altitude_m >= 2.5:
                            print("Reached correct altitude after takeoff!")
                            break
                    did_takeoff = True
                    await asyncio.sleep(5)
                else:
                    print("\nReconnected. Restarting forward flight only...")

                print(f"Flying forward {target_distance_m:.1f} meters...")
                await fly_forward_10m(
                    drone,
                    target_distance_m=target_distance_m,
                    distance_scale_a=distance_scale_a,
                    distance_bias_b=distance_bias_b,
                    brake_accel_m_s2=brake_accel_m_s2,
                    safety_margin_m=safety_margin_m,
                    slow_zone_ratio=slow_zone_ratio,
                    slow_speed_m_s=slow_speed_m_s,
                    flow_state=flow_state,
                )
                print("Forward test complete. Holding position.")
                await asyncio.sleep(3)
                break
            except Exception as e:
                if is_transport_error(e):
                    print("\nMAVSDK transport disconnected. Reconnecting in 3 seconds...")
                else:
                    print(f"\nSequence failed: {e}. Retrying in 3 seconds...")
                await asyncio.sleep(3)
            finally:
                flight_mode_task.cancel()
                telemetry_task.cancel()
                await asyncio.gather(flight_mode_task, telemetry_task, return_exceptions=True)
    finally:
        if flow_stop_event is not None:
            flow_stop_event.set()
        if flow_task is not None:
            flow_task.cancel()
            await asyncio.gather(flow_task, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nDisconnected.")