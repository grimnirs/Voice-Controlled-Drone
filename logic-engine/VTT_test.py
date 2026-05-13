import pytest
import json
import os
import tempfile
from VTT import parse_and_validate, get_int, get_unit, append_command, _command_log, RE_NOISE, COMMAND_WORDS, parse_multi_command
from nlp.model import predict
import string
import re
# To run tests:
# 1. cd logic-engine
# 2. pytest -s VTT_test.py

def clean_text(text):
    return text.lower().strip()

def remove_triggers(text):
    return re.sub(r'\b(drone|over)\b', '', text, flags=re.IGNORECASE).strip()

def test_empty_string():
    assert parse_and_validate("") is None

def test_whitespace_only():
    assert parse_and_validate("   ") is None

def test_random_words():
    assert parse_and_validate("banana helicopter purple") is None

def test_only_direction():
    assert parse_and_validate("forward") is None

def test_only_action_fly():
    assert parse_and_validate("fly") is None

def test_only_rotate():
    assert parse_and_validate("rotate") is None

def test_multiple_directions():
    # result = parse_and_validate("fly forward backward")
    intent, _ = predict("fly forward backward!")
    result = parse_and_validate(intent)
    assert result == {"action": "fly", "direction": "forward"}

# def test_multiple_actions():
#     # result = parse_and_validate("fly and then land")
#     intent, _ = predict("fly and then land")
#     result = parse_and_validate(intent)
#     assert result == {"action": "fly", "direction": None} or result is None # returns land


# dessa är supported nu
# def test_west_not_supported():
#     assert parse_and_validate("fly west") is None

# def test_east_not_supported():
#     assert parse_and_validate("fly east") is None

def test_direction_with_punctuation():
    # result = parse_and_validate("fly forward!")
    intent, _ = predict("fly forward!")
    result = parse_and_validate(intent)
    assert result == {"action": "fly", "direction": "forward"}

# def test_synonym_go_parse():
#     words = normalize_text(["go", "forward"])
#     result = parse_and_validate(" ".join(words))
#     assert result == {"action": "fly", "direction": "forward"}

# def test_synonym_turn():
#     words = normalize_text(["turn", "clockwise"])
#     result = parse_and_validate(" ".join(words))
#     assert result == {"action": "rotate", "direction": "clockwise"}

# def test_synonym_halt():
#     words = normalize_text(["halt"])
#     result = parse_and_validate(" ".join(words))
#     assert result == {"action": "stop", "direction": None}

def test_large_number_not_supported():
    assert get_int(["fly", "forward", "twenty"]) is None

def test_multiple_numbers():
    # returns first match
    assert get_int(["fly", "5", "then", "10"]) == 5

def test_number_with_punctuation():
    assert get_int(["fly", "forward", "5,", "meters"]) is None  # comma breaks it

def test_unit_without_number():
    assert get_unit(["fly", "forward", "meters"]) is None

def test_unit_wrong_order():
    assert get_unit(["meters", "5"]) is None

def test_unit_far_from_number():
    assert get_unit(["fly", "5", "blah", "meters"]) is None

def test_remove_multiple_triggers():
    assert remove_triggers("drone drone fly forward over over") == "fly forward"

def test_remove_case_insensitive():
    assert remove_triggers("DRONE fly forward OVER") == "fly forward"

def test_noise_only():
    cleaned = RE_NOISE.sub('', "[inaudible]").strip()
    assert cleaned == ""

def test_noise_mixed():
    cleaned = RE_NOISE.sub('', "[laughter] fly forward").strip()
    assert cleaned == "fly forward"

def test_command_word_filter_removes_noise():
    words = ["banana", "fly", "forward", "pizza"]
    filtered = [w for w in words if w in COMMAND_WORDS]
    assert filtered == ["fly", "forward"]

def test_numbers_are_allowed():
    words = ["fly", "forward", "5"]
    filtered = [w for w in words if w in COMMAND_WORDS]
    assert "5" in filtered

