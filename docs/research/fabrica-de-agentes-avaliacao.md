# O harness genérico e o guia correspondem a uma fábrica de agentes?

Pesquisa realizada em **25/10/2026**. Escopo: avaliação documental e consulta a fontes primárias externas. Nenhuma implementação, instalação de harness ou alteração dos documentos analisados foi realizada.

## Resposta direta

**Os dois materiais oferecem uma base consistente para uma fábrica de software operada por agentes, mas não especificam uma fábrica completa de criação e operação de agentes como produtos.** Também não demonstram, por si só, que exista uma fábrica funcionando.

O nome mais preciso para o estágio documentado é **“proposta de harness genérico para desenvolvimento de software com agentes”**. “Base de uma fábrica de software com agentes” também descreve bem a direção. Chamar simplesmente de “Fábrica de Agentes” exige explicar qual produto essa fábrica entrega.

| Pergunta | Avaliação |
| --- | --- |
| Tem conteúdo relevante para uma fábrica? | **Sim.** Contexto, procedimentos reutilizáveis, papéis, orquestração, memória, verificação, intervenção humana e avaliação. |
| Tem requisitos para uma fábrica de software com agentes? | **Boa parte do núcleo técnico está proposta.** Faltam detalhamento operacional e demonstrações de execução repetível. |
| Tem requisitos suficientes para criar, publicar e operar agentes de diferentes domínios? | **Não.** O produto central continua sendo código/feature/PR; falta o ciclo de vida do agente entregue. |
| Já pode ser considerada uma fábrica operacional? | **Não é possível concluir pelos documentos.** Arquitetura e roadmap não equivalem a capacidade implementada e validada. |

## 1. O significado de “fábrica” muda a resposta

As fontes consultadas usam o termo em sentidos diferentes. Esta pesquisa não encontrou nelas uma definição normativa única nem um checklist universal de certificação. Os critérios abaixo são uma **síntese analítica**, não uma norma de mercado.

