"""Source-only codebook extraction over the registered documents."""

from __future__ import annotations

import collections
import hashlib
import shutil
import subprocess
from fractions import Fraction

import pytest

from populace_dynamics.data import psid_codebook_extraction as codebook
from populace_dynamics.data.psid_source_classifier import _normalize_entries
from populace_dynamics.data.psid_source_compiler import (
    DEFAULT_PSID_ROOT,
    load_authenticated_evidence,
)

pytestmark = pytest.mark.skipif(
    not DEFAULT_PSID_ROOT.exists() or shutil.which("pdftotext") is None,
    reason="registered PSID corpus or Poppler pdftotext is unavailable",
)

# The V93 locator pinned by the committed 1968 evidence artifact.
V93_PAGE = 23
V93_PAGE_TEXT_SHA256 = (
    "22ea3467d32c12e76e2c73f2af20efbc050e2f1f130141d7dec697318ae847d4"
)


def _fraction(value):
    if isinstance(value, int):
        return Fraction(value)
    return Fraction(value["numerator"], value["denominator"])


@pytest.fixture(scope="module")
def corpus():
    return load_authenticated_evidence()


@pytest.fixture(scope="module")
def codebook_documents(corpus):
    return {
        row["canonical_source_path"]: row
        for row in corpus.source_manifest
        if row["document_role"] == "codebook"
    }


@pytest.fixture(scope="module")
def wave_1968(codebook_documents):
    document = codebook_documents["family/1968/fam1968_codebook.pdf"]
    return codebook.extract_codebook_rows(document)


def test_registered_codebook_documents_are_exactly_47(codebook_documents):
    """43 family codebook PDFs plus the four 2021/2023 value-label files."""

    assert len(codebook_documents) == 47
    families = collections.Counter(
        path.rsplit(".", 1)[1] for path in codebook_documents
    )
    assert families == {"pdf": 43, "do": 2, "sps": 2}


def test_pinned_poppler_version_is_the_registered_derivation():
    assert codebook.pdftotext_version() == codebook.PDFTOTEXT_VERSION


def test_pinned_page_text_reproduces_the_evidence_digest():
    path = DEFAULT_PSID_ROOT / "family/1968/fam1968_codebook.pdf"
    pages = codebook.pinned_pdf_page_text(path)
    assert len(pages) == 148
    digest = hashlib.sha256(pages[V93_PAGE - 1].encode("utf-8")).hexdigest()
    assert digest == V93_PAGE_TEXT_SHA256


