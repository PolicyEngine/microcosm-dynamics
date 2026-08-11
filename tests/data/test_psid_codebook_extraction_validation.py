"""Exact-schema tests for source-only codebook derivations."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path

import pytest

from populace_dynamics.data import psid_codebook_extraction as extraction

DOCUMENT_ID = "psid-source-document:" + "a" * 64
SOURCE_BYTES = b"VALUE LABELS\nV1\n 0 'Zero'\n.\n"


def _source_document(relative_path: str, raw: bytes = SOURCE_BYTES):
    return {
        "source_document_id": DOCUMENT_ID,
        "document_role": "codebook",
        "canonical_source_path": relative_path,
        "byte_size": len(raw),
        "sha256": extraction.sha256_bytes(raw),
    }


def _write_source(root: Path, relative_path: str, raw: bytes = SOURCE_BYTES):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def _text_derivation():
    raw = b"first statement\nsecond statement\n"
    locators = [
        extraction._raw_locator(DOCUMENT_ID, raw, 0, 15),
        extraction._raw_locator(DOCUMENT_ID, raw, 16, 32),
    ]
    rows = [
        extraction._canonical_row(
            DOCUMENT_ID,
            0,
            "V1",
            "First field",
            (),
            None,
            (("0", "Zero"),),
            (locators[0]["source_region_locator_id"],),
        ),
        extraction._canonical_row(
            DOCUMENT_ID,
            1,
            "V2",
            "Second field",
            (),
            None,
            (("1 - 2", "One through two"),),
            (locators[1]["source_region_locator_id"],),
        ),
    ]
    return extraction._document_derivation(
        DOCUMENT_ID,
        {
            "decoder_kind": "strict_source_text",
            "encoding": "UTF-8",
            "error_action": "abort",
            "bom_action": "forbidden",
            "newline_action": "preserve_source_cr_lf_crlf_sequences",
        },
        {
            "parser_family": extraction.STATA_PARSER_FAMILY,
            "source_region_locators": locators,
            "row_terminator": "\n",
            "row_order": "first_complete_source_occurrence",
            "unparsed_field_statement_action": "abort",
        },
        rows,
    )


def _pdf_derivation():
    page = 'V1 "First field" NUM(1.0)\n0 0.00 0 Zero\n'
    locator = extraction._pdf_locator(
        DOCUMENT_ID, page, 1, 0, len(page.encode("utf-8"))
    )
    row = extraction._canonical_row(
        DOCUMENT_ID,
        0,
        "V1",
        "First field",
        (),
        "NUM(1.0)",
        (("0", "Zero"),),
        (locator["source_region_locator_id"],),
    )
    return extraction._document_derivation(
        DOCUMENT_ID,
        {
            "decoder_kind": "pinned_pdf_page_text_derivation",
            "encoding": "UTF-8",
            "error_action": "abort",
            "bom_action": "forbidden",
            "newline_action": "preserve_pinned_page_strings",
        },
        {
            "parser_family": extraction.PDF_PARSER_FAMILY,
            "source_region_locators": [locator],
            "row_terminator": "\n",
            "row_order": "first_complete_source_occurrence",
            "unparsed_field_statement_action": "abort",
        },
        (row,),
    )


def _repin_rows(derivation):
    rows = derivation["canonical_rows"]
    for row in rows:
        row["normalized_entry_domain_sha256"] = extraction.canonical_sha256(
            row["normalized_entries"]
        )
    derivation["canonical_row_keyset_sha256"] = extraction.canonical_sha256(
        [row["codebook_field_row_id"] for row in rows]
    )
    derivation["canonical_row_domain_sha256"] = extraction.canonical_sha256(
        rows
    )


@pytest.mark.parametrize("factory", [_text_derivation, _pdf_derivation])
def test_exact_nested_derivation_schemas_accept_generated_shapes(factory):
    extraction.validate_document_derivation(factory())


@pytest.mark.parametrize(
    ("key", "replacement", "match"),
    [
        ("decoder_kind", "garbage", "decoder kind"),
        ("encoding", "utf-8", "source-text decoder"),
        ("error_action", "replace", "decoder action"),
        ("bom_action", "strip_all", "source-text decoder"),
        ("newline_action", "normalize", "source-text decoder"),
    ],
)
def test_decoder_literal_mutations_abort(key, replacement, match):
    derivation = _text_derivation()
    derivation["decoder"][key] = replacement
    with pytest.raises(extraction.CodebookExtractionError, match=match):
        extraction.validate_document_derivation(derivation)


def test_extra_decoder_key_aborts():
    derivation = _text_derivation()
    derivation["decoder"]["fallback"] = True
    with pytest.raises(extraction.CodebookExtractionError, match="keyset"):
        extraction.validate_document_derivation(derivation)


@pytest.mark.parametrize(
    ("key", "replacement", "match"),
    [
        ("parser_family", "garbage", "parser family"),
        ("row_terminator", "", "segmentation law"),
        ("row_order", "sorted", "segmentation law"),
        ("unparsed_field_statement_action", "ignore", "segmentation law"),
    ],
)
def test_segmentation_literal_mutations_abort(key, replacement, match):
    derivation = _text_derivation()
    derivation["row_segmentation"][key] = replacement
    with pytest.raises(extraction.CodebookExtractionError, match=match):
        extraction.validate_document_derivation(derivation)


def test_extra_segmentation_key_aborts():
    derivation = _text_derivation()
    derivation["row_segmentation"]["fallback"] = True
    with pytest.raises(extraction.CodebookExtractionError, match="keyset"):
        extraction.validate_document_derivation(derivation)


def test_decoder_and_parser_family_must_agree():
    derivation = _text_derivation()
    derivation["row_segmentation"][
        "parser_family"
    ] = extraction.PDF_PARSER_FAMILY
    with pytest.raises(
        extraction.CodebookExtractionError, match="decoder/parser-family"
    ):
        extraction.validate_document_derivation(derivation)


def test_extra_locator_key_aborts():
    derivation = _text_derivation()
    derivation["row_segmentation"]["source_region_locators"][0][
        "fallback"
    ] = True
    with pytest.raises(extraction.CodebookExtractionError, match="keyset"):
        extraction.validate_document_derivation(derivation)


def test_locator_identity_equation_aborts_coordinate_mutation():
    derivation = _text_derivation()
    derivation["row_segmentation"]["source_region_locators"][0][
        "byte_end"
    ] -= 1
    with pytest.raises(
        extraction.CodebookExtractionError, match="identity equation"
    ):
        extraction.validate_document_derivation(derivation)


def test_locator_order_mutation_aborts():
    derivation = _text_derivation()
    locators = derivation["row_segmentation"]["source_region_locators"]
    locators.reverse()
    with pytest.raises(extraction.CodebookExtractionError, match="order"):
        extraction.validate_document_derivation(derivation)


def test_duplicate_locator_mutation_aborts():
    derivation = _text_derivation()
    locators = derivation["row_segmentation"]["source_region_locators"]
    locators[1] = deepcopy(locators[0])
    with pytest.raises(extraction.CodebookExtractionError, match="duplicate"):
        extraction.validate_document_derivation(derivation)


def test_canonical_row_keyset_digest_is_recomputed():
    derivation = _text_derivation()
    derivation["canonical_row_keyset_sha256"] = "0" * 64
    with pytest.raises(extraction.CodebookExtractionError, match="keyset"):
        extraction.validate_document_derivation(derivation)


def test_extra_canonical_row_key_aborts_even_after_domain_repin():
    derivation = _text_derivation()
    derivation["canonical_rows"][0]["fallback"] = True
    _repin_rows(derivation)
    with pytest.raises(extraction.CodebookExtractionError, match="keyset"):
        extraction.validate_document_derivation(derivation)


def test_row_locator_ids_must_be_an_ordered_unique_foreign_key_subsequence():
    derivation = _text_derivation()
    locator_ids = [
        locator["source_region_locator_id"]
        for locator in derivation["row_segmentation"]["source_region_locators"]
    ]
    derivation["canonical_rows"][0]["source_locator_ids"] = locator_ids[::-1]
    _repin_rows(derivation)
    with pytest.raises(extraction.CodebookExtractionError, match="order"):
        extraction.validate_document_derivation(derivation)


@pytest.mark.parametrize(
    ("key", "replacement", "match"),
    [
        ("source_meaning", "", "empty source meaning"),
        ("typed_value_unit", "USD", "value unit"),
        ("missing_reason_code", "invented", "missing reason"),
        ("canonical_value", 1, "literal canonical value"),
        ("canonical_value", True, "literal canonical value"),
        ("canonical_value", 0.0, "literal canonical value"),
    ],
)
def test_self_consistently_repinned_literal_mutations_abort(
    key, replacement, match
):
    derivation = _text_derivation()
    derivation["canonical_rows"][0]["normalized_entries"][0][key] = replacement
    _repin_rows(derivation)
    with pytest.raises(extraction.CodebookExtractionError, match=match):
        extraction.validate_document_derivation(derivation)


def test_self_consistently_repinned_range_step_mutation_aborts():
    derivation = _text_derivation()
    derivation["canonical_rows"][1]["normalized_entries"][0]["step"] = 2
    _repin_rows(derivation)
    with pytest.raises(extraction.CodebookExtractionError, match="step"):
        extraction.validate_document_derivation(derivation)


def test_registered_source_is_read_stably_and_exact_bytes_are_parsed(tmp_path):
    relative_path = "nested/source.sps"
    _write_source(tmp_path, relative_path)

    derivation = extraction.extract_codebook_rows(
        _source_document(relative_path), tmp_path
    )

    assert derivation["canonical_row_count"] == 1
    row = derivation["canonical_rows"][0]
    assert row["raw_field_id"] == "V1"
    assert row["normalized_entries"][0]["source_meaning"] == "Zero"


def test_pdf_derivation_consumes_the_authenticated_byte_buffer(
    tmp_path, monkeypatch
):
    raw = b"registered PDF bytes"
    relative_path = "source.pdf"
    _write_source(tmp_path, relative_path, raw)
    observed = []

    def derive_pages(value):
        observed.append(value)
        return ("derived page",)

    monkeypatch.setattr(
        extraction, "pinned_pdf_page_text_from_bytes", derive_pages
    )
    monkeypatch.setattr(
        extraction,
        "_extract_pdf_document",
        lambda source_document, pages: {"pages": pages},
    )

    result = extraction.extract_codebook_rows(
        _source_document(relative_path, raw), tmp_path
    )

    assert observed == [raw]
    assert result == {"pages": ("derived page",)}


@pytest.mark.parametrize(
    "relative_path",
    ["../source.sps", "/source.sps", "nested/../source.sps", "./source.sps"],
)
def test_registered_source_path_must_remain_beneath_anchored_root(
    tmp_path, relative_path
):
    with pytest.raises(
        extraction.CodebookExtractionError, match="canonical source path"
    ):
        extraction.extract_codebook_rows(
            _source_document(relative_path), tmp_path
        )


def test_registered_source_leaf_symlink_aborts(tmp_path):
    real_path = _write_source(tmp_path, "real.sps")
    linked_path = tmp_path / "linked.sps"
    linked_path.symlink_to(real_path.name)

    with pytest.raises(
        extraction.CodebookExtractionError, match="cannot securely open"
    ):
        extraction.extract_codebook_rows(
            _source_document("linked.sps"), tmp_path
        )


def test_registered_source_ancestor_symlink_aborts(tmp_path):
    _write_source(tmp_path, "real/source.sps")
    (tmp_path / "linked").symlink_to("real", target_is_directory=True)

    with pytest.raises(
        extraction.CodebookExtractionError, match="cannot securely open"
    ):
        extraction.extract_codebook_rows(
            _source_document("linked/source.sps"), tmp_path
        )


def test_registered_source_mutation_during_read_aborts(tmp_path, monkeypatch):
    relative_path = "source.sps"
    source_path = _write_source(tmp_path, relative_path)
    mutated = SOURCE_BYTES.replace(b"Zero", b"Hero")
    real_read = os.read
    changed = False

    def mutating_read(descriptor, count):
        nonlocal changed
        if not changed:
            changed = True
            source_path.write_bytes(mutated)
            metadata = source_path.stat()
            os.utime(
                source_path,
                ns=(
                    metadata.st_atime_ns,
                    metadata.st_mtime_ns + 1_000_000_000,
                ),
            )
        return real_read(descriptor, count)

    monkeypatch.setattr(extraction.os, "read", mutating_read)
    with pytest.raises(
        extraction.CodebookExtractionError, match="changed while reading"
    ):
        extraction.extract_codebook_rows(
            _source_document(relative_path), tmp_path
        )


def test_registered_source_exact_size_and_full_sha_are_required(tmp_path):
    relative_path = "source.sps"
    _write_source(tmp_path, relative_path)

    wrong_size = _source_document(relative_path)
    wrong_size["byte_size"] += 1
    with pytest.raises(
        extraction.CodebookExtractionError, match="size mismatch"
    ):
        extraction.extract_codebook_rows(wrong_size, tmp_path)

    wrong_hash = _source_document(relative_path)
    wrong_hash["sha256"] = "0" * 64
    with pytest.raises(
        extraction.CodebookExtractionError, match="SHA-256 mismatch"
    ):
        extraction.extract_codebook_rows(wrong_hash, tmp_path)
