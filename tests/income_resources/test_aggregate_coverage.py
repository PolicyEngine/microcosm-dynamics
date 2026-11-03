"""Coverage references from data/external; all table fixtures are invented.

The public references are checked against their pinned raw HTML. Census
requests were refused, so these tests establish parser behavior using
INVENTED payloads and make no assertion about published Census totals.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.aggregate_coverage import (
    parse_census,
    parse_coverage,
    parse_reference,
    read_reference,
)
from populace_dynamics.income_resources.aggregate_tables import (
    CaptureMismatchError,
    TableSpec,
    TableStructureError,
    load_registry,
    read_verified,
)

INVENTED_CSV = (
    b"state,year,total,active,inactive\n"
    b'Invented State,2025,"1,500",1000,500\n'
    b"Invented Other,2025,(D),NA,0\n"
)
INVENTED_HTML = b"""<table id="invented-membership">
<tr><th rowspan="2">State</th><th colspan="2">Membership<sup>b</sup></th></tr>
<tr><th>Active</th><th>Inactive</th></tr>
<tr><th>Invented State<sup>r</sup></th><td>1,200<sup>a</sup></td><td>(D)</td></tr>
</table>"""
INVENTED_REFERENCE = b"""<div class="poms">
<h1>INVENTED coverage guidance</h1>
<div class="poms-subsection1"><div class="poms-subsection1-title">
<h2>A. Invented authority</h2></div>
<div class="poms-subsection1-body"><p>Invented State (1-2-2000).</p>
<p>Permission is not observed membership.</p></div></div></div>"""
REFERENCE_IDS = tuple(
    sorted(
        key
        for key, spec in load_registry().items()
        if spec.parser == "coverage_reference"
    )
)


def _check(condition, message):
    if not condition:
        pytest.fail(message, pytrace=False)


def _read_real_reference(spec):
    error = False
    result = None
    try:
        result = read_reference(spec)
    except Exception:
        error = True
    _check(not error, "Pinned reference has its adjudicated structure")
    return result


def _invented_spec(payload, parser="census", selector=None):
    return TableSpec(
        identifier="INVENTED_membership",
        publisher="Invented publisher",
        edition="Invented 2025",
        url="https://example.invalid/INVENTED",
        capture_file="INVENTED_not_a_real_capture",
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_size=len(payload),
        retrieved_at="2026-10-24T00:00:00Z",
        units=("members",),
        years=(2025,),
        geography=("Invented State", "Invented Other"),
        parser=parser,
        role="INVENTED fixture",
        selector=selector or {},
    )


def _invented_csv_spec(payload=INVENTED_CSV, format_name="csv"):
    return _invented_spec(
        payload,
        selector={
            "format": format_name,
            "row_fields": ["state"],
            "year_field": "year",
            "data_columns": [
                {"field": label, "label": label, "unit": "members"}
                for label in ["total", "active", "inactive"]
            ],
        },
    )


class _IndependentReferenceText(HTMLParser):
    """Locate subsection bodies directly in the raw HTML token stream."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.current = []
        self.texts = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif dict(attrs).get("class") == "poms-subsection1-body":
                self.depth = 1
                self.current = []

    def handle_data(self, text):
        if self.depth:
            self.current.append(text)

    def handle_endtag(self, tag):
        if tag == "div" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.texts.append(" ".join(" ".join(self.current).split()))


