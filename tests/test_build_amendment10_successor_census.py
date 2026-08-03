"""Focused tests for Amendment 10's fail-closed A10-R04 runner."""

from __future__ import annotations

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
        pins.denotation_candidate_total_occurrence_count,
        pins.denotation_candidate_unselected_count,
        pins.denotation_candidate_overselected_count,
        pins.denotation_candidate_unadjudicated_count,
        pins.denotation_candidate_table_sha256,
    ) == (
        1_114_747,
        2_240_669,
        2_240_669,
        717_823,
        2_240_991,
        0,
        0,
        0,
        "8ecc92a6a134fec30a3575e2eff8305dd1d6d17f6230d75555262c38b5300a7f",
    )
    assert (
        pins.denotation_start_occurrence_row_count,
        pins.denotation_start_occurrence_byte_count,
        pins.denotation_start_occurrence_sha256,
        pins.denotation_start_partition_rows,
    ) == (
        2_240_669,
        268_223_757,
        "6b239ef7b534c0b9c6f5350808b20017f9b3392f3f3d91cd56d00f2d9b9a33d5",
        (
            ("whole_domain_denotation", 8_234),
            ("explicit_no_whole_domain_denotation", 4_532),
            ("explicit_no_denotation", 2_227_903),
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
        "ef31ee7f41ab33b0ad683c6f5a8597258277e5a19932ac850d235ced28a2d95f",
        "df58afe79ea36b39e3a39477b7566f7e0d47dd34c75c83b669fcf072a8235345",
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


def test_valid_gate_emits_only_after_every_pin_passes(tmp_path: Path) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    output = tmp_path / "payload.json"
    statements = tmp_path / "statements.jsonl"
    _write_rows(field_rows, rows)

    build = runner.execute_gate(
        field_rows,
        output=output,
        statements=statements,
        pins=_pins(rows),
    )

    assert json.loads(output.read_text(encoding="utf-8")) == build.payload
    emitted_table = [
        json.loads(line)
        for line in statements.read_text(encoding="utf-8").splitlines()
    ]
    assert emitted_table == list(build.statement_rows)


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
    ["segment/start", "coding-start", "anchor", "clause", "predicate"],
)
def test_semantic_registry_reordering_aborts_without_emission(
    tmp_path: Path,
    monkeypatch,
    relation: str,
) -> None:
    rows = _rows()
    pins = _pins(rows)
    source_name = {
        "segment/start": "SEGMENT_START_AUTHORITY",
        "coding-start": "CODING_START_AUTHORITY",
        "anchor": "ANCHORS",
        "clause": "CLAUSE_TABLE",
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
    ["input-output", "output-statements", "input-output-hard-link"],
)
def test_path_aliases_fail_before_read_or_write(
    tmp_path: Path,
    collision: str,
) -> None:
    rows = _rows()
    field_rows = tmp_path / "rows.jsonl"
    _write_rows(field_rows, rows)
    output = field_rows if collision == "input-output" else tmp_path / "same"
    statements = tmp_path / "statements"
    if collision == "output-statements":
        statements = output
        output.write_bytes(b"sentinel\n")
    elif collision == "input-output-hard-link":
        output.hardlink_to(field_rows)
    original = field_rows.read_bytes()

    with pytest.raises(runner.GateError, match="path collision"):
        runner.execute_gate(
            field_rows,
            output=output,
            statements=statements,
            pins=_pins(rows),
        )

    assert field_rows.read_bytes() == original
    if collision == "output-statements":
        assert output.read_bytes() == b"sentinel\n"


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
