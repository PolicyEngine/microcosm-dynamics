"""Track M's Census thresholds before 2003 (plan item M2; cos d279).

M4's structural count shows the in-window records need the threshold
years 1982, 1986, 1988, 1989, 1991, 1992 and 1994-2002 (M1 specification,
sections 4, 7 and 10).  Their fifteen Census workbooks are committed in
``data/external/census_poverty_thresholds`` and captured with 2003-2022 in
``census_poverty_thresholds_1982_2022.json``.  This module checks:

* the parser on each layout before 2003 (the March CPS and CPS ADS notes,
  2001's "persons" rows, the revision lines of 1982 and 2000) and its
  refusals of those departures in any other year;
* a differential: every captured value equals the workbook cell read by
  its row label from the sheet XML, with code that shares nothing with the
  capture script or openpyxl;
* a cross-check against Census's own HTML edition of historical poverty
  Table 1 (1959-2006, page of September 29, 2009), an independent
  publication of the weighted averages and of the annual CPI-U;
* the invariants: every threshold positive; the one-person (and
  two-person) 65-and-over threshold below the under-65 one every year;
  every threshold rising between captured years except 2008-2009, the one
  year whose own note says the CPI-U fell; every year-pair matrix ratio
  equal to the CPI-U ratio within rounding; the G8 row equal to its single
  matrix cell (2022 excepted, $10 rounding);
* Hypothesis properties of the parser on INVENTED tables in every layout,
  of the cross-year check, of the captured-years text and of the
  threshold-year check.

Census thresholds are published public parameters, not PSID data.  Every
table the Hypothesis tests build is INVENTED.  No PSID file is read.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from populace_dynamics.min_benefit_track_m import rules, thresholds

ROOT = Path(__file__).resolve().parents[2]
WORKBOOKS = ROOT / "data" / "external" / "census_poverty_thresholds"
CAPTURE = (
    ROOT / "data" / "external" / "census_poverty_thresholds_1982_2022.json"
)
TABLE1_HTML = WORKBOOKS / "crosscheck" / "hstpov1-20100209011620.html"
TABLE1_SHA256 = (
    "d219cb20f4a6978ffabf265e4feabe1ad02b5446705c5cc1bda73cb9c91f038f"
)
BEFORE_2003 = (1982, 1986, 1988, 1989, 1991, 1992, *range(1994, 2003))
YEARS = (*BEFORE_2003, *range(2003, 2023))
NOT_CAPTURED = (1983, 1984, 1985, 1987, 1990, 1993)
REVISION_LINES = {
    1982: "Revised on 4/19/2022 due to rounding issues.",
    2000: "Revised on 2/1/2023 due to a formatting error.",
}


def _script():
    path = ROOT / "scripts" / "capture_track_u_parameters.py"
    spec = importlib.util.spec_from_file_location("capture_before_2003", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT = _script()


@pytest.fixture(scope="module")
def capture():
    return json.loads(CAPTURE.read_text())


def _name(year: int) -> str:
    return f"thresh{year % 100:02d}.xlsx"


def _survey(year: int) -> str:
    if year >= 2002:
        return "cps_asec"
    return "cps_ads" if year == 2001 else "march_cps"


def _rows(year: int) -> list[list]:
    return SCRIPT.read_workbook_rows(WORKBOOKS / _name(year), year)[1]


def _set(rows, row, column, value):
    rows = copy.deepcopy(rows)
    while len(rows) <= row:
        rows.append([])
    while len(rows[row]) <= column:
        rows[row].append(None)
    rows[row][column] = value
    return rows


# -------------------------------------------------------------------------
# The years and their pins
# -------------------------------------------------------------------------
def test_the_captured_years_are_m4s_and_2003_to_2022():
    assert thresholds.TRACK_M_THRESHOLD_YEARS_BEFORE_2003 == BEFORE_2003
    assert thresholds.TRACK_M_THRESHOLD_YEARS == YEARS
    assert sorted(
        set(range(1982, 2023)) - set(thresholds.TRACK_M_THRESHOLD_YEARS)
    ) == list(NOT_CAPTURED)
    for year in BEFORE_2003:
        assert _name(year) in SCRIPT.CENSUS_WORKBOOK_SHA256
        digest = hashlib.sha256((WORKBOOKS / _name(year)).read_bytes())
        assert digest.hexdigest() == SCRIPT.CENSUS_WORKBOOK_SHA256[_name(year)]
    assert sorted(SCRIPT.CENSUS_WORKBOOK_SHA256) == sorted(
        _name(year) for year in YEARS
    )
    assert sorted(p.name for p in WORKBOOKS.glob("thresh*.xlsx")) == sorted(
        _name(year) for year in YEARS
    )


def test_thresh95s_internet_archive_provenance_is_carried(capture):
    source = capture["sources"]["1995"]
    retrieval = source["retrieval"]
    assert retrieval == SCRIPT.ARCHIVE_RETRIEVALS["thresh95.xlsx"]
    assert retrieval["retrieved_from"] == "internet_archive"
    assert retrieval["captures_identical"] is True
    urls = [item["url"] for item in retrieval["archive_captures"]]
    assert urls == [
        "http://web.archive.org/web/20230226205734id_/" + source["url"],
        "http://web.archive.org/web/20260820215832id_/" + source["url"],
    ]
    assert [c["cdx_sha1_base32"] for c in retrieval["archive_captures"]] == [
        "ARBZSSCAOHTKTGHH6INRSDDWBDJVFVAB",
        "ZCDVY76QW2OH6NA6RLKWJPMJCNTMZIAQ",
    ]
    # the file itself is the 2026 capture: its SHA-1 is the CDX digest
    import base64

    sha1 = hashlib.sha1((WORKBOOKS / "thresh95.xlsx").read_bytes()).digest()
    assert (
        base64.b32encode(sha1).decode() == "ZCDVY76QW2OH6NA6RLKWJPMJCNTMZIAQ"
    )
    assert source["sha256"] == (
        "32bb678f3e0847b71c96c7c3c2b2ca8151a5c82307466df2807e9438ab2138f8"
    )
    provenance = " ".join((WORKBOOKS / "provenance.md").read_text().split())
    for text in (
        "Request Rejected",
        "20230226205734id_",
        "20260820215832id_",
        "ZCDVY76QW2OH6NA6RLKWJPMJCNTMZIAQ",
        "ARBZSSCAOHTKTGHH6INRSDDWBDJVFVAB",
    ):
        assert text in provenance, text
    for year in YEARS:
        if year != 1995:
            assert "retrieval" not in capture["sources"][str(year)], year


# -------------------------------------------------------------------------
# The parser on each layout before 2003
# -------------------------------------------------------------------------
@pytest.mark.parametrize("year", BEFORE_2003)
def test_the_parser_reads_each_layout_before_2003(capture, year):
    parsed = SCRIPT.parse_threshold_rows(_rows(year), year)
    key = str(year)
    assert parsed["weighted_average"] == capture["weighted_average"][key]
    assert parsed["all_ages"] == capture["weighted_average_all_ages"][key]
    assert {
        row: {str(k): v for k, v in cells.items()}
        for row, cells in parsed["matrix"].items()
    } == capture["matrix"][key]
    assert parsed["survey"] == _survey(year)
    assert parsed["survey_year"] == year + 1
    assert ("cps_asec_year" in parsed) == (year >= 2002)
    assert parsed["revision_line"] == REVISION_LINES.get(year)
    assert parsed["source_line"] == f"Source: U.S. Census Bureau, {year + 1}."
    assert parsed["title"] == (
        f"Poverty Thresholds for {year} by Size of Family and Number of "
        "Related Children Under 18 Years"
    )


def test_the_layout_tables_name_exactly_the_inspected_years():
    assert SCRIPT.NOTE_SURVEY_BEFORE_2002 == {
        year: _survey(year) for year in BEFORE_2003 if year < 2002
    }
    assert SCRIPT.PERSONS_ROW_LABEL_YEARS == frozenset({2001})
    assert SCRIPT.REVISION_LINES == REVISION_LINES
    for year in YEARS:
        assert SCRIPT.note_survey(year) == _survey(year)
    for year in (1959, 1981, *NOT_CAPTURED):
        with pytest.raises(ValueError, match="no inspected layout"):
            SCRIPT.note_survey(year)
    assert SCRIPT.row_labels(2001)[3] == "two persons"
    assert SCRIPT.row_labels(2001)[-1] == "nine persons or more"
    assert SCRIPT.row_labels(2001)[:3] == SCRIPT.row_labels(2000)[:3]
    assert SCRIPT.row_labels(2001)[4:6] == SCRIPT.row_labels(2000)[4:6]


#: Edits the parser must refuse: (name, year, edit, message).  Row 23 is
#: the note, row 24 1982's and 2000's revision line; rows 11 and 15-21
#: are the size rows "Two ..." and "Three ..." to "Nine ... or more".
_REFUSALS = [
    (
        "a March CPS year's note naming the CPS ASEC",
        1995,
        lambda r: _set(
            r,
            23,
            0,
            "Note: The source of the weighted average thresholds is the "
            "1996 Current Population Survey Annual Social and Economic "
            "Supplement (CPS ASEC).",
        ),
        "does not name the 1996 March CPS",
    ),
    (
        "a CPS ASEC year's note naming the March CPS",
        2005,
        lambda r: _set(
            r,
            23,
            0,
            "Note: The source of the weighted average thresholds is the "
            "March 2006 Current Population Survey (CPS).",
        ),
        "does not name the 2006 CPS ASEC",
    ),
    (
        "2001's note naming the March CPS",
        2001,
        lambda r: _set(
            r,
            23,
            0,
            "Note: The source of the weighted average thresholds is the "
            "March 2002 Current Population Survey (CPS).",
        ),
        "does not name the 2002 CPS ADS",
    ),
    (
        "a March CPS note of another vintage",
        1989,
        lambda r: _set(r, 23, 0, r[23][0].replace("1990", "1989")),
        "does not name the 1990 March CPS",
    ),
    (
        "2001's size rows saying people",
        2001,
        lambda r: _set(r, 11, 0, "Two people:"),
        "row labels",
    ),
    (
        "another year's size rows saying persons",
        1999,
        lambda r: _set(r, 16, 0, "Four persons"),
        "row labels",
    ),
    (
        "1982 without its revision line",
        1982,
        lambda r: _set(r, 24, 0, None),
        "expected the revision line",
    ),
    (
        "1982 with another revision line",
        1982,
        lambda r: _set(
            r, 24, 0, "Revised on 4/19/2022 due to a formatting error."
        ),
        "expected the revision line",
    ),
    (
        "2000's revision line in 1999",
        1999,
        lambda r: _set(r, 24, 0, REVISION_LINES[2000]),
        "below the source",
    ),
    (
        "a value below 1982's revision line",
        1982,
        lambda r: _set(r, 25, 0, "Preliminary"),
        "below the source",
    ),
    (
        "a value beside 2000's revision line",
        2000,
        lambda r: _set(r, 24, 3, 1),
        "below the source",
    ),
    (
        "the 65-and-over row above the under-65 row (1994)",
        1994,
        lambda r: _set(_set(r, 9, 1, 7711), 9, 2, 7711),
        "not below under-65",
    ),
]


@pytest.mark.parametrize(
    "year, edit, message",
    [(y, e, m) for _, y, e, m in _REFUSALS],
    ids=[name for name, _, _, _ in _REFUSALS],
)
def test_the_parser_refuses_departures_outside_their_years(
    year, edit, message
):
    rows = _rows(year)
    SCRIPT.parse_threshold_rows(rows, year)  # the unedited layout parses
    with pytest.raises(ValueError, match=message):
        SCRIPT.parse_threshold_rows(edit(rows), year)


def test_a_year_without_an_inspected_layout_is_refused():
    """1987's table (were it the 1986 layout relabelled) has no inspected
    layout, so the parser refuses it rather than guess its note."""

    rows = _rows(1986)
    relabelled = _set(rows, 1, 0, rows[1][0].replace("1986", "1987"))
    relabelled = _set(relabelled, 22, 0, "Source: U.S. Census Bureau, 1988.")
    with pytest.raises(ValueError, match="no inspected layout"):
        SCRIPT.parse_threshold_rows(relabelled, 1987)


# -------------------------------------------------------------------------
# Differential: the capture against the sheet XML, read by row label
# -------------------------------------------------------------------------
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_ID = (
    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
)
#: Printed row label (lower case, whitespace collapsed, dot leaders and
#: colon dropped) to the capture's key.  "persons" is 2001's noun.
_LABEL_KEYS = {
    "one person (unrelated individual)": ("all_ages", "one"),
    "under 65 years": ("row", "one_under_65"),
    "65 years and over": ("row", "one_65_plus"),
    "householder under 65 years": ("row", "two_under_65"),
    "householder 65 years and over": ("row", "two_65_plus"),
}
for _noun in ("people", "persons"):
    _LABEL_KEYS[f"two {_noun}"] = ("all_ages", "two")
    for _word, _key in (
        ("three", "three"),
        ("four", "four"),
        ("five", "five"),
        ("six", "six"),
        ("seven", "seven"),
        ("eight", "eight"),
    ):
        _LABEL_KEYS[f"{_word} {_noun}"] = ("row", _key)
    _LABEL_KEYS[f"nine {_noun} or more"] = ("row", "nine_plus")


def _column_index(letters: str) -> int:
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index - 1


def _sheet_grid(path: Path) -> dict[tuple[int, int], object]:
    """The first worksheet's cell values by (row, column), 0-based, read
    from the package XML (shared, inline and formula strings; numbers as
    floats).  Refuses a formula cell."""

    with zipfile.ZipFile(path) as package:
        names = set(package.namelist())
        book = ET.fromstring(package.read("xl/workbook.xml"))
        rels = ET.fromstring(package.read("xl/_rels/workbook.xml.rels"))
        target = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}[
            next(book.iter(f"{_MAIN}sheet")).attrib[_REL_ID]
        ].lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        shared = (
            [
                "".join(t.text or "" for t in item.iter(f"{_MAIN}t"))
                for item in ET.fromstring(
                    package.read("xl/sharedStrings.xml")
                ).iter(f"{_MAIN}si")
            ]
            if "xl/sharedStrings.xml" in names
            else []
        )
        sheet = ET.fromstring(package.read(target))
    grid: dict[tuple[int, int], object] = {}
    for cell in sheet.iter(f"{_MAIN}c"):
        assert cell.find(f"{_MAIN}f") is None, f"formula in {cell.attrib}"
        match = re.fullmatch(r"([A-Z]+)(\d+)", cell.attrib["r"])
        where = (int(match.group(2)) - 1, _column_index(match.group(1)))
        kind = cell.attrib.get("t")
        value = cell.find(f"{_MAIN}v")
        if kind == "inlineStr":
            grid[where] = "".join(t.text or "" for t in cell.iter(f"{_MAIN}t"))
        elif value is None:
            continue
        elif kind == "s":
            grid[where] = shared[int(value.text)]
        elif kind in ("str", "e"):
            grid[where] = value.text
        else:
            grid[where] = float(value.text)
    return grid


def _normalized(text: object) -> str:
    return re.sub(r"[\s.:]+$", "", " ".join(str(text).split()).lower())


def _read_by_label(year: int) -> dict[str, object]:
    """Every threshold of ``year``'s workbook, located by its row label."""

    grid = _sheet_grid(WORKBOOKS / _name(year))
    labels = {
        row: _normalized(value)
        for (row, column), value in grid.items()
        if column == 0 and isinstance(value, str) and value.strip()
    }
    header = [
        row for row, text in labels.items() if text == "size of family unit"
    ]
    assert len(header) == 1, year
    assert _normalized(grid[(header[0], 1)]) == "weighted average thresholds"
    children = [
        _normalized(grid.get((header[0] + 1, 2 + k), "")) for k in range(9)
    ]
    assert children[0] == "none" and children[-1] == "eight or more", year
    out: dict[str, object] = {"all_ages": {}, "weighted": {}, "matrix": {}}
    order = []
    for row in sorted(labels):
        text = labels[row]
        if text not in _LABEL_KEYS:
            continue
        kind, key = _LABEL_KEYS[text]
        order.append(key)
        weighted = grid[(row, 1)]
        assert isinstance(weighted, float) and weighted.is_integer(), year
        if kind == "all_ages":
            out["all_ages"][key] = int(weighted)
            assert not any(
                isinstance(grid.get((row, c)), float) for c in range(2, 11)
            ), (year, text)
            continue
        out["weighted"][key] = int(weighted)
        out["matrix"][key] = {
            str(c - 2): int(grid[(row, c)])
            for c in range(2, 11)
            if isinstance(grid.get((row, c)), float)
        }
    # G8's row: "65 years and over" under "One person (unrelated
    # individual)", before the two-person rows, in every year
    assert order[:3] == ["one", "one_under_65", "one_65_plus"], year
    assert order[3] == "two", year
    assert len(order) == 13, year
    return out


