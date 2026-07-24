"""Focused tests for pure first-estimates artifact assembly."""

from __future__ import annotations

import statistics
from dataclasses import replace

import pytest

from populace_dynamics.estimates.career import (
    BirthSource,
    BirthYearRecord,
    CandidateOriginRecord,
    CareerProvenance,
    CareerRecord,
    CareerYear,
    ClaimOrigin,
    DIClass,
    DIRecord,
    EntrantDiagnostic,
    IncludedClaimant,
    InclusionResult,
    WeightedCount,
    WeightedShare,
)
from populace_dynamics.estimates.first_report import (
    CONTEXT_RATIO_DISCLOSURE,
    FirstReportDrawBundle,
    build_first_estimates_artifact,
)
from populace_dynamics.estimates.ledgers import (
    BENEFIT_MEASURE_LABEL,
    EVIDENCE_LABELS,
    BenefitAnnualRow,
    BenefitBiennialRow,
    BenefitLedger,
    BenefitPersonLedger,
    RevenueAnnualRow,
    RevenueBiennialRow,
    RevenueLedger,
)
from populace_dynamics.estimates.publication import (
    validate_first_estimates_artifact,
)

_REPORT_YEARS = tuple(range(2015, 2023))
_BIENNIAL_END_YEARS = (2016, 2018, 2020, 2022)
_INCLUSION_KEYS = (
    "excluded_di_conversion",
    "excluded_di_unknown",
    "nonclaimant",
    "excluded_domain_incomplete",
    "excluded_pre1979_eligibility",
    "excluded_empty_span",
    "excluded_chronology_inconsistent",
    "excluded_low_coverage",
    "included",
    "drawn_never_claimed",
    "never_drawn",
    "origin_modeled_award",
    "origin_opening_backfill",
)


def _career(
    person_id: int,
    *,
    claim_year: int,
    opening: bool,
) -> CareerRecord:
    if opening:
        years = (
            CareerYear(1968, 0.0, CareerProvenance.UNKNOWN),
            CareerYear(1999, 40_000.0, CareerProvenance.OBSERVED),
        )
        pre_1968 = (1960,)
        coverage_start = 1968
    else:
        years = (
            CareerYear(2010, 40_000.0, CareerProvenance.OBSERVED),
            CareerYear(2013, 41_000.0, CareerProvenance.GAP_IMPUTED),
            CareerYear(2014, 42_000.0, CareerProvenance.BOUNDARY_2014),
            CareerYear(2015, 42_000.0, CareerProvenance.PROJECTED),
        )
        pre_1968 = ()
        coverage_start = 2010
    return CareerRecord(
        person_id=person_id,
        claim_year=claim_year,
        coverage_start_year=coverage_start,
        coverage_end_year=claim_year,
        coverage_ratio=0.9,
        imputed_year_share=0.1,
        years=years,
        pre_career_years_zeroed=(),
        pre_1968_top35_zero_years=pre_1968,
    )


def _included() -> tuple[IncludedClaimant, IncludedClaimant]:
    modeled_career = _career(1, claim_year=2015, opening=False)
    opening_career = _career(2, claim_year=2000, opening=True)
    return (
        IncludedClaimant(
            person_id=1,
            birth_year=1953,
            birth_source=BirthSource.EXACT_MARRIAGE,
            sex="male",
            weight=1.0,
            origin=ClaimOrigin.MODELED_AWARD,
            claim_age=62,
            claim_year=2015,
            first_exposure_year=2015,
            first_exposure_age=62,
            presence_years=(2015, 2016),
            last_present_year=2016,
            career=modeled_career,
            post_claim_earnings=((2016, 1.0),),
        ),
        IncludedClaimant(
            person_id=2,
            birth_year=1938,
            birth_source=BirthSource.INFERRED_PERIOD_AGE,
            sex="female",
            weight=2.0,
            origin=ClaimOrigin.OPENING_BACKFILL,
            claim_age=62,
            claim_year=2000,
            first_exposure_year=2015,
            first_exposure_age=77,
            presence_years=(2015, 2016),
            last_present_year=2016,
            career=opening_career,
            post_claim_earnings=(),
        ),
    )


def _count(key: str, unweighted: int, weighted: float) -> WeightedCount:
    return WeightedCount(key, unweighted, weighted)


