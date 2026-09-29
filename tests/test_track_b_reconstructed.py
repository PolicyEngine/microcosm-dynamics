"""Invented-data tests of Track B B1 v2, the reconstructed-reproduction baseline.

Decision d571 (2026-09-28) ruled a new registered B1 version that passes as
RECONSTRUCTED_REPRODUCTION only when four exact conditions hold. Invariants
stated and tested here:

I1. Admission: the status is RECONSTRUCTED_REPRODUCTION, ``equal is True``
    and the scope is exactly ADMITTED_SCOPE if and only if all four
    registered conditions pass. Otherwise the status is
    BASELINE_REPLAY_MISMATCH, ``equal is False``, the scope is "none", and
    ``failed_conditions`` names every failing condition in registered order.
I2. Cells: any single change to any one of the 600 committed cells, or to
    either side's computed value for it (one ulp, sign of zero, NaN, type,
    absence), fails condition 1 and the diagnostics name exactly that cell.
I3. Cell order is immaterial: permuting per-seed rows, cell entries or the
    observed values leaves the comparison result unchanged.
I4. Each condition fails the run on its own when only it is perturbed.
I5. v2 never yields REPRODUCED; v1 never yields RECONSTRUCTED_REPRODUCTION.
I6. The guard admits a v2 claim only when it re-derives all four conditions
    from the published evidence, and refuses every other claim.
I7. Determinism: the same invented inputs give byte-identical evidence and
    an identical result.
I8. Differential: the guard's payload-level person comparison and the run's
    ``compare_frames`` agree on equality for invented frames.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.harness import m6_candidate3_runner
from populace_dynamics.harness.m6_scoring import EARNINGS_CELL_NAMES
from populace_dynamics.track_b import reconstructed, runner
from populace_dynamics.track_b.equality import compare_frames
from tests.test_track_b_runner import _invented_differential_inputs

SETTINGS = settings(
    deadline=None,
    max_examples=60,
    suppress_health_check=[HealthCheck.too_slow],
)
ANCHOR = {
    "pe_us_root": "/invented/anchor/.venv/lib/python3.14/site-packages",
    "command": list(reconstructed.LOADER_REVISION_COMMAND),
    "git_environment": {},
    "loader_revision": "f10cca5",
    "head": runner.BASELINE_COMMIT,
    "toplevel": "/invented/anchor",
    "core_abbrev": "7",
    "tracked_clean": True,
}
LINEAGE_EXTRA = {
    "certified_full_window_artifacts_read": False,
    "certified_full_window_artifacts_written": False,
    "earnings_spec_registration": "invented-earnings-registration",
    "earnings_spec_sha256": "e" * 64,
    "engine_candidate_id": "invented_engine_v1",
    "floor_run": "invented/floors.json",
    "floor_sha256": "f" * 64,
}
PROVENANCE = {
    "boundary_year": 2014,
    "earnings_seed": 5200,
    "readers": {"earnings_panel": "invented.reader"},
    "external_vintages": {"ssa_parameters": 2014},
    "external_details": {
        "ssa_revision": "f10cca5",
        "claiming_schema": "invented_claim_ages.v1",
    },
    "source_rows": {"earnings": 40},
    "source_max_year": {"earnings": 2022, "mortality_exposure": None},
    "truth_rows": {"earnings": 22},
    "training_population": {"family": 8},
    "certified_full_window_artifacts_read": False,
    "certified_full_window_artifacts_written": False,
}
RUNTIME_IDENTITY = {
    "python": "3.14.4",
    "numpy": "2.5.1",
    "pandas": "3.0.3",
    "scipy": "1.18.0",
}
FREEZE = {
    "runtime": dict(RUNTIME_IDENTITY),
    "thread_environment": {"OMP_NUM_THREADS": "8"},
    "omp_wait_policy": "ACTIVE",
    "populace_fit": {"version": "0.1.0", "tracked_source_clean": True},
}


def _nextafter(value: float) -> float:
    return float(np.nextafter(value, np.inf))


# ---------------------------------------------------------------------------
# Pure checks of condition 1 (600 cells), admission and payload comparison
# ---------------------------------------------------------------------------
SEEDS, DRAWS = runner.REGISTERED_SEEDS, runner.REGISTERED_DRAWS
COVERAGE = [
    (seed, draw, cell)
    for seed in SEEDS
    for draw in DRAWS
    for cell in EARNINGS_CELL_NAMES
]


def _invented_cell_values() -> dict[tuple[int, int, str], float]:
    """600 distinct invented floats, including a signed zero."""
    values = {
        key: float(index) / 7.0 + 0.125 for index, key in enumerate(COVERAGE)
    }
    values[COVERAGE[0]] = 0.0
    values[COVERAGE[1]] = -0.0
    return values


def _registered_baseline(values, *, seed_order=None, rng=None) -> dict:
    rows = []
    for seed in seed_order or SEEDS:
        names = list(EARNINGS_CELL_NAMES)
        if rng is not None:
            rng.shuffle(names)
        rows.append(
            {
                "seed": seed,
                "gated_cells": {
                    cell: {
                        "per_draw_rate": [
                            values[seed, draw, cell] for draw in DRAWS
                        ]
                    }
                    for cell in names
                },
            }
        )
    return {"family_a": {"per_seed": rows}}


def _compare(baseline, observed):
    registered, problems = reconstructed.registered_cells(
        baseline, seeds=SEEDS, draws=DRAWS
    )
    return reconstructed.compare_cells(
        registered, observed, seeds=SEEDS, draws=DRAWS, problems=problems
    )


def test_the_registered_product_is_600_cells():
    assert len(COVERAGE) == 600
    values = _invented_cell_values()
    result = _compare(
        _registered_baseline(values),
        {side: dict(values) for side in reconstructed.SIDES},
    )
    assert result["equal"] is True
    assert result["status"] == reconstructed.PASS
    assert result["compared_cells"] == 600
    assert result["sides"] == ["replay", "original"]


PERTURBATIONS = {
    "next_up": lambda value: _nextafter(value),
    "next_down": lambda value: float(np.nextafter(value, -np.inf)),
    "negate": lambda value: -value,
    "nan": lambda value: float("nan"),
    "none": lambda value: None,
    "int": lambda value: int(round(value)),
    "numpy": lambda value: np.float64(value),
    "text": lambda value: repr(value),
}


@SETTINGS
@given(
    target=st.sampled_from(COVERAGE),
    where=st.sampled_from(["registered", "replay", "original"]),
    kind=st.sampled_from(sorted(PERTURBATIONS) + ["absent"]),
)
def test_any_single_cell_perturbation_fails_and_names_that_cell(
    target, where, kind
):
    values = _invented_cell_values()
    registered_values = dict(values)
    observed = {side: dict(values) for side in reconstructed.SIDES}
    if kind == "absent":
        if where == "registered":
            # Structural: the whole rate list for this cell loses its draw.
            seed, draw, cell = target
            baseline = _registered_baseline(registered_values)
            row = next(
                row
                for row in baseline["family_a"]["per_seed"]
                if row["seed"] == seed
            )
            row["gated_cells"][cell]["per_draw_rate"].pop(DRAWS.index(draw))
            result = _compare(baseline, observed)
            assert result["equal"] is False
            assert any(
                item.get("seed") == seed and item.get("cell") == cell
                for item in result["differences"]
            )
            return
        del observed[where][target]
    elif where == "registered":
        registered_values[target] = PERTURBATIONS[kind](values[target])
    else:
        observed[where][target] = PERTURBATIONS[kind](values[target])
    result = _compare(_registered_baseline(registered_values), observed)

    assert result["equal"] is False
    assert result["status"] == reconstructed.FAIL
    named = {
        (item["seed"], item["draw"], item["cell"])
        for item in result["differences"]
    }
    assert named == {target}


@SETTINGS
@given(
    seed_order=st.permutations(SEEDS),
    rng=st.randoms(use_true_random=False),
    target=st.none() | st.sampled_from(COVERAGE),
)
def test_cell_order_is_immaterial(seed_order, rng, target):
    values = _invented_cell_values()
    observed = {side: dict(values) for side in reconstructed.SIDES}
    if target is not None:
        observed["replay"][target] = _nextafter(values[target])
    canonical = _compare(_registered_baseline(values), observed)

    shuffled_observed = {}
    for side in reversed(reconstructed.SIDES):
        items = list(observed[side].items())
        rng.shuffle(items)
        shuffled_observed[side] = dict(items)
    permuted = _compare(
        _registered_baseline(values, seed_order=list(seed_order), rng=rng),
        shuffled_observed,
    )

    assert permuted == canonical
    assert canonical["equal"] is (target is None)


@pytest.mark.parametrize(
    "mutate, kind",
    [
        (lambda rows: rows.append(copy.deepcopy(rows[0])), "duplicate"),
        (lambda rows: rows.pop(), "missing_registered_seed"),
        (lambda rows: rows[0].update(seed=True), "registered_seed_type"),
        (lambda rows: rows[0].update(seed="0"), "registered_seed_type"),
        (
            lambda rows: rows.append({**copy.deepcopy(rows[0]), "seed": 99}),
            "extra_registered_seed",
        ),
        (lambda rows: rows[0].pop("gated_cells"), "missing_gated_cells"),
    ],
)
def test_registered_cell_structure_fails_closed(mutate, kind):
    values = _invented_cell_values()
    baseline = _registered_baseline(values)
    mutate(baseline["family_a"]["per_seed"])
    result = _compare(
        baseline, {side: dict(values) for side in reconstructed.SIDES}
    )
    assert result["equal"] is False
    assert any(kind in item["kind"] for item in result["differences"])


def test_extra_or_unregistered_observed_cells_fail_closed():
    values = _invented_cell_values()
    observed = {side: dict(values) for side in reconstructed.SIDES}
    observed["replay"][0, 0, "earn_invented"] = 1.0
    result = _compare(_registered_baseline(values), observed)
    assert [item["kind"] for item in result["differences"]] == [
        "extra_observed_cell"
    ]
    observed = {side: dict(values) for side in ("replay", "original", "x")}
    result = _compare(_registered_baseline(values), observed)
    assert [item["kind"] for item in result["differences"]] == [
        "unregistered_side"
    ]


def _condition(status, equal=None, differences=()):
    return {
        "status": status,
        "equal": (status == reconstructed.PASS) if equal is None else equal,
        "differences": list(differences),
    }


@SETTINGS
@given(
    statuses=st.lists(
        st.sampled_from(
            [
                reconstructed.PASS,
                reconstructed.FAIL,
                reconstructed.NOT_EVALUATED,
            ]
        ),
        min_size=4,
        max_size=4,
    )
)
def test_admission_passes_iff_every_condition_passes(statuses):
    conditions = {
        name: _condition(status)
        for name, status in zip(
            reconstructed.CONDITIONS, statuses, strict=True
        )
    }
    verdict = reconstructed.admission(conditions)
    passed = all(status == reconstructed.PASS for status in statuses)
    assert verdict["equal"] is passed
    assert verdict["status"] == (
        reconstructed.RECONSTRUCTED_REPRODUCTION
        if passed
        else "BASELINE_REPLAY_MISMATCH"
    )
    assert verdict["admitted_scope"] == (
        reconstructed.ADMITTED_SCOPE if passed else "none"
    )
    assert verdict["failed_conditions"] == [
        name
        for name, status in zip(
            reconstructed.CONDITIONS, statuses, strict=True
        )
        if status == reconstructed.FAIL
    ]


@pytest.mark.parametrize(
    "record",
    [
        _condition(reconstructed.PASS, equal=1),
        _condition(reconstructed.PASS, equal=False),
        _condition(reconstructed.PASS, differences=[{"kind": "value"}]),
        _condition("PASS"),
        {"equal": True, "differences": []},
    ],
    ids=["equal-1", "equal-false", "differences", "status-case", "no-status"],
)
def test_admission_requires_an_exact_pass_record(record):
    conditions = {
        name: _condition(reconstructed.PASS)
        for name in reconstructed.CONDITIONS
    }
    conditions["fit_lineage"] = record
    verdict = reconstructed.admission(conditions)
    assert verdict["status"] == "BASELINE_REPLAY_MISMATCH"
    assert verdict["failed_conditions"] == ["fit_lineage"]


def test_admission_refuses_missing_and_unregistered_conditions():
    passing = {
        name: _condition(reconstructed.PASS)
        for name in reconstructed.CONDITIONS
    }
    assert reconstructed.admission(passing)["equal"] is True
    missing = dict(passing)
    del missing["provenance"]
    verdict = reconstructed.admission(missing)
    assert verdict["equal"] is False
    assert verdict["not_evaluated_conditions"] == ["provenance"]
    extra = {**passing, "tolerance": _condition(reconstructed.PASS)}
    verdict = reconstructed.admission(extra)
    assert verdict["equal"] is False
    assert verdict["unregistered_conditions"] == ["'tolerance'"]
    assert reconstructed.admission(None)["not_evaluated_conditions"] == list(
        reconstructed.CONDITIONS
    )


@st.composite
def _frames(draw):
    rows = draw(st.integers(min_value=1, max_value=5))
    person = draw(
        st.lists(
            st.integers(min_value=1, max_value=50),
            min_size=rows,
            max_size=rows,
            unique=True,
        )
    )
    earnings = draw(
        st.lists(
            st.floats(allow_nan=False, allow_infinity=False, width=64),
            min_size=rows,
            max_size=rows,
        )
    )
    cohort = draw(
        st.lists(
            st.sampled_from(["prime", "older"]), min_size=rows, max_size=rows
        )
    )
    return pd.DataFrame(
        {
            "person_id": person,
            "period": [2016] * rows,
            "earnings": earnings,
            "weight": [1.5] * rows,
            "cohort": cohort,
        }
    )


@SETTINGS
@given(
    frame=_frames(),
    rng=st.randoms(use_true_random=False),
    change=st.sampled_from(
        ["none", "earnings", "sign", "row", "dtype", "column", "duplicate"]
    ),
)
def test_payload_comparison_agrees_with_compare_frames(frame, rng, change):
    other = frame.copy()
    if change == "earnings":
        other.loc[0, "earnings"] = _nextafter(other.loc[0, "earnings"])
    elif change == "sign":
        other.loc[0, "earnings"] = -other.loc[0, "earnings"]
    elif change == "row":
        other = other.iloc[1:] if len(other) > 1 else other.iloc[:0]
    elif change == "dtype":
        other["weight"] = other["weight"].astype("float32")
    elif change == "column":
        other = other.drop(columns="cohort")
    elif change == "duplicate":
        other = pd.concat([other, other.iloc[:1]], ignore_index=True)
    rows = list(range(len(other)))
    rng.shuffle(rows)
    columns = list(other.columns)
    rng.shuffle(columns)
    other = other.iloc[rows][columns]

    in_memory = compare_frames(frame, other)["equal"]
    published = not reconstructed.compare_frame_payloads(
        runner.frame_payload(frame), runner.frame_payload(other)
    )
    assert published is in_memory
    # Every change, including negating a zero, is material to both.
    assert in_memory is (change == "none")


def test_payload_comparison_fails_closed_on_malformed_payloads():
    frame = pd.DataFrame(
        {"person_id": [1], "period": [2016], "earnings": [1.0]}
    )
    good = runner.frame_payload(frame)
    assert reconstructed.compare_frame_payloads(good, good) == []
    null_key = copy.deepcopy(good)
    null_key["columns"][0]["values"][0] = None
    ragged = copy.deepcopy(good)
    ragged["columns"][2]["values"].append({"float64_hex": "00" * 8})
    empty = {
        "columns": [{**column, "values": []} for column in good["columns"]]
    }
    for broken, kind in (
        (null_key, "null_key"),
        (ragged, "ragged_frame"),
        (empty, "empty_frame"),
        ({"columns": "invented"}, "missing_frame"),
        (None, "missing_frame"),
    ):
        kinds = [
            item["kind"]
            for item in reconstructed.compare_frame_payloads(good, broken)
        ]
        assert kind in kinds


@pytest.mark.parametrize("dropped", ["earnings", "weight"])
def test_evidence_differential_requires_earnings_and_weight(dropped):
    # Identical payloads that both lack a scored column compare equal as
    # frames, but they are not person-level evidence: condition 3 fails
    # and names the missing column on each side.
    frame = pd.DataFrame(
        {
            "person_id": [1, 2],
            "period": [2016, 2016],
            "earnings": [1.0, 2.0],
            "weight": [1.5, 1.5],
        }
    )
    signature = {"invented": "signature"}

    def payloads(scored):
        encoded = runner.frame_payload(scored)
        return {
            (0, 0): {
                "original_scored": encoded,
                "replay_scored": copy.deepcopy(encoded),
                "original_fit_signature": signature,
                "replay_fit_signature": dict(signature),
                "original_rng_signature": signature,
                "replay_rng_signature": dict(signature),
            }
        }

    complete = reconstructed.compare_evidence_differential(
        payloads(frame), seeds=[0], draws=[0]
    )
    assert complete["status"] == reconstructed.PASS
    stripped_frame = frame.drop(columns=dropped)
    assert (
        reconstructed.compare_frame_payloads(
            runner.frame_payload(stripped_frame),
            runner.frame_payload(stripped_frame),
        )
        == []
    )
    stripped = reconstructed.compare_evidence_differential(
        payloads(stripped_frame), seeds=[0], draws=[0]
    )
    assert stripped["status"] == reconstructed.FAIL
    assert stripped["equal"] is False
    assert [
        (item["side"], item["column"])
        for item in stripped["differences"]
        if item["kind"] == "missing_required_column"
    ] == [("expected", dropped), ("actual", dropped)]


def test_v2_publication_fallback_keeps_condition_statuses(tmp_path):
    # An unserializable v2 result publishes a mismatch that admits nothing,
    # keeps each evaluated condition's status, and marks anything missing
    # or malformed as not evaluated rather than failed.
    result = {
        "schema_version": reconstructed.SCHEMA_VERSION,
        "registration_id": "9999999999",
        "baseline_version": runner.RECONSTRUCTED,
        "status": reconstructed.RECONSTRUCTED_REPRODUCTION,
        "equal": True,
        "admitted_scope": reconstructed.ADMITTED_SCOPE,
        "condition_status": {
            "per_draw_cells": reconstructed.PASS,
            "fit_lineage": reconstructed.FAIL,
            "person_level_differential": "invented",
        },
        "diagnostic": object(),
    }
    published = runner._publish(tmp_path, result)

    assert json.loads((tmp_path / "result.json").read_text()) == published
    assert published["status"] == "BASELINE_REPLAY_MISMATCH"
    assert published["equal"] is False
    assert published["admitted_scope"] == "none"
    assert published["baseline_version"] == runner.RECONSTRUCTED
    assert published["condition_status"] == {
        "per_draw_cells": reconstructed.PASS,
        "fit_lineage": reconstructed.FAIL,
        "person_level_differential": reconstructed.NOT_EVALUATED,
        "provenance": reconstructed.NOT_EVALUATED,
    }
    assert published["failed_conditions"] == ["fit_lineage"]
    assert published["not_evaluated_conditions"] == [
        "person_level_differential",
        "provenance",
    ]
    assert published["unserializable_result_fields"] == ["diagnostic"]


# ---------------------------------------------------------------------------
# The four conditions end to end on invented loops
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def invented():
    supplied = _invented_differential_inputs()
    lineage = {**supplied["baseline"]["lineage"], **LINEAGE_EXTRA}
    baseline = runner._json_canonical(
        {
            "protocol": {
                "gate_seeds": list(supplied["seeds"]),
                "draw_index": list(supplied["draws"]),
                "draw_seeds": list(range(5200, 5220)),
            },
            "family_a": supplied["baseline"]["family_a"],
            "lineage": lineage,
            "provenance": PROVENANCE,
            "runtime_identity": RUNTIME_IDENTITY,
        }
    )
    return SimpleNamespace(
        supplied=supplied,
        populations=supplied["populations"],
        generator=supplied["generator"],
        baseline=baseline,
        sidecar={"environment": {"candidate3_gate_freeze": FREEZE}},
        seeds=tuple(supplied["seeds"]),
        draws=tuple(supplied["draws"]),
    )


def _actuals(invented) -> dict:
    return dict(
        actual_lineage=copy.deepcopy(invented.baseline["lineage"]),
        actual_provenance={
            "provenance": copy.deepcopy(invented.baseline["provenance"]),
            "runtime_identity": copy.deepcopy(
                invented.baseline["runtime_identity"]
            ),
            "candidate3_gate_freeze": copy.deepcopy(FREEZE),
        },
        anchor=copy.deepcopy(ANCHOR),
    )


def _run(invented, output: Path, **overrides) -> dict:
    arguments = dict(
        populations=invented.populations,
        generator=invented.generator,
        baseline=copy.deepcopy(invented.baseline),
        sidecar=copy.deepcopy(invented.sidecar),
        output=output,
        seeds=invented.seeds,
        draws=invented.draws,
        **_actuals(invented),
    )
    arguments.update(overrides)
    output.mkdir(parents=True, exist_ok=True)
    return reconstructed.run_reconstructed(**arguments)


@pytest.fixture(scope="module")
def passing_run(invented, tmp_path_factory):
    output = tmp_path_factory.mktemp("v2_passing")
    result = _run(invented, output)
    files = {
        entry["path"]: (output / entry["path"]).read_bytes()
        for entry in result["files"]
    }
    return SimpleNamespace(result=result, files=files, output=output)


def test_all_four_conditions_passing_yields_reconstructed_reproduction(
    invented, passing_run, tmp_path
):
    result = passing_run.result
    assert result["status"] == reconstructed.RECONSTRUCTED_REPRODUCTION
    assert result["equal"] is True
    assert result["admitted_scope"] == (
        "reconstructed reproduction (weaker than bit-for-bit)"
    )
    assert result["failed_conditions"] == []
    assert result["not_evaluated_conditions"] == []
    assert result["condition_status"] == {
        name: reconstructed.PASS for name in reconstructed.CONDITIONS
    }
    assert result["historical_person_level_reference_used"] is False
    assert result["conditions"]["per_draw_cells"]["compared_cells"] == (
        len(invented.seeds) * len(invented.draws) * len(EARNINGS_CELL_NAMES)
    )
    # I5: no v2 record carries the bit-for-bit status.
    assert "REPRODUCED" not in json.dumps(result)
    for entry in result["files"]:
        payload = json.loads(passing_run.files[entry["path"]])
        assert runner.sha256(passing_run.files[entry["path"]]) == (
            entry["sha256"]
        )
        assert set(payload["replay_cells"]) == set(EARNINGS_CELL_NAMES)
        assert payload["replay_cells"] == payload["original_cells"]

    # I7: a second run is byte-identical.
    again = _run(invented, tmp_path / "again")
    assert again == result
    for name, payload in passing_run.files.items():
        assert (tmp_path / "again" / name).read_bytes() == payload


def test_v2_evidence_is_the_v1_evidence_plus_both_sides_cells(
    invented, passing_run, tmp_path
):
    v1 = runner.run_differential(**invented.supplied, output=tmp_path)
    for entry in v1["files"]:
        v2_payload = json.loads(passing_run.files[entry["path"]])
        del v2_payload["replay_cells"], v2_payload["original_cells"]
        assert runner.json_bytes(v2_payload) == (
            (tmp_path / entry["path"]).read_bytes()
        )


def test_mutated_committed_cell_fails_only_condition_1(invented, tmp_path):
    baseline = copy.deepcopy(invented.baseline)
    cell = EARNINGS_CELL_NAMES[2]
    rates = baseline["family_a"]["per_seed"][1]["gated_cells"][cell][
        "per_draw_rate"
    ]
    rates[1] = _nextafter(rates[1])
    result = _run(invented, tmp_path, baseline=baseline)

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert result["failed_conditions"] == ["per_draw_cells"]
    differences = result["conditions"]["per_draw_cells"]["differences"]
    assert {
        (item["side"], item["seed"], item["draw"]) for item in differences
    } == {
        ("replay", 1, 1),
        ("original", 1, 1),
    }
    assert {item["cell"] for item in differences} == {cell}


def test_mutated_lineage_field_fails_only_condition_2(invented, tmp_path):
    baseline = copy.deepcopy(invented.baseline)
    baseline["lineage"]["floor_sha256"] = "0" * 64
    result = _run(invented, tmp_path, baseline=baseline)

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["failed_conditions"] == ["fit_lineage"]
    differences = result["conditions"]["fit_lineage"]["differences"]
    assert [item["path"] for item in differences] == [
        ["lineage", "floor_sha256"]
    ]


def test_fit_signature_lineage_field_also_fails_the_differential(
    invented, tmp_path
):
    # Intended overlap: the existing differential compares the committed
    # FIT_SIGNATURE_KEYS with the refit's, so condition 3 fails as well.
    lineage = copy.deepcopy(invented.baseline["lineage"])
    lineage["q_invariant_fit_signature_sha256"] = "d" * 64
    result = _run(invented, tmp_path, actual_lineage=lineage)

    assert result["failed_conditions"] == [
        "fit_lineage",
        "person_level_differential",
    ]
    paths = {
        tuple(item["path"])
        for item in result["conditions"]["person_level_differential"][
            "differences"
        ]
    }
    assert paths == {("fit_signature", "q_invariant_fit_signature_sha256")}


def _perturb_replay(monkeypatch, column, change):
    """Change one person-period value in the copy's first draw-1 output."""
    real = runner.replay_earnings_on_realized_support
    state = {"done": False}

    def perturbed(**arguments):
        replay = real(**arguments)
        if arguments["draw_index"] != 1 or state["done"]:
            return replay
        state["done"] = True
        scored = replay.scored.copy()
        row = scored.index[
            (scored["person_id"] == 3) & (scored["period"] == 2016)
        ][0]
        scored.loc[row, column] = change(scored.loc[row, column])
        return dataclasses.replace(replay, scored=scored)

    monkeypatch.setattr(
        runner, "replay_earnings_on_realized_support", perturbed
    )