def test_pipeline_natural_speech():
    raw = "drone go forward five meters over"
    cleaned = remove_triggers(raw)

    words = cleaned.split()
    # words = normalize_text(words)
    cleaned = " ".join(words)

    intent, _ = predict(cleaned)

    structured = parse_and_validate(intent)
    assert structured is not None

    integer = get_int(words)
    unit = get_unit(words)

    structured.update({"integer": integer, "unit": unit})

    assert structured == {
        "action": "fly",
        "direction": "forward",
        "integer": 5,
        "unit": "meters"
    }

def test_pipeline_with_noise_words():
    raw = "drone banana fly forward pizza 5 meters over"
    cleaned = remove_triggers(raw)

    words = cleaned.split()
    # words = normalize_text(words)

    filtered = [w for w in words if w in COMMAND_WORDS]
    cleaned = " ".join(filtered)

    intent, _ = predict(cleaned)

    structured = parse_and_validate(intent)

    assert structured["action"] == "fly"

def test_takeoff_single_word_fails():
    # assert parse_and_validate("takeoff") is None
    result = parse_and_validate("takeoff")
    assert result == {"action": "takeoff", "direction": None}

# def test_go_maps_to_fly():
#         assert normalize_text(["go", "left"]) == ["fly", "left"]

# def test_move_maps_to_fly():
#     assert normalize_text(["move", "forward"]) == ["fly", "forward"]

# def test_halt_maps_to_stop():
#     assert normalize_text(["halt"]) == ["stop"]

# def test_turn_maps_to_rotate():
#     assert normalize_text(["turn", "clockwise"]) == ["rotate", "clockwise"]

# def test_no_synonym():
#     assert normalize_text(["fly", "left"]) == ["fly", "left"]

# def test_mixed():
#     assert normalize_text(["go", "fly", "halt"]) == ["fly", "fly", "stop"]

def test_removes_drone():
    assert remove_triggers("drone fly forward") == "fly forward"

def test_removes_over():
    assert remove_triggers("fly forward over") == "fly forward"

def test_removes_both():
    assert remove_triggers("drone fly forward over") == "fly forward"

def test_case_insensitive():
    assert remove_triggers("DRONE fly forward OVER") == "fly forward"
    
def load():
    from nlp.model import predict
    predict = predict

def test_returns_tuple():
    intent, confidence = predict("fly forward")
    assert isinstance(intent, str)
    assert isinstance(confidence, float)

def test_confidence_between_0_and_1():
    __, confidence = predict("fly forward 5 meters")
    assert 0.0 <= confidence <= 1.0

def test_fly_forward():
    intent, confidence = predict("fly forward 5 meters")
    assert intent == "fly_forward"
    assert confidence >= 0.5

def test_fly_left():
    intent, confidence = predict("go left 10 meters")
    assert intent == "fly_left"

def test_land():
    intent, confidence = predict("land")
    assert intent == "land"

def test_take_off():
    intent, confidence = predict("take off")
    assert intent == "takeoff"

def test_arm():
    intent, confidence = predict("arm")
    assert intent == "arm"

def test_rotate():
    intent, confidence = predict("rotate clockwise")
    assert intent == "rotate_clockwise"

def test_stop():
    intent, confidence = predict("stop")
    assert intent == "stop"

def test_synonym_go():
    intent, confidence = predict("go forward 3 meters")
    assert intent == "fly_forward"

def test_synonym_move():
    intent, confidence = predict("move right 5 meters")
    print(intent)
    assert intent == "fly_right"

def test_synonym_halt_nlp():
    intent, confidence = predict("halt")
    assert intent == "stop"

def test_garbage_input_low_confidence():
    # Garbage should either return wrong intent or low confidence
    intent, confidence = predict("the weather is nice today")
    # We don't assert intent but confidence should be low
    # assert confidence < 0.9
    assert intent == "unknown"

def test_empty_string():
    # Should not crash
    intent, confidence = predict("")
    assert isinstance(intent, str)

def test_noisy_but_valid():
    # Simulate what comes through after buffer pruning
    intent, confidence = predict("fly left five meters")
    assert intent == "fly_left"
    assert confidence >= 0.5

# --- NLP Intent Tests ---

def test_nlp_returns_correct_types():
    # Tests that the output is (string, float)
    intent, confidence = predict("fly forward")
    assert isinstance(intent, str)
    assert isinstance(confidence, float)

