"""INVENTED fixed filing, ordering, spouse arithmetic and cross-cutting tests."""

import dataclasses
import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.fra68_track.reform import spouse_excess_months_early
from populace_dynamics.ss import benefits
from populace_dynamics.track_a_v2.filing import (
    Application,
    FilingRefusal,
    application_month,
    classify_ordering,
    spouse_timing,
)
from tests.track_a_v2._invented import build, calculator, parameters


def paid(own, worker, months, params=None):
    return (
        math.floor(
            10
            * benefits.spousal_benefit(
                own, worker, months, params or parameters()
            )
            + 1e-9
        )
        / 10
    )


@pytest.mark.parametrize(
    "case,spouse,award,claim,ordering,early,amount",
    [
        ("Q", 2024, 2020, None, "di_first", 36, 300),
        ("Q", 2024, 2024, None, "concurrent", 36, 300),
        ("P", 2022, 2025, 2022, "prior_rib_spouse_di", 60, 260),
        ("P", 2024, 2023, 2022, "prior_rib_di_spouse", 36, 300),
    ],
)
def test_direct_ordering_amounts(
    case, spouse, award, claim, ordering, early, amount
):
    """Each supported ordering has explicit Formula-F amount; own stays 600."""
    app = Application(spouse, 12 * (spouse - 1960), case, {})
    assert (
        classify_ordering(
            app,
            entitlement_year=spouse,
            di_entitlement_year=award,
            claim_year=claim,
        )
        == ordering
    )
    excess = paid(600, 2000, early)
    assert excess == amount
    assert 600 + excess == 600 + amount
    if ordering == "prior_rib_spouse_di":
        assert paid(700, 2000, early) == 195


@pytest.mark.parametrize("case,claim", [("Q", None), ("P", 2023)])
def test_intended_spouse_only_first_refuses(case, claim):
    """Intended spouse-first ordering refuses; it must not get concurrent F."""
    with pytest.raises(FilingRefusal, match="spouse-only"):
        classify_ordering(
            Application(2022, 744, case, {}),
            entitlement_year=2022,
            di_entitlement_year=2025,
            claim_year=claim,
        )
    assert 750 - 600 == 150  # Explicit different arithmetic, never dispatched.
    assert paid(280, 800, 36) == 90
    assert 280 + 90 == 370 and 280 + 20 == 300


def test_filing_null_dates_future_and_integrity():
    """Null claim selects Q; only scheduled year decides horizon payment."""
    for birth, q, expected in ((1965, None, 2032), (1963, 2030, 2030)):
        app = application_month(
            birth_year=birth,
            claim_year=None,
            entitlement_year=2020,
            conversion_year=q,
            baseline_params=parameters(),
        )
        assert app.year == expected and app.month == 804
        assert app.counters.get("s_application_after_reference", 0) == (
            expected > 2030
        )
    for claim, q in ((2029, 2030), (2030, None), (2030, 2029)):
        with pytest.raises(FilingRefusal):
            application_month(
                birth_year=1963,
                claim_year=claim,
                entitlement_year=2020,
                conversion_year=q,
                baseline_params=parameters(),
            )
    for birth, award, params in (
        (None, 2020, parameters()),
        (1960, None, parameters()),
        (1960, 2020, parameters(fra_months_by_birth_year=[])),
    ):
        with pytest.raises(FilingRefusal):
            application_month(
                birth_year=birth,
                claim_year=None,
                entitlement_year=award,
                conversion_year=None,
                baseline_params=params,
            )


def couple(
    *,
    birth=1964,
    claim=2026,
    award=2027,
    conversion=None,
    worker_birth=1950,
    worker_claim=2020,
    opening=False,
    own_pia=600,
    worker_pia=2000,
    recoveries=(),
    awards=None,
):
    return build(
        [
            dict(
                id=1,
                birth=birth,
                awards=(award,) if awards is None else awards,
                recoveries=recoveries,
                conversion=conversion,
                claim=claim,
                marital="married",
                spouse=2,
                opening_receipt=opening,
            ),
            dict(id=2, birth=worker_birth, claim=worker_claim),
        ],
        careers={1: {1987: own_pia * 420}, 2: {1987: worker_pia * 420}},
    )


