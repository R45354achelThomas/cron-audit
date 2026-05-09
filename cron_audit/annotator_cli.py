"""CLI sub-commands for managing cron-entry annotations."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cron_audit.annotator import AnnotationError, load_annotations, save_annotations, upsert_annotation, Annotation
from cron_audit.pipeline import run_from_files


def build_annotator_parser(parent: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = parent.add_parser("annotate", help="Manage cron-entry annotations")
    sub = p.add_subparsers(dest="ann_cmd", required=True)

    # annotate add
    add_p = sub.add_parser("add", help="Add or update a note for an entry")
    add_p.add_argument("--crontab", required=True, help="Crontab file to identify the entry")
    add_p.add_argument("--command", required=True, help="Command string to match")
    add_p.add_argument("--note", required=True, help="Free-text note")
    add_p.add_argument("--tags", nargs="*", default=[], metavar="TAG")
    add_p.add_argument("--annotations-file", default="annotations.json", dest="ann_file")

    # annotate list
    list_p = sub.add_parser("list", help="List all annotations")
    list_p.add_argument("--annotations-file", default="annotations.json", dest="ann_file")


def _cmd_add(args: argparse.Namespace) -> int:
    ann_path = Path(args.ann_file)
    try:
        annotations = load_annotations(ann_path)
    except AnnotationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = run_from_files([Path(args.crontab)])
    matches = [e for e in result.entries if args.command in e.command]
    if not matches:
        print(f"error: no entry matching command {args.command!r}", file=sys.stderr)
        return 1

    entry = matches[0]
    ann = upsert_annotation(entry, args.note, args.tags, annotations)
    try:
        save_annotations(annotations, ann_path)
    except AnnotationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved annotation for {ann.key!r}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    ann_path = Path(args.ann_file)
    try:
        annotations = load_annotations(ann_path)
    except AnnotationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not annotations:
        print("No annotations found.")
        return 0

    for ann in annotations.values():
        tags_str = ", ".join(ann.tags) if ann.tags else "—"
        print(f"  [{ann.key}]  tags={tags_str}")
        print(f"    {ann.note}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cron-annotate")
    sub = parser.add_subparsers(dest="ann_cmd", required=True)
    build_annotator_parser(sub)  # type: ignore[arg-type]
    args = parser.parse_args(argv)
    if args.ann_cmd == "add":
        return _cmd_add(args)
    return _cmd_list(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
