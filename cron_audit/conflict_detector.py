"""Detect scheduling conflicts between cron entries."""

from dataclasses import dataclass
from typing import List, Tuple
from .parser import CronEntry


@dataclass
class Conflict:
    """Represents a scheduling conflict between two cron entries."""
    entry_a: CronEntry
    entry_b: CronEntry
    reason: str

    def __str__(self) -> str:
        return (
            f"CONFLICT [{self.reason}]\n"
            f"  A: {self.entry_a}\n"
            f"  B: {self.entry_b}"
        )


def _normalize_field(field: str) -> set:
    """Expand a cron field into a set of integer values (0-59 or 0-23 range)."""
    values = set()
    parts = field.split(",")
    for part in parts:
        if part == "*":
            return None  # wildcard matches everything
        if "/" in part:
            base, step = part.split("/")
            step = int(step)
            start = 0 if base == "*" else int(base)
            end = 59 if base == "*" else int(base)
            if base == "*":
                for i in range(start, 60, step):
                    values.add(i)
            else:
                values.add(start)
        elif "-" in part:
            start, end = part.split("-")
            values.update(range(int(start), int(end) + 1))
        else:
            values.add(int(part))
    return values


def _fields_overlap(field_a: str, field_b: str) -> bool:
    """Return True if two cron schedule fields can fire at the same time."""
    set_a = _normalize_field(field_a)
    set_b = _normalize_field(field_b)
    if set_a is None or set_b is None:
        return True
    return bool(set_a & set_b)


def _schedules_overlap(a: CronEntry, b: CronEntry) -> bool:
    """Return True if two entries could fire at the same minute."""
    fields = [
        (a.schedule.minute, b.schedule.minute),
        (a.schedule.hour, b.schedule.hour),
        (a.schedule.day_of_month, b.schedule.day_of_month),
        (a.schedule.month, b.schedule.month),
        (a.schedule.day_of_week, b.schedule.day_of_week),
    ]
    return all(_fields_overlap(fa, fb) for fa, fb in fields)


def detect_conflicts(entries: List[CronEntry]) -> List[Conflict]:
    """Find all pairs of cron entries with overlapping schedules."""
    conflicts: List[Conflict] = []
    for i, entry_a in enumerate(entries):
        for entry_b in entries[i + 1:]:
            if _schedules_overlap(entry_a, entry_b):
                reason = "overlapping schedule"
                if entry_a.command == entry_b.command:
                    reason = "duplicate command with overlapping schedule"
                conflicts.append(Conflict(entry_a, entry_b, reason))
    return conflicts
