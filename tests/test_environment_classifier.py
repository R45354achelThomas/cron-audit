"""Tests for environment_classifier and formatter_environment."""
from __future__ import annotations

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.environment_classifier import (
    build_environment_report,
    _classify_entry,
    _DEFAULT_RULES,
    EnvironmentGroup,
)
from cron_audit.formatter_environment import format_environment_report


def make_entry(command: str = "/bin/true", server: str = "web-prod-01") -> CronEntry:
    sched = CronSchedule(minute="0", hour="*", dom="*", month="*", dow="*")
    return CronEntry(schedule=sched, command=command, server=server, raw="0 * * * * /bin/true")


# ---------------------------------------------------------------------------
# _classify_entry
# ---------------------------------------------------------------------------

class TestClassifyEntry:
    def test_prod_server_classified_as_production(self):
        entry = make_entry(server="web-prod-01")
        assert _classify_entry(entry, _DEFAULT_RULES) == "production"

    def test_staging_server_classified_as_staging(self):
        entry = make_entry(server="app-staging-02")
        assert _classify_entry(entry, _DEFAULT_RULES) == "staging"

    def test_dev_server_classified_as_development(self):
        entry = make_entry(server="dev-box")
        assert _classify_entry(entry, _DEFAULT_RULES) == "development"

    def test_qa_server_classified_as_testing(self):
        entry = make_entry(server="qa-runner")
        assert _classify_entry(entry, _DEFAULT_RULES) == "testing"

    def test_unknown_server_is_unclassified(self):
        entry = make_entry(server="mystery-host")
        assert _classify_entry(entry, _DEFAULT_RULES) == "unclassified"

    def test_command_pattern_used_when_server_empty(self):
        entry = make_entry(command="/opt/prod/deploy.sh", server="")
        assert _classify_entry(entry, _DEFAULT_RULES) == "production"

    def test_custom_rules_override_defaults(self):
        entry = make_entry(server="canary-host")
        rules = [(r"canary", "canary")]
        assert _classify_entry(entry, rules) == "canary"


# ---------------------------------------------------------------------------
# build_environment_report
# ---------------------------------------------------------------------------

class TestBuildEnvironmentReport:
    def test_empty_entries_returns_empty_report(self):
        report = build_environment_report([])
        assert report.groups == {}

    def test_groups_entries_by_environment(self):
        entries = [
            make_entry(server="prod-01"),
            make_entry(server="prod-02"),
            make_entry(server="staging-01"),
        ]
        report = build_environment_report(entries)
        assert len(report.groups["production"].entries) == 2
        assert len(report.groups["staging"].entries) == 1

    def test_unclassified_group_present_for_unknown(self):
        entry = make_entry(server="random-host")
        report = build_environment_report([entry])
        assert "unclassified" in report.groups

    def test_environments_property_sorted(self):
        entries = [
            make_entry(server="staging-01"),
            make_entry(server="prod-01"),
        ]
        report = build_environment_report(entries)
        envs = report.environments
        assert envs == sorted(envs)

    def test_server_names_on_group(self):
        entries = [
            make_entry(server="prod-01"),
            make_entry(server="prod-02"),
        ]
        report = build_environment_report(entries)
        assert report.groups["production"].server_names == ["prod-01", "prod-02"]


# ---------------------------------------------------------------------------
# format_environment_report
# ---------------------------------------------------------------------------

class TestFormatEnvironmentReport:
    def test_empty_report_returns_no_entries_message(self):
        from cron_audit.environment_classifier import EnvironmentReport
        result = format_environment_report(EnvironmentReport())
        assert "No entries" in result

    def test_section_header_contains_environment_name(self):
        entries = [make_entry(server="prod-01")]
        report = build_environment_report(entries)
        result = format_environment_report(report)
        assert "PRODUCTION" in result

    def test_entry_count_in_header(self):
        entries = [make_entry(server="prod-01"), make_entry(server="prod-02")]
        report = build_environment_report(entries)
        result = format_environment_report(report)
        assert "2 entries" in result

    def test_server_names_listed(self):
        entries = [make_entry(server="prod-01")]
        report = build_environment_report(entries)
        result = format_environment_report(report)
        assert "prod-01" in result

    def test_command_appears_in_output(self):
        entries = [make_entry(command="/usr/bin/backup.sh", server="prod-01")]
        report = build_environment_report(entries)
        result = format_environment_report(report)
        assert "/usr/bin/backup.sh" in result
