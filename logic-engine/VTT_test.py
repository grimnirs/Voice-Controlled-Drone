import pytest
import json
import os
import tempfile
from VTT import parse_and_validate, get_int, get_unit, clean_text, remove_triggers, append_command, _command_log

# To run tests:
# 1. cd logic-engine
# 2. pytest -s VTT_test.py

# --- parse_and_validate ---

def test_arm():
    result = parse_and_validate("arm")
    assert result == {"action": "arm", "direction": None}

def test_take_off():
    result = parse_and_validate("take off")
    assert result == {"action": "take off", "direction": None}

def test_land():
    result = parse_and_validate("land")
    assert result == {"action": "land", "direction": None}

def test_stop():
    result = parse_and_validate("stop")
    assert result == {"action": "stop", "direction": None}

def test_fly_forward():
    result = parse_and_validate("fly forward")
    assert result == {"action": "fly", "direction": "forward"}

def test_fly_backward():
    result = parse_and_validate("fly backward")
    assert result == {"action": "fly", "direction": "backward"}

def test_fly_left():
    result = parse_and_validate("move to the left")
    assert result == {"action": "fly", "direction": "left"}

def test_fly_right():
    result = parse_and_validate("move to the right")
    assert result == {"action": "fly", "direction": "right"}

def test_fly_up():
    result = parse_and_validate("fly up")
    assert result == {"action": "fly", "direction": "up"}

def test_fly_down():
    result = parse_and_validate("fly down")
    assert result == {"action": "fly", "direction": "down"}

def test_rotate_clockwise():
    result = parse_and_validate("rotate clockwise")
    assert result == {"action": "rotate", "direction": "clockwise"}

def test_rotate_counter_clockwise():
    result = parse_and_validate("rotate counter clockwise")
    assert result == {"action": "rotate", "direction": "counter clockwise"}

def test_invalid_command_returns_none():
    result = parse_and_validate("hello there")
    assert result is None

def test_fly_without_direction_returns_none():
    result = parse_and_validate("fly")
    assert result is None

def test_case_insensitive():
    result = parse_and_validate("FLY FORWARD")
    assert result == {"action": "fly", "direction": "forward"}

# --- get_int ---

def test_get_int_digit():
    assert get_int(["fly", "forward", "5", "meters"]) == 5

def test_get_int_word_two():
    assert get_int(["fly", "forward", "two", "meters"]) == 2

def test_get_int_word_ten():
    assert get_int(["fly", "forward", "ten", "meters"]) == 10

def test_get_int_missing():
    assert get_int(["fly", "forward"]) is None

# --- get_unit ---

def test_get_unit_meters():
    assert get_unit(["fly", "forward", "5", "meters"]) == "meters"

def test_get_unit_meter_singular():
    assert get_unit(["fly", "forward", "1", "meter"]) == "meter"

def test_get_unit_centimeters():
    assert get_unit(["fly", "forward", "5", "centimeters"]) == "centimeters"

def test_get_unit_word_number():
    assert get_unit(["fly", "five", "meters"]) == "meters"

def test_get_unit_missing():
    assert get_unit(["fly", "forward"]) is None

# --- remove_triggers ---

def test_remove_drone():
    assert remove_triggers("drone fly forward") == "fly forward"

def test_remove_over():
    assert remove_triggers("fly forward over") == "fly forward"

def test_remove_both():
    assert remove_triggers("drone fly forward over") == "fly forward"

# --- simulating from parsed -> handled --> json ---


def test_pipeline_fly_forward_5_meters():
    raw = "drone fly forward 5 meters over"
    cleaned = remove_triggers(raw)
    structured = parse_and_validate(cleaned)
    assert structured is not None
    words = cleaned.split()
    integer = get_int(words)
    unit = get_unit(words)
    structured.update({"integer": integer, "unit": unit})
    assert structured == {"action": "fly", "direction": "forward", "integer": 5, "unit": "meters"}

def test_pipeline_fly_up_three_meters():
    raw = "drone fly up three meters over"
    cleaned = remove_triggers(raw)
    structured = parse_and_validate(cleaned)
    assert structured is not None
    words = cleaned.split()
    integer = get_int(words)
    unit = get_unit(words)
    structured.update({"integer": integer, "unit": unit})
    assert structured == {"action": "fly", "direction": "up", "integer": 3, "unit": "meters"}

def test_pipeline_land():
    raw = "drone land over"
    cleaned = remove_triggers(raw)
    structured = parse_and_validate(cleaned)
    assert structured == {"action": "land", "direction": None}

def test_pipeline_rotate_clockwise():
    raw = "drone rotate clockwise over"
    cleaned = remove_triggers(raw)
    structured = parse_and_validate(cleaned)
    assert structured == {"action": "rotate", "direction": "clockwise"}

def test_pipeline_invalid_no_direction():
    raw = "drone fly over"
    cleaned = remove_triggers(raw)
    structured = parse_and_validate(cleaned)
    assert structured is None

def test_pipeline_noise_ignored():
    raw = "[blank_audio]"
    assert "blank_audio" in raw  
    structured = parse_and_validate(raw)
    assert structured is None