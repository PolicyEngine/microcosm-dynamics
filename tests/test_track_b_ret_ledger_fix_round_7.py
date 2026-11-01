"""Round 7: what a declared history reaches, and what age rules out.

Every record is invented or built from a captured SSA rule. Nothing here
admits a population, behavioral or forecast claim.
"""

from __future__ import annotations

import html
import re
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
UR = g.UnsupportedReason
ARF_SOURCES = Path(__file__).parent / "data/track_b/arf_recompute_sources"
RET_SOURCES = Path(__file__).parent / "data/track_b/ret_sources"
OWN_HISTORY = UR.OWN_RIB_HISTORY_BEFORE_1978
REDUCED_HISTORY = UR.REDUCED_BENEFIT_HISTORY_BEFORE_1978
DUAL = UR.DUAL_ENTITLEMENT_SEQUENCE
PRE_1978_REASONS = (OWN_HISTORY, REDUCED_HISTORY)
CARRYOVER_REASONS = (DUAL, REDUCED_HISTORY)
# Written out, not read from G: an edit to G's sets must fail here.
AMOUNT_TEST_ROLES = (
    g.Role.WIDOW,
    g.Role.SURVIVING_DIVORCED_SPOUSE,
    g.Role.DISABLED_WIDOW,
    g.Role.MOTHER_FATHER,
    g.Role.PARENT,
)
SPOUSE_ROLES = (g.Role.SPOUSE, g.Role.DIVORCED_SPOUSE)
# (conditions, deferred reason, the refusal it names)
PRIOR_REDUCED_HOLDS = (
    ({RC.DIB_AFTER_REDUCED_RIB}, None, UR.DIB_AFTER_REDUCED_RIB),
    ((), UR.DIB_AFTER_REDUCED_RIB, UR.DIB_AFTER_REDUCED_RIB),
    ((), DUAL, DUAL),
)
# None of these holds needs a prior reduced benefit.
AGE_FREE_HOLDS = (
    ({RC.WORKERS_COMPENSATION_OFFSET}, None, UR.WORKERS_COMPENSATION_OFFSET),
    ((), UR.WORKERS_COMPENSATION_OFFSET, UR.WORKERS_COMPENSATION_OFFSET),
    ({RC.ADMINISTRATIVE_FINALITY}, None, UR.ADMINISTRATIVE_FINALITY),
    ((), UR.ADMINISTRATIVE_FINALITY, UR.ADMINISTRATIVE_FINALITY),
)


def _outcome(case):
    return r.evaluate_ret(
        "round7", F(7), lambda: r.apply_ret_year(case, PARAMS)
    )


def _assert_refusal(case, reason):
    outcome = _outcome(case)
    assert not outcome.supported
    assert outcome.unsupported.reason is reason
    counts = r.count_ret_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


def _assert_invalid(case, match="G context does not match RET rates"):
    rows = []
    with pytest.raises(g.InvalidFamilyInput, match=match):
        rows.append(_outcome(case))
    counts = r.count_ret_outcomes(rows)
    assert (counts.rows, counts.weight) == (0, 0)


def _assert_preflight_neutral(case):
    actual = _outcome(case)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(r, "_check_settled_family_facts", lambda record: None)
        without = _outcome(case)
    assert not actual.supported and not without.supported
    assert actual.unsupported.reason is without.unsupported.reason
    assert actual.unsupported.detail == without.unsupported.detail
    assert r.count_ret_outcomes([actual]) == r.count_ret_outcomes([without])


def _deferred(reason):
    return None if reason is None else (reason, "invented declared history")


def _rib_record(
    pia, gross, *, reason=None, cohort=None, months=8, conditions=()
):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        g.floor_dime(pia * F(3, 2)),
        worker=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            pia,
            reduction_months=months,
            birth_year=cohort,
        ),
        worker_birth_year=cohort,
        conditions=conditions,
        deferred_refusal=_deferred(reason),
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


def _ordinary(pia, months=8):
    return g.floor_dime(pia * F(180 - months, 180))


