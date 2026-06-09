"""soarm-record: preflight-checked dataset recording via lerobot-record.

Wraps `lerobot-record` with our config (ports/ids from config.toml), a preflight health
check on both arms, and a simple camera spec. Records leader->follower teleoperated
demonstrations into a LeRobot dataset (the input for training a policy).

Deliberately does NOT apply the teleop motion-clamp: a clamp would cap legitimate fast
demonstration motion. Record on a supply with headroom (12V 5A for the follower) instead
of clamping — see README.

Examples:
    soarm-record --list-cameras
    soarm-record --task "pick up the red cube and drop it in the bin" --episodes 30 \
        --camera front=0 --camera wrist=2
    soarm-record --task "..." --episodes 50 --repo-id andymai/so101-cube --push
"""

from __future__ import annotations

import getpass
import re
import subprocess

from .bus import lerobot_cli, load_config
from .teleop import _preflight


def _cameras_arg(specs: list[str], width: int, height: int, fps: int) -> str:
    """Turn ['front=0', 'wrist=2'] into the draccus cameras dict lerobot-record expects."""
    entries = []
    for spec in specs:
        name, _, index = spec.partition("=")
        # names/indices flow unquoted into a draccus YAML dict, so reject anything that
        # would corrupt it (spaces, ':', ',', '{') rather than fail confusingly downstream
        if not index or not re.fullmatch(r"[A-Za-z0-9_]+", name):
            raise SystemExit(f"--camera must be NAME=INDEX with an alphanumeric NAME (got '{spec}')")
        entries.append(
            f"{name}: {{type: opencv, index_or_path: {index}, "
            f"width: {width}, height: {height}, fps: {fps}}}"
        )
    return "{" + ", ".join(entries) + "}"


def run(task: str | None = None, episodes: int = 30, repo_id: str | None = None,
        camera: list[str] | None = None, width: int = 640, height: int = 480, fps: int = 30,
        episode_time: float = 30, reset_time: float = 15, push: bool = False,
        skip_preflight: bool = False, list_cameras: bool = False) -> None:
    camera = camera or []
    if list_cameras:
        raise SystemExit(subprocess.call([lerobot_cli("lerobot-find-cameras"), "opencv"]))

    if not task:
        raise SystemExit("--task is required (the dataset's natural-language label)")

    if not skip_preflight and not _preflight():
        raise SystemExit("preflight failed — fix the issues above (see `soarm scan`) before recording.")

    cfg = load_config()
    f, lead = cfg["follower"], cfg["leader"]
    repo_id = repo_id or f"{getpass.getuser()}/so101-dataset"

    cmd = [
        lerobot_cli("lerobot-record"),
        "--robot.type=so101_follower", f"--robot.port={f.port}", f"--robot.id={f.id}",
        "--teleop.type=so101_leader", f"--teleop.port={lead.port}", f"--teleop.id={lead.id}",
        f"--dataset.repo_id={repo_id}",
        f"--dataset.single_task={task}",
        f"--dataset.num_episodes={episodes}",
        f"--dataset.fps={fps}",
        f"--dataset.episode_time_s={episode_time}",
        f"--dataset.reset_time_s={reset_time}",
        f"--dataset.push_to_hub={'true' if push else 'false'}",
    ]
    if camera:
        cmd.append(f"--robot.cameras={_cameras_arg(camera, width, height, fps)}")

    print("\nlaunching:", " ".join(cmd), "\n")
    raise SystemExit(subprocess.call(cmd))
