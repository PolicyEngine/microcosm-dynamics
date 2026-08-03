"""Amendment 10 (§24) unit authority: prose-to-unit derivation and census.

§19.3.2 requires every member of a numeric-required row's normalized range
subprojection ``R`` to carry "one common ``rational | json_integer`` type and
one common nonempty unit", and §19.3.2 fixes the sole source of that unit as
"the complete codebook domain".  No registered codebook value block,
value-label file, or setup statement carries a unit anywhere in the corpus,
so the only unit-bearing bytes any registered source holds are the free prose
of the codebook field description.

This module is the §24 machinery.  It is deliberately pure: it consumes the
already-derived codebook field description together with the field's ratified
§20.3.7 terminal, and returns the successor terminal.  It reads no PDF, opens
no evidence artifact, and imports nothing from the source compiler, so the
law it encodes can be exercised and reviewed without the derivation stack.

Three closed stages, in order:

``normalize_description``
    Fold the pinned page-text description to one space-separated line.
``extract_statements`` / ``statement_predicate``
    Select the value-denotation statements under the closed anchor set.
``statement_disposition`` / ``field_unit``
    Apply the closed clause table under maximal munch and fail closed on an
    absent, defeated, or conflicting reading.

``successor_terminal`` then applies §20.3.5's ratified failure precedence —
conflict, then unsupported, then incomplete — so a field whose ratified
terminal already belongs to an earlier failure class never moves.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

__all__ = [
    "ANCHORS",
    "ARTIFACT_PARTITION",
    "CLAUSE_TABLE",
    "COMPILED_TERMINALS",
    "DENOTATION_VERBS",
    "FAILURE_TERMINALS",
    "NO_UNIT",
    "TERMINAL_ORDER",
    "UNIT_ABSENT_RESOLUTION_REASON",
    "UNIT_VOCABULARY",
    "VALUE_SUBJECT_ANCHORS",
    "VARIABLE_DENOTATION_ANCHORS",
    "artifact_of_position",
    "canonical_json_bytes",
    "canonical_sha256",
    "clause_occurrences",
    "extract_statements",
    "failure_reason_rows",
    "field_unit",
    "normalize_description",
    "statement_anchor",
    "statement_disposition",
    "statement_predicate",
    "statement_table",
    "successor_census",
    "successor_terminal",
]


# --------------------------------------------------------------------------
# §10.1 canonical serialization
# --------------------------------------------------------------------------


def canonical_json_bytes(value: Any) -> bytes:
    """Return the §10.1 canonical JSON encoding with one terminal LF."""

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


def canonical_sha256(value: Any) -> str:
    """Hash a standalone §10.1 canonical JSON value."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


# --------------------------------------------------------------------------
# Stage 1 — description normalization
# --------------------------------------------------------------------------

_SPACE_RUN = re.compile(r"[ ]+")


def normalize_description(description: str | None) -> str:
    """Return the §24 normalized description of one codebook field row.

    Exactly three steps, and no other:

    1. every LF becomes one U+0020, because the derived description retains
       the pinned page's own line breaks and those breaks are a ``-layout``
       rendering artifact rather than a source semantic;
    2. every maximal run of U+0020 becomes one U+0020, because ``-layout``
       column alignment inserts runs whose width depends on the page, not on
       the sentence;
    3. leading and trailing U+0020 are removed.

    No case folding, punctuation removal, Unicode normalization, or quote
    substitution occurs: each of those would merge byte-distinct source
    spellings and so would silently widen the closed clause table.
    """

    if description is None:
        return ""
    return _SPACE_RUN.sub(" ", description.replace("\n", " ")).strip()


# --------------------------------------------------------------------------
# Stage 2 — value-denotation statement extraction
# --------------------------------------------------------------------------

