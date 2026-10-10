"""Artifact invariants for the supplied Supplement 2026 claiming reference."""

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.claiming import load_claim_age_reference

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "data" / "external"
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location(
    "extract_ssa_claim_ages_2026",
    SCRIPT_DIR / "extract_ssa_claim_ages_2026.py",
)
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)

FILE_SHA256 = (
    "1721f82ae6bc865a1e19f22a9578963032e7b30da9ba3f6f53448ab49fd17210"
)


def test_pins_and_offline_reparse():
    """Exact captures and every rebuilt output match committed bytes."""
    outputs = extract.build()
    for path, raw in outputs.items():
        assert path.read_bytes() == raw
    assert hashlib.sha256(outputs[extract.OUT_PATH]).hexdigest() == FILE_SHA256
    for edition, digest in extract.SOURCE_SHA256.items():
        assert (
            hashlib.sha256(extract.read_source(edition)).hexdigest() == digest
        )


def test_schema_coverage_and_existing_loader():
    ref = load_claim_age_reference(extract.OUT_PATH)
    assert ref.schema_version == "ssa_claim_ages.v1"
    assert ref.supplement_year == 2026
    assert ref.years() == list(range(1998, 2026))
    assert ref.raw_columns == extract.RAW_COLUMNS
    assert ref.collapsed_categories == extract.COLLAPSED_CATEGORIES
    for sex in ("male", "female"):
        for year in ref.years():
            row = ref.row(sex, year)
            assert sum(row["categories"].values()) == pytest.approx(
                row["component_sum"]
            )
            assert row["residual"] == pytest.approx(
                row["component_sum"] - row["published_total"]
            )
            assert abs(row["residual"]) <= ref.validation["sum_tolerance"]
            assert (
                row["fra_at"]["share"]
                <= row["categories"][f"age{row['fra_at']['at_age']}"]
            )
            assert row["applicable_raw_columns"] == [
                key for key, value in row["raw"].items() if value is not None
            ]


def test_differential_position_parser():
    """Header-keyed parser equals independent positional source extraction."""
    raw = extract.read_source(2026)
    text = raw.decode()
    start = text.index('id="table6.b5.1"')
    table = text[start : text.index("</table>", start)]
    source_rows = re.findall(
        r'<th class="stub0"[^>]*>(\d{4})</th>(.*?)</tr>', table, re.S
    )
    document = json.loads(extract.OUT_PATH.read_text())
    assert len(source_rows) == 56
    for index, (year, body) in enumerate(source_rows):
        sex = "male" if index < 28 else "female"
        tokens = re.findall(r"<td[^>]*>(.*?)</td>", body, re.S)
        tokens = [" ".join(html.unescape(t).split()) for t in tokens]
        assert len(tokens) == 15
        row = document["data"][sex][year]
        assert row["number_thousands"] == int(tokens[0].replace(",", ""))
        assert row["average_age"] == float(tokens[1])
        assert row["published_total"] == float(tokens[2])
        assert list(row["raw"].values()) == [
            None if token == ". . ." else float(token) for token in tokens[3:]
        ]


@pytest.mark.parametrize(
    "old,new,error",
    [
        ('id="table6.b5.1"', 'id="missing"', "boundaries"),
        (">Year of entitlement<", ">Changed column<", "layout"),
        ('id="c3"', 'id="c2"', "layout"),
        ('id="c4"', 'id="c20"', "layout"),
        (
            'headers="r1 r2 c3">63.4<',
            'headers="r1 r2 c3">NaN<',
            "Unrecognized",
        ),
        (
            'headers="r1 r2 c3">63.4<',
            'headers="r1 r2 c3">Infinity<',
            "Unrecognized",
        ),
        (
            'headers="r1 r2 c3">63.4<',
            'headers="r1 r2 c3">. . .<',
            "Missing average",
        ),
        ('id="r1">Men<', 'id="r1">Unknown<', "sex panel"),
        ('headers="r1 r2 c2"', 'headers="r1 r2 absent"', "cell header"),
        ('headers="r1 r2 c3"', 'headers="r1 r2 c2"', "Duplicate cell"),
        ('headers="r1 c1">1999<', 'headers="r1 c1">1998<', "Duplicate male"),
        (
            'headers="r1 r2 c4 c6">50.8<',
            'headers="r1 r2 c4 c6">bad<',
            "Unrecognized",
        ),
        (
            'headers="r1 r2 c4 c6">50.8<',
            'headers="r1 r2 c4 c6">101.0<',
            "outside",
        ),
    ],
)
def test_changed_source_layout_refused(old, new, error):
    raw = extract.read_source(2026)
    # Replace only inside the selected table, since section 6.B reuses ids.
    start = raw.index(b'id="table6.b5.1"')
    prefix, selected = raw[:start], raw[start:]
    assert old.encode() in selected
    changed = prefix + selected.replace(old.encode(), new.encode(), 1)
    with pytest.raises(ValueError, match=error):
        extract.parse_table(changed, 2026)


def test_source_tampering_refused(tmp_path):
    (tmp_path / "supplement_2026_6b.html").write_bytes(b"INVENTED BAD CAPTURE")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        extract.read_source(2026, tmp_path)


def test_missing_published_cell_refused():
    raw = extract.read_source(2026)
    start = raw.index(b'id="table6.b5.1"')
    prefix, selected = raw[:start], raw[start:]
    cell = b'<td headers="r1 r2 c3">63.4</td>'
    assert cell in selected
    changed = prefix + selected.replace(cell, b"", 1)
    with pytest.raises(ValueError, match="Missing published"):
        extract.parse_table(changed, 2026)


@settings(max_examples=60, deadline=None)
@given(
    st.lists(
        st.one_of(st.none(), st.integers(0, 1000)), min_size=12, max_size=12
    )
)
def test_collapsing_preserves_partition(values):
    """INVENTED tenths: collapsing age65/66 preserves all component mass."""
    raw = {
        name: None if value is None else value / 10
        for name, value in zip(extract.RAW_COLUMNS, values, strict=True)
    }
    collapsed = extract._collapse(raw)
    expected_tenths = sum(value or 0 for value in values)
    assert sum(collapsed.values()) == pytest.approx(expected_tenths / 10)
    assert collapsed["age65"] == pytest.approx(
        sum(v or 0 for v in values[3:6]) / 10
    )
    assert collapsed["age66"] == pytest.approx(
        sum(v or 0 for v in values[6:9]) / 10
    )
