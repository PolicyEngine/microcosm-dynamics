"""Invented-case tests for the opt-in scenario COLA benefit paths (A6).

Every COLA rate, earnings history, PIA, birth year and weight below is
INVENTED for testing.  No test reads PSID, SSA administrative data, a
Trustees path or any comparator value, and none computes the exercise-1
age-group statistic.
"""

from __future__ import annotations

import hashlib
import math
import struct
from datetime import date

import pytest

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.estimates import ledgers
from populace_dynamics.estimates.parameters import (
    COLASeries,
    PayrollRateLegs,
    ReportParameters,
)
from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters

# Invented realized history: a deterministic closed-form path over the
# committed loader's 1979-2022 span (0.012 to 0.090), with a few zero years.
_INVENTED_REALIZED = {
    year: (
        0.0
        if year in {1986, 2009, 2010, 2015}
        else 0.012 + ((year * 37) % 79) / 1000
    )
    for year in range(1979, 2023)
}
# Invented projection; every rate exceeds the 0.01 reduction so the zero
# floor never binds.
_INVENTED_PROJECTION = {
    year: 0.015 + 0.001 * (year % 7) for year in range(2008, 2032)
}
# Pinned sha256 of repr(BenefitLedger) for the invented claimants below,
# computed with the sealed ledger module (unchanged since the reviewed
# implementation commit, which the birth-evidence identity test enforces).
_SEALED_LEDGER_REPR_SHA256 = (
    "156304852698780609d74288f00643c43f2187841622527179c7d0c66f46cbb5"
)


def _realized() -> COLASeries:
    return COLASeries(
        by_determination_year=dict(_INVENTED_REALIZED),
        provenance={"invented": True},
    )


def _baseline() -> COLASeries:
    return sb.extend_cola_series(
        _realized(),
        _INVENTED_PROJECTION,
        projection_label="INVENTED test projection",
    )


