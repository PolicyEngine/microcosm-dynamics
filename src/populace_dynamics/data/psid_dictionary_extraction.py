"""Source-only ``extract_dictionary_layout_rows`` for the 86 setup documents.

§20.2.3 requires the v3 implementation to reproduce every document derivation
independently: the committed field-evidence artifacts pin coordinates for
regression but cannot supply a canonical row.  This module therefore parses
the registered Stata and SPSS setup files themselves and emits the §19.3.2
canonical dictionary rows, their decoder, and their exact byte-range region
locators.

It covers the ``dictionary_layout`` role only.  The 47 ``codebook`` documents
are a separate entry point and are not derived here.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .psid_source_compiler import (
    DEFAULT_PSID_ROOT,
    canonical_sha256,
    sha256_bytes,
)

STATA_PARSER_FAMILY = "psid_stata_setup_statements_v1"
SPSS_PARSER_FAMILY = "psid_spss_setup_statements_v1"

# The setups prefix a field statement with an optional Stata storage type.
# Only `long` and `str` occur across the 43 registered Stata documents; the
# prefix is source syntax and never a declared parse kind.
_STORAGE_TYPES = rb"byte|int|long|float|double|strL|str[0-9]*"
_FIELD_TRIPLE = re.compile(
    rb"(?:\b(?:" + _STORAGE_TYPES + rb")\s+)?([A-Za-z][A-Za-z0-9_]*)\s+"
    rb"([0-9]+)\s*-\s*([0-9]+)"
)
_STATA_LABEL = re.compile(
    rb'label variable\s+([A-Za-z][A-Za-z0-9_]*)\s+"((?:[^"\\]|\\.)*)"\s*;'
)
_SPSS_LABEL = re.compile(
    rb'^\s*([A-Za-z][A-Za-z0-9_]*)\s+"((?:[^"\\]|\\.)*)"\s*$'
)
_SPSS_FORMAT = re.compile(
    rb"([A-Za-z][A-Za-z0-9_]*)\s+\(F([1-9][0-9]*)\.([0-9]+)\)"
)


@dataclass(frozen=True)
class DecodedSource:
    """One strictly decoded setup document."""

    raw: bytes
    text: str
    encoding: str
    bom_action: str


def decode_source(raw: bytes) -> DecodedSource:
    """Decode strict ``UTF-8`` then strict ``windows-1252``, in that order."""

    payload = raw
    bom_action = "forbidden"
    if payload.startswith(b"\xef\xbb\xbf"):
        payload = payload[3:]
        bom_action = "remove_one_source_declared_bom"
    for encoding in ("UTF-8", "windows-1252"):
        try:
            text = payload.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            continue
        return DecodedSource(raw, text, encoding, bom_action)
    raise ValueError("no registered decoder consumes the complete document")


def _locator_id(
    source_document_id: str,
    byte_start: int,
    byte_end: int,
    range_sha256: str,
) -> str:
    preimage = [
        source_document_id,
        "raw_byte_range",
        byte_start,
        byte_end,
        None,
        None,
        None,
        range_sha256,
    ]
    return "psid-source-region:" + canonical_sha256(preimage)


def _locator(
    source_document_id: str,
    raw: bytes,
    byte_start: int,
    byte_end: int,
) -> dict[str, Any]:
    if not 0 <= byte_start < byte_end <= len(raw):
        raise ValueError("locator coordinates must be a nonempty subrange")
    range_sha256 = sha256_bytes(raw[byte_start:byte_end])
    return {
        "source_region_locator_id": _locator_id(
            source_document_id,
            byte_start,
            byte_end,
            range_sha256,
        ),
        "locator_kind": "raw_byte_range",
        "byte_start": byte_start,
        "byte_end": byte_end,
        "page_number": None,
        "utf8_start": None,
        "utf8_end": None,
        "range_sha256": range_sha256,
    }


def _iter_lines(raw: bytes) -> Iterator[tuple[int, int, bytes]]:
    """Yield ``(start, end, content)`` byte coordinates for every source line."""

    position = 0
    total = len(raw)
    while position < total:
        newline = raw.find(b"\n", position)
        if newline == -1:
            yield position, total, raw[position:total]
            return
        content_end = newline
        if content_end > position and raw[content_end - 1 : content_end] == (
            b"\r"
        ):
            content_end -= 1
        yield position, content_end, raw[position:content_end]
        position = newline + 1


def _decode_label(value: bytes, encoding: str) -> str:
    return value.decode(encoding).replace('\\"', '"')


def _block_bounds(
    lines: Sequence[tuple[int, int, bytes]],
    predicate,
) -> tuple[int, int]:
    matched = [index for index, line in enumerate(lines) if predicate(line[2])]
    if not matched:
        raise ValueError("required source block is absent")
    return matched[0], matched[-1]


def _stata_layout(
    raw: bytes,
    encoding: str,
) -> tuple[list[tuple[str, int, int, int, int]], dict[str, tuple[str, int, int]]]:
    lines = list(_iter_lines(raw))
    start_index, _ = _block_bounds(
        lines, lambda content: content.strip().startswith(b"infix")
    )
    using_index, _ = _block_bounds(
        lines, lambda content: content.strip().startswith(b"using")
    )
    if using_index <= start_index:
        raise ValueError("stata infix block is not closed by a using clause")

    triples: list[tuple[str, int, int, int, int]] = []
    for line_start, line_end, content in lines[start_index:using_index]:
        payload = content
        offset = 0
        if payload.strip().startswith(b"infix"):
            offset = payload.index(b"infix") + len(b"infix")
        consumed = bytearray(b" " * len(payload))
        consumed[:offset] = payload[:offset]
        for match in _FIELD_TRIPLE.finditer(payload, offset):
            name = match.group(1).decode("ascii")
            triples.append(
                (
                    name,
                    int(match.group(2)),
                    int(match.group(3)),
                    line_start + match.start(),
                    line_start + match.end(),
                )
            )
            consumed[match.start() : match.end()] = payload[
                match.start() : match.end()
            ]
        residue = bytes(
            byte
            for index, byte in enumerate(payload)
            if consumed[index] == 0x20 and byte not in b" \t"
        )
        if residue:
            raise ValueError(
                f"unparsed stata field statement bytes: {residue!r}"
            )
        del line_end

    labels: dict[str, tuple[str, int, int]] = {}
    for line_start, _, content in lines[using_index:]:
        for match in _STATA_LABEL.finditer(content):
            name = match.group(1).decode("ascii")
            if name in labels:
                raise ValueError(f"duplicate stata label statement: {name}")
            labels[name] = (
                _decode_label(match.group(2), encoding),
                line_start + match.start(),
                line_start + match.end(),
            )
    return triples, labels


def _spss_layout(
    raw: bytes,
    encoding: str,
) -> tuple[
    list[tuple[str, int, int, int, int]],
    dict[str, tuple[str, int, int]],
    dict[str, tuple[int, int, int, int]],
]:
    lines = list(_iter_lines(raw))
    data_list_index, _ = _block_bounds(
        lines, lambda content: content.strip().startswith(b"DATA LIST")
    )
    terminators = [
        index
        for index, line in enumerate(lines)
        if index > data_list_index
        and (
            line[2].strip().startswith(b"FORMATS")
            or line[2].strip().startswith(b"VARIABLE LABELS")
        )
    ]
    if not terminators:
        raise ValueError("spss layout block has no closing section")
    layout_end = terminators[0]

    triples: list[tuple[str, int, int, int, int]] = []
    for line_start, _, content in lines[data_list_index:layout_end]:
        offset = 0
        if content.strip().startswith(b"DATA LIST"):
            slash = content.find(b"/")
            offset = len(content) if slash == -1 else slash + 1
        for match in _FIELD_TRIPLE.finditer(content, offset):
            triples.append(
                (
                    match.group(1).decode("ascii"),
                    int(match.group(2)),
                    int(match.group(3)),
                    line_start + match.start(),
                    line_start + match.end(),
                )
            )

    formats: dict[str, tuple[int, int, int, int]] = {}
    format_indexes = [
        index
        for index, line in enumerate(lines)
        if line[2].strip().startswith(b"FORMATS")
    ]
    label_index, _ = _block_bounds(
        lines,
        lambda content: content.strip().startswith(b"VARIABLE LABELS"),
    )
    if format_indexes:
        for line_start, _, content in lines[format_indexes[0] : label_index]:
            for match in _SPSS_FORMAT.finditer(content):
                name = match.group(1).decode("ascii")
                if name in formats:
                    raise ValueError(f"duplicate spss format: {name}")
                formats[name] = (
                    int(match.group(2)),
                    int(match.group(3)),
                    line_start + match.start(),
                    line_start + match.end(),
                )

    labels: dict[str, tuple[str, int, int]] = {}
    for line_start, _, content in lines[label_index:]:
        match = _SPSS_LABEL.match(content)
        if match is None:
            continue
        name = match.group(1).decode("ascii")
        if name in labels:
            raise ValueError(f"duplicate spss label statement: {name}")
        labels[name] = (
            _decode_label(match.group(2), encoding),
            line_start + match.start(1),
            line_start + match.end(),
        )
    return triples, labels, formats


def extract_dictionary_layout_rows(
    source_document: Mapping[str, Any],
    psid_root: Path = DEFAULT_PSID_ROOT,
) -> dict[str, Any]:
    """Derive one setup document's complete canonical dictionary rows."""

    if source_document["document_role"] != "dictionary_layout":
        raise ValueError("input is not a dictionary_layout document")
    path = psid_root / source_document["canonical_source_path"]
    raw = path.read_bytes()
    if len(raw) != source_document["byte_size"]:
        raise ValueError(f"dictionary size mismatch: {path}")
    if sha256_bytes(raw) != source_document["sha256"]:
        raise ValueError(f"dictionary SHA-256 mismatch: {path}")
    decoded = decode_source(raw)
    document_id = source_document["source_document_id"]

    formats: dict[str, tuple[int, int, int, int]] = {}
    if path.suffix == ".do":
        parser_family = STATA_PARSER_FAMILY
        row_terminator = ";"
        triples, labels = _stata_layout(raw, decoded.encoding)
    elif path.suffix == ".sps":
        parser_family = SPSS_PARSER_FAMILY
        row_terminator = "\n"
        triples, labels, formats = _spss_layout(raw, decoded.encoding)
    else:
        raise ValueError(f"unsupported dictionary parser family: {path}")

    locators: list[dict[str, Any]] = []
    seen_locators: set[str] = set()

    def register(byte_start: int, byte_end: int) -> str:
        locator = _locator(document_id, raw, byte_start, byte_end)
        identifier = locator["source_region_locator_id"]
        if identifier not in seen_locators:
            seen_locators.add(identifier)
            locators.append(locator)
        return identifier

    canonical_rows: list[dict[str, Any]] = []
    seen_fields: set[str] = set()
    for position, (name, source_start, source_end, start, end) in enumerate(
        triples
    ):
        if name in seen_fields:
            raise ValueError(f"duplicate dictionary field statement: {name}")
        seen_fields.add(name)
        row_locators = [register(start, end)]
        label = labels.get(name)
        if label is not None:
            row_locators.append(register(label[1], label[2]))
        declaration = formats.get(name)
        format_text = None
        decimal_places = None
        if declaration is not None:
            width, decimal_places, format_start, format_end = declaration
            format_text = f"F{width}.{decimal_places}"
            row_locators.append(register(format_start, format_end))
        canonical_rows.append(
            {
                "dictionary_field_row_id": f"{document_id}#row:{position}",
                "source_document_id": document_id,
                "source_row_position": position,
                "raw_field_id": name,
                "source_coordinate_basis": "one_based_inclusive",
                "source_start": source_start,
                "source_end": source_end,
                "start": source_start - 1,
                "end": source_end,
                "raw_width": source_end - source_start + 1,
                "declared_parse_kind": None,
                "declared_signed": None,
                "declared_decimal_places": decimal_places,
                "declared_implied_scale": None,
                "declared_typed_value_type": None,
                "declared_typed_value_unit": None,
                "source_label": None if label is None else label[0],
                "source_description": None,
                "source_format_text": format_text,
                "source_missing_literals": [],
                "source_locator_ids": row_locators,
            }
        )

    locators.sort(key=lambda row: (row["byte_start"], row["byte_end"]))
    row_ids = [row["dictionary_field_row_id"] for row in canonical_rows]
    return {
        "source_document_id": document_id,
        "derivation_kind": "dictionary_layout_rows",
        "decoder": {
            "decoder_kind": "strict_source_text",
            "encoding": decoded.encoding,
            "error_action": "abort",
            "bom_action": decoded.bom_action,
            "newline_action": "preserve_source_cr_lf_crlf_sequences",
        },
        "row_segmentation": {
            "parser_family": parser_family,
            "source_region_locators": locators,
            "row_terminator": row_terminator,
            "row_order": "first_complete_source_occurrence",
            "unparsed_field_statement_action": "abort",
        },
        "canonical_rows": canonical_rows,
        "canonical_row_count": len(canonical_rows),
        "canonical_row_keyset_sha256": canonical_sha256(row_ids),
        "canonical_row_domain_sha256": canonical_sha256(canonical_rows),
    }
