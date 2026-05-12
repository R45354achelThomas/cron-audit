"""Estimates rough resource usage (CPU/IO load) for cron schedules.

Provides a simple heuristic score based on execution frequency and
keyword hints in the command string.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cron_audit.parser import CronEntry
from cron_audit.scheduler import _field_values

# Keywords that hint at heavier resource usage
_HEAVY_KEYWORDS = (
    "rsync", "pg_dump", "mysqldump", "find", "tar", "gzip", "bzip2",
    "ffmpeg", "convert", "python", "ruby", "java", "node", "rake",
)
_LIGHT_KEYWORDS = ("echo", "touch", "curl", "wget", "ping", "ls", "cat")


@dataclass
class ResourceEstimate:
    entry: CronEntry
    runs_per_day: float
    keyword_weight: float  # 0.5 light … 1.0 normal … 2.0 heavy
    score: float           # runs_per_day * keyword_weight

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ResourceEstimate(server={self.entry.server!r}, "
            f"command={self.entry.command!r}, score={self.score:.2f})"
        )


def _keyword_weight(command: str) -> float:
    cmd_lower = command.lower()
    for kw in _HEAVY_KEYWORDS:
        if kw in cmd_lower:
            return 2.0
    for kw in _LIGHT_KEYWORDS:
        if kw in cmd_lower:
            return 0.5
    return 1.0


def _runs_per_day(entry: CronEntry) -> float:
    """Return the expected number of executions in a 24-hour period."""
    minutes = len(_field_values(entry.schedule.minute, 0, 59))
    hours = len(_field_values(entry.schedule.hour, 0, 23))
    return float(minutes * hours)


def estimate_resources(entries: List[CronEntry]) -> List[ResourceEstimate]:
    """Return a ResourceEstimate for every entry, sorted by score descending."""
    results: List[ResourceEstimate] = []
    for entry in entries:
        rpd = _runs_per_day(entry)
        kw = _keyword_weight(entry.command)
        results.append(
            ResourceEstimate(
                entry=entry,
                runs_per_day=rpd,
                keyword_weight=kw,
                score=rpd * kw,
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results
