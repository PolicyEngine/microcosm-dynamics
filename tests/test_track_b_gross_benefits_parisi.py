"""GN 02603 dual-entitlement conformance over statutory and invented cases.

Verification class: statutory conformance. These tests admit gross benefits
for supported configurations only; they make no population or forecast claim.
GN 02603.060 A.5, A.8, A.9 and B.2 supply every quoted example figure.
Whole-dollar amounts below follow 215(g) independently of the captures.
Work deductions, compensation offsets and combined maximums are not tested
as supported family computations in this module.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
MONTH = g.YearMonth(2000, 1)
OLD_AGE = g.OwnBenefitKind.OLD_AGE
DISABILITY = g.OwnBenefitKind.DISABILITY


def _floor_dime(value):
    """Independent integer-quotient reference, with no G rounding helper."""
    value = F(value)
    return F((value * 10).numerator // (value * 10).denominator, 10)


def _whole(value):
    value = F(value)
    return value.numerator // value.denominator


def _retired(pia, maximum, own=None):
    pia = F(pia)
    return g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        F(maximum),
        worker=own or g.OwnBenefit(OLD_AGE, pia),
    )


def _family(state, members):
    return g.family_benefits(
        state,
        members,
        payment_month=MONTH,
        params=PARAMS,
        standalone=True,
    )


EXAMPLES = [
    dict(
        id="A.5",
        section="5. Full deduction for dual entitlement",
        next_section="6. Full deduction because",
        pia="400.00",
        maximum="650.00",
        ob="200.00",
        standard="83.30",
        before_spouse="83.30",
        spouse_months=0,
        own_person="B",
        own_pia="100.00",
        own_kind=OLD_AGE,
        own_months=0,
        own_payable="100.00",
        payable={"B": "0.00", "C1": "125.00", "C2": "125.00"},
        counted="0.00",
        figures=(
            "400.00",
            "650.00",
            "200.00",
            "83.30",
            "100.00",
            "0.00",
            "125.00",
        ),
    ),
    dict(
        id="A.8",
        section="8. Full deduction because",
        next_section="9. Full deduction because",
        pia="400.00",
        maximum="650.00",
        ob="200.00",
        standard="83.30",
        before_spouse="62.40",
        spouse_months=36,
        own_person="B",
        own_pia="100.00",
        own_kind=OLD_AGE,
        own_months=36,
        own_payable="80.00",
        payable={"B": "0.00", "C1": "125.00", "C2": "125.00"},
        counted="0.00",
        figures=(
            "400.00",
            "650.00",
            "200.00",
            "83.30",
            "62.40",
            "100.00",
            "80.00",
            "0.00",
            "125.00",
        ),
    ),
    dict(
        id="A.9",
        section="9. Full deduction because",
        next_section="B. Examples of permanent partial deductions",
        pia="600.00",
        maximum="900.00",
        ob="300.00",
        standard="100.00",
        before_spouse="75.00",
        spouse_months=36,
        own_person="C2",
        own_pia="200.00",
        own_kind=DISABILITY,
        own_months=0,
        own_payable="200.00",
        payable={"B": "112.50", "C1": "150.00", "C2": "0.00"},
        counted="0.00",
        figures=(
            "600.00",
            "900.00",
            "300.00",
            "100.00",
            "75.00",
            "200.00",
            "112.50",
            "150.00",
            "0.00",
        ),
    ),
    dict(
        id="B.2",
        section="2. Partial deduction and age reduction Involved",
        next_section="3. Partial deduction for dual entitlement",
        pia="500.00",
        maximum="750.00",
        ob="250.00",
        standard="83.30",
        before_spouse="62.40",
        spouse_months=36,
        own_person="B",
        own_pia="80.00",
        own_kind=OLD_AGE,
        own_months=36,
        own_payable="64.00",
        payable={"B": "2.40", "C1": "123.30", "C2": "123.30"},
        counted="3.30",
        figures=(
            "500.00",
            "750.00",
            "250.00",
            "83.30",
            "62.40",
            "80.00",
            "64.00",
            "3.30",
            "2.40",
            "0.90",
            "246.70",
            "123.30",
        ),
    ),
]


def _example_members(example, own=None):
    spouse = g.Beneficiary(
        "B",
        g.Role.SPOUSE,
        reduction_months=example["spouse_months"],
        birth_year=1935,
        own_benefit=own if example["own_person"] == "B" else None,
        own_benefit_first=(
            True if own is not None and example["own_person"] == "B" else None
        ),
    )
    return [
        spouse,
        g.Beneficiary("C1", g.Role.CHILD),
        g.Beneficiary(
            "C2",
            g.Role.CHILD,
            own_benefit=own if example["own_person"] == "C2" else None,
        ),
    ]


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda case: case["id"])
@pytest.mark.parametrize(
    "household", [False, True], ids=["standalone", "household"]
)
def test_gn_02603_060_dual_entitlement_examples(example, household):
    """Reproduce every quoted figure and both supported integration routes."""
    text = source_text("poms_gn_02603_060")
    section = text.split(example["section"], 1)[1].split(
        example["next_section"], 1
    )[0]
    for figure in example["figures"]:
        assert figure in section, (example["id"], figure)
    state = _retired(example["pia"], example["maximum"])
    before = _family(state, _example_members(example))
    assert before.worker_benefit == F(example["pia"])
    assert before.by_id()["B"].auxiliary_payable == F(example["before_spouse"])
    assert all(
        row.original_benefit == F(example["ob"])
        for row in before.beneficiaries
    )
    assert all(
        row.standard_rate == F(example["standard"])
        for row in before.beneficiaries
    )
    own = g.OwnBenefit(
        example["own_kind"],
        F(example["own_pia"]),
        reduction_months=example["own_months"],
        birth_year=1935 if example["own_kind"] is OLD_AGE else None,
    )
    members = _example_members(example, own)
    if household:
        own_maximum = _floor_dime(own.pia * F(3, 2))
        own_state = (
            _retired(own.pia, own_maximum, own)
            if own.kind is OLD_AGE
            else g.RecordState(g.FamilyKind.DISABILITY, own.pia, own_maximum)
        )
        outcome = g.household_benefits(
            {
                "insured": g.HouseholdRecord("A", state, members),
                "own": g.HouseholdRecord(example["own_person"], own_state),
            },
            payment_month=MONTH,
            params=PARAMS,
        )
        result = outcome.records["insured"]
        assert outcome.records["own"].worker_benefit == F(
            example["own_payable"]
        )
    else:
        result = _family(state, members)
    assert result.redistribution_applied
    rows = result.by_id()
    for person, amount in example["payable"].items():
        assert rows[person].auxiliary_payable == F(amount)
        assert rows[person].whole_dollar_auxiliary == _whole(F(amount))
        assert rows[person].original_benefit == F(example["ob"])
        assert rows[person].standard_rate == F(example["standard"])
    dual = rows[example["own_person"]]
    assert dual.own_benefit == F(example["own_payable"])
    assert dual.whole_dollar_own == _whole(F(example["own_payable"]))
    assert dual.counted_against_maximum == F(example["counted"])
    expected_total = F(example["pia"]) + sum(
        map(F, example["payable"].values()), F(0)
    )
    expected_whole = _whole(F(example["pia"])) + sum(
        _whole(F(v)) for v in example["payable"].values()
    )
    assert (result.record_total, result.record_total_whole_dollars) == (
        expected_total,
        expected_whole,
    )
    if household:
        assert outcome.record_total == expected_total + F(
            example["own_payable"]
        )
        assert outcome.record_total_whole_dollars == expected_whole + _whole(
            F(example["own_payable"])
        )
    if example["id"] == "B.2":
        assert dual.counted_against_maximum - dual.auxiliary_payable == F(
            "0.90"
        )
        assert (
            result.available_for_auxiliaries - dual.counted_against_maximum
            == F("246.70")
        )


RULE_QUOTES = {
    "poms_gn_02603_045": (
        "Only pay this increase to others who are not dually entitled.",
        "this change is effective for all benefits beginning with those payable for October 1999.",
        "The benefit payable to the dually entitled person is the amount before any applicable reduction for age",
    ),
    "poms_gn_02603_050": (
        "Age reduction amount for all workers or deductees",
        "Partial benefit payable to any worker or deductee",
        "Use the OB if the result of this calculation is greater than the OB.",
        "If dual entitlement reduces a beneficiary's rate to $0.00 (technically entitled)",
    ),
}


def test_parisi_rule_text_is_quoted_from_the_captures():
    for source, quotes in RULE_QUOTES.items():
        text = source_text(source)
        for quote in quotes:
            assert quote in text, (source, quote)


def test_ptap_subtracts_auxiliary_age_reduction_and_partial_payable():
    """GN 02603.060 B.2: 250-2.40-.90=246.70, split to 123.30 each."""
    actual = g.maximum_redistribution_rates(
        {"B": F(250), "C1": F(250), "C2": F(250)},
        F(250),
        deductee_payables={"B": F("2.40")},
        age_reductions={"B": F("0.90")},
    )
    assert dict(actual) == {"C1": F("123.30"), "C2": F("123.30")}


@st.composite
def redistribution_cases(draw):
    count = draw(st.integers(1, 6))
    obs = {f"b{i}": F(draw(st.integers(0, 20_000)), 10) for i in range(count)}
    ids = draw(st.sets(st.sampled_from(list(obs)), max_size=count))
    payable = {key: F(draw(st.integers(0, 10_000)), 10) for key in sorted(ids)}
    age = {key: F(draw(st.integers(0, 10_000)), 10) for key in sorted(ids)}
    other = {key: F(draw(st.integers(0, 10_000)), 10) for key in sorted(ids)}
    available = F(draw(st.integers(0, 80_000)), 10)
    return obs, available, payable, age, other


def _reference(obs, available, payable, age, other):
    pool = (
        available
        - sum(payable.values(), F(0))
        - sum(age.values(), F(0))
        - sum(other.values(), F(0))
    )
    candidates = {key: ob for key, ob in obs.items() if key not in payable}
    total = sum(candidates.values(), F(0))
    return {
        key: (
            F(0)
            if total == 0
            else max(F(0), min(ob, _floor_dime(ob * pool / total)))
        )
        for key, ob in candidates.items()
    }


def _redistribute(case):
    obs, available, payable, age, other = case
    return g.maximum_redistribution_rates(
        obs,
        available,
        deductee_payables=payable,
        age_reductions=age,
        other_deductions=other,
    )


@given(redistribution_cases())
@settings(deadline=None)
def test_ptap_formula_matches_independent_fraction_reference(case):
    """Exact differential; proportional floor/cap plus all supplied terms."""
    obs, available, payable, age, other = case
    assert dict(_redistribute(case)) == _reference(
        obs, available, payable, age, other
    )


@given(redistribution_cases())
@settings(deadline=None)
def test_ptap_rates_obey_bounds_dime_units_and_pool_budget(case):
    obs, available, payable, age, other = case
    actual = _redistribute(case)
    assert set(actual) == set(obs) - set(payable)
    pool = (
        available
        - sum(payable.values(), F(0))
        - sum(age.values(), F(0))
        - sum(other.values(), F(0))
    )
    assert sum(actual.values(), F(0)) <= max(F(0), pool)
    for key, rate in actual.items():
        assert F(0) <= rate <= obs[key]
        assert (rate * 10).denominator == 1
    if pool >= sum(obs[key] for key in actual):
        assert dict(actual) == {key: obs[key] for key in actual}


@given(redistribution_cases())
@settings(deadline=None)
def test_ptap_is_deterministic_and_independent_of_mapping_order(case):
    obs, available, payable, age, other = case
    first = dict(_redistribute(case))
    assert first == dict(_redistribute(case))
    reversed_case = (
        dict(reversed(list(obs.items()))),
        available,
        dict(reversed(list(payable.items()))),
        dict(reversed(list(age.items()))),
        dict(reversed(list(other.items()))),
    )
    assert first == dict(_redistribute(reversed_case))


@given(
    redistribution_cases(),
    st.integers(0, 10_000),
    st.sampled_from(["payable", "age", "other"]),
)
@settings(deadline=None)
def test_increasing_a_supplied_deduction_cannot_raise_other_rates(
    case, extra_dimes, term
):
    obs, available, payable, age, other = case
    if not payable:
        return
    before = _redistribute(case)
    maps = {"payable": dict(payable), "age": dict(age), "other": dict(other)}
    deductee = sorted(payable)[0]
    maps[term][deductee] += F(extra_dimes, 10)
    after = _redistribute(
        (obs, available, maps["payable"], maps["age"], maps["other"])
    )
    assert set(before) == set(after)
    assert all(after[key] <= before[key] for key in before)


@st.composite
def method_c_cases(draw):
    pia = F(draw(st.integers(600, 60_000)), 10)
    standard = _floor_dime(pia / 6)
    own_pia = F(draw(st.integers(1, _whole(standard * 10) - 1)), 10)
    spouse_months = draw(st.integers(0, 60))
    worker_months = draw(st.integers(0, 60))
    return pia, own_pia, spouse_months, worker_months


@given(method_c_cases())
@example((F(600), F("99.90"), 36, 0))
@settings(deadline=None)
def test_method_c_own_rib_age_reduction_does_not_change_redistributed_rates(
    case,
):
    """GN .060 B.2's method C excludes the own-RIB reduction from PTAP.

    This exact differential compares reduced-own-RIB and unreduced-own-RIB
    computations over their shared semantics. Own RIB payment changes;
    auxiliary payable and the non-deductee shares remain identical.
    A positive before-age excess rounded to zero after age reduction is
    counted whole, as GN 02603.045's before-age amount.
    """
    pia, own_pia, spouse_months, worker_months = case
    state = _retired(pia, _floor_dime(pia * F(3, 2)))
    own = g.OwnBenefit(OLD_AGE, own_pia, birth_year=1960)
    spouse = g.Beneficiary(
        "B",
        g.Role.SPOUSE,
        reduction_months=spouse_months,
        own_benefit=own,
        own_benefit_first=True,
        birth_year=1960,
    )
    children = [g.Beneficiary(key, g.Role.CHILD) for key in ("C1", "C2")]
    reduced_spouse = dataclasses.replace(
        spouse,
        own_benefit=dataclasses.replace(own, reduction_months=worker_months),
    )
    standard = _floor_dime((state.family_maximum - pia) / 3)
    excess = standard - own_pia
    reduction = min(spouse_months, 36) * F(1, 144) + max(
        0, spouse_months - 36
    ) * F(1, 240)
    auxiliary = _floor_dime(excess * (1 - reduction))
    unchanged = _family(state, [spouse, *children])
    reduced = _family(state, [reduced_spouse, *children])
    counted = excess
    child_rate = min(
        _floor_dime(pia / 2),
        _floor_dime((state.family_maximum - pia - counted) / 2),
    )
    for result in [unchanged, reduced]:
        rows = result.by_id()
        assert rows["B"].auxiliary_payable == auxiliary
        assert rows["B"].counted_against_maximum == counted
        assert (
            rows["C1"].auxiliary_payable
            == rows["C2"].auxiliary_payable
            == child_rate
        )
    worker_reduction = min(worker_months, 36) * F(1, 180) + max(
        0, worker_months - 36
    ) * F(1, 240)
    assert reduced.by_id()["B"].own_benefit == _floor_dime(
        own_pia * (1 - worker_reduction)
    )


def test_method_b_zero_only_after_age_keeps_the_age_reduction_in_ptap():
    """Source conflict us:oasdi-dual-entitlement-zero-after-age-reduction.

    Invented PIA500/max750; B36months ownRIB64, method B. Share83.30
    reduces to62.40 for age, then offsets to0. Dual entitlement considered
    first leaves83.30-64=19.30, so GN .050A.2's disregard does not apply.
    In 402(k)(3)(A)'s order the offset withholds62.40 and age20.90;
    20 CFR 404.403(a)(5) excludes only the former and .060 B.2 keeps the
    age slice in PTAP: children114.50 each, record total729. Rejected
    diagnostics: A.2's disregard (125 each, total750) and .045's
    before-age amount alone (115.30 each, total730.60).
    """
    spouse = g.Beneficiary(
        "B",
        g.Role.SPOUSE,
        reduction_months=36,
        own_benefit=g.OwnBenefit(OLD_AGE, F(64)),
        own_benefit_first=False,
    )
    state = _retired(500, 750)
    members = [
        spouse,
        g.Beneficiary("C1", g.Role.CHILD),
        g.Beneficiary("C2", g.Role.CHILD),
    ]
    rows = _family(state, members).by_id()
    assert rows["B"].age_adjusted_rate == F("62.40")
    assert rows["B"].auxiliary_payable == 0
    assert rows["B"].counted_against_maximum == F("20.90")
    assert rows["C1"].auxiliary_payable == rows["C2"].auxiliary_payable
    assert rows["C1"].auxiliary_payable == F("114.50")
    total = sum((row.auxiliary_payable for row in rows.values()), F(0))
    assert F(500) + total == 729
    zero_rate_exception = g.maximum_redistribution_rates(
        {"B": F(250), "C1": F(250), "C2": F(250)},
        F(250),
        deductee_payables={"B": F(0)},
    )
    assert dict(zero_rate_exception) == {"C1": F(125), "C2": F(125)}
    assert F(500) + sum(zero_rate_exception.values(), F(0)) == 750
    before_age_only = g.maximum_redistribution_rates(
        {"B": F(250), "C1": F(250), "C2": F(250)},
        F(250),
        deductee_payables={"B": F("19.30")},
    )
    assert dict(before_age_only) == {"C1": F("115.30"), "C2": F("115.30")}
    assert F(500) + sum(before_age_only.values(), F(0)) == F("730.60")
    assert (
        "The benefit payable to the dually entitled person is the amount before any applicable reduction for age"
        in source_text("poms_gn_02603_045")
    )
    rule = " ".join(source_text("poms_gn_02603_050").split())
    for quote in (
        "If dual entitlement reduces a beneficiary's rate to $0.00 "
        "(technically entitled)",
        "Age reduction amount for all workers or deductees",
        "Partial benefit payable to any worker or deductee",
    ):
        assert quote in rule
    examples = " ".join(source_text("poms_gn_02603_060").split())
    for quote in (
        "In order to redistribute only the amount being withheld because "
        "of dual entitlement we must account for the entire $83.30 due B.",
        "This example shows that B's age reduction has no effect because "
        "we consider their dual entitlement first.",
    ):
        assert quote in examples


@settings(deadline=None)
@example(F(64), 36)
@example(F("62.40"), 36)
@example(F("83.20"), 36)
@example(F("83.30"), 36)
@example(F(50), 60)
@given(
    st.integers(1, 1000).map(lambda dimes: F(dimes, 10)),
    st.integers(0, 60),
)
def test_method_b_counts_payable_plus_age_reduction_until_a2(own, months):
    """Method B counts what dual entitlement does not withhold.

    Counted = payable + the auxiliary's own age reduction, which is
    standard - min(own, age-adjusted rate), until the own benefit reaches
    the standard rate and GN 02603.050A.2 disregards the spouse. Children
    never fall when the own benefit rises.
    """
    spouse = g.Beneficiary(
        "B",
        g.Role.SPOUSE,
        reduction_months=months,
        own_benefit=g.OwnBenefit(OLD_AGE, own),
        own_benefit_first=False,
    )
    state = _retired(500, 750)
    children = [g.Beneficiary(key, g.Role.CHILD) for key in ("C1", "C2")]
    rows = _family(state, [spouse, *children]).by_id()
    standard = F("83.30")
    age_adjusted = rows["B"].age_adjusted_rate
    counted = F(0) if own >= standard else standard - min(own, age_adjusted)
    assert rows["B"].counted_against_maximum == counted
    assert rows["B"].auxiliary_payable == max(F(0), age_adjusted - own)
    child = min(F(250), _floor_dime((F(250) - counted) / 2))
    assert rows["C1"].auxiliary_payable == rows["C2"].auxiliary_payable
    assert rows["C1"].auxiliary_payable == child
    richer = _family(
        state,
        [
            dataclasses.replace(
                spouse, own_benefit=g.OwnBenefit(OLD_AGE, own + F(1, 10))
            ),
            *children,
        ],
    ).by_id()
    assert richer["C1"].auxiliary_payable >= rows["C1"].auxiliary_payable


@pytest.mark.parametrize(
    ("payable", "ages", "other"),
    [
        ({"unknown": F(0)}, {}, {}),
        ({"B": F(0)}, {"C": F(1)}, {}),
        ({"B": F(0)}, {}, {"C": F(1)}),
    ],
)
def test_ptap_deduction_ids_must_identify_deductees(payable, ages, other):
    with pytest.raises(g.InvalidFamilyInput):
        g.maximum_redistribution_rates(
            {"B": F(100), "C": F(100)},
            F(100),
            deductee_payables=payable,
            age_reductions=ages,
            other_deductions=other,
        )
