"""Contrato do repo-fixture n0-python (spec 1G, item 5)."""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from core.lib import schema

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "repos" / "n0-python"
H = FIXTURE / ".harness"

# Lista BF §4.1 (arquivos de instrução, skills, sub-agents, hooks, MCP, spec, CI).
BF_41 = [
    "AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", "GEMINI.md", ".cursorrules", ".windsurfrules", ".clinerules",
    "CONVENTIONS.md", ".github", ".claude", ".agents", ".cursor", ".windsurf", ".junie", ".codex", ".mcp.json",
    ".vscode", ".specify", "openspec", ".kiro", ".specs", "agent-os", "llms.txt",
]


def _json(name: str) -> dict:
    return json.loads((H / name).read_text(encoding="utf-8").replace("@PYTHON@", sys.executable.replace("\\", "/")))


@pytest.mark.parametrize("name", ["profile.json.in", "profile-planned.json.in"])
def test_profile_valid(name):
    assert schema.validate(_json(name), "profile") == []


def test_profile_variants():
    green, planned = _json("profile.json.in"), _json("profile-planned.json.in")
    assert green["commands"]["test"]["unit"]["status"] == "verified"
    assert planned["commands"]["test"]["unit"]["status"] == "planned"
    assert green["limits"]["stopReentries"] == 3


def test_tasks_valid():
    data = _json("work/FIX-1/tasks.json")
    assert schema.validate(data, "tasks") == []
    assert [t["status"] for t in data["tasks"]] == ["in-progress", "todo"]
    assert "### Verifier" not in (H / "work/FIX-1/validation.md").read_text(encoding="utf-8")


def test_invalid_variant_is_rejected():
    bad = _json("work/FIX-1/tasks.json")
    bad["tasks"][0]["status"] = "done"  # done sem evidence
    assert schema.validate(bad, "tasks") != []


def test_no_bf41_paths():
    found = [p.relative_to(FIXTURE).as_posix() for p in FIXTURE.rglob("*")
             if "__pycache__" not in p.parts and (p.name in BF_41 or p.suffix == ".mdc"
                                                  or p.name.endswith(".instructions.md"))]
    assert found == [], f"o fixture N0 não pode conter arquivos da lista BF §4.1: {found}"


def _run_fixture(tmp: Path):
    import shutil
    dst = tmp / "calc"
    shutil.copytree(FIXTURE, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return dst


def _pytest(dst: Path):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "junit_family=xunit1",
           "--junitxml=.harness/runs/junit-unit.xml"]
    proc = subprocess.run(cmd, cwd=dst, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, ET.parse(dst / ".harness/runs/junit-unit.xml").getroot().find("testsuite")


def test_fixture_alone_green_then_red(tmp_path):
    dst = _run_fixture(tmp_path)
    code, suite = _pytest(dst)
    assert code == 0 and suite.get("tests") == "3" and suite.get("failures") == "0"
    test = dst / "tests" / "test_calc.py"
    test.write_text(test.read_text(encoding="utf-8").replace("== 3", "== 4"), encoding="utf-8")
    code, suite = _pytest(dst)
    assert code == 1 and suite.get("failures") == "1"
    failed = next(c for c in suite.iter("testcase") if c.find("failure") is not None)
    assert failed.get("file") and failed.get("line")
