"""Maps cron entries to team or individual owners via a config file."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cron_audit.parser import CronEntry


class OwnerMapError(Exception):
    """Raised when the owner map config cannot be loaded or is invalid."""


@dataclass
class OwnerRule:
    owner: str
    servers: List[str] = field(default_factory=list)
    command_contains: List[str] = field(default_factory=list)

    def matches(self, entry: CronEntry) -> bool:
        server_match = (
            not self.servers
            or (entry.server is not None and entry.server in self.servers)
        )
        if not server_match:
            return False
        if self.command_contains:
            return any(kw in entry.command for kw in self.command_contains)
        return True


@dataclass
class OwnerReport:
    owned: Dict[str, List[CronEntry]] = field(default_factory=dict)
    unowned: List[CronEntry] = field(default_factory=list)

    def all_owners(self) -> List[str]:
        return sorted(self.owned.keys())

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"OwnerReport(owners={len(self.owned)}, "
            f"unowned={len(self.unowned)})"
        )


def load_owner_rules(path: Path) -> List[OwnerRule]:
    """Load owner rules from a JSON file.

    Expected format::

        [
          {"owner": "team-infra", "servers": ["prod1"], "command_contains": ["backup"]},
          {"owner": "team-data", "command_contains": ["etl", "import"]}
        ]
    """
    if not path.exists():
        raise OwnerMapError(f"Owner map file not found: {path}")
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise OwnerMapError(f"Invalid JSON in owner map: {exc}") from exc
    if not isinstance(raw, list):
        raise OwnerMapError("Owner map must be a JSON array of rule objects")
    rules: List[OwnerRule] = []
    for item in raw:
        if "owner" not in item:
            raise OwnerMapError(f"Rule missing 'owner' field: {item}")
        rules.append(
            OwnerRule(
                owner=item["owner"],
                servers=item.get("servers", []),
                command_contains=item.get("command_contains", []),
            )
        )
    return rules


def assign_owners(
    entries: List[CronEntry], rules: List[OwnerRule]
) -> OwnerReport:
    """Assign each entry to the first matching owner rule."""
    report = OwnerReport()
    for entry in entries:
        matched: Optional[str] = None
        for rule in rules:
            if rule.matches(entry):
                matched = rule.owner
                break
        if matched:
            report.owned.setdefault(matched, []).append(entry)
        else:
            report.unowned.append(entry)
    return report
