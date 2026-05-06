"""Tests for cron_audit.scheduler."""

from datetime import datetime

import pytest

from cron_audit.parser import CronEntry
from cron_audit.scheduler import _field_values, next_run, human_schedule


def make_entry(minute="0", hour="*", day="*", month="*", weekday="*", command="/bin/cmd", server="srv"):
    from cron_audit.parser import CronSchedule
    schedule = CronSchedule(minute=minute, hour=hour, day=day, month=month, weekday=weekday)
    return CronEntry(schedule=schedule, command=command, server=server, raw="")


class TestFieldValues:
    def test_wildcard_minute(self):
        assert _field_values("*", 0, 59) == list(range(60))

    def test_single_value(self):
        assert _field_values("5", 0, 59) == [5]

    def test_range(self):
        assert _field_values("1-3", 0, 59) == [1, 2, 3]

    def test_step(self):
        assert _field_values("*/15", 0, 59) == [0, 15, 30, 45]

    def test_list(self):
        assert _field_values("1,3,5", 0, 59) == [1, 3, 5]

    def test_step_with_range(self):
        assert _field_values("0-10/5", 0, 59) == [0, 5, 10]


class TestNextRun:
    def test_next_run_every_hour(self):
        entry = make_entry(minute="0", hour="*")
        after = datetime(2024, 1, 15, 10, 30)
        result = next_run(entry, after=after)
        assert result == datetime(2024, 1, 15, 11, 0)

    def test_next_run_daily_midnight(self):
        entry = make_entry(minute="0", hour="0")
        after = datetime(2024, 1, 15, 10, 0)
        result = next_run(entry, after=after)
        assert result == datetime(2024, 1, 16, 0, 0)

    def test_next_run_specific_minute(self):
        entry = make_entry(minute="30", hour="14")
        after = datetime(2024, 1, 15, 14, 0)
        result = next_run(entry, after=after)
        assert result == datetime(2024, 1, 15, 14, 30)

    def test_next_run_crosses_month(self):
        entry = make_entry(minute="0", hour="0", day="1")
        after = datetime(2024, 1, 15, 0, 0)
        result = next_run(entry, after=after)
        assert result.day == 1
        assert result.month == 2

    def test_next_run_is_after_given_time(self):
        entry = make_entry(minute="*/5")
        after = datetime(2024, 3, 10, 8, 7)
        result = next_run(entry, after=after)
        assert result > after
        assert result.minute % 5 == 0


class TestHumanSchedule:
    def test_daily_midnight(self):
        entry = make_entry(minute="0", hour="0", day="*", month="*", weekday="*")
        assert human_schedule(entry) == "daily at midnight"

    def test_monthly(self):
        entry = make_entry(minute="0", hour="0", day="1", month="*", weekday="*")
        assert human_schedule(entry) == "monthly (1st, midnight)"

    def test_every_hour(self):
        entry = make_entry(minute="0", hour="*", day="*", month="*", weekday="*")
        assert human_schedule(entry) == "every hour on the hour"

    def test_fallback_raw(self):
        entry = make_entry(minute="17", hour="3", day="*", month="*", weekday="1")
        result = human_schedule(entry)
        assert "17" in result and "3" in result
