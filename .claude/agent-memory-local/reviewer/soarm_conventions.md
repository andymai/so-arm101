---
name: soarm-conventions
description: Non-obvious conventions and invariants in the soarm SO-ARM101 CLI package
metadata:
  type: project
---

soarm/ is a CLI toolkit for the Seeed SO-ARM101 arm via LeRobot, talking to Feetech STS3215 servos over serial.

Key invariants and gotchas (verified against the scservo_sdk + lerobot installed in .venv, python 3.10):

- `Bus.read()` (bus.py) wraps scservo_sdk `read1/2ByteTxRx`, which return `(data, comm_result, error)`. `COMM_SUCCESS == 0`. `Bus.COMM_FAIL == -1`. On a serial exception `Bus.read` returns `(0, -1, 0)`. So a successful comm is `comm == 0`; any nonzero comm means failure.
- `Bus.value()` discards comm+error and returns only `data`, so a failed read silently yields 0. Callers that compute on `.value()` (protect._dump, fix_voltage_limit verify loop, homing_offset) cannot distinguish a real 0 from a dropout. This is the recurring correctness weak spot.
- `Bus.write()` returns the comm result but NO caller checks it — EEPROM writes are fire-and-forget except the explicit verify loop in fix_voltage_limit.
- EEPROM writes require Lock=0 then Lock=1; use `Bus.unlocked()` context manager. Recenter uses Feetech 'set middle' (Torque_Enable=128).
- Homing_Offset register is 11-bit magnitude + sign at bit 11 (max |value| 2047). encode_sign_magnitude raises ValueError at >=2048.
- `devices.follower()/leader()` set calibration_dir=None, which LeRobot resolves to the standard HF cache dir — the SAME path calib_io.leader_cache()/follower_cache() compute. So calibrate_leader's write-JSON-then-reload flow is consistent by design (not a bug).
- Exit-code convention: scan.py and sync_check.py raise SystemExit(1) on problems; most other tools do not set nonzero exit on failure.
- Hardware is never available in review; reason statically against the .venv SDK source.
