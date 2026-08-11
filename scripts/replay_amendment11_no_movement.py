#!/usr/bin/env python3
"""Fail-closed Amendment 11 downstream replay preflight.

The production relation cannot presently be replayed.  Registered source
bytes explicitly authorize 52 opaque occurrence codes but do not determine
the disposition of the other 524,538 literal entries; the old 231,263-member
lexical vector is a candidate classifier, not source authority.  There is
therefore no complete settled input relation for A11-R05.  Revision 12's
capacity result remains an authenticated historical census, but Amendment 11
cannot carry it forward: a future disposition authority may change the
terminal assignment and storage populations.

This module validates the source-boundary census and the already-ratified
aggregates only as historical evidence, then raises the named source-authority
blocker.  It never turns copied Amendment 10 assignments, its capacity result,
or lexical candidates into an Amendment 11 pass.

``replay_constructible_fixture`` is the deliberately separate, satisfiable
test seam.  Conditional on explicitly supplied synthetic dispositions, it
rebuilds classifications from complete synthetic settled fields, checks that
terminal selection is insensitive to the spelling of a nonempty reason code,
recounts storage and the T-plus/T-minus partition, and constructs all six
positions of a small relation identity.  The fixture supplies no evidence for
the production disposition.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from populace_dynamics.data.psid_missing_reason_authority import (  # noqa: E402
    MissingReasonAuthorityError,
    settle_missing_reason_codes,
    validate_authority_artifact,
)
from scripts import (  # noqa: E402
    rebuild_amendment11_missing_reason_authority as authority_builder,
)
from scripts.build_amendment10_successor_census import (  # noqa: E402
    EXPECTED_A10_R04_PINS,
)

FIXTURE_IDENTITY_LITERAL = (
    "amendment_11_constructible_fixture_full_relation_identity"
)
AUTHORITY_ARTIFACT = (
    REPOSITORY_ROOT
    / "data"
    / "external"
    / "psid_missing_reason_code_authority_v1.json"
)
REGISTERED_SOURCE_ROOT = Path("~/PolicyEngine/psid-data").expanduser()
SOURCE_REGISTRY = REPOSITORY_ROOT / authority_builder.EXPECTED_REGISTRY_PATH
PRODUCTION_FIELD_COUNT = 89_599
SOURCE_MEMBER_COUNT = 561_873
SOURCE_LITERAL_ENTRY_COUNT = 524_590
SOURCE_NUMERIC_RANGE_ENTRY_COUNT = 37_283
SOURCE_AUTHORIZED_MISSING_LITERAL_COUNT = 52
UNADJUDICATED_LITERAL_ENTRY_COUNT = 524_538
LEXICAL_MISSING_CANDIDATE_COUNT = 231_263
LITERAL_LEXICAL_OTHER_COUNT = 293_327
ALL_MEMBER_LEXICAL_OTHER_COUNT = 330_610
DIRECTLY_DISPROVEN_LEXICAL_CANDIDATE_MINIMUM = 61
CONTEXT_REQUIRED_LEXICAL_CANDIDATE_MINIMUM = 118
EMPTY_ARRAY_SHA256 = (
    "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
)
EXPECTED_COUNT_ARRAY_SHA256 = (
    "2347179a44340f53dff3770a2dc23a6bfebffac755ed94efe11dd94543131071"
)
EXPECTED_ORDERED_ASSIGNMENT_SHA256 = (
    "463ab96ca73185dd5e269fb3c8c0891dc358e90f3cb4088590b5c442240d652b"
)
EXPECTED_FAILURE_REASON_ROWS_BYTE_COUNT = 211_195
EXPECTED_FAILURE_REASON_ROWS_SHA256 = (
    "024ea03ad9c4f4cac6c490e3899bba74a9c78f7de1737cd5c4a7187b69b5bfda"
)
EXPECTED_SOURCE_SETTLEMENT_BLOCKER = (
    "source missing disposition is unadjudicated for 524538 literals"
)

TERMINALS = (
    "compiled_source_numeric_grammar",
    "compiled_source_numeric_grammar_padding_underdetermined_exact_replay",
    (
        "compiled_source_numeric_grammar_"
        "finite_domain_arm_ambiguous_exact_replay"
    ),
    "compiled_source_numeric_grammar_partial_range_exact_replay",
    "value_code_domain_no_numeric_grammar",
    "value_code_range_physical_rendering_unestablished",
    "nonnumeric_source_field_outside_numeric_grammar",
    "conflicting_source_numeric_format",
    "unsupported_source_numeric_format",
    "incomplete_source_numeric_authority",
)
T_PLUS = frozenset(TERMINALS[:7])
T_MINUS = frozenset(TERMINALS[7:])
EXPECTED_TERMINAL_VECTOR = (
    8_025,
    273,
    77,
    1,
    67_316,
    1_145,
    0,
    1,
    421,
    12_340,
)
EXPECTED_T_PLUS_COUNT = 76_837
EXPECTED_T_MINUS_COUNT = 12_762

EXPECTED_COMPLETED_FIELD_COUNT = 8_376
EXPECTED_NUMERIC_RANGE_ENTRY_COUNT = 8_519
EXPECTED_LOGICAL_MEMBER_COUNT = 376_171_374_879
EXPECTED_EXPLICIT_MEMBER_COUNT = 2_051_179
EXPECTED_ANALYTIC_MEMBER_COUNT = 376_169_323_700
EXPECTED_EMPTY_OBJECT_FLOOR_BYTES = 1_128_514_124_639
EXPECTED_HISTORICAL_TWO_SHAPE_FLOOR_BYTES = 122_255_013_079_550
EXPECTED_COMPILED_DECOMPOSITION = (
    (8_025, 8_167, 376_170_541_305),
    (273, 273, 18_270),
    (77, 77, 122_604),
    (1, 2, 692_700),
)

EXPECTED_SEVEN_KEY_MEMBER_COUNT = 376_169_049_272
EXPECTED_SIX_KEY_RATIONAL_MEMBER_COUNT = 999
EXPECTED_SIX_KEY_INTEGER_MEMBER_COUNT = 9_999
EXPECTED_FOUR_KEY_MEMBER_COUNT = 263_430
EXPECTED_FOUR_SHAPE_FLOOR_BYTES = 122_255_013_691_442
MEASURED_CAPACITY_REFERENCE_TIB = Decimal("1.304")

NUMERIC_ROW_KEYS = (
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
FIELD_SOURCE_KEYS = (
    "implementation_identity",
    "document_derivations",
    "document_derivation_count",
    "document_derivation_domain_sha256",
    "numeric_grammar_derivation_rows",
    "numeric_grammar_derivation_row_count",
    "numeric_grammar_derivation_keyset_sha256",
    "numeric_grammar_derivation_domain_sha256",
    "status",
)


class ReplayError(ValueError):
    """An Amendment-11 downstream replay or fixture is invalid."""


class SourceMissingDispositionUnderdetermined(ReplayError):
    """Registered sources do not supply a total missing disposition."""

    code = "blocked_source_missing_disposition_underdetermined"

    def __init__(self, evidence: Mapping[str, Any]) -> None:
        self.evidence = dict(evidence)
        super().__init__(
            f"{self.code}: registered sources do not determine a missing "
            f"disposition for {evidence['blocked_literal_entry_count']} "
            "literal entries; no complete settled relation exists"
        )


@dataclass(frozen=True)
class FixtureStorage:
    """One constructible fixture field's range-member decomposition."""

    logical_member_count: int
    explicit_member_count: int
    analytic_member_count: int
    four_shape_floor_bytes: int


