"""Staged-PSID checks of the row-U7 employer DC reader.

Skipped when the staged PSID family files under ``~/PolicyEngine/psid-data``
are absent.  They verify labels, field widths, code domains, the join to
the family file and the codebooks' routing; they compute no income
concept, annuity, threshold or poverty status, and they assert no amount
(only counts of records, as the specification's structural counts do).

The setup-file check is independent of the reader: it parses the SAS
(``.sas``) and Stata (``.do``) setup files with its own regular
expressions, never with :mod:`populace_dynamics.data.psid` (which the
reader uses on the ``.sps`` file), and compares every adjudicated
variable's label and column span with the reader's table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from populace_dynamics.data import employer_dc as ed
from populace_dynamics.data import family_income as fi

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()

needs_real_psid = pytest.mark.skipif(
    not all(
        (REAL_DATA / "family" / str(wave) / f"FAM{wave}ER.sas").is_file()
        for wave in ed.EMPLOYER_DC_WAVES
    ),
    reason="staged PSID family files 2005-2013 not present",
)


def _norm(text: str) -> str:
    return " ".join(text.split())


def _sas(wave: int) -> tuple[dict[str, str], dict[str, tuple[int, int]]]:
    text = (REAL_DATA / "family" / str(wave) / f"FAM{wave}ER.sas").read_text(
        encoding="latin-1"
    )
    labels = {
        name: _norm(label)
        for name, label in re.findall(
            r'^\s*(ER\d+)\s+LABEL="([^"]*)"', text, re.M
        )
    }
    spans = {
        name: (int(a), int(b))
        for name, a, b in re.findall(r"\b(ER\d+)\s+(\d+)\s*-\s*(\d+)", text)
    }
    return labels, spans


def _do(wave: int) -> tuple[dict[str, str], dict[str, tuple[int, int]]]:
    text = (REAL_DATA / "family" / str(wave) / f"FAM{wave}ER.do").read_text(
        encoding="latin-1"
    )
    labels = {
        name: _norm(label)
        for name, label in re.findall(
            r'^\s*label\s+variable\s+(ER\d+)\s+"([^"]*)"', text, re.M
        )
    }
    spans = {
        name: (int(a), int(b))
        for name, a, b in re.findall(r"\b(ER\d+)\s+(\d+)\s*-\s*(\d+)", text)
    }
    return labels, spans


@needs_real_psid
@pytest.mark.parametrize("wave", ed.EMPLOYER_DC_WAVES)
def test_the_tables_equal_the_sas_and_stata_setup_files(wave):
    """Differential: the reader's table against two setup files it never
    parses (labels and column widths)."""

    sas_labels, sas_spans = _sas(wave)
    do_labels, do_spans = _do(wave)
    for concept, (var, label) in ed.employer_dc_variables(wave).items():
        assert sas_labels[var] == _norm(label), (concept, var)
        assert do_labels[var] == _norm(label), (concept, var)
        assert sas_spans[var] == do_spans[var], (concept, var)
        start, end = sas_spans[var]
        if concept == "interview":
            continue
        kind = concept.rsplit("_", 1)[-1]
        width = end - start + 1
        if kind == "amount":
            part = concept.split("_")[-2]
            expected = ed.AMOUNT_WIDTHS[
                "current_amount" if part == "current" else f"{part}_amount"
            ]
        else:
            expected = 1
        assert width == expected, (concept, var, width)
        # the label is carried by this variable only
        holders = [n for n, text in sas_labels.items() if text == _norm(label)]
        assert holders == [var], (concept, holders)


@needs_real_psid
@pytest.mark.parametrize("wave", ed.EMPLOYER_DC_WAVES)
def test_labels_verify_on_the_staged_files(wave):
    frame = ed.read_employer_dc(wave, data_dir=REAL_DATA, nrows=200)
    assert set(ed.employer_dc_variables(wave)) <= set(frame.columns)
    assert set(ed.BALANCE_COLUMNS) <= set(frame.columns)
    assert (frame["wave"] == wave).all()


@needs_real_psid
@pytest.mark.parametrize("wave", ed.EMPLOYER_DC_WAVES)
def test_every_family_has_one_record_and_the_routing_holds(wave):
    """Every family-file interview has one pension-section record (the
    section is in the family file); the balances are non-negative; no
    record carries an account amount after a disposition that asks none,
    and no record carries a top code (found 2026-09-25; counts only)."""

    frame = ed.read_employer_dc(wave, data_dir=REAL_DATA)
    income = fi.read_family_income(wave, data_dir=REAL_DATA)
    assert sorted(frame["interview"]) == sorted(income["interview"])
    assert (frame["employer_dc"] >= 0).all()
    counts = ed.reconcile_employer_dc(frame, wave)
    assert counts["n_families"] == len(income)
    assert counts["dc_amount_disposition_off_route"] == 0
    assert counts["dc_amount_plan_type_inap"] == 0
    assert counts["families_with_top_coded_amount"] == 0
    # with P16/P86 routing the current-job item is off route in 2009 only
    assert counts["current_amount_without_account_plan"] == (
        2 if wave == 2009 else 0
    )
    assert counts["combo_amount_off_route"] == (1 if wave == 2009 else 0)
    assert counts["dc_amount_plan_type_na"] == 0
    # every wave carries account amounts under a plan of DK type, which the
    # codebooks route to the account items (U7 counts them), and under
    # formula and "both" plans, which they do not (U7 excludes them)
    assert counts["dc_amount_plan_type_dk"] > 0
    assert counts["dc_amount_plan_type_formula"] > 0
    assert counts["dc_amount_plan_type_both"] > 0
    # a plan carrying both a "both" amount (P49) and an account amount
    # (P65) is a "both" plan: excluding its P65 keeps one account from
    # being counted twice
    assert (
        0
        < counts["plans_with_combo_and_dc_amounts"]
        <= (counts["dc_amount_plan_type_both"])
    )


@needs_real_psid
def test_the_both_plan_duplicates_are_both_plans():
    """Every previous plan that carries a "both" amount and an account
    amount has plan type "both" (counts and match flags only)."""

    for wave in ed.EMPLOYER_DC_WAVES:
        frame = ed.read_employer_dc(wave, data_dir=REAL_DATA)
        both = ed.plan_type_codes(wave)["previous_both"]
        for person in ed.PERSONS:
            for plan in ed.PREVIOUS_PLANS:
                stem = f"{person}_prev{plan}"
                has = (frame[f"{stem}_combo_amount"] != 0) & (
                    frame[f"{stem}_dc_amount"] != 0
                )
                assert (frame.loc[has, f"{stem}_type"] == both).all(), (
                    wave,
                    stem,
                )
