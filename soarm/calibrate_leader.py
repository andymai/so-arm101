"""soarm-calibrate-leader: seam-safe manual calibration for the leader arm.

Why not `lerobot-calibrate`? Its first step zeroes every Homing_Offset, which re-exposes
the raw encoder frame. On the leader, several joints' ranges straddle the 0/4095 encoder
seam, so the homing math overflows the 11-bit field and calibration aborts. This tool
instead recenters each joint (Feetech 'set middle') so ranges sit mid-scale off the seam,
sweeps the ranges, and writes the calibration directly — preserving the recentering.

Flow (interactive):
  1. Put the WHOLE arm in a neutral pose       -> recenters all joints to 2048
  2. Sweep every joint except wrist_roll        -> records range_min/range_max
  3. Writes calibration JSON + pushes to motors -> is_calibrated == True
  4. (optional) align continuous wrist_roll to the follower

Example:
    soarm-calibrate-leader
    soarm-calibrate-leader --align-wrist-roll   # also sync wrist_roll to follower
"""

from __future__ import annotations

import argparse
import json
import threading
import time

from .bus import (
    CONTINUOUS,
    MOTORS,
    NAME_TO_ID,
    RESOLUTION,
    Bus,
    BusCommError,
    decode_present_position,
    load_config,
)
from .calib_io import leader_cache


def _sweep(bus: Bus, ids: list[int]) -> dict[int, tuple[int, int]]:
    """Record min/max of Present_Position until the user presses Enter."""
    mn = {i: 10**9 for i in ids}
    mx = {i: -(10**9) for i in ids}
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            for i in ids:
                data, comm, _ = bus.read(i, "Present_Position")
                if comm != 0:
                    continue  # drop the sample on a transient dropout, never record 0
                p = decode_present_position(data)
                if 0 <= p <= RESOLUTION - 1:
                    mn[i] = min(mn[i], p)
                    mx[i] = max(mx[i], p)
            time.sleep(0.02)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    input("  move every joint except wrist_roll through its FULL range, then press Enter...")
    stop.set()
    t.join()
    return {i: (mn[i], mx[i]) for i in ids}


def main() -> None:
    ap = argparse.ArgumentParser(description="Seam-safe manual leader calibration")
    ap.add_argument("--align-wrist-roll", action="store_true",
                    help="also align continuous wrist_roll zero to the follower")
    args = ap.parse_args()

    cfg = load_config()["leader"]
    swept_ids = [i for i in MOTORS if MOTORS[i] not in CONTINUOUS]

    # 1 + 2: recenter, then sweep ranges (raw bus)
    with Bus(cfg.port) as bus:
        input("Put the leader in a clean NEUTRAL pose (all joints mid-travel), press Enter...")
        try:
            for mid in MOTORS:
                bus.recenter(mid)
            print("recentered all joints to 2048.")
            ranges = _sweep(bus, swept_ids)
            bad = [MOTORS[i] for i, (lo, hi) in ranges.items() if hi - lo < 200]
            if bad:
                raise SystemExit(f"insufficient range captured for {bad} — sweep each joint "
                                 "fully (or check the bus); not writing a bad calibration.")
            homings = {mid: bus.homing_offset(mid) for mid in MOTORS}
        except BusCommError as e:
            raise SystemExit(f"bus dropout during calibration ({e}); not writing a partial "
                             "calibration — retry.")

    # 3: build calibration dict (wrist_roll is continuous -> full range)
    calib = {}
    for mid, name in MOTORS.items():
        rmin, rmax = (0, RESOLUTION - 1) if name in CONTINUOUS else ranges[mid]
        calib[name] = {"id": mid, "drive_mode": 0,
                       "homing_offset": homings[mid], "range_min": rmin, "range_max": rmax}
    path = leader_cache()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(calib, indent=4))
    print(f"\nwrote {path}")
    for name, c in calib.items():
        print(f"  {name:14} homing={c['homing_offset']:>6} range=[{c['range_min']},{c['range_max']}]")

    # push to motors so is_calibrated == True
    from .devices import leader
    with leader() as l:
        l.bus.write_calibration(l.bus.calibration)
        print("\nis_calibrated:", l.is_calibrated)

    if args.align_wrist_roll:
        _align_wrist_roll()


def _align_wrist_roll() -> None:
    """Shift leader wrist_roll homing so it matches the follower at a common pose."""
    from .devices import follower, follower_positions, leader, leader_positions

    input("\nAlign BOTH wrist_rolls to the same physical orientation, then press Enter...")

    # read both arms' normalized wrist_roll + the leader's current homing
    with follower() as f, leader() as l:
        fpos = follower_positions(f)["wrist_roll"]
        lpos = leader_positions(l)["wrist_roll"]
        cur = l.bus.calibration["wrist_roll"].homing_offset

    # to raise leader by (fpos - lpos) degrees we lower homing by that many counts
    diff_deg = fpos - lpos
    new = cur - round(diff_deg * RESOLUTION / 360)
    # continuous joint: shifting by a full turn is physically identical, so fold the
    # correction into the +/-2047 window the Homing_Offset register can store
    while new > 2047:
        new -= RESOLUTION
    while new < -2047:
        new += RESOLUTION

    # apply to the motor EEPROM and update the calibration JSON
    wid = NAME_TO_ID["wrist_roll"]
    with Bus(load_config()["leader"].port, ids=[wid]) as bus:
        bus.set_homing_offset(wid, new)
    path = leader_cache()
    calib = json.loads(path.read_text())
    calib["wrist_roll"]["homing_offset"] = new
    path.write_text(json.dumps(calib, indent=4))
    print(f"wrist_roll aligned: homing {cur} -> {new} (diff {diff_deg:.1f} deg). "
          "re-run soarm-sync-check to verify.")


if __name__ == "__main__":
    main()
