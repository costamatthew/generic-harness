---
status: proposed   # proposed | accepted | rejected | superseded by ADR-NNNN
date: AAAA-MM-DD
deciders: <pessoas>
---

# NNNN <decisão em uma frase>

## Contexto e problema

<o que força a decisão; cite o guia como "cap. N" e as pesquisas como HG/BF/GF §>

## Opções consideradas

1. <opção>
2. <opção>

## Decisão

<opção escolhida e motivo>

## Consequências

- Bom: <...>
- Ruim: <...>
- Como verificar: <teste, check ou critério que mostra que a decisão está valendo>

<!-- ADR de fundação de um hospedeiro greenfield (GF §4.3, D37/D38): acrescente no fim
## Profile
```json
{ "commands": { "test": { "unit": { "run": "...", "report": "..." } } } }
```
O bloco é lido por `harness profile from-adrs` e entra no perfil com origin "decision:ADR-NNNN" e status "planned". -->
