"""Every G entry point validates the same supplied family information.

Verification class: statutory conformance. Invented cases only, admitting
no population, behavioral or forecast claim. All comparisons are exact;
the only discarded result field is diagnostic construction provenance.
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
ROUTES = ("direct", "built", "household", "household-month-outcome")


def _unclaimed(*, pia=F(1000), eligibility=1998, built=False):
    fields = dict(
        kind=g.FamilyKind.RETIREMENT,
        eligibility_year=eligibility,
        worker_birth_year=1935,
        conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
    )
    if built:
        return g.record_state(
            g.WorkerRecord(eligibility_pia=pia, **fields), PARAMS
        )
    return g.RecordState(pia=pia, family_maximum=pia * F(3, 2), **fields)


def _gpo_divorced_spouse():
    return g.Beneficiary(
        "spouse",
        g.Role.DIVORCED_SPOUSE,
        conditions={g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET},
    )


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("pia", (F(0), F(1000)))
def test_review_unclaimed_eligibility_error_precedes_gpo_and_guard(route, pia):
    guard = g.SavingsClauseGuard(NOW, earlier_months_unknown=False)
    with pytest.raises(
        g.InvalidFamilyInput, match="eligibility_year exceeds birth year"
    ):
        state = _unclaimed(pia=pia, built=route == "built")
        members = (_gpo_divorced_spouse(),)
        if route in ("direct", "built"):
            g.evaluate_family(
                "invalid",
                WEIGHT,
                lambda: g.family_benefits(
                    state,
                    members,
                    payment_month=NOW,
                    params=PARAMS,
                    standalone=True,
                ),
            )
        else:
            records = {"record": g.HouseholdRecord("worker", state, members)}
            if route == "household":
                g.household_benefits(records, payment_month=NOW, params=PARAMS)
            else:
                g.household_month_outcome(
                    records,
                    payment_month=NOW,
                    params=PARAMS,
                    guards={"record": guard},
                    weight=WEIGHT,
                )
    assert guard.next_month == NOW


@pytest.mark.parametrize("built", (False, True))
def test_valid_unclaimed_eligibility_gpo_stays_in_denominator(built):
    state = _unclaimed(eligibility=1997, built=built)
    guard = g.SavingsClauseGuard(NOW, earlier_months_unknown=False)
    outcome = g.household_month_outcome(
        {
            "record": g.HouseholdRecord(
                "worker", state, [_gpo_divorced_spouse()]
            )
        },
        payment_month=NOW,
        params=PARAMS,
        guards={"record": guard},
        weight=WEIGHT,
    )
    counts = g.count_family_outcomes([outcome])
    assert counts.unsupported_by_reason == {
        g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET: (1, WEIGHT)
    }
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == WEIGHT
    assert guard.next_month == g.YearMonth(2024, 1)


def _direct_state(record):
    """Construct the same dated snapshot without calling record_state."""
    pia = g.increase_by_colas(record.eligibility_pia, record.cola_percents)
    # Historical maxima are outside coverage. Match the builder's harmless
    # sentinel so family validation and the shared refusal order still run.
    base_maximum = (
        record.eligibility_pia
        if record.eligibility_year < g.FIRST_SUPPORTED_ELIGIBILITY_YEAR
        else g.retirement_survivor_family_maximum(
            record.eligibility_pia, record.eligibility_year, PARAMS
        )
    )
    maximum = g.increase_by_colas(
        base_maximum,
        record.cola_percents,
    )
    worker = None
    if record.kind is g.FamilyKind.RETIREMENT and (
        g.RecordCondition.WORKER_NOT_ENTITLED not in record.conditions
    ):
        worker = g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            pia,
            reduction_months=record.worker_reduction_months,
            birth_year=record.worker_birth_year,
        )
    return g.RecordState(
        record.kind,
        pia,
        maximum,
        worker=worker,
        eligibility_year=record.eligibility_year,
        worker_birth_year=record.worker_birth_year,
        conditions=record.conditions,
    )


@st.composite
def _family_cases(draw):
    mode = draw(st.sampled_from(("claimed", "unclaimed", "deceased")))
    worker_year = draw(st.integers(1918, 1960))
    eligibility = worker_year + 62 + draw(st.integers(-1, 1))
    known_worker = draw(st.booleans())
    record = g.WorkerRecord(
        (
            g.FamilyKind.SURVIVOR
            if mode == "deceased"
            else g.FamilyKind.RETIREMENT
        ),
        eligibility,
        F(draw(st.integers(0, 20000)), 10),
        cola_percents=(F(draw(st.integers(0, 10))),),
        worker_birth_year=worker_year if known_worker else None,
        worker_reduction_months=(
            draw(st.integers(0, 60)) if mode == "claimed" else 0
        ),
        conditions=(
            {g.RecordCondition.WORKER_NOT_ENTITLED}
            if mode == "unclaimed"
            else set()
        )
        | draw(
            st.sets(
                st.sampled_from(
                    (
                        g.RecordCondition.NON_AIME_FORMULA_PIA,
                        g.RecordCondition.ADMINISTRATIVE_FINALITY,
                    )
                )
            )
        ),
    )
    year = draw(st.integers(1912, 1962))
    birth_year = draw(st.sampled_from((None, year)))
    own_year = draw(st.sampled_from((None, year, year + 1)))
    own = None
    if draw(st.booleans()):
        own = g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(draw(st.integers(0, 10000)), 10),
            reduction_months=draw(st.integers(0, 60)),
            birth_year=own_year,
        )
    widow = mode == "deceased"
    role = (
        draw(st.sampled_from((g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE)))
        if widow
        else (
            g.Role.DIVORCED_SPOUSE
            if mode == "unclaimed"
            else draw(st.sampled_from((g.Role.SPOUSE, g.Role.DIVORCED_SPOUSE)))
        )
    )
    members = [
        g.Beneficiary(
            "auxiliary",
            role,
            reduction_months=draw(st.integers(0, 60)),
            reduction_period_months=(
                draw(st.sampled_from(tuple(range(60, 85, 2))))
                if widow
                else None
            ),
            birth_year=birth_year,
            own_benefit=own,
            own_benefit_first=draw(st.booleans()) if own is not None else None,
            child_in_care=False if role is not g.Role.SPOUSE else None,
            first_entitlement_child_in_care=(
                False if role is g.Role.DIVORCED_SPOUSE else None
            ),
            conditions=(
                {g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET}
                if draw(st.booleans())
                else set()
            ),
        )
    ]
    if mode != "unclaimed" and draw(st.booleans()):
        members.append(g.Beneficiary("child", g.Role.CHILD))
    return (
        record,
        tuple(members),
        g.YearMonth(draw(st.integers(2023, 2026)), 12),
    )


def _result_key(result):
    if isinstance(result, g.FamilyBenefits):
        return replace(result, state_source="normalized-for-comparison")
    return tuple(
        (key, _result_key(result.records[key]))
        for key in sorted(result.records)
    )


def _capture(compute):
    try:
        result = compute()
    except g.InvalidFamilyInput as error:
        # Constructors and family checks can name different representations
        # of the same field (worker_reduction_months / reduction_months).
        # The API contract is the identical input-error class, not wording.
        return "input-error", type(error)
    except g.FamilyConfigurationUnsupported as error:
        return "refused", error.reason
    return "supported", _result_key(result)


def _guarded(records, month):
    guards = {
        key: g.SavingsClauseGuard(month, earlier_months_unknown=False)
        for key in records
    }
    try:
        outcome = g.household_month_outcome(
            records,
            payment_month=month,
            params=PARAMS,
            guards=guards,
            weight=WEIGHT,
        )
    except g.InvalidFamilyInput:
        assert all(guard.next_month == month for guard in guards.values())
        raise
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == 1 and counts.weight == WEIGHT
    assert all(guard.next_month != month for guard in guards.values())
    if outcome.unsupported is not None:
        assert counts.unsupported_rows == 1
        assert counts.unsupported_weight == WEIGHT
        assert counts.unsupported_by_reason == {
            outcome.unsupported.reason: (1, WEIGHT)
        }
        raise outcome.unsupported
    assert counts.supported_rows == 1 and counts.supported_weight == WEIGHT
    return outcome.benefits


def _single_route(case, route):
    record, members, month = case
    state = (
        g.record_state(record, PARAMS)
        if route == "built"
        else _direct_state(record)
    )
    if route in ("direct", "built"):
        return g.family_benefits(
            state, members, payment_month=month, params=PARAMS, standalone=True
        )
    records = {"record": g.HouseholdRecord("worker", state, members)}
    if route == "household":
        result = g.household_benefits(
            records, payment_month=month, params=PARAMS
        )
    else:
        result = _guarded(records, month)
    return result.records["record"]


def _pre_1983_competing_refusals():
    return (
        g.WorkerRecord(
            g.FamilyKind.RETIREMENT,
            1982,
            F(0),
            conditions={g.RecordCondition.NON_AIME_FORMULA_PIA},
        ),
        (),
        NOW,
    )


@pytest.mark.parametrize("route", ROUTES)
def test_review_pre_1983_refusal_precedence_matches_every_entry(route):
    assert _capture(
        lambda: _single_route(_pre_1983_competing_refusals(), route)
    ) == ("refused", g.UnsupportedReason.ELIGIBILITY_BEFORE_1983)


@settings(max_examples=300, deadline=None, derandomize=True)
@example(_pre_1983_competing_refusals())
@given(_family_cases())
def test_property_all_single_record_entry_points_have_identical_outcomes(case):
    original = deepcopy(case)
    outcomes = [
        _capture(lambda route=route: _single_route(case, route))
        for route in ROUTES
    ]
    assert all(outcome == outcomes[0] for outcome in outcomes)
    assert case == original


def _household_route(cases, link, *, built, guarded, reverse):
    records = {}
    month = max(case[2] for case in cases)
    for index, (record, members, _) in enumerate(cases):
        state = (
            g.record_state(record, PARAMS) if built else _direct_state(record)
        )
        worker = f"worker-{index}"
        renamed = tuple(
            replace(member, beneficiary_id=f"{member.beneficiary_id}-{index}")
            for member in members
        )
        if link == "same-auxiliary":
            renamed = (
                replace(renamed[0], beneficiary_id="shared"),
                *renamed[1:],
            )
        elif index == 1 and link == "worker-is-auxiliary":
            renamed = (
                replace(renamed[0], beneficiary_id="worker-0"),
                *renamed[1:],
            )
        records[f"record-{index}"] = g.HouseholdRecord(worker, state, renamed)
    if reverse:
        records = dict(reversed(tuple(records.items())))
    if guarded:
        return _guarded(records, month)
    return g.household_benefits(records, payment_month=month, params=PARAMS)


def _competing_refusals():
    record = g.WorkerRecord(g.FamilyKind.RETIREMENT, 1997, F(0))
    return [
        (
            replace(
                record, conditions={g.RecordCondition.NON_AIME_FORMULA_PIA}
            ),
            (g.Beneficiary("spouse", g.Role.SPOUSE),),
            NOW,
        ),
        (record, (_gpo_divorced_spouse(),), NOW),
    ]


@settings(max_examples=500, deadline=None, derandomize=True)
@example(_competing_refusals(), "independent")
@example(
    [_pre_1983_competing_refusals(), _competing_refusals()[1]],
    "independent",
)
@given(
    st.lists(_family_cases(), min_size=2, max_size=3),
    st.sampled_from(("independent", "same-auxiliary", "worker-is-auxiliary")),
)
def test_property_multi_record_entry_points_have_identical_outcomes(
    cases, link
):
    original = deepcopy(cases)
    outcomes = [
        _capture(
            lambda built=built, guarded=guarded, reverse=reverse: _household_route(
                cases, link, built=built, guarded=guarded, reverse=reverse
            )
        )
        for built in (False, True)
        for guarded in (False, True)
        for reverse in (False, True)
    ]
    assert all(outcome == outcomes[0] for outcome in outcomes)
    assert cases == original


@pytest.mark.parametrize("built", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
def test_household_refusal_reason_is_independent_of_entry_and_record_order(
    built, reverse
):
    expected = "refused", g.UnsupportedReason.NON_AIME_FORMULA_PIA
    for guarded in (False, True):
        assert (
            _capture(
                lambda guarded=guarded: _household_route(
                    _competing_refusals(),
                    "independent",
                    built=built,
                    guarded=guarded,
                    reverse=reverse,
                )
            )
            == expected
        )


@pytest.mark.parametrize("built", (False, True))
@pytest.mark.parametrize("guarded", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
def test_later_invalid_record_precedes_earlier_refusal(
    built, guarded, reverse
):
    cases = _competing_refusals()
    cases[1] = (
        g.WorkerRecord(
            g.FamilyKind.RETIREMENT,
            1998,
            F(0),
            worker_birth_year=1935,
            conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
        ),
        (_gpo_divorced_spouse(),),
        NOW,
    )
    assert _capture(
        lambda: _household_route(
            cases,
            "independent",
            built=built,
            guarded=guarded,
            reverse=reverse,
        )
    ) == ("input-error", g.InvalidFamilyInput)


def _linked_route(
    cohort,
    placement,
    conflict,
    mode,
    months,
    eligibility_delta,
    gpo,
    *,
    built,
    guarded,
    reverse,
):
    record = g.WorkerRecord(
        (
            g.FamilyKind.SURVIVOR
            if mode == "deceased"
            else g.FamilyKind.RETIREMENT
        ),
        cohort + 62 + eligibility_delta,
        F(100),
        worker_birth_year=cohort if placement & 1 else None,
        conditions=(
            {g.RecordCondition.WORKER_NOT_ENTITLED}
            if mode == "unclaimed"
            else set()
        ),
    )
    other = g.WorkerRecord(g.FamilyKind.RETIREMENT, 1997, F(1000))
    build = (
        (lambda record: g.record_state(record, PARAMS))
        if built
        else _direct_state
    )
    own = None
    if mode == "claimed":
        own = g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(100),
            birth_year=cohort if placement & 2 else None,
        )
    member = g.Beneficiary(
        "person",
        g.Role.SPOUSE,
        birth_year=cohort + int(conflict) if placement & 4 else None,
        own_benefit=own,
        own_benefit_first=True if own is not None else None,
        reduction_months=months,
        conditions=(
            {g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET}
            if gpo
            else set()
        ),
    )
    records = {
        "record-a": g.HouseholdRecord("person", build(record)),
        "record-b": g.HouseholdRecord("other", build(other), (member,)),
    }
    if reverse:
        records = dict(reversed(tuple(records.items())))
    if guarded:
        return _guarded(records, NOW)
    return g.household_benefits(records, payment_month=NOW, params=PARAMS)


@settings(max_examples=250, deadline=None, derandomize=True)
@example(1935, 4, False, "unclaimed", 0, 1, True)
@example(1935, 1, False, "unclaimed", 36, 0, False)
@example(1935, 3, False, "claimed", 36, 0, False)
@given(
    st.integers(1929, 1960),
    st.integers(0, 7),
    st.booleans(),
    st.sampled_from(("claimed", "unclaimed", "deceased")),
    st.integers(0, 60),
    st.integers(-1, 1),
    st.booleans(),
)
def test_property_household_cohort_resolution_agrees_across_entries(
    cohort, placement, conflict, mode, months, eligibility_delta, gpo
):
    outcomes = [
        _capture(
            lambda built=built, guarded=guarded, reverse=reverse: _linked_route(
                cohort,
                placement,
                conflict,
                mode,
                months,
                eligibility_delta,
                gpo,
                built=built,
                guarded=guarded,
                reverse=reverse,
            )
        )
        for built in (False, True)
        for guarded in (False, True)
        for reverse in (False, True)
    ]
    assert all(outcome == outcomes[0] for outcome in outcomes)
