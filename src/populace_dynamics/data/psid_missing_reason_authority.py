"""Fail-closed Amendment-11 law for ``missing_reason_code``.

The 47 registered codebook/value-label sources carry value lexemes and source
meanings, but no missing-disposition column or reason-code vocabulary.  The
predecessor extractor's ``typed_disposition`` field is a reproducible lexical
candidate: it is not source authority.  Registered counterexamples such as
``Never refused``, ``Refused at least once``, and ``missing finger`` prove
that the substring classifier cannot authorize a reason assignment.

The current production disposition is therefore deliberately modest.  A
numeric range has JSON-null ``missing_reason_code`` under the inherited tagged
union.  Every literal remains unadjudicated until a separate authenticated
source authority supplies its missing/nonmissing disposition.  The opaque
occurrence-code construction is defined and testable for such a future
authority, but this module refuses to settle the current literal relation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "psid_missing_reason_code_fail_closed_authority.v1"
ARTIFACT_ID = SCHEMA_VERSION
MEMBER_IDENTITY_VERSION = "psid_codebook_source_member_identity.v1"
REASON_PREIMAGE_VERSION = "psid_source_missing_reason_preimage.v1"
REASON_CODE_PREFIX = "psid-source-missing-reason:"

ENTRY_KIND_VECTOR_ENCODING = "msb0-one-is-literal-zero-is-numeric-range"
LEXICAL_VECTOR_ENCODING = (
    "msb0-one-is-lexical-missing-candidate-zero-is-other-candidate"
)

EXPECTED_REGISTRY_PATH = (
    "data/external/"
    "psid_questionnaire_dictionary_inventory_registration_required_v1.json"
)
EXPECTED_REGISTRY_BYTE_SIZE = 25_474_435
EXPECTED_REGISTRY_SHA256 = (
    "a974c6fb65a9f3d52387163f2e98b7cd8cfdbd57f5e95d1f766b3aa25d167ac0"
)
EXPECTED_REGISTERED_SOURCE_COUNT = 47
EXPECTED_REGISTERED_SOURCE_BYTE_SIZE = 114_875_090
EXPECTED_REGISTERED_SOURCE_ROWS_SHA256 = (
    "d5b67f8b6b95dded9d8987af5784ea93bdc4b05744c3338619dd3681b7e62957"
)
EXPECTED_PROJECTED_SOURCE_ROWS_SHA256 = (
    "0d27b2f940413d11727753a820360ac0a680eed503ea85bbe0a1344ed2f187e0"
)

EXPECTED_DOCUMENT_COUNT = 47
EXPECTED_CANONICAL_ROW_COUNT = 102_179
EXPECTED_MEMBER_COUNT = 561_873
EXPECTED_LITERAL_COUNT = 524_590
EXPECTED_NUMERIC_RANGE_COUNT = 37_283
EXPECTED_LEXICAL_MISSING_COUNT = 231_263
EXPECTED_LEXICAL_OTHER_COUNT = 330_610
EXPECTED_PDF_ROW_COUNT = 89_599
EXPECTED_PDF_MEMBER_COUNT = 479_345
EXPECTED_PDF_LEXICAL_MISSING_COUNT = 203_283
EXPECTED_LABEL_LEXICAL_MISSING_COUNT = 27_980
EXPECTED_DISTINCT_CANDIDATE_MEANING_COUNT = 35_925
EXPECTED_SOURCE_LOCATOR_COUNT = 112_382
EXPECTED_DICTIONARY_MISSING_DECLARATION_COUNT = 0

EXPECTED_SOURCE_DOCUMENT_ROWS_SHA256 = (
    "c6db713d8dee860adeafbcfd0f232ece9ce374ee66dee3fe39c02bd52a39999a"
)
EXPECTED_ENTRY_KIND_PACKED_SHA256 = (
    "c22dedca28755870ad892d5f7be89e79a02dc30b001bcc6171c19f8ce4d053f3"
)
EXPECTED_LEXICAL_PACKED_SHA256 = (
    "0534dd57a3f2ff12db460323b92a583ec4c0e7d7fb3d884a1bef6cced67a15c7"
)
EXPECTED_COUNTEREXAMPLE_COUNT = 118
EXPECTED_COUNTEREXAMPLE_SHA256 = (
    "25a3b74e34d5f594937cdbc9bb260c28ed5db3f0fb9abea07af6603651fd8bfc"
)
EXPECTED_DIRECTLY_DISPROVEN_COUNT = 61
EXPECTED_DIRECTLY_DISPROVEN_SHA256 = (
    "a9be450dc6e38331c5bf491a73de40ad2e72367c40df6ffdeb81e88a4c6e2845"
)
EXPECTED_RANGE_REJECTION_SHA256 = (
    "5473c792d62339b1da55c6124ddb548020480d6a8dfcd06b7cc500088d3a15d5"
)
EXPECTED_REJECTION_CLASS_SHA256 = (
    "01c9fd7a3cb4627e5fef7970fd1fa52ae410505a39c5ce34612d9bf89d6f4f19"
)
EXPECTED_MISSING_CANDIDATE_PROJECTION_SHA256 = (
    "792b02b8deb5341b6b9ca8abd714dbc08242699a1c951685fca89ac4173c1c92"
)
EXPECTED_EMPTY_ARRAY_SHA256 = (
    "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
)

EXPECTED_CENSUS_SHA256S = {
    "canonical_source_row_domain_sha256": (
        "5feb5dacc3320f83a7b9eb7a331637721bbb58fe77f4e8f9cfb9165b4bad64ac"
    ),
    "source_member_complete_domain_sha256": (
        "547f6331fa469b3890e41b841cc89d807b9e7779326eb7b4f60b1208e2ddd4a1"
    ),
    "source_member_identity_sha256": (
        "1e8384aec708a30b5beec81e4c4c08e330dd2ca6a33c36a9dfe208b9b8eee312"
    ),
    "lexical_missing_candidate_identity_sha256": (
        "e9bfe0593cfbdf4fa218d4e01f0ec60ac9b2350838f6dd631e4d91683ab53baa"
    ),
    "distinct_lexical_candidate_meaning_sha256": (
        "6f76fefce541fec600b35d5526d981529a9134cf0a5e6949198315c837614fb1"
    ),
    "source_locator_domain_sha256": (
        "1e261e8f0fa1da3942ca97da9de7d657715d0518e075e9149f546b1165012f8d"
    ),
}

EXPECTED_SELECTED_EXACT_MEANING_COUNTS = {
    "DK": 50_975,
    "DK; NA; refused": 9_249,
    "NA; DK": 12_290,
    "NA; refused": 54_409,
}
EXPECTED_SELECTED_EXACT_MEANING_COUNTS_SHA256 = (
    "499f73b16da86766fb7a71afafffad3b35bae6570fc856d0fe52ab3aee3244f6"
)
EXPECTED_OVERLAPPING_PHRASE_COUNTS = {
    "DK": 116_452,
    "Inap": 90_626,
    "NA": 123_703,
    "RF": 35_840,
    "data suppressed": 178,
    "don't know": 38,
    "missing": 118,
    "not ascertained": 4,
    "refus": 66_189,
    "wild code": 683,
}
EXPECTED_OVERLAPPING_PHRASE_COUNTS_SHA256 = (
    "dc2f86e4686055409441c894f473772114dd6042b5df89c1a87e03591dd57cdd"
)

EXPECTED_IMPLEMENTATION_PATHS = (
    "src/populace_dynamics/data/psid_codebook_extraction.py",
    "src/populace_dynamics/data/psid_missing_reason_authority.py",
    "scripts/rebuild_amendment11_missing_reason_authority.py",
)

_HEX = frozenset("0123456789abcdef")

_LITERAL_ENTRY_KEYS = (
    "canonical_value",
    "entry_kind",
    "entry_ref",
    "missing_reason_code",
    "raw_token_hex",
    "source_meaning",
    "source_value_lexeme",
    "typed_disposition",
    "typed_value_unit",
    "value_type",
)
_NUMERIC_RANGE_ENTRY_KEYS = (
    "entry_kind",
    "entry_ref",
    "inclusive_max",
    "inclusive_min",
    "missing_reason_code",
    "source_meaning",
    "source_value_lexeme",
    "step",
    "typed_disposition",
    "typed_value_unit",
    "value_type",
)


class MissingReasonAuthorityError(ValueError):
    """The candidate relation or requested reason assignment is inadmissible."""


@dataclass(frozen=True)
class SourceMember:
    """One normalized member in complete registered source order."""

    member_position: int
    source_document_position: int
    source_row_position: int
    entry_position: int
    source_document_id: str
    codebook_field_row_id: str
    source_locator_ids: tuple[str, ...]
    entry: Mapping[str, Any]


def _canonical_compact_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise MissingReasonAuthorityError(
            "value is not section-10.1 canonical JSON"
        ) from error


def canonical_json_bytes(value: Any) -> bytes:
    """Return sorted-key compact ASCII JSON with one terminal LF."""

    return _canonical_compact_bytes(value) + b"\n"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_array_sha256(values: Iterable[Any]) -> str:
    digest = hashlib.sha256(b"[")
    for position, value in enumerate(values):
        if position:
            digest.update(b",")
        digest.update(_canonical_compact_bytes(value))
    digest.update(b"]\n")
    return digest.hexdigest()


def document_derivation_metadata_identity(
    derivation: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind decoder and complete segmentation metadata outside row bytes."""

    return {
        "decoder": derivation["decoder"],
        "derivation_kind": derivation["derivation_kind"],
        "row_segmentation": derivation["row_segmentation"],
        "source_document_id": derivation["source_document_id"],
    }


