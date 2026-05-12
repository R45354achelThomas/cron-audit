"""Retention policy evaluation for cron entries.

Determines whether a cron entry is within an expected execution
frequency window and flags entries that may be over- or under-scheduled
based on configurable policy rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cron_audit.parser import CronEntry


@dataclass
class PolicyRule:
    """A single retention policy rule."""
    name: str
    command_pattern: str          # substring match against entry.command
    min_interval_minutes: int     # minimum expected gap between runs
    max_interval_minutes: int     # maximum expected gap between runs
    severity: str = "medium"      # low | medium | high

    def __post_init__(self) -> None:
        if self.min_interval_minutes < 0:
            raise ValueError("min_interval_minutes must be >= 0")
        if self.max_interval_minutes < self.min_interval_minutes:
            raise ValueError("max_interval_minutes must be >= min_interval_minutes")
        if self.severity not in {"low", "medium", "high"}:
            raise ValueError(f"Unknown severity: {self.severity}")

    def matches(self, entry: CronEntry) -> bool:
        return self.command_pattern.lower() in entry.command.lower()


@dataclass
class PolicyViolation:
    """A policy rule violation for a specific entry."""
    entry: CronEntry
    rule: PolicyRule
    actual_interval_minutes: int
    message: str

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"PolicyViolation(rule={self.rule.name!r}, "
            f"server={self.entry.server!r}, "
            f"command={self.entry.command!r}, "
            f"severity={self.rule.severity!r})"
        )


def _estimate_interval_minutes(entry: CronEntry) -> Optional[int]:
    """Return the approximate interval between runs in minutes, or None."""
    s = entry.schedule
    try:
        minute = s.minute
        hour = s.hour
        dom = s.dom
        month = s.month
        dow = s.dow
    except AttributeError:
        return None

    if minute == "*" and hour == "*":
        return 1
    if hour == "*" and minute != "*":
        # runs once per hour
        return 60
    if dom == "*" and month == "*" and dow == "*":
        # runs once per day if minute and hour are fixed
        return 1440
    if dom != "*" or dow != "*":
        return 10080  # weekly approximation
    return None


def evaluate_policy(
    entries: List[CronEntry],
    rules: List[PolicyRule],
) -> List[PolicyViolation]:
    """Return all policy violations found across *entries* given *rules*."""
    violations: List[PolicyViolation] = []
    for entry in entries:
        for rule in rules:
            if not rule.matches(entry):
                continue
            interval = _estimate_interval_minutes(entry)
            if interval is None:
                continue
            if interval < rule.min_interval_minutes:
                msg = (
                    f"Entry runs every ~{interval}m but policy '{rule.name}' "
                    f"requires at least {rule.min_interval_minutes}m between runs."
                )
                violations.append(PolicyViolation(entry, rule, interval, msg))
            elif interval > rule.max_interval_minutes:
                msg = (
                    f"Entry runs every ~{interval}m but policy '{rule.name}' "
                    f"expects at most {rule.max_interval_minutes}m between runs."
                )
                violations.append(PolicyViolation(entry, rule, interval, msg))
    return violations
