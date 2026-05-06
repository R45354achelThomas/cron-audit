"""Tests for cron_audit.formatter_diff."""

import pytest

from cron_audit.differ import DiffResult
from cron_audit.formatter_diff import format_diff
from cron_audit.parser import CronEntry, CronSchedule


def make_entry(command="/bin/job", server="web1"):
    schedule = CronSchedule(minute="0", hour="*", day="*", month="*", weekday="*")
    return CronEntry(schedule=schedule, command=command, server=server, raw="")


class TestFormatDiff:
    def test_contains_summary_line(self):
        result = DiffResult(added=[make_entry()])
        output = format_diff(result)
        assert "Summary:" in output

    def test_no_changes_summary(self):
        result = DiffResult(unchanged=[make_entry()])
        output = format_diff(result)
        assert "no changes" in output

    def test_added_section_present(self):
        result = DiffResult(added=[make_entry(command="/bin/new")])
        output = format_diff(result)
        assert "Added" in output
        assert "/bin/new" in output

    def test_removed_section_present(self):
        result = DiffResult(removed=[make_entry(command="/bin/old")])
        output = format_diff(result)
        assert "Removed" in output
        assert "/bin/old" in output

    def test_unchanged_section_present(self):
        result = DiffResult(unchanged=[make_entry(command="/bin/same")])
        output = format_diff(result)
        assert "Unchanged" in output
        assert "/bin/same" in output

    def test_custom_labels_in_header(self):
        result = DiffResult()
        output = format_diff(result, label_before="prod", label_after="staging")
        assert "prod" in output
        assert "staging" in output

    def test_no_color_by_default_no_escape_codes(self):
        result = DiffResult(added=[make_entry()], removed=[make_entry()])
        output = format_diff(result, color=False)
        assert "\033[" not in output

    def test_color_mode_includes_escape_codes(self):
        result = DiffResult(added=[make_entry()], removed=[make_entry()])
        output = format_diff(result, color=True)
        assert "\033[" in output

    def test_output_ends_with_newline(self):
        result = DiffResult()
        output = format_diff(result)
        assert output.endswith("\n")
