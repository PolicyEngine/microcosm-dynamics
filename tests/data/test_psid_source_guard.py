import hashlib
import json

import pytest

from populace_dynamics.data.psid_source_guard import (
    CLOSED_FAILURE_DERIVATION_STATUSES,
    CLOSED_FAILURE_REFERENCE_ROW_KEYS,
    CLOSED_FAILURE_RESOLUTION_REASONS,
    CONSUMER_KINDS,
    PASSING_DERIVATION_STATUSES,
    T_MINUS,
    T_PLUS,
    V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY,
    ClosedFailureReferenceError,
    ConsumerKind,
    SourceReferenceResolutionError,
    canonical_json_bytes,
    closed_failure_reference_rows,
    guard_physical_consumption,
    numeric_grammar_derivation_sha256,
)

pytestmark = pytest.mark.unit


def _derivation_row(
    interview_wave,
    raw_field_id,
    derivation_status="compiled_source_numeric_grammar",
):
    failed = derivation_status in T_MINUS
    return {
        "numeric_grammar_derivation_id": (
            f"psid-numeric-grammar-derivation:{interview_wave}:{raw_field_id}"
        ),
        "interview_wave": interview_wave,
        "raw_field_id": raw_field_id,
        "dictionary_field_row_ids": [f"dictionary#{raw_field_id}"],
        "dictionary_field_rows_sha256": "1" * 64,
        "codebook_field_row_ids": [f"codebook#{raw_field_id}"],
        "codebook_field_rows_sha256": "2" * 64,
        "source_format_projection": [],
        "source_meaning_projection": [],
        "dictionary_field_meaning": None if failed else raw_field_id,
        "derived_parse_kind": "fixed_width_numeric",
        "normalized_format_profile": (None if failed else {"raw_width": 2}),
        "nonmissing_observation_count": 1,
        "derivation_status": derivation_status,
        "padding_rule": None if failed else {"padding_kind": "none"},
        "registered_numeric_grammar": (
            None if failed else {"grammar_id": f"grammar:{raw_field_id}"}
        ),
    }


PASSING_KEYS = (
    (1976, "V4379"),
    (1977, "V5289"),
    (1978, "V5788"),
)
FORBIDDEN_KEYS = tuple(V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY)


@pytest.fixture
def real_shaped_relation():
    passing = [_derivation_row(*key) for key in PASSING_KEYS]
    failures = [
        _derivation_row(
            *key,
            derivation_status="incomplete_source_numeric_authority",
        )
        for key in FORBIDDEN_KEYS
    ]
    return passing + failures


