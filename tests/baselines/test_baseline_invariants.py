"""Invariants every registered baseline must satisfy.

Stated invariants (each is tested below, with Hypothesis where the
domain is large):

1. **Mortality.**  ``q`` is finite and in [0, 1] for every age 0-120,
   both sexes and every covered year; age 120 repeats age 119; the
   year-aware model returns ``q[year][sex][min(age, 120)]`` for any
   frame.
2. **Fertility.**  ASFR covers single ages 14-49, is non-negative and
   below one (a Bernoulli probability per woman-year), and sums to the
   baseline's TFR: exactly (to 1e-12) where the TFR is derived from the
   schedule or the schedule from the TFR, and within the printed
   rounding where both are published (CBO 2026-2099).
3. **AWI.**  Strictly positive and finite; ``ssa_parameters`` keeps the
   oracle's pre-1975 series and replaces every later year it covers.
4. **COLA splices are continuous.**  The path covers every
   determination year from 1979 consecutively, each year from one named
   source; the 2026 baselines keep realized increases through 2025 (the
   committed history through 2022, then TR2026 V.C1's historical rows
   and the 2.8 percent 2025 actual) and their path does not depend on
   the first rate year; the committed history and V.C1 agree in every
   year both cover.  The CBO AWI analog starts from the realized 2024
   level.
5. **Claiming.**  Every claim-age PMF is non-negative on ages 62-70 and
   sums to one.
6. **DI.**  Every baseline supplies the 2008 fit (a named gap).
7. **Provenance.**  Every recorded file hash is the hash of that file's
   bytes under ``data/external``; derived values carry derived tags.

Artifact tier: reads the committed TR2008, TR2026, CBO 2026, NCHS,
claim-age, COLA-history and DI inputs under ``data/external`` through
their pinned accessors.  No projection runs and no outcome is computed.
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

from populace_dynamics.baselines import (
    BASELINE_NAMES,
    DEFAULT_BASELINE,
    Baseline,
    BaselineGapError,
    BaselineYearAwareMortality,
    CBO2026LongTerm,
    TR2008Legacy,
    TR2026Intermediate,
    get_baseline,
    realized,
)
from populace_dynamics.baselines.base import (
    SEXES,
    pad_to_max_age,
    replace_awi,
)
from populace_dynamics.cola_track_a.runner import _same_values
from populace_dynamics.data import cbo2026, tr2026
from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    SINGLE_YEAR_AGE_BANDS,
    DIEntitlementSpec,
    load_di_entitlement_rates,
)
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.estimates.parameters import load_cola_history
from populace_dynamics.ss.params import SSAParameters

ROOT = Path(__file__).resolve().parents[2]
DATA_EXTERNAL = ROOT / "data" / "external"
#: Years each baseline supplies mortality for (TR2008: the V.A1 ASADR
#: ratios; CBO: its 2021-2099 tables with OACT history spliced before).
MORTALITY_YEARS = {
    "tr2008_intermediate": range(2005, 2086),
    "tr2026_intermediate": range(1950, 2101),
    "cbo2026_long_term": range(1950, 2100),
}
LAST_COLA_YEAR = {
    "tr2008_intermediate": 2085,
    "tr2026_intermediate": 2100,
    "cbo2026_long_term": 2100,
}
#: CBO prints ASFR per 1,000 women to two decimals and the TFR to three
#: (``cbo2026_demographics.json``), so the 36 rates per woman sum to the
#: TFR within 36 half-units of 1e-5 plus half a unit of 1e-3.
CBO_PRINTED_ROUNDING = 36 * 0.5e-5 + 0.5e-3
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
        wage_base={1937: 3_000.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
    )


@pytest.fixture(scope="module", params=BASELINE_NAMES)
def baseline(request) -> Baseline:
    return get_baseline(request.param)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
def test_registry_names_and_default():
    assert BASELINE_NAMES == (
        "tr2008_intermediate",
        "tr2026_intermediate",
        "cbo2026_long_term",
    )
    assert DEFAULT_BASELINE == "tr2008_intermediate"
    assert isinstance(get_baseline(), TR2008Legacy)
    assert isinstance(get_baseline("tr2026_intermediate"), TR2026Intermediate)
    assert isinstance(get_baseline("cbo2026_long_term"), CBO2026LongTerm)
    with pytest.raises(KeyError, match="unknown baseline"):
        get_baseline("tr2025_intermediate")


def test_every_baseline_implements_the_protocol_and_is_frozen(baseline):
    assert isinstance(baseline, Baseline)
    assert baseline.name in BASELINE_NAMES
    assert baseline.vintage
    with pytest.raises(dataclasses.FrozenInstanceError):
        baseline.name = "other"


# ---------------------------------------------------------------------------
# 1. Mortality
# ---------------------------------------------------------------------------
def test_q_lies_in_the_unit_interval_every_year_age_and_sex(baseline):
    for year in MORTALITY_YEARS[baseline.name]:
        qx = baseline.qx(year)
        assert set(qx) == set(SEXES)
        for sex in SEXES:
            values = qx[sex]
            assert values.shape == (MAX_AGE + 1,)
            assert np.isfinite(values).all(), (year, sex)
            assert ((values >= 0.0) & (values <= 1.0)).all(), (year, sex)
            assert values[MAX_AGE] == values[MAX_AGE - 1]
            assert not values.flags.writeable


def test_q_outside_coverage_refuses(baseline):
    years = MORTALITY_YEARS[baseline.name]
    with pytest.raises((KeyError, ValueError)):
        baseline.qx(years.stop + 1)


def test_published_q_are_used_unaltered():
    tr = TR2026Intermediate()
    cbo = CBO2026LongTerm()
    for year in (1990, 2023, 2024, 2050, 2099):
        for sex in SEXES:
            published = tr2026.death_probability(year, sex)
            assert np.array_equal(tr.qx(year)[sex][:120], published)
            if year >= 2021:
                assert np.array_equal(
                    cbo.qx(year)[sex][:120], cbo2026.mortality(year, sex)
                )
                assert cbo.qx(year)[sex][119] == 1.0
            else:
                assert np.array_equal(cbo.qx(year)[sex][:120], published)
    # OACT publishes q(119) below one and the TR2026 baseline keeps it.
    assert tr.qx(2050)["male"][119] < 1.0


@settings(max_examples=30, deadline=None)
@given(
    name=st.sampled_from(BASELINE_NAMES),
    year=st.integers(2009, 2085),
    ages=st.lists(st.integers(0, 140), min_size=1, max_size=40),
    data=st.data(),
)
def test_the_year_aware_model_returns_q_at_the_capped_age(
    name, year, ages, data
):
    baseline = get_baseline(name)
    model = baseline.population_mortality(range(year, year + 1))
    assert tuple(model.bands) == SINGLE_YEAR_AGE_BANDS
    assert not hasattr(model, "probabilities")
    sexes = data.draw(
        st.lists(
            st.sampled_from(SEXES), min_size=len(ages), max_size=len(ages)
        )
    )
    frame = pd.DataFrame({"age": ages, "sex": sexes})
    context = PeriodContext(
        period_index=1, year=year, draw_index=0, metadata={}
    )
    observed = model(frame, context)
    qx = baseline.qx(year)
    expected = [
        qx[sex][min(age, MAX_AGE)]
        for age, sex in zip(ages, sexes, strict=True)
    ]
    assert np.array_equal(observed, np.asarray(expected))


def test_the_generic_model_refuses_bad_inputs():
    good = {2030: {sex: np.full(MAX_AGE + 1, 0.01) for sex in SEXES}}
    model = BaselineYearAwareMortality(baseline="INVENTED", qx_by_year=good)
    frame = pd.DataFrame({"age": [30], "sex": ["female"]})
    with pytest.raises(KeyError, match="no INVENTED mortality for 2031"):
        model.probabilities_for_year(frame, 2031)
    with pytest.raises(ValueError, match="sex labels"):
        model.probabilities_for_year(
            pd.DataFrame({"age": [30], "sex": ["other"]}), 2030
        )
    with pytest.raises(ValueError, match="non-negative"):
        model.probabilities_for_year(
            pd.DataFrame({"age": [-1], "sex": ["male"]}), 2030
        )
    with pytest.raises(ValueError, match="missing columns"):
        model.probabilities_for_year(pd.DataFrame({"age": [30]}), 2030)
    bad = {2030: {"female": np.full(MAX_AGE + 1, 1.5), "male": good[2030]}}
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        BaselineYearAwareMortality(baseline="INVENTED", qx_by_year=bad)
    short = {2030: {sex: np.full(MAX_AGE, 0.01) for sex in SEXES}}
    with pytest.raises(ValueError, match="ages 0-120"):
        BaselineYearAwareMortality(baseline="INVENTED", qx_by_year=short)
    with pytest.raises(ValueError, match="single-year"):
        BaselineYearAwareMortality(
            baseline="INVENTED", qx_by_year=good, bands=((0, 65), (65, 121))
        )
    with pytest.raises(TypeError):
        model.qx_by_year[2030]["male"] = np.zeros(MAX_AGE + 1)
    with pytest.raises(ValueError, match="read-only"):
        model.qx_by_year[2030]["male"][30] = 0.5
    assert not model.qx_by_year[2030]["male"].flags.writeable
    with pytest.raises(ValueError, match="at most"):
        pad_to_max_age(np.zeros(MAX_AGE + 2))


# ---------------------------------------------------------------------------
# 2. Fertility
# ---------------------------------------------------------------------------
def _check_schedule(rates: dict[int, float]) -> np.ndarray:
    assert tuple(rates) == tuple(range(14, 50))
    values = np.asarray(list(rates.values()))
    assert np.isfinite(values).all()
    assert (values >= 0.0).all() and (values < 1.0).all()
    return values


def test_tr2026_asfr_sums_to_the_v_a1_tfr_every_year():
    baseline = TR2026Intermediate()
    for year in range(1940, 2101):
        values = _check_schedule(baseline.asfr(year))
        assert values.sum() == pytest.approx(baseline.tfr(year), rel=1e-12)
        assert baseline.tfr(year) == tr2026.tfr(year)


def test_cbo_asfr_is_published_and_sums_to_the_tfr_within_rounding():
    baseline = CBO2026LongTerm()
    for year in range(2021, 2100):
        rates = baseline.asfr(year)
        values = _check_schedule(rates)
        assert rates == cbo2026.asfr(year, "all")
        if year < 2026:
            assert values.sum() == pytest.approx(baseline.tfr(year), 1e-12)
        else:
            assert abs(values.sum() - baseline.tfr(year)) <= (
                CBO_PRINTED_ROUNDING
            ), year
    with pytest.raises(ValueError, match="outside coverage"):
        baseline.asfr(2020)


def test_legacy_supplies_no_fertility():
    with pytest.raises(BaselineGapError):
        TR2008Legacy().asfr(2030)


# ---------------------------------------------------------------------------
# 3. AWI
# ---------------------------------------------------------------------------
def test_awi_is_positive_and_ssa_parameters_splice_it(baseline):
    last = LAST_COLA_YEAR[baseline.name]
    awi = baseline.awi(1975, last)
    assert list(awi) == list(range(1975, last + 1))
    values = np.asarray(list(awi.values()))
    assert np.isfinite(values).all() and (values > 0.0).all()
    base = invented_base_params()
    params = baseline.ssa_parameters(base)
    assert all(np.isfinite(v) and v > 0.0 for v in params.nawi.values())
    for year in range(1951, 1975):
        assert params.nawi[year] == base.nawi[year]
    for year in range(1975, last + 1):
        assert params.nawi[year] == awi[year]
    assert params.pe_us_revision.startswith("INVENTED+")
    assert dataclasses.replace(params, nawi=base.nawi, pe_us_revision="X") == (
        dataclasses.replace(base, pe_us_revision="X")
    )


def test_realized_awi_runs_through_2024_in_both_2026_baselines():
    tr, cbo = TR2026Intermediate(), CBO2026LongTerm()
    tr_awi, cbo_awi = tr.awi(1975, 2100), cbo.awi(1975, 2100)
    for year in range(1975, 2025):
        assert tr_awi[year] == cbo_awi[year] == realized.realized_awi(year)[0]
        assert tr.value_sources(year)["awi"] == "tr2026_vi_g1_historical"
        assert cbo.value_sources(year)["awi"] == "tr2026_vi_g1_historical"
    # The CBO analog starts from the realized 2024 level (no level jump).
    (anchor,) = cbo2026.awi(2024, 2024)
    assert anchor.amount == cbo_awi[2024]
    for year in range(2025, 2101):
        (entry,) = cbo2026.awi(year, year)
        assert cbo_awi[year] == entry.amount
        assert cbo.value_sources(year)["awi"].startswith("derived_cbo2026")
    assert tr.value_sources(2025)["awi"] == "tr2026_vi_g1_estimated"
    assert tr.value_sources(2026)["awi"] == "tr2026_vi_g1_projected"


def test_replace_awi_refuses_gaps_and_non_positive_amounts():
    base = invented_base_params()
    with pytest.raises(ValueError, match="consecutive"):
        replace_awi(base, {1975: 1.0, 1977: 1.0}, revision_suffix="x")
    with pytest.raises(ValueError, match="positive"):
        replace_awi(base, {1975: 0.0}, revision_suffix="x")
    with pytest.raises(ValueError, match="positive"):
        replace_awi(base, {1975: float("nan")}, revision_suffix="x")


# ---------------------------------------------------------------------------
# 4. COLA splices
# ---------------------------------------------------------------------------
def test_cola_covers_consecutive_years_from_1979(baseline):
    last = LAST_COLA_YEAR[baseline.name]
    series = baseline.cola_rates(2008, last)
    years = sorted(series.by_determination_year)
    assert years == list(range(1979, last + 1))
    values = np.asarray([series.rate_for_determination_year(y) for y in years])
    assert np.isfinite(values).all() and (values >= 0.0).all()


def test_the_committed_history_and_v_c1_agree_where_both_cover():
    realized.check_realized_cola_agreement()
    history = load_cola_history()
    for entry in tr2026.cola_path(1979, 2022):
        year = entry.determination_year
        committed = 100.0 * history.rate_for_determination_year(year)
        assert round(committed, 10) == round(entry.percent, 10), year


def test_the_agreement_check_refuses_a_different_history(monkeypatch):
    history = load_cola_history()
    changed = dict(history.by_determination_year)
    changed[2015] = 0.017
    tampered = dataclasses.replace(history, by_determination_year=changed)
    monkeypatch.setattr(realized, "load_cola_history", lambda: tampered)
    with pytest.raises(ValueError, match="differ"):
        realized.check_realized_cola_agreement.__wrapped__()


@pytest.mark.parametrize("name", ["tr2026_intermediate", "cbo2026_long_term"])
def test_2026_baselines_keep_realized_increases_through_2025(name):
    baseline = get_baseline(name)
    series = baseline.cola_rates(2008, 2100)
    history = load_cola_history()
    for year in range(1979, 2023):
        assert series.rate_for_determination_year(
            year
        ) == history.rate_for_determination_year(year)
    for year in range(2023, 2026):
        percent, source = realized.realized_cola_percent(year)
        assert series.rate_for_determination_year(year) == round(
            percent / 100.0, 10
        )
        assert baseline.value_sources(year)["cola"] == source
    assert series.rate_for_determination_year(2025) == 0.028
    assert baseline.value_sources(2025)["cola"] == "tr2026_v_c1_actual"
    # From 2026 every rate is the projected or derived source's.
    for year in range(2026, 2101):
        if name == "tr2026_intermediate":
            (entry,) = tr2026.cola_path(year, year)
            expected = entry.percent
        else:
            expected = cbo2026.cpiu_growth(year)
        assert series.rate_for_determination_year(year) == round(
            expected / 100.0, 10
        ), year


@settings(max_examples=25, deadline=None)
@given(
    name=st.sampled_from(["tr2026_intermediate", "cbo2026_long_term"]),
    first=st.integers(1979, 2040),
    last=st.integers(2026, 2100),
)
def test_2026_cola_path_does_not_depend_on_the_first_rate_year(
    name, first, last
):
    baseline = get_baseline(name)
    first = min(first, last)
    observed = baseline.cola_rates(first, last).by_determination_year
    reference = baseline.cola_rates(2008, last).by_determination_year
    assert observed == reference


def test_cola_requests_are_validated():
    for baseline in (TR2026Intermediate(), CBO2026LongTerm()):
        with pytest.raises(ValueError, match="must not follow"):
            baseline.cola_rates(2031, 2030)
        with pytest.raises(ValueError, match="at least 2023"):
            baseline.cola_rates(2008, 2022)
        with pytest.raises(TypeError, match="integer"):
            baseline.cola_rates(2008.0, 2030)
    with pytest.raises(KeyError, match="after 2100"):
        CBO2026LongTerm().cola_rates(2008, 2101)
    with pytest.raises(KeyError):
        TR2026Intermediate().cola_rates(2008, 2101)


def test_legacy_splices_tr2008_rates_from_the_first_rate_year():
    series = TR2008Legacy().cola_rates(2008, 2030)
    history = load_cola_history()
    for year in range(1979, 2008):
        assert series.rate_for_determination_year(
            year
        ) == history.rate_for_determination_year(year)


def test_derived_values_carry_derived_tags():
    tr, cbo = TR2026Intermediate(), CBO2026LongTerm()
    assert tr.value_sources(2035)["cola"] == "tr2026_v_c1_projected"
    assert tr.value_sources(2036)["cola"] == "derived_annual_cpiw_cola"
    assert tr.value_sources(2030)["asfr"].startswith("derived_")
    assert tr.value_sources(2030)["tfr"] == "tr2026_v_a1_projected"
    assert cbo.value_sources(2026)["cola"].startswith("derived_")
    assert cbo.value_sources(2026)["cpiw_growth"].startswith("derived_")
    assert cbo.value_sources(2025)["cpiw_growth"] == "tr2026_v_b1_estimated"
    assert "oact_historical" in cbo.value_sources(2015)["mortality"]
    assert cbo.value_sources(2030)["mortality"] == (
        "cbo2026_mortality_q_verified"
    )
    for year in (2015, 2030, 2050):
        for baseline in (tr, cbo):
            assert baseline.value_sources(year)["di_rates"] == (
                "di_entitlement_fit_2008"
            )
    assert tr.value_sources(2040)["claiming"].endswith("_row_2025")
    assert tr.value_sources(2010)["claiming"].endswith("_row_2010")


def test_cpiw_growth_splices_realized_values_before_projections():
    tr, cbo = TR2026Intermediate(), CBO2026LongTerm()
    for year in range(1980, 2026):
        assert cbo.cpiw_growth(year) == tr.cpiw_growth(year)
        assert tr.cpiw_growth(year) == tr2026.cpiw_growth(year)
    for year in range(2026, 2101):
        assert cbo.cpiw_growth(year) == cbo2026.cpiu_growth(year)


# ---------------------------------------------------------------------------
# 5. Claiming and 6. DI
# ---------------------------------------------------------------------------
def test_claim_pmfs_sum_to_one(baseline):
    pmfs = baseline.claim_pmf()
    years = {year for _, year in pmfs}
    assert max(years) >= baseline.claim_table_max_year
    assert {sex for sex, _ in pmfs} == set(SEXES)
    for key, pmf in pmfs.items():
        assert set(pmf) == set(range(62, 71)), key
        assert all(value >= 0.0 for value in pmf.values()), key
        assert sum(pmf.values()) == pytest.approx(1.0, abs=1e-12), key


def test_2026_baselines_read_the_2026_supplement_through_2025():
    for baseline in (TR2026Intermediate(), CBO2026LongTerm()):
        assert baseline.claim_table_max_year == 2025
        assert {year for _, year in baseline.claim_pmf()} == set(
            range(1998, 2026)
        )


def test_every_baseline_supplies_the_2008_di_fit(baseline):
    ours = baseline.di_rates()
    theirs = load_di_entitlement_rates(DIEntitlementSpec())
    assert ours.spec == theirs.spec
    for name in DI_FIELDS:
        assert _same_values(getattr(ours, name), getattr(theirs, name))
    assert ours.provenance["information_boundary_year"] == 2008


# ---------------------------------------------------------------------------
# 7. Provenance
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "factory",
    [
        TR2008Legacy,
        TR2026Intermediate,
        lambda: TR2026Intermediate(asfr_shape="cbo2026"),
        CBO2026LongTerm,
    ],
)
def test_every_recorded_file_hash_is_the_files_hash(factory):
    record = factory().provenance()
    files = dict(record["files_sha256"])
    files.update(record.get("cbo_files_sha256", {}))
    assert files
    for relative, digest in files.items():
        path = ROOT / relative
        assert path.is_relative_to(DATA_EXTERNAL), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
    assert record["name"] and record["vintage"] and record["gaps"]


def test_2026_provenance_names_the_splices_and_pending_defaults():
    for baseline in (TR2026Intermediate(), CBO2026LongTerm()):
        record = baseline.provenance()
        assert "2025" in record["splices"]["cola"]
        assert "2024" in record["splices"]["awi"]
        assert "last actual" in record["splices"]["cola"]
        assert record["builder_defaults_awaiting_ratification"]
        assert any("2008 fit" in gap for gap in record["gaps"])
        assert record["captured_sources_sha256"]["tr2026"]
    cbo = CBO2026LongTerm().provenance()
    assert set(cbo2026.PENDING_RATIFICATION) <= set(
        cbo["builder_defaults_awaiting_ratification"]
    )
