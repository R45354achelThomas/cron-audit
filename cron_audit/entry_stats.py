"""Compute per-entry execution statistics from last-run data."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cron_audit.parser import CronEntry
from cron_audit.scheduler import next_run


@dataclass
class EntryStats:
    """Aggregated statistics for a single cron entry."""

    server: str
    command: str
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    run_count: int
    avg_gap_seconds: Optional[float]

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"EntryStats(server={self.server!r}, command={self.command!r}, "
            f"run_count={self.run_count}, next_run={self.next_run})"
        )


def _entry_key(entry: CronEntry) -> str:
    return f"{entry.server}::{entry.command}"


def compute_stats(
    entries: List[CronEntry],
    last_run_map: Dict[str, List[datetime]],
    reference: Optional[datetime] = None,
) -> List[EntryStats]:
    """Return an EntryStats for each entry.

    Args:
        entries: Parsed cron entries.
        last_run_map: Mapping of ``server::command`` to a list of past run
            timestamps (UTC), sorted ascending.
        reference: The point-in-time used as "now" for next_run calculation.
            Defaults to the current UTC time.
    """
    if reference is None:
        reference = datetime.now(timezone.utc)

    stats: List[EntryStats] = []
    for entry in entries:
        key = _entry_key(entry)
        runs: List[datetime] = last_run_map.get(key, [])

        last: Optional[datetime] = runs[-1] if runs else None

        try:
            nxt: Optional[datetime] = next_run(entry, reference)
        except Exception:
            nxt = None

        avg_gap: Optional[float] = None
        if len(runs) >= 2:
            gaps = [
                (runs[i] - runs[i - 1]).total_seconds()
                for i in range(1, len(runs))
            ]
            avg_gap = sum(gaps) / len(gaps)

        stats.append(
            EntryStats(
                server=entry.server or "",
                command=entry.command,
                last_run=last,
                next_run=nxt,
                run_count=len(runs),
                avg_gap_seconds=avg_gap,
            )
        )
    return stats
