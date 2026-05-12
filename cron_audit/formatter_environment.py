"""Format an :class:`EnvironmentReport` for human-readable console output."""
from __future__ import annotations

from typing import List

from cron_audit.environment_classifier import EnvironmentReport
from cron_audit.formatter import format_entry


_ENV_ORDER = ["production", "staging", "development", "testing", "unclassified"]


def _header(text: str, width: int = 60) -> str:
    bar = "=" * width
    return f"{bar}\n  {text}\n{bar}"


def _sorted_envs(report: EnvironmentReport) -> List[str]:
    """Return environments in a stable, human-friendly order."""
    ordered = [e for e in _ENV_ORDER if e in report.groups]
    extras = sorted(e for e in report.environments if e not in _ENV_ORDER)
    return ordered + extras


def format_environment_report(report: EnvironmentReport) -> str:
    """Return a multi-section string representation of *report*."""
    if not report.groups:
        return "No entries to classify.\n"

    sections: List[str] = []
    for env in _sorted_envs(report):
        group = report.groups[env]
        lines: List[str] = [_header(f"Environment: {env.upper()} ({len(group.entries)} entries)")]
        if group.server_names:
            lines.append(f"  Servers: {', '.join(group.server_names)}")
        lines.append("")
        for entry in group.entries:
            lines.append(format_entry(entry))
        sections.append("\n".join(lines))

    return "\n\n".join(sections) + "\n"
