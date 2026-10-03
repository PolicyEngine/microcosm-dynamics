"""The committed exercise-4 run is the parent the breakdown can reproduce.

Artifact tier: reads the committed ``runs/replication_urban2006_minimum_
benefit_v1.json`` and its sidecar for their bindings, keys and
environment only.  No outcome value is read into an assertion or printed,
no PSID file is opened and nothing is computed on real data.

Checked here, before any host run: the parent's bytes are the pinned
ones and its sidecar binds them; it is Registration 17's run on the M1
specification at this commit; every block the adapter compares exists;
the parameter pins the entry script checks are the specification's; the
COLA history on disk is the file the parent recorded (bytes, not
location); the environment fields the entry script compares are recorded;
and ``scripts/make_nasi_repro_venv.sh`` pins exactly those versions.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from populace_dynamics.estimates.parameters import load_cola_history
from populace_dynamics.group_breakdowns import common
from populace_dynamics.group_breakdowns import min_benefit as mb
from populace_dynamics.min_benefit_track_m.policy import REGISTERED_ROWS
from populace_dynamics.min_benefit_track_m.specification import (
    M1_SPECIFICATION_PATH,
    m1_parameter_block,
)

ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT / "runs" / "replication_urban2006_minimum_benefit_v1.json"
VENV_SCRIPT = ROOT / "scripts" / "make_nasi_repro_venv.sh"


def _script():
    path = ROOT / "scripts" / "run_min_benefit_groups_registered.py"
    spec = importlib.util.spec_from_file_location("_g4c_run_artifact", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def parent() -> common.CommittedArtifact:
    assert mb.PARENT_ARTIFACT_PATH == PARENT
    return mb.load_parent_artifact()


def test_the_parent_bytes_are_pinned_and_bound(parent):
    assert parent.sha256 == mb.PARENT_ARTIFACT_SHA256
    assert parent.sidecar["artifact"] == PARENT.name
    assert parent.sidecar["artifact_sha256"] == mb.PARENT_ARTIFACT_SHA256


def test_the_parent_is_registration_17s_run_on_this_specification(parent):
    binding = mb.check_parent_binding(
        parent,
        specification_sha256=common.file_sha256(M1_SPECIFICATION_PATH),
    )
    assert binding["registration_pointer"] == mb.PARENT_REGISTRATION_POINTER
    assert binding["specification_version"] == "m1-ratified-1"


def test_every_block_the_adapter_compares_exists(parent):
    document = parent.document
    for key in (
        "parameters",
        "inputs",
        "rows",
        "sensitivities",
        "cohort_structure",
        "labels",
        "data_provenance",
        "registration_pointer",
    ):
        assert key in document, key
    assert list(document["rows"]) == list(REGISTERED_ROWS)
    for row in REGISTERED_ROWS:
        assert {"tabulation", "diagnostics"} <= set(document["rows"][row])
    sensitivity = document["sensitivities"][mb.SENSITIVITY_KEY]
    assert {"tabulation", "diagnostics", "cohort_structure"} <= set(
        sensitivity
    )
    files = document["inputs"]["source"]["psid_files_sha256"]
    assert files and all(
        re.fullmatch(r"[0-9a-f]{64}", digest) for digest in files.values()
    )


def test_the_parameter_pins_are_the_specifications(parent):
    sources = m1_parameter_block()["sources"]
    assert parent.document["checks"]["parameter_pins"] == {
        "quarter_of_coverage": sources["quarter_of_coverage_amounts"][
            "sha256"
        ],
        "census_thresholds": sources["census_thresholds"]["sha256"],
    }


def test_the_only_location_field_is_the_cola_history_path(parent):
    """No other string in the parent names an absolute path."""

    def walk(node, path="$"):
        if isinstance(node, dict):
            for key, value in node.items():
                yield from walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from walk(value, f"{path}[{index}]")
        elif isinstance(node, str) and node.startswith("/"):
            yield path

    assert list(walk(parent.document)) == [
        "$." + ".".join(keys) for keys in mb.LOCATION_FIELDS
    ]


def test_the_cola_history_on_disk_is_the_parents(parent):
    """The re-execution will record this checkout's COLA history; by the
    location rule it must equal the parent's record exactly."""

    recorded = parent.document["inputs"]["source"]["cola_history"]
    here = dict(load_cola_history().provenance)
    check = common.compare_exact(
        "cola_history",
        mb.located({"inputs": {"source": {"cola_history": recorded}}}),
        mb.located({"inputs": {"source": {"cola_history": here}}}),
    )
    assert check.identical, check.differences


def test_the_environment_fields_are_recorded(parent):
    script = _script()
    environment = parent.sidecar["environment"]
    for field in script.ENVIRONMENT_FIELDS:
        value = environment
        for key in field.split("."):
            value = value[key]
        assert isinstance(value, str) and value, field


def _pins(exercise="min-benefit") -> dict:
    completed = subprocess.run(
        [
            "bash",
            str(VENV_SCRIPT),
            "--check-only",
            "--source-python",
            sys.executable,
            "--exercise",
            exercise,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_the_repro_venv_script_pins_the_parents_environment(parent):
    environment = parent.sidecar["environment"]
    manifest = _pins()
    assert manifest["versions"] == {
        "python": environment["python"],
        "numpy": environment["packages"]["numpy"],
        "pandas": environment["packages"]["pandas"],
        "scipy": environment["packages"]["scipy"],
        "policyengine-social-security-model": environment["packages"][
            "policyengine-social-security-model"
        ],
    }
    assert (
        manifest["parameter_revision"]
        == environment["policyengine_us_parameters"]["revision"]
    )
    assert manifest["scipy_pin_provenance"] == "recorded sidecar"


def test_the_repro_venv_script_asks_for_the_gil_build():
    text = VENV_SCRIPT.read_text(encoding="utf-8")
    assert '--python "${PYTHON_VERSION}+gil"' in text
    assert "Py_GIL_DISABLED" in text
    assert "replication_urban2006_minimum_benefit_v1" in text


def test_the_parent_names_the_files_both_readers_record(parent):
    """The side frame's reader and Track M's must agree on shared bytes;
    the parent records Track M's by repository-relative path."""

    files = parent.document["inputs"]["source"]["psid_files_sha256"]
    assert all(not name.startswith("/") for name in files)
    json.dumps(files)


@pytest.mark.parametrize(
    "exercise", ("cola", "fra68", "uniform-cut", "min-benefit")
)
def test_one_environment_builder_selects_each_exact_sidecar(exercise):
    manifest = _pins(exercise)
    selected = manifest["source_sidecars"][exercise]
    path = Path(selected["sidecar"])
    assert common.file_sha256(path) == selected["sha256"]
    environment = json.loads(path.read_text())["environment"]
    assert manifest["versions"]["python"] == environment["python"]
    for package in ("numpy", "pandas", "scipy"):
        if package in environment["packages"]:
            assert (
                manifest["versions"][package]
                == environment["packages"][package]
            )
        else:
            assert package not in manifest["versions"]
    assert (
        "original version unrecorded" in manifest["scipy_pin_provenance"]
        if exercise == "uniform-cut"
        else manifest["scipy_pin_provenance"] == "recorded sidecar"
    )
