"""Leitura validada de `.harness/profile.json` (somente leitura; ADR-0003)."""

from __future__ import annotations

import json
from pathlib import Path

from core.lib import fsx, schema

PROFILE_REL = ".harness/profile.json"
DEFAULT_TIMEOUT_SEC = 600
DEFAULT_SUMMARY_LINES = 10


def path(root: str | Path) -> Path:
    return Path(root) / PROFILE_REL


def load(root: str | Path) -> dict:
    """Devolve o perfil validado contra `profile`.

    `FileNotFoundError` se não existe; `ValueError` com os erros do schema (ou do JSON)."""
    p = path(root)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{PROFILE_REL}: JSON inválido: {exc}") from exc
    errors = schema.validate(doc, "profile")
    if errors:
        raise ValueError(f"{PROFILE_REL} não passa no schema profile: " + "; ".join(errors))
    return doc


def sha256(root: str | Path) -> str | None:
    """sha256 dos bytes do perfil, ou None se ele não existe."""
    try:
        return fsx.sha256_file(path(root))
    except FileNotFoundError:
        return None


def resolve_command(doc: dict, name: str) -> dict | None:
    """`test.unit` → `commands.test.unit`; `lint` → `commands.lint`. None se não existe."""
    commands = doc.get("commands", {})
    head, _, tail = name.partition(".")
    if tail:
        group = commands.get(head)
        if head != "test" or not isinstance(group, dict):
            return None
        return group.get(tail)
    cmd = commands.get(head)
    if head == "test" or not isinstance(cmd, dict):
        return None  # `test` é um mapa de suítes, não um comando
    return cmd


def summary_lines(doc: dict) -> int:
    return doc.get("limits", {}).get("summaryLines", DEFAULT_SUMMARY_LINES)
