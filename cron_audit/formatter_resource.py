"""Text formatter for resource estimation results."""
from __future__ import annotations

from typing import List

from cron_audit.resource_estimator import ResourceEstimate

_COLS = ("SERVER", "COMMAND", "RUNS/DAY", "WEIGHT", "SCORE")
_SEP = "  "


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def format_resource_report(
    estimates: List[ResourceEstimate],
    top_n: int = 0,
    wide: bool = False,
) -> str:
    """Return a formatted table of resource estimates.

    Args:
        estimates: Pre-sorted list from ``estimate_resources``.
        top_n: If > 0, only show the top *n* entries.
        wide: When True do not truncate the command column.
    """
    if not estimates:
        return "No entries to estimate.\n"

    rows = estimates[:top_n] if top_n > 0 else estimates

    cmd_width = 40 if not wide else 80

    lines: List[str] = []
    header = (
        f"{_COLS[0]:<20}{_SEP}{_COLS[1]:<{cmd_width}}{_SEP}"
        f"{_COLS[2]:>9}{_SEP}{_COLS[3]:>7}{_SEP}{_COLS[4]:>7}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for est in rows:
        server = _truncate(est.entry.server or "unknown", 20)
        cmd = _truncate(est.entry.command, cmd_width)
        lines.append(
            f"{server:<20}{_SEP}{cmd:<{cmd_width}}{_SEP}"
            f"{est.runs_per_day:>9.1f}{_SEP}{est.keyword_weight:>7.1f}"
            f"{_SEP}{est.score:>7.1f}"
        )

    return "\n".join(lines) + "\n"
