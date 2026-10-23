"""G round-2 regressions for the discrete widow(er) reduction periods.

Verification class: statutory conformance. The captured RS 00615.301B.2
chart and invented monetary cases admit no population, behavioral or
forecast claim. Exact family/primitive differentials have zero tolerance.
"""

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)
LEGAL_PERIODS = tuple(range(60, 85, 2))
ODD_PERIODS = tuple(range(61, 84, 2))
STYLES = ("age_primitive", "fraction_primitive", "built", "direct")
AGED_WIDOW_ROLES = (g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE)


def _state(style, pia, *, refused=False):
    conditions = (
        {g.RecordCondition.WORKERS_COMPENSATION_OFFSET} if refused else set()
    )
    if style == "built":
        state = g.record_state(
            g.WorkerRecord(
                g.FamilyKind.SURVIVOR, 2020, pia, conditions=conditions
            ),
            PARAMS,
        )
        return replace(state, widow_drc_savings_clause=False)
    return g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        g.floor_dime(pia * F(3, 2)),
        conditions=conditions,
        widow_drc_savings_clause=False,
    )


def _compute(style, pia, months, period, *, role=g.Role.WIDOW):
    if style == "age_primitive":
        return g.survivor_age_reduced(pia, months, period, PARAMS)
    if style == "fraction_primitive":
        return g.survivor_reduction_fraction(months, period, PARAMS)
    widow = g.Beneficiary(
        "w", role, reduction_months=months, reduction_period_months=period
    )
    result = g.family_benefits(
        _state(style, pia),
        [widow],
        payment_month=NOW,
        params=PARAMS,
        standalone=True,
    )
    return result.by_id()["w"].auxiliary_payable


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize(
    "pia,months", [(F("11.60"), 60), (F("673.70"), 1), (F(1000), 60)]
)
def test_review_odd_period_61_rejects_minimized_cases_without_birth_year(
    style, pia, months
):
    # Reviewer replay: RF61 used to pay $8.30, $670.50 or $719.60 even
    # though no cohort has this total possible reduction period.
    with pytest.raises(g.InvalidFamilyInput, match="reduction_period"):
        _compute(style, pia, months, 61)


@pytest.mark.parametrize("style", ["built", "direct"])
@pytest.mark.parametrize("role", AGED_WIDOW_ROLES)
@pytest.mark.parametrize("period", ODD_PERIODS)
def test_every_odd_period_is_invalid_in_both_aged_widow_roles_and_styles(
    style, role, period
):
    with pytest.raises(g.InvalidFamilyInput, match="reduction_period"):
        _compute(style, F("11.60"), 60, period, role=role)


@pytest.mark.parametrize("style", ["built", "direct"])
@pytest.mark.parametrize("role", AGED_WIDOW_ROLES)
@pytest.mark.parametrize("refusal", ["record", "beneficiary"])
def test_odd_period_input_error_precedes_record_and_beneficiary_refusals(
    style, role, refusal
):
    state = _state(style, F("11.60"), refused=refusal == "record")
    with pytest.raises(g.InvalidFamilyInput, match="reduction_period"):
        # Keep construction in the family closure: invalid inputs must
        # escape evaluate_family instead of becoming a refused row.
        g.evaluate_family(
            "odd-period",
            F(3, 2),
            lambda: g.family_benefits(
                state,
                [
                    g.Beneficiary(
                        "w",
                        role,
                        reduction_months=60,
                        reduction_period_months=61,
                        conditions=(
                            {g.BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD}
                            if refusal == "beneficiary"
                            else set()
                        ),
                    )
                ],
                payment_month=NOW,
                params=PARAMS,
                standalone=True,
            ),
        )


@pytest.mark.parametrize("style", ["built", "direct"])
@pytest.mark.parametrize("role", AGED_WIDOW_ROLES)
def test_known_cohort_still_rejects_another_legal_period(style, role):
    widow = g.Beneficiary(
        "w",
        role,
        birth_year=1935,
        reduction_months=60,
        reduction_period_months=62,
    )
    with pytest.raises(g.InvalidFamilyInput, match="cohort"):
        g.family_benefits(
            _state(style, F("11.60")),
            [widow],
            payment_month=NOW,
            params=PARAMS,
            standalone=True,
        )


@pytest.mark.parametrize("style", ["age_primitive", "built", "direct"])
@pytest.mark.parametrize(
    "period,payable",
    tuple(
        zip(
            LEGAL_PERIODS,
            map(
                F,
                (
                    "8.20",
                    "8.40",
                    "8.50",
                    "8.50",
                    "8.60",
                    "8.70",
                    "8.80",
                    "8.90",
                    "8.90",
                    "9.00",
                    "9.10",
                    "9.10",
                    "9.20",
                ),
            ),
            strict=True,
        )
    ),
)
def test_review_legal_periods_never_produce_impossible_8_30(
    style, period, payable
):
    actual = _compute(style, F("11.60"), 60, period)
    assert actual == payable
    assert actual != F("8.30")
    assert g.whole_dollars(actual) == int(payable)


@given(
    st.sampled_from(STYLES),
    st.sampled_from(LEGAL_PERIODS),
    st.integers(1, 1_000_000),
    st.data(),
)
@settings(deadline=None)
def test_property_every_legal_period_matches_exact_integer_reference(
    style, period, pia_dimes, data
):
    months = data.draw(st.integers(0, period), label="reduction months")
    result = _compute(style, F(pia_dimes, 10), months, period)
    if style == "fraction_primitive":
        assert result == F(57 * months, 200 * period)
    else:
        numerator = pia_dimes * 57 * months
        denominator = 200 * period
        reduction_dimes = (numerator + denominator - 1) // denominator
        assert result == F(pia_dimes - reduction_dimes, 10)
        assert 0 <= result <= F(pia_dimes, 10)
        assert (result * 10).denominator == 1


@given(
    st.sampled_from(STYLES),
    st.integers(-100, 200).filter(lambda period: period not in LEGAL_PERIODS),
    st.integers(0, 60),
)
@settings(deadline=None)
def test_property_every_nonstatutory_integer_period_is_an_input_error(
    style, period, months
):
    with pytest.raises(g.InvalidFamilyInput, match="reduction_period"):
        _compute(style, F("11.60"), months, period)


def test_rule_text_is_quoted_from_the_capture_for_each_discrete_period():
    text = source_text("poms_rs_00615_301")
    rows = (
        "Through 1/1/40 65 19/40",
        "1/2/40 - 1/1/41 65 + 2 57/124",
        "1/2/41 - 1/1/42 65 + 4 57/128",
        "1/2/42 - 1/1/43 65 + 6 19/44",
        "1/2/43 - 1/1/44 65 + 8 57/136",
        "1/2/44 - 1/1/45 65 + 10 57/140",
        "1/2/45 - 1/1/57 66 19/48",
        "1/2/57 - 1/1/58 66 + 2 57/148",
        "1/2/58 - 1/1/59 66 + 4 57/152",
        "1/2/59 - 1/1/60 66 + 6 19/52",
        "1/2/60 - 1/1/61 66 + 8 57/160",
        "1/2/61 - 1/1/62 66 + 10 57/164",
        "1/2/62 or later 67 19/56",
    )
    assert len(rows) == len(LEGAL_PERIODS)
    for row in rows:
        assert row in text
