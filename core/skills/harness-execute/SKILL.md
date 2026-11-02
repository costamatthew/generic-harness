---
name: harness-execute
description: Executa uma task do tasks.json pelo loop L1 (ler, implementar, gate, corrigir, verificar, concluir). Use quando a pessoa pedir para implementar, executar ou continuar uma task com ID (ex.: T1), ou quando o Stop gate bloquear o encerramento. Só o CLI harness escreve evidência; esta skill nunca edita tasks.json nem .harness/runs.
license: MIT
compatibility: Requer o CLI harness (python3 .harness/bin/harness) no hospedeiro e um perfil válido.
metadata:
  etapa: "1"
  componente: G4
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

# harness-execute

Executa **uma task por vez** até o gate verde na árvore atual. Fonte: loop L1 do cap. 17; "pronto" é decidido por sensor, não por palavra do agente (cap. 12 e 13). Na Etapa 1 só existe o L1: sem workers, e a profundidade máxima é 1 (o `harness-verifier` e o `explorer`). Para decidir quando delegar leitura, veja [references/decision-tree.md](references/decision-tree.md) (cap. 11).

Comando do CLI: `python3 .harness/bin/harness <comando>` (abaixo abreviado `harness`). Use `harness --json ...` se precisar do envelope.

## Loop L1 (cap. 17)

1. **Ler.** Abra a task em `tasks.json` e o `task.md` dela, e leia o `STATE.md` (decisões, blockers, handoff). Comando de apoio: `harness task status <ID>`. Fique no escopo: arquivos e `dod.commands` da task. Se o escopo parecer errado, vá ao passo 8 de bloqueio (`task block`), não alargue.
2. **Implementar** só o que a task pede, com os testes dela. Não apague nem enfraqueça teste para ficar verde; se um teste parecer errado, registre um blocker.
3. **Gate.** Rode `harness gate <ID>`. Ele roda os `dod.commands` do perfil e grava o manifesto em `.harness/runs/`.
4. **Corrigir.** Se o exit for 1, leia as linhas `arquivo:linha` da saída, corrija e volte ao passo 3. No máximo `limits.maxFixIterations` vezes (perfil). Estourou: `harness task block <ID> --reason "<o que falha>" --needs "decisão humana"` e pare.
5. **Verificar.** Com o gate verde, chame o subagente `harness-verifier` com **contexto limpo**: passe só o `<ID>`, os `dod.checks`, a `tree` (7 hex) do gate e a lista de arquivos tocados. **Não passe `model` na chamada**: o modelo vem do pin do papel e só vale assim (D31). Não passe o histórico da conversa nem a sua opinião de que está pronto (cap. 13).
6. **Registrar.** Copie a resposta do verifier, sem editar, para a seção `### Verifier <ID>` de `validation.md` (fora do bloco de evidência gerenciado). Se algum check vier `não atende`, volte ao passo 2 (conta como iteração do passo 4).
7. **Concluir.** Rode `harness task done <ID>`. Só ele muda o status e grava a evidência. Depois `harness state --handoff "<o que foi feito, o que falta, riscos>"`.
8. **Commit.** Proponha à pessoa o commit que o `task done` sugeriu (linha `→`). Não faça push nem merge.

## O que fazer em cada saída do CLI

| Exit | Significa | Faça |
| --- | --- | --- |
| 1 | verificação vermelha | corrija o código (passo 4) e rode o gate de novo |
| 3 | sensor ausente (comando `planned`) | **não improvise outro comando** (ex.: um `pytest` avulso não vale como gate). Siga a task que cria o sensor; se não houver, `harness task block <ID> --reason "sensor ausente: <comando>"` |
| 4 | recusado (verde antigo, árvore mudou) | você editou depois do gate: rode `harness gate <ID>` de novo e então repita o passo atual |
| 10 | trilha dona não entregou | `harness task block <ID> --reason "comando não implementado: <comando>, trilha <X>"` citando a trilha da mensagem |
| 2 ou 5 | uso errado ou erro interno | corrija a chamada (2); rode `harness doctor` e registre o blocker (5) |

Fonte: tabela de códigos de saída do contrato do CLI (`docs/contracts/cli.md`) e cap. 12.

## Stop gate (cap. 12)

Se tentar encerrar com uma task `in-progress` sem gate verde na árvore atual e sem blocker, o Stop gate devolve uma mensagem de bloqueio. Ela **não é erro a contornar**: significa que a task não tem evidência. Faça no lugar: rode `harness gate <ID>` e conclua pelo passo 7, ou, se não consegue, `harness task block <ID> --reason "<motivo>" --needs "<o que falta>"`. O `task block` é o único encerramento legítimo. Depois de algumas reentradas a mensagem pede o blocker explicitamente: registre-o.

## Proibido (e o que fazer no lugar)

- Não escreva em `tasks.json`, `.harness/runs/**`, no bloco de evidência de `validation.md` nem no perfil (ADR-0003), mesmo que o shell permita. No lugar: use `harness task done|block` e `harness state`. Precisa mudar o perfil? Registre um blocker pedindo a pessoa.
- Não declare a task pronta por conta própria. No lugar: gate verde + verifier + `task done`.
- Não chame o verifier com `model` nem com o seu raciocínio. No lugar: só ID, checks, `tree` e arquivos tocados.
- Não rode outro comando quando o exit for 3. No lugar: veja a tabela acima.
- Não faça trabalho fora do escopo da task. No lugar: anote em "Ideias para depois" do `STATE.md` e siga.
- Não faça push, merge nem `git add -A` cego. No lugar: proponha o commit com os arquivos da task.
