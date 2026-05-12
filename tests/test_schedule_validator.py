"""Tests for cron_audit.schedule_validator."""
from __future__ import annotations

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.schedule_validator import (
    ValidationIssue,
    ValidationReport,
    validate_entries,
    _check_field,
)


def make_entry(
    minute="0",
    hour="2",
    dom="*",
    month="*",
    dow="*",
    command="/usr/bin/backup",
    server="host1",
) -> CronEntry:
    sched = CronSchedule(minute=minute, hour=hour, dom=dom, month=month, dow=dow)
    return CronEntry(schedule=sched, command=command, server=server)


# --- _check_field unit tests ---

class TestCheckField:
    def test_wildcard_returns_no_issues(self):
        assert _check_field("*", "minute", 0, 59) == []

    def test_valid_single_value(self):
        assert _check_field("30", "minute", 0, 59) == []

    def test_out_of_range_value(self):
        issues = _check_field("60", "minute", 0, 59)
        assert any("out of range" in i for i in issues)

    def test_valid_range(self):
        assert _check_field("1-5", "hour", 0, 23) == []

    def test_inverted_range_flagged(self):
        issues = _check_field("10-5", "hour", 0, 23)
        assert any("start" in i and ">" in i for i in issues)

    def test_valid_step(self):
        assert _check_field("*/5", "minute", 0, 59) == []

    def test_invalid_step_zero(self):
        issues = _check_field("*/0", "minute", 0, 59)
        assert any("step" in i for i in issues)

    def test_non_numeric_value(self):
        issues = _check_field("abc", "hour", 0, 23)
        assert any("non-numeric" in i for i in issues)

    def test_comma_list_mixed(self):
        issues = _check_field("1,2,99", "hour", 0, 23)
        assert any("out of range" in i for i in issues)

    def test_comma_list_all_valid(self):
        assert _check_field("1,2,3", "hour", 0, 23) == []


# --- validate_entries integration tests ---

class TestValidateEntries:
    def test_valid_entry_no_issues(self):
        entry = make_entry(minute="0", hour="6", dom="*", month="*", dow="1")
        report = validate_entries([entry])
        assert not report.has_issues()

    def test_out_of_range_hour_detected(self):
        entry = make_entry(hour="25")
        report = validate_entries([entry])
        assert report.has_issues()
        assert any(i.field == "hour" for i in report.issues)

    def test_invalid_month_detected(self):
        entry = make_entry(month="13")
        report = validate_entries([entry])
        assert any(i.field == "month" for i in report.issues)

    def test_error_severity_for_out_of_range(self):
        entry = make_entry(minute="99")
        report = validate_entries([entry])
        assert any(i.severity == "error" for i in report.issues)

    def test_multiple_entries_aggregated(self):
        e1 = make_entry(hour="25")
        e2 = make_entry(minute="61")
        report = validate_entries([e1, e2])
        assert len(report.errors) >= 2

    def test_empty_entries_returns_empty_report(self):
        report = validate_entries([])
        assert not report.has_issues()

    def test_report_repr(self):
        report = ValidationReport()
        assert "errors=0" in repr(report)

    def test_issue_repr(self):
        entry = make_entry()
        issue = ValidationIssue(entry=entry, field="hour", message="test", severity="warning")
        assert "warning" in repr(issue)
        assert "hour" in repr(issue)