#: Openers whose grammatical subject is the variable's value or values.
VALUE_SUBJECT_ANCHORS: tuple[str, ...] = (
    "The values for this variable ",
    "Values for this variable ",
    "values for this variable ",
    "The value for this variable ",
    "the value for this variable ",
)

#: Openers whose subject is the variable and whose verb is the denotation
#: verb.  ``This variable is``/``was``/``contains`` are provenance rather than
#: denotation and are deliberately outside the closed set.
VARIABLE_DENOTATION_ANCHORS: tuple[str, ...] = (
    "This variable represents ",
    "this variable represents ",
)

ANCHORS: tuple[str, ...] = VALUE_SUBJECT_ANCHORS + VARIABLE_DENOTATION_ANCHORS

#: Verbs that make a value-subject opener a whole-domain denotation.
DENOTATION_VERBS: tuple[str, ...] = ("represent ", "represents ")


def _statement_end(text: str, index: int) -> int:
    """Return the exclusive end of the statement beginning at *index*."""

    cursor = index
    while True:
        stop = text.find(".", cursor)
        if stop < 0:
            return len(text)
        if stop + 1 == len(text) or text[stop + 1] == " ":
            return stop + 1
        cursor = stop + 1


def extract_statements(text: str) -> tuple[str, ...]:
    """Return the ordered value-denotation statements of *text*.

    A statement begins at an anchor occurrence that starts the text or is
    immediately preceded by U+0020, takes the longest anchor matching at that
    index, and ends at the first ``.`` followed by U+0020 or ending the text.
    An anchor occurrence inside an already-selected anchor cannot open a
    second statement, so ``The value for this variable represents`` yields one
    statement rather than also yielding its ``this variable represents`` tail.
    """

    found: list[str] = []
    index = 0
    guard = 0
    while index < len(text):
        if index < guard or (index and text[index - 1] != " "):
            index += 1
            continue
        anchor = max(
            (a for a in ANCHORS if text.startswith(a, index)),
            key=len,
            default=None,
        )
        if anchor is None:
            index += 1
            continue
        found.append(text[index : _statement_end(text, index)])
        guard = index + len(anchor)
        index += 1
    return tuple(found)


def statement_anchor(statement: str) -> str:
    """Return the longest closed anchor that opens *statement*."""

    return max((a for a in ANCHORS if statement.startswith(a)), key=len)


def statement_predicate(statement: str) -> str | None:
    """Return the whole-domain denotation predicate, or ``None``.

    A value-subject opener denotes the whole domain only when its verb is
    the denotation verb.  ``The values for this variable in the range
    00001-99998 represent ...`` names a unit for a stated subrange and cannot
    establish §19.3.2's unit common to *every* member of ``R``, so it has no
    predicate here and fails closed.
    """

    anchor = statement_anchor(statement)
    rest = statement[len(anchor) :]
    if anchor in VARIABLE_DENOTATION_ANCHORS:
        return rest
    for verb in DENOTATION_VERBS:
        if rest.startswith(verb):
            return rest[len(verb) :]
    return None


# --------------------------------------------------------------------------
# Stage 3 — the closed clause table
# --------------------------------------------------------------------------

#: Sentinel disposition for a clause that defeats a unit reading.
NO_UNIT = "no_unit_derivable"

#: The closed canonical unit vocabulary §24 fixes.  §19.3.2 fixes none, so
#: every member here is introduced by §24 and nothing outside it is lawful.
UNIT_VOCABULARY: tuple[str, ...] = (
    "count",
    "day",
    "hour",
    "hour_per_week",
    "hour_per_year",
    "mile",
    "mile_per_year",
    "minute",
    "month",
    "percent",
    "united_states_dollar",
    "united_states_dollar_per_hour",
    "week",
    "year",
)

