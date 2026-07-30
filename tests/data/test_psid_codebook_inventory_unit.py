"""Unit tests for the locator-pinned PSID codebook extractor."""

from __future__ import annotations

import ast
import base64
import zlib
from pathlib import Path

import pytest

from populace_dynamics.data import psid_covered_earnings_registry
from populace_dynamics.data import psid_questionnaire_inventory as inventory

TABLE_HEADER = "  Count       %    Value/Range Code Value/Range Text"


def test_code_map_parser_preserves_column_and_page_wrap_edge_cases():
    assert inventory._parse_codebook_map(
        [
            "  4,549   94.73              0 No assignments",
            "                               3 - 6",
            "      1     .02              1 -2",
        ],
        TABLE_HEADER,
    ) == [
        ["4,549", "94.73", "0", "No assignments 3 - 6"],
        ["1", ".02", "1", "-2"],
    ]
    assert inventory._parse_codebook_map(
        [
            "  5,161   76.49          .01 - Actual amount",
            "                    999,998.99",
            "  1,586   23.51            .00 No labor income",
        ],
        TABLE_HEADER,
    ) == [
        ["5,161", "76.49", ".01 - 999,998.99", "Actual amount"],
        ["1,586", "23.51", ".00", "No labor income"],
    ]
    assert inventory._parse_codebook_map(
        [
            "    140    1.75              1",
            "                                Was received this month",
        ],
        TABLE_HEADER,
    ) == [["140", "1.75", "1", "Was received this month"]]
    assert inventory._is_explicit_missing_meaning("Not ascertained")
    assert inventory._is_explicit_missing_meaning(
        "Number of rooms in dwelling not ascertained"
    )
    assert inventory._is_explicit_missing_meaning("Don't know")
    assert not inventory._is_explicit_missing_meaning(
        "Number of rooms in dwelling not ascertained or respondent "
        "shares room"
    )
    assert not inventory._is_explicit_missing_meaning(
        "Completed education was less than high school; completed "
        "education was not ascertained"
    )
    assert not inventory._is_explicit_missing_meaning(
        "This family is primary either alone or sharing was not ascertained"
    )
    assert not inventory._is_explicit_missing_meaning(
        "Teachers and related occupations (including NA type)"
    )


def test_code_map_parser_rejects_orphan_and_unclosed_continuations():
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="precedes its first row",
    ):
        inventory._parse_codebook_map(
            ["                               continuation"],
            TABLE_HEADER,
        )
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="upper bound",
    ):
        inventory._parse_codebook_map(
            [
                "      1     .01          .01 - Actual amount",
                "                               not an upper bound",
            ],
            TABLE_HEADER,
        )


def test_pdf_stream_decoder_supports_only_authenticated_filter_chain():
    payload = b"BT /F1 9 Tf (ER85496) Tj ET"
    encoded = base64.a85encode(zlib.compress(payload), adobe=True)
    assert (
        inventory._decode_pdf_stream(
            encoded,
            ["ASCII85Decode", "FlateDecode"],
        )
        == payload
    )
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="unsupported PDF stream filter",
    ):
        inventory._decode_pdf_stream(payload, ["LZWDecode"])


def test_codebook_page_framing_is_wave_and_page_exact():
    pages = [
        "cover",
        "Filename = FAM1968\nsubstantive\nPage 2 of 2",
    ]
    assert inventory._codebook_content_lines(pages, 1968) == [
        (1, "cover"),
        (2, "substantive"),
    ]
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="header drifted",
    ):
        inventory._codebook_content_lines(pages, 1969)


def test_complete_codebook_domain_constants_are_frozen():
    assert len(inventory.CODEBOOK_ERA_SPECS) == 6
    assert sum(len(waves) for _, waves in inventory.CODEBOOK_ERA_SPECS) == 43
    assert inventory.CODEBOOK_TOTAL_FIELD_COUNT == 89_599
    assert inventory.CODEBOOK_TOTAL_PAGE_COUNT == 29_897
    assert inventory.CODEBOOK_TOTAL_MAP_ROW_COUNT == 479_345
    assert inventory.CODEBOOK_TOTAL_CLOSED_RANGE_COUNT == 36_950
    assert inventory.CODEBOOK_TOTAL_DESCRIPTION_LINE_COUNT == 219_518
    assert inventory.FROZEN_INVENTORY_WAVE_ROWS_SHA256 == (
        psid_covered_earnings_registry.INVENTORY_WAVE_ROWS_SHA256
    )
    assert inventory.POST_CUTOFF_INVENTORY_WAVES == (
        psid_covered_earnings_registry.POST_CUTOFF_INVENTORY_WAVES
    )


def test_codebook_extractor_imports_no_reader_crosswalk_or_registry():
    source = Path(inventory.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        "populace_dynamics.data.family",
        "populace_dynamics.data.psid_covered_earnings",
        "populace_dynamics.data.psid_covered_earnings_registry",
        "populace_dynamics.data.psid_job_context_registry",
    }
    assert imported.isdisjoint(forbidden)
