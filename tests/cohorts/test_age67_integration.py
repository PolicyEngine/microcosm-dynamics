"""Staged-PSID structure of the Track U age-67 population (counts only).

Skipped when the staged PSID products under ``~/PolicyEngine/psid-data``
are absent. These tests build the observations and check their structure
and the guards; they compute no income concept, threshold or poverty
status. The one call into the income concept checks that it refuses the
PSID-built rows before computing anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()

needs_real_psid = pytest.mark.skipif(
    not (REAL_DATA / "ind2023er").is_dir()
    or not all(
        (REAL_DATA / "family" / str(wave)).is_dir() for wave in age67.WAVES
    ),
    reason="staged PSID individual and family files not present",
)


@pytest.fixture(scope="module")
def inputs():
    return age67.load_age67_inputs(data_dir=REAL_DATA)


@needs_real_psid
def test_primary_population_structure(inputs):
    cohort = age67.build_age67_cohort(inputs)
    assert cohort.provenance["kind"] == age67.PSID_FILES
    obs = cohort.observations
    assert obs["observation_id"].is_unique
    assert (obs["member_age"] == age67.TARGET_AGE).all()
    assert set(obs["birth_year"]) == set(age67.PRIMARY_BIRTH_YEARS)
    assert (obs["weight"] > 0).all()
    assert obs["stratum"].notna().all() and obs["cluster"].notna().all()
    blocked = obs["wealth_status"] != "family_file"
    assert set(obs.loc[blocked, "wave"]) == {2005, 2007}
    assert set(obs.loc[~blocked, "wave"]) == {2009, 2011, 2013}
    # Structure found on the staged files 2026-09-24 (counts only).
    counts = obs.groupby("birth_year").size().to_dict()
    assert counts == {1937: 81, 1939: 82, 1941: 93, 1943: 116, 1945: 111}
    assert set(inputs.wealth_refusals) == {2005, 2007}


@needs_real_psid
def test_real_rows_are_refused_by_the_income_concept(inputs):
    cohort = age67.build_age67_cohort(inputs)
    with pytest.raises(ValueError, match="wealth supplement"):
        age67.income_rows(cohort, inputs)
    rows = age67.income_rows(cohort, inputs, allow_blocked=True)
    assert rows.attrs["provenance_kind"] == age67.PSID_FILES
    missing = [c for c in ap.REQUIRED_COLUMNS if c not in rows.columns]
    assert not missing
    table = ap.load_nchs_2000_life_table()
    with pytest.raises(ap.AdjustedPovertyError, match="registration"):
        ap.adjusted_incomes(
            rows,
            data_provenance=ap.INVENTED,
            life_table=table,
            thresholds=None,
            ssi=None,
        )
