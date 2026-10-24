"""Invented numeric/HTML fixtures only; no published statistical values."""

from dataclasses import replace
from decimal import Decimal
from hashlib import sha256

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.aggregate_tables import (
    AggregateCell,
    CaptureMismatchError,
    TableSpec,
    TableStructureError,
    expand_html_table,
    parse_html,
    parse_number,
    parse_ssa_4b,
    read_verified,
    verify_payload,
)

INVENTED_MERGED_HTML = b"""
<table><thead>
<tr><th rowspan=2>Year</th><th colspan=2>Amounts<sup>a</sup></th></tr>
<tr><th>Total</th><th>Part</th></tr></thead>
<tbody><tr><th>2001</th><td>1,234<sup>7</sup></td><td>(D)</td>
</tr></tbody></table>
"""


@settings(deadline=None)
@given(
    st.integers(min_value=-(10**15), max_value=10**15),
    st.sampled_from(["a", "b", "*", "†", "‡", "[1]", "¹", "(2)"]),
    st.sampled_from([",", " ", "\u00a0", "\u202f"]),
)
def test_invented_separators_and_flags_preserve_number(value, flag, separator):
    decorated = format(value, ",").replace(",", separator) + flag
    assert parse_number(decorated).value == Decimal(value)


@settings(deadline=None)
@given(
    st.sampled_from(
        ["", "...", "…", "--", "—", "(D)", "(X)", "N/A", "ND", "None", "*"]
    )
)
def test_invented_missing_markers_never_become_zero(marker):
    parsed = parse_number(marker)
    assert parsed.value is None
    assert parsed.footnote_flags


@settings(deadline=None)
@given(st.decimals(min_value=-(10**6), max_value=10**6, places=2))
def test_invented_decimal_separators_preserve_magnitude(value):
    decorated = format(value, ",.2f") + "[a]"
    assert parse_number(decorated).value == value


@pytest.mark.parametrize(
    "token", ["1,23", "1,,234", "unexpected", "1.2.3", "(-1)", "1$2", "1%2"]
)
def test_invented_unrecognized_numbers_refuse_without_echo(token):
    with pytest.raises(
        TableStructureError, match="^Unrecognized numeric cell$"
    ):
        parse_number(token)


def test_invented_negative_parentheses_and_decimal_fraction():
    assert parse_number("(1,234.50)").value == Decimal("-1234.50")
    assert parse_number(".25").value == Decimal(".25")
    assert parse_number("123.").value == Decimal(123)
    assert parse_number("(D)[a]").value is None
    assert parse_number("($1,234.50)").value == Decimal("-1234.50")
    assert parse_number("-$1,234.50").value == Decimal("-1234.50")
    assert parse_number("12.5%").value == Decimal("12.5")


def test_invented_merged_headers_and_numeric_superscript():
    table = parse_html(INVENTED_MERGED_HTML).find("table")
    grid = expand_html_table(table)
    assert len(grid) == 3
    assert {len(row) for row in grid} == {3}
    assert grid[0][1] == grid[0][2]
    assert grid[0][0] == grid[1][0]
    assert grid[0][1].flags == ("a",)
    assert grid[2][1].flags == ("7",)
    assert parse_number(grid[2][1].text).value == Decimal(1234)
    assert parse_number(grid[2][2].text).value is None


@settings(deadline=None)
@given(st.integers(1, 12), st.integers(1, 12))
def test_invented_merged_header_expands_to_rectangle(rows, columns):
    html = (
        f'<table><tr><th rowspan="{rows}" colspan="{columns}">Label</th>'
        "</tr>" + "<tr></tr>" * (rows - 1) + "</table>"
    )
    grid = expand_html_table(parse_html(html).find("table"))
    assert len(grid) == rows
    assert all(len(row) == columns for row in grid)
    assert all(cell.text == "Label" for row in grid for cell in row)


def test_invented_capture_mismatch_refuses_before_parsing(tmp_path):
    payload = b"INVENTED_CAPTURE"
    path = tmp_path / "invented.html"
    path.write_bytes(payload)
    spec = TableSpec(
        "invented",
        "Invented publisher",
        "invented",
        "https://example.test",
        "invented.html",
        sha256(payload).hexdigest(),
        len(payload),
        "2001-01-01T00:00:00Z",
        ("usd",),
        (2001,),
        ("Invented",),
        "ssa_4b",
        "invented",
        selector={"id": "invented"},
    )
    assert read_verified(spec, tmp_path) == payload
    with pytest.raises(
        CaptureMismatchError, match="Capture identity mismatch"
    ):
        read_verified(replace(spec, sha256="0" * 64), tmp_path)
    with pytest.raises(
        CaptureMismatchError, match="Capture identity mismatch"
    ):
        parse_ssa_4b(spec, payload + b"CHANGED")
    with pytest.raises(CaptureMismatchError, match="escapes root"):
        read_verified(replace(spec, capture_file="../invented.html"), tmp_path)


def test_invented_cell_representations_hide_values():
    cell = AggregateCell(
        "invented", "row", "column", 2001, "usd", Decimal(987654)
    )
    assert "987654" not in repr(cell)
    assert "987654" not in repr(parse_number("987654"))


@settings(deadline=None)
@given(st.binary(min_size=1, max_size=512))
def test_invented_same_size_mutation_always_refuses(payload):
    spec = TableSpec(
        "invented",
        "Invented",
        "invented",
        "https://example.test",
        "invented.bin",
        sha256(payload).hexdigest(),
        len(payload),
        "2001-01-01T00:00:00Z",
        ("usd",),
        (2001,),
        ("Invented",),
        "invented",
        "invented",
    )
    verify_payload(spec, payload)
    changed = bytes([payload[0] ^ 1]) + payload[1:]
    with pytest.raises(
        CaptureMismatchError, match="Capture identity mismatch"
    ):
        verify_payload(spec, changed)
