"""Source-only ``extract_codebook_rows`` for the 47 codebook documents.

§20.2.3 forbids evidence laundering: the committed field-evidence artifacts
pin actual field coordinates for regression but cannot supply a canonical
row.  This module therefore derives the §19.3.2 canonical codebook rows from
the registered documents themselves — the 43 family codebook PDFs under the
§19.3.3 pinned page-text derivation, and the four 2021/2023 value-label
files under the two setup-statement parser families.

Three normalized-entry members are deliberately *not* populated here, for
two different reasons.  ``raw_token_hex`` is deferred by §20.3.2, which
makes §19's "select one physical arm before inserting every normalized
literal" conditional and requires the complete semantic relation to be
parsed without it; the pre-profile constructor inserts it later.
``typed_value_unit`` and ``missing_reason_code`` are different: no
registered codebook page, value-label statement, or setup statement carries
either value, so neither has a source-determined derivation at all.
:func:`undetermined_entry_members` names those two, and
:func:`validate_document_derivation` refuses to call a derivation
§19.3.2-complete while they are unresolved.

The predecessor schema also requires ``typed_disposition``.  This extractor
retains its historical lexical classifier so the registered lane can be
reproduced, but Amendment 11 proves that classifier is a candidate rather
than source authority: substantive categories such as ``Never refused`` and
``missing finger`` match its substring grammar.  Literal disposition and the
dependent literal ``canonical_value`` branch therefore remain unadjudicated
outside this source-row serialization.  ``entry_ref``, ``entry_kind``, exact
lexeme/meaning, and a range's bounds and step remain source-derived.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any

DEFAULT_PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()


@dataclass(frozen=True)
class DecodedSource:
    """One strictly decoded source document."""

    raw: bytes
    text: str
    encoding: str
    bom_action: str


def decode_source(raw: bytes) -> DecodedSource:
    """Decode strict UTF-8 then strict windows-1252, in that order."""

    payload = raw
    bom_action = "forbidden"
    if payload.startswith(b"\xef\xbb\xbf"):
        payload = payload[3:]
        bom_action = "remove_one_source_declared_bom"
    for encoding in ("UTF-8", "windows-1252"):
        try:
            decoded = payload.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            continue
        return DecodedSource(raw, decoded, encoding, bom_action)
    raise ValueError("no registered decoder consumes the complete document")


def _canonical_compact_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Hash a standalone section 10.1 canonical JSON value."""

    return hashlib.sha256(_canonical_compact_bytes(value) + b"\n").hexdigest()


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 of *value*."""

    return hashlib.sha256(value).hexdigest()


PDF_PARSER_FAMILY = "psid_family_codebook_pages_v1"
STATA_PARSER_FAMILY = "psid_stata_setup_statements_v1"
SPSS_PARSER_FAMILY = "psid_spss_setup_statements_v1"

PDFTOTEXT_ARGUMENTS = ("-layout", "-enc", "UTF-8")
PDFTOTEXT_VERSION = "26.04.0"

# §19.3.2 fixes the complete supported source-format syntax.  A header-shaped
# line whose declaration is outside it is not a field statement.
_FORMAT = r"NUM\([0-9]+\.[0-9]+\)|F[0-9]+\.[0-9]+|CHR\([0-9]+\)"
_FIELD_HEADER = re.compile(
    rf'^([A-Za-z][A-Za-z0-9_]*)\s+"(.*)"\s+({_FORMAT})$'
)
_MAP_HEADER = re.compile(
    r"^\s*Count\s+%\s+Value/Range Code Value/Range Text\s*$"
)
_PAGE_FOOTER = re.compile(r"^\s*Page [0-9]+ of [0-9]+\s*$")

# A displayed count is a comma-grouped nonnegative integer or the exact
# suppressed-cell dash; a displayed percent is a two-decimal fraction or that
# same dash.  Across all 479,345 committed code-map rows the two cells are
# dashes together or numeric together, never mixed.
_COUNT = r"-|[0-9]{1,3}(?:,[0-9]{3})*"
_PERCENT = r"-|[0-9]{0,3}\.[0-9]{2}"
_NUMBER = r"-?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?|-?\.[0-9]+"
_VALUE = rf"(?:{_NUMBER})(?: - (?:{_NUMBER}))?"
_MAP_ROW = re.compile(
    rf"^\s*({_COUNT})\s+({_PERCENT})\s+({_VALUE})(?: (.*))?$"
)
_LEADING_NUMBER = re.compile(rf"^\s*({_NUMBER})(?: (.*))?$")
# A value cell too wide for its column wraps: the row keeps the range
# separator, and the upper bound's own sign, ahead of the meaning, while the
# bound's magnitude appears on the next line under the same column.
_WRAPPED_SEPARATOR = re.compile(r"^-\s+(?:(-)\s+)?")
_RANGE_LEXEME = re.compile(rf"^({_NUMBER}) - ({_NUMBER})$")

_STATA_DEFINE = re.compile(r"label define\s+([A-Za-z][A-Za-z0-9_]*)")
_STATA_VALUES = re.compile(
    r"label values\s+([A-Za-z][A-Za-z0-9_]*)\s+([A-Za-z][A-Za-z0-9_]*)\s*$"
)
_STATA_FORVALUES = re.compile(
    r"forvalues\s+n\s*=\s*(-?[0-9]+)\s*/\s*(-?[0-9]+)\s*\{"
)
# A meaning is a plain double-quoted string or, when it contains a double
# quote, Stata's compound `"..."' form.  Both are exact source lexemes.
_STATA_PAIR = re.compile(
    r"(`n'|-?[0-9]+)\s+(?:`\"(?P<compound>.*?)\"'|\"(?P<plain>[^\"]*)\")"
)
_STATA_CONTINUATION = "///"
_STATA_CHAR_MACRO = re.compile(r"`=char\(([0-9]+)\)'")
# 2,460 of the 3,212 2021 blocks and 2,327 of the 3,078 2023 blocks append a
# source truncation note to the variable line; it is a comment, not a name.
_SPSS_NAME = re.compile(
    r"^([A-Za-z][A-Za-z0-9_]*)(?:\s+/\*[^*]*(?:\*(?!/)[^*]*)*\*/)?$"
)
_SPSS_PAIR = re.compile(r"^\s*(-?[0-9]+(?:\.[0-9]+)?)\s+'((?:[^']|'')*)'\s*$")


class CodebookExtractionError(ValueError):
    """A codebook document does not parse under its registered family."""


def _open_flags(*, directory: bool) -> int:
    """Return non-following, close-on-exec flags for a source component."""

    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    except AttributeError as error:
        raise CodebookExtractionError(
            "platform lacks descriptor-relative source-path protections"
        ) from error
    if directory:
        try:
            flags |= os.O_DIRECTORY
        except AttributeError as error:
            raise CodebookExtractionError(
                "platform lacks directory-only source-path opens"
            ) from error
    else:
        # A nonblocking leaf open prevents a substituted FIFO from hanging
        # before the mandatory regular-file fstat can reject it.
        flags |= getattr(os, "O_NONBLOCK", 0)
    return flags


def _registered_path_parts(canonical_source_path: Any) -> tuple[str, ...]:
    """Return an exact, relative POSIX path with no traversal components."""

    if type(canonical_source_path) is not str or not canonical_source_path:
        raise CodebookExtractionError("invalid canonical source path")
    relative = PurePosixPath(canonical_source_path)
    parts = relative.parts
    if (
        relative.is_absolute()
        or not parts
        or any(part in ("", ".", "..") for part in parts)
        or relative.as_posix() != canonical_source_path
    ):
        raise CodebookExtractionError("non-canonical source path")
    return parts


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    """Return metadata that must remain fixed across a complete read."""

    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_stable_regular_file(
    descriptor: int,
    expected_size: int,
    display_path: Path,
) -> bytes:
    """Read one regular descriptor and reject an in-flight mutation."""

    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        raise CodebookExtractionError(
            f"codebook source is not a regular file: {display_path}"
        )
    if before.st_size != expected_size:
        raise CodebookExtractionError(
            f"codebook size mismatch: {display_path}"
        )

    chunks: list[bytes] = []
    while True:
        block = os.read(descriptor, 4 * 1024 * 1024)
        if not block:
            break
        chunks.append(block)
    after = os.fstat(descriptor)
    if _stat_identity(before) != _stat_identity(after):
        raise CodebookExtractionError(
            f"codebook source changed while reading: {display_path}"
        )
    raw = b"".join(chunks)
    if len(raw) != expected_size:
        raise CodebookExtractionError(
            f"codebook size mismatch: {display_path}"
        )
    return raw


def _read_registered_source_bytes(
    source_document: Mapping[str, Any], psid_root: Path
) -> tuple[bytes, Path]:
    """Open and authenticate a registered source beneath an anchored root.

    The root, every descendant directory, and the leaf are opened with
    ``O_NOFOLLOW``.  Each descendant is resolved relative to the already-open
    parent descriptor, so pathname replacement cannot redirect a later
    component outside the anchored tree.
    """

    parts = _registered_path_parts(source_document["canonical_source_path"])
    display_path = psid_root.joinpath(*parts)
    descriptor: int | None = None
    try:
        descriptor = os.open(os.fspath(psid_root), _open_flags(directory=True))
        for component in parts[:-1]:
            child = os.open(
                component,
                _open_flags(directory=True),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        leaf = os.open(
            parts[-1],
            _open_flags(directory=False),
            dir_fd=descriptor,
        )
        os.close(descriptor)
        descriptor = leaf
        raw = _read_stable_regular_file(
            descriptor, source_document["byte_size"], display_path
        )
    except OSError as error:
        raise CodebookExtractionError(
            f"cannot securely open codebook source: {display_path}"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)

    if sha256_bytes(raw) != source_document["sha256"]:
        raise CodebookExtractionError(
            f"codebook SHA-256 mismatch: {display_path}"
        )
    return raw, display_path


def undetermined_entry_members() -> tuple[str, ...]:
    """Return source-undetermined members serialized specifically as null.

    §19.3.2 requires a nonempty ``typed_value_unit`` on every rational or
    integer literal and on every numeric range, and requires a value-code
    range to obtain type and unit "from the complete codebook domain"; it
    likewise requires a missing literal to carry "a nonempty source-backed
    reason".  The registered corpus states neither.  A codebook value block
    displays only count, percent, value-or-range, and meaning; the two
    value-label languages display only value and meaning; and the setup
    documents declare only coordinates, labels, and numeric formats.  The
    design fixes no ``missing_reason_code`` vocabulary anywhere.  Both
    members are therefore emitted as JSON null with this declaration rather
    than filled from an invented default.  The legacy ``typed_disposition``
    slot is separately populated by a reproducible lexical candidate because
    changing that predecessor row shape would hide the very candidate that
    Amendment 11 audits; it is not source-authorized settlement.
    """

    return ("typed_value_unit", "missing_reason_code")


# Historical lexical candidate grammar.  It reproduces the predecessor lane
# but is not source authority: the same substrings occur in ordinary response
# categories and accuracy indicators.  Amendment 11 retains it only as an
# auditable candidate relation whose counterexamples force fail-closed law.
_MISSING_MEANING = re.compile(
    r"(?:\bDK\b|\bNA\b(?!\s+type\b)|\bN/A\b|\bRF\b|refus|missing|"
    r"\binap\b|not applicable|data suppressed|wild code|"
    r"don(?:'|’)?t know)",
    re.IGNORECASE,
)
# The predecessor made one contextual exception for "Not ascertained".  That
# exception does not cure the grammar's other context dependence.
_NOT_ASCERTAINED = re.compile(r"\bnot ascertained\b", re.IGNORECASE)


def is_missing_source_meaning(meaning: str) -> bool:
    """Return the predecessor lexical missing candidate, not an authority."""

    if _MISSING_MEANING.search(meaning):
        return True
    if _NOT_ASCERTAINED.search(meaning) is None:
        return False
    normalized = f" {' '.join(meaning.lower().split())} "
    return not (
        " either " in normalized or " or " in normalized or ";" in normalized
    )


def pinned_pdf_page_text(path: Path) -> tuple[str, ...]:
    """Return the §19.3.3 pinned page strings for one registered PDF."""

    completed = subprocess.run(
        ["pdftotext", *PDFTOTEXT_ARGUMENTS, str(path), "-"],
        capture_output=True,
        check=True,
    )
    pages = completed.stdout.decode("utf-8", errors="strict").split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    if not pages:
        raise CodebookExtractionError(f"pinned derivation has no page: {path}")
    return tuple(pages)


def pinned_pdf_page_text_from_bytes(raw: bytes) -> tuple[str, ...]:
    """Derive page strings from already-authenticated PDF bytes.

    Standard input binds Poppler to the exact bytes whose size and SHA-256
    were checked by :func:`extract_codebook_rows`; the registered pathname is
    never opened a second time between authentication and parsing.
    """

    completed = subprocess.run(
        ["pdftotext", *PDFTOTEXT_ARGUMENTS, "-", "-"],
        input=raw,
        capture_output=True,
        check=True,
    )
    pages = completed.stdout.decode("utf-8", errors="strict").split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    if not pages:
        raise CodebookExtractionError("pinned byte derivation has no page")
    return tuple(pages)


def pdftotext_version() -> str:
    """Return the exact Poppler version string of the local ``pdftotext``."""

    completed = subprocess.run(
        ["pdftotext", "-v"], capture_output=True, check=True
    )
    stream = completed.stderr or completed.stdout
    first = stream.decode("utf-8", errors="strict").splitlines()[0]
    return first.split()[-1]


def _fold(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.strip())


def _running_head(pages: Sequence[str]) -> str | None:
    """Return the document's modal folded first nonblank line, if any."""

    counts: dict[str, int] = {}
    for page in pages:
        for line in page.split("\n"):
            if line.strip():
                folded = _fold(line)
                counts[folded] = counts.get(folded, 0) + 1
                break
    if not counts:
        return None
    return max(counts, key=lambda key: (counts[key], key))


