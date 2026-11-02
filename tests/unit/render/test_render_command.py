"""harness render (trilha 1C): idempotência, merge sem perda, blocos, sub-agents e skills."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from core.cli.render import CORE_ROOT, render

HERE = Path(__file__).parent / "data"
FAKE_CORE = HERE / "core"
ROOT = Path(__file__).resolve().parents[3]
PROFILE = json.loads((ROOT / "core/schemas/examples/profile/valid-brownfield-python.json").read_text(encoding="utf-8"))
CMD = '"/usr/bin/python3" "/clone/bootstrap.py" hook stop_gate --adapter claude-code'


def make_repo(tmp_path, profile=None, settings=None, agents_md=None):
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness/profile.json").write_text(json.dumps(profile or PROFILE), encoding="utf-8")
    if settings is not None:
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude/settings.json").write_text(settings, encoding="utf-8")
    if agents_md is not None:
        (tmp_path / "AGENTS.md").write_text(agents_md, encoding="utf-8")
    return tmp_path


def do_render(repo):
    return render(repo, FAKE_CORE, CMD)


def snapshot(repo):
    return {p.relative_to(repo).as_posix(): p.read_bytes() for p in sorted(repo.rglob("*")) if p.is_file()}


def test_second_render_changes_nothing_and_is_byte_identical(tmp_path):
    repo = make_repo(tmp_path)
    first = do_render(repo)
    assert first.status == "ok" and first.data["changed"]
    before = snapshot(repo)
    second = do_render(repo)
    assert second.status == "ok" and second.data.get("changed", []) == []
    assert snapshot(repo) == before


def test_first_render_creates_expected_files(tmp_path):
    repo = make_repo(tmp_path)
    changed = set(do_render(repo).data["changed"])
    assert changed == {
        "AGENTS.md", ".claude/settings.json", ".claude/agents/harness-implementer.md",
        ".claude/agents/harness-verifier.md",
        ".agents/skills/harness-execute/SKILL.md", ".agents/skills/harness-execute/references/decision-tree.md",
        ".claude/skills/harness-execute/SKILL.md", ".claude/skills/harness-execute/references/decision-tree.md",
    }


def test_settings_from_empty_has_one_stop_handler_and_deny_rules(tmp_path):
    repo = make_repo(tmp_path, settings=(HERE / "settings/empty.json").read_text(encoding="utf-8"))
    do_render(repo)
    doc = json.loads((repo / ".claude/settings.json").read_text(encoding="utf-8"))
    handlers = [h for g in doc["hooks"]["Stop"] for h in g["hooks"]]
    assert handlers == [{"type": "command", "command": CMD, "timeout": 60}]
    assert "SubagentStop" not in doc["hooks"]
    assert "Edit(.harness/work/*/tasks.json)" in doc["permissions"]["deny"]
    assert not any(r.startswith("Write(") for r in doc["permissions"]["deny"])


@pytest.mark.parametrize("name", ["team.json", "team-deny.json"])
def test_settings_merge_keeps_everything_of_the_team_in_order(tmp_path, name):
    raw = (HERE / "settings" / name).read_text(encoding="utf-8")
    original = json.loads(raw)
    repo = make_repo(tmp_path, settings=raw)
    do_render(repo)
    do_render(repo)
    merged = json.loads((repo / ".claude/settings.json").read_text(encoding="utf-8"))

    def contains_in_order(old, new):
        if isinstance(old, dict):
            assert list(old) == [k for k in new if k in old]
            for k in old:
                contains_in_order(old[k], new[k])
        elif isinstance(old, list) and all(not isinstance(x, (dict, list)) for x in old):
            assert [x for x in new if x in old] == old
        elif isinstance(old, list):
            for o, n in zip(old, new):
                contains_in_order(o, n)
        else:
            assert old == new

    contains_in_order(original, merged)
    if "hooks" in original:  # o grupo do time continua intacto e o do harness vem depois
        assert merged["hooks"]["Stop"][0] == original["hooks"]["Stop"][0]
    handlers = [h for g in merged["hooks"]["Stop"] for h in g["hooks"] if "hook stop_gate --adapter claude-code" in h["command"]]
    assert len(handlers) == 1


def test_stale_harness_handler_is_replaced_not_duplicated(tmp_path):
    old = {"hooks": {"Stop": [{"hooks": [
        {"type": "command", "command": "echo time"},
        {"type": "command", "command": '"/old/python" "/old/bootstrap.py" hook stop_gate --adapter claude-code', "timeout": 5},
        {"type": "command", "command": '"/old2/python" hook stop_gate --adapter claude-code'}]}]}}
    repo = make_repo(tmp_path, settings=json.dumps(old))
    do_render(repo)
    doc = json.loads((repo / ".claude/settings.json").read_text(encoding="utf-8"))
    assert doc["hooks"]["Stop"] == [{"hooks": [{"type": "command", "command": "echo time"},
                                                {"type": "command", "command": CMD, "timeout": 60}]}]


def test_invalid_settings_json_fails_without_writing(tmp_path):
    repo = make_repo(tmp_path, settings=(HERE / "settings/invalid.json").read_text(encoding="utf-8"))
    before = snapshot(repo)
    result = do_render(repo)
    assert result.status == "fail"
    assert "settings.json" in result.summary[0] and "linha" in result.summary[0]
    assert snapshot(repo) == before


TEAM_AGENTS = """# Pedidos API

Texto do time acima.

<!-- harness:begin boundaries -->
velho
<!-- harness:end boundaries -->

## Convenções do time

Não mexa aqui.

<!-- harness:begin workflow -->
velho
<!-- harness:end workflow -->

