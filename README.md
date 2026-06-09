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

soarm-scan --arm follower     # bus health (ids, voltage, temp, errors)
soarm-scan --arm leader
soarm-teleop                  # preflight checks + brownout-safe teleop
```

Ports live in [`soarm/config.toml`](soarm/config.toml). macOS `usbmodem` paths can
change if you replug; re-discover with `lerobot-find-port` (or `soarm-scan --list-ports`)
and update the config, or pass `--port` to any tool.

## Tools

| Command | What it does |
|---------|--------------|
| `soarm-scan` | Per-motor health for one arm: id, voltage, temperature, error bits. `--sweep` for full discovery, `--list-ports` to find boards. |
| `soarm-sync-check` | Compare leader vs follower normalized joint positions (hold both in the same pose). Flags joints beyond `--tol`. |
| `soarm-recenter` | Set a joint's current pose as encoder center (Feetech `torque=128`). Fixes the encoder-seam problem and aligns continuous joints. |
| `soarm-fix-voltage-limit` | Repair/standardize STS3215 `Max/Min_Voltage_Limit` (the wrist_roll over-voltage failure). |
| `soarm-calibrate-leader` | Seam-safe manual calibration for the leader (recenter → sweep → write calibration). `--align-wrist-roll` to sync the continuous joint. |
| `soarm-set-protection` | Apply *moderate* brownout guardrails to the follower (acceleration cap + uniform voltage/overload limits). Doesn't weaken holding torque. |
| `soarm-teleop` | Preflight health check on both arms, then `lerobot-teleoperate` with a motion clamp. |
| `soarm-calib` | Back up / restore calibration JSONs between the repo and LeRobot's cache. |

## The four gotchas (and why the tools exist)

### 1. Board needs a jumper *and* external power
The Seeed Bus Servo Driver Board enumerates its USB port from USB alone, but the
servos only get power from the **DC barrel jack**. For USB control you must also fit the
**front 2-pin jumper** (not shorted by default). Symptom without these: the port appears
but `setup-motors` reports "motor not found".

### 2. A wrong voltage limit bricks a motor onto the bus → `soarm-fix-voltage-limit`
One follower servo shipped with `Max_Voltage_Limit = 8.0 V` on a 12 V rail. The motor
raised a permanent over-voltage error and **refused all bus traffic** — it looked like a
broken daisy-chain, not one bad register. Fix: power the board within the motor's current
limit window (e.g. 5 V) so the error clears, then raise the limit to 16 V. Factory limits
are also inconsistent across motors, so we standardize them.

### 3. Encoder seam breaks leader calibration → `soarm-recenter` + `soarm-calibrate-leader`
Several leader joints' ranges straddle the encoder's **0/4095 seam**, so positions read
negative and LeRobot's homing offset (an 11-bit field, ±2047) overflows —
`lerobot-calibrate` aborts with *"Magnitude N exceeds 2047"*. And because it zeroes homing
on every run, it can't recover. Fix: recenter each joint (`torque=128`) so its range sits
mid-scale off the seam, then write the calibration directly.

### 4. Desynced continuous joint → current draw → brownout → `soarm-sync-check`, `soarm-set-protection`, `soarm-teleop`
A continuous joint (wrist_roll) calibrated to an arbitrary zero was **111° out of sync**,
so the follower drove that motor near-stall every cycle chasing an unreachable target. The
extra current tipped the 12 V **2 A** supply into brownout (whole arm goes limp,
`id_=1 ... no status packet`). Fixing the sync removed the brownout. Guardrails:
`soarm-set-protection` caps acceleration (limits current spikes without weakening torque),
and `soarm-teleop` runs a preflight + motion clamp. A 12 V ≥5 A supply adds headroom for
fast/loaded motion but isn't required.

## Bring-up order (from scratch)

```bash
# 1. set motor ids (one motor at a time, per arm)
lerobot-setup-motors --robot.type=so101_follower --robot.port=<FOLLOWER_PORT>
lerobot-setup-motors --teleop.type=so101_leader  --teleop.port=<LEADER_PORT>

# 2. health + voltage standardization
soarm-scan --arm follower
soarm-fix-voltage-limit --arm follower

# 3. calibrate
lerobot-calibrate --robot.type=so101_follower --robot.port=<FOLLOWER_PORT> --robot.id=my_follower
soarm-calibrate-leader --align-wrist-roll

# 4. guardrails + verify + run
soarm-set-protection --arm follower
soarm-sync-check
soarm-teleop
```

Full machine-specific log: [`docs/SETUP.md`](docs/SETUP.md).

## Next steps
Add a camera (`lerobot-find-cameras`), record demonstrations (`lerobot-record`),
then train a policy (`lerobot-train`).
