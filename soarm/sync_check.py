"""soarm-sync-check: compare leader vs follower normalized joint positions.

Hold both arms in the SAME physical pose (use hard stops where possible), then run
this. Joints that differ beyond --tol are flagged. wrist_roll is continuous and only
syncs if its homing zero is aligned (see soarm-recenter / soarm-calibrate-leader).

Example:
    soarm-sync-check --tol 8
"""

from __future__ import annotations

from .bus import MOTORS
from .console import OK, console, status, table
from .devices import follower, follower_positions, leader, leader_positions


def run(tol: float = 8.0) -> None:
    with follower() as f, leader() as lead:
        console.print(f"leader is_calibrated: {lead.is_calibrated}   "
                      f"follower is_calibrated: {f.is_calibrated}")
        fpos = follower_positions(f)
        lpos = leader_positions(lead)

    t = table("joint", "leader", "follower", "diff", "sync", title="leader ↔ follower")
    worst = 0.0
    for name in MOTORS.values():
        lv, fv = lpos.get(name, float("nan")), fpos.get(name, float("nan"))
        d = lv - fv
        worst = max(worst, abs(d))
        in_sync = abs(d) <= tol
        t.add_row(name, f"{lv:.1f}", f"{fv:.1f}", f"{d:.1f}",
                  status("in sync" if in_sync else "OUT OF SYNC", ok=in_sync))
    console.print(t)
    style = OK if worst <= tol else "bold red"
    console.print(f"\nworst |diff| = [{style}]{worst:.1f} deg[/] (tolerance {tol})")
    raise SystemExit(0 if worst <= tol else 1)
