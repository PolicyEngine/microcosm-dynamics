"""U2 parameters (section 13, group "Parameters").

Complete years, 2022 precision, exact 2012 threshold/SSI overlap, unknown
revision refusal and constant checks; U1 captures refused as U2 sources;
caller-supplied hashes cannot bypass the target-bound bundle; U1's own
guards refuse the Track M and U2 captures.
"""

from __future__ import annotations

import copy
import dataclasses
import inspect
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.min_benefit_track_m import thresholds as track_m
from populace_dynamics.uniform_cut_track_u import runner as u1_runner
from populace_dynamics.uniform_cut_track_u2 import (
    diagnostics,
    identity,
    invented,
    parameters,
)

ROOT = Path(__file__).resolve().parents[2]
U2_SSI = ROOT / "data" / "external" / "track_u2_ssi_parameters_2012_2022.json"
TRACK_M = ROOT / "data" / "external" / "census_poverty_thresholds_1982_2022.json"


@pytest.fixture(scope="module")
def thresholds():
    return parameters.load_u2_thresholds()


@pytest.fixture(scope="module")
def ssi():
    return parameters.load_u2_ssi_parameters()


def test_threshold_capture_is_the_pinned_track_m_file(thresholds):
    assert parameters.THRESHOLDS_PATH == TRACK_M
    assert parameters.THRESHOLDS_SHA256 == track_m.TRACK_M_THRESHOLDS_SHA256
    assert thresholds.provenance["target_id"] == "U2"
    assert thresholds.provenance["sha256"] == parameters.THRESHOLDS_SHA256


def test_threshold_coverage_includes_every_required_year(thresholds):
    for year in (2012, 2014, 2016, 2018, 2020, 2022):
        assert year in thresholds.weighted_average
        assert year in thresholds.matrix
        for size in range(1, 12):
            value, _ = ap.threshold_for(
                thresholds, year, size, 0, "census_weighted_average_65plus"
            )
            assert value > 0


def test_2012_equals_u1_capture_in_every_entry(thresholds):
    u1 = ap.load_poverty_thresholds()
    assert thresholds.weighted_average[2012] == u1.weighted_average[2012]
    assert thresholds.matrix[2012] == u1.matrix[2012]


def test_2022_precision_is_read_as_captured(thresholds):
    raw = json.loads(TRACK_M.read_text())
    assert thresholds.provenance["weighted_average_unit_dollars_2022"] == 10
    for row, value in raw["weighted_average"]["2022"].items():
        assert thresholds.weighted_average[2022][row] == float(value)


def test_ssi_capture_years_revision_constants_and_2012(ssi):
    assert sorted(ssi.fbr_individual_monthly) == list(range(2012, 2023))
    assert sorted(ssi.fbr_couple_monthly) == list(range(2012, 2023))
    assert ssi.provenance["target_id"] == "U2"
    u1 = ap.load_ssi_parameters()
    assert ssi.fbr_individual_monthly[2012] == u1.fbr_individual_monthly[2012]
    assert ssi.fbr_couple_monthly[2012] == u1.fbr_couple_monthly[2012]
    for name in (
        "general_income_exclusion_monthly",
        "earned_income_exclusion_monthly",
        "earned_income_share_excluded",
        "resource_limit_individual",
        "resource_limit_couple",
    ):
        assert getattr(ssi, name) == getattr(u1, name)


@pytest.mark.parametrize("revision", [None, "", "unknown", "abc123"])
def test_unknown_revision_is_refused(revision):
    data = json.loads(U2_SSI.read_text())
    data["source"]["policyengine_us_revision"] = revision
    with pytest.raises(parameters.U2ParameterError, match="revision"):
        parameters.validate_u2_ssi_document(data)


def test_varying_constants_and_other_years_are_refused():
    data = json.loads(U2_SSI.read_text())
    varying = copy.deepcopy(data)
    varying["verification"]["constant_parameters"][
        "general_income_exclusion"
    ] = list(range(2012, 2020))
    with pytest.raises(parameters.U2ParameterError, match="not constant"):
        parameters.validate_u2_ssi_document(varying)
    short = copy.deepcopy(data)
    short["years"] = list(range(2013, 2023))
    with pytest.raises(parameters.U2ParameterError, match="2012-2022"):
        parameters.validate_u2_ssi_document(short)
    shifted = copy.deepcopy(data)
    shifted["federal_benefit_rate_monthly"]["individual"]["2012"] = 699.0
    with pytest.raises(parameters.U2ParameterError, match="2012"):
        parameters.validate_u2_ssi_document(shifted)
    other = copy.deepcopy(data)
    other["target_id"] = "U1"
    with pytest.raises(ValueError, match="not 'U2'"):
        parameters.validate_u2_ssi_document(other)


def test_loaders_take_no_caller_supplied_hash():
    for loader in (
        parameters.load_u2_thresholds,
        parameters.load_u2_ssi_parameters,
    ):
        assert list(inspect.signature(loader).parameters) == []


