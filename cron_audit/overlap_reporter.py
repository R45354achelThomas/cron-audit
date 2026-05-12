"""Generates a focused report of overlapping/conflicting cron schedules.

Groups conflicts by severity and provides per-server breakdowns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from cron_audit.conflict_detector import Conflict
from cron_audit.parser import CronEntry


@dataclass
class OverlapReport:
    """Structured result of an overlap analysis."""

    high: List[Conflict] = field(default_factory=list)
    medium: List[Conflict] = field(default_factory=list)
    low: List[Conflict] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.high) + len(self.medium) + len(self.low)

    def by_server(self) -> Dict[str, List[Conflict]]:
        """Return conflicts grouped by the server of the first entry."""
        groups: Dict[str, List[Conflict]] = {}
        for conflict in self.high + self.medium + self.low:
            server = conflict.entry_a.server or "unknown"
            groups.setdefault(server, []).append(conflict)
        return groups

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"OverlapReport(high={len(self.high)}, "
            f"medium={len(self.medium)}, low={len(self.low)})"
        )


def _severity(conflict: Conflict) -> str:
    """Derive a simple severity from conflict reason text."""
    reason = conflict.reason.lower()
    if "duplicate" in reason or "identical" in reason:
        return "high"
    if "overlap" in reason:
        return "medium"
    return "low"


def build_overlap_report(conflicts: List[Conflict]) -> OverlapReport:
    """Classify *conflicts* by severity and return an OverlapReport."""
    report = OverlapReport()
    for conflict in conflicts:
        sev = _severity(conflict)
        if sev == "high":
            report.high.append(conflict)
        elif sev == "medium":
            report.medium.append(conflict)
        else:
            report.low.append(conflict)
    return report


def format_overlap_report(report: OverlapReport) -> str:
    """Render an OverlapReport as a human-readable string."""
    if report.total == 0:
        return "No overlapping cron schedules detected.\n"

    lines: List[str] = []
    lines.append(f"Overlap Report  ({report.total} conflict(s))")
    lines.append("=" * 50)

    for label, conflicts in (
        ("HIGH", report.high),
        ("MEDIUM", report.medium),
        ("LOW", report.low),
    ):
        if not conflicts:
            continue
        lines.append(f"\n[{label}] {len(conflicts)} conflict(s)")
        lines.append("-" * 40)
        for c in conflicts:
            lines.append(f"  {c}")

    lines.append("")
    return "\n".join(lines)
