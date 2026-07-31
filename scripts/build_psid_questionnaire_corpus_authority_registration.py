#!/usr/bin/env python3
"""Build the fail-closed PSID documentation-corpus registration attempt.

The 3 GB corpus remains in the conventional external PSID staging tree.  This
source-only builder reads the capture ceremony inputs and document bytes; it
does not import a PSID reader, crosswalk, candidate model, or adjudication
registry.  A failed identity closure is serialized as an audit attempt, never
as an accepted authority registry.
"""

from __future__ import annotations

import argparse
import copy
import decimal
import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)
OUT_PATH = (
    ROOT
    / "data"
    / "external"
    / "psid_questionnaire_corpus_authority_registration_attempt_v1.json"
)

SCHEMA_VERSION = (
    "psid_questionnaire_corpus_authority_registration_attempt.v1"
)
ARTIFACT_ID = SCHEMA_VERSION
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
CAPTURE_ROOT_ID = "psid_external_staging_root"
CAPTURE_RELATIVE_PATH = "documentation/capture1"
FAILURE_DISPOSITION = "abort_without_accepted_corpus_authority"

EXPECTED_DOCUMENT_ROW_COUNT = 456
EXPECTED_LINK_COUNT = 465
EXPECTED_UNIQUE_HREF_COUNT = 456
EXPECTED_DUPLICATE_LINK_COUNT = 9
EXPECTED_DISAMBIGUATION_COUNT = 3
EXPECTED_UNIQUE_DOCUMENT_IDENTITY_COUNT = 455
EXPECTED_ORDERED_UNIQUE_HREFS_SHA256 = (
    "baa4c9fc45343701afea62349497f1e0fe5624ab12494f71fd10633254c0c323"
)
EXPECTED_DOCUMENT_ROWS_SHA256 = (
    "7e4bc4eeb395c8c65a79fdb0d390c0f7de3591af98cef951d796c6ee7d8ff559"
)
EXPECTED_CONTENT_SHA256 = (
    "9f15d3d0472ec74dd7fc3388f6a4a516f8d253ec5b2bc52d242a287091865678"
)
EXPECTED_FAILED_DOCUMENT_IDS = [
    "psid-corpus-document-0250",
    "psid-corpus-document-0253",
    "psid-corpus-document-0254",
    "psid-corpus-document-0256",
    "psid-corpus-document-0259",
    "psid-corpus-document-0262",
    "psid-corpus-document-0265",
    "psid-corpus-document-0278",
    "psid-corpus-document-0322",
    "psid-corpus-document-0342",
    "psid-corpus-document-0356",
    "psid-corpus-document-0359",
    "psid-corpus-document-0371",
    "psid-corpus-document-0379",
    "psid-corpus-document-0380",
    "psid-corpus-document-0383",
]
EXPECTED_DISAMBIGUATION_ROWS = [
    {
        "line_number": 6,
        "digest_row_filename": "Active%20Saving_Intro.pdf",
        "sha256": "01a18b2e40c11311be00592f9d175effaead8cba0b4a51147e20d7d549b58c05",
        "on_disk_filename": "Active%20Saving_Intro.pdf",
    },
    {
        "line_number": 7,
        "digest_row_filename": "PCGchild.pdf",
        "sha256": "164310dd55a198cb23f739586cfa57cfad63d80c36e9c74cc51083be7b775041",
        "on_disk_filename": "cds-i_english_PCGchild.pdf",
    },
    {
        "line_number": 8,
        "digest_row_filename": "PCGChild.pdf",
        "sha256": "168eb8fbae17615ca9d164c7f0ecd8676affd38996938bf2a0be9ac8d593a4ad",
        "on_disk_filename": "cds-i_spanish_PCGChild.pdf",
    },
]

# Capture-ceremony files are frozen independently of the generated artifact.
CAPTURE_INPUT_SPECS = (
    (
        "browser_digest_manifest",
        "browser_digests.txt",
        41_272,
        "b5273e5818c796c0c6208ae562c724a599b9b2b4214599347c1c10a9aa64c3c7",
    ),
    (
        "name_disambiguation",
        "name_disambiguation.txt",
        626,
        "71ff7ad133830d31a80190e5a2bd6b52fb870841b9571b778f4b094deae23376",
    ),
    (
        "source_page_index",
        "psid_documents_index.html",
        668_104,
        "159ec5a660b2b302ef16153f6570f24252e2f77a2b9297dd111e39002846a5b7",
    ),
    (
        "source_link_inventory",
        "psid_documents_inventory.json",
        58_679,
        "4c18313b66e3afa4737081d186deb9cf5a2cb7ff4355386cbd5c99bfa2fa21bd",
    ),
)

