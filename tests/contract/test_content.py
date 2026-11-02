"""Itens estruturais do critério da 1D (spec 1G, item 4).

Enquanto a trilha 1D não entrega `core/skills` e `core/roles`, os testes sobre os
arquivos pulam com a política de `tests/scenarios/policy.py` (falham com
HARNESS_REQUIRE_ALL=1). Os testes dos parsers (`test_parser_*`) sempre rodam, para
que os checks não sejam vacuosos.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.cli.harness import COMMANDS
from core.lib import schema
from tests.scenarios.policy import not_delivered

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "core/skills/harness-execute/SKILL.md"
ROLES = ROOT / "core/roles"
TEMPLATES = ROOT / "core/templates"
PORTABLE = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
ROLE_KEYS = {"role", "description", "readonly"}
ROLE_FILES = ["implementer.md", "verifier.md", "explorer.md"]


def need(path: Path) -> Path:
    if not path.exists():
        not_delivered("1D", path.relative_to(ROOT).as_posix())
    return path


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    assert m, "arquivo sem frontmatter delimitado por ---"
    out: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        top = re.match(r"([A-Za-z][\w-]*):\s*(.*)$", line)
        if top:
            key = top.group(1)
            out[key] = top.group(2)
        elif key:
            out[key] += " " + line.strip()
    return out


def unknown_commands(text: str) -> list[str]:
    """`harness <cmd>` citado entre crases que não existe em COMMANDS."""
    bad = []
    for span in re.findall(r"`([^`\n]+)`", text):
        for m in re.finditer(r"(?<![\w-])harness\s+(?:--json\s+)?([a-z][a-z-]*)(?:\s+([a-z][a-z-]*))?", span):
            first, second = m.group(1), m.group(2)
            groups = {n.split(" ")[0] for n in COMMANDS if " " in n}
            if first in groups:
                ok = second is not None and f"{first} {second}" in COMMANDS
            else:
                ok = first in COMMANDS
            if not ok:
                bad.append(m.group(0))
    return bad


VERIFIER_EVID = re.compile(r"^(\S+:\d+|exec: .+ exit=\d+)$")


def verifier_problems(text: str) -> list[str]:
    m = re.search(r"^### Verifier (\S+)\n- tree: ([0-9a-f]{7})\n\n(\|.*(?:\n\|.*)+)", text, re.M)
    if not m:
        return ["seção '### Verifier <ID>' com '- tree: <7 hex>' e tabela não encontrada"]
    rows = [[c.strip() for c in r.strip("|").split("|")] for r in m.group(3).splitlines()]
    if rows[0] != ["#", "Check", "Resultado", "Evidência"]:
        return [f"cabeçalho da tabela inesperado: {rows[0]}"]
    problems = []
    for row in rows[2:]:
        if len(row) != 4 or row[2] not in ("atende", "não atende"):
            problems.append(f"linha inválida: {row}")
        elif not VERIFIER_EVID.match(row[3]):
            problems.append(f"evidência inválida: {row[3]}")
    return problems


def agents_problems(text: str) -> list[str]:
    problems = []
    if len(text.splitlines()) >= 100:
        problems.append("AGENTS.md com 100 linhas ou mais")
    if "TODO" not in text:
        problems.append("sem TODO")
    for block in ("boundaries", "workflow"):
        b, e = f"<!-- harness:begin {block} -->", f"<!-- harness:end {block} -->"
        if text.count(b) != 1 or text.count(e) != 1 or text.find(b) > text.find(e):
            problems.append(f"marcadores de {block} fora de par")
    for span in re.findall(r"`([^`\s]*/[^`\s]*)`", text):
        if not span.startswith((".harness/", ".agents/", ".claude/", "http")):
            problems.append(f"caminho do hospedeiro: {span}")
    return problems


# ---- parsers (sempre rodam) ----------------------------------------------
def test_parser_commands():
    assert unknown_commands("`harness gate T1` e `harness task done T1` e `harness --json state`") == []
    assert unknown_commands("`harness task` `harness inventado x` `harness gat`") == [
        "harness task", "harness inventado x", "harness gat"]


def test_parser_verifier():
    good = ("### Verifier T1\n- tree: 3f9c1e2\n\n| # | Check | Resultado | Evidência |\n| --- | --- | --- | --- |\n"
            "| 1 | a | atende | src/a.py:42 |\n| 2 | b | atende | exec: python -m pytest exit=0 |\n")
    assert verifier_problems(good) == []
    assert verifier_problems(good.replace("src/a.py:42", "src/a.py")) != []
    assert verifier_problems(good.replace("atende |", "talvez |", 1)) != []
    assert verifier_problems(good.replace("3f9c1e2", "xyz")) != []


def test_parser_agents():
    good = ("# X\n<!-- harness:begin boundaries -->\n<!-- harness:end boundaries -->\nTODO\n`.harness/profile.json`\n"
            "<!-- harness:begin workflow -->\n<!-- harness:end workflow -->\n")
    assert agents_problems(good) == []
    assert agents_problems(good.replace("TODO", "")) != []
    assert agents_problems(good + "`src/app/main.py`") != []
    assert agents_problems(good.replace("<!-- harness:end workflow -->", "")) != []


# ---- conteúdo da 1D --------------------------------------------------------
def test_skill_frontmatter_portable():
    text = need(SKILL).read_text(encoding="utf-8")
    fm = frontmatter(text)
    assert set(fm) <= PORTABLE, f"campos não portáveis na SKILL.md: {sorted(set(fm) - PORTABLE)}"
    assert {"name", "description"} <= set(fm)
    assert len(fm["description"]) <= 1536
    assert len(text.splitlines()) < 500


def _command_files() -> list[Path]:
    files = [need(SKILL)]
    files += [need(ROLES / n) for n in ROLE_FILES]
    files += [need(TEMPLATES / n) for n in ("STATE.md", "task.md", "validation.md", "AGENTS.md", "agents-workflow.md")]
    files += sorted((SKILL.parent / "references").glob("*.md"))
    return files


def test_no_invented_commands():
    for f in _command_files():
        bad = unknown_commands(f.read_text(encoding="utf-8"))
        assert bad == [], f"{f.relative_to(ROOT)} cita comando fora de COMMANDS: {bad}"


@pytest.mark.parametrize("name", ROLE_FILES)
def test_role_frontmatter(name):
    fm = frontmatter(need(ROLES / name).read_text(encoding="utf-8"))
    assert set(fm) == ROLE_KEYS, f"{name}: frontmatter deve ter só {sorted(ROLE_KEYS)}, tem {sorted(fm)}"
    if name in ("verifier.md", "explorer.md"):
        assert fm["readonly"].strip() == "true"


def test_template_tasks_json_valid():
    data = json.loads(need(TEMPLATES / "tasks.json").read_text(encoding="utf-8"))
    assert schema.validate(data, "tasks") == []


def test_template_agents_md():
    assert agents_problems(need(TEMPLATES / "AGENTS.md").read_text(encoding="utf-8")) == []


def test_template_validation_verifier_example():
    assert verifier_problems(need(TEMPLATES / "validation.md").read_text(encoding="utf-8")) == []
