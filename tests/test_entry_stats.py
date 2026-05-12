"""Tests for cron_audit.entry_stats."""
from datetime import datetime, timezone
from typing import List

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.entry_stats import EntryStats, _entry_key, compute_stats


def make_entry(
    command: str = "/usr/bin/backup",
    server: str = "web01",
    minute: str = "0",
    hour: str = "3",
) -> CronEntry:
    schedule = CronSchedule(
        minute=minute, hour=hour, dom="*", month="*", dow="*"
    )
    return CronEntry(schedule=schedule, command=command, server=server, raw="")


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class TestEntryKey:
    def test_key_includes_server_and_command(self):
        entry = make_entry(command="/bin/foo", server="host1")
        assert _entry_key(entry) == "host1::/bin/foo"

    def test_different_servers_produce_different_keys(self):
        e1 = make_entry(server="host1")
        e2 = make_entry(server="host2")
        assert _entry_key(e1) != _entry_key(e2)


class TestComputeStats:
    def test_returns_one_stat_per_entry(self):
        entries = [make_entry(), make_entry(command="/bin/other")]
        result = compute_stats(entries, {}, reference=_utc(2024, 6, 1))
        assert len(result) == 2

    def test_run_count_zero_when_no_history(self):
        entry = make_entry()
        (stat,) = compute_stats([entry], {}, reference=_utc(2024, 6, 1))
        assert stat.run_count == 0
        assert stat.last_run is None

    def test_run_count_matches_history_length(self):
        entry = make_entry()
        runs = [_utc(2024, 5, 30), _utc(2024, 5, 31), _utc(2024, 6, 1)]
        key = _entry_key(entry)
        (stat,) = compute_stats([entry], {key: runs}, reference=_utc(2024, 6, 2))
        assert stat.run_count == 3

    def test_last_run_is_most_recent(self):
        entry = make_entry()
        runs = [_utc(2024, 5, 28), _utc(2024, 5, 31)]
        key = _entry_key(entry)
        (stat,) = compute_stats([entry], {key: runs}, reference=_utc(2024, 6, 1))
        assert stat.last_run == _utc(2024, 5, 31)

    def test_avg_gap_none_with_single_run(self):
        entry = make_entry()
        key = _entry_key(entry)
        (stat,) = compute_stats(
            [entry], {key: [_utc(2024, 6, 1)]}, reference=_utc(2024, 6, 2)
        )
        assert stat.avg_gap_seconds is None

    def test_avg_gap_computed_correctly(self):
        entry = make_entry()
        runs = [
            _utc(2024, 6, 1, 3, 0),
            _utc(2024, 6, 2, 3, 0),
            _utc(2024, 6, 3, 3, 0),
        ]
        key = _entry_key(entry)
        (stat,) = compute_stats([entry], {key: runs}, reference=_utc(2024, 6, 4))
        assert stat.avg_gap_seconds == pytest.approx(86400.0)

    def test_next_run_is_datetime(self):
        entry = make_entry(hour="4", minute="30")
        (stat,) = compute_stats([entry], {}, reference=_utc(2024, 6, 1, 0, 0))
        assert isinstance(stat.next_run, datetime)

    def test_server_field_populated(self):
        entry = make_entry(server="db01")
        (stat,) = compute_stats([entry], {}, reference=_utc(2024, 6, 1))
        assert stat.server == "db01"
