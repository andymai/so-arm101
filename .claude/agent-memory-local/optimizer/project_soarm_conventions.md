---
name: project-soarm-conventions
description: Key conventions and non-obvious patterns in the so-arm101 soarm/ Python toolkit
metadata:
  type: project
---

**Fail-loud-on-data / degrade-on-display split** — the core bus access pattern:
- `bus.value()` raises `BusCommError` on comm failure — used for any read that feeds a calculation or write (calibration, verification). A comm failure here is a hard error.
- `bus.read()` returns `(data, comm, err)` and never raises — used when displaying health (scan, preflight).
- `bus.read_display()` returns the int value or `"--"` on failure — convenience wrapper for display-only reads that would otherwise need a two-line comm check.

**Why:** A comm dropout that silently returns 0 would corrupt calibration (0 looks like a valid encoder position or homing offset).

**How to apply:** When adding new register reads, ask: "does this value feed a write/calculation?" → `value()`. "Is this for display only?" → `read()` or `read_display()`.

**Exit code convention:** Diagnostic CLIs that can find problems use explicit `raise SystemExit(1 if N_problems else 0)`. Tools that only fail on comm errors use `raise SystemExit(1)` on the failure path and fall through to implicit 0.

**Error-bit semantics:** `err` in `bus.read()` is the STS3215 status byte error bits, not a comm error. A motor can respond (comm=0) and still have error bits set (e.g. VOLTAGE error while communicating fine on a lower-voltage supply). These are separate failure modes.

**Domain gotchas preserved in comments (never strip):**
- voltage-limit lockout: a motor below its Max_Voltage_Limit refuses all bus traffic
- encoder seam: raw encoder range 0-4095; joints straddling 0/4095 need recentering before calibration
- "set middle" command: writing 128 to Torque_Enable moves current pos to encoder 2048
- Homing_Offset is 11-bit sign-magnitude (not two's complement)
- Present_Position is 16-bit sign-magnitude (bit 15 = sign), not the same encoding as Homing_Offset
