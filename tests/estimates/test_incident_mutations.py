"""Mutation battery for the frozen first-estimates incident contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from populace_dynamics.estimates import publication, runner

_LITERAL_SCHEMA_VERSION = "first_estimates_incident.v1"
_LITERAL_INCIDENT_KEYS = frozenset(
    {
        "schema_version",
        "incident_index",
        "timestamp_utc",
        "phase",
        "reason",
        "reason_detail",
        "registration_reference",
        "configuration_echo",
        "artifact_path",
    }
)
_LITERAL_PHASES = (
    "preparation",
    "invariant",
    "compute",
    "publication",
)


def _configuration() -> dict[str, Any]:
    return runner.registered_configuration_echo(
        registration_reference="issue-42-comment-1234567",
        parameter_bundle={"bundle_sha256": "c" * 64},
    )


def _record(
    *,
    index: int = 1,
    phase: str = "preparation",
    reason: str = "external_parameter_checkout_unavailable",
) -> dict[str, Any]:
    configuration = _configuration()
    return {
        "schema_version": _LITERAL_SCHEMA_VERSION,
        "incident_index": index,
        "timestamp_utc": "2026-07-24T12:34:56Z",
        "phase": phase,
        "reason": reason,
        "reason_detail": "pinned checkout was not mounted",
        "registration_reference": configuration["registration_reference"],
        "configuration_echo": configuration,
        "artifact_path": None,
    }


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    return root


def _validate(
    record: dict[str, Any],
    *,
    root: Path,
    filename: str = "first_estimates_incident_1.json",
    expected_configuration: dict[str, Any] | None = None,
    validate_artifact_existence: bool = True,
) -> None:
    publication.validate_first_estimates_incident(
        record,
        path=root / "runs" / filename,
        expected_configuration_echo=(
            _configuration()
            if expected_configuration is None
            else expected_configuration
        ),
        repository_root=root,
        validate_artifact_existence=validate_artifact_existence,
    )


@pytest.mark.parametrize("missing_key", sorted(_LITERAL_INCIDENT_KEYS))
def test__incident_mutation__rejects_each_deleted_schema_key(
    tmp_path,
    missing_key,
):
    root = _repository(tmp_path)
    record = _record()
    del record[missing_key]

    with pytest.raises(ValueError, match="incident keys"):
        _validate(record, root=root)


def test__incident_mutation__rejects_an_added_schema_key(tmp_path):
    root = _repository(tmp_path)
    record = _record()
    record["projection_result"] = [1.0]

    with pytest.raises(ValueError, match="incident keys"):
        _validate(record, root=root)


def test__incident_mutation__pins_literal_schema_version(tmp_path):
    root = _repository(tmp_path)
    record = _record()

    assert record["schema_version"] == "first_estimates_incident.v1"
    _validate(record, root=root)

    record["schema_version"] = "first_estimates_incident.v2"
    with pytest.raises(ValueError, match="schema version"):
        _validate(record, root=root)


@pytest.mark.parametrize(
    ("index", "filename", "error_type", "message"),
    [
        (False, "first_estimates_incident_1.json", TypeError, "positive"),
        (0, "first_estimates_incident_1.json", TypeError, "positive"),
        ("1", "first_estimates_incident_1.json", TypeError, "positive"),
        (1, "first_estimates_incident_2.json", ValueError, "filename"),
        (1, "first_estimates_incident_01.json", ValueError, "filename"),
    ],
)
def test__incident_mutation__rejects_invalid_index_and_filename_pairs(
    tmp_path,
    index,
    filename,
    error_type,
    message,
):
    root = _repository(tmp_path)
    record = _record()
    record["incident_index"] = index

    with pytest.raises(error_type, match=message):
        _validate(record, root=root, filename=filename)


def test__incident_mutation__rejects_noncanonical_parent_directory(tmp_path):
    root = _repository(tmp_path)
    record = _record()

    with pytest.raises(ValueError, match="canonical runs directory"):
        publication.validate_first_estimates_incident(
            record,
            path=root / "elsewhere" / "first_estimates_incident_1.json",
            expected_configuration_echo=_configuration(),
            repository_root=root,
        )


@pytest.mark.parametrize(
    "phase",
    [
        "prepare",
        "validation",
        "computation",
        "publish",
        "",
    ],
)
def test__incident_mutation__rejects_phase_outside_literal_enum(
    tmp_path,
    phase,
):
    root = _repository(tmp_path)
    record = _record()
    record["phase"] = phase

    with pytest.raises(ValueError, match="frozen enum"):
        _validate(record, root=root)


@pytest.mark.parametrize(
    ("field", "mutant"),
    [
        ("reason", 17),
        ("reason_detail", {"message": "not free text"}),
        ("registration_reference", ["issue-42-comment-1234567"]),
        ("configuration_echo", "not an object"),
        ("artifact_path", 17),
    ],
)
def test__incident_mutation__rejects_wrong_declared_field_types(
    tmp_path,
    field,
    mutant,
):
    root = _repository(tmp_path)
    record = _record()
    record[field] = mutant

    with pytest.raises((TypeError, ValueError)):
        _validate(record, root=root)


@pytest.mark.parametrize(
    "timestamp",
    [
        None,
        1,
        "2026-07-24",
        "2026-07-24T12:34:56",
        "2026-07-24T12:34:56+00:00",
    ],
)
def test__incident_mutation__rejects_non_iso_utc_timestamp(
    tmp_path,
    timestamp,
):
    root = _repository(tmp_path)
    record = _record()
    record["timestamp_utc"] = timestamp

    with pytest.raises(ValueError, match="ISO-8601"):
        _validate(record, root=root)


def test__incident_mutation__rejects_empty_machine_reason(tmp_path):
    root = _repository(tmp_path)
    record = _record()
    record["reason"] = ""

    with pytest.raises(ValueError, match="must not be empty"):
        _validate(record, root=root)


def test__incident_mutation__rejects_configuration_echo_drift(tmp_path):
    root = _repository(tmp_path)
    expected = _configuration()
    record = _record()
    record["configuration_echo"] = copy.deepcopy(expected)
    record["configuration_echo"]["projection"]["root_seeds"][0] += 1

    with pytest.raises(ValueError, match="pre-compute object"):
        _validate(
            record,
            root=root,
            expected_configuration=expected,
        )


def test__incident_mutation__numeric_array_predicate_is_nested_and_literal():
    assert publication._contains_numeric_array(
        {"outer": {"inner": ["label", 1.0]}}
    )
    assert not publication._contains_numeric_array(
        {"outer": {"inner": ["label", True]}}
    )


def test__incident_mutation__validator_invokes_outside_echo_array_guard(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    record = _record()

    # Registered numeric lists inside the pre-compute echo are legitimate.
    _validate(record, root=root)
    assert record["configuration_echo"]["projection"]["draw_indices"]

    monkeypatch.setattr(publication, "_contains_numeric_array", lambda _: True)
    with pytest.raises(ValueError, match="numeric array outside"):
        _validate(record, root=root)


def test__incident_mutation__pins_retry_eligibility_truth_matrix():
    for phase in _LITERAL_PHASES:
        for reason in (
            "external_dependency_unavailable",
            "dependency_unavailable",
        ):
            expected = phase in {
                "preparation",
                "compute",
            } and reason.startswith("external_")
            record = _record(phase=phase, reason=reason)
            assert publication.incident_is_retry_eligible(record) is expected

    non_string_reason = _record()
    non_string_reason["reason"] = ["external_dependency_unavailable"]
    assert not publication.incident_is_retry_eligible(non_string_reason)


def test__incident_mutation__artifact_path_iff_rule_is_fail_closed(tmp_path):
    root = _repository(tmp_path)
    record = _record(phase="compute")
    record["artifact_path"] = "runs/first_estimates_v1.json"
    with pytest.raises(ValueError, match="artifact_path"):
        _validate(record, root=root)

    partial = root / "runs" / "first_estimates_v1.json"
    partial.write_text('{"partial":true}\\n', encoding="utf-8")
    record = _record(phase="publication")
    with pytest.raises(ValueError, match="artifact_path"):
        _validate(record, root=root)

    record["artifact_path"] = "runs/first_estimates_v1.json"
    _validate(record, root=root)

    record["artifact_path"] = "../first_estimates_v1.json"
    with pytest.raises(ValueError, match="escapes"):
        _validate(record, root=root)


def test__incident_mutation__writer_appends_contiguous_indices(tmp_path):
    root = _repository(tmp_path)
    configuration = _configuration()
    writer_kwargs = {
        "repository_root": root,
        "phase": "preparation",
        "reason": "external_parameter_checkout_unavailable",
        "reason_detail": "pinned checkout was not mounted",
        "registration_reference": configuration["registration_reference"],
        "configuration_echo": configuration,
        "timestamp_utc": "2026-07-24T12:34:56Z",
    }

    first = publication._write_first_estimates_incident_for_test(
        **writer_kwargs
    )
    second = publication._write_first_estimates_incident_for_test(
        **writer_kwargs
    )

    assert first.name == "first_estimates_incident_1.json"
    assert second.name == "first_estimates_incident_2.json"
    assert json.loads(first.read_text(encoding="utf-8"))["incident_index"] == 1
    assert (
        json.loads(second.read_text(encoding="utf-8"))["incident_index"] == 2
    )


def test__incident_mutation__writer_rejects_noncontiguous_history(tmp_path):
    root = _repository(tmp_path)
    configuration = _configuration()
    (root / "runs" / "first_estimates_incident_2.json").touch()

    with pytest.raises(RuntimeError, match="not contiguous"):
        publication._write_first_estimates_incident_for_test(
            repository_root=root,
            phase="preparation",
            reason="external_parameter_checkout_unavailable",
            reason_detail="pinned checkout was not mounted",
            registration_reference=configuration["registration_reference"],
            configuration_echo=configuration,
            timestamp_utc="2026-07-24T12:34:56Z",
        )

    assert not (root / "runs" / "first_estimates_incident_1.json").exists()
