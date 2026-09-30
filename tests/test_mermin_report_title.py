"""Pin the corrected title of Mermin (2005), Urban Institute report 411260.

The replication scripts and the benchmark source-capture request called
the report "The Effect of Benefit Reductions on the Distribution of Social
Security Benefits". Its title page, its PDF metadata and Urban's landing
page all read "Distributional Effects of Reforming Social Security through
Benefit Reductions". The erratum
docs/errata/2026-09-30-mermin-report-title.md corrects the title.

Several tests fail on the pre-erratum strings: the script and docstring
pins, the capture-request pin and the repository scan. The bibliography
and registry checks pin sites that already carried the title.

This change does not edit or regenerate the committed evidence artifacts,
so three keep the old title. This module checks two things about them:
the erratum names every one, and each differs from its script's current
citation only in the title.

The erratum's title-page quote, the PDF's metadata title and the source
hashes are checked against the archived sources when those are staged
locally; otherwise that one check skips.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ERRATUM = ROOT / "docs" / "errata" / "2026-09-30-mermin-report-title.md"
PROVENANCE_ERRATUM = (
    ROOT / "docs" / "errata" / "2026-09-29-anchor-provenance.md"
)
BIBLIOGRAPHY = ROOT / "docs" / "references.bib"
SOURCES_NEEDED = ROOT / "benchmarks" / "SOURCES-NEEDED.md"
REGISTRY = ROOT / "benchmarks" / "registry.json"
SOURCE_TEXTS = Path("~/PolicyEngine/dynasim-refs").expanduser()

TITLE = (
    "Distributional Effects of Reforming Social Security through Benefit "
    "Reductions"
)
OLD_TITLE = (
    "The Effect of Benefit Reductions on the Distribution of Social "
    "Security Benefits"
)
LANDING_URL = (
    "https://www.urban.org/research/publication/"
    "distributional-effects-reforming-social-security-through-benefit-"
    "reductions"
)
OLD_LANDING_URL = (
    "https://www.urban.org/research/publication/"
    "effect-benefit-reductions-distribution-social-security-benefits"
)

# Scans compare text with everything but letters and digits removed, so
# the old title is found across any seam: a wrapped string literal, a
# wrapped comment, a line break or a hyphenated URL slug.
_NON_ALNUM = bytes(
    b for b in range(256) if not (48 <= b <= 57 or 97 <= b <= 122)
)


def _squash(data: bytes | str) -> bytes:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return data.lower().translate(None, _NON_ALNUM)


#: The old title (without its leading article) and its URL slug, squashed.
OLD_SIGNATURES = (
    _squash(OLD_TITLE.removeprefix("The ")),
    _squash(OLD_LANDING_URL.rsplit("/", 1)[1]),
)
#: Tracked binary types the scans skip; every other tracked file is read.
BINARY_SUFFIXES = {".gz", ".xlsx", ".pdf", ".png", ".ico"}
#: Files that must be among those scanned, so the scan cannot pass on an
#: empty or truncated listing.
KNOWN_SCANNED = {
    Path("scripts/replication_ppi_mermin.py"),
    Path("scripts/replication_mermin_rows.py"),
    Path("scripts/replication_ppi_shared.py"),
    Path("benchmarks/SOURCES-NEEDED.md"),
    Path("docs/references.bib"),
}
#: Files that quote the old title on purpose.
SCAN_EXEMPT = {
    Path("docs/errata/2026-09-30-mermin-report-title.md"),
    Path("tests/test_mermin_report_title.py"),
}

# ---------------------------------------------------------------------
# The corrected citations, pinned exactly.
# ---------------------------------------------------------------------
_CITATION_HEAD = (
    f"Mermin, G. B. T. (2005). {TITLE}. Urban Institute report 411260. "
    "DYNASIM3, Runid 432. 2005 Trustees intermediate assumptions"
)
_WITH_CBO_SCORING = f"{_CITATION_HEAD}; CBO (2005) solvency scoring."
EXPECTED_PAPER = {
    "replication_ppi_mermin": _WITH_CBO_SCORING,
    "replication_mermin_rows": _WITH_CBO_SCORING,
    "replication_ppi_shared": f"{_CITATION_HEAD}.",
}
#: The committed artifact each script's citation was frozen into.
COMMITTED_ARTIFACT = {
    "replication_ppi_mermin": "runs/replication_ppi_mermin_v1.json",
    "replication_mermin_rows": "runs/replication_mermin_rows_v1.json",
    "replication_ppi_shared": "runs/replication_ppi_shared_v1.json",
}
#: Scripts whose module docstring names the anchor report.
DOCSTRING_SCRIPTS = ("replication_ppi_mermin", "replication_mermin_rows")

TABLE_ROW = re.compile(
    r"^\| `(?P<path>runs/[\w./-]+)` \| `(?P<ptr>/[^`]+)` \|$"
)
QUOTE_BLOCK = re.compile(
    r"`(?P<file>[\w.-]+\.txt)` lines? (?P<start>\d+)(?:–(?P<end>\d+))?"
    r"[^\n]*:\n\n```text\n(?P<body>.*?)\n```",
    re.DOTALL,
)
HASH_ROW = re.compile(r"\| `(?P<file>[\w.-]+)` \| `(?P<sha>[0-9a-f]{64})` \|")
HASHED_SOURCES = (
    "411260-benefit-reductions.txt",
    "411260-benefit-reductions.pdf",
)


def _script(name: str):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module(name)


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _has_old_title(data: bytes | str) -> bool:
    squashed = _squash(data)
    return any(signature in squashed for signature in OLD_SIGNATURES)


def _erratum() -> str:
    return ERRATUM.read_text(encoding="utf-8")


def _json_pointer_leaves(node, pointer: str = ""):
    """Yield (JSON pointer, value) for every string leaf."""
    if isinstance(node, dict):
        for key, value in node.items():
            token = str(key).replace("~", "~0").replace("/", "~1")
            yield from _json_pointer_leaves(value, f"{pointer}/{token}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _json_pointer_leaves(value, f"{pointer}/{index}")
    elif isinstance(node, str):
        yield pointer, node


def _tracked_files() -> list[Path]:
    """Every tracked file on disk, excluding tracked binary types."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        if (ROOT / ".git").exists():
            raise
        pytest.skip("not a git checkout, so tracked files cannot be listed")
    files = [
        Path(name) for name in listing.decode("utf-8").split("\0") if name
    ]
    return [
        path
        for path in files
        if path.suffix.lower() not in BINARY_SUFFIXES
        and (ROOT / path).is_file()
    ]


