"""Generates a summary report grouped by tags across all cron entries."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from cron_audit.parser import CronEntry


@dataclass
class TagGroup:
    """All entries that share a given tag."""

    tag: str
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def server_names(self) -> List[str]:
        return sorted({e.server for e in self.entries if e.server})

    def __repr__(self) -> str:  # pragma: no cover
        return f"TagGroup(tag={self.tag!r}, count={len(self.entries)})"


@dataclass
class TagReport:
    """Complete tag-based breakdown of all cron entries."""

    groups: Dict[str, TagGroup] = field(default_factory=dict)
    untagged: List[CronEntry] = field(default_factory=list)

    @property
    def total_tagged(self) -> int:
        return sum(len(g.entries) for g in self.groups.values())

    @property
    def total_untagged(self) -> int:
        return len(self.untagged)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TagReport(tags={len(self.groups)}, "
            f"tagged={self.total_tagged}, untagged={self.total_untagged})"
        )


def build_tag_report(entries: List[CronEntry]) -> TagReport:
    """Group *entries* by their tags and return a :class:`TagReport`.

    An entry may appear in multiple groups if it carries multiple tags.
    Entries with no tags are collected in :attr:`TagReport.untagged`.
    """
    groups: Dict[str, TagGroup] = defaultdict(lambda: TagGroup(tag=""))
    untagged: List[CronEntry] = []

    for entry in entries:
        tags = getattr(entry, "tags", None) or []
        if not tags:
            untagged.append(entry)
            continue
        for tag in tags:
            if tag not in groups:
                groups[tag] = TagGroup(tag=tag)
            groups[tag].entries.append(entry)

    return TagReport(groups=dict(sorted(groups.items())), untagged=untagged)


def format_tag_report(report: TagReport) -> str:
    """Return a human-readable text representation of *report*."""
    lines: List[str] = ["=== Tag Report ===", ""]

    if not report.groups and not report.untagged:
        lines.append("No entries found.")
        return "\n".join(lines)

    for tag, group in report.groups.items():
        servers = ", ".join(group.server_names) if group.server_names else "unknown"
        lines.append(f"[{tag}]  ({len(group.entries)} entries, servers: {servers})")
        for entry in group.entries:
            lines.append(f"  {entry.server or '?'}  {entry.schedule_str()}  {entry.command}")
        lines.append("")

    if report.untagged:
        lines.append(f"[untagged]  ({len(report.untagged)} entries)")
        for entry in report.untagged:
            lines.append(f"  {entry.server or '?'}  {entry.schedule_str()}  {entry.command}")
        lines.append("")

    lines.append(
        f"Summary: {len(report.groups)} tag(s), "
        f"{report.total_tagged} tagged, {report.total_untagged} untagged."
    )
    return "\n".join(lines)
