import pytest
import asyncio
import pytest_asyncio
import os
from mavsdk import System
from command_handler import txt_to_cmd
from drone_connection import connect_and_wait_for_ready

# To run tests:
# 1. docker compose up -d
# 2. docker compose exec logic-engine pytest -s test.py


SITL_ADDRESS = "tcpout://sim:5790"

@pytest_asyncio.fixture(scope="function")
async def drone():
    # Använd samma logik som i main!
    drone = await connect_and_wait_for_ready(SITL_ADDRESS)
    yield drone

#-----Test for cmd_arm--------#
@pytest.mark.asyncio
async def test_arm_drone(drone):
    # check that drone is not armed at the start of the test
    async for is_armed in drone.telemetry.armed():
        assert not is_armed, "Drone was already armed at the start of the test!"
        break 

    # send arm command
    arm_cmd = {"action": "arm"}
    await txt_to_cmd(drone, arm_cmd)
    await asyncio.sleep(1)

    # check that drone is armed after sending the command
    async for is_armed in drone.telemetry.armed():
        assert is_armed, "Drone failed to arm!"
        break

#-----Test for cmd_takeoff--------#
@pytest.mark.asyncio
async def test_takeoff_and_altitude(drone):
    async for is_armed in drone.telemetry.armed():
        if not is_armed:
            print("Drone not armed, arming now...")
            arm_cmd = {"action": "arm"}
            await txt_to_cmd(drone, arm_cmd)
            await asyncio.sleep(2)  
        break
    # send takeoff command
    takeoff_cmd = {"action": "takeoff"}
    await txt_to_cmd(drone, takeoff_cmd)
    await asyncio.sleep(5) 

    # check that drone is flying and has reached approximately 3m altitude
    async for position in drone.telemetry.position():
        altitude = position.relative_altitude_m
        print(f"Current altitude: {altitude:.2f} m")
        assert altitude > 2.5, f"Drone failed to take off properly, altitude is only {altitude:.2f} m"
        break


#-----Test for cmd_fly--------#
@pytest.mark.asyncio
async def test_move_forward(drone):
    # TODO: check if drone is flying, then move forward and check the position after a few seconds
    pass

@pytest.mark.asyncio
async def test_move_backwards(drone):
    # TODO: check if drone is flying, then move backwards and check the position after a few seconds
    pass

@pytest.mark.asyncio
async def test_move_right(drone):
    # TODO: check if drone is flying, then move right and check the position after a few seconds
    pass

@pytest.mark.asyncio
async def test_move_left(drone):
    # TODO: check if drone is flying, then move left and check the position after a few seconds
    pass

#-----Test for cmd_rotate--------#
@pytest.mark.asyncio
async def test_rotate_clockwise(drone):
    """Verifies that the drone rotates approximately 90 degrees clockwise."""

    # Get start heading
    async for h in drone.telemetry.heading():
        start_heading = h.heading_deg
        break

    rotate_cmd = {"action": "rotate", "direction": "clockwise"}
    await txt_to_cmd(drone, rotate_cmd)
    
    # Get end heading
    async for h in drone.telemetry.heading():
        end_heading = h.heading_deg
        break
    
    # Calculating the difference in heading
    diff = (end_heading - start_heading + 540) % 360 - 180
    
    print(f"Start: {start_heading:.1f}°, End: {end_heading:.1f}°, Diff: {diff:.1f}°")

    # Check if the difference is approximately 90 degrees (allowing for some margin of error)
    assert abs(diff - 90) < 5, f"Rotation was {diff:.1f} degrees, expected ~90"

@pytest.mark.asyncio
async def test_rotate_counter_clockwise(drone):
    """Verifies that the drone rotates approximately 90 degrees counter-clockwise."""

    # Get start heading
    async for h in drone.telemetry.heading():
        start_heading = h.heading_deg
        break

    rotate_cmd = {"action": "rotate", "direction": "counter-clockwise"}
    await txt_to_cmd(drone, rotate_cmd)
    
    # Get end heading
    async for h in drone.telemetry.heading():
        end_heading = h.heading_deg
        break
    
    # Calculating the difference in heading
    diff = (end_heading - start_heading + 540) % 360 - 180
    
    print(f"Start: {start_heading:.1f}°, End: {end_heading:.1f}°, Diff: {diff:.1f}°")

    # Check if the difference is approximately 90 degrees (allowing for some margin of error)
    assert abs(diff + 90) < 5, f"Rotation was {diff:.1f} degrees, expected ~90"


#-----Test for cmd_land--------#
@pytest.mark.asyncio
async def test_land(drone):
    # TODO: check if drone is flying, then send land command and check that it lands properly
    pass