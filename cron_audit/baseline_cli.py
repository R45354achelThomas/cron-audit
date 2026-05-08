"""CLI sub-commands for baseline management.

Usage examples:
    cron-audit baseline save --files crontabs/*.txt --output baseline.json
    cron-audit baseline compare --files crontabs/*.txt --baseline baseline.json
"""

from __future__ import annotations

import argparse
import sys

from cron_audit.baseline import save_baseline, load_baseline, BaselineError
from cron_audit.differ import diff_entries
from cron_audit.formatter_diff import format_diff
from cron_audit.pipeline import run_from_files


def build_baseline_parser(parent: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    bp = parent.add_parser("baseline", help="Manage cron baseline snapshots")
    sub = bp.add_subparsers(dest="baseline_cmd", required=True)

    # --- save ---
    save_p = sub.add_parser("save", help="Save current cron state as baseline")
    save_p.add_argument("--files", nargs="+", required=True,
                        metavar="FILE", help="Crontab files to snapshot")
    save_p.add_argument("--output", required=True,
                        metavar="PATH", help="Destination baseline JSON file")

    # --- compare ---
    cmp_p = sub.add_parser("compare", help="Compare current state against baseline")
    cmp_p.add_argument("--files", nargs="+", required=True,
                       metavar="FILE", help="Current crontab files")
    cmp_p.add_argument("--baseline", required=True,
                       metavar="PATH", help="Baseline JSON file to compare against")
    cmp_p.add_argument("--no-color", action="store_true",
                       help="Disable ANSI colour output")


def _cmd_save(args: argparse.Namespace) -> int:
    result = run_from_files(args.files)
    try:
        save_baseline(result.entries, args.output)
    except BaselineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Baseline saved to {args.output!r} ({len(result.entries)} entries).")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    try:
        baseline_entries = load_baseline(args.baseline)
    except BaselineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    result = run_from_files(args.files)
    diff = diff_entries(baseline_entries, result.entries)
    print(format_diff(diff, color=not args.no_color))
    return 0 if not diff.has_changes() else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cron-audit-baseline",
        description="Baseline snapshot commands for cron-audit",
    )
    sub = parser.add_subparsers(dest="baseline_cmd", required=True)
    _register(sub)
    args = parser.parse_args(argv)
    if args.baseline_cmd == "save":
        return _cmd_save(args)
    if args.baseline_cmd == "compare":
        return _cmd_compare(args)
    parser.print_help()
    return 1


def _register(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    save_p = sub.add_parser("save")
    save_p.add_argument("--files", nargs="+", required=True)
    save_p.add_argument("--output", required=True)

    cmp_p = sub.add_parser("compare")
    cmp_p.add_argument("--files", nargs="+", required=True)
    cmp_p.add_argument("--baseline", required=True)
    cmp_p.add_argument("--no-color", action="store_true")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
