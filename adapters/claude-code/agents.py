"""Sub-agents `.claude/agents/harness-<papel>.md`: frontmatter do perfil + corpo do papel (1D).

O frontmatter neutro do papel (`role`, `description`, `readonly`) não vai para o
arquivo; modelo, tier e effort vêm do perfil, nunca do papel. Só stdlib.
"""

from __future__ import annotations

import json

READONLY_DENY = "Edit, Write, NotebookEdit, Agent"
DEFAULT_DENY = "Agent"  # profundidade da Etapa 1 = L1
ROLES = ("implementer", "verifier")


class RoleError(ValueError):
    """Perfil ou papel que não permite gerar o sub-agent."""


def split_frontmatter(text: str) -> tuple[dict, str]:
    """(campos `chave: valor` do frontmatter, corpo). Sem frontmatter → ({}, texto)."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        close = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise RoleError("frontmatter sem o `---` de fechamento") from None
    fields = {}
    for ln in lines[1:close]:
        key, sep, value = ln.partition(":")
        if sep and key and not key[0].isspace():
            value = value.strip()
            if value[:1] in "\"'" and value[-1:] == value[:1] and len(value) > 1:
                value = value[1:-1]
            fields[key.strip()] = value
    return fields, "\n".join(lines[close + 1:]).lstrip("\n")


def resolve_model(role: str, profile: dict) -> str:
    models = profile.get("models") or {}
    spec = (profile.get("roles") or {}).get(role) or {}
    if spec.get("pinned"):
        pin = (models.get("pins") or {}).get(role)
        if not pin:
            raise RoleError(f"pin obrigatório para o {role} (D31): `roles.{role}.pinned` é true, "
                            f"mas `models.pins.{role}` não existe no perfil; "
                            f"declare o ID completo do modelo em models.pins.{role}")
        return pin
    tier = spec.get("tier")
    alias = ((models.get("tiers") or {}).get(tier) or {}).get("claude-code")
    if not alias:
        raise RoleError(f"o tier '{tier}' do papel {role} não tem modelo para claude-code em "
                        f"`models.tiers.{tier}.claude-code`; declare o alias no perfil")
    return alias


def build(role: str, profile: dict, role_text: str) -> str:
    spec = (profile.get("roles") or {}).get(role)
    if spec is None:
        raise RoleError(f"o perfil não declara o papel '{role}' em `roles`")
    meta, body = split_frontmatter(role_text)
    description = meta.get("description")
    if not description:
        raise RoleError(f"core/roles/{role}.md sem `description` no frontmatter")
    readonly = bool(spec.get("readonly")) or meta.get("readonly", "").lower() == "true"
    head = [
        "---",
        f"name: harness-{role}",
        f"description: {json.dumps(description, ensure_ascii=False)}",
        f"model: {resolve_model(role, profile)}",
    ]
    if spec.get("effort"):
        head.append(f"effort: {spec['effort']}")
    head += [f"disallowedTools: {READONLY_DENY if readonly else DEFAULT_DENY}", "---", "",
             f"<!-- gerado por harness render a partir de core/roles/{role}.md; não edite -->", ""]
    return "\n".join(head) + "\n" + body.rstrip("\n") + "\n"
