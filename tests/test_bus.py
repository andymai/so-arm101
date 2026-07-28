"""Tests for the pure (hardware-free) logic in soarm.bus."""

import sys
from pathlib import Path

import pytest

from soarm.bus import (
    CONTINUOUS,
    MOTORS,
    NAME_TO_ID,
    RESOLUTION,
    decode_present_position,
    decode_sign_magnitude,
    encode_sign_magnitude,
    error_flags,
    fold_homing,
    is_controller_port,
    lerobot_cli,
    load_config,
    resolve_arm,
)

# --- sign-magnitude homing encode/decode (11-bit magnitude + sign at bit 11) ---

@pytest.mark.parametrize("value", [0, 1, -1, 2047, -2047, 1000, -1000])
def test_sign_magnitude_round_trip(value):
    assert decode_sign_magnitude(encode_sign_magnitude(value)) == value


def test_encode_negative_sets_sign_bit():
    assert encode_sign_magnitude(-5) == (5 | (1 << 11))
    assert encode_sign_magnitude(5) == 5


@pytest.mark.parametrize("value", [2048, -2048, 5000, -5000])
def test_encode_rejects_out_of_range(value):
    with pytest.raises(ValueError):
        encode_sign_magnitude(value)


# --- present position: sign-magnitude in a 16-bit field (bit 15 = sign) ---

def test_decode_present_position_positive():
    assert decode_present_position(2048) == 2048
    assert decode_present_position(0) == 0


def test_decode_present_position_negative():
    # 0x8000 | 225  ->  -225  (the "32993" we saw on hardware near the seam)
    assert decode_present_position(0x8000 | 225) == -225
    assert decode_present_position(32993) == -225


# --- fold_homing: continuous-joint correction folded into +/-2047 by whole turns ---

@pytest.mark.parametrize("value", [0, 100, -100, 2047, -2047])
def test_fold_homing_in_range_unchanged(value):
    assert fold_homing(value) == value


def test_fold_homing_folds_overflow_by_a_turn():
    # the real wrist_roll case: -3286 is unencodable, +4096 turn -> 810 (same angle)
    assert fold_homing(-3286) == -3286 + RESOLUTION == 810
    # and the upstream "Magnitude 2073 exceeds 2047" case folds the other way
    assert fold_homing(2073) == 2073 - RESOLUTION
    assert abs(fold_homing(2073)) <= 2047


def test_fold_homing_result_is_always_encodable():
    for v in range(-3 * RESOLUTION, 3 * RESOLUTION, 137):
        assert abs(fold_homing(v)) <= 2047


# --- error_flags: decode the status byte into names ---

def test_error_flags_none():
    assert error_flags(0) == []


def test_error_flags_single_and_multiple():
    assert error_flags(1) == ["VOLTAGE"]
    assert error_flags(4) == ["OVERHEAT"]
    assert set(error_flags(1 | 4 | 32)) == {"VOLTAGE", "OVERHEAT", "OVERLOAD"}


# --- resolve_arm: --arm / --port resolution ---

def test_resolve_arm_by_name():
    port, arm_id = resolve_arm("follower", None)
    cfg = load_config()["follower"]
    assert port == cfg.port and arm_id == cfg.id


def test_resolve_arm_port_overrides():
    port, _ = resolve_arm("follower", "/dev/tty.custom")
    assert port == "/dev/tty.custom"


def test_resolve_arm_unknown_raises():
    with pytest.raises(SystemExit):
        resolve_arm("third_arm", None)


def test_resolve_arm_no_port_raises():
    with pytest.raises(SystemExit):
        resolve_arm(None, None)


# --- config + motor map invariants ---

def test_config_has_both_arms():
    cfg = load_config()
    assert {"follower", "leader"} <= set(cfg)
    assert cfg["follower"].port and cfg["leader"].port


def test_lerobot_cli_resolves_sibling_then_falls_back():
    # a real sibling of the interpreter (use the interpreter itself) resolves to its path...
    bindir = Path(sys.executable)
    assert lerobot_cli(bindir.name) == str(bindir)
    # ...and an unknown CLI falls back to the bare name (PATH lookup when activated)
    assert lerobot_cli("definitely-not-a-real-cli-xyz") == "definitely-not-a-real-cli-xyz"


@pytest.mark.parametrize("device", [
    "/dev/tty.usbmodem5B415319461",  # macOS
    "/dev/ttyACM0",                  # Linux CDC-ACM (Seeed/Waveshare board)
    "/dev/ttyUSB0",                  # Linux FTDI/CH340 adapter
])
def test_is_controller_port_matches_across_oses(device):
    assert is_controller_port(device)


@pytest.mark.parametrize("device", [
    "/dev/ttyS0",          # legacy onboard serial, not a USB controller
    "/dev/null",
    "/dev/tty.Bluetooth",  # macOS bluetooth serial
])
def test_is_controller_port_rejects_non_controllers(device):
    assert not is_controller_port(device)


def test_motor_map_consistency():
    assert len(MOTORS) == 6
    assert NAME_TO_ID == {v: k for k, v in MOTORS.items()}
    assert CONTINUOUS <= set(MOTORS.values())  # continuous joints are real joints
    assert "wrist_roll" in CONTINUOUS
