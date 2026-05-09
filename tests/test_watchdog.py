"""Tests for cron_audit.watchdog."""

from datetime import datetime, timezone

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.watchdog import StaleEntry, check_staleness


def make_entry(
    command: str = "/usr/bin/backup",
    server: str = "web01",
    minute: str = "0",
    hour: str = "2",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
) -> CronEntry:
    schedule = CronSchedule(minute=minute, hour=hour, dom=dom, month=month, dow=dow)
    return CronEntry(schedule=schedule, command=command, server=server, raw="")


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


class TestCheckStaleness:
    def test_never_run_entry_is_stale(self):
        entry = make_entry(minute="0", hour="2")
        ref = _utc(2024, 6, 1, 4, 0, 0)  # well past any expected run
        result = check_staleness([entry], last_run_map={}, reference_time=ref)
        assert len(result) == 1
        assert result[0].last_run is None
        assert result[0].overdue_seconds > 0

    def test_recently_run_entry_not_stale(self):
        entry = make_entry(minute="0", hour="2")
        # Last run at 02:00, next expected 02:00 next day; ref is 03:00 same day
        last_run = _utc(2024, 6, 1, 2, 0, 0)
        ref = _utc(2024, 6, 1, 3, 0, 0)
        result = check_staleness(
            [entry],
            last_run_map={("web01", "/usr/bin/backup"): last_run},
            reference_time=ref,
        )
        assert result == []

    def test_overdue_entry_detected(self):
        entry = make_entry(minute="0", hour="2")
        last_run = _utc(2024, 6, 1, 2, 0, 0)
        # Reference is more than 24 h after last run -> next expected run has passed
        ref = _utc(2024, 6, 2, 5, 0, 0)
        result = check_staleness(
            [entry],
            last_run_map={("web01", "/usr/bin/backup"): last_run},
            reference_time=ref,
        )
        assert len(result) == 1
        assert result[0].entry is entry
        assert result[0].overdue_seconds > 0

    def test_grace_period_suppresses_flag(self):
        entry = make_entry(minute="0", hour="2")
        last_run = _utc(2024, 6, 1, 2, 0, 0)
        # Next expected: 2024-06-02 02:00; ref is 2 minutes past that
        ref = _utc(2024, 6, 2, 2, 2, 0)
        # With 5-minute grace, should NOT be stale
        result = check_staleness(
            [entry],
            last_run_map={("web01", "/usr/bin/backup"): last_run},
            reference_time=ref,
            grace_seconds=300,
        )
        assert result == []

    def test_multiple_entries_partial_stale(self):
        e1 = make_entry(command="/bin/job1", hour="1")
        e2 = make_entry(command="/bin/job2", hour="3", server="db01")
        last_run_e1 = _utc(2024, 6, 1, 1, 0, 0)
        ref = _utc(2024, 6, 2, 4, 0, 0)
        result = check_staleness(
            [e1, e2],
            last_run_map={("web01", "/bin/job1"): last_run_e1},
            reference_time=ref,
        )
        commands = {r.entry.command for r in result}
        # e2 never ran -> stale; e1 next run 2024-06-02 01:00 which has passed -> stale
        assert "/bin/job2" in commands

    def test_stale_entry_repr_does_not_raise(self):
        entry = make_entry()
        se = StaleEntry(
            entry=entry,
            last_run=None,
            expected_next=_utc(2024, 1, 1, 2, 0),
            overdue_seconds=3600.0,
        )
        assert "web01" in repr(se)

    def test_default_reference_time_used(self):
        """Passing no reference_time should not raise."""
        entry = make_entry()
        # Should complete without error; result may vary by wall clock
        result = check_staleness([entry], last_run_map={})
        assert isinstance(result, list)
