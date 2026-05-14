"""Text formatter for TimeZoneReport."""
from __future__ import annotations

from typing import List

from cron_audit.time_zone_report import TimeZoneReport


def _header(text: str, char: str = "=") -> str:
    return f"{text}\n{char * len(text)}"


def format_timezone_report(report: TimeZoneReport, *, color: bool = False) -> str:
    """Return a human-readable summary of the time-zone report."""
    lines: List[str] = [_header("Time Zone Report")]

    if not report.groups:
        lines.append("  No entries found.")
        return "\n".join(lines)

    for tz in report.timezones:
        group = report.groups[tz]
        lines.append("")
        lines.append(_header(f"  Zone: {tz}  ({len(group.entries)} entries)", "-"))
        lines.append(f"  Servers: {', '.join(group.server_names) or 'none'}")
        for entry in group.entries:
            server_tag = f"[{entry.server}] " if entry.server else ""
            lines.append(f"    {server_tag}{entry.schedule_str()}  {entry.command}")

    if report.has_mixed:
        warning = "WARNING: servers with mixed time zones detected"
        if color:
            warning = f"\033[33m{warning}\033[0m"
        lines.append("")
        lines.append(warning)
        for srv in report.mixed_servers:
            lines.append(f"  - {srv}")
    else:
        lines.append("")
        lines.append("All servers operate in a single time zone.")

    return "\n".join(lines)