@pytest.mark.parametrize("identifier", REFERENCE_IDS)
def test_real_reference_capture_identity_and_structure(identifier):
    spec = load_registry()[identifier]
    _check(
        Path(spec.capture_file).is_relative_to(Path("data") / "external"),
        "Reference capture stays within the public artifact directory",
    )
    payload = read_verified(spec)
    passages = _read_real_reference(spec)
    _check(bool(passages), "Reference has cited passages")
    _check(spec.units == ("cited_text",), "Reference uses cited-text units")
    _check(spec.years == (), "Reference carries no invented observation year")
    _check(
        all(
            p.table == identifier and spec.url in p.citation for p in passages
        ),
        "Reference retains its source citation",
    )
    _check(
        all(p.text not in repr(p) for p in passages),
        "Reference representation excludes body text",
    )
    independent = _IndependentReferenceText()
    independent.feed(payload.decode())
    if independent.texts:
        _check(
            [p.text for p in passages] == independent.texts,
            "Cited subsection text agrees with independent raw HTML location",
        )
    else:
        _check(
            len(passages) == 1, "Table-of-contents reference is one passage"
        )


def test_real_authority_lists_stay_cited_text():
    identifiers = ["poms_sl_30001_331", "poms_sl_30001_347"]
    for identifier in identifiers:
        spec = load_registry()[identifier]
        passages = _read_real_reference(spec)
        _check(
            any("California" in passage.text for passage in passages),
            "State authority list remains available in cited text",
        )
        with pytest.raises(TableStructureError, match="not a numeric table"):
            parse_coverage(spec, read_verified(spec))


def test_invented_csv_cells_units_years_and_components():
    cells = parse_census(_invented_csv_spec(), INVENTED_CSV)
    _check(len(cells) == 6, "Invented table has expected cell count")
    _check(
        all(c.unit == "members" and c.year == 2025 for c in cells),
        "Invented cells retain units and reference years",
    )
    _check(
        cells[0].value == cells[1].value + cells[2].value,
        "Invented total equals its components",
    )
    _check(cells[3].value is None, "Suppressed invented cell remains missing")
    _check(
        "suppressed" in cells[3].footnote_flags, "Suppression flag retained"
    )
    _check(cells[4].value is None, "Missing invented cell remains missing")
    _check(cells[5].value == Decimal(0), "Explicit invented zero stays zero")


def test_invented_csv_and_api_json_agree():
    rows = [
        ["state", "year", "total", "active", "inactive"],
        ["Invented State", "2025", "1,500", "1000", "500"],
        ["Invented Other", "2025", "(D)", "NA", "0"],
    ]
    payload = json.dumps(rows).encode()
    csv_cells = parse_census(_invented_csv_spec(), INVENTED_CSV)
    json_cells = parse_census(_invented_csv_spec(payload, "json"), payload)
    _check(csv_cells == json_cells, "Invented CSV and API JSON cells agree")


def test_invented_merged_headers_and_superscript_flags():
    spec = _invented_spec(
        INVENTED_HTML,
        "coverage",
        {
            "table_id": "invented-membership",
            "header_rows": 2,
            "year": 2025,
        },
    )
    cells = parse_coverage(spec, INVENTED_HTML)
    _check(
        [c.column_key for c in cells]
        == ["Membership | Active", "Membership | Inactive"],
        "Merged invented headers retain hierarchy",
    )
    _check(cells[0].value == Decimal(1200), "Invented separated amount parsed")
    _check(
        cells[0].footnote_flags == ("b", "r", "a"),
        "Header, row and cell superscript flags retained",
    )
    _check(cells[1].value is None, "Invented suppressed HTML stays missing")


@pytest.mark.parametrize(
    "parser", [parse_census, parse_coverage, parse_reference]
)
def test_invented_direct_parser_refuses_hash_mismatch(parser):
    spec = _invented_spec(INVENTED_CSV)
    with pytest.raises(CaptureMismatchError, match="identity mismatch"):
        parser(spec, INVENTED_CSV + b" ")


