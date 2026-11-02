# Etapa 0: decisões e contratos

> Spec da [seção 3 do plano](../plano-de-construcao.md#3-etapa-0-decisões-e-contratos-sequencial), executada em sequência numa janela só. Data: 30–31/10/2026.
> Escopo: só a Etapa 0. Nenhum subcomando foi implementado, exceto `validate`, que serve para conferir os próprios contratos.

## Entregas

| ID | Entrega | Onde | Estado |
| --- | --- | --- | --- |
| 0.1 | Seção 1 e pilotos | [pilotos.md](pilotos.md) | **pilotos não escolhidos**, registrados como blocker da 1I; seção 1 segue como proposta |
| 0.2 | Esqueleto do repo | [AGENTS.md](../../../AGENTS.md) (< 100 linhas), [pyproject.toml](../../../pyproject.toml), [ci.yml](../../../.github/workflows/ci.yml), diretórios das trilhas (`.gitkeep`) | feito; CI ainda não rodou (ver critérios) |
| 0.3 | JSON Schemas v0 com exemplos | [core/schemas/](../../../core/schemas/) + [examples/](../../../core/schemas/examples/); validador stdlib [core/lib/schema.py](../../../core/lib/schema.py); parser de intake [core/lib/intake.py](../../../core/lib/intake.py) | feito |
| 0.4 | Contrato de hook neutro | [docs/contracts/hooks.md](../../contracts/hooks.md), schemas `hook-event` e `hook-result` | feito |
| 0.5 | Superfície do CLI | [docs/contracts/cli.md](../../contracts/cli.md), [core/cli/harness.py](../../../core/cli/harness.py), [bootstrap.py](../../../bootstrap.py), schema `cli-output` | feito |
| 0.6 | Formato dos catálogos | [docs/contracts/catalogs.md](../../contracts/catalogs.md), schemas `readiness-check`, `scaffolder`, `suggestion` | feito |
| 0.7 | Spike do Claude Code | [claude-code-facts.md](claude-code-facts.md) | feito (leitura de doc; confirmação em contract test fica com a 1C) |
| 0.8 | ADRs E0-a…E0-d | [docs/decisions/0001–0004](../../decisions/) + template MADR | feito |

## Schemas v0

Todos usam `"schema": 0` (exceto os de troca, que usam `contract`) e são provisórios até a 1I (plano §10).

| Schema | Arquivo no hospedeiro | Fonte | Válidos / inválidos |
| --- | --- | --- | --- |
| `profile` | `.harness/profile.json` | HG §3.1; BF §5.1, §15.8, §16.7; GF §4.1, §7.3 | 2 / 7 |
| `inventory` | `.harness/inventory.json` | BF §4, §5, §16.8; GF §3 | 2 / 2 |
| `tasks` | `.harness/work/<ID>/tasks.json` | HG M2, S2, §3.7 | 1 / 3 |
| `features` | `.harness/features.json` | GF §7.1 | 1 / 2 |
| `run-manifest` | `.harness/runs/<runId>/manifest.json` | HG §3.7; GF §4.2 | 2 / 3 |
| `harness-lock` | `.harness/harness.lock` | HG §4.2; BF §3.2, §9 | 1 / 2 |
| `intake` | `.harness/intake/<ID>.md` (forma parseada) | BF §6.3 | 1 / 2 |
| `hook-event`, `hook-result` | stdin/stdout dos hooks | HG §1.4, §4.1 | 5 / 3 · 3 / 2 |
| `cli-output` | `--json` de qualquer subcomando | HG §3.5 | 2 / 2 |
| `readiness-check`, `scaffolder`, `suggestion` | `core/catalog/**` | BF §15.2, §10.1; GF §6.2 | 2 / 2 · 1 / 2 · 1 / 2 |

Decisões de forma tomadas aqui (as pesquisas não fixavam):

- **Origem e status por valor** (BF §5.1 + GF §4.1): `origin` ∈ `ci | task-runner | manifest | docs | preset | env | human | decision:ADR-NNNN`, e `status` ∈ `detected | confirmed | planned | verified`. Só `verified` pode alimentar um gate.
- **`parallelSafe: false` exige `why`**, porque o isolamento é um julgamento que precisa de motivo (HG §3.1).
- **Pins só para `verifier` e `judge`** (D31), validados pelo schema.
- **Task `done` exige `evidence`** (runId, tentativa, manifesto, tree); task `blocked` exige `blocker`.
- **O hash da árvore é SHA-256 (`sha256-worktree-v0`)**, inclui mudanças não comitadas e declara `treeExcludes`. O algoritmo exato é da trilha 1A; o formato fica fixo aqui.
- **A mensagem de bloqueio de hook tem os campos `what`/`why`/`instead`**, o que transforma o P15 em contrato testável.

## O que cada trilha da Etapa 1 consome

Critério de saída: "todas as trilhas da Etapa 1 têm, para o que consomem, schema, exemplo e stub".

| Trilha | Consome | Schema | Exemplo | Stub |
| --- | --- | --- | --- | --- |
| **1A** gate | perfil (comandos), manifesto, envelope do CLI | `profile`, `run-manifest`, `cli-output` | `profile/valid-*`, `run-manifest/valid-*`, `cli-output/valid-gate-fail` | o dispatcher responde `not-implemented` até `core/cli/gate/` exportar `run` |
| **1B** task done e estado | manifesto do gate, tasks, envelope | `run-manifest`, `tasks`, `cli-output` | `tasks/valid`, `run-manifest/valid-pass` | [tests/stubs/gate_stub.py](../../../tests/stubs/gate_stub.py) (manifesto + envelope válidos, para pass, fail, sensor-absent e error) |
| **1C** render e adaptador Claude Code | perfil (boundaries, roles, models), evento e resultado de hook, fatos do Claude Code | `profile`, `hook-event`, `hook-result` | pares nativo→neutro em [tests/fixtures/claude-code/](../../../tests/fixtures/claude-code/) (5 eventos, incluindo reentrada e Windows) | [tests/stubs/hook_stub.py](../../../tests/stubs/hook_stub.py) (hook neutro com decisão configurável) |
| **1D** conteúdo | formatos de tasks, STATE e validation; papéis | `tasks`, `profile#roles` | `tasks/valid`, `profile/valid-brownfield-python` | não precisa: produz Markdown, conferido pelo verifier da trilha |
| **1G** fixtures | todos os schemas | todos | todos | os dois stubs acima, para escrever os cenários antes de 1A/1B/1C |

## Esclarecimento dos donos de diretório (plano §2.1)

A tabela do plano não dava dono a três módulos que a superfície do CLI cria. Esta proposta fica valendo até a pessoa revisar:

| Módulo | Dono | Motivo |
| --- | --- | --- |
| `core/cli/render/`, `core/cli/hook/` | **C** | são a ponte entre o perfil e os adaptadores |
| `core/cli/assess/` | **F** | o `assess` é o leitor do catálogo de prontidão, que é da F |
| `core/cli/spec/` | **D** (Etapa 4: 4S) | spec nativa, junto com a skill `harness-spec` |
| `core/schemas/`, `core/cli/harness.py`, `core/lib/schema.py` | **Etapa 0**; depois, só pelo procedimento de [mudança de contrato](../contract-changes.md) | são o contrato |

## Critério de saída

- [x] **Os schemas validam seus exemplos válidos e rejeitam os inválidos (`pytest`).** `tests/contract/test_schemas.py`: 13 schemas, 58 exemplos (24 válidos, 34 inválidos). Cada inválido é rejeitado pelo motivo pretendido, e o validador stdlib concorda com o `jsonschema` de referência em todos os exemplos.
- [x] **Todas as trilhas da Etapa 1 têm schema, exemplo e stub para o que consomem.** Tabela acima; os stubs são cobertos por `tests/contract/test_stubs.py`.
- [x] **Pilotos escolhidos e registrados, ou a falta registrada como blocker da 1I.** Falta registrada em [pilotos.md](pilotos.md).
- [x] **CI verde nos três sistemas operacionais.** Run [41375182714](https://github.com/costamatthew/generic-harness/actions/runs/41375182714) no commit `bc75beb`: ubuntu, macos e windows × Python 3.10 e 3.13, todos `success`. As três execuções anteriores falhavam só no Windows: o `hook_stub` escrevia em cp1252. Corrigido em `bc75beb`.
