"""Real capture checks; invented data remain in test_aggregate_numbers.

Only public aggregate captures under data/external are read. Numeric
comparisons return booleans so failures disclose labels and structure only.
"""

import re
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest

from populace_dynamics.income_resources.aggregate_tables import (
    load_registry,
    parse_table,
    read_verified,
)

ARTIFACT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIRECTORY = ARTIFACT_ROOT / "data" / "external"
SSA_IDS = tuple(f"ssa_2025_4b{suffix}" for suffix in (1, 2, 10, 11))


def _quiet_equal(left, right):
    return left == right


class _IndependentBodyReader(HTMLParser):
    """Independent streaming extraction; no span expansion or number parser."""

    def __init__(self, section_id):
        super().__init__()
        self.section_id = section_id
        self.active = False
        self.body = False
        self.cell = False
        self.sup = False
        self.rows = []
        self.row = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == "div" and dict(attrs).get("id") == self.section_id:
            self.active = True
        if self.active and tag == "tbody":
            self.body = True
        if self.body and tag == "tr":
            self.row = []
        if self.body and tag in {"th", "td"}:
            self.cell = True
            self.text = []
        if tag == "sup":
            self.sup = True

    def handle_data(self, data):
        if self.cell and not self.sup:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "sup":
            self.sup = False
        if self.body and tag in {"th", "td"}:
            self.row.append("".join(self.text).strip())
            self.cell = False
        if self.body and tag == "tr":
            self.rows.append(self.row)
        if tag == "tbody":
            self.body = False
        if tag == "div":
            self.active = False


@pytest.mark.parametrize("table_id", SSA_IDS)
def test_real_ssa_shapes_labels_years_and_units(table_id):
    spec = load_registry()[table_id]
    cells = parse_table(spec)
    expected = {
        "ssa_2025_4b1": (78, 8),
        "ssa_2025_4b2": (74, 12),
        "ssa_2025_4b10": (55, 9),
        "ssa_2025_4b11": (78, 9),
    }
    rows, columns = expected[table_id]
    assert len(cells) == rows * columns
    assert len({c.column_key for c in cells}) == columns
    assert {c.year for c in cells} == set(spec.years)
    assert {c.unit for c in cells} == set(spec.units)
    assert all(c.column_key and c.row_key for c in cells)
    assert any("Number" in c.column_key for c in cells)
    if table_id == "ssa_2025_4b10":
        assert {c.row_key for c in cells} == set(spec.geography)
    else:
        assert "2024" in {c.row_key for c in cells}
    assert any(c.footnote_flags for c in cells)


@pytest.mark.parametrize("table_id", SSA_IDS)
def test_real_ssa_cells_match_independent_raw_html(table_id):
    spec = load_registry()[table_id]
    reader = _IndependentBodyReader(spec.selector["id"])
    reader.feed(read_verified(spec).decode())
    parsed = parse_table(spec)
    width = len(spec.selector["column_units"])
    for ri, row in enumerate(reader.rows):
        for ci, raw in enumerate(row[1:]):
            token = re.sub(r"[\s,]", "", raw)
            if re.fullmatch(r"\d+(?:\.\d+)?", token):
                matches = _quiet_equal(
                    parsed[ri * width + ci].value, Decimal(token)
                )
                if not matches:
                    pytest.fail(
                        f"Raw-cell differential failed: {table_id} {row[0]} column {ci}",
                        pytrace=False,
                    )


@pytest.mark.parametrize("table_id", ("ssa_2025_4b10", "ssa_2025_4b11"))
def test_real_ssa_taxable_earnings_components_reconcile(table_id):
    cells = parse_table(table_id)
    # Workers overlap across employment types; only earnings are additive.
    for start in range(0, len(cells), 9):
        row = cells[start : start + 9]
        group = row[3:6]
        if all(c.value is not None for c in group):
            within_rounding = abs(
                group[0].value - group[1].value - group[2].value
            ) <= Decimal(1)
            if not within_rounding:
                pytest.fail(
                    f"Earnings identity failed: {table_id} {row[0].row_key}",
                    pytrace=False,
                )


def test_real_ssa_shared_capture_is_reused_and_has_expected_role():
    registry = load_registry()
    assert len({registry[k].capture_file for k in SSA_IDS}) == 1
    assert "ssa_level_anchors_vintage1" in registry[SSA_IDS[0]].capture_file
    assert (
        registry["ssa_2025_4b10"].role
        == "gate_truth_ce_g_state_cells_if_ir0_powered"
    )


def test_all_registry_files_match_pinned_hash_and_size():
    registry = load_registry()
    assert registry
    assert ARTIFACT_DIRECTORY.is_dir()
    for spec in registry.values():
        read_verified(spec)
        assert spec.publisher and spec.edition and spec.url
        assert spec.retrieved_at.endswith("Z")
        assert spec.role and spec.parser


def test_all_registry_metadata_matches_capture_manifest():
    directory = ARTIFACT_DIRECTORY / "snapshots" / "income_resources_d4_v1"
    records = {}
    source_url = None
    for line in (directory / "capture_manifest.txt").read_text().splitlines():
        if line.startswith("#"):
            match = re.search(r"https?://\S+", line)
            if match:
                source_url = match[0]
        elif line.strip():
            timestamp, digest, size, filename = line.split()
            path = (directory / filename).resolve()
            assert path not in records, "Capture manifest repeats a file"
            records[path] = (timestamp, digest, int(size), source_url)
    for spec in load_registry().values():
        path = (ARTIFACT_ROOT / spec.capture_file).resolve()
        assert path in records, f"Missing manifest record: {spec.identifier}"
        matches = records[path] == (
            spec.retrieved_at,
            spec.sha256,
            spec.byte_size,
            spec.url.split("#")[0],
        )
        assert matches, f"Manifest metadata differs: {spec.identifier}"
