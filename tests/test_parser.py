"""Unit tests for cron_audit.parser."""

import pytest
from cron_audit.parser import CronEntry, parse_crontab


SAMPLE_CRONTAB = """
# Daily backup at midnight
0 0 * * * /usr/local/bin/backup.sh

# Hourly health-check
*/15 * * * * /opt/scripts/healthcheck.py --quiet

# First day of every month
30 6 1 * * /usr/bin/monthly_report.sh

# This line should be ignored (malformed)
not_a_valid_cron_line
"""


class TestParseCrontab:
    def test_returns_list_of_cron_entries(self):
        entries = parse_crontab(SAMPLE_CRONTAB)
        assert isinstance(entries, list)
        assert all(isinstance(e, CronEntry) for e in entries)

    def test_correct_number_of_entries_parsed(self):
        entries = parse_crontab(SAMPLE_CRONTAB)
        assert len(entries) == 3

    def test_first_entry_fields(self):
        entry = parse_crontab(SAMPLE_CRONTAB)[0]
        assert entry.minute == "0"
        assert entry.hour == "0"
        assert entry.dom == "*"
        assert entry.month == "*"
        assert entry.dow == "*"
        assert entry.command == "/usr/local/bin/backup.sh"

    def test_step_expression_parsed(self):
        entry = parse_crontab(SAMPLE_CRONTAB)[1]
        assert entry.minute == "*/15"
        assert "/opt/scripts/healthcheck.py" in entry.command

    def test_source_label_attached(self):
        entries = parse_crontab(SAMPLE_CRONTAB, source="web-01")
        assert all(e.source == "web-01" for e in entries)

    def test_line_numbers_recorded(self):
        entries = parse_crontab(SAMPLE_CRONTAB)
        # Line numbers must be positive integers
        assert all(isinstance(e.line_number, int) and e.line_number > 0 for e in entries)

    def test_blank_and_comment_lines_ignored(self):
        crontab = "# comment\n\n5 4 * * 1 /bin/true\n"
        entries = parse_crontab(crontab)
        assert len(entries) == 1

    def test_empty_input_returns_empty_list(self):
        assert parse_crontab("") == []

    def test_schedule_property(self):
        entry = parse_crontab("30 6 1 * * /bin/report")[0]
        assert entry.schedule == "30 6 1 * *"

    def test_malformed_lines_skipped(self):
        entries = parse_crontab("not_valid\n0 0 * * * /bin/ok")
        assert len(entries) == 1
        assert entries[0].command == "/bin/ok"
