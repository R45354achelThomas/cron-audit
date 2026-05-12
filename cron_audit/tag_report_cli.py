"""CLI sub-command: tag-report — show cron entries grouped by tag."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from cron_audit.pipeline import run_from_files
from cron_audit.tag_report import build_tag_report, format_tag_report


def build_tag_report_parser(sub: "argparse._SubParsersAction") -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser(
        "tag-report",
        help="Display cron entries grouped by their tags.",
    )
    p.add_argument("files", nargs="+", metavar="CRONTAB", help="Crontab files to audit.")
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--tag",
        metavar="TAG",
        dest="filter_tag",
        default=None,
        help="Restrict output to a single tag.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="cron-audit-tag-report")
    sub = parser.add_subparsers(dest="command")
    build_tag_report_parser(sub)
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        result = run_from_files(args.files)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2

    entries = result.entries
    report = build_tag_report(entries)

    if args.filter_tag:
        from cron_audit.tag_report import TagReport, TagGroup

        filtered_group = report.groups.get(args.filter_tag)
        groups = {args.filter_tag: filtered_group} if filtered_group else {}
        report = TagReport(groups=groups, untagged=[])

    if args.format == "json":
        payload = {
            "tags": {
                tag: [
                    {
                        "server": e.server,
                        "command": e.command,
                        "schedule": e.schedule_str(),
                        "tags": getattr(e, "tags", []),
                    }
                    for e in group.entries
                ]
                for tag, group in report.groups.items()
            },
            "untagged_count": report.total_untagged,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_tag_report(report))

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
