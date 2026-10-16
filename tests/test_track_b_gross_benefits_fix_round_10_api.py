"""The complete G public input boundary rejects malformed declarations.

Verification class: statutory conformance. Invented cases only; no
population, behavioral or forecast claim. Every public name is classified,
every dataclass field and callable argument is enumerated, and Hypothesis
varies the otherwise valid benefits while each corruption is exercised.
"""

from copy import deepcopy
from dataclasses import fields, is_dataclass, replace
from datetime import date
from enum import Enum
from fractions import Fraction as F
from inspect import isclass, isfunction, signature

import pytest
from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.test_track_b_gross_benefits_fix_round_9_validation import (
    CATALOG as INPUT_ERRORS,
)
from tests.track_b_gross_benefit_support import ssa_params

PROPERTY_PHASES = (Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink)
PARAMS = ssa_params()
NOW = g.YearMonth(2023, 12)
MONEY = (True, None, F(-1, 10), float("inf"), float("nan"), [])
OPTIONAL_MONEY = tuple(value for value in MONEY if value is not None)
DIMES = (*MONEY, F(1, 100))
OPTIONAL_DIMES = (*OPTIONAL_MONEY, F(1, 100))
INTEGER = (True, "1", -1)
YEAR = (True, "1940", 0, 10000)
TEXT = (None, 1, "")
BOOL = (None, 0, "true")
OBJECT = (None, True, "invalid")
PERIOD = (True, "60", 59, 61, 86)

# Constants, enum vocabularies and marker exceptions have no domain input
# fields. They are explicitly listed, so adding even one public name forces
# a deliberate test classification instead of silently escaping coverage.
CONSTANTS = {
    "BASE_NAWI_YEAR",
    "DI_MAXIMUM_FIRST_ENTITLEMENT",
    "FAMILY_MAXIMUM_BASE_BEND_POINTS",
    "FAMILY_MAXIMUM_PERCENTS",
    "FIRST_SUPPORTED_DELAYED_CREDIT_BIRTH_YEAR",
    "FIRST_SUPPORTED_ELIGIBILITY_YEAR",
    "FIRST_SUPPORTED_PAYMENT_MONTH",
    "GROSS_BENEFITS_VERSION",
    "PARISI_FIRST_PAYMENT_MONTH",
}
ENUMS = {
    "BeneficiaryCondition",
    "FamilyKind",
    "OwnBenefitKind",
    "RecordCondition",
    "Role",
    "UnsupportedReason",
}
MARKER_ERRORS = {"InvalidFamilyInput", "FamilyTargetBlocked"}

