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
needs_supplements = pytest.mark.skipif(
    not all(
        (REAL_DATA / "wealth" / str(wave)).is_dir()
        for wave in fi.WEALTH_SUPPLEMENT_WAVES
    ),
    reason="staged PSID 2005 and 2007 wealth supplements not present",
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
@needs_supplements
@pytest.mark.parametrize("wave", fi.WEALTH_SUPPLEMENT_WAVES)
def test_supplements_are_the_adjudicated_files_and_join_one_to_one(wave):
    """The staged supplement is the pinned file (Release 2), its labels
    verify, and its family ID joins the family file's interview number one
    to one (found 2026-09-25: 8,002 families in 2005, 8,289 in 2007;
    counts only)."""

    status = fi.wealth_supplement_status(wave, data_dir=REAL_DATA)
    assert status["staged"] and status["adjudicated"], status
    frame = fi.read_family_wealth(wave, data_dir=REAL_DATA, nrows=50)
    assert list(frame.columns) == [
        "wave",
        "interview",
        *fi.wealth_variables(wave),
    ]
    join = fi.wealth_supplement_join(wave, data_dir=REAL_DATA)
    assert join["n_supplement_only"] == 0
    assert join["n_family_file_only"] == 0
    assert (
        join["n_matched"]
        == join["n_supplement_records"]
        == (join["n_family_file_records"])
    )
    assert join["n_matched"] == {2005: 8002, 2007: 8289}[wave]


@needs_real_psid
def test_component_identities_hold_on_every_family():
    """Counts only: TOTAL FAMILY INCOME and WEALTH1 add up exactly.

    Found on the staged files 2026-09-24 (and 2026-09-25 for the 2005 and
    2007 wealth supplements): the seven aggregates sum to TOTAL FAMILY
    INCOME and the codebook components to WEALTH1 (and WEALTH1 plus home
    equity to WEALTH2 within $10) for every family; the
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
    waves = [
        *(
            wave
            for wave in fi.WEALTH_SUPPLEMENT_WAVES
            if (REAL_DATA / "wealth" / str(wave)).is_dir()
        ),
        *fi.WEALTH_WAVES,
    ]
    wealth = pd.concat(
        [fi.read_family_wealth(wave, data_dir=REAL_DATA) for wave in waves],
        ignore_index=True,
    )
    reconciled = fi.reconcile_wealth1(wealth)
    assert sorted(reconciled) == [str(wave) for wave in waves]
    for wave, counts in reconciled.items():
        assert counts["wealth1"]["n_exact"] == counts["wealth1"]["n_families"]
        assert counts["wealth2"]["n_beyond_tolerance"] == 0, wave
