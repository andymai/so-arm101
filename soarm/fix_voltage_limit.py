"""soarm-fix-voltage-limit: repair/standardize STS3215 voltage limits.

Background: a motor whose Max_Voltage_Limit is below its supply voltage raises a
persistent over-voltage error and refuses ALL bus traffic — it looks like a dead
motor or a broken chain. We hit this on the follower's wrist_roll (limit 8.0V on a
12V rail). Factory limits are also inconsistent across motors (some 0, some 140).

This tool sets Max/Min voltage limits uniformly on the chosen motors.

IMPORTANT: a motor already in over-voltage error won't accept the EEPROM write while
the error is active. If a motor is stuck, temporarily power the board at a voltage
WITHIN its current limit window (e.g. the 5V leader supply) so the error clears, run
this, then restore the normal supply.

Examples:
    soarm-fix-voltage-limit --arm follower            # set all to 16.0V max / 4.0V min
    soarm-fix-voltage-limit --arm follower --max 16 --min 4
    soarm-fix-voltage-limit --arm follower --check    # report only, no writes
"""

from __future__ import annotations

import argparse

from .bus import MOTORS, BusCommError, Bus, add_arm_port_args, error_flags, resolve_arm


def main() -> None:
    ap = argparse.ArgumentParser(description="Repair/standardize STS3215 voltage limits")
    add_arm_port_args(ap)
    ap.add_argument("--max", type=float, default=16.0, help="Max_Voltage_Limit in volts")
    ap.add_argument("--min", type=float, default=4.0, help="Min_Voltage_Limit in volts")
    ap.add_argument("--check", action="store_true", help="report only, do not write")
    args = ap.parse_args()

    port, _ = resolve_arm(args.arm, args.port)
    max_raw, min_raw = round(args.max * 10), round(args.min * 10)

    with Bus(port) as bus:
        print(f"{'id':>2}  {'joint':14} {'present':>7} {'max_lim':>7} {'min_lim':>7} {'errors':>10}")
        for mid, name in MOTORS.items():
            v_raw, comm, err = bus.read(mid, "Present_Voltage")
            try:
                if comm != 0:
                    raise BusCommError(f"motor {mid}: no response")
                cmax = bus.value(mid, "Max_Voltage_Limit")
                cmin = bus.value(mid, "Min_Voltage_Limit")
            except BusCommError:
                print(f"{mid:>2}  {name:14} {'NO RESPONSE':>34}")
                continue
            flags = ",".join(error_flags(err)) or "ok"
            print(f"{mid:>2}  {name:14} {v_raw/10:>5.1f}V {cmax/10:>6.1f}V {cmin/10:>6.1f}V {flags:>10}")
            if args.check:
                continue
            try:
                with bus.unlocked(mid):
                    bus.write_checked(mid, "Max_Voltage_Limit", max_raw)
                    bus.write_checked(mid, "Min_Voltage_Limit", min_raw)
            except BusCommError as e:
                print(f"  WARNING: {e} (motor may be in error state)")

        if not args.check:
            print(f"\nset all motors -> max {args.max}V / min {args.min}V. verifying:")
            ok = True
            for mid, name in MOTORS.items():
                try:
                    nmax = bus.value(mid, "Max_Voltage_Limit") / 10
                    nmin = bus.value(mid, "Min_Voltage_Limit") / 10
                except BusCommError:
                    ok = False
                    print(f"  {name:14} NO RESPONSE")
                    continue
                good = abs(nmax - args.max) < 0.05 and abs(nmin - args.min) < 0.05
                ok &= good
                print(f"  {name:14} max {nmax:>4.1f}V min {nmin:>4.1f}V  {'ok' if good else 'MISMATCH'}")
            if not ok:
                print("\nsome writes did not stick — a motor may be in error state; "
                      "power it within its current limit window and retry.")
                raise SystemExit(1)


if __name__ == "__main__":
    main()
