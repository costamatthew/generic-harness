# Repositório do zero (greenfield): pesquisa

> **Fase:** Research do RPI (cap. 9). Entrada para um Plan futuro, numa janela nova. Nada aqui foi implementado.
> **Hierarquia de fontes:** o guia *IA First Dev* (`ia-first-dev.pdf`, cap. N / Ap. X) decide. [harness-generico.md](harness-generico.md) é a fonte da verdade do harness ("HG §N"). [bootstrap-fabrica-de-agentes.md](bootstrap-fabrica-de-agentes.md) descreve como o harness se instala num repositório existente ("BF §N"). Esta pesquisa **estende o BF** para o caso que ele trata em uma linha (BF §9.1, "Greenfield"): o repositório ainda não tem código, e a fábrica precisa ajudar a criar tudo. Mudanças propostas aparecem como **[Proposta ao BF]** ou **[Proposta ao HG]** e não substituem o texto original até serem aceitas.
> **Complementos externos** vêm marcados como **[Externo]**, consultados em 29/10/2026. Inferências desta pesquisa vêm marcadas como **[Inferência]**.
> **Data:** 29/10/2026.

---

## 0. TL;DR

1. **O BF parte de "detectar"; o greenfield parte de "decidir".** Em repo vazio não há CI, manifesto nem teste para ler. Os slots do perfil que o BF preenche por detecção (comandos, stack, padrões) passam a ser preenchidos por **decisões humanas registradas em ADR** e só viram fato quando o código que as executa existe e roda. O perfil ganha a origem `decision` e o estado `planned` (seção 4).
2. **A regra do cap. 4 continua valendo, e fica mais fácil de cumprir.** O guia proíbe gerar o AGENTS.md a partir do codebase. Em greenfield não há codebase: o conteúdo vem das decisões de fundação (stack, comandos, boundaries), que são exatamente o "mínimo" que o cap. 4 manda escrever primeiro. O que continua proibido é a IA inventar convenções que ninguém decidiu (cap. 7, armadilha).
3. **A primeira demanda da fábrica é o esqueleto andante** (*walking skeleton*): o menor caminho de ponta a ponta que builda, testa, linta, passa no CI e sobe. É o primeiro loop do cap. 17 e o critério de aceite do bootstrap em greenfield. Antes dele, nenhum sensor existe e nenhum gate pode ficar verde (seção 6).
4. **Sensor novo precisa provar que sente.** A task que cria o comando de teste não pode se validar só com exit 0 do próprio comando. O gate exige a demonstração vermelho → verde: um teste quebrado de propósito faz o comando falhar, e o teste correto faz passar (seção 6.3; cap. 12, fase red).
5. **Código de partida vem do gerador oficial do ecossistema, não do modelo.** `uv init`, `cargo new`, `go mod init`, `npm create vite`, `dotnet new`, `flutter create` e equivalentes produzem a estrutura que a comunidade espera. O harness mantém um catálogo de geradores como dado (seção 6.2). Boilerplate escrito pelo modelo é mais caro e menos previsível.
6. **A escolha da stack é decisão humana com critério de harnessability.** **[Externo]** Böckeler: "Greenfield teams can bake harnessability in from day one". Tipagem forte vira sensor de graça, e 94% dos erros de compilação em TypeScript gerado por LLM foram falhas de tipo num estudo da PLDI 2025. Ao mesmo tempo, LLMs têm viés forte por Python e se contradizem nas próprias recomendações (83% num estudo de 2025). A IA propõe alternativas e trade-offs; a pessoa decide e registra em ADR (seção 5).
7. **Discovery antes de código, proporcional ao porte.** Solo: brief de uma página. Time pequeno: brief + ADRs. Projeto médio com incerteza: Lean Inception antes de tudo (cap. 7). O harness oferece templates e um questionário curto, não gera PRD sozinho.
8. **Backlog de produto como lista de features com status.** O guia manda dar ao agente "uma lista explícita de features com status, para que 'pronto' tenha um critério" (cap. 13, FAÇA). O harness guarda `features.json` em que só o script muda o status. A spec de cada feature é escrita **na hora de implementar** (auto-sizing do cap. 9), não toda de uma vez no início.
9. **As primeiras features fixam os padrões.** "O modelo copia o que vê" (cap. 2). Em greenfield, a primeira implementação de cada tipo de arquivo (endpoint, componente, teste, migration) vira o exemplo que o agente vai repetir. Ela recebe review mais rigoroso e é marcada como **exemplar canônico** (seção 7.3).
10. **O greenfield termina numa transição explícita para brownfield.** Quando o esqueleto existe, as camadas principais têm exemplar e o repo chega a P2, o perfil muda `project.kind` para `brownfield` e o fluxo normal do BF (avaliação, captura de padrões, retro) assume (seção 8).
11. **Sem skill nova no orçamento.** O orquestrador `harness-prepare` (BF §15.7) ganha um ramo greenfield em `references/greenfield.md`. Nenhum papel novo no roster: `researcher`, `planner`, `implementer`, `mechanical` e `verifier` cobrem o fluxo (seção 9).

---

## 1. Escopo e interpretação

### 1.1 O pedido, reformulado

> Preparar o generic-harness para pegar um repositório do zero, em que ainda vamos criar tudo, e dar suporte a essa criação.

Requisitos derivados:

| # | Requisito | Consequência |
| --- | --- | --- |
| G-R1 | Funciona num diretório vazio, num repo só com README/LICENSE ou num repo recém-gerado por um scaffolder | Classificação de greenfield antes do inventário (seção 3) |
| G-R2 | Ajuda a **decidir** o que o BF só **detecta**: stack, arquitetura, estratégia de testes, CI, camada de spec | Fluxo de decisões de fundação com ADR (seção 5) |
| G-R3 | Cria os **sensores** antes das features | Esqueleto andante como primeira demanda (seção 6) |
| G-R4 | Conduz a construção do produto pela fábrica, não só a instalação | Backlog de features com status e spec just-in-time (seção 7) |
| G-R5 | Mantém as restrições do guia: estrutura sim, conteúdo inventado não; humano nos pontos de decisão; um loop verificável antes da infraestrutura inteira | Seções 2 e 10 |
| G-R6 | Continua agnóstico de linguagem | Catálogo de geradores como dado; JUnit como língua franca (BF §5.2) |

### 1.2 O que muda em relação ao BF

| Tema | BF | Esta pesquisa |
| --- | --- | --- |
| Fonte dos valores do perfil | detecção (CI → task runner → manifesto → docs → preset, BF §5.1) | **decisão** registrada em ADR; depois verificação ao rodar |
| Nível de maturidade | N0–N4 e P0–P4 medem o que existe | o repo começa em N0 e abaixo de P0; os níveis viram **metas de construção** |
| Primeiro loop | um READY de preparação (ex.: fazer o teste emitir JUnit) | o **esqueleto andante** |
| Captura de padrões (BF §15.3) | lê o código existente | não há o que ler; os padrões são **decididos** e depois **fixados** pelos exemplares canônicos |
| Docs | diffs de poda sobre o que existe | criação mínima a partir de decisões |
| Fim | prontidão alvo atingida | **transição para brownfield** |

### 1.3 Fora de escopo

