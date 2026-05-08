"""Summarizes cron audit pipeline results into structured statistics."""

from dataclasses import dataclass, field
from typing import Dict, List
from collections import Counter

from cron_audit.pipeline import PipelineResult
from cron_audit.conflict_detector import Conflict


@dataclass
class AuditSummary:
    total_entries: int = 0
    total_conflicts: int = 0
    servers: List[str] = field(default_factory=list)
    entries_per_server: Dict[str, int] = field(default_factory=dict)
    conflicts_per_server: Dict[str, int] = field(default_factory=dict)
    high_severity_conflicts: int = 0
    low_severity_conflicts: int = 0
    most_common_commands: List[tuple] = field(default_factory=list)
    tags_frequency: Dict[str, int] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"AuditSummary(servers={len(self.servers)}, "
            f"entries={self.total_entries}, "
            f"conflicts={self.total_conflicts}, "
            f"high_severity={self.high_severity_conflicts})"
        )


def _severity(conflict: Conflict) -> str:
    """Mirrors severity logic from formatter for consistency."""
    if conflict.reason and "duplicate" in conflict.reason.lower():
        return "high"
    return "low"


def summarize(result: PipelineResult, top_commands: int = 5) -> AuditSummary:
    """Build an AuditSummary from a PipelineResult.

    Args:
        result: The pipeline result containing entries and conflicts.
        top_commands: How many top commands to include in most_common_commands.

    Returns:
        A populated AuditSummary dataclass.
    """
    summary = AuditSummary()

    summary.total_entries = len(result.entries)
    summary.total_conflicts = len(result.conflicts)

    server_set = set()
    entries_per_server: Counter = Counter()
    conflicts_per_server: Counter = Counter()
    command_counter: Counter = Counter()
    tag_counter: Counter = Counter()

    for entry in result.entries:
        server = entry.server or "unknown"
        server_set.add(server)
        entries_per_server[server] += 1
        command_counter[entry.command] += 1
        for tag in getattr(entry, "tags", []) or []:
            tag_counter[tag] += 1

    for conflict in result.conflicts:
        sev = _severity(conflict)
        if sev == "high":
            summary.high_severity_conflicts += 1
        else:
            summary.low_severity_conflicts += 1

        for entry in (conflict.entry_a, conflict.entry_b):
            server = entry.server or "unknown"
            server_set.add(server)
            conflicts_per_server[server] += 1

    summary.servers = sorted(server_set)
    summary.entries_per_server = dict(entries_per_server)
    summary.conflicts_per_server = dict(conflicts_per_server)
    summary.most_common_commands = command_counter.most_common(top_commands)
    summary.tags_frequency = dict(tag_counter)

    return summary
