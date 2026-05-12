"""Builds a dependency graph of cron entries based on shared resources.

Entries are linked when they share the same command binary or write to the
same output path (detected via simple heuristic pattern matching).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from cron_audit.parser import CronEntry

_REDIRECT_RE = re.compile(r'>>?\s*(\S+)')
_BINARY_RE = re.compile(r'(?:^|[|;&&]\s*)([/\w][\w./\-]+)')


def _extract_binary(command: str) -> str | None:
    m = _BINARY_RE.search(command.strip())
    return m.group(1).split('/')[-1] if m else None


def _extract_output_paths(command: str) -> Set[str]:
    return set(_REDIRECT_RE.findall(command))


def _entry_label(entry: CronEntry) -> str:
    return f"{entry.server}::{entry.command}"


@dataclass
class DependencyGraph:
    """Directed adjacency list of cron entries sharing resources."""
    nodes: List[str] = field(default_factory=list)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)  # (from, to, reason)

    def neighbours(self, label: str) -> List[Tuple[str, str]]:
        """Return [(neighbour_label, reason), ...] for a given node."""
        return [(t, r) for (f, t, r) in self.edges if f == label]

    def __repr__(self) -> str:  # pragma: no cover
        return f"DependencyGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"


def build_dependency_graph(entries: List[CronEntry]) -> DependencyGraph:
    """Analyse *entries* and return a DependencyGraph.

    Two entries are linked when they:
    - share the same top-level binary name, **or**
    - redirect output to the same file path.
    """
    labels = [_entry_label(e) for e in entries]
    binaries: Dict[str, List[str]] = {}
    outputs: Dict[str, List[str]] = {}

    for entry, label in zip(entries, labels):
        binary = _extract_binary(entry.command)
        if binary:
            binaries.setdefault(binary, []).append(label)
        for path in _extract_output_paths(entry.command):
            outputs.setdefault(path, []).append(label)

    edges: List[Tuple[str, str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    def _add_edge(a: str, b: str, reason: str) -> None:
        if a != b and (a, b) not in seen:
            seen.add((a, b))
            seen.add((b, a))
            edges.append((a, b, reason))
            edges.append((b, a, reason))

    for binary, lbls in binaries.items():
        for i, a in enumerate(lbls):
            for b in lbls[i + 1:]:
                _add_edge(a, b, f"shared binary: {binary}")

    for path, lbls in outputs.items():
        for i, a in enumerate(lbls):
            for b in lbls[i + 1:]:
                _add_edge(a, b, f"shared output: {path}")

    return DependencyGraph(nodes=list(set(labels)), edges=edges)