def test_mutated_person_period_value_fails_only_condition_3(
    invented, tmp_path, monkeypatch
):
    _perturb_replay(monkeypatch, "age", lambda value: value + 1)
    result = _run(invented, tmp_path)

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["failed_conditions"] == ["person_level_differential"]
    differences = result["conditions"]["person_level_differential"][
        "differences"
    ]
    assert len(differences) == 1
    assert differences[0]["seed"] == 0
    assert differences[0]["draw"] == 1
    assert differences[0]["column"] == "age"
    assert differences[0]["kind"] == "value"


def test_one_ulp_person_earnings_change_fails_condition_3(
    invented, tmp_path, monkeypatch
):
    _perturb_replay(monkeypatch, "earnings", _nextafter)
    result = _run(invented, tmp_path)

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert "person_level_differential" in result["failed_conditions"]
    assert set(result["failed_conditions"]) <= {
        "per_draw_cells",
        "person_level_differential",
    }
    differences = result["conditions"]["person_level_differential"][
        "differences"
    ]
    assert [item["column"] for item in differences] == ["earnings"]


def test_mutated_provenance_field_fails_only_condition_4(invented, tmp_path):
    actuals = _actuals(invented)
    # The value a B1 checkout's own .venv would record (review, High).
    actuals["actual_provenance"]["provenance"]["external_details"][
        "ssa_revision"
    ] = "7f55d4c"
    result = _run(invented, tmp_path, **actuals)

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["failed_conditions"] == ["provenance"]
    differences = result["conditions"]["provenance"]["differences"]
    assert [item["path"] for item in differences] == [
        ["provenance", "external_details", "ssa_revision"]
    ]


