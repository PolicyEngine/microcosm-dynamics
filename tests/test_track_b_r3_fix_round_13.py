"""Statutory conformance: invented adversarial R2/R3 boundary cases only.

No population, behavioral, or forecast claim is admitted.
"""

import pickle
from dataclasses import fields, replace
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import recompute as c
from populace_dynamics.track_b import ret_grace as grace
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b._provenance import _computed, _result_values
from tests.test_track_b_r3_provenance import (
    PARAMS,
    arf_result,
    recomputation_result,
)
from tests.test_track_b_ret_ledger import PARAMS as RET_PARAMS
from tests.test_track_b_ret_ledger import beneficiary, record


def test_ret_negative_gross_is_input_error_before_foreign_work_refusal():
    member = r.RETBeneficiary(
        "nh",
        (r.BenefitType.RIB,) * 12,
        frozenset(range(1, 13)),
        (F(0),) * 12,
        (F(0),) * 12,
    )
    case = r.RecordYear(2026, "nh", beneficiaries=(member,), foreign_work=True)
    object.__setattr__(
        case.beneficiaries[0], "gross_rates", (F(-1, 10),) + (F(0),) * 11
    )
    with pytest.raises(g.InvalidFamilyInput):
        r.evaluate_ret("case", 1, lambda: r.apply_ret_year(case, RET_PARAMS))


def test_arf_1959_1960_pickle_patch_is_blocked_at_serialization():
    result = arf_result()
    assert result.claim.birth_date == date(1960, 1, 2)
    assert result.fra_month == g.YearMonth(2027, 1)
    assert result.benefit == 910
    fresh_1959 = a.apply_arf(
        replace(result.claim, birth_date=date(1959, 1, 2)),
        payment_month=g.YearMonth(2027, 1),
        params=PARAMS,
    )
    assert fresh_1959.fra_month == g.YearMonth(2025, 11)
    assert fresh_1959.adjusted_reduction_months == 46
    assert fresh_1959.benefit == F("985.8")
    assert fresh_1959.whole_dollar_benefit == 985
    with pytest.raises(g.InvalidFamilyInput):
        serialized = pickle.dumps(result, protocol=0)
        # The reviewer's public-byte attack must be unreachable.
        patched = serialized.replace(b"\x07\xa8\x01\x02", b"\x07\xa7\x01\x02")
        restored = pickle.loads(patched)
        a.evaluate_arf("restored", 1, lambda: restored)


class MutableFraction(F):
    def __radd__(self, other):
        return other + self.value

    def __mul__(self, other):
        return self.value * other


@pytest.mark.parametrize(
    "evaluator,factory",
    [
        (a.evaluate_arf, arf_result),
        (c.evaluate_recomputation, recomputation_result),
    ],
)
def test_r3_mutable_fraction_weight_is_rejected_or_detached(
    evaluator, factory
):
    weight = MutableFraction(1)
    weight.value = F(1)
    try:
        row = evaluator("weight", weight, factory)
    except g.InvalidFamilyInput:
        return
    before = g.count_family_outcomes([row])
    weight.value = F(0)
    assert type(row.weight) is F
    assert g.count_family_outcomes([row]) == before


# Every declared field is attacked after normal construction. The consumer
# may rebuild it or reject it, but coverage must never hide the input error.


def claim():
    return a.ARFClaim(
        a.ARFBenefitKind.RIB, date(1960, 1, 2), g.YearMonth(2022, 1), F(1300)
    )


def basis():
    return c.RecomputationBasis(
        2020, 2018, 35, (960, 5785), g.YearMonth(2020, 6)
    )


def recompute(value):
    return c.annual_recomputation(
        value, dict.fromkeys(range(1951, 2021), 0), 2020, 0, PARAMS, {2020: 0}
    )


def grace_case():
    return grace.GraceMonth(
        {grace.BenefitType.RIB}, {grace.BenefitType.RIB}, True
    )


