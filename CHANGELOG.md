# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0](https://github.com/andymai/so-arm101/compare/soarm101-v0.1.0...soarm101-v0.2.0) (2026-06-09)


### Features

* recenter --verify, soarm-record, sim assets; doc upgrades ([5f6edb1](https://github.com/andymai/so-arm101/commit/5f6edb1c99afb562bd040329f62b5c0c0d479dc7))
* soarm-find-port — auto-detect follower/leader by supply voltage ([8302ea7](https://github.com/andymai/so-arm101/commit/8302ea7f5b092b6b4792b2c0eaa5e4cc87fbd68c))


### Bug Fixes

* resolve lerobot-* CLIs next to the interpreter for subprocess calls ([ac7c7ca](https://github.com/andymai/so-arm101/commit/ac7c7ca5f8b359e8c9029cbcf6106fa49cb8c522))

## [Unreleased]

### Added
- `soarm-find-port`: auto-detect which port is follower (~12 V) vs leader (~5 V) by
  supply voltage; `--write` updates `config.toml` in place (preserving comments).
- `tests/`: pytest suite for the pure logic (sign-magnitude codecs, present-position
  decode, `fold_homing`, `error_flags`, `resolve_arm`, config/motor-map invariants,
  cameras-arg, port classification + config rewrite, CLI resolution). CI runs it.
- `recenter --verify` now skips the continuous wrist_roll and flags bounded-joint drift
  OK/HIGH against a threshold.

### Repo
- release-please automation (`release-please-config.json` + manifest + workflow),
  Dependabot (uv + github-actions), and git hooks (`.githooks/`: conventional-commit
  gate, pre-commit lint/test + lockfile-drift guard, README reminder) installed via
  `just hooks`.

### Fixed
- `soarm-record`/`soarm-teleop` resolve `lerobot-*` CLIs next to the interpreter, so
  subprocess calls work without the venv on PATH (`uv run`, direct path, pipx).
- `record`: validate `--camera NAME=INDEX` instead of producing a malformed draccus dict.
- `sim/fetch.py`: guard `extractfile()` returning `None`; add a path-traversal check.
- `soarm-recenter --verify`: after the "set middle" write, torque the joint to goal 2048
  and report drift, confirming the recenter physically held.
- `soarm-record`: preflight-checked wrapper over `lerobot-record` with a simple camera
  spec (`--camera name=index`) for collecting teleoperated demonstrations.
- `sim/`: `fetch.py` downloads the SO-101 URDF + MuJoCo MJCF assets (TheRobotStudio,
  Apache-2.0) on demand; README documents the new-calibration convention.
- `docs/PHONE_TELEOP.md`: rationale for deferring phone/leader-less teleop (requires the
  LeRobot 0.5.x end-effector pipeline; deferred while the encoder-seam bug is unfixed).
- `bus.read()` retries transient packet drops so a flaky bus doesn't produce false
  NO RESPONSE / preflight failures.

### Changed
- `bus`: reads that feed persisted calibration (`value`, `present_position`, `homing_offset`)
  raise `BusCommError` on dropout instead of silently returning 0; EEPROM writes use
  `write_checked`; display paths degrade to `--`.
- `soarm-set-protection`: verified writes with per-motor failure tracking and a nonzero exit.
- README: power-supply guidance (official 12V 2A is the brownout risk; 12V 5A recommended);
  recording section; deferred-phone-teleop note.

## [0.1.0]

Initial toolkit: `soarm-scan`, `soarm-sync-check`, `soarm-recenter`, `soarm-fix-voltage-limit`,
`soarm-calibrate-leader` (seam-safe), `soarm-set-protection`, `soarm-teleop` (preflight +
motion clamp), `soarm-calib`. Shared Feetech STS3215 bus library. Documents the four
hardware gotchas (board jumper+power, voltage-limit lockout, encoder-seam calibration
overflow, desync-driven brownout).
