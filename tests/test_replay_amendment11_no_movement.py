"""Executable fail-closed and satisfiable-fixture checks for A11-R05."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace

import pytest

from populace_dynamics.data import psid_missing_reason_authority as authority
from scripts import replay_amendment11_no_movement as replay

# Final §25 byte-identity pin for the frozen replay script.
EXPECTED_REPLAY_SCRIPT_BYTE_SIZE = 32_330
EXPECTED_REPLAY_SCRIPT_SHA256 = (
    "597670958b6609740eb4742c4144fb448026df82c767ece4db3e30777d6b77e6"
)
EXPECTED_ORIGINATING_RECORD_SPECS = (
    {
        "path": (
            "data/external/amendment_11_originating_records/"
            "claude-ce-v3compiler-codebook-report.md"
        ),
        "byte_size": 15_872,
        "sha256": (
            "245cedcd3f5d3ecd2245e8acec14e56511e973707cc5022cb8b75e94a387a605"
        ),
        "span_start": 13_605,
        "span_end": 14_213,
        "span_byte_size": 608,
        "span_sha256": (
            "beada0568d204372f7d26b15f19602aa5ff11c6b8590c8a5d6830d37575d8fb5"
        ),
    },
    {
        "path": (
            "data/external/amendment_11_originating_records/"
            "claude-ce-amend10-report.md"
        ),
        "byte_size": 17_745,
        "sha256": (
            "9165cd527964bbefa10cb20c8afe69444c776b2b44956dbef239360a6f8b1ddb"
        ),
        "span_start": 13_566,
        "span_end": 13_807,
        "span_byte_size": 241,
        "span_sha256": (
            "a7854580bca100104df376530aa2a1204c3d7dc5360ad2c91d80c8790d0d92d0"
        ),
    },
)
EXPECTED_ORIGINATING_RECORD_DOMAIN_SHA256 = (
    "3921b4c3c4c6658a164b57a48fd1ec35a806cd97adfca05a4389523e692c9f3d"
)


def test_replay_script_matches_exact_documented_byte_pin():
    script = (
        replay.REPOSITORY_ROOT / "scripts/replay_amendment11_no_movement.py"
    )
    raw = script.read_bytes()
    assert len(raw) == EXPECTED_REPLAY_SCRIPT_BYTE_SIZE
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_REPLAY_SCRIPT_SHA256


def test_committed_originating_records_match_full_byte_and_span_pins():
    assert authority.ORIGINATING_RECORD_SPECS == (
        EXPECTED_ORIGINATING_RECORD_SPECS
    )
    observed_specs = []
    for spec in EXPECTED_ORIGINATING_RECORD_SPECS:
        raw = (replay.REPOSITORY_ROOT / spec["path"]).read_bytes()
        assert len(raw) == spec["byte_size"]
        assert hashlib.sha256(raw).hexdigest() == spec["sha256"]

        start = spec["span_start"]
        end = spec["span_end"]
        span = raw[start:end]
        assert 0 <= start < end <= len(raw)
        assert end - start == spec["span_byte_size"]
        assert len(span) == spec["span_byte_size"]
        assert hashlib.sha256(span).hexdigest() == spec["span_sha256"]
        observed_specs.append(spec)

    encoded_specs = (
        json.dumps(
            observed_specs,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )
    assert hashlib.sha256(encoded_specs).hexdigest() == (
        EXPECTED_ORIGINATING_RECORD_DOMAIN_SHA256
    )
    assert authority.EXPECTED_ORIGINATING_RECORD_DOMAIN_SHA256 == (
        EXPECTED_ORIGINATING_RECORD_DOMAIN_SHA256
    )


def _numeric_row(
    field: str,
    status: str,
    position: int,
) -> dict[str, object]:
    values: dict[str, object] = {
        "numeric_grammar_derivation_id": f"fixture-derivation:{position}",
        "interview_wave": 1968,
        "raw_field_id": field,
        "dictionary_field_row_ids": [f"dictionary:{field}"],
        "dictionary_field_rows_sha256": f"{position + 1:064x}",
        "codebook_field_row_ids": [f"codebook:{field}"],
        "codebook_field_rows_sha256": f"{position + 11:064x}",
        "source_format_projection": [],
        "source_meaning_projection": [],
        "dictionary_field_meaning": f"fixture field {field}",
        "derived_parse_kind": "numeric",
        "normalized_format_profile": {"width": 1},
        "nonmissing_observation_count": 1,
        "derivation_status": status,
        "padding_rule": None,
        "registered_numeric_grammar": None,
    }
    assert tuple(values) == replay.NUMERIC_ROW_KEYS
    return values


def _fields() -> tuple[replay.FixtureField, ...]:
    return (
        replay.FixtureField(
            numeric_grammar_derivation_row=_numeric_row(
                "V1", replay.TERMINALS[0], 0
            ),
            settled_entries=(
                {
                    "typed_disposition": "missing",
                    "missing_reason_code": "fixture-reason:V1:0",
                },
                {
                    "typed_disposition": "json_integer",
                    "missing_reason_code": None,
                },
            ),
            resolution_reason=None,
            storage=replay.FixtureStorage(3, 3, 0, 975),
        ),
        replay.FixtureField(
            numeric_grammar_derivation_row=_numeric_row(
                "V2", replay.TERMINALS[4], 1
            ),
            settled_entries=(
                {
                    "typed_disposition": "rational",
                    "missing_reason_code": None,
                },
            ),
            resolution_reason=None,
            storage=replay.FixtureStorage(0, 0, 0, 0),
        ),
        replay.FixtureField(
            numeric_grammar_derivation_row=_numeric_row(
                "V3", replay.TERMINALS[8], 2
            ),
            settled_entries=(
                {
                    "typed_disposition": "missing",
                    "missing_reason_code": "fixture-reason:V3:0",
                },
            ),
            resolution_reason="fixture_unsupported_token",
            storage=replay.FixtureStorage(2, 0, 2, 650),
        ),
    )


def _reason_insensitive_classifier(row, _entries):
    return row["derivation_status"]


def test_production_preflight_stops_at_source_disposition_boundary():
    evidence = replay.production_blocker_evidence()
    assert evidence["blocker"] == (
        "blocked_source_missing_disposition_underdetermined"
    )
    assert evidence["source_member_count"] == 561_873
    assert evidence["source_literal_entry_count"] == 524_590
    assert evidence["source_numeric_range_entry_count"] == 37_283
    assert evidence["source_authorized_missing_literal_count"] == 52
    assert evidence["lexical_missing_candidate_count"] == 231_263
    assert evidence["literal_lexical_other_count"] == 293_327
    assert evidence["all_member_lexical_other_count"] == 330_610
    assert 231_263 + 293_327 == 524_590
    assert 293_327 + 37_283 == 330_610
    assert evidence["directly_disproven_lexical_candidate_minimum"] == 61
    assert evidence["context_required_lexical_candidate_minimum"] == 118
    assert evidence["literal_disposition_action"] == (
        "classify_source_authorized_then_block_underdetermined"
    )
    assert evidence["blocked_literal_entry_count"] == 524_538
    assert 52 + 524_538 == evidence["source_literal_entry_count"]
    assert evidence["structural_null_entry_count"] == 37_283
    assert evidence["source_authorized_nonempty_reason_code_count"] == 52
    assert evidence["accepted_output_nonempty_reason_code_count"] == 0
    assert evidence["complete_settled_relation_exists"] is False
    assert evidence["production_replay_started"] is False
    assert evidence["production_replay_complete"] is False
    assert evidence["revision_13_full_relation_identity_available"] is False
    assert evidence["accepted_output_emitted"] is False
    historical = evidence["historical_predecessor_capacity_evidence"]
    assert historical["status"] == ("ratified_revision_12_census_reproduced")
    assert historical["amendment_11_inference_authorized"] is False
    assert historical["field_count"] == 89_599
    assert historical["ratified_predecessor_terminal_vector"] == [
        8_025,
        273,
        77,
        1,
        67_316,
        1_145,
        0,
        1,
        421,
        12_340,
    ]
    assert historical["t_plus_field_count"] == 76_837
    assert historical["t_minus_field_count"] == 12_762
    assert historical["revision_12_logical_member_count"] == 376_171_374_879
    assert historical["four_shape_floor_bytes"] == 122_255_013_691_442
    assert "expected_a11_delta_movement_row_count" not in historical
    assert "revision_13_full_relation_identity_prefix" not in historical


def test_revision_12_capacity_audit_mints_no_amendment_11_inference():
    evidence = replay.run_historical_capacity_audit()
    assert evidence["status"] == "ratified_revision_12_census_reproduced"
    assert evidence["amendment_11_inference_authorized"] is False
    assert evidence["amendment_11_inference_blocker"] == (
        "blocked_source_missing_disposition_underdetermined"
    )


def test_production_preflight_rejects_absent_or_mutated_authority(tmp_path):
    absent = tmp_path / "absent.json"
    with pytest.raises(replay.ReplayError, match="unreadable"):
        replay.production_blocker_evidence(absent)

    mutated = tmp_path / "mutated.json"
    raw = bytearray(replay.AUTHORITY_ARTIFACT.read_bytes())
    raw[100] ^= 1
    mutated.write_bytes(raw)
    with pytest.raises(replay.ReplayError):
        replay.production_blocker_evidence(mutated)


def test_production_cli_emits_no_stdout_or_pass(monkeypatch, capsys):
    evidence = {"blocked_literal_entry_count": 524_538}

    def expected_blocker():
        raise replay.SourceMissingDispositionUnderdetermined(evidence)

    monkeypatch.setattr(replay, "run_production_gate", expected_blocker)
    assert replay.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "blocked_source_missing_disposition_underdetermined" in captured.err
    assert "524538 literal entries" in captured.err
    assert "pass" not in captured.err


def test_production_gate_delegates_to_settlement_and_rejects_return(
    monkeypatch,
):
    authority = {"fixture": "validated authority"}
    evidence = {"blocked_literal_entry_count": 524_538}
    calls = []
    monkeypatch.setattr(
        replay, "validate_committed_authority", lambda _path: authority
    )
    monkeypatch.setattr(
        replay, "validate_authority_artifact", lambda _authority: None
    )
    monkeypatch.setattr(
        replay, "_production_blocker_evidence", lambda _authority: evidence
    )
    monkeypatch.setattr(
        replay,
        "authenticated_source_derivations",
        lambda _root: iter(("authenticated derivation",)),
    )

    def expected_terminal(derivations, observed_authority):
        calls.append((list(derivations), observed_authority))
        raise replay.MissingReasonAuthorityError(
            replay.EXPECTED_SOURCE_SETTLEMENT_BLOCKER
        )

    monkeypatch.setattr(
        replay, "settle_missing_reason_codes", expected_terminal
    )
    with pytest.raises(replay.SourceMissingDispositionUnderdetermined):
        replay.run_production_gate()
    assert calls == [(["authenticated derivation"], authority)]

    monkeypatch.setattr(
        replay, "settle_missing_reason_codes", lambda _rows, _authority: ()
    )
    with pytest.raises(replay.ReplayError, match="returned"):
        replay.run_production_gate()


def test_production_gate_translates_only_exact_terminal_blocker(monkeypatch):
    monkeypatch.setattr(
        replay, "validate_committed_authority", lambda _path: {}
    )
    monkeypatch.setattr(
        replay,
        "_production_blocker_evidence",
        lambda _authority: {"blocked_literal_entry_count": 524_538},
    )
    monkeypatch.setattr(
        replay,
        "authenticated_source_derivations",
        lambda _root: iter(("authenticated derivation",)),
    )

    def wrong_blocker(_derivations, _authority):
        raise replay.MissingReasonAuthorityError("wrong terminal blocker")

    monkeypatch.setattr(replay, "settle_missing_reason_codes", wrong_blocker)
    with pytest.raises(replay.ReplayError, match="before the expected"):
        replay.run_production_gate()


def test_production_script_resolves_worktree_without_pythonpath(tmp_path):
    script = (
        replay.REPOSITORY_ROOT
        / "scripts"
        / "replay_amendment11_no_movement.py"
    )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy; "
                f"runpy.run_path({str(script)!r}, "
                "run_name='amendment11_import_probe')"
            ),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""


@pytest.mark.parametrize(
    ("constant", "replacement", "message"),
    (
        (
            "EXPECTED_TERMINAL_VECTOR",
            (0,) * 10,
            "terminal vector drift",
        ),
        (
            "EXPECTED_SEVEN_KEY_MEMBER_COUNT",
            replay.EXPECTED_SEVEN_KEY_MEMBER_COUNT + 1,
            "four-shape population decomposition drift",
        ),
        (
            "LITERAL_LEXICAL_OTHER_COUNT",
            replay.LITERAL_LEXICAL_OTHER_COUNT + 1,
            "lexical literal partition drift",
        ),
        (
            "ALL_MEMBER_LEXICAL_OTHER_COUNT",
            replay.ALL_MEMBER_LEXICAL_OTHER_COUNT + 1,
            "all-member lexical-other partition drift",
        ),
    ),
)
def test_production_pin_mutation_is_discovered(
    monkeypatch, constant, replacement, message
):
    monkeypatch.setattr(replay, constant, replacement)
    with pytest.raises(replay.ReplayError, match=message):
        replay.production_blocker_evidence()


def test_constructible_fixture_replays_every_required_r05_projection():
    result = replay.replay_constructible_fixture(
        _fields(), _reason_insensitive_classifier
    )
    assert result["status"] == "pass"
    assert result["fixture_only"] is True
    assert (
        result["conditional_on_supplied_synthetic_missing_dispositions"]
        is True
    )
    assert result["production_source_authority_claimed"] is False
    assert result["field_count"] == 3
    assert result["terminal_vector"] == [1, 0, 0, 0, 1, 0, 0, 0, 1, 0]
    assert result["missing_member_count"] == 2
    assert result["nonmissing_member_count"] == 2
    assert result["included_storage"] == {
        "logical_member_count": 3,
        "explicit_member_count": 3,
        "analytic_member_count": 0,
        "four_shape_floor_bytes": 975,
    }
    assert result["excluded_storage"] == {
        "logical_member_count": 2,
        "explicit_member_count": 0,
        "analytic_member_count": 2,
        "four_shape_floor_bytes": 650,
    }
    assert result["t_plus_field_count"] == 2
    assert result["t_minus_field_count"] == 1
    assert result["failure_reason_rows"] == [
        {
            "derivation_status": replay.TERMINALS[8],
            "resolution_reason": "fixture_unsupported_token",
            "field_keys": [[1968, "V3"]],
        }
    ]
    assert result["delta_movement_rows"] == []
    assert result["delta_movement_sha256"] == replay.EMPTY_ARRAY_SHA256
    identity = result["fixture_full_relation_identity"]
    assert identity[0:2] == [
        "amendment_11_constructible_fixture_full_relation_identity",
        3,
    ]
    assert len(identity) == 6
    assert all(
        len(value) == 64 for value in (identity[2], identity[3], identity[5])
    )
    assert type(identity[4]) is int and identity[4] > 0


def test_reason_string_sensitive_classifier_is_rejected():
    def classifier(row, entries):
        if any(
            str(entry["missing_reason_code"]).startswith("counterfactual")
            for entry in entries
            if entry["typed_disposition"] == "missing"
        ):
            return replay.TERMINALS[9]
        return row["derivation_status"]

    with pytest.raises(replay.ReplayError, match="reason-string-sensitive"):
        replay.replay_constructible_fixture(_fields(), classifier)


def test_terminal_movement_is_rejected():
    def classifier(row, _entries):
        if row["raw_field_id"] == "V2":
            return replay.TERMINALS[9]
        return row["derivation_status"]

    with pytest.raises(replay.ReplayError, match="nonempty delta movement"):
        replay.replay_constructible_fixture(_fields(), classifier)


@pytest.mark.parametrize(
    ("field_position", "entry_position", "replacement", "message"),
    (
        (0, 0, None, "unsettled missing member"),
        (0, 1, "invented", "nonmissing reason"),
    ),
)
def test_unsettled_or_overassigned_member_is_rejected(
    field_position, entry_position, replacement, message
):
    fields = list(_fields())
    entries = [dict(entry) for entry in fields[field_position].settled_entries]
    entries[entry_position]["missing_reason_code"] = replacement
    fields[field_position] = replace(
        fields[field_position], settled_entries=tuple(entries)
    )
    with pytest.raises(replay.ReplayError, match=message):
        replay.replay_constructible_fixture(
            tuple(fields), _reason_insensitive_classifier
        )


def test_duplicate_opaque_reason_code_is_rejected():
    fields = list(_fields())
    entries = [dict(entry) for entry in fields[2].settled_entries]
    entries[0]["missing_reason_code"] = "fixture-reason:V1:0"
    fields[2] = replace(fields[2], settled_entries=tuple(entries))
    with pytest.raises(replay.ReplayError, match="duplicate opaque"):
        replay.replay_constructible_fixture(
            tuple(fields), _reason_insensitive_classifier
        )


def test_numeric_row_mutation_changes_fixture_relation_identity():
    baseline = replay.replay_constructible_fixture(
        _fields(), _reason_insensitive_classifier
    )
    fields = list(_fields())
    row = copy.deepcopy(fields[0].numeric_grammar_derivation_row)
    row["dictionary_field_meaning"] = "changed source meaning"
    fields[0] = replace(fields[0], numeric_grammar_derivation_row=row)
    changed = replay.replay_constructible_fixture(
        tuple(fields), _reason_insensitive_classifier
    )
    before = baseline["fixture_full_relation_identity"]
    after = changed["fixture_full_relation_identity"]
    assert before[0:3] == after[0:3]
    assert before[3:] != after[3:]


def test_reason_mutation_changes_field_source_identity_but_not_terminal():
    baseline = replay.replay_constructible_fixture(
        _fields(), _reason_insensitive_classifier
    )
    fields = list(_fields())
    entries = [dict(entry) for entry in fields[0].settled_entries]
    entries[0]["missing_reason_code"] = "fixture-reason:V1:changed"
    fields[0] = replace(fields[0], settled_entries=tuple(entries))
    changed = replay.replay_constructible_fixture(
        tuple(fields), _reason_insensitive_classifier
    )
    assert changed["terminal_vector"] == baseline["terminal_vector"]
    assert changed["delta_movement_rows"] == []
    before = baseline["fixture_full_relation_identity"]
    after = changed["fixture_full_relation_identity"]
    assert before[0:4] == after[0:4]
    assert before[4:] != after[4:]