def _inclusion() -> InclusionResult:
    included = _included()
    counts = []
    for key in _INCLUSION_KEYS:
        if key == "included":
            counts.append(_count(key, 2, 3.0))
        elif key == "origin_modeled_award":
            counts.append(_count(key, 1, 1.0))
        elif key == "origin_opening_backfill":
            counts.append(_count(key, 1, 2.0))
        else:
            counts.append(_count(key, 0, 0.0))
    return InclusionResult(
        births=(
            BirthYearRecord(1, 1953, BirthSource.EXACT_MARRIAGE),
            BirthYearRecord(2, 1938, BirthSource.INFERRED_PERIOD_AGE),
        ),
        di_partition=(
            DIRecord(1, DIClass.NON_DI),
            DIRecord(2, DIClass.NON_DI),
        ),
        nonclaimants=(),
        origins=(
            CandidateOriginRecord(
                person_id=1,
                origin=ClaimOrigin.MODELED_AWARD,
                first_exposure_year=2015,
                first_exposure_age=62,
                engine_claim_age=62,
                engine_claim_year=2015,
                operative_claim_age=62,
                operative_claim_year=2015,
                schedule_year=None,
                schedule_snap=None,
            ),
            CandidateOriginRecord(
                person_id=2,
                origin=ClaimOrigin.OPENING_BACKFILL,
                first_exposure_year=2015,
                first_exposure_age=77,
                engine_claim_age=62,
                engine_claim_year=2015,
                operative_claim_age=62,
                operative_claim_year=2000,
                schedule_year=1998,
                schedule_snap="lower",
            ),
        ),
        exclusions=(),
        included=included,
        counts=tuple(counts),
        birth_source_counts=(
            _count("exact_marriage", 1, 1.0),
            _count("inferred_period_age", 1, 2.0),
            _count("synthetic_native", 0, 0.0),
        ),
        opening_stock_snap_counts=(
            _count("lower_endpoint", 1, 2.0),
            _count("upper_endpoint", 0, 0.0),
        ),
        opening_stock_snap_denominator=_count(
            "included_opening_backfill", 1, 2.0
        ),
        opening_stock_snap_weighted_shares=(
            WeightedShare("lower_endpoint", 2.0, 2.0, 1.0),
            WeightedShare("upper_endpoint", 0.0, 2.0, 0.0),
        ),
        entrant_diagnostic=EntrantDiagnostic(
            (),
            _count("explicit_2016_2018_row_entrant", 0, 0.0),
        ),
    )


def _benefit_people(draw_index: int) -> tuple[BenefitPersonLedger, ...]:
    common = {
        "aime": 100.0,
        "eligibility_pia": 90.0,
        "claim_age_factor": 1.0,
        "adjusted_pia_at_eligibility": 90.0,
        "aime_history_years": (1999,),
        "positive_post_claim_earnings": False,
        "post_claim_earnings_years_examined": (),
        "career_provenance_counts": {
            "observed": 1,
            "gap_imputed": 0,
            "boundary_2014": 0,
            "projected": 0,
            "unknown": 0,
        },
        "career_provenance_shares": {
            "observed": 1.0,
            "gap_imputed": 0.0,
            "boundary_2014": 0.0,
            "projected": 0.0,
            "unknown": 0.0,
        },
        "odd_year_carried_year_share": 0.0,
    }
    return (
        BenefitPersonLedger(
            person_id=1,
            birth_year=1953,
            eligibility_year=2015,
            claim_age=62,
            claim_year=2015,
            claim_origin="modeled_award",
            weight=1.0,
            monthly_benefit_at_award=100.0 + draw_index,
            payment_monthly_by_year={2015: 100.0 + draw_index},
            **common,
        ),
        BenefitPersonLedger(
            person_id=2,
            birth_year=1938,
            eligibility_year=2000,
            claim_age=62,
            claim_year=2000,
            claim_origin="opening_backfill",
            weight=2.0,
            monthly_benefit_at_award=200.0 + draw_index,
            payment_monthly_by_year={2015: 200.0 + draw_index},
            **common,
        ),
    )


