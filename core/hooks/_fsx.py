"""Escrita atômica local da trilha 1C.

Cópia mínima de `core.lib.fsx.write_atomic` (1A), com suporte a bytes. Sai na
integração (1I), quando o render e o stop_gate passam a importar `core.lib.fsx`.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_atomic(path: str | os.PathLike, data: str | bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = data.encode("utf-8") if isinstance(data, str) else data
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
