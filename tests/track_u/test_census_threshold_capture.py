"""The committed Census poverty-threshold capture and its real workbooks.

Artifact tier: reads the nine Census workbooks committed in
``data/external/census_poverty_thresholds`` (``thresh04.xlsx`` ...
``thresh12.xlsx``, staged 2026-09-24 under cos decision d194) and the
capture ``data/external/census_poverty_thresholds_2004_2012.json``.  It
checks the pins, re-runs the capture, compares the capture with the
workbook cells read without the parser or openpyxl, exercises the
parser's refusals on the real layouts and refuses tampered workbooks and
a tampered capture.  It computes no poverty status on PSID data.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import openpyxl
import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u import rows as track_u_rows
from populace_dynamics.uniform_cut_track_u import runner

ROOT = Path(__file__).resolve().parents[2]
WORKBOOKS = ROOT / "data" / "external" / "census_poverty_thresholds"
CAPTURE = (
    ROOT / "data" / "external" / "census_poverty_thresholds_2004_2012.json"
)
YEARS = tuple(range(2004, 2013))


def _script():
    path = ROOT / "scripts" / "capture_track_u_parameters.py"
    spec = importlib.util.spec_from_file_location("capture_track_u", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script():
    return _script()


@pytest.fixture(scope="module")
def capture():
    return json.loads(CAPTURE.read_text())


def _name(year: int) -> str:
    return f"thresh{year % 100:02d}.xlsx"


def _real_rows(script, year: int) -> list[list]:
    return script.read_workbook_rows(WORKBOOKS / _name(year))[1]


# -------------------------------------------------------------------------
# Pins and reproduction
# -------------------------------------------------------------------------
def test_committed_workbooks_match_their_pins(script):
    assert script.CENSUS_WORKBOOK_DIR == WORKBOOKS
    assert (
        sorted(p.name for p in WORKBOOKS.glob("*.xlsx"))
        == sorted(script.CENSUS_WORKBOOK_SHA256)
        == [_name(year) for year in YEARS]
    )
    provenance = (WORKBOOKS / "provenance.md").read_text()
    for name, pin in script.CENSUS_WORKBOOK_SHA256.items():
        digest = hashlib.sha256((WORKBOOKS / name).read_bytes()).hexdigest()
        assert digest == pin, name
        assert f"| `{name}` |" in provenance and f"`{pin}`" in provenance


def test_capture_matches_the_pin_the_registered_run_checks():
    assert ap.THRESHOLDS_PATH == CAPTURE
    digest = hashlib.sha256(CAPTURE.read_bytes()).hexdigest()
    assert digest == ap.THRESHOLDS_SHA256
    thresholds = ap.load_poverty_thresholds()
    assert thresholds.provenance == {
        "kind": "census_capture",
        "sha256": ap.THRESHOLDS_SHA256,
    }
    assert sorted(thresholds.weighted_average) == list(YEARS)
    assert sorted(thresholds.matrix) == list(YEARS)
    # the registered run's parameter check accepts exactly this capture
    params = runner.committed_parameters(thresholds)
    runner._check_parameters(params, ap.REGISTERED_REAL)


def test_the_capture_reproduces_byte_for_byte(script):
    capture = script.build_threshold_capture(WORKBOOKS)
    text = json.dumps(capture, indent=2) + "\n"
    assert text == CAPTURE.read_text(encoding="utf-8")


def test_capture_records_each_workbook(capture, script):
    assert capture["schema_version"] == ap.THRESHOLDS_SCHEMA_VERSION
    assert capture["years"] == [YEARS[0], YEARS[-1]]
    assert capture["checks"]["workbook_sha256"].startswith("pinned")
    for year in YEARS:
        source = capture["sources"][str(year)]
        name = _name(year)
        assert source["file"] == name
        assert source["url"] == (
            "https://www2.census.gov/programs-surveys/cps/tables/"
            f"time-series/historical-poverty-thresholds/{name}"
        )
        assert source["sha256"] == script.CENSUS_WORKBOOK_SHA256[name]
        assert source["bytes"] == (WORKBOOKS / name).stat().st_size
        assert source["title"] == (
            f"Poverty Thresholds for {year} by Size of Family and Number "
            "of Related Children Under 18 Years"
        )
        assert source["cps_asec_year"] == year + 1


def test_capture_covers_every_income_year_the_rows_read(capture):
    """The rows read the even income years 2004-2012 (PSID waves
    2005-2013); the capture covers 2004-2012, as the SSI capture does."""

    read = {
        income_year
        for row in track_u_rows.REGISTERED_ROWS.values()
        for _, _, income_year, _ in age67.observation_plan(row.age67_spec())
    }
    assert read == {2004, 2006, 2008, 2010, 2012}
    assert read <= {int(year) for year in capture["weighted_average"]}
    ssi_years = sorted(ap.load_ssi_parameters().fbr_individual_monthly)
    assert capture["years"] == [ssi_years[0], ssi_years[-1]]


def test_primary_and_matrix_lookups_on_the_capture():
    thresholds = ap.load_poverty_thresholds()
    primary = "census_weighted_average_65plus"
    assert ap.threshold_for(thresholds, 2004, 1, 0, primary) == (
        9060.0,
        "one_65_plus",
    )
    assert ap.threshold_for(thresholds, 2012, 2, 0, primary) == (
        13892.0,
        "two_65_plus",
    )
    assert ap.threshold_for(thresholds, 2008, 11, 4, primary) == (
        44346.0,
        "nine_plus",
    )
    assert ap.threshold_for(
        thresholds, 2010, 2, 3, "census_matrix_65plus"
    ) == (
        14973.0,
        "two_65_plus:1",
    )


# -------------------------------------------------------------------------
# The capture against the workbook cells, read without the parser
# -------------------------------------------------------------------------
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
#: The shared layout's fixed rows: row number -> (printed label, key).
_FIXED_ROWS = {
    8: ("One person (unrelated individual):", "one"),
    9: ("Under 65 years......", "one_under_65"),
    10: ("65 years and over......", "one_65_plus"),
    12: ("Two people:", "two"),
    13: ("Householder under 65 years", "two_under_65"),
    14: ("Householder 65 years and over......", "two_65_plus"),
    16: ("Three people", "three"),
    17: ("Four people", "four"),
    18: ("Five people", "five"),
    19: ("Six people", "six"),
    20: ("Seven people", "seven"),
    21: ("Eight people", "eight"),
    22: ("Nine people or more", "nine_plus"),
}


def _xml_cells(path: Path) -> dict[str, object]:
    """Cell values of the one worksheet, straight from the xlsx XML."""

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        sheets = [n for n in names if n.startswith("xl/worksheets/sheet")]
        assert len(sheets) == 1
        strings = [
            "".join(t.text or "" for t in item.iter(f"{_MAIN}t"))
            for item in ET.fromstring(
                archive.read("xl/sharedStrings.xml")
            ).iter(f"{_MAIN}si")
        ]
        sheet = ET.fromstring(archive.read(sheets[0]))
    cells: dict[str, object] = {}
    for cell in sheet.iter(f"{_MAIN}c"):
        assert cell.find(f"{_MAIN}f") is None, "formula cell"
        value = cell.find(f"{_MAIN}v")
        if value is None:
            continue
        if cell.attrib.get("t") == "s":
            cells[cell.attrib["r"]] = strings[int(value.text)]
        else:
            cells[cell.attrib["r"]] = float(value.text)
    return cells


@pytest.mark.parametrize("year", YEARS)
def test_capture_equals_the_workbook_cells(capture, year):
    cells = _xml_cells(WORKBOOKS / _name(year))
    assert cells["A2"].startswith(f"Poverty Thresholds for {year} by")
    key = str(year)
    # the two cells the primary reads for the Report's 65-and-over rule
    assert cells["A10"] == "65 years and over......"
    assert cells["B10"] == capture["weighted_average"][key]["one_65_plus"]
    assert cells["A14"] == "Householder 65 years and over......"
    assert cells["B14"] == capture["weighted_average"][key]["two_65_plus"]
    compared = 0
    for row, (label, name) in _FIXED_ROWS.items():
        assert cells[f"A{row}"] == label
        if name in ("one", "two"):
            expected = capture["weighted_average_all_ages"][key][name]
            assert cells[f"B{row}"] == expected
            compared += 1
            continue
        assert cells[f"B{row}"] == capture["weighted_average"][key][name]
        matrix = capture["matrix"][key][name]
        for k, value in matrix.items():
            assert cells[f"{'CDEFGHIJK'[int(k)]}{row}"] == value
        compared += 1 + len(matrix)
        # no numeric cell beyond the row's children columns
        for column in "CDEFGHIJK"[len(matrix) :]:
            assert not isinstance(cells.get(f"{column}{row}"), float)
    assert compared == 61


# -------------------------------------------------------------------------
# The parser on the real layouts
# -------------------------------------------------------------------------
@pytest.mark.parametrize("year", YEARS)
def test_parser_reads_every_real_layout(script, capture, year):
    parsed = script.parse_threshold_rows(_real_rows(script, year), year)
    key = str(year)
    assert parsed["weighted_average"] == capture["weighted_average"][key]
    assert parsed["all_ages"] == capture["weighted_average_all_ages"][key]
    assert {
        row: {str(k): v for k, v in cells.items()}
        for row, cells in parsed["matrix"].items()
    } == capture["matrix"][key]
    assert parsed["source_line"] == f"Source: U.S. Census Bureau, {year + 1}."


def test_whitespace_cells_in_the_real_layouts_count_as_blank(script):
    """thresh07 fills the unused cells of its rows with spaces, and
    thresh11 and thresh12 each have one; the parser treats them as
    blank."""

    for year, cell in ((2007, (7, 3)), (2011, (14, 1)), (2012, (11, 2))):
        rows = _real_rows(script, year)
        value = rows[cell[0]][cell[1]]
        assert isinstance(value, str) and not value.strip()
        script.parse_threshold_rows(rows, year)


def _set(rows, row, column, value):
    rows = copy.deepcopy(rows)
    rows[row][column] = value
    return rows


#: Edits of the real 2008 layout the parser must refuse (0-based row and
#: column; row 9 is "65 years and over", row 13 "Householder 65 years and
#: over", row 16 "Four people").
_REFUSALS = [
    (
        "title of another year",
        lambda r: _set(r, 1, 0, r[1][0].replace("2008", "2007")),
        "the title names 2007",
    ),
    ("no units line", lambda r: _set(r, 2, 0, None), "In dollars"),
    (
        "weighted column relabelled",
        lambda r: _set(r, 4, 1, "Median"),
        "Weighted average",
    ),
    (
        "children headers swapped",
        lambda r: _set(_set(r, 5, 3, "Two"), 5, 4, "One"),
        "children headers",
    ),
    ("rows swapped", lambda r: [*r[:12], r[13], r[12], *r[14:]], "row labels"),
    ("duplicated row", lambda r: [*r[:17], r[16], *r[18:]], "row labels"),
    (
        "value one column right",
        lambda r: _set(_set(r, 9, 2, None), 9, 3, 10326),
        "children columns",
    ),
    ("text in a matrix cell", lambda r: _set(r, 16, 3, "n/a"), "not a number"),
    (
        "formula in a matrix cell",
        lambda r: _set(r, 16, 3, "=C17+1"),
        "not a number",
    ),
    ("fractional dollars", lambda r: _set(r, 9, 1, 10326.5), "whole dollar"),
    ("negative threshold", lambda r: _set(r, 16, 2, -22207), "whole dollar"),
    ("value in a spacer row", lambda r: _set(r, 10, 4, 1), "unlabelled"),
    (
        "value above the header",
        lambda r: _set(r, 2, 5, 2008),
        "above the header",
    ),
    ("value below the note", lambda r: [*r, [None, 1]], "below the source"),
    (
        "source of another vintage",
        lambda r: _set(r, 22, 0, "Source: U.S. Census Bureau, 2008."),
        "Bureau, 2009",
    ),
    (
        "note of another vintage",
        lambda r: _set(r, 23, 0, r[23][0].replace("2009", "2010")),
        "2009 CPS ASEC",
    ),
    (
        "65-and-over weighted average changed",
        lambda r: _set(r, 9, 1, 10327),
        "outside its matrix cells",
    ),
    (
        "age rows' values swapped",
        lambda r: _set(
            _set(_set(r, 13, 1, 14489), 13, 2, 14417), 13, 3, 14840
        ),
        "not below under-65",
    ),
    # regression (independent review, 2026-09-24): any text above the
    # header passed, including a formula, an extra line, a changed or
    # missing caption, and the title or units in another column or order
    (
        "text line added above the header",
        lambda r: _set(r, 3, 0, "Preliminary estimates"),
        "not exactly the caption",
    ),
    (
        "caption replaced",
        lambda r: _set(r, 0, 0, "Table with row headings in column A."),
        "not exactly the caption",
    ),
    ("caption removed", lambda r: _set(r, 0, 0, None), "not exactly"),
    (
        "units line above the title",
        lambda r: _set(_set(r, 1, 0, "(In dollars)"), 2, 0, r[1][0]),
        "not exactly the caption",
    ),
    (
        "formula above the header",
        lambda r: _set(r, 2, 2, "=SUM(B8:B22)"),
        "outside column A",
    ),
    (
        "title moved to column D",
        lambda r: _set(_set(r, 1, 0, None), 1, 3, r[1][0]),
        "outside column A",
    ),
    (
        "note with another sentence",
        lambda r: _set(r, 23, 0, r[23][0] + " Thresholds were revised."),
        "note says more",
    ),
]


@pytest.mark.parametrize(
    "edit, message",
    [(e, m) for _, e, m in _REFUSALS],
    ids=[name for name, _, _ in _REFUSALS],
)
def test_parser_refuses_edits_of_a_real_layout(script, edit, message):
    rows = _real_rows(script, 2008)
    script.parse_threshold_rows(rows, 2008)  # the unedited layout parses
    with pytest.raises(ValueError, match=message):
        script.parse_threshold_rows(edit(rows), 2008)


def test_the_2009_cpi_sentences_pass_only_in_the_2009_note(script):
    """The 2009 note adds two CPI-U sentences naming 2009 and 2008; the
    note may carry them for its own year only."""

    rows_2009 = _real_rows(script, 2009)
    note_2009 = rows_2009[23][0]
    assert "CPI-U for 2009 was lower" in note_2009
    script.parse_threshold_rows(rows_2009, 2009)
    first_sentence = note_2009[: note_2009.index("(CPS ASEC).") + 11]
    tail = note_2009[len(first_sentence) :]
    rows_2008 = _real_rows(script, 2008)
    note_2008 = rows_2008[23][0]
    with pytest.raises(ValueError, match="note says more"):
        script.parse_threshold_rows(
            _set(rows_2008, 23, 0, note_2008 + tail), 2008
        )
    with pytest.raises(ValueError, match="note says more"):
        script.parse_threshold_rows(
            _set(
                rows_2009, 23, 0, first_sentence + tail.replace("2008", "2007")
            ),
            2009,
        )


def test_one_misread_cell_breaks_the_cross_year_check(script):
    earlier = script.parse_threshold_rows(_real_rows(script, 2007), 2007)
    later = script.parse_threshold_rows(_real_rows(script, 2008), 2008)
    ratio = script.check_matrix_moves_together(
        earlier["matrix"], later["matrix"], 2008
    )
    assert ratio == pytest.approx(1.0384, abs=1e-4)
    moved = copy.deepcopy(later["matrix"])
    moved["four"][0] += 50  # within its row's range, so the year passes
    with pytest.raises(ValueError, match="common ratio"):
        script.check_matrix_moves_together(earlier["matrix"], moved, 2008)


# -------------------------------------------------------------------------
# Tampering
# -------------------------------------------------------------------------
@pytest.fixture
def staged_copy(tmp_path):
    for path in WORKBOOKS.glob("thresh*.xlsx"):
        shutil.copy2(path, tmp_path / path.name)
    return tmp_path


def _edit_workbook(path: Path, cell: str, delta: int) -> None:
    workbook = openpyxl.load_workbook(path)
    sheet = workbook.worksheets[0]
    sheet[cell] = sheet[cell].value + delta
    workbook.save(path)


def test_a_tampered_workbook_is_refused_before_parsing(script, staged_copy):
    script.build_threshold_capture(staged_copy)  # the copies pass
    _edit_workbook(staged_copy / "thresh08.xlsx", "B10", 1)
    with pytest.raises(ValueError, match="not the captured Census file"):
        script.build_threshold_capture(staged_copy)
    # the parser refuses the same edit on its own (the size-1 weighted
    # average must equal its single cell)
    with pytest.raises(ValueError, match="outside its matrix cells"):
        script.build_threshold_capture(staged_copy, expected_sha256=None)


def test_a_tampered_matrix_cell_is_refused(script, staged_copy):
    _edit_workbook(staged_copy / "thresh10.xlsx", "C17", 50)
    with pytest.raises(ValueError, match="not the captured Census file"):
        script.build_threshold_capture(staged_copy)
    with pytest.raises(ValueError, match="common ratio"):
        script.build_threshold_capture(staged_copy, expected_sha256=None)


def test_a_missing_workbook_is_refused(script, staged_copy):
    (staged_copy / "thresh12.xlsx").unlink()
    with pytest.raises(FileNotFoundError, match="thresh12"):
        script.build_threshold_capture(staged_copy)


def test_a_tampered_capture_is_refused(tmp_path, capture):
    edited = copy.deepcopy(capture)
    edited["weighted_average"]["2008"]["one_65_plus"] += 1
    path = tmp_path / "census_poverty_thresholds_2004_2012.json"
    path.write_text(json.dumps(edited, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ap.AdjustedPovertyError, match="sha256"):
        ap.load_poverty_thresholds(path)
    with pytest.raises(ap.ThresholdsNotCapturedError):
        ap.load_poverty_thresholds(tmp_path / "missing.json")
