"""Render a report section that includes per-entry annotations."""
from __future__ import annotations

from typing import Dict, List

from cron_audit.annotator import Annotation, annotate_entry
from cron_audit.formatter import format_entry
from cron_audit.parser import CronEntry

_RESET = "\033[0m"
_CYAN = "\033[36m"
_DIM = "\033[2m"


def _note_line(ann: Annotation) -> str:
    tags_str = "  [" + ", ".join(ann.tags) + "]" if ann.tags else ""
    return f"{_CYAN}    note: {ann.note}{tags_str}{_RESET}"


def format_annotated_entry(entry: CronEntry, annotations: Dict[str, Annotation]) -> str:
    """Return formatted entry string with an appended annotation line if present."""
    base = format_entry(entry)
    ann = annotate_entry(entry, annotations)
    if ann:
        return base + "\n" + _note_line(ann)
    return base


def format_annotated_server_section(
    server: str,
    entries: List[CronEntry],
    annotations: Dict[str, Annotation],
) -> str:
    """Format a full server section with annotation lines."""
    lines = [f"=== {server} ({len(entries)} entries) ==="]
    for entry in entries:
        lines.append(format_annotated_entry(entry, annotations))
    return "\n".join(lines)


def format_annotated_report(
    grouped: Dict[str, List[CronEntry]],
    annotations: Dict[str, Annotation],
) -> str:
    """Produce a full multi-server report with annotations embedded."""
    sections = [
        format_annotated_server_section(server, entries, annotations)
        for server, entries in sorted(grouped.items())
    ]
    if not sections:
        return _DIM + "(no entries)" + _RESET
    return "\n\n".join(sections)