# Frozen repo authorities are constants.  The ratified design is append-only,
# so later validation accepts only a live file having these exact bytes as its
# prefix.  The staging implementation is an exact frozen file identity.
FROZEN_REPO_AUTHORITY_IDENTITIES = {
    "docs/design/covered_earnings_correction.md": {
        "identity_scope": "append_only_prefix",
        "size_bytes": 1_252_209,
        "sha256": (
            "29f0cb134e95b6215dc502d0e25392b5c971fdb93dfad40fd5d221e8a482a1b7"
        ),
    },
    "src/populace_dynamics/data/psid.py": {
        "identity_scope": "exact_file",
        "size_bytes": 14_292,
        "sha256": (
            "b0983390f84833f1b1436f60a066a829700f6149193aa712808b87d53867e29f"
        ),
    },
}

REPO_AUTHORITY_LOCATOR_SPECS = (
    (
        "psid_source_only_authority_registration_law",
        "docs/design/covered_earnings_correction.md",
        706,
        718,
        "source-only extraction and byte-pinned PSID authority law",
    ),
    (
        "psid_authority_manifest_and_locator_law",
        "docs/design/covered_earnings_correction.md",
        720,
        800,
        "immutable source manifest and locator identity law",
    ),
    (
        "psid_inventory_integrity_law",
        "docs/design/covered_earnings_correction.md",
        809,
        826,
        "complete counts, ordered hashes, and source reproduction law",
    ),
    (
        "psid_absence_proof_law",
        "docs/design/covered_earnings_correction.md",
        847,
        874,
        "source-backed structural-absence and fail-closed drift law",
    ),
    (
        "authenticated_registry_identity_law",
        "docs/design/covered_earnings_correction.md",
        17962,
        18032,
        "strict authenticated authority identity and append-only history law",
    ),
    (
        "psid_external_staging_law",
        "src/populace_dynamics/data/psid.py",
        63,
        109,
        "PSID products staged outside Git",
    ),
)

