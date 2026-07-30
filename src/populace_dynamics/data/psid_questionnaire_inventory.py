"""Source-only audit of the staged PSID family dictionaries.

This module deliberately does not import the family reader, a correction
crosswalk, or any adjudication registry.  Its only inputs are the staged
``.do`` and ``.sps`` dictionary files.  That separation enforces the
independent-domain rule in covered-earnings design section 4.2.

The staged dictionaries pin physical fields, short labels, and fixed-width
coordinates.  They do not contain enough evidence to ratify
``psid_questionnaire_slot_specs.v1``: most waves have no value maps, no wave
declares missing-value tokens, and the files do not establish complete
questionnaire slot hierarchies, full descriptions, timing, or exhaustive
absence proofs.  The public builder therefore emits a reproducible
registration-required audit and refuses to manufacture either ratified
artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

SCHEMA_VERSION = (
    "psid_questionnaire_dictionary_inventory.registration_required.v1"
)
ARTIFACT_ID = SCHEMA_VERSION
SLOT_SPECS_ID = "psid_questionnaire_slot_specs.v1"
SOURCE_INVENTORY_ID = "psid_covered_earnings_source_field_inventory.v1"

INTERVIEW_WAVES: tuple[int, ...] = (
    *range(1968, 1998),
    *range(1999, 2024, 2),
)
ROLES: tuple[str, ...] = (
    "head_or_reference_person",
    "spouse_or_partner",
)
FIELD_PURPOSES: tuple[str, ...] = (
    "interview_and_role_attachment",
    "amount",
    "reporting_unit",
    "month_or_exposure",
    "assignment",
    "employee_self_or_mixed",
    "incorporation",
    "government_level",
    "industry",
    "occupation",
    "enrollment",
    "job_identifier",
    "state_of_residence",
    "section_218_group",
    "section_218_position",
    "public_retirement_system_participation",
    "federal_retirement_system",
    "federal_service",
    "railroad_covered_employer",
    "railroad_covered_service",
    "ministerial_service",
    "clergy_remuneration",
    "church_employee_service",
    "religious_order_service",
    "clergy_or_religious_exemption",
    "domestic_service",
    "agricultural_service",
    "election_work",
    "family_service",
    "casual_service",
    "foreign_government_service",
    "international_organization_service",
    "nonresident_alien_status",
    "employer_school_nexus",
    "statutory_student_service",
)

PHYSICAL_FIELD_COLUMNS: tuple[str, ...] = (
    "source_field_key",
    "interview_wave",
    "earnings_reference_year",
    "raw_field_id",
    "start",
    "end",
    "raw_width",
    "spss_numeric_format",
    "exact_short_label",
    "source_document_ids",
)

_LAYOUT_FIELD_RE = re.compile(
    r"(?:\b(?:byte|int|long|float|double)\s+)?"
    r"([A-Za-z][A-Za-z0-9_]*)\s+(\d+)\s*-\s*(\d+)"
)
_SPSS_FORMAT_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9_]*)\s+\(([A-Za-z]\d+(?:\.\d+)?)\)"
)
_ZERO_SHA256 = "0" * 64


class DictionaryDriftError(ValueError):
    """Raised when paired dictionary files disagree or are ambiguous."""


class RegistrationRequiredError(RuntimeError):
    """Raised when code requests an artifact the sources cannot ratify."""

    def __init__(self, target_artifact_id: str, item_ids: Sequence[str]):
        self.target_artifact_id = target_artifact_id
        self.item_ids = tuple(item_ids)
        joined = ", ".join(self.item_ids)
        super().__init__(
            f"{target_artifact_id} ratification aborted; "
            f"registration_required: {joined}"
        )


def default_psid_root() -> Path:
    """Return the repository-convention PSID staging root."""

    return Path("~/PolicyEngine/psid-data").expanduser()


def canonical_json_bytes(value: Any) -> bytes:
    """Return the artifact's deterministic JSON encoding."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(value).hexdigest()


def _normalise_label(value: str) -> str:
    return " ".join(value.split())


