"""Test-only latency instrumentation. Production code is not modified."""

import asyncio
import csv
import time
from typing import Optional


class LatencyRecorder:
    """Wraps drone.offboard.set_velocity_body to capture the first setpoint timestamp."""

    def __init__(self):
        self.t_first_setpoint: Optional[float] = None
        self._original = None
        self._drone = None

    def attach(self, drone):
        if self._original is not None:
            return
        self._drone = drone
        self._original = drone.offboard.set_velocity_body

        async def wrapped(setpoint, *args, **kwargs):
            # Skip the (0,0,0,0) priming setpoint that offboard mode requires before start().
            # We want the first setpoint that actually commands movement.
            is_zero = (
                getattr(setpoint, "forward_m_s", 0.0) == 0.0
                and getattr(setpoint, "right_m_s", 0.0) == 0.0
                and getattr(setpoint, "down_m_s", 0.0) == 0.0
                and getattr(setpoint, "yawspeed_deg_s", 0.0) == 0.0
            )
            if not is_zero and self.t_first_setpoint is None:
                self.t_first_setpoint = time.perf_counter()
            return await self._original(setpoint, *args, **kwargs)

        drone.offboard.set_velocity_body = wrapped

    def reset(self):
        self.t_first_setpoint = None


async def wait_for_linear_motion(drone, threshold_m_s: float = 0.15, timeout: float = 15.0) -> Optional[float]:
    """Returns perf_counter timestamp when |velocity| first exceeds threshold, or None on timeout."""

    async def _poll():
        async for pv in drone.telemetry.position_velocity_ned():
            v = pv.velocity
            speed = (v.north_m_s ** 2 + v.east_m_s ** 2 + v.down_m_s ** 2) ** 0.5
            if speed > threshold_m_s:
                return time.perf_counter()

    try:
        return await asyncio.wait_for(_poll(), timeout=timeout)
    except asyncio.TimeoutError:
        return None


async def wait_for_angular_motion(drone, threshold_rad_s: float = 0.1, timeout: float = 15.0) -> Optional[float]:
    """Returns perf_counter timestamp when |yaw rate| first exceeds threshold, or None on timeout."""

    async def _poll():
        async for av in drone.telemetry.attitude_angular_velocity_body():
            if abs(av.yaw_rad_s) > threshold_rad_s:
                return time.perf_counter()

    try:
        return await asyncio.wait_for(_poll(), timeout=timeout)
    except asyncio.TimeoutError:
        return None


class LatencyLogger:
    """Collects latency samples across the pytest session and writes them to CSV."""

    FIELDS = [
        "test",
        "dispatch_to_setpoint_ms",
        "setpoint_to_motion_ms",
        "total_dispatch_to_motion_ms",
    ]

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.rows = []

    def log(self, test_name: str, t_dispatch: float, t_first_setpoint: Optional[float], t_motion: Optional[float]):
        def ms(a, b):
            if a is None or b is None:
                return None
            return round((b - a) * 1000.0, 2)

        self.rows.append({
            "test": test_name,
            "dispatch_to_setpoint_ms": ms(t_dispatch, t_first_setpoint),
            "setpoint_to_motion_ms": ms(t_first_setpoint, t_motion),
            "total_dispatch_to_motion_ms": ms(t_dispatch, t_motion),
        })

    def flush(self):
        if not self.rows:
            return
        with open(self.csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.FIELDS)
            w.writeheader()
            w.writerows(self.rows)
