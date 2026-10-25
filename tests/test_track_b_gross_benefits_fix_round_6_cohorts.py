"""One household-wide cohort per person, including their worker record.

Verification class: statutory conformance. Invented cases only; no
population, behavioral or forecast claim. Cohort-placement and standalone
family differentials require exact equality, with no rounding tolerance.
"""

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2023, 12)
WEIGHT = F(7, 3)
STYLES = ("direct", "built")
ENTRIES = ("household", "household-month-outcome")


def _records(
    style,
    months,
    *,
    cohort=1935,
    placement=1,
    gpo=False,
    own_months=0,
    pia=F(100),
):
    # Three optional sources: the worker record, beneficiary and declared
    # own benefit. Nonempty bit masks exercise every placement combination.
    worker = g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE,
        pia,
        reduction_months=own_months,
        birth_year=cohort if placement & 1 else None,
    )

    def state(own):
        if style == "built":
            return g.record_state(
                g.WorkerRecord(
                    g.FamilyKind.RETIREMENT,
                    min(cohort + 62, 2020),
                    own.pia,
                    worker_reduction_months=own.reduction_months,
                    worker_birth_year=own.birth_year,
                ),
                PARAMS,
            )
        return g.RecordState(
            g.FamilyKind.RETIREMENT,
            own.pia,
            g.floor_dime(own.pia * F(3, 2)),
            worker=own,
        )

    beneficiary = g.Beneficiary(
        "p",
        g.Role.SPOUSE,
        reduction_months=months,
        birth_year=cohort if placement & 2 else None,
        own_benefit=replace(
            worker, birth_year=cohort if placement & 4 else None
        ),
        own_benefit_first=True,
        conditions=(
            {g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET}
            if gpo
            else set()
        ),
    )
    return {
        "A": g.HouseholdRecord("p", state(worker)),
        "B": g.HouseholdRecord(
            "q",
            state(g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000))),
            (beneficiary,),
        ),
    }


def _run(
    records,
    entry,
    expected_refusal=g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET,
):
    original = deepcopy(records)
    guards = {
        key: g.SavingsClauseGuard(NOW, earlier_months_unknown=False)
        for key in records
    }
    try:
        if entry == "household":
            return g.household_benefits(
                records, payment_month=NOW, params=PARAMS
            )
        try:
            outcome = g.household_month_outcome(
                records,
                payment_month=NOW,
                params=PARAMS,
                guards=guards,
                weight=WEIGHT,
            )
        except g.InvalidFamilyInput:
            assert all(guard.next_month == NOW for guard in guards.values())
            raise
        assert all(
            guard.next_month == g.YearMonth(2024, 1)
            for guard in guards.values()
        )
        counts = g.count_family_outcomes([outcome])
        assert (counts.rows, counts.weight) == (1, WEIGHT)
        if not outcome.supported:
            assert counts.unsupported_rows == 1
            assert counts.unsupported_weight == WEIGHT
            assert counts.unsupported_by_reason == {
                expected_refusal: (1, WEIGHT)
            }
            if (
                expected_refusal
                is g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
            ):
                assert outcome.unsupported.record_id == "B"
            return outcome.unsupported.reason
        assert counts.supported_rows == 1
        assert counts.supported_weight == WEIGHT
        assert counts.unsupported_rows == counts.unsupported_weight == 0
        return outcome.benefits
    finally:
        assert records == original


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("gpo", (False, True))
def test_review_worker_cohort_makes_auxiliary_rf37_invalid(style, entry, gpo):
    with pytest.raises(g.InvalidFamilyInput, match="between 0 and 36"):
        _run(_records(style, 37, gpo=gpo), entry)


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("field", ("beneficiary", "own", "both"))
@pytest.mark.parametrize("months", (36, 37))
@pytest.mark.parametrize("gpo", (False, True))
def test_review_conflicting_worker_cohort_is_invalid(
    style, entry, field, months, gpo
):
    records = _records(style, months, gpo=gpo)
    member = records["B"].beneficiaries[0]
    member = replace(
        member,
        birth_year=1960 if field != "own" else None,
        own_benefit=replace(
            member.own_benefit,
            birth_year=1960 if field != "beneficiary" else None,
        ),
    )
    records["B"] = replace(records["B"], beneficiaries=(member,))
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        _run(records, entry)


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
def test_review_rf36_control_matches_explicit_cohort_and_single_record(
    style, entry
):
    actual = _run(_records(style, 36), entry)
    explicit = _records(style, 36, placement=7)
    assert actual == _run(explicit, entry)
    for record_id, record in explicit.items():
        assert actual.records[record_id] == g.family_benefits(
            record.state,
            record.beneficiaries,
            payment_month=NOW,
            params=PARAMS,
            standalone=True,
        )
    assert actual.records["B"].by_id()["p"].auxiliary_payable == 300
    assert actual.record_total == actual.record_total_whole_dollars == 1400


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
def test_review_rf36_gpo_control_preserves_refusal_weight(style, entry):
    records = _records(style, 36, gpo=True)
    expected = g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
    if entry == "household":
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            _run(records, entry)
        assert caught.value.reason is expected
    else:
        assert _run(records, entry) is expected