#: The closed clause table.  Displayed order is the ratified order; matching
#: is order-independent because maximal munch resolves nesting.
CLAUSE_TABLE: tuple[tuple[str, str], ...] = (
    # money
    ("dollars and cents per hour", "united_states_dollar_per_hour"),
    ("dollars and cents", "united_states_dollar"),
    ("dollar and cents", "united_states_dollar"),
    ("whole dollars", "united_states_dollar"),
    ("dollar amount", "united_states_dollar"),
    ("dollar income amount", "united_states_dollar"),
    ("dollar value", "united_states_dollar"),
    ("dollar lump sum amount", "united_states_dollar"),
    ("value in dollars", "united_states_dollar"),
    ("tax credit dollars", "united_states_dollar"),
    # time
    ("number of hours per week", "hour_per_week"),
    ("hours per week", "hour_per_week"),
    ("weekly work hours", "hour_per_week"),
    ("hours per year", "hour_per_year"),
    ("number of hours (0001-2080) per year", "hour_per_year"),
    ("number of hours", "hour"),
    ("annual hours", "hour"),
    ("annual work hours", "hour"),
    ("annual overtime hours", "hour"),
    ("annualized hours", "hour"),
    ("annualized work hours", "hour"),
    ("annual extra job hours", "hour"),
    ("annual hours worked", "hour"),
    ("extra job hours", "hour"),
    ("number of weeks", "week"),
    ("number of reported weeks", "week"),
    ("expressed as weeks", "week"),
    ("duration in weeks", "week"),
    ("total weeks", "week"),
    ("weeks worked", "week"),
    ("number of days", "day"),
    ("number of reported days", "day"),
    ("number of months", "month"),
    ("number of reported months", "month"),
    ("number of years", "year"),
    ("number of additional years", "year"),
    ("in whole years", "year"),
    ("in years", "year"),
    ("number of minutes", "minute"),
    # length
    ("number of miles", "mile"),
    ("number of miles per year", "mile_per_year"),
    # dimensionless
    ("number of", "count"),
    ("percent", "percent"),
    ("percentage", "percent"),
    ("percentange", "percent"),
    # defeating clauses
    ("the last two digits", NO_UNIT),
    ("ID number of", NO_UNIT),
    ("interview number of", NO_UNIT),
    ("marginal tax rate", NO_UNIT),
    ("value per room", NO_UNIT),
    ("income/needs ratio", NO_UNIT),
    ("the ratio of", NO_UNIT),
    ('number of Wife/"Wife" missed', NO_UNIT),
)


def clause_occurrences(predicate: str) -> tuple[tuple[int, int, str], ...]:
    """Return the surviving ``(start, end, unit)`` clause occurrences.

    Every clause is matched as an exact byte substring at every position.
    An occurrence strictly contained in a strictly longer occurrence is
    dropped, so ``dollars and cents per hour`` consumes the ``dollars and
    cents`` inside it and a nested clause never manufactures a conflict.
    """

    hits: list[tuple[int, int, str]] = []
    for clause, unit in CLAUSE_TABLE:
        start = 0
        while True:
            index = predicate.find(clause, start)
            if index < 0:
                break
            hits.append((index, index + len(clause), unit))
            start = index + 1
    return tuple(
        hit
        for position, hit in enumerate(hits)
        if not any(
            other_position != position
            and other[0] <= hit[0]
            and hit[1] <= other[1]
            and other[1] - other[0] > hit[1] - hit[0]
            for other_position, other in enumerate(hits)
        )
    )


def statement_disposition(statement: str) -> tuple[str | None, str]:
    """Return ``(unit, reason)`` for one extracted statement."""

    predicate = statement_predicate(statement)
    if predicate is None:
        return None, "not_a_whole_domain_denotation"
    units = {unit for _, _, unit in clause_occurrences(predicate)}
    if not units:
        return None, "no_unit_naming_clause"
    if NO_UNIT in units:
        return None, "defeating_clause"
    if len(units) > 1:
        return None, "conflicting_unit_clauses"
    return next(iter(units)), "unit_naming_clause"


