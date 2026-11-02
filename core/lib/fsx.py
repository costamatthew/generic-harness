"""Escrita atômica, sha256 de arquivo e lock exclusivo, só com a stdlib.

ADR-0003 / cli.md "Quem escreve o quê": todo arquivo de estado é gravado num
temporário no mesmo diretório e trocado com `os.replace`, que é atômico no
mesmo sistema de arquivos (POSIX e Windows).
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from pathlib import Path


def write_atomic(path: str | os.PathLike, text: str) -> None:
    """Grava `text` (UTF-8, sem traduzir fim de linha) em `path` de forma atômica."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class LockHeld(Exception):
    """Outro processo segura o lock e ele ainda não é órfão."""


class Lock:
    """Lock por arquivo (`O_CREAT|O_EXCL`). Um lock mais velho que `stale_after`
    segundos é tratado como órfão: é removido e `self.warning` explica o porquê.

        with Lock(path, stale_after=600) as lock: ...
    """

    def __init__(self, path: str | os.PathLike, stale_after: float):
        self.path = Path(path)
        self.stale_after = stale_after
        self.warning: str | None = None
        self._held = False

    def acquire(self) -> "Lock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                except FileNotFoundError:
                    continue  # foi liberado entre o open e o stat
                if attempt == 0 and age > self.stale_after:
                    self.warning = (f"lock órfão removido: {self.path.name} tinha {age:.0f}s "
                                    f"(limite {self.stale_after:.0f}s)")
                    try:
                        os.unlink(self.path)
                    except FileNotFoundError:
                        pass
                    continue
                raise LockHeld(str(self.path)) from None
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(f"pid={os.getpid()} at={time.time():.3f}\n")
            self._held = True
            return self
        raise LockHeld(str(self.path))

    def release(self) -> None:
        if self._held:
            self._held = False
            try:
                os.unlink(self.path)
            except FileNotFoundError:
                pass

    def __enter__(self) -> "Lock":
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.release()
