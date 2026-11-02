"""Repo descartável com gate real para os testes da 1B."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.cli.gate import run_gate
from tests.unit.lib import repo as R

ROOT = Path(__file__).resolve().parents[3]
CHECKS = ["carrinho intacto após recusa", "erro mostrado ao usuário"]
VERIFIER = """### Verifier PAG-1.T1
- tree: {tree}

| # | Check | Resultado | Evidência |
| --- | --- | --- | --- |
| 1 | carrinho intacto após recusa | atende | src/app.py:1 |
| 2 | erro mostrado ao usuário | atende | exec: python -m pytest tests/test_x.py exit=0 |
"""


def setup(root: Path, checks: list[str] | None = None, commands: dict | None = None, dod=("test.unit",)) -> Path:
    R.init(root)
    R.write_profile(root, commands or {"test": R.unit(R.DATA_GATE / "xunit2-pass.xml")})
    dod_doc = {"commands": list(dod)}
    if checks:
        dod_doc["checks"] = checks
    doc = {"schema": 0, "workId": "PAG-1", "revision": 3, "tasks": [
        {"id": "T1", "title": "Recusar pagamento", "status": "in-progress", "dod": dod_doc},
        {"id": "T2", "title": "Estornar", "status": "todo", "dod": {"commands": ["test.unit"]}}]}
    write_tasks_doc(root, doc)
    return root


def tasks_path(root: Path) -> Path:
    return root / ".harness" / "work" / "PAG-1" / "tasks.json"


def write_tasks_doc(root: Path, doc: dict) -> None:
    p = tasks_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def tasks_doc(root: Path) -> dict:
    return json.loads(tasks_path(root).read_text(encoding="utf-8"))


def gate(root: Path, task="PAG-1.T1") -> dict:
    res, path = run_gate(root, task)
    return json.loads(path.read_text(encoding="utf-8")) if path else {}


def write_verifier(root: Path, text: str) -> None:
    p = root / ".harness" / "work" / "PAG-1" / "validation.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def cli(root: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    import os
    return subprocess.run([sys.executable, str(ROOT / "bootstrap.py"), "--json", *args], cwd=root,
                          capture_output=True, text=True, encoding="utf-8", env={**os.environ, **(env or {})})