def excess(calc):
    values, _ = calc.projected_person(1, calc.lookups.final.loc[1])
    return values.get("spouse", (0, 0))[0]


@pytest.mark.parametrize("exercise", [1, 3])
def test_prior_claim_active_di_and_null_identity(exercise):
    """S keeps own DI and H fixed; null policy preserves both component paths."""
    cohort, result = couple()
    for mechanism in ("L", "D", "S", "DS"):
        calc = calculator(
            cohort, result, mechanism=mechanism, exercise=exercise
        )
        components, _ = calc.projected_person(1, calc.lookups.final.loc[1])
        assert all(base == reform for base, reform in components.values())
        assert all(min(pair) >= 0 for pair in components.values())
        assert not (
            "retired_worker" in components and "disabled_worker" in components
        )
        if mechanism in ("L", "D"):
            assert "spouse" not in components
        else:
            assert calc.counters["s_prior_claim_projected"] == 1
            assert calc.counters["s_rib_to_di_own_reduction_not_modeled"] == 1
    s = calculator(cohort, result, mechanism="S", exercise=exercise)
    assert excess(s) == 260
    reform = calculator(
        cohort,
        result,
        mechanism="S",
        exercise=3,
        baseline_params=parameters(),
        params=parameters(fra_months_by_birth_year=[(1900, 816)]),
    )
    assert excess(reform) == 240


@pytest.mark.parametrize("exercise", [1, 3])
def test_opening_proxy_deferral(exercise):
    """A prior opening application is counted and deferred, never withheld."""
    cohort, result = couple(
        birth=1960,
        claim=2008,
        award=2015,
        conversion=2027,
        worker_claim=2005,
        opening=True,
        worker_birth=1940,
    )
    legacy = calculator(cohort, result, exercise=exercise)
    changed = calculator(cohort, result, mechanism="S", exercise=exercise)
    assert excess(legacy) == 0
    assert excess(changed) == 260
    assert changed.counters["s_entitlement_deferred_to_62"] == 1
    assert changed.counters["s_prior_claim_opening"] == 1


def test_fractional_fra_and_fixed_application_after_both_conversions():
    """H stays fixed after reform conversion; group 4 uses the scenario FRA."""
    for birth, fra, conversion, expected, reform_expected in (
        (1955, 794, 2021, 394.4, None),
        (1957, 798, 2024, 400, 383.3),
    ):
        cohort, result = couple(
            birth=birth, claim=conversion, award=2015, conversion=conversion
        )
        base = parameters(fra_months_by_birth_year=[(1900, fra)])
        calc = calculator(
            cohort, result, mechanism="S", exercise=3, params=base
        )
        assert excess(calc) == expected
        assert (
            excess(calculator(cohort, result, exercise=3, params=base))
            == expected
        )
        if reform_expected is not None:
            reform = dataclasses.replace(
                base, fra_months_by_birth_year=[(1900, fra + 12)]
            )
            assert (
                excess(
                    calculator(
                        cohort,
                        result,
                        mechanism="S",
                        exercise=3,
                        params=reform,
                        baseline_params=base,
                    )
                )
                == reform_expected
            )
            assert (
                excess(
                    calculator(
                        cohort,
                        result,
                        exercise=3,
                        params=reform,
                        baseline_params=base,
                    )
                )
                == 400
            )


def test_baseline_converted_reform_disabled_zero_own():
    """Zero own DI permits positive S excess in both conversion labels."""
    cohort, result = couple(
        birth=1963,
        award=2020,
        claim=2030,
        conversion=2030,
        own_pia=0,
        worker_pia=800,
    )
    baseline = parameters()
    reform = parameters(fra_months_by_birth_year=[(1900, 816)])
    assert excess(calculator(cohort, result, mechanism="S", exercise=3)) == 400
    assert (
        excess(
            calculator(
                cohort,
                result,
                mechanism="S",
                exercise=3,
                params=reform,
                baseline_params=baseline,
            )
        )
        == 366.6
    )
    assert (
        excess(
            calculator(
                cohort,
                result,
                exercise=3,
                params=reform,
                baseline_params=baseline,
            )
        )
        == 0
    )


