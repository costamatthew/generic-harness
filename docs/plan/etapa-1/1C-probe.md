# 1C: probe dos fatos do Claude Code

> Exigência do spike 0.7 e do item 4 da [spec 1C](1C.md). Feito em 01/11/2026 com o `claude` real, **versão 2.1.316 (Claude Code)**, em repos descartáveis criados com `git init` fora do projeto, com `claude -p` não interativo (`</dev/null`, senão ele espera 3 s pelo stdin). Modelos baratos (`haiku`). Resultado: os cinco fatos confirmados, **nenhuma divergência**, então não há item em `contract-changes.md`.

| Fato | Resultado | Evidência |
| --- | --- | --- |
| (a) exit 2 + stderr no `Stop` faz o agente continuar e recebe a razão | **provado** | Hook que sai com 2 nas duas primeiras chamadas, com `RAZAO: inclua a palavra CARAMBOLA na sua resposta final.` no stderr. A resposta final do agente foi `feito, CARAMBOLA`; o hook foi chamado 3 vezes. |
| (b) `stop_hook_active` chega `true` na reentrada | **provado** | O log do hook registrou `false` na 1ª chamada e `true` na 2ª e na 3ª. O stdin traz também `prompt_id`, `effort`, `background_tasks`, `session_crons` (que o adaptador ignora). |
| (c) forma do `Edit(...)` que bloqueia | **provado**: `Edit(.harness/work/*/tasks.json)` (relativo à raiz) | Três formas negaram a ferramenta Edit e deixaram o arquivo intacto: relativa, `Edit(/.harness/work/*/tasks.json)` e `Edit(//<absoluto>/…)`. A forma relativa é a usada pelo render. Com `Write(.harness/work/*/tasks.json)` a ferramenta Edit **passou** e alterou o arquivo (consistente com o fato §2 de que `Write(path)` não protege). Com regras `Edit(...)` para `.harness/work/*/tasks.json`, `.harness/runs/**`, `.harness/harness.lock` e `.harness/bin/**`, a ferramenta **Write** também foi negada nos quatro arquivos (4 `permission_denials`, nenhum arquivo alterado). |
| (d) `model` com ID completo no frontmatter é o modelo do sub-agent | **provado** | Sub-agent com `model: claude-haiku-5-5`, conversa em `--model sonnet`. O `modelUsage` do resultado listou `claude-sonnet-5-5` e `claude-haiku-5-5`, e o sub-agent respondeu. Não foi testada a precedência com `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` (é do `doctor`, 3B). |
| (e) o AGENTS.md é lido sem CLAUDE.md | **provado** | Sem CLAUDE.md e com `--tools ""` (nenhuma ferramenta), o agente respondeu a palavra que só existe no AGENTS.md (`ABACAXI-7`). Com um `CLAUDE.md` que não importa `@AGENTS.md`, nas mesmas condições, respondeu `DESCONHECIDA` e disse que o AGENTS.md não está no contexto. |

Observações para quem for reproduzir: a prova do (e) precisa de `--tools ""`; sem isso o agente abre o AGENTS.md com Read/Grep e o resultado engana (foi o que aconteceu na primeira tentativa). O `claude -p` usa `--allowedTools` para liberar Edit/Write sem pergunta; as regras de `deny` valem mesmo assim.

## Como repetir

```bash
# (a) e (b): .claude/settings.json com hooks.Stop apontando para um script que loga o stdin e sai 2 nas duas primeiras chamadas
claude -p "responda apenas: feito" --model haiku </dev/null
# (c)
claude -p 'Use a ferramenta Edit para trocar "a" por "b" em .harness/work/X/tasks.json' --model haiku --allowedTools Edit Write --output-format json </dev/null
# (d)
claude -p "Use o sub-agent harness-probe e repita a resposta dele." --model sonnet --output-format json </dev/null   # ver modelUsage
# (e)
claude -p "Qual é a palavra secreta do repo? Se não souber, diga DESCONHECIDA." --model haiku --tools "" </dev/null
```

## Não coberto aqui

- O comportamento **interativo** (a mensagem aparecendo na TUI) e o teto de 8 continuações não foram exercitados: o `-p` provou o laço de reentrada, e o limite do harness (`limits.stopReentries`, padrão 3) fica abaixo do teto por construção.
- `SubagentStop` fica fora de propósito (ver a spec): só `Stop` é instalado.