def _page_content(page: str, head: str | None) -> list[tuple[int, str]]:
    """Return ``(line_index, line)`` for one page after removing furniture.

    The furniture law is positional, not lexical: a page's first nonblank
    line is a running head exactly when it folds to the document's modal
    first nonblank line, and its last nonblank line is dropped exactly when
    it is the ``Page n of m`` footer or the one page that carries no such
    footer (the cover page's derivation timestamp).
    """

    rows = [
        (index, line)
        for index, line in enumerate(page.split("\n"))
        if line.strip()
    ]
    if not rows:
        return []
    if head is not None and _fold(rows[0][1]) == head:
        rows = rows[1:]
    if rows and (
        _PAGE_FOOTER.match(rows[-1][1]) or not _PAGE_FOOTER.search(page)
    ):
        rows = rows[:-1]
    return rows


def _utf8_span(page: str, first_line: int, last_line: int) -> tuple[int, int]:
    """Return the half-open UTF-8 byte span covering the given line range."""

    lines = page.split("\n")
    start = len("\n".join(lines[:first_line]).encode("utf-8"))
    if first_line:
        start += 1
    end = len("\n".join(lines[: last_line + 1]).encode("utf-8"))
    return start, end


def _pdf_locator(
    source_document_id: str,
    page: str,
    page_number: int,
    utf8_start: int,
    utf8_end: int,
) -> dict[str, Any]:
    payload = page.encode("utf-8")[utf8_start:utf8_end]
    if not payload:
        raise CodebookExtractionError("pdf page locator range is empty")
    range_sha256 = sha256_bytes(payload)
    preimage = [
        source_document_id,
        "pdf_page_text_range",
        None,
        None,
        page_number,
        utf8_start,
        utf8_end,
        range_sha256,
    ]
    return {
        "source_region_locator_id": (
            "psid-source-region:" + canonical_sha256(preimage)
        ),
        "locator_kind": "pdf_page_text_range",
        "byte_start": None,
        "byte_end": None,
        "page_number": page_number,
        "utf8_start": utf8_start,
        "utf8_end": utf8_end,
        "range_sha256": range_sha256,
    }


