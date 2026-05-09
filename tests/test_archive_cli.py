"""Tests for cron_audit.archive_cli."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cron_audit.archive_cli import main
from cron_audit.archiver import ArchiveError
from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.pipeline import PipelineResult


def _make_result() -> PipelineResult:
    sched = CronSchedule("0", "2", "*", "*", "*")
    entry = CronEntry(server="s1", user="root", schedule=sched, command="cmd", raw="0 2 * * * cmd")
    return PipelineResult(entries=[entry], conflicts=[])


class TestArchiveCliSave:
    def test_save_creates_snapshot(self, tmp_path: Path, monkeypatch) -> None:
        crontab = tmp_path / "web1.crontab"
        crontab.write_text("0 2 * * * root backup.sh\n")
        snap_dir = tmp_path / "snaps"
        ret = main(["save", str(crontab), "--dir", str(snap_dir)])
        assert ret == 0
        assert any(snap_dir.glob("snapshot_*.json"))

    def test_save_returns_error_on_bad_dir(self, tmp_path: Path) -> None:
        crontab = tmp_path / "web1.crontab"
        crontab.write_text("0 2 * * * root backup.sh\n")
        with patch("cron_audit.archive_cli.save_snapshot", side_effect=ArchiveError("boom")):
            ret = main(["save", str(crontab), "--dir", "/dev/null/bad"])
        assert ret == 1


class TestArchiveCliList:
    def test_list_empty(self, tmp_path: Path, capsys) -> None:
        ret = main(["list", "--dir", str(tmp_path)])
        assert ret == 0
        out = capsys.readouterr().out
        assert "No snapshots" in out

    def test_list_shows_files(self, tmp_path: Path, capsys) -> None:
        snap = tmp_path / "snapshot_20240101T000000Z.json"
        snap.write_text(json.dumps({"timestamp": "", "entries": [], "conflicts": []}))
        ret = main(["list", "--dir", str(tmp_path)])
        assert ret == 0
        out = capsys.readouterr().out
        assert "snapshot_" in out


class TestArchiveCliShow:
    def test_show_prints_summary(self, tmp_path: Path, capsys) -> None:
        snap = tmp_path / "snapshot_20240101T000000Z.json"
        snap.write_text(
            json.dumps({"timestamp": "2024-01-01T00:00:00Z", "entries": [{}, {}], "conflicts": []})
        )
        ret = main(["show", str(snap)])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Entries" in out
        assert "2" in out

    def test_show_returns_error_on_missing(self, tmp_path: Path) -> None:
        ret = main(["show", str(tmp_path / "missing.json")])
        assert ret == 1
