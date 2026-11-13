# SO-ARM101: setup, repair, and brownout-safe operation

These tools set up, repair, and run a **Seeed Studio SO-ARM101** robot arm (leader + follower) on [LeRobot](https://github.com/huggingface/lerobot) without brownouts. The `soarm` command reads servo health, repairs voltage limits, calibrates the leader when joints cross the encoder seam, and runs teleop with a motion clamp. Its subcommands contain the fixes for [four hardware problems](#the-four-gotchas-and-why-the-tools-exist) from a real build. The [bring-up order](#bring-up-order-from-scratch) lists the setup steps from the start.

> Hardware: 2× controller boards (Seeed Bus Servo Driver Board) and 12× Feetech **STS3215** servos. The follower runs on **12 V**, and the leader runs on **5 V**.

## Quick start

```bash
cd so-arm101
uv sync                       # create .venv, install (pinned via uv.lock)
source .venv/bin/activate

soarm scan --arm follower     # bus health (ids, voltage, temp, errors)
soarm scan --arm leader
soarm teleop                  # preflight checks + brownout-safe teleop
soarm --help                  # all subcommands
```

All tools are subcommands of one `soarm` command (Typer + Rich). Run `soarm --help` to list them, or `soarm <cmd> --help` to see the options of one.

The serial ports are in [`soarm/config.toml`](soarm/config.toml). They are different on each OS: `/dev/tty.usbmodem*` on macOS, and `/dev/ttyACM*` on Linux (`/dev/ttyUSB*` with some adapters). A port can also change when you connect the board again. Run `soarm find-port --write` to find both arms by their supply voltage and write the ports into the config. You can also give `--port` to any tool. On **Linux**, first add yourself to the `dialout` group so that you can open the serial device (see [Linux serial access](#linux-serial-access) below).

### Linux serial access

macOS opens USB serial devices with no special permission. On Linux, only members of the `dialout` group can open `/dev/ttyACM*` and `/dev/ttyUSB*`. Do these steps one time on each machine:

```bash
sudo usermod -aG dialout "$USER"     # add yourself to the serial-device group
# log out and back in (or: newgrp dialout) for the new group to take effect
groups | grep -q dialout && echo "ok: in dialout"
```

If you are not in the group, every hardware command fails with `Permission denied: '/dev/ttyACM0'`. The `uv`/Python toolchain needs no setup for a specific platform. `uv sync`, the tests, and the Rerun visualizers run the same way on macOS and Linux.

## Tools

| Command | What it does |
|---------|--------------|
| `soarm scan` | Per-motor health for one arm: id, voltage, temperature, error bits. `--sweep` for full discovery, `--list-ports` to find boards. |
| `soarm find-port` | Find which port is the follower (~12 V) and which is the leader (~5 V) from the supply voltage. `--write` updates `config.toml`, so after a replug you do not unplug the boards and compare the port lists by hand. |
| `soarm sync-check` | Compare leader vs follower normalized joint positions (hold both in the same pose). Flags joints beyond `--tol`. |
| `soarm recenter` | Set a joint's current pose as encoder center (Feetech `torque=128`). Fixes the encoder-seam problem and aligns continuous joints. |
| `soarm fix-voltage-limit` | Repair/standardize STS3215 `Max/Min_Voltage_Limit` (the wrist_roll over-voltage failure). |
| `soarm calibrate-leader` | Seam-safe manual calibration for the leader (recenter → sweep → write calibration). `--align-wrist-roll` to sync the continuous joint. |
| `soarm set-protection` | Apply *moderate* brownout guardrails to the follower (acceleration cap + uniform voltage/overload limits). It does not weaken holding torque. |
| `soarm teleop` | Preflight health check on both arms, then `lerobot-teleoperate` with a motion clamp. |
| `soarm record` | Preflight-checked dataset recording via `lerobot-record` (see below). |
| `soarm calib` | Back up / restore calibration JSONs between the repo and LeRobot's cache. |
| `soarm twin` | Live **digital twin** in [Rerun](https://rerun.io): overlay the leader (ghost) on the follower, plot leader↔follower sync. `--live` to mirror hardware. |
| `soarm view` | Offline Rerun viewer of the SO-101 at neutral, or `--sweep` each joint (visual calibration check). |
| `soarm replay` | Replay a recorded LeRobot episode in Rerun (joint poses + camera frames). |
| `soarm fetch` | Download the SO-101 URDF + meshes used by the viz tools. |

## The four gotchas (and why the tools exist)

### 1. Board needs a jumper *and* external power

With only the USB cable, the Seeed Bus Servo Driver Board enumerates its USB port. The servos get power only from the **DC barrel jack**. For USB control, you must also fit the **front 2-pin jumper**, because the board does not short these pins by default. Without the jumper and the barrel-jack power, the port appears, but `setup-motors` reports "motor not found".

### 2. A wrong voltage limit bricks a motor onto the bus → `soarm fix-voltage-limit`

One follower servo shipped with `Max_Voltage_Limit = 8.0 V` on a 12 V rail. The motor raised a permanent over-voltage error and **refused all bus traffic**. It looked like a broken daisy chain, not one bad register. To fix it, power the board at a voltage inside the motor's present limit window (for example, 5 V) so that the error clears. Then raise the limit to 16 V. The factory limits are also different from motor to motor, so `soarm fix-voltage-limit` sets the same limits on each motor.

### 3. Encoder seam breaks leader calibration → `soarm recenter` + `soarm calibrate-leader`

On the leader, the ranges of several joints cross the encoder's **0/4095 seam**. Their positions read negative, and LeRobot's homing offset (an 11-bit field, ±2047) overflows. `lerobot-calibrate` then stops with *"Magnitude N exceeds 2047"*. It sets the homing offsets to zero at the start of each run, so another run cannot recover. To fix it, recenter each joint (`torque=128`) so that its range is at mid-scale, away from the seam. Then write the calibration directly.

### 4. Desynced continuous joint → current draw → brownout → `soarm sync-check`, `soarm set-protection`, `soarm teleop`

A continuous joint (wrist_roll) had a calibration with an arbitrary zero and was **111° out of sync**. On each cycle, the follower drove that motor near stall, toward a target that it could not reach. The extra current pushed the 12 V **2 A** supply into brownout: the whole arm went limp, with `id_=1 ... no status packet`. After the sync fix, the brownout stopped. Two guardrails help:

- `soarm set-protection` caps acceleration. This limits current spikes and does not weaken torque.
- `soarm teleop` runs a preflight check and a motion clamp.

**Power supply:** The Seeed specification for the follower is **12 V 2 A**. That is the same supply that browns out under load here, and the brownout is a [recurring, unsolved upstream issue](https://github.com/huggingface/lerobot/issues/3131). The community recommends a **12 V 5 A** adapter (5.5×2.1 mm barrel, center-positive), and it is the real fix because it gives headroom. The guardrails above make the 2 A supply *usable* for gentle teleop. For recording, or for motion at high speed or under load, use a 5 A supply.

## Bring-up order (from scratch)

```bash
# 1. set motor ids (one motor at a time, per arm)
lerobot-setup-motors --robot.type=so101_follower --robot.port=<FOLLOWER_PORT>
lerobot-setup-motors --teleop.type=so101_leader  --teleop.port=<LEADER_PORT>

# 2. health + voltage standardization
soarm scan --arm follower
soarm fix-voltage-limit --arm follower

# 3. calibrate
lerobot-calibrate --robot.type=so101_follower --robot.port=<FOLLOWER_PORT> --robot.id=my_follower
soarm calibrate-leader --align-wrist-roll

# 4. guardrails + verify + run
soarm set-protection --arm follower
soarm sync-check
soarm teleop
```

The full setup log for one machine is in [`docs/SETUP.md`](docs/SETUP.md).

## Recording demonstrations

`soarm record` wraps `lerobot-record` with the same preflight health check and your configured ports. It adds a `--camera NAME=INDEX` option that you can repeat. It records teleoperated episodes (leader→follower) into a LeRobot dataset, which is the input to train a policy.

```bash
soarm record --list-cameras                       # discover camera indices
soarm record --task "pick up the red cube" --episodes 30 \
    --camera front=0 --camera wrist=2
```

By design, it does **not** apply the teleop motion clamp, because the clamp caps the high-speed motion that a demonstration needs. For headroom, record with a 12 V 5 A follower supply instead.

## Visualize (Rerun)

`soarm twin`, `soarm view`, and `soarm replay` show the arm in [Rerun](https://rerun.io), the same visualization stack that LeRobot uses. Fetch the model one time, then:

```bash
soarm fetch                   # download URDF + meshes into sim/SO101/ (gitignored)
soarm view                    # the arm at its neutral pose
soarm view --sweep            # sweep each joint through its range (visual calib check)
soarm twin --live             # live digital twin: leader (ghost) over follower, + sync plots
soarm replay ./outputs/my_dataset --episode 0   # play back a recorded episode
```

Each command opens a Rerun window. To write a recording file that you can share instead, add `--save run.rrd`. The twin reads the normalized joints of both arms over serial and shows the leader over the follower. You can then see leader↔follower divergence (the root cause of the brownout) immediately. The twin is a live 3D version of `soarm sync-check`, and it streams voltage and temperature onto the same timeline.

## Next steps

After you record, train a policy on the dataset with `lerobot-train` (ACT, diffusion, SmolVLA, pi0…), then evaluate it. Before you train, use `soarm replay` to examine the demonstrations and `soarm twin` to check the calibration. For the asset details, see [`sim/README.md`](sim/README.md).

Teleop from a phone, without the leader arm, needs LeRobot 0.5.x. This toolkit avoids that upgrade while the encoder-seam bug stays open upstream. [`docs/PHONE_TELEOP.md`](docs/PHONE_TELEOP.md) gives the reasons and the upgrade path.

## Development

```bash
just hooks      # install git hooks (one-time): conventional-commit gate + pre-commit lint/test
just check      # import smoke test
just test       # pytest
just lint       # ruff
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/), and the `commit-msg` hook enforces them. The pre-commit hook runs ruff and pytest, and `SOARM_FAST=1` skips them. [release-please](https://github.com/googleapis/release-please) makes the releases. When you merge its release PR, it creates the tag, the GitHub release, and the version bump from the commit history.
