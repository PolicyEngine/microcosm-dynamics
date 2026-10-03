"""No registered path can reach the selectable baselines.

``TR2008Legacy`` delegates to the constructors the registered projection
tests already call, so the differential tests in
``test_legacy_differential.py`` only show that it passes them the right
arguments.  What guarantees that every registered result is unchanged
is narrower and stronger: nothing outside the ``baselines`` package
imports it, apart from the documentation CLI.  This module asserts that
by scanning the source, so a later import from a registered runner, a
v1 track module or the engine fails here.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "populace_dynamics.baselines"
SRC = REPO_ROOT / "src" / "populace_dynamics"
SCRIPTS = REPO_ROOT / "scripts"

#: The only importer outside the package: it prints input paths and runs
#: no projection.
ALLOWED_IMPORTERS = frozenset({Path("scripts/describe_baseline.py")})

#: Entry points of the registered runs and the modules behind them.
REGISTERED_PATHS = (
    Path("scripts/run_track_a_registered.py"),
    Path("scripts/run_fra68_registered.py"),
    Path("scripts/run_track_u_registered.py"),
    Path("scripts/run_track_m_registered.py"),
    Path("src/populace_dynamics/cola_track_a"),
    Path("src/populace_dynamics/fra68_track"),
    Path("src/populace_dynamics/uniform_cut_track_u"),
    Path("src/populace_dynamics/min_benefit_track_m"),
    Path("src/populace_dynamics/track_a_v2"),
    Path("src/populace_dynamics/engine"),
    Path("src/populace_dynamics/ss"),
    Path("src/populace_dynamics/estimates"),
)


def _imports_baselines(path: Path) -> bool:
    """Whether ``path`` imports the baselines package, by its syntax tree."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name == PACKAGE or alias.name.startswith(PACKAGE + ".")
                for alias in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module or ""
            if module == PACKAGE or module.startswith(PACKAGE + "."):
                return True
            if module == "populace_dynamics" and any(
                alias.name == "baselines" for alias in node.names
            ):
                return True
    return False


def _python_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.py"))


def test_registered_paths_exist():
    """A renamed path must not silently drop out of the scan."""

    missing = [
        str(path)
        for path in REGISTERED_PATHS
        if not (REPO_ROOT / path).exists()
    ]
    assert not missing


def test_no_registered_path_imports_the_baselines_package():
    importers = [
        str(file.relative_to(REPO_ROOT))
        for path in REGISTERED_PATHS
        for file in _python_files(REPO_ROOT / path)
        if _imports_baselines(file)
    ]
    assert not importers


def test_only_the_documentation_cli_imports_baselines_from_outside():
    outside = [
        file.relative_to(REPO_ROOT)
        for root in (SRC, SCRIPTS)
        for file in _python_files(root)
        if SRC / "baselines" not in file.parents and _imports_baselines(file)
    ]
    assert set(outside) == ALLOWED_IMPORTERS


def test_the_scan_detects_each_import_form(tmp_path):
    """The scanner itself is not vacuous."""

    forms = {
        "plain": f"import {PACKAGE}\n",
        "submodule": f"import {PACKAGE}.track_a as t\n",
        "from_package": f"from {PACKAGE} import get_baseline\n",
        "from_submodule": f"from {PACKAGE}.legacy import TR2008Legacy\n",
        "from_parent": "from populace_dynamics import baselines\n",
    }
    for name, source in forms.items():
        file = tmp_path / f"{name}.py"
        file.write_text(source, encoding="utf-8")
        assert _imports_baselines(file), name
    clean = tmp_path / "clean.py"
    clean.write_text(
        "from populace_dynamics.data import tr2008\n"
        "# populace_dynamics.baselines in a comment is not an import\n",
        encoding="utf-8",
    )
    assert not _imports_baselines(clean)
