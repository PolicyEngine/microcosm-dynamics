"""Independent dictionary-layout extraction over the 86 setup documents."""

from __future__ import annotations

from pathlib import Path

import pytest

from populace_dynamics.data import psid_source_compiler as compiler
from populace_dynamics.data.psid_dictionary_extraction import (
    decode_source,
    extract_dictionary_layout_rows,
)

PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()

pytestmark = pytest.mark.skipif(
    not PSID_ROOT.is_dir(),
    reason="staged PSID source corpus is unavailable",
)


@pytest.fixture(scope="module")
def evidence_corpus():
    return compiler.load_authenticated_evidence(
        psid_root=PSID_ROOT,
        authenticate_source_files=False,
    )


@pytest.fixture(scope="module")
def dictionary_derivations(evidence_corpus):
    return {
        document["canonical_source_path"]: (
            extract_dictionary_layout_rows(document, PSID_ROOT)
        )
        for document in evidence_corpus.source_manifest
        if document["document_role"] == "dictionary_layout"
    }


def test_every_registered_setup_document_derives(dictionary_derivations):
    assert len(dictionary_derivations) == 86
    stata = [
        path for path in dictionary_derivations if path.endswith(".do")
    ]
    spss = [path for path in dictionary_derivations if path.endswith(".sps")]
    assert len(stata) == 43
    assert len(spss) == 43
    assert sum(
        derivation["canonical_row_count"]
        for derivation in dictionary_derivations.values()
    ) == 179_198


def test_derivation_shapes_are_exact(dictionary_derivations):
    for derivation in dictionary_derivations.values():
        assert sorted(derivation) == [
            "canonical_row_count",
            "canonical_row_domain_sha256",
            "canonical_row_keyset_sha256",
            "canonical_rows",
            "decoder",
            "derivation_kind",
            "row_segmentation",
            "source_document_id",
        ]
        assert derivation["derivation_kind"] == "dictionary_layout_rows"
        decoder = derivation["decoder"]
        assert decoder["decoder_kind"] == "strict_source_text"
        assert decoder["encoding"] in {"UTF-8", "windows-1252"}
        assert decoder["error_action"] == "abort"
        assert decoder["bom_action"] in {
            "forbidden",
            "remove_one_source_declared_bom",
        }
        assert decoder["newline_action"] == (
            "preserve_source_cr_lf_crlf_sequences"
        )
        segmentation = derivation["row_segmentation"]
        assert segmentation["parser_family"] in {
            "psid_stata_setup_statements_v1",
            "psid_spss_setup_statements_v1",
        }
        assert segmentation["row_order"] == "first_complete_source_occurrence"
        assert segmentation["unparsed_field_statement_action"] == "abort"
        assert segmentation["source_region_locators"]
        assert derivation["canonical_row_count"] == len(
            derivation["canonical_rows"]
        )


def test_locators_are_unique_ordered_exact_byte_ranges(
    dictionary_derivations,
):
    for path, derivation in dictionary_derivations.items():
        raw = (PSID_ROOT / path).read_bytes()
        locators = derivation["row_segmentation"]["source_region_locators"]
        identifiers = [
            locator["source_region_locator_id"] for locator in locators
        ]
        assert len(set(identifiers)) == len(identifiers)
        previous = -1
        for locator in locators:
            assert locator["locator_kind"] == "raw_byte_range"
            assert locator["page_number"] is None
            assert locator["utf8_start"] is None
            assert locator["utf8_end"] is None
            assert 0 <= locator["byte_start"] < locator["byte_end"]
            assert locator["byte_end"] <= len(raw)
            assert locator["byte_start"] >= previous
            previous = locator["byte_start"]
            assert locator["range_sha256"] == compiler.sha256_bytes(
                raw[locator["byte_start"] : locator["byte_end"]]
            )
        known = set(identifiers)
        for row in derivation["canonical_rows"]:
            assert row["source_locator_ids"]
            assert set(row["source_locator_ids"]) <= known


def test_setups_cover_and_agree_with_every_evidence_field(
    evidence_corpus,
    dictionary_derivations,
):
    """Both setup languages must reproduce all 89,599 field coordinates."""

    by_key: dict[tuple[int, str], list[dict[str, object]]] = {}
    for path, derivation in dictionary_derivations.items():
        wave = next(
            document["interview_waves"][0]
            for document in evidence_corpus.source_manifest
            if document["canonical_source_path"] == path
        )
        for row in derivation["canonical_rows"]:
            by_key.setdefault((wave, row["raw_field_id"]), []).append(row)

    for field in evidence_corpus.fields:
        rows = by_key.get(field.key)
        assert rows, f"no setup statement for {field.key}"
        assert len(rows) == 2, f"expected both setup languages for {field.key}"
        assert {row["source_start"] for row in rows} == {field.layout_start}
        assert {row["source_end"] for row in rows} == {field.layout_end}
        assert {row["raw_width"] for row in rows} == {field.raw_width}
        assert {row["start"] for row in rows} == {field.layout_start - 1}
        assert {row["end"] for row in rows} == {field.layout_end}
        declared = {
            row["source_format_text"]
            for row in rows
            if row["source_format_text"] is not None
        }
        if field.spss_numeric_format is None:
            assert not declared
        else:
            assert declared == {field.spss_numeric_format}


def test_extraction_is_deterministic(evidence_corpus):
    document = next(
        row
        for row in evidence_corpus.source_manifest
        if row["canonical_source_path"] == "family/1968/FAM1968.do"
    )
    first = extract_dictionary_layout_rows(document, PSID_ROOT)
    second = extract_dictionary_layout_rows(document, PSID_ROOT)
    assert first == second
    assert first["canonical_row_count"] == 447
    row = first["canonical_rows"][0]
    assert row["raw_field_id"] == "V1"
    assert row["source_start"] == 1
    assert row["source_end"] == 1
    assert row["source_label"] == "RELEASE NUMBER"
    assert row["source_format_text"] is None
    assert row["dictionary_field_row_id"].endswith("#row:0")


def test_storage_type_prefixes_never_become_a_declared_parse_kind(
    evidence_corpus,
):
    """`long` and `str` are Stata syntax, not a semantic declaration."""

    document = next(
        row
        for row in evidence_corpus.source_manifest
        if row["canonical_source_path"] == "family/2019/FAM2019ER.do"
    )
    derivation = extract_dictionary_layout_rows(document, PSID_ROOT)
    assert derivation["canonical_row_count"] > 0
    for row in derivation["canonical_rows"]:
        assert row["declared_parse_kind"] is None
        assert not row["raw_field_id"].startswith(("long", "str"))


def test_decoder_prefers_strict_utf8_then_windows_1252():
    assert decode_source(b"plain ascii").encoding == "UTF-8"
    assert decode_source(b"\xef\xbb\xbfascii").bom_action == (
        "remove_one_source_declared_bom"
    )
    assert decode_source(b"caf\xe9").encoding == "windows-1252"
    with pytest.raises(ValueError):
        decode_source(b"\x81")
