# SO-ARM101 toolkit — common commands. Run `just` to list.

default:
    @just --list

# Install / sync the environment (uv)
sync:
    uv sync

# Install the git hooks (conventional-commit gate + pre-commit lint/test)
hooks:
    git config core.hooksPath .githooks
    @echo "git hooks installed (core.hooksPath = .githooks)"

# Import smoke test — the de-facto correctness check (no hardware needed)
check:
    uv run python -c "import soarm.cli, soarm.console, soarm.viz, soarm.fetch, soarm.scan, soarm.sync_check, soarm.recenter, soarm.fix_voltage_limit, soarm.calibrate_leader, soarm.protect, soarm.teleop, soarm.record, soarm.calib_io, soarm.bus, soarm.devices; print('imports OK')"

# Run the test suite (pure logic; no hardware needed)
test:
    uv run pytest -q

# Lint
lint:
    uv run ruff check soarm tests

# Bus health for an arm:  just scan follower
scan arm="follower":
    uv run soarm scan --arm {{arm}}

# Compare leader/follower joint sync (hold both in the same pose)
sync-check:
    uv run soarm sync-check

# Brownout-safe teleoperation (preflight + motion clamp)
teleop:
    uv run soarm teleop

# Record demonstrations:  just record "pick up the cube" 30
record task episodes="30":
    uv run soarm record --task "{{task}}" --episodes {{episodes}}

# Apply moderate brownout protection to the follower
protect:
    uv run soarm set-protection --arm follower

# Back up / restore calibration between repo and LeRobot cache
backup:
    uv run soarm calib backup
restore:
    uv run soarm calib restore

# Fetch the SO-101 URDF + meshes for visualization (Rerun)
fetch:
    uv run soarm fetch

# Offline Rerun viewer (neutral pose; `just view sweep` to sweep joints)
view mode="":
    uv run soarm view {{ if mode == "sweep" { "--sweep" } else { "" } }}

# Live digital twin: overlay leader (ghost) on follower, plot sync
twin:
    uv run soarm twin --live

# Replay a recorded episode:  just replay ./outputs/my_dataset 0
replay dataset episode="0":
    uv run soarm replay "{{dataset}}" --episode {{episode}}
