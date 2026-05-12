"""Tests for cron_audit.run_window."""
import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.run_window import check_run_window, RunWindowReport, WindowViolation


def make_entry(
    minute="0",
    hour="2",
    dom="*",
    month="*",
    dow="*",
    command="/usr/bin/backup.sh",
    server="web01",
) -> CronEntry:
    schedule = CronSchedule(minute=minute, hour=hour, day_of_month=dom, month=month, day_of_week=dow)
    return CronEntry(schedule=schedule, command=command, server=server)


class TestCheckRunWindow:
    def test_empty_entries_returns_empty_report(self):
        report = check_run_window([], allowed_start_hour=8, allowed_end_hour=18)
        assert isinstance(report, RunWindowReport)
        assert report.checked == 0
        assert not report.has_violations

    def test_entry_within_window_no_violation(self):
        entry = make_entry(hour="10")
        report = check_run_window([entry], allowed_start_hour=8, allowed_end_hour=18)
        assert not report.has_violations
        assert report.checked == 1

    def test_entry_outside_window_creates_violation(self):
        entry = make_entry(hour="3")
        report = check_run_window([entry], allowed_start_hour=8, allowed_end_hour=18)
        assert report.has_violations
        assert len(report.violations) == 1
        assert isinstance(report.violations[0], WindowViolation)

    def test_violation_reason_contains_hour(self):
        entry = make_entry(hour="3")
        report = check_run_window([entry], allowed_start_hour=8, allowed_end_hour=18)
        assert "3" in report.violations[0].reason

    def test_wildcard_hour_triggers_violation(self):
        entry = make_entry(hour="*")
        report = check_run_window([entry], allowed_start_hour=10, allowed_end_hour=12)
        assert report.has_violations

    def test_boundary_hours_are_inclusive(self):
        entry_start = make_entry(hour="8")
        entry_end = make_entry(hour="18")
        report = check_run_window([entry_start, entry_end], allowed_start_hour=8, allowed_end_hour=18)
        assert not report.has_violations

    def test_multiple_entries_mixed_violations(self):
        ok = make_entry(hour="9", command="/ok.sh")
        bad = make_entry(hour="1", command="/bad.sh")
        report = check_run_window([ok, bad], allowed_start_hour=8, allowed_end_hour=20)
        assert report.checked == 2
        assert len(report.violations) == 1
        assert report.violations[0].entry.command == "/bad.sh"

    def test_day_restriction_violation(self):
        entry = make_entry(hour="10", dow="6")  # Sunday
        report = check_run_window([entry], allowed_start_hour=8, allowed_end_hour=18, allowed_days=[0, 1, 2, 3, 4])
        assert report.has_violations
        assert "weekday" in report.violations[0].reason

    def test_day_restriction_no_violation(self):
        entry = make_entry(hour="10", dow="1")  # Monday
        report = check_run_window([entry], allowed_start_hour=8, allowed_end_hour=18, allowed_days=[0, 1, 2, 3, 4])
        assert not report.has_violations

    def test_none_allowed_days_skips_day_check(self):
        entry = make_entry(hour="10", dow="6")
        report = check_run_window([entry], allowed_start_hour=8, allowed_end_hour=18, allowed_days=None)
        assert not report.has_violations

    def test_invalid_start_hour_raises(self):
        with pytest.raises(ValueError, match="allowed_start_hour"):
            check_run_window([], allowed_start_hour=25, allowed_end_hour=18)

    def test_invalid_end_hour_raises(self):
        with pytest.raises(ValueError, match="allowed_end_hour"):
            check_run_window([], allowed_start_hour=8, allowed_end_hour=-1)

    def test_repr_includes_counts(self):
        report = check_run_window([], allowed_start_hour=8, allowed_end_hour=18)
        assert "checked=0" in repr(report)
        assert "violations=0" in repr(report)

    def test_violation_repr_includes_server_and_command(self):
        entry = make_entry(hour="3", server="db01", command="/cleanup.sh")
        report = check_run_window([entry], allowed_start_hour=8, allowed_end_hour=18)
        r = repr(report.violations[0])
        assert "db01" in r
        assert "/cleanup.sh" in r