def _raw_locator(
    source_document_id: str,
    raw: bytes,
    byte_start: int,
    byte_end: int,
) -> dict[str, Any]:
    if not 0 <= byte_start < byte_end <= len(raw):
        raise CodebookExtractionError("locator range is not a nonempty span")
    range_sha256 = sha256_bytes(raw[byte_start:byte_end])
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
    return {
        "source_region_locator_id": (
            "psid-source-region:" + canonical_sha256(preimage)
        ),
        "locator_kind": "raw_byte_range",
        "byte_start": byte_start,
        "byte_end": byte_end,
        "page_number": None,
        "utf8_start": None,
        "utf8_end": None,
        "range_sha256": range_sha256,
    }


def source_value_lexeme(cell: str) -> str:
    """Apply the §19.3.2 source-cell function to one decoded value cell."""

    lexeme = cell.strip(" \t")
    if not lexeme:
        raise CodebookExtractionError("empty source value cell")
    if "\r" in lexeme or "\n" in lexeme:
        raise CodebookExtractionError("source value cell spans lines")
    return lexeme


def parse_source_scalar(lexeme: str) -> Fraction:
    """Parse one displayed value token as an exact rational."""

    return Fraction(lexeme.replace(",", ""))


def _decimal_places(lexeme: str) -> int:
    return len(lexeme.rsplit(".", 1)[1]) if "." in lexeme else 0


