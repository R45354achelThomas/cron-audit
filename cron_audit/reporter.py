"""Generates a unified human-readable report from parsed cron entries and detected conflicts."""

from typing import List, Dict
from datetime import datetime
from cron_audit.parser import CronEntry
from cron_audit.conflict_detector import Conflict


def _group_entries_by_server(entries: List[CronEntry]) -> Dict[str, List[CronEntry]]:
    """Group cron entries by their server attribute."""
    groups: Dict[str, List[CronEntry]] = {}
    for entry in entries:
        server = getattr(entry, "server", "unknown")
        groups.setdefault(server, []).append(entry)
    return groups


def generate_report(
    entries: List[CronEntry],
    conflicts: List[Conflict],
    title: str = "Cron Audit Report",
) -> str:
    """Generate a formatted plain-text report.

    Args:
        entries: All parsed cron entries across servers.
        conflicts: Detected conflicts from conflict_detector.
        title: Optional report title.

    Returns:
        A multi-line string report.
    """
    lines: List[str] = []
    separator = "=" * 60
    thin_sep = "-" * 60

    lines.append(separator)
    lines.append(f"  {title}")
    lines.append(f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append(separator)
    lines.append(f"Total entries : {len(entries)}")
    lines.append(f"Total conflicts: {len(conflicts)}")
    lines.append("")

    # --- Entries section ---
    lines.append("CRON ENTRIES BY SERVER")
    lines.append(thin_sep)
    grouped = _group_entries_by_server(entries)
    if grouped:
        for server, server_entries in sorted(grouped.items()):
            lines.append(f"\n[{server}]  ({len(server_entries)} job(s))")
            for entry in server_entries:
                lines.append(f"  {entry}")
    else:
        lines.append("  (no entries)")

    lines.append("")

    # --- Conflicts section ---
    lines.append("CONFLICTS DETECTED")
    lines.append(thin_sep)
    if conflicts:
        for idx, conflict in enumerate(conflicts, start=1):
            lines.append(f"\n[{idx}] {conflict}")
    else:
        lines.append("  No conflicts detected.")

    lines.append("")
    lines.append(separator)
    return "\n".join(lines)
