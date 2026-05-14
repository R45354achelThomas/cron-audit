"""Tests for cron_audit.owner_map."""

import json
import pytest
from pathlib import Path

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.owner_map import (
    OwnerMapError,
    OwnerRule,
    assign_owners,
    load_owner_rules,
)


def make_entry(command: str = "/bin/job", server: str = "web1") -> CronEntry:
    sched = CronSchedule(minute="0", hour="1", dom="*", month="*", dow="*")
    return CronEntry(schedule=sched, command=command, server=server)


# ---------------------------------------------------------------------------
# OwnerRule.matches
# ---------------------------------------------------------------------------

class TestOwnerRuleMatches:
    def test_matches_by_command_substring(self):
        rule = OwnerRule(owner="team-a", command_contains=["backup"])
        entry = make_entry(command="/usr/local/bin/backup.sh")
        assert rule.matches(entry)

    def test_no_match_different_keyword(self):
        rule = OwnerRule(owner="team-a", command_contains=["etl"])
        entry = make_entry(command="/usr/local/bin/backup.sh")
        assert not rule.matches(entry)

    def test_matches_by_server(self):
        rule = OwnerRule(owner="team-b", servers=["db1"])
        entry = make_entry(server="db1")
        assert rule.matches(entry)

    def test_no_match_different_server(self):
        rule = OwnerRule(owner="team-b", servers=["db1"])
        entry = make_entry(server="web1")
        assert not rule.matches(entry)

    def test_empty_rule_matches_everything(self):
        rule = OwnerRule(owner="catch-all")
        entry = make_entry()
        assert rule.matches(entry)

    def test_server_and_command_both_required(self):
        rule = OwnerRule(owner="team-c", servers=["prod"], command_contains=["sync"])
        assert rule.matches(make_entry(command="sync_data", server="prod"))
        assert not rule.matches(make_entry(command="sync_data", server="staging"))
        assert not rule.matches(make_entry(command="backup", server="prod"))


# ---------------------------------------------------------------------------
# load_owner_rules
# ---------------------------------------------------------------------------

class TestLoadOwnerRules:
    def test_loads_valid_file(self, tmp_path: Path):
        cfg = [{"owner": "team-x", "command_contains": ["deploy"]}]
        p = tmp_path / "owners.json"
        p.write_text(json.dumps(cfg))
        rules = load_owner_rules(p)
        assert len(rules) == 1
        assert rules[0].owner == "team-x"

    def test_raises_if_file_missing(self, tmp_path: Path):
        with pytest.raises(OwnerMapError, match="not found"):
            load_owner_rules(tmp_path / "missing.json")

    def test_raises_on_invalid_json(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid")
        with pytest.raises(OwnerMapError, match="Invalid JSON"):
            load_owner_rules(p)

    def test_raises_if_not_array(self, tmp_path: Path):
        p = tmp_path / "obj.json"
        p.write_text(json.dumps({"owner": "x"}))
        with pytest.raises(OwnerMapError, match="array"):
            load_owner_rules(p)

    def test_raises_if_rule_missing_owner(self, tmp_path: Path):
        p = tmp_path / "norule.json"
        p.write_text(json.dumps([{"command_contains": ["foo"]}]))
        with pytest.raises(OwnerMapError, match="'owner'"):
            load_owner_rules(p)


# ---------------------------------------------------------------------------
# assign_owners
# ---------------------------------------------------------------------------

class TestAssignOwners:
    def test_entry_assigned_to_matching_owner(self):
        rules = [OwnerRule(owner="ops", command_contains=["backup"])]
        entries = [make_entry(command="/bin/backup.sh")]
        report = assign_owners(entries, rules)
        assert "ops" in report.owned
        assert len(report.unowned) == 0

    def test_unmatched_entry_goes_to_unowned(self):
        rules = [OwnerRule(owner="ops", command_contains=["deploy"])]
        entries = [make_entry(command="/bin/backup.sh")]
        report = assign_owners(entries, rules)
        assert len(report.unowned) == 1
        assert report.owned == {}

    def test_first_matching_rule_wins(self):
        rules = [
            OwnerRule(owner="first", command_contains=["job"]),
            OwnerRule(owner="second", command_contains=["job"]),
        ]
        report = assign_owners([make_entry(command="run_job")], rules)
        assert "first" in report.owned
        assert "second" not in report.owned

    def test_all_owners_returns_sorted_list(self):
        rules = [
            OwnerRule(owner="zebra", command_contains=["z"]),
            OwnerRule(owner="alpha", command_contains=["a"]),
        ]
        entries = [make_entry(command="z_task"), make_entry(command="a_task")]
        report = assign_owners(entries, rules)
        assert report.all_owners() == ["alpha", "zebra"]
