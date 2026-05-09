"""Filter cron entries by tag, server, command pattern, or schedule fields."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from cron_audit.parser import CronEntry


@dataclass
class FilterCriteria:
    """Criteria used to select a subset of CronEntry objects."""

    servers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    command_pattern: Optional[str] = None
    minute: Optional[str] = None
    hour: Optional[str] = None

    def is_empty(self) -> bool:
        """Return True when no criteria have been set."""
        return (
            not self.servers
            and not self.tags
            and self.command_pattern is None
            and self.minute is None
            and self.hour is None
        )


def _matches_server(entry: CronEntry, servers: List[str]) -> bool:
    if not servers:
        return True
    return entry.server in servers


def _matches_tags(entry: CronEntry, tags: List[str]) -> bool:
    if not tags:
        return True
    entry_tags = getattr(entry, "tags", []) or []
    return any(t in entry_tags for t in tags)


def _matches_command(entry: CronEntry, pattern: Optional[str]) -> bool:
    if pattern is None:
        return True
    try:
        return bool(re.search(pattern, entry.command))
    except re.error:
        return entry.command == pattern


def _matches_field(actual: str, expected: Optional[str]) -> bool:
    if expected is None:
        return True
    return actual == expected


def filter_entries(
    entries: List[CronEntry], criteria: FilterCriteria
) -> List[CronEntry]:
    """Return entries that satisfy *all* conditions in *criteria*."""
    if criteria.is_empty():
        return list(entries)

    result = []
    for entry in entries:
        if not _matches_server(entry, criteria.servers):
            continue
        if not _matches_tags(entry, criteria.tags):
            continue
        if not _matches_command(entry, criteria.command_pattern):
            continue
        if not _matches_field(entry.schedule.minute, criteria.minute):
            continue
        if not _matches_field(entry.schedule.hour, criteria.hour):
            continue
        result.append(entry)
    return result
