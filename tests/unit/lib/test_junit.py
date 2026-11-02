"""Parser JUnit: xunit1, xunit2, aninhado, erro/skip, malformado."""

from __future__ import annotations

import pytest

from core.lib import junit
from tests.unit.lib import repo as R

D = R.DATA_LIB


@pytest.fixture
def root(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_calc.py").write_text("", encoding="utf-8")
    return tmp_path


def test_xunit1_uses_file_and_line(root):
    rep = junit.parse(D / "xunit1-fail.xml", root)
    assert rep.counts() == {"tests": 2, "failures": 1, "errors": 0, "skipped": 0}
    assert rep.first_failures == [{"location": "tests/test_calc.py:7", "name": "test_soma"}]


def test_xunit2_falls_back_to_failure_text(root):
    rep = junit.parse(D / "xunit2-fail.xml", root)
    assert rep.first_failures == [{"location": "tests/test_calc.py:8", "name": "test_soma"}]


def test_xunit2_absolute_path_in_text(root):
    xml = (D / "xunit2-fail.xml").read_text(encoding="utf-8").replace(
        "tests/test_calc.py:8:", f"{(root / 'tests' / 'test_calc.py').as_posix()}:9:")
    (root / "r.xml").write_text(xml, encoding="utf-8")
    assert junit.parse(root / "r.xml", root).first_failures[0]["location"] == "tests/test_calc.py:9"


def test_nested_with_error_skip_and_classname_fallback(root):
    rep = junit.parse(D / "nested-error-skip.xml", root)
    # testcases: 4 (1 error, 1 skip, 1 failure) + suíte só com atributos (3, 1 erro, 1 skip)
    assert rep.counts() == {"tests": 7, "failures": 1, "errors": 2, "skipped": 2}
    locs = [f["location"] for f in rep.first_failures]
    assert locs == ["tests/test_calc.py", "pkg/nao/existe"]


def test_testsuite_root_without_testsuites(root):
    xml = (D / "xunit2-pass.xml").read_text(encoding="utf-8")
    xml = xml.replace("<testsuites>", "").replace("</testsuites>", "")
    (root / "r.xml").write_text(xml, encoding="utf-8")
    assert junit.parse(root / "r.xml").counts()["tests"] == 1


def test_malformed_raises():
    with pytest.raises(junit.JUnitError):
        junit.parse(D / "malformed.xml")


def test_unknown_root_raises(tmp_path):
    (tmp_path / "r.xml").write_text("<html/>", encoding="utf-8")
    with pytest.raises(junit.JUnitError):
        junit.parse(tmp_path / "r.xml")


def test_first_failures_capped_at_10(tmp_path):
    cases = "".join(f'<testcase name="t{i}" file="a.py" line="{i}"><failure/></testcase>' for i in range(15))
    (tmp_path / "r.xml").write_text(f"<testsuite>{cases}</testsuite>", encoding="utf-8")
    rep = junit.parse(tmp_path / "r.xml")
    assert rep.failures == 15 and len(rep.first_failures) == 10
