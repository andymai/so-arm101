# Changelog

All notable changes to this project are documented here.
Releases are managed by [release-please](https://github.com/googleapis/release-please)
from Conventional Commits; entries below the latest are generated on release.

## [0.3.0](https://github.com/andymai/so-arm101/compare/soarm101-v0.2.1...soarm101-v0.3.0) (2026-07-16)


### ⚠ BREAKING CHANGES

* the soarm-scan / soarm-teleop / soarm-* entry points are removed. Use `soarm <subcommand>` instead (run `soarm --help`).

### Features

* cross-platform serial support (Linux + macOS) ([995567b](https://github.com/andymai/so-arm101/commit/995567bc8cf1dd7275ca5d74866cf85385c74452))
* **ports:** detect controller boards on Linux (ttyACM/ttyUSB) ([facb928](https://github.com/andymai/so-arm101/commit/facb928d1b4685babdbd8035fc3445334c3f8687))
* **sim:** add mjpython-free viewer with joint sweep ([0c3a4e1](https://github.com/andymai/so-arm101/commit/0c3a4e1a6128e854106c880a49332c1b5b241431))
* **teleop:** log to file + post-mortem on exit to diagnose limps ([d08e27b](https://github.com/andymai/so-arm101/commit/d08e27bac6eb9cb88ed53199b29b57282e775fc2))
* unify into a single soarm Typer CLI ([520e989](https://github.com/andymai/so-arm101/commit/520e989f758faa66a821b03fb82b62be8d20faf3))
* **viz:** Rerun digital twin, episode replay, and offline viewer ([17aded1](https://github.com/andymai/so-arm101/commit/17aded1d4a5643154dbba1edc7d513c34aa39efb))


### Bug Fixes

* **deps:** override diffusers to &gt;=0.38.0 (two high-severity RCE bypasses) ([1b08529](https://github.com/andymai/so-arm101/commit/1b08529e2c5926899b30e6cfdc1e6c8f8074d88f))
* **deps:** patch diffusers RCE bypasses (override to &gt;=0.38.0) ([3ffb282](https://github.com/andymai/so-arm101/commit/3ffb2826cfe9540ebbddd3c56ef626b2a927848d))


### Documentation

* document Linux serial access (dialout group) ([9767d82](https://github.com/andymai/so-arm101/commit/9767d820ff5a870b10df95ebcfd5e2e0bcb0158e))
* rearchitect for the unified soarm CLI + Rerun viz ([c64295b](https://github.com/andymai/so-arm101/commit/c64295b41968cb355436afea0bb8fd4df9652625))

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