- Escolher a stack pela pessoa. O harness só estrutura a decisão.
- Gerar o produto inteiro numa sessão autônoma longa. Isso é L6 (HG §3.3) e fica para a fase 3, com as ressalvas da seção 7.4.
- Agentes como produtos (HG §14).

---

## 2. O que o guia diz sobre projeto novo

O guia trata greenfield de forma esparsa, mas as regras que existem são claras:

| Regra | Guia | Efeito no greenfield |
| --- | --- | --- |
| "Quando o projeto é novo e não há contexto nenhum, a Discovery precisa de um ponto de partida." Lean Inception para projeto novo, de médio porte, com incerteza | cap. 7 | Discovery entra antes do esqueleto, escolhida pelo porte |
| PRD e Design Doc para "projeto novo, de várias semanas, com várias pessoas"; sozinho, "na maioria das vezes, a spec basta" | cap. 7 | Conjunto de documentos pelo tamanho do time (BF §15.4) |
| "Concentrar o esforço humano na Discovery, onde estão as decisões que a IA não consegue tomar" | cap. 7 | Stack, arquitetura e escopo do MVP são decisões humanas |
| RFC "explora uma decisão técnica com várias opções (qual banco de dados usar, por exemplo)"; ADR registra a decisão tomada | cap. 7 | Decisões de fundação: RFC quando há dúvida real, ADR sempre |
| Design It Twice: afiar a linguagem do domínio (`/domain-modeling`), explorar três desenhos com restrições diferentes (`/code-design`), comparar por *depth*, *locality* e *seam*, sintetizar num RFC | cap. 18 | Procedimento para a decisão de arquitetura (seção 5.3) |
| Comece o AGENTS.md "com o mínimo (stack, comandos, boundaries)" e acrescente a partir dos erros reais | cap. 4 | O AGENTS.md nasce das decisões, curto, e cresce pela retro |
| "O código precisa permitir o harness. [...] Projetar o código e projetar o harness passam a ser o mesmo trabalho" | cap. 13 | Harnessability entra como critério na escolha da stack |
| "Dê ao agente uma lista explícita de features com status, para que 'pronto' tenha um critério" | cap. 13, FAÇA | Backlog em `features.json` (seção 7) |
| Initializer agent: na primeira sessão cria `init.sh`, arquivo de progresso e commit inicial; o coding agent faz uma feature por vez | cap. 15, Complemento (Young) | O esqueleto andante cumpre o papel do initializer, com gate |
| Planner expande "um pedido de 1 a 4 frases numa spec de produto" | cap. 15, Complemento (Rajasekaran) | Possível no modo autônomo da fase 3, com revisão humana do resultado |
| Pastas por domínio; nada de `utils`, `common`, `misc`; monólito modular antes de microserviços | cap. 2 | Recomendação padrão de layout no ADR de arquitetura |
| "Adicione bons exemplos ao repositório. O modelo copia o que vê" | cap. 2 | Exemplares canônicos (seção 7.3) |
| "Montar toda a infraestrutura antes de completar uma task" é a armadilha | cap. 17 | O esqueleto é pequeno e é ele o primeiro loop; o resto entra por demanda |

O guia **não** trata: como escolher linguagem para trabalhar com agentes, como criar o primeiro sensor de um projeto sem nenhum, quando um projeto deixa de ser "novo", nem como a feature list do Young convive com spec por demanda. O restante desta pesquisa preenche essas lacunas, marcando o que é externo ou inferência.

---

## 3. Classificar o repositório como greenfield

### 3.1 Sinais

A classificação roda no `detect` (BF §9, passo 1), antes do inventário de IA, e é somente leitura.

| Classe | Sinais | Fluxo |
| --- | --- | --- |
| **G0 vazio** | sem `.git`, ou `.git` sem commits; nenhum arquivo além de `.gitignore`/README/LICENSE | greenfield completo (seção 4) |
| **G1 só documentação** | README, docs de produto, talvez PRD ou notas; nenhum manifesto de linguagem | greenfield completo; os docs existentes viram entrada da Discovery |
| **G2 recém-gerado** | manifesto e estrutura de um gerador conhecido, poucos commits, nenhum código de domínio além do exemplo do gerador | greenfield a partir do passo 4 (a stack já foi decidida; registrar a decisão em ADR retroativo) |
| **G3 pacote novo em repo existente** | monorepo brownfield em que a pessoa quer criar um app ou pacote novo | **híbrido**: perfil raiz brownfield, perfil do pacote greenfield (BF §5.3) |
| brownfield | qualquer outra coisa | fluxo do BF |

Os limiares exatos (número de commits, de arquivos de código) são heurísticas a calibrar no piloto. Em caso de dúvida, a classificação vira pergunta, como todo conflito no BF (BF §4.2).

### 3.2 O que o `detect` ainda faz em greenfield

Mesmo sem código, há fatos para coletar:

- **Ferramentas de IA e provedor** (BF §16.8): os mesmos sinais de ambiente e binários no PATH.
- **Runtimes instalados** na máquina: `python3`, `node`, `go`, `cargo`, `dotnet`, `flutter`, `java`, e suas versões. Não decidem a stack, mas mostram o custo de cada alternativa (instalar um runtime novo é custo real para o time).
- **Docs de produto existentes** (G1): viram fontes de contexto do brief.
- **Remoto git e hospedagem** (GitHub, GitLab): define o template de CI e o MCP do board a sugerir.

Saída: `inventory.json` com `project.kind: "greenfield"` e a classe (G0–G3).

---

## 4. Mudanças no contrato: perfil que nasce de decisões **[Proposta ao HG §3.1 e BF §5.1]**

### 4.1 Origem e estado de cada valor

O BF já marca cada valor do perfil com origem (`ci`, `task-runner`, `manifest`, `docs`, `preset`) e status (`detected` → `confirmed`). Greenfield precisa de mais uma origem e mais um estado:

| Campo | Valores novos | Significado |
| --- | --- | --- |
| `origin` | `decision:<ADR-NNNN>` | o valor vem de uma decisão registrada, não de leitura do repo |
| `status` | `planned` | decidido, mas o comando ou arquivo ainda não existe; nenhum gate pode depender dele |
| `status` | `verified` | o comando rodou no repo com o exit code esperado (o `confirmed` do BF para comandos passa a exigir isso) |

Ciclo de vida de um comando em greenfield: `planned` (ADR aceito) → `verified` (rodou no esqueleto) → é usado por gates. Ciclo em brownfield, para comparação: `detected` → `confirmed` (pessoa aprovou) → `verified` (rodou).

Exemplo, logo depois das decisões de fundação e antes do esqueleto:

```json
{
  "schema": 1,
  "project": { "name": "pedidos", "kind": "greenfield", "class": "G0",
               "genesis": { "step": "skeleton", "exitCriteria": "seção 8.1" } },
  "commands": {
    "install":   { "run": "uv sync",                       "origin": "decision:ADR-0002", "status": "planned" },
    "lint":      { "run": "uv run ruff check .",           "origin": "decision:ADR-0004", "status": "planned" },
    "typecheck": { "run": "uv run mypy src",               "origin": "decision:ADR-0004", "status": "planned" },
    "test": {
      "unit": { "run": "uv run pytest --junitxml=.harness/runs/unit.xml",
                "report": ".harness/runs/unit.xml",
                "origin": "decision:ADR-0003", "status": "planned" }
    }
  }
}
```

