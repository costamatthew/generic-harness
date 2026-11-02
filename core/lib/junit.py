"""Parser JUnit XML (stdlib `xml.etree`), para o gate (spec 1A, item 4).

Aceita `<testsuites>` ou `<testsuite>` na raiz, aninhados. As contagens vêm dos
`<testcase>`; uma suíte sem testcases nem subsuítes contribui com os próprios
atributos. `firstFailures` sai como `arquivo:linha` (ver `_location`).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

MAX_FAILURES = 10
_LOC_RE = re.compile(r"((?:[A-Za-z]:)?[^\s:\"'()<>,\[\]]+):(\d+)")


class JUnitError(ValueError):
    """Relatório ilegível ou com raiz desconhecida."""


@dataclass
class Report:
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    first_failures: list[dict] = field(default_factory=list)

    def counts(self) -> dict:
        return {"tests": self.tests, "failures": self.failures, "errors": self.errors, "skipped": self.skipped}


def _int(el: ET.Element, attr: str) -> int:
    try:
        return max(0, int(float(el.get(attr, "0") or 0)))
    except ValueError:
        return 0


def parse(path: str | Path, root: str | Path | None = None) -> Report:
    """Lê o relatório. `root` é a raiz do repo, usada para validar caminhos do fallback."""
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise JUnitError(f"XML inválido: {exc}") from exc
    top = tree.getroot()
    if top.tag not in ("testsuites", "testsuite"):
        raise JUnitError(f"raiz <{top.tag}> não é <testsuites> nem <testsuite>")
    rep = Report()
    _walk(top, rep, Path(root) if root else None)
    return rep


def _walk(suite: ET.Element, rep: Report, root: Path | None) -> None:
    cases = suite.findall("testcase")
    subs = suite.findall("testsuite")
    if not cases and not subs and suite.tag == "testsuite":
        rep.tests += _int(suite, "tests")
        rep.failures += _int(suite, "failures")
        rep.errors += _int(suite, "errors")
        rep.skipped += _int(suite, "skipped") + _int(suite, "disabled")
        return
    for case in cases:
        rep.tests += 1
        bad = case.find("failure")
        err = case.find("error")
        if bad is not None:
            rep.failures += 1
        if err is not None:
            rep.errors += 1
        if case.find("skipped") is not None:
            rep.skipped += 1
        node = bad if bad is not None else err
        if node is not None and len(rep.first_failures) < MAX_FAILURES:
            rep.first_failures.append({"location": _location(case, node, root), "name": case.get("name", "?")})
    for sub in subs:
        _walk(sub, rep, root)


def _location(case: ET.Element, node: ET.Element, root: Path | None) -> str:
    # 1) atributos do testcase (pytest xunit1, a maioria dos runners JS/Java)
    file, line = case.get("file"), case.get("line")
    if file:
        file = file.replace("\\", "/")
        return f"{file}:{line}" if line not in (None, "") else file
    # 2) último `caminho:linha` do texto da falha que exista no repo (pytest xunit2)
    text = "\n".join(t for t in (node.get("message"), node.text) if t)
    for cand, ln in reversed(_LOC_RE.findall(text)):
        rel = _in_repo(cand, root)
        if rel:
            return f"{rel}:{ln}"
    # 3) classname como caminho, sem linha
    classname = case.get("classname", "")
    if not classname:
        return case.get("name", "?")
    parts = classname.split(".")
    if root is not None:
        for n in range(len(parts), 0, -1):
            cand = "/".join(parts[:n]) + ".py"
            if (root / cand).is_file():
                return cand
    return "/".join(parts)


def _in_repo(cand: str, root: Path | None) -> str | None:
    if root is None:
        return None
    cand = cand.replace("\\", "/")
    p = Path(cand)
    if p.is_absolute():
        try:
            p = p.resolve().relative_to(root.resolve())
        except (ValueError, OSError):
            return None
    elif not (root / p).is_file():
        return None
    return p.as_posix() if (root / p).is_file() else None
