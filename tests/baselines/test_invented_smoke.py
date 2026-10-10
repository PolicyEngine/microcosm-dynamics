"""Smoke test: the invented Track A projection under every baseline.

INVENTED DATA - NOT A COMPARISON.  The cohorts are the invented
generator's people (``cola_track_a.invented``, seed 20260922, the dry
runs' default), read as the 2011 wave (row R0) and the 2009 wave (row
R6), and the oracle parameter bundle the AWI is spliced into is
INVENTED.  Each baseline's committed inputs (COLA, AWI, mortality, DI,
claim-age table, read under ``data/external`` through their pinned
accessors) drive the projection to 2035.  Nothing about real data is
computed or printed; the assertions are structural (completion,
finiteness, accounting), not values.

* Under every baseline :func:`project_track_a` (the ``run_track_a``
  projection, one draw) must complete through 2035 with finite weights,
  ages consistent with birth years, a closed population (alive counts
  fall only by the logged deaths) and claim years no later than the
  slice year.
* Under the legacy baseline the full ``run_track_a`` (projection,
  benefits and A7 tabulation of rows R0 and R6) must complete with every
  tabulated number finite.
* Under the 2026 baselines ``run_track_a`` refuses at the A1 floor
  assertion (realized zero COLAs for 2009, 2010 and 2015 cannot take a
  one-point cut), the documented scope limit of ``baselines.track_a``.
* The opt-in ASFR fertility step (not gated, report-only) projects an
  INVENTED open population from 2025 to 2035 under each 2026
  baseline's ASFR and population mortality: the population changes by
  exactly the logged births minus deaths, every expected-birth count is
  the sum of the baseline's rates over the exposed women, every mother
  is a woman aged 14-49 and total births lie within five Poisson
  standard errors of the expected total.  The legacy baseline, which
  supplies no fertility, refuses rather than drawing zero births.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.baselines import (
    BASELINE_NAMES,
    BaselineGapError,
    build_track_a_inputs,
    get_baseline,
    project_track_a,
    track_a_config_for,
)
from populace_dynamics.baselines.fertility import AsfrFertilityStep
from populace_dynamics.cola_track_a import run_track_a
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.engine.loop import (
    MaritalStepResult,
    PeriodModules,
    ProjectionEngine,
)
from populace_dynamics.engine.steps import advance_age
from populace_dynamics.ss.params import SSAParameters

ROOT = Path(__file__).resolve().parents[2]
DATA_EXTERNAL = ROOT / "data" / "external"
END_YEAR = 2035
START_YEARS = {2011: 2010, 2009: 2008}


def invented_base_params() -> SSAParameters:
    """INVENTED oracle parameters (4 percent wage growth from 1951)."""
    return SSAParameters(
        nawi={
            year: 2_800.0 * 1.04 ** (year - 1951) for year in range(1951, 2061)
        },
        wage_base={1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


@pytest.fixture(scope="module", params=BASELINE_NAMES)
def projected(request):
    """One invented projection to 2035 under the named baseline."""
    baseline = get_baseline(request.param)
    config = track_a_config_for(
        TrackAConfig(
            reference_year=END_YEAR, draw_indices=(0,), rows=("R0", "R6")
        ),
        baseline,
    )
    inputs = build_track_a_inputs(
        config,
        baseline,
        data_provenance="invented",
        base_params=invented_base_params(),
    )
    death_log = {}
    results = project_track_a(inputs, config, death_log=death_log)
    return baseline, config, inputs, results, death_log


def test_the_projection_completes_to_2035_with_finite_state(projected):
    baseline, config, inputs, results, death_log = projected
    assert set(results) == set(START_YEARS)
    for wave, result in results.items():
        years = [int(frame["year"].iloc[0]) for frame in result.slices]
        assert years == list(range(START_YEARS[wave], END_YEAR + 1))
        alive = [len(frame) for frame in result.slices]
        assert alive[0] > alive[-1] > 0
        deaths = death_log[wave]
        for index in range(1, len(result.slices)):
            year = years[index]
            previous = set(result.slices[index - 1]["person_id"])
            current = set(result.slices[index]["person_id"])
            assert current <= previous, (wave, year)
            died = previous - current
            logged = set(deaths.get(year, {"person_id": []})["person_id"])
            assert died == logged, (wave, year)
        for frame in result.slices:
            year = int(frame["year"].iloc[0])
            weight = frame["weight"].to_numpy(dtype=np.float64)
            assert np.isfinite(weight).all() and (weight > 0).all()
            age = frame["age"].to_numpy(dtype=np.int64)
            assert (age == year - frame["birth_year"].to_numpy()).all()
            claimed = frame["claim_year"].dropna().astype(int)
            assert (claimed <= year).all()
            for column in frame.select_dtypes("number").columns:
                values = frame[column].dropna().to_numpy(dtype=np.float64)
                assert np.isfinite(values).all(), (wave, year, column)
    assert inputs.provenance["baseline"]["name"] == baseline.name
    assert config.reference_year == END_YEAR


def test_the_projection_uses_the_baselines_mortality(projected):
    baseline, config, inputs, results, death_log = projected
    model = inputs.population_mortality
    for year in range(2009, END_YEAR + 1):
        frame = results[2011].slices[-1][["age", "sex"]]
        expected = np.minimum(frame["age"].to_numpy(), 120)
        qx = baseline.qx(year)
        observed = model.probabilities_for_year(frame, year)
        sexes = frame["sex"].to_numpy()
        assert np.array_equal(
            observed,
            np.where(
                sexes == "male", qx["male"][expected], qx["female"][expected]
            ),
        )


def test_legacy_run_track_a_completes_to_2035_with_finite_tables():
    baseline = get_baseline("tr2008_intermediate")
    config = TrackAConfig(
        reference_year=END_YEAR, draw_indices=(0,), rows=("R0", "R6")
    )
    inputs = build_track_a_inputs(
        config,
        baseline,
        data_provenance="invented",
        base_params=invented_base_params(),
    )
    result = run_track_a(inputs, config=config)
    assert result["data_provenance"] == "invented"
    assert result["parameter_consistency"]["consistent"]
    assert result["inputs_provenance"]["baseline"]["name"] == baseline.name

    def non_finite(value, path=""):
        if isinstance(value, float):
            return [] if math.isfinite(value) else [path]
        if isinstance(value, dict):
            return [
                bad
                for key, item in value.items()
                for bad in non_finite(item, f"{path}/{key}")
            ]
        if isinstance(value, list | tuple):
            return [
                bad
                for index, item in enumerate(value)
                for bad in non_finite(item, f"{path}[{index}]")
            ]
        return []

    for row in ("R0", "R6"):
        record = result["rows"][row]
        assert record["status"] == "tabulated", record["status"]
        assert record["tabulation"] is not None
        assert non_finite(record["tabulation"]) == []


@pytest.mark.parametrize("name", ["tr2026_intermediate", "cbo2026_long_term"])
def test_run_track_a_refuses_a_one_point_cut_on_realized_zero_colas(name):
    baseline = get_baseline(name)
    config = track_a_config_for(
        TrackAConfig(reference_year=END_YEAR, draw_indices=(0,), rows=("R0",)),
        baseline,
    )
    inputs = build_track_a_inputs(
        config,
        baseline,
        data_provenance="invented",
        base_params=invented_base_params(),
    )
    zero_years = [
        year
        for year in range(2009, END_YEAR + 1)
        if inputs.baseline.rate_for_determination_year(year) == 0.0
    ]
    assert zero_years == [2009, 2010, 2015]
    with pytest.raises(ValueError, match="A1 floor assertion"):
        run_track_a(inputs, config=config)


# ---------------------------------------------------------------------------
# The opt-in ASFR fertility step on an INVENTED open population
# ---------------------------------------------------------------------------
OPEN_START = 2025


def invented_open_population(size: int = 3_000) -> pd.DataFrame:
    """INVENTED people in 2025: ages 0-89 spread evenly, sexes alternating."""
    ids = np.arange(1, size + 1, dtype=np.int64)
    ages = (7 * ids) % 90
    return pd.DataFrame(
        {
            "person_id": ids,
            "year": OPEN_START,
            "age": ages,
            "birth_year": OPEN_START - ages,
            "sex": np.where(ids % 2 == 0, "female", "male"),
            "weight": 1.0,
            "household_id": ids,
        }
    )


def open_population_modules(baseline, births, expected, deaths):
    """Mortality from the baseline's model, aging and ASFR births only."""
    model = baseline.population_mortality(range(OPEN_START + 1, END_YEAR + 1))

    def mortality(frame, context, rng):
        died = rng.random(len(frame)) < model(frame, context)
        deaths[context.year] = int(died.sum())
        return frame.loc[~died].reset_index(drop=True)

    def keep(frame, context, rng):
        return frame

    def marital(frame, context, rng):
        return MaritalStepResult(
            sim_years=frame[["person_id"]].copy(),
            births=pd.DataFrame(columns=["parent_person_id", "birth_year"]),
        )

    def household(frame, context, marital, rng):
        return frame

    return PeriodModules(
        mortality=mortality,
        aging=advance_age,
        marital_core=marital,
        fertility=AsfrFertilityStep(
            asfr=baseline.asfr, birth_log=births, expected_log=expected
        ),
        disability=keep,
        earnings=keep,
        claiming=keep,
        household_composition=household,
    )


