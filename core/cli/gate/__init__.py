"""`harness gate <ID>` (trilha 1A; componente S1, HG §3.2).

Lê a DoD da task, confere os comandos no perfil, roda cada um, lê o JUnit e
grava um manifesto por tentativa em `.harness/runs/<runId>/manifest.json`,
associado ao hash da árvore (`sha256-worktree-v0`). Spec: docs/plan/etapa-1/1A.md.

`data` = {"manifest", "runId", "result", "tree"}.
"""

from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from core.cli.harness import DEFAULT_SUMMARY_LINES, Result
from core.lib import evidence, fsx, junit, profile, schema, tree, work
from core.lib.version import HARNESS_VERSION

RUNS_REL = evidence.RUNS_REL
TOOL_MISSING_EXITS = {127} | ({9009} if os.name == "nt" else set())
RESULT_TO_STATUS = {"pass": "ok", "fail": "fail", "sensor-absent": "sensor-absent", "error": "error"}
WORD = {"pass": "PASS", "fail": "FAIL", "absent": "ABSENT", "unavailable": "ABSENT", "error": "FAIL"}
MAX_LINE = 200  # cli-output: summary.items.maxLength


def run(args) -> Result:
    if getattr(args, "prove_sensor", False):
        return Result(
            "not-implemented",
            ["harness gate --prove-sensor: ainda não implementado (trilha 2E)"],
            next=f"Rode `harness gate {args.id}` sem --prove-sensor; a prova por mutação chega com a trilha 2E.",
        )
    result, _ = run_gate(find_root(Path.cwd()), args.id)
    return result


def find_root(start: Path) -> Path:
    """Primeiro ancestral com `.harness/profile.json`; sem nenhum, o próprio `start`."""
    start = start.resolve()
    for d in (start, *start.parents):
        if (d / profile.PROFILE_REL).is_file():
            return d
    return start


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def _usage(msg: str, next_: str) -> tuple[Result, None]:
    return Result("usage", [f"GATE  {msg}"[:MAX_LINE]], next=next_,
                  errors=[{"code": "USAGE", "message": msg}]), None


def run_gate(root: str | Path, task_id: str) -> tuple[Result, Path | None]:
    """O mesmo que o subcomando, chamável no próprio processo. Devolve (Result, caminho do manifesto)."""
    root = Path(root).resolve()
    try:
        work.split_id(task_id)
    except ValueError as exc:
        return _usage(str(exc), "Passe o ID como está em tasks.json: `harness gate T5` ou `harness gate PAG-12.T5`.")
    try:
        tree.require_repo(root)
    except tree.NotAGitRepo as exc:
        return _usage(str(exc), "Rode `git init` na raiz do projeto e chame o gate de novo; sem git não há hash da árvore.")
    try:
        prof = profile.load(root)
    except FileNotFoundError:
        return _usage(f"{profile.PROFILE_REL} não existe em {root.as_posix()}",
                      "Rode o gate na raiz do projeto hospedeiro; se o harness não está instalado, rode `harness apply`.")
    except ValueError as exc:
        return Result("refused", [f"GATE {task_id}  REFUSED  perfil inválido"], logs=[],
                      next="Não edite o perfil: peça à pessoa para corrigi-lo (`harness validate profile .harness/profile.json`).",
                      errors=[{"code": "PROFILE", "message": str(exc)[:2000]}]), None
    try:
        ref = work.find_task(root, task_id)
    except LookupError as exc:
        return _usage(str(exc), "Confira o ID com `harness task status`; se houver mais de um item de trabalho, use o ID qualificado.")
    except ValueError as exc:
        return Result("refused", [f"GATE {task_id}  REFUSED  tasks.json inválido"],
                      next="Não edite tasks.json à mão: só `harness task` escreve nele. Registre um blocker se ele estiver corrompido.",
                      errors=[{"code": "TASKS", "message": str(exc)[:2000]}]), None

    names = ref.task["dod"]["commands"]
    cmds = {n: profile.resolve_command(prof, n) for n in names}
    timeouts = [int((c or {}).get("timeoutSec", profile.DEFAULT_TIMEOUT_SEC)) for c in cmds.values()]
    lock = fsx.Lock(root / RUNS_REL / f"{ref.qualified_id}.lock", stale_after=max(timeouts) * len(timeouts))
    try:
        lock.acquire()
    except fsx.LockHeld:
        return Result("refused", [f"GATE {task_id}  REFUSED  outro gate desta task está rodando"],
                      next=(f"Espere o outro gate terminar e leia o resultado dele em {RUNS_REL}/; não rode dois gates "
                            f"da mesma task ao mesmo tempo (lock {RUNS_REL}/{ref.qualified_id}.lock)."),
                      errors=[{"code": "LOCKED", "message": str(lock.path)}]), None
    try:
        return _gate(root, task_id, ref, prof, names, cmds, lock.warning)
    finally:
        lock.release()


