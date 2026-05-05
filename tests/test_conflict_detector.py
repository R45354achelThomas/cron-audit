"""Tests for the conflict detection module."""

import unittest
from cron_audit.parser import CronEntry, schedule
from cron_audit.conflict_detector import detect_conflicts, Conflict


def make_entry(minute="*", hour="*", dom="*", month="*", dow="*", command="/bin/cmd", user="root"):
    s = schedule(minute=minute, hour=hour, day_of_month=dom, month=month, day_of_week=dow)
    return CronEntry(user=user, schedule=s, command=command)


class TestDetectConflicts(unittest.TestCase):

    def test_no_conflicts_different_hours(self):
        entries = [
            make_entry(hour="1", command="/bin/a"),
            make_entry(hour="2", command="/bin/b"),
        ]
        result = detect_conflicts(entries)
        self.assertEqual(result, [])

    def test_conflict_detected_wildcard_overlap(self):
        entries = [
            make_entry(minute="0", hour="*", command="/bin/a"),
            make_entry(minute="0", hour="*", command="/bin/b"),
        ]
        result = detect_conflicts(entries)
        self.assertEqual(len(result), 1)

    def test_duplicate_command_conflict_reason(self):
        entries = [
            make_entry(command="/bin/backup"),
            make_entry(command="/bin/backup"),
        ]
        result = detect_conflicts(entries)
        self.assertEqual(len(result), 1)
        self.assertIn("duplicate", result[0].reason)

    def test_overlapping_schedule_reason(self):
        entries = [
            make_entry(minute="*/5", command="/bin/a"),
            make_entry(minute="0", command="/bin/b"),
        ]
        result = detect_conflicts(entries)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].reason, "overlapping schedule")

    def test_no_conflicts_empty_list(self):
        self.assertEqual(detect_conflicts([]), [])

    def test_no_conflicts_single_entry(self):
        entries = [make_entry()]
        self.assertEqual(detect_conflicts(entries), [])

    def test_conflict_str_representation(self):
        entries = [
            make_entry(command="/bin/a"),
            make_entry(command="/bin/b"),
        ]
        result = detect_conflicts(entries)
        conflict_str = str(result[0])
        self.assertIn("CONFLICT", conflict_str)
        self.assertIn("/bin/a", conflict_str)
        self.assertIn("/bin/b", conflict_str)

    def test_multiple_conflicts_detected(self):
        entries = [
            make_entry(command="/bin/a"),
            make_entry(command="/bin/b"),
            make_entry(command="/bin/c"),
        ]
        result = detect_conflicts(entries)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
