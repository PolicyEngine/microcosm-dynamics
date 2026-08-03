"""Focused tests for Amendment 10's fail-closed A10-R04 runner."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import build_amendment10_successor_census as runner


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
            "This variable represents an amount in whole dollars.",
        ),
        _row(1968, "B", "compiled_source_numeric_grammar", None),
        _row(1968, "C", "value_code_domain_no_numeric_grammar", None),
        _row(1968, "D", "unsupported_source_numeric_format", None),
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
            "denotation candidate",
            "denotation candidate table",
            lambda pins: replace(
                pins,
                denotation_candidate_table_sha256="0" * 64,
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
