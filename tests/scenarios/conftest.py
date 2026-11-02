"""Helper `host` dos cenários: copia o repo-fixture, instala o perfil e roda o CLI real.

Os cenários não usam stubs (spec 1G): exit 10 (`not-implemented`) vira skip pela
política de `tests/scenarios/policy.py`. Só `sys.executable` e `/` nos caminhos.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.scenarios.policy import not_delivered

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "repos" / "n0-python"
CC = ROOT / "tests" / "fixtures" / "claude-code"
WORK = ".harness/work/FIX-1"
TASK = "FIX-1.T1"


@dataclass
class Completed:
    returncode: int
    stdout: str
    stderr: str

    @property
    def data(self) -> dict:
        """Envelope cli/v0 (vazio se a saída não é JSON, ex.: hook)."""
        try:
            parsed = json.loads(self.stdout)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @property
    def text(self) -> str:
        env = self.data
        parts = list(env.get("summary", [])) + ([env["next"]] if env.get("next") else [])
        return "\n".join(parts + [self.stdout, self.stderr])


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8")


class Host:
    def __init__(self, path: Path, variant: str):
        self.path = path
        self.variant = variant
        self.last_gate: Completed | None = None

    # ---- execução -------------------------------------------------------
    def _env(self, extra: dict | None) -> dict:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONUTF8"] = "1"
        env["CLAUDE_PROJECT_DIR"] = str(self.path)
        env.pop("HARNESS_TEST_CRASH_AT", None)
        env.update(extra or {})
        return env

    def _run(self, argv: list[str], stdin: str | None, env: dict | None) -> Completed:
        proc = subprocess.run(
            [sys.executable, "-m", "core.cli.harness", *argv], cwd=self.path, input=stdin,
            capture_output=True, text=True, encoding="utf-8", env=self._env(env), timeout=300)
        done = Completed(proc.returncode, proc.stdout, proc.stderr)
        if done.returncode == 10:
            m = re.search(r"trilha (\w+)", done.text)
            not_delivered(m.group(1) if m else "desconhecida", " ".join(argv))
        return done

    def harness(self, *args: str, stdin: str | None = None, env: dict | None = None) -> Completed:
        done = self._run(["--json", *args], stdin, env)
        if args and args[0] == "gate":
            self.last_gate = done
        return done

    def hook(self, native_fixture: str) -> Completed:
        """Roda `hook stop_gate` com o stdin nativo do caso, trocando `cwd` pelo host."""
        event = json.loads((CC / f"{native_fixture}.native.json").read_text(encoding="utf-8"))
        event["cwd"] = self.path.as_posix()
        return self._run(["hook", "stop_gate", "--adapter", "claude-code"], json.dumps(event), None)

    # ---- arquivos -------------------------------------------------------
    def read(self, rel: str) -> str:
        return (self.path / rel).read_text(encoding="utf-8")

    def tasks(self) -> dict:
        return json.loads(self.read(f"{WORK}/tasks.json"))

    def task(self, task_id: str = TASK) -> dict:
        return next(t for t in self.tasks()["tasks"] if t["id"] == task_id)

    def manifest(self) -> dict:
        rel = self.last_gate.data["data"]["manifest"]
        return json.loads(self.read(Path(rel).as_posix()))

    def gate_tree(self) -> str:
        return self.manifest()["inputs"]["tree"]

    # ---- mutações do cenário ---------------------------------------------
    def break_test(self) -> None:
        p = self.path / "tests" / "test_calc.py"
        p.write_text(p.read_text(encoding="utf-8").replace("== 3", "== 4"), encoding="utf-8", newline="\n")

    def edit_src(self) -> None:
        p = self.path / "src" / "calc" / "__init__.py"
        p.write_text(p.read_text(encoding="utf-8") + "\n\ndef mul(a: int, b: int) -> int:\n    return a * b\n",
                     encoding="utf-8", newline="\n")

    def write_verifier(self, tree: str) -> None:
        """Acrescenta a seção Verifier (formato da 1D) com um `atende` por check."""
        checks = self.task()["dod"]["checks"]
        rows = "\n".join(f"| {i} | {c} | atende | src/calc/__init__.py:{4 + 4 * i} |" for i, c in enumerate(checks, 1))
        section = (f"\n### Verifier {TASK}\n- tree: {tree[:7]}\n\n"
                   f"| # | Check | Resultado | Evidência |\n| --- | --- | --- | --- |\n{rows}\n")
        p = self.path / WORK / "validation.md"
        p.write_text(p.read_text(encoding="utf-8") + section, encoding="utf-8", newline="\n")


@pytest.fixture
def host(tmp_path, request):
    variant = getattr(request, "param", "green")
    if variant not in ("green", "red", "planned"):
        raise ValueError(f"variante desconhecida: {variant}")
    path = tmp_path / "repo"
    shutil.copytree(FIXTURE, path, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    src = "profile-planned.json.in" if variant == "planned" else "profile.json.in"
    text = (path / ".harness" / src).read_text(encoding="utf-8").replace("@PYTHON@", sys.executable.replace("\\", "/"))
    (path / ".harness" / "profile.json").write_text(text, encoding="utf-8", newline="\n")
    for name in ("profile.json.in", "profile-planned.json.in"):
        (path / ".harness" / name).unlink()
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "fixture")
    _git(path, "config", "user.email", "fixture@example.invalid")
    _git(path, "config", "core.autocrlf", "false")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "fixture")
    h = Host(path, variant)
    if variant == "red":
        h.break_test()
    return h
