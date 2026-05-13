import pytest
import asyncio
import pytest_asyncio
import os
from mavsdk import System
from command_handler import txt_to_cmd
from drone_connection import connect_and_wait_for_ready
from collision_handler import get_forward_distance, get_up_distance, get_down_distance, stopping_distance
import math

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
    await asyncio.sleep(5)

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
    await asyncio.sleep(5)

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
    await asyncio.sleep(5)

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
    await asyncio.sleep(5)

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
    await asyncio.sleep(5)

    async for end_pos in drone.telemetry.position_velocity_ned():
        end = end_pos.position
        
        d_north = end.north_m - start.north_m
        d_east = end.east_m - start.east_m
        d_down = end.down_m - start.down_m 

        horizontal_drift = math.sqrt(d_north**2 + d_east**2)
        vertical_change = abs(d_down)

        print(f"Vertikal ändring: {vertical_change:.2f}m")
        print(f"Horisontell drift: {horizontal_drift:.2f}m")

        # 1. Kolla höjden (viktigast för Up/Down)
        assert 4.0 < vertical_change < 6.0, f"Fel höjdförändring: {vertical_change:.2f}m"
        
        # 2. Kolla stabiliteten
        assert horizontal_drift < 1.5, f"För mycket drift i sidled: {horizontal_drift:.2f}m"
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
    await asyncio.sleep(5)

    async for end_pos in drone.telemetry.position_velocity_ned():
        end = end_pos.position
        
        d_north = end.north_m - start.north_m
        d_east = end.east_m - start.east_m
        d_down = end.down_m - start.down_m 

        total_distance = math.sqrt(d_north**2 + d_east**2 + d_down**2)
        horizontal_drift = math.sqrt(d_north**2 + d_east**2)
        vertical_change = abs(d_down)

        print(f"Vertikal ändring: {vertical_change:.2f}m")
        print(f"Horisontell drift: {horizontal_drift:.2f}m")
        print(f"Total sträcka: {total_distance:.2f}m")

        # Kontrollera att den faktiskt sänkte sig ca 5m
        assert 4.0 < vertical_change < 6.0, f"Wrong altitude change: {vertical_change:.2f}m"
        
        # Kontrollera att drönaren höll sig hyfsat stabil (max 1.5m drift åt sidan)
        assert horizontal_drift < 1.5, f"Too much horizontal drift: {horizontal_drift:.2f}m"
        break


#-----Test for sensor_forward--------#
@pytest.mark.asyncio
async def test_forward_sensor(drone, capfd):
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    sensor_value = get_forward_distance()
    print(f"forward before: {sensor_value}")

    async for pos in drone.telemetry.position_velocity_ned():
        start = pos.position
        break

    capfd.readouterr()  # discard prior output so we only inspect this command's logs

    # Command a deliberately-too-long flight so the brake MUST be what stops the drone
    fly_fwd_cmd = {"action": "fly", "direction": "forward", "integer": 99, "unit": "meters"}
    await txt_to_cmd(drone, fly_fwd_cmd)
    await asyncio.sleep(10)

    captured = capfd.readouterr()

    async for pos in drone.telemetry.position_velocity_ned():
        end = pos.position
        break

    dist_moved = math.sqrt(
        (end.north_m - start.north_m)**2 + (end.east_m - start.east_m)**2
    )
    print(f"Drone flew {dist_moved:.2f}m before stopping (commanded 99m)")
    print(captured.out)
    assert "EMERGENCY STOPPING" in captured.out, (
    "Forward brake never fired — sensor pipeline did not stop the drone"
    )

    final_sensor_value = get_forward_distance()
    print(f"Forward distance after stop: {final_sensor_value:.2f}m")

    assert final_sensor_value is not None, "No final forward sensor value"

    assert 1.0 <= final_sensor_value <= 2.5, (
        f"Drone stopped at {final_sensor_value:.2f}m from obstacle, "
        "expected about 1–2m"
    )

#-----Test for sensor_up--------#
@pytest.mark.asyncio
async def test_up_sensor(drone, capfd):
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break

    sensor_value = get_up_distance()
    print(f"up before: {sensor_value}")

    async for pos in drone.telemetry.position_velocity_ned():
        start = pos.position
        break

    capfd.readouterr()

    fly_up_cmd = {"action": "fly", "direction": "up", "integer": 99, "unit": "meters"}
    await txt_to_cmd(drone, fly_up_cmd)
    await asyncio.sleep(10)

    captured = capfd.readouterr()

    async for pos in drone.telemetry.position_velocity_ned():
        end = pos.position
        break

    # NED down is positive downward, so climbing reduces down. Flip sign for "altitude gained".
    dist_moved = abs(start.down_m - end.down_m)
    print(f"Drone climbed {dist_moved:.2f}m before stopping (commanded 99m)")
    print(captured.out)

    assert "EMERGENCY STOPPING" in captured.out, (
        "Up brake never fired — sensor pipeline did not stop the drone"
    )

    final_sensor_value = get_up_distance()

    assert final_sensor_value is not None, "No final up sensor value"
    
    assert 1.0 <= final_sensor_value <= 2.5, (
        f"Drone stopped at {final_sensor_value:.2f}m from upper obstacle, "
        "expected about 1-2m"
    )

#-----Test for sensor_down--------#
@pytest.mark.asyncio
async def test_down_sensor(drone, capfd):
    async for in_air in drone.telemetry.in_air():
        assert in_air, "Drone was not in air!"
        break
    
    sensor_value = get_down_distance()
    print(f"down before: {sensor_value}")

    async for pos in drone.telemetry.position_velocity_ned():
        start = pos.position
        break

    capfd.readouterr()

    fly_down_cmd = {"action": "fly", "direction": "down", "integer": 99, "unit": "meters"}
    await txt_to_cmd(drone, fly_down_cmd)
    await asyncio.sleep(10)

    captured = capfd.readouterr()

    async for pos in drone.telemetry.position_velocity_ned():
        end = pos.position
        break

    dist_moved = abs(end.down_m - start.down_m)
    print(f"Drone descended {dist_moved:.2f}m before stopping (commanded 99m)")
    
    print(captured.out)
    assert "EMERGENCY STOPPING" in captured.out, (
        "Down brake never fired — sensor pipeline did not stop the drone"
    )
    final_sensor_value = get_down_distance()

    assert final_sensor_value is not None, "No final down sensor value"

    assert 1.0 <= final_sensor_value <= 2.5, (
        f"Drone stopped at {final_sensor_value:.2f}m from ground/obstacle, "
        "expected about 1–2m"
    )


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
    