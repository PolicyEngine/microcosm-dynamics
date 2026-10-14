"""Invented cross-result publication invariants; no artifact or data read."""

from copy import deepcopy

from hypothesis import given, settings
from hypothesis import strategies as st

from scripts.d1408_projection_publication import (
    MARKER,
    protect_cross_result_privacy,
)


def _cell(people, workers=None):
    return {
        "people": people,
        "worker_records": people if workers is None else workers,
        "weight": float(10 * people),
        "admitted_weight_share": people / 1000,
    }


def _fixture(n, extra, *, worker_only=False, changed_only=False):
    total = n + extra + 50
    result, ledger = [], []
    for left in (True, False):
        count = n + extra if changed_only or (left and not worker_only) else n
        recipients = set(range(count))
        associations = {
            (
                2011,
                person,
                (
                    n + person
                    if worker_only and not left and person < extra
                    else person
                ),
            )
            for person in recipients
        }
        records = {
            (wave, worker, "old_age") for wave, _, worker in associations
        }
        changed_count = (n + extra if left else n) if changed_only else count
        changed = set(range(changed_count))
        public = {
            "counts": {
                "2011": {
                    "seed_cohort_weight": float(total * 10),
                    "supported/factor_evaluation": _cell(len(records)),
                    "supported/recipient": _cell(
                        len(recipients), len(records)
                    ),
                    "supported/empty": _cell(0),
                    "supported/hidden": {key: "<10" for key in _cell(0)},
                }
            },
            "admitted_beneficiary_counts_by_row": {
                "row": {
                    "admitted_people": total,
                    "admitted_weight": float(total * 10),
                    "mean_draw_admitted_weight": float(total * 10),
                    "supported/factor_evaluation": _cell(
                        len(recipients), len(records)
                    ),
                }
            },
            "headline_changes": {
                "row": {
                    "changed_recipients": len(changed),
                    "groups": {
                        "positive": {
                            "changed_recipients": len(changed),
                            "model_headlines": {"mean": 1.25},
                        },
                        "empty": {
                            "changed_recipients": 0,
                            "model_headlines": {"change": None},
                        },
                        "hidden": {
                            "changed_recipients": "<10",
                            "model_headlines": "<10",
                        },
                    },
                }
            },
            "reproduction_check": {
                "verified": True,
                "projection_draws_exact": True,
            },
            "counts_verified": True,
        }
        if worker_only:
            public["counts"]["2011"]["supported/factor_evaluation"] = {
                key: MARKER for key in _cell(0)
            }
        result.append(public)
        ledger.append(
            {
                "events": {
                    ("supported", "factor_evaluation"): records,
                    ("supported", "recipient"): associations,
                },
                "row_events": {
                    ("row", "supported", "factor_evaluation"): records,
                    ("row", "supported", "recipient"): associations,
                },
                "changed_people_by_row": {"row": changed},
                "row_waves": {"row": 2011},
                "admitted_people_by_row": {"row": set(range(total))},
            }
        )
    return *result, *ledger


def _assert_masked(fra):
    assert set(fra["counts"]["2011"]["supported/recipient"].values()) == {
        MARKER
    }
    assert set(
        fra["admitted_beneficiary_counts_by_row"]["row"][
            "supported/factor_evaluation"
        ].values()
    ) == {MARKER}
    change = fra["headline_changes"]["row"]
    assert change["changed_recipients"] == MARKER
    assert change["groups"]["positive"] == {
        "changed_recipients": MARKER,
        "model_headlines": MARKER,
    }


def test_minimized_cross_result_residual_is_withheld():
    cola, fra, left, right = _fixture(10, 1)
    protect_cross_result_privacy(cola, fra, left, right)
    _assert_masked(fra)


