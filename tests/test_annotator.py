"""Tests for cron_audit.annotator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cron_audit.annotator import (
    Annotation,
    AnnotationError,
    _entry_key,
    annotate_entry,
    load_annotations,
    save_annotations,
    upsert_annotation,
)
from cron_audit.parser import CronEntry, CronSchedule


def make_entry(command: str = "/usr/bin/backup", server: str = "web01") -> CronEntry:
    sched = CronSchedule(minute="0", hour="3", dom="*", month="*", dow="*")
    return CronEntry(schedule=sched, command=command, server=server, raw="0 3 * * * " + command)


class TestLoadAnnotations:
    def test_returns_empty_dict_when_file_missing(self, tmp_path: Path) -> None:
        result = load_annotations(tmp_path / "missing.json")
        assert result == {}

    def test_loads_valid_file(self, tmp_path: Path) -> None:
        f = tmp_path / "ann.json"
        f.write_text(json.dumps([{"key": "web01::/usr/bin/backup", "note": "nightly", "tags": ["db"]}]))
        result = load_annotations(f)
        assert "web01::/usr/bin/backup" in result
        assert result["web01::/usr/bin/backup"].note == "nightly"

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("not json")
        with pytest.raises(AnnotationError):
            load_annotations(f)

    def test_tags_default_to_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "ann.json"
        f.write_text(json.dumps([{"key": "srv::cmd", "note": "hi"}]))
        result = load_annotations(f)
        assert result["srv::cmd"].tags == []


class TestSaveAnnotations:
    def test_creates_file(self, tmp_path: Path) -> None:
        ann = {"k": Annotation(key="k", note="test", tags=[])}
        path = tmp_path / "out.json"
        save_annotations(ann, path)
        assert path.exists()

    def test_file_is_valid_json(self, tmp_path: Path) -> None:
        ann = {"k": Annotation(key="k", note="hello", tags=["x"])}
        path = tmp_path / "out.json"
        save_annotations(ann, path)
        data = json.loads(path.read_text())
        assert data[0]["note"] == "hello"

    def test_raises_on_bad_path(self) -> None:
        ann = {"k": Annotation(key="k", note="n", tags=[])}
        with pytest.raises(AnnotationError):
            save_annotations(ann, Path("/no/such/dir/file.json"))


class TestAnnotateEntry:
    def test_returns_annotation_when_present(self) -> None:
        entry = make_entry()
        annotations = {_entry_key(entry): Annotation(key=_entry_key(entry), note="ok", tags=[])}
        result = annotate_entry(entry, annotations)
        assert result is not None
        assert result.note == "ok"

    def test_returns_none_when_absent(self) -> None:
        entry = make_entry()
        assert annotate_entry(entry, {}) is None

    def test_unknown_server_fallback(self) -> None:
        sched = CronSchedule(minute="0", hour="1", dom="*", month="*", dow="*")
        entry = CronEntry(schedule=sched, command="/bin/foo", server=None, raw="0 1 * * * /bin/foo")
        key = _entry_key(entry)
        assert key == "unknown::/bin/foo"


class TestUpsertAnnotation:
    def test_inserts_new(self) -> None:
        entry = make_entry()
        store: dict = {}
        ann = upsert_annotation(entry, "new note", ["tag1"], store)
        assert ann.note == "new note"
        assert len(store) == 1

    def test_updates_existing(self) -> None:
        entry = make_entry()
        store: dict = {}
        upsert_annotation(entry, "old", [], store)
        upsert_annotation(entry, "new", ["t"], store)
        assert len(store) == 1
        assert store[_entry_key(entry)].note == "new"
