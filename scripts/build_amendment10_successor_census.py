"""Run Amendment 10's fail-closed successor-census reproduction gate.

The input is the §24 unit-authority input relation: one JSON object per line,
in §20.3.7 denominator order, carrying exactly ``interview_wave``,
``raw_field_id``, ``derivation_status``, ``resolution_reason``, and
``source_description``.  The relation is produced by the pinned §19.3.2
codebook derivation and the ratified §20 classifier; this script does not
derive it.

Nothing is written, and nothing is printed to stdout, until every A10-R04
pin has passed.  In particular, the observed result is never treated as its
own expected value.

Usage::

    python scripts/build_amendment10_successor_census.py \\
        --field-rows <path.jsonl> [--output <path.json>] \\
        [--statements <path>] [--titles <path>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from populace_dynamics.data.psid_unit_authority import (  # noqa: E402
    ANCHORS,
    CLAUSE_TABLE,
    COMPILED_TERMINALS,
    INCOMPLETE,
    UNIT_ABSENT_RESOLUTION_REASON,
    actual_candidate_table,
    canonical_json_bytes,
    canonical_sha256,
    coding_candidate_table,
    denotation_candidate_occurrence_identity,
    denotation_candidate_start_count,
    denotation_candidate_table,
    statement_table,
    successor_census,
    title_header_candidate_table,
)
from populace_dynamics.data.psid_unit_predicate_authority import (  # noqa: E402
    CODING_START_AUTHORITY,
    PREDICATE_AUTHORITY,
    SEGMENT_START_AUTHORITY,
)
from populace_dynamics.data.psid_unit_title_authority import (  # noqa: E402
    TITLE_GENERIC_UNIT_FAMILIES,
    TITLE_LITERAL_FAMILIES,
    TITLE_START_AUTHORITY,
)

INPUT_KEYS = (
    "derivation_status",
    "interview_wave",
    "raw_field_id",
    "resolution_reason",
    "source_description",
)
MOVEMENT_KEYS = (
    "interview_wave",
    "ratified_status",
    "raw_field_id",
    "resolution_reason",
    "source_artifact",
    "successor_status",
    "unit_absence_reason",
)
FAILURE_REASON_KEYS = (
    "derivation_status",
    "field_keys",
    "resolution_reason",
)

CountPin = tuple[str, int]
MatrixPin = tuple[str, tuple[int, ...], int, str]
FailureReasonPin = tuple[str, str, int]
PredicatePartitionPin = tuple[str, int]
StartPartitionPin = tuple[str, int]

PREDICATE_DISPOSITION_ORDER = (
    "unit_naming_clause",
    "defeating_clause",
    "no_unit_naming_clause",
    "conflicting_unit_clauses",
)
START_DISPOSITION_ORDER = (
    "whole_domain_denotation",
    "explicit_no_whole_domain_denotation",
    "explicit_no_denotation",
    "unadjudicated_start",
)


class GateError(ValueError):
    """An A10-R04 preflight, parsing, construction, or pin failure."""


@dataclass(frozen=True)
class GatePins:
    """Every independent equality required by A10-R04.

    Tuples make the expected count, matrix, and reason relations immutable.
    The full-relation digests remain necessary: the tuple projections expose
    the reviewable aggregate laws but do not replace the byte-complete pins.
    """

    input_relation_row_count: int
    input_relation_sha256: str
    denominator_sha256: str
    ratified_count_rows: tuple[CountPin, ...]
    count_rows: tuple[CountPin, ...]
    count_array_sha256: str
    ordered_assignment_sha256: str
    status_matrix_rows: tuple[MatrixPin, ...]
    movement_row_count: int
    movement_rows_sha256: str
    movement_key_sha256: str
    failure_reason_rows: tuple[FailureReasonPin, ...]
    failure_reason_row_count: int
    failure_reason_rows_byte_count: int
    failure_reason_rows_sha256: str
    actual_candidate_table_row_count: int
    actual_candidate_occurrence_count: int
    actual_candidate_unadjudicated_count: int
    actual_candidate_table_sha256: str
    coding_candidate_table_row_count: int
    coding_candidate_occurrence_count: int
    coding_candidate_unadjudicated_count: int
    coding_candidate_table_sha256: str
    title_header_candidate_table_row_count: int
    title_header_matched_field_count: int
    title_header_candidate_occurrence_count: int
    title_header_positive_start_count: int
    title_header_defeated_start_count: int
    title_header_unadjudicated_start_count: int
    title_header_positive_field_count: int
    title_header_defeat_field_count: int
    title_header_no_match_field_count: int
    title_header_candidate_table_relation_byte_count: int
    title_header_candidate_table_relation_sha256: str
    title_header_candidate_table_array_sha256: str
    denotation_candidate_table_row_count: int
    denotation_candidate_occurrence_count: int
    denotation_candidate_start_count: int
    denotation_candidate_distinct_text_count: int
    denotation_candidate_plus_actual_distinct_text_count: int
    denotation_candidate_total_occurrence_count: int
    denotation_candidate_unselected_count: int
    denotation_candidate_overselected_count: int
    denotation_candidate_unadjudicated_count: int
    denotation_candidate_table_sha256: str
    denotation_start_occurrence_row_count: int
    denotation_start_occurrence_byte_count: int
    denotation_start_occurrence_sha256: str
    denotation_start_partition_rows: tuple[StartPartitionPin, ...]
    segment_start_authority_row_count: int
    segment_start_authority_start_count: int
    segment_start_authority_relation_byte_count: int
    segment_start_authority_relation_sha256: str
    segment_start_authority_array_sha256: str
    coding_start_authority_row_count: int
    coding_start_authority_relation_byte_count: int
    coding_start_authority_relation_sha256: str
    coding_start_authority_array_sha256: str
    title_start_authority_row_count: int
    title_start_authority_relation_byte_count: int
    title_start_authority_relation_sha256: str
    title_start_authority_array_sha256: str
    anchor_relation_row_count: int
    anchor_relation_byte_count: int
    anchor_relation_sha256: str
    anchor_relation_array_sha256: str
    clause_relation_row_count: int
    clause_relation_byte_count: int
    clause_relation_sha256: str
    clause_relation_array_sha256: str
    title_literal_relation_row_count: int
    title_literal_relation_byte_count: int
    title_literal_relation_sha256: str
    title_literal_relation_array_sha256: str
    title_generic_relation_array_sha256: str
    title_generic_relation_byte_count: int
    title_generic_relation_row_count: int
    title_generic_relation_sha256: str
    predicate_authority_row_count: int
    predicate_authority_relation_byte_count: int
    predicate_authority_relation_sha256: str
    predicate_authority_sha256: str
    predicate_authority_partition_rows: tuple[PredicatePartitionPin, ...]
    statement_table_row_count: int
    statement_table_sha256: str
    unit_bearing_statement_count: int
    unit_bearing_relation_byte_count: int
    unit_bearing_relation_sha256: str
    unit_bearing_relation_array_sha256: str
    census_payload_sha256: str


@dataclass(frozen=True)
class CensusBuild:
    """A pure, not-yet-emitted census build and its gated side relations."""

    field_rows: tuple[dict[str, Any], ...]
    actual_candidate_rows: tuple[dict[str, Any], ...]
    coding_candidate_rows: tuple[dict[str, Any], ...]
    title_header_candidate_rows: tuple[dict[str, Any], ...]
    title_header_candidate_relation_bytes: bytes
    denotation_candidate_rows: tuple[dict[str, Any], ...]
    segment_start_authority_rows: tuple[tuple[str, str], ...]
    segment_start_authority_relation_bytes: bytes
    coding_start_authority_rows: tuple[tuple[str, str, str | None], ...]
    coding_start_authority_relation_bytes: bytes
    title_start_authority_rows: tuple[tuple[Any, ...], ...]
    title_start_authority_relation_bytes: bytes
    anchor_rows: tuple[str, ...]
    anchor_relation_bytes: bytes
    clause_rows: tuple[tuple[str, str], ...]
    clause_relation_bytes: bytes
    title_literal_rows: tuple[tuple[str, tuple[str, ...]], ...]
    title_literal_relation_bytes: bytes
    title_generic_rows: tuple[tuple[str, tuple[str, ...]], ...]
    title_generic_relation_bytes: bytes
    predicate_authority_rows: tuple[tuple[str, str | None, str], ...]
    predicate_authority_relation_bytes: bytes
    statement_rows: tuple[dict[str, Any], ...]
    unit_bearing_rows: tuple[tuple[Any, ...], ...]
    unit_bearing_relation_bytes: bytes
    payload: dict[str, Any]


# Frozen only after regeneration from the lawful raw relation.  These are
# expected values, never observations synthesized by the production gate.
EXPECTED_A10_R04_PINS = GatePins(
    input_relation_row_count=89599,
    input_relation_sha256="563b1eaede9dcb5a085d8014dd3a4aacb2d3419ce7d0a0eb65063753b375ca6e",
    denominator_sha256="7e497f20e05cbdad384daece86d4aa08b16587b83cb6290193b6fdc28705b764",
    ratified_count_rows=(
        ("compiled_source_numeric_grammar", 17329),
        (
            "compiled_source_numeric_grammar_padding_underdetermined_exact_replay",
            1853,
        ),
        (
            "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_exact_replay",
            674,
        ),
        ("compiled_source_numeric_grammar_partial_range_exact_replay", 47),
        ("value_code_domain_no_numeric_grammar", 67316),
        ("value_code_range_physical_rendering_unestablished", 1145),
        ("nonnumeric_source_field_outside_numeric_grammar", 0),
        ("conflicting_source_numeric_format", 1),
        ("unsupported_source_numeric_format", 421),
        ("incomplete_source_numeric_authority", 813),
    ),
    count_rows=(
        ("compiled_source_numeric_grammar", 8024),
        (
            "compiled_source_numeric_grammar_padding_underdetermined_exact_replay",
            273,
        ),
        (
            "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_exact_replay",
            77,
        ),
        ("compiled_source_numeric_grammar_partial_range_exact_replay", 1),
        ("value_code_domain_no_numeric_grammar", 67316),
        ("value_code_range_physical_rendering_unestablished", 1145),
        ("nonnumeric_source_field_outside_numeric_grammar", 0),
        ("conflicting_source_numeric_format", 1),
        ("unsupported_source_numeric_format", 421),
        ("incomplete_source_numeric_authority", 12341),
    ),
    count_array_sha256="017baffe4d9e2ee6ce373a93f4f82df1e1b2a42b1a18acd8c3477826df1ec32c",
    ordered_assignment_sha256="0bc16e56c3c9284070dbf68d3f6cdda9da183629b8dc9e75e32dc124ed6f19f4",
    status_matrix_rows=(
        (
            "compiled_source_numeric_grammar",
            (303, 200, 2185, 1789, 2268, 1279),
            8024,
            "d9a3ebfcdf376a065f78745c0adeddfa3ed7ace44dbe74319cabdc22402c5669",
        ),
        (
            "compiled_source_numeric_grammar_padding_underdetermined_exact_replay",
            (2, 14, 124, 36, 57, 40),
            273,
            "b8db6417119abb5f086d61ce8f6bbeada4396e08d47060bf9857283cc2d6323f",
        ),
        (
            "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_exact_replay",
            (1, 7, 42, 15, 7, 5),
            77,
            "14637a7f88c43e00f431845a0ad6d78b3ea07b88fab7765ca34ad6e852b7b46f",
        ),
        (
            "compiled_source_numeric_grammar_partial_range_exact_replay",
            (1, 0, 0, 0, 0, 0),
            1,
            "179e226fe0291c83938c8a7709968d54312f1edd21758aca8df6b261e6abe2d8",
        ),
        (
            "value_code_domain_no_numeric_grammar",
            (2606, 1130, 10064, 11668, 26700, 15148),
            67316,
            "6ee97ba9db16520c734a21094623376714a468c3148977666f8e107dbd35e05f",
        ),
        (
            "value_code_range_physical_rendering_unestablished",
            (89, 16, 127, 371, 320, 222),
            1145,
            "75296e361be3c9b0afb99cd74afb29849305010a93c2c1a9de3da6b54fd5054e",
        ),
        (
            "nonnumeric_source_field_outside_numeric_grammar",
            (0, 0, 0, 0, 0, 0),
            0,
            "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
        ),
        (
            "conflicting_source_numeric_format",
            (1, 0, 0, 0, 0, 0),
            1,
            "a95936320c1eb3a2b288790ac5550fd5a1d5f3e860b53fe86d0ff4da74993cb1",
        ),
        (
            "unsupported_source_numeric_format",
            (67, 20, 122, 46, 90, 76),
            421,
            "fe1aa0725ea533452ff05acd0b8fb1b907aaa5716ac9c7a287b6290e4b330010",
        ),
        (
            "incomplete_source_numeric_authority",
            (798, 451, 3081, 2058, 3712, 2241),
            12341,
            "966a4e99d37cde2c4836bc2ab73f9a41ae3da30d3b5229020f88d22dd73d14f5",
        ),
    ),
    movement_row_count=11528,
    movement_rows_sha256="03f1a9cea18b340ee7068075ca1e9bea1e1337b10f2f7e5d89092ac866cfb4fe",
    movement_key_sha256="fe844ca115d9c5314ce76608043d46393d4b129e7334cffcf761bb6e7604007c",
    failure_reason_rows=(
        (
            "conflicting_source_numeric_format",
            "conflict:overlapping_numeric_ranges",
            1,
        ),
        (
            "unsupported_source_numeric_format",
            "character_raw_replay_unknown_token",
            16,
        ),
        (
            "unsupported_source_numeric_format",
            "observed_token_outside_all_candidate_forms_or_semantics",
            144,
        ),
        (
            "unsupported_source_numeric_format",
            "selected_space_literal_unrenderable",
            78,
        ),
        (
            "unsupported_source_numeric_format",
            "selected_space_range_zero_renderable",
            183,
        ),
        (
            "incomplete_source_numeric_authority",
            "finite_no_arm_no_lawful_complete_disposition",
            46,
        ),
        (
            "incomplete_source_numeric_authority",
            "literal_only_zero_diagnostic_padding_capacity",
            767,
        ),
        (
            "incomplete_source_numeric_authority",
            "unresolved_typed_value_unit_no_source_authority",
            11528,
        ),
    ),
    failure_reason_row_count=8,
    failure_reason_rows_byte_count=211210,
    failure_reason_rows_sha256="aeba54648c4cf53eef5c0e755582f81735b4c6fd5d2e7b01089163d11afded62",
    actual_candidate_table_row_count=82,
    actual_candidate_occurrence_count=322,
    actual_candidate_unadjudicated_count=0,
    actual_candidate_table_sha256="bf77cd7294752ac9e6ac01d4d68efac86c47b7327094d5eec479d9db1f27176b",
    coding_candidate_table_row_count=203,
    coding_candidate_occurrence_count=1154,
    coding_candidate_unadjudicated_count=0,
    coding_candidate_table_sha256="9f6cd23d36ad6825a17d3ece2d2612ef89c066d5c587bd72d1933f19e4c0c195",
    # Round-3 title pins regenerated with the full successor object from the
    # lawful raw relation, never copied from a partial or evidence build.
    title_header_candidate_table_row_count=89599,
    title_header_matched_field_count=51957,
    title_header_candidate_occurrence_count=80306,
    title_header_positive_start_count=8202,
    title_header_defeated_start_count=72104,
    title_header_unadjudicated_start_count=0,
    title_header_positive_field_count=8183,
    title_header_defeat_field_count=43774,
    title_header_no_match_field_count=37642,
    title_header_candidate_table_relation_byte_count=89412166,
    title_header_candidate_table_relation_sha256=(
        "407d9aec93f7c9f42e28cf84c57f336a794be9938cfb78cbea5b8958d63adb0a"
    ),
    title_header_candidate_table_array_sha256=(
        "203a5903bbbac2f9cfeeaffad184a7fd4dd25fe98e2f942bc150695cdbfe1051"
    ),
    denotation_candidate_table_row_count=1114747,
    denotation_candidate_occurrence_count=2240669,
    denotation_candidate_start_count=2240669,
    denotation_candidate_distinct_text_count=717810,
    denotation_candidate_plus_actual_distinct_text_count=717823,
    denotation_candidate_total_occurrence_count=2240991,
    denotation_candidate_unselected_count=0,
    denotation_candidate_overselected_count=0,
    denotation_candidate_unadjudicated_count=0,
    denotation_candidate_table_sha256="aa7d466df0460808cb17e4f692e40760d5b4b2ea90c15cce322df00f5b8baff9",
    denotation_start_occurrence_row_count=2240669,
    denotation_start_occurrence_byte_count=269160095,
    denotation_start_occurrence_sha256="f1f56750744b3cb11531fcab1e6fee9d97655d32eb6241d1c6a92d443e66b27f",
    denotation_start_partition_rows=(
        ("whole_domain_denotation", 16460),
        ("explicit_no_whole_domain_denotation", 76558),
        ("explicit_no_denotation", 2147651),
        ("unadjudicated_start", 0),
    ),
    segment_start_authority_row_count=59445,
    segment_start_authority_start_count=1114747,
    segment_start_authority_relation_byte_count=8466288,
    segment_start_authority_relation_sha256="15010ecdc6985e2a69f60ab627ad58b28981d536500087e9c2702277a5974281",
    segment_start_authority_array_sha256="e9fe527412664f86654f3b423d4422a23bb5966b128b98e3136e391e45f7a04c",
    coding_start_authority_row_count=203,
    coding_start_authority_relation_byte_count=31396,
    coding_start_authority_relation_sha256="6f164c6772def69a29a57e1de04b3927ab8f56141bc2a8c6f0dee0964c8da6bf",
    coding_start_authority_array_sha256="ac2bddbed10bb445215bb19354259685efe24c82b2f59b258dec5d23fcf8497b",
    title_start_authority_row_count=54185,
    title_start_authority_relation_byte_count=16636024,
    title_start_authority_relation_sha256=(
        "d25d9312c6e88ed80896aee07c2133d1745214214104bedad73ae661294c7117"
    ),
    title_start_authority_array_sha256=(
        "ebccedca54e914da8a1f9f20a39657e220f80346df84c8bc45834169c4b971df"
    ),
    anchor_relation_row_count=105,
    anchor_relation_byte_count=4421,
    anchor_relation_sha256="9f4a835c8f6cf140b1f084c3323d887cf19f4e729341d6790216d70b8a02ca4b",
    anchor_relation_array_sha256="db4247efe4f93c66ec3d46c27154c4dbef3954a4b9b5865d4fbe364cc62d657f",
    clause_relation_row_count=165,
    clause_relation_byte_count=7578,
    clause_relation_sha256="8ddc26217bd530fae469643458648b159548e0c344d6b967dffb87abfa16ed43",
    clause_relation_array_sha256="1bd2a989c7fe7a1471bbb8b289d64e1fc66e399a0c9b2701419b6d5b636116d3",
    title_literal_relation_row_count=13,
    title_literal_relation_byte_count=733,
    title_literal_relation_sha256=(
        "e1159929e711f73757b7e51a648f2c096965881a2342d9f26ce4e95d7c8af46e"
    ),
    title_literal_relation_array_sha256=(
        "c5f6b75b64ebd86134e1b655c5d522fcd18dc2179fd28fa2c66a0943465e2913"
    ),
    title_generic_relation_array_sha256=(
        "f709526fe7802085ed691167a595f3d24504523dfa9a5fd4f61eb9269debd9de"
    ),
    title_generic_relation_byte_count=1733,
    title_generic_relation_row_count=38,
    title_generic_relation_sha256=(
        "b56ffd655abb00c8aca6e382092d08cd94325cfbf8ef4ce25651a59fc6cf8133"
    ),
    predicate_authority_row_count=2590,
    predicate_authority_relation_byte_count=400372,
    predicate_authority_relation_sha256="a783a0a3824096688374e0f9802546e847a00c4cb3905ce6a7ee6f64a51e050e",
    predicate_authority_sha256="dc4df039cd1c0ae9d31bd8827d07e1bb737c8ee383e6cbe0308789257ba5ff89",
    predicate_authority_partition_rows=(
        ("unit_naming_clause", 1534),
        ("defeating_clause", 702),
        ("no_unit_naming_clause", 353),
        ("conflicting_unit_clauses", 1),
    ),
    statement_table_row_count=3589,
    statement_table_sha256="7c3642475294dc0ecf809138ff2202ee137e441c7cc76e96b8a2642983163a57",
    unit_bearing_statement_count=1545,
    unit_bearing_relation_byte_count=238735,
    unit_bearing_relation_sha256="354de946fbb0c15f05eb1c5b202bbbd8cdc5913922cf8c402e6e253699daa153",
    unit_bearing_relation_array_sha256="0e7a96f1146063da99dfa576eb254e38cf577762522911e6332863ef9992d6b8",
    census_payload_sha256="4cd1c37140127a3cc0c48910648f091e817d34d4631966dd66bec75165d39159",
)


def _reject_constant(token: str) -> None:
    raise GateError(f"non-finite JSON number is forbidden: {token}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build an object while rejecting duplicate members at every depth."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateError(f"duplicate JSON member: {key!r}")
        result[key] = value
    return result


def _require_scalar_string(value: Any, label: str) -> None:
    if type(value) is not str:
        raise GateError(f"{label} must be a JSON string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise GateError(f"{label} is not a Unicode scalar string") from error


def _validate_input_row(row: Any, number: int) -> dict[str, Any]:
    if type(row) is not dict:
        raise GateError(f"line {number}: row must be a JSON object")
    keys = tuple(sorted(row))
    if keys != INPUT_KEYS:
        raise GateError(f"line {number}: unexpected keys {keys!r}")
    if type(row["interview_wave"]) is not int:
        raise GateError(
            f"line {number}: interview_wave must be a JSON integer"
        )
    _require_scalar_string(row["raw_field_id"], f"line {number}: raw_field_id")
    _require_scalar_string(
        row["derivation_status"], f"line {number}: derivation_status"
    )
    _require_scalar_string(
        row["resolution_reason"], f"line {number}: resolution_reason"
    )
    description = row["source_description"]
    if description is not None:
        _require_scalar_string(
            description,
            f"line {number}: source_description",
        )
    return row


def read_field_rows(path: Path) -> tuple[dict[str, Any], ...]:
    """Read the input exactly once with strict JSON and exact member types."""

    rows: list[dict[str, Any]] = []
    try:
        handle = path.open(
            "r",
            encoding="utf-8",
            errors="strict",
            newline="",
        )
    except OSError as error:
        raise GateError(f"cannot open input relation: {error}") from error
    try:
        with handle:
            for number, raw_line in enumerate(handle, 1):
                if number == 1 and raw_line.startswith("\ufeff"):
                    raise GateError("line 1: UTF-8 BOM is forbidden")
                line = raw_line.removesuffix("\n").removesuffix("\r")
                if not line:
                    raise GateError(f"line {number}: blank JSON line")
                try:
                    value = json.loads(
                        line,
                        object_pairs_hook=_strict_object,
                        parse_constant=_reject_constant,
                    )
                except GateError as error:
                    raise GateError(f"line {number}: {error}") from error
                except json.JSONDecodeError as error:
                    raise GateError(
                        f"line {number}: invalid JSON at column {error.colno}"
                    ) from error
                rows.append(_validate_input_row(value, number))
    except UnicodeDecodeError as error:
        raise GateError("input relation is not strict UTF-8") from error
    return tuple(rows)


def input_relation_sha256(field_rows: Sequence[Mapping[str, Any]]) -> str:
    """Hash the ordered five-position relation fixed by §24.4.2."""

    relation = [
        [
            row["interview_wave"],
            row["raw_field_id"],
            row["derivation_status"],
            row["resolution_reason"],
            row["source_description"],
        ]
        for row in field_rows
    ]
    return canonical_sha256(relation)


def _unit_bearing_relation(
    table: Sequence[Mapping[str, Any]],
) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            row["statement"],
            row["typed_value_unit"],
            row["field_count"],
        )
        for row in table
        if row["typed_value_unit"] is not None
    )


def _jsonl_relation_bytes(rows: Sequence[Any]) -> bytes:
    """Serialize a §24 fence as one compact JSON value per terminal LF."""

    return b"".join(
        json.dumps(
            row,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
        for row in rows
    )


def _canonical_array_sha256_stream(rows: Sequence[Any]) -> str:
    """Hash a canonical JSON array without allocating its complete bytes."""

    digest = hashlib.sha256()
    digest.update(b"[")
    for position, row in enumerate(rows):
        if position:
            digest.update(b",")
        digest.update(
            json.dumps(
                row,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
        )
    digest.update(b"]\n")
    return digest.hexdigest()


def _unit_bearing_relation_bytes(
    rows: Sequence[Sequence[Any]],
) -> bytes:
    """Serialize the §24.3 fence: one compact three-position row per LF."""

    return _jsonl_relation_bytes(rows)


def _predicate_authority_partition(
    rows: Sequence[Sequence[Any]],
) -> tuple[PredicatePartitionPin, ...]:
    """Return the closed four-way full-predicate disposition partition."""

    counts = {reason: 0 for reason in PREDICATE_DISPOSITION_ORDER}
    for position, row in enumerate(rows):
        if len(row) != 3:
            raise GateError(
                f"predicate-authority row {position}: noncanonical shape"
            )
        predicate, unit, reason = row
        if type(predicate) is not str or not predicate:
            raise GateError(
                f"predicate-authority row {position}: invalid predicate"
            )
        if type(reason) is not str or reason not in counts:
            raise GateError(
                f"predicate-authority row {position}: invalid disposition"
            )
        if reason == "unit_naming_clause":
            if type(unit) is not str or not unit:
                raise GateError(
                    f"predicate-authority row {position}: invalid unit"
                )
        elif unit is not None:
            raise GateError(
                f"predicate-authority row {position}: "
                "non-unit disposition carries a unit"
            )
        counts[reason] += 1
    return tuple((reason, counts[reason]) for reason in counts)


def _title_header_summary(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Project the complete per-field title audit into its closed census."""

    summary = {
        "matched_field_count": 0,
        "candidate_occurrence_count": 0,
        "positive_start_count": 0,
        "defeated_start_count": 0,
        "unadjudicated_start_count": 0,
        "positive_field_count": 0,
        "defeat_field_count": 0,
        "no_match_field_count": 0,
    }
    field_reasons = {
        "derived_from_title_denotation": "positive_field_count",
        "title_clause_explicitly_non_whole_domain": "defeat_field_count",
        "no_title_denotation_clause": "no_match_field_count",
    }
    for position, row in enumerate(rows):
        candidates = row.get("candidate_adjudications")
        candidate_count = row.get("candidate_count")
        if type(candidates) is not list or type(candidate_count) is not int:
            raise GateError(
                f"title/header row {position}: noncanonical candidates"
            )
        if candidate_count != len(candidates):
            raise GateError(
                f"title/header row {position}: candidate count mismatch"
            )
        summary["candidate_occurrence_count"] += candidate_count
        if candidate_count:
            summary["matched_field_count"] += 1
        for candidate in candidates:
            if type(candidate) is not dict:
                raise GateError(
                    f"title/header row {position}: non-object candidate"
                )
            disposition = candidate.get("adjudication")
            unit = candidate.get("typed_value_unit")
            if disposition == "whole_domain_denotation" and type(unit) is str:
                summary["positive_start_count"] += 1
            elif (
                disposition == "explicit_no_whole_domain_denotation"
                and unit is None
            ):
                summary["defeated_start_count"] += 1
            elif disposition == "unadjudicated_title_start" and unit is None:
                summary["unadjudicated_start_count"] += 1
            else:
                raise GateError(
                    f"title/header row {position}: invalid adjudication"
                )
        reason = row.get("disposition_reason")
        field_bucket = field_reasons.get(reason)
        if field_bucket is not None:
            summary[field_bucket] += 1
    return summary


