"""`harness state` e blocos gerenciados (trilha 1B)."""

from __future__ import annotations

import pytest

from core.cli.harness import envelope
from core.cli.state import state, STATE_REL
from core.lib import blocks, schema

CUSTOM = """# STATE

Texto livre  com espaços  
e CRLF não, mas linhas \t com tab.

## Blockers

- Nenhum.

## Handoff

<!-- harness:begin handoff -->
antigo
<!-- harness:end handoff -->

## Final

fim sem newline"""


def test_creates_from_template_and_prints(tmp_path):
    res = state(tmp_path)
    assert res.exit == 0 and schema.validate(envelope(res, "state"), "cli-output") == []
    assert not (tmp_path / STATE_REL).exists()  # ler não escreve
    state(tmp_path, "primeiro")
    text = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    assert blocks.has(text, "handoff") and blocks.has(text, "tasks")
    assert res.data == {"handoff": "", "blockers": []}
    assert blocks.get(text, "handoff") != ""


def test_handoff_idempotent_and_preserves_outside(tmp_path):
    p = tmp_path / STATE_REL
    p.parent.mkdir(parents=True)
    p.write_bytes(CUSTOM.encode("utf-8"))
    assert state(tmp_path, "feito T1; próximo T2").exit == 0
    first = p.read_bytes().decode("utf-8")
    assert state(tmp_path, "feito T1; próximo T2").data["handoff"].endswith("· feito T1; próximo T2")
    second = p.read_bytes().decode("utf-8")
    date1, date2 = blocks.get(first, "handoff").split(" · ")[0], blocks.get(second, "handoff").split(" · ")[0]
    assert first.replace(date1, "D") == second.replace(date2, "D")
    outside = lambda t: blocks.replace(t, "handoff", "")
    assert outside(CUSTOM) == outside(first) == outside(second)


def test_empty_handoff_is_usage(tmp_path):
    assert state(tmp_path, "   ").exit == 2


def test_malformed_block_refused(tmp_path):
    p = tmp_path / STATE_REL
    p.parent.mkdir(parents=True)
    p.write_text("<!-- harness:begin handoff -->\n", encoding="utf-8")
    res = state(tmp_path, "x")
    assert res.exit == 4 and "marcadores" in res.next


def test_blocks_unit():
    t = "a\n<!-- harness:begin x -->\n1\n2\n<!-- harness:end x -->\nb"
    assert blocks.get(t, "x") == "1\n2" and blocks.get(t, "y") is None
    assert blocks.replace(t, "x", "") == "a\n<!-- harness:begin x -->\n<!-- harness:end x -->\nb"
    with pytest.raises(blocks.BlockError):
        blocks.replace(t, "y", "z")
    assert blocks.get(blocks.append("fim", "y", "k"), "y") == "k"
