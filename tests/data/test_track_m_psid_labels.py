"""Staged-PSID label checks of the Track M readers (plan item M3).

Skipped when the staged PSID under ``~/PolicyEngine/psid-data`` is absent.
Every check reads setup-file labels and SAS format blocks only: no data
value of any person or family is read, compared or asserted.

* Every adjudicated variable of :mod:`populace_dynamics.data.
  social_security_receipt` and :mod:`populace_dynamics.data.
  prior_year_labor_income` carries its exact label in the staged setup
  files, and every individual-file type and accuracy code its documented
  format label.
* The label searches behind the readers' scope statements: no person-
  level Social Security item in the 1994-2003 family files, a
  year-before-last Social Security item in the 2005-2015 family files
  only, and the individual file's odd-year earnings series (a finding the
  readers record, not a source they read).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from populace_dynamics.data import family, psid
from populace_dynamics.data import prior_year_labor_income as pyl
from populace_dynamics.data import social_security_receipt as ssr

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()
_FAMILY_WAVES = (
    1993,
    *ssr.FAMILY_TOTAL_WAVES,
    *ssr.YEAR_BEFORE_LAST_WAVES,
    *pyl._VARS,
    2017,
    2019,
    2021,
)

needs_real_psid = pytest.mark.skipif(
    not (REAL_DATA / "ind2023er").is_dir()
    or not all(
        (REAL_DATA / "family" / str(wave)).is_dir() for wave in _FAMILY_WAVES
    ),
    reason="staged PSID individual and family files not present",
)


def _family_labels(wave: int) -> dict[str, str]:
    sps, _ = family._family_paths(wave, REAL_DATA)
    return psid.parse_sps_labels(sps)


def _check(labels: dict[str, str], table: dict, wave: int) -> None:
    for var, label in table.values():
        family._verified(labels, var, label, wave)


@needs_real_psid
def test_every_individual_item_carries_its_label_and_codes():
    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", REAL_DATA)
    )
    expected = {}
    for wave in ssr.INDIVIDUAL_WAVES:
        for var, label in ssr.individual_variables(wave).values():
            expected[var] = label
    psid.verify_labels(labels, expected, context="Track M M3 labels")
    checked = ssr.verify_individual_codes(data_dir=REAL_DATA)
    assert set(checked) == set(ssr.INDIVIDUAL_WAVES)
    assert " ".join(labels[ssr.AMOUNT_2023[0]].split()) == ssr.AMOUNT_2023[1]


@needs_real_psid
@pytest.mark.parametrize("wave", ssr.YEAR_BEFORE_LAST_WAVES)
def test_year_before_last_labels(wave):
    _check(_family_labels(wave), ssr.year_before_last_variables(wave), wave)


@needs_real_psid
@pytest.mark.parametrize("wave", ssr.FAMILY_TOTAL_WAVES)
def test_family_total_labels(wave):
    _check(_family_labels(wave), ssr.family_total_variables(wave), wave)


@needs_real_psid
def test_the_1993_head_and_wife_labels():
    _check(_family_labels(1993), ssr._FAMILY_1993, 1993)


@needs_real_psid
@pytest.mark.parametrize("wave", tuple(pyl._VARS))
def test_prior_year_labor_income_labels(wave):
    table = pyl.prior_year_variables(wave)
    labels = _family_labels(wave)
    _check(labels, {"interview": table["interview"]}, wave)
    for role in pyl.ROLES:
        _check(labels, table[role], wave)


_SOCIAL_SECURITY = re.compile(r"SOC\s*SEC|SOCIAL SEC", re.IGNORECASE)
_YEAR_BEFORE_LAST = re.compile(r"BEFORE LAST|B4 LAST", re.IGNORECASE)


@needs_real_psid
@pytest.mark.parametrize("wave", ssr.FAMILY_TOTAL_WAVES)
def test_the_1994_2003_files_carry_no_person_level_social_security(wave):
    """Their Social Security labels name the family: a total, the
    whether-any-member item, and pension offset items (1999-2003)."""

    hits = [
        " ".join(label.split())
        for label in _family_labels(wave).values()
        if _SOCIAL_SECURITY.search(label)
    ]
    assert hits
    for label in hits:
        assert not re.search(r"\b(HD|HEAD|WF|WIFE|OFUM)\b", label), label


@needs_real_psid
@pytest.mark.parametrize("wave", (2003, *ssr.YEAR_BEFORE_LAST_WAVES, 2017))
def test_year_before_last_social_security_items_end_with_2015(wave):
    labels = _family_labels(wave)
    found = sorted(
        var
        for var, label in labels.items()
        if _SOCIAL_SECURITY.search(label) and _YEAR_BEFORE_LAST.search(label)
    )
    table = (
        ssr.year_before_last_variables(wave)
        if wave in ssr.YEAR_BEFORE_LAST_WAVES
        else {}
    )
    received = [var for key, (var, _) in table.items() if key == "received"]
    if wave in ssr.YEAR_BEFORE_LAST_TYPED_WAVES:
        # R20, R22 (two mentions), R23 (amount, time unit), R24 (months)
        assert len(found) == 17
        assert set(received) <= set(found)
    elif wave in ssr.YEAR_BEFORE_LAST_WAVES:
        assert found == received
    else:
        assert found == []


@needs_real_psid
def test_the_individual_file_carries_odd_year_earnings_the_readers_skip():
    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", REAL_DATA)
    )
    for var, label in pyl.INDIVIDUAL_FILE_ODD_YEAR_SERIES.values():
        assert " ".join(labels[var].split()) == label
