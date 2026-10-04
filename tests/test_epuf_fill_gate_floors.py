"""gate_epuf_fill's committed floors recompute from what they store.

Pins ``runs/epuf_fill_gate_floors_v1.json`` (the DEV floor build) and
``runs/epuf_fill_gate_psid_scale_v1.json`` (the PSID-2010 counts) to the
registration's rules: sample sizes, seeds, sigmas, tolerances, the
partition, the checks on bite and the lock condition.
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
FLOORS = ROOT / "runs" / "epuf_fill_gate_floors_v1.json"
SCALE = ROOT / "runs" / "epuf_fill_gate_psid_scale_v1.json"
#: Files whose bytes at the floor build's commit must equal the checkout's:
#: the rules and the builders that ran.
BOUND_FILES = (
    "src/populace_dynamics/harness/epuf_fill_gate.py",
    "scripts/build_epuf_fill_gate_floors.py",
    "scripts/build_epuf_fill_psid_scale.py",
)


def _number(value):
    """Floats stored as JSON numbers or, when not finite, as strings."""
    return float(value)


@pytest.fixture(scope="module")
def floors():
    return json.loads(FLOORS.read_text())


@pytest.fixture(scope="module")
def scale():
    return json.loads(SCALE.read_text())


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_epuf_fill_gate_floors",
        ROOT / "scripts" / "build_epuf_fill_gate_floors.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_build_is_the_registered_dev_build(floors):
    assert floors["schema"] == "populace_dynamics.epuf_fill_gate_floors.v1"
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
    # The builder can read TRAIN or DEV, never TEST.
    assert set(_builder().PARTS.values()) == {g.TRAIN, g.DEV}


def test_inputs_hash_to_the_committed_scale_and_pinned_epuf(floors, scale):
    from populace_dynamics.data import epuf

    assert floors["inputs"]["epuf_sha256"] == epuf.EPUF_SHA256
    assert (
        floors["inputs"]["psid_scale_sha256"]
        == hashlib.sha256(SCALE.read_bytes()).hexdigest()
    )
    assert scale["registration_id"] == g.REGISTRATION_ID
    assert scale["n_members"] == 11_405


def test_bound_files_are_unchanged_since_the_build(floors):
    commit = floors["code_commit"]
    probe = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
    )
    if probe.returncode != 0:
        pytest.skip("the floor build's commit is not in this clone")
    for path in BOUND_FILES:
        built = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
            capture_output=True,
            check=True,
        ).stdout
        assert built == (ROOT / path).read_bytes(), path


def test_groups_cover_every_cell_with_registered_sizes_and_seeds(
    floors, scale
):
    groups = sorted({g.group_of(cell) for cell in floors["truth"]})
    assert sorted(floors["groups"]) == groups
    assert len(groups) == 24
    for index, group in enumerate(groups):
        record = floors["groups"][group]
        assert record["group_index"] == index
        n = record["sample_size"]
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
        assert record["noise_ratio"] == pytest.approx(
            np.sqrt(n / record["pool_size"])
        )


def test_sigmas_recompute_from_the_stored_replicates(floors):
    for record in floors["groups"].values():
        for cell, replicates in record["replicates"].items():
            values = np.array([_number(x) for x in replicates])
            assert len(values) == g.N_FLOOR_REPLICATES
            stored = _number(record["sigma"][cell])
            if np.isfinite(values).all():
                assert stored == pytest.approx(np.sqrt(np.mean(values**2)))
            else:
                assert np.isnan(stored)


def _floor_groups(floors):
    return {
        group: g.FloorGroup(
            group=group,
            sample_size=record["sample_size"],
            pool_size=record["pool_size"],
            seed=tuple(record["seed"]),
            replicates={},
            sigma={k: _number(v) for k, v in record["sigma"].items()},
            min_events={k: tuple(v) for k, v in record["min_events"].items()},
        )
        for group, record in floors["groups"].items()
    }


def test_partition_and_tolerances_recompute(floors):
    truth = {
        cell: CellValue(_number(row["value"]), row["events"], row["n"])
        for cell, row in floors["truth"].items()
    }
    groups = _floor_groups(floors)
    assert g.partition(truth, groups) == floors["partition"]
    gating = {c for c, r in floors["partition"].items() if r == "gates"}
    assert set(floors["tolerance"]) == gating
    for cell in gating:
        sigma = groups[g.group_of(cell)].sigma[cell]
        assert floors["tolerance"][cell] == pytest.approx(
            g.K_TOLERANCE * sigma
        )
    assert len(gating) == 130


@pytest.mark.parametrize(
    ("bite", "family"),
    [("B1_current_odd_rule", "odd"), ("B2_current_pre_career_rule", "pre")],
)
def test_checks_on_bite_hold_and_recompute(floors, bite, family):
    record = floors["bites"][bite]
    cells = record["score"]["cells"]
    multiples = []
    for cell, row in cells.items():
        assert cell.startswith(f"{family}.")
        if "tolerance" not in row:
            continue
        gap = _number(row["gap"])
        expected = abs(gap) / row["tolerance"] if np.isfinite(gap) else np.inf
        assert _number(row["gap_in_tolerances"]) == pytest.approx(expected)
        assert row["passes"] == bool(
            np.isfinite(gap) and abs(gap) <= row["tolerance"]
        )
        multiples.append(expected)
    beyond = sum(m > g.BITE_MULTIPLE for m in multiples)
    assert record["n_cells_beyond_bite_multiple"] == beyond
    assert record["holds"] is True and beyond >= 1
    assert record["score"]["passes"] is False


def test_the_gate_is_lockable(floors):
    assert floors["lockable"] is True


def test_oracles_are_reported_without_changing_the_partition(floors):
    for name, family in (
        ("O1_odd_conditional_permutation", "odd"),
        ("O2_pre_career_block_permutation", "pre"),
    ):
        result = floors["oracles"][name]
        gating_in_family = {
            c
            for c, r in floors["partition"].items()
            if r == "gates" and c.startswith(f"{family}.")
        }
        scored = {c for c, row in result["cells"].items() if "passes" in row}
        assert scored == gating_in_family
