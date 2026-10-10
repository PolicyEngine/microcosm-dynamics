"""gate_epuf_fill's committed floors recompute from what they store.

``runs/epuf_fill_gate_floors_v3.json`` is the registered DEV floor build
(amendment 1 with referee round 2's fixes); its rules, cell helpers and
builders are bound to the commit it ran at, and its sample sizes, seeds,
sigmas, tolerances, partition and checks on bite recompute from the stored
replicates and the PSID-2010 counts
(``runs/epuf_fill_gate_psid_scale_v2.json``). Its floors, tolerances and
partition equal the v2 build's exactly: round 2's fixes changed the
scoring of fills, not the floors. ``runs/epuf_fill_gate_floors_v1.json``
(the first build) and ``..._v2.json`` are superseded and frozen; they must
stay internally consistent.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness.epuf_cells import CellValue

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
BUILDS = {
    "v1": (
        RUNS / "epuf_fill_gate_floors_v1.json",
        RUNS / "epuf_fill_gate_psid_scale_v1.json",
    ),
    "v2": (
        RUNS / "epuf_fill_gate_floors_v2.json",
        RUNS / "epuf_fill_gate_psid_scale_v2.json",
    ),
    "v3": (
        RUNS / "epuf_fill_gate_floors_v3.json",
        RUNS / "epuf_fill_gate_psid_scale_v2.json",
    ),
}
REGISTERED = "v3"
#: Files whose bytes at the registered build's commit must equal the
#: checkout's: the rules, the cell helpers, the wage bases and the builders.
BOUND_FILES = (
    "src/populace_dynamics/harness/epuf_fill_gate.py",
    "src/populace_dynamics/harness/epuf_cells.py",
    "src/populace_dynamics/harness/epuf_operator.py",
    "scripts/build_epuf_fill_gate_floors.py",
    "scripts/build_epuf_fill_psid_scale.py",
)


def _load(version):
    floors, scale = BUILDS[version]
    return json.loads(floors.read_text()), json.loads(scale.read_text())


@pytest.fixture(scope="module", params=sorted(BUILDS))
def build(request):
    floors, scale = _load(request.param)
    return request.param, floors, scale


@pytest.fixture(scope="module")
def registered():
    return _load(REGISTERED)


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_epuf_fill_gate_floors",
        ROOT / "scripts" / "build_epuf_fill_gate_floors.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_build_is_a_dev_build_with_the_registered_constants(build):
    version, floors, _ = build
    assert floors["schema"] == (
        f"populace_dynamics.epuf_fill_gate_floors.{version}"
    )
    assert floors["registration_id"] == g.REGISTRATION_ID
    assert floors["part"] == "dev"
    assert floors["registered_build"] is True
    assert floors["constants"] == {
        "k_tolerance": g.K_TOLERANCE,
        "min_events": g.MIN_EVENTS,
        "events_share": g.EVENTS_SHARE,
        "bite_multiple": g.BITE_MULTIPLE,
        "n_floor_replicates": g.N_FLOOR_REPLICATES,
        "floor_seed_base": g.FLOOR_SEED_BASE,
    }
    assert floors["oracles"]["seeds"] == list(g.ORACLE_SEEDS)


def test_inputs_hash_to_the_committed_scale_and_pinned_epuf(build):
    from populace_dynamics.data import epuf

    version, floors, scale = build
    assert floors["inputs"]["epuf_sha256"] == epuf.EPUF_SHA256
    assert (
        floors["inputs"]["psid_scale_sha256"]
        == hashlib.sha256(BUILDS[version][1].read_bytes()).hexdigest()
    )
    assert scale["registration_id"] == g.REGISTRATION_ID
    assert scale["n_members"] == 11_405


def _sigma(values):
    values = np.array([float(x) for x in values])
    return (
        float(np.sqrt(np.mean(values**2)))
        if np.isfinite(values).all()
        else float("nan")
    )


def test_sizes_seeds_and_sigmas_recompute(build):
    version, floors, scale = build
    groups = sorted(floors["groups"])
    assert groups == sorted({g.group_of(cell) for cell in floors["truth"]})
    for index, group in enumerate(groups):
        record = floors["groups"][group]
        n = record["sample_size"]
        assert record["group_index"] == index
        assert record["seed"] == [
            g.FLOOR_SEED_BASE,
            index,
            g.N_FLOOR_REPLICATES,
            n,
        ]
        basis = record["sample_size_basis"]
        counts = scale["groups"][group]
        if "psid_persons" in basis:
            assert n == counts["persons"] == basis["psid_persons"]
        else:
            assert basis["psid_filled_person_years"] == (
                counts["filled_person_years"]
            )
            assert n == round(
                basis["psid_filled_person_years"]
                / basis["dev_units_per_eligible_person"]
            )
        assert 2 * n <= record["pool_size"]
        # A cohort group's pool is exactly the population its cells count.
        if "psid_persons" in basis and version != "v1":
            cells = [
                c
                for c in floors["truth"]
                if c.startswith(f"{group}.") and "aime_p50" in c
            ]
            assert cells, group
            assert record["pool_size"] == floors["truth"][cells[0]]["n"]
        assert record["noise_ratio"] == pytest.approx(
            np.sqrt(n / record["pool_size"])
        )
        for cell, replicates in record["replicates"].items():
            assert len(replicates) == g.N_FLOOR_REPLICATES
            stored = float(record["sigma"][cell])
            expected = _sigma(replicates)
            if np.isnan(expected):
                assert np.isnan(stored)
            else:
                assert stored == pytest.approx(expected)


def _floor_groups(floors):
    return {
        group: g.FloorGroup(
            group=group,
            sample_size=record["sample_size"],
            pool_size=record["pool_size"],
            seed=tuple(record["seed"]),
            replicates={},
            sigma={k: float(v) for k, v in record["sigma"].items()},
            min_events={k: tuple(v) for k, v in record["min_events"].items()},
        )
        for group, record in floors["groups"].items()
    }


def test_partition_and_tolerances_recompute(build):
    _, floors, _ = build
    truth = {
        cell: CellValue(float(row["value"]), row["events"], row["n"])
        for cell, row in floors["truth"].items()
    }
    floor_groups = _floor_groups(floors)
    assert g.partition(truth, floor_groups) == floors["partition"]
    gating = {c for c, r in floors["partition"].items() if r == "gates"}
    assert set(floors["tolerance"]) == gating
    for cell in gating:
        sigma = floor_groups[g.group_of(cell)].sigma[cell]
        assert floors["tolerance"][cell] == pytest.approx(
            g.K_TOLERANCE * sigma
        )


@pytest.mark.parametrize(
    ("bite", "family"),
    [("B1_current_odd_rule", "odd"), ("B2_current_pre_career_rule", "pre")],
)
def test_checks_on_bite_hold_and_recompute(build, bite, family):
    _, floors, _ = build
    record = floors["bites"][bite]
    multiples = []
    for cell, row in record["score"]["cells"].items():
        assert cell.startswith(f"{family}.")
        if "tolerance" not in row:
            continue
        gap = float(row["gap"])
        expected = abs(gap) / row["tolerance"] if np.isfinite(gap) else np.inf
        assert float(row["gap_in_tolerances"]) == pytest.approx(expected)
        assert row["passes"] == bool(
            np.isfinite(gap) and abs(gap) <= row["tolerance"]
        )
        multiples.append(expected)
    beyond = sum(m > g.BITE_MULTIPLE for m in multiples)
    assert record["n_cells_beyond_bite_multiple"] == beyond
    assert record["holds"] is True and beyond >= 1
    assert record["score"]["passes"] is False
    assert floors["lockable"] is True


def test_oracles_score_every_gating_cell_of_their_family(build):
    _, floors, _ = build
    for name, family in (
        ("O1_odd_conditional_permutation", "odd"),
        ("O2_pre_career_block_permutation", "pre"),
    ):
        gating_in_family = {
            c
            for c, r in floors["partition"].items()
            if r == "gates" and c.startswith(f"{family}.")
        }
        scored = {
            c
            for c, row in floors["oracles"][name]["cells"].items()
            if "passes" in row
        }
        assert scored == gating_in_family


# -- the registered build only ----------------------------------------------
def test_registered_build_covers_the_amended_groups(registered):
    floors, scale = registered
    assert sorted(floors["groups"]) == g.groups()
    assert sorted(scale["groups"]) == g.groups()
    # The builder can read TRAIN or DEV, never TEST.
    assert set(_builder().PARTS.values()) == {g.TRAIN, g.DEV}


def _assert_bound(commit: str, paths) -> None:
    probe = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
    )
    if probe.returncode != 0:
        pytest.skip("the build's commit is not in this clone")
    for path in paths:
        built = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
            capture_output=True,
            check=True,
        ).stdout
        assert built == (ROOT / path).read_bytes(), (commit, path)


def test_registered_build_is_bound_to_its_rules(registered):
    floors, scale = registered
    _assert_bound(floors["code_commit"], BOUND_FILES)
    assert floors["bound_files_clean"] is True
    # The PSID counts depend only on their script and the group definitions
    # (checked against groups() above).
    _assert_bound(
        scale["code_commit"], ["scripts/build_epuf_fill_psid_scale.py"]
    )


def test_registered_build_reports_the_dosed_perturbations(registered):
    floors, _ = registered
    doses = floors["dosed_perturbations"]
    for name in (
        "D1_copy_next_year_share",
        "D2_marginal_within_sex_age",
        "D3_shrink_to_median_lambda_0.75",
        "D3_shrink_to_median_lambda_0.5",
        "D4_scale_pre_blocks_0.95",
        "D4_scale_pre_blocks_0.9",
        "D5_blocks_within_sex_birth_year",
        "D6_years_independent_within_sex_birth_year",
    ):
        record = doses[name]
        assert record["score"]["passes"] is False, name
        assert record["n_failing"] >= 1, name
    for name in (
        "D3_shrink_to_median_lambda_dose_at_tolerances",
        "D4_scale_pre_blocks_dose_at_tolerances",
    ):
        one, two = (float(doses[name][key]) for key in ("1", "2"))
        assert 0 < one < two


def test_registered_floors_equal_the_v2_floors_exactly(registered):
    floors, _ = registered
    v2, _ = _load("v2")
    assert floors["truth"] == v2["truth"]
    assert floors["partition"] == v2["partition"]
    assert floors["tolerance"] == v2["tolerance"]
    for group, record in floors["groups"].items():
        old = v2["groups"][group]
        for key in (
            "sample_size",
            "pool_size",
            "seed",
            "sigma",
            "replicates",
            "min_events",
        ):
            assert record[key] == old[key], (group, key)


def test_registered_build_was_clean_and_names_its_dose_cells(registered):
    floors, _ = registered
    assert floors["bound_files_clean"] is True
    doses = floors["dosed_perturbations"]
    for name in (
        "D3_shrink_to_median_lambda_dose_at_tolerances",
        "D4_scale_pre_blocks_dose_at_tolerances",
    ):
        assert doses[name]["1_cell"] in floors["tolerance"]
        assert doses[name]["1_aime_cell"] in floors["tolerance"]
    # The odd family's checks never move a pre-career odd year.
    assert "D1_copy_next_year_share" in doses


def test_the_scoring_module_pins_the_registered_build(registered):
    from populace_dynamics.harness import epuf_fill_scoring as scoring

    path = BUILDS[REGISTERED][0]
    assert scoring.REGISTERED_FLOORS == path
    assert (
        scoring.REGISTERED_FLOORS_SHA256
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    loaded = scoring.load_registered_floors()
    assert loaded["gating"] == sorted(
        c for c, r in registered[0]["partition"].items() if r == "gates"
    )
