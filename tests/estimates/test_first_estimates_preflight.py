"""Fast tests for the advisory first-estimates birth preflight."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from populace_dynamics.estimates.career import BirthSource, BirthYearRecord

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "first_estimates_preflight.py"
SPEC = importlib.util.spec_from_file_location(
    "first_estimates_preflight_test_module",
    SCRIPT_PATH,
)
assert SPEC is not None and SPEC.loader is not None
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


def _seed() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5],
            "year": [2014] * 5,
            "anchor_wave": [2015] * 5,
            "age": [64, 54, 50, 14, 1],
        }
    )


def test_audit_publishes_five_source_counts_and_accepts_unresolved():
    records = (
        BirthYearRecord(1, 1950, BirthSource.EXACT_MARRIAGE),
        BirthYearRecord(2, 1960, BirthSource.INFERRED_PERIOD_AGE),
        BirthYearRecord(3, 1964, BirthSource.DERIVED_PROJECTION_AGE),
        BirthYearRecord(4, 2000, BirthSource.SYNTHETIC_NATIVE),
        BirthYearRecord(5, None, BirthSource.UNRESOLVED),
    )

    report = preflight.audit_birth_dispositions(
        candidate_possible_ids={1, 2, 3, 4, 5},
        seed_coordinates=_seed(),
        records=records,
    )

    assert report["status"] == "pass"
    assert report["source_counts"] == {
        "exact_marriage": 1,
        "inferred_period_age": 1,
        "derived_projection_age": 1,
        "synthetic_native": 1,
        "unresolved": 1,
    }
    assert report["checks"]["five_source_counts_reconcile"]["passed"]
    assert report["checks"]["derived_projection_age_bounds"] == {
        "passed": True,
        "derived_count": 1,
        "rule": (
            "seed_year - 125 <= birth_year <= seed_year - 2; "
            "1889 <= birth_year <= 2016; "
            "birth_year = seed_year - seed_age for age 2..125"
        ),
        "violation_count": 0,
        "violation_sample": [],
    }


def test_audit_fails_when_candidate_possible_person_lacks_disposition():
    report = preflight.audit_birth_dispositions(
        candidate_possible_ids={1, 2},
        seed_coordinates=_seed(),
        records=(BirthYearRecord(1, 1950, BirthSource.EXACT_MARRIAGE),),
    )

    assert report["status"] == "fail"
    coverage = report["checks"]["candidate_possible_disposition_coverage"]
    assert coverage["missing_count"] == 1
    assert coverage["missing_person_ids_sample"] == [2]
    assert report["source_counts"] == {
        "exact_marriage": 1,
        "inferred_period_age": 0,
        "derived_projection_age": 0,
        "synthetic_native": 0,
        "unresolved": 0,
    }
    assert "lack a disposition" in report["errors"][0]


def test_audit_independently_rejects_derived_year_outside_bounds():
    report = preflight.audit_birth_dispositions(
        candidate_possible_ids={3},
        seed_coordinates=_seed(),
        records=(
            BirthYearRecord(
                3,
                1800,
                BirthSource.DERIVED_PROJECTION_AGE,
            ),
        ),
    )

    assert report["status"] == "fail"
    bounds = report["checks"]["derived_projection_age_bounds"]
    assert bounds["passed"] is False
    assert bounds["violation_count"] == 1
    assert bounds["violation_sample"] == [
        {
            "person_id": 3,
            "reason": "derived birth year violates clause-3 bounds",
            "birth_year": 1800,
            "seed_year": 2014,
            "seed_age": 50,
            "expected_birth_year": 1964,
            "per_row_bounds": [1889, 2012],
            "global_bounds": [1889, 2016],
        }
    ]


def test_population_loader_uses_all_holdouts_without_fit(
    monkeypatch, tmp_path
):
    anchor = pd.DataFrame({"person_id": [11, 12]})
    inputs = SimpleNamespace(
        truth=SimpleNamespace(anchor=anchor),
        refit_inputs=object(),
        demographic_panel=object(),
        death_records=object(),
        earnings_panel=object(),
        disability_panel=object(),
        panel_builder_inputs=object(),
    )
    events: list[object] = []

    class Plan:
        fit_inputs = inputs.refit_inputs

        def load_full_inputs(self):
            events.append("load_full_inputs")
            return inputs

    def load_plan(repository):
        events.append(("load_plan", repository))
        return Plan()

    population = SimpleNamespace(holdout_ids=frozenset({11, 12}))

    def build_population(**kwargs):
        events.append(("build_population", kwargs))
        return population

    monkeypatch.setattr(
        preflight.coordinator,
        "_load_registered_input_plan",
        load_plan,
    )
    monkeypatch.setattr(
        preflight.m6_population,
        "build_realized_population",
        build_population,
    )

    observed_inputs, observed_population = (
        preflight._load_candidate_possible_population(tmp_path)
    )

    assert observed_inputs is inputs
    assert observed_population is population
    assert events[:2] == [
        ("load_plan", tmp_path),
        "load_full_inputs",
    ]
    kwargs = events[2][1]
    assert kwargs["earnings_domain_ids"] == frozenset({11, 12})
    assert kwargs["reserved_real_ids"] == frozenset({11, 12})


def test_run_preflight_threads_seed_coordinates_and_all_holdout_ids(
    monkeypatch,
    tmp_path,
):
    marriage = object()
    earnings = object()
    inputs = SimpleNamespace(
        refit_inputs=SimpleNamespace(
            family_context=SimpleNamespace(marriage_records=marriage)
        ),
        earnings_panel=earnings,
    )
    initial = object()
    scheduled = object()
    population = SimpleNamespace(
        initial_slice=initial,
        scheduled_entries_by_year=scheduled,
        holdout_ids=frozenset({21, 22}),
    )
    seed = pd.DataFrame(
        {
            "person_id": [21, 22],
            "year": [2014, 2014],
            "anchor_wave": [2015, 2015],
            "age": [50, 999],
        }
    )
    records = (
        BirthYearRecord(21, 1964, BirthSource.DERIVED_PROJECTION_AGE),
        BirthYearRecord(22, None, BirthSource.UNRESOLVED),
    )
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        preflight,
        "_load_candidate_possible_population",
        lambda repository: (inputs, population),
    )

    def build_seed(observed_initial, observed_scheduled):
        calls["seed_args"] = (observed_initial, observed_scheduled)
        return seed

    def derive(
        observed_marriage,
        observed_earnings,
        synthetic_birth_years,
        *,
        seed_coordinates,
        required_person_ids,
    ):
        calls["derive_args"] = {
            "marriage": observed_marriage,
            "earnings": observed_earnings,
            "synthetic": synthetic_birth_years,
            "seed": seed_coordinates,
            "required": required_person_ids,
        }
        return records

    monkeypatch.setattr(
        preflight.career,
        "build_seed_coordinates",
        build_seed,
    )
    monkeypatch.setattr(preflight.career, "derive_birth_years", derive)

    report = preflight.run_preflight(tmp_path)

    assert report["status"] == "pass"
    assert calls["seed_args"] == (initial, scheduled)
    assert calls["derive_args"] == {
        "marriage": marriage,
        "earnings": earnings,
        "synthetic": None,
        "seed": seed,
        "required": frozenset({21, 22}),
    }


def test_main_returns_clear_nonzero_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        preflight,
        "run_preflight",
        lambda repository: {
            "status": "fail",
            "errors": ["one candidate lacks a disposition"],
        },
    )

    assert preflight.main([]) == 1
    captured = capsys.readouterr()
    assert '"status": "fail"' in captured.out
    assert "birth-completeness preflight FAILED" in captured.err
    assert "one candidate lacks a disposition" in captured.err
