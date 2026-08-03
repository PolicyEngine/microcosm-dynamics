"""Independent §20 all-field terminal classifier.

The classifier consumes only the authenticated ``EvidenceCorpus`` and the
43 source-derived raw census rows.  Expected census identities are used only
after classification for validation; no expected field membership can
participate in a terminal decision.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .psid_source_compiler import (
    EXPECTED_ASSIGNMENT_SHA256,
    EXPECTED_COUNT_ARRAY_SHA256,
    EXPECTED_DENOMINATOR_SHA256,
    PADDING_ARMS,
    TERMINAL_ORDER,
    EvidenceCorpus,
    SourceField,
    canonical_sha256,
    numeric_form_order,
    parse_rendered_numeric_token,
    render_numeric_token,
)

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
CONFLICTING = "conflicting_source_numeric_format"
UNSUPPORTED = "unsupported_source_numeric_format"
INCOMPLETE = "incomplete_source_numeric_authority"

EXPECTED_COUNTS = (
    17_329,
    1_853,
    674,
    47,
    67_316,
    1_145,
    0,
    1,
    421,
    813,
)
EXPECTED_FAILURE_REASON_SHA256 = (
    "66a88e6f1138c738892eeb80af22458d57c11a8033315ceba591534ce6908324"
)

_NUMBER = r"[+-]?(?:(?:[0-9]{1,3}(?:,[0-9]{3})+)|[0-9]+)?" r"(?:\.[0-9]+)?"
_RANGE = re.compile(rf"^({_NUMBER}) - ({_NUMBER})$")
_NUM_FORMAT = re.compile(r"^NUM\(([1-9][0-9]*)\.([0-9]+)\)$")
_CHR_FORMAT = re.compile(r"^CHR\(([1-9][0-9]*)\)$")


@dataclass(frozen=True)
class _Literal:
    index: int
    lexeme: str
    scalar: Fraction
    meaning: str
    missing: bool


@dataclass(frozen=True)
class _Range:
    index: int
    lexeme: str
    minimum: Fraction
    maximum: Fraction
    step: Fraction
    meaning: str

    @property
    def count(self) -> int:
        return int((self.maximum - self.minimum) / self.step) + 1


def _parse_number(text: str) -> Fraction:
    normalized = text.replace(",", "")
    if normalized.startswith("."):
        normalized = "0" + normalized
    elif normalized.startswith("-."):
        normalized = "-0" + normalized[1:]
    elif normalized.startswith("+."):
        normalized = "+0" + normalized[1:]
    return Fraction(normalized)


def _decimal_places(text: str) -> int:
    return len(text.rsplit(".", 1)[1]) if "." in text else 0


def _normalize_entries(
    field: SourceField,
) -> tuple[tuple[_Literal, ...], tuple[_Range, ...]]:
    literals: list[_Literal] = []
    ranges: list[_Range] = []
    missing = set(field.missing_code_map_indices)
    for index, source_row in enumerate(field.code_map):
        lexeme = source_row[2]
        meaning = source_row[3]
        match = _RANGE.fullmatch(lexeme)
        if match is not None and meaning.startswith("to "):
            # The 17 retained 1969 PDF column continuations place the start
            # of the meaning in the apparent value cell.  The first fragment
            # remains the literal value; this is a syntactic rule, not a key
            # exception.
            first, second = match.groups()
            literals.append(
                _Literal(
                    index,
                    first,
                    _parse_number(first),
                    f"- {second} {meaning}",
                    index in missing,
                )
            )
            continue
        if match is None:
            literals.append(
                _Literal(
                    index,
                    lexeme,
                    _parse_number(lexeme),
                    meaning,
                    index in missing,
                )
            )
            continue
        lower_text, upper_text = match.groups()
        lower = _parse_number(lower_text)
        upper = _parse_number(upper_text)
        if (
            lower < 0
            and not upper_text.startswith(("-", "+"))
            and meaning.startswith("- ")
        ):
            upper = -upper
        step = Fraction(
            1,
            10
            ** max(
                _decimal_places(lower_text),
                _decimal_places(upper_text),
            ),
        )
        ranges.append(_Range(index, lexeme, lower, upper, step, meaning))
    return tuple(literals), tuple(ranges)


def _range_contains(item: _Range, value: Fraction) -> bool:
    return (
        item.minimum <= value <= item.maximum
        and (value - item.minimum) % item.step == 0
    )


def _ranges_overlap(first: _Range, second: _Range) -> bool:
    lower = max(first.minimum, second.minimum)
    upper = min(first.maximum, second.maximum)
    if lower > upper:
        return False
    denominator = math.lcm(
        first.minimum.denominator,
        first.step.denominator,
        second.minimum.denominator,
        second.step.denominator,
    )
    first_start = int(first.minimum * denominator)
    first_step = int(first.step * denominator)
    second_start = int(second.minimum * denominator)
    second_step = int(second.step * denominator)
    lower_integer = math.ceil(lower * denominator)
    upper_integer = math.floor(upper * denominator)
    common = math.gcd(first_step, second_step)
    if (second_start - first_start) % common:
        return False
    first_reduced = first_step // common
    second_reduced = second_step // common
    difference = (second_start - first_start) // common
    if second_reduced == 1:
        multiplier = 0
    else:
        multiplier = (
            difference * pow(first_reduced, -1, second_reduced)
        ) % second_reduced
    candidate = first_start + first_step * multiplier
    period = math.lcm(first_step, second_step)
    if candidate < lower_integer:
        candidate += (
            (lower_integer - candidate + period - 1) // period
        ) * period
    return candidate <= upper_integer


def _is_signed(token_form: str) -> bool:
    return token_form.startswith("leading_ascii_minus_signed_")


def _render(
    value: Fraction,
    token_form: str,
    arm: str,
    width: int,
    decimal_places: int,
) -> bytes | None:
    return render_numeric_token(
        value,
        width,
        decimal_places,
        token_form,
        arm,
    )


def _scalar_from_token(
    token: bytes,
    token_form: str,
    width: int,
    decimal_places: int,
) -> Fraction | None:
    values = {
        value
        for arm in PADDING_ARMS
        if (
            value := parse_rendered_numeric_token(
                token,
                width,
                decimal_places,
                token_form,
                arm,
            )
        )
        is not None
    }
    return next(iter(values)) if len(values) == 1 else None


def _literal_candidates(
    literal: _Literal,
    width: int,
    decimal_places: int,
    observations: Counter[bytes],
) -> tuple[set[bytes], bytes | None, str]:
    images = {
        image
        for token_form in numeric_form_order(decimal_places)
        for arm in PADDING_ARMS
        if (
            image := _render(
                literal.scalar,
                token_form,
                arm,
                width,
                decimal_places,
            )
        )
        is not None
    }
    strict = literal.lexeme.encode("ascii")
    if len(strict) == width and strict in images:
        return images, strict, "strict_unchanged_width"
    if len(images) == 1:
        return images, next(iter(images)), "singleton"
    observed = [image for image in images if observations[image] > 0]
    if len(observed) == 1:
        return images, observed[0], "sole_observed"
    if len(observed) > 1:
        return images, None, "mixed_observed"
    return images, None, "deferred"


def _progression_count(
    item: _Range,
    lower: Fraction | None = None,
    upper: Fraction | None = None,
    exact_decimal_places: int | None = None,
) -> int:
    """Count an arithmetic range intersection without member expansion."""

    effective_lower = (
        item.minimum if lower is None else max(item.minimum, lower)
    )
    effective_upper = (
        item.maximum if upper is None else min(item.maximum, upper)
    )
    if effective_lower > effective_upper:
        return 0
    first_index = max(
        0,
        math.ceil((effective_lower - item.minimum) / item.step),
    )
    last_index = min(
        item.count - 1,
        math.floor((effective_upper - item.minimum) / item.step),
    )
    if first_index > last_index:
        return 0
    if exact_decimal_places is None:
        return last_index - first_index + 1

    denominator = math.lcm(
        item.minimum.denominator,
        item.step.denominator,
    )
    start = int(item.minimum * denominator)
    delta = int(item.step * denominator)
    modulus = Fraction(
        denominator,
        10**exact_decimal_places,
    ).numerator
    common = math.gcd(delta, modulus)
    if (-start) % common:
        return 0
    reduced_modulus = modulus // common
    if reduced_modulus == 1:
        residue = 0
    else:
        residue = (
            ((-start) // common) * pow(delta // common, -1, reduced_modulus)
        ) % reduced_modulus
    first_match = first_index
    if reduced_modulus != 1:
        first_match += (residue - first_match) % reduced_modulus
    if first_match > last_index:
        return 0
    return (last_index - first_match) // reduced_modulus + 1


def _range_render_counts(
    item: _Range,
    token_form: str,
    width: int,
    decimal_places: int,
) -> tuple[int, int]:
    """Return exact (renderable, arm-invariant renderable) cardinalities."""

    renderable = 0
    invariant = 0
    signed = _is_signed(token_form)
    implied = token_form.endswith("_implied_decimal")
    literal_decimal = token_form.endswith("_literal_ascii_decimal")
    if not literal_decimal:
        multiplier = 10**decimal_places if implied else 1
        for negative in (False, True):
            if negative and not signed:
                continue
            sign_width = int(negative)
            for digits in range(1, width - sign_width + 1):
                minimum_magnitude = 0 if digits == 1 else 10 ** (digits - 1)
                maximum_magnitude = 10**digits - 1
                if negative:
                    lower = Fraction(-maximum_magnitude, multiplier)
                    upper = Fraction(
                        -max(1, minimum_magnitude),
                        multiplier,
                    )
                else:
                    lower = Fraction(minimum_magnitude, multiplier)
                    upper = Fraction(maximum_magnitude, multiplier)
                count = _progression_count(
                    item,
                    lower,
                    upper,
                    decimal_places if implied else 0,
                )
                renderable += count
                if digits + sign_width == width:
                    invariant += count
        return renderable, invariant

    for negative in (False, True):
        if negative and not signed:
            continue
        sign_width = int(negative)
        for digits in range(1, width - sign_width - 1):
            minimum_magnitude = 0 if digits == 1 else 10 ** (digits - 1)
            maximum_magnitude = Fraction(10**digits) - Fraction(
                1,
                10**decimal_places,
            )
            capacity = width - sign_width - digits - 1
            precision = min(decimal_places, capacity)
            if precision < 1:
                continue
            if negative:
                lower = -maximum_magnitude
                upper = -max(
                    Fraction(1, 10**decimal_places),
                    Fraction(minimum_magnitude),
                )
            else:
                lower = Fraction(minimum_magnitude)
                upper = maximum_magnitude
            count = _progression_count(
                item,
                lower,
                upper,
                precision,
            )
            renderable += count
            if sign_width + digits + 1 + precision == width:
                invariant += count
    return renderable, invariant


def _registered_relations(
    literals: Sequence[_Literal],
    registrations: Mapping[int, bytes],
) -> tuple[dict[bytes, list[_Literal]], dict[bytes, list[_Literal]]]:
    missing: dict[bytes, list[_Literal]] = defaultdict(list)
    ordinary: dict[bytes, list[_Literal]] = defaultdict(list)
    for literal in literals:
        image = registrations.get(literal.index)
        if image is None:
            continue
        relation = missing if literal.missing else ordinary
        relation[image].append(literal)
    return missing, ordinary


def _terminal(
    status: str,
    reason: str,
) -> tuple[str, str]:
    return status, reason


def _classify_numeric(
    field: SourceField,
    observations: Counter[bytes],
    literals: Sequence[_Literal],
    ranges: Sequence[_Range],
) -> tuple[str, str]:
    declaration = _NUM_FORMAT.fullmatch(field.declared_format)
    if declaration is None:
        return _terminal(
            UNSUPPORTED,
            "observed_token_outside_all_candidate_forms_or_semantics",
        )
    width, decimal_places = map(int, declaration.groups())

    if any(
        _ranges_overlap(first, second)
        for index, first in enumerate(ranges)
        for second in ranges[index + 1 :]
    ):
        return _terminal(
            CONFLICTING,
            "conflict:overlapping_numeric_ranges",
        )

    registrations: dict[int, bytes] = {}
    for literal in literals:
        _, registered, producer = _literal_candidates(
            literal,
            width,
            decimal_places,
            observations,
        )
        if producer == "mixed_observed":
            return _terminal(CONFLICTING, "mixed_literal_candidate_evidence")
        if registered is not None:
            registrations[literal.index] = registered

    missing_relation, ordinary_relation = _registered_relations(
        literals,
        registrations,
    )
    if any(len(rows) > 1 for rows in missing_relation.values()):
        return _terminal(CONFLICTING, "duplicate_registered_missing_image")
    if set(missing_relation) & set(ordinary_relation):
        return _terminal(CONFLICTING, "missing_ordinary_literal_collision")
    for rows in ordinary_relation.values():
        if (
            len({row.scalar for row in rows}) > 1
            or len({row.meaning for row in rows}) > 1
        ):
            return _terminal(CONFLICTING, "unequal_ordinary_literal_collision")

    missing_tokens = set(missing_relation)
    nonmissing_count = sum(
        frequency
        for token, frequency in observations.items()
        if token not in missing_tokens
    )
    if nonmissing_count == 0:
        if ranges:
            return _terminal(RANGE_UNESTABLISHED, "zero_nonmissing_range")
        return _terminal(VALUE_CODE_ONLY, "zero_nonmissing_literal_domain")

    ordinary_scalars = {
        token: rows[0].scalar for token, rows in ordinary_relation.items()
    }

    def token_scalar(token: bytes, token_form: str) -> Fraction | None:
        if token in ordinary_scalars:
            value = ordinary_scalars[token]
            if any(
                _render(
                    value,
                    token_form,
                    arm,
                    width,
                    decimal_places,
                )
                == token
                for arm in PADDING_ARMS
            ):
                return value
            return None
        value = _scalar_from_token(
            token,
            token_form,
            width,
            decimal_places,
        )
        if value is None:
            return None
        memberships = sum(_range_contains(item, value) for item in ranges)
        return value if memberships == 1 else None

    candidate_values = {
        token_form: {
            token: (
                None
                if token in missing_tokens
                else token_scalar(token, token_form)
            )
            for token in observations
        }
        for token_form in numeric_form_order(decimal_places)
    }
    minus_count = sum(
        frequency
        for token, frequency in observations.items()
        if token not in missing_tokens and token.lstrip(b" ").startswith(b"-")
    )
    passing_forms = []
    for token_form, values in candidate_values.items():
        covers = all(
            token in missing_tokens or value is not None
            for token, value in values.items()
        )
        sign_matches = (minus_count > 0) == _is_signed(token_form)
        if covers and sign_matches:
            passing_forms.append(token_form)
    if len(passing_forms) > 1:
        return _terminal(CONFLICTING, "multiple_passing_token_forms")
    if not passing_forms:
        individually_lawful = all(
            token in missing_tokens
            or any(
                candidate_values[token_form][token] is not None
                for token_form in numeric_form_order(decimal_places)
            )
            for token in observations
        )
        if individually_lawful:
            return _terminal(CONFLICTING, "mixed_individually_lawful_forms")
        return _terminal(
            UNSUPPORTED,
            "observed_token_outside_all_candidate_forms_or_semantics",
        )

    token_form = passing_forms[0]
    selected_values = candidate_values[token_form]
    deferred = [
        literal for literal in literals if literal.index not in registrations
    ]
    selected_images = {
        literal.index: (
            _render(
                literal.scalar,
                token_form,
                "zero_left_padding",
                width,
                decimal_places,
            ),
            _render(
                literal.scalar,
                token_form,
                "left_ascii_space_padding",
                width,
                decimal_places,
            ),
        )
        for literal in deferred
    }
    for literal in deferred:
        zero_image, space_image = selected_images[literal.index]
        if zero_image is not None and zero_image == space_image:
            registrations[literal.index] = zero_image

    zero_accepts = True
    space_accepts = True
    diagnostic_count = 0
    observed_invariant = True
    for token, frequency in observations.items():
        if token in missing_tokens:
            continue
        value = selected_values[token]
        if value is None:
            raise AssertionError(
                "selected token form lacks an observed scalar"
            )
        zero_image = _render(
            value,
            token_form,
            "zero_left_padding",
            width,
            decimal_places,
        )
        space_image = _render(
            value,
            token_form,
            "left_ascii_space_padding",
            width,
            decimal_places,
        )
        if zero_image != space_image:
            diagnostic_count += frequency
            observed_invariant = False
        zero_accepts &= zero_image == token
        space_accepts &= space_image == token

    if diagnostic_count > 0:
        if not space_accepts or zero_accepts:
            return _terminal(UNSUPPORTED, "excluded_or_mixed_padding_arm")
        for literal in deferred:
            _, space_image = selected_images[literal.index]
            if space_image is None:
                return _terminal(
                    UNSUPPORTED,
                    "selected_space_literal_unrenderable",
                )
            registrations[literal.index] = space_image
        if not ranges:
            return _terminal(VALUE_CODE_ONLY, "diagnostic_literal_domain")
        range_counts = [
            _range_render_counts(
                item,
                token_form,
                width,
                decimal_places,
            )
            for item in ranges
        ]
        if any(renderable == 0 for renderable, _ in range_counts):
            return _terminal(
                UNSUPPORTED,
                "selected_space_range_zero_renderable",
            )
        if any(
            renderable < item.count
            for item, (renderable, _) in zip(
                ranges,
                range_counts,
                strict=True,
            )
        ):
            return _terminal(PARTIAL_RANGE, "partial_range")
        return _terminal(COMPILED, "diagnostic_space")

    structural = (
        width == 1
        and decimal_places == 0
        and token_form == "unsigned_ascii_integer"
    ) or (
        token_form == "unsigned_literal_ascii_decimal"
        and width == decimal_places + 2
    )
    if structural:
        for literal in deferred:
            zero_image, space_image = selected_images[literal.index]
            if zero_image is None or zero_image != space_image:
                return _terminal(
                    UNSUPPORTED, "structural_literal_unrenderable"
                )
            registrations[literal.index] = zero_image
        if not ranges:
            return _terminal(VALUE_CODE_ONLY, "structural_literal_domain")
        range_counts = [
            _range_render_counts(
                item,
                token_form,
                width,
                decimal_places,
            )
            for item in ranges
        ]
        if any(renderable == 0 for renderable, _ in range_counts):
            return _terminal(
                UNSUPPORTED,
                "selected_space_range_zero_renderable",
            )
        if any(
            renderable < item.count
            for item, (renderable, _) in zip(
                ranges,
                range_counts,
                strict=True,
            )
        ):
            return _terminal(PARTIAL_RANGE, "partial_range")
        return _terminal(PADDING_UNDERDETERMINED, "structural_no_arm")

    if not ranges:
        return _terminal(
            INCOMPLETE,
            "literal_only_zero_diagnostic_padding_capacity",
        )

    range_counts = [
        _range_render_counts(
            item,
            token_form,
            width,
            decimal_places,
        )
        for item in ranges
    ]
    ambiguous_literals = 0
    for literal in deferred:
        zero_image, space_image = selected_images[literal.index]
        if zero_image is not None and zero_image == space_image:
            registrations[literal.index] = zero_image
        elif zero_image is not None and space_image is not None:
            ambiguous_literals += 1
        else:
            return _terminal(UNSUPPORTED, "finite_literal_unrenderable")

    all_renderable = all(
        renderable == item.count
        for item, (renderable, _) in zip(
            ranges,
            range_counts,
            strict=True,
        )
    )
    ambiguous_count = ambiguous_literals + sum(
        renderable - invariant for renderable, invariant in range_counts
    )
    every_range_has_invariant = all(
        invariant > 0 for _, invariant in range_counts
    )
    if all_renderable and ambiguous_count == 0:
        return _terminal(
            PADDING_UNDERDETERMINED,
            "finite_complete_equality",
        )
    if (
        ambiguous_count > 0
        and every_range_has_invariant
        and observed_invariant
    ):
        return _terminal(FINITE_ARM_AMBIGUOUS, "finite_arm_ambiguous")
    return _terminal(
        INCOMPLETE,
        "finite_no_arm_no_lawful_complete_disposition",
    )


def _observations_by_key(
    raw_derivations: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, str], Counter[bytes]]:
    observations: dict[tuple[int, str], Counter[bytes]] = {}
    for derivation in raw_derivations:
        for row in derivation["field_census_rows"]:
            key = (row["interview_wave"], row["raw_field_id"])
            if key in observations:
                raise ValueError(f"duplicate raw field census: {key}")
            observations[key] = Counter(
                {
                    bytes.fromhex(token_row["raw_token_hex"]): token_row[
                        "frequency"
                    ]
                    for token_row in row["observed_token_rows"]
                }
            )
    return observations


def _classify_character(
    field: SourceField,
    observations: Counter[bytes],
    literals: Sequence[_Literal],
    ranges: Sequence[_Range],
) -> tuple[str, str]:
    declaration = _CHR_FORMAT.fullmatch(field.declared_format)
    if declaration is None:
        return _terminal(UNSUPPORTED, "character_raw_replay_unknown_token")
    width = int(declaration.group(1))
    registered = {
        literal.lexeme.encode("ascii")
        for literal in literals
        if len(literal.lexeme.encode("ascii")) == width
    }
    # Unknown physical content is an earlier unsupported failure than the
    # inert character-range branch.
    if set(observations) - registered:
        return _terminal(UNSUPPORTED, "character_raw_replay_unknown_token")
    if ranges:
        return _terminal(RANGE_UNESTABLISHED, "character_range")
    return _terminal(VALUE_CODE_ONLY, "character_literal_domain")


def _failure_reason_rows(
    classifications: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[list[Any]]] = defaultdict(list)
    for row in classifications:
        if row["derivation_status"] not in {
            CONFLICTING,
            UNSUPPORTED,
            INCOMPLETE,
        }:
            continue
        grouped[(row["derivation_status"], row["resolution_reason"])].append(
            [row["interview_wave"], row["raw_field_id"]]
        )
    terminal_position = {
        status: index for index, status in enumerate(TERMINAL_ORDER)
    }
    return [
        {
            "derivation_status": status,
            "field_keys": grouped[(status, reason)],
            "resolution_reason": reason,
        }
        for status, reason in sorted(
            grouped,
            key=lambda pair: (terminal_position[pair[0]], pair[1]),
        )
    ]


def classify_complete_corpus(
    corpus: EvidenceCorpus,
    raw_derivations: Sequence[Mapping[str, Any]],
    *,
    validate_expected: bool = True,
) -> dict[str, Any]:
    """Classify the complete source denominator and return census digests.

    ``raw_derivations`` is the return of ``derive_all_raw_censuses``.  Rows
    remain in ``corpus.fields`` order, which is the §20.3.7 denominator order.
    """

    observations = _observations_by_key(raw_derivations)
    field_keys = [list(field.key) for field in corpus.fields]
    if len(observations) != len(corpus.fields):
        raise ValueError(
            "raw census does not exact-cover the field denominator"
        )
    if set(observations) != {field.key for field in corpus.fields}:
        raise ValueError("raw census keyset differs from field denominator")

    classifications: list[dict[str, Any]] = []
    assignment: list[list[Any]] = []
    for field in corpus.fields:
        literals, ranges = _normalize_entries(field)
        if _CHR_FORMAT.fullmatch(field.declared_format):
            status, reason = _classify_character(
                field,
                observations[field.key],
                literals,
                ranges,
            )
        else:
            status, reason = _classify_numeric(
                field,
                observations[field.key],
                literals,
                ranges,
            )
        classifications.append(
            {
                "interview_wave": field.interview_wave,
                "raw_field_id": field.raw_field_id,
                "derivation_status": status,
                "resolution_reason": reason,
            }
        )
        assignment.append([field.interview_wave, field.raw_field_id, status])

    counts = Counter(row["derivation_status"] for row in classifications)
    count_rows = [
        {"derivation_status": status, "field_count": counts[status]}
        for status in TERMINAL_ORDER
    ]
    failure_reason_rows = _failure_reason_rows(classifications)
    result = {
        "classification_rows": classifications,
        "classification_row_count": len(classifications),
        "denominator_sha256": canonical_sha256(field_keys),
        "count_rows": count_rows,
        "count_array_sha256": canonical_sha256(count_rows),
        "ordered_assignment_sha256": canonical_sha256(assignment),
        "failure_reason_rows": failure_reason_rows,
        "failure_reason_rows_sha256": canonical_sha256(failure_reason_rows),
    }
    if validate_expected:
        actual_counts = tuple(counts[status] for status in TERMINAL_ORDER)
        if actual_counts != EXPECTED_COUNTS:
            raise ValueError(f"terminal count mismatch: {actual_counts!r}")
        expected = {
            "denominator_sha256": EXPECTED_DENOMINATOR_SHA256,
            "count_array_sha256": EXPECTED_COUNT_ARRAY_SHA256,
            "ordered_assignment_sha256": EXPECTED_ASSIGNMENT_SHA256,
            "failure_reason_rows_sha256": (EXPECTED_FAILURE_REASON_SHA256),
        }
        for member, expected_value in expected.items():
            if result[member] != expected_value:
                raise ValueError(
                    f"{member} mismatch: {result[member]} != {expected_value}"
                )
    return result
