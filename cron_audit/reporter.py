"""Generates human-readable audit reports from parsed cron data."""

from typing import Dict, List
from cron_audit.parser import CronEntry
from cron_audit.conflict_detector import Conflict
from cron_audit.formatter import (
    format_server_section,
    format_conflicts_section,
    format_summary,
    _HEADER,
)


def _group_entries_by_server(entries: List[CronEntry]) -> Dict[str, List[CronEntry]]:
    """Group a list of CronEntry objects by their server attribute."""
    groups: Dict[str, List[CronEntry]] = {}
    for entry in entries:
        server = entry.server or "unknown"
        groups.setdefault(server, []).append(entry)
    return groups


def generate_report(
    entries: List[CronEntry],
    conflicts: List[Conflict],
    title: str = "Cron Audit Report",
) -> str:
    """Generate a complete human-readable report string.

    Args:
        entries: All parsed CronEntry objects across servers.
        conflicts: Detected Conflict objects.
        title: Optional report title shown in the header.

    Returns:
        A formatted multi-line string suitable for printing or saving.
    """
    lines = [
        _HEADER,
        title.center(60),
        _HEADER,
        "",
    ]

    grouped = _group_entries_by_server(entries)
    for server in sorted(grouped):
        lines.append(format_server_section(server, grouped[server]))
        lines.append("")

    lines.append("")
    lines.append(format_conflicts_section(conflicts))
    lines.append("")
    lines.append(_HEADER)
    lines.append(
        format_summary(
            entry_count=len(entries),
            server_count=len(grouped),
            conflict_count=len(conflicts),
        )
    )
    lines.append(_HEADER)

    return "\n".join(lines)
