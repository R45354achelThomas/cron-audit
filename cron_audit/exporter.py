"""Export cron audit reports to various file formats (JSON, CSV)."""

import csv
import json
import io
from typing import List, Dict, Any

from cron_audit.parser import CronEntry
from cron_audit.conflict_detector import Conflict


def _entry_to_dict(entry: CronEntry) -> Dict[str, Any]:
    """Convert a CronEntry to a serializable dictionary."""
    return {
        "server": entry.server,
        "user": entry.user,
        "schedule": entry.schedule,
        "command": entry.command,
        "comment": entry.comment,
    }


def _conflict_to_dict(conflict: Conflict) -> Dict[str, Any]:
    """Convert a Conflict to a serializable dictionary."""
    return {
        "reason": conflict.reason,
        "entry_a": _entry_to_dict(conflict.entry_a),
        "entry_b": _entry_to_dict(conflict.entry_b),
    }


def export_json(
    entries: List[CronEntry],
    conflicts: List[Conflict],
    indent: int = 2,
) -> str:
    """Serialize entries and conflicts to a JSON string."""
    payload = {
        "entries": [_entry_to_dict(e) for e in entries],
        "conflicts": [_conflict_to_dict(c) for c in conflicts],
    }
    return json.dumps(payload, indent=indent)


def export_csv(entries: List[CronEntry], conflicts: List[Conflict]) -> str:
    """Serialize entries and conflicts to a CSV string.

    The output contains two sections separated by a blank line:
    one for cron entries and one for detected conflicts.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # --- Entries section ---
    writer.writerow(["section", "server", "user", "schedule", "command", "comment"])
    for entry in entries:
        writer.writerow(
            [
                "entry",
                entry.server,
                entry.user,
                entry.schedule,
                entry.command,
                entry.comment or "",
            ]
        )

    writer.writerow([])  # blank separator

    # --- Conflicts section ---
    writer.writerow(
        ["section", "reason", "server_a", "command_a", "schedule_a", "server_b", "command_b", "schedule_b"]
    )
    for conflict in conflicts:
        writer.writerow(
            [
                "conflict",
                conflict.reason,
                conflict.entry_a.server,
                conflict.entry_a.command,
                conflict.entry_a.schedule,
                conflict.entry_b.server,
                conflict.entry_b.command,
                conflict.entry_b.schedule,
            ]
        )

    return output.getvalue()