def _validate_title_start_authority(
    rows: Sequence[Sequence[Any]],
    field_rows: Sequence[Mapping[str, Any]],
) -> None:
    """Validate description-relative title spans independently of digests."""

    descriptions: dict[tuple[Any, Any], Any] = {}
    for position, field_row in enumerate(field_rows):
        witness_key = (
            field_row.get("interview_wave"),
            field_row.get("raw_field_id"),
        )
        if witness_key in descriptions:
            raise GateError(
                "title-start authority input row "
                f"{position}: duplicate raw-field witness key "
                f"{witness_key!r}"
            )
        descriptions[witness_key] = field_row.get("source_description")

    seen: set[tuple[Any, ...]] = set()
    for position, row in enumerate(rows):
        if len(row) != 11:
            raise GateError(
                f"title-start authority row {position}: noncanonical shape"
            )
        (
            description_sha256,
            bounded_context_header,
            family,
            start,
            end,
            spelling,
            unit,
            disposition,
            reason,
            wave,
            field,
        ) = row
        key = (description_sha256, family, start, end, spelling)
        if key in seen:
            raise GateError(
                f"title-start authority row {position}: duplicate context"
            )
        seen.add(key)
        if (
            type(description_sha256) is not str
            or len(description_sha256) != 64
            or type(bounded_context_header) is not str
            or type(family) is not str
            or type(start) is not int
            or type(end) is not int
            or type(spelling) is not str
            or type(reason) is not str
            or type(wave) is not int
            or type(field) is not str
        ):
            raise GateError(
                f"title-start authority row {position}: invalid member"
            )
        try:
            spelling_bytes = spelling.encode("ascii")
        except UnicodeEncodeError as error:
            raise GateError(
                f"title-start authority row {position}: non-ASCII span"
            ) from error
        if start < 0 or end <= start or end - start != len(spelling_bytes):
            raise GateError(
                f"title-start authority row {position}: invalid raw span"
            )
        witness_key = (wave, field)
        if witness_key not in descriptions:
            raise GateError(
                f"title-start authority row {position}: "
                f"missing raw-field witness key {witness_key!r}"
            )
        description = descriptions[witness_key]
        if type(description) is not str:
            raise GateError(
                f"title-start authority row {position}: "
                f"non-string raw-description witness {witness_key!r}"
            )
        description_bytes = description.encode("utf-8")
        if (
            hashlib.sha256(description_bytes).hexdigest() != description_sha256
            or not description.startswith(bounded_context_header)
            or description_bytes[start:end] != spelling_bytes
        ):
            raise GateError(
                f"title-start authority row {position}: "
                "raw-description grounding mismatch"
            )
        if disposition == "whole_domain_denotation":
            if type(unit) is not str or not unit:
                raise GateError(
                    f"title-start authority row {position}: missing unit"
                )
        elif disposition == "explicit_no_whole_domain_denotation":
            if unit is not None:
                raise GateError(
                    f"title-start authority row {position}: defeated unit"
                )
        else:
            raise GateError(
                f"title-start authority row {position}: open disposition"
            )


