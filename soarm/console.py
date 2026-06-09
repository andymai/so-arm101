"""Shared Rich console + table styling for the soarm CLI.

Centralizes what used to be hand-aligned f-string tables duplicated across scan,
fix_voltage_limit, protect, and sync_check. One Console, one table factory, one set
of status colors — so every command's output looks the same and error/out-of-sync
states are colored consistently.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

# semantic colors, used everywhere so "bad" always reads the same
OK = "green"
WARN = "yellow"
BAD = "bold red"
MUTED = "dim"


def table(*columns: str, title: str | None = None) -> Table:
    """A motor-health table. First column left-aligned (joint/label), rest right-aligned
    (numbers). Pass column headers; add rows with Rich markup or Text for color."""
    t = Table(title=title, title_justify="left", header_style="bold cyan", pad_edge=False)
    for i, header in enumerate(columns):
        t.add_column(header, justify="left" if i == 0 else "right", no_wrap=True)
    return t


def status(text: str, ok: bool, *, warn: bool = False) -> Text:
    """A colored status cell: green when ok, red when not (yellow if warn=True)."""
    return Text(text, style=OK if ok else (WARN if warn else BAD))


def dropout() -> Text:
    """The standard 'motor did not answer' cell."""
    return Text("NO RESPONSE", style=BAD)
