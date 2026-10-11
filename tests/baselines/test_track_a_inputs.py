"""``build_track_a_inputs``: the dry runs' inputs, and its refusals.

Differential tests against the hand-built inputs of the two invented
dry runs (``scripts/track_a_dry_run.py`` and ``scripts/fra68_dry_run.
py``): each script's ``main`` is run up to the point where it hands its
``TrackAInputs`` to the runner, which is replaced by a capture, so the
comparison is with the scripts' own construction code.  Under the
default ``tr2008_intermediate`` baseline every input must be equal:
the oracle parameters, the COLA path, the DI rates, the population
mortality, the claim-age table and the invented cohorts (by the seal
``prepare_track_a_cohort`` sets).  ``TrackAConfig.as_dict()`` must not
change.

INVENTED data only: the cohorts are the invented generator's people
(seed 20260922, the dry runs' default) and the oracle parameter bundle
is INVENTED (the scripts' policyengine-us loader is replaced by it, on
both sides).  Artifact tier: the baselines read committed inputs under
``data/external`` through their pinned accessors.  No PSID file is
opened; no outcome is computed (the runners are never called).
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.util
from functools import cache
from pathlib import Path

import numpy as np
import pytest

from populace_dynamics.baselines import (
    INVENTED_SEED,
    BaselineYearAwareMortality,
    CBO2026LongTerm,
    TR2008Legacy,
    TR2026Intermediate,
    build_track_a_inputs,
    invented_track_a_cohorts,
    project_track_a,
    track_a_config_for,
)
from populace_dynamics.baselines.track_a import RUNNER_LABEL_CAVEAT
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.cola_track_a.mortality import Tr2008YearAwareMortality
from populace_dynamics.cola_track_a.runner import _same_values
from populace_dynamics.fra68_track.config import FRA68Config
from populace_dynamics.ss.params import SSAParameters

ROOT = Path(__file__).resolve().parents[2]
DATA_EXTERNAL = ROOT / "data" / "external"
#: The five hand-built input builders the factory replaces (not edited).
BUILDERS = (
    "scripts/run_track_a_registered.py",
    "scripts/run_fra68_registered.py",
    "scripts/track_a_dry_run.py",
    "scripts/fra68_dry_run.py",
    "src/populace_dynamics/track_a_v2/protocol.py",
)
#: The constructor each of them calls, by input.
LEGACY_CONSTRUCTORS = {
    "cola": "tr2008_baseline_cola",
    "awi": "tr2008_ssa_parameters",
    "mortality": "load_tr2008_mortality",
    "claiming": "load_claiming_pmf",
    "di": "load_di_entitlement_rates",
}
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


class _Captured(Exception):
    """Stops a dry run at the runner call."""


def _script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_b2_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@cache
def _dry_run_inputs(name: str, runner: str):
    """The inputs a dry run hands its runner, with INVENTED oracle params."""
    module = _script(name)
    captured = {}

    def capture(inputs, **kwargs):
        captured["inputs"] = inputs
        captured["config"] = kwargs["config"]
        raise _Captured

    module.load_ssa_parameters = invented_base_params
    setattr(module, runner, capture)
    with pytest.raises(_Captured):
        module.main(["--output-dir", str(ROOT / "unused"), "--draws", "1"])
    return captured["inputs"], captured["config"]


def _assert_same_inputs(ours, theirs) -> None:
    assert ours.params == theirs.params
    assert ours.baseline == theirs.baseline
    assert ours.di_rates.spec == theirs.di_rates.spec
    for name in DI_FIELDS:
        assert _same_values(
            getattr(ours.di_rates, name), getattr(theirs.di_rates, name)
        ), name
    ours_m, theirs_m = ours.population_mortality, theirs.population_mortality
    assert type(ours_m) is type(theirs_m) is Tr2008YearAwareMortality
    for sex in ("female", "male"):
        assert np.array_equal(ours_m.qx_by_sex[sex], theirs_m.qx_by_sex[sex])
    assert dict(ours_m.ratio_by_year) == dict(theirs_m.ratio_by_year)
    assert dict(ours_m.provenance) == dict(theirs_m.provenance)
    assert (ours_m.alternative, ours_m.base_year) == (
        theirs_m.alternative,
        theirs_m.base_year,
    )
    assert ours.claiming_pmf == theirs.claiming_pmf
    ours_c, theirs_c = ours.cohorts_by_wave(), theirs.cohorts_by_wave()
    assert list(ours_c) == list(theirs_c)
    for wave in ours_c:
        assert ours_c[wave].seal is not None
        assert ours_c[wave].seal == theirs_c[wave].seal, wave
        assert ours_c[wave].initial_slice.equals(theirs_c[wave].initial_slice)
    provenance = theirs.provenance
    record = ours.provenance["baseline"]
    assert record["mortality"] == provenance["mortality"]
    assert record["di_rates_sha256"] == provenance["di_rates"]
    assert record["ssa_parameters"] == provenance["ssa_parameters"]
    files = record["files_sha256"]
    for file_name, digest in provenance["tr2008_file_sha256"].items():
        assert files[f"data/external/tr2008/{file_name}"] == digest
    assert provenance["cola_history_sha256"] in files.values()
    assert provenance["claiming_reference_sha256"] in files.values()


# ---------------------------------------------------------------------------
# Differential: the legacy factory equals both dry runs' inputs
# ---------------------------------------------------------------------------
@cache
def _legacy_factory_inputs():
    """The factory's inputs for the Track A dry run's configuration."""
    return build_track_a_inputs(
        TrackAConfig(draw_indices=(0,)),
        TR2008Legacy(),
        data_provenance="invented",
        base_params=invented_base_params(),
    )


def test_track_a_dry_run_inputs_are_the_factorys():
    theirs, config = _dry_run_inputs("track_a_dry_run", "run_track_a")
    assert config == TrackAConfig(draw_indices=(0,))
    ours = _legacy_factory_inputs()
    _assert_same_inputs(ours, theirs)
    assert ours.provenance["baseline"]["invented_cohorts"]["seed"] == (
        INVENTED_SEED
    )


def test_fra68_dry_run_inputs_are_the_factorys():
    """FRA-68 projects the same two populations (rows R0 and R6).

    The factory-built Track A cohorts are passed in (they are compared
    with the FRA-68 dry run's own cohorts by seal), so the comparison
    covers every input without building the invented cohorts again.
    """
    theirs, config = _dry_run_inputs("fra68_dry_run", "run_fra68")
    assert config == FRA68Config(draw_indices=(0,))
    ours = build_track_a_inputs(
        config.track_a_config(),
        TR2008Legacy(),
        data_provenance="invented",
        cohorts=_legacy_factory_inputs().cohorts_by_wave(),
        base_params=invented_base_params(),
    )
    _assert_same_inputs(ours, theirs)


def _called_names(relative: str) -> set[str]:
    """Names of every function or method a source file calls."""
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def test_every_builder_calls_the_constructors_the_legacy_delegates_to():
    """A static guard that the factory still mirrors all five builders.

    The two dry runs are compared value for value above.  The two
    registered entry points and Track A v2 read PSID cohorts, so they
    are checked statically: each builds ``TrackAInputs`` from the same
    five constructors :class:`TR2008Legacy` delegates to (and records in
    its provenance).  A builder that changes constructor fails here, and
    the legacy baseline must follow it.
    """
    recorded = TR2008Legacy().provenance()["constructors"]
    assert {
        key: path.rsplit(".", 1)[1] for key, path in recorded.items()
    } == LEGACY_CONSTRUCTORS
    expected = set(LEGACY_CONSTRUCTORS.values())
    legacy = _called_names("src/populace_dynamics/baselines/legacy.py")
    assert expected <= legacy
    for relative in BUILDERS:
        called = _called_names(relative)
        assert "TrackAInputs" in called, relative
        assert expected <= called, (relative, expected - called)


def test_the_default_configuration_is_not_touched():
    default = TrackAConfig()
    before = default.as_dict()
    legacy = TR2008Legacy()
    assert track_a_config_for(default, legacy) is default
    assert default.as_dict() == before == TrackAConfig().as_dict()
    assert before["claim_table_max_year"] == 2008
    assert before["tr2008_first_rate_year"] == 2008
    assert before["reference_year"] == 2030


# ---------------------------------------------------------------------------
# The 2026 baselines
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def inputs_2026():
    """Both 2026 baselines' inputs on one set of INVENTED cohorts.

    The two baselines share the claim-age table, so the factory would
    build the same cohorts for each; they are built once (and checked
    against a fresh build in ``test_shared_cohorts_are_the_factorys``).
    """
    config = track_a_config_for(
        TrackAConfig(draw_indices=(0,), rows=("R0", "R6")),
        TR2026Intermediate(),
    )
    first = build_track_a_inputs(
        config,
        TR2026Intermediate(),
        data_provenance="invented",
        base_params=invented_base_params(),
    )
    out = {"tr2026_intermediate": (TR2026Intermediate(), config, first)}
    baseline = CBO2026LongTerm()
    assert track_a_config_for(config, baseline) == config
    out["cbo2026_long_term"] = (
        baseline,
        config,
        build_track_a_inputs(
            config,
            baseline,
            data_provenance="invented",
            cohorts=first.cohorts_by_wave(),
            base_params=invented_base_params(),
        ),
    )
    return out


def test_2026_inputs_come_from_the_baseline(inputs_2026):
    for name, (baseline, config, inputs) in inputs_2026.items():
        assert config.claim_table_max_year == 2025
        assert config.as_dict() == {
            **TrackAConfig(draw_indices=(0,), rows=("R0", "R6")).as_dict(),
            "claim_table_max_year": 2025,
        }
        model = inputs.population_mortality
        assert isinstance(model, BaselineYearAwareMortality)
        assert model.years == tuple(range(2009, 2031))
        for year in model.years:
            for sex in ("female", "male"):
                assert np.array_equal(
                    model.qx_by_year[year][sex], baseline.qx(year)[sex]
                )
        assert inputs.claiming_pmf == baseline.claim_pmf()
        assert (
            inputs.baseline.by_determination_year
            == baseline.cola_rates(2008, 2030).by_determination_year
        )
        assert inputs.baseline.rate_for_determination_year(2025) == 0.028
        assert inputs.params == baseline.ssa_parameters(invented_base_params())
        record = inputs.provenance["baseline"]
        assert record["name"] == name
        assert record["runner_label_caveat"] == RUNNER_LABEL_CAVEAT
        assert record["claim_table_max_year"] == 2025
        assert record["projection_years"] == [2009, 2030]
        for cohort in inputs.cohorts_by_wave().values():
            assert cohort.data_provenance == "invented"
            assert cohort.source_provenance["seed"] == INVENTED_SEED


def test_shared_cohorts_are_the_factorys(inputs_2026):
    """CBO's own invented cohort is the shared one (by seal)."""
    baseline = CBO2026LongTerm()
    assert baseline.claim_pmf() == TR2026Intermediate().claim_pmf()
    config = track_a_config_for(TrackAConfig(rows=("R0",)), baseline)
    fresh = invented_track_a_cohorts(config, baseline)
    assert list(fresh) == [2011]
    shared = inputs_2026["cbo2026_long_term"][2].cohort
    assert fresh[2011].seal is not None
    assert fresh[2011].seal == shared.seal
    assert fresh[2011].source_provenance["seed"] == INVENTED_SEED


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def test_registered_real_is_refused_under_a_2026_baseline():
    for baseline in (TR2026Intermediate(), CBO2026LongTerm()):
        config = track_a_config_for(TrackAConfig(), baseline)
        with pytest.raises(ValueError, match="own registered entry point"):
            build_track_a_inputs(
                config, baseline, data_provenance="registered_real"
            )


def test_registered_real_cohorts_are_never_built_here():
    with pytest.raises(ValueError, match="must pass the cohorts"):
        build_track_a_inputs(
            TrackAConfig(),
            TR2008Legacy(),
            data_provenance="registered_real",
            base_params=invented_base_params(),
        )


def test_inconsistent_requests_are_refused(inputs_2026):
    legacy = TR2008Legacy()
    base = invented_base_params()
    tr2026_baseline, tr2026_config, tr2026_inputs = inputs_2026[
        "tr2026_intermediate"
    ]
    with pytest.raises(ValueError, match="track_a_config_for"):
        build_track_a_inputs(
            TrackAConfig(),
            tr2026_baseline,
            data_provenance="invented",
            base_params=base,
        )
    with pytest.raises(ValueError, match="tr2008_alternative"):
        build_track_a_inputs(
            TrackAConfig(tr2008_alternative="low"),
            legacy,
            data_provenance="invented",
            base_params=base,
        )
    with pytest.raises(ValueError, match="written by this factory"):
        build_track_a_inputs(
            tr2026_config,
            tr2026_baseline,
            data_provenance="invented",
            cohorts=tr2026_inputs.cohorts_by_wave(),
            base_params=base,
            provenance={"baseline": "mine"},
        )
    with pytest.raises(ValueError, match="data_provenance"):
        build_track_a_inputs(
            TrackAConfig(), legacy, data_provenance="psid", base_params=base
        )
    with pytest.raises(TypeError, match="Baseline protocol"):
        build_track_a_inputs(
            TrackAConfig(), object(), data_provenance="invented"
        )
    cohorts = tr2026_inputs.cohorts_by_wave()
    with pytest.raises(ValueError, match="no prepared cohort"):
        build_track_a_inputs(
            tr2026_config,
            tr2026_baseline,
            data_provenance="invented",
            cohorts={2011: cohorts[2011]},
            base_params=base,
        )
    with pytest.raises(ValueError, match="has anchor wave"):
        build_track_a_inputs(
            tr2026_config,
            tr2026_baseline,
            data_provenance="invented",
            cohorts={2011: cohorts[2009], 2009: cohorts[2009]},
            base_params=base,
        )
    with pytest.raises(ValueError, match="labelled 'invented'"):
        build_track_a_inputs(
            TrackAConfig(rows=("R0", "R6")),
            legacy,
            data_provenance="registered_real",
            cohorts=cohorts,
            base_params=base,
        )


def test_project_track_a_refuses_what_run_track_a_would(inputs_2026):
    baseline, config, inputs = inputs_2026["tr2026_intermediate"]
    with pytest.raises(ValueError, match="claim rows through 2025"):
        project_track_a(inputs, TrackAConfig(rows=("R0", "R6")))
    # dataclasses.replace resets the seal prepare_track_a_cohort set.
    unsealed = dataclasses.replace(
        inputs, cohort=dataclasses.replace(inputs.cohort)
    )
    assert unsealed.cohort.seal is None
    with pytest.raises(ValueError, match="seal"):
        project_track_a(unsealed, config)
    real_label = dataclasses.replace(
        inputs,
        cohort=dataclasses.replace(
            inputs.cohort, data_provenance="registered_real"
        ),
    )
    with pytest.raises(ValueError, match="INVENTED cohorts only"):
        project_track_a(real_label, config)
    with pytest.raises(ValueError, match="no cohort for anchor waves"):
        project_track_a(
            dataclasses.replace(inputs, additional_cohorts=()), config
        )
