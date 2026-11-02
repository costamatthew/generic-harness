"""sha256-worktree-v0: o que muda e o que não muda o hash (critério da 1A)."""

from __future__ import annotations

import os

import pytest

from core.lib import tree
from tests.unit.lib import repo as R


@pytest.fixture
def root(tmp_path):
    return R.init(tmp_path)


def test_stable_without_changes(root):
    assert tree.compute(root) == tree.compute(root)
    assert len(tree.compute(root)) == 64


@pytest.mark.parametrize("change", ["edit-tracked", "new-untracked", "delete-tracked"])
def test_changes_hash(root, change):
    before = tree.compute(root)
    if change == "edit-tracked":
        (root / "src" / "app.py").write_text("x = 2\n", encoding="utf-8")
    elif change == "new-untracked":
        (root / "src" / "novo.py").write_text("", encoding="utf-8")
    else:
        (root / "src" / "app.py").unlink()
    assert tree.compute(root) != before


def test_deleted_tracked_file_is_type_d(root):
    (root / "src" / "app.py").unlink()
    assert tree.entries(root)["src/app.py"] == b"src/app.py\0d\0\n"


@pytest.mark.skipif(os.name == "nt", reason="sem bit de execução no Windows")
def test_exec_bit_changes_hash(root):
    before = tree.compute(root)
    os.chmod(root / "src" / "app.py", 0o755)
    assert tree.compute(root) != before
    assert b"\0x\0" in tree.entries(root)["src/app.py"]


def test_symlink_hashes_target(root):
    try:
        os.symlink("src/app.py", root / "link")
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponível")
    line = tree.entries(root)["link"]
    assert b"\0l\0" in line
    import hashlib
    assert hashlib.sha256(b"src/app.py").hexdigest().encode() in line


@pytest.mark.parametrize("path", [
    "ignorado/x.txt", ".harness/runs/abc/manifest.json", ".harness/work/PAG-1/tasks.json",
    ".harness/work/PAG-1/validation.md", ".harness/work/PAG-1/.journal/a/b.md", ".harness/STATE.md",
])
def test_ignored_and_excluded_do_not_change_hash(root, path):
    before = tree.compute(root)
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x", encoding="utf-8")
    assert tree.compute(root) == before
    assert tree.dirty(root) is False


def test_excludes_do_not_hide_other_harness_files(root):
    before = tree.compute(root)
    (root / ".harness").mkdir()
    (root / ".harness" / "profile.json").write_text("{}", encoding="utf-8")
    assert tree.compute(root) != before


def test_line_endings_are_not_normalized(root):
    (root / "src" / "app.py").write_bytes(b"x = 1\n")
    a = tree.compute(root)
    (root / "src" / "app.py").write_bytes(b"x = 1\r\n")
    assert tree.compute(root) != a


def test_revision_and_dirty(tmp_path):
    R.init(tmp_path, commit=False)
    assert tree.revision(tmp_path) is None
    assert tree.dirty(tmp_path) is True
    R.commit_all(tmp_path)
    assert len(tree.revision(tmp_path)) == 40
    assert tree.dirty(tmp_path) is False


def test_not_a_git_repo(tmp_path):
    with pytest.raises(tree.NotAGitRepo, match="git init"):
        tree.compute(tmp_path)


@pytest.mark.parametrize("path,pattern,hit", [
    (".harness/runs/a/b/c", ".harness/runs/**", True),
    (".harness/runsX/a", ".harness/runs/**", False),
    (".harness/work/A-1/tasks.json", ".harness/work/*/tasks.json", True),
    (".harness/work/A-1/sub/tasks.json", ".harness/work/*/tasks.json", False),
    ("a/b/c.py", "**/c.py", True),
    ("c.py", "**/c.py", True),
])
def test_glob(path, pattern, hit):
    assert tree.excluded(path, [pattern]) is hit
