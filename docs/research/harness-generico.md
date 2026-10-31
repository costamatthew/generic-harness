# Harness genérico: pesquisa

> **Fase:** Research do RPI (cap. 9). Este arquivo é a saída da pesquisa e a entrada da fase de Plan, que deve começar numa janela nova.
> **Fonte da verdade:** o guia *IA First Dev: Agentes, Loops e Harness* (`ia-first-dev.pdf`, out/2026). As referências "cap. N" e "Ap. X" apontam para ele.
> **Complementos externos** aparecem marcados como **[Externo]**, separados do conteúdo do guia, como o próprio guia faz nos blocos *Complemento*. Eles foram consultados em 22/10/2026 e servem para confirmar se o desenho funciona nas ferramentas atuais. Quando contradizem o guia, a seção 13 registra a divergência.
> **Data:** pesquisa original em 22/10/2026; enriquecimento documental em 25/10/2026.
> **Avaliação complementar:** [O harness genérico e o guia correspondem a uma fábrica de agentes?](fabrica-de-agentes-avaliacao.md). As adições marcadas como **[Síntese da avaliação]** incorporam sua análise e propostas; não são requisitos atribuídos ao guia nem capacidades implementadas. A matriz de ferramentas e as fontes externas de 22/10 não foram revalidadas nesta revisão.

---

## 0. TL;DR

1. **Harness é tudo o que não é o modelo** (cap. 10 e 13). Ele tem três grupos: *guides* (feedforward), *sensors* (feedback) e *memória + bootstrap*. Um harness genérico **não é um agente novo**. É a camada "de usuário" que se acopla aos agentes que já existem (Claude Code, Cursor, Codex), alinhada com o "usuário antes de builder" do cap. 1.
2. **Nem tudo é portável.** Processos, formatos, papéis, gates e scripts são portáveis. Comandos, boundaries, convenções e arquitetura são fatos ou decisões de cada projeto, e o guia proíbe gerá-los automaticamente (cap. 4). Daí o desenho em três partes: **núcleo genérico + adaptadores por ferramenta + perfil do projeto**.
3. **O perfil do projeto (`.harness/profile.json`) é o contrato.** Ele tem slots que o projeto preenche: comandos reais, tipos de teste e isolamento, boundaries em três níveis, mapa de docs sob demanda, papéis e modelos, limites. Todo o núcleo lê esses slots e **nada fica hardcoded**, conforme o princípio 10 do cap. 12.
4. **Enforcement em vez de instrução** (cap. 12, princípio 3). Toda regra importante do harness tem um passo que bloqueia: um hook, um script ou um gate. O contrato proposto reserva a conclusão a `harness task done <ID>`, e só com o gate verde. **[Síntese da avaliação]** Impedir alterações por outros caminhos exige isolamento e testes de contorno; negar ferramentas de edição, sozinho, não demonstra essa garantia (seção 3.7).
5. **O código de saída decide** (caps. 9 e 12). O gate roda os comandos do perfil, devolve uma saída enxuta e guarda o log completo em disco. Um *test guard* genérico, que lê JUnit XML, ataca as quatro trapaças do iceberg: asserções enfraquecidas, testes apagados, skip e adiamento.
6. **Quem implementa não valida** (cap. 13). O verifier e o juiz rodam em sub-agents custom, com modelo pinado e contexto limpo, e precisam citar evidência `arquivo:linha` (cap. 15).
7. **O estado fica em disco**: `STATE.md` com handoff, status de tasks em JSON (cuja escrita deve ser reservada ao executor de confiança) e um bootstrap no início de cada sessão (caps. 9 e 13).
8. **Proporcionalidade vem embutida**: auto-sizing (cap. 9), árvore de decisão de sub-agents com ~3 workers por blocos de fases e nunca um por task (cap. 11), e um orçamento de contexto para o **próprio harness** (cap. 4 e 5).
9. **A portabilidade é viável em out/2026.** AGENTS.md e Agent Skills são padrões abertos lidos por Claude Code, Cursor e Codex. Hooks e sub-agents existem nas três ferramentas, mas com formatos diferentes, e são eles que exigem adaptadores **[Externo]**.
10. **Comece por um loop verificável**, não pela infraestrutura inteira (armadilha do cap. 17). O roadmap da seção 9 tem critérios de saída binários em cada fase.
11. **[Síntese da avaliação] O produto atual é um harness para desenvolvimento de software.** Ele pode sustentar uma fábrica de software operada por agentes, mas a pesquisa não comprova uma fábrica operacional. Criar e operar agentes como produtos exige uma decisão adicional de escopo e contratos próprios (seções 1.5 e 14).

---

## 1. O que o guia entende por harness, e o que isso implica para "genérico"

### 1.1 Agent = Model + Harness

- O modelo decide e o agente orquestra. O modelo é stateless e recebe a cada chamada o pacote inteiro: system prompt, AGENTS.md, conversa, arquivos e saídas (caps. 1 e 10).
- O harness tem três grupos (cap. 13, Fig. 13.1):
  - **Guides (feedforward):** AGENTS.md, spec e tasks, docs de arquitetura, convenções.
  - **Sensors (feedback):** linters, type checkers, testes e E2E, agente de review.
  - **Memória + bootstrap:** `init.sh`, `progress.md`/`STATE.md`, disciplina de git.
- Guides sem sensors produzem um agente bem orientado que nunca descobre se acertou. Sensors sem guides produzem um agente que erra do mesmo jeito sempre. Os dois só funcionam juntos, num loop, com a memória levando o resultado para a sessão seguinte (cap. 13).
- O fio da Parte IV é a pergunta **"quem fecha o loop?"**, e a resposta fica cada vez mais distante do modelo que fez o trabalho (cap. 10).

### 1.2 Que tipo de harness construir

O guia defende ser **usuário antes de builder** (cap. 1). Para esta pesquisa, isso significa não reescrever o loop agêntico, que Claude Code, Cursor e Codex já implementam, e sim construir a instrumentação em volta dele.

**[Externo]** Böckeler (martinfowler.com, 02/04/2026) usa a mesma distinção: existe o harness *embutido* do agente e o harness *externo* que o usuário monta em volta dele. Um harness genérico é um harness externo empacotado. Ela também propõe **harness templates**: "a bundle of guides and sensors that leash a coding agent to the structure, conventions and tech stack of a topology". É exatamente o que este projeto pretende ser, com o aviso dela de que templates assim herdam os problemas de versionamento e sincronia dos *service templates*.

### 1.3 O que é portável e o que não é

| Peça | Genérica? | Onde mora | Motivo no guia |
| --- | --- | --- | --- |
| Loop implementar → testar → corrigir | sim | skill + scripts | é processo, não fato do projeto (cap. 12) |
| Formato de spec, task e DoD; IDs; WHEN/THEN/SHALL | sim | templates | cap. 9, Ap. A |
| Papéis Planner / Generator / Evaluator; revisores especialistas; juiz | sim | definições de sub-agent | caps. 13, 14, 15 |
| Gate runner, soma de pesos, validações estruturais | sim | scripts determinísticos | "o que pode ser determinístico deve ser" (caps. 5 e 15) |
| Hooks de enforcement | a lógica sim; os matchers não | hooks + perfil | cap. 12, princípio 3 |
| STATE.md e handoff | o formato sim; o conteúdo não | template + `.harness/` | cap. 9 |
| Regras de proporcionalidade (auto-sizing, árvore de sub-agents) | sim | skills | caps. 9 e 11 |
| Comandos de build, lint, typecheck e testes | **não**: detectados e confirmados | perfil | cap. 4; cap. 12, princípio 10; cap. 17, passo 1 |
| Boundaries (sempre, pergunte, nunca) | **não**: decididos pelo time | perfil, renderizado no AGENTS.md | cap. 4 |
| Convenções, arquitetura, domínio | **não** | AGENTS.md + docs sob demanda | caps. 2 e 4: construídos a partir de erros reais, nunca gerados pelo `/init` |
| Isolamento de testes (o que pode rodar em paralelo) | **não**: mapeado | perfil | mapeamento do cap. 9; cap. 12, princípio 8 |
| Integrações (board, docs) | a conexão sim (MCP); o uso não | MCP + skill do projeto | cap. 6: "MCP é conexão, não instrução" |

A coluna "não" é o motivo de existir o perfil: **um harness genérico não pode trazer as respostas do projeto. Ele traz as perguntas certas e as gates que dependem das respostas.**

### 1.4 Consequência: três camadas

```
┌─────────────────────────── projeto hospedeiro ───────────────────────────┐
│ AGENTS.md (do time) ◄── blocos curtos renderizados pelo harness          │
│ .harness/profile.json ◄── o CONTRATO: comandos, testes, boundaries, docs │
│ .harness/STATE.md · specs/ · runs/ (estado e evidência)                  │
│                                                                          │
│ ┌──────────────── NÚCLEO GENÉRICO (independente de ferramenta) ───────┐  │
│ │ skills (Agent Skills) · papéis (sub-agents) · templates             │  │
│ │ scripts: gate · test-guard · task · state · doctor                  │  │
│ │ hooks com contrato neutro (stdin JSON → exit code + mensagem)       │  │
│ └───────┬──────────────────────┬─────────────────────┬────────────────┘  │
│   adaptador Claude Code   adaptador Cursor     adaptador Codex           │
│   (.claude/…, plugin)     (.cursor/…)          (.agents/…)               │
└──────────────────────────────────────────────────────────────────────────┘
```

