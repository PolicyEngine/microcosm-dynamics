"""Round 6: rates a hold can lower and original rates it cannot.

Every record is invented or copied from a captured SSA example. Nothing here
admits a population, behavioral or forecast claim.
"""

from __future__ import annotations

import html
import re
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import BenefitType as T
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = load_ret_parameters()
RC = g.RecordCondition
BC = g.BeneficiaryCondition
UR = g.UnsupportedReason
ARF_SOURCES = Path(__file__).parent / "data/track_b/arf_recompute_sources"
LOWERING_REASONS = (
    UR.DUAL_ENTITLEMENT_SEQUENCE,
    UR.OWN_RIB_HISTORY_BEFORE_1978,
    UR.REDUCED_BENEFIT_HISTORY_BEFORE_1978,
    UR.DIB_AFTER_REDUCED_RIB,
    UR.WORKERS_COMPENSATION_OFFSET,
)
HISTORY_REASONS = (
    UR.DUAL_ENTITLEMENT_SEQUENCE,
    UR.REDUCED_BENEFIT_HISTORY_BEFORE_1978,
)
PRE_1978_REASONS = (
    UR.OWN_RIB_HISTORY_BEFORE_1978,
    UR.REDUCED_BENEFIT_HISTORY_BEFORE_1978,
)
# Written out, not read from G's table: an edit to the table must fail here.
DIB_UNSETTLING_REASONS = frozenset(
    {*LOWERING_REASONS, UR.ADMINISTRATIVE_FINALITY}
)
RIB_UNSETTLING_REASONS = frozenset(
    {
        *HISTORY_REASONS,
        UR.WORKERS_COMPENSATION_OFFSET,
        UR.ADMINISTRATIVE_FINALITY,
    }
)


def _outcome(case):
    return r.evaluate_ret(
        "round6", F(7), lambda: r.apply_ret_year(case, PARAMS)
    )


def _assert_refusal(case, reason):
    outcome = _outcome(case)
    assert not outcome.supported
    assert outcome.unsupported.reason is reason
    counts = r.count_ret_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


def _assert_invalid(case):
    rows = []
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(_outcome(case))
    counts = r.count_ret_outcomes(rows)
    assert (counts.rows, counts.weight) == (0, 0)


def _assert_preflight_neutral(case):
    actual = _outcome(case)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(r, "_check_settled_family_facts", lambda record: None)
        without = _outcome(case)
    assert actual.supported == without.supported
    assert not actual.supported
    assert actual.unsupported.reason is without.unsupported.reason
    assert actual.unsupported.detail == without.unsupported.detail
    assert r.count_ret_outcomes([actual]) == r.count_ret_outcomes([without])


def _published_widow_drc(flag, child_original, *, scale=100, child_gross=None):
    """RS 00615.712B: PIA $400, maximum $700, widow $410 with DRCs."""
    pia, maximum = F(4 * scale), F(7 * scale)
    basis = pia + F(1, 10) * (scale // 10 or 1)
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        maximum,
        eligibility_year=1999,
        widow_drc_savings_clause=flag,
    )
    members = (
        g.Beneficiary(
            "w",
            g.Role.WIDOW,
            birth_year=1934,
            child_in_care=False,
            original_benefit_basis=basis,
        ),
        g.Beneficiary("c", g.Role.CHILD),
    )
    return r.RecordYear(
        2000,
        "nh",
        r.RecordKind.DECEASED,
        (
            r.RETBeneficiary(
                "w",
                (T.WIDOW,) * 12,
                {1},
                (pia,) + (F(0),) * 11,
                (basis,) * 12,
                fra_month=0,
            ),
            r.RETBeneficiary(
                "c",
                (T.CDB,) * 12,
                {1},
                (F(3 * scale) if child_gross is None else child_gross,)
                + (F(0),) * 11,
                (child_original,) * 12,
                fra_month=0,
            ),
        ),
        family_months={
            1: r.RETFamilyMonth(
                state, members, ssa_params(), {"w": "h", "c": "h"}
            )
        },
        family_maximum_binding_months={1},
    )