def build_payload(field_rows: Sequence[dict[str, Any]]) -> CensusBuild:
    """Construct all census relations without validating or emitting them."""

    frozen_rows = tuple(field_rows)
    try:
        # The independently selected all-field title audit is constructed
        # before the successor; validation below must close it before emit.
        title_rows = tuple(title_header_candidate_table(frozen_rows))
        actual_rows = tuple(actual_candidate_table(frozen_rows))
        coding_rows = tuple(coding_candidate_table(frozen_rows))
        candidate_rows = tuple(denotation_candidate_table(frozen_rows))
        start_identity = denotation_candidate_occurrence_identity(frozen_rows)
        table = tuple(statement_table(frozen_rows))
        census = successor_census(frozen_rows)
    except (KeyError, TypeError, ValueError) as error:
        raise GateError(f"census construction failed: {error}") from error
    unit_rows = _unit_bearing_relation(table)
    unit_bytes = _unit_bearing_relation_bytes(unit_rows)
    anchor_rows = tuple(ANCHORS)
    anchor_bytes = _jsonl_relation_bytes(anchor_rows)
    clause_rows = tuple(CLAUSE_TABLE)
    clause_bytes = _jsonl_relation_bytes(clause_rows)
    title_literal_rows = tuple(TITLE_LITERAL_FAMILIES)
    title_literal_bytes = _jsonl_relation_bytes(title_literal_rows)
    title_generic_rows = tuple(TITLE_GENERIC_UNIT_FAMILIES)
    title_generic_bytes = _jsonl_relation_bytes(title_generic_rows)
    predicate_rows = tuple(PREDICATE_AUTHORITY)
    predicate_bytes = _jsonl_relation_bytes(predicate_rows)
    title_authority_rows = tuple(TITLE_START_AUTHORITY)
    title_authority_bytes = _jsonl_relation_bytes(title_authority_rows)
    segment_authority_rows = tuple(SEGMENT_START_AUTHORITY)
    segment_authority_bytes = _jsonl_relation_bytes(segment_authority_rows)
    coding_authority_rows = tuple(CODING_START_AUTHORITY)
    coding_authority_bytes = _jsonl_relation_bytes(coding_authority_rows)
    title_bytes = b"".join(canonical_json_bytes(row) for row in title_rows)
    title_summary = _title_header_summary(title_rows)
    actual_occurrences = sum(row["occurrence_count"] for row in actual_rows)
    actual_unadjudicated = sum(
        row["occurrence_count"]
        for row in actual_rows
        if row["adjudication"].startswith("unadjudicated")
    )
    coding_occurrences = sum(row["occurrence_count"] for row in coding_rows)
    coding_unadjudicated = sum(
        row["occurrence_count"]
        for row in coding_rows
        if row["adjudication"].startswith("unadjudicated")
    )
    candidate_occurrences = sum(
        row["occurrence_count"] for row in candidate_rows
    )
    candidate_starts = sum(
        denotation_candidate_start_count(row["source_description"])
        for row in frozen_rows
    )
    unadjudicated = sum(
        row["occurrence_count"]
        for row in candidate_rows
        if row["adjudication"].startswith("unadjudicated")
    )
    candidate_texts = {row["candidate"] for row in candidate_rows}
    candidate_plus_actual_texts = candidate_texts | {
        row["candidate"] for row in actual_rows
    }
    payload: dict[str, Any] = {
        "schema_version": "amendment_10_successor_census.v4",
        "input_relation_row_count": len(frozen_rows),
        "input_relation_sha256": input_relation_sha256(frozen_rows),
        "actual_candidate_table_row_count": len(actual_rows),
        "actual_candidate_occurrence_count": actual_occurrences,
        "actual_candidate_unadjudicated_count": actual_unadjudicated,
        "actual_candidate_table_sha256": canonical_sha256(actual_rows),
        "coding_candidate_table_row_count": len(coding_rows),
        "coding_candidate_occurrence_count": coding_occurrences,
        "coding_candidate_unadjudicated_count": coding_unadjudicated,
        "coding_candidate_table_sha256": canonical_sha256(coding_rows),
        "title_header_candidate_table_row_count": len(title_rows),
        "title_header_matched_field_count": title_summary[
            "matched_field_count"
        ],
        "title_header_candidate_occurrence_count": title_summary[
            "candidate_occurrence_count"
        ],
        "title_header_positive_start_count": title_summary[
            "positive_start_count"
        ],
        "title_header_defeated_start_count": title_summary[
            "defeated_start_count"
        ],
        "title_header_unadjudicated_start_count": title_summary[
            "unadjudicated_start_count"
        ],
        "title_header_positive_field_count": title_summary[
            "positive_field_count"
        ],
        "title_header_defeat_field_count": title_summary["defeat_field_count"],
        "title_header_no_match_field_count": title_summary[
            "no_match_field_count"
        ],
        "title_header_candidate_table_relation_byte_count": len(title_bytes),
        "title_header_candidate_table_relation_sha256": hashlib.sha256(
            title_bytes
        ).hexdigest(),
        "title_header_candidate_table_array_sha256": (
            _canonical_array_sha256_stream(title_rows)
        ),
        "denotation_candidate_table_row_count": len(candidate_rows),
        "denotation_candidate_occurrence_count": candidate_occurrences,
        "denotation_candidate_start_count": candidate_starts,
        "denotation_candidate_distinct_text_count": len(candidate_texts),
        "denotation_candidate_plus_actual_distinct_text_count": len(
            candidate_plus_actual_texts
        ),
        "denotation_candidate_total_occurrence_count": (
            candidate_occurrences + actual_occurrences
        ),
        "denotation_candidate_unselected_count": start_identity[
            "unselected_count"
        ],
        "denotation_candidate_overselected_count": start_identity[
            "overselected_count"
        ],
        "denotation_candidate_unadjudicated_count": unadjudicated,
        "denotation_candidate_table_sha256": (
            _canonical_array_sha256_stream(candidate_rows)
        ),
        "denotation_start_occurrence_row_count": start_identity["row_count"],
        "denotation_start_occurrence_byte_count": start_identity["byte_count"],
        "denotation_start_occurrence_sha256": start_identity["sha256"],
        "denotation_start_partition_rows": [
            {
                "adjudication": disposition,
                "occurrence_count": start_identity["partition"][disposition],
            }
            for disposition in START_DISPOSITION_ORDER
        ],
        "segment_start_authority_row_count": len(segment_authority_rows),
        "segment_start_authority_start_count": sum(
            len(vector) for _segment, vector in segment_authority_rows
        ),
        "segment_start_authority_relation_byte_count": len(
            segment_authority_bytes
        ),
        "segment_start_authority_relation_sha256": hashlib.sha256(
            segment_authority_bytes
        ).hexdigest(),
        "segment_start_authority_array_sha256": canonical_sha256(
            segment_authority_rows
        ),
        "coding_start_authority_row_count": len(coding_authority_rows),
        "coding_start_authority_relation_byte_count": len(
            coding_authority_bytes
        ),
        "coding_start_authority_relation_sha256": hashlib.sha256(
            coding_authority_bytes
        ).hexdigest(),
        "coding_start_authority_array_sha256": canonical_sha256(
            coding_authority_rows
        ),
        "title_start_authority_row_count": len(title_authority_rows),
        "title_start_authority_relation_byte_count": len(
            title_authority_bytes
        ),
        "title_start_authority_relation_sha256": hashlib.sha256(
            title_authority_bytes
        ).hexdigest(),
        "title_start_authority_array_sha256": canonical_sha256(
            title_authority_rows
        ),
        "title_literal_relation_row_count": len(title_literal_rows),
        "title_literal_relation_byte_count": len(title_literal_bytes),
        "title_literal_relation_sha256": hashlib.sha256(
            title_literal_bytes
        ).hexdigest(),
        "title_literal_relation_array_sha256": canonical_sha256(
            title_literal_rows
        ),
        "title_generic_relation_array_sha256": canonical_sha256(
            title_generic_rows
        ),
        "title_generic_relation_byte_count": len(title_generic_bytes),
        "title_generic_relation_row_count": len(title_generic_rows),
        "title_generic_relation_sha256": hashlib.sha256(
            title_generic_bytes
        ).hexdigest(),
        "predicate_authority_row_count": len(predicate_rows),
        "predicate_authority_sha256": canonical_sha256(predicate_rows),
        "statement_table_row_count": len(table),
        "statement_table_sha256": canonical_sha256(table),
        "unit_bearing_statement_count": len(unit_rows),
        **census,
    }
    payload["census_sha256"] = canonical_sha256(payload)
    return CensusBuild(
        field_rows=frozen_rows,
        actual_candidate_rows=actual_rows,
        coding_candidate_rows=coding_rows,
        title_header_candidate_rows=title_rows,
        title_header_candidate_relation_bytes=title_bytes,
        denotation_candidate_rows=candidate_rows,
        segment_start_authority_rows=segment_authority_rows,
        segment_start_authority_relation_bytes=segment_authority_bytes,
        coding_start_authority_rows=coding_authority_rows,
        coding_start_authority_relation_bytes=coding_authority_bytes,
        title_start_authority_rows=title_authority_rows,
        title_start_authority_relation_bytes=title_authority_bytes,
        anchor_rows=anchor_rows,
        anchor_relation_bytes=anchor_bytes,
        clause_rows=clause_rows,
        clause_relation_bytes=clause_bytes,
        title_literal_rows=title_literal_rows,
        title_literal_relation_bytes=title_literal_bytes,
        title_generic_rows=title_generic_rows,
        title_generic_relation_bytes=title_generic_bytes,
        predicate_authority_rows=predicate_rows,
        predicate_authority_relation_bytes=predicate_bytes,
        statement_rows=table,
        unit_bearing_rows=unit_rows,
        unit_bearing_relation_bytes=unit_bytes,
        payload=payload,
    )


