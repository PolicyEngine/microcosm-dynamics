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
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .psid_analytic_partition import (
    complement_runs,
    merge_runs,
    subtract_runs,
)
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


@dataclass(frozen=True)
class FieldDerivationDetails:
    """Source-derived field details needed by artifact serialization."""

    interview_wave: int
    raw_field_id: str
    normalized_literals: tuple[dict[str, Any], ...]
    normalized_ranges: tuple[dict[str, Any], ...]
    registered_literals: tuple[dict[str, Any], ...]
    missing_raw_token_hexes: tuple[str, ...]
    record_count: int
    nonmissing_observation_count: int
    selected_token_form: str | None
    token_form_candidate_results: tuple[dict[str, Any], ...]
    padding_arm_candidate_results: tuple[dict[str, Any], ...]
    selected_arm: str | None
    range_renderability_counts: tuple[dict[str, Any], ...]
    derivation_status: str
    resolution_reason: str
    # The selected declaration tuple. It is a derivation input rather than a
    # serialized member, so `as_dict` deliberately omits it; §22 consumers
    # need it to rebuild the same renderability bands.
    selected_width: int | None = None
    selected_decimal_places: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable, source-ordered projection."""

        return {
            "interview_wave": self.interview_wave,
            "raw_field_id": self.raw_field_id,
            "normalized_literals": list(self.normalized_literals),
            "normalized_ranges": list(self.normalized_ranges),
            "registered_literals": list(self.registered_literals),
            "missing_raw_token_hexes": list(self.missing_raw_token_hexes),
            "record_count": self.record_count,
            "nonmissing_observation_count": (
                self.nonmissing_observation_count
            ),
            "selected_token_form": self.selected_token_form,
            "token_form_candidate_results": list(
                self.token_form_candidate_results
            ),
            "padding_arm_candidate_results": list(
                self.padding_arm_candidate_results
            ),
            "selected_arm": self.selected_arm,
            "range_renderability_counts": list(
                self.range_renderability_counts
            ),
            "derivation_status": self.derivation_status,
            "resolution_reason": self.resolution_reason,
        }


def _fraction_projection(value: Fraction) -> dict[str, int]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _normalized_literal_projection(literal: _Literal) -> dict[str, Any]:
    return {
        "source_entry_index": literal.index,
        "source_value_lexeme": literal.lexeme,
        "source_scalar": _fraction_projection(literal.scalar),
        "source_meaning": literal.meaning,
        "typed_disposition": "missing" if literal.missing else "ordinary",
    }


def _normalized_range_projection(item: _Range) -> dict[str, Any]:
    return {
        "source_entry_index": item.index,
        "source_value_lexeme": item.lexeme,
        "inclusive_min": _fraction_projection(item.minimum),
        "inclusive_max": _fraction_projection(item.maximum),
        "step": _fraction_projection(item.step),
        "source_member_count": item.count,
        "source_meaning": item.meaning,
    }


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


def _progression_segment(
    item: _Range,
    lower: Fraction | None = None,
    upper: Fraction | None = None,
    exact_decimal_places: int | None = None,
) -> tuple[int, int, int] | None:
    """Return one arithmetic intersection as ``(first, last, stride)`` indexes.

    The result describes the member indexes ``first, first + stride, ...`` up
    to ``last`` without expanding them, so a band covering billions of members
    stays an O(1) description.
    """

    effective_lower = (
        item.minimum if lower is None else max(item.minimum, lower)
    )
    effective_upper = (
        item.maximum if upper is None else min(item.maximum, upper)
    )
    if effective_lower > effective_upper:
        return None
    first_index = max(
        0,
        math.ceil((effective_lower - item.minimum) / item.step),
    )
    last_index = min(
        item.count - 1,
        math.floor((effective_upper - item.minimum) / item.step),
    )
    if first_index > last_index:
        return None
    if exact_decimal_places is None:
        return first_index, last_index, 1

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
        return None
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
        return None
    return first_match, last_index, reduced_modulus


def _segment_count(segment: tuple[int, int, int] | None) -> int:
    if segment is None:
        return 0
    first, last, stride = segment
    return (last - first) // stride + 1


def _progression_count(
    item: _Range,
    lower: Fraction | None = None,
    upper: Fraction | None = None,
    exact_decimal_places: int | None = None,
) -> int:
    """Count an arithmetic range intersection without member expansion."""

    return _segment_count(
        _progression_segment(item, lower, upper, exact_decimal_places)
    )


def _render_bands(
    item: _Range,
    token_form: str,
    width: int,
    decimal_places: int,
) -> list[tuple[tuple[int, int, int], bool]]:
    """Return every renderable magnitude band as an index segment.

    Each band is one sign/digit-count combination of the §20.3.3 renderer.
    Bands are pairwise index-disjoint because the member value is strictly
    increasing in the member index, and a band is arm-invariant exactly when
    its payload fills the declared width and therefore leaves no padding
    position for the two arms to disagree about.
    """

    bands: list[tuple[tuple[int, int, int], bool]] = []
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
                segment = _progression_segment(
                    item,
                    lower,
                    upper,
                    decimal_places if implied else 0,
                )
                if segment is not None:
                    bands.append((segment, digits + sign_width == width))
        bands.sort()
        return bands

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
            segment = _progression_segment(
                item,
                lower,
                upper,
                precision,
            )
            if segment is not None:
                bands.append(
                    (segment, sign_width + digits + 1 + precision == width)
                )
    bands.sort()
    return bands


def _range_render_counts(
    item: _Range,
    token_form: str,
    width: int,
    decimal_places: int,
) -> tuple[int, int]:
    """Return exact (renderable, arm-invariant renderable) cardinalities."""

    bands = _render_bands(item, token_form, width, decimal_places)
    renderable = sum(_segment_count(segment) for segment, _ in bands)
    invariant = sum(
        _segment_count(segment)
        for segment, is_invariant in bands
        if is_invariant
    )
    return renderable, invariant


@dataclass(frozen=True)
class RangeMemberRuns:
    """One range's exhaustive partition as unique maximal index runs."""

    source_member_count: int
    renderable: tuple[tuple[int, int], ...]
    unrenderable: tuple[tuple[int, int], ...]
    arm_invariant: tuple[tuple[int, int], ...]
    arm_ambiguous: tuple[tuple[int, int], ...]

    @property
    def renderable_count(self) -> int:
        return sum(count for _, count in self.renderable)

    @property
    def unrenderable_count(self) -> int:
        return sum(count for _, count in self.unrenderable)

    @property
    def arm_ambiguous_count(self) -> int:
        return sum(count for _, count in self.arm_ambiguous)