def _benefits(draw_index: int) -> BenefitLedger:
    annual = []
    for origin in ("modeled_award", "opening_backfill"):
        for year in _REPORT_YEARS:
            modeled_award = origin == "modeled_award" and year == 2015
            beneficiary = year == 2015
            annual.append(
                BenefitAnnualRow(
                    claim_origin=origin,
                    year=year,
                    unweighted_award_count=int(modeled_award),
                    weighted_award_count=float(modeled_award),
                    average_monthly_benefit_at_award=(
                        100.0 + draw_index if modeled_award else None
                    ),
                    unweighted_beneficiary_count=int(beneficiary),
                    weighted_beneficiary_count=(
                        (1.0 if origin == "modeled_award" else 2.0)
                        if beneficiary
                        else 0.0
                    ),
                    frame_annualized_benefit=(
                        (1_200.0 if origin == "modeled_award" else 4_800.0)
                        + draw_index
                        if beneficiary
                        else 0.0
                    ),
                )
            )
    biennial = []
    for origin in ("modeled_award", "opening_backfill"):
        for end_year in _BIENNIAL_END_YEARS:
            first_pair = end_year == 2016
            biennial.append(
                BenefitBiennialRow(
                    claim_origin=origin,
                    end_year=end_year,
                    component_years=(end_year - 1, end_year),
                    unweighted_award_count=int(
                        first_pair and origin == "modeled_award"
                    ),
                    weighted_award_count=float(
                        first_pair and origin == "modeled_award"
                    ),
                    average_monthly_benefit_at_award=(
                        100.0 + draw_index
                        if first_pair and origin == "modeled_award"
                        else None
                    ),
                    unweighted_beneficiary_count=int(first_pair),
                    weighted_beneficiary_count=(
                        (1.0 if origin == "modeled_award" else 2.0)
                        if first_pair
                        else 0.0
                    ),
                    frame_annualized_benefit=(
                        (1_200.0 if origin == "modeled_award" else 4_800.0)
                        + draw_index
                        if first_pair
                        else 0.0
                    ),
                )
            )
    return BenefitLedger(
        draw_index=draw_index,
        people=_benefit_people(draw_index),
        annual_rows=tuple(annual),
        biennial_rows=tuple(biennial),
        diagnostics={
            "included_claimants_unweighted": 2.0,
            "post_claim_recomputation_count": 0.0,
            "fixture_draw_value": float(draw_index),
        },
    )


def _revenue(draw_index: int) -> RevenueLedger:
    annual = tuple(
        RevenueAnnualRow(
            year=year,
            unweighted_person_year_count=2,
            weighted_person_year_count=3.0,
            unweighted_covered_earner_count=2,
            weighted_covered_earner_count=3.0,
            weighted_taxable_payroll=10_000.0 + draw_index,
            employee_contributions=620.0 + draw_index,
            employer_contributions=620.0 + draw_index,
            combined_contributions=1_240.0 + draw_index,
            odd_year_carry_affected=year % 2 == 1,
        )
        for year in _REPORT_YEARS
    )
    biennial = tuple(
        RevenueBiennialRow(
            end_year=end_year,
            component_years=(end_year - 1, end_year),
            unweighted_person_year_count=4,
            weighted_person_year_count=6.0,
            unweighted_covered_earner_count=4,
            weighted_covered_earner_count=6.0,
            weighted_taxable_payroll=20_000.0 + draw_index,
            employee_contributions=1_240.0 + draw_index,
            employer_contributions=1_240.0 + draw_index,
            combined_contributions=2_480.0 + draw_index,
            odd_year_carry_pair_interpretation="fixture pair",
        )
        for end_year in _BIENNIAL_END_YEARS
    )
    return RevenueLedger(
        draw_index=draw_index,
        annual_rows=annual,
        biennial_rows=biennial,
        diagnostics={
            "explicit_earnings_person_years_unweighted": 16.0,
            "fixture_draw_value": float(draw_index),
        },
    )


def _bundle(draw_index: int) -> FirstReportDrawBundle:
    return FirstReportDrawBundle(
        draw_index=draw_index,
        inclusion=_inclusion(),
        benefits=_benefits(draw_index),
        revenue=_revenue(draw_index),
    )


def _configuration() -> dict:
    return {
        "registration_reference": "issue-42-comment-registered",
        "projection": {"draw_indices": list(range(20))},
        "parameters": {"bundle_sha256": "c" * 64},
    }


def _find_aggregate(
    rows: list[dict],
    *,
    metric: str,
    **dimensions: object,
) -> dict:
    return next(
        row
        for row in rows
        if row["metric"] == metric
        and all(row.get(key) == value for key, value in dimensions.items())
    )


