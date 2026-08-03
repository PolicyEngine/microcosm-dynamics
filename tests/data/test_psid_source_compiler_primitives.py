"""Unit vectors for the revision-9 source compiler primitives."""

from __future__ import annotations

from fractions import Fraction

import pytest

from populace_dynamics.data import psid_source_compiler as compiler


def _assertion(kind: str, row_id: str, text: str | None) -> dict:
    return {
        "source_kind": kind,
        "source_field_row_id": row_id,
        "parser_family": "psid_spss_setup_statements_v1",
        "source_format_text": text,
        "source_locator_ids": [f"locator:{row_id}"],
    }


@pytest.mark.unit
def test_section_10_1_canonical_json_has_sorted_keys_and_one_lf():
    assert compiler.canonical_json_bytes({"z": 1, "a": "\N{SNOWMAN}"}) == (
        b'{"a":"\\u2603","z":1}\n'
    )


@pytest.mark.unit
def test_declaration_dispositions_compare_every_row_to_selector():
    assertions = [
        _assertion("dictionary_layout", "row:0", "F6.2"),
        _assertion("codebook", "row:1", "NUM(6.2)"),
        _assertion("codebook", "row:2", "NUM(6.2)"),
    ]
    rows = compiler.build_source_format_projection(1979, "V6363", assertions)
    assert [row["declaration_disposition"] for row in rows] == [
        "selecting_numeric_declaration",
        "corroborating_tuple_equivalent_numeric_declaration",
        "corroborating_tuple_equivalent_numeric_declaration",
    ]
    assert (
        rows[1]["selecting_source_format_assertion_id"]
        == rows[0]["source_format_assertion_id"]
    )
    assert (
        rows[2]["selecting_source_format_assertion_id"]
        == rows[0]["source_format_assertion_id"]
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "NUM(4.2)",
            ("num_parenthesized_numeric_declaration", 4, 2),
        ),
        ("F4.2", ("spss_f_numeric_declaration", 4, 2)),
        ("CHR(7)", ("character_declaration", 7, None)),
        ("NUM(04.2)", None),
        ("NUM(4.4)", None),
        ("f4.2", None),
    ],
)
def test_closed_declaration_syntax(text, expected):
    assert compiler.parse_format_declaration(text) == expected


@pytest.mark.unit
def test_a6_r04_literal_decimal_no_padding_capacity():
    form = "unsigned_literal_ascii_decimal"
    for arm in compiler.PADDING_ARMS:
        assert (
            compiler.render_numeric_token(Fraction(13, 5), 4, 2, form, arm)
            == b"2.60"
        )
        assert compiler.parse_rendered_numeric_token(
            b"2.60", 4, 2, form, arm
        ) == Fraction(13, 5)


@pytest.mark.unit
def test_a6_r05_leading_minus_after_spaces_and_forbidden_spellings():
    form = "leading_ascii_minus_signed_integer"
    assert (
        compiler.render_numeric_token(
            Fraction(-242), 5, 0, form, "left_ascii_space_padding"
        )
        == b" -242"
    )
    assert (
        compiler.parse_rendered_numeric_token(
            b" -242", 5, 0, form, "left_ascii_space_padding"
        )
        == -242
    )
    for hostile in (b"+0242", b"0242-", b"2-042", b"-0242"):
        assert (
            compiler.parse_rendered_numeric_token(
                hostile,
                5,
                0,
                form,
                "left_ascii_space_padding",
            )
            is None
        )


@pytest.mark.unit
def test_a6_r06_literal_decimal_space_rendering():
    form = "unsigned_literal_ascii_decimal"
    token = compiler.render_numeric_token(
        Fraction(132, 5),
        6,
        2,
        form,
        "left_ascii_space_padding",
    )
    assert token == b" 26.40"
    assert compiler.parse_rendered_numeric_token(
        token,
        6,
        2,
        form,
        "left_ascii_space_padding",
    ) == Fraction(132, 5)


@pytest.mark.unit
def test_a6_r07_uses_greatest_exact_precision_that_fits():
    form = "leading_ascii_minus_signed_literal_ascii_decimal"
    assert (
        compiler.render_numeric_token(
            Fraction(-1040),
            7,
            2,
            form,
            "left_ascii_space_padding",
        )
        == b"-1040.0"
    )
    assert (
        compiler.render_numeric_token(
            Fraction(-104001, 100),
            7,
            2,
            form,
            "left_ascii_space_padding",
        )
        is None
    )


@pytest.mark.unit
def test_mandatory_two_digit_dfa_vector():
    tokens = [f"{value:02d}".encode("ascii") for value in range(100)]
    dfa = compiler.compile_exact_token_dfa(tokens, 2)
    assert dfa["state_ids"] == ["q:0", "q:1", "q:2"]
    assert dfa["accepting_state_ids"] == ["q:2"]
    assert dfa["transition_row_count"] == 20
    assert [row["position"] for row in dfa["transition_rows"]] == (
        [0] * 10 + [1] * 10
    )


def _dfa_accepts(dfa, token):
    transitions = {
        (row["state_id"], bytes.fromhex(row["input_byte_hex"])): row[
            "next_state_id"
        ]
        for row in dfa["transition_rows"]
    }
    state = dfa["start_state_id"]
    for byte in token:
        state = transitions.get((state, bytes([byte])))
        if state is None:
            return False
    return state in dfa["accepting_state_ids"]


@pytest.mark.unit
def test_a6_r01_full_form_dfa_uses_missing_first_subtraction():
    dfa = compiler.compile_numeric_form_dfa(
        2,
        0,
        "unsigned_ascii_integer",
        "left_ascii_space_padding",
        excluded_tokens=(b" 0", b"99"),
    )
    expected = {f"{value:2d}".encode("ascii") for value in range(100)} - {
        b" 0",
        b"99",
    }
    actual = {
        bytes((first, second))
        for first in range(256)
        for second in range(256)
        if _dfa_accepts(dfa, bytes((first, second)))
    }
    assert actual == expected


@pytest.mark.unit
def test_full_form_dfa_preserves_sign_point_and_space_actions():
    dfa = compiler.compile_numeric_form_dfa(
        5,
        2,
        "leading_ascii_minus_signed_literal_ascii_decimal",
        "left_ascii_space_padding",
    )
    assert _dfa_accepts(dfa, b"-2.40")
    assert _dfa_accepts(dfa, b" 2.40")
    assert not _dfa_accepts(dfa, b"-0.00")
    assert not _dfa_accepts(dfa, b"+2.40")
    actions = {row["value_action"] for row in dfa["transition_rows"]}
    assert {"no_op", "set_negative", "consume_decimal_point"} <= actions
