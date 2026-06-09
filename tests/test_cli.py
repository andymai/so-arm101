"""Tests that lock the CLI surface: every subcommand is registered, and the clean break
left exactly one console entry point (`soarm`)."""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from typer.main import get_command

import soarm.cli

EXPECTED = {
    # hardware
    "scan", "find-port", "sync-check", "recenter", "fix-voltage-limit",
    "calibrate-leader", "set-protection", "teleop", "record", "calib",
    # viz
    "view", "twin", "replay", "fetch",
}


def test_all_commands_registered():
    names = set(get_command(soarm.cli.app).commands.keys())
    missing = EXPECTED - names
    assert not missing, f"missing subcommands: {missing}"


def test_single_console_entrypoint():
    pp = Path(__file__).resolve().parent.parent / "pyproject.toml"
    scripts = tomllib.loads(pp.read_text())["project"]["scripts"]
    assert scripts == {"soarm": "soarm.cli:app"}, "clean break: only `soarm` should remain"