def test_anchor_reporting_another_abbreviation_fails_only_condition_4(
    invented, tmp_path
):
    actuals = _actuals(invented)
    # What the unchanged loader reports once git abbreviates to eight.
    actuals["anchor"]["loader_revision"] = "f10cca54"
    result = _run(invented, tmp_path, **actuals)

    assert result["failed_conditions"] == ["provenance"]
    differences = result["conditions"]["provenance"]["differences"]
    assert [item["path"] for item in differences] == [
        ["ssa_revision_anchor", "loader_revision"]
    ]


def _passing_provenance_inputs():
    # registered_provenance returns the records it is given, so copy them:
    # a test that relabels the registered side must not rewrite the
    # module-level fixtures for every later test.
    registered = copy.deepcopy(
        reconstructed.registered_provenance(
            {"provenance": PROVENANCE, "runtime_identity": RUNTIME_IDENTITY},
            {"environment": {"candidate3_gate_freeze": FREEZE}},
        )
    )
    actual = copy.deepcopy(registered)
    return registered, actual, copy.deepcopy(ANCHOR)


@pytest.mark.parametrize(
    "mutate, path",
    [
        (
            lambda r, a, n: a["runtime_identity"].update(numpy="2.5.3"),
            ["runtime_identity", "numpy"],
        ),
        (
            lambda r, a, n: a["candidate3_gate_freeze"].update(
                omp_wait_policy="PASSIVE"
            ),
            ["candidate3_gate_freeze", "omp_wait_policy"],
        ),
        (
            lambda r, a, n: a["provenance"]["source_rows"].update(earnings=41),
            ["provenance", "source_rows", "earnings"],
        ),
        (
            lambda r, a, n: a["provenance"].update(boundary_year=2014.0),
            ["provenance", "boundary_year"],
        ),
        (
            lambda r, a, n: n.update(head="f10cca5" + "0" * 33),
            ["ssa_revision_anchor", "head"],
        ),
        (
            lambda r, a, n: n.update(tracked_clean=False),
            ["ssa_revision_anchor", "tracked_clean"],
        ),
        (
            lambda r, a, n: n.update(tracked_clean=1),
            ["ssa_revision_anchor", "tracked_clean"],
        ),
        (
            lambda r, a, n: n.update(
                git_environment={"GIT_DIR": "/elsewhere"}
            ),
            ["ssa_revision_anchor", "git_environment"],
        ),
        (
            lambda r, a, n: n.update(loader_revision="unknown"),
            ["ssa_revision_anchor", "loader_revision"],
        ),
    ],
)
def test_every_provenance_record_and_anchor_field_is_material(mutate, path):
    registered, actual, anchor = _passing_provenance_inputs()
    assert reconstructed.compare_provenance(registered, actual, anchor)[
        "equal"
    ]
    mutate(registered, actual, anchor)
    result = reconstructed.compare_provenance(registered, actual, anchor)
    assert result["equal"] is False
    assert [item["path"] for item in result["differences"]] == [path]


