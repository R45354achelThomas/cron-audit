"""Tests for cron_audit.loader module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cron_audit.loader import LoadError, load_from_file, load_from_ssh


class TestLoadFromFile:
    def test_returns_tuple_of_server_and_content(self, tmp_path):
        cron_file = tmp_path / "webserver.crontab"
        cron_file.write_text("* * * * * root /usr/bin/backup\n")
        server, content = load_from_file(str(cron_file))
        assert server == "webserver"
        assert "/usr/bin/backup" in content

    def test_explicit_server_name_overrides_stem(self, tmp_path):
        cron_file = tmp_path / "host1.crontab"
        cron_file.write_text("0 2 * * * root /usr/bin/cleanup\n")
        server, _ = load_from_file(str(cron_file), server="prod-web-01")
        assert server == "prod-web-01"

    def test_raises_load_error_if_file_missing(self):
        with pytest.raises(LoadError, match="File not found"):
            load_from_file("/nonexistent/path/crontab")

    def test_raises_load_error_on_read_failure(self, tmp_path):
        cron_file = tmp_path / "locked.crontab"
        cron_file.write_text("* * * * * root /bin/true\n")
        cron_file.chmod(0o000)
        try:
            with pytest.raises(LoadError, match="Cannot read file"):
                load_from_file(str(cron_file))
        finally:
            cron_file.chmod(0o644)

    def test_content_is_full_file_text(self, tmp_path):
        lines = "0 1 * * * root /bin/job1\n0 2 * * * root /bin/job2\n"
        cron_file = tmp_path / "multi.crontab"
        cron_file.write_text(lines)
        _, content = load_from_file(str(cron_file))
        assert content == lines


class TestLoadFromSsh:
    def _make_result(self, returncode=0, stdout="", stderr=""):
        result = MagicMock()
        result.returncode = returncode
        result.stdout = stdout
        result.stderr = stderr
        return result

    @patch("cron_audit.loader.subprocess.run")
    def test_returns_host_and_content(self, mock_run):
        mock_run.return_value = self._make_result(stdout="0 5 * * * root /bin/backup\n")
        host, content = load_from_ssh("192.168.1.10")
        assert host == "192.168.1.10"
        assert "/bin/backup" in content

    @patch("cron_audit.loader.subprocess.run")
    def test_includes_user_in_ssh_target(self, mock_run):
        mock_run.return_value = self._make_result(stdout="")
        load_from_ssh("myserver", user="admin")
        args = mock_run.call_args[0][0]
        assert "admin@myserver" in args

    @patch("cron_audit.loader.subprocess.run")
    def test_raises_load_error_on_nonzero_exit(self, mock_run):
        mock_run.return_value = self._make_result(returncode=1, stderr="Permission denied")
        with pytest.raises(LoadError, match="SSH command failed"):
            load_from_ssh("badhost")

    @patch("cron_audit.loader.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=30))
    def test_raises_load_error_on_timeout(self, mock_run):
        with pytest.raises(LoadError, match="timed out"):
            load_from_ssh("slowhost")

    @patch("cron_audit.loader.subprocess.run", side_effect=FileNotFoundError)
    def test_raises_load_error_when_ssh_missing(self, mock_run):
        with pytest.raises(LoadError, match="SSH client not found"):
            load_from_ssh("anyhost")