def mutation_cases():
    cases = []

    def add(label, factory, consumer, values):
        assert set(values) == {field.name for field in fields(factory())}
        cases.extend(
            (f"{label}.{field}", factory, consumer, field, invalid)
            for field, invalid in values.items()
        )

    add(
        "record",
        lambda: record(beneficiary(), foreign_work=True),
        lambda value: r.apply_ret_year(value, RET_PARAMS),
        {
            "year": 0,
            "nh_id": "",
            "kind": "retirement",
            "beneficiaries": (),
            "family_maximum_binding_months": {13},
            "other_deduction_months": {0},
            "fiscal_year": 1,
            "short_taxable_year": 1,
            "suspension_method": "full_month",
            "foreign_work": 1,
            "vocational_rehabilitation_refusal": 1,
        },
    )
    add(
        "beneficiary",
        beneficiary,
        lambda value: r.apply_ret_year(
            record(value, foreign_work=True), RET_PARAMS
        ),
        {
            "beneficiary_id": "",
            "benefit_types": ("rib",) * 12,
            "entitled_months": {13},
            "gross_rates": (F(-1, 10),) * 12,
            "original_rates": (F(-1, 10),) * 12,
            "earnings": None,
            "estimated_earnings": object(),
            "fra_month": 13,
            "grace": object(),
            "estimated_grace": object(),
            "divorced_months": {1},
            "nh_entitled_before_divorce": 1,
            "deemed_entitled": 1,
            "deemed_married_to_nh": 1,
            "deemed_child_age_18_months": {13},
            "death_month": 0,
            "own_work_exempt_months": {1},
            "two_record_entitlement": 1,
        },
    )
    add(
        "work",
        r.WorkEarnings,
        lambda value: r.countable_earnings(value, 0),
        {
            "wages": (F(-1),) * 12,
            "nese": "nan",
            "self_employment_months": {0},
            "substantial_service_months": {1},
        },
    )
    add(
        "state",
        grace.GraceYearState,
        lambda value: grace.grace_year(2026, value, [grace_case()] * 12),
        {
            "last_met_year": 2025,
            "previous_entitled_types": {"rib"},
            "had_entitlement": 1,
            "gap_since_entitlement": 1,
            "pending_after_break": 1,
            "last_processed_year": 0,
            "previous_section_202_types": {"rib"},
            "gap_since_section_202": 1,
        },
    )
    add(
        "month",
        grace_case,
        lambda value: grace.grace_year(
            2026, grace.GraceYearState(), [value] * 12
        ),
        {
            "entitled_types": {"rib"},
            "received_types": {"rib"},
            "nonservice": 1,
        },
    )
    add(
        "termination",
        lambda: grace.TerminationEvent(12, grace.BenefitType.RIB),
        lambda value: grace.grace_year(
            2026,
            grace.GraceYearState(),
            [grace_case()] * 12,
            termination_events=[value],
        ),
        {
            "last_entitled_month": 0,
            "benefit_type": "rib",
            "young_spouse": 1,
            "reason": "normal",
        },
    )
    values = {
        field.name: [(0, 1)]
        for field in fields(claim())
        if field.name.endswith("_months")
    }
    values.update(
        kind="rib",
        birth_date="1960-01-02",
        first_reduction_month=(0, 1),
        unreduced_benefit=-1,
        death_date=date(1959, 1, 1),
        spouse_own=object(),
        conditions=["unknown"],
    )
    add(
        "claim",
        claim,
        lambda value: a.apply_arf(
            value, payment_month=(2027, 1), params=PARAMS
        ),
        values,
    )
    add(
        "own",
        lambda: a.SpouseOwnBenefit(
            F(1), F(1), a.SpouseOwnSequence.CONCURRENT_OR_PRECEDING
        ),
        lambda value: a.apply_arf(
            replace(
                claim(),
                kind=a.ARFBenefitKind.SPOUSE,
                spouse_own=value,
                conditions={a.ARFUnsupportedReason.OTHER_SUSPENSION},
            ),
            payment_month=(2027, 1),
            params=PARAMS,
        ),
        {
            "pia": -1,
            "payable": -1,
            "sequence": "concurrent_or_preceding",
        },
    )
    add(
        "basis",
        basis,
        recompute,
        {
            "eligibility_year": 0,
            "indexing_year": 0,
            "computation_years": 0,
            "bend_points": (0, 0),
            "entitlement_month": g.YearMonth(1900, 1),
            "first_base_year": 1950,
            "entitlement_end_month": g.YearMonth(1900, 1),
            "formula": "aime",
            "conditions": {"unknown"},
        },
    )
    return cases


MUTATION_CASES = mutation_cases()


@pytest.mark.parametrize(
    "label,factory,consumer,field,invalid",
    MUTATION_CASES,
    ids=[case[0] for case in MUTATION_CASES],
)
def test_every_r2_r3_declared_field_is_revalidated(
    label, factory, consumer, field, invalid
):
    value = factory()
    object.__setattr__(value, field, invalid)
    with pytest.raises(g.InvalidFamilyInput):
        consumer(value)


