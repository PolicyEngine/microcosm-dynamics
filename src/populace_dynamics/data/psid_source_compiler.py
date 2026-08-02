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
from fractions import Fraction
from typing import Any

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


def canonical_json_bytes(value: Any) -> bytes:
    """Return the section 10.1 canonical JSON encoding with one final LF."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Hash a standalone section 10.1 canonical JSON value."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 of *value*."""

    return hashlib.sha256(value).hexdigest()


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

    class_by_node: list[int] = [-1] * len(children)
    class_signature_to_id: dict[tuple[Any, ...], int] = {}
    class_children: dict[int, dict[int, int]] = {}
    class_accepting: dict[int, bool] = {}
    class_depth: dict[int, int] = {}
    for depth in range(payload_width, -1, -1):
        for node in (
            index
            for index, node_depth in enumerate(depths)
            if node_depth == depth
        ):
            edges = tuple(
                (
                    byte,
                    transition_action(byte),
                    class_by_node[target],
                )
                for byte, target in sorted(children[node].items())
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
        for target in class_children[state_class].values():
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
    transitions = []
    for state_class in bfs_classes:
        for byte, target_class in sorted(class_children[state_class].items()):
            transitions.append(
                {
                    "position": class_depth[state_class],
                    "state_id": state_id[state_class],
                    "input_byte_hex": bytes([byte]).hex(),
                    "next_state_id": state_id[target_class],
                    "value_action": transition_action(byte),
                }
            )
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


def frame_fixed_width_records(*args: Any, **kwargs: Any) -> Any:
    """Revision-9 raw framing entry point (implemented below)."""

    raise NotImplementedError("all-source raw framing is not built yet")


def extract_codebook_rows(*args: Any, **kwargs: Any) -> Any:
    """Revision-9 codebook extraction entry point (implemented below)."""

    raise NotImplementedError(
        "all-source codebook extraction is not built yet"
    )


def derive_source_numeric_grammar(*args: Any, **kwargs: Any) -> Any:
    """Revision-9 complete numeric compiler entry point (implemented below)."""

    raise NotImplementedError("all-field grammar derivation is not built yet")
