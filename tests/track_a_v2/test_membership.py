"""INVENTED DATA - NOT A COMPARISON: §§9, 12.7 membership invariants."""

import math
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.ss.benefits import spousal_benefit
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.track_a_v2.matrix import MECHANISMS, get_row
from populace_dynamics.track_a_v2.membership import (
    MembershipRefusal,
    guard_membership,
)


def parameters(fra):
    return SSAParameters(
        nawi={1977: 100},
        wage_base={1951: 1e9},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, fra)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="invented",
    )


def record(base=100, reform=0, *, component="retired_worker", **extra):
    return {
        "draw": 0,
        "person_id": 1,
        "family_unit_id": 1,
        "weight": 1,
        "birth_year": 1963,
        "beneficiary_base": base > 0,
        "beneficiary_reform": reform > 0,
        "benefit_base": base,
        "benefit_reform": reform,
        "benefit_components": {component: {"base": base, "reform": reform}},
        "basis": "projected",
        "own_kind_base": "retired",
        "own_kind_reform": "retired",
        **extra,
    }


def guard(rows, mechanism="L", row_id="F0"):
    return guard_membership(
        rows,
        get_row(mechanism, row_id),
        baseline_params=parameters(804),
        reform_params=parameters(816),
    )


def legacy():
    return record(
        component="spouse",
        own_kind_base="converted",
        own_kind_reform="disabled",
    )


@pytest.mark.parametrize("mechanism", MECHANISMS)
@pytest.mark.parametrize("row_id", ("F0", "F1", "F2", "F5", "F6", "F7", "U0"))
@pytest.mark.parametrize("base,reform", ((100, 0), (0, 100)))
def test_every_c0_unexplained_direction_refuses(
    mechanism, row_id, base, reform
):
    """Both unexplained C0 directions refuse before any tabulation (§10.5)."""
    with pytest.raises(MembershipRefusal) as exc:
        guard([record(base, reform)], mechanism, row_id)
    assert (exc.value.person_id, exc.value.draw, exc.value.step) == (1, 0, 5)
    assert exc.value.counters["n_rows_differ"] == 1


@pytest.mark.parametrize("mechanism", MECHANISMS)
@pytest.mark.parametrize("row_id", tuple(f"R{i}" for i in range(6)))
@pytest.mark.parametrize("base,reform", ((100, 0), (0, 100)))
def test_r_unfiltered_both_directions_reach_guard(
    mechanism, row_id, base, reform
):
    """R catches baseline-zero reform-only people before the legacy filter."""
    item = record(base, reform)
    # Intended invalid input flags: §9 reconstructs truthful flags from totals.
    item["beneficiary_base"] = item["beneficiary_reform"] = False
    with pytest.raises(MembershipRefusal) as exc:
        guard([item], mechanism, row_id)
    assert exc.value.step == 3
    assert exc.value.person_id == 1


@pytest.mark.parametrize("mechanism", MECHANISMS)
@pytest.mark.parametrize("row_id", tuple(f"R{i}" for i in range(6)))
def test_r_double_zero_flags_do_not_refuse(mechanism, row_id):
    """Two false selected-recipient flags agree and do not trigger refusal."""
    assert guard([record(0, 0)], mechanism, row_id)["n_rows_differ"] == 0


@pytest.mark.parametrize("mechanism", MECHANISMS)
@pytest.mark.parametrize("reverse", (False, True))
def test_component_selection_not_all_component_totals_controls_guard(
    mechanism, reverse
):
    """Workers-only R5 and F6 use selected components before filtering."""
    base, reform = (0, 100) if reverse else (100, 0)
    item = record(base, reform)
    item["benefit_components"]["spouse"] = {
        "base": 100 - base,
        "reform": 100 - reform,
    }
    item["benefit_base"] = item["benefit_reform"] = 100
    item["beneficiary_base"] = item["beneficiary_reform"] = True
    assert guard([item], mechanism, "R0")["n_rows_differ"] == 0
    for row_id in ("R5", "F6"):
        with pytest.raises(MembershipRefusal):
            guard([item], mechanism, row_id)