@pytest.mark.parametrize("year", YEARS)
def test_every_captured_value_equals_the_cell_read_by_its_label(capture, year):
    read = _read_by_label(year)
    key = str(year)
    assert read["weighted"] == capture["weighted_average"][key]
    assert read["all_ages"] == capture["weighted_average_all_ages"][key]
    assert read["matrix"] == capture["matrix"][key]
    assert rules.load_aged_thresholds().for_year(year) == (
        read["weighted"]["one_65_plus"]
    )


# -------------------------------------------------------------------------
# Cross-check: Census's HTML Table 1 (1959-2006, page of 2009-09-29)
# -------------------------------------------------------------------------
def _table1() -> dict[int, dict[str, float]]:
    """Census historical poverty Table 1 as its HTML edition prints it.

    Three blocks in one ``<pre>``: unrelated individuals (all ages, under
    65, 65 or older) and two people (all ages, householder under 65, 65 or
    older); families of 3, 4, 5, 6 and 7 or more people; families of 7, 8
    and 9 or more people and the annual average CPI-U (1982-84 = 100).
    """

    raw = TABLE1_HTML.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == TABLE1_SHA256
    text = raw.decode("latin-1")
    pre = text[text.index("<pre>") : text.index("</pre>")]
    blocks = pre.split("Table 1. Weighted Average Poverty Thresholds")[1:]
    assert len(blocks) == 3
    flat = [" ".join(block.split()) for block in blocks]
    # the column heads, as printed (read across the header lines)
    assert "2 people Unrelated individuals" in flat[0]
    assert "All ages age 65 or older All ages age 65 or older" in flat[0]
    assert "3 people 4 people 5 people 6 people or more" in flat[1]
    assert "7 people 8 people or more =100) B/" in flat[2]
    columns = (
        (
            "one",
            "one_under_65",
            "one_65_plus",
            "two",
            "two_under_65",
            "two_65_plus",
        ),
        ("three", "four", "five", "six", "seven_plus"),
        ("seven", "eight", "nine_plus", "cpi_u"),
    )
    out: dict[int, dict[str, float]] = {}
    for block, names in zip(blocks, columns, strict=True):
        for match in re.finditer(
            r"^[ \t]+(\d{4})(?: \d+/)?\.+[ \t]+(.+?)[ \t\r]*$", block, re.M
        ):
            values = match.group(2).split()
            assert len(values) == len(names), match.group(0)
            row = out.setdefault(int(match.group(1)), {})
            for name, value in zip(names, values, strict=True):
                if value != "***":
                    row[name] = float(value.replace("$", "").replace(",", ""))
    assert sorted(out) == list(range(1959, 2007))
    return out