### 4.2 Gate com sensor ausente

Hoje o HG prevê que o `task done` "bloqueia se uma verificação exigida estiver indisponível" (HG §3.2, S2). Em greenfield isso é o estado normal no começo, então a regra precisa ser explícita:

- Um comando `planned` **não conta como verde nem como vermelho**: conta como **sensor ausente**. Task cuja DoD depende dele não pode ser concluída.
- A **única** exceção é a task que cria o sensor (seção 6.3), com a prova vermelho → verde.
- O relatório do gate diz qual ADR decidiu o sensor e qual task do esqueleto vai criá-lo, para o agente não "resolver" a ausência improvisando outro comando (P15).

### 4.3 Onde as decisões ficam

| Artefato | Onde | Quem escreve |
| --- | --- | --- |
| brief do produto | `docs/product/brief.md` | pessoa, com a IA ajudando a perguntar (5.1) |
| decisões de fundação | `docs/decisions/0001-*.md` em diante | IA redige a partir da conversa; **pessoa aceita** (status do ADR) |
| RFC, quando há alternativas reais | `docs/decisions/rfc-NNNN-*.md` | `researcher` + `synthesizer` (5.3); pessoa decide |
| perfil | `.harness/profile.json` | `bootstrap.py` a partir dos ADRs aceitos |
| progresso da gênese | `.harness/STATE.md` (passo atual, próxima decisão pendente) | orquestrador |

**[Inferência]** Gerar o perfil a partir de ADRs exige que cada ADR de fundação tenha um bloco estruturado no final (ex.: `profile:` em YAML ou JSON com os comandos e boundaries que ele decide). É uma convenção do harness sobre um formato livre; MADR permite seções extras sem quebrar o formato. Alternativa: o orquestrador extrai os valores e pede confirmação. A escolha fica em D37.

---

## 5. Decisões de fundação

### 5.1 Discovery proporcional ao porte

O questionário do BF §15.7 (passo 2) ganha um bloco de produto quando o repo é greenfield. O objetivo continua sendo "decidir, não escrever": perguntas curtas com padrão sugerido.

| Pergunta | Por quê |
| --- | --- |
| Qual problema, para quem, e como se sabe que foi resolvido? | o "o quê e o porquê" do PRD (cap. 7), em três linhas |
| O que está fora do escopo do MVP? | evita que a spec invente escopo (cap. 7, armadilha) |
| Tamanho do time e prazo | escolhe os documentos (tabela do cap. 7) |
| Nível de incerteza sobre o produto | alta + porte médio → Lean Inception antes de tudo (cap. 7) |
| Restrições técnicas já dadas (linguagem da empresa, nuvem, banco existente, compliance) | encurta as decisões de fundação: o que já está decidido vira ADR retroativo |
| Há UI? Web, mobile, CLI, API pura? | define E2E (R36) e o tipo de esqueleto |
| Onde mora a demanda (board, issues, nada)? | estação Intake (BF §6.1) |

Saída: `docs/product/brief.md`, uma página:

```markdown
# Brief: <nome>
- Problema: <o que dói, para quem>
- Resultado esperado: <como saber que resolveu; métrica se houver>
- Usuários e jornadas principais: <2 a 5 linhas>
- Escopo do MVP: <lista curta> · Fora do escopo: <lista curta>
- Restrições: <técnicas, legais, de prazo>
- Incertezas abertas: <o que ainda não sabemos e como vamos descobrir>
- Fontes: <links para PRD, Lean Inception, notas de reunião>
```

O brief não é spec. Ele alimenta as decisões de fundação e a primeira versão do backlog (seção 7). Se houver PRD ou Design Doc fora do repo, o brief aponta para eles via MCP (cap. 6), sem copiar.

### 5.2 Quais decisões, em que ordem

Cada linha vira um ADR. A ordem segue a dependência: não dá para escolher o test runner antes da linguagem.

| # | Decisão | Depende de | Precisa de RFC? | Alimenta no perfil |
| --- | --- | --- | --- | --- |
| ADR-0001 | Camada de spec (BF §15.5) e ferramentas de IA do time | — | raramente | `spec`, adaptadores |
| ADR-0002 | Linguagem, runtime, gerenciador de pacotes e versões | brief, restrições | quando há duas opções viáveis | `install`, `build`, stack |
| ADR-0003 | Estratégia de testes: tipos, runner, reporter JUnit, o que precisa de E2E, isolamento | 0002 | não | `test.*`, `parallelSafe`, `globs`, `skipMarkers` |
| ADR-0004 | Lint, formatter, typecheck e hooks pós-edição | 0002 | não | `lint`, `typecheck`, S6 |
| ADR-0005 | Arquitetura e layout: módulos por domínio, fronteiras, direção das dependências | brief, 0002 | **sim**, se o produto não for trivial (5.3) | `docs/agents/architecture.md`, sensor de drift (fase 3) |
| ADR-0006 | Persistência e integrações externas (banco, filas, APIs de terceiros) | 0005 | quando há alternativas reais | boundaries (ex.: migrations), `integration-patterns.md` |
| ADR-0007 | CI, ambiente de desenvolvimento (devcontainer opcional) e `dev` com `ready` | 0002–0004 | não | `dev`, R38 |
| ADR-0008 | Boundaries iniciais e política de git (branch, commit, quem comita) | — | não | `boundaries`, M6 |

Projetos pequenos colapsam várias linhas num ADR só. A tabela é a lista de perguntas, não a lista de arquivos.

**ADR retroativo.** Em G2 (repo recém-gerado) ou quando a restrição já vem dada ("a empresa usa .NET"), o ADR registra a decisão que já foi tomada, com o motivo. Isso mantém o perfil com `origin: decision:` em vez de `preset`.

### 5.3 Como a IA ajuda a decidir sem decidir

O procedimento é o Design It Twice do cap. 18 aplicado às decisões que pedem RFC (normalmente 0002 e 0005):

1. **Linguagem do domínio primeiro** (`/domain-modeling` ou equivalente): termos do brief viram `docs/agents/glossary.md`. Sem isso, as alternativas de arquitetura comparam nomes diferentes para a mesma coisa.
2. **Três alternativas com restrições diferentes**, geradas em paralelo (cap. 18). Ex.: "minimizar dependências", "maximizar velocidade de entrega do MVP", "maximizar harnessability". Cada alternativa é um sub-agent `researcher` (BF §16.5, `strong`) que grava `reports/genesis/alt-<n>.md`.
3. **Síntese num RFC** por um `synthesizer`, com tabela de trade-offs e os critérios abaixo.
4. **A pessoa decide.** O RFC vira ADR aceito. O orquestrador não escolhe.

Critérios que todo RFC de stack ou arquitetura deve cobrir:

| Critério | Pergunta | Fonte |
| --- | --- | --- |
| Adequação ao problema | resolve o brief com o menor número de peças? | cap. 7 |
| Conhecimento do time | quem vai revisar o código domina a stack? | cap. 14 (o humano decide no review) |
| **Harnessability** | tem typecheck forte? linter com regras configuráveis? test runner com JUnit? framework opinativo com convenção de pastas? | cap. 13; **[Externo]** Böckeler |
| Familiaridade dos modelos | a stack é popular o bastante para os modelos errarem pouco e gastarem menos tokens? | **[Externo]** Wu et al.; ver ressalvas abaixo |
| Custo de ambiente | runtime novo na máquina dos devs e no CI? | BF §3.3 (R2) |
| Documentação atualizada acessível | há doc no Context7 ou equivalente para as versões escolhidas? | cap. 4 |
| Reversibilidade | quanto custa trocar se a hipótese do brief estiver errada? | **[Externo]** agentpatterns (abaixo) |

