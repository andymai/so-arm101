"""Shared low-level helpers for talking to the SO-ARM101 Feetech STS3215 bus.

Why this exists: LeRobot's high-level ``read``/``write`` raise on any motor error
bit, which makes diagnostics impossible when a motor is *in* an error state (e.g.
the wrist_roll over-voltage failure). Here we keep a thin wrapper around LeRobot's
``FeetechMotorsBus`` but reach for the underlying ``packet_handler`` so we can read
registers regardless of error bits, and decode the STS3215 sign-magnitude encodings
ourselves.

All register addresses are taken from LeRobot's STS_SMS control table.
"""

from __future__ import annotations

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib
import argparse
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech.feetech import FeetechMotorsBus

# joint name <-> bus id (base -> gripper), identical on both arms
MOTORS: dict[int, str] = {
    1: "shoulder_pan",
    2: "shoulder_lift",
    3: "elbow_flex",
    4: "wrist_flex",
    5: "wrist_roll",   # continuous joint
    6: "gripper",
}
NAME_TO_ID = {v: k for k, v in MOTORS.items()}
CONTINUOUS = {"wrist_roll"}  # no hard stops; homing-defined zero
MODEL = "sts3215"

# register name -> (address, byte length), from STS_SMS_SERIES_CONTROL_TABLE
REG: dict[str, tuple[int, int]] = {
    "Min_Voltage_Limit": (15, 1),
    "Max_Voltage_Limit": (14, 1),
    "Max_Temperature_Limit": (13, 1),
    "Min_Position_Limit": (9, 2),
    "Max_Position_Limit": (11, 2),
    "Phase": (18, 1),
    "Protection_Current": (28, 2),
    "Homing_Offset": (31, 2),
    "Operating_Mode": (33, 1),
    "Protective_Torque": (34, 1),
    "Protection_Time": (35, 1),
    "Overload_Torque": (36, 1),
    "Over_Current_Protection_Time": (38, 1),
    "Torque_Enable": (40, 1),
    "Acceleration": (41, 1),
    "Goal_Position": (42, 2),
    "Torque_Limit": (48, 2),
    "Lock": (55, 1),
    "Present_Position": (56, 2),
    "Present_Voltage": (62, 1),
    "Present_Temperature": (63, 1),
    "Maximum_Acceleration": (85, 1),
}

# error bits in the status byte
ERROR_BITS = {1: "VOLTAGE", 2: "ANGLE", 4: "OVERHEAT", 8: "OVERELE", 32: "OVERLOAD"}


def error_flags(err: int) -> list[str]:
    """Decode a motor status byte into the names of its set error bits."""
    return [b for k, b in ERROR_BITS.items() if err & k]

# Feetech special command: write 128 to Torque_Enable -> set current pos as 2048
SET_MIDDLE = 128
RESOLUTION = 4096          # 12-bit encoder
HOMING_SIGN_BIT = 11       # Homing_Offset magnitude is 11-bit + sign at bit 11


class BusCommError(RuntimeError):
    """A motor did not respond (serial dropout / contention / NAK)."""


def _config_path() -> Path:
    return Path(__file__).with_name("config.toml")


@dataclass
class ArmCfg:
    name: str
    port: str
    id: str
    supply: str


def load_config() -> dict[str, ArmCfg]:
    data = tomllib.loads(_config_path().read_text())
    return {
        name: ArmCfg(name=name, port=d["port"], id=d["id"], supply=d.get("supply", ""))
        for name, d in data.items()
    }


def add_arm_port_args(ap: argparse.ArgumentParser, *, arm_default: str | None = None) -> None:
    """Add the shared --arm/--port selection flags used by every per-arm CLI."""
    ap.add_argument("--arm", choices=["follower", "leader"], default=arm_default,
                    help="arm from config.toml")
    ap.add_argument("--port", help="explicit serial port (overrides --arm)")


def resolve_arm(arm: str | None, port: str | None) -> tuple[str, str]:
    """Return (port, id) from --arm name and/or explicit --port override."""
    cfg = load_config()
    if arm and arm not in cfg:
        raise SystemExit(f"unknown arm '{arm}'; known: {', '.join(cfg)}")
    chosen = cfg[arm] if arm else None
    out_port = port or (chosen.port if chosen else None)
    out_id = chosen.id if chosen else (arm or "")
    if not out_port:
        raise SystemExit("no port: pass --arm follower|leader or --port /dev/...")
    return out_port, out_id


def decode_sign_magnitude(raw: int, sign_bit: int = HOMING_SIGN_BIT) -> int:
    mag = raw & ((1 << sign_bit) - 1)
    return -mag if (raw >> sign_bit) & 1 else mag


def encode_sign_magnitude(value: int, sign_bit: int = HOMING_SIGN_BIT) -> int:
    if abs(value) >= (1 << sign_bit):
        raise ValueError(f"|{value}| exceeds {(1 << sign_bit) - 1} (sign_bit={sign_bit})")
    return (abs(value) | (1 << sign_bit)) if value < 0 else value


def decode_present_position(raw: int) -> int:
    """Present_Position is sign-magnitude in a 16-bit field (bit 15 = sign)."""
    return -(raw & 0x7FFF) if raw & 0x8000 else raw


def fold_homing(value: int, sign_bit: int = HOMING_SIGN_BIT) -> int:
    """Fold a continuous-joint homing offset into the encodable ±(2**sign_bit - 1) window
    by whole turns. A full-RESOLUTION shift is physically identical for a continuous joint,
    so this lets a correction that would overflow the 11-bit field wrap to an equal angle."""
    limit = (1 << sign_bit) - 1
    while value > limit:
        value -= RESOLUTION
    while value < -limit:
        value += RESOLUTION
    return value


