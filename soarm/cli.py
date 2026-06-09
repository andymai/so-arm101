"""The ``soarm`` command — a single first-class CLI for the SO-ARM101 toolkit.

Each subcommand is a thin Typer wrapper over the logic in its module (scan, teleop,
calibrate-leader, twin, ...). The load-bearing hardware knowledge and bus invariants
live in bus.py / devices.py and are not touched here — this file is only argument
parsing, help text, and dispatch.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional

import typer

from . import calib_io as _calib
from . import calibrate_leader as _calibrate_leader
from . import find_port as _find_port
from . import fix_voltage_limit as _fix_voltage
from . import protect as _protect
from . import recenter as _recenter
from . import record as _record
from . import scan as _scan
from . import sync_check as _sync_check
from . import teleop as _teleop

app = typer.Typer(
    name="soarm",
    help="SO-ARM101 toolkit — bring-up, calibration, brownout-safe operation, and visualization.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


class Arm(str, Enum):
    follower = "follower"
    leader = "leader"


class CalibAction(str, Enum):
    backup = "backup"
    restore = "restore"
    path = "path"


# Reusable option annotations for the shared --arm/--port arm selection.
ArmOpt = Annotated[Optional[Arm], typer.Option(help="arm from config.toml")]
PortOpt = Annotated[Optional[str], typer.Option(help="explicit serial port (overrides --arm)")]


def _arm(arm: Optional[Arm]) -> Optional[str]:
    return arm.value if arm else None


def _version_callback(value: bool) -> None:
    if value:
        from importlib.metadata import version

        typer.echo(f"soarm {version('soarm101')}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        bool, typer.Option("--version", callback=_version_callback, is_eager=True,
                           help="show version and exit")
    ] = False,
) -> None:
    """SO-ARM101 toolkit."""


# --------------------------------------------------------------------------- hardware


@app.command()
def scan(
    arm: ArmOpt = None,
    port: PortOpt = None,
    sweep: Annotated[bool, typer.Option(help="full baudrate/id discovery")] = False,
    list_ports: Annotated[bool, typer.Option(help="list connected boards and exit")] = False,
) -> None:
    """Bus health for one arm — id, voltage, temperature, error bits."""
    _scan.run(_arm(arm), port, sweep=sweep, list_ports=list_ports)


@app.command(name="find-port")
def find_port(
    write: Annotated[bool, typer.Option(help="update soarm/config.toml in place")] = False,
) -> None:
    """Auto-detect which port is follower (~12 V) vs leader (~5 V) by supply voltage."""
    _find_port.run(write=write)


@app.command(name="sync-check")
def sync_check(
    tol: Annotated[float, typer.Option(help="max allowed |diff| in degrees")] = 8.0,
) -> None:
    """Compare leader vs follower normalized joint positions (hold both in one pose)."""
    _sync_check.run(tol=tol)


@app.command()
def recenter(
    joint: Annotated[str, typer.Option(help="joint name (e.g. elbow_flex) or 'all'")],
    arm: ArmOpt = None,
    port: PortOpt = None,
    verify: Annotated[bool, typer.Option(help="torque to goal 2048 and report drift")] = False,
) -> None:
    """Set a joint's current pose as encoder center (Feetech 'set middle')."""
    _recenter.run(_arm(arm), port, joint=joint, verify=verify)


@app.command(name="fix-voltage-limit")
def fix_voltage_limit(
    arm: ArmOpt = None,
    port: PortOpt = None,
    max_v: Annotated[float, typer.Option("--max", help="Max_Voltage_Limit in volts")] = 16.0,
    min_v: Annotated[float, typer.Option("--min", help="Min_Voltage_Limit in volts")] = 4.0,
    check: Annotated[bool, typer.Option(help="report only, do not write")] = False,
) -> None:
    """Repair/standardize STS3215 Max/Min voltage limits (the over-voltage lockout fix)."""
    _fix_voltage.run(_arm(arm), port, max_v=max_v, min_v=min_v, check=check)


@app.command(name="calibrate-leader")
def calibrate_leader(
    align_wrist_roll: Annotated[
        bool, typer.Option(help="also align continuous wrist_roll zero to the follower")
    ] = False,
) -> None:
    """Seam-safe manual calibration for the leader (recenter → sweep → write)."""
    _calibrate_leader.run(align_wrist_roll=align_wrist_roll)


@app.command(name="set-protection")
def set_protection(
    arm: ArmOpt = Arm.follower,
    port: PortOpt = None,
    accel: Annotated[int, typer.Option(help="Maximum_Acceleration cap 0-254 (lower = gentler)")] = 100,
    max_volt: Annotated[float, typer.Option()] = 16.0,
    min_volt: Annotated[float, typer.Option()] = 4.0,
    overload: Annotated[int, typer.Option(help="Overload_Torque % threshold")] = 80,
    check: Annotated[bool, typer.Option(help="report current values only")] = False,
) -> None:
    """Apply moderate brownout guardrails to the follower (accel cap + uniform limits)."""
    _protect.run(_arm(arm), port, accel=accel, max_volt=max_volt, min_volt=min_volt,
                 overload=overload, check=check)


@app.command()
def teleop(
    clamp: Annotated[float, typer.Option(help="max_relative_target deg/cycle (current cap)")] = 8.0,
    no_clamp: Annotated[bool, typer.Option(help="disable motion clamp")] = False,
    check_only: Annotated[bool, typer.Option(help="run preflight then exit")] = False,
    skip_preflight: Annotated[bool, typer.Option(help="skip the health preflight")] = False,
) -> None:
    """Preflight health check on both arms, then clamped lerobot-teleoperate."""
    _teleop.run(clamp=clamp, no_clamp=no_clamp, check_only=check_only,
                skip_preflight=skip_preflight)


@app.command()
def record(
    task: Annotated[Optional[str], typer.Option(help="natural-language task (dataset label)")] = None,
    episodes: Annotated[int, typer.Option(help="number of episodes to record")] = 30,
    repo_id: Annotated[Optional[str], typer.Option(help="dataset repo id (default <user>/so101-dataset)")] = None,
    camera: Annotated[Optional[list[str]], typer.Option(help="NAME=INDEX, repeatable")] = None,
    width: Annotated[int, typer.Option()] = 640,
    height: Annotated[int, typer.Option()] = 480,
    fps: Annotated[int, typer.Option()] = 30,
    episode_time: Annotated[float, typer.Option(help="seconds per episode")] = 30,
    reset_time: Annotated[float, typer.Option(help="seconds to reset between episodes")] = 15,
    push: Annotated[bool, typer.Option(help="push the dataset to the Hugging Face Hub")] = False,
    skip_preflight: Annotated[bool, typer.Option(help="skip the health preflight")] = False,
    list_cameras: Annotated[bool, typer.Option(help="discover camera indices and exit")] = False,
) -> None:
    """Preflight-checked dataset recording via lerobot-record."""
    _record.run(task=task, episodes=episodes, repo_id=repo_id, camera=camera, width=width,
                height=height, fps=fps, episode_time=episode_time, reset_time=reset_time,
                push=push, skip_preflight=skip_preflight, list_cameras=list_cameras)


@app.command()
def calib(
    action: Annotated[CalibAction, typer.Argument(help="backup | restore | path")],
) -> None:
    """Back up / restore calibration JSONs between the repo and LeRobot's cache."""
    _calib.run(action.value)


# ------------------------------------------------------------------------------- viz
from . import viz as _viz  # noqa: E402  (registers view/twin/replay/fetch on `app`)

_viz.register(app)


if __name__ == "__main__":
    app()
