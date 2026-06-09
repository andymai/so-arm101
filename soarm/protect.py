"""soarm-set-protection: write 'moderate' brownout/safety limits to the follower.

The follower brownout we hit was a current spike (a desynced joint driven near-stall,
plus simultaneous acceleration) exceeding the 12V 2A supply. The safe, effective
on-motor guardrails are:

  1. Cap Maximum_Acceleration  -> limits the PEAK current spike from motion WITHOUT
     reducing holding torque (so it can't cause the arm to go limp).
  2. Standardize voltage limits (max 16.0V / min 4.0V) -> prevents the over-voltage
     limp failure and fixes inconsistent factory values.
  3. Standardize the factory overload protection (Overload_Torque% -> Protective_Torque%
     after Protection_Time) so a stalled joint backs off instead of stalling forever.

This does NOT lower Torque_Limit (that would weaken normal holding). Run on the
follower (the arm that does work); the leader doesn't need it.

Examples:
    soarm-set-protection --arm follower               # apply moderate defaults
    soarm-set-protection --arm follower --check        # report only
    soarm-set-protection --arm follower --accel 120    # looser accel cap
"""

from __future__ import annotations

import argparse

from .bus import MOTORS, BusCommError, Bus, add_arm_port_args, resolve_arm

# moderate defaults
DEFAULTS = dict(accel=100, max_volt=16.0, min_volt=4.0,
                overload_torque=80, protective_torque=20, protection_time=200)


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply moderate brownout/safety limits")
    add_arm_port_args(ap, arm_default="follower")
    ap.add_argument("--accel", type=int, default=DEFAULTS["accel"],
                    help="Maximum_Acceleration cap 0-254 (lower = gentler current)")
    ap.add_argument("--max-volt", type=float, default=DEFAULTS["max_volt"])
    ap.add_argument("--min-volt", type=float, default=DEFAULTS["min_volt"])
    ap.add_argument("--overload", type=int, default=DEFAULTS["overload_torque"],
                    help="Overload_Torque %% threshold")
    ap.add_argument("--check", action="store_true", help="report current values only")
    args = ap.parse_args()

    port, _ = resolve_arm(args.arm, args.port)
    show = ["Maximum_Acceleration", "Max_Voltage_Limit", "Min_Voltage_Limit",
            "Overload_Torque", "Protective_Torque", "Protection_Time", "Torque_Limit"]

    with Bus(port) as bus:
        print("current values:")
        _dump(bus, show)
        if args.check:
            return
        for mid in MOTORS:
            with bus.unlocked(mid):
                bus.write(mid, "Maximum_Acceleration", args.accel)
                bus.write(mid, "Acceleration", args.accel)
                bus.write(mid, "Max_Voltage_Limit", round(args.max_volt * 10))
                bus.write(mid, "Min_Voltage_Limit", round(args.min_volt * 10))
                bus.write(mid, "Overload_Torque", args.overload)
                bus.write(mid, "Protective_Torque", DEFAULTS["protective_torque"])
                bus.write(mid, "Protection_Time", DEFAULTS["protection_time"])
        print("\napplied. new values:")
        _dump(bus, show)
    print("\nmoderate protection set: acceleration capped (limits current spikes), "
          "voltage limits standardized, overload protection uniform. Holding torque unchanged.")


_HEADER = {
    "Maximum_Acceleration": "MaxAccel",
    "Max_Voltage_Limit":    "MaxVolt",
    "Min_Voltage_Limit":    "MinVolt",
    "Overload_Torque":      "Overload",
    "Protective_Torque":    "Protect",
    "Protection_Time":      "Prot_ms",
    "Torque_Limit":         "TrqLim",
}


def _dump(bus: Bus, regs: list[str]) -> None:
    print(f"{'joint':14} " + " ".join(f"{_HEADER.get(r, r[:8]):>8}" for r in regs))
    for mid, name in MOTORS.items():
        cells = []
        for r in regs:
            try:
                cells.append(str(bus.value(mid, r)))
            except BusCommError:
                cells.append("--")
        print(f"{name:14} " + " ".join(f"{c:>8}" for c in cells))


if __name__ == "__main__":
    main()
