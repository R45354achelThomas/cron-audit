"""Cron job parser module.

Parses crontab entries from a string or file and returns structured
representations of each scheduled job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# Matches a standard 5-field cron expression followed by a command.
_CRON_LINE_RE = re.compile(
    r"^\s*"
    r"(?P<minute>[\w*/,\-]+)\s+"
    r"(?P<hour>[\w*/,\-]+)\s+"
    r"(?P<dom>[\w*/,\-]+)\s+"
    r"(?P<month>[\w*/,\-]+)\s+"
    r"(?P<dow>[\w*/,\-]+)\s+"
    r"(?P<command>.+)$"
)


@dataclass
class CronEntry:
    """Represents a single parsed cron job."""

    minute: str
    hour: str
    dom: str          # day-of-month
    month: str
    dow: str          # day-of-week
    command: str
    source: str = ""  # hostname or file path
    line_number: Optional[int] = None

    @property
    def schedule(self) -> str:
        """Return the 5-field schedule expression."""
        return f"{self.minute} {self.hour} {self.dom} {self.month} {self.dow}"

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.source}] {self.schedule}  {self.command}"


def parse_crontab(text: str, source: str = "") -> List[CronEntry]:
    """Parse *text* as a crontab and return a list of :class:`CronEntry` objects.

    Lines that are blank or start with ``#`` are silently ignored.
    Lines that do not match the expected format are also skipped.

    Args:
        text:   Raw crontab content.
        source: Label attached to every parsed entry (e.g. hostname).

    Returns:
        Ordered list of parsed cron entries.
    """
    entries: List[CronEntry] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _CRON_LINE_RE.match(stripped)
        if m is None:
            continue
        entries.append(
            CronEntry(
                minute=m.group("minute"),
                hour=m.group("hour"),
                dom=m.group("dom"),
                month=m.group("month"),
                dow=m.group("dow"),
                command=m.group("command").strip(),
                source=source,
                line_number=lineno,
            )
        )
    return entries