#: The weighted averages in which the capture's workbooks and Table 1's
#: 2009 edition differ: {(year, row): (Table 1, workbook)}.  All are
#: averages over several thresholds (a family size over its related-children
#: cells, or a size over both ages), in 1989, 1991, 1992, 1999 and 2000.
#: Table 1 flags 1999 (11/: Census 2000 population controls) and 2000
#: (12/: those controls and a sample expanded by 28,000 households) and
#: nothing in 1989-1992; neither source says why the workbooks differ.
#: No one-person row by age differs: each is a single threshold.
TABLE1_DIFFERENCES: dict[tuple[int, str], tuple[int, int]] = {
    (1989, "one"): (6310, 6313),
    (1989, "two"): (8076, 8078),
    (1989, "two_under_65"): (8343, 8344),
    (1989, "three"): (9885, 9886),
    (1989, "seven"): (19162, 19160),
    (1989, "eight"): (21328, 21323),
    (1989, "nine_plus"): (25480, 25496),
    (1991, "eight"): (23582, 23605),
    (1992, "one"): (7143, 7146),
    (1992, "two"): (9137, 9140),
    (1992, "two_under_65"): (9443, 9444),
    (1992, "three"): (11186, 11187),
    (1992, "five"): (16952, 16950),
    (1992, "six"): (19137, 19135),
    (1992, "seven"): (21594, 21589),
    (1992, "eight"): (24053, 24056),
    (1992, "nine_plus"): (28745, 28749),
    (1999, "one"): (8499, 8501),
    (1999, "two"): (10864, 10869),
    (1999, "two_under_65"): (11213, 11214),
    (1999, "three"): (13289, 13290),
    (1999, "four"): (17030, 17029),
    (1999, "five"): (20128, 20127),
    (1999, "six"): (22730, 22727),
    (1999, "seven"): (25918, 25912),
    (1999, "eight"): (28970, 28967),
    (1999, "nine_plus"): (34436, 34417),
    (2000, "one"): (8791, 8794),
    (2000, "two"): (11235, 11239),
    (2000, "two_under_65"): (11589, 11590),
    (2000, "two_65_plus"): (10418, 10419),
    (2000, "three"): (13740, 13738),
    (2000, "four"): (17604, 17603),
    (2000, "five"): (20815, 20819),
    (2000, "six"): (23533, 23528),
    (2000, "seven"): (26750, 26753),
    (2000, "nine_plus"): (35150, 35060),
}
_ROWS_COMPARED = (
    "one",
    "one_under_65",
    "one_65_plus",
    "two",
    "two_under_65",
    "two_65_plus",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine_plus",
)