def _count_projection(payload: Mapping[str, Any]) -> tuple[CountPin, ...]:
    return tuple(
        (row["derivation_status"], row["field_count"])
        for row in payload["count_rows"]
    )


def _matrix_projection(payload: Mapping[str, Any]) -> tuple[MatrixPin, ...]:
    return tuple(
        (
            row["derivation_status"],
            tuple(row["artifact_field_counts"]),
            row["field_count"],
            row["field_key_sha256"],
        )
        for row in payload["status_matrix_rows"]
    )


def _failure_projection(
    payload: Mapping[str, Any],
) -> tuple[FailureReasonPin, ...]:
    return tuple(
        (
            row["derivation_status"],
            row["resolution_reason"],
            len(row["field_keys"]),
        )
        for row in payload["failure_reason_rows"]
    )


def pins_from_build(build: CensusBuild) -> GatePins:
    """Project a build into pins for isolated tests and independent review.

    The production CLI never calls this function.  Its authority is the
    separately committed ``EXPECTED_A10_R04_PINS`` object above.
    """

    payload = build.payload
    unit_bytes = build.unit_bearing_relation_bytes
    return GatePins(
        input_relation_row_count=payload["input_relation_row_count"],
        input_relation_sha256=payload["input_relation_sha256"],
        denominator_sha256=payload["denominator_sha256"],
        ratified_count_rows=tuple(
            (row["derivation_status"], row["field_count"])
            for row in payload["ratified_count_rows"]
        ),
        count_rows=_count_projection(payload),
        count_array_sha256=payload["count_array_sha256"],
        ordered_assignment_sha256=payload["ordered_assignment_sha256"],
        status_matrix_rows=_matrix_projection(payload),
        movement_row_count=payload["movement_row_count"],
        movement_rows_sha256=payload["movement_rows_sha256"],
        movement_key_sha256=payload["movement_key_sha256"],
        failure_reason_rows=_failure_projection(payload),
        failure_reason_row_count=payload["failure_reason_row_count"],
        failure_reason_rows_byte_count=(
            payload["failure_reason_rows_byte_count"]
        ),
        failure_reason_rows_sha256=payload["failure_reason_rows_sha256"],
        actual_candidate_table_row_count=(
            payload["actual_candidate_table_row_count"]
        ),
        actual_candidate_occurrence_count=(
            payload["actual_candidate_occurrence_count"]
        ),
        actual_candidate_unadjudicated_count=(
            payload["actual_candidate_unadjudicated_count"]
        ),
        actual_candidate_table_sha256=(
            payload["actual_candidate_table_sha256"]
        ),
        coding_candidate_table_row_count=(
            payload["coding_candidate_table_row_count"]
        ),
        coding_candidate_occurrence_count=(
            payload["coding_candidate_occurrence_count"]
        ),
        coding_candidate_unadjudicated_count=(
            payload["coding_candidate_unadjudicated_count"]
        ),
        coding_candidate_table_sha256=(
            payload["coding_candidate_table_sha256"]
        ),
        title_header_candidate_table_row_count=(
            payload["title_header_candidate_table_row_count"]
        ),
        title_header_matched_field_count=(
            payload["title_header_matched_field_count"]
        ),
        title_header_candidate_occurrence_count=(
            payload["title_header_candidate_occurrence_count"]
        ),
        title_header_positive_start_count=(
            payload["title_header_positive_start_count"]
        ),
        title_header_defeated_start_count=(
            payload["title_header_defeated_start_count"]
        ),
        title_header_unadjudicated_start_count=(
            payload["title_header_unadjudicated_start_count"]
        ),
        title_header_positive_field_count=(
            payload["title_header_positive_field_count"]
        ),
        title_header_defeat_field_count=(
            payload["title_header_defeat_field_count"]
        ),
        title_header_no_match_field_count=(
            payload["title_header_no_match_field_count"]
        ),
        title_header_candidate_table_relation_byte_count=len(
            build.title_header_candidate_relation_bytes
        ),
        title_header_candidate_table_relation_sha256=hashlib.sha256(
            build.title_header_candidate_relation_bytes
        ).hexdigest(),
        title_header_candidate_table_array_sha256=(
            payload["title_header_candidate_table_array_sha256"]
        ),
        denotation_candidate_table_row_count=(
            payload["denotation_candidate_table_row_count"]
        ),
        denotation_candidate_occurrence_count=(
            payload["denotation_candidate_occurrence_count"]
        ),
        denotation_candidate_start_count=(
            payload["denotation_candidate_start_count"]
        ),
        denotation_candidate_distinct_text_count=(
            payload["denotation_candidate_distinct_text_count"]
        ),
        denotation_candidate_plus_actual_distinct_text_count=(
            payload["denotation_candidate_plus_actual_distinct_text_count"]
        ),
        denotation_candidate_total_occurrence_count=(
            payload["denotation_candidate_total_occurrence_count"]
        ),
        denotation_candidate_unselected_count=(
            payload["denotation_candidate_unselected_count"]
        ),
        denotation_candidate_overselected_count=(
            payload["denotation_candidate_overselected_count"]
        ),
        denotation_candidate_unadjudicated_count=(
            payload["denotation_candidate_unadjudicated_count"]
        ),
        denotation_candidate_table_sha256=(
            payload["denotation_candidate_table_sha256"]
        ),
        denotation_start_occurrence_row_count=(
            payload["denotation_start_occurrence_row_count"]
        ),
        denotation_start_occurrence_byte_count=(
            payload["denotation_start_occurrence_byte_count"]
        ),
        denotation_start_occurrence_sha256=(
            payload["denotation_start_occurrence_sha256"]
        ),
        denotation_start_partition_rows=tuple(
            (row["adjudication"], row["occurrence_count"])
            for row in payload["denotation_start_partition_rows"]
        ),
        segment_start_authority_row_count=(
            payload["segment_start_authority_row_count"]
        ),
        segment_start_authority_start_count=(
            payload["segment_start_authority_start_count"]
        ),
        segment_start_authority_relation_byte_count=len(
            build.segment_start_authority_relation_bytes
        ),
        segment_start_authority_relation_sha256=hashlib.sha256(
            build.segment_start_authority_relation_bytes
        ).hexdigest(),
        segment_start_authority_array_sha256=(
            payload["segment_start_authority_array_sha256"]
        ),
        coding_start_authority_row_count=(
            payload["coding_start_authority_row_count"]
        ),
        coding_start_authority_relation_byte_count=len(
            build.coding_start_authority_relation_bytes
        ),
        coding_start_authority_relation_sha256=hashlib.sha256(
            build.coding_start_authority_relation_bytes
        ).hexdigest(),
        coding_start_authority_array_sha256=(
            payload["coding_start_authority_array_sha256"]
        ),
        title_start_authority_row_count=(
            payload["title_start_authority_row_count"]
        ),
        title_start_authority_relation_byte_count=len(
            build.title_start_authority_relation_bytes
        ),
        title_start_authority_relation_sha256=hashlib.sha256(
            build.title_start_authority_relation_bytes
        ).hexdigest(),
        title_start_authority_array_sha256=(
            payload["title_start_authority_array_sha256"]
        ),
        anchor_relation_row_count=len(build.anchor_rows),
        anchor_relation_byte_count=len(build.anchor_relation_bytes),
        anchor_relation_sha256=hashlib.sha256(
            build.anchor_relation_bytes
        ).hexdigest(),
        anchor_relation_array_sha256=canonical_sha256(build.anchor_rows),
        clause_relation_row_count=len(build.clause_rows),
        clause_relation_byte_count=len(build.clause_relation_bytes),
        clause_relation_sha256=hashlib.sha256(
            build.clause_relation_bytes
        ).hexdigest(),
        clause_relation_array_sha256=canonical_sha256(build.clause_rows),
        title_literal_relation_row_count=(
            payload["title_literal_relation_row_count"]
        ),
        title_literal_relation_byte_count=len(
            build.title_literal_relation_bytes
        ),
        title_literal_relation_sha256=hashlib.sha256(
            build.title_literal_relation_bytes
        ).hexdigest(),
        title_literal_relation_array_sha256=(
            payload["title_literal_relation_array_sha256"]
        ),
        title_generic_relation_array_sha256=(
            payload["title_generic_relation_array_sha256"]
        ),
        title_generic_relation_byte_count=len(
            build.title_generic_relation_bytes
        ),
        title_generic_relation_row_count=(
            payload["title_generic_relation_row_count"]
        ),
        title_generic_relation_sha256=hashlib.sha256(
            build.title_generic_relation_bytes
        ).hexdigest(),
        predicate_authority_row_count=payload["predicate_authority_row_count"],
        predicate_authority_relation_byte_count=len(
            build.predicate_authority_relation_bytes
        ),
        predicate_authority_relation_sha256=hashlib.sha256(
            build.predicate_authority_relation_bytes
        ).hexdigest(),
        predicate_authority_sha256=payload["predicate_authority_sha256"],
        predicate_authority_partition_rows=_predicate_authority_partition(
            build.predicate_authority_rows
        ),
        statement_table_row_count=payload["statement_table_row_count"],
        statement_table_sha256=payload["statement_table_sha256"],
        unit_bearing_statement_count=payload["unit_bearing_statement_count"],
        unit_bearing_relation_byte_count=len(unit_bytes),
        unit_bearing_relation_sha256=hashlib.sha256(unit_bytes).hexdigest(),
        unit_bearing_relation_array_sha256=canonical_sha256(
            build.unit_bearing_rows
        ),
        census_payload_sha256=payload["census_sha256"],
    )


