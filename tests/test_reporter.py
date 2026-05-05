"""Tests for cron_audit.reporter.generate_report."""

import pytest
from unittest.mock import MagicMock
from cron_audit.reporter import generate_report, _group_entries_by_server


def make_entry(server="web-01", command="/usr/bin/backup", schedule="0 2 * * *"):
    entry = MagicMock()
    entry.server = server
    entry.command = command
    entry.__str__ = lambda self: f"{schedule} {command}"
    return entry


def make_conflict(description="duplicate command"):
    conflict = MagicMock()
    conflict.__str__ = lambda self: description
    return conflict


class TestGroupEntriesByServer:
    def test_groups_correctly(self):
        entries = [
            make_entry(server="web-01"),
            make_entry(server="web-02"),
            make_entry(server="web-01"),
        ]
        result = _group_entries_by_server(entries)
        assert set(result.keys()) == {"web-01", "web-02"}
        assert len(result["web-01"]) == 2
        assert len(result["web-02"]) == 1

    def test_unknown_server_fallback(self):
        entry = MagicMock(spec=["command"])
        entry.command = "/bin/true"
        entry.__str__ = lambda self: "* * * * * /bin/true"
        result = _group_entries_by_server([entry])
        assert "unknown" in result


class TestGenerateReport:
    def test_report_contains_title(self):
        report = generate_report([], [], title="My Audit")
        assert "My Audit" in report

    def test_report_shows_entry_count(self):
        entries = [make_entry(), make_entry()]
        report = generate_report(entries, [])
        assert "Total entries : 2" in report

    def test_report_shows_conflict_count(self):
        conflicts = [make_conflict(), make_conflict()]
        report = generate_report([], conflicts)
        assert "Total conflicts: 2" in report

    def test_no_conflicts_message(self):
        report = generate_report([], [])
        assert "No conflicts detected." in report

    def test_conflict_listed_in_report(self):
        conflicts = [make_conflict("overlapping schedule on /usr/bin/backup")]
        report = generate_report([], conflicts)
        assert "overlapping schedule on /usr/bin/backup" in report

    def test_server_section_present(self):
        entries = [make_entry(server="db-01")]
        report = generate_report(entries, [])
        assert "[db-01]" in report

    def test_entry_command_in_report(self):
        entries = [make_entry(command="/usr/bin/cleanup")]
        report = generate_report(entries, [])
        assert "/usr/bin/cleanup" in report

    def test_report_is_string(self):
        report = generate_report([], [])
        assert isinstance(report, str)