def _ssa() -> SSAParameters:
    return SSAParameters(
        nawi={year: 9_779.44 for year in range(1968, 2031)},
        wage_base={1900: 1_000_000.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 66 * 12)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="invented-fixture",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


def _report_parameters(cola: COLASeries) -> ReportParameters:
    return ReportParameters(
        ssa=_ssa(),
        rates=PayrollRateLegs(
            employee_by_effective_year={1900: 0.062},
            employer_by_effective_year={1900: 0.062},
            provenance={"invented": True},
        ),
        cola=cola,
        provenance={"invented": True},
    )


def _product(baseline: COLASeries, years: range, reduction: float) -> float:
    return math.prod(
        (1.0 + baseline[year] - reduction) / (1.0 + baseline[year])
        for year in years
    )


def _bits(values: dict[int, float]) -> list[tuple[int, bytes]]:
    return [(year, struct.pack("<d", value)) for year, value in values.items()]


# ---------------------------------------------------------------------------
# Default behavior equals the sealed ledger path, bit for bit
# ---------------------------------------------------------------------------
_PIAS = (0.0, 90.0, 1_234.56, 2_609.87, 3_999.99)
_FACTORS = (0.7, 0.75, 0.8, 14 / 15, 1.0, 1.24, 1.32)
_ELIGIBILITY_YEARS = (1979, 1990, 2004, 2012, 2015, 2021, 2022, 2023)


@pytest.mark.parametrize("eligibility_year", _ELIGIBILITY_YEARS)
@pytest.mark.parametrize("factor", _FACTORS)
def test_default_path_is_the_sealed_ledger_path_bit_for_bit(
    eligibility_year, factor
):
    cola = _realized()
    for pia in _PIAS:
        sealed = ledgers._monthly_benefit_path(
            eligibility_pia=pia,
            claim_age_factor=factor,
            eligibility_year=eligibility_year,
            cola=cola,
        )
        general = sb.monthly_benefit_path(
            eligibility_pia=pia,
            claim_age_factor=factor,
            eligibility_year=eligibility_year,
            cola=cola,
        )
        assert repr(general) == repr(sealed)
        assert _bits(general) == _bits(sealed)


def test_baseline_rate_wrapper_and_late_reform_leave_the_sealed_path_alone():
    cola = _realized()
    clock = sb.WorkerClock.at_age_62(1950, entitlement_year=2013)
    late_reform = sb.COLAReform(first_reduced_determination_year=2022)
    for rates in (
        sb.scenario_rates(cola, None, clock=clock),
        sb.scenario_rates(cola, late_reform, clock=clock),
    ):
        general = sb.monthly_benefit_path(
            eligibility_pia=1_234.56,
            claim_age_factor=0.8,
            eligibility_year=2012,
            cola=rates,
        )
        sealed = ledgers._monthly_benefit_path(
            eligibility_pia=1_234.56,
            claim_age_factor=0.8,
            eligibility_year=2012,
            cola=cola,
        )
        assert _bits(general) == _bits(sealed)


def test_horizon_extension_does_not_move_the_sealed_years():
    baseline = _baseline()
    realized = _realized()
    extended = sb.monthly_benefit_path(
        eligibility_pia=2_609.87,
        claim_age_factor=0.75,
        eligibility_year=2003,
        cola=baseline,
        horizon_year=2030,
    )
    # Invented projection supersedes realized years from 2008, so compare
    # against the sealed path fed the same spliced series.
    sealed_same_series = ledgers._monthly_benefit_path(
        eligibility_pia=2_609.87,
        claim_age_factor=0.75,
        eligibility_year=2003,
        cola=baseline,
    )
    assert list(extended)[-1] == 2030
    assert _bits({y: extended[y] for y in sealed_same_series}) == _bits(
        sealed_same_series
    )
    # Before the splice the realized history alone determines the path.
    sealed_realized = ledgers._monthly_benefit_path(
        eligibility_pia=2_609.87,
        claim_age_factor=0.75,
        eligibility_year=2003,
        cola=realized,
    )
    assert _bits({y: extended[y] for y in range(2003, 2009)}) == _bits(
        {y: sealed_realized[y] for y in range(2003, 2009)}
    )


def _invented_claimants() -> list[ledgers.BenefitClaimant]:
    rows = []
    for person_id, (birth, claim_age, origin, weight) in enumerate(
        (
            (1953, 62, "modeled_award", 2.0),
            (1950, 65, "modeled_award", 1.5),
            (1948, 70, "modeled_award", 3.25),
            (1940, 62, "opening_backfill", 4.0),
            (1925, 66, "opening_backfill", 0.75),
            (1958, 64, "modeled_award", 1.0),
        ),
        start=1,
    ):
        claim_year = birth + claim_age
        earnings = {
            year: 9_000.0 + 1_137.0 * ((year * person_id) % 29)
            for year in range(max(1968, birth + 22), claim_year + 1)
        }
        rows.append(
            ledgers.BenefitClaimant(
                person_id=person_id,
                birth_year=birth,
                claim_age=claim_age,
                claim_year=claim_year,
                claim_origin=origin,
                weight=weight,
                earnings_by_year=earnings,
                presence_years=frozenset(range(2015, 2023)),
                provenance_by_year={year: "observed" for year in earnings},
            )
        )
    return rows


def test_sealed_ledger_output_is_byte_identical_under_generalized_path(
    monkeypatch,
):
    parameters = _report_parameters(_realized())
    sealed = ledgers.build_benefit_ledger(
        _invented_claimants(), parameters, draw_index=3
    )
    sealed_repr = repr(sealed)
    assert (
        hashlib.sha256(sealed_repr.encode()).hexdigest()
        == _SEALED_LEDGER_REPR_SHA256
    )

    calls = []

    def generalized(**kwargs):
        calls.append(kwargs["eligibility_year"])
        return sb.monthly_benefit_path(**kwargs)

    monkeypatch.setattr(ledgers, "_monthly_benefit_path", generalized)
    substituted = ledgers.build_benefit_ledger(
        _invented_claimants(), parameters, draw_index=3
    )
    assert len(calls) == len(_invented_claimants())
    assert repr(substituted) == sealed_repr


# ---------------------------------------------------------------------------
# Scenario COLA series
# ---------------------------------------------------------------------------
def test_extend_cola_series_splices_and_records_superseded_years():
    series = _baseline()
    assert tuple(series) == tuple(range(1979, 2032))
    for year in range(1979, 2008):
        assert series[year] == _INVENTED_REALIZED[year]
    for year in range(2008, 2032):
        assert series[year] == _INVENTED_PROJECTION[year]
    provenance = series.provenance
    assert provenance["realized_through_determination_year"] == 2007
    assert provenance["superseded_realized_determination_years"] == list(
        range(2008, 2023)
    )
    assert provenance["projection_label"] == "INVENTED test projection"
    assert provenance["projected_first_determination_year"] == 2008
    assert provenance["projected_last_determination_year"] == 2031
    assert len(provenance["projected_rates_sha256"]) == 64


@pytest.mark.parametrize(
    ("projected", "error"),
    [
        ({2025: 0.02}, ValueError),  # gap: 2023 and 2024 missing
        ({2023: 0.02, 2025: 0.02}, ValueError),  # nonconsecutive
        ({2023: 2.8}, ValueError),  # a percent, not a fraction
        ({2023: -0.01}, ValueError),
        ({2023: float("nan")}, ValueError),
        ({True: 0.02}, TypeError),
        ({}, ValueError),
    ],
)
def test_extend_cola_series_rejects_bad_projections(projected, error):
    with pytest.raises(error):
        sb.extend_cola_series(
            _realized(), projected, projection_label="INVENTED"
        )


def test_scenario_rates_explain_a_missing_determination_year():
    clock = sb.WorkerClock.at_age_62(1950, entitlement_year=2012)
    rates = sb.scenario_rates(_realized(), None, clock=clock)
    with pytest.raises(ValueError, match="lacks determination year 2023"):
        sb.increased_pia_path(
            eligibility_pia=1_000.0,
            eligibility_year=2012,
            cola=rates,
            horizon_year=2030,
        )


# ---------------------------------------------------------------------------
# Reform definition
# ---------------------------------------------------------------------------
def test_reform_defaults_are_the_plan_proposals():
    reform = sb.COLAReform()
    assert reform == sb.PLAN_PROPOSED_REFORM
    assert reform.annual_reduction == 0.01
    assert reform.first_reduced_determination_year == 2009
    assert reform.negative_rate_policy is sb.NegativeRatePolicy.REFUSE
    assert reform.first_reduced_effective_month == date(2009, 12, 1)
    assert reform.first_reduced_payment_month == date(2010, 1, 1)


def test_reform_from_effective_month_requires_december():
    reform = sb.COLAReform.from_effective_month(date(2010, 12, 1))
    assert reform.first_reduced_determination_year == 2010
    with pytest.raises(ValueError, match="December"):
        sb.COLAReform.from_effective_month(date(2010, 1, 1))
    with pytest.raises(ValueError, match="1983"):
        sb.COLAReform(first_reduced_determination_year=1982)
    with pytest.raises(ValueError):
        sb.COLAReform(annual_reduction=1.5)
    with pytest.raises(TypeError):
        sb.COLAReform(first_reduced_determination_year=True)


def test_negative_reformed_rate_is_refused_or_floored_explicitly():
    series = COLASeries(
        by_determination_year={
            **_INVENTED_REALIZED,
            2012: 0.004,
        },
        provenance={"invented": True},
    )
    clock = sb.WorkerClock.at_age_62(1950, entitlement_year=2012)
    refuse = sb.scenario_rates(series, sb.COLAReform(), clock=clock)
    with pytest.raises(ValueError, match="nonbinding"):
        refuse.rate_for_determination_year(2012)
    floor = sb.scenario_rates(
        series,
        sb.COLAReform(
            negative_rate_policy=sb.NegativeRatePolicy.FLOOR_AT_ZERO
        ),
        clock=clock,
    )
    assert floor.rate_for_determination_year(2012) == 0.0
    path = sb.increased_pia_path(
        eligibility_pia=1_000.0,
        eligibility_year=2012,
        cola=floor,
        horizon_year=2013,
    )
    assert path == {2012: 1_000.0, 2013: 1_000.0}
    assert sb.minimum_reformed_rate(
        series, sb.COLAReform(), through_determination_year=2022
    ) == pytest.approx(
        -0.01
    )  # the invented realized 2009 zero
    assert sb.minimum_reformed_rate(
        _baseline(), sb.COLAReform(), through_determination_year=2029
    ) == pytest.approx(0.005)


# ---------------------------------------------------------------------------
# The arithmetic: n reduced increases scale by prod((1+c-r)/(1+c))
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("first_reduced", "exposure_clock", "entitlement", "first_counted"),
    [
        (2009, sb.ExposureClock.ELIGIBILITY, 2016, 2012),
        (2010, sb.ExposureClock.ELIGIBILITY, 2016, 2012),
        (2009, sb.ExposureClock.ENTITLEMENT, 2016, 2016),
        (2014, sb.ExposureClock.ELIGIBILITY, 2012, 2014),
        (2014, sb.ExposureClock.ENTITLEMENT, 2012, 2014),
    ],
)
def test_reduced_increases_scale_unrounded_benefit_by_the_product(
    first_reduced, exposure_clock, entitlement, first_counted
):
    baseline = _baseline()
    reform = sb.COLAReform(first_reduced_determination_year=first_reduced)
    clock = sb.WorkerClock.at_age_62(1950, entitlement_year=entitlement)
    paths = sb.worker_scenario_paths(
        eligibility_pia=1_873.45,
        claim_age_factor=0.8666,
        clock=clock,
        baseline=baseline,
        reform=reform,
        exposure_clock=exposure_clock,
        round_to_dime=False,
    )
    assert paths.exposure_start_year == (
        2012 if exposure_clock is sb.ExposureClock.ELIGIBILITY else entitlement
    )
    assert list(paths.baseline_monthly_by_payment_year) == list(
        range(entitlement, 2031)
    )
    for year, base in paths.baseline_monthly_by_payment_year.items():
        reduced_years = range(first_counted, year)
        n = len(reduced_years)
        assert paths.reduced_increases_by_payment_year[year] == n
        ratio = paths.reform_monthly_by_payment_year[year] / base
        assert ratio == pytest.approx(
            _product(baseline, reduced_years, 0.01), rel=1e-12, abs=0.0
        )
    assert paths.reduced_increases_by_payment_year[2030] == 2030 - (
        first_counted
    )


