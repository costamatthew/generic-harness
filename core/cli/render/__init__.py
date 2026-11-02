"""`harness render`: reescreve os blocos gerenciados e os arquivos do adaptador a partir do perfil.

Idempotente e tudo-ou-nada: monta o conteúdo de todos os arquivos na memória,
valida, e só então grava (de forma atômica) os que mudaram.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.cli.harness import Result
from core.cli.render import _blocks, agents_md
from core.hooks import _fsx, _loader
from core.lib import schema

CORE_ROOT = Path(__file__).resolve().parents[2]
CLONE_ROOT = CORE_ROOT.parent
ADAPTER = "claude-code"


class RenderError(Exception):
    def __init__(self, what: str, instead: str, status: str = "fail"):
        super().__init__(what)
        self.what, self.instead, self.status = what, instead, status


def _read(path: Path, what: str, instead: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RenderError(f"{what} ilegível ({path}): {exc.strerror or exc}", instead) from exc


def load_profile(target: Path) -> dict:
    path = target / ".harness" / "profile.json"
    if not path.is_file():
        raise RenderError(f"{path} não existe", "rode `harness apply` (ou escreva o perfil) antes do render", "usage")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RenderError(f"{path} ilegível: {exc}", "corrija o JSON do perfil") from exc
    errors = schema.validate(profile, "profile")
    if errors:
        raise RenderError(f".harness/profile.json inválido: {errors[0]}",
                          "corrija o perfil; o contrato está em core/schemas/profile.schema.json")
    return profile


def hook_python_command(adapter_settings) -> str:
    import sys

    return adapter_settings.hook_command(sys.executable, str(CLONE_ROOT / "bootstrap.py"))


def plan(target: Path, core_root: Path = CORE_ROOT, command: str | None = None) -> tuple[dict[str, bytes], list[str]]:
    """Conteúdo desejado de cada arquivo (caminho relativo com '/') e as notas para a pessoa."""
    profile = load_profile(target)
    settings = _loader.load(ADAPTER, "settings")
    agents = _loader.load(ADAPTER, "agents")
    skills = _loader.load(ADAPTER, "skills")
    files: dict[str, bytes] = {}
    notes: list[str] = []

    # AGENTS.md (G1)
    agents_path = target / "AGENTS.md"
    existing = agents_path.read_text(encoding="utf-8") if agents_path.exists() else None
    template = ""
    if existing is None:
        template = _read(core_root / "templates" / "AGENTS.md", "o esqueleto core/templates/AGENTS.md",
                         "o esqueleto é da trilha 1D; sem ele não há como criar o AGENTS.md")
    workflow = _read(core_root / "templates" / "agents-workflow.md", "core/templates/agents-workflow.md",
                     "o texto do bloco Workflow é da trilha 1D")
    try:
        files["AGENTS.md"] = agents_md.render(existing, template, profile, workflow).encode("utf-8")
    except _blocks.BlockError as exc:
        raise RenderError(f"AGENTS.md:{exc.line}: {exc}",
                          "corrija ou apague o marcador (cada bloco tem um `begin` e um `end`); nada foi gravado") from exc

    # CLAUDE.md: avisa, não toca
    claude_md = target / "CLAUDE.md"
    if claude_md.exists() and "@AGENTS.md" not in claude_md.read_text(encoding="utf-8", errors="replace"):
        notes.append("CLAUDE.md não importa @AGENTS.md: o Claude Code lê só o CLAUDE.md; acrescente `@AGENTS.md`")

    # .claude/settings.json
    settings_path = target / ".claude" / "settings.json"
    raw = settings_path.read_text(encoding="utf-8") if settings_path.exists() else ""
    try:
        current = settings.parse(raw)
        merged = settings.merge(current, command or hook_python_command(settings))
    except settings.SettingsError as exc:
        raise RenderError(f".claude/settings.json: {exc}",
                          "corrija o arquivo à mão (o render não sobrescreve o que não consegue ler); nada foi gravado") from exc
    files[".claude/settings.json"] = (raw if merged == current and raw else settings.dumps(merged)).encode("utf-8")
    notes.append("never/ask do perfil ainda não viram regras de permissão (compilação é da trilha 3S)")

    # sub-agents
    for role in agents.ROLES:
        if role not in (profile.get("roles") or {}):
            notes.append(f"perfil sem o papel '{role}': harness-{role}.md não gerado")
            continue
        role_text = _read(core_root / "roles" / f"{role}.md", f"core/roles/{role}.md",
                          "os papéis são da trilha 1D")
        try:
            content = agents.build(role, profile, role_text)
        except agents.RoleError as exc:
            raise RenderError(f"harness-{role}: {exc}", "corrija o perfil (.harness/profile.json) e rode o render de novo") from exc
        files[f".claude/agents/harness-{role}.md"] = content.encode("utf-8")

    # skills (D15)
    overlay_path = CLONE_ROOT / "adapters" / ADAPTER / "skills.json"
    overlay = json.loads(overlay_path.read_text(encoding="utf-8")) if overlay_path.exists() else {}
    skills_dir = core_root / "skills"
    for skill in sorted(p for p in skills_dir.glob("harness-*") if p.is_dir()) if skills_dir.is_dir() else []:
        for src in sorted(p for p in skill.rglob("*") if p.is_file()):
            rel = src.relative_to(skill).as_posix()
            data = src.read_bytes()
            claude_data = data
            if rel == "SKILL.md":
                text = data.decode("utf-8")
                try:
                    extra = skills.non_portable(text)
                    if extra:
                        raise RenderError(
                            f"core/skills/{skill.name}/SKILL.md tem campos não portáveis: {', '.join(extra)}",
                            f"mova-os para adapters/claude-code/skills.json (chave '{skill.name}'); a skill canônica leva só campos portáveis (D15)")
                    claude_data = skills.with_extras(text, overlay.get(skill.name, {})).encode("utf-8")
                except ValueError as exc:
                    if isinstance(exc, RenderError):
                        raise
                    raise RenderError(f"core/skills/{skill.name}/SKILL.md: {exc}", "corrija o frontmatter da skill") from exc
            files[f".agents/skills/{skill.name}/{rel}"] = data
            files[f".claude/skills/{skill.name}/{rel}"] = claude_data
    return files, notes


def apply(target: Path, files: dict[str, bytes]) -> list[str]:
    """Grava só o que mudou. Devolve os caminhos alterados."""
    changed = []
    for rel, data in files.items():
        path = target / rel
        if path.exists() and path.read_bytes() == data:
            continue
        _fsx.write_atomic(path, data)
        changed.append(rel)
    return changed


def render(target: Path, core_root: Path = CORE_ROOT, command: str | None = None) -> Result:
    try:
        files, notes = plan(target, core_root, command)
    except RenderError as exc:
        return Result(exc.status, [f"RENDER  {'FAIL' if exc.status == 'fail' else 'USAGE'}  {exc.what}"], next=exc.instead,
                      errors=[{"code": "RENDER", "message": exc.what}])
    changed = apply(target, files)
    head = f"RENDER  OK  {len(changed)} arquivo(s) alterado(s)" if changed else "RENDER  OK  nada mudou"
    return Result("ok", [head, *(f"  {rel}" for rel in changed), *(f"  aviso: {n}" for n in notes)],
                  data={"changed": changed})


def run(args) -> Result:
    if args.tools != ADAPTER:
        return Result("usage", [f"RENDER  ferramenta '{args.tools}' não suportada"],
                      next="Use --tools claude-code; Cursor e Codex chegam na Etapa 3 (trilha 3C).")
    return render(Path(args.target).resolve())