**O que a evidência externa diz sobre stack e agentes [Externo]:**

- **Tipos como sensor.** Böckeler: "A codebase written in a strongly typed language naturally has type-checking as a sensor" e "Greenfield teams can bake harnessability in from day one". Ela também observa que times podem começar a escolher stacks "partly based on what harnesses are already available for them".
- **Erros de tipo dominam os erros de compilação.** Mündler et al. (PLDI 2025), avaliando LLMs abertos: em média 94% dos erros de compilação em TypeScript gerado eram falhas de type check e 6% erros de sintaxe. O GitHub Octoverse 2025 repercutiu o número ao comentar a subida do TypeScript. **[Inferência]** Se a maioria dos erros é de tipo, um typecheck no gate pega a maioria deles antes do teste rodar; numa linguagem sem tipos, esses erros só aparecem em runtime ou não aparecem.
- **Linguagens menos comuns custam mais.** Wu, Anderson e Guha (2026, preprint) compararam Python, Java, Rust e OCaml com cinco modelos: o consumo de tokens varia de forma consistente por linguagem, e em linguagens menos familiares os agentes "repeatedly produce noncompiling solutions". Uma avaliação de terceiros (Dan Luu, só vista em cobertura secundária) não encontrou a vantagem de tokens das linguagens dinâmicas em projetos reais e viu popularidade correlacionada com resultado.
- **O modelo tem viés e se contradiz.** Twist et al. (arXiv 2503.17181): os LLMs escolheram Python em 90–97% dos problemas agnósticos de linguagem e ainda em 58% das tarefas de setup de projeto em que Python não era a melhor opção; Rust não foi escolhido nenhuma vez; e as recomendações de linguagem contradisseram o código que o próprio modelo escreveu em 83% dos casos. **Consequência direta:** perguntar "qual stack devo usar?" a um agente sem critério nem alternativas forçadas produz a resposta do viés, não a do problema. Por isso as três alternativas têm restrições diferentes e a decisão é humana.
- **Compromisso cedo demais.** O padrão "agent-driven greenfield" do agentpatterns.ai avisa que fixar a estrutura cedo é um mau encaixe quando "domain uncertainty outweighs delivery speed", porque compromissos de arquitetura cedo são difíceis de desfazer. **[Inferência]** Isso reforça o Lean Inception do cap. 7 para incerteza alta e justifica o modo spike (5.4).

As fontes não dizem "use a linguagem X". Dizem que tipagem, popularidade e ferramental determinístico pesam a favor do agente, e que o agente não é um bom juiz da própria preferência. Fica como critério, não como regra.

### 5.4 Modo spike: explorar antes de decidir

**[Externo]** O Spec Kit separa três caminhos: "0-to-1 Development (Greenfield)", "Creative Exploration" (implementações paralelas, comparação de tecnologias) e "Iterative Enhancement (Brownfield)". O segundo é o que falta quando a pessoa não consegue decidir no papel.

Proposta: um spike é uma demanda com tipo `spike` (ID `SPIKE-NNN`):

- roda numa branch ou worktree descartável, nunca na principal;
- tem pergunta e critério de decisão escritos antes ("qual ORM lida melhor com o nosso modelo de dados? critério: as três consultas do brief, tempo de setup");
- não passa pelo verifier de spec nem vira código de produção; o resultado é um anexo no RFC;
- tem orçamento (tempo e tokens) declarado no intake.

É o "explorar alternativas em paralelo é diferente de implementar opções concorrentes no mesmo código" do cap. 18, com a fronteira tornada explícita.

---

## 6. O esqueleto andante: a primeira demanda

### 6.1 Definição

O esqueleto andante (*walking skeleton*, termo de Alistair Cockburn popularizado por Freeman e Pryce em *Growing Object-Oriented Software, Guided by Tests*) é a menor implementação que atravessa todas as camadas do sistema e roda de ponta a ponta, com build, testes e deploy automatizados, antes de qualquer feature real. **[Externo]** Ferramentas recentes para agentes usam a mesma ideia: uma skill descreve o esqueleto como "the thinnest end-to-end slice that touches every layer" e trata todo o resto como trabalho posterior, test-first; outra para depois do esqueleto para revisão humana da forma antes de escrever comportamento.

No harness, o esqueleto é a demanda `GEN-001` e tem um contrato fixo:

| Item da DoD | Comando ou evidência | Check do BF §15.2 que fica verde |
| --- | --- | --- |
| dependências instalam por um comando, com lockfile | `install` | R03 |
| builda ou typechecka | `build` / `typecheck` | R02, R31 |
| um teste de unidade real passa, com JUnit | `test.unit` + relatório | R01, R32 |
| o teste falha quando a asserção é quebrada (6.3) | log da prova vermelho → verde | — (novo, R05) |
| lint e formatter rodam sem erro | `lint` | R30 |
| um caminho de ponta a ponta mínimo funciona (rota `/health`, comando `--version`, tela inicial) | `dev` + `ready`; E2E se houver UI | R36 quando aplicável |
| o CI roda os mesmos comandos | workflow verde no primeiro push | R38 |
| `.gitignore` cobre artefatos e segredos | arquivo + check | R04 |
| AGENTS.md mínimo e perfil com comandos `verified` | `doctor` | R10, R12 |
| `STATE.md` atualizado e commit inicial | arquivo + git log | R22 |

O esqueleto **não** tem domínio. Nenhuma entidade de negócio, nenhuma regra. Ele prova que o loop fecha. As features vêm depois, uma por vez.

### 6.2 Gerador oficial antes do modelo

A estrutura inicial vem do gerador oficial do ecossistema, executado pelo papel `mechanical` (BF §16.5, `fast`) com aprovação da pessoa, porque roda código de terceiros e usa rede (BF §11).

Motivos:

- é a estrutura que a documentação, os tutoriais e os modelos esperam encontrar, o que ajuda a "familiaridade" da seção 5.3;
- é determinística (P8) e não gasta modelo;
- o modelo escrevendo boilerplate é o caso que o cap. 5 manda tirar do modelo: "converter um formato, gerar um esqueleto de arquivo, validar uma estrutura" saem mais baratos por script.

O catálogo fica no generic-harness como dado, no mesmo espírito do catálogo de sugestões (BF §10.1):

```json
{
  "id": "python-uv-app",
  "ecosystem": "python",
  "when": { "adr0002": { "language": "python", "packageManager": "uv" } },
  "generate": { "run": "uv init --app {name}", "interactive": false, "network": true },
  "addons": [
    { "for": "test",      "run": "uv add --dev pytest",  "profile": { "test.unit.run": "uv run pytest --junitxml=.harness/runs/unit.xml" } },
    { "for": "lint",      "run": "uv add --dev ruff",    "profile": { "lint.run": "uv run ruff check .", "lint.fix": "uv run ruff check --fix ." } },
    { "for": "typecheck", "run": "uv add --dev mypy",    "profile": { "typecheck.run": "uv run mypy src" } }
  ],
  "ciTemplate": "github-actions/python-uv.yml",
  "source": "https://docs.astral.sh/uv/",
  "testedVersion": "<a definir no Plan>"
}
```