def _committed_old_title_hits() -> dict[tuple[str, str], str]:
    """Every tracked runs/ string that still carries the old title.

    JSON artifacts are keyed by (path, JSON pointer); any other tracked
    runs/ file that carries it is keyed by (path, "").
    """
    found = {}
    for relative in _tracked_files():
        if relative.parts[0] != "runs":
            continue
        raw = (ROOT / relative).read_bytes()
        if not _has_old_title(raw):
            continue
        if relative.suffix != ".json":
            found[(relative.as_posix(), "")] = ""
            continue
        for pointer, value in _json_pointer_leaves(json.loads(raw)):
            if _has_old_title(value):
                found[(relative.as_posix(), pointer)] = value
    return found


# =====================================================================
# Corrected strings
# =====================================================================
@pytest.mark.parametrize("script", sorted(EXPECTED_PAPER))
def test_script_cites_the_report_title(script):
    paper = _script(script).anchor_provenance()["paper"]
    assert paper == EXPECTED_PAPER[script]
    assert not _has_old_title(paper)


@pytest.mark.parametrize("script", DOCSTRING_SCRIPTS)
def test_script_docstring_names_the_report_title(script):
    doc = _script(script).__doc__
    assert f'"{TITLE}"' in _normalize(doc)
    assert not _has_old_title(doc)


def test_bibliography_entry_has_the_report_title_and_landing_page():
    text = BIBLIOGRAPHY.read_text(encoding="utf-8")
    entry = text[text.index("@techreport{mermin2005benefitreductions,") :]
    entry = entry[: entry.index("\n}")]
    assert f"title={{{TITLE}}}," in entry
    assert "number={411260}," in entry
    assert f"url={{{LANDING_URL}}}," in entry


def test_source_capture_request_gives_the_title_and_landing_page():
    text = SOURCES_NEEDED.read_text(encoding="utf-8")
    item = text[text.index("8. **Mermin (2005)") : text.index("9. **")]
    assert f"“{TITLE},” Urban report 411260" in _normalize(item)
    assert f"- URL: {LANDING_URL}\n" in item
    assert not _has_old_title(text)
    assert "Congressional Budget Office (2005) estimates" in _normalize(item)