def document_derivation_metadata_sha256(
    derivation: Mapping[str, Any],
) -> str:
    return canonical_sha256(document_derivation_metadata_identity(derivation))


def _require_exact_keys(
    row: Mapping[str, Any], expected: Sequence[str], label: str
) -> None:
    if len(row) != len(expected) or set(row) != set(expected):
        raise MissingReasonAuthorityError(f"{label} keyset")


def _require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise MissingReasonAuthorityError(f"{label} integer")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise MissingReasonAuthorityError(f"{label} lowercase SHA-256")
    return value


def iter_source_members(
    derivations: Iterable[Mapping[str, Any]],
) -> Iterator[SourceMember]:
    """Yield entries in document, source-row, and entry order."""

    member_position = 0
    for document_position, derivation in enumerate(derivations):
        source_document_id = derivation.get("source_document_id")
        if not isinstance(source_document_id, str) or not source_document_id:
            raise MissingReasonAuthorityError("source document ID")
        rows = derivation.get("canonical_rows")
        if not isinstance(rows, list) or derivation.get(
            "canonical_row_count"
        ) != len(rows):
            raise MissingReasonAuthorityError("canonical row array")
        for row_position, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise MissingReasonAuthorityError("canonical row object")
            row_id = f"{source_document_id}#row:{row_position}"
            if (
                row.get("source_row_position") != row_position
                or row.get("source_document_id") != source_document_id
                or row.get("codebook_field_row_id") != row_id
            ):
                raise MissingReasonAuthorityError("canonical row identity")
            locator_ids = row.get("source_locator_ids")
            if (
                not isinstance(locator_ids, list)
                or not locator_ids
                or not all(
                    isinstance(value, str) and value for value in locator_ids
                )
                or len(set(locator_ids)) != len(locator_ids)
            ):
                raise MissingReasonAuthorityError("source locator ID array")
            entries = row.get("normalized_entries")
            if not isinstance(entries, list) or row.get(
                "normalized_entry_count"
            ) != len(entries):
                raise MissingReasonAuthorityError("normalized entry array")
            for entry_position, entry in enumerate(entries):
                if not isinstance(entry, Mapping) or entry.get(
                    "entry_ref"
                ) != (f"{row_id}:entry:{entry_position}"):
                    raise MissingReasonAuthorityError("entry reference")
                yield SourceMember(
                    member_position=member_position,
                    source_document_position=document_position,
                    source_row_position=row_position,
                    entry_position=entry_position,
                    source_document_id=source_document_id,
                    codebook_field_row_id=row_id,
                    source_locator_ids=tuple(locator_ids),
                    entry=entry,
                )
                member_position += 1


