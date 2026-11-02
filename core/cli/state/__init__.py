"""`harness state [--handoff <texto>]` e os blocos gerenciados do STATE.md (trilha 1B; componente M1).

STATE.md fica em `.harness/STATE.md`. O CLI escreve só nos blocos
`handoff` e `tasks` e na seção Blockers; o resto do arquivo é da pessoa e do
agente e é preservado byte a byte. `data` = {"handoff", "blockers"}.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.cli.harness import Result
from core.lib import blocks, fsx, work

STATE_REL = ".harness/STATE.md"
TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "STATE.md"
BLOCKERS_HEADING = "## Blockers"
NO_BLOCKERS = "- Nenhum."

# Usado só se core/templates/STATE.md (1D) não estiver no pacote vendorizado.
FALLBACK = """# STATE

> Memória de trabalho da feature (cap. 4 e 17). Os blocos `harness:begin/end` são escritos só pelo CLI.

## Decisões

- AD-001: TODO decisão — TODO motivo — AAAA-MM-DD

## Blockers

- Nenhum.

## Aprendizados

- TODO

## Ideias para depois

- TODO

## Pendentes

- TODO

## Handoff

<!-- harness:begin handoff -->
<!-- harness:end handoff -->

## Tasks

<!-- harness:begin tasks -->
<!-- harness:end tasks -->
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def path(root: str | Path) -> Path:
    return Path(root) / STATE_REL


def _slurp(p: Path) -> str:
    with open(p, encoding="utf-8", newline="") as fh:  # sem traduzir fim de linha (Path.read_text só aceita newline no 3.13)
        return fh.read()


def read(root: str | Path) -> str:
    """Texto do STATE.md; cria o arquivo a partir do template se não existe."""
    p = path(root)
    if p.is_file():
        return _slurp(p)
    try:
        text = _slurp(TEMPLATE)
    except OSError:
        text = FALLBACK
    fsx.write_atomic(p, text)
    return text


def _with_block(text: str, name: str) -> str:
    if blocks.has(text, name):
        return text
    return blocks.append(text, name)


def set_task_line(root: str | Path, qualified_id: str, line: str) -> None:
    """Idempotente: troca a linha da task no bloco `tasks` (ou a acrescenta)."""
    text = _with_block(read(root), "tasks")
    prefix = f"- {qualified_id} "
    cur = [ln for ln in blocks.lines(text, "tasks") if not ln.startswith(prefix)]
    cur.append(f"{prefix}{line}")
    new = blocks.replace(text, "tasks", "\n".join(sorted(cur)))
    if new != text:
        fsx.write_atomic(path(root), new)


def add_blocker(root: str | Path, line: str) -> None:
    """Acrescenta `line` à seção Blockers (sem duplicar; tira o '- Nenhum.')."""
    text = read(root)
    nl = "\r\n" if "\r\n" in text else "\n"
    rows = text.split(nl)
    try:
        start = rows.index(BLOCKERS_HEADING)
    except ValueError:
        sep = "" if text.endswith(nl) else nl
        new = f"{text}{sep}{nl}{BLOCKERS_HEADING}{nl}{nl}{line}{nl}"
    else:
        end = next((i for i in range(start + 1, len(rows)) if rows[i].startswith("## ")), len(rows))
        section = [r for r in rows[start + 1:end] if r.strip() != NO_BLOCKERS]
        if line in section:
            return
        last = max((i for i, r in enumerate(section) if r.startswith("- ")), default=None)
        if last is None:
            while section and not section[-1].strip():
                section.pop()
            section += ["", line, ""]
        else:
            section.insert(last + 1, line)
        if end < len(rows) and section and section[-1].strip():
            section.append("")
        new = nl.join(rows[:start + 1] + section + rows[end:])
    if new != text:
        fsx.write_atomic(path(root), new)


def open_blockers(text: str) -> list[str]:
    rows = text.splitlines()
    try:
        start = rows.index(BLOCKERS_HEADING)
    except ValueError:
        return []
    out = []
    for r in rows[start + 1:]:
        if r.startswith("## "):
            break
        if r.startswith("- ") and r.strip() != NO_BLOCKERS:
            out.append(r[2:].strip())
    return out


def in_progress(root: Path) -> list[str]:
    out = []
    for f in sorted((root / work.WORK_REL).glob("*/tasks.json")):
        try:
            doc = work.load_tasks(f)
        except ValueError:
            continue
        out += [f"{doc['workId']}.{work.split_id(t['id'])[1]} {t['title']}" for t in doc["tasks"]
                if t["status"] == "in-progress"]
    return out


def run(args) -> Result:
    from core.cli.gate import find_root
    return state(find_root(Path.cwd()), getattr(args, "handoff", None))


def state(root: str | Path, handoff: str | None = None) -> Result:
    root = Path(root).resolve()
    try:
        text = read(root)
        if handoff is not None:
            handoff = " ".join(handoff.split())
            if not handoff:
                return Result("usage", ["STATE  --handoff vazio"],
                              next="Passe um texto: `harness state --handoff \"o que foi feito e o próximo passo\"`.",
                              errors=[{"code": "USAGE", "message": "handoff vazio"}])
            text2 = _with_block(text, "handoff")
            text2 = blocks.replace(text2, "handoff", f"{now_utc()} · {handoff}")
            if text2 != text:
                fsx.write_atomic(path(root), text2)
            text = text2
    except blocks.BlockError as exc:
        return Result("refused", [f"STATE  {exc}"[:200]], next="Corrija os marcadores em .harness/STATE.md e rode de novo.",
                      errors=[{"code": "BLOCK", "message": str(exc), "where": STATE_REL}])
    except OSError as exc:
        return Result("error", [f"STATE  não consegui ler/gravar {STATE_REL}: {exc}"[:200]],
                      next="Confira as permissões de .harness/ e rode de novo.",
                      errors=[{"code": "IO", "message": str(exc)}])
    try:
        current = blocks.get(text, "handoff") or ""
    except blocks.BlockError:
        current = ""
    blockers = open_blockers(text)
    summary = [f"STATE  handoff: {current or '(vazio)'}"[:200]]
    summary += [f"  blocker: {b}"[:200] for b in blockers] or ["  blockers: nenhum"]
    prog = in_progress(root)
    summary += [f"  em andamento: {t}"[:200] for t in prog] or ["  em andamento: nenhuma"]
    verb = "Handoff gravado. " if handoff is not None else ""
    return Result("ok", summary, next=(verb + "Siga com a próxima task ou encerre a sessão.").strip(),
                  data={"handoff": current, "blockers": blockers})