def field_unit(description: str | None) -> tuple[str | None, str]:
    """Return one codebook field's ``(typed_value_unit, reason)``.

    A field takes a unit exactly when its statements name one unit and no
    other.  Zero statements, zero units, or two distinct units all fail
    closed, because §19.3.2 needs one unit common to every member of ``R``.
    """

    found = extract_statements(normalize_description(description))
    if not found:
        return None, "no_denotation_statement"
    units = {
        unit
        for unit, _ in (statement_disposition(s) for s in found)
        if unit is not None
    }
    if not units:
        return None, "no_statement_names_a_unit"
    if len(units) > 1:
        return None, "conflicting_statement_units"
    return next(iter(units)), "derived_from_denotation_statement"


# --------------------------------------------------------------------------
# The successor terminal function
# --------------------------------------------------------------------------

COMPILED = "compiled_source_numeric_grammar"
PADDING_UNDERDETERMINED = (
    "compiled_source_numeric_grammar_padding_underdetermined_exact_replay"
)
FINITE_ARM_AMBIGUOUS = (
    "compiled_source_numeric_grammar_finite_domain_arm_ambiguous_exact_replay"
)
PARTIAL_RANGE = "compiled_source_numeric_grammar_partial_range_exact_replay"
VALUE_CODE_ONLY = "value_code_domain_no_numeric_grammar"
RANGE_UNESTABLISHED = "value_code_range_physical_rendering_unestablished"
NONNUMERIC = "nonnumeric_source_field_outside_numeric_grammar"
CONFLICTING = "conflicting_source_numeric_format"
UNSUPPORTED = "unsupported_source_numeric_format"
INCOMPLETE = "incomplete_source_numeric_authority"

#: §20.3.7's canonical serialization order.
TERMINAL_ORDER: tuple[str, ...] = (
    COMPILED,
    PADDING_UNDERDETERMINED,
    FINITE_ARM_AMBIGUOUS,
    PARTIAL_RANGE,
    VALUE_CODE_ONLY,
    RANGE_UNESTABLISHED,
    NONNUMERIC,
    CONFLICTING,
    UNSUPPORTED,
    INCOMPLETE,
)

#: The four passing compiled terminals; exactly the numeric-required rows
#: with nonempty ``R`` that reach §19.3.2's compile block.
COMPILED_TERMINALS: frozenset[str] = frozenset(
    {COMPILED, PADDING_UNDERDETERMINED, FINITE_ARM_AMBIGUOUS, PARTIAL_RANGE}
)

#: The §24 resolution reason for a field that moves under the unit test.
UNIT_ABSENT_RESOLUTION_REASON = (
    "unresolved_typed_value_unit_no_source_authority"
)

#: The three closed failure terminals in §20.3.5 precedence order.
FAILURE_TERMINALS: tuple[str, ...] = (CONFLICTING, UNSUPPORTED, INCOMPLETE)

#: The six pinned §20.3.7 evidence artifacts and their field counts.  The
#: denominator order is artifact-major, so a row's zero-based denominator
#: position alone fixes its artifact column.
ARTIFACT_PARTITION: tuple[tuple[str, int], ...] = (
    ("wave1968_ry1968_1974_early_totals_v1", 3_868),
    ("ry1975_1977_spouse_concept_seam_v1", 1_838),
    ("ry1978_1992_pre_er_totals_v1", 15_745),
    ("ry1993_2001_er_transition_v1", 15_983),
    ("ry2002_2014_modern_bc_de_v1", 33_154),
    ("ry2015_2022_exclusion_lineage_v1", 19_011),
)


def artifact_of_position(position: int) -> str:
    """Return the evidence artifact holding one denominator position."""

    cursor = 0
    for name, size in ARTIFACT_PARTITION:
        cursor += size
        if position < cursor:
            return name
    raise ValueError(f"position outside the denominator: {position}")


