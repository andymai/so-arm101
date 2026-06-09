"""soarm-sync-check: compare leader vs follower normalized joint positions.

Hold both arms in the SAME physical pose (use hard stops where possible), then run
this. Joints that differ beyond --tol are flagged. wrist_roll is continuous and only
syncs if its homing zero is aligned (see soarm-recenter / soarm-calibrate-leader).

Example:
    soarm-sync-check --tol 8
"""

from __future__ import annotations

import argparse

from .bus import MOTORS
from .devices import follower, follower_positions, leader, leader_positions


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare leader vs follower joint sync")
    ap.add_argument("--tol", type=float, default=8.0, help="max allowed |diff| in degrees")
    args = ap.parse_args()

    with follower() as f, leader() as lead:
        print("leader is_calibrated:", lead.is_calibrated, " follower is_calibrated:", f.is_calibrated)
        fpos = follower_positions(f)
        lpos = leader_positions(lead)

    print(f"\n{'joint':14} {'leader':>9} {'follower':>9} {'diff':>8}")
    worst = 0.0
    for name in MOTORS.values():
        lv, fv = lpos.get(name, float("nan")), fpos.get(name, float("nan"))
        d = lv - fv
        worst = max(worst, abs(d))
        flag = "  <-- OUT OF SYNC" if abs(d) > args.tol else ""
        print(f"{name:14} {lv:9.1f} {fv:9.1f} {d:8.1f}{flag}")
    print(f"\nworst |diff| = {worst:.1f} deg (tolerance {args.tol})")
    raise SystemExit(0 if worst <= args.tol else 1)


if __name__ == "__main__":
    main()
