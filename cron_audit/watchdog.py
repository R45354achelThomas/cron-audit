"""Watchdog: detect cron entries that have not run recently based on expected schedule."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cron_audit.parser import CronEntry
from cron_audit.scheduler import next_run


@dataclass
class StaleEntry:
    """A cron entry whose last known run is overdue relative to its schedule."""

    entry: CronEntry
    last_run: Optional[datetime]
    expected_next: datetime
    overdue_seconds: float

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"StaleEntry(server={self.entry.server!r}, "
            f"command={self.entry.command!r}, "
            f"overdue_seconds={self.overdue_seconds:.0f})"
        )


def check_staleness(
    entries: List[CronEntry],
    last_run_map: dict,
    reference_time: Optional[datetime] = None,
    grace_seconds: float = 0.0,
) -> List[StaleEntry]:
    """Return entries that are overdue given *last_run_map*.

    Args:
        entries: All cron entries to evaluate.
        last_run_map: Mapping of ``(server, command)`` -> last run ``datetime``
            (timezone-aware UTC).  Missing keys are treated as never run.
        reference_time: The "now" used for comparison.  Defaults to UTC now.
        grace_seconds: Extra seconds of tolerance before flagging an entry.

    Returns:
        List of :class:`StaleEntry` objects, one per overdue entry.
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    stale: List[StaleEntry] = []

    for entry in entries:
        key = (entry.server, entry.command)
        last_run: Optional[datetime] = last_run_map.get(key)

        # Determine the next expected run after last_run (or epoch if never run).
        base = last_run if last_run is not None else datetime(1970, 1, 1, tzinfo=timezone.utc)
        expected = next_run(entry, base)

        deadline = expected.timestamp() + grace_seconds
        if reference_time.timestamp() > deadline:
            overdue = reference_time.timestamp() - expected.timestamp()
            stale.append(
                StaleEntry(
                    entry=entry,
                    last_run=last_run,
                    expected_next=expected,
                    overdue_seconds=max(overdue, 0.0),
                )
            )

    return stale