def _captured_average(capture, year: int, row: str) -> int:
    key = str(year)
    if row in ("one", "two"):
        return capture["weighted_average_all_ages"][key][row]
    return capture["weighted_average"][key][row]


def test_g8s_row_agrees_with_censuss_table_1_every_year_to_2006(capture):
    """The row Track M reads (one person, 65 and over), and the under-65
    row, equal Table 1's unrelated individuals by age in all nineteen
    captured years 1982-2006."""

    table = _table1()
    years = [y for y in YEARS if y <= 2006]
    assert len(years) == 19
    for year in years:
        for row in ("one_under_65", "one_65_plus"):
            assert table[year][row] == _captured_average(capture, year, row)
        assert rules.load_aged_thresholds().for_year(year) == (
            table[year]["one_65_plus"]
        )


def test_every_other_weighted_average_agrees_but_the_recorded(capture):
    """Differential over the 13 weighted averages x 19 years: every one
    equals Table 1 except the 37 recorded in :data:`TABLE1_DIFFERENCES`,
    none of them a one-person row by age (a single threshold, which no
    weighting changes)."""

    table = _table1()
    found = {}
    for year in (y for y in YEARS if y <= 2006):
        for row in _ROWS_COMPARED:
            printed = int(table[year][row])
            captured = _captured_average(capture, year, row)
            if printed != captured:
                found[(year, row)] = (printed, captured)
    assert found == TABLE1_DIFFERENCES
    assert {year for year, _ in found} == {1989, 1991, 1992, 1999, 2000}
    assert not any(row in ("one_under_65", "one_65_plus") for _, row in found)
    # each differing average is still one the workbook's own matrix
    # brackets (the parser's within-year check), and Table 1's footnote
    # markers stand on 1999, 2000 and 2004 only
    for (year, row), (_, captured) in found.items():
        if row in ("one", "two"):
            continue
        cells = capture["matrix"][str(year)][row].values()
        assert min(cells) <= captured <= max(cells)
    marked = re.findall(
        r"^[ \t]+(\d{4}) (\d+)/\.",
        TABLE1_HTML.read_bytes().decode("latin-1"),
        re.M,
    )
    assert sorted(set(marked)) == [
        ("1999", "11"),
        ("2000", "12"),
        ("2004", "14"),
    ]


