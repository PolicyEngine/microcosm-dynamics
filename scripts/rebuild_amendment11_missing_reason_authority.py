"""Rebuild Amendment 11's complete missing-reason authority artifact.

The builder authenticates the pinned registration artifact and all 47 raw
codebook/value-label inputs before parsing any semantic member.  It then
derives the complete 561,873-member relation and two audit-only vectors:
entry kind and the predecessor lexical candidate.  Neither vector supplies a
literal missing disposition.  The builder emits only after the complete
fail-closed artifact passes validation.  ``--check`` performs a fresh build
and byte-compares it with the committed artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat as stat_module
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import populace_dynamics.data.psid_codebook_extraction as extraction  # noqa: E402
from populace_dynamics.data.psid_missing_reason_authority import (  # noqa: E402
    ARTIFACT_ID,
    AUTHORITY_FAILURE_DISPOSITION_ROWS,
    CONFLICTING_AUTHORITY_FAILURE_STATES,
    CONFLICTING_MISSING_REASON_AUTHORITY,
    ENTRY_KIND_VECTOR_ENCODING,
    EXPECTED_CANONICAL_ROW_COUNT,
    EXPECTED_COUNTEREXAMPLE_COUNT,
    EXPECTED_COUNTEREXAMPLE_SHA256,
    EXPECTED_DIRECTLY_DISPROVEN_COUNT,
    EXPECTED_DIRECTLY_DISPROVEN_SHA256,
    EXPECTED_DISTINCT_CANDIDATE_MEANING_COUNT,
    EXPECTED_DOCUMENT_COUNT,
    EXPECTED_LABEL_LEXICAL_MISSING_COUNT,
    EXPECTED_LEXICAL_MISSING_COUNT,
    EXPECTED_LITERAL_COUNT,
    EXPECTED_MEMBER_COUNT,
    EXPECTED_MISSING_CANDIDATE_PROJECTION_SHA256,
    EXPECTED_NUMERIC_RANGE_COUNT,
    EXPECTED_OVERLAPPING_PHRASE_COUNTS,
    EXPECTED_OVERLAPPING_PHRASE_COUNTS_SHA256,
    EXPECTED_PDF_LEXICAL_MISSING_COUNT,
    EXPECTED_PDF_MEMBER_COUNT,
    EXPECTED_PDF_ROW_COUNT,
    EXPECTED_PROJECTED_SOURCE_ROWS_SHA256,
    EXPECTED_REGISTERED_SOURCE_BYTE_SIZE,
    EXPECTED_REGISTERED_SOURCE_COUNT,
    EXPECTED_REGISTERED_SOURCE_ROWS_SHA256,
    EXPECTED_REGISTRY_BYTE_SIZE,
    EXPECTED_REGISTRY_PATH,
    EXPECTED_REGISTRY_SHA256,
    EXPECTED_SELECTED_EXACT_MEANING_COUNTS,
    EXPECTED_SELECTED_EXACT_MEANING_COUNTS_SHA256,
    EXPECTED_SOURCE_AUTHORITY_PACKED_SHA256,
    EXPECTED_SOURCE_AUTHORIZED_AUDIT_BYTE_SIZE,
    EXPECTED_SOURCE_AUTHORIZED_AUDIT_SHA256,
    EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT,
    EXPECTED_SOURCE_AUTHORIZED_OCCURRENCE_SHA256,
    EXPECTED_SOURCE_LOCATOR_COUNT,
    EXPECTED_UNADJUDICATED_LITERAL_COUNT,
    INCOMPLETE_AUTHORITY_FAILURE_STATES,
    INCOMPLETE_MISSING_REASON_AUTHORITY,
    LEXICAL_VECTOR_ENCODING,
    MEMBER_IDENTITY_VERSION,
    REASON_CODE_PREFIX,
    REASON_PREIMAGE_VERSION,
    SCHEMA_VERSION,
    SOURCE_AUTHORITY_VECTOR_ENCODING,
    MissingReasonAuthorityError,
    candidate_is_missing,
    canonical_json_bytes,
    canonical_sha256,
    document_derivation_metadata_sha256,
    iter_source_members,
    pack_disposition_bits,
    sha256_bytes,
    source_authorized_audit_row,
    source_authorized_occurrence_row,
    source_authorizes_current_missing_reason,
    source_member_identity,
    utf8_compact_json_bytes,
    validate_authority_artifact,
    verify_originating_records,
)

DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "data/external/psid_missing_reason_code_authority_v1.json"
)
DEFAULT_PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()
SOURCE_ROLES = frozenset(
    ("family_codebook", "stata_value_labels", "spss_value_labels")
)
ZERO_SHA256 = "0" * 64
EXPECTED_DOCUMENT_MEMBER_COUNTS = (
    2_674,
    3_325,
    3_275,
    3_176,
    3_346,
    1_934,
    1_984,
    2_614,
    5_052,
    2_676,
    2_845,
    2_988,
    3_221,
    3_185,
    2_863,
    3_358,
    6_146,
    8_327,
    7_257,
    6_293,
    8_027,
    7_470,
    6_963,
    6_942,
    6_934,
    8_571,
    13_250,
    12_000,
    14_686,
    12_707,
    19_770,
    18_601,
    16_230,
    15_947,
    25_875,
    25_727,
    26_328,
    26_690,
    29_213,
    30_414,
    29_406,
    21_246,
    17_640,
    25_263,
    19_809,
    16_251,
    23_374,
)


class BuildError(ValueError):
    """The fresh Amendment-11 build cannot be accepted."""


class _CanonicalArrayHasher:
    """Incrementally hash one §10.1 canonical JSON array."""

    def __init__(self) -> None:
        self._digest = hashlib.sha256(b"[")
        self.count = 0

    def update(self, value: Any) -> None:
        if self.count:
            self._digest.update(b",")
        self._digest.update(canonical_json_bytes(value)[:-1])
        self.count += 1

    def hexdigest(self) -> str:
        digest = self._digest.copy()
        digest.update(b"]\n")
        return digest.hexdigest()


_MISSING_PROJECTION_KEYS = (
    "codebook_field_row_id",
    "entry_ref",
    "source_document_id",
    "source_locator_ids",
    "source_meaning",
    "source_value_lexeme",
)


def _missing_projection(derivation: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for member in iter_source_members((derivation,)):
        if not candidate_is_missing(member):
            continue
        rows.append(
            {
                "source_document_id": member.source_document_id,
                "codebook_field_row_id": member.codebook_field_row_id,
                "entry_ref": member.entry["entry_ref"],
                "source_value_lexeme": member.entry["source_value_lexeme"],
                "source_meaning": member.entry["source_meaning"],
                "source_locator_ids": list(member.source_locator_ids),
            }
        )
    return rows


def _phrase_matches(meaning: str) -> tuple[str, ...]:
    folded = meaning.casefold()
    matches = []
    for label, pattern in (
        ("DK", r"\bdk\b"),
        ("NA", r"\bna\b"),
        ("RF", r"\brf\b"),
        ("Inap", r"\binap\b"),
        ("missing", r"\bmissing\b"),
        ("don't know", r"don(?:'|’)?t know"),
    ):
        if re.search(pattern, folded):
            matches.append(label)
    for label, substring in (
        ("refus", "refus"),
        ("wild code", "wild code"),
        ("data suppressed", "data suppressed"),
        ("not ascertained", "not ascertained"),
    ):
        if substring in folded:
            matches.append(label)
    return tuple(matches)


def _reject_constant(value: str) -> None:
    raise BuildError(f"nonfinite JSON constant: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_bytes(raw: bytes, label: str) -> Any:
    """Parse exactly one strict UTF-8 JSON value with duplicate rejection."""

    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BuildError(f"invalid strict JSON: {label}") from error


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _project_source_manifest_row(row: Mapping[str, Any]) -> dict[str, Any]:
    if row["dictionary_role"] not in SOURCE_ROLES:
        raise BuildError("non-codebook row projected")
    role = "codebook"
    waves = [row["interview_wave"]]
    preimage = [role, waves, row["path"], row["size_bytes"], row["sha256"]]
    return {
        "source_document_id": "psid-source-document:"
        + canonical_sha256(preimage),
        "upstream_document_id": row["document_id"],
        "document_role": role,
        "interview_waves": waves,
        "canonical_source_path": row["path"],
        "encoding": row["encoding"],
        "byte_size": row["size_bytes"],
        "sha256": row["sha256"],
    }


def load_and_authenticate_sources(
    registry_path: Path, psid_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return exact registered and projected rows after all byte checks."""

    if registry_path != REPOSITORY_ROOT / EXPECTED_REGISTRY_PATH:
        raise BuildError("registry path is not the pinned repository path")
    raw = registry_path.read_bytes()
    if len(raw) != EXPECTED_REGISTRY_BYTE_SIZE:
        raise BuildError("registry byte-size mismatch")
    if sha256_bytes(raw) != EXPECTED_REGISTRY_SHA256:
        raise BuildError("registry SHA-256 mismatch")
    registry = strict_json_bytes(raw, str(registry_path))
    if not isinstance(registry, Mapping):
        raise BuildError("registry is not an object")
    manifest = registry.get("source_authority_manifest")
    if not isinstance(manifest, list):
        raise BuildError("registry source manifest is not an array")
    registered = [
        dict(row)
        for row in manifest
        if isinstance(row, Mapping)
        and row.get("dictionary_role") in SOURCE_ROLES
    ]
    if len(registered) != EXPECTED_REGISTERED_SOURCE_COUNT:
        raise BuildError("registered codebook source count")
    if sum(row["size_bytes"] for row in registered) != (
        EXPECTED_REGISTERED_SOURCE_BYTE_SIZE
    ):
        raise BuildError("registered source byte census")
    registered_sha = sha256_bytes(
        json.dumps(
            registered,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    )
    if registered_sha != EXPECTED_REGISTERED_SOURCE_ROWS_SHA256:
        raise BuildError("registered source row-domain mismatch")

    root = psid_root.resolve(strict=True)
    for row in registered:
        candidate = psid_root / row["path"]
        if candidate.is_symlink() or not candidate.is_file():
            raise BuildError(
                f"source is not a regular nonsymlink file: {candidate}"
            )
        path = candidate.resolve(strict=True)
        if os.path.commonpath((str(root), str(path))) != str(root):
            raise BuildError(f"source escapes PSID root: {candidate}")
        stat = path.stat()
        if stat.st_size != row["size_bytes"]:
            raise BuildError(f"source byte-size mismatch: {candidate}")
        if _sha256_file(path) != row["sha256"]:
            raise BuildError(f"source SHA-256 mismatch: {candidate}")

    projected = [_project_source_manifest_row(row) for row in registered]
    if canonical_sha256(projected) != EXPECTED_PROJECTED_SOURCE_ROWS_SHA256:
        raise BuildError("projected source row-domain mismatch")
    return registered, projected


def _implementation_identity() -> dict[str, Any]:
    originating_records = verify_originating_records(REPOSITORY_ROOT)
    paths = (
        "src/populace_dynamics/data/psid_codebook_extraction.py",
        "src/populace_dynamics/data/psid_missing_reason_authority.py",
        "scripts/rebuild_amendment11_missing_reason_authority.py",
    )
    rows = []
    for position, relative in enumerate(paths):
        raw = (REPOSITORY_ROOT / relative).read_bytes()
        rows.append(
            {
                "position": position,
                "path": relative,
                "byte_size": len(raw),
                "sha256": sha256_bytes(raw),
            }
        )
    return {
        "interface_version": "amendment_11_missing_reason_fail_closed.v1",
        "originating_record_count": len(originating_records),
        "originating_record_domain_sha256": canonical_sha256(
            list(originating_records)
        ),
        "pdftotext_arguments": list(extraction.PDFTOTEXT_ARGUMENTS),
        "pdftotext_version": extraction.pdftotext_version(),
        "implementation_files": rows,
        "implementation_file_domain_sha256": canonical_sha256(rows),
    }


def _rejection_class_witnesses() -> list[dict[str, Any]]:
    """Return one exact raw witness or mechanical fixture per defeat class."""

    return [
        {
            "class": "lexical_substring_negation",
            "fixture": "V1107 code 0: Never refused",
            "required_action": "defeat_candidate_authority_and_abort",
        },
        {
            "class": "lexical_substring_substantive_event",
            "fixture": "V1107 code 1: Refused at least once",
            "required_action": "defeat_candidate_authority_and_abort",
        },
        {
            "class": "lexical_substring_substantive_anatomy",
            "fixture": "V2833 code 3 includes missing finger",
            "required_action": "defeat_candidate_authority_and_abort",
        },
        {
            "class": "lexical_substring_accuracy_status",
            "fixture": "1988 ACC/ACCURACY category contains missing data",
            "required_action": "defeat_candidate_authority_and_abort",
        },
        {
            "class": "lexical_substring_information_access_reason",
            "fixture": "V7774 code 3: DK how to apply",
            "required_action": "defeat_candidate_authority_and_abort",
        },
        {
            "class": "composite_meaning_atom_choice",
            "fixture": "DK; NA; refused",
            "required_action": "no_atom_or_reason_assignment",
        },
        {
            "class": "numeric_range_wild_code_defeat",
            "fixture": "ER2087 range 999.60 - 999.97 Wild codes",
            "required_action": "range_reason_is_null",
        },
        {
            "class": "same_spelling_cross_occurrence_equivalence",
            "fixture": "two source occurrences both spell DK",
            "required_action": "no_semantic_equivalence_claim",
        },
        {
            "class": "sibling_wave_or_locale_default",
            "fixture": "literal beside a seemingly missing sibling",
            "required_action": "abort_without_emission",
        },
        {
            "class": "empty_source_preimage",
            "fixture": "literal with empty source meaning or locator",
            "required_action": "abort_without_emission",
        },
        {
            "class": "unregistered_or_reordered_member",
            "fixture": "identity digest or member position drift",
            "required_action": "abort_without_emission",
        },
        {
            "class": "evidence_artifact_laundering",
            "fixture": "historical candidate flag offered as disposition",
            "required_action": "abort_without_emission",
        },
        {
            "class": "future_disposition_conflict",
            "fixture": "two authorities disagree on one literal",
            "required_action": "abort_without_emission",
        },
        {
            "class": "reason_code_collision_or_duplicate_assignment",
            "fixture": "equal code from unequal occurrence preimages",
            "required_action": "abort_without_emission",
        },
        {
            "class": "semantic_taxonomy_request",
            "fixture": "consumer asks whether an opaque code means refused",
            "required_action": "semantic_reason_taxonomy_undetermined",
        },
    ]


def _summarize_document(
    source: Mapping[str, Any],
    document: Mapping[str, Any],
    derivation: Mapping[str, Any],
    position: int,
    member_offset: int,
) -> dict[str, Any]:
    """Reduce one raw derivation to source facts and nonauthority candidates."""

    extraction.validate_document_derivation(derivation)
    complete_hasher = _CanonicalArrayHasher()
    identity_hasher = _CanonicalArrayHasher()
    candidate_identity_hasher = _CanonicalArrayHasher()
    locator_hasher = _CanonicalArrayHasher()
    for locator in derivation["row_segmentation"]["source_region_locators"]:
        locator_hasher.update([document["source_document_id"], locator])

    entry_kind_bits = bytearray()
    lexical_bits = bytearray()
    source_authority_bits = bytearray()
    authorized_audit_rows: list[dict[str, Any]] = []
    authorized_occurrence_rows: list[list[Any]] = []
    candidate_meanings: set[str] = set()
    candidate_fields: set[str] = set()
    candidate_counts: Counter[str] = Counter()
    range_rows: list[dict[str, Any]] = []
    counterexamples: list[dict[str, Any]] = []
    directly_disproven: list[dict[str, Any]] = []
    rows_by_id = {
        row["codebook_field_row_id"]: row
        for row in derivation["canonical_rows"]
    }
    for local_member in iter_source_members((derivation,)):
        member = type(local_member)(
            member_position=member_offset + local_member.member_position,
            source_document_position=position,
            source_row_position=local_member.source_row_position,
            entry_position=local_member.entry_position,
            source_document_id=local_member.source_document_id,
            codebook_field_row_id=local_member.codebook_field_row_id,
            source_locator_ids=local_member.source_locator_ids,
            entry=local_member.entry,
        )
        identity = source_member_identity(member)
        identity_hasher.update(identity)
        complete_hasher.update(
            [
                member.source_document_id,
                member.codebook_field_row_id,
                member.entry_position,
                member.entry,
            ]
        )
        is_literal = member.entry["entry_kind"] == "literal"
        is_candidate = candidate_is_missing(member)
        is_source_authorized = source_authorizes_current_missing_reason(member)
        entry_kind_bits.append(int(is_literal))
        lexical_bits.append(int(is_candidate))
        source_authority_bits.append(int(is_source_authorized))
        candidate_counts[member.entry["typed_disposition"]] += 1
        row = rows_by_id[member.codebook_field_row_id]
        meaning = member.entry["source_meaning"]
        folded = meaning.casefold()
        if is_source_authorized:
            authorized_occurrence_rows.append(
                source_authorized_occurrence_row(
                    member,
                    source["interview_wave"],
                    source["path"],
                    row["raw_field_id"],
                )
            )
            authorized_audit_rows.append(
                source_authorized_audit_row(
                    member,
                    source["interview_wave"],
                    source["path"],
                    row["raw_field_id"],
                    row["source_label"],
                    row["source_description"],
                )
            )
        accuracy_status = (
            document["canonical_source_path"]
            == "family/1988/FAM1988_codebook.pdf"
            and "missing data" in folded
            and (row["source_label"] or "").upper().startswith("ACC")
        )
        direct_disproof = (
            folded == "never refused"
            or folded == "refused at least once"
            or "missing finger" in folded
            or "dk how to go about applying for them" in folded
            or ("dk how to apply; didn't know anything about it" in folded)
        )
        if is_candidate:
            candidate_meanings.add(meaning)
            candidate_fields.add(member.codebook_field_row_id)
            candidate_identity_hasher.update(identity)
            if (
                direct_disproof
                or folded.startswith("never refused;")
                or accuracy_status
            ):
                witness = {
                    "source_document_id": member.source_document_id,
                    "canonical_source_path": document["canonical_source_path"],
                    "codebook_field_row_id": member.codebook_field_row_id,
                    "raw_field_id": row["raw_field_id"],
                    "entry_ref": member.entry["entry_ref"],
                    "source_value_lexeme": member.entry["source_value_lexeme"],
                    "source_meaning": meaning,
                    "source_locator_ids": list(member.source_locator_ids),
                    "lexical_candidate_disposition": "missing",
                    "required_action": (
                        "defeat_source_authority_claim_and_abort_"
                        "literal_settlement"
                    ),
                }
                counterexamples.append(witness)
                if direct_disproof:
                    directly_disproven.append(witness)
        if (
            member.entry["entry_kind"] == "numeric_range"
            and "wild code" in folded
        ):
            range_rows.append(
                {
                    "source_document_id": member.source_document_id,
                    "codebook_field_row_id": member.codebook_field_row_id,
                    "entry_ref": member.entry["entry_ref"],
                    "source_value_lexeme": member.entry["source_value_lexeme"],
                    "source_meaning": meaning,
                    "source_locator_ids": list(member.source_locator_ids),
                    "required_missing_reason_code": None,
                    "rejection_reason": (
                        "numeric_range_cannot_be_missing_literal"
                    ),
                }
            )

    member_count = len(lexical_bits)
    candidate_count = sum(lexical_bits)
    source_document_row = {
        "position": position,
        "upstream_document_id": source["document_id"],
        "source_document_id": document["source_document_id"],
        "interview_wave": source["interview_wave"],
        "canonical_source_path": source["path"],
        "source_byte_size": source["size_bytes"],
        "source_sha256": source["sha256"],
        "canonical_row_count": derivation["canonical_row_count"],
        "derivation_metadata_sha256": (
            document_derivation_metadata_sha256(derivation)
        ),
        "normalized_entry_count": member_count,
        "lexical_missing_candidate_count": candidate_count,
        "member_start": member_offset,
        "member_end": member_offset + member_count,
        "canonical_row_domain_sha256": derivation[
            "canonical_row_domain_sha256"
        ],
        "source_member_complete_domain_sha256": complete_hasher.hexdigest(),
        "source_member_identity_sha256": identity_hasher.hexdigest(),
        "source_authorized_missing_count": len(authorized_occurrence_rows),
        "source_authorized_missing_occurrence_sha256": canonical_sha256(
            authorized_occurrence_rows
        ),
        "lexical_missing_candidate_identity_sha256": (
            candidate_identity_hasher.hexdigest()
        ),
        "source_locator_count": locator_hasher.count,
        "source_locator_domain_sha256": locator_hasher.hexdigest(),
    }
    return {
        "position": position,
        "source_document_row": source_document_row,
        "entry_kind_bits": entry_kind_bits.hex(),
        "lexical_candidate_bits": lexical_bits.hex(),
        "source_authority_bits": source_authority_bits.hex(),
        "source_authorized_audit_rows": authorized_audit_rows,
        "source_authorized_occurrence_rows": authorized_occurrence_rows,
        "distinct_candidate_meanings": sorted(candidate_meanings),
        "candidate_field_count": len(candidate_fields),
        "candidate_counts": dict(candidate_counts),
        "directly_disproven_candidates": directly_disproven,
        "minimum_counterexamples": counterexamples,
        "numeric_range_rejection_rows": range_rows,
    }


def _document_digest_manifest(
    rows: Sequence[Mapping[str, Any]], count_key: str, digest_key: str
) -> str:
    return canonical_sha256(
        [
            [row["source_document_id"], row[count_key], row[digest_key]]
            for row in rows
        ]
    )


def _build_artifact_from_summaries(
    summaries: Sequence[Mapping[str, Any]],
    *,
    candidate_projection_sha256: str,
    exact_meaning_counts: Mapping[str, int],
    implementation_identity: Mapping[str, Any],
    phrase_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Merge isolated summaries into the fail-closed boundary artifact."""

    if len(summaries) != EXPECTED_DOCUMENT_COUNT:
        raise BuildError("isolated document-summary count")
    if candidate_projection_sha256 != (
        EXPECTED_MISSING_CANDIDATE_PROJECTION_SHA256
    ):
        raise BuildError("complete lexical-candidate projection")
    if dict(exact_meaning_counts) != EXPECTED_SELECTED_EXACT_MEANING_COUNTS:
        raise BuildError("selected exact candidate-meaning census")
    if dict(phrase_counts) != EXPECTED_OVERLAPPING_PHRASE_COUNTS:
        raise BuildError("overlapping candidate-meaning phrase census")

    source_document_rows: list[dict[str, Any]] = []
    all_entry_kind_bits = bytearray()
    all_lexical_bits = bytearray()
    all_source_authority_bits = bytearray()
    authorized_audit_rows: list[dict[str, Any]] = []
    authorized_occurrence_rows: list[list[Any]] = []
    candidate_meanings: set[str] = set()
    candidate_counts: Counter[str] = Counter()
    range_rows: list[dict[str, Any]] = []
    counterexample_rows: list[dict[str, Any]] = []
    directly_disproven_rows: list[dict[str, Any]] = []
    pdf_candidate_field_count = 0
    for position, summary in enumerate(summaries):
        if summary.get("position") != position:
            raise BuildError("isolated summary order")
        row = summary.get("source_document_row")
        if not isinstance(row, Mapping) or row.get("position") != position:
            raise BuildError("isolated source-document row")
        if row.get("member_start") != len(all_lexical_bits):
            raise BuildError("isolated member-start continuity")
        kind_hex = summary.get("entry_kind_bits")
        candidate_hex = summary.get("lexical_candidate_bits")
        source_authority_hex = summary.get("source_authority_bits")
        if (
            not isinstance(kind_hex, str)
            or not isinstance(candidate_hex, str)
            or not isinstance(source_authority_hex, str)
        ):
            raise BuildError("isolated bit strings")
        try:
            kind_bits = bytes.fromhex(kind_hex)
            lexical_bits = bytes.fromhex(candidate_hex)
            source_authority_bits = bytes.fromhex(source_authority_hex)
        except ValueError as error:
            raise BuildError("isolated bit encoding") from error
        if (
            len(kind_bits) != len(lexical_bits)
            or len(kind_bits) != len(source_authority_bits)
            or any(value not in (0, 1) for value in kind_bits)
            or any(value not in (0, 1) for value in lexical_bits)
            or any(value not in (0, 1) for value in source_authority_bits)
        ):
            raise BuildError("isolated bit domain")
        if row.get("normalized_entry_count") != len(lexical_bits):
            raise BuildError("isolated member count")
        if row.get("lexical_missing_candidate_count") != sum(lexical_bits):
            raise BuildError("isolated candidate count")
        if row.get("source_authorized_missing_count") != sum(
            source_authority_bits
        ):
            raise BuildError("isolated source-authority count")
        if row.get("member_end") != len(all_lexical_bits) + len(lexical_bits):
            raise BuildError("isolated member-end continuity")
        all_entry_kind_bits.extend(kind_bits)
        all_lexical_bits.extend(lexical_bits)
        all_source_authority_bits.extend(source_authority_bits)
        source_document_rows.append(dict(row))

        document_occurrences = summary.get("source_authorized_occurrence_rows")
        document_audit = summary.get("source_authorized_audit_rows")
        if (
            not isinstance(document_occurrences, list)
            or not isinstance(document_audit, list)
            or len(document_occurrences) != sum(source_authority_bits)
            or len(document_audit) != len(document_occurrences)
            or canonical_sha256(document_occurrences)
            != row.get("source_authorized_missing_occurrence_sha256")
        ):
            raise BuildError("isolated source-authorized occurrence rows")
        authorized_occurrence_rows.extend(document_occurrences)
        authorized_audit_rows.extend(document_audit)

        meanings = summary.get("distinct_candidate_meanings")
        if not isinstance(meanings, list) or meanings != sorted(set(meanings)):
            raise BuildError("isolated candidate-meaning domain")
        candidate_meanings.update(meanings)
        counts = summary.get("candidate_counts")
        if not isinstance(counts, Mapping):
            raise BuildError("isolated candidate counts")
        candidate_counts.update(counts)
        rejected = summary.get("numeric_range_rejection_rows")
        counterexamples = summary.get("minimum_counterexamples")
        directly_disproven = summary.get("directly_disproven_candidates")
        if (
            not isinstance(rejected, list)
            or not isinstance(counterexamples, list)
            or not isinstance(directly_disproven, list)
        ):
            raise BuildError("isolated rejection rows")
        range_rows.extend(rejected)
        counterexample_rows.extend(counterexamples)
        directly_disproven_rows.extend(directly_disproven)
        if row["canonical_source_path"].endswith(".pdf"):
            field_count = summary.get("candidate_field_count")
            if type(field_count) is not int:
                raise BuildError("isolated candidate-field count")
            pdf_candidate_field_count += field_count

    if len(all_lexical_bits) != EXPECTED_MEMBER_COUNT:
        raise BuildError("complete member count")
    if sum(all_entry_kind_bits) != EXPECTED_LITERAL_COUNT:
        raise BuildError("complete literal count")
    if len(all_entry_kind_bits) - sum(all_entry_kind_bits) != (
        EXPECTED_NUMERIC_RANGE_COUNT
    ):
        raise BuildError("complete numeric-range count")
    if sum(all_lexical_bits) != EXPECTED_LEXICAL_MISSING_COUNT:
        raise BuildError("complete lexical-candidate count")
    if (
        sum(all_source_authority_bits)
        != EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
        or len(authorized_occurrence_rows)
        != EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
        or len(authorized_audit_rows)
        != EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
    ):
        raise BuildError("complete source-authorized occurrence count")
    if canonical_sha256(authorized_occurrence_rows) != (
        EXPECTED_SOURCE_AUTHORIZED_OCCURRENCE_SHA256
    ):
        raise BuildError("complete source-authorized occurrence digest")
    audit_raw = utf8_compact_json_bytes(authorized_audit_rows)
    if (
        len(audit_raw) != EXPECTED_SOURCE_AUTHORIZED_AUDIT_BYTE_SIZE
        or sha256_bytes(audit_raw) != EXPECTED_SOURCE_AUTHORIZED_AUDIT_SHA256
    ):
        raise BuildError("complete source-authorized audit digest")
    if len(candidate_meanings) != EXPECTED_DISTINCT_CANDIDATE_MEANING_COUNT:
        raise BuildError("distinct candidate-meaning count")
    if candidate_counts != {
        "missing": EXPECTED_LEXICAL_MISSING_COUNT,
        "json_integer": 326_868,
        "rational": 3_742,
    }:
        raise BuildError("candidate-disposition partition")
    if len(range_rows) != 21:
        raise BuildError("numeric-range Wild-code rejection census")
    if (
        len(counterexample_rows) != EXPECTED_COUNTEREXAMPLE_COUNT
        or canonical_sha256(counterexample_rows)
        != EXPECTED_COUNTEREXAMPLE_SHA256
    ):
        raise BuildError("minimum contextual counterexample census")
    if (
        len(directly_disproven_rows) != EXPECTED_DIRECTLY_DISPROVEN_COUNT
        or canonical_sha256(directly_disproven_rows)
        != EXPECTED_DIRECTLY_DISPROVEN_SHA256
    ):
        raise BuildError("directly disproven candidate census")

    pdf_document_rows = [
        row
        for row in source_document_rows
        if row["canonical_source_path"].endswith(".pdf")
    ]
    label_document_rows = [
        row
        for row in source_document_rows
        if not row["canonical_source_path"].endswith(".pdf")
    ]
    if len(pdf_document_rows) != 43 or len(label_document_rows) != 4:
        raise BuildError("PDF/value-label document partition")
    pdf_rows = sum(row["canonical_row_count"] for row in pdf_document_rows)
    pdf_members = sum(
        row["normalized_entry_count"] for row in pdf_document_rows
    )
    pdf_candidates = sum(
        row["lexical_missing_candidate_count"] for row in pdf_document_rows
    )
    label_candidates = sum(
        row["lexical_missing_candidate_count"] for row in label_document_rows
    )
    if (pdf_rows, pdf_members, pdf_candidates, label_candidates) != (
        EXPECTED_PDF_ROW_COUNT,
        EXPECTED_PDF_MEMBER_COUNT,
        EXPECTED_PDF_LEXICAL_MISSING_COUNT,
        EXPECTED_LABEL_LEXICAL_MISSING_COUNT,
    ):
        raise BuildError("PDF/value-label projection census")
    if pdf_candidate_field_count != 83_863:
        raise BuildError("PDF fields with lexical candidates")

    kind_hex, kind_count = pack_disposition_bits(
        bool(value) for value in all_entry_kind_bits
    )
    lexical_hex, lexical_count = pack_disposition_bits(
        bool(value) for value in all_lexical_bits
    )
    source_authority_hex, source_authority_count = pack_disposition_bits(
        bool(value) for value in all_source_authority_bits
    )
    kind_packed = bytes.fromhex(kind_hex)
    lexical_packed = bytes.fromhex(lexical_hex)
    source_authority_packed = bytes.fromhex(source_authority_hex)
    if (
        source_authority_count != EXPECTED_MEMBER_COUNT
        or sha256_bytes(source_authority_packed)
        != EXPECTED_SOURCE_AUTHORITY_PACKED_SHA256
    ):
        raise BuildError("source-authority vector digest")
    rejection_rows = _rejection_class_witnesses()
    boundary = {
        "authorized_current_literal_disposition_count": (
            EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
        ),
        "dictionary_missing_declaration_scope": (
            "inherited_86_document_compiler_fact_not_reproduced_by_"
            "47_source_A11"
        ),
        "directly_disproven_candidate_count": len(directly_disproven_rows),
        "directly_disproven_candidate_sha256": canonical_sha256(
            directly_disproven_rows
        ),
        "directly_disproven_candidates": directly_disproven_rows,
        "inherited_dictionary_missing_declaration_count": 0,
        "inherited_dictionary_missing_relation_sha256": (
            "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
        ),
        "lexical_candidate_is_source_authority": False,
        "minimum_counterexample_count": len(counterexample_rows),
        "minimum_counterexample_sha256": canonical_sha256(counterexample_rows),
        "minimum_counterexamples": counterexample_rows,
        "numeric_range_rejection_witnesses": {
            "domain_sha256": canonical_sha256(range_rows),
            "row_count": len(range_rows),
            "rows": range_rows,
        },
        "opaque_occurrence_code_conditionally_supported": True,
        "opaque_occurrence_code_current_source_supported": True,
        "rejection_class_witness_count": len(rejection_rows),
        "rejection_class_witness_sha256": canonical_sha256(rejection_rows),
        "rejection_class_witnesses": rejection_rows,
        "source_defines_missing_disposition_column": False,
        "source_defines_missing_disposition_vocabulary": True,
        "source_defines_reason_code_column": False,
        "source_defines_reason_vocabulary": True,
        "source_authorized_missing_audit": {
            "domain_sha256": EXPECTED_SOURCE_AUTHORIZED_AUDIT_SHA256,
            "row_count": len(authorized_audit_rows),
            "rows": authorized_audit_rows,
        },
        "source_authorized_missing_occurrences": {
            "domain_sha256": canonical_sha256(authorized_occurrence_rows),
            "row_count": len(authorized_occurrence_rows),
            "rows": authorized_occurrence_rows,
        },
        "unadjudicated_literal_count": EXPECTED_UNADJUDICATED_LITERAL_COUNT,
    }
    census = {
        "canonical_source_row_count": sum(
            row["canonical_row_count"] for row in source_document_rows
        ),
        "canonical_source_row_domain_sha256": _document_digest_manifest(
            source_document_rows,
            "canonical_row_count",
            "canonical_row_domain_sha256",
        ),
        "distinct_lexical_candidate_meaning_count": len(candidate_meanings),
        "distinct_lexical_candidate_meaning_sha256": canonical_sha256(
            sorted(candidate_meanings)
        ),
        "json_integer_candidate_count": candidate_counts["json_integer"],
        "lexical_missing_candidate_count": sum(all_lexical_bits),
        "lexical_missing_candidate_identity_sha256": (
            _document_digest_manifest(
                source_document_rows,
                "lexical_missing_candidate_count",
                "lexical_missing_candidate_identity_sha256",
            )
        ),
        "lexical_missing_candidate_projection_sha256": (
            candidate_projection_sha256
        ),
        "lexical_other_candidate_count": (
            len(all_lexical_bits) - sum(all_lexical_bits)
        ),
        "literal_member_count": sum(all_entry_kind_bits),
        "numeric_range_member_count": (
            len(all_entry_kind_bits) - sum(all_entry_kind_bits)
        ),
        "overlapping_candidate_phrase_counts": dict(phrase_counts),
        "overlapping_candidate_phrase_counts_sha256": canonical_sha256(
            dict(phrase_counts)
        ),
        "pdf_lexical_missing_candidate_count": pdf_candidates,
        "pdf_missing_candidate_field_count": pdf_candidate_field_count,
        "pdf_source_member_count": pdf_members,
        "pdf_source_row_count": pdf_rows,
        "pdf_without_missing_candidate_field_count": (
            pdf_rows - pdf_candidate_field_count
        ),
        "rational_candidate_count": candidate_counts["rational"],
        "selected_exact_candidate_meaning_counts": dict(exact_meaning_counts),
        "selected_exact_candidate_meaning_counts_sha256": canonical_sha256(
            dict(exact_meaning_counts)
        ),
        "source_locator_count": sum(
            row["source_locator_count"] for row in source_document_rows
        ),
        "source_locator_domain_sha256": _document_digest_manifest(
            source_document_rows,
            "source_locator_count",
            "source_locator_domain_sha256",
        ),
        "source_member_complete_domain_sha256": _document_digest_manifest(
            source_document_rows,
            "normalized_entry_count",
            "source_member_complete_domain_sha256",
        ),
        "source_member_count": len(all_lexical_bits),
        "source_member_identity_sha256": _document_digest_manifest(
            source_document_rows,
            "normalized_entry_count",
            "source_member_identity_sha256",
        ),
        "source_authorized_missing_audit_sha256": (
            EXPECTED_SOURCE_AUTHORIZED_AUDIT_SHA256
        ),
        "source_authorized_missing_literal_count": (
            len(authorized_occurrence_rows)
        ),
        "source_authorized_missing_occurrence_sha256": canonical_sha256(
            authorized_occurrence_rows
        ),
        "value_label_lexical_missing_candidate_count": label_candidates,
    }
    if census["canonical_source_row_count"] != EXPECTED_CANONICAL_ROW_COUNT:
        raise BuildError("canonical source row count")
    if census["source_locator_count"] != EXPECTED_SOURCE_LOCATOR_COUNT:
        raise BuildError("source locator count")
    if (
        census["selected_exact_candidate_meaning_counts_sha256"]
        != EXPECTED_SELECTED_EXACT_MEANING_COUNTS_SHA256
    ):
        raise BuildError("selected exact candidate-meaning digest")
    if (
        census["overlapping_candidate_phrase_counts_sha256"]
        != EXPECTED_OVERLAPPING_PHRASE_COUNTS_SHA256
    ):
        raise BuildError("overlapping candidate-phrase digest")

    def vector(
        encoding: str, packed: bytes, packed_hex: str, ones: int
    ) -> dict[str, Any]:
        return {
            "encoding": encoding,
            "one_count": ones,
            "packed_byte_count": len(packed),
            "packed_hex": packed_hex,
            "packed_sha256": sha256_bytes(packed),
            "source_member_count": EXPECTED_MEMBER_COUNT,
            "zero_count": EXPECTED_MEMBER_COUNT - ones,
        }

    artifact: dict[str, Any] = {
        "artifact_id": ARTIFACT_ID,
        "authority_boundary": boundary,
        "conditional_reason_code_law": {
            "authority_failure_disposition_rows": [
                list(row) for row in AUTHORITY_FAILURE_DISPOSITION_ROWS
            ],
            "authority_failure_precedence": [
                CONFLICTING_MISSING_REASON_AUTHORITY,
                INCOMPLETE_MISSING_REASON_AUTHORITY,
            ],
            "conflicting_failure_states": list(
                CONFLICTING_AUTHORITY_FAILURE_STATES
            ),
            "current_source_authorized_missing_literal_action": (
                "nonempty_opaque_source_occurrence_code"
            ),
            "current_unadjudicated_literal_action": "abort_without_emission",
            "current_unadjudicated_literal_disposition": (
                "unadjudicated_source_missing_disposition"
            ),
            "future_authenticated_missing_literal_action": (
                "nonempty_opaque_source_occurrence_code"
            ),
            "future_authenticated_nonmissing_literal_action": "json_null",
            "incomplete_failure_states": list(
                INCOMPLETE_AUTHORITY_FAILURE_STATES
            ),
            "member_identity_version": MEMBER_IDENTITY_VERSION,
            "numeric_range_action": "json_null",
            "reason_code_prefix": REASON_CODE_PREFIX,
            "reason_preimage_version": REASON_PREIMAGE_VERSION,
            "semantic_equivalence_claimed": False,
        },
        "derivation_identity": dict(implementation_identity),
        "entry_kind_vector": vector(
            ENTRY_KIND_VECTOR_ENCODING,
            kind_packed,
            kind_hex,
            EXPECTED_LITERAL_COUNT,
        ),
        "integrity": {
            "canonicalization": (
                "section-10.1 UTF-8 sorted-key compact JSON with one terminal "
                "LF; content_sha256 computed with itself set to 64 zeroes"
            ),
            "content_sha256": ZERO_SHA256,
            "reproduced_from_source_bytes": True,
        },
        "lexical_candidate_vector": vector(
            LEXICAL_VECTOR_ENCODING,
            lexical_packed,
            lexical_hex,
            EXPECTED_LEXICAL_MISSING_COUNT,
        ),
        "registered_source_identity": {
            "projected_source_rows_sha256": (
                EXPECTED_PROJECTED_SOURCE_ROWS_SHA256
            ),
            "registered_source_byte_size": (
                EXPECTED_REGISTERED_SOURCE_BYTE_SIZE
            ),
            "registered_source_count": EXPECTED_REGISTERED_SOURCE_COUNT,
            "registered_source_rows_sha256": (
                EXPECTED_REGISTERED_SOURCE_ROWS_SHA256
            ),
            "registry_byte_size": EXPECTED_REGISTRY_BYTE_SIZE,
            "registry_path": EXPECTED_REGISTRY_PATH,
            "registry_sha256": EXPECTED_REGISTRY_SHA256,
            "source_file_mismatch_count": 0,
            "source_file_verification": "size_and_full_sha256_match",
        },
        "schema_version": SCHEMA_VERSION,
        "source_authority_vector": vector(
            SOURCE_AUTHORITY_VECTOR_ENCODING,
            source_authority_packed,
            source_authority_hex,
            EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT,
        ),
        "source_document_count": len(source_document_rows),
        "source_document_rows": source_document_rows,
        "source_document_rows_sha256": canonical_sha256(source_document_rows),
        "source_member_census": census,
    }
    artifact["integrity"]["content_sha256"] = sha256_bytes(
        canonical_json_bytes(artifact)
    )
    validate_authority_artifact(artifact)
    return artifact


def fresh_build(registry_path: Path, psid_root: Path) -> dict[str, Any]:
    """Authenticate, isolate each derivation, and construct the artifact."""

    registered, projected = load_and_authenticate_sources(
        registry_path, psid_root
    )
    if extraction.pdftotext_version() != "26.04.0":
        raise BuildError("Poppler version drift before semantic parsing")
    if list(extraction.PDFTOTEXT_ARGUMENTS) != [
        "-layout",
        "-enc",
        "UTF-8",
    ]:
        raise BuildError("Poppler argument drift before semantic parsing")
    implementation_identity = _implementation_identity()
    with tempfile.TemporaryDirectory(prefix="amendment11-workers-") as name:
        directory = Path(name)
        manifest_path = directory / "manifest.json"
        worker_capability = secrets.token_hex(32)
        manifest_path.write_bytes(
            canonical_json_bytes(
                {
                    "implementation_identity": implementation_identity,
                    "projected": projected,
                    "registered": registered,
                    "worker_capability": worker_capability,
                }
            )
        )
        summaries = []
        offsets = []
        member_offset = 0
        for count in EXPECTED_DOCUMENT_MEMBER_COUNTS:
            offsets.append(member_offset)
            member_offset += count
        if (
            len(offsets) != EXPECTED_DOCUMENT_COUNT
            or member_offset != EXPECTED_MEMBER_COUNT
        ):
            raise BuildError("pinned per-document member-count vector")

        def run_worker(position: int) -> tuple[int, int, str]:
            output = directory / f"summary-{position}.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker-manifest",
                    str(manifest_path),
                    "--worker-output",
                    str(output),
                    "--worker-position",
                    str(position),
                    "--worker-member-offset",
                    str(offsets[position]),
                    "--worker-capability",
                    worker_capability,
                    "--psid-root",
                    str(psid_root),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
            return (
                position,
                completed.returncode,
                completed.stderr.decode("utf-8", errors="replace"),
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            worker_results = tuple(
                executor.map(run_worker, range(EXPECTED_DOCUMENT_COUNT))
            )
        for position, return_code, error_message in worker_results:
            if return_code:
                raise BuildError(
                    f"isolated derivation {position} failed: "
                    f"exit {return_code}: {error_message.strip()}"
                )

        candidate_projection_hasher = _CanonicalArrayHasher()
        exact_meaning_counter: Counter[str] = Counter()
        phrase_counter: Counter[str] = Counter()
        for position in range(EXPECTED_DOCUMENT_COUNT):
            output = directory / f"summary-{position}.json"
            summary = strict_json_bytes(
                output.read_bytes(), f"isolated summary {position}"
            )
            if not isinstance(summary, dict):
                raise BuildError("isolated summary is not an object")
            projection_count = summary.pop("candidate_projection_count", None)
            projection_sha256 = summary.pop(
                "candidate_projection_sha256", None
            )
            projection_path = output.with_suffix(".candidate-projection.json")
            projection_raw = projection_path.read_bytes()
            projection = strict_json_bytes(
                projection_raw,
                f"isolated lexical-candidate projection {position}",
            )
            if (
                not isinstance(projection, list)
                or type(projection_count) is not int
                or projection_count != len(projection)
                or projection_sha256 != sha256_bytes(projection_raw)
                or projection_raw != canonical_json_bytes(projection)
            ):
                raise BuildError("isolated candidate projection identity")
            for row in projection:
                if (
                    not isinstance(row, Mapping)
                    or tuple(row) != _MISSING_PROJECTION_KEYS
                    or not isinstance(row["source_meaning"], str)
                    or not row["source_meaning"]
                ):
                    raise BuildError("isolated candidate projection row")
                candidate_projection_hasher.update(row)
                meaning = row["source_meaning"]
                exact_meaning_counter[meaning] += 1
                phrase_counter.update(_phrase_matches(meaning))
            summaries.append(summary)
            if os.environ.get("A11_DEBUG"):
                print(
                    f"accepted isolated derivation {position + 1}/"
                    f"{EXPECTED_DOCUMENT_COUNT}",
                    file=sys.stderr,
                    flush=True,
                )
        if candidate_projection_hasher.count != EXPECTED_LEXICAL_MISSING_COUNT:
            raise BuildError("complete candidate projection count")
        exact_meaning_counts = {
            key: exact_meaning_counter[key]
            for key in EXPECTED_SELECTED_EXACT_MEANING_COUNTS
        }
        phrase_counts = {
            key: phrase_counter[key]
            for key in EXPECTED_OVERLAPPING_PHRASE_COUNTS
        }
        if _implementation_identity() != implementation_identity:
            raise BuildError("implementation identity drift during workers")
        artifact = _build_artifact_from_summaries(
            summaries,
            candidate_projection_sha256=(
                candidate_projection_hasher.hexdigest()
            ),
            exact_meaning_counts=exact_meaning_counts,
            implementation_identity=implementation_identity,
            phrase_counts=phrase_counts,
        )
        if _implementation_identity() != implementation_identity:
            raise BuildError("implementation identity drift during build")
        return artifact


def _worker_main(args: argparse.Namespace) -> int:
    validated_parent_identity = _validate_worker_paths(args)
    summary_target = validate_output_target(args.worker_output, args.psid_root)
    projection_target = validate_output_target(
        args.worker_output.with_suffix(".candidate-projection.json"),
        args.psid_root,
    )
    try:
        temp_descriptor = _open_stable_directory(
            Path(tempfile.gettempdir()).resolve(strict=True),
            "post-handoff temporary root",
        )
        try:
            if (
                summary_target.parent_identity != validated_parent_identity
                or projection_target.parent_identity
                != validated_parent_identity
                or summary_target.parent_identity
                != projection_target.parent_identity
                or stat_module.S_IMODE(
                    os.fstat(summary_target.parent_descriptor).st_mode
                )
                & 0o077
                or not _descriptor_is_within(
                    temp_descriptor, summary_target.parent_descriptor
                )
                or not _descriptor_is_within(
                    temp_descriptor, projection_target.parent_descriptor
                )
            ):
                raise BuildError("worker parent changed after confinement")
        finally:
            os.close(temp_descriptor)
        return _worker_main_anchored(args, summary_target, projection_target)
    finally:
        projection_target.close()
        summary_target.close()


def _worker_main_anchored(
    args: argparse.Namespace,
    summary_target: _OutputTarget,
    projection_target: _OutputTarget,
) -> int:
    _manifest_snapshot, raw = _read_regular_leaf(
        summary_target, "manifest.json", require_single_link=True
    )
    manifest = strict_json_bytes(raw, str(args.worker_manifest))
    if not isinstance(manifest, Mapping):
        raise BuildError("worker manifest is not an object")
    registered = manifest.get("registered")
    projected = manifest.get("projected")
    position = args.worker_position
    if (
        set(manifest)
        != {
            "implementation_identity",
            "projected",
            "registered",
            "worker_capability",
        }
        or manifest.get("worker_capability") != args.worker_capability
        or not isinstance(registered, list)
        or not isinstance(projected, list)
        or len(registered) != EXPECTED_DOCUMENT_COUNT
        or len(projected) != EXPECTED_DOCUMENT_COUNT
        or type(position) is not int
        or not 0 <= position < EXPECTED_DOCUMENT_COUNT
    ):
        raise BuildError("worker manifest domain")
    implementation_identity = manifest.get("implementation_identity")
    if (
        not isinstance(implementation_identity, Mapping)
        or dict(implementation_identity) != _implementation_identity()
    ):
        raise BuildError("worker implementation identity drift")
    document = extraction.extract_codebook_rows(
        projected[position], args.psid_root
    )
    summary = _summarize_document(
        registered[position],
        projected[position],
        document,
        position,
        args.worker_member_offset,
    )
    projection = _missing_projection(document)
    projection_raw = canonical_json_bytes(projection)
    _commit_output(projection_target, projection_raw)
    summary["candidate_projection_count"] = len(projection)
    summary["candidate_projection_sha256"] = sha256_bytes(projection_raw)
    _commit_output(summary_target, canonical_json_bytes(summary))
    return 0


@dataclass(frozen=True)
class _LeafSnapshot:
    """Identity and bytes of one descriptor-anchored regular leaf."""

    device: int
    inode: int
    byte_size: int
    mode: int
    sha256: str


@dataclass
class _OutputTarget:
    """One output held beneath a stable, open parent-directory descriptor."""

    requested_path: Path
    resolved_path: Path
    requested_parent: Path
    resolved_parent: Path
    parent_descriptor: int
    parent_identity: tuple[int, int]
    initial_snapshot: _LeafSnapshot | None
    initial_raw: bytes | None

    @property
    def name(self) -> str:
        return self.resolved_path.name

    def close(self) -> None:
        if self.parent_descriptor >= 0:
            os.close(self.parent_descriptor)
            self.parent_descriptor = -1


def _identity(status: os.stat_result) -> tuple[int, int]:
    return status.st_dev, status.st_ino


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _open_stable_directory(path: Path, label: str) -> int:
    """Open one resolved directory and reject a pathname swap."""

    try:
        before = path.stat()
        descriptor = os.open(path, _directory_open_flags())
    except OSError as error:
        raise BuildError(f"cannot anchor {label}") from error
    try:
        opened = os.fstat(descriptor)
        after = path.stat()
        if (
            not stat_module.S_ISDIR(opened.st_mode)
            or _identity(before) != _identity(opened)
            or _identity(after) != _identity(opened)
        ):
            raise BuildError(f"{label} changed while anchoring")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _descriptor_is_within(
    root_descriptor: int, candidate_descriptor: int
) -> bool:
    """Walk descriptor-relative ancestors without consulting pathnames."""

    root_identity = _identity(os.fstat(root_descriptor))
    current = os.dup(candidate_descriptor)
    try:
        while True:
            current_identity = _identity(os.fstat(current))
            if current_identity == root_identity:
                return True
            try:
                parent = os.open("..", _directory_open_flags(), dir_fd=current)
            except OSError as error:
                raise BuildError("cannot inspect output ancestry") from error
            parent_identity = _identity(os.fstat(parent))
            if parent_identity == current_identity:
                os.close(parent)
                return False
            os.close(current)
            current = parent
    finally:
        os.close(current)


def _path_is_within(root: Path, candidate: Path) -> bool:
    """Check the already-resolved lexical hierarchy without new I/O."""

    return candidate == root or root in candidate.parents


def _leaf_lstat(target: _OutputTarget, name: str) -> os.stat_result | None:
    try:
        return os.stat(
            name,
            dir_fd=target.parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    except OSError as error:
        raise BuildError(
            f"cannot inspect output leaf {name}: {error}"
        ) from error


def _read_regular_leaf(
    target: _OutputTarget,
    name: str,
    *,
    require_single_link: bool,
) -> tuple[_LeafSnapshot, bytes]:
    status = _leaf_lstat(target, name)
    if status is None:
        raise BuildError("output target disappeared during build")
    if stat_module.S_ISLNK(status.st_mode):
        raise BuildError("output target is a symbolic link")
    if not stat_module.S_ISREG(status.st_mode):
        raise BuildError("output target is not a regular file")
    if require_single_link and status.st_nlink != 1:
        raise BuildError("output target has hard-link aliases")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(name, flags, dir_fd=target.parent_descriptor)
    except OSError as error:
        raise BuildError(f"cannot open output leaf {name}: {error}") from error
    try:
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            opened = os.fstat(stream.fileno())
            if _identity(opened) != _identity(status):
                raise BuildError("output target changed while opening")
            digest = hashlib.sha256()
            chunks = []
            while chunk := stream.read(1024 * 1024):
                chunks.append(chunk)
                digest.update(chunk)
            finished = os.fstat(stream.fileno())
            raw = b"".join(chunks)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if _identity(finished) != _identity(opened) or finished.st_size != len(
        raw
    ):
        raise BuildError("output target changed while reading")
    if not stat_module.S_ISREG(finished.st_mode):
        raise BuildError("output target changed file type while reading")
    if require_single_link and finished.st_nlink != 1:
        raise BuildError("output target gained hard-link aliases")
    return (
        _LeafSnapshot(
            device=finished.st_dev,
            inode=finished.st_ino,
            byte_size=len(raw),
            mode=stat_module.S_IMODE(finished.st_mode),
            sha256=digest.hexdigest(),
        ),
        raw,
    )


def _initial_leaf_snapshot(
    target: _OutputTarget,
) -> tuple[_LeafSnapshot | None, bytes | None]:
    if _leaf_lstat(target, target.name) is None:
        return None, None
    snapshot, raw = _read_regular_leaf(
        target, target.name, require_single_link=True
    )
    return snapshot, raw


def _assert_parent_stable(target: _OutputTarget) -> None:
    try:
        current_parent = target.requested_parent.resolve(strict=True)
        current_status = current_parent.stat()
        anchored_status = os.fstat(target.parent_descriptor)
    except OSError as error:
        raise BuildError("output parent changed during build") from error
    if (
        _identity(current_status) != target.parent_identity
        or _identity(anchored_status) != target.parent_identity
        or current_parent != target.resolved_parent
    ):
        raise BuildError("output parent changed during build")


def _assert_leaf_stable(target: _OutputTarget) -> bytes | None:
    _assert_parent_stable(target)
    current_status = _leaf_lstat(target, target.name)
    if target.initial_snapshot is None:
        if current_status is not None:
            raise BuildError("output target changed during build")
        _assert_parent_stable(target)
        return None
    if current_status is None:
        raise BuildError("output target changed during build")
    snapshot, raw = _read_regular_leaf(
        target, target.name, require_single_link=True
    )
    if snapshot != target.initial_snapshot:
        raise BuildError("output target changed during build")
    _assert_parent_stable(target)
    return raw


def _temporary_leaf_name(target: _OutputTarget, purpose: str) -> str:
    return f".{target.name}.a11-{purpose}-{secrets.token_hex(12)}"


def _stage_output(
    target: _OutputTarget, raw: bytes, *, mode: int = 0o644
) -> tuple[str, tuple[int, int]]:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = -1
    stage_name = ""
    for _attempt in range(100):
        stage_name = _temporary_leaf_name(target, "stage")
        try:
            descriptor = os.open(
                stage_name,
                flags,
                0o600,
                dir_fd=target.parent_descriptor,
            )
            break
        except FileExistsError:
            continue
        except OSError as error:
            raise BuildError(f"cannot stage output: {error}") from error
    if descriptor < 0:
        raise BuildError("cannot allocate unique output stage")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            os.fchmod(stream.fileno(), mode)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        snapshot, observed = _read_regular_leaf(
            target, stage_name, require_single_link=True
        )
        if observed != raw:
            raise BuildError("staged output failed byte validation")
        return stage_name, (snapshot.device, snapshot.inode)
    except BaseException:
        _discard_leaf(target, stage_name)
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _discard_leaf(target: _OutputTarget, name: str | None) -> None:
    if name is None:
        return
    try:
        os.unlink(name, dir_fd=target.parent_descriptor)
    except OSError:
        pass


def _backup_output(target: _OutputTarget) -> str | None:
    if target.initial_snapshot is None:
        return None
    for _attempt in range(100):
        backup_name = _temporary_leaf_name(target, "backup")
        try:
            os.link(
                target.name,
                backup_name,
                src_dir_fd=target.parent_descriptor,
                dst_dir_fd=target.parent_descriptor,
                follow_symlinks=False,
            )
        except FileExistsError:
            continue
        except OSError as error:
            raise BuildError(
                f"cannot back up output target: {error}"
            ) from error
        original = _leaf_lstat(target, target.name)
        backup = _leaf_lstat(target, backup_name)
        expected_identity = (
            target.initial_snapshot.device,
            target.initial_snapshot.inode,
        )
        if (
            original is None
            or backup is None
            or _identity(original) != expected_identity
            or _identity(backup) != expected_identity
            or original.st_nlink != 2
            or backup.st_nlink != 2
        ):
            _discard_leaf(target, backup_name)
            raise BuildError("output target changed while backing up")
        return backup_name
    raise BuildError("cannot allocate unique output backup")


def _output_is_restored(target: _OutputTarget) -> bool:
    status = _leaf_lstat(target, target.name)
    if target.initial_snapshot is None:
        return status is None
    if status is None:
        return False
    try:
        snapshot, raw = _read_regular_leaf(
            target, target.name, require_single_link=True
        )
    except BuildError:
        return False
    return (
        snapshot.byte_size == target.initial_snapshot.byte_size
        and snapshot.mode == target.initial_snapshot.mode
        and snapshot.sha256 == target.initial_snapshot.sha256
        and raw == target.initial_raw
    )


def _unlink_leaf(target: _OutputTarget, name: str) -> None:
    try:
        os.unlink(name, dir_fd=target.parent_descriptor)
    except FileNotFoundError:
        return
    except OSError as error:
        raise BuildError(f"cannot unlink transaction leaf {name}") from error


def _restore_output(
    target: _OutputTarget, backup_name: str | None
) -> str | None:
    last_error: BaseException | None = None
    for _attempt in range(2):
        stage_name: str | None = None
        try:
            if target.initial_raw is None:
                _unlink_leaf(target, target.name)
            else:
                stage_name, _stage_identity = _stage_output(
                    target,
                    target.initial_raw,
                    mode=target.initial_snapshot.mode,
                )
                os.replace(
                    stage_name,
                    target.name,
                    src_dir_fd=target.parent_descriptor,
                    dst_dir_fd=target.parent_descriptor,
                )
                stage_name = None
            os.fsync(target.parent_descriptor)
        except BaseException as error:
            last_error = error
        finally:
            _discard_leaf(target, stage_name)
        try:
            if _output_is_restored(target):
                if backup_name is not None:
                    _unlink_leaf(target, backup_name)
                os.fsync(target.parent_descriptor)
                if _output_is_restored(target):
                    return None
        except BaseException as error:
            last_error = error
    return str(last_error or "prior output bytes were not restored")


def _verify_committed_output(
    target: _OutputTarget,
    raw: bytes,
    expected_identity: tuple[int, int],
) -> None:
    snapshot, observed = _read_regular_leaf(
        target, target.name, require_single_link=True
    )
    if (
        snapshot.device,
        snapshot.inode,
    ) != expected_identity or observed != raw:
        raise BuildError("committed output identity or bytes mismatch")
    _assert_parent_stable(target)


def _commit_output(target: _OutputTarget, raw: bytes) -> tuple[int, int]:
    """Replace one output or restore its byte-identical predecessor."""

    _assert_leaf_stable(target)
    stage_name, stage_identity = _stage_output(target, raw)
    backup_name: str | None = None
    commit_succeeded = False
    try:
        _assert_leaf_stable(target)
        backup_name = _backup_output(target)
        try:
            # Make the stable predecessor link durable before changing the
            # named destination.
            os.fsync(target.parent_descriptor)
            os.replace(
                stage_name,
                target.name,
                src_dir_fd=target.parent_descriptor,
                dst_dir_fd=target.parent_descriptor,
            )
            os.fsync(target.parent_descriptor)
            _verify_committed_output(target, raw, stage_identity)
            if backup_name is not None:
                _unlink_leaf(target, backup_name)
                backup_name = None
            os.fsync(target.parent_descriptor)
            _verify_committed_output(target, raw, stage_identity)
            # No fallible filesystem operation may intervene between this
            # final verification and acceptance of the transaction.
            _verify_committed_output(target, raw, stage_identity)
            commit_succeeded = True
        except BaseException as commit_error:
            rollback_error = _restore_output(target, backup_name)
            if rollback_error is not None:
                location = (
                    str(target.resolved_parent / backup_name)
                    if backup_name is not None
                    else "no predecessor backup"
                )
                backup_name = None
                raise BuildError(
                    "output replacement failed and rollback remains "
                    f"incomplete; recovery material: {location}; "
                    f"rollback error: {rollback_error}"
                ) from commit_error
            if isinstance(commit_error, Exception):
                raise BuildError(
                    "output replacement failed; prior target restored"
                ) from commit_error
            raise
    finally:
        _discard_leaf(target, stage_name)
    if not commit_succeeded:  # pragma: no cover - every failure raises
        raise BuildError("output transaction did not commit")
    return stage_identity


def validate_output_target(path: Path, psid_root: Path) -> _OutputTarget:
    """Anchor and snapshot one nonaliased output before the long build."""

    requested = path.absolute()
    try:
        parent = requested.parent.resolve(strict=True)
        parent_status = parent.stat()
    except OSError as error:
        raise BuildError("output parent does not resolve") from error
    if not stat_module.S_ISDIR(parent_status.st_mode):
        raise BuildError("output parent is not a directory")
    try:
        parent_descriptor = os.open(parent, _directory_open_flags())
    except OSError as error:
        raise BuildError("cannot anchor output parent") from error
    target = _OutputTarget(
        requested_path=requested,
        resolved_path=parent / requested.name,
        requested_parent=requested.parent,
        resolved_parent=parent,
        parent_descriptor=parent_descriptor,
        parent_identity=_identity(parent_status),
        initial_snapshot=None,
        initial_raw=None,
    )
    try:
        if _identity(os.fstat(parent_descriptor)) != target.parent_identity:
            raise BuildError("output parent changed while anchoring")
        repository_root = REPOSITORY_ROOT.resolve(strict=True)
        source_root = psid_root.resolve(strict=True)
        anchored_directories: list[int] = []
        try:
            repository_descriptor = _open_stable_directory(
                repository_root, "repository root"
            )
            anchored_directories.append(repository_descriptor)
            source_descriptor = _open_stable_directory(
                source_root, "PSID source root"
            )
            anchored_directories.append(source_descriptor)
            default_parent_descriptor = _open_stable_directory(
                DEFAULT_OUTPUT.parent.resolve(strict=True),
                "default output parent",
            )
            anchored_directories.append(default_parent_descriptor)
            if _path_is_within(source_root, parent) or _descriptor_is_within(
                source_descriptor, target.parent_descriptor
            ):
                raise BuildError("output target aliases the PSID source tree")
            inside_repository = _path_is_within(
                repository_root, parent
            ) or _descriptor_is_within(
                repository_descriptor, target.parent_descriptor
            )
            if inside_repository and (
                _identity(os.fstat(default_parent_descriptor))
                != target.parent_identity
                or requested.name != DEFAULT_OUTPUT.name
            ):
                raise BuildError("repository output is not the named artifact")
        finally:
            for descriptor in reversed(anchored_directories):
                os.close(descriptor)
        target.initial_snapshot, target.initial_raw = _initial_leaf_snapshot(
            target
        )
        return target
    except BaseException:
        target.close()
        raise


def _validate_worker_paths(args: argparse.Namespace) -> tuple[int, int]:
    """Confine hidden worker products to one private temporary directory."""

    position = args.worker_position
    if (
        type(position) is not int
        or not 0 <= position < EXPECTED_DOCUMENT_COUNT
    ):
        raise BuildError("worker position")
    if (
        args.check
        or not isinstance(args.worker_capability, str)
        or len(args.worker_capability) != 64
        or any(
            character not in "0123456789abcdef"
            for character in args.worker_capability
        )
    ):
        raise BuildError("worker capability")
    expected_offset = sum(EXPECTED_DOCUMENT_MEMBER_COUNTS[:position])
    if args.worker_member_offset != expected_offset:
        raise BuildError("worker member offset")
    manifest = args.worker_manifest.absolute()
    output = args.worker_output.absolute()
    projection = output.with_suffix(".candidate-projection.json")
    try:
        manifest_parent = manifest.parent.resolve(strict=True)
        output_parent = output.parent.resolve(strict=True)
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
        source_root = args.psid_root.resolve(strict=True)
        repository_root = REPOSITORY_ROOT.resolve(strict=True)
    except OSError as error:
        raise BuildError("worker path does not resolve") from error
    anchored_directories: list[int] = []
    validated_parent_identity: tuple[int, int] | None = None
    try:
        manifest_parent_descriptor = _open_stable_directory(
            manifest_parent, "worker manifest parent"
        )
        anchored_directories.append(manifest_parent_descriptor)
        output_parent_descriptor = _open_stable_directory(
            output_parent, "worker output parent"
        )
        anchored_directories.append(output_parent_descriptor)
        temp_descriptor = _open_stable_directory(temp_root, "temporary root")
        anchored_directories.append(temp_descriptor)
        source_descriptor = _open_stable_directory(
            source_root, "PSID source root"
        )
        anchored_directories.append(source_descriptor)
        repository_descriptor = _open_stable_directory(
            repository_root, "repository root"
        )
        anchored_directories.append(repository_descriptor)
        within_temp = _path_is_within(
            temp_root, output_parent
        ) or _descriptor_is_within(temp_descriptor, output_parent_descriptor)
        within_source = _path_is_within(
            source_root, output_parent
        ) or _descriptor_is_within(source_descriptor, output_parent_descriptor)
        within_repository = _path_is_within(
            repository_root, output_parent
        ) or _descriptor_is_within(
            repository_descriptor, output_parent_descriptor
        )
        if (
            _identity(os.fstat(manifest_parent_descriptor))
            != _identity(os.fstat(output_parent_descriptor))
            or manifest.name != "manifest.json"
            or output.name != f"summary-{position}.json"
            or not within_temp
            or within_source
            or within_repository
        ):
            raise BuildError("worker output confinement")
        parent_mode = stat_module.S_IMODE(
            os.fstat(output_parent_descriptor).st_mode
        )
        if parent_mode & 0o077:
            raise BuildError("worker directory is not private")
        validated_parent_identity = _identity(
            os.fstat(output_parent_descriptor)
        )
        try:
            manifest_status = os.stat(
                manifest.name,
                dir_fd=manifest_parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as error:
            raise BuildError("worker manifest is unavailable") from error
        if (
            stat_module.S_ISLNK(manifest_status.st_mode)
            or not stat_module.S_ISREG(manifest_status.st_mode)
            or manifest_status.st_nlink != 1
        ):
            raise BuildError("worker manifest identity")
        for candidate in (output, projection):
            try:
                os.stat(
                    candidate.name,
                    dir_fd=output_parent_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                continue
            except OSError as error:
                raise BuildError("cannot inspect worker output") from error
            raise BuildError("worker output already exists")
    finally:
        for descriptor in reversed(anchored_directories):
            os.close(descriptor)
    if validated_parent_identity is None:  # pragma: no cover - failures raise
        raise BuildError("worker parent identity unavailable")
    return validated_parent_identity


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--psid-root", type=Path, default=DEFAULT_PSID_ROOT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--worker-manifest", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-position", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "--worker-member-offset", type=int, help=argparse.SUPPRESS
    )
    parser.add_argument("--worker-capability", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    worker_values = (
        args.worker_manifest,
        args.worker_output,
        args.worker_position,
        args.worker_member_offset,
        args.worker_capability,
    )
    if any(value is not None for value in worker_values):
        if any(value is None for value in worker_values):
            raise BuildError("incomplete isolated-worker arguments")
        return _worker_main(args)
    registry_path = REPOSITORY_ROOT / EXPECTED_REGISTRY_PATH
    target = validate_output_target(args.output, args.psid_root)
    try:
        artifact = fresh_build(registry_path, args.psid_root)
        raw = canonical_json_bytes(artifact)
        committed_identity: tuple[int, int] | None = None
        if args.check:
            candidate = _assert_leaf_stable(target)
            if candidate is None:
                raise BuildError(
                    f"artifact does not exist: {target.resolved_path}"
                )
            strict_json_bytes(candidate, str(target.resolved_path))
            if candidate != raw:
                raise BuildError(
                    "fresh artifact is not byte-equal to candidate"
                )
        else:
            committed_identity = _commit_output(target, raw)
        if committed_identity is None:
            if _assert_leaf_stable(target) != raw:
                raise BuildError("checked output changed before acceptance")
        else:
            try:
                _verify_committed_output(target, raw, committed_identity)
            except BaseException as acceptance_error:
                rollback_error = _restore_output(target, None)
                if rollback_error is not None:
                    raise BuildError(
                        "output changed before acceptance and rollback "
                        f"failed: {rollback_error}"
                    ) from acceptance_error
                if isinstance(acceptance_error, Exception):
                    raise BuildError(
                        "output changed before acceptance; prior target "
                        "restored"
                    ) from acceptance_error
                raise
        summary = {
            "artifact_path": str(target.resolved_path),
            "byte_size": len(raw),
            "check": args.check,
            "content_sha256": artifact["integrity"]["content_sha256"],
            "file_sha256": sha256_bytes(raw),
            "authorized_reason_assignment_count": (
                EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
            ),
            "lexical_missing_candidate_count": (
                EXPECTED_LEXICAL_MISSING_COUNT
            ),
            "literal_member_count": EXPECTED_LITERAL_COUNT,
            "source_member_count": EXPECTED_MEMBER_COUNT,
            "status": "pass",
            "unadjudicated_literal_count": (
                EXPECTED_UNADJUDICATED_LITERAL_COUNT
            ),
        }
        sys.stdout.buffer.write(canonical_json_bytes(summary))
        return 0
    finally:
        target.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, MissingReasonAuthorityError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