Geradores candidatos por ecossistema (**flags exatas e modo não interativo a validar no Plan**, como a matriz do BF §5.2):

| Ecossistema | Gerador | Observação |
| --- | --- | --- |
| JS/TS | `npm create vite@latest`, `pnpm create next-app`, `npm init` + `tsc --init` | muitos geradores são interativos; preferir os que aceitam flags |
| Python | `uv init`, `poetry new` | `uv init --app` ou `--lib` |
| Go | `go mod init` | não cria estrutura; o layout vem do ADR-0005 |
| Rust | `cargo new` / `cargo init` | `--bin` ou `--lib` |
| Java/Kotlin | `gradle init`, Spring Initializr (`curl start.spring.io`) | `gradle init` tem modo não interativo |
| .NET | `dotnet new <template>` | templates oficiais por tipo de app |
| Dart/Flutter | `flutter create`, `dart create` | |
| Ruby | `rails new`, `bundle gem` | |
| Elixir | `mix new`, `mix phx.new` | |
| Swift | `swift package init` | |
| PHP | `composer create-project` | |

Quando o ecossistema não tem gerador ou a pessoa não quer um, o `implementer` escreve o esqueleto a partir do ADR-0005, e a DoD continua a mesma.

**O que o gerador traz e não deveria ficar.** Exemplos de demonstração do gerador (contador, página de boas-vindas) não são exemplares canônicos (7.3): o modelo copiaria um padrão que ninguém escolheu. A task do esqueleto remove ou substitui esses arquivos.

### 6.3 O primeiro sensor precisa provar que sente

No brownfield, o comando de teste já existe e o gate só o executa. No greenfield, a task do esqueleto **cria** o comando que vai julgá-la. Um exit 0 nessa situação não prova nada: um runner sem nenhum teste, ou com um teste que nunca falha, também sai com 0.

Regra proposta (check novo **R05**, nível P0):

1. O esqueleto escreve um teste que exercita código real (não `assert True`).
2. O gate roda o comando com uma mutação simples aplicada pelo script (inverter a asserção, ou trocar o valor esperado) e exige **exit ≠ 0** e `failures ≥ 1` no JUnit.
3. Desfaz a mutação, roda de novo e exige **exit 0** e `tests ≥ 1`.
4. Grava as duas execuções em `validation.md`.

É o vermelho → verde do TDD (cap. 12) feito por script, e é a versão mínima do *discrimination sensor* que o HG deixa para a fase 3 (HG §3.2, S10). **[Inferência]** A mutação pode ser genérica o bastante (trocar um literal na asserção marcada) para não depender da linguagem; os detalhes ficam para o Plan.

O mesmo vale, de forma mais leve, para lint e typecheck: o gate injeta um erro conhecido (variável não usada, tipo incompatível) numa cópia e confere que o sensor reclama. Sensor que nunca falhou não provou que funciona (HG §11, pergunta de Böckeler: "um sensor que nunca dispara indica qualidade alta ou detecção fraca?").

### 6.4 Quem executa

| Passo | Executor | Tier |
| --- | --- | --- |
| rodar o gerador e os addons | `mechanical` | `fast` |
| ajustar layout ao ADR-0005, escrever o teste real e o caminho de ponta a ponta | `implementer` | `standard` |
| prova vermelho → verde, `doctor`, contagem JUnit | script | sem modelo |
| conferir a DoD com evidência | `verifier` | `strong`, pinado |
| revisar e comitar | pessoa | — |

Cabe numa janela só (cap. 11: um agente por padrão). Não há motivo para workers paralelos no esqueleto.

---

## 7. Construir o produto pela fábrica

### 7.1 Backlog de features com status

O guia pede uma lista explícita de features com status (cap. 13). O Young mostra o formato (JSON, só o status muda, tudo começa como falhando). O harness propõe `.harness/features.json`, gerado a partir do brief e editado pela pessoa:

```json
{
  "schema": 1,
  "features": [
    { "id": "FEAT-001", "title": "Cliente cria pedido", "epic": "pedidos",
      "priority": "P1", "dependsOn": [], "status": "todo",
      "acceptance": ["WHEN um cliente envia um pedido válido THEN o sistema SHALL registrar e devolver o número"],
      "spec": null }
  ]
}
```

Regras:

- **Só o script muda `status`** (`todo` → `in-spec` → `in-progress` → `done` / `blocked`), pelo mesmo caminho autorizado do `task done` (HG §3.2, S2; proteção a demonstrar em HG §3.7).
- **`acceptance` é curta e de produto**, em WHEN/THEN/SHALL. Os critérios técnicos e as tasks vêm na spec da feature.
- **A spec é escrita na hora** (`spec: null` até a feature entrar em implementação). O auto-sizing do cap. 9 decide Quick Mode, spec breve ou spec completa. A pessoa revisa cada spec (cap. 9: "meia hora de leitura economiza mais").
- **Granularidade:** uma feature cabe numa spec de escopo médio (< 10 tasks, cap. 9). Feature maior vira épico com várias features.

**Divergência a registrar.** O Young expande o pedido em mais de 200 features de uma vez, com os passos de teste de cada uma, porque o objetivo dele é rodar o agente por muitas sessões sem humano. O guia põe a pessoa em cada spec (P10) e manda começar pequeno (cap. 17). **Padrão desta pesquisa:** backlog no nível de feature com critério de produto, spec de cada feature só quando ela for a próxima. O backlog completo no estilo Young fica como modo autônomo da fase 3 (7.4).

Com board externo (Jira, Linear, issues), `features.json` é um espelho: o `triager` (BF §16.5) lê o board e o script atualiza o arquivo. O ID do board vira o ID da feature (P13).

### 7.2 Ordem de construção

1. `GEN-001` esqueleto andante.
2. A **primeira fatia vertical**: a feature P1 mais simples que atravessa as camadas do esqueleto com domínio real. Ela cria os primeiros exemplares canônicos (7.3).
3. Features P1 restantes, em ordem de dependência.
4. Sensores que entram por necessidade observada: E2E na primeira feature com UI (R36), testes de integração na primeira feature com banco, revisores especialistas quando o volume de PR justificar (BF §16.9, fase 2).

O cap. 17 já diz isso: cada peça escolhida precisa resolver uma necessidade concreta. Em greenfield, a necessidade aparece com a feature que a cria.

### 7.3 Exemplares canônicos

O cap. 2 diz que o modelo copia o que vê. Num repo vazio, o que ele vê são as primeiras implementações. Se a primeira rota tiver validação no controller, todas as seguintes terão.

Proposta:

- A primeira feature que cria um **tipo de arquivo** novo (rota, serviço, repositório, componente, migration, teste de integração) marca esses arquivos como **exemplares** no perfil:

  ```json
  "exemplars": [
    { "kind": "http-route", "path": "src/pedidos/api/criar_pedido.py", "since": "FEAT-001" },
    { "kind": "unit-test",  "path": "tests/pedidos/test_criar_pedido.py", "since": "FEAT-001" }
  ]
  ```

