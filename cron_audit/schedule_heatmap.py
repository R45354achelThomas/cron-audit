"""Builds a frequency heatmap of cron job executions across hours and weekdays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from cron_audit.parser import CronEntry
from cron_audit.scheduler import _field_values

# Axes
HOURS = list(range(24))
DAYS = list(range(7))  # 0=Sunday … 6=Saturday


@dataclass
class HeatmapCell:
    hour: int
    day: int
    count: int = 0

    def __repr__(self) -> str:  # pragma: no cover
        return f"HeatmapCell(day={self.day}, hour={self.hour}, count={self.count})"


@dataclass
class ScheduleHeatmap:
    """A 7×24 grid counting how many jobs fire at each (weekday, hour) pair."""

    # grid[day][hour] = count
    grid: Dict[int, Dict[int, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for d in DAYS:
            self.grid.setdefault(d, {h: 0 for h in HOURS})

    def get(self, day: int, hour: int) -> int:
        return self.grid.get(day, {}).get(hour, 0)

    def peak(self) -> HeatmapCell:
        """Return the (day, hour) cell with the highest count."""
        best = HeatmapCell(hour=0, day=0, count=-1)
        for d, hours in self.grid.items():
            for h, cnt in hours.items():
                if cnt > best.count:
                    best = HeatmapCell(hour=h, day=d, count=cnt)
        return best

    def total(self) -> int:
        return sum(cnt for hours in self.grid.values() for cnt in hours.values())

    def __repr__(self) -> str:  # pragma: no cover
        return f"ScheduleHeatmap(total={self.total()})"


def build_heatmap(entries: Sequence[CronEntry]) -> ScheduleHeatmap:
    """Accumulate a heatmap from a collection of CronEntry objects."""
    hm = ScheduleHeatmap()
    for entry in entries:
        s = entry.schedule
        hours = _field_values(s.hour, 0, 23)
        days = _field_values(s.day_of_week, 0, 6)
        for d in days:
            for h in hours:
                hm.grid[d % 7][h] += 1
    return hm