def test_nlp_fly_intent():
    intent, __ = predict("go forward 5 meters")
    assert intent == "fly_forward"

def test_nlp_stop_intent():
    intent, __ = predict("halt")
    assert intent == "stop"

def test_nlp_land_intent():
    intent, __ = predict("land the drone")
    assert intent == "land"

def test_nlp_empty_string():
    # This ensures the model doesn't crash on empty input
    intent, confidence = predict("")
    assert isinstance(intent, str)

def test_nlp_low_confidence_on_garbage():
    # High confidence should be reserved for actual commands
    intent , confidence = predict("what time is it")
    # assert confidence < 0.9
    assert intent == "unknown"

# ─── full pipeline tests ──────────────────────────────────────────────────────

def test_pipeline_fly_forward():
    intent , confidence = predict("fly forward five meters")
    assert confidence >= 0.5
    result = parse_and_validate(intent)
    assert result["action"] == "fly"
    assert result["direction"] == "forward"
    words = [w.strip(string.punctuation) for w in "fly forward five meters".split()]
    assert get_int(words) == 5
    assert get_unit(words) == "meters"

def test_pipeline_rotate_clockwise():
    intent, confidence = predict("rotate clockwise")
    assert confidence >= 0.5
    result = parse_and_validate(intent)
    assert result["action"] == "rotate"
    assert result["direction"] == "clockwise"

def test_pipeline_garbage_rejected():
    intent, confidence = predict("the weather is nice today")
    result = parse_and_validate(intent)
    assert confidence < 0.5 or result is None
    
def test_parse_fly_backward():
    # result = parse_and_validate("fly backward")
    intent, _ = predict("fly backward")
    result = parse_and_validate(intent)
    assert result == {"action": "fly", "direction": "backward"}

def test_get_int_ten():
    assert get_int(["ten", "meters"]) == 10

def test_nlp_fly_backward_intent():
    intent, _ = predict("fly backward 7 meters")
    assert intent == "fly_backward"

def test_rotate_counterclockwise():
    intent_oneword, _ = predict("rotate counterclockwise")
    intent_space, _ = predict("rotate counter clockwise")
    assert intent_oneword == "rotate_counterclockwise"
    assert intent_space == "rotate_counterclockwise"

def test_parse_counterclockwise():
    intent_oneword, conf = predict("rotate counterclockwise")
    print(f"intent: '{intent_oneword}', confidence: {conf}")
    intent_space, _ = predict("rotate counter clockwise")
    result_oneword = parse_and_validate(intent_oneword)
    result_space = parse_and_validate(intent_space)
    assert result_oneword == {"action": "rotate", "direction": "counterclockwise"}
    assert result_space == {"action": "rotate", "direction": "counterclockwise"}

# ─── multiple commands and noise ──────────────────────────────────────────────────────

def test_multiple_actions_with_noise():
    raw_text = "fly to the left 2 meters and then move right 5 meters"
    
    # Call the multi-command parser which cleans and splits the text
    results = parse_multi_command(raw_text)
    
    # Assert two commands were extracted
    assert len(results) == 2
    
    # Validate the first segment: "fly to the left 2 meters"
    assert results[0] == {
        "action": "fly",
        "direction": "left",
        "integer": 2,
        "unit": "meters"
    }
    
    # Validate the second segment: "move right 5 meters"
    # Note: 'move' is in your CMD whitelist, allowing it to be parsed as 'fly'
    assert results[1] == {
        "action": "fly",
        "direction": "right",
        "integer": 5,
        "unit": "meters"
    }

def test_multi_command_simple_sequence():
    """Tests two distinct actions connected by 'and then'."""
    raw = "drone arm and then takeoff over"
    # Note: your code removes 'drone' and 'over' in main, 
    # but parse_multi_command needs the cleaned segment.
    cleaned = "arm and then takeoff"
    results = parse_multi_command(cleaned)
    
    assert len(results) == 2
    assert results[0]["action"] == "arm"
    assert results[1]["action"] == "take off" # Logic normalizes takeoff -> take off

