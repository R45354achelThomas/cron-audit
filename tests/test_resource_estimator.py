"""Tests for cron_audit.resource_estimator and cron_audit.formatter_resource."""
from __future__ import annotations

import unittest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.resource_estimator import (
    ResourceEstimate,
    _keyword_weight,
    _runs_per_day,
    estimate_resources,
)
from cron_audit.formatter_resource import format_resource_report


def make_entry(
    command: str = "/usr/bin/true",
    minute: str = "0",
    hour: str = "*",
    server: str = "web1",
) -> CronEntry:
    sched = CronSchedule(minute=minute, hour=hour, dom="*", month="*", dow="*")
    return CronEntry(schedule=sched, command=command, server=server, raw="")


class TestKeywordWeight(unittest.TestCase):
    def test_heavy_keyword_returns_2(self):
        self.assertEqual(_keyword_weight("/usr/bin/pg_dump mydb"), 2.0)

    def test_light_keyword_returns_half(self):
        self.assertEqual(_keyword_weight("echo hello"), 0.5)

    def test_unknown_command_returns_1(self):
        self.assertEqual(_keyword_weight("/opt/app/run_task.sh"), 1.0)

    def test_case_insensitive(self):
        self.assertEqual(_keyword_weight("/usr/bin/RSYNC -av src dst"), 2.0)


class TestRunsPerDay(unittest.TestCase):
    def test_once_per_day_midnight(self):
        entry = make_entry(minute="0", hour="0")
        self.assertEqual(_runs_per_day(entry), 1.0)

    def test_every_hour_once(self):
        entry = make_entry(minute="30", hour="*")
        self.assertEqual(_runs_per_day(entry), 24.0)

    def test_every_minute_every_hour(self):
        entry = make_entry(minute="*", hour="*")
        self.assertEqual(_runs_per_day(entry), 1440.0)

    def test_step_expression(self):
        # */6 in hour → 4 values (0,6,12,18)
        entry = make_entry(minute="0", hour="*/6")
        self.assertEqual(_runs_per_day(entry), 4.0)


class TestEstimateResources(unittest.TestCase):
    def test_returns_list_of_estimates(self):
        entries = [make_entry(), make_entry(command="rsync src dst")]
        result = estimate_resources(entries)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ResourceEstimate)

    def test_sorted_by_score_descending(self):
        low = make_entry(command="echo hi", minute="0", hour="0")
        high = make_entry(command="pg_dump db", minute="*", hour="*")
        result = estimate_resources([low, high])
        self.assertGreater(result[0].score, result[1].score)

    def test_score_equals_rpd_times_weight(self):
        entry = make_entry(command="rsync", minute="0", hour="*/6")
        result = estimate_resources([entry])
        est = result[0]
        self.assertAlmostEqual(est.score, est.runs_per_day * est.keyword_weight)

    def test_empty_list_returns_empty(self):
        self.assertEqual(estimate_resources([]), [])


class TestFormatResourceReport(unittest.TestCase):
    def _estimates(self):
        entries = [
            make_entry(command="/opt/backup.sh", minute="0", hour="2"),
            make_entry(command="rsync -av /data", minute="*", hour="*", server="db1"),
        ]
        from cron_audit.resource_estimator import estimate_resources
        return estimate_resources(entries)

    def test_contains_header(self):
        output = format_resource_report(self._estimates())
        self.assertIn("SERVER", output)
        self.assertIn("SCORE", output)

    def test_contains_server_name(self):
        output = format_resource_report(self._estimates())
        self.assertIn("db1", output)

    def test_top_n_limits_rows(self):
        output = format_resource_report(self._estimates(), top_n=1)
        # header + separator + 1 data row
        data_lines = [l for l in output.splitlines() if "rsync" in l or "/opt/backup" in l]
        self.assertEqual(len(data_lines), 1)

    def test_empty_estimates_returns_message(self):
        output = format_resource_report([])
        self.assertIn("No entries", output)
