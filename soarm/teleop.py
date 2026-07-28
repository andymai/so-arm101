"""soarm-teleop: brownout-safe teleoperation launcher.

Runs a preflight health check on BOTH arms (all motors respond, no error bits,
voltages sane), then launches lerobot-teleoperate with a motion clamp
(--robot.max_relative_target) to cap per-cycle current spikes.

Note: the motion clamp is for *teleop* on a marginal supply. Do NOT reuse the same
clamp during lerobot-record or policy eval — it clamps legitimate fast actions too and
silently degrades the recorded/executed motion. Record with a beefier supply instead.

Examples:
    soarm-teleop                 # preflight + clamped teleop
    soarm-teleop --clamp 12      # looser clamp (faster, more current)
    soarm-teleop --no-clamp      # disable the clamp
    soarm-teleop --check-only    # run preflight and exit
"""

from __future__ import annotations

import datetime
import subprocess
import sys
from pathlib import Path

from .bus import MOTORS, Bus, error_flags, lerobot_cli, load_config

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


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


def run(clamp: float = 8.0, no_clamp: bool = False, check_only: bool = False,
        skip_preflight: bool = False) -> None:
    if not skip_preflight and not _preflight():
        print("\nAborting: fix the issues above (see `soarm scan`) before teleoperating.")
        raise SystemExit(1)
    if check_only:
        return

    cfg = load_config()
    f, lead = cfg["follower"], cfg["leader"]
    cmd = [
        lerobot_cli("lerobot-teleoperate"),
        "--robot.type=so101_follower", f"--robot.port={f.port}", f"--robot.id={f.id}",
        "--teleop.type=so101_leader", f"--teleop.port={lead.port}", f"--teleop.id={lead.id}",
    ]
    if not no_clamp:
        cmd.append(f"--robot.max_relative_target={clamp}")
    print("\nlaunching:", " ".join(cmd), "\n")
    raise SystemExit(_run_logged(cmd))


def _run_logged(cmd: list[str]) -> int:
    """Run teleop, teeing output to a timestamped log. On a nonzero exit (teleop died —
    which drops torque on the whole arm), run a post-mortem so an intermittent 'goes limp'
    is self-documenting: the log holds the death traceback AND the motor state at failure."""
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    logpath = LOG_DIR / f"teleop-{stamp}.log"
    print(f"logging to {logpath}\n")
    with open(logpath, "w") as log:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
        rc = proc.wait()
        if rc != 0:
            _post_mortem(log)
    return rc


def _post_mortem(log) -> None:
    """Read every motor's voltage/temp/error bits right after teleop died. A latched
    OVERLOAD/OVERHEAT bit or high temp => protection tripped (not power); all-clean with a
    'no status packet' traceback => comm timeout under load; a VOLTAGE bit => supply."""
    def emit(line: str) -> None:
        sys.stdout.write(line + "\n")
        log.write(line + "\n")

    emit("\n=== soarm-teleop post-mortem (teleop exited non-zero; arm torque is now off) ===")
    cfg = load_config()
    for arm in ("follower", "leader"):
        try:
            with Bus(cfg[arm].port) as bus:
                for mid, name in MOTORS.items():
                    v, comm, err = bus.read(mid, "Present_Voltage")
                    if comm != 0:
                        emit(f"  [{arm}] {name:14} NO RESPONSE")
                        continue
                    t, _, _ = bus.read(mid, "Present_Temperature")
                    flags = ",".join(error_flags(err)) or "ok"
                    temp = f"{t}C" if isinstance(t, int) else "--"
                    emit(f"  [{arm}] {name:14} {v / 10:>5.1f}V {temp:>4}  {flags}")
        except Exception as e:  # noqa: BLE001 — diagnostics must not raise
            emit(f"  [{arm}] bus unavailable: {e}")
    emit("=== end post-mortem — share this log to diagnose the limp ===")
