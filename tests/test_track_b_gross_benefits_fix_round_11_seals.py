"""Sealed G computations: statutory conformance on invented cases only.

No population, behavioral, payment-timing or forecast claim.
"""

import pickle
from copy import copy, deepcopy
from dataclasses import fields, replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
JAN = g.YearMonth(2026, 1)
FEB = g.YearMonth(2026, 2)


def _records(pia=F("1.10"), maximum=F("1.90")):
    return {
        "record": g.HouseholdRecord(
            "worker",
            g.RecordState(
                g.FamilyKind.RETIREMENT,
                pia,
                maximum,
                g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
            ),
            tuple(g.Beneficiary(key, g.Role.CHILD) for key in ("a", "b")),
        )
    }


def _family(month=JAN, pia=F("1.10"), maximum=F("1.90")):
    record = _records(pia, maximum)["record"]
    return g.family_benefits(
        record.state,
        record.beneficiaries,
        payment_month=month,
        params=PARAMS,
        standalone=True,
    )


def _refuse():
    return g.retirement_survivor_family_maximum(F(1000), 1982, PARAMS)


def _outputs():
    family = _family()
    outcome = g.evaluate_family("supported", F(1), lambda: family)
    refusal = g.evaluate_family("refused", F(1), _refuse)
    return (
        family.beneficiaries[0],
        family,
        g.household_benefits(_records(), payment_month=JAN, params=PARAMS),
        outcome,
        g.count_family_outcomes([outcome, refusal]),
        refusal.unsupported,
    )


def _values(value):
    if isinstance(value, g.FamilyConfigurationUnsupported):
        return {
            key: getattr(value, key)
            for key in ("reason", "detail", "beneficiary_id", "record_id")
        }
    return {field.name: getattr(value, field.name) for field in fields(value)}


