"""Pure Amendment-11 missing-reason authority tests."""

from __future__ import annotations

from itertools import combinations

import pytest

from populace_dynamics.data.psid_missing_reason_authority import (
    AUTHORITY_FAILURE_DISPOSITION_ROWS,
    AUTHORITY_FAILURE_STATES,
    CONFLICTING_AUTHORITY_FAILURE_STATES,
    CONFLICTING_MISSING_REASON_AUTHORITY,
    INCOMPLETE_AUTHORITY_FAILURE_STATES,
    INCOMPLETE_MISSING_REASON_AUTHORITY,
    REASON_CODE_PREFIX,
    SOURCE_AUTHORIZED_DISPOSITION,
    SOURCE_AUTHORIZED_MEANING,
    SOURCE_AUTHORIZED_VALUE_LEXEME,
    MissingReasonAuthorityError,
    SourceMember,
    authority_failure_disposition,
    candidate_is_missing,
    canonical_json_bytes,
    canonical_sha256,
    disposition_at,
    fixture_conditional_missing_reason_relation,
    fixture_conditional_missing_reason_value,
    fixture_conditional_missing_reason_value_from_claims,
    fixture_request_missing_reason_taxonomy,
    missing_reason_code,
    pack_disposition_bits,
    source_authorizes_current_missing_reason,
    source_member_identity,
    validate_disposition_vector,
)


def _literal_entry(**changes):
    document_id = "psid-source-document:" + "a" * 64
    entry = {
        "entry_ref": f"{document_id}#row:0:entry:0",
        "entry_kind": "literal",
        "source_value_lexeme": "9",
        "raw_token_hex": None,
        "source_meaning": "DK; NA; refused",
        "typed_disposition": "missing",
        "value_type": None,
        "typed_value_unit": None,
        "canonical_value": None,
        "missing_reason_code": None,
    }
    entry.update(changes)
    return entry


def _member(**entry_changes):
    document_id = "psid-source-document:" + "a" * 64
    return SourceMember(
        member_position=7,
        source_document_position=1,
        source_row_position=0,
        entry_position=0,
        source_document_id=document_id,
        codebook_field_row_id=f"{document_id}#row:0",
        source_locator_ids=("psid-source-region:" + "b" * 64,),
        entry=_literal_entry(**entry_changes),
    )


def _range_member(**entry_changes):
    document_id = "psid-source-document:" + "a" * 64
    entry = {
        "entry_ref": f"{document_id}#row:0:entry:0",
        "entry_kind": "numeric_range",
        "source_value_lexeme": "1 - 9",
        "value_type": "json_integer",
        "typed_value_unit": None,
        "inclusive_min": 1,
        "inclusive_max": 9,
        "step": 1,
        "source_meaning": "Values 1 through 9",
        "typed_disposition": "json_integer",
        "missing_reason_code": None,
    }
    entry.update(entry_changes)
    return SourceMember(
        member_position=7,
        source_document_position=1,
        source_row_position=0,
        entry_position=0,
        source_document_id=document_id,
        codebook_field_row_id=f"{document_id}#row:0",
        source_locator_ids=("psid-source-region:" + "b" * 64,),
        entry=entry,
    )


def _source_authorized_member(**entry_changes):
    changes = {
        "source_value_lexeme": SOURCE_AUTHORIZED_VALUE_LEXEME,
        "source_meaning": SOURCE_AUTHORIZED_MEANING,
        "typed_disposition": SOURCE_AUTHORIZED_DISPOSITION,
    }
    changes.update(entry_changes)
    return _member(**changes)


def test_canonical_json_has_sorted_keys_ascii_and_one_lf():
    assert canonical_json_bytes({"z": "é", "a": 1}) == (
        b'{"a":1,"z":"\\u00e9"}\n'
    )


def test_reason_code_is_deterministic_opaque_occurrence_identity():
    member = _member()
    code = missing_reason_code(member)
    assert code == missing_reason_code(member)
    assert code.startswith(REASON_CODE_PREFIX)
    assert len(code) == len(REASON_CODE_PREFIX) + 64
    assert "refused" not in code


def test_exact_source_authority_bytes_yield_an_opaque_occurrence_code():
    member = _source_authorized_member()
    assert source_authorizes_current_missing_reason(member) is True
    code = missing_reason_code(member)
    assert code.startswith(REASON_CODE_PREFIX)
    assert len(code) == len(REASON_CODE_PREFIX) + 64
    assert SOURCE_AUTHORIZED_VALUE_LEXEME not in code
    assert SOURCE_AUTHORIZED_MEANING not in code


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source_value_lexeme", "9,999,999.0"),
        ("source_value_lexeme", "9999999.00"),
        ("source_meaning", "missing, not imputed"),
        ("source_meaning", "Missing,  not imputed"),
        ("source_meaning", "Missing, not imputed."),
        ("source_meaning", "Missing, imputed"),
    ],
)
def test_near_byte_source_authority_mutants_remain_unauthorized(
    field, replacement
):
    authorized = _source_authorized_member()
    mutant = _source_authorized_member(**{field: replacement})
    assert source_authorizes_current_missing_reason(mutant) is False
    assert missing_reason_code(mutant) != missing_reason_code(authorized)


