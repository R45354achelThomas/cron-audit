"""Tests for cron_audit.exporter module."""

import csv
import io
import json
import unittest

from cron_audit.parser import CronEntry
from cron_audit.conflict_detector import Conflict
from cron_audit.exporter import export_json, export_csv


def make_entry(server="web-01", user="root", schedule="0 * * * *",
               command="/usr/bin/backup", comment="backup job"):
    return CronEntry(server=server, user=user, schedule=schedule,
                     command=command, comment=comment)


def make_conflict(reason="duplicate command"):
    a = make_entry(server="web-01", command="/usr/bin/sync")
    b = make_entry(server="web-02", command="/usr/bin/sync")
    return Conflict(reason=reason, entry_a=a, entry_b=b)


class TestExportJson(unittest.TestCase):

    def test_returns_valid_json_string(self):
        result = export_json([make_entry()], [])
        data = json.loads(result)  # should not raise
        self.assertIsInstance(data, dict)

    def test_entries_key_present(self):
        data = json.loads(export_json([make_entry()], []))
        self.assertIn("entries", data)
        self.assertEqual(len(data["entries"]), 1)

    def test_conflicts_key_present(self):
        conflict = make_conflict()
        data = json.loads(export_json([], [conflict]))
        self.assertIn("conflicts", data)
        self.assertEqual(len(data["conflicts"]), 1)

    def test_entry_fields_serialized(self):
        entry = make_entry(server="db-01", command="/bin/clean")
        data = json.loads(export_json([entry], []))
        serialized = data["entries"][0]
        self.assertEqual(serialized["server"], "db-01")
        self.assertEqual(serialized["command"], "/bin/clean")

    def test_conflict_reason_serialized(self):
        conflict = make_conflict(reason="schedule overlap")
        data = json.loads(export_json([], [conflict]))
        self.assertEqual(data["conflicts"][0]["reason"], "schedule overlap")

    def test_empty_inputs_produce_empty_lists(self):
        data = json.loads(export_json([], []))
        self.assertEqual(data["entries"], [])
        self.assertEqual(data["conflicts"], [])


class TestExportCsv(unittest.TestCase):

    def _parse_csv(self, text):
        return list(csv.reader(io.StringIO(text)))

    def test_returns_string(self):
        result = export_csv([make_entry()], [])
        self.assertIsInstance(result, str)

    def test_entry_row_present(self):
        result = export_csv([make_entry(server="app-01")], [])
        rows = self._parse_csv(result)
        servers = [r[1] for r in rows if r and r[0] == "entry"]
        self.assertIn("app-01", servers)

    def test_conflict_row_present(self):
        result = export_csv([], [make_conflict()])
        rows = self._parse_csv(result)
        sections = [r[0] for r in rows if r]
        self.assertIn("conflict", sections)

    def test_blank_separator_between_sections(self):
        result = export_csv([make_entry()], [make_conflict()])
        rows = self._parse_csv(result)
        self.assertIn([], rows)

    def test_comment_empty_string_when_none(self):
        entry = make_entry(comment=None)
        result = export_csv([entry], [])
        rows = self._parse_csv(result)
        entry_rows = [r for r in rows if r and r[0] == "entry"]
        self.assertEqual(entry_rows[0][5], "")


if __name__ == "__main__":
    unittest.main()
