"""RET FRA facts: statutory conformance on invented declarations only.

No population, behavioral, or forecast claim. Act 203(f)(9) makes the RIB
FRA govern every section 202 benefit; a cohort identifies twelve possible
attainment months rather than a particular birthday.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import replace
from datetime import date, timedelta
from fractions import Fraction as F
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import BenefitType as T
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = load_ret_parameters()
DECLARATIONS = (None, *range(13))
# Independent statutory bands, not the implementation's parameter lookup.
COHORTS = (
    (1930, 780),
    (1937, 780),
    (1938, 782),
    (1939, 784),
    (1940, 786),
    (1941, 788),
    (1942, 790),
    (1943, 792),
    (1950, 792),
    (1954, 792),
    (1955, 794),
    (1956, 796),
    (1957, 798),
    (1958, 800),
    (1959, 802),
    (1960, 804),
    (1961, 804),
)


def _person(key, kind, rate, fra=None, *, estimated=False):
    work = r.WorkEarnings((F(22322),) + (F(0),) * 11)
    return r.RETBeneficiary(
        key,
        (kind,) * 12,
        {1},
        (F(rate),) + (F(0),) * 11,
        (F(rate),) * 12,
        fra_month=fra,
        **({"estimated_earnings": work} if estimated else {"earnings": work}),
    )


def _widow(
    fra=None, *, cohort=1950, estimated=False, fiscal=False, held_g=False
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(1),
        F(1),
        conditions=(
            {g.RecordCondition.ADMINISTRATIVE_FINALITY} if held_g else ()
        ),
        eligibility_year=2024,
        widow_drc_savings_clause=False,
    )
    member = g.Beneficiary("w", g.Role.WIDOW, birth_year=cohort)
    return r.RecordYear(
        2024,
        "nh",
        r.RecordKind.DECEASED,
        (_person("w", T.WIDOW, 1, fra, estimated=estimated),),
        fiscal_year=fiscal,
        family_months={
            1: r.RETFamilyMonth(state, (member,), ssa_params(), {"w": "h"})
        },
    )


def _facts(
    year, fra, cohort, *, nh=False, role=g.Role.WIDOW, month=1, own=None
):
    """Declare facts without calculating money or needing a parameter year."""
    if nh:
        state = g.RecordState(
            g.FamilyKind.RETIREMENT,
            own.pia if own else F(4),
            F(6),
            worker=own or g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(4)),
            worker_birth_year=cohort,
        )
        people = (_person("nh", T.RIB, 4, fra),)
        members = ()
        kind = r.RecordKind.RETIREMENT
    else:
        living = role in {
            g.Role.SPOUSE,
            g.Role.SPOUSE_CHILD_IN_CARE,
            g.Role.DIVORCED_SPOUSE,
        }
        state = g.RecordState(
            g.FamilyKind.RETIREMENT if living else g.FamilyKind.SURVIVOR,
            F(4),
            F(6),
            worker=(
                g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(4))
                if living
                else None
            ),
            widow_drc_savings_clause=False,
        )
        benefit_type = {
            g.Role.WIDOW: T.WIDOW,
            g.Role.SURVIVING_DIVORCED_SPOUSE: T.WIDOW,
            g.Role.DISABLED_WIDOW: T.DWB,
            g.Role.MOTHER_FATHER: T.MOTHER_FATHER,
            g.Role.CHILD: T.CHILD,
            g.Role.SPOUSE: T.SPOUSE,
            g.Role.SPOUSE_CHILD_IN_CARE: T.SPOUSE,
            g.Role.DIVORCED_SPOUSE: T.DIVORCED_SPOUSE,
        }[role]
        people = (_person("w", benefit_type, 1, fra),)
        if living:
            people += (_person("nh", T.RIB, 4),)
        members = (
            g.Beneficiary("w", role, birth_year=cohort, own_benefit=own),
        )
        kind = r.RecordKind.RETIREMENT if living else r.RecordKind.DECEASED
    people = tuple(
        replace(
            p,
            entitled_months={month},
            gross_rates=tuple(
                F(1) if m == month else F(0) for m in range(1, 13)
            ),
        )
        for p in people
    )
    return r.RecordYear(
        year,
        "nh",
        kind,
        people,
        family_months={
            month: r.RETFamilyMonth(
                state,
                members,
                ssa_params(),
                {b.beneficiary_id: "h" for b in members},
            )
        },
    )


def _spouse_case(fra=None, *, cohort=1950, estimated=False):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(4),
        F(6),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(4)),
        eligibility_year=2024,
    )
    members = (
        g.Beneficiary("s", g.Role.SPOUSE, birth_year=cohort),
        g.Beneficiary("c", g.Role.CHILD),
    )
    spouse = replace(
        _person("s", T.SPOUSE, 1, fra, estimated=estimated),
        original_rates=(F(2),) * 12,
    )
    people = (
        replace(_person("nh", T.RIB, 4), earnings=r.WorkEarnings()),
        spouse,
        replace(
            _person("c", T.CHILD, 1),
            earnings=r.WorkEarnings(),
            original_rates=(F(2),) * 12,
        ),
    )
    return r.RecordYear(
        2024,
        "nh",
        beneficiaries=people,
        family_maximum_binding_months={1},
        family_months={
            1: r.RETFamilyMonth(
                state, members, ssa_params(), {"s": "h", "c": "h"}
            )
        },
    )


def test_sole_widow_contradictory_fra_is_input_error_and_has_no_row():
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput, match="FRA"):
        outcomes.append(
            r.evaluate_ret(
                "aged", 3, lambda: r.apply_ret_year(_widow(), PARAMS)
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


def test_sole_widow_consistent_fra_has_no_own_deduction():
    result = r.apply_ret_year(_widow(0), PARAMS)
    january = next(row for row in result.months if row.month == 1)
    assert (january.net_due, january.payment, january.own_deduction) == (
        1,
        1,
        0,
    )


def test_spouse_counterexample_is_input_error_and_has_no_row():
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput, match="FRA"):
        outcomes.append(
            r.evaluate_ret(
                "aged", 3, lambda: r.apply_ret_year(_spouse_case(), PARAMS)
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize("cohort", [1930, 1950, 1957])
@pytest.mark.parametrize("fra", [None, 12])
@pytest.mark.parametrize("estimated", [False, True])
def test_old_cohort_cannot_be_overridden_by_actual_or_estimated_declaration(
    cohort, fra, estimated
):
    with pytest.raises(g.InvalidFamilyInput, match="FRA"):
        r.apply_ret_year(
            _spouse_case(fra, cohort=cohort, estimated=estimated), PARAMS
        )


@pytest.mark.parametrize("estimated", [False, True])
@pytest.mark.parametrize("held_g", [False, True])
def test_fra_contradiction_precedes_coverage_refusal(estimated, held_g):
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput, match="FRA"):
        outcomes.append(
            r.evaluate_ret(
                "aged",
                3,
                lambda: r.apply_ret_year(
                    _widow(estimated=estimated, fiscal=True, held_g=held_g),
                    PARAMS,
                ),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


def test_consistent_fra_keeps_named_coverage_refusal_in_denominator():
    outcome = r.evaluate_ret(
        "aged", 3, lambda: r.apply_ret_year(_widow(0, held_g=True), PARAMS)
    )
    assert (
        outcome.unsupported.reason
        is g.UnsupportedReason.ADMINISTRATIVE_FINALITY
    )
    denominator = g.count_family_outcomes([outcome])
    assert (denominator.rows, denominator.unsupported_weight) == (1, 3)


def _birthday_months(cohort, age_months):
    """Enumerate actual SSA-cohort birthdays and age-attainment dates."""
    birthday = date(cohort, 1, 2)
    result = set()
    while birthday <= date(cohort + 1, 1, 1):
        target = birthday.year * 12 + birthday.month - 1 + age_months
        # Month-end dates do not affect the endpoints; use the first and
        # second of every month to independently enumerate all months.
        if birthday.day in (1, 2):
            attained = date(
                target // 12, target % 12 + 1, birthday.day
            ) - timedelta(days=1)
            result.add(attained.year * 12 + attained.month - 1)
        birthday += timedelta(days=1)
    return result


def _accepted_months(year, months):
    return {
        0 if m < year * 12 else None if m >= (year + 1) * 12 else m % 12 + 1
        for m in months
    }


@pytest.mark.parametrize("cohort,age", COHORTS)
@pytest.mark.parametrize("nh", [False, True])
def test_every_cohort_interval_endpoint_and_every_inside_declaration(
    cohort, age, nh
):
    months = _birthday_months(cohort, age)
    assert (min(months), max(months)) == (
        cohort * 12 + age,
        cohort * 12 + age + 11,
    )
    for year in range(min(months) // 12 - 1, max(months) // 12 + 2):
        accepted = _accepted_months(year, months)
        for fra in DECLARATIONS:
            if fra in accepted:
                assert (
                    _facts(year, fra, cohort, nh=nh).beneficiaries[0].fra_month
                    == fra
                )
            else:
                with pytest.raises(g.InvalidFamilyInput, match="FRA"):
                    _facts(year, fra, cohort, nh=nh)


@settings(max_examples=65, deadline=None)
@given(
    st.sampled_from(COHORTS),
    st.integers(-1, 2),
    st.sampled_from(DECLARATIONS),
    st.booleans(),
)
def test_fra_classification_matches_independent_birthday_enumeration(
    cohort_age, offset, fra, nh
):
    cohort, age = cohort_age
    months = _birthday_months(cohort, age)
    year = min(months) // 12 + offset
    if fra in _accepted_months(year, months):
        assert (
            _facts(year, fra, cohort, nh=nh).beneficiaries[0].fra_month == fra
        )
    else:
        with pytest.raises(g.InvalidFamilyInput, match="FRA"):
            _facts(year, fra, cohort, nh=nh)


@pytest.mark.parametrize(
    "role",
    [
        g.Role.WIDOW,
        g.Role.SURVIVING_DIVORCED_SPOUSE,
        g.Role.DISABLED_WIDOW,
        g.Role.MOTHER_FATHER,
        g.Role.CHILD,
        g.Role.SPOUSE,
        g.Role.SPOUSE_CHILD_IN_CARE,
        g.Role.DIVORCED_SPOUSE,
    ],
)
def test_every_auxiliary_role_uses_rib_fra_not_widow_reduction_age(role):
    # 1957: RIB age 66y6m; WIB reduction FRA 66y2m. March 2023 is
    # possible only under the WIB reduction schedule and must error.
    with pytest.raises(g.InvalidFamilyInput, match="FRA"):
        _facts(2023, 3, 1957, role=role)
    assert _facts(2023, 7, 1957, role=role)


@pytest.mark.parametrize("nh", [False, True])
@pytest.mark.parametrize("fra", DECLARATIONS)
def test_missing_cohort_preserves_every_fra_declaration(nh, fra):
    assert _facts(2024, fra, None, nh=nh)


@pytest.mark.parametrize("nh", [False, True])
@pytest.mark.parametrize("fra", DECLARATIONS)
def test_own_delayed_credits_prove_only_fra_by_context_month(nh, fra):
    own = g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE,
        F(1),
        delayed_credit_months=1,
        birth_year=1957,
    )
    # July is the first possible FRA month. Applied credits prove FRA has
    # occurred by the September snapshot, without fixing a birthday.
    if fra is not None and fra <= 9 and fra >= 7:
        assert _facts(2023, fra, 1957, nh=nh, month=9, own=own)
    else:
        with pytest.raises(g.InvalidFamilyInput, match="FRA"):
            _facts(2023, fra, 1957, nh=nh, month=9, own=own)


def test_auxiliary_own_cohort_alone_constrains_fra():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1), birth_year=1950)
    with pytest.raises(g.InvalidFamilyInput, match="FRA"):
        _facts(2024, None, None, own=own)
    assert _facts(2024, 0, None, own=own)


def _paired_cohort_record(cohort, own_cohort, held_g):
    # FRA0 is valid for either old cohort on its own. Only the assertion
    # that one auxiliary has two different birth cohorts is impossible.
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1), birth_year=own_cohort)
    assert _facts(2024, 0, None, own=own)
    case = _facts(2024, 0, cohort)
    context = case.family_months[1]
    auxiliary = replace(context.beneficiaries[0], own_benefit=own)
    state = replace(
        context.state,
        conditions=(
            {g.RecordCondition.ADMINISTRATIVE_FINALITY} if held_g else ()
        ),
    )
    return replace(
        case,
        fiscal_year=True,
        family_months={
            1: replace(context, state=state, beneficiaries=(auxiliary,))
        },
    )


@pytest.mark.parametrize("held_g", [False, True])
def test_paired_auxiliary_birth_cohorts_error_at_declaration_before_refusal(
    held_g,
):
    # This tests the public declaration boundary itself, before G money
    # computation or either declared coverage condition is considered.
    with pytest.raises(
        g.InvalidFamilyInput,
        match="G own and beneficiary birth cohorts differ",
    ):
        _paired_cohort_record(1930, 1950, held_g)


@settings(max_examples=25, deadline=None)
@given(
    st.tuples(st.integers(1930, 1956), st.integers(1930, 1956)).filter(
        lambda pair: pair[0] != pair[1]
    ),
    st.booleans(),
)
def test_one_auxiliary_cannot_have_two_individually_post_fra_cohorts(
    pair, held_g
):
    with pytest.raises(
        g.InvalidFamilyInput,
        match="G own and beneficiary birth cohorts differ",
    ):
        _paired_cohort_record(*pair, held_g)


def test_unentitled_nh_still_retains_cohort_facts():
    case = _facts(2024, 0, 1950, nh=True)
    context = case.family_months[1]
    state = replace(
        context.state,
        worker=None,
        conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
    )
    person = replace(
        case.beneficiaries[0],
        entitled_months=(),
        gross_rates=(F(0),) * 12,
    )
    assert replace(
        case,
        beneficiaries=(person,),
        family_months={1: replace(context, state=state)},
    )
    with pytest.raises(g.InvalidFamilyInput, match="FRA"):
        replace(
            case,
            beneficiaries=(replace(person, fra_month=None),),
            family_months={1: replace(context, state=state)},
        )


def test_fra_facts_validate_once_per_public_ledger_call(monkeypatch):
    case = _widow(0)
    calls = []
    check = r._check_fra_facts

    def counted(*args):
        calls.append(args[0].beneficiary_id)
        return check(*args)

    monkeypatch.setattr(r, "_check_fra_facts", counted)
    r.apply_ret_year(case, PARAMS)
    assert calls == ["w"]


def test_reduction_months_and_deceased_worker_credits_do_not_prove_current_fra():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1), reduction_months=1)
    assert _facts(2024, None, None, nh=True, own=own)
    assert _facts(2024, 0, None, nh=True, own=own)
    # A survivor's deceased worker is a different person.
    case = _facts(2024, None, None)
    context = case.family_months[1]
    inherited = replace(context.beneficiaries[0], original_benefit_basis=F(5))
    assert (
        replace(
            case,
            family_months={1: replace(context, beneficiaries=(inherited,))},
        )
        .beneficiaries[0]
        .fra_month
        is None
    )


def test_fra_sources_are_hashed_and_role_rules_are_quoted():
    root = Path(__file__).with_name("data") / "track_b"
    quotes = {
        "ret_sources": {
            "ssa_act_203": "which is applicable in the case of old-age insurance benefits, regardless of whether or not the particular benefits"
        },
        "ret_ledger_sources": {
            "poms_rs_02501_021": "Always use the FRA for retirement insurance benefits (RIB) when applying the ET for RIB or widow(er)'s insurance benefits (WIB).",
            "ecfr_20cfr404_subpart_e": "full retirement age (as defined in § 404.409(a))",
        },
        "gross_benefit_sources": {
            "poms_rs_00615_003": "FRA for retirement or spouse's benefits is age 65.",
            "lii_usc_402_415": "after the month before the month in which such individual attained retirement age",
        },
    }
    for folder, rules in quotes.items():
        manifest = json.loads((root / folder / "manifest.json").read_text())
        for source_id, quote in rules.items():
            source = next(
                s for s in manifest["sources"] if s["id"] == source_id
            )
            raw = (root / folder / source["file"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == source["sha256"]
            plain = re.sub(r"<[^>]+>", " ", raw.decode())
            plain = " ".join(html.unescape(plain).replace("’", "'").split())
            assert quote in plain