@pytest.mark.parametrize(
    ("attribute", "replacement"),
    [
        ("member_position", 8),
        ("source_document_position", 2),
        ("source_locator_ids", ("psid-source-region:" + "c" * 64,)),
    ],
)
def test_occurrence_coordinate_mutations_change_reason_code(
    attribute, replacement
):
    member = _member()
    values = dict(member.__dict__)
    values[attribute] = replacement
    mutated = SourceMember(**values)
    assert missing_reason_code(mutated) != missing_reason_code(member)


def test_coherent_nested_coordinate_mutations_change_reason_code():
    member = _member()
    document_id = "psid-source-document:" + "c" * 64
    row_id = f"{document_id}#row:1"
    mutated = SourceMember(
        member_position=member.member_position,
        source_document_position=member.source_document_position,
        source_row_position=1,
        entry_position=2,
        source_document_id=document_id,
        codebook_field_row_id=row_id,
        source_locator_ids=member.source_locator_ids,
        entry=_literal_entry(entry_ref=f"{row_id}:entry:2"),
    )
    assert missing_reason_code(mutated) != missing_reason_code(member)


@pytest.mark.parametrize(
    ("attribute", "replacement", "match"),
    [
        ("member_position", -1, "member position"),
        ("member_position", True, "member position"),
        ("source_document_position", -1, "document position"),
        ("source_row_position", -1, "row position"),
        ("entry_position", -1, "entry position"),
        ("source_document_id", "psid-source-document:short", "document ID"),
        ("codebook_field_row_id", "wrong", "row identity"),
        ("source_locator_ids", (), "locator identity"),
        (
            "source_locator_ids",
            ("psid-source-region:" + "b" * 64,) * 2,
            "locator identity",
        ),
        (
            "source_locator_ids",
            ("psid-source-region:short",),
            "locator identity",
        ),
    ],
)
def test_malformed_occurrence_preimages_abort(attribute, replacement, match):
    values = dict(_member().__dict__)
    values[attribute] = replacement
    with pytest.raises(MissingReasonAuthorityError, match=match):
        missing_reason_code(SourceMember(**values))


def test_incoherent_entry_reference_aborts():
    with pytest.raises(MissingReasonAuthorityError, match="entry reference"):
        missing_reason_code(_member(entry_ref="wrong"))


@pytest.mark.parametrize(
    ("member", "expected"),
    [
        (_member(), True),
        (
            _member(
                typed_disposition="json_integer",
                value_type="json_integer",
                canonical_value=9,
            ),
            False,
        ),
        (
            _range_member(),
            False,
        ),
    ],
)
def test_candidate_disposition_valid_branches(member, expected):
    assert candidate_is_missing(member) is expected


@pytest.mark.parametrize(
    "changes",
    [
        {"entry_kind": "numeric_range"},
        {"value_type": "json_integer"},
        {"canonical_value": 9},
        {"typed_value_unit": "USD"},
        {"missing_reason_code": "invented_default"},
        {"typed_disposition": "enum"},
    ],
)
def test_malformed_or_overreaching_candidate_aborts(changes):
    with pytest.raises(MissingReasonAuthorityError):
        candidate_is_missing(_member(**changes))


@pytest.mark.parametrize(
    "member",
    [
        _member(source_value_lexeme="NOT_A_NUMBER"),
        _member(
            typed_disposition="json_integer",
            value_type="json_integer",
            canonical_value=8,
        ),
        _range_member(inclusive_max=8),
        _range_member(source_value_lexeme="9 - 1"),
    ],
)
def test_invalid_scalar_or_range_semantics_cannot_mint_reason(member):
    with pytest.raises(MissingReasonAuthorityError):
        source_member_identity(member)
    with pytest.raises(MissingReasonAuthorityError):
        candidate_is_missing(member)
    with pytest.raises(MissingReasonAuthorityError):
        fixture_conditional_missing_reason_value(member, True)


@pytest.mark.parametrize(
    "meaning",
    [
        "DK",
        "NA; refused",
        "DK; NA; refused",
        "missing finger",
        "6-8 grades; DK; NA",
    ],
)
def test_source_meaning_is_retained_whole_without_semantic_split(meaning):
    member = _member(source_meaning=meaning)
    identity = source_member_identity(member)
    assert identity[-1] == meaning
    assert candidate_is_missing(member)
    assert meaning not in missing_reason_code(member)