def test_each_year_pair_moves_with_the_cpi_u_table_1_prints(capture):
    """The 2009 workbook's note says the thresholds are updated each year
    by the change in the average annual CPI-U.  Between captured years
    through 2006 the matrix ratio equals Table 1's CPI-U ratio to within
    the rounding of the CPI to 0.1 and of the cells to whole dollars."""

    cpi = {year: row["cpi_u"] for year, row in _table1().items()}
    ratios = capture["checks"]["matrix_ratio_by_year_pair"]
    through_2006 = [y for y in YEARS if y <= 2006]
    for earlier, later in zip(through_2006, through_2006[1:], strict=False):
        implied = cpi[later] / cpi[earlier]
        bound = 0.05 / cpi[earlier] + 0.05 / cpi[later] + 1 / 4000
        ratio = ratios[f"{earlier}-{later}"]
        assert abs(ratio / implied - 1) <= bound, (earlier, later)


# -------------------------------------------------------------------------
# Invariants over the whole capture
# -------------------------------------------------------------------------
def test_every_threshold_is_positive(capture):
    for key in map(str, YEARS):
        values = [
            *capture["weighted_average"][key].values(),
            *capture["weighted_average_all_ages"][key].values(),
            *(
                cell
                for cells in capture["matrix"][key].values()
                for cell in cells.values()
            ),
        ]
        assert len(values) == 11 + 2 + 48
        assert all(isinstance(v, int) and v > 0 for v in values), key


def test_65_and_over_is_below_under_65_every_year(capture):
    for key in map(str, YEARS):
        weighted = capture["weighted_average"][key]
        assert weighted["one_65_plus"] < weighted["one_under_65"], key
        assert weighted["two_65_plus"] < weighted["two_under_65"], key
    loaded = rules.load_aged_thresholds()
    for year in YEARS:
        under = capture["weighted_average"][str(year)]["one_under_65"]
        assert loaded.for_year(year) < under


