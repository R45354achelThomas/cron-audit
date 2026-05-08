"""Tests for cron_audit.summarizer."""

import pytest
from unittest.mock import MagicMock

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.conflict_detector import Conflict
from cron_audit.pipeline import PipelineResult
from cron_audit.summarizer import summarize, AuditSummary


def make_entry(command="/bin/job", server="web1", tags=None):
    schedule = CronSchedule(minute="0", hour="1", dom="*", month="*", dow="*")
    entry = CronEntry(schedule=schedule, command=command, server=server, raw="0 1 * * * " + command)
    entry.tags = tags or []
    return entry


def make_conflict(entry_a, entry_b, reason="duplicate command"):
    return Conflict(entry_a=entry_a, entry_b=entry_b, reason=reason)


def _result(entries=None, conflicts=None):
    r = MagicMock(spec=PipelineResult)
    r.entries = entries or []
    r.conflicts = conflicts or []
    return r


class TestSummarize:
    def test_empty_result(self):
        s = summarize(_result())
        assert isinstance(s, AuditSummary)
        assert s.total_entries == 0
        assert s.total_conflicts == 0
        assert s.servers == []

    def test_counts_entries(self):
        entries = [make_entry(server="web1"), make_entry(server="web1"), make_entry(server="db1")]
        s = summarize(_result(entries=entries))
        assert s.total_entries == 3

    def test_entries_per_server(self):
        entries = [make_entry(server="web1"), make_entry(server="web1"), make_entry(server="db1")]
        s = summarize(_result(entries=entries))
        assert s.entries_per_server["web1"] == 2
        assert s.entries_per_server["db1"] == 1

    def test_servers_list_is_sorted(self):
        entries = [make_entry(server="z_server"), make_entry(server="a_server")]
        s = summarize(_result(entries=entries))
        assert s.servers == ["a_server", "z_server"]

    def test_counts_conflicts(self):
        e1 = make_entry(server="web1")
        e2 = make_entry(server="web1", command="/bin/other")
        conflicts = [make_conflict(e1, e2)]
        s = summarize(_result(entries=[e1, e2], conflicts=conflicts))
        assert s.total_conflicts == 1

    def test_high_severity_conflict_counted(self):
        e1 = make_entry()
        e2 = make_entry()
        conflicts = [make_conflict(e1, e2, reason="duplicate command detected")]
        s = summarize(_result(entries=[e1, e2], conflicts=conflicts))
        assert s.high_severity_conflicts == 1
        assert s.low_severity_conflicts == 0

    def test_low_severity_conflict_counted(self):
        e1 = make_entry()
        e2 = make_entry(command="/bin/other")
        conflicts = [make_conflict(e1, e2, reason="schedule overlap")]
        s = summarize(_result(entries=[e1, e2], conflicts=conflicts))
        assert s.low_severity_conflicts == 1
        assert s.high_severity_conflicts == 0

    def test_most_common_commands(self):
        entries = [
            make_entry(command="/bin/a"),
            make_entry(command="/bin/a"),
            make_entry(command="/bin/b"),
        ]
        s = summarize(_result(entries=entries))
        assert s.most_common_commands[0] == ("/bin/a", 2)

    def test_tags_frequency(self):
        entries = [
            make_entry(tags=["backup", "nightly"]),
            make_entry(tags=["backup"]),
        ]
        s = summarize(_result(entries=entries))
        assert s.tags_frequency.get("backup") == 2
        assert s.tags_frequency.get("nightly") == 1

    def test_unknown_server_fallback(self):
        entry = make_entry(server=None)
        s = summarize(_result(entries=[entry]))
        assert "unknown" in s.servers

    def test_repr_contains_key_info(self):
        s = AuditSummary(total_entries=5, total_conflicts=2, servers=["a", "b"], high_severity_conflicts=1)
        r = repr(s)
        assert "servers=2" in r
        assert "entries=5" in r
        assert "conflicts=2" in r
