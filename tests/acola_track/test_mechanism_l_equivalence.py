"""Registration 18's seeded invented mechanism-L regression evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from populace_dynamics.acola_track.config import REGISTERED_ROWS

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/acola_mechanism_l_equivalence.py"
GOLDEN = Path(__file__).with_name("mechanism_l_dd222b9.json")
PROVENANCE = GOLDEN.with_suffix(".provenance.json")


@lru_cache(maxsize=1)
def equivalence_script():
    spec = importlib.util.spec_from_file_location("_acola_equivalence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mechanism_l_is_bit_identical_to_registration_commit(tmp_path):
    output = tmp_path / "head.json"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(ROOT),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    actual, expected = output.read_bytes(), GOLDEN.read_bytes()
    if actual != expected:
        differences = equivalence_script().differing_people(
            json.loads(expected), json.loads(actual)
        )
        raise AssertionError(
            "REG18_MECHANISM_DRIFT: "
            + (", ".join(differences) or "canonical JSON metadata/encoding")
        )


def test_historical_golden_pins_source_script_and_output():
    provenance = json.loads(PROVENANCE.read_text())
    assert provenance["registered_commit"] == (
        "dd222b9af926c773a0f92732e2d08be507793378"
    )
    assert (
        provenance["script_sha256"]
        == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    )
    assert (
        provenance["golden_sha256"]
        == hashlib.sha256(GOLDEN.read_bytes()).hexdigest()
    )
    assert provenance["historical_command"]
    assert provenance["historical_source_files"]


def test_historical_interface_rows_match_new_registry():
    for row in equivalence_script().registered_rows():
        assert row == REGISTERED_ROWS[row.row_id].track_row()


def test_invented_population_exercises_old_dual_entitlement_and_components():
    value = json.loads(GOLDEN.read_text())
    assert tuple(value["rows"]) == equivalence_script().ROW_IDS
    assert value["seed"] == 20261024
    for people in value["rows"].values():
        assert {person["birth_year"] for person in people.values()} >= set(
            range(1917, 1943)
        )
        components = set()
        for person in people.values():
            components.update(person["components"])
            if (
                1917 <= person["birth_year"] <= 1942
                and person["basis"] == "projected"
            ):
                assert person["components"]["retired_worker"]["base"] > 0
        assert components == {
            "retired_worker",
            "disabled_worker",
            "spouse",
            "aged_widow",
            "disabled_widow",
        }
        dual = [
            p
            for p in people.values()
            if 1917 <= p["birth_year"] <= 1942
            and "spouse" in p["components"]
            and p["basis"] == "projected"
        ]
        assert {p["birth_year"] for p in dual} == set(range(1917, 1943))
    assert value["rows"]["M0"] == value["rows"]["M4"]
    assert value["rows"]["C0"] != value["rows"]["C1"]
    assert value["rows"]["M0"] != value["rows"]["M1"]
    assert value["rows"]["M0"] != value["rows"]["M2"]
    assert value["rows"]["M0"] != value["rows"]["M3"]
