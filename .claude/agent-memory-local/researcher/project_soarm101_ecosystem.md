---
name: soarm101-ecosystem
description: Non-obvious findings on the SO-ARM101 / LeRobot ecosystem relevant to the so-arm101 toolkit (versions, known bugs, power specs)
metadata:
  type: project
---

Research findings (as of 2026-06-08) on how the upstream SO-ARM/LeRobot ecosystem relates to the local `soarm-*` toolkit at /Users/andy/git/so-arm101.

**Why:** the toolkit was built to fix 4 hardware gotchas; this records which are still unsolved upstream so we know our tools remain load-bearing.
**How to apply:** when the user asks about upgrading LeRobot or adopting upstream features, consult these.

- Toolkit pins `lerobot[feetech]>=0.4.4`. Current upstream is **v0.5.x** (v0.5.0 = "Scaling Every Dimension", v0.5.1 exists). v0.5.0 unified SO-100/SO-101 into one codebase. Import paths changed: `lerobot.robots.so_follower.SO101Follower`, `lerobot.teleoperators.so_leader.SO101Leader`. Upgrading is NOT free — verify devices.py/bus.py imports still resolve.
- **Our gotcha #3 (encoder-seam / "Magnitude N exceeds 2047") is STILL UNSOLVED upstream as of v0.5.1** — open issue huggingface/lerobot#3193 (Mar 2026). `set_half_turn_homings()` in motors_bus.py still writes homing to continuous wrist_roll without ensuring it's near 2048, and leader/follower wrist_roll zeros still don't correspond. Our `soarm-calibrate-leader` + `soarm-recenter` remain the better fix.
- **Feetech "set middle" confirmed:** writing 128 (decimal) to Torque_Enable (addr 40) one-key-corrects current physical position to 2048. Matches our `SET_MIDDLE=128` in bus.py exactly. (Source: Feetech manual via search; Waveshare ST3215 wiki.)
- **LeRobot config defaults:** `SO101FollowerConfig.max_relative_target` default = `None` (no clamp); `disable_torque_on_disconnect` default = `True`. No official recommended numeric for max_relative_target (issue #1483 went unanswered). Our teleop clamp default of 8 deg/cycle is a reasonable home-grown value.
- **Power supply:** Seeed SO-ARM101 Pro follower is officially spec'd **12V 2A** (matches our README/config), but Seeed sells a 12V 5A adapter and TheRobotStudio README says 12V variant wants "12V 5A+". Our brownout was on 12V 2A — the headroom note in our README is correct.
- **Seeed's own tool repo:** github.com/Seeed-Projects/Seeed_RoboController has servo_middle_calibration.py (= our recenter), servo_disable.py, servo_center_test.py, servo_remote_control.py (dual-port teleop), scan_id.py, change_single_servo_id.py, servo_angle_limit_set.py (GUI). Overlaps our toolkit; servo_center_test (drift-after-recenter verification) is the one idea we lack.
- **No gravity compensation** exists for SO-101 in LeRobot (the 5V/differently-geared leader is the mechanical substitute). Don't promise it.
- LeRobot now has **phone teleop** (`lerobot[phone]`, iOS HEBI Mobile I/O / Android WebXR) — leader-less EE control via IK (Placo/Pinocchio). Needs the SO101 URDF from TheRobotStudio/SO-ARM100/Simulation/SO101.
- Dataset format is **v3.0** (multi-episode-per-file, streaming); `lerobot-edit-dataset` CLI exists for split/merge/delete-episode.
