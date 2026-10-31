# generic-harness

Harness externo, genérico e vendorizável para agentes de código: núcleo + adaptadores + perfil do projeto (HG §1.4).

## BOUNDARIES

**SEMPRE**
- Rode `python -m pytest` e deixe verde antes de dar a trilha por terminada.
- Justifique cada decisão com o guia (`ia-first-dev.pdf`, "cap. N") ou com a pesquisa (HG/BF/GF §). Marque fontes de fora como **[Externo]**.
- Escreva docs e mensagens para o agente em pt-BR. Toda mensagem de bloqueio diz o que falhou, por quê e o que fazer no lugar (P15).

**PERGUNTE ANTES**
- Mudar um schema, um código de saída, um subcomando ou o contrato de hook → registre em `docs/plan/contract-changes.md` e espere a aprovação.
- Adicionar uma dependência de desenvolvimento ao `pyproject.toml`.
- Mudar uma ADR com `status: accepted` → crie uma nova ADR que a substitua.

**NUNCA**
- Importar fora da stdlib em `core/` ou `adapters/` → use só a biblioteca padrão; o teste `test_stdlib_only` cobra (ADR-0004).
- Editar o diretório de outra trilha na sua branch → use o contrato e um stub (plano §2.1).
- Anunciar uma garantia de enforcement sem teste que a demonstre → declare o limite na tabela da ADR-0003.
- Gerar conteúdo de AGENTS.md do hospedeiro (paths, convenções) → entregue esqueleto com TODOs (cap. 4).

## Comandos

| O quê | Comando |
| --- | --- |
| ambiente de dev | `python3 -m venv .venv && .venv/bin/pip install pytest jsonschema` |
| testes (é o gate até a Etapa 1 terminar) | `.venv/bin/python -m pytest` |
| validar um arquivo contra um schema | `python3 bootstrap.py validate <schema> <arquivo>` |
| CLI | `python3 bootstrap.py [--json] <comando>` |

## Onde ler

| Fazendo | Leia |
| --- | --- |
| qualquer coisa | `docs/plan/plano-de-construcao.md` (etapas, trilhas, donos de diretório) |
| mexendo em JSON do hospedeiro | `core/schemas/*.schema.json` e `core/schemas/examples/` |
| subcomando novo ou alterado | `docs/contracts/cli.md` |
| hook ou adaptador | `docs/contracts/hooks.md` e `docs/plan/etapa-0/claude-code-facts.md` |
| catálogo (readiness, scaffolder, sugestão) | `docs/contracts/catalogs.md` |
| decisão já tomada | `docs/decisions/` |
| porquê de um componente | `docs/research/harness-generico.md` (HG), depois BF e GF |

## Workflow

1. Uma trilha, uma worktree, uma branch `etapa-N/<trilha>` (plano §2.2).
2. Spec curta em `docs/plan/etapa-N/<trilha>.md`; implementação numa janela nova.
3. Implementar um subcomando = criar o módulo que `COMMANDS` aponta em `core/cli/harness.py`, com `run(args) -> Result`.
4. Contrato errado? Pare e registre em `docs/plan/contract-changes.md` (plano §2.3).
5. Dados de exemplo: um válido e um inválido por regra nova, em `core/schemas/examples/<schema>/`.
