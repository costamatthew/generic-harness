"""`harness hook <nome> --adapter <ferramenta>` (docs/contracts/hooks.md, Fluxo).

Exceção ao envelope cli/v0: lê o JSON nativo no stdin e responde no formato
nativo (stdout, stderr e exit). Só erro de uso (nome ou adaptador inválido)
devolve o envelope, porque aí não há evento para decidir.

Passos: 1) o adaptador traduz nativo → hook-event; 2) `core.hooks.<nome>.decide`
devolve o hook-result, validado contra o schema; 3) o adaptador traduz de volta.
Falha do hook: fail-closed para `stop_gate` (bloqueia), fail-open com aviso nos demais.
"""

from __future__ import annotations

import importlib
import json
import re
import sys

from core.cli.harness import Result
from core.hooks import _loader
from core.lib import schema

FAIL_CLOSED = {"stop_gate"}
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def failure_message(name: str, exc: BaseException) -> dict:
    detail = f"{exc.__class__.__name__}: {exc}".replace("\n", " ")
    return {
        "what": f"hook falhou: {name} não produziu uma decisão válida ({detail})"[:300],
        "why": "uma falha de hook não é decisão; o stop_gate é fail-closed (S4, hooks.md) para o vermelho não passar em silêncio",
        "instead": "rode `harness doctor`; para encerrar, registre o blocker com `harness task block <ID> --reason …`",
    }


def process(name: str, adapter: str, raw: str) -> tuple[int, str, str]:
    """Os três passos, com a política de falha. Devolve (exit, stdout, stderr)."""
    translate = _loader.load(adapter, "translate")
    closed = name in FAIL_CLOSED
    try:
        event = translate.to_neutral(json.loads(raw))
        errors = schema.validate(event, "hook-event")
        if errors:
            raise ValueError("evento neutro inválido: " + "; ".join(errors[:3]))
        module = importlib.import_module(f"core.hooks.{name}")
        result = module.decide(event)
        errors = schema.validate(result, "hook-result")
        if errors:
            raise ValueError("hook-result inválido: " + "; ".join(errors[:3]))
        return translate.to_native(result, event)
    except Exception as exc:  # noqa: BLE001 - qualquer falha cai na política do hook
        return translate.failure_native(name, failure_message(name, exc), closed)


def run(args) -> Result:
    name, adapter = args.name, args.adapter
    if not _NAME.match(name):
        return Result("usage", [f"HOOK {name}  nome inválido"],
                      next="Use o nome de um módulo de core/hooks, ex.: stop_gate.")
    try:
        _loader.load(adapter, "translate")
    except ImportError as exc:
        return Result("usage", [f"HOOK {name}  adaptador '{adapter}' indisponível: {exc}"],
                      next="Use --adapter claude-code (Cursor e Codex chegam na Etapa 3).")
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raw = sys.stdin.read()
    code, out, err = process(name, adapter, raw)
    if err:
        print(err, file=sys.stderr)
    print(out)
    sys.stdout.flush()
    raise SystemExit(code)
