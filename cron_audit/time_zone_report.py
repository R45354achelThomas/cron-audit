"""Classify cron entries by inferred time zone and report cross-zone conflicts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cron_audit.parser import CronEntry

# Common TZ env-var prefixes or server-name hints
_TZ_HINTS: Dict[str, str] = {
    "utc": "UTC",
    "est": "US/Eastern",
    "cst": "US/Central",
    "mst": "US/Mountain",
    "pst": "US/Pacific",
    "gmt": "GMT",
    "cet": "Europe/Berlin",
    "jst": "Asia/Tokyo",
}


def _infer_tz(entry: CronEntry) -> str:
    """Return a time-zone label inferred from server name or entry metadata."""
    server = (entry.server or "").lower()
    for hint, label in _TZ_HINTS.items():
        if hint in server:
            return label
    return "UTC"  # safe default


@dataclass
class TimeZoneGroup:
    timezone: str
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def server_names(self) -> List[str]:
        return sorted({e.server or "unknown" for e in self.entries})

    def __repr__(self) -> str:  # pragma: no cover
        return f"TimeZoneGroup(tz={self.timezone!r}, entries={len(self.entries)})"


@dataclass
class TimeZoneReport:
    groups: Dict[str, TimeZoneGroup] = field(default_factory=dict)
    mixed_servers: List[str] = field(default_factory=list)

    @property
    def timezones(self) -> List[str]:
        return sorted(self.groups)

    @property
    def has_mixed(self) -> bool:
        return len(self.mixed_servers) > 0

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TimeZoneReport(zones={self.timezones}, "
            f"mixed_servers={self.mixed_servers})"
        )


def build_timezone_report(entries: List[CronEntry]) -> TimeZoneReport:
    """Group entries by inferred time zone and flag servers that span multiple zones."""
    report = TimeZoneReport()
    server_zones: Dict[str, set] = {}

    for entry in entries:
        tz = _infer_tz(entry)
        if tz not in report.groups:
            report.groups[tz] = TimeZoneGroup(timezone=tz)
        report.groups[tz].entries.append(entry)

        server = entry.server or "unknown"
        server_zones.setdefault(server, set()).add(tz)

    report.mixed_servers = sorted(
        srv for srv, zones in server_zones.items() if len(zones) > 1
    )
    return report
