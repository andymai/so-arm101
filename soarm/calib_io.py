"""soarm-calib: back up / restore LeRobot calibration files.

LeRobot stores calibration under ~/.cache/huggingface/lerobot/calibration/.
This versions copies inside the repo (calibration/) and restores them.

Examples:
    soarm-calib backup            # cache -> repo/calibration/
    soarm-calib restore           # repo/calibration/ -> cache
    soarm-calib path              # print the cache paths
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .bus import load_config

CACHE = Path.home() / ".cache/huggingface/lerobot/calibration"
REPO = Path(__file__).resolve().parent.parent / "calibration"


def follower_cache() -> Path:
    return CACHE / "robots/so_follower" / f"{load_config()['follower'].id}.json"


def leader_cache() -> Path:
    return CACHE / "teleoperators/so_leader" / f"{load_config()['leader'].id}.json"


def _pairs() -> list[tuple[Path, Path]]:
    return [
        (follower_cache(), REPO / "my_follower.json"),
        (leader_cache(), REPO / "my_leader.json"),
    ]


def run(action: str) -> None:
    if action == "path":
        print("follower:", follower_cache())
        print("leader:  ", leader_cache())
        return

    REPO.mkdir(parents=True, exist_ok=True)
    for cache, repo in _pairs():
        src, dst = (cache, repo) if action == "backup" else (repo, cache)
        if not src.exists():
            print(f"skip (missing): {src}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"{action}: {src}  ->  {dst}")
