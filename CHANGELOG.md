# Changelog

All notable changes to this project are documented here.
Releases are managed by [release-please](https://github.com/googleapis/release-please)
from Conventional Commits; entries below the latest are generated on release.

## [0.2.1](https://github.com/andymai/so-arm101/compare/soarm101-v0.2.0...soarm101-v0.2.1) (2026-06-09)


### Documentation

* tidy changelog into release-please format ([f7e3f42](https://github.com/andymai/so-arm101/commit/f7e3f42cc8c56cfed7b410fd23bbaf1d235cf062))

## [0.2.0](https://github.com/andymai/so-arm101/compare/soarm101-v0.1.0...soarm101-v0.2.0) (2026-06-09)

### Features

* `soarm-find-port` — auto-detect follower/leader by supply voltage; `--write` updates `config.toml` ([8302ea7](https://github.com/andymai/so-arm101/commit/8302ea7f5b092b6b4792b2c0eaa5e4cc87fbd68c))
* `soarm-record` — preflight-checked `lerobot-record` wrapper with a `--camera NAME=INDEX` spec ([5f6edb1](https://github.com/andymai/so-arm101/commit/5f6edb1c99afb562bd040329f62b5c0c0d479dc7))
* `soarm-recenter --verify` — confirm a recenter physically held (reports drift), skipping the continuous wrist_roll
* `sim/fetch.py` — on-demand SO-101 URDF + MuJoCo MJCF assets (TheRobotStudio, Apache-2.0)
* pytest suite (42 tests) wired into CI; release-please, Dependabot, and git hooks added

### Bug Fixes

* resolve `lerobot-*` CLIs next to the interpreter so subprocess calls work without the venv on PATH ([ac7c7ca](https://github.com/andymai/so-arm101/commit/ac7c7ca5f8b359e8c9029cbcf6106fa49cb8c522))
* `bus`: raise `BusCommError` on a read dropout instead of silently returning 0 (calibration-corruption guard); `write_checked` for EEPROM; `read()` retries transient packet drops
* `record`: validate `--camera NAME=INDEX`; `sim/fetch.py`: guard `extractfile()` returning `None` + path-traversal check
* `soarm-set-protection`: verified writes with per-motor failure tracking and a nonzero exit

## [0.1.0]

Initial toolkit: `soarm-scan`, `soarm-sync-check`, `soarm-recenter`, `soarm-fix-voltage-limit`,
`soarm-calibrate-leader` (seam-safe), `soarm-set-protection`, `soarm-teleop` (preflight +
motion clamp), `soarm-calib`. Shared Feetech STS3215 bus library. Documents the four
hardware gotchas (board jumper+power, voltage-limit lockout, encoder-seam calibration
overflow, desync-driven brownout).
