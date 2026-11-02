"""Adaptador Claude Code: os pares nativo ↔ neutro (tests/fixtures/claude-code) e o passo 3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.hooks import _loader
from core.lib import schema

translate = _loader.load("claude-code", "translate")
FIXTURES = Path(__file__).resolve().parents[4] / "tests/fixtures/claude-code"
CASES = sorted(p.name.removesuffix(".native.json") for p in FIXTURES.glob("*.native.json"))
# O projectDir vem do git (ou, nos testes, do argumento): ver o README das fixtures.
PROJECT_DIR = {"post_edit_windows": "C:\\dev\\pedidos"}


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_seven_pairs_exist():
    assert len(CASES) == 7


@pytest.mark.parametrize("case", CASES)
def test_native_to_neutral_matches_fixture(case):
    neutral = translate.to_neutral(load(f"{case}.native.json"), PROJECT_DIR.get(case, "/home/dev/pedidos"))
    assert neutral == load(f"{case}.neutral.json")
    assert schema.validate(neutral, "hook-event") == []


def test_project_dir_comes_from_git_not_env(tmp_path, monkeypatch):
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src").mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/outra/sessao")
    native = load("stop_first.native.json") | {"cwd": str(tmp_path / "src")}
    got = translate.to_neutral(native)["session"]["projectDir"]
    assert Path(got).resolve() == tmp_path.resolve()


def test_unknown_native_event_is_rejected():
    with pytest.raises(ValueError, match="sem tradução"):
        translate.to_neutral({"hook_event_name": "Notification", "cwd": "/x", "session_id": "s"}, "/x")


def event_for(kind):
    native = {"stop": "stop_first", "pre_tool": "pre_tool_write", "session_start": "session_start"}[kind]
    return translate.to_neutral(load(f"{native}.native.json"), "/home/dev/pedidos")


MSG = {"what": "X falhou", "why": "regra Y", "instead": "rode Z"}


def test_block_is_exit_2_with_message_on_stderr_and_json_on_stdout():
    code, out, err = translate.to_native({"contract": "hook/v0", "hook": "h", "decision": "block", "message": MSG}, event_for("stop"))
    assert code == 2 and err == "X falhou — regra Y — rode Z"
    assert json.loads(out) == {"decision": "block", "reason": err}


def test_block_in_pre_tool_uses_permission_decision():
    code, out, err = translate.to_native({"contract": "hook/v0", "hook": "h", "decision": "block", "message": MSG}, event_for("pre_tool"))
    assert code == 2 and json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_ask_and_allow_are_exit_0():
    code, out, err = translate.to_native({"contract": "hook/v0", "hook": "h", "decision": "ask", "message": MSG}, event_for("pre_tool"))
    assert code == 0 and err == "" and json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "ask"
    code, out, err = translate.to_native({"contract": "hook/v0", "hook": "h", "decision": "allow"}, event_for("stop"))
    assert (code, json.loads(out), err) == (0, {}, "")


def test_allow_context_goes_to_additional_context_in_session_start():
    res = {"contract": "hook/v0", "hook": "h", "decision": "allow", "context": ["a", "b"]}
    code, out, _ = translate.to_native(res, event_for("session_start"))
    assert json.loads(out)["hookSpecificOutput"] == {"hookEventName": "SessionStart", "additionalContext": "a\nb"}


@pytest.mark.parametrize("path, expected", [
    ("C:\\dev\\pedidos\\src\\a.py", "src/a.py"), ("c:/DEV/pedidos/src/a.py", "src/a.py"),
    ("src\\a.py", "src/a.py"), ("./src/a.py", "src/a.py"), ("D:\\outro\\a.py", "D:/outro/a.py"),
])
def test_windows_paths(path, expected):
    assert translate.relativize(path, "C:/dev/pedidos") == expected
