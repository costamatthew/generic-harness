"""Cenários C1-C4 do loop mínimo (plano §4; spec 1G). Rodam o CLI real.

Valem de verdade depois da integração 1I: antes, as trilhas ausentes dão skip
(ou falha, com HARNESS_REQUIRE_ALL=1).
"""

from __future__ import annotations

import json

import pytest

from core.lib import schema
from tests.scenarios.conftest import TASK, WORK

RED = pytest.mark.parametrize("host", ["red"], indirect=True)
PLANNED = pytest.mark.parametrize("host", ["planned"], indirect=True)
CRASH_POINTS = ["after-journal", "after-tasks", "after-validation"]


def _assert_valid_artifacts(host):
    assert schema.validate(host.tasks(), "tasks") == []
    if host.last_gate is not None:
        assert schema.validate(host.last_gate.data, "cli-output") == []
        assert schema.validate(host.manifest(), "run-manifest") == []


def _green_with_verifier(host):
    gate = host.harness("gate", TASK)
    assert gate.returncode == 0, gate.text
    host.write_verifier(host.gate_tree())
    return gate


@RED
def test_c1_gate_vermelho_bloqueia_o_stop(host):
    gate = host.harness("gate", TASK)
    assert gate.returncode == 1, gate.text
    hook = host.hook("stop_first")
    assert hook.returncode == 2, hook.stderr
    assert "harness gate" in hook.stderr and "task block" in hook.stderr
    _assert_valid_artifacts(host)


@RED
def test_c1b_blocker_libera_o_stop(host):
    host.harness("gate", TASK)
    assert host.hook("stop_first").returncode == 2
    block = host.harness("task", "block", TASK, "--reason", "x")
    assert block.returncode == 0, block.text
    assert host.hook("stop_first").returncode == 0
    assert host.task()["status"] == "blocked"
    _assert_valid_artifacts(host)


@RED
def test_c1c_limite_de_reentradas_pede_so_o_blocker(host):
    msgs = []
    for _ in range(3):
        hook = host.hook("stop_reentry")
        assert hook.returncode == 2, hook.stderr
        msgs.append(hook.stderr)
    assert "harness gate" in msgs[0]
    assert "harness task block" in msgs[2]
    assert "harness gate" not in msgs[2], "a 3ª mensagem deve pedir só o task block"


def test_c2_verde_antigo_e_recusado(host):
    assert host.harness("gate", TASK).returncode == 0
    host.edit_src()
    before = host.read(f"{WORK}/tasks.json")
    done = host.harness("task", "done", TASK)
    assert done.returncode == 4, done.text
    assert host.read(f"{WORK}/tasks.json") == before
    hook = host.hook("stop_first")
    assert hook.returncode == 2 and "stale-tree" in hook.stderr, hook.stderr
    _assert_valid_artifacts(host)


def test_c2b_verde_fresco_conclui(host):
    _green_with_verifier(host)
    done = host.harness("task", "done", TASK)
    assert done.returncode == 0, done.text
    task = host.task()
    assert task["status"] == "done"
    tree = host.gate_tree()
    assert tree.startswith(task["evidence"]["tree"]) or task["evidence"]["tree"] == tree
    _assert_valid_artifacts(host)


@pytest.mark.parametrize("crash_at", CRASH_POINTS)
def test_c3_interrupcao_nao_gera_conclusao_sem_prova(host, crash_at):
    _green_with_verifier(host)
    crashed = host.harness("task", "done", TASK, env={"HARNESS_TEST_CRASH_AT": crash_at})
    assert crashed.returncode == 99, f"esperava os._exit(99) em {crash_at}: {crashed.text}"
    assert host.harness("task", "status", TASK).returncode == 0
    _assert_valid_artifacts(host)  # `done` sem evidence reprova no schema
    task = host.task()
    if task["status"] == "done":
        run_id = task["evidence"]["runId"]
        assert host.read(f"{WORK}/validation.md").count(f"run={run_id}") == 1
        assert host.read(".harness/STATE.md").count(f"run={run_id}") == 1
        host.harness("task", "done", TASK)  # repetir não duplica
        assert host.read(f"{WORK}/validation.md").count(f"run={run_id}") == 1
        assert host.read(".harness/STATE.md").count(f"run={run_id}") == 1
    else:
        assert "evidence" not in task


def test_c3b_interrupcao_mais_edicao_nao_conclui(host):
    _green_with_verifier(host)
    crashed = host.harness("task", "done", TASK, env={"HARNESS_TEST_CRASH_AT": "after-journal"})
    assert crashed.returncode == 99
    host.edit_src()
    status = host.harness("task", "status", TASK)
    assert host.task()["status"] != "done"
    assert "gate" in status.text
    _assert_valid_artifacts(host)


@PLANNED
def test_c4_comando_planned_bloqueia(host):
    gate = host.harness("gate", TASK)
    assert gate.returncode == 3, gate.text
    assert not (host.path / ".harness" / "runs" / "junit-unit.xml").exists()
    done = host.harness("task", "done", TASK)
    assert done.returncode == 3, done.text
    _assert_valid_artifacts(host)
