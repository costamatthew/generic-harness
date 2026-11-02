"""Carrega um módulo de `adapters/<ferramenta>/` pelo caminho.

O diretório `adapters/claude-code` tem hífen e não é um pacote importável; o
núcleo o enxerga só por aqui, para continuar sem depender do adaptador (HG §1.4).
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

ADAPTERS_DIR = Path(__file__).resolve().parents[2] / "adapters"
_SAFE = re.compile(r"^[a-z][a-z0-9_-]*$")


def load(adapter: str, module: str, adapters_dir: Path = ADAPTERS_DIR) -> ModuleType:
    if not _SAFE.match(adapter) or not _SAFE.match(module):
        raise ImportError(f"nome de adaptador ou módulo inválido: {adapter}/{module}")
    path = adapters_dir / adapter / f"{module}.py"
    if not path.is_file():
        raise ImportError(f"adaptador '{adapter}' sem o módulo {module}.py (esperado em {path})")
    name = f"harness_adapter_{adapter.replace('-', '_')}_{module}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
