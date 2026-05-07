"""Tests for cron_audit.notify_config."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cron_audit.notify_config import (
    load_notify_config,
    validate_notify_config,
    NotifyConfigError,
)
from cron_audit.notifier import NotifierConfig


def write_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "notify.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


class TestLoadNotifyConfig:
    def test_loads_valid_config(self, tmp_path):
        p = write_config(tmp_path, {"recipients": ["a@b.com"]})
        cfg = load_notify_config(p)
        assert cfg.recipients == ["a@b.com"]

    def test_raises_if_file_missing(self, tmp_path):
        with pytest.raises(NotifyConfigError, match="not found"):
            load_notify_config(tmp_path / "missing.json")

    def test_raises_on_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json", encoding="utf-8")
        with pytest.raises(NotifyConfigError, match="Invalid JSON"):
            load_notify_config(p)

    def test_raises_if_not_object(self, tmp_path):
        p = tmp_path / "list.json"
        p.write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(NotifyConfigError, match="JSON object"):
            load_notify_config(p)

    def test_raises_if_no_recipients(self, tmp_path):
        p = write_config(tmp_path, {"smtp_host": "localhost"})
        with pytest.raises(NotifyConfigError, match="recipient"):
            load_notify_config(p)

    def test_smtp_port_parsed(self, tmp_path):
        p = write_config(tmp_path, {"recipients": ["x@y.com"], "smtp_port": 587})
        cfg = load_notify_config(p)
        assert cfg.smtp_port == 587


class TestValidateNotifyConfig:
    def test_no_warnings_for_valid_config(self):
        cfg = NotifierConfig(recipients=["a@b.com"])
        assert validate_notify_config(cfg) == []

    def test_warns_on_empty_recipients(self):
        cfg = NotifierConfig(recipients=[])
        warnings = validate_notify_config(cfg)
        assert any("recipient" in w.lower() for w in warnings)

    def test_warns_on_tls_without_credentials(self):
        cfg = NotifierConfig(recipients=["a@b.com"], use_tls=True)
        warnings = validate_notify_config(cfg)
        assert any("credential" in w.lower() for w in warnings)

    def test_no_warning_tls_with_credentials(self):
        cfg = NotifierConfig(
            recipients=["a@b.com"], use_tls=True, username="u", password="p"
        )
        warnings = validate_notify_config(cfg)
        assert not any("credential" in w.lower() for w in warnings)
