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
    build_seed_coordinates,
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


def test_outside_required_birth_conflict_is_omitted():
    marriage = pd.DataFrame(
        {
            "person_id": [1, 4, 4],
            "birth_year": [1950, 1951, 1952],
        }
    )
    observed = pd.DataFrame(
        [
            {"person_id": 2, "period": 2000, "age": 48},
            {"person_id": 4, "period": 2000, "age": 50},
        ]
    )

    records = {
        record.person_id: (record.birth_year, record.source)
        for record in derive_birth_years(
            marriage,
            observed,
            {3: 1960, 4: 1949},
            required_person_ids={1, 2, 3},
        )
    }

    assert records == {
        1: (1950, BirthSource.EXACT_MARRIAGE),
        2: (1952, BirthSource.INFERRED_PERIOD_AGE),
        3: (1960, BirthSource.SYNTHETIC_NATIVE),
    }


def test_required_birth_conflict_still_fails_closed():
    marriage = pd.DataFrame({"person_id": [1, 1], "birth_year": [1950, 1951]})
    observed = pd.DataFrame(columns=["person_id", "period", "age"])

    with pytest.raises(ValueError) as error:
        derive_birth_years(
            marriage,
            observed,
            required_person_ids={1},
        )

    assert str(error.value) == (
        "conflicting exact birth years for person 1: [1950, 1951]"
    )


def test_required_person_ids_normalize_like_marriage_ids():
    marriage = pd.DataFrame({"person_id": [1, 1], "birth_year": [1950, 1951]})
    observed = pd.DataFrame(columns=["person_id", "period", "age"])

    with pytest.raises(ValueError, match="conflicting exact birth"):
        derive_birth_years(
            marriage,
            observed,
            required_person_ids={"1"},
        )


def test_required_birth_scope_preserves_conflict_free_resolutions():
    marriage = pd.DataFrame({"person_id": [1], "birth_year": [1950]})
    observed = pd.DataFrame(
        [
            {"person_id": 1, "period": 2000, "age": 49},
            {"person_id": 2, "period": 2000, "age": 48},
            {"person_id": 4, "period": 2001, "age": 50},
        ]
    )
    synthetic = {1: 1949, 2: 1949, 3: 1960}

    unscoped = derive_birth_years(marriage, observed, synthetic)
    scoped = derive_birth_years(
        marriage,
        observed,
        synthetic,
        required_person_ids={1, 2, 3},
    )

    assert scoped == unscoped
    assert [(record.birth_year, record.source) for record in scoped] == [
        (1950, BirthSource.EXACT_MARRIAGE),
        (1952, BirthSource.INFERRED_PERIOD_AGE),
        (1960, BirthSource.SYNTHETIC_NATIVE),
        (1951, BirthSource.INFERRED_PERIOD_AGE),
    ]


def test_clause3_seed_age_codes_bounds_and_unresolved_dispositions():
    initial = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5],
            "year": [2014] * 5,
            "anchor_wave": [2015] * 5,
            "age": [2, 125, 1, 999, pd.NA],
        }
    )
    scheduled = {
        2019: pd.DataFrame(
            {
                "person_id": [6],
                "year": [2018],
                "anchor_wave": [2019],
                "age": [2],
            }
        )
    }
    seed = build_seed_coordinates(
        initial,
        scheduled,
        holdout_ids=range(1, 7),
    )

    records = {
        record.person_id: record
        for record in derive_birth_years(
            pd.DataFrame(columns=["person_id", "birth_year"]),
            pd.DataFrame(columns=["person_id", "period", "age"]),
            seed_coordinates=seed,
            required_person_ids=range(1, 7),
        )
    }

    assert (records[1].birth_year, records[1].source) == (
        2012,
        BirthSource.DERIVED_PROJECTION_AGE,
    )
    assert (records[2].birth_year, records[2].source) == (
        1889,
        BirthSource.DERIVED_PROJECTION_AGE,
    )
    assert (records[6].birth_year, records[6].source) == (
        2016,
        BirthSource.DERIVED_PROJECTION_AGE,
    )
    for person_id in (3, 4, 5):
        assert records[person_id].birth_year is None
        assert records[person_id].source is BirthSource.UNRESOLVED
        assert not records[person_id].inferred


def test_clause3_preserves_precedence_and_has_no_trajectory_input():
    seed = build_seed_coordinates(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "year": [2014] * 4,
                "anchor_wave": [2015] * 4,
                "age": [99] * 4,
            }
        ),
        {},
        holdout_ids={"1", "2", "3", "4"},
    )
    marriage = pd.DataFrame({"person_id": [1], "birth_year": [1950]})
    observed = pd.DataFrame([{"person_id": 2, "period": 2000, "age": 48}])

    first = derive_birth_years(
        marriage,
        observed,
        {3: 1960},
        seed_coordinates=seed,
        required_person_ids={1, 2, 3, 4},
    )
    second = derive_birth_years(
        marriage.iloc[::-1],
        observed.iloc[::-1],
        {3: 1960},
        seed_coordinates=seed.iloc[::-1].reset_index(drop=True),
        required_person_ids={4, 3, 2, 1},
    )

    assert first == second
    assert [(row.person_id, row.source) for row in first] == [
        (1, BirthSource.EXACT_MARRIAGE),
        (2, BirthSource.INFERRED_PERIOD_AGE),
        (3, BirthSource.SYNTHETIC_NATIVE),
        (4, BirthSource.DERIVED_PROJECTION_AGE),
    ]


