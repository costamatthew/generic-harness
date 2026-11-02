"""Política de skip dos cenários e do teste de conteúdo (spec 1G, item 2).

Uma trilha ainda não entregue faz o teste pular com o nome da trilha. Com
HARNESS_REQUIRE_ALL=1 (modo da integração 1I) o mesmo caso vira falha: assim
nenhum cenário passa por vacuidade. Nenhum outro motivo de skip é permitido.
"""

from __future__ import annotations

import os

import pytest


def not_delivered(track: str, detail: str = ""):
    msg = f"trilha {track} não entregue" + (f" ({detail})" if detail else "")
    if os.environ.get("HARNESS_REQUIRE_ALL") == "1":
        pytest.fail(
            f"{msg}. HARNESS_REQUIRE_ALL=1 exige todas as trilhas; entregue a trilha {track} "
            "ou rode sem a variável para pular este cenário.",
            pytrace=False,
        )
    pytest.skip(msg)
