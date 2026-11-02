"""S4: o agente não encerra com vermelho (cap. 17, HG §3.2).

`decide(event)` bloqueia o Stop enquanto houver task `in-progress`, sem blocker,
cujo último manifesto de gate não seja `fresh` na árvore atual. O limite de
reentradas (`limits.stopReentries`) troca o `instead` por "registre o blocker",
para o harness decidir antes do teto de 8 continuações da ferramenta.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.hooks import _fsx

HOOK = "stop_gate"
COUNTER_REL = ".harness/runs/stop-gate.json"
DEFAULT_REENTRIES = 3
MAX_LISTED = 3
WHY = "S4: não se encerra com vermelho (cap. 17)"


def _result(decision: str, message: dict | None = None) -> dict:
    out = {"contract": "hook/v0", "hook": HOOK, "decision": decision}
    if message:
        out["message"] = {k: v[:300] for k, v in message.items()}
    return out


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _profile(root: Path) -> dict:
    """Leitura tolerante: o perfil inválido não pode derrubar o portão (o gate o valida)."""
    doc = _read_json(root / ".harness" / "profile.json")
    return doc if isinstance(doc, dict) else {}


def in_progress_tasks(root: Path) -> list[str]:
    """IDs qualificados (`WORK.Tn`) das tasks `in-progress` sem blocker."""
    found = []
    for path in sorted((root / ".harness" / "work").glob("*/tasks.json")):
        doc = _read_json(path)
        if not isinstance(doc, dict):
            continue
        work = doc.get("workId") or path.parent.name
        for task in doc.get("tasks") or []:
            if isinstance(task, dict) and task.get("status") == "in-progress" and not task.get("blocker"):
                tid = str(task.get("id"))
                # O schema aceita `T1` e `WORK-1.T1`; não qualifica de novo o que já vem qualificado.
                found.append(tid if "." in tid else f"{work}.{tid}")
    return found


def _counters(root: Path) -> dict:
    doc = _read_json(root / COUNTER_REL)
    return {k: v for k, v in doc.items() if isinstance(v, int)} if isinstance(doc, dict) else {}


def _save_counters(root: Path, counters: dict) -> None:
    path = root / COUNTER_REL
    if counters:
        _fsx.write_atomic(path, json.dumps(counters, indent=2, sort_keys=True) + "\n")
    elif path.exists():
        path.unlink()


def decide(event: dict, check=None, latest=None) -> dict:
    """`check(root, manifest) -> Verdict` e `latest(root, task_id) -> Path | None`
    entram por parâmetro; em produção são `core.lib.evidence` (1A)."""
    root = Path(event["session"]["projectDir"])
    profile = _profile(root)
    if (profile.get("components") or {}).get("stopGate") is False:
        return _result("allow")
    limit = (profile.get("limits") or {}).get("stopReentries", DEFAULT_REENTRIES)

    tasks = in_progress_tasks(root)
    failing: list[tuple[str, str]] = []
    if tasks and (check is None or latest is None):
        from core.lib import evidence  # sem o módulo, o import falha e o fail-closed bloqueia

        check = check or evidence.check
        latest = latest or evidence.latest
    for task_id in tasks:
        manifest = latest(root, task_id)
        code = "no-manifest" if manifest is None else check(root, manifest).code
        if code != "fresh":
            failing.append((task_id, code))

    if not failing:
        _save_counters(root, {})
        return _result("allow")

    counters = {t: _counters(root).get(t, 0) + 1 for t, _ in failing}
    _save_counters(root, counters)
    listed = failing[:MAX_LISTED]
    what = "; ".join(f"{t} em andamento sem gate verde na árvore atual ({c})" for t, c in listed)
    if len(failing) > MAX_LISTED:
        what += f"; +{len(failing) - MAX_LISTED}"
    first = listed[0][0]
    block_cmd = f"harness task block {first} --reason …"
    if max(counters[t] for t, _ in listed) >= limit:
        instead = f"já houve {limit} bloqueios seguidos: registre o blocker com `{block_cmd}` para poder encerrar"
    else:
        instead = f"rode `harness gate {first}`; se não der para resolver, `{block_cmd}`"
    return _result("block", {"what": what, "why": WHY, "instead": instead})
