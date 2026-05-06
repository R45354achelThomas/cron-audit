"""Command-line interface for cron-audit."""

import argparse
import sys
from pathlib import Path

from cron_audit.parser import parse_crontab
from cron_audit.conflict_detector import detect_conflicts
from cron_audit.reporter import generate_report
from cron_audit.exporter import export_json, export_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cron-audit",
        description="Parse and document cron jobs with conflict detection.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="CRONTAB_FILE",
        help="One or more crontab files to audit.",
    )
    parser.add_argument(
        "--server",
        metavar="NAME",
        default=None,
        help="Override the server name for all supplied files.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        dest="output_format",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Write output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--no-conflicts",
        action="store_true",
        default=False,
        help="Skip conflict detection.",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    entries = []
    for filepath in args.files:
        path = Path(filepath)
        if not path.exists():
            print(f"cron-audit: file not found: {filepath}", file=sys.stderr)
            return 1
        server = args.server or path.stem
        entries.extend(parse_crontab(path.read_text(), server=server))

    conflicts = [] if args.no_conflicts else detect_conflicts(entries)

    if args.output_format == "json":
        output = export_json(entries, conflicts)
    elif args.output_format == "csv":
        output = export_csv(entries, conflicts)
    else:
        output = generate_report(entries, conflicts)

    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
