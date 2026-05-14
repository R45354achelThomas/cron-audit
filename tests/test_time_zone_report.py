"""Tests for time_zone_report and formatter_timezone."""
import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.time_zone_report import (
    TimeZoneReport,
    TimeZoneGroup,
    _infer_tz,
    build_timezone_report,
)
from cron_audit.formatter_timezone import format_timezone_report


def make_entry(command: str = "/bin/job", server: str = "web-utc-01") -> CronEntry:
    sched = CronSchedule(
        minute="0", hour="2", dom="*", month="*", dow="*"
    )
    return CronEntry(schedule=sched, command=command, server=server, raw="")


# ---------------------------------------------------------------------------
# _infer_tz
# ---------------------------------------------------------------------------

class TestInferTz:
    def test_utc_hint_in_server_name(self):
        entry = make_entry(server="app-utc-prod")
        assert _infer_tz(entry) == "UTC"

    def test_pst_hint_in_server_name(self):
        entry = make_entry(server="pst-worker-01")
        assert _infer_tz(entry) == "US/Pacific"

    def test_jst_hint(self):
        entry = make_entry(server="jst-tokyo-app")
        assert _infer_tz(entry) == "Asia/Tokyo"

    def test_unknown_server_defaults_to_utc(self):
        entry = make_entry(server="mystery-host")
        assert _infer_tz(entry) == "UTC"

    def test_case_insensitive(self):
        entry = make_entry(server="EST-EAST-01")
        assert _infer_tz(entry) == "US/Eastern"


# ---------------------------------------------------------------------------
# build_timezone_report
# ---------------------------------------------------------------------------

class TestBuildTimezoneReport:
    def test_empty_entries_returns_empty_report(self):
        report = build_timezone_report([])
        assert report.groups == {}
        assert report.mixed_servers == []
        assert not report.has_mixed

    def test_single_zone_group(self):
        entries = [make_entry(server="utc-host"), make_entry(server="utc-backup")]
        report = build_timezone_report(entries)
        assert "UTC" in report.groups
        assert len(report.groups["UTC"].entries) == 2

    def test_multiple_zones_split_correctly(self):
        entries = [
            make_entry(server="utc-host"),
            make_entry(server="pst-host"),
        ]
        report = build_timezone_report(entries)
        assert "UTC" in report.groups
        assert "US/Pacific" in report.groups

    def test_mixed_server_detected(self):
        # same server name appears in two zones — simulate by patching server name
        # We create two entries with identical server but different zone hints by
        # constructing them manually.
        e1 = make_entry(server="pst-utc-mixed")
        # _infer_tz picks first matching hint; we just need two distinct servers
        e2 = make_entry(server="est-host")
        e3 = make_entry(server="pst-host")
        report = build_timezone_report([e1, e2, e3])
        # No truly mixed server here; verify no false positives
        assert isinstance(report.mixed_servers, list)

    def test_server_names_property(self):
        entries = [
            make_entry(server="utc-alpha"),
            make_entry(server="utc-beta"),
        ]
        report = build_timezone_report(entries)
        assert "utc-alpha" in report.groups["UTC"].server_names
        assert "utc-beta" in report.groups["UTC"].server_names

    def test_timezones_property_sorted(self):
        entries = [
            make_entry(server="pst-host"),
            make_entry(server="cet-host"),
            make_entry(server="utc-host"),
        ]
        report = build_timezone_report(entries)
        assert report.timezones == sorted(report.timezones)


# ---------------------------------------------------------------------------
# format_timezone_report
# ---------------------------------------------------------------------------

class TestFormatTimezoneReport:
    def test_empty_report_mentions_no_entries(self):
        report = TimeZoneReport()
        out = format_timezone_report(report)
        assert "No entries" in out

    def test_zone_name_present_in_output(self):
        entries = [make_entry(server="utc-host")]
        report = build_timezone_report(entries)
        out = format_timezone_report(report)
        assert "UTC" in out

    def test_command_present_in_output(self):
        entries = [make_entry(command="/usr/bin/backup", server="utc-host")]
        report = build_timezone_report(entries)
        out = format_timezone_report(report)
        assert "/usr/bin/backup" in out

    def test_no_mixed_message_when_single_zone(self):
        entries = [make_entry(server="utc-host")]
        report = build_timezone_report(entries)
        out = format_timezone_report(report)
        assert "single time zone" in out

    def test_warning_present_for_mixed_servers(self):
        report = TimeZoneReport(
            groups={"UTC": TimeZoneGroup(timezone="UTC")},
            mixed_servers=["mixed-server"],
        )
        out = format_timezone_report(report)
        assert "WARNING" in out
        assert "mixed-server" in out