@pytest.mark.parametrize("age", [0, 126])
def test_clause3_rejects_unrecognized_seed_age_codes(age):
    seed = pd.DataFrame(
        {
            "person_id": [1],
            "year": [2014],
            "anchor_wave": [2015],
            "age": [age],
        }
    )

    with pytest.raises(ValueError, match="unrecognized PSID seed-age"):
        derive_birth_years(
            pd.DataFrame(columns=["person_id", "birth_year"]),
            pd.DataFrame(columns=["person_id", "period", "age"]),
            seed_coordinates=seed,
            required_person_ids={1},
        )


@pytest.mark.parametrize(
    ("entry_year", "age", "expected_year"),
    [(2014, 125, 1888), (2020, 2, 2017)],
)
def test_clause3_rejects_derived_year_outside_global_bounds(
    entry_year: int,
    age: int,
    expected_year: int,
):
    seed = pd.DataFrame(
        {
            "person_id": [1],
            "year": [entry_year - 1],
            "anchor_wave": [entry_year],
            "age": [age],
        }
    )

    with pytest.raises(
        AssertionError,
        match=rf"derived birth year {expected_year}.*outside",
    ):
        derive_birth_years(
            pd.DataFrame(columns=["person_id", "birth_year"]),
            pd.DataFrame(columns=["person_id", "period", "age"]),
            seed_coordinates=seed,
            required_person_ids={1},
        )


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


def test_inclusion_ignores_conflicting_birth_years_outside_population():
    trajectory = pd.DataFrame(_trajectory_rows(1, 1952))
    roster = _roster([(1, "female", 1.0)])
    observed = pd.DataFrame(_observed_rows(1, 1952))
    marriage = pd.DataFrame(
        {
            "person_id": [1, 99, 99],
            "birth_year": [1952, 1900, 1901],
        }
    )

    result = build_career_inclusion(
        trajectory,
        roster,
        observed,
        marriage,
        {},
        _schedule(),
        {1},
        stock_imputation_root_seed=8108,
    )

    assert [
        (record.person_id, record.birth_year, record.source)
        for record in result.births
    ] == [(1, 1952, BirthSource.EXACT_MARRIAGE)]


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
    assert counts["excluded_birth_year_unresolved"].unweighted == 0
    assert counts["included"].unweighted == 2
    assert counts["origin_modeled_award"].unweighted == 1
    assert counts["origin_opening_backfill"].unweighted == 1
    assert {row.key for row in result.birth_source_counts} == {
        source.value for source in BirthSource
    }
    assert sum(row.unweighted for row in result.birth_source_counts) == len(
        roster
    )
    assert sum(row.weighted for row in result.birth_source_counts) == (
        roster["weight"].sum()
    )
    assert {row.person_id for row in result.births} == set(roster["person_id"])
    candidate_outcomes = {
        "excluded_birth_year_unresolved",
        "excluded_domain_incomplete",
        "excluded_pre1979_eligibility",
        "excluded_empty_span",
        "excluded_chronology_inconsistent",
        "excluded_low_coverage",
        "included",
    }
    assert counts["origin_modeled_award"].unweighted + counts[
        "origin_opening_backfill"
    ].unweighted == sum(counts[key].unweighted for key in candidate_outcomes)
    assert counts["origin_modeled_award"].weighted + counts[
        "origin_opening_backfill"
    ].weighted == sum(counts[key].weighted for key in candidate_outcomes)

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


def test_stage_c5_unresolved_backfill_precedes_stage_d_and_skips_imputation(
    monkeypatch,
):
    trajectory = pd.DataFrame(
        _trajectory_rows(1, 1952, claim_age=62, claim_year=2015)
    )
    roster = _roster([(1, "female", 1.0)])
    observed = pd.DataFrame(
        columns=["person_id", "period", "earnings", "age", "weight"]
    )
    marriage = pd.DataFrame(columns=["person_id", "birth_year"])

    seed = pd.DataFrame(
        {
            "person_id": [1],
            "year": [2014],
            "anchor_wave": [2015],
            "age": [1],
        }
    )

    def forbidden_imputation(**_kwargs):
        raise AssertionError("unresolved candidate reached §6 imputation")

    monkeypatch.setattr(
        career_module,
        "_opening_stock_draw",
        forbidden_imputation,
    )
    result = build_career_inclusion(
        trajectory,
        roster,
        observed,
        marriage,
        {},
        _schedule(),
        set(),
        stock_imputation_root_seed=8108,
        seed_coordinates=seed,
    )

    assert [(row.person_id, row.reason) for row in result.exclusions] == [
        (1, "excluded_birth_year_unresolved")
    ]
    assert result.origins[0].origin is ClaimOrigin.OPENING_BACKFILL
    assert result.origins[0].operative_claim_age is None
    assert result.origins[0].operative_claim_year is None
    counts = {row.key: row for row in result.counts}
    assert counts["excluded_birth_year_unresolved"].unweighted == 1
    assert counts["excluded_domain_incomplete"].unweighted == 0
    assert counts["origin_opening_backfill"].unweighted == 1


