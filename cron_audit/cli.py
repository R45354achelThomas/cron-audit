"""Command-line interface for cron-audit."""

import argparse
import sys
from pathlib import Path
from cron_audit.parser import parse_crontab, CronEntry
from cron_audit.conflict_detector import detect_conflicts
from cron_audit.reporter import generate_report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cron-audit",
        description="Parse crontab files and generate a unified audit report.",
    )
    p.add_argument(
        "files",
        metavar="FILE",
        nargs="+",
        help="Path(s) to crontab file(s). Use --server to label each file.",
    )
    p.add_argument(
        "--server",
        metavar="NAME",
        nargs="+",
        help="Server name(s) corresponding to each FILE (positional match).",
    )
    p.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Write report to FILE instead of stdout.",
    )
    p.add_argument(
        "--title",
        default="Cron Audit Report",
        help="Title shown at the top of the report.",
    )
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    servers = args.server or []
    all_entries: list[CronEntry] = []

    for idx, filepath in enumerate(args.files):
        path = Path(filepath)
        if not path.exists():
            print(f"ERROR: File not found: {filepath}", file=sys.stderr)
            return 1

        server_name = servers[idx] if idx < len(servers) else path.stem
        raw = path.read_text(encoding="utf-8")
        entries = parse_crontab(raw)
        for entry in entries:
            entry.server = server_name  # type: ignore[attr-defined]
        all_entries.extend(entries)

    conflicts = detect_conflicts(all_entries)
    report = generate_report(all_entries, conflicts, title=args.title)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(report)

    return 1 if conflicts else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