def test_a_consistent_relabel_of_ssa_revision_cannot_pass():
    # Rule (a) is not a mapping: an artifact and replay that agree on some
    # other abbreviation still fail, because the anchor must be f10cca5.
    registered, actual, anchor = _passing_provenance_inputs()
    for record in (registered, actual):
        record["provenance"]["external_details"]["ssa_revision"] = "7f55d4c"
    anchor["loader_revision"] = "7f55d4c"
    result = reconstructed.compare_provenance(registered, actual, anchor)
    kinds = [item["kind"] for item in result["differences"]]
    assert result["equal"] is False
    assert kinds == ["registered_ssa_revision", "ssa_revision_anchor"]


def test_missing_provenance_records_fail_closed():
    registered, actual, anchor = _passing_provenance_inputs()
    del actual["runtime_identity"]
    actual["invented_extra"] = {"x": 1}
    kinds = [
        item["kind"]
        for item in reconstructed.compare_provenance(
            registered, actual, anchor
        )["differences"]
    ]
    assert kinds == ["missing_replay_record", "unregistered_record"]
    assert (
        reconstructed.compare_provenance(registered, None, None)["equal"]
        is False
    )


# ---------------------------------------------------------------------------
# The ssa_revision probe on invented git repositories
# ---------------------------------------------------------------------------
def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Invented",
            "-c",
            "user.email=invented@example.invalid",
            *arguments,
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def anchor_repository(tmp_path, monkeypatch):
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    root = tmp_path / "anchor"
    root.mkdir()
    _git(root, "init", "--quiet")
    (root / "tracked.txt").write_text("invented\n")
    (root / ".gitignore").write_text(".venv/\n")
    _git(root, "add", "tracked.txt", ".gitignore")
    _git(root, "commit", "--quiet", "-m", "invented")
    site = root / ".venv" / "lib" / "site-packages"
    site.mkdir(parents=True)
    return SimpleNamespace(
        root=root, site=site, head=_git(root, "rev-parse", "HEAD")
    )


