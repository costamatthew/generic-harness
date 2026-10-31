"""Stub do `harness gate` (trilha 1A) para quem consome o gate antes dele existir (1B, 1G).

Produz um manifesto válido contra core/schemas/run-manifest.schema.json e o
envelope cli/v0 correspondente, sem rodar comando nenhum. Não é o gate: não
calcula hash de árvore nem lê JUnit. Ao integrar, troque por `harness gate`.

    python -m tests.stubs.gate_stub T1 --result fail --out .harness/runs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

RESULT_TO_STATUS = {"pass": "ok", "fail": "fail", "sensor-absent": "sensor-absent", "error": "error"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_manifest(task_id: str, result: str = "pass", tree: str | None = None,
                  attempt: int = 1, command: str = "test.unit") -> dict:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    tree = tree or hashlib.sha256(b"stub-tree").hexdigest()
    log = {"path": f".harness/runs/{run_id}/{command}.log", "sha256": hashlib.sha256(b"log").hexdigest()}
    if result == "sensor-absent":
        check = {"name": command, "status": "absent", "absent": {"reason": "planned", "decidedBy": "ADR-0003"}}
    elif result == "error":
        check = {"name": command, "status": "error", "run": "stub", "exitCode": None}
    else:
        code = 0 if result == "pass" else 1
        check = {"name": command, "status": result, "run": "stub", "exitCode": code, "log": log}
    system = platform.system().lower()
    return {
        "schema": 0,
        "runId": run_id,
        "attempt": attempt,
        "taskId": task_id,
        "startedAt": _now(),
        "finishedAt": _now(),
        "result": result,
        "inputs": {
            "revision": None, "dirty": True, "tree": tree, "treeAlgorithm": "sha256-worktree-v0",
            "treeExcludes": [".harness/runs/**"],
            "profileSha256": hashlib.sha256(b"profile").hexdigest(), "harnessVersion": "0.0.0-stub",
        },
        "environment": {"os": system if system in ("linux", "darwin", "windows") else "other",
                        "python": platform.python_version()},
        "checks": [check],
    }


def make_envelope(manifest: dict, manifest_path: str) -> dict:
    result = manifest["result"]
    status = RESULT_TO_STATUS[result]
    exit_code = {"ok": 0, "fail": 1, "sensor-absent": 3, "error": 5}[status]
    tree = manifest["inputs"]["tree"][:7]
    check = manifest["checks"][0]
    return {
        "contract": "cli/v0", "command": "gate", "status": status, "exit": exit_code,
        "summary": [f"GATE {manifest['taskId']} {check['name']}  {result.upper()} exit={check.get('exitCode')}  tree={tree}"],
        "data": {"manifest": manifest_path, "runId": manifest["runId"]},
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("task_id")
    p.add_argument("--result", choices=list(RESULT_TO_STATUS), default="pass")
    p.add_argument("--tree")
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--out", default=".harness/runs")
    a = p.parse_args(argv)
    manifest = make_manifest(a.task_id, a.result, a.tree, a.attempt)
    path = Path(a.out) / manifest["runId"] / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    env = make_envelope(manifest, path.as_posix())
    print(json.dumps(env, ensure_ascii=False))
    return env["exit"]


if __name__ == "__main__":
    sys.exit(main())
