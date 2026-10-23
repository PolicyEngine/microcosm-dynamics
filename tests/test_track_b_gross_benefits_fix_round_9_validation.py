"""Malformed public inputs never enter statutory coverage denominators.

Verification class: statutory conformance. Invented cases only; no
population, behavioral or forecast claim. Frozen objects are deliberately
corrupted after construction to exercise every public entry point's own
validation, independently of constructor checks.
"""

from copy import deepcopy
from dataclasses import fields, replace
from fractions import Fraction as F
from functools import partial

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2023, 12)
WEIGHT = F(7, 3)
ROUTES = (
    "direct",
    "built",
    "household-direct",
    "household-built",
    "guarded-direct",
    "guarded-built",
)


def _assert_invalid(compute, guards, *, guarded=False):
    before = {key: deepcopy(guard.__dict__) for key, guard in guards.items()}
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(
            compute()
            if guarded
            else g.evaluate_family("invalid", WEIGHT, compute)
        )
    assert not outcomes
    counts = g.count_family_outcomes(outcomes)
    assert counts.rows == counts.unsupported_rows == 0
    assert counts.weight == counts.unsupported_weight == 0
    assert counts.unsupported_by_reason == {}
    assert {key: guard.__dict__ for key, guard in guards.items()} == before


def _run(state, beneficiaries, route, guards, *, month=NOW):
    if route in ("direct", "built"):
        return g.family_benefits(
            state,
            beneficiaries,
            payment_month=month,
            params=PARAMS,
            standalone=True,
        )
    records = {
        "record": g.HouseholdRecord("worker", state, beneficiaries),
    }
    if route.startswith("guarded"):
        return g.household_month_outcome(
            records,
            payment_month=month,
            params=PARAMS,
            guards=guards,
            weight=WEIGHT,
        )
    return g.household_benefits(records, payment_month=month, params=PARAMS)


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("malformation", ("mixed-conditions", "bool-cohort"))
def test_review_malformed_inputs_precede_refusal_and_guard(
    route, malformation
):
    guards = {
        "record": g.SavingsClauseGuard(
            NOW,
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        ),
    }

    def compute():
        kind = (
            g.FamilyKind.RETIREMENT
            if malformation == "mixed-conditions"
            else g.FamilyKind.SURVIVOR
        )
        conditions = {g.RecordCondition.ADMINISTRATIVE_FINALITY}
        if malformation == "mixed-conditions":
            conditions.add(g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET)
        if route.endswith("built") or route == "built":
            state = g.record_state(
                g.WorkerRecord(kind, 1983, F(0), conditions=conditions),
                PARAMS,
            )
        else:
            state = g.RecordState(
                kind,
                F(0),
                F(0),
                worker=(
                    g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(0))
                    if kind is g.FamilyKind.RETIREMENT
                    else None
                ),
                eligibility_year=1983,
                conditions=conditions,
            )
        beneficiaries = (
            (g.Beneficiary("widow", g.Role.WIDOW, birth_year=True),)
            if malformation == "bool-cohort"
            else ()
        )
        return _run(state, beneficiaries, route, guards)

    _assert_invalid(compute, guards, guarded=route.startswith("guarded"))


