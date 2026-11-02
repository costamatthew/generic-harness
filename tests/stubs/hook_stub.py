"""Stub de hook do núcleo (contrato hook/v0) para a trilha 1C testar o adaptador
antes dos hooks reais existirem.

Lê um evento neutro no stdin e responde com a decisão pedida em
HARNESS_STUB_DECISION (allow | ask | block; padrão allow). Exit code segue o
contrato: 0 para allow/ask, 2 para block.
"""

from __future__ import annotations

import json
import os
import sys


def decide(event: dict, decision: str = "allow") -> dict:
    result = {"contract": "hook/v0", "hook": "stub", "decision": decision}
    if decision != "allow":
        result["message"] = {
            "what": f"stub bloqueou o evento {event['event']}",
            "why": "HARNESS_STUB_DECISION pediu esta decisão",
            "instead": "ajuste HARNESS_STUB_DECISION para allow",
        }
    return result


def main() -> int:
    # O contrato de hook é UTF-8 em qualquer SO; no Windows o stdio padrão é cp1252.
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    event = json.load(sys.stdin)
    result = decide(event, os.environ.get("HARNESS_STUB_DECISION", "allow"))
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result["decision"] == "block" else 0


if __name__ == "__main__":
    sys.exit(main())
