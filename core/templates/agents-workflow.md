## Workflow

1. Uma task por vez; execute com a skill `harness-execute` (loop: implementar → gate → verificar → concluir).
2. `harness gate <ID>` roda a DoD da task; corrija até ficar verde.
3. `harness task done <ID>` conclui só com gate verde na árvore atual; sem isso, `harness task block <ID> --reason "<motivo>"`.
4. `harness state --handoff "<texto>"` registra o handoff.
5. Nunca edite `tasks.json` nem `.harness/runs/`; só o CLI escreve evidência.