CLASS_ERRORS = {cls.__name__: errors for cls, errors in INPUT_ERRORS.items()}
CLASS_ERRORS.update(
    {
        "StatutoryRates": {
            **{
                name: (True, None, F(-1), F(2), float("inf"))
                for name in (
                    "worker_first",
                    "worker_later",
                    "spouse_first",
                    "spouse_later",
                    "survivor_max_reduction",
                    "rib_lim_share",
                    "spouse_share",
                    "widow_share",
                )
            },
            "worker_bracket_months": (True, "36", 0, -1),
            "spouse_bracket_months": (True, "36", 0, -1),
            "pe_us_revision": TEXT,
        },
        "BeneficiaryBenefit": {
            "beneficiary_id": TEXT,
            "role": (g.FamilyKind.SURVIVOR, "widow"),
            "entitled": BOOL,
            "subject_to_family_maximum": BOOL,
            **{
                name: DIMES
                for name in (
                    "original_benefit",
                    "standard_rate",
                    "family_maximum_rate",
                    "counted_against_maximum",
                    "age_adjusted_rate",
                    "auxiliary_payable",
                )
            },
            "own_benefit": OPTIONAL_DIMES,
            "whole_dollar_auxiliary": INTEGER,
            "whole_dollar_own": INTEGER,
            "note": (None, 1),
        },
        "FamilyBenefits": {
            "kind": (g.OwnBenefitKind.OLD_AGE, "retirement"),
            "payment_month": OBJECT,
            **{
                name: DIMES
                for name in (
                    "pia",
                    "family_maximum",
                    "available_for_auxiliaries",
                    "total_original_benefits",
                    "record_total",
                    "subject_total",
                )
            },
            "family_maximum_binding": BOOL,
            "redistribution_applied": BOOL,
            "worker_benefit": OPTIONAL_DIMES,
            "whole_dollar_worker": INTEGER,
            "beneficiaries": (None, "invalid", (None,)),
            "record_total_whole_dollars": INTEGER,
            "state_source": TEXT,
            "pe_us_revision": TEXT,
            "version": TEXT,
        },
        "HouseholdBenefits": {
            "payment_month": OBJECT,
            "records": (None, [], {"record": None}, {1: None}),
        },
        "FamilyOutcome": {
            "key": TEXT,
            "weight": MONEY,
            "benefits": (None, True, "invalid"),
            "unsupported": (
                True,
                "invalid",
                g.UnsupportedReason.SAVINGS_CLAUSE,
            ),
        },
        "FamilyDenominator": {
            "rows": INTEGER,
            "weight": MONEY,
            "supported_rows": INTEGER,
            "supported_weight": MONEY,
            "unsupported_rows": INTEGER,
            "unsupported_weight": MONEY,
            "unsupported_by_reason": (
                None,
                [],
                {"savings_clause_403a5": (1, F(1))},
                {g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET: (1, F(1))},
                {g.UnsupportedReason.SAVINGS_CLAUSE: (True, F(1))},
                {g.UnsupportedReason.SAVINGS_CLAUSE: (1, F(-1))},
            ),
        },
        "FamilyConfigurationUnsupported": {
            "reason": (
                None,
                "savings_clause_403a5",
                g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET,
            ),
            "detail": TEXT,
            "beneficiary_id": (True, 1, ""),
            "record_id": (True, 1, ""),
        },
        "SavingsClauseGuard": {
            "first_month": OBJECT,
            "earlier_months_unknown": BOOL,
        },
    }
)

# These are argument names, not introspected/generated coverage: a new
# argument must receive both a valid seed and deliberate corrupt probes.
FUNCTION_ARGUMENTS = {
    "applicable_cola_percents": (
        "eligibility_year",
        "payment_month",
        "december_cola_percent",
    ),
    "ceil_dime": ("amount",),
    "check_household_records": ("records",),
    "count_family_outcomes": ("outcomes",),
    "delayed_credit_window_months": ("birth_year", "params"),
    "disability_family_maximum": ("pia", "aime"),
    "evaluate_family": ("key", "weight", "compute"),
    "family_benefits": (
        "state",
        "beneficiaries",
        "payment_month",
        "params",
        "standalone",
    ),
    "family_maximum_bend_points": ("eligibility_year", "params"),
    "family_maximum_formula": ("pia", "eligibility_year", "params"),
    "floor_dime": ("amount",),
    "household_benefits": ("records", "payment_month", "params"),
    "household_month_outcome": (
        "records",
        "payment_month",
        "params",
        "guards",
        "key",
        "weight",
    ),
    "increase_by_colas": ("amount", "percents"),
    "original_benefit": ("role", "kind", "pia", "basis", "parent_count"),
    "maximum_redistribution_rates": (
        "original_benefits",
        "available",
        "deductee_payables",
        "age_reductions",
        "other_deductions",
    ),
    "own_monthly_benefit": ("own", "params"),
    "record_state": ("record", "params"),
    "retirement_survivor_family_maximum": (
        "pia",
        "eligibility_year",
        "params",
    ),
    "savings_clause_total": ("result",),
    "spouse_age_reduced": ("amount", "reduction_months", "params"),
    "spouse_reduction_fraction": ("months", "params"),
    "statutory_rates": ("params",),
    "survivor_reduction_fraction": (
        "months",
        "reduction_period_months",
        "params",
    ),
    "survivor_age_reduced": (
        "amount",
        "reduction_months",
        "reduction_period_months",
        "params",
    ),
    "weighted_mean_record_total": ("outcomes",),
    "weighted_record_total": ("outcomes",),
    "whole_dollars": ("amount",),
    "widow_reduction_period_months": ("birth_date",),
    "worker_age_adjusted": (
        "pia",
        "reduction_months",
        "delayed_credit_months",
        "birth_year",
        "params",
    ),
    "worker_reduction_fraction": ("months", "params"),
}
READ_MEMBERS = {
    "YearMonth": {"as_tuple"},
    "BeneficiaryBenefit": {"total_received"},
    "FamilyBenefits": {"by_id"},
    "HouseholdBenefits": {"record_total", "record_total_whole_dollars"},
    "FamilyOutcome": {"supported"},
    "FamilyDenominator": {"supported_weight_share"},
    "SavingsClauseGuard": {
        "next_month",
        "protected_total",
        "protected_since",
        "refused_since",
        "unknown_since",
    },
}


