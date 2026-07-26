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
    "a279095c4f72c6cb7e4ed91efb2c6baff68fae928a4c437f02d8b7342db0c69e"
)
TABLE_START = (
    b"| Disclosure (certified-record source) | Classification here |\n"
)
TABLE_END = (
    b"| **Birth-timing sensitivity (amendment 2, frozen; revision 10.1 "
    b"corrects the candidate share)** \xe2\x80\x94 2,892 of 3,083 "
    b"candidates (93.8%) and 1,440 of 1,514 baseline included claimants "
    b"carry age-derived birth years (\xc2\xa73.1 clauses 2 and 3: 2,806 "
    b"inferred + 86 derived); coherent \xc2\xb11 stress scenarios through "
    b"the production ledger: births\xe2\x88\x921 \xe2\x86\x92 "
    b"\xe2\x88\x92$30.3B (\xe2\x88\x920.92%), births+1 \xe2\x86\x92 "
    b"\xe2\x88\x92$312.6B (\xe2\x88\x929.47%) of the $3,301.7B baseline, "
    b"dominated by 278 modeled-award chronology movers; adversarial "
    b"per-person range \xe2\x89\x88[\xe2\x88\x92$408.2B, +$65.2B]. Stress "
    b"scenarios, not bounds. v1 recomputes them per draw (reduction-stage "
    b"arithmetic) and publishes across-draw mean and SD; **this row travels "
    b"with every publication of these numbers until a ratified birth-timing "
    b"resolution retires it by amendment** | material \xe2\x80\x94 the "
    b"report's largest quantified sensitivity; every underlying flip is "
    b"`modeled_award` (the artifact measures `opening_backfill` immunity: "
    b"the birth year cancels in the chronology predicate) |\n"
)


def _gap_table_bytes(document: bytes) -> bytes:
    start = document.index(TABLE_START)
    end = document.index(TABLE_END, start) + len(TABLE_END)
    return document[start:end]


def test__gap_block_fixture__is_literal_and_matches_frozen_design_bytes():
    fixture = FIXTURE_PATH.read_bytes()

    assert hashlib.sha256(fixture).hexdigest() == EXPECTED_FIXTURE_SHA256
    assert len(fixture.splitlines()) == 34
    assert fixture == _gap_table_bytes(DESIGN_PATH.read_bytes())
    rows = tuple(
        dict(
            zip(
                ("disclosure", "classification"),
                line.removeprefix("| ").removesuffix(" |").split(" | ", 1),
                strict=True,
            )
        )
        for line in fixture.decode().splitlines()[2:]
    )
    assert publication.GAP_BLOCK == rows


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
        "**material** — directly motivates the §5 precedence law and the "
        "`di_unknown` class"
    )
    assert f9 == (
        "inapplicable — household composition fields are not consumed by "
        "this report"
    )
    assert by_disclosure["M4 is not DI adjudication"] == (
        "material — DI out of scope"
    )
