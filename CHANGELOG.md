# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
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
