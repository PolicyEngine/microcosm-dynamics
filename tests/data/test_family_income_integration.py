"""Staged-PSID checks of the family income and wealth reader.

Skipped when the staged PSID family files under ``~/PolicyEngine/psid-data``
are absent.  These tests verify labels, code domains and component
identities only: they compute no income concept, threshold or poverty
status and assert no value of any income or wealth variable.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.data import family_income as fi

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()

needs_real_psid = pytest.mark.skipif(
    not all(
        (REAL_DATA / "family" / str(wave)).is_dir() for wave in fi.INCOME_WAVES
    ),
    reason="staged PSID family files 2005-2013 not present",
)


@needs_real_psid
@pytest.mark.parametrize("wave", fi.INCOME_WAVES)
def test_income_labels_verify_on_the_staged_files(wave):
    frame = fi.read_family_income(wave, data_dir=REAL_DATA, nrows=50)
    assert set(fi.income_variables(wave)) <= set(frame.columns)
    assert (frame["income_year"] == wave - 1).all()


@needs_real_psid
@pytest.mark.parametrize("wave", fi.WEALTH_WAVES)
def test_wealth_labels_verify_on_the_staged_files(wave):
    frame = fi.read_family_wealth(wave, data_dir=REAL_DATA, nrows=50)
    assert set(fi.wealth_variables(wave)) <= set(frame.columns)


@needs_real_psid
@pytest.mark.parametrize("wave", fi.WEALTH_SUPPLEMENT_WAVES)
def test_supplement_waves_are_refused_while_unstaged(wave):
    status = fi.wealth_supplement_status(wave, data_dir=REAL_DATA)
    if status["staged"]:
        pytest.skip("a supplement has been staged; adjudicate its labels")
    with pytest.raises(fi.WealthSupplementNotStagedError, match=str(wave)):
        fi.read_family_wealth(wave, data_dir=REAL_DATA)


@needs_real_psid
def test_component_identities_hold_on_every_family():
    """Counts only: TOTAL FAMILY INCOME and WEALTH1 add up exactly.

    Found on the staged files 2026-09-24: the seven aggregates sum to
    TOTAL FAMILY INCOME and the codebook components to WEALTH1 (and
    WEALTH1 plus home equity to WEALTH2 within $10) for every family; the
    head and wife taxable total equals labor, farm, business-labor and the
    ten asset items for all but two 2005 families and within $10
    elsewhere.
    """

    incomes = pd.concat(
        [
            fi.read_family_income(wave, data_dir=REAL_DATA)
            for wave in fi.INCOME_WAVES
        ],
        ignore_index=True,
    )
    income_counts = fi.reconcile_family_income(incomes)
    for wave, counts in income_counts.items():
        total = counts["total_family_income"]
        assert total["n_exact"] == total["n_families"], wave
        for identity in ("hw_transfer", "ofum_transfer"):
            assert counts[identity]["n_beyond_tolerance"] == 0, (
                wave,
                identity,
            )
        allowed = 2 if wave == "2005" else 0
        assert counts["hw_taxable"]["n_beyond_tolerance"] <= allowed, wave
    wealth = pd.concat(
        [
            fi.read_family_wealth(wave, data_dir=REAL_DATA)
            for wave in fi.WEALTH_WAVES
        ],
        ignore_index=True,
    )
    for wave, counts in fi.reconcile_wealth1(wealth).items():
        assert counts["wealth1"]["n_exact"] == counts["wealth1"]["n_families"]
        assert counts["wealth2"]["n_beyond_tolerance"] == 0, wave
