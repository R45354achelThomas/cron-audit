"""Archive pipeline results to timestamped JSON snapshots on disk."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cron_audit.exporter import _entry_to_dict, _conflict_to_dict
from cron_audit.pipeline import PipelineResult


class ArchiveError(Exception):
    """Raised when an archive operation fails."""


_TIMESTAMP_FMT = "%Y%m%dT%H%M%SZ"


def _snapshot_filename(prefix: str, ts: datetime) -> str:
    return f"{prefix}_{ts.strftime(_TIMESTAMP_FMT)}.json"


def save_snapshot(
    result: PipelineResult,
    directory: str | Path,
    prefix: str = "snapshot",
    now: Optional[datetime] = None,
) -> Path:
    """Serialise *result* to a timestamped JSON file inside *directory*.

    Returns the path of the written file.
    """
    directory = Path(directory)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ArchiveError(f"Cannot create archive directory '{directory}': {exc}") from exc

    ts = now or datetime.now(tz=timezone.utc)
    filename = _snapshot_filename(prefix, ts)
    dest = directory / filename

    payload = {
        "timestamp": ts.isoformat(),
        "entries": [_entry_to_dict(e) for e in result.entries],
        "conflicts": [_conflict_to_dict(c) for c in result.conflicts],
    }

    try:
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        raise ArchiveError(f"Failed to write snapshot '{dest}': {exc}") from exc

    return dest


def list_snapshots(directory: str | Path, prefix: str = "snapshot") -> List[Path]:
    """Return snapshot files in *directory* sorted oldest-first."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    files = sorted(directory.glob(f"{prefix}_*.json"))
    return files


def load_snapshot(path: str | Path) -> dict:
    """Load a snapshot file and return its parsed contents."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArchiveError(f"Cannot read snapshot '{path}': {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ArchiveError(f"Snapshot '{path}' is not valid JSON: {exc}") from exc
