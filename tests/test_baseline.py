"""Tests for cron_audit.baseline."""

import json
import os
import pytest

from cron_audit.baseline import save_baseline, load_baseline, BaselineError
from cron_audit.parser import CronEntry, CronSchedule


def make_entry(server="web1", command="/usr/bin/backup", user="root",
               minute="0", hour="2", dom="*", month="*", dow="*"):
    schedule = CronSchedule(minute=minute, hour=hour, dom=dom,
                            month=month, dow=dow)
    return CronEntry(server=server, command=command, user=user,
                     raw_line="", schedule=schedule)


class TestSaveBaseline:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "baseline.json")
        save_baseline([make_entry()], path)
        assert os.path.exists(path)

    def test_file_is_valid_json(self, tmp_path):
        path = str(tmp_path / "baseline.json")
        save_baseline([make_entry()], path)
        with open(path) as fh:
            data = json.load(fh)
        assert "entries" in data
        assert data["version"] == 1

    def test_entry_fields_preserved(self, tmp_path):
        path = str(tmp_path / "baseline.json")
        entry = make_entry(server="db1", command="/opt/clean", hour="3")
        save_baseline([entry], path)
        with open(path) as fh:
            data = json.load(fh)
        saved = data["entries"][0]
        assert saved["server"] == "db1"
        assert saved["command"] == "/opt/clean"
        assert saved["schedule"]["hour"] == "3"

    def test_raises_on_bad_path(self):
        with pytest.raises(BaselineError):
            save_baseline([make_entry()], "/no/such/dir/baseline.json")


class TestLoadBaseline:
    def test_returns_list_of_entries(self, tmp_path):
        path = str(tmp_path / "baseline.json")
        save_baseline([make_entry(), make_entry(server="db1")], path)
        entries = load_baseline(path)
        assert len(entries) == 2

    def test_entry_type_correct(self, tmp_path):
        path = str(tmp_path / "baseline.json")
        save_baseline([make_entry()], path)
        entries = load_baseline(path)
        assert isinstance(entries[0], CronEntry)

    def test_schedule_restored(self, tmp_path):
        path = str(tmp_path / "baseline.json")
        save_baseline([make_entry(minute="15", hour="4")], path)
        entry = load_baseline(path)[0]
        assert entry.schedule.minute == "15"
        assert entry.schedule.hour == "4"

    def test_raises_if_missing(self, tmp_path):
        with pytest.raises(BaselineError, match="not found"):
            load_baseline(str(tmp_path / "missing.json"))

    def test_raises_on_corrupt_json(self, tmp_path):
        path = str(tmp_path / "bad.json")
        with open(path, "w") as fh:
            fh.write("NOT JSON")
        with pytest.raises(BaselineError):
            load_baseline(path)

    def test_empty_entries_returns_empty_list(self, tmp_path):
        path = str(tmp_path / "empty.json")
        with open(path, "w") as fh:
            json.dump({"version": 1, "entries": []}, fh)
        assert load_baseline(path) == []