def _precheck(name: str, cmd: dict | None) -> dict | None:
    """Check `absent` se o comando não pode alimentar o gate; None se pode."""
    if cmd is None:
        return {"name": name, "status": "absent", "absent": {"reason": "not-in-profile"}}
    st = cmd["status"]
    if st == "verified":
        return None
    absent: dict = {"reason": "planned" if st == "planned" else "not-approved"}
    origin = cmd.get("origin", "")
    if st == "planned" and origin.startswith("decision:"):
        absent["decidedBy"] = origin.split(":", 1)[1]
    return {"name": name, "status": "absent", "run": cmd["run"], "absent": absent}


def _gate(root: Path, task_id: str, ref: work.TaskRef, prof: dict, names: list[str],
          cmds: dict, lock_warning: str | None) -> tuple[Result, Path | None]:
    excludes = tree.DEFAULT_EXCLUDES
    started = _now()
    runs = root / RUNS_REL
    while True:
        run_id = started.strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
        run_dir = runs / run_id
        try:
            run_dir.mkdir(parents=True)
            break
        except FileExistsError:
            continue
    previous = evidence.manifests(root, ref.qualified_id)
    before = tree.entries(root, excludes)

    pre = [_precheck(n, cmds[n]) for n in names]
    notes: list[str] = []
    if any(pre):
        checks = [p or {"name": n, "status": "skipped", "run": cmds[n]["run"]} for n, p in zip(names, pre)]
    else:
        # Referência de tempo do próprio sistema de arquivos: o relógio dos mtimes
        # pode andar atrás de time.time() (Linux usa um relógio grosso).
        marker = run_dir / ".start"
        marker.write_bytes(b"")
        start_mtime = marker.stat().st_mtime
        marker.unlink()
        checks = [_run_check(root, run_dir, n, cmds[n], start_mtime, notes) for n in names]

    after = tree.entries(root, excludes)
    moved = tree.changed(before, after)
    statuses = {c["status"] for c in checks}
    if statuses & {"absent", "unavailable"}:
        result = "sensor-absent"
    elif "error" in statuses or moved:
        result = "error"
    elif "fail" in statuses:
        result = "fail"
    else:
        result = "pass"

    tree_hex = tree.digest(before)
    manifest = {
        "schema": 0,
        "runId": run_id,
        "attempt": len(previous) + 1,
        "taskId": ref.qualified_id,
        "workId": ref.work_id,
        "mode": "gate",
        "startedAt": _ts(started),
        "finishedAt": _ts(_now()),
        "result": result,
        "inputs": {
            "revision": tree.revision(root),
            "dirty": tree.dirty(root, excludes),
            "tree": tree_hex,
            "treeAlgorithm": tree.ALGORITHM,
            "treeExcludes": list(excludes),
            "profileSha256": profile.sha256(root),
            "harnessVersion": HARNESS_VERSION,
        },
        "environment": _environment(),
        "checks": checks,
    }
    if ref.task.get("requirements"):
        manifest["requirements"] = list(ref.task["requirements"])
    if previous:
        manifest["supersedes"] = previous[-1][0]["runId"]
    problems = schema.validate(manifest, "run-manifest")
    if problems:  # bug do harness: não grava evidência fora do contrato
        return Result("error", [f"GATE {task_id}  manifesto fora do schema run-manifest (bug do harness)"],
                      next="Rode `harness doctor` e registre um blocker com a mensagem de erro.",
                      errors=[{"code": "SCHEMA", "message": p} for p in problems[:10]]), None
    manifest_path = run_dir / "manifest.json"
    fsx.write_atomic(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    return _result(task_id, prof, manifest, _rel(root, manifest_path), moved, notes, lock_warning), manifest_path


def _environment() -> dict:
    system = platform.system().lower()
    env = {"os": system if system in ("linux", "darwin", "windows") else "other",
           "python": platform.python_version()}
    if os.environ.get("CI"):
        env["ci"] = True
    return env


def _run_check(root: Path, run_dir: Path, name: str, cmd: dict, start_mtime: float, notes: list[str]) -> dict:
    timeout = int(cmd.get("timeoutSec", profile.DEFAULT_TIMEOUT_SEC))
    log_path = run_dir / f"{name}.log"
    check: dict = {"name": name, "status": "error", "run": cmd["run"]}
    t0 = _now()
    m0 = time.monotonic()
    code, timed_out = None, False
    with open(log_path, "wb") as log:
        try:
            code, timed_out = _execute(cmd["run"], root / cmd.get("cwd", "."), log, timeout)
        except FileNotFoundError as exc:  # shell ou cwd inexistente
            log.write(f"[harness] não foi possível executar: {exc}\n".encode())
            if not (root / cmd.get("cwd", ".")).is_dir():
                notes.append(f"{name}: cwd {cmd.get('cwd')} não existe")
                code = None
            else:
                code = 127
        except OSError as exc:
            log.write(f"[harness] erro ao executar: {exc}\n".encode())
            notes.append(f"{name}: erro ao executar ({exc.__class__.__name__})")
    check.update(startedAt=_ts(t0), finishedAt=_ts(_now()), durationMs=int((time.monotonic() - m0) * 1000))
    check["exitCode"] = code
    check["log"] = {"path": _rel(root, log_path), "sha256": fsx.sha256_file(log_path)}

    if timed_out:
        check["status"] = "fail"
        notes.append(f"timeout {timeout}s  ({name})")
        return check
    if code is None:
        return check  # status error
    if code in TOOL_MISSING_EXITS or _missing_on_windows(cmd["run"], root / cmd.get("cwd", "."), code):
        check["status"] = "unavailable"
        check["absent"] = {"reason": "tool-missing"}
        return check
    check["status"] = "pass" if code == 0 else "fail"

    if cmd.get("report") and cmd.get("reportFormat") == "junit":
        _read_report(root, run_dir, name, cmd["report"], start_mtime, check, notes)
    return check


def _missing_on_windows(command: str, cwd: Path, code: int | None) -> bool:
    """No Windows, `cmd /c` sai com 1 (não 9009) quando o executável não existe.
    Então, com exit != 0, confere se o primeiro token resolve. Um builtin do cmd que falha
    (`dir x`) vira `tool-missing`: continua não sendo `pass`, e o `task done` recusa do mesmo jeito."""
    if os.name != "nt" or code in (0, None):
        return False
    text = command.strip()
    exe = text[1:].split('"', 1)[0] if text.startswith('"') else (text.split() or [""])[0]
    return bool(exe) and shutil.which(exe) is None and not (cwd / exe).exists()


def _execute(command: str, cwd: Path, log, timeout: int) -> tuple[int | None, bool]:
    """Roda com shell=True; em timeout mata o grupo de processos. Devolve (exit, timed_out)."""
    kwargs: dict = {"shell": True, "cwd": str(cwd), "stdout": log, "stderr": subprocess.STDOUT,
                    "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(command, **kwargs)
    try:
        return proc.wait(timeout=timeout), False
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        proc.wait()
        log.write(f"\n[harness] timeout {timeout}s: processo encerrado\n".encode())
        return None, True


def _read_report(root: Path, run_dir: Path, name: str, report: str, start_mtime: float,
                 check: dict, notes: list[str]) -> None:
    src = root / report
    try:
        mtime = src.stat().st_mtime
    except FileNotFoundError:
        check["status"] = "fail"
        notes.append(f"{name}: relatório ausente ({report})")
        return
    copy = run_dir / f"{name}.junit.xml"
    shutil.copyfile(src, copy)
    fresh = mtime >= start_mtime
    try:
        rep = junit.parse(copy, root)
    except junit.JUnitError as exc:
        check["status"] = "fail"
        notes.append(f"{name}: relatório ilegível ({exc})"[:MAX_LINE])
        return
    data = {"path": _rel(root, copy), "sha256": fsx.sha256_file(copy), "mtimeAfterStart": fresh, **rep.counts()}
    if rep.first_failures:
        data["firstFailures"] = rep.first_failures
    check["report"] = data
    if not fresh:
        check["status"] = "fail"
        notes.append(f"{name}: relatório antigo ({report} não foi reescrito nesta tentativa)")
    elif rep.failures + rep.errors > 0:
        check["status"] = "fail"


# ---- saída -----------------------------------------------------------------

def _result(task_id: str, prof: dict, m: dict, manifest_rel: str, moved: list[str],
            notes: list[str], lock_warning: str | None) -> Result:
    tree7 = m["inputs"]["tree"][:7]
    result = m["result"]
    lines: list[str] = []
    detail: list[str] = []
    skipped = []
    for c in m["checks"]:
        if c["status"] == "skipped":
            skipped.append(c["name"])
            continue
        exit_ = "-" if c.get("exitCode") is None else c["exitCode"]
        dur = c.get("durationMs", 0) / 1000
        lines.append(f"GATE {task_id} {c['name']}  {WORD.get(c['status'], 'FAIL')} exit={exit_}  {dur:.1f}s  tree={tree7}")
        if c["status"] == "absent":
            a = c["absent"]
            why = {"planned": "planned", "not-in-profile": "fora do perfil", "not-approved": "não verificado"}[a["reason"]]
            detail.append(f"  {c['name']}: {why}" + (f" ({a['decidedBy']})" if a.get("decidedBy") else ""))
        rep = c.get("report")
        if rep:
            detail.append(f"tests {rep['tests']}  failed {rep['failures']}  errors {rep['errors']}  skipped {rep['skipped']}")
            detail += [f"  {f['location']}  {f['name']}" for f in rep.get("firstFailures", [])]
    if skipped:
        detail.append("não rodou (sensor ausente): " + ", ".join(skipped))
    detail += notes
    if moved:
        detail.append("a árvore mudou durante o gate: " + ", ".join(moved[:3]) + (" …" if len(moved) > 3 else ""))
    if lock_warning:
        detail.append(lock_warning)

    logs = [c["log"]["path"] for c in m["checks"] if c.get("log")]
    bad_logs = [c["log"]["path"] for c in m["checks"] if c.get("log") and c["status"] != "pass"]
    tail = [f"log: {(bad_logs or logs)[0]}"] if logs else [f"manifest: {manifest_rel}"]

    status = RESULT_TO_STATUS[result]
    if result == "error" and moved:
        status = "refused"
    next_ = _next(task_id, m, moved, bad_logs)

    budget = min(profile.summary_lines(prof), DEFAULT_SUMMARY_LINES) - 1  # a linha → também conta
    room = budget - len(lines) - len(tail)
    if room < len(detail):
        cut = len(detail) - max(room - 1, 0)
        detail = detail[: max(room - 1, 0)] + [f"… (+{cut} linhas no manifesto {manifest_rel})"]
    summary = [s[:MAX_LINE] for s in (lines + detail + tail)][:max(budget, 1)]

    return Result(status, summary, next=next_, logs=logs,
                  data={"manifest": manifest_rel, "runId": m["runId"], "result": result, "tree": m["inputs"]["tree"]})


def _next(task_id: str, m: dict, moved: list[str], bad_logs: list[str]) -> str:
    result = m["result"]
    checks = m["checks"]
    if result == "pass":
        return (f"Gate verde. Conclua com `harness task done {task_id}` sem mudar nenhum arquivo antes "
                "(qualquer mudança na árvore invalida esta evidência).")
    if result == "sensor-absent":
        c = next(c for c in checks if c["status"] in ("absent", "unavailable"))
        reason = c["absent"]["reason"]
        head = "Não improvise outro comando para substituir o sensor. "
        block = f"Registre `harness task block {task_id} --reason \"sensor {c['name']} ausente\" --needs \"...\"`"
        if reason == "planned":
            by = c["absent"].get("decidedBy")
            return head + f"{c['name']} está planned{f' ({by})' if by else ''}: faça antes a task que cria o sensor, ou {block[0].lower() + block[1:]}."
        if reason == "not-approved":
            return head + f"{c['name']} ainda não foi verificado no perfil: peça à pessoa para conferir e marcar `status: verified`, ou {block[0].lower() + block[1:]}."
        if reason == "not-in-profile":
            return head + f"{c['name']} não existe em .harness/profile.json: peça à pessoa para declará-lo, ou {block[0].lower() + block[1:]}."
        return head + f"O executável de {c['name']} não foi encontrado (exit 127): instale a ferramenta ou {block[0].lower() + block[1:]}."
    if result == "error":
        if moved:
            return ("Os comandos alteraram arquivos que entram no hash da árvore, então esta evidência não vale. "
                    "Ponha o que eles geram no .gitignore (ou aponte `report` para .harness/runs/) e rode o gate de novo.")
        return "O harness não conseguiu executar um comando. Leia o log; se não for do seu código, rode `harness doctor` e registre um blocker."
    for c in checks:
        if c["status"] != "fail":
            continue
        rep = c.get("report")
        if rep is None and c.get("exitCode") == 0:
            return (f"{c['name']} saiu 0 sem gravar o JUnit. Confira se o comando grava o relatório no caminho do perfil; "
                    "verde sem relatório não vale.")
        if rep and not rep.get("mtimeAfterStart", True):
            return (f"{c['name']} não reescreveu o relatório nesta tentativa: o arquivo é de um run anterior. "
                    "Confira o caminho do relatório no comando e rode o gate de novo.")
        if rep and rep.get("firstFailures"):
            first = rep["firstFailures"][0]["location"]
            return f"Corrija a primeira falha ({first}) e rode `harness gate {task_id}` de novo. Não edite os testes para passar."
        if c.get("exitCode") is None:
            return f"{c['name']} estourou o timeout. Procure um teste travado no log; não aumente o timeout do perfil."
        log = c["log"]["path"]
        return f"{c['name']} falhou (exit {c['exitCode']}). Leia {log}, corrija e rode `harness gate {task_id}` de novo."
    return f"Leia {bad_logs[0] if bad_logs else 'o manifesto'} e rode `harness gate {task_id}` de novo."
