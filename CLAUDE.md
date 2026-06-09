# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A CLI toolkit (`soarm-*` commands) for bringing up a **Seeed SO-ARM101** robot arm
(leader + follower) on LeRobot. It exists because a real build hit four non-obvious
hardware failures; each tool encodes the fix. See `README.md` for the four gotchas
(board jumper+power, voltage-limit lockout, encoder-seam calibration overflow,
desync-driven current brownout) — that context explains *why* the code is shaped as it is.

## Commands

```bash
uv sync                       # create .venv + install (pinned via uv.lock)
source .venv/bin/activate
```

There is **no test suite or linter configured**. The de-facto correctness check after
any edit is an import smoke test (catches the most common breakage):

```bash
.venv/bin/python -c "import soarm.scan, soarm.sync_check, soarm.recenter, soarm.fix_voltage_limit, soarm.calibrate_leader, soarm.protect, soarm.teleop, soarm.calib_io, soarm.bus, soarm.devices"
```

Most tools require the physical arms connected (serial ports). Static edits can only
be import-checked; real behavior must be verified on hardware. The CLIs (entry points
in `pyproject.toml`): `soarm-scan`, `soarm-find-port`, `soarm-sync-check`, `soarm-recenter`,
`soarm-fix-voltage-limit`, `soarm-calibrate-leader`, `soarm-set-protection`,
`soarm-teleop`, `soarm-record`, `soarm-calib`. Most take `--arm follower|leader` or `--port`.
Common workflows are also wrapped in a `justfile` (`just check`, `just scan`, `just teleop`,
`just record "task" 30`).

## Architecture (the parts that span files)

**`soarm/bus.py` is the foundation.** It wraps LeRobot's `FeetechMotorsBus` but reaches
through to the low-level `packet_handler`. This is deliberate: LeRobot's high-level
`read`/`write` *raise on a motor's error bit*, which makes a motor that is *in* an error
state (e.g. over-voltage lockout) impossible to diagnose. The low-level path lets us read
registers regardless of error bits.

**The central invariant — "fail loud on data, degrade on display" — is a three-level
read hierarchy. Preserve it when editing:**
- `read()` — tolerant; returns `(data, comm, err)`, never raises, retries transient
  packet drops (the bus is flaky). For callers that want to *display* health and inspect
  `comm` themselves (e.g. `scan`).
- `read_display()` — returns the value or the string `"--"` on dropout. For tables.
- `value()` / `present_position()` / `homing_offset()` — raise `BusCommError` on dropout.
  Used wherever the result feeds persisted calibration. **A silent `0` from a dropout
  written into calibration is the worst failure mode** — that's why these raise.

Writes mirror this: `write()` is best-effort (returns comm); `write_checked()` raises and
is used for EEPROM-persisted values. EEPROM writes must be wrapped in the `unlocked()`
context manager (sets the `Lock` register to 0, relocks after).

**`soarm/devices.py`** wraps LeRobot's high-level `SOFollower`/`SOLeader` to read
*normalized* joint positions (degrees; gripper 0–100) — this is the leader↔follower
comparison space used by `sync-check`. Note the construction quirk: the config dataclasses
don't expose `id`/`calibration_dir` as fields, so they're set as attributes after
construction (`cfg.id = ...; cfg.calibration_dir = None`); `None` resolves to LeRobot's
default cache path.

**Calibration data lives in two places that must stay in sync.** The source of truth at
runtime is LeRobot's cache (`~/.cache/huggingface/lerobot/calibration/...`, also mirrored
to motor EEPROM). `soarm/calib_io.py` backs those JSONs up into `calibration/` in the repo.
**Critical:** changing a motor's homing/limits means writing BOTH the motor EEPROM AND the
calibration JSON — LeRobot writes the JSON's values back to the motor on every `connect()`,
so a motor-only change is silently reverted.

**`soarm-calibrate-leader` deliberately bypasses `lerobot-calibrate`.** The standard tool
zeroes every homing offset first, which re-exposes the raw encoder frame; on the leader,
joints straddle the 0/4095 encoder seam and the homing math overflows LeRobot's 11-bit
field. This tool instead recenters each joint (`torque=128` "set middle"), sweeps ranges,
and writes the calibration JSON directly, preserving the recentering.

## Hardware encoding facts (load-bearing)

- `Homing_Offset` is **sign-magnitude, 11-bit magnitude (±2047)**. `encode/decode_sign_magnitude`.
- `Present_Position` is **sign-magnitude in a 16-bit field (bit 15 = sign)**. `decode_present_position`.
- `wrist_roll` is the only **continuous** joint (`CONTINUOUS` in `bus.py`): no hard stops,
  homing-defined zero, full 0–4095 range. Its normalized value is discontinuous at the
  seam; calibration parks the seam ~180° from the rest orientation so normal motion never
  crosses it. Bounded joints self-sync via `range_min`/`range_max`; the continuous joint's
  zero must be aligned explicitly.
- Follower runs at **12 V**, leader at **5 V** — do not swap the supplies.

## When editing

- Keep the domain-knowledge comments/docstrings — they record real hardware gotchas, not
  narration.
- Ports in `soarm/config.toml` are macOS `usbmodem` paths and can change on replug;
  every tool accepts `--port` to override.
