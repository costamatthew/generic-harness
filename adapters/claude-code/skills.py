"""Skills (D15): a canônica leva só campos portáveis; o Claude Code recebe os extras do overlay."""

from __future__ import annotations

import json

PORTABLE = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


def _frontmatter_span(lines: list[str]) -> tuple[int, int]:
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md sem frontmatter (`---` na primeira linha)")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return 0, i
    raise ValueError("SKILL.md com frontmatter sem o `---` de fechamento")


def top_level_keys(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").split("\n")
    start, close = _frontmatter_span(lines)
    keys = []
    for ln in lines[start + 1:close]:
        key, sep, _ = ln.partition(":")
        if sep and key and not key[0].isspace() and not key.startswith("#"):
            keys.append(key.strip())
    return keys


def non_portable(text: str) -> list[str]:
    return [k for k in top_level_keys(text) if k not in PORTABLE]


def with_extras(text: str, extras: dict) -> str:
    """Acrescenta os campos do overlay ao frontmatter (valores em JSON, que é YAML válido)."""
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    start, close = _frontmatter_span(lines)
    head = [ln for ln in lines[start + 1:close]
            if not any(ln.startswith(f"{key}:") for key in extras)]
    added = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in extras.items()]
    return eol.join(["---", *head, *added, *lines[close:]])
