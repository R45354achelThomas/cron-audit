"""Loads crontab content from local files or remote servers via SSH."""

import subprocess
from pathlib import Path
from typing import Optional


class LoadError(Exception):
    """Raised when a crontab cannot be loaded."""
    pass


def load_from_file(filepath: str, server: Optional[str] = None) -> tuple[str, str]:
    """Load crontab content from a local file.

    Args:
        filepath: Path to the crontab file.
        server: Optional server label to associate with entries.

    Returns:
        A tuple of (server_name, raw_crontab_content).

    Raises:
        LoadError: If the file cannot be read.
    """
    path = Path(filepath)
    if not path.exists():
        raise LoadError(f"File not found: {filepath}")
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LoadError(f"Cannot read file {filepath}: {exc}") from exc

    server_name = server or path.stem
    return server_name, content


def load_from_ssh(host: str, user: Optional[str] = None, crontab_path: str = "/etc/crontab") -> tuple[str, str]:
    """Load crontab content from a remote server over SSH.

    Args:
        host: Hostname or IP of the remote server.
        user: Optional SSH username.
        crontab_path: Path to the crontab file on the remote server.

    Returns:
        A tuple of (host, raw_crontab_content).

    Raises:
        LoadError: If SSH connection or file read fails.
    """
    target = f"{user}@{host}" if user else host
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", target, f"cat {crontab_path}"]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise LoadError(f"SSH connection to {host} timed out") from exc
    except FileNotFoundError as exc:
        raise LoadError("SSH client not found; ensure 'ssh' is installed") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise LoadError(f"SSH command failed for {host}: {stderr}")

    return host, result.stdout
