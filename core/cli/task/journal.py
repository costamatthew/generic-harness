"""Journal, lock e reconciliação do `task done` (trilha 1B; HG §3.7 "Estado e retomada").

`task done` grava tasks.json, validation.md e STATE.md em passos separados. O
journal em `.harness/work/<W>/.journal/<runId>.json` diz o que já foi feito, para
que uma interrupção nunca deixe uma task `done` sem evidência (nem duplique o
bloco ao repetir).

Pontos de falha para teste (a 1G depende deles): com
`HARNESS_TEST_CRASH_AT=<passo>` o processo chama `os._exit(99)` logo depois do
passo. Valores: `after-journal`, `after-tasks`, `after-validation`. Qualquer
outro valor não tem efeito.
"""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from core.cli import state as state_mod
from core.cli.task import validation
from core.lib import evidence, fsx, schema, work

JOURNAL_DIR = ".journal"
CRASH_ENV = "HARNESS_TEST_CRASH_AT"
CRASH_POINTS = ("after-journal", "after-tasks", "after-validation")
LOCK_STALE_SEC = 600


class Conflict(Exception):
    """`revision` de tasks.json mudou durante a operação."""


class Busy(Exception):
    """Outra operação segura o lock do item de trabalho."""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def crash_point(name: str) -> None:
    if name in CRASH_POINTS and os.environ.get(CRASH_ENV) == name:
        os._exit(99)


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.windll.kernel32.GetLastError() == 5  # acesso negado: existe
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def locked(work_dir: Path):
    """Lock por item de trabalho. Um lock cujo dono morreu (crash) é removido."""
    lock = fsx.Lock(work_dir / JOURNAL_DIR / "lock", stale_after=LOCK_STALE_SEC)
    try:
        lock.acquire()
    except fsx.LockHeld:
        m = re.search(r"pid=(\d+)", _read_lock(lock.path))
        if m and not _pid_alive(int(m.group(1))):
            try:
                lock.path.unlink()
            except FileNotFoundError:
                pass
            try:
                lock.acquire()
            except fsx.LockHeld:
                raise Busy(str(lock.path)) from None
        else:
            raise Busy(str(lock.path)) from None
    try:
        yield lock
    finally:
        lock.release()


