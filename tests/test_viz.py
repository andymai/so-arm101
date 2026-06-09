"""Unit tests for the LeRobot-normalized -> URDF-radians joint mapping.

These don't need the mesh assets (the mapping is decoupled from yourdfpy): a revolute
joint is degrees->radians, the gripper is 0-100% across its URDF limit.
"""

import math

from soarm.viz import normalized_to_radians

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
GRIP = (0.0, 1.0)


def test_revolute_degrees_to_radians():
    out = normalized_to_radians({"elbow_flex": 90.0}, JOINTS, GRIP)
    assert math.isclose(out["elbow_flex"], math.pi / 2)


def test_revolute_negative_degrees():
    out = normalized_to_radians({"shoulder_pan": -45.0}, JOINTS, GRIP)
    assert math.isclose(out["shoulder_pan"], -math.pi / 4)


def test_gripper_percent_interpolates_limits():
    assert math.isclose(normalized_to_radians({"gripper": 0}, JOINTS, (0.0, 2.0))["gripper"], 0.0)
    assert math.isclose(normalized_to_radians({"gripper": 100}, JOINTS, (0.0, 2.0))["gripper"], 2.0)
    assert math.isclose(normalized_to_radians({"gripper": 50}, JOINTS, (0.0, 2.0))["gripper"], 1.0)


def test_missing_joints_are_skipped():
    out = normalized_to_radians({"wrist_roll": 10.0}, JOINTS, GRIP)
    assert set(out) == {"wrist_roll"}


def test_unknown_joint_in_pos_is_ignored():
    # only joints in joint_names are emitted, even if pos has extras
    out = normalized_to_radians({"elbow_flex": 0.0, "bogus": 99.0}, JOINTS, GRIP)
    assert "bogus" not in out
