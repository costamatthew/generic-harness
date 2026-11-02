"""Repo git descartável para os testes da 1A (o repo-fixture da 1G ainda não existe)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PY = sys.executable
DATA_LIB = Path(__file__).resolve().parent / "data"
DATA_GATE = Path(__file__).resolve().parents[1] / "gate" / "data"

# Scripts auxiliares gravados no repo de teste: evitam aspas diferentes entre sh e cmd.exe.
EMIT = """import shutil, sys
src, dest, code = sys.argv[1], sys.argv[2], int(sys.argv[3])
if src != "-":
    shutil.copyfile(src, dest)
print("emit", dest, code)
sys.exit(code)
"""
TOUCH = """import sys, time
open(sys.argv[1], "w").write("ran")
if len(sys.argv) > 2:
    time.sleep(float(sys.argv[2]))
"""


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def init(root: Path, commit: bool = True) -> Path:
    git(root, "init", "-q")
    git(root, "config", "core.autocrlf", "false")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    (root / ".gitignore").write_text("ignorado/\n__pycache__/\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_calc.py").write_text("def test_soma():\n    assert 1 + 2 == 4\n", encoding="utf-8")
    (root / "emit.py").write_text(EMIT, encoding="utf-8")
    (root / "touch.py").write_text(TOUCH, encoding="utf-8")
    if commit:
        commit_all(root)
    return root


def commit_all(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "c")


def q(p) -> str:
    return f'"{p}"'


def cmd(run: str, status: str = "verified", **extra) -> dict:
    return {"run": run, "origin": extra.pop("origin", "ci"), "status": status, **extra}


def emit(src: str | Path, code: int = 0, report: str = ".harness/runs/unit.xml") -> str:
    return f"{q(PY)} emit.py {q(src) if src != '-' else '-'} {report} {code}"


def write_profile(root: Path, commands: dict, limits: dict | None = None) -> None:
    doc = {"schema": 0, "project": {"name": "t", "kind": "brownfield"}, "commands": commands,
           "boundaries": {"always": [], "ask": [], "never": []}}
    if limits:
        doc["limits"] = limits
    p = root / ".harness" / "profile.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def write_tasks(root: Path, work_id: str, tasks: list[tuple[str, list[str]]]) -> None:
    doc = {"schema": 0, "workId": work_id, "revision": 0,
           "tasks": [{"id": i, "title": f"task {i}", "status": "todo", "dod": {"commands": c}} for i, c in tasks]}
    p = root / ".harness" / "work" / work_id / "tasks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def unit(src: str | Path, code: int = 0, **extra) -> dict:
    return {"unit": cmd(emit(src, code), report=".harness/runs/unit.xml", reportFormat="junit", **extra)}
