"""Tests for cron_audit.notifier."""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from cron_audit.notifier import (
    NotifierConfig,
    NotificationResult,
    _build_subject,
    _build_body,
    send_conflict_alert,
    notifier_config_from_dict,
)
from cron_audit.conflict_detector import Conflict
from cron_audit.parser import CronEntry, CronSchedule


def make_conflict(severity: str = "high", reason: str = "overlap") -> Conflict:
    sched = CronSchedule("0", "2", "*", "*", "*")
    a = CronEntry(server="s1", user="root", schedule=sched, command="/bin/a")
    b = CronEntry(server="s1", user="root", schedule=sched, command="/bin/b")
    return Conflict(entry_a=a, entry_b=b, reason=reason, severity=severity)


class TestBuildSubject:
    def test_includes_count(self):
        conflicts = [make_conflict()]
        assert "1 conflict" in _build_subject(conflicts)

    def test_high_severity_tag(self):
        conflicts = [make_conflict(severity="high")]
        assert "[HIGH:1]" in _build_subject(conflicts)

    def test_no_high_tag_for_low(self):
        conflicts = [make_conflict(severity="low")]
        assert "HIGH" not in _build_subject(conflicts)


class TestBuildBody:
    def test_contains_total(self):
        body = _build_body([make_conflict()])
        assert "Total conflicts: 1" in body

    def test_contains_conflict_str(self):
        c = make_conflict(reason="duplicate schedule")
        body = _build_body([c])
        assert "duplicate schedule" in body


class TestSendConflictAlert:
    def test_no_send_when_no_conflicts(self):
        cfg = NotifierConfig(recipients=["a@b.com"])
        result = send_conflict_alert([], cfg)
        assert result.sent is False

    def test_no_send_when_no_recipients(self):
        cfg = NotifierConfig(recipients=[])
        result = send_conflict_alert([make_conflict()], cfg)
        assert result.sent is False

    def test_successful_send(self):
        cfg = NotifierConfig(recipients=["ops@example.com"])
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = lambda s: s
        mock_smtp.__exit__ = MagicMock(return_value=False)
        with patch("smtplib.SMTP", return_value=mock_smtp):
            result = send_conflict_alert([make_conflict()], cfg)
        assert result.sent is True
        assert result.recipient_count == 1

    def test_smtp_error_returns_failed_result(self):
        cfg = NotifierConfig(recipients=["ops@example.com"])
        with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("conn refused")):
            result = send_conflict_alert([make_conflict()], cfg)
        assert result.sent is False
        assert "conn refused" in (result.error or "")


class TestNotifierConfigFromDict:
    def test_defaults(self):
        cfg = notifier_config_from_dict({"recipients": ["a@b.com"]})
        assert cfg.smtp_host == "localhost"
        assert cfg.smtp_port == 25
        assert cfg.use_tls is False

    def test_custom_values(self):
        cfg = notifier_config_from_dict(
            {"smtp_host": "mail.example.com", "smtp_port": "587", "recipients": ["x@y.com"], "use_tls": True}
        )
        assert cfg.smtp_host == "mail.example.com"
        assert cfg.smtp_port == 587
        assert cfg.use_tls is True