@pytest.mark.parametrize("requested_category", ["DK", "NA", "refused"])
def test_composite_reason_taxonomy_requests_are_undetermined(
    requested_category,
):
    with pytest.raises(
        MissingReasonAuthorityError,
        match="^semantic_reason_taxonomy_undetermined$",
    ):
        fixture_request_missing_reason_taxonomy(
            _member(source_meaning="DK; NA; refused"),
            (True,),
            requested_category,
        )


def test_lexical_candidate_does_not_authorize_literal_settlement():
    member = _member(source_meaning="Never refused")
    assert candidate_is_missing(member) is True
    with pytest.raises(
        MissingReasonAuthorityError, match="disposition is unadjudicated"
    ):
        fixture_conditional_missing_reason_value(member, None)


@pytest.mark.parametrize(
    ("authenticated_missing", "expects_code"),
    [(False, False), (True, True)],
)
def test_conditional_literal_law_has_satisfiable_future_arms(
    authenticated_missing, expects_code
):
    value = fixture_conditional_missing_reason_value(
        _member(), authenticated_missing
    )
    if expects_code:
        assert value == missing_reason_code(_member())
    else:
        assert value is None


def test_five_state_disposition_partition_covers_all_31_predicate_sets():
    singleton_rows = dict(AUTHORITY_FAILURE_DISPOSITION_ROWS)
    assert len(AUTHORITY_FAILURE_STATES) == 5
    assert set(CONFLICTING_AUTHORITY_FAILURE_STATES).isdisjoint(
        INCOMPLETE_AUTHORITY_FAILURE_STATES
    )
    assert set(CONFLICTING_AUTHORITY_FAILURE_STATES) | set(
        INCOMPLETE_AUTHORITY_FAILURE_STATES
    ) == set(AUTHORITY_FAILURE_STATES)
    assert set(singleton_rows) == set(AUTHORITY_FAILURE_STATES)
    assert {
        singleton_rows[state] for state in CONFLICTING_AUTHORITY_FAILURE_STATES
    } == {CONFLICTING_MISSING_REASON_AUTHORITY}
    assert {
        singleton_rows[state] for state in INCOMPLETE_AUTHORITY_FAILURE_STATES
    } == {INCOMPLETE_MISSING_REASON_AUTHORITY}

    observed = {}
    for width in range(1, len(AUTHORITY_FAILURE_STATES) + 1):
        for active_states in combinations(AUTHORITY_FAILURE_STATES, width):
            expected = (
                CONFLICTING_MISSING_REASON_AUTHORITY
                if set(active_states).intersection(
                    CONFLICTING_AUTHORITY_FAILURE_STATES
                )
                else INCOMPLETE_MISSING_REASON_AUTHORITY
            )
            disposition = authority_failure_disposition(active_states)
            assert disposition == expected
            assert authority_failure_disposition(reversed(active_states)) == (
                expected
            )
            observed[frozenset(active_states)] = disposition
    assert len(observed) == 31
    assert set(observed.values()) == {
        CONFLICTING_MISSING_REASON_AUTHORITY,
        INCOMPLETE_MISSING_REASON_AUTHORITY,
    }


@pytest.mark.parametrize(
    "active_states",
    [
        (),
        ("unknown_failure_state",),
        ("malformed_member_or_authority",) * 2,
        "malformed_member_or_authority",
        (1,),
    ],
)
def test_disposition_partition_rejects_nonstates_and_nonsets(active_states):
    with pytest.raises(
        MissingReasonAuthorityError,
        match="^malformed authority failure predicate set$",
    ):
        authority_failure_disposition(active_states)


def test_conflicting_future_disposition_claims_abort():
    with pytest.raises(
        MissingReasonAuthorityError,
        match=f"^{CONFLICTING_MISSING_REASON_AUTHORITY}:",
    ):
        fixture_conditional_missing_reason_value_from_claims(
            _member(), (True, False)
        )


@pytest.mark.parametrize("claim", [False, True])
def test_duplicated_future_disposition_claims_abort(claim):
    with pytest.raises(
        MissingReasonAuthorityError,
        match=f"^{CONFLICTING_MISSING_REASON_AUTHORITY}:",
    ):
        fixture_conditional_missing_reason_value_from_claims(
            _member(), (claim, claim)
        )


def test_duplicate_conditional_assignment_aborts():
    member = _member()
    with pytest.raises(
        MissingReasonAuthorityError,
        match=f"^{CONFLICTING_MISSING_REASON_AUTHORITY}:",
    ):
        fixture_conditional_missing_reason_relation(
            ((member, (True,)), (member, (True,)))
        )


