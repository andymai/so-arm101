"""`soarm scan`: bus health for one arm — id, voltage, temperature, error bits.

Examples:
    soarm scan --arm follower
    soarm scan --port /dev/tty.usbmodem5B415319461
    soarm scan --arm leader --sweep      # full baudrate/id discovery
    soarm scan --list-ports              # find connected boards
"""

from __future__ import annotations

from .bus import MOTORS, Bus, error_flags, is_controller_port, resolve_arm, scan_port
from .console import console, dropout, status, table


def list_controller_ports() -> None:
    from serial.tools import list_ports

    ports = [p.device for p in list_ports.comports() if is_controller_port(p.device)]
    console.print("candidate controller ports:")
    for p in ports or ["(none found)"]:
        console.print(f"  {p}")


def run(arm: str | None, port: str | None, sweep: bool = False, list_ports: bool = False) -> None:
    if list_ports:
        list_controller_ports()
        return

    port, _ = resolve_arm(arm, port)

    if sweep:
        console.print(f"sweeping {port} ...")
        console.print(f"found: {scan_port(port)}")
        return

    console.print(f"port: [cyan]{port}[/]")
    t = table("id", "joint", "volt", "temp", "errors", title="bus health")
    problems = 0
    with Bus(port) as bus:
        for mid, name in MOTORS.items():
            data, comm, err = bus.read(mid, "Present_Voltage")
            if comm != 0:
                t.add_row(str(mid), name, "--", "--", dropout())
                problems += 1
                continue
            volt = data / 10
            temp = bus.read_display(mid, "Present_Temperature")
            flags = error_flags(err)
            if err:
                problems += 1
            t.add_row(str(mid), name, f"{volt:.1f}V", f"{temp}C",
                      status(",".join(flags) or "ok", ok=not flags))
    console.print(t)
    if problems == 0:
        console.print("\n[green]all motors healthy[/]")
    else:
        console.print(f"\n[bold red]{problems} problem(s) found[/]")
    raise SystemExit(1 if problems else 0)
