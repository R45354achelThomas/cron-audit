"""Tests for cron_audit.overlap_reporter."""
from __future__ import annotations

import pytest

from cron_audit.conflict_detector import Conflict
from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.overlap_reporter import (
    OverlapReport,
    build_overlap_report,
    format_overlap_report,
)


def make_entry(command: str = "/usr/bin/job", server: str = "web1") -> CronEntry:
    schedule = CronSchedule(minute="0", hour="*", dom="*", month="*", dow="*")
    return CronEntry(schedule=schedule, command=command, server=server, raw="")


def make_conflict(reason: str = "schedule overlap") -> Conflict:
    return Conflict(
        entry_a=make_entry("/bin/a", "web1"),
        entry_b=make_entry("/bin/b", "web2"),
        reason=reason,
    )


class TestBuildOverlapReport:
    def test_empty_input_returns_empty_report(self):
        report = build_overlap_report([])
        assert report.total == 0
        assert report.high == []
        assert report.medium == []
        assert report.low == []

    def test_duplicate_classified_as_high(self):
        c = make_conflict("duplicate command detected")
        report = build_overlap_report([c])
        assert len(report.high) == 1
        assert report.medium == []
        assert report.low == []

    def test_overlap_classified_as_medium(self):
        c = make_conflict("schedule overlap between entries")
        report = build_overlap_report([c])
        assert len(report.medium) == 1
        assert report.high == []

    def test_unknown_reason_classified_as_low(self):
        c = make_conflict("suspicious timing")
        report = build_overlap_report([c])
        assert len(report.low) == 1

    def test_total_counts_all_severities(self):
        conflicts = [
            make_conflict("identical schedules"),
            make_conflict("overlap detected"),
            make_conflict("minor issue"),
        ]
        report = build_overlap_report(conflicts)
        assert report.total == 3

    def test_by_server_groups_correctly(self):
        c1 = Conflict(
            entry_a=make_entry("/bin/a", "web1"),
            entry_b=make_entry("/bin/b", "web1"),
            reason="overlap",
        )
        c2 = Conflict(
            entry_a=make_entry("/bin/c", "db1"),
            entry_b=make_entry("/bin/d", "db1"),
            reason="overlap",
        )
        report = build_overlap_report([c1, c2])
        by_server = report.by_server()
        assert "web1" in by_server
        assert "db1" in by_server
        assert len(by_server["web1"]) == 1


class TestFormatOverlapReport:
    def test_no_conflicts_message(self):
        report = OverlapReport()
        output = format_overlap_report(report)
        assert "No overlapping" in output

    def test_contains_high_section(self):
        c = make_conflict("duplicate")
        report = build_overlap_report([c])
        output = format_overlap_report(report)
        assert "[HIGH]" in output

    def test_contains_medium_section(self):
        c = make_conflict("overlap")
        report = build_overlap_report([c])
        output = format_overlap_report(report)
        assert "[MEDIUM]" in output

    def test_total_shown_in_header(self):
        conflicts = [make_conflict("overlap"), make_conflict("overlap")]
        report = build_overlap_report(conflicts)
        output = format_overlap_report(report)
        assert "2 conflict" in output

    def test_low_section_absent_when_empty(self):
        c = make_conflict("duplicate")
        report = build_overlap_report([c])
        output = format_overlap_report(report)
        assert "[LOW]" not in output