O núcleo **define portas** (o que precisa saber do projeto) e o perfil **preenche** essas portas. Os adaptadores traduzem o núcleo para o formato de cada ferramenta. É *ports & adapters* aplicado ao harness.

### 1.5 Unidade de entrega e maturidade **[Síntese da avaliação]**

A [avaliação complementar, seções 1–3](fabrica-de-agentes-avaliacao.md), distingue três objetivos. “Fábrica” é usado em sentidos diferentes; esta classificação é uma síntese analítica, não uma norma de certificação.

| Objetivo | Entrada → saída principal | Cobertura desta pesquisa |
| --- | --- | --- |
| Harness de desenvolvimento | Projeto, regras e tarefa → ambiente e loop verificável | Escopo direto: núcleo, adaptadores e perfil |
| Fábrica de software com agentes | Demanda de software → código, testes, evidências e PR | Base conceitual forte; operação repetível ainda precisa ser demonstrada |
| Fábrica de agentes como produtos | Necessidade de um agente → agente versionado, avaliado, publicado e acompanhado | Ampliação de escopo; faltam contratos de produto e ciclo de vida |

O catálogo de skills e papéis da seção 3.2 organiza componentes do harness; não é um inventário de agentes entregues a consumidores. Da mesma forma, instalar o harness num repositório não equivale a publicar um agente em produção. O princípio P1 continua orientando o escopo atual.

Neste documento, **previsto** significa descrito, **parcial** significa que existem mecanismos relacionados sem contrato completo, e **não especificado** indica ausência de definição suficiente. Nenhum desses termos comprova implementação:

- **Previstos para software:** specs e aceite, reuso, papéis, delegação, memória em arquivos, gates, avaliação do harness e distribuição versionada.
- **Parciais:** proteção efetiva de permissões e estado, recuperação após falhas, execução automática, observabilidade e controle operacional de custos.
- **Não especificados como produto:** definição e inventário de agentes entregues, avaliação por domínio, releases, implantação, reversão e desativação.
- **Sem resultados apresentados:** piloto, benchmark e demonstração de repetibilidade. Arquitetura e roadmap são propostas para validação.

---

## 2. Princípios de design derivados do guia

Cada princípio vira um critério de revisão do próprio harness.

| # | Princípio | De onde vem |
| --- | --- | --- |
| P1 | **Construa o harness externo, não um agente.** Use o loop da ferramenta e instrumente em volta. | cap. 1 (usuário antes de builder); cap. 10 |
| P2 | **Contexto é orçamento.** Tudo o que o harness põe no contexto fixo é pago em toda requisição. O que é fixo fica mínimo; o resto, sob demanda. | caps. 1, 3, 4, 5 |
| P3 | **Lógica genérica, dados do projeto.** O núcleo descobre a infraestrutura real (frameworks, tipos de teste, isolamento) e nunca supõe. | cap. 12, princípio 10 |
| P4 | **Enforcement em vez de instrução.** Cada regra importante tem um passo que bloqueia até a conformidade ser provada. | cap. 12, princípio 3 |
| P5 | **Verificação externa e binária.** Exit code 0/≠0, nunca a opinião do agente. | caps. 2, 9, 12 |
| P6 | **Quem faz não julga.** Contexto limpo, papel único, modelo pinado para o juiz. | caps. 13, 15 |
| P7 | **Estado em disco, não na conversa.** | caps. 9, 10, 13 |
| P8 | **Determinístico onde der.** Scripts para o que é repetitivo, estrutural ou aritmético. | caps. 5, 15 (item 8) |
| P9 | **Proporcionalidade.** Auto-sizing, um agente por padrão, ~3 sub-agents por blocos, nunca um por task. | caps. 9, 11 |
| P10 | **O humano em pontos combinados**: Discovery, revisão da spec, revisão do plano, decisão sobre achados de review. Quem comita é o workflow ou o humano. | caps. 7, 8, 9, 14 |
| P11 | **Itere a partir de erros reais e pode.** Todo componente embute uma suposição sobre o que o modelo não faz sozinho, e ela envelhece. | caps. 2, 4, 13; **[Externo]** Rajasekaran |
| P12 | **Verificação visível.** Tabela de validação e evidência junto com a entrega. | cap. 12, princípio 4; cap. 15 |
| P13 | **Rastreabilidade.** IDs atravessam problema → spec → task → commit → evidência. | caps. 9, 16 |
| P14 | **Um percurso verificável antes da infraestrutura.** | cap. 17 (armadilha) |
| P15 | **Mensagens de sensor escritas para o agente.** Cada bloqueio diz o que falhou, por quê e o que fazer no lugar, pareando cada proibição com a alternativa. | cap. 4; **[Externo]** Böckeler: "a positive kind of prompt injection" |

---

## 3. Arquitetura proposta

### 3.1 O contrato: `.harness/profile.json`

**Por que JSON:** scripts em qualquer linguagem leem JSON sem dependências, e o modelo altera ou sobrescreve JSON indevidamente com menos frequência do que Markdown (Complemento de Young no cap. 15).

Exemplo ilustrativo de um projeto Node/TS. Os valores são do projeto, não do harness:

```json
{
  "schema": 1,
  "project": { "name": "fakeflix", "kind": "brownfield" },
  "commands": {
    "install":   { "run": "pnpm install" },
    "build":     { "run": "pnpm build" },
    "lint":      { "run": "pnpm lint", "fix": "pnpm lint --fix" },
    "typecheck": { "run": "pnpm tsc --noEmit" },
    "dev":       { "run": "pnpm dev", "ready": "http://localhost:3000/health" },
    "test": {
      "unit":        { "run": "pnpm vitest run --reporter=junit --outputFile=.harness/runs/unit.xml",
                       "report": ".harness/runs/unit.xml", "parallelSafe": true },
      "integration": { "run": "pnpm test:int", "report": ".harness/runs/int.xml",
                       "parallelSafe": false, "why": "banco compartilhado, sem testcontainers" },
      "e2e":         { "run": "pnpm playwright test", "requires": ["dev"] }
    }
  },
  "tests": {
    "globs": ["src/**/*.spec.ts", "e2e/**/*.spec.ts"],
    "skipMarkers": [".skip(", "xit(", "it.todo(", ".only("]
  },
  "boundaries": {
    "always": ["rodar os testes antes do PR", "dar stage só no que foi pedido"],
    "ask":    [{ "rule": "adicionar dependências", "match": ["shell:pnpm add *"] }],
    "never":  [
      { "rule": "push direto na main", "match": ["shell:git push * main*"], "instead": "abra um PR" },
      { "rule": "criar migrations à mão", "match": ["write:**/migrations/**"],
        "instead": "gere com pnpm migration:generate" }
    ]
  },
  "docs": [
    { "when": "criando controllers ou services", "read": "docs/code-patterns.md" },
    { "when": "integrando com APIs externas",     "read": "docs/integration-patterns.md" }
  ],
  "roles": {
    "planner":     { "model": "strong" },
    "implementer": { "model": "cheap" },
    "verifier":    { "model": "strong", "pinned": true }
  },
  "limits": { "maxFixIterations": 3, "maxWorkers": 3, "contextTarget": 0.40 },
  "components": { "stopGate": true, "testGuard": true, "boundaryGuard": true, "reviewLoop": false }
}
```

Regras do contrato:

- **Comandos são verificados na instalação.** O `init` roda cada comando e registra o exit code. Um comando inventado transforma a primeira execução numa investigação do ambiente (cap. 17, passo 1).
- **Detectar não é decidir.** Fatos, como os scripts do `package.json`, o framework de teste e o diretório de testes, podem ser **detectados** por script. Julgamentos, como boundaries, convenções e se um teste pode rodar em paralelo, **precisam ser confirmados por uma pessoa**. O perfil marca a origem de cada valor (`detected` ou `confirmed`).
- **Cada "never" tem um "instead"** (cap. 4), e cada "never" e "ask" tem um `match` neutro que os adaptadores compilam para a deny-list ou o hook de cada ferramenta. É *boundaries-as-code*: a regra escrita e a regra aplicada têm a mesma origem.
- **Modelos são abstratos** (`strong` ou `cheap`) e o adaptador os mapeia: Opus/Sonnet no Claude Code, Composer no Cursor e assim por diante. Isso segue o "modelo forte para planejar, barato para implementar" do cap. 8.
- **Componentes são desligáveis** (`components`). Assim dá para medir o impacto de cada um e remover o que um modelo melhor tornou desnecessário (P11).
- **Presets por topologia (futuro).** `node-ts-vitest`, `python-pytest`, `go-test` e outros seriam os *harness templates* de Böckeler: reduzem variedade e servem de ponto de partida para o `init`.

### 3.2 Catálogo de componentes

