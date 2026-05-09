"""CLI sub-command: cron-audit watchdog — report stale cron entries."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import List, Optional

from cron_audit.pipeline import run_from_files
from cron_audit.watchdog import StaleEntry, check_staleness


def build_watchdog_parser(subparsers=None) -> argparse.ArgumentParser:
    desc = "Detect cron entries that are overdue based on their schedule."
    if subparsers is not None:
        p = subparsers.add_parser("watchdog", help=desc, description=desc)
    else:
        p = argparse.ArgumentParser(prog="cron-audit watchdog", description=desc)

    p.add_argument("files", nargs="+", metavar="CRONTAB", help="Crontab files to load.")
    p.add_argument(
        "--last-run",
        metavar="JSON",
        help=(
            'JSON file mapping {"server:command": "ISO8601-datetime"} '
            "to last known run times."
        ),
    )
    p.add_argument(
        "--grace",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Grace period in seconds before flagging an entry (default: 0).",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    return p


def _load_last_run_map(path: Optional[str]) -> dict:
    if path is None:
        return {}
    try:
        with open(path) as fh:
            raw: dict = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[watchdog] Cannot load last-run file: {exc}", file=sys.stderr)
        return {}
    result = {}
    for key, ts in raw.items():
        if ":" not in key:
            continue
        server, _, command = key.partition(":")
        try:
            dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        result[(server.strip(), command.strip())] = dt
    return result


def _format_text(stale: List[StaleEntry]) -> str:
    if not stale:
        return "No stale entries detected.\n"
    lines = [f"Stale entries detected: {len(stale)}\n"]
    for se in stale:
        hours = se.overdue_seconds / 3600
        last = se.last_run.isoformat() if se.last_run else "never"
        lines.append(
            f"  [{se.entry.server}] {se.entry.command}\n"
            f"    last run : {last}\n"
            f"    expected : {se.expected_next.isoformat()}\n"
            f"    overdue  : {hours:.1f}h\n"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = build_watchdog_parser()
    args = parser.parse_args(argv)

    result = run_from_files(args.files)
    last_run_map = _load_last_run_map(args.last_run)
    stale = check_staleness(result.entries, last_run_map, grace_seconds=args.grace)

    if args.format == "json":
        payload = [
            {
                "server": se.entry.server,
                "command": se.entry.command,
                "last_run": se.last_run.isoformat() if se.last_run else None,
                "expected_next": se.expected_next.isoformat(),
                "overdue_seconds": round(se.overdue_seconds, 1),
            }
            for se in stale
        ]
        print(json.dumps(payload, indent=2))
    else:
        print(_format_text(stale), end="")

    return 1 if stale else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