# Every public input field has malformed probes. Each parameter case is a
# Hypothesis property over otherwise valid invented families; parameterizing
# the field and corrupt value prevents random sampling from missing a field.
MONEY_ERRORS = (True, None, F(-1, 10), F(1, 100), float("inf"))
OPTIONAL_MONEY_ERRORS = (True, F(-1, 10), F(1, 100), float("inf"))
YEAR_ERRORS = (True, "1940", 0, 10000)
MONTH_COUNT_ERRORS = (True, "1", -1, 85)
CATALOG = {
    g.YearMonth: {
        "year": YEAR_ERRORS,
        "month": (True, "12", 0, 13),
    },
    g.OwnBenefit: {
        "kind": (g.FamilyKind.RETIREMENT, "old_age"),
        "pia": MONEY_ERRORS,
        "reduction_months": (True, "1", -1, 61),
        "delayed_credit_months": MONTH_COUNT_ERRORS,
        "birth_year": YEAR_ERRORS,
    },
    g.Beneficiary: {
        "beneficiary_id": ("", 1),
        "role": (g.FamilyKind.SURVIVOR, "widow"),
        "reduction_months": MONTH_COUNT_ERRORS,
        "reduction_period_months": (True, "60", 59, 61, 86),
        "original_benefit_basis": OPTIONAL_MONEY_ERRORS,
        "own_benefit": ("own", 1),
        "own_benefit_first": (1, "yes"),
        "birth_year": YEAR_ERRORS,
        "conditions": (
            None,
            frozenset({g.RecordCondition.ADMINISTRATIVE_FINALITY}),
            frozenset({"government_pension_offset"}),
        ),
        "child_in_care": (True, 1, ""),
        "first_entitlement_child_in_care": (1, "yes"),
    },
    g.WorkerRecord: {
        "kind": (g.OwnBenefitKind.OLD_AGE, "retirement"),
        "eligibility_year": YEAR_ERRORS,
        "eligibility_pia": MONEY_ERRORS,
        "cola_percents": (None, (True,), (F(-1),), (float("inf"),)),
        "aime": (True, "1000", -1, F(1, 2)),
        "first_dib_entitlement": (True, "1983-01"),
        "worker_reduction_months": (True, "1", -1, 61),
        "worker_delayed_credit_months": MONTH_COUNT_ERRORS,
        "worker_birth_year": YEAR_ERRORS,
        "rib_lim_benefit": OPTIONAL_MONEY_ERRORS,
        "conditions": (
            None,
            frozenset({g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET}),
            frozenset({"administrative_finality"}),
        ),
    },
    g.RecordState: {
        "kind": (g.OwnBenefitKind.OLD_AGE, "retirement"),
        "pia": MONEY_ERRORS,
        "family_maximum": MONEY_ERRORS,
        "worker": (None, "worker"),
        "rib_lim_benefit": OPTIONAL_MONEY_ERRORS,
        "conditions": (
            None,
            frozenset({g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET}),
            frozenset({"administrative_finality"}),
        ),
        "source": (None, 1),
        "eligibility_year": YEAR_ERRORS,
        "first_dib_entitlement": (True, "1983-01"),
        "deferred_refusal": (
            (),
            (g.RecordCondition.ADMINISTRATIVE_FINALITY, "detail"),
            (g.UnsupportedReason.ADMINISTRATIVE_FINALITY, 1),
            ("administrative_finality", "detail"),
        ),
        "widow_drc_savings_clause": (1, "yes"),
        "worker_birth_year": YEAR_ERRORS,
    },
    g.HouseholdRecord: {
        "worker_id": ("", 1),
        "state": (None, "state"),
        "beneficiaries": (None, ("beneficiary",)),
    },
}
FIELD_CASES = [
    pytest.param(cls, name, bad, id=f"{cls.__name__}.{name}-{index}")
    for cls, catalog in CATALOG.items()
    for name, values in catalog.items()
    for index, bad in enumerate(values)
]


def test_malformed_catalog_covers_every_public_input_dataclass_field():
    for cls, catalog in CATALOG.items():
        assert set(catalog) == {item.name for item in fields(cls)}


def _valid_inputs(pia, cohort, refusing, *, survivor=False):
    kind = g.FamilyKind.SURVIVOR if survivor else g.FamilyKind.RETIREMENT
    conditions = (
        frozenset({g.RecordCondition.ADMINISTRATIVE_FINALITY})
        if refusing
        else frozenset()
    )
    record = g.WorkerRecord(
        kind,
        cohort + 62,
        F(pia),
        worker_birth_year=cohort,
        conditions=conditions,
    )
    state = g.RecordState(
        kind,
        F(pia),
        g.retirement_survivor_family_maximum(F(pia), cohort + 62, PARAMS),
        worker=(
            None
            if survivor
            else g.OwnBenefit(
                g.OwnBenefitKind.OLD_AGE, F(pia), birth_year=cohort
            )
        ),
        conditions=conditions,
        eligibility_year=cohort + 62,
        worker_birth_year=cohort,
    )
    beneficiary = g.Beneficiary(
        "auxiliary",
        g.Role.WIDOW if survivor else g.Role.SPOUSE,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F(pia // 10), birth_year=cohort
        ),
        own_benefit_first=True,
        birth_year=cohort,
        child_in_care=False if survivor else None,
    )
    return record, state, beneficiary


def _applicable_routes(cls):
    routes = ROUTES
    if cls is g.WorkerRecord:
        routes = tuple(route for route in routes if route.endswith("built"))
    if cls is g.HouseholdRecord:
        routes = tuple(route for route in routes if "-" in route)
    return routes


