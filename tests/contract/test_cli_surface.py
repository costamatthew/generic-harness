"""Contrato cli/v0 (docs/contracts/cli.md): a tabela de subcomandos, os códigos de saída e o envelope."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.cli import harness
from core.lib import schema

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = schema.SCHEMAS_DIR / "examples"


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "bootstrap.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", cwd=ROOT)


def test_exit_codes_match_schema():
    sch = schema.load("cli-output")
    assert sorted(harness.EXIT.values()) == sorted(sch["properties"]["exit"]["enum"])
    assert sorted(harness.EXIT) == sorted(sch["properties"]["status"]["enum"])


@pytest.mark.parametrize("name", [n for n in harness.COMMANDS if n != "validate"])
def test_unimplemented_commands_answer_with_envelope(name, tmp_path):
    args = name.split()
    for flags, kwargs in harness.COMMANDS[name][3]:
        if not flags[0].startswith("-"):
            if kwargs.get("nargs") != "?":
                args.append("X-1")
        elif kwargs.get("required"):
            args += [flags[0], "x"]
    proc = run_cli("--json", *args)
    env = json.loads(proc.stdout)
    assert schema.validate(env, "cli-output") == []
    assert proc.returncode == env["exit"]
    # Quando a trilha entregar o módulo, este teste passa a aceitar qualquer status válido.
    assert env["status"] in harness.EXIT


def test_validate_ok_and_fail():
    ok = run_cli("--json", "validate", "tasks", str(EXAMPLES / "tasks" / "valid.json"))
    assert ok.returncode == 0 and json.loads(ok.stdout)["status"] == "ok"
    bad = run_cli("validate", "tasks", str(EXAMPLES / "tasks" / "invalid-done-without-evidence.json"))
    assert bad.returncode == 1
    assert bad.stdout.splitlines()[-1].startswith("→ ")


def test_usage_error_is_exit_2():
    assert run_cli("gate").returncode == 2


def test_text_output_is_capped():
    result = harness.Result("fail", [f"linha {i}" for i in range(30)], next="faça X", logs=["run.log"])
    lines = harness.render_text(result, limit=10).splitlines()
    assert len(lines) == 11
    assert lines[-2] == "… (+21 linhas em run.log)"
    assert lines[-1] == "→ faça X"