def successor_terminal(
    ratified_status: str, unit: str | None
) -> tuple[str, bool]:
    """Return ``(successor_status, moved)`` for one field.

    §20.3.5 replaces §19.3.2's failure mapping with three mutually exclusive
    classes evaluated in precedence order — conflict, then unsupported, then
    incomplete — and §20.3.7 step 5 applies that precedence.  An unresolved
    unit is an *incomplete*-class predicate, so it can only move a field that
    is not already in an earlier class.  The only fields it can reach are
    therefore the four passing compiled terminals: every other terminal is
    either outside §19.3.2's numeric-required scope (empty ``R``, diverted
    before the compile block, or outside numeric grammar) or already at or
    before the incomplete class.
    """

    if ratified_status not in COMPILED_TERMINALS:
        return ratified_status, False
    if unit is not None:
        return ratified_status, False
    return INCOMPLETE, True


# --------------------------------------------------------------------------
# The successor census
# --------------------------------------------------------------------------

_ROW_KEYS = (
    "derivation_status",
    "interview_wave",
    "raw_field_id",
    "resolution_reason",
    "source_description",
)


def _row_view(row: Mapping[str, Any]) -> tuple[int, str, str, str, str | None]:
    missing = [key for key in _ROW_KEYS if key not in row]
    if missing:
        raise ValueError(f"field row is missing {missing!r}")
    return (
        int(row["interview_wave"]),
        str(row["raw_field_id"]),
        str(row["derivation_status"]),
        str(row["resolution_reason"]),
        row["source_description"],
    )


def failure_reason_rows(
    assignment: Sequence[tuple[int, str, str, str]],
) -> list[dict[str, Any]]:
    """Return the closed failure-reason artifact rows.

    Rows are ordered by failure-terminal precedence and then by reason
    lexically, exactly as §20.3.7 fixes for the ratified seven-row artifact.
    """

    grouped: dict[tuple[str, str], list[list[Any]]] = {}
    for wave, field, status, reason in assignment:
        if status not in FAILURE_TERMINALS:
            continue
        grouped.setdefault((status, reason), []).append([wave, field])
    rows: list[dict[str, Any]] = []
    for terminal in FAILURE_TERMINALS:
        for status, reason in sorted(
            (key for key in grouped if key[0] == terminal),
            key=lambda key: key[1],
        ):
            rows.append(
                {
                    "derivation_status": status,
                    "resolution_reason": reason,
                    "field_keys": grouped[(status, reason)],
                }
            )
    return rows


