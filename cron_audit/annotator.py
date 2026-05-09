"""Annotator: attach free-text notes to cron entries identified by a key."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cron_audit.parser import CronEntry


class AnnotationError(Exception):
    """Raised when annotation loading or saving fails."""


@dataclass
class Annotation:
    key: str          # server::command
    note: str
    tags: List[str] = field(default_factory=list)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Annotation(key={self.key!r}, note={self.note!r})"


def _entry_key(entry: CronEntry) -> str:
    server = entry.server or "unknown"
    return f"{server}::{entry.command}"


def load_annotations(path: Path) -> Dict[str, Annotation]:
    """Load annotations from a JSON file.  Returns empty dict if file absent."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnnotationError(f"Cannot load annotations from {path}: {exc}") from exc
    result: Dict[str, Annotation] = {}
    for item in raw:
        ann = Annotation(
            key=item["key"],
            note=item.get("note", ""),
            tags=item.get("tags", []),
        )
        result[ann.key] = ann
    return result


def save_annotations(annotations: Dict[str, Annotation], path: Path) -> None:
    """Persist annotations to *path* as JSON."""
    payload = [
        {"key": a.key, "note": a.note, "tags": a.tags}
        for a in annotations.values()
    ]
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        raise AnnotationError(f"Cannot save annotations to {path}: {exc}") from exc


def annotate_entry(entry: CronEntry, annotations: Dict[str, Annotation]) -> Optional[Annotation]:
    """Return the Annotation for *entry*, or None if none exists."""
    return annotations.get(_entry_key(entry))


def upsert_annotation(entry: CronEntry, note: str, tags: List[str],
                      annotations: Dict[str, Annotation]) -> Annotation:
    """Insert or update the annotation for *entry* and return it."""
    key = _entry_key(entry)
    ann = Annotation(key=key, note=note, tags=list(tags))
    annotations[key] = ann
    return ann
