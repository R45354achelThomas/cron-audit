"""Prune old snapshot files, keeping the N most recent."""

from __future__ import annotations

from pathlib import Path
from typing import List

from cron_audit.archiver import ArchiveError, list_snapshots


class PruneResult:
    """Outcome of a prune operation."""

    def __init__(self, kept: List[Path], removed: List[Path]) -> None:
        self.kept = kept
        self.removed = removed

    def __repr__(self) -> str:  # pragma: no cover
        return f"PruneResult(kept={len(self.kept)}, removed={len(self.removed)})"


def prune_snapshots(
    directory: str | Path,
    keep: int,
    prefix: str = "snapshot",
    dry_run: bool = False,
) -> PruneResult:
    """Delete all but the *keep* most recent snapshots in *directory*.

    When *dry_run* is True, files are identified but not deleted.
    Raises :class:`ArchiveError` if *keep* is less than 1.
    """
    if keep < 1:
        raise ArchiveError(f"'keep' must be >= 1, got {keep}")

    snapshots = list_snapshots(directory, prefix=prefix)
    # list_snapshots returns oldest-first; keep the tail
    to_remove = snapshots[: max(0, len(snapshots) - keep)]
    to_keep = snapshots[max(0, len(snapshots) - keep) :]

    for path in to_remove:
        if not dry_run:
            try:
                path.unlink()
            except OSError as exc:
                raise ArchiveError(f"Failed to remove '{path}': {exc}") from exc

    return PruneResult(kept=to_keep, removed=to_remove)