- O review dessa feature tem um item a mais: "este arquivo deve ser copiado pelas próximas features?". Se não, corrige antes do merge.
- `docs/agents/code-patterns.md` nasce aqui, curto, apontando para os exemplares com `arquivo:linha` (BF §7.2). É o primeiro doc sob demanda escrito **a partir de código real** e não de intenção.
- Quando um exemplar muda de padrão (refatoração aceita), o perfil e o doc mudam junto; o `doctor` acusa exemplar que aponta para arquivo inexistente.

Isso substitui, em greenfield, a captura de padrões do BF §15.3: lá a pessoa marca candidatos extraídos do legado; aqui a pessoa aprova cada padrão no momento em que ele nasce.

### 7.4 Modo autônomo (fase 3, opcional)

O que Young e Rajasekaran descrevem (cap. 15, Complementos) é um greenfield longo e quase sem humano: o planner expande um pedido curto em spec de produto, o initializer prepara o ambiente, os coding agents fazem uma feature por sessão, um evaluator testa pelo navegador. O custo relatado foi de US$ 200 e 6 horas contra US$ 9 e 20 minutos do agente solo, com o solo entregando algo que não funcionava.

O harness pode suportar isso como **L6** (HG §3.3) depois de ter o fluxo normal funcionando:

- o brief e as decisões de fundação continuam humanos;
- `features.json` completo, gerado pelo `planner` e **revisado pela pessoa antes de rodar**;
- runner headless com orçamento, limites e escalonamento (HG §3.8);
- evaluator com E2E real, nunca só teste de unidade (cap. 13, Teste Fake);
- medição de custo por feature aceita (BF §16.6, regra 7).

Fica fora das fases 0–2.

---

## 8. Transição para brownfield

### 8.1 Critério de saída do greenfield

`project.kind` muda de `greenfield` para `brownfield` quando todos os itens abaixo são verdadeiros (checks computacionais, BF §15.2):

| Check | Por quê |
| --- | --- |
| `GEN-001` concluído com a prova vermelho → verde | os sensores existem e sentem |
| todos os comandos do perfil estão `verified` | nenhum `planned` restante |
| pelo menos uma feature concluída por camada principal do ADR-0005 | há exemplares para o agente copiar |
| nível de prontidão ≥ P2 | o contrato de spec funciona (R20–R25) |
| nenhum ADR de fundação em `proposed` | as decisões que o perfil cita estão aceitas |

**[Inferência]** Os limiares (uma feature por camada, P2) são um ponto de partida; o piloto pode mostrar que três features são o mínimo para os padrões estabilizarem.

### 8.2 O que muda na transição

- O `assess` (BF §15.2) passa a rodar no modo normal, e o histórico de prontidão começa a contar.
- A captura de padrões (BF §15.3) roda uma vez: agora há código suficiente para achar contra-exemplos entre as primeiras features. Divergências entre os exemplares aprovados e o que as features seguintes fizeram viram achados.
- A primeira retro (`harness-retro`) roda sobre todas as features da gênese: erros recorrentes viram regra, exemplo, teste ou sensor (cap. 4; HG G8).
- O ramo greenfield do orquestrador sai de cena. O bloco `project.genesis` do perfil vai para o histórico em `STATE.md`.

### 8.3 Caso híbrido (G3)

Pacote novo num monorepo existente: o perfil do pacote começa greenfield e o raiz continua brownfield. As decisões de fundação do pacote podem herdar ADRs do repo ("mesma linguagem e mesmo CI do resto do monorepo", ADR retroativo curto). Os exemplares do repo raiz servem de ponto de partida, mas a pessoa confirma se valem para o pacote novo.

---

## 9. Encaixe no que já existe

### 9.1 Fluxo de ponta a ponta

É o fluxo do BF §15.7 com o ramo greenfield. Os pontos humanos encerram a sessão, como lá.

```
 dev: "comece este projeto"        (BOOTSTRAP.md → agente)  ou  python3 bootstrap.py prepare
   │
   ▼
 0. CLASSIFICAR ──────── script · G0–G3 ou brownfield (3.1) · runtimes e ferramentas de IA
   │
   ▼
 1. DISCOVERY ────────── orquestrador · questionário curto (5.1) → docs/product/brief.md
   │                     Lean Inception sugerida se porte médio + incerteza alta
   ⏸ pessoa revisa o brief                                              fim da sessão
   ▼
 2. DECISÕES ─────────── por ADR, na ordem da 5.2
   │                     simples: orquestrador redige o ADR, pessoa aceita
   │                     com alternativas: researcher × 3 → synthesizer → RFC (5.3)
   │                     dúvida que o papel não resolve: SPIKE-NNN (5.4)
   ⏸ pessoa aceita os ADRs                                              fim da sessão
   ▼
 3. APLICAR O BÁSICO ─── bootstrap.py apply · estrutura da fábrica (BF §6.2), perfil com
   │                     comandos planned, AGENTS.md mínimo das decisões, adaptadores,
   │                     features.json inicial a partir do brief
   ▼
 4. ESQUELETO ────────── GEN-001 pela fábrica (seção 6) · gerador oficial + addons
   │                     prova vermelho → verde · CI verde · comandos viram verified
   ⏸ pessoa revisa e comita                    ← critério de aceite do bootstrap
   ▼
 5. PRIMEIRA FATIA ───── FEAT P1 mais simples · spec → execute → verify → review
   │                     exemplares canônicos marcados (7.3) · code-patterns.md nasce
   ⏸ pessoa revisa (incluindo "isto deve ser copiado?")
   ▼
 6. FEATURES ─────────── uma por vez, spec just-in-time, sensores entram por necessidade
   │
   ▼
 7. TRANSIÇÃO ────────── critério da 8.1 → kind: brownfield · assess · captura · retro
                         daqui em diante, o fluxo do BF §15.7
```

### 9.2 Skills, papéis e scripts

**Skills.** Nenhuma skill nova. O `harness-prepare` (BF §15.7) detecta `project.kind` e carrega `references/greenfield.md` só nesse caso. Isso mantém as ≤ 6 skills do harness (HG §3.2) e não paga description extra em todo repo brownfield (cap. 5). As skills externas que ajudam aparecem como sugestão (BF §10), pelo critério "a pergunta que responde":

| Pergunta | Sugestão | Guia |
| --- | --- | --- |
| como alinhar escopo e jornadas sem contexto nenhum? | roteiro de Lean Inception | cap. 7 |
| quais termos do domínio vamos usar? | `/domain-modeling` | cap. 18 |
| quais desenhos alternativos existem? | `/code-design` | cap. 18 |
| preciso de um Design Doc para alinhar pessoas? | Technical Design Doc Creator | cap. 7 |
| a API desta lib nova mudou? | Context7 | cap. 4 |
| a tela faz o que a spec diz? | Playwright MCP | caps. 13, 16 |

**Papéis.** Nenhum papel novo no roster do BF §16.5:

