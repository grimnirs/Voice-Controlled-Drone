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
    # TODO: check if drone is disarmed, then arm and check if it's armed
    pass

#-----Test for cmd_takeoff--------#
@pytest.mark.asyncio
async def test_takeoff_and_altitude(drone):
    # TODO: check if drone is armed, then takeoff and check the altitude after a few seconds
    pass

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
async def test_rotation_logic(drone):
    """Testar att drönaren faktiskt har ändrat heading efter en rotation."""
    # 1. Kolla start-heading
    async for h in drone.telemetry.heading():
        start_heading = h.heading_deg
        break

    rotate_cmd = {"action": "rotate", "direction": "clockwise"}
    await txt_to_cmd(drone, rotate_cmd)
    
    # 2. Kolla ny heading
    async for h in drone.telemetry.heading():
        end_heading = h.heading_deg
        break
    
    # Kolla att heading har ändrats (vi förväntar oss ca 90 grader eller åtminstone en skillnad)
    diff = abs((end_heading - start_heading + 180) % 360 - 180)
    assert diff > 10, f"Drönaren roterade inte tillräckligt, diff: {diff}"


#-----Test for cmd_land--------#
@pytest.mark.asyncio
async def test_land(drone):
    # TODO: check if drone is flying, then land and check if it's on the ground
    pass

  