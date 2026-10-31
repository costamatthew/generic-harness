# Superfície do CLI `cli/v0`

> Entrega 0.5 do [plano](../plan/plano-de-construcao.md). Decisão: [ADR-0001](../decisions/0001-cli-unico-harness.md). Schema do envelope: [cli-output](../../core/schemas/cli-output.schema.json). Tabela executável: `COMMANDS` em [core/cli/harness.py](../../core/cli/harness.py).

## Invocação

| Onde | Comando |
| --- | --- |
| clone do generic-harness (primeiro uso) | `python3 bootstrap.py <comando> [--target <repo>]` |
| hospedeiro depois do `apply` | `python3 .harness/bin/harness <comando>` |
| este repo | `python3 -m core.cli.harness <comando>` |

O CLI é um só, com os mesmos subcomandos nas três formas. `--json` vale para qualquer subcomando e vem **antes** dele: `harness --json gate T5`.

## Códigos de saída

| Exit | `status` | Significado | Quem chama faz o quê |
| --- | --- | --- | --- |
| 0 | `ok` | passou | segue |
| 1 | `fail` | verificação vermelha (gate, schema, check) | corrige e roda de novo |
| 2 | `usage` | argumento errado ou arquivo inexistente | corrige a chamada |
| 3 | `sensor-absent` | um comando exigido está `planned` ou indisponível (GF §4.2) | **não improvisa outro comando**: segue a task que cria o sensor ou registra um blocker |
| 4 | `refused` | pré-condição não atendida: verde antigo, árvore mudou, falta aprovação, conflito de escrita | refaz o passo anterior (normalmente `gate`) |
| 5 | `error` | erro interno do harness | `harness doctor`, depois um blocker |
| 10 | `not-implemented` | a trilha dona ainda não entregou | registra um blocker se depender disto |

O 3 e o 4 existem para que "vermelho", "sensor não existe" e "evidência não vale" nunca sejam confundidos (HG §3.7; GF §4.2).

## Saída enxuta (padrão)

Sem `--json`, o CLI imprime as linhas de `summary` e, se houver `next`, uma última linha com `→ `. O teto é `limits.summaryLines` (padrão 10). O excedente vira `… (+N linhas em <log>)`, e o log completo fica em disco (cap. 10; HG §3.5). A primeira linha segue o formato:

```
<VERBO> <ID> <escopo>  <PASS|FAIL|ABSENT|REFUSED> exit=<n>  <dur>s  tree=<7 hex>
```

Exemplo (gate):

```
GATE T5 test.unit  FAIL exit=1  12.4s  tree=3f9c1e2
tests 41 (baseline 43, -2)  failed 1  skipped 0
  src/billing/payment.service.spec.ts:57  [PAG-03] recusado mantém carrinho
log: .harness/runs/20261030T141500Z-a1b2c3/test.unit.log
→ A contagem caiu 2 desde o congelamento. Restaure os testes ou peça aprovação humana (nível ask).
```

Falhas aparecem como `arquivo:linha`. A linha `→` é escrita para o agente (P15): ela diz o que fazer, não só o que deu errado.

## Envelope `--json`

```json
{ "contract": "cli/v0", "command": "gate", "status": "fail", "exit": 1,
  "summary": ["GATE T5 test.unit  FAIL exit=1 ..."], "next": "...",
  "data": { "manifest": ".harness/runs/<runId>/manifest.json" },
  "logs": [".harness/runs/<runId>/test.unit.log"],
  "errors": [{ "code": "SCHEMA", "message": "...", "where": "arquivo:linha" }] }
```

`status` e `exit` andam juntos, e o schema rejeita combinações incoerentes. `data` é livre por subcomando, e cada trilha documenta o seu `data` na própria spec.

## Subcomandos

| Comando | Trilha | O que faz | `data` mínimo |
| --- | --- | --- | --- |
| `gate <ID> [--prove-sensor]` | 1A (2E) | roda a DoD da task a partir do perfil e grava o manifesto | `manifest`, `runId` |
| `task done <ID>` | 1B | aceita só um manifesto `pass` com `inputs.tree` igual à árvore atual; grava `tasks.json` (atômico), `validation.md` e o STATE | `task`, `manifest` |
| `task block <ID> --reason <r> [--needs <n>]` | 1B | registra o blocker; libera o Stop gate | `task` |
| `task status [ID]` | 1B | mostra o status das tasks | `tasks` |
| `task freeze <ID>` | 3A | congela os testes da fase red | `frozen` |
| `state [--handoff <texto>]` | 1B | mostra ou atualiza o handoff | — |
| `render [--target] [--tools]` | 1C | reescreve blocos e arquivos do adaptador a partir do perfil (idempotente) | `changed` |
| `hook <nome> --adapter <ferramenta>` | 1C | ponto de entrada dos hooks ([hooks.md](hooks.md)). **Exceção:** fala o formato nativo da ferramenta no stdin e no stdout, não o envelope | — |
| `detect`, `plan`, `apply` | 2B | bootstrap (BF §9) | `inventory` / `diff` / `created` |
| `assess`, `backlog` | 2F | prontidão e backlog READY | `level`, `failed` |
| `agents` | 2D | roster com o modelo resolvido | `roles` |
| `scaffold <id> --name <n>` | 2E | scaffolder do catálogo, com aprovação | `ran` |
| `doctor`, `uninstall` | 3B | sensor do harness; remoção pelo lock | `findings` |
| `feature <ID> <status>`, `profile from-adrs`, `genesis exit` | 3E | gênese completa | — |
| `spec validate <ID>`, `spec archive <ID>` | 4S | spec nativa | — |
| `suggest`, `update` | 5U | sugestões; merge de 3 vias | — |
| `validate <schema> <arquivo>` | E0 | valida JSON (ou o Markdown de intake) contra `core/schemas/` | — |

**Implementar um subcomando:** crie o módulo indicado em `COMMANDS` (ex.: `core/cli/gate/__init__.py`) com `run(args) -> Result`. Subcomandos que dividem um módulo (`task done`, `task block`...) leem `args.command`. Uma mudança de nome, argumento ou código de saída é mudança de contrato ([procedimento](../plan/contract-changes.md)).

## Quem escreve o quê (ADR-0003)

Só o CLI escreve `tasks.json`, `features.json` (status), `runs/**`, baselines e o bloco de evidência de `validation.md`. Todo subcomando que escreve esses arquivos grava de forma atômica (arquivo temporário + `os.replace`) e confere `revision` antes de gravar.
