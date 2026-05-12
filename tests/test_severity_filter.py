"""Tests for cron_audit.severity_filter."""
from __future__ import annotations

import pytest

from cron_audit.conflict_detector import Conflict
from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.severity_filter import (
    SeverityFilterCriteria,
    filter_conflicts,
    severity_counts,
)


def _sched() -> CronSchedule:
    from cron_audit.parser import CronSchedule
    return CronSchedule("0", "*", "*", "*", "*")


def make_conflict(severity: str, reason: str = "overlap") -> Conflict:
    e = CronEntry(server="srv", user="root", schedule=_sched(), command="/bin/cmd")
    return Conflict(entry_a=e, entry_b=e, reason=reason, severity=severity)


class TestSeverityFilterCriteria:
    def test_is_empty_by_default(self):
        c = SeverityFilterCriteria()
        assert c.is_empty()

    def test_not_empty_with_min(self):
        c = SeverityFilterCriteria(min_severity="low")
        assert not c.is_empty()

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            SeverityFilterCriteria(min_severity="critical")

    def test_exact_matches_only_that_level(self):
        c = SeverityFilterCriteria(exact="medium")
        assert c.matches("medium")
        assert not c.matches("low")
        assert not c.matches("high")

    def test_min_severity_filters_lower(self):
        c = SeverityFilterCriteria(min_severity="medium")
        assert not c.matches("low")
        assert c.matches("medium")
        assert c.matches("high")

    def test_max_severity_filters_higher(self):
        c = SeverityFilterCriteria(max_severity="medium")
        assert c.matches("low")
        assert c.matches("medium")
        assert not c.matches("high")

    def test_range_inclusive(self):
        c = SeverityFilterCriteria(min_severity="low", max_severity="medium")
        assert c.matches("low")
        assert c.matches("medium")
        assert not c.matches("high")

    def test_empty_criteria_matches_all(self):
        c = SeverityFilterCriteria()
        for s in ("low", "medium", "high"):
            assert c.matches(s)


class TestFilterConflicts:
    def test_empty_criteria_returns_all(self):
        conflicts = [make_conflict("low"), make_conflict("high")]
        result = filter_conflicts(conflicts, SeverityFilterCriteria())
        assert len(result) == 2

    def test_filters_by_exact_severity(self):
        conflicts = [make_conflict("low"), make_conflict("high"), make_conflict("high")]
        result = filter_conflicts(conflicts, SeverityFilterCriteria(exact="high"))
        assert len(result) == 2
        assert all(c.severity == "high" for c in result)

    def test_filters_by_min_severity(self):
        conflicts = [make_conflict("low"), make_conflict("medium"), make_conflict("high")]
        result = filter_conflicts(conflicts, SeverityFilterCriteria(min_severity="medium"))
        assert len(result) == 2

    def test_empty_list_returns_empty(self):
        result = filter_conflicts([], SeverityFilterCriteria(exact="high"))
        assert result == []


class TestSeverityCounts:
    def test_counts_all_levels(self):
        conflicts = [
            make_conflict("low"),
            make_conflict("medium"),
            make_conflict("medium"),
            make_conflict("high"),
        ]
        counts = severity_counts(conflicts)
        assert counts["low"] == 1
        assert counts["medium"] == 2
        assert counts["high"] == 1

    def test_empty_input_all_zeros(self):
        counts = severity_counts([])
        assert counts == {"low": 0, "medium": 0, "high": 0}

    def test_unknown_severity_not_counted(self):
        c = make_conflict("critical")
        counts = severity_counts([c])
        assert sum(counts.values()) == 0
