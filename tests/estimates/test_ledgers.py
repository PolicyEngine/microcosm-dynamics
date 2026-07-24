"""Fast fixture tests for the first-estimates statutory ledgers."""

from __future__ import annotations

import statistics
from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest

from populace_dynamics.estimates import ledgers
from populace_dynamics.estimates.parameters import (
    COLASeries,
    PayrollRateLegs,
    ReportParameters,
)
from populace_dynamics.ss.params import SSAParameters


def _parameters(
    *,
    wage_base: float = 1_000_000.0,
    cola_updates: dict[int, float] | None = None,
) -> ReportParameters:
    cola = {year: 0.0 for year in range(1979, 2023)}
    cola.update(cola_updates or {})
    ssa = SSAParameters(
        nawi={year: 9_779.44 for year in range(1968, 2023)},
        wage_base={1900: wage_base},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 66 * 12)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="fixture",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )
    rates = PayrollRateLegs(
        employee_by_effective_year={1900: 0.062},
        employer_by_effective_year={1900: 0.062},
        provenance={"fixture": True},
    )
    return ReportParameters(
        ssa=ssa,
        rates=rates,
        cola=COLASeries(
            by_determination_year=cola,
            provenance={"fixture": True},
        ),
        provenance={"fixture": True},
    )


def _claimant(
    *,
    person_id: int = 1,
    weight: float = 2.0,
) -> ledgers.BenefitClaimant:
    return ledgers.BenefitClaimant(
        person_id=person_id,
        birth_year=1953,
        claim_age=62,
        claim_year=2015,
        claim_origin="modeled_award",
        weight=weight,
        earnings_by_year={
            2010: 42_000.0,
            2015: 0.0,
        },
        presence_years=frozenset({2015, 2017}),
        provenance_by_year={
            2010: "observed",
            2015: "projected",
        },
        odd_year_carried_years=frozenset({2015}),
        post_claim_earnings_by_year={2016: 999_999.0},
    )


def _projection(
    draw_index: int,
    *,
    positive_earnings: float = 150.0,
    drift_weight: bool = False,
) -> SimpleNamespace:
    slices = []
    for year in range(2014, 2023):
        first_weight = 2.5 if drift_weight and year == 2020 else 2.0
        slices.append(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3],
                    "year": [year, year, year],
                    "earnings": [positive_earnings, -10.0, float("nan")],
                    "weight": [first_weight, 1.0, 4.0],
                }
            )
        )
    return SimpleNamespace(draw_index=draw_index, slices=tuple(slices))


def _benefit_row(
    result: ledgers.BenefitLedger,
    origin: str,
    year: int,
) -> ledgers.BenefitAnnualRow:
    return next(
        row
        for row in result.annual_rows
        if row.claim_origin == origin and row.year == year
    )


def _aggregate_row(
    rows: tuple[ledgers.AcrossDrawTableRow, ...],
    **dimensions: object,
) -> ledgers.AcrossDrawTableRow:
    return next(row for row in rows if row.dimensions == dimensions)