def test_builds_complete_three_table_artifact_with_flat_aggregates():
    configuration = _configuration()
    artifact = build_first_estimates_artifact(
        [_bundle(draw_index) for draw_index in reversed(range(20))],
        configuration_echo=configuration,
        environment_sidecar_sha256="a" * 64,
    )

    assert set(artifact["tables"]) == {
        "modeled_award_flow",
        "opening_stock",
        "revenue",
    }
    for table in artifact["tables"].values():
        assert table["labels"] == list(EVIDENCE_LABELS)
        assert {row["draw_index"] for row in table["per_draw"]} == set(
            range(20)
        )
        assert {row["row_basis"] for row in table["biennial_companion"]} == {
            "per_draw",
            "across_draw",
        }
        assert all(
            "mean" in row and "sample_sd" in row and "metrics" not in row
            for row in table["aggregate"]
        )

    modeled = artifact["tables"]["modeled_award_flow"]
    assert all(
        row["claim_origin"] == "modeled_award" for row in modeled["per_draw"]
    )
    assert all(
        row["claim_origin"] == "modeled_award" for row in modeled["aggregate"]
    )
    award = _find_aggregate(
        modeled["aggregate"],
        metric="average_monthly_benefit_at_award",
        claim_origin="modeled_award",
        year=2015,
    )
    assert award["mean"] == 109.5
    assert award["sample_sd"] == pytest.approx(
        statistics.stdev(100.0 + draw for draw in range(20))
    )

    assert artifact["tables"]["opening_stock"]["unit_label"].startswith(
        "report-only imputed opening stock"
    )
    assert artifact["tables"]["revenue"]["unit_label"].endswith(
        "labor-income proxy"
    )
    assert artifact["counts"]["entrant_diagnostic"] == {
        "source_income_years": [2016, 2018],
        "may_overlap_inclusion_classes": True,
        "operative_exclusion_rule": False,
    }
    included = _find_aggregate(
        artifact["counts"]["aggregate"],
        metric="inclusion__included__unweighted",
    )
    assert included["mean"] == 2.0
    assert included["sample_sd"] == 0.0
    assert len(artifact["diagnostics"]["included_career_per_draw"]) == 40
    assert artifact["diagnostics"]["context_ratio"] == (
        CONTEXT_RATIO_DISCLOSURE
    )
    assert artifact["diagnostics"]["context_ratio"]["status"] == (
        "not_computed"
    )
    assert "design_question" in artifact["diagnostics"]["context_ratio"]
    assert BENEFIT_MEASURE_LABEL in artifact["diagnostics"]["benefit_measure"]

    validate_first_estimates_artifact(
        artifact,
        expected_configuration_echo=configuration,
    )


@pytest.mark.parametrize(
    "bundles",
    [
        [_bundle(draw_index) for draw_index in range(19)],
        [_bundle(draw_index) for draw_index in range(19)] + [_bundle(18)],
    ],
)
def test_requires_exactly_one_of_each_registered_draw(bundles):
    with pytest.raises(ValueError, match="requires draw indices"):
        build_first_estimates_artifact(
            bundles,
            configuration_echo=_configuration(),
            environment_sidecar_sha256="a" * 64,
        )


def test_rejects_configuration_or_cross_ledger_identity_drift():
    configuration = _configuration()
    configuration["projection"]["draw_indices"] = list(range(19))
    with pytest.raises(ValueError, match="configuration must register"):
        build_first_estimates_artifact(
            [_bundle(draw_index) for draw_index in range(20)],
            configuration_echo=configuration,
            environment_sidecar_sha256="a" * 64,
        )

    bundles = [_bundle(draw_index) for draw_index in range(20)]
    bundles[7] = replace(
        bundles[7],
        revenue=replace(bundles[7].revenue, draw_index=8),
    )
    with pytest.raises(ValueError, match="ledger draw indices"):
        build_first_estimates_artifact(
            bundles,
            configuration_echo=_configuration(),
            environment_sidecar_sha256="a" * 64,
        )


def test_rejects_incomplete_ledger_grid_and_recomputation():
    bundles = [_bundle(draw_index) for draw_index in range(20)]
    bundles[0] = replace(
        bundles[0],
        benefits=replace(
            bundles[0].benefits,
            annual_rows=bundles[0].benefits.annual_rows[:-1],
        ),
    )
    with pytest.raises(ValueError, match="annual row grid"):
        build_first_estimates_artifact(
            bundles,
            configuration_echo=_configuration(),
            environment_sidecar_sha256="a" * 64,
        )

    bundles = [_bundle(draw_index) for draw_index in range(20)]
    bundles[0] = replace(
        bundles[0],
        benefits=replace(
            bundles[0].benefits,
            diagnostics={
                **bundles[0].benefits.diagnostics,
                "post_claim_recomputation_count": 1.0,
            },
        ),
    )
    with pytest.raises(ValueError, match="recomputation"):
        build_first_estimates_artifact(
            bundles,
            configuration_echo=_configuration(),
            environment_sidecar_sha256="a" * 64,
        )
