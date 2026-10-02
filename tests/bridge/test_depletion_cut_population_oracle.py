"""Live PE-US 2.18.0 checks, exclusively on invented entity-table frames.

The interpreter is POPULACE_DYNAMICS_PE_US_PYTHON, otherwise the bridge's
pinned default. A missing interpreter skips this oracle tier. Children run
sequentially, with an explicit dataset and timeout; no real frame is opened.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest

from populace_dynamics.bridge import depletion_cut_population as population
from populace_dynamics.bridge import depletion_cut_population_child as child
from populace_dynamics.bridge import policyengine_us as bridge

CHILD = Path(child.__file__).resolve()
INTERPRETER = Path(
    os.environ.get(
        "POPULACE_DYNAMICS_PE_US_PYTHON", str(bridge.DEFAULT_PE_US_PYTHON)
    )
).expanduser()
pytestmark = pytest.mark.skipif(
    not INTERPRETER.is_file(), reason="PE-US oracle interpreter is missing"
)


def _job(
    job: dict, *, expect_success: bool = True
) -> dict | subprocess.CompletedProcess:
    """Run one child at a time, limiting BLAS threads on the small host."""
    result = subprocess.run(
        [str(INTERPRETER), str(CHILD)],
        input=json.dumps(job),
        text=True,
        capture_output=True,
        timeout=7200,
        env={
            **os.environ,
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        },
    )
    if not expect_success:
        return result
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def oracle(tmp_path_factory):
    """Use one tiny frame and four sequential baseline/cut scenario children."""
    directory = tmp_path_factory.mktemp("depletion-population-invented")
    frame = directory / "invented.h5"
    written = _job(
        {
            "mode": "write-invented",
            "frame_path": str(frame),
            "households": 12,
            "persons": 30,
            "seed": 20261001,
            "labels": ["INVENTED DRY RUN - NOT RESULTS", *population.LABELS],
            "named_differences": population.NAMED_DIFFERENCES,
        }
    )
    common = {
        "frame_path": str(frame),
        "expected_sha256": written["sha256"],
        "registered": False,
        "labels": ["INVENTED DRY RUN - NOT RESULTS", *population.LABELS],
        "named_differences": population.NAMED_DIFFERENCES,
    }
    probe_meta = _job(
        {
            **common,
            "mode": "probe",
            "output_path": str(directory / "probe.npz"),
        }
    )
    with np.load(probe_meta["array_path"], allow_pickle=False) as saved:
        probe = {name: saved[name].copy() for name in saved.files}
    components = {name: probe[name].copy() for name in child.COMPONENTS}
    # The examples describe 2026 benefits. Override only these invented
    # component arrays to their 2026 amounts, rather than assuming uprating.
    for values in components.values():
        values[:10] = 0
    components[child.COMPONENTS[0]][:10] = [
        8916,
        8916,
        8916,
        4000,
        4000,
        4000,
        0,
        4000,
        4000,
        0,
    ]
    cut, _, person_cut = population.cut_components(
        components, "oasi22", Decimal("0.78")
    )
    scenario_inputs = {"baseline": components, "oasi22": cut}
    runs, metadata = {}, {}
    for scenario, inputs in scenario_inputs.items():
        inputs_path = directory / f"{scenario}-inputs.npz"
        np.savez(inputs_path, **inputs)
        for variant in population.VARIANTS:
            key = (scenario, variant)
            meta = _job(
                {
                    **common,
                    "mode": "scenario",
                    "variant": variant,
                    "components_path": str(inputs_path),
                    "output_path": str(
                        directory / f"{scenario}-{variant}.npz"
                    ),
                }
            )
            metadata[key] = meta
            with np.load(meta["array_path"], allow_pickle=False) as saved:
                runs[key] = {name: saved[name].copy() for name in saved.files}
    return {
        "directory": directory,
        "frame": frame,
        "common": common,
        "probe": probe,
        "components": scenario_inputs,
        "person_cut": person_cut,
        "runs": runs,
        "metadata": metadata,
    }


def test_probe_order_carry_forward_and_float32_components(oracle):
    probe = oracle["probe"]
    assert np.array_equal(probe["person_id"], np.arange(1, 31))
    assert np.array_equal(probe["age"], probe["frame_age"])
    assert np.array_equal(probe["household_id"], np.arange(1, 13))
    for name in child.COMPONENTS:
        assert probe[name].dtype == np.dtype("float64")
        assert np.array_equal(probe[name], probe[name].astype(np.float32))
    assert np.bincount(probe["unit_index"]).max() == 2
    assert set(probe["person_support_channel"]) == {"cps", "puf_tax_detail"}


def test_set_input_overrides_extended_holders_for_all_components(oracle):
    for (scenario, _variant), run in oracle["runs"].items():
        expected = oracle["components"][scenario]
        for name in child.COMPONENTS:
            assert np.allclose(run[name], expected[name], rtol=0, atol=0.01)
            assert np.array_equal(
                run[f"baseline_{name}"], oracle["probe"][name]
            )
        assert np.allclose(
            run["social_security"],
            np.sum(list(expected.values()), axis=0),
            rtol=0,
            atol=0.05,
        )


@pytest.mark.parametrize("scenario", ["baseline", "oasi22"])
def test_structural_reform_and_person_level_ssi_identity(oracle, scenario):
    encoded = oracle["runs"][(scenario, "asset_test_as_encoded")]
    no_test = oracle["runs"][(scenario, "no_asset_test")]
    assert no_test["meets_ssi_resource_test"].all()
    assert not encoded["meets_ssi_resource_test"].all()
    assert float(encoded["individual_limit"]) == 2000
    assert float(encoded["couple_limit"]) == 3000
    for name in ("ssi_if_takes_up", "ssi"):
        assert np.allclose(
            encoded[name],
            no_test[name] * encoded["meets_ssi_resource_test"],
            rtol=0,
            atol=0.01,
        )


def test_annual_ssi_sums_and_take_up_identity(oracle):
    baseline = oracle["runs"][("baseline", "asset_test_as_encoded")]
    assert baseline["ssi_if_takes_up"][0] == pytest.approx(3252, abs=0.01)
    no_test = oracle["runs"][("baseline", "no_asset_test")]
    assert no_test["ssi_if_takes_up"][1] > 0
    assert not no_test["takes_up_ssi_if_eligible"][1]
    assert no_test["ssi"][1] == 0
    for run in oracle["runs"].values():
        assert np.allclose(
            run["ssi"],
            run["ssi_if_takes_up"] * run["takes_up_ssi_if_eligible"],
            atol=0.01,
            rtol=0,
        )
        assert run["immigration_status"].dtype.kind == "U"


def test_worked_single_cases_full_or_completely_blocked(oracle):
    labels = {}
    for variant in population.VARIANTS:
        baseline = oracle["runs"][("baseline", variant)]
        cut = oracle["runs"][("oasi22", variant)]
        labels[variant] = population.replacement_labels(
            oracle["person_cut"],
            baseline["ssi_if_takes_up"],
            cut["ssi_if_takes_up"],
            oracle["probe"]["unit_index"],
        )
    assert oracle["person_cut"][0] == 1968
    assert labels["asset_test_as_encoded"][:3].tolist() == [
        population.FULL,
        population.NONE,
        population.NONE,
    ]
    assert labels["no_asset_test"][:3].tolist() == [population.FULL] * 3
    print(
        "invented single cases: cut=1968, bank1500 full/full; "
        "bank50000 none/full; stocks2500 none/full"
    )


def test_joint_and_non_abd_spouse_resource_tests(oracle):
    encoded = oracle["runs"][("baseline", "asset_test_as_encoded")]
    assert encoded["ssi_claim_is_joint"][3:5].all()
    assert encoded["meets_ssi_resource_test"][3:5].all()
    assert not encoded["ssi_claim_is_joint"][5:7].any()
    assert encoded["meets_ssi_resource_test"][5:7].tolist() == [False, True]
    r3 = population.resource_test_spousal(
        encoded["ssi_countable_resources"],
        oracle["probe"]["unit_index"],
        np.bincount(oracle["probe"]["unit_index"]),
        2000,
        3000,
    )
    assert r3[5:7].all()


def test_older_parent_couple_is_partly_blocked_encoded_and_blocked_r3(oracle):
    base = oracle["runs"][("baseline", "asset_test_as_encoded")]
    no_base = oracle["runs"][("baseline", "no_asset_test")]
    cut = oracle["runs"][("oasi22", "asset_test_as_encoded")]
    no_cut = oracle["runs"][("oasi22", "no_asset_test")]
    units = oracle["probe"]["unit_index"]
    assert not base["ssi_claim_is_joint"][7:9].any()
    assert base["meets_ssi_resource_test"][7:9].tolist() == [False, True]
    encoded_labels = population.replacement_labels(
        oracle["person_cut"],
        base["ssi_if_takes_up"],
        cut["ssi_if_takes_up"],
        units,
    )
    no_labels = population.replacement_labels(
        oracle["person_cut"],
        no_base["ssi_if_takes_up"],
        no_cut["ssi_if_takes_up"],
        units,
    )
    assert encoded_labels[7:9].tolist() == [population.PART] * 2
    assert no_labels[7:9].tolist() == [population.FULL] * 2
    r3 = population.resource_test_spousal(
        base["ssi_countable_resources"], units, np.bincount(units), 2000, 3000
    )
    r3_labels = population.replacement_labels(
        oracle["person_cut"],
        no_base["ssi_if_takes_up"] * r3,
        no_cut["ssi_if_takes_up"] * r3,
        units,
    )
    assert r3_labels[7:9].tolist() == [population.NONE] * 2
    print("invented older-parent couple: encoded part/full; R3 none/full")


def test_real_frame_hash_guard_refuses_without_opening_hdf(
    tmp_path, monkeypatch
):
    fake = tmp_path / "fake.h5"
    fake.write_bytes(b"invented fake bytes, never the real frame")
    monkeypatch.setattr(child, "_sha256", lambda _path: child.FRAME_SHA256)
    with pytest.raises(ValueError, match="real frame"):
        child._check_frame(
            fake, expected_sha256=child.FRAME_SHA256, registered=False
        )


def test_child_refuses_non_invented_file_and_wrong_hash(oracle):
    directory = oracle["directory"]
    foreign = directory / "not-invented.h5"
    shutil.copyfile(oracle["frame"], foreign)
    removed = subprocess.run(
        [
            str(INTERPRETER),
            "-c",
            "import pandas as pd, sys; "
            "store = pd.HDFStore(sys.argv[1], mode='a'); "
            "store.remove('invented'); store.close()",
            str(foreign),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        env={
            **os.environ,
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        },
    )
    assert removed.returncode == 0, removed.stderr
    refused = _job(
        {
            "mode": "probe",
            "frame_path": str(foreign),
            "expected_sha256": hashlib.sha256(
                foreign.read_bytes()
            ).hexdigest(),
            "registered": False,
            "output_path": str(directory / "refused.npz"),
        },
        expect_success=False,
    )
    assert refused.returncode != 0
    assert "invented marker table" in refused.stderr
    assert not (directory / "refused.npz").exists()
    wrong_hash = _job(
        {
            **oracle["common"],
            "mode": "probe",
            "expected_sha256": "0" * 64,
            "output_path": str(directory / "wrong-hash.npz"),
        },
        expect_success=False,
    )
    assert wrong_hash.returncode != 0
    assert "SHA-256" in wrong_hash.stderr


def test_default_microsimulation_guard_and_process_metadata(oracle):
    with pytest.raises(ValueError, match="explicit dataset"):
        child._microsimulation(None, None)
    for metadata in oracle["metadata"].values():
        assert metadata["dataset_end_year"] == 2026
        assert metadata["checks"] == {
            "explicit_dataset": True,
            "frame_guard": True,
        }
        assert metadata["peak_rss_bytes"] > 0
        assert metadata["timings"]["total_seconds"] > 0


def test_raw_arrays_carry_every_output_label(oracle):
    for run in oracle["runs"].values():
        assert run["metadata_labels"].tolist() == [
            "INVENTED DRY RUN - NOT RESULTS",
            *population.LABELS,
        ]
        assert json.loads(str(run["metadata_named_differences"])) == list(
            population.NAMED_DIFFERENCES
        )
