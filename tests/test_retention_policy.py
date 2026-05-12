"""Tests for cron_audit.retention_policy."""

from __future__ import annotations

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.retention_policy import (
    PolicyRule,
    PolicyViolation,
    _estimate_interval_minutes,
    evaluate_policy,
)


def make_entry(
    command: str = "/usr/bin/backup",
    minute: str = "0",
    hour: str = "2",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
    server: str = "web01",
) -> CronEntry:
    schedule = CronSchedule(minute=minute, hour=hour, dom=dom, month=month, dow=dow)
    return CronEntry(schedule=schedule, command=command, server=server)


class TestPolicyRule:
    def test_valid_rule_creates_successfully(self):
        rule = PolicyRule("daily", "backup", 1380, 1500)
        assert rule.name == "daily"

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="Unknown severity"):
            PolicyRule("x", "cmd", 60, 120, severity="critical")

    def test_max_less_than_min_raises(self):
        with pytest.raises(ValueError, match="max_interval_minutes"):
            PolicyRule("x", "cmd", 120, 60)

    def test_negative_min_raises(self):
        with pytest.raises(ValueError, match="min_interval_minutes"):
            PolicyRule("x", "cmd", -1, 60)

    def test_matches_substring(self):
        rule = PolicyRule("r", "backup", 60, 120)
        assert rule.matches(make_entry(command="/usr/bin/backup.sh"))

    def test_no_match(self):
        rule = PolicyRule("r", "restore", 60, 120)
        assert not rule.matches(make_entry(command="/usr/bin/backup.sh"))

    def test_case_insensitive_match(self):
        rule = PolicyRule("r", "BACKUP", 60, 120)
        assert rule.matches(make_entry(command="/usr/bin/backup.sh"))


class TestEstimateInterval:
    def test_wildcard_minute_and_hour_returns_one(self):
        entry = make_entry(minute="*", hour="*")
        assert _estimate_interval_minutes(entry) == 1

    def test_fixed_minute_wildcard_hour_returns_60(self):
        entry = make_entry(minute="30", hour="*")
        assert _estimate_interval_minutes(entry) == 60

    def test_fixed_hour_and_minute_returns_1440(self):
        entry = make_entry(minute="0", hour="3")
        assert _estimate_interval_minutes(entry) == 1440

    def test_dom_set_returns_weekly(self):
        entry = make_entry(minute="0", hour="2", dom="1")
        assert _estimate_interval_minutes(entry) == 10080


class TestEvaluatePolicy:
    def _rule(self, min_m: int, max_m: int, pattern: str = "backup") -> PolicyRule:
        return PolicyRule("test-rule", pattern, min_m, max_m, severity="high")

    def test_no_violations_when_within_range(self):
        entry = make_entry(command="/usr/bin/backup", minute="0", hour="2")
        rule = self._rule(1000, 2000)
        assert evaluate_policy([entry], [rule]) == []

    def test_violation_when_too_frequent(self):
        entry = make_entry(command="/usr/bin/backup", minute="*", hour="*")
        rule = self._rule(60, 1440)
        violations = evaluate_policy([entry], [rule])
        assert len(violations) == 1
        assert isinstance(violations[0], PolicyViolation)
        assert "at least" in violations[0].message

    def test_violation_when_too_infrequent(self):
        entry = make_entry(command="/usr/bin/backup", minute="0", hour="2")
        rule = self._rule(1, 60)
        violations = evaluate_policy([entry], [rule])
        assert len(violations) == 1
        assert "at most" in violations[0].message

    def test_non_matching_rule_skipped(self):
        entry = make_entry(command="/usr/bin/cleanup")
        rule = self._rule(1, 60, pattern="backup")
        assert evaluate_policy([entry], [rule]) == []

    def test_multiple_entries_multiple_violations(self):
        entries = [
            make_entry(command="/usr/bin/backup", minute="*", hour="*"),
            make_entry(command="/usr/bin/backup", minute="*", hour="*", server="db01"),
        ]
        rule = self._rule(60, 1440)
        violations = evaluate_policy(entries, rule if isinstance(rule, list) else [rule])
        assert len(violations) == 2
