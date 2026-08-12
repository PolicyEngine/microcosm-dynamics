"""Tests for the phase-0 job-spell imputation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.firms import ic1
from populace_dynamics.firms import spell_imputation as si

BANDS = {
    0: "LT10",
    1: "B10_49",
    2: "B50_99",
    3: "B100_499",
    4: "B500_PLUS",
}


def _donor(n: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "age": rng.integers(18, 65, n),
            "sex": rng.integers(0, 2, n),
            "education": rng.integers(1, 5, n),
            "industry_sector": rng.choice(["31", "44"], n),
            "annual_earnings": rng.lognormal(10.5, 0.5, n),
            "weight": rng.uniform(50, 500, n),
        }
    )
    latent = frame["annual_earnings"] / 40000 + frame["education"] * 0.4
    frame["firm_size_band_code"] = np.clip(latent.astype(int), 0, 4)
    frame["tenure_months"] = np.clip(latent * 12, 0, 480)
    frame["earnings_share"] = np.clip(rng.beta(8, 1, n), 0, 1)
    return frame


def _hosts(n: int = 200, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "person_id": [f"{i:022d}" for i in range(n)],
            "age": rng.integers(18, 65, n),
            "sex": rng.integers(0, 2, n),
            "education": rng.integers(1, 5, n),
            "industry_sector": rng.choice(["31", "44"], n),
            "annual_earnings": rng.lognormal(10.5, 0.5, n),
            "class_of_worker": rng.choice(
                ["private", "federal", "self_employed"], n, p=[0.8, 0.1, 0.1]
            ),
        }
    )


def test_bridge_must_be_one_of_the_ratified_names():
    with pytest.raises(ValueError, match="Unknown bridge"):
        si.SpellImputationSpec(bridge="nlsy", seed=1)


def test_bridge_and_seed_have_no_defaults():
    """A run that does not name its bridge and seed cannot be refereed."""
    with pytest.raises(TypeError):
        si.SpellImputationSpec()
    with pytest.raises(TypeError):
        si.SpellImputationSpec(bridge="sipp_2008_primary")


def test_both_ratified_bridges_are_accepted():
    for bridge in si.BRIDGES:
        assert si.SpellImputationSpec(bridge=bridge, seed=1).bridge == bridge


def test_predictor_missing_from_host_is_rejected():
    spec = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=1)
    with pytest.raises(ValueError, match="Host frame lacks predictors"):
        si.check_frames(_donor(), _hosts().drop(columns=["age"]), spec)


def test_predictor_missing_from_donor_is_rejected():
    spec = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=1)
    with pytest.raises(ValueError, match="Donor frame lacks predictors"):
        si.check_frames(_donor().drop(columns=["age"]), _hosts(), spec)


def test_imputing_over_an_observed_host_column_is_rejected():
    """Overwriting measurement with a draw must be deliberate."""
    spec = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=1)
    hosts = _hosts()
    hosts["tenure_months"] = 24
    with pytest.raises(ValueError, match="already carries imputed"):
        si.check_frames(_donor(), hosts, spec)


def test_missing_class_of_worker_is_rejected():
    spec = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=1)
    fitted = si.fit_spell_model(_donor(), spec, weight_column="weight")
    with pytest.raises(ValueError, match="class of worker"):
        si.impute_spells(
            fitted,
            _hosts().drop(columns=["class_of_worker"]),
            spec,
            band_codes=BANDS,
        )


def test_imputation_emits_valid_ic1():
    spec = si.SpellImputationSpec(bridge="sipp_2014_proxy_chain", seed=7)
    fitted = si.fit_spell_model(_donor(), spec, weight_column="weight")
    out = si.impute_spells(fitted, _hosts(), spec, band_codes=BANDS)
    ic1.validate(out)
    assert list(out.columns) == list(ic1.IC1_COLUMNS)
    assert len(out) == 200


def test_self_employed_never_receives_an_imputed_band():
    """The draw does not get to invent a band that is undefined."""
    spec = si.SpellImputationSpec(bridge="sipp_2014_proxy_chain", seed=7)
    fitted = si.fit_spell_model(_donor(), spec, weight_column="weight")
    out = si.impute_spells(fitted, _hosts(), spec, band_codes=BANDS)
    undefined = out["class_of_worker"].isin(ic1.NO_FIRM_SIZE_CLASSES)
    assert undefined.any()
    assert out.loc[undefined, "firm_size_band"].isna().all()


def test_class_of_worker_is_carried_not_imputed():
    spec = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=3)
    hosts = _hosts()
    fitted = si.fit_spell_model(_donor(), spec, weight_column="weight")
    out = si.impute_spells(fitted, hosts, spec, band_codes=BANDS)
    assert list(out["class_of_worker"]) == list(hosts["class_of_worker"])


def test_run_records_its_bridge_and_seed():
    spec = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=11)
    fitted = si.fit_spell_model(_donor(), spec, weight_column="weight")
    out = si.impute_spells(fitted, _hosts(), spec, band_codes=BANDS)
    assert out.attrs["bridge"] == "sipp_2008_primary"
    assert out.attrs["seed"] == 11
    assert out.attrs["band_is_imputed"] is True


def test_same_seed_reproduces_the_same_draw():
    spec = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=5)
    donor, hosts = _donor(), _hosts()
    fitted = si.fit_spell_model(donor, spec, weight_column="weight")
    a = si.impute_spells(fitted, hosts, spec, band_codes=BANDS)
    b = si.impute_spells(fitted, hosts, spec, band_codes=BANDS)
    assert a["firm_size_band"].equals(b["firm_size_band"])


def test_a_different_seed_changes_the_draw():
    donor, hosts = _donor(), _hosts()
    spec_a = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=5)
    spec_b = si.SpellImputationSpec(bridge="sipp_2008_primary", seed=6)
    fitted = si.fit_spell_model(donor, spec_a, weight_column="weight")
    a = si.impute_spells(fitted, hosts, spec_a, band_codes=BANDS)
    b = si.impute_spells(fitted, hosts, spec_b, band_codes=BANDS)
    assert not a["firm_size_band"].equals(b["firm_size_band"])


def test_imputed_spells_feed_the_calibration_universe():
    spec = si.SpellImputationSpec(bridge="sipp_2014_proxy_chain", seed=9)
    fitted = si.fit_spell_model(_donor(), spec, weight_column="weight")
    out = si.impute_spells(fitted, _hosts(), spec, band_codes=BANDS)
    universe = ic1.calibration_universe(out)
    assert set(universe["class_of_worker"]) == {"private"}
    assert universe.attrs["excluded_total"] > 0