@dataclass(frozen=True)
class FixtureField:
    """One complete synthetic settled field used only by the test seam."""

    numeric_grammar_derivation_row: Mapping[str, Any]
    settled_entries: tuple[Mapping[str, Any], ...]
    resolution_reason: str | None
    storage: FixtureStorage


def canonical_json_bytes(value: Any) -> bytes:
    """Return section-10.1 canonical JSON with one terminal LF."""

    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ReplayError("noncanonical fixture value") from error


def canonical_sha256(value: Any) -> str:
    """Hash one standalone canonical JSON value."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def validate_committed_authority(
    path: Path = AUTHORITY_ARTIFACT,
) -> Mapping[str, Any]:
    """Bind R05 to the canonical, validator-accepted audit artifact."""

    try:
        raw = path.read_bytes()
        authority = json.loads(raw.decode("utf-8"))
        if raw != canonical_json_bytes(authority):
            raise ReplayError("authority artifact is not canonical")
        validate_authority_artifact(authority)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReplayError("authority artifact is unreadable") from error
    except MissingReasonAuthorityError as error:
        raise ReplayError("authority artifact validation failed") from error
    return authority


def _require_plain_nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ReplayError(f"{label} must be a nonnegative JSON integer")
    return value


def _production_floor() -> int:
    products = (
        EXPECTED_SEVEN_KEY_MEMBER_COUNT * 325,
        EXPECTED_SIX_KEY_RATIONAL_MEMBER_COUNT * 377,
        EXPECTED_SIX_KEY_INTEGER_MEMBER_COUNT * 381,
        EXPECTED_FOUR_KEY_MEMBER_COUNT * 260,
    )
    return sum(products)


def historical_predecessor_capacity_evidence() -> dict[str, Any]:
    """Validate §24's census without carrying it into Amendment 11."""

    pins = EXPECTED_A10_R04_PINS
    observed_statuses = tuple(status for status, _count in pins.count_rows)
    observed_vector = tuple(count for _status, count in pins.count_rows)
    if observed_statuses != TERMINALS:
        raise ReplayError("ratified §24 terminal order drift")
    if observed_vector != EXPECTED_TERMINAL_VECTOR:
        raise ReplayError("ratified §24 terminal vector drift")
    if pins.count_array_sha256 != EXPECTED_COUNT_ARRAY_SHA256:
        raise ReplayError("ratified §24 count-array digest drift")
    if pins.ordered_assignment_sha256 != EXPECTED_ORDERED_ASSIGNMENT_SHA256:
        raise ReplayError("ratified §24 ordered-assignment digest drift")
    if sum(observed_vector) != PRODUCTION_FIELD_COUNT:
        raise ReplayError("ratified §24 field count drift")
    if (
        sum(observed_vector[:7]),
        sum(observed_vector[7:]),
    ) != (EXPECTED_T_PLUS_COUNT, EXPECTED_T_MINUS_COUNT):
        raise ReplayError("ratified §24 T-plus/T-minus partition drift")
    if len(pins.failure_reason_rows) != 8:
        raise ReplayError("ratified §24 failure census drift")
    if pins.failure_reason_rows_byte_count != (
        EXPECTED_FAILURE_REASON_ROWS_BYTE_COUNT
    ):
        raise ReplayError("ratified §24 failure census byte-count drift")
    if pins.failure_reason_rows_sha256 != EXPECTED_FAILURE_REASON_ROWS_SHA256:
        raise ReplayError("ratified §24 failure census digest drift")
    if sum(row[2] for row in pins.failure_reason_rows) != (
        EXPECTED_T_MINUS_COUNT
    ):
        raise ReplayError("ratified §24 failure census does not cover T-minus")
    if canonical_sha256([]) != EMPTY_ARRAY_SHA256:
        raise ReplayError("canonical empty movement identity drift")

    if EXPECTED_EXPLICIT_MEMBER_COUNT + EXPECTED_ANALYTIC_MEMBER_COUNT != (
        EXPECTED_LOGICAL_MEMBER_COUNT
    ):
        raise ReplayError("§24 threshold member identity drift")
    compiled_field_vector = tuple(
        row[0] for row in EXPECTED_COMPILED_DECOMPOSITION
    )
    if compiled_field_vector != EXPECTED_TERMINAL_VECTOR[:4]:
        raise ReplayError("§24 compiled field decomposition drift")
    if sum(row[0] for row in EXPECTED_COMPILED_DECOMPOSITION) != (
        EXPECTED_COMPLETED_FIELD_COUNT
    ):
        raise ReplayError("§24 completed field decomposition drift")
    if sum(row[1] for row in EXPECTED_COMPILED_DECOMPOSITION) != (
        EXPECTED_NUMERIC_RANGE_ENTRY_COUNT
    ):
        raise ReplayError("§24 range-entry decomposition drift")
    if sum(row[2] for row in EXPECTED_COMPILED_DECOMPOSITION) != (
        EXPECTED_LOGICAL_MEMBER_COUNT
    ):
        raise ReplayError("§24 logical-member decomposition drift")
    if (
        EXPECTED_SEVEN_KEY_MEMBER_COUNT
        + EXPECTED_SIX_KEY_RATIONAL_MEMBER_COUNT
        + EXPECTED_SIX_KEY_INTEGER_MEMBER_COUNT
        + EXPECTED_FOUR_KEY_MEMBER_COUNT
        != EXPECTED_ANALYTIC_MEMBER_COUNT
    ):
        raise ReplayError("§24 four-shape population decomposition drift")
    if 3 * EXPECTED_LOGICAL_MEMBER_COUNT + 2 != (
        EXPECTED_EMPTY_OBJECT_FLOOR_BYTES
    ):
        raise ReplayError("§24 empty-object floor drift")
    if _production_floor() != EXPECTED_FOUR_SHAPE_FLOOR_BYTES:
        raise ReplayError("§24 four-shape floor drift")
    if EXPECTED_HISTORICAL_TWO_SHAPE_FLOOR_BYTES >= (
        EXPECTED_FOUR_SHAPE_FLOOR_BYTES
    ):
        raise ReplayError("§24 four-shape successor ordering drift")

    capacity_bytes = MEASURED_CAPACITY_REFERENCE_TIB * Decimal(2**40)
    if Decimal(EXPECTED_FOUR_SHAPE_FLOOR_BYTES) <= capacity_bytes:
        raise ReplayError("§24 nonconstructibility inequality no longer holds")
    with localcontext() as context:
        context.prec = 80
        ratio = Decimal(EXPECTED_FOUR_SHAPE_FLOOR_BYTES) / capacity_bytes

    return {
        "status": "ratified_revision_12_census_reproduced",
        "amendment_11_inference_authorized": False,
        "amendment_11_inference_blocker": (
            SourceMissingDispositionUnderdetermined.code
        ),
        "field_count": PRODUCTION_FIELD_COUNT,
        "ratified_predecessor_terminal_vector": list(EXPECTED_TERMINAL_VECTOR),
        "ratified_predecessor_count_array_sha256": (
            EXPECTED_COUNT_ARRAY_SHA256
        ),
        "ratified_predecessor_ordered_assignment_sha256": (
            EXPECTED_ORDERED_ASSIGNMENT_SHA256
        ),
        "ratified_predecessor_failure_reason_row_count": len(
            pins.failure_reason_rows
        ),
        "ratified_predecessor_failure_reason_rows_byte_count": (
            EXPECTED_FAILURE_REASON_ROWS_BYTE_COUNT
        ),
        "ratified_predecessor_failure_reason_rows_sha256": (
            EXPECTED_FAILURE_REASON_ROWS_SHA256
        ),
        "revision_12_completed_field_count": EXPECTED_COMPLETED_FIELD_COUNT,
        "revision_12_numeric_range_entry_count": (
            EXPECTED_NUMERIC_RANGE_ENTRY_COUNT
        ),
        "revision_12_logical_member_count": EXPECTED_LOGICAL_MEMBER_COUNT,
        "revision_12_explicit_member_count": EXPECTED_EXPLICIT_MEMBER_COUNT,
        "revision_12_analytic_member_count": EXPECTED_ANALYTIC_MEMBER_COUNT,
        "revision_12_compiled_decomposition": [
            list(row) for row in EXPECTED_COMPILED_DECOMPOSITION
        ],
        "revision_12_empty_object_floor_bytes": (
            EXPECTED_EMPTY_OBJECT_FLOOR_BYTES
        ),
        "ratified_historical_two_shape_floor_bytes": (
            EXPECTED_HISTORICAL_TWO_SHAPE_FLOOR_BYTES
        ),
        "four_shape_floor_bytes": EXPECTED_FOUR_SHAPE_FLOOR_BYTES,
        "measured_capacity_reference_tib": str(
            MEASURED_CAPACITY_REFERENCE_TIB
        ),
        "floor_to_capacity_ratio": format(ratio, "f"),
        "t_plus_field_count": EXPECTED_T_PLUS_COUNT,
        "t_minus_field_count": EXPECTED_T_MINUS_COUNT,
        "revision_13_full_relation_identity_defined": False,
        "revision_13_full_relation_identity_blocker": (
            SourceMissingDispositionUnderdetermined.code
        ),
    }


