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

from .bus import MOTORS, BusCommError, Bus, error_flags, resolve_arm
from .console import console, dropout, status, table


def run(arm: str | None, port: str | None, max_v: float = 16.0, min_v: float = 4.0,
        check: bool = False) -> None:
    port, _ = resolve_arm(arm, port)
    max_raw, min_raw = round(max_v * 10), round(min_v * 10)

    with Bus(port) as bus:
        t = table("id", "joint", "present", "max_lim", "min_lim", "errors", title="voltage limits")
        for mid, name in MOTORS.items():
            v_raw, comm, err = bus.read(mid, "Present_Voltage")
            try:
                if comm != 0:
                    raise BusCommError(f"motor {mid}: no response")
                cmax = bus.value(mid, "Max_Voltage_Limit")
                cmin = bus.value(mid, "Min_Voltage_Limit")
            except BusCommError:
                t.add_row(str(mid), name, dropout(), "", "", "")
                continue
            flags = error_flags(err)
            t.add_row(str(mid), name, f"{v_raw/10:.1f}V", f"{cmax/10:.1f}V", f"{cmin/10:.1f}V",
                      status(",".join(flags) or "ok", ok=not flags))
            if check:
                continue
            try:
                with bus.unlocked(mid):
                    bus.write_checked(mid, "Max_Voltage_Limit", max_raw)
                    bus.write_checked(mid, "Min_Voltage_Limit", min_raw)
            except BusCommError as e:
                console.print(f"  [yellow]WARNING[/]: {e} (motor may be in error state)")
        console.print(t)

        if not check:
            console.print(f"\nset all motors -> max {max_v}V / min {min_v}V. verifying:")
            ok = True
            vt = table("joint", "max", "min", "result")
            for mid, name in MOTORS.items():
                try:
                    nmax = bus.value(mid, "Max_Voltage_Limit") / 10
                    nmin = bus.value(mid, "Min_Voltage_Limit") / 10
                except BusCommError:
                    ok = False
                    vt.add_row(name, "", "", dropout())
                    continue
                good = abs(nmax - max_v) < 0.05 and abs(nmin - min_v) < 0.05
                ok &= good
                vt.add_row(name, f"{nmax:.1f}V", f"{nmin:.1f}V",
                           status("ok" if good else "MISMATCH", ok=good))
            console.print(vt)
            if not ok:
                console.print("\n[bold red]some writes did not stick[/] — a motor may be in error "
                              "state; power it within its current limit window and retry.")
                raise SystemExit(1)