@pytest.mark.parametrize("name", BASELINE_NAMES)
def test_the_asfr_step_projects_an_open_population_to_2035(name):
    baseline = get_baseline(name)
    births, expected, deaths = {}, {}, {}
    engine = ProjectionEngine(
        open_population_modules(baseline, births, expected, deaths)
    )
    initial = invented_open_population()
    if name == "tr2008_intermediate":
        with pytest.raises(BaselineGapError, match="no age-specific"):
            engine.project(initial, end_year=END_YEAR, draw_index=0)
        return
    result = engine.project(initial, end_year=END_YEAR, draw_index=0)
    years = list(range(OPEN_START + 1, END_YEAR + 1))
    assert [int(frame["year"].iloc[0]) for frame in result.slices] == [
        OPEN_START,
        *years,
    ]
    for index, year in enumerate(years, start=1):
        frame = result.slices[index]
        logged = births[year]
        assert len(frame) == (
            len(result.slices[index - 1]) - deaths[year] + len(logged)
        ), year
        assert np.isfinite(frame["weight"].to_numpy(dtype=float)).all()
        assert (frame["age"] == year - frame["birth_year"]).all(), year
        born = frame[frame["birth_year"] == year]
        before = frame[frame["birth_year"] < year].set_index("person_id")
        assert sorted(born["parent_person_id"]) == sorted(
            logged["parent_person_id"]
        )
        mothers = before.loc[born["parent_person_id"]]
        assert (mothers["sex"] == "female").all()
        assert mothers["age"].between(14, 49).all()
        assert (born["age"] == 0).all() and born["person_id"].is_unique
        rates = baseline.asfr(year)
        exposed = before[
            (before["sex"] == "female") & before["age"].between(14, 49)
        ]
        assert expected[year] == pytest.approx(
            sum(rates[int(age)] for age in exposed["age"]), rel=1e-12
        )
    total_expected = sum(expected.values())
    total_births = sum(len(logged) for logged in births.values())
    assert total_births > 0
    assert abs(total_births - total_expected) <= 5.0 * math.sqrt(
        total_expected
    )
