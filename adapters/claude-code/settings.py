"""Merge de `.claude/settings.json` sem perder nada do time (spec 1C, item 1).

O harness acrescenta um handler em `hooks.Stop` e as regras `permissions.deny`
dos insumos de aceite (ADR-0003). Tudo o mais fica como está, na mesma ordem.
Só stdlib.
"""

from __future__ import annotations

import copy
import json

HOOK_NAME = "stop_gate"
MARKER = f"hook {HOOK_NAME} --adapter claude-code"
TIMEOUT = 60

# `Write(path)` nunca casa (fatos §2); `Edit(...)` vale também para Write
# (provado em docs/plan/etapa-1/1C-probe.md, item c). Caminho relativo à raiz.
DENY_RULES = [
    "Edit(.harness/work/*/tasks.json)",
    "Edit(.harness/runs/**)",
    "Edit(.harness/profile.json)",
    "Edit(.harness/harness.lock)",
    "Edit(.harness/bin/**)",
    "Edit(.claude/settings.json)",
]


class SettingsError(ValueError):
    """O settings.json existente não permite o merge sem arriscar o conteúdo do time."""


def hook_command(python: str, bootstrap: str) -> str:
    """Sem bash e sem variável de ambiente: funciona igual no Windows (fatos §6)."""
    return f'"{python}" "{bootstrap}" {MARKER}'


def parse(text: str) -> dict:
    if not text.strip():
        return {}
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SettingsError(f"JSON inválido na linha {exc.lineno}, coluna {exc.colno}: {exc.msg}") from exc
    if not isinstance(doc, dict):
        raise SettingsError("a raiz do arquivo não é um objeto JSON")
    return doc


def _is_ours(handler) -> bool:
    return isinstance(handler, dict) and MARKER in str(handler.get("command", ""))


def merge(doc: dict, command: str) -> dict:
    out = copy.deepcopy(doc)
    ours = {"type": "command", "command": command, "timeout": TIMEOUT}

    hooks = out.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SettingsError("`hooks` não é um objeto")
    stop = hooks.setdefault("Stop", [])
    if not isinstance(stop, list):
        raise SettingsError("`hooks.Stop` não é uma lista")
    placed = False
    for group in list(stop):
        if not isinstance(group, dict) or not isinstance(group.get("hooks", []), list):
            raise SettingsError("um grupo de `hooks.Stop` tem formato inesperado")
        handlers = group.get("hooks", [])
        if not any(_is_ours(h) for h in handlers):
            continue
        kept = []
        for handler in handlers:
            if not _is_ours(handler):
                kept.append(handler)
            elif not placed:  # no lugar do primeiro; os duplicados somem
                kept.append(ours)
                placed = True
        if kept:
            group["hooks"] = kept
        else:
            stop.remove(group)
    if not placed:
        stop.append({"hooks": [ours]})

    perms = out.setdefault("permissions", {})
    if not isinstance(perms, dict):
        raise SettingsError("`permissions` não é um objeto")
    deny = perms.setdefault("deny", [])
    if not isinstance(deny, list):
        raise SettingsError("`permissions.deny` não é uma lista")
    deny.extend(rule for rule in DENY_RULES if rule not in deny)
    return out


def dumps(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
