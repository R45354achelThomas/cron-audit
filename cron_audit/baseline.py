"""Baseline snapshot management for cron-audit.

Allows saving and loading a known-good snapshot of CronEntry lists
so that future runs can diff against a stable reference.
"""

from __future__ import annotations

import json
import os
from typing import List, Tuple

from cron_audit.parser import CronEntry, CronSchedule


class BaselineError(Exception):
    """Raised when a baseline file cannot be read or written."""


def _entry_to_dict(entry: CronEntry) -> dict:
    s = entry.schedule
    return {
        "server": entry.server,
        "command": entry.command,
        "user": entry.user,
        "raw_line": entry.raw_line,
        "schedule": {
            "minute": s.minute,
            "hour": s.hour,
            "dom": s.dom,
            "month": s.month,
            "dow": s.dow,
        },
    }


def _dict_to_entry(d: dict) -> CronEntry:
    s = d["schedule"]
    schedule = CronSchedule(
        minute=s["minute"],
        hour=s["hour"],
        dom=s["dom"],
        month=s["month"],
        dow=s["dow"],
    )
    return CronEntry(
        server=d["server"],
        command=d["command"],
        user=d.get("user", ""),
        raw_line=d.get("raw_line", ""),
        schedule=schedule,
    )


def save_baseline(entries: List[CronEntry], path: str) -> None:
    """Serialise *entries* to *path* as a JSON baseline file."""
    try:
        data = [_entry_to_dict(e) for e in entries]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "entries": data}, fh, indent=2)
    except OSError as exc:
        raise BaselineError(f"Cannot write baseline to {path!r}: {exc}") from exc


def load_baseline(path: str) -> List[CronEntry]:
    """Load a previously saved baseline from *path*."""
    if not os.path.exists(path):
        raise BaselineError(f"Baseline file not found: {path!r}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"Cannot read baseline from {path!r}: {exc}") from exc
    return [_dict_to_entry(d) for d in raw.get("entries", [])]
