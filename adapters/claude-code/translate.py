"""Claude Code ↔ hook/v0 (passos 1 e 3 de docs/contracts/hooks.md).

`to_neutral` lê o JSON nativo do stdin e produz o `hook-event`; `to_native`
transforma o `hook-result` em (exit, stdout, stderr) nativos. Só stdlib.
Fatos: docs/plan/etapa-0/claude-code-facts.md; provados em docs/plan/etapa-1/1C-probe.md.
"""

from __future__ import annotations

import json
import os
import re
import subprocess

TOOL = "claude-code"

EVENTS = {
    "PreToolUse": "pre_tool",
    "PostToolUse": "post_edit",
    "Stop": "stop",
    "SubagentStop": "stop",
    "SessionStart": "session_start",
    "PreCompact": "pre_compact",
}
SHELL_TOOLS = {"Bash", "PowerShell"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob"}
SESSION_REASONS = {"startup", "resume", "clear", "compact", "fork"}
# additionalContext só é aceito nestes eventos nativos (fatos §1).
CONTEXT_EVENTS = {"session_start": "SessionStart", "post_edit": "PostToolUse"}

_DRIVE = re.compile(r"^[A-Za-z]:/")


def norm(path: str) -> str:
    """Barras normais e sem '/' final (exceto a raiz)."""
    out = path.replace("\\", "/")
    return out.rstrip("/") if len(out) > 1 and not out.endswith(":/") else out


def project_root(cwd: str) -> str:
    """Raiz da worktree a partir do `cwd`, nunca de CLAUDE_PROJECT_DIR (fatos §6)."""
    try:
        proc = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, encoding="utf-8", timeout=10)
        top = proc.stdout.strip()
        if proc.returncode == 0 and top:
            return norm(top)
    except (OSError, subprocess.SubprocessError):
        pass
    return norm(cwd)


def relativize(path: str, project_dir: str) -> str:
    """Caminho absoluto dentro do projeto vira relativo, sempre com '/'."""
    p = norm(path)
    root = norm(project_dir)
    absolute = p.startswith("/") or bool(_DRIVE.match(p))
    if not absolute:
        return p[2:] if p.startswith("./") else p
    windows = bool(_DRIVE.match(root))
    a, b = (p.lower(), root.lower()) if windows else (p, root)
    if a == b:
        return "."
    if a.startswith(b.rstrip("/") + "/"):
        return p[len(root.rstrip("/")) + 1:]
    if not windows:  # symlink: o cwd pode vir por outro caminho que o da raiz
        rp, rr = norm(os.path.realpath(p)), norm(os.path.realpath(root))
        if rp.startswith(rr.rstrip("/") + "/"):
            return rp[len(rr.rstrip("/")) + 1:]
    return p


def _tool(native: dict, project_dir: str, event: str) -> dict:
    name = native.get("tool_name") or "unknown"
    args = native.get("tool_input") if isinstance(native.get("tool_input"), dict) else {}
    tool: dict = {"name": name}
    if name in SHELL_TOOLS:
        tool["kind"] = "shell"
        tool["command"] = str(args.get("command", ""))
    elif name in WRITE_TOOLS:
        tool["kind"] = "write"
        raw = args.get("file_path") or args.get("notebook_path")
        tool["paths"] = [relativize(raw, project_dir)] if raw else []
    elif name in READ_TOOLS:
        tool["kind"] = "read"
        raw = args.get("file_path") or args.get("path")
        if raw:
            tool["paths"] = [relativize(raw, project_dir)]
    else:
        tool["kind"] = "other"
    if event == "post_edit":
        resp = native.get("tool_response")
        failed = isinstance(resp, dict) and (resp.get("success") is False or bool(resp.get("error")))
        tool["succeeded"] = not failed
    return tool


def to_neutral(native: dict, project_dir: str | None = None) -> dict:
    """Levanta `ValueError` para evento desconhecido ou sem `cwd`/`session_id`."""
    native_event = native.get("hook_event_name")
    if native_event not in EVENTS:
        raise ValueError(f"evento nativo sem tradução: {native_event!r} (suportados: {', '.join(EVENTS)})")
    cwd = native.get("cwd")
    if not isinstance(cwd, str) or not cwd or not native.get("session_id"):
        raise ValueError("o stdin nativo não traz `cwd` e `session_id`")
    event = EVENTS[native_event]
    root = norm(project_dir) if project_dir else project_root(cwd)
    session: dict = {"id": str(native["session_id"]), "projectDir": root, "cwd": norm(cwd)}
    if native.get("agent_type"):
        agent = {"type": str(native["agent_type"])}
        if native.get("agent_id"):
            agent["id"] = str(native["agent_id"])
        session["agent"] = agent
    out: dict = {"contract": "hook/v0", "event": event,
                 "source": {"tool": TOOL, "nativeEvent": native_event}, "session": session}
    if event in ("pre_tool", "post_edit"):
        out["tool"] = _tool(native, root, event)
    elif event == "stop":
        stop: dict = {"reentry": bool(native.get("stop_hook_active"))}
        if isinstance(native.get("last_assistant_message"), str):
            stop["lastMessage"] = native["last_assistant_message"]
        out["stop"] = stop
    elif event == "session_start":
        source = native.get("source")
        out["sessionStart"] = {"reason": source if source in SESSION_REASONS else "other"}
    elif event == "pre_compact":
        out["compact"] = {"trigger": "auto" if native.get("trigger") == "auto" else "manual"}
    return out


def format_message(message: dict) -> str:
    return f"{message['what']} — {message['why']} — {message['instead']}"


def to_native(result: dict, event: dict) -> tuple[int, str, str]:
    """(exit, stdout, stderr) nativos. `allow`/`ask` → 0; `block` → 2 com a razão no stderr."""
    decision = result["decision"]
    kind = event["event"]
    native_event = event["source"].get("nativeEvent")
    if decision == "block":
        text = format_message(result["message"])
        if kind == "pre_tool":
            out = {"hookSpecificOutput": {"hookEventName": native_event or "PreToolUse",
                                          "permissionDecision": "deny", "permissionDecisionReason": text}}
        else:
            out = {"decision": "block", "reason": text}
        return 2, json.dumps(out, ensure_ascii=False), text
    out = {}
    if decision == "ask":
        out = {"hookSpecificOutput": {"hookEventName": native_event or "PreToolUse",
                                      "permissionDecision": "ask",
                                      "permissionDecisionReason": format_message(result["message"])}}
    elif result.get("context") and kind in CONTEXT_EVENTS:
        out = {"hookSpecificOutput": {"hookEventName": native_event or CONTEXT_EVENTS[kind],
                                      "additionalContext": "\n".join(result["context"])}}
    return 0, json.dumps(out, ensure_ascii=False), ""


def failure_native(hook: str, message: dict, fail_closed: bool) -> tuple[int, str, str]:
    """Falha do hook (hooks.md, Falhas). Fail-closed vira `block`; fail-open vira aviso (exit 0)."""
    text = format_message(message)
    if fail_closed:
        return 2, json.dumps({"decision": "block", "reason": text}, ensure_ascii=False), text
    return 0, json.dumps({"systemMessage": f"hook {hook} falhou (fail-open): {text}"}, ensure_ascii=False), text
