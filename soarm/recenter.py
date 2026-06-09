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

import argparse

from .bus import (
    CONTINUOUS,
    MOTORS,
    NAME_TO_ID,
    BusCommError,
    Bus,
    add_arm_port_args,
    resolve_arm,
)

DRIFT_OK = 25  # counts (~2.2 deg); below this the recenter clearly held


def main() -> None:
    ap = argparse.ArgumentParser(description="Recenter joint(s) to encoder middle (2048)")
    add_arm_port_args(ap)
    ap.add_argument("--joint", required=True,
                    help="joint name (e.g. elbow_flex) or 'all'")
    ap.add_argument("--verify", action="store_true",
                    help="after recentering, torque to goal 2048 and report drift "
                         "(the joint will briefly move and hold center)")
    args = ap.parse_args()

    port, _ = resolve_arm(args.arm, args.port)
    if args.joint == "all":
        ids = list(MOTORS)
    elif args.joint in NAME_TO_ID:
        ids = [NAME_TO_ID[args.joint]]
    else:
        raise SystemExit(f"unknown joint '{args.joint}'; valid: {', '.join(NAME_TO_ID)}, all")

    failed = 0
    with Bus(port) as bus:
        for mid in ids:
            try:
                before = bus.present_position(mid)
                homing = bus.recenter(mid)
                after = bus.present_position(mid)
                verify = ""
                if args.verify:
                    if MOTORS[mid] in CONTINUOUS:
                        # raw center 2048 isn't this joint's calibrated zero, and it can
                        # rotate the long way around the seam — drift would be meaningless
                        verify = "  (verify skipped: continuous joint)"
                    else:
                        d = bus.verify_center(mid)
                        verify = f"  drift {d} {'OK' if d <= DRIFT_OK else 'HIGH'}"
            except BusCommError as e:
                failed += 1
                print(f"{MOTORS[mid]:14} FAILED: {e}")
                continue
            print(f"{MOTORS[mid]:14} pos {before:>5} -> {after:>5}  (homing_offset now {homing}){verify}")
    if failed < len(ids):
        print("\nrecentered. NOTE: this changed Homing_Offset; if these joints are calibrated,")
        print("re-run soarm-calibrate-leader (or re-write ranges) so the calibration matches.")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