def test_exact_terminal_and_consumer_kind_domains():
    assert PASSING_DERIVATION_STATUSES == (
        "compiled_source_numeric_grammar",
        "compiled_source_numeric_grammar_padding_underdetermined_exact_replay",
        "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_exact_replay",
        "compiled_source_numeric_grammar_partial_range_exact_replay",
        "value_code_domain_no_numeric_grammar",
        "value_code_range_physical_rendering_unestablished",
        "nonnumeric_source_field_outside_numeric_grammar",
    )
    assert CLOSED_FAILURE_DERIVATION_STATUSES == (
        "conflicting_source_numeric_format",
        "unsupported_source_numeric_format",
        "incomplete_source_numeric_authority",
    )
    assert T_PLUS == frozenset(PASSING_DERIVATION_STATUSES)
    assert T_MINUS == frozenset(CLOSED_FAILURE_DERIVATION_STATUSES)
    assert CONSUMER_KINDS == (
        "q5_positive_field_join",
        "slot_registry_row",
        "official_inventory_row",
        "value_map",
        "crosswalk",
        "correction_input",
        "context_output",
    )
    assert tuple(kind.value for kind in ConsumerKind) == CONSUMER_KINDS
    assert CLOSED_FAILURE_RESOLUTION_REASONS == {
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


def test_complete_row_sha_is_sorted_compact_ascii_with_one_lf():
    row = _derivation_row(1976, "V4379")
    expected_bytes = (
        json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode()
    assert canonical_json_bytes(row) == expected_bytes
    assert expected_bytes.endswith(b"\n")
    assert not expected_bytes.endswith(b"\n\n")
    assert (
        numeric_grammar_derivation_sha256(row)
        == hashlib.sha256(expected_bytes).hexdigest()
    )


def test_closed_failure_rows_have_exact_schema_and_reference_order(
    real_shaped_relation,
):
    diagnostics = closed_failure_reference_rows(
        consumer_kind=ConsumerKind.CROSSWALK,
        consumer_row_identity=["consumer-fixture.v1", 17],
        references=list(FORBIDDEN_KEYS),
        derivation_rows=real_shaped_relation,
        resolution_reason_by_field_key=(
            V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY
        ),
    )

    assert len(diagnostics) == 4
    assert [tuple(row) for row in diagnostics] == [
        CLOSED_FAILURE_REFERENCE_ROW_KEYS
    ] * 4
    assert [
        (row["interview_wave"], row["raw_field_id"]) for row in diagnostics
    ] == list(FORBIDDEN_KEYS)
    assert [row["consumer_reference_position"] for row in diagnostics] == [
        0,
        1,
        2,
        3,
    ]
    assert {row["derivation_status"] for row in diagnostics} == {
        "incomplete_source_numeric_authority"
    }
    assert {row["resolution_reason"] for row in diagnostics} == {
        "literal_only_zero_diagnostic_padding_capacity"
    }
    assert all(row["consumer_kind"] == "crosswalk" for row in diagnostics)
    assert all(
        row["consumer_row_identity"] == ["consumer-fixture.v1", 17]
        for row in diagnostics
    )


def test_forbidden_fields_abort_atomically_with_all_rows(
    real_shaped_relation,
):
    callback_calls = []

    def consume(rows):
        callback_calls.append(rows)
        return "must-not-run"

    with pytest.raises(ClosedFailureReferenceError) as error:
        guard_physical_consumption(
            consumer_kind="official_inventory_row",
            consumer_row_identity=["inventory-fixture.v1", 3],
            references=list(FORBIDDEN_KEYS),
            derivation_rows=real_shaped_relation,
            resolution_reason_by_field_key=(
                V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY
            ),
            consume=consume,
        )

    assert callback_calls == []
    rows = error.value.closed_failure_reference_rows
    assert len(rows) == 4
    assert error.value.diagnostic_bytes == canonical_json_bytes(list(rows))
    assert str(error.value).encode("ascii") == error.value.diagnostic_bytes
    assert [row["consumer_reference_position"] for row in rows] == [
        0,
        1,
        2,
        3,
    ]


def test_diagnostic_positions_include_passing_references(
    real_shaped_relation,
):
    references = [
        PASSING_KEYS[0],
        FORBIDDEN_KEYS[0],
        PASSING_KEYS[1],
        FORBIDDEN_KEYS[1],
    ]
    diagnostics = closed_failure_reference_rows(
        consumer_kind="crosswalk",
        consumer_row_identity=("mixed-stream.v1", 4),
        references=references,
        derivation_rows=real_shaped_relation,
        resolution_reason_by_field_key=(
            V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY
        ),
    )

    assert [row["consumer_reference_position"] for row in diagnostics] == [
        1,
        3,
    ]
    assert all(
        row["consumer_row_identity"] == ["mixed-stream.v1", 4]
        for row in diagnostics
    )


def test_passing_amount_fields_are_read_once_after_guard(
    real_shaped_relation,
):
    callback_calls = []

    def consume(rows):
        callback_calls.append(rows)
        return [(row["interview_wave"], row["raw_field_id"]) for row in rows]

    result = guard_physical_consumption(
        consumer_kind="correction_input",
        consumer_row_identity="passing-amount-operands.v1",
        references=list(PASSING_KEYS),
        derivation_rows=real_shaped_relation,
        resolution_reason_by_field_key=(
            V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY
        ),
        consume=consume,
    )

    assert result == list(PASSING_KEYS)
    assert len(callback_calls) == 1
    assert [
        (row["interview_wave"], row["raw_field_id"])
        for row in callback_calls[0]
    ] == list(PASSING_KEYS)


@pytest.mark.parametrize(
    ("member", "bad_value", "message"),
    [
        (
            "numeric_grammar_derivation_id",
            "wrong-derivation-id",
            "derivation_id does not match",
        ),
        (
            "numeric_grammar_derivation_sha256",
            "0" * 64,
            "sha256 does not match",
        ),
    ],
)
def test_optional_derivation_identity_and_complete_row_hash_are_checked(
    real_shaped_relation,
    member,
    bad_value,
    message,
):
    row = real_shaped_relation[0]
    reference = {
        "interview_wave": row["interview_wave"],
        "raw_field_id": row["raw_field_id"],
        "numeric_grammar_derivation_id": row["numeric_grammar_derivation_id"],
        "numeric_grammar_derivation_sha256": (
            numeric_grammar_derivation_sha256(row)
        ),
    }
    assert (
        closed_failure_reference_rows(
            consumer_kind="value_map",
            consumer_row_identity=["value-map.v1", 0],
            references=[reference],
            derivation_rows=real_shaped_relation,
            resolution_reason_by_field_key=(
                V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY
            ),
        )
        == []
    )

    reference[member] = bad_value
    with pytest.raises(
        SourceReferenceResolutionError,
        match=message,
    ):
        closed_failure_reference_rows(
            consumer_kind="value_map",
            consumer_row_identity=["value-map.v1", 0],
            references=[reference],
            derivation_rows=real_shaped_relation,
            resolution_reason_by_field_key=(
                V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY
            ),
        )


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_reference_resolution_aborts_before_callback(
    real_shaped_relation,
    mutation,
):
    callback_calls = []
    rows = list(real_shaped_relation)
    if mutation == "missing":
        references = [(1999, "ER_MISSING")]
    else:
        references = [PASSING_KEYS[0]]
        rows.append(dict(rows[0]))

    with pytest.raises(SourceReferenceResolutionError):
        guard_physical_consumption(
            consumer_kind="context_output",
            consumer_row_identity=["context.v1", 0],
            references=references,
            derivation_rows=rows,
            resolution_reason_by_field_key=(
                V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY
            ),
            consume=lambda resolved: callback_calls.append(resolved),
        )

    assert callback_calls == []


def test_failure_rows_require_null_profile_padding_and_grammar():
    row = _derivation_row(
        1976,
        "V4902",
        derivation_status="incomplete_source_numeric_authority",
    )
    row["padding_rule"] = {"padding_kind": "none"}
    with pytest.raises(
        SourceReferenceResolutionError,
        match="null profile, padding, and grammar",
    ):
        numeric_grammar_derivation_sha256(row)


def test_failure_reason_must_match_its_exact_terminal(real_shaped_relation):
    bad_reasons = dict(V_B6_CLOSED_FAILURE_REASON_BY_FIELD_KEY)
    bad_reasons[FORBIDDEN_KEYS[0]] = "selected_space_literal_unrenderable"

    with pytest.raises(
        SourceReferenceResolutionError,
        match="not admitted for the exact closed-failure terminal",
    ):
        closed_failure_reference_rows(
            consumer_kind="slot_registry_row",
            consumer_row_identity=["slot.v1", 0],
            references=[FORBIDDEN_KEYS[0]],
            derivation_rows=real_shaped_relation,
            resolution_reason_by_field_key=bad_reasons,
        )