class Bus:
    """One arm's bus. Use as a context manager."""

    def __init__(self, port: str, ids: list[int] | None = None):
        self.port = port
        ids = ids or list(MOTORS)
        motors = {MOTORS[i]: Motor(i, MODEL, MotorNormMode.RANGE_M100_100) for i in ids}
        self._bus = FeetechMotorsBus(port, motors=motors)

    def __enter__(self) -> "Bus":
        self._bus.connect(handshake=False)
        self.ph = self._bus.packet_handler
        self.po = self._bus.port_handler
        return self

    def __exit__(self, *exc) -> None:
        try:
            self.po.closePort()
        except Exception:
            pass

    COMM_FAIL = -1

    # --- raw register access: read() is tolerant (for display); value() raises ---
    def read(self, motor_id: int, reg: str, retries: int = 2) -> tuple[int, int, int]:
        """Low-level read. Returns (data, comm, err); comm != 0 means no response.
        Never raises — callers that display health (scan) inspect comm themselves.
        Retries a few times: this bus drops the occasional single packet, and a
        transient miss shouldn't read as a dead motor (false NO RESPONSE / preflight fail)."""
        addr, length = REG[reg]
        result = (0, self.COMM_FAIL, 0)
        for _ in range(retries + 1):
            try:
                if length == 1:
                    result = self.ph.read1ByteTxRx(self.po, motor_id, addr)
                else:
                    result = self.ph.read2ByteTxRx(self.po, motor_id, addr)
            except Exception:  # serial dropout, contention, etc.
                result = (0, self.COMM_FAIL, 0)
            if result[1] == 0:  # comm success — stop retrying
                break
        return result

    def read_display(self, motor_id: int, reg: str) -> str | int:
        """Read a register for display purposes. Returns the int value on success,
        or '--' on comm failure. Use value() when the result feeds a calculation."""
        data, comm, _ = self.read(motor_id, reg)
        return "--" if comm != 0 else data

    def value(self, motor_id: int, reg: str) -> int:
        """Read a register, raising BusCommError on no-response so a dropout is never
        silently treated as a real value of 0 (which would corrupt calibration)."""
        data, comm, _ = self.read(motor_id, reg)
        if comm != 0:
            raise BusCommError(f"motor {motor_id}: no response reading {reg}")
        return data

    def write(self, motor_id: int, reg: str, value: int) -> int:
        """Low-level write. Returns comm status; use write_checked() when the value
        is persisted (EEPROM) and a silent failure would matter."""
        addr, length = REG[reg]
        if length == 1:
            comm, _ = self.ph.write1ByteTxRx(self.po, motor_id, addr, value)
        else:
            comm, _ = self.ph.write2ByteTxRx(self.po, motor_id, addr, value)
        return comm

    def write_checked(self, motor_id: int, reg: str, value: int) -> None:
        if self.write(motor_id, reg, value) != 0:
            raise BusCommError(f"motor {motor_id}: write {reg}={value} failed")

    @contextmanager
    def unlocked(self, motor_id: int):
        """EEPROM writes require Lock=0; relock afterwards."""
        self.write(motor_id, "Lock", 0)
        try:
            yield
        finally:
            self.write(motor_id, "Lock", 1)

    def present_position(self, motor_id: int) -> int:
        data, comm, _ = self.read(motor_id, "Present_Position")
        if comm != 0:
            raise BusCommError(f"motor {motor_id}: no response reading position")
        return decode_present_position(data)

    def homing_offset(self, motor_id: int) -> int:
        return decode_sign_magnitude(self.value(motor_id, "Homing_Offset"))

    def set_homing_offset(self, motor_id: int, value: int) -> None:
        with self.unlocked(motor_id):
            self.write_checked(motor_id, "Homing_Offset", encode_sign_magnitude(value))

    def recenter(self, motor_id: int) -> int:
        """Feetech 'set middle': current physical pose becomes 2048. Returns new homing."""
        with self.unlocked(motor_id):
            self.write_checked(motor_id, "Torque_Enable", SET_MIDDLE)
        self.write(motor_id, "Torque_Enable", 0)  # release so the joint moves freely
        return self.homing_offset(motor_id)

    def verify_center(self, motor_id: int, settle_s: float = 0.4) -> int:
        """Confirm a recenter physically held: torque the joint, command goal 2048,
        and return |Present_Position - 2048| (drift in counts). A small drift means the
        'set middle' write landed. Leaves torque DISABLED so the joint stays hand-movable."""
        center = RESOLUTION // 2
        self.write_checked(motor_id, "Torque_Enable", 1)
        try:
            self.write_checked(motor_id, "Goal_Position", center)
            time.sleep(settle_s)
            pos = self.present_position(motor_id)
        finally:
            self.write(motor_id, "Torque_Enable", 0)  # always release
        return abs(pos - center)


def scan_port(port: str):
    """Sweep all baudrates/ids. Returns LeRobot's {baud: [ids]} dict."""
    return FeetechMotorsBus.scan_port(port)


def lerobot_cli(name: str) -> str:
    """Resolve a lerobot-* console script next to the current interpreter (the venv's
    bin/), so subprocesses find it even when our entry point is run without the venv on
    PATH (uv run, a direct path, pipx). Falls back to the bare name when activated."""
    candidate = Path(sys.executable).parent / name
    return str(candidate) if candidate.exists() else name
