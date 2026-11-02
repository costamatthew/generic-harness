"""evidence.check: um teste por código; latest pega a maior tentativa."""

from __future__ import annotations

import json

import pytest

from core.cli.gate import run_gate
from core.lib import evidence
from tests.unit.lib import repo as R


def _repo(tmp_path, xml="xunit2-pass.xml", status="verified"):
    R.init(tmp_path)
    R.write_profile(tmp_path, {"test": {"unit": R.cmd(R.emit(R.DATA_GATE / xml), status=status,
                                                       report=".harness/runs/unit.xml", reportFormat="junit")}})
    R.write_tasks(tmp_path, "PAG-1", [("T1", ["test.unit"])])
    return tmp_path


@pytest.fixture
def green(tmp_path):
    root = _repo(tmp_path)
    res, path = run_gate(root, "T1")
    assert res.status == "ok", res.summary
    return root, path


def _rewrite(path, fn):
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_fresh(green):
    root, path = green
    v = evidence.check(root, path)
    assert (v.ok, v.code) == (True, "fresh")
    assert evidence.check(root, path.relative_to(root)).code == "fresh"


def test_not_pass(tmp_path):
    root = _repo(tmp_path, xml="xunit2-fail.xml")
    _, path = run_gate(root, "T1")
    assert evidence.check(root, path).code == "not-pass"


def test_sensor_absent(tmp_path):
    root = _repo(tmp_path, status="planned")
    _, path = run_gate(root, "T1")
    v = evidence.check(root, path)
    assert (v.ok, v.code) == (False, "sensor-absent")


def test_stale_tree(green):
    root, path = green
    (root / "src" / "app.py").write_text("x = 99\n", encoding="utf-8")
    assert evidence.check(root, path).code == "stale-tree"


def test_writes_by_harness_keep_it_fresh(green):
    root, path = green
    (root / ".harness" / "work" / "PAG-1" / "validation.md").write_text("ok", encoding="utf-8")
    (root / ".harness" / "STATE.md").write_text("ok", encoding="utf-8")
    assert evidence.check(root, path).code == "fresh"


def test_stale_profile(green):
    root, path = green
    p = root / ".harness" / "profile.json"
    p.write_text(p.read_text(encoding="utf-8").replace('"name": "t"', '"name": "u"'), encoding="utf-8")
    assert evidence.check(root, path).code == "stale-profile"


def test_log_tampered(green):
    root, path = green
    log = root / json.loads(path.read_text(encoding="utf-8"))["checks"][0]["log"]["path"]
    log.write_text("tudo verde", encoding="utf-8")
    assert evidence.check(root, path).code == "log-tampered"


def test_report_tampered(green):
    root, path = green
    rep = root / json.loads(path.read_text(encoding="utf-8"))["checks"][0]["report"]["path"]
    rep.write_text("<testsuite/>", encoding="utf-8")
    assert evidence.check(root, path).code == "report-tampered"


def test_invalid_manifest(green):
    root, path = green
    _rewrite(path, lambda d: d.pop("inputs"))
    assert evidence.check(root, path).code == "invalid-manifest"
    path.write_text("{", encoding="utf-8")
    assert evidence.check(root, path).code == "invalid-manifest"
    assert evidence.check(root, root / "nao-existe.json").code == "invalid-manifest"


def test_forged_result_is_not_fresh_when_tree_differs(green):
    root, path = green
    _rewrite(path, lambda d: d["inputs"].update(tree="0" * 64))
    assert evidence.check(root, path).code == "stale-tree"


def test_codes_cover_spec():
    assert set(evidence.CODES) == {"fresh", "not-pass", "sensor-absent", "stale-tree", "stale-profile",
                                   "log-tampered", "report-tampered", "invalid-manifest"}


def test_latest_and_attempts(tmp_path):
    root = _repo(tmp_path)
    assert evidence.latest(root, "T1") is None
    _, p1 = run_gate(root, "T1")
    _, p2 = run_gate(root, "PAG-1.T1")
    assert evidence.latest(root, "T1") == p2
    assert evidence.latest(root, "PAG-1.T1") == p2
    assert evidence.latest(root, "OPS-1.T1") is None
    m1, m2 = (json.loads(p.read_text(encoding="utf-8")) for p in (p1, p2))
    assert (m1["attempt"], m2["attempt"]) == (1, 2)
    assert m2["supersedes"] == m1["runId"] and "supersedes" not in m1