def test_rounded_paths_stay_within_dime_floors_of_the_product():
    baseline = _baseline()
    clock = sb.WorkerClock.at_age_62(1950, entitlement_year=2014)
    common = {
        "eligibility_pia": 1_873.45,
        "claim_age_factor": 0.8666,
        "clock": clock,
        "baseline": baseline,
    }
    exact = sb.worker_scenario_paths(**common, round_to_dime=False)
    rounded = sb.worker_scenario_paths(**common)
    for scenario in ("baseline", "reform"):
        exact_path = getattr(exact, f"{scenario}_monthly_by_payment_year")
        rounded_path = getattr(rounded, f"{scenario}_monthly_by_payment_year")
        for year, value in rounded_path.items():
            steps = year - 2012 + 2
            assert value == ledgers.floor_to_dime(value)
            assert 0.0 <= exact_path[year] - value < 0.1 * steps * 1.6
    for year in rounded.reform_monthly_by_payment_year:
        assert (
            rounded.reform_monthly_by_payment_year[year]
            <= rounded.baseline_monthly_by_payment_year[year]
        )


def test_invented_constant_path_gives_twenty_one_or_twenty_increases():
    # INVENTED flat 3% path, used only to check first-application counts.
    flat = COLASeries(
        by_determination_year={year: 0.03 for year in range(1979, 2031)},
        provenance={"invented": True},
    )
    clock = sb.WorkerClock.at_age_62(1940, entitlement_year=2004)
    for first_reduced, expected_n in ((2009, 21), (2010, 20)):
        paths = sb.worker_scenario_paths(
            eligibility_pia=1_000.0,
            claim_age_factor=1.0,
            clock=clock,
            baseline=flat,
            reform=sb.COLAReform(
                first_reduced_determination_year=first_reduced
            ),
            round_to_dime=False,
        )
        assert paths.reduced_increases_by_payment_year[2030] == expected_n
        assert paths.reform_monthly_by_payment_year[2030] / (
            paths.baseline_monthly_by_payment_year[2030]
        ) == pytest.approx((1.02 / 1.03) ** expected_n, rel=1e-12)