def _require_equal(label: str, observed: Any, expected: Any) -> None:
    if observed != expected:
        observed_text = repr(observed)
        expected_text = repr(expected)
        if len(observed_text) > 240:
            observed_text = observed_text[:237] + "..."
        if len(expected_text) > 240:
            expected_text = expected_text[:237] + "..."
        raise GateError(
            f"{label} mismatch: observed {observed_text}; "
            f"expected {expected_text}"
        )


def _validate_movement_invariants(payload: Mapping[str, Any]) -> None:
    seen: set[tuple[int, str]] = set()
    for position, row in enumerate(payload["movement_rows"]):
        if type(row) is not dict or tuple(sorted(row)) != MOVEMENT_KEYS:
            raise GateError(f"movement row {position}: noncanonical shape")
        key = (row["interview_wave"], row["raw_field_id"])
        if key in seen:
            raise GateError(f"movement row {position}: duplicate key {key!r}")
        seen.add(key)
        if row["ratified_status"] not in COMPILED_TERMINALS:
            raise GateError(
                f"movement row {position}: ratified status is not compiled"
            )
        if row["successor_status"] != INCOMPLETE:
            raise GateError(
                f"movement row {position}: successor is not {INCOMPLETE!r}"
            )
        if row["resolution_reason"] != UNIT_ABSENT_RESOLUTION_REASON:
            raise GateError(
                f"movement row {position}: wrong resolution reason"
            )


