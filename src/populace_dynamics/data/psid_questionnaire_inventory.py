"""Source-only audit of the staged PSID family dictionaries.

This module deliberately does not import the family reader, a correction
crosswalk, or any adjudication registry.  Its only inputs are the staged
family source files.  The ``.do`` and ``.sps`` dictionaries establish the
physical layout, while the raw ``.txt`` files are byte-pinned without being
parsed.  That separation enforces the independent-domain rule in
covered-earnings design section 4.2.

The staged dictionaries pin physical fields, short labels, and fixed-width
coordinates.  The 2021 and 2023 format pairs also provide field-bound code
maps, including positive DK, NA/refused, and inapplicable-code evidence.
They still do not contain enough evidence to ratify
``psid_questionnaire_slot_specs.v1``: 41 waves have no value maps, no main
SPSS setup has a formal ``MISSING VALUES`` declaration, and the files do not
establish complete questionnaire slot hierarchies, full descriptions,
timing, or exhaustive absence proofs.  The public builder therefore emits a
reproducible registration-required audit and refuses to manufacture either
ratified artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
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
FORMAT_MAP_IDENTITIES: tuple[tuple[int, int, int, int, str], ...] = (
    (
        2021,
        3_212,
        25_263,
        2_460,
        "39a29fa289ddd41852214e30bb7d77e41534c41efd21a75a68633282e808cfd2",
    ),
    (
        2023,
        3_078,
        23_374,
        2_327,
        "d58883d52bb8a76b64206ae36093563e6cbb9d6c542de2bb3189f0e4b70cc2f2",
    ),
)
FORMAT_MAP_WAVES: tuple[int, ...] = tuple(
    row[0] for row in FORMAT_MAP_IDENTITIES
)
FORMAT_SOURCE_IDENTITIES: tuple[
    tuple[int, str, str, str, int, str, str], ...
] = (
    (
        2021,
        "psid-family-2021-stata_value_labels",
        "stata_value_labels",
        "family/2021/FAM2021ER_formats.do",
        1_531_909,
        "c227518baa7ec94ed042aadfea42c4ed5bdd1b89df11c4bf4d578f4a4dd60e38",
        "windows-1252",
    ),
    (
        2021,
        "psid-family-2021-spss_value_labels",
        "spss_value_labels",
        "family/2021/FAM2021ER_formats.sps",
        1_151_352,
        "863f151a4cab1282060aa3bfe4f6648bbbc1822e6f739bcfd502ff13b40a952c",
        "windows-1252",
    ),
    (
        2023,
        "psid-family-2023-stata_value_labels",
        "stata_value_labels",
        "family/2023/FAM2023ER_formats.do",
        1_427_122,
        "7ecaa861c7e8afd80e579a0d04c9a8040ffeae42ad4a174acd8a8a0e558171eb",
        "windows-1252",
    ),
    (
        2023,
        "psid-family-2023-spss_value_labels",
        "spss_value_labels",
        "family/2023/FAM2023ER_formats.sps",
        1_084_066,
        "89e4f2be4bea66fe83e0f11682bdcfab2590c01310bd697833846377d64a59f2",
        "windows-1252",
    ),
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
FIELD_BOUND_FORMAT_MAP_COLUMNS: tuple[str, ...] = (
    "raw_field_id",
    "stata_value_label_id",
    "code_label_rows",
)
CODE_LABEL_COLUMNS: tuple[str, ...] = (
    "raw_code",
    "exact_stata_value_label",
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


def _format_pair_for_wave(
    directory: Path,
    wave: int,
) -> tuple[Path, Path] | None:
    pair = _optional_format_pair(directory)
    if wave in FORMAT_MAP_WAVES and pair is None:
        raise DictionaryDriftError(
            f"{directory}: wave {wave} is missing its required field-bound "
            "format pair"
        )
    if wave not in FORMAT_MAP_WAVES and pair is not None:
        raise DictionaryDriftError(
            f"{directory}: unexpected field-bound format pair for wave {wave}"
        )
    return pair


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
    *,
    encoding: str = "windows-1252",
) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "document_id": f"psid-family-{wave}-{dictionary_role}",
        "interview_wave": wave,
        "dictionary_role": dictionary_role,
        "path": path.relative_to(data_root).as_posix(),
        "size_bytes": len(content),
        "sha256": sha256_bytes(content),
        "encoding": encoding,
    }


def _stata_statements(text: str) -> list[str]:
    statements: list[str] = []
    continued: list[str] = []
    for source_line in text.splitlines():
        line = source_line.strip()
        if not line and not continued:
            continue
        if line.endswith("///"):
            continued.append(line[:-3].rstrip())
            continue
        continued.append(line)
        statement = " ".join(part for part in continued if part)
        if statement:
            statements.append(statement)
        continued = []
    if continued:
        raise DictionaryDriftError("unterminated Stata line continuation")
    return statements


def _expand_stata_char_macros(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        code = int(match.group(1))
        if not 0 <= code <= 255:
            raise DictionaryDriftError(
                f"unsupported Stata char() code: {code}"
            )
        return bytes([code]).decode("cp1252")

    expanded = re.sub(r"`=char\((\d+)\)'", replace, value)
    if re.search(r"`[^']*'", expanded):
        raise DictionaryDriftError(
            f"unsupported Stata macro in value label: {expanded!r}"
        )
    return expanded


def _parse_stata_code_label_rows(
    body: str,
    *,
    loop_variable: str | None = None,
    loop_value: int | None = None,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    position = 0
    while position < len(body):
        while position < len(body) and body[position].isspace():
            position += 1
        if position == len(body):
            break
        integer_match = re.match(r"[+-]?\d+", body[position:])
        if integer_match is not None:
            raw_code = int(integer_match.group())
            position += len(integer_match.group())
        else:
            macro_match = re.match(
                r"`([A-Za-z][A-Za-z0-9_]*)'", body[position:]
            )
            if macro_match is None:
                raise DictionaryDriftError(
                    f"unparsed Stata value-label code near {body[position:]!r}"
                )
            if (
                loop_variable is None
                or macro_match.group(1) != loop_variable
                or loop_value is None
            ):
                raise DictionaryDriftError(
                    f"unbound Stata loop macro: {macro_match.group()!r}"
                )
            raw_code = loop_value
            position += len(macro_match.group())
        while position < len(body) and body[position].isspace():
            position += 1
        if body.startswith('`"', position):
            label_start = position + 2
            label_end = body.find("\"'", label_start)
            if label_end < 0:
                raise DictionaryDriftError(
                    "unterminated Stata compound-quoted value label"
                )
            label = body[label_start:label_end]
            position = label_end + 2
        elif position < len(body) and body[position] == '"':
            label_start = position + 1
            label_end = body.find('"', label_start)
            if label_end < 0:
                raise DictionaryDriftError("unterminated Stata value label")
            label = body[label_start:label_end]
            position = label_end + 1
        else:
            raise DictionaryDriftError(
                f"unparsed Stata value-label text near {body[position:]!r}"
            )
        rows.append([raw_code, _expand_stata_char_macros(label)])
    if not rows:
        raise DictionaryDriftError("empty Stata value-label definition")
    return rows


def _parse_stata_label_definition(
    statement: str,
    *,
    loop_variable: str | None = None,
    loop_value: int | None = None,
) -> tuple[str, list[list[Any]]]:
    match = re.fullmatch(
        r"label\s+define\s+([A-Za-z][A-Za-z0-9_]*)\s+"
        r"(?P<body>.*?)(?:\s*,\s*modify)?",
        statement,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise DictionaryDriftError(
            f"unparsed Stata label definition: {statement!r}"
        )
    return (
        match.group(1),
        _parse_stata_code_label_rows(
            match.group("body"),
            loop_variable=loop_variable,
            loop_value=loop_value,
        ),
    )


def _append_stata_label_rows(
    definitions: dict[str, list[list[Any]]],
    label_id: str,
    rows: Sequence[list[Any]],
) -> None:
    defined = definitions.setdefault(label_id, [])
    existing_codes = {row[0] for row in defined}
    incoming_codes = [row[0] for row in rows]
    if len(incoming_codes) != len(set(incoming_codes)):
        raise DictionaryDriftError(
            f"duplicate Stata codes in value-label definition {label_id}"
        )
    duplicates = existing_codes.intersection(incoming_codes)
    if duplicates:
        raise DictionaryDriftError(
            f"duplicate Stata value-label codes for {label_id}: "
            f"{sorted(duplicates)}"
        )
    defined.extend(rows)


def _parse_stata_format_maps(text: str) -> list[list[Any]]:
    statements = _stata_statements(text)
    definitions: dict[str, list[list[Any]]] = {}
    bindings: list[tuple[str, str]] = []
    bound_fields: set[str] = set()
    bound_label_ids: set[str] = set()
    index = 0
    while index < len(statements):
        statement = statements[index]
        loop_match = re.fullmatch(
            r"forvalues\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*"
            r"([+-]?\d+)\s*/\s*([+-]?\d+)\s*\{",
            statement,
            flags=re.IGNORECASE,
        )
        if loop_match is not None:
            if index + 2 >= len(statements) or statements[index + 2] != "}":
                raise DictionaryDriftError(
                    f"unclosed or multi-command Stata forvalues: {statement!r}"
                )
            variable, first_text, last_text = loop_match.groups()
            first = int(first_text)
            last = int(last_text)
            if first > last:
                raise DictionaryDriftError(
                    f"descending Stata forvalues range: {statement!r}"
                )
            for value in range(first, last + 1):
                label_id, rows = _parse_stata_label_definition(
                    statements[index + 1],
                    loop_variable=variable,
                    loop_value=value,
                )
                _append_stata_label_rows(definitions, label_id, rows)
            index += 3
            continue
        if re.match(r"label\s+define\b", statement, flags=re.IGNORECASE):
            label_id, rows = _parse_stata_label_definition(statement)
            _append_stata_label_rows(definitions, label_id, rows)
            index += 1
            continue
        binding_match = re.fullmatch(
            r"label\s+values\s+([A-Za-z][A-Za-z0-9_]*)\s+"
            r"([A-Za-z][A-Za-z0-9_]*)",
            statement,
            flags=re.IGNORECASE,
        )
        if binding_match is not None:
            field_id, label_id = binding_match.groups()
            if field_id in bound_fields:
                raise DictionaryDriftError(
                    f"duplicate Stata value-label binding for {field_id}"
                )
            if label_id in bound_label_ids:
                raise DictionaryDriftError(
                    f"Stata value-label definition bound twice: {label_id}"
                )
            bound_fields.add(field_id)
            bound_label_ids.add(label_id)
            bindings.append((field_id, label_id))
            index += 1
            continue
        raise DictionaryDriftError(
            f"unparsed Stata format statement: {statement!r}"
        )

    definition_ids = set(definitions)
    if definition_ids != bound_label_ids:
        raise DictionaryDriftError(
            "Stata value-label definitions and bindings disagree; "
            f"unbound={sorted(definition_ids - bound_label_ids)[:4]}, "
            f"undefined={sorted(bound_label_ids - definition_ids)[:4]}"
        )
    return [
        [field_id, label_id, definitions[label_id]]
        for field_id, label_id in bindings
    ]


def _parse_spss_format_domains(
    text: str,
) -> tuple[dict[str, tuple[int, ...]], int]:
    block_pattern = re.compile(
        r"^\s*VALUE\s+LABELS\s*$" r"(?P<body>.*?)" r"^\s*\.\s*$",
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    blocks = list(block_pattern.finditer(text))
    remainder = block_pattern.sub("", text)
    if remainder.strip().upper() not in {"", "EXECUTE."}:
        raise DictionaryDriftError(
            f"unparsed SPSS format content: {remainder.strip()[:80]!r}"
        )
    domains: dict[str, tuple[int, ...]] = {}
    truncation_count = 0
    for block in blocks:
        lines = [
            line.strip()
            for line in block.group("body").splitlines()
            if line.strip()
        ]
        if not lines:
            raise DictionaryDriftError("empty SPSS value-label block")
        header_match = re.fullmatch(
            r"([A-Za-z][A-Za-z0-9_]*)"
            r"(?:\s+/\*Truncated value label ends with \.\.\.\*/)?",
            lines[0],
            flags=re.IGNORECASE,
        )
        if header_match is None:
            raise DictionaryDriftError(
                f"unparsed SPSS value-label header: {lines[0]!r}"
            )
        field_id = header_match.group(1)
        if field_id in domains:
            raise DictionaryDriftError(
                f"duplicate SPSS value-label map for {field_id}"
            )
        if "/*" in lines[0]:
            truncation_count += 1
        codes: list[int] = []
        for line in lines[1:]:
            row_match = re.fullmatch(r"([+-]?\d+)\s+'(.*)'", line)
            if row_match is None:
                raise DictionaryDriftError(
                    f"unparsed SPSS value-label row: {line!r}"
                )
            codes.append(int(row_match.group(1)))
        if not codes or len(codes) != len(set(codes)):
            raise DictionaryDriftError(
                f"empty or duplicate SPSS code domain for {field_id}"
            )
        domains[field_id] = tuple(codes)
    if not domains:
        raise DictionaryDriftError("no SPSS field-bound value-label maps")
    return domains, truncation_count


def _format_evidence(
    stata_path: Path,
    spss_path: Path,
    physical_field_names: Iterable[str],
) -> dict[str, Any]:
    stata_maps = _parse_stata_format_maps(
        stata_path.read_bytes().decode("cp1252")
    )
    spss_domains, truncation_count = _parse_spss_format_domains(
        spss_path.read_bytes().decode("cp1252")
    )
    stata_domains = {
        row[0]: tuple(code_row[0] for code_row in row[2]) for row in stata_maps
    }
    if set(stata_domains) != set(spss_domains):
        raise DictionaryDriftError(
            "Stata and SPSS field-bound value-label domains disagree"
        )
    for field_id, stata_codes in stata_domains.items():
        if set(stata_codes) != set(spss_domains[field_id]):
            raise DictionaryDriftError(
                f"Stata and SPSS code domains disagree for {field_id}"
            )
    unknown_fields = set(stata_domains).difference(physical_field_names)
    if unknown_fields:
        raise DictionaryDriftError(
            "format maps bind fields outside the physical layout: "
            f"{sorted(unknown_fields)[:4]}"
        )
    row_count = sum(len(row[2]) for row in stata_maps)
    return {
        "field_bound_format_map_columns": list(FIELD_BOUND_FORMAT_MAP_COLUMNS),
        "code_label_columns": list(CODE_LABEL_COLUMNS),
        "field_bound_format_maps": stata_maps,
        "field_bound_format_maps_sha256": sha256_bytes(
            canonical_json_bytes(stata_maps)
        ),
        "value_label_map_count": len(stata_maps),
        "value_label_row_count": row_count,
        "explicit_truncation_count": truncation_count,
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
                "V5289 and V5788 do not prove wages_only.  The 2021/2023 "
                "format maps provide later positive evidence but not the "
                "required pre-modern maps."
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
                "waves contain multiple plausible mapped concepts; neither "
                "the setup labels nor the later maps establish a stable "
                "earlier mapping."
            ),
        },
    ]


def _target_artifacts() -> list[dict[str, str]]:
    return [
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
    ]


def _inventory_ratification_abort(
    registration_items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
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
    }


def build_registration_required_audit(
    data_root: Path | None = None,
) -> dict[str, Any]:
    """Build the source-only physical-field audit.

    Raw microdata are byte-pinned for source identity but never parsed.  All
    physical-field metadata are derived independently from the dictionaries.
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
        raw_path = _single_file(directory, ".txt", formats=False)
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
        raw_document = _document_row(
            raw_path,
            root,
            wave,
            "raw_fixed_width",
            encoding="binary",
        )
        manifest.extend([do_document, sps_document, raw_document])
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
            raw_document["document_id"],
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

        format_pair = _format_pair_for_wave(directory, wave)
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
            evidence = _format_evidence(
                format_do_path,
                format_sps_path,
                (name for name, *_ in rows),
            )
            evidence["interview_wave"] = wave
            evidence["source_document_ids"] = [
                format_do_document["document_id"],
                format_sps_document["document_id"],
            ]
            format_file_evidence.append(evidence)

    registration_items = _registration_required_items()
    dictionary_manifest = [
        row for row in manifest if row["dictionary_role"] != "raw_fixed_width"
    ]
    raw_manifest = [
        row for row in manifest if row["dictionary_role"] == "raw_fixed_width"
    ]
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "target_artifacts": _target_artifacts(),
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
            "source_authority_file_count": len(manifest),
            "source_authority_total_size_bytes": sum(
                row["size_bytes"] for row in manifest
            ),
            "dictionary_file_count": len(dictionary_manifest),
            "dictionary_total_size_bytes": sum(
                row["size_bytes"] for row in dictionary_manifest
            ),
            "raw_fixed_width_file_count": len(raw_manifest),
            "raw_fixed_width_total_size_bytes": sum(
                row["size_bytes"] for row in raw_manifest
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
        "inventory_ratification_abort": _inventory_ratification_abort(
            registration_items
        ),
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


def _validate_format_file_evidence(
    evidence: Mapping[str, Any],
    physical_fields_by_wave: Mapping[int, set[str]],
) -> None:
    if evidence.get("field_bound_format_map_columns") != list(
        FIELD_BOUND_FORMAT_MAP_COLUMNS
    ):
        raise DictionaryDriftError("field-bound format-map columns drifted")
    if evidence.get("code_label_columns") != list(CODE_LABEL_COLUMNS):
        raise DictionaryDriftError("format code-label columns drifted")
    maps = evidence.get("field_bound_format_maps")
    if not isinstance(maps, list):
        raise DictionaryDriftError("field-bound format maps are not a list")
    field_ids: list[str] = []
    label_ids: list[str] = []
    code_label_row_count = 0
    for field_map in maps:
        if not isinstance(field_map, list) or len(field_map) != 3:
            raise DictionaryDriftError("field-bound format-map row drifted")
        field_id, label_id, code_rows = field_map
        if not isinstance(field_id, str) or not isinstance(label_id, str):
            raise DictionaryDriftError(
                "field-bound format-map identity is not textual"
            )
        if not isinstance(code_rows, list) or not code_rows:
            raise DictionaryDriftError(
                f"empty format code-label rows for {field_id}"
            )
        codes: list[int] = []
        for code_row in code_rows:
            if not isinstance(code_row, list) or len(code_row) != 2:
                raise DictionaryDriftError(
                    f"format code-label row drifted for {field_id}"
                )
            raw_code, label = code_row
            if (
                isinstance(raw_code, bool)
                or not isinstance(raw_code, int)
                or not isinstance(label, str)
            ):
                raise DictionaryDriftError(
                    f"invalid format code-label types for {field_id}"
                )
            codes.append(raw_code)
        if len(codes) != len(set(codes)):
            raise DictionaryDriftError(
                f"duplicate format-map raw code for {field_id}"
            )
        code_label_row_count += len(code_rows)
        field_ids.append(field_id)
        label_ids.append(label_id)
    if len(field_ids) != len(set(field_ids)):
        raise DictionaryDriftError("duplicate field-bound format-map field")
    if len(label_ids) != len(set(label_ids)):
        raise DictionaryDriftError("duplicate field-bound Stata label ID")
    if evidence.get("value_label_map_count") != len(maps):
        raise DictionaryDriftError("field-bound format-map count mismatch")
    if evidence.get("value_label_row_count") != code_label_row_count:
        raise DictionaryDriftError("format code-label row count mismatch")
    if evidence.get("field_bound_format_maps_sha256") != sha256_bytes(
        canonical_json_bytes(maps)
    ):
        raise DictionaryDriftError("field-bound format-map hash mismatch")
    wave = evidence.get("interview_wave")
    if wave not in physical_fields_by_wave:
        raise DictionaryDriftError(
            "format-map wave is outside physical domain"
        )
    unknown_fields = set(field_ids).difference(physical_fields_by_wave[wave])
    if unknown_fields:
        raise DictionaryDriftError(
            "format maps bind fields outside the artifact physical layout"
        )


def _validate_physical_field_integrity(
    artifact: Mapping[str, Any],
) -> list[list[Any]]:
    rows = artifact["physical_fields"]
    if artifact["physical_field_count"] != len(rows):
        raise DictionaryDriftError("physical field count mismatch")
    keys = [row[0] for row in rows]
    if len(keys) != len(set(keys)):
        raise DictionaryDriftError("duplicate physical field key")
    if artifact["physical_field_keyset_sha256"] != _keyset_hash(keys):
        raise DictionaryDriftError("physical field keyset hash mismatch")
    return rows


def _validate_content_integrity(artifact: Mapping[str, Any]) -> None:
    expected_content_sha = artifact["integrity"]["content_sha256"]
    candidate = json.loads(json.dumps(artifact))
    candidate["integrity"]["content_sha256"] = _ZERO_SHA256
    if expected_content_sha != sha256_bytes(canonical_json_bytes(candidate)):
        raise DictionaryDriftError("artifact content hash mismatch")


def _validate_fail_closed_status(artifact: Mapping[str, Any]) -> None:
    registration_items = _registration_required_items()
    if artifact.get("target_artifacts") != _target_artifacts():
        raise DictionaryDriftError(
            "registered audit target-artifact status drifted"
        )
    if artifact.get("registration_required_items") != registration_items:
        raise DictionaryDriftError(
            "registered audit registration-required findings drifted"
        )
    if artifact.get(
        "inventory_ratification_abort"
    ) != _inventory_ratification_abort(registration_items):
        raise DictionaryDriftError(
            "registered audit fail-closed disposition drifted"
        )
    integrity = artifact.get("integrity")
    if not isinstance(integrity, Mapping):
        raise DictionaryDriftError("registered audit integrity is not a map")
    if integrity.get("reproduced_from_source_bytes") is not False:
        raise DictionaryDriftError(
            "registered audit falsely claims source-byte reproduction"
        )


def validate_integrity(artifact: dict[str, Any]) -> None:
    """Validate every frozen identity and positive-evidence commitment."""

    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise DictionaryDriftError("registered audit schema version drifted")
    if artifact.get("artifact_id") != ARTIFACT_ID:
        raise DictionaryDriftError("registered audit artifact ID drifted")
    _validate_fail_closed_status(artifact)
    rows = _validate_physical_field_integrity(artifact)
    summary = artifact.get("evidence_summary")
    if not isinstance(summary, Mapping):
        raise DictionaryDriftError(
            "registered audit lacks its evidence summary"
        )
    columns = artifact["physical_field_columns"]
    wave_index = columns.index("interview_wave")
    field_index = columns.index("raw_field_id")
    physical_fields_by_wave: dict[int, set[str]] = {}
    for row in rows:
        physical_fields_by_wave.setdefault(row[wave_index], set()).add(
            row[field_index]
        )
    format_evidence = summary.get("format_file_evidence", [])
    if not isinstance(format_evidence, list):
        raise DictionaryDriftError("format file evidence is not a list")
    format_waves = [row.get("interview_wave") for row in format_evidence]
    if len(format_waves) != len(set(format_waves)):
        raise DictionaryDriftError("duplicate format evidence wave")
    if format_waves != list(FORMAT_MAP_WAVES):
        raise DictionaryDriftError(
            "registered field-bound format evidence waves drifted"
        )
    for evidence in format_evidence:
        if not isinstance(evidence, Mapping):
            raise DictionaryDriftError("format evidence row is not a map")
        _validate_format_file_evidence(
            evidence,
            physical_fields_by_wave,
        )
    expected_by_wave = {row[0]: row[1:] for row in FORMAT_MAP_IDENTITIES}
    manifest = artifact.get("source_authority_manifest")
    if not isinstance(manifest, list):
        raise DictionaryDriftError(
            "registered audit source manifest is not a list"
        )
    if not all(isinstance(row, Mapping) for row in manifest):
        raise DictionaryDriftError(
            "source-authority manifest row is not a map"
        )
    manifest_by_id = {row.get("document_id"): row for row in manifest}
    manifest_ids = list(manifest_by_id)
    if len(manifest_by_id) != len(manifest):
        raise DictionaryDriftError("duplicate source-authority document ID")
    if not all(isinstance(document_id, str) for document_id in manifest_ids):
        raise DictionaryDriftError("invalid source-authority document ID")
    format_sources_by_wave: dict[int, list[dict[str, Any]]] = {}
    for (
        wave,
        document_id,
        source_role,
        path,
        size_bytes,
        sha256,
        encoding,
    ) in FORMAT_SOURCE_IDENTITIES:
        expected_source = {
            "document_id": document_id,
            "interview_wave": wave,
            "dictionary_role": source_role,
            "path": path,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "encoding": encoding,
        }
        if manifest_by_id.get(document_id) != expected_source:
            raise DictionaryDriftError(
                f"wave {wave}: frozen {source_role} source identity drifted"
            )
        format_sources_by_wave.setdefault(wave, []).append(expected_source)
    for evidence in format_evidence:
        wave = evidence["interview_wave"]
        expected_identity = expected_by_wave[wave]
        observed_identity = (
            evidence.get("value_label_map_count"),
            evidence.get("value_label_row_count"),
            evidence.get("explicit_truncation_count"),
            evidence.get("field_bound_format_maps_sha256"),
        )
        if observed_identity != expected_identity:
            raise DictionaryDriftError(
                f"wave {wave}: frozen field-bound format evidence "
                "identity drifted"
            )
        expected_source_ids = [
            source["document_id"] for source in format_sources_by_wave[wave]
        ]
        if evidence.get("source_document_ids") != expected_source_ids:
            raise DictionaryDriftError(
                f"wave {wave}: format evidence source identities drifted"
            )
        if not set(expected_source_ids).issubset(manifest_ids):
            raise DictionaryDriftError(
                f"wave {wave}: format evidence sources are absent "
                "from the authority manifest"
            )
    _validate_content_integrity(artifact)


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
