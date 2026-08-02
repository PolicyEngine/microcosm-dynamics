"""Closed-failure guards for physical PSID source consumers.

The complete field-source relation may pass with closed failures, but a
physical consumer may resolve only rows whose derivation status is in T+.
This module implements the row-local boundary in section 21.4 of the covered
earnings correction design.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from copy import deepcopy
from enum import Enum
from typing import Any, TypeVar

PASSING_DERIVATION_STATUSES = (
    "compiled_source_numeric_grammar",
    "compiled_source_numeric_grammar_padding_underdetermined_exact_replay",
    "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_exact_replay",
    "compiled_source_numeric_grammar_partial_range_exact_replay",
    "value_code_domain_no_numeric_grammar",
    "value_code_range_physical_rendering_unestablished",
    "nonnumeric_source_field_outside_numeric_grammar",
)

CLOSED_FAILURE_DERIVATION_STATUSES = (
    "conflicting_source_numeric_format",
    "unsupported_source_numeric_format",
    "incomplete_source_numeric_authority",
)

T_PLUS = frozenset(PASSING_DERIVATION_STATUSES)
T_MINUS = frozenset(CLOSED_FAILURE_DERIVATION_STATUSES)
ALL_DERIVATION_STATUSES = T_PLUS | T_MINUS

CLOSED_FAILURE_RESOLUTION_REASONS = {
    "conflicting_source_numeric_format": frozenset(
        {"conflict:overlapping_numeric_ranges"}
    ),
    "unsupported_source_numeric_format": frozenset(
        {
            "character_raw_replay_unknown_token",
            "observed_token_outside_all_candidate_forms_or_semantics",
            "selected_space_literal_unrenderable",
            "selected_space_range_zero_renderable",
        }
    ),
    "incomplete_source_numeric_authority": frozenset(
        {
            "finite_no_arm_no_lawful_complete_disposition",
            "literal_only_zero_diagnostic_padding_capacity",
        }
    ),
}

NUMERIC_GRAMMAR_DERIVATION_ROW_KEYS = (
    "numeric_grammar_derivation_id",
    "interview_wave",
    "raw_field_id",
    "dictionary_field_row_ids",
    "dictionary_field_rows_sha256",
    "codebook_field_row_ids",
    "codebook_field_rows_sha256",
    "source_format_projection",
    "source_meaning_projection",
    "dictionary_field_meaning",
    "derived_parse_kind",
    "normalized_format_profile",
    "nonmissing_observation_count",
    "derivation_status",
    "padding_rule",
    "registered_numeric_grammar",
)

CLOSED_FAILURE_REFERENCE_ROW_KEYS = (
    "consumer_kind",
    "consumer_row_identity",
    "consumer_reference_position",
    "interview_wave",
    "raw_field_id",
    "numeric_grammar_derivation_id",
    "numeric_grammar_derivation_sha256",
    "derivation_status",
    "resolution_reason",
)


class ConsumerKind(str, Enum):
    """The closed section-21.4 physical-consumer domain."""

    Q5_POSITIVE_FIELD_JOIN = "q5_positive_field_join"
    SLOT_REGISTRY_ROW = "slot_registry_row"
    OFFICIAL_INVENTORY_ROW = "official_inventory_row"
    VALUE_MAP = "value_map"
    CROSSWALK = "crosswalk"
    CORRECTION_INPUT = "correction_input"
    CONTEXT_OUTPUT = "context_output"


CONSUMER_KINDS = tuple(kind.value for kind in ConsumerKind)

V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY = {
    (1976, "V4519"): "literal_only_zero_diagnostic_padding_capacity",
    (1976, "V4902"): "literal_only_zero_diagnostic_padding_capacity",
    (1977, "V5429"): "literal_only_zero_diagnostic_padding_capacity",
    (1978, "V5916"): "literal_only_zero_diagnostic_padding_capacity",
}

FieldKey = tuple[int, str]
JsonObject = dict[str, Any]
Reference = Mapping[str, Any] | Sequence[Any]
ResultT = TypeVar("ResultT")


def canonical_json_bytes(value: Any) -> bytes:
    """Return the section-10.1 canonical JSON encoding of ``value``."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def numeric_grammar_derivation_sha256(row: Mapping[str, Any]) -> str:
    """Hash one complete terminal-LF canonical 16-key derivation row."""

    _validate_derivation_row(row)
    return hashlib.sha256(canonical_json_bytes(row)).hexdigest()


