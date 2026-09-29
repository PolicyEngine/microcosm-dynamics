"""Pin the corrected provenance of two replication anchors (issue #488).

Two anchors carried the wrong model label, and the erratum
docs/errata/2026-09-29-anchor-provenance.md corrects them:

* Mermin (2005), Urban 411260, Table 1: the "75-year deficit/surplus
  (percentage of taxable payroll)" row is Congressional Budget Office
  (2005) estimates as Mermin reports them, not DYNASIM3 Runid 432 output
  (the table's benefit rows are DYNASIM3's). It anchors cost-ordering T2.
* Smith/Johnson/Favreault (2020), Urban 103050, Tables 3 and 15: DYNASIM4
  ID980, not DYNASIM3 ID980. Table 3 anchors cost-ordering T3; Table 15
  anchors the caregiver replication.

The pins below fail on the pre-erratum strings. Committed evidence
artifacts keep their original labels (they are never edited in place);
the erratum governs them, so this module reads no committed evidence.

The erratum's verbatim source quotes are checked against the archived
source texts when those are staged locally; otherwise that one check
skips.
"""

from __future__ import annotations

import hashlib
import importlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ERRATUM = ROOT / "docs" / "errata" / "2026-09-29-anchor-provenance.md"
SOURCE_TEXTS = Path("~/PolicyEngine/dynasim-refs").expanduser()

# ---------------------------------------------------------------------
# The corrected strings, pinned exactly.
# ---------------------------------------------------------------------
EXPECTED_MERMIN_ANCHOR_CITE = (
    "Congressional Budget Office (2005) estimates as reported in Mermin "
    "(2005), Urban Institute 411260, Table 1 ('Annual Mean Social Security "
    "Benefits at Ages 62 to 67, by Policy Scenario'), '75-year "
    "deficit/surplus (percentage of taxable payroll)' row -- CBO's "
    "estimates, not DYNASIM3 output (the table's benefit rows are DYNASIM3, "
    "Runid: 432); verified against 411260-benefit-reductions.{txt,pdf} "
    "PDF p.15, narrative printed p.5-6"
)
EXPECTED_CAREGIVER_ANCHOR_CITE = (
    "Smith/Johnson/Favreault (2020), Urban Institute 103050, DYNASIM4 "
    "ID980, Table 3 (actuarial balance as a percentage of taxable payroll, "
    "2019-93), 'Provide caregiver credits' row; verified against "
    "103050-five-dem.{txt,pdf} printed p.19 (PDF p.29)"
)
EXPECTED_CAREGIVER_PAPER = (
    "Smith, K. E., Johnson, R. W. and Favreault, M. M. (2020). Five "
    "Democratic Approaches to Social Security Reform: Estimated Impact of "
    "Plans from the 2020 Presidential Campaign. The Urban Institute "
    "(report 103050). DYNASIM4, ID980. 2019 Trustees intermediate "
    "assumptions."
)
EXPECTED_TABLE15_CITATION = (
    "Table 15 (Percentage of Benefit Increases Going to the Bottom Fifth "
    "of Lifetime Earners, 2065), printed p. 66, 'Create caregiver credit' "
    "row, scheduled scenario; DYNASIM4 ID980 (the table's own source line "
    "reads 'Source: DYNASIM ID980.'; the report's analysis is based on "
    "DYNASIM4)"
)
EXPECTED_MERMIN_TABLE1_CITATION = (
    "Table 1 (PDF p.15); 2050 row of the percent-of-scheduled block, "
    "DYNASIM3 Runid 432. seventy_five_year_payroll_pct is the table's "
    "75-year deficit/surplus row: Congressional Budget Office (2005) "
    "estimates as reported in Mermin (2005), not DYNASIM3 output"
)

# ---------------------------------------------------------------------
# The pre-erratum labels that must not come back.
# ---------------------------------------------------------------------
OLD_MERMIN_CITE_PREFIX = (
    "Mermin (2005), Urban Institute 411260, DYNASIM3 Runid 432, Table 1"
)
OLD_MERMIN_TABLE1_CITATION = "Table 1 (printed p., DYNASIM3 Runid 432)"
OLD_FIVE_APPROACHES_LABELS = ("DYNASIM3 ID980", "DYNASIM3, ID980")
OLD_FIVE_APPROACHES_SUBTITLE = "Plans by 2020 Presidential Candidates"
OLD_T2_SWAP_WORDING = "versus DYNASIM's fuller projected careers"
OLD_PAPER_WORDING = "DYNASIM ranks them the other way"