def test_page_text_uses_only_the_registered_argument_array(monkeypatch):
    captured = {}
    real = subprocess.run

    def spy(command, **kwargs):
        captured["command"] = command
        return real(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    codebook.pinned_pdf_page_text(
        DEFAULT_PSID_ROOT / "family/1968/fam1968_codebook.pdf"
    )
    assert captured["command"][0] == "pdftotext"
    assert tuple(captured["command"][1:4]) == codebook.PDFTOTEXT_ARGUMENTS
    assert captured["command"][-1] == "-"


def test_v93_regression_vector(wave_1968):
    codebook.validate_document_derivation(wave_1968)
    assert wave_1968["derivation_kind"] == "codebook_rows"
    assert wave_1968["row_segmentation"]["parser_family"] == (
        codebook.PDF_PARSER_FAMILY
    )
    assert wave_1968["decoder"] == {
        "decoder_kind": "pinned_pdf_page_text_derivation",
        "encoding": "UTF-8",
        "error_action": "abort",
        "bom_action": "forbidden",
        "newline_action": "preserve_pinned_page_strings",
    }
    rows = {row["raw_field_id"]: row for row in wave_1968["canonical_rows"]}
    assert len(rows) == 447
    v93 = rows["V93"]
    assert v93["source_label"] == "STATE (68)"
    assert v93["source_format_text"] == "NUM(2.0)"
    assert v93["source_description"].startswith("State where lives now\n")
    entries = v93["normalized_entries"]
    assert [entry["source_value_lexeme"] for entry in entries] == [
        "0",
        "1 - 51",
        "99",
    ]
    assert [entry["entry_kind"] for entry in entries] == [
        "literal",
        "numeric_range",
        "literal",
    ]
    assert [entry["typed_disposition"] for entry in entries] == [
        "missing",
        "json_integer",
        "missing",
    ]
    assert entries[1]["inclusive_min"] == 1
    assert entries[1]["inclusive_max"] == 51
    assert entries[1]["step"] == 1
    assert entries[1]["source_meaning"] == "Actual state (PSID state code)"
    row_id = v93["codebook_field_row_id"]
    assert [entry["entry_ref"] for entry in entries] == [
        f"{row_id}:entry:0",
        f"{row_id}:entry:1",
        f"{row_id}:entry:2",
    ]


def test_v93_locator_binds_the_pinned_page(wave_1968):
    locators = {
        row["source_region_locator_id"]: row
        for row in wave_1968["row_segmentation"]["source_region_locators"]
    }
    rows = {row["raw_field_id"]: row for row in wave_1968["canonical_rows"]}
    pages = {
        locators[value]["page_number"]
        for value in rows["V93"]["source_locator_ids"]
    }
    assert pages == {V93_PAGE}
    for locator in locators.values():
        assert locator["locator_kind"] == "pdf_page_text_range"
        assert locator["byte_start"] is None and locator["byte_end"] is None
        assert 0 <= locator["utf8_start"] < locator["utf8_end"]


def test_wrapped_value_cell_retains_the_upper_bound_sign(codebook_documents):
    document = codebook_documents["family/1993/fam1993_codebook.pdf"]
    derivation = codebook.extract_codebook_rows(document)
    rows = {row["raw_field_id"]: row for row in derivation["canonical_rows"]}
    entry = rows["V22506"]["normalized_entries"][0]
    assert entry["entry_kind"] == "numeric_range"
    assert entry["source_value_lexeme"] == "-99,997.99 - -.01"
    assert entry["inclusive_min"] == {
        "numerator": -9999799,
        "denominator": 100,
    }
    assert entry["inclusive_max"] == {"numerator": -1, "denominator": 100}
    assert entry["step"] == {"numerator": 1, "denominator": 100}
    assert entry["source_meaning"] == "Actual amount of loss"


def test_bracket_label_is_not_a_one_member_range(codebook_documents):
    document = codebook_documents["family/1969/FAM1969_codebook.pdf"]
    derivation = codebook.extract_codebook_rows(document)
    rows = {row["raw_field_id"]: row for row in derivation["canonical_rows"]}
    entries = rows["V922"]["normalized_entries"]
    # Every row is a bracket label whose meaning opens in the value column;
    # `4 - 4 to + 4%` must not become a one-member range.
    assert [entry["entry_kind"] for entry in entries] == ["literal"] * 9
    assert entries[3]["source_value_lexeme"] == "4"
    assert entries[3]["source_meaning"] == "- 4 to + 4%"
    assert entries[0]["source_meaning"] == "-100 to -30%"


@pytest.mark.parametrize("wave", [1968, 1969, 1993, 2021])
def test_entries_reproduce_the_classifier_domain(
    corpus, codebook_documents, wave
):
    document = next(
        row
        for path, row in codebook_documents.items()
        if path.endswith(".pdf") and row["interview_waves"] == [wave]
    )
    derivation = codebook.extract_codebook_rows(document)
    fields = {
        field.raw_field_id: field
        for field in corpus.fields
        if field.interview_wave == wave
    }
    assert len(fields) == derivation["canonical_row_count"]
    for row in derivation["canonical_rows"]:
        literals, ranges = _normalize_entries(fields[row["raw_field_id"]])
        entries = row["normalized_entries"]
        assert [
            entry["source_value_lexeme"]
            for entry in entries
            if entry["entry_kind"] == "literal"
        ] == [item.lexeme for item in literals]
        # A wrapped value cell makes the retained lexeme differ from the
        # evidence's split, so ranges are compared on their exact bounds.
        assert [
            (
                _fraction(entry["inclusive_min"]),
                _fraction(entry["inclusive_max"]),
                _fraction(entry["step"]),
            )
            for entry in entries
            if entry["entry_kind"] == "numeric_range"
        ] == [(item.minimum, item.maximum, item.step) for item in ranges]
        derived_missing = {
            index
            for index, entry in enumerate(entries)
            if entry["typed_disposition"] == "missing"
        }
        literal_positions = {
            index
            for index, entry in enumerate(entries)
            if entry["entry_kind"] == "literal"
        }
        expected = (
            set(fields[row["raw_field_id"]].missing_code_map_indices)
            & literal_positions
        )
        assert derived_missing == expected


def test_value_label_documents_agree_across_both_languages(
    codebook_documents,
):
    """Stata compresses value labels into loops; SPSS enumerates them."""

    stata = codebook.extract_codebook_rows(
        codebook_documents["family/2021/FAM2021ER_formats.do"]
    )
    spss = codebook.extract_codebook_rows(
        codebook_documents["family/2021/FAM2021ER_formats.sps"]
    )
    codebook.validate_document_derivation(stata)
    codebook.validate_document_derivation(spss)
    assert stata["row_segmentation"]["parser_family"] == (
        codebook.STATA_PARSER_FAMILY
    )
    assert spss["row_segmentation"]["parser_family"] == (
        codebook.SPSS_PARSER_FAMILY
    )
    assert stata["canonical_row_count"] == spss["canonical_row_count"] == 3212

    def expand(derivation):
        """Key each value domain by scalar, so a loop expands to members."""

        domains = {}
        for row in derivation["canonical_rows"]:
            values = {}
            for entry in row["normalized_entries"]:
                if entry["entry_kind"] == "literal":
                    scalar = codebook.parse_source_scalar(
                        entry["source_value_lexeme"]
                    )
                    values[scalar] = entry["source_meaning"]
                    continue
                for value in range(
                    entry["inclusive_min"], entry["inclusive_max"] + 1
                ):
                    values[Fraction(value)] = entry["source_meaning"]
            domains[row["raw_field_id"]] = values
        return domains

    left, right = expand(stata), expand(spss)
    assert set(left) == set(right)
    # Every meaning agrees outright or under exactly three source-encoding
    # differences: Stata writes the apostrophe through its `=char(146)'
    # escape, whose windows-1252 expansion is U+2019, where SPSS and the
    # codebook page both carry U+0027; the SPSS writer truncates a long
    # label at the source cap; and two SPSS labels carry an outer space.
    tally = {"equal": 0, "quote_macro": 0, "outer_space": 0, "truncated": 0}
    for field, values in left.items():
        assert set(values) == set(right[field]), field
        for value, meaning in values.items():
            other = right[field][value]
            if meaning == other:
                tally["equal"] += 1
                continue
            folded = meaning.replace("’", "'")
            if folded == other:
                tally["quote_macro"] += 1
            elif folded.strip() == other.strip():
                tally["outer_space"] += 1
            else:
                assert other.endswith("..."), (field, value, meaning, other)
                assert folded.strip().startswith(other[:-3].strip())
                tally["truncated"] += 1
    assert tally == {
        "equal": 22653,
        "quote_macro": 84,
        "outer_space": 2,
        "truncated": 2524,
    }
    assert sum(tally.values()) == 25263


def test_stata_loops_compress_into_numeric_ranges(codebook_documents):
    stata = codebook.extract_codebook_rows(
        codebook_documents["family/2021/FAM2021ER_formats.do"]
    )
    rows = {row["raw_field_id"]: row for row in stata["canonical_rows"]}
    entries = rows["ER78003"]["normalized_entries"]
    kinds = [entry["entry_kind"] for entry in entries]
    assert kinds.count("numeric_range") == 1
    span = entries[kinds.index("numeric_range")]
    assert span["source_value_lexeme"] == "1 - 51"
    assert span["inclusive_min"] == 1
    assert span["inclusive_max"] == 51
    assert span["source_meaning"] == "Actual state (PSID State code)"


def test_undetermined_members_are_null_and_declared(wave_1968):
    assert codebook.undetermined_entry_members() == (
        "typed_value_unit",
        "missing_reason_code",
    )
    for row in wave_1968["canonical_rows"]:
        for entry in row["normalized_entries"]:
            for member in codebook.undetermined_entry_members():
                assert entry[member] is None


def test_a_non_codebook_document_is_refused(corpus):
    document = next(
        row
        for row in corpus.source_manifest
        if row["document_role"] == "dictionary_layout"
    )
    with pytest.raises(codebook.CodebookExtractionError):
        codebook.extract_codebook_rows(document)


def test_missing_meaning_classification_is_source_lexical():
    assert codebook.is_missing_source_meaning("DK; NA")
    assert codebook.is_missing_source_meaning("Inap.: no income from labor")
    assert codebook.is_missing_source_meaning("Wild code")
    assert codebook.is_missing_source_meaning("Not ascertained")
    assert not codebook.is_missing_source_meaning("Actual amount")
    assert not codebook.is_missing_source_meaning(
        "Yes; or not ascertained whether the spouse also worked"
    )
