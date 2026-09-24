"""The committed parameters Track U reads, pinned by SHA-256.

Artifact tier: reads committed files under ``data/external`` (the SSI
capture ``track_u_ssi_parameters.json``, the NCHS 2000 life tables) and
the TR2008-vintage SSA period life table for 2004.  It checks their pins,
their shape and properties any real table has (the price of a life
annuity falls with age and is higher for women than men at 67).  It
computes nothing on PSID data and asserts no poverty value.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import adjusted_poverty as ap

ROOT = Path(__file__).resolve().parents[2]
SSI_CAPTURE = ROOT / "data" / "external" / "track_u_ssi_parameters.json"
NCHS_2000 = ROOT / "data" / "external" / "nchs_life_tables_2000.json"


def test_ssi_capture_matches_its_pin():
    digest = hashlib.sha256(SSI_CAPTURE.read_bytes()).hexdigest()
    assert digest == ap.SSI_PARAMETERS_SHA256
    assert ap.SSI_PARAMETERS_PATH == SSI_CAPTURE


def test_ssi_capture_shape():
    capture = json.loads(SSI_CAPTURE.read_text())
    assert capture["schema_version"] == ap.SSI_SCHEMA_VERSION
    fbr = capture["federal_benefit_rate_monthly"]
    years = [str(year) for year in range(2004, 2013)]
    for kind in ("individual", "couple"):
        assert list(fbr[kind]) == years
        values = [fbr[kind][year] for year in years]
        assert values == sorted(values)
    for year in years:
        assert fbr["individual"][year] < fbr["couple"][year]
    params = ap.load_ssi_parameters()
    assert params.fbr_annual(2010, False) == 12 * fbr["individual"]["2010"]
    assert params.resource_limit(False) < params.resource_limit(True)
    source = capture["source"]
    assert len(source["policyengine_us_files_sha256"]) == 7
    assert source["policyengine_us_revision"]


def test_nchs_2000_life_table_and_annuity_prices():
    assert ap.NCHS_2000_PATH == NCHS_2000
    table = ap.load_nchs_2000_life_table()
    assert table.last_age == 100
    male = [
        ap.annuity_factor_single(table, "male", age) for age in (62, 67, 72)
    ]
    assert male == sorted(male, reverse=True)
    female = ap.annuity_factor_single(table, "female", 67)
    assert female > male[1]
    joint = ap.annuity_factor_joint(table, "male", 67, "female", 67)
    assert joint == pytest.approx(0.5 * (male[1] + female))
    with pytest.raises(ap.AdjustedPovertyError, match="sha256"):
        ap.load_nchs_2000_life_table(expected_sha256="0" * 64)


def test_ssa_2004_period_life_table_loads():
    table = ap.load_ssa_period_2004_life_table()
    assert table.name == "ssa_period_2004"
    assert table.last_age == 119
    assert ap.load_life_table("ssa_period_2004").qx == table.qx


def test_census_thresholds_are_not_yet_captured():
    assert ap.THRESHOLDS_SHA256 is None
    assert not ap.THRESHOLDS_PATH.exists()
    with pytest.raises(ap.ThresholdsNotCapturedError):
        ap.load_poverty_thresholds()
