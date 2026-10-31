# Bootstrap de fábrica de agentes em qualquer repositório: pesquisa

> **Fase:** Research do RPI (cap. 9). Entrada para um Plan futuro, numa janela nova. Nada aqui foi implementado.
> **Hierarquia de fontes:** o guia *IA First Dev* (`ia-first-dev.pdf`, cap. N / Ap. X) decide. A pesquisa [harness-generico.md](harness-generico.md) é a fonte da verdade do **harness** e é citada como "HG §N". Esta pesquisa **estende** o HG com a camada que faltava: como o harness, baixado dentro de um repositório qualquer, gera nele a estrutura de uma fábrica de agentes. Onde esta pesquisa propõe mudar algo do HG, a mudança aparece como **[Proposta ao HG]** e não substitui o texto original até ser aceita.
> **Complementos externos** vêm marcados como **[Externo]**, consultados em 25/10/2026. Fontes secundárias e afirmações não conferidas no original são sinalizadas.
> **Data:** 25/10/2026.

---

## 0. TL;DR

1. **A pergunta mudou de "como é o harness" para "como o harness se instala sozinho em qualquer repo".** O HG descreve núcleo + adaptadores + perfil (HG §1.4). Falta o **bootstrapper**: o fluxo que parte de um `git clone` do generic-harness dentro (ou ao lado) de um repositório hospedeiro, de qualquer linguagem, com ou sem estrutura de IA, e termina com uma fábrica operável.
2. **"Fábrica de agentes" aqui significa fábrica de software operada por agentes, escopada ao repositório hospedeiro.** É a segunda linha da tabela do HG §1.5. Agentes-produto (HG §14) ficam fora. Esta interpretação resolve D8 a favor da recomendação do HG e precisa de confirmação (D13).
3. **Gerar estrutura, nunca conteúdo.** O guia proíbe gerar o AGENTS.md a partir do codebase (cap. 4) e manda mapear o projeto real antes de escrever regras (caps. 2 e 9). O bootstrapper cria **diretórios, contratos, esqueletos com TODO, gates e processo**. O conteúdo (comandos, boundaries, convenções) é **detectado com evidência e confirmado por uma pessoa**. **[Externo]** O estudo da ETH Zurich (fev/2026) reforça: arquivos de contexto gerados por LLM reduziram o sucesso em ~3% e aumentaram o custo em mais de 20%, e visões gerais do repositório não ajudaram.
4. **Bootstrap em duas metades.** Uma metade **determinística** (script Python stdlib: detectar, planejar, aplicar, validar) e uma metade **agêntica** (skill `factory-onboard`, rodada pelo agente do dev, que mapeia o codebase com sub-agents e propõe valores marcados como incertos). É o "determinístico onde der" (P8) com o humano em pontos combinados (P10).
5. **Primeiro inventário, depois escrita.** O bootstrapper classifica o repo num **nível de maturidade de IA (N0–N4)**: nada; só instruções; skills e comandos; framework de spec; enforcement. A estratégia muda por nível: criar, adotar, fazer ponte ou coexistir. **Nunca sobrescrever** o que o time escreveu.
6. **Agnóstico de linguagem pela detecção, não por suposição.** A fonte mais confiável dos comandos reais é o **CI e o task runner** (`.github/workflows`, `Makefile`, `justfile`, scripts do manifesto), seguidos dos manifestos e dos presets. Os testes convergem para **JUnit XML** em quase todos os ecossistemas (HG §3.5), inclusive Dart/Flutter via conversor.
7. **A fábrica é uma linha de estações com artefato, papel e gate em cada uma:** Intake → Spec → Plan → Execute → Verify → Review → Deliver → Learn. Cada estação já tem componente no HG (G/S/M). A estrutura de diretórios materializa essas estações (seção 6).
8. **Documentação para IA em quatro camadas**: sempre (AGENTS.md < 100 linhas), sob demanda (`docs/agents/*.md` com "leia quando"), procedimento (skills) e histórico (ADRs, specs arquivadas). O `doctor` mede tamanho, links e frescor.
9. **Sugestões, não instalações.** O bootstrapper gera um relatório de skills, MCPs e sensores recomendados a partir do inventário, cada um com motivo, custo de contexto e fonte. Nada é instalado sem aceite, e o teto de ~20 skills conta as que já existem (cap. 5; cap. 18: "escolha a skill pela pergunta").
10. **Critério de pronto do bootstrap = o primeiro loop do cap. 17 rodando no repo hospedeiro**, não a quantidade de arquivos criados (HG §5, passo 4).
11. **Além da infra, o harness prepara o próprio repo para IA** (seção 15): avalia a prontidão com checks binários derivados do guia (níveis P0–P4, só checks computacionais mudam o nível), captura os padrões reais do projeto como candidatos com evidência `arquivo:linha` para a pessoa aprovar, propõe diffs de documentação (podar antes de acrescentar) e ajuda o dev a escolher e implementar a camada de spec (nativa, TLC, OpenSpec, Spec Kit...), ligando-a ao gate e ao verifier da fábrica. Cada melhoria vira uma demanda que atravessa as estações da fábrica; a primeira delas é o primeiro loop.
12. **Nenhum passo grande roda numa janela só** (15.7, "Quem executa cada passo"). O fluxo de preparação passa a ter executor declarado por passo: script quando é determinístico, sub-agent quando é leitura ou escrita que devolve resultado curto, janela nova depois de cada ponto humano. O orquestrador (`harness-prepare`) não lê código nem escreve docs: lê o estado em disco, delega, recebe referências a arquivos e para nos pontos humanos. Fan-out barato só para leitura; escrita de código segue a árvore do cap. 11 (~3 workers por blocos, nunca um por task).
13. **Cada papel da fábrica tem um tier de modelo, e o harness registra isso no hospedeiro** (seção 16). Quatro tiers abstratos (`fast`, `standard`, `strong`, `frontier`) mapeados por adaptador: leitura em massa em `fast` (Haiku 5.5), implementação em `standard` (Sonnet 5.5), pesquisa, spec, verificação e segurança em `strong` (Opus 5.5), `frontier` (Fable 5.1) desligado por padrão. **[Externo]** Opus custa 2× Sonnet e 40× Haiku; o maior ganho está em tirar a leitura em massa do modelo forte. O harness detecta ferramentas, provedor e agentes que o time já tem, propõe o roster, a pessoa confirma e o `apply` gera os arquivos de sub-agent de cada ferramenta.

---

## 1. Escopo e interpretação

### 1.1 O que o usuário pediu, reformulado

> Baixar o generic-harness, independente da linguagem, e criar no repositório onde ele foi baixado a estrutura de uma fábrica de agentes, com bom contexto, desempenho, spec e documentação otimizada para IA. Sugerir skills ao dev, mas o foco é a estrutura.

Três requisitos derivados:

| # | Requisito | Consequência de design |
| --- | --- | --- |
| R1 | Funciona em repos **com ou sem** estrutura de IA | Inventário e níveis de maturidade antes de qualquer escrita (seção 4) |
| R2 | **Independente da linguagem** | Detecção por evidência + JUnit como língua franca + scripts sem dependência de runtime da stack (seções 3 e 5) |
| R3 | Resultado é uma **fábrica**, não só arquivos de instrução | Estações com artefato, papel, gate e estado em disco (seção 6) |
| R4 | O **repositório** fica pronto para IA, não só a infra: documentação, padrões, sensores e camada de spec, com o menor esforço possível do dev | Avaliação, captura de padrões, melhoria de docs e implementação assistida da camada de spec, executadas como demandas da própria fábrica (seção 15) |
| R5 | **Eficiência e economia**: nenhuma tarefa grande numa janela só; cada papel roda no modelo mais barato que cumpre o gate; o dev sabe quais agentes existem e qual modelo cada um usa | Orquestrador fino com executor declarado por passo (15.7); roster de papéis com tier de modelo, detectado, confirmado e registrado no hospedeiro (seção 16) |

### 1.2 Qual "fábrica"

O HG §1.5 e a [avaliação](fabrica-de-agentes-avaliacao.md) separam três objetivos. Pelo pedido ("a estrutura necessária para que aquele repositório tenha uma fábrica de agentes"), o produto da fábrica é **mudança de software no próprio repositório**: código, testes, evidência e PR. Isso é a **fábrica de software com agentes, de escopo delimitado**. A fábrica de agentes-produto (HG §14) continua sendo extensão separada.

O que essa leitura permite chamar de fábrica, de acordo com a avaliação (seção 5): uma demanda real atravessa as estações com evidência vinculada à revisão, a retomada funciona, contornos de gate são detectados e o processo se repete. O bootstrapper **instala a linha de produção**; a repetibilidade continua precisando ser demonstrada no repo hospedeiro (HG §7.1 e §9.1).

### 1.3 Diferença em relação ao HG

| Tema | HG | Esta pesquisa |
| --- | --- | --- |
| Unidade | o harness (núcleo, adaptadores, perfil) | o **bootstrapper** + a estrutura resultante no hospedeiro |
| Instalação | `harness init` em 5 passos (HG §5) | protocolo detalhado: download, inventário, plano, aplicação, onboarding agêntico, confirmação, primeiro loop (seção 9) |
| Estrutura de IA pré-existente | não tratada | níveis N0–N4 e estratégia por nível (seção 4) |
| Linguagens | 3 presets (node-ts-vitest, python-pytest, go-test) | matriz de detecção para ~12 ecossistemas (seção 5) |
| Documentação | AGENTS.md + `profile.docs` + `docs/agents/testing.md` | camadas, formato de doc para agente, ADRs, frescor (seção 7) |
| Sugestões ao dev | ausente | catálogo de sugestões guiado por sinais do inventário (seção 10) |
| Preparação do repo para IA | `harness-onboard` mapeia e propõe valores do perfil (HG G6) | scorecard P0–P4, captura de padrões com evidência, linter e diffs de documentação, escolha e instalação assistida da camada de spec, backlog de preparação executado pela fábrica (seção 15) |
| Papéis e modelos | `roles` com `strong`/`cheap` e verifier pinado (HG §3.1) | quatro tiers, 15 papéis de sub-agent mais o orquestrador, com esforço, ferramentas e paralelismo; detecção de ferramentas, provedor e agentes do time; arquivos de sub-agent gerados por ferramenta; `reports/agents.md` (seção 16) |

---

## 2. Restrições que o guia impõe a um gerador de estrutura

O desejo de "criar a estrutura automaticamente" encontra limites explícitos no guia. Eles definem o que o bootstrapper pode e não pode fazer.

| Restrição | Fonte | Efeito no bootstrapper |
| --- | --- | --- |
| Não gerar AGENTS.md com `/init` nem listar paths e estrutura | cap. 4 (tabela "fica de fora"; EVITE) | Esqueleto com seções e TODOs; nenhum parágrafo descritivo gerado |
| Começar com o mínimo (stack, comandos, boundaries) e crescer pelos erros reais | cap. 4 ("Construa de forma iterativa"); cap. 2 | O bootstrap entrega o mínimo + a skill de retro (HG G8) |
| Em legado, mapear o real antes de mudar; regras de projeto ideal confundem | cap. 2; cap. 9 (mapeamento) | Inventário e onboarding antes de propor regras; `concerns.md` |
| Comandos precisam existir de verdade | cap. 17, passo 1; Ap. A (checklist) | Todo comando proposto é executado e o exit code registrado (após confirmação, ver 11) |
| ≤ ~20 skills no total; não instalar "por via das dúvidas" | cap. 5 | Instala no máximo o núcleo; o resto vira sugestão |
| Escolher a skill pela pergunta | cap. 18 (ARMADILHA) | Cada sugestão diz qual pergunta ela responde |
| Discovery é humana; a IA ajuda pouco | cap. 7 | Boundaries e decisões ficam com a pessoa; a IA só propõe |
| Montar toda a infraestrutura antes de uma task é o erro | cap. 17 (ARMADILHA) | O bootstrap termina no primeiro loop verificável, não em "tudo instalado" |
| Escolher documentos pelo tamanho do time | cap. 7 ("Quando usar cada documento") | `docs/product/` e RFC são opcionais; spec sempre; ADR quando houver decisão |
| Organização por domínio importa para a IA | cap. 2 ("O codebase é contexto") | O bootstrap **diagnostica** (pastas genéricas, módulos acoplados) mas não reorganiza código |

**Evidência externa que reforça as restrições [Externo]:**

- **Gloaguen et al. (ETH Zurich, arXiv 2602.11988, fev/2026).** Em SWE-bench e num conjunto de issues de repos com arquivos de contexto comitados pelos devs, os arquivos de contexto **não melhoraram** a taxa de sucesso em geral e **aumentaram o custo de inferência em mais de 20%**. Os agentes seguem bem as instruções, mas **visões gerais do repositório não ajudaram**. Os autores dizem que esses arquivos servem para **práticas não padrão** e que qualquer tentativa de melhoria deve ser avaliada antes. Resumos secundários citam ~-3% para arquivos gerados por LLM e ~+4% para escritos por devs (não conferido no corpo do artigo).
- **Lulla et al. (arXiv 2601.20404, ICSE JAWs 2026).** Em 10 repos e 124 PRs, a presença de AGENTS.md se **associou** a -28,64% de tempo mediano e -16,58% de tokens de saída, com conclusão comparável. É correlacional e de amostra pequena.
- **Probe-and-refine (arXiv 2606.20512).** Guidance refinada a partir de sondas sintéticas de bug-fix subiu a taxa de resolução de 28,3% (guidance estática) para 33,0% num modelo aberto. O ganho veio de **localizar o arquivo certo**, não da qualidade do patch. Conclusão dos autores: "how the guidance is produced is the decisive variable".

Leitura conjunta: o que paga o custo é **instrução não óbvia, testável e operacional** (comandos, onde fica o quê no sentido de subsistema, armadilhas conhecidas), produzida a partir de falhas reais. É exatamente o cap. 4. O bootstrapper deve otimizar para isso e medir (seção 8).

---

## 3. Modelo de distribuição: "baixar o repo"

### 3.1 Como outros projetos se instalam **[Externo]**

| Projeto | Como instala | Dependência de runtime | Onde escreve | Atualização |
| --- | --- | --- | --- | --- |
| GitHub Spec Kit | `uv tool install specify-cli` → `specify init --integration <agente>` | Python 3.11+ e uv | `.specify/` + comandos/skills por agente | reinstala templates |
| OpenSpec | CLI npm → `openspec init` | Node 20.19+ | `openspec/specs/`, `openspec/changes/` (+ `archive/`) + comandos por agente (30+ ferramentas) | via CLI |
| BMAD Method | `npx bmad-method install` (v6); v7 alpha via `npx skills add` ou marketplace de plugins | Node 20.12+, Python 3.10+, uv | não detalhado na página | reinstalação |
| Agent OS | base em `~/agent-os/` → `project-install.sh` no projeto | bash (Windows via WSL/Git Bash) | `agent-os/standards/` + `index.yml` + `.claude/commands/` | `project-update.sh`: preserva docs e specs, **reinstala** standards e comandos |
| skills.sh (Vercel) | `npx skills add <owner/repo>` | Node | diretório de skills de cada agente detectado; `--copy` evita symlink | reexecução |
| Copier (templates genéricos) | `copier copy` | Python | qualquer | `copier update`: **merge de 3 vias** entre template antigo, novo e projeto, usando `.copier-answers.yml` (`_src_path`, `_commit`); conflitos em `.rej` |

Observações:

- Todos os frameworks de spec **impõem um runtime** (Node ou Python+uv). Para um repo Go, Rust, Flutter ou .NET, isso é uma dependência estranha à stack.
- Agent OS separa **o que é do framework** (reinstalável) do **que é do projeto** (preservado). É a mesma linha de corte do HG §1.3.
- Copier resolve o problema de atualização que o HG §4.2 descreve ("merge de 3 vias com lockfile") de forma comprovada: guarda a versão de origem e **regenera a base antiga** para comparar.

### 3.2 Opções para o generic-harness

| Opção | Como o dev usa | Prós | Contras |
| --- | --- | --- | --- |
| A. Clone temporário dentro do hospedeiro | `git clone <gh> .harness-src && python3 .harness-src/bootstrap.py` | É literalmente "baixar o repo"; sem gerenciador de pacotes | Precisa ser ignorado ou removido depois; risco de comitar por engano |
| B. Clone fora, apontando para o hospedeiro | `git clone <gh> ~/generic-harness && python3 ~/generic-harness/bootstrap.py --target .` | Hospedeiro fica limpo; um clone serve vários repos (como Agent OS) | O dev precisa lembrar onde está o clone para atualizar |
| C. Submodule ou subtree | `git submodule add <gh> tools/harness` | Versão pinada no próprio repo | Submodule confunde muita gente; subtree polui o histórico |
| D. Instalador via gerenciador (`uvx`, `npx`, `pipx`) | `uvx generic-harness init` | Uma linha | Impõe runtime (contradiz R2) |
| E. Agente como instalador | o dev abre o agente e pede "instale o harness a partir de <url>" | Zero comandos para lembrar; adapta-se à ferramenta | Não determinístico; difícil de testar; viola P8 se for o único caminho |

**Recomendação: A ou B (o mesmo script), com E como camada por cima.**

- `bootstrap.py` aceita `--target <dir>` (padrão: o diretório pai do clone, se o clone estiver dentro de um repo git; senão o cwd). Isso cobre A e B com um código só.
- O que vai para o hospedeiro é **vendorizado** (cópia, não symlink, HG §4.2) com `.harness/harness.lock` contendo a URL de origem, o commit/tag e o hash de cada arquivo instalado. Com isso, `update` pode regenerar a base da versão antiga e fazer o merge de 3 vias à moda Copier.
- No caso A, o bootstrapper adiciona `.harness-src/` ao `.gitignore` e, ao final, oferece removê-lo (o hospedeiro já tem tudo vendorizado).
- A camada E é um `BOOTSTRAP.md` na raiz do generic-harness, escrito para o agente: "rode `python3 bootstrap.py detect`, mostre o relatório, pergunte X, rode `apply`, depois use a skill `factory-onboard`". O agente orquestra; o script faz.

