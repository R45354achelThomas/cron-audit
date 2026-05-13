"""Allowlist checker: flags cron commands not present in an approved list."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cron_audit.parser import CronEntry


class AllowlistError(Exception):
    """Raised when the allowlist file cannot be loaded or parsed."""


@dataclass
class AllowlistViolation:
    entry: CronEntry
    reason: str

    def __repr__(self) -> str:  # pragma: no cover
        return f"AllowlistViolation(server={self.entry.server!r}, command={self.entry.command!r})"


@dataclass
class AllowlistReport:
    violations: List[AllowlistViolation] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return bool(self.violations)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AllowlistReport(violations={len(self.violations)})"


def load_allowlist(path: Path) -> List[str]:
    """Load approved command prefixes/substrings from a JSON file.

    The file must contain a JSON array of strings, e.g.::

        ["/usr/bin/backup", "/opt/scripts/", "python3 /srv"]

    Raises :class:`AllowlistError` on any I/O or parse failure.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AllowlistError(f"Allowlist file not found: {path}")
    except OSError as exc:
        raise AllowlistError(f"Cannot read allowlist file: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AllowlistError(f"Invalid JSON in allowlist file: {exc}") from exc

    if not isinstance(data, list) or not all(isinstance(s, str) for s in data):
        raise AllowlistError("Allowlist file must contain a JSON array of strings.")

    return [s.strip() for s in data if s.strip()]


def _is_allowed(command: str, allowlist: List[str]) -> bool:
    """Return True if *command* starts with or contains any allowlist entry."""
    for pattern in allowlist:
        if command.startswith(pattern) or pattern in command:
            return True
    return False


def check_allowlist(
    entries: List[CronEntry],
    allowlist: List[str],
    server: Optional[str] = None,
) -> AllowlistReport:
    """Check *entries* against *allowlist*, optionally filtering by *server*."""
    violations: List[AllowlistViolation] = []
    for entry in entries:
        if server and entry.server != server:
            continue
        if not _is_allowed(entry.command, allowlist):
            violations.append(
                AllowlistViolation(
                    entry=entry,
                    reason=f"Command not in allowlist: {entry.command!r}",
                )
            )
    return AllowlistReport(violations=violations)