def _validate_failure_shapes(payload: Mapping[str, Any]) -> None:
    for position, row in enumerate(payload["failure_reason_rows"]):
        if type(row) is not dict or tuple(sorted(row)) != FAILURE_REASON_KEYS:
            raise GateError(
                f"failure-reason row {position}: noncanonical shape"
            )
        if type(row["field_keys"]) is not list:
            raise GateError(f"failure-reason row {position}: non-array keys")


def validate_a10_r04(build: CensusBuild, pins: GatePins) -> None:
    """Apply every A10-R04 equality; raise before any caller may emit."""

    payload = build.payload

    # Step 1: exact input relation and row count.
    _require_equal(
        "input relation row count",
        payload["input_relation_row_count"],
        pins.input_relation_row_count,
    )
    _require_equal(
        "input relation digest",
        payload["input_relation_sha256"],
        pins.input_relation_sha256,
    )

    # Step 2: denominator identity (also detects field-key reordering).
    _require_equal(
        "denominator digest",
        payload["denominator_sha256"],
        pins.denominator_sha256,
    )
    _require_equal(
        "census field count",
        payload["field_count"],
        pins.input_relation_row_count,
    )
    _require_equal(
        "ratified input count rows",
        tuple(
            (row["derivation_status"], row["field_count"])
            for row in payload["ratified_count_rows"]
        ),
        pins.ratified_count_rows,
    )

    # Step 3: complete successor census and ordered assignment.
    _require_equal(
        "successor count rows",
        _count_projection(payload),
        pins.count_rows,
    )
    _require_equal(
        "successor count-array digest",
        payload["count_array_sha256"],
        pins.count_array_sha256,
    )
    _require_equal(
        "ordered assignment digest",
        payload["ordered_assignment_sha256"],
        pins.ordered_assignment_sha256,
    )

    # Step 4: all matrix cells and every per-status field-key digest.
    _require_equal(
        "status-by-artifact matrix",
        _matrix_projection(payload),
        pins.status_matrix_rows,
    )

    # Step 5: full movement relation, key projection, and closed terminals.
    _validate_movement_invariants(payload)
    _require_equal(
        "movement row count",
        payload["movement_row_count"],
        pins.movement_row_count,
    )
    _require_equal(
        "movement relation digest",
        payload["movement_rows_sha256"],
        pins.movement_rows_sha256,
    )
    _require_equal(
        "movement key digest",
        payload["movement_key_sha256"],
        pins.movement_key_sha256,
    )

    # Step 6: complete failure artifact plus inherited literal/count rows.
    _validate_failure_shapes(payload)
    _require_equal(
        "failure-reason rows",
        _failure_projection(payload),
        pins.failure_reason_rows,
    )
    _require_equal(
        "failure-reason row count",
        payload["failure_reason_row_count"],
        pins.failure_reason_row_count,
    )
    _require_equal(
        "failure-reason byte count",
        payload["failure_reason_rows_byte_count"],
        pins.failure_reason_rows_byte_count,
    )
    _require_equal(
        "failure-reason digest",
        payload["failure_reason_rows_sha256"],
        pins.failure_reason_rows_sha256,
    )

    # Step 7: exhaustive source audit.  The normalized relation dispositions
    # every U+0020 word start; the independent Actual and coding relations
    # cover starts whose raw spelling or punctuation is material to the law.
    _require_equal(
        "Actual candidate table row count",
        payload["actual_candidate_table_row_count"],
        pins.actual_candidate_table_row_count,
    )
    _require_equal(
        "Actual candidate occurrence count",
        payload["actual_candidate_occurrence_count"],
        pins.actual_candidate_occurrence_count,
    )
    _require_equal(
        "unadjudicated Actual candidate count",
        payload["actual_candidate_unadjudicated_count"],
        pins.actual_candidate_unadjudicated_count,
    )
    if payload["actual_candidate_unadjudicated_count"] != 0:
        raise GateError("unadjudicated raw Actual candidates remain")
    _require_equal(
        "Actual candidate table digest",
        payload["actual_candidate_table_sha256"],
        pins.actual_candidate_table_sha256,
    )
    _require_equal(
        "coding candidate table row count",
        payload["coding_candidate_table_row_count"],
        pins.coding_candidate_table_row_count,
    )
    _require_equal(
        "coding candidate occurrence count",
        payload["coding_candidate_occurrence_count"],
        pins.coding_candidate_occurrence_count,
    )
    _require_equal(
        "unadjudicated coding candidate count",
        payload["coding_candidate_unadjudicated_count"],
        pins.coding_candidate_unadjudicated_count,
    )
    if payload["coding_candidate_unadjudicated_count"] != 0:
        raise GateError("unadjudicated raw coding starts remain")
    _require_equal(
        "coding candidate table digest",
        payload["coding_candidate_table_sha256"],
        pins.coding_candidate_table_sha256,
    )
    title_bytes = build.title_header_candidate_relation_bytes
    _require_equal(
        "title/header candidate table row count",
        payload["title_header_candidate_table_row_count"],
        pins.title_header_candidate_table_row_count,
    )
    _require_equal(
        "title/header table versus denominator rows",
        payload["title_header_candidate_table_row_count"],
        payload["input_relation_row_count"],
    )
    _require_equal(
        "title/header matched field count",
        payload["title_header_matched_field_count"],
        pins.title_header_matched_field_count,
    )
    _require_equal(
        "title/header candidate occurrence count",
        payload["title_header_candidate_occurrence_count"],
        pins.title_header_candidate_occurrence_count,
    )
    _require_equal(
        "positive title/header start count",
        payload["title_header_positive_start_count"],
        pins.title_header_positive_start_count,
    )
    _require_equal(
        "defeated title/header start count",
        payload["title_header_defeated_start_count"],
        pins.title_header_defeated_start_count,
    )
    _require_equal(
        "unadjudicated title/header start count",
        payload["title_header_unadjudicated_start_count"],
        pins.title_header_unadjudicated_start_count,
    )
    _require_equal(
        "title/header start exact cover",
        payload["title_header_positive_start_count"]
        + payload["title_header_defeated_start_count"]
        + payload["title_header_unadjudicated_start_count"],
        payload["title_header_candidate_occurrence_count"],
    )
    if payload["title_header_unadjudicated_start_count"] != 0:
        raise GateError("unadjudicated title/header starts remain")
    _require_equal(
        "positive title/header field count",
        payload["title_header_positive_field_count"],
        pins.title_header_positive_field_count,
    )
    _require_equal(
        "defeat-only title/header field count",
        payload["title_header_defeat_field_count"],
        pins.title_header_defeat_field_count,
    )
    _require_equal(
        "no-match title/header field count",
        payload["title_header_no_match_field_count"],
        pins.title_header_no_match_field_count,
    )
    _require_equal(
        "title/header field disposition exact cover",
        payload["title_header_positive_field_count"]
        + payload["title_header_defeat_field_count"]
        + payload["title_header_no_match_field_count"],
        payload["title_header_candidate_table_row_count"],
    )
    _require_equal(
        "title/header matched-field arithmetic",
        payload["title_header_positive_field_count"]
        + payload["title_header_defeat_field_count"],
        payload["title_header_matched_field_count"],
    )
    _require_equal(
        "title/header candidate table relation byte count",
        len(title_bytes),
        pins.title_header_candidate_table_relation_byte_count,
    )
    _require_equal(
        "title/header candidate table relation digest",
        hashlib.sha256(title_bytes).hexdigest(),
        pins.title_header_candidate_table_relation_sha256,
    )
    _require_equal(
        "title/header candidate table canonical-array digest",
        payload["title_header_candidate_table_array_sha256"],
        pins.title_header_candidate_table_array_sha256,
    )
    _require_equal(
        "denotation candidate table row count",
        payload["denotation_candidate_table_row_count"],
        pins.denotation_candidate_table_row_count,
    )
    _require_equal(
        "denotation candidate occurrence count",
        payload["denotation_candidate_occurrence_count"],
        pins.denotation_candidate_occurrence_count,
    )
    _require_equal(
        "universal statement-candidate start count",
        payload["denotation_candidate_start_count"],
        pins.denotation_candidate_start_count,
    )
    _require_equal(
        "distinct denotation candidate text count",
        payload["denotation_candidate_distinct_text_count"],
        pins.denotation_candidate_distinct_text_count,
    )
    _require_equal(
        "distinct denotation-plus-Actual candidate text count",
        payload["denotation_candidate_plus_actual_distinct_text_count"],
        pins.denotation_candidate_plus_actual_distinct_text_count,
    )
    _require_equal(
        "total denotation candidate occurrence count",
        payload["denotation_candidate_total_occurrence_count"],
        pins.denotation_candidate_total_occurrence_count,
    )
    _require_equal(
        "candidate occurrence sum versus universal starts",
        payload["denotation_candidate_occurrence_count"],
        payload["denotation_candidate_start_count"],
    )
    _require_equal(
        "total occurrence arithmetic",
        payload["denotation_candidate_total_occurrence_count"],
        payload["denotation_candidate_occurrence_count"]
        + payload["actual_candidate_occurrence_count"],
    )
    _require_equal(
        "whole-domain candidates missed by production selectors",
        payload["denotation_candidate_unselected_count"],
        pins.denotation_candidate_unselected_count,
    )
    if payload["denotation_candidate_unselected_count"] != 0:
        raise GateError(
            "a whole-domain candidate escaped production selection"
        )
    _require_equal(
        "production selections lacking whole-domain authority",
        payload["denotation_candidate_overselected_count"],
        pins.denotation_candidate_overselected_count,
    )
    if payload["denotation_candidate_overselected_count"] != 0:
        raise GateError("production selected a non-whole-domain start")
    _require_equal(
        "unadjudicated denotation candidate count",
        payload["denotation_candidate_unadjudicated_count"],
        pins.denotation_candidate_unadjudicated_count,
    )
    if payload["denotation_candidate_unadjudicated_count"] != 0:
        raise GateError("unadjudicated denotation candidates remain")
    _require_equal(
        "denotation candidate table digest",
        payload["denotation_candidate_table_sha256"],
        pins.denotation_candidate_table_sha256,
    )
    _require_equal(
        "ordered start-occurrence row count",
        payload["denotation_start_occurrence_row_count"],
        pins.denotation_start_occurrence_row_count,
    )
    _require_equal(
        "ordered start-occurrence byte count",
        payload["denotation_start_occurrence_byte_count"],
        pins.denotation_start_occurrence_byte_count,
    )
    _require_equal(
        "ordered start-occurrence digest",
        payload["denotation_start_occurrence_sha256"],
        pins.denotation_start_occurrence_sha256,
    )
    start_partition = tuple(
        (row["adjudication"], row["occurrence_count"])
        for row in payload["denotation_start_partition_rows"]
    )
    _require_equal(
        "start-occurrence disposition partition",
        start_partition,
        pins.denotation_start_partition_rows,
    )
    _require_equal(
        "start-occurrence exact cover",
        sum(count for _disposition, count in start_partition),
        payload["denotation_start_occurrence_row_count"],
    )
    _require_equal(
        "materialized starts versus ordered start occurrences",
        payload["denotation_candidate_start_count"],
        payload["denotation_start_occurrence_row_count"],
    )

    # Step 8: exact cleartext semantic authorities, complete statement table,
    # and both forms of the positive fence.  The raw JSONL pins bind the
    # displayed fences byte for byte; canonical-array pins independently bind
    # row order and membership.
    title_authority_bytes = build.title_start_authority_relation_bytes
    _validate_title_start_authority(
        build.title_start_authority_rows,
        build.field_rows,
    )
    _require_equal(
        "title-start authority row count",
        payload["title_start_authority_row_count"],
        pins.title_start_authority_row_count,
    )
    _require_equal(
        "title-start authority relation byte count",
        len(title_authority_bytes),
        pins.title_start_authority_relation_byte_count,
    )
    _require_equal(
        "title-start authority relation digest",
        hashlib.sha256(title_authority_bytes).hexdigest(),
        pins.title_start_authority_relation_sha256,
    )
    _require_equal(
        "title-start authority canonical-array digest",
        payload["title_start_authority_array_sha256"],
        pins.title_start_authority_array_sha256,
    )
    segment_bytes = build.segment_start_authority_relation_bytes
    _require_equal(
        "segment/start authority row count",
        payload["segment_start_authority_row_count"],
        pins.segment_start_authority_row_count,
    )
    _require_equal(
        "segment/start authority start count",
        payload["segment_start_authority_start_count"],
        pins.segment_start_authority_start_count,
    )
    _require_equal(
        "segment/start authority versus candidate-table rows",
        payload["segment_start_authority_start_count"],
        payload["denotation_candidate_table_row_count"],
    )
    _require_equal(
        "segment/start authority relation byte count",
        len(segment_bytes),
        pins.segment_start_authority_relation_byte_count,
    )
    _require_equal(
        "segment/start authority relation digest",
        hashlib.sha256(segment_bytes).hexdigest(),
        pins.segment_start_authority_relation_sha256,
    )
    _require_equal(
        "segment/start authority canonical-array digest",
        payload["segment_start_authority_array_sha256"],
        pins.segment_start_authority_array_sha256,
    )
    coding_bytes = build.coding_start_authority_relation_bytes
    _require_equal(
        "coding-start authority row count",
        payload["coding_start_authority_row_count"],
        pins.coding_start_authority_row_count,
    )
    _require_equal(
        "coding candidate/authority exact row cover",
        payload["coding_candidate_table_row_count"],
        payload["coding_start_authority_row_count"],
    )
    _require_equal(
        "coding-start authority relation byte count",
        len(coding_bytes),
        pins.coding_start_authority_relation_byte_count,
    )
    _require_equal(
        "coding-start authority relation digest",
        hashlib.sha256(coding_bytes).hexdigest(),
        pins.coding_start_authority_relation_sha256,
    )
    _require_equal(
        "coding-start authority canonical-array digest",
        payload["coding_start_authority_array_sha256"],
        pins.coding_start_authority_array_sha256,
    )
    anchor_bytes = build.anchor_relation_bytes
    _require_equal(
        "anchor relation row count",
        len(build.anchor_rows),
        pins.anchor_relation_row_count,
    )
    _require_equal(
        "anchor relation byte count",
        len(anchor_bytes),
        pins.anchor_relation_byte_count,
    )
    _require_equal(
        "anchor relation digest",
        hashlib.sha256(anchor_bytes).hexdigest(),
        pins.anchor_relation_sha256,
    )
    _require_equal(
        "anchor relation canonical-array digest",
        canonical_sha256(build.anchor_rows),
        pins.anchor_relation_array_sha256,
    )
    clause_bytes = build.clause_relation_bytes
    _require_equal(
        "clause relation row count",
        len(build.clause_rows),
        pins.clause_relation_row_count,
    )
    _require_equal(
        "clause relation byte count",
        len(clause_bytes),
        pins.clause_relation_byte_count,
    )
    _require_equal(
        "clause relation digest",
        hashlib.sha256(clause_bytes).hexdigest(),
        pins.clause_relation_sha256,
    )
    _require_equal(
        "clause relation canonical-array digest",
        canonical_sha256(build.clause_rows),
        pins.clause_relation_array_sha256,
    )
    title_literal_bytes = build.title_literal_relation_bytes
    _require_equal(
        "title-literal relation row count",
        payload["title_literal_relation_row_count"],
        pins.title_literal_relation_row_count,
    )
    _require_equal(
        "title-literal materialized row count",
        len(build.title_literal_rows),
        payload["title_literal_relation_row_count"],
    )
    _require_equal(
        "title-literal relation byte count",
        payload["title_literal_relation_byte_count"],
        pins.title_literal_relation_byte_count,
    )
    _require_equal(
        "title-literal materialized byte count",
        len(title_literal_bytes),
        payload["title_literal_relation_byte_count"],
    )
    _require_equal(
        "title-literal relation digest",
        payload["title_literal_relation_sha256"],
        pins.title_literal_relation_sha256,
    )
    _require_equal(
        "title-literal materialized relation digest",
        hashlib.sha256(title_literal_bytes).hexdigest(),
        payload["title_literal_relation_sha256"],
    )
    _require_equal(
        "title-literal relation canonical-array digest",
        payload["title_literal_relation_array_sha256"],
        pins.title_literal_relation_array_sha256,
    )
    _require_equal(
        "title-literal materialized canonical-array digest",
        canonical_sha256(build.title_literal_rows),
        payload["title_literal_relation_array_sha256"],
    )
    title_generic_bytes = build.title_generic_relation_bytes
    _require_equal(
        "title-generic relation row count",
        payload["title_generic_relation_row_count"],
        pins.title_generic_relation_row_count,
    )
    _require_equal(
        "title-generic materialized row count",
        len(build.title_generic_rows),
        payload["title_generic_relation_row_count"],
    )
    _require_equal(
        "title-generic relation byte count",
        payload["title_generic_relation_byte_count"],
        pins.title_generic_relation_byte_count,
    )
    _require_equal(
        "title-generic materialized byte count",
        len(title_generic_bytes),
        payload["title_generic_relation_byte_count"],
    )
    _require_equal(
        "title-generic relation digest",
        payload["title_generic_relation_sha256"],
        pins.title_generic_relation_sha256,
    )
    _require_equal(
        "title-generic materialized relation digest",
        hashlib.sha256(title_generic_bytes).hexdigest(),
        payload["title_generic_relation_sha256"],
    )
    _require_equal(
        "title-generic relation canonical-array digest",
        payload["title_generic_relation_array_sha256"],
        pins.title_generic_relation_array_sha256,
    )
    _require_equal(
        "title-generic materialized canonical-array digest",
        canonical_sha256(build.title_generic_rows),
        payload["title_generic_relation_array_sha256"],
    )
    predicate_bytes = build.predicate_authority_relation_bytes
    _require_equal(
        "predicate-authority row count",
        payload["predicate_authority_row_count"],
        pins.predicate_authority_row_count,
    )
    _require_equal(
        "predicate-authority relation byte count",
        len(predicate_bytes),
        pins.predicate_authority_relation_byte_count,
    )
    _require_equal(
        "predicate-authority relation digest",
        hashlib.sha256(predicate_bytes).hexdigest(),
        pins.predicate_authority_relation_sha256,
    )
    _require_equal(
        "predicate-authority canonical-array digest",
        payload["predicate_authority_sha256"],
        pins.predicate_authority_sha256,
    )
    _require_equal(
        "predicate-authority four-way partition",
        _predicate_authority_partition(build.predicate_authority_rows),
        pins.predicate_authority_partition_rows,
    )
    unit_bytes = build.unit_bearing_relation_bytes
    _require_equal(
        "statement-table row count",
        payload["statement_table_row_count"],
        pins.statement_table_row_count,
    )
    _require_equal(
        "statement-table digest",
        payload["statement_table_sha256"],
        pins.statement_table_sha256,
    )
    _require_equal(
        "unit-bearing statement count",
        payload["unit_bearing_statement_count"],
        pins.unit_bearing_statement_count,
    )
    _require_equal(
        "unit-bearing relation byte count",
        len(unit_bytes),
        pins.unit_bearing_relation_byte_count,
    )
    _require_equal(
        "unit-bearing relation digest",
        hashlib.sha256(unit_bytes).hexdigest(),
        pins.unit_bearing_relation_sha256,
    )
    _require_equal(
        "unit-bearing canonical-array digest",
        canonical_sha256(build.unit_bearing_rows),
        pins.unit_bearing_relation_array_sha256,
    )

    # Step 9: the complete payload pin (computed before adding its own member).
    _require_equal(
        "census payload digest",
        payload["census_sha256"],
        pins.census_payload_sha256,
    )


