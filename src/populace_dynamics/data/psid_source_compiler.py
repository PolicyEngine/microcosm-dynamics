"""Source-only PSID fixed-width numeric grammar compiler.

This module implements the revision-9 ``dictionary_codebook_fixed_width_``
``source_derivation_v3`` interface.  It deliberately imports no PSID model
reader, correction crosswalk, candidate registry, or configuration module.
The compiler operates on authenticated source bytes and source-derived rows.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np

INTERFACE_VERSION = "dictionary_codebook_fixed_width_source_derivation_v3"
ENTRY_POINTS = (
    "extract_dictionary_layout_rows",
    "frame_fixed_width_records",
    "extract_codebook_rows",
    "derive_source_numeric_grammar",
)

T_PLUS = (
    "compiled_source_numeric_grammar",
    "compiled_source_numeric_grammar_padding_underdetermined_exact_replay",
    "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_exact_replay",
    "compiled_source_numeric_grammar_partial_range_exact_replay",
    "value_code_domain_no_numeric_grammar",
    "value_code_range_physical_rendering_unestablished",
    "nonnumeric_source_field_outside_numeric_grammar",
)
T_MINUS = (
    "conflicting_source_numeric_format",
    "unsupported_source_numeric_format",
    "incomplete_source_numeric_authority",
)
TERMINAL_ORDER = T_PLUS + T_MINUS

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()

EVIDENCE_SPECS = (
    (
        "data/external/psid_codebook_field_evidence/"
        "wave1968_ry1968_1974_early_totals_v1.json",
        3_868,
        4_628_883,
        "52c22edacb8d492348479c609da6ce5c0f73285881e0768c25470bd95864fc48",
    ),
    (
        "data/external/psid_codebook_field_evidence/"
        "ry1975_1977_spouse_concept_seam_v1.json",
        1_838,
        2_203_624,
        "0122369d2f8fd6cc8d4e748cf1e93fa3b21ce1c695c9e4bf65338cd30ea13e87",
    ),
    (
        "data/external/psid_codebook_field_evidence/"
        "ry1978_1992_pre_er_totals_v1.json",
        15_745,
        21_115_064,
        "109d7ecb4dd933fdcd2efaf572d9bbb8378bb8b054badccda1ac52c049afcedf",
    ),
    (
        "data/external/psid_codebook_field_evidence/"
        "ry1993_2001_er_transition_v1.json",
        15_983,
        19_201_179,
        "549508cb31a26a81643339f9cda0824a8f44c9ffc5bac300d7647c34ba78c892",
    ),
    (
        "data/external/psid_codebook_field_evidence/"
        "ry2002_2014_modern_bc_de_v1.json",
        33_154,
        45_941_875,
        "d56356b4a34b32489b5b2e1cc6c782479e910b9711eeff8b74d22d483d8880fe",
    ),
    (
        "data/external/psid_codebook_field_evidence/"
        "ry2015_2022_exclusion_lineage_v1.json",
        19_011,
        28_227_120,
        "d7018a633ec8127ab799d07db58f63d1582e5417c305c9c03d63b08c41803f78",
    ),
)

EXPECTED_EVIDENCE_IDENTITY_SHA256 = (
    "235b568b54ba04e43d5be85aa4a922148e9ca01f431b94c95ca5fa1976403d9a"
)
EXPECTED_RAW_IDENTITY_SHA256 = (
    "079811364c1ea8f6fbaa624cd4e624570b082ad911307401f8222b73a0affc8d"
)
EXPECTED_DENOMINATOR_SHA256 = (
    "7e497f20e05cbdad384daece86d4aa08b16587b83cb6290193b6fdc28705b764"
)
EXPECTED_COUNT_ARRAY_SHA256 = (
    "421105abb63991c3cc1d14d15c98ff68803f7e50dd992107fd797a01ec346624"
)
EXPECTED_ASSIGNMENT_SHA256 = (
    "5c9020ad92ced4916dd1152f0ce06cc276878a0ca312cd34f9d25c3c3977e72e"
)

NUMERIC_FORM_KINDS = (
    "unsigned_ascii_integer",
    "leading_ascii_minus_signed_integer",
    "unsigned_ascii_implied_decimal",
    "leading_ascii_minus_signed_implied_decimal",
    "unsigned_literal_ascii_decimal",
    "leading_ascii_minus_signed_literal_ascii_decimal",
)
PADDING_ARMS = ("zero_left_padding", "left_ascii_space_padding")

_NUM = re.compile(r"NUM\(([1-9][0-9]*)\.(0|[1-9][0-9]*)\)\Z")
_SPSS_F = re.compile(r"F([1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
_CHR = re.compile(r"CHR\(([1-9][0-9]*)\)\Z")
_SOURCE_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


@dataclass(frozen=True)
class SourceField:
    """One authenticated field-evidence row in denominator order."""

    denominator_position: int
    evidence_path: str
    evidence_pointer: str
    evidence_row_sha256: str
    codebook_field_key: str
    interview_wave: int
    earnings_reference_year: int
    raw_field_id: str
    short_label: str
    declared_format: str
    layout_start: int
    layout_end: int
    raw_width: int
    spss_numeric_format: str | None
    description: str
    code_map: tuple[tuple[Any, ...], ...]
    missing_code_map_indices: tuple[int, ...]
    source_document_ids: tuple[str, ...]
    source_locator_ids: tuple[str, ...]
    derived_field_block_sha256: str

    @property
    def key(self) -> tuple[int, str]:
        """Return the canonical two-position field key."""

        return self.interview_wave, self.raw_field_id

    @property
    def start(self) -> int:
        """Return the zero-based half-open start coordinate."""

        return self.layout_start - 1

    @property
    def end(self) -> int:
        """Return the zero-based half-open end coordinate."""

        return self.layout_end


@dataclass(frozen=True)
class EvidenceCorpus:
    """Authenticated six-artifact source denominator."""

    fields: tuple[SourceField, ...]
    source_manifest: tuple[dict[str, Any], ...]
    artifact_identity_rows: tuple[dict[str, Any], ...]


def _canonical_compact_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_bytes(value: Any) -> bytes:
    """Return the section 10.1 canonical JSON encoding with one final LF."""

    return _canonical_compact_bytes(value) + b"\n"


def canonical_sha256(value: Any) -> str:
    """Hash a standalone section 10.1 canonical JSON value."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 of *value*."""

    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    """Hash a file without retaining its bytes."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_array_sha256(values: Iterable[Any]) -> str:
    """Hash an iterable as one canonical JSON array without materializing it."""

    digest = hashlib.sha256()
    digest.update(b"[")
    for index, value in enumerate(values):
        if index:
            digest.update(b",")
        digest.update(_canonical_compact_bytes(value))
    digest.update(b"]\n")
    return digest.hexdigest()


def _project_document_role(dictionary_role: str) -> str:
    if dictionary_role in {"stata_setup", "spss_setup"}:
        return "dictionary_layout"
    if dictionary_role in {
        "family_codebook",
        "stata_value_labels",
        "spss_value_labels",
    }:
        return "codebook"
    if dictionary_role == "raw_fixed_width":
        return "raw_fixed_width_data"
    raise ValueError(f"unsupported source role: {dictionary_role}")


def _project_source_manifest_row(row: Mapping[str, Any]) -> dict[str, Any]:
    role = _project_document_role(row["dictionary_role"])
    waves = [row["interview_wave"]]
    preimage = [
        role,
        waves,
        row["path"],
        row["size_bytes"],
        row["sha256"],
    ]
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


def load_authenticated_evidence(
    repo_root: Path = REPO_ROOT,
    psid_root: Path = DEFAULT_PSID_ROOT,
    *,
    authenticate_source_files: bool = True,
) -> EvidenceCorpus:
    """Load the six pinned evidence artifacts and authenticate their corpus.

    Field rows are returned in the §20.3.7 denominator order: artifact,
    declared wave, then physical field-evidence position within that wave.
    Source files are hashed incrementally and are never retained in memory.
    """

    fields: list[SourceField] = []
    artifact_identities: list[dict[str, Any]] = []
    upstream_documents: dict[str, dict[str, Any]] = {}
    denominator_position = 0
    for (
        relative_path,
        expected_count,
        expected_size,
        expected_sha,
    ) in EVIDENCE_SPECS:
        path = repo_root / relative_path
        raw_bytes = path.read_bytes()
        if len(raw_bytes) != expected_size:
            raise ValueError(f"evidence size mismatch: {relative_path}")
        if sha256_bytes(raw_bytes) != expected_sha:
            raise ValueError(f"evidence SHA-256 mismatch: {relative_path}")
        artifact = json.loads(raw_bytes)
        rows = artifact["field_evidence"]
        if (
            artifact["field_evidence_count"] != expected_count
            or len(rows) != expected_count
        ):
            raise ValueError(f"evidence count mismatch: {relative_path}")
        artifact_identities.append(
            {
                "evidence_path": relative_path,
                "field_evidence_count": expected_count,
                "raw_sha256": expected_sha,
            }
        )
        for document in artifact["source_authority_manifest"]:
            old = upstream_documents.setdefault(
                document["document_id"], document
            )
            if old != document:
                raise ValueError(
                    "unequal repeated source manifest row: "
                    f"{document['document_id']}"
                )

        columns = {
            name: index
            for index, name in enumerate(artifact["field_evidence_columns"])
        }
        physical_rows = list(enumerate(rows))
        ordered_rows = [
            item
            for wave in artifact["interview_waves"]
            for item in physical_rows
            if item[1][columns["interview_wave"]] == wave
        ]
        if len(ordered_rows) != len(rows):
            raise ValueError(f"field wave cover mismatch: {relative_path}")
        for physical_index, row in ordered_rows:
            row_width = (
                row[columns["layout_end"]] - row[columns["layout_start"]] + 1
            )
            if row_width != row[columns["raw_width"]]:
                raise ValueError(
                    "field coordinate mismatch: "
                    f"{row[columns['interview_wave']]}/"
                    f"{row[columns['raw_field_id']]}"
                )
            fields.append(
                SourceField(
                    denominator_position=denominator_position,
                    evidence_path=relative_path,
                    evidence_pointer=f"/field_evidence/{physical_index}",
                    evidence_row_sha256=canonical_sha256(row),
                    codebook_field_key=row[columns["codebook_field_key"]],
                    interview_wave=row[columns["interview_wave"]],
                    earnings_reference_year=row[
                        columns["earnings_reference_year"]
                    ],
                    raw_field_id=row[columns["raw_field_id"]],
                    short_label=row[columns["exact_codebook_short_label"]],
                    declared_format=row[columns["declared_format"]],
                    layout_start=row[columns["layout_start"]],
                    layout_end=row[columns["layout_end"]],
                    raw_width=row[columns["raw_width"]],
                    spss_numeric_format=row[columns["spss_numeric_format"]],
                    description=row[columns["full_source_description"]],
                    code_map=tuple(
                        tuple(code_row)
                        for code_row in row[columns["code_map"]]
                    ),
                    missing_code_map_indices=tuple(
                        row[columns["missing_code_map_indices"]]
                    ),
                    source_document_ids=tuple(
                        row[columns["source_document_ids"]]
                    ),
                    source_locator_ids=tuple(
                        row[columns["source_locator_ids"]]
                    ),
                    derived_field_block_sha256=row[
                        columns["derived_field_block_sha256"]
                    ],
                )
            )
            denominator_position += 1

    if canonical_sha256(artifact_identities) != (
        EXPECTED_EVIDENCE_IDENTITY_SHA256
    ):
        raise ValueError("complete evidence identity mismatch")
    keys = [list(field.key) for field in fields]
    if len(fields) != 89_599 or len(set(field.key for field in fields)) != len(
        fields
    ):
        raise ValueError("field denominator is not an 89,599-key exact cover")
    if canonical_sha256(keys) != EXPECTED_DENOMINATOR_SHA256:
        raise ValueError("field denominator SHA-256 mismatch")

    source_manifest = sorted(
        (
            _project_source_manifest_row(row)
            for row in upstream_documents.values()
        ),
        key=lambda row: (
            (
                "questionnaire_flow",
                "dictionary_layout",
                "codebook",
                "raw_fixed_width_data",
            ).index(row["document_role"]),
            row["interview_waves"][0],
            row["canonical_source_path"].encode("utf-8"),
            row["source_document_id"],
        ),
    )
    if len(source_manifest) != 176:
        raise ValueError("source manifest is not a 176-document exact cover")
    if authenticate_source_files:
        for document in source_manifest:
            source_path = psid_root / document["canonical_source_path"]
            if not source_path.is_file() or source_path.is_symlink():
                raise ValueError(
                    f"source is not a regular file: {source_path}"
                )
            if source_path.stat().st_size != document["byte_size"]:
                raise ValueError(f"source size mismatch: {source_path}")
            if sha256_file(source_path) != document["sha256"]:
                raise ValueError(f"source SHA-256 mismatch: {source_path}")
    return EvidenceCorpus(
        fields=tuple(fields),
        source_manifest=tuple(source_manifest),
        artifact_identity_rows=tuple(artifact_identities),
    )


def parse_format_declaration(
    source_format_text: str | None,
) -> tuple[str, int, int | None] | None:
    """Parse one declaration under the closed revision-9 syntax."""

    if source_format_text is None:
        return None
    match = _NUM.fullmatch(source_format_text)
    if match:
        width, decimal_places = map(int, match.groups())
        if decimal_places >= width:
            return None
        return (
            "num_parenthesized_numeric_declaration",
            width,
            decimal_places,
        )
    match = _SPSS_F.fullmatch(source_format_text)
    if match:
        width, decimal_places = map(int, match.groups())
        if decimal_places >= width:
            return None
        return "spss_f_numeric_declaration", width, decimal_places
    match = _CHR.fullmatch(source_format_text)
    if match:
        return "character_declaration", int(match.group(1)), None
    return None


def _format_assertion_id(
    interview_wave: int,
    raw_field_id: str,
    assertion: Mapping[str, Any],
) -> str:
    preimage = [
        interview_wave,
        raw_field_id,
        assertion["source_kind"],
        assertion["source_field_row_id"],
        assertion["parser_family"],
        assertion["source_format_text"],
        assertion["source_locator_ids"],
    ]
    return "psid-source-format-assertion:" + canonical_sha256(preimage)


def build_source_format_projection(
    interview_wave: int,
    raw_field_id: str,
    assertions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply the source-ordered declaration disposition relation.

    Every assertion remains visible.  Later assertions compare directly to
    the unique first supported selector, including the hostile
    ``F6.2, NUM(6.2), NUM(6.2)`` case.
    """

    parsed = [
        parse_format_declaration(row["source_format_text"])
        for row in assertions
    ]
    selector_index = next(
        (index for index, value in enumerate(parsed) if value is not None),
        None,
    )
    selector_id = (
        _format_assertion_id(
            interview_wave,
            raw_field_id,
            assertions[selector_index],
        )
        if selector_index is not None
        else None
    )
    selector_parse = (
        parsed[selector_index] if selector_index is not None else None
    )
    selector_text = (
        assertions[selector_index]["source_format_text"]
        if selector_index is not None
        else None
    )

    result: list[dict[str, Any]] = []
    for index, (assertion, normalized) in enumerate(
        zip(assertions, parsed, strict=True)
    ):
        source_text = assertion["source_format_text"]
        assertion_id = (
            None
            if source_text is None
            else _format_assertion_id(
                interview_wave,
                raw_field_id,
                assertion,
            )
        )
        if source_text is None:
            disposition = "source_silence"
            selecting_id = None
        elif normalized is None:
            disposition = "unsupported_source_declaration"
            selecting_id = selector_id
        elif index == selector_index:
            disposition = (
                "selecting_character_declaration"
                if normalized[0] == "character_declaration"
                else "selecting_numeric_declaration"
            )
            selecting_id = assertion_id
        elif source_text == selector_text and normalized == selector_parse:
            disposition = "corroborating_byte_equal_declaration"
            selecting_id = selector_id
        elif (
            normalized[0] != "character_declaration"
            and selector_parse is not None
            and selector_parse[0] != "character_declaration"
            and normalized[1:] == selector_parse[1:]
        ):
            disposition = "corroborating_tuple_equivalent_numeric_declaration"
            selecting_id = selector_id
        else:
            disposition = "conflicting_source_declaration"
            selecting_id = selector_id

        result.append(
            {
                "source_kind": assertion["source_kind"],
                "source_field_row_id": assertion["source_field_row_id"],
                "parser_family": assertion["parser_family"],
                "source_format_text": source_text,
                "source_format_assertion_id": assertion_id,
                "normalized_format_kind": (
                    normalized[0] if normalized is not None else None
                ),
                "normalized_width": (
                    normalized[1] if normalized is not None else None
                ),
                "normalized_decimal_places": (
                    normalized[2] if normalized is not None else None
                ),
                "declaration_disposition": disposition,
                "selecting_source_format_assertion_id": selecting_id,
            }
        )
    return result