### 3.3 Runtime dos scripts

O HG recomenda **Python 3 stdlib** (HG §8.2, D4). Isso continua valendo, com duas ressalvas:

- Python 3 costuma estar presente em Linux e macOS, mas **não vem instalado por padrão no Windows**. O `BOOTSTRAP.md` precisa dizer isso, e a decisão D4 deve registrar a alternativa (binário único em Go) caso o público tenha muitos devs Windows sem WSL.
- **Nunca** depender do runtime da stack do hospedeiro (nada de `npm` para instalar o harness num repo Python). Os comandos da stack só aparecem **dentro do perfil**, como fatos do projeto.

---

## 4. Inventário: repos com ou sem estrutura de IA

### 4.1 O que procurar **[Externo; lista a validar por ferramenta no Plan]**

| Categoria | Arquivos e diretórios | Ferramenta |
| --- | --- | --- |
| Instruções | `AGENTS.md` (raiz e aninhados), `CLAUDE.md`, `CLAUDE.local.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.cursorrules` (legado), `.cursor/rules/*.mdc`, `.windsurfrules` / `.windsurf/rules/`, `.clinerules`, `.junie/guidelines.md`, `CONVENTIONS.md` (aider) | várias |
| Skills | `.claude/skills/`, `.agents/skills/`, `.cursor/skills/` | Claude Code, Codex/Cursor, Cursor |
| Comandos e prompts | `.claude/commands/`, `.github/prompts/`, `.cursor/commands/` | várias |
| Sub-agents | `.claude/agents/`, `.cursor/agents/` | Claude Code, Cursor |
| Hooks e permissões | `.claude/settings.json`, `.claude/settings.local.json`, `.cursor/hooks.json`, `.cursor/cli.json`, `.codex/config.toml` | várias |
| MCP | `.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json` | várias |
| Frameworks de spec | `.specify/` (Spec Kit), `openspec/` (OpenSpec), `.kiro/steering/` e `.kiro/specs/` (Kiro), `.specs/` (TLC Spec-Driven), `agent-os/` (Agent OS), diretórios do BMAD | — |
| Automação de agentes no CI | workflows com `anthropics/claude-code-action`, `claude -p`, `codex exec`, `agent -p` | — |
| Docs que já servem de contexto | `README*`, `CONTRIBUTING.md`, `docs/`, `adr/` ou `docs/decisions/`, `ARCHITECTURE.md`, `llms.txt` | — |

### 4.2 Níveis de maturidade e estratégia

| Nível | Sinal | Estratégia do bootstrapper |
| --- | --- | --- |
| **N0** nada | nenhum arquivo da 4.1 | **Criar**: esqueleto de AGENTS.md com TODOs (HG G2), perfil, estrutura completa da seção 6 |
| **N1** só instruções | AGENTS.md, CLAUDE.md, rules do Cursor ou Copilot | **Adotar**: AGENTS.md vira canônico; os outros viram **pontes** (CLAUDE.md com `@AGENTS.md`) só com aceite; inserir os blocos gerenciados (HG G1) sem tocar o resto; relatar tamanho, contradições entre arquivos e itens da coluna "fica de fora" do cap. 4 |
| **N2** skills, comandos, sub-agents | `.claude/skills`, `.agents/skills`, `.claude/agents`... | **Coexistir**: contar no orçamento de ~20 skills; prefixar as do harness (`harness-*`) para não colidir; sugerir desativação de duplicatas, nunca apagar |
| **N3** framework de spec | `.specify/`, `openspec/`, `.kiro/`, `.specs/`, BMAD, Agent OS | **Plugar**: a camada de spec do harness é plugável (HG D3). O bootstrapper configura um **adaptador de leitura** (tasks e critérios do framework → `tasks.json` + gate) em vez de instalar a `harness-spec`. Usar o layout dele (HG D7) |
| **N4** enforcement | hooks, deny-lists, agentes no CI | **Compor**: mesclar hooks e permissões preservando os existentes; relatar conflitos (dois Stop hooks, deny que bloqueia o gate); nunca desligar um controle do time |

Regras transversais:

- **Detectar é ler.** A fase de inventário é somente leitura no hospedeiro e escreve apenas em `.harness/` (ou em stdout no `--dry-run`).
- **Toda escrita fora de `.harness/` passa por um plano** mostrado antes (lista de arquivos criados, alterados e intocados) e é idempotente: rodar de novo não duplica blocos.
- **Conflito vira pergunta.** Exemplo: CLAUDE.md e AGENTS.md com regras diferentes. O bootstrapper não escolhe; lista as divergências e deixa a decisão para a pessoa.

### 4.3 Prontidão para harness (*harnessability*)

**[Externo]** Böckeler chama de *harnessability* o quanto um codebase permite ser instrumentado (HG §5). O guia diz o mesmo pelo avesso: um type checker só verifica o que tem tipo, um linter só cobra a convenção que existe (cap. 13).

O inventário mede os **sensores disponíveis**, porque são eles que fecham o loop:

| Sensor | Pergunta binária | Se "não" |
| --- | --- | --- |
| Testes | existe ao menos um comando de teste que roda e sai com 0? | a primeira demanda da fábrica é **criar o sensor** (teste de caracterização), não uma feature |
| Relatório | o teste produz ou pode produzir JUnit? | configurar reporter (seção 5) ou degradar o test guard para "contagem por stdout" com aviso |
| Lint / typecheck | existem e rodam? | registrar como lacuna; sugerir (seção 10) |
| CI | há pipeline que roda os mesmos comandos? | o gate local é a única fonte; sugerir CI na fase 3 |
| Ambiente | existe comando de subir o app (`dev`) com um `ready` verificável? | E2E e verificação de interface ficam sem validação, registrado |

O resultado vai para `.harness/reports/readiness.md`. O HG já diz que, em brownfield, as fases 0 e 1 vêm antes de review sofisticado (HG §5). Esta tabela torna isso decidível.

---

## 5. Detecção agnóstica de linguagem

### 5.1 Ordem de confiança das fontes de comandos

