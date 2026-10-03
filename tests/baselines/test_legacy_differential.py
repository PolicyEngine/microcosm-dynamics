"""``tr2008_intermediate`` equals the registered tests' constructors.

Differential tests: every input :class:`TR2008Legacy` supplies is
compared, value for value (exact equality, no tolerance), with the
constructor the registered Track A and FRA-68 entry points call, over
every year, age and sex those tests read: the COLA path for
determination years 2008-2030, the AWI 1975-2030 (and the whole NAWI the
oracle receives), population mortality for projection years 2009-2030,
every claim-age PMF and every DI rate array.  The registered runner's
own committed-value checks (``runner._tr2008_value_checks`` and
``runner._committed_value_checks``, which a ``registered_real`` run
enforces) must also pass on the legacy baseline's inputs.

Artifact tier: reads the committed TR2008, COLA-history, claim-age and
DI inputs under ``data/external`` through their pinned accessors.  The
SSA parameter bundle the AWI is spliced into is INVENTED (pre-1975 wage
index, wage base and formula constants); both sides receive the same
one, so the comparison does not depend on it.  No projection runs.
"""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.baselines import TR2008Legacy, get_baseline
from populace_dynamics.baselines.base import SEXES
from populace_dynamics.cola_track_a import runner
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.cola_track_a.mortality import (
    Tr2008YearAwareMortality,
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.runner import (
    TrackAInputs,
    load_claiming_pmf,
    tr2008_baseline_cola,
    tr2008_ssa_parameters,
)
from populace_dynamics.data import tr2008
from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    DIEntitlementSpec,
    load_di_entitlement_rates,
)
from populace_dynamics.estimates.parameters import load_cola_history
from populace_dynamics.ss.params import SSAParameters

ROOT = Path(__file__).resolve().parents[2]
DATA_EXTERNAL = ROOT / "data" / "external"
#: The registered tests' years (TrackAConfig defaults: first TR2008 rate
#: year 2008, reference year 2030, earliest opening year 2008).
COLA_YEARS = range(2008, 2031)
AWI_YEARS = range(1975, 2031)
MORTALITY_YEARS = range(2009, 2031)
DI_FIELDS = (
    "incidence",
    "recovery_attained",
    "death_attained",
    "population_reference_death",
    "recovery_select",
    "death_select",
    "recovery_level_factor",
    "death_level_factor",
)


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


@pytest.fixture(scope="module")
def legacy() -> TR2008Legacy:
    return TR2008Legacy()


def test_the_registry_default_is_the_legacy_baseline():
    baseline = get_baseline()
    assert isinstance(baseline, TR2008Legacy)
    assert baseline == TR2008Legacy()
    assert baseline.name == "tr2008_intermediate"
    assert baseline.claim_table_max_year == 2008
    with pytest.raises(ValueError, match="2008"):
        TR2008Legacy(claim_table_max_year=2025)


# ---------------------------------------------------------------------------
# COLA
# ---------------------------------------------------------------------------
def test_cola_equals_tr2008_baseline_cola_for_the_registered_years(legacy):
    ours = legacy.cola_rates(2008, 2030)
    theirs = tr2008_baseline_cola(
        load_cola_history(),
        first_year=2008,
        last_year=2030,
        alternative="intermediate",
    )
    assert ours == theirs
    assert ours.provenance == theirs.provenance
    for year in COLA_YEARS:
        (entry,) = tr2008.cola_path(year, year, alternative="intermediate")
        assert ours.rate_for_determination_year(year) == round(
            entry.percent / 100.0, 10
        )


@settings(max_examples=25, deadline=None)
@given(
    first=st.integers(1983, 2010),
    span=st.integers(0, 75),
)
def test_cola_equals_the_constructor_for_any_first_and_last(first, span):
    last = min(first + span, 2085)
    assert TR2008Legacy().cola_rates(first, last) == tr2008_baseline_cola(
        load_cola_history(), first_year=first, last_year=last
    )


# ---------------------------------------------------------------------------
# AWI
# ---------------------------------------------------------------------------
def test_ssa_parameters_equal_tr2008_ssa_parameters(legacy):
    base = invented_base_params()
    ours = legacy.ssa_parameters(base)
    theirs = tr2008_ssa_parameters(base, alternative="intermediate")
    assert ours == theirs
    assert ours.nawi == theirs.nawi
    assert list(ours.nawi) == list(theirs.nawi)
    assert ours.pe_us_revision == theirs.pe_us_revision
    for year in AWI_YEARS:
        (entry,) = tr2008.awi_path(year, year, alternative="intermediate")
        assert ours.nawi[year] == entry.amount
    for year in range(1951, 1975):
        assert ours.nawi[year] == base.nawi[year]


def test_awi_equals_the_tr2008_awi_path(legacy):
    path = tr2008.awi_path(1975, 2085, alternative="intermediate")
    assert legacy.awi(1975, 2085) == {e.year: e.amount for e in path}
    params = legacy.ssa_parameters(invented_base_params())
    assert {
        year: params.nawi[year] for year in range(1975, 2086)
    } == legacy.awi(1975, 2085)


