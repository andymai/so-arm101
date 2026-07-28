"""`soarm fetch`: download the SO-101 URDF + meshes used by the visualization tools.

We don't vendor these — they're ~MBs of third-party CAD meshes with their own
(Apache-2.0) license. This downloads them on demand into sim/SO101/ (gitignored).

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
# Repo-relative asset dir, consistent with calibration/ and logs/. Gitignored.
DEST = Path(__file__).resolve().parent.parent / "sim" / "SO101"


def run() -> None:
    url = f"https://codeload.github.com/{REPO}/tar.gz/refs/heads/{BRANCH}"
    print(f"downloading {REPO}@{BRANCH} ...")
    # trusted host (codeload.github.com), fixed https scheme
    with urllib.request.urlopen(url) as resp:
        blob = resp.read()

    prefix = f"{REPO.split('/')[1]}-{BRANCH}/{SUBDIR}/"
    DEST.mkdir(parents=True, exist_ok=True)
    dest_root = DEST.resolve()
    count = 0
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.startswith(prefix):
                continue
            rel = member.name[len(prefix):]
            out = (DEST / rel).resolve()
            if not out.is_relative_to(dest_root):
                continue  # path-traversal guard (defense-in-depth on a trusted source)
            src = tar.extractfile(member)
            if src is None:
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with src:
                out.write_bytes(src.read())
            count += 1

    if count == 0:
        print(f"ERROR: nothing extracted — did {SUBDIR} move upstream?", file=sys.stderr)
        raise SystemExit(1)
    print(f"extracted {count} files into {DEST}")
    print("view with:  soarm view   (or: soarm twin --live)")
