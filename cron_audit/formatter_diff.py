"""Format DiffResult objects for human-readable output."""

from cron_audit.differ import DiffResult
from cron_audit.formatter import format_entry

_RESET = "\033[0m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_DIM = "\033[2m"


def _green(text: str, color: bool) -> str:
    return f"{_GREEN}{text}{_RESET}" if color else text


def _red(text: str, color: bool) -> str:
    return f"{_RED}{text}{_RESET}" if color else text


def _dim(text: str, color: bool) -> str:
    return f"{_DIM}{text}{_RESET}" if color else text


def format_diff(
    result: DiffResult,
    label_before: str = "before",
    label_after: str = "after",
    color: bool = False,
) -> str:
    """Return a human-readable diff report string."""
    lines: list[str] = []
    lines.append(f"Diff: {label_before} → {label_after}")
    lines.append(f"Summary: {result.summary()}")
    lines.append("")

    if result.added:
        lines.append(f"Added ({len(result.added)}):")
        for entry in result.added:
            lines.append(_green(f"  + {format_entry(entry)}", color))
        lines.append("")

    if result.removed:
        lines.append(f"Removed ({len(result.removed)}):")
        for entry in result.removed:
            lines.append(_red(f"  - {format_entry(entry)}", color))
        lines.append("")

    if result.unchanged:
        lines.append(f"Unchanged ({len(result.unchanged)}):")
        for entry in result.unchanged:
            lines.append(_dim(f"    {format_entry(entry)}", color))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