| Passo | Papel | Tier |
| --- | --- | --- |
| alternativas de stack e arquitetura | `researcher` × até 3, em paralelo | `strong` |
| RFC a partir das alternativas | `synthesizer` | `strong` |
| ADRs simples e spec do esqueleto | `planner` | `strong` |
| gerador e addons | `mechanical` | `fast` |
| esqueleto e features | `implementer` | `standard` |
| DoD do esqueleto e das features | `verifier` | `strong`, pinado |
| brief a partir de notas ou PRD existentes | `explorer` lê, orquestrador conversa | `fast` |

**[Inferência]** As três alternativas em `strong` custam caro, mas acontecem uma vez por projeto e decidem o que todas as features vão herdar. É o caso "modelo forte onde o erro se multiplica" (BF §16.6, regra 3). Para decisões de menor impacto, um `researcher` só.

**Scripts novos ou estendidos** (Python stdlib, BF §3.3):

| Comando | O que faz |
| --- | --- |
| `bootstrap.py detect` | + classificação G0–G3 e runtimes (3) |
| `bootstrap.py genesis status` | mostra o passo atual, ADRs pendentes, comandos `planned` |
| `bootstrap.py profile from-adrs` | monta ou atualiza o perfil a partir dos blocos estruturados dos ADRs aceitos (D37) |
| `bootstrap.py scaffold <id>` | roda o gerador e os addons do catálogo, com aprovação (6.2) |
| `harness gate --prove-sensor` | prova vermelho → verde (6.3) |
| `harness feature <cmd>` | muda status em `features.json` pelo caminho autorizado (7.1) |
| `bootstrap.py genesis exit` | confere a 8.1 e faz a transição |

### 9.3 Artefatos novos no layout (BF §6.2)

| Artefato | Onde | Regenerável? |
| --- | --- | --- |
| brief | `docs/product/brief.md` | não |
| ADRs de fundação e RFCs | `docs/decisions/` | não |
| glossário | `docs/agents/glossary.md` (já previsto no BF) | não |
| alternativas brutas | `.harness/reports/genesis/alt-<n>.md` | sim |
| backlog | `.harness/features.json` | não (só o status muda por script) |
| spikes | `.harness/intake/SPIKE-NNN.md` + branch | não |
| exemplares | bloco `exemplars` no perfil + `docs/agents/code-patterns.md` | não |
| no generic-harness | `core/catalog/scaffolders/*.json`, `core/templates/{brief,adr-foundation,rfc}.md`, `core/templates/ci/*.yml`, `core/skills/harness-prepare/references/greenfield.md` | — |

### 9.4 Checks de prontidão novos ou ajustados (BF §15.2)

| ID | Check | Tipo | Nível |
| --- | --- | --- | --- |
| R05 | o comando de teste falha com mutação e passa sem ela (6.3) | C | P0 |
| R06 | nenhum comando do perfil em `planned` | C | P0 |
| R18 | decisões de fundação (stack, testes, lint, arquitetura) registradas em ADR aceito | C | P1 |
| R19 | exemplares canônicos declarados para cada tipo de arquivo com mais de uma ocorrência | C | P1 |
| R26 | backlog com status alterado só por script; toda feature `done` tem spec e evidência | C | P2 |

R05 vale também para brownfield: um repo que já tem testes pode ter um runner que nunca falha. **[Proposta ao BF]** incluir R05 no `assess` geral.

---

## 10. Anti-padrões do greenfield

- Pedir ao agente "crie o projeto" e aceitar a stack e a arquitetura que ele escolher. O viés por Python e a taxa de contradição medidos por Twist et al. mostram por quê.
- Escrever o AGENTS.md com convenções que ainda não existem no código ("usamos Clean Architecture") antes do esqueleto e da primeira fatia. Regras de projeto ideal confundem a IA (cap. 2); em greenfield, "ideal" é tudo o que ainda não foi construído.
- Gerar PRD, Design Doc, arquitetura, backlog completo e 200 specs antes da primeira linha de código. É a armadilha do cap. 17 em escala de projeto.
- Deixar o boilerplate de demonstração do gerador como primeiro exemplo de código.
- Considerar o esqueleto pronto com um teste que nunca falha.
- Instalar todos os sensores, revisores e skills no dia 1 "porque o projeto é novo e dá para fazer certo desde o começo". Cada peça entra quando a primeira feature precisar dela (cap. 17).
- Microserviços desde o início "para escalar". O cap. 2 defende monólito modular por domínio para trabalhar com IA.
- Ficar em greenfield para sempre: sem critério de saída, o projeto nunca ganha retro, captura de padrões nem histórico de prontidão.

---

## 11. Riscos

| Risco | Mitigação |
| --- | --- |
| Decisão de stack enviesada pelo modelo | três alternativas com restrições forçadas; critérios fixos no RFC; pessoa decide (5.3) |
| Arquitetura fixada cedo demais com domínio incerto | Lean Inception para incerteza alta (cap. 7); modo spike (5.4); ADR registra o que faria a decisão mudar |
| Gerador oficial muda flags ou vira interativo | catálogo como dado com `testedVersion`; fixture por gerador no Plan; fallback para o `implementer` com a mesma DoD |
| Gerador executa código de terceiros e usa rede | aprovação explícita (BF §11); mostrar o comando antes; registrar versão no inventário |
| O primeiro sensor aprova tudo | prova vermelho → verde obrigatória (R05) |
| Exemplares ruins se replicam | review com item "deve ser copiado?"; `doctor` confere exemplares; captura de padrões na transição |
| Backlog vira especificação waterfall | features com critério de produto curto; spec just-in-time; modo Young só na fase 3 |
| Perfil gerado de ADRs fica dessincronizado da decisão | `profile from-adrs` idempotente; `doctor` compara perfil e blocos dos ADRs |
| Brief vira PRD inventado pela IA | questionário com perguntas; a IA não preenche campo que a pessoa não respondeu; `INCERTO` explícito |
| Custo das alternativas em `strong` | só para decisões que pedem RFC; até 3; uma vez por projeto |
| Greenfield sem critério de fim | transição com checks computacionais (8.1) |

---

## 12. Decisões para o Plan

Continuam abertas D1–D12 (HG §12) e D13–D34 (BF §12). As novas:

| # | Decisão | Opções | Recomendação e motivo |
| --- | --- | --- | --- |
| D35 | Onde mora o fluxo greenfield | skill nova (`harness-genesis`); ramo do `harness-prepare` | **Ramo do `harness-prepare`** com `references/greenfield.md`: não ocupa slot no teto de skills nem paga description em repo brownfield (cap. 5) |
| D36 | Estados novos no perfil | só `detected`/`confirmed`; + `decision:` e `planned`/`verified` | **Acrescentar `decision:<ADR>` como origem e `planned`/`verified` como estado** (4.1). Sem `planned`, o gate não distingue "sensor ainda não existe" de "sensor vermelho" |
| D37 | Perfil a partir de ADRs | bloco estruturado no ADR; extração pelo orquestrador com confirmação | **Bloco estruturado** no fim de cada ADR de fundação: determinístico (P8) e auditável; a extração livre fica como fallback |
| D38 | Formato de ADR | próprio; MADR 4 | **MADR** com a seção extra `profile`, sem fork (BF §15.4 já sugere MADR) |
| D39 | Origem do código inicial | gerador oficial; template próprio por stack (Copier); modelo | **Gerador oficial** via catálogo; template próprio só se o time já tiver um; modelo como fallback com a mesma DoD |
| D40 | Prova do primeiro sensor | só exit 0; vermelho → verde por mutação | **Vermelho → verde** (R05), e estender ao `assess` geral |
| D41 | Backlog | spec de tudo no início; lista de features com spec just-in-time; só board externo | **`features.json` com spec just-in-time**, espelhando o board quando existir (7.1) |
| D42 | Critério de saída do greenfield | manual; checks computacionais | **Checks da 8.1**, com limiares calibrados no piloto |
| D43 | Discovery | só brief; brief + Lean Inception opcional; PRD sempre | **Brief sempre**, Lean Inception sugerida por porte e incerteza, PRD e Design Doc pela tabela do cap. 7 |
| D44 | Modo autônomo à la Young | fase 0; fase 3; nunca | **Fase 3**, como L6, com brief e decisões humanos e revisão do backlog antes de rodar |
| D45 | Piloto greenfield (refina D21 do BF) | nenhum; um greenfield além dos dois brownfield | **Um greenfield G0** numa stack diferente dos pilotos brownfield. É o caminho com menos conflitos e exercita o que o BF não exercita: decisões, gerador, prova do sensor, exemplares e transição |

