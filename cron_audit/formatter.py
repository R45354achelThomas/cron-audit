"""Human-readable text formatting utilities for cron audit output."""

from typing import List
from cron_audit.parser import CronEntry
from cron_audit.conflict_detector import Conflict

_SEVERITY_ICONS = {
    "duplicate": "[!!]",
    "overlap": "[! ]",
    "info": "[  ]",
}

_HEADER = "="* 60
_SUBHEADER = "-" * 60


def _severity(conflict: Conflict) -> str:
    reason = conflict.reason.lower()
    if "duplicate" in reason:
        return "duplicate"
    if "overlap" in reason:
        return "overlap"
    return "info"


def format_entry(entry: CronEntry, indent: int = 2) -> str:
    """Return a single-line formatted string for a CronEntry."""
    pad = " " * indent
    schedule_str = str(entry.schedule)
    return f"{pad}{schedule_str:<40} {entry.command}"


def format_conflict(conflict: Conflict, indent: int = 2) -> str:
    """Return a formatted string describing a conflict."""
    pad = " " * indent
    icon = _SEVERITY_ICONS.get(_severity(conflict), "[  ]")
    lines = [
        f"{pad}{icon} {conflict.reason}",
        f"{pad}    Entry A: [{conflict.entry_a.server}] {conflict.entry_a.command}",
        f"{pad}    Entry B: [{conflict.entry_b.server}] {conflict.entry_b.command}",
    ]
    return "\n".join(lines)


def format_server_section(server: str, entries: List[CronEntry]) -> str:
    """Return a formatted section for one server's entries."""
    lines = [
        _SUBHEADER,
        f"Server: {server}  ({len(entries)} job(s))",
        _SUBHEADER,
    ]
    for entry in entries:
        lines.append(format_entry(entry))
    return "\n".join(lines)


def format_conflicts_section(conflicts: List[Conflict]) -> str:
    """Return a formatted section listing all conflicts."""
    if not conflicts:
        return "No conflicts detected."
    lines = [
        _SUBHEADER,
        f"Conflicts Detected: {len(conflicts)}",
        _SUBHEADER,
    ]
    for conflict in conflicts:
        lines.append(format_conflict(conflict))
        lines.append("")
    return "\n".join(lines).rstrip()


def format_summary(entry_count: int, server_count: int, conflict_count: int) -> str:
    """Return a one-line summary string."""
    return (
        f"Summary: {entry_count} job(s) across "
        f"{server_count} server(s), {conflict_count} conflict(s) found."
    )