def parse_source_number(source_value_lexeme: str) -> Fraction | None:
    """Parse an exact ASCII source scalar, removing grouping commas only."""

    text = source_value_lexeme.strip(" \t").replace(",", "")
    if not _SOURCE_NUMBER.fullmatch(text):
        return None
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    if "." in text:
        whole, fractional = text.split(".")
        numerator = int(whole + fractional)
        value = Fraction(numerator, 10 ** len(fractional))
    else:
        value = Fraction(int(text), 1)
    return -value if negative else value


def numeric_form_order(decimal_places: int) -> tuple[str, ...]:
    """Return the closed form order for the selected declaration."""

    if decimal_places == 0:
        return NUMERIC_FORM_KINDS[:2]
    return NUMERIC_FORM_KINDS[2:]


def _canonical_magnitude(value: int) -> str:
    if value < 0:
        raise ValueError("magnitude must be nonnegative")
    return str(value)


def _apply_padding(
    payload: str,
    width: int,
    padding_arm: str,
    *,
    negative: bool,
) -> bytes | None:
    sign_width = 1 if negative else 0
    padding_width = width - sign_width - len(payload)
    if padding_width < 0:
        return None
    sign = "-" if negative else ""
    if padding_arm == "left_ascii_space_padding":
        rendered = " " * padding_width + sign + payload
    elif padding_arm == "zero_left_padding":
        rendered = sign + "0" * padding_width + payload
    else:
        raise ValueError(f"unknown padding arm: {padding_arm}")
    encoded = rendered.encode("ascii")
    return encoded if len(encoded) == width else None