def test_review_altered_age_rate_cannot_lower_savings_clause_protection():
    january, february = _family(), _family(FEB, F("1.20"))
    assert january.record_total == F("1.90")
    assert february.record_total == F("1.80")
    row = january.beneficiaries[0]
    assert row.age_adjusted_rate == row.auxiliary_payable == F("0.40")
    with pytest.raises(g.InvalidFamilyInput):
        replace(row, age_adjusted_rate=F(0))
    guard = g.SavingsClauseGuard(
        JAN,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    outcomes = [
        guard.evaluate("January", 1, lambda: january),
        guard.evaluate("February", 1, lambda: february),
    ]
    assert outcomes[1].unsupported.reason is g.UnsupportedReason.SAVINGS_CLAUSE
    counts = g.count_family_outcomes(outcomes)
    assert (counts.rows, counts.supported_rows, counts.unsupported_rows) == (
        2,
        1,
        1,
    )
    assert guard.protected_total == F("1.90")


@pytest.mark.parametrize("index", range(6))
@pytest.mark.parametrize(
    "operation", ("direct", "copy", "deepcopy", "replace")
)
def test_only_g_computation_can_construct_results(index, operation):
    result = _outputs()[index]
    if operation == "replace" and isinstance(result, Exception):
        return  # Exception is not a dataclass; direct/copy/deepcopy cover it.
    with pytest.raises(g.InvalidFamilyInput):
        if operation == "direct":
            type(result)(**_values(result))
        else:
            {"copy": copy, "deepcopy": deepcopy, "replace": replace}[
                operation
            ](result)


@pytest.mark.parametrize(
    "consumer",
    ("evaluate", "guard", "savings", "household", "count", "sum", "mean"),
)
@pytest.mark.parametrize("altered", (False, True))
def test_every_consumer_rejects_unsealed_or_altered_results(
    consumer, altered, monkeypatch
):
    result = _family()
    if altered:
        object.__setattr__(result.beneficiaries[0], "age_adjusted_rate", F(0))
    else:
        forged = object.__new__(g.FamilyBenefits)
        for key, value in _values(result).items():
            object.__setattr__(forged, key, value)
        result = forged
    guard = g.SavingsClauseGuard(
        JAN,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    before = vars(guard).copy()
    with pytest.raises(g.InvalidFamilyInput):
        if consumer == "evaluate":
            g.evaluate_family("bad", 1, lambda: result)
        elif consumer == "guard":
            guard.evaluate("bad", 1, lambda: result)
        elif consumer == "savings":
            g.savings_clause_total(result)
        elif consumer == "household":
            monkeypatch.setattr(g, "_family_benefits", lambda *args: result)
            g.household_benefits(_records(), payment_month=JAN, params=PARAMS)
        else:
            outcome = g.evaluate_family("bad", 1, _family)
            object.__setattr__(outcome, "benefits", result)
            {
                "count": g.count_family_outcomes,
                "sum": g.weighted_record_total,
                "mean": g.weighted_mean_record_total,
            }[consumer]([outcome])
    assert vars(guard) == before


@settings(max_examples=40, deadline=None, derandomize=True)
@given(st.integers(0, 10000), st.integers(0, 10000))
def test_sealed_accounting_and_serialization_rejection(pia_dimes, room_dimes):
    pia, maximum = F(pia_dimes, 10), F(pia_dimes + room_dimes, 10)
    result = _family(pia=pia, maximum=maximum)
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(result)
    for row in result.beneficiaries:
        assert row.auxiliary_payable == max(
            F(0), row.age_adjusted_rate - (row.own_benefit or 0)
        )
        assert 0 <= row.standard_rate <= row.original_benefit
        assert 0 <= row.family_maximum_rate <= row.original_benefit
    assert result.available_for_auxiliaries == maximum - pia
    assert result.total_original_benefits == sum(
        row.original_benefit for row in result.beneficiaries
    )
    assert result.subject_total == pia + sum(
        row.counted_against_maximum for row in result.beneficiaries
    )
    assert result.family_maximum_binding == (
        result.total_original_benefits > result.available_for_auxiliaries
    )
    assert g.evaluate_family("computed", 1, lambda: result).supported


def test_seal_time_rejects_inconsistent_computed_payable(monkeypatch):
    original = g._reduce_and_offset

    def inconsistent(*args, **kwargs):
        age, payable = original(*args, **kwargs)
        return F(0), payable

    monkeypatch.setattr(g, "_reduce_and_offset", inconsistent)
    with pytest.raises(g.InvalidFamilyInput):
        _family()


@settings(max_examples=40, deadline=None, derandomize=True)
@given(st.integers(0, 1000))
def test_guard_history_is_detached_from_caller_result(extra):
    pia, maximum = F(11 + 2 * extra, 10), F(19 + 4 * extra, 10)
    january = _family(pia=pia, maximum=maximum)
    guard = g.SavingsClauseGuard(
        JAN,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    assert guard.admit(january) is january
    object.__setattr__(january.beneficiaries[0], "age_adjusted_rate", F(0))
    outcome = guard.evaluate(
        "February", 1, lambda: _family(FEB, pia + F("0.10"), maximum)
    )
    assert outcome.unsupported.reason is g.UnsupportedReason.SAVINGS_CLAUSE
    assert guard.protected_total == maximum


@pytest.mark.parametrize("index", range(6))
def test_every_sealed_type_rejects_pickle_without_losing_its_seal(index):
    original = _outputs()[index]
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(original)
    restored = original  # Check the computed value after serialization denial.
    with pytest.raises(g.InvalidFamilyInput):
        copy(restored)
    if isinstance(restored, g.FamilyOutcome):
        assert g.count_family_outcomes([restored]).supported_rows == 1
    if isinstance(restored, g.FamilyConfigurationUnsupported):

        def refuse():
            raise restored

        assert not g.evaluate_family("restored", 1, refuse).supported


@pytest.mark.parametrize("changed", (False, True))
def test_report_witnesses_require_sealed_refusals(monkeypatch, changed):
    from scripts import track_b_g_conformance_report as report

    error = g.evaluate_family("refused", 1, _refuse).unsupported
    if changed:
        error.detail = "caller-altered refusal"
    else:
        fake = g.FamilyConfigurationUnsupported.__new__(
            g.FamilyConfigurationUnsupported
        )
        for key, value in _values(error).items():
            setattr(fake, key, value)
        error = fake

    def refuse():
        raise error

    monkeypatch.setattr(
        report,
        "refusal_witnesses",
        lambda: {
            reason: ("untrusted", refuse) for reason in g.UnsupportedReason
        },
    )
    with pytest.raises(g.InvalidFamilyInput):
        report.execute_refusal_witnesses()


@settings(max_examples=40, deadline=None, derandomize=True)
@given(st.sampled_from(range(6)), st.sampled_from((copy, deepcopy)))
def test_property_public_copy_cannot_create_sealed_outputs(index, duplicate):
    original = _outputs()[index]
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(original)
    restored = original  # Check the computed value after serialization denial.
    with pytest.raises(g.InvalidFamilyInput):
        duplicate(restored)


@settings(max_examples=40, deadline=None, derandomize=True)
@given(st.integers(1, 1000), st.fractions(min_value=F(0), max_value=F(10)))
def test_property_changed_outcome_never_counts_or_advances(extra, weight):
    family = _family()
    outcome = g.evaluate_family("original", weight, lambda: family)
    object.__setattr__(outcome, "weight", weight + extra)
    with pytest.raises(g.InvalidFamilyInput):
        g.count_family_outcomes([outcome])
    guard = g.SavingsClauseGuard(
        JAN,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    before = vars(guard).copy()
    object.__setattr__(family.beneficiaries[0], "age_adjusted_rate", F(0))
    with pytest.raises(g.InvalidFamilyInput):
        guard.evaluate("changed", weight, lambda: family)
    assert vars(guard) == before


@pytest.mark.parametrize(
    "field",
    (
        "available_for_auxiliaries",
        "total_original_benefits",
        "subject_total",
        "record_total",
        "record_total_whole_dollars",
    ),
)
@settings(max_examples=20, deadline=None, derandomize=True)
@given(st.integers(1, 1000))
def test_property_seal_time_reconciles_family_accounting(field, delta):
    values = _values(_family())
    values[field] += delta
    # Exercise the trusted computation's defence independently of the public
    # construction barrier. This private capability is never an input API.
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(g.FamilyBenefits, **values)


@pytest.mark.parametrize(
    "field",
    (
        "standard_rate",
        "family_maximum_rate",
        "counted_against_maximum",
    ),
)
@settings(max_examples=20, deadline=None, derandomize=True)
@given(st.integers(1, 1000))
def test_property_seal_time_bounds_beneficiary_rates(field, delta):
    values = _values(_family().beneficiaries[0])
    values[field] = values["original_benefit"] + delta
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(g.BeneficiaryBenefit, **values)


def test_seal_time_reconciles_binding_and_proportional_rates():
    result = _family()
    values = _values(result)
    values["family_maximum_binding"] = False
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(g.FamilyBenefits, **values)
    values = _values(result)
    values["redistribution_applied"] = True
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(g.FamilyBenefits, **values)
    row_values = _values(result.beneficiaries[0])
    row_values["counted_against_maximum"] = F(0)
    row = g._computed(g.BeneficiaryBenefit, **row_values)
    values = _values(result)
    values["beneficiaries"] = (row, result.beneficiaries[1])
    values["subject_total"] -= F("0.40")
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(g.FamilyBenefits, **values)
    for field in ("standard_rate", "family_maximum_rate"):
        values = _values(result.beneficiaries[0])
        values[field] = F("0.50")  # Valid row bound, wrong maximum share.
        row = g._computed(g.BeneficiaryBenefit, **values)
        values = _values(result)
        values["beneficiaries"] = (row, result.beneficiaries[1])
        with pytest.raises(g.InvalidFamilyInput):
            g._computed(g.FamilyBenefits, **values)


@pytest.mark.parametrize(
    "property_name,index",
    (
        ("total_received", 0),
        ("record_total", 2),
        ("record_total_whole_dollars", 2),
        ("supported", 3),
        ("supported_weight_share", 4),
    ),
)
def test_derived_public_totals_and_status_require_unchanged_seals(
    property_name, index
):
    result = _outputs()[index]
    values = _values(result)
    key = next(iter(values))
    object.__setattr__(result, key, object())
    with pytest.raises(g.InvalidFamilyInput):
        getattr(result, property_name)
