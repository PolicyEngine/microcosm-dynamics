"""Fast fixtures for the first-estimates career and inclusion laws."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from populace_dynamics.engine.steps import ClaimingSchedule
from populace_dynamics.estimates import career as career_module
from populace_dynamics.estimates.career import (
    BirthSource,
    CareerProvenance,
    ClaimOrigin,
    DIClass,
    NonClaimantPath,
    build_career,
    build_career_inclusion,
    build_population_roster,
    classify_di_trajectory,
    derive_birth_years,
)


def _schedule(
    pmf: dict[int, float] | None = None,
) -> ClaimingSchedule:
    values = pmf or {62: 1.0}
    return ClaimingSchedule(
        {
            (sex, year): dict(values)
            for sex in ("female", "male")
            for year in range(1998, 2014)
        }
    )


def _observed_rows(
    person_id: int,
    birth_year: int,
    *,
    years: list[int] | None = None,
    earnings: float = 10.0,
) -> list[dict[str, int | float]]:
    observed_years = years
    if observed_years is None:
        observed_years = [
            *range(1968, 1997),
            *range(1998, 2013, 2),
        ]
    return [
        {
            "person_id": person_id,
            "period": year,
            "earnings": earnings,
            "age": year - birth_year,
            "weight": 1.0,
        }
        for year in observed_years
    ]


def _trajectory_rows(
    person_id: int,
    birth_year: int,
    *,
    sex: str = "female",
    weight: float = 1.0,
    claim_age: int | None = None,
    claim_year: int | None = None,
    years: tuple[int, ...] = (2014, 2015, 2016),
    di_values: tuple[object, ...] = (pd.NA, False, False),
) -> list[dict[str, object]]:
    rows = []
    for index, year in enumerate(years):
        exposed = year > 2014 and claim_age is not None
        stamped = (
            exposed
            and claim_year is not None
            and year >= min(claim_year, 2015)
        )
        rows.append(
            {
                "person_id": person_id,
                "year": year,
                "age": year - birth_year,
                "sex": sex,
                "weight": weight,
                "earnings": float(year - 2000),
                "claim_age": claim_age if exposed else pd.NA,
                "claim_year": claim_year if stamped else pd.NA,
                "di_converted": di_values[index],
            }
        )
    return rows


def _roster(
    specs: list[tuple[int, str, float]],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"person_id": person_id, "sex": sex, "weight": weight}
            for person_id, sex, weight in specs
        ]
    )


def _year(record, year: int):
    return next(value for value in record.years if value.year == year)


def test_birth_precedence_and_rounding():
    marriage = pd.DataFrame(
        {
            "person_id": [1, 1, 2],
            "birth_year": [1950, 1950, pd.NA],
        }
    )
    observed = pd.DataFrame(
        [
            {
                "person_id": 1,
                "period": 2000,
                "age": 49,
                "earnings": 1.0,
            },
            {
                "person_id": 2,
                "period": 2000,
                "age": 49,
                "earnings": 1.0,
            },
            {
                "person_id": 2,
                "period": 2002,
                "age": 50,
                "earnings": 1.0,
            },
        ]
    )
    records = {
        record.person_id: record
        for record in derive_birth_years(
            marriage, observed, {3: 2020, 1: 1949}
        )
    }

    assert records[1].birth_year == 1950
    assert records[1].source is BirthSource.EXACT_MARRIAGE
    assert records[2].birth_year == 1952
    assert records[2].source is BirthSource.INFERRED_PERIOD_AGE
    assert records[3].birth_year == 2020
    assert records[3].source is BirthSource.SYNTHETIC_NATIVE


def test_conflicting_exact_birth_years_fail_closed():
    marriage = pd.DataFrame({"person_id": [1, 1], "birth_year": [1950, 1951]})
    observed = pd.DataFrame(columns=["person_id", "period", "age"])
    with pytest.raises(ValueError, match="conflicting exact birth"):
        derive_birth_years(marriage, observed)


def test_cutoff_runs_before_gap_imputation():
    observed = pd.DataFrame(
        [
            {
                "person_id": 1,
                "period": 2010,
                "earnings": 10.0,
            },
            {
                "person_id": 1,
                "period": 2012,
                "earnings": 30.0,
            },
        ]
    )
    trajectory = pd.DataFrame(
        [{"person_id": 1, "year": 2014, "earnings": 50.0}]
    )

    career = build_career(
        person_id=1,
        birth_year=1970,
        claim_year=2011,
        observed_earnings=observed,
        trajectory=trajectory,
    )

    assert _year(career, 2011).earnings == 10.0
    assert _year(career, 2011).provenance is CareerProvenance.GAP_IMPUTED
    assert all(year.year <= 2011 for year in career.years)


@pytest.mark.parametrize(
    ("claim_year", "include_2012", "expected_2013", "expected_provenance"),
    [
        (2013, True, 20.0, CareerProvenance.GAP_IMPUTED),
        (2013, False, 0.0, CareerProvenance.UNKNOWN),
        (2014, True, 30.0, CareerProvenance.GAP_IMPUTED),
        (2014, False, 40.0, CareerProvenance.GAP_IMPUTED),
    ],
)
def test_corrected_2013_boundary_seam(
    claim_year: int,
    include_2012: bool,
    expected_2013: float,
    expected_provenance: CareerProvenance,
):
    rows = [{"person_id": 1, "period": 2010, "earnings": 10.0}]
    if include_2012:
        rows.append({"person_id": 1, "period": 2012, "earnings": 20.0})
    observed = pd.DataFrame(rows)
    trajectory = pd.DataFrame(
        [
            {"person_id": 1, "year": 2014, "earnings": 40.0},
            {"person_id": 1, "year": 2015, "earnings": 40.0},
        ]
    )

    career = build_career(
        person_id=1,
        birth_year=1970,
        claim_year=claim_year,
        observed_earnings=observed,
        trajectory=trajectory,
    )

    seam = _year(career, 2013)
    assert seam.earnings == expected_2013
    assert seam.provenance is expected_provenance
    if not include_2012:
        assert _year(career, 2012).provenance is CareerProvenance.UNKNOWN
    if claim_year == 2014:
        assert _year(career, 2014).provenance is CareerProvenance.BOUNDARY_2014


def test_structural_odd_gap_and_precareer_zero_diagnostics():
    observed = pd.DataFrame(
        [
            {"person_id": 1, "period": 1996, "earnings": 10.0},
            {"person_id": 1, "period": 1998, "earnings": 30.0},
            {"person_id": 1, "period": 2000, "earnings": 99.0},
        ]
    )
    trajectory = pd.DataFrame(
        [{"person_id": 1, "year": 2014, "earnings": 40.0}]
    )
    career = build_career(
        person_id=1,
        birth_year=1980,
        claim_year=2014,
        observed_earnings=observed,
        trajectory=trajectory,
    )

    assert career.coverage_start_year == 2002
    assert 2000 in career.pre_career_years_zeroed
    assert all(year.year >= 2002 for year in career.years)

    older = build_career(
        person_id=1,
        birth_year=1917,
        claim_year=1979,
        observed_earnings=pd.DataFrame(
            _observed_rows(1, 1917, years=list(range(1968, 1980)))
        ),
        trajectory=trajectory,
    )
    assert older.top35_reaches_pre_1968
    assert len(older.pre_1968_top35_zero_years) == 23


def test_di_precedence_uses_only_extant_post_start_rows():
    trajectory = pd.DataFrame(
        [
            {"person_id": 1, "year": 2014, "di_converted": pd.NA},
            {"person_id": 1, "year": 2015, "di_converted": False},
            {"person_id": 2, "year": 2014, "di_converted": pd.NA},
            {"person_id": 2, "year": 2015, "di_converted": False},
            {"person_id": 2, "year": 2016, "di_converted": pd.NA},
            {"person_id": 3, "year": 2014, "di_converted": pd.NA},
            {"person_id": 3, "year": 2015, "di_converted": pd.NA},
            {"person_id": 3, "year": 2016, "di_converted": True},
            {"person_id": 4, "year": 2014, "di_converted": pd.NA},
        ]
    )
    classes = {
        record.person_id: record.classification
        for record in classify_di_trajectory(
            trajectory, population_ids={1, 2, 3, 4, 5}
        )
    }

    assert classes == {
        1: DIClass.NON_DI,
        2: DIClass.DI_UNKNOWN,
        3: DIClass.DI_CONVERSION,
        4: DIClass.NON_DI,
        5: DIClass.NON_DI,
    }


def test_population_roster_retains_never_returned_scheduled_person():
    initial = _roster([(1, "female", 1.0)])
    scheduled = {2017: _roster([(2, "male", 2.0)])}
    trajectory = pd.DataFrame(
        _trajectory_rows(1, 1952, claim_age=None, claim_year=None)
    )

    roster = build_population_roster(initial, scheduled, trajectory)

    assert roster["person_id"].tolist() == [1, 2]
    assert roster.set_index("person_id").loc[2, "weight"] == 2.0


def test_four_stage_partition_origin_and_snap_diagnostics():
    rows = []
    rows.extend(_trajectory_rows(1, 1952, claim_age=63, claim_year=2015))
    rows.extend(
        _trajectory_rows(
            2,
            1917,
            sex="male",
            weight=2.0,
            claim_age=62,
            claim_year=2015,
        )
    )
    rows.extend(_trajectory_rows(3, 1950, claim_age=70))
    rows.extend(_trajectory_rows(4, 1950))
    rows.extend(
        _trajectory_rows(
            5,
            1950,
            di_values=(pd.NA, True, pd.NA),
        )
    )
    rows.extend(
        _trajectory_rows(
            6,
            1950,
            di_values=(pd.NA, False, pd.NA),
        )
    )
    trajectory = pd.DataFrame(rows)
    roster = _roster(
        [
            (1, "female", 1.0),
            (2, "male", 2.0),
            (3, "female", 1.0),
            (4, "female", 1.0),
            (5, "female", 1.0),
            (6, "female", 1.0),
            (7, "male", 3.0),
        ]
    )
    observed = pd.DataFrame(
        [
            *_observed_rows(1, 1952),
            *_observed_rows(2, 1917),
            {
                "person_id": 4,
                "period": 2016,
                "earnings": 1.0,
                "age": 66,
                "weight": 1.0,
            },
        ]
    )
    marriage = pd.DataFrame(
        {
            "person_id": [*range(1, 8), 99],
            "birth_year": [
                1952,
                1917,
                1950,
                1950,
                1950,
                1950,
                1950,
                1900,
            ],
        }
    )

    result = build_career_inclusion(
        trajectory,
        roster,
        observed,
        marriage,
        {},
        _schedule(),
        {1, 2, 3},
        stock_imputation_root_seed=8108,
    )

    assert [row.person_id for row in result.included] == [1, 2]
    included = {row.person_id: row for row in result.included}
    assert included[1].origin is ClaimOrigin.MODELED_AWARD
    assert included[1].claim_year == 2015
    assert included[2].origin is ClaimOrigin.OPENING_BACKFILL
    assert included[2].claim_age == 62
    assert included[2].claim_year == 1979
    assert included[1].post_claim_earnings_by_year[2016] > 0

    paths = {row.person_id: row.path for row in result.nonclaimants}
    assert paths[3] is NonClaimantPath.DRAWN_NEVER_CLAIMED
    assert paths[4] is NonClaimantPath.NEVER_DRAWN
    assert paths[7] is NonClaimantPath.NEVER_DRAWN
    counts = {row.key: row for row in result.counts}
    assert counts["excluded_di_conversion"].unweighted == 1
    assert counts["excluded_di_unknown"].unweighted == 1
    assert counts["nonclaimant"].unweighted == 3
    assert counts["included"].unweighted == 2
    assert counts["origin_modeled_award"].unweighted == 1
    assert counts["origin_opening_backfill"].unweighted == 1
    assert sum(row.unweighted for row in result.birth_source_counts) == len(
        roster
    )
    assert {row.person_id for row in result.births} == set(roster["person_id"])

    assert result.opening_stock_snap_denominator.weighted == 2.0
    shares = {
        row.key: row.share for row in result.opening_stock_snap_weighted_shares
    }
    assert shares == {"lower_endpoint": 1.0, "upper_endpoint": 0.0}
    assert result.entrant_diagnostic.person_ids == (4,)
    assert result.entrant_diagnostic.may_overlap_inclusion_classes
    assert not result.entrant_diagnostic.operative_exclusion_rule
    json.dumps(result.as_dict())


def test_opening_draw_is_strict_and_person_keyed_under_reordering():
    trajectory = pd.DataFrame(
        [
            *_trajectory_rows(1, 1952, claim_age=62, claim_year=2015),
            *_trajectory_rows(2, 1952, claim_age=62, claim_year=2015),
        ]
    )
    roster = _roster([(1, "female", 1.0), (2, "female", 1.0)])
    observed = pd.DataFrame(
        [
            *_observed_rows(1, 1952),
            *_observed_rows(2, 1952),
        ]
    )
    marriage = pd.DataFrame({"person_id": [1, 2], "birth_year": [1952, 1952]})
    schedule = _schedule({62: 0.01, 63: 0.99})

    first = build_career_inclusion(
        trajectory,
        roster,
        observed,
        marriage,
        {},
        schedule,
        {1, 2},
        stock_imputation_root_seed=8108,
    )
    second = build_career_inclusion(
        trajectory.iloc[::-1].reset_index(drop=True),
        roster.iloc[::-1].reset_index(drop=True),
        observed.iloc[::-1].reset_index(drop=True),
        marriage.iloc[::-1].reset_index(drop=True),
        {},
        schedule,
        {1, 2},
        stock_imputation_root_seed=8108,
    )

    assert {
        row.person_id: row.operative_claim_age for row in first.origins
    } == {1: 62, 2: 62}
    assert [row.as_dict() for row in first.origins] == [
        row.as_dict() for row in second.origins
    ]


def test_opening_draw_fails_closed_when_strict_truncation_is_empty():
    trajectory = pd.DataFrame(
        _trajectory_rows(1, 1952, claim_age=62, claim_year=2015)
    )
    roster = _roster([(1, "female", 1.0)])
    observed = pd.DataFrame(_observed_rows(1, 1952))
    marriage = pd.DataFrame({"person_id": [1], "birth_year": [1952]})

    with pytest.raises(
        ValueError,
        match="empty strictly-below exposure-age claiming mass",
    ):
        build_career_inclusion(
            trajectory,
            roster,
            observed,
            marriage,
            {},
            _schedule({63: 1.0}),
            {1},
            stock_imputation_root_seed=8108,
        )


def test_opening_draw_rng_namespace_is_exact_literal(monkeypatch):
    hashed_values: list[bytes] = []
    real_sha256 = career_module.hashlib.sha256

    def recording_sha256(value: bytes):
        hashed_values.append(value)
        return real_sha256(value)

    monkeypatch.setattr(career_module.hashlib, "sha256", recording_sha256)

    career_module._stable_person_rng(8108, 314159)

    assert hashed_values == [b"first_estimates.opening_stock.person.v1|314159"]


def test_stage_d_first_failure_order_and_exact_coverage_boundary():
    specs = {
        10: (1900, 120, 2015),
        # Person 11 fails both predicates 2 and 3. Predicate 2 must win.
        11: (1916, 100, 1967),
        12: (2000, 62, 2015),
        13: (1950, 65, 2000),
        14: (1940, 62, 2015),
        15: (1940, 62, 2015),
    }
    trajectory_rows = []
    for person_id, (birth_year, claim_age, claim_year) in specs.items():
        trajectory_rows.extend(
            _trajectory_rows(
                person_id,
                birth_year,
                claim_age=claim_age,
                claim_year=claim_year,
            )
        )
    trajectory = pd.DataFrame(trajectory_rows)
    roster = _roster([(person_id, "female", 1.0) for person_id in specs])
    marriage = pd.DataFrame(
        {
            "person_id": list(specs),
            "birth_year": [values[0] for values in specs.values()],
        }
    )
    observed = pd.DataFrame(
        [
            *_observed_rows(14, 1940, years=list(range(1968, 1995))),
            *_observed_rows(15, 1940, years=list(range(1968, 1996))),
        ]
    )

    result = build_career_inclusion(
        trajectory,
        roster,
        observed,
        marriage,
        {},
        _schedule(),
        {11, 12, 13, 14, 15},
        stock_imputation_root_seed=8108,
    )

    reasons = {row.person_id: row.reason for row in result.exclusions}
    assert reasons == {
        10: "excluded_domain_incomplete",
        11: "excluded_pre1979_eligibility",
        12: "excluded_empty_span",
        13: "excluded_chronology_inconsistent",
        14: "excluded_low_coverage",
    }
    assert [row.person_id for row in result.included] == [15]
    assert result.included[0].career.coverage_ratio == 0.8


def test_missing_candidate_birth_fails():
    trajectory = pd.DataFrame(
        _trajectory_rows(1, 1952, claim_age=63, claim_year=2015)
    )
    roster = _roster([(1, "female", 1.0)])
    observed = pd.DataFrame(
        columns=["person_id", "period", "earnings", "age", "weight"]
    )
    marriage = pd.DataFrame(columns=["person_id", "birth_year"])

    with pytest.raises(ValueError, match="candidate birth year"):
        build_career_inclusion(
            trajectory,
            roster,
            observed,
            marriage,
            {},
            _schedule(),
            {1},
            stock_imputation_root_seed=8108,
        )
