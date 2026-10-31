"""CLI único do harness (ADR-0001). Contrato em docs/contracts/cli.md.

Cada subcomando aponta para `core.cli.<módulo>:run`. Enquanto a trilha dona
não entrega o módulo, o subcomando responde `not-implemented` (exit 10) com o
envelope do contrato: as outras trilhas já podem chamar o CLI e tratar a resposta.

Uma implementação recebe `argparse.Namespace` e devolve `Result`.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

CONTRACT = "cli/v0"

EXIT = {
    "ok": 0,
    "fail": 1,
    "usage": 2,
    "sensor-absent": 3,
    "refused": 4,
    "error": 5,
    "not-implemented": 10,
}

DEFAULT_SUMMARY_LINES = 10


@dataclass
class Result:
    status: str
    summary: list[str]
    next: str | None = None
    data: dict = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    @property
    def exit(self) -> int:
        return EXIT[self.status]


# nome → (módulo de implementação, etapa/trilha dona, ajuda, argumentos)
# Argumentos: lista de (flags, kwargs do argparse). Mudar esta tabela é mudar o
# contrato: siga docs/plan/contract-changes.md.
_ID = (["id"], {"help": "ID da task (ex.: T5 ou PAG-12.T5)"})
_TARGET = (["--target"], {"default": ".", "help": "raiz do repo hospedeiro"})

COMMANDS: dict[str, tuple[str, str, str, list]] = {
    "gate": ("core.cli.gate", "1A", "roda os comandos da DoD e grava o manifesto", [
        _ID, (["--prove-sensor"], {"action": "store_true", "help": "prova vermelho → verde por mutação (2E, R05)"})]),
    "task done": ("core.cli.task", "1B", "conclui a task: gate verde na árvore atual → tasks.json + validation.md", [_ID]),
    "task block": ("core.cli.task", "1B", "registra um blocker (encerramento legítimo)", [
        _ID, (["--reason"], {"required": True}), (["--needs"], {})]),
    "task freeze": ("core.cli.task", "3A", "congela os testes da fase red", [_ID]),
    "task status": ("core.cli.task", "1B", "mostra o status das tasks", [(["id"], {"nargs": "?"})]),
    "state": ("core.cli.state", "1B", "mostra ou atualiza o handoff do STATE.md", [
        (["--handoff"], {"help": "texto do handoff"})]),
    "render": ("core.cli.render", "1C", "reescreve blocos gerenciados e arquivos do adaptador a partir do perfil", [
        _TARGET, (["--tools"], {"default": "claude-code"})]),
    "hook": ("core.cli.hook", "1C", "ponto de entrada dos hooks: lê o JSON nativo, normaliza, decide", [
        (["name"], {"help": "hook do núcleo, ex.: stop_gate"}), (["--adapter"], {"required": True})]),
    "detect": ("core.cli.bootstrap.detect", "2B", "inventário somente leitura → inventory.json", [_TARGET]),
    "plan": ("core.cli.bootstrap.plan", "2B", "dry-run do apply, com diff", [_TARGET]),
    "apply": ("core.cli.bootstrap.apply", "2B", "instala no hospedeiro (idempotente)", [
        _TARGET, (["--tools"], {"default": "claude-code"})]),
    "assess": ("core.cli.assess", "2F", "scorecard de prontidão → readiness.{md,json}", [_TARGET]),
    "backlog": ("core.cli.assess", "2F", "gera intake/READY-NNN.md a partir dos checks reprovados", [_TARGET]),
    "agents": ("core.cli.bootstrap.agents", "2D", "relatório do roster com o modelo resolvido", [_TARGET]),
    "scaffold": ("core.cli.genesis.scaffold", "2E", "roda um scaffolder do catálogo, com aprovação", [
        (["scaffolder"], {}), (["--name"], {"required": True})]),
    "doctor": ("core.cli.bootstrap.doctor", "3B", "sensor do próprio harness", [_TARGET]),
    "uninstall": ("core.cli.bootstrap.uninstall", "3B", "remove só o que o lock registra", [_TARGET]),
    "feature": ("core.cli.genesis.feature", "3E", "muda o status de uma feature em features.json", [
        (["id"], {}), (["status"], {})]),
    "profile from-adrs": ("core.cli.genesis.profile", "3E", "gera o perfil a partir dos ADRs aceitos", [_TARGET]),
    "genesis exit": ("core.cli.genesis.exit", "3E", "transição greenfield → brownfield (GF §8.1)", [_TARGET]),
    "spec validate": ("core.cli.spec", "4S", "validador estrutural da spec", [(["work_id"], {})]),
    "spec archive": ("core.cli.spec", "4S", "arquiva a spec preservando os ponteiros de evidência", [(["work_id"], {})]),
    "suggest": ("core.cli.bootstrap.suggest", "5U", "sugestões do catálogo → reports/suggestions.md", [_TARGET]),
    "update": ("core.cli.bootstrap.update", "5U", "merge de 3 vias a partir do lock", [_TARGET]),
    "validate": ("core.cli.harness", "E0", "valida um arquivo contra um schema de core/schemas", [
        (["schema"], {}), (["file"], {})]),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness", description="generic-harness CLI (contrato cli/v0)")
    parser.add_argument("--json", action="store_true", help="imprime o envelope cli/v0 em vez do resumo")
    sub = parser.add_subparsers(dest="cmd", metavar="<comando>")
    groups: dict[str, argparse._SubParsersAction] = {}
    for name, (_, owner, help_, args) in COMMANDS.items():
        head, _, tail = name.partition(" ")
        if tail:
            if head not in groups:
                gp = sub.add_parser(head, help=f"subcomandos de {head}")
                groups[head] = gp.add_subparsers(dest="subcmd", metavar="<ação>")
            p = groups[head].add_parser(tail, help=f"{help_} [{owner}]")
        else:
            p = sub.add_parser(head, help=f"{help_} [{owner}]")
        for flags, kwargs in args:
            p.add_argument(*flags, **kwargs)
        p.set_defaults(command=name)
    return parser


def dispatch(args: argparse.Namespace) -> Result:
    name = args.command
    module_name, owner, _, _ = COMMANDS[name]
    if name == "validate":
        return validate_file(args.schema, args.file)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name and module_name.startswith(exc.name):
            return not_implemented(name, owner)
        raise
    run = getattr(module, "run", None)
    if run is None:
        return not_implemented(name, owner)
    return run(args)


def not_implemented(name: str, owner: str) -> Result:
    return Result(
        status="not-implemented",
        summary=[f"harness {name}: ainda não implementado (trilha {owner})"],
        next="Não há substituto: registre um blocker se a sua task depende deste comando.",
    )


def validate_file(schema_name: str, file: str) -> Result:
    from core.lib import intake, schema

    path = Path(file)
    try:
        text = path.read_text(encoding="utf-8")
        instance = intake.parse(text) if path.suffix == ".md" else json.loads(text)
        errors = schema.validate(instance, schema_name)
    except FileNotFoundError as exc:
        return Result("usage", [f"VALIDATE {schema_name} {file}  arquivo não encontrado"],
                      errors=[{"code": "NOT_FOUND", "message": str(exc)}])
    except (ValueError, OSError) as exc:
        return Result("fail", [f"VALIDATE {schema_name} {file}  FAIL  ilegível"],
                      errors=[{"code": "UNREADABLE", "message": str(exc)}])
    if not errors:
        return Result("ok", [f"VALIDATE {schema_name} {file}  OK"])
    return Result(
        "fail",
        [f"VALIDATE {schema_name} {file}  FAIL  {len(errors)} erro(s)", *(f"  {e}" for e in errors)],
        next=f"Corrija os campos apontados; o contrato está em core/schemas/{schema_name}.schema.json.",
        errors=[{"code": "SCHEMA", "message": e} for e in errors],
    )


def render_text(result: Result, limit: int = DEFAULT_SUMMARY_LINES) -> str:
    lines = list(result.summary)
    if len(lines) > limit:
        hidden = len(lines) - (limit - 1)
        where = f" em {result.logs[0]}" if result.logs else ""
        lines = lines[: limit - 1] + [f"… (+{hidden} linhas{where})"]
    if result.next:
        lines.append(f"→ {result.next}")
    return "\n".join(lines)


def envelope(result: Result, command: str) -> dict:
    env = {"contract": CONTRACT, "command": command, "status": result.status,
           "exit": result.exit, "summary": result.summary}
    if result.next:
        env["next"] = result.next
    if result.data:
        env["data"] = result.data
    if result.logs:
        env["logs"] = result.logs
    if result.errors:
        env["errors"] = result.errors
    return env


def main(argv: list[str] | None = None) -> int:
    # No Windows o stdout padrão é cp1252; o contrato é UTF-8 em qualquer SO.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return EXIT["usage"]
    try:
        result = dispatch(args)
    except Exception as exc:  # o envelope precisa sair mesmo com bug na trilha
        result = Result("error", [f"harness {args.command}: erro interno: {exc.__class__.__name__}: {exc}"],
                        errors=[{"code": "INTERNAL", "message": str(exc)}])
    if args.json:
        print(json.dumps(envelope(result, args.command), ensure_ascii=False))
    else:
        print(render_text(result))
    return result.exit


if __name__ == "__main__":
    sys.exit(main())
