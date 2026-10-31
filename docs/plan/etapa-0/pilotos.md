# Pilotos (D5, D21, D45): blocker da integração 1I

> Entrega 0.1 do [plano](../plano-de-construcao.md). A escolha é da pessoa (P10): o plano não escolhe repositório por ela.

**Status em 31/10/2026: NÃO ESCOLHIDOS.** Isso bloqueia só a integração 1I e as seguintes. As trilhas da Etapa 1 seguem com fixtures (plano §10).

| Piloto | Requisito | Usado em | Escolha |
| --- | --- | --- | --- |
| **BF-N0** | repo real, sem nenhum arquivo de IA (BF §4.1), com testes que rodam e saem com 0 | 1I, 2I, 3I | _a definir_ |
| **BF-N1** | repo real com AGENTS.md ou CLAUDE.md, **em outra linguagem** que o N0 | 2I, 3I | _a definir_ |
| **GF-G0** | diretório vazio numa **terceira** stack, com gerador oficial não interativo (GF §6.2) | 2I, 3I | _a definir_ |

**O que a escolha destrava:**

- 1G: o repo-fixture mínimo é feito na stack do N0.
- 2E: o catálogo de scaffolder da Etapa 2 cobre só a stack do G0.
- 2B: a matriz de detecção da Etapa 2 cobre as três stacks.

**Como registrar:** preencha a coluna "Escolha" com o caminho ou a URL e a stack. Depois confirme que o N0 roda os testes com exit 0 e anote aqui o comando e a data.

## Decisões da seção 1 do plano

As decisões assumidas (D1, D2/D14, D3/D24, D4, D6, D7, D8/D13, D15, D19, D29–D31, D35–D38) seguem **como proposta**, pendentes da revisão da pessoa. As que este repo já fixou como ADR são E0-a…E0-d ([0001](../../decisions/0001-cli-unico-harness.md) a [0004](../../decisions/0004-testes-pytest-so-em-dev.md)). Mudar uma das outras antes da Etapa 1 custa só editar a linha da tabela do plano. Depois dela, passa pelo procedimento de mudança de contrato.
