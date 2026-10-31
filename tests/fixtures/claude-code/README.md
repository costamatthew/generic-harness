# Fixtures do Claude Code (hook/v0)

Pares `<caso>.native.json` (stdin do Claude Code, formato de docs/plan/etapa-0/claude-code-facts.md) e
`<caso>.neutral.json` (o evento neutro que o adaptador da trilha 1C precisa produzir).
O `projectDir` vem de `CLAUDE_PROJECT_DIR`, que não está no stdin: nos testes, use o `cwd` do
caso `pre_tool_write` (`/home/dev/pedidos`) ou `C:\dev\pedidos` no caso Windows.
Caminhos saem relativos a `projectDir`, com `/`.