class SourceReferenceResolutionError(ValueError):
    """A consumer reference did not resolve uniquely and completely."""

    def __init__(
        self,
        reason: str,
        *,
        consumer_reference_position: int | None = None,
        field_key: FieldKey | None = None,
    ) -> None:
        self.reason = reason
        self.consumer_reference_position = consumer_reference_position
        self.field_key = field_key
        super().__init__(reason)


class ClosedFailureReferenceError(RuntimeError):
    """Atomic consumer-boundary abort carrying every offending row."""

    def __init__(self, rows: Sequence[Mapping[str, Any]]) -> None:
        if not rows:
            raise ValueError("closed-failure abort requires at least one row")
        copied_rows = tuple(deepcopy(dict(row)) for row in rows)
        self.closed_failure_reference_rows = copied_rows
        self.diagnostic_bytes = canonical_json_bytes(list(copied_rows))
        super().__init__(self.diagnostic_bytes.decode("ascii"))


def _validate_derivation_row_shape(row: Mapping[str, Any]) -> None:
    actual_keys = frozenset(row)
    expected_keys = frozenset(NUMERIC_GRAMMAR_DERIVATION_ROW_KEYS)
    if actual_keys != expected_keys or len(row) != len(expected_keys):
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise SourceReferenceResolutionError(
            "incomplete numeric-grammar derivation row: "
            f"missing={missing!r}, extra={extra!r}"
        )

    wave = row["interview_wave"]
    raw_field_id = row["raw_field_id"]
    derivation_id = row["numeric_grammar_derivation_id"]
    if isinstance(wave, bool) or not isinstance(wave, int):
        raise SourceReferenceResolutionError(
            "interview_wave must be a JSON integer excluding booleans"
        )
    if not isinstance(raw_field_id, str) or not raw_field_id:
        raise SourceReferenceResolutionError(
            "raw_field_id must be a nonempty string"
        )
    if not isinstance(derivation_id, str) or not derivation_id:
        raise SourceReferenceResolutionError(
            "numeric_grammar_derivation_id must be a nonempty string"
        )
    count = row["nonmissing_observation_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise SourceReferenceResolutionError(
            "nonmissing_observation_count must be a nonnegative JSON "
            "integer excluding booleans"
        )


def _validate_derivation_terminal(row: Mapping[str, Any]) -> None:
    status = row["derivation_status"]
    if status not in ALL_DERIVATION_STATUSES:
        raise SourceReferenceResolutionError(
            f"unknown derivation_status {status!r}"
        )
    if status in T_MINUS and any(
        row[key] is not None
        for key in (
            "normalized_format_profile",
            "padding_rule",
            "registered_numeric_grammar",
        )
    ):
        raise SourceReferenceResolutionError(
            "closed-failure row must serialize null profile, padding, "
            "and grammar"
        )


def _validate_derivation_row(row: Mapping[str, Any]) -> None:
    _validate_derivation_row_shape(row)
    _validate_derivation_terminal(row)


def _reference_key(reference: Reference, position: int) -> FieldKey:
    if isinstance(reference, Mapping):
        try:
            wave = reference["interview_wave"]
            raw_field_id = reference["raw_field_id"]
        except KeyError as error:
            raise SourceReferenceResolutionError(
                f"reference is missing {error.args[0]!r}",
                consumer_reference_position=position,
            ) from error
    elif (
        isinstance(reference, Sequence)
        and not isinstance(reference, (str, bytes, bytearray))
        and len(reference) == 2
    ):
        wave, raw_field_id = reference
    else:
        raise SourceReferenceResolutionError(
            "reference must be a mapping or a two-position field key",
            consumer_reference_position=position,
        )

    if isinstance(wave, bool) or not isinstance(wave, int):
        raise SourceReferenceResolutionError(
            "reference interview_wave must be an integer excluding booleans",
            consumer_reference_position=position,
        )
    if not isinstance(raw_field_id, str) or not raw_field_id:
        raise SourceReferenceResolutionError(
            "reference raw_field_id must be a nonempty string",
            consumer_reference_position=position,
        )
    return wave, raw_field_id


