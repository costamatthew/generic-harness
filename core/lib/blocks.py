"""Blocos gerenciados `<!-- harness:begin X -->` ... `<!-- harness:end X -->` (ADR-0003, HG §3.7).

Só o texto entre os marcadores é do harness; tudo fora deles é preservado byte
a byte. Usado pela 1B (STATE.md, validation.md) e pelo render da 1C.
"""

from __future__ import annotations

import re


class BlockError(ValueError):
    """Bloco ausente, duplicado ou mal formado. A mensagem diz o que fazer."""


def markers(name: str) -> tuple[str, str]:
    return f"<!-- harness:begin {name} -->", f"<!-- harness:end {name} -->"


def _span(text: str, name: str) -> tuple[int, int, int, int] | None:
    """(início do begin, fim do begin, início do end, fim do end) ou None se não há bloco."""
    begin, end = markers(name)
    nb, ne = text.count(begin), text.count(end)
    if nb == 0 and ne == 0:
        return None
    if nb != 1 or ne != 1:
        raise BlockError(
            f"bloco '{name}' malformado: {nb} marcador(es) begin e {ne} end (esperado 1 de cada). "
            f"Deixe exatamente um par {begin} ... {end} e rode o comando de novo.")
    b = text.index(begin)
    e = text.index(end)
    if e < b:
        raise BlockError(f"bloco '{name}': o marcador end vem antes do begin. Reordene os marcadores.")
    return b, b + len(begin), e, e + len(end)


def has(text: str, name: str) -> bool:
    return _span(text, name) is not None


def get(text: str, name: str) -> str | None:
    """Conteúdo do bloco sem a quebra de linha logo após o begin e antes do end; None se não existe."""
    sp = _span(text, name)
    if sp is None:
        return None
    inner = text[sp[1]:sp[2]]
    # Arquivo do hospedeiro com CRLF (checkout no Windows): a quebra de linha pode ser \r\n.
    inner = inner[2:] if inner.startswith("\r\n") else inner[1:] if inner.startswith("\n") else inner
    return inner[:-2] if inner.endswith("\r\n") else inner[:-1] if inner.endswith("\n") else inner


def replace(text: str, name: str, content: str) -> str:
    """Troca o conteúdo do bloco. `BlockError` se ele não existe (use `append`)."""
    sp = _span(text, name)
    if sp is None:
        begin, end = markers(name)
        raise BlockError(f"bloco '{name}' não existe. Acrescente o par {begin} ... {end} ao arquivo.")
    body = f"\n{content}\n" if content else "\n"
    return text[:sp[1]] + body + text[sp[2]:]


def append(text: str, name: str, content: str = "") -> str:
    """Acrescenta ao fim do texto um bloco novo (não toca em nada do que existe)."""
    if _span(text, name) is not None:
        raise BlockError(f"bloco '{name}' já existe.")
    begin, end = markers(name)
    sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return f"{text}{sep}{begin}\n{content + chr(10) if content else ''}{end}\n"


def lines(text: str, name: str) -> list[str]:
    inner = get(text, name)
    return [] if not inner else [ln for ln in inner.split("\n") if ln.strip()]


RUN_RE = re.compile(r"\brun=(\S+)")
