"""Detects cron entries that run outside of a defined allowed time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cron_audit.parser import CronEntry
from cron_audit.scheduler import _field_values


@dataclass
class WindowViolation:
    entry: CronEntry
    reason: str

    def __repr__(self) -> str:
        return f"WindowViolation(server={self.entry.server!r}, command={self.entry.command!r}, reason={self.reason!r})"


@dataclass
class RunWindowReport:
    violations: List[WindowViolation] = field(default_factory=list)
    checked: int = 0

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    def __repr__(self) -> str:
        return f"RunWindowReport(checked={self.checked}, violations={len(self.violations)})"


def _hours_for_entry(entry: CronEntry) -> List[int]:
    """Return the concrete hour values an entry can run at."""
    return _field_values(entry.schedule.hour, 0, 23)


def _minutes_for_entry(entry: CronEntry) -> List[int]:
    return _field_values(entry.schedule.minute, 0, 59)


def check_run_window(
    entries: List[CronEntry],
    allowed_start_hour: int,
    allowed_end_hour: int,
    allowed_days: Optional[List[int]] = None,
) -> RunWindowReport:
    """Check whether each entry runs within the allowed window.

    Args:
        entries: List of CronEntry objects to check.
        allowed_start_hour: Inclusive start of the allowed hour window (0-23).
        allowed_end_hour: Inclusive end of the allowed hour window (0-23).
        allowed_days: Optional list of allowed weekday integers (0=Mon … 6=Sun).
                      If None, all days are permitted.

    Returns:
        RunWindowReport containing any violations found.
    """
    if not 0 <= allowed_start_hour <= 23:
        raise ValueError(f"allowed_start_hour must be 0-23, got {allowed_start_hour}")
    if not 0 <= allowed_end_hour <= 23:
        raise ValueError(f"allowed_end_hour must be 0-23, got {allowed_end_hour}")

    violations: List[WindowViolation] = []

    for entry in entries:
        hours = _hours_for_entry(entry)
        outside_hours = [
            h for h in hours
            if not (allowed_start_hour <= h <= allowed_end_hour)
        ]
        if outside_hours:
            sample = ", ".join(str(h) for h in sorted(outside_hours)[:5])
            violations.append(WindowViolation(
                entry=entry,
                reason=(
                    f"runs at hour(s) [{sample}] outside allowed window "
                    f"{allowed_start_hour:02d}:00-{allowed_end_hour:02d}:59"
                ),
            ))
            continue

        if allowed_days is not None:
            days = _field_values(entry.schedule.day_of_week, 0, 6)
            outside_days = [d for d in days if d not in allowed_days]
            if outside_days:
                sample = ", ".join(str(d) for d in sorted(outside_days))
                violations.append(WindowViolation(
                    entry=entry,
                    reason=f"runs on weekday(s) [{sample}] not in allowed days {allowed_days}",
                ))

    return RunWindowReport(violations=violations, checked=len(entries))
