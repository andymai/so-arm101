"""soarm-teleop: brownout-safe teleoperation launcher.

Runs a preflight health check on BOTH arms (all motors respond, no error bits,
voltages sane), then launches lerobot-teleoperate with a motion clamp
(--robot.max_relative_target) to cap per-cycle current spikes.

Examples:
    soarm-teleop                 # preflight + clamped teleop
    soarm-teleop --clamp 12      # looser clamp (faster, more current)
    soarm-teleop --no-clamp      # disable the clamp
    soarm-teleop --check-only    # run preflight and exit
"""

from __future__ import annotations

import argparse
import subprocess

from .bus import MOTORS, Bus, error_flags, load_config


def _preflight(min_volt: float = 9.0) -> bool:
    cfg = load_config()
    ok = True
    for arm in ("follower", "leader"):
        port = cfg[arm].port
        print(f"[{arm}] {port}")
        try:
            with Bus(port) as bus:
                for mid, name in MOTORS.items():
                    v, comm, err = bus.read(mid, "Present_Voltage")
                    if comm != 0:
                        print(f"   {name:14} NO RESPONSE")
                        ok = False
                        continue
                    flags = error_flags(err)
                    low = arm == "follower" and v / 10 < min_volt
                    if flags or low:
                        ok = False
                        print(f"   {name:14} {v/10:.1f}V  PROBLEM: "
                              f"{','.join(flags)}{' LOW_VOLTAGE' if low else ''}")
        except Exception as e:  # noqa: BLE001
            print(f"   could not open bus: {e}")
            ok = False
    print("preflight:", "PASS" if ok else "FAIL")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description="Brownout-safe teleoperation")
    ap.add_argument("--clamp", type=float, default=8.0,
                    help="max_relative_target degrees per cycle (current cap)")
    ap.add_argument("--no-clamp", action="store_true", help="disable motion clamp")
    ap.add_argument("--check-only", action="store_true", help="run preflight then exit")
    ap.add_argument("--skip-preflight", action="store_true")
    args = ap.parse_args()

    if not args.skip_preflight:
        if not _preflight():
            print("\nAborting: fix the issues above (see soarm-scan) before teleoperating.")
            raise SystemExit(1)
    if args.check_only:
        return

    cfg = load_config()
    f, l = cfg["follower"], cfg["leader"]
    cmd = [
        "lerobot-teleoperate",
        "--robot.type=so101_follower", f"--robot.port={f.port}", f"--robot.id={f.id}",
        "--teleop.type=so101_leader", f"--teleop.port={l.port}", f"--teleop.id={l.id}",
    ]
    if not args.no_clamp:
        cmd.append(f"--robot.max_relative_target={args.clamp}")
    print("\nlaunching:", " ".join(cmd), "\n")
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