@settings(deadline=None)
@given(
    n=st.integers(10, 40),
    extra=st.integers(1, 9),
    reverse=st.booleans(),
    cola_wave=st.sampled_from((2009, 2011)),
)
def test_small_people_residual_masks_counts_weights_shares_and_changes(
    n, extra, reverse, cola_wave
):
    cola, fra, left, right = _fixture(n, extra)
    if reverse:
        cola, fra, left, right = fra, cola, right, left
    if cola_wave != 2011:
        cola["counts"][str(cola_wave)] = cola["counts"].pop("2011")
        for name in ("events", "row_events"):
            left[name] = {
                key: {
                    (cola_wave, person, worker) for _, person, worker in rows
                }
                for key, rows in left[name].items()
            }
        left["row_waves"]["row"] = cola_wave
    before_cola, before_left, before_right = deepcopy((cola, left, right))
    admitted = deepcopy(fra["admitted_beneficiary_counts_by_row"]["row"])
    reproduction = deepcopy(fra["reproduction_check"])
    protect_cross_result_privacy(cola, fra, left, right)
    _assert_masked(fra)
    assert (cola, left, right) == (before_cola, before_left, before_right)
    row = fra["admitted_beneficiary_counts_by_row"]["row"]
    for field in (
        "admitted_people",
        "admitted_weight",
        "mean_draw_admitted_weight",
    ):
        assert row[field] == admitted[field]
    assert fra["reproduction_check"] == reproduction
    assert fra["counts_verified"] is True
    assert fra["counts"]["2011"]["supported/empty"] == _cell(0)
    assert set(fra["counts"]["2011"]["supported/hidden"].values()) == {"<10"}
    groups = fra["headline_changes"]["row"]["groups"]
    assert groups["empty"] == {
        "changed_recipients": 0,
        "model_headlines": {"change": None},
    }
    assert groups["hidden"] == {
        "changed_recipients": "<10",
        "model_headlines": "<10",
    }


@settings(deadline=None)
@given(n=st.integers(10, 40), extra=st.integers(1, 9))
def test_small_worker_residual_masks_even_when_people_are_identical(n, extra):
    cola, fra, left, right = _fixture(n, extra, worker_only=True)
    assert {r[1] for r in left["events"][("supported", "recipient")]} == {
        r[1] for r in right["events"][("supported", "recipient")]
    }
    protect_cross_result_privacy(cola, fra, left, right)
    _assert_masked(fra)


@settings(deadline=None)
@given(n=st.integers(10, 40), extra=st.one_of(st.just(0), st.integers(10, 20)))
def test_equal_memberships_and_residuals_at_least_ten_remain_public(n, extra):
    cola, fra, left, right = _fixture(n, extra)
    original = deepcopy((cola, fra, left, right))
    protect_cross_result_privacy(cola, fra, left, right)
    assert (cola, fra, left, right) == original


@settings(deadline=None)
@given(n=st.integers(10, 40), extra=st.integers(1, 9))
def test_changed_row_residual_also_masks_wave_count_aliases(n, extra):
    cola, fra, left, right = _fixture(n, extra, changed_only=True)
    assert left["events"] == right["events"]
    protect_cross_result_privacy(cola, fra, left, right)
    _assert_masked(fra)


@settings(deadline=None)
@given(n=st.integers(10, 40), extra=st.integers(1, 9))
def test_cross_result_publication_is_deterministic_order_independent_and_idempotent(
    n, extra
):
    cola, fra, left, right = _fixture(n, extra)
    other_cola, other_fra, other_left, other_right = deepcopy(
        (cola, fra, left, right)
    )
    for ledger in (other_left, other_right):
        for name in (
            "events",
            "row_events",
            "changed_people_by_row",
            "row_waves",
            "admitted_people_by_row",
        ):
            ledger[name] = dict(reversed(list(ledger[name].items())))
    method = protect_cross_result_privacy(cola, fra, left, right)
    other_method = protect_cross_result_privacy(
        other_cola, other_fra, other_left, other_right
    )
    assert fra == other_fra
    assert method == other_method
    once = deepcopy(fra)
    assert protect_cross_result_privacy(cola, fra, left, right) == method
    assert fra == once
