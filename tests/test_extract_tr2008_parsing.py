"""Parser unit tests for the TR2008 extractor, on invented inputs only.

Every row, cell and HTML fragment below is INVENTED to exercise one parsing
rule; none is a transcription of the report.  The committed outputs are
tested in ``test_tr2008_parameters.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import extract_tr2008_parameters as extractor  # noqa: E402


def test__year_row__keeps_a_leading_decimal_value_after_dot_leaders():
    # Regression: dot leaders once swallowed the "." of ".1".
    line = "  2011 . . . . . . . . . .             .1           -.3   4.0"
    match = extractor._YEAR_ROW.match(line)
    assert match is not None
    assert match["year"] == "2011"
    assert match["rest"].split() == [".1", "-.3", "4.0"]


def test__year_row__reads_glued_and_spaced_footnote_markers():
    glued = extractor._YEAR_ROW.match("  20073 . . . . . . .   1.4   .0")
    spaced = extractor._YEAR_ROW.match("  2005 2 . . .   74.9   79.8")
    plain = extractor._YEAR_ROW.match("  1960. . . . . .   455   77")
    assert (glued["year"], glued["fn"]) == ("2007", "3")
    assert (spaced["year"], spaced["fn2"]) == ("2005", "2")
    assert plain["year"] == "1960" and plain["fn"] is None


def test__range_row__reads_multi_year_labels():
    match = extractor._RANGE_ROW.match("  2015 to 2020. . . .   1.7  -.2")
    assert (match["first"], match["last"]) == ("2015", "2020")
    assert match["rest"].split() == ["1.7", "-.2"]


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("$8,000.50", 8000.5),
        (".9", 0.9),
        ("-.2", -0.2),
        ("-0.2", -0.2),
        ("45,000", 45000),
        ("--", None),
        (". . .", None),
    ],
)
def test__num__parses_printed_cells(token, expected):
    value = extractor._num(token)
    assert value == expected
    assert type(value) is type(expected)


def test__num__rejects_text():
    with pytest.raises(ValueError, match="not a numeric cell"):
        extractor._num("a")


def test__take_footnoted__strips_separate_and_glued_markers():
    columns = ("a", "b", "c")
    markers = {"a": "7", "c": "7"}
    separate = extractor._take_footnoted(
        ["7", "2.0", "10.5", "7", "$300"], columns, markers
    )
    glued = extractor._take_footnoted(
        ["71.5", "10.5", "7300"], columns, markers
    )
    assert separate == {"a": 2.0, "b": 10.5, "c": 300}
    assert glued == {"a": 1.5, "b": 10.5, "c": 300}


def test__take_footnoted__fails_closed():
    with pytest.raises(ValueError, match="expected footnote"):
        extractor._take_footnoted(["1.5"], ("a",), {"a": "7"})
    with pytest.raises(ValueError, match="unconsumed"):
        extractor._take_footnoted(["1.5", "2.5"], ("a",), {})
    with pytest.raises(ValueError, match="ended before"):
        extractor._take_footnoted([], ("a",), {})


def test__vc1_footnotes__marks_only_the_documented_cells():
    assert extractor._vc1_footnotes("historical", 1999) == {
        "cola_percent": "6"
    }
    assert set(extractor._vc1_footnotes("low_cost", 2007)) == {
        "cola_percent",
        "contribution_benefit_base",
        "ret_exempt_under_nra",
        "ret_exempt_at_nra",
    }
    assert set(extractor._vc1_footnotes("high_cost", 2008)) == set(
        extractor.VC1_ACTUAL_COLUMNS
    )
    assert extractor._vc1_footnotes("intermediate", 2009) == {}
    assert extractor._vc1_footnotes("historical", 2006) == {}


def test__rounded_growth__rounds_half_up_like_the_printed_tables():
    assert extractor._rounded_growth(105.05, 100.0) == 5.1
    assert extractor._rounded_growth(100.0, 100.0) == 0.0
    assert extractor._rounded_growth(99.0, 100.0) == -1.0


def test__json_encoding__round_trips_and_keeps_short_rows_on_one_line():
    rows = [{"year": 2000 + i, "value": 1.5} for i in range(40)]
    payload = {
        "b": [*rows, {"year": 2040, "value": None}],
        "a": {"nested": {"deep": [1, 2, 3]}, "text": "x" * 500},
    }
    text = extractor._json_dump(payload)
    assert json.loads(text) == payload
    assert '    {"value": 1.5, "year": 2000},\n' in text
    assert '    "nested": {"deep": [1, 2, 3]},\n' in text
    assert text.endswith("\n")


def test__table_collector__captions_nesting_scripts_and_soft_hyphens():
    html = (
        "<table><caption>Table 1.<br>Invented caption</caption>"
        "<tr><td>Ter\u00admination</td><td>1,234</td></tr>"
        "<tr><td><table><tr><td>inner</td></tr></table></td></tr>"
        "</table><script>var x = '<table>';</script>"
    )
    collector = extractor._TableCollector()
    collector.feed(html)
    outer, inner = collector.tables
    assert outer["caption"] == "Table 1. Invented caption"
    assert outer["rows"][0] == ["Termination", "1,234"]
    assert inner["rows"] == [["inner"]]


def test__sectioned_year_rows__tracks_sections_and_footnotes():
    rows = [
        ["Calendar year", "", "Value"],
        ["Intermediate:"],
        ["2008", "", "1.0"],
        ["2009 2", "", "2.0"],
        ["Low Cost:"],
        ["2008", "", "3.0"],
    ]
    assert extractor._sectioned_year_rows(rows) == [
        ("intermediate", 2008, None, ["1.0"]),
        ("intermediate", 2009, "2", ["2.0"]),
        ("low_cost", 2008, None, ["3.0"]),
    ]


def test__comparison__reports_mismatches_and_refuses_empty_checks():
    check = extractor._Comparison("x", "invented", "left", "right")
    check.compare("cell/1", 1, 1)
    check.compare("cell/2", 1, 2)
    result = check.result()
    assert result["cells_compared"] == 2
    assert result["passed"] is False
    assert result["mismatches"] == [{"cell": "cell/2", "left": 1, "right": 2}]
    with pytest.raises(ValueError, match="compared no cells"):
        extractor._Comparison("y", "empty", "l", "r").result()


def test__printed_page_offset__maps_pdf_index_to_printed_number():
    assert extractor._printed(110) == 102
    assert extractor._locator("V.C1", (110, 111)) == {
        "table": "V.C1",
        "pdf_pages": [110, 111],
        "printed_pages": [102, 103],
    }


def test__captioned_tables__keeps_single_digit_ids_and_joins_continued():
    # Regression: 'Table 2' (one character) was skipped by the old regex.
    tables = [
        {"caption": "Invented section Table 2. Invented", "rows": [["a"]]},
        {"caption": "Table 19. Invented", "rows": [["b", "1"]]},
        {"caption": "Table 19. Continued", "rows": [["c", "2"]]},
        {"caption": "Table 4.C2—Invented", "rows": [["d"]]},
        {"caption": "No id here", "rows": [["e"]]},
    ]
    out = extractor._captioned_tables(tables, "invented.html", r"Table\s*")
    assert sorted(out) == ["Table 19", "Table 2", "Table 4.C2"]
    assert out["Table 2"]["tsv"] == "a"
    assert out["Table 19"]["tsv"] == "b\t1\nc\t2"
    assert out["Table 19"]["continued"] is True


def test__as118_cell__reads_dashes_and_enforces_cell_type():
    assert extractor._as118_cell("—", integer=False) is None
    assert extractor._as118_cell("0.004751", integer=False) == 0.004751
    assert extractor._as118_cell("100,022", integer=True) == 100022
    with pytest.raises(ValueError, match="unexpected cell type"):
        extractor._as118_cell("100,022", integer=False)
    with pytest.raises(ValueError, match="unexpected cell type"):
        extractor._as118_cell("0.5", integer=True)


def test__as118_row_patterns__match_invented_grid_year_and_old_age_rows():
    select = extractor._AS118_SELECT_ROW.match(
        "   16        0.001000     —      26"
    )
    assert select["age"] == "16"
    assert select["rest"].split() == ["0.001000", "—", "26"]
    year = extractor._AS118_YEAR_ROW.match("1999        1,000   2.50   9.9")
    assert (year["year"], year["rest"].split()) == (
        "1999",
        ["1,000", "2.50", "9.9"],
    )
    assert extractor._AS118_YEAR_ROW.match("  17") is None
    old = extractor._AS118_OLD_ROW.match("   110      —      1")
    assert (old["age"], old["male"], old["female"]) == ("110", "—", "1")


def test__survival_step__rounds_half_up():
    assert extractor._survival_step(1000, 0.0015) == 999  # 998.5 -> 999
    assert extractor._survival_step(1000, 0.0016) == 998  # 998.4 -> 998
    assert extractor._survival_step(100000, 0.0) == 100000


def test__visible_text__separates_tags_and_skips_scripts():
    collector = extractor._VisibleText()
    collector.feed(
        "<p>age-sex-adjusted<sup>1</sup> death</p>"
        "<script>var x = 'hidden';</script><p>disabil­ity</p>"
    )
    collector.close()
    text = extractor._normalize("".join(collector.parts))
    assert text == "age-sex-adjusted 1 death disability"


def test__text_html_sources__cover_every_text_spec():
    assert set(extractor.TEXT_HTML_SOURCES) == {
        spec[0] for spec in extractor.TEXT_SPECS
    }
    assert set(extractor.TEXT_HTML_SOURCES.values()) <= set(
        extractor.WAYBACK_SOURCES
    )
