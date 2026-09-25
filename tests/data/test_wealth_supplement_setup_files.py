"""The wealth-supplement tables against the staged setup files and codebooks.

An independent check of :mod:`populace_dynamics.data.family_income`'s
2005 and 2007 supplement tables (adjudicated 2026-09-25): it parses the
SAS (``.sas``) and Stata (``.do``) setup files and the supplement
codebooks with its own regular expressions, never with
:mod:`populace_dynamics.data.psid` (which the reader uses on the ``.sps``
file).  Skipped when the staged supplements under
``~/PolicyEngine/psid-data/wealth`` are absent; the codebook checks also
need ``pdftotext``.  It reads setup files and codebook text only: no data
value.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from populace_dynamics.data import family_income as fi

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()

needs_supplements = pytest.mark.skipif(
    not all(
        (REAL_DATA / "wealth" / str(wave) / f"WLTH{wave}.sas").is_file()
        for wave in fi.WEALTH_SUPPLEMENT_WAVES
    ),
    reason="staged PSID 2005 and 2007 wealth supplements not present",
)
_TRIPLE = re.compile(r"\b([A-Z][A-Z0-9]*)\s+(\d+)\s*-\s*(\d+)\b")


def _norm(text: str) -> str:
    return " ".join(text.split())


def _sas(wave: int) -> tuple[dict[str, str], list[tuple[str, int, int]]]:
    text = (REAL_DATA / "wealth" / str(wave) / f"WLTH{wave}.sas").read_text(
        encoding="ascii"
    )
    labels = {
        name: _norm(label)
        for name, label in re.findall(
            r'^\s*([A-Z][A-Z0-9]*)\s+LABEL="([^"]*)"', text, re.M
        )
    }
    block = re.search(r"INPUT\s*\n(.*?)\n\s*;", text, re.S).group(1)
    positions = [(n, int(a), int(b)) for n, a, b in _TRIPLE.findall(block)]
    return labels, positions


def _do(wave: int) -> tuple[dict[str, str], list[tuple[str, int, int]]]:
    text = (REAL_DATA / "wealth" / str(wave) / f"WLTH{wave}.do").read_text(
        encoding="ascii"
    )
    labels = {
        name: _norm(label)
        for name, label in re.findall(
            r'label variable\s+([A-Z][A-Z0-9]*)\s+"([^"]*)"', text
        )
    }
    block = re.search(r"infix\s*\n(.*?)\nusing", text, re.S).group(1)
    positions = [(n, int(a), int(b)) for n, a, b in _TRIPLE.findall(block)]
    return labels, positions


@needs_supplements
@pytest.mark.parametrize("wave", fi.WEALTH_SUPPLEMENT_WAVES)
def test_every_adjudicated_label_is_the_sas_and_stata_label(wave):
    sas_labels, sas_positions = _sas(wave)
    do_labels, do_positions = _do(wave)
    assert sas_labels == do_labels
    assert sas_positions == do_positions
    assert len(sas_labels) == 38
    table = fi.wealth_supplement_variables(wave)
    for concept, (var, label) in table.items():
        assert sas_labels[var] == _norm(label), (wave, concept)
    # each adjudicated variable's column span in the .sas INPUT equals the
    # one the reader's .sps parser returns
    from populace_dynamics.data import psid

    sps = (
        psid.parse_sps_layout(
            REAL_DATA / "wealth" / str(wave) / f"WLTH{wave}.sps"
        )
        .set_index("name")[["start", "end"]]
        .astype(int)
    )
    spans = {name: (a, b) for name, a, b in sas_positions}
    for var, _ in table.values():
        assert spans[var] == tuple(sps.loc[var]), (wave, var)


def _codebook(wave: int) -> str:
    return subprocess.run(
        [
            "pdftotext",
            "-layout",
            str(REAL_DATA / "wealth" / str(wave) / f"wlth{wave}_codebook.pdf"),
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@needs_supplements
@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="no pdftotext")
@pytest.mark.parametrize("wave", fi.WEALTH_SUPPLEMENT_WAVES)
def test_codebook_defines_the_family_id_and_wealth1_as_the_reader_does(wave):
    text = _codebook(wave)
    table = fi.wealth_supplement_variables(wave)
    headers = {
        name: _norm(label)
        for name, label in re.findall(
            r'^(S\d{3}A?)\s+"([^"]+)"\s+NUM\(\d+\.0\)', text, re.M
        )
    }
    for concept, (var, label) in table.items():
        assert headers[var] == _norm(label), (wave, concept)
    flat = _norm(text)
    interview = table["interview"][0]
    assert f"represent the {wave} interview number" in flat
    entry = flat.split(f'{interview} "{wave} FAMILY ID"')[1][:80]
    assert entry.split(" NUM(5.0) ")[1].startswith(f"{wave} Interview Number")
    listed = re.search(
        r"seven asset types \(([^)]*)\) net of debt value \((S\d{3})\)\. "
        r"Count",
        flat,
    )
    assert listed is not None
    assets = sorted(s.strip() for s in listed.group(1).split(","))
    assert assets == sorted(table[c][0] for c in fi.WEALTH1_ASSETS[wave])
    assert [listed.group(2)] == [table[c][0] for c in fi.WEALTH1_DEBTS[wave]]
    # every accuracy flag the reader reads is "Accuracy code for
    # imputation", 0 "Not Imputed" and 1 "Imputed"
    for concept, (var, _) in table.items():
        if not concept.endswith("_acc"):
            continue
        body = flat.split(f"{var} ")[1][:260]
        assert "Accuracy code for imputation" in body, (wave, var)
        assert "0 Not Imputed" in body and "1 Imputed" in body, (wave, var)
    # the release number: code 2 is "Release 2: March, 2011"
    assert "2 Release 2: March, 2011" in flat