def test_benefit_cutoff_cola_dime_presence_and_no_recomputation(monkeypatch):
    parameters = _parameters(
        cola_updates={
            # Determination 2015 -> first payment 2016.
            2015: 0.031,
            # Determination 2016 -> first payment 2017.
            2016: 0.027,
        }
    )
    calls: list[dict[int, float]] = []
    real_aime = ledgers.benefits.aime

    def recording_aime(history, birth_year, ssa):
        calls.append(dict(history))
        return real_aime(history, birth_year, ssa)

    monkeypatch.setattr(ledgers.benefits, "aime", recording_aime)
    result = ledgers.build_benefit_ledger(
        [_claimant()],
        parameters,
        draw_index=0,
    )

    assert calls == [{2010: 42_000.0, 2015: 0.0}]
    assert len(calls) == 1
    person = result.people[0]
    assert person.aime == 100
    assert person.eligibility_pia == 90.0
    assert person.claim_age_factor == pytest.approx(0.75)
    assert person.adjusted_pia_at_eligibility == 67.5
    assert person.payment_monthly_by_year == {2015: 67.5, 2017: 71.4}
    assert person.positive_post_claim_earnings is True
    assert person.award_formula_computation_count == 1
    assert person.post_claim_recomputation_count == 0

    award = _benefit_row(result, "modeled_award", 2015)
    assert award.unweighted_award_count == 1
    assert award.weighted_award_count == 2.0
    assert award.average_monthly_benefit_at_award == 67.5
    assert award.frame_annualized_benefit == 2.0 * 12 * 67.5
    assert (
        _benefit_row(result, "modeled_award", 2016).frame_annualized_benefit
        == 0.0
    )
    assert _benefit_row(
        result, "modeled_award", 2017
    ).frame_annualized_benefit == pytest.approx(2.0 * 12 * 71.4)
    assert result.diagnostics["positive_post_claim_earnings_unweighted"] == 1
    assert result.diagnostics["award_formula_computation_count"] == 1
    assert result.diagnostics["post_claim_recomputation_count"] == 0
    assert person.career_provenance_counts["projected"] == 1
    assert person.odd_year_carried_year_share == 0.5
    assert person.post_claim_earnings_years_examined == (2016,)


def test_aime_excludes_future_years_from_career_mapping(monkeypatch):
    calls: list[dict[int, float]] = []
    real_aime = ledgers.benefits.aime

    def recording_aime(history, birth_year, ssa):
        calls.append(dict(history))
        return real_aime(history, birth_year, ssa)

    monkeypatch.setattr(ledgers.benefits, "aime", recording_aime)
    claimant = replace(
        _claimant(),
        earnings_by_year={
            2010: 42_000.0,
            2015: 0.0,
            2022: 9_999_999.0,
        },
    )

    result = ledgers.build_benefit_ledger(
        [claimant],
        _parameters(),
        draw_index=0,
    )

    assert calls == [{2010: 42_000.0, 2015: 0.0}]
    assert result.people[0].aime_history_years == (2010, 2015)


def test_pia_uses_literal_birth_plus_62_year(monkeypatch):
    pia_years: list[int] = []
    real_pia = ledgers.benefits.pia

    def recording_pia(aime_value, year, ssa):
        pia_years.append(year)
        return real_pia(aime_value, year, ssa)

    monkeypatch.setattr(ledgers.benefits, "pia", recording_pia)
    claimant = replace(
        _claimant(),
        birth_year=1950,
        claim_age=65,
        claim_year=2015,
    )

    result = ledgers.build_benefit_ledger(
        [claimant],
        _parameters(),
        draw_index=0,
    )

    assert pia_years == [2012]
    assert result.people[0].eligibility_year == 2012


def test_preclaim_presence_is_not_a_payment_year():
    claimant = replace(
        _claimant(),
        claim_age=64,
        claim_year=2017,
        presence_years=frozenset({2015, 2017}),
        post_claim_earnings_by_year={2018: 1.0},
    )

    result = ledgers.build_benefit_ledger(
        [claimant],
        _parameters(),
        draw_index=0,
    )

    assert set(result.people[0].payment_monthly_by_year) == {2017}
    assert (
        _benefit_row(
            result,
            "modeled_award",
            2015,
        ).unweighted_beneficiary_count
        == 0
    )
    assert (
        _benefit_row(
            result,
            "modeled_award",
            2017,
        ).unweighted_beneficiary_count
        == 1
    )


def test_positive_postclaim_diagnostic_uses_people_and_their_weights():
    positive = _claimant(person_id=1, weight=2.0)
    nonpositive = replace(
        _claimant(person_id=2, weight=7.0),
        post_claim_earnings_by_year={
            2016: 0.0,
            2018: -1.0,
        },
    )

    result = ledgers.build_benefit_ledger(
        [positive, nonpositive],
        _parameters(),
        draw_index=0,
    )

    assert {
        person.person_id: person.positive_post_claim_earnings
        for person in result.people
    } == {1: True, 2: False}
    assert result.diagnostics["included_claimants_unweighted"] == 2
    assert result.diagnostics["included_claimants_weighted"] == 9.0
    assert result.diagnostics["positive_post_claim_earnings_unweighted"] == 1
    assert result.diagnostics["positive_post_claim_earnings_weighted"] == 2.0