def source_member_identity(member: SourceMember) -> list[Any]:
    """Return the source-occurrence identity; it claims no disposition."""

    for label, value in (
        ("member position", member.member_position),
        ("source document position", member.source_document_position),
        ("source row position", member.source_row_position),
        ("entry position", member.entry_position),
    ):
        _require_int(value, label)
    document_prefix = "psid-source-document:"
    if (
        not isinstance(member.source_document_id, str)
        or not member.source_document_id.startswith(document_prefix)
        or len(member.source_document_id) != len(document_prefix) + 64
        or any(
            character not in _HEX
            for character in member.source_document_id[len(document_prefix) :]
        )
    ):
        raise MissingReasonAuthorityError("source document ID")
    expected_row_id = (
        f"{member.source_document_id}#row:{member.source_row_position}"
    )
    if member.codebook_field_row_id != expected_row_id:
        raise MissingReasonAuthorityError("source row identity equation")
    locator_prefix = "psid-source-region:"
    if (
        not isinstance(member.source_locator_ids, tuple)
        or not member.source_locator_ids
        or len(set(member.source_locator_ids))
        != len(member.source_locator_ids)
        or any(
            not isinstance(locator, str)
            or not locator.startswith(locator_prefix)
            or len(locator) != len(locator_prefix) + 64
            or any(
                character not in _HEX
                for character in locator[len(locator_prefix) :]
            )
            for locator in member.source_locator_ids
        )
    ):
        raise MissingReasonAuthorityError("source locator identity array")

    entry_kind = member.entry.get("entry_kind")
    expected_entry_keys = (
        _LITERAL_ENTRY_KEYS
        if entry_kind == "literal"
        else _NUMERIC_RANGE_ENTRY_KEYS
    )
    _require_exact_keys(
        member.entry, expected_entry_keys, "source member entry"
    )
    lexeme = member.entry.get("source_value_lexeme")
    meaning = member.entry.get("source_meaning")
    if entry_kind not in ("literal", "numeric_range"):
        raise MissingReasonAuthorityError("entry kind")
    if not isinstance(lexeme, str) or not lexeme:
        raise MissingReasonAuthorityError("empty source value lexeme")
    if not isinstance(meaning, str) or not meaning:
        raise MissingReasonAuthorityError("empty source meaning")
    expected_ref = f"{expected_row_id}:entry:{member.entry_position}"
    if member.entry.get("entry_ref") != expected_ref:
        raise MissingReasonAuthorityError("entry reference equation")
    if member.entry.get("missing_reason_code") is not None:
        raise MissingReasonAuthorityError(
            "source member supplied reason value"
        )
    if member.entry.get("typed_value_unit") is not None:
        raise MissingReasonAuthorityError("source member supplied unit value")
    disposition = member.entry.get("typed_disposition")
    value_type = member.entry.get("value_type")
    if entry_kind == "literal":
        if member.entry.get("raw_token_hex") is not None:
            raise MissingReasonAuthorityError(
                "source member supplied raw token"
            )
        if disposition == "missing":
            if (
                value_type is not None
                or member.entry.get("canonical_value") is not None
            ):
                raise MissingReasonAuthorityError(
                    "malformed lexical candidate"
                )
        elif disposition not in ("json_integer", "rational") or (
            value_type != disposition
        ):
            raise MissingReasonAuthorityError(
                "malformed literal candidate branch"
            )
    elif disposition not in ("json_integer", "rational") or (
        value_type != disposition
    ):
        raise MissingReasonAuthorityError("malformed numeric range branch")
    try:
        from populace_dynamics.data.psid_codebook_extraction import (
            CodebookExtractionError,
            validate_normalized_entry,
        )

        validate_normalized_entry(
            member.entry, expected_row_id, member.entry_position
        )
    except (CodebookExtractionError, ValueError, ZeroDivisionError) as error:
        raise MissingReasonAuthorityError(
            "malformed normalized source entry"
        ) from error
    return [
        MEMBER_IDENTITY_VERSION,
        member.member_position,
        member.source_document_position,
        member.source_row_position,
        member.entry_position,
        member.source_document_id,
        member.codebook_field_row_id,
        list(member.source_locator_ids),
        member.entry["entry_ref"],
        entry_kind,
        lexeme,
        meaning,
    ]


def source_member_identity_sha256(member: SourceMember) -> str:
    return canonical_sha256(source_member_identity(member))


def missing_reason_preimage(member: SourceMember) -> list[Any]:
    return [REASON_PREIMAGE_VERSION, *source_member_identity(member)[1:]]


def missing_reason_code(member: SourceMember) -> str:
    """Construct an opaque occurrence code without authorizing its use."""

    if member.entry.get("entry_kind") != "literal":
        raise MissingReasonAuthorityError(
            "numeric range cannot carry a missing reason code"
        )
    return REASON_CODE_PREFIX + canonical_sha256(
        missing_reason_preimage(member)
    )


def candidate_is_missing(member: SourceMember) -> bool:
    """Validate and return the predecessor lexical candidate only."""

    source_member_identity(member)
    entry = member.entry
    if entry.get("missing_reason_code") is not None:
        raise MissingReasonAuthorityError("candidate supplied reason value")
    disposition = entry.get("typed_disposition")
    if disposition == "missing":
        if (
            entry.get("entry_kind") != "literal"
            or entry.get("value_type") is not None
            or entry.get("canonical_value") is not None
            or entry.get("typed_value_unit") is not None
        ):
            raise MissingReasonAuthorityError("malformed lexical candidate")
        return True
    if disposition not in ("json_integer", "rational"):
        raise MissingReasonAuthorityError("unsupported lexical candidate")
    if entry.get("value_type") != disposition:
        raise MissingReasonAuthorityError("candidate value type mismatch")
    return False


def fixture_conditional_missing_reason_value(
    member: SourceMember, authenticated_missing: bool | None
) -> str | None:
    """Exercise the conditional law in fixtures, never production.

    The Boolean stands in for a future, separately registered exact-occurrence
    authority that this amendment does not define.  Consequently this helper
    is not an admissible settlement entry point.  Production must call
    :func:`settle_missing_reason_codes`, which authenticates the complete
    current relation and then fails closed.  Passing ``None`` for a literal is
    the current state and therefore aborts.  Numeric ranges are structurally
    nonmissing under the inherited tagged union.
    """

    source_member_identity(member)
    if member.entry["entry_kind"] == "numeric_range":
        if authenticated_missing is True:
            raise MissingReasonAuthorityError(
                "numeric range conflicts with missing disposition"
            )
        if authenticated_missing not in (None, False):
            raise MissingReasonAuthorityError(
                "malformed disposition authority"
            )
        return None
    if authenticated_missing is None:
        raise MissingReasonAuthorityError(
            "source missing disposition is unadjudicated"
        )
    if type(authenticated_missing) is not bool:
        raise MissingReasonAuthorityError("malformed disposition authority")
    return missing_reason_code(member) if authenticated_missing else None