def test_thresholds_rise_between_captured_years_except_2009(capture):
    """Every threshold (each of the 48 matrix cells, the one-person rows by
    age among them) rises from one captured year to the next, save the
    pair 2008-2009, where every one falls: the one year whose own workbook
    note says the average annual CPI-U fell.

    The weighted averages over several cells follow in every other pair.
    In 2009 two of them rose while all their cells fell (eight people +$32,
    nine or more +$20): they weight the cells by family composition, and
    the notes name the CPS as their source.  Track M reads a single
    threshold, not such an average."""

    exceptions = []
    for earlier, later in zip(YEARS, YEARS[1:], strict=False):
        a, b = capture["matrix"][str(earlier)], capture["matrix"][str(later)]
        cells = [b[row][k] - a[row][k] for row in a for k in a[row]]
        assert len(cells) == 48
        averages = {
            row: capture["weighted_average"][str(later)][row]
            - capture["weighted_average"][str(earlier)][row]
            for row in capture["weighted_average"][str(earlier)]
        }
        if all(move > 0 for move in cells):
            assert all(move > 0 for move in averages.values()), earlier
            continue
        assert all(move < 0 for move in cells), (earlier, later)
        exceptions.append((earlier, later))
        assert sorted(row for row, move in averages.items() if move > 0) == [
            "eight",
            "nine_plus",
        ]
        assert averages["one_65_plus"] < 0 and averages["one_under_65"] < 0
    assert exceptions == [(2008, 2009)]
    note = " ".join(str(_rows(2009)[23][0]).split())
    assert "Since the average annual CPI-U for 2009 was lower" in note
    # no other captured year's note carries the CPI-U sentences
    for year in YEARS:
        if year != 2009:
            assert "was lower" not in " ".join(str(_rows(year)[23][0]).split())


def test_the_g8_row_is_its_single_matrix_cell(capture):
    for year in YEARS:
        key = str(year)
        weighted = capture["weighted_average"][key]["one_65_plus"]
        cell = capture["matrix"][key]["one_65_plus"]
        assert list(cell) == ["0"], year
        if year == 2022:
            assert abs(weighted - cell["0"]) <= 5 and weighted % 10 == 0
        else:
            assert weighted == cell["0"], year


# -------------------------------------------------------------------------
# Hypothesis: the parser on INVENTED tables in every layout
# -------------------------------------------------------------------------
_SIZE_WORDS = ("three", "four", "five", "six", "seven", "eight")


def _invented_table(year: int, level: int, step: int, gap: int, less: int):
    """An INVENTED threshold table in ``year``'s printed layout.

    Not Census values: the size-1 under-65 threshold is ``level``, each
    further person adds ``step``, the 65-and-over rows are ``gap`` lower
    and each related child ``less`` lower, all times $10 in 2022 (whose
    layout prints weighted averages rounded to $10).  Returns (rows,
    expected).
    """

    unit = 10 if year == 2022 else 1
    noun = "persons" if year == 2001 else "people"
    suffix = "......" if year == 2001 else ""
    one_under = [level]
    one_old = [level - gap]
    two_under = [level + step, level + step - less]
    two_old = [level + step - gap, level + step - gap - less]
    sizes = {
        key: [level + (n - 1) * step - k * less for k in range(n)]
        for n, key in zip(
            range(3, 10), (*_SIZE_WORDS, "nine_plus"), strict=True
        )
    }
    matrix = {
        "one_under_65": one_under,
        "one_65_plus": one_old,
        "two_under_65": two_under,
        "two_65_plus": two_old,
        **sizes,
    }
    weighted = {key: min(cells) for key, cells in matrix.items()}
    all_ages = {
        "one": level - gap // 2,
        "two": (weighted["two_65_plus"] + weighted["two_under_65"]) // 2,
    }
    matrix = {
        key: [unit * cell for cell in cells] for key, cells in matrix.items()
    }
    weighted = {key: unit * value for key, value in weighted.items()}
    all_ages = {key: unit * value for key, value in all_ages.items()}

    def row(label, key):
        return [label, weighted[key], *matrix[key]]

    survey = _survey(year)
    note = {
        "march_cps": (
            f"Note: The source of the weighted average thresholds is the "
            f"March {year + 1} Current Population Survey (CPS). "
        ),
        "cps_ads": (
            f"Note: The source of the weighted average thresholds is the "
            f"{year + 1} Current Population Survey Annual Demographic "
            "Supplement (CPS ADS). "
        ),
        "cps_asec": (
            f"Note: The source of the weighted average thresholds is the "
            f"{year + 1} Current Population Survey Annual Social and "
            "Economic Supplement (CPS ASEC)."
        ),
    }[survey]
    rows = [
        [
            "Table with row headings in column A and column headings in "
            "rows 5 to 6."
        ],
        [
            f"Poverty Thresholds for {year} by Size of Family and Number of "
            "Related Children Under 18 Years"
        ],
        ["(In dollars)"],
        [],
        [
            "Size of family unit",
            "Weighted\nAverage\nThresholds",
            "Related children under 18 years",
        ],
        [
            None,
            None,
            "None",
            "One",
            "Two",
            "Three",
            "Four",
            "Five",
            "Six",
            "Seven",
            "Eight\nor\nmore",
        ],
        [],
        [f"One person (unrelated individual){suffix or ':'}", all_ages["one"]],
        row("Under 65 years......", "one_under_65"),
        row("65 years and over......", "one_65_plus"),
        [],
        [f"Two {noun}{suffix or ':'}", all_ages["two"]],
        row(f"Householder under 65 years{suffix}", "two_under_65"),
        row("Householder 65 years and over......", "two_65_plus"),
        [],
        *(
            row(f"{word.capitalize()} {noun}{suffix}", word)
            for word in _SIZE_WORDS
        ),
        row(f"Nine {noun} or more{suffix}", "nine_plus"),
        [f"Source: U.S. Census Bureau, {year + 1}."],
        [note],
    ]
    if year in REVISION_LINES:
        rows.append([REVISION_LINES[year] + " "])
    expected = {
        "weighted_average": weighted,
        "all_ages": all_ages,
        "matrix": {
            key: dict(enumerate(cells)) for key, cells in matrix.items()
        },
    }
    return rows, expected


