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
  count, and its kept pages as its qpdf command lists them. It keeps the
  cover first unless a ``cover_dropped`` record names the text derivative
  of a kept page that states the edition; a recorded ``chain`` of qpdf
  steps leads from the original to the extract's bytes. Its
  ``signature_status`` matches whether the extract carries the original's
  ``/ByteRange``. A text derivative of an extract records its pages in
  both numberings.
* Every recorded ``pdftotext`` call parses under pdftotext 26.09.0, and a
  derivative's ``-f``/``-l`` range is its recorded ``pdf_pages``.
* A row that cites a scanned page also quotes that page's OCR text.
* Each IRS edition extract cited for a threshold is followed by a citation
  of its page text that quotes the edition's published value.
* Published prose runs no word or citation into a number.

Registry-wide checks: an open reading has one name and a prose
description, and a closed row's named options say which one governs.

Fact-pattern invariants (review r5):

* ``cases_met`` holds a condition only when a text the fixture states
  for the worker equals it exactly; the worker's facts never come from
  the row's own `when`. Each fixture names the consequence the sources
  give and the case (or residual) that decides it.
* Every case of every row decides at least one INVENTED sweep worker,
  and every row's residual (or open row) another, so a case reworded or
  narrowed, re-ranked or given another consequence fails the worker it
  decides; a deferred worker also pins its ``defers_to``.
* A broadened case fails a worker only where some worker just misses it
  on the dropped condition (``just_miss_workers``): every condition in
  the fixture's ``just_miss_required`` has one, and the conditions none
  has are a stated limit of at most ``UNSEEN_CONDITION_LIMIT`` (review
  r6 M-1).
* A pinned sample of unread-fact reasons keeps its content and a pinned
  sample of ties names its cases.
* A State or local exclusion reaches only the State or local level, and
  a federal one only service for the United States: a worker with every
  other fact at another level reaches the residual.
* Each covered case's statutory condition, when it fails, reaches the
  exclusion or residual the source gives, by a named path.
* Every trigger fact a row lists is read by a case or named with its
  reason, and every parameter that states a condition is tied.

Hypothesis properties test the pdftotext parser and the retention, OCR,
IRS-quote, fused-token, open-reading and operative-reading checkers, the
unread-fact, worded-condition and just-miss checkers.
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
    CoverageRegistry,
    CoverageRegistryError,
    NoRuleError,
    OpenRuleError,
    ThresholdUnavailableError,
    UnknownIdentifierError,
    _holds_condition_record,
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
    # Review r3 low 8: Pub 51 (2023), cited for pages 10-12 (low 6).
    | {"ce1c_irs_pub51_2023_extract.pdf"}
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
        assert pages[-1] <= original["pages"]
        # Review r3 note 1: an extract keeps its cover unless a kept page
        # states the edition (test_dropped_covers_name_their_edition).
        assert (pages[0] == 1) == ("cover_dropped" not in row["provenance"])
        method = QPDF_PAGES.match(row["provenance"]["method"])
        assert (method[1], method[3]) == (original["file"], row["file"])
        assert [int(page) for page in method[2].split(",")] == pages
        assert chain_problems(row) == []
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


def chain_problems(row):
    """Breaks in a recorded chain of qpdf steps from the original.

    The first step takes original pages from the recorded original; each
    later step takes pages of the step before it by their page numbers
    there, from those bytes; the last step's output is the row's bytes.
    """
    provenance = row["provenance"]
    chain = provenance.get("chain")
    if chain is None:
        return []
    original = provenance["extracted_from"]
    problems = []
    first = chain[0]
    if (first["input"], first["input_sha256"]) != (
        original["file"],
        original["sha256"],
    ):
        problems.append("first step input")
    pages = first["original_pdf_pages"]
    for before, step in zip(chain, chain[1:], strict=False):
        if step["input_sha256"] != before["output_sha256"]:
            problems.append("step input")
        if not all(1 <= page <= len(pages) for page in step["input_pages"]):
            problems.append("step pages")
            break
        pages = [pages[page - 1] for page in step["input_pages"]]
    if pages != provenance["original_pdf_pages"]:
        problems.append("pages")
    if (chain[-1]["output_bytes"], chain[-1]["output_sha256"]) != (
        row["bytes"],
        row["sha256"],
    ):
        problems.append("output")
    return problems


@settings(deadline=None)
@given(
    st.lists(st.integers(2, 30), min_size=1, max_size=4, unique=True),
    st.sampled_from(
        ["none", "first_input", "link", "pages", "output", "out_of_range"]
    ),
)
def test_chain_checker_flags_broken_links(later_pages, broken):
    """The note 1 chain checker is the test's oracle: a cover-and-pages
    extract, then the same pages without the cover."""
    kept = [1, *sorted(later_pages)]
    second_pages = list(range(2, len(kept) + 1))
    row = {
        "bytes": 2,
        "sha256": "2" * 64,
        "provenance": {
            "extracted_from": {"file": "INVENTED.pdf", "sha256": "0" * 64},
            "original_pdf_pages": kept[1:],
            "chain": [
                {
                    "input": "INVENTED.pdf",
                    "input_sha256": "0" * 64,
                    "original_pdf_pages": kept,
                    "output_bytes": 1,
                    "output_sha256": "1" * 64,
                },
                {
                    "input_sha256": "1" * 64,
                    "input_pages": second_pages,
                    "output_bytes": 2,
                    "output_sha256": "2" * 64,
                },
            ],
        },
    }
    chain = row["provenance"]["chain"]
    if broken == "first_input":
        chain[0]["input_sha256"] = "9" * 64
    elif broken == "link":
        chain[1]["input_sha256"] = "9" * 64
    elif broken == "pages":
        chain[1]["input_pages"] = [1, *second_pages]
    elif broken == "output":
        chain[1]["output_sha256"] = "9" * 64
    elif broken == "out_of_range":
        chain[1]["input_pages"] = [len(kept) + 1]
    assert bool(chain_problems(row)) == (broken != "none")


EDITION_FILE = re.compile(r"(?:^|_)irs_pub(\d+)_(\d{4})_extract\.pdf$")


def dropped_cover_problems(row, derivatives):
    """A dropped cover whose edition statement names another edition, or is
    not in the pinned text of a kept page of the extract.

    ``derivatives`` maps a text derivative's file name to its provenance
    and its whitespace-normalized text.
    """
    record = row["provenance"].get("cover_dropped")
    if record is None:
        return []
    problems = []
    edition = EDITION_FILE.search(row["file"])
    statement = record["edition_statement"]
    if not (
        edition
        and re.fullmatch(
            rf"Publication {edition[1]} \((?:[A-Z][a-z]+ )?{edition[2]}\)",
            statement,
        )
    ):
        problems.append("edition")
    derivative = derivatives.get(record["text_derivative"])
    if derivative is None or (
        derivative["provenance"].get("derived_from") != row["file"]
    ):
        problems.append("derivative")
    elif statement not in derivative["text"]:
        problems.append("statement")
    return problems


def test_dropped_covers_name_their_edition():
    """Review r3 note 1: 28 IRS extracts carried one 873,242-byte cover
    JPEG. Each now drops it, and a kept page's own text, in its pinned
    derivative, states the edition; the rest keep their first page."""
    inventory = read_inventory()
    rows = {row["file"]: row for row in inventory if "file" in row}
    dropped = {
        name: row
        for name, row in rows.items()
        if "cover_dropped" in structured_provenance(row)
    }
    derivatives = {
        name: {
            "provenance": row["provenance"],
            "text": " ".join((CAPTURE_DIRECTORY / name).read_text().split()),
        }
        for name, row in rows.items()
        if structured_provenance(row).get("derived_from") in dropped
    }
    problems = {
        name: found
        for name, row in dropped.items()
        if (found := dropped_cover_problems(row, derivatives))
    }
    assert problems == {}
    assert set(dropped) == (
        {f"irs_pub926_{year}_extract.pdf" for year in range(2008, 2026)}
        | {f"irs_pub15_{year}_extract.pdf" for year in range(2017, 2026)}
        | {"ce1c_irs_pub51_2023_extract.pdf"}
    )
    for name, row in dropped.items():
        assert 1 not in row["provenance"]["original_pdf_pages"]
        assert len(row["provenance"]["chain"]) == 2
        assert row["bytes"] < 200_000, name


@settings(deadline=None)
@given(
    st.sampled_from(["926", "15", "51"]),
    st.integers(2008, 2025),
    st.integers(-1, 1),
    st.sampled_from(["", "March "]),
    st.sampled_from(["kept", "absent", "other_extract", "no_derivative"]),
)
def test_dropped_cover_checker_flags_unstated_editions(
    publication, year, year_shift, month, text
):
    """The note 1 checker is the test's oracle."""
    name = f"irs_pub{publication}_{year}_extract.pdf"
    statement = f"Publication {publication} ({month}{year + year_shift})"
    row = {
        "file": name,
        "provenance": {
            "cover_dropped": {
                "edition_statement": statement,
                "text_derivative": name + ".txt",
            }
        },
    }
    texts = {
        "kept": f"INVENTED Page 3 {statement} INVENTED",
        "absent": "INVENTED Page 3 INVENTED",
    }
    derivatives = {}
    if text != "no_derivative":
        source = "INVENTED_other.pdf" if text == "other_extract" else name
        derivatives[name + ".txt"] = {
            "provenance": {"derived_from": source},
            "text": texts.get(text, texts["kept"]),
        }
    expected = year_shift != 0 or text != "kept"
    assert bool(dropped_cover_problems(row, derivatives)) == expected
    del row["provenance"]["cover_dropped"]
    assert dropped_cover_problems(row, derivatives) == []


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
def test_real_ranges_partition_each_family(registry, data):
    family = data.draw(st.sampled_from(registry.families))
    rules = sorted(
        [r for r in registry.rules if r.family == family],
        key=lambda r: (r.effective_start, r.rule_id),
    )
    for left, right in zip(rules, rules[1:], strict=False):
        assert left.effective_end + timedelta(days=1) == right.effective_start


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
    # Review r3 M3: the families whose boundary clauses key on payment or
    # taxable year, beyond the five the review found hard-coded here.
    for family in PAYMENT_DATE_FAMILIES:
        assert axes[family] == {"payment_date"}, family
    for family in TAXABLE_YEAR_FAMILIES:
        assert axes[family] == {"taxable_year_start"}, family
    # The notes give calendar dates (Oct. 4, 1976; Oct. 1, 2008), so both
    # wordings govern part of each boundary year.
    assert axes[PASSIVE] == {"payment_date"}
    for year in (1976, 2008):
        assert len(registry.lookup(PASSIVE, year)) == 2
    with pytest.raises(UnknownIdentifierError):
        registry.lookup("self_employment_public_ofice", 2000)


PAYMENT_DATE_FAMILIES = (
    "agricultural_service",
    "domestic_service",
    "family_service",
    "fishing_crew_share_service",
    "self_employment_insurance_termination",
)
TAXABLE_YEAR_FAMILIES = (
    "electing_church_employee_service",
    "self_employment_church_sect_exemption",
    "self_employment_clergy_gross_concept",
    "self_employment_community_income",
    "self_employment_farm_rental_participation",
    "self_employment_foreign_911_income",
    "self_employment_health_insurance_deduction",
    "self_employment_limited_partner",
    "self_employment_optional_methods",
    "self_employment_qualified_joint_venture",
    "self_employment_units",
)
MONTH_NAMES = (
    "January February March April May June July August September October "
    "November December"
).split()
MONTH_ABBREVIATIONS = (
    "Jan. Feb. Mar. Apr. May June July Aug. Sept. Oct. Nov. Dec.".split()
)
CLAUSE_KINDS = (
    (
        "payment_date",
        r"\b(paid|payments?( made)?|received)\s+(on or )?(after|before)",
    ),
    (
        "taxable_year_start",
        r"\btaxable years?\s+(beginning|that begin|which begin|that include"
        r"|ending)(\s+(on or )?(after|before))?",
    ),
    ("service_date", r"\bservices?( performed)?\s+(on or )?(after|before)"),
)


def clause_kinds(text, days):
    """The date axes the effective-date clauses printing these days use.

    A clause is the 60 characters before a printed date (full or
    abbreviated month). Kinds are payment, taxable-year or service.
    """
    found = set()
    for day in days:
        for names in (MONTH_NAMES, MONTH_ABBREVIATIONS):
            printed = f"{names[day.month - 1]} {day.day}, {day.year}"
            for hit in re.finditer(re.escape(printed), text):
                before = text[max(0, hit.start() - 60) : hit.start()]
                found |= {
                    kind
                    for kind, pattern in CLAUSE_KINDS
                    if re.search(f"(?:{pattern})\\s*$", before, re.I)
                }
    return found


def quote_kind(quote):
    """The axis a pinned clause's own wording uses, or None for a date."""
    for kind, pattern in CLAUSE_KINDS:
        if re.search(pattern, quote, re.I):
            return kind
    return None


def capture_text(name, cache):
    if name not in cache:
        path = CAPTURE_DIRECTORY / name
        if path.suffix == ".pdf":
            # A PDF's pinned text derivative, where it has one.
            path = path.with_name(path.name + ".txt")
        if not path.exists():
            cache[name] = ""
        elif path.suffix in {".txt", ".xml"}:
            cache[name] = " ".join(path.read_text(errors="replace").split())
        else:
            cache[name] = source_text(path)
    return cache[name]


def axis_problems(rows, texts):
    """Internal family boundaries whose clauses use another axis.

    For each boundary, the later row's ``parameters.boundary_clause`` pins
    the governing clause (quoted from a capture the row cites), and its
    wording must use the family's axis, be a bare date, or come with an
    ``axis_exception`` reason. Without a pin, the effective-date clauses
    that the two rows' captures print for the boundary must all use the
    family's axis. Where they print clauses on more than one axis, several
    amendments share the date and only a pin says which one governs
    (review r4 M-1).
    """
    problems = []
    by_family = {}
    for row in rows:
        by_family.setdefault(row["family"], []).append(row)
    for members in by_family.values():
        members.sort(key=lambda row: row["effective_start"])
        axes = {
            row["parameters"].get("effective_basis", "service_date")
            for row in members
        }
        axis = axes.pop() if len(axes) == 1 else None
        for left, right in zip(members, members[1:], strict=False):
            boundary = date.fromisoformat(right["effective_start"])
            pin = right["parameters"].get("boundary_clause")
            if pin is not None:
                cited = {c["capture"] for c in right["citations"]}
                kind = quote_kind(pin["citation"]["quote"])
                if pin["citation"]["capture"] not in cited:
                    problems.append((right["rule_id"], "pin not cited"))
                if (
                    kind not in {None, axis}
                    and not str(pin.get("axis_exception", "")).strip()
                ):
                    problems.append((right["rule_id"], f"pin uses {kind}"))
                continue
            captures = {
                c["capture"] for row in (left, right) for c in row["citations"]
            }
            kinds = set()
            for capture in captures:
                kinds |= clause_kinds(
                    capture_text(capture, texts),
                    (boundary - timedelta(days=1), boundary),
                )
            if len(kinds) > 1:
                problems.append((right["rule_id"], "mixed kinds need a pin"))
            elif kinds and axis not in kinds:
                problems.append((right["rule_id"], sorted(kinds)))
    return problems


def test_family_axes_follow_their_boundary_clauses():
    """Review r3 M3 and r4 M-1: a family uses the axis its boundary
    clauses use, and a boundary whose clauses mix axes is pinned.

    On ea599b92's registry this checker flags 38 boundaries, among them
    the insurance termination, agricultural, domestic and family payment
    boundaries and the taxable-year boundaries round 3 lists; on
    fd5b7b2a's it flags the 17 unpinned boundaries whose clauses mix axes.
    """
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    assert axis_problems(rows, {}) == []
    pinned = [
        r["rule_id"] for r in rows if "boundary_clause" in r["parameters"]
    ]
    assert sorted(pinned) == [
        "clergy_1973_1981",
        "clergy_1982_2026",
        "domestic_service_1995",
        "electing_church_1984_1985",
        "electing_church_1986_2026",
        "election_work_1978",
        "election_work_1995",
        "federal_1984_1986",
        "federal_1987_2026",
        "fishing_crew_share_service_1995",
        "international_organization_service_1995",
        "newspaper_service_1996",
        "nonprofit_1984_2026",
        "nonresident_alien_vocational_service_1987",
        "nonresident_alien_vocational_service_1988_1110",
        "religious_order_1984_2026",
        "se_clergy_gross_concept_1973_1987",
        "se_clergy_gross_concept_1987_2026",
        "se_conservation_reserve_2008_2026",
        "se_foreign_income_1984_2026",
        "se_health_insurance_2010",
        "se_health_insurance_2011_2026",
        "se_nonresident_alien_1983_2026",
        "se_optional_2008_2026",
        "se_units_1984_1985",
        "state_local_1983_1991",
    ]
    excepted = [
        r["rule_id"]
        for r in rows
        if "axis_exception" in r["parameters"].get("boundary_clause", {})
    ]
    assert sorted(excepted) == [
        "clergy_1973_1981",
        "domestic_service_1995",
        "electing_church_1984_1985",
        "election_work_1978",
        "nonresident_alien_vocational_service_1987",
        "se_units_1984_1985",
    ]


def test_domestic_minor_exclusion_reaches_only_service_after_1994(registry):
    """Review r4 M-1: 410(a)(21) applies "to services performed after Dec.
    31, 1994", so a payment-date lookup of 1995 pay for 1994 babysitting
    must not reach the under-18 exclusion. INVENTED: a 16-year-old's
    December 1994 babysitting, paid $1,200 on 1995-01-06."""
    (rule,) = registry.lookup_date("domestic_service", date(1995, 1, 6))
    minor = next(
        c
        for c in rule.cases
        if c["case_id"] == "minor_not_principal_occupation"
    )
    condition = minor["when"]["services_performed_date"]
    assert not service_date_condition_holds(condition, date(1994, 12, 20))
    assert service_date_condition_holds(condition, date(1995, 1, 2))
    clause = rule.parameters["boundary_clause"]
    assert "services performed after Dec. 31, 1994" in (
        clause["citation"]["quote"]
    )
    assert clause["axis_exception"].strip()


@settings(deadline=None)
@given(
    st.sampled_from(sorted(EFFECTIVE_BASES)),
    st.sampled_from(["payment", "taxable", "service", "none"]),
    st.sampled_from(["payment", "taxable", "service", "none"]),
    st.booleans(),
    st.booleans(),
)
def test_axis_checker_flags_clauses_on_another_axis(
    axis, wording, other, pinned, excepted
):
    """The M3 and M-1 checker is the test's oracle: an unpinned boundary
    passes only when every clause printed for it uses the family's axis."""
    clauses = {
        "payment": "INVENTED amendment applicable to remuneration paid after",
        "taxable": "INVENTED amendment applies to taxable years beginning "
        "after",
        "service": "INVENTED amendment applies to services performed after",
        "none": "INVENTED amendment enacted",
    }
    kinds = {
        "payment": "payment_date",
        "taxable": "taxable_year_start",
        "service": "service_date",
        "none": None,
    }
    capture = "INVENTED_note.html"
    texts = {
        capture: f"{clauses[wording]} December 31, 1987. "
        f"{clauses[other]} December 31, 1987."
    }
    rows = []
    for start, end in (
        ("1968-01-01", "1987-12-31"),
        ("1988-01-01", "2026-12-31"),
    ):
        rows.append(
            {
                "rule_id": f"INVENTED_{start[:4]}",
                "family": "INVENTED_family",
                "effective_start": start,
                "effective_end": end,
                "citations": [{"capture": capture}],
                "parameters": (
                    {} if axis == "service_date" else {"effective_basis": axis}
                ),
            }
        )
    if pinned:
        pin = {"citation": {"capture": capture, "quote": clauses[wording]}}
        if excepted:
            pin["axis_exception"] = "INVENTED reason"
        rows[1]["parameters"]["boundary_clause"] = pin
    flagged = bool(axis_problems(rows, texts))
    if pinned:
        mismatch = kinds[wording] not in {None, axis}
        assert flagged == (mismatch and not excepted)
    else:
        printed = {kinds[wording], kinds[other]} - {None}
        assert flagged == (bool(printed) and printed != {axis})


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
    # r4 M-4 adds the two self_employment_nonresident_alien rows.
    assert checked == 58


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
    # r4 M-2 adds NONPROFIT_RETROACTIVE_HIRE_UNSETTLED's two readings to
    # each pre-1984 nonprofit row; the r4 sweep adds the Army Corps student
    # aide and the pre-1996 dealer holdings questions; round 5 adds the
    # pre-1998 insurance termination payment (review r4 low 10); the review
    # r5 fix adds the 3121(k)(4)(C) period of a deemed nonprofit
    # certificate (52); the review r5 sweep adds 16 open cases with two
    # readings each (84). The review r6 fix settles the Army Corps aide
    # case in four rows and the (k)(4)(C) case, and drops the 1968-1972
    # CNMI ministry case (72); it opens the 521 cooperative, the pre-1983
    # agreement exemption and the non-individual farm arrangement (78), and
    # the sect member's 1984-85 church income and the 1973-1987 pensions
    # and church annuity contributions (84), and a 401(a) trust's small
    # remuneration in the 1978 and 1984 nonprofit rows (88), and the
    # clergy rows' agreement exemption before 1983-04-20 (92), and a minor
    # newspaper direct seller after 1982 (94). The review r7 fix dates the
    # agreement exemption from 26 U.S.C. 1401(c) and 42 U.S.C. 433 and
    # closes the three pre-1983 agreement cases (88), and closes the
    # 1973-1987 church annuity contributions on 411(a)'s start from gross
    # income (86), and splits the minor newspaper direct-seller case by
    # 410(a)(14) arrangement (review r7 M-7; 88), and opens a 521
    # cooperative's small remuneration in the 1978 and 1984 rows (review r7
    # M-8(e); 92).
    assert described == 92


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


NESTED_OPTION_KEYS = {"named_options", "named_alternatives"}


def nested_option_problems(parameters):
    """Option records below the top level that do not name an operative
    option with a basis (review r3 low 3)."""
    problems = []

    def walk(value, path):
        if isinstance(value, dict):
            if path and NESTED_OPTION_KEYS & set(value):
                key = next(k for k in value if k in NESTED_OPTION_KEYS)
                names = option_names(value[key])
                if value.get("operative") not in names:
                    problems.append((".".join(path), "operative"))
                basis = value.get("basis", value.get("resolution", ""))
                if not str(basis).strip():
                    problems.append((".".join(path), "basis"))
            for child_key, child in value.items():
                walk(child, (*path, child_key))
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child, path)

    walk(parameters, ())
    return problems


def test_nested_option_records_name_their_operative_option():
    """Review r3 low 3: agricultural_service_1988's SSR 95-3P date and
    student_service_1973's auxiliary-organization start sat in nested
    records the operative-reading check did not reach."""
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    problems = {
        row["rule_id"]: found
        for row in rows
        if row["open_reason"] is None
        and (found := nested_option_problems(row["parameters"]))
    }
    assert problems == {}
    agri = next(r for r in rows if r["rule_id"] == "agricultural_service_1988")
    ruling = agri["parameters"]["ruling_effective_date_axis"]
    assert ruling["operative"] == "services_performed_date"
    assert ruling["basis"].startswith("CE1's ruling")


@settings(deadline=None)
@given(
    st.sampled_from(["named_options", "named_alternatives"]),
    st.sampled_from(["first", "second", "missing", "INVENTED_other"]),
    st.sampled_from(["basis", "resolution", None]),
    st.booleans(),
)
def test_nested_option_checker_requires_an_operative_option(
    key, operative, basis, nested
):
    """The low 3 checker is the test's oracle."""
    record = {key: {"first": "INVENTED", "second": "INVENTED"}}
    if operative != "missing":
        record["operative"] = operative
    if basis:
        record[basis] = "INVENTED basis"
    parameters = {"INVENTED_record": record} if nested else record
    expected = nested and (operative not in {"first", "second"} or not basis)
    assert bool(nested_option_problems(parameters)) == expected


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
    assert "se_units_1984_1985" in resolved
    # Review r7 M-6: casual_service_1968 names its chosen reading of Pub. L.
    # 95-216 section 351(d) and the conjunctive reading it does not apply.
    assert "casual_service_1968" in resolved
    assert len(resolved) == 10


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
# Review r7 low 8: a sentence run into the next one ("duties.Noncovered",
# "(3121(r)(1)(B)).POMS"). A digit before the point is a section number
# ("section 4.B"), so it does not count.
FUSED_SENTENCE = re.compile(r"[a-z)]\.[A-Z]")
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
    """Words or citations run into a number, or a sentence run into the
    next, in prose (text with a space), and words run into a number in an
    identifier. Links and anchors are skipped."""
    if " " in text.strip():
        plain = LINKS.sub(" ", text)
        return (
            FUSED_PROSE.findall(plain)
            + FUSED_WORDS.findall(plain)
            + FUSED_PAREN_YEAR.findall(plain)
            + FUSED_SENTENCE.findall(plain)
        )
    return FUSED_IDENTIFIER.findall(text) + FUSED_PAREN_YEAR.findall(text)


