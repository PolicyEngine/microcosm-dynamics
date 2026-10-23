"""Unclaimed workers retain their household-wide SSA birth cohort.

Verification class: statutory conformance. Invented cases only; no
population, behavioral or forecast claim. Household/standalone and cohort
placement differentials require exact equality, without tolerance.
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
ENTRIES = ("household", "household-month-outcome")
STYLES = ("built", "direct")


def _records(months, *, cohort=1935, gpo=False, explicit=False, style="built"):
    unclaimed = g.record_state(
        g.WorkerRecord(
            g.FamilyKind.RETIREMENT,
            cohort + 62,
            F(100),
            worker_birth_year=cohort,
            conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
        ),
        PARAMS,
    )
    if style == "direct":
        unclaimed = g.RecordState(
            g.FamilyKind.RETIREMENT,
            F(100),
            g.retirement_survivor_family_maximum(F(100), cohort + 62, PARAMS),
            worker_birth_year=cohort,
            conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
            eligibility_year=cohort + 62,
            source=unclaimed.source,
        )
    other = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(1000),
        F(1500),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000)),
    )
    spouse = g.Beneficiary(
        "p",
        g.Role.SPOUSE,
        reduction_months=months,
        birth_year=cohort if explicit else None,
        conditions=(
            {g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET}
            if gpo
            else set()
        ),
    )
    return {
        "A": g.HouseholdRecord("p", unclaimed),
        "B": g.HouseholdRecord("q", other, (spouse,)),
    }


def _run(records, entry):
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
        if outcome.supported:
            assert (counts.supported_rows, counts.supported_weight) == (
                1,
                WEIGHT,
            )
            return outcome.benefits
        reason = g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
        assert counts.unsupported_by_reason == {reason: (1, WEIGHT)}
        assert (counts.unsupported_rows, counts.unsupported_weight) == (
            1,
            WEIGHT,
        )
        assert outcome.unsupported.record_id == "B"
        return outcome.unsupported.reason
    finally:
        assert records == original


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("gpo", (False, True))
@pytest.mark.parametrize("style", STYLES)
def test_review_unclaimed_worker_cohort_makes_rf37_invalid(entry, gpo, style):
    with pytest.raises(g.InvalidFamilyInput, match="between 0 and 36"):
        _run(_records(37, gpo=gpo, style=style), entry)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("style", STYLES)
def test_review_unclaimed_worker_rf36_control_matches_explicit_cohort(
    entry, style
):
    result = _run(_records(36, style=style), entry)
    explicit = _records(36, explicit=True, style=style)
    assert result == _run(explicit, entry)
    for record_id, record in explicit.items():
        assert result.records[record_id] == g.family_benefits(
            record.state,
            record.beneficiaries,
            payment_month=NOW,
            params=PARAMS,
            standalone=True,
        )
    assert result.records["A"].worker_benefit is None
    assert result.records["A"].record_total == 0
    row = result.records["B"].by_id()["p"]
    assert row.own_benefit is None
    assert row.auxiliary_payable == row.whole_dollar_auxiliary == 375
    assert result.record_total == result.record_total_whole_dollars == 1375


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("style", STYLES)
def test_review_unclaimed_worker_rf36_gpo_control_retains_denominator(
    entry, style
):
    records = _records(36, gpo=True, style=style)
    reason = g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
    if entry == "household":
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            _run(records, entry)
        assert caught.value.reason is reason
    else:
        assert _run(records, entry) is reason


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("style", STYLES)
def test_unclaimed_worker_cohort_conflict_precedes_gpo(entry, reverse, style):
    records = _records(36, gpo=True, style=style)
    member = records["B"].beneficiaries[0]
    records["B"] = replace(
        records["B"], beneficiaries=(replace(member, birth_year=1960),)
    )
    if reverse:
        records = dict(reversed(list(records.items())))
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        g.check_household_records(records)
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        _run(records, entry)


@settings(max_examples=100, deadline=None, derandomize=True)
@example(1935, 37, "household-month-outcome", True, "built")
@given(
    st.integers(1929, 1960),
    st.integers(0, 60),
    st.sampled_from(ENTRIES),
    st.booleans(),
    st.sampled_from(STYLES),
)
def test_property_unclaimed_cohort_validation_is_order_independent(
    cohort, months, entry, gpo, style
):
    results = []
    for explicit in (False, True):
        records = _records(
            months, cohort=cohort, gpo=gpo, explicit=explicit, style=style
        )
        for ordered in (records, dict(reversed(list(records.items())))):
            if months > PARAMS.fra_months(cohort) - 744:
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
@given(st.integers(1929, 1960), st.sampled_from(ENTRIES))
def test_property_unclaimed_builder_and_direct_cohorts_agree(cohort, entry):
    built = _records(36, cohort=cohort)
    direct = _records(36, cohort=cohort, style="direct")
    assert built == direct
    assert _run(built, entry) == _run(direct, entry)
    assert built["A"].state.worker_birth_year == cohort
    assert built["A"].state.worker is None


@settings(deadline=None, derandomize=True)
@given(
    st.integers(1929, 1960),
    st.integers(1, 30),
    st.sampled_from(ENTRIES),
    st.sampled_from(STYLES),
    st.booleans(),
)
def test_property_unclaimed_cohort_conflicts_precede_refusals(
    cohort, delta, entry, style, reverse
):
    records = _records(36, cohort=cohort, gpo=True, style=style)
    member = records["B"].beneficiaries[0]
    records["B"] = replace(
        records["B"],
        beneficiaries=(replace(member, birth_year=cohort + delta),),
    )
    if reverse:
        records = dict(reversed(list(records.items())))
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        _run(records, entry)


@settings(deadline=None, derandomize=True)
@given(
    st.integers(1929, 1960),
    st.sampled_from(tuple(g.FamilyKind)),
    st.booleans(),
)
def test_property_record_builder_preserves_cohort_without_rib(
    cohort, kind, unclaimed
):
    record = g.WorkerRecord(
        kind,
        cohort + 62,
        F(100),
        worker_birth_year=cohort,
        aime=1000 if kind is g.FamilyKind.DISABILITY else None,
        first_dib_entitlement=(
            g.YearMonth(cohort + 62, 1)
            if kind is g.FamilyKind.DISABILITY
            else None
        ),
        conditions=(
            {g.RecordCondition.WORKER_NOT_ENTITLED}
            if unclaimed and kind is g.FamilyKind.RETIREMENT
            else set()
        ),
    )
    original = deepcopy(record)
    state = g.record_state(record, PARAMS)
    assert state.worker_birth_year == cohort
    assert record == original
    if kind is not g.FamilyKind.RETIREMENT or unclaimed:
        assert state.worker is None
    else:
        assert state.worker.birth_year == cohort


@settings(deadline=None, derandomize=True)
@given(st.integers(1929, 1960), st.integers(1, 30))
def test_property_record_and_own_cohorts_reconcile_immutably(cohort, delta):
    states = []
    for placement in (1, 2, 3):
        own = g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(100),
            birth_year=cohort if placement & 1 else None,
        )
        state = g.RecordState(
            g.FamilyKind.RETIREMENT,
            F(100),
            F(150),
            worker=own,
            worker_birth_year=cohort if placement & 2 else None,
        )
        assert own.birth_year == (cohort if placement & 1 else None)
        assert state.worker_birth_year == state.worker.birth_year == cohort
        states.append(state)
    assert states[0] == states[1] == states[2]
    with pytest.raises(g.InvalidFamilyInput, match="birth_year.*differs"):
        replace(states[0], worker_birth_year=cohort + delta)


@pytest.mark.parametrize("year", (True, "1935", F(1935)))
def test_record_cohort_requires_integer_year(year):
    with pytest.raises(TypeError, match="worker_birth_year must be an int"):
        g.RecordState(
            g.FamilyKind.RETIREMENT,
            F(100),
            F(150),
            worker_birth_year=year,
            conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
        )
