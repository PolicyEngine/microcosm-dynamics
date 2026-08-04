"""Focused tests for Amendment 10's fail-closed A10-R04 runner."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import build_amendment10_successor_census as runner

RAW_V4742 = "Length of Interview\nCode actual number of minutes"
RAW_V4367 = (
    "Number of months used food stamps in 1975\n"
    "Code 1-11 for actual number of months used food stamps in 1975"
)
RAW_V5453 = (
    "E13. How long have you been looking for work?\n"
    "Code actual number of weeks (01 - 98)"
)


def _normalize_raw(description: str) -> str:
    return " ".join(
        part for part in description.replace("\n", " ").split(" ") if part
    )


def _segments(description: str) -> tuple[str, ...]:
    text = _normalize_raw(description)
    found: list[str] = []
    start = 0
    while start < len(text):
        cursor = start
        while True:
            stop = text.find(".", cursor)
            if stop < 0:
                found.append(text[start:])
                return tuple(found)
            if stop + 1 == len(text) or text[stop + 1] == " ":
                found.append(text[start : stop + 1])
                start = stop + 2
                break
            cursor = stop + 1
    return tuple(found)


_SYNTHETIC_SEGMENTS = {
    segment
    for description in (RAW_V4742, RAW_V4367, RAW_V5453)
    for segment in _segments(description)
}
_SYNTHETIC_SEGMENT_AUTHORITY = tuple(
    row
    for row in runner.SEGMENT_START_AUTHORITY
    if row[0] in _SYNTHETIC_SEGMENTS
)
_SYNTHETIC_CODING_STARTS = {
    "Code actual number of minutes",
    "Code 1-11 for actual number of months used food stamps in 1975",
    "Code actual number of weeks (01 - 98)",
}
_SYNTHETIC_CODING_AUTHORITY = tuple(
    row
    for row in runner.CODING_START_AUTHORITY
    if row[0] in _SYNTHETIC_CODING_STARTS
)


def _synthetic_title_authority_row(
    description: str,
    bounded_context_header: str,
    family: str,
    spelling: str,
    unit: str,
    field: str,
) -> tuple[object, ...]:
    start = description.index(spelling)
    return (
        hashlib.sha256(description.encode("utf-8")).hexdigest(),
        bounded_context_header,
        family,
        start,
        start + len(spelling.encode("ascii")),
        spelling,
        unit,
        "whole_domain_denotation",
        "synthetic_title_denotation",
        1968,
        field,
    )


_SYNTHETIC_TITLE_AUTHORITY = (
    _synthetic_title_authority_row(
        RAW_V4742,
        "Length of Interview",
        "minute_token",
        "minutes",
        "minute",
        "A",
    ),
    _synthetic_title_authority_row(
        RAW_V4367,
        "Number of months used food stamps in 1975",
        "month_token",
        "months",
        "month",
        "C",
    ),
)

_EXPECTED_PAYLOAD_KEYS = (
    "actual_candidate_occurrence_count",
    "actual_candidate_table_row_count",
    "actual_candidate_table_sha256",
    "actual_candidate_unadjudicated_count",
    "census_sha256",
    "coding_candidate_occurrence_count",
    "coding_candidate_table_row_count",
    "coding_candidate_table_sha256",
    "coding_candidate_unadjudicated_count",
    "coding_start_authority_array_sha256",
    "coding_start_authority_relation_byte_count",
    "coding_start_authority_relation_sha256",
    "coding_start_authority_row_count",
    "count_array_sha256",
    "count_rows",
    "denominator_sha256",
    "denotation_candidate_distinct_text_count",
    "denotation_candidate_occurrence_count",
    "denotation_candidate_overselected_count",
    "denotation_candidate_plus_actual_distinct_text_count",
    "denotation_candidate_start_count",
    "denotation_candidate_table_row_count",
    "denotation_candidate_table_sha256",
    "denotation_candidate_total_occurrence_count",
    "denotation_candidate_unadjudicated_count",
    "denotation_candidate_unselected_count",
    "denotation_start_occurrence_byte_count",
    "denotation_start_occurrence_row_count",
    "denotation_start_occurrence_sha256",
    "denotation_start_partition_rows",
    "failure_reason_row_count",
    "failure_reason_rows",
    "failure_reason_rows_byte_count",
    "failure_reason_rows_sha256",
    "field_count",
    "input_relation_row_count",
    "input_relation_sha256",
    "movement_key_sha256",
    "movement_row_count",
    "movement_rows",
    "movement_rows_sha256",
    "ordered_assignment_sha256",
    "predicate_authority_row_count",
    "predicate_authority_sha256",
    "ratified_count_rows",
    "schema_version",
    "segment_start_authority_array_sha256",
    "segment_start_authority_relation_byte_count",
    "segment_start_authority_relation_sha256",
    "segment_start_authority_row_count",
    "segment_start_authority_start_count",
    "statement_table_row_count",
    "statement_table_sha256",
    "status_matrix_rows",
    "title_generic_relation_array_sha256",
    "title_generic_relation_byte_count",
    "title_generic_relation_row_count",
    "title_generic_relation_sha256",
    "title_header_candidate_occurrence_count",
    "title_header_candidate_table_array_sha256",
    "title_header_candidate_table_relation_byte_count",
    "title_header_candidate_table_relation_sha256",
    "title_header_candidate_table_row_count",
    "title_header_defeat_field_count",
    "title_header_defeated_start_count",
    "title_header_matched_field_count",
    "title_header_no_match_field_count",
    "title_header_positive_field_count",
    "title_header_positive_start_count",
    "title_header_unadjudicated_start_count",
    "title_literal_relation_array_sha256",
    "title_literal_relation_byte_count",
    "title_literal_relation_row_count",
    "title_literal_relation_sha256",
    "title_start_authority_array_sha256",
    "title_start_authority_relation_byte_count",
    "title_start_authority_relation_sha256",
    "title_start_authority_row_count",
    "unit_bearing_statement_count",
    "unit_field_counts",
    "unit_reason_field_counts",
)


@pytest.fixture(autouse=True)
def _closed_synthetic_authorities(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep isolated gates closed without rebuilding the 89,599-row corpus."""

    assert len(_SYNTHETIC_SEGMENT_AUTHORITY) == 4
    assert len(_SYNTHETIC_CODING_AUTHORITY) == 3
    monkeypatch.setattr(
        runner,
        "SEGMENT_START_AUTHORITY",
        _SYNTHETIC_SEGMENT_AUTHORITY,
    )
    monkeypatch.setattr(
        runner,
        "CODING_START_AUTHORITY",
        _SYNTHETIC_CODING_AUTHORITY,
    )
    monkeypatch.setattr(
        runner,
        "TITLE_START_AUTHORITY",
        _SYNTHETIC_TITLE_AUTHORITY,
    )


