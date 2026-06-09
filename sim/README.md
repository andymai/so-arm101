# Simulation assets (SO-101)

URDF + MuJoCo MJCF models for the SO-101, used for visual calibration checking and
policy evaluation. They are **not vendored** here (third-party CAD meshes with their own
license) — fetch them on demand.

```bash
uv sync --extra sim       # install mujoco + glfw (the `sim` optional group)
python sim/fetch.py       # downloads into sim/SO101/ (gitignored)
```

Then view in MuJoCo:

```bash
python sim/view.py                # interactive: orbit/pan/zoom (scene.xml, lit + floor)
python sim/view.py --sweep        # drive each joint through its range (calibration check)
python sim/view.py sim/SO101/so101_old_calib.xml   # compare the old-calib zero
```

> **Why not `python -m mujoco.viewer`?** On macOS that requires the `mjpython`
> trampoline, which relaunches into the system *framework* Python and crashes inside
> `_Simulate` ("Caught an unknown exception!") on a uv/venv whose interpreter isn't a
> framework build. `sim/view.py` drives the GLFW render loop directly from the venv —
> no `mjpython` — so it works. Point the viewer at `scene.xml` (not the bare
> `so101_*_calib.xml`); the robot-only files have no lights or floor and render black.

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