@given(st.sampled_from(MUTATION_CASES), st.booleans())
@settings(max_examples=90, deadline=None)
def test_declared_tree_errors_never_become_coverage_rows(case, wrap):
    _, factory, consumer, field, invalid = case
    value = factory()
    object.__setattr__(value, field, invalid)
    with pytest.raises(g.InvalidFamilyInput):
        if wrap:
            g.evaluate_family("invalid", 1, lambda: consumer(value))
        else:
            consumer(value)


@given(st.integers(0, 10000))
@settings(max_examples=20, deadline=None)
def test_valid_planted_r2_r3_values_match_fresh_declarations(amount):
    member = beneficiary()
    rates = (F(amount),) * 12
    object.__setattr__(member, "gross_rates", rates)
    object.__setattr__(member, "original_rates", rates)
    assert r.apply_ret_year(record(member), RET_PARAMS) == r.apply_ret_year(
        record(beneficiary(rate=amount)), RET_PARAMS
    )
    source = claim()
    object.__setattr__(source, "unreduced_benefit", F(amount))
    fresh = replace(claim(), unreduced_benefit=F(amount))
    assert a.apply_arf(
        source, payment_month=(2027, 1), params=PARAMS
    ) == a.apply_arf(fresh, payment_month=(2027, 1), params=PARAMS)


class MutableInt(int):
    pass


class MutableDecimal(Decimal):
    pass


@pytest.mark.parametrize("kind", [MutableInt, MutableFraction, MutableDecimal])
@pytest.mark.parametrize(
    "consumer",
    [
        lambda value: r.WorkEarnings(wages=(value,) * 12),
        lambda value: r.WorkEarnings(nese=value, self_employment_months={1}),
        lambda value: r.calculated_excess(value, 0, F(1, 2)),
        lambda value: r.calculated_excess(1, value, F(1, 2)),
        lambda value: r.partial_payments(value, {"nh": 1}, {"nh": 1}),
        lambda value: r.partial_payments(1, {"nh": value}, {"nh": 1}),
        lambda value: r.partial_payments(1, {"nh": 1}, {"nh": value}),
        lambda value: a.ARFClaim(
            a.ARFBenefitKind.RIB, date(1960, 1, 2), (2022, 1), value
        ),
        lambda value: a.SpouseOwnBenefit(
            value, F(1), a.SpouseOwnSequence.CONCURRENT_OR_PRECEDING
        ),
        lambda value: c.recomputation_decision(value, 2),
        lambda value: c.recomputation_decision(1, value),
    ],
)
def test_r2_r3_numeric_subclasses_never_enter_declared_or_computed_fields(
    kind, consumer
):
    with pytest.raises(g.InvalidFamilyInput):
        consumer(kind(1))


@given(st.integers(0, 10000))
@settings(max_examples=20, deadline=None)
def test_ret_beneficiary_accessor_returns_detached_sealed_rows(amount):
    result = r.apply_ret_year(record(beneficiary(rate=amount)), RET_PARAMS)
    first = result.for_beneficiary("nh")
    second = result.for_beneficiary("nh")
    assert first == second
    assert all(
        left is not right for left, right in zip(first, second, strict=True)
    )
    object.__setattr__(first[0], "payment", 9999)
    assert result.for_beneficiary("nh") == second
    assert r.evaluate_ret("ledger", 1, lambda: result).supported


@given(st.booleans())
@settings(max_examples=2, deadline=None)
def test_grace_carried_input_is_detached_from_later_caller_changes(nonservice):
    state = grace.GraceYearState()
    months = [replace(grace_case(), nonservice=nonservice)] * 12
    result = grace.grace_year(2026, state, months)
    twin = grace.grace_year(
        2026,
        grace.GraceYearState(),
        [replace(grace_case(), nonservice=nonservice)] * 12,
    )
    object.__setattr__(state, "had_entitlement", True)
    object.__setattr__(months[0], "nonservice", not nonservice)
    assert result == twin
    assert grace.grace_year(
        2027, result.next_state, [grace_case()] * 12
    ) == grace.grace_year(2027, twin.next_state, [grace_case()] * 12)