def _segment_runs(
    segment: tuple[int, int, int],
) -> Iterator[tuple[int, int]]:
    first, last, stride = segment
    if stride == 1:
        yield first, last - first + 1
        return
    for index in range(first, last + 1, stride):
        yield index, 1


def range_member_runs(
    item: _Range,
    token_form: str,
    width: int,
    decimal_places: int,
) -> RangeMemberRuns:
    """Decompose one range into its exhaustive renderability partition.

    The partition is derived from O(width) magnitude bands rather than from
    member expansion, so a range with billions of members is described in
    bounded work.  Renderability follows §22.4.5: a member is renderable
    exactly when the one §20.3.3 renderer returns it an exact-width image,
    and arm invariance never moves a member between the two relations.
    """

    bands = _render_bands(item, token_form, width, decimal_places)
    renderable = merge_runs(
        run for segment, _ in bands for run in _segment_runs(segment)
    )
    invariant = merge_runs(
        run
        for segment, is_invariant in bands
        if is_invariant
        for run in _segment_runs(segment)
    )
    return RangeMemberRuns(
        source_member_count=item.count,
        renderable=renderable,
        unrenderable=complement_runs(renderable, item.count),
        arm_invariant=invariant,
        arm_ambiguous=subtract_runs(renderable, invariant),
    )


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
    trace: dict[str, Any] | None = None,
) -> tuple[str, str]:
    if trace is None:
        trace = {}
    declaration = _NUM_FORMAT.fullmatch(field.declared_format)
    if declaration is None:
        return _terminal(
            UNSUPPORTED,
            "observed_token_outside_all_candidate_forms_or_semantics",
        )
    width, decimal_places = map(int, declaration.groups())
    trace["width"] = width
    trace["decimal_places"] = decimal_places

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
    producer_transitions: dict[int, str] = {}
    trace["registrations"] = registrations
    trace["producer_transitions"] = producer_transitions
    for literal in literals:
        _, registered, producer = _literal_candidates(
            literal,
            width,
            decimal_places,
            observations,
        )
        producer_transitions[literal.index] = producer
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
    trace["nonmissing_observation_count"] = nonmissing_count
    if nonmissing_count == 0:
        for literal in literals:
            if literal.index not in registrations:
                producer_transitions[literal.index] = (
                    "zero_count_physical_unestablished"
                )
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
    record_count = sum(observations.values())
    acceptance_vectors = {
        token: [
            token in missing_tokens
            or candidate_values[token_form][token] is not None
            for token_form in numeric_form_order(decimal_places)
        ]
        for token in observations
    }
    form_diagnostic_count = sum(
        frequency
        for token, frequency in observations.items()
        if token not in missing_tokens
        and any(acceptance_vectors[token])
        and not all(acceptance_vectors[token])
    )
    token_form_results: list[dict[str, Any]] = []
    passing_forms = []
    for token_form, values in candidate_values.items():
        accepted_count = sum(
            frequency
            for token, frequency in observations.items()
            if token in missing_tokens or values[token] is not None
        )
        rejected_count = record_count - accepted_count
        covers = rejected_count == 0
        sign_matches = (minus_count > 0) == _is_signed(token_form)
        passes = covers and sign_matches
        token_form_results.append(
            {
                "token_form_kind": token_form,
                "accepted_observation_count": accepted_count,
                "diagnostic_observation_count": form_diagnostic_count,
                "rejected_observation_count": rejected_count,
                "status": "pass" if passes else "fail",
            }
        )
        if passes:
            passing_forms.append(token_form)
    trace["token_form_candidate_results"] = tuple(token_form_results)
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
    trace["selected_token_form"] = token_form
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
            producer_transitions[literal.index] = "common_image"

    arm_accepted = {
        "zero_left_padding": 0,
        "left_ascii_space_padding": 0,
    }
    diagnostic_count = 0
    observed_invariant = True
    for token, frequency in observations.items():
        if token in missing_tokens:
            for arm in PADDING_ARMS:
                arm_accepted[arm] += frequency
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
        if zero_image == token:
            arm_accepted["zero_left_padding"] += frequency
        if space_image == token:
            arm_accepted["left_ascii_space_padding"] += frequency

    arm_results: list[dict[str, Any]] = []
    for arm in PADDING_ARMS:
        accepted_count = arm_accepted[arm]
        rejected_count = record_count - accepted_count
        if rejected_count == 0 and diagnostic_count == 0:
            arm_status = "indistinguishable"
        elif rejected_count == 0 and diagnostic_count > 0:
            arm_status = "pass"
        else:
            arm_status = "fail"
        arm_results.append(
            {
                "profile_kind": arm,
                "accepted_observation_count": accepted_count,
                "diagnostic_observation_count": diagnostic_count,
                "rejected_observation_count": rejected_count,
                "status": arm_status,
            }
        )
    trace["padding_arm_candidate_results"] = tuple(arm_results)
    zero_accepts = arm_accepted["zero_left_padding"] == record_count
    space_accepts = arm_accepted["left_ascii_space_padding"] == record_count

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
            producer_transitions[literal.index] = "selected_space"
        trace["selected_arm"] = "left_ascii_space_padding"
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
        trace["range_counts"] = tuple(range_counts)
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
        if width == 1:
            trace["selected_arm"] = (
                "padding_arm_underdetermined_width_one_exact_replay_v1"
            )
        else:
            trace["selected_arm"] = (
                "padding_arm_underdetermined_no_padding_capacity_"
                "exact_replay_v1"
            )
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
        trace["range_counts"] = tuple(range_counts)
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
    trace["range_counts"] = tuple(range_counts)
    ambiguous_literals = 0
    ambiguous_literal_indices: list[int] = []
    for literal in deferred:
        zero_image, space_image = selected_images[literal.index]
        if zero_image is not None and zero_image == space_image:
            registrations[literal.index] = zero_image
        elif zero_image is not None and space_image is not None:
            ambiguous_literals += 1
            ambiguous_literal_indices.append(literal.index)
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
        trace["selected_arm"] = (
            "padding_arm_underdetermined_no_padding_capacity_exact_replay_v1"
        )
        return _terminal(
            PADDING_UNDERDETERMINED,
            "finite_complete_equality",
        )
    if (
        ambiguous_count > 0
        and every_range_has_invariant
        and observed_invariant
    ):
        trace["selected_arm"] = (
            "padding_arm_underdetermined_finite_domain_arm_ambiguous_"
            "exact_replay_v1"
        )
        for index in ambiguous_literal_indices:
            producer_transitions[index] = "finite_arm_ambiguous_candidate_only"
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


