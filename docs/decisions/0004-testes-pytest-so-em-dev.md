---
status: accepted
date: 2026-10-30
deciders: mateus
---

# 0004 `pytest` só como dependência de desenvolvimento; o que é vendorizado usa só a stdlib

## Contexto e problema

O código que vai para o hospedeiro (`core/`, `adapters/`) é Python 3 só com a stdlib (D4; HG §8.2; BF §3.3). Este repo, porém, precisa de testes. E o test guard do harness lê JUnit XML, então os testes do próprio repo podem servir de primeiro cliente dele (dogfooding). É a decisão E0-d.

## Opções consideradas

1. `unittest` da stdlib.
2. `pytest` como dependência de dev, com relatório `--junitxml`.

## Decisão

Opção 2, com quatro regras:

- `pytest` e `jsonschema` ficam em `[dependency-groups].dev` do `pyproject.toml`. Nada em `core/` ou `adapters/` importa um deles.
- O validador de schema que roda no hospedeiro é `core/lib/schema.py` (stdlib). O `jsonschema` serve só para **conferir** esse validador nos testes.
- O CI roda `python -m pytest --junitxml=reports/junit.xml` em Linux, macOS e Windows, com Python 3.10 e 3.13. A mínima é 3.10.
- A partir da Etapa 2, o próprio `harness gate` roda essa suíte neste repo (plano §8).

## Consequências

- Bom: fixtures e parametrização baratas; o JUnit do repo vira fixture real para o parser do 1A.
- Ruim: quem contribui precisa de um venv (`python -m venv .venv && .venv/bin/pip install pytest jsonschema`).
- Como verificar: `tests/contract/test_stdlib_only.py` reprova qualquer import fora da stdlib em `core/` e `adapters/`.
