"""Prettier cannot parse QML's JavaScript libraries (they start with ".pragma library"): .prettierignore must list
each one, and tests/tools_prettier_pragma.py checks their layout instead (make format-check)."""

import pytest
from conftest import REPO

IGNORED = set((REPO / ".prettierignore").read_text().splitlines())
SKIPPED_FOLDERS = ("node_modules", ".git", "test-output", "report")


def pragma_libraries():
    return sorted(
        str(path.relative_to(REPO))
        for path in REPO.rglob("*.js")
        if not set(path.relative_to(REPO).parts) & set(SKIPPED_FOLDERS)
        and path.read_text(errors="replace").startswith(".pragma")
    )


@pytest.mark.parametrize("library", pragma_libraries())
def test_prettier_leaves_each_qml_javascript_library_alone(library):
    assert library in IGNORED