METHOD_ARGUMENTS = {
    "admit": ("result",),
    "skip": ("month", "pia"),
    "evaluate": ("key", "weight", "compute", "pia"),
}


def _argument_errors(function, argument):
    if argument == "amount" and function in ("ceil_dime", "floor_dime"):
        # Signed intermediate arithmetic is part of these rounding helpers.
        return (True, None, [], float("inf"), float("nan"))
    if argument == "amount" and function == "whole_dollars":
        return MONEY
    if argument == "pia" and function in ("skip", "evaluate"):
        return OPTIONAL_DIMES
    if argument in ("pia", "amount", "available"):
        return DIMES
    if argument == "basis":
        return OPTIONAL_DIMES
    if argument == "weight":
        return MONEY
    if argument in ("eligibility_year", "birth_year"):
        return YEAR
    if argument in ("months", "reduction_months", "delayed_credit_months"):
        return (True, "1", -1, 85)
    if argument == "reduction_period_months":
        return PERIOD
    if argument == "aime":
        return (True, None, F(-1), F(1, 2), float("inf"))
    if argument == "parent_count":
        return (True, "1", 0, 3)
    if argument == "role":
        return (g.FamilyKind.SURVIVOR, "widow", None)
    if argument == "kind":
        return (g.OwnBenefitKind.OLD_AGE, "survivor", None)
    if argument == "standalone":
        return (None, 1, "true", False)
    if argument == "key":
        return TEXT
    if argument == "percents":
        return (None, True, "2.8", (True,), (F(-1),), (float("inf"),))
    if argument == "december_cola_percent":
        return (
            None,
            [],
            {True: F(0)},
            {2002: F(-1)},
            {2002: True},
            {2002: float("inf")},
        )
    if argument in (
        "original_benefits",
        "deductee_payables",
        "age_reductions",
        "other_deductions",
    ):
        optional = argument in ("age_reductions", "other_deductions")
        values = (
            [],
            True,
            {1: F(0)},
            {"auxiliary": True},
            {"auxiliary": F(-1)},
            {"auxiliary": float("inf")},
        )
        return values if optional else (None, *values)
    if argument == "outcomes":
        return (None, True, "outcome", (None,), (g.FamilyKind.RETIREMENT,))
    if argument == "records":
        return (None, [], {"record": None}, {1: None})
    if argument == "guards":
        return (None, [], {"record": None})
    if argument == "beneficiaries":
        return (None, "auxiliary", (None,))
    if argument in (
        "state",
        "own",
        "record",
        "result",
        "params",
        "compute",
        "payment_month",
        "month",
        "birth_date",
    ):
        return OBJECT
    raise AssertionError((function, argument))


CLASS_CASES = [
    pytest.param(name, field_name, bad, id=f"{name}.{field_name}-{index}")
    for name, catalog in CLASS_ERRORS.items()
    for field_name, values in catalog.items()
    for index, bad in enumerate(values)
]
CALL_CASES = [
    pytest.param(name, argument, bad, id=f"{name}.{argument}-{index}")
    for name, arguments in {**FUNCTION_ARGUMENTS, **METHOD_ARGUMENTS}.items()
    for argument in arguments
    for index, bad in enumerate(_argument_errors(name, argument))
]