def _resolve_reference_stream(
    references: Iterable[Reference],
    derivation_rows: Iterable[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[str]]:
    rows_by_key: defaultdict[FieldKey, list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for row in derivation_rows:
        _validate_derivation_row_shape(row)
        key = (row["interview_wave"], row["raw_field_id"])
        rows_by_key[key].append(row)

    resolved_rows: list[Mapping[str, Any]] = []
    resolved_hashes: list[str] = []
    for position, reference in enumerate(references):
        key = _reference_key(reference, position)
        matching_rows = rows_by_key.get(key, [])
        if len(matching_rows) != 1:
            raise SourceReferenceResolutionError(
                "field reference must resolve to exactly one complete row; "
                f"resolved {len(matching_rows)}",
                consumer_reference_position=position,
                field_key=key,
            )

        row = matching_rows[0]
        try:
            row_sha256 = hashlib.sha256(canonical_json_bytes(row)).hexdigest()
        except (TypeError, ValueError) as error:
            raise SourceReferenceResolutionError(
                "resolved complete row is not canonical-JSON serializable",
                consumer_reference_position=position,
                field_key=key,
            ) from error
        if isinstance(reference, Mapping):
            if (
                "numeric_grammar_derivation_id" in reference
                and reference["numeric_grammar_derivation_id"]
                != row["numeric_grammar_derivation_id"]
            ):
                raise SourceReferenceResolutionError(
                    "numeric_grammar_derivation_id does not match the "
                    "resolved row",
                    consumer_reference_position=position,
                    field_key=key,
                )
            if (
                "numeric_grammar_derivation_sha256" in reference
                and reference["numeric_grammar_derivation_sha256"]
                != row_sha256
            ):
                raise SourceReferenceResolutionError(
                    "numeric_grammar_derivation_sha256 does not match the "
                    "resolved complete row",
                    consumer_reference_position=position,
                    field_key=key,
                )
        resolved_rows.append(row)
        resolved_hashes.append(row_sha256)
    for row in resolved_rows:
        _validate_derivation_terminal(row)
    return resolved_rows, resolved_hashes


def _consumer_values(
    consumer_kind: ConsumerKind | str,
    consumer_row_identity: Any,
) -> tuple[ConsumerKind, Any]:
    try:
        resolved_kind = ConsumerKind(consumer_kind)
    except ValueError as error:
        raise SourceReferenceResolutionError(
            f"unknown consumer_kind {consumer_kind!r}"
        ) from error

    identity_is_id = (
        isinstance(consumer_row_identity, str) and consumer_row_identity
    )
    identity_is_pair = (
        isinstance(consumer_row_identity, Sequence)
        and not isinstance(
            consumer_row_identity,
            (str, bytes, bytearray),
        )
        and len(consumer_row_identity) == 2
        and isinstance(consumer_row_identity[0], str)
        and bool(consumer_row_identity[0])
        and isinstance(consumer_row_identity[1], int)
        and not isinstance(consumer_row_identity[1], bool)
        and consumer_row_identity[1] >= 0
    )
    if not identity_is_id and not identity_is_pair:
        raise SourceReferenceResolutionError(
            "consumer_row_identity must be a nonempty existing row ID or "
            "[artifact_or_output_identity, zero_based_row_position]"
        )
    try:
        normalized_identity = json.loads(
            canonical_json_bytes(consumer_row_identity)
        )
    except (TypeError, ValueError) as error:
        raise SourceReferenceResolutionError(
            "consumer_row_identity is not canonical-JSON serializable"
        ) from error
    return resolved_kind, normalized_identity


def _diagnostics_from_resolved(
    *,
    consumer_kind: ConsumerKind,
    consumer_row_identity: Any,
    resolved_rows: Sequence[Mapping[str, Any]],
    resolved_hashes: Sequence[str],
    resolution_reason_by_field_key: Mapping[FieldKey, str],
) -> list[JsonObject]:
    diagnostics: list[JsonObject] = []
    for position, (row, row_sha256) in enumerate(
        zip(resolved_rows, resolved_hashes, strict=True)
    ):
        status = row["derivation_status"]
        if status not in T_MINUS:
            continue
        key = (row["interview_wave"], row["raw_field_id"])
        try:
            resolution_reason = resolution_reason_by_field_key[key]
        except KeyError as error:
            raise SourceReferenceResolutionError(
                "closed-failure row has no exact resolution_reason mapping",
                consumer_reference_position=position,
                field_key=key,
            ) from error
        if resolution_reason not in CLOSED_FAILURE_RESOLUTION_REASONS[status]:
            raise SourceReferenceResolutionError(
                "resolution_reason is not admitted for the exact closed-"
                "failure terminal",
                consumer_reference_position=position,
                field_key=key,
            )

        diagnostic = {
            "consumer_kind": consumer_kind.value,
            "consumer_row_identity": deepcopy(consumer_row_identity),
            "consumer_reference_position": position,
            "interview_wave": row["interview_wave"],
            "raw_field_id": row["raw_field_id"],
            "numeric_grammar_derivation_id": row[
                "numeric_grammar_derivation_id"
            ],
            "numeric_grammar_derivation_sha256": row_sha256,
            "derivation_status": status,
            "resolution_reason": resolution_reason,
        }
        if tuple(diagnostic) != CLOSED_FAILURE_REFERENCE_ROW_KEYS:
            raise AssertionError("closed-failure diagnostic schema drift")
        diagnostics.append(diagnostic)
    return diagnostics


def closed_failure_reference_rows(
    *,
    consumer_kind: ConsumerKind | str,
    consumer_row_identity: Any,
    references: Iterable[Reference],
    derivation_rows: Iterable[Mapping[str, Any]],
    resolution_reason_by_field_key: Mapping[FieldKey, str],
) -> list[JsonObject]:
    """Resolve a complete reference stream and return every T- diagnostic.

    Resolution is a distinct first phase: missing, duplicate, outside, ID,
    or complete-row-hash mismatches abort before any terminal is tested.
    Returned rows preserve the independently supplied reference order.
    """

    resolved_kind, normalized_identity = _consumer_values(
        consumer_kind, consumer_row_identity
    )

    resolved_rows, resolved_hashes = _resolve_reference_stream(
        references, derivation_rows
    )
    return _diagnostics_from_resolved(
        consumer_kind=resolved_kind,
        consumer_row_identity=normalized_identity,
        resolved_rows=resolved_rows,
        resolved_hashes=resolved_hashes,
        resolution_reason_by_field_key=resolution_reason_by_field_key,
    )


def guard_physical_consumption(
    *,
    consumer_kind: ConsumerKind | str,
    consumer_row_identity: Any,
    references: Iterable[Reference],
    derivation_rows: Iterable[Mapping[str, Any]],
    resolution_reason_by_field_key: Mapping[FieldKey, str],
    consume: Callable[[tuple[Mapping[str, Any], ...]], ResultT] | None = None,
) -> tuple[Mapping[str, Any], ...] | ResultT:
    """Guard one physical consumer and invoke ``consume`` only after pass.

    The entire ordered reference stream is resolved and every T- row is
    collected before the callback can run. A nonempty diagnostic raises one
    atomic exception carrying all offending rows.
    """

    reference_stream = tuple(references)
    derivation_relation = tuple(derivation_rows)
    resolved_kind, normalized_identity = _consumer_values(
        consumer_kind, consumer_row_identity
    )
    resolved_rows, resolved_hashes = _resolve_reference_stream(
        reference_stream, derivation_relation
    )
    diagnostics = _diagnostics_from_resolved(
        consumer_kind=resolved_kind,
        consumer_row_identity=normalized_identity,
        resolved_rows=resolved_rows,
        resolved_hashes=resolved_hashes,
        resolution_reason_by_field_key=resolution_reason_by_field_key,
    )
    if diagnostics:
        raise ClosedFailureReferenceError(diagnostics)

    result = tuple(resolved_rows)
    if consume is None:
        return result
    return consume(result)


__all__ = [
    "ALL_DERIVATION_STATUSES",
    "CLOSED_FAILURE_DERIVATION_STATUSES",
    "CLOSED_FAILURE_REFERENCE_ROW_KEYS",
    "CLOSED_FAILURE_RESOLUTION_REASONS",
    "CONSUMER_KINDS",
    "ClosedFailureReferenceError",
    "ConsumerKind",
    "NUMERIC_GRAMMAR_DERIVATION_ROW_KEYS",
    "PASSING_DERIVATION_STATUSES",
    "SourceReferenceResolutionError",
    "T_MINUS",
    "T_PLUS",
    "V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY",
    "canonical_json_bytes",
    "closed_failure_reference_rows",
    "guard_physical_consumption",
    "numeric_grammar_derivation_sha256",
]
