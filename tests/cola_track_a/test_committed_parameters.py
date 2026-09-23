"""Track A assembly against the committed parameter captures.

These tests read committed evidence under "data/external" (the TR2008
capture in data/external/tr2008, the 2008-vintage DI inputs in
data/external/di_asr_2008, the realized COLA history, the claim-age table
and the statutory capture data/external/track_a_statutory_parameters.json)
and the A1 block.  The cohort is INVENTED
(:mod:`populace_dynamics.cola_track_a.invented`).  The oracle parameters
are built from the committed statutory capture
(:func:`populace_dynamics.cola_track_a.statutory.captured_ssa_parameters`),
or are INVENTED where a test says so, so no policyengine-us checkout is
needed.  Nothing here reads PSID or a comparator value.
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
from populace_dynamics.cola_track_a.mortality import (
    Tr2008YearAwareMortality,
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.runner import (
    a1_parameter_block,
    load_claiming_pmf,
    tr2008_baseline_cola,
    tr2008_ssa_parameters,
)
from populace_dynamics.cola_track_a.statutory import (
    captured_ssa_parameters,
)
from populace_dynamics.data import tr2008
from populace_dynamics.engine.di_entitlement_rates import (
    load_di_entitlement_rates,
)
from populace_dynamics.engine.steps import AgeSexMortalityModel
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
            params=captured_ssa_parameters(),
            baseline=tr2008_baseline_cola(load_cola_history()),
            di_rates=load_di_entitlement_rates(config.di_spec),
            population_mortality=load_tr2008_mortality(range(2011, 2031)),
            claiming_pmf=claiming_pmf,
        ),
        config=config,
        check_committed_parameters=True,
    )
    consistency = result["parameter_consistency"]
    assert consistency["committed_values_compared"] is True
    assert consistency["consistent"] is True, consistency
    assert set(consistency["checks"]) == {
        "cola_path",
        "awi",
        "mortality_values",
        "di_rates",
        "claiming_pmf",
        "di_spec",
        "mortality",
        "claim_table_max_year",
        # statutory.statutory_value_checks
        "realized_cola_history",
        "contribution_and_benefit_base",
        "contribution_and_benefit_base_tr2008",
        "awi_before_1975",
        "bend_points",
        "pia_factors",
        "full_retirement_age",
        "early_reduction",
        "delayed_retirement_credit",
        "auxiliary_constants",
    }
    for row in result["rows"].values():
        assert row["status"] == "tabulated", row["status"]
    # Draw diagnostics are keyed by the population's anchor wave.
    assert set(result["draws"]) == {"2011"}
    flows = result["draws"]["2011"]["0"]["di_stock_flow"]
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
        params=captured_ssa_parameters(),
        baseline=tr2008_baseline_cola(load_cola_history(), first_year=2009),
        di_rates=load_di_entitlement_rates(config.di_spec),
        population_mortality=load_tr2008_mortality(range(2011, 2031)),
        claiming_pmf=claiming_pmf,
    )
    with pytest.raises(ValueError, match=r"differ.*\['cola_path'\]"):
        run_track_a(
            inputs, config=config, registration_pointer="INVENTED-POINTER"
        )


def _invented_cohort(config: TrackAConfig):
    """The INVENTED cohort as prepare_track_a_cohort returns it (sealed)."""

    a3 = psid2010.build_psid2010_cohort(
        invented.invented_psid2010_inputs(claiming_pmf=load_claiming_pmf())
    )
    return prepare_track_a_cohort(
        a3, data_provenance="invented", config=config
    )


def _registered_inputs(config: TrackAConfig, **changes) -> TrackAInputs:
    """Committed parameters on the INVENTED cohort, labelled
    registered_real only to reach the interlock (the refusals below come
    before any projection)."""

    claiming_pmf = load_claiming_pmf()
    cohort = _invented_cohort(config)
    values = {
        "cohort": replace(cohort, data_provenance="registered_real"),
        "params": captured_ssa_parameters(),
        "baseline": tr2008_baseline_cola(load_cola_history()),
        "di_rates": load_di_entitlement_rates(config.di_spec),
        "population_mortality": load_tr2008_mortality(range(2011, 2031)),
        "claiming_pmf": claiming_pmf,
    }
    values.update(changes)
    return TrackAInputs(**values)


def _scaled_di_rates(config: TrackAConfig):
    # INVENTED perturbation of the committed rates; the spec is unchanged.
    rates = load_di_entitlement_rates(config.di_spec)
    return replace(rates, incidence=rates.incidence * 0.5)


def _relabelled_mortality():
    # INVENTED qx under the labels the config names (intermediate, 2004).
    committed = load_tr2008_mortality(range(2011, 2031))
    return Tr2008YearAwareMortality(
        qx_by_sex={
            sex: values * 0.5 for sex, values in committed.qx_by_sex.items()
        },
        ratio_by_year=committed.ratio_by_year,
        alternative=committed.alternative,
        base_year=committed.base_year,
    )


def _flat_mortality():
    # INVENTED flat mortality with no year axis.
    return AgeSexMortalityModel(
        bands=((0, 64), (65, 120)),
        probability={
            ("0-64", "female"): 0.002,
            ("0-64", "male"): 0.003,
            ("65+", "female"): 0.03,
            ("65+", "male"): 0.04,
        },
    )


@pytest.mark.parametrize(
    ("field", "build", "check"),
    [
        ("di_rates", _scaled_di_rates, "di_rates"),
        (
            "population_mortality",
            lambda config: _relabelled_mortality(),
            "mortality_values",
        ),
        (
            "population_mortality",
            lambda config: _flat_mortality(),
            "mortality_values",
        ),
        (
            "claiming_pmf",
            lambda config: invented.invented_claiming_pmf(),
            "claiming_pmf",
        ),
    ],
)
def test_registered_run_refuses_values_that_are_not_the_committed_ones(
    field, build, check
):
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    inputs = _registered_inputs(config, **{field: build(config)})
    with pytest.raises(ValueError, match=rf"differ.*\['{check}'\]"):
        run_track_a(
            inputs, config=config, registration_pointer="INVENTED-POINTER"
        )


def test_committed_value_checks_name_each_mismatch():
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    # The sealed invented cohort as prepared (a cohort relabelled with
    # dataclasses.replace loses the preparation seal and is refused).
    inputs = _registered_inputs(
        config,
        cohort=_invented_cohort(config),
        di_rates=_scaled_di_rates(config),
        population_mortality=_flat_mortality(),
        claiming_pmf=invented.invented_claiming_pmf(),
    )
    result = run_track_a(
        inputs, config=config, check_committed_parameters=True
    )
    checks = result["parameter_consistency"]["checks"]
    assert checks["di_rates"]["mismatched"] == ["incidence"]
    assert checks["mortality_values"]["mismatched"] == [
        "not_the_a2_substitute"
    ]
    assert checks["mortality_values"]["runtime_class"] == (
        "AgeSexMortalityModel"
    )
    assert checks["claiming_pmf"]["consistent"] is False
    assert checks["cola_path"]["consistent"] is True
    assert result["parameter_consistency"]["consistent"] is False


class _ReplacedRates:
    """INVENTED rate source: the committed baseline with one year replaced."""

    def __init__(self, baseline, year, rate):
        self._baseline, self._year, self._rate = baseline, year, rate

    def rate_for_determination_year(self, year):
        if year == self._year:
            return self._rate
        return self._baseline.rate_for_determination_year(year)

    def __getattr__(self, name):
        return getattr(self._baseline, name)


@pytest.mark.parametrize(
    ("changes", "check"),
    [
        # INVENTED: the third PIA factor read as 16 percent.
        (
            lambda: {
                "params": replace(
                    captured_ssa_parameters(), pia_factors=(0.9, 0.32, 0.16)
                )
            },
            "pia_factors",
        ),
        # INVENTED: 42,300 for the 1986 contribution and benefit base.
        (
            lambda: {
                "params": replace(
                    captured_ssa_parameters(),
                    wage_base={
                        **captured_ssa_parameters().wage_base,
                        1986: 42_300.0,
                    },
                )
            },
            "contribution_and_benefit_base",
        ),
        # INVENTED: the realized 1990 increase (5.4 percent) read as 5.0.
        (
            lambda: {
                "baseline": _ReplacedRates(
                    tr2008_baseline_cola(load_cola_history()), 1990, 0.05
                )
            },
            "realized_cola_history",
        ),
    ],
)
def test_registered_run_refuses_statutory_values_not_the_committed_ones(
    changes, check
):
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    inputs = _registered_inputs(config, **changes())
    with pytest.raises(ValueError, match=rf"differ.*{check}"):
        run_track_a(
            inputs, config=config, registration_pointer="INVENTED-POINTER"
        )


def test_registered_run_refuses_an_invented_cohort_relabelled_real():
    # Every committed value agrees, so the run reaches the source check:
    # the INVENTED cohort's A3 provenance is "invented", which a
    # registered_real label contradicts.
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    inputs = _registered_inputs(config)
    with pytest.raises(ValueError, match="source provenance is 'invented'"):
        run_track_a(
            inputs, config=config, registration_pointer="INVENTED-POINTER"
        )