# ---------------------------------------------------------------------
# The erratum's verbatim quotes: (source file, first line, last line).
# ---------------------------------------------------------------------
EXPECTED_QUOTE_RANGES = {
    ("411260-benefit-reductions.txt", 212, 214),
    ("411260-benefit-reductions.txt", 231, 233),
    ("411260-benefit-reductions.txt", 514, 521),
    ("103050-five-dem.txt", 11, 13),
    ("103050-five-dem.txt", 330, 331),
    ("103050-five-dem.txt", 906, 906),
    ("103050-five-dem.txt", 1052, 1052),
    ("103050-five-dem.txt", 3299, 3299),
}
#: Key sentences the erratum must carry verbatim (checked without the
#: staged sources; the staged check below proves them exact).
KEY_SOURCE_SENTENCES = (
    "The last row of table 1 presents Congressional Budget Office (CBO) "
    "estimates of the",
    "Source : Author's calculations from DYNASIM3 (Runid: 432) and the "
    "Congressional Budget Office (2005).",
    "Source: DYNASIM4 ID980.",
    "Source: DYNASIM ID980.",
    "Our analysis of the candidates’ Social Security reform proposals "
    "is based on DYNASIM4.",
)
#: The one inline (non-block) quote: Mermin's statement of his model.
INLINE_QUOTE = (
    "411260-benefit-reductions.txt",
    127,
    "are based on the Urban Institute’s DYNASIM3 model",
)
QUOTE_BLOCK = re.compile(
    r"`(?P<file>[\w.-]+\.txt)` lines? (?P<start>\d+)(?:–(?P<end>\d+))?"
    r"[^\n]*:\n\n```text\n(?P<body>.*?)\n```",
    re.DOTALL,
)
HASH_ROW = re.compile(r"\| `(?P<file>[\w.-]+)` \| `(?P<sha>[0-9a-f]{64})` \|")
#: Every archived source the erratum hashes (the quoted texts and PDFs).
HASHED_SOURCES = (
    "411260-benefit-reductions.txt",
    "411260-benefit-reductions.pdf",
    "103050-five-dem.txt",
    "103050-five-dem.pdf",
)


def _script(name: str):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module(name)


def _erratum() -> str:
    return ERRATUM.read_text(encoding="utf-8")


def _quote_blocks() -> dict[tuple[str, int, int], str]:
    blocks = {}
    for match in QUOTE_BLOCK.finditer(_erratum()):
        start = int(match["start"])
        end = int(match["end"] or start)
        blocks[(match["file"], start, end)] = match["body"]
    return blocks


def _source_lines(name: str) -> list[str]:
    return (SOURCE_TEXTS / name).read_text(encoding="utf-8").split("\n")


# =====================================================================
# Corrected strings in the scripts
# =====================================================================
def test_cost_ordering_mermin_cite_attributes_the_deficit_row_to_cbo():
    cite = _script("replication_cost_ordering").MERMIN_ANCHOR_CITE
    assert cite == EXPECTED_MERMIN_ANCHOR_CITE
    assert cite.startswith("Congressional Budget Office (2005) estimates")
    assert "not DYNASIM3 output" in cite
    assert OLD_MERMIN_CITE_PREFIX not in cite


def test_cost_ordering_caregiver_cite_reads_dynasim4():
    cite = _script("replication_cost_ordering").CAREGIVER_ANCHOR_CITE
    assert cite == EXPECTED_CAREGIVER_ANCHOR_CITE
    assert "DYNASIM4 ID980" in cite
    assert "DYNASIM3" not in cite


def test_t2_swap_named_delta_names_the_cbo_anchor():
    deltas = _script("replication_cost_ordering")._named_deltas()
    (swap,) = [d for d in deltas if d.startswith("PPI/NRA ordering driver")]
    assert "the anchor is CBO's 2005 75-year estimates" in swap
    assert "PPI 81.8, NRA 85.2" in swap
    assert OLD_T2_SWAP_WORDING not in swap


