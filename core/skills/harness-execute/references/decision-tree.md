# Árvore de decisão: onde fazer o trabalho (cap. 11)

Use ao decidir se uma etapa fica na janela principal, vai para um `explorer` ou para um worker. Fonte: cap. 11 do guia (contexto é recurso escasso; delegue leitura em massa, não decisão).

```
A etapa precisa de leitura de muitos arquivos (> ~5) ou de saída longa, só para responder uma pergunta?
├─ sim → explorer (somente leitura). Peça síntese com arquivo:linha, nunca o conteúdo cru.
└─ não → ela edita código da task atual?
        ├─ sim → faça na janela principal (você é o implementer).
        └─ não → é a verificação do resultado?
                ├─ sim → harness-verifier, com contexto limpo (passo 5 do L1).
                └─ não → faça na janela principal e mantenha curto.
```

## Limites da Etapa 1

- Só o loop L1. **Não há workers**: se a tarefa pede paralelismo, registre um blocker (`harness task block <ID> --reason "precisa de worker (Etapa 3+)"`) em vez de simular.
- Profundidade máxima 1: o verifier e o explorer não chamam outros subagentes. Se um deles precisar, ele devolve o pedido e você decide.
- O verifier e o explorer são somente leitura (`readonly: true`).
- Não passe `model` ao chamar um papel: o perfil define o modelo (D31).