def render_numeric_token(
    value: Fraction,
    width: int,
    decimal_places: int,
    token_form_kind: str,
    padding_arm: str,
    *,
    implied_scale: Fraction = Fraction(1, 1),
) -> bytes | None:
    """Render one exact scalar without rounding, truncation, or floats."""

    if implied_scale <= 0:
        raise ValueError("implied_scale must be positive")
    scaled = value / implied_scale
    negative = scaled < 0
    signed = token_form_kind.startswith("leading_ascii_minus_signed_")
    if negative and not signed:
        return None
    magnitude = abs(scaled)

    if token_form_kind.endswith("_integer"):
        if decimal_places != 0 or magnitude.denominator != 1:
            return None
        payload = _canonical_magnitude(magnitude.numerator)
        return _apply_padding(
            payload,
            width,
            padding_arm,
            negative=negative,
        )

    if token_form_kind.endswith("_implied_decimal"):
        if decimal_places <= 0:
            return None
        encoded = magnitude * (10**decimal_places)
        if encoded.denominator != 1:
            return None
        payload = _canonical_magnitude(encoded.numerator)
        return _apply_padding(
            payload,
            width,
            padding_arm,
            negative=negative,
        )

    if token_form_kind.endswith("_literal_ascii_decimal"):
        if decimal_places <= 0:
            return None
        integral = magnitude.numerator // magnitude.denominator
        integral_text = str(integral)
        sign_width = 1 if negative else 0
        fractional_places = min(
            decimal_places,
            width - sign_width - len(integral_text) - 1,
        )
        if fractional_places < 1:
            return None
        exact = magnitude * (10**fractional_places)
        if exact.denominator != 1:
            return None
        digits = str(exact.numerator).zfill(
            len(integral_text) + fractional_places
        )
        payload = (
            digits[:-fractional_places] + "." + digits[-fractional_places:]
        )
        return _apply_padding(
            payload,
            width,
            padding_arm,
            negative=negative,
        )

    raise ValueError(f"unknown token form: {token_form_kind}")


