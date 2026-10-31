"""O validador stdlib recusa schemas com palavra-chave que ele ignoraria."""

from core.lib import intake, schema

import pytest


def test_unsupported_keyword_is_reported():
    problems = schema.check_schema({"type": "object", "properties": {"a": {"dependentRequired": {}}}})
    assert problems == ["#/properties/a: palavra-chave não suportada 'dependentRequired'"]


def test_bool_is_not_integer():
    assert schema.validate(True, {"type": "integer"})
    assert schema.validate(1, {"const": True})


def test_intake_rejects_unknown_field():
    with pytest.raises(ValueError):
        intake.parse("# X-1 t\n- Estimativa: 3 dias\n")