---

## 13. Roadmap: o que o greenfield acrescenta às fases

Mesma régua do HG §9 e do BF §13: uma fase só começa quando a anterior passou no critério.

| Fase | Acréscimo | Critério de saída adicional (sim/não) |
| --- | --- | --- |
| 0 | classificação G0–G3; brief e templates de ADR de fundação; origens e estados novos no perfil; `scaffold` com os geradores da stack do piloto; esqueleto `GEN-001` com prova vermelho → verde; gate com "sensor ausente" | No piloto G0, o bootstrap termina com o esqueleto aceito: CI verde, comandos `verified`, R05 verde, e uma tentativa de concluir uma task antes do esqueleto é bloqueada por sensor ausente |
| 1 | Design It Twice com `researcher` × 3 e RFC; `profile from-adrs`; `features.json` com status por script; exemplares canônicos e `code-patterns.md`; transição para brownfield; catálogo com geradores de ≥ 3 ecossistemas | No piloto G0, a primeira fatia vertical termina com exemplares declarados, e a transição acontece pelos checks da 8.1 sem edição manual do perfil. Fixtures de ≥ 3 geradores produzem esqueletos que passam no R05 |
| 2 | modo spike; caso híbrido G3; integração do backlog com board via `triager`; escolha da camada de spec na gênese ligada ao adaptador (BF §15.5) | Num monorepo, um pacote novo passa pela gênese sem alterar o perfil raiz; um spike termina com anexo no RFC e branch descartada |
| 3 | modo autônomo (7.4) com runner L6; ablação: com e sem exemplares canônicos, com e sem prova do sensor | Uma probe compara features construídas com e sem exemplares canônicos em aderência ao padrão e custo por feature aceita |

---

## Apêndice: fontes

### Locais

- *IA First Dev: Agentes, Loops e Harness* (`ia-first-dev.pdf`, out/2026). Capítulos usados: 2 (codebase é contexto, organização por domínio, exemplos, legado), 4 (AGENTS.md iterativo, Ap. A checklist), 5 (tirar do modelo o que é determinístico), 7 (Discovery, documentos por tamanho de time, Lean Inception, RFC e ADR), 9 (auto-sizing, spec, RPI), 11 (um agente por padrão), 12 (fase red), 13 (o código precisa permitir o harness; lista de features com status), 15 (Complementos de Young e Rajasekaran), 17 (playbook e armadilha da infraestrutura), 18 (Design It Twice, `/domain-modeling`, `/code-design`).
- [Harness genérico: pesquisa](harness-generico.md) (HG).
- [Bootstrap de fábrica de agentes em qualquer repositório](bootstrap-fabrica-de-agentes.md) (BF).

### Externas (consultadas em 29/10/2026)

Harnessability e greenfield:

- Birgitta Böckeler, *Harness engineering for coding agent users* (citações sobre greenfield, harnessability e harness templates): https://martinfowler.com/articles/harness-engineering.html
- Justin Young (Anthropic), *Effective harnesses for long-running agents* (initializer agent, `init.sh`, progresso, feature list em JSON, commit inicial): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- agentpatterns.ai, *Agent-driven greenfield* (quando encaixa e quando não; pilha mínima; opinião de praticante, não estudo): https://agentpatterns.ai/workflows/agent-driven-greenfield/

Stack e desempenho de agentes:

- Mündler et al., *Type-Constrained Code Generation with Language Models* (PLDI 2025; 94% dos erros de compilação em TypeScript gerado são de tipo): https://arxiv.org/abs/2504.09246
- Wu, Anderson e Guha, *The Best Programming Language for Tokenmaxxing* (2026, preprint): https://www.khoury.northeastern.edu/~arjunguha/main/papers/wu-tokenmaxxing.html · https://www.alphaxiv.org/abs/2607.22807
- Twist et al., *LLMs Love Python: A Study of LLMs' Bias for Programming Languages and Libraries* (arXiv 2503.17181; números vistos em trechos e resumos, conferir no corpo do artigo): https://arxiv.org/abs/2503.17181
- Avaliação de Dan Luu sobre linguagens e agentes, **só em cobertura secundária** (original não localizado): https://zeli.app/en/story/49245936
- GitHub Octoverse 2025 e o número de 94%, **só em cobertura secundária**: https://atmarkit.itmedia.co.jp/ait/articles/2602/05/news054.html

Frameworks de spec e greenfield:

- GitHub Spec Kit, caminhos de desenvolvimento (0-to-1, Creative Exploration, Brownfield): https://github.github.com/spec-kit/history.html · issue sobre templates genéricos em brownfield: https://github.com/github/spec-kit/issues/1436
- OpenSpec ("built for brownfield not just greenfield"; `specs/` vazio no `init` e crescendo a cada arquivamento): https://github.com/Fission-AI/OpenSpec · https://glukhov.org/ai-devtools/openspec/
- BMAD, trilhas Quick Flow, BMad Method e Enterprise, com PRD e arquitetura no greenfield (fontes secundárias e espelhos da doc; versões divergem): https://docs.bmad-method.org/llms-full.txt · https://www.augmentcode.com/guides/bmad-method-ai-development

Esqueleto andante:

- Skill *atelier-greenfield* (definição de walking skeleton para agentes; listagem de terceiros, sem avaliação): https://skillselion.com/skills/vdelacou/atelier/atelier-greenfield
- *pi-topdown-kit* (esqueleto de stubs com revisão humana antes do comportamento): https://cdn.jsdelivr.net/gh/yinloo-ola/pi-topdown-kit@main/README.md
- Origem do termo: Alistair Cockburn; Freeman e Pryce, *Growing Object-Oriented Software, Guided by Tests* (2009). Referência de conhecimento geral, não consultada nesta pesquisa.

Não verificado nesta pesquisa e pendente para o Plan: flags não interativas e saída de cada gerador da tabela 6.2; se o MADR 4 aceita a seção `profile` sem quebrar ferramentas que o leem; o artigo completo de Twist et al. e o de Wu et al. (números por linguagem); a fonte original da avaliação de Dan Luu; o fluxo greenfield atual do BMAD v6 na doc oficial; e se o Kiro gera steering para projeto vazio (a busca não retornou fonte útil).
