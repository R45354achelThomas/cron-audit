"""Tests for cron_audit.severity_cli."""
from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

import pytest

from cron_audit.conflict_detector import Conflict
from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.pipeline import PipelineResult
from cron_audit.severity_cli import build_severity_parser, main


def _sched() -> CronSchedule:
    return CronSchedule("0", "6", "*", "*", "*")


def _entry(cmd: str = "/bin/job") -> CronEntry:
    return CronEntry(server="host1", user="root", schedule=_sched(), command=cmd)


def _make_conflict(severity: str) -> Conflict:
    e = _entry()
    return Conflict(entry_a=e, entry_b=e, reason="overlap", severity=severity)


def _make_result(conflicts):
    return PipelineResult(entries=[_entry()], conflicts=conflicts)


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        snapshot="fake.json",
        min_severity=None,
        max_severity=None,
        exact=None,
        format="text",
        counts_only=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestBuildSeverityParser:
    def test_parser_registers_severity_command(self):
        root = argparse.ArgumentParser()
        sub = root.add_subparsers()
        p = build_severity_parser(sub)
        assert p is not None

    def test_snapshot_argument_present(self):
        root = argparse.ArgumentParser()
        sub = root.add_subparsers()
        build_severity_parser(sub)
        ns = root.parse_args(["severity", "snap.json"])
        assert ns.snapshot == "snap.json"


class TestSeverityCliMain:
    def _run(self, conflicts, **kwargs):
        result = _make_result(conflicts)
        with patch("cron_audit.severity_cli.load_snapshot", return_value=result):
            return main(_args(**kwargs))

    def test_returns_zero_on_success(self):
        code = self._run([])
        assert code == 0

    def test_returns_one_on_load_error(self):
        with patch("cron_audit.severity_cli.load_snapshot", side_effect=OSError("nope")):
            code = main(_args())
        assert code == 1

    def test_json_output_has_counts_key(self, capsys):
        self._run([_make_conflict("high")], format="json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "counts" in data

    def test_json_counts_only_omits_conflicts_key(self, capsys):
        self._run([_make_conflict("high")], format="json", counts_only=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "conflicts" not in data

    def test_exact_filter_applied(self, capsys):
        conflicts = [_make_conflict("low"), _make_conflict("high")]
        self._run(conflicts, format="json", exact="high")
        data = json.loads(capsys.readouterr().out)
        assert data["counts"]["high"] == 1
        assert data["counts"]["low"] == 0

    def test_text_output_contains_severity(self, capsys):
        self._run([_make_conflict("medium")], format="text")
        out = capsys.readouterr().out
        assert "MEDIUM" in out

    def test_counts_only_text_does_not_list_conflicts(self, capsys):
        self._run([_make_conflict("high")], format="text", counts_only=True)
        out = capsys.readouterr().out
        assert "HIGH" not in out
        assert "counts" in out.lower()