def _production_blocker_evidence(
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-bind one validated authority to the production blocker."""

    if SOURCE_LITERAL_ENTRY_COUNT + SOURCE_NUMERIC_RANGE_ENTRY_COUNT != (
        SOURCE_MEMBER_COUNT
    ):
        raise ReplayError("source entry-kind census drift")
    if (
        SOURCE_AUTHORIZED_MISSING_LITERAL_COUNT
        + UNADJUDICATED_LITERAL_ENTRY_COUNT
        != SOURCE_LITERAL_ENTRY_COUNT
    ):
        raise ReplayError("source authority partition drift")
    if not 0 < LEXICAL_MISSING_CANDIDATE_COUNT < SOURCE_LITERAL_ENTRY_COUNT:
        raise ReplayError("lexical candidate census drift")
    if (
        LEXICAL_MISSING_CANDIDATE_COUNT + LITERAL_LEXICAL_OTHER_COUNT
        != SOURCE_LITERAL_ENTRY_COUNT
    ):
        raise ReplayError("lexical literal partition drift")
    if (
        LITERAL_LEXICAL_OTHER_COUNT + SOURCE_NUMERIC_RANGE_ENTRY_COUNT
        != ALL_MEMBER_LEXICAL_OTHER_COUNT
    ):
        raise ReplayError("all-member lexical-other partition drift")
    if (
        LEXICAL_MISSING_CANDIDATE_COUNT + ALL_MEMBER_LEXICAL_OTHER_COUNT
        != SOURCE_MEMBER_COUNT
    ):
        raise ReplayError("complete lexical partition drift")
    if not (
        0
        < DIRECTLY_DISPROVEN_LEXICAL_CANDIDATE_MINIMUM
        <= LEXICAL_MISSING_CANDIDATE_COUNT
    ):
        raise ReplayError("disproven lexical candidate census drift")
    census = authority["source_member_census"]
    boundary = authority["authority_boundary"]
    artifact_values = (
        census["source_member_count"],
        census["literal_member_count"],
        census["numeric_range_member_count"],
        census["lexical_missing_candidate_count"],
        census["lexical_other_candidate_count"],
        census["literal_member_count"]
        - census["lexical_missing_candidate_count"],
        boundary["directly_disproven_candidate_count"],
        boundary["minimum_counterexample_count"],
        boundary["authorized_current_literal_disposition_count"],
        boundary["unadjudicated_literal_count"],
    )
    expected_values = (
        SOURCE_MEMBER_COUNT,
        SOURCE_LITERAL_ENTRY_COUNT,
        SOURCE_NUMERIC_RANGE_ENTRY_COUNT,
        LEXICAL_MISSING_CANDIDATE_COUNT,
        ALL_MEMBER_LEXICAL_OTHER_COUNT,
        LITERAL_LEXICAL_OTHER_COUNT,
        DIRECTLY_DISPROVEN_LEXICAL_CANDIDATE_MINIMUM,
        CONTEXT_REQUIRED_LEXICAL_CANDIDATE_MINIMUM,
        SOURCE_AUTHORIZED_MISSING_LITERAL_COUNT,
        UNADJUDICATED_LITERAL_ENTRY_COUNT,
    )
    if artifact_values != expected_values:
        raise ReplayError("authority/replay census cross-binding drift")
    historical = historical_predecessor_capacity_evidence()
    return {
        "blocker": SourceMissingDispositionUnderdetermined.code,
        "source_member_count": SOURCE_MEMBER_COUNT,
        "source_literal_entry_count": SOURCE_LITERAL_ENTRY_COUNT,
        "source_numeric_range_entry_count": (SOURCE_NUMERIC_RANGE_ENTRY_COUNT),
        "source_authorized_missing_literal_count": (
            SOURCE_AUTHORIZED_MISSING_LITERAL_COUNT
        ),
        "lexical_missing_candidate_count": LEXICAL_MISSING_CANDIDATE_COUNT,
        "literal_lexical_other_count": LITERAL_LEXICAL_OTHER_COUNT,
        "all_member_lexical_other_count": ALL_MEMBER_LEXICAL_OTHER_COUNT,
        "directly_disproven_lexical_candidate_minimum": (
            DIRECTLY_DISPROVEN_LEXICAL_CANDIDATE_MINIMUM
        ),
        "context_required_lexical_candidate_minimum": (
            CONTEXT_REQUIRED_LEXICAL_CANDIDATE_MINIMUM
        ),
        "literal_disposition_action": (
            "classify_source_authorized_then_block_underdetermined"
        ),
        "numeric_range_missing_reason_code_action": "json_null",
        "blocked_literal_entry_count": UNADJUDICATED_LITERAL_ENTRY_COUNT,
        "structural_null_entry_count": SOURCE_NUMERIC_RANGE_ENTRY_COUNT,
        "source_authorized_nonempty_reason_code_count": (
            SOURCE_AUTHORIZED_MISSING_LITERAL_COUNT
        ),
        "accepted_output_nonempty_reason_code_count": 0,
        "complete_settled_relation_exists": False,
        "production_replay_started": False,
        "production_replay_complete": False,
        "revision_13_full_relation_identity_available": False,
        "historical_predecessor_capacity_evidence": historical,
        "accepted_output_emitted": False,
    }


def production_blocker_evidence(
    authority_path: Path = AUTHORITY_ARTIFACT,
) -> dict[str, Any]:
    """Return the ordered production blockers without claiming replay."""

    return _production_blocker_evidence(
        validate_committed_authority(authority_path)
    )


def authenticated_source_derivations(
    psid_root: Path = REGISTERED_SOURCE_ROOT,
) -> Iterator[Mapping[str, Any]]:
    """Authenticate all sources, then lazily derive one document at a time."""

    _registered, projected = authority_builder.load_and_authenticate_sources(
        SOURCE_REGISTRY, psid_root
    )
    if authority_builder.extraction.pdftotext_version() != "26.04.0":
        raise authority_builder.BuildError(
            "Poppler version drift before semantic parsing"
        )
    if list(authority_builder.extraction.PDFTOTEXT_ARGUMENTS) != [
        "-layout",
        "-enc",
        "UTF-8",
    ]:
        raise authority_builder.BuildError(
            "Poppler argument drift before semantic parsing"
        )

    def derive() -> Iterator[Mapping[str, Any]]:
        for source_document in projected:
            yield authority_builder.extraction.extract_codebook_rows(
                source_document, psid_root
            )

    return derive()


def run_production_gate(
    authority_path: Path = AUTHORITY_ARTIFACT,
    psid_root: Path = REGISTERED_SOURCE_ROOT,
) -> None:
    """Invoke the sole production settlement entry point and require abort."""

    authority = validate_committed_authority(authority_path)
    evidence = _production_blocker_evidence(authority)
    try:
        derivations = authenticated_source_derivations(psid_root)
        settled = settle_missing_reason_codes(derivations, authority)
    except MissingReasonAuthorityError as error:
        if str(error) != EXPECTED_SOURCE_SETTLEMENT_BLOCKER:
            raise ReplayError(
                "production settlement failed before the expected terminal "
                "blocker"
            ) from error
        try:
            validate_authority_artifact(authority)
        except MissingReasonAuthorityError as drift:
            raise ReplayError(
                "authority implementation drifted during settlement"
            ) from drift
        raise SourceMissingDispositionUnderdetermined(evidence) from error
    except (
        authority_builder.BuildError,
        authority_builder.extraction.CodebookExtractionError,
        OSError,
    ) as error:
        raise ReplayError("production source authentication failed") from error

    raise ReplayError(
        "production settlement returned instead of failing closed: "
        f"{type(settled).__name__}"
    )


def run_historical_capacity_audit() -> dict[str, Any]:
    """Return revision 12 evidence without asserting an Amendment-11 result."""

    return historical_predecessor_capacity_evidence()


def _validate_fixture_storage(storage: FixtureStorage, label: str) -> None:
    for member in (
        "logical_member_count",
        "explicit_member_count",
        "analytic_member_count",
        "four_shape_floor_bytes",
    ):
        _require_plain_nonnegative_integer(getattr(storage, member), label)
    if storage.explicit_member_count + storage.analytic_member_count != (
        storage.logical_member_count
    ):
        raise ReplayError(f"{label} threshold decomposition")


def _counterfactual_entries(
    entries: Sequence[Mapping[str, Any]], field_position: int
) -> tuple[dict[str, Any], ...]:
    changed = []
    for entry_position, entry in enumerate(entries):
        copied = dict(entry)
        if entry["typed_disposition"] == "missing":
            copied["missing_reason_code"] = (
                f"counterfactual-opaque:{field_position}:{entry_position}"
            )
        changed.append(copied)
    return tuple(changed)


def replay_constructible_fixture(
    fields: Sequence[FixtureField],
    classifier: Callable[
        [Mapping[str, Any], Sequence[Mapping[str, Any]]], str
    ],
) -> dict[str, Any]:
    """Replay one complete, small settled relation and require no movement.

    This function is not a production fallback.  It exists so the logical
    gate has satisfiable positive fixtures despite the production storage
    blocker.
    """

    if not fields:
        raise ReplayError("fixture relation is empty")
    numeric_rows: list[Mapping[str, Any]] = []
    document_rows: list[dict[str, Any]] = []
    identifiers: list[str] = []
    assignments: list[str] = []
    failure_groups: dict[tuple[str, str], list[list[Any]]] = {}
    seen_keys: set[tuple[int, str]] = set()
    seen_identifiers: set[str] = set()
    seen_reason_codes: set[str] = set()
    missing_count = 0
    nonmissing_count = 0
    included_storage = Counter()
    excluded_storage = Counter()

    for field_position, field in enumerate(fields):
        row = field.numeric_grammar_derivation_row
        if tuple(row) != NUMERIC_ROW_KEYS:
            raise ReplayError(f"fixture field {field_position}: 16-key row")
        wave = row["interview_wave"]
        raw_field_id = row["raw_field_id"]
        if type(wave) is not int or type(raw_field_id) is not str:
            raise ReplayError(f"fixture field {field_position}: field key")
        key = (wave, raw_field_id)
        if key in seen_keys:
            raise ReplayError(f"fixture field {field_position}: duplicate key")
        seen_keys.add(key)
        identifier = row["numeric_grammar_derivation_id"]
        if not isinstance(identifier, str) or not identifier:
            raise ReplayError(
                f"fixture field {field_position}: derivation identity"
            )
        if identifier in seen_identifiers:
            raise ReplayError(
                f"fixture field {field_position}: duplicate derivation identity"
            )
        seen_identifiers.add(identifier)
        terminal = row["derivation_status"]
        if terminal not in TERMINALS:
            raise ReplayError(f"fixture field {field_position}: terminal")

        entries = field.settled_entries
        for entry_position, entry in enumerate(entries):
            if not isinstance(entry, Mapping):
                raise ReplayError(
                    f"fixture field {field_position}: member object"
                )
            disposition = entry.get("typed_disposition")
            reason = entry.get("missing_reason_code")
            if disposition == "missing":
                if not isinstance(reason, str) or not reason:
                    raise ReplayError(
                        f"fixture field {field_position}: unsettled missing "
                        f"member {entry_position}"
                    )
                if reason in seen_reason_codes:
                    raise ReplayError("fixture duplicate opaque reason code")
                seen_reason_codes.add(reason)
                missing_count += 1
            elif disposition in ("json_integer", "rational"):
                if reason is not None:
                    raise ReplayError(
                        f"fixture field {field_position}: nonmissing reason"
                    )
                nonmissing_count += 1
            else:
                raise ReplayError(
                    f"fixture field {field_position}: member disposition"
                )

        observed = classifier(row, entries)
        counterfactual = classifier(
            row,
            _counterfactual_entries(entries, field_position),
        )
        if observed not in TERMINALS or counterfactual not in TERMINALS:
            raise ReplayError(f"fixture field {field_position}: open terminal")
        if counterfactual != observed:
            raise ReplayError(
                f"fixture field {field_position}: reason-string-sensitive "
                "terminal"
            )
        if observed != terminal:
            raise ReplayError(
                f"fixture field {field_position}: nonempty delta movement"
            )
        assignments.append(observed)

        if terminal in T_MINUS:
            if not isinstance(field.resolution_reason, str) or not (
                field.resolution_reason
            ):
                raise ReplayError(
                    f"fixture field {field_position}: missing failure reason"
                )
            failure_groups.setdefault(
                (terminal, field.resolution_reason), []
            ).append([wave, raw_field_id])
        elif field.resolution_reason is not None:
            raise ReplayError(
                f"fixture field {field_position}: T-plus failure reason"
            )

        _validate_fixture_storage(
            field.storage, f"fixture field {field_position} storage"
        )
        target = included_storage if terminal in T_PLUS else excluded_storage
        for member in (
            "logical_member_count",
            "explicit_member_count",
            "analytic_member_count",
            "four_shape_floor_bytes",
        ):
            target[member] += getattr(field.storage, member)

        numeric_rows.append(row)
        identifiers.append(identifier)
        document_rows.append(
            {
                "interview_wave": wave,
                "raw_field_id": raw_field_id,
                "settled_entries": [dict(entry) for entry in entries],
            }
        )

    if missing_count == 0:
        raise ReplayError("fixture has no satisfiable missing-positive arm")

    keyset_sha256 = canonical_sha256(identifiers)
    domain_sha256 = canonical_sha256(numeric_rows)
    document_domain_sha256 = canonical_sha256(document_rows)
    field_source_derivation = {
        "implementation_identity": {
            "interface_version": "constructible_amendment_11_fixture.v1"
        },
        "document_derivations": document_rows,
        "document_derivation_count": len(document_rows),
        "document_derivation_domain_sha256": document_domain_sha256,
        "numeric_grammar_derivation_rows": list(numeric_rows),
        "numeric_grammar_derivation_row_count": len(numeric_rows),
        "numeric_grammar_derivation_keyset_sha256": keyset_sha256,
        "numeric_grammar_derivation_domain_sha256": domain_sha256,
        "status": "pass",
    }
    if tuple(field_source_derivation) != FIELD_SOURCE_KEYS:
        raise ReplayError("fixture field-source key order")
    field_source_bytes = canonical_json_bytes(field_source_derivation)
    identity = [
        FIXTURE_IDENTITY_LITERAL,
        len(numeric_rows),
        keyset_sha256,
        domain_sha256,
        len(field_source_bytes),
        hashlib.sha256(field_source_bytes).hexdigest(),
    ]
    terminal_counts = Counter(assignments)
    terminal_vector = [terminal_counts[name] for name in TERMINALS]
    t_plus_count = sum(terminal_counts[name] for name in T_PLUS)
    t_minus_count = sum(terminal_counts[name] for name in T_MINUS)
    failure_rows = [
        {
            "derivation_status": terminal,
            "resolution_reason": reason,
            "field_keys": keys,
        }
        for (terminal, reason), keys in failure_groups.items()
    ]
    if sum(len(row["field_keys"]) for row in failure_rows) != t_minus_count:
        raise ReplayError("fixture failure census does not cover T-minus")

    return {
        "status": "pass",
        "fixture_only": True,
        "conditional_on_supplied_synthetic_missing_dispositions": True,
        "production_source_authority_claimed": False,
        "field_count": len(numeric_rows),
        "terminal_vector": terminal_vector,
        "failure_reason_rows": failure_rows,
        "missing_member_count": missing_count,
        "nonmissing_member_count": nonmissing_count,
        "included_storage": dict(included_storage),
        "excluded_storage": dict(excluded_storage),
        "t_plus_field_count": t_plus_count,
        "t_minus_field_count": t_minus_count,
        "delta_movement_rows": [],
        "delta_movement_sha256": canonical_sha256([]),
        "fixture_full_relation_identity": identity,
    }


def main() -> int:
    """Run the production preflight; stdout is always empty."""

    try:
        run_production_gate()
    except SourceMissingDispositionUnderdetermined as error:
        print(str(error), file=sys.stderr)
        return 2
    except ReplayError as error:
        print(str(error), file=sys.stderr)
        return 1
    raise AssertionError("production gate must never report pass")


if __name__ == "__main__":
    raise SystemExit(main())
