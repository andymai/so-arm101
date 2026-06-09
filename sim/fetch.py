#!/usr/bin/env python3
"""Fetch the SO-101 simulation assets (URDF + MuJoCo MJCF + meshes) from TheRobotStudio.

We don't vendor these — they're ~MBs of third-party CAD meshes with their own (Apache-2.0)
license. This downloads them on demand into sim/SO101/ (gitignored).

    python sim/fetch.py

Source: https://github.com/TheRobotStudio/SO-ARM100  (Simulation/SO101, Apache-2.0)
"""

from __future__ import annotations

import io
import sys
import tarfile
import urllib.request
from pathlib import Path

REPO = "TheRobotStudio/SO-ARM100"
BRANCH = "main"
SUBDIR = "Simulation/SO101"
DEST = Path(__file__).resolve().parent / "SO101"


def main() -> int:
    url = f"https://codeload.github.com/{REPO}/tar.gz/refs/heads/{BRANCH}"
    print(f"downloading {REPO}@{BRANCH} ...")
    with urllib.request.urlopen(url) as resp:  # noqa: S310 (trusted host)
        blob = resp.read()

    prefix = f"{REPO.split('/')[1]}-{BRANCH}/{SUBDIR}/"
    DEST.mkdir(parents=True, exist_ok=True)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.startswith(prefix):
                continue
            rel = member.name[len(prefix):]
            out = DEST / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src:
                out.write_bytes(src.read())
            count += 1

    if count == 0:
        print(f"ERROR: nothing extracted — did {SUBDIR} move upstream?", file=sys.stderr)
        return 1
    print(f"extracted {count} files into {DEST}")
    print("view with:  python -m mujoco.viewer --mjcf sim/SO101/so101_new_calib.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