_TABLES = st.tuples(
    st.sampled_from(YEARS),
    st.integers(1_000, 60_000),
    st.integers(200, 5_000),
    st.integers(1, 190),
    st.integers(0, 60),
)


@settings(max_examples=150, deadline=None)
@given(_TABLES)
def test_property_the_parser_round_trips_invented_tables_in_every_layout(
    drawn,
):
    year, level, step, gap, less = drawn
    rows, expected = _invented_table(year, level, step, gap, less)
    parsed = SCRIPT.parse_threshold_rows(rows, year)
    assert parsed["weighted_average"] == expected["weighted_average"]
    assert parsed["all_ages"] == expected["all_ages"]
    assert parsed["matrix"] == expected["matrix"]
    assert parsed["survey"] == _survey(year)
    assert parsed["revision_line"] == REVISION_LINES.get(year)


@settings(max_examples=100, deadline=None)
@given(_TABLES, st.integers(0, 500))
def test_property_65_and_over_at_or_above_under_65_is_refused(drawn, above):
    """Invariant: one person aged 65 and over below one under 65.  An
    INVENTED table whose 65-and-over threshold is at or above the under-65
    one is refused in every layout."""

    year, level, step, gap, less = drawn
    rows, expected = _invented_table(year, level, step, gap, less)
    unit = 10 if year == 2022 else 1
    value = expected["weighted_average"]["one_under_65"] + unit * above
    rows = _set(_set(rows, 9, 1, value), 9, 2, value)
    with pytest.raises(ValueError, match="not below under-65"):
        SCRIPT.parse_threshold_rows(rows, year)


@settings(max_examples=100, deadline=None)
@given(_TABLES, st.sampled_from(YEARS))
def test_property_a_layout_departure_is_refused_in_another_year(drawn, other):
    """An INVENTED table in one year's layout, parsed as another year's
    (its title and source relabelled), is refused unless the two years
    share every layout feature: the survey, the size-row noun and the
    revision line."""

    year, level, step, gap, less = drawn
    rows, _ = _invented_table(year, level, step, gap, less)
    rows = _set(rows, 1, 0, rows[1][0].replace(str(year), str(other)))
    rows = _set(rows, 22, 0, f"Source: U.S. Census Bureau, {other + 1}.")
    rows = _set(
        rows, 23, 0, rows[23][0].replace(str(year + 1), str(other + 1))
    )
    same = (
        _survey(year) == _survey(other)
        and (year == 2001) == (other == 2001)
        and REVISION_LINES.get(year) == REVISION_LINES.get(other)
        # 2022's layout needs weighted averages in $10 (the invented table
        # has them only in its own 2022 layout)
        and not (other == 2022 and year != 2022)
    )
    if same:
        SCRIPT.parse_threshold_rows(rows, other)
    else:
        with pytest.raises(ValueError):
            SCRIPT.parse_threshold_rows(rows, other)


@settings(max_examples=150, deadline=None)
@given(
    _TABLES,
    st.floats(0.9, 1.6),
    st.integers(0, 60),
    st.integers(5, 400),
)
def test_property_the_cross_year_check(drawn, ratio, pick, bump):
    """A matrix scaled by one ratio and rounded to whole dollars passes and
    returns that ratio; moving any one cell by $5 or more is refused.

    The bound: every cell's ratio lies within 0.5 / (smallest cell) of the
    true ratio, so the median does too, and a cell of value v then misses
    the median ratio by at most 0.5 + 0.5 v / (smallest cell): at most
    $2 when the largest cell is at most three times the smallest, and at
    least bump - $2 for the moved cell.  That is a sufficient condition
    for the proof, not a property of the real tables (their largest cell
    is 4.64 times the smallest; they pass with their actual rounding,
    test_threshold_capture.py's real-layout test)."""

    year, level, step, gap, less = drawn
    _, expected = _invented_table(year, level, step, gap, less)
    earlier = expected["matrix"]
    values = [v for cells in earlier.values() for v in cells.values()]
    assume(max(values) <= 3 * min(values))
    later = {
        key: {k: round(v * ratio) for k, v in cells.items()}
        for key, cells in earlier.items()
    }
    returned = SCRIPT.check_matrix_moves_together(earlier, later, 2000, 1990)
    assert abs(returned - ratio) <= 0.5 / min(values)
    cells = [(key, k) for key, row in later.items() for k in row]
    key, k = cells[pick % len(cells)]
    moved = copy.deepcopy(later)
    moved[key][k] += bump
    with pytest.raises(ValueError, match="from 1990's"):
        SCRIPT.check_matrix_moves_together(earlier, moved, 2000, 1990)


# -------------------------------------------------------------------------
# Hypothesis: the captured-years text and the threshold-year check
# -------------------------------------------------------------------------
def _years_from_text(text: str) -> set[int]:
    out: set[int] = set()
    for part in text.split(", "):
        first, _, last = part.partition("-")
        out.update(range(int(first), int(last or first) + 1))
    return out


@settings(max_examples=200, deadline=None)
@given(st.sets(st.integers(1950, 2050), min_size=1, max_size=60))
def test_property_the_captured_years_text_round_trips(years):
    text = thresholds.captured_years_text(years)
    assert _years_from_text(text) == years
    # runs are maximal: no two parts are adjacent
    parts = [tuple(map(int, part.split("-"))) for part in text.split(", ")]
    ends = [part[-1] for part in parts]
    starts = [part[0] for part in parts]
    assert all(
        start > end + 1 for end, start in zip(ends, starts[1:], strict=False)
    )


