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
        --field-rows <path.jsonl> [--output <path.json>] [--statements <path>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from populace_dynamics.data.psid_unit_authority import (  # noqa: E402
    COMPILED_TERMINALS,
    INCOMPLETE,
    UNIT_ABSENT_RESOLUTION_REASON,
    actual_candidate_table,
    canonical_json_bytes,
    canonical_sha256,
    denotation_candidate_table,
    denotation_candidate_start_count,
    denotation_candidate_unselected_count,
    statement_table,
    successor_census,
)
from populace_dynamics.data.psid_unit_predicate_authority import (  # noqa: E402
    EXPLICIT_NO_DENOTATION_CANDIDATE_HASHES,
    PREDICATE_AUTHORITY,
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
    actual_candidate_table_sha256: str
    denotation_candidate_table_row_count: int
    denotation_candidate_occurrence_count: int
    denotation_candidate_start_count: int
    denotation_candidate_unselected_count: int
    denotation_candidate_unadjudicated_count: int
    denotation_candidate_table_sha256: str
    predicate_authority_row_count: int
    predicate_authority_sha256: str
    explicit_no_denotation_candidate_count: int
    explicit_no_denotation_candidate_sha256: str
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
    denotation_candidate_rows: tuple[dict[str, Any], ...]
    statement_rows: tuple[dict[str, Any], ...]
    unit_bearing_rows: tuple[tuple[Any, ...], ...]
    unit_bearing_relation_bytes: bytes
    payload: dict[str, Any]


# The completed round-1 relation.  These are authority, never observations
# copied from the current run; ``validate_a10_r04`` compares each independent
# projection before the caller is permitted to emit any byte.
EXPECTED_A10_R04_PINS: GatePins | None = GatePins(
    input_relation_row_count=89_599,
    input_relation_sha256=(
        "11189cf48eae995d999f12a2155a03dc9c9f9f11804c1a732fc451a71a195f19"
    ),
    denominator_sha256=(
        "7e497f20e05cbdad384daece86d4aa08b16587b83cb6290193b6fdc28705b764"
    ),
    ratified_count_rows=(
        ("compiled_source_numeric_grammar", 17_329),
        (
            "compiled_source_numeric_grammar_padding_underdetermined_"
            "exact_replay",
            1_853,
        ),
        (
            "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_"
            "exact_replay",
            674,
        ),
        (
            "compiled_source_numeric_grammar_partial_range_exact_replay",
            47,
        ),
        ("value_code_domain_no_numeric_grammar", 67_316),
        ("value_code_range_physical_rendering_unestablished", 1_145),
        ("nonnumeric_source_field_outside_numeric_grammar", 0),
        ("conflicting_source_numeric_format", 1),
        ("unsupported_source_numeric_format", 421),
        ("incomplete_source_numeric_authority", 813),
    ),
    count_rows=(
        ("compiled_source_numeric_grammar", 4_692),
        (
            "compiled_source_numeric_grammar_padding_underdetermined_"
            "exact_replay",
            170,
        ),
        (
            "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_"
            "exact_replay",
            49,
        ),
        (
            "compiled_source_numeric_grammar_partial_range_exact_replay",
            0,
        ),
        ("value_code_domain_no_numeric_grammar", 67_316),
        ("value_code_range_physical_rendering_unestablished", 1_145),
        ("nonnumeric_source_field_outside_numeric_grammar", 0),
        ("conflicting_source_numeric_format", 1),
        ("unsupported_source_numeric_format", 421),
        ("incomplete_source_numeric_authority", 15_805),
    ),
    count_array_sha256=(
        "4eedf3845787cabb8132b7cec5ac3fc12c81a9da1a9f33fcec340ec954d335da"
    ),
    ordered_assignment_sha256=(
        "a37d958fde17b520913c9ceae8444f89a3b9914a9797ca7b1e8efe2c7ac82bc2"
    ),
    status_matrix_rows=(
        (
            "compiled_source_numeric_grammar",
            (29, 90, 1_613, 1_198, 1_052, 710),
            4_692,
            "78a57200331afb1f281c589dae0d25037e8caa8af5202007f4bf925fa50e4725",
        ),
        (
            "compiled_source_numeric_grammar_padding_underdetermined_"
            "exact_replay",
            (1, 14, 123, 10, 14, 8),
            170,
            "8f07c2ed166464ed35321956d66f738b5518df9ef212ce6ccb32de84b7438ca5",
        ),
        (
            "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_"
            "exact_replay",
            (0, 7, 29, 11, 0, 2),
            49,
            "b24e5e68c6d0bede46d149dd488886dc47f0314b0743e91b404df5ae78fa9b69",
        ),
        (
            "compiled_source_numeric_grammar_partial_range_exact_replay",
            (0, 0, 0, 0, 0, 0),
            0,
            "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
        ),
        (
            "value_code_domain_no_numeric_grammar",
            (2_606, 1_130, 10_064, 11_668, 26_700, 15_148),
            67_316,
            "6ee97ba9db16520c734a21094623376714a468c3148977666f8e107dbd35e05f",
        ),
        (
            "value_code_range_physical_rendering_unestablished",
            (89, 16, 127, 371, 320, 222),
            1_145,
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
            (1_075, 561, 3_667, 2_679, 4_978, 2_845),
            15_805,
            "befdfdbf0a4344e660635969467e373663e5c4d16582f15a4a0b5b98860eddf8",
        ),
    ),
    movement_row_count=14_992,
    movement_rows_sha256=(
        "fb98df0642cba77d674ad828023c6debd4b54643b3ac9b9fbc14ffe328dd344f"
    ),
    movement_key_sha256=(
        "6bcce3db17451c2b73fa97544c6b4804593237de38a481018ba9225d1f67fd2e"
    ),
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
            14_992,
        ),
    ),
    failure_reason_row_count=8,
    failure_reason_rows_byte_count=268_408,
    failure_reason_rows_sha256=(
        "038364e416830c748fb5404a272cf6c9e715094422441d84ff08e2bcea8a4039"
    ),
    actual_candidate_table_row_count=82,
    actual_candidate_occurrence_count=322,
    actual_candidate_table_sha256=(
        "88f5b25a52d8ea524d1e0c19ea90c9e1a8f9d26c1da437511678342abd2e0e5c"
    ),
    denotation_candidate_table_row_count=59_521,
    denotation_candidate_occurrence_count=195_835,
    denotation_candidate_start_count=2_240_669,
    denotation_candidate_unselected_count=0,
    denotation_candidate_unadjudicated_count=0,
    denotation_candidate_table_sha256=(
        "a8a61db0f8b9663a60a493f3c20ea1c4ff2256f060dc22962eeb814b88275d6a"
    ),
    predicate_authority_row_count=2_558,
    predicate_authority_sha256=(
        "482decde64943c421a8e04c556e08c9120bbf427874624152f2d93e057eeabda"
    ),
    explicit_no_denotation_candidate_count=53_255,
    explicit_no_denotation_candidate_sha256=(
        "80e3bf6bbf200c9431a1f9560d8ef268cdc97fe9ede2cedca5f89a374797dde8"
    ),
    statement_table_row_count=3_403,
    statement_table_sha256=(
        "8fe68f479e303b28552d885dbc284c86ff657f496da1eebb4a1feb1228627d25"
    ),
    unit_bearing_statement_count=1_532,
    unit_bearing_relation_byte_count=237_671,
    unit_bearing_relation_sha256=(
        "e21865b6d2c480cc254db9b71cdc4e12151d6a07bc7d17a679e49a155c3ec6a5"
    ),
    unit_bearing_relation_array_sha256=(
        "ba7244b3a7539eb54a81353c52008e709458c8e4b906cf84c41ed4374c91d6b3"
    ),
    census_payload_sha256=(
        "02ea701ef59b8a5b5cacc2c17bedb4e82f4ca63a01b875931d9c889ae9772e5d"
    ),
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


def _unit_bearing_relation_bytes(
    rows: Sequence[Sequence[Any]],
) -> bytes:
    """Serialize the §24.3 fence: one compact three-position row per LF."""

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


def build_payload(field_rows: Sequence[dict[str, Any]]) -> CensusBuild:
    """Construct all census relations without validating or emitting them."""

    frozen_rows = tuple(field_rows)
    try:
        census = successor_census(frozen_rows)
        actual_rows = tuple(actual_candidate_table(frozen_rows))
        candidate_rows = tuple(denotation_candidate_table(frozen_rows))
        table = tuple(statement_table(frozen_rows))
    except (KeyError, TypeError, ValueError) as error:
        raise GateError(f"census construction failed: {error}") from error
    unit_rows = _unit_bearing_relation(table)
    unit_bytes = _unit_bearing_relation_bytes(unit_rows)
    actual_occurrences = sum(row["field_count"] for row in actual_rows)
    candidate_occurrences = sum(
        row["occurrence_count"] for row in candidate_rows
    )
    candidate_starts = sum(
        denotation_candidate_start_count(row["source_description"])
        for row in frozen_rows
    )
    unselected_candidates = sum(
        denotation_candidate_unselected_count(row["source_description"])
        for row in frozen_rows
    )
    unadjudicated = sum(
        row["occurrence_count"]
        for row in candidate_rows
        if row["adjudication"].startswith("unadjudicated")
    )
    payload: dict[str, Any] = {
        "schema_version": "amendment_10_successor_census.v1",
        "input_relation_row_count": len(frozen_rows),
        "input_relation_sha256": input_relation_sha256(frozen_rows),
        "actual_candidate_table_row_count": len(actual_rows),
        "actual_candidate_occurrence_count": actual_occurrences,
        "actual_candidate_table_sha256": canonical_sha256(actual_rows),
        "denotation_candidate_table_row_count": len(candidate_rows),
        "denotation_candidate_occurrence_count": candidate_occurrences,
        "denotation_candidate_start_count": candidate_starts,
        "denotation_candidate_unselected_count": unselected_candidates,
        "denotation_candidate_unadjudicated_count": unadjudicated,
        "denotation_candidate_table_sha256": canonical_sha256(candidate_rows),
        "predicate_authority_row_count": len(PREDICATE_AUTHORITY),
        "predicate_authority_sha256": canonical_sha256(PREDICATE_AUTHORITY),
        "explicit_no_denotation_candidate_count": len(
            EXPLICIT_NO_DENOTATION_CANDIDATE_HASHES
        ),
        "explicit_no_denotation_candidate_sha256": canonical_sha256(
            sorted(EXPLICIT_NO_DENOTATION_CANDIDATE_HASHES)
        ),
        "statement_table_row_count": len(table),
        "statement_table_sha256": canonical_sha256(table),
        "unit_bearing_statement_count": len(unit_rows),
        **census,
    }
    payload["census_sha256"] = canonical_sha256(payload)
    return CensusBuild(
        field_rows=frozen_rows,
        actual_candidate_rows=actual_rows,
        denotation_candidate_rows=candidate_rows,
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
        actual_candidate_table_sha256=(
            payload["actual_candidate_table_sha256"]
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
        denotation_candidate_unselected_count=(
            payload["denotation_candidate_unselected_count"]
        ),
        denotation_candidate_unadjudicated_count=(
            payload["denotation_candidate_unadjudicated_count"]
        ),
        denotation_candidate_table_sha256=(
            payload["denotation_candidate_table_sha256"]
        ),
        predicate_authority_row_count=payload["predicate_authority_row_count"],
        predicate_authority_sha256=payload["predicate_authority_sha256"],
        explicit_no_denotation_candidate_count=(
            payload["explicit_no_denotation_candidate_count"]
        ),
        explicit_no_denotation_candidate_sha256=(
            payload["explicit_no_denotation_candidate_sha256"]
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

    # Step 7: exhaustive source audit and the exact Actual residual.
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
        "Actual candidate table digest",
        payload["actual_candidate_table_sha256"],
        pins.actual_candidate_table_sha256,
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
        "whole-domain candidates missed by production selectors",
        payload["denotation_candidate_unselected_count"],
        pins.denotation_candidate_unselected_count,
    )
    if payload["denotation_candidate_unselected_count"] != 0:
        raise GateError("a whole-domain candidate escaped production selection")
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

    # Step 8: exact semantic registries, complete statement table, and both
    # forms of the positive fence.
    _require_equal(
        "predicate-authority row count",
        payload["predicate_authority_row_count"],
        pins.predicate_authority_row_count,
    )
    _require_equal(
        "predicate-authority digest",
        payload["predicate_authority_sha256"],
        pins.predicate_authority_sha256,
    )
    _require_equal(
        "explicit no-denotation candidate count",
        payload["explicit_no_denotation_candidate_count"],
        pins.explicit_no_denotation_candidate_count,
    )
    _require_equal(
        "explicit no-denotation candidate digest",
        payload["explicit_no_denotation_candidate_sha256"],
        pins.explicit_no_denotation_candidate_sha256,
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
) -> None:
    named = [("field rows", field_rows)]
    if output is not None:
        named.append(("output", output))
    if statements is not None:
        named.append(("statements", statements))
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


def execute_gate(
    field_rows: Path,
    *,
    output: Path | None = None,
    statements: Path | None = None,
    pins: GatePins | None = None,
) -> CensusBuild:
    """Read once, build, validate fully, and only then emit requested files."""

    _validate_output_paths(field_rows, output, statements)
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
    if statements is not None:
        statements.write_bytes(statement_bytes)
    if output is not None:
        output.write_bytes(payload_bytes)
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        build = execute_gate(
            arguments.field_rows,
            output=arguments.output,
            statements=arguments.statements,
        )
    except GateError as error:
        print(f"A10-R04 abort: {error}", file=sys.stderr)
        return 1
    print(json.dumps(build.payload, indent=2, sort_keys=True)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
