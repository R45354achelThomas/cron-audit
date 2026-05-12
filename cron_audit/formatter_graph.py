"""Text formatter for DependencyGraph output."""
from __future__ import annotations

from cron_audit.dependency_graph import DependencyGraph


def _header(text: str) -> str:
    return f"\n{'=' * 60}\n{text}\n{'=' * 60}"


def format_graph(graph: DependencyGraph) -> str:
    """Return a human-readable representation of *graph*."""
    if not graph.nodes:
        return "Dependency graph: no entries."

    lines: list[str] = [_header("Cron Dependency Graph")]
    lines.append(f"Nodes : {len(graph.nodes)}")
    lines.append(f"Edges : {len(graph.edges) // 2} (undirected)\n")

    if not graph.edges:
        lines.append("No shared resources detected — entries are independent.")
        return "\n".join(lines)

    lines.append("Connections (undirected):")
    seen: set[tuple[str, str]] = set()
    for frm, to, reason in sorted(graph.edges, key=lambda e: (e[0], e[1])):
        pair = tuple(sorted([frm, to]))
        if pair in seen:
            continue
        seen.add(pair)  # type: ignore[arg-type]
        lines.append(f"  {frm}")
        lines.append(f"    <-> {to}")
        lines.append(f"        reason: {reason}")

    return "\n".join(lines)


def format_node_detail(node: str, graph: DependencyGraph) -> str:
    """Return detail lines for a single *node* in *graph*."""
    neighbours = graph.neighbours(node)
    if not neighbours:
        return f"{node}: no dependencies"
    lines = [f"{node} depends on / shares resources with:"]
    for neighbour, reason in sorted(neighbours):
        lines.append(f"  - {neighbour}  [{reason}]")
    return "\n".join(lines)
