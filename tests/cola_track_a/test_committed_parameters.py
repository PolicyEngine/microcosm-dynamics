"""Track A assembly against the committed parameter captures.

These tests read committed evidence under "data/external" (the TR2008
capture in data/external/tr2008, the 2008-vintage DI inputs in
data/external/di_asr_2008, the realized COLA history and the claim-age
table) and the A1 draft block.  The cohort is INVENTED
(:mod:`populace_dynamics.cola_track_a.invented`); the oracle parameters
are INVENTED too, so no policyengine-us checkout is needed.  Nothing here
reads PSID or a comparator value.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import (
    TrackAConfig,
    TrackAInputs,
    invented,
    prepare_track_a_cohort,
    run_track_a,
)
from populace_dynamics.cola_track_a.mortality import load_tr2008_mortality
from populace_dynamics.cola_track_a.runner import (
    a1_parameter_block,
    load_claiming_pmf,
    tr2008_baseline_cola,
    tr2008_ssa_parameters,
)
from populace_dynamics.data import tr2008
from populace_dynamics.engine.di_entitlement_rates import (
    load_di_entitlement_rates,
)
from populace_dynamics.estimates.parameters import load_cola_history
from populace_dynamics.ss.params import SSAParameters

ROOT = Path(__file__).resolve().parents[2]
#: The committed inputs these tests read through the loaders.
COMMITTED_INPUT_DIRS = (
    ROOT / "data" / "external" / "tr2008",
    ROOT / "data" / "external" / "di_asr_2008",
)


def test_committed_inputs_are_present():
    for directory in COMMITTED_INPUT_DIRS:
        assert directory.is_dir(), directory


def _invented_params() -> SSAParameters:
    """INVENTED oracle parameters (4 percent wage growth from 1951)."""
    return SSAParameters(
        nawi={y: 2_800.0 * 1.04 ** (y - 1951) for y in range(1951, 2086)},
        wage_base={1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


def test_mortality_is_the_a2_substitute():
    model = load_tr2008_mortality(range(2011, 2031))
    frame = pd.DataFrame(
        {"age": [0, 40, 64, 65, 90, 119, 120], "sex": ["male"] * 7}
    )
    table = {row.age: row.qx for row in tr2008.period_life_table_2004("male")}
    for year in (2011, 2020, 2030):
        values = model.probabilities_for_year(frame, year)
        expected = [
            min(
                1.0,
                table[min(age, 119)]
                * tr2008.mortality_improvement_ratio(year, age),
            )
            for age in frame["age"]
        ]
        assert np.allclose(values, expected, rtol=0, atol=1e-15)


def test_baseline_cola_is_the_a1_rate_path():
    realized = load_cola_history()
    baseline = tr2008_baseline_cola(realized)
    block = a1_parameter_block()["rate_path"]["baseline"]
    for year, percent in block.items():
        assert baseline.rate_for_determination_year(int(year)) == (
            pytest.approx(percent / 100.0, abs=1e-12)
        )
    for year in range(1979, 2008):
        assert baseline[year] == realized[year]
    for first, minimum in ((2009, 0.015), (2010, 0.018)):
        reform = sb.COLAReform(first_reduced_determination_year=first)
        assert sb.minimum_reformed_rate(
            baseline, reform, through_determination_year=2030
        ) == pytest.approx(minimum, abs=1e-12)


def test_claiming_pmf_is_the_a3_table():
    ours = load_claiming_pmf()
    theirs, _ = psid2010._load_claiming_pmf(psid2010.CLAIMING_REFERENCE_PATH)
    assert ours == theirs


def test_tr2008_awi_replaces_the_oracle_series_from_1975():
    base = _invented_params()
    params = tr2008_ssa_parameters(base)
    assert params.nawi[1974] == base.nawi[1974]
    for year in (1975, 2006, 2017, 2040, 2085):
        assert params.nawi[year] == tr2008.awi(year)
    assert params.pe_us_revision.startswith("INVENTED+tr2008_awi")


def test_end_to_end_with_committed_rates_on_an_invented_cohort():
    config = TrackAConfig(draw_indices=(0,), rows=("R0", "R2"))
    claiming_pmf = load_claiming_pmf()
    a3 = psid2010.build_psid2010_cohort(
        invented.invented_psid2010_inputs(claiming_pmf=claiming_pmf)
    )
    cohort = prepare_track_a_cohort(
        a3, data_provenance="invented", config=config
    )
    result = run_track_a(
        TrackAInputs(
            cohort=cohort,
            params=tr2008_ssa_parameters(_invented_params()),
            baseline=tr2008_baseline_cola(load_cola_history()),
            di_rates=load_di_entitlement_rates(config.di_spec),
            population_mortality=load_tr2008_mortality(range(2011, 2031)),
            claiming_pmf=claiming_pmf,
        ),
        config=config,
        check_tr2008_parameters=True,
    )
    consistency = result["parameter_consistency"]
    assert consistency["tr2008_values_compared"] is True
    assert consistency["consistent"] is True, consistency
    for row in result["rows"].values():
        assert row["status"] == "tabulated", row["status"]
    flows = result["draws"]["0"]["di_stock_flow"]
    assert [row["year"] for row in flows] == list(range(2011, 2031))
    assert result["reduced_rate_minimum_by_row"]["R0"] == pytest.approx(0.015)


def test_registered_run_refuses_inputs_the_config_does_not_name():
    # INVENTED cohort labelled registered_real only to reach the interlock;
    # the refusal comes before any projection.  The baseline keeps the
    # realized 2008 rate although the config names TR2008 from 2008.
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    claiming_pmf = load_claiming_pmf()
    a3 = psid2010.build_psid2010_cohort(
        invented.invented_psid2010_inputs(claiming_pmf=claiming_pmf)
    )
    cohort = prepare_track_a_cohort(
        a3, data_provenance="invented", config=config
    )
    inputs = TrackAInputs(
        cohort=replace(cohort, data_provenance="registered_real"),
        params=tr2008_ssa_parameters(_invented_params()),
        baseline=tr2008_baseline_cola(load_cola_history(), first_year=2009),
        di_rates=load_di_entitlement_rates(config.di_spec),
        population_mortality=load_tr2008_mortality(range(2011, 2031)),
        claiming_pmf=claiming_pmf,
    )
    with pytest.raises(ValueError, match=r"differ.*cola_path"):
        run_track_a(
            inputs, config=config, registration_pointer="INVENTED-POINTER"
        )