def _row(
    wave: int,
    field: str,
    status: str,
    description: str | None,
) -> dict[str, object]:
    return {
        "interview_wave": wave,
        "raw_field_id": field,
        "derivation_status": status,
        "resolution_reason": "synthetic_ratified_reason",
        "source_description": description,
    }


def _rows() -> list[dict[str, object]]:
    return [
        _row(
            1968,
            "A",
            "compiled_source_numeric_grammar",
            RAW_V4742,
        ),
        _row(1968, "B", "compiled_source_numeric_grammar", None),
        _row(
            1968,
            "C",
            "value_code_domain_no_numeric_grammar",
            RAW_V4367,
        ),
        _row(
            1968,
            "D",
            "unsupported_source_numeric_format",
            RAW_V5453,
        ),
    ]


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _pins(rows: list[dict[str, object]]) -> runner.GatePins:
    return runner.pins_from_build(runner.build_payload(rows))


def _sentinel_outputs(tmp_path: Path) -> tuple[Path, Path]:
    output = tmp_path / "payload.json"
    statements = tmp_path / "statements.jsonl"
    output.write_bytes(b"payload sentinel\n")
    statements.write_bytes(b"statements sentinel\n")
    return output, statements


def test_frozen_raw_route_and_total_adjudication_pins() -> None:
    pins = runner.EXPECTED_A10_R04_PINS
    assert pins.input_relation_row_count == 89_599
    assert pins.input_relation_sha256 == (
        "563b1eaede9dcb5a085d8014dd3a4aacb2d3419ce7d0a0eb65063753b375ca6e"
    )
    assert tuple(count for _status, count in pins.count_rows) == (
        8_140,
        309,
        77,
        12,
        67_316,
        1_145,
        0,
        1,
        421,
        12_178,
    )
    assert (
        pins.count_array_sha256,
        pins.ordered_assignment_sha256,
        pins.movement_row_count,
        pins.movement_rows_sha256,
        pins.movement_key_sha256,
        pins.census_payload_sha256,
    ) == (
        "de75d6601129d8e1f940b43d9aedb9ed9c57c8e1aaaed9b8ac0a80cad027c1c8",
        "cadec36379fe7e46701a16b5f7fd03b587a3ebb7f18f0f193261e9c69c8bfd99",
        11_365,
        "23d44c23310508857fd879534afb8daf3dd59aa181582d63fb64a46734b647dc",
        "9cffc90dc9e7173d734b629d5ac857aa02865005433e1b8de38c123708bc4d97",
        "7b66e4bed27c272e5b99bcd1cdd69fb4ad1f61c56b9fc0a787fc7d3301b46834",
    )
    assert (
        pins.actual_candidate_table_row_count,
        pins.actual_candidate_occurrence_count,
        pins.actual_candidate_unadjudicated_count,
        pins.actual_candidate_table_sha256,
    ) == (
        82,
        322,
        0,
        "bf77cd7294752ac9e6ac01d4d68efac86c47b7327094d5eec479d9db1f27176b",
    )
    assert (
        pins.coding_candidate_table_row_count,
        pins.coding_candidate_occurrence_count,
        pins.coding_candidate_unadjudicated_count,
        pins.coding_candidate_table_sha256,
    ) == (
        203,
        1_154,
        0,
        "9f6cd23d36ad6825a17d3ece2d2612ef89c066d5c587bd72d1933f19e4c0c195",
    )
    assert (
        pins.denotation_candidate_table_row_count,
        pins.denotation_candidate_occurrence_count,
        pins.denotation_candidate_start_count,
        pins.denotation_candidate_distinct_text_count,
        pins.denotation_candidate_plus_actual_distinct_text_count,
        pins.denotation_candidate_total_occurrence_count,
        pins.denotation_candidate_unselected_count,
        pins.denotation_candidate_overselected_count,
        pins.denotation_candidate_unadjudicated_count,
        pins.denotation_candidate_table_sha256,
    ) == (
        1_114_747,
        2_240_669,
        2_240_669,
        717_810,
        717_823,
        2_240_991,
        0,
        0,
        0,
        "58675b1998587ce2bd7b6dc005f4e2d2983cff1ec338139d081aa4e1348bb847",
    )
    assert (
        pins.denotation_start_occurrence_row_count,
        pins.denotation_start_occurrence_byte_count,
        pins.denotation_start_occurrence_sha256,
        pins.denotation_start_partition_rows,
    ) == (
        2_240_669,
        269_157_391,
        "e7b83dc2cccc9b42af157543d77efa8861315825b3cbb0599bb7db95fc9f8c43",
        (
            ("whole_domain_denotation", 16_668),
            ("explicit_no_whole_domain_denotation", 76_350),
            ("explicit_no_denotation", 2_147_651),
            ("unadjudicated_start", 0),
        ),
    )
    assert (
        pins.segment_start_authority_row_count,
        pins.segment_start_authority_start_count,
        pins.segment_start_authority_relation_byte_count,
        pins.segment_start_authority_relation_sha256,
        pins.segment_start_authority_array_sha256,
    ) == (
        59_445,
        1_114_747,
        8_466_288,
        "b2185fd7d44c83292ad2af25b1186369cfef119e4dcc16a4f960d3e225a7cb36",
        "c0eb8d26bf903137f73afc5fc37e79f8bfd0b2983d9ac79d33f14abd35c84883",
    )
    assert (
        pins.coding_start_authority_row_count,
        pins.coding_start_authority_relation_byte_count,
        pins.coding_start_authority_relation_sha256,
        pins.coding_start_authority_array_sha256,
    ) == (
        203,
        31_396,
        "6f164c6772def69a29a57e1de04b3927ab8f56141bc2a8c6f0dee0964c8da6bf",
        "ac2bddbed10bb445215bb19354259685efe24c82b2f59b258dec5d23fcf8497b",
    )
    assert (
        pins.title_header_candidate_table_row_count,
        pins.title_header_matched_field_count,
        pins.title_header_candidate_occurrence_count,
        pins.title_header_positive_start_count,
        pins.title_header_defeated_start_count,
        pins.title_header_unadjudicated_start_count,
        pins.title_header_positive_field_count,
        pins.title_header_defeat_field_count,
        pins.title_header_no_match_field_count,
    ) == (
        89_599,
        51_957,
        80_306,
        8_410,
        71_896,
        0,
        8_388,
        43_569,
        37_642,
    )
    assert (
        pins.title_header_candidate_table_relation_byte_count,
        pins.title_header_candidate_table_relation_sha256,
        pins.title_header_candidate_table_array_sha256,
    ) == (
        89_417_509,
        "a6f44097bfdaf82e1dcb4fdb09d7027b4c619177e7f2695385cb0b24d40f654b",
        "87d0872cb45f8319f0a9ed25bf705096f5a6c62453319e650ba1081bb56589c6",
    )
    assert (
        pins.title_start_authority_row_count,
        pins.title_start_authority_relation_byte_count,
        pins.title_start_authority_relation_sha256,
        pins.title_start_authority_array_sha256,
    ) == (
        54_185,
        16_637_872,
        "ab0db98fc0b763553ef0373c57baa51e13551d9831f55c72f19321da4c830a01",
        "8be723069f257659cc2c36dd55758c76d084eded24d987629d1950c172032933",
    )
    assert (
        pins.title_literal_relation_row_count,
        pins.title_literal_relation_byte_count,
        pins.title_literal_relation_sha256,
        pins.title_literal_relation_array_sha256,
    ) == (
        13,
        733,
        "e1159929e711f73757b7e51a648f2c096965881a2342d9f26ce4e95d7c8af46e",
        "c5f6b75b64ebd86134e1b655c5d522fcd18dc2179fd28fa2c66a0943465e2913",
    )
    assert (
        pins.title_generic_relation_row_count,
        pins.title_generic_relation_byte_count,
        pins.title_generic_relation_sha256,
        pins.title_generic_relation_array_sha256,
    ) == (
        38,
        1_733,
        "b56ffd655abb00c8aca6e382092d08cd94325cfbf8ef4ce25651a59fc6cf8133",
        "f709526fe7802085ed691167a595f3d24504523dfa9a5fd4f61eb9269debd9de",
    )