def test_the_captured_years_text_of_the_capture():
    assert thresholds.captured_years_text(YEARS) == (
        "1982, 1986, 1988-1989, 1991-1992, 1994-2022"
    )
    assert thresholds.captured_years_text([]) == "none"


@settings(max_examples=200, deadline=None)
@given(
    st.dictionaries(
        st.integers(1970, 2030), st.integers(0, 50), min_size=1, max_size=40
    )
)
def test_property_the_threshold_year_check_refuses_exactly_the_missing(
    needed,
):
    """The check passes iff every needed year is captured, and its refusal
    names every missing year and no captured one."""

    loaded = rules.load_aged_thresholds()
    missing = sorted(set(needed) - set(YEARS))
    if not missing:
        rules.check_threshold_years(needed, loaded)
        rules.check_threshold_years(list(needed), loaded)
        return
    with pytest.raises(rules.ThresholdYearMissingError) as refused:
        rules.check_threshold_years(needed, loaded)
    named = refused.value.args[0].split(" are not in the capture")[0]
    named_years = {int(y) for y in re.findall(r"\b(\d{4})\b", named)}
    assert named_years == set(missing)


# -------------------------------------------------------------------------
# The loader's and the capture's year guards (independent review,
# 2026-09-25: each guard was added with the years before 2003 but had no
# test)
# -------------------------------------------------------------------------
def _repinned(directory: Path, edit) -> tuple[Path, str]:
    """The committed capture with ``edit`` applied, written to
    ``directory`` and returned with its own SHA-256 (so that the loader's
    pin check passes and its year guards are what is exercised)."""

    data = json.loads(CAPTURE.read_text())
    edit(data)
    raw = (json.dumps(data, indent=2) + "\n").encode()
    path = directory / CAPTURE.name
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest()


def _drop_captured_1998(data):
    data["captured_years"].remove(1998)


def _add_captured_1993(data):
    data["captured_years"] = sorted([*data["captured_years"], 1993])


def _add_weighted_1993(data):
    data["weighted_average"]["1993"] = data["weighted_average"]["1994"]


def _drop_weighted_1998(data):
    del data["weighted_average"]["1998"]


@pytest.mark.parametrize(
    "edit, message",
    [
        (_drop_captured_1998, "captured years"),
        (_add_captured_1993, "captured years"),
        (_add_weighted_1993, "weighted averages for other years"),
        (_drop_weighted_1998, "weighted averages for other years"),
    ],
    ids=[
        "captured_years_lacks_1998",
        "captured_years_adds_1993",
        "weighted_averages_add_1993",
        "weighted_averages_lack_1998",
    ],
)
def test_the_loader_refuses_a_capture_of_other_years(tmp_path, edit, message):
    """A capture whose SHA-256 matches its pin but whose captured years, or
    whose weighted averages' years, are not exactly
    ``TRACK_M_THRESHOLD_YEARS`` is refused with a ValueError naming the
    guard (without the guards, the first two loaded and the last raised a
    bare KeyError)."""

    path, digest = _repinned(tmp_path, edit)
    with pytest.raises(ValueError, match=message):
        rules.load_aged_thresholds(path, expected_sha256=digest)


def test_the_loader_accepts_the_committed_content_repinned(tmp_path):
    path, digest = _repinned(tmp_path, lambda data: None)
    loaded = rules.load_aged_thresholds(path, expected_sha256=digest)
    assert loaded.annual == rules.load_aged_thresholds().annual


@settings(max_examples=40, deadline=None)
@given(
    st.sets(st.sampled_from(YEARS), max_size=3),
    st.sets(st.sampled_from((1981, *NOT_CAPTURED, 2023)), max_size=3),
    st.sets(st.sampled_from(YEARS), max_size=3),
    st.sets(st.sampled_from((1981, *NOT_CAPTURED, 2023)), max_size=3),
)
def test_property_the_loader_accepts_exactly_the_captured_years(
    drop_listed, add_listed, drop_values, add_values
):
    """Invariant: the loader accepts a (re-pinned) capture iff its
    ``captured_years`` and the years of its weighted averages are both
    exactly ``TRACK_M_THRESHOLD_YEARS``; then it returns every one of those
    years and no other."""

    import tempfile

    def edit(data):
        data["captured_years"] = sorted(
            (set(data["captured_years"]) - drop_listed) | add_listed
        )
        values = data["weighted_average"]
        template = dict(values["1994"])
        for year in drop_values:
            del values[str(year)]
        for year in add_values:
            values[str(year)] = dict(template)

    with tempfile.TemporaryDirectory() as directory:
        path, digest = _repinned(Path(directory), edit)
        exact = not (drop_listed or add_listed or drop_values or add_values)
        if exact:
            loaded = rules.load_aged_thresholds(path, expected_sha256=digest)
            assert sorted(loaded.annual) == sorted(YEARS)
        else:
            with pytest.raises(ValueError):
                rules.load_aged_thresholds(path, expected_sha256=digest)


@pytest.mark.parametrize(
    "years", [(1994, 1992), (1994, 1994, 1995)], ids=["unordered", "repeated"]
)
def test_the_capture_refuses_years_not_strictly_increasing(years):
    """The cross-year check pairs each captured year with the one before it
    in the list, so the list must be strictly increasing (a guard added
    with the gaps before 2003)."""

    with pytest.raises(ValueError, match="not strictly increasing"):
        SCRIPT._parse_years(WORKBOOKS, years, SCRIPT.CENSUS_WORKBOOK_SHA256)
