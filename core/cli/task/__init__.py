"""`harness task done|block|status` (trilha 1B; componentes S2, M2).

Únicos escritores de `tasks.json`, do bloco de evidência de `validation.md` e
dos blocos do STATE (ADR-0003). `task done` NÃO roda o gate: só aceita um
manifesto `pass` fresco (decisão de 01/11/2026, spec 1B). `task freeze` é da 3A.

`data`: done → {task, manifest, runId, tree}; block → {task}; status → {tasks}.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from core.cli import state as state_mod
from core.cli.harness import Result, not_implemented
from core.cli.task import journal, validation
from core.lib import evidence, fsx, work

MAX_LINE = 200
GIT_ADD_LIMIT = 15


def _cut(s: str) -> str:
    return s if len(s) <= MAX_LINE else s[:MAX_LINE - 1] + "…"


def _res(status: str, lines: list[str], next_: str | None = None, data: dict | None = None,
         code: str | None = None, **kw) -> Result:
    errors = [{"code": code, "message": lines[0]}] if code else []
    return Result(status, [_cut(ln) for ln in lines], next=next_, data=data or {}, errors=errors, **kw)


def run(args) -> Result:
    from core.cli.gate import find_root
    root = find_root(Path.cwd())
    name = args.command
    if name == "task done":
        return task_done(root, args.id)
    if name == "task block":
        return task_block(root, args.id, args.reason, args.needs)
    if name == "task status":
        return task_status(root, args.id)
    return not_implemented(name, "3A")


def _usage(cmd: str, exc: Exception) -> Result:
    return _res("usage", [f"TASK {cmd}  {exc}"],
                "Confira o ID em .harness/work/<ITEM>/tasks.json (ex.: T5 ou PAG-12.T5) e rode de novo.", code="USAGE")


def _busy(cmd: str, qid: str) -> Result:
    return _res("refused", [f"TASK {cmd} {qid}  outra operação segura o lock do item de trabalho"],
                "Espere a outra operação `harness task` terminar e rode de novo. Se nenhuma estiver rodando, "
                "apague .harness/work/<ITEM>/.journal/lock.", code="LOCKED")


def _conflict(cmd: str, qid: str, exc: Exception) -> Result:
    return _res("refused", [f"TASK {cmd} {qid}  tasks.json mudou durante a operação ({exc})"],
                f"Nada foi gravado. Rode `harness task {cmd.lower()} {qid}` de novo.", code="REVISION")


def _git_next(root: Path, ref: work.TaskRef) -> str:
    title = ref.task["title"].replace('"', "'")
    try:
        out = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                             capture_output=True, check=True).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.CalledProcessError):
        return f"Faça o commit atômico da task: git commit -m \"{ref.qualified_id}: {title}\""
    parts = out.split("\0")
    files: list[str] = []
    i = 0
    while i < len(parts):
        rec = parts[i]
        i += 1
        if len(rec) < 4:
            continue
        if rec[0] in "RC":
            i += 1  # o caminho de origem vem no registro seguinte
        path = rec[3:]
        # O lock é removido quando o `task done` sai; um `git add` dele faria o comando inteiro falhar.
        if not path.startswith(".harness/runs/") and not path.endswith(f"/{journal.JOURNAL_DIR}/lock"):
            files.append(path)
    add = "-A" if (not files or len(files) > GIT_ADD_LIMIT) else " ".join(shlex.quote(f) for f in files)
    msg = shlex.quote(ref.qualified_id + ": " + ref.task["title"])
    return f"git add {add} && git commit -m {msg}"


def _sensor_reasons(manifest: dict) -> str:
    out = []
    for c in manifest.get("checks", []):
        if c.get("status") in ("absent", "unavailable"):
            reason = (c.get("absent") or {}).get("reason") or c.get("status")
            out.append(f"{c['name']}: {reason}")
    return "; ".join(out) or "sem detalhe no manifesto"


def task_done(root: str | Path, task_id: str, check=evidence.check, latest=evidence.latest) -> Result:
    root = Path(root).resolve()
    try:
        ref = work.find_task(root, task_id)
    except (ValueError, LookupError) as exc:
        return _usage("done", exc)
    qid = ref.qualified_id
    try:
        with journal.locked(ref.work_dir):
            return _done_locked(root, task_id, ref, check, latest)
    except journal.Busy:
        return _busy("done", qid)
    except journal.Conflict as exc:
        return _conflict("done", qid, exc)


def _done_locked(root: Path, task_id: str, ref: work.TaskRef, check, latest) -> Result:
    qid = ref.qualified_id
    notes = journal.reconcile(root, ref.work_dir, check)
    ref = work.find_task(root, qid)
    task = ref.task
    status = task["status"]
    if status == "done":
        run_id = (task.get("evidence") or {}).get("runId", "?")
        return _res("refused", [*notes, f"TASK done {qid}  já concluída em {run_id}"],
                    "Nada a fazer. Para a próxima task: `harness task status`.", code="ALREADY_DONE")
    if status == "blocked":
        return _res("refused", [*notes, f"TASK done {qid}  a task está blocked: {task.get('blocker', {}).get('reason', '?')}"],
                    "Remova o blocker (edite o status em tasks.json depois que a causa for resolvida) e rode de novo.",
                    code="BLOCKED")
    rerun = f"rode harness gate {qid}"
    mp = latest(root, qid)
    if mp is None:
        return _res("refused", [*notes, f"TASK done {qid}  nenhum manifesto do gate encontrado"], rerun, code="NO_MANIFEST")
    verdict = check(root, mp)
    manifest = json.loads(Path(mp).read_text(encoding="utf-8")) if Path(mp).is_file() else {}
    if verdict.code == "sensor-absent":
        return _res("sensor-absent", [*notes, f"TASK done {qid}  sensor ausente: {_sensor_reasons(manifest)}"],
                    "Sem sensor não há aceite: instale/declare o sensor no perfil, ou registre `harness task block` "
                    "com o que falta.", code="SENSOR_ABSENT")
    if not verdict.ok:
        return _res("refused", [*notes, f"TASK done {qid}  {verdict.reason}"], rerun, code=verdict.code.upper().replace("-", "_"))

    checks = task["dod"].get("checks") or []
    if checks:
        label = qid
        problem = validation.verify(validation.read(ref.work_dir), (qid, ref.local_id), checks,
                                    manifest["inputs"]["tree"], label)
        if problem:
            return _res("refused", [*notes, f"TASK done {qid}  {problem}"],
                        "Corrija a seção Verifier em validation.md (ou rode o verifier de novo) e repita `harness task done`.",
                        code="VERIFIER")

    mrel = Path(mp).resolve().relative_to(root).as_posix()
    entry = {"taskId": qid, "runId": manifest["runId"], "manifest": mrel,
             "manifestSha256": fsx.sha256_file(mp), "attempt": manifest["attempt"],
             "tree": manifest["inputs"]["tree"], "at": journal.now()}
    expected = ref.doc.get("revision", 0)
    j = journal.new_journal(entry)
    journal.write_journal(ref.work_dir, j)
    journal.crash_point("after-journal")
    journal.finish(root, ref.work_dir, j, entry, expected)
    tree7 = entry["tree"][:7]
    return _res("ok", [*notes, f"TASK done {qid}  OK  run={entry['runId']} tree={tree7}"],
                _git_next(root, ref),
                {"task": qid, "manifest": mrel, "runId": entry["runId"], "tree": entry["tree"]})


def task_block(root: str | Path, task_id: str, reason: str, needs: str | None = None) -> Result:
    root = Path(root).resolve()
    reason = " ".join((reason or "").split())
    if not reason:
        return _usage("block", ValueError("--reason vazio"))
    try:
        ref = work.find_task(root, task_id)
    except (ValueError, LookupError) as exc:
        return _usage("block", exc)
    qid = ref.qualified_id
    try:
        with journal.locked(ref.work_dir):
            notes = journal.reconcile(root, ref.work_dir)
            ref = work.find_task(root, qid)
            if ref.task["status"] == "done":
                return _res("refused", [*notes, f"TASK block {qid}  a task já está done"],
                            "Task concluída não recebe blocker. Se algo quebrou, abra uma task nova.", code="ALREADY_DONE")
            expected = ref.doc.get("revision", 0)
            blocker = {"reason": reason, "at": journal.now()}
            if needs:
                blocker["needs"] = " ".join(needs.split())
            ref.task["status"] = "blocked"
            ref.task["blocker"] = blocker
            ref.task["updatedAt"] = blocker["at"]
            fresh = work.load_tasks(ref.work_dir / "tasks.json")
            if fresh.get("revision", 0) != expected:
                raise journal.Conflict(f"revision {expected} → {fresh.get('revision', 0)}")
            journal.write_tasks(ref.work_dir, ref.doc, expected + 1)
            line = f"- {qid} {blocker['at'][:10]}: {reason}" + (f" (precisa: {blocker['needs']})" if needs else "")
            state_mod.add_blocker(root, line)
    except journal.Busy:
        return _busy("block", qid)
    except journal.Conflict as exc:
        return _conflict("block", qid, exc)
    return _res("ok", [*notes, f"TASK block {qid}  blocked: {reason}"],
                "O Stop gate está liberado para esta task. Quando a causa for resolvida, volte o status para "
                "todo/in-progress em tasks.json.", {"task": qid})


def _last_gate(root: Path, qid: str) -> dict | None:
    mp = evidence.latest(root, qid)
    if mp is None:
        return None
    try:
        m = json.loads(mp.read_text(encoding="utf-8"))
        return {"result": m["result"], "tree": m["inputs"]["tree"][:7], "attempt": m["attempt"]}
    except (OSError, ValueError, KeyError):
        return None


def task_status(root: str | Path, task_id: str | None = None) -> Result:
    root = Path(root).resolve()
    notes = journal.reconcile_all(root)
    rows: list[dict] = []
    try:
        if task_id:
            refs = [work.find_task(root, task_id)]
            docs = [(r.doc, r.task) for r in refs]
        else:
            docs = []
            for f in sorted((root / work.WORK_REL).glob("*/tasks.json")):
                doc = work.load_tasks(f)
                docs += [(doc, t) for t in doc["tasks"]]
    except (ValueError, LookupError) as exc:
        return _usage("status", exc)
    for doc, t in docs:
        qid = f"{doc['workId']}.{work.split_id(t['id'])[1]}"
        b = t.get("blocker")
        rows.append({"id": qid, "status": t["status"], "gate": _last_gate(root, qid),
                     "blocker": b["reason"] if b else None})
    if not rows:
        return _res("ok", [*notes, "TASK status  nenhuma task em .harness/work/*/tasks.json"],
                    "Escreva o tasks.json do item de trabalho e confira com `harness validate tasks <arquivo>`.",
                    {"tasks": []})
    lines = []
    for r in rows:
        g = r["gate"]
        gate = f"{g['result']} tree={g['tree']} attempt={g['attempt']}" if g else "sem gate"
        lines.append(f"{r['id']} · {r['status']} · {gate}" + (f" · blocker: {r['blocker']}" if r["blocker"] else ""))
    return _res("ok", [*notes, *lines], data={"tasks": rows})