**Guides (feedforward)**

| ID | Componente | O que faz | Guia | Fase |
| --- | --- | --- | --- | --- |
| G1 | Blocos do harness no AGENTS.md | Dois blocos curtos entre marcadores: **BOUNDARIES** no topo, em caixa alta, renderizado do perfil, e **Workflow do harness** com no máximo ~10 linhas. Fora deles, o arquivo é do time. | cap. 4 | 0 |
| G2 | Checklist e esqueleto de AGENTS.md | Para projetos sem AGENTS.md: um esqueleto **com TODOs**, não com conteúdo gerado, mais o checklist do Ap. A | cap. 4, Ap. A | 0 |
| G3 | Árvore de docs sob demanda | Renderiza `profile.docs` como "Fazendo X → leia Y". O `doctor` falha se Y não existir | caps. 2, 4; Ap. A ("referências não devem apontar para arquivos inexistentes") | 1 |
| G4 | Skill `harness-execute` | Loop do sub-agent (cap. 12) e orquestração por fases (cap. 11) | caps. 11, 12 | 0 |
| G5 | Skill `harness-spec` | Specify / Design / Tasks com auto-sizing; WHEN/THEN/SHALL; IDs; task com o quê, onde e DoD | cap. 9; Ap. A | 2 |
| G6 | Skill `harness-onboard` | Mapeamento do codebase com sub-agents: dependências, arquitetura, **padrões de teste e isolamento**, `concerns.md`. Propõe valores para o perfil, marcando incertezas | cap. 9 (mapeamento); cap. 2 (legado: mapear o real antes de mudar) | 1 |
| G7 | Skill `harness-review` | 6 especialistas mais 1 consolidador, cada um em `references/<especialista>.md` com checklist | cap. 14 | 2 |
| G8 | Skill `harness-retro` | Transforma cada erro recorrente numa regra, num exemplo, num teste ou num **sensor**, e poda o que não paga mais o custo | caps. 2, 4, 13 | 1 |
| G9 | Templates | `spec.md`, `design.md`, `tasks.md`, task com DoD (Ap. A), `STATE.md`, `validation.md` | Ap. A | 0 |

O catálogo tem no máximo **6 skills do harness**. O projeto ainda vai ter as dele, e o guia recomenda **≤ 20 no total** (cap. 5).

**Sensors (feedback)**

| ID | Componente | O que faz | Tipo | Guia | Fase |
| --- | --- | --- | --- | --- | --- |
| S1 | `harness gate <ID>` | Roda os comandos da DoD a partir do perfil. Devolve um **resumo enxuto** (status, contagens, primeiras falhas com `arquivo:linha`) e grava o log completo em `.harness/runs/`. Associa o resultado ao *hash da árvore* de trabalho, para que um verde antigo não valha | computational | caps. 9, 10 ("resultado das tools enxuto"), 12 | 0 |
| S2 | `harness task done <ID>` | **Caminho autorizado para concluir uma task** (proteção a demonstrar na seção 3.7). Roda S1 e, a partir da fase 1, S3; registra as verificações executadas e bloqueia se uma verificação exigida estiver indisponível. Só com tudo verde atualiza `tasks.json`, anexa evidência em `validation.md` e sugere o commit atômico | computational | caps. 9, 12 | 0 |
| S3 | Test guard | Detecta o iceberg (seção 3.5): contagem de testes contra o baseline, skips, testes congelados alterados, task sem teste | computational | cap. 12, princípios 6 e 7 | 1 |
| S4 | Stop gate (hook) | Impede o agente de encerrar com uma task em andamento e gate vermelho. Permite encerrar se houver blocker registrado. Tem um limite de reentradas | computational | caps. 10, 12, 17 | 0 |
| S5 | Boundary guard (hook + deny-list) | Compila `never` e `ask` do perfil em deny e ask da ferramenta. Bloqueia `git commit` e `git push` no modo review/fix | computational | caps. 4, 14 | 1 |
| S6 | Sensores pós-edição (hook) | Formata e linta o arquivo editado, com mensagem escrita para o agente | computational | cap. 13; **[Externo]** Böckeler | 1 |
| S7 | Verifier | Sub-agent custom, com **modelo pinado** e contexto limpo. Responde checks binários com evidência `arquivo:linha` ou resultado de execução. Check sem evidência conta como não atendido | inferential | caps. 13, 15, 16 | 0 |
| S8 | Review loop | Local (skill) e CI (GitHub Actions com `/review`, decisão humana, `/fix`, commit pelo workflow). Precision > recall (limiar de 80%), second pass, gap detection | inferential | cap. 14 | 2–3 |
| S9 | `harness doctor` | Sensor **do próprio harness**: linhas do AGENTS.md (alvo < 100, teto 150), número de skills ativas, tamanho das descriptions, referências quebradas, comandos do perfil que não rodam, blocos dessincronizados | computational | caps. 4, 5; Ap. A | 1 |
| S10 | Sensores contínuos | Drift de arquitetura, código morto, ciclos de dependência e um *discrimination sensor* (injeta falhas numa cópia e confere se os testes pegam) | computational | cap. 13 (AI Slop); **[Externo]** Böckeler, TLC atual | 3 |

**Memória + bootstrap**

| ID | Componente | O que faz | Guia | Fase |
| --- | --- | --- | --- | --- |
| M1 | `.harness/STATE.md` | Decisões (AD-NNN), blockers, aprendizados, ideias para depois, pendentes e **handoff**. Vale além de uma feature | caps. 9, 13 | 0 |
| M2 | `tasks.json` por feature | Status das tasks. **Escrita reservada ao executor de confiança.** Negar Write/Edit é uma camada; shell, scripts e configuração também precisam de proteção (seção 3.7) | **[Externo]** Young (feature list em JSON; o agente só muda o status) | 0 |
| M3 | Bootstrap de sessão (hook SessionStart) | Injeta **no máximo ~20 linhas**: task atual, último gate, blockers, próximo passo, e pede para ler o STATE.md | cap. 13; **[Externo]** rotina de início de Young: pwd → git log + progresso → feature list → init.sh → teste básico | 1 |
| M4 | `init.sh` / `harness up` | Sobe o ambiente a partir de `profile.commands.dev` e espera o `ready` | cap. 13 | 1 |
| M5 | PreCompact / fim de sessão | Força a atualização do handoff antes de compactar ou sair | caps. 3, 10 (compaction) | 1 |
| M6 | Disciplina de git | Uma task, um commit atômico; Conventional Commits; worktrees para paralelismo | cap. 9; **[Externo]** Osmani | 1–3 |
| M7 | Ciclo de vida das specs | Comitar com a implementação, usar no review do PR e retirar da área ativa (`harness spec archive`), preservando referências e evidências conforme 8.2 | cap. 9 | 2 |

### 3.3 Os loops que o harness monta, e quem fecha cada um

| Nível | Loop | Quem fecha | Componentes | Fase |
| --- | --- | --- | --- | --- |
| L0 | contexto → modelo → tool → resultado | a ferramenta (não é nosso) | — | — |
| L1 | implementar → testar → corrigir (dentro do worker) | **exit code** via S1 e S2, com S4 impedindo a saída | G4, S1–S4 | 0 |
| L2 | orquestrador → workers por blocos de fases | o orquestrador, fase a fase, pelo mapa de execução | G4, G5 | 2 |
| L3 | Planner → Generator → Evaluator → Fix | o Evaluator, em processo separado; fix loop até `maxFixIterations` e depois escala para o humano | S7 | 2 |
| L4 | `/review` → humano decide → `/fix` → commit pelo workflow | **o humano**; a IA nunca aprova, rejeita ou comita | G7, S5, S8 | 2–3 |
| L5 | harness de avaliação (benchmark do próprio harness) | checks binários somados por script, em vários runs | seção 7 | 3 |
| L6 | Loop Engineering: um sistema dispara, verifica, registra e decide o próximo passo | condição verificável por máquina + orçamento + escalonamento | **[Externo]** Osmani, Lulla et al. | 3 |

### 3.4 Os seis problemas do cap. 13 mapeados para mecanismos

| Problema (cap. 13) | Mecanismo no harness | Por que segura |
| --- | --- | --- |
| 1. One-Shot Hero | tasks atômicas (G5), uma por vez no worker (G4), validador de granularidade das tasks | o trabalho chega ao agente já fatiado |
| 2. Vitória Prematura | `tasks.json` com status que só S2 muda; Stop gate (S4) | "pronto" deixa de ser uma frase e passa a ser um exit code |
| 3. Amnésia entre Sessões | STATE.md + handoff (M1), SessionStart (M3), git log | a sessão nova começa do estado conhecido |
| 4. Teste Fake | test guard (S3); E2E pelo navegador (Playwright MCP) para requisitos de interface; discrimination sensor (S10) | o sinal de "testado" passa a corresponder a teste real |
| 5. Tudo no Mesmo Processo | verifier e revisores em sub-agents de contexto limpo, com modelo pinado (S7, S8) | quem julga nunca viu o código ser escrito |
| 6. AI Slop Acumulado | revisores de Architecture e Regression & Hallucination (S8); sensores contínuos (S10); retro (G8) | algo compara o código de hoje com as regras sempre, não só por sessão |

