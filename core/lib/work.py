"""Leitura das tasks em `.harness/work/<WORK>/tasks.json` (somente leitura; só `harness task` escreve)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from core.lib import schema

WORK_REL = ".harness/work"
TASK_ID_RE = re.compile(r"^(?:([A-Z][A-Z0-9]*-\d+)\.)?(T\d+)$")


@dataclass
class TaskRef:
    work_dir: Path
    doc: dict
    task: dict

    @property
    def work_id(self) -> str:
        return self.doc["workId"]

    @property
    def local_id(self) -> str:
        return split_id(self.task["id"])[1]

    @property
    def qualified_id(self) -> str:
        return f"{self.work_id}.{self.local_id}"


def split_id(task_id: str) -> tuple[str | None, str]:
    """`PAG-12.T5` → (`PAG-12`, `T5`); `T5` → (None, `T5`). `ValueError` se o formato é outro."""
    m = TASK_ID_RE.match(task_id)
    if not m:
        raise ValueError(f"ID de task inválido: {task_id!r} (use T5 ou PAG-12.T5)")
    return m.group(1), m.group(2)


def load_tasks(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.as_posix()}: JSON inválido: {exc}") from exc
    errors = schema.validate(doc, "tasks")
    if errors:
        raise ValueError(f"{path.as_posix()} não passa no schema tasks: " + "; ".join(errors))
    return doc


def find_task(root: str | Path, task_id: str) -> TaskRef:
    """Localiza a task. `LookupError` se não existe ou se `T5` puro é ambíguo;
    `ValueError` se o ID é malformado ou um tasks.json é inválido."""
    root = Path(root)
    work_id, local = split_id(task_id)
    base = root / WORK_REL
    files = [base / work_id / "tasks.json"] if work_id else sorted(base.glob("*/tasks.json"))
    hits: list[TaskRef] = []
    for f in files:
        if not f.is_file():
            continue
        doc = load_tasks(f)
        for task in doc["tasks"]:
            if split_id(task["id"])[1] == local:
                hits.append(TaskRef(f.parent, doc, task))
    if not hits:
        where = f"{WORK_REL}/{work_id}/tasks.json" if work_id else f"{WORK_REL}/*/tasks.json"
        raise LookupError(f"task {task_id} não encontrada em {where}")
    if len(hits) > 1:
        ids = ", ".join(h.qualified_id for h in hits)
        raise LookupError(f"task {task_id} é ambígua: {ids}. Use o ID qualificado.")
    return hits[0]
