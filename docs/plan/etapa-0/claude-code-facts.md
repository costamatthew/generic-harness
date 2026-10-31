# Claude Code: fatos verificados para o adaptador (spike 0.7)

> **[Externo]** Leitura da documentação atual em 30/10/2026: [hooks](https://code.claude.com/docs/en/hooks), [sub-agents](https://code.claude.com/docs/en/sub-agents), [skills](https://code.claude.com/docs/en/skills), [permissions](https://code.claude.com/docs/en/permissions) e [memory](https://code.claude.com/docs/en/memory). Nada foi executado: são fatos de documentação. A trilha 1C confirma cada um num contract test antes de depender dele.
> **Para que serve:** revalida a HG §4.1 e a BF §16.4. As divergências estão na seção 6.

## 1. Hooks

**Onde ficam.** `.claude/settings.json` (projeto, comitado), `.claude/settings.local.json`, `~/.claude/settings.json`, managed settings, `hooks/hooks.json` de plugin e frontmatter de skill ou de sub-agent.

**Estrutura.** São três níveis: evento → grupo com `matcher` → lista de handlers.

```json
{ "hooks": { "PreToolUse": [ { "matcher": "Bash", "hooks": [
  { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.harness/bin/harness hook boundary_guard --adapter claude-code", "timeout": 30 }
] } ] } }
```

- `matcher`: omitido, `""` ou `"*"` casa com tudo. Letras, dígitos, `_`, `-`, espaço, `,` e `|` formam um nome exato ou uma lista (`Edit|Write`). Qualquer outro caractere transforma o matcher numa regex JavaScript sem âncora.
- Campos do handler `command`: `command`, `args` (forma exec, sem shell), `timeout` (segundos; padrão 600), `if` (sintaxe de regra de permissão, por exemplo `Bash(git *)`, só em eventos de ferramenta), `shell` (`bash` ou `powershell`), `async`, `once`, `onFailure` (`continue` ou `block`, v2.1.295+), `statusMessage`.
- Variável de ambiente: `CLAUDE_PROJECT_DIR` é a raiz onde a sessão começou e **não muda** quando o agente entra numa worktree. Ela **não vem no stdin**.

**Eventos que o contrato neutro usa** (a doc lista 33):

| Neutro | Claude Code | Campos específicos no stdin |
| --- | --- | --- |
| `pre_tool` | `PreToolUse` | `tool_name`, `tool_input`, `tool_use_id` |
| `post_edit` | `PostToolUse`, com matcher `Edit\|Write\|NotebookEdit` | `tool_name`, `tool_input`, `tool_response`, `tool_use_id`, `duration_ms` |
| `stop` | `Stop` (e `SubagentStop` nos workers) | `stop_hook_active`, `last_assistant_message`, `background_tasks`, `session_crons` |
| `session_start` | `SessionStart` | `source` (`startup`, `resume`, `clear`, `compact`, `fork`), `model` |
| `pre_compact` | `PreCompact` | `trigger` (`manual`, `auto`), `custom_instructions` |

**Campos comuns:** `session_id`, `prompt_id`, `transcript_path`, `cwd`, `permission_mode`, `effort`, `hook_event_name`. Dentro de um sub-agent, vêm também `agent_id` e `agent_type`.

**`tool_input` por ferramenta:**

| Ferramenta | Campos |
| --- | --- |
| Bash | `command`, `description`, `timeout` (ms), `run_in_background` |
| Write | `file_path` (absoluto), `content` |
| Edit | `file_path`, `old_string`, `new_string`, `replace_all` |
| Read | `file_path`, `offset`, `limit` |

No Windows, os caminhos chegam com `\`, mesmo no Git Bash. Sem Git Bash, a ferramenta Bash não é registrada, e quem roda os comandos é a PowerShell. O matcher precisa ser `Bash|PowerShell`.

**Exit codes:**

| Exit | Efeito |
| --- | --- |
| 0 | Sucesso. O stdout é lido como JSON se for um único objeto. Ele só entra no contexto do modelo em `SessionStart`, `UserPromptSubmit` e mais dois eventos; nos outros, vai para o log de debug |
| 2 | Bloqueia nos eventos que aceitam bloqueio: `PreToolUse`, `Stop`, `SubagentStop`, `PreCompact` e outros. O **stderr** vira a razão entregue ao modelo. O JSON ainda é lido, mas não desfaz o bloqueio. Em `PostToolUse` não há o que bloquear (a ferramenta já rodou): o stderr só é mostrado ao modelo |
| outro | Erro não bloqueante: a ação segue e aparece um aviso com a primeira linha do stderr. **Exit 1 não bloqueia** |

**Saída JSON:**

- Campos universais: `continue` (se `false`, o agente para), `stopReason`, `systemMessage` (aviso para a pessoa) e `suppressOutput` (sem efeito).
- `decision: "block"` + `reason` funciona em `PostToolUse`, `Stop`, `SubagentStop`, `PreCompact` e outros.
- `PreToolUse`: `hookSpecificOutput.permissionDecision` (`allow`, `deny`, `ask` ou `defer`), `permissionDecisionReason` e `updatedInput`. Quando vários hooks respondem, a precedência é `deny` > `defer` > `ask` > `allow`.
- `hookSpecificOutput.additionalContext`: aceito em `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop` e outros. Vai embrulhado num system reminder, com teto de 10.000 caracteres. No `SessionStart`, o stdout em texto puro também entra no contexto.
- `PreCompact` descarta `systemMessage` e `continue`. Exit 2 ou `decision: "block"` impede a compactação. Bloquear uma compactação automática disparada por erro de limite de contexto faz a requisição falhar.

**Loop do Stop.** `stop_hook_active` é `true` quando o agente já está continuando por causa de um Stop hook. Além disso, há um **teto de 8 continuações consecutivas**: depois disso, o Claude Code ignora o bloqueio e encerra o turno. O contador zera a cada chamada de ferramenta e pode ser alterado por `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`.

**Concorrência.** `PostToolUse` roda uma vez por ferramenta, então pode rodar em paralelo quando há chamadas paralelas.

## 2. Permissões

- `permissions.allow`, `permissions.ask` e `permissions.deny` em `settings.json`. A ordem de avaliação é deny → ask → allow, e a primeira que casar decide. Uma regra mais específica não muda essa ordem.
- **Hook × regras.** A decisão de um `PreToolUse` não fura as regras: um deny que casa bloqueia mesmo que o hook devolva `allow`. Um hook com exit 2 bloqueia antes das regras, mesmo com um allow que casaria.
- **Bash.** `*` casa com qualquer texto, inclusive espaços, e `Bash(git push *)` equivale a `Bash(git push:*)`. Os separadores `&&`, `||`, `;`, `|`, `&` e quebra de linha são reconhecidos: deny e ask se aplicam a qualquer subcomando, inclusive dentro de `$(...)`. Os wrappers `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin` e o `xargs` sem flags são removidos antes de casar.
- **Limite documentado, essencial para o E0-c:** uma regra Bash "não é uma fronteira de segurança em volta do programa". `Bash(git push *)` não pega `git -C . push`, `/usr/bin/git push`, `sh -c '...'` nem `git 'push'`. A doc manda usar sandbox para enforcement que não dependa do texto do comando.
- **Arquivos.** Só `Edit(path)` e `Read(path)` casam caminho: `Write(path)` é aceito e **nunca casa**. Para proteger escrita, use `Edit(...)`. Um deny de `Read` também bloqueia Edit e Write no mesmo caminho. Deny de Read/Edit vale para as ferramentas de arquivo, para `cat`, `sed`, `tee` e redirecionamentos `>`, mas **não** para um script Python ou Node que abre o arquivo sozinho.
- **Padrões de caminho** seguem o gitignore: `//abs`, `~/home`, `/relativo-ao-arquivo-de-settings`, `relativo-ao-cwd`.

## 3. Sub-agents

- Ficam em `.claude/agents/*.md` (projeto, varrido recursivamente). A identidade é o campo `name`, não o caminho do arquivo. Precedência: managed > `--agents` > projeto > usuário > plugin.
- **Frontmatter:** `name` (obrigatório, sem `:`), `description` (obrigatório), `tools`, `disallowedTools`, `model` (`sonnet`, `opus`, `haiku`, `fable`, ID completo como `claude-opus-5-5` ou `inherit`), `effort` (`low`, `medium`, `high`, `xhigh`, `max`), `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `isolation: worktree`, `color`, `omitClaudeMd`. Campos desconhecidos são ignorados sem erro.
- **Resolução do modelo:** parâmetro `model` da chamada (só alias) → `model` do arquivo → `CLAUDE_CODE_SUBAGENT_MODEL` → modelo da conversa. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` aplica a variável a **todos** os sub-agents.
- **Aninhamento:** até 3 níveis abaixo da conversa principal, com até 20 sub-agents concorrentes. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` limita a profundidade. Para impedir que um sub-agent dispare outros, omita `Agent` de `tools` ou ponha `Agent` em `disallowedTools`.
- **Plugin:** sub-agents de plugin ignoram `hooks`, `mcpServers`, `permissionMode` e `initialPrompt`.

**Pinagem do verifier (D31).** Um `model` com o ID completo no arquivo vence a variável global, a menos que `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` esteja ligada, e o parâmetro da chamada vence o arquivo. Portanto, o pin só é garantido se o `doctor` checar a variável **e** a skill não passar `model` na chamada.

## 4. Skills

- Ficam em `.claude/skills/<nome>/SKILL.md`, carregadas do diretório inicial até a raiz do repo e também em níveis aninhados (sob demanda). Pastas com symlink funcionam. **A doc não menciona `.agents/skills`.**
- **Frontmatter:** `name` (padrão: o nome do diretório), `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context: fork`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`, `compatibility`.
- **Portabilidade.** Fora do Claude Code (claude.ai, Skills API), só `name`, `description`, `license`, `compatibility`, `metadata` e `allowed-tools` são aceitos. Qualquer outra chave é **erro**. É o mesmo corte da HG §4.1: a skill canônica (`.agents/skills`) leva só esses campos, e o adaptador injeta o resto na cópia para `.claude/skills`.
- **Limites:** `description` + `when_to_use` são truncados em 1.536 caracteres na listagem. O `SKILL.md` deve ficar abaixo de 500 linhas. Depois de uma compactação, cada skill mantém os primeiros 5.000 tokens, num orçamento conjunto de 25.000.

## 5. Instruções (AGENTS.md)

- O Claude Code lê `AGENTS.md` nativamente desde a **v2.1.277**, mas **só se não houver** `CLAUDE.md`, `.claude/CLAUDE.md` ou `CLAUDE.local.md` no diretório de trabalho ou acima dele. Se houver um CLAUDE.md, ele lê só o CLAUDE.md, a menos que esse arquivo importe `@AGENTS.md`. `~/.claude/CLAUDE.md` e `.claude/rules/` não contam nesse teste.
- A doc recomenda menos de 200 linhas por arquivo. Fica o número do guia, < 100 com teto de 150 (cap. 4), como na HG §13.

## 6. Consequências para o plano

| Fato | Afeta | O que muda |
| --- | --- | --- |
| Exit 1 não bloqueia; só exit 2 | contrato hook/v0 | Erro interno de hook = exit ≠ 0 e ≠ 2 = **não bloqueia**. A política por hook está em [hooks.md](../../contracts/hooks.md#falhas) |
| A razão do bloqueio sai pelo stderr (exit 2), não pelo stdout | 1C | O adaptador escreve a mensagem P15 no stderr **e** o JSON nativo no stdout |
| Teto de 8 continuações e `stop_hook_active` | S4, 1C | O limite de reentradas do harness (`limits.stopReentries`, padrão 3) fica **abaixo** do teto da ferramenta, para o harness decidir antes dela: na reentrada N, ele exige um blocker registrado |
| `CLAUDE_PROJECT_DIR` não muda na worktree | 1C, M6 | Em worktree, o gate precisa usar o `cwd` (raiz da worktree), não o `CLAUDE_PROJECT_DIR`. Para isso, `harness hook` resolve a raiz pelo `git rev-parse --show-toplevel` a partir do `cwd` |
| `Write(path)` nunca casa | 3S, E0-c | O deny de escrita em `tasks.json` e afins é compilado como `Edit(...)`, e o contract test confirma |
| Regras Bash não são fronteira de segurança | E0-c, 3S | Confirma a ADR-0003: na fase 0, os limites são declarados; o shell continua alcançando os arquivos protegidos |
| `PostToolUse` roda em paralelo | S6 (fase 1) | O hook pós-edição não pode presumir que roda sozinho; precisa escrever de forma atômica |
| A skill canônica não pode ter campos extras fora do Claude Code | 1C, 1D | `core/skills/*/SKILL.md` leva só os campos portáveis; os extras ficam num arquivo de overlay do adaptador |
| Windows: `\` nos caminhos; Bash pode não existir | 1C | O adaptador normaliza para `/` relativo à raiz; o matcher é `Bash\|PowerShell`; o comando do hook é `python` com caminho absoluto, sem depender de bash |

**Divergências com a HG §4.1:** nenhuma de fundo. A HG não registrava quatro coisas: o teto de 8 continuações, o fato de `Write(path)` nunca casar, a falta de menção a `.agents/skills` nas skills do Claude Code (a cópia continua necessária, D15) e o `onFailure` (v2.1.295+), que pode substituir a política de falha nos hooks críticos quando a versão mínima do adaptador permitir.