@pytest.mark.parametrize(
    "consumer",
    [
        lambda value: grace.grace_year(
            value, grace.GraceYearState(), [grace_case()] * 12
        ),
        lambda value: grace.grace_year(
            2026, grace.GraceYearState(), [grace_case()] * 12, fra_month=value
        ),
        lambda value: r.calculated_excess(1, 0, value),
        lambda value: r.countable_earnings(r.WorkEarnings(), value),
        lambda value: r.evaluate_ret(
            "weight",
            value,
            lambda: r.apply_ret_year(record(beneficiary()), RET_PARAMS),
        ),
        lambda value: a.age_attainment_month(date(1960, 1, 2), value),
        lambda value: a.apply_arf(
            claim(), payment_month=(2027, value), params=PARAMS
        ),
        lambda value: a.evaluate_arf("weight", value, arf_result),
        lambda value: c.eligibility_bend_points(value, PARAMS),
        lambda value: c.exact_pia(value, (960, 5785)),
        lambda value: c.exact_pia(1000, (value, 5785)),
        lambda value: c.earnings_aime(
            dict.fromkeys(range(1951, 2021), 0), basis(), value, PARAMS
        ),
        lambda value: c.annual_recomputation(
            basis(),
            dict.fromkeys(range(1951, 2021), 0),
            2020,
            value,
            PARAMS,
            {2020: 0},
        ),
        lambda value: c.recompute_sequence(
            basis(),
            dict.fromkeys(range(1951, 2021), 0),
            (2020,),
            value,
            PARAMS,
            {2020: 0},
        ),
        lambda value: c.evaluate_recomputation(
            "weight", value, recomputation_result
        ),
    ],
)
def test_every_r2_r3_scalar_entry_rejects_numeric_subclasses(consumer):
    with pytest.raises(g.InvalidFamilyInput):
        consumer(MutableInt(1))


@given(
    st.sampled_from([MutableInt, MutableFraction, MutableDecimal]),
    st.integers(0, 10000),
)
@settings(max_examples=30, deadline=None)
def test_r2_r3_mutable_number_rejection_is_value_independent(kind, amount):
    value = kind(amount)
    for evaluator, factory in (
        (
            r.evaluate_ret,
            lambda: r.apply_ret_year(record(beneficiary()), RET_PARAMS),
        ),
        (a.evaluate_arf, arf_result),
        (c.evaluate_recomputation, recomputation_result),
    ):
        with pytest.raises(g.InvalidFamilyInput):
            evaluator("weight", value, factory)


@pytest.mark.parametrize("invalid", [True, False, -1, F(1, 100), 1.0])
@pytest.mark.parametrize("field", ["claim", "own_pia", "own_payable"])
def test_r3_public_constructors_reject_illegal_money_immediately(
    field, invalid
):
    with pytest.raises(g.InvalidFamilyInput):
        if field == "claim":
            a.ARFClaim(
                a.ARFBenefitKind.RIB, date(1960, 1, 2), (2022, 1), invalid
            )
        else:
            a.SpouseOwnBenefit(
                invalid if field == "own_pia" else F(1),
                invalid if field == "own_payable" else F(1),
                a.SpouseOwnSequence.CONCURRENT_OR_PRECEDING,
            )


@pytest.mark.parametrize(
    "field,invalid",
    [
        ("kind", "rib"),
        ("birth_date", "1960-01-02"),
        ("first_reduction_month", (2022, 0)),
        ("conditions", {"other_suspension"}),
        ("death_date", "2025-01-01"),
        ("spouse_own", object()),
        ("full_work_deduction_months", {(2022, 0)}),
    ],
)
def test_arf_public_constructor_rejects_malformed_scalar_and_month_fields(
    field, invalid
):
    with pytest.raises(g.InvalidFamilyInput):
        replace(claim(), **{field: invalid})


def test_spouse_own_public_constructor_rejects_untyped_sequence():
    with pytest.raises(g.InvalidFamilyInput):
        a.SpouseOwnBenefit(F(1), F(1), "concurrent_or_preceding")


@given(st.integers(0, 100000), st.sampled_from([int, str, Decimal, F]))
@settings(max_examples=30, deadline=None)
def test_arf_constructor_money_is_canonical_at_admission(amount, encoding):
    raw = encoding(amount)
    source = a.ARFClaim(a.ARFBenefitKind.RIB, date(1960, 1, 2), (2022, 1), raw)
    own = a.SpouseOwnBenefit(
        raw, raw, a.SpouseOwnSequence.CONCURRENT_OR_PRECEDING
    )
    assert type(source.unreduced_benefit) is F
    assert type(own.pia) is type(own.payable) is F
    assert source.unreduced_benefit == own.pia == own.payable == amount


@pytest.mark.parametrize(
    "amount",
    [10**1000, F(10**1000), -(10**1000)],
    ids=["positive-int", "positive-fraction", "negative-int"],
)
def test_huge_finite_arf_rate_is_an_input_error_before_coverage(amount):
    params = replace(PARAMS, early_monthly_rates=(amount, F(1, 240)))
    source = replace(
        claim(), conditions={a.ARFUnsupportedReason.OTHER_SUSPENSION}
    )
    with pytest.raises(g.InvalidFamilyInput):
        a.evaluate_arf(
            "invalid",
            1,
            lambda: a.apply_arf(
                source, payment_month=(2027, 1), params=params
            ),
        )


