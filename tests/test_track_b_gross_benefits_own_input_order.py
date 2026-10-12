"""Own-DIB input-order regressions over invented statutory families.

Verification class: statutory conformance. These tests admit gross benefits
only for supported configurations, with no population, behavioral or
forecast claim. A DIB reduced for prior RIB remains a 402(q)(2) coverage
refusal; constructing its declaration must not hide invalid family inputs.
The minimized case uses own PIA 100 and one reduction month, with no birth
year or record-date metadata, then duplicates a child beneficiary.
"""

from __future__ import annotations

from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)


def _own(months):
    return g.OwnBenefit(
        g.OwnBenefitKind.DISABILITY, F(100), reduction_months=months
    )


def _members(own, invalid):
    if invalid == "wrong_role":
        return [g.Beneficiary("p", g.Role.PARENT, own_benefit=own)]
    kwargs = {}
    if invalid == "negative_months":
        kwargs["reduction_months"] = -1
    elif invalid == "wrong_period":
        kwargs["reduction_period_months"] = 60
    child = g.Beneficiary("c", g.Role.CHILD, own_benefit=own, **kwargs)
    return [child, child] if invalid == "duplicate" else [child]


def _evaluate(prebuilt, months, invalid=None):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(1000),
        F(1750),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000)),
    )
    own = _own(months) if prebuilt else None

    def compute():
        declaration = own if prebuilt else _own(months)
        return g.family_benefits(
            state,
            _members(declaration, invalid),
            payment_month=NOW,
            params=PARAMS,
            standalone=True,
        )

    return g.evaluate_family("own-dib", F(3, 2), compute)


@pytest.mark.parametrize("prebuilt", [False, True])
def test_minimized_duplicate_input_precedes_own_dib_refusal(prebuilt):
    with pytest.raises(g.InvalidFamilyInput, match="unique"):
        _evaluate(prebuilt, 1, "duplicate")


@given(
    st.integers(1, 60),
    st.booleans(),
    st.sampled_from(
        ["duplicate", "wrong_role", "negative_months", "wrong_period"]
    ),
)
@settings(deadline=None)
def test_family_input_errors_precede_own_dib_refusal_in_both_entry_styles(
    months, prebuilt, invalid
):
    """Invalid families propagate; they cannot become coverage outcomes."""
    with pytest.raises(g.InvalidFamilyInput):
        _evaluate(prebuilt, months, invalid)


@given(st.integers(1, 60), st.booleans())
@settings(deadline=None)
def test_valid_reduced_own_dib_is_refused_and_kept_in_denominators(
    months, prebuilt
):
    outcome = _evaluate(prebuilt, months)
    reason = g.UnsupportedReason.DIB_AFTER_REDUCED_RIB
    assert not outcome.supported
    assert outcome.unsupported.reason is reason
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight) == (1, F(3, 2))
    assert (counts.unsupported_rows, counts.unsupported_weight) == (
        1,
        F(3, 2),
    )
    assert counts.unsupported_by_reason == {reason: (1, F(3, 2))}


@given(st.integers(1, 60))
@settings(deadline=None)
def test_own_dib_primitive_retains_the_402q2_coverage_refusal(months):
    own = _own(months)
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        g.own_monthly_benefit(own, PARAMS)
    assert caught.value.reason is g.UnsupportedReason.DIB_AFTER_REDUCED_RIB
    assert g.own_monthly_benefit(_own(0), PARAMS) == (F(100), F(100))
    with pytest.raises(g.InvalidFamilyInput):
        g.own_monthly_benefit(_own(61), PARAMS)
    assert (
        "such disability insurance benefit for each month shall be reduced "
        "by the amount such old-age insurance benefit would be reduced "
        "under paragraphs (1) and (4)" in source_text("ssa_act_202_215")
    )
