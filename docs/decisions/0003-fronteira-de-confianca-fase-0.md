---
status: accepted
date: 2026-10-30
deciders: mateus
---

# 0003 Fronteira de confiança na fase 0: só o CLI escreve o estado de aceite, e os limites ficam declarados

## Contexto e problema

O agente pode editar o código da task, mas o estado que diz "a task está pronta" precisa vir de um executor de confiança (HG §3.7, D9). Negar Write/Edit não basta: a doc do Claude Code diz que regras Bash não são fronteira de segurança, e que deny de arquivo não pega um script que abre o arquivo sozinho ([fatos](../plan/etapa-0/claude-code-facts.md#2-permissões)). É a decisão E0-c. O guia manda o enforcement em vez da instrução (cap. 12, princípio 3), e a avaliação pede que nenhuma garantia seja anunciada antes de ser demonstrada (HG §3.7).

## Opções consideradas

1. Prometer proteção completa já na fase 0.
2. Fase 0: CLI como único escritor + deny das ferramentas de edição + limites declarados. Fase 1 (trilha 3S): proteção do shell e suíte de contorno.
3. Executor isolado (sandbox ou processo separado) desde o início.

## Decisão

Opção 2.

**Insumos de aceite**, escritos só pelo CLI: `.harness/work/*/tasks.json`, `.harness/features.json` (campo `status`), `.harness/runs/**`, baselines do test guard e o bloco de evidência de `validation.md`. Arquivos que o agente não deve alterar sem a pessoa: `.harness/profile.json`, `.harness/harness.lock`, `.harness/bin/**`, `.claude/settings.json`.

**O que a fase 0 faz:**

- o adaptador compila deny de `Edit(...)` para esses caminhos (`Write(path)` nunca casa no Claude Code);
- `task done` só aceita um manifesto `pass` cujo `inputs.tree` seja igual ao hash atual da árvore e cujos hashes de log e relatório confiram;
- toda escrita é atômica e confere `revision`.

**Limites declarados na fase 0** (o que ainda não está protegido):

| Caminho de contorno | Estado na fase 0 |
| --- | --- |
| Shell escrevendo nos arquivos (`echo > tasks.json`, `python -c ...`, `sed -i`) | **não bloqueado** (deny de Edit pega parte dos comandos de arquivo, não scripts) |
| Rodar `harness task done` com um manifesto forjado | **parcialmente detectado**: árvore e hashes precisam bater, mas o manifesto não é assinado |
| Editar `profile.json` para trocar o comando de teste por `true` | **não bloqueado**; detectado só se o `profileSha256` do manifesto for comparado com o aprovado (fase 1) |
| Editar o próprio código do harness em `.harness/bin` | **não bloqueado** (deny de Edit cobre só as ferramentas de arquivo) |

## Consequências

- Bom: a fase 0 entrega o loop sem prometer o que não demonstrou; a 3S tem uma lista concreta de contornos para transformar em testes (`tests/bypass/`).
- Ruim: na fase 0, um agente determinado consegue marcar uma task como concluída por shell. O Stop gate e o verifier reduzem esse risco, mas não o eliminam.
- Como verificar: a integração 1I escreve esta tabela no relatório do piloto, e a 3S muda cada linha para "bloqueado", "detectado" ou "lacuna declarada", com teste.
