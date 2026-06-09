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

import argparse
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


def main() -> None:
    ap = argparse.ArgumentParser(description="Preflight-checked LeRobot dataset recording")
    ap.add_argument("--list-cameras", action="store_true",
                    help="run lerobot-find-cameras (discover indices) and exit")
    ap.add_argument("--task", help="natural-language task description (the dataset label)")
    ap.add_argument("--episodes", type=int, default=30, help="number of episodes to record")
    ap.add_argument("--repo-id", help="dataset repo id, e.g. user/so101-cube "
                                      "(default: <user>/so101-dataset)")
    ap.add_argument("--camera", action="append", default=[], metavar="NAME=INDEX",
                    help="camera, repeatable (e.g. --camera front=0 --camera wrist=2)")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--episode-time", type=float, default=30, help="seconds per episode")
    ap.add_argument("--reset-time", type=float, default=15, help="seconds to reset between episodes")
    ap.add_argument("--push", action="store_true", help="push the dataset to the Hugging Face Hub")
    ap.add_argument("--skip-preflight", action="store_true")
    args = ap.parse_args()

    if args.list_cameras:
        raise SystemExit(subprocess.call([lerobot_cli("lerobot-find-cameras"), "opencv"]))

    if not args.task:
        raise SystemExit("--task is required (the dataset's natural-language label)")

    if not args.skip_preflight and not _preflight():
        raise SystemExit("preflight failed — fix the issues above (see soarm-scan) before recording.")

    cfg = load_config()
    f, lead = cfg["follower"], cfg["leader"]
    repo_id = args.repo_id or f"{getpass.getuser()}/so101-dataset"

    cmd = [
        lerobot_cli("lerobot-record"),
        "--robot.type=so101_follower", f"--robot.port={f.port}", f"--robot.id={f.id}",
        "--teleop.type=so101_leader", f"--teleop.port={lead.port}", f"--teleop.id={lead.id}",
        f"--dataset.repo_id={repo_id}",
        f"--dataset.single_task={args.task}",
        f"--dataset.num_episodes={args.episodes}",
        f"--dataset.fps={args.fps}",
        f"--dataset.episode_time_s={args.episode_time}",
        f"--dataset.reset_time_s={args.reset_time}",
        f"--dataset.push_to_hub={'true' if args.push else 'false'}",
    ]
    if args.camera:
        cmd.append(f"--robot.cameras={_cameras_arg(args.camera, args.width, args.height, args.fps)}")

    print("\nlaunching:", " ".join(cmd), "\n")
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