def parse_rendered_numeric_token(
    raw_token: bytes,
    width: int,
    decimal_places: int,
    token_form_kind: str,
    padding_arm: str,
    *,
    implied_scale: Fraction = Fraction(1, 1),
) -> Fraction | None:
    """Parse only a canonical token for the named form and arm."""

    if len(raw_token) != width:
        return None
    try:
        text = raw_token.decode("ascii")
    except UnicodeDecodeError:
        return None
    if padding_arm == "left_ascii_space_padding":
        payload = text.lstrip(" ")
        if not payload or " " in payload:
            return None
    elif padding_arm == "zero_left_padding":
        if " " in text:
            return None
        payload = text
    else:
        raise ValueError(f"unknown padding arm: {padding_arm}")

    negative = payload.startswith("-")
    if negative:
        payload = payload[1:]
    signed = token_form_kind.startswith("leading_ascii_minus_signed_")
    if negative and not signed:
        return None

    if token_form_kind.endswith("_integer"):
        if (
            decimal_places != 0
            or not payload.isascii()
            or not payload.isdigit()
        ):
            return None
        value = Fraction(int(payload), 1)
    elif token_form_kind.endswith("_implied_decimal"):
        if (
            decimal_places <= 0
            or not payload.isascii()
            or not payload.isdigit()
        ):
            return None
        value = Fraction(int(payload), 10**decimal_places)
    elif token_form_kind.endswith("_literal_ascii_decimal"):
        if decimal_places <= 0 or payload.count(".") != 1:
            return None
        whole, fractional = payload.split(".")
        if (
            not whole
            or not fractional
            or len(fractional) > decimal_places
            or not whole.isascii()
            or not fractional.isascii()
            or not whole.isdigit()
            or not fractional.isdigit()
        ):
            return None
        value = Fraction(
            int(whole + fractional),
            10 ** len(fractional),
        )
    else:
        raise ValueError(f"unknown token form: {token_form_kind}")

    if negative:
        value = -value
    value *= implied_scale
    replay = render_numeric_token(
        value,
        width,
        decimal_places,
        token_form_kind,
        padding_arm,
        implied_scale=implied_scale,
    )
    return value if replay == raw_token else None


