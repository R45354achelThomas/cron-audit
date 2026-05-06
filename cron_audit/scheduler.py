"""Utilities for computing next-run times and schedule summaries for cron entries."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from cron_audit.parser import CronEntry


def _field_values(field: str, min_val: int, max_val: int) -> list[int]:
    """Expand a single cron field into a sorted list of matching integer values."""
    values: set[int] = set()
    for part in field.split(","):
        if part == "*":
            values.update(range(min_val, max_val + 1))
        elif "/" in part:
            base, step = part.split("/", 1)
            step = int(step)
            start = min_val if base == "*" else int(base.split("-")[0])
            end = max_val if base == "*" else (int(base.split("-")[1]) if "-" in base else start)
            values.update(range(start, end + 1, step))
        elif "-" in part:
            lo, hi = part.split("-", 1)
            values.update(range(int(lo), int(hi) + 1))
        else:
            values.add(int(part))
    return sorted(v for v in values if min_val <= v <= max_val)


def next_run(entry: CronEntry, after: Optional[datetime] = None) -> datetime:
    """Return the next datetime (after *after*) at which *entry* would fire.

    Raises ValueError if the schedule cannot produce a valid datetime within
    a reasonable search window (1 year).
    """
    if after is None:
        after = datetime.now().replace(second=0, microsecond=0)

    schedule = entry.schedule
    minutes = _field_values(schedule.minute, 0, 59)
    hours = _field_values(schedule.hour, 0, 23)
    days = _field_values(schedule.day, 1, 31)
    months = _field_values(schedule.month, 1, 12)
    weekdays = _field_values(schedule.weekday, 0, 6)

    candidate = after + timedelta(minutes=1)
    deadline = after + timedelta(days=366)

    while candidate <= deadline:
        if candidate.month not in months:
            candidate = (candidate.replace(day=1) + timedelta(days=32)).replace(
                day=1, hour=0, minute=0
            )
            continue
        if candidate.day not in days or candidate.weekday() not in [w % 7 for w in weekdays]:
            candidate = (candidate + timedelta(days=1)).replace(hour=0, minute=0)
            continue
        if candidate.hour not in hours:
            candidate = (candidate + timedelta(hours=1)).replace(minute=0)
            continue
        if candidate.minute not in minutes:
            candidate += timedelta(minutes=1)
            continue
        return candidate

    raise ValueError(f"No valid next run found for entry: {entry.command}")


def human_schedule(entry: CronEntry) -> str:
    """Return a brief human-readable description of an entry's schedule."""
    s = entry.schedule
    if s.minute == "0" and s.hour == "0" and s.day == "1" and s.month == "*":
        return "monthly (1st, midnight)"
    if s.minute == "0" and s.hour == "0" and s.weekday == "*":
        return "daily at midnight"
    if s.minute == "0" and s.weekday == "*" and s.day == "*":
        return f"hourly at minute {s.hour}" if s.hour == "0" else f"every day at {s.hour}:00"
    if s.minute == "0" and s.hour == "*":
        return "every hour on the hour"
    return f"{s.minute} {s.hour} {s.day} {s.month} {s.weekday}"
