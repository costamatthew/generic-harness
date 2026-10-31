"""ADR-0004: o que é vendorizado (core/, adapters/) importa só a biblioteca padrão."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VENDORED = sorted(p for d in ("core", "adapters") for p in (ROOT / d).rglob("*.py"))
LOCAL = {"core", "adapters"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("path", VENDORED, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_only_stdlib(path):
    foreign = _imports(path) - set(sys.stdlib_module_names) - LOCAL
    assert not foreign, f"{path.relative_to(ROOT)} importa fora da stdlib: {sorted(foreign)}"
