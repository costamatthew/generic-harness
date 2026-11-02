"""Hash da árvore de trabalho `sha256-worktree-v0` (spec 1A, item 5; HG §3.7).

Algoritmo fixado:
- arquivos = `git ls-files -z --cached --others --exclude-standard`, menos os
  que casam com `excludes` (glob com `**`, separador `/`);
- por caminho, em ordem de bytes UTF-8: `caminho \\0 tipo \\0 sha256hex \\n`, com
  tipo `f` (arquivo), `x` (executável; nunca no Windows), `l` (symlink: hash do
  alvo) e `d` (rastreado mas apagado: hash vazio);
- tree = sha256 da sequência. Bytes lidos como estão (sem normalizar EOL).

Submódulos (diretórios listados pelo git) ficam fora do v0.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from functools import lru_cache
from pathlib import Path

ALGORITHM = "sha256-worktree-v0"

# Arquivos que o próprio harness escreve depois do gate; sem isso, `task done`
# invalidaria o próprio verde.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".harness/runs/**",
    ".harness/work/*/tasks.json",
    ".harness/work/*/validation.md",
    ".harness/work/*/.journal/**",
    ".harness/STATE.md",
)


class NotAGitRepo(RuntimeError):
    """O hash exige git. Mensagem pronta para o agente."""

    def __init__(self, root: Path, detail: str = ""):
        super().__init__(f"o gate exige git; rode `git init` em {Path(root).as_posix()}"
                         + (f" ({detail})" if detail else ""))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    except FileNotFoundError as exc:
        raise NotAGitRepo(root, "git não encontrado no PATH") from exc


def require_repo(root: str | Path) -> None:
    root = Path(root)
    proc = _git(root, "rev-parse", "--is-inside-work-tree")
    if proc.returncode != 0 or proc.stdout.strip() != b"true":
        raise NotAGitRepo(root)


@lru_cache(maxsize=64)
def _glob_re(pattern: str) -> re.Pattern:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def excluded(path: str, excludes) -> bool:
    return any(_glob_re(p).match(path) for p in excludes)


def _split_z(raw: bytes) -> list[str]:
    return [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p]


def files(root: str | Path, excludes=DEFAULT_EXCLUDES) -> list[str]:
    """Caminhos (com `/`) que entram no hash, já ordenados por bytes UTF-8."""
    root = Path(root)
    require_repo(root)
    proc = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if proc.returncode != 0:
        raise NotAGitRepo(root, proc.stderr.decode("utf-8", "replace").strip())
    paths = {p for p in _split_z(proc.stdout) if not excluded(p, excludes)}
    return sorted(paths, key=lambda p: p.encode("utf-8", "surrogateescape"))


def _entry(root: Path, rel: str) -> bytes | None:
    full = root / rel
    try:
        st = os.lstat(full)
    except (FileNotFoundError, NotADirectoryError):
        kind, digest = "d", ""
    else:
        if stat.S_ISLNK(st.st_mode):
            kind = "l"
            digest = hashlib.sha256(os.fsencode(os.readlink(full))).hexdigest()
        elif stat.S_ISDIR(st.st_mode):
            return None  # submódulo: fora do v0
        else:
            kind = "x" if os.name != "nt" and st.st_mode & 0o111 else "f"
            h = hashlib.sha256()
            with open(full, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 16), b""):
                    h.update(chunk)
            digest = h.hexdigest()
    return rel.encode("utf-8", "surrogateescape") + b"\0" + kind.encode() + b"\0" + digest.encode() + b"\n"


def entries(root: str | Path, excludes=DEFAULT_EXCLUDES) -> dict[str, bytes]:
    """caminho → linha do hash. Útil para dizer *o que* mudou entre dois hashes."""
    root = Path(root)
    out = {}
    for rel in files(root, excludes):
        line = _entry(root, rel)
        if line is not None:
            out[rel] = line
    return out


def digest(ents: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for line in ents.values():  # já em ordem de bytes
        h.update(line)
    return h.hexdigest()


def compute(root: str | Path, excludes=DEFAULT_EXCLUDES) -> str:
    """Hex de 64 caracteres. `NotAGitRepo` fora de um repo git."""
    return digest(entries(root, excludes))


def changed(before: dict[str, bytes], after: dict[str, bytes]) -> list[str]:
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))


def revision(root: str | Path) -> str | None:
    proc = _git(Path(root), "rev-parse", "--verify", "-q", "HEAD")
    if proc.returncode != 0:
        return None
    return proc.stdout.decode().strip() or None


def dirty(root: str | Path, excludes=DEFAULT_EXCLUDES) -> bool:
    """`git status --porcelain` não vazio, desconsiderando os excludes."""
    proc = _git(Path(root), "status", "--porcelain", "-z", "--untracked-files=all")
    if proc.returncode != 0:
        raise NotAGitRepo(Path(root), proc.stderr.decode("utf-8", "replace").strip())
    chunks = _split_z(proc.stdout)
    i = 0
    while i < len(chunks):
        entry = chunks[i]
        code, path = entry[:2], entry[3:]
        i += 1
        if "R" in code or "C" in code:
            orig = chunks[i] if i < len(chunks) else ""
            i += 1
            if not (excluded(path, excludes) and excluded(orig, excludes)):
                return True
            continue
        if not excluded(path, excludes):
            return True
    return False
