"""O helper `host` monta o repo certo (roda sem as outras trilhas)."""

from __future__ import annotations

import json
import subprocess

import pytest

from core.lib import schema


def _git_status(host) -> str:
    return subprocess.run(["git", "status", "--porcelain"], cwd=host.path, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


@pytest.mark.parametrize("host", ["green", "red", "planned"], indirect=True)
def test_host_variants(host):
    profile = json.loads(host.read(".harness/profile.json"))
    assert schema.validate(profile, "profile") == []
    assert "@PYTHON@" not in host.read(".harness/profile.json")
    status = profile["commands"]["test"]["unit"]["status"]
    assert status == ("planned" if host.variant == "planned" else "verified")
    dirty = _git_status(host)
    assert (" M tests/test_calc.py" in dirty) == (host.variant == "red")


def test_host_mutations_and_verifier(host):
    host.edit_src()
    assert "mul" in host.read("src/calc/__init__.py")
    host.write_verifier("abcdef0123456789")
    text = host.read(".harness/work/FIX-1/validation.md")
    assert "### Verifier FIX-1.T1\n- tree: abcdef0\n" in text and text.count("| atende |") == 2