# ---------------------------------------------------------------------------
# Exposure clocks
# ---------------------------------------------------------------------------
def test_exposure_clock_changes_only_the_reform_path():
    baseline = _baseline()
    clock = sb.WorkerClock.at_age_62(1952, entitlement_year=2019)
    results = {
        exposure: sb.worker_scenario_paths(
            eligibility_pia=2_000.0,
            claim_age_factor=1.0,
            clock=clock,
            baseline=baseline,
            exposure_clock=exposure,
        )
        for exposure in sb.ExposureClock
    }
    eligibility = results[sb.ExposureClock.ELIGIBILITY]
    entitlement = results[sb.ExposureClock.ENTITLEMENT]
    assert (
        eligibility.baseline_monthly_by_payment_year
        == entitlement.baseline_monthly_by_payment_year
    )
    assert eligibility.reduced_increases_by_payment_year[2030] == 16
    assert entitlement.reduced_increases_by_payment_year[2030] == 11
    assert (
        eligibility.reform_monthly_by_payment_year[2030]
        < entitlement.reform_monthly_by_payment_year[2030]
    )
    assert eligibility.evidence_labels == sb.SCENARIO_EVIDENCE_LABELS


def test_di_onset_starts_the_eligibility_clock():
    clock = sb.WorkerClock.at_di_onset(2003, entitlement_year=2004)
    assert clock.basis is sb.EligibilityBasis.DI_ONSET
    assert clock.eligibility_year == 2003
    paths = sb.worker_scenario_paths(
        eligibility_pia=1_400.0,  # INVENTED supplied PIA; no DI level rule
        claim_age_factor=1.0,
        clock=clock,
        baseline=_baseline(),
    )
    assert paths.reduced_increases_by_payment_year[2030] == 21
    assert list(paths.baseline_monthly_by_payment_year)[0] == 2004