def _rib_record(pia, gross, *, birth=1927, reason=None, conditions=()):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        g.floor_dime(pia * F(3, 2)),
        worker=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            pia,
            reduction_months=12,
            birth_year=birth,
        ),
        eligibility_year=birth + 62,
        conditions=conditions,
        deferred_refusal=(
            None if reason is None else (reason, "invented declared history")
        ),
    )
    return r.RecordYear(
        2000,
        "nh",
        r.RecordKind.RETIREMENT,
        (
            r.RETBeneficiary(
                "nh",
                (T.RIB,) * 12,
                {1},
                (gross,) + (F(0),) * 11,
                (pia,) * 12,
                fra_month=0,
            ),
        ),
        family_months={1: r.RETFamilyMonth(state, (), ssa_params(), {})},
    )


def _dib_record(pia, gross, *, reason=None, conditions=(), birth=None):
    if birth is None:
        birth = 1927 if reason in PRE_1978_REASONS else 1960
    year = 1985 if birth < 1960 else 2024
    state = g.RecordState(
        g.FamilyKind.DISABILITY,
        pia,
        g.floor_dime(pia * F(3, 2)),
        worker_birth_year=birth,
        eligibility_year=year - 1,
        first_dib_entitlement=g.YearMonth(year - 1, 1),
        conditions=conditions,
        deferred_refusal=(
            None if reason is None else (reason, "invented declared history")
        ),
    )
    return r.RecordYear(
        year,
        "nh",
        r.RecordKind.DISABILITY,
        (
            r.RETBeneficiary(
                "nh",
                (T.DIB,) * 12,
                {1},
                (gross,) + (F(0),) * 11,
                (pia,) * 12,
                fra_month=None,
            ),
        ),
        family_months={1: r.RETFamilyMonth(state, (), ssa_params(), {})},
    )


def _carryover_rib(pia, prior_widow_pia):
    """Exact 404.411(c)(2)(ii) rate: WIB at 60, own RIB at 64, cohort 1927."""
    return g.floor_dime(
        pia
        - prior_widow_pia * 24 * F(19, 4000)
        - (pia - prior_widow_pia) * F(12, 180)
    )


def _ordinary_rib(pia):
    return g.floor_dime(pia * F(168, 180))


def test_the_captures_carry_each_quoted_rule():
    drc = source_text("poms_rs_00615_712")
    for quote in (
        "In 3/00 the original rates would be $400 for the widow and $300 "
        "for the child.",
        "The child's original rate is $300.",
        "the child is protected by the savings clause and the child's rate "
        "will remain at $300.",
        "The MBR will show a PIA of $400.00",
    ):
        assert quote in drc
    assert (
        "Eliminated the additional reduction for the period between age 50 "
        "and age 60." in source_text("poms_rs_00615_005")
    )
    raw = (ARF_SOURCES / "ecfr_20cfr_404_411.xml").read_text()
    text = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", raw)))
    for quote in (
        "Individual born before January 2, 1928.",
        "except that the old-age benefit equals or exceeds the primary "
        "insurance amount on which the widow's or widower's benefit would "
        "be based.",
        "the old-age benefit is reduced by the larger of the following",
        "Individual born after January 1, 1928. The old-age benefit is "
        "reduced in accordance with § 404.410(a). There is no further "
        "reduction.",
        "the disability benefit is reduced by the amount by which the "
        "old-age benefit would be reduced",
    ):
        assert quote in text


@pytest.mark.parametrize("flag", [True, None])
@pytest.mark.parametrize("scale,original", [(100, "300.10"), (1, "3.10")])
def test_child_original_stays_settled_under_widow_drc_protection(
    flag, scale, original
):
    _assert_invalid(_published_widow_drc(flag, F(original), scale=scale))


@pytest.mark.parametrize(
    "flag,reason",
    [
        (True, UR.WIDOW_DRC_SAVINGS_CLAUSE),
        (None, UR.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN),
    ],
)
def test_published_child_rate_keeps_its_widow_drc_refusal(flag, reason):
    case = _published_widow_drc(flag, F(300))
    _assert_refusal(case, reason)
    _assert_preflight_neutral(case)


def test_a_child_condition_alone_leaves_the_child_original_settled():
    case = _published_widow_drc(False, F("300.10"))
    context = case.family_months[1]
    widow, child = context.beneficiaries
    case = replace(
        case,
        family_months={
            1: replace(
                context,
                beneficiaries=(
                    widow,
                    replace(child, conditions={BC.WIDOW_DRC_SAVINGS_CLAUSE}),
                ),
            )
        },
    )
    _assert_invalid(case)


