"""Parse raw crontab text into structured CronEntry objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CronSchedule:
    minute: str
    hour: str
    day: str
    month: str
    weekday: str

    def __str__(self) -> str:
        return f"{self.minute} {self.hour} {self.day} {self.month} {self.weekday}"


@dataclass
class CronEntry:
    schedule: CronSchedule
    command: str
    server: str
    raw: str
    user: Optional[str] = None

    @property
    def schedule_str(self) -> str:
        return str(self.schedule)

    def __str__(self) -> str:
        user_part = f" ({self.user})" if self.user else ""
        return f"[{self.server}]{user_part} {self.schedule_str}  {self.command}"


_COMMENT_OR_BLANK = frozenset(("", "#"))
_SPECIAL_SCHEDULES: dict[str, CronSchedule] = {
    "@yearly":   CronSchedule("0", "0", "1", "1", "*"),
    "@annually": CronSchedule("0", "0", "1", "1", "*"),
    "@monthly":  CronSchedule("0", "0", "1", "*", "*"),
    "@weekly":   CronSchedule("0", "0", "*", "*", "0"),
    "@daily":    CronSchedule("0", "0", "*", "*", "*"),
    "@midnight": CronSchedule("0", "0", "*", "*", "*"),
    "@hourly":   CronSchedule("0", "*", "*", "*", "*"),
}


def _is_system_crontab_line(parts: list[str]) -> bool:
    """Heuristic: system crontabs have a username field before the command."""
    # parts already has 5 schedule fields stripped; parts[0] is either user or command
    # A username won't contain '/' and won't start with common command characters.
    if len(parts) < 2:
        return False
    candidate = parts[0]
    return (
        not candidate.startswith("/")
        and not candidate.startswith("env")
        and not candidate.startswith("nice")
        and "/" not in candidate
        and candidate.isidentifier()
    )


def parse_crontab(text: str, server: str = "unknown", system: bool = False) -> List[CronEntry]:
    """Parse *text* as a crontab file and return a list of :class:`CronEntry`.

    Parameters
    ----------
    text:   Raw crontab content.
    server: Logical server name to attach to each entry.
    system: If True, treat lines as system crontab format (with username field).
    """
    entries: List[CronEntry] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("@reboot"):
            continue
        if line.startswith("@"):
            token, _, command = line.partition(" ")
            schedule = _SPECIAL_SCHEDULES.get(token)
            if schedule and command:
                entries.append(CronEntry(schedule=schedule, command=command.strip(), server=server, raw=raw_line))
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        schedule = CronSchedule(
            minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], weekday=parts[4]
        )
        rest = parts[5:]
        user: Optional[str] = None
        if system or _is_system_crontab_line(rest):
            user = rest[0]
            command = " ".join(rest[1:])
        else:
            command = " ".join(rest)
        entries.append(CronEntry(schedule=schedule, command=command, server=server, raw=raw_line, user=user))
    return entries
