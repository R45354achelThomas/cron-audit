"""Renders a ScheduleHeatmap as a compact ASCII table."""

from __future__ import annotations

from cron_audit.schedule_heatmap import DAYS, HOURS, ScheduleHeatmap

_DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def _intensity(count: int, max_count: int) -> str:
    """Return a single character representing relative intensity."""
    if count == 0 or max_count == 0:
        return "."
    ratio = count / max_count
    if ratio < 0.25:
        return "░"
    if ratio < 0.5:
        return "▒"
    if ratio < 0.75:
        return "▓"
    return "█"


def format_heatmap(hm: ScheduleHeatmap) -> str:
    """Return a multi-line ASCII heatmap string."""
    max_count = max(
        hm.grid[d][h] for d in DAYS for h in HOURS
    ) if hm.total() > 0 else 1

    hour_header = "     " + "".join(f"{h:2}" for h in HOURS)
    lines: list[str] = ["Cron Schedule Heatmap (day × hour)", hour_header]

    for d in DAYS:
        row = "".join(
            f" {_intensity(hm.grid[d][h], max_count)} " for h in HOURS
        )
        lines.append(f"{_DAY_LABELS[d]}  {row}")

    peak = hm.peak()
    lines.append("")
    lines.append(
        f"Peak: {_DAY_LABELS[peak.day]} {peak.hour:02d}:00  ({peak.count} job(s))"
    )
    lines.append(f"Total scheduled slots: {hm.total()}")
    return "\n".join(lines)