def test_title_authority_offsets_are_relative_to_raw_description() -> None:
    description = RAW_V4742
    start = description.index("minutes")
    authority_row = (
        hashlib.sha256(description.encode("utf-8")).hexdigest(),
        "Length of Interview",
        "minute_token",
        start,
        start + len("minutes"),
        "minutes",
        "minute",
        "whole_domain_denotation",
        "elapsed_interview_length_title",
        1968,
        "A",
    )

    runner._validate_title_start_authority((authority_row,), _rows())


def test_title_authority_missing_witness_key_is_rejected() -> None:
    field_rows = tuple(row for row in _rows() if row["raw_field_id"] != "A")

    with pytest.raises(runner.GateError, match="missing raw-field witness key"):
        runner._validate_title_start_authority(
            (_SYNTHETIC_TITLE_AUTHORITY[0],),
            field_rows,
        )


def test_title_authority_non_string_witness_is_rejected() -> None:
    field_rows = _rows()
    field_rows[0] = dict(field_rows[0], source_description=None)

    with pytest.raises(
        runner.GateError,
        match="non-string raw-description witness",
    ):
        runner._validate_title_start_authority(
            (_SYNTHETIC_TITLE_AUTHORITY[0],),
            field_rows,
        )


def test_title_authority_duplicate_witness_rejects_last_row_wins() -> None:
    correct_last_row = _rows()[0]
    incorrect_first_row = dict(
        correct_last_row,
        source_description="not the authority witness",
    )

    with pytest.raises(
        runner.GateError,
        match="duplicate raw-field witness key",
    ):
        runner._validate_title_start_authority(
            (_SYNTHETIC_TITLE_AUTHORITY[0],),
            (incorrect_first_row, correct_last_row),
        )


