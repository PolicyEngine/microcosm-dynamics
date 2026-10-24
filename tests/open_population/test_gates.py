"""Check the unaligned facade required by the approved design's §5.1.

``docs/design/open_population.md`` §§2.9, 3.1 (OP1), 5.1 and 7, approved in
ruling d1925, give gate runs a fixed horizon and no target-bearing request.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.engine.loop import PeriodModules
from populace_dynamics.engine.steps import advance_age
from populace_dynamics.open_population.exits import no_marital_transitions
from populace_dynamics.open_population.gates import (
    GateRunRequest,
    run_gate,
)
from populace_dynamics.open_population.harness import ProductionRequest


@pytest.mark.parametrize("keyword", ["target_bundle", "targets", "alignment"])
def test_gate_requests_reject_target_keywords(keyword):
    assert {field.name for field in fields(GateRunRequest)} == {
        "horizon",
        "draw_index",
        "start_year",
    }
    with pytest.raises(TypeError, match="unexpected keyword"):
        GateRunRequest(horizon=2026, **{keyword: object()})
    request = GateRunRequest(horizon=2026)
    with pytest.raises((AttributeError, TypeError)):
        request.target_bundle = object()


def test_gate_runner_refuses_production_request_before_adapters_run():
    with pytest.raises(TypeError, match="requires a GateRunRequest"):
        run_gate(pd.DataFrame(), None, ProductionRequest(2026, 2026))


def test_gate_runs_to_its_own_fixed_horizon():
    def unchanged(frame, *args):
        return frame

    modules = PeriodModules(
        mortality=unchanged,
        aging=advance_age,
        marital_core=no_marital_transitions,
        fertility=unchanged,
        disability=unchanged,
        earnings=unchanged,
        claiming=unchanged,
        household_composition=unchanged,
    )
    initial = pd.DataFrame(
        {"person_id": [1], "year": [2025], "age": [25], "weight": [1.0]}
    )
    result = run_gate(initial, modules, GateRunRequest(horizon=2027))
    assert result.horizon == 2027
    assert len(result.projection.slices) == 3
    assert result.projection.slices[-1]["year"].tolist() == [2027]
    assert len(result.accounting.periods) == 2
    with pytest.raises(TypeError, match="target_bundle"):
        run_gate(
            initial,
            modules,
            GateRunRequest(horizon=2027),
            target_bundle=object(),
        )


def test_importing_gate_facade_loads_no_alignment_module():
    root = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(root / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; "
            "import populace_dynamics.open_population.gates; "
            "loaded = sorted(name for name in sys.modules "
            "if 'align' in name.lower()); "
            "assert not loaded, loaded",
        ],
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        # The existing engine initializer has a broad cold import closure.
        timeout=600,
    )
    assert result.returncode == 0, result.stderr


def test_gate_project_import_closure_excludes_future_alignment_producers():
    """Inspect deferred imports too, so a future producer cannot hide there."""
    package = (
        Path(__file__).resolve().parents[2]
        / "src/populace_dynamics/open_population"
    )
    prefix = "populace_dynamics.open_population"
    modules = {
        (prefix if path.stem == "__init__" else f"{prefix}.{path.stem}"): path
        for path in package.glob("*.py")
    }
    pending = [f"{prefix}.gates"]
    visited = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        tree = ast.parse(modules[name].read_text())
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    base = f"{prefix}.{base}".rstrip(".")
                imported = [
                    base,
                    *(f"{base}.{alias.name}" for alias in node.names),
                ]
            for target in imported:
                if target.startswith("populace_dynamics"):
                    assert "align" not in target.lower(), target
                if target in modules and target not in visited:
                    pending.append(target)
