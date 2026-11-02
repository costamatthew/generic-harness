# Pilotos (D5, D21, D45): blocker da integração 1I

> Entrega 0.1 do [plano](../plano-de-construcao.md). A escolha é da pessoa (P10): o plano não escolhe repositório por ela.

**Status em 02/11/2026: ESCOLHIDOS.** O N0 já serviu à integração 1I (piloto `~/projets/midcortes-piloto-1`, ver [1I.md](../etapa-1/1I.md)). O N1 e o G0 entram na 2I.

| Piloto | Requisito | Usado em | Escolha |
| --- | --- | --- | --- |
| **BF-N0** | repo real, sem nenhum arquivo de IA (BF §4.1), com testes que rodam e saem com 0 | 1I, 2I, 3I | ~/projets/midcortes |
| **BF-N1** | repo real com AGENTS.md ou CLAUDE.md, **em outra linguagem** que o N0 | 2I, 3I | ~/profit/profit-app-flutter |
| **GF-G0** | diretório vazio numa **terceira** stack, com gerador oficial não interativo (GF §6.2) | 2I, 3I | JavaScript: Vite (template `vanilla`) + Vitest/jsdom. Ensaio em ~/projets/html-simples; a 2I parte de um diretório vazio novo (ver abaixo) |

**O que a escolha destrava:**

- 1G: o repo-fixture mínimo é feito na stack do N0.
- 2E: o catálogo de scaffolder da Etapa 2 cobre só a stack do G0.
- 2B: a matriz de detecção da Etapa 2 cobre as três stacks.

**Como registrar:** preencha a coluna "Escolha" com o caminho ou a URL e a stack. Depois confirme que o N0 roda os testes com exit 0 e anote aqui o comando e a data.

## Stack do G0 (D45), decidida em 02/11/2026

**Decisão: JavaScript, com `create-vite` (template `vanilla`, `--no-interactive`) como gerador e Vitest + jsdom como addons de teste.** Node 24, versões diretas exatas e `package-lock.json`.

- **Por quê.** "HTML puro" não tem test runner nem gerador, então não cumpre a DoD do esqueleto (GF §6.2: gerador oficial; R05: prova vermelho → verde). A pessoa já tinha escolhido Vite + Vitest ao preparar o `html-simples` (ADR-0001 daquele diretório, 31/10/2026). Esta seção só traz a decisão para o plano, sem escolher outra. A stack é diferente do N0 (Python) e do N1 (Dart/Flutter) (GF D45). O `npm create vite` está na tabela de geradores da GF §6.2.
- **Versão testada.** `create-vite@9.3.3`, `vite@8.3.5`, `vitest@5.0.5`, `jsdom@30.1.3`, Node 24.18.0 (`~/projets/html-simples/package.json`). A 2E usa esses valores como `testedVersion` da entrada do catálogo de scaffolder.
- **O `html-simples` não serve como G0.** Ele já foi gerado (classe G2, GF §3) e não tem git. Ele fica como **ensaio de referência**: mostra a saída esperada do gerador, a prova por mutação (`scripts/prove-sensor.mjs`) e o JUnit (`npm run test:ci`). A 2I cria um diretório vazio novo, `~/projets/html-simples-g0`, com `git init`, e percorre o GF-G0 inteiro (classificar → brief → ADRs → apply → `GEN-001`).
- **Lacuna declarada.** Ninguém validou a página num navegador real; os testes rodam no jsdom (`html-simples/docs/requisitos.md`). O critério da 2I não depende disso.

## Decisões da seção 1 do plano

As decisões assumidas (D1, D2/D14, D3/D24, D4, D6, D7, D8/D13, D15, D19, D29–D31, D35–D38) seguem **como proposta**, pendentes da revisão da pessoa. As que este repo já fixou como ADR são E0-a…E0-d ([0001](../../decisions/0001-cli-unico-harness.md) a [0004](../../decisions/0004-testes-pytest-so-em-dev.md)). Mudar uma das outras antes da Etapa 1 custa só editar a linha da tabela do plano. Depois dela, passa pelo procedimento de mudança de contrato.
