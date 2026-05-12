"""CLI sub-command: retention — evaluate retention policies against cron entries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from cron_audit.pipeline import run_from_files
from cron_audit.retention_policy import PolicyRule, PolicyViolation, evaluate_policy


def build_retention_parser(sub: "argparse._SubParsersAction") -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser(
        "retention",
        help="Evaluate retention policies against parsed cron entries.",
    )
    p.add_argument("files", nargs="+", help="Crontab files to audit.")
    p.add_argument(
        "--policy",
        required=True,
        metavar="FILE",
        help="JSON file containing policy rules.",
    )
    p.add_argument(
        "--severity",
        choices=["low", "medium", "high"],
        default=None,
        help="Only report violations at this severity level or above.",
    )
    p.add_argument(
        "--format",
        dest="fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    return p


_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def _load_rules(path: str) -> List[PolicyRule]:
    data = json.loads(Path(path).read_text())
    rules = []
    for item in data:
        rules.append(
            PolicyRule(
                name=item["name"],
                command_pattern=item["command_pattern"],
                min_interval_minutes=item["min_interval_minutes"],
                max_interval_minutes=item["max_interval_minutes"],
                severity=item.get("severity", "medium"),
            )
        )
    return rules


def _format_text(violations: List[PolicyViolation]) -> str:
    if not violations:
        return "No retention policy violations found.\n"
    lines = [f"Retention Policy Violations ({len(violations)} found):", ""]
    for v in violations:
        lines.append(f"  [{v.rule.severity.upper()}] {v.rule.name}")
        lines.append(f"    Server : {v.entry.server or 'unknown'}")
        lines.append(f"    Command: {v.entry.command}")
        lines.append(f"    Reason : {v.message}")
        lines.append("")
    return "\n".join(lines)


def _format_json(violations: List[PolicyViolation]) -> str:
    out = [
        {
            "rule": v.rule.name,
            "severity": v.rule.severity,
            "server": v.entry.server,
            "command": v.entry.command,
            "actual_interval_minutes": v.actual_interval_minutes,
            "message": v.message,
        }
        for v in violations
    ]
    return json.dumps(out, indent=2)


def main(args: argparse.Namespace) -> int:
    try:
        rules = _load_rules(args.policy)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error loading policy file: {exc}", file=sys.stderr)
        return 1

    result = run_from_files(args.files)
    violations = evaluate_policy(result.entries, rules)

    if args.severity:
        min_level = _SEVERITY_ORDER[args.severity]
        violations = [v for v in violations if _SEVERITY_ORDER[v.rule.severity] >= min_level]

    if args.fmt == "json":
        print(_format_json(violations))
    else:
        print(_format_text(violations), end="")

    return 1 if violations else 0
