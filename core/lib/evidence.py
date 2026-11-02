"""Leitura e frescor da evidência do gate (spec 1A; HG §3.7). Consumido pela 1B (`task done`) e pela 1C (Stop hook).

`check` só devolve `fresh` quando o manifesto é válido, `result == pass`, os
hashes de log e relatório conferem, o perfil é o mesmo e a árvore é a mesma.
Ordem dos testes: integridade (manifesto, log, relatório) → resultado →
perfil → árvore. O perfil vem antes da árvore porque `profile.json` também
entra no hash da árvore, e "perfil mudou" é o diagnóstico mais útil.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.lib import fsx, profile, schema, tree
from core.lib.work import split_id

RUNS_REL = ".harness/runs"

CODES = ("fresh", "not-pass", "sensor-absent", "stale-tree", "stale-profile",
         "log-tampered", "report-tampered", "invalid-manifest")


@dataclass
class Verdict:
    ok: bool
    code: str
    reason: str


def _matches(manifest: dict, task_id: str) -> bool:
    want_work, want_local = split_id(task_id)
    try:
        got_work, got_local = split_id(manifest.get("taskId", ""))
    except ValueError:
        return False
    got_work = got_work or manifest.get("workId")
    return got_local == want_local and (want_work is None or want_work == got_work)


def manifests(root: str | Path, task_id: str) -> list[tuple[dict, Path]]:
    """Manifestos legíveis da task, do mais antigo ao mais novo (attempt, runId).
    Prefira o ID qualificado: com `T5` puro entram os T5 de todos os itens de trabalho."""
    out = []
    for p in sorted((Path(root) / RUNS_REL).glob("*/manifest.json")):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and _matches(doc, task_id):
            out.append((doc, p))
    out.sort(key=lambda item: (item[0].get("attempt", 0) if isinstance(item[0].get("attempt"), int) else 0,
                               str(item[0].get("runId", ""))))
    return out


def latest(root: str | Path, task_id: str) -> Path | None:
    """O manifesto de maior `attempt` da task, ou None."""
    found = manifests(root, task_id)
    return found[-1][1] if found else None


def check(root: str | Path, manifest_path: str | Path) -> Verdict:
    root = Path(root)
    mp = Path(manifest_path)
    if not mp.is_absolute():
        mp = root / mp
    try:
        doc = json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Verdict(False, "invalid-manifest", f"manifesto ilegível: {exc}")
    errors = schema.validate(doc, "run-manifest")
    if errors:
        return Verdict(False, "invalid-manifest", f"manifesto fora do schema run-manifest: {errors[0]}")

    for c in doc["checks"]:
        log = c.get("log")
        if log and not _same(root, log["path"], log["sha256"]):
            return Verdict(False, "log-tampered", f"o log de {c['name']} ({log['path']}) não confere com o sha256 do manifesto")
        rep = c.get("report")
        if rep and not _same(root, rep["path"], rep["sha256"]):
            return Verdict(False, "report-tampered", f"o relatório de {c['name']} ({rep['path']}) não confere com o sha256 do manifesto")

    if doc["result"] == "sensor-absent":
        names = ", ".join(c["name"] for c in doc["checks"] if c["status"] in ("absent", "unavailable"))
        return Verdict(False, "sensor-absent", f"o gate não rodou: sensor ausente ({names})")
    if doc["result"] != "pass":
        return Verdict(False, "not-pass", f"o resultado do gate foi {doc['result']}")

    if profile.sha256(root) != doc["inputs"]["profileSha256"]:
        return Verdict(False, "stale-profile", f"{profile.PROFILE_REL} mudou depois do gate")
    now = tree.compute(root, tuple(doc["inputs"]["treeExcludes"]))
    if now != doc["inputs"]["tree"]:
        return Verdict(False, "stale-tree", f"a árvore mudou depois do gate (era {doc['inputs']['tree'][:7]}, agora {now[:7]})")
    return Verdict(True, "fresh", f"gate {doc['runId']} verde na árvore atual {now[:7]}")


def _same(root: Path, rel: str, sha: str) -> bool:
    try:
        return fsx.sha256_file(root / rel) == sha
    except OSError:
        return False
