"""Tests for cron_audit.command_frequency."""
from __future__ import annotations

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.command_frequency import (
    CommandFrequency,
    _runs_per_day,
    compute_command_frequency,
)


def make_entry(
    command: str,
    minute: str = "0",
    hour: str = "*",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
    server: str = "web1",
) -> CronEntry:
    schedule = CronSchedule(
        minute=minute, hour=hour, dom=dom, month=month, dow=dow
    )
    return CronEntry(schedule=schedule, command=command, server=server)


class TestRunsPerDay:
    def test_once_per_hour_all_hours(self):
        entry = make_entry("backup.sh", minute="0", hour="*")
        assert _runs_per_day(entry) == pytest.approx(24.0)

    def test_once_per_day_at_midnight(self):
        entry = make_entry("cleanup.sh", minute="0", hour="0")
        assert _runs_per_day(entry) == pytest.approx(1.0)

    def test_every_minute_every_hour(self):
        entry = make_entry("poll.sh", minute="*", hour="*")
        assert _runs_per_day(entry) == pytest.approx(60 * 24)

    def test_restricted_month_reduces_daily_estimate(self):
        # Only runs in January (1/12 of months)
        entry = make_entry("report.sh", minute="0", hour="9", month="1")
        full = make_entry("report.sh", minute="0", hour="9", month="*")
        assert _runs_per_day(entry) < _runs_per_day(full)

    def test_restricted_dow_reduces_daily_estimate(self):
        # Only runs on Monday
        entry_mon = make_entry("weekly.sh", minute="0", hour="6", dow="1")
        entry_all = make_entry("weekly.sh", minute="0", hour="6", dow="*")
        assert _runs_per_day(entry_mon) < _runs_per_day(entry_all)


class TestComputeCommandFrequency:
    def test_empty_input_returns_empty_list(self):
        assert compute_command_frequency([]) == []

    def test_single_entry_returns_one_record(self):
        entry = make_entry("/usr/bin/backup", minute="0", hour="2")
        result = compute_command_frequency([entry])
        assert len(result) == 1
        assert result[0].command == "/usr/bin/backup"
        assert result[0].entry_count == 1

    def test_same_command_different_servers_merged(self):
        e1 = make_entry("sync.sh", server="web1")
        e2 = make_entry("sync.sh", server="web2")
        result = compute_command_frequency([e1, e2])
        assert len(result) == 1
        rec = result[0]
        assert rec.entry_count == 2
        assert set(rec.servers) == {"web1", "web2"}

    def test_different_commands_produce_separate_records(self):
        e1 = make_entry("alpha.sh")
        e2 = make_entry("beta.sh")
        result = compute_command_frequency([e1, e2])
        commands = {r.command for r in result}
        assert commands == {"alpha.sh", "beta.sh"}

    def test_results_sorted_descending_by_runs_per_day(self):
        # every minute vs once per day
        frequent = make_entry("frequent.sh", minute="*", hour="*")
        rare = make_entry("rare.sh", minute="0", hour="3")
        result = compute_command_frequency([rare, frequent])
        assert result[0].command == "frequent.sh"
        assert result[1].command == "rare.sh"

    def test_runs_per_day_accumulated_across_servers(self):
        e1 = make_entry("job.sh", minute="0", hour="*", server="s1")
        e2 = make_entry("job.sh", minute="0", hour="*", server="s2")
        result = compute_command_frequency([e1, e2])
        # two servers each running 24 times/day => 48
        assert result[0].runs_per_day == pytest.approx(48.0)

    def test_unknown_server_fallback(self):
        entry = make_entry("task.sh", server="")
        # set server to empty string to trigger fallback
        entry = CronEntry(
            schedule=entry.schedule, command=entry.command, server=None
        )
        result = compute_command_frequency([entry])
        assert "unknown" in result[0].servers
