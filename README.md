# SO-ARM101 — setup, repair & brownout-safe operation

Tooling and a battle-tested runbook for bringing up a **Seeed Studio SO-ARM101**
(leader + follower) on [LeRobot](https://github.com/huggingface/lerobot). It packages
the fixes for four non-obvious problems hit during a real build, as reusable CLIs.

> Hardware: 2× controller boards (Seeed Bus Servo Driver Board), 12× Feetech **STS3215**
> servos. Follower runs on **12 V**, leader on **5 V**.

## Quick start

```bash
cd ~/git/so-arm101
uv sync                       # create .venv, install (pinned via uv.lock)
source .venv/bin/activate

soarm scan --arm follower     # bus health (ids, voltage, temp, errors)
soarm scan --arm leader
soarm teleop                  # preflight checks + brownout-safe teleop
soarm --help                  # all subcommands
```

Everything is one `soarm` command (Typer + Rich) with subcommands — run `soarm --help`
to discover them, or `soarm <cmd> --help` for any one. Ports live in
[`soarm/config.toml`](soarm/config.toml); macOS `usbmodem` paths can change if you
replug, so run `soarm find-port --write` to auto-detect both arms by voltage and update
the config, or pass `--port` to any tool.

## Tools

| Command | What it does |
|---------|--------------|
| `soarm scan` | Per-motor health for one arm: id, voltage, temperature, error bits. `--sweep` for full discovery, `--list-ports` to find boards. |
| `soarm find-port` | Auto-detect which port is follower (~12 V) vs leader (~5 V) by supply voltage. `--write` updates `config.toml` — no manual unplug-and-diff after a replug. |
| `soarm sync-check` | Compare leader vs follower normalized joint positions (hold both in the same pose). Flags joints beyond `--tol`. |
| `soarm recenter` | Set a joint's current pose as encoder center (Feetech `torque=128`). Fixes the encoder-seam problem and aligns continuous joints. |
| `soarm fix-voltage-limit` | Repair/standardize STS3215 `Max/Min_Voltage_Limit` (the wrist_roll over-voltage failure). |
| `soarm calibrate-leader` | Seam-safe manual calibration for the leader (recenter → sweep → write calibration). `--align-wrist-roll` to sync the continuous joint. |
| `soarm set-protection` | Apply *moderate* brownout guardrails to the follower (acceleration cap + uniform voltage/overload limits). Doesn't weaken holding torque. |
| `soarm teleop` | Preflight health check on both arms, then `lerobot-teleoperate` with a motion clamp. |
| `soarm record` | Preflight-checked dataset recording via `lerobot-record` (see below). |
| `soarm calib` | Back up / restore calibration JSONs between the repo and LeRobot's cache. |
| `soarm twin` | Live **digital twin** in [Rerun](https://rerun.io): overlay the leader (ghost) on the follower, plot leader↔follower sync. `--live` to mirror hardware. |
| `soarm view` | Offline Rerun viewer of the SO-101 at neutral, or `--sweep` each joint (visual calibration check). |
| `soarm replay` | Replay a recorded LeRobot episode in Rerun (joint poses + camera frames). |
| `soarm fetch` | Download the SO-101 URDF + meshes used by the viz tools. |

## The four gotchas (and why the tools exist)

### 1. Board needs a jumper *and* external power
The Seeed Bus Servo Driver Board enumerates its USB port from USB alone, but the
servos only get power from the **DC barrel jack**. For USB control you must also fit the
**front 2-pin jumper** (not shorted by default). Symptom without these: the port appears
but `setup-motors` reports "motor not found".

### 2. A wrong voltage limit bricks a motor onto the bus → `soarm fix-voltage-limit`
One follower servo shipped with `Max_Voltage_Limit = 8.0 V` on a 12 V rail. The motor
raised a permanent over-voltage error and **refused all bus traffic** — it looked like a
broken daisy-chain, not one bad register. Fix: power the board within the motor's current
limit window (e.g. 5 V) so the error clears, then raise the limit to 16 V. Factory limits
are also inconsistent across motors, so we standardize them.

### 3. Encoder seam breaks leader calibration → `soarm recenter` + `soarm calibrate-leader`
Several leader joints' ranges straddle the encoder's **0/4095 seam**, so positions read
negative and LeRobot's homing offset (an 11-bit field, ±2047) overflows —
`lerobot-calibrate` aborts with *"Magnitude N exceeds 2047"*. And because it zeroes homing
on every run, it can't recover. Fix: recenter each joint (`torque=128`) so its range sits
mid-scale off the seam, then write the calibration directly.

### 4. Desynced continuous joint → current draw → brownout → `soarm sync-check`, `soarm set-protection`, `soarm teleop`
A continuous joint (wrist_roll) calibrated to an arbitrary zero was **111° out of sync**,
so the follower drove that motor near-stall every cycle chasing an unreachable target. The
extra current tipped the 12 V **2 A** supply into brownout (whole arm goes limp,
`id_=1 ... no status packet`). Fixing the sync removed the brownout. Guardrails:
`soarm set-protection` caps acceleration (limits current spikes without weakening torque),
and `soarm teleop` runs a preflight + motion clamp.

**Power supply:** Seeed officially specs the follower at **12 V 2 A** — but that is the exact
supply that browns out under load here, and the brownout is a [recurring, unsolved upstream
issue](https://github.com/huggingface/lerobot/issues/3131). A **12 V 5 A** adapter
(5.5×2.1 mm barrel, center-positive) is the de-facto community recommendation and the real
fix for headroom; the guardrails above make the 2 A supply *usable* for gentle teleop but a
5 A supply is recommended for recording or fast/loaded motion.

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

Full machine-specific log: [`docs/SETUP.md`](docs/SETUP.md).

## Recording demonstrations

`soarm record` wraps `lerobot-record` with the same preflight health check and your
configured ports, and adds a simple camera spec. It records leader→follower teleoperated
episodes into a LeRobot dataset — the input for training a policy.

```bash
soarm record --list-cameras                       # discover camera indices
soarm record --task "pick up the red cube" --episodes 30 \
    --camera front=0 --camera wrist=2
```

It intentionally does **not** apply the teleop motion-clamp (that would cap legitimate
fast demonstration motion) — record on a 12 V 5 A follower supply for headroom instead.

## Visualize (Rerun)

`soarm twin`, `soarm view`, and `soarm replay` render the arm in [Rerun](https://rerun.io)
— the same visualization stack LeRobot itself uses. Fetch the model once, then:

```bash
soarm fetch                   # download URDF + meshes into sim/SO101/ (gitignored)
soarm view                    # the arm at its neutral pose
soarm view --sweep            # sweep each joint through its range (visual calib check)
soarm twin --live             # live digital twin: leader (ghost) over follower, + sync plots
soarm replay ./outputs/my_dataset --episode 0   # play back a recorded episode
```

Each opens a Rerun window; add `--save run.rrd` to write a shareable recording instead.
The twin reads both arms' normalized joints over serial and overlays them, so
leader↔follower divergence (the brownout root cause) is visible at a glance — a live,
3D version of `soarm sync-check`, with voltage/temperature streamed onto the same timeline.

## Next steps
After recording, train a policy with `lerobot-train` (ACT, diffusion, SmolVLA, pi0…) on
the dataset, then evaluate. Use `soarm replay` to inspect demonstrations before training
and `soarm twin` to sanity-check calibration. See [`sim/README.md`](sim/README.md) for the
asset details.

Phone / leader-less teleop is **deferred** — it requires LeRobot 0.5.x (an upgrade we avoid
while the encoder-seam bug is unfixed upstream). Rationale and path forward:
[`docs/PHONE_TELEOP.md`](docs/PHONE_TELEOP.md).

## Development

```bash
just hooks      # install git hooks (one-time): conventional-commit gate + pre-commit lint/test
just check      # import smoke test
just test       # pytest
just lint       # ruff
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/) (enforced by the
`commit-msg` hook); the pre-commit hook runs ruff + pytest (skip with `SOARM_FAST=1`).
Releases are automated by [release-please](https://github.com/googleapis/release-please):
merging its release PR cuts the tag, GitHub release, and version bump from the commit history.