1. **CI do projeto** (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`, `bitbucket-pipelines.yml`). É o que o time de fato roda para aceitar código.
2. **Task runners** (`Makefile`, `justfile`, `Taskfile.yml`, scripts do manifesto como `package.json#scripts`, `pyproject` com tox/nox/poe, `melos.yaml`).
3. **Docs do projeto** (`README`, `CONTRIBUTING`): fonte fraca, só para confirmar.
4. **Convenção do ecossistema** (preset): último recurso, marcado `origin: preset`.

Cada valor do perfil carrega a origem (`ci`, `task-runner`, `manifest`, `docs`, `preset`) e o status (`detected` → `confirmed`). Isso estende o `detected`/`confirmed` do HG §3.1.

### 5.2 Matriz por ecossistema

| Ecossistema | Manifesto / sinal | Teste típico | JUnit XML (para o test guard) |
| --- | --- | --- | --- |
| JS/TS | `package.json` + lockfile (pnpm/yarn/npm/bun) | vitest, jest, playwright | vitest `--reporter=junit --outputFile=…`; jest com `jest-junit`; playwright reporter `junit` |
| Python | `pyproject.toml`, `requirements*.txt`, `uv.lock`, `poetry.lock` | pytest | `pytest --junitxml=…` |
| Go | `go.mod` | `go test` | `gotestsum --junitfile …` (ou `go-junit-report`) |
| Rust | `Cargo.toml` | `cargo test`, nextest | `cargo nextest` com `junit` no perfil de `.config/nextest.toml` |
| Java/Kotlin | `pom.xml`, `build.gradle(.kts)` | JUnit via Maven/Gradle | nativo: `target/surefire-reports/`, `build/test-results/` |
| .NET | `*.csproj`, `*.sln` | `dotnet test` | logger `junit` (pacote JunitXml.TestLogger) ou TRX nativo + conversão |
| Dart/Flutter | `pubspec.yaml` (+ `melos.yaml`) | `flutter test`, `dart test` | saída JSON (`--machine` / `--reporter json`) convertida por `junitreport` (**a validar**) |
| Ruby | `Gemfile` | rspec, minitest | `rspec_junit_formatter`; minitest-reporters |
| PHP | `composer.json` | phpunit, pest | `phpunit --log-junit …` |
| Elixir | `mix.exs` | `mix test` | `junit_formatter` |
| Swift | `Package.swift`, `*.xcodeproj` | `swift test`, xcodebuild | `swift test --xunit-output …` |
| C/C++ | `CMakeLists.txt`, `meson.build` | ctest, gtest | `ctest --output-junit …`; gtest `--gtest_output=xml` |

As flags exatas variam por versão. A matriz é um **ponto de partida para os presets** e cada linha precisa de um teste de fixture no Plan (HG §7, item 1). Quando nenhum JUnit for viável, o guard cai para um modo degradado declarado, nunca para aprovação silenciosa (HG §3.5, "limite da evidência").

### 5.3 Monorepos e poliglotas

- Detectar workspaces (`pnpm-workspace.yaml`, `go.work`, `Cargo.toml [workspace]`, `melos.yaml`, `settings.gradle`, `nx.json`, `turbo.json`) e gerar **um perfil por pacote** quando os comandos diferirem (HG §5, "Monorepo").
- O perfil raiz agrega e o gate pode rodar só os pacotes afetados pelo diff. Isso é desempenho, mas também evita gate vermelho por pacote alheio à task.
- AGENTS.md aninhado só onde o pacote tem regras diferentes de verdade. O custo é manutenção (cap. 4).

---

## 6. A estrutura da fábrica no repositório hospedeiro

### 6.1 Estações

A fábrica é a sequência do cap. 16, com o "quem fecha o loop" do cap. 10 em cada passagem. Toda estação já tem componente no HG.

| Estação | Entrada → saída | Papel | Gate / quem fecha | Componentes HG | Guia |
| --- | --- | --- | --- | --- | --- |
| 1. Intake | demanda (issue, board, pedido) → item rastreável com ID | humano + MCP do board | o item tem problema, origem e responsável | — (nova, ver 6.3) | caps. 7, 8, 16 |
| 2. Spec | item → `spec.md` (+ `design.md`, `tasks.md` por auto-sizing) | planner (modelo forte) | **revisão humana da spec**; validador estrutural (IDs, WHEN/THEN/SHALL, DoD em toda task) | G5, G9 | cap. 9 |
| 3. Plan | tasks → mapa de execução | orquestrador | árvore de decisão de sub-agents | G4 | caps. 11, 17 |
| 4. Execute | task → diff + testes | implementer (modelo barato) | exit code do gate; Stop gate; test guard | S1–S4, S6 | cap. 12 |
| 5. Verify | diff + spec → `validation.md` com evidência | verifier (contexto limpo, modelo pinado) | check sem evidência = não atendido | S7 | caps. 13, 15 |
| 6. Review | diff + regras → achados | especialistas + consolidador | **humano decide**; IA não aprova nem comita | G7, S5, S8 | cap. 14 |
| 7. Deliver | aprovado → commit/PR | humano ou workflow | `task done` + rastreabilidade ID → commit | S2, M6 | caps. 9, 14 |
| 8. Learn | erros recorrentes → regra, exemplo, teste ou sensor | retro | linha nova paga o custo? (poda) | G8, S9 | caps. 2, 4, 13 |

Estado transversal: `STATE.md` + `tasks.json` + bootstrap de sessão (M1–M3).

A coluna "Papel" é detalhada na seção 16: cada papel tem tier de modelo, esforço, ferramentas permitidas e regra de paralelismo.

### 6.2 Layout proposto **[Proposta ao HG §8.2]**

```
host/
├── AGENTS.md                      # do time; harness só reescreve os blocos marcados
├── CLAUDE.md                      # ponte opcional: "@AGENTS.md" (+ específicos do Claude Code)
├── docs/
│   ├── agents/                    # docs SOB DEMANDA para agentes (seção 7)
│   │   ├── testing.md             # tipos de teste, como rodam, o que é parallelSafe
│   │   ├── architecture.md        # alto nível: módulos, fronteiras, fluxo; sem listar paths
│   │   ├── concerns.md            # pontos de atenção do mapeamento (cap. 9)
│   │   └── glossary.md            # linguagem do domínio (cap. 18: /domain-modeling)
│   └── decisions/                 # ADRs imutáveis (cap. 7); 0001-*.md
├── .harness/
│   ├── profile.json               # o contrato (HG §3.1), com origin/status por valor
│   ├── inventory.json             # fatos detectados: stack, IA existente, sensores (somente leitura humana)
│   ├── harness.lock               # origem, versão e hash do que foi vendorizado
│   ├── STATE.md                   # memória e handoff
│   ├── intake/                    # itens de demanda (se não houver board via MCP)
│   ├── work/<ID>/                 # spec.md, design.md, tasks.md, tasks.json, validation.md
│   ├── archive/<data>-<ID>/       # specs encerradas (cap. 9), com ponteiro para o manifesto de evidência
│   ├── reports/                   # readiness.md, suggestions.md, doctor.md (regeráveis)
│   ├── runs/                      # logs e junit (gitignored; retenção conforme HG §8.2)
│   └── evals/                     # fase 3: probes e benchmark do harness neste repo
├── .agents/skills/harness-*       # canônico, padrão aberto (Codex, Cursor)
├── .claude/{skills,agents}/harness-* + settings.json   # adaptador Claude Code
├── .cursor/{hooks.json,cli.json}  # adaptador Cursor
└── .github/workflows/agent-*.yml  # fase 3, opcional: review e runner L6
```

Mudanças em relação ao HG §8.2, com motivo:

| Mudança | Motivo |
| --- | --- |
| `docs/agents/` e `docs/decisions/` fora de `.harness/` | São documentação do **projeto**, úteis a pessoas e versionadas com o código; `.harness/` fica para contrato, estado e evidência |
| `specs/<feature>/` → `work/<ID>/` + `archive/` | Explicita o ciclo de vida do cap. 9 (ativa → arquivada) e o ID como chave (P13) |
| `inventory.json` separado do `profile.json` | Fato detectado ≠ decisão confirmada (HG §3.1, "detectar não é decidir"); o inventário é regenerável, o perfil não |
| `intake/` | Estação 1 sem board; com board, fica vazio e o MCP cumpre o papel (cap. 6: "MCP é conexão") |
| `reports/` | Saídas do bootstrapper e do `doctor` são regeráveis e não poluem o estado |

### 6.3 Contrato mínimo do item de intake

Para a estação 1 não virar "ticket pouco detalhado direto para implementação" (cap. 16, EVITE):

```markdown
# <ID> <título>
- Origem: <issue/board/pedido> · Responsável: <pessoa> · Prioridade: P1|P2|P3
- Problema: <o que dói e para quem>
- Fora de escopo: <...>
- Fontes de contexto: <PRD, Design Doc, ADR, link>
- Dúvidas abertas (decisões que a IA não deve tomar): <...>
```

É o mínimo para a spec não inventar decisões ("documentar para a IA o que ninguém decidiu", cap. 7, ARMADILHA).

---

## 7. Documentação otimizada para IA

### 7.1 Quatro camadas

| Camada | Onde | Quando entra no contexto | Regra de tamanho | Guia |
| --- | --- | --- | --- | --- |
| **Sempre** | AGENTS.md (+ blocos do harness) | toda requisição | < 100 linhas, teto 150; seção > ~20 linhas vira skill | cap. 4 |
| **Sob demanda** | `docs/agents/*.md`, `docs/decisions/` | quando o ponteiro "fazendo X → leia Y" casa | um tema por arquivo; o `doctor` alerta acima de um limite configurável | caps. 2, 4 |
| **Procedimento** | skills (`SKILL.md` + `references/`) | quando a description casa | corpo < ~500 linhas; ≤ ~20 skills | cap. 5 |
| **Histórico** | ADRs, `archive/`, git log | quando a tarefa pede contexto de decisão | ADR é imutável | caps. 7, 9 |

### 7.2 Formato de um doc sob demanda

Proposta de cabeçalho, para o agente e para o `doctor`:

```markdown
---
summary: Como os testes de integração sobem o banco e por que não rodam em paralelo.
read_when: escrevendo ou depurando testes de integração; mexendo em fixtures de banco
verified: 2026-10-25 @ 3f9c1e2   # data e revisão em que o conteúdo foi conferido
owner: <time ou pessoa>
---
```

Regras de corpo, todas derivadas do cap. 4:

- regras **testáveis** ("valores monetários usam Decimal"), não frases vagas;
- **exemplos reais curtos** que apontam para código existente (`arquivo:linha`), porque "o modelo copia o que vê" (cap. 2);
- cada proibição com a alternativa (P15);
- **sem** árvore de pastas, sem cópia do README, sem instruções de uma task específica.

O `read_when` do arquivo e a linha do AGENTS.md que aponta para ele devem dizer a mesma coisa. O `doctor` confere que todo arquivo de `docs/agents/` tem ponteiro, que todo ponteiro tem arquivo (Ap. A) e que `verified` não está mais velho que N commits nos caminhos citados (frescor, configurável). Esse último item ataca "informação desatualizada", que o cap. 2 lista como causa de falha.

### 7.3 O que o bootstrapper gera e o que não gera

| Artefato | Gera? | Como |
| --- | --- | --- |
| AGENTS.md (N0) | esqueleto | seções do checklist do Ap. A com TODOs; blocos BOUNDARIES e Workflow renderizados do perfil |
| AGENTS.md (N1+) | só blocos | insere ou atualiza os blocos marcados; o resto é do time |
| `docs/agents/testing.md` | rascunho com evidência | a skill `factory-onboard` escreve a partir do que **executou e observou**; trechos sem evidência saem como `> INCERTO:` |
| `docs/agents/architecture.md` | rascunho curto | alto nível só (cap. 4); **[Externo]** visões gerais não melhoraram o sucesso no estudo da ETH, então o arquivo é sob demanda e curto |
| `concerns.md` | sim | saída direta do mapeamento (cap. 9) |
| ADRs | não | template `docs/decisions/0000-template.md`; ADRs nascem de decisões reais |
| `llms.txt` | não por padrão | ver 7.4 |

### 7.4 `llms.txt`

**[Externo]** `llms.txt` é um Markdown na raiz de um **site** com resumo e links curados, proposto em 2024 e mantido pela comunidade, sem padronização formal. Fontes secundárias relatam adoção desigual e que poucos acessos de bots de IA realmente buscam o arquivo. Ele serve a quem **publica documentação** para ser consumida por LLMs de fora. Dentro do repositório, a árvore "fazendo X → leia Y" do AGENTS.md cumpre o papel, e de forma condicional. Recomendação: gerar `llms.txt` só se o hospedeiro for biblioteca ou produto com site de docs, como sugestão (seção 10), não como estrutura.

---

## 8. Spec e desempenho

### 8.1 Formato de spec

O contrato do guia (cap. 9; Ap. A) continua sendo o do harness: problema e escopo, user stories com ID e prioridade em WHEN/THEN/SHALL, edge cases, requisitos, critérios de sucesso; design com decisões e racional; tasks com o quê, onde e DoD; auto-sizing.

Comparação com os frameworks que o bootstrapper pode encontrar (nível N3) **[Externo]**:

| Framework | Artefatos | Ideia própria | Como o harness se acopla |
| --- | --- | --- | --- |
| Spec Kit | constitution, spec, plan, tasks (+ extensões de bug e assess) | **constitution**: princípios não negociáveis do projeto | constitution ≈ boundaries + perfil; não duplicar, apontar |
| OpenSpec | `specs/` (estado atual) + `changes/<nome>/{proposal,specs,design,tasks}` → `archive/` | **specs vivas**: o arquivamento de uma change atualiza `specs/` | ler `tasks.md` da change ativa; gate e verifier usam os cenários WHEN/THEN |
| Kiro | `.kiro/steering/` + `.kiro/specs/<feature>/{requirements,design,tasks}` | requisitos em **EARS** (WHEN … THE SYSTEM SHALL …) | o WHEN/THEN/SHALL do guia já é compatível com EARS |
| TLC Spec-Driven | `.specs/` com STATE, LESSONS, validation | validadores Python com exit code (HG §13) | layout dele (HG D7) |

**Divergência a registrar: specs vivas.** O guia manda comitar a spec com a implementação, usá-la no review e **retirá-la da área ativa** (cap. 9). O OpenSpec mantém um `specs/` que descreve o comportamento atual do sistema e cresce a cada change. A segunda ideia não está no guia. Ela ajudaria o agente a **localizar** comportamento existente, que é onde o probe-and-refine viu o ganho, mas cria mais um conjunto de arquivos que envelhece (custo de manutenção do cap. 4). Fica como decisão (D17), com o padrão do guia como recomendação.

### 8.2 Desempenho

"Desempenho" aqui tem dois sentidos: custo e velocidade por requisição, e taxa de entregas aceitas. A estrutura afeta os dois.

| Alavanca | Mecanismo na estrutura | Guia / fonte |
| --- | --- | --- |
| Contexto fixo mínimo | AGENTS.md < 100 linhas; ≤ 6 skills do harness; SessionStart ≤ ~20 linhas; `doctor` estima tokens fixos e falha acima do orçamento (HG §4.4) | caps. 3, 4, 5 |
| Prefixo estável | conteúdo que muda (task atual, último gate) vai para o SessionStart, **nunca** para o AGENTS.md; mantém estável a parte fixa do contexto. **[Inferência]** favorece o cache de prompt das ferramentas | cap. 4; **[Externo]** cache de prompt |
| Saídas enxutas | gate devolve resumo; log completo em disco | cap. 10 |
| Modelo por papel | `strong` planeja e verifica; `cheap` implementa | cap. 8 |
| Delegação por acoplamento | árvore do cap. 11; ~3 workers por blocos; nunca um por task | cap. 11 |
| Gate incremental | monorepo: só pacotes afetados; testes `parallelSafe` em paralelo | caps. 9, 12 |
| Guidance que localiza | `docs/agents/` com "onde fica o subsistema X" no nível de módulo e armadilhas conhecidas | **[Externo]** probe-and-refine |
| Medir em vez de supor | `.harness/evals/` com probes do próprio repo (fase 3): rodar tarefas pequenas com e sem um componente (ablação, HG §7.4) | cap. 15; **[Externo]** ETH, probe-and-refine |

Os dois estudos de 2026 sobre AGENTS.md divergem (um vê custo maior sem ganho de sucesso, outro vê tempo e tokens menores). Para o harness, a conclusão prática é a mesma do cap. 15: **medir no repo hospedeiro** antes de afirmar ganho.

---

## 9. Protocolo de bootstrap, de ponta a ponta

Aplica o playbook do cap. 17 ao próprio bootstrap e detalha o HG §5.

| Passo | Comando / ator | Escreve | Saída verificável |
| --- | --- | --- | --- |
| 0. Baixar | dev: `git clone <gh>` (dentro ou fora do hospedeiro) | nada no hospedeiro | — |
| 1. Detectar | `python3 bootstrap.py detect` | só `.harness/inventory.json` e `reports/readiness.md` | nível N0–N4, stack, comandos candidatos com origem, sensores disponíveis |
| 2. Planejar | `bootstrap.py plan` | nada (dry-run) | lista de arquivos a criar, alterar (com diff dos blocos) e preservar; conflitos encontrados |
| 3. Confirmar comandos | **humano** | — | lista de comandos aprovados para execução (ver 11: rodar comandos é executar código do repo) |
| 4. Aplicar | `bootstrap.py apply --tools claude[,cursor,codex]` | estrutura da 6.2, adaptadores, `harness.lock`, `.gitignore` | `doctor` verde; comandos aprovados executados com exit code registrado |
| 5. Onboarding agêntico | agente do dev, skill `factory-onboard`, **janela nova** | `docs/agents/*`, `concerns.md`, propostas no perfil marcadas `detected` | cada afirmação com evidência ou `INCERTO` (cadeia codebase → docs → Context7 → web → incerto, cap. 9) |
| 6. Discovery do harness | **humano** revisa o perfil | `profile.json` (`confirmed`) | boundaries com par `instead`; `parallelSafe` marcado; docs sob demanda apontados |
| 7. Primeiro loop | dev + agente, uma mudança pequena | `work/<ID>/`, `validation.md`, `STATE.md` | **critério de aceite do bootstrap** (HG §5, passo 4): gate rodou, evidência registrada, STATE atualizado, encerrar com vermelho foi bloqueado |
| 8. Sugestões | `bootstrap.py suggest` | `reports/suggestions.md` | lista priorizada (seção 10); nada instalado |
| 9. Retro | skill `harness-retro` após as primeiras tasks | AGENTS.md, docs, sensores | cada erro recorrente virou regra, exemplo, teste ou sensor; linhas que não pagam o custo foram podadas |

Propriedades do script:

- **Idempotente**: `apply` repetido não duplica blocos nem sobrescreve arquivos do time.
- **Reversível**: `apply` registra no lock o que criou; `bootstrap.py uninstall` remove só isso e os blocos marcados.
- **Atualizável**: `bootstrap.py update` regenera a base da versão do lock, faz merge de 3 vias e marca conflitos (padrão Copier, seção 3.1).
- **Sem rede por padrão** depois do download, exceto quando o dev pede sugestões com busca externa.

### 9.1 Comportamento por cenário

| Cenário | Diferença no protocolo |
| --- | --- |
| Greenfield (repo vazio ou quase) | Passo 1 detecta pouco; passo 5 é curto; a primeira demanda tende a ser criar os sensores (teste, lint) e o primeiro ADR de stack. O guia sugere Lean Inception só se houver incerteza e porte médio (cap. 7). Detalhado em [greenfield-do-zero.md](greenfield-do-zero.md) (D35–D45) |
| Brownfield sem IA (N0) | Fluxo completo; `concerns.md` e `readiness.md` pesam mais; regras descrevem o real (cap. 2) |
| Brownfield com IA (N1–N4) | Passo 2 mostra adoção, pontes e conflitos; passo 5 começa pelas regras existentes |
| Sem testes | O primeiro loop é escrever um teste de caracterização que passa; sem sensor não há fábrica (cap. 13) |
| Monorepo | Perfil por pacote; primeiro loop num pacote só |

---

## 10. Sugestões ao dev: skills, MCPs, sensores

### 10.1 Mecanismo

`bootstrap.py suggest` cruza o `inventory.json` com um **catálogo versionado** no generic-harness (`core/catalog/*.json`). Cada entrada tem:

```json
{
  "id": "mcp-playwright",
  "kind": "mcp",
  "when": { "any": ["web-ui-detected", "e2e-missing"] },
  "answers": "Como verificar comportamento de interface no navegador?",
  "why": "Requisitos de interface precisam de E2E real (cap. 13, Teste Fake; cap. 16).",
  "contextCost": "ferramentas do MCP no contexto enquanto ativo",
  "source": "<url>",
  "trust": "oficial | comunidade | não auditado"
}
```

Regras, todas do guia:

- **Nunca instala.** Gera `reports/suggestions.md`; o dev aceita item por item (cap. 5: "instalar por via das dúvidas" é EVITE).
- **Conta o orçamento.** Mostra "skills ativas: 9 (6 do harness + 3 do time); teto ~20" antes de sugerir mais (cap. 5).
- **Diz a pergunta que a sugestão responde** (cap. 18).
- **Marca a confiança da fonte.** **[Externo]** Diretórios como skills.sh avisam que não garantem qualidade nem segurança das skills listadas. Arquivos vendorizados passam por revisão (HG §11).

### 10.2 Exemplos de regras sinal → sugestão

| Sinal no inventário | Sugestão | Pergunta que responde | Fonte no guia |
| --- | --- | --- | --- |
| dependências externas com versões recentes | MCP **Context7** + linha no AGENTS.md | a API desta lib mudou? | cap. 4 |
| UI web ou mobile detectada; sem E2E | MCP **Playwright** (web) ou equivalente da stack | a tela faz o que a spec diz? | caps. 13, 16 |
| board referenciado (Jira/Linear) em docs ou CI | MCP do board + skill de tasks no padrão do time | de onde vem a demanda e como ela vira task? | caps. 8, 16 |
| codebase grande sem docs de arquitetura | **CodeNavi** / mapeamento | como este código está organizado? | cap. 18 |
| pastas genéricas, módulos muito acoplados | **Domain Analysis**, **Coupling Analysis** | onde estão as fronteiras? | caps. 2, 18 |
| PRs com muitos comentários de review | **gh-address-comments** | quais comentários procedem? | cap. 18 |
| decisão de arquitetura em aberto | `/domain-modeling` + `/code-design` → RFC | quais alternativas e trade-offs? | cap. 18 |
| tarefa recorrente sem procedimento (vista na retro) | criar skill do projeto com **skill-creator / skill-architect** | como fazer esta classe de trabalho sempre igual? | cap. 5 |
| framework de spec ausente e equipe > 1 | camada de spec do harness ou adotar TLC/OpenSpec/Spec Kit | qual contrato a IA recebe? | cap. 9 |
| sem lint ou typecheck | sensor computacional da stack | o que o agente erra que uma ferramenta pegaria? | cap. 13 |
| lib ou produto com site de docs | `llms.txt` | como LLMs de fora leem nossa doc? | **[Externo]** |

O catálogo é dado, não código: crescer o catálogo não muda o bootstrapper (P3).

---

## 11. Riscos específicos do bootstrapper

| Risco | Mitigação |
| --- | --- |
| **Executar código do repo ao "verificar comandos".** Rodar `npm test` ou `make` num repo recém-baixado executa scripts arbitrários | Passo 3: a pessoa aprova a lista antes da execução; `detect` nunca executa nada; documentar no `BOOTSTRAP.md` |
| Sobrescrever regras do time | Escrita só em blocos marcados ou arquivos novos; plano antes; lock para desfazer |
| Gerar conteúdo que dilui o contexto | Esqueletos com TODO; `INCERTO` explícito; `doctor` mede tamanho; **[Externo]** ETH |
| Impor runtime estranho à stack | Python stdlib (ou binário único, D4); nada de npm/uv para instalar |
| Symlinks quebrando no Windows ou entre ferramentas | Cópia por padrão (HG §4.2; **[Externo]** `skills --copy`) |
| `.harness-src/` comitado por engano | `.gitignore` automático + oferta de remoção ao final |
| Colisão com framework de spec existente | Nível N3 → adaptador de leitura, não instalação paralela |
| Docs sob demanda envelhecem | `verified` + frescor no `doctor`; retro poda |
| Catálogo de sugestões vira vetor de supply chain | Fonte e confiança declaradas; nada auto-instalado; revisão do que for vendorizado |
| Confundir "estrutura instalada" com "fábrica operando" | Critério de aceite = primeiro loop (passo 7); repetibilidade medida depois (HG §9.1) |
| Lock-in numa ferramenta | AGENTS.md + skills pela spec aberta como canônicos; adaptadores finos (HG §4) |

---

## 12. Decisões para o Plan

Continuam abertas D1–D12 do HG §12. As novas:

| # | Decisão | Opções | Recomendação e motivo |
| --- | --- | --- | --- |
| D13 | Sentido de "fábrica de agentes" | software no próprio repo; agentes-produto; ambos | **Software no próprio repo** (1.2). Fecha D8 do HG na mesma direção |
| D14 | Forma de distribuição | clone dentro; clone fora; submodule; gerenciador de pacotes; agente-instalador | **Clone dentro ou fora com o mesmo `bootstrap.py --target`** + `BOOTSTRAP.md` para o agente orquestrar (3.2) |
| D15 | Diretório canônico de skills | `.agents/skills` + cópias por adaptador; `.claude/skills` canônico | **`.agents/skills` canônico** (padrão aberto, lido por Codex e relatado no Cursor), cópia com campos extras para o Claude Code (HG §4.2) |
| D16 | Onde moram docs para agentes | `docs/agents/`; `.harness/docs/`; `agent_docs/` (exemplo do cap. 4) | **`docs/agents/`**: é doc do projeto, útil a pessoas; o nome exato é preferência do time e vai para o perfil |
| D17 | Specs vivas (estilo OpenSpec) | não; sim, opcional; sim, padrão | **Não por padrão** (cap. 9 manda arquivar); habilitar como componente desligável se o piloto mostrar ganho de localização |
| D18 | Política com framework de spec existente | adaptar; migrar; ignorar | **Adaptar** (adaptador de leitura), nunca migrar sem pedido (4.2, N3) |
| D19 | Execução de comandos no bootstrap | nunca; com aprovação; automática | **Com aprovação explícita da lista** (11) |
| D20 | Escopo do catálogo de sugestões na fase 0 | nenhum; só MCPs e skills citados no guia; aberto | **Só itens citados no guia** (Context7, Playwright, board, kit do cap. 18, skill-creator); externo depois, com campo de confiança |
| D21 | Projeto piloto (refina D5 do HG) | um repo; dois repos de stacks diferentes | **Dois**: um N0 brownfield e um N1+ (com estrutura de IA), de linguagens diferentes, para exercitar R1 e R2 desde o início |
| D22 | Escala de prontidão | adotar a da Factory ou Larridin; própria derivada do guia | **Própria (P0–P4, 15.2)**, com tabela de correspondência para os pilares externos. Os modelos externos pontuam presença e cobrem temas que o guia não trata |
| D23 | Quem decide o nível | checks computacionais e inferenciais; só computacionais | **Só computacionais**; inferenciais geram achados (cap. 15: tirar do juiz a liberdade que ele não precisa ter) |
| D24 | Frameworks de spec com adaptador na fase 2 | todos; nativo + um; nativo + dois | **Nativo + OpenSpec + TLC**: OpenSpec é o mais universal, tem binário sem runtime e `validate --json`; TLC é o mais próximo do guia e já traz validadores. Spec Kit na fase 3; Superpowers, Kiro e BMAD em coexistência até haver piloto |
| D25 | Fonte do contexto permanente quando há framework | AGENTS.md canônico; arquivo do framework canônico; os dois | **AGENTS.md canônico**; constituição, `config.yaml#context` e steering só apontam e acrescentam o específico do framework; o linter acusa duplicação |
| D26 | Como as melhorias de preparação são aplicadas | script direto; demandas da fábrica | **Demandas da fábrica** (READY-NNN, quase sempre Quick Mode), exceto a estrutura determinística do `apply`. É o que transforma a preparação no primeiro loop |
| D27 | Escopo da avaliação | só o guia; guia + pilares externos | **Guia decide o nível**; pilares externos (observabilidade, segurança de branch, devcontainer, analytics) aparecem como informativos |
| D28 | Quem conduz o fluxo da 15.7 | um agente faz tudo; orquestrador + sub-agents; só scripts | **Orquestrador fino (`harness-prepare`) + executor declarado por passo** (script, sub-agent ou janela nova); profundidade 2; ponto humano encerra a sessão (15.7) |
| D29 | Tiers de modelo no perfil | 2 (`strong`/`cheap`, HG); 4 (`fast`/`standard`/`strong`/`frontier`) | **4 tiers [Proposta ao HG §3.1]**. `cheap` vira `standard`. A diferença de preço entre Sonnet e Haiku (20×) é maior que entre Opus e Sonnet (2×), e dois tiers escondem a economia principal (16.3) |
| D30 | Roster padrão | só os papéis do HG (planner, implementer, verifier); roster completo da 16.5 | **Roster da 16.5 entregue por fase** (16.9): fase 0 com `explorer`, `implementer`, `verifier`; o resto entra quando a estação correspondente entra |
| D31 | Política de pin | nada pinado; tudo pinado; só juízes | **Só `verifier` e `judge` pinados por ID completo**; os demais usam alias, e o `doctor` mostra o modelo resolvido (16.8) |
| D32 | Uso do tier `frontier` | desligado; ligado para pesquisa; advisor | **Desligado por padrão**; liga por papel, com motivo registrado. O ganho medido como advisor (+1,7 ponto a 2,1× do custo) ficou no ruído (16.3) |
| D33 | Onde registrar | só `profile.json`; arquivo próprio (`agents.json`); perfil + relatório | **`profile.json` (`models` + `roles`) como decisão confirmada; `inventory.json#agents` como fato detectado; `reports/agents.md` para a pessoa**; arquivos de sub-agent gerados por ferramenta (16.7) |
| D34 | Como validar a escolha de modelo por papel | aceitar a tabela; medir | **Medir na fase 3** com ablação por papel em `.harness/evals/`, por custo por task concluída (16.6) |

---

## 13. Roadmap: o que o bootstrap acrescenta às fases do HG

Mantém a regra do HG §9: uma fase só começa quando a anterior passou no critério.

| Fase HG | Acréscimo do bootstrapper | Critério de saída adicional (sim/não) |
| --- | --- | --- |
| 0 | `detect` + `plan` + `apply` para N0 e N1; esqueleto de AGENTS.md; `inventory.json`; `readiness.md`; adaptador Claude Code | No piloto N0, o bootstrap termina com o primeiro loop aceito (passo 7). Rodar `apply` duas vezes não altera nada na segunda |
| 1 | N2–N4 (coexistir, compor hooks); matriz de detecção com fixtures por ecossistema; `factory-onboard`; `uninstall`; `doctor` com frescor | No piloto N1+, nenhum arquivo do time foi alterado fora dos blocos; os conflitos foram listados. Fixtures de ≥ 3 ecossistemas geram perfil com comandos que rodam |
| 2 | Adaptador de leitura para ≥ 1 framework de spec (N3); intake; `archive/` | Uma feature num repo N3 passa pelo gate e verifier do harness usando as tasks do framework existente |
| 3 | `update` com merge de 3 vias; `suggest` com catálogo externo; probes em `.harness/evals/` | Atualizar o harness num piloto preserva as edições locais e marca conflitos; as probes mostram efeito mensurável (positivo ou nulo) de pelo menos um componente |

Acréscimos da preparação do repositório (seção 15), na mesma régua:

| Fase HG | Acréscimo | Critério de saída adicional (sim/não) |
| --- | --- | --- |
| 0 | `assess` com os checks computacionais de P0 e P1; questionário; backlog READY | Rodar `assess` duas vezes sem mudança no repo gera o mesmo `readiness.json`; nenhuma escrita fora de `.harness/`. No piloto N0, o primeiro loop aceito é um READY |
| 1 | captura de padrões (`patterns.md`); linter de AGENTS.md (metade computacional e inferencial); diffs de poda | Todo candidato em `patterns.md` tem evidência `arquivo:linha`; no piloto N1+, o diff de poda reduz o AGENTS.md sem remover nenhum comando ou boundary aprovado |
| 2 | escolha da camada de spec; instalação assistida; adaptadores nativo, OpenSpec e TLC; checks P2–P3; diretrizes de review a partir dos padrões | Num piloto, o dev escolhe um framework externo e uma change passa pelo validador nativo, pelo gate e pelo verifier do harness, com R20 e R21 verdes |
| 3 | histórico de prontidão; `doctor` no CI; criação de skills do projeto a partir de padrões; checks P4 | O histórico mostra o nível do piloto em pelo menos duas datas; uma probe compara o resultado de tarefas antes e depois de uma melhoria de preparação |

Acréscimos de orquestração, agentes e modelos (15.7 e seção 16):

| Fase HG | Acréscimo | Critério de saída adicional (sim/não) |
| --- | --- | --- |
| 0 | `harness-prepare` com executor por passo; tiers e `roles` no perfil; `explorer`, `implementer`, `verifier` gerados para o Claude Code; detecção de provedor e de agentes do time; `reports/agents.md` | No piloto N0, a preparação inteira roda sem que a janela principal passe de 40%, e todo passo de leitura em massa roda num sub-agent `fast` |
| 1 | `researcher`, `planner`, `mechanical`, `doc-writer`, `retro`, `auditor`, `synthesizer`; geração para Cursor e Codex; checks do `doctor` sobre agentes (16.8) | No piloto N1+, os agentes que o time já tinha foram adotados ou mantidos, nenhum foi sobrescrito, e o `doctor` mostra o modelo resolvido de cada papel em cada ferramenta |
| 2 | `reviewer` por especialidade, `security`, `consolidator`, `triager`; escalonamento por `fallbackTier` | Uma feature de ~10–18 tasks termina com custo registrado por papel no `STATE.md`, e nenhum worker foi disparado por task |
| 3 | `judge`; ablação por papel em `.harness/evals/` | A ablação compara pelo menos dois tiers para o `implementer` em custo por task concluída e mantém ou troca o padrão com base no resultado |

---

## 14. Anti-padrões do bootstrapper

- Gerar AGENTS.md, `architecture.md` ou README a partir do código e chamar isso de onboarding (cap. 4; **[Externo]** ETH).
- Instalar todos os componentes e todas as skills "para o repo ficar completo" (caps. 5, 17).
- Exigir Node, uv ou outro runtime alheio à stack para instalar a fábrica.
- Migrar um framework de spec existente sem pedido.
- Executar comandos do repo sem aprovação.
- Declarar a fábrica pronta porque os diretórios existem (cap. 17, ARMADILHA; avaliação, seção 6).
- Reescrever a estrutura de pastas do código para "ficar boa para IA" (o cap. 2 diagnostica; reorganizar é decisão do time, via RFC/ADR).

---

## 15. Preparação do repositório para IA: avaliar, capturar padrões e implementar

> Seção acrescentada em 25/10/2026. Continua sendo Research: nada aqui foi implementado.

### 15.1 O que muda no pedido

As seções 3 a 13 tratam da **infra da fábrica**: inventário, estrutura, estações, gates e orquestração. O pedido novo acrescenta um segundo produto: um **repositório que funciona bem com IA**, com documentação, convenções, sensores, camada de spec, skills e conexões no lugar. O guia trata as duas coisas como inseparáveis:

- "A IA cobra as boas práticas" (cap. 7): sem bom input, o output é ruim e os tokens vão embora.
- "O código precisa permitir o harness" (cap. 13): um type checker só verifica o que tem tipo, um linter só cobra a convenção que existe, um agente de review só aplica a arquitetura que está documentada.
- "Organizar para a IA é, em grande parte, organizar para pessoas" (cap. 2).

A consequência para o harness é uma **trilha de preparação** com quatro movimentos, todos do guia:

| Movimento | Pergunta | Saída | Guia |
| --- | --- | --- | --- |
| Avaliar | o repo está pronto para um loop verificável? | scorecard com checks binários e nível P0–P4 (15.2) | caps. 4, 9, 12, 13, 17; Ap. A |
| Capturar padrões | como este projeto realmente faz as coisas? | candidatos a regra, cada um com evidência e destino (15.3) | caps. 2, 4, 6, 9 |
| Melhorar ou criar documentação | o que falta, o que sobra, o que está errado? | diffs propostos e esqueletos, nunca escrita silenciosa (15.4) | caps. 2, 4, 7, 14 |
| Implementar o que falta | qual camada de spec, quais skills, quais sensores? | instalação assistida e adaptador para o framework escolhido (15.5, 15.6) | caps. 5, 6, 9, 12, 18 |

A regra que costura os quatro: **cada melhoria vira uma demanda da própria fábrica** (15.7). A preparação usa as estações da seção 6 para preparar o repositório. Isso evita a armadilha do cap. 17 ("montar toda a infraestrutura antes de completar uma task"): a primeira melhoria já é o primeiro loop.

São dois eixos diferentes, que não devem ser confundidos:

| Eixo | Mede | Escala | Seção |
| --- | --- | --- | --- |
| Estrutura de IA existente | o que o time já instalou (instruções, skills, spec, hooks) | N0–N4 | 4.2 |
| Prontidão | se o repo sustenta um loop verificável e melhora com ele | P0–P4 | 15.2 |

Um repo pode ser N3 (tem OpenSpec instalado) e P0 (o comando de teste não roda). A estratégia de escrita segue o eixo N; a ordem das melhorias segue o eixo P.

### 15.2 Avaliação: o scorecard de prontidão

#### O que o mercado faz **[Externo]**

| Modelo | Estrutura | Regra de nível | Correção |
| --- | --- | --- | --- |
| Factory, *Agent Readiness* | 9 pilares (Style & Validation, Build System, Testing, Documentation, Development Environment, Debugging & Observability, Security, Task Discovery, Product & Experimentation); 5 níveis (Functional, Documented, Standardized, Optimized, Autonomous); critérios por repositório e por aplicação em monorepos (`3 / 4`) | contíguo; passar 80% dos critérios do nível atual para destravar o próximo | `/readiness-report` avalia; `/readiness-fix` corrige os critérios que falharam; o artigo de 27/05/2026 diz que ele "propõe" mudanças (ex.: criar AGENTS.md, montar scaffolding de teste, documentar convenção) |
| Larridin, *readiness checklist* | 84 checks binários em 9 categorias; 5 níveis (Baseline, Documented, Agent-ready, Optimized, Autonomous) | contíguo; o nível passa com ≥ 50% dos checks avaliados passando e ≥ 50% dos checks efetivamente avaliados; o que não dá para avaliar é pulado | não descrita |
| `agent-ready` (CLI aberto) e skills de "codebase readiness" | nota 0–100 explicável | faixas | variável |

Três ideias desses modelos valem para o harness: **checks binários**, **níveis contíguos** (não se pula nível) e **escopo por aplicação em monorepos** (casa com a seção 5.3). Também vale o ciclo **relatório → correção → novo relatório** e a observação da Factory de que a nota serve para comparar o mesmo repo ao longo do tempo.

Duas ideias **não** valem sem ajuste:

1. **Presença não é qualidade.** "AGENTS.md existe" e "Skills existem" pontuam nesses modelos. O guia (cap. 4) e o estudo da ETH (seção 2) dizem que um AGENTS.md ruim custa mais do que ajuda. O scorecard do harness mede propriedades: tamanho, boundaries com alternativa, comandos que rodam, ponteiros que resolvem.
2. **Escopo.** Observabilidade, analytics de produto, experimentação e proteção de branch são boas práticas, mas o guia não as trata. Entram como **informativas**, sem afetar o nível (D27).

A Factory não diz, na página consultada, se cada critério é avaliado por LLM ou por regra determinística. O harness precisa decidir isso explicitamente (abaixo).

#### Os níveis do harness, derivados do guia

A escala segue a ordem em que o guia monta o loop: comandos reais (cap. 17, passo 1), contexto permanente (cap. 4), contrato (cap. 9), enforcement (caps. 12 e 13) e, por último, review e aprendizado (caps. 14 e 2).

| Nível | Nome | Significa | Fase HG típica |
| --- | --- | --- | --- |
| P0 | Operável | dá para instalar, buildar e testar por comando; sem isso não existe sensor (cap. 13) | antes da fase 0 |
| P1 | Orientado | o agente sabe a stack, os comandos, os limites e onde ler o resto | 0 |
| P2 | Contratado | toda demanda vira spec com tasks, DoD e gate; há estado entre sessões | 0–2 |
| P3 | Verificado | as regras importantes têm enforcement; quem faz não julga | 1 |
| P4 | Revisado e aprendendo | review ancorado nos docs do projeto, retro, sensores contínuos | 2–3 |

**Regra de nível:** só checks **computacionais** (C) bloqueiam um nível. Checks **inferenciais** (I) geram achados com evidência e sugestão, mas não mudam o nível. É a postura do cap. 15: não deixar um juiz não determinístico decidir sozinho o que pode ser um script. Um nível passa quando **todos** os checks C aplicáveis passam. Os não aplicáveis (ex.: E2E num repo sem interface) são pulados e declarados no relatório. A escala é contígua, como nos modelos externos. O critério de 100% é viável porque cada nível tem poucos checks e cada um vem de uma regra explícita do guia.

#### Checks

| ID | Check | Tipo | Guia |
| --- | --- | --- | --- |
| **P0** | | | |
| R01 | existe um comando de teste que roda e sai com 0 | C | caps. 12, 17 |
| R02 | existe um comando de build ou typecheck que roda | C | Ap. A |
| R03 | dependências instaláveis por um comando, com lockfile | C | cap. 17 ("um comando inventado transforma a primeira execução numa investigação do ambiente") |
| R04 | `.gitignore` cobre artefatos e segredos; nenhum segredo óbvio versionado | C | cap. 6 (credenciais fora do repositório) |
| **P1** | | | |
| R10 | AGENTS.md (ou equivalente) existe, com menos de 150 linhas; alvo abaixo de 100 | C | cap. 4 |
| R11 | boundaries em três níveis no início do arquivo; cada "nunca" tem a alternativa | C (estrutura) + I (qualidade) | cap. 4 |
| R12 | todo comando citado existe no task runner, no manifesto ou no CI | C | cap. 17; Ap. A |
| R13 | todo ponteiro resolve para um arquivo e diz quando ler | C | cap. 4; Ap. A |
| R14 | sem árvore de pastas, sem frases vagas, sem instruções de uma task, sem cópia do README | C (heurística) + I | cap. 4 (tabela "fica de fora") |
| R15 | arquivos de instrução de ferramentas diferentes não se contradizem | I | seção 4.2 |
| R16 | doc de testes: tipos, como rodam, o que é seguro em paralelo | C (presença) + I | cap. 9 (mapeamento) |
| R17 | instrução de consultar documentação atualizada (Context7 ou equivalente) quando há dependências externas relevantes | C | cap. 4 |
| **P2** | | | |
| R20 | camada de spec escolhida e registrada em ADR | C | cap. 9 |
| R21 | tasks com o quê, onde e DoD com comando real (validador do framework ou do harness) | C | cap. 9; Ap. A |
| R22 | memória entre sessões (STATE.md ou equivalente do framework) existe e foi tocada na última task | C | caps. 9, 13 |
| R23 | `concerns.md` do mapeamento existe | C | cap. 9 |
| R24 | ciclo de vida das specs decidido (comitar, usar no review, arquivar ou manter viva) | C (decisão registrada) | cap. 9; D17 |
| R25 | a demanda chega por board via MCP + skill, ou pelo template de intake (6.3) | C | caps. 8, 16 |
| **P3** | | | |
| R30 | lint e formatter configurados e rodando | C | cap. 13 |
| R31 | typecheck onde a linguagem permite | C | cap. 13 |
| R32 | testes produzem relatório estruturado (JUnit) para contagem | C | cap. 12, princípio 7 |
| R33 | gate bloqueante ativo (Stop gate e `task done`) | C | cap. 12, princípio 3 |
| R34 | `git commit` e `git push` fora do alcance da IA no modo fix | C | cap. 14 |
| R35 | verifier separado, com contexto limpo e modelo pinado | C | caps. 13, 15 |
| R36 | requisitos de interface verificados no navegador por ferramenta que o agente aciona | C | caps. 13, 16 |
| R37 | isolamento dos testes conhecido (`parallelSafe` marcado) | I | cap. 12, princípio 8 |
| R38 | o CI roda os mesmos comandos do gate | C | seção 4.3 |
| R39 | papéis da fábrica com tier de modelo declarado; leitura em massa fora do tier `strong`; verifier pinado por ID completo e diferente do implementer | C | caps. 8, 11, 15; seção 16 |
| **P4** | | | |
| R40 | diretrizes de review escritas para a IA, ancoradas em docs do projeto | C (presença) + I | caps. 7, 14 (grounding) |
| R41 | template de PR liga o ID da spec ou do ticket | C | caps. 14, 16 |
| R42 | docs sob demanda dentro do limite de frescor (`verified`) | C | seção 7.2 |
| R43 | retro registrada nas últimas N tasks e AGENTS.md podado desde então | C | cap. 4 (armadilha do arquivo que só cresce) |
| R44 | skills ativas ≤ ~20; description com o quê, quando e sinônimos; corpo < ~500 linhas | C + I | cap. 5 |
| R45 | sensor contínuo de arquitetura (drift, ciclos, código morto) | C | cap. 13 (armadilha "medir só por sessão") |

**Diagnóstico de organização do código (fora da escala).** Pastas genéricas (`utils`, `common`, `misc`), camadas misturadas com domínios, nomes inconsistentes e duplicação espalhada (cap. 2) entram no relatório como achados e alimentam o `concerns.md`. O harness não reorganiza código; reorganizar é decisão do time via RFC ou ADR (seção 14).

**Informativos [Externo].** Devcontainer, `.env` de exemplo, CODEOWNERS, proteção de branch, secret scanning, logging estruturado, tracing, templates de issue. Aparecem numa tabela à parte, com a fonte (Factory, Larridin), sem afetar o nível.

#### Formato do check

Cada check é dado no catálogo (P3 do HG: lógica genérica, dados do projeto), não código espalhado:

```json
{
  "id": "R12",
  "level": "P1",
  "kind": "computational",
  "scope": "app",
  "check": "commands-cited-exist",
  "guide": ["cap. 17", "Ap. A"],
  "evidence": "lista de comandos citados × fontes onde foram encontrados",
  "fix": { "recipe": "agents-md-commands", "size": "quick" }
}
```

O relatório tem duas saídas: `reports/readiness.md`, para a pessoa, com o nível, os checks que falharam e as cinco ações de maior impacto, e `reports/readiness.json`, para máquina, anexado a `reports/readiness-history.jsonl` a cada execução, para mostrar a evolução.

### 15.3 Captura de padrões do projeto

#### Princípio

O cap. 2 manda, em legado, "primeiro mapeie o codebase como ele é, com os padrões que ele realmente tem". O cap. 4 proíbe gerar o AGENTS.md a partir do código. Essas duas regras não se contradizem se a captura produzir **candidatos com evidência**, e não texto pronto. A pessoa decide o que vira regra. **[Externo]** O estudo da ETH (seção 2) mostra por que: visão geral gerada não ajudou; o que ajuda é instrução não óbvia e operacional.

**[Externo]** Outros frameworks fazem captura parecida, com graus diferentes de geração:

| Framework | Mecanismo | Saída | Diferença para o harness |
| --- | --- | --- | --- |
| BMAD | `bmad-generate-project-context` escaneia stack, padrões, nomes e convenções de teste; `bmad-document-project` gera `index.md`, `architecture.md`, `source-tree-analysis.md` | `_bmad-output/project-context.md`, "enxuto e orientado a LLM"; a doc recomenda rodar de novo após refatorações grandes ou quando o output do agente se desvia do padrão do time | gera texto; `source-tree-analysis` é exatamente o que o cap. 4 manda deixar de fora |
| Kiro | "Generate Steering Docs" cria `product.md`, `tech.md`, `structure.md` em `.kiro/steering/`; modos de inclusão `always`, `fileMatch`, `manual`, `auto` | os três arquivos entram em toda interação por padrão | `structure.md` inclui organização de arquivos (contraria o cap. 4); os modos `fileMatch` e `auto` são uma boa forma de progressive disclosure |
| OpenSpec | campo `context` em `openspec/config.yaml`, texto livre com stack e convenções, injetado quando a IA escreve artefatos | um bloco de contexto | é um segundo lugar de contexto permanente, que pode duplicar o AGENTS.md (15.5) |
| Spec Kit | `/speckit-constitution`, uma vez por projeto | princípios não negociáveis | idem |

#### Fontes de evidência e o que cada uma captura

| Fonte | Captura | Destino provável | Guia |
| --- | --- | --- | --- |
| Configs de lint, formatter, typecheck, `.editorconfig` | convenções que **já têm sensor** | nenhum texto: o sensor já cobra; no máximo um ponteiro | cap. 12 (enforcement > instrução); P4 do HG |
| Manifestos, task runners, CI | comandos reais, versões | AGENTS.md (comandos) e perfil | cap. 4; seção 5.1 |
| Arquivos exemplares por tipo (controller, service, teste, migration, componente) | "como se faz aqui", com `arquivo:linha` | `docs/agents/code-patterns.md`, com exemplos de 3 a 10 linhas | cap. 2 ("o modelo copia o que vê"); cap. 4 |
| Testes, fixtures, setup de banco | tipos, runner, isolamento, o que paraleliza | `docs/agents/testing.md`; `parallelSafe` no perfil | cap. 9; cap. 12, princípios 8 e 10 |
| Grafo de imports | fronteiras entre módulos e direção das dependências | `architecture.md` em alto nível; sensor de drift na fase 3 | caps. 2, 13; cap. 18 (Coupling Analysis) |
| Identificadores, docs de produto, Design Docs | linguagem do domínio | `glossary.md` | cap. 2 (exemplo de rules com "Domínio"); cap. 18 (`/domain-modeling`) |
| SDKs e clientes HTTP | como o projeto integra com terceiros | `docs/agents/integration-patterns.md` + linha do Context7 | caps. 2, 4, 8 |
| Comandos de migration, seeds, scripts de dados | o que nunca fazer à mão e o que fazer no lugar | boundary com par "instead" | cap. 4 |
| Histórico do git | estilo de commit, nomes de branch, atomicidade | regra testável no AGENTS.md ou `commit-msg` hook | caps. 2, 9 |
| Comentários de review em PRs (via `gh` ou MCP, só leitura) | correções que o time repete | candidato a regra, exemplo, teste ou sensor | cap. 2 ("use os reviews de PR como aprendizado") |
| README, CONTRIBUTING, ADRs, wiki (via MCP) | o que já está escrito | ponteiro, nunca cópia | cap. 4 ("o que já está no README ou na wiki" fica de fora) |

#### Árvore de destino de um padrão

Aplicada a cada candidato, na ordem. É o critério do cap. 6 ("onde colocar algo novo") com o P4 do HG na frente:

1. Uma ferramenta consegue verificar? → **sensor** (lint, typecheck, teste, hook). Instrução sem enforcement não segura (cap. 12, princípio 3).
2. Vale para toda tarefa do projeto e cabe em uma ou duas linhas testáveis? → **AGENTS.md**.
3. Vale para um tipo de trabalho, com detalhe e exemplos? → **doc sob demanda** com ponteiro "fazendo X → leia Y".
4. É um procedimento com passos, talvez útil em outros repos, ou a seção passou de ~20 linhas? → **skill** (cap. 4).
5. Depende de sistema externo? → **MCP** + skill que ensina a usá-lo (cap. 6, armadilha).
6. O modelo já faz isso sem ajuda? → **nada**. O cap. 4 diz que os modelos atuais precisam de instrução só sobre o que é não óbvio.

#### Formato do candidato e revisão humana

A captura roda com sub-agents numa janela nova (cap. 9, mapeamento) e grava `reports/patterns.md`, um checklist para a pessoa marcar:

```markdown
- [ ] PAT-007 · Serviços recebem dependências pelo construtor
  - Evidência: 23 de 26 services (ex.: src/billing/payment.service.ts:12)
  - Contra-exemplos: 3, todos em src/legacy/ (ex.: src/legacy/order.js:40)
  - Confiança: alta · Destino proposto: doc sob demanda (code-patterns.md)
  - Pergunta: o padrão de src/legacy/ deve ser seguido ou evitado?
```

Regras:

- **Sem evidência, sem candidato.** Cada candidato cita arquivo e linha; o que não tem prova sai como `INCERTO` (cadeia de conhecimento do cap. 9).
- **Contra-exemplos aparecem sempre.** Em legado convivem padrões diferentes (cap. 4: AGENTS.md por diretório). A pessoa escolhe qual é o canônico; o outro vira "legado: não copiar" ou uma regra aninhada.
- **A pessoa marca; o harness aplica.** Os itens marcados viram diffs (15.4) ou demandas (15.7). Nada é escrito antes da marcação.

### 15.4 Documentação: avaliar, melhorar ou criar

#### Decisão por artefato

| Estado encontrado | Ação | Exemplo |
| --- | --- | --- |
| existe e passa nos checks | apontar; não tocar | ADRs do time viram ponteiro na árvore "leia quando" |
| existe e falha em checks | **diff de poda** proposto, com o check que motivou cada linha removida | AGENTS.md de 320 linhas: mover a seção de testes para `testing.md`, remover a árvore de pastas |
| existe em lugar que a IA não alcança (Notion, Confluence) | MCP + ponteiro, não cópia | PRD no Notion (caps. 6, 7) |
| não existe e é necessário para o nível alvo | esqueleto com TODO ou rascunho com evidência (7.3) | `testing.md` escrito a partir do que o agente executou |
| não existe e não é necessário | não criar | Design Doc num projeto solo (cap. 7) |

O cap. 4 dá a direção da melhoria: "o jeito mais rápido de melhorar um AGENTS.md costuma ser deletar". O diagnóstico propõe primeiro o que sai, depois o que entra.

#### Linter de AGENTS.md

O checklist do Ap. A e a tabela "entra / fica de fora" do cap. 4 viram um linter com duas metades:

- **Computacional** (`bootstrap.py assess`, parte do `doctor`): contagem de linhas; boundaries no topo; cada linha "nunca" seguida de alternativa; comandos citados existem (R12); ponteiros resolvem (R13); padrões de árvore de pastas (linhas com `├──`, listas de paths); lista de frases vagas ("código limpo", "boas práticas", "mantenha a qualidade"); linhas duplicadas entre AGENTS.md, CLAUDE.md, rules e arquivos de framework (15.5).
- **Inferencial** (skill de preparação, janela nova): a regra é testável? É não óbvia? É de uma task específica? Sai como achado com sugestão, nunca como edição.

#### Conjunto de documentos por tamanho de time

O questionário inicial (15.7) pergunta o tamanho do time e aplica a tabela do cap. 7:

| Situação | Documentos que a preparação sugere |
| --- | --- |
| solo | spec por demanda; ADR quando houver decisão. "Na maioria das vezes, a spec basta" |
| time pequeno | spec + ADR; Design Doc para projetos de várias semanas |
| time médio ou grande | PRD (se houver PM), Design Doc, RFC para decisões de grande impacto, ADR |
| projeto novo, porte médio, muita incerteza | Lean Inception antes de tudo |

#### Templates que a preparação oferece

| Template | Onde | Fonte |
| --- | --- | --- |
| ADR | `docs/decisions/0000-template.md` | cap. 7. **[Externo]** MADR 4.0.0 é uma opção madura, com arquivos `NNNN-titulo.md`; adotar sem fork mantém o upstream |
| Design Doc | gerado sob pedido pela skill Technical Design Doc Creator | cap. 7 |
| RFC | `docs/decisions/rfc-template.md` | caps. 7, 18 (Design It Twice termina num RFC) |
| Intake | `.harness/intake/_template.md` | seção 6.3 |
| Diretrizes de review | `docs/agents/review/<especialista>.md` (segurança, arquitetura, requisitos, testes, regressão e alucinação, performance) | cap. 14: grounding antes do diff; "os docs do seu projeto são a lei" |
| Template de PR | `.github/pull_request_template.md` com campo de ID da spec ou do ticket | caps. 14, 16 (rastreabilidade) |
| Task com DoD, SKILL.md | já previstos (HG G9) | Ap. A |

As diretrizes de review merecem destaque: o cap. 14 diz que o agente de arquitetura carrega 7 ou mais docs do projeto antes do diff. Se esses docs não existem, o review sai genérico. A preparação as cria **a partir dos padrões aceitos em 15.3**, e não do conhecimento geral do modelo.

### 15.5 Camada de spec plugável: o dev escolhe, o harness implementa

O HG já decidiu que a camada de spec é plugável (D3), e a seção 4.2 trata o caso N3 (framework já instalado). Falta o caso em que o repo **não tem** framework e o dev quer escolher um. O guia dá o critério: escolher pelos gates e pelo uso da janela, não pelo nome (cap. 9). O harness deve ajudar nas três etapas: escolher, instalar e ligar à fábrica.

#### As opções **[Externo, consultado em 25/10/2026; versões mudam rápido]**

| Framework | Instalação | Runtime | Escreve | Fluxo | Validação nativa |
| --- | --- | --- | --- | --- | --- |
| **Nativo do harness** (`harness-spec`, HG G5) | vem com o harness | Python stdlib | `.harness/work/<ID>/` | Specify, Design, Tasks, Execute com auto-sizing | validador estrutural do harness (G5) |
| **TLC Spec-Driven** | `npx @tech-leads-club/agent-skills install --skill tlc-spec-driven` (ou ZIP) | Node para o instalador; scripts em Python | `.specs/STATE.md`, `LESSONS.md`, `lessons.json`, `features/<f>/{spec,context,design,tasks,validation}.md`, criados sob demanda | Specify (EARS) e Execute sempre; Design e Tasks por escopo (Small, Medium, Large, Complex); um commit convencional por task; verifier ao final | `validate_spec.py`, `validate_tasks.py` (exige campos Tests e Gate por task), `check_commit.py`, `validate_state.py` (PASS com evidência) |
| **OpenSpec** | binário standalone (`install.sh` / `install.ps1`), `brew install openspec` ou `npm install -g @fission-ai/openspec` | **nenhum** no binário standalone; Node ≥ 20.19 via npm | `openspec/{config.yaml,specs/,changes/,changes/archive/}` + skills e comandos por ferramenta (`.claude/skills/openspec-*`, `.claude/commands/opsx/`, `.agents/skills/`) | `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`; perfil expandido com `/opsx:verify` | `openspec validate --all --strict --json`; `openspec status --json` |
| **Spec Kit** | `uv tool install specify-cli` → `specify init --integration <agente>` | Python 3.11+ e uv | `.specify/` (constituição, templates, scripts; caminho exato a conferir) + comandos por agente | `/speckit-constitution`, `-specify`, `-clarify`, `-plan`, `-checklist`, `-tasks`, `-analyze`, `-implement`, `-converge` | `/speckit-analyze` e checklists (inferenciais); extensões podem acrescentar gates e hooks |
| **Superpowers** | `/plugin marketplace add obra/superpowers-marketplace` → `/plugin install superpowers@superpowers-marketplace` | — (plugin do Claude Code; o guia cita Cursor e Claude Code) | skills (brainstorming, writing-plans, TDD, verification-before-completion etc.) | brainstorm → plano → implementação com TDD e review | review de qualidade após cada task (cap. 9) |
| **Kiro** | IDE / CLI próprios | — | `.kiro/specs/<f>/{requirements,design,tasks}.md` + `.kiro/steering/` | requisitos em EARS → design → tasks | da ferramenta |
| **BMAD** | `npx bmad-method install` | Node e Python + uv | `_bmad-output/` e diretórios do método | papéis (analista, PM, arquiteto, dev) | da ferramenta |

O guia compara três deles no mesmo projeto (cap. 9): Superpowers implementa tudo na mesma janela (chegou a 70%) e paraleliza mal; TLC é feito para sub-agents genéricos e janela principal baixa, com gates explícitos na DoD; OpenSpec é leve, iterativo, o mais universal, pensado para brownfield, e exige uma CLI Node. **[Externo]** Esta última desvantagem diminuiu: o OpenSpec passou a oferecer binário standalone sem Node, o que conversa com a restrição R2 desta pesquisa. **Divergência a registrar:** o guia descreve o `concerns.md` como saída do mapeamento do TLC (cap. 9), mas a página atual da skill não menciona esse arquivo; o harness mantém o `concerns.md` próprio (6.2).

#### Escolher: perguntas com recomendação

| Pergunta | Se a resposta for… | Tende a |
| --- | --- | --- |
| Já existe framework no repo? | sim | **manter e plugar** (N3, D18); nunca migrar sem pedido |
| Quer specs que descrevem o sistema atual e crescem a cada mudança? | sim | OpenSpec (specs vivas com deltas); aceitar o custo de manutenção (D17) |
| Quer o fluxo mais próximo do guia, com gates na DoD, STATE e verifier? | sim | TLC Spec-Driven ou o nativo |
| Pode adicionar Node ou Python+uv ao ambiente dos devs? | não | nativo ou OpenSpec standalone |
| Usa mais de uma ferramenta de IA no time? | sim | OpenSpec (40+ ferramentas em `--tools`) ou TLC (agnóstico); evitar o que só roda numa |
| Time grande, com papéis de produto e arquitetura formais? | sim | Spec Kit ou BMAD podem caber; conferir uso da janela e gates antes |
| Quer o mínimo de arquivos novos? | sim | nativo |

O resultado é uma recomendação com motivo, que a pessoa aceita ou troca. A escolha vira **ADR 0001** ("Adotar X como camada de spec"), com as respostas acima como contexto.

#### Instalar e ligar: o que o harness faz em cada caso

O harness não reescreve o framework. Ele faz cinco coisas, as mesmas para qualquer escolha:

1. **Instalação assistida.** Mostra o comando oficial, confere o runtime, pede aprovação (seção 11: instalar executa código de terceiros) e roda em modo não interativo quando o framework permite (ex.: `openspec init --tools claude,cursor`). Registra versão e origem no `inventory.json`; o `harness.lock` continua guardando só o que o harness vendorizou.
2. **Fonte única de contexto.** Framework que tem contexto permanente próprio (`config.yaml#context`, constituição, steering) recebe um texto curto que **aponta** para o AGENTS.md e para `docs/agents/`, com só o que for específico do framework. O linter (15.4) acusa linhas duplicadas entre eles (D25). Sem isso o repo ganha dois AGENTS.md que envelhecem separados.
3. **Contrato de task com gate.** Onde o framework não exige DoD com comando, o harness injeta a regra pelo mecanismo de configuração do próprio framework (ex.: `rules` por artefato no `config.yaml` do OpenSpec; constituição ou extensão no Spec Kit; a TLC já exige Tests e Gate). A regra cita os comandos reais do perfil.
4. **Adaptador de leitura** (o mesmo da seção 4.2, N3). Traduz o artefato do framework para o contrato do harness: tasks → `tasks.json`; critérios → checks binários do verifier; ID → rastreabilidade (P13).
5. **Primeiro loop no framework escolhido.** Uma mudança pequena passa pelo validador nativo, pelo gate e pelo verifier do harness (passo 7 da seção 9). Só então a escolha conta como implementada (R20 e R21 verdes).

| Framework | Fonte de tasks | Fonte de critérios | Validador a encadear | Lacuna que o harness cobre |
| --- | --- | --- | --- | --- |
| Nativo | `work/<ID>/tasks.md` | WHEN/THEN/SHALL da spec | validador G5 | — |
| TLC | `.specs/features/<f>/tasks.md` | critérios EARS da `spec.md` | `validate_spec.py`, `validate_tasks.py`, `validate_state.py` | Stop gate, test guard e boundary guard (enforcement fora da conversa); a TLC já tem verifier e `validation.md`, que o harness reaproveita em vez de duplicar |
| OpenSpec | `openspec/changes/<c>/tasks.md` | `### Requirement` / `#### Scenario` (WHEN/THEN) da change | `openspec validate <c> --strict --json` | DoD com comando por task; verifier com modelo pinado; STATE.md; `archive --yes` só depois do gate |
| Spec Kit | `tasks.md` da feature ativa (`.specify/feature.json` aponta o diretório) | `spec.md` e checklists | `/speckit-analyze` é inferencial: o harness acrescenta o gate computacional | gate computacional; verifier separado; contagem de testes |
| Superpowers | plano gerado pela skill writing-plans | o próprio plano | — | execução por sub-agents (janela principal), STATE.md, verifier separado |
| Kiro, BMAD | `tasks.md` do framework | requisitos EARS / histórias | da ferramenta | coexistência primeiro; adaptador só depois de um piloto (D24) |

Detalhes que precisam de conferência no Plan: os cabeçalhos de delta do OpenSpec (a página consultada só mostra `## ADDED Requirements`; `MODIFIED`, `REMOVED` e `RENAMED` são citados por fontes secundárias), o caminho da constituição e das features no Spec Kit e o formato do plano do Superpowers.

Duas regras transversais:

- **Um framework por vez.** Dois contratos de spec ativos no mesmo repo dobram o contexto e confundem o agente sobre qual seguir.
- **Orçamento de skills.** O OpenSpec instala 6 skills e 6 comandos no Claude Code no perfil padrão; o Superpowers traz um pacote inteiro. O relatório mostra o efeito no teto de ~20 skills (cap. 5) antes de instalar, e sugere o perfil mínimo (ex.: `openspec init --profile core`).

### 15.6 Skills, MCPs e sensores sugeridos a partir da avaliação e da captura

A seção 10 sugere a partir do inventário. A preparação acrescenta dois sinais: os **checks que falharam** (15.2) e os **padrões aceitos** (15.3). Linhas novas para o catálogo:

| Sinal | Sugestão | Camada | Guia |
| --- | --- | --- | --- |
| padrão aceito com procedimento de vários passos (criar módulo, novo endpoint, migration) | **skill do projeto**, escrita com skill-architect ou skill-creator; description testada com pedidos reais do time | skill | cap. 5 (armadilha "a skill que nunca dispara") |
| conhecimento de domínio recorrente em várias demandas | **skill de domínio** mantida para o projeto inteiro | skill | cap. 16 (caso Frances Thai: issue + documento guarda-chuva + skill de domínio) |
| regras de segurança, arquitetura ou padrões cobradas só no review | skills **shift-left**, carregadas enquanto o agente escreve | skill | cap. 12 (shift-left) |
| tasks com dúvida frequente sobre o que paraleliza | skill que analisa tasks e aponta paralelismo | skill | cap. 12 (sugestão da aula) |
| board identificado (R25 falhou) | MCP do board + skill no padrão do time (Jira Assistant ou equivalente) | MCP + skill | caps. 6, 8 |
| PRD ou Design Doc fora do repo | MCP de leitura do Notion ou Confluence | MCP | cap. 7 |
| R36 falhou e há UI web | Playwright MCP | MCP | caps. 13, 16 |
| R30 ou R31 falharam | linter, formatter ou typecheck da stack, mais o hook pós-edição (HG S6) | sensor | cap. 13 |
| R32 falhou | reporter JUnit da stack (tabela 5.2) | sensor | cap. 12 |
| comentário de review repetido em vários PRs (15.3) | regra de lint ou teste quando der; regra no AGENTS.md só quando nenhuma ferramenta verificar | sensor ou guide | caps. 2, 12 |
| projeto novo, Design Doc pedido | Technical Design Doc Creator | skill | cap. 7 |
| decisão de arquitetura em aberto | `/domain-modeling` + `/code-design` → RFC | skill | cap. 18 |
| codebase grande ou desconhecido | CodeNavi, Domain Analysis, Coupling Analysis, conforme a pergunta | skill | cap. 18 |
| migração de arquitetura no roadmap | Legacy Migration Planner, só com objetivo e restrições já claros | skill | cap. 18 (armadilha) |

**Fontes e confiança [Externo].** O marketplace da TLC instala por CLI (`npx @tech-leads-club/agent-skills`, com `install -s`, `update`, `remove`, `audit`), usa lockfile e hash de conteúdo, oferece cópia ou symlink e diz que as skills passam por varredura (Snyk Agent Scan) antes da publicação. O Spec Kit avisa que listagens de catálogo não são auditoria. A spec aberta de skills (agentskills.io) define o formato (`SKILL.md` com `name` e `description`, pastas opcionais) e aponta uma biblioteca de validação de frontmatter. O catálogo do harness registra a fonte e o nível de confiança de cada item (seção 10.1), e o padrão continua sendo **sugerir, nunca instalar sem aceite**.

### 15.7 O fluxo de ponta a ponta para o dev

O objetivo é que o trabalho do dev seja **decidir, não escrever**: responder poucas perguntas, aprovar comandos, marcar checkboxes e revisar diffs.

```
 dev: "prepare este repo"      (BOOTSTRAP.md → agente) ou  python3 bootstrap.py prepare
   │
   ▼
 1. AVALIAR ─────────── somente leitura · readiness.md/json · nível P0–P4 · top 5 ações
   │
   ▼
 2. PERGUNTAR ───────── ≤ 7 perguntas com padrão sugerido
   │                    ferramentas de IA · tamanho do time · board · framework de spec
   │                    · nível alvo · comandos aprovados para execução
   ▼
 3. APLICAR O BÁSICO ── determinístico (seção 9, passos 2–4): estrutura, blocos, perfil
   │
   ▼
 4. CAPTURAR ────────── janela nova, sub-agents · patterns.md com evidência
   │                    dev marca [x] o que vale
   ▼
 5. BACKLOG DE PREPARAÇÃO ── READY-001..N em .harness/intake/, ordenado por nível
   │                    (P0 antes de P1...), cada um com check de origem e tamanho
   ▼
 6. EXECUTAR NA FÁBRICA ─── cada READY passa pelas estações (seção 6), quase sempre
   │                    em Quick Mode: spec curta → execute → gate → verifier → dev revisa → commit
   │                    ex.: READY-003 "adotar OpenSpec" = 15.5 inteiro
   ▼
 7. REAVALIAR ───────── delta de nível e de checks em readiness-history.jsonl
   │
   ▼
 8. MANTER ──────────── doctor no CI (frescor, tamanho, ponteiros) · retro a cada N tasks
                        · nova avaliação após refatoração grande ou quando o output desviar
```

Propriedades do fluxo:

- **A primeira demanda de preparação é o primeiro loop.** O critério de aceite do bootstrap (seção 9, passo 7) é atendido por um READY real, como "fazer os testes emitirem JUnit" ou "escrever `testing.md` a partir do que foi executado". Não existe uma fase de "deixar tudo pronto" antes de trabalhar (cap. 17).
- **Ordem por nível, não por vontade.** Não adianta adotar um framework de spec (P2) se o comando de teste não roda (P0): o gate da DoD não teria o que executar.
- **Cada item é pequeno e reversível.** Um READY, um commit atômico (cap. 9). Desfazer uma escolha é reverter um commit.
- **Paradas legítimas.** Um READY pode terminar como blocker registrado (ex.: "o CI depende de segredo que o agente não tem"). O cap. 17 diz que um impedimento registrado é resultado legítimo.
- **Sem sessão gigante.** Avaliar, capturar e executar acontecem em janelas separadas, com estado em disco (RPI, cap. 9; zonas do cap. 3).
- **Reavaliar quando o output desviar.** **[Externo]** O BMAD recomenda regenerar o contexto do projeto depois de refatorações grandes ou quando o output do agente se afasta do padrão do time. No harness, o gatilho é a retro ou o `doctor`, e a ação é reavaliar e capturar de novo, não regenerar texto.

#### Quem executa cada passo: orquestrador fino, sub-agents e janelas novas

> Acrescentado em 25/10/2026, em resposta à pergunta: "o fluxo de ponta a ponta já é conduzido por um orquestrador que chama sub-agents, para não pôr uma tarefa grande num agente só?"

**Resposta curta: ainda não estava explícito.** O fluxo acima diz que avaliar, capturar e executar acontecem em janelas separadas e que a captura usa sub-agents, e a estação Execute já tem orquestração por fases (G4, cap. 11). Mas o texto não dizia **quem executa cada passo**. Nada impedia o dev de pedir "prepare este repo" e o agente fazer os oito passos na mesma janela: ler o código para capturar padrões, escrever docs, implementar os READY e reavaliar. Seria a sessão que o cap. 3 põe na Dumb Zone e que o benchmark do cap. 11 mostra estourando (agente único em 74% da janela ao fim de 18 tasks, sem folga para uma correção).

O guia dá a direção, com uma ressalva que também vale aqui: **sub-agent é gestão de orçamento de contexto, não técnica de qualidade** (cap. 11, TL;DR). Fragmentar demais custa mais caro e piora a nota (um sub-agent por task: 25M de tokens e nota 0,81, contra 10,5M e 0,95 com 3 workers por blocos). A meta é não deixar o trabalho grande numa janela só **e** não pulverizá-lo.

**Três tipos de executor, escolhidos nesta ordem:**

1. **Script**, quando o passo é determinístico (P8). Custo de modelo zero, resultado reproduzível.
2. **Sub-agent**, quando o passo é leitura ou escrita que cabe numa janela e devolve um resultado curto. O modelo do sub-agent sai do papel dele (seção 16).
3. **Janela nova** (sessão nova), quando há um ponto humano no meio ou quando o trabalho seguinte não precisa de nada da conversa anterior além do que está em disco. É o RPI do cap. 9 aplicado à preparação.

**O orquestrador** é a skill `harness-prepare`, na janela principal. Ele **não lê código-fonte nem escreve documentação**. Lê o estado em disco, decide o próximo passo, dispara o executor, recebe um resumo curto com caminhos de arquivo e para nos pontos humanos. É a recomendação do cap. 11 ("peça explicitamente ao orquestrador para delegar e manter a própria janela baixa") transformada em regra da skill, em vez de depender do pedido do dev.

| Passo | Executor | Papel e tier (seção 16) | Paralelo? | Grava em disco | Volta para o orquestrador |
| --- | --- | --- | --- | --- | --- |
| 1. Avaliar | `bootstrap.py assess` para os checks C; sub-agents para os checks I | script; `auditor` (standard, só leitura) apoiado por `explorer` (fast) | sim: um sub-agent por grupo de checks inferenciais (leitura de baixo acoplamento) | `reports/readiness.{json,md}` | nível, número de checks falhando, top 5 ações |
| 2. Perguntar | o próprio orquestrador | orquestrador | — | respostas no `profile.json` (`confirmed`) | — |
| 3. Aplicar o básico | `bootstrap.py apply` | script | — | estrutura, blocos, adaptadores, arquivos de sub-agent (16.7) | exit code e lista de arquivos |
| 4. Capturar | um `explorer` por fonte de evidência da 15.3; depois um `synthesizer` | `explorer` (fast) × N; `synthesizer` (strong) × 1 | sim nos explorers (fontes independentes); não no synthesizer, que precisa de tudo para achar contra-exemplos | `reports/patterns/raw-<fonte>.md` → `reports/patterns.md` | "PAT-001..023 · 4 INCERTO · ver patterns.md" |
| ⏸ ponto humano | dev marca `patterns.md` | — | — | marcações | **fim da sessão** |
| 5. Backlog | `bootstrap.py backlog` a partir das receitas `fix.recipe` dos checks; padrões marcados viram READY | script + orquestrador (só ordena e nomeia) | — | `intake/READY-NNN.md` | lista ordenada por nível |
| 6. Executar | cada READY, ou bloco coeso de READYs pequenos, entra pela estação Spec numa **janela nova** e segue as estações da seção 6 com a `harness-execute` | `planner` (strong) só fora do Quick Mode; `implementer` (standard) ou `mechanical` (fast) para tarefa mecânica; `verifier` (strong, pinado); `reviewer` (standard) e `security` (strong) | blocos independentes e `parallelSafe` em paralelo, até 3 workers; o resto em sequência (cap. 11) | `work/<ID>/`, `validation.md`, `STATE.md` | gate verde ou vermelho, blocker registrado |
| ⏸ ponto humano | dev revisa o diff e commita | — | — | commit | fim da sessão do READY |
| 7. Reavaliar | `bootstrap.py assess` | script | — | `readiness-history.jsonl` | delta de nível e de checks |
| 8. Manter | `doctor` no CI; retro a cada N tasks | script; `retro` (standard) | — | relatório do doctor; diffs de poda | achados |

Dos oito passos, quatro são scripts e não gastam modelo. Os que leem muito (1 e 4) usam o tier mais barato em paralelo. O modelo forte aparece onde um erro se multiplica: síntese dos padrões, spec, verificação e segurança.

**Regras do orquestrador:**

- **Orçamento da própria janela.** Alvo abaixo de 40% (`limits.contextTarget`, HG §3.1). Ao passar disso, grava o handoff no `STATE.md` e encerra; a próxima sessão retoma pelo bootstrap de sessão (M1–M3). Acompanhar a janela principal é "a métrica do capítulo" (cap. 11).
- **Resultado por referência, não por cópia.** O sub-agent grava o resultado em arquivo e devolve no máximo ~20 linhas: o que fez, onde gravou, o que ficou `INCERTO`. **[Externo]** É a técnica que a Anthropic usa contra o "telefone sem fio" no sistema de pesquisa multi-agente: os sub-agents gravam a saída fora da conversa e passam referências leves ao coordenador. A documentação do Claude Code dá o motivo: "running many subagents that each return detailed results can consume significant context".
- **Profundidade máxima 2** (orquestrador → worker). Workers não disparam sub-agents: `Agent` vai em `disallowedTools` no Claude Code. **[Externo]** O Claude Code permite até três níveis abaixo da conversa principal; o Cursor só deixa o agente principal e os filhos diretos dispararem. Ficar no menor denominador mantém o comportamento igual entre ferramentas e evita a fragmentação que o cap. 11 desaconselha.
- **Fan-out só onde o acoplamento é baixo.** Leitura e varredura (passos 1 e 4) vão em paralelo, com vários sub-agents baratos e teto de leitores (`limits.maxReaders`, 16.7). Escrita de código (passo 6) segue a árvore do cap. 11: um agente por padrão, ~3 workers por blocos de fases, nunca um por task. READYs pequenos do mesmo tema (ex.: três ajustes no AGENTS.md) vão juntos para um worker.
- **Ponto humano encerra a sessão.** Depois de marcar padrões ou revisar um diff, o trabalho seguinte começa numa janela nova que lê o disco. A conversa anterior não carrega nada que o disco não tenha. Isso também é o ponto natural para trocar de modelo sem perder cache (16.6).
- **Não dividir o que cabe.** Um READY de Quick Mode (≤ 3 arquivos, sem decisão de design) roda num worker só, sem planner separado. Usar sub-agents "para melhorar a qualidade" de algo que já cabe numa janela é EVITE no cap. 11.
- **Trocar de modelo não é a primeira reação.** Quando um worker esgota `maxFixIterations`, o orquestrador primeiro confere o contexto que o worker recebeu (task sem DoD clara? doc sob demanda faltando?). Só então pode redisparar uma vez com o tier acima (`fallbackTier`, 16.7) e, se falhar de novo, escalar para o humano. O cap. 10 lista "trocar de modelo como primeira reação a um resultado ruim" como EVITE: "na maioria das vezes, o problema está no contexto".

O mesmo desenho vale fora da preparação. A estação Execute já funciona assim (HG §6, passo 3). A seção 16 dá a cada papel citado na tabela um modelo, um esforço e um conjunto de ferramentas.

#### O que o dev vê no fim

`reports/readiness.md` com o antes e o depois, por exemplo:

```
Nível: P1 → P2   (alvo: P3)
Falhando: R30 lint sem config · R32 sem JUnit · R36 UI sem E2E
Próximas ações: READY-007 (R32, quick) · READY-008 (R30, quick) · READY-009 (R36, medium)
Informativos: sem CODEOWNERS · sem devcontainer
```

### 15.8 Artefatos novos e acréscimos ao layout (6.2)

| Artefato | Onde | Regenerável? |
| --- | --- | --- |
| scorecard | `.harness/reports/readiness.{md,json}` + `readiness-history.jsonl` | sim (o histórico é anexado) |
| candidatos a padrão | `.harness/reports/patterns.md` | sim, mas as marcações da pessoa são preservadas |
| backlog de preparação | `.harness/intake/READY-NNN.md` | não (é demanda) |
| docs de padrões | `docs/agents/code-patterns.md`, `integration-patterns.md` | não (doc do projeto) |
| diretrizes de review | `docs/agents/review/*.md` | não |
| decisão da camada de spec | `docs/decisions/0001-camada-de-spec.md` | não |
| configuração da camada de spec | bloco `spec` no `profile.json`: `framework`, `version`, `taskSource`, `criteriaSource`, `validator`, `idPattern` | não (confirmado pela pessoa) |
| estado do fluxo de preparação | `STATE.md` (passo atual, próximo executor, último ponto humano) | não |
| saídas brutas da captura | `.harness/reports/patterns/raw-<fonte>.md` | sim |
| roster de papéis e modelos | bloco `models` + `roles` no `profile.json`; `reports/agents.md` (16.7) | o roster não (confirmado); o relatório sim |
| no generic-harness | `core/catalog/readiness/*.json` (checks), `core/catalog/patterns/*.json` (detectores de padrão por ecossistema), `core/spec-adapters/<framework>/` (mapeamento + fixture de contrato) | — |

### 15.9 Riscos específicos da preparação

| Risco | Mitigação |
| --- | --- |
| A nota vira meta (efeito Goodhart): o time cria arquivos para subir o nível | checks medem propriedades, não presença (15.2); só checks computacionais mudam nível; a nota compara o repo com ele mesmo |
| A captura transforma anti-padrão de legado em regra | contra-exemplos sempre visíveis; a pessoa escolhe o canônico; padrão minoritário nunca vira regra sem marcação |
| Contexto duplicado entre AGENTS.md, constituição, `config.yaml#context` e steering | fonte única + ponteiros; linter acusa duplicação (D25) |
| O framework de spec muda de versão e quebra o adaptador | versão registrada no inventário; fixture de contrato por adaptador; `doctor` avisa versão fora da faixa testada |
| Instalar framework adiciona runtime e skills | mostrar runtime e efeito no orçamento antes; preferir opções sem runtime extra (nativo, binário standalone); aprovação explícita |
| Correção automática gera documentação genérica (o equivalente a `/init`) | a preparação propõe diffs com evidência; a pessoa aplica; nenhum commit sem revisão (caps. 4, 14) |
| Ler PRs e board exige credenciais | MCP com autenticação do protocolo, escopo de leitura (caps. 6, 16) |
| Preparar vira projeto infinito | nível alvo escolhido no passo 2; backlog ordenado; o resto fica como sugestão |
| Pilares externos (observabilidade, segurança de branch) parecem obrigatórios | ficam na tabela informativa, sem afetar o nível (D27) |

---

## 16. Agentes e modelos por papel: identificar, registrar e economizar

> Seção acrescentada em 25/10/2026. Continua sendo Research: nada aqui foi implementado. Preços, nomes de modelo e campos de configuração mudam a cada release; tudo o que é **[Externo]** fica em dado versionado (catálogo), nunca em código.

### 16.1 O que o pedido acrescenta

1. O harness precisa **saber quais agentes existem** no ambiente do dev (ferramentas, provedor, modelos liberados, sub-agents que o time já escreveu) e **indicar qual usar** em cada situação da fábrica.
2. Essa escolha precisa ficar **registrada no repositório hospedeiro**, legível pelo dev e aplicada pelas ferramentas.
3. O critério é **eficiência máxima com economia**: modelo potente onde o raciocínio paga (ex.: pesquisa), modelo mais barato onde o trabalho é execução de um plano (ex.: implementação), e assim por diante em cada estação.

### 16.2 O que o guia já decide

| Regra | Guia |
| --- | --- |
| "Planeje com um modelo mais capaz (por exemplo, o Opus)", salve o plano e implemente numa janela nova com um modelo mais barato. "Usar o modelo mais caro para tudo" é EVITE | cap. 8 |
| Research com "um modelo bom, numa janela grande", que "pode orquestrar sub-agents para pesquisar frentes diferentes sem encher a janela principal"; Implement com janela nova, modelo mais barato e só o plano | cap. 9 |
| Custo medido: com TLC e Superpowers, ~US$ 10 por integração; com Opus planejando e Sonnet ou Composer implementando, ~US$ 5 | cap. 9 |
| Sub-agent é gestão de contexto; ~3 workers por blocos; nunca um por task; medir o acoplamento antes | cap. 11 |
| No caso Stripe, a janela principal (modelo mais barato que o do plano) só delegou e ficou em no máximo 37% | cap. 11 |
| Os seis especialistas de review "rodam com Sonnet"; um consolidador agrupa e deduplica | cap. 14 |
| Juiz em sub-agent com modelo fixo e contexto isolado; quem faz não julga | caps. 13, 15 |
| Não trocar de modelo como primeira reação a um resultado ruim | cap. 10 |
| A ferramenta deve permitir escolher modelo e nível de esforço (thinking) | cap. 6 |

O guia **não** trata: um tier abaixo do "barato" para leitura em massa, o modelo do revisor de segurança, o modelo dos sub-agents de exploração, esforço por papel, nem como registrar isso de forma portável. O restante desta seção é extensão, marcada como tal.

### 16.3 Modelos, preços e o que a Anthropic mede **[Externo, consultado em 25/10/2026]**

| Modelo | ID | Alias no Claude Code (API Anthropic) | Janela | Entrada US$/MTok | Saída US$/MTok | Leitura de cache | Posição na doc da Anthropic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fable 5.1 | `claude-fable-5-1` | `fable` (e `best`) | 1M | 10,00 | 50,00 | 0,25 | "the highest available capability": sessões de horas, pesquisa profunda de vários passos |
| Opus 5.5 | `claude-opus-5-5` | `opus` | 1M | 4,00 | 20,00 | 0,20 | "complex agentic coding": agentes autônomos de várias horas, refatoração grande, engenharia de sistemas |
| Sonnet 5.5 | `claude-sonnet-5-5` | `sonnet` | 1M | 2,00 | 10,00 | 0,20 | "everyday coding": geração de código, análise, tool use agêntico |
| Haiku 5.5 | `claude-haiku-5-5` | `haiku` | 1M | 0,10 (prompt ≤ 100K; 0,50 acima) | 0,50 (2,50 acima) | não conferido | "lowest latency and price": alto volume, "subagent tasks" |

**Proporções que orientam o desenho:**

- Opus custa **2×** o Sonnet. Sonnet custa **20×** o Haiku (prompts até 100K). Opus custa **40×** o Haiku. Fable custa **2,5×** o Opus.
- **[Inferência]** O maior ganho de economia não está em trocar Opus por Sonnet (2×), e sim em **tirar a leitura em massa do modelo forte** (20× a 40×). A regra do cap. 8 (Opus planeja, Sonnet implementa) continua valendo e é a economia que o guia mediu (~50%). A divisão em dois tiers do HG (`strong`/`cheap`) esconde a segunda economia, e por isso esta pesquisa propõe quatro (D29).

**O que a Anthropic diz sobre escolher e combinar modelos:**

- "Most workloads start with Claude Opus 5.5." Dois caminhos: começar pelo eficiente (Haiku) e subir só se faltar capacidade, ou começar pelo capaz (Opus) e descer depois.
- "Tuning effort is often a better lever than switching models." O esforço (`low`…`max`) troca profundidade por custo dentro do mesmo modelo. O padrão é `medium` no Opus 5.5 e no Haiku 5.5; no Sonnet 5.5, `high` na API e `medium` no Claude Code.
- **Orquestrador com workers baratos**: economizou em trabalho rotineiro com cauda longa de custo e em trabalho maior que uma janela (busca de defeitos: cerca de metade do custo do Fable sozinho, nota 10 a 12 pontos menor). **Não ajudou** quando o trabalho é "one dependent chain" ou cabe numa janela: aí o modelo do orquestrador sozinho, com esforço menor, saiu melhor em todos os casos medidos. É a mesma conclusão do cap. 11.
- **Executor com advisor** (o modelo menor consulta um maior nos pontos difíceis): Opus 5.5 com advisor Fable 5.1 subiu 1,7 ponto num benchmark interno de código, "at the edge of run-to-run noise", a ~2,1× o custo. Não justifica ligar o tier `frontier` por padrão (D32).
- "Price per completed task, not per token": uma task que falha cobra os tokens e depois o retry.
- Sistema de pesquisa multi-agente: líder Opus 4 com sub-agents Sonnet 4 superou o Opus 4 sozinho em 90,2% numa avaliação interna de **pesquisa**; agentes gastam ~4× os tokens de um chat e sistemas multi-agente ~15×. A própria Anthropic diz que a maioria das tarefas de código tem poucas partes paralelizáveis (o guia cita isso no cap. 10).

**Divergência a registrar.** O guia manda separar modelos por fase. A Anthropic recomenda medir antes o modelo forte com esforço menor e lembra que o cache de prompt é por modelo, o que penaliza alternar modelos na mesma conversa. **[Inferência]** As duas posições não se contradizem: no RPI a troca de modelo acontece na fronteira de janela, onde o cache já começaria frio. O que fica em aberto é se Opus com esforço `low` empata com Sonnet `medium` como implementer em custo por task concluída. O padrão segue o guia (Sonnet) e a fase 3 mede (D34).

### 16.4 Como cada ferramenta declara agente e modelo **[Externo, consultado em 25/10/2026]**

| | Claude Code | Cursor | Codex | Copilot (VS Code) |
| --- | --- | --- | --- | --- |
| Onde | `.claude/agents/*.md` (projeto), `~/.claude/agents/` (usuário); plugins e managed settings | `.cursor/agents/`; também lê `.claude/agents/` e `.codex/agents/` "for compatibility"; `.cursor/` vence em conflito de nome | `.codex/agents/*.toml` (projeto), `~/.codex/agents/` | arquivos `*.agent.md` (diretório exato a conferir) |
| Campo de modelo | `model`: `fable`, `opus`, `sonnet`, `haiku`, ID completo ou `inherit` | `model`: `inherit` (padrão) ou ID, com parâmetros entre colchetes (ex. da doc: `claude-opus-5[effort=high,context=300k]`) | `model`, `model_reasoning_effort` | `model`: string ou lista em ordem de preferência (usa o primeiro disponível) |
| Esforço | `effort`: `low`…`max` | dentro dos colchetes | `model_reasoning_effort` | não conferido |
| Restringir a leitura | `tools` / `disallowedTools` | `readonly: true` | `features.shell_tool = false` etc.; sandbox e aprovações vêm da sessão pai | `tools` |
| Padrão global para sub-agents | `CLAUDE_CODE_SUBAGENT_MODEL`; com `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` ele **sobrescreve** o `model` de todos | — | `agents.default_subagent_model`, `agents.default_subagent_reasoning_effort` | — |
| Ordem de resolução do modelo | parâmetro da chamada → `model` do arquivo → variável global → modelo da conversa | `model` do arquivo → `inherit` | arquivo → valor da chamada → `[agents]` → sessão pai | `model` do arquivo → modelo selecionado |
| Aninhamento | até 3 níveis abaixo; até 20 concorrentes | só o principal e os filhos diretos disparam | `agents.max_concurrent_threads_per_session` | campo `agents` lista quem pode ser sub-agent |
| Sub-agents embutidos | **Explore**: modelo da conversa principal (com exceções); **Plan**: herda; **general-purpose**: variável global ou principal; claude-code-guide: Haiku | **Explore**: "a faster model"; Browser | `default`, `worker`, `explorer` (modelos não informados) | — |
| Quando delega | pela `description` ou por pedido | pela `description` | só por pedido direto ou instrução do projeto ou da skill | via `agents` e handoffs |

Consequências para o harness:

1. **O Explore do Claude Code herda o modelo principal.** Se o dev trabalha com Opus, toda exploração delegada ao Explore sai a preço de Opus. O harness entrega o próprio `harness-explorer` com `model: haiku` e as skills do harness mandam usá-lo. Não sobrescreve o Explore embutido: isso é escolha do time (coexistência, N2).
2. **O mesmo alias resolve para modelos diferentes conforme o provedor.** Na API Anthropic, `sonnet` é Sonnet 5.5 e `haiku` é Haiku 5.5. Em Bedrock e no Agent Platform do Google, `sonnet` é Sonnet 4.5 e `haiku` é Haiku 4.5; no Foundry, `opus` é Opus 4.6. O roster precisa mostrar o modelo **resolvido**, não só o alias (16.8).
3. **O Codex só delega quando pedido.** As skills do harness pedem delegação de forma explícita, o que é bom para todas as ferramentas (cap. 11: "peça explicitamente ao orquestrador para delegar").
4. **O Cursor lê `.claude/agents/`.** Um arquivo com `model: sonnet` pensado para o Claude Code pode ser lido pelo Cursor, e o comportamento com um alias que ele não conhece não foi verificado. O harness gera `.cursor/agents/harness-*.md` com o mesmo nome, que tem precedência.
5. **Planos legados do Cursor sem Max Mode rodam sub-agents em Composer**, seja qual for o `model`. O relatório avisa.
6. **Uma variável de ambiente na máquina do dev pode anular o roster** (`CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`). O `doctor` detecta e avisa.

### 16.5 Roster: qual agente para cada situação

Quatro tiers abstratos, mapeados por adaptador (16.7):

| Tier | Para quê | Claude Code, API Anthropic (out/2026) |
| --- | --- | --- |
| `fast` | ler muito e devolver pouco; tarefas mecânicas com DoD fechada | `haiku` → Haiku 5.5 |
| `standard` | executar um plano; revisar com checklist; escrever doc a partir de evidência | `sonnet` → Sonnet 5.5 |
| `strong` | pesquisar e sintetizar, especificar, decidir design, verificar, revisar segurança | `opus` → Opus 5.5 |
| `frontier` | exceção registrada: pesquisa de horizonte muito longo ou advisor em ponto difícil | `fable` → Fable 5.1 (desligado por padrão) |

**Sem modelo** (scripts, custo zero): gate, test guard, boundary guard, checks computacionais do `assess`, `doctor`, ordenação do backlog, contagem JUnit, soma de notas do juiz. É o P8 ("determinístico onde der") e é a primeira economia.

**O roster.** Os nomes de arquivo são `harness-<papel>` em cada ferramenta.

| Papel | Estações | O que faz | Tier | Esforço | Ferramentas | Paralelo | Base |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **orquestrador** (sessão principal: `harness-prepare`, `harness-execute`) | todas | lê o estado, decide, delega, para nos pontos humanos; não lê código | é o modelo da sessão do dev: `strong` em janelas de Research e Spec, `standard` em janelas de Execute. No Claude Code, o alias `opusplan` (Opus no plan mode, Sonnet na execução) aplica o cap. 8 numa sessão só | medium | todas | — | caps. 8, 11; **[Externo]** doc de modelos do Claude Code |
| `explorer` | Intake, Spec, preparação (passos 1 e 4) | varre o código e coleta evidência com `arquivo:linha`; responde "onde isso é usado?"; não julga | `fast` | low | só leitura (`Read`, `Grep`, `Glob`) | sim, até `maxReaders` | cap. 11 (leitura de baixo acoplamento); **[Externo]** Anthropic indica Haiku para "subagent tasks" |
| `researcher` | Spec (R do RPI) | pesquisa externa e interna, compara alternativas, escreve o documento de pesquisa | `strong` | high | leitura + web; pode disparar `explorer`s | um por pesquisa | cap. 9; **[Externo]** líder Opus no sistema de pesquisa da Anthropic |
| `synthesizer` | preparação (passo 4) | consolida as saídas dos explorers em candidatos com contra-exemplos e `INCERTO` | `strong` | high | leitura; escreve só em `reports/` | não | caps. 2, 9; 15.3 |
| `auditor` | preparação (passo 1); linter de AGENTS.md | responde os checks inferenciais (a regra é testável? é não óbvia?) e gera achados | `standard` | medium | só leitura | sim, por grupo de checks | 15.2, 15.4 |
| `planner` | Spec, Plan | spec, design e tasks com DoD; mapa de execução; auto-sizing | `strong` | high; `xhigh` com decisão de arquitetura | leitura; escreve só em `work/<ID>/` | não | caps. 8, 9 (o erro da spec se multiplica) |
| `implementer` | Execute | implementa um bloco de tasks, escreve os testes da task, roda o gate, corrige | `standard` | medium | edição, shell; sem `Agent` | até 3, só blocos independentes e `parallelSafe` | caps. 8, 11, 12 |
| `mechanical` | Execute (Quick Mode) | tarefa mecânica com DoD por comando: renomear, mover seção de doc, ajustar import, atualizar referência | `fast` | medium | edição, shell; sem `Agent` | como o implementer | **[Inferência]** o gate independe do modelo; a medir |
| `verifier` | Verify | responde checks binários da spec com evidência; check sem evidência = não atendido | `strong`, **pinado** por ID (`claude-opus-5-5`) | high | leitura + execução de comandos; sem edição | não | caps. 13, 15; HG S7 |
| `reviewer` (um arquivo; a especialidade vem de `docs/agents/review/<tema>.md`) | Review | requisitos, arquitetura, testes, regressão e alucinação, performance | `standard` | medium | só leitura | sim, um por especialidade | cap. 14 ("rodam com Sonnet"); 15.4 |
| `security` | Review | revisão de segurança ancorada em `integration-patterns.md` e boundaries | `strong` | high | só leitura | junto com os reviewers | cap. 14; **[Externo]** a doc do Codex recomenda esforço `high` para agentes de review e segurança |
| `consolidator` | Review | agrupa por severidade, deduplica, lista arquivos não revisados | `standard` | medium | só leitura | não | cap. 14 |
| `doc-writer` | Learn, preparação (passo 6) | escreve `docs/agents/*` a partir do que foi executado e dos padrões aceitos | `standard` | medium | escreve só em `docs/` | não | caps. 4, 9; 7.3 |
| `retro` | Learn | transforma erro recorrente em regra, exemplo, teste ou sensor; propõe poda | `standard` | medium | leitura; diff proposto | não | caps. 2, 4; HG G8 |
| `triager` | Intake | lê issue ou board, preenche o template de intake (6.3), propõe o tamanho | `fast` | low | leitura + MCP do board | sim, por item | caps. 8, 16 |
| `judge` | evals (fase 3) | avalia runs com checks binários e evidência; nunca avalia trabalho próprio | `strong`, **pinado** | fixo | só leitura | um por run | cap. 15; HG §7 |

Notas sobre o roster:

- **Testes.** O guia põe a escrita dos testes dentro do loop do implementer, derivada da spec (cap. 12), e o test guard congela os testes da fase red (HG §6). Por isso não há um "agente de testes" no padrão. Rodar testes e contar resultados é script. Um `test-author` separado (`standard`, esforço high) é opcional para testes de aceitação E2E de requisitos de interface (R36), quando a pessoa quiser que quem escreve o teste não seja quem implementa.
- **Pesquisa = strong, leitura = fast.** O pedido "pesquisa num modelo potente" vale para quem **sintetiza e decide** (researcher, synthesizer, planner). A coleta que alimenta essa síntese é leitura de baixo acoplamento e vai para o tier mais barato, em paralelo. É o desenho do sistema de pesquisa da Anthropic com o tier atual mais barato no lugar do Sonnet; o tier exato dos coletores é uma das coisas que a fase 3 mede.
- **Verifier diferente do implementer.** Modelo diferente e contexto limpo. **[Inferência]** A troca de modelo pode reduzir a autopreferência, que o guia registra como não confirmada no artigo de referência (cap. 15). O motivo principal continua sendo o do cap. 13: quem julga não viu o código ser escrito.
- **Segurança em `strong`.** Um falso negativo custa mais que o preço do tier. **[Externo]** Opus 5.5 e Sonnet 5.5 têm classificadores que podem recusar conteúdo de categorias como `cyber`. Recusa vira "revisão de segurança incompleta" no relatório, nunca "aprovado".
- **Orçamento de contexto do roster.** A `description` de cada sub-agent entra na listagem da sessão principal, como as skills (cap. 5). Descriptions de uma ou duas linhas, roster entregue por fase (16.9) e o `doctor` somando o custo junto com o resto do harness (HG §4.4).

### 16.6 Regras de economia

1. **Script antes de modelo.** Tudo o que é determinístico sai do modelo (P8).
2. **Leitura em massa no tier `fast`, em paralelo; julgamento num tier acima.** Os explorers coletam evidência com `arquivo:linha`; quem decide o que a evidência significa é o synthesizer, o planner ou o verifier.
3. **Modelo forte onde o erro se multiplica:** spec, design, verificação e segurança (cap. 9, armadilha "a spec que ninguém revisou").
4. **Execução de plano no tier `standard`.** Desce para `fast` em tarefa mecânica com DoD por comando; o gate cobra igual de qualquer modelo.
5. **Esforço antes de modelo.** Antes de subir de tier, subir o esforço no tier atual. Antes de criar uma cascata, medir o modelo forte com esforço baixo (**[Externo]** Anthropic).
6. **Trocar de modelo só na fronteira de janela.** O cache de prompt é por modelo; trocar no meio da conversa paga a leitura de novo. O RPI e os pontos humanos (15.7) já dão as fronteiras certas.
7. **Custo por task concluída, não por token.** Um modelo barato que precisa de três voltas de correção pode sair mais caro que um forte que acerta de primeira. O `STATE.md` registra modelo, voltas e tokens por task quando a ferramenta expõe isso.
8. **Escalar com regra, não por reflexo.** Primeiro o contexto, depois um tier acima uma vez (`fallbackTier`), depois o humano (15.7; cap. 10).
9. **`frontier` com motivo registrado.** Desligado por padrão; quando ligado, o papel e o motivo vão para o `STATE.md`.
10. **Medir no repo hospedeiro.** Ablação por papel em `.harness/evals/` (fase 3), como o cap. 15 e o HG §7.4 mandam para qualquer componente.

**Ordem de grandeza, ilustrativa** (preços da 16.3, sem cache, prompts até 100K): ler 5M tokens e devolver 200K custa ~US$ 24 no Opus 5.5, ~US$ 12 no Sonnet 5.5 e ~US$ 0,60 no Haiku 5.5. Para quem usa assinatura em vez de API, **[Inferência, não conferido]** a mesma proporção aparece como consumo do limite de uso.

### 16.7 Registro no repositório hospedeiro **[Proposta ao HG §3.1]**

Três lugares, cada um com um papel, seguindo "detectar não é decidir" (HG §3.1):

| Onde | O quê | Quem escreve |
| --- | --- | --- |
| `.harness/inventory.json#agents` | fatos detectados: ferramentas, provedor, restrições de modelo, variáveis que anulam o roster, sub-agents que o time já tem e o modelo de cada um | `bootstrap.py detect` (regenerável) |
| `.harness/profile.json` → `models` + `roles` | a decisão: tier por papel, mapeamento de tier para modelo por ferramenta, pins, limites | proposto pelo bootstrap, **confirmado pela pessoa** |
| `.harness/reports/agents.md` | para o dev: cada papel, quando é chamado, arquivo por ferramenta, modelo resolvido, esforço, custo relativo, avisos | `bootstrap.py agents` e `doctor` (regenerável) |

Bloco proposto no perfil, compatível com o `roles` atual do HG (`cheap` passa a ser `standard`):

```json
"models": {
  "provider": { "value": "anthropic-api", "origin": "env", "status": "confirmed" },
  "tiers": {
    "fast":     { "claude-code": "haiku",  "cursor": "<a definir no piloto>", "codex": "<a definir>" },
    "standard": { "claude-code": "sonnet", "cursor": "<a definir no piloto>", "codex": "<a definir>" },
    "strong":   { "claude-code": "opus",   "cursor": "<a definir no piloto>", "codex": "<a definir>" },
    "frontier": { "claude-code": "fable",  "enabled": false }
  },
  "pins": { "verifier": "claude-opus-5-5", "judge": "claude-opus-5-5" }
},
"roles": {
  "explorer":     { "tier": "fast",     "effort": "low",    "readonly": true, "parallel": true },
  "researcher":   { "tier": "strong",   "effort": "high",   "readonly": true },
  "planner":      { "tier": "strong",   "effort": "high" },
  "implementer":  { "tier": "standard", "effort": "medium", "fallbackTier": "strong" },
  "mechanical":   { "tier": "fast",     "effort": "medium", "fallbackTier": "standard" },
  "verifier":     { "tier": "strong",   "effort": "high",   "pinned": true, "readonly": true },
  "reviewer":     { "tier": "standard", "effort": "medium", "readonly": true, "parallel": true },
  "security":     { "tier": "strong",   "effort": "high",   "readonly": true }
},
"limits": { "maxDepth": 2, "maxWorkers": 3, "maxReaders": 6, "contextTarget": 0.40, "maxFixIterations": 3 }
```

O `maxReaders` de 6 é um ponto de partida: a Anthropic usa 2 a 4 sub-agents para comparações e mais de 10 só em pesquisa complexa; o valor final sai do piloto.

**O que o `apply` gera a partir do perfil** (adaptadores finos, HG §4.2):

| Ferramenta | Arquivo | Campos preenchidos |
| --- | --- | --- |
| Claude Code | `.claude/agents/harness-<papel>.md` | `name`, `description`, `model` (alias, ou ID se pinado), `effort`, `tools` / `disallowedTools` (sempre com `Agent` nos workers), `skills` quando o papel precisa de uma |
| Cursor | `.cursor/agents/harness-<papel>.md` | `name`, `description`, `model` com colchetes de esforço, `readonly` |
| Codex | `.codex/agents/harness-<papel>.toml` | `name`, `description`, `developer_instructions`, `model`, `model_reasoning_effort` |
| Copilot | `harness-<papel>.agent.md` | `model` como lista de preferência; `tools` |

O corpo de cada arquivo é o mesmo texto (o prompt do papel), mantido uma vez em `core/roles/<papel>.md` no generic-harness. O adaptador só acrescenta o frontmatter da ferramenta. Assim o "qual agente para cada situação" tem uma fonte só, e trocar de modelo é editar o perfil e rodar `apply`, não reescrever agentes.

**No AGENTS.md: nada.** As ferramentas já listam os sub-agents pela `description`, e as skills do harness chamam os papéis pelo nome. Uma linha a mais no contexto permanente não paga o custo (cap. 4).

### 16.8 Detecção e verificação

**O que `detect` procura** (somente leitura, como toda a 4.1):

| Sinal | Onde | Uso |
| --- | --- | --- |
| Ferramentas presentes | diretórios de configuração (4.1) e binários no PATH (`claude`, `cursor-agent`, `codex`) | quais adaptadores gerar |
| Provedor | variáveis como `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_BASE_URL` (lista exata a conferir) | qual modelo cada alias resolve (16.4, item 2) |
| Aliases redefinidos | `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU,FABLE}_MODEL` | idem |
| Restrições | `availableModels`, `model` e `fallbackModel` nos `settings.json` do projeto | um tier que aponta para modelo bloqueado vira conflito, não falha silenciosa |
| Anulação do roster | `CLAUDE_CODE_SUBAGENT_MODEL` e `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` | aviso no relatório |
| Agentes do time | `.claude/agents/`, `.cursor/agents/`, `.codex/agents/`, arquivos `*.agent.md`: nome, `description`, `model`, ferramentas | **adotar** (ex.: o time já tem um `code-reviewer` com Sonnet: o papel `reviewer` aponta para ele, com aceite) ou **coexistir** (prefixo `harness-`). Nunca sobrescrever (N2) |

**O que não dá para detectar e vira pergunta** no passo 2 da 15.7: plano ou assinatura, teto de custo, modelos liberados pela organização, e se o time aceita o tier `frontier` em algum papel.

**Checks do `doctor` sobre agentes:**

- todo papel do `roles` tem arquivo em cada ferramenta habilitada, e todo arquivo `harness-*` tem papel (o mesmo par ponteiro↔arquivo do 7.2);
- o modelo pinado existe na lista de modelos do provedor detectado;
- `verifier` e `judge` estão pinados por ID e não usam o mesmo modelo do `implementer`;
- nenhum worker tem `Agent` liberado (profundidade 2);
- nenhuma variável de ambiente anula o roster sem aviso;
- a soma das `description`s cabe no orçamento de contexto do harness (HG §4.4);
- o `reports/agents.md` mostra o modelo **resolvido** de cada papel em cada ferramenta, para o dev conferir de relance.

### 16.9 Entrega por fase

| Fase HG | Papéis | Motivo |
| --- | --- | --- |
| 0 | `explorer`, `implementer`, `verifier` (+ orquestrador como skill) | o primeiro loop precisa de exploração barata, execução e verificação separada (HG §9) |
| 1 | `researcher`, `synthesizer`, `auditor`, `planner`, `mechanical`, `doc-writer`, `retro` | entram com o onboarding, a captura de padrões e a retro |
| 2 | `reviewer`, `security`, `consolidator`, `triager` | entram com review local e intake |
| 3 | `judge`; ablação por papel | entram com as evals |

### 16.10 Riscos específicos

| Risco | Mitigação |
| --- | --- |
| Um alias passa a apontar para outro modelo num release e o juiz muda sem ninguém ver | `verifier` e `judge` pinados por ID; o modelo resolvido entra na evidência de cada run (HG §7: o objeto avaliado é modelo + harness + configuração) |
| O mesmo perfil roda modelos diferentes em provedores diferentes | provedor detectado e confirmado; `reports/agents.md` mostra o modelo resolvido; o tier aceita ID explícito por ferramenta |
| O Explore embutido herda o modelo principal e a exploração sai a preço de Opus | `harness-explorer` próprio no tier `fast`; as skills do harness o chamam pelo nome |
| Fan-out explode o consumo (multi-agente ~15× um chat, **[Externo]** Anthropic) | fan-out só em leitura; `maxReaders`; profundidade 2; resultado por referência |
| O tier `fast` perde nuance em leitura que exige interpretação | explorers só coletam evidência; julgamento num tier acima; medir na fase 3 |
| O modelo barato "trapaceia" nos testes | gate, test guard e boundary guard independem do modelo (cap. 12) |
| Recusa por classificador em revisão de segurança | resultado "incompleto", nunca "aprovado"; fallback de modelo onde a ferramenta oferece |
| Trocar de modelo no meio da conversa invalida o cache | troca só na fronteira de janela (16.6, regra 6) |
| O Cursor lê `.claude/agents/` com aliases do Claude Code | gerar `.cursor/agents/` com o mesmo nome, que tem precedência; conferir no piloto |
| Uma variável de ambiente anula o roster | o `doctor` detecta e avisa |
| Os nomes de modelo de Cursor, Codex e Copilot mudam rápido | ficam no catálogo versionado e no perfil, nunca no código; o adaptador declara a versão mínima testada (HG §11) |
| Roster grande pesa no contexto fixo | entrega por fase; descriptions curtas; o `doctor` soma |
| A tabela vira dogma | o roster é ponto de partida; a fase 3 mede por custo por task concluída e o perfil muda com evidência (P11) |

---

## Apêndice: fontes

### Locais

- *IA First Dev: Agentes, Loops e Harness* (`ia-first-dev.pdf`, out/2026). Capítulos usados: 2 (codebase é contexto, legado, feedback), 3 (zonas da janela), 4 (AGENTS.md, Ap. A checklist), 5 (skills), 6 (onde colocar algo novo; MCP; escolha de modelo e esforço na ferramenta), 7 (documentos do fluxo, por tamanho de time), 8 (board e Jira Assistant; modelo forte para planejar, barato para implementar), 9 (RPI, mapeamento, spec, tasks, comparação de frameworks, custo por modelo), 10 (não trocar de modelo como primeira reação), 11 (sub-agents, benchmark, acoplamento, orquestrador), 12 (enforcement, shift-left), 13 (o código precisa permitir o harness), 14 (grounding e diretrizes de review), 15, 16 (ponta a ponta), 17 (playbook), 18 (kit de skills).
- [Harness genérico: pesquisa](harness-generico.md) (HG), 22–25/10/2026.
- [O harness genérico e o guia correspondem a uma fábrica de agentes?](fabrica-de-agentes-avaliacao.md), 25/10/2026.

### Externas (consultadas em 25/10/2026)

Estudos sobre arquivos de contexto:

- Gloaguen et al., *Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?* (ETH Zurich): https://arxiv.org/abs/2602.11988 · resumo secundário: https://www.marktechpost.com/2026/02/25/new-eth-zurich-study-proves-your-ai-coding-agents-are-failing-because-your-agents-md-files-are-too-detailed/
- Lulla et al., AGENTS.md e eficiência de agentes: https://arxiv.org/abs/2601.20404
- *Probe-and-Refine Tuning of Repository Guidance for Coding Agents*: https://arxiv.org/abs/2606.20512

Frameworks de spec e instaladores:

- OpenSpec: https://github.com/Fission-AI/OpenSpec
- GitHub Spec Kit: https://github.com/github/spec-kit
- BMAD Method: https://github.com/bmad-code-org/BMAD-METHOD
- Agent OS: https://buildermethods.com/agent-os/installation · https://buildermethods.com/agent-os/v2/updating · https://github.com/buildermethods/agent-os
- Kiro, specs: https://kiro.dev/docs/specs/concepts · guia de terceiros sobre steering: https://thepromptshelf.dev/blog/amazon-kiro-ide-complete-guide-2026/
- Comparativos (opinião, não fonte primária): https://glukhov.org/ai-devtools/ai-coding-assistants/spec-kit-vs-kiro-vs-claude-code/ · https://codemyspec.com/blog/best-spec-driven-development-tools

Distribuição, sincronização e sugestões:

- skills.sh / `npx skills`: https://qaskills.sh/blog/skills-sh-agent-skills-directory-guide · https://supabase.com/docs/guides/ai-tools/ai-skills.md
- Copier update (fonte secundária): https://af.datarobot.com/guides/working-with-copier/
- Sincronizadores de regras entre agentes (projetos pequenos, citados como evidência de padrão, não como recomendação): https://github.com/PanisHandsome/ai-rules-sync · https://pypi.org/project/rulesync · https://github.com/yelmuratoff/agent_sync · https://getunblocked.com/blog/keeping-claude-md-agents-md-cursorrules-in-sync/

Prontidão do repositório para agentes (seção 15):

- Factory, Agent Readiness (overview): https://docs.factory.com/web/agent-readiness/overview · artigo *Measuring agent readiness* (27/05/2026): https://factory.com/articles/measuring-agent-readiness
- Larridin, readiness checklist (doc de produto, atualizada em 07/09/2026): https://larridin.com/developer-intelligence/readiness-checklist/
- `agent-ready` (CLI aberto): https://github.com/eshener/agent-ready
- BMAD, projetos existentes (project context e document-project): https://docs.bmad-method.org/how-to/established-projects/
- Kiro, steering: https://kiro.dev/docs/steering/
- MADR (ADRs em Markdown): https://adr.github.io/madr/ (versão 4.0.0 vista em projetos que a adotam; página do projeto não consultada diretamente)

Camada de spec, instalação e CLIs (seção 15.5):

- OpenSpec, setup: https://openspec.dev/docs/setup · CLI: https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md
- Spec Kit, quickstart: https://github.github.io/spec-kit/quickstart.html
- TLC Spec-Driven: https://agent-skills.techleads.club/skills/tlc-spec-driven/ · instalador: https://github.com/tech-leads-club/agent-skills
- Superpowers, instalação no Claude Code (fonte secundária): https://www.mintlify.com/obra/superpowers/installation/claude-code
- Agent Skills, spec aberta: https://agentskills.io/ (consultada por espelhos e resumos; página oficial a conferir)
- AGENTS.md: https://agents.md/ (precedência de arquivos aninhados e suporte por ferramenta vistos só em fontes secundárias)

Documentação para LLMs:

- Estado do `llms.txt` (fontes secundárias): https://presenc.ai/research/state-of-llms-txt-2026 · https://aiagentrank.io/glossary/llms-txt

Agentes, modelos e orquestração (15.7 e seção 16):

- Anthropic, escolha de modelo: https://platform.claude.com/docs/en/about-claude/models/choosing-a-model · estratégias com mais de um modelo (advisor e orquestrador, com medições): https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence · preços e IDs: tabela de modelos da documentação da API (cache de 06/10/2026 consultado em 25/10/2026)
- Anthropic, *How we built our multi-agent research system*: https://www.anthropic.com/engineering/multi-agent-research-system
- Claude Code, sub-agents (campos, embutidos, ordem de resolução do modelo, aninhamento): https://code.claude.com/docs/en/sub-agents · configuração de modelo (aliases por provedor, `opusplan`, esforço): https://code.claude.com/docs/en/model-config
- Cursor, subagents: https://cursor.com/docs/subagents
- Codex, subagents (redireciona para learn.chatgpt.com): https://learn.chatgpt.com/docs/agent-configuration/subagents.md · cobertura secundária: https://simonwillison.net/2026/Mar/16/codex-subagents
- VS Code / Copilot, custom agents: https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference
- Comparativos de modelos de terceiros (opinião, conflitam entre si nos preços; não usados como fonte de número): https://www.claudelog.com/mechanics/tactical-model-selection/ · https://www.morphllm.com/comparisons/claude-haiku-vs-sonnet-vs-opus

Execução headless (fontes secundárias, flags a conferir na doc oficial):

- https://developertoolkit.ai/en/ecosystem/agent-tools/headless-agents-ci/ · https://inventivehq.com/blog/ai-coding-clis-in-ci-cd-automation · https://www.deployhq.com/blog/running-ai-coding-agents-cicd-headless-mode-claude-code-codex-gemini

Não revalidadas nesta pesquisa: a matriz de capacidades por ferramenta (HG §4.1), a lista exata de arquivos de configuração por ferramenta (4.1 desta pesquisa) e as flags de JUnit por ecossistema (5.2). Todas precisam de conferência na fase de Plan. Da seção 15, também ficam para o Plan: os cabeçalhos de delta do OpenSpec além de `ADDED`, os caminhos de constituição e features do Spec Kit, o formato do plano do Superpowers e a regra exata de nível da Factory (a doc diz 80%; o artigo não detalha). Da seção 16, ficam para o Plan: o diretório dos `*.agent.md` do Copilot e o suporte a esforço nele, os nomes de modelo por tier no Cursor e no Codex, a lista exata de variáveis de provedor do Claude Code, o preço de leitura de cache do Haiku 5.5, como o Cursor trata um alias do Claude Code lido de `.claude/agents/` e quais modelos os sub-agents embutidos do Codex usam.