def fixture_conditional_missing_reason_value_from_claims(
    member: SourceMember,
    authenticated_claims: Sequence[bool],
) -> str | None:
    """Resolve unanimous synthetic claims and reject future conflicts.

    The claims are fixture inputs, not registered authority.  Requiring an
    explicit, unanimous nonempty sequence makes the conflict arm executable
    without implying that any such current source relation exists.
    """

    if (
        not isinstance(authenticated_claims, Sequence)
        or isinstance(authenticated_claims, (str, bytes, bytearray))
        or not authenticated_claims
        or any(type(claim) is not bool for claim in authenticated_claims)
    ):
        raise MissingReasonAuthorityError(
            "malformed future disposition claims"
        )
    if len(set(authenticated_claims)) != 1:
        raise MissingReasonAuthorityError(
            "conflicting future disposition authority"
        )
    return fixture_conditional_missing_reason_value(
        member, authenticated_claims[0]
    )


def fixture_conditional_missing_reason_relation(
    assignments: Sequence[tuple[SourceMember, Sequence[bool]]],
) -> tuple[str | None, ...]:
    """Exercise duplicate-assignment and opaque-code collision rejection."""

    if not assignments:
        raise MissingReasonAuthorityError("empty conditional fixture relation")
    seen_identities: set[str] = set()
    seen_codes: set[str] = set()
    values: list[str | None] = []
    for member, claims in assignments:
        identity = source_member_identity_sha256(member)
        if identity in seen_identities:
            raise MissingReasonAuthorityError(
                "duplicate conditional member assignment"
            )
        seen_identities.add(identity)
        value = fixture_conditional_missing_reason_value_from_claims(
            member, claims
        )
        if value is not None:
            if value in seen_codes:
                raise MissingReasonAuthorityError(
                    "opaque reason code collision"
                )
            seen_codes.add(value)
        values.append(value)
    return tuple(values)


def pack_disposition_bits(values: Iterable[bool]) -> tuple[str, int]:
    packed = bytearray()
    current = 0
    count = 0
    for value in values:
        if type(value) is not bool:
            raise MissingReasonAuthorityError("vector member is not Boolean")
        current |= int(value) << (7 - count % 8)
        count += 1
        if count % 8 == 0:
            packed.append(current)
            current = 0
    if count % 8:
        packed.append(current)
    return packed.hex(), count


def validate_disposition_vector(packed_hex: Any, member_count: Any) -> bytes:
    member_count = _require_int(member_count, "vector member count")
    if (
        not isinstance(packed_hex, str)
        or len(packed_hex) % 2
        or any(character not in _HEX for character in packed_hex)
    ):
        raise MissingReasonAuthorityError("vector hex")
    packed = bytes.fromhex(packed_hex)
    if len(packed) != (member_count + 7) // 8:
        raise MissingReasonAuthorityError("vector byte count")
    if member_count % 8 and packed:
        unused = 8 - member_count % 8
        if packed[-1] & ((1 << unused) - 1):
            raise MissingReasonAuthorityError("nonzero vector padding")
    return packed


