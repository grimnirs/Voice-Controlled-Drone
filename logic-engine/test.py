import pytest
import asyncio
import pytest_asyncio
import os
from mavsdk import System
from mavsdk.offboard import PositionNedYaw
from command_handler import txt_to_cmd
from drone_connection import connect_and_wait_for_ready
from collision_handler import (
    get_forward_distance,
    get_up_distance,
    get_down_distance,
    COLLISION_THRESHOLD,
)
import math


RESET_TIMEOUT = 15  # seconds


async def reset_to_origin(drone):
    """Fly drone back to spawn @ 3m altitude, yaw 0. Wait until within 0.5m."""
    print("-- Resetting to origin --")
    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, -3.0, 0.0))
    try:
        await drone.offboard.start()
    except Exception:
        pass  # already started

    deadline = asyncio.get_event_loop().time() + RESET_TIMEOUT
    err = float("inf")
    while asyncio.get_event_loop().time() < deadline:
        async for p in drone.telemetry.position_velocity_ned():
            n, e, d = p.position.north_m, p.position.east_m, p.position.down_m
            err = math.sqrt(n*n + e*e + (d + 3.0)**2)
            print(f"reset err={err:.2f}m  pos=({n:.2f},{e:.2f},{-d:.2f})")
            break
        if err < 0.5:
            print("✅ Reset complete")
            return
        await asyncio.sleep(0.5)
    print(f"⚠️ Reset timed out at err={err:.2f}m")

# To run tests:
# 1. docker compose up -d
# 2. docker compose exec logic-engine pytest -s test.py



SITL_ADDRESS = "tcpout://sim:5790"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
command_file = os.path.join(BASE_DIR, 'commands.json')

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
    takeoff_cmd = {"action": "take off"}
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
async def test_fly_forward(drone):
    # TODO: check if drone is flying, then move forward and check the position after a few seconds
    ##### Move 5m forwards #####
    # Get starting position
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    async for start_pos in drone.telemetry.position_velocity_ned():
        start = start_pos.position
        break

    fly_fwd_cmd = {"action": "fly", "direction": "forward", "integer": 5, "unit": "meters"}
    await txt_to_cmd(drone, fly_fwd_cmd)
    await asyncio.sleep(8)

    # Get end position and use pythagoras theorem
    async for end_pos in drone.telemetry.position_velocity_ned():
        end = end_pos.position

        d_north = end.north_m - start.north_m
        d_east = end.east_m - start.east_m
        d_down = end.down_m - start.down_m

        # Apply pythagoras
        distance = math.sqrt(d_north**2 + d_east**2 + d_down**2)
        assert 4.0 < distance < 6.0
        break

#-----Test for sensor_forward--------#
@pytest.mark.asyncio
async def test_forward_sensor(drone):


    #TODO: Fixa så att den checkar data från sensorn istället för GPS!
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    await reset_to_origin(drone)

    # checka sensor
    before = get_forward_distance()
    print(f"forward before: {before}")

    fly_fwd_cmd = {"action": "fly", "direction": "forward", "integer": 99, "unit": "meters"}
    await txt_to_cmd(drone, fly_fwd_cmd)
    await asyncio.sleep(10)

    # checka sensor igen
    after = get_forward_distance()
    print(f"forward after: {after}")

    #kontroll
    assert after is not None, "No forward value"
    assert after < COLLISION_THRESHOLD, (
        f"Drone did not stop near ceiling: up={after:.2f}m, "
        f"expected < {COLLISION_THRESHOLD}m"
    )
    
#-----Test for sensor_up--------#
@pytest.mark.asyncio
async def test_up_sensor(drone):
    #TODO: Fixa så att den checkar data från sensorn istället för GPS!
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    await reset_to_origin(drone)

    # checka sensor
    before = get_up_distance()
    print(f"up before: {before}")

    fly_up_cmd = {"action": "fly", "direction": "up", "integer": 99, "unit": "meters"}
    await txt_to_cmd(drone, fly_up_cmd)
    await asyncio.sleep(10)


    # checka sensor igen
    after = get_up_distance()
    print(f"up after: {after}")

    assert after is not None, "No forward value"
    assert after < COLLISION_THRESHOLD, (
        f"Drone did not stop near ceiling: up={after:.2f}m, "
        f"expected < {COLLISION_THRESHOLD}m"
    )
    

#-----Test for sensor_down--------#
@pytest.mark.asyncio
async def test_down_sensor(drone):
    #TODO: Fixa så att den checkar data från sensorn istället för GPS!
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    await reset_to_origin(drone)

    # checka sensor
    before = get_down_distance()
    print(f"down before: {before}")


    fly_down_cmd = {"action": "fly", "direction": "down", "integer": 99, "unit": "meters"}
    await txt_to_cmd(drone, fly_down_cmd)
    await asyncio.sleep(10)

    # checka sensor igen
    after = get_down_distance()
    print(f"down after: {after}")

    assert after is not None, "No forward value"
    assert after < COLLISION_THRESHOLD, (
        f"Drone did not stop near ceiling: up={after:.2f}m, "
        f"expected < {COLLISION_THRESHOLD}m"
    )
    