def test_multi_command_with_parameters():
    """Tests complex navigation followed by a state change."""
    raw = "fly forward 5 meters and then stop"
    results = parse_multi_command(raw)
    
    assert len(results) == 2
    # First command validation
    assert results[0]["action"] == "fly"
    assert results[0]["direction"] == "forward"
    assert results[0]["integer"] == 5
    assert results[0]["unit"] == "meters"
    # Second command validation
    assert results[1]["action"] == "stop"
    assert results[1]["direction"] is None

def test_multi_command_heavy_noise():
    """Tests if filler words like 'please' or 'the' are ignored correctly."""
    # your clean_segment removes 'please', 'to the', etc.
    raw = "please fly to the left 3 meters and then land the drone"
    results = parse_multi_command(raw)
    
    assert len(results) == 2
    assert results[0] == {"action": "fly", "direction": "left", "integer": 3, "unit": "meters"}
    assert results[1]["action"] == "land"

def test_multi_command_synonym_substitution():
    """Tests if 'move' and 'go' correctly map to 'fly' in a sequence."""
    raw = "move up 2 meters and then go south 10 meters"
    results = parse_multi_command(raw)
    
    assert len(results) == 2
    assert results[0]["action"] == "fly"
    assert results[0]["direction"] == "up"
    assert results[1]["action"] == "fly"
    assert results[1]["direction"] == "backward"
    assert results[1]["integer"] == 10

def test_multi_command_invalid_second_part():
    """Tests that a valid first command is kept even if the second part is garbage."""
    raw = "fly backward 1 meter and then banana pizza"
    results = parse_multi_command(raw)
    
    # Should only return the first valid command
    assert len(results) == 1
    assert results[0]["action"] == "fly"
    assert results[0]["direction"] == "backward"

def test_multi_command_no_params_reject():
    """Tests that fly commands without distance are rejected in a sequence."""
    raw = "arm and then fly forward and then land"
    # 'fly forward' should be rejected because integer/unit are missing
    results = parse_multi_command(raw)
    
    assert len(results) == 2
    assert results[0]["action"] == "arm"
    assert results[1]["action"] == "land"

def test_multi_command_rotation():
    """Tests rotation with specific direction in a sequence."""
    raw = "rotate clockwise and then fly down 1 meter"
    results = parse_multi_command(raw)
    
    assert len(results) == 2
    assert results[0]["action"] == "rotate"
    assert results[0]["direction"] == "clockwise"
    assert results[1]["direction"] == "down"

def test_long_sequential_mission():
    """Tests a continuous sequence of 5 commands."""
    raw = "takeoff and then fly up 2 meters and then fly forward 10 meters and then rotate clockwise and then land"
    results = parse_multi_command(raw)
    
    # Check that all 5 parts were captured
    assert len(results) == 5
    expected_actions = ["take off", "fly", "fly", "rotate", "land"]
    
    for i, action in enumerate(expected_actions):
        assert results[i]["action"] == action
    
    # Check specific middle parameters
    assert results[2] == {"action": "fly", "direction": "forward", "integer": 10, "unit": "meters"}

def test_noisy_box_pattern():
    """Tests 4 directional commands with heavy filler words."""
    raw = "please fly forward 5 meters then go right 5 meters then move backward 5 meters and finally drift left 5 meters"
    results = parse_multi_command(raw)
    
    assert len(results) == 4
    directions = ["forward", "right", "backward", "left"]
    
    for i, direction in enumerate(directions):
        assert results[i]["action"] == "fly"
        assert results[i]["direction"] == direction
        assert results[i]["integer"] == 5

def test_arm_move_stop_sequence():
    """Tests transition from system arming to movement to emergency stop."""
    raw = "drone arm and then takeoff and then fly north 20 meters and then stop immediately over"
    # Note: main.py usually handles 'drone' and 'over', but for the unit test:
    cleaned = "arm and then takeoff and then fly north 20 meters and then stop"
    results = parse_multi_command(cleaned)
    
    assert len(results) == 4
    assert results[0]["action"] == "arm"
    assert results[1]["action"] == "take off"
    assert results[2]["direction"] == "forward"
    assert results[3]["action"] == "stop"