def _read_lock(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def journal_path(work_dir: Path, run_id: str) -> Path:
    return work_dir / JOURNAL_DIR / f"{run_id}.json"


def write_journal(work_dir: Path, j: dict) -> None:
    fsx.write_atomic(journal_path(work_dir, j["runId"]), json.dumps(j, indent=2, ensure_ascii=False) + "\n")


def new_journal(entry: dict) -> dict:
    return {"taskId": entry["taskId"], "runId": entry["runId"], "manifest": entry["manifest"],
            "manifestSha256": entry["manifestSha256"], "attempt": entry["attempt"], "tree": entry["tree"],
            "at": entry["at"], "steps": {"tasks": False, "validation": False, "state": False}, "complete": False}


def pending(work_dir: Path) -> list[tuple[Path, dict]]:
    out = []
    for p in sorted((work_dir / JOURNAL_DIR).glob("*.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            p.unlink(missing_ok=True)  # journal ilegível não prova nada: a task só vale com tasks.json + evidência
            continue
        if isinstance(j, dict) and not j.get("complete") and "runId" in j and "taskId" in j:
            out.append((p, j))
    return out


def _read_tasks(work_dir: Path) -> dict:
    return work.load_tasks(work_dir / "tasks.json")


def write_tasks_done(work_dir: Path, entry: dict, expected_rev: int) -> None:
    """Passo `tasks`. Relê do disco e recusa se o `revision` não é o que foi lido no início."""
    doc = _read_tasks(work_dir)
    if doc.get("revision", 0) != expected_rev:
        raise Conflict(f"tasks.json estava na revision {expected_rev} e agora está na {doc.get('revision', 0)}")
    local = work.split_id(entry["taskId"])[1]
    task = next(t for t in doc["tasks"] if work.split_id(t["id"])[1] == local)
    task["status"] = "done"
    task.pop("blocker", None)
    task["evidence"] = {"runId": entry["runId"], "attempt": entry["attempt"], "manifest": entry["manifest"],
                        "manifestSha256": entry["manifestSha256"], "tree": entry["tree"]}
    task["updatedAt"] = entry["at"]
    write_tasks(work_dir, doc, expected_rev + 1)


def write_tasks(work_dir: Path, doc: dict, revision: int) -> None:
    doc["revision"] = revision
    errors = schema.validate(doc, "tasks")
    if errors:
        raise ValueError("tasks.json resultante não passa no schema tasks: " + "; ".join(errors))
    fsx.write_atomic(work_dir / "tasks.json", json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def finish(root: Path, work_dir: Path, j: dict, entry: dict, expected_rev: int | None) -> None:
    """Executa os passos que faltam (tasks → validation → state), cada um idempotente, e fecha o journal.
    `expected_rev` é o `revision` lido pelo chamador; None quando o passo `tasks` já está no disco."""
    if expected_rev is not None:
        write_tasks_done(work_dir, entry, expected_rev)
    j["steps"]["tasks"] = True
    write_journal(work_dir, j)
    crash_point("after-tasks")
    validation.add_evidence(work_dir, entry)
    j["steps"]["validation"] = True
    write_journal(work_dir, j)
    crash_point("after-validation")
    state_mod.set_task_line(root, entry["taskId"], f"· done · run={entry['runId']} · tree={entry['tree'][:7]}")
    j["steps"]["state"] = True
    j["complete"] = True
    write_journal(work_dir, j)


def _entry(j: dict) -> dict:
    return {k: j[k] for k in ("taskId", "runId", "manifest", "manifestSha256", "attempt", "tree", "at")}


def reconcile(root: Path, work_dir: Path, check=evidence.check) -> list[str]:
    """Conclui ou descarta os journals incompletos. Chamar com o lock do item de trabalho. Devolve avisos."""
    notes: list[str] = []
    for p, j in pending(work_dir):
        try:
            doc = _read_tasks(work_dir)
            local = work.split_id(j["taskId"])[1]
            task = next((t for t in doc["tasks"] if work.split_id(t["id"])[1] == local), None)
            if task is None:
                raise KeyError(local)
        except (ValueError, KeyError):
            p.unlink(missing_ok=True)
            notes.append(f"journal de {j['taskId']} descartado: a task não existe mais em tasks.json")
            continue
        ev = task.get("evidence") or {}
        if task["status"] == "done" and ev.get("runId") == j["runId"]:
            finish(root, work_dir, j, _entry(j), None)
            notes.append(f"{j['taskId']}: conclusão interrompida retomada (run={j['runId']})")
            continue
        verdict = check(root, j["manifest"])
        sha_ok = False
        try:
            sha_ok = fsx.sha256_file(root / j["manifest"]) == j["manifestSha256"]
        except OSError:
            pass
        if task["status"] in ("todo", "in-progress") and verdict.ok and sha_ok:
            finish(root, work_dir, j, _entry(j), doc.get("revision", 0))
            notes.append(f"{j['taskId']}: conclusão interrompida retomada (run={j['runId']})")
        elif task["status"] not in ("todo", "in-progress"):
            p.unlink(missing_ok=True)
            notes.append(f"journal de {j['taskId']} descartado: a task já está {task['status']} sem este run")
        else:
            p.unlink(missing_ok=True)
            notes.append(f"→ a conclusão de {j['taskId']} foi interrompida e a árvore mudou; rode harness gate {j['taskId']}")
    return notes


def reconcile_all(root: Path, check=evidence.check) -> list[str]:
    notes: list[str] = []
    for tf in sorted((root / work.WORK_REL).glob("*/tasks.json")):
        wd = tf.parent
        if not (wd / JOURNAL_DIR).is_dir() or not pending(wd):
            continue
        try:
            with locked(wd):
                notes += reconcile(root, wd, check)
        except Busy:
            notes.append(f"reconciliação de {wd.name} adiada: outra operação segura o lock")
        except Conflict as exc:
            notes.append(f"reconciliação de {wd.name} recusada: {exc}")
    return notes
