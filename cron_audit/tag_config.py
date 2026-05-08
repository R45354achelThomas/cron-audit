"""Load and validate tag rule configuration from a JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from cron_audit.tagger import TagRule, load_tag_rules


class TagConfigError(Exception):
    """Raised when a tag config file cannot be loaded or validated."""


_REQUIRED_RULE_KEYS = {"pattern", "tags"}


def _validate_rules(rules: Any) -> None:
    if not isinstance(rules, list):
        raise TagConfigError("'rules' must be a list")
    for i, item in enumerate(rules):
        if not isinstance(item, dict):
            raise TagConfigError(f"Rule #{i} must be an object")
        missing = _REQUIRED_RULE_KEYS - item.keys()
        if missing:
            raise TagConfigError(
                f"Rule #{i} is missing required keys: {', '.join(sorted(missing))}"
            )
        if not isinstance(item["tags"], list):
            raise TagConfigError(f"Rule #{i}: 'tags' must be a list")


def load_tag_config(path: str | Path) -> List[TagRule]:
    """Load a JSON tag-rules config file and return parsed :class:`TagRule` objects.

    The JSON file must have the structure::

        {
            "rules": [
                {"pattern": "<regex>", "tags": ["tag1", "tag2"]}
            ]
        }

    Raises :class:`TagConfigError` on any loading or validation failure.
    """
    p = Path(path)
    if not p.exists():
        raise TagConfigError(f"Tag config file not found: {p}")

    try:
        raw: Dict = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TagConfigError(f"Invalid JSON in tag config: {exc}") from exc

    if "rules" not in raw:
        raise TagConfigError("Tag config must contain a top-level 'rules' key")

    _validate_rules(raw["rules"])
    return load_tag_rules(raw)