def transition_action(input_byte: int) -> str:
    """Return the exact action for an admitted source byte."""

    if input_byte == 0x20:
        return "no_op"
    if input_byte == 0x2D:
        return "set_negative"
    if input_byte == 0x2E:
        return "consume_decimal_point"
    if 0x30 <= input_byte <= 0x39:
        return f"append_digit_{input_byte - 0x30}"
    raise ValueError(f"unsupported DFA byte: {input_byte:#x}")


def _serialize_minimized_dfa(
    children: Sequence[Mapping[int, int]],
    accepting: Sequence[bool],
    depths: Sequence[int],
    payload_width: int,
) -> dict[str, Any]:
    """Minimize and serialize one reachable, acyclic, fixed-width DFA."""

    coreachable = set(
        index for index, is_accepting in enumerate(accepting) if is_accepting
    )
    for depth in range(payload_width - 1, -1, -1):
        for node, node_depth in enumerate(depths):
            if node_depth == depth and any(
                target in coreachable for target in children[node].values()
            ):
                coreachable.add(node)
    if 0 not in coreachable:
        raise ValueError("accepted fixed-width language must be nonempty")

    class_by_node: list[int] = [-1] * len(children)
    class_signature_to_id: dict[tuple[Any, ...], int] = {}
    class_children: dict[int, dict[int, int]] = {}
    class_accepting: dict[int, bool] = {}
    class_depth: dict[int, int] = {}
    for depth in range(payload_width, -1, -1):
        for node, node_depth in enumerate(depths):
            if node_depth != depth or node not in coreachable:
                continue
            edges = tuple(
                (
                    byte,
                    transition_action(byte),
                    class_by_node[target],
                )
                for byte, target in sorted(children[node].items())
                if target in coreachable
            )
            signature = (depth, accepting[node], edges)
            class_id = class_signature_to_id.get(signature)
            if class_id is None:
                class_id = len(class_signature_to_id)
                class_signature_to_id[signature] = class_id
                class_children[class_id] = {
                    byte: target_class for byte, _, target_class in edges
                }
                class_accepting[class_id] = accepting[node]
                class_depth[class_id] = depth
            class_by_node[node] = class_id

    root_class = class_by_node[0]
    bfs_classes: list[int] = []
    queue = deque([root_class])
    queued = {root_class}
    while queue:
        state_class = queue.popleft()
        bfs_classes.append(state_class)
        for _, target in sorted(class_children[state_class].items()):
            if target not in queued:
                queued.add(target)
                queue.append(target)
    state_id = {
        state_class: f"q:{index}"
        for index, state_class in enumerate(bfs_classes)
    }
    state_ids = [state_id[state_class] for state_class in bfs_classes]
    accepting_state_ids = [
        state_id[state_class]
        for state_class in bfs_classes
        if class_accepting[state_class]
    ]
    transitions = [
        {
            "position": class_depth[state_class],
            "state_id": state_id[state_class],
            "input_byte_hex": bytes([byte]).hex(),
            "next_state_id": state_id[target_class],
            "value_action": transition_action(byte),
        }
        for state_class in bfs_classes
        for byte, target_class in sorted(class_children[state_class].items())
    ]
    transitions.sort(
        key=lambda row: (
            row["position"],
            int(row["state_id"].split(":", 1)[1]),
            int(row["input_byte_hex"], 16),
        )
    )
    return {
        "payload_width": payload_width,
        "state_ids": state_ids,
        "start_state_id": "q:0",
        "accepting_state_ids": accepting_state_ids,
        "transition_rows": transitions,
        "transition_row_count": len(transitions),
        "transition_domain_sha256": canonical_sha256(transitions),
    }


