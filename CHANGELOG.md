# Changelog

All notable changes to this project are documented here.
Releases are managed by [release-please](https://github.com/googleapis/release-please)
from Conventional Commits; entries below the latest are generated on release.

## [0.3.0](https://github.com/andymai/so-arm101/compare/soarm101-v0.2.1...soarm101-v0.3.0) (2026-06-10)


### ⚠ BREAKING CHANGES

* the soarm-scan / soarm-teleop / soarm-* entry points are removed. Use `soarm <subcommand>` instead (run `soarm --help`).

### Features

* cross-platform serial support (Linux + macOS) ([639ddfd](https://github.com/andymai/so-arm101/commit/639ddfd06847bac873641c525068658943d3dc56))
* **ports:** detect controller boards on Linux (ttyACM/ttyUSB) ([e742495](https://github.com/andymai/so-arm101/commit/e7424959bc9022e203c9c8753617491187c5972e))
* **sim:** add mjpython-free viewer with joint sweep ([babe128](https://github.com/andymai/so-arm101/commit/babe128326e9a377d321fe5085e9f253e4cf292d))
* **teleop:** log to file + post-mortem on exit to diagnose limps ([001ab26](https://github.com/andymai/so-arm101/commit/001ab26c6ba273980413b215ed1494a9c869d11b))
* unify into a single soarm Typer CLI ([e439f3a](https://github.com/andymai/so-arm101/commit/e439f3a13ecb6cc4504ff293a107fc57bcbc7574))
* **viz:** Rerun digital twin, episode replay, and offline viewer ([becda24](https://github.com/andymai/so-arm101/commit/becda24e2166de06bb5241d5747105400bcf4442))


### Bug Fixes

* **deps:** override diffusers to &gt;=0.38.0 (two high-severity RCE bypasses) ([998bdbe](https://github.com/andymai/so-arm101/commit/998bdbe49a54c52dd49278a36607bf34ffd842b0))
* **deps:** patch diffusers RCE bypasses (override to &gt;=0.38.0) ([d8a3096](https://github.com/andymai/so-arm101/commit/d8a30967aa491b2578404fab43e56a3dabcf683e))


### Documentation

* document Linux serial access (dialout group) ([2cf8f78](https://github.com/andymai/so-arm101/commit/2cf8f783d68d7f0fe13fe57c138a4f002d45465f))
* rearchitect for the unified soarm CLI + Rerun viz ([5668e56](https://github.com/andymai/so-arm101/commit/5668e56d9fcae32bf422d213220971facbbe18ce))

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
