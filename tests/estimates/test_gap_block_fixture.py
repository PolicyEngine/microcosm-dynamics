"""Byte-exact fixture guard for the currently frozen section 10 gap block."""

from __future__ import annotations

import hashlib
from pathlib import Path

from populace_dynamics.estimates import publication

REPOSITORY_ROOT = Path(__file__).parents[2]
DESIGN_PATH = REPOSITORY_ROOT / "docs/design/first_estimates_report.md"
FIXTURE_PATH = (
    REPOSITORY_ROOT / "tests/fixtures/first_estimates_gap_block_v1.md"
)
EXPECTED_FIXTURE_SHA256 = (
    "e499a338a6de3b92e8e795cb89dadabbeb23036064b5c642461d5a42a032ace0"
)
TABLE_START = (
    b"| Disclosure (certified-record source) | Classification here |\n"
)
TABLE_END = (
    b"| Levels unanchored \xe2\x80\x94 no committed annual SSA level series | "
    b"material; the registered anchor extraction is the successor step |\n"
)


def _gap_table_bytes(document: bytes) -> bytes:
    start = document.index(TABLE_START)
    end = document.index(TABLE_END, start) + len(TABLE_END)
    return document[start:end]


def test__gap_block_fixture__is_literal_and_matches_frozen_design_bytes():
    fixture = FIXTURE_PATH.read_bytes()

    assert hashlib.sha256(fixture).hexdigest() == EXPECTED_FIXTURE_SHA256
    assert fixture == _gap_table_bytes(DESIGN_PATH.read_bytes())


def test__gap_block__matches_current_three_semantic_corrections():
    by_disclosure = {
        row["disclosure"]: row["classification"]
        for row in publication.GAP_BLOCK
    }

    f4 = next(
        value
        for disclosure, value in by_disclosure.items()
        if disclosure.startswith("F4 —")
    )
    f9 = next(
        value
        for disclosure, value in by_disclosure.items()
        if disclosure.startswith("F9 —")
    )
    assert f4 == (
        "material — directly motivates the §5 precedence law and the "
        "di_unknown class"
    )
    assert f9 == (
        "inapplicable — household composition fields are not consumed by "
        "this report"
    )
    assert by_disclosure["M4 is not DI adjudication"] == (
        "material — DI out of scope"
    )
