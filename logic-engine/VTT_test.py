import pytest
import json
import os
import tempfile
from VTT import parse_and_validate, get_int, get_unit, clean_text, remove_triggers, append_command, _command_log, normalize_text, RE_NOISE, COMMAND_WORDS
from nlp.model import predict
# To run tests:
# 1. cd logic-engine
# 2. pytest -s VTT_test.py

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
    result = parse_and_validate("fly forward backward")
    # Your parser picks FIRST match → forward
    assert result == {"action": "fly", "direction": "forward"}

def test_multiple_actions():
    result = parse_and_validate("fly and then land")
    # parser grabs first match → fly
    assert result == {"action": "fly", "direction": None} or result is None

def test_west_not_supported():
    assert parse_and_validate("fly west") is None

def test_east_not_supported():
    assert parse_and_validate("fly east") is None

def test_direction_with_punctuation():
    result = parse_and_validate("fly forward!")
    assert result == {"action": "fly", "direction": "forward"}

def test_synonym_go_parse():
    words = normalize_text(["go", "forward"])
    result = parse_and_validate(" ".join(words))
    assert result == {"action": "fly", "direction": "forward"}

def test_synonym_turn():
    words = normalize_text(["turn", "clockwise"])
    result = parse_and_validate(" ".join(words))
    assert result == {"action": "rotate", "direction": "clockwise"}

def test_synonym_halt():
    words = normalize_text(["halt"])
    result = parse_and_validate(" ".join(words))
    assert result == {"action": "stop", "direction": None}

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
    words = normalize_text(words)
    cleaned = " ".join(words)

    structured = parse_and_validate(cleaned)
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
    words = normalize_text(words)

    filtered = [w for w in words if w in COMMAND_WORDS]
    cleaned = " ".join(filtered)

    structured = parse_and_validate(cleaned)
    assert structured["action"] == "fly"

def test_takeoff_single_word_fails():
    assert parse_and_validate("takeoff") is None

def test_go_maps_to_fly():
        assert normalize_text(["go", "left"]) == ["fly", "left"]

def test_move_maps_to_fly():
    assert normalize_text(["move", "forward"]) == ["fly", "forward"]

def test_halt_maps_to_stop():
    assert normalize_text(["halt"]) == ["stop"]

def test_turn_maps_to_rotate():
    assert normalize_text(["turn", "clockwise"]) == ["rotate", "clockwise"]

def test_no_synonym():
    assert normalize_text(["fly", "left"]) == ["fly", "left"]

def test_mixed():
    assert normalize_text(["go", "fly", "halt"]) == ["fly", "fly", "stop"]

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
    assert confidence < 0.9

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
    __, confidence = predict("what time is it")
    assert confidence < 0.9

