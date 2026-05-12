"""Tests for cron_audit.dependency_graph and cron_audit.formatter_graph."""
from __future__ import annotations

import pytest

from cron_audit.parser import CronEntry, CronSchedule
from cron_audit.dependency_graph import (
    build_dependency_graph,
    _extract_binary,
    _extract_output_paths,
)
from cron_audit.formatter_graph import format_graph, format_node_detail


def make_entry(command: str, server: str = "host1") -> CronEntry:
    sched = CronSchedule(minute="0", hour="1", dom="*", month="*", dow="*")
    return CronEntry(server=server, schedule=sched, command=command, raw="")


# ---------------------------------------------------------------------------
# _extract_binary
# ---------------------------------------------------------------------------

class TestExtractBinary:
    def test_simple_command(self):
        assert _extract_binary("/usr/bin/python script.py") == "python"

    def test_relative_command(self):
        assert _extract_binary("backup.sh --all") == "backup.sh"

    def test_empty_string_returns_none(self):
        assert _extract_binary("") is None


# ---------------------------------------------------------------------------
# _extract_output_paths
# ---------------------------------------------------------------------------

class TestExtractOutputPaths:
    def test_single_redirect(self):
        assert _extract_output_paths("cmd >> /var/log/out.log") == {"/var/log/out.log"}

    def test_no_redirect(self):
        assert _extract_output_paths("cmd --flag") == set()

    def test_multiple_redirects(self):
        paths = _extract_output_paths("cmd > /tmp/a.log && other >> /tmp/b.log")
        assert "/tmp/a.log" in paths
        assert "/tmp/b.log" in paths


# ---------------------------------------------------------------------------
# build_dependency_graph
# ---------------------------------------------------------------------------

class TestBuildDependencyGraph:
    def test_empty_entries_produces_empty_graph(self):
        g = build_dependency_graph([])
        assert g.nodes == []
        assert g.edges == []

    def test_no_shared_resources_no_edges(self):
        entries = [
            make_entry("/usr/bin/alpha", "s1"),
            make_entry("/usr/bin/beta", "s2"),
        ]
        g = build_dependency_graph(entries)
        assert g.edges == []

    def test_shared_binary_creates_edge(self):
        entries = [
            make_entry("/usr/bin/rsync src/ dest/", "s1"),
            make_entry("/usr/bin/rsync backup/ archive/", "s2"),
        ]
        g = build_dependency_graph(entries)
        assert len(g.edges) == 2  # bidirectional
        reasons = {r for _, _, r in g.edges}
        assert any("rsync" in r for r in reasons)

    def test_shared_output_file_creates_edge(self):
        entries = [
            make_entry("cmd1 >> /var/log/shared.log", "s1"),
            make_entry("cmd2 >> /var/log/shared.log", "s2"),
        ]
        g = build_dependency_graph(entries)
        assert len(g.edges) == 2
        assert any("shared.log" in r for _, _, r in g.edges)

    def test_neighbours_returns_correct_pairs(self):
        entries = [
            make_entry("/usr/bin/python job.py", "s1"),
            make_entry("/usr/bin/python other.py", "s2"),
        ]
        g = build_dependency_graph(entries)
        label = "s1::/usr/bin/python job.py"
        neighbours = g.neighbours(label)
        assert len(neighbours) == 1
        assert "python" in neighbours[0][1]


# ---------------------------------------------------------------------------
# formatter_graph
# ---------------------------------------------------------------------------

class TestFormatGraph:
    def test_empty_graph_message(self):
        from cron_audit.dependency_graph import DependencyGraph
        out = format_graph(DependencyGraph())
        assert "no entries" in out

    def test_contains_node_count(self):
        entries = [
            make_entry("/usr/bin/rsync a", "s1"),
            make_entry("/usr/bin/rsync b", "s2"),
        ]
        g = build_dependency_graph(entries)
        out = format_graph(g)
        assert "Nodes" in out

    def test_format_node_detail_no_deps(self):
        from cron_audit.dependency_graph import DependencyGraph
        g = DependencyGraph(nodes=["s1::cmd"], edges=[])
        out = format_node_detail("s1::cmd", g)
        assert "no dependencies" in out

    def test_format_node_detail_with_dep(self):
        entries = [
            make_entry("/usr/bin/python a.py", "s1"),
            make_entry("/usr/bin/python b.py", "s2"),
        ]
        g = build_dependency_graph(entries)
        label = "s1::/usr/bin/python a.py"
        out = format_node_detail(label, g)
        assert "python" in out
