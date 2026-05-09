"""Tests for cron_audit.annotator_cli."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cron_audit.annotator_cli import main
from cron_audit.parser import CronEntry, CronSchedule


def _make_entry(command: str = "/usr/bin/backup", server: str = "web01") -> CronEntry:
    sched = CronSchedule(minute="0", hour="3", dom="*", month="*", dow="*")
    return CronEntry(schedule=sched, command=command, server=server, raw="0 3 * * * " + command)


class TestAnnotatorCliAdd:
    def _pipeline_result(self, entries):
        r = MagicMock()
        r.entries = entries
        r.conflicts = []
        return r

    def test_add_saves_annotation(self, tmp_path: Path) -> None:
        ann_file = tmp_path / "ann.json"
        crontab = tmp_path / "web01.crontab"
        crontab.write_text("0 3 * * * /usr/bin/backup\n")
        entry = _make_entry()
        result = self._pipeline_result([entry])

        with patch("cron_audit.annotator_cli.run_from_files", return_value=result):
            rc = main(["add", "--crontab", str(crontab),
                       "--command", "/usr/bin/backup",
                       "--note", "nightly backup",
                       "--annotations-file", str(ann_file)])

        assert rc == 0
        data = json.loads(ann_file.read_text())
        assert any(d["note"] == "nightly backup" for d in data)

    def test_add_returns_error_when_no_match(self, tmp_path: Path) -> None:
        ann_file = tmp_path / "ann.json"
        crontab = tmp_path / "web01.crontab"
        crontab.write_text("0 3 * * * /usr/bin/backup\n")
        result = self._pipeline_result([])

        with patch("cron_audit.annotator_cli.run_from_files", return_value=result):
            rc = main(["add", "--crontab", str(crontab),
                       "--command", "/nonexistent",
                       "--note", "x",
                       "--annotations-file", str(ann_file)])

        assert rc == 1

    def test_add_with_tags(self, tmp_path: Path) -> None:
        ann_file = tmp_path / "ann.json"
        crontab = tmp_path / "web01.crontab"
        crontab.write_text("0 3 * * * /usr/bin/backup\n")
        entry = _make_entry()
        result = self._pipeline_result([entry])

        with patch("cron_audit.annotator_cli.run_from_files", return_value=result):
            rc = main(["add", "--crontab", str(crontab),
                       "--command", "/usr/bin/backup",
                       "--note", "tagged",
                       "--tags", "db", "critical",
                       "--annotations-file", str(ann_file)])

        assert rc == 0
        data = json.loads(ann_file.read_text())
        assert data[0]["tags"] == ["db", "critical"]


class TestAnnotatorCliList:
    def test_list_empty(self, tmp_path: Path, capsys) -> None:
        ann_file = tmp_path / "ann.json"
        rc = main(["list", "--annotations-file", str(ann_file)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No annotations" in out

    def test_list_shows_entries(self, tmp_path: Path, capsys) -> None:
        ann_file = tmp_path / "ann.json"
        ann_file.write_text(json.dumps([{"key": "web01::/usr/bin/backup",
                                          "note": "nightly", "tags": ["db"]}]))
        rc = main(["list", "--annotations-file", str(ann_file)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "nightly" in out
        assert "web01" in out