### 3.5 O iceberg dos testes, com detecção genérica

**Ideia central: JUnit XML como língua franca.** Vitest, Jest, pytest, Go (via `gotestsum`), JUnit e outros produzem relatórios JUnit. O perfil diz onde fica o relatório (`report`), e o guard lê **contagens, falhas e skips** sem conhecer o framework (P3).

| Trapaça (cap. 12) | Detecção genérica | Resposta |
| --- | --- | --- |
| Asserções enfraquecidas | Na fase red, `harness task freeze <ID>` grava hashes dos arquivos de teste da task. Depois disso, qualquer diff nesses arquivos reprova o gate. Na fase 3, o discrimination sensor injeta falhas e confere se os testes as pegam | "testes escritos na fase red ficam congelados; para mudar, pare e peça ao humano" (princípio 6) |
| Testes deletados | `tests` do JUnit menor que o baseline congelado | "se a contagem diminuiu, investigue antes de seguir" (princípio 7) |
| Skip / pending | `skipped` do JUnit maior que o baseline, ou `skipMarkers` no diff | reprova com uma mensagem que diz o que fazer |
| Adiamento ("os testes vêm na próxima task") | o validador de tasks exige *Testes* e *Gate* em toda task; S2 reprova uma task que não toque nenhum arquivo de teste, a menos que a task traga `noTests: <justificativa>` aprovada | "dependência de compilação não justifica adiar; a fronteira da task está errada" (princípio 9) |

**Limite da evidência [Síntese da avaliação].** Contagem estável não detecta a troca de um teste por outro, e congelar arquivos não comprova que as asserções iniciais representam o requisito. O guard detecta sinais estruturais; a cobertura semântica depende de rastreabilidade à spec, revisão e injeção de falhas. Relatório ausente, antigo ou sem vínculo com a tentativa atual não pode produzir aprovação (seção 3.7).

**Válvula de escape:** alguns casos são legítimos, como a refatoração aprovada de um teste. Eles passam pelo nível **ask**: a pessoa aprova, a aprovação vai para o STATE.md e o baseline é recongelado. Sem essa válvula, o guard vira atrito e acaba desligado.

Exemplo de saída enxuta do gate, que é o que entra no contexto (cap. 10):

```
GATE T5 unit  FAIL exit=1  12.4s  tree=3f9c1e2
tests 41 (baseline 43, -2)  failed 1  skipped 0
  src/billing/payment.service.spec.ts:57  [PAG-03] recusado mantém carrinho
log: .harness/runs/T5-unit.log
→ A contagem caiu 2 desde o congelamento. Restaure os testes ou peça aprovação humana (nível ask).
```

### 3.6 Proporcionalidade embutida (números do guia)

| Regra | Valor | Guia |
| --- | --- | --- |
| AGENTS.md | alvo < 100 linhas; teto 150; seção com mais de ~20 linhas vira skill | cap. 4 |
| Skills ativas | ≤ ~20 no total; desativar as que não estão em uso | cap. 5 |
| Corpo do SKILL.md | < ~500 linhas; o resto vai para `references/` com ponteiro condicional | cap. 5 |
| Description da skill | o quê + quando + sinônimos; todo o "quando usar" fica nela | cap. 5 |
| Janela durante a implementação | < 40% (Smart Zone); 40–60% é atenção; > 60% é Dumb Zone | cap. 3 |
| Quick Mode | ≤ 3 arquivos, sem decisão de design | cap. 9 |
| Escopo médio | < 10 tasks: spec breve, design inline, tasks implícitas | cap. 9 |
| Plan Mode | bom para 1 a 3 tasks; agrupar em planos de ≤ 10 arquivos | cap. 8 |
| Sub-agents | 1 agente por padrão; ~3 workers por blocos de fases é o sweet spot; **nunca** um por task | cap. 11 |
| Review | limiar de confiança de 80%; second pass obrigatório | cap. 14 |
| Fix loop | um limite duro existe; o número não está no guia. Sugestão: 3 voltas e depois escalar (é o que o TLC atual usa **[Externo]**) | cap. 10 |

A skill `harness-execute` aplica a árvore de decisão do cap. 11 / Ap. A antes de delegar:

1. Cabe numa janela com folga para uma correção? Então um agente só.
2. Não cabe? Existe fronteira de acoplamento?
   - Não: reduzir o escopo.
   - Sim, com blocos dependentes: workers em sequência.
   - Sim, com blocos independentes **e** testes `parallelSafe`: workers em paralelo.

### 3.7 Fronteira de confiança e procedência da evidência **[Síntese da avaliação]**

A [avaliação, seção 4](fabrica-de-agentes-avaliacao.md), identifica garantias que o desenho precisa demonstrar. São riscos inferidos da proposta, não vulnerabilidades observadas numa implementação.

**Separação de permissões.** O agente pode editar os arquivos da tarefa, mas o estado de aceite deve ser produzido por um executor de confiança. O Plan precisa definir como proteger `tasks.json`, scripts de gate, perfil aprovado, baselines, configuração de permissões e evidências. A proteção deve abranger shell e outros caminhos de escrita disponíveis, além de Write/Edit. Matchers `shell:<glob>` ajudam a aplicar regras, mas não provam cobertura de comandos equivalentes. Cada adaptador deve declarar os caminhos cobertos e os limites; uma proteção indisponível não deve ser apresentada como garantia ativa.

**Contrato mínimo de evidência por tentativa.** O gate deve registrar:

- IDs de run, tentativa, task e requisitos verificados;
- revisão e hash dos arquivos de entrada, incluindo mudanças ainda não comitadas, com regra explícita para excluir artefatos gerados pelo próprio gate;
- versões ou hashes do harness, adaptador, perfil aprovado, testes e baselines;
- comandos efetivamente executados, identificação do ambiente, início, término e códigos de saída;
- verificações executadas ou indisponíveis e localização e hashes dos relatórios e logs.

O resultado só é aceito se corresponder à tentativa e às entradas atuais. Alterações relevantes invalidam o verde anterior; relatório ausente, reutilizado ou adulterado deve bloquear o aceite. Hashes ajudam a detectar mudanças, mas não substituem a proteção do executor e do registro que os contém.

**Estado e retomada.** `STATE.md` é o handoff legível; o estado estruturado de execução deve ser a referência para transições. O Plan deve definir gravação atômica, controle de concorrência e reconciliação após interrupção. Uma falha entre executar o gate e persistir a conclusão não pode gerar uma task concluída sem prova nem duas conclusões conflitantes. Se a prova não puder ser validada na retomada, o gate precisa ser executado novamente.

### 3.8 Contrato operacional do runner L6 **[Síntese da avaliação]**

Agenda, eventos, execução headless, worktrees e orçamento já estão previstos em L6 e na fase 3. Para transformá-los em operação verificável, o Plan deve especificar os comportamentos abaixo, proporcionalmente ao piloto:

| Situação | Comportamento a especificar e validar |
| --- | --- |
| Entrada e fila | Registrar demanda, revisão alvo, critérios de aceite e responsável pelo escalonamento; tornar a ordem de execução explícita |
| Evento duplicado | Identificar a demanda e a tentativa; não duplicar entrega ou efeitos externos ao repetir o mesmo evento |
| Reinício ou queda de worker | Retomar de checkpoint validado; reconciliar trabalho em andamento e evidências antes de continuar |
| Concorrência | Isolar worktrees e recursos compartilhados; definir propriedade da task e tratamento de conflitos |
| Timeout, orçamento ou excesso de tentativas | Interromper o trabalho, preservar evidências e escalar com motivo; nunca converter esgotamento em sucesso |
| Cancelamento | Encerrar workers e processos associados, registrar resultado e liberar recursos com segurança |
| Falha de ferramenta ou dependência | Definir falhas recuperáveis, limite e intervalo de novas tentativas; encaminhar as demais ao responsável |
| Observabilidade | Relacionar logs, duração, custo e resultado ao run e à entrega; definir alertas e metas de serviço quando a operação exigir |

O vocabulário de estados deve distinguir pelo menos espera, execução, bloqueio, falha, cancelamento e conclusão aceita. A aprovação humana pode continuar fazendo parte do processo; autonomia total não é pré-requisito para uma fábrica de software de escopo delimitado.

---

## 4. Portabilidade entre agentes (estado em out/2026) **[Externo]**

### 4.1 Matriz de capacidades