# ---------------------------------------------------------------------------
# Mortality
# ---------------------------------------------------------------------------
def _same_mortality(
    ours: Tr2008YearAwareMortality, theirs: Tr2008YearAwareMortality
) -> None:
    assert type(ours) is type(theirs) is Tr2008YearAwareMortality
    assert set(ours.qx_by_sex) == set(theirs.qx_by_sex) == set(SEXES)
    for sex in SEXES:
        assert np.array_equal(ours.qx_by_sex[sex], theirs.qx_by_sex[sex])
    assert dict(ours.ratio_by_year) == dict(theirs.ratio_by_year)
    assert ours.alternative == theirs.alternative
    assert ours.base_year == theirs.base_year
    assert tuple(ours.bands) == tuple(theirs.bands)
    assert dict(ours.provenance) == dict(theirs.provenance)


def test_mortality_equals_load_tr2008_mortality(legacy):
    _same_mortality(
        legacy.population_mortality(MORTALITY_YEARS),
        load_tr2008_mortality(
            MORTALITY_YEARS, alternative="intermediate", base_year=2004
        ),
    )


def test_qx_is_the_model_probability_at_every_age_and_year(legacy):
    model = load_tr2008_mortality(MORTALITY_YEARS)
    ages = np.arange(MAX_AGE + 1)
    for year in MORTALITY_YEARS:
        qx = legacy.qx(year)
        for sex in SEXES:
            frame = pd.DataFrame({"age": ages, "sex": sex})
            expected = model.probabilities_for_year(frame, year)
            assert np.array_equal(qx[sex], expected)
            under, over = model.ratio_by_year[year]
            ratio = np.where(ages >= 65, over, under)
            assert np.array_equal(
                qx[sex], np.clip(model.qx_by_sex[sex] * ratio, 0.0, 1.0)
            )


# ---------------------------------------------------------------------------
# Claiming and DI
# ---------------------------------------------------------------------------
def test_claim_pmf_equals_load_claiming_pmf(legacy):
    ours = legacy.claim_pmf()
    theirs = load_claiming_pmf()
    assert ours == theirs
    assert {year for _, year in ours} == set(range(1998, 2014))


def test_di_rates_equal_the_2008_fit_field_by_field(legacy):
    ours = legacy.di_rates()
    theirs = load_di_entitlement_rates(DIEntitlementSpec())
    assert ours.spec == theirs.spec == DIEntitlementSpec()
    for name in DI_FIELDS:
        assert runner._same_values(
            getattr(ours, name), getattr(theirs, name)
        ), name
    assert dict(ours.provenance) == dict(theirs.provenance)
    spec = dataclasses.replace(DIEntitlementSpec(), death_mode="explicit")
    assert legacy.di_rates(spec).spec == spec


# ---------------------------------------------------------------------------
# The registered runner's own checks accept the legacy baseline's inputs
# ---------------------------------------------------------------------------
def test_the_runners_committed_value_checks_pass(legacy):
    config = TrackAConfig()
    inputs = TrackAInputs(
        cohort=None,
        params=legacy.ssa_parameters(invented_base_params()),
        baseline=legacy.cola_rates(
            config.tr2008_first_rate_year, config.reference_year
        ),
        di_rates=legacy.di_rates(config.di_spec),
        population_mortality=legacy.population_mortality(
            range(
                min(config.start_years.values()) + 1,
                config.reference_year + 1,
            )
        ),
        claiming_pmf=legacy.claim_pmf(),
    )
    checks = {
        **runner._tr2008_value_checks(inputs, config),
        **runner._committed_value_checks(inputs, config),
    }
    assert set(checks) == {
        "cola_path",
        "awi",
        "mortality_values",
        "di_rates",
        "claiming_pmf",
    }
    for name, check in checks.items():
        assert check["consistent"], (name, check)


# ---------------------------------------------------------------------------
# Provenance hashes are the files' bytes
# ---------------------------------------------------------------------------
def test_every_recorded_file_hash_is_the_files_hash(legacy):
    record = legacy.provenance()
    files = record["files_sha256"]
    assert "data/external/ssa_cola_history.json" in files
    assert "data/external/ssa_claim_ages_2014supplement.json" in files
    for relative, digest in files.items():
        path = ROOT / relative
        assert path.is_relative_to(DATA_EXTERNAL), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    di = legacy.di_rates().provenance
    assert di["inputs_sha256"] in files.values()
    assert di["nchs_2000_sha256"] in files.values()


def test_legacy_fertility_is_a_named_gap(legacy):
    from populace_dynamics.baselines import BaselineGapError

    with pytest.raises(BaselineGapError, match="no age-specific"):
        legacy.asfr(2030)
    with pytest.raises(BaselineGapError, match="no fertility"):
        legacy.tfr(2030)
    sources = legacy.value_sources(2030)
    assert sources["asfr"] == sources["tfr"] == "gap_not_supplied"