def test_opening_stock_pays_only_during_actual_presence():
    claimant = ledgers.BenefitClaimant(
        person_id=8,
        birth_year=1938,
        claim_age=62,
        claim_year=2000,
        claim_origin="opening_backfill",
        weight=3.0,
        earnings_by_year={1999: 42_000.0, 2001: 10.0},
        presence_years=frozenset({2019, 2021}),
        provenance_by_year={1999: "observed", 2001: "observed"},
    )
    result = ledgers.build_benefit_ledger(
        [claimant],
        _parameters(),
        draw_index=0,
    )

    assert result.people[0].payment_monthly_by_year == {
        2019: 67.5,
        2021: 67.5,
    }
    assert all(
        row.unweighted_award_count == 0
        for row in result.annual_rows
        if row.claim_origin == "opening_backfill"
    )
    assert (
        _benefit_row(
            result, "opening_backfill", 2018
        ).unweighted_beneficiary_count
        == 0
    )
    assert (
        _benefit_row(
            result, "opening_backfill", 2019
        ).unweighted_beneficiary_count
        == 1
    )
    assert (
        _benefit_row(
            result, "opening_backfill", 2020
        ).unweighted_beneficiary_count
        == 0
    )


def test_benefit_accepts_the_career_modules_included_claimant():
    from populace_dynamics.estimates.career import (
        BirthSource,
        CareerProvenance,
        CareerRecord,
        CareerYear,
        ClaimOrigin,
        IncludedClaimant,
    )

    career = CareerRecord(
        person_id=11,
        claim_year=2015,
        coverage_start_year=2010,
        coverage_end_year=2015,
        coverage_ratio=1.0,
        imputed_year_share=0.0,
        years=(
            CareerYear(2010, 42_000.0, CareerProvenance.OBSERVED),
            CareerYear(2015, 0.0, CareerProvenance.PROJECTED),
        ),
        pre_career_years_zeroed=(),
        pre_1968_top35_zero_years=(),
    )
    included = IncludedClaimant(
        person_id=11,
        birth_year=1953,
        birth_source=BirthSource.EXACT_MARRIAGE,
        sex="male",
        weight=2.0,
        origin=ClaimOrigin.MODELED_AWARD,
        claim_age=62,
        claim_year=2015,
        first_exposure_year=2015,
        first_exposure_age=62,
        presence_years=(2015,),
        last_present_year=2015,
        career=career,
        post_claim_earnings=((2016, 999_999.0),),
    )

    result = ledgers.build_benefit_ledger(
        [included],
        _parameters(),
        draw_index=0,
    )
    person = result.people[0]
    assert person.aime_history_years == (2010, 2015)
    assert person.claim_origin == "modeled_award"
    assert person.positive_post_claim_earnings is True
    assert person.post_claim_earnings_years_examined == (2016,)
    assert person.career_provenance_counts == {
        "observed": 1,
        "gap_imputed": 0,
        "boundary_2014": 0,
        "projected": 1,
        "unknown": 0,
    }
    assert person.odd_year_carried_year_share == 0.5