def test_valid_gate_emits_only_after_every_pin_passes(tmp_path: Path) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    output = tmp_path / "payload.json"
    statements = tmp_path / "statements.jsonl"
    titles = tmp_path / "titles.jsonl"
    _write_rows(field_rows, rows)

    build = runner.execute_gate(
        field_rows,
        output=output,
        statements=statements,
        titles=titles,
        pins=_pins(rows),
    )

    assert json.loads(output.read_text(encoding="utf-8")) == build.payload
    assert tuple(sorted(build.payload)) == _EXPECTED_PAYLOAD_KEYS
    assert len(build.payload) == 81
    assert build.payload["schema_version"] == "amendment_10_successor_census.v4"
    assert (
        build.payload["title_literal_relation_row_count"],
        build.payload["title_literal_relation_byte_count"],
        build.payload["title_literal_relation_sha256"],
        build.payload["title_literal_relation_array_sha256"],
    ) == (
        13,
        733,
        "e1159929e711f73757b7e51a648f2c096965881a2342d9f26ce4e95d7c8af46e",
        "c5f6b75b64ebd86134e1b655c5d522fcd18dc2179fd28fa2c66a0943465e2913",
    )
    assert (
        build.payload["title_generic_relation_row_count"],
        build.payload["title_generic_relation_byte_count"],
        build.payload["title_generic_relation_sha256"],
        build.payload["title_generic_relation_array_sha256"],
    ) == (
        38,
        1_733,
        "b56ffd655abb00c8aca6e382092d08cd94325cfbf8ef4ce25651a59fc6cf8133",
        "f709526fe7802085ed691167a595f3d24504523dfa9a5fd4f61eb9269debd9de",
    )
    emitted_table = [
        json.loads(line)
        for line in statements.read_text(encoding="utf-8").splitlines()
    ]
    assert emitted_table == list(build.statement_rows)
    emitted_titles = [
        json.loads(line)
        for line in titles.read_text(encoding="utf-8").splitlines()
    ]
    assert emitted_titles == list(build.title_header_candidate_rows)


@pytest.mark.parametrize(
    ("description", "message"),
    [
        (
            "Question text with no registered semantic authority.",
            "unadjudicated denotation candidates remain",
        ),
        (
            "Code actual number of fortnights",
            "unadjudicated raw coding starts remain",
        ),
        (
            "Annual work hours in 2099",
            "unadjudicated title/header starts remain",
        ),
    ],
)
def test_unadjudicated_start_aborts_even_when_observed_pins_match(
    tmp_path: Path,
    description: str,
    message: str,
) -> None:
    rows = _rows()
    rows[0] = dict(rows[0], source_description=description)
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output, statements = _sentinel_outputs(tmp_path)

    with pytest.raises(runner.GateError, match=message):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=_pins(rows),
        )

    assert output.read_bytes() == b"payload sentinel\n"
    assert statements.read_bytes() == b"statements sentinel\n"


@pytest.mark.parametrize(
    ("family", "message", "mutate"),
    [
        (
            "input relation",
            "input relation",
            lambda pins: replace(pins, input_relation_sha256="0" * 64),
        ),
        (
            "denominator",
            "denominator",
            lambda pins: replace(pins, denominator_sha256="0" * 64),
        ),
        (
            "census",
            "count-array",
            lambda pins: replace(pins, count_array_sha256="0" * 64),
        ),
        (
            "matrix",
            "matrix",
            lambda pins: replace(
                pins,
                status_matrix_rows=pins.status_matrix_rows[:-1],
            ),
        ),
        (
            "movement",
            "movement",
            lambda pins: replace(pins, movement_rows_sha256="0" * 64),
        ),
        (
            "artifact",
            "failure-reason",
            lambda pins: replace(
                pins,
                failure_reason_rows_sha256="0" * 64,
            ),
        ),
        (
            "Actual candidate",
            "Actual candidate table",
            lambda pins: replace(
                pins,
                actual_candidate_table_sha256="0" * 64,
            ),
        ),
        (
            "coding candidate",
            "coding candidate table",
            lambda pins: replace(
                pins,
                coding_candidate_table_sha256="0" * 64,
            ),
        ),
        (
            "title/header candidate",
            "title/header candidate table relation digest",
            lambda pins: replace(
                pins,
                title_header_candidate_table_relation_sha256="0" * 64,
            ),
        ),
        (
            "title/header candidate array",
            "title/header candidate table canonical-array digest",
            lambda pins: replace(
                pins,
                title_header_candidate_table_array_sha256="0" * 64,
            ),
        ),
        (
            "denotation candidate",
            "denotation candidate table",
            lambda pins: replace(
                pins,
                denotation_candidate_table_sha256="0" * 64,
            ),
        ),
        (
            "ordered start occurrence",
            "ordered start-occurrence digest",
            lambda pins: replace(
                pins,
                denotation_start_occurrence_sha256="0" * 64,
            ),
        ),
        (
            "statement",
            "statement",
            lambda pins: replace(pins, statement_table_sha256="0" * 64),
        ),
        (
            "payload",
            "payload",
            lambda pins: replace(pins, census_payload_sha256="0" * 64),
        ),
    ],
)
def test_each_gate_family_aborts_without_emission(
    tmp_path: Path,
    family: str,
    message: str,
    mutate,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output, statements = _sentinel_outputs(tmp_path)

    with pytest.raises(runner.GateError, match=message):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=mutate(_pins(rows)),
        )

    assert output.read_bytes() == b"payload sentinel\n"
    assert statements.read_bytes() == b"statements sentinel\n"


