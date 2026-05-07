"""Notification dispatch for cron-audit conflict alerts."""

from __future__ import annotations

import smtplib
import json
from email.mime.text import MIMEText
from dataclasses import dataclass, field
from typing import List, Optional

from cron_audit.conflict_detector import Conflict


@dataclass
class NotifierConfig:
    smtp_host: str = "localhost"
    smtp_port: int = 25
    sender: str = "cron-audit@localhost"
    recipients: List[str] = field(default_factory=list)
    use_tls: bool = False
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class NotificationResult:
    sent: bool
    recipient_count: int
    error: Optional[str] = None

    def __repr__(self) -> str:
        status = "sent" if self.sent else f"failed({self.error})"
        return f"NotificationResult({status}, recipients={self.recipient_count})"


def _build_subject(conflicts: List[Conflict]) -> str:
    count = len(conflicts)
    severity_high = sum(1 for c in conflicts if c.severity == "high")
    tag = f"[HIGH:{severity_high}] " if severity_high else ""
    return f"{tag}cron-audit: {count} conflict(s) detected"


def _build_body(conflicts: List[Conflict]) -> str:
    lines = ["cron-audit conflict report", "=" * 40, ""]
    for c in conflicts:
        lines.append(str(c))
        lines.append("")
    lines.append(f"Total conflicts: {len(conflicts)}")
    return "\n".join(lines)


def send_conflict_alert(
    conflicts: List[Conflict],
    config: NotifierConfig,
) -> NotificationResult:
    """Send an email alert summarising detected conflicts."""
    if not conflicts or not config.recipients:
        return NotificationResult(sent=False, recipient_count=0, error="nothing to send")

    body = _build_body(conflicts)
    msg = MIMEText(body)
    msg["Subject"] = _build_subject(conflicts)
    msg["From"] = config.sender
    msg["To"] = ", ".join(config.recipients)

    try:
        cls = smtplib.SMTP_SSL if config.use_tls else smtplib.SMTP
        with cls(config.smtp_host, config.smtp_port) as smtp:
            if config.username and config.password:
                smtp.login(config.username, config.password)
            smtp.sendmail(config.sender, config.recipients, msg.as_string())
        return NotificationResult(sent=True, recipient_count=len(config.recipients))
    except Exception as exc:  # noqa: BLE001
        return NotificationResult(sent=False, recipient_count=0, error=str(exc))


def notifier_config_from_dict(data: dict) -> NotifierConfig:
    """Build a NotifierConfig from a plain dict (e.g. parsed from YAML/JSON)."""
    return NotifierConfig(
        smtp_host=data.get("smtp_host", "localhost"),
        smtp_port=int(data.get("smtp_port", 25)),
        sender=data.get("sender", "cron-audit@localhost"),
        recipients=list(data.get("recipients", [])),
        use_tls=bool(data.get("use_tls", False)),
        username=data.get("username"),
        password=data.get("password"),
    )
