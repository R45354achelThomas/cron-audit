"""High-level pipeline: load -> parse -> detect conflicts -> report/export."""

from typing import Optional

from cron_audit.loader import load_from_file, load_from_ssh
from cron_audit.parser import CronEntry, parse_crontab
from cron_audit.conflict_detector import Conflict, detect_conflicts
from cron_audit.reporter import generate_report
from cron_audit.exporter import export_json, export_csv


class PipelineResult:
    """Holds the outcome of a full audit pipeline run."""

    def __init__(self, entries: list[CronEntry], conflicts: list[Conflict], report: str):
        self.entries = entries
        self.conflicts = conflicts
        self.report = report

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"PipelineResult(entries={len(self.entries)}, "
            f"conflicts={len(self.conflicts)})"
        )


def run_from_files(
    filepaths: list[str],
    server_names: Optional[list[str]] = None,
) -> PipelineResult:
    """Run the audit pipeline over a list of local crontab files.

    Args:
        filepaths: Paths to crontab files.
        server_names: Optional list of server labels aligned with filepaths.

    Returns:
        A PipelineResult containing entries, conflicts, and a text report.
    """
    server_names = server_names or [None] * len(filepaths)  # type: ignore[list-item]
    all_entries: list[CronEntry] = []

    for filepath, server in zip(filepaths, server_names):
        server_label, content = load_from_file(filepath, server=server)
        entries = parse_crontab(content, server=server_label)
        all_entries.extend(entries)

    conflicts = detect_conflicts(all_entries)
    report = generate_report(all_entries, conflicts)
    return PipelineResult(entries=all_entries, conflicts=conflicts, report=report)


def run_from_ssh_hosts(
    hosts: list[str],
    user: Optional[str] = None,
    crontab_path: str = "/etc/crontab",
) -> PipelineResult:
    """Run the audit pipeline over remote servers via SSH.

    Args:
        hosts: List of hostnames or IPs.
        user: SSH username to use for all hosts.
        crontab_path: Remote path to the crontab file.

    Returns:
        A PipelineResult containing entries, conflicts, and a text report.
    """
    all_entries: list[CronEntry] = []

    for host in hosts:
        server_label, content = load_from_ssh(host, user=user, crontab_path=crontab_path)
        entries = parse_crontab(content, server=server_label)
        all_entries.extend(entries)

    conflicts = detect_conflicts(all_entries)
    report = generate_report(all_entries, conflicts)
    return PipelineResult(entries=all_entries, conflicts=conflicts, report=report)


def result_to_json(result: PipelineResult) -> str:
    """Serialise a PipelineResult to a JSON string."""
    return export_json(result.entries, result.conflicts)


def result_to_csv(result: PipelineResult) -> str:
    """Serialise a PipelineResult entries to CSV."""
    return export_csv(result.entries, result.conflicts)
