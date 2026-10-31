"""Stubs e fixtures da Etapa 0 cumprem os contratos que as trilhas da Etapa 1 consomem."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.lib import schema
from tests.stubs import gate_stub, hook_stub

ROOT = Path(__file__).resolve().parents[2]
CC = ROOT / "tests" / "fixtures" / "claude-code"


@pytest.mark.parametrize("result", ["pass", "fail", "sensor-absent", "error"])
def test_gate_stub_manifest_and_envelope(result):
    manifest = gate_stub.make_manifest("T1", result)
    assert schema.validate(manifest, "run-manifest") == []
    env = gate_stub.make_envelope(manifest, "x/manifest.json")
    assert schema.validate(env, "cli-output") == []


def test_gate_stub_cli_writes_manifest(tmp_path):
    proc = subprocess.run([sys.executable, "-m", "tests.stubs.gate_stub", "T3", "--result", "fail", "--out", str(tmp_path)],
                          capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    env = json.loads(proc.stdout)
    assert proc.returncode == 1 == env["exit"]
    manifest = json.loads(Path(env["data"]["manifest"]).read_text(encoding="utf-8"))
    assert schema.validate(manifest, "run-manifest") == []


@pytest.mark.parametrize("decision", ["allow", "ask", "block"])
def test_hook_stub_results(decision):
    event = json.loads((CC / "stop_first.neutral.json").read_text(encoding="utf-8"))
    assert schema.validate(hook_stub.decide(event, decision), "hook-result") == []


def test_hook_stub_exit_code():
    event = (CC / "pre_tool_bash.neutral.json").read_text(encoding="utf-8")
    proc = subprocess.run([sys.executable, "-m", "tests.stubs.hook_stub"], input=event, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env={**os.environ, "HARNESS_STUB_DECISION": "block"})
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["decision"] == "block"


CASES = sorted(p.name.removesuffix(".native.json") for p in CC.glob("*.native.json"))


@pytest.mark.parametrize("case", CASES)
def test_claude_code_fixture_pairs(case):
    native = json.loads((CC / f"{case}.native.json").read_text(encoding="utf-8"))
    neutral = json.loads((CC / f"{case}.neutral.json").read_text(encoding="utf-8"))
    assert schema.validate(neutral, "hook-event") == []
    assert neutral["source"]["nativeEvent"] == native["hook_event_name"]
    assert neutral["session"]["id"] == native["session_id"]


def test_every_neutral_event_has_a_claude_code_fixture():
    events = {json.loads(p.read_text(encoding="utf-8"))["event"] for p in CC.glob("*.neutral.json")}
    assert events == set(schema.load("hook-event")["properties"]["event"]["enum"])