def test_empty_conditional_relation_exposes_incomplete_identifier():
    with pytest.raises(
        MissingReasonAuthorityError,
        match=f"^{INCOMPLETE_MISSING_REASON_AUTHORITY}:",
    ):
        fixture_conditional_missing_reason_relation(())


def test_malformed_conditional_claim_exposes_incomplete_identifier():
    with pytest.raises(
        MissingReasonAuthorityError,
        match=f"^{INCOMPLETE_MISSING_REASON_AUTHORITY}:",
    ):
        fixture_conditional_missing_reason_value_from_claims(
            _member(), ("missing",)
        )


def test_opaque_code_collision_aborts(monkeypatch):
    first = _member()
    values = dict(first.__dict__)
    values["member_position"] += 1
    second = SourceMember(**values)
    monkeypatch.setattr(
        "populace_dynamics.data.psid_missing_reason_authority."
        "missing_reason_code",
        lambda _member: REASON_CODE_PREFIX + "0" * 64,
    )
    with pytest.raises(
        MissingReasonAuthorityError,
        match=f"^{CONFLICTING_MISSING_REASON_AUTHORITY}:",
    ):
        fixture_conditional_missing_reason_relation(
            ((first, (True,)), (second, (True,)))
        )


def test_numeric_range_is_structurally_null_without_a_default():
    member = _range_member()
    assert fixture_conditional_missing_reason_value(member, None) is None
    assert fixture_conditional_missing_reason_value(member, False) is None
    with pytest.raises(
        MissingReasonAuthorityError,
        match=f"^{CONFLICTING_MISSING_REASON_AUTHORITY}:",
    ):
        fixture_conditional_missing_reason_value(member, True)
    with pytest.raises(MissingReasonAuthorityError, match="numeric range"):
        missing_reason_code(member)


@pytest.mark.parametrize("malformed", [0, 0.0, "false"])
def test_numeric_range_rejects_nonboolean_disposition_authority(malformed):
    with pytest.raises(
        MissingReasonAuthorityError,
        match=f"^{INCOMPLETE_MISSING_REASON_AUTHORITY}:",
    ):
        fixture_conditional_missing_reason_value(_range_member(), malformed)


def test_empty_meaning_is_known_undetermined_and_aborts():
    with pytest.raises(
        MissingReasonAuthorityError, match="empty source meaning"
    ):
        source_member_identity(_member(source_meaning=""))


def test_equal_spelling_in_distinct_occurrences_does_not_claim_equivalence():
    first = _member(source_meaning="DK")
    values = dict(first.__dict__)
    values["member_position"] = first.member_position + 1
    second = SourceMember(**values)
    assert missing_reason_code(first) != missing_reason_code(second)


@pytest.mark.parametrize(
    "values",
    [
        [],
        [False],
        [True],
        [True, False, True, False, True, False, True, False],
        [True, False, True, True, False, False, True, False, True],
    ],
)
def test_disposition_vector_round_trip(values):
    packed_hex, count = pack_disposition_bits(values)
    packed = validate_disposition_vector(packed_hex, count)
    assert [
        disposition_at(packed, index, count) for index in range(count)
    ] == (values)


@pytest.mark.parametrize(
    ("packed_hex", "count", "match"),
    [
        ("0", 1, "hex"),
        ("gg", 1, "hex"),
        ("00", -1, "member count"),
        ("", 1, "byte count"),
        ("01", 1, "padding"),
    ],
)
def test_disposition_vector_malformed_mutations_abort(
    packed_hex, count, match
):
    with pytest.raises(MissingReasonAuthorityError, match=match):
        validate_disposition_vector(packed_hex, count)


def test_disposition_lookup_rejects_absent_key_instead_of_defaulting():
    packed = validate_disposition_vector("80", 1)
    with pytest.raises(MissingReasonAuthorityError, match="unregistered"):
        disposition_at(packed, 1, 1)


def test_reason_code_changes_on_case_whitespace_and_punctuation_mutations():
    source = _member(source_meaning="DK; NA; refused")
    codes = {
        missing_reason_code(source),
        missing_reason_code(_member(source_meaning="dk; NA; refused")),
        missing_reason_code(_member(source_meaning="DK;  NA; refused")),
        missing_reason_code(_member(source_meaning="DK, NA; refused")),
    }
    assert len(codes) == 4


def test_identity_hash_changes_if_entry_kind_flips_literal_to_range():
    literal = _member()
    numeric_range = _range_member()
    assert canonical_sha256(source_member_identity(literal)) != (
        canonical_sha256(source_member_identity(numeric_range))
    )