def _coerce_observations(
    observations: Mapping[bytes, int],
) -> Counter[bytes]:
    result: Counter[bytes] = Counter()
    for token, frequency in observations.items():
        if not isinstance(token, bytes):
            raise TypeError("observation tokens must be exact bytes")
        if isinstance(frequency, bool) or not isinstance(frequency, int):
            raise TypeError("observation frequencies must be JSON integers")
        if frequency <= 0:
            raise ValueError("observation frequencies must be positive")
        result[token] += frequency
    if not result:
        raise ValueError("field observation relation must be nonempty")
    return result


def derive_field_details(
    field: SourceField,
    observations: Mapping[bytes, int],
) -> FieldDerivationDetails:
    """Derive one field's complete classifier inputs and disposition.

    The function neither reads expected census membership nor consults another
    field.  ``observations`` is the exact byte/frequency relation produced by
    source framing for ``field``.
    """

    observed = _coerce_observations(observations)
    literals, ranges = _normalize_entries(field)
    trace: dict[str, Any] = {}
    if _CHR_FORMAT.fullmatch(field.declared_format):
        status, reason = _classify_character(
            field,
            observed,
            literals,
            ranges,
        )
        width = field.raw_width
        registrations = {
            literal.index: literal.lexeme.encode("ascii")
            for literal in literals
            if len(literal.lexeme.encode("ascii")) == width
        }
        producer_transitions = {
            literal.index: (
                "strict_unchanged_width_character"
                if literal.index in registrations
                else "field_level_closed_failure"
            )
            for literal in literals
        }
        missing_images = {
            registrations[literal.index]
            for literal in literals
            if literal.missing and literal.index in registrations
        }
        nonmissing_count = sum(
            frequency
            for token, frequency in observed.items()
            if token not in missing_images
        )
    else:
        status, reason = _classify_numeric(
            field,
            observed,
            literals,
            ranges,
            trace,
        )
        registrations = trace.get("registrations", {})
        producer_transitions = trace.get("producer_transitions", {})
        nonmissing_count = trace.get(
            "nonmissing_observation_count",
            sum(observed.values()),
        )

    registered_literals = []
    missing_raw_token_hexes = []
    seen_missing: set[bytes] = set()
    for literal in literals:
        image = registrations.get(literal.index)
        producer = producer_transitions.get(
            literal.index,
            "field_level_closed_failure",
        )
        if image is not None:
            disposition = "registered_authoritative_image"
        elif producer == "finite_arm_ambiguous_candidate_only":
            disposition = "candidate_only_null_authority"
        elif producer == "zero_count_physical_unestablished":
            disposition = "physical_rendering_unestablished"
        else:
            disposition = "field_level_closed_failure"
        registered_literals.append(
            {
                "source_entry_index": literal.index,
                "source_value_lexeme": literal.lexeme,
                "typed_disposition": (
                    "missing" if literal.missing else "ordinary"
                ),
                "raw_token_hex": image.hex() if image is not None else None,
                "producer_transition": producer,
                "final_disposition": disposition,
            }
        )
        if literal.missing and image is not None and image not in seen_missing:
            missing_raw_token_hexes.append(image.hex())
            seen_missing.add(image)

    range_counts = trace.get("range_counts")
    if range_counts is None:
        range_renderability_counts = tuple(
            {
                "source_entry_index": item.index,
                "source_member_count": item.count,
                "renderable_member_count": None,
                "arm_invariant_renderable_member_count": None,
                "arm_ambiguous_renderable_member_count": None,
                "unrenderable_member_count": None,
            }
            for item in ranges
        )
    else:
        range_renderability_counts = tuple(
            {
                "source_entry_index": item.index,
                "source_member_count": item.count,
                "renderable_member_count": renderable,
                "arm_invariant_renderable_member_count": invariant,
                "arm_ambiguous_renderable_member_count": (
                    renderable - invariant
                ),
                "unrenderable_member_count": item.count - renderable,
            }
            for item, (renderable, invariant) in zip(
                ranges,
                range_counts,
                strict=True,
            )
        )
    return FieldDerivationDetails(
        interview_wave=field.interview_wave,
        raw_field_id=field.raw_field_id,
        normalized_literals=tuple(
            _normalized_literal_projection(literal) for literal in literals
        ),
        normalized_ranges=tuple(
            _normalized_range_projection(item) for item in ranges
        ),
        registered_literals=tuple(registered_literals),
        missing_raw_token_hexes=tuple(missing_raw_token_hexes),
        record_count=sum(observed.values()),
        nonmissing_observation_count=nonmissing_count,
        selected_token_form=trace.get("selected_token_form"),
        token_form_candidate_results=trace.get(
            "token_form_candidate_results",
            (),
        ),
        padding_arm_candidate_results=trace.get(
            "padding_arm_candidate_results",
            (),
        ),
        selected_arm=trace.get("selected_arm"),
        range_renderability_counts=range_renderability_counts,
        derivation_status=status,
        resolution_reason=reason,
        selected_width=trace.get("width"),
        selected_decimal_places=trace.get("decimal_places"),
    )


def normalize_field_entries(
    field: SourceField,
) -> tuple[tuple[_Literal, ...], tuple[_Range, ...]]:
    """Return one field's complete normalized literal and range entries."""

    return _normalize_entries(field)


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
    observer: Callable[[SourceField, FieldDerivationDetails], None]
    | None = None,
) -> dict[str, Any]:
    """Classify the complete source denominator and return census digests.

    ``raw_derivations`` is the return of ``derive_all_raw_censuses``.  Rows
    remain in ``corpus.fields`` order, which is the §20.3.7 denominator order.
    ``observer`` sees every field's complete derivation as it is produced, so
    a §22 consumer can accumulate partition facts in this one pass instead of
    reclassifying the corpus.
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
    field_details: list[dict[str, Any]] = []
    assignment: list[list[Any]] = []
    for field in corpus.fields:
        details = derive_field_details(field, observations[field.key])
        if observer is not None:
            observer(field, details)
        status = details.derivation_status
        reason = details.resolution_reason
        field_details.append(details.as_dict())
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
        "field_details": field_details,
        "field_detail_count": len(field_details),
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
