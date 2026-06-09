"""Helpers to construct LeRobot's high-level SOFollower / SOLeader objects.

These load the saved calibration and expose normalized joint values (degrees,
gripper 0-100), which is what we compare for leader<->follower sync.
"""

from __future__ import annotations

from contextlib import contextmanager

from lerobot.robots.so_follower import SOFollower, SOFollowerConfig
from lerobot.teleoperators.so_leader import SOLeader, SOLeaderConfig

from .bus import load_config


@contextmanager
def _device(arm: str, config_cls, device_cls, calibrate: bool):
    cfg = load_config()[arm]
    dcfg = config_cls(port=cfg.port)
    dcfg.id = cfg.id
    dcfg.calibration_dir = None
    dev = device_cls(dcfg)
    dev.connect(calibrate=calibrate)
    try:
        yield dev
    finally:
        dev.disconnect()


def follower(calibrate: bool = False):
    return _device("follower", SOFollowerConfig, SOFollower, calibrate)


def leader(calibrate: bool = False):
    return _device("leader", SOLeaderConfig, SOLeader, calibrate)


def follower_positions(dev) -> dict[str, float]:
    return {k.replace(".pos", ""): v for k, v in dev.get_observation().items() if k.endswith(".pos")}


def leader_positions(dev) -> dict[str, float]:
    return {k.replace(".pos", ""): v for k, v in dev.get_action().items() if k.endswith(".pos")}
