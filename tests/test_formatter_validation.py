"""Tests for cron_audit.formatter_validation."""
from __future__ import annotations

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.schedule_validator import ValidationIssue, ValidationReport
from cron_audit.formatter_validation import format_validation_report, _format_issue


def make_entry(command: str = "/usr/bin/job", server: str = "host1") -> CronEntry:
    sched = CronSchedule(minute="0", hour="2", dom="*", month="*", dow="*")
    return CronEntry(schedule=sched, command=command, server=server)


def make_issue(severity: str = "error", field: str = "hour", message: str = "bad") -> ValidationIssue:
    return ValidationIssue(
        entry=make_entry(),
        field=field,
        message=message,
        severity=severity,
    )


class TestFormatValidationReport:
    def test_no_issues_returns_pass_message(self):
        report = ValidationReport()
        result = format_validation_report(report)
        assert "passed" in result.lower()

    def test_error_section_present(self):
        report = ValidationReport(issues=[make_issue(severity="error")])
        result = format_validation_report(report)
        assert "Errors" in result

    def test_warning_section_present(self):
        report = ValidationReport(issues=[make_issue(severity="warning")])
        result = format_validation_report(report)
        assert "Warnings" in result

    def test_summary_line_present(self):
        report = ValidationReport(issues=[make_issue(severity="error")])
        result = format_validation_report(report)
        assert "Summary" in result

    def test_summary_hidden_when_disabled(self):
        report = ValidationReport(issues=[make_issue()])
        result = format_validation_report(report, show_summary=False)
        assert "Summary" not in result

    def test_command_truncated_to_60_chars(self):
        long_cmd = "/usr/bin/" + "x" * 80
        issue = ValidationIssue(
            entry=make_entry(command=long_cmd),
            field="minute",
            message="out of range",
            severity="error",
        )
        report = ValidationReport(issues=[issue])
        result = format_validation_report(report)
        # command repr should not exceed 60 chars + quotes
        for line in result.splitlines():
            if "cmd=" in line:
                cmd_part = line.split("cmd=")[1].split(" |")[0]
                assert len(cmd_part) <= 64

    def test_color_codes_absent_by_default(self):
        report = ValidationReport(issues=[make_issue()])
        result = format_validation_report(report, color=False)
        assert "\033[" not in result

    def test_color_codes_present_when_enabled(self):
        report = ValidationReport(issues=[make_issue()])
        result = format_validation_report(report, color=True)
        assert "\033[" in result

    def test_server_name_in_output(self):
        issue = ValidationIssue(
            entry=make_entry(server="prod-server"),
            field="dom",
            message="bad dom",
            severity="warning",
        )
        report = ValidationReport(issues=[issue])
        result = format_validation_report(report)
        assert "prod-server" in result

    def test_format_issue_contains_field(self):
        issue = make_issue(field="month")
        line = _format_issue(issue)
        assert "month" in line
