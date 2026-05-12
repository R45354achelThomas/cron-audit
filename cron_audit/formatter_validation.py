"""Human-readable and structured formatting for ValidationReport."""
from __future__ import annotations

from cron_audit.schedule_validator import ValidationReport, ValidationIssue

_SEV_COLORS = {
    "error": "\033[31m",   # red
    "warning": "\033[33m",  # yellow
}
_RESET = "\033[0m"


def _colorize(text: str, severity: str, color: bool) -> str:
    if not color:
        return text
    code = _SEV_COLORS.get(severity, "")
    return f"{code}{text}{_RESET}"


def _format_issue(issue: ValidationIssue, color: bool = False) -> str:
    tag = _colorize(f"[{issue.severity.upper()}]", issue.severity, color)
    cmd = issue.entry.command[:60]
    return (
        f"{tag} {issue.entry.server} | field={issue.field} | "
        f"cmd={cmd!r} | {issue.message}"
    )


def format_validation_report(
    report: ValidationReport,
    color: bool = False,
    show_summary: bool = True,
) -> str:
    if not report.has_issues():
        return "Validation passed — no issues found."

    lines: list[str] = []

    if report.errors:
        lines.append("=== Errors ===")
        for issue in report.errors:
            lines.append("  " + _format_issue(issue, color=color))

    if report.warnings:
        lines.append("=== Warnings ===")
        for issue in report.warnings:
            lines.append("  " + _format_issue(issue, color=color))

    if show_summary:
        lines.append(
            f"Summary: {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
        )

    return "\n".join(lines)
