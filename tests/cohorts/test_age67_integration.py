"""Staged-PSID structure of the Track U age-67 population (counts only).

Skipped when the staged PSID products under ``~/PolicyEngine/psid-data``
are absent. These tests build the observations and check their structure
and the guards; they compute no income concept, threshold or poverty
status. The one call into the income concept checks that it refuses the
PSID-built rows before computing anything.

Since the specification's u1-draft-6 (2026-09-25) the 2005 and 2007 wealth
supplements are staged and adjudicated, so every observation's family has
WEALTH1 (1937 and 1939 from the supplements) and nothing is refused.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.data import family_income
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
    supplement = obs["wealth_status"] == "wealth_supplement"
    family_file = obs["wealth_status"] == "family_file"
    assert (supplement | family_file).all()
    assert set(obs.loc[supplement, "wave"]) == {2005, 2007}
    assert set(obs.loc[family_file, "wave"]) == {2009, 2011, 2013}
    # Structure found on the staged files 2026-09-24 (counts only).
    counts = obs.groupby("birth_year").size().to_dict()
    assert counts == {1937: 81, 1939: 82, 1941: 93, 1943: 116, 1945: 111}
    assert inputs.wealth_refusals == {}
    # the supplements were read from the adjudicated files, whose hashes
    # the loader records with every other PSID file it read
    files = inputs.provenance["psid_files_sha256"]
    for wave, pins in family_income.WEALTH_SUPPLEMENT_SHA256.items():
        for name, digest in pins.items():
            assert files[f"wealth/{wave}/{name}"] == digest
    # the fallback rule on the staged PSID gives the headline the
    # specification block records (U0)
    from populace_dynamics.uniform_cut_track_u import rows, runner

    headline = rows.specification_block()["population"]["headline"]
    assert runner.headline_row(inputs) == headline["staged_psid_headline"]
    assert runner.headline_row(inputs) == rows.PRIMARY_ROW


@needs_real_psid
def test_real_rows_are_refused_by_the_income_concept(inputs):
    cohort = age67.build_age67_cohort(inputs)
    # every observation joins its family's income and wealth (u1-draft-6)
    rows = age67.income_rows(cohort, inputs)
    assert rows.attrs["left_out"] == {"wealth_supplement_not_staged": 0}
    assert len(rows) == len(cohort.observations)
    assert rows["wealth1"].notna().all()
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
