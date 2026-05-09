"""Tests for cron_audit.deduplicator."""

from __future__ import annotations

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.deduplicator import (
    DuplicateGroup,
    find_duplicates,
    deduplicate,
    _entry_key,
)


def make_entry(
    command: str = "/usr/bin/backup",
    minute: str = "0",
    hour: str = "2",
    server: str = "web01",
) -> CronEntry:
    schedule = CronSchedule(
        minute=minute,
        hour=hour,
        day_of_month="*",
        month="*",
        day_of_week="*",
    )
    return CronEntry(schedule=schedule, command=command, server=server)


class TestEntryKey:
    def test_same_schedule_and_command_produce_same_key(self):
        e1 = make_entry(command="/bin/foo", hour="3")
        e2 = make_entry(command="/bin/foo", hour="3", server="web02")
        assert _entry_key(e1) == _entry_key(e2)

    def test_different_command_produces_different_key(self):
        e1 = make_entry(command="/bin/foo")
        e2 = make_entry(command="/bin/bar")
        assert _entry_key(e1) != _entry_key(e2)

    def test_different_hour_produces_different_key(self):
        e1 = make_entry(hour="1")
        e2 = make_entry(hour="2")
        assert _entry_key(e1) != _entry_key(e2)

    def test_command_whitespace_is_stripped(self):
        e1 = make_entry(command="/bin/foo")
        e2 = make_entry(command="  /bin/foo  ")
        assert _entry_key(e1) == _entry_key(e2)


class TestFindDuplicates:
    def test_no_duplicates_returns_empty(self):
        entries = [make_entry(hour=str(h)) for h in range(3)]
        assert find_duplicates(entries) == []

    def test_two_identical_entries_form_one_group(self):
        e1 = make_entry(server="web01")
        e2 = make_entry(server="web02")
        groups = find_duplicates([e1, e2])
        assert len(groups) == 1
        assert len(groups[0].entries) == 2

    def test_group_is_cross_server_when_servers_differ(self):
        e1 = make_entry(server="web01")
        e2 = make_entry(server="web02")
        groups = find_duplicates([e1, e2])
        assert groups[0].is_cross_server is True

    def test_group_not_cross_server_when_same_server(self):
        e1 = make_entry(server="web01")
        e2 = make_entry(server="web01")
        groups = find_duplicates([e1, e2])
        assert groups[0].is_cross_server is False

    def test_three_duplicates_in_one_group(self):
        entries = [make_entry(server=f"s{i}") for i in range(3)]
        groups = find_duplicates(entries)
        assert len(groups) == 1
        assert len(groups[0].entries) == 3


class TestDeduplicate:
    def test_no_duplicates_returns_all_entries(self):
        entries = [make_entry(hour=str(h)) for h in range(4)]
        kept, groups = deduplicate(entries)
        assert len(kept) == 4
        assert groups == []

    def test_duplicates_collapsed_to_first_occurrence(self):
        e1 = make_entry(server="web01")
        e2 = make_entry(server="web02")
        kept, groups = deduplicate([e1, e2])
        assert len(kept) == 1
        assert kept[0] is e1

    def test_returns_correct_number_of_groups(self):
        e1 = make_entry(command="/bin/a", server="s1")
        e2 = make_entry(command="/bin/a", server="s2")
        e3 = make_entry(command="/bin/b", server="s1")
        e4 = make_entry(command="/bin/b", server="s2")
        kept, groups = deduplicate([e1, e2, e3, e4])
        assert len(kept) == 2
        assert len(groups) == 2

    def test_unique_entries_are_all_kept(self):
        entries = [make_entry(command=f"/bin/cmd{i}") for i in range(5)]
        kept, groups = deduplicate(entries)
        assert len(kept) == 5
        assert len(groups) == 0