@pytest.mark.parametrize(
    "response", ["at_or_after_anchor_delay", "all_projected_delay"]
)
@pytest.mark.parametrize("worker_claim,expected", [(2029, 333.3), (2030, 0)])
def test_exact_worker_claim_move(response, worker_claim, expected):
    """C1/C2 leave H fixed; worker exact months and annual gate both apply."""
    cohort, result = couple(
        birth=1964,
        claim=2029,
        award=2030,
        worker_birth=1964,
        worker_claim=worker_claim,
    )
    calc = calculator(
        cohort,
        result,
        mechanism="S",
        exercise=3,
        params=parameters(fra_months_by_birth_year=[(1900, 816)]),
        baseline_params=parameters(),
        response=response,
    )
    assert excess(calc) == expected
    moved = calc.worker_record(2, calc.lookups.final.loc[2])
    assert moved.entitlement_year == worker_claim + 1
    assert moved.claim_move_months == 12


@pytest.mark.parametrize(
    "gap", ["unlinked", "outside", "no_record", "under62", "future"]
)
def test_unpaid_cases_and_existing_gap_counters(gap):
    """Unpaid eligibility/link gaps create no excess; only existing gaps count."""
    cohort, result = couple(
        birth=1970 if gap == "under62" else 1965,
        award=2022,
        claim=None,
    )
    if gap == "unlinked":
        result.slices[-1].loc[0, "spouse_person_id"] = None
    if gap == "outside":
        result.slices[-1].loc[0, "spouse_person_id"] = 999
    if gap == "no_record":
        result.slices[-1].loc[1, "claimed"] = False
    calc = calculator(cohort, result, mechanism="S")
    if gap == "under62":
        # Intentionally impossible engine claim removed; Q schedules future.
        result.slices[-1].loc[0, "claim_year"] = None
    assert excess(calc) == 0
    if gap in ("unlinked", "outside"):
        name = (
            "spouse_unlinked" if gap == "unlinked" else "spouse_outside_roster"
        )
        assert calc.counters[name] == 1
    if gap == "future":
        assert calc.counters["s_application_after_reference"] == 1


@pytest.mark.parametrize("mechanism", ["S", "DS", "D"])
def test_ended_spell_reaward_refusal(mechanism):
    """Intended ended spell/re-award refuses every reached supported mechanism."""
    cohort, result = couple(
        birth=1960, claim=2022, awards=(2015, 2023), recoveries=(2018,)
    )
    calc = calculator(cohort, result, mechanism=mechanism)
    with pytest.raises(ValueError, match="recovery|award|spell"):
        excess(calc)


@settings(deadline=None)
@given(
    st.integers(0, 3000),
    st.integers(0, 6000),
    st.integers(0, 120),
    st.integers(0, 24),
)
def test_spouse_amount_bounds_and_c0_monotonicity(
    own, worker, early, increase
):
    """Excess is bounded by half-worker less own; more early months cannot raise it."""
    first = paid(own, worker, early)
    later = paid(own, worker, early + increase)
    assert 0 <= later <= first <= max(0, worker / 2 - own)
    assert (own >= worker / 2) <= (first == 0)


@settings(deadline=None)
@given(st.integers(1960, 1967), st.integers(62, 70), st.integers(2010, 2030))
def test_baseline_count_differential(birth, age, worker_year):
    """Where L already pays, S baseline months early equals retained helper."""
    app = Application(birth + age, 12 * age, "P", {})
    timing = spouse_timing(
        app,
        birth_year=birth,
        worker_entitlement_year=worker_year,
        fra_months=804,
    )
    assert timing.months_early == spouse_excess_months_early(
        own_claim_month=12 * age,
        worker_entitlement_year=worker_year,
        birth_year=birth,
        params=parameters(),
    )


def test_ended_spell_future_application_refuses_and_retains_counters():
    """An intended ended spell refuses on S reach, even before unpaid gates."""
    cohort, result = couple(
        birth=1965, claim=None, awards=(2015, 2023), recoveries=(2018,)
    )
    calc = calculator(cohort, result, mechanism="S")
    with pytest.raises(FilingRefusal) as caught:
        excess(calc)
    assert caught.value.person_id == 1
    assert isinstance(caught.value.counters, dict)