@pytest.mark.parametrize(
    ("message", "mutate"),
    [
        (
            "Actual candidate table row count",
            lambda pins: replace(
                pins,
                actual_candidate_table_row_count=(
                    pins.actual_candidate_table_row_count + 1
                ),
            ),
        ),
        (
            "Actual candidate occurrence count",
            lambda pins: replace(
                pins,
                actual_candidate_occurrence_count=(
                    pins.actual_candidate_occurrence_count + 1
                ),
            ),
        ),
        (
            "unadjudicated Actual candidate count",
            lambda pins: replace(
                pins,
                actual_candidate_unadjudicated_count=1,
            ),
        ),
        (
            "coding candidate table row count",
            lambda pins: replace(
                pins,
                coding_candidate_table_row_count=(
                    pins.coding_candidate_table_row_count + 1
                ),
            ),
        ),
        (
            "coding candidate occurrence count",
            lambda pins: replace(
                pins,
                coding_candidate_occurrence_count=(
                    pins.coding_candidate_occurrence_count + 1
                ),
            ),
        ),
        (
            "unadjudicated coding candidate count",
            lambda pins: replace(
                pins,
                coding_candidate_unadjudicated_count=1,
            ),
        ),
        (
            "title/header candidate table row count",
            lambda pins: replace(
                pins,
                title_header_candidate_table_row_count=(
                    pins.title_header_candidate_table_row_count + 1
                ),
            ),
        ),
        (
            "title/header matched field count",
            lambda pins: replace(
                pins,
                title_header_matched_field_count=(
                    pins.title_header_matched_field_count + 1
                ),
            ),
        ),
        (
            "title/header candidate occurrence count",
            lambda pins: replace(
                pins,
                title_header_candidate_occurrence_count=(
                    pins.title_header_candidate_occurrence_count + 1
                ),
            ),
        ),
        (
            "positive title/header start count",
            lambda pins: replace(
                pins,
                title_header_positive_start_count=(
                    pins.title_header_positive_start_count + 1
                ),
            ),
        ),
        (
            "defeated title/header start count",
            lambda pins: replace(
                pins,
                title_header_defeated_start_count=(
                    pins.title_header_defeated_start_count + 1
                ),
            ),
        ),
        (
            "unadjudicated title/header start count",
            lambda pins: replace(
                pins,
                title_header_unadjudicated_start_count=1,
            ),
        ),
        (
            "positive title/header field count",
            lambda pins: replace(
                pins,
                title_header_positive_field_count=(
                    pins.title_header_positive_field_count + 1
                ),
            ),
        ),
        (
            "defeat-only title/header field count",
            lambda pins: replace(
                pins,
                title_header_defeat_field_count=(
                    pins.title_header_defeat_field_count + 1
                ),
            ),
        ),
        (
            "no-match title/header field count",
            lambda pins: replace(
                pins,
                title_header_no_match_field_count=(
                    pins.title_header_no_match_field_count + 1
                ),
            ),
        ),
        (
            "title/header candidate table relation byte count",
            lambda pins: replace(
                pins,
                title_header_candidate_table_relation_byte_count=(
                    pins.title_header_candidate_table_relation_byte_count + 1
                ),
            ),
        ),
        (
            "denotation candidate table row count",
            lambda pins: replace(
                pins,
                denotation_candidate_table_row_count=(
                    pins.denotation_candidate_table_row_count + 1
                ),
            ),
        ),
        (
            "denotation candidate occurrence count",
            lambda pins: replace(
                pins,
                denotation_candidate_occurrence_count=(
                    pins.denotation_candidate_occurrence_count + 1
                ),
            ),
        ),
        (
            "universal statement-candidate start count",
            lambda pins: replace(
                pins,
                denotation_candidate_start_count=(
                    pins.denotation_candidate_start_count + 1
                ),
            ),
        ),
        (
            "distinct denotation candidate text count",
            lambda pins: replace(
                pins,
                denotation_candidate_distinct_text_count=(
                    pins.denotation_candidate_distinct_text_count + 1
                ),
            ),
        ),
        (
            "distinct denotation-plus-Actual candidate text count",
            lambda pins: replace(
                pins,
                denotation_candidate_plus_actual_distinct_text_count=(
                    pins.denotation_candidate_plus_actual_distinct_text_count
                    + 1
                ),
            ),
        ),
        (
            "total denotation candidate occurrence count",
            lambda pins: replace(
                pins,
                denotation_candidate_total_occurrence_count=(
                    pins.denotation_candidate_total_occurrence_count + 1
                ),
            ),
        ),
        (
            "whole-domain candidates missed by production selectors",
            lambda pins: replace(
                pins,
                denotation_candidate_unselected_count=1,
            ),
        ),
        (
            "production selections lacking whole-domain authority",
            lambda pins: replace(
                pins,
                denotation_candidate_overselected_count=1,
            ),
        ),
        (
            "unadjudicated denotation candidate count",
            lambda pins: replace(
                pins,
                denotation_candidate_unadjudicated_count=1,
            ),
        ),
        (
            "ordered start-occurrence row count",
            lambda pins: replace(
                pins,
                denotation_start_occurrence_row_count=(
                    pins.denotation_start_occurrence_row_count + 1
                ),
            ),
        ),
        (
            "ordered start-occurrence byte count",
            lambda pins: replace(
                pins,
                denotation_start_occurrence_byte_count=(
                    pins.denotation_start_occurrence_byte_count + 1
                ),
            ),
        ),
        (
            "start-occurrence disposition partition",
            lambda pins: replace(
                pins,
                denotation_start_partition_rows=(
                    *pins.denotation_start_partition_rows[:-1],
                    ("unadjudicated_start", 1),
                ),
            ),
        ),
    ],
)
def test_each_total_adjudication_pin_aborts_without_emission(
    tmp_path: Path,
    message: str,
    mutate,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output, statements = _sentinel_outputs(tmp_path)

    with pytest.raises(runner.GateError, match=message):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=mutate(_pins(rows)),
        )

    assert output.read_bytes() == b"payload sentinel\n"
    assert statements.read_bytes() == b"statements sentinel\n"


