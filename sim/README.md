# Visualization assets (SO-101)

URDF + meshes for the SO-101, used by the `soarm` visualization commands (`twin`, `view`,
`replay`), which render in [Rerun](https://rerun.io). They are **not vendored** here
(third-party CAD meshes with their own license) — fetch them on demand:

```bash
soarm fetch        # downloads into sim/SO101/ (gitignored)
```

Then:

```bash
soarm view                 # the arm at its neutral pose
soarm view --sweep         # sweep each joint through its range (visual calibration check)
soarm twin --live          # live digital twin: leader (ghost) over follower
soarm replay <dataset>     # play back a recorded LeRobot episode
```

## Why the `_new_calib` URDF

Upstream ships two zero conventions; the toolkit uses **`so101_new_calib.urdf`** (the
default), whose joint zeros are the **middle of each joint's range** — matching
`soarm recenter` / `soarm calibrate-leader`, which recenter each joint to encoder 2048.
The `so101_old_calib` variant (zero = horizontal/extended pose) is the older convention.
Pass `--urdf sim/SO101/so101_old_calib.urdf` to any viz command to compare.

> The renderer is kinematics-only (FK via [yourdfpy](https://github.com/clemense/yourdfpy),
> logged to Rerun) — no physics. That's exactly right for calibration checking, the digital
> twin, and dataset replay. `wrist_roll` is continuous on the real arm but bounded in the
> URDF, so trust the twin for the five bounded joints; verify the seam on hardware with
> `soarm recenter --align-wrist-roll`.

## Attribution

Assets © [TheRobotStudio / SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100),
Apache-2.0, generated from the Onshape CAD. Downloaded by `soarm fetch`; not redistributed
in this repo.