| Capacidade | Claude Code | Cursor | Codex |
| --- | --- | --- | --- |
| Instruções | `CLAUDE.md`. Lê `AGENTS.md` **nativamente** quando não há CLAUDE.md (v2.1.277+). Se houver, `@AGENTS.md` importa o arquivo | `AGENTS.md` + `.cursor/rules/` | `AGENTS.md` |
| Instruções por diretório | CLAUDE.md aninhado (sob demanda); `.claude/rules/` com `paths:` | AGENTS.md aninhado (vale o mais próximo) | AGENTS.md aninhado |
| Skills | `.claude/skills/<nome>/SKILL.md`; aninhadas; de plugin. Sem confirmação de que lê `.agents/skills` | `.cursor/skills/` (2.4+); `.agents/skills/` aparece num relato de fórum | `.agents/skills` do cwd até a raiz do repo; `~/.agents/skills`; segue symlinks |
| Sub-agents custom | `.claude/agents/*.md`: `model` (pin), `tools`, `disallowedTools`, `maxTurns`, `skills`, `isolation: worktree`, `hooks` | `.cursor/agents/` (2.4+), com modelo próprio | há documentação de *Subagents* (detalhes não verificados) |
| Hooks | `settings.json` ou `hooks/hooks.json` de plugin: `PreToolUse`, `PostToolUse`, `Stop`/`SubagentStop` (exit 2 bloqueia e continua), `SessionStart`, `PreCompact` e outros | `.cursor/hooks.json`: `preToolUse`, `beforeShellExecution`, `afterFileEdit`, `stop` com `followup_message` e `loop_limit` (padrão 5), `sessionStart`, `preCompact`. **Carrega hooks do Claude Code** (third-party hooks); exit 2 é compatível; `CLAUDE_PROJECT_DIR` é um alias | hooks existem (beta, segundo fontes de terceiros; não verificado) |
| Deny-list | `permissions.deny` / `ask` no `settings.json` | `.cursor/cli.json` (há um bug relatado: o "always allow" grava no arquivo global) | política de aprovação e sandbox no `config.toml` |
| Empacotamento | plugin (`.claude-plugin/plugin.json` + `skills/`, `agents/`, `hooks/`, `bin/`) e marketplace | plugins (`/add-plugin`) | marketplace de plugins |

O que isso significa para o desenho:

- **AGENTS.md pode ser a fonte única de instruções.** No Claude Code, basta não ter CLAUDE.md, ou ter um CLAUDE.md com `@AGENTS.md` mais o que for específico dele.
- **Skills seguem o padrão aberto puro.** O `name` tem até 64 caracteres, só minúsculas, dígitos e hífen, e precisa ser igual ao nome do diretório. A `description` tem até 1024 caracteres. O corpo fica abaixo de ~5000 tokens, com referências a um nível de profundidade, e `skills-ref validate` confere o formato. Os campos extras do Claude Code (`disable-model-invocation`, `context: fork`, `model`, `hooks`, `paths`) **não são portáveis**: empacotar para claude.ai falha com campos fora da spec. Quem injeta esses campos é o adaptador.
- **O ponto fraco é o hook.** Os eventos são parecidos, mas nomes, entrada e saída mudam. Por isso os hooks do núcleo seguem um **contrato neutro** (entrada JSON normalizada, exit code e mensagem), e cada adaptador traduz. Como o Cursor carrega hooks do Claude Code, o adaptador do Claude Code cobre parte do Cursor. Falta testar quais eventos ele mapeia (a página "Third Party Hooks" não foi lida).

### 4.2 Estratégia de adaptadores

```
core/skills/harness-execute/SKILL.md   (spec aberta pura)
        │  harness install --tools claude,cursor,codex
        ├─► .agents/skills/harness-execute/      (Codex, Cursor)
        ├─► .claude/skills/harness-execute/      (Claude Code: cópia + campos extras)
        ├─► .claude/agents/harness-verifier.md   (model: pinado, tools: só leitura)
        ├─► .claude/settings.json                (hooks + permissions.deny do perfil)
        ├─► .cursor/hooks.json + .cursor/cli.json
        └─► AGENTS.md                            (blocos entre marcadores, idempotente)
```

- **Copiar em vez de symlink, por padrão.** O instalador da TLC recomenda cópia, e symlinks se comportam diferente entre ferramentas e Windows. O instalador grava um `harness.lock` com versão e hash de cada arquivo instalado, e o `update` faz merge de 3 vias: avisa quando um arquivo do harness foi editado localmente.
- **Blocos gerenciados no AGENTS.md** (`<!-- harness:boundaries -->` e `<!-- harness:workflow -->`) são reescritos por `harness render`. Fora deles, o harness não mexe em nada. O `doctor` acusa um bloco editado à mão.

### 4.3 Distribuição: vendorizar ou plugin?

| | Vendorizar no repo (recomendado) | Plugin por usuário |
| --- | --- | --- |
| Funciona em CI, cloud agents e para o time inteiro | sim, porque está no repo | só para quem instalou |
| Versionado e revisado com o código | sim: "trate o harness como código" (cap. 10); "skills versionadas no repositório como fonte de verdade" (cap. 14) | não |
| Atualização | `harness update` com lockfile | automática pelo marketplace |
| Portável entre ferramentas | sim | um plugin por ferramenta |

**Recomendação:** vendorizar o núcleo e o perfil no repositório, e oferecer o plugin do Claude Code como conveniência para uso pessoal e fora de repositórios. Uma restrição **[Externo]**: sub-agents de plugin ignoram `hooks`, `mcpServers` e `permissionMode`. No plugin, os hooks precisam ir em `hooks/hooks.json`.

### 4.4 Orçamento de contexto do próprio harness

O harness precisa **declarar e medir** quanto custa em toda requisição (P2):

- Blocos do AGENTS.md: ≤ ~10 linhas de workflow + os boundaries que o time definiu.
- ≤ 6 skills. Cada description é paga em toda requisição, por toda skill instalada (cap. 5).
- SessionStart: ≤ ~20 linhas.
- Saída de gate e de hooks: resumos curtos, com o log completo em disco.
- `harness doctor` imprime uma estimativa do contexto fixo e falha acima do limite configurado.

---

## 5. Como o harness se acopla a um projeto

O protocolo de instalação aplica o playbook do cap. 17 ao próprio harness:

