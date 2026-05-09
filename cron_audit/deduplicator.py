"""Deduplicator: identify and remove duplicate cron entries across servers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from cron_audit.parser import CronEntry


def _entry_key(entry: CronEntry) -> str:
    """Return a normalised key representing the schedule + command pair."""
    sched = entry.schedule
    parts = [
        sched.minute,
        sched.hour,
        sched.day_of_month,
        sched.month,
        sched.day_of_week,
        entry.command.strip(),
    ]
    return "|".join(parts)


@dataclass
class DuplicateGroup:
    """A set of entries that share an identical schedule and command."""

    key: str
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def servers(self) -> List[str]:
        return [e.server for e in self.entries if e.server]

    @property
    def is_cross_server(self) -> bool:
        """True when duplicates span more than one server."""
        return len(set(self.servers)) > 1

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DuplicateGroup(servers={self.servers}, "
            f"command={self.entries[0].command!r})"
        )


def find_duplicates(entries: List[CronEntry]) -> List[DuplicateGroup]:
    """Return groups of entries that are exact duplicates (schedule + command).

    Only groups with more than one entry are returned.
    """
    buckets: Dict[str, List[CronEntry]] = {}
    for entry in entries:
        key = _entry_key(entry)
        buckets.setdefault(key, []).append(entry)

    return [
        DuplicateGroup(key=key, entries=dupes)
        for key, dupes in buckets.items()
        if len(dupes) > 1
    ]


def deduplicate(
    entries: List[CronEntry],
) -> Tuple[List[CronEntry], List[DuplicateGroup]]:
    """Return a deduplicated entry list and the groups that were collapsed.

    For each duplicate group the *first* occurrence (by original list order)
    is kept; all subsequent duplicates are dropped.
    """
    groups = find_duplicates(entries)
    seen: set[str] = set()
    kept: List[CronEntry] = []

    for entry in entries:
        key = _entry_key(entry)
        if key not in seen:
            seen.add(key)
            kept.append(entry)

    return kept, groups