def _corrupted_computation(
    cls, name, bad, route, guards, pia, cohort, refusing
):
    record, state, beneficiary = _valid_inputs(
        pia, cohort, refusing, survivor=cls is g.Beneficiary
    )
    if cls is g.WorkerRecord:
        object.__setattr__(record, name, deepcopy(bad))
    if route.endswith("built"):
        state = g.record_state(record, PARAMS)
    household = g.HouseholdRecord("worker", state, (beneficiary,))
    if route not in ("direct", "built"):
        state = household.state
        beneficiary = household.beneficiaries[0]
    month = g.YearMonth(2023, 12)
    target = {
        g.YearMonth: month,
        g.RecordState: state,
        g.WorkerRecord: record,
        g.Beneficiary: beneficiary,
        g.OwnBenefit: state.worker,
        g.HouseholdRecord: household,
    }[cls]
    if cls is not g.WorkerRecord:
        object.__setattr__(target, name, deepcopy(bad))
    if route in ("direct", "built"):
        return g.family_benefits(
            state,
            (beneficiary,),
            payment_month=month,
            params=PARAMS,
            standalone=True,
        )
    records = {"record": household}
    if route.startswith("guarded"):
        return g.household_month_outcome(
            records,
            payment_month=month,
            params=PARAMS,
            guards=guards,
            weight=WEIGHT,
        )
    return g.household_benefits(records, payment_month=month, params=PARAMS)


def _assert_constructor_rejects(cls, name, bad, pia, cohort):
    # Global/cohort upper bounds intentionally belong to family validation;
    # existing callers may construct an unresolved month count first.
    if name in ("reduction_months", "worker_reduction_months") and (
        type(bad) is int and bad > 0
    ):
        return
    record, state, beneficiary = _valid_inputs(
        pia, cohort, False, survivor=cls is g.Beneficiary
    )
    target = {
        g.YearMonth: NOW,
        g.RecordState: state,
        g.WorkerRecord: record,
        g.Beneficiary: beneficiary,
        g.OwnBenefit: state.worker,
        g.HouseholdRecord: g.HouseholdRecord("worker", state, (beneficiary,)),
    }[cls]
    with pytest.raises(g.InvalidFamilyInput):
        replace(target, **{name: deepcopy(bad)})


@pytest.mark.parametrize("cls,name,bad", FIELD_CASES)
@settings(max_examples=6, deadline=None)
@given(pia=st.integers(0, 2000), cohort=st.integers(1929, 1955))
def test_malformed_field_never_counts_or_advances_any_entry(
    cls, name, bad, pia, cohort
):
    _assert_constructor_rejects(cls, name, bad, pia, cohort)
    for refusing in (False, True):
        for route in _applicable_routes(cls):
            guards = {
                "record": g.SavingsClauseGuard(
                    NOW,
                    earlier_months_unknown=False,
                    reading=g.SavingsClauseReading.LITERAL_REFUSAL,
                ),
            }
            _assert_invalid(
                partial(
                    _corrupted_computation,
                    cls,
                    name,
                    bad,
                    route,
                    guards,
                    pia,
                    cohort,
                    refusing,
                ),
                guards,
                guarded=route.startswith("guarded"),
            )


@settings(max_examples=25, deadline=None)
@given(pia=st.integers(0, 2000), cohort=st.integers(1929, 1955))
def test_malformed_property_starts_from_supported_families(pia, cohort):
    for survivor in (False, True):
        record, state, beneficiary = _valid_inputs(
            pia, cohort, False, survivor=survivor
        )
        for candidate in (state, g.record_state(record, PARAMS)):
            outcome = g.evaluate_family(
                "valid",
                WEIGHT,
                partial(
                    g.family_benefits,
                    candidate,
                    (beneficiary,),
                    payment_month=NOW,
                    params=PARAMS,
                    standalone=True,
                ),
            )
            assert outcome.supported


@pytest.mark.parametrize(
    "first_month,unknown",
    ((None, False), ("2023-12", False), (NOW, 0), (NOW, 1), (NOW, None)),
)
def test_guard_constructor_rejects_malformed_public_arguments(
    first_month, unknown
):
    with pytest.raises(g.InvalidFamilyInput):
        g.SavingsClauseGuard(
            first_month,
            earlier_months_unknown=unknown,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        )


@pytest.mark.parametrize("name,bad", (("year", True), ("month", 13)))
def test_guard_revalidates_nested_first_month(name, bad):
    first = g.YearMonth(2023, 12)
    object.__setattr__(first, name, bad)
    with pytest.raises(g.InvalidFamilyInput):
        g.SavingsClauseGuard(
            first,
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        )


CROSS_FIELD_CASES = (
    "maximum-below-pia",
    "worker-pia-differs",
    "worker-cohort-differs",
    "retirement-eligibility-after-age-62",
    "first-dib-after-payment",
    "own-cohort-differs",
    "widow-period-differs-from-cohort",
    "widow-reduced-without-period",
    "widow-basis-below-pia",
    "child-care-id-missing",
    "first-care-on-widow",
    "spouse-order-missing",
    "duplicate-beneficiary",
    "worker-is-beneficiary",
)


