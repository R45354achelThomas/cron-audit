"""Tests for cron_audit.archiver."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cron_audit.archiver import (
    ArchiveError,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)
from cron_audit.conflict_detector import Conflict
from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.pipeline import PipelineResult


def _schedule() -> CronSchedule:
    return CronSchedule("0", "3", "*", "*", "*")


def make_entry(cmd: str = "backup.sh", server: str = "web1") -> CronEntry:
    return CronEntry(
        server=server,
        user="root",
        schedule=_schedule(),
        command=cmd,
        raw="0 3 * * * " + cmd,
    )


def make_result(n_entries: int = 2, n_conflicts: int = 0) -> PipelineResult:
    entries = [make_entry(f"cmd{i}") for i in range(n_entries)]
    conflicts: list[Conflict] = []
    if n_conflicts:
        conflicts.append(
            Conflict(
                entries=[entries[0], entries[1]] if len(entries) >= 2 else entries,
                reason="duplicate",
                severity="high",
            )
        )
    return PipelineResult(entries=entries, conflicts=conflicts)


_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestSaveSnapshot:
    def test_creates_file(self, tmp_path: Path) -> None:
        result = make_result()
        dest = save_snapshot(result, tmp_path, now=_TS)
        assert dest.exists()

    def test_filename_contains_timestamp(self, tmp_path: Path) -> None:
        result = make_result()
        dest = save_snapshot(result, tmp_path, now=_TS)
        assert "20240601T120000Z" in dest.name

    def test_custom_prefix(self, tmp_path: Path) -> None:
        result = make_result()
        dest = save_snapshot(result, tmp_path, prefix="audit", now=_TS)
        assert dest.name.startswith("audit_")

    def test_file_is_valid_json(self, tmp_path: Path) -> None:
        result = make_result()
        dest = save_snapshot(result, tmp_path, now=_TS)
        data = json.loads(dest.read_text())
        assert "entries" in data
        assert "conflicts" in data
        assert "timestamp" in data

    def test_entry_count_matches(self, tmp_path: Path) -> None:
        result = make_result(n_entries=3)
        dest = save_snapshot(result, tmp_path, now=_TS)
        data = json.loads(dest.read_text())
        assert len(data["entries"]) == 3

    def test_raises_on_bad_directory(self) -> None:
        result = make_result()
        with pytest.raises(ArchiveError):
            save_snapshot(result, "/dev/null/impossible", now=_TS)


class TestListSnapshots:
    def test_empty_directory(self, tmp_path: Path) -> None:
        assert list_snapshots(tmp_path) == []

    def test_returns_sorted_list(self, tmp_path: Path) -> None:
        result = make_result()
        ts1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        p1 = save_snapshot(result, tmp_path, now=ts1)
        p2 = save_snapshot(result, tmp_path, now=ts2)
        snaps = list_snapshots(tmp_path)
        assert snaps == [p1, p2]

    def test_nonexistent_directory_returns_empty(self, tmp_path: Path) -> None:
        assert list_snapshots(tmp_path / "missing") == []


class TestLoadSnapshot:
    def test_loads_data(self, tmp_path: Path) -> None:
        result = make_result(n_entries=1)
        dest = save_snapshot(result, tmp_path, now=_TS)
        data = load_snapshot(dest)
        assert isinstance(data, dict)
        assert len(data["entries"]) == 1

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ArchiveError):
            load_snapshot(tmp_path / "nope.json")

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        with pytest.raises(ArchiveError):
            load_snapshot(bad)
