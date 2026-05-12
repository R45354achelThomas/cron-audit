"""CLI entry point for schedule validation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cron_audit.loader import load_from_file, LoadError
from cron_audit.parser import parse_crontab
from cron_audit.schedule_validator import validate_entries, ValidationReport


def build_validation_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cron-validate",
        description="Validate cron schedule fields for range and syntax errors.",
    )
    p.add_argument("files", nargs="+", metavar="FILE", help="Crontab files to validate")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--strict", action="store_true", help="Exit non-zero on warnings too")
    return p


def _format_text(report: ValidationReport) -> str:
    if not report.has_issues():
        return "No issues found."
    lines = []
    for issue in report.issues:
        tag = f"[{issue.severity.upper()}]"
        cmd = issue.entry.command[:50]
        lines.append(f"{tag} server={issue.entry.server} field={issue.field} cmd={cmd!r} — {issue.message}")
    return "\n".join(lines)


def _format_json(report: ValidationReport) -> str:
    data = [
        {
            "severity": i.severity,
            "server": i.entry.server,
            "field": i.field,
            "command": i.entry.command,
            "message": i.message,
        }
        for i in report.issues
    ]
    return json.dumps(data, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = build_validation_parser()
    args = parser.parse_args(argv)

    all_entries = []
    for filepath in args.files:
        try:
            server, content = load_from_file(Path(filepath))
            all_entries.extend(parse_crontab(content, server=server))
        except LoadError as exc:
            print(f"Error loading {filepath}: {exc}", file=sys.stderr)
            return 2

    report = validate_entries(all_entries)

    output = _format_json(report) if args.format == "json" else _format_text(report)
    print(output)

    if report.errors:
        return 1
    if args.strict and report.warnings:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