def test_revenue_uses_every_person_year_nominal_cap_and_both_rate_legs():
    result = ledgers.build_revenue_ledger(
        _projection(0),
        _parameters(wage_base=100.0),
    )

    assert [row.year for row in result.annual_rows] == list(range(2015, 2023))
    row = result.annual_rows[0]
    # The design freezes min(earnings, base), not max(0, min(...)).
    assert row.weighted_taxable_payroll == 2.0 * 100.0 - 10.0
    assert row.unweighted_person_year_count == 2
    assert row.weighted_person_year_count == 3.0
    assert row.unweighted_covered_earner_count == 1
    assert row.weighted_covered_earner_count == 2.0
    assert row.employee_contributions == pytest.approx(190.0 * 0.062)
    assert row.employer_contributions == pytest.approx(190.0 * 0.062)
    assert row.combined_contributions == pytest.approx(190.0 * 0.124)

    companion = result.biennial_rows[-1]
    assert companion.end_year == 2022
    assert companion.component_years == (2021, 2022)
    assert companion.weighted_taxable_payroll == 380.0
    assert companion.odd_year_carry_pair_interpretation == (
        "2021 carries 2020 earnings; 2022 is the newly drawn even year."
    )
    assert (
        result.diagnostics["odd_year_carry_share__weighted_taxable_payroll"]
        == 0.5
    )
    assert result.population_basis == "unsplit projection.slices"
    assert result.dollar_basis == "nominal"
    assert (
        result.diagnostics["explicit_earnings_person_years_unweighted"] == 16
    )
    assert (
        result.diagnostics["projection_rows_missing_earnings_unweighted"] == 8
    )
    assert (
        result.diagnostics["projection_rows_missing_earnings_weighted"] == 32
    )


def test_revenue_rejects_incomplete_projection_and_weight_drift():
    incomplete = _projection(0)
    incomplete.slices = incomplete.slices[:-1]
    with pytest.raises(ValueError, match="complete 2014-2022"):
        ledgers.build_revenue_ledger(
            incomplete,
            _parameters(wage_base=100.0),
        )

    with pytest.raises(ValueError, match="fixed weight"):
        ledgers.build_revenue_ledger(
            _projection(0, drift_weight=True),
            _parameters(wage_base=100.0),
        )


def test_registered_draw_aggregation_uses_sample_standard_deviation():
    parameters = _parameters(wage_base=1_000.0)
    benefit_draws = [
        ledgers.build_benefit_ledger(
            [_claimant(weight=float(draw + 1))],
            parameters,
            draw_index=draw,
        )
        for draw in ledgers.DRAW_INDICES
    ]
    benefit = ledgers.aggregate_benefit_draws(benefit_draws)
    benefit_row = _aggregate_row(
        benefit.annual_rows,
        claim_origin="modeled_award",
        year=2015,
    )
    weight_summary = benefit_row.metrics["weighted_award_count"]
    assert weight_summary.mean == 10.5
    assert weight_summary.sample_sd == pytest.approx(
        statistics.stdev(range(1, 21))
    )
    assert benefit_row.metrics[
        "average_monthly_benefit_at_award"
    ].sample_sd == pytest.approx(
        0.0,
        abs=1e-15,
    )

    revenue_draws = [
        ledgers.build_revenue_ledger(
            _projection(
                draw,
                positive_earnings=float(draw + 1),
            ),
            parameters,
        )
        for draw in ledgers.DRAW_INDICES
    ]
    revenue = ledgers.aggregate_revenue_draws(revenue_draws)
    revenue_row = _aggregate_row(revenue.annual_rows, year=2015)
    # The second fixture person contributes -10 in every draw.
    expected = [2.0 * value - 10.0 for value in range(1, 21)]
    taxable_summary = revenue_row.metrics["weighted_taxable_payroll"]
    assert taxable_summary.mean == pytest.approx(statistics.mean(expected))
    assert taxable_summary.sample_sd == pytest.approx(
        statistics.stdev(expected)
    )

    with pytest.raises(ValueError, match="draw indices"):
        ledgers.aggregate_revenue_draws(revenue_draws[:-1])


def test_floor_to_dime_rejects_invalid_values():
    assert ledgers.floor_to_dime(12.399) == 12.3
    with pytest.raises(ValueError, match="negative"):
        ledgers.floor_to_dime(-0.01)
    with pytest.raises(ValueError, match="finite"):
        ledgers.floor_to_dime(float("nan"))