def test_clock_validation_and_never_entitled_workers():
    with pytest.raises(ValueError, match="precedes"):
        sb.WorkerClock.at_age_62(1950, entitlement_year=2011)
    with pytest.raises(ValueError, match="no own entitlement"):
        sb.WorkerClock(
            basis=sb.EligibilityBasis.DEATH_BEFORE_ELIGIBILITY,
            eligibility_year=2015,
            entitlement_year=2015,
        )
    never = sb.WorkerClock.at_age_62(1950)
    assert never.exposure_start_year(sb.ExposureClock.ELIGIBILITY) == 2012
    with pytest.raises(ValueError, match="never entitled"):
        never.exposure_start_year(sb.ExposureClock.ENTITLEMENT)
    with pytest.raises(ValueError, match="entitlement year"):
        sb.worker_scenario_paths(
            eligibility_pia=1.0,
            claim_age_factor=1.0,
            clock=never,
            baseline=_baseline(),
        )


# ---------------------------------------------------------------------------
# Auxiliary benefits follow the worker's clock
# ---------------------------------------------------------------------------
def test_spouse_follows_the_workers_clock_not_the_spouses_age():
    baseline = _baseline()
    ssa = _ssa()
    worker = sb.WorkerClock.at_age_62(1950, entitlement_year=2014)
    for exposure, first_counted in (
        (sb.ExposureClock.ELIGIBILITY, 2012),
        (sb.ExposureClock.ENTITLEMENT, 2014),
    ):
        paths = sb.spouse_scenario_paths(
            worker_eligibility_pia=2_222.2,
            worker_clock=worker,
            own=None,
            months_early=48,
            entitlement_year=2018,  # spouse born 1956 claims at 62
            params=ssa,
            baseline=baseline,
            exposure_clock=exposure,
            round_to_dime=False,
        )
        assert paths.beneficiary_type == "spouse"
        assert paths.worker_clock == worker
        assert list(paths.baseline_monthly_by_payment_year) == list(
            range(2018, 2031)
        )
        for year, base in paths.baseline_monthly_by_payment_year.items():
            reduced_years = range(first_counted, year)
            assert paths.reduced_increases_by_payment_year[year] == len(
                reduced_years
            )
            assert paths.reform_monthly_by_payment_year[
                year
            ] / base == pytest.approx(
                _product(baseline, reduced_years, 0.01), rel=1e-12
            )


