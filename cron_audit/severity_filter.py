"""Severity-based filtering for conflicts and overlap reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from cron_audit.conflict_detector import Conflict

SEVERITY_LEVELS = ("low", "medium", "high")
_RANK = {s: i for i, s in enumerate(SEVERITY_LEVELS)}


def _rank(severity: str) -> int:
    return _RANK.get(severity.lower(), -1)


@dataclass
class SeverityFilterCriteria:
    min_severity: Optional[str] = None   # inclusive lower bound
    max_severity: Optional[str] = None   # inclusive upper bound
    exact: Optional[str] = None          # match exactly one level

    def __post_init__(self) -> None:
        for attr in ("min_severity", "max_severity", "exact"):
            val = getattr(self, attr)
            if val is not None and val.lower() not in SEVERITY_LEVELS:
                raise ValueError(
                    f"Invalid severity '{val}'. Choose from {SEVERITY_LEVELS}."
                )

    def is_empty(self) -> bool:
        return self.min_severity is None and self.max_severity is None and self.exact is None

    def matches(self, severity: str) -> bool:
        if self.is_empty():
            return True
        r = _rank(severity)
        if self.exact is not None:
            return r == _rank(self.exact)
        low = _rank(self.min_severity) if self.min_severity else 0
        high = _rank(self.max_severity) if self.max_severity else len(SEVERITY_LEVELS) - 1
        return low <= r <= high


def filter_conflicts(
    conflicts: Sequence[Conflict],
    criteria: SeverityFilterCriteria,
) -> List[Conflict]:
    """Return only conflicts whose severity matches *criteria*."""
    if criteria.is_empty():
        return list(conflicts)
    return [c for c in conflicts if criteria.matches(c.severity)]


def severity_counts(conflicts: Sequence[Conflict]) -> dict:
    """Return a dict mapping each severity level to its count."""
    counts: dict = {s: 0 for s in SEVERITY_LEVELS}
    for c in conflicts:
        key = c.severity.lower()
        if key in counts:
            counts[key] += 1
    return counts
