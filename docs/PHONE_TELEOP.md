# Phone / leader-less teleop — status: DEFERRED (blocked on LeRobot 0.5.x)

Goal: control the follower from a phone (iOS HEBI Mobile I/O or Android WebXR) via inverse
kinematics, so you can collect data without a physical leader arm.

## Why it's deferred

Investigated against our pinned **LeRobot 0.4.4**. It is **not viable here** without a major
upgrade:

1. **No SO101 end-effector / IK robot in 0.4.4.** Phone teleop streams a phone *pose* and
   maps it to an end-effector target via IK. That needs an EE-control robot wrapper (EE
   bounds, `max_ee_step_m`, kinematics). In 0.4.4 the robot list has only `so_follower` —
   the EE-control pipeline is a **0.5.x** feature.
2. **The phone teleoperator hard-imports `hebi`** (`teleop_phone.py` fails to import without
   it), and IK needs `placo` + `pin` (pinocchio) — none installed; heavy/uncertain on
   macOS arm64.
3. **Hardware we can't validate** — requires an iOS device with HEBI Mobile I/O (or Android
   WebXR) plus the SO101 URDF (available via `soarm fetch`).

## The blocker: the LeRobot upgrade tradeoff

Enabling this means upgrading to **LeRobot 0.5.x**, which we deliberately avoided:
- 0.5.x changed import paths (would break `soarm/bus.py` / `soarm/devices.py`).
- The encoder-seam calibration bug this toolkit works around is **still open upstream**
  ([#3193](https://github.com/huggingface/lerobot/issues/3193)) — upgrading does not fix it
  and could regress our calibration flow.

## Path forward (when you decide to)

1. Branch, bump `lerobot[feetech]` to 0.5.x **and add `lerobot[phone]`** in `pyproject.toml`.
2. Run the import smoke test; fix `bus.py`/`devices.py` import paths for the consolidated
   SO-100/101 module layout.
3. Re-validate the whole toolkit on hardware (calibration especially — the seam workaround).
4. Add a `soarm teleop-phone` subcommand: reuse `soarm.teleop._preflight`, point IK at
   `sim/SO101/so101_new_calib.urdf`, and reuse the EE safety bounds. Then test with the phone app.

Until then, use the leader arm (`soarm teleop`).
