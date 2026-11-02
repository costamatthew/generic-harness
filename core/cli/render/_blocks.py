"""Blocos gerenciados `<!-- harness:begin X -->`/`<!-- harness:end X -->`.

Cópia local da trilha 1C: a versão canônica será `core/lib/blocks.py` (1B). Sai
na integração (1I), conforme a decisão 2 da spec 1C.
"""

from __future__ import annotations


class BlockError(ValueError):
    """Marcador órfão, duplicado ou fora de ordem. `line` é 1-based."""

    def __init__(self, message: str, line: int):
        super().__init__(message)
        self.line = line


def begin(name: str) -> str:
    return f"<!-- harness:begin {name} -->"


def end(name: str) -> str:
    return f"<!-- harness:end {name} -->"


def locate(lines: list[str], name: str) -> tuple[int, int] | None:
    """Índices (0-based) das linhas begin e end, ou None se não há bloco."""
    begins = [i for i, ln in enumerate(lines) if ln.strip() == begin(name)]
    ends = [i for i, ln in enumerate(lines) if ln.strip() == end(name)]
    if len(begins) > 1:
        raise BlockError(f"marcador `{begin(name)}` duplicado", begins[1] + 1)
    if len(ends) > 1:
        raise BlockError(f"marcador `{end(name)}` duplicado", ends[1] + 1)
    if begins and not ends:
        raise BlockError(f"marcador `{begin(name)}` sem o `{end(name)}` correspondente", begins[0] + 1)
    if ends and not begins:
        raise BlockError(f"marcador `{end(name)}` sem o `{begin(name)}` correspondente", ends[0] + 1)
    if not begins:
        return None
    if ends[0] < begins[0]:
        raise BlockError(f"`{end(name)}` aparece antes do `{begin(name)}`", ends[0] + 1)
    return begins[0], ends[0]


def _first_h1(lines: list[str]) -> int | None:
    fenced = False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and ln.startswith("# "):
            return i
    return None


def upsert(text: str, name: str, body: list[str], where: str) -> str:
    """Reescreve o miolo do bloco `name`; se não existe, insere em `where`
    (`after-h1` ou `end`). Só toca entre os marcadores. Preserva CRLF."""
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    found = locate(lines, name)
    if found:
        b, e = found
        lines[b + 1:e] = body
    else:
        block = [begin(name), *body, end(name)]
        if where == "after-h1":
            h1 = _first_h1(lines)
            at = 0 if h1 is None else h1 + 1
            ins = ([""] if h1 is not None else []) + block
            if at < len(lines) and lines[at].strip():
                ins.append("")
            lines[at:at] = ins
        else:
            while lines and lines[-1] == "":
                lines.pop()
            lines += ([""] if lines else []) + block + [""]
    return eol.join(lines)
