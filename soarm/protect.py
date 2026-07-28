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

from .bus import MOTORS, Bus, BusCommError, resolve_arm
from .console import console, table

# moderate defaults
DEFAULTS = {"accel": 100, "max_volt": 16.0, "min_volt": 4.0,
            "overload_torque": 80, "protective_torque": 20, "protection_time": 200}


def run(arm: str | None, port: str | None, accel: int = DEFAULTS["accel"],
        max_volt: float = DEFAULTS["max_volt"], min_volt: float = DEFAULTS["min_volt"],
        overload: int = DEFAULTS["overload_torque"], check: bool = False) -> None:
    port, _ = resolve_arm(arm, port)
    show = ["Maximum_Acceleration", "Max_Voltage_Limit", "Min_Voltage_Limit",
            "Overload_Torque", "Protective_Torque", "Protection_Time", "Torque_Limit"]

    with Bus(port) as bus:
        _dump(bus, show, title="current values")
        if check:
            return
        writes = {
            "Maximum_Acceleration": accel,
            "Acceleration": accel,
            "Max_Voltage_Limit": round(max_volt * 10),
            "Min_Voltage_Limit": round(min_volt * 10),
            "Overload_Torque": overload,
            "Protective_Torque": DEFAULTS["protective_torque"],
            "Protection_Time": DEFAULTS["protection_time"],
        }
        failed = []
        for mid in MOTORS:
            try:
                with bus.unlocked(mid):
                    for reg, val in writes.items():
                        bus.write_checked(mid, reg, val)
            except BusCommError as e:
                failed.append(MOTORS[mid])
                console.print(f"  [yellow]WARNING[/]: {e}")
        _dump(bus, show, title="applied — new values")
    if failed:
        console.print(f"\n[bold red]FAILED on[/]: {', '.join(failed)} — re-run "
                      "(a motor likely dropped mid-write).")
        raise SystemExit(1)
    console.print("\n[green]moderate protection set[/]: acceleration capped (limits current spikes), "
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


def _dump(bus: Bus, regs: list[str], *, title: str) -> None:
    t = table("joint", *(_HEADER.get(r, r[:8]) for r in regs), title=title)
    for mid, name in MOTORS.items():
        cells = []
        for r in regs:
            try:
                cells.append(str(bus.value(mid, r)))
            except BusCommError:
                cells.append("[dim]--[/]")
        t.add_row(name, *cells)
    console.print(t)
