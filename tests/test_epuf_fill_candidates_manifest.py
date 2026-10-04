"""The registered candidate manifest of gate_epuf_fill.

``runs/epuf_fill_candidates_v1.json`` names the four registered fills by
SHA-256. Their bytes live outside the repository (``~/PolicyEngine/
epuf-data/fills``), so the hash checks of the staged files skip where they
are not staged.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "runs" / "epuf_fill_candidates_v1.json"
FILLS_DIR = Path(
    os.environ.get(
        "POPULACE_DYNAMICS_EPUF_FILLS_DIR", "~/PolicyEngine/epuf-data/fills"
    )
).expanduser()


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text())


def _script():
    spec = importlib.util.spec_from_file_location(
        "fit_epuf_fills", ROOT / "scripts" / "fit_epuf_fills.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_manifest_registers_one_primary_and_one_alternative_per_family(
    manifest,
):
    assert manifest["schema"] == "populace_dynamics.epuf_fill_candidates.v1"
    assert manifest["registration_id"] == "2026-10-03-epuf-career-fill"
    assert manifest["part"] == "train"
    assert manifest["code_files_clean"] is True
    roles = sorted(
        (record["family"], record["role"])
        for record in manifest["fills"].values()
    )
    assert roles == [
        ("odd", "alternative"),
        ("odd", "primary"),
        ("pre", "alternative"),
        ("pre", "primary"),
    ]
    for record in manifest["fills"].values():
        assert len(record["sha256"]) == 64 and record["bytes"] > 0


def test_the_manifest_parameters_are_the_scripts(manifest):
    registered = _script().REGISTERED
    assert set(registered) == set(manifest["fills"])
    for name, record in manifest["fills"].items():
        assert record["params"] == registered[name]["params"]
        assert record["family"] == registered[name]["family"]
        assert record["role"] == registered[name]["role"]


def test_the_fill_code_is_unchanged_since_the_fit(manifest):
    commit = manifest["code_commit"]
    probe = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
    )
    if probe.returncode != 0:
        pytest.skip("the fit's commit is not in this clone")
    for path in _script().CODE_FILES:
        built = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
            capture_output=True,
            check=True,
        ).stdout
        assert built == (ROOT / path).read_bytes(), path


@pytest.mark.parametrize(
    "name", ["odd_forest", "odd_knn", "pre_donor", "pre_chain"]
)
def test_staged_fills_hash_to_the_manifest(manifest, name):
    record = manifest["fills"][name]
    path = FILLS_DIR / record["file"]
    if not path.is_file():
        pytest.skip(f"{path} is not staged")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]


def test_the_registered_copula_binds_for_each_coded_sex(manifest):
    diagnostics = manifest["fills"]["odd_forest"]["diagnostics"]
    for sex in ("1", "2"):
        rho = diagnostics[sex]["rho"]
        assert any(value > 0 for value in rho[int(sex)])


def _score_script():
    spec = importlib.util.spec_from_file_location(
        "score_epuf_fill_test", ROOT / "scripts" / "score_epuf_fill_test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_score_script_pins_this_manifest():
    script = _score_script()
    assert script.REGISTERED_MANIFEST == "runs/epuf_fill_candidates_v1.json"
    assert (
        script.REGISTERED_MANIFEST_SHA256
        == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    )


def test_the_score_script_refuses_before_reading_test(tmp_path):
    script = _score_script()
    output = tmp_path / "result.json"
    other = tmp_path / "other.json"
    other.write_text("{}")
    with pytest.raises(ValueError, match="not the registered"):
        script.main(["--manifest", str(other), "--output", str(output)])
    # The registered manifest, but the gate is not locked in gates.yaml.
    from populace_dynamics.harness import epuf_fill_gate as g

    with pytest.raises(g.TestPartLocked):
        script.main(["--manifest", str(MANIFEST), "--output", str(output)])
    assert not output.exists()
    assert not tmp_path.joinpath("result.json.started.json").exists()
    output.write_text("{}")
    with pytest.raises(FileExistsError, match="scored once"):
        script.main(["--manifest", str(MANIFEST), "--output", str(output)])