def test_a_widow_drc_rate_stays_unsettled_for_the_widow_herself():
    """.712's widow has two original rates: $400, and $410 with DRCs."""
    case = _published_widow_drc(True, F(300))
    context = case.family_months[1]
    widow, child = context.beneficiaries
    unstated = replace(
        case,
        family_months={
            1: replace(
                context,
                beneficiaries=(
                    replace(widow, original_benefit_basis=None),
                    child,
                ),
            )
        },
    )
    _assert_refusal(unstated, UR.WIDOW_DRC_SAVINGS_CLAUSE)
    unknown = _published_widow_drc(None, F(300))
    person = unknown.beneficiaries[0]
    _assert_refusal(
        replace(
            unknown,
            beneficiaries=(
                replace(person, original_rates=(F(400),) * 12),
                unknown.beneficiaries[1],
            ),
        ),
        UR.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN,
    )


@pytest.mark.parametrize(
    "flag,reason",
    [
        (True, UR.WIDOW_DRC_SAVINGS_CLAUSE),
        (None, UR.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN),
    ],
)
def test_protected_cash_above_the_original_stays_a_named_refusal(flag, reason):
    """The capture states no cap on protected cash, so the row stays."""
    _assert_refusal(
        _published_widow_drc(flag, F(300), child_gross=F("300.10")),
        reason,
    )


def test_deduction_cap_stays_open_under_widow_drc_protection():
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(400),
        F(700),
        eligibility_year=1999,
        widow_drc_savings_clause=True,
    )
    child = g.Beneficiary("c", g.Role.CHILD)
    outcome = g.evaluate_family(
        "protected-cap",
        F(7),
        lambda: g.family_benefits_after_deductions(
            state,
            (child,),
            payment_month=g.YearMonth(2000, 1),
            params=ssa_params(),
            deductions={
                "c": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, F("300.10")
                )
            },
            households={"c": "h"},
            standalone=True,
        ),
    )
    assert not outcome.supported
    assert outcome.unsupported.reason is UR.WIDOW_DRC_SAVINGS_CLAUSE
    assert not g._fact_is_settled(
        "F4", state, child, params=ssa_params(), upper_bound=True
    )
    assert g._fact_is_settled("F4", state, child, params=ssa_params())


@pytest.mark.parametrize(
    "pia,prior,declared",
    [
        ("400", "300", "359.10"),
        ("1.20", ".50", "1.00"),
    ],
)
def test_published_rule_carryover_keeps_its_refusal(pia, prior, declared):
    pia, prior, declared = F(pia), F(prior), F(declared)
    assert _carryover_rib(pia, prior) == declared < _ordinary_rib(pia)
    # The own RIB exceeds the deceased PIA even in whole dollars, so no
    # current WIB or omitted auxiliary record explains the lower rate.
    assert declared // 1 >= prior
    case = _rib_record(pia, declared, reason=UR.DUAL_ENTITLEMENT_SEQUENCE)
    _assert_refusal(case, UR.DUAL_ENTITLEMENT_SEQUENCE)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize("reason", HISTORY_REASONS)
@pytest.mark.parametrize(
    "birth,settled", [(1926, False), (1927, False), (1928, True), (1929, True)]
)
def test_carryover_ends_at_cohort_1928(reason, birth, settled):
    case = _rib_record(F("1.20"), F(1), birth=birth, reason=reason)
    if settled:
        _assert_invalid(case)
    else:
        _assert_refusal(case, reason)


