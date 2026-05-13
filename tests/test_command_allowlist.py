"""Tests for cron_audit.command_allowlist."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.command_allowlist import (
    AllowlistError,
    AllowlistReport,
    AllowlistViolation,
    check_allowlist,
    load_allowlist,
)


def make_entry(command: str, server: str = "web-01") -> CronEntry:
    sched = CronSchedule(minute="0", hour="3", dom="*", month="*", dow="*")
    return CronEntry(schedule=sched, command=command, server=server, raw="0 3 * * * " + command)


# ---------------------------------------------------------------------------
# load_allowlist
# ---------------------------------------------------------------------------

class TestLoadAllowlist:
    def test_loads_valid_file(self, tmp_path: Path):
        f = tmp_path / "allow.json"
        f.write_text(json.dumps(["/usr/bin/backup", "/opt/scripts/"]))
        result = load_allowlist(f)
        assert result == ["/usr/bin/backup", "/opt/scripts/"]

    def test_strips_whitespace_entries(self, tmp_path: Path):
        f = tmp_path / "allow.json"
        f.write_text(json.dumps(["  /usr/bin/backup  ", "  "]))
        result = load_allowlist(f)
        assert result == ["/usr/bin/backup"]

    def test_raises_if_file_missing(self, tmp_path: Path):
        with pytest.raises(AllowlistError, match="not found"):
            load_allowlist(tmp_path / "missing.json")

    def test_raises_on_invalid_json(self, tmp_path: Path):
        f = tmp_path / "bad.json"
        f.write_text("not json")
        with pytest.raises(AllowlistError, match="Invalid JSON"):
            load_allowlist(f)

    def test_raises_when_not_a_list(self, tmp_path: Path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps({"key": "value"}))
        with pytest.raises(AllowlistError, match="array of strings"):
            load_allowlist(f)

    def test_raises_when_list_contains_non_strings(self, tmp_path: Path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps(["/usr/bin/ok", 42]))
        with pytest.raises(AllowlistError, match="array of strings"):
            load_allowlist(f)


# ---------------------------------------------------------------------------
# check_allowlist
# ---------------------------------------------------------------------------

class TestCheckAllowlist:
    def test_no_violations_when_all_allowed(self):
        entries = [make_entry("/usr/bin/backup --full")]
        report = check_allowlist(entries, ["/usr/bin/backup"])
        assert not report.has_violations
        assert report.violations == []

    def test_violation_when_command_not_in_allowlist(self):
        entries = [make_entry("/usr/local/bin/mystery_script")]
        report = check_allowlist(entries, ["/usr/bin/backup"])
        assert report.has_violations
        assert len(report.violations) == 1
        assert isinstance(report.violations[0], AllowlistViolation)

    def test_violation_reason_contains_command(self):
        cmd = "/usr/local/bin/mystery_script"
        entries = [make_entry(cmd)]
        report = check_allowlist(entries, ["/usr/bin/backup"])
        assert cmd in report.violations[0].reason

    def test_substring_match_is_allowed(self):
        entries = [make_entry("/opt/scripts/daily_cleanup.sh")]
        report = check_allowlist(entries, ["/opt/scripts/"])
        assert not report.has_violations

    def test_server_filter_skips_other_servers(self):
        entries = [
            make_entry("/bad/cmd", server="web-01"),
            make_entry("/bad/cmd", server="db-01"),
        ]
        report = check_allowlist(entries, ["/usr/bin/backup"], server="db-01")
        assert len(report.violations) == 1
        assert report.violations[0].entry.server == "db-01"

    def test_empty_allowlist_flags_all_commands(self):
        entries = [make_entry("/usr/bin/backup"), make_entry("/opt/run.sh")]
        report = check_allowlist(entries, [])
        assert len(report.violations) == 2

    def test_empty_entries_returns_empty_report(self):
        report = check_allowlist([], ["/usr/bin/backup"])
        assert isinstance(report, AllowlistReport)
        assert not report.has_violations