def _rational(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _canonical_scalar(value: Fraction) -> Any:
    return value.numerator if value.denominator == 1 else _rational(value)


def _value_type(*values: Fraction) -> str:
    return (
        "json_integer"
        if all(value.denominator == 1 for value in values)
        else "rational"
    )


def _normalized_entry(
    row_id: str,
    position: int,
    lexeme: str,
    meaning: str,
) -> dict[str, Any]:
    """Build one normalized entry of the §19.3.2 closed tagged union."""

    entry_ref = f"{row_id}:entry:{position}"
    match = _RANGE_LEXEME.fullmatch(lexeme)
    if match is not None:
        lower_text, upper_text = match.groups()
        lower = parse_source_scalar(lower_text)
        upper = parse_source_scalar(upper_text)
        if lower <= upper and not meaning.startswith("to "):
            step = Fraction(
                1,
                10
                ** max(
                    _decimal_places(lower_text), _decimal_places(upper_text)
                ),
            )
            value_type = _value_type(lower, upper, step)
            return {
                "entry_ref": entry_ref,
                "entry_kind": "numeric_range",
                "source_value_lexeme": lexeme,
                "value_type": value_type,
                "typed_value_unit": None,
                "inclusive_min": _canonical_scalar(lower),
                "inclusive_max": _canonical_scalar(upper),
                "step": _canonical_scalar(step),
                "source_meaning": meaning,
                "typed_disposition": value_type,
                "missing_reason_code": None,
            }
        # The apparent range is one literal followed by a meaning that opens
        # with a signed or bracket-continuation token in the value column.
        lexeme, meaning = lower_text, f"- {upper_text} {meaning}".rstrip()
    scalar = parse_source_scalar(lexeme)
    missing = is_missing_source_meaning(meaning)
    value_type = None if missing else _value_type(scalar)
    return {
        "entry_ref": entry_ref,
        "entry_kind": "literal",
        "source_value_lexeme": lexeme,
        "raw_token_hex": None,
        "source_meaning": meaning,
        "typed_disposition": "missing" if missing else value_type,
        "value_type": value_type,
        "typed_value_unit": None,
        "canonical_value": None if missing else _canonical_scalar(scalar),
        "missing_reason_code": None,
    }


def _canonical_row(
    document_id: str,
    position: int,
    raw_field_id: str,
    label: str,
    description: Sequence[str],
    format_text: str | None,
    cells: Sequence[tuple[str, str]],
    locator_ids: Sequence[str],
) -> dict[str, Any]:
    row_id = f"{document_id}#row:{position}"
    entries = [
        _normalized_entry(row_id, index, lexeme, meaning)
        for index, (lexeme, meaning) in enumerate(cells)
    ]
    return {
        "codebook_field_row_id": row_id,
        "source_document_id": document_id,
        "source_row_position": position,
        "raw_field_id": raw_field_id,
        "source_label": label,
        "source_description": "\n".join(description) or None,
        "source_format_text": format_text,
        "normalized_entries": entries,
        "normalized_entry_count": len(entries),
        "normalized_entry_domain_sha256": canonical_sha256(entries),
        "source_locator_ids": list(locator_ids),
    }


def _iter_pdf_lines(
    pages: Sequence[str],
    head: str | None,
) -> Iterator[tuple[int, int, str]]:
    for page_number, page in enumerate(pages, 1):
        for line_index, line in _page_content(page, head):
            yield page_number, line_index, line


def _extract_pdf_document(
    source_document: Mapping[str, Any],
    pages: Sequence[str],
) -> dict[str, Any]:
    document_id = source_document["source_document_id"]
    head = _running_head(pages)
    stream = list(_iter_pdf_lines(pages, head))

    locators: dict[int, dict[str, Any]] = {}
    page_first: dict[int, int] = {}
    page_last: dict[int, int] = {}
    first_field: tuple[int, int] | None = None
    for page_number, line_index, line in stream:
        if first_field is None:
            if not _FIELD_HEADER.match(line):
                continue
            first_field = (page_number, line_index)
        page_first.setdefault(page_number, line_index)
        page_last[page_number] = line_index
    if first_field is None:
        raise CodebookExtractionError(f"no field statement: {document_id}")
    for page_number, first in page_first.items():
        start, end = _utf8_span(
            pages[page_number - 1], first, page_last[page_number]
        )
        locators[page_number] = _pdf_locator(
            document_id, pages[page_number - 1], page_number, start, end
        )

    rows: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    reading_map = False
    skip_line = False
    for index, (page_number, line_index, line) in enumerate(stream):
        if (page_number, line_index) < first_field:
            continue
        if skip_line:
            skip_line = False
            continue
        header = _FIELD_HEADER.match(line)
        if header is not None:
            if pending is not None:
                rows.append(_finish(document_id, len(rows), pending))
            pending = {
                "raw_field_id": header.group(1),
                "label": header.group(2),
                "format_text": header.group(3),
                "description": [],
                "cells": [],
                "pages": [page_number],
            }
            reading_map = False
            continue
        if pending is None:
            raise CodebookExtractionError(
                f"unconsumed line before the first field: {line!r}"
            )
        if page_number not in pending["pages"]:
            pending["pages"].append(page_number)
        if _MAP_HEADER.match(line):
            reading_map = True
            continue
        if not reading_map:
            pending["description"].append(line.strip())
            continue
        row = _MAP_ROW.match(line)
        if row is not None and (row.group(1) == "-") == (row.group(2) == "-"):
            lexeme = source_value_lexeme(row.group(3))
            meaning = (row.group(4) or "").strip()
            wrapped = _WRAPPED_SEPARATOR.match(meaning)
            if " - " not in lexeme and wrapped is not None:
                follow = _following_number(stream, index)
                if follow is not None:
                    upper, tail = follow
                    sign = wrapped.group(1) or ""
                    if sign and upper.startswith("-"):
                        raise CodebookExtractionError("double upper sign")
                    lexeme = f"{lexeme} - {sign}{upper}"
                    meaning = " ".join(
                        part
                        for part in (meaning[wrapped.end() :].strip(), tail)
                        if part
                    )
                    skip_line = True
            pending["cells"].append((lexeme, meaning))
            continue
        if not pending["cells"]:
            raise CodebookExtractionError(
                f"unconsumed value-list member: {line!r}"
            )
        lexeme, meaning = pending["cells"][-1]
        pending["cells"][-1] = (
            lexeme,
            " ".join(part for part in (meaning, line.strip()) if part),
        )
    if pending is not None:
        rows.append(_finish(document_id, len(rows), pending))

    ordered = [locators[number] for number in sorted(locators)]
    return _document_derivation(
        document_id,
        {
            "decoder_kind": "pinned_pdf_page_text_derivation",
            "encoding": "UTF-8",
            "error_action": "abort",
            "bom_action": "forbidden",
            "newline_action": "preserve_pinned_page_strings",
        },
        {
            "parser_family": PDF_PARSER_FAMILY,
            "source_region_locators": ordered,
            "row_terminator": "\n",
            "row_order": "first_complete_source_occurrence",
            "unparsed_field_statement_action": "abort",
        },
        rows,
    )


def _following_number(
    stream: Sequence[tuple[int, int, str]],
    index: int,
) -> tuple[str, str] | None:
    """Return the wrapped upper bound and meaning tail on the next line."""

    if index + 1 >= len(stream):
        return None
    follow = stream[index + 1][2]
    if _FIELD_HEADER.match(follow) or _MAP_HEADER.match(follow):
        return None
    row = _MAP_ROW.match(follow)
    if row is not None and (row.group(1) == "-") == (row.group(2) == "-"):
        return None
    match = _LEADING_NUMBER.match(follow)
    if match is None:
        return None
    return match.group(1), (match.group(2) or "").strip()


def _finish(
    document_id: str,
    position: int,
    pending: Mapping[str, Any],
) -> dict[str, Any]:
    return _canonical_row(
        document_id,
        position,
        pending["raw_field_id"],
        pending["label"],
        pending["description"],
        pending["format_text"],
        pending["cells"],
        [f"__page__{number}" for number in pending["pages"]],
    )


def _document_derivation(
    document_id: str,
    decoder: Mapping[str, Any],
    segmentation: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_page = {
        locator["page_number"]: locator["source_region_locator_id"]
        for locator in segmentation["source_region_locators"]
        if locator["locator_kind"] == "pdf_page_text_range"
    }
    resolved: list[dict[str, Any]] = []
    for row in rows:
        row = dict(row)
        row["source_locator_ids"] = [
            (
                by_page[int(value.removeprefix("__page__"))]
                if isinstance(value, str) and value.startswith("__page__")
                else value
            )
            for value in row["source_locator_ids"]
        ]
        resolved.append(row)
    identifiers = [row["codebook_field_row_id"] for row in resolved]
    if len(set(identifiers)) != len(identifiers):
        raise CodebookExtractionError(f"duplicate row id: {document_id}")
    return {
        "source_document_id": document_id,
        "derivation_kind": "codebook_rows",
        "decoder": dict(decoder),
        "row_segmentation": dict(segmentation),
        "canonical_rows": resolved,
        "canonical_row_count": len(resolved),
        "canonical_row_keyset_sha256": canonical_sha256(identifiers),
        "canonical_row_domain_sha256": canonical_sha256(resolved),
    }


def _statement_spans(raw: bytes, encoding: str) -> list[tuple[int, int, str]]:
    """Return ``(byte_start, byte_end, statement)`` for each source line.

    Coordinates are exact raw-byte offsets, so a CR/LF terminator and a
    ``windows-1252`` byte that widens under UTF-8 cannot shift a locator.
    """

    spans: list[tuple[int, int, str]] = []
    position = 0
    for payload in raw.split(b"\n"):
        end = position + len(payload)
        spans.append((position, end, payload.decode(encoding, "strict")))
        position = end + 1
    return spans


def _expand_stata_char_macros(value: str) -> str:
    """Expand the ``\\`=char(n)'`` escape a Stata label uses for a quote.

    The escape is source syntax rather than content, exactly as the doubled
    quote is in an SPSS label.  The 2021 and 2023 documents use only code
    146, which is the ``windows-1252`` right single quotation mark.
    """

    def replace(match: re.Match[str]) -> str:
        code = int(match.group(1))
        if not 0 <= code <= 255:
            raise CodebookExtractionError(f"unsupported char() code: {code}")
        return bytes([code]).decode("cp1252")

    expanded = _STATA_CHAR_MACRO.sub(replace, value)
    if re.search(r"`[^']*'", expanded):
        raise CodebookExtractionError(f"unsupported macro: {expanded!r}")
    return expanded


def _extract_stata_labels(
    source_document: Mapping[str, Any],
    raw: bytes,
    encoding: str,
) -> dict[str, Any]:
    document_id = source_document["source_document_id"]
    spans = _statement_spans(raw, encoding)
    order: list[str] = []
    cells: dict[str, list[tuple[str, str]]] = {}
    regions: dict[str, list[tuple[int, int]]] = {}
    binding: dict[str, str] = {}
    bounds: tuple[int, int] | None = None
    current: str | None = None
    continued = False
    for byte_start, byte_end, line in spans:
        body = line.rstrip("\r").rstrip()
        if not body.strip():
            current, continued = None, False
            continue
        loop = _STATA_FORVALUES.search(body)
        if loop is not None:
            bounds = (int(loop.group(1)), int(loop.group(2)))
            continue
        if body.strip() == "}":
            bounds = None
            continue
        values = _STATA_VALUES.search(body)
        if values is not None:
            if binding.setdefault(values.group(2), values.group(1)) != (
                values.group(1)
            ):
                raise CodebookExtractionError("label set binds two fields")
            current, continued = None, False
            continue
        define = _STATA_DEFINE.search(body)
        if define is not None:
            current = define.group(1)
            if current not in cells:
                order.append(current)
                cells[current] = []
                regions[current] = []
            payload = body[define.end() :]
        elif continued and current is not None:
            payload = body
        else:
            raise CodebookExtractionError(f"unconsumed statement: {line!r}")
        continued = body.endswith(_STATA_CONTINUATION)
        if continued:
            payload = payload[: -len(_STATA_CONTINUATION)]
        payload = payload.split(", modify")[0]
        for match in _STATA_PAIR.finditer(payload):
            meaning = match.group("compound")
            if meaning is None:
                meaning = match.group("plain")
            meaning = _expand_stata_char_macros(meaning)
            if match.group(1) == "`n'":
                if bounds is None:
                    raise CodebookExtractionError("loop index outside a loop")
                lower, upper = bounds
                lexeme = f"{lower} - {upper}" if lower < upper else str(lower)
            else:
                lexeme = match.group(1)
            cells[current].append((lexeme, meaning))
            regions[current].append((byte_start, byte_end))
    missing = [name for name in order if name not in binding]
    if missing:
        raise CodebookExtractionError(f"unbound label set: {missing[0]}")
    return _text_document(
        document_id,
        raw,
        STATA_PARSER_FAMILY,
        "\n",
        [binding[name] for name in order],
        {binding[name]: cells[name] for name in order},
        {binding[name]: regions[name] for name in order},
        source_document,
    )


def _extract_spss_labels(
    source_document: Mapping[str, Any],
    raw: bytes,
    encoding: str,
) -> dict[str, Any]:
    document_id = source_document["source_document_id"]
    spans = _statement_spans(raw, encoding)
    order: list[str] = []
    cells: dict[str, list[tuple[str, str]]] = {}
    regions: dict[str, list[tuple[int, int]]] = {}
    field: str | None = None
    expect_name = False
    for byte_start, byte_end, line in spans:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "VALUE LABELS":
            expect_name = True
            continue
        if expect_name:
            name = _SPSS_NAME.match(stripped)
            if name is None:
                raise CodebookExtractionError(f"missing variable: {line!r}")
            field = name.group(1)
            expect_name = False
            if field not in cells:
                order.append(field)
                cells[field] = []
                regions[field] = []
            continue
        if stripped == ".":
            field = None
            continue
        if field is None:
            # The one top-level statement outside every value list is the
            # single terminal `EXECUTE.`; it defines no field or entry.
            if stripped == "EXECUTE.":
                continue
            raise CodebookExtractionError(f"unconsumed statement: {line!r}")
        pair = _SPSS_PAIR.match(line)
        if pair is None:
            raise CodebookExtractionError(f"unparsed value label: {line!r}")
        cells[field].append((pair.group(1), pair.group(2).replace("''", "'")))
        regions[field].append((byte_start, byte_end))
    return _text_document(
        document_id,
        raw,
        SPSS_PARSER_FAMILY,
        "\n",
        order,
        cells,
        regions,
        source_document,
    )


def _text_document(
    document_id: str,
    raw: bytes,
    parser_family: str,
    row_terminator: str,
    order: Sequence[str],
    cells: Mapping[str, Sequence[tuple[str, str]]],
    regions: Mapping[str, Sequence[tuple[int, int]]],
    source_document: Mapping[str, Any],
) -> dict[str, Any]:
    locators: dict[tuple[int, int], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for position, field in enumerate(order):
        identifiers: list[str] = []
        for span in regions[field]:
            if span not in locators:
                locators[span] = _raw_locator(document_id, raw, *span)
            identifier = locators[span]["source_region_locator_id"]
            if identifier not in identifiers:
                identifiers.append(identifier)
        rows.append(
            _canonical_row(
                document_id,
                position,
                field,
                field,
                (),
                None,
                cells[field],
                identifiers,
            )
        )
    ordered = [locators[span] for span in sorted(locators)]
    decoded = decode_source(raw)
    return _document_derivation(
        document_id,
        {
            "decoder_kind": "strict_source_text",
            "encoding": decoded.encoding,
            "error_action": "abort",
            "bom_action": decoded.bom_action,
            "newline_action": "preserve_source_cr_lf_crlf_sequences",
        },
        {
            "parser_family": parser_family,
            "source_region_locators": ordered,
            "row_terminator": row_terminator,
            "row_order": "first_complete_source_occurrence",
            "unparsed_field_statement_action": "abort",
        },
        rows,
    )


def extract_codebook_rows(
    source_document: Mapping[str, Any],
    psid_root: Path = DEFAULT_PSID_ROOT,
) -> dict[str, Any]:
    """Derive one codebook document's complete canonical codebook rows."""

    if source_document["document_role"] != "codebook":
        raise CodebookExtractionError("input is not a codebook document")
    raw, path = _read_registered_source_bytes(source_document, psid_root)
    if path.suffix == ".pdf":
        pages = pinned_pdf_page_text_from_bytes(raw)
        return _extract_pdf_document(source_document, pages)
    decoded = decode_source(raw)
    if path.suffix == ".do":
        return _extract_stata_labels(source_document, raw, decoded.encoding)
    if path.suffix == ".sps":
        return _extract_spss_labels(source_document, raw, decoded.encoding)
    raise CodebookExtractionError(f"unsupported codebook family: {path}")


def derive_all_codebook_documents(
    source_manifest: Sequence[Mapping[str, Any]],
    psid_root: Path = DEFAULT_PSID_ROOT,
) -> Iterator[dict[str, Any]]:
    """Yield the 47 codebook document derivations in source-manifest order."""

    for document in source_manifest:
        if document["document_role"] != "codebook":
            continue
        yield extract_codebook_rows(document, psid_root)


_DOCUMENT_ID_PREFIX = "psid-source-document:"
_LOCATOR_ID_PREFIX = "psid-source-region:"
_LOWER_HEX = frozenset("0123456789abcdef")
_DECODER_KEYS = (
    "decoder_kind",
    "encoding",
    "error_action",
    "bom_action",
    "newline_action",
)
_SEGMENTATION_KEYS = (
    "parser_family",
    "source_region_locators",
    "row_terminator",
    "row_order",
    "unparsed_field_statement_action",
)
_LOCATOR_KEYS = (
    "source_region_locator_id",
    "locator_kind",
    "byte_start",
    "byte_end",
    "page_number",
    "utf8_start",
    "utf8_end",
    "range_sha256",
)
_CODEBOOK_ROW_KEYS = (
    "codebook_field_row_id",
    "source_document_id",
    "source_row_position",
    "raw_field_id",
    "source_label",
    "source_description",
    "source_format_text",
    "normalized_entries",
    "normalized_entry_count",
    "normalized_entry_domain_sha256",
    "source_locator_ids",
)
_LITERAL_ENTRY_KEYS = (
    "entry_ref",
    "entry_kind",
    "source_value_lexeme",
    "raw_token_hex",
    "source_meaning",
    "typed_disposition",
    "value_type",
    "typed_value_unit",
    "canonical_value",
    "missing_reason_code",
)
_RANGE_ENTRY_KEYS = (
    "entry_ref",
    "entry_kind",
    "source_value_lexeme",
    "value_type",
    "typed_value_unit",
    "inclusive_min",
    "inclusive_max",
    "step",
    "source_meaning",
    "typed_disposition",
    "missing_reason_code",
)


def _require_exact_mapping(
    value: Any, expected: Sequence[str], label: str
) -> Mapping[str, Any]:
    if (
        not isinstance(value, Mapping)
        or len(value) != len(expected)
        or set(value) != set(expected)
    ):
        raise CodebookExtractionError(f"{label} keyset")
    return value


def _require_integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CodebookExtractionError(f"{label} integer")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _LOWER_HEX for character in value)
    ):
        raise CodebookExtractionError(f"{label} lowercase SHA-256")
    return value


def _require_prefixed_sha256(value: Any, prefix: str, label: str) -> str:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise CodebookExtractionError(f"{label} identity")
    _require_sha256(value[len(prefix) :], label)
    return value


def _validate_decoder(decoder: Any) -> str:
    decoder = _require_exact_mapping(decoder, _DECODER_KEYS, "decoder")
    kind = decoder["decoder_kind"]
    expected_common = {
        "error_action": "abort",
    }
    if any(decoder[key] != value for key, value in expected_common.items()):
        raise CodebookExtractionError("decoder action")
    if kind == "strict_source_text":
        if (
            decoder["encoding"] not in ("UTF-8", "windows-1252")
            or decoder["bom_action"]
            not in ("forbidden", "remove_one_source_declared_bom")
            or decoder["newline_action"]
            != "preserve_source_cr_lf_crlf_sequences"
        ):
            raise CodebookExtractionError("strict source-text decoder")
    elif kind == "pinned_pdf_page_text_derivation":
        if (
            decoder["encoding"] != "UTF-8"
            or decoder["bom_action"] != "forbidden"
            or decoder["newline_action"] != "preserve_pinned_page_strings"
        ):
            raise CodebookExtractionError("pinned PDF decoder")
    else:
        raise CodebookExtractionError("decoder kind")
    return kind


def _validate_locator(
    locator: Any,
    source_document_id: str,
    expected_kind: str,
) -> tuple[int, ...]:
    locator = _require_exact_mapping(locator, _LOCATOR_KEYS, "source locator")
    locator_kind = locator["locator_kind"]
    if locator_kind != expected_kind:
        raise CodebookExtractionError("source locator kind")
    range_sha256 = _require_sha256(
        locator["range_sha256"], "source locator range"
    )
    if locator_kind == "raw_byte_range":
        byte_start = _require_integer(locator["byte_start"], "byte start")
        byte_end = _require_integer(locator["byte_end"], "byte end")
        if byte_start >= byte_end:
            raise CodebookExtractionError("empty raw-byte locator")
        if any(
            locator[key] is not None
            for key in ("page_number", "utf8_start", "utf8_end")
        ):
            raise CodebookExtractionError("raw-byte locator coordinates")
        coordinates = (byte_start, byte_end)
    else:
        if locator_kind != "pdf_page_text_range":
            raise CodebookExtractionError("source locator kind")
        page_number = _require_integer(
            locator["page_number"], "page number", minimum=1
        )
        utf8_start = _require_integer(locator["utf8_start"], "UTF-8 start")
        utf8_end = _require_integer(locator["utf8_end"], "UTF-8 end")
        if utf8_start >= utf8_end:
            raise CodebookExtractionError("empty PDF-page locator")
        if (
            locator["byte_start"] is not None
            or locator["byte_end"] is not None
        ):
            raise CodebookExtractionError("PDF-page locator coordinates")
        coordinates = (page_number, utf8_start, utf8_end)
    preimage = [
        source_document_id,
        locator_kind,
        locator["byte_start"],
        locator["byte_end"],
        locator["page_number"],
        locator["utf8_start"],
        locator["utf8_end"],
        range_sha256,
    ]
    expected_id = _LOCATOR_ID_PREFIX + canonical_sha256(preimage)
    if locator["source_region_locator_id"] != expected_id:
        raise CodebookExtractionError("source locator identity equation")
    return coordinates


def _validate_segmentation(
    segmentation: Any,
    source_document_id: str,
    decoder_kind: str,
) -> dict[str, int]:
    segmentation = _require_exact_mapping(
        segmentation, _SEGMENTATION_KEYS, "row segmentation"
    )
    parser_family = segmentation["parser_family"]
    if parser_family == PDF_PARSER_FAMILY:
        expected_decoder = "pinned_pdf_page_text_derivation"
        locator_kind = "pdf_page_text_range"
    elif parser_family in (STATA_PARSER_FAMILY, SPSS_PARSER_FAMILY):
        expected_decoder = "strict_source_text"
        locator_kind = "raw_byte_range"
    else:
        raise CodebookExtractionError("parser family")
    if decoder_kind != expected_decoder:
        raise CodebookExtractionError("decoder/parser-family mismatch")
    if (
        segmentation["row_terminator"] != "\n"
        or segmentation["row_order"] != "first_complete_source_occurrence"
        or segmentation["unparsed_field_statement_action"] != "abort"
    ):
        raise CodebookExtractionError("row segmentation law")
    locators = segmentation["source_region_locators"]
    if not isinstance(locators, list) or not locators:
        raise CodebookExtractionError("source locator array")
    positions: dict[str, int] = {}
    coordinates: list[tuple[int, ...]] = []
    coordinate_domain: set[tuple[int, ...]] = set()
    for position, locator in enumerate(locators):
        coordinate = _validate_locator(
            locator, source_document_id, locator_kind
        )
        locator_id = locator["source_region_locator_id"]
        if locator_id in positions or coordinate in coordinate_domain:
            raise CodebookExtractionError("duplicate source locator")
        positions[locator_id] = position
        coordinates.append(coordinate)
        coordinate_domain.add(coordinate)
    if coordinates != sorted(coordinates):
        raise CodebookExtractionError("source locator order")
    return positions


def _fraction_from_canonical(value: Any, label: str) -> Fraction:
    if type(value) is int:
        return Fraction(value)
    value = _require_exact_mapping(
        value, ("numerator", "denominator"), f"{label} rational"
    )
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int:
        raise CodebookExtractionError(f"{label} rational integer")
    if denominator <= 0:
        raise CodebookExtractionError(f"{label} rational denominator")
    result = Fraction(numerator, denominator)
    if value != _rational(result):
        raise CodebookExtractionError(f"{label} noncanonical rational")
    return result


def _validate_entry(entry: Any, row_id: str, position: int) -> None:
    if not isinstance(entry, Mapping):
        raise CodebookExtractionError("normalized entry object")
    entry_kind = entry.get("entry_kind")
    if entry_kind == "literal":
        expected_keys = _LITERAL_ENTRY_KEYS
    elif entry_kind == "numeric_range":
        expected_keys = _RANGE_ENTRY_KEYS
    else:
        raise CodebookExtractionError("normalized entry kind")
    entry = _require_exact_mapping(entry, expected_keys, "normalized entry")
    if entry["entry_ref"] != f"{row_id}:entry:{position}":
        raise CodebookExtractionError("normalized entry reference")
    lexeme = entry["source_value_lexeme"]
    meaning = entry["source_meaning"]
    if not isinstance(lexeme, str) or not lexeme:
        raise CodebookExtractionError("empty source value lexeme")
    if not isinstance(meaning, str) or not meaning:
        raise CodebookExtractionError("empty source meaning")
    if entry["typed_value_unit"] is not None:
        raise CodebookExtractionError("source-undetermined value unit")
    if entry["missing_reason_code"] is not None:
        raise CodebookExtractionError("source-undetermined missing reason")

    if entry_kind == "literal":
        if entry["raw_token_hex"] is not None:
            raise CodebookExtractionError("deferred literal raw token")
        try:
            scalar = parse_source_scalar(lexeme)
        except (ValueError, ZeroDivisionError) as error:
            raise CodebookExtractionError("literal source scalar") from error
        disposition = entry["typed_disposition"]
        if disposition == "missing":
            if (
                entry["value_type"] is not None
                or entry["canonical_value"] is not None
            ):
                raise CodebookExtractionError("missing literal is typed")
            return
        expected_type = _value_type(scalar)
        if (
            disposition != expected_type
            or entry["value_type"] != expected_type
        ):
            raise CodebookExtractionError("literal disposition mismatch")
        if (
            _fraction_from_canonical(
                entry["canonical_value"], "literal canonical value"
            )
            != scalar
        ):
            raise CodebookExtractionError("literal canonical value")
        return

    match = _RANGE_LEXEME.fullmatch(lexeme)
    if match is None or meaning.startswith("to "):
        raise CodebookExtractionError("numeric-range source lexeme")
    lower_text, upper_text = match.groups()
    lower = parse_source_scalar(lower_text)
    upper = parse_source_scalar(upper_text)
    step = Fraction(
        1,
        10 ** max(_decimal_places(lower_text), _decimal_places(upper_text)),
    )
    expected_type = _value_type(lower, upper, step)
    if lower > upper:
        raise CodebookExtractionError("descending numeric range")
    if (
        entry["typed_disposition"] != expected_type
        or entry["value_type"] != expected_type
    ):
        raise CodebookExtractionError("numeric-range disposition mismatch")
    for key, expected_value in (
        ("inclusive_min", lower),
        ("inclusive_max", upper),
        ("step", step),
    ):
        if _fraction_from_canonical(entry[key], key) != expected_value:
            raise CodebookExtractionError(f"numeric-range {key}")


def validate_normalized_entry(
    entry: Mapping[str, Any], row_id: str, position: int
) -> None:
    """Validate one normalized entry without granting source authority.

    This public boundary lets downstream fail-closed audit code validate the
    complete scalar/range grammar before constructing even a fixture-only
    occurrence identity.  It deliberately delegates to the same validator
    used for authenticated document derivations so the two paths cannot
    acquire different entry semantics.
    """

    _validate_entry(entry, row_id, position)


def validate_document_derivation(derivation: Mapping[str, Any]) -> None:
    """Assert the §19.3.2 shape of one codebook document derivation.

    The two members represented as source-null are checked here rather than
    assumed.  ``typed_disposition`` remains the predecessor lexical candidate
    and is shape-validated without being promoted to source authority.  A
    separately authenticated disposition authority plus a unit authority is
    required before the relation can become §19.3.2-complete.
    """

    expected = (
        "source_document_id",
        "derivation_kind",
        "decoder",
        "row_segmentation",
        "canonical_rows",
        "canonical_row_count",
        "canonical_row_keyset_sha256",
        "canonical_row_domain_sha256",
    )
    derivation = _require_exact_mapping(
        derivation, expected, "document derivation"
    )
    source_document_id = _require_prefixed_sha256(
        derivation["source_document_id"],
        _DOCUMENT_ID_PREFIX,
        "source document",
    )
    if derivation["derivation_kind"] != "codebook_rows":
        raise CodebookExtractionError("document derivation kind")
    decoder_kind = _validate_decoder(derivation["decoder"])
    locator_positions = _validate_segmentation(
        derivation["row_segmentation"], source_document_id, decoder_kind
    )
    rows = derivation["canonical_rows"]
    if not isinstance(rows, list):
        raise CodebookExtractionError("canonical row array")
    if _require_integer(
        derivation["canonical_row_count"], "canonical row count"
    ) != len(rows):
        raise CodebookExtractionError("canonical row count")
    for position, row in enumerate(rows):
        row = _require_exact_mapping(row, _CODEBOOK_ROW_KEYS, "canonical row")
        if row["source_document_id"] != source_document_id:
            raise CodebookExtractionError("canonical row document identity")
        if (
            _require_integer(row["source_row_position"], "source row position")
            != position
        ):
            raise CodebookExtractionError("canonical row position")
        row_id = row["codebook_field_row_id"]
        if row_id != f"{source_document_id}#row:{position}":
            raise CodebookExtractionError("canonical row id")
        if not isinstance(row["raw_field_id"], str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]*", row["raw_field_id"]
        ):
            raise CodebookExtractionError("canonical raw field ID")
        if not isinstance(row["source_label"], str):
            raise CodebookExtractionError("canonical source label")
        if row["source_description"] is not None and (
            not isinstance(row["source_description"], str)
            or not row["source_description"]
        ):
            raise CodebookExtractionError("canonical source description")
        source_format = row["source_format_text"]
        if source_format is not None and (
            not isinstance(source_format, str)
            or _FIELD_HEADER.fullmatch(
                f'{row["raw_field_id"]} "{row["source_label"]}" '
                f"{source_format}"
            )
            is None
        ):
            raise CodebookExtractionError("canonical source format")
        row_locator_ids = row["source_locator_ids"]
        if not isinstance(row_locator_ids, list) or not row_locator_ids:
            raise CodebookExtractionError("empty locator array")
        if any(
            not isinstance(locator_id, str)
            or locator_id not in locator_positions
            for locator_id in row_locator_ids
        ) or len(set(row_locator_ids)) != len(row_locator_ids):
            raise CodebookExtractionError("unresolved row locator")
        row_locator_positions = [
            locator_positions[locator_id] for locator_id in row_locator_ids
        ]
        if row_locator_positions != sorted(row_locator_positions):
            raise CodebookExtractionError("row locator order")
        entries = row["normalized_entries"]
        if not isinstance(entries, list):
            raise CodebookExtractionError("normalized entry array")
        if _require_integer(
            row["normalized_entry_count"], "normalized entry count"
        ) != len(entries):
            raise CodebookExtractionError("normalized entry count")
        if row["normalized_entry_domain_sha256"] != canonical_sha256(entries):
            raise CodebookExtractionError("normalized entry digest")
        for index, entry in enumerate(entries):
            _validate_entry(entry, row_id, index)
    identifiers = [row["codebook_field_row_id"] for row in rows]
    if derivation["canonical_row_keyset_sha256"] != canonical_sha256(
        identifiers
    ):
        raise CodebookExtractionError("canonical row keyset digest")
    if derivation["canonical_row_domain_sha256"] != canonical_sha256(rows):
        raise CodebookExtractionError("canonical row domain digest")