def _single_file(
    directory: Path,
    suffix: str,
    *,
    formats: bool,
) -> Path:
    candidates = sorted(directory.glob(f"*{suffix}"))
    candidates = [
        path
        for path in candidates
        if path.stem.lower().endswith("_formats") is formats
    ]
    if len(candidates) != 1:
        kind = "format" if formats else "main"
        raise DictionaryDriftError(
            f"{directory}: expected exactly one {kind} {suffix} file, "
            f"found {[path.name for path in candidates]}"
        )
    return candidates[0]


def _optional_format_pair(directory: Path) -> tuple[Path, Path] | None:
    do_files = sorted(
        path
        for path in directory.glob("*.do")
        if path.stem.lower().endswith("_formats")
    )
    sps_files = sorted(
        path
        for path in directory.glob("*.sps")
        if path.stem.lower().endswith("_formats")
    )
    if not do_files and not sps_files:
        return None
    if len(do_files) != 1 or len(sps_files) != 1:
        raise DictionaryDriftError(
            f"{directory}: format dictionaries must be an unambiguous "
            f".do/.sps pair; found do={len(do_files)}, sps={len(sps_files)}"
        )
    return do_files[0], sps_files[0]


def _extract_statement(
    text: str,
    opening: str,
    *,
    terminator: str = r"^\s*\.\s*$",
) -> str:
    match = re.search(
        opening + r"(?P<body>.*?)" + terminator,
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise DictionaryDriftError(
            f"dictionary statement not found: {opening}"
        )
    return match.group("body")


def _parse_spss(text: str) -> tuple[list[tuple[str, int, int]], dict, dict]:
    layout_body = _extract_statement(
        text,
        r"^\s*DATA\s+LIST\b[^\n]*/",
    )
    layout = [
        (name, int(start), int(end))
        for name, start, end in _LAYOUT_FIELD_RE.findall(layout_body)
    ]
    label_body = _extract_statement(text, r"^\s*VARIABLE\s+LABELS\b")
    labels: dict[str, str] = {}
    for line in label_body.splitlines():
        match = re.fullmatch(
            r'\s*([A-Za-z][A-Za-z0-9_]*)\s+"(.*)"\s*',
            line,
        )
        if match is None:
            if line.strip():
                raise DictionaryDriftError(
                    f"unparsed SPSS variable-label line: {line!r}"
                )
            continue
        name, label = match.groups()
        if name in labels:
            raise DictionaryDriftError(f"duplicate SPSS label for {name}")
        labels[name] = label

    formats: dict[str, str] = {}
    for match in re.finditer(
        r"^\s*FORMATS\b(?P<body>.*?)^\s*\.\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ):
        for name, numeric_format in _SPSS_FORMAT_RE.findall(
            match.group("body")
        ):
            if name in formats:
                raise DictionaryDriftError(
                    f"duplicate SPSS numeric format for {name}"
                )
            formats[name] = numeric_format.upper()
    return layout, labels, formats


def _parse_stata(text: str) -> tuple[list[tuple[str, int, int]], dict]:
    layout_body = _extract_statement(
        text,
        r"^\s*infix\b",
        terminator=r"^\s*using\b.*?;\s*$",
    )
    layout = [
        (name, int(start), int(end))
        for name, start, end in _LAYOUT_FIELD_RE.findall(layout_body)
    ]
    labels: dict[str, str] = {}
    for match in re.finditer(
        r'^\s*label\s+variable\s+([A-Za-z][A-Za-z0-9_]*)\s+"(.*)"\s*;\s*$',
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        name, label = match.groups()
        if name in labels:
            raise DictionaryDriftError(f"duplicate Stata label for {name}")
        labels[name] = label
    return layout, labels


def _assert_layout_complete(
    wave: int,
    layout: Sequence[tuple[str, int, int]],
) -> None:
    if not layout:
        raise DictionaryDriftError(f"wave {wave}: empty physical layout")
    names = [row[0] for row in layout]
    if len(names) != len(set(names)):
        raise DictionaryDriftError(f"wave {wave}: duplicate field names")
    previous_end = 0
    for name, start, end in layout:
        if start != previous_end + 1:
            raise DictionaryDriftError(
                f"wave {wave}: layout gap/overlap before {name}: "
                f"{previous_end} -> {start}"
            )
        if end < start:
            raise DictionaryDriftError(
                f"wave {wave}: reversed coordinates for {name}"
            )
        previous_end = end


def _document_row(
    path: Path,
    data_root: Path,
    wave: int,
    dictionary_role: str,
) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "document_id": f"psid-family-{wave}-{dictionary_role}",
        "interview_wave": wave,
        "dictionary_role": dictionary_role,
        "path": path.relative_to(data_root).as_posix(),
        "size_bytes": len(content),
        "sha256": sha256_bytes(content),
        "encoding": "windows-1252",
    }


def _format_evidence(path: Path) -> dict[str, int]:
    text = path.read_bytes().decode("cp1252")
    blocks = re.findall(
        r"^\s*VALUE\s+LABELS\s*$" r"(?P<body>.*?)" r"^\s*\.\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    value_rows = sum(
        len(
            re.findall(
                r"^\s*-?\d+(?:\.\d+)?\s+'",
                body,
                flags=re.MULTILINE,
            )
        )
        for body in blocks
    )
    return {
        "value_label_map_count": len(blocks),
        "value_label_row_count": value_rows,
        "explicit_truncation_count": len(
            re.findall(
                r"/\*Truncated value label ends with \.\.\.\*/",
                text,
                flags=re.IGNORECASE,
            )
        ),
    }


def _compare_wave_dictionaries(
    wave: int,
    do_path: Path,
    sps_path: Path,
) -> tuple[list[tuple[str, int, int, str | None, str]], int, int]:
    do_text = do_path.read_bytes().decode("cp1252")
    sps_text = sps_path.read_bytes().decode("cp1252")
    do_layout, do_labels = _parse_stata(do_text)
    sps_layout, sps_labels, sps_formats = _parse_spss(sps_text)
    _assert_layout_complete(wave, do_layout)
    _assert_layout_complete(wave, sps_layout)
    if do_layout != sps_layout:
        raise DictionaryDriftError(
            f"wave {wave}: Stata and SPSS physical layouts disagree"
        )
    layout_names = [name for name, _, _ in sps_layout]
    if set(layout_names) != set(do_labels):
        raise DictionaryDriftError(
            f"wave {wave}: Stata label domain does not equal layout domain"
        )
    if set(layout_names) != set(sps_labels):
        raise DictionaryDriftError(
            f"wave {wave}: SPSS label domain does not equal layout domain"
        )
    unknown_formats = set(sps_formats).difference(layout_names)
    if unknown_formats:
        raise DictionaryDriftError(
            f"wave {wave}: formats for unknown fields "
            f"{sorted(unknown_formats)}"
        )

    rows: list[tuple[str, int, int, str | None, str]] = []
    for name, start, end in sps_layout:
        do_label = do_labels[name]
        sps_label = sps_labels[name]
        if _normalise_label(do_label) != _normalise_label(sps_label):
            raise DictionaryDriftError(
                f"wave {wave}: label disagreement for {name}: "
                f"{do_label!r} != {sps_label!r}"
            )
        rows.append(
            (
                name,
                start,
                end,
                sps_formats.get(name),
                sps_label,
            )
        )
    missing_declarations = len(
        re.findall(
            r"^\s*MISSING\s+VALUES\b",
            sps_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    value_label_declarations = len(
        re.findall(
            r"^\s*VALUE\s+LABELS\b",
            sps_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    return rows, missing_declarations, value_label_declarations


def _field_key(wave: int, name: str, start: int, end: int) -> str:
    digest = sha256_bytes(canonical_json_bytes([wave, name, start, end]))
    return f"psid-physical-field:{digest}"


def _keyset_hash(keys: Iterable[str]) -> str:
    return sha256_bytes(canonical_json_bytes(list(keys)))


def _registration_required_items() -> list[dict[str, Any]]:
    return [
        {
            "registration_item_id": "V-B5",
            "status": "registration_required",
            "required_evidence": (
                "Exact early-era, spouse, and secondary-job industry and "
                "occupation concepts and complete source code maps."
            ),
            "source_finding": (
                "Physical fields and short labels exist, but the setup "
                "dictionaries do not establish a common code system, full "
                "code maps, or complete slot attachment."
            ),
        },
        {
            "registration_item_id": "V-B6",
            "status": "registration_required",
            "required_evidence": (
                "Exact reference-year 1976/1977 spouse concepts plus "
                "pre-modern employee/self/mixed, incorporation, and "
                "government-level maps."
            ),
            "source_finding": (
                "V4379 is design-adjudicated mixed; the short labels for "
                "V5289 and V5788 do not prove wages_only, and the requested "
                "code maps are absent."
            ),
        },
        {
            "registration_item_id": "V-B8",
            "status": "registration_required",
            "required_evidence": (
                "A stable cross-era current-enrollment mapping and complete "
                "source code maps."
            ),
            "source_finding": (
                "Current-enrollment labels begin only in 2013 and later "
                "waves contain multiple plausible concepts; setup labels "
                "do not establish a stable earlier mapping."
            ),
        },
    ]


def build_registration_required_audit(
    data_root: Path | None = None,
) -> dict[str, Any]:
    """Build the source-only physical-field audit.

    No microdata file is opened or hashed.  The audit includes only the
    dictionary manifest and parsed dictionary metadata.
    """

    root = default_psid_root() if data_root is None else Path(data_root)
    family_root = root / "family"
    manifest: list[dict[str, Any]] = []
    physical_fields: list[list[Any]] = []
    format_file_evidence: list[dict[str, Any]] = []
    missing_declaration_count = 0
    main_value_label_count = 0
    explicit_numeric_format_count = 0
    wave_field_counts: list[list[int]] = []

    for wave in INTERVIEW_WAVES:
        directory = family_root / str(wave)
        if not directory.is_dir():
            raise DictionaryDriftError(
                f"missing staged family-wave directory: {directory}"
            )
        do_path = _single_file(directory, ".do", formats=False)
        sps_path = _single_file(directory, ".sps", formats=False)
        do_document = _document_row(
            do_path,
            root,
            wave,
            "stata_setup",
        )
        sps_document = _document_row(
            sps_path,
            root,
            wave,
            "spss_setup",
        )
        manifest.extend([do_document, sps_document])
        rows, missing_count, value_label_count = _compare_wave_dictionaries(
            wave,
            do_path,
            sps_path,
        )
        missing_declaration_count += missing_count
        main_value_label_count += value_label_count
        explicit_numeric_format_count += sum(
            numeric_format is not None for _, _, _, numeric_format, _ in rows
        )
        wave_field_counts.append([wave, len(rows)])
        source_ids = [
            do_document["document_id"],
            sps_document["document_id"],
        ]
        for name, start, end, numeric_format, label in rows:
            physical_fields.append(
                [
                    _field_key(wave, name, start, end),
                    wave,
                    wave - 1,
                    name,
                    start,
                    end,
                    end - start + 1,
                    numeric_format,
                    label,
                    source_ids,
                ]
            )

        format_pair = _optional_format_pair(directory)
        if format_pair is not None:
            format_do_path, format_sps_path = format_pair
            format_do_document = _document_row(
                format_do_path,
                root,
                wave,
                "stata_value_labels",
            )
            format_sps_document = _document_row(
                format_sps_path,
                root,
                wave,
                "spss_value_labels",
            )
            manifest.extend([format_do_document, format_sps_document])
            evidence = _format_evidence(format_sps_path)
            evidence["interview_wave"] = wave
            evidence["source_document_id"] = format_sps_document["document_id"]
            format_file_evidence.append(evidence)

    registration_items = _registration_required_items()
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "target_artifacts": [
            {
                "schema_version": SLOT_SPECS_ID,
                "artifact_id": SLOT_SPECS_ID,
                "status": "not_emitted_registration_required",
            },
            {
                "schema_version": "psid_source_field_inventory.v1",
                "artifact_id": SOURCE_INVENTORY_ID,
                "status": "not_emitted_registration_required",
            },
        ],
        "source_authority_manifest": manifest,
        "interview_waves": list(INTERVIEW_WAVES),
        "roles": list(ROLES),
        "field_purposes": list(FIELD_PURPOSES),
        "physical_field_columns": list(PHYSICAL_FIELD_COLUMNS),
        "physical_fields": physical_fields,
        "physical_field_count": len(physical_fields),
        "physical_field_keyset_sha256": _keyset_hash(
            row[0] for row in physical_fields
        ),
        "evidence_summary": {
            "dictionary_file_count": len(manifest),
            "dictionary_total_size_bytes": sum(
                row["size_bytes"] for row in manifest
            ),
            "wave_field_counts": wave_field_counts,
            "main_dictionary_field_count": len(physical_fields),
            "explicit_spss_numeric_format_count": (
                explicit_numeric_format_count
            ),
            "main_spss_missing_values_declaration_count": (
                missing_declaration_count
            ),
            "main_spss_value_label_statement_count": main_value_label_count,
            "format_file_evidence": format_file_evidence,
        },
        "inventory_ratification_abort": {
            "status": "registration_required",
            "failure_disposition": "abort_inventory_ratification",
            "missing_source_commitments": [
                "complete questionnaire job/component/context slot hierarchy",
                "full source descriptions for every present field",
                "complete raw-code maps with typed missing dispositions",
                "complete missing-token grammar for uncoded fields",
                "source-backed periodicity and information-date basis",
                "exhaustive questionnaire/layout absence proofs",
            ],
            "forbidden_fallbacks": [
                "derive the slot domain from the correction crosswalk",
                "infer structural_missing from a label keyword search",
                "treat a short label as a full source description",
                "infer a missing token or timing rule at runtime",
                "claim reproduced_from_source_bytes true",
            ],
            "registration_required_item_ids": [
                row["registration_item_id"] for row in registration_items
            ],
        },
        "registration_required_items": registration_items,
        "canonical_order": [
            "interview_wave",
            "physical_layout_coordinate",
        ],
        "integrity": {
            "canonicalization": (
                "UTF-8 JSON; keys sorted; no insignificant whitespace; "
                "content_sha256 computed with itself set to 64 zeroes"
            ),
            "content_sha256": _ZERO_SHA256,
            "builder_source_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "reproduced_from_source_bytes": False,
        },
    }
    artifact["integrity"]["content_sha256"] = sha256_bytes(
        canonical_json_bytes(artifact)
    )
    return artifact


def require_ratified_slot_specs(
    audit: dict[str, Any],
) -> None:
    """Fail closed instead of returning invented slot specifications."""

    item_ids = audit["inventory_ratification_abort"][
        "registration_required_item_ids"
    ]
    raise RegistrationRequiredError(SLOT_SPECS_ID, item_ids)


def require_ratified_source_inventory(
    audit: dict[str, Any],
) -> None:
    """Fail closed instead of returning an invented field inventory."""

    item_ids = audit["inventory_ratification_abort"][
        "registration_required_item_ids"
    ]
    raise RegistrationRequiredError(SOURCE_INVENTORY_ID, item_ids)


def validate_integrity(artifact: dict[str, Any]) -> None:
    """Validate the audit's count, keyset, and content commitments."""

    rows = artifact["physical_fields"]
    if artifact["physical_field_count"] != len(rows):
        raise DictionaryDriftError("physical field count mismatch")
    keys = [row[0] for row in rows]
    if len(keys) != len(set(keys)):
        raise DictionaryDriftError("duplicate physical field key")
    if artifact["physical_field_keyset_sha256"] != _keyset_hash(keys):
        raise DictionaryDriftError("physical field keyset hash mismatch")
    expected_content_sha = artifact["integrity"]["content_sha256"]
    candidate = json.loads(json.dumps(artifact))
    candidate["integrity"]["content_sha256"] = _ZERO_SHA256
    if expected_content_sha != sha256_bytes(canonical_json_bytes(candidate)):
        raise DictionaryDriftError("artifact content hash mismatch")


def render_artifact(artifact: dict[str, Any]) -> bytes:
    """Render the canonical committed file, including one trailing newline."""

    validate_integrity(artifact)
    return canonical_json_bytes(artifact) + b"\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=default_psid_root(),
        help="PSID staging root (default: ~/PolicyEngine/psid-data)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/external/"
            "psid_questionnaire_dictionary_inventory_"
            "registration_required_v1.json"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare generated bytes with --output instead of writing",
    )
    args = parser.parse_args(argv)
    rendered = render_artifact(
        build_registration_required_audit(args.data_root)
    )
    if args.check:
        if not args.output.is_file():
            raise SystemExit(f"missing committed artifact: {args.output}")
        if args.output.read_bytes() != rendered:
            raise SystemExit(
                f"committed artifact differs from source build: {args.output}"
            )
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
