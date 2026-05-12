"""Classify cron entries by environment (prod, staging, dev, etc.) based on server name or command patterns."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cron_audit.parser import CronEntry


_DEFAULT_RULES: List[tuple[str, str]] = [
    (r"prod", "production"),
    (r"staging|stage", "staging"),
    (r"dev(?:el)?", "development"),
    (r"test|qa", "testing"),
]


@dataclass
class EnvironmentGroup:
    environment: str
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def server_names(self) -> List[str]:
        return sorted({e.server for e in self.entries if e.server})

    def __repr__(self) -> str:  # pragma: no cover
        return f"EnvironmentGroup(env={self.environment!r}, count={len(self.entries)})"


@dataclass
class EnvironmentReport:
    groups: Dict[str, EnvironmentGroup] = field(default_factory=dict)

    @property
    def environments(self) -> List[str]:
        return sorted(self.groups.keys())

    @property
    def unclassified(self) -> List[CronEntry]:
        return self.groups.get("unclassified", EnvironmentGroup("unclassified")).entries

    def __repr__(self) -> str:  # pragma: no cover
        return f"EnvironmentReport(envs={self.environments})"


def _classify_entry(
    entry: CronEntry,
    rules: List[tuple[str, str]],
) -> str:
    """Return the environment label for *entry* using *rules*, or 'unclassified'."""
    candidates = [entry.server or "", entry.command]
    for pattern, label in rules:
        rx = re.compile(pattern, re.IGNORECASE)
        if any(rx.search(c) for c in candidates):
            return label
    return "unclassified"


def build_environment_report(
    entries: List[CronEntry],
    rules: Optional[List[tuple[str, str]]] = None,
) -> EnvironmentReport:
    """Group *entries* into an :class:`EnvironmentReport` using *rules*.

    If *rules* is ``None`` the built-in heuristics are used.
    """
    effective_rules = rules if rules is not None else _DEFAULT_RULES
    report = EnvironmentReport()
    for entry in entries:
        label = _classify_entry(entry, effective_rules)
        if label not in report.groups:
            report.groups[label] = EnvironmentGroup(environment=label)
        report.groups[label].entries.append(entry)
    return report
