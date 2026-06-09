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
def follower(calibrate: bool = False):
    cfg = load_config()["follower"]
    fcfg = SOFollowerConfig(port=cfg.port)
    fcfg.id = cfg.id
    fcfg.calibration_dir = None
    dev = SOFollower(fcfg)
    dev.connect(calibrate=calibrate)
    try:
        yield dev
    finally:
        dev.disconnect()


@contextmanager
def leader(calibrate: bool = False):
    cfg = load_config()["leader"]
    lcfg = SOLeaderConfig(port=cfg.port)
    lcfg.id = cfg.id
    lcfg.calibration_dir = None
    dev = SOLeader(lcfg)
    dev.connect(calibrate=calibrate)
    try:
        yield dev
    finally:
        dev.disconnect()


def follower_positions(dev) -> dict[str, float]:
    return {k.replace(".pos", ""): v for k, v in dev.get_observation().items() if k.endswith(".pos")}


def leader_positions(dev) -> dict[str, float]:
    return {k.replace(".pos", ""): v for k, v in dev.get_action().items() if k.endswith(".pos")}