def test_probe_reports_what_git_log_reports_from_the_install(
    anchor_repository,
):
    record = reconstructed.ssa_revision_anchor(anchor_repository.site)
    assert record["loader_revision"] == _git(
        anchor_repository.site, "log", "-1", "--format=%h"
    )
    assert record["head"] == anchor_repository.head
    assert record["tracked_clean"] is True
    assert record["git_environment"] == {}
    assert (
        Path(record["toplevel"]).resolve() == anchor_repository.root.resolve()
    )
    assert record["command"] == ["git", "log", "-1", "--format=%h"]


def test_probe_follows_the_abbreviation_setting(anchor_repository):
    _git(anchor_repository.root, "config", "core.abbrev", "12")
    record = reconstructed.ssa_revision_anchor(anchor_repository.site)
    assert record["loader_revision"] == anchor_repository.head[:12]
    assert record["core_abbrev"] == "12"


def test_probe_flags_dirty_tracked_files_and_git_redirection(
    anchor_repository, monkeypatch
):
    (anchor_repository.root / "tracked.txt").write_text("edited\n")
    assert (
        reconstructed.ssa_revision_anchor(anchor_repository.site)[
            "tracked_clean"
        ]
        is False
    )
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", "/invented")
    record = reconstructed.ssa_revision_anchor(anchor_repository.site)
    assert record["git_environment"] == {
        "GIT_CEILING_DIRECTORIES": "/invented"
    }