@pytest.mark.parametrize(
    ("message", "mutate"),
    [
        (
            "title-start authority row count",
            lambda pins: replace(
                pins,
                title_start_authority_row_count=(
                    pins.title_start_authority_row_count - 1
                ),
            ),
        ),
        (
            "title-start authority relation byte count",
            lambda pins: replace(
                pins,
                title_start_authority_relation_byte_count=(
                    pins.title_start_authority_relation_byte_count - 1
                ),
            ),
        ),
        (
            "title-start authority relation digest",
            lambda pins: replace(
                pins,
                title_start_authority_relation_sha256="0" * 64,
            ),
        ),
        (
            "title-start authority canonical-array digest",
            lambda pins: replace(
                pins,
                title_start_authority_array_sha256="0" * 64,
            ),
        ),
        (
            "segment/start authority row count",
            lambda pins: replace(
                pins,
                segment_start_authority_row_count=(
                    pins.segment_start_authority_row_count - 1
                ),
            ),
        ),
        (
            "segment/start authority start count",
            lambda pins: replace(
                pins,
                segment_start_authority_start_count=(
                    pins.segment_start_authority_start_count - 1
                ),
            ),
        ),
        (
            "segment/start authority relation byte count",
            lambda pins: replace(
                pins,
                segment_start_authority_relation_byte_count=(
                    pins.segment_start_authority_relation_byte_count - 1
                ),
            ),
        ),
        (
            "segment/start authority relation digest",
            lambda pins: replace(
                pins,
                segment_start_authority_relation_sha256="0" * 64,
            ),
        ),
        (
            "segment/start authority canonical-array digest",
            lambda pins: replace(
                pins,
                segment_start_authority_array_sha256="0" * 64,
            ),
        ),
        (
            "coding-start authority row count",
            lambda pins: replace(
                pins,
                coding_start_authority_row_count=(
                    pins.coding_start_authority_row_count - 1
                ),
            ),
        ),
        (
            "coding-start authority relation byte count",
            lambda pins: replace(
                pins,
                coding_start_authority_relation_byte_count=(
                    pins.coding_start_authority_relation_byte_count - 1
                ),
            ),
        ),
        (
            "coding-start authority relation digest",
            lambda pins: replace(
                pins,
                coding_start_authority_relation_sha256="0" * 64,
            ),
        ),
        (
            "coding-start authority canonical-array digest",
            lambda pins: replace(
                pins,
                coding_start_authority_array_sha256="0" * 64,
            ),
        ),
        (
            "anchor relation row count",
            lambda pins: replace(
                pins,
                anchor_relation_row_count=pins.anchor_relation_row_count - 1,
            ),
        ),
        (
            "anchor relation byte count",
            lambda pins: replace(
                pins,
                anchor_relation_byte_count=(
                    pins.anchor_relation_byte_count - 1
                ),
            ),
        ),
        (
            "anchor relation digest",
            lambda pins: replace(pins, anchor_relation_sha256="0" * 64),
        ),
        (
            "anchor relation canonical-array digest",
            lambda pins: replace(
                pins,
                anchor_relation_array_sha256="0" * 64,
            ),
        ),
        (
            "clause relation row count",
            lambda pins: replace(
                pins,
                clause_relation_row_count=pins.clause_relation_row_count - 1,
            ),
        ),
        (
            "clause relation byte count",
            lambda pins: replace(
                pins,
                clause_relation_byte_count=(
                    pins.clause_relation_byte_count - 1
                ),
            ),
        ),
        (
            "clause relation digest",
            lambda pins: replace(pins, clause_relation_sha256="0" * 64),
        ),
        (
            "clause relation canonical-array digest",
            lambda pins: replace(
                pins,
                clause_relation_array_sha256="0" * 64,
            ),
        ),
        (
            "title-literal relation row count",
            lambda pins: replace(
                pins,
                title_literal_relation_row_count=(
                    pins.title_literal_relation_row_count - 1
                ),
            ),
        ),
        (
            "title-literal relation byte count",
            lambda pins: replace(
                pins,
                title_literal_relation_byte_count=(
                    pins.title_literal_relation_byte_count - 1
                ),
            ),
        ),
        (
            "title-literal relation digest",
            lambda pins: replace(
                pins,
                title_literal_relation_sha256="0" * 64,
            ),
        ),
        (
            "title-literal relation canonical-array digest",
            lambda pins: replace(
                pins,
                title_literal_relation_array_sha256="0" * 64,
            ),
        ),
        (
            "title-generic relation row count",
            lambda pins: replace(
                pins,
                title_generic_relation_row_count=(
                    pins.title_generic_relation_row_count - 1
                ),
            ),
        ),
        (
            "title-generic relation byte count",
            lambda pins: replace(
                pins,
                title_generic_relation_byte_count=(
                    pins.title_generic_relation_byte_count - 1
                ),
            ),
        ),
        (
            "title-generic relation digest",
            lambda pins: replace(
                pins,
                title_generic_relation_sha256="0" * 64,
            ),
        ),
        (
            "title-generic relation canonical-array digest",
            lambda pins: replace(
                pins,
                title_generic_relation_array_sha256="0" * 64,
            ),
        ),
        (
            "predicate-authority row count",
            lambda pins: replace(
                pins,
                predicate_authority_row_count=(
                    pins.predicate_authority_row_count - 1
                ),
            ),
        ),
        (
            "predicate-authority relation byte count",
            lambda pins: replace(
                pins,
                predicate_authority_relation_byte_count=(
                    pins.predicate_authority_relation_byte_count - 1
                ),
            ),
        ),
        (
            "predicate-authority relation digest",
            lambda pins: replace(
                pins,
                predicate_authority_relation_sha256="0" * 64,
            ),
        ),
        (
            "predicate-authority canonical-array digest",
            lambda pins: replace(
                pins,
                predicate_authority_sha256="0" * 64,
            ),
        ),
        (
            "predicate-authority four-way partition",
            lambda pins: replace(
                pins,
                predicate_authority_partition_rows=(
                    *pins.predicate_authority_partition_rows[:-1],
                    ("conflicting_unit_clauses", 2),
                ),
            ),
        ),
    ],
)
def test_each_semantic_registry_pin_aborts_without_emission(
    tmp_path: Path,
    message: str,
    mutate,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output, statements = _sentinel_outputs(tmp_path)

    with pytest.raises(runner.GateError, match=message):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=mutate(_pins(rows)),
        )

    assert output.read_bytes() == b"payload sentinel\n"
    assert statements.read_bytes() == b"statements sentinel\n"


