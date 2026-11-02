"""S4 stop_gate (trilha 1C): decide() com a evidência injetada."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.hooks import stop_gate
from core.lib import schema


def event(root):
    return {"contract": "hook/v0", "event": "stop", "source": {"tool": "test"},
            "session": {"id": "s", "projectDir": str(root), "cwd": str(root)}, "stop": {"reentry": False}}


def write_tasks(root, tasks, work="PAG-12"):
    d = Path(root) / ".harness/work" / work
    d.mkdir(parents=True, exist_ok=True)
    (d / "tasks.json").write_text(json.dumps({"schema": 0, "workId": work, "revision": 1, "tasks": tasks}), encoding="utf-8")


def task(tid, status="in-progress", **extra):
    return {"id": tid, "title": "t", "status": status, "dod": {"commands": ["lint"]}, **extra}


def fakes(code_by_task):
    """latest/check falsos: `None` em code_by_task = sem manifesto."""
    def latest(root, task_id):
        return None if code_by_task[task_id] is None else Path(task_id)

    def check(root, manifest):
        return SimpleNamespace(ok=code_by_task[str(manifest)] == "fresh", code=code_by_task[str(manifest)], reason="")
    return {"latest": latest, "check": check}


def decide(root, codes):
    result = stop_gate.decide(event(root), **fakes(codes))
    assert schema.validate(result, "hook-result") == []
    return result


def test_fresh_manifest_allows(tmp_path):
    write_tasks(tmp_path, [task("T1")])
    assert decide(tmp_path, {"PAG-12.T1": "fresh"})["decision"] == "allow"


def test_no_task_in_progress_allows_without_touching_evidence(tmp_path):
    write_tasks(tmp_path, [task("T1", "done"), task("T2", "todo")])
    assert stop_gate.decide(event(tmp_path), check=None, latest=lambda *a: pytest.fail("não deveria consultar"))["decision"] == "allow"


@pytest.mark.parametrize("code", ["stale-tree", "not-pass", None])
def test_not_fresh_blocks_with_what_why_instead(tmp_path, code):
    write_tasks(tmp_path, [task("T1")])
    result = decide(tmp_path, {"PAG-12.T1": code})
    assert result["decision"] == "block"
    msg = result["message"]
    assert msg["what"].startswith("PAG-12.T1 em andamento sem gate verde na árvore atual (")
    assert (code or "no-manifest") in msg["what"]
    assert msg["why"] == "S4: não se encerra com vermelho (cap. 17)"
    assert "harness gate PAG-12.T1" in msg["instead"] and "harness task block PAG-12.T1 --reason" in msg["instead"]


def test_task_with_blocker_allows(tmp_path):
    write_tasks(tmp_path, [task("T1", blocker={"reason": "x", "at": "2026-11-01T00:00:00Z"})])
    assert decide(tmp_path, {"PAG-12.T1": "stale-tree"})["decision"] == "allow"


def test_lists_at_most_three_tasks(tmp_path):
    ids = [f"T{i}" for i in range(1, 6)]
    write_tasks(tmp_path, [task(i) for i in ids])
    result = decide(tmp_path, {f"PAG-12.{i}": "not-pass" for i in ids})
    what = result["message"]["what"]
    assert what.count("em andamento") == 3 and what.endswith("+2") and len(what) <= 300


def test_third_reentry_only_asks_for_blocker_and_allow_resets(tmp_path):
    write_tasks(tmp_path, [task("T1")])
    bad = {"PAG-12.T1": "stale-tree"}
    first = decide(tmp_path, bad)["message"]["instead"]
    second = decide(tmp_path, bad)["message"]["instead"]
    third = decide(tmp_path, bad)["message"]["instead"]
    assert "harness gate" in first and "harness gate" in second
    assert "harness gate" not in third and "harness task block PAG-12.T1" in third
    counter = json.loads((tmp_path / ".harness/runs/stop-gate.json").read_text(encoding="utf-8"))
    assert counter == {"PAG-12.T1": 3}
    assert decide(tmp_path, {"PAG-12.T1": "fresh"})["decision"] == "allow"
    assert not (tmp_path / ".harness/runs/stop-gate.json").exists()
    assert "harness gate" in decide(tmp_path, bad)["message"]["instead"]  # contagem recomeça


def test_limit_comes_from_profile_and_counts_even_without_reentry_flag(tmp_path):
    write_tasks(tmp_path, [task("T1")])
    (tmp_path / ".harness/profile.json").write_text(json.dumps({"limits": {"stopReentries": 1}}), encoding="utf-8")
    ev = event(tmp_path)
    assert ev["stop"]["reentry"] is False
    result = stop_gate.decide(ev, **fakes({"PAG-12.T1": "not-pass"}))
    assert "harness gate" not in result["message"]["instead"]


def test_component_off_always_allows(tmp_path):
    write_tasks(tmp_path, [task("T1")])
    (tmp_path / ".harness/profile.json").write_text(json.dumps({"components": {"stopGate": False}}), encoding="utf-8")
    assert decide(tmp_path, {"PAG-12.T1": "not-pass"})["decision"] == "allow"


def test_in_progress_aceita_id_ja_qualificado(tmp_path):
    # Achado da integração 1I: o fixture da 1G grava `FIX-1.T1`, e o schema aceita as duas formas.
    write_tasks(tmp_path, [task("PAG-12.T1"), task("T2")])
    assert stop_gate.in_progress_tasks(tmp_path) == ["PAG-12.T1", "PAG-12.T2"]