def compile_exact_token_dfa(
    raw_tokens: Iterable[bytes],
    payload_width: int,
) -> dict[str, Any]:
    """Build and action-sensitively minimize an exact-token DFA.

    The implementation creates the prefix trie, quotients only same-depth
    states with identical accepting/action-labelled suffix behavior, removes
    the reject sink by never creating it, and numbers the quotient with BFS
    and unsigned-byte edge order.
    """

    if payload_width <= 0:
        raise ValueError("payload_width must be positive")
    children: list[dict[int, int]] = [{}]
    accepting: list[bool] = [False]
    depths: list[int] = [0]
    seen_tokens: set[bytes] = set()
    for token in raw_tokens:
        if len(token) != payload_width:
            raise ValueError("token width mismatch")
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        state = 0
        for depth, byte in enumerate(token, start=1):
            transition_action(byte)
            next_state = children[state].get(byte)
            if next_state is None:
                next_state = len(children)
                children[state][byte] = next_state
                children.append({})
                accepting.append(False)
                depths.append(depth)
            state = next_state
        accepting[state] = True
    if not seen_tokens:
        raise ValueError("accepted exact-token language must be nonempty")

    return _serialize_minimized_dfa(
        children,
        accepting,
        depths,
        payload_width,
    )


def _numeric_form_patterns(
    width: int,
    decimal_places: int,
    token_form_kind: str,
    padding_arm: str,
) -> tuple[tuple[frozenset[int], ...], ...]:
    """Return a compact Cartesian-pattern cover of one canonical form."""

    digits = frozenset(range(0x30, 0x3A))
    nonzero = frozenset(range(0x31, 0x3A))
    zero = frozenset({0x30})
    space = frozenset({0x20})
    minus = frozenset({0x2D})
    point = frozenset({0x2E})
    signed = token_form_kind.startswith("leading_ascii_minus_signed_")
    if padding_arm not in PADDING_ARMS:
        raise ValueError(f"unknown padding arm: {padding_arm}")
    if padding_arm == "zero_left_padding":
        if token_form_kind.endswith("_literal_ascii_decimal"):
            padding = zero
        else:
            # Zero padding is not canonical magnitude padding: it is part of
            # the digit payload and can precede a nonzero magnitude.
            padding = zero
    else:
        padding = space

    patterns: list[tuple[frozenset[int], ...]] = []
    if token_form_kind.endswith("_integer") or token_form_kind.endswith(
        "_implied_decimal"
    ):
        if token_form_kind.endswith("_integer") and decimal_places != 0:
            return ()
        if token_form_kind.endswith("_implied_decimal") and (
            decimal_places <= 0
        ):
            return ()
        for negative in (False, True) if signed else (False,):
            sign_width = int(negative)
            for magnitude_width in range(1, width - sign_width + 1):
                pad_width = width - sign_width - magnitude_width
                if padding_arm == "zero_left_padding":
                    # The renderer emits the sign before zero fill.  Every
                    # unsigned payload is simply w digits; retain one cover.
                    if negative:
                        pattern = (minus,) + (zero,) * pad_width
                        pattern += (nonzero,) + (digits,) * (
                            magnitude_width - 1
                        )
                    else:
                        if magnitude_width != width:
                            continue
                        pattern = (digits,) * width
                else:
                    first = digits if magnitude_width == 1 else nonzero
                    if negative and magnitude_width == 1:
                        first = nonzero
                    pattern = (space,) * pad_width
                    if negative:
                        pattern += (minus,)
                    pattern += (first,) + (digits,) * (magnitude_width - 1)
                patterns.append(pattern)
    elif token_form_kind.endswith("_literal_ascii_decimal"):
        if decimal_places <= 0:
            return ()
        for negative in (False, True) if signed else (False,):
            sign_width = int(negative)
            for integral_width in range(1, width):
                capacity = width - sign_width - integral_width - 1
                if capacity < 1:
                    continue
                fractional_width = min(decimal_places, capacity)
                pad_width = capacity - fractional_width
                if padding_arm == "zero_left_padding" and pad_width:
                    # Literal-decimal zero padding precedes the canonical
                    # integral payload, exactly as the renderer specifies.
                    pad = (zero,) * pad_width
                else:
                    pad = (padding,) * pad_width
                first = digits if integral_width == 1 else nonzero
                if negative and integral_width == 1:
                    # Excluding only negative numeric zero is handled as a
                    # finite token subtraction by the caller when needed.
                    first = digits
                pattern = pad
                if negative:
                    pattern += (minus,)
                pattern += (first,) + (digits,) * (integral_width - 1)
                pattern += (point,) + (digits,) * fractional_width
                patterns.append(pattern)
    else:
        raise ValueError(f"unknown token form: {token_form_kind}")
    return tuple(dict.fromkeys(patterns))


