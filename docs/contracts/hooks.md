# Contrato de hook neutro `hook/v0`

> Entrega 0.4 do [plano](../plan/plano-de-construcao.md). Schemas: [hook-event](../../core/schemas/hook-event.schema.json) e [hook-result](../../core/schemas/hook-result.schema.json). Fatos da ferramenta: [claude-code-facts.md](../plan/etapa-0/claude-code-facts.md).
> **Por quê:** os eventos das ferramentas são parecidos, mas nome, entrada e saída mudam (HG §4.1). O hook do núcleo decide; o adaptador só traduz (HG §1.4).

## Fluxo

```
ferramenta ──stdin nativo──► harness hook <nome> --adapter <ferramenta>
                                 │ 1. adapters/<ferramenta>: nativo → hook-event (neutro)
                                 │ 2. core/hooks/<nome>: hook-event → hook-result
                                 │ 3. adapters/<ferramenta>: hook-result → stdout/stderr/exit nativos
ferramenta ◄──saída nativa───────┘
```

O passo 2 nunca vê o formato nativo, e o hook do núcleo pode ser testado só com JSON neutro. Os passos 1 e 3 são testados com os pares `tests/fixtures/<ferramenta>/<caso>.{native,neutral}.json`.

## Entrada: `hook-event`

| Campo | Regra |
| --- | --- |
| `contract` | sempre `"hook/v0"` |
| `event` | `pre_tool`, `post_edit`, `stop`, `session_start`, `pre_compact` |
| `source.tool` | `claude-code`, `cursor`, `codex` (ou `test`) |
| `session.projectDir` | raiz do hospedeiro. Em worktree, é a raiz **da worktree** (resolvida pelo `cwd`, não por `CLAUDE_PROJECT_DIR`, que não muda) |
| `tool.kind` | `shell` (exige `command`), `write` (exige `paths`), `read`, `other`. É contra isso que os matchers `shell:<glob>` e `write:<glob>` casam |
| `tool.paths` | relativos a `projectDir`, com `/`. O adaptador normaliza `\` e caminhos absolutos |
| `stop.reentry` | `true` se a ferramenta já está continuando por causa de um bloqueio (`stop_hook_active`) |

Campos nativos que o núcleo não usa (transcript, `tool_use_id`, conteúdo do arquivo) não entram no evento. Se um hook precisar de um deles, o pedido segue o procedimento de [mudança de contrato](../plan/contract-changes.md).

## Saída: `hook-result`

Um **único objeto JSON no stdout**, com o exit code coerente:

| `decision` | Exit | Uso |
| --- | --- | --- |
| `allow` | 0 | segue. `context` (≤ 20 linhas) é injetado em `session_start` e `pre_compact` |
| `ask` | 0 | a ferramenta pede confirmação à pessoa (só em `pre_tool`). Exige `message` |
| `block` | 2 | impede a ação: a ferramenta, a parada ou a compactação. Exige `message` |

`message` tem três campos obrigatórios, e é assim que o P15 vira contrato: **`what`** (o que falhou), **`why`** (a regra e a sua origem) e **`instead`** (o que fazer no lugar, com o comando exato). Cada campo tem até 300 caracteres. Para o Claude Code, o adaptador junta os três numa mensagem só, no stderr, quando o exit é 2.

O `hook-result` não leva a mensagem nativa: montá-la é trabalho do adaptador.

## Eventos e hooks do núcleo previstos

| Evento | Hook do núcleo | Etapa | Decisões possíveis |
| --- | --- | --- | --- |
| `stop` | `stop_gate` (S4) | 1C | `block` se há task `in-progress` sem gate verde na árvore atual **e** sem blocker; `allow` caso contrário |
| `pre_tool` | `boundary_guard` (S5) | 3S | `block` para `never`, `ask` para `ask`, `allow` para o resto |
| `post_edit` | `post_edit` (S6) | 3S | `allow` com `context`; `block` só para devolver a mensagem do linter ao agente |
| `session_start` | `session_bootstrap` (M3) | 3C | sempre `allow`, com `context` ≤ 20 linhas |
| `pre_compact` | `handoff_guard` (M5) | 3C | `block` se o handoff do STATE.md está velho; `allow` com `context` caso contrário |

## Limite de reentradas

O Stop gate não pode prender o agente para sempre. Ao bloquear, o `stop_gate` conta as reentradas consecutivas daquela task num arquivo de estado em `.harness/runs/` (o `stop.reentry` da ferramenta só diz se houve **ao menos uma**). Quando a contagem chega a `limits.stopReentries` (padrão 3), a mensagem muda: **registre o blocker** (`harness task block <ID> --reason …`) para poder encerrar. O padrão fica abaixo do teto de 8 continuações do Claude Code, para que o harness, e não a ferramenta, decida o que acontece no limite.

## Falhas

Um hook do núcleo que levanta exceção ou sai com código diferente de 0 e de 2 é uma **falha do hook**, não uma decisão. Cada hook declara a sua política:

| Hook | Em caso de falha | Motivo |
| --- | --- | --- |
| `stop_gate` | **fail-closed**: o adaptador converte a falha em `block`, com a mensagem "hook falhou: rode `harness doctor`; para encerrar, registre o blocker", limitado pelas reentradas | uma falha silenciosa liberaria o encerramento com vermelho, que é exatamente o que o S4 existe para impedir |
| `boundary_guard` | fail-closed para `never`; fail-open para o resto | a regra `never` é a que tem `instead`; o resto vira atrito |
| `post_edit`, `session_bootstrap`, `handoff_guard` | **fail-open**, com aviso | são guias, não portões |

No Claude Code, o exit 1 não bloqueia. Por isso o fail-closed precisa ser implementado no passo 3 do adaptador (`harness hook` captura a falha e sai com 2), não deixado para a ferramenta. A partir da v2.1.295, `onFailure: "block"` é uma alternativa nativa (ver os fatos).

## Garantias e limites (ADR-0003)

O hook vê o que a ferramenta mostra a ele. Na fase 0, `pre_tool` com `kind: shell` só enxerga o texto do comando, e a própria doc do Claude Code diz que regras sobre esse texto não são uma fronteira de segurança. Qualquer documentação de hook que fale em "protege X" precisa citar a linha correspondente da tabela de limites da ADR-0003.
