"""Statutory conformance: malformed public helpers never create observations.

Invented cases only; no population, behavioral or forecast claim.
"""

from copy import copy
from fractions import Fraction as F

import pytest

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import computed_refusal, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2023, 12)


def _result():
    return g.family_benefits(
        g.RecordState(
            g.FamilyKind.SURVIVOR, F(0), F(0), widow_drc_savings_clause=False
        ),
        (),
        payment_month=NOW,
        params=PARAMS,
        standalone=True,
    )


def test_boolean_pia_is_invalid_before_historical_refusal_and_guard():
    guard = g.SavingsClauseGuard(
        NOW,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    before = vars(guard).copy()
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(
            guard.evaluate(
                "bad",
                F(7, 3),
                lambda: g.retirement_survivor_family_maximum(
                    True, 1982, PARAMS
                ),
            )
        )
    assert outcomes == []
    assert g.count_family_outcomes(outcomes).weight == 0
    assert vars(guard) == before


@pytest.mark.parametrize("field,value", [("year", True), ("month", 13)])
def test_cola_helper_revalidates_calendar_fields(field, value):
    month = copy(NOW)
    object.__setattr__(month, field, value)
    with pytest.raises(g.InvalidFamilyInput):
        g.applicable_cola_percents(2023, month, {2023: F(3)})


@pytest.mark.parametrize(
    "field,value", [("beneficiaries", None), ("record_total", F(-1))]
)
@pytest.mark.parametrize("method", ["admit", "evaluate"])
def test_guard_revalidates_entire_result_before_any_state_change(
    field, value, method
):
    result = _result()
    # Bypass frozen construction to test defensive public consumption too.
    object.__setattr__(result, field, value)
    guard = g.SavingsClauseGuard(
        NOW,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    before = vars(guard).copy()
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        if method == "admit":
            guard.admit(result)
        else:
            outcomes.append(guard.evaluate("bad", F(7, 3), lambda: result))
    assert outcomes == []
    assert g.count_family_outcomes(outcomes).rows == 0
    assert vars(guard) == before


def test_guard_revalidates_refusal_before_skipping():
    refusal = computed_refusal(g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET)
    object.__setattr__(
        refusal, "reason", g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET
    )
    guard = g.SavingsClauseGuard(
        NOW,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    before = vars(guard).copy()

    def compute():
        raise refusal

    with pytest.raises(g.InvalidFamilyInput):
        guard.evaluate("bad", F(7, 3), compute)
    assert vars(guard) == before


@pytest.mark.parametrize(
    "consumer",
    [
        g.count_family_outcomes,
        g.weighted_record_total,
        g.weighted_mean_record_total,
    ],
)
def test_consumers_validate_all_rows_before_coverage(consumer):
    def compute_refused():
        raise computed_refusal(g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET)

    refused = g.evaluate_family("refused", F(7, 3), compute_refused)
    malformed = g.evaluate_family("bad", F(1), _result)
    object.__setattr__(malformed.benefits, "record_total", F(-1))
    with pytest.raises(g.InvalidFamilyInput):
        consumer([refused, malformed])