@pytest.mark.parametrize("mechanism", MECHANISMS)
def test_r_retains_all_component_baseline_positive_reform_zero_check(
    mechanism,
):
    """R retains the per-person all-component refusal before selected filtering."""
    with pytest.raises(MembershipRefusal) as exc:
        guard([legacy()], mechanism, "R5")
    assert exc.value.step == 3


@pytest.mark.parametrize("mechanism", MECHANISMS)
@pytest.mark.parametrize("row_id", ("F0", "F1", "F2", "F5", "F7", "U0"))
def test_exact_legacy_conjunction_only_admitted_for_l_and_d(mechanism, row_id):
    """The complete legacy conjunction excuses C0 only under L and D."""
    if mechanism in ("L", "D"):
        assert (
            guard([legacy()], mechanism, row_id)["n_legacy_predicate_matches"]
            == 1
        )
    else:
        with pytest.raises(MembershipRefusal) as exc:
            guard([legacy()], mechanism, row_id)
        assert exc.value.counters["n_legacy_predicate_matches"] == 1


@pytest.mark.parametrize("mechanism", ("L", "D"))
@pytest.mark.parametrize(
    "mutation",
    (
        "direction",
        "basis",
        "baseline_kind",
        "reform_kind",
        "no_straddle",
        "other_component",
        "absent_spouse",
        "worker_selection",
    ),
)
def test_every_legacy_conjunct_is_required(mechanism, mutation):
    """Dropping any legacy predicate condition cannot excuse a C0 difference."""
    item = legacy()
    row_id = "F0"
    if mutation == "direction":
        item = record(0, 100, component="spouse")
    elif mutation == "basis":
        item["basis"] = "opening_stock"
    elif mutation == "baseline_kind":
        item["own_kind_base"] = "retired"
    elif mutation == "reform_kind":
        item["own_kind_reform"] = "retired"
    elif mutation == "no_straddle":
        item["birth_year"] = 1960
    elif mutation == "other_component":
        item["benefit_components"]["retired_worker"] = {
            "base": 10,
            "reform": 0,
        }
        item["benefit_base"] += 10
    else:
        item["benefit_components"] = {
            "retired_worker": {"base": 100, "reform": 0}
        }
        if mutation == "worker_selection":
            row_id = "F6"
    with pytest.raises(MembershipRefusal):
        guard([item], mechanism, row_id)


@pytest.mark.parametrize("mechanism", MECHANISMS)
@pytest.mark.parametrize("row_id", ("F3", "F4", "U1", "U2"))
def test_c1_c2_count_both_directions_and_legacy_matches(mechanism, row_id):
    """C1/C2 count and allow both directions; legacy matches are diagnostic."""
    rows = [legacy(), record(0, 100, person_id=2, family_unit_id=2)]
    result = guard(rows, mechanism, row_id)
    assert result["n_rows_baseline_only"] == 1
    assert result["n_rows_reform_only"] == 1
    assert result["n_legacy_predicate_matches"] == 1


@pytest.mark.parametrize("mechanism", MECHANISMS)
def test_dime_floor_boundary_has_no_exception(mechanism):
    """Positive factors can cross zero after flooring; no C0 exception exists."""
    params = parameters(804)
    base = math.floor(10 * spousal_benefit(0, 0.30, 48, params)) / 10
    reform = math.floor(10 * spousal_benefit(0, 0.30, 60, params)) / 10
    assert (base, reform) == (0.1, 0)
    with pytest.raises(MembershipRefusal):
        guard([record(base, reform, component="spouse")], mechanism)


@given(st.permutations([0, 1, 2]))
@settings(max_examples=6, deadline=None)
def test_first_failing_person_draw_and_counts_are_deterministic(order):
    """Refusal identity and counts do not depend on per-person row order."""
    rows = [record(person_id=p + 1, family_unit_id=p + 1) for p in range(3)]
    with pytest.raises(MembershipRefusal) as exc:
        guard([deepcopy(rows[p]) for p in order])
    assert exc.value.person_id == 1
    assert exc.value.counters["n_rows_baseline_only"] == 3