def _world(pia):
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(pia), birth_year=1940)
    worker = g.WorkerRecord(
        g.FamilyKind.RETIREMENT, 2002, F(pia), worker_birth_year=1940
    )
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(pia),
        F(pia * 2),
        worker=own,
        eligibility_year=2002,
    )
    beneficiary = g.Beneficiary("auxiliary", g.Role.SPOUSE, birth_year=1940)
    household_record = g.HouseholdRecord("worker", state, (beneficiary,))
    result = g.family_benefits(
        state,
        (beneficiary,),
        payment_month=NOW,
        params=PARAMS,
        standalone=True,
    )
    household = g.household_benefits(
        {"record": household_record}, payment_month=NOW, params=PARAMS
    )
    outcome = g.evaluate_family("valid", F(7, 3), lambda: result)
    objects = {
        "YearMonth": NOW,
        "StatutoryRates": g.statutory_rates(PARAMS),
        "OwnBenefit": own,
        "Beneficiary": beneficiary,
        "WorkerRecord": worker,
        "RecordState": state,
        "BeneficiaryBenefit": result.beneficiaries[0],
        "FamilyBenefits": result,
        "HouseholdRecord": household_record,
        "HouseholdBenefits": household,
        "FamilyOutcome": outcome,
        "FamilyDenominator": g.count_family_outcomes((outcome,)),
    }
    guard = g.SavingsClauseGuard(NOW, earlier_months_unknown=False)
    arguments = {
        "amount": F(pia),
        "pia": F(pia),
        "available": F(pia),
        "eligibility_year": 2002,
        "birth_year": 1940,
        "months": 12,
        "reduction_months": 12,
        "delayed_credit_months": 0,
        "reduction_period_months": 62,
        "aime": pia,
        "parent_count": None,
        "role": g.Role.WIDOW,
        "kind": g.FamilyKind.SURVIVOR,
        "basis": None,
        "params": PARAMS,
        "standalone": True,
        "key": "valid",
        "weight": F(7, 3),
        "percents": (F(0), F(2)),
        "december_cola_percent": {year: F(0) for year in range(2002, 2024)},
        "payment_month": NOW,
        "month": NOW,
        "birth_date": date(1940, 1, 2),
        "original_benefits": {"auxiliary": F(pia)},
        "deductee_payables": {},
        "age_reductions": {},
        "other_deductions": {},
        "outcomes": (outcome,),
        "records": {"record": household_record},
        "guards": {"record": guard},
        "state": state,
        "beneficiaries": (beneficiary,),
        "own": own,
        "record": worker,
        "result": result,
        "compute": lambda: result,
    }
    return objects, arguments, guard


def _assert_invalid_and_atomic(call, guard):
    before = deepcopy(guard.__dict__)
    emitted = []
    with pytest.raises(g.InvalidFamilyInput):
        emitted.append(call())
    assert emitted == []
    denominator = g.count_family_outcomes(emitted)
    assert (
        denominator.rows
        == denominator.supported_rows
        == denominator.unsupported_rows
        == 0
    )
    assert (
        denominator.weight
        == denominator.supported_weight
        == denominator.unsupported_weight
        == 0
    )
    assert denominator.unsupported_by_reason == {}
    assert guard.__dict__ == before