@pytest.mark.parametrize(
    "relation",
    [
        "title-start",
        "segment/start",
        "coding-start",
        "anchor",
        "clause",
        "title-generic",
        "title-literal",
        "predicate",
    ],
)
def test_semantic_registry_reordering_aborts_without_emission(
    tmp_path: Path,
    monkeypatch,
    relation: str,
) -> None:
    rows = _rows()
    pins = _pins(rows)
    source_name = {
        "title-start": "TITLE_START_AUTHORITY",
        "segment/start": "SEGMENT_START_AUTHORITY",
        "coding-start": "CODING_START_AUTHORITY",
        "anchor": "ANCHORS",
        "clause": "CLAUSE_TABLE",
        "title-generic": "TITLE_GENERIC_UNIT_FAMILIES",
        "title-literal": "TITLE_LITERAL_FAMILIES",
        "predicate": "PREDICATE_AUTHORITY",
    }[relation]
    source_rows = getattr(runner, source_name)
    monkeypatch.setattr(
        runner,
        source_name,
        (source_rows[1], source_rows[0], *source_rows[2:]),
    )
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output, statements = _sentinel_outputs(tmp_path)

    with pytest.raises(runner.GateError, match=relation):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=pins,
        )

    assert output.read_bytes() == b"payload sentinel\n"
    assert statements.read_bytes() == b"statements sentinel\n"


@pytest.mark.parametrize("mutation", ["short", "reordered"])
def test_wrong_count_or_reordering_is_rejected_without_emission(
    tmp_path: Path,
    mutation: str,
) -> None:
    rows = _rows()
    pins = _pins(rows)
    if mutation == "short":
        changed = rows[:-1]
    else:
        changed = [rows[1], rows[0], *rows[2:]]
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, changed)
    output, statements = _sentinel_outputs(tmp_path)

    with pytest.raises(runner.GateError):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=pins,
        )

    assert output.read_bytes() == b"payload sentinel\n"
    assert statements.read_bytes() == b"statements sentinel\n"


def test_duplicate_json_member_is_rejected_at_any_object_depth(
    tmp_path: Path,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    field_rows.write_text(
        '{"derivation_status":"compiled_numeric_ranges",'
        '"interview_wave":1968,"raw_field_id":"A",'
        '"resolution_reason":"reason",'
        '"source_description":{"nested":1,"nested":2}}\n',
        encoding="utf-8",
    )
    output, statements = _sentinel_outputs(tmp_path)

    with pytest.raises(runner.GateError, match="duplicate JSON member"):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=_pins(rows),
        )

    assert output.read_bytes() == b"payload sentinel\n"
    assert statements.read_bytes() == b"statements sentinel\n"