def compile_numeric_form_dfa(
    payload_width: int,
    decimal_places: int,
    token_form_kind: str,
    padding_arm: str,
    *,
    excluded_tokens: Iterable[bytes] = (),
) -> dict[str, Any]:
    """Compile a full canonical numeric-form language minus exact tokens.

    Pattern determinization keeps the construction proportional to width and
    the finite exclusion set; it never enumerates ``10**payload_width``
    possible observations.
    """

    patterns = _numeric_form_patterns(
        payload_width,
        decimal_places,
        token_form_kind,
        padding_arm,
    )
    if not patterns:
        raise ValueError("numeric form has an empty pattern cover")
    exclusion_set = set(excluded_tokens)
    if token_form_kind == ("leading_ascii_minus_signed_literal_ascii_decimal"):
        fractional_width = min(decimal_places, payload_width - 3)
        if fractional_width >= 1:
            pad_width = payload_width - 3 - fractional_width
            pad_byte = b"0" if padding_arm == "zero_left_padding" else b" "
            exclusion_set.add(
                pad_byte * pad_width + b"-0." + b"0" * fractional_width
            )
    exclusions = tuple(sorted(exclusion_set))
    if any(len(token) != payload_width for token in exclusions):
        raise ValueError("excluded token width mismatch")

    start = (0, tuple(range(len(patterns))), tuple(range(len(exclusions))))
    states = [start]
    state_index = {start: 0}
    children: list[dict[int, int]] = [{}]
    accepting = [False]
    depths = [0]
    queue = deque([start])
    while queue:
        depth, active_patterns, active_exclusions = queue.popleft()
        node = state_index[(depth, active_patterns, active_exclusions)]
        if depth == payload_width:
            accepting[node] = not active_exclusions
            continue
        alphabet = sorted(
            set().union(*(patterns[index][depth] for index in active_patterns))
        )
        for byte in alphabet:
            next_patterns = tuple(
                index
                for index in active_patterns
                if byte in patterns[index][depth]
            )
            if not next_patterns:
                continue
            next_exclusions = tuple(
                index
                for index in active_exclusions
                if exclusions[index][depth] == byte
            )
            next_state = (depth + 1, next_patterns, next_exclusions)
            target = state_index.get(next_state)
            if target is None:
                target = len(states)
                state_index[next_state] = target
                states.append(next_state)
                children.append({})
                accepting.append(False)
                depths.append(depth + 1)
                queue.append(next_state)
            children[node][byte] = target
    return _serialize_minimized_dfa(
        children,
        accepting,
        depths,
        payload_width,
    )


def build_registered_numeric_grammar(
    raw_tokens: Iterable[bytes],
    payload_width: int,
    value_derivation: Mapping[str, Any],
) -> dict[str, Any]:
    """Serialize the ten-key registered grammar around an exact-token DFA."""

    dfa = compile_exact_token_dfa(raw_tokens, payload_width)
    invalid_action = (
        "abort_before_classification_require_successor_inventory_ratification"
    )
    preimage = [
        dfa["payload_width"],
        dfa["state_ids"],
        dfa["start_state_id"],
        dfa["accepting_state_ids"],
        dfa["transition_rows"],
        dfa["transition_row_count"],
        dfa["transition_domain_sha256"],
        dict(value_derivation),
        invalid_action,
    ]
    return {
        "grammar_id": "psid-numeric-grammar:" + canonical_sha256(preimage),
        **dfa,
        "value_derivation": dict(value_derivation),
        "invalid_payload_action": invalid_action,
    }


def extract_dictionary_layout_rows(*args: Any, **kwargs: Any) -> Any:
    """Revision-9 dictionary extraction entry point (implemented below)."""

    raise NotImplementedError(
        "all-source dictionary extraction is not built yet"
    )


