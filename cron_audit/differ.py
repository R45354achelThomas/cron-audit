"""Diff cron entries between two snapshots (e.g. two runs or two servers)."""

from dataclasses import dataclass, field
from typing import List, Tuple

from cron_audit.parser import CronEntry


@dataclass
class DiffResult:
    """Result of diffing two sets of cron entries."""

    added: List[CronEntry] = field(default_factory=list)
    removed: List[CronEntry] = field(default_factory=list)
    unchanged: List[CronEntry] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)

    def summary(self) -> str:
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} added")
        if self.removed:
            parts.append(f"-{len(self.removed)} removed")
        if not parts:
            return "no changes"
        return ", ".join(parts)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DiffResult(added={len(self.added)}, "
            f"removed={len(self.removed)}, "
            f"unchanged={len(self.unchanged)})"
        )


def _entry_key(entry: CronEntry) -> Tuple[str, str]:
    """Stable identity key for a cron entry: (schedule_string, command)."""
    schedule = (
        f"{entry.schedule.minute} {entry.schedule.hour} "
        f"{entry.schedule.day} {entry.schedule.month} "
        f"{entry.schedule.weekday}"
    )
    return (schedule, entry.command.strip())


def diff_entries(
    before: List[CronEntry],
    after: List[CronEntry],
) -> DiffResult:
    """Compare two lists of CronEntry and return a DiffResult.

    Entries are matched by (schedule, command) pairs, ignoring server name
    so diffs across servers are meaningful.
    """
    before_keys = {_entry_key(e): e for e in before}
    after_keys = {_entry_key(e): e for e in after}

    added = [e for k, e in after_keys.items() if k not in before_keys]
    removed = [e for k, e in before_keys.items() if k not in after_keys]
    unchanged = [e for k, e in before_keys.items() if k in after_keys]

    return DiffResult(added=added, removed=removed, unchanged=unchanged)


def diff_servers(
    entries: List[CronEntry],
    server_a: str,
    server_b: str,
) -> DiffResult:
    """Diff cron entries between two named servers within a combined list."""
    a = [e for e in entries if e.server == server_a]
    b = [e for e in entries if e.server == server_b]
    return diff_entries(a, b)
