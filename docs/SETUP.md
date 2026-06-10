# SO-ARM101 Setup (Seeed Kit Pro)

## Activate environment (run first, every new terminal)
```bash
cd ~/so-arm101 && source .venv/bin/activate
```

## Hardware notes (Seeed / Waveshare driver board)
- Each arm has its own controller board. Configure ONE arm at a time.
- **Waveshare board: set BOTH jumpers to the `B` (USB) channel.**
- Power supply AND USB must both be connected to the board.
- Motors: 6x Feetech STS3215. They ship with default id=1 — must be made unique.

---

## STEP 1 — Find the USB port for each arm
Plug in ONE arm's controller board (USB + power), then:
```bash
lerobot-find-port
```
Follow the prompt (it tells you to unplug, press Enter). Record the port below.

- FOLLOWER port: /dev/tty.usbmodem5B415319461
- LEADER   port: /dev/tty.usbmodem5B415322401

(macOS ports look like `/dev/tty.usbmodem585A0076841`; on Linux they are
`/dev/ttyACM0` etc. — and you must be in the `dialout` group to open them:
`sudo usermod -aG dialout "$USER"`, then re-login. See README → "Linux serial access".)

---

## STEP 2 — Set motor IDs + baudrate

### Follower  ✅ DONE (all 6 ids set, port /dev/tty.usbmodem5B415319461)
Connect ONLY the gripper motor to the follower board first, then run:
```bash
lerobot-setup-motors --robot.type=so101_follower --robot.port=<FOLLOWER_PORT>
```
Order it walks you through (one motor connected at a time):
  6 gripper -> 5 wrist_roll -> 4 wrist_flex -> 3 elbow_flex -> 2 shoulder_lift -> 1 shoulder_pan
After each "set to N" message, move the 3-pin cable to the next motor and press Enter.

### Leader  ✅ DONE (all 6 ids set, port /dev/tty.usbmodem5B415322401)
```bash
lerobot-setup-motors --teleop.type=so101_leader --teleop.port=<LEADER_PORT>
```
Same one-motor-at-a-time sequence.

When done, daisy-chain all 6 motors and connect motor 1 (shoulder_pan) to the board.

---

## NOTE — wrist_roll (id 5) voltage fix (2026-06-08)
Follower wrist_roll shipped with Max_Voltage_Limit=8.0V but runs at 12V ->
persistent "Input voltage error", motor refused all commands, looked like a
broken chain. Fixed by powering board at 5V (clears error so writes are accepted)
then writing Max_Voltage_Limit=16.0V (addr 14) via low-level packet handler
(Lock addr55=0, write, Lock=1). Persists in EEPROM. Watch this joint's temp under
load; if it runs hot it may be a 7.4V-variant motor that needs swapping.

## STEP 3 — Calibrate
### Follower ✅ DONE — standard calibrate worked
```bash
lerobot-calibrate --robot.type=so101_follower --robot.port=/dev/tty.usbmodem5B415319461 --robot.id=my_follower
```
Saved: ~/.cache/huggingface/lerobot/calibration/robots/so_follower/my_follower.json

### Leader ✅ DONE — needed a manual workaround (encoder-seam issue)
`lerobot-calibrate` FAILED: "Magnitude 2359 exceeds 2047". Several leader joints
(esp. elbow_flex) have their range straddling the encoder 0/4095 seam, so the
position read negative at middle and Homing_Offset overflowed the 11-bit field.
Standard calibrate calls reset_calibration (zeros Homing_Offset) every run, so it
kept re-failing.

Fix (all software, no disassembly):
1. Put arm in good neutral pose; recenter every joint with Feetech "set middle"
   command: write 128 to Torque_Enable (addr 40) -> current pos becomes 2048.
   (unlock Lock addr55=0, write 128 to addr40, lock; then write 0 to addr40 to
   release torque). This sets Homing_Offset so range sits mid-scale, off the seam.
2. shoulder_lift needed recentering at its OWN mid-travel (was biased high near 4095).
3. Swept all joints except wrist_roll, recorded Present_Position min/max.
4. Wrote calibration JSON directly (homing_offset from registers + swept ranges;
   wrist_roll range 0-4095) to
   ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/my_leader.json
5. Pushed to motors via bus.write_calibration() so is_calibrated==True.
Verified: leader connects, is_calibrated True, normalized degrees read sane.

## NOTE — wrist_roll sync fix (leader)
After manual leader calibration, wrist_roll was out of sync vs follower (~111 deg off)
because it's continuous (homing-defined zero) and the manual cal set an arbitrary zero.
Fixed: aligned both wrists physically, computed homing shift; direct value (-3286)
overflowed +/-2047 so used full-turn equivalent (-3286+4096 = 810). Wrote homing 810 to
leader wrist_roll (motor EEPROM addr31 + my_leader.json). Result: all 6 joints sync
within ~4 deg at matched poses; is_calibrated True. Bounded joints (gripper/wrist_flex)
were already synced (verified at hard stops) — only the continuous joint needed manual alignment.

## STEP 4 — Teleoperate
```bash
lerobot-teleoperate \
  --robot.type=so101_follower --robot.port=/dev/tty.usbmodem5B415319461 --robot.id=my_follower \
  --teleop.type=so101_leader  --teleop.port=/dev/tty.usbmodem5B415322401 --teleop.id=my_leader
```
WORKS. Earlier it browned out under motion ("... id_=1 ... no status packet") and this
was first blamed on the 12V 2A supply. REAL root cause: the desynced continuous wrist_roll
(~111° off) drove that motor near-stall every cycle chasing an unreachable target -> excess
current -> brown-out. After the wrist_roll sync fix (above), current dropped and teleop runs
fine on the existing 2A supply. A 12V >=5A adapter (5.5x2.1mm, center-positive) is still
nice-to-have for fast/loaded motion but is NOT required.
