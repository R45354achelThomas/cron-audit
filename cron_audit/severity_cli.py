"""CLI sub-command: severity  — filter and summarise conflicts by severity."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from cron_audit.archiver import load_snapshot
from cron_audit.severity_filter import (
    SEVERITY_LEVELS,
    SeverityFilterCriteria,
    filter_conflicts,
    severity_counts,
)


def build_severity_parser(parent: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = parent.add_parser(
        "severity",
        help="Filter and summarise conflicts by severity level.",
    )
    p.add_argument("snapshot", help="Path to a saved snapshot (.json).")
    p.add_argument(
        "--min",
        dest="min_severity",
        choices=SEVERITY_LEVELS,
        default=None,
        help="Minimum severity to include (inclusive).",
    )
    p.add_argument(
        "--max",
        dest="max_severity",
        choices=SEVERITY_LEVELS,
        default=None,
        help="Maximum severity to include (inclusive).",
    )
    p.add_argument(
        "--exact",
        choices=SEVERITY_LEVELS,
        default=None,
        help="Show only conflicts of exactly this severity.",
    )
    p.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--counts-only",
        action="store_true",
        help="Print only the severity counts, not individual conflicts.",
    )
    return p


def main(args: argparse.Namespace) -> int:
    snapshot_path = Path(args.snapshot)
    try:
        result = load_snapshot(snapshot_path)
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not load snapshot: {exc}", file=sys.stderr)
        return 1

    criteria = SeverityFilterCriteria(
        min_severity=args.min_severity,
        max_severity=args.max_severity,
        exact=args.exact,
    )

    filtered = filter_conflicts(result.conflicts, criteria)
    counts = severity_counts(filtered)

    if args.format == "json":
        payload: dict = {"counts": counts}
        if not args.counts_only:
            payload["conflicts"] = [
                {
                    "severity": c.severity,
                    "reason": c.reason,
                    "command_a": c.entry_a.command,
                    "command_b": c.entry_b.command,
                }
                for c in filtered
            ]
        print(json.dumps(payload, indent=2))
        return 0

    # text output
    print(f"Severity counts: {counts}")
    if not args.counts_only:
        if not filtered:
            print("No conflicts match the given criteria.")
        else:
            for c in filtered:
                print(f"  [{c.severity.upper()}] {c.reason} — {c.entry_a.command}")
    return 0
