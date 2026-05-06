"""Tests for cron_audit.formatter."""

import pytest
from unittest.mock import MagicMock
from cron_audit.formatter import (
    format_entry,
    format_conflict,
    format_server_section,
    format_conflicts_section,
    format_summary,
)


def make_entry(command="/usr/bin/backup", server="web-01", schedule_str="0 2 * * *"):
    entry = MagicMock()
    entry.command = command
    entry.server = server
    entry.schedule = MagicMock()
    entry.schedule.__str__ = MagicMock(return_value=schedule_str)
    return entry


def make_conflict(reason="Duplicate command", server_a="web-01", server_b="web-02"):
    conflict = MagicMock()
    conflict.reason = reason
    conflict.entry_a = make_entry(server=server_a)
    conflict.entry_b = make_entry(server=server_b)
    return conflict


class TestFormatEntry:
    def test_contains_command(self):
        entry = make_entry(command="/usr/bin/backup")
        result = format_entry(entry)
        assert "/usr/bin/backup" in result

    def test_contains_schedule(self):
        entry = make_entry(schedule_str="0 2 * * *")
        result = format_entry(entry)
        assert "0 2 * * *" in result

    def test_default_indent(self):
        entry = make_entry()
        result = format_entry(entry)
        assert result.startswith("  ")

    def test_custom_indent(self):
        entry = make_entry()
        result = format_entry(entry, indent=4)
        assert result.startswith("    ")


class TestFormatConflict:
    def test_contains_reason(self):
        conflict = make_conflict(reason="Duplicate command detected")
        result = format_conflict(conflict)
        assert "Duplicate command detected" in result

    def test_contains_both_servers(self):
        conflict = make_conflict(server_a="alpha", server_b="beta")
        result = format_conflict(conflict)
        assert "alpha" in result
        assert "beta" in result

    def test_duplicate_icon(self):
        conflict = make_conflict(reason="Duplicate command")
        result = format_conflict(conflict)
        assert "[!!]" in result

    def test_overlap_icon(self):
        conflict = make_conflict(reason="Schedule overlap")
        result = format_conflict(conflict)
        assert "[! ]" in result


class TestFormatServerSection:
    def test_server_name_in_output(self):
        entries = [make_entry()]
        result = format_server_section("db-01", entries)
        assert "db-01" in result

    def test_entry_count_in_output(self):
        entries = [make_entry(), make_entry()]
        result = format_server_section("db-01", entries)
        assert "2 job(s)" in result


class TestFormatConflictsSection:
    def test_no_conflicts_message(self):
        result = format_conflicts_section([])
        assert "No conflicts" in result

    def test_conflict_count_shown(self):
        conflicts = [make_conflict(), make_conflict()]
        result = format_conflicts_section(conflicts)
        assert "2" in result


class TestFormatSummary:
    def test_summary_contains_counts(self):
        result = format_summary(10, 3, 2)
        assert "10" in result
        assert "3" in result
        assert "2" in result