def frame_fixed_width_records(
    source_document: Mapping[str, Any],
    fields: Sequence[SourceField],
    psid_root: Path = DEFAULT_PSID_ROOT,
    *,
    framing_source_row_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Frame one authenticated raw file and derive every field census row.

    The raw file remains a read-only memory map.  Each field is sliced from
    the fixed-width record matrix independently, so memory use is bounded by
    one wave plus one field-column copy rather than all 255.6M observations.
    """

    if source_document["document_role"] != "raw_fixed_width_data":
        raise ValueError("frame input is not raw_fixed_width_data")
    waves = source_document["interview_waves"]
    if len(waves) != 1:
        raise ValueError("raw source must name exactly one wave")
    wave = waves[0]
    wave_fields = [field for field in fields if field.interview_wave == wave]
    if not wave_fields:
        raise ValueError(f"raw source has no fields: {wave}")
    record_width = max(field.end for field in wave_fields)
    if any(field.end > record_width for field in wave_fields):
        raise AssertionError("unreachable coordinate error")
    source_path = psid_root / source_document["canonical_source_path"]
    size_bytes = source_path.stat().st_size
    record_size = record_width + 2
    record_count, remainder = divmod(size_bytes, record_size)
    if remainder or record_count <= 0:
        raise ValueError(f"raw framing remainder: {source_path}")

    raw = np.memmap(source_path, dtype=np.uint8, mode="r")
    physical_records = raw.reshape(record_count, record_size)
    if not (
        np.all(physical_records[:, record_width] == 0x0D)
        and np.all(physical_records[:, record_width + 1] == 0x0A)
    ):
        raise ValueError(f"raw separator mismatch: {source_path}")
    records = physical_records[:, :record_width]

    record_domain_sha256 = _canonical_array_sha256(
        [
            record_index,
            sha256_bytes(bytes(records[record_index])),
        ]
        for record_index in range(record_count)
    )
    field_census_rows: list[dict[str, Any]] = []
    for field in wave_fields:
        observed, frequencies = np.unique(
            records[:, field.start : field.end],
            axis=0,
            return_counts=True,
        )
        observed_token_rows = [
            {
                "raw_token_hex": bytes(token).hex(),
                "frequency": int(frequency),
            }
            for token, frequency in zip(observed, frequencies, strict=True)
        ]
        field_census_rows.append(
            {
                "interview_wave": field.interview_wave,
                "raw_field_id": field.raw_field_id,
                "start": field.start,
                "end": field.end,
                "raw_width": field.raw_width,
                "observed_token_rows": observed_token_rows,
                "observed_token_row_count": len(observed_token_rows),
                "observed_token_rows_sha256": canonical_sha256(
                    observed_token_rows
                ),
            }
        )
    del records
    del physical_records
    del raw

    empty_sha256 = sha256_bytes(b"")
    record_framing = {
        "record_width": record_width,
        "header_byte_count": 0,
        "header_sha256": empty_sha256,
        "trailer_byte_count": 0,
        "trailer_sha256": empty_sha256,
        "record_separator_hex": "0d0a",
        "separator_placement": "between_records_and_terminal",
        "framing_source_row_ids": list(framing_source_row_ids),
    }
    return {
        "source_document_id": source_document["source_document_id"],
        "derivation_kind": "fixed_width_records",
        "record_framing": record_framing,
        "record_count": record_count,
        "record_keyset_sha256": _canonical_array_sha256(range(record_count)),
        "record_domain_sha256": record_domain_sha256,
        "field_census_rows": field_census_rows,
        "field_census_row_count": len(field_census_rows),
        "field_census_keyset_sha256": canonical_sha256(
            [
                [row["interview_wave"], row["raw_field_id"]]
                for row in field_census_rows
            ]
        ),
        "field_census_domain_sha256": canonical_sha256(field_census_rows),
    }


def derive_all_raw_censuses(
    corpus: EvidenceCorpus,
    psid_root: Path = DEFAULT_PSID_ROOT,
) -> tuple[dict[str, Any], ...]:
    """Derive all 43 raw document rows in canonical document order."""

    raw_documents = [
        row
        for row in corpus.source_manifest
        if row["document_role"] == "raw_fixed_width_data"
    ]
    derivations = tuple(
        frame_fixed_width_records(document, corpus.fields, psid_root)
        for document in raw_documents
    )
    raw_identity_rows = [
        {
            "interview_wave": document["interview_waves"][0],
            "path": document["canonical_source_path"],
            "record_count": derivation["record_count"],
            "record_width": derivation["record_framing"]["record_width"],
            "sha256": document["sha256"],
            "size_bytes": document["byte_size"],
        }
        for document, derivation in zip(
            raw_documents, derivations, strict=True
        )
    ]
    if canonical_sha256(raw_identity_rows) != EXPECTED_RAW_IDENTITY_SHA256:
        raise ValueError("complete raw identity mismatch")
    return derivations


def extract_codebook_rows(*args: Any, **kwargs: Any) -> Any:
    """Revision-9 codebook extraction entry point (implemented below)."""

    raise NotImplementedError(
        "all-source codebook extraction is not built yet"
    )


def derive_source_numeric_grammar(*args: Any, **kwargs: Any) -> Any:
    """Revision-9 complete numeric compiler entry point (implemented below)."""

    raise NotImplementedError("all-field grammar derivation is not built yet")
