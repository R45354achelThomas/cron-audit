"""Tests for cron_audit.differ."""

import pytest

from cron_audit.differ import DiffResult, diff_entries, diff_servers, _entry_key
from cron_audit.parser import CronEntry, CronSchedule


def make_entry(minute="0", hour="*", command="/bin/job", server="web1"):
    schedule = CronSchedule(
        minute=minute, hour=hour, day="*", month="*", weekday="*"
    )
    return CronEntry(schedule=schedule, command=command, server=server, raw="")


class TestDiffEntries:
    def test_all_unchanged_when_identical(self):
        entries = [make_entry(), make_entry(command="/bin/other")]
        result = diff_entries(entries, entries)
        assert len(result.unchanged) == 2
        assert not result.added
        assert not result.removed

    def test_added_entry_detected(self):
        before = [make_entry(command="/bin/a")]
        after = [make_entry(command="/bin/a"), make_entry(command="/bin/b")]
        result = diff_entries(before, after)
        assert len(result.added) == 1
        assert result.added[0].command == "/bin/b"
        assert not result.removed

    def test_removed_entry_detected(self):
        before = [make_entry(command="/bin/a"), make_entry(command="/bin/b")]
        after = [make_entry(command="/bin/a")]
        result = diff_entries(before, after)
        assert len(result.removed) == 1
        assert result.removed[0].command == "/bin/b"
        assert not result.added

    def test_changed_schedule_appears_as_remove_and_add(self):
        before = [make_entry(hour="1", command="/bin/x")]
        after = [make_entry(hour="2", command="/bin/x")]
        result = diff_entries(before, after)
        assert len(result.added) == 1
        assert len(result.removed) == 1

    def test_empty_before_all_added(self):
        after = [make_entry(), make_entry(command="/bin/b")]
        result = diff_entries([], after)
        assert len(result.added) == 2
        assert not result.removed
        assert not result.unchanged

    def test_empty_after_all_removed(self):
        before = [make_entry()]
        result = diff_entries(before, [])
        assert len(result.removed) == 1
        assert not result.added


class TestDiffResult:
    def test_has_changes_true_when_added(self):
        r = DiffResult(added=[make_entry()])
        assert r.has_changes

    def test_has_changes_false_when_only_unchanged(self):
        r = DiffResult(unchanged=[make_entry()])
        assert not r.has_changes

    def test_summary_no_changes(self):
        r = DiffResult(unchanged=[make_entry()])
        assert r.summary() == "no changes"

    def test_summary_with_changes(self):
        r = DiffResult(added=[make_entry()], removed=[make_entry(), make_entry()])
        assert "+1 added" in r.summary()
        assert "-2 removed" in r.summary()


class TestDiffServers:
    def test_diff_between_two_servers(self):
        entries = [
            make_entry(command="/bin/shared", server="a"),
            make_entry(command="/bin/shared", server="b"),
            make_entry(command="/bin/only_a", server="a"),
            make_entry(command="/bin/only_b", server="b"),
        ]
        result = diff_servers(entries, server_a="a", server_b="b")
        assert len(result.unchanged) == 1
        assert len(result.added) == 1
        assert result.added[0].command == "/bin/only_b"
        assert len(result.removed) == 1
        assert result.removed[0].command == "/bin/only_a"