def test_spouse_dual_entitlement_uses_each_pia_on_its_own_clock():
    baseline = _baseline()
    ssa = _ssa()
    worker = sb.WorkerClock.at_age_62(1950, entitlement_year=2012)
    own = sb.OwnBenefit(
        eligibility_pia=600.0,
        claim_age_factor=0.75,
        clock=sb.WorkerClock.at_age_62(1954, entitlement_year=2016),
    )
    paths = sb.spouse_scenario_paths(
        worker_eligibility_pia=2_400.0,
        worker_clock=worker,
        own=own,
        months_early=48,
        entitlement_year=2016,
        params=ssa,
        baseline=baseline,
    )
    reform_rates = sb.scenario_rates(baseline, sb.COLAReform(), clock=worker)
    own_rates = sb.scenario_rates(baseline, sb.COLAReform(), clock=own.clock)
    worker_pia = sb.increased_pia_path(
        eligibility_pia=2_400.0,
        eligibility_year=2012,
        cola=reform_rates,
        horizon_year=2030,
    )
    own_pia = sb.increased_pia_path(
        eligibility_pia=600.0,
        eligibility_year=2016,
        cola=own_rates,
        horizon_year=2030,
    )
    reduction = benefits.spousal_early_reduction(48, ssa)
    for year, amount in paths.reform_monthly_by_payment_year.items():
        expected = max(0.0, 0.5 * worker_pia[year] - own_pia[year]) * (
            1.0 - reduction
        )
        assert amount == ledgers.floor_to_dime(expected)
    with pytest.raises(ValueError, match="entitled worker"):
        sb.spouse_scenario_paths(
            worker_eligibility_pia=2_400.0,
            worker_clock=sb.WorkerClock.at_age_62(1950),
            own=None,
            months_early=0,
            entitlement_year=2016,
            params=ssa,
            baseline=baseline,
        )


def test_widow_follows_the_deceased_workers_clock():
    baseline = _baseline()
    ssa = _ssa()
    # Invented deceased worker: born 1948, claimed at 62 (factor 0.75),
    # died 2020.  Invented widow born 1952, entitled 2020 at 68.
    deceased = sb.WorkerClock.at_age_62(1948, entitlement_year=2010)
    paths = sb.widow_scenario_paths(
        deceased_eligibility_pia=1_900.0,
        deceased_clock=deceased,
        deceased_claim_age_factor=0.75,
        own=None,
        survivor_months_early=0,
        entitlement_year=2020,
        params=ssa,
        baseline=baseline,
        round_to_dime=False,
    )
    assert paths.beneficiary_type == "widow(er)"
    assert paths.reduced_increases_by_payment_year[2030] == 20
    for year, base in paths.baseline_monthly_by_payment_year.items():
        assert paths.reform_monthly_by_payment_year[
            year
        ] / base == pytest.approx(
            _product(baseline, range(2010, year), 0.01), rel=1e-12
        )
    # RIB-LIM: 82.5% of the deceased's increased PIA binds here.
    pia_2030 = sb.increased_pia_path(
        eligibility_pia=1_900.0,
        eligibility_year=2010,
        cola=baseline,
        horizon_year=2030,
        round_to_dime=False,
    )[2030]
    assert paths.baseline_monthly_by_payment_year[2030] == pytest.approx(
        0.825 * pia_2030, rel=1e-12
    )


def test_widow_own_benefit_counts_only_from_own_entitlement():
    baseline = _baseline()
    ssa = _ssa()
    deceased = sb.WorkerClock.at_age_62(1948, entitlement_year=2014)
    own = sb.OwnBenefit(
        eligibility_pia=2_500.0,
        claim_age_factor=1.0,
        clock=sb.WorkerClock.at_age_62(1954, entitlement_year=2024),
    )
    paths = sb.widow_scenario_paths(
        deceased_eligibility_pia=1_000.0,
        deceased_clock=deceased,
        deceased_claim_age_factor=1.0,
        own=own,
        survivor_months_early=0,
        entitlement_year=2020,
        params=ssa,
        baseline=baseline,
    )
    before = paths.baseline_monthly_by_payment_year[2023]
    after = paths.baseline_monthly_by_payment_year[2024]
    assert before < 1_500.0  # the widow(er)'s benefit alone
    assert after > 2_500.0  # the larger own benefit from 2024


