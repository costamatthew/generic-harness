---
status: accepted
date: 2026-10-30
deciders: mateus
---

# 0001 Um só CLI, `harness`, com `bootstrap.py` como shim do primeiro uso

## Contexto e problema

A HG fala em `harness <cmd>` (HG §3.2, §8.1), enquanto o BF e o GF falam em `bootstrap.py <cmd>` (BF §3.2, §9; GF §6). Dois CLIs dobrariam a superfície que as trilhas precisam respeitar e a documentação que o agente precisa ler (cap. 5: contexto é orçamento). É a decisão E0-a do plano.

## Opções consideradas

1. Dois CLIs: `bootstrap.py` para instalar e `harness` para operar.
2. Um CLI `harness` com subcomandos; `bootstrap.py` na raiz do generic-harness só encaminha para ele.

## Decisão

Opção 2. O hospedeiro recebe `.harness/bin/harness` (cópia vendorizada, ADR-0004). O clone usa `python3 bootstrap.py <cmd> --target <repo>`, que chama o mesmo código. A superfície é a de [docs/contracts/cli.md](../contracts/cli.md), e a tabela executável é `COMMANDS` em `core/cli/harness.py`.

## Consequências

- Bom: um contrato, uma tabela de códigos de saída e um envelope `--json`; o `BOOTSTRAP.md` (2B) e as skills citam os mesmos comandos.
- Ruim: o CLI vendorizado carrega subcomandos de instalação que o hospedeiro raramente usa (custo só em disco, não em contexto).
- Como verificar: `tests/contract/test_cli_surface.py` exige que todo subcomando responda com envelope válido e com exit code coerente.
