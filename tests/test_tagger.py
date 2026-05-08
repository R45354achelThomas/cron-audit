"""Tests for cron_audit.tagger."""

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.tagger import TagRule, load_tag_rules, tag_entry, tag_entries


def make_entry(command: str, server: str = "web1") -> CronEntry:
    schedule = CronSchedule(
        minute="0", hour="3", day="*", month="*", weekday="*"
    )
    return CronEntry(server=server, user="root", schedule=schedule, command=command)


class TestTagRule:
    def test_matches_substring(self):
        rule = TagRule(pattern="backup", tags=["backup"])
        assert rule.matches("/usr/local/bin/backup.sh")

    def test_no_match(self):
        rule = TagRule(pattern="backup", tags=["backup"])
        assert not rule.matches("/usr/bin/cleanup.sh")

    def test_regex_pattern(self):
        rule = TagRule(pattern=r"db_(dump|restore)", tags=["database"])
        assert rule.matches("db_dump.sh")
        assert rule.matches("db_restore.sh")
        assert not rule.matches("db_migrate.sh")


class TestLoadTagRules:
    def test_returns_list_of_tag_rules(self):
        data = {"rules": [{"pattern": "backup", "tags": ["backup"]}]}
        rules = load_tag_rules(data)
        assert len(rules) == 1
        assert isinstance(rules[0], TagRule)

    def test_skips_invalid_entries(self):
        data = {"rules": [{"pattern": "", "tags": ["x"]}, {"pattern": "ok", "tags": []}]}
        rules = load_tag_rules(data)
        assert rules == []

    def test_empty_rules_key(self):
        assert load_tag_rules({}) == []
        assert load_tag_rules({"rules": []}) == []


class TestTagEntry:
    def test_single_tag_applied(self):
        entry = make_entry("/scripts/backup.sh")
        rules = [TagRule(pattern="backup", tags=["backup"])]
        assert tag_entry(entry, rules) == ["backup"]

    def test_multiple_rules_can_match(self):
        entry = make_entry("/scripts/db_backup.sh")
        rules = [
            TagRule(pattern="backup", tags=["backup"]),
            TagRule(pattern="db_", tags=["database"]),
        ]
        tags = tag_entry(entry, rules)
        assert "backup" in tags
        assert "database" in tags

    def test_no_duplicate_tags(self):
        entry = make_entry("/scripts/backup_db_backup.sh")
        rules = [
            TagRule(pattern="backup", tags=["backup"]),
            TagRule(pattern="backup", tags=["backup"]),
        ]
        assert tag_entry(entry, rules).count("backup") == 1

    def test_no_match_returns_empty(self):
        entry = make_entry("/scripts/cleanup.sh")
        rules = [TagRule(pattern="backup", tags=["backup"])]
        assert tag_entry(entry, rules) == []


class TestTagEntries:
    def test_returns_dict_keyed_by_entry(self):
        e1 = make_entry("/scripts/backup.sh")
        e2 = make_entry("/scripts/cleanup.sh")
        rules = [TagRule(pattern="backup", tags=["backup"])]
        result = tag_entries([e1, e2], rules)
        assert result[e1] == ["backup"]
        assert result[e2] == []

    def test_empty_entries(self):
        assert tag_entries([], []) == {}
