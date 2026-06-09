# Simulation assets (SO-101)

URDF + MuJoCo MJCF models for the SO-101, used for visual calibration checking and
policy evaluation. They are **not vendored** here (third-party CAD meshes with their own
license) — fetch them on demand:

```bash
python sim/fetch.py        # downloads into sim/SO101/ (gitignored)
```

Then view in MuJoCo:

```bash
python -m mujoco.viewer --mjcf sim/SO101/so101_new_calib.xml
```

## Two calibration conventions

Upstream ships two zero conventions — match the one your calibration uses:

- **`so101_new_calib`** — each joint's zero is the **middle of its range**. This matches
  this toolkit's approach (`soarm-recenter` / `soarm-calibrate-leader` recenter each joint
  to 2048). **Use this one.**
- `so101_old_calib` — zero is the horizontal/extended pose. Older convention.

## Attribution

Assets © [TheRobotStudio / SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100),
Apache-2.0, generated from the Onshape CAD. Downloaded by `sim/fetch.py`; not redistributed
in this repo.
