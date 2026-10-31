"""Validador de JSON Schema (subconjunto do draft 2020-12), só com a stdlib.

O harness vendorizado não pode depender de `jsonschema` (D4 / ADR-0004), mas
precisa validar `profile.json`, `tasks.json` e o manifesto de run em tempo de
execução. Este módulo cobre só as palavras-chave usadas em `core/schemas/`.
Uma palavra-chave fora de SUPPORTED faz `check_schema` falhar, para que um
schema novo não seja aceito em silêncio com uma regra ignorada.

Uso:
    from core.lib import schema
    errors = schema.validate(instance, "profile")   # [] quando válido
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

SUPPORTED = {
    "$schema", "$id", "$defs", "$ref", "$comment", "title", "description",
    "examples", "default", "type", "enum", "const", "properties", "required",
    "additionalProperties", "patternProperties", "propertyNames", "items",
    "minItems", "maxItems", "uniqueItems", "minLength", "maxLength", "pattern",
    "minimum", "maximum", "exclusiveMinimum", "minProperties", "oneOf", "anyOf",
    "allOf", "not", "if", "then", "else", "format",
}

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def load(name: str) -> dict:
    """Carrega `core/schemas/<name>.schema.json`."""
    path = SCHEMAS_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def check_schema(schema: dict) -> list[str]:
    """Lista palavras-chave não suportadas, com o caminho onde aparecem."""
    problems: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key not in SUPPORTED:
                    problems.append(f"{path}: palavra-chave não suportada '{key}'")
                if key in ("properties", "patternProperties", "$defs"):
                    for sub, subschema in value.items():
                        walk(subschema, f"{path}/{key}/{sub}")
                elif key in ("oneOf", "anyOf", "allOf"):
                    for i, subschema in enumerate(value):
                        walk(subschema, f"{path}/{key}/{i}")
                elif key in ("items", "additionalProperties", "propertyNames",
                             "not", "if", "then", "else") and isinstance(value, dict):
                    walk(value, f"{path}/{key}")

    walk(schema, "#")
    return problems


def validate(instance: Any, schema: dict | str) -> list[str]:
    """Valida `instance`. Devolve a lista de erros (vazia quando válido)."""
    root = load(schema) if isinstance(schema, str) else schema
    errors: list[str] = []
    _validate(instance, root, root, "$", errors)
    return errors


def _resolve(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"só $ref locais são suportados: {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _validate(inst: Any, sch: Any, root: dict, path: str, errors: list[str]) -> None:
    if sch is True or sch == {}:
        return
    if sch is False:
        errors.append(f"{path}: nenhum valor é permitido aqui")
        return

    if "$ref" in sch:
        _validate(inst, _resolve(sch["$ref"], root), root, path, errors)

    if "type" in sch:
        types = sch["type"] if isinstance(sch["type"], list) else [sch["type"]]
        if not any(_TYPES[t](inst) for t in types):
            errors.append(f"{path}: esperado {'|'.join(types)}, veio {type(inst).__name__}")
            return

    if "enum" in sch and not any(_equal(inst, e) for e in sch["enum"]):
        errors.append(f"{path}: {inst!r} não está em {sch['enum']}")
    if "const" in sch and not _equal(inst, sch["const"]):
        errors.append(f"{path}: esperado {sch['const']!r}, veio {inst!r}")

    if isinstance(inst, str):
        if "minLength" in sch and len(inst) < sch["minLength"]:
            errors.append(f"{path}: menor que {sch['minLength']} caracteres")
        if "maxLength" in sch and len(inst) > sch["maxLength"]:
            errors.append(f"{path}: maior que {sch['maxLength']} caracteres")
        if "pattern" in sch and not re.search(sch["pattern"], inst):
            errors.append(f"{path}: {inst!r} não casa com /{sch['pattern']}/")

    if _TYPES["number"](inst):
        if "minimum" in sch and inst < sch["minimum"]:
            errors.append(f"{path}: {inst} < mínimo {sch['minimum']}")
        if "maximum" in sch and inst > sch["maximum"]:
            errors.append(f"{path}: {inst} > máximo {sch['maximum']}")
        if "exclusiveMinimum" in sch and inst <= sch["exclusiveMinimum"]:
            errors.append(f"{path}: {inst} <= {sch['exclusiveMinimum']}")

    if isinstance(inst, list):
        if "minItems" in sch and len(inst) < sch["minItems"]:
            errors.append(f"{path}: menos de {sch['minItems']} itens")
        if "maxItems" in sch and len(inst) > sch["maxItems"]:
            errors.append(f"{path}: mais de {sch['maxItems']} itens")
        if sch.get("uniqueItems"):
            seen: list[Any] = []
            for item in inst:
                if any(_equal(item, s) for s in seen):
                    errors.append(f"{path}: itens repetidos")
                    break
                seen.append(item)
        if "items" in sch:
            for i, item in enumerate(inst):
                _validate(item, sch["items"], root, f"{path}[{i}]", errors)

    if isinstance(inst, dict):
        if "minProperties" in sch and len(inst) < sch["minProperties"]:
            errors.append(f"{path}: menos de {sch['minProperties']} chaves")
        for key in sch.get("required", []):
            if key not in inst:
                errors.append(f"{path}: falta o campo obrigatório '{key}'")
        props = sch.get("properties", {})
        patterns = sch.get("patternProperties", {})
        for key, value in inst.items():
            sub = f"{path}.{key}"
            if "propertyNames" in sch:
                _validate(key, sch["propertyNames"], root, f"{path}<chave {key}>", errors)
            matched = False
            if key in props:
                matched = True
                _validate(value, props[key], root, sub, errors)
            for pat, psch in patterns.items():
                if re.search(pat, key):
                    matched = True
                    _validate(value, psch, root, sub, errors)
            if not matched and "additionalProperties" in sch:
                addl = sch["additionalProperties"]
                if addl is False:
                    errors.append(f"{path}: campo não previsto '{key}'")
                else:
                    _validate(value, addl, root, sub, errors)

    for sub in sch.get("allOf", []):
        _validate(inst, sub, root, path, errors)
    if "anyOf" in sch and not any(_ok(inst, s, root) for s in sch["anyOf"]):
        errors.append(f"{path}: não atende a nenhuma alternativa de anyOf")
    if "oneOf" in sch:
        hits = sum(_ok(inst, s, root) for s in sch["oneOf"])
        if hits != 1:
            errors.append(f"{path}: atende a {hits} alternativas de oneOf (esperado 1)")
    if "not" in sch and _ok(inst, sch["not"], root):
        errors.append(f"{path}: casa com um schema proibido (not)")
    if "if" in sch:
        branch = sch.get("then") if _ok(inst, sch["if"], root) else sch.get("else")
        if branch is not None:
            _validate(inst, branch, root, path, errors)


def _ok(inst: Any, sch: Any, root: dict) -> bool:
    errs: list[str] = []
    _validate(inst, sch, root, "$", errs)
    return not errs


def _equal(a: Any, b: Any) -> bool:
    # 1 == True em Python; em JSON Schema não.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b
