"""Tag cron entries with user-defined labels based on command patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cron_audit.parser import CronEntry


@dataclass
class TagRule:
    """A rule that maps a regex pattern to one or more tags."""

    pattern: str
    tags: List[str]
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern)

    def matches(self, command: str) -> bool:
        return bool(self._compiled.search(command))


def load_tag_rules(rules_dict: Dict) -> List[TagRule]:
    """Parse a list of rule dicts into TagRule objects.

    Expected format::

        [{"pattern": "backup", "tags": ["backup", "storage"]}, ...]
    """
    rules: List[TagRule] = []
    for item in rules_dict.get("rules", []):
        pattern = item.get("pattern", "")
        tags = item.get("tags", [])
        if pattern and tags:
            rules.append(TagRule(pattern=pattern, tags=tags))
    return rules


def tag_entry(entry: CronEntry, rules: List[TagRule]) -> List[str]:
    """Return a deduplicated list of tags that apply to *entry*."""
    matched: List[str] = []
    for rule in rules:
        if rule.matches(entry.command):
            for t in rule.tags:
                if t not in matched:
                    matched.append(t)
    return matched


def tag_entries(
    entries: List[CronEntry], rules: List[TagRule]
) -> Dict[CronEntry, List[str]]:
    """Return a mapping of every entry to its resolved tags."""
    return {entry: tag_entry(entry, rules) for entry in entries}