def _resolved(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError as error:
        raise GateError(f"cannot resolve path {path}: {error}") from error


def _validate_output_paths(
    field_rows: Path,
    output: Path | None,
    statements: Path | None,
    titles: Path | None,
) -> None:
    named = [("field rows", field_rows)]
    if output is not None:
        named.append(("output", output))
    if statements is not None:
        named.append(("statements", statements))
    if titles is not None:
        named.append(("titles", titles))
    resolved: dict[Path, str] = {}
    inodes: dict[tuple[int, int], str] = {}
    for label, path in named:
        target = _resolved(path)
        if target in resolved:
            raise GateError(
                f"path collision: {label} aliases "
                f"{resolved[target]} ({target})"
            )
        resolved[target] = label
        try:
            stat = target.stat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise GateError(
                f"cannot inspect path {target}: {error}"
            ) from error
        inode = (stat.st_dev, stat.st_ino)
        if inode in inodes:
            raise GateError(
                f"path collision: {label} is a hard link to {inodes[inode]}"
            )
        inodes[inode] = label


def _stage_output(label: str, destination: Path, content: bytes) -> Path:
    """Write and validate one same-filesystem staging file."""

    descriptor = -1
    staged: Path | None = None
    staged_is_valid = False
    try:
        descriptor, raw_path = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.a10-r04-stage-",
        )
        staged = Path(raw_path)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        digest = hashlib.sha256()
        byte_count = 0
        with staged.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                byte_count += len(chunk)
                digest.update(chunk)
        expected_digest = hashlib.sha256(content).hexdigest()
        if byte_count != len(content) or digest.hexdigest() != expected_digest:
            raise GateError(f"staged {label} failed byte validation")
        staged_is_valid = True
        return staged
    except GateError:
        raise
    except OSError as error:
        raise GateError(
            f"cannot stage {label} at {destination}: {error}"
        ) from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if staged is not None and not staged_is_valid:
            try:
                staged.unlink()
            except OSError:
                pass