def test_an_unknown_cohort_cannot_rule_out_the_carryover():
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F("1.20"),
        F("1.80"),
        worker=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F("1.20"), reduction_months=12
        ),
        deferred_refusal=(UR.DUAL_ENTITLEMENT_SEQUENCE, "invented history"),
    )
    assert not g._fact_is_settled("F3", state, params=ssa_params())
    assert g._fact_is_settled(
        "F3", state, params=ssa_params(), upper_bound=True
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
def test_an_unknown_cohort_cannot_rule_out_a_pre_1978_history(reason):
    state = g.RecordState(
        g.FamilyKind.DISABILITY,
        F(4),
        F(6),
        deferred_refusal=(reason, "invented history"),
    )
    assert not g._fact_is_settled("F2", state, params=ssa_params())
    assert g._fact_is_settled(
        "F2", state, params=ssa_params(), upper_bound=True
    )


@pytest.mark.parametrize(
    "kind,settled",
    [(g.OwnBenefitKind.OLD_AGE, False), (g.OwnBenefitKind.DISABILITY, True)],
)
def test_the_carryover_reaches_only_an_old_age_benefit(kind, settled):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(4),
        F(8),
        eligibility_year=1989,
        widow_drc_savings_clause=False,
        deferred_refusal=(UR.DUAL_ENTITLEMENT_SEQUENCE, "invented history"),
    )
    widow = g.Beneficiary(
        "w",
        g.Role.WIDOW,
        birth_year=1927,
        child_in_care=False,
        own_benefit=g.OwnBenefit(kind, F(5)),
    )
    assert (
        g._fact_is_settled(
            "F6",
            state,
            widow,
            payment_month=g.YearMonth(2000, 1),
            beneficiaries=(widow,),
            params=ssa_params(),
        )
        is settled
    )


def test_a_zero_pia_leaves_no_rate_for_the_carryover_to_lower():
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(0),
        F(0),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(0), birth_year=1927),
        deferred_refusal=(UR.DUAL_ENTITLEMENT_SEQUENCE, "invented history"),
    )
    assert g._fact_is_settled("F3", state, params=ssa_params())


@pytest.mark.parametrize("reason", HISTORY_REASONS)
@pytest.mark.parametrize("gap", ["0.10", "1.00"])
def test_rib_above_the_canonical_rate_stays_an_input_error(reason, gap):
    pia = F(400)
    _assert_invalid(
        _rib_record(pia, _ordinary_rib(pia) + F(gap), reason=reason)
    )


@pytest.mark.parametrize("reason", HISTORY_REASONS)
def test_rib_at_the_canonical_rate_keeps_its_refusal(reason):
    pia = F(400)
    _assert_refusal(
        _rib_record(pia, _ordinary_rib(pia), reason=reason), reason
    )


def test_workers_compensation_caps_a_rib_at_its_canonical_rate():
    pia = F(400)
    conditions = {RC.WORKERS_COMPENSATION_OFFSET}
    ordinary = _ordinary_rib(pia)
    _assert_invalid(
        _rib_record(pia, ordinary + F(1, 10), conditions=conditions)
    )
    _assert_refusal(
        _rib_record(pia, ordinary - F(1), conditions=conditions),
        UR.WORKERS_COMPENSATION_OFFSET,
    )


@pytest.mark.parametrize(
    "conditions,reason",
    [
        ({RC.DIB_AFTER_REDUCED_RIB}, None),
        ({RC.WORKERS_COMPENSATION_OFFSET}, None),
        ((), UR.DIB_AFTER_REDUCED_RIB),
        ((), UR.WORKERS_COMPENSATION_OFFSET),
        ((), UR.DUAL_ENTITLEMENT_SEQUENCE),
        ((), UR.OWN_RIB_HISTORY_BEFORE_1978),
        ((), UR.REDUCED_BENEFIT_HISTORY_BEFORE_1978),
    ],
)
@pytest.mark.parametrize("pia", ["0.10", "4", "400"])
def test_a_reducing_hold_bounds_a_dib_at_its_pia(conditions, reason, pia):
    pia = F(pia)
    named = (
        reason
        if reason is not None
        else g._RECORD_CONDITION_REASONS[next(iter(conditions))][0]
    )
    above = _dib_record(
        pia, pia + F(1, 10), conditions=conditions, reason=reason
    )
    below = _dib_record(
        pia, pia - F(1, 10), conditions=conditions, reason=reason
    )
    _assert_invalid(above)
    _assert_refusal(below, named)
    _assert_preflight_neutral(below)
    _assert_refusal(
        _dib_record(pia, pia, conditions=conditions, reason=reason), named
    )


@pytest.mark.parametrize("reason", LOWERING_REASONS)
def test_finality_still_protects_a_rate_above_the_cap(reason):
    pia = F(4)
    _assert_refusal(
        _dib_record(
            pia,
            pia + F(1, 10),
            conditions={RC.ADMINISTRATIVE_FINALITY},
            reason=reason,
        ),
        UR.ADMINISTRATIVE_FINALITY,
    )