def test_published_prose_has_no_fused_tokens():
    """Review r2 low 10: no word or citation runs into a number, and
    (review r7 low 8) no sentence runs into the next.

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
    assert fused_tokens(f"INVENTED rule {number} applies.Noncovered text")
    assert fused_tokens(f"INVENTED (see {word} {number}).POMS text")
    assert not fused_tokens(f"INVENTED rule {number} applies. Noncovered")
    assert not fused_tokens(f"INVENTED Supplement {year}, section 4.B")


VOCATIONAL = "nonresident_alien_vocational_service"


def test_vocational_readings_agree_before_1987_and_refuse_between(registry):
    """Review r2 low 9 and r3 M5: both readings settle what they share.

    Pub. L. 100-647 section 1001(d) names Reform Act section 123, so the
    M-class exclusion reaches no service before taxable years beginning
    after 1986. From 1987 to November 9, 1988 only authorized M-1 service
    for the admission purpose refuses, and from enactment, November 10,
    1988 (the extract's "Approved November 10, 1988"), both readings
    exclude it.
    """
    rows = {r.rule_id: r for r in registry.rules if r.family == VOCATIONAL}
    early = rows["nonresident_alien_vocational_service_1968"]
    unsettled = rows["nonresident_alien_vocational_service_1987"]
    later = rows["nonresident_alien_vocational_service_1988_1110"]
    agree = date.fromisoformat(early.parameters["readings_agree_before"])
    assert "M-1" in early.parameters["visa_classes"]
    assert "M" not in early.parameters["excluded_visa_classes"]
    for year in range(1968, agree.year):
        (rule,) = registry.lookup(VOCATIONAL, year)
        assert rule.resolve(())["consequence"] == "covered"
    assert unsettled.open_reason is None
    (case,) = unsettled.cases
    starts = {
        name: date.fromisoformat(start)
        for name, start in unsettled.parameters[
            "m1_exclusion_start_by_reading"
        ].items()
    }
    assert set(starts) == {o["name"] for o in case["open_alternatives"]}
    assert min(starts.values()) == agree == unsettled.effective_start
    assert max(starts.values()) == later.effective_start
    assert unsettled.effective_end + timedelta(days=1) == later.effective_start
    for day in (agree, date(1988, 11, 9)):
        (rule,) = registry.lookup_date(VOCATIONAL, day)
        with pytest.raises(OpenRuleError, match="VOCATIONAL_M_CLASS"):
            rule.resolve({case["case_id"]})
        # M-2 and other service: not excluded under either reading.
        assert rule.resolve(())["consequence"] == "covered"
    for day in (date(1988, 11, 10), date(1988, 12, 31), date(2000, 1, 1)):
        (rule,) = registry.lookup_date(VOCATIONAL, day)
        assert rule is later
        purpose = {"m1_admission_purpose_service"}
        assert rule.resolve(purpose)["consequence"] == "noncovered"
    assert [r.rule_id for r in registry.lookup(VOCATIONAL, 1988)] == [
        unsettled.rule_id,
        later.rule_id,
    ]
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
    "condition_cases",
    "boundary_clause",
}
# Review r3 M2: the words and keys reach "if", "when", "where" and
# "requires", and the keys are the ones rows with cases tie.
CONDITION_KEY = re.compile(
    r"(^|_)(conditions?|requires_all|requires?|required|any_of|"
    r"exceptions?|if_applies)$"
)
CONDITION_WORDS = re.compile(
    r"\b(only when|only if|unless|except|excepts|excepted|is excluded|"
    r"are excluded|excludes|remains excluded|depends on|if|when|whenever|"
    r"where|provided that|requires?)\b",
    re.IGNORECASE,
)


# Review r6 M-7: the worded-condition guard also reads "exclude",
# "excluded", "required", "only for" and "subject to", and reads
# snake_case as words, since "_" is a word character.
WORDED_CONDITION = re.compile(
    r"\b(only when|only if|only for|unless|except|excepts|excepted|"
    r"exclude|excluded|excludes|remains excluded|depends on|if|when|"
    r"whenever|where|provided that|requires?|required|subject to)\b",
    re.IGNORECASE,
)


def states_condition(text):
    """Whether a text, snake_case read as words, states a condition."""
    return bool(WORDED_CONDITION.search(text.replace("_", " ")))


# Review r7 M-10(c): the parameter guard also reads "only" and "limited"
# (mutant D6b's untied "limited to ministers under 18"). Both guards read
# a fixed word list, so a condition worded with none of the listed words
# stays unseen; the PR states that limit. Reasons keep WORDED_CONDITION.
PARAMETER_CONDITION_WORDS = re.compile(r"\b(only|limited)\b", re.IGNORECASE)


def states_parameter_condition(text):
    """Whether a parameter key or text states a condition: a word of
    WORDED_CONDITION, or "only" or "limited"."""
    return states_condition(text) or bool(
        PARAMETER_CONDITION_WORDS.search(text.replace("_", " "))
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
    if _holds_condition_record(row["parameters"]):
        signals.append("parameter record with a when key")
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
    """Review r3 M2: a case-free basis quotes the passage it rests on.

    At ea599b92 the widened detector flags eight rows, among them
    se_community_income_2004_2026 and se_units_1984_1985, and the four
    bases there are prose.
    """
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    assert rows_missing_condition_cases(rows) == {}
    based = []
    for row in rows:
        if "case_free_basis" in row["parameters"]:
            based.append(row["rule_id"])
            assert not row["cases"]
            assert row["consequence"] not in {"noncovered", "deferred"}
            leaves = parameter_leaves(row["parameters"])
            assert not any(v in CONSEQUENCE_VALUES for _, v in leaves)
            basis = row["parameters"]["case_free_basis"]
            assert set(basis) == {"explanation", "citation"}
            cited = basis["citation"]
            assert cited["capture"] in {c["capture"] for c in row["citations"]}
            text = source_text(CAPTURE_DIRECTORY / cited["capture"])
            assert " ".join(cited["quote"].split()) in text
    # The review r5 sweep gives the partner-death row a case.
    assert len(based) == 8
    assert not set(based) & {
        "se_community_income_1968_1979",
        "se_community_income_2004_2026",
    }


# Review r6 low 2: registry text cites sources and cases, never a builder's
# scratch notes.
SCRATCH_NOTE = re.compile(
    r"\bNOTE N-?\d+|\bN-TIP-\d|table\.md|\bworker \d+\b|"
    r"\bdecision D\d|\bfindings N-"
)


def test_registry_text_cites_no_scratch_note():
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    hits = [
        (row["rule_id"], match.group(0))
        for row in rows
        for match in SCRATCH_NOTE.finditer(json.dumps(row))
    ]
    assert hits == []


def unread_trigger_fact_problems(row):
    """Trigger facts no case reads and no reason names, and reasons for
    facts a case reads (review r5 item 7).

    A row lists the facts that decide it. A fact no case reads either
    plays another role (the amount a threshold compares, the taxable-year
    axis, a fact another family reads) or is a condition no case carries,
    the gap that hid H-6's federal level. So each unread fact needs its
    reason in ``parameters.unread_trigger_facts``.
    """
    read = {fact for case in row["cases"] for fact in case["when"]}
    unread = set(row["trigger_facts"]) - read
    reasons = row["parameters"].get("unread_trigger_facts", {})
    problems = [(fact, "unread, no reason") for fact in unread - set(reasons)]
    problems += [(fact, "read by a case") for fact in set(reasons) & read]
    problems += [
        (fact, "not a trigger fact")
        for fact in set(reasons) - set(row["trigger_facts"])
    ]
    problems += [
        (fact, "empty reason")
        for fact, reason in reasons.items()
        if not (isinstance(reason, str) and reason.strip())
    ]
    return sorted(problems)


def test_every_trigger_fact_is_read_by_a_case_or_named_with_its_reason():
    """Review r5 item 7: every trigger fact a row lists is read by one of
    its cases' `when`, or named with its reason. All four federal rows
    listed government_level and no case read it until the r5 fix (H-6)."""
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    assert {
        row["rule_id"]: found
        for row in rows
        if (found := unread_trigger_fact_problems(row))
    } == {}
    federal = [r for r in rows if r["family"] == "federal_retirement_service"]
    for row in federal:
        assert "government_level" not in row["parameters"].get(
            "unread_trigger_facts", {}
        )
    assert (
        sum(
            len(row["parameters"].get("unread_trigger_facts", {}))
            for row in rows
        )
        # Review r7 M-8: the open cases of the three nonprofit rows now
        # read the amount, and the rental row's non-individual case reads
        # material participation (369 -> 365).
        == 365
    )


# Review r6 M-1: a pinned sample of unread-fact reasons (seed 20261102,
# 24 of 374) and the phrases each must keep. A reason emptied of its
# content no longer names the provision or case that accounts for the
# fact.
UNREAD_REASON_ANCHORS = {
    ("communist_organization_service_1968", "historical_fica_treatment"): (
        "410(a)(17)",
    ),
    ("domestic_service_1995", "domestic_service"): (
        "domestic_farm_service",
        "410(a)(21)",
    ),
    ("election_work_1978", "section_218_group"): ("418(b)(5)", "418(d)(4)"),
    (
        "fishing_crew_share_service_1968",
        "fishing_additional_cash_conditions",
    ): ("the row is open with no",),
    ("fishing_crew_share_service_1989", "services_performed_date"): (
        "The row is on the payment-date",
    ),
    ("fishing_crew_share_service_1995", "employee_self_or_mixed"): (
        "410(a)(20)",
    ),
    ("fishing_crew_share_service_1995", "reporting_unit"): (
        "Reporting is not a coverage condition.",
    ),
    ("se_community_income_2004_2026", "joint_business_distributive_shares"): (
        "business_operator_spouse",
    ),
    ("se_director_timing_1988_1990", "employee_self_or_mixed"): (
        "se_ordinary_employee_1968_2026",
        "411(c)(2)",
    ),
    ("se_director_timing_1988_1990", "industry"): ("403(f)(5)(E)",),
    ("se_director_timing_1991_2026", "amount"): (
        "The director fees the row times;",
    ),
    ("se_foreign_income_1968_1972_open", "foreign_earned_income_exclusion"): (
        "The row is open (no cases);",
    ),
    ("se_foreign_income_1982_1983", "foreign_earned_income_exclusion"): (
        "The row is open (no cases);",
    ),
    ("se_health_insurance_2011_2026", "taxable_year"): ("taxable_year_start",),
    ("se_joint_venture_1968_2006", "assignment"): (
        "The partnership and community-income families assign",
    ),
    ("se_joint_venture_2007_2026", "taxable_year_start"): ("lookup_date",),
    ("se_optional_1973_2007", "amount"): ("condition_cases",),
    ("se_optional_1973_2007", "taxable_year_start"): (
        "lookup_date",
        "effective_basis",
    ),
    ("se_optional_2008_2026", "agricultural_service"): (
        "selects farm versus nonfarm optional computation;",
    ),
    ("se_partner_death_1968_2026", "partner_death_date"): (
        "share_after_death_month",
        "partnership_status",
    ),
    ("se_passive_income_1968_1976", "trade_or_business"): (
        "se_base_definition_1968_2026",
        "411(a)(2)",
    ),
    ("se_possessions_931_1987_2026", "residence_period"): (
        "country_of_residence",
        "411(a)(8)",
    ),
    ("se_rental_income_1968_1996", "trade_or_business"): (
        "411(a)(1)",
        "real_estate_dealer_status",
    ),
    ("statutory_homeworker_service_1978", "reporting_unit"): (
        "employer_employee_year",
    ),
}


def test_unread_fact_reasons_keep_their_content():
    rows = {
        r["rule_id"]: r
        for r in json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    }
    for (rule_id, fact), anchors in UNREAD_REASON_ANCHORS.items():
        reason = rows[rule_id]["parameters"]["unread_trigger_facts"][fact]
        for anchor in anchors:
            assert anchor in reason, (rule_id, fact, anchor)


# Review r6 M-1: a pinned sample of condition_cases ties (seed 20261102,
# 15 of 162, plus clergy_1982_2026.cantor), each to its cases and facts.
PINNED_TIES = {
    ("agricultural_service_1988", "seasonal_exception_facts"): {
        "seasonal_hand_harvest_under_150": ["agricultural_service", "amount"]
    },
    ("clergy_1982_2026", "cantor"): {
        "ministry_without_exemption_or_vow": ["ministerial_service"],
        "non_ministerial_service": ["ministerial_service"],
    },
    ("election_work_1968", "agreement_has_no_exclusion"): {
        "agreement_without_election_exclusion": ["section_218_position"]
    },
    ("election_work_1978", "scope"): {
        "agreement_with_lower_threshold": [
            "election_work",
            "government_level",
        ],
        "agreement_with_statutory_threshold": [
            "election_work",
            "government_level",
        ],
        "outside_agreement": ["election_work", "government_level"],
    },
    ("election_work_1995", "scope"): {
        "agreement_with_lower_threshold_member": [
            "election_work",
            "government_level",
        ],
        "agreement_with_lower_threshold_nonmember": [
            "election_work",
            "government_level",
        ],
        "agreement_with_statutory_threshold": [
            "election_work",
            "government_level",
        ],
        "outside_agreement_member": ["election_work", "government_level"],
        "outside_agreement_nonmember": ["election_work", "government_level"],
    },
    ("family_service_1968", "spouse_trade_business_excluded"): {
        "spouse_employee": ["family_service"]
    },
    (
        "fishing_crew_share_service_1989",
        "wage_employment_excluded_when_arrangement_qualifies",
    ): {
        "catch_share_1996_clarification": [
            "fishing_catch_share_arrangement",
            "historical_fica_treatment",
        ],
        "catch_share_payor_treated_as_fica": [
            "fishing_catch_share_arrangement",
            "historical_fica_treatment",
        ],
    },
    ("religious_order_1968_1983", "election_covers"): {
        "vow_duties_with_3121r_election": [
            "clergy_or_religious_exemption",
            "religious_order_service",
        ],
        "vow_duties_without_election": ["clergy_or_religious_exemption"],
        "vowed_member_outside_3121r2_definition": ["religious_order_service"],
    },
    ("se_foreign_income_1973_1981", "income_tax_exclusion_disregarded"): {
        "us_resident_entire_taxable_year": ["residence_period"]
    },
    ("se_joint_venture_2007_2026", "required_conditions"): {
        "qualified_joint_venture": [
            "joint_return",
            "material_participation",
            "partnership_status",
            "qualified_joint_venture_election",
            "trade_or_business",
        ]
    },
    ("se_passive_income_1968_1976", "stock_dividends_excluded"): {
        "specified_dividends": ["dividend_or_interest_income"]
    },
    ("se_rental_income_1996_2026", "real_estate_dealer_exception"): {
        "real_estate_dealer_rentals": ["real_estate_dealer_status"]
    },
    (
        "se_rental_income_1996_2026",
        "rental_income_and_attributable_deductions_excluded",
    ): {"real_estate_rentals": ["rental_income"]},
    ("se_treaty_fishing_1968_2026", "qualified_entity_conditions"): {
        "section_7873_exempt_income": ["tribal_fishing_qualified_entity"]
    },
    ("state_local_1968_1983", "scope"): {
        "no_section_218_agreement": ["government_level"]
    },
}


def test_pinned_ties_name_their_cases():
    rows = {
        r["rule_id"]: r
        for r in json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    }
    for (rule_id, key), cases in PINNED_TIES.items():
        tie = rows[rule_id]["parameters"]["condition_cases"][key]["cases"]
        assert {c: sorted(f) for c, f in tie.items()} == cases, (rule_id, key)


@settings(deadline=None)
@given(
    st.sampled_from(["amount", "government_level", "taxable_year_start"]),
    st.sampled_from(["no_reason", "reason", "read", "read_and_reason"]),
)
def test_unread_trigger_fact_checker_flags_every_gap(fact, state):
    """The checker is the test's oracle, so its own cases are tested on an
    INVENTED row."""
    row = {
        "trigger_facts": [fact, "occupation"],
        "cases": [{"when": {"occupation": "INVENTED"}}],
        "parameters": {},
    }
    if state.startswith("read"):
        row["cases"][0]["when"][fact] = "INVENTED"
    if state in {"reason", "read_and_reason"}:
        row["parameters"]["unread_trigger_facts"] = {fact: "INVENTED reason"}
    flagged = unread_trigger_fact_problems(row)
    assert bool(flagged) == (state in {"no_reason", "read_and_reason"})


@settings(deadline=None)
@given(
    st.sampled_from(sorted(CONSEQUENCE_VALUES - {"open"})),
    st.sampled_from(
        [
            "",
            "unless the employer elects",
            "only when paid",
            "when a spouse manages it",
            "if the arrangement requires it",
        ]
    ),
    st.booleans(),
    st.booleans(),
)
def test_condition_detector_flags_every_signal(
    consequence, words, key, nested
):
    """The detector is the test's oracle, so its own signals are tested."""
    row = {
        "consequence": consequence,
        "description": f"INVENTED rule {words}".strip(),
        "parameters": {"required_conditions": ["a"]} if key else {},
        "open_reason": None,
        "cases": [],
    }
    if nested:
        row["parameters"]["INVENTED_branches"] = [{"when": "INVENTED"}]
    expected = (consequence == "noncovered") + bool(words) + key + nested
    assert len(condition_signals(row)) == expected
    flagged = rows_missing_condition_cases([{"rule_id": "INVENTED", **row}])
    assert bool(flagged) == bool(expected)
    with_case = {**row, "rule_id": "INVENTED", "cases": [{"case_id": "a"}]}
    assert rows_missing_condition_cases([with_case]) == {}


# Review r3 M1: on rows with cases, a parameter that names a condition must
# say where the condition is decided: in named cases (whose `when` carries
# the listed facts), by cited thresholds, or nowhere, with the reason.
CASE_CONDITION_KEY = re.compile(
    r"(^|_)(conditions?|requires_all|requires?|required|any_of|"
    r"exceptions?|if_applies)$"
)
# Review r4 M-5: top-level keys that describe a scope (applies_to,
# requires_*, *_excluded, non_*, *_scope, *_concept, *_exception, ...),
# which the leaf-name pattern above missed (H-C's applies_to).
SCOPE_KEY = re.compile(
    r"^non_|(^|_)(applies|requires?|required|excluded|exclusions?|scope|"
    r"concepts?|included|eligible|eligibility|disregarded|exceptions?|"
    r"limits?|criteria|test|approval|repealed|removed|available)(_|$)"
)
SCOPE_KEY_EXEMPT = {
    "unread_trigger_facts",
    "effective_basis",
    "effective_basis_description",
    "evidence_only_boundaries",
    "deferral_exceptions",
    "threshold_id",
}
TIE_KINDS = {"cases", "threshold_ids", "not_a_coverage_condition"}


def condition_parameters(parameters):
    """Top-level parameter keys holding a condition-named leaf.

    Named option records are readings, which the operative-reading checker
    covers, so they are skipped here.
    """
    leaves = {
        path[0]
        for path, _ in parameter_leaves(parameters)
        if path
        and path[0] not in SCOPE_KEY_EXEMPT
        and not OPTION_RECORDS.search(path[0])
        and CASE_CONDITION_KEY.search(path[-1])
    }
    scopes = {
        key
        for key in parameters
        if key not in PARAMETER_EVIDENCE | SCOPE_KEY_EXEMPT
        and not OPTION_RECORDS.search(key)
        and SCOPE_KEY.search(key)
    }
    # Review r5 item 7: a parameter whose text states a condition in words
    # (if, when, where, unless, except, requires ...) is a condition too,
    # whatever its key. section_2601d3_delay named the delay in prose and
    # no case carried it (H-7); only a "before 1987" text check saw it.
    worded = {
        key
        for key in parameters
        if key not in PARAMETER_EVIDENCE | SCOPE_KEY_EXEMPT
        and not OPTION_RECORDS.search(key)
        and (
            states_parameter_condition(key)
            or any(
                isinstance(value, str) and states_parameter_condition(value)
                for _, value in parameter_leaves({key: parameters[key]})
            )
        )
    }
    return leaves | scopes | worded


def condition_case_problems(row, threshold_ids):
    """Condition and scope parameters on a closed row left untied.

    A case-free row ties them to thresholds or to a reason (review r4 M-5).

    ``parameters.condition_cases`` maps each such key to one record:
    ``cases`` (case ID to the facts its ``when`` must carry),
    ``threshold_ids`` (thresholds the registry defines) or
    ``not_a_coverage_condition`` (the reason, in text).
    """
    if row["open_reason"] is not None:
        return []
    parameters = row["parameters"]
    ties = parameters.get("condition_cases", {})
    when = {case["case_id"]: set(case["when"]) for case in row["cases"]}
    problems = [
        (key, "untied")
        for key in sorted(condition_parameters(parameters))
        if key not in ties
    ]
    for key, tie in ties.items():
        if key not in parameters or key == "condition_cases":
            problems.append((key, "names no parameter"))
        if not (isinstance(tie, dict) and len(tie) == 1):
            problems.append((key, "one tie record"))
            continue
        ((kind, value),) = tie.items()
        if kind not in TIE_KINDS:
            problems.append((key, f"tie kind {kind}"))
        elif kind == "cases":
            if not value or not row["cases"]:
                problems.append((key, "no cases"))
            for case_id, facts in value.items():
                if case_id not in when:
                    problems.append((key, f"unknown case {case_id}"))
                elif not facts or not set(facts) <= when[case_id]:
                    problems.append((key, f"{case_id} lacks {facts}"))
        elif kind == "threshold_ids":
            if not value or not set(value) <= threshold_ids:
                problems.append((key, "unknown threshold"))
        elif not (isinstance(value, str) and value.strip()):
            problems.append((key, "reason"))
    return problems


def test_condition_parameters_on_case_rows_name_their_cases():
    """Review r3 M1: the detector reaches rows that have cases.

    At ea599b92 no row recorded these ties, so it flagged all 32 rows it
    reached then; se_community_income_1968_1979 gained cases since. With
    the scope keys and case-free rows of review r4 M-5 it flags 84 rows
    (186 keys) there and 79 rows (149 keys) at fd5b7b2a, among them every
    row the review's param_keys.txt lists.
    """
    raw = json.loads(REGISTRY_ARTIFACT.read_text())
    threshold_ids = {t["threshold_id"] for t in raw["thresholds"]}
    problems = {
        row["rule_id"]: found
        for row in raw["rules"]
        if (found := condition_case_problems(row, threshold_ids))
    }
    assert problems == {}
    tied = [
        row for row in raw["rules"] if "condition_cases" in row["parameters"]
    ]
    # The review r5 fix ties the four federal rows' scope and the
    # church cases se_units_1968_1983 now carries; its sweep ties three
    # more (communist 1968, casual 1978 and domestic 1994), and the
    # condition-word ties three more; the review r6 fix ties casual 1968's
    # payment-date threshold, and its widened word guard five more rows.
    assert len(tied) == 106
    assert all(row["open_reason"] is None for row in tied)
    # H-C: the 2018 tribal row's scope parameter names the case that reads
    # federal recognition.
    tribal = next(
        r
        for r in raw["rules"]
        if r["rule_id"] == "tribal_council_service_2018_0920"
    )
    assert tribal["parameters"]["condition_cases"]["applies_to"] == {
        "cases": {
            "no_section_418a_inclusion": [
                "tribal_council_service",
                "tribal_federal_recognition",
            ]
        }
    }


@settings(deadline=None)
@given(
    st.sampled_from(
        [
            "required_conditions",
            "exception",
            "notes",
            "if_applies",
            "applies_to",
            "non_recognized_groups",
            "wage_employment_excluded",
        ]
    ),
    st.sampled_from(
        [
            None,
            "cases",
            "missing_fact",
            "unknown_case",
            "threshold",
            "unknown_threshold",
            "reason",
            "blank_reason",
            "two_records",
        ]
    ),
    st.booleans(),
    st.booleans(),
)
def test_condition_case_checker_requires_a_tie(key, tie, with_cases, is_open):
    """The M1 checker is the test's oracle."""
    row = {
        "open_reason": "INVENTED question" if is_open else None,
        "cases": (
            [{"case_id": "invented_case", "when": {"amount": "INVENTED"}}]
            if with_cases
            else []
        ),
        "parameters": {key: ["INVENTED condition"]},
    }
    records = {
        "cases": {"cases": {"invented_case": ["amount"]}},
        "missing_fact": {"cases": {"invented_case": ["occupation"]}},
        "unknown_case": {"cases": {"invented_other": ["amount"]}},
        "threshold": {"threshold_ids": ["INVENTED_threshold"]},
        "unknown_threshold": {"threshold_ids": ["INVENTED_missing"]},
        "reason": {"not_a_coverage_condition": "INVENTED reason"},
        "blank_reason": {"not_a_coverage_condition": " "},
        "two_records": {
            "threshold_ids": ["INVENTED_threshold"],
            "not_a_coverage_condition": "INVENTED reason",
        },
    }
    if tie is not None:
        row["parameters"]["condition_cases"] = {key: records[tie]}
    problems = condition_case_problems(row, {"INVENTED_threshold"})
    if is_open:
        assert problems == []
        return
    flagged = key != "notes" and tie is None
    bad = tie in {
        "missing_fact",
        "unknown_case",
        "unknown_threshold",
        "blank_reason",
        "two_records",
    } or (not with_cases and tie in {"cases", "missing_fact"})
    assert bool(problems) == (flagged or bad)


@settings(deadline=None)
@given(
    st.sampled_from(
        [
            "unless",
            "only if",
            "where",
            "requires",
            "if",
            "excluded",
            "subject to",
            "only for",
            "required_if",
            "limited to",
            "only",
        ]
    ),
    st.sampled_from([None, "cases", "reason"]),
)
def test_condition_case_checker_flags_a_worded_condition(word, tie):
    """Review r5 item 7: a parameter named like a note but stating a
    condition in words (the H-7 shape) needs a tie, by more than a text
    check."""
    row = {
        "open_reason": None,
        "cases": [
            {"case_id": "invented_case", "when": {"amount": "INVENTED"}}
        ],
        "parameters": {
            "invented_delay": f"coverage starts later {word} INVENTED",
        },
    }
    if tie == "cases":
        row["parameters"]["condition_cases"] = {
            "invented_delay": {"cases": {"invented_case": ["amount"]}}
        }
    elif tie == "reason":
        row["parameters"]["condition_cases"] = {
            "invented_delay": {"not_a_coverage_condition": "INVENTED"}
        }
    assert bool(condition_case_problems(row, set())) == (tie is None)


# Review r6 M-7: an unread-fact reason that states a condition says where
# it is decided (a case of the row, a family or a threshold) or that
# nothing depends on the fact.
NO_DEPENDENCE = re.compile(
    r"no case|excludes nothing|no exclusion|not a (coverage |separate )?"
    r"condition|no condition|whatever|whoever|no 410|no paragraph|"
    r"no reading|no source|no captured source|is open|does not depend|"
    r"carried by|entry fact",
    re.IGNORECASE,
)


def unread_reason_problems(row, families, thresholds):
    names = {c["case_id"] for c in row["cases"]} | families | thresholds
    return sorted(
        fact
        for fact, reason in row["parameters"]
        .get("unread_trigger_facts", {})
        .items()
        if states_condition(reason)
        and not any(name in reason for name in names)
        and not NO_DEPENDENCE.search(reason)
    )


def test_unread_reasons_that_state_a_condition_say_where_it_is_decided():
    raw = json.loads(REGISTRY_ARTIFACT.read_text())
    families = {r["family"] for r in raw["rules"]}
    thresholds = {t["threshold_id"] for t in raw["thresholds"]}
    assert {
        row["rule_id"]: found
        for row in raw["rules"]
        if (found := unread_reason_problems(row, families, thresholds))
    } == {}


@settings(deadline=None)
@given(
    st.sampled_from(
        [
            "INVENTED amount the threshold compares",
            "excluded only if INVENTED",
            "required_when_INVENTED",
            "excluded when INVENTED; invented_case decides it",
            "subject to INVENTED; no case depends on it",
        ]
    )
)
def test_unread_reason_checker_needs_a_pointer(reason):
    row = {
        "cases": [{"case_id": "invented_case"}],
        "parameters": {"unread_trigger_facts": {"amount": reason}},
    }
    flagged = bool(unread_reason_problems(row, set(), set()))
    assert flagged == (
        reason in {"excluded only if INVENTED", "required_when_INVENTED"}
    )


def boundary_clause_problems(row):
    """A pinned boundary clause that states a condition carries an
    axis_exception or a condition_cases tie (review r6 M-7)."""
    pin = row["parameters"].get("boundary_clause")
    if pin is None or not states_condition(pin["citation"].get("quote", "")):
        return []
    if str(pin.get("axis_exception", "")).strip():
        return []
    if "boundary_clause" in row["parameters"].get("condition_cases", {}):
        return []
    return ["boundary_clause"]


def test_worded_boundary_clauses_are_tied():
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    assert {
        row["rule_id"]: found
        for row in rows
        if (found := boundary_clause_problems(row))
    } == {}


# Review r3 M1: statutory conditions the review found outside `when`, each
# pinned to the passage that imposes it (capture, quoted text) and to the
# case facts, and phrases in their values, that must carry it.
REQUIRED_CONDITIONS = [
    *[
        (
            rule_id,
            "effective_1402e_exemption",
            {"clergy_or_religious_exemption": (), "ministerial_service": ()},
            "lii_42_411.html",
            "The provisions of paragraph (4) or (5) shall not apply to "
            "service",
        )
        for rule_id in (
            "clergy_1968_1972",
            "clergy_1973_1981",
            "clergy_1982_2026",
        )
    ],
    *[
        (
            rule_id,
            "nonresident_alien_ministry",
            {
                "ministerial_service": (),
                "nonresident_alien_status": ("nonresident alien",),
            },
            "lii_42_411.html",
            "(other than a nonresident alien individual, except as provided "
            "by an agreement under section 433 of this title",
        )
        for rule_id in (
            "clergy_1968_1972",
            "clergy_1973_1981",
            "clergy_1982_2026",
        )
    ],
    (
        "religious_order_1968_1983",
        "election_member_abroad_not_covered",
        {
            "place_of_work": ("outside the United States",),
            "citizenship": ("not a United States citizen",),
        },
        "poms_rs_01901620.html",
        "the member is a U.S. citizen, or effective January 1, 1984, a "
        "resident alien",
    ),
    (
        "religious_order_1984_2026",
        "election_member_abroad_not_covered",
        {
            "place_of_work": ("outside the United States",),
            "nonresident_alien_status": ("nor a resident alien",),
        },
        "poms_rs_01901620.html",
        "the member is a U.S. citizen, or effective January 1, 1984, a "
        "resident alien",
    ),
    *[
        (
            rule_id,
            "vow_duties_with_3121r_election",
            {"clergy_or_religious_exemption": ("living on the first day",)},
            "uscode_119_120_26_3121.html",
            "only if the member performing such services was a member at the "
            "time such services were performed and is living on the first day "
            "of the quarter in which such certificate is filed",
        )
        for rule_id in (
            "religious_order_1968_1983",
            "religious_order_1984_2026",
        )
    ],
    # Review r5 H-1: 3121(r)(2) defines a member "For purposes of this
    # subsection" only, so the active, unretired member limits the
    # election's covered case and its noncovered counterpart.
    *[
        (
            rule_id,
            case_id,
            {"religious_order_service": (phrase,)},
            "uscode_119_120_26_3121.html",
            "who performs tasks usually required (and to the extent usually "
            "required) of an active member of such order and who is not "
            "considered retired because of old age or total disability",
        )
        for rule_id in (
            "religious_order_1968_1983",
            "religious_order_1984_2026",
        )
        for case_id, phrase in (
            (
                "vow_duties_with_3121r_election",
                "is not considered retired because of old age or total "
                "disability",
            ),
            (
                "vowed_member_outside_3121r2_definition",
                "or is considered retired because of old age or total "
                "disability",
            ),
        )
    ],
    (
        "se_retired_partner_1968_2026",
        "qualifying_retirement_payment",
        {
            "retirement_payment": (
                "requirements as are prescribed by the Secretary",
                "a class or classes of partners",
                "until the partner's death",
            ),
            "partner_no_services": (),
            "partner_no_other_obligation": (),
            "partner_capital_paid": (),
        },
        "lii_42_411.html",
        "which meets such requirements as are prescribed by the Secretary of "
        "the Treasury or his delegate",
    ),
    (
        "se_conservation_reserve_2008_2026",
        "crp_payment_in_real_estate_dealer_business",
        {"real_estate_dealer_status": ("real estate dealer",)},
        "lii_42_411.html",
        "unless such rentals are received in the course of a trade or "
        "business as a real estate dealer",
    ),
    (
        "se_conservation_reserve_2008_2026",
        "crp_payment_under_farm_arrangement",
        {"rental_income": ("agricultural or horticultural commodities",)},
        "lii_42_411.html",
        "shall not apply to any income derived by the owner or tenant of "
        "land if",
    ),
    (
        "fishing_crew_share_service_1989",
        "catch_share_1996_clarification",
        {
            "historical_fica_treatment": ("did not treat",),
            "fishing_catch_share_arrangement": (
                "$100 per trip",
                "contingent on a minimum catch",
                "solely for additional duties",
                "preceding 4 calendar quarters",
                "is normally made up of fewer than 10 individuals",
                "each boat from which the individual receives a share",
            ),
        },
        "ce1c_plaw104_188.html",
        "which is contingent on a minimum catch",
    ),
    # Review r4 M-3: the crew test is "normally made up of fewer than 10",
    # the average only deems it, and before 1996 (A) barred only cash.
    (
        "fishing_crew_share_service_1989",
        "catch_share_payor_treated_as_fica",
        {
            "historical_fica_treatment": ("payor treated",),
            "fishing_catch_share_arrangement": (
                "is normally made up of fewer than 10 individuals",
                "each boat from which the individual receives a share",
                "no cash remuneration apart from that share",
            ),
        },
        "ce1c_usc2023_42_410.html",
        "such individual does not receive any cash remuneration (other than "
        "as provided in subparagraph (B)),",
    ),
    (
        "fishing_crew_share_service_1995",
        "qualifying_catch_share_arrangement",
        {
            "fishing_catch_share_arrangement": (
                "is normally made up of fewer than 10 individuals",
                "each boat from which the individual receives a share",
                "is treated as normally fewer than 10",
                "$100 per trip",
            ),
        },
        "ce1c_usc2023_42_410.html",
        "shall be treated as normally made up of fewer than 10 individuals if "
        "the average size of the operating crew",
    ),
    (
        "tribal_council_service_2018_0920",
        "section_418a_retroactive_inclusion",
        {
            "tribal_coverage_agreement": ("before the agreement's",),
            "historical_fica_treatment": ("timely paid in good faith",),
        },
        "ce1c_plaw115_243.html",
        "timely paid in good faith (and not subsequently refunded)",
    ),
    # Review r3 low 6: the narrow omissions, each pinned to its passage.
    (
        "se_limited_partner_1978_2026",
        "guaranteed_payment_not_for_services",
        {
            "partnership_status": (
                "707(c) guaranteed payment",
                "not for services actually rendered",
                "not established to be in the nature of remuneration",
            )
        },
        "lii_42_411.html",
        "other than guaranteed payments described in section 707(c) of the "
        "Internal Revenue Code of 1986 to that partner for services actually "
        "rendered",
    ),
    (
        "se_treaty_fishing_1968_2026",
        "section_7873c2_de_minimis_amount",
        {
            "tribal_fishing_rights_income": ("de minimis", "7873(a)(1)"),
            "tribal_fishing_qualified_entity": ("7873(b)(3)",),
        },
        "uscode_2024_26_7873.html",
        "If, but for this paragraph, all but a de minimis amount",
    ),
    *[
        (
            "foreign_vessel_aircraft_service_1968",
            case_id,
            {
                "place_of_work": (
                    "when it is outside the United States",
                    "service within the United States is included",
                )
            },
            "poms_rs_01901170.html",
            "including service done within the U.S. if some part of the "
            "employee's service is done outside the U.S.",
        )
        for case_id in (
            "foreign_craft_noncitizen",
            "foreign_craft_non_american_employer",
        )
    ],
    *[
        (
            rule_id,
            case_id,
            {"federal_retirement_system": ("section 2601(c)",)},
            "lii_42_410.html",
            "if he is contributing a reduced amount by reason of the Federal "
            "Employees’ Retirement Contribution Temporary Adjustment Act of "
            "1983",
        )
        for rule_id in ("federal_1984_1986", "federal_1987_2026")
        for case_id in (
            "defra_2601d_requalification",
            "legislative_not_retirement_covered_1983",
            "legislative_ceased_coverage_after_1983",
        )
    ],
    *[
        (
            "federal_1984_1986",
            case_id,
            {
                "federal_retirement_system": (
                    "section 2601(d)(3)",
                    "first month beginning after that 30-day period",
                )
            },
            "lii_42_410.html",
            "become effective with the first month beginning after such "
            "30-day period",
        )
        for case_id in (
            "legislative_lump_sum_after_1983",
            "legislative_ceased_coverage_after_1983",
        )
    ],
    # The POMS NOTE has no end date, so it reaches the 1995 row too (r3c).
    *[
        (
            rule_id,
            "agreement_with_lower_threshold_nonmember",
            {
                "section_218_position": ("below the statutory amount",),
                "public_retirement_system_participation": (
                    "not a member, when the service is performed",
                    "a statewide system included",
                ),
            },
            "poms_sl_30001357.html",
            "Beginning July 2, 1991, services optionally excluded from "
            "coverage under a Section 218 Agreement may be mandatorily "
            "covered unless the employee is a member of a public retirement "
            "system",
        )
        for rule_id in ("election_work_1991_0702", "election_work_1995")
    ],
    *[
        (
            rule_id,
            "agreement_with_lower_threshold_member",
            {
                "section_218_position": ("below the statutory amount",),
                "public_retirement_system_participation": (
                    "member, when the service is performed, of a qualified",
                    "a statewide system included",
                ),
            },
            "poms_sl_30001357.html",
            "In these States, the Social Security and Medicare tax applies "
            "when the amount specified in the State’s agreement is met.",
        )
        for rule_id in ("election_work_1991_0702", "election_work_1995")
    ],
    # Review r7 H-1: membership goes entity by entity, on the captured
    # regulation, in every membership case of the three rows.
    *[
        (
            rule_id,
            case_id,
            {
                "public_retirement_system_participation": (
                    "entity by entity, not position by position "
                    "(31.3121(b)(7)-2(c)(2))",
                    "employing the individual maintains, alone or with other "
                    "such entities (a statewide system included)",
                ),
            },
            "ce1r7_cfr2025_26_31_3121b7_2.xml",
            "whether an employee is a member of a retirement system is "
            "determined on an entity-by-entity rather than a "
            "position-by-position basis.",
        )
        for rule_id, case_id in (
            ("state_local_1991_2026", "mandatory_nonmember_coverage"),
            (
                "state_local_1991_2026",
                "qualified_system_member_without_agreement",
            ),
            *[
                (rule_id, case_id)
                for rule_id in (
                    "election_work_1991_0702",
                    "election_work_1995",
                )
                for case_id in (
                    "agreement_with_lower_threshold_nonmember",
                    "agreement_with_lower_threshold_member",
                    "outside_agreement_nonmember",
                    "outside_agreement_member",
                )
            ],
        )
    ],
    (
        "foreign_agricultural_service_1968",
        "temporary_agricultural_admission_agricultural_labor",
        {
            "nonresident_alien_status": (
                "on a temporary basis to perform agricultural labor",
            ),
            "agricultural_service": (
                "agricultural labor performed in connection with that "
                "admission",
            ),
        },
        "ce1c_irs_pub51_2023_extract.pdf.txt",
        "compensation paid to H-2A workers for agricultural labor",
    ),
    (
        "foreign_agricultural_service_1968",
        "temporary_agricultural_admission_other_service",
        {
            "nonresident_alien_status": (
                "on a temporary basis to perform agricultural labor",
            ),
            "agricultural_service": ("other than agricultural labor",),
        },
        "lii_42_410.html",
        "(1) Service performed by foreign agricultural workers lawfully "
        "admitted to the United States",
    ),
    # Review r3 sibling (r3c): former 410(a)(1)(A), struck in 1984.
    (
        "foreign_agricultural_service_1968",
        "title_v_contract_worker_before_1984_07_18",
        {
            "nonresident_alien_status": (
                "under a contract entered into in accordance with title V of "
                "the Agricultural Act of 1949",
            ),
            "services_performed_date": ("before 1984-07-18",),
        },
        "lii_42_410.html",
        "struck out “(A) under contracts entered into in accordance with "
        "title V of the Agricultural Act of 1949",
    ),
    *[
        (
            rule_id,
            "us_citizen_in_united_states",
            {
                "international_organization_service": (
                    "while the designation is in effect and its conditions "
                    "are met",
                )
            },
            "lii_42_411.html",
            "(C) service described in section 410(a) (11), (12), or (15) of "
            "this title performed in the United States by a citizen of the "
            "United States",
        )
        for rule_id in (
            "international_organization_service_1968",
            "international_organization_service_1995",
        )
    ],
    (
        "international_organization_service_1995",
        "transferred_federal_employee_410r",
        {"federal_service": ("immediately before the transfer",)},
        "lii_42_410.html",
        "immediately before such transfer, such individual performed service "
        "with a Federal agency",
    ),
    # No 410 note amends 410(j) after 1960, so the 1978 row too (r3c).
    *[
        (
            rule_id,
            "statutory_homeworker",
            {
                "occupation": (
                    "contract of service that contemplates",
                    "(other than in facilities for transportation)",
                    "continuing relationship",
                )
            },
            "lii_42_410.html",
            "if the contract of service contemplates that substantially all "
            "of such services are to be performed personally by such "
            "individual",
        )
        for rule_id in (
            "statutory_homeworker_service_1968",
            "statutory_homeworker_service_1978",
        )
    ],
    (
        "nonresident_alien_service_1968",
        "f1_j1_admission_purpose_service",
        {
            "nonresident_alien_status": ("nonresident alien",),
            "visa_status": ("F-1 or J-1 nonimmigrant",),
            "statutory_student_service": ("to carry out the purpose",),
        },
        "lii_42_410.html",
        "(19) Service which is performed by a nonresident alien individual "
        "for the period he is temporarily present in the United States as a "
        "nonimmigrant",
    ),
    *[
        (
            "student_service_1973",
            case_id,
            {
                "employer_school_nexus": (
                    "organized, and at all times thereafter is operated",
                    "operated, supervised or controlled by or in connection",
                )
            },
            "lii_42_410.html",
            "if the organization is organized, and at all times thereafter "
            "is operated, exclusively for the benefit of",
        )
        for case_id in (
            "enrolled_student_before_2024_08_15",
            "enrolled_student_from_2024_08_15",
        )
    ],
    # Review r3 sibling (r3c): POMS RS 01901.720 C.2-C.3, effective
    # 08/15/2024, apply to service from that date and not before.
    (
        "student_service_1973",
        "enrolled_student_before_2024_08_15",
        {"services_performed_date": ("before 2024-08-15",)},
        "poms_rs_01901720.html",
        "Effective Dates: 08/15/2024 - Present",
    ),
    (
        "student_service_1973",
        "enrolled_student_from_2024_08_15",
        {
            "services_performed_date": ("on or after 2024-08-15",),
            "statutory_student_service": (
                "main purpose is pursuing a course of study",
                "half-time academic workload",
                "retirement plan or annuity",
                "reduced tuition",
                "career employee",
                "postdoctoral student, postdoctoral fellow",
                "medical resident or medical intern",
            ),
            "enrollment": (
                "regular academic year and summer session",
                "between semesters",
                "more than five weeks",
            ),
        },
        "poms_rs_01901720.html",
        "Also, the student must carry at least a half-time academic "
        "workload.",
    ),
    # Review r3 sibling (r3c): section 8015(c)(3) as the 2024 Code's note
    # under 26 U.S.C. 3121 sets out its enacted text.
    (
        "federal_1987_2026",
        "after_official_service_from_1988_11_10",
        {"federal_service": ("performed on or after 1988-11-10",)},
        "ce1c_usc2024_26_3121.html",
        "shall apply to any individual only upon the performance by such "
        "individual of service described in subparagraph (C), (D), (E), "
        "(F), (G), or (H) of section 210(a)(5) of the Social Security Act",
    ),
]
REQUIRED_CONDITION_ROWS_ALL = json.loads(REGISTRY_ARTIFACT.read_text())[
    "rules"
]
REQUIRED_CONDITION_ROWS = {
    row["rule_id"]: row
    for row in json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    if row["rule_id"] in {entry[0] for entry in REQUIRED_CONDITIONS}
}


def required_condition_id(entry):
    """A unique test id: row, case, capture and the first required phrase
    (review r4 low 2; pytest suffixed three duplicate pairs)."""
    rule_id, case_id, facts, capture, _ = entry
    phrases = [phrase for fact in sorted(facts) for phrase in facts[fact]]
    first = phrases[0] if phrases else sorted(facts)[0]
    return f"{rule_id}-{case_id}-{capture}-{first}"


def required_condition_problems(case, captures, facts, capture):
    """Required facts or phrases a case's `when` lacks, and an uncited
    capture. ``facts`` maps each fact to phrases its value must contain."""
    problems = []
    for fact, phrases in facts.items():
        if fact not in case["when"]:
            problems.append((fact, "missing"))
            continue
        problems.extend(
            (fact, phrase)
            for phrase in phrases
            if phrase not in str(case["when"][fact])
        )
    if capture not in captures:
        problems.append((capture, "uncited"))
    return problems


@pytest.mark.parametrize(
    ("rule_id", "case_id", "facts", "capture", "passage"),
    REQUIRED_CONDITIONS,
    ids=[required_condition_id(entry) for entry in REQUIRED_CONDITIONS],
)
def test_statutory_conditions_sit_in_their_cases(
    registry, rule_id, case_id, facts, capture, passage
):
    """Review r3 M1 and low 6: each listed condition is a `when` fact of
    its case, and the row cites the capture whose passage imposes it."""
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    case = next(c for c in rule.cases if c["case_id"] == case_id)
    captures = {c.capture for c in rule.citations}
    assert required_condition_problems(case, captures, facts, capture) == []
    text = source_text(CAPTURE_DIRECTORY / capture)
    assert " ".join(passage.split()) in text


@settings(deadline=None)
@given(
    st.sampled_from(REQUIRED_CONDITIONS),
    st.sampled_from(["fact", "phrase", "capture"]),
    st.data(),
)
def test_required_condition_checker_flags_a_dropped_condition(
    entry, dropped, data
):
    """The M1 and low 6 checker is the test's oracle: removing any listed
    fact, phrase or citation from a real case is flagged."""
    rule_id, case_id, facts, capture, _ = entry
    row = REQUIRED_CONDITION_ROWS[rule_id]
    case = next(c for c in row["cases"] if c["case_id"] == case_id)
    captures = {c["capture"] for c in row["citations"]}
    assert required_condition_problems(case, captures, facts, capture) == []
    when = dict(case["when"])
    phrased = sorted(fact for fact, phrases in facts.items() if phrases)
    if dropped == "phrase" and phrased:
        fact = data.draw(st.sampled_from(phrased))
        phrase = data.draw(st.sampled_from(facts[fact]))
        when[fact] = str(when[fact]).replace(phrase, "INVENTED")
    elif dropped == "capture":
        captures = captures - {capture}
    else:
        del when[data.draw(st.sampled_from(sorted(facts)))]
    mutated = {**case, "when": when}
    assert required_condition_problems(mutated, captures, facts, capture)


# Review r3 low 6: what each narrowed row returns for INVENTED fact
# patterns, by the cases whose conditions they meet.
LOW6_OUTCOMES = [
    # A limited partner's 707(c) payment for the use of capital.
    (
        "self_employment_limited_partner",
        2000,
        {"guaranteed_payment_not_for_services"},
        "noncovered",
    ),
    (
        "self_employment_limited_partner",
        2000,
        {"guaranteed_payment_for_services"},
        "covered",
    ),
    # The de minimis unrelated part of an entity-derived fishing amount.
    (
        "self_employment_treaty_fishing",
        2000,
        {"section_7873c2_de_minimis_amount"},
        "noncovered",
    ),
    # A noncitizen crewman's in-port service on a foreign vessel he also
    # serves on at sea.
    (
        "foreign_vessel_aircraft_service",
        2000,
        {"foreign_craft_noncitizen"},
        "noncovered",
    ),
    # Nonmember and member election workers under a lower agreement amount.
    (
        "election_work",
        1992,
        {"agreement_with_lower_threshold_nonmember"},
        "covered_above_threshold",
    ),
    (
        "election_work",
        1992,
        {"agreement_with_lower_threshold_member"},
        "covered_above_threshold",
    ),
    # An H-2A worker's farm work, and the same worker's other service.
    (
        "foreign_agricultural_service",
        2000,
        {"temporary_agricultural_admission_agricultural_labor"},
        "noncovered",
    ),
    (
        "foreign_agricultural_service",
        2000,
        {"temporary_agricultural_admission_other_service"},
        "refuses",
    ),
    ("foreign_agricultural_service", 2000, set(), "covered"),
    # A transferred Federal employee, and a citizen in the United States.
    (
        "international_organization_service",
        2000,
        {
            "transferred_federal_employee_410r",
            "us_citizen_in_united_states",
            "designated_international_organization",
        },
        "covered",
    ),
    # F-1 admission-purpose work keyed on the visa class.
    (
        "nonresident_alien_service",
        2000,
        {"f1_j1_admission_purpose_service"},
        "noncovered",
    ),
]


@pytest.mark.parametrize(
    ("family", "year", "matched", "expected"),
    LOW6_OUTCOMES,
    ids=[
        f"{family}-{sorted(matched)}"
        for family, _, matched, _ in LOW6_OUTCOMES
    ],
)
def test_narrowed_rows_resolve_as_their_sources_say(
    registry, family, year, matched, expected
):
    (rule,) = registry.lookup(family, year)
    if expected == "refuses":
        with pytest.raises(OpenRuleError, match="FOREIGN_AGRICULTURAL"):
            rule.resolve(matched)
    else:
        assert rule.resolve(matched)["consequence"] == expected


@pytest.mark.parametrize("year", [1992, 2000])
def test_election_nonmember_meets_either_threshold(registry, year):
    """Review r3 low 6: from 1991-07-02 an optionally excluded nonmember is
    mandatorily covered unless 410(a)(7)(F)(iv) excepts the pay, so both the
    agreement's amount and the statutory annual amount bear on it. The POMS
    NOTE states no end date, so the 1995 row splits the case too (r3c)."""
    (rule,) = registry.lookup("election_work", year)
    cases = {case["case_id"]: case for case in rule.cases}
    nonmember = cases["agreement_with_lower_threshold_nonmember"]
    assert "the agreement's amount" in nonmember["description"]
    assert "statutory annual amount" in nonmember["description"]
    member = cases["agreement_with_lower_threshold_member"]
    assert "statutory annual" not in member["description"]
    assert "agreement_with_lower_threshold" not in cases


def test_foreign_agricultural_readings_name_both_sources(registry):
    """Review r3 low 6: the agricultural-labor condition rests on Pub 51
    (2023) section 3, which the row now cites; the statute and POMS key on
    the worker's admission, so the worker's other service refuses."""
    (rule,) = registry.lookup("foreign_agricultural_service", 2000)
    other = next(c for c in rule.cases if "open_reason" in c)
    names = {option["name"] for option in other["open_alternatives"]}
    assert names == {"worker_admission_reading", "agricultural_labor_reading"}
    quotes = " ".join(c.quote or "" for c in rule.citations)
    assert "for agricultural labor" in quotes
    assert "Service performed by foreign agricultural workers" in quotes
    assert "ce1c_irs_pub51_2023_extract.pdf" in {
        c.capture for c in rule.citations
    }


@pytest.mark.parametrize("rule_id", ["federal_1984_1986", "federal_1987_2026"])
def test_federal_rows_carry_section_2601_c_d3_and_e(registry, rule_id):
    """Review r3 low 6: 2601(c) narrows "subject to", 2601(d)(3) delays
    (G) coverage for late requalifiers, and 2601(e) makes a 501(c)(3)
    employee under subchapter III a Federal instrumentality employee."""
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    nonprofit = rule.parameters["section_2601e_nonprofit_service"]
    cited = nonprofit["citation"]
    assert cited["capture"] in {c.capture for c in rule.citations}
    assert "501(c)(3)" in cited["quote"]
    assert "instrumentality of the United States" in cited["quote"]
    assert " ".join(cited["quote"].split()) in source_text(
        CAPTURE_DIRECTORY / cited["capture"]
    )
    # Review r6 code quality: 2601(c) leaves an individual contributing a
    # reduced amount outside subchapter III, in the requalification text.
    cases = {case["case_id"]: case for case in rule.cases}
    requalified = cases["defra_2601d_requalification"]["when"]
    assert "Pub. L. 98-369 section 2601(c)" in (
        requalified["federal_retirement_system"]
    )
    delay = rule.parameters.get("section_2601d3_delay")
    assert (delay is None) == (rule_id == "federal_1984_1986")
    # Review r5 H-7: both rows' (G)(ii) and (G)(iii) cases carry the
    # 2601(d)(3) delay, which has no outer date under (d)(2).
    cases = {case["case_id"]: case for case in rule.cases}
    for case_id in (
        "legislative_lump_sum_after_1983",
        "legislative_ceased_coverage_after_1983",
    ):
        text = cases[case_id]["when"]["federal_retirement_system"]
        assert text.endswith(SECTION_2601D3_CLAUSE), case_id
    if delay is not None:
        ties = rule.parameters["condition_cases"]["section_2601d3_delay"]
        assert set(ties["cases"]) == {
            "legislative_lump_sum_after_1983",
            "legislative_ceased_coverage_after_1983",
            "after_official_during_2601d3_delay",
        }


SECTION_2601D3_CLAUSE = (
    "; where the individual meets Pub. L. 98-369 section 2601(d)(1)(A) and "
    "(B) and did not again become subject to subchapter III (or "
    "effectively apply for it) before July 18, 1984 or within the 30-day "
    "period of section 2601(d)(1) or (2), the service is performed in or "
    "after the first month beginning after that 30-day period (section "
    "2601(d)(3))"
)


SECTION_8015C3_ENACTED = (
    "shall apply to any individual only upon the performance by such "
    "individual of service described in subparagraph (C), (D), (E), (F), "
    "(G), or (H) of section 210(a)(5) of the Social Security Act"
)


@pytest.mark.parametrize("rule_id", ["federal_1984_1986", "federal_1987_2026"])
def test_federal_rows_quote_section_8015c3_as_enacted(registry, rule_id):
    """Review r3 sibling (r3c): both rows cited section 8015(c)(3) only
    through LII's paraphrase. The 2024 Code's note under 26 U.S.C. 3121
    sets out the enacted text, so the rows quote it and keep the LII note.
    """
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    enacted = [
        c
        for c in rule.citations
        if c.capture == "ce1c_usc2024_26_3121.html"
        and c.quote
        and SECTION_8015C3_ENACTED in c.quote
    ]
    assert len(enacted) == 1
    assert "8015(c)(3)" in enacted[0].location
    assert "[Nov. 10, 1988]" in enacted[0].quote
    assert any(
        c.capture == "lii_42_410.html" and "8015(c)(3)" in c.location
        for c in rule.citations
    )
    descriptions = " ".join(c.get("description", "") for c in rule.cases)
    assert ("only upon the performance by such" in descriptions) == (
        rule_id == "federal_1987_2026"
    )


def test_tribal_posting_rule_is_a_crediting_rule_not_a_case(registry):
    """Review r3 low 6: POMS RS 01901.700 C.1 says council-member services
    "do not constitute employment", and its NOTE uses earnings posted
    through 2005 in benefit computations. No case reads the posting fact,
    so the 1968 row lists it only in the crediting rule that reads it."""
    rule = next(
        r for r in registry.rules if r.rule_id == "tribal_council_service_1968"
    )
    posting = rule.parameters["benefit_credit_posting_rule"]
    assert posting["posting_fact"] == "historical_earnings_posting"
    assert "historical_earnings_posting" not in rule.trigger_facts
    tie = rule.parameters["condition_cases"]["benefit_credit_posting_rule"]
    assert "historical_earnings_posting" in tie["not_a_coverage_condition"]
    read = {fact for case in rule.cases for fact in case["when"]}
    assert "historical_earnings_posting" not in read
    member = {"federally_recognized_council_member"}
    assert rule.resolve(member)["consequence"] == "noncovered"
    assert any(
        c.quote and "We use earnings posted" in c.quote for c in rule.citations
    )


def test_tribal_posting_rule_reaches_no_year_of_the_2018_row(registry):
    """Review r3 sibling (r3c): the NOTE reaches tax years through 2005,
    and the 2018 row begins 2018-09-20, so it lists no posting fact."""
    rule = next(
        r
        for r in registry.rules
        if r.rule_id == "tribal_council_service_2018_0920"
    )
    assert "historical_earnings_posting" not in rule.trigger_facts
    read = {fact for case in rule.cases for fact in case["when"]}
    assert "historical_earnings_posting" not in read
    posting = rule.parameters["benefit_credit_posting_rule"]
    assert posting["through_tax_year"] < rule.effective_start.year
    tie = rule.parameters["condition_cases"]["benefit_credit_posting_rule"]
    assert "2018-09-20" in tie["not_a_coverage_condition"]
    assert any(
        c.quote and "for tax years 2005 and earlier" in c.quote
        for c in rule.citations
    )


def test_homeworker_cash_test_cites_its_1968_1977_location(registry):
    """Review r3 low 6: before Pub. L. 101-239 redesignated it in 1989, the
    home-worker cash test was 409(j), not 409(a)(8)."""
    rule = next(
        r
        for r in registry.rules
        if r.rule_id == "statutory_homeworker_service_1968"
    )
    locators = [c.location for c in rule.citations] + [
        case.get("description", "") for case in rule.cases
    ]
    for text in locators:
        if "409(a)(8)" in text:
            assert "409(j)" in text, text
    quotes = " ".join(c.quote or "" for c in rule.citations)
    assert "Former subsec. (j) redesignated subsec. (a)(8)." in quotes
    # The subsec. (a) note: section 10208(d)(1)(A)-(K) moved it.
    assert "former subsecs. (j) and (k) as pars. (8) and (9)" in quotes
    (cash_test,) = [
        c for c in rule.cases if c["case_id"] == "statutory_homeworker"
    ]
    assert "10208(d)(1)(A)-(K)" in cash_test["description"]
    assert "“$100” for “$50”" in quotes


def test_homeworker_1978_cash_test_sat_in_409j_until_1989(registry):
    """Review r3 sibling (r3c): from 1978 the $100 calendar-year test sat
    in former 409(j) until the 1989 redesignation, then in 409(a)(8)."""
    rule = next(
        r
        for r in registry.rules
        if r.rule_id == "statutory_homeworker_service_1978"
    )
    texts = [c.location for c in rule.citations] + [
        case.get("description", "") for case in rule.cases
    ]
    for text in texts:
        if "409(a)(8)" in text:
            assert "409(j)" in text, text
    (cash_test,) = [
        c for c in rule.cases if c["case_id"] == "statutory_homeworker"
    ]
    assert "former 409(j) until" in cash_test["description"]
    assert "10208(d)(1)(A)-(K)" in cash_test["description"]
    quotes = " ".join(c.quote or "" for c in rule.citations)
    for quote in (
        "Former subsec. (j) redesignated subsec. (a)(8).",
        "former subsecs. (j) and (k) as pars. (8) and (9)",
        "“$100” for “$50”",
        "remuneration paid and services rendered after December 31, 1977",
        "is less than $100;",
    ):
        assert quote in quotes, quote
    assert rule.effective_start == date(1978, 1, 1)


def test_section_410a19_rows_key_the_visa_class_alike(registry):
    """Review r3 low 6: every 410(a)(19) case names the alien status and the
    visa class in separate facts, as the M-1 and Q rows do."""
    families = {
        "nonresident_alien_service",
        "nonresident_alien_vocational_service",
        "nonresident_alien_cultural_exchange_service",
    }
    found = [
        case
        for rule in registry.rules
        if rule.family in families
        for case in rule.cases
        if "nonresident_alien_status" in case["when"]
    ]
    assert len(found) >= 4
    for case in found:
        assert case["when"]["nonresident_alien_status"] == "nonresident alien"
        assert "nonimmigrant" in case["when"]["visa_status"]


# Review r3 sibling rows (r3c): rows that share a low-6 row's defect, and
# helper-batch lows on low-6 rows. What each returns for INVENTED fact
# patterns, by the cases whose conditions they meet.
SIBLING_OUTCOMES = [
    # Nonmember and member election workers under a lower agreement amount.
    (
        "election_work",
        2000,
        {"agreement_with_lower_threshold_nonmember"},
        "covered_above_threshold",
    ),
    (
        "election_work",
        2000,
        {"agreement_with_lower_threshold_member"},
        "covered_above_threshold",
    ),
    # A title V contract worker, also admitted under clause (B), whose
    # 1980 service is not agricultural labor: clause (A) decides.
    (
        "foreign_agricultural_service",
        1980,
        {
            "title_v_contract_worker_before_1984_07_18",
            "temporary_agricultural_admission_other_service",
        },
        "noncovered",
    ),
    # A covering section 218 agreement displaces the 2024 criteria case.
    (
        "student_service",
        2025,
        {
            "section_218_agreement_covers_students",
            "enrolled_student_from_2024_08_15",
        },
        "covered",
    ),
    (
        "student_service",
        2025,
        {"enrolled_student_from_2024_08_15"},
        "noncovered",
    ),
]


@pytest.mark.parametrize(
    ("family", "year", "matched", "expected"),
    SIBLING_OUTCOMES,
    ids=[
        f"{family}-{year}-{sorted(matched)}"
        for family, year, matched, _ in SIBLING_OUTCOMES
    ],
)
def test_sibling_rows_resolve_as_their_sources_say(
    registry, family, year, matched, expected
):
    (rule,) = registry.lookup(family, year)
    assert rule.resolve(matched)["consequence"] == expected


@pytest.mark.parametrize(
    "rule_id", ["clergy_1968_1972", "clergy_1973_1981", "clergy_1982_2026"]
)
def test_clergy_exemption_reaches_only_ministry(registry, rule_id):
    """Review r3 M1: an exempt minister's secular earnings are not excluded
    by the clergy family, and a nonresident alien's ministry is."""
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    exempt_ministry = {"effective_1402e_exemption"}
    assert rule.resolve(exempt_ministry)["consequence"] == "noncovered"
    secular = {"non_ministerial_service"}
    assert rule.resolve(secular)["consequence"] == "covered"
    nonresident = {
        "nonresident_alien_ministry",
        "ministry_without_exemption_or_vow",
    }
    assert rule.resolve(nonresident)["consequence"] == "noncovered"
    citizen_abroad = {"ministry_without_exemption_or_vow"}
    assert rule.resolve(citizen_abroad)["consequence"] == "covered"


BOILERPLATE_RESIDUAL = "This family returns its stated consequence"


def test_case_free_residuals_say_what_applies():
    """Review r3 low 9: 27 case-free rows at ea599b92 kept a residual that
    referred to conditional cases they do not have."""
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    stale = [
        row["rule_id"]
        for row in rows
        if row["residual_default"]["description"].startswith(
            BOILERPLATE_RESIDUAL
        )
        or (
            not row["cases"]
            and "conditional case" in row["residual_default"]["description"]
        )
    ]
    assert stale == []


def test_consequences_live_in_cases_not_parameters():
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    stored = [
        (row["rule_id"], ".".join(path))
        for row in rows
        for path, value in parameter_leaves(row["parameters"])
        if value in CONSEQUENCE_VALUES
    ]
    assert stored == []


def deferral_refusals(registry):
    """Deferring outcomes whose target refuses or has no rule, by year.

    Returns (refused, absent): refused maps (rule, case, target) to the
    years whose lookup raises OpenRuleError; absent lists years with no
    rule at all.
    """
    refused, absent = {}, []
    for rule in registry.rules:
        for outcome in (rule.residual_default, *rule.cases):
            if outcome["consequence"] != "deferred":
                continue
            case_id = outcome.get("case_id", "residual_default")
            for target in outcome["defers_to"]:
                for year in range(
                    rule.effective_start.year, rule.effective_end.year + 1
                ):
                    try:
                        assert registry.lookup(target, year)
                    except OpenRuleError:
                        key = (rule.rule_id, case_id, target)
                        refused.setdefault(key, []).append(year)
                    except NoRuleError:
                        absent.append((rule.rule_id, target, year))
    return refused, absent


def test_real_deferral_targets_cover_the_deferring_years(registry):
    """Every deferral reaches a family with a rule in each deferring year.

    Review r3 low 2: an open target is no longer excused. Where the target
    refuses, the deferring row records it in parameters.deferral_exceptions
    (target, years and reason), and the deferral refuses rather than
    misclassify. At ea599b92 three deferrals refused unrecorded.
    """
    refused, absent = deferral_refusals(registry)
    assert absent == []
    recorded = {}
    for rule in registry.rules:
        exceptions = rule.parameters.get("deferral_exceptions", {})
        for case_id, entries in exceptions.items():
            assert case_id in {c["case_id"] for c in rule.cases}
            for entry in entries:
                assert str(entry["reason"]).strip()
                first, last = entry["years"]
                recorded[(rule.rule_id, case_id, entry["target"])] = list(
                    range(first, last + 1)
                )
    assert refused == recorded
    assert len(recorded) == 3


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
    # A bona fide commodity transfer, or lodging and meals in kind, stays
    # outside wages (409(a)(7)(A); review r4 sweep).
    genuine = {
        c["case_id"]
        for c in rule.cases
        if "any medium other than cash"
        in c["when"].get("cash_remuneration", "")
    }
    assert len(genuine) == 1
    assert rule.resolve(genuine)["consequence"] == "noncovered"


TITLE_V_CLAUSE_STRUCK = date(1984, 7, 18)


@example(date(1980, 6, 15), False)
@example(TITLE_V_CLAUSE_STRUCK - timedelta(days=1), True)
@example(TITLE_V_CLAUSE_STRUCK, True)
@example(TITLE_V_CLAUSE_STRUCK, False)
@given(st.dates(date(1968, 1, 1), date(2026, 12, 31)), st.booleans())
@settings(deadline=None)
def test_title_v_contract_clause_applies_before_july_18_1984(
    registry, service_day, also_admitted
):
    """INVENTED worker under a title V contract, whose service is not
    agricultural labor, and who may also hold a clause (B) admission.

    Review r3 sibling (r3c): Pub. L. 98-369 section 2663(a)(7)(A) struck
    former 410(a)(1)(A) effective July 18, 1984 (section 2664(b)). Before
    that date the clause excludes the service; from it, the residual or
    the clause (B) open case decides.
    """
    (rule,) = registry.lookup("foreign_agricultural_service", service_day.year)
    matched = {
        c["case_id"]
        for c in rule.cases
        if "title V" in c["when"].get("nonresident_alien_status", "")
        and service_date_condition_holds(
            c["when"]["services_performed_date"], service_day
        )
    }
    assert len(matched) == (service_day < TITLE_V_CLAUSE_STRUCK)
    if also_admitted:
        matched.add("temporary_agricultural_admission_other_service")
    if service_day < TITLE_V_CLAUSE_STRUCK:
        assert rule.resolve(matched)["consequence"] == "noncovered"
    elif also_admitted:
        with pytest.raises(OpenRuleError, match="FOREIGN_AGRICULTURAL"):
            rule.resolve(matched)
    else:
        assert rule.resolve(matched) is rule.residual_default
        assert rule.resolve(matched)["consequence"] == "covered"
    quotes = " ".join(c.quote or "" for c in rule.citations)
    assert "effective July 18, 1984" in quotes
    assert "title V of the Agricultural Act of 1949" in quotes
    # The clause stood from the row's start: the 410 notes amend (a)(1)
    # in 1951, 1954, 1956, 1958 and 1984 only.
    assert "added subpar. (C)" in quotes
    clause = rule.parameters["title_v_contract_clause"]
    assert "1951, 1954, 1956, 1958 and 1984 only" in clause


POMS_STUDENT_EDITION = date(2024, 8, 15)
# INVENTED workers, each an enrolled, regularly attending student of the
# employing school, by the POMS RS 01901.720 C.2-C.3 phrase each fails.
STUDENT_WORKERS = {
    "meets_every_criterion": None,
    "career_employee": "career employee",
    "eligible_for_reduced_tuition": "reduced tuition",
    "medical_resident": "medical resident",
    "under_half_time": "half-time academic workload",
    "six_week_break_not_attending": "more than five weeks",
}


def student_cases_met(rule, service_day, fails):
    """Student cases whose date holds and whose `when` the worker meets: a
    worker failing a criterion misses every case whose text names it."""
    return {
        c["case_id"]
        for c in rule.cases
        if "services_performed_date" in c["when"]
        and service_date_condition_holds(
            c["when"]["services_performed_date"], service_day
        )
        and not (
            fails and any(fails in str(value) for value in c["when"].values())
        )
    }


@example(date(2023, 6, 15), "career_employee")
@example(POMS_STUDENT_EDITION - timedelta(days=1), "medical_resident")
@example(POMS_STUDENT_EDITION, "medical_resident")
@example(POMS_STUDENT_EDITION, "meets_every_criterion")
@given(
    st.dates(date(2020, 1, 1), date(2026, 12, 31)),
    st.sampled_from(sorted(STUDENT_WORKERS)),
)
@settings(deadline=None)
def test_poms_2024_student_criteria_decide_from_august_15_2024(
    registry, service_day, worker
):
    """Review r3 sibling (r3c): the captured POMS RS 01901.720 is TN 62
    (08-24), effective 08/15/2024, and no capture holds an earlier edition.
    Its criteria decide service from that date; before it, the statutory
    test alone does, as the row has said since round 2."""
    (rule,) = registry.lookup("student_service", service_day.year)
    fails = STUDENT_WORKERS[worker]
    matched = student_cases_met(rule, service_day, fails)
    assert len(matched) <= 1
    excluded = service_day < POMS_STUDENT_EDITION or fails is None
    expected = "noncovered" if excluded else "covered"
    assert rule.resolve(matched)["consequence"] == expected
    criteria = rule.parameters["current_poms_student_criteria"]
    assert criteria["service_from"] == POMS_STUDENT_EDITION.isoformat()
    assert criteria["date_axis"]["operative"] == "services_performed_date"
    assert criteria["citation"]["quote"] == (
        "Effective Dates: 08/15/2024 - Present"
    )


def test_small_boat_fishing_date_comes_from_section_1207f4(registry):
    """Review r3 low 4: no 1976 effective-date note is captured; section
    1207(f)(4)(A) applies the 411 amendment to taxable years ending after
    December 31, 1954."""
    (rule,) = registry.lookup("self_employment_employee_definition", 2000)
    case = next(c for c in rule.cases if c["case_id"] == "small_boat_fishing")
    assert "1976" not in case["when"]["fishing_catch_share_arrangement"]
    assert "1954" in case["description"]
    assert any(
        c.capture == "lii_26_3121.html"
        and c.quote
        == ("shall apply to taxable years ending after December 31, 1954")
        for c in rule.citations
    )


def test_tribal_council_cases_and_uncaptured_crp_history(registry):
    tribal = registry.lookup("tribal_council_service", 2019)[0]
    council = {"no_section_418a_inclusion"}
    assert tribal.resolve(council)["consequence"] == "noncovered"
    agreement = council | {"section_418a_agreement_inclusion"}
    assert tribal.resolve(agreement)["consequence"] == "covered"
    # Council staff and tribal employees are not council-member service.
    assert tribal.resolve(set())["consequence"] == "covered"
    (crp,) = registry.lookup("self_employment_conservation_reserve", 2007)
    with pytest.raises(OpenRuleError, match="CRP_CLASSIFICATION"):
        crp.resolve({"crp_payment_classification_open"})


CRP = "self_employment_conservation_reserve"


@pytest.mark.parametrize("year", [1990, 2007, 2008, 2010])
def test_conservation_reserve_payments_follow_one_rule(registry, year):
    """Review r3 M4: one classification question in both windows.

    Before 2008 every Conservation Reserve payment, and from 2008 a
    payment to a recipient not receiving 402 or 423 benefits, refuses on
    the same question with the same readings, unless both readings agree
    (a real estate dealer's rent); a beneficiary's payment is excluded from
    2008.
    """
    rows = [r for r in registry.rules if r.family == CRP]
    questions = {
        (
            case["open_reason"],
            tuple(o["name"] for o in case["open_alternatives"]),
        )
        for rule in rows
        for case in rule.cases
        if "open_reason" in case
    }
    assert len(questions) == 1
    assert all(rule.open_reason is None for rule in rows)
    (rule,) = registry.lookup(CRP, year)
    with pytest.raises(OpenRuleError, match="CRP_CLASSIFICATION"):
        rule.resolve({"crp_payment_classification_open"})
    dealer = {
        "crp_payment_in_real_estate_dealer_business",
        "crp_payment_classification_open",
    }
    assert rule.resolve(dealer)["consequence"] == "covered"
    assert rule.resolve(())["consequence"] == "covered"
    ids = {case["case_id"] for case in rule.cases}
    assert ("crp_payment_to_beneficiary" in ids) == (year >= 2008)
    if year >= 2008:
        beneficiary = {"crp_payment_to_beneficiary"}
        assert rule.resolve(beneficiary)["consequence"] == "noncovered"


@pytest.mark.parametrize(
    ("family", "year", "matched", "expected"),
    [
        # HIGH-1 repros: each condition's failure no longer excludes.
        ("self_employment_conservation_reserve", 2010, set(), "covered"),
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
                "enrolled_student_before_2024_08_15",
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


def cases_met(rule, facts):
    """Cases whose every `when` condition an INVENTED worker's facts meet.

    ``facts`` maps each trigger fact to the condition texts a fixture states
    are true of the worker: one text, a tuple or list of texts, or a
    boolean. A condition holds only when one of them equals its text
    exactly (a boolean equals only the same boolean); a condition on a fact
    the pattern leaves out fails. So the worker's facts are a statement
    separate from the row's `when`: a case narrowed, broadened or reworded
    no longer equals what the worker states, and "a United States citizen"
    never meets "not a United States citizen" (review r5 M-2; review r4
    M-5 used substring matching, which saw neither).
    """

    def holds(fact, condition):
        stated = facts.get(fact, ())
        if isinstance(stated, (str, bool)):
            stated = (stated,)
        return any(
            (
                phrase is condition
                if isinstance(phrase, bool) or isinstance(condition, bool)
                else phrase == condition
            )
            for phrase in stated
        )

    return {
        case["case_id"]
        for case in rule.cases
        if all(holds(fact, text) for fact, text in case["when"].items())
    }


def resolved_consequence(rule, facts):
    """The consequence for a fact pattern, or "refuses" for an open case."""
    try:
        return rule.resolve(cases_met(rule, facts))["consequence"]
    except OpenRuleError:
        return "refuses"


# An INVENTED nonprofit worker's facts (review r4 H-A, M-2; r5 H-2 to H-4),
# as the texts of the conditions the worker meets.
NONPROFIT_501C3 = (
    "employer is an organization described in 501(c)(3) and exempt under "
    "501(a), whose service former 410(a)(8)(B) excluded"
)
NONPROFIT_IN_EFFECT = (
    "actual waiver certificate (Form SS-15) in effect for the service: the "
    "service falls on or after the certificate's effective date (RS "
    "01901.540 C.3) and before any termination took effect (C.5), and the "
    "certificate covers the employee's group where the organization divided "
    "its employees under 3121(k)(1)(E)"
)
NONPROFIT_DEEMED = (
    "certificate deemed filed under the 1976 amendments' constructive-filing "
    "provisions (no refund before 9/9/76), in effect for the service: the "
    "service falls on or after the first day of the first quarter for which "
    "the taxes were paid (RS 01901.540 C.2); taxes paid while the employer "
    "was waiting for an IRS ruling on its 501(c)(3) status do not count "
    "toward the constructive filing (RS 01901.540 D.8)"
)
NONPROFIT_NOT_IN_EFFECT = (
    "no actual or deemed certificate in effect for this service: none filed "
    "or deemed filed; the service falls before the certificate's effective "
    "date (for a deemed certificate, before the first day of the first "
    "quarter for which the taxes were paid); a termination took effect "
    "before the service; or the only certificate covers another "
    "3121(k)(1)(E) group"
)
# Review r7 M-9: the window is each quarter, after the organization
# stopped paying, for which it paid no taxes (POMS RS 01901.540 D.8
# forgives "the tax liability ... through 6/30/77").
NONPROFIT_K4C_GAP = (
    "certificate deemed filed under 3121(k)(4) (the 1976 amendments' "
    "constructive filing), where the organization stopped paying the taxes "
    "before October 19, 1976, and the service falls before July 1, 1977, "
    "on or after the first day of the deemed certificate's applicable "
    "period, in a calendar quarter, after the organization stopped paying "
    "the taxes, for which it paid no taxes"
)
NONPROFIT_312C_REQUEST = (
    "the employee filed a request under Pub. L. 95-216 section 312(c) on or "
    "before April 15, 1980, with full payment of the employee taxes (or an "
    "installment arrangement under 3121(k)(8))"
)
NONPROFIT_COVERED_EMPLOYEE = (
    "listed on the Form SS-15a filed with the certificate; listed on a "
    "supplemental list filed before the end of the twenty-fourth month "
    "following the calendar quarter in which the certificate was filed, for "
    "service on or after the first day of the calendar quarter in which that "
    "list was filed; hired after the certificate was filed; or, after the "
    "calendar quarter in which the certificate was filed for a 3121(k)(1)(E) "
    "group, became a member of that group"
)
NONPROFIT_NOT_LISTED = (
    "not listed for the service: not on the Form SS-15a filed with the "
    "certificate, and not on a supplemental list filed in or before the "
    "service's calendar quarter"
)
NONPROFIT_RETRO_HIRE = (
    "hired after the certificate's effective date and on or before its filing "
    "date (a certificate effective before it was filed, RS 01901.540 C.3.b), "
    "and not listed for the service: not on the Form SS-15a filed with the "
    "certificate, and not on a supplemental list filed in or before the "
    "service's calendar quarter and before the end of the twenty-fourth month "
    "following the calendar quarter in which the certificate was filed"
)
NONPROFIT_EXISTING_UNLISTED = (
    "hired on or before both the certificate's filing date and its effective "
    "date; had become a member of the employees or 3121(k)(1)(E) group the "
    "certificate covers by the end of the calendar quarter in which the "
    "certificate was filed; and not listed for the service: not on the Form "
    "SS-15a filed with the certificate, and not on a supplemental list filed "
    "in or before the service's calendar quarter and before the end of the "
    "twenty-fourth month following the calendar quarter in which the "
    "certificate was filed"
)
NONPROFIT_WAIVER_WORKERS = {
    # INVENTED workers of a 501(c)(3) employer: (waiver facts, concurrence,
    # other facts), and per year the outcome the sources give and the
    # deciding case.
    # H-A repro 1: a deemed certificate effective 1974-01-01 (first FICA
    # quarter 1974Q1) and a nurse's earlier service (RS 01901.540 C.2).
    "service_before_deemed_certificate": (
        (NONPROFIT_NOT_IN_EFFECT,),
        NONPROFIT_EXISTING_UNLISTED,
        {},
        {year: ("noncovered", "no_effective_waiver") for year in (1975, 1980)},
    ),
    # H-A repro 2: a certificate filed 1975-08-01 effective 1975-10-01 and
    # a listed employee's March 1975 service (C.3.a; NPO508 c).
    "listed_service_before_effective_date": (
        (NONPROFIT_NOT_IN_EFFECT,),
        NONPROFIT_COVERED_EMPLOYEE,
        {},
        {year: ("noncovered", "no_effective_waiver") for year in (1975, 1980)},
    ),
    "listed_existing_employee": (
        (NONPROFIT_IN_EFFECT,),
        NONPROFIT_COVERED_EMPLOYEE,
        {},
        {
            year: (
                "covered_above_threshold",
                "effective_waiver_concurring_employee",
            )
            for year in (1975, 1980)
        },
    ),
    # Includes a worker hired between the filing and the effective date,
    # for service from the effective date (NPO503, NPO505).
    "hired_after_filing": (
        (NONPROFIT_IN_EFFECT,),
        NONPROFIT_COVERED_EMPLOYEE,
        {},
        {
            year: (
                "covered_above_threshold",
                "effective_waiver_concurring_employee",
            )
            for year in (1975, 1980)
        },
    ),
    # r5 H-2 repro: a certificate filed 1974-03-01 and effective
    # 1974-01-01; a clerk employed since 1970 signs a supplemental list
    # filed 1975-05-15. Her 1974Q3 service: the 1958 (k)(1) note covers a
    # supplemental-list employee only from the first day of that list's
    # filing quarter.
    "supplemental_list_service_before_its_quarter": (
        (NONPROFIT_IN_EFFECT,),
        NONPROFIT_EXISTING_UNLISTED,
        {},
        {
            year: ("noncovered", "waiver_nonconcurring_existing_employee")
            for year in (1975, 1980)
        },
    ),
    # The same clerk's service from 1975-04-01.
    "supplemental_list_service_from_its_quarter": (
        (NONPROFIT_IN_EFFECT,),
        NONPROFIT_COVERED_EMPLOYEE,
        {},
        {
            year: (
                "covered_above_threshold",
                "effective_waiver_concurring_employee",
            )
            for year in (1975, 1980)
        },
    ),
    # r5 H-3 repro: a nurse hired in 1972 into a State-system position
    # moves in 1976 into the non-system group the 1973 certificate covers
    # (1958 (a)(8)(B) note).
    "group_joiner_after_filing_quarter": (
        (NONPROFIT_IN_EFFECT,),
        NONPROFIT_COVERED_EMPLOYEE,
        {},
        {
            year: (
                "covered_above_threshold",
                "effective_waiver_concurring_employee",
            )
            for year in (1975, 1980)
        },
    ),
    # M-2 repro: hired 1972-03-01 under a certificate filed 1975-08-01 and
    # made effective 1971-01-01; never signed (C.4 against NPO505/NPO506).
    "unlisted_hire_in_retroactive_period": (
        (NONPROFIT_IN_EFFECT,),
        NONPROFIT_RETRO_HIRE,
        {},
        {
            year: ("refuses", "waiver_retroactive_period_hire_unlisted")
            for year in (1975, 1980)
        },
    ),
    "unlisted_existing_employee": (
        (NONPROFIT_IN_EFFECT,),
        NONPROFIT_EXISTING_UNLISTED,
        {},
        {
            year: ("noncovered", "waiver_nonconcurring_existing_employee")
            for year in (1975, 1980)
        },
    ),
    "deemed_waiver_employee": (
        (NONPROFIT_DEEMED,),
        NONPROFIT_EXISTING_UNLISTED,
        {},
        {
            year: ("covered_above_threshold", "deemed_waiver_all_employees")
            for year in (1975, 1980)
        },
    ),
    # r5 H-4 repro: a clinic pays FICA 1974Q1-1975Q2, stops in 1975Q3 and
    # gets no refund; its 1976Q2 service, with no request. The 312(c) note
    # and D.8 settle it as noncovered (review r6 M-2).
    "deemed_certificate_k4c_gap": (
        (NONPROFIT_DEEMED, NONPROFIT_K4C_GAP),
        NONPROFIT_EXISTING_UNLISTED,
        {},
        {1975: ("noncovered", "deemed_waiver_k4c_period")},
    ),
    # The same service where the employee filed a timely 312(c) request.
    "deemed_certificate_k4c_gap_with_request": (
        (NONPROFIT_DEEMED, NONPROFIT_K4C_GAP),
        NONPROFIT_EXISTING_UNLISTED,
        {"historical_fica_treatment": NONPROFIT_312C_REQUEST},
        {
            1975: (
                "covered_above_threshold",
                "deemed_waiver_section_312c_request",
            )
        },
    ),
    "no_certificate": (
        (NONPROFIT_NOT_IN_EFFECT,),
        NONPROFIT_EXISTING_UNLISTED,
        {},
        {year: ("noncovered", "no_effective_waiver") for year in (1975, 1980)},
    ),
    "after_termination": (
        (NONPROFIT_NOT_IN_EFFECT,),
        NONPROFIT_COVERED_EMPLOYEE,
        {},
        {year: ("noncovered", "no_effective_waiver") for year in (1975, 1980)},
    ),
    "other_group_certificate_only": (
        (NONPROFIT_NOT_IN_EFFECT,),
        NONPROFIT_COVERED_EMPLOYEE,
        {},
        {year: ("noncovered", "no_effective_waiver") for year in (1975, 1980)},
    ),
}
# Review r6 M-1: the exempt-organization text each pre-1984 row states.
CIVIC_LEAGUE = {
    "nonprofit_1968_1977": (
        "employer is an organization exempt from income tax under 501(a), "
        "other than one described in 401(a) or in 501(c)(3)"
    ),
    "nonprofit_1978_1983": (
        "employer is an organization exempt from income tax under 501(a) "
        "(other than one described in 401(a)) or under 521, and not one "
        "described in 501(c)(3)"
    ),
}
NONPROFIT_WORKER_YEARS = sorted(
    (worker, year)
    for worker, (*_, outcomes) in NONPROFIT_WAIVER_WORKERS.items()
    for year in outcomes
)


@pytest.mark.parametrize(
    ("worker", "year"),
    NONPROFIT_WORKER_YEARS,
    ids=[f"{worker}-{year}" for worker, year in NONPROFIT_WORKER_YEARS],
)
def test_nonprofit_waiver_covers_only_listed_or_later_employees(
    registry, year, worker
):
    """Review r3 H1, r4 H-A and M-2, r5 H-2 to H-4, by fact pattern.

    NPO503 covers "the employees who signed the SS-15a, as well as those
    hired afterwards"; NPO505 and NPO506 exclude an existing employee who
    did not sign; the 1958 (k)(1) note covers a supplemental-list employee
    only from the first day of that list's filing quarter, and the 1958
    (a)(8)(B) note covers an employee who joins the certificate's
    3121(k)(1)(E) group after its filing quarter. RS 01901.540 D.7 deems a
    constructive waiver to cover all employees, effective (C.2) "with the
    first day of the quarter for which payments were made", and the Pub. L.
    95-216 section 312(c) note takes some of that service before July 1,
    1977 back out under 3121(k)(4)(C), whose text no capture holds. Former
    410(a)(8)(B) excludes the service unless a certificate "is (or is
    deemed to be) in effect" for it.
    """
    (rule,) = registry.lookup("nonprofit_service", year)
    waiver, concurrence, other, outcomes = NONPROFIT_WAIVER_WORKERS[worker]
    expected, decides = outcomes[year]
    facts = {
        "nonprofit_organization": NONPROFIT_501C3,
        "nonprofit_coverage_waiver": waiver,
        "nonprofit_employee_concurrence": concurrence,
        **other,
    }
    met = cases_met(rule, facts)
    actual = {
        "effective_waiver_concurring_employee",
        "waiver_retroactive_period_hire_unlisted",
        "waiver_nonconcurring_existing_employee",
        "no_effective_waiver",
    }
    # The actual-certificate cases are disjoint, so no rank decides
    # between sources there.
    assert len(met & actual) <= 1
    assert resolved_consequence(rule, facts) == expected
    if expected != "refuses":
        assert rule.resolve(met).get("case_id", "residual") == decides
    else:
        assert decides in met
    # Review r6 M-1: a civic league's worker, whatever its waiver, meets
    # the small-remuneration case (former 410(a)(10)), not the residual.
    other_employer = {
        **facts,
        "nonprofit_organization": (
            "employer is a 501(c)(4) civic league exempt under 501(a), not "
            "an organization described in 501(c)(3)",
            CIVIC_LEAGUE[rule.rule_id],
        ),
    }
    decided = rule.resolve(cases_met(rule, other_employer))
    assert decided.get("case_id") == "exempt_organization_small_remuneration"
    cases = {case["case_id"]: case for case in rule.cases}
    deemed = cases["deemed_waiver_all_employees"]["when"]
    assert "nonprofit_employee_concurrence" not in deemed
    quotes = {c.quote for c in rule.citations if c.quote}
    for passage in (
        "signed the Form SS-15a",
        "covering all employees",
        "effective with the first day of the quarter for which payments",
        "hired after the effective date of the certificate",
        "Service performed for this employer prior to that date",
        "is (or is deemed to be) in effect",
        "whose name appears on a supplemental list only with respect to "
        "service performed by the employee for the period beginning with "
        "the first day of the calendar quarter in which the supplemental "
        "list is filed",
        "became a member of such group",
    ):
        assert any(passage in quote for quote in quotes), passage
    if year < 1978:
        assert any("3121(k)(4)(C)" in quote for quote in quotes)
    assert "501(c)(3)" in rule.residual_default["description"]


# An INVENTED order member's facts (review r4 H-B, r5 H-1). 410(a)(8)(A)
# and 411(c)'s closing sentence reach every member "who has taken a vow of
# poverty as a member of such order"; 3121(r)(2)'s active, unretired
# member limits only what the election deems employment.
ORDER_VOWED = (
    "member of a religious order who has taken a vow of poverty as a "
    "member of such order, performing duties required by such order"
)
ORDER_ACTIVE = (
    "member of a religious order who is subject to a vow of poverty as a "
    "member of such order, performs tasks usually required (and to the "
    "extent usually required) of an active member of such order and is "
    "not considered retired because of old age or total disability "
    "(3121(r)(2)), performing duties required by such order"
)
ORDER_OUTSIDE_R2 = (
    "member of a religious order who has taken a vow of poverty as a member "
    "of such order but does not perform the tasks usually required of an "
    "active member of such order to the extent usually required, or is "
    "considered retired because of old age or total disability (outside "
    "3121(r)(2)), performing duties required by such order"
)
ACTIVE_VOWED = (ORDER_VOWED, ORDER_ACTIVE)
RETIRED_VOWED = (ORDER_VOWED, ORDER_OUTSIDE_R2)
NO_ORDER_ELECTION = (
    "no 3121(r) election by the member's order, or by the autonomous "
    "subdivision of it to which the member belongs, in effect for the period"
)
ORDER_ELECTION = (
    "effective 3121(r) election by the member's order, or by the autonomous "
    "subdivision of it to which the member belongs, covering the period"
)
# The election's covered case adds 3121(r)(3)(A)'s retroactive-quarter
# limb, which a member in a prospective quarter meets too.
ORDER_ELECTION_APPLIES = (
    "effective 3121(r) election by the member's order, or by the autonomous "
    "subdivision of it to which the member belongs, covering the period; for "
    "a retroactive quarter, the member was a member when performing the "
    "service and was living on the first day of the quarter in which the "
    "certificate was filed"
)
ORDER_RETROACTIVE_FAILED = (
    "3121(r) certificate whose designated retroactive period (a quarter "
    "before the quarter of filing) covers the service, where the member was "
    "not a member when performing the service or was not living on the "
    "first day of the quarter in which the order filed the certificate"
)
ORDER_ABROAD_NONCITIZEN = (
    "not a United States citizen",
    "neither a United States citizen nor a resident alien",
)
ORDER_MEMBERS = {
    # member: (order service, exemption, place, alien status or
    # citizenship), the outcome the sources give and the deciding case.
    "vow_duties_no_election": (
        ACTIVE_VOWED,
        (NO_ORDER_ELECTION,),
        "in the United States",
        "a United States citizen",
        "noncovered",
        "vow_duties_without_election",
    ),
    # r5 H-1 repro: a nun retired for old age in 1975 does order duties in
    # 1979, and her order never elected.
    "retired_member_no_election": (
        RETIRED_VOWED,
        (NO_ORDER_ELECTION,),
        "in the United States",
        "a United States citizen",
        "noncovered",
        "vow_duties_without_election",
    ),
    # The same retired nun when her order has an election: 3121(r)(1)(C)
    # deems only a 3121(r)(2) member's duties to be employment.
    "retired_member_under_election": (
        RETIRED_VOWED,
        (ORDER_ELECTION,),
        "in the United States",
        "a United States citizen",
        "noncovered",
        "vowed_member_outside_3121r2_definition",
    ),
    "election_prospective_quarter": (
        ACTIVE_VOWED,
        (ORDER_ELECTION, ORDER_ELECTION_APPLIES),
        "in the United States",
        "a United States citizen",
        "covered",
        "vow_duties_with_3121r_election",
    ),
    "election_retroactive_quarter_conditions_met": (
        ACTIVE_VOWED,
        (ORDER_ELECTION, ORDER_ELECTION_APPLIES),
        "in the United States",
        "a United States citizen",
        "covered",
        "vow_duties_with_3121r_election",
    ),
    # H-B repro: an order files on 1975-02-10 designating 1970-01-01; a
    # member did order duties in 1971 and died before the filing quarter.
    "retroactive_quarter_member_died": (
        ACTIVE_VOWED,
        (ORDER_ELECTION, ORDER_RETROACTIVE_FAILED),
        "in the United States",
        "a United States citizen",
        "noncovered",
        "retroactive_quarter_member_condition_failed",
    ),
    # r5 H-1: a vowed sister retired for total disability in 1969 does
    # order duties in 1971 in a quarter the order's 1975 certificate
    # designates. She was not a 3121(r)(2) member when she did them.
    "retroactive_quarter_not_a_member": (
        RETIRED_VOWED,
        (ORDER_ELECTION, ORDER_RETROACTIVE_FAILED),
        "in the United States",
        "a United States citizen",
        "noncovered",
        "retroactive_quarter_member_condition_failed",
    ),
    # Review r5 M-2 (A4 F2): a citizen member abroad under an election is
    # covered; the oracle never reads "a United States citizen" as "not a
    # United States citizen".
    "election_citizen_abroad": (
        ACTIVE_VOWED,
        (ORDER_ELECTION, ORDER_ELECTION_APPLIES),
        "outside the United States",
        "a United States citizen",
        "covered",
        "vow_duties_with_3121r_election",
    ),
    "election_noncitizen_abroad": (
        ACTIVE_VOWED,
        (ORDER_ELECTION, ORDER_ELECTION_APPLIES),
        "outside the United States",
        ORDER_ABROAD_NONCITIZEN,
        "noncovered",
        "election_member_abroad_not_covered",
    ),
}


ORDER_NO_AGREEMENT = (
    "no agreement under section 433 (section 233 of the Social Security "
    "Act) designates this service as employment or recognizes it as "
    "equivalent to employment (410(a)(C), effective in taxable years "
    "beginning on or after April 20, 1983)"
)


@pytest.mark.parametrize("member", sorted(ORDER_MEMBERS))
@pytest.mark.parametrize(
    "rule_id", ["religious_order_1968_1983", "religious_order_1984_2026"]
)
def test_religious_order_members_resolve_from_their_facts(
    registry, rule_id, member
):
    """Review r4 H-B and r5 H-1, by fact pattern. 3121(r)(3)(A) applies an
    election to pre-filing quarters "only if the member performing such
    services was a member at the time such services were performed and is
    living on the first day of the quarter in which such certificate is
    filed", so a member who fails it stays excluded by the vow of poverty.
    The vow excludes a retired member's duties too: 3121(r)(2)'s "active"
    and "not considered retired" define a member only "For purposes of
    this subsection", the election."""
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    service, exemption, place, status, expected, decides = ORDER_MEMBERS[
        member
    ]
    facts = {
        "religious_order_service": service,
        "clergy_or_religious_exemption": exemption,
        "place_of_work": place,
        "citizenship": status,
        "nonresident_alien_status": status,
        # Review r7 low 9: no section 433 agreement designates the service
        # (410(a)(C)); the sweep fixture holds the member it reaches.
        "social_security_agreement_coverage": ORDER_NO_AGREEMENT,
    }
    assert resolved_consequence(rule, facts) == expected
    decided = rule.resolve(cases_met(rule, facts))
    assert decided.get("case_id", "residual") == decides
    third_party = {
        "religious_order_service": (
            "ordinary employment for a third party outside duties required "
            "by the order"
        )
    }
    assert resolved_consequence(rule, third_party) == "covered"
    # Without a vow this family excludes nothing; the clergy family, which
    # defers vow-of-poverty order duties here, decides (r4 sweep).
    no_vow = {
        "religious_order_service": (
            "duties required by the order, performed by a member who has "
            "not taken a vow of poverty"
        )
    }
    assert resolved_consequence(rule, no_vow) == "covered"


# Phrases stating an INVENTED 2018-2026 council member's facts (r4 H-C).
TRIBAL_COUNCIL_MEMBER = (
    "service as a member or the head of an Indian tribal council, in that "
    "capacity, for the tribal government"
)
TRIBAL_NOT_INCLUDED = (
    "council-capacity services not included under an effective section "
    "418a agreement"
)
TRIBAL_INCLUDED = (
    "council-capacity services performed on or after the effective date of "
    "an effective section 418a agreement"
)
TRIBAL_2018_MEMBERS = {
    "recognized_tribe_no_agreement": (
        "federally recognized tribe",
        TRIBAL_NOT_INCLUDED,
        "noncovered",
    ),
    # H-C repro: a council member of an unrecognized tribe in 2020.
    "unrecognized_tribe_no_agreement": (
        "a tribe that is not federally recognized",
        TRIBAL_NOT_INCLUDED,
        "covered",
    ),
    "recognized_tribe_agreement": (
        "federally recognized tribe",
        TRIBAL_INCLUDED,
        "covered",
    ),
}


@pytest.mark.parametrize("member", sorted(TRIBAL_2018_MEMBERS))
def test_tribal_council_2018_resolves_from_its_facts(registry, member):
    """Review r4 H-C: 418a(b)(2) defines a tribal council as "the appointed
    or elected governing body of a federally recognized Indian tribe", and
    POMS RS 01901.700 F covers every service of a tribe that is not."""
    (rule,) = registry.lookup_date("tribal_council_service", date(2020, 6, 1))
    recognition, agreement, expected = TRIBAL_2018_MEMBERS[member]
    facts = {
        "tribal_council_service": TRIBAL_COUNCIL_MEMBER,
        "tribal_federal_recognition": recognition,
        "tribal_coverage_agreement": agreement,
    }
    assert resolved_consequence(rule, facts) == expected
    staff = {**facts, "tribal_council_service": "council staff"}
    assert resolved_consequence(rule, staff) == "covered"


# Phrases stating INVENTED crew members' facts (review r4 M-3): a new
# boat crewed by 5 has no four-quarter average, and noncash pay did not
# defeat the pre-1996 test.
FISHING_NOT_FICA = (
    "payor did not treat the remuneration, when paid, as subject to FICA tax"
)
FISHING_FICA = (
    "payor treated the remuneration, when paid, as subject to FICA tax"
)
FISHING_SHARE_1996 = (
    "a share of the boat's catch or its proceeds (or the boats' catch in a "
    "fishing operation involving more than one boat) that depends on the "
    "amount caught, where the operating crew of the boat (or each boat from "
    "which the individual receives a share) is normally made up of fewer "
    "than 10 individuals (a crew whose average size on trips made during the "
    "preceding 4 calendar quarters was fewer than 10 is treated as normally "
    "fewer than 10), with no additional compensation other than cash of at "
    "most $100 per trip that is contingent on a minimum catch and paid "
    "solely for additional duties (such as mate, engineer, or cook) for "
    "which additional cash is traditional in the industry"
)
FISHING_SHARE_BEFORE_1996 = (
    "a share of the boat's catch or its proceeds (or the boats' catch in a "
    "fishing operation involving more than one boat) that depends on the "
    "amount caught, where the operating crew of the boat (or each boat from "
    "which the individual receives a share) is normally made up of fewer "
    "than 10 individuals, with no cash remuneration apart from that share "
    "(former 410(a)(20)(A), before the 1996 amendment)"
)
FISHING_CREW = {
    # (year, FICA treatment, arrangement texts the crew member meets) and
    # the deciding case. A new boat crewed by 5 has no four-quarter
    # average; noncash pay did not defeat the pre-1996 test.
    "new_boat_no_fica": (
        1991,
        FISHING_NOT_FICA,
        FISHING_SHARE_1996,
        "catch_share_1996_clarification",
    ),
    "noncash_pay_payor_fica": (
        1991,
        FISHING_FICA,
        FISHING_SHARE_BEFORE_1996,
        "catch_share_payor_treated_as_fica",
    ),
    "new_boat_after_1994": (
        2015,
        FISHING_NOT_FICA,
        FISHING_SHARE_1996,
        "qualifying_catch_share_arrangement",
    ),
    # Review r5 M-2 (A4 2d): neighbours who just miss. A boat normally
    # crewed by 12, and a $150 cash bonus, meet neither text; the
    # residual's ordinary wage rules apply.
    "crew_of_twelve_payor_fica": (
        1991,
        FISHING_FICA,
        "a share of the catch on a boat whose crew is normally 12",
        "residual",
    ),
    "cash_bonus_150_after_1994": (
        2015,
        FISHING_NOT_FICA,
        "a share of the catch plus a $150 cash bonus per trip as mate",
        "residual",
    ),
}


@pytest.mark.parametrize("crew", sorted(FISHING_CREW))
def test_fishing_crew_test_is_normally_under_ten(registry, crew):
    """410(a)(20)(C): "is normally made up of fewer than 10 individuals";
    the closing sentence only deems an average under 10 to meet it. A
    qualifying crew member reaches the self-employment case, not the
    residual's ordinary wage rules (review r4 M-3)."""
    year, fica, arrangement, expected = FISHING_CREW[crew]
    (rule,) = registry.lookup("fishing_crew_share_service", year)
    facts = {
        "historical_fica_treatment": fica,
        "fishing_catch_share_arrangement": arrangement,
    }
    decided = rule.resolve(cases_met(rule, facts))
    assert decided.get("case_id", "residual") == expected


# INVENTED self-employed people, by the phrases stating their 411(b)
# facts (review r4 M-4): (year, facts, outcome).
NONRESIDENT_ALIEN = "nonresident alien individual for the taxable year"
SECTION_433_AGREEMENT = (
    "an agreement under section 433 makes the net earnings of this "
    "nonresident alien self-employment income for the taxable year"
)
TERRITORIAL_RESIDENT = (
    "a resident of the Commonwealth of Puerto Rico, the Virgin Islands, "
    "Guam, or American Samoa"
)
# The clergy rows' nonresident-alien texts (review r4 M-4).
CLERGY_NONRESIDENT_ALIEN = {
    "clergy_1973_1981": (
        "nonresident alien individual for the taxable year (a noncitizen who "
        "is a resident of the Commonwealth of Puerto Rico, the Virgin "
        "Islands, Guam, or American Samoa is not one)"
    ),
    "clergy_1982_2026": (
        "nonresident alien individual for the taxable year (a noncitizen who "
        "is a resident of the Commonwealth of Puerto Rico, the Virgin "
        "Islands, Guam, or American Samoa is not one), and, for a taxable "
        "year beginning on or after 1983-04-20, no agreement under section "
        "433 covers the earnings"
    ),
}
CLERGY_MINISTRY = (
    "qualifying ministry, order duties, or service in the exercise of the "
    "profession of a Christian Science practitioner"
)
NONRESIDENT_SELF_EMPLOYED = {
    "nonresident_alien_1978": (
        1978,
        {"nonresident_alien_status": NONRESIDENT_ALIEN},
        "noncovered",
    ),
    "nonresident_alien_2010": (
        2010,
        {"nonresident_alien_status": NONRESIDENT_ALIEN},
        "noncovered",
    ),
    # Before 1983-04-20 no agreement exception exists.
    "agreement_before_1983": (
        1980,
        {
            "nonresident_alien_status": (
                NONRESIDENT_ALIEN,
                "an agreement under section 433 covers the earnings",
            )
        },
        "noncovered",
    ),
    "agreement_after_1983": (
        1995,
        {
            "nonresident_alien_status": (
                NONRESIDENT_ALIEN,
                SECTION_433_AGREEMENT,
            )
        },
        "covered",
    ),
    # 411(b)'s last sentence: a noncitizen resident of Guam is not a
    # nonresident alien (review r5 M-2, A4 F8).
    "guam_resident_noncitizen": (
        1970,
        {
            "nonresident_alien_status": (
                "not a nonresident alien: a noncitizen resident of Guam"
            ),
            "citizenship": "not a citizen of the United States",
            "country_of_residence": TERRITORIAL_RESIDENT,
        },
        "covered",
    ),
    "citizen": (2000, {"citizenship": "a United States citizen"}, "covered"),
}


@pytest.mark.parametrize("person", sorted(NONRESIDENT_SELF_EMPLOYED))
def test_nonresident_alien_net_earnings_follow_411b(registry, person):
    """411(b): self-employment income is the net earnings of an individual
    "(other than a nonresident alien individual, except as provided by an
    agreement under section 433 of this title)", the agreement clause from
    taxable years beginning on or after 1983-04-20 (Pub. L. 98-21 section
    322(c)); a noncitizen resident of Puerto Rico, the Virgin Islands,
    Guam or American Samoa is not a nonresident alien (review r4 M-4)."""
    year, facts, expected = NONRESIDENT_SELF_EMPLOYED[person]
    (rule,) = registry.lookup("self_employment_nonresident_alien", year)
    assert resolved_consequence(rule, facts) == expected
    # The clergy rows read a plain nonresident alien or citizen the same
    # way.
    if person in {
        "nonresident_alien_1978",
        "nonresident_alien_2010",
        "citizen",
    }:
        clergy = next(
            r
            for r in registry.rules
            if r.family == "clergy_religious_service"
            and r.effective_start.year <= year <= r.effective_end.year
        )
        ministry = {**facts, "ministerial_service": CLERGY_MINISTRY}
        if "nonresident_alien_status" in facts:
            ministry["nonresident_alien_status"] = CLERGY_NONRESIDENT_ALIEN[
                clergy.rule_id
            ]
        assert (
            "nonresident_alien_ministry" in cases_met(clergy, ministry)
        ) == (expected == "noncovered")


# Review r5 H-5: INVENTED people whose amounts the base definition must
# keep or exclude, by the texts of the conditions they meet.
BASE_NOT_OWN_BUSINESS = (
    "the amount is not derived from any trade or business (as 411(c) "
    "defines the term) carried on by the person, and no 411(a)(5) rule "
    "treats it as the person's gross income (before taxable years "
    "including October 1980, former 411(a)(5)(A) treated all of a "
    "community business's gross income and deductions as the husband's "
    "unless the wife exercised substantially all of the management and "
    "control)"
)
BASE_NOT_PARTNERSHIP_INCOME = (
    "the amount is not the person's distributive share of the ordinary net "
    "income or loss from a trade or business carried on by a partnership "
    "of which the person is a member, and not a guaranteed payment "
    "described in section 707(c) from such a partnership"
)
BASE_DEFINITION_PEOPLE = {
    # A limited partner paid by the partnership for its bookkeeping, 2000:
    # a 707(c) guaranteed payment, which 411(a)(12) keeps.
    "limited_partner_guaranteed_payment": (
        2000,
        {
            "trade_or_business": BASE_NOT_OWN_BUSINESS,
            "partnership_status": (
                "a guaranteed payment described in section 707(c) from a "
                "partnership of which the person is a member"
            ),
        },
        "covered",
        "residual",
    ),
    # A general partner's guaranteed payment for the use of capital, 1990:
    # the 1985 Form 1040 instructions include "any guaranteed payments".
    "general_partner_capital_payment": (
        1990,
        {
            "trade_or_business": BASE_NOT_OWN_BUSINESS,
            "partnership_status": (
                "a guaranteed payment described in section 707(c) from a "
                "partnership of which the person is a member"
            ),
        },
        "covered",
        "residual",
    ),
    # A husband in a community property State, 1975, whose store a hired
    # manager runs; his wife does not exercise substantially all of the
    # management and control, so former 411(a)(5)(A) makes it his.
    "husband_under_former_411a5a": (
        1975,
        {
            "trade_or_business": (
                "the amount is not derived from any trade or business "
                "carried on by the person, but former 411(a)(5)(A) treats "
                "it as the person's gross income"
            ),
            "partnership_status": BASE_NOT_PARTNERSHIP_INCOME,
        },
        "covered",
        "residual",
    ),
    # The neighbour who just misses: interest on a savings account, 2000.
    "savings_interest": (
        2000,
        {
            "trade_or_business": BASE_NOT_OWN_BUSINESS,
            "partnership_status": BASE_NOT_PARTNERSHIP_INCOME,
        },
        "noncovered",
        "outside_own_trade_or_business_and_partnership",
    ),
}


@pytest.mark.parametrize("person", sorted(BASE_DEFINITION_PEOPLE))
def test_base_definition_keeps_guaranteed_payments_and_411a5_income(
    registry, person
):
    """Review r5 H-5: 411(a)(12) excludes a limited partner's share "other
    than guaranteed payments described in section 707(c)", the 1985 Form
    1040 instructions include "any guaranteed payments", and former
    411(a)(5)(A) treated a community business's income "as the gross income
    and deductions of the husband unless the wife exercises substantially
    all of the management and control". None of these amounts is outside
    the person's net earnings, so the base family excludes none of them."""
    year, facts, expected, decides = BASE_DEFINITION_PEOPLE[person]
    (rule,) = registry.lookup("self_employment_base_definition", year)
    decided = rule.resolve(cases_met(rule, facts))
    assert decided["consequence"] == expected
    assert decided.get("case_id", "residual") == decides
    quotes = " ".join(c.quote for c in rule.citations if c.quote)
    assert "other than guaranteed payments described in section 707(c)" in (
        quotes
    )
    assert "unless the wife exercises substantially all" in quotes


# Review r4 M-5: for each REQUIRED_CONDITIONS entry on a covered case,
# an INVENTED worker who meets the case except for its condition, by the
# texts of the conditions the worker meets. "reaches" names the
# consequence the failure must reach and the case (or residual) that
# decides it; "stays_covered" says why failing leaves the worker covered,
# and which case (or the residual) decides (review r5 M-2: every entry
# names its path).
# An INVENTED State or local employee, as the State and local cases'
# government_level states the level (round 5).
STATE_EMPLOYEE = (
    "employee of a State (one of the 50 States, the Commonwealth of Puerto "
    "Rico or the Virgin Islands, each a State under 410(h)), of a political "
    "subdivision or of a wholly owned instrumentality, other than the "
    "District of Columbia, Guam and American Samoa"
)
ELECTION_WORKER = "election official or election worker"
GRANDFATHERED_FEDERAL = (
    "would be excluded under 410(a)(5)-(6) as in effect in January 1983 "
    "and has been performed continuously since December 31, 1983, under "
    "the continuity rules of 410(a)(5)(B)(i)(I)-(V)"
)
LEGISLATIVE_STILL_UNDER_CSRS = (
    "reaches",
    {
        "government_level": (
            "employee of the United States or of an instrumentality of the "
            "United States"
        ),
        "federal_service": (
            "service in the legislative branch of the Federal Government "
            "other than as a Member, Delegate or Resident Commissioner",
            GRANDFATHERED_FEDERAL,
        ),
        "federal_retirement_system": (
            "subject throughout to subchapter III at the full contribution"
        ),
    },
    "noncovered",
    "grandfathered_continuous_service",
)
DESIGNATED_ORGANIZATION = (
    "employee of a public international organization designated under the "
    "International Organizations Immunities Act, while the designation is "
    "in effect and its conditions are met"
)
CRP_PAYMENT = (
    "payment under 16 U.S.C. 3833(2), or, after Pub. L. 113-79 generally "
    "amended section 1233 of the Food Security Act of 1985 on 2014-02-07, "
    "under 16 U.S.C. 3833(a)(2), where the substance of former section "
    "1233(2) now appears"
)
ELECTION_LOWER_AMOUNT = (
    "covered for OASDI (old-age, survivors and disability insurance) by a "
    "section 218 agreement that excludes election workers paid less than an "
    "amount the agreement states below the statutory amount; a modification "
    "under 418(v), redesignated 418(n), that extends only Medicare hospital "
    "insurance does not count"
)
# Review r7 H-1: membership of "a retirement system of such State,
# political subdivision, or instrumentality" (410(a)(7)(F)) goes entity by
# entity, not position by position (26 C.F.R. 31.3121(b)(7)-2(c)(2)): a
# system the employing entity maintains, alone or with others (a statewide
# system included), whichever of its positions the membership comes through.
ELECTION_NONMEMBER = (
    "not a member, when the service is performed, of any qualified "
    "retirement system (the IRS standards of 26 C.F.R. 31.3121(b)(7)-2, as "
    "POMS SL 50001.501 B cites them) that the State, political subdivision "
    "or instrumentality employing the individual maintains, alone or with "
    "other such entities (a statewide system included); membership goes "
    "entity by entity, not position by position (31.3121(b)(7)-2(c)(2)), "
    "so membership only in a system this employer does not maintain does "
    "not count, and an employee who belongs only to a system that fails "
    "those standards meets this condition"
)
ELECTION_MEMBER = (
    "member, when the service is performed, of a qualified retirement "
    "system (the IRS standards of 26 C.F.R. 31.3121(b)(7)-2, as POMS SL "
    "50001.501 B cites them) that the State, political subdivision or "
    "instrumentality employing the individual maintains, alone or with "
    "other such entities (a statewide system included); membership goes "
    "entity by entity, not position by position (31.3121(b)(7)-2(c)(2)), "
    "so membership through one position with this employer generally "
    "counts for service in its other positions, and benefits from service "
    "for another entity count only as 31.3121(b)(7)-2(d)(4)(ii) and "
    "(e)(2)(v) allow"
)
NO_OASDI_AGREEMENT = (
    "not covered for OASDI by any effective agreement/modification, "
    "including a position that only a Medicare hospital insurance "
    "modification under 418(v), redesignated 418(n), reaches"
)
REQUIRED_CONDITION_FAILURES = {
    # Review r7 H-1 pins the entity-by-entity membership text in these
    # covered cases too: a member of a qualified system the employing
    # entity maintains reaches the member case's exclusion.
    **{
        (rule_id, case_id): (
            "reaches",
            {
                "government_level": STATE_EMPLOYEE,
                "public_retirement_system_participation": ELECTION_MEMBER,
                "section_218_position": NO_OASDI_AGREEMENT,
                **extra,
            },
            "noncovered",
            via,
        )
        for rule_id, case_id, extra, via in (
            (
                "state_local_1991_2026",
                "mandatory_nonmember_coverage",
                {},
                "qualified_system_member_without_agreement",
            ),
            *[
                (
                    rule_id,
                    "outside_agreement_nonmember",
                    {"election_work": ELECTION_WORKER},
                    "outside_agreement_member",
                )
                for rule_id in (
                    "election_work_1991_0702",
                    "election_work_1995",
                )
            ],
        )
    },
    **{
        (rule_id, "vow_duties_with_3121r_election"): (
            "reaches",
            {
                "clergy_or_religious_exemption": (
                    ORDER_ELECTION,
                    ORDER_RETROACTIVE_FAILED,
                ),
                "religious_order_service": ACTIVE_VOWED,
            },
            "noncovered",
            "retroactive_quarter_member_condition_failed",
        )
        for rule_id in (
            "religious_order_1968_1983",
            "religious_order_1984_2026",
        )
    },
    (
        "se_conservation_reserve_2008_2026",
        "crp_payment_in_real_estate_dealer_business",
    ): (
        "reaches",
        {
            "conservation_reserve_payment": CRP_PAYMENT,
            "real_estate_dealer_status": "not a real estate dealer",
            "benefit_type": (
                "recipient is receiving benefits under 42 U.S.C. 402 or 423"
            ),
        },
        "noncovered",
        "crp_payment_to_beneficiary",
    ),
    **{
        key: (
            "stays_covered",
            "A crew member outside 410(a)(20)'s terms is in employment: the "
            "residual applies the ordinary wage rules, so the pay stays "
            "covered as wages instead of 411(c)(2)(F) self-employment.",
            facts,
            "residual",
        )
        for key, facts in (
            (
                (
                    "fishing_crew_share_service_1989",
                    "catch_share_1996_clarification",
                ),
                {
                    "historical_fica_treatment": FISHING_NOT_FICA,
                    "fishing_catch_share_arrangement": (
                        "a share of the catch plus a $150 cash bonus"
                    ),
                },
            ),
            (
                (
                    "fishing_crew_share_service_1989",
                    "catch_share_payor_treated_as_fica",
                ),
                {
                    "historical_fica_treatment": FISHING_FICA,
                    "fishing_catch_share_arrangement": (
                        "a share of the catch plus a $50 cash bonus"
                    ),
                },
            ),
            (
                (
                    "fishing_crew_share_service_1995",
                    "qualifying_catch_share_arrangement",
                ),
                {
                    "fishing_catch_share_arrangement": (
                        "a flat $80 per trip, not a share of the catch"
                    )
                },
            ),
        )
    },
    (
        "tribal_council_service_2018_0920",
        "section_418a_retroactive_inclusion",
    ): (
        "reaches",
        {
            "tribal_council_service": TRIBAL_COUNCIL_MEMBER,
            "tribal_federal_recognition": "federally recognized tribe",
            "tribal_coverage_agreement": (
                "council-capacity services before the agreement's effective "
                "date that the tribe, at the time of the agreement, asked the "
                "agreement to include",
                TRIBAL_NOT_INCLUDED,
            ),
            "historical_fica_treatment": (
                "FICA-equivalent amounts were never paid for the service"
            ),
        },
        "noncovered",
        "no_section_418a_inclusion",
    ),
    **{
        (rule_id, case_id): LEGISLATIVE_STILL_UNDER_CSRS
        for rule_id, case_id in (
            ("federal_1984_1986", "legislative_not_retirement_covered_1983"),
            ("federal_1984_1986", "legislative_lump_sum_after_1983"),
            ("federal_1984_1986", "legislative_ceased_coverage_after_1983"),
            ("federal_1987_2026", "legislative_not_retirement_covered_1983"),
            ("federal_1987_2026", "legislative_ceased_coverage_after_1983"),
        )
    },
    ("federal_1987_2026", "after_official_service_from_1988_11_10"): (
        "reaches",
        {
            "federal_service": GRANDFATHERED_FEDERAL,
            "government_level": (
                "employee of the United States or of an instrumentality of "
                "the United States"
            ),
        },
        "noncovered",
        "grandfathered_continuous_service",
    ),
    **{
        (rule_id, case_id): (
            "stays_covered",
            "Membership decides which amount applies, not whether pay is "
            "covered: POMS SL 30001.357's NOTE covers a nonmember unless "
            "410(a)(7)(F)(iv) excepts the pay, and a member's pay is "
            "covered when the agreement's amount is met. A worker who fails "
            "one case's membership limb meets its twin.",
            {
                "section_218_position": ELECTION_LOWER_AMOUNT,
                "public_retirement_system_participation": phrase,
                "government_level": STATE_EMPLOYEE,
                "election_work": ELECTION_WORKER,
            },
            via,
        )
        for rule_id in ("election_work_1991_0702", "election_work_1995")
        for case_id, phrase, via in (
            (
                "agreement_with_lower_threshold_nonmember",
                ELECTION_MEMBER,
                "agreement_with_lower_threshold_member",
            ),
            (
                "agreement_with_lower_threshold_member",
                ELECTION_NONMEMBER,
                "agreement_with_lower_threshold_nonmember",
            ),
        )
    },
    **{
        (rule_id, "us_citizen_in_united_states"): (
            "reaches",
            {
                "citizenship": "a citizen of Canada",
                "place_of_work": "United States",
                "international_organization_service": (
                    DESIGNATED_ORGANIZATION
                ),
            },
            "noncovered",
            "designated_international_organization",
        )
        for rule_id in (
            "international_organization_service_1968",
            "international_organization_service_1995",
        )
    },
    (
        "international_organization_service_1995",
        "transferred_federal_employee_410r",
    ): (
        "reaches",
        {
            "federal_service": "no Federal service before joining",
            "citizenship": "a citizen of Canada",
            "international_organization_service": DESIGNATED_ORGANIZATION,
        },
        "noncovered",
        "designated_international_organization",
    ),
    **{
        (rule_id, "statutory_homeworker"): (
            "reaches",
            {
                "occupation": "home worker who invested substantially in "
                "facilities",
                "employee_self_or_mixed": "independent contractor",
            },
            "deferred",
            "residual",
        )
        for rule_id in (
            "statutory_homeworker_service_1968",
            "statutory_homeworker_service_1978",
        )
    },
}
COVERED_CONSEQUENCES = {"covered", "covered_above_threshold"}


def test_every_covered_required_condition_names_its_failure():
    """Review r4 M-5: each REQUIRED_CONDITIONS entry on a covered case says
    what its condition's failure reaches."""
    covered = set()
    for rule_id, case_id, *_ in REQUIRED_CONDITIONS:
        row = REQUIRED_CONDITION_ROWS[rule_id]
        case = next(c for c in row["cases"] if c["case_id"] == case_id)
        if case["consequence"] in COVERED_CONSEQUENCES:
            covered.add((rule_id, case_id))
    assert set(REQUIRED_CONDITION_FAILURES) == covered
    # Review r7 H-1 adds the three covered membership cases (25).
    assert len(covered) == 25


@pytest.mark.parametrize(
    "key",
    sorted(REQUIRED_CONDITION_FAILURES),
    ids=["-".join(key) for key in sorted(REQUIRED_CONDITION_FAILURES)],
)
def test_failing_a_covered_condition_reaches_an_exclusion(registry, key):
    """Review r4 M-5: a condition that changes no outcome is vacuous. The
    worker who fails it misses the covered case and reaches the exclusion
    the sources give, or the entry says why the worker stays covered."""
    rule_id, case_id = key
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    kind, *rest = REQUIRED_CONDITION_FAILURES[key]
    if kind == "stays_covered":
        reason, facts, via = rest
        assert reason.strip()
        expected = None
    else:
        facts, expected, via = rest
    assert via is not None and via != case_id
    assert via == "residual" or via in {c["case_id"] for c in rule.cases}
    met = cases_met(rule, facts)
    decided = rule.resolve(met)
    assert decided.get("case_id", "residual") == via
    if expected is None:
        assert decided["consequence"] in COVERED_CONSEQUENCES
    else:
        assert decided["consequence"] == expected
    assert case_id not in met


INVENTED_SWEEP_FIXTURE = json.loads(
    (Path(__file__).parent / "ce1_invented_sweep_workers.json").read_text()
)
INVENTED_SWEEP_WORKERS = INVENTED_SWEEP_FIXTURE["workers"]
JUST_MISS_REQUIRED = [
    tuple(key) for key in INVENTED_SWEEP_FIXTURE["just_miss_required"]
]
JUST_MISS_OWN_TEXT = {
    tuple(key) for key in INVENTED_SWEEP_FIXTURE["just_miss_own_text"]
}
JUST_MISS_STATED_LIMITS = {
    tuple(key.split("|")): reason
    for key, reason in INVENTED_SWEEP_FIXTURE[
        "just_miss_stated_limits"
    ].items()
}
# Review r6 M-1: conditions of multi-condition cases that no worker just
# misses. Each such condition can be dropped without failing a test, so
# the number is the PR's stated limit; it may fall, never rise.
# Review r7: the round's just-miss workers bring it from 178 to 171.
UNSEEN_CONDITION_LIMIT = 171


@pytest.mark.parametrize(
    "worker",
    INVENTED_SWEEP_WORKERS,
    ids=[f"{w['rule_id']}-{i}" for i, w in enumerate(INVENTED_SWEEP_WORKERS)],
)
def test_swept_rows_resolve_invented_workers_from_their_facts(
    registry, worker
):
    """Review r4 item 9: the exclusion sweep's fact patterns. Each worker
    named in a sweep finding, and a neighbour whose outcome must not
    change, resolves from the cases its facts meet."""
    rule = next(r for r in registry.rules if r.rule_id == worker["rule_id"])
    assert resolved_consequence(rule, worker["facts"]) == worker["expected"]
    met = cases_met(rule, worker["facts"])
    if worker["expected"] == "refuses" and rule.open_reason is not None:
        # The whole row is an open legal question.
        assert worker["decides"] == "row_open"
    elif worker["expected"] == "refuses":
        # The deciding case is the open one: it ranks first among those met.
        first = min(
            (c for c in rule.cases if c["case_id"] in met),
            key=lambda c: c["precedence"],
        )
        assert first["case_id"] == worker["decides"]
        assert "open_reason" in first
    else:
        decided = rule.resolve(met)
        assert decided.get("case_id", "residual") == worker["decides"]
        # Review r6 M-1: a deferral's target is pinned too.
        if worker["expected"] == "deferred":
            assert list(decided["defers_to"]) == worker["defers_to"]


def test_every_case_and_residual_decides_a_swept_worker():
    """Review r5 items 6 and 7: the sweep fixture holds, for every case of
    every row, a worker that case decides, and for every closed row a
    worker its residual decides (for an open row, a worker it refuses).
    Under the exact-text oracle, a case narrowed, broadened or reworded
    then fails at least one worker, and a consequence or rank change fails
    the worker it decides."""
    decided = {}
    for worker in INVENTED_SWEEP_WORKERS:
        decided.setdefault(worker["rule_id"], set()).add(worker["decides"])
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    missing = {}
    for row in rows:
        want = {case["case_id"] for case in row["cases"]}
        want.add("row_open" if row["open_reason"] else "residual")
        if gap := want - decided.get(row["rule_id"], set()):
            missing[row["rule_id"]] = sorted(gap)
    assert missing == {}
    assert len(rows) == 119
    assert sum(len(row["cases"]) for row in rows) == 364
    deferred = [
        w for w in INVENTED_SWEEP_WORKERS if w["expected"] == "deferred"
    ]
    assert all(w["defers_to"] for w in deferred)


def stated(facts, fact):
    """The texts a worker states for one fact, as a tuple."""
    value = facts.get(fact, ())
    return (value,) if isinstance(value, (str, bool)) else tuple(value)


def just_miss_workers(row, case, fact, own_text=False, workers=None):
    """INVENTED workers who just miss ``case`` on ``fact`` (review r6 M-1).

    Each states every other condition of the case exactly, does not state
    the case's text for ``fact``, and is decided below the case (by a
    lower-ranked case or the residual). Dropping ``fact`` from the case
    would make the case decide that worker, so the sweep test would fail.
    With ``own_text``, the worker also states for ``fact`` a text of its
    own, which no case of the row reads. ``workers`` defaults to the sweep
    fixture; the checker's own test passes its INVENTED worker instead of
    adding it to the fixture's list (review r7 low 10).
    """
    rank = {c["case_id"]: c["precedence"] for c in row["cases"]}
    case_texts = {c["when"][fact] for c in row["cases"] if fact in c["when"]}
    others = {f: t for f, t in case["when"].items() if f != fact}
    found = []
    for worker in INVENTED_SWEEP_WORKERS if workers is None else workers:
        if worker["rule_id"] != row["rule_id"]:
            continue
        facts = worker["facts"]
        if not all(
            any(_text_holds(p, t) for p in stated(facts, f))
            for f, t in others.items()
        ):
            continue
        own = stated(facts, fact)
        if any(_text_holds(p, case["when"][fact]) for p in own):
            continue
        if own_text and not any(p not in case_texts for p in own):
            continue
        if rank.get(worker["decides"], len(rank) + 1) > case["precedence"]:
            found.append(worker)
    return found


def _text_holds(phrase, condition):
    if isinstance(phrase, bool) or isinstance(condition, bool):
        return phrase is condition
    return phrase == condition


def unseen_conditions(rows):
    """Conditions of multi-condition cases no worker just misses."""
    return {
        (row["rule_id"], case["case_id"], fact)
        for row in rows
        for case in row["cases"]
        if len(case["when"]) > 1
        for fact in case["when"]
        if not just_miss_workers(row, case, fact)
    }


@pytest.mark.parametrize(
    "key", JUST_MISS_REQUIRED, ids=["-".join(k) for k in JUST_MISS_REQUIRED]
)
def test_listed_conditions_have_a_just_miss_worker(key):
    """Review r6 M-1: the exact-text oracle sees a dropped condition only
    through a worker who just misses the case on it. Each condition the
    fixture's just_miss_required lists has one, with a deciding text of its
    own where just_miss_own_text lists the condition. The list does not
    hold every condition of every case a round changed (review r7
    M-10(a)); the conditions no worker just misses are the stated limit
    test_unseen_conditions_are_a_stated_limit counts."""
    rule_id, case_id, fact = key
    rows = {r["rule_id"]: r for r in REQUIRED_CONDITION_ROWS_ALL}
    (case,) = [c for c in rows[rule_id]["cases"] if c["case_id"] == case_id]
    own_text = key in JUST_MISS_OWN_TEXT
    assert just_miss_workers(rows[rule_id], case, fact, own_text)


def test_unseen_conditions_are_a_stated_limit():
    """Review r6 M-1: the conditions no worker just misses are the PR's
    stated limit, at most UNSEEN_CONDITION_LIMIT; each of the review's
    drop-free conditions that remains among them carries its reason, and
    no required condition is among them."""
    unseen = unseen_conditions(REQUIRED_CONDITION_ROWS_ALL)
    assert len(unseen) <= UNSEEN_CONDITION_LIMIT
    assert set(JUST_MISS_STATED_LIMITS) <= unseen
    assert not unseen & set(JUST_MISS_REQUIRED)
    assert JUST_MISS_OWN_TEXT <= set(JUST_MISS_REQUIRED)
    assert all(reason.strip() for reason in JUST_MISS_STATED_LIMITS.values())


@settings(deadline=None)
@given(st.sampled_from(["other", "case_text", "absent", "stated"]))
def test_just_miss_checker_needs_an_own_text_below_the_case(kind):
    """The just-miss checker is an oracle, so its own cases are tested on
    an INVENTED row."""
    row = {
        "rule_id": "INVENTED_just_miss_row",
        "cases": [
            {
                "case_id": "invented_limited",
                "precedence": 1,
                "when": {"age": "under 18", "occupation": "INVENTED work"},
            },
            {
                "case_id": "invented_other",
                "precedence": 2,
                "when": {"age": "INVENTED other age"},
            },
        ],
    }
    texts = {
        "other": "19 years old",
        "case_text": "INVENTED other age",
        "absent": None,
        "stated": "under 18",
    }
    facts = {"occupation": "INVENTED work"}
    if texts[kind] is not None:
        facts["age"] = texts[kind]
    worker = {
        "rule_id": "INVENTED_just_miss_row",
        "facts": facts,
        "decides": "invented_other" if kind == "case_text" else "residual",
    }
    found = just_miss_workers(row, row["cases"][0], "age", True, [worker])
    loose = just_miss_workers(row, row["cases"][0], "age", workers=[worker])
    assert bool(found) == (kind == "other")
    assert bool(loose) == (kind != "stated")


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
    assert [
        entry for entry in found if not GOVERNMENT_LEVEL.search(entry[2])
    ] == []
    # Six before round 5, which adds 20: the 1991 State and local row's
    # three mandatory-rule cases, 16 election cases and the 1968
    # public-office election. The review r5 fix adds 32 federal cases and
    # the 1977 election pay case (59), then its sweep 8 more: the Army
    # Corps aide in three federal rows, the 1987 delay open case, and the
    # federal level on first_hired_after_1983 (both rows),
    # after_official_service_from_1988_11_10 and fers_or_fsps_election.
    # Review r7 low 5 drops the army-corps case from federal_1968_1972,
    # since 10 U.S.C. 2360 dates from December 1, 1981 (66).
    assert len(found) == 66


# Round 5: 410(a)(7) excludes "Service performed in the employ of a State,
# or any political subdivision thereof, or any instrumentality of any one
# or more of the foregoing which is wholly owned thereby". Its (F), whose
# (i)-(v) the 1991 row's mandatory-rule cases apply, reaches "service in
# the employ of a State (other than the District of Columbia, Guam, or
# American Samoa)", and for agreements 418(b)(1)'s "State" "does not
# include the District of Columbia, Guam, or American Samoa". So a case
# these families decide by an exclusion, a threshold or a deferral reaches
# that level of government and no other.
STATE_LOCAL_LEVEL = (
    "employee of a State (one of the 50 States, the Commonwealth of Puerto "
    "Rico or the Virgin Islands, each a State under 410(h)), of a political "
    "subdivision or of a wholly owned instrumentality, other than the "
    "District of Columbia, Guam and American Samoa"
)
STATE_LOCAL_FAMILIES = {
    "section_218_and_mandatory_state_local": (
        "state_local_1968_1983",
        "state_local_1983_1991",
        "state_local_1991_2026",
    ),
    "election_work": (
        "election_work_1968",
        "election_work_1978",
        "election_work_1991_0702",
        "election_work_1995",
    ),
}
LEVEL_LIMITED_CONSEQUENCES = {
    "noncovered",
    "covered_above_threshold",
    "deferred",
}
LEVEL_PASSAGES = (
    (
        "lii_42_410.html",
        "(7) Service performed in the employ of a State , or any political "
        "subdivision thereof, or any instrumentality of any one or more of "
        "the foregoing which is wholly owned thereby",
    ),
    (
        "lii_42_410.html",
        "(F) service in the employ of a State (other than the District of "
        "Columbia, Guam, or American Samoa)",
    ),
    (
        "lii_42_418.html",
        "does not include the District of Columbia, Guam, or American Samoa",
    ),
)
OFFICE_LEVEL_PASSAGES = (
    (
        "lii_42_411.html",
        "other than the functions of a public office of a State or a "
        "political subdivision thereof",
    ),
    (
        "lii_26_1402.html",
        "any individual who in 1968 is in a position to which the "
        "amendments made by such subsections apply",
    ),
)


def test_state_and_local_exclusions_name_the_level_their_law_reaches(
    registry,
):
    """Round 5: in the section 218 and election families, every case that
    excludes, sets a threshold or defers names the level 410(a)(7)(F) and
    418(b)(1) print, and the row's scope parameter ties it to the case. A
    covering case needs no level: a private worker is covered anyway.

    The 1968 public-office election reaches only the State or local fee
    positions 411(c)(1) names, so it carries the fee exception's level;
    the public-office exclusion reaches every office, federal included.
    """
    for capture, passage in LEVEL_PASSAGES:
        text = source_text(CAPTURE_DIRECTORY / capture)
        assert " ".join(passage.split()) in text
    limited = []
    for family, rule_ids in STATE_LOCAL_FAMILIES.items():
        rules = [r for r in registry.rules if r.family == family]
        assert sorted(r.rule_id for r in rules) == sorted(rule_ids)
        for rule in rules:
            assert "lii_42_410.html" in {c.capture for c in rule.citations}
            ties = rule.parameters["condition_cases"]["scope"]["cases"]
            for case in rule.cases:
                if case["consequence"] not in LEVEL_LIMITED_CONSEQUENCES:
                    continue
                key = (rule.rule_id, case["case_id"])
                limited.append(key)
                assert case["when"].get("government_level") == (
                    STATE_LOCAL_LEVEL
                ), key
                assert "government_level" in ties[case["case_id"]], key
                if family == "election_work":
                    # 418(c)(8) and 410(a)(7)(F)(iv) reach only election
                    # officials and election workers.
                    assert case["when"].get("election_work") == (
                        ELECTION_WORKER
                    ), key
                    assert "election_work" in ties[case["case_id"]], key
    assert len(limited) == 23
    office = next(
        r for r in registry.rules if r.rule_id == "se_public_office_1968_2026"
    )
    cases = {case["case_id"]: case for case in office.cases}
    for case_id in (
        "public_law_90_248_election",
        "state_local_fee_basis_office",
    ):
        assert cases[case_id]["when"]["government_level"] == (
            "State or political subdivision"
        )
    assert "government_level" not in cases["public_office_functions"]["when"]
    cited = {c.capture for c in office.citations}
    for capture, passage in OFFICE_LEVEL_PASSAGES:
        assert capture in cited
        text = source_text(CAPTURE_DIRECTORY / capture)
        assert " ".join(passage.split()) in text


# Round 5: INVENTED workers who hold every fact of a State or local case
# but its level. A State or local employee meets the case. A private
# firm's employee, and an employee of the District of Columbia, which
# 410(a)(7)(F) and 418(b)(1) leave out, reach the row's residual: these
# families do not exclude the service, and the other families decide (for
# the District, the territorial family, which refuses while its history is
# open).
PRIVATE_EMPLOYEE = "employee of a private firm"
DISTRICT_EMPLOYEE = "employee of the District of Columbia government"
LEVEL_EMPLOYERS = {
    "state_or_local": STATE_EMPLOYEE,
    "private": PRIVATE_EMPLOYEE,
    "district_of_columbia": DISTRICT_EMPLOYEE,
}
LOWER_AGREEMENT_AMOUNT = (
    "covered by a section 218 agreement that excludes election workers "
    "paid less than an amount the agreement states below the statutory "
    "amount"
)
MANDATORY_NOT_COVERED = (
    "not covered for OASDI by any effective agreement/modification, "
    "including a position that only a Medicare hospital insurance "
    "modification under 418(v), redesignated 418(n), reaches"
)
LOWER_AGREEMENT_AMOUNT_OASDI = (
    "covered for OASDI (old-age, survivors and disability insurance) by a "
    "section 218 agreement that excludes election workers paid less than an "
    "amount the agreement states below the statutory amount; a modification "
    "under 418(v), redesignated 418(n), that extends only Medicare hospital "
    "insurance does not count"
)
STATUTORY_AGREEMENT_AMOUNT_OASDI = (
    "covered for OASDI (old-age, survivors and disability insurance) by a "
    "section 218 agreement that excludes election workers paid less than the "
    "statutory amount; a modification under 418(v), redesignated 418(n), that "
    "extends only Medicare hospital insurance does not count"
)
STATUTORY_AGREEMENT_AMOUNT = (
    "covered by a section 218 agreement that excludes election workers "
    "paid less than the statutory amount"
)
NOT_A_MEMBER = ELECTION_NONMEMBER
CAFETERIA_AGREEMENT = (
    "covered by effective agreement/modification for OASDI (old-age, "
    "survivors and disability insurance); a modification under 418(v), "
    "redesignated 418(n), that extends only Medicare hospital insurance "
    "does not count"
)
QUALIFIED_MEMBER = ELECTION_MEMBER
# Review r5 M-2: each key's outcome for a State or local employee, as the
# sources give it, stated here rather than read from the case: 410(a)(7)(F)
# (ii) excludes the patient's work, (F)(iv) sends the poll worker and (F)(v)
# the fee position to their own families; 418(c)(8) sets the election
# amounts, and an election worker outside any agreement is excluded only
# where 410(a)(7)(F) does not cover a nonmember.
STATE_LOCAL_CASE_FACTS = {
    # A patient who works in an institution's laundry, in no retirement
    # system, whose position no agreement covers (410(a)(7)(F)(ii)).
    ("state_local_1991_2026", "mandatory_rule_exclusions"): (
        "noncovered",
        {
            "assignment": (
                "service to relieve the individual from unemployment; "
                "service in a hospital, home or other institution by a "
                "patient or inmate; or temporary service in case of fire, "
                "storm, snow, earthquake, flood or similar emergency"
            ),
            "section_218_position": MANDATORY_NOT_COVERED,
            "public_retirement_system_participation": ELECTION_NONMEMBER,
        },
    ),
    # A county road worker whose position no agreement covers, before
    # mandatory coverage (410(a)(7)).
    ("state_local_1968_1983", "no_section_218_agreement"): (
        "noncovered",
        {"section_218_position": "not covered"},
    ),
    ("state_local_1983_1991", "no_section_218_agreement"): (
        "noncovered",
        {"section_218_position": MANDATORY_NOT_COVERED},
    ),
    # A member of a qualified city system whose position no agreement
    # covers (410(a)(7)(F) reaches only nonmembers).
    ("state_local_1991_2026", "qualified_system_member_without_agreement"): (
        "noncovered",
        {
            "section_218_position": MANDATORY_NOT_COVERED,
            "public_retirement_system_participation": ELECTION_MEMBER,
        },
    ),
    # A poll worker whose position no agreement covers ((F)(iv)).
    ("state_local_1991_2026", "mandatory_rule_election_worker"): (
        "deferred",
        {
            "election_work": ELECTION_WORKER,
            "section_218_position": MANDATORY_NOT_COVERED,
        },
    ),
    # A position paid only by fees, outside any agreement ((F)(v)).
    ("state_local_1991_2026", "mandatory_rule_fee_basis_position"): (
        "deferred",
        {
            "public_office_fee_basis": (
                "position compensated solely on a fee basis, treated under "
                "411(c)(2)(E) as a trade or business"
            ),
            "section_218_position": MANDATORY_NOT_COVERED,
        },
    ),
    # Poll workers before mandatory coverage, by their agreement position.
    **{
        (rule_id, case_id): (
            consequence,
            {
                "section_218_position": position,
                "election_work": ELECTION_WORKER,
            },
        )
        for rule_id, lower, statutory, outside in (
            (
                "election_work_1968",
                LOWER_AGREEMENT_AMOUNT,
                STATUTORY_AGREEMENT_AMOUNT,
                "not covered",
            ),
            # From 1978 a Medicare-only modification does not count
            # (review r5 sweep, 418(n)).
            (
                "election_work_1978",
                LOWER_AGREEMENT_AMOUNT_OASDI,
                STATUTORY_AGREEMENT_AMOUNT_OASDI,
                MANDATORY_NOT_COVERED,
            ),
        )
        for case_id, position, consequence in (
            (
                "agreement_with_lower_threshold",
                lower,
                "covered_above_threshold",
            ),
            (
                "agreement_with_statutory_threshold",
                statutory,
                "covered_above_threshold",
            ),
            ("outside_agreement", outside, "noncovered"),
        )
    },
    # A 1977 poll worker paid in 1978 (review r5 M-1).
    (
        "election_work_1968",
        "agreement_with_statutory_threshold_paid_after_1977",
    ): (
        "covered_above_threshold",
        {
            "section_218_position": STATUTORY_AGREEMENT_AMOUNT,
            "election_work": ELECTION_WORKER,
            "remuneration_paid_date": (
                "remuneration paid on or after 1978-01-01"
            ),
        },
    ),
    # Poll workers from 1991-07-02, by agreement position and membership.
    **{
        (rule_id, case_id): (
            consequence,
            {
                "section_218_position": position,
                "election_work": ELECTION_WORKER,
                **(
                    {"public_retirement_system_participation": membership}
                    if membership
                    else {}
                ),
            },
        )
        for rule_id in ("election_work_1991_0702", "election_work_1995")
        for case_id, position, membership, consequence in (
            (
                "agreement_with_lower_threshold_nonmember",
                LOWER_AGREEMENT_AMOUNT_OASDI,
                NOT_A_MEMBER,
                "covered_above_threshold",
            ),
            (
                "agreement_with_lower_threshold_member",
                LOWER_AGREEMENT_AMOUNT_OASDI,
                QUALIFIED_MEMBER,
                "covered_above_threshold",
            ),
            (
                "agreement_with_statutory_threshold",
                STATUTORY_AGREEMENT_AMOUNT_OASDI,
                None,
                "covered_above_threshold",
            ),
            (
                "outside_agreement_nonmember",
                MANDATORY_NOT_COVERED,
                NOT_A_MEMBER,
                "covered_above_threshold",
            ),
            (
                "outside_agreement_member",
                MANDATORY_NOT_COVERED,
                QUALIFIED_MEMBER,
                "noncovered",
            ),
        )
    },
}


@pytest.mark.parametrize("employer", sorted(LEVEL_EMPLOYERS))
@pytest.mark.parametrize(
    "key",
    sorted(STATE_LOCAL_CASE_FACTS),
    ids=["-".join(key) for key in sorted(STATE_LOCAL_CASE_FACTS)],
)
def test_state_and_local_cases_reach_only_their_level(registry, key, employer):
    """Round 5: a private worker who reaches a State or local family with
    every other fact of one of its exclusions, thresholds or deferrals gets
    the row's residual, not that case (410(a)(7): "Service performed in the
    employ of a State"); a State or local employee gets the case."""
    rule_id, case_id = key
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    expected, own = STATE_LOCAL_CASE_FACTS[key]
    facts = {**own, "government_level": LEVEL_EMPLOYERS[employer]}
    decided = rule.resolve(cases_met(rule, facts))
    if employer == "state_or_local":
        assert decided.get("case_id") == case_id
        # The outcome the fixture states, not the case's own consequence
        # (review r5 M-2).
        assert decided["consequence"] == expected
    else:
        assert "case_id" not in decided
        assert decided["consequence"] == "covered"
        assert rule.residual_default["consequence"] == "covered"


# Round 5: every case the two families decide by an exclusion, a threshold
# or a deferral, and INVENTED employers outside the level they reach.
LEVEL_LIMITED_CASES = sorted(
    (row["rule_id"], case["case_id"])
    for row in json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    if row["family"] in STATE_LOCAL_FAMILIES
    for case in row["cases"]
    if case["consequence"] in LEVEL_LIMITED_CONSEQUENCES
)


def test_state_local_case_facts_list_every_level_limited_case():
    """Round 5: STATE_LOCAL_CASE_FACTS states the facts of every case the
    two families decide by an exclusion, a threshold or a deferral. (Review
    r6 M-1: the round-5 property over other employers could not fail under
    exact matching, so the employer matrix above is the level test.)"""
    assert sorted(STATE_LOCAL_CASE_FACTS) == LEVEL_LIMITED_CASES
    assert len(LEVEL_LIMITED_CASES) == 23


# Round 5: an INVENTED State or local employee whose work is not election
# work, holding every other fact of an election case.
NON_ELECTION_WORK = "a county clerk's office work, not election work"
ELECTION_CASE_KEYS = sorted(
    key for key in STATE_LOCAL_CASE_FACTS if key[0].startswith("election_")
)


@pytest.mark.parametrize(
    "key", ELECTION_CASE_KEYS, ids=["-".join(k) for k in ELECTION_CASE_KEYS]
)
def test_election_cases_reach_only_election_work(registry, key):
    """Round 5: 418(c)(8) and 410(a)(7)(F)(iv) reach service "by election
    officials or election workers". Other State or local work that reaches
    the election family takes its residual, not the election threshold or
    exclusion; the section 218 family decides that work."""
    rule_id, _ = key
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    facts = {
        **STATE_LOCAL_CASE_FACTS[key][1],
        "government_level": STATE_EMPLOYEE,
        "election_work": NON_ELECTION_WORK,
    }
    decided = rule.resolve(cases_met(rule, facts))
    assert "case_id" not in decided
    assert decided["consequence"] == "covered"


# Review r5 H-6: the conditions of every federal case that excludes or
# stays open, other than its level, as the INVENTED federal workers
# below state them. Former 410(a)(5)-(6), and 410(a)(5)-(6) from 1984,
# reach only service "in the employ of the United States".
FEDERAL_LEVEL = (
    "employee of the United States or of an instrumentality of the United "
    "States"
)
FED_DELAYED_AFTER_OFFICIAL_SYSTEM = (
    "meets Pub. L. 98-369 section 2601(d)(1)(A) and (B), did not again become "
    "subject to subchapter III (or effectively apply for it) before July 18, "
    "1984 or within the 30-day period of section 2601(d)(1) or (2), and the "
    "service is performed before the first month beginning after that 30-day "
    "period (section 2601(d)(3))"
)
# Review r6 M-2: the open delay case reads (G) service as the trigger and
# the grandfathered or annuitant service the lower cases exclude.
FED_DELAYED_AFTER_OFFICIAL_SERVICE = (
    "legislative-branch service, other than as a Member, Delegate or "
    "Resident Commissioner, that would be excluded under 410(a)(5)-(6) as in "
    "effect in January 1983, either as service performed continuously since "
    "December 31, 1983 (410(a)(5)(B)(i)(I)-(V)) or as service by an "
    "individual receiving an annuity from the Civil Service Retirement and "
    "Disability Fund or benefits under another Federal employee retirement "
    "system (410(a)(5)(B)(ii)), performed on or after a date on which the "
    "individual performed service described in 410(a)(5)(G) that was "
    "performed on or after 1988-11-10"
)
FED_ARMY_CORPS_2360_STUDENT_AIDE_SERVICE = (
    "performed by a student as an aide in a U.S. Army Corps of Engineers "
    "research and development laboratory under a 10 U.S.C. 2360 contract for "
    "seasonal or part-time student employment"
)
FED_DEFRA_SYSTEM = (
    "subject on 1983-12-31 to 5 U.S.C. chapter 83 subchapter III or another "
    "Federal employee retirement system (other than for uniformed services); "
    "after 1983 received a lump-sum payment under 5 U.S.C. 8342(a), or under "
    "the corresponding provision of the law establishing the other retirement "
    "system described in section 2601(d)(1)(A), within the dates of section "
    "2601(d)(1)(B)(i) or otherwise ceased to be subject to subchapter III as "
    "410(a)(5)(G)(iii) describes; and again became subject to (or effectively "
    "applied for) subchapter III within the period section 2601(d)(1) or (2) "
    "allows (an individual contributing a reduced amount by reason of the "
    "Federal Employees' Retirement Contribution Temporary Adjustment Act of "
    "1983 is not subject to it: Pub. L. 98-369 section 2601(c))"
)
FED_DEFRA_SERVICE = "otherwise meets 410(a)(5)(A) and (B)(i) or (B)(ii)"
FED_EXEMPT_1950_SYSTEM_SERVICE = (
    "service for an instrumentality exempt from the former IRC 1410 tax on "
    "1950-12-31 and covered by a retirement system the instrumentality "
    "established, other than service the January 1983 text of former "
    "410(a)(6)(B)(i)-(v) excepts: wholly owned United States corporations; "
    "the listed Federal banks and credit associations, Federal Reserve Banks "
    "(Federal home loan banks only from 1973) and Federal Credit Unions; "
    "Production and Marketing Administration committees; and "
    "nonappropriated-fund exchange and welfare employees of the Defense "
    "Department and the Coast Guard"
)
FED_EXEMPT_1950_SYSTEM_SERVICE_1973 = (
    "service for an instrumentality exempt from the former IRC 1410 tax on "
    "1950-12-31 and covered by a retirement system the instrumentality "
    "established, other than service the January 1983 text of former "
    "410(a)(6)(B)(i)-(v) excepts: wholly owned United States corporations; "
    "the listed Federal banks and credit associations, Federal Reserve Banks, "
    "Federal home loan banks and Federal Credit Unions; Production and "
    "Marketing Administration committees; and nonappropriated-fund exchange "
    "and welfare employees of the Defense Department and the Coast Guard"
)
FED_ANNUITANT_SYSTEM = (
    "receiving an annuity from the Civil Service Retirement and Disability "
    "Fund, or benefits for employee service under another Federal employee "
    "retirement system (other than for uniformed services)"
)
FED_ANNUITANT_SERVICE = (
    "would be excluded under 410(a)(5)-(6) as in effect in January 1983"
)
FED_HOSPITAL_STUDENT_EMPLOYEE_SERVICE = (
    "performed as an employee included under 5 U.S.C. 5351(2) (certain "
    "interns, student nurses and other student employees of Federal "
    "hospitals), other than as a medical or dental intern or a medical or "
    "dental resident in training"
)
FED_HOSPITAL_STUDENT_EMPLOYEE = (
    "employee under 5 U.S.C. 5351(2) (interns, student nurses and other "
    "student employees of Federal hospitals) other than a medical or dental "
    "intern or resident in training"
)
FED_PENAL_INMATE_SERVICE = (
    "performed in a penal institution of the United States by an inmate "
    "thereof"
)
FED_RETIREMENT_SYSTEM = (
    "covers this service, and was established by a law of the United States"
)
FED_FEPCA_SYSTEM = (
    "reemployed annuitant with an approved waiver of annuity offset under the "
    "Federal Employees Pay Comparability Act"
)
FED_GRANDFATHERED_SERVICE = (
    "would be excluded under 410(a)(5)-(6) as in effect in January 1983 and "
    "has been performed continuously since December 31, 1983, under the "
    "continuity rules of 410(a)(5)(B)(i)(I)-(V)"
)
FED_OTHER_SYSTEM_SYSTEM = (
    "not subject to the Civil Service Retirement System because subject to "
    "another retirement system, other than the Tennessee Valley Authority's"
)
FED_PRESIDENT_CONGRESS_LEGISLATIVE = (
    "President/Vice President/Congress/legislative employee"
)
FED_RETIRED_JUDGE_371B_PAYMENT = (
    "retired justice or judge performing service under 28 U.S.C. 294 "
    "(assignment to active duty), paid under 28 U.S.C. 371(b) during that "
    "service"
)
FED_STATUTORY_1410_SERVICE = (
    "instrumentality itself exempt by specific statutory reference to former "
    "IRC 1410"
)
FED_TEMPORARY_EMERGENCY_EMPLOYEE_SERVICE = (
    "performed as an employee serving on a temporary basis in case of fire, "
    "storm, earthquake, flood, or other similar emergency"
)
FED_TEMPORARY_EMERGENCY_EMPLOYEE = (
    "employee serving on a temporary basis in case of fire, storm, "
    "earthquake, flood or other similar emergency"
)
# Names the reproduction and delay tests use.
FED_EMERGENCY_TEMPORARY_1968 = FED_TEMPORARY_EMERGENCY_EMPLOYEE
FED_GRANDFATHERED_CONTINUOUS = FED_GRANDFATHERED_SERVICE
# Review r7 low 5: 10 U.S.C. 2360 dates from December 1, 1981, so
# federal_1968_1972 no longer carries the army-corps case.
FEDERAL_CASE_FACTS = {
    ("federal_1968_1972", "federal_retirement_system_service"): (
        "noncovered",
        {"federal_retirement_system": FED_RETIREMENT_SYSTEM},
    ),
    ("federal_1968_1972", "statutory_1410_instrumentality"): (
        "noncovered",
        {"federal_service": FED_STATUTORY_1410_SERVICE},
    ),
    ("federal_1968_1972", "president_congress_legislative"): (
        "noncovered",
        {"occupation": FED_PRESIDENT_CONGRESS_LEGISLATIVE},
    ),
    ("federal_1968_1972", "federal_penal_inmate"): (
        "noncovered",
        {"federal_service": FED_PENAL_INMATE_SERVICE},
    ),
    ("federal_1968_1972", "federal_hospital_student_employee"): (
        "noncovered",
        {"occupation": FED_HOSPITAL_STUDENT_EMPLOYEE},
    ),
    ("federal_1968_1972", "temporary_emergency_employee"): (
        "noncovered",
        {"occupation": FED_TEMPORARY_EMERGENCY_EMPLOYEE},
    ),
    ("federal_1968_1972", "other_federal_retirement_system"): (
        "noncovered",
        {"federal_retirement_system": FED_OTHER_SYSTEM_SYSTEM},
    ),
    ("federal_1968_1972", "exempt_1950_instrumentality_system"): (
        "noncovered",
        {"federal_service": FED_EXEMPT_1950_SYSTEM_SERVICE},
    ),
    ("federal_1973_1983", "army_corps_2360_student_aide"): (
        "noncovered",
        {"federal_service": FED_ARMY_CORPS_2360_STUDENT_AIDE_SERVICE},
    ),
    ("federal_1973_1983", "federal_retirement_system_service"): (
        "noncovered",
        {"federal_retirement_system": FED_RETIREMENT_SYSTEM},
    ),
    ("federal_1973_1983", "statutory_1410_instrumentality"): (
        "noncovered",
        {"federal_service": FED_STATUTORY_1410_SERVICE},
    ),
    ("federal_1973_1983", "exempt_1950_instrumentality_system"): (
        "noncovered",
        {"federal_service": FED_EXEMPT_1950_SYSTEM_SERVICE_1973},
    ),
    ("federal_1973_1983", "president_congress_legislative"): (
        "noncovered",
        {"occupation": FED_PRESIDENT_CONGRESS_LEGISLATIVE},
    ),
    ("federal_1973_1983", "federal_penal_inmate"): (
        "noncovered",
        {"federal_service": FED_PENAL_INMATE_SERVICE},
    ),
    ("federal_1973_1983", "federal_hospital_student_employee"): (
        "noncovered",
        {"occupation": FED_HOSPITAL_STUDENT_EMPLOYEE},
    ),
    ("federal_1973_1983", "temporary_emergency_employee"): (
        "noncovered",
        {"occupation": FED_TEMPORARY_EMERGENCY_EMPLOYEE},
    ),
    ("federal_1973_1983", "other_federal_retirement_system"): (
        "noncovered",
        {"federal_retirement_system": FED_OTHER_SYSTEM_SYSTEM},
    ),
    ("federal_1984_1986", "retired_judge_371b_payment"): (
        "noncovered",
        {"occupation": FED_RETIRED_JUDGE_371B_PAYMENT},
    ),
    ("federal_1984_1986", "federal_penal_inmate"): (
        "noncovered",
        {"federal_service": FED_PENAL_INMATE_SERVICE},
    ),
    ("federal_1984_1986", "federal_hospital_student_employee"): (
        "noncovered",
        {"federal_service": FED_HOSPITAL_STUDENT_EMPLOYEE_SERVICE},
    ),
    ("federal_1984_1986", "temporary_emergency_employee"): (
        "noncovered",
        {"federal_service": FED_TEMPORARY_EMERGENCY_EMPLOYEE_SERVICE},
    ),
    ("federal_1984_1986", "army_corps_2360_student_aide"): (
        "noncovered",
        {"federal_service": FED_ARMY_CORPS_2360_STUDENT_AIDE_SERVICE},
    ),
    ("federal_1984_1986", "defra_2601d_requalification"): (
        "noncovered",
        {
            "federal_retirement_system": FED_DEFRA_SYSTEM,
            "federal_service": FED_DEFRA_SERVICE,
        },
    ),
    ("federal_1984_1986", "grandfathered_continuous_service"): (
        "noncovered",
        {"federal_service": FED_GRANDFATHERED_SERVICE},
    ),
    ("federal_1984_1986", "federal_annuitant"): (
        "noncovered",
        {
            "federal_retirement_system": FED_ANNUITANT_SYSTEM,
            "federal_service": FED_ANNUITANT_SERVICE,
        },
    ),
    ("federal_1987_2026", "retired_judge_371b_payment"): (
        "noncovered",
        {"occupation": FED_RETIRED_JUDGE_371B_PAYMENT},
    ),
    ("federal_1987_2026", "federal_penal_inmate"): (
        "noncovered",
        {"federal_service": FED_PENAL_INMATE_SERVICE},
    ),
    ("federal_1987_2026", "federal_hospital_student_employee"): (
        "noncovered",
        {"federal_service": FED_HOSPITAL_STUDENT_EMPLOYEE_SERVICE},
    ),
    ("federal_1987_2026", "temporary_emergency_employee"): (
        "noncovered",
        {"federal_service": FED_TEMPORARY_EMERGENCY_EMPLOYEE_SERVICE},
    ),
    ("federal_1987_2026", "army_corps_2360_student_aide"): (
        "noncovered",
        {"federal_service": FED_ARMY_CORPS_2360_STUDENT_AIDE_SERVICE},
    ),
    ("federal_1987_2026", "after_official_during_2601d3_delay"): (
        "refuses",
        {
            "federal_retirement_system": FED_DELAYED_AFTER_OFFICIAL_SYSTEM,
            "federal_service": FED_DELAYED_AFTER_OFFICIAL_SERVICE,
        },
    ),
    # Review r7 low 11: the case reaches only 410(a)(5)(A) service, where
    # its readings differ.
    ("federal_1987_2026", "fepca_waiver_reemployed_annuitant"): (
        "refuses",
        {
            "federal_retirement_system": FED_FEPCA_SYSTEM,
            "federal_service": FED_ANNUITANT_SERVICE,
        },
    ),
    ("federal_1987_2026", "defra_2601d_requalification"): (
        "noncovered",
        {
            "federal_retirement_system": FED_DEFRA_SYSTEM,
            "federal_service": FED_DEFRA_SERVICE,
        },
    ),
    ("federal_1987_2026", "grandfathered_continuous_service"): (
        "noncovered",
        {"federal_service": FED_GRANDFATHERED_SERVICE},
    ),
    ("federal_1987_2026", "federal_annuitant"): (
        "noncovered",
        {
            "federal_retirement_system": FED_ANNUITANT_SYSTEM,
            "federal_service": FED_ANNUITANT_SERVICE,
        },
    ),
}
FEDERAL_ROWS = (
    "federal_1968_1972",
    "federal_1973_1983",
    "federal_1984_1986",
    "federal_1987_2026",
)
FEDERAL_LEVEL_PASSAGES = {
    "federal_1968_1972": (
        "uscode_1994_42_410.html",
        "(C) Service performed in the employ of the United States or in the "
        "employ of any instrumentality of the United States, if such service "
        "is performed",
    ),
    "federal_1973_1983": (
        "uscode_1994_42_410.html",
        "(C) Service performed in the employ of the United States or in the "
        "employ of any instrumentality of the United States, if such service "
        "is performed",
    ),
    "federal_1984_1986": (
        "lii_42_410.html",
        "(6) Service performed in the employ of the United States or any "
        "instrumentality of the United States if such service is performed",
    ),
    "federal_1987_2026": (
        "lii_42_410.html",
        "(6) Service performed in the employ of the United States or any "
        "instrumentality of the United States if such service is performed",
    ),
}


def test_federal_exclusions_name_the_level_their_law_reaches(registry):
    """Review r5 H-6: former 410(a)(5)-(6), and 410(a)(5)-(6) from 1984,
    reach only service "in the employ of the United States" or of its
    instrumentalities. So every federal case that excludes or stays open
    names that level, and the row's scope parameter ties it to the case;
    a covering case needs no level."""
    limited = []
    for rule_id in FEDERAL_ROWS:
        rule = next(r for r in registry.rules if r.rule_id == rule_id)
        capture, passage = FEDERAL_LEVEL_PASSAGES[rule_id]
        assert capture in {c.capture for c in rule.citations}
        text = source_text(CAPTURE_DIRECTORY / capture)
        assert " ".join(passage.split()) in text
        ties = rule.parameters["condition_cases"]["scope"]["cases"]
        for case in rule.cases:
            if case["consequence"] not in {"noncovered", "open"}:
                continue
            key = (rule_id, case["case_id"])
            limited.append(key)
            assert case["when"].get("government_level") == FEDERAL_LEVEL, key
            assert "government_level" in ties[case["case_id"]], key
    assert sorted(limited) == sorted(FEDERAL_CASE_FACTS)
    # Review r7 low 5: no army-corps case before 10 U.S.C. 2360 (35).
    assert len(limited) == 35


FEDERAL_SERVICE_TEXT = re.compile(
    r"United States|Federal|uniformed service|Executive Schedule|Congress"
)


def test_federal_covered_cases_name_federal_service(registry):
    """Review r6 M-1: the level guard also reaches the federal rows'
    covered cases. Each names the federal level, or a when text that is
    itself service for the United States (a uniformed service, the
    President, an Executive Schedule position, the Congress or the
    legislative branch of the Federal Government)."""
    covered = []
    for rule_id in FEDERAL_ROWS:
        rule = next(r for r in registry.rules if r.rule_id == rule_id)
        for case in rule.cases:
            if case["consequence"] in {"noncovered", "open"}:
                continue
            covered.append((rule_id, case["case_id"]))
            if case["when"].get("government_level") == FEDERAL_LEVEL:
                continue
            assert any(
                isinstance(text, str) and FEDERAL_SERVICE_TEXT.search(text)
                for text in case["when"].values()
            ), (rule_id, case["case_id"])
    assert covered


# Review r7 H-2 and low 1: the scope gap names each clause of 410(a)'s
# preamble that reaches service abroad, with (B)(ii)'s 3121(l) condition,
# and each federal residual that points to it names the same clauses.
SCOPE_GAP_CLAUSES = (
    "(A)(ii)",
    "irrespective of the citizenship or residence of either",
    '"by a citizen or resident of the United States"',
    "during any period for which there is in effect an agreement, entered "
    "into pursuant to section 3121(l)",
    '(C) "regardless of where or by whom performed"',
    "an agreement under section 433",
)


def scope_gap_problems(text):
    """The preamble clauses a scope-gap or residual text leaves out."""
    return [clause for clause in SCOPE_GAP_CLAUSES if clause not in text]


def scope_gap_texts():
    raw = json.loads(REGISTRY_ARTIFACT.read_text())
    (gap,) = raw["scope_gaps"]
    residuals = {
        row["rule_id"]: row["residual_default"]["description"]
        for row in raw["rules"]
        if "registry scope_gaps" in row["residual_default"]["description"]
    }
    return gap, residuals


def test_scope_gap_and_federal_residuals_name_the_preamble_clauses():
    gap, residuals = scope_gap_texts()
    assert "(A), (B) and (C)" in gap["provision"]
    assert scope_gap_problems(gap["gap"]) == []
    assert sorted(residuals) == sorted(FEDERAL_ROWS)
    for rule_id, text in residuals.items():
        assert scope_gap_problems(text) == [], rule_id
    cited = {c["location"] for c in gap["citations"]}
    assert {
        "410(a), preamble, clause (A)",
        "410(a), preamble, clause (B)(ii)",
        "410(a), preamble, clause (C)",
    } <= cited


@settings(deadline=None)
@given(st.sampled_from(SCOPE_GAP_CLAUSES), st.booleans())
def test_scope_gap_checker_flags_a_dropped_clause(clause, residual):
    gap, residuals = scope_gap_texts()
    text = residuals["federal_1987_2026"] if residual else gap["gap"]
    assert clause in scope_gap_problems(text.replace(clause, "INVENTED"))


FEDERAL_LEVEL_EMPLOYERS = {
    "federal": FEDERAL_LEVEL,
    "state_or_local": STATE_EMPLOYEE,
    "private": PRIVATE_EMPLOYEE,
    "district_of_columbia": DISTRICT_EMPLOYEE,
}


@pytest.mark.parametrize("employer", sorted(FEDERAL_LEVEL_EMPLOYERS))
@pytest.mark.parametrize(
    "key",
    sorted(FEDERAL_CASE_FACTS),
    ids=["-".join(key) for key in sorted(FEDERAL_CASE_FACTS)],
)
def test_federal_cases_reach_only_federal_service(registry, key, employer):
    """Review r5 H-6: a worker with every other fact of a federal exclusion
    meets it only in the employ of the United States. A State or local, a
    private or a District of Columbia employee with the same facts reaches
    the row's residual (covered), and the other families decide."""
    rule_id, case_id = key
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    expected, facts = FEDERAL_CASE_FACTS[key]
    worker = {**facts, "government_level": FEDERAL_LEVEL_EMPLOYERS[employer]}
    met = cases_met(rule, worker)
    if employer == "federal":
        assert case_id in met
        assert resolved_consequence(rule, worker) == expected
    else:
        assert resolved_consequence(rule, worker) == "covered"
        assert "case_id" not in rule.resolve(met)


# Review r5 H-6 repros (INVENTED): an Ohio legislature aide in 1975 whose
# position a 218 agreement covers, and a private flood-cleanup temp in
# 1972. Neither works for the United States.
FEDERAL_REPRO_WORKERS = {
    "ohio_legislature_aide_1975": (
        1975,
        {
            "government_level": STATE_EMPLOYEE,
            "occupation": FED_PRESIDENT_CONGRESS_LEGISLATIVE,
        },
    ),
    "private_flood_cleanup_temp_1972": (
        1972,
        {
            "government_level": PRIVATE_EMPLOYEE,
            "occupation": FED_EMERGENCY_TEMPORARY_1968,
        },
    ),
}


@pytest.mark.parametrize("worker", sorted(FEDERAL_REPRO_WORKERS))
def test_federal_rows_leave_non_federal_workers_to_other_families(
    registry, worker
):
    """Review r5 H-6: former 410(a)(6)(C) reaches only "Service performed
    in the employ of the United States"."""
    year, facts = FEDERAL_REPRO_WORKERS[worker]
    (rule,) = registry.lookup("federal_retirement_service", year)
    decided = rule.resolve(cases_met(rule, facts))
    assert decided["consequence"] == "covered"
    assert "case_id" not in decided


# Review r5 H-7: INVENTED House staffers who took a CSRS refund in May
# 1984. 2601(d)(2) reaches one "not in the employ of the United States"
# on July 18, 1984; its 30 days run from the first return to the
# legislative branch, here 1987-02-02, so (d)(3) delays (G) coverage to
# April 1987. A staffer in the Foreign Service on July 18, 1984 has only
# (d)(1)'s period, which ended in 1984.
FED_LEGISLATIVE_STAFF = (
    "service in the legislative branch of the Federal Government other than "
    "as a Member, Delegate or Resident Commissioner"
)
FED_LUMP_SUM_WITH_DELAY = (
    "received, at any time after 1983-12-31 and before the service is "
    "performed, a lump-sum payment under 5 U.S.C. 8342(a) or the "
    "corresponding provision of the other Federal retirement system; where "
    "the individual meets Pub. L. 98-369 section 2601(d)(1)(A) and (B) and "
    "did not again become subject to subchapter III (or effectively apply for "
    "it) before July 18, 1984 or within the 30-day period of section "
    "2601(d)(1) or (2), the service is performed in or after the first month "
    "beginning after that 30-day period (section 2601(d)(3))"
)
DELAYED_STAFFERS = {
    # Out of Federal employ on 1984-07-18; Commerce 1985-1986; back on
    # House staff 1987-02-02 without applying. February 1987 falls inside
    # the (d)(2) period, so the 1983 exclusion still reaches the service.
    "returned_1987_service_in_february": (
        {
            "government_level": FEDERAL_LEVEL,
            "federal_service": (
                FED_LEGISLATIVE_STAFF,
                FED_GRANDFATHERED_CONTINUOUS,
            ),
            "federal_retirement_system": (
                "received a lump-sum payment after 1983 and is within the "
                "section 2601(d)(3) delay"
            ),
        },
        "noncovered",
        "grandfathered_continuous_service",
    ),
    # The same staffer's April 1987 service.
    "returned_1987_service_in_april": (
        {
            "government_level": FEDERAL_LEVEL,
            "federal_service": (
                FED_LEGISLATIVE_STAFF,
                FED_GRANDFATHERED_CONTINUOUS,
            ),
            "federal_retirement_system": FED_LUMP_SUM_WITH_DELAY,
        },
        "covered",
        "legislative_lump_sum_after_1983",
    ),
    # The review's staffer, in the Foreign Service on 1984-07-18, back on
    # House staff 1987-02-02: (d)(2) does not reach him, and the (d)(1)
    # delay ended in September 1984, so February 1987 is covered.
    "foreign_service_on_enactment_date": (
        {
            "government_level": FEDERAL_LEVEL,
            "federal_service": (
                FED_LEGISLATIVE_STAFF,
                FED_GRANDFATHERED_CONTINUOUS,
            ),
            "federal_retirement_system": FED_LUMP_SUM_WITH_DELAY,
        },
        "covered",
        "legislative_lump_sum_after_1983",
    ),
}


@pytest.mark.parametrize("staffer", sorted(DELAYED_STAFFERS))
def test_section_2601d3_delay_reaches_service_after_1986(registry, staffer):
    """Review r5 H-7: 2601(d)(3) makes (G) coverage "effective with the
    first month beginning after such 30-day period", and (d)(2)'s period
    can fall in any later year."""
    facts, expected, decides = DELAYED_STAFFERS[staffer]
    (rule,) = registry.lookup_date(
        "federal_retirement_service", date(1987, 2, 9)
    )
    decided = rule.resolve(cases_met(rule, facts))
    assert decided["consequence"] == expected
    assert decided.get("case_id", "residual") == decides


# Review r5 M-1: no code reads axis_exception, so the rows a fiscal year
# that began in 1983 reaches carry the 1984 church cases with the service
# date. INVENTED: a church secretary paid $80 by an electing church for
# January 1984 service, in a fiscal year that began 1983-07-01.
ELECTING_CHURCH_SERVICE = (
    "service for a church or qualified church-controlled organization that "
    "has in effect for the service an election under section 3121(w): made "
    "within the time 3121(w)(2) allows, and not revoked for a period that "
    "includes the service (a revocation by the Secretary for failure to "
    "furnish the section 6051 information applies retroactively to the "
    "beginning of the 2-year period for which it was not furnished); outside "
    "an unrelated trade or business, and outside ministry or order duties"
)
# Review r7 M-5: the review's $80 comes from an employer paying less
# than $100, which former 411(a)(13)(C) keeps out of self-employment
# income, so it meets the units row's church_employer_below_100 text.
CHURCH_REMUNERATION_BELOW_GATE = (
    "remuneration for service performed on or after 1984-01-01 in the "
    "employ of an electing church or qualified church-controlled "
    "organization, other than service in an unrelated trade or business "
    "(section 513(a)), and other than service by a minister in the exercise "
    "of ministry or by a member of a religious order in the exercise of "
    "duties the order requires (410(a)(8)(A) service; for 1984-1985 the "
    "1984 Schedule SE and 1985 Form 1040 instructions send a minister or a "
    "member of a religious order elsewhere), from an employer paying less "
    "than $100 of such remuneration (for service on or after 1984-01-01) in "
    "the taxable year"
)


@pytest.mark.parametrize(
    ("service_date", "expected", "decides"),
    [
        (
            "on or after 1984-01-01",
            "covered_above_threshold",
            "electing_church_nonministerial_service",
        ),
        ("before 1984-01-01", "deferred", "residual"),
    ],
)
def test_fiscal_year_church_service_after_1983_takes_the_1984_cases(
    registry, service_date, expected, decides
):
    """Review r5 M-1: Pub. L. 98-369 section 2603(e) applies the church
    election to "service performed after December 31, 1983"; a fiscal
    year that began in 1983 reaches the 1968-1983 row, whose cases carry
    that date. Below the $100 employer gate the pay is excluded, so the
    review's $80 is noncovered; earlier service defers to nonprofit. In
    the units row the $80 meets church_employer_below_100: former
    411(a)(13)(C) says such pay "shall not be included in self-employment
    income" (review r7 M-5; round 6's low 3 sent it to the residual's $400
    floor, and round 5 to church_combined_below_100). Service before 1984
    meets no church case, so the residual applies."""
    (rule,) = registry.lookup_date(
        "electing_church_employee_service", date(1983, 7, 1)
    )
    facts = {
        "church_employee_service": ELECTING_CHURCH_SERVICE,
        "services_performed_date": service_date,
    }
    decided = rule.resolve(cases_met(rule, facts))
    assert decided["consequence"] == expected
    assert decided.get("case_id", "residual") == decides
    if expected == "covered_above_threshold":
        gate = rule.parameters["church_se_threshold_cents"]
        assert 8000 < gate == 10000
    (units,) = registry.lookup_date("self_employment_units", date(1983, 7, 1))
    unit_facts = {
        "church_employee_service": CHURCH_REMUNERATION_BELOW_GATE,
        "services_performed_date": service_date,
        "amount": "combined earnings below $100",
    }
    decided = units.resolve(cases_met(units, unit_facts))
    if service_date == "on or after 1984-01-01":
        assert decided["case_id"] == "church_employer_below_100"
        assert decided["consequence"] == "noncovered"
    else:
        assert "case_id" not in decided
        assert decided["consequence"] == "covered_above_threshold"


@pytest.mark.parametrize(
    ("paid", "decides", "threshold_id"),
    [
        (
            "remuneration paid on or after 1978-01-01",
            "agreement_with_statutory_threshold_paid_after_1977",
            "election_remuneration_annual",
        ),
        (
            "remuneration paid before 1978-01-01",
            "agreement_with_statutory_threshold",
            "election_remuneration_quarterly",
        ),
    ],
)
def test_1977_election_pay_follows_its_payment_date(
    registry, paid, decides, threshold_id
):
    """Review r5 M-1 check of every off-axis pin: the 1977 amendment
    applies "with respect to remuneration paid after December 31, 1977",
    on a service-date family. INVENTED: a poll worker's November 1977
    service under an agreement with the statutory exclusion."""
    (rule,) = registry.lookup_date("election_work", date(1977, 11, 8))
    facts = {
        "section_218_position": STATUTORY_AGREEMENT_AMOUNT,
        "government_level": STATE_EMPLOYEE,
        "election_work": ELECTION_WORKER,
        "remuneration_paid_date": paid,
    }
    decided = rule.resolve(cases_met(rule, facts))
    assert decided.get("case_id") == decides
    assert decided["consequence"] == "covered_above_threshold"
    by_case = rule.parameters.get("threshold_id_by_case", {})
    entry = by_case.get(decides)
    named = (
        rule.parameters["threshold_id"]
        if entry is None
        else (entry["threshold_id"])
    )
    assert named == threshold_id
    assert registry.threshold(threshold_id, 1978 if entry else 1977)


def test_case_thresholds_are_available_for_their_years(registry):
    """Review r6 M-6: each threshold_id_by_case entry names a case of its
    row and a threshold the registry gives for every year the entry
    lists (the loader refuses any other). Casual 1978's case read the
    service date, which the family's service axis never sends to that row,
    and named a threshold unpublished for 1978; both casual rows now read
    the payment date."""
    entries = {
        (rule.rule_id, case_id): entry
        for rule in registry.rules
        for case_id, entry in rule.parameters.get(
            "threshold_id_by_case", {}
        ).items()
    }
    assert sorted(entries) == [
        ("casual_service_1968", "remuneration_paid_after_1977"),
        ("casual_service_1978", "remuneration_paid_before_1978"),
        (
            "election_work_1968",
            "agreement_with_statutory_threshold_paid_after_1977",
        ),
    ]
    for (rule_id, case_id), entry in entries.items():
        rule = next(r for r in registry.rules if r.rule_id == rule_id)
        (case,) = [c for c in rule.cases if c["case_id"] == case_id]
        assert "remuneration_paid_date" in case["when"]
        first, last = entry["income_years"]
        for year in range(first, last + 1):
            assert registry.threshold(entry["threshold_id"], year) > 0


PUBLIC_OFFICE_ELECTION = (
    "Timely irrevocable election under Public Law 90-248 section 122(c)(2), "
    "made by an individual in an affected position in 1968, applies to "
    "these fees."
)
PUBLIC_OFFICE_ELECTION_HOLDERS = {
    # INVENTED: a county recorder paid only by fees, outside any
    # agreement, who made the 1968 election.
    "county_fee_officer": (
        {
            "public_office_1968_exemption_election": PUBLIC_OFFICE_ELECTION,
            "government_level": "State or political subdivision",
            "public_office_functions": (
                "income is for performing the functions of a public office"
            ),
            "public_office_fee_basis": (
                "position compensated solely on a fee basis"
            ),
        },
        "noncovered",
        "public_law_90_248_election",
    ),
    # INVENTED: a federal officer paid by fees whose facts state the same
    # election. Section 122(c)(2) does not reach the post; 411(c)(1)
    # excludes its functions.
    "federal_fee_officer": (
        {
            "public_office_1968_exemption_election": PUBLIC_OFFICE_ELECTION,
            "government_level": "federal",
            "public_office_functions": (
                "income is for performing the functions of a public office"
            ),
            "public_office_fee_basis": (
                "position compensated solely on a fee basis"
            ),
        },
        "noncovered",
        "public_office_functions",
    ),
    # INVENTED: a private firm's agent whose facts state the election.
    "private_agent": (
        {
            "public_office_1968_exemption_election": PUBLIC_OFFICE_ELECTION,
            "government_level": "private firm",
        },
        "covered",
        "residual",
    ),
}


@pytest.mark.parametrize("holder", sorted(PUBLIC_OFFICE_ELECTION_HOLDERS))
def test_public_office_1968_election_reaches_only_state_or_local_fees(
    registry, holder
):
    """Round 5: Pub. L. 90-248 section 122(c)(2) lets only "any individual
    who in 1968 is in a position to which the amendments made by such
    subsections apply" elect, and those amendments reach a public office of
    a State or a political subdivision (411(c)(1))."""
    rule = next(
        r for r in registry.rules if r.rule_id == "se_public_office_1968_2026"
    )
    facts, consequence, via = PUBLIC_OFFICE_ELECTION_HOLDERS[holder]
    decided = rule.resolve(cases_met(rule, facts))
    assert decided["consequence"] == consequence
    assert decided.get("case_id", "residual") == via


# Round 5 (review r4 low 10): 411(j) is headed "Codification of treatment
# of certain termination payments received by former insurance salesmen"
# and says what subsection (a) "shall be construed as including"; the 411
# notes date it "applicable to payments after Dec. 31, 1997". INVENTED
# former agents' termination payments, by the date paid and their terms.
TERMINATION_HEADING = (
    "Codification of treatment of certain termination payments received by "
    "former insurance salesmen"
)
TERMINATION_EFFECTIVE = "applicable to payments after Dec. 31, 1997"
QUALIFYING_TERMINATION_TERMS = (
    "received from an insurance company on account of services the individual "
    "performed as an insurance salesman for that company, after the "
    "individual's agreement to perform those services for the company ends; "
    "no services for the company after that termination and before the close "
    "of the taxable year; a covenant not to compete against the company that "
    "applies to at least the 1-year period beginning on the date of "
    "termination; and an amount that depends primarily on policies sold by or "
    "credited to the individual's account during the agreement's last year, "
    "or on how long those policies remain in force after termination, or "
    "both, and does not depend to any extent on length of service or overall "
    "earnings from services for the company (whether or not eligibility for "
    "the payment depends on length of service)"
)
SERVICE_LENGTH_TERMS = "an amount that grows with length of service"
TERMINATION_PAYMENTS = {
    "qualifying_paid_1995": (
        date(1995, 6, 1),
        QUALIFYING_TERMINATION_TERMS,
        "refuses",
        "qualifying_termination_payment_before_1998",
    ),
    "qualifying_paid_1999": (
        date(1999, 6, 1),
        QUALIFYING_TERMINATION_TERMS,
        "noncovered",
        "qualifying_termination_payment",
    ),
    "service_length_paid_1995": (
        date(1995, 6, 1),
        SERVICE_LENGTH_TERMS,
        "covered",
        "residual",
    ),
    # Review r5 M-2 (A4 2h): a payment received while the agreement still
    # runs fails 411(j)(1) and reaches the residual.
    "paid_before_agreement_ends_1999": (
        date(1999, 6, 1),
        "received before the agreement ends; otherwise as 411(j)(2)-(4) "
        "describe",
        "deferred",
        "residual",
    ),
    "service_length_paid_1999": (
        date(1999, 6, 1),
        SERVICE_LENGTH_TERMS,
        "deferred",
        "residual",
    ),
}


@pytest.mark.parametrize("payment", sorted(TERMINATION_PAYMENTS))
def test_termination_payments_before_1998_keep_the_codification_open(
    registry, payment
):
    """Review r4 low 10: the heading and construction wording present
    411(j) as stating how 411(a) already treated a qualifying payment,
    while its effective date reaches only payments after 1997. No CE1
    capture records the earlier treatment, so a qualifying payment before
    1998 refuses with both readings named; other payments resolve."""
    paid, terms, consequence, via = TERMINATION_PAYMENTS[payment]
    (rule,) = registry.lookup_date(
        "self_employment_insurance_termination", paid
    )
    met = cases_met(rule, {"insurance_sales_termination_payment": terms})
    if consequence != "refuses":
        decided = rule.resolve(met)
        assert decided["consequence"] == consequence
        assert decided.get("case_id", "residual") == via
        return
    with pytest.raises(OpenRuleError, match="INSURANCE_TERMINATION_PRE_1998"):
        rule.resolve(met)
    case = next(c for c in rule.cases if c["case_id"] == via)
    names = {option["name"] for option in case["open_alternatives"]}
    assert names == {"effective_date_reading", "codification_reading"}
    text = source_text(CAPTURE_DIRECTORY / "lii_42_411.html")
    for passage in (TERMINATION_HEADING, TERMINATION_EFFECTIVE):
        assert passage in text
        assert passage in case["open_reason"]
    later = next(
        r
        for r in registry.rules
        if r.rule_id == "se_insurance_termination_1998_2026"
    )
    assert case["when"] == later.cases[0]["when"]


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
    ("day", "rule_id", "with_931"),
    [
        (date(1973, 1, 1), "se_clergy_gross_concept_1973_1987", True),
        (date(1987, 12, 21), "se_clergy_gross_concept_1973_1987", True),
        (date(1987, 12, 22), "se_clergy_gross_concept_1987_2026", False),
        (date(2025, 1, 1), "se_clergy_gross_concept_1987_2026", False),
    ],
)
def test_clergy_gross_concept_disregards_931_until_1987(
    registry, day, rule_id, with_931
):
    """Review r3 M6: the 1972 amendment put sections 911 and 931 in
    411(a)(7); Pub. L. 100-203 section 9023(b)(1) struck "and section 931"
    from it, and (a)(8) as amended disregards 931 for everyone."""
    (rule,) = registry.lookup_date("self_employment_clergy_gross_concept", day)
    assert rule.rule_id == rule_id
    disregarded = rule.parameters["gross_income_exclusions_disregarded"]
    assert ("26USC931" in disregarded) == with_931
    assert {"26USC107", "26USC119", "26USC911"} <= set(disregarded)
    assert any(
        c.quote and "struck out reference to section 931" in c.quote
        for c in rule.citations
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
    # Review r3 low 7: every outcome a case decides goes through resolve,
    # with every case whose conditions the example's facts meet.
    if kind == "domestic_threshold":
        annual = facts.pop("weekly_cash_wages") * facts.pop("weeks")
        over_18 = facts.pop("employee_over_18")
        unrelated = facts.pop("employee_unrelated")
        eligible = over_18 and unrelated
        threshold = registry.threshold(params["threshold_id"], year)
        minor = set() if over_18 else {"minor_not_principal_occupation"}
        decided = rule.resolve(minor)["consequence"]
        result = {
            "annual_cash_wages_dollars": annual,
            "social_security_coverage": (
                "covered"
                if eligible
                and annual >= threshold
                and decided == "covered_above_threshold"
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
            matched = set()
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
            matched = set() if over_18 else {"minor_not_principal_occupation"}
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
                and rule.resolve(matched)["consequence"]
                == "covered_above_threshold"
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
                if "any medium other than cash"
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
        matched = {
            c["case_id"]
            for c in rule.cases
            if c["when"]
            .get("family_service", "")
            .startswith("parent employed by child in")
        }
        assert matched
        decided = rule.resolve(matched)["consequence"]
        result = {"social_security_coverage": decided}
    elif kind == "order_service":
        required = facts.pop("required_order_duties")
        vow = facts.pop("vow_of_poverty")
        if required and vow:
            # The example states no order election.
            assert params["poverty_vow_self_employment_excluded"]
            decided = rule.resolve({"vow_duties_without_election"})
            result = {"self_employment_coverage": decided["consequence"]}
        else:
            matched = {
                c["case_id"]
                for c in rule.cases
                if c["when"]
                .get("religious_order_service", "")
                .startswith("ordinary employment for a third party")
            }
            consequence = rule.resolve(matched)["consequence"]
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
        matched = {
            c["case_id"]
            for c in rule.cases
            if c["when"].get("clergy_or_religious_exemption") == condition
        }
        assert len(matched) == 1
        result = {
            "social_security_coverage": rule.resolve(matched)["consequence"]
        }
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
        # Review r6 M-1: the worker states the texts the cases read, so
        # the example decides through a case, not the residual.
        worker = {
            "government_level": STATE_EMPLOYEE,
            "public_retirement_system_participation": (
                QUALIFIED_MEMBER if member else NOT_A_MEMBER
            ),
            "section_218_position": (
                CAFETERIA_AGREEMENT if agreement else MANDATORY_NOT_COVERED
            ),
        }
        matched = cases_met(rule, worker)
        assert matched
        decided = rule.resolve(matched)["consequence"]
        result = {"social_security_coverage": decided}
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
        matched = {
            c["case_id"]
            for c in rule.cases
            if c["when"].get("material_participation") is participation
        }
        decided = rule.resolve(matched)["consequence"]
        result = {
            "rental_income_included_in_nese": {
                "covered": True,
                "noncovered": False,
            }[decided]
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


COMMUNITY_SPOUSES = {
    # INVENTED spouses' records, by the cases whose conditions hold.
    "partner_on_own_share": (set(), "covered"),
    "spouse_of_partner": (
        {"partnership_share_of_spouse_partner"},
        "noncovered",
    ),
    "spouse_the_income_belongs_to": (set(), "covered"),
}


@pytest.mark.parametrize("spouse", sorted(COMMUNITY_SPOUSES))
@pytest.mark.parametrize(
    ("day", "other_spouse"),
    [
        (date(1975, 6, 1), "business_income_treated_as_other_spouses"),
        (date(2010, 6, 1), "business_income_of_other_spouse"),
    ],
)
def test_community_income_excludes_the_other_spouses_share(
    registry, day, other_spouse, spouse
):
    """Review r3 M2: 411(a)(5)(B) says "no part of such share shall be
    taken into account in computing the net earnings from self-employment
    of the spouse"; (a)(5)(A) assigns business income to one spouse (or by
    shares), so the other spouse's record excludes it."""
    (rule,) = registry.lookup_date("self_employment_community_income", day)
    matched, expected = COMMUNITY_SPOUSES[spouse]
    assert rule.resolve(matched)["consequence"] == expected
    assert rule.resolve({other_spouse})["consequence"] == "noncovered"
    assert "case_free_basis" not in rule.parameters


def test_units_1984_1985_base_cases_are_schema_cases(registry):
    """Review r3 M2: the five base cases left parameters for the schema."""
    (rule,) = registry.lookup("self_employment_units", 1985)
    assert "coverage_base_cases" not in rule.parameters
    bases = rule.parameters["eligible_base_by_case"]
    assert set(bases) == {c["case_id"] for c in rule.cases} | {
        "residual_default"
    }
    below = rule.resolve({"church_combined_below_100"})
    assert below["consequence"] == "noncovered"
    assert rule.resolve(())["consequence"] == "covered_above_threshold"


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
