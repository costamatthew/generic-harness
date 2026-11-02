"""G1: AGENTS.md = esqueleto (1D) + blocos gerenciados BOUNDARIES e Workflow."""

from __future__ import annotations

from core.cli.render import _blocks


def boundaries_body(profile: dict) -> list[str]:
    """Texto do bloco a partir de `profile.boundaries`. Os matchers não entram."""
    b = profile.get("boundaries") or {}
    always = [str(x) for x in b.get("always") or []]
    ask = [str(r["rule"]) for r in b.get("ask") or []]
    never = [f"{r['rule']} → {r['instead']}" for r in b.get("never") or []]
    sections = []
    for title, items in (("SEMPRE", always), ("PERGUNTE ANTES", ask), ("NUNCA", never)):
        if items:
            sections.append([f"**{title}**", *(f"- {item}" for item in items)])
    if not sections:
        sections = [["_(o perfil não declara fronteiras)_"]]
    lines = ["## BOUNDARIES"]
    for section in sections:
        lines += ["", *section]
    return lines


def workflow_body(text: str) -> list[str]:
    return text.strip("\n").replace("\r\n", "\n").split("\n")


def render(existing: str | None, template: str, profile: dict, workflow: str) -> str:
    """Levanta `_blocks.BlockError` se os marcadores estiverem órfãos ou duplicados."""
    text = existing if existing is not None else template
    original = text.replace("\r\n", "\n").split("\n")
    for name in ("boundaries", "workflow"):  # valida tudo antes de reescrever: as linhas citadas são as do arquivo original
        _blocks.locate(original, name)
    text = _blocks.upsert(text, "boundaries", boundaries_body(profile), "after-h1")
    text = _blocks.upsert(text, "workflow", workflow_body(workflow), "end")
    return text
