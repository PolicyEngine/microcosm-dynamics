"""Tests for the synthetic roster assignment layer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.firms import assignment


def _frame(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "sponsor_ein": "123456789",
        "naics_sector": "31",
        "canonical_band": "B50_99",
        "active_participants": 60,
        "weight": 1.0,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def _workers(n: int, sector: str = "31", band: str = "B50_99"):
    return pd.DataFrame(
        {
            "person_id": np.arange(n),
            "naics_sector": [sector] * n,
            "canonical_band": [band] * n,
        }
    )


def test_expansion_requires_the_calibrated_columns():
    with pytest.raises(ValueError, match="weight"):
        assignment.expand_to_firm_instances(
            _frame([{}]).drop(columns=["weight"]), seed=1
        )


def test_expansion_rejects_negative_weights():
    with pytest.raises(ValueError, match="Negative weights"):
        assignment.expand_to_firm_instances(_frame([{"weight": -1}]), seed=1)


def test_integer_weight_expands_exactly():
    out = assignment.expand_to_firm_instances(_frame([{"weight": 3}]), seed=1)
    assert len(out) == 3
    assert set(out["firm_instance_id"]) == {0, 1, 2}
    assert (out["capacity"] == 60).all()


def test_fractional_weight_is_bernoulli_not_rounded():
    """Rounding would bias the firm margin down.

    Most calibrated weights sit between 1 and 4, so rounding 1.5 to 1
    (or 2) systematically loses (or invents) firms. A seeded Bernoulli
    draw makes the expected count equal the weight instead.
    """
    counts = [
        len(
            assignment.expand_to_firm_instances(
                _frame([{"weight": 1.5}]), seed=seed
            )
        )
        for seed in range(400)
    ]
    assert set(counts) == {1, 2}
    assert 1.4 < float(np.mean(counts)) < 1.6


def test_expansion_is_reproducible_under_a_pinned_seed():
    kwargs = {"seed": 20260812}
    frame = _frame([{"weight": 2.7}, {"weight": 5.2, "naics_sector": "44"}])
    first = assignment.expand_to_firm_instances(frame, **kwargs)
    second = assignment.expand_to_firm_instances(frame, **kwargs)
    assert first["capacity"].tolist() == second["capacity"].tolist()
    assert len(first) == len(second)


def test_expansion_seed_is_required():
    with pytest.raises(TypeError):
        assignment.expand_to_firm_instances(_frame([{}]))


def test_assignment_respects_capacity():
    instances = assignment.expand_to_firm_instances(
        _frame([{"weight": 1, "active_participants": 5}]), seed=1
    )
    out = assignment.assign_workers(_workers(12), instances, seed=1)
    assert out.attrs["assigned_workers"] == 5
    assert out["firm_instance_id"].notna().sum() == 5
    reasons = [u["reason"] for u in out.attrs["unassigned"]]
    assert reasons == ["cell capacity exhausted"]


def test_worker_in_a_cell_with_no_firm_is_left_unassigned():
    """Never relocate across cells — that would fabricate mobility."""
    instances = assignment.expand_to_firm_instances(
        _frame([{"weight": 1, "naics_sector": "31"}]), seed=1
    )
    out = assignment.assign_workers(
        _workers(4, sector="52"), instances, seed=1
    )
    assert out["firm_instance_id"].isna().all()
    assert out.attrs["unassigned"][0]["reason"] == "no firm instance in cell"


def test_assignment_is_reproducible_and_seed_sensitive():
    instances = assignment.expand_to_firm_instances(
        _frame([{"weight": 20, "active_participants": 5}]), seed=1
    )
    workers = _workers(40)
    a = assignment.assign_workers(workers, instances, seed=7)
    b = assignment.assign_workers(workers, instances, seed=7)
    c = assignment.assign_workers(workers, instances, seed=8)
    assert a["firm_instance_id"].equals(b["firm_instance_id"])
    assert not a["firm_instance_id"].equals(c["firm_instance_id"])


def test_no_firm_instance_exceeds_its_capacity():
    instances = assignment.expand_to_firm_instances(
        _frame([{"weight": 4, "active_participants": 3}]), seed=2
    )
    out = assignment.assign_workers(_workers(12), instances, seed=2)
    per_firm = out["firm_instance_id"].value_counts()
    assert (per_firm <= 3).all()


def test_output_carries_an_artificial_key_not_an_employer_identity():
    """The roster must never look like an observed link."""
    instances = assignment.expand_to_firm_instances(_frame([{}]), seed=1)
    out = assignment.assign_workers(_workers(3), instances, seed=1)
    assert "firm_instance_id" in out.columns
    assert "sponsor_ein" not in out.columns
    assert out.attrs["observed_link"] is False


def test_assignment_rejects_frames_missing_cell_keys():
    instances = assignment.expand_to_firm_instances(_frame([{}]), seed=1)
    bad = _workers(3).drop(columns=["canonical_band"])
    with pytest.raises(ValueError, match="canonical_band"):
        assignment.assign_workers(bad, instances, seed=1)


def test_assignment_rejects_instances_without_capacity():
    instances = assignment.expand_to_firm_instances(_frame([{}]), seed=1)
    with pytest.raises(ValueError, match="capacity"):
        assignment.assign_workers(
            _workers(3), instances.drop(columns=["capacity"]), seed=1
        )


def test_zero_capacity_cell_is_reported_not_silently_skipped():
    instances = assignment.expand_to_firm_instances(
        _frame([{"weight": 1, "active_participants": 0}]), seed=1
    )
    out = assignment.assign_workers(_workers(3), instances, seed=1)
    assert out["firm_instance_id"].isna().all()
    assert out.attrs["unassigned"][0]["reason"] == "zero capacity in cell"
