"""`harness hook` (passo 3 e política de falha) com stubs, sem depender do estado do stop_gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.cli import hook as hook_cli
from core.hooks import stop_gate
from core.lib import schema
from tests.stubs import hook_stub

ROOT = Path(__file__).resolve().parents[3]
FIX = ROOT / "tests/fixtures/claude-code"
STOP = (FIX / "stop_first.native.json").read_text(encoding="utf-8")


def cli(*args, stdin="", cwd=None):
    return subprocess.run([sys.executable, str(ROOT / "bootstrap.py"), *args], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", cwd=cwd or ROOT)


@pytest.fixture
def stub_hook(monkeypatch):
    """Faz `core.hooks.stop_gate.decide` responder pelo stub (allow/ask/block)."""
    def install(decision):
        monkeypatch.setattr(stop_gate, "decide", lambda ev: hook_stub.decide(ev, decision) | {"hook": "stop_gate"})
    return install


@pytest.mark.parametrize("decision, code", [("allow", 0), ("block", 2)])
def test_step3_exit_codes(stub_hook, decision, code):
    stub_hook(decision)
    got, out, err = hook_cli.process("stop_gate", "claude-code", STOP)
    assert got == code
    assert (err != "") == (decision == "block")
    if decision == "block":
        assert json.loads(out)["decision"] == "block" and "stub bloqueou" in err


def boom(ev):
    raise RuntimeError("estourou")


def test_stop_gate_fails_closed_when_decide_raises(monkeypatch):
    monkeypatch.setattr(stop_gate, "decide", boom)
    code, out, err = hook_cli.process("stop_gate", "claude-code", STOP)
    assert code == 2
    assert "hook falhou" in err and "harness doctor" in err and "registre o blocker" in err and "RuntimeError" in err
    assert json.loads(out)["decision"] == "block"


def test_stop_gate_fails_closed_on_invalid_result(monkeypatch):
    monkeypatch.setattr(stop_gate, "decide", lambda ev: {"contract": "hook/v0", "hook": "stop_gate", "decision": "block"})
    code, _, err = hook_cli.process("stop_gate", "claude-code", STOP)
    assert code == 2 and "hook-result inválido" in err


def test_stop_gate_fails_closed_on_garbage_stdin():
    code, _, err = hook_cli.process("stop_gate", "claude-code", "isto não é json")
    assert code == 2 and "harness doctor" in err


def test_other_hooks_fail_open_with_warning(monkeypatch):
    import types

    fake = types.ModuleType("core.hooks.post_edit")
    fake.decide = boom
    monkeypatch.setitem(sys.modules, "core.hooks.post_edit", fake)
    code, out, err = hook_cli.process("post_edit", "claude-code", STOP)
    assert code == 0 and "fail-open" in json.loads(out)["systemMessage"] and "hook falhou" in err


def test_missing_hook_module_fails_open_for_non_critical_and_closed_for_stop_gate():
    assert hook_cli.process("modulo_que_nao_existe", "claude-code", STOP)[0] == 0
    assert "stop_gate" in hook_cli.FAIL_CLOSED


def test_every_result_produced_here_matches_the_schema(stub_hook):
    for decision in ("allow", "ask", "block"):
        stub_hook(decision)
        assert schema.validate(stop_gate.decide({"event": "stop"}), "hook-result") == []


def make_repo(tmp_path, with_task):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    if with_task:
        d = tmp_path / ".harness/work/W-1"
        d.mkdir(parents=True)
        (d / "tasks.json").write_text(json.dumps({"schema": 0, "workId": "W-1", "revision": 1, "tasks": [
            {"id": "T1", "title": "t", "status": "in-progress", "dod": {"commands": ["lint"]}}]}), encoding="utf-8")
    native = json.loads(STOP) | {"cwd": str(tmp_path)}
    return json.dumps(native)


def test_end_to_end_blocks_with_exit_2_on_stderr_when_task_has_no_green_gate(tmp_path):
    proc = cli("hook", "stop_gate", "--adapter", "claude-code", stdin=make_repo(tmp_path, True))
    assert proc.returncode == 2
    # sem core.lib.evidence (1A, antes do merge) é o fail-closed; depois do merge, o stop_gate cita a task
    assert "harness" in proc.stderr
    assert json.loads(proc.stdout)["decision"] == "block"


def test_end_to_end_allows_without_task_in_progress(tmp_path):
    proc = cli("hook", "stop_gate", "--adapter", "claude-code", stdin=make_repo(tmp_path, False))
    assert proc.returncode == 0 and json.loads(proc.stdout) == {} and proc.stderr == ""


def test_usage_errors_keep_the_cli_envelope():
    bad_adapter = cli("--json", "hook", "stop_gate", "--adapter", "nao-existe")
    assert bad_adapter.returncode == 2 and json.loads(bad_adapter.stdout)["status"] == "usage"
    bad_name = cli("--json", "hook", "../x", "--adapter", "claude-code")
    assert json.loads(bad_name.stdout)["status"] == "usage"