1. **`harness init`** (determinístico):
   - Detecta a stack: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Makefile`, frameworks e relatórios de teste.
   - Gera um rascunho de `profile.json` com `origin: detected`.
   - **Roda cada comando** e registra o exit code.
   - Instala os adaptadores escolhidos e escreve o `harness.lock`.
2. **Revisão humana do perfil**, que é a "Discovery" do harness. É aqui que a pessoa:
   - confirma os comandos;
   - escreve os **boundaries** com o par "instead";
   - marca o que é `parallelSafe`;
   - aponta os docs sob demanda.

   O guia é claro: regras descrevem o projeto **real**, não um ideal (cap. 2).
3. **`harness-onboard`**, numa janela nova e com sub-agents (cap. 9, mapeamento):
   - Produz `docs/agents/testing.md` (tipos de teste, como rodam, o que paraleliza), `concerns.md` e um resumo de arquitetura em alto nível, sem listar paths (cap. 4).
   - Segue a cadeia de conhecimento: codebase → docs → Context7 → web → marcar como incerto. Nunca inventa (cap. 9).
4. **Primeiro loop com uma mudança pequena** (cap. 17). Esse é o **teste de aceitação do acoplamento**. Ele passa quando:
   - o gate rodou;
   - a evidência ficou registrada;
   - o STATE.md foi atualizado;
   - uma tentativa de encerrar com gate vermelho foi bloqueada.
5. **Retro (`harness-retro`)**. Cada erro observado vira uma regra, um exemplo, um teste ou um sensor. Toda revisão pergunta quais linhas ainda pagam o custo de ir em toda requisição (cap. 4, armadilha "o arquivo que só cresce").

**Brownfield ou greenfield.** **[Externo]** Böckeler chama de *harnessability* o quanto um codebase permite ser instrumentado: tipos fortes, fronteiras claras de módulo, frameworks opinativos. No legado, "the harness is most needed where it is hardest to build". O guia diz o mesmo pelo outro lado: o código precisa permitir o harness. Um type checker só verifica o que tem tipo, e um linter só cobra a convenção que existe (cap. 13). Em brownfield, as fases 0 e 1 vêm antes de qualquer review sofisticado.

**Monorepo.** Pode haver um perfil por pacote (`packages/x/.harness/profile.json`) e AGENTS.md aninhado. O AGENTS.md mais próximo vale (padrão agents.md), e o Codex varre `.agents/skills` do cwd até a raiz. O custo é a manutenção de cada arquivo a mais (cap. 4).

---

## 6. Uma feature com o harness, de ponta a ponta

É o cap. 16 com as peças do harness:

1. **A sessão abre.** O SessionStart injeta o handoff: task atual, último gate, blockers e próximo passo.
2. **"Vou trabalhar na CAM-42."** A task chega pelo MCP do board (cap. 8). A skill `harness-spec` faz o auto-sizing:
   - pequeno: Quick Mode;
   - médio: spec breve;
   - grande: spec, design e tasks com mapa de execução.

   → **Ponto humano:** revisar a spec. "É o ponto do fluxo em que meia hora de leitura economiza mais" (cap. 9).
3. **Janela nova, modelo barato** (RPI). A `harness-execute` lê o `tasks.md`, aplica a árvore de decisão e delega blocos de fases. Cada worker:
   - `harness task freeze T5` (congela os testes escritos na fase red);
   - implementa;
   - roda `harness gate T5`;
   - corrige;
   - roda `harness task done T5`.
4. **O agente tenta encerrar com vermelho.** O Stop gate bloqueia com a mensagem "rode `harness task done T5` ou registre o blocker". Um blocker registrado é um resultado legítimo, não uma conclusão fictícia (cap. 17).
5. **O verifier** (contexto limpo, modelo pinado) responde aos checks binários derivados dos IDs da spec, com `arquivo:linha` → `validation.md`. Os reprovados voltam como tasks de correção, no máximo `maxFixIterations` vezes, e depois escalam para o humano.
6. **Review local** (`harness-review`): os especialistas rodam em paralelo (leitura com baixo acoplamento, cap. 11) e o consolidador agrupa → **o humano decide** → fixes mínimos → commit atômico feito pelo humano ou pelo workflow.
7. **Encerramento.** O STATE.md é atualizado. As specs são comitadas no PR, usadas no review e depois retiradas da área ativa (cap. 9), preservando a referência à revisão e às evidências conforme a política da seção 8.2. A retro roda se algum erro se repetiu.

---

## 7. Como verificar o próprio harness (o cap. 15 aplicado)

Um harness genérico é um produto. Ele precisa de **testes das partes determinísticas** e de um **harness de avaliação** para as partes inferential.

1. **Partes determinísticas** (gate, test guard, task, hooks, render, init): testes comuns com fixtures. Inclui um **teste por trapaça do iceberg**: apagar um teste, adicionar um skip, alterar uma asserção congelada, task sem teste. Cada um precisa reprovar o gate.
2. **Contract tests por adaptador.** O mesmo evento neutro precisa produzir a mesma decisão em Claude Code e Cursor. As ferramentas mudam rápido (cap. 6), então isso é o alarme de quebra.
3. **Harness de avaliação** (cap. 15):
   - **Fixtures:** 3 ou 4 repositórios pequenos em stacks diferentes (TS/vitest, Python/pytest, Go), cada um com um PRD em WHEN/THEN/SHALL.
   - **Baseline congelado** de checks binários por PRD, com pesos por prioridade (P1/P2/P3) e por implementação vs testes.
   - **Juiz** num sub-agent custom com modelo fixo e contexto isolado. Ele nunca avalia trabalho próprio e cita `arquivo:linha` para cada "sim".
   - **Soma por script** (`score.py`), nunca pelo modelo.
   - **Vários runs** por configuração. Reportar pass@k e pass^k **[Externo]** Grace et al.
   - **Ambiente limpo a cada trial**, sem histórico de git de runs anteriores. **[Externo]** No caso relatado pela Anthropic, o agente "colou" lendo o git history.
4. **Ablação.** Comparar sem harness, com harness MVP e com harness + componente X, removendo um componente de cada vez. **[Externo]** Rajasekaran: "every component in a harness encodes an assumption about what the model can't do on its own".
5. **Métricas além da nota**, tiradas do benchmark do cap. 11:
   - pico da janela principal;
   - tokens;
   - tempo;
   - voltas de correção;
   - intervenções humanas;
   - variação da contagem de testes.
6. **Ler transcripts.** Não confiar na nota antes de ler alguns julgamentos inteiros (cap. 15). A armadilha é "o juiz que concorda com tudo".

### 7.1 Provas adicionais de confiabilidade **[Síntese da avaliação]**

O objeto avaliado é o conjunto **modelo + harness + configuração + ambiente**, e não apenas o modelo. Cada comparação precisa identificar essas versões e usar tentativas isoladas. Modelo fixo e contexto limpo reduzem contaminação, mas **não tornam o juiz determinístico**: os checks precisam de calibração com avaliações humanas e inspeção de falsos aceites e falsas rejeições.

Além das quatro fixtures do iceberg, a validação deve cobrir:

| Prova | Resultado esperado |
| --- | --- |
| Tentativa de alterar estado, scripts, perfil, baseline ou evidência por caminhos disponíveis ao agente, inclusive shell | Bloqueio ou detecção antes do aceite, com os limites de cobertura documentados |
| Relatório antigo, modificado, ausente ou produzido para outras entradas | Gate recusa a evidência e exige nova execução válida |
| Substituição de teste mantendo a contagem e falha relevante injetada | A suíte de avaliação expõe a limitação da contagem; a combinação de guard, revisão e sensor semântico detecta a violação do requisito |
| Interrupção durante gate ou persistência do estado | Retomada consistente, sem conclusão sem prova |
| Evento repetido, conflito entre workers, timeout, cancelamento e orçamento esgotado | Runner cumpre os resultados previstos na seção 3.8 |

Medir também taxa de entregas aceitas, custo por entrega aceita (incluindo tentativas malsucedidas), retrabalho e intervenção humana. Registrar número de execuções e dispersão dos resultados, além de pass@k/pass^k. O piloto deve mostrar uma demanda real percorrendo spec → implementação → gate → avaliação → entrega, com provas vinculadas à mesma revisão. Repetir o percurso e exercitar falhas é o que permite avaliar repetibilidade e valor; uma execução bem-sucedida isolada não basta.

---

## 8. Estrutura sugerida

### 8.1 Este repositório (`generic-harness`)

```
generic-harness/
├── AGENTS.md                  # instruções para desenvolver o próprio harness
├── ia-first-dev.pdf           # fonte da verdade
├── docs/research/harness-generico.md
├── core/
│   ├── skills/                # Agent Skills, spec aberta pura
│   │   ├── harness-execute/   # SKILL.md + references/ (orquestração, árvore de sub-agents)
│   │   ├── harness-spec/      # SKILL.md + references/ (auto-sizing, templates)
│   │   ├── harness-onboard/
│   │   ├── harness-review/    # references/{security,requirements,e2e,architecture,regression,performance}.md
│   │   └── harness-retro/
│   ├── agents/                # papéis neutros: verifier, reviewer, consolidator, judge
│   ├── hooks/                 # contrato neutro: stop_gate, boundary_guard, test_guard, session_bootstrap, post_edit
│   ├── cli/                   # harness: init, detect, render, doctor, gate, task, state, spec, update
│   ├── presets/               # node-ts-vitest, python-pytest, go-test (harness templates)
│   └── templates/             # profile.json, AGENTS-blocks.md, STATE.md, spec/design/tasks/task-DoD, validation.md
├── adapters/
│   ├── claude-code/           # tradução de hooks/permissions/agents + plugin opcional
│   ├── cursor/                # hooks.json, cli.json, rules
│   └── codex/
├── evals/                     # cap. 15: fixtures, PRDs, baselines congelados, juiz, score.py
└── tests/                     # testes das partes determinísticas + contract tests dos adaptadores
```

### 8.2 No projeto hospedeiro, depois da instalação

```
host/
├── AGENTS.md                  # do time; o harness só reescreve os blocos marcados
├── CLAUDE.md                  # opcional: "@AGENTS.md" + o que for específico do Claude Code
├── .harness/
│   ├── profile.json           # o contrato (comitado)
│   ├── STATE.md               # memória (comitado)
│   ├── harness.lock           # versão + hashes do que foi vendorizado (comitado)
│   ├── specs/<feature>/       # spec.md, design.md, tasks.md, tasks.json, validation.md
│   └── runs/                  # logs completos e junit.xml (gitignored)
├── .agents/skills/harness-*   # Codex e Cursor
├── .claude/{skills,agents}/harness-* + settings.json
└── .cursor/{hooks.json,cli.json}
```

**Política de estado.** **[Externo]** Lulla et al. viram que os repositórios comitam a configuração dos loops, mas quase nunca os *state files*. Eles também catalogam a "divergência entre as instruções comitadas e o estado do loop" como modo de falha. Proposta: STATE.md e as specs ativas são comitados; `runs/` não é.

**Retenção de evidências [Síntese da avaliação].** Deixar `runs/` fora do Git é uma decisão de armazenamento local, não uma política de auditoria. Antes de remover specs ou limpar runs, definir quais artefatos serão preservados, em qual destino, por quanto tempo, quem pode alterá-los e quem responde pela retenção. O registro da entrega deve apontar para a revisão das specs e para o manifesto de execução da seção 3.7. Quando necessário, logs e relatórios podem ser guardados como artefatos de CI ou em armazenamento controlado. O prazo e o acesso dependem do projeto; nenhuma infraestrutura específica é requisito universal.

**Linguagem dos scripts e hooks:** recomendo **Python 3, só com a biblioteca padrão**:

- funciona em qualquer projeto, independente da stack;
- é a escolha do cap. 15 (soma por script Python) e dos validadores atuais do TLC Spec-Driven **[Externo]**;
- evita hooks que só rodam em bash, o que quebraria no Windows.

---

## 9. Roadmap incremental com critérios de saída binários

O roadmap segue a armadilha do cap. 17: montar toda a infraestrutura antes de completar uma task é o erro. Cada fase só começa quando a anterior passou no seu critério.

| Fase | Entregas | Critério de saída (sim/não) |
| --- | --- | --- |
| **0. Um loop verificável** | `profile.json` (manual + detecção básica), blocos do AGENTS.md, templates (STATE, task com DoD, validation), `harness gate`, `harness task done`, Stop gate no Claude Code, skill `harness-execute` (L1), verifier com evidência | Num **projeto piloto real**, uma task pequena percorre o playbook do cap. 17 e termina com: gate exit 0 associado ao hash da árvore; `validation.md` com `arquivo:linha`; STATE.md atualizado. Uma tentativa de encerrar com gate vermelho **é bloqueada** |
| **1. Enforcement e portabilidade** | test guard (contagem, skip, congelados, task sem teste); boundaries-as-code (deny e ask); SessionStart e PreCompact; `harness init` para 3 presets; `harness doctor`; adaptadores Cursor e Codex; skills `harness-onboard` e `harness-retro` | As 4 trapaças do iceberg reprovam o gate nos testes de fixture. A mesma task piloto passa no Claude Code **e** no Cursor. O `doctor` acusa referência quebrada e comando inexistente |
| **2. Spec e orquestração** | `harness-spec` com auto-sizing e mapa de execução; orquestração por fases (≤ 3 workers, sequência quando há dependência); Planner → Generator → Evaluator com fix loop limitado; `harness-review` local; arquivamento das specs | Uma feature de ~10–18 tasks termina com o **pico da janela principal < 40%**, sem nenhum worker por task, e com cada task concluída via `task done` |
| **3. Medir e automatizar** | harness de avaliação (seção 7); review no GitHub Actions (`/review`, `/fix`, commit pelo workflow, deny de commit/push para a IA); runner de Loop Engineering (headless, disparo por agenda ou evento, worktrees, orçamento de tokens, escalonamento); sensores contínuos e discrimination sensor | O benchmark mostra ganho sobre "sem harness" em ≥ 2 stacks, com vários runs por configuração, e a ablação identifica pelo menos um componente que pode ser desligado |

### 9.1 Evidências complementares por fase **[Síntese da avaliação]**

Estes critérios enriquecem a proposta de roadmap para discussão no Plan; não indicam fases executadas nem autorizam implementação.

| Fase | Complemento ao critério de saída |
| --- | --- |
| 0 | Evidência identifica tentativa, entradas e comandos; um verde antigo é recusado; interrupção não gera conclusão fictícia. Registrar limitações dos controles ainda ausentes |
| 1 | Demonstrar proteção do estado e dos insumos de aceite contra os caminhos disponíveis em cada adaptador suportado, inclusive shell; documentar cobertura e lacunas |
| 2 | Manter rastreabilidade até a entrega e acesso às provas após arquivamento; exercitar retomada e conflitos de estado na orquestração |
| 3 | Repetir entregas em condições declaradas, medir custo por entrega aceita e intervenção humana, calibrar o juiz e demonstrar os cenários de falha do runner da seção 3.8 |

Com essas provas, pode-se avaliar a classificação como **fábrica de software com agentes, de escopo delimitado**. A denominação não depende de quantidade de workers, autonomia total ou infraestrutura empresarial. A fábrica de agentes-produto permanece uma decisão separada (seção 14).

---

## 10. Anti-padrões: o que **não** tornar genérico

- **Gerar o conteúdo do AGENTS.md** a partir do codebase (paths, estrutura, frases vagas). O harness entrega esqueleto, checklist e processo, não conteúdo (cap. 4).
- **Comandos e frameworks hardcoded.** Tudo vem do perfil e é detectado e confirmado (cap. 12, princípio 10).
- **Instalar um catálogo grande de skills por padrão.** Cada description é paga sempre (cap. 5). Escolha a skill pela pergunta a responder (armadilha do cap. 18).
- **Um sub-agent por task** ou "quanto mais agentes, melhor" (cap. 11).
- **Deixar a IA aprovar, rejeitar ou comitar** no review loop (cap. 14).
- **Autoavaliação na mesma janela**, ou um juiz que vê o histórico do run (caps. 13 e 15).
- **Notas de 1 a 5, ou de 0 a 10.** Use checks binários com pesos (cap. 15).
- **Regras sem enforcement**, como "nunca apague testes" só escrito (cap. 12).
- **Referências para arquivos que não existem** (Ap. A).
- **Loop de correção sem limite**, e correção na Dumb Zone (cap. 3). **[Externo]** "loops de correção infinitos" e "verifier theater" estão no catálogo de falhas de Lulla et al.
- **Saídas de tool verbosas** no contexto (cap. 10).
- **Trocar de ferramenta a cada falha** sem investigar que parte do loop faltou (cap. 17).

---

## 11. Riscos e perguntas em aberto

| Risco | Mitigação |
| --- | --- |
| As ferramentas mudam rápido (hooks, skills e sub-agents mudam a cada versão; cap. 6 alerta) | Adaptadores finos, contract tests (seção 7.2), versões mínimas declaradas por adaptador |
| O harness consome o contexto que deveria poupar | Orçamento explícito e `doctor` (seção 4.4) |
| Falsa sensação de segurança ("verde" enganoso, *verifier theater*) | Evidência obrigatória, contagem de testes, leitura de transcripts, conferência manual por amostragem (caps. 12 e 15) |
| Guards heurísticos com falso positivo travam o fluxo | Nível **ask** com aprovação registrada no STATE.md; componentes desligáveis |
| Excesso de engenharia antes do primeiro valor | Roadmap por fases com critérios binários (P14) |
| Segurança: hooks executam comandos; acesso a MCP | Arquivos vendorizados passam por revisão; acesso de pesquisa a dados só leitura e mínimo (cap. 16, nota editorial); credenciais nunca no repo (cap. 6) |
| Divergência entre instruções e estado | O `doctor` confere blocos renderizados contra o perfil; STATE.md comitado |
| Contorno de permissões ou alteração dos insumos de aceite **[Síntese da avaliação]** | Separação de permissões, proteção do executor e testes dos caminhos disponíveis (3.7 e 7.1) |
| Evidências perdidas, antigas ou adulteradas **[Síntese da avaliação]** | Manifesto por tentativa, validação de procedência e retenção vinculada à entrega (3.7 e 8.2) |
| Duplicidade de eventos, falhas na retomada e custo sem controle **[Síntese da avaliação]** | Contrato operacional, limites e testes de falha do runner (3.8) |
| Confundir papéis internos com agentes-produto entregues **[Síntese da avaliação]** | Declarar unidade de entrega e decidir explicitamente a ampliação de escopo (1.5 e 14) |

Perguntas em aberto, trazidas pelo **[Externo]** Böckeler e sem resposta no guia:

- Como medir a *cobertura* de um harness, no espírito da cobertura de código ou do mutation testing?
- Um sensor que nunca dispara indica qualidade alta ou detecção fraca?
- Como manter guides e sensors coerentes e sem contradição à medida que crescem?

Para a primeira e a segunda, o discrimination sensor (S10) e a ablação (seção 7.4) são começos de resposta.

---

## 12. Decisões para a fase de Plan

Cada decisão vem com uma recomendação. Elas pedem confirmação antes de planejar.

| # | Decisão | Opções | Recomendação e motivo |
| --- | --- | --- | --- |
| D1 | Ferramentas na fase 0 | Claude Code; Cursor; Codex; todas | **Claude Code** primeiro: hooks e sub-agents mais completos, e o Cursor carrega os hooks dele. Os formatos ficam neutros desde o início (AGENTS.md e skills pela spec aberta) |
| D2 | Distribuição | vendorizar; plugin; os dois | **Vendorizar + lockfile**, com plugin opcional (seção 4.3) |
| D3 | Camada de spec | própria e mínima; adotar TLC Spec-Driven; OpenSpec; Spec Kit | **Contrato próprio** (task com DoD + gate + `tasks.json`) e uma skill própria mínima, deixando a camada de spec plugável. O guia manda escolher pelos gates e pelo uso da janela, não pelo nome (cap. 9). O TLC atual converge para este desenho e pode ser referência ou alternativa |
| D4 | Linguagem dos scripts | Python stdlib; Node; Go (binário único) | **Python 3 stdlib** (seção 8) |
| D5 | Projeto piloto | — | **Precisa ser escolhido**: um repo real com testes que rodam, para o critério da fase 0 |
| D6 | Formato dos matchers neutros de boundaries | `shell:<glob>` / `write:<glob>`; regex; o formato de uma das ferramentas | Glob neutro e simples, compilado por adaptador e testado por contract test |
| D7 | Onde ficam specs e estado | `.harness/`; `.specs/` (compatível com o TLC) | `.harness/`, tudo num lugar. Se D3 adotar o TLC, usar o layout dele |
| D8 | Unidade de entrega **[Síntese da avaliação]** | Harness; fábrica de software; fábrica de agentes-produto | **Preservar o harness para software** e validar sua operação; tratar agentes-produto como extensão explícita (14) |
| D9 | Fronteira de confiança **[Síntese da avaliação]** | Controles locais; executor isolado; combinação por adaptador | Definir quem escreve estado e evidências, proteger os insumos de aceite e demonstrar cobertura antes de alegar enforcement (3.7) |
| D10 | Retenção e procedência **[Síntese da avaliação]** | Artefatos de CI; armazenamento controlado; política local do piloto | Definir destino, prazo, responsável e vínculo com revisão e run; Git não precisa conter todos os logs (8.2) |
| D11 | Operação do runner **[Síntese da avaliação]** | Acionamento humano; agenda; eventos | Automatizar na fase 3 com contratos de retomada, duplicidade, cancelamento, orçamento e escalonamento (3.8) |
| D12 | Evidência de repetibilidade **[Síntese da avaliação]** | Pilotos e cenários de falha a selecionar | Fixar no Plan as demandas, repetições, métricas e critérios de aceite; não declarar prontidão sem resultados (7.1 e 9.1) |

---

## 13. O que mudou desde o guia, e divergências encontradas **[Externo]**

- **Claude Code lê AGENTS.md nativamente** desde a v2.1.277, quando não há CLAUDE.md. O guia trata os dois como equivalentes e chama tudo de AGENTS.md (cap. 4), e agora isso funciona sem symlink.
- **Limite de tamanho.** A documentação do Claude Code fala em menos de 200 linhas por CLAUDE.md. O guia diz menos de 100, com teto de 150 (cap. 4). **Fica o número do guia**, mais estrito e coerente com P2.
- **Spec das Agent Skills:** `name` com até 64 caracteres, igual ao diretório; `description` com até 1024; corpo abaixo de ~5000 tokens, com até 500 linhas; referências a um nível de profundidade; validador `skills-ref`. O Claude Code trunca description + `when_to_use` em 1536 caracteres na listagem. Tudo isso confirma e detalha o cap. 5.
- **Diretórios de skills** divergem entre ferramentas: `.claude/skills` no Claude Code, `.agents/skills` no Codex, `.cursor/skills` no Cursor, com `.agents/skills` relatado. É o motivo dos adaptadores.
- **Cursor hooks:** o `stop` aceita `followup_message`, com `loop_limit` padrão 5 (null para hooks do Claude Code). O Cursor carrega hooks do Claude Code e trata exit 2 do mesmo jeito. O `cli.json` do cap. 14 corresponde às permissões do Cursor CLI (`.cursor/cli.json`).
- **O TLC Spec-Driven evoluiu além do que o guia descreve:**
  - layout `.specs/` com `STATE.md` (AD-NNN), `LESSONS.md` / `lessons.json` e `validation.md`;
  - validadores Python (`validate_spec`, `validate_tasks`, `check_commit`, `validate_state`) em que exit ≠ 0 bloqueia;
  - Verifier novo e obrigatório, com fault injection (*discrimination sensor*);
  - fix loop limitado a 3 voltas;
  - sub-agents oferecidos acima de ~8 tasks, em lotes de ~7 tasks de fases inteiras, nunca sem consentimento.

  A página atual não menciona `concerns.md` nem Quick Mode, que o guia cita (não confirmado). É um sinal forte de que o desenho desta pesquisa vai na direção que a própria TLC seguiu.
- **Rajasekaran.** Componentes foram removidos à medida que os modelos melhoraram: os context resets saíram com o Opus 4.5 e o construto de sprint saiu com o Opus 4.6. Para ele, o evaluator "is not a fixed yes-or-no decision". Isso fundamenta os `components` desligáveis do perfil.
- **Young.** Feature list em JSON (`category`, `description`, `steps`, `passes`), em que o agente só pode mudar `passes`, mais uma rotina fixa de início de sessão. Fundamenta M2 e M3; o `task done` propõe reservar também a mudança de status ao executor de confiança, com a proteção ainda a demonstrar (3.7).
- **OpenAI, "Harness engineering"** (citado no Ap. C, cap. 13): não foi possível ler o original (HTTP 403). Fontes secundárias descrevem mensagens de linter que dizem como corrigir, AGENTS.md como índice com uma base em `docs/`, e o AGENTS.md atualizado sempre que o agente erra. **Não verificado no original.**

---

## 14. Extensão opcional: agentes como produtos **[Síntese da avaliação]**

Esta seção delimita uma possível evolução, sem alterar P1 nem adicionar uma fase obrigatória ao roadmap. Segundo a [avaliação, seção 5](fabrica-de-agentes-avaliacao.md), fazer do próprio agente a unidade de entrega requer complementar o núcleo atual:

| Capacidade adicional | Contrato e evidência sugeridos |
| --- | --- |
| Entrada de demanda e contrato do agente | Identidade, objetivo, responsável, consumidores, interfaces, ferramentas, dados permitidos, limites de atuação e aceite definidos |
| Composição reutilizável | Montar agentes a partir de componentes versionados, explicitando decisões específicas do domínio |
| Avaliação por agente | Cenários de tarefa, falha de ferramenta e abuso relevante; testes do código do harness não substituem a avaliação comportamental do produto |
| Inventário e releases | Registrar proprietário, versão ativa, ambiente e estado de ciclo de vida; identificar a combinação de código, instruções, modelo, ferramentas e configuração de cada release |
| Publicação e reversão | Disponibilizar release aprovado no ambiente escolhido e demonstrar retorno a uma versão conhecida diante de regressão |
| Operação, melhoria e encerramento | Acompanhar sucesso, falhas, latência e custo; definir responsável, suspensão, desativação e revogação de acessos |

O `profile.json` descreve o projeto hospedeiro. Uma definição versionada de agente-produto teria identidade e ciclo de vida próprios, mesmo que reutilizasse o perfil. O formato e o local desse contrato ficam para um Plan específico, caso D8 escolha essa direção.

Uma demonstração proposta é entregar **dois agentes de objetivos distintos** pelo mesmo processo e atualizar um sem alterar indevidamente o outro. O número é um teste de reuso sugerido pela avaliação, não uma exigência normativa. Treinar modelos, criar framework próprio, usar Kubernetes, oferecer interface visual ou multi-tenancy depende dos consumidores e da operação pretendida.

---

## Apêndice: fontes

### Guia (fonte da verdade)

*IA First Dev: Agentes, Loops e Harness* (out/2026), em `ia-first-dev.pdf`. Capítulos mais usados:

- cap. 4: AGENTS.md
- cap. 5: Skills
- cap. 6: Tools, MCP e RAG
- cap. 9: RPI e Spec-Driven
- cap. 10: Anatomia do loop agêntico
- cap. 11: Sub-agents
- cap. 12: Loop de implementação
- cap. 13: Harness Engineering
- cap. 14: Code review
- cap. 15: Harness determinístico
- cap. 17: Playbook
- Ap. A: Cheat sheets

### Externas (consultadas em 22/10/2026)

- Agent Skills, especificação: https://agentskills.io/specification
- AGENTS.md: https://agents.md/
- Claude Code: plugins https://code.claude.com/docs/en/plugins-reference · hooks https://code.claude.com/docs/en/hooks · sub-agents https://code.claude.com/docs/en/sub-agents · skills https://code.claude.com/docs/en/skills · memória e AGENTS.md https://code.claude.com/docs/en/memory
- Cursor: hooks https://cursor.com/docs/hooks · changelog 2.4 (skills e subagents) https://cursor.com/changelog/2-4 · relato sobre `.agents/skills` https://forum.cursor.com/t/cursor-agent-skills-in-agents-skills/161142/5 · permissões do CLI https://cursor.com/docs/cli/reference/permissions
- Codex, skills: https://learn.chatgpt.com/docs/build-skills
- Justin Young (Anthropic), *Effective harnesses for long-running agents*: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Prithvi Rajasekaran (Anthropic), *Harness design for long-running application development*: https://www.anthropic.com/engineering/harness-design-long-running-apps
- Birgitta Böckeler, *Harness engineering for coding agent users*: https://martinfowler.com/articles/harness-engineering.html
- OpenAI, *Harness engineering* (403 no acesso): https://openai.com/index/harness-engineering/ · fonte secundária: https://www.ignorance.ai/p/the-emerging-harness-engineering
- Addy Osmani, *Loop Engineering*: https://addyosmani.com/blog/loop-engineering/
- Lulla et al., *Loop Engineering: Building Blocks, Adoption, and Impact*: https://arxiv.org/abs/2608.21884
- TLC Spec-Driven: https://agent-skills.techleads.club/skills/tlc-spec-driven/ · instalador TLC: https://github.com/tech-leads-club/agent-skills
- Superpowers: https://github.com/obra/superpowers · OpenSpec: https://github.com/Fission-AI/OpenSpec · Spec Kit: https://github.com/github/spec-kit

### Avaliação complementar local (incorporada em 25/10/2026)

- [O harness genérico e o guia correspondem a uma fábrica de agentes?](fabrica-de-agentes-avaliacao.md): fonte das adições **[Síntese da avaliação]**. Seções 1–3 fundamentam a distinção de escopo e maturidade; seção 4, os limites das garantias; seção 5, as provas operacionais e a extensão para agentes-produto.
- A avaliação contém as referências primárias da IBM Research e do artigo *Agent Factories for High Level Synthesis* sobre os usos de “fábrica”, da Microsoft Learn sobre ciclo de vida de agentes e da Anthropic sobre harnesses e avaliações. Essas referências foram incorporadas por meio da síntese local; não houve nova consulta externa nesta revisão.