def disposition_at(packed: bytes, position: int, member_count: int) -> bool:
    if type(position) is not int or not 0 <= position < member_count:
        raise MissingReasonAuthorityError("unregistered member position")
    if len(packed) != (member_count + 7) // 8:
        raise MissingReasonAuthorityError("unvalidated vector")
    return bool(packed[position // 8] & (1 << (7 - position % 8)))


_TOP_LEVEL_KEYS = (
    "artifact_id",
    "authority_boundary",
    "conditional_reason_code_law",
    "derivation_identity",
    "entry_kind_vector",
    "integrity",
    "lexical_candidate_vector",
    "registered_source_identity",
    "schema_version",
    "source_document_count",
    "source_document_rows",
    "source_document_rows_sha256",
    "source_member_census",
)

_SOURCE_DOCUMENT_ROW_KEYS = (
    "canonical_row_count",
    "canonical_row_domain_sha256",
    "canonical_source_path",
    "derivation_metadata_sha256",
    "interview_wave",
    "lexical_missing_candidate_count",
    "lexical_missing_candidate_identity_sha256",
    "member_end",
    "member_start",
    "normalized_entry_count",
    "position",
    "source_byte_size",
    "source_document_id",
    "source_locator_count",
    "source_locator_domain_sha256",
    "source_member_complete_domain_sha256",
    "source_member_identity_sha256",
    "source_sha256",
    "upstream_document_id",
)

_CENSUS_KEYS = (
    "canonical_source_row_count",
    "canonical_source_row_domain_sha256",
    "distinct_lexical_candidate_meaning_count",
    "distinct_lexical_candidate_meaning_sha256",
    "json_integer_candidate_count",
    "lexical_missing_candidate_count",
    "lexical_missing_candidate_identity_sha256",
    "lexical_missing_candidate_projection_sha256",
    "lexical_other_candidate_count",
    "literal_member_count",
    "numeric_range_member_count",
    "overlapping_candidate_phrase_counts",
    "overlapping_candidate_phrase_counts_sha256",
    "pdf_lexical_missing_candidate_count",
    "pdf_missing_candidate_field_count",
    "pdf_source_member_count",
    "pdf_source_row_count",
    "pdf_without_missing_candidate_field_count",
    "rational_candidate_count",
    "selected_exact_candidate_meaning_counts",
    "selected_exact_candidate_meaning_counts_sha256",
    "source_locator_count",
    "source_locator_domain_sha256",
    "source_member_complete_domain_sha256",
    "source_member_count",
    "source_member_identity_sha256",
    "value_label_lexical_missing_candidate_count",
)

_VECTOR_KEYS = (
    "encoding",
    "one_count",
    "packed_byte_count",
    "packed_hex",
    "packed_sha256",
    "source_member_count",
    "zero_count",
)


def _validate_vector(
    vector: Any,
    *,
    encoding: str,
    one_count: int,
    zero_count: int,
    packed_sha256: str,
) -> None:
    if not isinstance(vector, Mapping):
        raise MissingReasonAuthorityError("vector object")
    _require_exact_keys(vector, _VECTOR_KEYS, "vector")
    if vector.get("encoding") != encoding:
        raise MissingReasonAuthorityError("vector encoding")
    if _require_int(vector.get("source_member_count"), "vector count") != (
        EXPECTED_MEMBER_COUNT
    ):
        raise MissingReasonAuthorityError("vector member count pin")
    packed = validate_disposition_vector(
        vector.get("packed_hex"), vector.get("source_member_count")
    )
    if _require_int(vector.get("packed_byte_count"), "vector bytes") != len(
        packed
    ):
        raise MissingReasonAuthorityError("vector byte equation")
    if (
        vector.get("packed_sha256") != sha256_bytes(packed)
        or vector.get("packed_sha256") != packed_sha256
    ):
        raise MissingReasonAuthorityError("vector digest pin")
    if _require_int(vector.get("one_count"), "vector one count") != one_count:
        raise MissingReasonAuthorityError("vector one-count pin")
    if (
        _require_int(vector.get("zero_count"), "vector zero count")
        != zero_count
    ):
        raise MissingReasonAuthorityError("vector zero-count pin")
    if sum(byte.bit_count() for byte in packed) != one_count:
        raise MissingReasonAuthorityError("vector population equation")


def validate_authority_artifact(artifact: Mapping[str, Any]) -> None:
    """Validate every nested boundary-artifact pin and equation."""

    if not isinstance(artifact, Mapping):
        raise MissingReasonAuthorityError("authority artifact object")
    _require_exact_keys(artifact, _TOP_LEVEL_KEYS, "authority top level")
    if (
        artifact.get("schema_version") != SCHEMA_VERSION
        or artifact.get("artifact_id") != ARTIFACT_ID
    ):
        raise MissingReasonAuthorityError("authority identity")

    registered = artifact.get("registered_source_identity")
    expected_registered = {
        "projected_source_rows_sha256": EXPECTED_PROJECTED_SOURCE_ROWS_SHA256,
        "registered_source_byte_size": EXPECTED_REGISTERED_SOURCE_BYTE_SIZE,
        "registered_source_count": EXPECTED_REGISTERED_SOURCE_COUNT,
        "registered_source_rows_sha256": EXPECTED_REGISTERED_SOURCE_ROWS_SHA256,
        "registry_byte_size": EXPECTED_REGISTRY_BYTE_SIZE,
        "registry_path": EXPECTED_REGISTRY_PATH,
        "registry_sha256": EXPECTED_REGISTRY_SHA256,
        "source_file_mismatch_count": 0,
        "source_file_verification": "size_and_full_sha256_match",
    }
    if (
        not isinstance(registered, Mapping)
        or dict(registered) != expected_registered
    ):
        raise MissingReasonAuthorityError("registered source pins")
    for key in (
        "registered_source_byte_size",
        "registered_source_count",
        "registry_byte_size",
        "source_file_mismatch_count",
    ):
        _require_int(registered[key], f"registered {key}")

    rows = artifact.get("source_document_rows")
    if not isinstance(rows, list) or _require_int(
        artifact.get("source_document_count"), "source document count"
    ) != len(rows):
        raise MissingReasonAuthorityError("source document rows")
    if len(rows) != EXPECTED_DOCUMENT_COUNT:
        raise MissingReasonAuthorityError("source document count pin")
    rows_sha = canonical_sha256(rows)
    if artifact.get("source_document_rows_sha256") != rows_sha or rows_sha != (
        EXPECTED_SOURCE_DOCUMENT_ROWS_SHA256
    ):
        raise MissingReasonAuthorityError("source document row digest")
    member_end = 0
    row_total = 0
    candidate_total = 0
    locator_total = 0
    identities: set[str] = set()
    paths: set[str] = set()
    for position, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise MissingReasonAuthorityError("source document row object")
        _require_exact_keys(
            row, _SOURCE_DOCUMENT_ROW_KEYS, "source document row"
        )
        for key in (
            "canonical_row_count",
            "interview_wave",
            "lexical_missing_candidate_count",
            "member_end",
            "member_start",
            "normalized_entry_count",
            "position",
            "source_byte_size",
            "source_locator_count",
        ):
            _require_int(row[key], f"source document {key}")
        if row["position"] != position or row["member_start"] != member_end:
            raise MissingReasonAuthorityError(
                "source document order or interval"
            )
        member_end = row["member_end"]
        if member_end - row["member_start"] != row["normalized_entry_count"]:
            raise MissingReasonAuthorityError("source member interval length")
        if (
            row["lexical_missing_candidate_count"]
            > row["normalized_entry_count"]
        ):
            raise MissingReasonAuthorityError("document candidate count")
        for key in (
            "canonical_row_domain_sha256",
            "derivation_metadata_sha256",
            "lexical_missing_candidate_identity_sha256",
            "source_locator_domain_sha256",
            "source_member_complete_domain_sha256",
            "source_member_identity_sha256",
            "source_sha256",
        ):
            _require_sha256(row[key], f"source document {key}")
        for key in (
            "canonical_source_path",
            "source_document_id",
            "upstream_document_id",
        ):
            if not isinstance(row[key], str) or not row[key]:
                raise MissingReasonAuthorityError(f"source document {key}")
        if (
            row["source_document_id"] in identities
            or row["canonical_source_path"] in paths
        ):
            raise MissingReasonAuthorityError("duplicate source document")
        identities.add(row["source_document_id"])
        paths.add(row["canonical_source_path"])
        row_total += row["canonical_row_count"]
        candidate_total += row["lexical_missing_candidate_count"]
        locator_total += row["source_locator_count"]
    if member_end != EXPECTED_MEMBER_COUNT:
        raise MissingReasonAuthorityError("source member exact cover")

    census = artifact.get("source_member_census")
    if not isinstance(census, Mapping):
        raise MissingReasonAuthorityError("source member census")
    _require_exact_keys(census, _CENSUS_KEYS, "source member census")
    expected_counts = {
        "canonical_source_row_count": EXPECTED_CANONICAL_ROW_COUNT,
        "distinct_lexical_candidate_meaning_count": (
            EXPECTED_DISTINCT_CANDIDATE_MEANING_COUNT
        ),
        "json_integer_candidate_count": 326_868,
        "lexical_missing_candidate_count": EXPECTED_LEXICAL_MISSING_COUNT,
        "lexical_other_candidate_count": EXPECTED_LEXICAL_OTHER_COUNT,
        "literal_member_count": EXPECTED_LITERAL_COUNT,
        "numeric_range_member_count": EXPECTED_NUMERIC_RANGE_COUNT,
        "pdf_lexical_missing_candidate_count": (
            EXPECTED_PDF_LEXICAL_MISSING_COUNT
        ),
        "pdf_missing_candidate_field_count": 83_863,
        "pdf_source_member_count": EXPECTED_PDF_MEMBER_COUNT,
        "pdf_source_row_count": EXPECTED_PDF_ROW_COUNT,
        "pdf_without_missing_candidate_field_count": 5_736,
        "rational_candidate_count": 3_742,
        "source_locator_count": EXPECTED_SOURCE_LOCATOR_COUNT,
        "source_member_count": EXPECTED_MEMBER_COUNT,
        "value_label_lexical_missing_candidate_count": (
            EXPECTED_LABEL_LEXICAL_MISSING_COUNT
        ),
    }
    for key, expected in expected_counts.items():
        if _require_int(census.get(key), f"census {key}") != expected:
            raise MissingReasonAuthorityError(f"census count pin: {key}")
    if row_total != census["canonical_source_row_count"]:
        raise MissingReasonAuthorityError("canonical row count equation")
    if candidate_total != census["lexical_missing_candidate_count"]:
        raise MissingReasonAuthorityError("candidate count equation")
    if locator_total != census["source_locator_count"]:
        raise MissingReasonAuthorityError("locator count equation")
    if census["literal_member_count"] + census[
        "numeric_range_member_count"
    ] != (census["source_member_count"]):
        raise MissingReasonAuthorityError("entry-kind partition equation")
    if (
        census["lexical_missing_candidate_count"]
        + census["lexical_other_candidate_count"]
        != census["source_member_count"]
    ):
        raise MissingReasonAuthorityError("candidate partition equation")
    for key, expected in EXPECTED_CENSUS_SHA256S.items():
        if _require_sha256(census.get(key), key) != expected:
            raise MissingReasonAuthorityError(f"census digest pin: {key}")
    if census.get("lexical_missing_candidate_projection_sha256") != (
        EXPECTED_MISSING_CANDIDATE_PROJECTION_SHA256
    ):
        raise MissingReasonAuthorityError("candidate projection digest")
    if census.get("selected_exact_candidate_meaning_counts") != (
        EXPECTED_SELECTED_EXACT_MEANING_COUNTS
    ) or census.get("selected_exact_candidate_meaning_counts_sha256") != (
        EXPECTED_SELECTED_EXACT_MEANING_COUNTS_SHA256
    ):
        raise MissingReasonAuthorityError("selected candidate meaning counts")
    if canonical_sha256(census["selected_exact_candidate_meaning_counts"]) != (
        census["selected_exact_candidate_meaning_counts_sha256"]
    ):
        raise MissingReasonAuthorityError("selected meaning count equation")
    if census.get("overlapping_candidate_phrase_counts") != (
        EXPECTED_OVERLAPPING_PHRASE_COUNTS
    ) or census.get("overlapping_candidate_phrase_counts_sha256") != (
        EXPECTED_OVERLAPPING_PHRASE_COUNTS_SHA256
    ):
        raise MissingReasonAuthorityError("candidate phrase counts")
    if canonical_sha256(census["overlapping_candidate_phrase_counts"]) != (
        census["overlapping_candidate_phrase_counts_sha256"]
    ):
        raise MissingReasonAuthorityError("phrase count equation")

    _validate_vector(
        artifact.get("entry_kind_vector"),
        encoding=ENTRY_KIND_VECTOR_ENCODING,
        one_count=EXPECTED_LITERAL_COUNT,
        zero_count=EXPECTED_NUMERIC_RANGE_COUNT,
        packed_sha256=EXPECTED_ENTRY_KIND_PACKED_SHA256,
    )
    _validate_vector(
        artifact.get("lexical_candidate_vector"),
        encoding=LEXICAL_VECTOR_ENCODING,
        one_count=EXPECTED_LEXICAL_MISSING_COUNT,
        zero_count=EXPECTED_LEXICAL_OTHER_COUNT,
        packed_sha256=EXPECTED_LEXICAL_PACKED_SHA256,
    )

    law = artifact.get("conditional_reason_code_law")
    expected_law = {
        "current_literal_action": "abort_without_emission",
        "current_literal_disposition": (
            "unadjudicated_source_missing_disposition"
        ),
        "future_authenticated_missing_literal_action": (
            "nonempty_opaque_source_occurrence_code"
        ),
        "future_authenticated_nonmissing_literal_action": "json_null",
        "member_identity_version": MEMBER_IDENTITY_VERSION,
        "numeric_range_action": "json_null",
        "reason_code_prefix": REASON_CODE_PREFIX,
        "reason_preimage_version": REASON_PREIMAGE_VERSION,
        "semantic_equivalence_claimed": False,
        "unknown_or_conflict_action": "abort_without_emission",
    }
    if not isinstance(law, Mapping) or dict(law) != expected_law:
        raise MissingReasonAuthorityError("conditional reason-code law")
    if law["semantic_equivalence_claimed"] is not False:
        raise MissingReasonAuthorityError("semantic-equivalence Boolean")

    boundary = artifact.get("authority_boundary")
    if not isinstance(boundary, Mapping):
        raise MissingReasonAuthorityError("authority boundary")
    boundary_keys = (
        "authorized_current_literal_disposition_count",
        "dictionary_missing_declaration_scope",
        "directly_disproven_candidate_count",
        "directly_disproven_candidate_sha256",
        "directly_disproven_candidates",
        "inherited_dictionary_missing_declaration_count",
        "inherited_dictionary_missing_relation_sha256",
        "lexical_candidate_is_source_authority",
        "minimum_counterexample_count",
        "minimum_counterexample_sha256",
        "minimum_counterexamples",
        "numeric_range_rejection_witnesses",
        "opaque_occurrence_code_conditionally_supported",
        "rejection_class_witness_count",
        "rejection_class_witness_sha256",
        "rejection_class_witnesses",
        "source_defines_missing_disposition_column",
        "source_defines_missing_disposition_vocabulary",
        "source_defines_reason_code_column",
        "source_defines_reason_vocabulary",
        "unadjudicated_literal_count",
    )
    _require_exact_keys(boundary, boundary_keys, "authority boundary")
    false_keys = (
        "lexical_candidate_is_source_authority",
        "source_defines_missing_disposition_column",
        "source_defines_missing_disposition_vocabulary",
        "source_defines_reason_code_column",
        "source_defines_reason_vocabulary",
    )
    if any(boundary[key] is not False for key in false_keys):
        raise MissingReasonAuthorityError("boundary overreach")
    if boundary["opaque_occurrence_code_conditionally_supported"] is not True:
        raise MissingReasonAuthorityError(
            "conditional occurrence-code support"
        )
    if (
        _require_int(
            boundary["authorized_current_literal_disposition_count"],
            "authorized literal count",
        )
        != 0
        or _require_int(
            boundary["unadjudicated_literal_count"],
            "unadjudicated literal count",
        )
        != EXPECTED_LITERAL_COUNT
    ):
        raise MissingReasonAuthorityError("literal authority boundary")
    if boundary["dictionary_missing_declaration_scope"] != (
        "inherited_86_document_compiler_fact_not_reproduced_by_47_source_A11"
    ):
        raise MissingReasonAuthorityError("dictionary scope boundary")
    if (
        _require_int(
            boundary["inherited_dictionary_missing_declaration_count"],
            "dictionary missing declaration count",
        )
        != EXPECTED_DICTIONARY_MISSING_DECLARATION_COUNT
        or boundary["inherited_dictionary_missing_relation_sha256"]
        != EXPECTED_EMPTY_ARRAY_SHA256
    ):
        raise MissingReasonAuthorityError("inherited dictionary fact")

    counterexamples = boundary.get("minimum_counterexamples")
    if not isinstance(counterexamples, list) or _require_int(
        boundary.get("minimum_counterexample_count"), "counterexample count"
    ) != len(counterexamples):
        raise MissingReasonAuthorityError("counterexample rows")
    if (
        len(counterexamples) != EXPECTED_COUNTEREXAMPLE_COUNT
        or canonical_sha256(counterexamples)
        != boundary.get("minimum_counterexample_sha256")
        or boundary.get("minimum_counterexample_sha256")
        != EXPECTED_COUNTEREXAMPLE_SHA256
    ):
        raise MissingReasonAuthorityError("counterexample digest pin")
    directly_disproven = boundary.get("directly_disproven_candidates")
    if not isinstance(directly_disproven, list) or _require_int(
        boundary.get("directly_disproven_candidate_count"),
        "directly disproven count",
    ) != len(directly_disproven):
        raise MissingReasonAuthorityError("directly disproven rows")
    if (
        len(directly_disproven) != EXPECTED_DIRECTLY_DISPROVEN_COUNT
        or (
            canonical_sha256(directly_disproven)
            != boundary.get("directly_disproven_candidate_sha256")
        )
        or boundary.get("directly_disproven_candidate_sha256")
        != (EXPECTED_DIRECTLY_DISPROVEN_SHA256)
    ):
        raise MissingReasonAuthorityError("directly disproven digest pin")

    range_witnesses = boundary.get("numeric_range_rejection_witnesses")
    if not isinstance(range_witnesses, Mapping):
        raise MissingReasonAuthorityError("numeric range witnesses")
    _require_exact_keys(
        range_witnesses,
        ("domain_sha256", "row_count", "rows"),
        "numeric range witnesses",
    )
    range_rows = range_witnesses.get("rows")
    if not isinstance(range_rows, list) or _require_int(
        range_witnesses.get("row_count"), "numeric range witness count"
    ) != len(range_rows):
        raise MissingReasonAuthorityError("numeric range witness rows")
    if (
        len(range_rows) != 21
        or canonical_sha256(range_rows) != range_witnesses.get("domain_sha256")
        or range_witnesses.get("domain_sha256")
        != EXPECTED_RANGE_REJECTION_SHA256
    ):
        raise MissingReasonAuthorityError("numeric range witness digest")

    rejection_rows = boundary.get("rejection_class_witnesses")
    if not isinstance(rejection_rows, list) or _require_int(
        boundary.get("rejection_class_witness_count"),
        "rejection class witness count",
    ) != len(rejection_rows):
        raise MissingReasonAuthorityError("rejection class witnesses")
    if canonical_sha256(rejection_rows) != boundary.get(
        "rejection_class_witness_sha256"
    ) or boundary.get("rejection_class_witness_sha256") != (
        EXPECTED_REJECTION_CLASS_SHA256
    ):
        raise MissingReasonAuthorityError("rejection class digest")

    derivation = artifact.get("derivation_identity")
    if not isinstance(derivation, Mapping):
        raise MissingReasonAuthorityError("derivation identity")
    _require_exact_keys(
        derivation,
        (
            "implementation_file_domain_sha256",
            "implementation_files",
            "interface_version",
            "pdftotext_arguments",
            "pdftotext_version",
        ),
        "derivation identity",
    )
    if (
        derivation.get("interface_version")
        != ("amendment_11_missing_reason_fail_closed.v1")
        or derivation.get("pdftotext_arguments")
        != [
            "-layout",
            "-enc",
            "UTF-8",
        ]
        or derivation.get("pdftotext_version") != "26.04.0"
    ):
        raise MissingReasonAuthorityError(
            "derivation implementation interface"
        )
    files = derivation.get("implementation_files")
    if not isinstance(files, list) or len(files) != 3:
        raise MissingReasonAuthorityError("implementation file rows")
    repository_root = Path(__file__).resolve().parents[3]
    for position, row in enumerate(files):
        if not isinstance(row, Mapping):
            raise MissingReasonAuthorityError("implementation row")
        _require_exact_keys(
            row,
            ("byte_size", "path", "position", "sha256"),
            "implementation row",
        )
        if type(row.get("position")) is not int or row["position"] != position:
            raise MissingReasonAuthorityError("implementation order")
        if (
            _require_int(
                row.get("byte_size"), "implementation bytes", minimum=1
            )
            < 1
        ):
            raise MissingReasonAuthorityError("implementation bytes")
        _require_sha256(row.get("sha256"), "implementation digest")
        if row.get("path") != EXPECTED_IMPLEMENTATION_PATHS[position]:
            raise MissingReasonAuthorityError("implementation path")
        try:
            raw = (repository_root / row["path"]).read_bytes()
        except OSError as error:
            raise MissingReasonAuthorityError(
                "implementation unreadable"
            ) from error
        if len(raw) != row["byte_size"] or sha256_bytes(raw) != row["sha256"]:
            raise MissingReasonAuthorityError("implementation byte drift")
    if derivation.get("implementation_file_domain_sha256") != canonical_sha256(
        files
    ):
        raise MissingReasonAuthorityError("implementation domain digest")

    integrity = artifact.get("integrity")
    if not isinstance(integrity, Mapping):
        raise MissingReasonAuthorityError("artifact integrity")
    _require_exact_keys(
        integrity,
        ("canonicalization", "content_sha256", "reproduced_from_source_bytes"),
        "artifact integrity",
    )
    if (
        integrity.get("canonicalization")
        != (
            "section-10.1 UTF-8 sorted-key compact JSON with one terminal LF; "
            "content_sha256 computed with itself set to 64 zeroes"
        )
        or integrity.get("reproduced_from_source_bytes") is not True
    ):
        raise MissingReasonAuthorityError("artifact integrity law")
    expected_content = _require_sha256(
        integrity.get("content_sha256"), "artifact content digest"
    )
    candidate = json.loads(json.dumps(artifact, allow_nan=False))
    candidate["integrity"]["content_sha256"] = "0" * 64
    if sha256_bytes(canonical_json_bytes(candidate)) != expected_content:
        raise MissingReasonAuthorityError("artifact content digest")


def preflight_source_derivations(
    derivations: Sequence[Mapping[str, Any]],
    authority: Mapping[str, Any],
) -> None:
    """Authenticate the complete candidate relation before naming its blocker."""

    validate_authority_artifact(authority)
    if len(derivations) != EXPECTED_DOCUMENT_COUNT:
        raise MissingReasonAuthorityError("source document count drift")
    try:
        from populace_dynamics.data.psid_codebook_extraction import (
            CodebookExtractionError,
            validate_document_derivation,
        )
    except ImportError as error:  # pragma: no cover - broken installation
        raise MissingReasonAuthorityError(
            "source derivation validator unavailable"
        ) from error

    source_rows = authority["source_document_rows"]
    kind_vector = authority["entry_kind_vector"]
    lexical_vector = authority["lexical_candidate_vector"]
    packed_kinds = validate_disposition_vector(
        kind_vector["packed_hex"], kind_vector["source_member_count"]
    )
    packed_candidates = validate_disposition_vector(
        lexical_vector["packed_hex"], lexical_vector["source_member_count"]
    )
    member_position = 0
    for document_position, (derivation, source_row) in enumerate(
        zip(derivations, source_rows, strict=True)
    ):
        try:
            validate_document_derivation(derivation)
        except (
            CodebookExtractionError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            raise MissingReasonAuthorityError(
                "malformed source document derivation"
            ) from error
        if source_row["position"] != document_position:
            raise MissingReasonAuthorityError("source document order drift")
        if (
            derivation["source_document_id"]
            != source_row["source_document_id"]
        ):
            raise MissingReasonAuthorityError("source document identity drift")
        if source_row["member_start"] != member_position:
            raise MissingReasonAuthorityError("source member interval drift")
        if (
            derivation["canonical_row_count"]
            != source_row["canonical_row_count"]
            or derivation["canonical_row_domain_sha256"]
            != source_row["canonical_row_domain_sha256"]
        ):
            raise MissingReasonAuthorityError("canonical source row drift")
        if (
            document_derivation_metadata_sha256(derivation)
            != source_row["derivation_metadata_sha256"]
        ):
            raise MissingReasonAuthorityError(
                "source derivation metadata drift"
            )

        members: list[SourceMember] = []
        for local_member in iter_source_members((derivation,)):
            member = SourceMember(
                member_position=member_position,
                source_document_position=document_position,
                source_row_position=local_member.source_row_position,
                entry_position=local_member.entry_position,
                source_document_id=local_member.source_document_id,
                codebook_field_row_id=local_member.codebook_field_row_id,
                source_locator_ids=local_member.source_locator_ids,
                entry=local_member.entry,
            )
            expected_literal = disposition_at(
                packed_kinds, member_position, EXPECTED_MEMBER_COUNT
            )
            expected_candidate = disposition_at(
                packed_candidates, member_position, EXPECTED_MEMBER_COUNT
            )
            if (member.entry["entry_kind"] == "literal") != expected_literal:
                raise MissingReasonAuthorityError("entry-kind vector drift")
            if candidate_is_missing(member) != expected_candidate:
                raise MissingReasonAuthorityError(
                    "lexical candidate vector drift"
                )
            members.append(member)
            member_position += 1
        if source_row["member_end"] != member_position:
            raise MissingReasonAuthorityError("source member interval drift")

        identities = [source_member_identity(member) for member in members]
        candidate_identities = [
            identity
            for member, identity in zip(members, identities, strict=True)
            if candidate_is_missing(member)
        ]
        locators = derivation["row_segmentation"]["source_region_locators"]
        observed = {
            "lexical_missing_candidate_count": len(candidate_identities),
            "lexical_missing_candidate_identity_sha256": canonical_sha256(
                candidate_identities
            ),
            "normalized_entry_count": len(members),
            "source_locator_count": len(locators),
            "source_locator_domain_sha256": canonical_sha256(
                [
                    [derivation["source_document_id"], locator]
                    for locator in locators
                ]
            ),
            "source_member_complete_domain_sha256": canonical_sha256(
                [
                    [
                        member.source_document_id,
                        member.codebook_field_row_id,
                        member.entry_position,
                        member.entry,
                    ]
                    for member in members
                ]
            ),
            "source_member_identity_sha256": canonical_sha256(identities),
        }
        for key, value in observed.items():
            if source_row[key] != value:
                raise MissingReasonAuthorityError(
                    f"complete source relation drift: {key}"
                )
    if member_position != EXPECTED_MEMBER_COUNT:
        raise MissingReasonAuthorityError("source member exact-cover drift")


def settle_missing_reason_codes(
    derivations: Sequence[Mapping[str, Any]],
    authority: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Refuse production settlement after complete source preflight."""

    preflight_source_derivations(derivations, authority)
    raise MissingReasonAuthorityError(
        "source missing disposition is unadjudicated for 524590 literals"
    )
