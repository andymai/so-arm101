"""soarm-find-port: auto-detect which USB port is the follower vs the leader.

macOS usbmodem paths change on replug, which stales config.toml. Instead of the manual
unplug-and-diff dance, this reads each connected port's supply voltage — the follower
runs at ~12V, the leader at ~5V — and maps ports to arms. With --write it updates
config.toml in place (preserving comments).

Examples:
    soarm-find-port            # detect and print the mapping
    soarm-find-port --write    # also update soarm/config.toml
"""

from __future__ import annotations

from .bus import Bus, MOTORS, _config_path, is_controller_port
from .console import console, table

# follower supply ~12V, leader ~5V; 8V cleanly separates them
ARM_VOLTAGE_SPLIT = 8.0


def classify_arm(voltage: float) -> str:
    """Map a measured supply voltage to an arm role."""
    return "follower" if voltage >= ARM_VOLTAGE_SPLIT else "leader"


def normalize_port(port: str) -> str:
    """macOS exposes both /dev/cu.* and /dev/tty.* for one device; the toolkit and
    LeRobot use the tty.* form, so normalize to it for display/config consistency."""
    return port.replace("/dev/cu.", "/dev/tty.")


def detect_voltage(port: str) -> float | None:
    """Return the supply voltage of the first responding motor on a port, or None."""
    try:
        with Bus(port) as bus:
            for mid in MOTORS:
                data, comm, _ = bus.read(mid, "Present_Voltage")
                if comm == 0:
                    return data / 10
    except Exception:  # noqa: BLE001 — any port that won't open / talk isn't an arm
        return None
    return None


def update_config_ports(text: str, ports: dict[str, str]) -> str:
    """Replace the `port = "..."` line within each [arm] section of config.toml.
    Section-aware line edit so comments and the rest of the file are preserved."""
    out, section = [], None
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
        elif section in ports and stripped.startswith("port"):
            indent = line[: len(line) - len(line.lstrip())]
            line = f'{indent}port = "{ports[section]}"\n'
        out.append(line)
    return "".join(out)


def _candidate_ports() -> list[str]:
    from serial.tools import list_ports

    return [p.device for p in list_ports.comports() if is_controller_port(p.device)]


def run(write: bool = False) -> None:
    found: dict[str, str] = {}  # arm -> port
    t = table("port", "volt", "arm")
    for port in _candidate_ports():
        volt = detect_voltage(port)
        reported = normalize_port(port)
        if volt is None:
            t.add_row(reported, "--", "[dim](no motor — not an arm)[/]")
            continue
        arm = classify_arm(volt)
        dup = " [yellow]DUPLICATE[/]" if arm in found else ""
        found.setdefault(arm, reported)
        t.add_row(reported, f"{volt:.1f}V", f"{arm}{dup}")
    console.print(t)

    if not write:
        return
    if {"follower", "leader"} <= set(found):
        path = _config_path()
        path.write_text(update_config_ports(path.read_text(), found))
        console.print(f"\n[green]updated[/] {path}")
    else:
        console.print(f"\n[bold red]not writing[/]: need both arms, found {sorted(found)}")
        raise SystemExit(1)