def _dib_record(
    pia,
    gross,
    *,
    birth=1975,
    year=2024,
    month=1,
    conditions=(),
    reason=None,
    maximum=None,
    first=None,
):
    state = g.RecordState(
        g.FamilyKind.DISABILITY,
        pia,
        g.floor_dime(pia * F(3, 2)) if maximum is None else maximum,
        worker_birth_year=birth,
        eligibility_year=year - 1 if first is None else first.year,
        first_dib_entitlement=(
            g.YearMonth(year - 1, 1) if first is None else first
        ),
        conditions=conditions,
        deferred_refusal=_deferred(reason),
    )
    return r.RecordYear(
        year,
        "nh",
        r.RecordKind.DISABILITY,
        (
            r.RETBeneficiary(
                "nh",
                (T.DIB,) * 12,
                {month},
                tuple(gross if m == month else F(0) for m in range(1, 13)),
                (pia,) * 12,
                fra_month=None,
            ),
        ),
        family_months={month: r.RETFamilyMonth(state, (), ssa_params(), {})},
    )


def _mother_record(
    reason=DUAL,
    *,
    cohort=1919,
    pia=F(480),
    own=F(400),
    months=12,
    gross=F("0.90"),
    year=2000,
    eligibility=1990,
    maximum=None,
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        g.floor_dime(pia * F(3, 2)) if maximum is None else maximum,
        eligibility_year=eligibility,
        widow_drc_savings_clause=False,
        deferred_refusal=_deferred(reason),
    )
    members = (
        g.Beneficiary(
            "m",
            g.Role.MOTHER_FATHER,
            birth_year=cohort,
            own_benefit=g.OwnBenefit(
                g.OwnBenefitKind.OLD_AGE,
                own,
                reduction_months=months,
                birth_year=cohort,
            ),
        ),
        g.Beneficiary("c", g.Role.CHILD),
    )
    original = g.floor_dime(pia * F(3, 4))
    fra_month = 0 if year == 2000 else None
    return r.RecordYear(
        year,
        "nh",
        r.RecordKind.DECEASED,
        (
            r.RETBeneficiary(
                "m",
                (T.MOTHER_FATHER,) * 12,
                {1},
                (gross,) + (F(0),) * 11,
                (original,) * 12,
                fra_month=fra_month,
            ),
            r.RETBeneficiary(
                "c",
                (T.CDB,) * 12,
                {1},
                (original,) + (F(0),) * 11,
                (original,) * 12,
                fra_month=fra_month,
            ),
        ),
        family_months={
            1: r.RETFamilyMonth(
                state, members, ssa_params(), {"m": "h", "c": "h"}
            )
        },
    )


def _f2_settled(birth, year, month, *, conditions=(), reason=None):
    state = g.RecordState(
        g.FamilyKind.DISABILITY,
        F(400),
        F(600),
        worker_birth_year=birth,
        eligibility_year=year - 1,
        first_dib_entitlement=g.YearMonth(year - 1, 1),
        conditions=conditions,
        deferred_refusal=_deferred(reason),
    )
    return g._fact_is_settled(
        "F2",
        state,
        payment_month=g.YearMonth(year, month),
        params=ssa_params(),
    )


def _f6_settled(
    role, reason, cohort, *, pia=F(480), months=12, kind=None, own_pia=F(400)
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        g.floor_dime(pia * F(3, 2)),
        eligibility_year=1990,
        widow_drc_savings_clause=False,
        deferred_refusal=_deferred(reason),
    )
    member = g.Beneficiary(
        "m",
        role,
        birth_year=cohort,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE if kind is None else kind,
            own_pia,
            reduction_months=months,
            birth_year=cohort,
        ),
        own_benefit_first=True if role in SPOUSE_ROLES else None,
    )
    return g._fact_is_settled(
        "F6",
        state,
        member,
        payment_month=g.YearMonth(2000, 1),
        beneficiaries=(member,),
        params=ssa_params(),
    )


