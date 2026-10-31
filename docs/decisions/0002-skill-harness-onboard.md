---
status: accepted
date: 2026-10-30
deciders: mateus
---

# 0002 A skill de onboarding se chama `harness-onboard`

## Contexto e problema

A HG chama a skill de `harness-onboard` (HG G6); o BF, de `factory-onboard` (BF §3.2, §9). O nome é parte do contrato: ele aparece no diretório da skill, no `BOOTSTRAP.md` e na contagem do teto de skills (cap. 5). É a decisão E0-b.

## Opções consideradas

1. `factory-onboard`.
2. `harness-onboard`.

## Decisão

Opção 2. Todas as skills do harness usam o prefixo `harness-`, que evita colisão com as do time (BF §4.2, N2) e deixa claro de onde a skill veio. O teto de 6 skills do harness (HG §3.2, §4.4) fica:

| Skill | Etapa |
| --- | --- |
| `harness-execute` | 1 |
| `harness-prepare` (com `references/greenfield.md`, D35) | 2 |
| `harness-onboard` | 3 |
| `harness-retro` | 3 |
| `harness-spec` | 4 |
| `harness-review` | 4 |

## Consequências

- Bom: um prefixo só para skills, sub-agents (`harness-<papel>`) e blocos (`harness:*`).
- Ruim: o BF precisa ser lido trocando `factory-onboard` por `harness-onboard` (a pesquisa não é reescrita).
- Como verificar: na Etapa 3, o `doctor` acusa skill do harness sem o prefixo ou acima do teto.