def successor_census(
    field_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the complete §24 successor census over the field denominator.

    ``field_rows`` are the ratified §20.3.7 rows in denominator order, each
    carrying exactly ``interview_wave``, ``raw_field_id``,
    ``derivation_status``, ``resolution_reason``, and the derived codebook
    ``source_description``.  Every count, digest, matrix cell, movement row,
    and failure-reason row in the return is recomputed here rather than
    asserted, and the denominator digest is recomputed from the same input
    so that its invariance is a result rather than an assumption.
    """

    keys: list[list[Any]] = []
    assignment: list[list[Any]] = []
    successor_reasons: list[tuple[int, str, str, str]] = []
    movements: list[dict[str, Any]] = []
    counts = dict.fromkeys(TERMINAL_ORDER, 0)
    ratified_counts = dict.fromkeys(TERMINAL_ORDER, 0)
    matrix: dict[tuple[str, str], int] = {}
    status_keys: dict[str, list[list[Any]]] = {
        status: [] for status in TERMINAL_ORDER
    }
    unit_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    seen: set[tuple[int, str]] = set()
    for position, row in enumerate(field_rows):
        wave, field, status, reason, description = _row_view(row)
        if status not in counts:
            raise ValueError(f"unknown ratified terminal: {status!r}")
        if (wave, field) in seen:
            raise ValueError(f"duplicate field key: {(wave, field)!r}")
        seen.add((wave, field))
        unit, unit_reason = field_unit(description)
        if unit is not None and unit not in UNIT_VOCABULARY:
            raise ValueError(f"unit outside the vocabulary: {unit!r}")
        successor, moved = successor_terminal(status, unit)
        artifact = artifact_of_position(position)
        keys.append([wave, field])
        assignment.append([wave, field, successor])
        status_keys[successor].append([wave, field])
        matrix[(successor, artifact)] = (
            matrix.get((successor, artifact), 0) + 1
        )
        ratified_counts[status] += 1
        counts[successor] += 1
        unit_counts[unit or NO_UNIT] = unit_counts.get(unit or NO_UNIT, 0) + 1
        reason_counts[unit_reason] = reason_counts.get(unit_reason, 0) + 1
        successor_reasons.append(
            (
                wave,
                field,
                successor,
                UNIT_ABSENT_RESOLUTION_REASON if moved else reason,
            )
        )
        if moved:
            movements.append(
                {
                    "interview_wave": wave,
                    "raw_field_id": field,
                    "source_artifact": artifact,
                    "ratified_status": status,
                    "successor_status": successor,
                    "resolution_reason": UNIT_ABSENT_RESOLUTION_REASON,
                    "unit_absence_reason": unit_reason,
                }
            )
    count_rows = [
        {"derivation_status": status, "field_count": counts[status]}
        for status in TERMINAL_ORDER
    ]
    reason_rows = failure_reason_rows(successor_reasons)
    return {
        "field_count": len(keys),
        "denominator_sha256": canonical_sha256(keys),
        "count_rows": count_rows,
        "count_array_sha256": canonical_sha256(count_rows),
        "ordered_assignment_sha256": canonical_sha256(assignment),
        "ratified_count_rows": [
            {
                "derivation_status": status,
                "field_count": ratified_counts[status],
            }
            for status in TERMINAL_ORDER
        ],
        "status_matrix_rows": [
            {
                "derivation_status": status,
                "artifact_field_counts": [
                    matrix.get((status, name), 0)
                    for name, _size in ARTIFACT_PARTITION
                ],
                "field_count": counts[status],
                "field_key_sha256": canonical_sha256(status_keys[status]),
            }
            for status in TERMINAL_ORDER
        ],
        "failure_reason_rows": reason_rows,
        "failure_reason_row_count": len(reason_rows),
        "failure_reason_rows_byte_count": len(
            canonical_json_bytes(reason_rows)
        ),
        "failure_reason_rows_sha256": canonical_sha256(reason_rows),
        "movement_rows": movements,
        "movement_row_count": len(movements),
        "movement_rows_sha256": canonical_sha256(movements),
        "movement_key_sha256": canonical_sha256(
            [[row["interview_wave"], row["raw_field_id"]] for row in movements]
        ),
        "unit_field_counts": dict(sorted(unit_counts.items())),
        "unit_reason_field_counts": dict(sorted(reason_counts.items())),
    }


def statement_table(
    field_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return the complete spelling table over the codebook corpus.

    One row per distinct statement byte string, carrying its disposition,
    its no-unit reason, the number of fields whose description contains it,
    and the first field key in denominator order that carries it.
    """

    order: list[str] = []
    counts: dict[str, int] = {}
    witness: dict[str, Sequence[Any]] = {}
    for row in field_rows:
        wave, field, _status, _reason, description = _row_view(row)
        for statement in set(
            extract_statements(normalize_description(description))
        ):
            if statement not in counts:
                order.append(statement)
                counts[statement] = 0
                witness[statement] = [wave, field]
            counts[statement] += 1
    table: list[dict[str, Any]] = []
    for statement in sorted(order):
        unit, reason = statement_disposition(statement)
        table.append(
            {
                "statement": statement,
                "typed_value_unit": unit,
                "disposition_reason": reason,
                "field_count": counts[statement],
                "witness_field_key": list(witness[statement]),
            }
        )
    return table
