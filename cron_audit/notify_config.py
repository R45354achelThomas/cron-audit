"""Load notifier configuration from a JSON or YAML file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from cron_audit.notifier import NotifierConfig, notifier_config_from_dict


class NotifyConfigError(Exception):
    """Raised when the notifier config cannot be loaded or is invalid."""


def load_notify_config(path: Union[str, Path]) -> NotifierConfig:
    """Load a NotifierConfig from a JSON file.

    Args:
        path: Path to a JSON configuration file.

    Returns:
        A populated NotifierConfig instance.

    Raises:
        NotifyConfigError: If the file is missing, unreadable, or malformed.
    """
    p = Path(path)
    if not p.exists():
        raise NotifyConfigError(f"Config file not found: {p}")

    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise NotifyConfigError(f"Cannot read config file: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NotifyConfigError(f"Invalid JSON in config file: {exc}") from exc

    if not isinstance(data, dict):
        raise NotifyConfigError("Config file must contain a JSON object at the top level.")

    if not data.get("recipients"):
        raise NotifyConfigError("Config must specify at least one recipient.")

    return notifier_config_from_dict(data)


def validate_notify_config(config: NotifierConfig) -> list[str]:
    """Return a list of validation warnings for a NotifierConfig."""
    warnings: list[str] = []
    if not config.recipients:
        warnings.append("No recipients configured.")
    if config.smtp_port not in range(1, 65536):
        warnings.append(f"Unusual smtp_port: {config.smtp_port}")
    if config.use_tls and not (config.username and config.password):
        warnings.append("TLS enabled but no credentials provided.")
    return warnings
