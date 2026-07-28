"""soarm-recenter: set a joint's current physical pose as encoder center (2048).

Uses the Feetech 'set middle' command (Torque_Enable=128). This is the fix for the
encoder-seam problem (a joint whose range straddles 0/4095) and for aligning a
continuous joint's zero. Torque is released afterward so the joint stays hand-movable.

Hold the joint at the pose you want to become "center", then run.

Examples:
    soarm-recenter --arm leader --joint elbow_flex
    soarm-recenter --arm leader --joint all          # whole arm at current pose
    soarm-recenter --arm leader --joint all --verify  # confirm each recenter held
"""

from __future__ import annotations

from .bus import (
    CONTINUOUS,
    MOTORS,
    NAME_TO_ID,
    Bus,
    BusCommError,
    resolve_arm,
)
from .console import console

DRIFT_OK = 25  # counts (~2.2 deg); below this the recenter clearly held


def run(arm: str | None, port: str | None, joint: str, verify: bool = False) -> None:
    port, _ = resolve_arm(arm, port)
    if joint == "all":
        ids = list(MOTORS)
    elif joint in NAME_TO_ID:
        ids = [NAME_TO_ID[joint]]
    else:
        raise SystemExit(f"unknown joint '{joint}'; valid: {', '.join(NAME_TO_ID)}, all")

    failed = 0
    with Bus(port) as bus:
        for mid in ids:
            try:
                before = bus.present_position(mid)
                homing = bus.recenter(mid)
                after = bus.present_position(mid)
                note = ""
                if verify:
                    if MOTORS[mid] in CONTINUOUS:
                        # raw center 2048 isn't this joint's calibrated zero, and it can
                        # rotate the long way around the seam — drift would be meaningless
                        note = "  [dim](verify skipped: continuous joint)[/]"
                    else:
                        d = bus.verify_center(mid)
                        held = d <= DRIFT_OK
                        note = f"  drift {d} [{'green' if held else 'bold red'}]{'OK' if held else 'HIGH'}[/]"
            except BusCommError as e:
                failed += 1
                console.print(f"{MOTORS[mid]:14} [bold red]FAILED[/]: {e}")
                continue
            console.print(f"{MOTORS[mid]:14} pos {before:>5} -> {after:>5}  "
                          f"(homing_offset now {homing}){note}")
    if failed < len(ids):
        console.print("\n[yellow]recentered.[/] NOTE: this changed Homing_Offset; if these joints "
                      "are calibrated,\nre-run `soarm calibrate-leader` (or re-write ranges) so the "
                      "calibration matches.")
    raise SystemExit(1 if failed else 0)