@pytest.mark.parametrize("style", STYLES)
def test_review_minimized_positive_dime_rf37_is_invalid(style):
    with pytest.raises(g.InvalidFamilyInput, match="between 0 and 36"):
        _run(_records(style, 37, pia=F(1, 10)), "household-month-outcome")


@settings(max_examples=100, deadline=None, derandomize=True)
@example(1935, 37, 0, "direct", "household-month-outcome", True)
@example(1935, 0, 37, "direct", "household-month-outcome", True)
@given(
    st.integers(1929, 1960),
    st.integers(0, 60),
    st.integers(0, 60),
    st.sampled_from(STYLES),
    st.sampled_from(ENTRIES),
    st.booleans(),
)
def test_property_household_cohort_placement_and_order_are_equivalent(
    cohort, months, own_months, style, entry, gpo
):
    results = []
    for placement in range(1, 8):
        try:
            records = _records(
                style,
                months,
                cohort=cohort,
                placement=placement,
                gpo=gpo,
                own_months=own_months,
            )
        except g.InvalidFamilyInput:
            # The builder can reject the worker's own RF before a
            # household exists when its cohort was already supplied.
            assert style == "built" and placement & 1
            assert own_months > PARAMS.fra_months(cohort) - 744
            continue
        for ordered in (records, dict(reversed(list(records.items())))):
            if max(months, own_months) > PARAMS.fra_months(cohort) - 744:
                with pytest.raises(g.InvalidFamilyInput):
                    _run(ordered, entry)
            elif gpo and entry == "household":
                with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
                    _run(ordered, entry)
                assert caught.value.reason is (
                    g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
                )
            else:
                results.append(_run(ordered, entry))
    assert not results or all(result == results[0] for result in results)


@settings(deadline=None, derandomize=True)
@given(
    st.integers(1929, 1960),
    st.integers(1, 30),
    st.sampled_from(STYLES),
    st.sampled_from(ENTRIES),
    st.booleans(),
)
def test_property_household_conflicts_precede_refusals(
    cohort, difference, style, entry, reverse
):
    records = _records(style, 0, cohort=cohort, gpo=True)
    member = records["B"].beneficiaries[0]
    records["B"] = replace(
        records["B"],
        beneficiaries=(replace(member, birth_year=cohort + difference),),
    )
    if reverse:
        records = dict(reversed(list(records.items())))
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        g.check_household_records(records)
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        _run(records, entry)


def _auxiliary_only_records(style, first, second):
    record = _records(style, 0)["B"]
    return {
        "B": replace(record, beneficiaries=(first,)),
        "C": replace(record, worker_id="r", beneficiaries=(second,)),
    }


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("months", (36, 37))
def test_auxiliary_only_shared_cohort_precedes_multiple_record_refusal(
    style, entry, reverse, months
):
    records = _auxiliary_only_records(
        style,
        g.Beneficiary("p", g.Role.SPOUSE, reduction_months=months),
        g.Beneficiary("p", g.Role.SPOUSE, birth_year=1935),
    )
    if reverse:
        records = dict(reversed(list(records.items())))
    reason = g.UnsupportedReason.MULTIPLE_AUXILIARY_RECORDS
    if months == 37:
        with pytest.raises(g.InvalidFamilyInput, match="between 0 and 36"):
            _run(records, entry)
    elif entry == "household":
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            _run(records, entry)
        assert caught.value.reason is reason
    else:
        assert _run(records, entry, reason) is reason


@settings(deadline=None, derandomize=True)
@given(
    st.integers(1929, 1960),
    st.integers(1, 30),
    st.sampled_from((g.Role.SPOUSE, g.Role.CHILD)),
    st.sampled_from(STYLES),
    st.sampled_from(ENTRIES),
    st.booleans(),
)
def test_property_auxiliary_only_cohort_conflicts_precede_record_refusals(
    cohort, difference, role, style, entry, reverse
):
    records = _auxiliary_only_records(
        style,
        g.Beneficiary("p", role, birth_year=cohort),
        g.Beneficiary("p", role, birth_year=cohort + difference),
    )
    if reverse:
        records = dict(reversed(list(records.items())))
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        g.check_household_records(records)
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        _run(records, entry)
