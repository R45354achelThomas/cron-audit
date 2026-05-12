"""Validates cron schedule fields for correctness and common mistakes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cron_audit.parser import CronEntry

_FIELD_RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "dom": (1, 31),
    "month": (1, 12),
    "dow": (0, 7),
}


@dataclass
class ValidationIssue:
    entry: CronEntry
    field: str
    message: str
    severity: str = "warning"  # "warning" | "error"

    def __repr__(self) -> str:
        return f"<ValidationIssue [{self.severity}] {self.field}: {self.message}>"


@dataclass
class ValidationReport:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def has_issues(self) -> bool:
        return bool(self.issues)

    def __repr__(self) -> str:
        return f"<ValidationReport errors={len(self.errors)} warnings={len(self.warnings)}>"


def _check_field(value: str, name: str, lo: int, hi: int) -> List[str]:
    """Return a list of error messages for a single schedule field."""
    issues: List[str] = []
    if value == "*":
        return issues
    parts = value.split(",")
    for part in parts:
        step_parts = part.split("/")
        base = step_parts[0]
        if len(step_parts) == 2:
            step = step_parts[1]
            if not step.isdigit() or int(step) < 1:
                issues.append(f"invalid step value '{step}'")
        if "-" in base:
            bounds = base.split("-", 1)
            for b in bounds:
                if not b.isdigit():
                    issues.append(f"non-numeric range bound '{b}'")
                    continue
                v = int(b)
                if not (lo <= v <= hi):
                    issues.append(f"value {v} out of range [{lo}-{hi}]")
            if all(b.isdigit() for b in bounds):
                if int(bounds[0]) > int(bounds[1]):
                    issues.append(f"range start {bounds[0]} > end {bounds[1]}")
        elif base != "*":
            if not base.isdigit():
                issues.append(f"non-numeric value '{base}'")
            else:
                v = int(base)
                if not (lo <= v <= hi):
                    issues.append(f"value {v} out of range [{lo}-{hi}]")
    return issues


def validate_entries(entries: List[CronEntry]) -> ValidationReport:
    report = ValidationReport()
    for entry in entries:
        sched = entry.schedule
        field_values = {
            "minute": sched.minute,
            "hour": sched.hour,
            "dom": sched.dom,
            "month": sched.month,
            "dow": sched.dow,
        }
        for fname, fval in field_values.items():
            lo, hi = _FIELD_RANGES[fname]
            for msg in _check_field(fval, fname, lo, hi):
                severity = "error" if "out of range" in msg or "non-numeric" in msg else "warning"
                report.issues.append(ValidationIssue(entry=entry, field=fname, message=msg, severity=severity))
    return report
