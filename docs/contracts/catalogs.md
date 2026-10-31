# Formato dos catálogos v0

> Entrega 0.6 do [plano](../plan/plano-de-construcao.md). O catálogo é dado, não código: ele cresce sem mudar o código que o lê (HG P3; BF §10.1).

| Catálogo | Onde | Schema | Exemplo | Trilha que preenche |
| --- | --- | --- | --- | --- |
| Checks de prontidão | `core/catalog/readiness/<id>.json` | [readiness-check](../../core/schemas/readiness-check.schema.json) | [R12](../../core/schemas/examples/readiness-check/valid-r12.json) | 2F |
| Scaffolders | `core/catalog/scaffolders/<id>.json` | [scaffolder](../../core/schemas/scaffolder.schema.json) | [python-uv-app](../../core/schemas/examples/scaffolder/valid-python-uv.json) | 2E, 3E |
| Sugestões | `core/catalog/suggestions/<id>.json` | [suggestion](../../core/schemas/suggestion.schema.json) | [mcp-playwright](../../core/schemas/examples/suggestion/valid-mcp-playwright.json) | 5U (fase 0: só itens citados no guia, D20) |

Regras comuns:

- **Um arquivo por entrada**, com o nome igual ao `id`. Isso evita conflito de merge entre trilhas.
- Todo arquivo de catálogo passa por `harness validate <schema> <arquivo>`. A trilha dona acrescenta um teste que valida o diretório inteiro.
- **Check de prontidão:** `check` nomeia uma função determinística em `core/cli/assess/checks/<check>.py` (trilha 2F). `kind: inferential` ou `mixed` exige `role`, o papel que gera o achado, e esse achado **não muda o nível** (D23). `appliesWhen` falso significa "não aplicável": o check é pulado e declarado no relatório.
- **Scaffolder:** só entram geradores com modo não interativo (`interactive: false`). Os valores de `profile` dos addons entram no perfil com `status: planned` e `origin: decision:<ADR>`, e só viram `verified` depois que o esqueleto roda (GF §4.1). `testedVersion` é obrigatório: um scaffolder nunca testado não entra no catálogo.
- **Sugestão:** o harness nunca instala. `trust` é obrigatório, e "não auditado" aparece em destaque no relatório (BF §10.1).
