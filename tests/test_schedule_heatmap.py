"""Tests for schedule_heatmap and formatter_heatmap."""

from __future__ import annotations

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.schedule_heatmap import ScheduleHeatmap, build_heatmap
from cron_audit.formatter_heatmap import format_heatmap, _intensity


def make_entry(
    minute="0",
    hour="*",
    dom="*",
    month="*",
    dow="*",
    command="/usr/bin/job",
    server="srv1",
) -> CronEntry:
    schedule = CronSchedule(
        minute=minute, hour=hour, day_of_month=dom,
        month=month, day_of_week=dow,
    )
    return CronEntry(schedule=schedule, command=command, server=server)


class TestScheduleHeatmap:
    def test_empty_entries_produces_zero_grid(self):
        hm = build_heatmap([])
        assert hm.total() == 0

    def test_wildcard_hour_fills_all_hours(self):
        entry = make_entry(hour="*", dow="1")  # every hour on Monday
        hm = build_heatmap([entry])
        for h in range(24):
            assert hm.get(day=1, hour=h) == 1

    def test_specific_hour_only_increments_that_cell(self):
        entry = make_entry(hour="3", dow="2")
        hm = build_heatmap([entry])
        assert hm.get(day=2, hour=3) == 1
        assert hm.get(day=2, hour=4) == 0

    def test_multiple_entries_accumulate(self):
        e1 = make_entry(hour="6", dow="0")
        e2 = make_entry(hour="6", dow="0")
        hm = build_heatmap([e1, e2])
        assert hm.get(day=0, hour=6) == 2

    def test_wildcard_dow_fills_all_days(self):
        entry = make_entry(hour="12", dow="*")
        hm = build_heatmap([entry])
        for d in range(7):
            assert hm.get(day=d, hour=12) == 1

    def test_peak_returns_highest_cell(self):
        e1 = make_entry(hour="9", dow="1")
        e2 = make_entry(hour="9", dow="1")
        e3 = make_entry(hour="9", dow="1")
        e4 = make_entry(hour="10", dow="1")
        hm = build_heatmap([e1, e2, e3, e4])
        peak = hm.peak()
        assert peak.hour == 9
        assert peak.day == 1
        assert peak.count == 3

    def test_total_counts_all_slots(self):
        entry = make_entry(hour="0", dow="0")
        hm = build_heatmap([entry])
        assert hm.total() == 1


class TestFormatHeatmap:
    def test_output_contains_day_labels(self):
        hm = build_heatmap([])
        output = format_heatmap(hm)
        assert "Mon" in output
        assert "Fri" in output

    def test_output_contains_peak_line(self):
        entry = make_entry(hour="14", dow="3")
        hm = build_heatmap([entry])
        output = format_heatmap(hm)
        assert "Peak" in output
        assert "14:00" in output

    def test_output_contains_total_line(self):
        hm = build_heatmap([])
        output = format_heatmap(hm)
        assert "Total" in output

    def test_intensity_empty_returns_dot(self):
        assert _intensity(0, 10) == "."

    def test_intensity_full_returns_block(self):
        assert _intensity(10, 10) == "█"

    def test_intensity_zero_max_returns_dot(self):
        assert _intensity(0, 0) == "."
