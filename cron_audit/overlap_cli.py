"""CLI sub-command: overlap  —  report schedule conflicts from crontab files.

Usage:
    cron-audit overlap FILE [FILE ...] [--format text|json] [--min-severity LEVEL]
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from cron_audit.conflict_detector import detect_conflicts
from cron_audit.overlap_reporter import (
    build_overlap_report,
    format_overlap_report,
)
from cron_audit.pipeline import run_from_files

_SEVERITIES = ("low", "medium", "high")
_SEVERITY_RANK = {s: i for i, s in enumerate(_SEVERITIES)}


def build_overlap_parser(parent: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:  # noqa: E501
    kwargs = dict(
        description="Detect and report overlapping cron schedules.",
    )
    if parent is not None:
        parser = parent.add_parser("overlap", **kwargs)
    else:
        parser = argparse.ArgumentParser(prog="cron-audit overlap", **kwargs)

    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Crontab files to analyse.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--min-severity",
        choices=_SEVERITIES,
        default="low",
        dest="min_severity",
        help="Only show conflicts at or above this severity (default: low).",
    )
    return parser


def _filter_by_severity(report, min_severity: str):
    """Return a new report containing only conflicts >= *min_severity*."""
    from cron_audit.overlap_reporter import OverlapReport

    rank = _SEVERITY_RANK[min_severity]
    return OverlapReport(
        high=report.high if _SEVERITY_RANK["high"] >= rank else [],
        medium=report.medium if _SEVERITY_RANK["medium"] >= rank else [],
        low=report.low if _SEVERITY_RANK["low"] >= rank else [],
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_overlap_parser()
    args = parser.parse_args(argv)

    try:
        result = run_from_files(args.files)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1

    conflicts = detect_conflicts(result.entries)
    report = build_overlap_report(conflicts)
    report = _filter_by_severity(report, args.min_severity)

    if args.output_format == "json":
        payload = {
            "total": report.total,
            "high": [str(c) for c in report.high],
            "medium": [str(c) for c in report.medium],
            "low": [str(c) for c in report.low],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_overlap_report(report), end="")

    return 1 if report.total > 0 else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
