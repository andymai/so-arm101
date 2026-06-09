# SO-ARM101 toolkit — common commands. Run `just` to list.

default:
    @just --list

# Install / sync the environment (uv)
sync:
    uv sync

# Import smoke test — the de-facto correctness check (no hardware needed)
check:
    uv run python -c "import soarm.scan, soarm.sync_check, soarm.recenter, soarm.fix_voltage_limit, soarm.calibrate_leader, soarm.protect, soarm.teleop, soarm.record, soarm.calib_io, soarm.bus, soarm.devices; print('imports OK')"

# Lint (if ruff is available)
lint:
    uvx ruff check soarm

# Bus health for an arm:  just scan follower
scan arm="follower":
    uv run soarm-scan --arm {{arm}}

# Compare leader/follower joint sync (hold both in the same pose)
sync-check:
    uv run soarm-sync-check

# Brownout-safe teleoperation (preflight + motion clamp)
teleop:
    uv run soarm-teleop

# Record demonstrations:  just record "pick up the cube" 30
record task episodes="30":
    uv run soarm-record --task "{{task}}" --episodes {{episodes}}

# Apply moderate brownout protection to the follower
protect:
    uv run soarm-set-protection --arm follower

# Back up / restore calibration between repo and LeRobot cache
backup:
    uv run soarm-calib backup
restore:
    uv run soarm-calib restore

# Fetch SO-101 simulation assets (URDF + MuJoCo MJCF)
fetch-sim:
    uv run python sim/fetch.py