def test_public_api_has_no_unclassified_name_field_or_argument():
    classified = (
        CONSTANTS
        | ENUMS
        | MARKER_ERRORS
        | set(CLASS_ERRORS)
        | set(FUNCTION_ARGUMENTS)
    )
    assert len(g.__all__) == len(set(g.__all__))
    assert set(g.__all__) == classified
    assert {name for name in g.__all__ if isfunction(getattr(g, name))} == set(
        FUNCTION_ARGUMENTS
    )
    assert {
        name
        for name in g.__all__
        if isclass(getattr(g, name)) and issubclass(getattr(g, name), Enum)
    } == ENUMS
    for name, catalog in CLASS_ERRORS.items():
        cls = getattr(g, name)
        if is_dataclass(cls):
            assert set(catalog) == {item.name for item in fields(cls)}, name
        assert set(catalog) == set(signature(cls).parameters), name
    objects, _, guard = _world(100)
    objects["SavingsClauseGuard"] = guard
    for name in CLASS_ERRORS:
        cls = getattr(g, name)
        members = {
            member_name
            for member_name, value in vars(cls).items()
            if not member_name.startswith("_")
            and (isfunction(value) or isinstance(value, property))
        }
        expected = READ_MEMBERS.get(name, set())
        if name == "SavingsClauseGuard":
            expected = expected | set(METHOD_ARGUMENTS)
        assert members == expected, name
        for member_name in READ_MEMBERS.get(name, ()):
            value = getattr(objects[name], member_name)
            if callable(value):
                value()
    for name, arguments in FUNCTION_ARGUMENTS.items():
        assert set(signature(getattr(g, name)).parameters) == set(
            arguments
        ), name
    assert {
        name
        for name, value in vars(g.SavingsClauseGuard).items()
        if not name.startswith("_") and isfunction(value)
    } == set(METHOD_ARGUMENTS)
    for name, arguments in METHOD_ARGUMENTS.items():
        assert set(
            signature(getattr(g.SavingsClauseGuard, name)).parameters
        ) == {"self", *arguments}, name


@pytest.mark.parametrize("name,field_name,bad", CLASS_CASES)
@settings(max_examples=3, deadline=None, phases=PROPERTY_PHASES)
@given(pia=st.integers(1, 2000))
def test_every_public_constructor_field_rejects_corruption(
    name, field_name, bad, pia
):
    objects, _, guard = _world(pia)

    def construct():
        if name == "FamilyConfigurationUnsupported":
            arguments = dict(
                reason=g.UnsupportedReason.SAVINGS_CLAUSE,
                detail="invented refusal",
                beneficiary_id=None,
                record_id=None,
            )
            arguments[field_name] = deepcopy(bad)
            return g.FamilyConfigurationUnsupported(**arguments)
        if name == "SavingsClauseGuard":
            arguments = dict(first_month=NOW, earlier_months_unknown=False)
            arguments[field_name] = deepcopy(bad)
            return g.SavingsClauseGuard(**arguments)
        return replace(objects[name], **{field_name: deepcopy(bad)})

    _assert_invalid_and_atomic(construct, guard)


@pytest.mark.parametrize("name,argument,bad", CALL_CASES)
@settings(max_examples=3, deadline=None, phases=PROPERTY_PHASES)
@given(pia=st.integers(1, 2000))
def test_every_public_argument_rejects_corruption_before_output(
    name, argument, bad, pia
):
    _, values, guard = _world(pia)
    names = (
        METHOD_ARGUMENTS[name]
        if name in METHOD_ARGUMENTS
        else FUNCTION_ARGUMENTS[name]
    )
    arguments = {key: values[key] for key in names}
    arguments[argument] = deepcopy(bad)
    call = (
        getattr(guard, name) if name in METHOD_ARGUMENTS else getattr(g, name)
    )
    _assert_invalid_and_atomic(lambda: call(**arguments), guard)


@pytest.mark.parametrize(
    "name", tuple(FUNCTION_ARGUMENTS) + tuple(METHOD_ARGUMENTS)
)
@settings(max_examples=5, deadline=None, phases=PROPERTY_PHASES)
@given(pia=st.integers(1, 2000))
def test_public_argument_properties_start_from_valid_calls(name, pia):
    _, values, guard = _world(pia)
    names = (
        METHOD_ARGUMENTS[name]
        if name in METHOD_ARGUMENTS
        else FUNCTION_ARGUMENTS[name]
    )
    call = (
        getattr(guard, name) if name in METHOD_ARGUMENTS else getattr(g, name)
    )
    call(**{key: values[key] for key in names})