def _cross_field_computation(case, route, guards, pia, cohort):
    survivor = case in {
        "own-cohort-differs",
        "widow-period-differs-from-cohort",
        "widow-reduced-without-period",
        "widow-basis-below-pia",
        "child-care-id-missing",
        "first-care-on-widow",
    }
    record, state, beneficiary = _valid_inputs(
        pia, cohort, True, survivor=survivor
    )
    if route.endswith("built"):
        state = g.record_state(record, PARAMS)
    household = g.HouseholdRecord("worker", state, (beneficiary,))
    if route not in ("direct", "built"):
        state = household.state
        beneficiary = household.beneficiaries[0]
    members = (beneficiary,)
    if case == "maximum-below-pia":
        object.__setattr__(state, "family_maximum", state.pia - F(1, 10))
    elif case == "worker-pia-differs":
        object.__setattr__(state.worker, "pia", state.pia + 1)
    elif case == "worker-cohort-differs":
        object.__setattr__(state, "worker_birth_year", cohort + 1)
    elif case == "retirement-eligibility-after-age-62":
        object.__setattr__(state, "eligibility_year", cohort + 63)
    elif case == "first-dib-after-payment":
        object.__setattr__(
            state, "first_dib_entitlement", g.YearMonth(2024, 1)
        )
    elif case == "own-cohort-differs":
        object.__setattr__(beneficiary.own_benefit, "birth_year", cohort + 1)
    elif case == "widow-period-differs-from-cohort":
        object.__setattr__(
            beneficiary,
            "reduction_period_months",
            84 if cohort <= 1939 else 60,
        )
    elif case == "widow-reduced-without-period":
        object.__setattr__(beneficiary, "reduction_months", 1)
    elif case == "widow-basis-below-pia":
        object.__setattr__(
            beneficiary, "original_benefit_basis", state.pia - 1
        )
    elif case == "child-care-id-missing":
        object.__setattr__(beneficiary, "child_in_care", "missing-child")
    elif case == "first-care-on-widow":
        object.__setattr__(
            beneficiary, "first_entitlement_child_in_care", False
        )
    elif case == "spouse-order-missing":
        object.__setattr__(beneficiary, "own_benefit_first", None)
    elif case == "duplicate-beneficiary":
        members = (beneficiary, beneficiary)
        object.__setattr__(household, "beneficiaries", members)
    elif case == "worker-is-beneficiary":
        object.__setattr__(household, "worker_id", beneficiary.beneficiary_id)
    else:
        raise AssertionError(case)
    if route in ("direct", "built"):
        return g.family_benefits(
            state, members, payment_month=NOW, params=PARAMS, standalone=True
        )
    records = {"record": household}
    if route.startswith("guarded"):
        return g.household_month_outcome(
            records,
            payment_month=NOW,
            params=PARAMS,
            guards=guards,
            weight=WEIGHT,
        )
    return g.household_benefits(records, payment_month=NOW, params=PARAMS)


@pytest.mark.parametrize("case", CROSS_FIELD_CASES)
@settings(max_examples=6, deadline=None)
@given(pia=st.integers(1, 2000), cohort=st.integers(1929, 1955))
def test_cross_field_errors_precede_refusal_in_every_entry(case, pia, cohort):
    routes = (
        tuple(route for route in ROUTES if "-" in route)
        if case == "worker-is-beneficiary"
        else ROUTES
    )
    for route in routes:
        guards = {
            "record": g.SavingsClauseGuard(
                NOW,
                earlier_months_unknown=False,
                reading=g.SavingsClauseReading.LITERAL_REFUSAL,
            ),
        }
        _assert_invalid(
            partial(
                _cross_field_computation, case, route, guards, pia, cohort
            ),
            guards,
            guarded=route.startswith("guarded"),
        )


@pytest.mark.parametrize("refusing", (False, True))
@pytest.mark.parametrize("route", ("guard", "household"))
def test_terminal_calendar_month_errors_leave_every_guard_unchanged(
    refusing, route
):
    month = g.YearMonth(9999, 12)
    guard = g.SavingsClauseGuard(
        month,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    _, state, beneficiary = _valid_inputs(1000, 1940, refusing)
    guards = {"record": guard}

    def family():
        return g.family_benefits(
            state,
            (beneficiary,),
            payment_month=month,
            params=PARAMS,
            standalone=True,
        )

    def compute():
        if route == "guard":
            return guard.evaluate("invalid", WEIGHT, family, pia=state.pia)
        return g.household_month_outcome(
            {"record": g.HouseholdRecord("worker", state, (beneficiary,))},
            payment_month=month,
            params=PARAMS,
            guards=guards,
            weight=WEIGHT,
        )

    _assert_invalid(compute, guards, guarded=True)


def test_child_care_reference_requires_exact_string_type():
    class TextSubclass(str):
        pass

    with pytest.raises(g.InvalidFamilyInput):
        g.Beneficiary(
            "widow", g.Role.WIDOW, child_in_care=TextSubclass("child")
        )
