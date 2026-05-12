"""Analyse how frequently each unique command is scheduled across all servers."""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict, List, Sequence

from cron_audit.parser import CronEntry
from cron_audit.scheduler import _field_values


@dataclass
class CommandFrequency:
    """Aggregated scheduling frequency for a single command."""

    command: str
    servers: List[str]
    # estimated runs per day across all entries
    runs_per_day: float
    entry_count: int

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CommandFrequency(command={self.command!r}, "
            f"servers={self.servers!r}, runs_per_day={self.runs_per_day:.1f}, "
            f"entry_count={self.entry_count})"
        )


def _runs_per_day(entry: CronEntry) -> float:
    """Estimate how many times *entry* runs in a 24-hour period."""
    s = entry.schedule
    minutes = len(_field_values(s.minute, 0, 59))
    hours = len(_field_values(s.hour, 0, 23))
    dom = _field_values(s.dom, 1, 31)
    month = _field_values(s.month, 1, 12)
    dow = _field_values(s.dow, 0, 6)

    # If both dom and dow are restricted, cron uses OR semantics;
    # for a daily estimate we treat them independently and take the
    # more permissive of the two to avoid over-counting.
    dom_fraction = len(dom) / 31
    dow_fraction = len(dow) / 7
    day_fraction = max(dom_fraction, dow_fraction)
    month_fraction = len(month) / 12

    # runs per day = slots_per_day * probability that today qualifies
    return minutes * hours * day_fraction * month_fraction


def compute_command_frequency(
    entries: Sequence[CronEntry],
) -> List[CommandFrequency]:
    """Return a :class:`CommandFrequency` record for every distinct command.

    Results are sorted descending by *runs_per_day*.
    """
    freq: Dict[str, float] = defaultdict(float)
    servers: Dict[str, List[str]] = defaultdict(list)
    counts: Dict[str, int] = defaultdict(int)

    for entry in entries:
        cmd = entry.command
        freq[cmd] += _runs_per_day(entry)
        server = entry.server or "unknown"
        if server not in servers[cmd]:
            servers[cmd].append(server)
        counts[cmd] += 1

    results = [
        CommandFrequency(
            command=cmd,
            servers=servers[cmd],
            runs_per_day=freq[cmd],
            entry_count=counts[cmd],
        )
        for cmd in freq
    ]
    results.sort(key=lambda r: r.runs_per_day, reverse=True)
    return results
