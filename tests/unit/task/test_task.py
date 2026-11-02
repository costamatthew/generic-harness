"""`harness task done|block|status` (trilha 1B): critério binário da spec docs/plan/etapa-1/1B.md."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.cli import state as state_mod
from core.cli.harness import envelope
from core.cli.task import task_block, task_done, task_status, validation
from core.lib import blocks, evidence, schema
from tests.unit.lib import repo as R
from tests.unit.task import helpers as H


def _valid_env(res, cmd):
    env = envelope(res, cmd)
    assert schema.validate(env, "cli-output") == [], env
    return env


def _doc_ok(root):
    doc = H.tasks_doc(root)
    assert schema.validate(doc, "tasks") == []
    return doc


def _ready(root, checks=True):
    H.setup(root, H.CHECKS if checks else None)
    m = H.gate(root)
    assert m["result"] == "pass"
    if checks:
        H.write_verifier(root, "# Validação PAG-1\n\n" + H.VERIFIER.format(tree=m["inputs"]["tree"][:7]))
    return m


def test_done_ok_three_writes_and_revision(tmp_path):
    m = _ready(tmp_path)
    res = task_done(tmp_path, "T1")
    env = _valid_env(res, "task done")
    assert res.exit == 0 and set(res.data) == {"task", "manifest", "runId", "tree"}
    doc = _doc_ok(tmp_path)
    t = doc["tasks"][0]
    assert doc["revision"] == 4 and t["status"] == "done"
    assert t["evidence"]["runId"] == m["runId"] and t["evidence"]["tree"] == m["inputs"]["tree"]
    assert len(t["evidence"]["manifestSha256"]) == 64
    val = (tmp_path / ".harness/work/PAG-1/validation.md").read_text(encoding="utf-8")
    assert blocks.get(val, "evidence").count(f"run={m['runId']}") == 1
    assert "### Verifier PAG-1.T1" in val  # a seção do verifier fica intacta
    st = (tmp_path / ".harness/STATE.md").read_text(encoding="utf-8")
    assert f"- PAG-1.T1 · done · run={m['runId']}" in blocks.get(st, "tasks")
    assert env["next"].startswith("git add ") and "git commit -m" in env["next"] and "PAG-1.T1: Recusar pagamento" in env["next"]
    # o lock some ao fim do `task done`; sugerir `git add` dele faz o comando inteiro falhar (piloto 1I)
    assert ".journal/lock" not in env["next"]
    # rodar de novo: já concluída, nada duplica
    again = task_done(tmp_path, "PAG-1.T1")
    assert again.exit == 4 and "já concluída" in again.summary[-1] and m["runId"] in again.summary[-1]
    assert H.tasks_doc(tmp_path)["revision"] == 4


def test_done_without_checks_needs_no_verifier(tmp_path):
    _ready(tmp_path, checks=False)
    assert task_done(tmp_path, "T1").exit == 0


def test_stale_tree_refused_and_tasks_untouched(tmp_path):
    _ready(tmp_path)
    before = H.tasks_path(tmp_path).read_bytes()
    (tmp_path / "src" / "app.py").write_text("x = 2\n", encoding="utf-8")
    res = task_done(tmp_path, "T1")
    assert res.exit == 4 and "harness gate PAG-1.T1" in res.next
    assert H.tasks_path(tmp_path).read_bytes() == before
    assert not (tmp_path / ".harness/STATE.md").exists()


def test_no_manifest_refused(tmp_path):
    H.setup(tmp_path)
    res = task_done(tmp_path, "T1")
    assert res.exit == 4 and "harness gate" in res.next


def test_fail_manifest_refused(tmp_path):
    H.setup(tmp_path, commands={"test": R.unit(R.DATA_GATE / "xunit2-fail.xml")})
    assert H.gate(tmp_path)["result"] == "fail"
    assert task_done(tmp_path, "T1").exit == 4


def test_sensor_absent_exit_3_repeats_reason(tmp_path):
    H.setup(tmp_path, commands={"lint": R.cmd("x", status="planned", origin="decision:ADR-0007")}, dod=("lint",))
    assert H.gate(tmp_path)["result"] == "sensor-absent"
    res = task_done(tmp_path, "T1")
    assert res.exit == 3 and "planned" in res.summary[-1]
    assert H.tasks_doc(tmp_path)["tasks"][0]["status"] == "in-progress"


@pytest.mark.parametrize("name,mutate", [
    ("sem seção", lambda t, tree: "# Validação\n"),
    ("tree diferente", lambda t, tree: t.replace(f"tree: {tree}", "tree: 0000000")),
    ("check sem linha", lambda t, tree: "\n".join(ln for ln in t.splitlines() if "erro mostrado" not in ln) + "\n"),
    ("não atende", lambda t, tree: t.replace("| atende | src/app.py:1", "| não atende | src/app.py:1")),
    ("evidência sem arquivo:linha", lambda t, tree: t.replace("src/app.py:1", "parece certo")),
    ("exec com exit diferente de 0", lambda t, tree: t.replace("exit=0", "exit=1")),
])
def test_verifier_cases_exit_4(tmp_path, name, mutate):
    m = _ready(tmp_path)
    tree = m["inputs"]["tree"][:7]
    H.write_verifier(tmp_path, mutate(H.VERIFIER.format(tree=tree), tree))
    before = H.tasks_path(tmp_path).read_bytes()
    res = task_done(tmp_path, "T1")
    assert res.exit == 4, name
    assert "Verifier" in res.summary[-1] or "verifier" in res.summary[-1]
    assert H.tasks_path(tmp_path).read_bytes() == before


def test_done_refuses_blocked(tmp_path):
    _ready(tmp_path)
    assert task_block(tmp_path, "T1", "falta credencial").exit == 0
    res = task_done(tmp_path, "T1")
    assert res.exit == 4 and "blocked" in res.summary[-1]


def test_revision_divergent_refused_without_write(tmp_path):
    _ready(tmp_path)

    def racing_check(root, mp):  # outro processo grava tasks.json entre a leitura e a escrita
        doc = H.tasks_doc(tmp_path)
        doc["revision"] += 1
        H.write_tasks_doc(tmp_path, doc)
        return evidence.check(root, mp)

    res = task_done(tmp_path, "T1", check=racing_check)
    assert res.exit == 4 and "mudou durante a operação" in res.summary[-1]
    doc = H.tasks_doc(tmp_path)
    assert doc["revision"] == 4 and doc["tasks"][0]["status"] == "in-progress"


def test_block_writes_tasks_and_state(tmp_path):
    H.setup(tmp_path)
    res = task_block(tmp_path, "T1", "sandbox fora do ar", "credencial")
    _valid_env(res, "task block")
    assert res.exit == 0 and res.data == {"task": "PAG-1.T1"}
    doc = _doc_ok(tmp_path)
    t = doc["tasks"][0]
    assert t["status"] == "blocked" and t["blocker"]["needs"] == "credencial" and doc["revision"] == 4
    st = (tmp_path / ".harness/STATE.md").read_text(encoding="utf-8")
    assert "sandbox fora do ar (precisa: credencial)" in st and "- Nenhum." not in st
    assert task_block(tmp_path, "T1", "sandbox fora do ar", "credencial").exit == 0
    assert st.count("sandbox fora do ar") == (tmp_path / ".harness/STATE.md").read_text(encoding="utf-8").count("sandbox fora do ar")


def test_block_done_refused(tmp_path):
    _ready(tmp_path)
    assert task_done(tmp_path, "T1").exit == 0
    res = task_block(tmp_path, "T1", "x")
    assert res.exit == 4 and _doc_ok(tmp_path)["tasks"][0]["status"] == "done"


def test_status_table(tmp_path):
    m = _ready(tmp_path)
    res = task_status(tmp_path)
    _valid_env(res, "task status")
    rows = {r["id"]: r for r in res.data["tasks"]}
    assert rows["PAG-1.T1"]["gate"] == {"result": "pass", "tree": m["inputs"]["tree"][:7], "attempt": 1}
    assert rows["PAG-1.T2"]["gate"] is None
    assert res.summary[0].startswith("PAG-1.T1 · in-progress · pass tree=")
    assert len(task_status(tmp_path, "T2").data["tasks"]) == 1


def test_unknown_task_is_usage(tmp_path):
    _ready(tmp_path)
    assert task_done(tmp_path, "T9").exit == 2
    assert task_done(tmp_path, "xx").exit == 2


# ---- crash e reconciliação (processo de verdade, os._exit(99)) ----

@pytest.mark.parametrize("point", ["after-journal", "after-tasks", "after-validation"])
def test_crash_never_done_without_evidence(tmp_path, point):
    m = _ready(tmp_path)
    crashed = H.cli(tmp_path, "task", "done", "PAG-1.T1", env={"HARNESS_TEST_CRASH_AT": point})
    assert crashed.returncode == 99, crashed.stderr
    st = H.cli(tmp_path, "task", "status")
    assert st.returncode == 0, st.stdout + st.stderr
    doc = _doc_ok(tmp_path)
    t = doc["tasks"][0]
    if t["status"] == "done":
        val = (tmp_path / ".harness/work/PAG-1/validation.md").read_text(encoding="utf-8")
        state = (tmp_path / ".harness/STATE.md").read_text(encoding="utf-8")
        assert blocks.get(val, "evidence").count(f"run={m['runId']}") == 1
        assert blocks.get(state, "tasks").count(f"run={m['runId']}") == 1
        assert t["evidence"]["runId"] == m["runId"]
    else:
        assert "evidence" not in t
    # repetir não duplica nada
    H.cli(tmp_path, "task", "done", "PAG-1.T1")
    val = (tmp_path / ".harness/work/PAG-1/validation.md").read_text(encoding="utf-8")
    state = (tmp_path / ".harness/STATE.md").read_text(encoding="utf-8")
    assert blocks.get(val, "evidence").count("run=") == 1 and blocks.get(state, "tasks").count("run=") == 1
    assert _doc_ok(tmp_path)["tasks"][0]["status"] == "done" and _doc_ok(tmp_path)["revision"] == 4
    journals = list((tmp_path / ".harness/work/PAG-1/.journal").glob("*.json"))
    assert journals and all(json.loads(j.read_text())["complete"] for j in journals)


def test_crash_after_journal_then_tree_edit_asks_for_gate(tmp_path):
    _ready(tmp_path)
    assert H.cli(tmp_path, "task", "done", "PAG-1.T1", env={"HARNESS_TEST_CRASH_AT": "after-journal"}).returncode == 99
    (tmp_path / "src" / "app.py").write_text("x = 99\n", encoding="utf-8")
    st = H.cli(tmp_path, "task", "status")
    out = json.loads(st.stdout)
    assert any("a conclusão de PAG-1.T1 foi interrompida e a árvore mudou; rode harness gate" in s for s in out["summary"])
    assert _doc_ok(tmp_path)["tasks"][0]["status"] == "in-progress"
    assert not list((tmp_path / ".harness/work/PAG-1/.journal").glob("*.json"))


def test_crash_env_only_at_three_points(tmp_path):
    _ready(tmp_path)
    r = H.cli(tmp_path, "task", "done", "PAG-1.T1", env={"HARNESS_TEST_CRASH_AT": "qualquer"})
    assert r.returncode == 0


def test_no_gate_stub_imports():
    needle = "tests.stubs" + ".gate_stub"
    for f in Path(__file__).parent.glob("*.py"):
        assert needle not in f.read_text(encoding="utf-8"), f.name