def test_caregiver_paper_and_table15_citation_read_dynasim4():
    prov = _script("replication_caregiver").anchor_provenance()
    assert prov["paper"] == EXPECTED_CAREGIVER_PAPER
    table15 = prov["table15_bottom_fifth_2065"]["citation"]
    assert table15 == EXPECTED_TABLE15_CITATION
    for text in (prov["paper"], table15):
        assert "DYNASIM3" not in text
    assert OLD_FIVE_APPROACHES_SUBTITLE not in prov["paper"]


def test_mermin_rows_table1_citation_names_cbo_for_the_payroll_row():
    mermin_rows = _script("replication_mermin_rows")
    block = mermin_rows.anchor_provenance()["table1_ages_62_67_by_year"]
    assert block["citation"] == EXPECTED_MERMIN_TABLE1_CITATION
    assert OLD_MERMIN_TABLE1_CITATION not in block["citation"]
    assert (
        block["seventy_five_year_payroll_pct"]
        is mermin_rows.ANCHOR_TABLE1_PAYROLL_PCT
    )


def test_no_prose_or_code_outside_the_erratum_repeats_an_old_label():
    candidates = [
        *sorted((ROOT / "scripts").rglob("*.py")),
        *sorted((ROOT / "src").rglob("*.py")),
        *sorted((ROOT / "paper").glob("*.qmd")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "docs").rglob("*.bib")),
    ]
    old_labels = (
        *OLD_FIVE_APPROACHES_LABELS,
        OLD_FIVE_APPROACHES_SUBTITLE,
        OLD_MERMIN_CITE_PREFIX,
        OLD_MERMIN_TABLE1_CITATION,
        OLD_T2_SWAP_WORDING,
        OLD_PAPER_WORDING,
    )
    hits = [
        f"{path.relative_to(ROOT)}: {label}"
        for path in candidates
        if path != ERRATUM
        for label in old_labels
        if label in path.read_text(encoding="utf-8")
    ]
    assert not hits, hits


# =====================================================================
# The erratum
# =====================================================================
def test_erratum_quotes_the_expected_source_lines():
    blocks = _quote_blocks()
    assert set(blocks) == EXPECTED_QUOTE_RANGES
    text = _erratum()
    for sentence in KEY_SOURCE_SENTENCES:
        assert sentence in text, sentence
    assert f'"{INLINE_QUOTE[2]}" (line {INLINE_QUOTE[1]})' in text
    hashed = [m["file"] for m in HASH_ROW.finditer(text)]
    assert sorted(hashed) == sorted(HASHED_SOURCES)


def test_erratum_names_the_committed_artifacts_and_unchanged_results():
    text = _erratum()
    for artifact in (
        "replication_cost_ordering_v1.json`",
        "replication_caregiver_v1.json`",
        "replication_mermin_rows_v1.json`",
        "`benchmarks/registry.json`",
        "`benchmarks/history.jsonl`",
    ):
        assert artifact in text, artifact
    assert "this erratum governs" in text
    assert "`dynasim.mermin.four_reform_cost_ordering`" in text
    assert "T1 sign agreement 100% (forecast 100%, met)" in text
    assert "T2 Kendall tau 0.667 against the CBO column" in text
    assert "(forecast 1.0, not met)" in text
    assert "T3 Kendall tau 0.913 against the DYNASIM4 Table 3 row" in text
    assert "it was not blind" in text


@pytest.mark.skipif(
    not all((SOURCE_TEXTS / name).is_file() for name in HASHED_SOURCES),
    reason="archived source texts not staged",
)
def test_erratum_quotes_match_the_staged_sources_exactly():
    for (name, start, end), body in _quote_blocks().items():
        expected = "\n".join(_source_lines(name)[start - 1 : end])
        assert body == expected, (name, start, end)
    name, line, fragment = INLINE_QUOTE
    assert fragment in _source_lines(name)[line - 1]
    for match in HASH_ROW.finditer(_erratum()):
        digest = hashlib.sha256(
            (SOURCE_TEXTS / match["file"]).read_bytes()
        ).hexdigest()
        assert digest == match["sha"], match["file"]