@pytest.mark.parametrize(
    "payload,selector_change",
    [
        (b"state,year,total,active\nInvented,2025,5,3\n", {}),
        (INVENTED_CSV, {"row_fields": ["absent"]}),
        (
            INVENTED_CSV,
            {
                "data_columns": [
                    {"field": "total", "label": "total", "unit": "unknown"}
                ]
            },
        ),
        (INVENTED_CSV.replace(b"2025", b"2024"), {}),
        (INVENTED_CSV.replace(b"2025", b"2025.5"), {}),
        (INVENTED_CSV.replace(b"Invented State", b" "), {}),
        (INVENTED_CSV + INVENTED_CSV.splitlines(keepends=True)[1], {}),
    ],
    ids=[
        "row-width",
        "row-field",
        "units",
        "year",
        "fractional-year",
        "blank-geography",
        "duplicate-cell",
    ],
)
def test_invented_census_schema_changes_refused(payload, selector_change):
    spec = _invented_csv_spec(payload)
    spec = replace(spec, selector=spec.selector | selector_change)
    with pytest.raises(TableStructureError):
        parse_census(spec, payload)


@settings(deadline=None)
@given(st.integers(min_value=0, max_value=10**12), st.sampled_from(["a", "†"]))
def test_invented_table_separators_and_flags_preserve_cells(amount, flag):
    payload = (
        "state,year,total,active,inactive\n"
        f'Invented State,2025,"{amount:,}{flag}",0,0\n'
    ).encode()
    cells = parse_census(_invented_csv_spec(payload), payload)
    _check(cells[0].value == Decimal(amount), "Invented cell value preserved")
    _check(cells[0].footnote_flags == (flag,), "Invented source flag retained")


@settings(deadline=None)
@given(st.sampled_from(["", "(D)", "NA", "—", "..."]))
def test_invented_missing_membership_never_becomes_zero(marker):
    payload = (
        "state,year,total,active,inactive\n"
        f"Invented State,2025,{marker},0,0\n"
    ).encode()
    cells = parse_census(_invented_csv_spec(payload), payload)
    _check(cells[0].value is None, "Invented missing cell stays missing")
    _check(
        bool(cells[0].footnote_flags), "Invented missing marker is explicit"
    )


@settings(deadline=None)
@given(st.integers(min_value=1, max_value=100000))
def test_invented_reference_dates_stay_text(year):
    payload = INVENTED_REFERENCE.replace(b"2000", str(year).encode())
    spec = replace(
        _invented_spec(payload),
        record_kind="reference",
        selector={"title": "INVENTED coverage guidance"},
    )
    passages = parse_reference(spec, payload)
    _check(len(passages) == 1, "Invented reference has one subsection")
    _check(
        f"1-2-{year}" in passages[0].text,
        "Invented authority date remains cited text",
    )
    _check(not hasattr(passages[0], "value"), "Reference has no numeric cell")


@settings(deadline=None)
@given(st.binary(min_size=1, max_size=16))
def test_invented_payload_mutations_always_refused(suffix):
    spec = _invented_spec(INVENTED_CSV)
    for parser in (parse_census, parse_coverage, parse_reference):
        with pytest.raises(CaptureMismatchError, match="identity mismatch"):
            parser(spec, INVENTED_CSV + suffix)


@settings(deadline=None)
@given(st.integers(min_value=0, max_value=10**12))
def test_invented_repeated_geography_cells_always_refused(amount):
    row = f"Invented State,2025,{amount},0,0\n"
    payload = ("state,year,total,active,inactive\n" + row + row).encode()
    with pytest.raises(TableStructureError, match="Duplicate Census cell"):
        parse_census(_invented_csv_spec(payload), payload)


@settings(deadline=None)
@given(st.sampled_from(["c", "†", "‡"]))
def test_invented_merged_header_flags_reach_each_child(flag):
    payload = INVENTED_HTML.replace(
        b"<sup>b</sup>", f"<sup>{flag}</sup>".encode()
    )
    spec = _invented_spec(
        payload,
        "coverage",
        {
            "table_id": "invented-membership",
            "header_rows": 2,
            "year": 2025,
        },
    )
    cells = parse_coverage(spec, payload)
    _check(
        all(flag in cell.footnote_flags for cell in cells),
        "Invented merged header flags reach both child columns",
    )
