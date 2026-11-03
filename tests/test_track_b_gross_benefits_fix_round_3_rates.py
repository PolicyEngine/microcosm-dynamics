"""Non-finite bundle regressions over invented statutory families.

Verification class: statutory conformance. Admitted scope: exact gross
benefits for supported invented cases only, with no population, behavioral
or forecast claim. Every cross-checked rate must be finite before a family
or household coverage refusal can be counted in a denominator.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)
RATE_FIELDS = (
    ("early_monthly_rates", 0),
    ("early_monthly_rates", 1),
    ("spousal_early_monthly_rates", 0),
    ("spousal_early_monthly_rates", 1),
    ("survivor_reduction_floor", None),
    ("rib_lim_pia_share", None),
    ("spousal_pia_share", None),
    ("survivor_pia_share", None),
)
RATE_IDS = [
    field if index is None else f"{field}[{index}]"
    for field, index in RATE_FIELDS
]
NONFINITE = (float("nan"), float("inf"), -float("inf"))
ENTRY_POINTS = (
    "family",
    "household",
    "evaluate-family",
    "evaluate-household",
    "household-month-outcome",
)


def _with_rate(field, index, value):
    if index is not None:
        rates = list(getattr(PARAMS, field))
        rates[index] = value
        value = tuple(rates)
    return replace(PARAMS, **{field: value})


def _compute_refused(entry_point, params):
    child = g.Beneficiary("child", g.Role.CHILD)
    state = g.RecordState(g.FamilyKind.SURVIVOR, F(1000), F(1750))

    def family():
        return g.family_benefits(
            replace(
                state,
                conditions=frozenset({g.RecordCondition.NON_AIME_FORMULA_PIA}),
            ),
            [child],
            payment_month=NOW,
            params=params,
            standalone=True,
        )

    records = {
        key: g.HouseholdRecord(key, state, (child,))
        for key in ("worker-a", "worker-b")
    }

    def household():
        return g.household_benefits(records, payment_month=NOW, params=params)

    if entry_point == "family":
        return family()
    if entry_point == "household":
        return household()
    if entry_point == "household-month-outcome":
        guards = {
            key: g.SavingsClauseGuard(
                NOW,
                earlier_months_unknown=False,
                reading=g.SavingsClauseReading.LITERAL_REFUSAL,
            )
            for key in records
        }
        try:
            return g.household_month_outcome(
                records,
                payment_month=NOW,
                params=params,
                guards=guards,
            )
        except ValueError:
            # Invalid bundles cannot advance any record's monthly guard.
            assert all(guard.next_month == NOW for guard in guards.values())
            raise
    compute = family if entry_point == "evaluate-family" else household
    return g.evaluate_family("invented", F(3, 2), compute)


@pytest.mark.parametrize("field,index", RATE_FIELDS, ids=RATE_IDS)
@pytest.mark.parametrize("bad", NONFINITE, ids=["nan", "inf", "-inf"])
def test_nonfinite_statutory_rate_is_an_input_error(field, index, bad):
    with pytest.raises(ValueError, match="disagrees with the statutory") as e:
        g.statutory_rates(_with_rate(field, index, bad))
    assert type(e.value) is g.InvalidFamilyInput


@pytest.mark.parametrize("field,index", RATE_FIELDS, ids=RATE_IDS)
@pytest.mark.parametrize("bad", NONFINITE, ids=["nan", "inf", "-inf"])
@pytest.mark.parametrize("entry_point", ENTRY_POINTS)
def test_nonfinite_rate_error_precedes_coverage_refusal(
    field, index, bad, entry_point
):
    with pytest.raises(ValueError, match="disagrees with the statutory") as e:
        _compute_refused(entry_point, _with_rate(field, index, bad))
    assert type(e.value) is g.InvalidFamilyInput


@pytest.mark.parametrize("entry_point", ENTRY_POINTS)
def test_finite_rate_mismatch_also_precedes_coverage_refusal(entry_point):
    with pytest.raises(ValueError, match="disagrees with the statutory"):
        _compute_refused(entry_point, ssa_params(spousal_pia_share=0.6))


@pytest.mark.parametrize("entry_point", ENTRY_POINTS)
def test_valid_bundle_retains_the_existing_coverage_refusal(entry_point):
    expected = (
        g.UnsupportedReason.NON_AIME_FORMULA_PIA
        if entry_point in ("family", "evaluate-family")
        else g.UnsupportedReason.COMBINED_FAMILY_MAXIMUM
    )
    if entry_point in ("family", "household"):
        with pytest.raises(g.FamilyConfigurationUnsupported) as e:
            _compute_refused(entry_point, PARAMS)
        assert e.value.reason is expected
    else:
        outcome = _compute_refused(entry_point, PARAMS)
        assert outcome.unsupported.reason is expected
        counts = g.count_family_outcomes([outcome])
        weight = F(1) if entry_point == "household-month-outcome" else F(3, 2)
        assert (counts.rows, counts.weight) == (1, weight)
        assert (counts.unsupported_rows, counts.unsupported_weight) == (
            1,
            weight,
        )


@given(
    st.sampled_from(RATE_FIELDS),
    st.sampled_from(NONFINITE),
    st.sampled_from(ENTRY_POINTS),
)
@settings(deadline=None)
def test_nonfinite_rate_never_becomes_a_coverage_outcome(rate, bad, entry):
    field, index = rate
    with pytest.raises(ValueError, match="disagrees with the statutory"):
        _compute_refused(entry, _with_rate(field, index, bad))


@given(st.sampled_from(RATE_FIELDS), st.integers(-90, 90))
@settings(deadline=None)
def test_finite_rate_tolerance_preserves_exact_statutory_fractions(
    rate, nanos
):
    # Existing tolerance is 1e-7; accepted decimals never become money rates.
    field, index = rate
    value = getattr(PARAMS, field)
    value = value if index is None else value[index]
    perturbed = _with_rate(field, index, value + nanos / 1_000_000_000)
    assert g.statutory_rates(perturbed) == g.statutory_rates(PARAMS)


@pytest.mark.parametrize("bad", NONFINITE, ids=["nan", "inf", "-inf"])
def test_other_bundle_number_checks_already_reject_nonfinite_values(bad):
    for field in (
        "early_first_bracket_months",
        "spousal_early_first_bracket_months",
    ):
        with pytest.raises(ValueError):
            g.statutory_rates(replace(PARAMS, **{field: bad}))
    nawi = dict(PARAMS.nawi)
    nawi[2024] = bad
    with pytest.raises(ValueError, match="finite"):
        g.family_maximum_bend_points(2026, replace(PARAMS, nawi=nawi))
    with pytest.raises(ValueError, match="finite"):
        g.worker_age_adjusted(
            F(1000),
            0,
            1,
            1960,
            replace(PARAMS, delayed_credit_by_birth_year=[(1900, bad)]),
        )


@pytest.mark.parametrize("bad", NONFINITE, ids=["nan", "inf", "-inf"])
@pytest.mark.parametrize("entry_point", ["benefit", "credit-window"])
def test_nonfinite_full_retirement_age_is_an_input_error(bad, entry_point):
    params = replace(PARAMS, fra_months_by_birth_year=[(1900, bad)])
    with pytest.raises(ValueError, match="finite"):
        if entry_point == "credit-window":
            g.delayed_credit_window_months(1960, params)
            return
        g.worker_age_adjusted(
            F(1000),
            0,
            0,
            1960,
            params,
        )


@given(st.sampled_from(NONFINITE), st.integers(1917, 2000))
@settings(deadline=None)
def test_nonfinite_full_retirement_age_never_produces_a_credit_window(
    bad, birth_year
):
    params = replace(PARAMS, fra_months_by_birth_year=[(1900, bad)])
    with pytest.raises(ValueError, match="finite"):
        g.delayed_credit_window_months(birth_year, params)
