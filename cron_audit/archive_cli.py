"""CLI sub-commands for managing cron-audit snapshots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cron_audit.archiver import ArchiveError, list_snapshots, load_snapshot, save_snapshot
from cron_audit.pipeline import run_from_files


def build_archive_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:  # noqa: SLF001
    desc = "Save and inspect cron-audit snapshots."
    if parent is not None:
        parser = parent.add_parser("archive", help=desc)
    else:
        parser = argparse.ArgumentParser(prog="cron-archive", description=desc)

    sub = parser.add_subparsers(dest="archive_cmd", required=True)

    # save
    p_save = sub.add_parser("save", help="Save a new snapshot from crontab files.")
    p_save.add_argument("files", nargs="+", metavar="FILE", help="Crontab files to parse.")
    p_save.add_argument("--dir", default="./snapshots", metavar="DIR", help="Snapshot directory.")
    p_save.add_argument("--prefix", default="snapshot", help="Filename prefix.")

    # list
    p_list = sub.add_parser("list", help="List saved snapshots.")
    p_list.add_argument("--dir", default="./snapshots", metavar="DIR")
    p_list.add_argument("--prefix", default="snapshot")

    # show
    p_show = sub.add_parser("show", help="Print summary of a snapshot.")
    p_show.add_argument("snapshot", help="Path to snapshot file.")

    return parser


def _cmd_save(args: argparse.Namespace) -> int:
    result = run_from_files(args.files)
    try:
        dest = save_snapshot(result, args.dir, prefix=args.prefix)
        print(f"Snapshot saved: {dest}")
        return 0
    except ArchiveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_list(args: argparse.Namespace) -> int:
    snapshots = list_snapshots(args.dir, prefix=args.prefix)
    if not snapshots:
        print("No snapshots found.")
        return 0
    for p in snapshots:
        print(p)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    try:
        data = load_snapshot(args.snapshot)
    except ArchiveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Timestamp : {data.get('timestamp', 'unknown')}")
    print(f"Entries   : {len(data.get('entries', []))}")
    print(f"Conflicts : {len(data.get('conflicts', []))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_archive_parser()
    args = parser.parse_args(argv)
    dispatch = {"save": _cmd_save, "list": _cmd_list, "show": _cmd_show}
    return dispatch[args.archive_cmd](args)


if __name__ == "__main__":
    sys.exit(main())