def _carried_rib(own, prior_pia):
    """404.411(c)(2)(ii): first WIB at 60, own RIB at 64, cohort 1927."""
    return g.floor_dime(
        own - prior_pia * 24 * F(19, 4000) - (own - prior_pia) * F(12, 180)
    )


def _money_history_rates(start_pia, months, final_pia):
    """Every dime path of RS 00615.005C.2's money reduction, as gross rates.

    The rate starts in December 1977 and takes each captured COLA through
    1999. Before June 1982 the MBA rounds up (RS 00615.101), so the money
    reduction rounds down, and each of the four PIA dimes can fall either
    way. From June 1982 the reduction rounds up. A January 2000 recomputation
    then applies the current money ratio to the new PIA.
    """
    raw = (RET_SOURCES / "ssa_cola_history.html").read_text()
    rows = re.findall(
        r"<tr><td[^>]*>(19[789]\d)(.*?)</td>\s*<td[^>]*>([\d.]+)</td>",
        raw,
        re.S,
    )
    colas = {int(year): int(F(rate) * 10) for year, _, rate in rows}
    rates = set()
    for path in range(16):
        pia = int(start_pia * 10)
        reduction = pia * months // 180
        for year in range(1978, 2000):
            raised = pia * (1000 + colas[year])
            upward = year < 1982 and path >> (year - 1978) & 1
            new_pia = (raised + 999) // 1000 if upward else raised // 1000
            scaled = new_pia * reduction
            reduction = (
                scaled // pia if year < 1982 else (scaled + pia - 1) // pia
            )
            pia = new_pia
        final = int(final_pia * 10)
        assert final > pia
        rates.add(F(final - (final * reduction + pia - 1) // pia, 10))
    return rates


def test_the_captures_carry_each_quoted_rule():
    assert (
        "DIB is not reduced unless there was prior entitlement to reduced "
        "RIB (or WIB prior to 1/90)." in source_text("poms_rs_00615_010")
    )
    reduced = source_text("poms_rs_00615_005")
    for quote in (
        "Provided for reduced disabled widow's benefits at ages 50-59",
        "Provided for the payment of reduced retirement, reduced spouse's "
        "and unreduced widow's benefits to women at age 62.",
        "Provided for reduced widow's benefits beginning at age 60.",
    ):
        assert quote in reduced
    raw = (ARF_SOURCES / "ecfr_20cfr_404_411.xml").read_text()
    text = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", raw)))
    for quote in (
        "the old-age benefit is reduced by the larger of the following",
        "A person's disability benefit is reduced following entitlement to "
        "an old-age or widow's or widower's benefit",
    ):
        assert quote in text


@pytest.mark.parametrize(
    "start,months,final,rate,ordinary",
    [
        ("123.40", 8, "333.30", "318.50", "318.40"),
        ("251.30", 2, "1000", "988.90", "988.80"),
    ],
)
def test_money_history_lands_above_todays_formula_on_every_path(
    start, months, final, rate, ordinary
):
    assert _money_history_rates(F(start), months, F(final)) == {F(rate)}
    assert _ordinary(F(final), months) == F(ordinary)


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
@pytest.mark.parametrize(
    "pia,gross,months",
    [("333.30", "318.50", 8), ("1000", "988.90", 2)],
)
def test_declared_history_keeps_a_rate_above_todays_formula(
    reason, pia, gross, months
):
    case = _rib_record(F(pia), F(gross), reason=reason, months=months)
    _assert_refusal(case, reason)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize("cohort", [None, 1913, 1915])
@pytest.mark.parametrize("reason", PRE_1978_REASONS)
@pytest.mark.parametrize("gap", ["-1.00", "-0.10", "0", "0.10", "1.00"])
def test_a_history_reaching_rib_keeps_either_direction(reason, cohort, gap):
    pia = F("333.30")
    gross = _ordinary(pia) + F(gap)
    _assert_refusal(
        _rib_record(pia, gross, reason=reason, cohort=cohort), reason
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
@pytest.mark.parametrize("cohort", [1916, 1920, 1927])
def test_a_cohort_past_1915_keeps_todays_formula_as_a_cap(reason, cohort):
    pia = F("333.30")
    _assert_invalid(
        _rib_record(
            pia, _ordinary(pia) + F(1, 10), reason=reason, cohort=cohort
        )
    )


@pytest.mark.parametrize("cohort", [1916, 1927])
def test_a_cohort_past_1915_keeps_exact_own_history(cohort):
    pia = F("333.30")
    _assert_invalid(
        _rib_record(
            pia, _ordinary(pia) - F(1, 10), reason=OWN_HISTORY, cohort=cohort
        )
    )
    _assert_refusal(
        _rib_record(
            pia,
            _ordinary(pia) - F(1, 10),
            reason=REDUCED_HISTORY,
            cohort=cohort,
        ),
        REDUCED_HISTORY,
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
def test_no_remaining_reduction_needs_no_money_history(reason):
    pia = F("333.30")
    _assert_invalid(_rib_record(pia, pia + F(1, 10), reason=reason, months=0))


@pytest.mark.parametrize(
    "conditions,reason",
    [
        ((), None),
        ((), DUAL),
        ((), UR.WORKERS_COMPENSATION_OFFSET),
        ({RC.WORKERS_COMPENSATION_OFFSET}, None),
    ],
)
def test_only_a_declared_history_reaches_past_an_omitted_cohort(
    conditions, reason
):
    pia = F("333.30")
    _assert_invalid(
        _rib_record(
            pia,
            _ordinary(pia) + F(1, 10),
            conditions=conditions,
            reason=reason,
        )
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
def test_finality_still_lifts_the_cap_past_the_history_scope(reason):
    pia = F("333.30")
    _assert_refusal(
        _rib_record(
            pia,
            _ordinary(pia) + F(1, 10),
            conditions={RC.ADMINISTRATIVE_FINALITY},
            reason=reason,
            cohort=1920,
        ),
        UR.ADMINISTRATIVE_FINALITY,
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
@pytest.mark.parametrize("birth", [None, 1927])
def test_history_leaves_a_dib_cap_alone(reason, birth):
    _assert_invalid(
        _dib_record(
            F(1000), F("1000.10"), birth=birth, year=1985, reason=reason
        )
    )


@given(
    pia=st.integers(10, 30_000).map(lambda n: F(n, 10)),
    months=st.integers(1, 36),
    cohort=st.sampled_from((None, 1900, 1913, 1915)),
    reason=st.sampled_from(PRE_1978_REASONS),
    gap=st.integers(-40, 40).map(lambda n: F(n, 10)),
)
@example(
    pia=F("333.30"), months=8, cohort=None, reason=OWN_HISTORY, gap=F(1, 10)
)
@settings(max_examples=150, deadline=None)
def test_history_keeps_every_rate_in_its_scope(
    pia, months, cohort, reason, gap
):
    gross = max(F(0), _ordinary(pia, months) + gap)
    _assert_refusal(
        _rib_record(pia, gross, reason=reason, cohort=cohort, months=months),
        reason,
    )


@given(
    pia=st.integers(10, 30_000).map(lambda n: F(n, 10)),
    months=st.integers(0, 36),
    cohort=st.integers(1916, 1927),
    reason=st.sampled_from(PRE_1978_REASONS + (DUAL,)),
    gap=st.integers(1, 40).map(lambda n: F(n, 10)),
)
@settings(max_examples=150, deadline=None)
def test_past_1915_every_reduction_only_hold_keeps_the_cap(
    pia, months, cohort, reason, gap
):
    _assert_invalid(
        _rib_record(
            pia,
            _ordinary(pia, months) + gap,
            reason=reason,
            cohort=cohort,
            months=months,
        )
    )


@pytest.mark.parametrize(
    "pia,own,prior,carried,ordinary,original",
    [
        ("480", "400", "300", "359.10", "373.30", "360"),
        ("1.20", "1", "0.80", "0.80", "0.90", "0.90"),
    ],
)
def test_a_mothers_carried_rib_passes_where_the_ordinary_one_fails(
    pia, own, prior, carried, ordinary, original
):
    pia, own, prior = F(pia), F(own), F(prior)
    assert _carried_rib(own, prior) == F(carried) < F(original)
    assert _ordinary(own, 12) == F(ordinary) >= F(original)
    assert g.floor_dime(pia * F(3, 4)) == F(original)
    case = _mother_record(pia=pia, own=own, gross=F(original) - F(carried))
    _assert_refusal(case, DUAL)
    _assert_preflight_neutral(case)


def test_a_pre_fra_mother_keeps_the_historical_year_row():
    case = _mother_record(
        cohort=1919,
        year=1983,
        eligibility=1983,
        maximum=g.retirement_survivor_family_maximum(
            F(480), 1983, ssa_params()
        ),
    )
    _assert_refusal(case, DUAL)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize(
    "reason,cohort,kept",
    [
        (DUAL, None, DUAL),
        (DUAL, 1919, DUAL),
        (DUAL, 1927, DUAL),
        (DUAL, 1928, None),
        (REDUCED_HISTORY, None, REDUCED_HISTORY),
        (REDUCED_HISTORY, 1919, REDUCED_HISTORY),
        (REDUCED_HISTORY, 1927, REDUCED_HISTORY),
        (REDUCED_HISTORY, 1928, None),
        (OWN_HISTORY, None, OWN_HISTORY),
        (OWN_HISTORY, 1915, OWN_HISTORY),
        (OWN_HISTORY, 1916, None),
        (OWN_HISTORY, 1927, None),
    ],
)
def test_a_mothers_own_rib_opens_only_in_each_holds_scope(
    reason, cohort, kept
):
    case = _mother_record(reason, cohort=cohort)
    if kept is None:
        _assert_invalid(case, "auxiliary entitlement facts differ")
    else:
        _assert_refusal(case, kept)


@pytest.mark.parametrize("reason", (DUAL, REDUCED_HISTORY, OWN_HISTORY))
def test_a_zero_pia_fails_every_rib_on_every_filling(reason):
    _assert_invalid(
        _mother_record(reason, cohort=None, pia=F(0), gross=F(0)),
        "auxiliary entitlement facts differ",
    )


@pytest.mark.parametrize("role", AMOUNT_TEST_ROLES)
@pytest.mark.parametrize("reason", CARRYOVER_REASONS)
@pytest.mark.parametrize("cohort,settled", [(1920, False), (1928, True)])
def test_every_actual_rib_test_shares_the_carryover(
    role, reason, cohort, settled
):
    assert _f6_settled(role, reason, cohort, months=0) is settled


@pytest.mark.parametrize(
    "role", (g.Role.CHILD, g.Role.SPOUSE, g.Role.DIVORCED_SPOUSE)
)
@pytest.mark.parametrize("reason", CARRYOVER_REASONS)
def test_a_role_with_no_rib_amount_test_stays_settled(role, reason):
    assert _f6_settled(role, reason, 1920, months=0) is True


@pytest.mark.parametrize("role", (g.Role.MOTHER_FATHER, g.Role.PARENT))
@pytest.mark.parametrize("reason", CARRYOVER_REASONS)
def test_a_disability_own_benefit_faces_no_rib_amount_test(role, reason):
    assert (
        _f6_settled(
            role, reason, 1920, months=0, kind=g.OwnBenefitKind.DISABILITY
        )
        is True
    )


def test_a_reduced_dib_opens_no_money_history():
    assert (
        _f6_settled(
            g.Role.MOTHER_FATHER,
            REDUCED_HISTORY,
            1913,
            kind=g.OwnBenefitKind.DISABILITY,
        )
        is True
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
def test_a_zero_own_pia_leaves_no_money_history(reason):
    assert (
        _f6_settled(g.Role.MOTHER_FATHER, reason, None, own_pia=F(0)) is True
    )


def test_a_deemed_pia_keeps_a_history_open_on_a_zero_record_pia():
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(0),
        F(0),
        eligibility_year=1990,
        widow_drc_savings_clause=False,
        deferred_refusal=_deferred(OWN_HISTORY),
    )
    member = g.Beneficiary(
        "w",
        g.Role.DISABLED_WIDOW,
        original_benefit_basis=F(100),
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F(400), reduction_months=12
        ),
    )
    assert g._hold_unsettles_fact(
        OWN_HISTORY,
        "F6",
        state,
        member,
        payment_month=g.YearMonth(2000, 1),
        beneficiaries=(member,),
        params=ssa_params(),
    )


@given(
    role=st.sampled_from(
        (g.Role.MOTHER_FATHER, g.Role.PARENT, g.Role.CHILD, g.Role.SPOUSE)
    ),
    reason=st.sampled_from(CARRYOVER_REASONS + (OWN_HISTORY,)),
    cohort=st.one_of(st.none(), st.integers(1905, 1935)),
    months=st.integers(0, 24),
    pia=st.sampled_from((F(0), F("0.10"), F(480))),
)
@example(
    role=g.Role.MOTHER_FATHER,
    reason=OWN_HISTORY,
    cohort=None,
    months=1,
    pia=F(480),
)
@settings(max_examples=250, deadline=None)
def test_f6_matches_a_table_written_from_the_sources(
    role, reason, cohort, months, pia
):
    money_history = (
        reason in PRE_1978_REASONS
        and months > 0
        and (cohort is None or cohort < 1916)
    )
    carryover = (
        reason in CARRYOVER_REASONS
        and role in (g.Role.MOTHER_FATHER, g.Role.PARENT)
        and (cohort is None or cohort < 1928)
    )
    # A known cohort refuses its own history whatever the record declares.
    implicit_history = months > 0 and cohort is not None and cohort < 1916
    expected_open = implicit_history or (
        pia > 0 and (money_history or carryover)
    )
    settled = _f6_settled(role, reason, cohort, months=months, pia=pia)
    assert settled is not expected_open


def test_a_cohort_too_young_for_any_reduced_benefit_has_one_dib_rate():
    case = _dib_record(
        F(405),
        F("404.90"),
        birth=1975,
        year=2024,
        reason=DUAL,
        maximum=F(405),
        first=g.YearMonth(2024, 1),
    )
    _assert_invalid(case)


@pytest.mark.parametrize("conditions,reason,named", PRIOR_REDUCED_HOLDS)
@pytest.mark.parametrize("birth", [1975, 1980, 2000])
def test_before_age_50_a_dib_below_the_pia_raises(
    conditions, reason, named, birth
):
    pia = F(405)
    _assert_invalid(
        _dib_record(
            pia,
            pia - F(1, 10),
            birth=birth,
            conditions=conditions,
            reason=reason,
        )
    )
    _assert_invalid(
        _dib_record(
            pia,
            pia + F(1, 10),
            birth=birth,
            conditions=conditions,
            reason=reason,
        )
    )
    _assert_refusal(
        _dib_record(
            pia, pia, birth=birth, conditions=conditions, reason=reason
        ),
        named,
    )


@pytest.mark.parametrize("conditions,reason,named", PRIOR_REDUCED_HOLDS)
@pytest.mark.parametrize(
    "birth,year,month,keeps",
    [
        (1974, 2023, 12, False),
        (1974, 2024, 1, True),
        (1973, 2023, 12, True),
        (1960, 2024, 1, True),
        (None, 2024, 1, True),
    ],
)
def test_the_floor_opens_in_january_of_the_year_a_cohort_turns_50(
    conditions, reason, named, birth, year, month, keeps
):
    pia = F(405)
    case = _dib_record(
        pia,
        pia - F(1, 10),
        birth=birth,
        year=year,
        month=month,
        conditions=conditions,
        reason=reason,
    )
    if keeps:
        _assert_refusal(case, named)
        _assert_preflight_neutral(case)
    else:
        _assert_invalid(case)


@pytest.mark.parametrize("conditions,reason,named", AGE_FREE_HOLDS)
@pytest.mark.parametrize("birth", [1975, 2000])
def test_a_hold_no_age_limits_keeps_a_young_row(
    conditions, reason, named, birth
):
    pia = F(405)
    case = _dib_record(
        pia,
        pia - F(1, 10),
        birth=birth,
        conditions=conditions,
        reason=reason,
    )
    _assert_refusal(case, named)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize(
    "conditions,named",
    [
        ({RC.WORKERS_COMPENSATION_OFFSET}, UR.WORKERS_COMPENSATION_OFFSET),
        ({RC.ADMINISTRATIVE_FINALITY}, UR.ADMINISTRATIVE_FINALITY),
    ],
)
def test_an_independent_hold_survives_a_young_dual_declaration(
    conditions, named
):
    pia = F(405)
    case = _dib_record(pia, pia - F(1, 10), conditions=conditions, reason=DUAL)
    _assert_refusal(case, named)


def test_the_floor_needs_a_cohort_and_a_month():
    assert not _f2_settled(None, 2024, 1, reason=DUAL)
    state = g.RecordState(
        g.FamilyKind.DISABILITY,
        F(400),
        F(600),
        worker_birth_year=1990,
        eligibility_year=2020,
        first_dib_entitlement=g.YearMonth(2020, 1),
        deferred_refusal=_deferred(DUAL),
    )
    assert not g._fact_is_settled("F2", state, params=ssa_params())


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
@pytest.mark.parametrize(
    "birth,year,month,settled",
    [
        (1927, 1976, 12, True),
        (1927, 1977, 1, False),
        (1926, 1976, 12, False),
        (1928, 1990, 1, True),
    ],
)
def test_a_pre_1978_hold_needs_both_the_cohort_and_the_age(
    reason, birth, year, month, settled
):
    assert _f2_settled(birth, year, month, reason=reason) is settled


@given(
    birth=st.integers(1900, 2005),
    year=st.integers(1984, 2030),
    month=st.integers(1, 12),
    hold=st.sampled_from(
        (
            RC.DIB_AFTER_REDUCED_RIB,
            UR.DIB_AFTER_REDUCED_RIB,
            DUAL,
            OWN_HISTORY,
            REDUCED_HISTORY,
            RC.WORKERS_COMPENSATION_OFFSET,
            UR.WORKERS_COMPENSATION_OFFSET,
            RC.ADMINISTRATIVE_FINALITY,
        )
    ),
)
@example(birth=1974, year=2023, month=12, hold=DUAL)
@example(birth=1974, year=2024, month=1, hold=DUAL)
@settings(max_examples=250, deadline=None)
def test_f2_matches_a_table_written_from_the_sources(birth, year, month, hold):
    if hold in (
        RC.WORKERS_COMPENSATION_OFFSET,
        UR.WORKERS_COMPENSATION_OFFSET,
        RC.ADMINISTRATIVE_FINALITY,
    ):
        expected_open = True
    else:
        expected_open = year >= birth + 50
        if hold in PRE_1978_REASONS:
            expected_open = expected_open and birth < 1928
    conditions, reason = ({hold}, None) if isinstance(hold, RC) else ((), hold)
    settled = _f2_settled(
        birth, year, month, conditions=conditions, reason=reason
    )
    assert settled is not expected_open


@given(
    pia=st.integers(2, 30_000).map(lambda n: F(n, 10)),
    gap=st.integers(0, 40).map(lambda n: F(n, 10)),
    birth=st.integers(1975, 2003),
    hold=st.sampled_from(PRIOR_REDUCED_HOLDS),
)
@settings(max_examples=120, deadline=None)
def test_a_young_dib_rate_equals_its_pia_or_raises(pia, gap, birth, hold):
    conditions, reason, named = hold
    case = _dib_record(
        pia,
        max(F(0), pia - gap),
        birth=birth,
        conditions=conditions,
        reason=reason,
    )
    if gap == 0:
        _assert_refusal(case, named)
    else:
        _assert_invalid(case)
