# Mudanças de contrato

> Procedimento do [plano §2.3](plano-de-construcao.md#23-mudança-de-contrato-durante-uma-etapa): a trilha para, registra aqui, a pessoa aprova, o schema sobe de versão num commit isolado (com exemplo e fixture), e as outras trilhas fazem rebase.

Contratos sob este procedimento: os schemas em `core/schemas/`, a tabela `COMMANDS` e os códigos de saída de `core/cli/harness.py`, o contrato `hook/v0` ([hooks.md](../contracts/hooks.md)) e o formato dos catálogos ([catalogs.md](../contracts/catalogs.md)).

Os contratos v0 são provisórios até a integração 1I (plano §10). Mesmo assim, cada mudança passa por aqui.

## Formato

```markdown
### CC-NNN <título>
- Trilha: <ID> · Data: AAAA-MM-DD · Status: proposta | aprovada | rejeitada
- Contrato: <schema ou documento>
- Problema: <o que a trilha descobriu, com arquivo:linha>
- Proposta: <diff do contrato>
- Impacto: <trilhas que precisam de rebase>
```

## Registro

Nenhuma mudança até agora.
