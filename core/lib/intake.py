"""Lê um item de intake em Markdown (BF §6.3) e devolve a forma estruturada.

Formato:

    # <ID> <título>
    - Origem: <...> · Responsável: <...> · Prioridade: P1|P2|P3
    - Problema: <...>
    - Fora de escopo: <...>
    - Fontes de contexto: <...>
    - Dúvidas abertas (decisões que a IA não deve tomar): <...>

Campos opcionais: `- Tamanho: quick|medium|large` e `- Receita: <recipe>`.
A validação de conteúdo fica com core/schemas/intake.schema.json.
"""

from __future__ import annotations

import re

_KEYS = {
    "origem": "origin",
    "responsável": "owner",
    "responsavel": "owner",
    "prioridade": "priority",
    "problema": "problem",
    "fora de escopo": "outOfScope",
    "fontes de contexto": "sources",
    "dúvidas abertas": "openQuestions",
    "duvidas abertas": "openQuestions",
    "tamanho": "size",
    "receita": "recipe",
}

_TITLE = re.compile(r"^#\s+(\S+)\s+(.+?)\s*$")


def parse(text: str) -> dict:
    """Devolve um dict com as chaves do schema `intake`.

    Chave desconhecida levanta ValueError: um campo novo precisa entrar no
    contrato antes (docs/plan/contract-changes.md).
    """
    item: dict = {}
    for line in text.splitlines():
        if "id" not in item:
            m = _TITLE.match(line)
            if m:
                item["id"], item["title"] = m.group(1), m.group(2)
                continue
        if not line.startswith("- "):
            continue
        for part in line[2:].split(" · "):
            key, sep, value = part.partition(":")
            if not sep:
                raise ValueError(f"linha de intake sem 'chave: valor': {part!r}")
            key = re.sub(r"\(.*?\)", "", key).strip().lower()
            if key not in _KEYS:
                raise ValueError(f"campo de intake desconhecido: {key!r}")
            item[_KEYS[key]] = value.strip()
    return item