@pytest.mark.parametrize(
    ("member", "value", "message"),
    [
        ("interview_wave", True, "JSON integer"),
        ("interview_wave", 1968.0, "JSON integer"),
        ("raw_field_id", 1, "JSON string"),
        ("derivation_status", None, "JSON string"),
        ("resolution_reason", False, "JSON string"),
        ("source_description", 1, "JSON string"),
    ],
)
def test_noncanonical_input_member_types_abort_without_emission(
    tmp_path: Path,
    member: str,
    value: object,
    message: str,
) -> None:
    rows = _rows()
    changed = [dict(rows[0])]
    changed[0][member] = value
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, changed)
    output, statements = _sentinel_outputs(tmp_path)

    with pytest.raises(runner.GateError, match=message):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=_pins(rows),
        )

    assert output.read_bytes() == b"payload sentinel\n"
    assert statements.read_bytes() == b"statements sentinel\n"


def test_nonfinite_json_number_is_rejected(tmp_path: Path) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    line = json.dumps(rows[0], sort_keys=True).replace("1968", "NaN", 1)
    field_rows.write_text(line + "\n", encoding="utf-8")

    with pytest.raises(runner.GateError, match="non-finite JSON number"):
        runner.execute_gate(field_rows, pins=_pins(rows))


@pytest.mark.parametrize(
    "collision",
    [
        "input-output",
        "output-statements",
        "input-output-hard-link",
        "input-titles",
        "output-titles",
        "statements-titles",
        "input-titles-hard-link",
    ],
)
def test_path_aliases_fail_before_read_or_write(
    tmp_path: Path,
    collision: str,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output = tmp_path / "output"
    statements = tmp_path / "statements"
    titles = tmp_path / "titles"
    if collision == "input-output":
        output = field_rows
    elif collision == "output-statements":
        statements = output
        output.write_bytes(b"sentinel\n")
    elif collision == "input-output-hard-link":
        output.hardlink_to(field_rows)
    elif collision == "input-titles":
        titles = field_rows
    elif collision == "output-titles":
        titles = output
        output.write_bytes(b"sentinel\n")
    elif collision == "statements-titles":
        titles = statements
        statements.write_bytes(b"sentinel\n")
    elif collision == "input-titles-hard-link":
        titles.hardlink_to(field_rows)
    original = field_rows.read_bytes()

    with pytest.raises(runner.GateError, match="path collision"):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            titles=titles,
            pins=_pins(rows),
        )

    assert field_rows.read_bytes() == original
    if collision in {"output-statements", "output-titles"}:
        assert output.read_bytes() == b"sentinel\n"
    if collision == "statements-titles":
        assert statements.read_bytes() == b"sentinel\n"


def test_gate_opens_input_relation_once(tmp_path: Path, monkeypatch) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    count = 0
    original_open = Path.open

    def counting_open(path: Path, *args, **kwargs):
        nonlocal count
        if path == field_rows:
            count += 1
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", counting_open)
    runner.execute_gate(field_rows, pins=_pins(rows))
    assert count == 1


def test_second_destination_replace_failure_restores_every_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output, statements = _sentinel_outputs(tmp_path)
    titles = tmp_path / "titles.jsonl"
    titles.write_bytes(b"titles sentinel\n")
    original_output = output.read_bytes()
    original_statements = statements.read_bytes()
    original_titles = titles.read_bytes()
    original_replace = runner.os.replace
    replacement_count = 0

    def fail_after_second_replace(source, destination) -> None:
        nonlocal replacement_count
        original_replace(source, destination)
        replacement_count += 1
        if replacement_count == 2:
            raise OSError("injected failure after second replacement")

    monkeypatch.setattr(runner.os, "replace", fail_after_second_replace)

    with pytest.raises(
        runner.GateError,
        match="output transaction failed; prior destinations restored",
    ):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            titles=titles,
            pins=_pins(rows),
        )

    assert replacement_count == 5
    assert output.read_bytes() == original_output
    assert statements.read_bytes() == original_statements
    assert titles.read_bytes() == original_titles
    assert not tuple(tmp_path.glob(".*.a10-r04-*"))


def test_cli_success_emits_complete_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    titles = tmp_path / "titles.jsonl"
    expected_build = runner.build_payload(rows)
    monkeypatch.setattr(
        runner,
        "EXPECTED_A10_R04_PINS",
        runner.pins_from_build(expected_build),
    )

    result = runner.main(
        ["--field-rows", str(field_rows), "--titles", str(titles)]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert len(captured.out) > 4_000
    assert json.loads(captured.out) == expected_build.payload
    assert captured.err == ""
    assert titles.read_bytes() == (
        expected_build.title_header_candidate_relation_bytes
    )


def test_cli_failure_has_empty_stdout_and_preserves_output(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output = tmp_path / "payload.json"
    output.write_bytes(b"sentinel\n")
    bad_pins = replace(_pins(rows), census_payload_sha256="0" * 64)
    monkeypatch.setattr(runner, "EXPECTED_A10_R04_PINS", bad_pins)

    result = runner.main(
        ["--field-rows", str(field_rows), "--output", str(output)]
    )
    captured = capsys.readouterr()

    assert result == 1
    assert captured.out == ""
    assert "A10-R04 abort" in captured.err
    assert output.read_bytes() == b"sentinel\n"