def test_widow_of_worker_who_died_before_eligibility():
    baseline = _baseline()
    ssa = _ssa()
    deceased = sb.WorkerClock.at_death_before_eligibility(2016)
    common = {
        "deceased_eligibility_pia": 1_500.0,  # INVENTED supplied PIA
        "deceased_clock": deceased,
        "deceased_claim_age_factor": 1.0,
        "own": None,
        "survivor_months_early": 200,  # capped: the 71.5 percent floor
        "entitlement_year": 2018,
        "params": ssa,
        "baseline": baseline,
    }
    paths = sb.widow_scenario_paths(**common)
    assert paths.reduced_increases_by_payment_year[2030] == 14
    pia = sb.increased_pia_path(
        eligibility_pia=1_500.0,
        eligibility_year=2016,
        cola=sb.scenario_rates(baseline, None, clock=deceased),
        horizon_year=2030,
    )
    assert paths.baseline_monthly_by_payment_year[2030] == (
        ledgers.floor_to_dime(0.715 * pia[2030])
    )
    with pytest.raises(ValueError, match="never entitled"):
        sb.widow_scenario_paths(
            **common, exposure_clock=sb.ExposureClock.ENTITLEMENT
        )


# ---------------------------------------------------------------------------
# Benefit levels: existing oracle for age 62; hooks awaiting rulings
# ---------------------------------------------------------------------------
def test_di_benefit_level_hook_awaits_a_ruling():
    with pytest.raises(NotImplementedError) as raised:
        sb.di_benefit_level()
    assert str(raised.value) == "awaiting ruling: DI benefit level"
    with pytest.raises(NotImplementedError, match="DI benefit level"):
        sb.eligibility_pia_for_clock(
            sb.WorkerClock.at_di_onset(2003, entitlement_year=2004),
            history={2000: 30_000.0},
            birth_year=1960,
            params=_ssa(),
        )
    with pytest.raises(NotImplementedError, match="died before"):
        sb.eligibility_pia_for_clock(
            sb.WorkerClock.at_death_before_eligibility(2016),
            history={2000: 30_000.0},
            birth_year=1960,
            params=_ssa(),
        )


def test_age_62_pia_matches_the_sealed_ledger_computation():
    parameters = _report_parameters(_realized())
    ledger = ledgers.build_benefit_ledger(
        _invented_claimants(), parameters, draw_index=0
    )
    for claimant, person in zip(
        _invented_claimants(), ledger.people, strict=True
    ):
        history = {
            year: amount
            for year, amount in claimant.earnings_by_year.items()
            if year <= claimant.claim_year
        }
        value = sb.eligibility_pia_for_clock(
            sb.WorkerClock.at_age_62(claimant.birth_year),
            history=history,
            birth_year=claimant.birth_year,
            params=parameters.ssa,
        )
        assert struct.pack("<d", value) == struct.pack(
            "<d", person.eligibility_pia
        )
    with pytest.raises(ValueError, match="attains 62"):
        sb.eligibility_pia_for_clock(
            sb.WorkerClock(
                basis=sb.EligibilityBasis.AGE_62, eligibility_year=2013
            ),
            history={},
            birth_year=1950,
            params=parameters.ssa,
        )


# ---------------------------------------------------------------------------
# Horizon and benefit period
# ---------------------------------------------------------------------------
def test_benefit_period_maps_to_a_payment_year_and_horizon():
    assert sb.payment_year_for_reference(2030) == 2030
    assert (
        sb.payment_year_for_reference(2030, sb.BenefitPeriod.DECEMBER) == 2031
    )
    horizon = sb.payment_year_for_reference(2030, sb.BenefitPeriod.DECEMBER)
    clock = sb.WorkerClock.at_age_62(1950, entitlement_year=2012)
    paths = sb.worker_scenario_paths(
        eligibility_pia=1_000.0,
        claim_age_factor=1.0,
        clock=clock,
        baseline=_baseline(),
        horizon_year=horizon,
    )
    counts = paths.reduced_increases_by_payment_year
    assert counts[2031] == counts[2030] + 1
    assert sb.SCENARIO_HORIZON_YEAR == 2030
    assert sb.LEDGER_HORIZON_YEAR == ledgers.REPORT_YEARS[-1] == 2022