@pytest.mark.parametrize("reason", HISTORY_REASONS)
def test_finality_still_protects_a_rib_above_the_cap(reason):
    pia = F(400)
    _assert_refusal(
        _rib_record(
            pia,
            _ordinary_rib(pia) + F(1, 10),
            reason=reason,
            conditions={RC.ADMINISTRATIVE_FINALITY},
        ),
        UR.ADMINISTRATIVE_FINALITY,
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
@pytest.mark.parametrize(
    "birth,settled", [(1927, False), (1928, True), (1960, True)]
)
def test_pre_1978_history_reaches_only_cohorts_old_enough_for_it(
    reason, birth, settled
):
    pia = F(400)
    case = _dib_record(pia, pia - F(1), reason=reason, birth=birth)
    if settled:
        _assert_invalid(case)
    else:
        _assert_refusal(case, reason)


@pytest.mark.parametrize("reason", list(UR), ids=lambda reason: reason.value)
def test_each_reason_classifies_a_lower_dib(reason):
    pia = F(400)
    case = _dib_record(pia, pia - F(1), reason=reason)
    if reason in DIB_UNSETTLING_REASONS:
        _assert_refusal(case, reason)
    else:
        _assert_invalid(case)


@pytest.mark.parametrize("reason", list(UR), ids=lambda reason: reason.value)
def test_each_reason_classifies_a_lower_rib(reason):
    pia = F(400)
    case = _rib_record(pia, _ordinary_rib(pia) - F(1), reason=reason)
    if reason in RIB_UNSETTLING_REASONS:
        _assert_refusal(case, reason)
    else:
        _assert_invalid(case)


@pytest.mark.parametrize("reason", list(UR), ids=lambda reason: reason.value)
@pytest.mark.parametrize("kind", ["dib", "rib"])
def test_only_finality_lifts_an_nh_rate_cap(reason, kind):
    pia = F(400)
    case = (
        _dib_record(pia, pia + F(1, 10), reason=reason)
        if kind == "dib"
        else _rib_record(pia, _ordinary_rib(pia) + F(1, 10), reason=reason)
    )
    if reason is UR.ADMINISTRATIVE_FINALITY:
        _assert_refusal(case, reason)
    else:
        _assert_invalid(case)


@settings(max_examples=80, deadline=None)
@given(
    pia=st.integers(1, 9_000).map(lambda n: F(n, 10)),
    reason=st.sampled_from(LOWERING_REASONS),
    gap=st.integers(0, 40).map(lambda n: F(n, 10)),
)
@example(pia=F(1, 10), reason=UR.DUAL_ENTITLEMENT_SEQUENCE, gap=F(1, 10))
def test_every_dib_at_or_below_the_cap_keeps_its_row(pia, reason, gap):
    """Valid rates stay rows with the preflight's own reason; the rest error."""
    below = max(F(0), pia - gap)
    case = _dib_record(pia, below, reason=reason)
    _assert_refusal(case, reason)
    _assert_preflight_neutral(case)
    _assert_invalid(_dib_record(pia, pia + gap + F(1, 10), reason=reason))


@settings(max_examples=80, deadline=None)
@given(
    pia=st.integers(10, 9_000).map(lambda n: F(n, 10)),
    share=st.integers(1, 9),
    reason=st.sampled_from(HISTORY_REASONS),
)
@example(pia=F("1.20"), share=4, reason=UR.DUAL_ENTITLEMENT_SEQUENCE)
def test_every_carryover_rate_keeps_its_row(pia, share, reason):
    """Each rate 404.411(c)(2)(ii) can reach stays a counted refusal."""
    prior = g.floor_dime(pia * F(share, 10))
    lawful = _carryover_rib(pia, prior)
    ordinary = _ordinary_rib(pia)
    assert lawful <= ordinary
    case = _rib_record(pia, lawful, reason=reason)
    _assert_refusal(case, reason)
    _assert_preflight_neutral(case)
    _assert_invalid(_rib_record(pia, ordinary + F(1, 10), reason=reason))


@settings(max_examples=60, deadline=None)
@given(
    scale=st.integers(1, 40),
    gap=st.integers(1, 9).map(lambda n: F(n, 10)),
    flag=st.sampled_from((True, None)),
)
def test_every_child_original_mismatch_errors_under_widow_drc(
    scale, gap, flag
):
    _assert_invalid(
        _published_widow_drc(flag, F(3 * scale) + gap, scale=scale)
    )