_DIGEST_ROW = re.compile(r"^([0-9a-f]{64}) ([1-9][0-9]*) (.+)$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json_bytes(value: Any) -> bytes:
    """Return the repository's frozen canonical JSON encoding."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _strictly_parsed_document(raw: bytes, label: str) -> Any:
    """Incident-5 parser: reject ambiguous keys and lossy JSON numbers."""

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(
                    f"{label} contains duplicate object key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> Any:
        raise ValueError(f"{label} contains non-finite constant {token}")

    def finite_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise ValueError(f"{label} contains non-finite number {token}")
        if decimal.Decimal(token) != decimal.Decimal(str(value)):
            raise ValueError(f"{label} contains inexact number {token}")
        return value

    try:
        text = raw.decode("utf-8")
        if text.startswith("\ufeff"):
            raise ValueError(f"{label} contains a leading U+FEFF BOM")
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
            parse_float=finite_float,
        )
    except (
        UnicodeError,
        ValueError,
        OverflowError,
        RecursionError,
        decimal.DecimalException,
    ) as error:
        raise ValueError(
            f"{label} is not a uniquely parseable JSON document"
        ) from error


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _full_file_locator(filename: str, raw: bytes) -> dict[str, Any]:
    digest = _sha256(raw)
    return {
        "location_type": "full_file_byte_range",
        "filename": filename,
        "full_file_sha256": digest,
        "size_bytes": len(raw),
        "byte_start": 0,
        "byte_end": len(raw),
        "range_sha256": digest,
    }


def _capture_inputs(capture_root: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    rows: list[dict[str, Any]] = []
    raw_by_id: dict[str, bytes] = {}
    for input_id, filename, size_bytes, sha256 in CAPTURE_INPUT_SPECS:
        path = capture_root / filename
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"{input_id} is unavailable or symlinked")
        raw = path.read_bytes()
        if len(raw) != size_bytes or _sha256(raw) != sha256:
            raise ValueError(f"{input_id} frozen identity drift")
        rows.append(
            {
                "capture_input_id": input_id,
                "locator": _full_file_locator(filename, raw),
            }
        )
        raw_by_id[input_id] = raw
    return rows, raw_by_id


def _frozen_repo_bytes(committed_path: str) -> tuple[bytes, Mapping[str, Any]]:
    identity = FROZEN_REPO_AUTHORITY_IDENTITIES[committed_path]
    live = (ROOT / committed_path).read_bytes()
    size_bytes = identity["size_bytes"]
    if identity["identity_scope"] == "append_only_prefix":
        if len(live) < size_bytes:
            raise ValueError(f"{committed_path} truncated frozen prefix")
        frozen = live[:size_bytes]
    else:
        if len(live) != size_bytes:
            raise ValueError(f"{committed_path} frozen size drift")
        frozen = live
    if _sha256(frozen) != identity["sha256"]:
        raise ValueError(f"{committed_path} frozen identity drift")
    return frozen, identity


def _repo_authority_locators() -> list[dict[str, Any]]:
    cache: dict[str, tuple[bytes, Mapping[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for locator_id, path, line_start, line_end, description in (
        REPO_AUTHORITY_LOCATOR_SPECS
    ):
        if path not in cache:
            cache[path] = _frozen_repo_bytes(path)
        raw, identity = cache[path]
        lines = raw.splitlines(keepends=True)
        if not 1 <= line_start <= line_end <= len(lines):
            raise ValueError(f"{locator_id} line range outside frozen bytes")
        byte_start = sum(len(line) for line in lines[: line_start - 1])
        byte_end = sum(len(line) for line in lines[:line_end])
        rows.append(
            {
                "locator_id": locator_id,
                "committed_path": path,
                "identity_scope": identity["identity_scope"],
                "full_source_sha256": identity["sha256"],
                "size_bytes": identity["size_bytes"],
                "line_start": line_start,
                "line_end": line_end,
                "byte_start": byte_start,
                "byte_end": byte_end,
                "range_sha256": _sha256(raw[byte_start:byte_end]),
                "description": description,
            }
        )
    return rows


def _digest_rows(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise ValueError("browser digest manifest is not UTF-8") from error
    rows: list[dict[str, Any]] = []
    for row_number, line in enumerate(text.splitlines(), start=1):
        match = _DIGEST_ROW.fullmatch(line)
        if match is None:
            raise ValueError(f"browser digest row {row_number} grammar drift")
        sha256, size, filename = match.groups()
        if Path(filename).name != filename or filename in {".", ".."}:
            raise ValueError(f"browser digest row {row_number} unsafe filename")
        rows.append(
            {
                "digest_row_number": row_number,
                "sha256": sha256,
                "size_bytes": int(size),
                "digest_row_filename": filename,
            }
        )
    if len(rows) != EXPECTED_DOCUMENT_ROW_COUNT:
        raise ValueError("browser digest manifest row count drift")
    return rows


def _disambiguation_rows(raw: bytes) -> list[dict[str, Any]]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise ValueError("name disambiguation file is not UTF-8") from error
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise ValueError(
                f"name disambiguation line {line_number} grammar drift"
            )
        digest_name, sha256, on_disk_name = parts
        if (
            _HEX64.fullmatch(sha256) is None
            or Path(digest_name).name != digest_name
            or Path(on_disk_name).name != on_disk_name
            or digest_name in {".", ".."}
            or on_disk_name in {".", ".."}
        ):
            raise ValueError(
                f"name disambiguation line {line_number} identity drift"
            )
        rows.append(
            {
                "line_number": line_number,
                "digest_row_filename": digest_name,
                "sha256": sha256,
                "on_disk_filename": on_disk_name,
            }
        )
    if len(rows) != EXPECTED_DISAMBIGUATION_COUNT:
        raise ValueError("name disambiguation row count drift")
    keys = [(row["digest_row_filename"], row["sha256"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("name disambiguation keys are not unique")
    return rows


class _HrefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href is not None:
            self.hrefs.append(href)


def _validate_inventory_against_html(html_raw: bytes, inventory_raw: bytes) -> None:
    """Require every captured inventory occurrence to exist in the source page."""

    try:
        html_text = html_raw.decode("utf-8")
    except UnicodeError as error:
        raise ValueError("PSID source-page index is not UTF-8") from error
    inventory = _strictly_parsed_document(
        inventory_raw, "PSID document link inventory"
    )
    if not isinstance(inventory, list):
        raise ValueError("PSID document link inventory is not an array")
    collector = _HrefCollector()
    collector.feed(html_text)
    source_counts = Counter(urldefrag(href).url for href in collector.hrefs)
    inventory_counts = Counter(item["href"] for item in inventory)
    if any(source_counts[href] < count for href, count in inventory_counts.items()):
        raise ValueError("PSID link inventory is not source-page backed")


def _unique_inventory_links(raw: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    value = _strictly_parsed_document(raw, "PSID document link inventory")
    if not isinstance(value, list) or len(value) != EXPECTED_LINK_COUNT:
        raise ValueError("PSID document link inventory count drift")
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for link_position, item in enumerate(value, start=1):
        if not isinstance(item, dict) or set(item) != {"href", "text", "row"}:
            raise ValueError(f"link inventory row {link_position} schema drift")
        if not all(isinstance(item[key], str) for key in item):
            raise ValueError(f"link inventory row {link_position} type drift")
        href = item["href"]
        if not href.startswith("https://psidonline.isr.umich.edu/"):
            raise ValueError(f"link inventory row {link_position} origin drift")
        if href in seen:
            continue
        seen.add(href)
        unique.append(
            {
                "unique_link_position": len(unique) + 1,
                "first_link_position": link_position,
                "href": href,
                "text": item["text"],
                "source_page_row": item["row"],
            }
        )
    duplicate_count = len(value) - len(unique)
    if (
        len(unique) != EXPECTED_UNIQUE_HREF_COUNT
        or duplicate_count != EXPECTED_DUPLICATE_LINK_COUNT
    ):
        raise ValueError("link inventory deduplication domain drift")
    summary = {
        "link_count": len(value),
        "unique_href_count": len(unique),
        "duplicate_link_count": duplicate_count,
        "deduplication_rule": "stable_first_occurrence_by_exact_href",
        "ordered_unique_hrefs_sha256": _sha256(
            canonical_json_bytes([row["href"] for row in unique])
        ),
    }
    return unique, summary


def _document_candidates(
    capture_root: Path,
    digest_rows: list[dict[str, Any]],
    links: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(digest_rows) != len(links):
        raise ValueError("digest and unique-link domains are not positional")
    mapping_by_key = {
        (row["digest_row_filename"], row["sha256"]): row["on_disk_filename"]
        for row in mappings
    }
    rows: list[dict[str, Any]] = []
    for digest_row, link in zip(digest_rows, links, strict=True):
        row_number = digest_row["digest_row_number"]
        expected_sha = digest_row["sha256"]
        expected_size = digest_row["size_bytes"]
        digest_name = digest_row["digest_row_filename"]
        on_disk_name = mapping_by_key.get((digest_name, expected_sha), digest_name)
        path = capture_root / on_disk_name
        observed_identity: dict[str, Any] | None = None
        locator: dict[str, Any] | None = None
        if path.is_file() and not path.is_symlink():
            raw = path.read_bytes()
            observed_identity = {
                "filename": on_disk_name,
                "sha256": _sha256(raw),
                "size_bytes": len(raw),
            }
            if (
                observed_identity["sha256"] == expected_sha
                and observed_identity["size_bytes"] == expected_size
            ):
                availability = "verified"
                locator = _full_file_locator(on_disk_name, raw)
            else:
                availability = "identity_mismatch"
        else:
            availability = "missing"
        identity_preimage = [
            row_number,
            link["href"],
            digest_name,
            expected_sha,
            expected_size,
        ]
        rows.append(
            {
                "source_document_id": f"psid-corpus-document-{row_number:04d}",
                "document_identity_sha256": _sha256(
                    canonical_json_bytes(identity_preimage)
                ),
                "digest_row_number": row_number,
                "unique_link_position": link["unique_link_position"],
                "first_link_position": link["first_link_position"],
                "source_url": link["href"],
                "source_link_text": link["text"],
                "source_page_row": link["source_page_row"],
                "digest_row_filename": digest_name,
                "on_disk_filename": on_disk_name,
                "expected_sha256": expected_sha,
                "expected_size_bytes": expected_size,
                "availability": availability,
                "observed_identity": observed_identity,
                "locator": locator,
            }
        )
    return rows


def _content_sha256(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return _sha256(canonical_json_bytes(preimage))


def build_registration_attempt(capture_root: Path = DEFAULT_CAPTURE_ROOT) -> dict[str, Any]:
    """Reconstruct the complete capture attempt from staged source bytes."""

    capture_inputs, raw = _capture_inputs(capture_root)
    digest_rows = _digest_rows(raw["browser_digest_manifest"])
    mappings = _disambiguation_rows(raw["name_disambiguation"])
    _validate_inventory_against_html(
        raw["source_page_index"], raw["source_link_inventory"]
    )
    links, link_summary = _unique_inventory_links(raw["source_link_inventory"])
    documents = _document_candidates(capture_root, digest_rows, links, mappings)
    verified_ids = [
        row["source_document_id"]
        for row in documents
        if row["availability"] == "verified"
    ]
    failed_ids = [
        row["source_document_id"]
        for row in documents
        if row["availability"] != "verified"
    ]
    registration_status = "pass" if not failed_ids else "fail"
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "authority_scope": "external_psid_questionnaire_and_codebook_bytes",
        "staging": {
            "staging_root_id": CAPTURE_ROOT_ID,
            "relative_capture_path": CAPTURE_RELATIVE_PATH,
            "absolute_paths_serialized": False,
            "repo_authority_locator_id": "psid_external_staging_law",
        },
        "repo_authority_locators": _repo_authority_locators(),
        "capture_input_identities": capture_inputs,
        "link_inventory_summary": link_summary,
        "name_disambiguation": mappings,
        "document_candidates": documents,
        "document_candidate_count": len(documents),
        "unique_document_identity_count": len(
            {
                (row["expected_sha256"], row["expected_size_bytes"])
                for row in documents
            }
        ),
        "ordered_document_ids": [row["source_document_id"] for row in documents],
        "document_rows_sha256": _sha256(canonical_json_bytes(documents)),
        "verified_document_ids": verified_ids,
        "verified_document_count": len(verified_ids),
        "failed_document_ids": failed_ids,
        "failed_document_count": len(failed_ids),
        "registration_status": registration_status,
        "failure_disposition": FAILURE_DISPOSITION,
        "accepted_authority_registry": None,
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
            "structural_status": "pass",
            "reproduced_from_available_capture_bytes": True,
        },
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    validate_structure(value)
    return value


def validate_structure(value: Mapping[str, Any]) -> None:
    """Validate closed schemas and all self-contained attempt equations."""

    expected_keys = {
        "schema_version",
        "artifact_id",
        "authority_scope",
        "staging",
        "repo_authority_locators",
        "capture_input_identities",
        "link_inventory_summary",
        "name_disambiguation",
        "document_candidates",
        "document_candidate_count",
        "unique_document_identity_count",
        "ordered_document_ids",
        "document_rows_sha256",
        "verified_document_ids",
        "verified_document_count",
        "failed_document_ids",
        "failed_document_count",
        "registration_status",
        "failure_disposition",
        "accepted_authority_registry",
        "integrity",
    }
    if set(value) != expected_keys:
        raise ValueError("registration-attempt top-level schema drift")
    if value["schema_version"] != SCHEMA_VERSION or value["artifact_id"] != ARTIFACT_ID:
        raise ValueError("registration-attempt identity drift")
    if value["authority_scope"] != "external_psid_questionnaire_and_codebook_bytes":
        raise ValueError("registration-attempt authority scope drift")
    if value["staging"] != {
        "staging_root_id": CAPTURE_ROOT_ID,
        "relative_capture_path": CAPTURE_RELATIVE_PATH,
        "absolute_paths_serialized": False,
        "repo_authority_locator_id": "psid_external_staging_law",
    }:
        raise ValueError("registration-attempt staging law drift")
    if value["repo_authority_locators"] != _repo_authority_locators():
        raise ValueError("registration-attempt repo authority locator drift")
    expected_capture_inputs = [
        {
            "capture_input_id": input_id,
            "locator": {
                "location_type": "full_file_byte_range",
                "filename": filename,
                "full_file_sha256": sha256,
                "size_bytes": size_bytes,
                "byte_start": 0,
                "byte_end": size_bytes,
                "range_sha256": sha256,
            },
        }
        for input_id, filename, size_bytes, sha256 in CAPTURE_INPUT_SPECS
    ]
    if value["capture_input_identities"] != expected_capture_inputs:
        raise ValueError("registration-attempt capture input identity drift")
    if value["link_inventory_summary"] != {
        "link_count": EXPECTED_LINK_COUNT,
        "unique_href_count": EXPECTED_UNIQUE_HREF_COUNT,
        "duplicate_link_count": EXPECTED_DUPLICATE_LINK_COUNT,
        "deduplication_rule": "stable_first_occurrence_by_exact_href",
        "ordered_unique_hrefs_sha256": EXPECTED_ORDERED_UNIQUE_HREFS_SHA256,
    }:
        raise ValueError("registration-attempt link inventory summary drift")
    if value["name_disambiguation"] != EXPECTED_DISAMBIGUATION_ROWS:
        raise ValueError("registration-attempt disambiguation domain drift")
    documents = value["document_candidates"]
    if not isinstance(documents, list) or len(documents) != EXPECTED_DOCUMENT_ROW_COUNT:
        raise ValueError("registration-attempt document domain drift")
    expected_document_keys = {
        "source_document_id",
        "document_identity_sha256",
        "digest_row_number",
        "unique_link_position",
        "first_link_position",
        "source_url",
        "source_link_text",
        "source_page_row",
        "digest_row_filename",
        "on_disk_filename",
        "expected_sha256",
        "expected_size_bytes",
        "availability",
        "observed_identity",
        "locator",
    }
    mapping_by_key = {
        (row["digest_row_filename"], row["sha256"]): row["on_disk_filename"]
        for row in EXPECTED_DISAMBIGUATION_ROWS
    }
    first_link_positions: list[int] = []
    for position, row in enumerate(documents, start=1):
        if not isinstance(row, dict) or set(row) != expected_document_keys:
            raise ValueError(f"registration-attempt document row {position} schema drift")
        expected_id = f"psid-corpus-document-{position:04d}"
        if (
            row["source_document_id"] != expected_id
            or row["digest_row_number"] != position
            or row["unique_link_position"] != position
        ):
            raise ValueError(f"{expected_id} positional identity drift")
        first_link_position = row["first_link_position"]
        if (
            not isinstance(first_link_position, int)
            or isinstance(first_link_position, bool)
            or not position <= first_link_position <= EXPECTED_LINK_COUNT
        ):
            raise ValueError(f"{expected_id} first-link position drift")
        first_link_positions.append(first_link_position)
        digest_name = row["digest_row_filename"]
        on_disk_name = row["on_disk_filename"]
        expected_sha256 = row["expected_sha256"]
        expected_size = row["expected_size_bytes"]
        if (
            not isinstance(digest_name, str)
            or not isinstance(on_disk_name, str)
            or Path(digest_name).name != digest_name
            or Path(on_disk_name).name != on_disk_name
            or digest_name in {".", ".."}
            or on_disk_name in {".", ".."}
            or _HEX64.fullmatch(expected_sha256) is None
            or not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size <= 0
        ):
            raise ValueError(f"{expected_id} source identity grammar drift")
        if on_disk_name != mapping_by_key.get(
            (digest_name, expected_sha256), digest_name
        ):
            raise ValueError(f"{expected_id} disambiguation projection drift")
        source_url = row["source_url"]
        if (
            not isinstance(source_url, str)
            or not source_url.startswith("https://psidonline.isr.umich.edu/")
            or not isinstance(row["source_link_text"], str)
            or not isinstance(row["source_page_row"], str)
        ):
            raise ValueError(f"{expected_id} link identity drift")
        identity_preimage = [
            position,
            source_url,
            digest_name,
            expected_sha256,
            expected_size,
        ]
        if row["document_identity_sha256"] != _sha256(
            canonical_json_bytes(identity_preimage)
        ):
            raise ValueError(f"{expected_id} document identity digest drift")
        availability = row["availability"]
        if availability not in {"verified", "identity_mismatch", "missing"}:
            raise ValueError(f"{expected_id} availability vocabulary drift")
        locator = row["locator"]
        observed = row["observed_identity"]
        if availability == "verified":
            expected_locator = {
                "location_type": "full_file_byte_range",
                "filename": on_disk_name,
                "full_file_sha256": expected_sha256,
                "size_bytes": expected_size,
                "byte_start": 0,
                "byte_end": expected_size,
                "range_sha256": expected_sha256,
            }
            if locator != expected_locator or observed != {
                "filename": on_disk_name,
                "sha256": expected_sha256,
                "size_bytes": expected_size,
            }:
                raise ValueError(f"{expected_id} verified locator drift")
        elif availability == "identity_mismatch":
            if (
                locator is not None
                or not isinstance(observed, dict)
                or set(observed) != {"filename", "sha256", "size_bytes"}
                or observed["filename"] != on_disk_name
                or not isinstance(observed["sha256"], str)
                or _HEX64.fullmatch(observed["sha256"]) is None
                or not isinstance(observed["size_bytes"], int)
                or isinstance(observed["size_bytes"], bool)
                or observed["size_bytes"] <= 0
                or (
                    observed["sha256"] == expected_sha256
                    and observed["size_bytes"] == expected_size
                )
            ):
                raise ValueError(f"{expected_id} mismatch identity drift")
        elif locator is not None or observed is not None:
            raise ValueError(f"{expected_id} missing-row identity drift")
    if first_link_positions != sorted(first_link_positions) or len(set(first_link_positions)) != len(first_link_positions):
        raise ValueError("registration-attempt first-link order drift")
    ids = [row["source_document_id"] for row in documents]
    if ids != value["ordered_document_ids"] or len(ids) != len(set(ids)):
        raise ValueError("registration-attempt document ID order drift")
    if value["document_candidate_count"] != EXPECTED_DOCUMENT_ROW_COUNT:
        raise ValueError("registration-attempt document count drift")
    if (
        value["document_rows_sha256"] != EXPECTED_DOCUMENT_ROWS_SHA256
        or value["document_rows_sha256"] != _sha256(canonical_json_bytes(documents))
    ):
        raise ValueError("registration-attempt document rows digest drift")
    unique_identity_count = len(
        {(row["expected_sha256"], row["expected_size_bytes"]) for row in documents}
    )
    if (
        value["unique_document_identity_count"]
        != EXPECTED_UNIQUE_DOCUMENT_IDENTITY_COUNT
        or value["unique_document_identity_count"] != unique_identity_count
    ):
        raise ValueError("registration-attempt unique identity count drift")
    verified = [row["source_document_id"] for row in documents if row["availability"] == "verified"]
    failed = [row["source_document_id"] for row in documents if row["availability"] != "verified"]
    if verified != value["verified_document_ids"] or failed != value["failed_document_ids"]:
        raise ValueError("registration-attempt availability projection drift")
    if (
        value["verified_document_count"] != 440
        or value["verified_document_count"] != len(verified)
        or value["failed_document_count"] != 16
        or value["failed_document_count"] != len(failed)
        or failed != EXPECTED_FAILED_DOCUMENT_IDS
    ):
        raise ValueError("registration-attempt availability count drift")
    expected_status = "pass" if not failed else "fail"
    if value["registration_status"] != "fail" or expected_status != "fail":
        raise ValueError("registration-attempt status drift")
    if value["accepted_authority_registry"] is not None:
        raise ValueError("registration attempt emitted an accepted authority")
    if value["failure_disposition"] != FAILURE_DISPOSITION:
        raise ValueError("registration-attempt failure disposition drift")
    integrity = value["integrity"]
    if set(integrity) != {
        "canonicalization",
        "content_sha256",
        "structural_status",
        "reproduced_from_available_capture_bytes",
    }:
        raise ValueError("registration-attempt integrity schema drift")
    if (
        integrity["canonicalization"] != CANONICALIZATION
        or integrity["structural_status"] != "pass"
        or integrity["reproduced_from_available_capture_bytes"] is not True
        or integrity["content_sha256"] != EXPECTED_CONTENT_SHA256
        or integrity["content_sha256"] != _content_sha256(value)
    ):
        raise ValueError("registration-attempt integrity failure")
    rendered = canonical_json_bytes(value)
    if b"/Users/" in rendered or b"maxghenis" in rendered:
        raise ValueError("registration-attempt serialized an absolute host path")


def validate_registration_attempt(
    value: Mapping[str, Any], capture_root: Path = DEFAULT_CAPTURE_ROOT
) -> None:
    """Re-resolve every row from the frozen ceremony inputs and source bytes."""

    validate_structure(value)
    if value != build_registration_attempt(capture_root):
        raise ValueError("registration attempt does not reproduce from capture bytes")


def render(capture_root: Path = DEFAULT_CAPTURE_ROOT) -> bytes:
    return canonical_json_bytes(build_registration_attempt(capture_root))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render(args.capture_root)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != rendered:
            raise SystemExit(f"artifact drift: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