def test_probe_outside_any_repository_reports_the_loader_fallback(
    tmp_path, monkeypatch
):
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.resolve()))
    outside = tmp_path / "no-repository"
    outside.mkdir()
    record = reconstructed.ssa_revision_anchor(outside)
    assert record["loader_revision"] == "unknown"
    assert record["head"] is None
    missing = reconstructed.ssa_revision_anchor(tmp_path / "absent")
    assert missing["loader_revision"] == "unknown"


def test_loader_and_probe_run_the_same_command():
    import inspect

    from populace_dynamics.ss import params

    source = inspect.getsource(params.load_ssa_parameters)
    assert '["git", "log", "-1", "--format=%h"]' in source
    assert "cwd=root" in source
    assert "root = _resolve_pe_us(pe_us_dir)" in source
    assert tuple(reconstructed.LOADER_REVISION_COMMAND) == (
        "git",
        "log",
        "-1",
        "--format=%h",
    )


# ---------------------------------------------------------------------------
# execute: version selection and the extended no-reference guard
# ---------------------------------------------------------------------------
@pytest.fixture
def repository(tmp_path, monkeypatch, invented):
    subprocess.run(
        ["git", "init", "--quiet", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    baseline_path = tmp_path / runner.BASELINE_PATH
    baseline_path.parent.mkdir()
    baseline_path.write_bytes(runner.json_bytes(invented.baseline))
    (tmp_path / runner.SIDECAR_PATH).write_bytes(
        runner.json_bytes(invented.sidecar)
    )
    monkeypatch.setattr(runner, "REGISTERED_SEEDS", invented.seeds)
    monkeypatch.setattr(runner, "REGISTERED_DRAWS", invented.draws)
    calls = []

    def guard(*arguments, **keywords):
        calls.append(keywords)
        return {"commit": "b" * 40}

    monkeypatch.setattr(runner, "source_guard", guard)
    probes = []

    def probe(*arguments, **keywords):
        probes.append(arguments)
        return copy.deepcopy(ANCHOR)

    monkeypatch.setattr(reconstructed, "ssa_revision_anchor", probe)
    return SimpleNamespace(root=tmp_path, guard_calls=calls, probes=probes)


def _execute(repository, operation, **keywords):
    return runner.execute(
        root=repository.root,
        registration_id="9999999999",
        expected_commit="b" * 40,
        operation=operation,
        **{"baseline_version": "reconstructed", **keywords},
    )


def _published(repository, location=reconstructed.DEFAULT_OUTPUT):
    return json.loads((repository.root / location / "result.json").read_text())


def _replayed(passing_run, mutate=None):
    """An operation that republishes the genuine passing run's evidence."""

    def operation(root, output, baseline):
        result = copy.deepcopy(passing_run.result)
        for name, payload in passing_run.files.items():
            (output / name).write_bytes(payload)
        if mutate is not None:
            mutate(result, output)
        return result

    return operation


def _rewrite(result, output, name, change, *, rehash=True):
    path = output / name
    payload = json.loads(path.read_bytes())
    change(payload)
    path.write_bytes(runner.json_bytes(payload))
    if rehash:
        for entry in result["files"]:
            if entry["path"] == name:
                entry["sha256"] = runner.sha256(path.read_bytes())


def test_execute_admits_a_rederived_reconstructed_reproduction(
    repository, passing_run
):
    result = _execute(repository, _replayed(passing_run))

    assert result["status"] == reconstructed.RECONSTRUCTED_REPRODUCTION
    assert result["equal"] is True
    assert result["admitted_scope"] == reconstructed.ADMITTED_SCOPE
    assert result["schema_version"] == "track_b_b1.v2"
    assert result["baseline_version"] == "reconstructed"
    assert result["verification_class"] == "reproduction"
    assert "abort" not in result
    assert _published(repository) == result
    assert not (repository.root / runner.DEFAULT_OUTPUT).exists()
    # Both source checks bind v2's extra sources; the guard probed again.
    assert (
        repository.guard_calls
        == [{"extra_sources": reconstructed.RECONSTRUCTED_SOURCES}] * 2
    )
    assert len(repository.probes) == 1


def _tamper_cell(result, output):
    name = result["files"][-1]["path"]
    cell = EARNINGS_CELL_NAMES[0]

    def change(payload):
        value = reconstructed._decode_cell(payload["replay_cells"][cell])
        payload["replay_cells"][cell] = runner._scalar(_nextafter(value))

    _rewrite(result, output, name, change)


def _tamper_row(result, output):
    name = result["files"][0]["path"]

    def change(payload):
        column = next(
            column
            for column in payload["replay_scored"]["columns"]
            if column["name"] == "age"
        )
        column["values"][0] += 1

    _rewrite(result, output, name, change)


def _tamper_both_frames(result, output):
    # The same change on both sides keeps the frames equal, so only a
    # recomputation of the cells from the frames can see it.
    name = result["files"][-1]["path"]

    def change(payload):
        for side in ("original_scored", "replay_scored"):
            column = next(
                column
                for column in payload[side]["columns"]
                if column["name"] == "earnings"
            )
            index = next(
                index
                for index, value in enumerate(column["values"])
                if reconstructed._decode_cell(value)
            )
            value = reconstructed._decode_cell(column["values"][index])
            column["values"][index] = runner._scalar(value * 1.5)

    _rewrite(result, output, name, change)


def _drop_cell_input_both_frames(result, output):
    name = result["files"][0]["path"]

    def change(payload):
        for side in ("original_scored", "replay_scored"):
            payload[side]["columns"] = [
                column
                for column in payload[side]["columns"]
                if column["name"] != "cohort"
            ]

    _rewrite(result, output, name, change)


def _stale_hash(result, output):
    name = result["files"][0]["path"]
    _rewrite(result, output, name, lambda payload: None, rehash=False)
    (output / name).write_bytes((output / name).read_bytes() + b" ")


def _missing_lineage(result, output):
    del result["conditions"]["fit_lineage"]["actual"]


def _moved_anchor(result, output):
    result["conditions"]["provenance"]["ssa_revision_anchor"] = {
        **ANCHOR,
        "core_abbrev": "8",
    }


@pytest.mark.parametrize(
    "mutate, failed",
    [
        (_tamper_cell, ["per_draw_cells"]),
        (_tamper_both_frames, ["per_draw_cells"]),
        (_drop_cell_input_both_frames, ["per_draw_cells"]),
        (_tamper_row, ["person_level_differential"]),
        (_stale_hash, ["per_draw_cells", "person_level_differential"]),
        (_missing_lineage, ["fit_lineage"]),
        (_moved_anchor, ["provenance"]),
    ],
    ids=[
        "cell",
        "both-frames",
        "cell-input-column",
        "row",
        "stale-hash",
        "lineage",
        "anchor",
    ],
)
def test_guard_rederives_each_condition_from_published_evidence(
    repository, passing_run, mutate, failed
):
    """The operation still reports every condition as passing."""
    result = _execute(repository, _replayed(passing_run, mutate))

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert "re-derived from the published evidence" in (
        result["abort"]["message"]
    )
    assert result["failed_conditions"] == failed
    assert [
        name
        for name, status in result["guard"]["condition_status"].items()
        if status == reconstructed.FAIL
    ] == failed
    assert _published(repository) == result


@pytest.mark.parametrize(
    "claim",
    [
        {"status": "REPRODUCED", "equal": True},
        {"status": "REPRODUCED", "equal": True, "admitted_scope": "x"},
        {
            "status": reconstructed.RECONSTRUCTED_REPRODUCTION,
            "equal": 1,
            "admitted_scope": reconstructed.ADMITTED_SCOPE,
        },
        {
            "status": reconstructed.RECONSTRUCTED_REPRODUCTION,
            "equal": True,
            "admitted_scope": "reconstructed reproduction",
        },
        {"status": "MATCH", "equal": False, "admitted_scope": "none"},
        {"status": "BASELINE_REPLAY_MISMATCH", "equal": True},
        {
            "status": "BASELINE_REPLAY_MISMATCH",
            "equal": False,
            "admitted_scope": reconstructed.ADMITTED_SCOPE,
        },
        {"schema_version": "track_b_b1.v1"},
        {"historical_person_level_reference_used": True},
    ],
)
def test_guard_refuses_every_other_claim(repository, passing_run, claim):
    def mutate(result, output):
        result.update(claim)

    result = _execute(repository, _replayed(passing_run, mutate))

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert "abort" in result
    assert _published(repository) == result


def test_guard_refuses_a_claim_without_evidence(repository):
    passing = {
        name: {"status": reconstructed.PASS, "equal": True, "differences": []}
        for name in reconstructed.CONDITIONS
    }

    def operation(root, output, baseline):
        return {
            "status": reconstructed.RECONSTRUCTED_REPRODUCTION,
            "equal": True,
            "admitted_scope": reconstructed.ADMITTED_SCOPE,
            "conditions": passing,
            "files": [],
        }

    result = _execute(repository, operation)
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["failed_conditions"] == list(reconstructed.CONDITIONS)


def test_guard_refuses_a_claim_whose_reported_conditions_fail(
    repository, passing_run
):
    def mutate(result, output):
        result["conditions"]["provenance"]["status"] = reconstructed.FAIL

    result = _execute(repository, _replayed(passing_run, mutate))
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert "reported conditions do not all pass" in result["abort"]["message"]
    assert result["failed_conditions"] == ["provenance"]
    assert "guard" not in result


def test_guard_probes_the_anchor_again_after_the_run(
    repository, passing_run, monkeypatch
):
    monkeypatch.setattr(
        reconstructed,
        "ssa_revision_anchor",
        lambda *arguments: {**ANCHOR, "loader_revision": "f10cca54"},
    )
    result = _execute(repository, _replayed(passing_run))
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["failed_conditions"] == ["provenance"]


def test_a_reported_mismatch_is_published_as_the_run_reported_it(
    repository, passing_run
):
    def operation(root, output, baseline):
        failing = copy.deepcopy(passing_run.result)
        failing["conditions"]["fit_lineage"].update(
            status=reconstructed.FAIL, equal=False
        )
        return {
            **failing,
            **reconstructed.admission(failing["conditions"]),
        }

    result = _execute(repository, operation)
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["failed_conditions"] == ["fit_lineage"]
    assert "abort" not in result


def test_v1_refuses_a_genuine_reconstructed_reproduction(
    repository, passing_run
):
    result = _execute(
        repository, _replayed(passing_run), baseline_version="bit-for-bit"
    )
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert "REPRODUCED requires" in result["abort"]["message"]
    assert result["schema_version"] == runner.SCHEMA_VERSION
    assert _published(repository, runner.DEFAULT_OUTPUT) == result
    assert repository.guard_calls == [{}, {}]


@pytest.mark.parametrize(
    "claim, allowed",
    [
        (
            {
                "status": "REPRODUCED",
                "equal": True,
                "admitted_scope": runner.BIT_FOR_BIT_SCOPE,
            },
            True,
        ),
        (
            {
                "status": "BASELINE_REPLAY_MISMATCH",
                "equal": False,
                "admitted_scope": "none",
            },
            True,
        ),
        (
            {
                "status": reconstructed.RECONSTRUCTED_REPRODUCTION,
                "equal": True,
                "admitted_scope": reconstructed.ADMITTED_SCOPE,
            },
            False,
        ),
        (
            {
                "status": "REPRODUCED",
                "equal": 1,
                "admitted_scope": runner.BIT_FOR_BIT_SCOPE,
            },
            False,
        ),
        (
            {
                "status": "REPRODUCED",
                "equal": True,
                "admitted_scope": reconstructed.ADMITTED_SCOPE,
            },
            False,
        ),
    ],
)
def test_v1_with_an_admitted_reference_may_claim_only_reproduced(
    claim, allowed
):
    reference = runner.HistoricalReference(b"invented")
    if allowed:
        runner._guard_bit_for_bit_claim(claim, reference)
    else:
        with pytest.raises(ValueError, match="only REPRODUCED"):
            runner._guard_bit_for_bit_claim(claim, reference)


def test_v2_refuses_a_historical_reference_before_any_output(
    repository, tmp_path
):
    with pytest.raises(ValueError, match="no historical"):
        _execute(
            repository,
            lambda *arguments: pytest.fail("data operation invoked"),
            historical_reference=tmp_path / "invented.json",
        )
    assert not (repository.root / "scratch").exists()


def test_unregistered_baseline_version_is_refused_before_any_output(
    repository,
):
    with pytest.raises(ValueError, match="unregistered B1 baseline version"):
        _execute(
            repository,
            lambda *arguments: pytest.fail("data operation invoked"),
            baseline_version="bit_for_bit",
        )
    assert not (repository.root / "scratch").exists()


@pytest.mark.parametrize(
    "output", [runner.DEFAULT_OUTPUT, "scratch/track_b/b1_v3"]
)
def test_v2_writes_only_to_its_own_directory(repository, output):
    with pytest.raises(ValueError, match="B1 output must be"):
        _execute(
            repository,
            lambda *arguments: pytest.fail("data operation invoked"),
            output=output,
        )
    assert not (repository.root / "scratch").exists()


def test_v2_abort_before_evaluation_names_no_failed_condition(
    repository, monkeypatch
):
    def failure(*arguments, **keywords):
        raise ValueError("invented source mismatch")

    monkeypatch.setattr(runner, "source_guard", failure)
    result = _execute(
        repository, lambda *arguments: pytest.fail("data operation invoked")
    )
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["baseline_version"] == "reconstructed"
    assert result["failed_conditions"] == []
    assert result["not_evaluated_conditions"] == list(reconstructed.CONDITIONS)
    assert result["abort"]["message"] == "invented source mismatch"


def test_production_anchor_failure_reads_no_data(
    repository, invented, monkeypatch, tmp_path
):
    """Rule (a) is checked before the input factory is even imported."""
    monkeypatch.setattr(
        m6_candidate3_runner,
        "_frozen_gate_environment",
        lambda: copy.deepcopy(FREEZE),
    )
    monkeypatch.setattr(
        reconstructed,
        "ssa_revision_anchor",
        lambda *arguments: {**ANCHOR, "loader_revision": "7f55d4c"},
    )
    trap = types.ModuleType("registered_m6_candidate3_inputs")

    def build_input_plan():
        pytest.fail("the input factory ran after an anchor failure")

    trap.build_input_plan = build_input_plan
    monkeypatch.setitem(sys.modules, "registered_m6_candidate3_inputs", trap)
    output = tmp_path / "evidence"
    output.mkdir()

    result = reconstructed.production_reconstructed(
        repository.root, output, copy.deepcopy(invented.baseline)
    )
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["failed_conditions"] == ["provenance"]
    assert result["not_evaluated_conditions"] == [
        "per_draw_cells",
        "fit_lineage",
        "person_level_differential",
    ]
    assert result["files"] == []
    assert list(output.iterdir()) == []
    assert result["frozen_candidate3_environment"] == FREEZE


# ---------------------------------------------------------------------------
# v1 is unchanged
# ---------------------------------------------------------------------------
V1_RESULT_KEYS = {
    "status",
    "equal",
    "verification_class",
    "admitted_scope",
    "baseline_kind",
    "historical_person_level_reference_available",
    "differences",
    "differential",
    "registered_per_draw_cells",
    "files",
}
V1_EVIDENCE_KEYS = {
    "seed",
    "draw",
    "annual_history",
    "original_scored",
    "replay_scored",
    "original_fit_signature",
    "replay_fit_signature",
    "original_rng_signature",
    "replay_rng_signature",
}


def test_v1_differential_reports_exactly_what_it_did(invented, tmp_path):
    result = runner.run_differential(**invented.supplied, output=tmp_path)
    assert set(result) == V1_RESULT_KEYS
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["baseline_kind"] == "reconstructed_original_scored_path"
    assert result["differential"]["status"] == "MATCH"
    for entry in result["files"]:
        assert set(json.loads((tmp_path / entry["path"]).read_bytes())) == (
            V1_EVIDENCE_KEYS
        )


def test_v1_default_execute_keeps_its_schema_output_and_fields(
    repository,
):
    def operation(root, output, baseline):
        return {
            "status": "BASELINE_REPLAY_MISMATCH",
            "equal": False,
            "admitted_scope": "none",
        }

    result = runner.execute(
        root=repository.root,
        registration_id="9999999999",
        expected_commit="b" * 40,
        operation=operation,
    )
    assert set(result) == {
        "schema_version",
        "registration_id",
        "verification_class",
        "admitted_scope",
        "disclosure",
        "publishes_regardless",
        "source",
        "status",
        "equal",
    }
    assert result["schema_version"] == "track_b_b1.v1"
    assert _published(repository, runner.DEFAULT_OUTPUT) == result
    assert repository.guard_calls == [{}, {}]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cli():
    script = Path(__file__).resolve().parents[1] / "scripts/run_track_b_b1.py"
    spec = importlib.util.spec_from_file_location("run_track_b_b1", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "arguments, version, output, status, code",
    [
        ([], "bit-for-bit", runner.DEFAULT_OUTPUT, "REPRODUCED", 0),
        (
            [],
            "bit-for-bit",
            runner.DEFAULT_OUTPUT,
            reconstructed.RECONSTRUCTED_REPRODUCTION,
            2,
        ),
        (
            ["--baseline-version", "reconstructed"],
            "reconstructed",
            reconstructed.DEFAULT_OUTPUT,
            reconstructed.RECONSTRUCTED_REPRODUCTION,
            0,
        ),
        (
            ["--baseline-version", "reconstructed"],
            "reconstructed",
            reconstructed.DEFAULT_OUTPUT,
            "REPRODUCED",
            2,
        ),
    ],
)
def test_cli_selects_the_registered_version_explicitly(
    monkeypatch, capsys, arguments, version, output, status, code
):
    module = _cli()
    calls = []

    def execute(**keywords):
        calls.append(keywords)
        return {"status": status}

    monkeypatch.setattr(module, "execute", execute)
    required = [
        "--registration-id",
        "9999999999",
        "--expected-commit",
        "b" * 40,
    ]
    assert module.main([*required, *arguments]) == code
    assert calls[0]["baseline_version"] == version
    assert calls[0]["output"] == output
    printed = capsys.readouterr().out
    assert status in printed
    if version == "reconstructed":
        assert "weaker than bit-for-bit" in printed


def test_cli_refuses_an_unregistered_version(monkeypatch, capsys):
    module = _cli()
    monkeypatch.setattr(
        module, "execute", lambda **keywords: pytest.fail("executed")
    )
    with pytest.raises(SystemExit) as exit_info:
        module.main(
            [
                "--registration-id",
                "9999999999",
                "--expected-commit",
                "b" * 40,
                "--baseline-version",
                "tolerant",
            ]
        )
    assert exit_info.value.code == 2
    assert "--baseline-version" in capsys.readouterr().err