def test_registry_mermin_locators_already_carry_the_title():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    documents = [
        locator["document"]
        for entry in registry["entries"]
        if entry["row_id"].startswith("dynasim.mermin.")
        for locator in entry["source_pin"]["exact_locators"]
    ]
    assert len(documents) == 20
    assert all(
        document.startswith(f"Mermin (2005), {TITLE}, report 411260")
        for document in documents
    )


def test_no_tracked_file_outside_runs_repeats_the_old_title():
    scanned = [
        relative
        for relative in _tracked_files()
        if relative.parts[0] != "runs" and relative not in SCAN_EXEMPT
    ]
    assert KNOWN_SCANNED <= set(scanned)
    hits = [
        relative.as_posix()
        for relative in scanned
        if _has_old_title((ROOT / relative).read_bytes())
    ]
    assert not hits, hits


# =====================================================================
# Committed artifacts that keep the old title
# =====================================================================
def test_erratum_table_names_every_committed_old_title():
    table = {
        (match["path"], match["ptr"])
        for line in _erratum().splitlines()
        if (match := TABLE_ROW.match(line))
    }
    assert table == {
        (artifact, "/anchor_provenance/paper")
        for artifact in COMMITTED_ARTIFACT.values()
    }
    assert set(_committed_old_title_hits()) == table


@pytest.mark.parametrize("script", sorted(COMMITTED_ARTIFACT))
def test_committed_citation_differs_from_the_script_only_in_title(script):
    artifact = json.loads(
        (ROOT / COMMITTED_ARTIFACT[script]).read_text(encoding="utf-8")
    )
    committed = artifact["anchor_provenance"]["paper"]
    assert committed.count(OLD_TITLE) == 1
    assert committed.replace(OLD_TITLE, TITLE) == EXPECTED_PAPER[script]


# =====================================================================
# The errata
# =====================================================================
def test_erratum_links_the_registry_issue_and_governs_the_artifacts():
    text = _erratum()
    assert "this erratum governs" in text
    assert "issues/497" in text
    assert f'"{TITLE}"' in text
    assert f'"{OLD_TITLE}"' in text
    assert LANDING_URL in text
    assert "returned HTTP 404 on 2026-09-30" in text
    assert "`tests/test_mermin_report_title.py`" in text


def test_provenance_erratum_addendum_points_to_the_follow_ups():
    text = PROVENANCE_ERRATUM.read_text(encoding="utf-8")
    addendum = text[text.index("## Addendum, 30 September 2026") :]
    assert "issues/497" in addendum
    assert "2026-09-30-mermin-report-title.md" in addendum
    assert "`dynasim.mermin.four_reform_cost_ordering`" in addendum
    # The table above names three of the row's fields; the addendum names
    # the fourth, which carries the same old attribution.
    assert "`/concept_mismatch/population`" in addendum


@pytest.mark.skipif(
    not all((SOURCE_TEXTS / name).is_file() for name in HASHED_SOURCES),
    reason="archived source texts not staged",
)
def test_erratum_quote_metadata_and_hashes_match_the_staged_sources():
    text = _erratum()
    blocks = list(QUOTE_BLOCK.finditer(text))
    assert [(m["file"], m["start"], m["end"]) for m in blocks] == [
        ("411260-benefit-reductions.txt", "1", "9")
    ]
    lines = (
        (SOURCE_TEXTS / "411260-benefit-reductions.txt")
        .read_text(encoding="utf-8")
        .split("\n")
    )
    assert blocks[0]["body"] == "\n".join(lines[0:9])
    assert lines[0].strip() == TITLE

    pdf = (SOURCE_TEXTS / "411260-benefit-reductions.pdf").read_bytes()
    assert f"/Title({TITLE})".encode() in pdf
    assert f'<rdf:li xml:lang="x-default">{TITLE}</rdf:li>'.encode() in pdf
    assert not _has_old_title(pdf)

    hashes = {m["file"]: m["sha"] for m in HASH_ROW.finditer(text)}
    assert sorted(hashes) == sorted(HASHED_SOURCES)
    for name, digest in hashes.items():
        assert (
            hashlib.sha256((SOURCE_TEXTS / name).read_bytes()).hexdigest()
            == digest
        ), name