Rodapé do time.
"""


def test_agents_md_diff_stays_between_markers(tmp_path):
    repo = make_repo(tmp_path, agents_md=TEAM_AGENTS)
    do_render(repo)
    new = (repo / "AGENTS.md").read_text(encoding="utf-8")
    outside = lambda t: (t.split("<!-- harness:begin boundaries -->")[0],  # noqa: E731
                         t.split("<!-- harness:end boundaries -->")[1].split("<!-- harness:begin workflow -->")[0],
                         t.split("<!-- harness:end workflow -->")[1])
    assert outside(new) == outside(TEAM_AGENTS)
    assert "velho" not in new
    assert "**NUNCA**" in new and "push direto na main → abra um PR" in new
    assert "shell:git push" not in new  # matchers não entram no texto


def test_agents_md_without_markers_inserts_after_h1_and_at_end(tmp_path):
    repo = make_repo(tmp_path, agents_md="# Meu repo\n\nTexto do time.\n")
    do_render(repo)
    lines = (repo / "AGENTS.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# Meu repo"
    assert lines[2] == "<!-- harness:begin boundaries -->"
    assert "Texto do time." in lines
    assert lines[-1] == "<!-- harness:end workflow -->"
    again = do_render(repo)
    assert again.data.get("changed", []) == []


def test_agents_md_created_from_template_when_absent(tmp_path):
    repo = make_repo(tmp_path)
    do_render(repo)
    text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert text.startswith("# TODO: nome do projeto") and "## BOUNDARIES" in text and "## Workflow" in text


@pytest.mark.parametrize("bad, line", [
    (TEAM_AGENTS.replace("<!-- harness:end boundaries -->\n", ""), 5),
    (TEAM_AGENTS + "<!-- harness:end workflow -->\n", 18),
    (TEAM_AGENTS.replace("<!-- harness:begin workflow -->", "<!-- harness:begin boundaries -->"), 13),
])
def test_orphan_or_duplicate_marker_fails_with_file_and_line(tmp_path, bad, line):
    repo = make_repo(tmp_path, agents_md=bad)
    before = snapshot(repo)
    result = do_render(repo)
    assert result.status == "fail"
    assert f"AGENTS.md:{line}" in result.summary[0]
    assert snapshot(repo) == before  # nada foi escrito


def test_claude_md_without_import_warns_and_is_untouched(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "CLAUDE.md").write_text("# time\n", encoding="utf-8")
    result = do_render(repo)
    assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == "# time\n"
    assert any("@AGENTS.md" in line for line in result.summary)


def frontmatter(text):
    return dict(ln.split(": ", 1) for ln in text.split("---")[1].strip().splitlines())


def test_verifier_is_pinned_and_readonly_implementer_is_not(tmp_path):
    repo = make_repo(tmp_path)
    do_render(repo)
    ver = (repo / ".claude/agents/harness-verifier.md").read_text(encoding="utf-8")
    fm = frontmatter(ver)
    assert fm["name"] == "harness-verifier" and fm["model"] == "claude-opus-5-5" and fm["effort"] == "high"
    assert {"Edit", "Agent"} <= set(fm["disallowedTools"].split(", ")) and "Bash" not in fm["disallowedTools"]
    assert "<!-- gerado por harness render a partir de core/roles/verifier.md; não edite -->" in ver
    assert "role: verifier" not in ver and "Sem evidência, não atende." in ver
    impl = frontmatter((repo / ".claude/agents/harness-implementer.md").read_text(encoding="utf-8"))
    assert impl["model"] == "sonnet" and impl["disallowedTools"] == "Agent"


def test_pinned_without_pin_fails(tmp_path):
    profile = copy.deepcopy(PROFILE)
    del profile["models"]["pins"]
    repo = make_repo(tmp_path, profile=profile)
    before = snapshot(repo)
    result = do_render(repo)
    assert result.status == "fail" and "pin obrigatório para o verifier (D31)" in result.summary[0]
    assert snapshot(repo) == before


def test_skill_canonical_is_portable_and_claude_copy_has_overlay(tmp_path):
    repo = make_repo(tmp_path)
    do_render(repo)
    canon = (repo / ".agents/skills/harness-execute/SKILL.md").read_text(encoding="utf-8")
    claude = (repo / ".claude/skills/harness-execute/SKILL.md").read_text(encoding="utf-8")
    assert canon == (FAKE_CORE / "skills/harness-execute/SKILL.md").read_text(encoding="utf-8")
    assert "when_to_use" not in canon and "when_to_use:" in claude
    assert claude.endswith(canon.split("---\n", 2)[2])


def test_skill_with_extra_field_in_canonical_fails(tmp_path):
    core = tmp_path / "core"
    shutil.copytree(FAKE_CORE, core)
    skill = core / "skills/harness-execute/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace("description:", "context: fork\ndescription:"), encoding="utf-8")
    (tmp_path / "repo").mkdir()
    repo = make_repo(tmp_path / "repo")
    result = render(repo, core, CMD)
    assert result.status == "fail" and "context" in result.summary[0]
    assert "skills.json" in result.next


def test_only_harness_skills_are_touched(tmp_path):
    repo = make_repo(tmp_path)
    (repo / ".claude/skills/do-time").mkdir(parents=True)
    (repo / ".claude/skills/do-time/SKILL.md").write_text("meu\n", encoding="utf-8")
    do_render(repo)
    assert (repo / ".claude/skills/do-time/SKILL.md").read_text(encoding="utf-8") == "meu\n"


def test_missing_profile_is_usage_error(tmp_path):
    result = do_render(tmp_path)
    assert result.status == "usage" and "profile.json" in result.summary[0]


def test_real_core_reaches_the_shared_paths():
    # A 1I confere o conteúdo da 1D; aqui só garante que o render aponta para o core real.
    assert CORE_ROOT.name == "core" and (CORE_ROOT / "cli" / "render").is_dir()
