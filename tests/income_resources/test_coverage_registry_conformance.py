"""Conformance of pinned public legal artifacts in data/external.

Published worked examples retain their cited passages. These tests use no
survey observations and do not implement the CE3 component classifier.

Capture-folder invariants:

* The capture manifests list exactly the folder's captures, with their
  sizes and SHA-256 digests. Every metadata row that records a file and a
  SHA-256 finds that file with those bytes or says why it is absent:
  ``not_retained`` with a reason,
  ``removed_uncited_no_derivative_dependency``, or
  ``removed_duplicate_of_cited_capture`` naming a present duplicate. All
  rows for one file agree.
* A page extract records its original's file, size, SHA-256 and page
  count, and its kept pages (the cover first) as its qpdf command lists
  them. Its ``signature_status`` matches whether the extract carries the
  original's ``/ByteRange``. A text derivative of an extract records its
  pages in both numberings.
* Every recorded ``pdftotext`` call parses under pdftotext 26.09.0, and a
  derivative's ``-f``/``-l`` range is its recorded ``pdf_pages``.
* A row that cites a scanned page also quotes that page's OCR text.
* Each IRS edition extract cited for a threshold is followed by a citation
  of its page text that quotes the edition's published value.
* Published prose runs no word or citation into a number.

Registry-wide checks: an open reading has one name and a prose
description, and a closed row's named options say which one governs.

Hypothesis properties test the pdftotext parser and the retention, OCR,
IRS-quote, fused-token, open-reading and operative-reading checkers.
"""

import gzip
import hashlib
import importlib.util
import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.coverage_rules import (
    CAPTURE_DIRECTORY,
    EFFECTIVE_BASES,
    REGISTRY_PATH,
    TRIGGER_FACTS,
    AlternativeRequiredError,
    CoverageRegistry,
    CoverageRegistryError,
    NoRuleError,
    OpenRuleError,
    ThresholdUnavailableError,
    UnknownIdentifierError,
    load_registry,
    source_text,
)

REGISTRY_ARTIFACT = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "income_resources_ce1"
    / "coverage_rules.json"
)
PUBLISHED_CASES = [
    (row["rule_id"], example["example_id"])
    for row in json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    for example in row["worked_examples"]
]


@pytest.fixture(scope="module")
def registry():
    return load_registry(REGISTRY_ARTIFACT)


def citations(value):
    if isinstance(value, dict):
        if "capture" in value:
            yield value
        for child in value.values():
            yield from citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from citations(child)


