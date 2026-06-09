"""soarm-scan: bus health for one arm — id, voltage, temperature, error bits.

Examples:
    soarm-scan --arm follower
    soarm-scan --port /dev/tty.usbmodem5B415319461
    soarm-scan --arm leader --sweep      # full baudrate/id discovery
    soarm-scan --list-ports              # find connected boards
"""

from __future__ import annotations

import argparse

from .bus import MOTORS, Bus, add_arm_port_args, error_flags, resolve_arm, scan_port


def _list_ports() -> None:
    from serial.tools import list_ports

    ports = [p.device for p in list_ports.comports() if "usbmodem" in p.device or "ACM" in p.device]
    print("candidate controller ports:")
    for p in ports or ["(none found)"]:
        print(f"  {p}")


def main() -> None:
    ap = argparse.ArgumentParser(description="SO-ARM101 bus health scan")
    add_arm_port_args(ap)
    ap.add_argument("--sweep", action="store_true", help="full baudrate/id discovery")
    ap.add_argument("--list-ports", action="store_true", help="list connected boards and exit")
    args = ap.parse_args()

    if args.list_ports:
        _list_ports()
        return

    port, _ = resolve_arm(args.arm, args.port)

    if args.sweep:
        print(f"sweeping {port} ...")
        print("found:", scan_port(port))
        return

    print(f"port: {port}")
    print(f"{'id':>2}  {'joint':14} {'volt':>6} {'temp':>5} {'errors':>22}")
    problems = 0
    with Bus(port) as bus:
        for mid, name in MOTORS.items():
            data, comm, err = bus.read(mid, "Present_Voltage")
            if comm != 0:
                print(f"{mid:>2}  {name:14} {'--':>6} {'--':>5} {'NO RESPONSE':>22}")
                problems += 1
                continue
            volt = data / 10
            temp = bus.read_display(mid, "Present_Temperature")
            flags = ",".join(error_flags(err)) or "ok"
            if err:
                problems += 1
            print(f"{mid:>2}  {name:14} {volt:>5.1f}V {temp:>4}C {flags:>22}")
    print("\n" + ("all motors healthy" if problems == 0 else f"{problems} problem(s) found"))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