def test_huge_exact_ret_money_and_recomputation_caps_do_not_overflow():
    amount = 10**1000
    assert r.calculated_excess(amount, 0, F(1, 2)) == amount // 2
    assert (
        r.countable_earnings(
            r.WorkEarnings(wages=(F(amount),) + (F(0),) * 11), None
        )
        == amount
    )
    history = dict.fromkeys(range(1951, 2021), 0)
    huge_history = history | {2020: amount}
    capped_history = history | {2020: 1000000}
    assert c.earnings_aime(
        huge_history, basis(), 2020, PARAMS
    ) == c.earnings_aime(capped_history, basis(), 2020, PARAMS)
    huge_nawi = replace(PARAMS, nawi={1977: amount, 2018: amount})
    assert c.eligibility_bend_points(2020, huge_nawi) == (180, 1085)


def test_recomputation_conditions_validate_raw_values_before_deduplication():
    source = basis()
    object.__setattr__(
        source,
        "conditions",
        (c.RecomputationCondition.PRIOR_DISABILITY, "prior_disability"),
    )
    with pytest.raises(g.InvalidFamilyInput):
        c.evaluate_recomputation("invalid", 1, lambda: recompute(source))


class EnumImpostor:
    def __init__(self, member):
        self.member = member

    def __eq__(self, other):
        return self.member == other

    def __hash__(self):
        return hash(self.member)


@pytest.mark.parametrize(
    "kind", ["grace-month", "grace-state", "arf", "recompute"]
)
@given(reverse=st.booleans())
@settings(max_examples=2, deadline=None)
def test_r2_r3_enum_collection_types_are_checked_before_equality_collapse(
    kind, reverse
):
    def items(member):
        values = (member, EnumImpostor(member))
        return tuple(reversed(values)) if reverse else values

    constructors = {
        "grace-month": lambda: grace.GraceMonth(
            entitled_types=items(grace.BenefitType.RIB)
        ),
        "grace-state": lambda: grace.GraceYearState(
            previous_entitled_types=items(grace.BenefitType.RIB),
            had_entitlement=True,
        ),
        "arf": lambda: replace(
            claim(), conditions=items(a.ARFUnsupportedReason.OTHER_SUSPENSION)
        ),
        "recompute": lambda: replace(
            basis(),
            conditions=items(c.RecomputationCondition.PRIOR_DISABILITY),
        ),
    }
    with pytest.raises(g.InvalidFamilyInput):
        constructors[kind]()


class MutableMappingKey:
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return self.value


class StringEnumIdentity(str, Enum):
    NH = "nh"


@pytest.mark.parametrize("boundary", ["computation", "seal", "lookup"])
@given(st.integers(0, 100), st.integers(0, 5))
@settings(max_examples=20, deadline=None)
def test_ret_partial_mapping_keys_are_builtin_nonempty_text(
    boundary, seed, key_kind
):
    key = (
        MutableMappingKey(seed),
        StringEnumIdentity.NH,
        seed,
        True,
        "",
        " ",
    )[key_kind]
    with pytest.raises(g.InvalidFamilyInput):
        if boundary == "computation":
            r.partial_payments(1, {key: 1}, {key: 1})
        elif boundary == "seal":
            # Private capability checks the same identity rule at sealing.
            _computed(r.PartialPaymentAllocation, {key: F(1)})
        else:
            r.partial_payments(1, {"nh": 1}, {"nh": 1})[key]


@pytest.mark.parametrize(
    "boundary", ["beneficiary", "record", "month", "worker", "accessor"]
)
def test_ret_identity_slots_reject_string_enum_subclasses(boundary):
    key = StringEnumIdentity.NH
    member = beneficiary()
    case = record(member)
    result = r.apply_ret_year(case, RET_PARAMS)
    with pytest.raises(g.InvalidFamilyInput):
        if boundary == "beneficiary":
            replace(member, beneficiary_id=key)
        elif boundary == "record":
            replace(case, nh_id=key)
        elif boundary in ("month", "worker"):
            # Private capability checks identities on computed nested rows.
            row = (
                result.months[0] if boundary == "month" else result.workers[0]
            )
            _computed(
                type(row), **(_result_values(row) | {"beneficiary_id": key})
            )
        else:
            result.for_beneficiary(key)