@dataclass(frozen=True)
class _DestinationBackup:
    """Stable rollback state for one destination."""

    label: str
    destination: Path
    path: Path | None
    original_identity: tuple[int, int] | None


def _lstat_identity(path: Path) -> tuple[int, int]:
    status = os.lstat(path)
    return status.st_dev, status.st_ino


def _backup_destination(label: str, destination: Path) -> _DestinationBackup:
    """Hard-link an existing destination so rollback preserves its bytes."""

    try:
        original_identity = _lstat_identity(destination)
    except FileNotFoundError:
        return _DestinationBackup(label, destination, None, None)
    except OSError as error:
        raise GateError(
            f"cannot inspect {label} at {destination}: {error}"
        ) from error
    descriptor = -1
    backup: Path | None = None
    backup_is_valid = False
    try:
        descriptor, raw_path = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.a10-r04-backup-",
        )
        os.close(descriptor)
        descriptor = -1
        backup = Path(raw_path)
        backup.unlink()
        os.link(destination, backup, follow_symlinks=False)
        if _lstat_identity(backup) != original_identity:
            raise OSError("backup identity changed while linking")
        backup_is_valid = True
        return _DestinationBackup(
            label,
            destination,
            backup,
            original_identity,
        )
    except OSError as error:
        raise GateError(
            f"cannot back up {label} at {destination}: {error}"
        ) from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if backup is not None and not backup_is_valid:
            try:
                backup.unlink()
            except OSError:
                pass


def _discard_temporary(path: Path) -> None:
    """Best-effort cleanup that cannot turn a completed commit into failure."""

    try:
        path.unlink()
    except OSError:
        pass


def _destination_is_restored(backup: _DestinationBackup) -> bool:
    """Verify restoration by the original lstat identity or nonexistence."""

    try:
        identity = _lstat_identity(backup.destination)
    except FileNotFoundError:
        identity = None
    return identity == backup.original_identity


def _fresh_restore_source(backup: _DestinationBackup) -> Path:
    """Link a disposable restore source without consuming the stable backup."""

    assert backup.path is not None
    descriptor = -1
    restore: Path | None = None
    restore_is_valid = False
    try:
        descriptor, raw_path = tempfile.mkstemp(
            dir=backup.destination.parent,
            prefix=f".{backup.destination.name}.a10-r04-restore-",
        )
        os.close(descriptor)
        descriptor = -1
        restore = Path(raw_path)
        restore.unlink()
        os.link(backup.path, restore, follow_symlinks=False)
        if _lstat_identity(restore) != backup.original_identity:
            raise OSError("restore-source identity differs from backup")
        restore_is_valid = True
        return restore
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if restore is not None and not restore_is_valid:
            _discard_temporary(restore)


def _restore_destination(backup: _DestinationBackup) -> str | None:
    """Retry once and verify after both before- and after-effect errors."""

    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            if _destination_is_restored(backup):
                return None
        except OSError as error:
            last_error = error
        restore_source: Path | None = None
        try:
            if backup.path is None:
                backup.destination.unlink()
            else:
                restore_source = _fresh_restore_source(backup)
                os.replace(restore_source, backup.destination)
        except Exception as error:
            last_error = error
        finally:
            if restore_source is not None:
                _discard_temporary(restore_source)
        try:
            if _destination_is_restored(backup):
                # A raised operation that nevertheless reached this state was
                # an after-effect error. No retry is necessary.
                return None
        except OSError as error:
            last_error = error
    detail = (
        str(last_error)
        if last_error is not None
        else "destination identity did not return to its original state"
    )
    if backup.path is not None:
        return f"{backup.label}: {detail}; backup preserved at {backup.path}"
    return f"{backup.label}: {detail}; originally absent destination remains"


def _replacement_effect(
    staged_identity: tuple[int, int],
    backup: _DestinationBackup,
) -> str:
    """Classify a raised replacement as before-, after-, or unknown-effect."""

    try:
        destination_identity = _lstat_identity(backup.destination)
    except FileNotFoundError:
        destination_identity = None
    except OSError:
        return "indeterminate-effect"
    if destination_identity == staged_identity:
        return "after-effect"
    if destination_identity == backup.original_identity:
        return "before-effect"
    return "indeterminate-effect"


def _emit_outputs_transactionally(
    outputs: Sequence[tuple[str, Path, bytes]],
) -> None:
    """Commit all requested files or restore every prior destination.

    Every new file is staged and byte-validated in its destination directory
    before any destination changes. Existing destinations are retained by
    hard link. If any atomic replacement raises, restoration uses disposable
    links so the stable backup survives every failed attempt. Verification
    distinguishes before-effect errors, which are retried once, from
    after-effect errors, whose completed restoration is accepted. Any
    unresolved backup is preserved and named in the raised ``GateError``.
    """

    if not outputs:
        return
    staged: list[tuple[str, Path, Path, tuple[int, int]]] = []
    backups: list[_DestinationBackup] = []
    # Stable backups are protected by default. A path becomes disposable only
    # after the whole commit succeeds or its destination is verified restored.
    # An exception outside the declared ``Exception`` failure model therefore
    # cannot make the cleanup path erase unresolved recovery material.
    discardable_backups: set[Path] = set()
    try:
        for label, destination, content in outputs:
            staged_path = _stage_output(label, destination, content)
            staged.append(
                (
                    label,
                    destination,
                    staged_path,
                    _lstat_identity(staged_path),
                )
            )
        for label, destination, _staged_path, _staged_identity in staged:
            backups.append(_backup_destination(label, destination))
        for (
            label,
            destination,
            staged_path,
            staged_identity,
        ), backup in zip(staged, backups, strict=True):
            try:
                os.replace(staged_path, destination)
            except Exception as commit_error:
                commit_effect = _replacement_effect(staged_identity, backup)
                rollback_errors: list[str] = []
                for prior in backups:
                    rollback_error = _restore_destination(prior)
                    if rollback_error is None:
                        if prior.path is not None:
                            discardable_backups.add(prior.path)
                        continue
                    rollback_errors.append(rollback_error)
                commit_context = f"{commit_effect} replacement for {label}"
                if rollback_errors:
                    joined = "; ".join(rollback_errors)
                    raise GateError(
                        "output transaction failed and rollback remains "
                        f"incomplete after {commit_context}: {joined}"
                    ) from commit_error
                raise GateError(
                    "output transaction failed; prior destinations restored "
                    f"after {commit_context}: {commit_error}"
                ) from commit_error
        discardable_backups.update(
            backup.path for backup in backups if backup.path is not None
        )
    finally:
        for _label, _destination, staged_path, _staged_identity in staged:
            _discard_temporary(staged_path)
        for backup in backups:
            if backup.path in discardable_backups:
                assert backup.path is not None
                _discard_temporary(backup.path)


def execute_gate(
    field_rows: Path,
    *,
    output: Path | None = None,
    statements: Path | None = None,
    titles: Path | None = None,
    pins: GatePins | None = None,
) -> CensusBuild:
    """Read once, build, validate fully, and only then emit requested files."""

    _validate_output_paths(field_rows, output, statements, titles)
    expected = EXPECTED_A10_R04_PINS if pins is None else pins
    if expected is None:
        raise GateError("A10-R04 production pins have not been finalized")
    rows = read_field_rows(field_rows)
    build = build_payload(rows)
    try:
        validate_a10_r04(build, expected)
    except GateError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise GateError(f"gate validation failed: {error}") from error

    # All output bytes are prepared only after the final gate equality.
    statement_bytes = b"".join(
        canonical_json_bytes(row) for row in build.statement_rows
    )
    payload_bytes = (
        json.dumps(
            build.payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )
    requested_outputs: list[tuple[str, Path, bytes]] = []
    if statements is not None:
        requested_outputs.append(("statements", statements, statement_bytes))
    if titles is not None:
        requested_outputs.append(
            (
                "titles",
                titles,
                build.title_header_candidate_relation_bytes,
            )
        )
    if output is not None:
        requested_outputs.append(("output", output, payload_bytes))
    _emit_outputs_transactionally(requested_outputs)
    return build


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field-rows", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--statements",
        type=Path,
        help="write the complete statement table as canonical JSON lines",
    )
    parser.add_argument(
        "--titles",
        type=Path,
        help="write the complete per-field title audit as canonical JSON lines",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        build = execute_gate(
            arguments.field_rows,
            output=arguments.output,
            statements=arguments.statements,
            titles=arguments.titles,
        )
    except GateError as error:
        print(f"A10-R04 abort: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            build.payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