@pytest.mark.asyncio
async def test_fly_backwards(drone):
    # TODO: check if drone is flying, then move backwards and check the position after a few seconds
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    async for start_pos in drone.telemetry.position_velocity_ned():
        start = start_pos.position
        break

    fly_bwd_cmd = {"action": "fly", "direction": "backward", "integer": 5, "unit": "meters"}
    await txt_to_cmd(drone, fly_bwd_cmd)
    await asyncio.sleep(8)

    # Get end position and use pythagoras theorem
    async for end_pos in drone.telemetry.position_velocity_ned():
        end = end_pos.position

        d_north = end.north_m - start.north_m
        d_east = end.east_m - start.east_m
        d_down = end.down_m - start.down_m

        # Apply pythagoras
        distance = math.sqrt(d_north**2 + d_east**2 + d_down**2)
        assert 4.0 < distance < 6.0
        break

@pytest.mark.asyncio
async def test_fly_right(drone):
    # TODO: check if drone is flying, then move right and check the position after a few seconds
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    async for start_pos in drone.telemetry.position_velocity_ned():
        start = start_pos.position
        break

    fly_right_cmd = {"action": "fly", "direction": "right", "integer": 5, "unit": "meters"}
    await txt_to_cmd(drone, fly_right_cmd)
    await asyncio.sleep(8)

    # Get end position and use pythagoras theorem
    async for end_pos in drone.telemetry.position_velocity_ned():
        end = end_pos.position

        d_north = end.north_m - start.north_m
        d_east = end.east_m - start.east_m
        d_down = end.down_m - start.down_m

        # Apply pythagoras
        distance = math.sqrt(d_north**2 + d_east**2 + d_down**2)
        assert 4.0 < distance < 6.0
        break

@pytest.mark.asyncio
async def test_fly_left(drone):
    # TODO: check if drone is flying, then move left and check the position after a few seconds
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    async for start_pos in drone.telemetry.position_velocity_ned():
        start = start_pos.position
        break

    fly_left_cmd = {"action": "fly", "direction": "left", "integer": 5, "unit": "meters"}
    await txt_to_cmd(drone, fly_left_cmd)
    await asyncio.sleep(8)

    # Get end position and use pythagoras theorem
    async for end_pos in drone.telemetry.position_velocity_ned():
        end = end_pos.position

        d_north = end.north_m - start.north_m
        d_east = end.east_m - start.east_m
        d_down = end.down_m - start.down_m

        # Apply pythagoras
        distance = math.sqrt(d_north**2 + d_east**2 + d_down**2)
        assert 4.0 < distance < 6.0
        break

@pytest.mark.asyncio
async def test_fly_up(drone):
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    async for start_pos in drone.telemetry.position_velocity_ned():
        start = start_pos.position
        break

    fly_up_cmd = {"action": "fly", "direction": "up", "integer": 5, "unit": "meters"}
    await txt_to_cmd(drone, fly_up_cmd)
    await asyncio.sleep(8)

    # Get end position and use pythagoras theorem
    async for end_pos in drone.telemetry.position_velocity_ned():
        end = end_pos.position

        d_north = end.north_m - start.north_m
        d_east = end.east_m - start.east_m
        d_down = end.down_m - start.down_m

        # Apply pythagoras
        distance = math.sqrt(d_north**2 + d_east**2 + d_down**2)
        assert 4.0 < distance < 6.0
        break

@pytest.mark.asyncio
async def test_fly_down(drone):
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    async for start_pos in drone.telemetry.position_velocity_ned():
        start = start_pos.position
        break

    fly_down_cmd = {"action": "fly", "direction": "down", "integer": 5, "unit": "meters"}
    await txt_to_cmd(drone, fly_down_cmd)
    await asyncio.sleep(8)

    # Get end position and use pythagoras theorem
    async for end_pos in drone.telemetry.position_velocity_ned():
        end = end_pos.position

        d_north = end.north_m - start.north_m
        d_east = end.east_m - start.east_m
        d_down = end.down_m - start.down_m

        # Apply pythagoras
        distance = math.sqrt(d_north**2 + d_east**2 + d_down**2)
        assert 4.0 < distance < 6.0
        break

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
    await asyncio.sleep(3)
    
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

    rotate_cmd = {"action": "rotate", "direction": "counter clockwise"}
    await txt_to_cmd(drone, rotate_cmd)
    await asyncio.sleep(3)
    
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
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    # Send land command
    land_cmd = {"action": "land"}
    await txt_to_cmd(drone, land_cmd)
    
    # Wait until the drone is no longer in the air (i.e., has landed)
    async for in_air in drone.telemetry.in_air():
        if not in_air:
            break
        await asyncio.sleep(1)

    # Check that drone has landed after sending the command
    async for position in drone.telemetry.position():
        altitude = position.relative_altitude_m
        assert altitude < 0.3, f"Drone failed to lande, altitude is {altitude:.2f} m"
        break
    
