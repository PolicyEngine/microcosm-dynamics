"""Committed-fixture rebuild of the first-estimates statutory pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from populace_dynamics.engine.steps import ClaimingSchedule
from populace_dynamics.estimates.career import (
    build_career_inclusion,
    build_population_roster,
)
from populace_dynamics.estimates.ledgers import (
    EVIDENCE_LABELS,
    build_benefit_ledger,
    build_revenue_ledger,
)
from populace_dynamics.estimates.parameters import (
    COLASeries,
    PayrollRateLegs,
    ReportParameters,
)
from populace_dynamics.ss.params import SSAParameters

FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "first_estimates_pipeline_v1.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _trajectory(document: dict) -> pd.DataFrame:
    metadata = {
        int(row["person_id"]): row
        for row in (
            *document["initial_population"],
            *(
                row
                for rows in document["scheduled_entries_by_year"].values()
                for row in rows
            ),
        )
    }
    rows = []
    for spec in document["trajectory_specs"]:
        person_id = int(spec["person_id"])
        birth_year = int(spec["birth_year"])
        for year in spec["years"]:
            post_start = year > 2014
            di_value = False if post_start else pd.NA
            raw_override = spec.get("di_by_year", {}).get(str(year), di_value)
            rows.append(
                {
                    "person_id": person_id,
                    "year": year,
                    "age": year - birth_year,
                    "sex": metadata[person_id]["sex"],
                    "weight": metadata[person_id]["weight"],
                    "earnings": spec["earnings"],
                    "claim_age": (
                        spec.get("claim_age", pd.NA) if post_start else pd.NA
                    ),
                    "claim_year": (
                        spec.get("claim_year", pd.NA)
                        if post_start and "claim_year" in spec
                        else pd.NA
                    ),
                    "di_converted": (
                        pd.NA if raw_override is None else raw_override
                    ),
                    "birth_year": spec.get("native_birth_year", pd.NA),
                }
            )
    return pd.DataFrame(rows)


def _observed(document: dict) -> pd.DataFrame:
    weights = {
        int(row["person_id"]): float(row["weight"])
        for row in (
            *document["initial_population"],
            *(
                row
                for rows in document["scheduled_entries_by_year"].values()
                for row in rows
            ),
        )
    }
    rows = []
    for spec in document["observed_series"]:
        person_id = int(spec["person_id"])
        birth_year = spec["birth_year_for_age"]
        for year in spec["years"]:
            rows.append(
                {
                    "person_id": person_id,
                    "period": year,
                    "age": (
                        pd.NA if birth_year is None else year - birth_year
                    ),
                    "earnings": spec["earnings"],
                    "weight": weights[person_id],
                }
            )
    return pd.DataFrame(rows)


def _schedule(document: dict) -> ClaimingSchedule:
    raw = document["claiming_schedule"]
    return ClaimingSchedule(
        {
            (sex, int(year)): {
                int(age): float(probability)
                for age, probability in raw[sex].items()
            }
            for sex in ("female", "male")
            for year in raw["years"]
        }
    )


def _parameters(document: dict) -> ReportParameters:
    raw = document["parameters"]
    cola = {year: 0.0 for year in range(1979, 2023)}
    cola.update(
        {
            int(year): float(rate)
            for year, rate in raw["cola_by_payment_year"].items()
        }
    )
    return ReportParameters(
        ssa=SSAParameters(
            nawi={year: 100.0 for year in range(1900, 2023)},
            wage_base={1900: float(raw["wage_base"])},
            pia_factors=(0.9, 0.32, 0.15),
            fra_months_by_birth_year=[(1900, 66 * 12)],
            early_monthly_rates=(5 / 900, 5 / 1200),
            early_first_bracket_months=36,
            pe_us_revision="committed-fixture",
            delayed_credit_by_birth_year=[(1900, 0.08)],
        ),
        rates=PayrollRateLegs(
            employee_by_effective_year={1900: float(raw["employee_rate"])},
            employer_by_effective_year={1900: float(raw["employer_rate"])},
            provenance={"source": "committed-fixture"},
        ),
        cola=COLASeries(
            by_payment_year=cola,
            provenance={"source": "committed-fixture"},
        ),
        provenance={"source": "committed-fixture"},
    )


def _projection(trajectory: pd.DataFrame) -> SimpleNamespace:
    slices = tuple(
        trajectory.loc[
            trajectory["year"] == year,
            ["person_id", "year", "earnings", "weight"],
        ].reset_index(drop=True)
        for year in range(2014, 2023)
    )
    return SimpleNamespace(draw_index=0, slices=slices)


def _annual_row(rows: tuple, year: int, origin: str | None = None):
    return next(
        row
        for row in rows
        if row.year == year and (origin is None or row.claim_origin == origin)
    )


def _assert_numeric_record(actual, expected: dict) -> None:
    for key, value in expected.items():
        assert getattr(actual, key) == pytest.approx(value)


def test_committed_fixture_rebuilds_join_inclusion_and_both_ledgers():
    document = _fixture()
    trajectory = _trajectory(document)
    observed = _observed(document)
    initial = pd.DataFrame(document["initial_population"])
    scheduled = {
        int(year): pd.DataFrame(rows)
        for year, rows in document["scheduled_entries_by_year"].items()
    }
    roster = build_population_roster(initial, scheduled, trajectory)
    marriage = pd.DataFrame(document["marriage_history"])
    result = build_career_inclusion(
        trajectory,
        roster,
        observed,
        marriage,
        {
            int(person_id): int(year)
            for person_id, year in document["synthetic_birth_years"].items()
        },
        _schedule(document),
        document["earnings_domain_ids"],
        stock_imputation_root_seed=document["stock_imputation_root_seed"],
    )
    expected = document["expected"]

    assert roster["person_id"].tolist() == list(range(1, 14))
    assert 8 not in set(trajectory["person_id"])
    assert roster.set_index("person_id").loc[8, "seed_year"] == 2016
    assert {
        str(row.person_id): row.source.value
        for row in result.births
        if str(row.person_id) in expected["birth_sources"]
    } == expected["birth_sources"]
    assert (
        next(row for row in result.births if row.person_id == 1).birth_year
        == 1953
    )
    assert {row.classification.value for row in result.di_partition} == {
        "di_conversion",
        "di_unknown",
        "non_di",
    }
    assert {
        str(row.person_id): row.classification.value
        for row in result.di_partition
        if str(row.person_id) in expected["di_partition"]
    } == expected["di_partition"]
    assert {
        str(row.person_id): row.path.value for row in result.nonclaimants
    } == expected["nonclaimants"]
    assert [row.person_id for row in result.included] == expected[
        "included_ids"
    ]
    assert {
        str(row.person_id): row.reason for row in result.exclusions
    } == expected["exclusions"]

    counts = {row.key: row for row in result.counts}
    for key, value in expected["stage_counts_unweighted"].items():
        assert counts[key].unweighted == value
    assert sum(
        counts[key].unweighted for key in expected["stage_counts_unweighted"]
    ) == len(roster)

    origins = {row.person_id: row for row in result.origins}
    assert origins[1].origin.value == "modeled_award"
    assert origins[2].origin.value == "opening_backfill"
    assert origins[3].origin.value == "opening_backfill"
    for person_id, expected_origin in expected["opening_imputation"].items():
        origin = origins[int(person_id)]
        for key, value in expected_origin.items():
            assert getattr(origin, key) == value
    for person_id in (2, 3):
        origin = origins[person_id]
        pmf = document["claiming_schedule"][
            roster.set_index("person_id").loc[person_id, "sex"]
        ]
        assert str(origin.first_exposure_age) in pmf
        assert pmf[str(origin.first_exposure_age)] > 0
        assert origin.operative_claim_age < origin.first_exposure_age
        assert origin.schedule_year == 2000

    included = {row.person_id: row for row in result.included}
    assert included[1].last_present_year == 2016
    assert included[1].presence_years == (2014, 2015, 2016)
    provenance = {
        year.year: year.provenance.value for year in included[1].career.years
    }
    assert provenance[1997] == "gap_imputed"
    assert provenance[2013] == "gap_imputed"
    assert provenance[2014] == "boundary_2014"
    assert provenance[2015] == "projected"
    assert included[1].career.imputed_year_share > 0
    assert included[1].career.affected_odd_year_share > 0
    assert included[2].career.top35_reaches_pre_1968
    assert result.opening_stock_snap_denominator.unweighted == 2
    snap_shares = {
        row.key: row.share for row in result.opening_stock_snap_weighted_shares
    }
    assert snap_shares == {
        "lower_endpoint": pytest.approx(0.25),
        "upper_endpoint": pytest.approx(0.75),
    }
    assert result.entrant_diagnostic.person_ids == (9,)
    assert result.entrant_diagnostic.may_overlap_inclusion_classes
    assert not result.entrant_diagnostic.operative_exclusion_rule

    births = {row.person_id: row.birth_year for row in result.births}
    assert 9 not in set(document["earnings_domain_ids"])
    assert births[9] + 62 < 1979
    assert (
        next(row for row in result.exclusions if row.person_id == 9).reason
        == "excluded_domain_incomplete"
    )
    coverage_start_11 = max(1968, births[11] + 22)
    coverage_end_11 = min(origins[11].operative_claim_year, 2022)
    assert coverage_start_11 > coverage_end_11
    assert births[11] + 62 > origins[11].operative_claim_year
    assert (
        next(row for row in result.exclusions if row.person_id == 11).reason
        == "excluded_empty_span"
    )

    parameters = _parameters(document)
    benefits = build_benefit_ledger(
        result.included,
        parameters,
        draw_index=0,
    )
    benefit_people = {row.person_id: row for row in benefits.people}
    for person_id, expected_person in expected["benefit_people"].items():
        person = benefit_people[int(person_id)]
        assert person.aime == expected_person["aime"]
        assert (
            person.monthly_benefit_at_award
            == expected_person["monthly_benefit_at_award"]
        )
        assert (
            person.payment_monthly_by_year[2015]
            == expected_person["payment_2015"]
        )
        assert (
            person.payment_monthly_by_year[2016]
            == expected_person["payment_2016"]
        )
    assert benefit_people[1].payment_monthly_by_year == {
        2015: 5.4,
        2016: 5.9,
    }
    assert benefit_people[1].positive_post_claim_earnings
    assert benefit_people[1].odd_year_carried_year_share > 0
    assert all(
        row.award_formula_computation_count == 1
        and row.post_claim_recomputation_count == 0
        for row in benefits.people
    )
    modeled_2015 = _annual_row(
        benefits.annual_rows,
        2015,
        "modeled_award",
    )
    assert modeled_2015.weighted_award_count == 2.0
    assert modeled_2015.average_monthly_benefit_at_award == 5.4
    assert modeled_2015.frame_annualized_benefit == 2 * 12 * 5.4
    _assert_numeric_record(
        _annual_row(
            benefits.annual_rows,
            2015,
            "opening_backfill",
        ),
        expected["opening_benefit_2015"],
    )
    assert benefits.diagnostics["award_formula_computation_count"] == 3
    assert benefits.diagnostics["post_claim_recomputation_count"] == 0
    assert benefits.diagnostics["career_gap_imputed_years_unweighted"] > 0
    assert benefits.diagnostics["odd_year_carried_share_mean_weighted"] > 0
    assert benefits.biennial_rows[0].odd_year_carry_disclosure
    assert benefits.evidence_labels == EVIDENCE_LABELS

    revenue = build_revenue_ledger(
        _projection(trajectory),
        parameters,
    )
    _assert_numeric_record(
        _annual_row(revenue.annual_rows, 2015),
        expected["revenue_2015"],
    )
    _assert_numeric_record(
        _annual_row(revenue.annual_rows, 2017),
        expected["revenue_2017"],
    )
    assert revenue.diagnostics[
        "odd_year_carry_share__weighted_taxable_payroll"
    ] == pytest.approx(0.5)
    assert revenue.biennial_rows[0].component_years == (2015, 2016)
    assert revenue.biennial_rows[0].weighted_taxable_payroll == 380.0
    assert revenue.population_basis == "unsplit projection.slices"
    assert revenue.earnings_measure_label == "labor-income proxy"
    assert revenue.evidence_labels == EVIDENCE_LABELS
