#!/usr/bin/env python3
"""Shim do primeiro uso (ADR-0001): `python3 bootstrap.py <comando> [--target <repo>]`.

Encaminha para o CLI `harness` deste clone. Depois do `apply`, o hospedeiro usa
`.harness/bin/harness`, que é o mesmo CLI vendorizado. Só biblioteca padrão.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.cli.harness import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
