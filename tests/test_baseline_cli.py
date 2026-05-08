"""Tests for cron_audit.baseline_cli."""

import json
import pytest
from unittest.mock import patch, MagicMock

from cron_audit.baseline_cli import main
from cron_audit.baseline import BaselineError
from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.differ import DiffResult


def make_entry(server="web1", command="/bin/job"):
    sched = CronSchedule(minute="0", hour="1", dom="*", month="*", dow="*")
    return CronEntry(server=server, command=command, user="root",
                     raw_line="", schedule=sched)


def _pipeline_result(entries):
    r = MagicMock()
    r.entries = entries
    return r


class TestBaselineCliSave:
    def test_save_writes_file(self, tmp_path):
        out = str(tmp_path / "bl.json")
        entries = [make_entry()]
        with patch("cron_audit.baseline_cli.run_from_files",
                   return_value=_pipeline_result(entries)):
            rc = main(["save", "--files", "dummy.txt", "--output", out])
        assert rc == 0
        with open(out) as fh:
            data = json.load(fh)
        assert len(data["entries"]) == 1

    def test_save_returns_error_on_bad_path(self):
        entries = [make_entry()]
        with patch("cron_audit.baseline_cli.run_from_files",
                   return_value=_pipeline_result(entries)):
            rc = main(["save", "--files", "dummy.txt",
                       "--output", "/no/such/dir/bl.json"])
        assert rc == 1


class TestBaselineCliCompare:
    def test_compare_no_changes_returns_zero(self, tmp_path):
        bl = str(tmp_path / "bl.json")
        entries = [make_entry()]
        with patch("cron_audit.baseline_cli.run_from_files",
                   return_value=_pipeline_result(entries)):
            main(["save", "--files", "dummy.txt", "--output", bl])

        with patch("cron_audit.baseline_cli.run_from_files",
                   return_value=_pipeline_result(entries)):
            rc = main(["compare", "--files", "dummy.txt",
                       "--baseline", bl, "--no-color"])
        assert rc == 0

    def test_compare_with_changes_returns_two(self, tmp_path):
        bl = str(tmp_path / "bl.json")
        old_entries = [make_entry(command="/bin/old")]
        new_entries = [make_entry(command="/bin/new")]
        with patch("cron_audit.baseline_cli.run_from_files",
                   return_value=_pipeline_result(old_entries)):
            main(["save", "--files", "dummy.txt", "--output", bl])

        with patch("cron_audit.baseline_cli.run_from_files",
                   return_value=_pipeline_result(new_entries)):
            rc = main(["compare", "--files", "dummy.txt",
                       "--baseline", bl, "--no-color"])
        assert rc == 2

    def test_compare_missing_baseline_returns_error(self, tmp_path):
        missing = str(tmp_path / "nope.json")
        entries = [make_entry()]
        with patch("cron_audit.baseline_cli.run_from_files",
                   return_value=_pipeline_result(entries)):
            rc = main(["compare", "--files", "dummy.txt",
                       "--baseline", missing, "--no-color"])
        assert rc == 1
