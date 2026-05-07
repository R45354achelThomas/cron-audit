"""CLI entry-point for sending cron-audit conflict notifications."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cron_audit.notify_config import load_notify_config, validate_notify_config, NotifyConfigError
from cron_audit.notifier import send_conflict_alert
from cron_audit.pipeline import run_from_files


def build_notify_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cron-audit-notify",
        description="Send email alerts for detected cron conflicts.",
    )
    p.add_argument(
        "crontab_files",
        nargs="+",
        metavar="FILE",
        help="Crontab files to analyse.",
    )
    p.add_argument(
        "--config",
        required=True,
        metavar="CONFIG_JSON",
        help="Path to notifier JSON config file.",
    )
    p.add_argument(
        "--min-severity",
        choices=["low", "medium", "high"],
        default="low",
        help="Minimum conflict severity to include in alert (default: low).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without actually sending.",
    )
    return p


_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


def main(argv: list[str] | None = None) -> int:
    parser = build_notify_parser()
    args = parser.parse_args(argv)

    try:
        config = load_notify_config(args.config)
    except NotifyConfigError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    warnings = validate_notify_config(config)
    for w in warnings:
        print(f"[warn] {w}", file=sys.stderr)

    files = [Path(f) for f in args.crontab_files]
    result = run_from_files(files)

    min_rank = _SEVERITY_RANK[args.min_severity]
    filtered = [
        c for c in result.conflicts
        if _SEVERITY_RANK.get(c.severity, 0) >= min_rank
    ]

    if not filtered:
        print("No conflicts meet the minimum severity threshold. No alert sent.")
        return 0

    if args.dry_run:
        print(f"[dry-run] Would send alert for {len(filtered)} conflict(s) to {config.recipients}")
        return 0

    notify_result = send_conflict_alert(filtered, config)
    if notify_result.sent:
        print(f"Alert sent to {notify_result.recipient_count} recipient(s).")
        return 0
    else:
        print(f"[error] Failed to send alert: {notify_result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
