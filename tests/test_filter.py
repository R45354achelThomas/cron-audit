"""Tests for cron_audit.filter."""

from __future__ import annotations

import pytest

from cron_audit.filter import FilterCriteria, filter_entries
from cron_audit.parser import CronEntry, CronSchedule


def make_entry(
    command: str = "echo hi",
    server: str = "web1",
    minute: str = "0",
    hour: str = "*",
    tags: list | None = None,
) -> CronEntry:
    schedule = CronSchedule(minute=minute, hour=hour, dom="*", month="*", dow="*")
    entry = CronEntry(server=server, schedule=schedule, command=command, raw="")
    entry.tags = tags or []
    return entry


class TestFilterCriteria:
    def test_is_empty_by_default(self):
        assert FilterCriteria().is_empty()

    def test_not_empty_with_server(self):
        assert not FilterCriteria(servers=["web1"]).is_empty()

    def test_not_empty_with_command_pattern(self):
        assert not FilterCriteria(command_pattern="backup").is_empty()


class TestFilterEntries:
    def test_empty_criteria_returns_all(self):
        entries = [make_entry(), make_entry(command="ls")]
        result = filter_entries(entries, FilterCriteria())
        assert result == entries

    def test_filter_by_server(self):
        e1 = make_entry(server="web1")
        e2 = make_entry(server="db1")
        result = filter_entries([e1, e2], FilterCriteria(servers=["web1"]))
        assert result == [e1]

    def test_filter_by_multiple_servers(self):
        e1 = make_entry(server="web1")
        e2 = make_entry(server="db1")
        e3 = make_entry(server="cache1")
        result = filter_entries([e1, e2, e3], FilterCriteria(servers=["web1", "db1"]))
        assert e3 not in result
        assert len(result) == 2

    def test_filter_by_tag_match(self):
        e1 = make_entry(tags=["backup", "nightly"])
        e2 = make_entry(tags=["cleanup"])
        result = filter_entries([e1, e2], FilterCriteria(tags=["backup"]))
        assert result == [e1]

    def test_filter_by_tag_no_match(self):
        e1 = make_entry(tags=["cleanup"])
        result = filter_entries([e1], FilterCriteria(tags=["backup"]))
        assert result == []

    def test_filter_by_command_pattern(self):
        e1 = make_entry(command="/usr/bin/backup.sh")
        e2 = make_entry(command="/usr/bin/cleanup.sh")
        result = filter_entries([e1, e2], FilterCriteria(command_pattern="backup"))
        assert result == [e1]

    def test_filter_by_invalid_regex_falls_back_to_equality(self):
        e1 = make_entry(command="[invalid")
        result = filter_entries([e1], FilterCriteria(command_pattern="[invalid"))
        assert result == [e1]

    def test_filter_by_hour(self):
        e1 = make_entry(hour="3")
        e2 = make_entry(hour="12")
        result = filter_entries([e1, e2], FilterCriteria(hour="3"))
        assert result == [e1]

    def test_filter_by_minute(self):
        e1 = make_entry(minute="30")
        e2 = make_entry(minute="0")
        result = filter_entries([e1, e2], FilterCriteria(minute="30"))
        assert result == [e1]

    def test_combined_criteria_all_must_match(self):
        e1 = make_entry(server="web1", command="backup", hour="2")
        e2 = make_entry(server="web1", command="backup", hour="5")
        criteria = FilterCriteria(servers=["web1"], command_pattern="backup", hour="2")
        result = filter_entries([e1, e2], criteria)
        assert result == [e1]

    def test_returns_empty_list_for_no_matches(self):
        entries = [make_entry(server="db1")]
        result = filter_entries(entries, FilterCriteria(servers=["web1"]))
        assert result == []