@pytest.fixture(scope="module")
def assemble():
    spec = importlib.util.spec_from_file_location(
        "ce1_assemble_registry", REGISTRY_PATH.parent / "assemble_registry.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build


def test_canonical_registry_matches_research_fragments(registry, assemble):
    assert PUBLISHED_CASES, "CE1 needs published conformance cases"
    assert len(PUBLISHED_CASES) == len(set(PUBLISHED_CASES))
    assert assemble().encode("utf-8") == REGISTRY_PATH.read_bytes()
    assert registry.to_json().encode("utf-8") == REGISTRY_PATH.read_bytes()


def test_every_pinned_citation_matches_its_capture(registry):
    found = list(citations(registry.to_dict()))
    assert found
    digests = {}
    texts = {}
    for citation in found:
        path = CAPTURE_DIRECTORY / citation["capture"]
        if path not in digests:
            digests[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digests[path] == citation["sha256"]
        if citation.get("quote"):
            if path not in texts:
                texts[path] = source_text(path)
            assert " ".join(citation["quote"].split()) in texts[path]


MANIFEST_ENTRY = re.compile(
    r"^(?P<time>.+) (?P<sha256>[0-9a-f]{64}) (?P<size>\d+) (?P<name>\S+)$"
)
CAPTURE_METADATA = re.compile(
    r"^(capture_manifest.*\.txt|sources_.*\.json|source_inventory\.json"
    r"|SOURCE_INVENTORY\.md)$"
)


def test_capture_folder_and_manifests_list_the_same_bytes():
    entries = []
    for manifest in sorted(CAPTURE_DIRECTORY.glob("capture_manifest*.txt")):
        for line in manifest.read_text().splitlines():
            entry = MANIFEST_ENTRY.match(line)
            if entry and not line.startswith("#"):
                entries.append(entry)
    assert entries
    for entry in entries:
        data = (CAPTURE_DIRECTORY / entry["name"]).read_bytes()
        assert len(data) == int(entry["size"]), entry["name"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    captures = {
        path.name
        for path in CAPTURE_DIRECTORY.iterdir()
        if path.is_file() and not CAPTURE_METADATA.match(path.name)
    }
    assert captures == {entry["name"] for entry in entries}


def structured_provenance(row):
    value = row.get("provenance")
    return value if isinstance(value, dict) else {}


STATUTE_EXTRACTS = {
    "federal_register_1975_07_10_extract.pdf",
    "govinfo_statute79_pg286_extract.pdf",
    "govinfo_statute81_pg821_extract.pdf",
    "govinfo_statute86_pg1329_extract.pdf",
    "govinfo_statute97_pg65_extract.pdf",
    "govinfo_statute101_pg1330_extract.pdf",
    "govinfo_statute102_pg3342_extract.pdf",
}
PUB15_EDITIONS = (*range(1999, 2008), *range(2017, 2026))
# Review r2 low 13: one extract per IRS edition cited for a threshold, and
# the scanned 1985 Form 1040 instructions cited for page 31.
IRS_EXTRACTS = (
    {f"irs_pub926_{year}_extract.pdf" for year in range(2008, 2026)}
    | {f"irs_pub15_{year}_extract.pdf" for year in PUB15_EDITIONS}
    | {"irs_form1040_instructions_1985_extract.pdf"}
)
PAGE_EXTRACTS = STATUTE_EXTRACTS | IRS_EXTRACTS
QPDF_PAGES = re.compile(
    r"^qpdf --deterministic-id --empty --pages (\S+) ([\d,]+) -- (\S+) "
)


def read_inventory():
    return json.loads(
        (CAPTURE_DIRECTORY / "source_inventory.json").read_text()
    )


def test_page_extracts_record_their_originals():
    inventory = read_inventory()
    extracts = [
        row
        for row in inventory
        if "extracted_from" in structured_provenance(row)
    ]
    names = {row["file"] for row in extracts}
    assert names == PAGE_EXTRACTS
    for row in extracts:
        data = (CAPTURE_DIRECTORY / row["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
        original = row["provenance"]["extracted_from"]
        # qpdf keeps a signed original's signature dictionary, which no
        # longer covers the extract's bytes. The IRS originals carry none.
        signed = b"/ByteRange" in data
        assert signed == (row["file"] in STATUTE_EXTRACTS)
        assert row["provenance"]["signature_status"] == (
            "original_signature_invalidated_by_page_extraction"
            if signed
            else "original_unsigned"
        )
        assert "recorded URL" in row["provenance"]["original_retrieval"]
        assert not (CAPTURE_DIRECTORY / original["file"]).exists()
        assert original["bytes"] > len(data)
        assert re.fullmatch(r"[0-9a-f]{64}", original["sha256"])
        pages = row["provenance"]["original_pdf_pages"]
        assert pages == sorted(set(pages))
        assert pages[0] == 1 and pages[-1] <= original["pages"]
        method = QPDF_PAGES.match(row["provenance"]["method"])
        assert (method[1], method[3]) == (original["file"], row["file"])
        assert [int(page) for page in method[2].split(",")] == pages
    derived = [
        row
        for row in inventory
        if structured_provenance(row).get("derived_from") in names
    ]
    assert {row["file"] for row in derived} == {
        "federal_register_1975_07_10_extract.pdf.txt",
        "govinfo_statute79_pg286_extract.pdf.txt",
        "govinfo_statute101_pg1330_extract.pdf.txt",
        "govinfo_statute102_pg3342_extract.pdf.txt",
    } | {name + ".txt" for name in IRS_EXTRACTS}
    for row in derived:
        extract = next(
            r
            for r in extracts
            if r["file"] == row["provenance"]["derived_from"]
        )
        assert row["provenance"]["source_sha256"] == extract["sha256"]
        kept = extract["provenance"]["original_pdf_pages"]
        assert row["provenance"]["original_pdf_pages"] == [
            kept[page - 1] for page in row["provenance"]["pdf_pages"]
        ]


# pdftotext 26.09.0's options, from `pdftotext -h`. Each value is its own
# argument: pdftotext 26.09.0 exits 99 on `-f2 -l2 -layout` and 0 on
# `-f 2 -l 2 -layout` (both run on 2026-10-26 against
# govinfo_statute79_pg286_extract.pdf).
PDFTOTEXT_VALUES = {
    **dict.fromkeys(["-f", "-l", "-x", "-y", "-W", "-H"], int),
    **dict.fromkeys(["-r", "-fixed", "-colspacing"], float),
    **dict.fromkeys(["-remove-hyphens", "-enc", "-eol", "-opw", "-upw"], str),
}
PDFTOTEXT_FLAGS = {
    "-layout",
    "-raw",
    "-nodiag",
    "-htmlmeta",
    "-tsv",
    "-listenc",
    "-nopgbrk",
    "-urls",
    "-bbox",
    "-bbox-layout",
    "-cropbox",
    "-q",
    "-v",
    "-h",
    "-help",
    "--help",
    "-?",
}
# A recorded call ends at a closing quote or code span, a pipe, a
# semicolon, a parenthesis or the end of the line.
PDFTOTEXT_CALL = re.compile(r"\bpdftotext\b([^`\"|;()\n]*)")


def parse_pdftotext(arguments):
    """The options of one recorded pdftotext call, as pdftotext 26.09 reads
    them, up to its first argument that is not an option (a file or prose).

    Raises ValueError for an argument pdftotext would reject.
    """
    tokens = arguments.split()
    options = {}
    while tokens and tokens[0].startswith("-"):
        token = tokens.pop(0)
        if token in PDFTOTEXT_FLAGS:
            options[token] = True
        elif token in PDFTOTEXT_VALUES:
            if not tokens:
                raise ValueError(f"{token} needs a value")
            options[token] = PDFTOTEXT_VALUES[token](tokens.pop(0))
        else:
            raise ValueError(f"pdftotext has no option {token}")
    if options.get("-f", 1) > options.get("-l", float("inf")):
        raise ValueError("first page after last page")
    return options


def capture_metadata_files():
    return sorted(
        path
        for path in CAPTURE_DIRECTORY.iterdir()
        if CAPTURE_METADATA.match(path.name)
    )


def test_recorded_pdftotext_commands_parse():
    """Review r2 low 5: every recorded pdftotext call runs as written, and
    a derivative's page range is the one it records."""
    errors = []
    calls = 0
    for path in [*capture_metadata_files(), REGISTRY_ARTIFACT]:
        for call in PDFTOTEXT_CALL.finditer(path.read_text()):
            calls += 1
            try:
                parse_pdftotext(call[1])
            except ValueError as error:
                errors.append((path.name, call[0], str(error)))
    assert errors == []
    assert calls > len(IRS_EXTRACTS)
    for row in read_inventory():
        provenance = structured_provenance(row)
        method = str(provenance.get("method", ""))
        if method.startswith("pdftotext ") and "pdf_pages" in provenance:
            options = parse_pdftotext(PDFTOTEXT_CALL.match(method)[1])
            pages = list(range(options["-f"], options["-l"] + 1))
            assert pages == provenance["pdf_pages"], row["file"]


@settings(deadline=None)
@given(
    st.integers(1, 999),
    st.integers(0, 40),
    st.sampled_from(["-layout", "-raw"]),
    st.sampled_from(["-f", "-l"]),
)
@example(2, 1, "-raw", "-f")
def test_pdftotext_parser_rejects_fused_values(first, span, mode, fused):
    last = first + span
    spaced = f"-f {first} -l {last}"
    assert parse_pdftotext(f" {spaced} {mode} INVENTED.pdf out.txt") == {
        "-f": first,
        "-l": last,
        mode: True,
    }
    joined = spaced.replace(f"{fused} ", fused, 1)
    with pytest.raises(ValueError):
        parse_pdftotext(f" {joined} {mode} INVENTED.pdf")
    if span:
        with pytest.raises(ValueError):
            parse_pdftotext(f" -f {last} -l {first} {mode}")
    for recorded in ("-f2 -l3 -raw", "-f2 -l2 -layout"):
        with pytest.raises(ValueError):
            parse_pdftotext(recorded)


RETENTION_REASONS = {
    "removed_uncited_no_derivative_dependency",
    "removed_duplicate_of_cited_capture",
}


def recorded_captures():
    """(table, file, row) for every metadata row that records captured
    bytes: a file name and its SHA-256."""
    for path in capture_metadata_files():
        if path.suffix == ".json":
            for row in json.loads(path.read_text()):
                name = row.get("file", row.get("capture"))
                if name and "sha256" in row:
                    yield path.name, name, row


def retention_state(row):
    if row.get("status") == "not_retained":
        return "not_retained"
    return row.get("retention_status")


def unexplained_capture_records(records, present):
    """Rows whose recorded file is missing without a stated reason, present
    though marked removed, or described differently by another row.

    records holds (table, file, row) triples; present maps each file in the
    capture folder to its SHA-256.
    """
    problems = []
    states = {}
    for table, name, row in records:
        state = retention_state(row)
        states.setdefault(name, set()).add(state)
        if state is None:
            if present.get(name) != row["sha256"]:
                problems.append((table, name, "missing or changed"))
            continue
        if name in present:
            problems.append((table, name, "present but marked removed"))
        if state == "not_retained" and not row.get("reason"):
            problems.append((table, name, "not_retained without reason"))
        if state not in RETENTION_REASONS | {"not_retained"}:
            problems.append((table, name, f"unknown retention {state}"))
        if state == "removed_duplicate_of_cited_capture" and (
            row.get("duplicate_of") not in present
        ):
            problems.append((table, name, "duplicate_of names no capture"))
    for name, found in states.items():
        if len(found) > 1:
            problems.append(("rows disagree", name, sorted(map(str, found))))
    return problems


def test_recorded_captures_are_present_or_say_why():
    """Review r2 low 6: every recorded capture is in the folder with its
    recorded bytes, or every row naming it says why it is not."""
    records = list(recorded_captures())
    present = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in CAPTURE_DIRECTORY.iterdir()
        if path.is_file()
    }
    assert unexplained_capture_records(records, present) == []
    poms = [row for _, name, row in records if name == "poms_rm_04907001.html"]
    assert len(poms) == 2
    assert {retention_state(row) for row in poms} == {
        "removed_uncited_no_derivative_dependency"
    }
    p517 = [row for _, name, row in records if name == "irs_p517_2025.pdf"]
    assert p517 and all(
        row["duplicate_of"] == "irs_p517_2025.html" for row in p517
    )


RETENTION_CHOICES = [None, "not_retained", *sorted(RETENTION_REASONS)]


@settings(deadline=None)
@given(
    st.booleans(),
    st.sampled_from(RETENTION_CHOICES),
    st.sampled_from(RETENTION_CHOICES),
    st.booleans(),
)
@example(False, None, "removed_uncited_no_derivative_dependency", True)
def test_retention_checker_flags_unexplained_absences(
    present, first, second, explained
):
    """The low 6 checker is the test's oracle; @example is the poms case."""

    def row(state):
        out = {"file": "INVENTED.pdf", "sha256": "0" * 64}
        if state == "not_retained":
            out["status"] = state
            if explained:
                out["reason"] = "INVENTED reason"
        elif state:
            out["retention_status"] = state
            if explained:
                out["duplicate_of"] = "INVENTED.html"
        return out

    records = [
        ("a.json", "INVENTED.pdf", row(first)),
        ("b.json", "INVENTED.pdf", row(second)),
    ]
    folder = {"INVENTED.html": "1" * 64}
    if present:
        folder["INVENTED.pdf"] = "0" * 64
    needs_reason = {"not_retained", "removed_duplicate_of_cited_capture"}
    consistent = first == second and (
        present
        if first is None
        else not present and (explained or first not in needs_reason)
    )
    assert (unexplained_capture_records(records, folder) == []) == consistent


def scanned_sources(inventory):
    """Each scanned PDF and its OCR text, from rows whose method is OCR."""
    return {
        row["provenance"]["derived_from"]: row["file"]
        for row in inventory
        if str(structured_provenance(row).get("method", "")).startswith(
            "pdftoppm "
        )
    }


def entries_citing_scans_without_text(entries, scans):
    """Entries that cite a scanned PDF but quote none of its OCR text."""
    missing = {}
    for entry_id, entry in entries:
        found = list(citations(entry))
        quoted = {c["capture"] for c in found if c.get("quote")}
        satisfied = {scan for scan, text in scans.items() if text in quoted}
        cited = {c["capture"] for c in found} & scans.keys()
        lacking = sorted(cited - satisfied)
        if lacking:
            missing[entry_id] = lacking
    return missing


def test_scanned_pages_keep_cited_ocr_text():
    """Review r2 low 7: pdftotext finds no text on these scanned pages, so
    each row citing one also quotes its OCR text, which the citation test
    then finds in that text."""
    inventory = read_inventory()
    scans = scanned_sources(inventory)
    assert scans == {
        name: name + ".txt"
        for name in (
            "irs_schedule_se_1984.pdf",
            "irs_schedule_se_1985.pdf",
            "irs_form1040_instructions_1985_extract.pdf",
        )
    }
    rows = {row["file"]: row for row in inventory if "file" in row}
    for scan, text in scans.items():
        data = (CAPTURE_DIRECTORY / text).read_bytes()
        assert hashlib.sha256(data).hexdigest() == rows[text]["sha256"]
        provenance = rows[text]["provenance"]
        assert provenance["source_sha256"] == rows[scan]["sha256"]
        page = provenance["pdf_pages"][0]
        assert provenance["method"].startswith(
            f"pdftoppm -r 140 -f {page} -l {page} -png {scan} | tesseract "
        )
    raw = json.loads(REGISTRY_ARTIFACT.read_text())
    entries = [(row["rule_id"], row) for row in raw["rules"]] + [
        (row["threshold_id"], row) for row in raw["thresholds"]
    ]
    assert entries_citing_scans_without_text(entries, scans) == {}
    quoted = {c["capture"] for c in citations(raw) if c.get("quote")}
    assert set(scans.values()) <= quoted


@settings(deadline=None)
@given(st.booleans(), st.booleans(), st.booleans(), st.booleans())
def test_scan_checker_requires_quoted_ocr_text(cited, text, quote, nested):
    """The low 7 checker is the test's oracle."""
    scans = {"INVENTED.pdf": "INVENTED.pdf.txt"}
    found = []
    if cited:
        found.append({"capture": "INVENTED.pdf", "sha256": "0" * 64})
    if text:
        ocr = {"capture": "INVENTED.pdf.txt", "sha256": "1" * 64}
        if quote:
            ocr["quote"] = "INVENTED words"
        found.append(ocr)
    entry = {"parameters": {"evidence": found}} if nested else {}
    entry["citations"] = [] if nested else found
    flagged = entries_citing_scans_without_text([("INVENTED", entry)], scans)
    assert bool(flagged) == (cited and not (text and quote))


IRS_EDITION = re.compile(r"^irs_pub(926|15)_(\d{4})_extract\.pdf$")
EXTRACT_PAGE = re.compile(r"extract page (\d+) \(original PDF page (\d+)\)$")


def irs_quote_problems(threshold):
    """IRS edition extracts not followed by a text citation that quotes the
    edition's published value (and its year, where the passage states one).
    """
    problems = []
    cited = threshold["citations"]
    for index, citation in enumerate(cited):
        edition = IRS_EDITION.match(citation["capture"])
        if not edition:
            continue
        year = int(edition[2])
        following = cited[index + 1] if index + 1 < len(cited) else {}
        quote = following.get("quote", "")
        if following.get("capture") != citation["capture"] + ".txt":
            problems.append((citation["capture"], "no text citation"))
            continue
        amount = threshold["published_values"].get(str(year))
        if amount is None or f"${amount:,} or more" not in quote:
            problems.append((citation["capture"], "amount"))
        # The 1999-2007 Publication 15 table row states no year; the
        # edition supplies it.
        dated = edition[1] == "926" or year >= 2017
        if dated and f"in {year}" not in quote:
            problems.append((citation["capture"], "year"))
    return problems


def test_irs_extracts_quote_each_published_threshold(registry):
    """Review r2 low 13: each IRS extract is cited for its edition's
    threshold beside the text of the extract page that states it."""
    raw = json.loads(REGISTRY_ARTIFACT.read_text())
    inventory = {row["file"]: row for row in read_inventory() if "file" in row}
    seen = set()
    for threshold in raw["thresholds"]:
        assert irs_quote_problems(threshold) == []
        cited = threshold["citations"]
        for index, citation in enumerate(cited):
            edition = IRS_EDITION.match(citation["capture"])
            if not edition:
                continue
            seen.add(citation["capture"])
            year = int(edition[2])
            assert registry.threshold(threshold["threshold_id"], year) == (
                threshold["published_values"][str(year)]
            )
            text = cited[index + 1]
            pages = EXTRACT_PAGE.search(citation["location"]).groups()
            assert EXTRACT_PAGE.search(text["location"]).groups() == pages
            provenance = inventory[text["capture"]]["provenance"]
            assert [str(provenance["pdf_pages"][0])] == [pages[0]]
            assert [str(provenance["original_pdf_pages"][0])] == [pages[1]]
            kept = inventory[citation["capture"]]["provenance"]
            assert kept["original_pdf_pages"][-1] == int(pages[1])
    assert seen == {name for name in IRS_EXTRACTS if IRS_EDITION.match(name)}
    assert len(seen) == 36


@settings(deadline=None)
@given(
    st.sampled_from(["926", "15"]),
    st.sampled_from(PUB15_EDITIONS),
    st.integers(100, 99_999),
    st.integers(-2, 2),
    st.integers(-1, 1),
    st.booleans(),
)
def test_irs_quote_checker_flags_wrong_or_missing_values(
    publication, year, amount, amount_shift, year_shift, drop_text
):
    """The low 13 checker is the test's oracle."""
    name = f"irs_pub{publication}_{year}_extract.pdf"
    quoted_amount = amount + amount_shift * 100
    quoted_year = year + year_shift
    threshold = {
        "published_values": {str(year): amount},
        "citations": [
            {"capture": name},
            {
                "capture": name + ".txt",
                "quote": f"INVENTED ${quoted_amount:,} or more in "
                f"{quoted_year} to any one",
            },
        ],
    }
    if drop_text:
        threshold["citations"].pop()
    dated = publication == "926" or year >= 2017
    expected = drop_text or bool(amount_shift) or (dated and year_shift != 0)
    assert bool(irs_quote_problems(threshold)) == expected


def test_archived_threshold_table_matches_every_published_year(registry):
    name = "ssa_oact_cola_covthresh_wayback_20261013081352.html"
    html = (CAPTURE_DIRECTORY / name).read_text()
    rows = re.findall(
        r'<td align="center">(\d{4})</td>\s*'
        r"<td>\$?([\d,]+)</td>\s*<td>\$?([\d,]+)</td>",
        html,
    )
    assert len(rows) == 33
    assert {int(row[0]) for row in rows} == set(range(1994, 2027))
    for year, domestic, election in rows:
        assert registry.threshold("domestic_cash_annual", int(year)) == int(
            domestic.replace(",", "")
        )
        assert registry.threshold(
            "election_remuneration_annual", int(year)
        ) == int(election.replace(",", ""))
    assert (
        gzip.decompress((CAPTURE_DIRECTORY / (name + ".gz")).read_bytes())
        == (CAPTURE_DIRECTORY / name).read_bytes()
    )
    inventory = json.loads(
        (CAPTURE_DIRECTORY / "source_inventory.json").read_text()
    )
    blocked = next(
        row
        for row in inventory
        if row.get("url") == "https://www.ssa.gov/oact/cola/CovThresh.html"
    )
    assert blocked["status"] == "SOURCE_BLOCKED"
    assert blocked["reason"] == "HTTP 403"
    assert blocked["resolution"]["status"] == "answered_by_archived_capture"
    assert blocked["resolution"]["capture"] == name


@settings(deadline=None)
@given(st.integers(1968, 1993))
def test_archived_pre1994_footnote_agrees_with_quarterly_statute(
    registry, year
):
    threshold = next(
        t
        for t in registry.thresholds
        if t["threshold_id"] == "domestic_cash_quarterly"
    )
    assert registry.threshold("domestic_cash_quarterly", year) == 50
    assert threshold["aggregation_scope"] == "employer_employee_quarter"
    assert any(
        c["capture"] == "lii_42_409.html" for c in threshold["citations"]
    )
    assert any(
        c.get("quote", "").startswith("Prior to 1994")
        for c in threshold["citations"]
    )


@settings(deadline=None)
@given(st.integers(1968, 2026), st.data())
def test_family_year_lookup_is_never_silently_empty(registry, year, data):
    family = data.draw(st.sampled_from(registry.families))
    try:
        rules = registry.lookup(family, year)
    except CoverageRegistryError as refusal:
        assert str(refusal)
    else:
        assert rules
        assert all(r.family == family for r in rules)
        assert min(r.effective_start for r in rules) <= date(year, 1, 1)
        if rules[0].parameters.get("effective_basis") == "taxable_year_start":
            assert max(r.effective_end for r in rules) >= date(year, 1, 1)
        else:
            assert max(r.effective_end for r in rules) >= date(year, 12, 31)


def test_all_family_year_coordinates_return_or_refuse(registry):
    for family in registry.families:
        for year in range(1968, 2027):
            try:
                assert registry.lookup(family, year)
            except CoverageRegistryError as refusal:
                assert str(refusal)


@settings(deadline=None)
@given(st.data())
def test_real_ranges_partition_or_name_their_overlap(registry, data):
    family = data.draw(st.sampled_from(registry.families))
    rules = sorted(
        [r for r in registry.rules if r.family == family],
        key=lambda r: (r.effective_start, r.rule_id),
    )
    for left, right in zip(rules, rules[1:], strict=False):
        if right.effective_start <= left.effective_end:
            assert left.alternative and right.alternative
            assert left.alternative["group"] == right.alternative["group"]
            assert left.alternative["name"] != right.alternative["name"]
        else:
            assert (
                left.effective_end + timedelta(days=1) == right.effective_start
            )


@settings(deadline=None)
@given(st.data())
def test_trigger_vocabulary_and_awaiting_identification(registry, data):
    rule = data.draw(st.sampled_from(registry.rules))
    assert set(rule.trigger_facts) <= TRIGGER_FACTS
    assert rule.identification_class == "awaiting_ce2"
    assert not rule.is_identified
    if rule.rare_exclusion is not None:
        rare = rule.rare_exclusion
        assert rare["strict"] == "unresolved"
        if rare["negligible_candidate"] is None:
            assert rare["searches"]
        else:
            candidate = rare["negligible_candidate"]
            assert candidate["bound"] and candidate["population"]
            assert candidate["citation"]


@settings(
    deadline=None,
    max_examples=8,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(st.randoms())
def test_real_loader_is_row_order_independent_and_round_trips(
    registry, assemble, tmp_path, random
):
    raw = registry.to_dict()
    random.shuffle(raw["rules"])
    random.shuffle(raw["thresholds"])
    restored = CoverageRegistry.from_dict(raw, capture_root=CAPTURE_DIRECTORY)
    assert restored.to_json() == registry.to_json()
    assert json.loads(restored.to_json()) == restored.to_dict()
    for path in REGISTRY_PATH.parent.glob("*.json"):
        if path == REGISTRY_PATH:
            continue
        fragment = json.loads(path.read_text())
        if path.name.endswith("_rules.json") or path.name.startswith(
            "thresholds_"
        ):
            random.shuffle(fragment)
        (tmp_path / path.name).write_text(json.dumps(fragment))
    assert assemble(tmp_path).encode("utf-8") == REGISTRY_PATH.read_bytes()


@settings(deadline=None)
@given(st.data())
def test_real_cases_and_open_readings_obey_schema(registry, data):
    rule = data.draw(st.sampled_from(registry.rules))
    assert rule.residual_default["consequence"] == rule.consequence
    for outcome in (rule.residual_default, *rule.cases):
        deferred = outcome["consequence"] == "deferred"
        assert deferred == ("defers_to" in outcome)
        if deferred:
            assert rule.family not in outcome["defers_to"]
            assert set(outcome["defers_to"]) <= set(registry.families)
    for case in rule.cases:
        assert case["when"]
        assert set(case["when"]) <= set(rule.trigger_facts)
        assert case["consequence"] in CONSEQUENCE_VALUES
        if "open_reason" in case:
            assert case["consequence"] == "open"
            names = [o["name"] for o in case["open_alternatives"]]
            assert len(names) >= 2 and len(set(names)) == len(names)
    if rule.open_reason:
        assert rule.consequence in {None, "open"}
        assert len(rule.open_alternatives) >= 2
        assert rule.alternative is None


def test_open_cases_separate_legal_questions_from_missing_facts(registry):
    """A bare open case awaits facts; a legal sub-question refuses.

    Every open case without an open_reason conditions only on facts that
    are not established, so resolve returns it for the caller to fill in.
    Every open case with an open_reason makes resolve refuse, naming the
    case, whenever that case decides.
    """
    legal, awaiting = [], []
    for rule in registry.rules:
        for case in rule.cases:
            if case["consequence"] != "open":
                continue
            if "open_reason" in case:
                legal.append((rule.rule_id, case["case_id"]))
                with pytest.raises(OpenRuleError, match=case["case_id"]):
                    rule.resolve({case["case_id"]})
                for other in rule.cases:
                    pair = {case["case_id"], other["case_id"]}
                    ranked_first = min(
                        (case, other), key=lambda c: c["precedence"]
                    )
                    assert_first_match(rule, pair, ranked_first)
            else:
                awaiting.append((rule.rule_id, case["case_id"]))
                assert set(case["when"].values()) == {"not established"}
                assert rule.resolve({case["case_id"]}) == case
    assert ("federal_1987_2026", "fepca_waiver_reemployed_annuitant") in legal
    assert {rule_id.split("_")[0] for rule_id, _ in awaiting} == {"clergy"}


def test_real_date_axes_name_their_effective_date_clause(registry):
    """Review r2 low 4: every axis is an enum value with its clause."""
    axes = {}
    for rule in registry.rules:
        basis = rule.parameters.get("effective_basis")
        assert basis is None or basis in EFFECTIVE_BASES
        if basis not in (None, "service_date"):
            assert rule.parameters["effective_basis_description"].strip()
        axes.setdefault(rule.family, set()).add(rule.date_axis)
    assert all(len(found) == 1 for found in axes.values())
    assert axes["self_employment_director_income_timing"] == {
        "taxable_year_start"
    }
    assert axes["self_employment_conservation_reserve"] == {"payment_date"}
    assert axes["self_employment_public_office"] == {"payment_date"}
    assert axes["self_employment_options_dealers"] == {"taxable_year_start"}
    # The notes give calendar dates (Oct. 4, 1976; Oct. 1, 2008), so both
    # wordings govern part of each boundary year.
    assert axes[PASSIVE] == {"payment_date"}
    for year in (1976, 2008):
        assert len(registry.lookup(PASSIVE, year)) == 2
    with pytest.raises(UnknownIdentifierError):
        registry.lookup("self_employment_public_ofice", 2000)


QUOTED_CLAUSE = re.compile(r'"([^"]+)"')


def test_date_axis_descriptions_quote_a_cited_capture(registry):
    """Each non-default axis quotes its effective-date clause verbatim.

    The quoted spans sit between straight double quotes and must appear in
    the normalized text of a capture the row itself cites.
    """
    checked = 0
    for rule in registry.rules:
        description = rule.parameters.get("effective_basis_description")
        if description is None:
            continue
        spans = QUOTED_CLAUSE.findall(description)
        assert spans, rule.rule_id
        texts = [
            source_text(CAPTURE_DIRECTORY / capture)
            for capture in sorted({c.capture for c in rule.citations})
            if not capture.endswith(".pdf")
        ]
        for span in spans:
            assert any(span in text for text in texts), (rule.rule_id, span)
        checked += 1
    assert checked == 11


OPTION_RECORDS = re.compile(r"(^|_)(named_options|named_alternatives)$")


def open_reading_problems(row):
    """Readings described by a serialized record or a locator, and option
    records on an open row whose names differ from its open_alternatives.
    """
    problems = []
    groups = [row["open_alternatives"]] + [
        case.get("open_alternatives", []) for case in row["cases"]
    ]
    for alternatives in groups:
        for option in alternatives:
            text = option["description"]
            if "{" in text or any(
                phrase in text
                for phrase in ("Unselected source reading", "locator")
            ):
                problems.append((option["name"], "description"))
    names = {option["name"] for option in row["open_alternatives"]}
    if row["open_reason"] is not None:
        for key, value in row["parameters"].items():
            if OPTION_RECORDS.search(key) and option_names(value) != names:
                problems.append((key, "names"))
    return problems


def test_open_readings_are_named_once_and_described_in_prose():
    """Review r2 lows 8 and 9: one name per reading, each a legal reading.

    A parameter record of options on an open row uses exactly the names in
    open_alternatives, and no description is a serialized record.
    """
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    problems = {row["rule_id"]: open_reading_problems(row) for row in rows}
    assert {key: value for key, value in problems.items() if value} == {}
    described = sum(
        len(row["open_alternatives"])
        + sum(len(case.get("open_alternatives", [])) for case in row["cases"])
        for row in rows
    )
    assert described == 36


READING_TEXT = {
    "prose": "INVENTED reading under the statute",
    "dump": 'INVENTED reading: {"date": "1988-11-10"}',
    "locator": "INVENTED retained locator alternative",
}


@settings(deadline=None)
@given(
    st.lists(st.sampled_from("abc"), min_size=2, max_size=3, unique=True),
    st.sampled_from(sorted(READING_TEXT)),
    st.sampled_from(["same", "renamed", "absent"]),
    st.booleans(),
    st.booleans(),
)
def test_open_reading_checker_flags_dumps_and_second_names(
    names, description, record, keyed, in_case
):
    """The lows 8 and 9 checker is the test's oracle."""
    readings = [
        {"name": name, "description": READING_TEXT[description]}
        for name in names
    ]
    row = {
        "open_reason": None if in_case else "INVENTED_QUESTION",
        "open_alternatives": [] if in_case else readings,
        "cases": [{"open_alternatives": readings}] if in_case else [],
        "parameters": {},
    }
    recorded = {"same": names, "renamed": [n + "_other" for n in names]}
    if record in recorded:
        row["parameters"]["named_alternatives"] = (
            dict.fromkeys(recorded[record], "INVENTED")
            if keyed
            else [{"name": name} for name in recorded[record]]
        )
    expected = description != "prose" or (record == "renamed" and not in_case)
    assert bool(open_reading_problems(row)) == expected


def option_names(records):
    """Option records are keyed by name or listed with a name field."""
    if isinstance(records, (list, tuple)):
        return {record["name"] for record in records}
    return set(records)


def operative_reading_problems(row):
    """A closed row's named options that do not say which one governs.

    Listed options carry a status, one operational entry per group; keyed
    options carry a resolution naming the operative option or parameter.
    """
    options = row["parameters"].get("named_options")
    if row["open_reason"] is not None or options is None:
        return []
    problems = []
    if isinstance(options, (list, tuple)):
        groups = {}
        for option in options:
            status = option["status"]
            if not (
                status.startswith("operational")
                or status.endswith("not_operational")
            ):
                problems.append((option["name"], status))
            groups.setdefault(option["group"], []).append(
                status.startswith("operational")
            )
        problems += [
            (group, "operational entries")
            for group, flags in groups.items()
            if sum(flags) != 1
        ]
    else:
        resolution = row["parameters"].get(
            "source_disagreement_resolution", {}
        )
        allowed = {*options, *row["parameters"]} - {
            "source_disagreement_resolution"
        }
        if resolution.get("operative_current_text") not in allowed:
            problems.append(("resolution", "operative_current_text"))
        if not str(resolution.get("basis", "")).strip():
            problems.append(("resolution", "basis"))
    return problems


def test_closed_rows_name_their_operative_reading():
    """Review r2 low 14: a closed row's recorded options say which governs."""
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    resolved = [
        row["rule_id"]
        for row in rows
        if row["open_reason"] is None and "named_options" in row["parameters"]
    ]
    problems = {
        row["rule_id"]: operative_reading_problems(row) for row in rows
    }
    assert {key: value for key, value in problems.items() if value} == {}
    assert "fishing_crew_share_service_1989" in resolved
    assert len(resolved) == 8


@settings(deadline=None)
@given(
    st.lists(st.booleans(), min_size=1, max_size=4),
    st.booleans(),
    st.booleans(),
    st.sampled_from(["option", "parameter", "unknown", "missing"]),
    st.booleans(),
)
def test_operative_reading_checker_requires_one_governing_option(
    flags, bad_status, keyed, operative, basis
):
    """The low 14 checker is the test's oracle."""
    if keyed:
        targets = {"option": "first", "parameter": "other_parameter"}
        resolution = {"basis": "INVENTED basis"} if basis else {}
        if operative != "missing":
            resolution["operative_current_text"] = targets.get(
                operative, "INVENTED_unknown"
            )
        parameters = {
            "named_options": {"first": "INVENTED", "second": "INVENTED"},
            "other_parameter": 1,
            "source_disagreement_resolution": resolution,
        }
        expected = operative not in targets or not basis
    else:
        listed = [
            {
                "name": f"option_{index}",
                "group": "INVENTED",
                "status": (
                    "operational_INVENTED" if flag else "not_operational"
                ),
            }
            for index, flag in enumerate(flags)
        ]
        if bad_status:
            listed[0]["status"] = "INVENTED_status"
        parameters = {"named_options": listed}
        operational = sum(flags) - (bad_status and flags[0])
        expected = bad_status or operational != 1
    row = {"open_reason": None, "parameters": parameters}
    assert bool(operative_reading_problems(row)) == expected


FUSED_PROSE = re.compile(
    r"\b(?:[a-z]{2,}|[A-Z][a-z]+|Stat\.|pp\.?|GAO|IRS|IRC|TY|OSI|GGD|HEHS)"
    r"\d"
)
FUSED_IDENTIFIER = re.compile(
    r"(?:^|_)(?:section|under|of|or|for|the|and|in|to|by|Law)\d"
)
FUSED_WORDS = re.compile(r"\bnotwith\b")
# A word or number run into a parenthesized year: "517(2025)".
FUSED_PAREN_YEAR = re.compile(r"\w\((?:1[89]|20)\d\d\)")
LINKS = re.compile(r"https?://\S+|#\S+|\S+\.(?:pdf|html?|txt|json|xml)\b")
VERBATIM = {
    "quote",
    "source_passage",
    "supporting_passages",
    "query",
    "sha256",
    "capture",
    "url",
    "file",
}


def published_strings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            if key not in VERBATIM:
                yield from published_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from published_strings(child)
    elif isinstance(value, str):
        yield value


def fused_tokens(text):
    """Words or citations run into a number, in prose (text with a space)
    or in an identifier. Links and anchors are skipped."""
    if " " in text.strip():
        plain = LINKS.sub(" ", text)
        return (
            FUSED_PROSE.findall(plain)
            + FUSED_WORDS.findall(plain)
            + FUSED_PAREN_YEAR.findall(plain)
        )
    return FUSED_IDENTIFIER.findall(text) + FUSED_PAREN_YEAR.findall(text)


def test_published_prose_has_no_fused_tokens():
    """Review r2 low 10: no word or citation runs into a number.

    Quotations, search strings, links and anchors are verbatim and skipped.
    """
    raw = json.loads(REGISTRY_ARTIFACT.read_text())
    found = []
    for text in published_strings(raw):
        found += fused_tokens(text)
    assert found == []


@settings(deadline=None)
@given(
    st.sampled_from(["section", "under", "Stat.", "pp.", "IRC", "GAO"]),
    st.integers(1, 9999),
    st.integers(1800, 2099),
)
def test_fused_token_detector_flags_only_fused_forms(word, number, year):
    """The low 10 detector is the test's oracle."""
    assert fused_tokens(f"INVENTED {word}{number} text")
    assert not fused_tokens(f"INVENTED {word} {number} text")
    assert fused_tokens(f"INVENTED Publication {number}({year}) text")
    assert not fused_tokens(f"INVENTED Publication {number} ({year}) text")
    assert fused_tokens(f"INVENTED_section{number}")
    assert not fused_tokens(f"INVENTED_section_{number}")


VOCATIONAL = "nonresident_alien_vocational_service"


def test_vocational_readings_agree_before_1987_and_refuse_between(registry):
    """Review r2 low 9: both legal readings settle the years they share.

    Pub. L. 100-647 section 1001(d) names Reform Act section 123, so the
    M-class exclusion reaches no service before taxable years beginning
    after 1986; its later start remains a named question.
    """
    rows = {r.rule_id: r for r in registry.rules if r.family == VOCATIONAL}
    early = rows["nonresident_alien_vocational_service_1968"]
    unsettled = rows["nonresident_alien_vocational_service_1987"]
    agree = date.fromisoformat(early.parameters["readings_agree_before"])
    assert "M-1" in early.parameters["visa_classes"]
    assert "M" not in early.parameters["excluded_visa_classes"]
    for year in range(1968, agree.year):
        (rule,) = registry.lookup(VOCATIONAL, year)
        assert rule.resolve(())["consequence"] == "covered"
    starts = {
        name: date.fromisoformat(option["m1_service_excluded_from"])
        for name, option in unsettled.parameters["named_options"].items()
    }
    assert set(starts) == {o["name"] for o in unsettled.open_alternatives}
    assert min(starts.values()) == agree == unsettled.effective_start
    assert max(starts.values()) <= unsettled.effective_end
    for year in range(agree.year, unsettled.effective_end.year + 1):
        with pytest.raises(OpenRuleError, match="VOCATIONAL_M_CLASS"):
            registry.lookup(VOCATIONAL, year)
    (later,) = registry.lookup(VOCATIONAL, unsettled.effective_end.year + 1)
    assert later.resolve({"m1_admission_purpose_service"})["consequence"] == (
        "noncovered"
    )
    assert any(
        c.quote and "SECTION 123 OF THE REFORM ACT" in c.quote
        for c in unsettled.citations
    )


CONSEQUENCE_VALUES = {
    "covered",
    "noncovered",
    "covered_above_threshold",
    "open",
    "deferred",
}
PARAMETER_EVIDENCE = {
    "citation",
    "citations",
    "code_edition_evidence",
    "later_edition_reliance",
    "case_free_basis",
}
CONDITION_KEY = re.compile(
    r"(^|_)(conditions?|requires_all|any_of|exceptions?)$"
)
CONDITION_WORDS = re.compile(
    r"\b(only when|only if|unless|except|excepts|excepted|is excluded|"
    r"are excluded|excludes|remains excluded|depends on)\b",
    re.IGNORECASE,
)


def parameter_leaves(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in PARAMETER_EVIDENCE:
                yield from parameter_leaves(child, (*path, key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from parameter_leaves(child, path)
    else:
        yield path, value


def condition_signals(row):
    """Why a closed row's text or parameters name a statutory condition."""
    signals = []
    if row["consequence"] == "noncovered":
        signals.append("noncovered residual")
    for path, value in parameter_leaves(row["parameters"]):
        if value in CONSEQUENCE_VALUES:
            signals.append(f"consequence parameter {'.'.join(path)}")
        if path and CONDITION_KEY.search(path[-1]):
            signals.append(f"condition parameter {'.'.join(path)}")
    words = CONDITION_WORDS.search(row["description"])
    if words:
        signals.append(f"description says {words.group(0)!r}")
    return signals


def rows_missing_condition_cases(rows):
    """Closed rows that name a condition but carry neither cases nor basis.

    A closed row's residual applies when no case holds, so a condition left
    in prose or parameters would apply its exclusion unconditionally.
    """
    return {
        row["rule_id"]: signals
        for row in rows
        if row["open_reason"] is None
        and not row["cases"]
        and "case_free_basis" not in row["parameters"]
        and (signals := condition_signals(row))
    }


def test_closed_rows_naming_a_condition_carry_cases():
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    assert rows_missing_condition_cases(rows) == {}
    for row in rows:
        if "case_free_basis" in row["parameters"]:
            assert not row["cases"]
            assert row["consequence"] not in {"noncovered", "deferred"}
            leaves = parameter_leaves(row["parameters"])
            assert not any(v in CONSEQUENCE_VALUES for _, v in leaves)


@settings(deadline=None)
@given(
    st.sampled_from(sorted(CONSEQUENCE_VALUES - {"open"})),
    st.sampled_from(["", "unless the employer elects", "only when paid"]),
    st.booleans(),
)
def test_condition_detector_flags_every_signal(consequence, words, key):
    """The detector is the test's oracle, so its own signals are tested."""
    row = {
        "consequence": consequence,
        "description": f"INVENTED rule {words}".strip(),
        "parameters": {"required_conditions": ["a"]} if key else {},
        "open_reason": None,
        "cases": [],
    }
    expected = (consequence == "noncovered") + bool(words) + key
    assert len(condition_signals(row)) == expected
    flagged = rows_missing_condition_cases([{"rule_id": "INVENTED", **row}])
    assert bool(flagged) == bool(expected)
    with_case = {**row, "rule_id": "INVENTED", "cases": [{"case_id": "a"}]}
    assert rows_missing_condition_cases([with_case]) == {}


def test_consequences_live_in_cases_not_parameters():
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    stored = [
        (row["rule_id"], ".".join(path))
        for row in rows
        for path, value in parameter_leaves(row["parameters"])
        if value in CONSEQUENCE_VALUES
    ]
    assert stored == []


def test_real_deferral_targets_cover_the_deferring_years(registry):
    """Every deferral names a family with a rule in each deferring year.

    Exhaustive over every deferring outcome and every year of its row, so
    no target family leaves a year where the deferral reaches no rule. An
    open or alternative-only target refuses rather than misclassifying.
    """
    absent, checked = [], set()
    for rule in registry.rules:
        for outcome in (rule.residual_default, *rule.cases):
            if outcome["consequence"] != "deferred":
                continue
            for target in outcome["defers_to"]:
                for year in range(
                    rule.effective_start.year, rule.effective_end.year + 1
                ):
                    if (target, year) in checked:
                        continue
                    checked.add((target, year))
                    try:
                        assert registry.lookup(target, year)
                    except (OpenRuleError, AlternativeRequiredError):
                        continue
                    except NoRuleError:
                        absent.append((rule.rule_id, target, year))
    assert checked
    assert absent == []


def service_date_condition_holds(condition, service_day):
    """Evaluate a case's ``services_performed_date`` text on one date.

    Only the two forms CE1 writes are accepted, so a new phrasing fails
    loudly instead of matching by accident.
    """
    match = re.fullmatch(
        r"(on or after|before) (\d{4}-\d{2}-\d{2})", condition
    )
    assert match, condition
    boundary = date.fromisoformat(match[2])
    if match[1] == "before":
        return service_day < boundary
    return service_day >= boundary


def cash_equivalent_transfer_cases(rule, service_day):
    """Cases matching a cash-equivalent transfer without dominion, by date."""
    return {
        c["case_id"]
        for c in rule.cases
        if c["when"].get("noncash_transfer_cash_equivalence") is True
        and service_date_condition_holds(
            c["when"]["services_performed_date"], service_day
        )
    }


SSR_95_3P_PUBLISHED = date(1995, 8, 7)


@example(date(1990, 6, 15))
@example(SSR_95_3P_PUBLISHED - timedelta(days=1))
@example(SSR_95_3P_PUBLISHED)
@given(st.dates(date(1988, 1, 1), date(2026, 12, 31)))
@settings(deadline=None)
def test_cash_equivalent_agricultural_transfer_follows_ssr_95_3p(
    registry, service_day
):
    """INVENTED transfer: cattle the employee must sell back at once.

    POMS RS 01402.020 A: before SSR 95-3P (published 1995-08-07) SSA
    excluded noncash transfers from wages; from that date a cash-equivalent
    transfer is tested as cash wages. The 1990 example is the review's
    repro: it used to fall through to the residual.
    """
    (rule,) = registry.lookup("agricultural_service", service_day.year)
    matched = cash_equivalent_transfer_cases(rule, service_day)
    assert len(matched) == 1
    expected = (
        "noncovered"
        if service_day < SSR_95_3P_PUBLISHED
        else "covered_above_threshold"
    )
    resolved = rule.resolve(matched)
    assert resolved["consequence"] == expected
    assert resolved is not rule.residual_default
    # A bona fide commodity transfer with dominion stays outside wages.
    genuine = {
        c["case_id"]
        for c in rule.cases
        if "dominion and control" in c["when"].get("cash_remuneration", "")
    }
    assert len(genuine) == 1
    assert rule.resolve(genuine)["consequence"] == "noncovered"


def test_tribal_council_cases_and_uncaptured_crp_history(registry):
    tribal = registry.lookup("tribal_council_service", 2019)[0]
    council = {"no_section_418a_inclusion"}
    assert tribal.resolve(council)["consequence"] == "noncovered"
    agreement = council | {"section_418a_agreement_inclusion"}
    assert tribal.resolve(agreement)["consequence"] == "covered"
    # Council staff and tribal employees are not council-member service.
    assert tribal.resolve(set())["consequence"] == "covered"
    with pytest.raises(OpenRuleError, match="CRP_PRE2008"):
        registry.lookup("self_employment_conservation_reserve", 2007)


@pytest.mark.parametrize(
    ("family", "year", "matched", "expected"),
    [
        # HIGH-1 repros: each condition's failure no longer excludes.
        ("self_employment_conservation_reserve", 2010, set(), "deferred"),
        (
            "self_employment_conservation_reserve",
            2010,
            {"crp_payment_to_beneficiary"},
            "noncovered",
        ),
        ("self_employment_farm_rental_participation", 1970, set(), "open"),
        (
            "self_employment_farm_rental_participation",
            1970,
            {"participation_under_required_arrangement"},
            "covered",
        ),
        ("self_employment_retired_partner", 2000, set(), "covered"),
        (
            "self_employment_limited_partner",
            2000,
            {
                "guaranteed_payment_for_services",
                "limited_partner_distributive_share",
            },
            "covered",
        ),
        ("self_employment_insurance_termination", 2000, set(), "deferred"),
        ("self_employment_treaty_fishing", 2000, set(), "covered"),
        (
            "student_service",
            1980,
            {
                "section_218_agreement_covers_students",
                "enrolled_student_at_employing_school",
            },
            "covered",
        ),
        (
            "tribal_council_service",
            2000,
            {
                "later_418a_retroactive_coverage",
                "federally_recognized_council_member",
            },
            "covered",
        ),
        (
            "self_employment_rental_income",
            2000,
            {"parking_warehouse_storage_space", "real_estate_rentals"},
            "covered",
        ),
        (
            "international_organization_service",
            2000,
            {
                "transferred_federal_employee_410r",
                "designated_international_organization",
            },
            "covered",
        ),
        ("nonresident_alien_service", 2000, set(), "covered"),
        ("foreign_government_service", 2000, set(), "covered"),
        # Review r3 H1: an existing employee who did not sign the Form
        # SS-15a stays excluded under an actual waiver.
        (
            "nonprofit_service",
            1975,
            {"waiver_nonconcurring_existing_employee"},
            "noncovered",
        ),
        (
            "nonprofit_service",
            1980,
            {"waiver_nonconcurring_existing_employee"},
            "noncovered",
        ),
    ],
)
def test_failed_conditions_no_longer_exclude(
    registry, family, year, matched, expected
):
    (rule,) = registry.lookup(family, year)
    assert rule.resolve(matched)["consequence"] == expected


NONPROFIT_WAIVER_WORKERS = {
    # INVENTED workers of a 501(c)(3) employer, by the cases that hold.
    "listed_existing_employee": (
        {"effective_waiver_concurring_employee"},
        "covered_above_threshold",
    ),
    "hired_after_certificate": (
        {"effective_waiver_concurring_employee"},
        "covered_above_threshold",
    ),
    "unlisted_existing_employee": (
        {"waiver_nonconcurring_existing_employee"},
        "noncovered",
    ),
    "deemed_waiver_employee": (
        {"deemed_waiver_all_employees"},
        "covered_above_threshold",
    ),
    "no_waiver": ({"no_effective_waiver"}, "noncovered"),
    "not_a_501c3_employer": (set(), "covered"),
}


@pytest.mark.parametrize("worker", sorted(NONPROFIT_WAIVER_WORKERS))
@pytest.mark.parametrize("year", [1975, 1980])
def test_nonprofit_waiver_covers_only_listed_or_later_employees(
    registry, year, worker
):
    """Review r3 H1: NPO503 covers "the employees who signed the SS-15a,
    as well as those hired afterwards"; NPO505 excludes an existing
    employee who did not sign; RS 01901.540 D.7 deems a constructive
    waiver to cover all employees.
    """
    (rule,) = registry.lookup("nonprofit_service", year)
    matched, expected = NONPROFIT_WAIVER_WORKERS[worker]
    assert rule.resolve(matched)["consequence"] == expected
    cases = {case["case_id"]: case for case in rule.cases}
    unlisted = cases["waiver_nonconcurring_existing_employee"]["when"]
    assert "not listed on the Form SS-15a" in (
        unlisted["nonprofit_employee_concurrence"]
    )
    assert unlisted["nonprofit_coverage_waiver"].startswith("actual")
    assert cases["effective_waiver_concurring_employee"]["when"][
        "nonprofit_coverage_waiver"
    ].startswith("actual")
    deemed = cases["deemed_waiver_all_employees"]["when"]
    assert "nonprofit_employee_concurrence" not in deemed
    quotes = {c.quote for c in rule.citations if c.quote}
    assert any("signed the Form SS-15a" in quote for quote in quotes)
    assert any("covering all employees" in quote for quote in quotes)
    assert "501(c)(3)" in rule.residual_default["description"]


PUBLIC_OFFICERS = {
    # INVENTED officers, by the cases whose conditions hold for them.
    "salaried_state_officer": ({"public_office_functions"}, "noncovered"),
    "fee_officer_in_a_section_218_position": (
        {"public_office_functions"},
        "noncovered",
    ),
    "federal_officer": ({"public_office_functions"}, "noncovered"),
    "fee_officer_outside_section_218": (
        {"public_office_functions", "state_local_fee_basis_office"},
        "covered",
    ),
    "fee_officer_with_1968_election": (
        {
            "public_office_functions",
            "public_law_90_248_election",
        },
        "noncovered",
    ),
    "not_a_public_office": (set(), "covered"),
}


@pytest.mark.parametrize("officer", sorted(PUBLIC_OFFICERS))
def test_public_office_exclusion_reaches_every_office_but_the_fee_one(
    registry, officer
):
    """Review r3 H2: 411(c)(1) excludes "the performance of the functions
    of a public office", other than a fee-only State or local position
    outside a section 418 agreement.

    The exclusion conditions on a fact that says whether the income is for
    a public office's functions, which the fee exception also requires.
    """
    (rule,) = registry.lookup_date(
        "self_employment_public_office", date(2000, 6, 1)
    )
    matched, expected = PUBLIC_OFFICERS[officer]
    assert rule.resolve(matched)["consequence"] == expected
    cases = {case["case_id"]: case for case in rule.cases}
    exclusion = cases["public_office_functions"]
    assert set(exclusion["when"]) == {"public_office_functions"}
    fee = cases["state_local_fee_basis_office"]
    assert fee["when"]["public_office_functions"] == (
        exclusion["when"]["public_office_functions"]
    )
    assert "public_office_functions" in fee["overrides"]
    assert "public_office_functions" in TRIGGER_FACTS


GOVERNMENT_LEVEL = re.compile(
    r"\b(state|political subdivision|federal|united states|"
    r"instrumentality|local|district of columbia|guam|american samoa)\b",
    re.IGNORECASE,
)


def test_government_level_conditions_name_a_level_of_government():
    """Review r3 H2: a case keyed on government_level that names no level
    of government can never match a real fact value."""
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    found = [
        (row["rule_id"], case["case_id"], case["when"]["government_level"])
        for row in rows
        for case in row["cases"]
        if "government_level" in case["when"]
    ]
    assert len(found) == 6
    assert [
        entry for entry in found if not GOVERNMENT_LEVEL.search(entry[2])
    ] == []


@settings(deadline=None)
@given(
    st.sampled_from(
        [
            "domestic_cash_quarterly",
            "casual_cash_quarterly",
            "homeworker_cash_quarterly",
            "election_remuneration_quarterly",
            "cash_tips_monthly",
        ]
    )
)
def test_period_thresholds_keep_employers_separate(registry, threshold_id):
    threshold = next(
        t for t in registry.thresholds if t["threshold_id"] == threshold_id
    )
    period = "month" if threshold_id == "cash_tips_monthly" else "quarter"
    assert threshold["aggregation_scope"] == f"employer_employee_{period}"


@settings(deadline=None)
@given(st.data())
def test_real_case_precedence_is_first_match(registry, data):
    rule = data.draw(st.sampled_from([r for r in registry.rules if r.cases]))
    by_id = {case["case_id"]: case for case in rule.cases}
    assert len(by_id) == len(rule.cases)
    assert sorted(c["precedence"] for c in rule.cases) == list(
        range(1, len(rule.cases) + 1)
    )
    matched = data.draw(st.sets(st.sampled_from(sorted(by_id))))
    if matched:
        winner = min(matched, key=lambda case_id: by_id[case_id]["precedence"])
        assert_first_match(rule, matched, by_id[winner])
    else:
        assert rule.resolve(matched) == rule.residual_default
    for case in rule.cases:
        for target in case.get("overrides", ()):
            assert by_id[target]["precedence"] > case["precedence"]
            assert by_id[target]["consequence"] != case["consequence"]
            assert_first_match(rule, {case["case_id"], target}, case)


def assert_first_match(rule, matched, winner):
    """The winner decides; a legal open sub-question decides by refusing."""
    if "open_reason" in winner:
        with pytest.raises(OpenRuleError, match=winner["case_id"]):
            rule.resolve(matched)
    else:
        assert rule.resolve(matched) is winner


FEDERAL_EXCEPTIONS = (
    "official_position_service",
    "after_official_service_from_1988_11_10",
    "fers_or_fsps_election",
    "legislative_not_retirement_covered_1983",
    "legislative_lump_sum_after_1983",
    "legislative_ceased_coverage_after_1983",
)
FEDERAL_PARAGRAPH_6 = (
    "federal_penal_inmate",
    "federal_hospital_student_employee",
    "temporary_emergency_employee",
)


@settings(deadline=None)
@given(st.integers(1984, 2026), st.data())
def test_federal_exceptions_outrank_the_grandfather_exclusion(
    registry, year, data
):
    (rule,) = registry.lookup("federal_retirement_service", year)
    ids = {case["case_id"] for case in rule.cases}
    assert ("fers_or_fsps_election" in ids) == (year >= 1987)
    # Review MED-1 repro: a Member of Congress serving since 1983.
    member = {"grandfathered_continuous_service", "official_position_service"}
    assert rule.resolve(member)["consequence"] == "covered"
    excluded = data.draw(
        st.sets(
            st.sampled_from(
                ["grandfathered_continuous_service", "federal_annuitant"]
            ),
            min_size=1,
        )
    )
    exception = data.draw(
        st.sampled_from(sorted(ids.intersection(FEDERAL_EXCEPTIONS)))
    )
    assert rule.resolve(excluded | {exception})["consequence"] == "covered"
    # 410(a)(5)(C)-(H) lift paragraph (5) only; paragraph (6) still applies.
    inmate = data.draw(st.sampled_from(FEDERAL_PARAGRAPH_6))
    assert (
        rule.resolve(excluded | {exception, inmate})["consequence"]
        == "noncovered"
    )
    # Pub. L. 98-369 section 2601(d) requalification displaces (G)(ii).
    requalified = {
        "defra_2601d_requalification",
        "legislative_lump_sum_after_1983",
        "grandfathered_continuous_service",
    }
    assert rule.resolve(requalified)["consequence"] == "noncovered"


@settings(deadline=None)
@given(st.integers(1984, 2026))
def test_federal_legislative_branch_exception_is_returned(registry, year):
    rule = registry.lookup("federal_retirement_service", year)[0]
    assert any(
        c["consequence"] == "covered"
        and "legislative" in str(c["when"]).lower()
        for c in rule.cases
    )


@pytest.mark.parametrize(
    ("rule_id", "example_id"),
    PUBLISHED_CASES,
    ids=[example_id for _, example_id in PUBLISHED_CASES],
)
def test_published_examples_conform_to_legal_lookup(
    registry, rule_id, example_id
):
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    example = next(
        e for e in rule.worked_examples if e["example_id"] == example_id
    )
    citation = example["citation"]
    passage = " ".join(example["source_passage"].split())
    assert passage in source_text(CAPTURE_DIRECTORY / citation["capture"])
    if example.get("income_year_basis") == (
        "source_edition_lookup_year_for_undated_published_example"
    ):
        assert example["income_year"] == example["source_edition_year"]
    returned = registry.lookup(rule.family, example["income_year"])
    matched = [r for r in returned if r.rule_id == example["expected_rule_id"]]
    assert len(matched) == 1
    for threshold_id, amount in example.get("expected_thresholds", {}).items():
        assert (
            registry.threshold(threshold_id, example["income_year"]) == amount
        )
    outcome = published_outcome(registry, matched[0], example)
    assert outcome == example["published_outputs"]
    if "expected_amount" in example:
        assert (
            outcome["annual_cash_wages_dollars"] == example["expected_amount"]
        )


def money_forms(cents):
    dollars, rest = divmod(cents, 100)
    whole = f"${dollars:,}"
    if rest:
        return {f"{whole}.{rest:02d}"}
    return {whole, f"{whole}.00"}


def rendered_amounts(facts):
    """Each published amount as the passage would print it."""
    for key, value in facts.items():
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        if key.endswith("_cents"):
            yield key, money_forms(value)
        elif key.endswith("_dollars") or key == "weekly_cash_wages":
            yield key, money_forms(value * 100)
        elif key == "weeks":
            yield key, {f"{value} weeks"}
        else:
            raise AssertionError(f"no rendering for published amount {key}")


@pytest.mark.parametrize(
    ("rule_id", "example_id"),
    PUBLISHED_CASES,
    ids=[example_id for _, example_id in PUBLISHED_CASES],
)
def test_published_amounts_sit_in_their_cited_passages(
    registry, rule_id, example_id
):
    """Review r2 low 11: the passage holds every input and outcome amount."""
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    example = next(
        e for e in rule.worked_examples if e["example_id"] == example_id
    )
    text = source_text(CAPTURE_DIRECTORY / example["citation"]["capture"])
    passages = [
        example["source_passage"],
        *example.get("supporting_passages", ()),
    ]
    for passage in passages:
        assert " ".join(passage.split()) in text
    joined = " ".join(" ".join(p.split()) for p in passages)
    facts = {**example["published_inputs"], **example["published_outputs"]}
    for key, forms in rendered_amounts(facts):
        assert any(form in joined for form in forms), (example_id, key)


def published_outcome(registry, rule, example):
    """Evaluate only the published example's facts against the returned law.

    The oracle is test-side arithmetic and condition checks, independent of
    stored expected parameters. Exhausting the inputs and comparing the whole
    output mapping prevents unused published facts or outcomes.
    """
    facts = dict(example["published_inputs"])
    kind = example["calculation"]
    params = rule.parameters
    year = example["income_year"]
    if kind == "domestic_threshold":
        annual = facts.pop("weekly_cash_wages") * facts.pop("weeks")
        over_18 = facts.pop("employee_over_18")
        unrelated = facts.pop("employee_unrelated")
        eligible = over_18 and unrelated
        threshold = registry.threshold(params["threshold_id"], year)
        result = {
            "annual_cash_wages_dollars": annual,
            "social_security_coverage": (
                "covered"
                if eligible
                and annual >= threshold
                and rule.consequence == "covered_above_threshold"
                else "noncovered"
            ),
        }
    elif kind in {"agricultural_cash_wages", "domestic_cash_wages"}:
        cash = facts.pop("cash_wages_cents")
        employer_paid_tax = facts.pop("employer_paid_employee_fica_cents")
        if kind == "agricultural_cash_wages":
            threshold_id = params["threshold_ids"][0]
            clears = cash >= 100 * registry.threshold(threshold_id, year)
            all_cash = params["all_cash_covered_when_test_met"]
            suffix = ""
        else:
            annual = facts.pop("expected_annual_cash_at_least_cents")
            over_18 = facts.pop("employee_over_18")
            unrelated = facts.pop("employee_unrelated")
            eligible = over_18 and unrelated
            clears = eligible and annual >= 100 * registry.threshold(
                params["threshold_id"], year
            )
            all_cash = params["all_cash_covered_when_threshold_met"]
            suffix = "_per_payday"
        ss_cash = cash + (
            employer_paid_tax
            if params["employer_paid_employee_fica_included_in_wages"]
            else 0
        )
        result = {
            f"social_security_wages{suffix}_cents": (
                ss_cash
                if clears
                and all_cash
                and rule.consequence == "covered_above_threshold"
                else 0
            ),
            f"federal_income_tax_wages{suffix}_cents": cash
            + employer_paid_tax,
        }
    elif kind == "agricultural_commodity":
        dominion = facts.pop("employee_exercises_dominion_and_control")
        if dominion:
            matched = {
                c["case_id"]
                for c in rule.cases
                if "dominion and control"
                in c["when"].get("cash_remuneration", "")
            }
            assert matched
            consequence = rule.resolve(matched)["consequence"]
        else:
            matched = cash_equivalent_transfer_cases(rule, date(year, 1, 1))
            assert len(matched) == 1
            consequence = rule.resolve(matched)["consequence"]
        result = {
            "commodity_remuneration": {
                "noncovered": "not_wages",
                "covered_above_threshold": "wages",
            }[consequence]
        }
    elif kind == "parent_child_business":
        parent = facts.pop("parent_works_for_child")
        business = facts.pop("trade_or_business")
        controlled = facts.pop("son_controls_work")
        assert parent and business and controlled
        case = next(
            c
            for c in rule.cases
            if c["when"]
            .get("family_service", "")
            .startswith("parent employed by child in")
        )
        result = {"social_security_coverage": case["consequence"]}
    elif kind == "order_service":
        required = facts.pop("required_order_duties")
        vow = facts.pop("vow_of_poverty")
        if required and vow:
            excluded = params["poverty_vow_self_employment_excluded"]
            result = {
                "self_employment_coverage": (
                    "noncovered" if excluded else "covered"
                )
            }
        else:
            consequence = next(
                c["consequence"]
                for c in rule.cases
                if c["when"]
                .get("religious_order_service", "")
                .startswith("ordinary employment for a third party")
            )
            result = {
                "social_security_and_medicare_treatment": {
                    "noncovered": "not_subject_to_FICA",
                    "covered": "subject_to_FICA",
                }[consequence]
            }
    elif kind == "minister_exemption":
        effective = facts.pop("exemption_granted")
        condition = (
            "effective 1402(e) exemption" if effective else "not established"
        )
        consequence = next(
            c["consequence"]
            for c in rule.cases
            if c["when"].get("clergy_or_religious_exemption") == condition
        )
        result = {"social_security_coverage": consequence}
    elif kind == "section_218_reentry":
        new_member = facts.pop("state_treats_as_new_member")
        prior_vote = facts.pop("prior_vote")
        rule_value = params["section_218_divided_vote_same_group_return"][
            "state_new_member" if new_member else "state_existing_member"
        ]
        covered = rule_value == "compulsorily_covered" or (
            rule_value == "retains_prior_vote" and prior_vote == "yes"
        )
        assert params["section_218_first"]
        result = {"agreement_coverage": "covered" if covered else "noncovered"}
    elif kind == "state_local_mandatory":
        agreement = facts.pop("section_218_covered")
        member = facts.pop("qualified_retirement_system_member")
        assert params["section_218_first"]
        assert date(year, 1, 1) >= date.fromisoformat(
            params["mandatory_start"]
        )
        if agreement:
            case = next(
                c
                for c in rule.cases
                if c["when"]
                .get("section_218_position", "")
                .startswith("covered by effective")
            )
        else:
            membership = (
                "member of an IRS-qualified system"
                if member
                else "not a member of an IRS-qualified system"
            )
            case = next(
                c
                for c in rule.cases
                if c["when"].get("public_retirement_system_participation")
                == membership
            )
        result = {"social_security_coverage": case["consequence"]}
    elif kind == "minister_gross_concept":
        salary = facts.pop("salary_cents")
        housing = facts.pop("parsonage_value_cents", 0)
        foreign_exclusion = facts.pop("income_tax_foreign_exclusion_cents", 0)
        exclusions = params["gross_income_exclusions_disregarded"]
        amount = salary + (housing if "26USC107" in exclusions else 0)
        if "26USC911" not in exclusions:
            amount -= foreign_exclusion
        result = {"included_se_gross_concept_cents": amount}
    elif kind == "farm_agent":
        owner_participates = facts.pop("owner_personally_participates")
        agent_participates = facts.pop("agent_participates")
        participation = owner_participates or (
            agent_participates and params["agent_activities_count"]
        )
        case = next(
            c
            for c in rule.cases
            if c["when"].get("material_participation") is participation
        )
        result = {
            "rental_income_included_in_nese": {
                "covered": True,
                "noncovered": False,
            }[case["consequence"]]
        }
    else:
        pytest.fail(f"missing published-example oracle: {kind}")
    assert not facts, f"unused published inputs: {facts}"
    return result


@settings(deadline=None)
@given(st.integers(1968, 2026), st.data())
def test_real_threshold_is_published_or_requires_exact_named_inputs(
    registry, year, data
):
    threshold = data.draw(st.sampled_from(registry.thresholds))
    try:
        value = registry.threshold(threshold["threshold_id"], year)
    except ThresholdUnavailableError:
        assert str(year) not in threshold["published_values"]
    else:
        assert value >= 0
        assert str(year) in threshold["published_values"]


@settings(deadline=None)
@given(st.data())
def test_law_declared_monotone_thresholds_never_fall(registry, data):
    thresholds = [t for t in registry.thresholds if t.get("monotone")]
    assert thresholds
    threshold = data.draw(st.sampled_from(thresholds))
    values = [
        registry.threshold(threshold["threshold_id"], int(year))
        for year in sorted(threshold["published_values"])
    ]
    assert values == sorted(values)


def test_state_local_change_occurs_after_july_first_1991(registry):
    family = "section_218_and_mandatory_state_local"
    before = registry.lookup_date(family, date(1991, 7, 1))
    after = registry.lookup_date(family, date(1991, 7, 2))
    assert before[0].rule_id != after[0].rule_id
    assert len(registry.lookup(family, 1991)) == 2


def test_primary_act_boundaries_preserve_midyear_changes(registry):
    for family, boundary, before_id, after_id in (
        (
            "communist_organization_service",
            date(2014, 12, 19),
            "communist_organization_service_1968",
            "communist_organization_service_2014_1219",
        ),
        (
            "tribal_council_service",
            date(2018, 9, 20),
            "tribal_council_service_1968",
            "tribal_council_service_2018_0920",
        ),
    ):
        assert (
            registry.lookup_date(family, boundary - timedelta(days=1))[
                0
            ].rule_id
            == before_id
        )
        assert registry.lookup_date(family, boundary)[0].rule_id == after_id
        assert len(registry.lookup(family, boundary.year)) == 2


def test_community_income_uses_operational_taxable_year_change(registry):
    before = registry.lookup("self_employment_community_income", 1979)[0]
    assert before.rule_id == "se_community_income_1968_1979"
    for year in (1980, 2000, 2003, 2004):
        with pytest.raises(OpenRuleError):
            registry.lookup("self_employment_community_income", year)
    after = registry.lookup_date(
        "self_employment_community_income", date(2004, 3, 2)
    )[0]
    assert after.rule_id == "se_community_income_2004_2026"
    assert after.parameters["statutory_text_amendment_date"] == "2004-03-02"


@settings(deadline=None)
@given(st.integers(1985, 2026))
def test_fishing_additional_cash_is_a_per_trip_upper_bound(registry, year):
    threshold = next(
        t
        for t in registry.thresholds
        if t["threshold_id"] == "fishing_additional_cash_per_trip"
    )
    assert threshold["comparison"] == "at_most"
    assert threshold["aggregation_scope"] == "employer_employee_trip"
    assert registry.threshold(threshold["threshold_id"], year) == 100


def test_open_source_history_refuses_instead_of_backcasting(registry):
    open_rules = [r for r in registry.rules if r.open_reason]
    assert open_rules
    for rule in open_rules:
        with pytest.raises(OpenRuleError):
            registry.lookup_date(rule.family, rule.effective_start)


PASSIVE = "self_employment_passive_income"


@given(st.integers(1968, 2026))
@settings(deadline=None)
def test_passive_income_returns_the_dividend_and_interest_exclusion(
    registry, year
):
    """411(a)(2) decides the receipts every year; sub-questions refuse.

    Review r2 MED-2: the family refused all 59 years although the exclusion
    of the dividends and interest themselves is captured.
    """
    for rule in registry.lookup(PASSIVE, year):
        ids = {c["case_id"] for c in rule.cases}
        interest = (
            ids & {"specified_interest", "specified_interest_registered_form"}
        ).pop()
        assert rule.open_reason is None
        assert rule.resolve({"specified_dividends"})["consequence"] == (
            "noncovered"
        )
        assert rule.resolve({interest})["consequence"] == "noncovered"
        dealer = {"dealer_in_stocks_or_securities", "specified_dividends"}
        assert rule.resolve(dealer | {interest})["consequence"] == "covered"
        assert rule.resolve(())["consequence"] == "covered"
        with pytest.raises(OpenRuleError, match="DEDUCTIONS_UNVERIFIED"):
            rule.resolve({"deductions_attributable_to_excluded_receipts"})


def test_passive_income_keeps_its_historical_interest_wording(registry):
    early = registry.lookup(PASSIVE, 1970)[0]
    former = {"interest_described_in_1939_code_25a", "specified_interest"}
    assert early.resolve(former)["consequence"] == "covered"
    middle = registry.lookup(PASSIVE, 1990)[0]
    assert "obligation_not_in_registered_form" not in {
        c["case_id"] for c in middle.cases
    }
    assert "interest_described_in_1939_code_25a" not in {
        c["case_id"] for c in middle.cases
    }
    late = registry.lookup(PASSIVE, 2010)[0]
    with pytest.raises(OpenRuleError, match="INTEREST_BENEFITS_WORDING"):
        late.resolve({"obligation_not_in_registered_form"})


def test_possessions_successor_rule_applies_from_enactment(registry):
    """Pub. L. 100-203 section 9023(b) states no effective date.

    The successor 411(a)(8) governs from enactment on 1987-12-22; the
    earlier history still refuses.
    """
    family = "self_employment_possessions_931_income"
    with pytest.raises(OpenRuleError):
        registry.lookup_date(family, date(1987, 12, 21))
    with pytest.raises(OpenRuleError):
        registry.lookup(family, 1987)
    (rule,) = registry.lookup_date(family, date(1987, 12, 22))
    assert rule.resolve(())["consequence"] == "covered"
    assert rule.parameters["enactment"] == "1987-12-22"
    for year in range(1988, 2027):
        assert [r.rule_id for r in registry.lookup(family, year)] == [
            rule.rule_id
        ]


@given(st.integers(1968, 1995))
@settings(deadline=None)
def test_rental_exclusion_returns_before_the_1996_cfr_edition(registry, year):
    """411(a)(1) decides 1968-1996-03-31; regulatory detail refuses."""
    (rule,) = registry.lookup("self_employment_rental_income", year)
    rent = {"real_estate_rentals"}
    assert rule.resolve(rent)["consequence"] == "noncovered"
    dealer = rent | {"real_estate_dealer_rentals"}
    assert rule.resolve(dealer)["consequence"] == "covered"
    farm = rule.resolve(rent | {"farm_rental_arrangement"})
    assert farm["consequence"] == "deferred"
    assert list(farm["defers_to"]) == [
        "self_employment_farm_rental_participation"
    ]
    assert rule.resolve(())["consequence"] == "covered"
    for case_id in (
        "dealer_investment_or_speculative_holdings",
        "services_to_occupants_regulatory_detail",
        "parking_warehouse_storage_space_regulatory_detail",
    ):
        with pytest.raises(OpenRuleError, match="RULE_UNVERIFIED"):
            rule.resolve(rent | {case_id})
    later = registry.lookup("self_employment_rental_income", 1997)[0]
    space = rent | {"parking_warehouse_storage_space"}
    assert later.resolve(space)["consequence"] == "covered"


def test_evidence_only_boundaries_name_their_edition(registry):
    """An edition-date split is recorded on both rows and in the capture."""
    marked = [
        (rule, entry)
        for rule in registry.rules
        for entry in rule.parameters.get("evidence_only_boundaries", ())
    ]
    assert {(rule.rule_id, entry["side"]) for rule, entry in marked} == {
        ("se_rental_income_1968_1996", "end"),
        ("se_rental_income_1996_2026", "start"),
    }
    for _, entry in marked:
        text = source_text(CAPTURE_DIRECTORY / entry["citation"]["capture"])
        edition = date.fromisoformat(entry["date"])
        assert f"{edition:%B} {edition.day}, {edition.year}" in text
        assert " ".join(entry["citation"]["quote"].split()) in text


def test_ret_concept_records_disregarded_limits_and_both_deeming_conditions(
    registry,
):
    ret = registry.metadata["earnings_test"]
    assert {r["paragraph"] for r in ret["disregarded_wage_limits"]} == {
        "409(a)(1)",
        "409(a)(6)(B)",
        "409(a)(6)(C)",
        "409(a)(7)(B)",
        "409(a)(8)",
    }
    assert ret["deeming_rule"]["connective"] == "both"
    assert len(ret["deeming_rule"]["required_conditions"]) == 2
    assert len(ret["gross_income_exclusions_D"]) == 2
    assert not ret["self_employment"]["thresholds_apply"]


@settings(deadline=None)
@given(st.integers(1968, 2026))
def test_ret_concept_refuses_years_with_unverified_dependencies(
    registry, year
):
    with pytest.raises(OpenRuleError):
        registry.earnings_test_concept(year)


def test_table_availability_does_not_infer_a_membership_rule(registry):
    definitions = registry.metadata["table_definitions"]
    assert {d["definition_id"] for d in definitions} == {
        "4.B2.c11",
        "4.B2.c12",
        "4.B11.total",
        "4.B11.wage",
        "4.B11.self_employment",
    }
    for definition in definitions:
        assert definition["status"] in {
            "verified",
            "TABLE_DEFINITION_UNVERIFIED",
        }
        assert definition["citations"]
        assert not definition["table_values_computed"]
        if definition["status"] == "TABLE_DEFINITION_UNVERIFIED":
            assert definition["reason"]