**Fábrica que coordena agentes para produzir resultados.** A IBM Research chama de *agent factory* um ciclo coordenado de exploração: um coordenador distribui trabalho a agentes, verificadores conferem os resultados e o feedback orienta novas rodadas dentro de um orçamento. O produto do exemplo é uma melhoria de hardware. Isso mostra que o termo também pode designar uma organização produtiva de agentes, sem exigir que o produto final seja outro agente. [IBM Research, 13/10/2026](https://research.ibm.com/blog/open-agent-factories-and-distributed-inference-for-chip-design).

O artigo associado à linha de pesquisa descreve um pipeline que constrói e coordena agentes de otimização especializados. Portanto, instanciar e coordenar trabalhadores especializados é um uso técnico existente de “fábrica”, embora aquele estudo não estabeleça requisitos universais. [Bhandwaldar et al., *Agent Factories for High Level Synthesis*, 2026](https://arxiv.org/abs/2603.25719).

**Fábrica que entrega agentes como produtos.** Para avaliar esse sentido, é útil a orientação de ciclo de vida da Microsoft: entrada de demanda, triagem, construção, implantação, monitoramento, melhoria e desativação. A orientação exige responsável, acompanhamento e um caminho de melhoria ou encerramento para cada agente. [Microsoft Learn, *Manage the agent lifecycle*](https://learn.microsoft.com/en-us/agents/center-of-excellence/agent-lifecycle).

**Harness.** É a infraestrutura que torna a execução de um agente mais confiável. A Anthropic exemplifica essa camada com preparação do ambiente, progresso incremental e artefatos que permitem continuar o trabalho entre sessões. Isso sustenta a função do harness, mas não transforma automaticamente seu pacote numa fábrica com gestão de produtos. [Anthropic, *Effective harnesses for long-running agents*](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents).

A diferença prática é a unidade de entrega:

| Interpretação | Entrada | Saída principal | Encaixe dos materiais |
| --- | --- | --- | --- |
| Harness de desenvolvimento | Projeto, regras e tarefa | Ambiente e loop de execução verificável | Direto e explícito |
| Fábrica de software com agentes | Demanda de software | Código, testes, evidências e PR | Forte alinhamento conceitual |
| Fábrica de agentes como produtos | Necessidade de um agente | Agente versionado, avaliado, disponibilizado e acompanhado | Cobertura parcial; ampliação de escopo |

## 2. O que os documentos realmente propõem

### O guia fornece a metodologia

O [PDF](../../ia-first-dev.pdf), com 129 páginas, explicita no capítulo 1, página 5, a prioridade de ser usuário de agentes existentes antes de construir novos agentes. Os capítulos seguintes desenvolvem esse objetivo:

| Evidência no guia | Contribuição |
| --- | --- |
| Caps. 4–6, pp. 20–35 | Regras, skills, ferramentas, MCP e contexto externo. |
| Caps. 7–9, pp. 37–52 | Discovery, planejamento, pesquisa, especificação e tarefas verificáveis. |
| Cap. 11, pp. 61–68 | Delegação orientada por contexto e acoplamento. |
| Cap. 12, pp. 69–75 | Implementar, testar e corrigir; integridade dos testes e gates. |
| Cap. 13, pp. 76–81 | Guides, sensors, memória e separação Planner → Generator → Evaluator. |
| Cap. 14, pp. 82–88 | Especialistas de review, rastreabilidade e decisão humana. |
| Cap. 15, pp. 89–99 | Avaliação com baseline, evidência, múltiplas execuções e introdução a Loop Engineering. |
| Cap. 17, pp. 105–108 | Primeiro percurso verificável e prevenção de excesso de infraestrutura. |

O guia não se apresenta como especificação de uma plataforma de criação de agentes. A busca textual integral não encontrou “fábrica” nem “factory”; isso é uma observação auxiliar, não a razão da classificação. A razão está no fluxo e no produto descritos.

### A pesquisa transforma a metodologia em uma proposta de produto

O [harness-generico.md](harness-generico.md) se identifica como **Research**, entrada para uma futura fase de Plan. Embora contenha arquitetura e roadmap, ainda não é uma especificação final aprovada nem prova de implementação.

Seu princípio P1, na seção 2, define expressamente: **“Construa o harness externo, não um agente.”** A seção 1.4 propõe núcleo genérico, adaptadores e perfil do projeto. A seção 6 descreve uma feature percorrendo especificação, implementação, testes, verificação e review. É uma linha de produção de mudanças de software.

Há geração de configurações e definição de papéis especializados. Isso pode ser entendido como montagem de agentes de desenvolvimento dentro de um escopo restrito. Porém, o catálogo da seção 3.2 é de componentes do harness; não equivale a um inventário de agentes entregues a usuários, com responsáveis e ciclo de vida próprio.

O fluxo L6 e a fase 3 já preveem disparo por agenda/evento, execução headless, worktrees, orçamento e escalonamento. **Não seria correto dizer que falta qualquer automação de operação.** Ela está prevista, mas ainda não detalhada e comprovada como serviço operacional.

## 3. Matriz de cobertura dos requisitos

“Previsto” significa descrito nos documentos, sem afirmar implementação. “Parcial” significa que há mecanismos relacionados, mas não um contrato completo para o sentido de fábrica avaliado. “Não especificado” significa que não foi encontrada definição suficiente nos materiais, não impossibilidade técnica.

| Capacidade | Situação documental | Evidência e limite |
| --- | --- | --- |
| Contrato de entrada e aceite | Previsto para software | Research §§3.1, 5–6; guia caps. 7–9. Specs e DoD, sem intake específico de produtos agentes. |
| Reuso e padronização | Previsto | Núcleo, skills, templates e presets; research §§1.4, 3.1–3.2 e 8. |
| Composição de papéis | Previsto para desenvolvimento | Planner, implementer, verifier, reviewers e judge; research §§3.1–3.3. |
| Orquestração e delegação | Previsto | Dependências, limites de workers e loops L1–L6; research §§3.3 e 3.6. |
| Memória e retomada | Previsto em arquivos | STATE.md, tasks.json e bootstrap; research §3.2. Recuperação transacional após falhas não está detalhada. |
| Verificação da entrega | Previsto | Gate, test guard, avaliação separada e evidência; research §§3.2, 3.5 e 7. |
| Avaliação do sistema agêntico | Previsto para o harness | Fixtures, baseline, múltiplos runs e ablação; research §7. Não há suíte por agente de domínio entregue. |
| Permissões e supervisão | Parcial | Boundaries, hooks, deny/ask e decisões humanas; research §§3.1–3.2 e 11. A resistência a contornos precisa ser demonstrada. |
| Versionamento e distribuição | Previsto para o harness | Adaptadores, cópias, lockfile e atualização; research §§4.2–4.3. Não cobre sozinho releases de agentes-produto. |
| Operação automática | Parcial, fase futura | L6 e fase 3; faltam contratos para fila, duplicidade de eventos, falhas e cancelamento. |
| Observabilidade e custo | Parcial | Logs, tokens, tempo, correções e intervenções; research §§4.4 e 7. Não há operação completa por agente com alertas e metas de serviço. |
| Definição versionada de cada agente-produto | Não especificado de forma completa | `profile.json` descreve o projeto hospedeiro, não identidade, proprietário, interfaces e release de cada agente entregue. |
| Inventário e gestão de agentes entregues | Não especificado | Não há registro de proprietário, consumidores, versão ativa, ambiente e estado de ciclo de vida. |
| Implantação, reversão e desativação de agentes | Não especificado | Instalar o harness no repositório e subir o ambiente de desenvolvimento não equivalem a essas operações. |
| Demonstração de repetibilidade e valor | Critérios propostos; resultados não apresentados | Research §9 exige piloto e benchmark, mas não fornece resultados dessas execuções. |

**Leitura da matriz:** a cobertura é forte para instrumentação do desenvolvimento. A lacuna mais importante para uma fábrica de agentes-produto é fazer do próprio agente uma unidade especificada, entregue e mantida.

## 4. Garantias que ainda precisam ser demonstradas

Os pontos seguintes são **inferências técnicas desta análise sobre o desenho**, não falhas observadas numa implementação existente.

1. **Negar Write/Edit não demonstra que só o script altera o estado.** A proposta protege JSON por ferramentas de edição, mas um executor com shell e acesso de escrita pode oferecer outros caminhos. Seria preciso demonstrar a separação de permissões e a proteção dos scripts, configuração, baselines e evidências que decidem o aceite. Da mesma forma, `shell:<glob>` não prova cobertura de todas as formas equivalentes de executar uma ação.
2. **Contagem JUnit não prova integridade semântica dos testes.** Apagar um teste e incluir outro pode manter a contagem. Congelar arquivos ajuda depois do congelamento, mas não prova que o teste inicial valida o requisito correto. A proposta já reconhece parte disso ao prever discrimination sensor, revisão e evidência.
3. **Gates verdes dependem da qualidade e da procedência da prova.** Além de associar o resultado à árvore, seria necessário definir como entram versões do perfil, comandos, testes, ambiente e artefatos. Um relatório antigo ou modificado não deve servir de prova de uma execução nova.
4. **Contexto limpo e modelo fixo não tornam o juiz determinístico.** O próprio guia explica isso no cap. 15, p. 89. A separação reduz contaminação; a confiabilidade ainda depende de critérios, calibração e comparação com avaliações humanas.
5. **Logs locais não resolvem sozinhos a retenção de evidências.** A seção 8.2 deixa `runs/` fora do Git, e o ciclo de specs prevê remoção após o uso. Isso pode ser adequado, desde que uma operação que precise de auditoria defina onde ficam evidências, por quanto tempo e como são vinculadas à entrega.
6. **Um runner agendado precisa de comportamento definido diante de falhas.** Reinício, repetição de eventos, timeout, esgotamento de orçamento e conflitos entre workers precisam ter resultados previsíveis. A fase 3 menciona o runner, mas ainda não fornece esses contratos.

A literatura de avaliação também distingue desempenho do modelo de desempenho do conjunto modelo+harness, recomenda isolamento das tentativas e inspeção dos registros. Isso reforça a necessidade de validar o sistema real, não apenas sua descrição. [Anthropic, *Demystifying evals for AI agents*](https://www.anthropic.com/research/demystifying-evals-for-ai-agents).

## 5. O que faltaria para cada objetivo

Os itens abaixo são critérios propostos por esta pesquisa para orientar uma futura decisão. **Não são um plano de implementação autorizado.**

### Para uma fábrica de software operada por agentes

O escopo atual pode ser preservado. O passo decisivo seria demonstrar que seu processo funciona repetidamente, incluindo falhas:

- Uma demanda real percorre spec, implementação, gate, avaliação e entrega com evidências vinculadas à mesma revisão.
- Uma execução interrompida retoma de estado conhecido; um bloqueio não vira conclusão fictícia.
- Tentativas de contornar gates ou adulterar evidências são detectadas nos caminhos suportados.
- Limites de tempo, tentativas e custo são aplicados, com responsável definido para escalonamento.
- Execuções repetidas permitem medir qualidade, custo por entrega aceita, retrabalho e intervenção humana.

O roadmap existente já contém parte dessas provas. Com elas, seria defensável descrever o resultado como **fábrica de software com agentes, de escopo delimitado**, mesmo com acionamento e aprovação humanos. Autonomia total, grande quantidade de workers e infraestrutura empresarial não são pré-requisitos universais.

### Para uma fábrica que cria e opera agentes como produtos

Além do núcleo atual, seria necessário definir:

| Complemento | Evidência de aceite sugerida |
| --- | --- |
| Contrato do agente | Cada agente tem identidade, versão, objetivo, responsável, interfaces, ferramentas, dados permitidos e limites de atuação definidos. |
| Processo de composição | Um novo agente pode ser montado a partir de componentes reutilizáveis, mantendo explícitas as decisões específicas do domínio. |
| Avaliação por agente | Cenários de tarefa, falha de ferramenta e abuso relevante verificam o comportamento do agente; testes do código do harness não substituem isso. |
| Registro de releases | É possível identificar exatamente qual combinação de código, instruções, modelo, ferramentas e configuração está ativa. |
| Publicação e reversão | Um release aprovado é disponibilizado no ambiente escolhido; regressões permitem voltar a uma versão conhecida. |
| Operação e encerramento | Há acompanhamento de sucesso, falhas, latência e custo, além de suspensão e revogação dos acessos quando o agente é retirado. |

Uma evidência prática forte seria entregar **dois agentes com objetivos distintos** pelo mesmo processo e atualizar um deles sem alterar indevidamente o outro. Esse número é uma proposta de demonstração de reuso, não uma exigência da literatura.

Não é necessário treinar um modelo, criar um framework próprio, usar Kubernetes, oferecer interface visual ou implementar multi-tenancy para justificar o termo num escopo pequeno. Essas escolhas dependem dos consumidores e da operação pretendida. O essencial é um processo repetível e verificável para o produto prometido.

## 6. Parecer final e limites

**O conteúdo existe em grande parte; a suficiência dos requisitos depende do que a fábrica pretende produzir.** Para produzir software com agentes, os materiais são uma base técnica bem alinhada e já propõem muitos dos requisitos centrais. Para produzir agentes como produtos mantidos em operação, ainda faltam contratos e processos importantes.

Renomear o projeto não fecha essas lacunas. A classificação mais defensável hoje é **harness genérico em fase de pesquisa, com potencial para sustentar uma fábrica de software operada por agentes**. A evolução para uma fábrica de agentes-produto seria uma decisão adicional de escopo.

Esta pesquisa avaliou os dois documentos, com leitura dirigida dos capítulos relevantes do PDF e busca textual integral. Não executou o roadmap, não auditou uma implementação e não revalidou toda a matriz de compatibilidade entre ferramentas da pesquisa anterior. As capacidades mencionadas ali como não verificadas continuam sendo hipóteses para validação futura. Percentuais de prontidão não foram atribuídos porque os requisitos têm pesos e escopos diferentes.

## Fontes consultadas

Fontes locais:

- [Harness genérico: pesquisa](harness-generico.md), 22/10/2026. Referências por seção ao longo da avaliação.
- [IA First Dev: Agentes, Loops e Harness](../../ia-first-dev.pdf), outubro de 2026. Referências por capítulo e página do PDF.

Fontes externas primárias, consultadas em 25/10/2026:

- [IBM Research — Making AI-driven chip design affordable with open agent factories and distributed inference at scale](https://research.ibm.com/blog/open-agent-factories-and-distributed-inference-for-chip-design), 13/10/2026. Uso técnico do termo para coordenação e verificação de trabalho agêntico.
- [Bhandwaldar et al. — Agent Factories for High Level Synthesis](https://arxiv.org/abs/2603.25719), submetido em 26/03/2026, revisão em 01/05/2026. Pipeline especializado de construção e coordenação de agentes.
- [Microsoft Learn — Manage the agent lifecycle](https://learn.microsoft.com/en-us/agents/center-of-excellence/agent-lifecycle). Referência para tratar agentes como produtos ao longo de sua operação.
- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents), 26/11/2025. Papel do ambiente e da continuidade entre sessões.
- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), 09/01/2026. Avaliação do conjunto modelo+harness e limites das evidências.