def test_stage_c_global_origin_and_c5_barriers_precede_imputation(monkeypatch):
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
    origin_seen: set[int] = set()
    c5_seen: set[int] = set()
    real_person_values = career_module._person_values

    def recording_person_values(frame, column, person_id):
        if column == "claim_age":
            origin_seen.add(person_id)
        return real_person_values(frame, column, person_id)

    class TrackingBirthRecord:
        birth_year = 1952

        def __init__(self, person_id):
            self.person_id = person_id

        @property
        def source(self):
            assert origin_seen == {1, 2}
            c5_seen.add(self.person_id)
            return BirthSource.EXACT_MARRIAGE

    def guarded_opening_draw(**_kwargs):
        assert c5_seen == {1, 2}
        return 62, 2013, "upper_endpoint"

    monkeypatch.setattr(
        career_module,
        "_person_values",
        recording_person_values,
    )
    monkeypatch.setattr(
        career_module,
        "derive_birth_years",
        lambda *_args, **_kwargs: (
            TrackingBirthRecord(1),
            TrackingBirthRecord(2),
        ),
    )
    monkeypatch.setattr(
        career_module,
        "_opening_stock_draw",
        guarded_opening_draw,
    )

    result = build_career_inclusion(
        trajectory,
        roster,
        observed,
        pd.DataFrame(columns=["person_id", "birth_year"]),
        {},
        _schedule(),
        {1, 2},
        stock_imputation_root_seed=8108,
    )

    assert origin_seen == c5_seen == {1, 2}
    assert [row.person_id for row in result.origins] == [1, 2]


def test_missing_candidate_disposition_is_a_code_bug(monkeypatch):
    trajectory = pd.DataFrame(
        _trajectory_rows(1, 1952, claim_age=62, claim_year=2015)
    )
    roster = _roster([(1, "female", 1.0)])
    observed = pd.DataFrame(_observed_rows(1, 1952))
    marriage = pd.DataFrame({"person_id": [1], "birth_year": [1952]})
    monkeypatch.setattr(
        career_module,
        "derive_birth_years",
        lambda *_args, **_kwargs: (),
    )

    with pytest.raises(
        AssertionError,
        match=r"birth-source disposition.*candidate code bug \[1\]",
    ):
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


def test_fully_dated_inclusion_is_identical_with_seed_coordinates():
    trajectory = pd.DataFrame(
        _trajectory_rows(1, 1952, claim_age=63, claim_year=2015)
    )
    roster = _roster([(1, "female", 1.0)])
    observed = pd.DataFrame(_observed_rows(1, 1952))
    marriage = pd.DataFrame({"person_id": [1], "birth_year": [1952]})
    arguments = (
        trajectory,
        roster,
        observed,
        marriage,
        {},
        _schedule(),
        {1},
    )

    pre_amendment_compatible = build_career_inclusion(
        *arguments,
        stock_imputation_root_seed=8108,
    )
    seeded = build_career_inclusion(
        *arguments,
        stock_imputation_root_seed=8108,
        seed_coordinates=pd.DataFrame(
            {
                "person_id": [1],
                "year": [2014],
                "anchor_wave": [2015],
                "age": [62],
            }
        ),
    )

    assert seeded.as_dict() == pre_amendment_compatible.as_dict()


def test_seed_coordinates_require_the_exact_normalized_holdout_universe():
    initial = pd.DataFrame(
        {
            "person_id": [1],
            "year": [2014],
            "anchor_wave": [2015],
            "age": [50],
        }
    )

    with pytest.raises(
        AssertionError,
        match="seed frames do not reconcile to holdout IDs",
    ):
        build_seed_coordinates(initial, {}, holdout_ids={1, 2})

    normalized = build_seed_coordinates(
        initial,
        {},
        holdout_ids={"1"},
    )
    assert normalized["person_id"].tolist() == [1]


def test_clause3_aborts_when_upstream_unresolved_person_has_no_seed_row():
    seed = pd.DataFrame(
        {
            "person_id": [1],
            "year": [2014],
            "anchor_wave": [2015],
            "age": [50],
        }
    )

    with pytest.raises(
        AssertionError,
        match=(
            "clauses-1/2/synthetic unresolved person has no seed row.*\\[2\\]"
        ),
    ):
        derive_birth_years(
            pd.DataFrame(columns=["person_id", "birth_year"]),
            pd.DataFrame(columns=["person_id", "period", "age"]),
            seed_coordinates=seed,
            required_person_ids={1, 2},
        )
