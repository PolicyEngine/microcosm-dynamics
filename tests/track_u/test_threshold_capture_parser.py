"""The Census threshold capture parser, exercised on INVENTED workbooks.

These workbooks are INVENTED in the layout of the real Census files
(``thresh04.xlsx`` ... ``thresh12.xlsx``; checked on the real files in
``test_census_threshold_capture.py``): the real files' caption, the
title naming the year, "(In dollars)", the two header rows, the thirteen
labelled rows, and the source and note naming the next year.  Their
worksheet is named INVENTED.  Every threshold below is made up; none is
a Census value.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import openpyxl
import pytest

from populace_dynamics.estimates import adjusted_poverty as ap

ROOT = Path(__file__).resolve().parents[2]


def _script():
    path = ROOT / "scripts" / "capture_track_u_parameters.py"
    spec = importlib.util.spec_from_file_location("capture_track_u", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHILD_HEADERS = [
    " None",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight or more",
]
#: INVENTED first-column (no children) cells for 2004; each further child
#: subtracts 10 and each later year adds 2 percent (rounded).
_BASE = {
    "Under 65 years......": 1100,
    "65 years and over......": 1000,
    "Householder under 65 years": 1400,
    "Householder 65 years and over......": 1300,
    "Three people": 1900,
    "Four people": 2200,
    "Five people": 2500,
    "Six people": 2800,
    "Seven people": 3100,
    "Eight people": 3400,
    "Nine people or more": 4000,
}
_COLUMNS = {
    "Under 65 years......": 1,
    "65 years and over......": 1,
    "Householder under 65 years": 2,
    "Householder 65 years and over......": 2,
    "Three people": 3,
    "Four people": 4,
    "Five people": 5,
    "Six people": 6,
    "Seven people": 7,
    "Eight people": 8,
    "Nine people or more": 9,
}


def _cells(label: str, year: int) -> list[int]:
    scale = 1.02 ** (year - 2004)
    return [
        round((_BASE[label] - 10 * k) * scale) for k in range(_COLUMNS[label])
    ]


def _invented_rows(year: int) -> list[list]:
    """INVENTED threshold table in the real layout (not Census values)."""

    def row(label: str) -> list:
        cells = _cells(label, year)
        # the weighted average: the row's lowest cell (within its range)
        return [label, min(cells), *cells]

    def all_ages(label: str, young: str, old: str) -> list:
        between = (_cells(young, year)[0] + _cells(old, year)[0]) // 2
        return [label, between]

    rows = [
        # the parser requires the real workbooks' caption above the title;
        # the sheet is named INVENTED (``_write``) and every value is made up
        [
            "Table with row headings in column A and column headings in "
            "rows 5 to 6."
        ],
        [
            f"Poverty Thresholds for {year} by Size of Family and Number "
            "of Related Children Under 18 Years"
        ],
        ["(In dollars)"],
        [],
        [
            "Size of family unit",
            "Weighted\naverage\nthresholds",
            "Related children under 18 years",
        ],
        [None, None, *CHILD_HEADERS],
        [],
        all_ages(
            "One person (unrelated individual):",
            "Under 65 years......",
            "65 years and over......",
        ),
        row("Under 65 years......"),
        row("65 years and over......"),
        [],
        all_ages(
            "Two people:",
            "Householder under 65 years",
            "Householder 65 years and over......",
        ),
        row("Householder under 65 years"),
        row("Householder 65 years and over......"),
        [],
        *(
            row(label)
            for label in (
                "Three people",
                "Four people",
                "Five people",
                "Six people",
                "Seven people",
                "Eight people",
                "Nine people or more",
            )
        ),
        [f"Source: U.S. Census Bureau, {year + 1}."],
        [
            "Note: The source of the weighted average thresholds is the "
            f"{year + 1} Current Population Survey Annual Social and "
            "Economic Supplement (CPS ASEC)."
        ],
    ]
    return rows


def _write(path: Path, rows: list[list]) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "INVENTED"
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def test_parser_reads_an_invented_table():
    module = _script()
    parsed = module.parse_threshold_rows(_invented_rows(2004), 2004)
    weighted = parsed["weighted_average"]
    assert weighted["one_65_plus"] == 1000
    assert weighted["two_under_65"] == 1390
    assert weighted["three"] == 1880
    assert weighted["nine_plus"] == 3920
    assert parsed["all_ages"] == {"one": 1050, "two": 1350}
    assert parsed["matrix"]["four"] == {0: 2200, 1: 2190, 2: 2180, 3: 2170}
    assert sorted(parsed["matrix"]["nine_plus"]) == list(range(9))
    assert parsed["matrix"]["two_65_plus"] == {0: 1300, 1: 1290}
    assert parsed["source_line"] == "Source: U.S. Census Bureau, 2005."
    assert parsed["cps_asec_year"] == 2005


def test_parser_refuses_another_years_table():
    module = _script()
    with pytest.raises(ValueError, match="the title names 2010"):
        module.parse_threshold_rows(_invented_rows(2010), 2011)


def test_parser_refuses_a_missing_row():
    module = _script()
    rows = [
        row
        for row in _invented_rows(2011)
        if not (row and str(row[0]).startswith("Five"))
    ]
    with pytest.raises(ValueError, match="row labels"):
        module.parse_threshold_rows(rows, 2011)


def test_parser_refuses_a_nonmonotone_table():
    module = _script()
    rows = _invented_rows(2010)
    for row in rows:
        if row and str(row[0]).startswith("Four"):
            row[1:] = [100, 100, 100, 100, 100]
    with pytest.raises(ValueError, match="increasing"):
        module.parse_threshold_rows(rows, 2010)


def test_capture_round_trips_through_the_loader(tmp_path):
    module = _script()
    for year in module.YEARS:
        _write(tmp_path / f"thresh{year % 100:02d}.xlsx", _invented_rows(year))
    capture = module.build_threshold_capture(tmp_path, expected_sha256=None)
    assert capture["sources"]["2004"]["url"].endswith("thresh04.xlsx")
    assert capture["checks"]["workbook_sha256"].startswith("not pinned")
    assert capture["checks"]["matrix_ratio_by_year_pair"]["2011-2012"] == (
        pytest.approx(1.02, abs=1e-3)
    )
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(capture, indent=2) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    thresholds = ap.load_poverty_thresholds(path, expected_sha256=digest)
    assert ap.threshold_for(
        thresholds, 2012, 2, 0, "census_weighted_average_65plus"
    ) == (
        float(min(_cells("Householder 65 years and over......", 2012))),
        "two_65_plus",
    )
    with pytest.raises(ap.AdjustedPovertyError, match="sha256"):
        ap.load_poverty_thresholds(path, expected_sha256="0" * 64)


def test_the_pinned_capture_refuses_invented_workbooks(tmp_path):
    """The default (the command line's) pins the nine Census files."""

    module = _script()
    for year in module.YEARS:
        _write(tmp_path / f"thresh{year % 100:02d}.xlsx", _invented_rows(year))
    with pytest.raises(ValueError, match="not the captured Census file"):
        module.build_threshold_capture(tmp_path)
