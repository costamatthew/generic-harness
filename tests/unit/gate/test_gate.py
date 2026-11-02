"""`harness gate` (trilha 1A): critério binário da spec docs/plan/etapa-1/1A.md."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from core.cli.gate import run_gate
from core.cli.harness import EXIT, envelope, render_text
from core.lib import schema
from tests.unit.lib import repo as R

ROOT = Path(__file__).resolve().parents[3]
D = R.DATA_GATE
FIRST_LINE = re.compile(r"^GATE \S+ \S+  (PASS|FAIL|ABSENT) exit=(-|-?\d+)  \d+\.\d+s  tree=[0-9a-f]{7}$")


def setup(root: Path, commands: dict, dod: list[str], limits: dict | None = None) -> Path:
    R.init(root)
    R.write_profile(root, commands, limits)
    R.write_tasks(root, "PAG-1", [("T1", dod)])
    return root


def gate(root: Path, task="T1"):
    res, path = run_gate(root, task)
    env = envelope(res, "gate")
    assert schema.validate(env, "cli-output") == [], env
    manifest = None
    if path is not None:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert schema.validate(manifest, "run-manifest") == []
        assert res.data["manifest"] == path.relative_to(root).as_posix()
        assert set(res.data) == {"manifest", "runId", "result", "tree"}
    return res, manifest


def cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "bootstrap.py"), *args], cwd=root,
                          capture_output=True, text=True, encoding="utf-8")


def test_pass(tmp_path):
    root = setup(tmp_path, {"test": R.unit(D / "xunit2-pass.xml")}, ["test.unit"])
    res, m = gate(root)
    assert (res.status, res.exit, m["result"]) == ("ok", 0, "pass")
    c = m["checks"][0]
    assert c["report"]["mtimeAfterStart"] is True and c["report"]["tests"] == 1
    # o relatório registrado é a cópia, não o caminho do perfil
    assert c["report"]["path"] == f".harness/runs/{m['runId']}/test.unit.junit.xml"
    assert c["log"]["path"] == f".harness/runs/{m['runId']}/test.unit.log"
    assert "emit" in (root / c["log"]["path"]).read_text(encoding="utf-8")
    assert m["taskId"] == "PAG-1.T1" and m["workId"] == "PAG-1" and m["attempt"] == 1
    assert m["inputs"]["revision"] and m["inputs"]["dirty"] is True  # profile/tasks não comitados
    assert FIRST_LINE.match(res.summary[0]), res.summary[0]


@pytest.mark.parametrize("xml,loc", [("xunit1-fail.xml", "tests/test_calc.py:7"),
                                     ("xunit2-fail.xml", "tests/test_calc.py:8")])
def test_exit0_with_failure_is_fail(tmp_path, xml, loc):
    root = setup(tmp_path, {"test": R.unit(D / xml)}, ["test.unit"])
    res, m = gate(root)
    assert res.exit == 1 and m["result"] == "fail"
    c = m["checks"][0]
    assert c["exitCode"] == 0 and c["status"] == "fail"
    assert c["report"]["firstFailures"][0]["location"] == loc
    assert re.fullmatch(r"[^:]+:\d+", c["report"]["firstFailures"][0]["location"])
    assert any(loc in s for s in res.summary)


def test_exit0_without_report_is_fail(tmp_path):
    root = setup(tmp_path, {"test": R.unit("-")}, ["test.unit"])
    res, m = gate(root)
    assert res.exit == 1 and m["result"] == "fail"
    assert "report" not in m["checks"][0]
    assert "relatório" in res.next


def test_exit0_with_old_report_is_fail(tmp_path):
    root = setup(tmp_path, {"test": R.unit("-")}, ["test.unit"])
    old = root / ".harness" / "runs" / "unit.xml"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes((D / "xunit2-pass.xml").read_bytes())
    t = time.time() - 3600
    os.utime(old, (t, t))
    res, m = gate(root)
    assert res.exit == 1 and m["result"] == "fail"
    assert m["checks"][0]["report"]["mtimeAfterStart"] is False


def test_nonzero_exit_is_fail(tmp_path):
    root = setup(tmp_path, {"lint": R.cmd(R.emit("-", code=2))}, ["lint"])
    res, m = gate(root)
    assert res.exit == 1 and m["checks"][0]["exitCode"] == 2
    assert res.summary[0].startswith("GATE T1 lint  FAIL exit=2")


def test_malformed_report_is_fail(tmp_path):
    root = setup(tmp_path, {"test": R.unit(R.DATA_LIB / "malformed.xml")}, ["test.unit"])
    res, m = gate(root)
    assert res.exit == 1 and any("ilegível" in s for s in res.summary)


@pytest.mark.parametrize("entry,reason", [
    ({"status": "planned", "origin": "decision:ADR-0007"}, "planned"),
    ({"status": "confirmed"}, "not-approved"),
    ({"status": "detected"}, "not-approved"),
    (None, "not-in-profile"),
])
def test_absent_sensor_runs_nothing(tmp_path, entry, reason):
    touch = f"{R.q(R.PY)} touch.py ran.txt"
    commands = {"lint": R.cmd(touch)}
    if entry is not None:
        commands["typecheck"] = R.cmd(touch, **entry)
    root = setup(tmp_path, commands, ["lint", "typecheck"])
    res, m = gate(root)
    assert res.exit == 3 == EXIT["sensor-absent"] and m["result"] == "sensor-absent"
    assert not (root / "ran.txt").exists()
    by_name = {c["name"]: c for c in m["checks"]}
    assert by_name["lint"]["status"] == "skipped"
    assert by_name["typecheck"]["absent"]["reason"] == reason
    if reason == "planned":
        assert by_name["typecheck"]["absent"]["decidedBy"] == "ADR-0007"
    assert "Não improvise" in res.next
    assert res.summary[0] == f"GATE T1 typecheck  ABSENT exit=-  0.0s  tree={m['inputs']['tree'][:7]}"


def test_tool_missing_is_sensor_absent(tmp_path):
    root = setup(tmp_path, {"lint": R.cmd("comando-que-nao-existe-xyz --version")}, ["lint"])
    res, m = gate(root)
    assert res.exit == 3 and m["result"] == "sensor-absent"
    c = m["checks"][0]
    assert c["status"] == "unavailable" and c["absent"]["reason"] == "tool-missing"


def test_timeout_is_fail_with_null_exit(tmp_path):
    root = setup(tmp_path, {"lint": R.cmd(f"{R.q(R.PY)} touch.py out.txt 30", timeoutSec=1)}, ["lint"])
    (root / ".gitignore").write_text("out.txt\nignorado/\n", encoding="utf-8")
    t0 = time.monotonic()
    res, m = gate(root)
    assert time.monotonic() - t0 < 20
    c = m["checks"][0]
    assert c["status"] == "fail" and c["exitCode"] is None
    assert "timeout 1s  (lint)" in res.summary
    assert res.summary[0].startswith("GATE T1 lint  FAIL exit=-")


def test_tree_changed_during_gate_is_refused(tmp_path):
    root = setup(tmp_path, {"lint": R.cmd(f"{R.q(R.PY)} touch.py gerado.txt")}, ["lint"])
    res, m = gate(root)
    assert res.status == "refused" and m["result"] == "error"
    assert any("gerado.txt" in s for s in res.summary)
    assert ".gitignore" in res.next


def test_cwd_and_tree_hash_match_lib(tmp_path):
    from core.lib import tree
    root = setup(tmp_path, {"lint": R.cmd(f"{R.q(R.PY)} ../emit.py - x 0", cwd="src")}, ["lint"])
    res, m = gate(root)
    assert res.status == "ok", res.summary
    assert m["inputs"]["tree"] == tree.compute(root) == res.data["tree"]


def test_concurrent_gates_same_task(tmp_path):
    root = setup(tmp_path, {"lint": R.cmd(f"{R.q(R.PY)} touch.py ignorado/a.txt 3")}, ["lint"])
    (root / "ignorado").mkdir()
    proc = subprocess.Popen([sys.executable, str(ROOT / "bootstrap.py"), "gate", "T1"], cwd=root,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lock = root / ".harness" / "runs" / "PAG-1.T1.lock"
    deadline = time.monotonic() + 15
    while not lock.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert lock.exists()
    res, _ = gate(root)
    assert res.exit == 4 and res.status == "refused"
    assert proc.wait(timeout=30) == 0
    assert not lock.exists()


def test_orphan_lock_is_removed_with_warning(tmp_path):
    root = setup(tmp_path, {"lint": R.cmd(R.emit("-"), timeoutSec=1)}, ["lint"])
    lock = root / ".harness" / "runs" / "PAG-1.T1.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("x")
    t = time.time() - 60
    os.utime(lock, (t, t))
    res, m = gate(root)
    assert res.exit == 0 and any("órfão" in s for s in res.summary)


def test_task_lookup_errors_are_usage(tmp_path):
    root = setup(tmp_path, {"lint": R.cmd(R.emit("-"))}, ["lint"])
    R.write_tasks(root, "OPS-2", [("T1", ["lint"])])
    res, _ = gate(root)
    assert res.exit == 2 and "OPS-2.T1" in res.summary[0] and "PAG-1.T1" in res.summary[0]
    assert gate(root, "T7")[0].exit == 2
    assert gate(root, "OPS-2.T1")[0].exit == 0


def test_not_a_git_repo_is_usage(tmp_path):
    R.write_profile(tmp_path, {"lint": R.cmd("x")})
    R.write_tasks(tmp_path, "PAG-1", [("T1", ["lint"])])
    res, path = gate(tmp_path)
    assert res.exit == 2 and path is None and "git init" in res.summary[0]


def test_missing_profile_is_usage(tmp_path):
    R.init(tmp_path)
    assert gate(tmp_path)[0].exit == 2


def test_text_output_respects_summary_lines(tmp_path):
    many = "".join(f'<testcase name="t{i}" file="tests/test_calc.py" line="{i}"><failure/></testcase>'
                   for i in range(12))
    xml = tmp_path.parent / f"{tmp_path.name}-many.xml"
    xml.write_text(f"<testsuite>{many}</testsuite>", encoding="utf-8")
    root = setup(tmp_path, {"test": R.unit(xml)}, ["test.unit"], limits={"summaryLines": 6})
    proc = cli(root, "gate", "T1")
    lines = proc.stdout.splitlines()
    assert proc.returncode == 1
    assert len(lines) <= 6, lines
    assert FIRST_LINE.match(lines[0]), lines[0]
    assert lines[-1].startswith("→ ")
    assert any(line.startswith("log: ") for line in lines)


def test_text_output_default_cap(tmp_path):
    root = setup(tmp_path, {"test": R.unit(D / "xunit1-fail.xml")}, ["test.unit"])
    res, _ = gate(root)
    assert len(render_text(res).splitlines()) <= 10


def test_cli_json_and_prove_sensor(tmp_path):
    root = setup(tmp_path, {"test": R.unit(D / "xunit2-pass.xml")}, ["test.unit"])
    proc = cli(root / "src", "--json", "gate", "T1")  # acha a raiz subindo a partir de src/
    env = json.loads(proc.stdout)
    assert proc.returncode == 0 == env["exit"] and env["data"]["result"] == "pass"
    proved = cli(root, "--json", "gate", "T1", "--prove-sensor")
    env = json.loads(proved.stdout)
    assert proved.returncode == 10 and "2E" in env["summary"][0]


def test_manifest_paths_use_forward_slashes(tmp_path):
    root = setup(tmp_path, {"test": R.unit(D / "xunit2-pass.xml")}, ["test.unit"])
    _, m = gate(root)
    text = json.dumps(m)
    assert "\\\\" not in text
