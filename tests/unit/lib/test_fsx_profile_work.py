"""fsx (escrita atômica, lock), profile e work."""

from __future__ import annotations

import json
import os
import time

import pytest

from core.lib import fsx, profile, schema, work
from tests.unit.lib import repo as R

EXAMPLES = schema.SCHEMAS_DIR / "examples"


def test_write_atomic_leaves_no_temp(tmp_path):
    target = tmp_path / "d" / "f.json"
    fsx.write_atomic(target, "a\r\nb")
    fsx.write_atomic(target, "ção")
    assert target.read_bytes() == "ção".encode()
    assert os.listdir(target.parent) == ["f.json"]


def test_lock_exclusive_and_stale(tmp_path):
    p = tmp_path / "x.lock"
    with fsx.Lock(p, stale_after=60):
        with pytest.raises(fsx.LockHeld):
            fsx.Lock(p, stale_after=60).acquire()
    assert not p.exists()
    p.write_text("velho")
    old = time.time() - 120
    os.utime(p, (old, old))
    lock = fsx.Lock(p, stale_after=60).acquire()
    assert lock.warning and "órfão" in lock.warning
    lock.release()


def test_profile_load_and_resolve(tmp_path):
    (tmp_path / ".harness").mkdir()
    src = EXAMPLES / "profile" / "valid-brownfield-python.json"
    (tmp_path / ".harness" / "profile.json").write_bytes(src.read_bytes())
    doc = profile.load(tmp_path)
    assert profile.resolve_command(doc, "test.unit")["status"] == "verified"
    assert profile.resolve_command(doc, "lint")["status"] == "confirmed"
    assert profile.resolve_command(doc, "test") is None
    assert profile.resolve_command(doc, "test.e2e") is None
    assert profile.resolve_command(doc, "lint.x") is None
    assert profile.sha256(tmp_path) == fsx.sha256_file(src)


def test_profile_invalid_raises_value_error(tmp_path):
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "profile.json").write_bytes(
        (EXAMPLES / "profile" / "invalid-command-without-origin.json").read_bytes())
    with pytest.raises(ValueError, match="origin"):
        profile.load(tmp_path)


def test_find_task_plain_qualified_ambiguous(tmp_path):
    R.write_tasks(tmp_path, "PAG-1", [("T1", ["lint"]), ("T2", ["lint"])])
    R.write_tasks(tmp_path, "OPS-2", [("T1", ["lint"])])
    assert work.find_task(tmp_path, "T2").qualified_id == "PAG-1.T2"
    assert work.find_task(tmp_path, "OPS-2.T1").work_id == "OPS-2"
    with pytest.raises(LookupError, match="OPS-2.T1, PAG-1.T1"):
        work.find_task(tmp_path, "T1")
    with pytest.raises(LookupError):
        work.find_task(tmp_path, "T9")
    with pytest.raises(LookupError):
        work.find_task(tmp_path, "XYZ-9.T1")
    with pytest.raises(ValueError):
        work.find_task(tmp_path, "t1")


def test_find_task_accepts_qualified_ids_in_file(tmp_path):
    R.write_tasks(tmp_path, "PAG-1", [("PAG-1.T3", ["lint"])])
    assert work.find_task(tmp_path, "T3").task["id"] == "PAG-1.T3"


def test_find_task_invalid_tasks_json(tmp_path):
    p = tmp_path / ".harness" / "work" / "PAG-1" / "tasks.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"schema": 0, "workId": "PAG-1", "tasks": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        work.find_task(tmp_path, "T1")
