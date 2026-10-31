"""Critério de saída da Etapa 0: cada schema valida seus exemplos válidos e rejeita os inválidos.

Os exemplos ficam em core/schemas/examples/<schema>/{valid,invalid}-*.{json,md}.
O validador stdlib (core/lib/schema.py) é o que roda no hospedeiro; quando o
`jsonschema` de referência está instalado, os dois precisam concordar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.lib import intake, schema

EXAMPLES = schema.SCHEMAS_DIR / "examples"
SCHEMAS = sorted(p.name.removesuffix(".schema.json") for p in schema.SCHEMAS_DIR.glob("*.schema.json"))


def _load(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        return intake.parse(text)
    return json.loads(text)


def _cases():
    for name in SCHEMAS:
        for path in sorted((EXAMPLES / name).glob("*")):
            yield pytest.param(name, path, id=f"{name}/{path.name}")


def test_every_schema_has_valid_and_invalid_examples():
    for name in SCHEMAS:
        files = [p.name for p in (EXAMPLES / name).glob("*")]
        assert any(f.startswith("valid") for f in files), f"{name}: falta exemplo válido"
        assert any(f.startswith("invalid") for f in files), f"{name}: falta exemplo inválido"


def test_example_dirs_match_schemas():
    dirs = sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir())
    assert dirs == SCHEMAS


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_uses_only_supported_keywords(name):
    assert schema.check_schema(schema.load(name)) == []


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_is_valid_draft_2020_12(name):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(schema.load(name))


@pytest.mark.parametrize("name,path", list(_cases()))
def test_example(name, path):
    instance = _load(path)
    errors = schema.validate(instance, name)
    if path.name.startswith("valid"):
        assert errors == [], errors
    else:
        assert errors, f"{path.name} deveria ser rejeitado"


@pytest.mark.parametrize("name,path", list(_cases()))
def test_stdlib_validator_agrees_with_reference(name, path):
    jsonschema = pytest.importorskip("jsonschema")
    instance = _load(path)
    ref = jsonschema.Draft202012Validator(schema.load(name))
    assert ref.is_valid(instance) == (schema.validate(instance, name) == [])
