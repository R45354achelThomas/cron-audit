"""Tests for cron_audit.tag_report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.tag_report import TagGroup, TagReport, build_tag_report, format_tag_report


def make_entry(
    command: str = "/usr/bin/backup",
    server: str = "web-01",
    tags: List[str] | None = None,
) -> CronEntry:
    sched = CronSchedule(minute="0", hour="2", dom="*", month="*", dow="*")
    entry = CronEntry(schedule=sched, command=command, server=server)
    entry.tags = tags or []
    return entry


class TestBuildTagReport:
    def test_empty_entries_returns_empty_report(self):
        report = build_tag_report([])
        assert report.groups == {}
        assert report.untagged == []

    def test_untagged_entry_goes_to_untagged(self):
        entry = make_entry(tags=[])
        report = build_tag_report([entry])
        assert len(report.untagged) == 1
        assert report.total_tagged == 0

    def test_tagged_entry_appears_in_correct_group(self):
        entry = make_entry(tags=["backup"])
        report = build_tag_report([entry])
        assert "backup" in report.groups
        assert report.groups["backup"].entries == [entry]

    def test_entry_with_multiple_tags_appears_in_each_group(self):
        entry = make_entry(tags=["backup", "nightly"])
        report = build_tag_report([entry])
        assert "backup" in report.groups
        assert "nightly" in report.groups
        assert report.groups["backup"].entries[0] is entry
        assert report.groups["nightly"].entries[0] is entry

    def test_total_untagged_count(self):
        entries = [make_entry(tags=[]) for _ in range(3)]
        report = build_tag_report(entries)
        assert report.total_untagged == 3

    def test_groups_are_sorted_alphabetically(self):
        entries = [
            make_entry(tags=["zebra"]),
            make_entry(tags=["alpha"]),
            make_entry(tags=["mango"]),
        ]
        report = build_tag_report(entries)
        assert list(report.groups.keys()) == ["alpha", "mango", "zebra"]

    def test_server_names_on_tag_group(self):
        e1 = make_entry(server="srv-1", tags=["db"])
        e2 = make_entry(server="srv-2", tags=["db"])
        report = build_tag_report([e1, e2])
        assert report.groups["db"].server_names == ["srv-1", "srv-2"]


class TestFormatTagReport:
    def test_no_entries_message(self):
        report = TagReport()
        text = format_tag_report(report)
        assert "No entries found" in text

    def test_tag_section_header_present(self):
        entry = make_entry(tags=["backup"])
        report = build_tag_report([entry])
        text = format_tag_report(report)
        assert "[backup]" in text

    def test_command_appears_in_output(self):
        entry = make_entry(command="/opt/scripts/run.sh", tags=["ops"])
        report = build_tag_report([entry])
        text = format_tag_report(report)
        assert "/opt/scripts/run.sh" in text

    def test_untagged_section_present_when_applicable(self):
        entry = make_entry(tags=[])
        report = build_tag_report([entry])
        text = format_tag_report(report)
        assert "[untagged]" in text

    def test_summary_line_present(self):
        entry = make_entry(tags=["cron"])
        report = build_tag_report([entry])
        text = format_tag_report(report)
        assert "Summary:" in text