def test_u1_captures_are_refused_as_u2_sources(u2_params):
    u1_thresholds = parameters.U2Parameters(
        thresholds=ap.load_poverty_thresholds(),
        ssi=u2_params.ssi,
        life_tables=u2_params.life_tables,
    )
    with pytest.raises(parameters.U2ParameterError, match="U1 capture"):
        parameters.check_u2_parameters(u1_thresholds, ap.INVENTED)
    u1_ssi = parameters.U2Parameters(
        thresholds=u2_params.thresholds,
        ssi=ap.load_ssi_parameters(),
        life_tables=u2_params.life_tables,
    )
    with pytest.raises(parameters.U2ParameterError, match="U1 capture"):
        parameters.check_u2_parameters(u1_ssi, ap.INVENTED)
    with pytest.raises(parameters.U2ParameterError, match="U1 capture"):
        parameters._read_pinned(
            parameters.U1_THRESHOLDS_PATH, parameters.THRESHOLDS_SHA256, "x"
        )


def test_registered_check_needs_every_u2_pin(u2_params, thresholds):
    with pytest.raises(parameters.U2ParameterError, match="Census"):
        parameters.check_u2_parameters(u2_params, ap.REGISTERED_REAL)
    committed = dataclasses.replace(u2_params, thresholds=thresholds)
    parameters.check_u2_parameters(committed, ap.REGISTERED_REAL)
    relabelled = dataclasses.replace(
        committed,
        thresholds=dataclasses.replace(
            thresholds,
            provenance={**thresholds.provenance, "sha256": "0" * 64},
        ),
    )
    with pytest.raises(parameters.U2ParameterError, match="Census"):
        parameters.check_u2_parameters(relabelled, ap.REGISTERED_REAL)
    ssi_hash = dataclasses.replace(
        committed,
        ssi=dataclasses.replace(
            committed.ssi,
            provenance={**committed.ssi.provenance, "sha256": "0" * 64},
        ),
    )
    with pytest.raises(parameters.U2ParameterError, match="SSI"):
        parameters.check_u2_parameters(ssi_hash, ap.REGISTERED_REAL)


def test_u1_runner_refuses_the_track_m_and_u2_captures(thresholds, ssi):
    params = u1_runner.committed_parameters(ap.load_poverty_thresholds())
    track_m_thresholds = dataclasses.replace(
        params, thresholds=dataclasses.replace(
            thresholds, provenance={"kind": "census_capture", "sha256": parameters.THRESHOLDS_SHA256}
        )
    )
    with pytest.raises(u1_runner.TrackURunError, match="Census"):
        u1_runner._check_parameters(track_m_thresholds, ap.REGISTERED_REAL)
    u2_ssi = dataclasses.replace(params, ssi=ssi)
    with pytest.raises(u1_runner.TrackURunError, match="SSI"):
        u1_runner._check_parameters(u2_ssi, ap.REGISTERED_REAL)
    with pytest.raises(ap.AdjustedPovertyError, match="sha256"):
        ap.load_poverty_thresholds(TRACK_M)
    with pytest.raises(ap.AdjustedPovertyError, match="sha256"):
        ap.load_ssi_parameters(U2_SSI)


def test_diagnostics_pin_equals_the_parameter_pin():
    assert diagnostics.SSI_SHA256 == parameters.SSI_SHA256
    assert diagnostics.SSI_PATH == parameters.SSI_PATH
    rates = diagnostics.federal_benefit_rates()
    assert rates["individual"] == parameters.load_u2_ssi_parameters().fbr_individual_monthly


def test_invented_fbr_placement_table_equals_the_capture():
    ssi = parameters.load_u2_ssi_parameters()
    assert {
        year: float(value)
        for year, value in invented.FBR_INDIVIDUAL_MONTHLY.items()
    } == dict(ssi.fbr_individual_monthly)


def test_life_tables_are_the_inherited_pins(u2_params):
    for basis, table in u2_params.life_tables.items():
        assert table.name == basis
    assert (
        u2_params.life_tables["nchs_2000"].source["sha256"]
        == ap.NCHS_2000_SHA256
    )
    assert identity.U1_SSI_SHA256 == ap.SSI_PARAMETERS_SHA256
    assert identity.U1_THRESHOLDS_SHA256 == ap.THRESHOLDS_SHA256


def test_invented_life_table_only_in_an_invented_run(u2_params):
    fake = ap.LifeTable(
        name=ap.INVENTED_LIFE_TABLE,
        qx={"male": (0.5,) * 120, "female": (0.5,) * 120},
    )
    bundle = dataclasses.replace(
        u2_params, life_tables={**u2_params.life_tables, "nchs_2000": fake}
    )
    parameters.check_u2_parameters(bundle, ap.INVENTED)
    with pytest.raises(parameters.U2ParameterError):
        parameters.check_u2_parameters(bundle, ap.REGISTERED_REAL)
