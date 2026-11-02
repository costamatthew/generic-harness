"""Bloco de evidência e parser da seção Verifier de `validation.md` (trilha 1B; formato da 1D).

O bloco `evidence` é escrito só por `harness task done`. A seção Verifier é
escrita pelo `harness-verifier`; aqui só é lida (S7: check sem evidência =
não atendido, cobrado por código).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from core.lib import blocks, fsx

VALIDATION = "validation.md"
BLOCK = "evidence"
HEADING_RE = re.compile(r"^###\s+Verifier\s+(\S+)\s*$")
TREE_RE = re.compile(r"^-\s*tree:\s*([0-9a-fA-F]+)\s*$")
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|(.+)\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$")
FILE_LINE_RE = re.compile(r"^\S+:\d+$")
EXEC_RE = re.compile(r"^exec: .+ exit=(\d+)$")
ATENDE = "atende"


def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split())


@dataclass
class Row:
    num: int
    check: str
    result: str
    evidence: str


def parse_verifier(text: str, task_ids: tuple[str, ...]) -> tuple[str | None, list[Row]] | None:
    """(tree, linhas) da seção `### Verifier <ID>` cujo ID está em `task_ids`; None se não há seção."""
    rows = text.splitlines()
    start = next((i for i, r in enumerate(rows) if (m := HEADING_RE.match(r)) and m.group(1) in task_ids), None)
    if start is None:
        return None
    tree = None
    out: list[Row] = []
    for r in rows[start + 1:]:
        if r.startswith("#"):
            break
        if (m := TREE_RE.match(r.strip())) and tree is None:
            tree = m.group(1).lower()
        elif (m := ROW_RE.match(r.strip())):
            out.append(Row(int(m.group(1)), m.group(2).strip(), _norm(m.group(3)), m.group(4).strip().strip("`")))
    return tree, out


def verify(text: str, task_ids: tuple[str, ...], checks: list[str], manifest_tree: str, label: str) -> str | None:
    """None se a seção Verifier está completa; senão a frase (o quê, por quê, o que fazer) com a linha que falta."""
    where = f"{VALIDATION}, seção '### Verifier {label}'"
    parsed = parse_verifier(text, task_ids)
    if parsed is None:
        return (f"a task tem dod.checks mas {where} não existe. Chame o harness-verifier com contexto limpo "
                f"e copie a resposta dele para {VALIDATION}.")
    tree, rows = parsed
    want = manifest_tree[:7].lower()
    if tree is None:
        return f"{where} não tem a linha '- tree: {want}'. Peça ao verifier a saída no formato fixo."
    if tree != want:
        return (f"{where} verificou a árvore {tree}, mas o gate verde é da árvore {want}. "
                f"O código mudou depois do verifier: rode harness gate e chame o verifier de novo.")
    for i, check in enumerate(checks, 1):
        row = next((r for r in rows if _norm(r.check) == _norm(check)), None)
        if row is None:
            return f"{where} não tem linha para o check {i} ('{check}'). Todo dod.checks precisa de uma linha."
        if row.result != ATENDE:
            return (f"check {i} ('{check}') está '{row.result}' em {where}. Corrija o código, rode harness gate "
                    f"e chame o verifier de novo.")
        m = EXEC_RE.match(row.evidence)
        if not (FILE_LINE_RE.match(row.evidence) or (m and m.group(1) == "0")):
            got = row.evidence if len(row.evidence) <= 40 else row.evidence[:39] + "…"
            # Duas linhas: a instrução não pode sumir no corte de linha longa (P15).
            return (f"check {i} ('{check}') diz 'atende' sem evidência válida em {where} (veio '{got}').\n"
                    f"A célula Evidência aceita um valor só, sem prosa nem lista: 'arquivo:linha' ou "
                    f"'exec: <comando> exit=0'. Peça ao verifier para refazer a linha com uma única referência.")
    return None


def read(work_dir: Path) -> str:
    p = work_dir / VALIDATION
    if not p.is_file():
        return ""
    with open(p, encoding="utf-8", newline="") as fh:
        return fh.read()


def evidence_line(entry: dict) -> str:
    return (f"- run={entry['runId']} · {entry['taskId']} · attempt={entry['attempt']} · tree={entry['tree'][:7]} · "
            f"manifest={entry['manifest']} · sha256={entry.get('manifestSha256', '-')} · {entry['at']}")


def add_evidence(work_dir: Path, entry: dict) -> None:
    """Idempotente por runId: um marcador `run=<runId>` no bloco impede duplicar."""
    p = work_dir / VALIDATION
    text = read(work_dir)
    if not text:
        text = f"# Validação {entry['taskId'].split('.')[0]}\n"
    if not blocks.has(text, BLOCK):
        text = blocks.append(text, BLOCK)
    cur = blocks.lines(text, BLOCK)
    if any(f"run={entry['runId']} " in ln + " " for ln in cur):
        return
    new = blocks.replace(text, BLOCK, "\n".join([*cur, evidence_line(entry)]))
    fsx.write_atomic(p, new)


def has_run(work_dir: Path, run_id: str) -> bool:
    text = read(work_dir)
    try:
        cur = blocks.lines(text, BLOCK) if text else []
    except blocks.BlockError:
        return False
    return any(f"run={run_id} " in ln + " " for ln in cur)
