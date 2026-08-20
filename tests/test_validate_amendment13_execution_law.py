"""Tests for Amendment 13's Amendment-16-governed execution law."""

from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_amendment13_execution_law as a13  # noqa: E402

A17_TEST_MUTATIONS = (
    "revision_general_test_expected_domain_forged",
    "revision_general_test_revision17_accepted",
    "activation_transition_full_pinned_battery_bypassed",
)
A17_FULL_PINNED_BATTERY_COMMAND = (
    f"{sys.executable} -m pytest -q "
    "tests/test_validate_amendment13_execution_law.py"
)
A17_FULL_PINNED_BATTERY_COLLECTED = 76
A18_FULL_PINNED_BATTERY_COLLECTED = 107
A18_TEST_MUTATIONS = (
    "tier2_build_input_domain_preimage_forged",
    "tier2_r05_current_snapshot_or_historical_binding_forged",
    "tier2_r06_result_or_lifecycle_forged",
)
A18_MUTATION_DOMAIN_SHA256 = (
    "1bf9f6d30461d003cab597a405cb5cc9855273372ed3e7e5b36b1627eaa11108"
)
A19_FULL_PINNED_BATTERY_COLLECTED = 201
A19_TEST_MUTATIONS = (
    "source_purpose_totality_or_binding_disposition_forged",
    "hierarchy_preproof_final_digest_order_forged",
    "r06_successor_program_stop_numbering_forged",
)
A19_MUTATION_DOMAIN_BYTE_SIZE = 151
A19_MUTATION_DOMAIN_SHA256 = (
    "002aa021325c18e311cc778562ad0e937468a90c378db0740290fcf617929101"
)
A20_TEST_MUTATIONS = (
    "shared_source_domain_or_statement_locator_forged",
    "missing_reason_rule_or_exact_cover_forged",
    "purpose_authority_or_totality_forged",
    "prompt_field_or_semantic_binding_forged",
    "r04_order_source_binding_or_q5_shape_forged",
    "r06_collection_or_lifecycle_order_forged",
    "receipt_verdict_or_scratch_transition_forged",
    "amendment20_terminal_pin_or_suffix_route_forged",
    "evidence_freeze_identity_shadow_or_status_forged",
    "failure_shadow_nonemission_provenance_forged",
    "determined_as_source_underdetermined_without_ruling_forged",
    "source_underdetermined_as_no_applicable_purpose_forged",
    "source_underdetermined_a4_census_binding_forged",
    "completed_ontology_new_arm_omitted",
    "coordinate_distinct_questionnaire_spans_collapsed_to_one_body_forged",
)


@pytest.fixture(scope="module")
def execution_law():
    value = a13.build_execution_law()
    a13.validate_execution_law(value)
    return value


@pytest.fixture(scope="module")
def rejected_mutations(execution_law):
    return a13.run_mutation_tests(execution_law)


@pytest.fixture(scope="module")
def rejected_enforcement_mutations(execution_law):
    return a13.run_enforcement_mutation_tests(execution_law)


def _a13_closure_material():
    closure = copy.deepcopy(a13.A13_EXPECTED_CLOSURE)
    closure_raw = a13.canonical_json_bytes(closure)
    binding = a13._closure_binding(a13.A13_CLOSURE_PATH, closure_raw)
    verdicts = {
        row["path"]: (ROOT / row["path"]).read_bytes()
        for row in closure["verdict_artifacts"]
    }
    design_raw = a13._git(
        "show", f"{a13.A13_MERGED_RATIFICATION_COMMIT}:{a13.DESIGN_PATH}"
    )
    assert isinstance(design_raw, bytes)
    return closure, closure_raw, binding, verdicts, design_raw


def _operativity_materials():
    return _a13_closure_material(), a13._synthetic_closure_material()


def _synthetic_registry_context(revision):
    amendment_numbers = tuple(range(13, revision - 1))
    context = {
        "path": a13.DESIGN_PATH,
        "ratification_commit": "a" * 40,
        "revision": revision,
        "blob_sha256": "b" * 64,
        "ratification_closures": [
            {
                "path": (
                    f"docs/analysis/amendment_{amendment_number}_ratification/"
                    "closure_v1.json"
                ),
                "raw_byte_size": amendment_number,
                "raw_sha256": f"{amendment_number:064x}",
            }
            for amendment_number in amendment_numbers
        ],
    }
    if revision >= a13.COMBINED_ACTIVATION_REVISION:
        context["ratification_closures"][1] = copy.deepcopy(
            a13.A14_HISTORICAL_CLOSURE_BINDING
        )
        context["ratification_closures"][2] = {
            "path": a13.A18_HISTORICAL_R05_BINDING["closure_path"],
            "raw_byte_size": a13.A18_HISTORICAL_R05_BINDING[
                "closure_byte_size"
            ],
            "raw_sha256": a13.A18_HISTORICAL_R05_BINDING["closure_raw_sha256"],
        }
    return context


def _amendment19_successor(amendment18):
    return amendment18 + (
        b"\n## 33. AMENDMENT SECTION \xe2\x80\x94 Amendment 19: "
        b"synthetic successor\n\nProspective successor.\n"
    )


def _amendment20_successor(amendment19):
    return amendment19 + (
        b"\n## 34. AMENDMENT SECTION \xe2\x80\x94 Amendment 20: "
        b"synthetic successor\n\nProspective successor.\n"
    )


def _historical_amendment19_implementation_pins():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    return a13._parse_amendment19_implementation_pins(
        raw[: a13.REVISION21_BYTE_SIZE]
    )


def _select_historical_r05_fixture(context, validated_closures):
    """Mirror the closed selector law without inventing a production API."""

    context = a13._validate_registry_ratification_context(context)
    amendment_numbers = a13._ratification_amendment_numbers(
        context["revision"]
    )
    assert context["revision"] >= 18
    assert amendment_numbers == tuple(range(13, context["revision"] - 1))
    assert tuple(validated_closures) == amendment_numbers
    assert amendment_numbers[2] == 15
    assert context["ratification_closures"][2] == {
        "path": a13.A18_HISTORICAL_R05_BINDING["closure_path"],
        "raw_byte_size": a13.A18_HISTORICAL_R05_BINDING["closure_byte_size"],
        "raw_sha256": a13.A18_HISTORICAL_R05_BINDING["closure_raw_sha256"],
    }
    assert validated_closures[15] == a13.A15_EXPECTED_CLOSURE
    return copy.deepcopy(a13.A18_HISTORICAL_R05_BINDING)


def _assert_revision_general_expectation(revision, candidate_expected):
    assert type(revision) is int
    assert revision == 16 or revision >= 18
    assert tuple(candidate_expected) == tuple(range(13, revision - 1))


def _expected_terminal_operativity_domain(revision):
    expected = tuple(range(13, revision - 1))
    _assert_revision_general_expectation(revision, expected)
    return expected


def _assert_revision_general_public_result(revision, closures):
    assert tuple(closures) == _expected_terminal_operativity_domain(revision)


def _assert_public_oracle_reaches_implementation_pin_verifier(
    monkeypatch,
    expected_domain,
):
    original_verifier = a13._verify_implementation_pins

    def pin_verifier_must_raise(*args, **kwargs):
        raise RuntimeError("PIN_VERIFIER_REACHED")

    monkeypatch.setattr(
        a13,
        "_verify_implementation_pins",
        pin_verifier_must_raise,
    )
    with pytest.raises(RuntimeError, match="PIN_VERIFIER_REACHED"):
        a13.validate_ratification_operativity()

    verifier_calls = []

    def counting_verifier(pins):
        verifier_calls.append(copy.deepcopy(pins))
        return original_verifier(pins)

    monkeypatch.setattr(
        a13,
        "_verify_implementation_pins",
        counting_verifier,
    )
    closures = a13.validate_ratification_operativity()
    assert tuple(closures) == expected_domain
    assert len(verifier_calls) >= 1
    return closures


def _assert_executed_transition_evidence(
    evidence,
    *,
    expected_revision=18,
    expected_domain=(13, 14, 15, 16),
    expected_command=A17_FULL_PINNED_BATTERY_COMMAND,
    expected_collected=A17_FULL_PINNED_BATTERY_COLLECTED,
):
    assert set(evidence) == {
        "simulated_state_authority",
        "simulated_state_identity_sha256",
        "simulated_state_manifest",
        "terminal_revision",
        "public_oracle",
        "full_pinned_battery",
    }
    assert evidence["simulated_state_authority"] == "NONAUTHORITY"
    manifest = evidence["simulated_state_manifest"]
    assert set(manifest) == {
        "schema_version",
        "simulated_state_authority",
        "candidate_or_scratch_HEAD",
        "terminal_revision",
        "canonical_registry_binding",
        "ordered_closure_identities",
        "full_pinned_battery_test_identity",
    }
    assert manifest["schema_version"] == "executed_transition_state.v1"
    assert manifest["simulated_state_authority"] == "NONAUTHORITY"
    assert a13._is_lower_hex(manifest["candidate_or_scratch_HEAD"], 40)
    state_identity = evidence["simulated_state_identity_sha256"]
    assert (
        state_identity
        == hashlib.sha256(a13.canonical_json_bytes(manifest)).hexdigest()
    )
    revision = evidence["terminal_revision"]
    assert revision == expected_revision
    assert manifest["terminal_revision"] == revision
    expected = _expected_terminal_operativity_domain(revision)
    assert expected == expected_domain
    registry_binding = a13._validate_registry_ratification_context(
        manifest["canonical_registry_binding"]
    )
    assert registry_binding["revision"] == revision
    closure_identities = manifest["ordered_closure_identities"]
    assert all(
        set(row) == {"path", "raw_byte_size", "raw_sha256", "git_blob"}
        and a13._is_lower_hex(row["git_blob"], 40)
        for row in closure_identities
    )
    assert [row["path"] for row in closure_identities] == [
        row["path"] for row in registry_binding["ratification_closures"]
    ]
    assert [
        {
            "path": row["path"],
            "raw_byte_size": row["raw_byte_size"],
            "raw_sha256": row["raw_sha256"],
        }
        for row in closure_identities
    ] == registry_binding["ratification_closures"]
    pins = _historical_amendment19_implementation_pins()
    test_pin = next(
        row
        for row in pins["files"]
        if row["path"] == "tests/test_validate_amendment13_execution_law.py"
    )
    assert manifest["full_pinned_battery_test_identity"] == {
        "path": test_pin["path"],
        "mode": pins["mode"],
        "git_blob": test_pin["blob_oid"],
        "raw_byte_size": test_pin["byte_size"],
        "raw_sha256": test_pin["sha256"],
    }
    oracle = evidence["public_oracle"]
    assert set(oracle) == {
        "entrypoint",
        "executed",
        "exit_code",
        "operative_amendments",
        "simulated_state_identity_sha256",
    }
    assert oracle["entrypoint"] == "validate_ratification_operativity"
    assert oracle["executed"] is True
    assert type(oracle["exit_code"]) is int
    assert oracle["exit_code"] == 0
    assert tuple(oracle["operative_amendments"]) == expected
    assert oracle["simulated_state_identity_sha256"] == state_identity
    battery = evidence["full_pinned_battery"]
    assert set(battery) == {
        "executed",
        "exit_code",
        "test_path",
        "test_mode_blob_bytes_sha256",
        "exact_command",
        "collected",
        "passed",
        "failed",
        "skipped",
        "deselected",
        "xfailed",
        "xpassed",
        "simulated_state_identity_sha256",
    }
    assert battery["executed"] is True
    for integer_field in (
        "exit_code",
        "collected",
        "passed",
        "failed",
        "skipped",
        "deselected",
        "xfailed",
        "xpassed",
    ):
        assert type(battery[integer_field]) is int
    assert battery["exit_code"] == 0
    assert battery["test_path"] == (
        "tests/test_validate_amendment13_execution_law.py"
    )
    assert (
        battery["test_mode_blob_bytes_sha256"]
        == manifest["full_pinned_battery_test_identity"]
    )
    assert battery["exact_command"] == expected_command
    assert battery["collected"] == expected_collected
    assert battery["passed"] == expected_collected
    for outcome in (
        "failed",
        "skipped",
        "deselected",
        "xfailed",
        "xpassed",
    ):
        assert battery[outcome] == 0
    assert battery["simulated_state_identity_sha256"] == state_identity


def _synthetic_transition_evidence(revision, collected):
    pins = _historical_amendment19_implementation_pins()
    test_pin = next(
        row
        for row in pins["files"]
        if row["path"] == "tests/test_validate_amendment13_execution_law.py"
    )
    context = _synthetic_registry_context(revision)
    closure_identities = [
        {
            **row,
            "git_blob": f"{position:040x}",
        }
        for position, row in enumerate(
            context["ratification_closures"], start=13
        )
    ]
    manifest = {
        "schema_version": "executed_transition_state.v1",
        "simulated_state_authority": "NONAUTHORITY",
        "candidate_or_scratch_HEAD": "c" * 40,
        "terminal_revision": revision,
        "canonical_registry_binding": context,
        "ordered_closure_identities": closure_identities,
        "full_pinned_battery_test_identity": {
            "path": test_pin["path"],
            "mode": pins["mode"],
            "git_blob": test_pin["blob_oid"],
            "raw_byte_size": test_pin["byte_size"],
            "raw_sha256": test_pin["sha256"],
        },
    }
    state_identity = hashlib.sha256(
        a13.canonical_json_bytes(manifest)
    ).hexdigest()
    return {
        "simulated_state_authority": "NONAUTHORITY",
        "simulated_state_identity_sha256": state_identity,
        "simulated_state_manifest": manifest,
        "terminal_revision": revision,
        "public_oracle": {
            "entrypoint": "validate_ratification_operativity",
            "executed": True,
            "exit_code": 0,
            "operative_amendments": list(range(13, revision - 1)),
            "simulated_state_identity_sha256": state_identity,
        },
        "full_pinned_battery": {
            "executed": True,
            "exit_code": 0,
            "test_path": "tests/test_validate_amendment13_execution_law.py",
            "test_mode_blob_bytes_sha256": manifest[
                "full_pinned_battery_test_identity"
            ],
            "exact_command": A17_FULL_PINNED_BATTERY_COMMAND,
            "collected": collected,
            "passed": collected,
            "failed": 0,
            "skipped": 0,
            "deselected": 0,
            "xfailed": 0,
            "xpassed": 0,
            "simulated_state_identity_sha256": state_identity,
        },
    }


def _repin_synthetic_transition_state(evidence):
    state_identity = hashlib.sha256(
        a13.canonical_json_bytes(evidence["simulated_state_manifest"])
    ).hexdigest()
    evidence["simulated_state_identity_sha256"] = state_identity
    evidence["public_oracle"][
        "simulated_state_identity_sha256"
    ] = state_identity
    evidence["full_pinned_battery"][
        "simulated_state_identity_sha256"
    ] = state_identity


def _run_amendment17_test_mutations():
    rejected = []
    for revision in (16, 18, 19):
        forged = tuple(range(13, revision - 2))
        with pytest.raises(AssertionError):
            _assert_revision_general_expectation(revision, forged)
    rejected.append(A17_TEST_MUTATIONS[0])

    with pytest.raises(AssertionError):
        _assert_revision_general_expectation(17, (13, 14, 15))
    rejected.append(A17_TEST_MUTATIONS[1])

    pins = _historical_amendment19_implementation_pins()
    test_pin = next(
        row
        for row in pins["files"]
        if row["path"] == "tests/test_validate_amendment13_execution_law.py"
    )
    context = _synthetic_registry_context(18)
    closure_identities = [
        {
            **row,
            "git_blob": f"{position:040x}",
        }
        for position, row in enumerate(
            context["ratification_closures"], start=13
        )
    ]
    manifest = {
        "schema_version": "executed_transition_state.v1",
        "simulated_state_authority": "NONAUTHORITY",
        "candidate_or_scratch_HEAD": "c" * 40,
        "terminal_revision": 18,
        "canonical_registry_binding": context,
        "ordered_closure_identities": closure_identities,
        "full_pinned_battery_test_identity": {
            "path": test_pin["path"],
            "mode": pins["mode"],
            "git_blob": test_pin["blob_oid"],
            "raw_byte_size": test_pin["byte_size"],
            "raw_sha256": test_pin["sha256"],
        },
    }
    state_identity = hashlib.sha256(
        a13.canonical_json_bytes(manifest)
    ).hexdigest()
    complete_evidence = {
        "simulated_state_authority": "NONAUTHORITY",
        "simulated_state_identity_sha256": state_identity,
        "simulated_state_manifest": manifest,
        "terminal_revision": 18,
        "public_oracle": {
            "entrypoint": "validate_ratification_operativity",
            "executed": True,
            "exit_code": 0,
            "operative_amendments": [13, 14, 15, 16],
            "simulated_state_identity_sha256": state_identity,
        },
        "full_pinned_battery": {
            "executed": True,
            "exit_code": 0,
            "test_path": "tests/test_validate_amendment13_execution_law.py",
            "test_mode_blob_bytes_sha256": manifest[
                "full_pinned_battery_test_identity"
            ],
            "exact_command": A17_FULL_PINNED_BATTERY_COMMAND,
            "collected": A17_FULL_PINNED_BATTERY_COLLECTED,
            "passed": A17_FULL_PINNED_BATTERY_COLLECTED,
            "failed": 0,
            "skipped": 0,
            "deselected": 0,
            "xfailed": 0,
            "xpassed": 0,
            "simulated_state_identity_sha256": state_identity,
        },
    }
    _assert_executed_transition_evidence(complete_evidence)

    focused_bypass = copy.deepcopy(complete_evidence)
    focused_bypass["full_pinned_battery"].update(
        {"collected": 1, "passed": 1, "deselected": 75}
    )
    with pytest.raises(AssertionError):
        _assert_executed_transition_evidence(focused_bypass)
    wrong_state_bypass = copy.deepcopy(complete_evidence)
    wrong_state_bypass["full_pinned_battery"][
        "simulated_state_identity_sha256"
    ] = ("d" * 64)
    with pytest.raises(AssertionError):
        _assert_executed_transition_evidence(wrong_state_bypass)
    extra_receipt_key = copy.deepcopy(complete_evidence)
    extra_receipt_key["unregistered_receipt_member"] = None
    with pytest.raises(AssertionError):
        _assert_executed_transition_evidence(extra_receipt_key)
    for object_name, field_name in (
        ("public_oracle", "exit_code"),
        ("full_pinned_battery", "exit_code"),
        ("full_pinned_battery", "failed"),
    ):
        boolean_numeric = copy.deepcopy(complete_evidence)
        boolean_numeric[object_name][field_name] = False
        with pytest.raises(AssertionError):
            _assert_executed_transition_evidence(boolean_numeric)
    rejected.append(A17_TEST_MUTATIONS[2])

    rejected_tuple = tuple(rejected)
    assert A17_TEST_MUTATIONS == a13.A17_EXPECTED_MUTATIONS
    assert rejected_tuple == A17_TEST_MUTATIONS
    assert len(set(rejected_tuple)) == len(rejected_tuple)
    return rejected_tuple


def test__amendment18_transition_receipt_schema_accepts_revision20_fixture():
    evidence = _synthetic_transition_evidence(
        20,
        A18_FULL_PINNED_BATTERY_COLLECTED,
    )
    _assert_executed_transition_evidence(
        evidence,
        expected_revision=20,
        expected_domain=(13, 14, 15, 16, 17, 18),
        expected_collected=A18_FULL_PINNED_BATTERY_COLLECTED,
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_count",
        "wrong_order",
        "revision19_with_six",
        "boolean_integer",
        "different_state",
        "focused_battery",
    ),
)
def test__amendment18_transition_receipt_variants_fail_closed(mutation):
    evidence = _synthetic_transition_evidence(
        20,
        A18_FULL_PINNED_BATTERY_COLLECTED,
    )
    expected_revision = 20
    expected_domain = (13, 14, 15, 16, 17, 18)
    if mutation == "wrong_count":
        evidence["simulated_state_manifest"]["canonical_registry_binding"][
            "ratification_closures"
        ].pop()
        evidence["simulated_state_manifest"][
            "ordered_closure_identities"
        ].pop()
        _repin_synthetic_transition_state(evidence)
    elif mutation == "wrong_order":
        context = evidence["simulated_state_manifest"][
            "canonical_registry_binding"
        ]
        context["ratification_closures"][4:6] = reversed(
            context["ratification_closures"][4:6]
        )
        identities = evidence["simulated_state_manifest"][
            "ordered_closure_identities"
        ]
        identities[4:6] = reversed(identities[4:6])
        _repin_synthetic_transition_state(evidence)
    elif mutation == "revision19_with_six":
        evidence["terminal_revision"] = 19
        evidence["simulated_state_manifest"]["terminal_revision"] = 19
        evidence["simulated_state_manifest"]["canonical_registry_binding"][
            "revision"
        ] = 19
        expected_revision = 19
        expected_domain = (13, 14, 15, 16, 17)
        _repin_synthetic_transition_state(evidence)
    elif mutation == "boolean_integer":
        evidence["full_pinned_battery"]["collected"] = True
    elif mutation == "different_state":
        evidence["full_pinned_battery"]["simulated_state_identity_sha256"] = (
            "d" * 64
        )
    else:
        evidence["full_pinned_battery"].update(
            {
                "collected": 1,
                "passed": 1,
                "deselected": A18_FULL_PINNED_BATTERY_COLLECTED - 1,
            }
        )
    with pytest.raises((AssertionError, a13.LawError)):
        _assert_executed_transition_evidence(
            evidence,
            expected_revision=expected_revision,
            expected_domain=expected_domain,
            expected_collected=A18_FULL_PINNED_BATTERY_COLLECTED,
        )


@pytest.fixture
def amendment19_external_transition_receipt():
    """Stand in for the external, uncommitted same-state receipt bytes."""

    return _synthetic_transition_evidence(
        21,
        A19_FULL_PINNED_BATTERY_COLLECTED,
    )


def test__amendment19_external_transition_receipt_is_integer_strict(
    amendment19_external_transition_receipt,
):
    _assert_executed_transition_evidence(
        amendment19_external_transition_receipt,
        expected_revision=21,
        expected_domain=tuple(range(13, 20)),
        expected_collected=A19_FULL_PINNED_BATTERY_COLLECTED,
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_count",
        "wrong_order",
        "revision20_with_seven",
        "boolean_integer",
        "different_state",
        "focused_battery",
        "extra_receipt_key",
    ),
)
def test__amendment19_external_transition_receipt_variants_fail_closed(
    amendment19_external_transition_receipt,
    mutation,
):
    evidence = copy.deepcopy(amendment19_external_transition_receipt)
    if mutation == "wrong_count":
        evidence["simulated_state_manifest"]["canonical_registry_binding"][
            "ratification_closures"
        ].pop()
        evidence["simulated_state_manifest"][
            "ordered_closure_identities"
        ].pop()
        _repin_synthetic_transition_state(evidence)
    elif mutation == "wrong_order":
        context = evidence["simulated_state_manifest"][
            "canonical_registry_binding"
        ]
        context["ratification_closures"][5:7] = reversed(
            context["ratification_closures"][5:7]
        )
        identities = evidence["simulated_state_manifest"][
            "ordered_closure_identities"
        ]
        identities[5:7] = reversed(identities[5:7])
        _repin_synthetic_transition_state(evidence)
    elif mutation == "revision20_with_seven":
        evidence["terminal_revision"] = 20
        evidence["simulated_state_manifest"]["terminal_revision"] = 20
        evidence["simulated_state_manifest"]["canonical_registry_binding"][
            "revision"
        ] = 20
        _repin_synthetic_transition_state(evidence)
    elif mutation == "boolean_integer":
        evidence["full_pinned_battery"]["collected"] = True
    elif mutation == "different_state":
        evidence["public_oracle"]["simulated_state_identity_sha256"] = "d" * 64
    elif mutation == "focused_battery":
        evidence["full_pinned_battery"].update(
            {
                "collected": 1,
                "passed": 1,
                "deselected": A19_FULL_PINNED_BATTERY_COLLECTED - 1,
            }
        )
    else:
        evidence["unregistered_receipt_member"] = None
    with pytest.raises((AssertionError, a13.LawError)):
        _assert_executed_transition_evidence(
            evidence,
            expected_revision=21,
            expected_domain=tuple(range(13, 20)),
            expected_collected=A19_FULL_PINNED_BATTERY_COLLECTED,
        )


def test__draft__emits_neither_authority_nor_certification(execution_law):
    assert execution_law["status"] == a13.DRAFT_STATUS
    assert execution_law["authority_emitted"] is False
    assert execution_law["certification_emitted"] is False
    assert (
        execution_law["governing_amendment13_ratification_identity"]
        == a13.GOVERNING_A13_CANDIDATE_IDENTITY
    )


def test__ratification__binds_exact_historical_document_blob(execution_law):
    identity = execution_law["amendment12_ratification_identity"]
    assert identity == a13.AMENDMENT12_RATIFICATION_IDENTITY
    assert identity["ratification_parents"] == [a13.RATIFICATION_PARENT]
    assert identity["document_blob_oid"] == a13.DESIGN_BLOB
    assert identity["document_byte_size"] == a13.DESIGN_BYTE_SIZE
    assert identity["document_sha256"] == a13.DESIGN_SHA256
    assert len(identity["dual_ratify_attestations"]) == 2


def test__ratification__seventeen_path_observation_is_not_identity_condition():
    result = subprocess.run(
        [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            a13.RATIFICATION_COMMIT,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert len(result.stdout.splitlines()) == 17
    assert a13.DESIGN_PATH in result.stdout.splitlines()


def test__ratification__path_count_is_outside_the_identity(execution_law):
    assert (
        "changed_path_count"
        not in execution_law["amendment12_ratification_identity"]
    )
    assert execution_law["ratification_history_observation"] == {
        "changed_path_count": 17,
        "commit_path_shape_is_identity_condition": False,
    }


def test__proof_successors__exact_cover_and_status_families(execution_law):
    rows = execution_law[
        "semantically_incompatible_local_proof_successor_rows"
    ]
    assert [row["predecessor_row_id"] for row in rows] == list(
        a13.INCOMPATIBLE_PROOF_IDS
    )
    assert {row["successor_payload"]["terminal_status"] for row in rows} == {
        a13.PROOF_TERMINAL_STATUS
    }
    assert tuple(a13.PROOF_PREDECESSOR_FINDING_BY_ID) == (
        a13.INCOMPATIBLE_PROOF_IDS
    )
    assert Counter(a13.PROOF_PREDECESSOR_FINDING_BY_ID.values()) == Counter(
        {
            a13.PROOF_FINDING_MIXED_ENDPOINT: 11,
            a13.PROOF_FINDING_HETEROGENEOUS_PAGE: 6,
            a13.PROOF_FINDING_JOB_CONTEXT: 1,
            a13.PROOF_FINDING_INCOMPLETE_CLAUSE: 4,
            a13.PROOF_FINDING_SHARED_INCOME_LIST: 5,
            a13.PROOF_FINDING_MISPAIRED_CONTEXT: 1,
        }
    )


def test__successors__identity_preimage_binds_exact_status_mapping(
    execution_law,
):
    rows = [
        *execution_law["semantically_incompatible_local_proof_successor_rows"],
        *execution_law["incomplete_fragment_terminal_successor_rows"],
        *execution_law["composed_fragment_successor_rows"],
    ]
    assert all(
        row["successor_identity_preimage"][-2]
        == row["predecessor_status_mapping"]
        for row in rows
    )


def test__incomplete_fragments__repair_by_disclosure_not_invention(
    execution_law,
):
    rows = execution_law["incomplete_fragment_terminal_successor_rows"]
    assert len(rows) == 8
    for row in rows:
        payload = row["successor_payload"]
        citation = payload["disclosed_incomplete_fragment_citation"]
        assert payload["terminal_status"] == a13.INCOMPLETE_FRAGMENT_STATUS
        assert payload["continuation_citation"] is None
        assert payload["alias_admitted"] is False
        assert citation["utf8_byte_end"] > citation["utf8_byte_start"]
        assert (
            hashlib.sha256(citation["matched_text"].encode()).hexdigest()
            == citation["matched_utf8_sha256"]
        )


def test__composed_fragments__use_exact_selector_and_transform(execution_law):
    rows = execution_law["composed_fragment_successor_rows"]
    assert [row["document_source_position"] for row in rows] == [66, 70]
    for row in rows:
        expected = a13.COMPOSITION_SPECS[row["document_source_position"]]
        payload = row["successor_payload"]
        citation = payload["composition_citation"]
        assert payload["terminal_status"] == a13.COMPOSED_FRAGMENT_STATUS
        assert citation["selector_rule"] == a13.FRAGMENT_SELECTOR_RULE
        assert (
            citation["selected_leading_occurrence_id"]
            == expected["selected_leading_occurrence_id"]
        )
        assert citation["combined_text"] == expected["combined_text"]
        assert (
            citation["combined_utf8_sha256"]
            == expected["combined_utf8_sha256"]
        )
        assert payload["occurrence_equivalence_admitted"] is False


def test__document036__changes_only_component_slot_to_aggregate(execution_law):
    rows = execution_law["doc036_aggregate_domain_successor_rows"]
    assert len(rows) == 8
    for row in rows:
        payload = row["successor_payload"]
        predecessor = payload["predecessor_classification_row"]
        successor = payload["successor_classification_row"]
        assert set(successor) == set(predecessor)
        assert predecessor["node_domain"] == "component_slot"
        assert successor["node_domain"] == "aggregate"
        assert {
            key
            for key in predecessor
            if predecessor.get(key) != successor.get(key)
        } == {"node_domain"}


def test__document036__successor_only_extra_key_fails_closed(execution_law):
    candidate = copy.deepcopy(execution_law)
    row = candidate["doc036_aggregate_domain_successor_rows"][0]
    row["successor_payload"]["successor_classification_row"]["forged"] = True
    a13._repin_successor(row)
    with pytest.raises(
        a13.LawError,
        match="document-036 transformation is not the sole determinate",
    ):
        a13.validate_execution_law(candidate, verify_git=False)


def test__closure__a13_direct_pins_and_canonical_instance_validate():
    closure, raw, binding, verdicts, design_raw = _a13_closure_material()
    validated = a13._validate_ratification_closure(
        raw,
        binding,
        verdicts,
        13,
        verify_git=False,
        ratification_design_raw=design_raw,
    )
    assert validated == closure
    assert closure["verdict_artifacts"] == list(a13.A13_VERDICT_ARTIFACTS)
    assert closure["ratification_commit"] == (
        a13.A13_MERGED_RATIFICATION_COMMIT
    )
    assert closure["operator_merge_commit"] == closure["ratification_commit"]


def test__closure__generic_a14_schema_validates_like_a13():
    closure, raw, binding, verdicts, design_raw = (
        a13._synthetic_closure_material()
    )
    validated = a13._validate_ratification_closure(
        raw,
        binding,
        verdicts,
        14,
        verify_git=False,
        ratification_design_raw=design_raw,
        registry_design_binding=a13._synthetic_registry_design_binding(
            closure
        ),
    )
    assert validated == closure
    assert tuple(validated) == a13.CLOSURE_TOP_LEVEL_KEYS
    assert all(
        tuple(row) == a13.CLOSURE_VERDICT_KEYS
        for row in validated["verdict_artifacts"]
    )


def test__closure__a14_must_match_revision16_design_binding():
    closure, raw, binding, verdicts, design_raw = (
        a13._synthetic_closure_material()
    )
    registry_binding = a13._synthetic_registry_design_binding(closure)
    registry_binding["blob_sha256"] = "0" * 64
    with pytest.raises(
        a13.LawError,
        match="does not match the revision-16 registry design binding",
    ):
        a13._validate_ratification_closure(
            raw,
            binding,
            verdicts,
            14,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=registry_binding,
        )


def test__closure__revision15_blob_cannot_pose_as_revision16():
    closure, _, _, _, _ = a13._synthetic_closure_material()
    revision15 = a13._git(
        "show",
        f"{a13.A13_MERGED_RATIFICATION_COMMIT}:{a13.DESIGN_PATH}",
    )
    assert isinstance(revision15, bytes)
    closure["attested_candidate_design_blob_oid"] = a13._git_blob_oid(
        revision15
    )
    closure["attested_candidate_design_byte_size"] = len(revision15)
    closure["attested_candidate_design_raw_sha256"] = hashlib.sha256(
        revision15
    ).hexdigest()
    verdicts = {}
    for position, row in enumerate(closure["verdict_artifacts"], 1):
        verdict_raw = a13._synthetic_verdict_bytes(
            closure,
            f"revision15-{position}",
        )
        verdicts[row["path"]] = verdict_raw
        row["byte_size"] = len(verdict_raw)
        row["raw_sha256"] = hashlib.sha256(verdict_raw).hexdigest()
    raw = a13.canonical_json_bytes(closure)
    with pytest.raises(
        a13.LawError,
        match="attests terminal Amendment 13 instead of Amendment 14",
    ):
        a13._validate_ratification_closure(
            raw,
            a13._closure_binding(a13.A14_CLOSURE_PATH, raw),
            verdicts,
            14,
            verify_git=False,
            ratification_design_raw=revision15,
            registry_design_binding=a13._synthetic_registry_design_binding(
                closure
            ),
        )


def test__closure__historical_a15_design_is_nonterminal_at_revision18():
    design_raw = a13._git(
        "show",
        f"{a13.A15_MERGED_RATIFICATION_COMMIT}:{a13.DESIGN_PATH}",
    )
    assert isinstance(design_raw, bytes)
    context = a13._validate_registry_ratification_context(
        _synthetic_registry_context(18)
    )
    a13._validate_non_a13_ratification_design(design_raw, 15)
    assert a13._terminal_design_amendment(design_raw) == 15
    assert context["ratification_closures"][2]["path"] == a13.A15_CLOSURE_PATH
    assert 15 + 2 < context["revision"]


def test__closure__historical_a15_closure_is_an_exact_enacted_object():
    closure, raw, binding, verdicts, design_raw = (
        a13._synthetic_closure_material(15)
    )
    with pytest.raises(
        a13.LawError,
        match="Amendment-15 closure differs from directly enacted values",
    ):
        a13._validate_ratification_closure(
            raw,
            binding,
            verdicts,
            15,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=_synthetic_registry_context(18),
        )


def test__closure__non_a13_closure_cannot_forge_another_amendment():
    revision17 = a13._git(
        "show",
        f"{a13.A15_MERGED_RATIFICATION_COMMIT}:{a13.DESIGN_PATH}",
    )
    assert isinstance(revision17, bytes)
    closure, raw, binding, verdicts, design_raw = (
        a13._synthetic_closure_material(16, design_raw=revision17)
    )
    context = _synthetic_registry_context(18)
    context["ratification_commit"] = closure["ratification_commit"]
    context["blob_sha256"] = closure["attested_candidate_design_raw_sha256"]
    with pytest.raises(
        a13.LawError,
        match="attests terminal Amendment 15 instead of Amendment 16",
    ):
        a13._validate_ratification_closure(
            raw,
            binding,
            verdicts,
            16,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=context,
        )


def test__closure__revision18_preserves_exact_historical_a14_binding():
    path = ROOT / a13.A14_CLOSURE_PATH
    closure_raw = path.read_bytes()
    closure = a13._strict_canonical_json(closure_raw, a13.A14_CLOSURE_PATH)
    closure["operator_merge_commit"] = (
        "ace88cda0e588f1b847552a31787cc69324d8646"
    )
    closure["ratification_commit"] = "ace88cda0e588f1b847552a31787cc69324d8646"
    closure["ratification_commit_sole_parent"] = (
        a13.A14_MERGED_RATIFICATION_COMMIT
    )
    forged_raw = a13.canonical_json_bytes(closure)
    forged_binding = a13._closure_binding(a13.A14_CLOSURE_PATH, forged_raw)
    context = _synthetic_registry_context(18)
    context["ratification_closures"][1] = forged_binding
    verdicts = {
        row["path"]: (ROOT / row["path"]).read_bytes()
        for row in closure["verdict_artifacts"]
    }
    with pytest.raises(
        a13.LawError,
        match="Amendment-14 historical closure binding drift",
    ):
        a13._validate_ratification_closure(
            forged_raw,
            forged_binding,
            verdicts,
            14,
            verify_git=True,
            registry_design_binding=context,
        )


def test__closure__unpaired_unicode_surrogate_fails_closed():
    closure, _, _, _, _ = a13._synthetic_closure_material()
    closure["verdict_artifacts"][0]["path"] = "\ud800"
    raw = a13.canonical_json_bytes(closure)
    with pytest.raises(
        a13.LawError,
        match="unpaired Unicode surrogate",
    ):
        a13._strict_canonical_json(raw, "synthetic closure")


def test__closure__public_missing_binding_fails_closed(monkeypatch):
    def fail_context():
        raise a13.LawError("registry ratification closure binding is missing")

    monkeypatch.setattr(
        a13, "_public_registry_ratification_context", fail_context
    )
    with pytest.raises(
        a13.LawError,
        match="registry ratification closure binding is missing",
    ):
        a13.validate_amendment_ratification_closure(13)


def test__closure__operativity_requires_both_public_closures(monkeypatch):
    context = _synthetic_registry_context(16)
    observed = []

    def validate(amendment_number, selected_context):
        assert selected_context == context
        observed.append(amendment_number)
        return {"amendment_number": amendment_number}

    assert a13._validate_ratification_operativity_context(
        context, validate
    ) == {
        13: {"amendment_number": 13},
        14: {"amendment_number": 14},
    }
    assert observed == [13, 14]


@pytest.mark.parametrize(
    ("revision", "amendment_numbers", "closure_count"),
    (
        (16, (13, 14), 2),
        (18, (13, 14, 15, 16), 4),
        (19, (13, 14, 15, 16, 17), 5),
        (20, (13, 14, 15, 16, 17, 18), 6),
        (21, (13, 14, 15, 16, 17, 18, 19), 7),
    ),
)
def test__closure__general_revision_domain_law(
    revision,
    amendment_numbers,
    closure_count,
):
    assert a13._ratification_amendment_numbers(revision) == amendment_numbers
    context = a13._validate_registry_ratification_context(
        _synthetic_registry_context(revision)
    )
    assert len(context["ratification_closures"]) == closure_count
    assert closure_count == revision - 14


def test__closure__revision17_standalone_activation_is_forbidden():
    with pytest.raises(
        a13.LawError,
        match="revision 17 cannot be a terminal ratification registry",
    ):
        a13._validate_registry_ratification_context(
            _synthetic_registry_context(17)
        )
    assert _run_amendment17_test_mutations() == A17_TEST_MUTATIONS


@pytest.mark.parametrize("mutation", ("wrong_count", "wrong_order"))
def test__closure__generalized_registry_domain_fails_closed(mutation):
    context = _synthetic_registry_context(18)
    if mutation == "wrong_count":
        context["ratification_closures"].pop()
        message = "closure count drift"
    else:
        context["ratification_closures"][1:3] = reversed(
            context["ratification_closures"][1:3]
        )
        message = "closure binding order drift"
    with pytest.raises(a13.LawError, match=message):
        a13._validate_registry_ratification_context(context)


def test__closure__revision18_operativity_is_atomic_and_ordered():
    context = a13._validate_registry_ratification_context(
        _synthetic_registry_context(18)
    )
    observed = []

    def validate(amendment_number, selected_context):
        assert selected_context == context
        observed.append(amendment_number)
        return {"amendment_number": amendment_number}

    closures = a13._validate_ratification_operativity_context(
        context, validate
    )
    assert tuple(closures) == (13, 14, 15, 16)
    assert observed == [13, 14, 15, 16]


def test__closure__revision20_operativity_is_atomic_and_ordered():
    context = a13._validate_registry_ratification_context(
        _synthetic_registry_context(20)
    )
    observed = []

    def validate(amendment_number, selected_context):
        assert selected_context == context
        observed.append(amendment_number)
        return {"amendment_number": amendment_number}

    closures = a13._validate_ratification_operativity_context(
        context, validate
    )
    assert tuple(closures) == (13, 14, 15, 16, 17, 18)
    assert observed == [13, 14, 15, 16, 17, 18]


def test__closure__revision21_operativity_is_atomic_and_ordered():
    context = a13._validate_registry_ratification_context(
        _synthetic_registry_context(21)
    )
    observed = []

    def validate(amendment_number, selected_context):
        assert selected_context == context
        observed.append(amendment_number)
        return {"amendment_number": amendment_number}

    closures = a13._validate_ratification_operativity_context(
        context, validate
    )
    assert tuple(closures) == tuple(range(13, 20))
    assert observed == list(range(13, 20))


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_a19",
        "extra_a20",
        "wrong_order",
        "duplicate_a18",
        "wrong_a19_path",
        "revision20_with_seven",
    ),
)
def test__closure__revision21_domain_variants_fail_closed(mutation):
    context = _synthetic_registry_context(21)
    if mutation == "missing_a19":
        context["ratification_closures"].pop()
    elif mutation == "extra_a20":
        context["ratification_closures"].append(
            {
                "path": (
                    "docs/analysis/amendment_20_ratification/"
                    "closure_v1.json"
                ),
                "raw_byte_size": 20,
                "raw_sha256": f"{20:064x}",
            }
        )
    elif mutation == "wrong_order":
        context["ratification_closures"][5:7] = reversed(
            context["ratification_closures"][5:7]
        )
    elif mutation == "duplicate_a18":
        context["ratification_closures"][6] = copy.deepcopy(
            context["ratification_closures"][5]
        )
    elif mutation == "wrong_a19_path":
        context["ratification_closures"][6][
            "path"
        ] = "docs/analysis/amendment_20_ratification/closure_v1.json"
    else:
        context["revision"] = 20
    with pytest.raises(a13.LawError):
        a13._validate_registry_ratification_context(context)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_a18",
        "extra_a19",
        "wrong_order",
        "duplicate_a17",
        "wrong_a18_path",
        "revision19_with_six",
    ),
)
def test__closure__revision20_domain_variants_fail_closed(mutation):
    context = _synthetic_registry_context(20)
    if mutation == "missing_a18":
        context["ratification_closures"].pop()
    elif mutation == "extra_a19":
        context["ratification_closures"].append(
            {
                "path": (
                    "docs/analysis/amendment_19_ratification/"
                    "closure_v1.json"
                ),
                "raw_byte_size": 19,
                "raw_sha256": f"{19:064x}",
            }
        )
    elif mutation == "wrong_order":
        context["ratification_closures"][4:6] = reversed(
            context["ratification_closures"][4:6]
        )
    elif mutation == "duplicate_a17":
        context["ratification_closures"][5] = copy.deepcopy(
            context["ratification_closures"][4]
        )
    elif mutation == "wrong_a18_path":
        context["ratification_closures"][5][
            "path"
        ] = "docs/analysis/amendment_19_ratification/closure_v1.json"
    else:
        context["revision"] = 19
    with pytest.raises(a13.LawError):
        a13._validate_registry_ratification_context(context)


@pytest.mark.parametrize("revision", (18, 19, 20, 21))
def test__tier2_r05__current_snapshot_selects_exact_historical_a15(
    revision,
    monkeypatch,
):
    context = _synthetic_registry_context(revision)
    context["ratification_closures"][2] = {
        "path": a13.A18_HISTORICAL_R05_BINDING["closure_path"],
        "raw_byte_size": a13.A18_HISTORICAL_R05_BINDING["closure_byte_size"],
        "raw_sha256": a13.A18_HISTORICAL_R05_BINDING["closure_raw_sha256"],
    }
    context = a13._validate_registry_ratification_context(context)
    observed = []

    def validate(amendment_number, selected_context):
        assert selected_context == context
        observed.append(amendment_number)
        if amendment_number == 15:
            return copy.deepcopy(a13.A15_EXPECTED_CLOSURE)
        return {"amendment_number": amendment_number}

    validated_closures = a13._validate_ratification_operativity_context(
        context, validate
    )
    assert observed == list(range(13, revision - 1))
    assert (
        _select_historical_r05_fixture(
            context,
            validated_closures,
        )
        == a13.A18_HISTORICAL_R05_BINDING
    )


@pytest.mark.parametrize("mutation", ("absent", "moved", "mismatched"))
def test__tier2_r05__a15_selector_prerequisites_fail_closed(mutation):
    context = _synthetic_registry_context(20)
    context["ratification_closures"][2] = {
        "path": a13.A18_HISTORICAL_R05_BINDING["closure_path"],
        "raw_byte_size": a13.A18_HISTORICAL_R05_BINDING["closure_byte_size"],
        "raw_sha256": a13.A18_HISTORICAL_R05_BINDING["closure_raw_sha256"],
    }
    if mutation == "absent":
        context["ratification_closures"].pop(2)
    elif mutation == "moved":
        context["ratification_closures"][2:4] = reversed(
            context["ratification_closures"][2:4]
        )
    else:
        context["ratification_closures"][2]["raw_sha256"] = "0" * 64
    with pytest.raises(a13.LawError):
        a13._validate_registry_ratification_context(context)


def test__closure__revision18_combined_set_passes_generalized_oracle(
    monkeypatch,
):
    a13_material = _a13_closure_material()
    a14_path = ROOT / a13.A14_CLOSURE_PATH
    a14_raw = a14_path.read_bytes()
    a14_closure = a13._strict_canonical_json(a14_raw, a13.A14_CLOSURE_PATH)
    a14_design = a13._git(
        "show",
        f"{a13.A14_MERGED_RATIFICATION_COMMIT}:{a13.DESIGN_PATH}",
    )
    assert isinstance(a14_design, bytes)
    a14_material = (
        a14_closure,
        a14_raw,
        a13._closure_binding(a13.A14_CLOSURE_PATH, a14_raw),
        {
            row["path"]: (ROOT / row["path"]).read_bytes()
            for row in a14_closure["verdict_artifacts"]
        },
        a14_design,
    )
    a15_design = a13._git(
        "show",
        f"{a13.A15_MERGED_RATIFICATION_COMMIT}:{a13.DESIGN_PATH}",
    )
    assert isinstance(a15_design, bytes)
    a16_material = a13._synthetic_closure_material(
        16,
        design_raw=(ROOT / a13.DESIGN_PATH).read_bytes()[
            : a13.REVISION18_BYTE_SIZE
        ],
    )
    materials = {13: a13_material, 14: a14_material, 16: a16_material}
    context = {
        "path": a13.DESIGN_PATH,
        "ratification_commit": a16_material[0]["ratification_commit"],
        "revision": 18,
        "blob_sha256": a16_material[0]["attested_candidate_design_raw_sha256"],
        "ratification_closures": [
            a13_material[2],
            a14_material[2],
            a13._closure_binding(
                a13.A15_CLOSURE_PATH,
                a13.canonical_json_bytes(a13.A15_EXPECTED_CLOSURE),
            ),
            a16_material[2],
        ],
    }

    def validate(amendment_number, selected_context):
        if amendment_number == 15:
            a13._validate_closure_shape(a13.A15_EXPECTED_CLOSURE, 15)
            a13._validate_non_a13_ratification_design(a15_design, 15)
            return a13.A15_EXPECTED_CLOSURE
        closure, raw, binding, verdicts, design_raw = materials[
            amendment_number
        ]
        return a13._validate_ratification_closure(
            raw,
            binding,
            verdicts,
            amendment_number,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=(
                selected_context if amendment_number != 13 else None
            ),
        )

    closures = a13._validate_ratification_operativity_context(
        context, validate
    )
    assert tuple(closures) == (13, 14, 15, 16)


def test__closure__real_public_path_adapts_at_revision16(monkeypatch):
    import covered_earnings_correction_registry as registry

    if registry.DESIGN_REVISION < 16:
        with pytest.raises(
            a13.LawError,
            match="registry ratification closure binding is missing",
        ):
            a13.validate_ratification_operativity()
        return

    if registry.DESIGN_REVISION == 17:
        with pytest.raises(
            a13.LawError,
            match="revision 17 cannot be a terminal ratification registry",
        ):
            a13.validate_ratification_operativity()
        return

    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    if a13._terminal_design_amendment(raw) != registry.DESIGN_REVISION - 2:
        if (
            registry.DESIGN_REVISION == 21
            and a13._terminal_design_amendment(raw) == 20
        ):
            closures = a13.validate_ratification_operativity()
            assert tuple(closures) == tuple(
                range(a13.FIRST_CLOSURE_AMENDMENT, 20)
            )
            return
        verifier_calls = []
        context = _synthetic_registry_context(registry.DESIGN_REVISION)
        monkeypatch.setattr(
            a13,
            "_public_registry_ratification_context",
            lambda: context,
        )
        monkeypatch.setattr(
            a13,
            "_verify_implementation_pins",
            lambda pins: verifier_calls.append(pins),
        )
        with pytest.raises(
            a13.LawError,
            match="ordinary registry/design terminal amendment mismatch",
        ):
            a13.validate_ratification_operativity()
        assert verifier_calls == []
        return

    expected_domain = _expected_terminal_operativity_domain(
        registry.DESIGN_REVISION
    )
    if registry.DESIGN_REVISION in (19, 20):
        assert (
            expected_domain
            == {
                19: (13, 14, 15, 16, 17),
                20: (13, 14, 15, 16, 17, 18),
            }[registry.DESIGN_REVISION]
        )
    closures = _assert_public_oracle_reaches_implementation_pin_verifier(
        monkeypatch,
        expected_domain,
    )
    _assert_revision_general_public_result(registry.DESIGN_REVISION, closures)
    template = a13.build_ratification_bound_execution_template()
    assert template["status"] == a13.RATIFICATION_BOUND_TEMPLATE_STATUS
    assert template["governing_amendment13_ratification_identity"] == (
        closures[13]
    )


def test__closure__public_operativity_rejects_replacement_ref_design_attack(
    monkeypatch,
):
    original_expect_law_error = a13._expect_law_error

    def expect_public_operativity_rejection(
        action,
        expected_message,
        label,
    ):
        assert action is a13._public_registry_ratification_context
        original_expect_law_error(action, expected_message, label)
        original_expect_law_error(
            a13.validate_ratification_operativity,
            expected_message,
            f"{label} through public operativity",
        )

    monkeypatch.setattr(
        a13,
        "_expect_law_error",
        expect_public_operativity_rejection,
    )
    a13._run_public_registry_replace_ref_enforcement_mutation()


def test__closure__ratification_commit_is_exact_single_parent():
    closure, raw, binding, verdicts, _ = _a13_closure_material()
    validated = a13._validate_ratification_closure(
        raw,
        binding,
        verdicts,
        13,
        verify_git=True,
    )
    assert validated == closure


def test__closure__tree_object_cannot_pose_as_commit():
    tree_object = str(a13._git("rev-parse", "HEAD^{tree}", text=True)).strip()
    with pytest.raises(
        a13.LawError,
        match="is not an exact commit object",
    ):
        a13._require_exact_commit_object(tree_object, "synthetic tree")


def test__ratification_bound_template__replaces_placeholder_everywhere():
    amendment13_material, amendment14_material = _operativity_materials()
    closure = amendment13_material[0]
    template = a13._build_ratification_bound_execution_template_for_test(
        amendment13_material,
        amendment14_material,
    )
    assert template["status"] == a13.RATIFICATION_BOUND_TEMPLATE_STATUS
    assert template["authority_emitted"] is False
    assert template["certification_emitted"] is False
    assert template["governing_amendment13_ratification_identity"] == closure
    assert all(
        overlay["governing_amendment13_ratification_identity"] == closure
        and overlay["overlay_identity_preimage"][-2] == closure
        for overlay in template["repair_overlay_rows"]
    )
    assert all(
        seal["governing_amendment13_ratification_identity"] == closure
        and seal["successor_era_seal_identity_preimage"][-1] == closure
        for seal in template["successor_era_seal_rows"]
    )


def test__ratification_bound_template__public_validator_cannot_bypass_git():
    amendment13_material, amendment14_material = _operativity_materials()
    closure = amendment13_material[0]
    template = a13._build_ratification_bound_execution_template_for_test(
        amendment13_material,
        amendment14_material,
    )
    assert template["governing_amendment13_ratification_identity"] == closure
    with pytest.raises(
        a13.LawError,
        match="ratification-bound validation may not disable Git verification",
    ):
        a13.validate_execution_law(template, verify_git=False)


def test__ratification_bound_template__rejects_coherent_source_forgery():
    amendment13_material, amendment14_material = _operativity_materials()
    template = a13._build_ratification_bound_execution_template_for_test(
        amendment13_material,
        amendment14_material,
    )
    row = template["semantically_incompatible_local_proof_successor_rows"][0]
    row["successor_payload"][
        "terminal_reason_code"
    ] = "forged_but_coherently_repinned_reason"
    a13._repin_successor(row)
    with pytest.raises(
        a13.LawError,
        match="forged incompatible-proof terminal status or admission",
    ):
        a13._validate_execution_law(
            template,
            verify_git=False,
            verified_closures={
                13: amendment13_material[0],
                14: amendment14_material[0],
            },
        )


def test__ratification_bound_template__rejects_invalid_a14_closure():
    amendment13_material, amendment14_material = _operativity_materials()
    closure, _, _, verdicts, design_raw = amendment14_material
    forged_closure = copy.deepcopy(closure)
    forged_closure["extra"] = True
    forged_raw = a13.canonical_json_bytes(forged_closure)
    forged_binding = a13._closure_binding(a13.A14_CLOSURE_PATH, forged_raw)
    with pytest.raises(
        a13.LawError,
        match="ratification closure keyset drift",
    ):
        a13._build_ratification_bound_execution_template_for_test(
            amendment13_material,
            (
                forged_closure,
                forged_raw,
                forged_binding,
                verdicts,
                design_raw,
            ),
        )


def test__supersession__retains_every_predecessor(execution_law):
    rows = execution_law["predecessor_supersession_rows"]
    assert len(rows) == 46
    assert all(row["predecessor_retained"] is True for row in rows)
    assert all(row["predecessor_erasure_permitted"] is False for row in rows)
    assert all(
        row["supersession_relation"] == a13.SUPERSESSION_RELATION
        for row in rows
    )


def test__era_cascade__requires_all_six_successor_seals(execution_law):
    rows = execution_law["successor_era_seal_rows"]
    assert len(rows) == 6
    assert [sum(row["repair_counts"].values()) for row in rows] == [
        16,
        10,
        18,
        38,
        10,
        0,
    ]
    assert all(
        row["all_named_domains_present_even_when_empty"] is True
        for row in rows
    )


def test__scope__fourteen_law_gaps_and_a12_continuations_are_untouched(
    execution_law,
):
    assert execution_law["untouched_law_gap_predecessor_ids"] == list(
        a13.LAW_GAP_IDS
    )
    continuation = execution_law["amendment12_continuation_domain"]
    assert continuation["disjoint_and_unchanged"] is True
    assert continuation["continuation_citation_count"] == 5
    assert continuation["continuation_restoration_count"] == 3
    assert len(continuation["continuation_projection_rows"]) == 5
    assert continuation["continuation_projection_byte_size"] == 1_457
    assert continuation["continuation_projection_sha256"] == (
        a13.A12_CONTINUATION_PROJECTION_SHA256
    )


def test__nested_authority_and_declared_schema_forgery_fail_closed(
    execution_law,
):
    candidates = []
    overlay = copy.deepcopy(execution_law)
    overlay["repair_overlay_rows"][0]["authority_kind"] = "AUTHORITY"
    candidates.append(overlay)
    seal = copy.deepcopy(execution_law)
    seal["successor_era_seal_rows"][0]["authority_kind"] = "AUTHORITY"
    candidates.append(seal)
    schema = copy.deepcopy(execution_law)
    schema["overlay_schema_version"] = "forged.v1"
    candidates.append(schema)
    for candidate in candidates:
        with pytest.raises(a13.LawError):
            a13.validate_execution_law(candidate, verify_git=False)


def test__document__semantic_projection_covers_amendments14_through19():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    projection = a13._parse_document_semantic_projection(raw)
    assert projection["amendment14"]["section_semantic_sha256"] == (
        a13.A14_SECTION_SEMANTIC_SHA256
    )
    assert projection["amendment14"]["a13_expected_closure"] == (
        a13.A13_EXPECTED_CLOSURE
    )
    assert projection["amendment14"]["enforcement_mutations"] == list(
        a13.A13_ENFORCEMENT_EXPECTED_MUTATIONS
    )
    assert projection["amendment15"]["section_semantic_sha256"] == (
        a13.A15_SECTION_SEMANTIC_SHA256
    )
    amendment16 = projection["amendment16"]
    assert amendment16["section_semantic_sha256"] == (
        a13.A16_SECTION_SEMANTIC_SHA256
    )
    assert amendment16["ratification_law_values"] == (
        a13.A16_RATIFICATION_LAW_VALUES
    )
    assert amendment16["a14_historical_closure_binding"] == (
        a13.A14_HISTORICAL_CLOSURE_BINDING
    )
    assert amendment16["a15_expected_closure"] == a13.A15_EXPECTED_CLOSURE
    assert amendment16["historical_r05_binding"] == (
        a13.A16_HISTORICAL_R05_BINDING
    )
    assert tuple(amendment16["oracle_mutations"]) == (
        a13.A16_EXPECTED_MUTATIONS
    )
    assert amendment16["oracle_mutation_domain_sha256"] == (
        a13.A16_MUTATION_DOMAIN_SHA256
    )
    amendment17 = projection["amendment17"]
    assert amendment17["section_semantic_sha256"] == (
        a13.A17_SECTION_SEMANTIC_SHA256
    )
    assert amendment17["revision_domain_rules"] == list(
        a13.A17_REVISION_DOMAIN_RULES
    )
    assert amendment17["executed_transition_obligation"] == (
        a13.A17_EXECUTED_TRANSITION_OBLIGATION
    )
    assert amendment17["receipt_schema"] == a13.A17_RECEIPT_SCHEMA
    assert amendment17["transition_registry_binding"] == (
        a13.A17_TRANSITION_REGISTRY_BINDING
    )
    assert amendment17["transition_closure_identities"] == list(
        a13.A17_TRANSITION_CLOSURE_IDENTITIES
    )
    assert amendment17["transition_verdict_artifacts"] == list(
        a13.A17_TRANSITION_VERDICT_ARTIFACTS
    )
    assert amendment17["required_public_output"] == list(
        a13.A17_REQUIRED_PUBLIC_OUTPUT
    )
    assert amendment17["full_pinned_battery"] == (a13.A17_FULL_PINNED_BATTERY)
    assert tuple(amendment17["test_ceremony_mutations"]) == (
        a13.A17_EXPECTED_MUTATIONS
    )
    assert amendment17["test_ceremony_mutation_domain_sha256"] == (
        a13.A17_MUTATION_DOMAIN_SHA256
    )
    assert amendment17["supersession_map"] == [
        list(row) for row in a13.A17_SUPERSESSION_MAP
    ]
    amendment18 = projection["amendment18"]
    assert set(amendment18) == {
        "section_semantic_sha256",
        "implementation_pins",
        "build_input_domain_contract",
        "historical_r05_binding",
        "r06_result_contract",
        "activation_transition",
        "contract_mutations",
        "contract_mutation_domain_sha256",
        "mutation_census",
        "supersession_map",
        "new_identifiers",
    }
    assert amendment18["section_semantic_sha256"] == (
        a13.A18_SECTION_SEMANTIC_SHA256
    )
    assert amendment18["implementation_pins"] == (
        a13._parse_amendment18_implementation_pins(raw)
    )
    assert amendment18["build_input_domain_contract"] == (
        a13.A18_BUILD_INPUT_DOMAIN_CONTRACT
    )
    assert amendment18["historical_r05_binding"] == (
        a13.A18_HISTORICAL_R05_BINDING
    )
    assert set(amendment18["historical_r05_binding"]) == {
        "amendment_number",
        "closure_byte_size",
        "closure_path",
        "closure_raw_sha256",
        "design_blob_oid",
        "design_byte_size",
        "design_path",
        "design_raw_sha256",
        "design_revision",
        "ratification_commit",
        "ratification_commit_sole_parent",
    }
    assert amendment18["r06_result_contract"] == (a13.A18_R06_RESULT_CONTRACT)
    assert amendment18["activation_transition"] == (
        a13.A18_ACTIVATION_TRANSITION
    )
    activation = amendment18["activation_transition"]
    assert activation["r05_public_entrypoint"] == (
        "validate_ratification_operativity"
    )
    assert activation["r05_minimum_terminal_revision"] == 18
    assert activation["r05_expected_domain_expression"] == (
        "tuple(range(13, R - 1))"
    )
    assert activation["r05_selected_zero_based_position"] == 2
    assert activation["r05_selected_amendment"] == 15
    assert tuple(amendment18["contract_mutations"]) == (
        a13.A18_EXPECTED_MUTATIONS
    )
    assert amendment18["contract_mutation_domain_sha256"] == (
        a13.A18_MUTATION_DOMAIN_SHA256
    )
    assert amendment18["mutation_census"] == a13.A18_MUTATION_CENSUS
    assert amendment18["supersession_map"] == [
        list(row) for row in a13.A18_SUPERSESSION_MAP
    ]
    assert amendment18["new_identifiers"] == a13.A18_NEW_IDENTIFIERS
    assert amendment18["new_identifiers"] == {
        "schema_and_path": [
            "amendment_12_tier2_build_input_domain.v1",
            "amendment_12_tier2_r06_expected_abort_result.v1",
            (
                "docs/analysis/amendment_12_rq_catalog_tier2/"
                "certification/amendment11_expected_abort_result_v1.json"
            ),
            "a12-tier2-r06-expected-abort-result:",
        ],
        "status_role_lifecycle": [
            "pass_a12_t2_r06_expected_abort_reproduced",
            "evidence_expected_amendment11_abort_reproduced_nonauthority",
            "A19_SUCCESSOR_PROGRAM_STOP",
        ],
        "input_class": ["source_document", "repair_seal_evidence"],
        "python": [
            "_validate_amendment18_ratification_design",
            "_validate_inherited_amendment18_ratification_design",
            "run_amendment18_contract_mutation_tests",
        ],
    }
    amendment19 = projection["amendment19"]
    assert set(amendment19) == {
        "section_semantic_sha256",
        "implementation_pins",
        "normative_manifest",
    }
    assert amendment19["section_semantic_sha256"] == (
        a13.A19_SECTION_SEMANTIC_SHA256
    )
    assert amendment19["implementation_pins"] == (
        a13._parse_amendment19_implementation_pins(raw)
    )
    assert amendment19["normative_manifest"] == a13.A19_NORMATIVE_MANIFEST
    assert amendment19["normative_manifest"] == (
        a13._canonical_amendment19_projection()["normative_manifest"]
    )
    manifest = amendment19["normative_manifest"]
    assert manifest["prefix_identity"] == {
        "blob_oid": "016c0fff757b54da730ae0044216416cde2d2c33",
        "byte_size": 3_964_278,
        "raw_sha256": (
            "631d3b2b8ecab1c29ec0595550a6d2b798f49ff96e74c722801d24c48ab111ec"
        ),
    }
    assert manifest["authenticated_build_input_envelope"] == {
        "canonical_byte_size": 168_504,
        "raw_sha256": (
            "f34ced6e80e1bf72e68635b4f729c5b983c094fd25d16105a6c161ccd52fff63"
        ),
        "row_count": 279,
    }
    assert manifest["purpose_mapping_contract"] == (
        a13.A19_PURPOSE_MAPPING_CONTRACT
    )
    assert manifest["semantic_binding_contract"] == (
        a13.A19_SEMANTIC_BINDING_CONTRACT
    )
    assert manifest["source_hierarchy_failure_contract"] == (
        a13.A19_SOURCE_HIERARCHY_FAILURE_CONTRACT
    )
    assert manifest["hierarchy_construction_contract"] == (
        a13.A19_HIERARCHY_CONSTRUCTION_CONTRACT
    )
    assert manifest["successor_routing_contract"] == (
        a13.A19_SUCCESSOR_ROUTING_CONTRACT
    )
    assert manifest["activation_transition"] == a13.A19_ACTIVATION_TRANSITION
    assert tuple(manifest["mutation_inventory"]) == a13.A19_EXPECTED_MUTATIONS
    assert manifest["mutation_domain_byte_size"] == (
        a13.A19_MUTATION_DOMAIN_BYTE_SIZE
    )
    assert manifest["mutation_domain_sha256"] == (
        a13.A19_MUTATION_DOMAIN_SHA256
    )
    assert manifest["mutation_census"] == a13.A19_MUTATION_CENSUS
    assert manifest["supersession_map"] == [
        list(row) for row in a13.A19_SUPERSESSION_MAP
    ]
    assert manifest["new_identifiers"] == a13.A19_NEW_IDENTIFIERS
    assert manifest["production_registry_boundary"] == {
        "closure_count": 6,
        "ordered_closure_domain": [13, 14, 15, 16, 17, 18],
        "revision": 20,
        "unchanged_by_draft": True,
    }
    amendment20 = projection["amendment20"]
    assert set(amendment20) == {
        "section_semantic_sha256",
        "implementation_pins",
        "normative_manifest",
    }
    assert amendment20["section_semantic_sha256"] == (
        a13.A20_SECTION_SEMANTIC_SHA256
    )
    assert amendment20["implementation_pins"] == (
        a13._parse_amendment20_implementation_pins(raw)
    )
    assert amendment20["normative_manifest"] == a13.A20_NORMATIVE_MANIFEST
    a13._validate_a20_manifest_contract(amendment20["normative_manifest"])


def test__amendment19__purpose_mapping_census_is_total_and_fail_closed():
    contract = a13.A19_PURPOSE_MAPPING_CONTRACT
    a13._validate_a19_purpose_mapping_contract(contract)
    assert contract["prompt_row_keys"] == [
        "source_prompt_occurrence_id",
        "source_classification_row_id",
        "serialized_source_literals",
        "explicit_official_purposes",
        "unresolved_legacy_literals",
        "purpose_mapping_disposition",
    ]
    assert contract["construction_order"] == [
        "authenticate_fixed_prompt_denominator",
        "construct_complete_purpose_mapping_rows_keyset_domain_and_counts",
        "compute_U_underdetermined_mapping_prompt_count",
        "select_failure_or_normal_variant",
        "normal_variant_only_construct_O_H_purpose_independent",
        "normal_variant_only_evaluate_O_P_witnesses",
    ]
    assert contract["source_classification_resolution"] == (
        "zero_or_one_same_annotation_row_by_shape_specific_occurrence_id"
    )
    assert contract["source_classification_join_keys"] == {
        "plural": "source_prompt_occurrence_id",
        "singular": "source_occurrence_id",
    }
    assert contract["source_classification_status_rules"] == {
        "plural": {"key": "annotation_status", "value": "complete"},
        "singular": {
            "key": "classification_status",
            "value": "complete_document_local_provisional",
        },
    }
    assert contract["source_classification_join_keys"]["plural"] in (
        contract["plural_source_row_keys"]
    )
    assert contract["source_classification_join_keys"]["singular"] in (
        contract["singular_source_row_keys"]
    )
    dispositions = contract["disposition_counts"]
    assert dispositions == {
        "complete_official_mapping": 818,
        "partial_official_mapping_with_legacy_residue_underdetermined": 14,
        "legacy_only_mapping_underdetermined": 56,
        "missing_mapping_underdetermined": 21_083,
    }
    assert sum(dispositions.values()) == contract["field_purpose_prompt_count"]
    assert contract["field_purpose_prompt_count"] == 21_971
    assert contract["official_mapped_prompt_count"] == 832
    assert contract["missing_official_mapping_prompt_count"] == 21_139
    assert contract["underdetermined_mapping_prompt_count"] == 21_153
    assert contract["underdetermined_mapping_prompt_count"] == sum(
        count
        for disposition, count in dispositions.items()
        if disposition != "complete_official_mapping"
    )
    assert (
        contract["classification_row_count"]
        + contract["unclassified_prompt_count"]
        == contract["field_purpose_prompt_count"]
    )
    assert (
        sum(
            row["prompt_count"]
            for row in contract["classification_document_rows"]
        )
        == contract["classification_row_count"]
    )
    assert (
        sum(
            row["official_mapped_prompt_count"]
            for row in contract["classification_document_rows"]
        )
        == contract["official_mapped_prompt_count"]
    )
    assert contract["first_source_prompt_occurrence_id"] == (
        "psid-questionnaire-occurrence:"
        "17d4dd6699adc429dc5548b30763fc11425469927c1f02c41c15ae6a93c3828a"
    )
    assert contract["last_source_prompt_occurrence_id"] == (
        "psid-questionnaire-occurrence:"
        "d1c8bdfb99364eff8092c663c399e6e4391e6fcd9c6bb742bdda13f1df489980"
    )
    assert contract["purpose_mapping_keyset_canonical_byte_size"] == 2_131_189
    assert contract["purpose_mapping_keyset_sha256"] == (
        "2d1300eaae5c8259f1cda59907d2cf0b8174faf5a37a3549e6d6f3eec9618921"
    )
    assert contract["purpose_mapping_domain_canonical_byte_size"] == 7_244_433
    assert contract["purpose_mapping_domain_sha256"] == (
        "53158188e774c75fcbe6b7af57bfa747060c80193556eac7a0e289e02b63ed1e"
    )
    audit = contract["exact_text_transfer_audit"]
    assert (
        audit["unmatched_text_prompt_count"]
        + audit["shared_text_prompt_count"]
        == audit["missing_official_mapping_prompt_count"]
    )
    assert audit["mapped_text_class_conflict_count"] == 8
    assert contract["no_current_prompt_source_proved_no_purpose"] is True
    assert contract["underdetermined_selects_early_failure_variant"] is True
    assert contract["selected_failure_variant_evaluates_o_h"] is False
    assert contract["selected_failure_variant_evaluates_o_p"] is False
    assert contract["normal_variant_o_h_remains_purpose_independent"] is True
    assert (
        contract["normal_variant_o_h_precedes_o_p_witness_evaluation"] is True
    )
    assert contract["normal_variant_known_positive_relation"] == (
        "existing_same_wave_branch_compatible_anchor_witness_using_only_"
        "explicit_official_purposes"
    )
    assert contract["text_transfer_forbidden"] is True
    assert contract["similarity_transfer_forbidden"] is True
    assert contract["legacy_literal_promotion_forbidden"] is True
    assert contract["manual_addition_forbidden"] is True


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_prompt_count",
        "boolean_prompt_count",
        "wrong_underdetermined_count",
        "boolean_underdetermined_count",
        "singular_uses_plural_join",
        "plural_uses_singular_status",
        "singular_uses_plural_status",
        "wrong_first_occurrence",
        "wrong_keyset_bytes",
        "wrong_domain_digest",
        "selector_disabled",
        "wrong_construction_order",
        "failure_evaluates_o_h",
        "purpose_dependent_o_h",
        "o_p_before_o_h",
        "o_p_evaluated_on_failure",
    ),
)
def test__amendment19__purpose_mapping_variants_fail_closed(mutation):
    candidate = copy.deepcopy(a13.A19_PURPOSE_MAPPING_CONTRACT)
    if mutation == "wrong_prompt_count":
        candidate["field_purpose_prompt_count"] = 21_970
    elif mutation == "boolean_prompt_count":
        candidate["field_purpose_prompt_count"] = True
    elif mutation == "wrong_underdetermined_count":
        candidate["underdetermined_mapping_prompt_count"] = 21_152
    elif mutation == "boolean_underdetermined_count":
        candidate["underdetermined_mapping_prompt_count"] = True
    elif mutation == "singular_uses_plural_join":
        candidate["source_classification_join_keys"][
            "singular"
        ] = "source_prompt_occurrence_id"
    elif mutation == "plural_uses_singular_status":
        candidate["source_classification_status_rules"]["plural"][
            "value"
        ] = "complete_document_local_provisional"
    elif mutation == "singular_uses_plural_status":
        candidate["source_classification_status_rules"]["singular"][
            "value"
        ] = "complete"
    elif mutation == "wrong_first_occurrence":
        candidate["first_source_prompt_occurrence_id"] = (
            "psid-questionnaire-occurrence:" + "0" * 64
        )
    elif mutation == "wrong_keyset_bytes":
        candidate["purpose_mapping_keyset_canonical_byte_size"] = 2_131_188
    elif mutation == "wrong_domain_digest":
        candidate["purpose_mapping_domain_sha256"] = "0" * 64
    elif mutation == "selector_disabled":
        candidate["underdetermined_selects_early_failure_variant"] = False
    elif mutation == "wrong_construction_order":
        (
            candidate["construction_order"][1],
            candidate["construction_order"][4],
        ) = (
            candidate["construction_order"][4],
            candidate["construction_order"][1],
        )
    elif mutation == "failure_evaluates_o_h":
        candidate["selected_failure_variant_evaluates_o_h"] = True
    elif mutation == "purpose_dependent_o_h":
        candidate["normal_variant_o_h_remains_purpose_independent"] = False
    elif mutation == "o_p_before_o_h":
        candidate["normal_variant_o_h_precedes_o_p_witness_evaluation"] = False
    else:
        candidate["selected_failure_variant_evaluates_o_p"] = True
    with pytest.raises(
        a13.LawError,
        match="Amendment-19 purpose-mapping totality contract drift",
    ):
        a13._validate_a19_purpose_mapping_contract(candidate)


def test__amendment19__failure_selector_preempts_semantic_binding_evaluation():
    contract = a13.A19_SEMANTIC_BINDING_CONTRACT
    a13._validate_a19_semantic_binding_contract(contract)
    assert contract["authenticated_annotation_document_count"] == 81
    assert (
        contract["authenticated_complete_semantic_binding_relation_count"] == 0
    )
    assert contract[
        "audit_is_discovery_evidence_not_selected_branch_member_input"
    ]
    assert contract["purpose_mapping_does_not_create_five_coordinate_binding"]
    assert contract["candidate_binding_forbidden"]
    assert contract["text_inference_forbidden"]
    assert contract["failure_selector_precedes_semantic_binding_evaluation"]
    assert (
        contract["selected_failure_variant_serializes_near_match_rows"]
        is False
    )
    assert contract[
        "normal_variant_requires_inherited_complete_semantic_bindings"
    ]
    assert "absent_binding_input_semantic_bindings" not in contract
    assert "absent_binding_input_annotation_disposition" not in contract
    assert "current_all_source_atoms_unresolved" not in contract


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("authenticated_complete_semantic_binding_relation_count", 1),
        (
            "audit_is_discovery_evidence_not_selected_branch_member_input",
            False,
        ),
        ("failure_selector_precedes_semantic_binding_evaluation", False),
        ("selected_failure_variant_serializes_near_match_rows", True),
        (
            "normal_variant_requires_inherited_complete_semantic_bindings",
            False,
        ),
    ),
)
def test__amendment19__semantic_binding_variants_fail_closed(field, value):
    candidate = copy.deepcopy(a13.A19_SEMANTIC_BINDING_CONTRACT)
    candidate[field] = value
    with pytest.raises(
        a13.LawError,
        match="Amendment-19 semantic-binding totality contract drift",
    ):
        a13._validate_a19_semantic_binding_contract(candidate)


def test__amendment19__early_failure_member_and_identity_are_byte_exact():
    contract = a13.A19_SOURCE_HIERARCHY_FAILURE_CONTRACT
    a13._validate_a19_source_hierarchy_failure_contract(contract)
    member = contract["failure_member"]
    assert (
        list(member)
        == contract["failure_member_keys"]
        == [
            "authority_kind",
            "questionnaire_document_count",
            "questionnaire_document_keyset_sha256",
            "questionnaire_document_domain_sha256",
            "purpose_mapping_row_count",
            "purpose_mapping_keyset_sha256",
            "purpose_mapping_domain_sha256",
            "purpose_mapping_disposition_counts",
            "canonical_order",
            "status",
        ]
    )
    assert member == a13.A19_SOURCE_HIERARCHY_FAILURE_MEMBER
    assert member["questionnaire_document_count"] == 81
    assert member["purpose_mapping_row_count"] == 21_971
    assert member["canonical_order"] == "questionnaire_occurrence_source_order"
    assert member["status"] == "fail_source_purpose_mapping_underdetermined"
    member_bytes = a13.canonical_json_bytes(member)
    assert len(member_bytes) == contract["failure_member_canonical_byte_size"]
    assert len(member_bytes) == 877
    assert hashlib.sha256(member_bytes).hexdigest() == (
        contract["failure_member_raw_sha256"]
    )
    assert hashlib.sha256(member_bytes).hexdigest() == (
        "1651c50ff1f171ac420e55982cb060db70946f9283999c3d9edb2fa140d467c5"
    )

    identity = contract["source_hierarchy_member_identity"]
    assert list(identity) == contract["source_hierarchy_member_identity_keys"]
    assert list(identity) == [
        "authority_kind",
        "canonical_byte_size",
        "canonicalization",
        "member_name",
        "raw_sha256",
        "status",
    ]
    assert identity == a13.A19_SOURCE_HIERARCHY_MEMBER_IDENTITY
    assert identity["canonical_byte_size"] == 877
    assert identity["raw_sha256"] == hashlib.sha256(member_bytes).hexdigest()
    assert identity["authority_kind"] == (
        "pre_q5_source_hierarchy_failure_member_nonauthority"
    )
    identity_bytes = a13.canonical_json_bytes(identity)
    assert len(identity_bytes) == (
        contract["source_hierarchy_member_identity_canonical_byte_size"]
    )
    assert len(identity_bytes) == 351
    assert hashlib.sha256(identity_bytes).hexdigest() == (
        contract["source_hierarchy_member_identity_raw_sha256"]
    )
    assert hashlib.sha256(identity_bytes).hexdigest() == (
        "077c6a19e44d8abdf96422a8d2d203fdf263ecbbfb70cb9bb3dc9522a3dcd2bd"
    )


def test__amendment19__early_failure_forbids_all_pass_continuation():
    contract = a13.A19_SOURCE_HIERARCHY_FAILURE_CONTRACT
    assert contract["selection_stage"] == (
        "after_purpose_mapping_before_all_pass_member_construction"
    )
    assert contract["selection_predicate"] == (
        "underdetermined_mapping_prompt_count_gt_zero"
    )
    assert contract["fixed_selector_value"] is True
    assert contract["global_purpose_mapping_rows_constructed_before_selection"]
    assert (
        contract[
            "selected_failure_variant_serializes_per_era_purpose_mapping_rows"
        ]
        is False
    )
    inherited_header = a13.A19_A12_SUCCESSOR_AUTHORITY_HEADER_KEYS
    failure_keys = contract["failure_member_keys"]
    assert len(inherited_header) == len(set(inherited_header)) == 78
    assert len(failure_keys) == len(set(failure_keys)) == 10
    assert set(inherited_header) & set(failure_keys) == {
        "authority_kind",
        "questionnaire_document_count",
        "questionnaire_document_keyset_sha256",
        "questionnaire_document_domain_sha256",
        "canonical_order",
        "status",
    }
    effective_normal_header = list(inherited_header)
    hierarchy_position = effective_normal_header.index(
        "hierarchy_domain_sha256"
    )
    effective_normal_header.insert(
        hierarchy_position,
        "hierarchy_preproof_domain_sha256",
    )
    hierarchy_position += 1
    for offset, key in enumerate(
        (
            "purpose_mapping_row_count",
            "purpose_mapping_keyset_sha256",
            "purpose_mapping_domain_sha256",
            "purpose_mapping_disposition_counts",
        ),
        start=1,
    ):
        effective_normal_header.insert(hierarchy_position + offset, key)
    assert (
        len(effective_normal_header) == len(set(effective_normal_header)) == 83
    )
    assert set(failure_keys) <= set(effective_normal_header)
    assert set(contract["forbidden_authority_header_keys"]) == (
        set(effective_normal_header) - set(failure_keys)
    )
    assert len(contract["forbidden_authority_header_keys"]) == 73
    assert contract["forbidden_authority_header_keys"] == [
        "questionnaire_page_text_derivation_byte_size",
        "questionnaire_page_text_derivation_sha256",
        "role_node_rows",
        "role_node_count",
        "role_node_domain_sha256",
        "role_label_class_rows",
        "role_label_class_count",
        "role_label_class_domain_sha256",
        "role_assignment_rows",
        "role_assignment_count",
        "role_assignment_keyset_sha256",
        "role_assignment_domain_sha256",
        "job_slot_rows",
        "job_slot_count",
        "job_slot_domain_sha256",
        "questionnaire_component_slot_rows",
        "questionnaire_component_slot_count",
        "questionnaire_component_slot_domain_sha256",
        "component_parent_resolution_rows",
        "component_parent_resolution_count",
        "component_parent_resolution_keyset_sha256",
        "component_parent_resolution_domain_sha256",
        "component_parent_resolution_disposition_counts",
        "node_alias_rows",
        "node_alias_count",
        "node_alias_domain_sha256",
        "outside_r_q_repeat_terminal_rows",
        "outside_r_q_repeat_terminal_count",
        "outside_r_q_repeat_terminal_keyset_sha256",
        "outside_r_q_repeat_terminal_domain_sha256",
        "noncatalog_aggregate_relation_disposition_rows",
        "noncatalog_aggregate_relation_disposition_count",
        "noncatalog_aggregate_relation_disposition_keyset_sha256",
        "noncatalog_aggregate_relation_disposition_domain_sha256",
        "in_domain_redirection_disposition_rows",
        "in_domain_redirection_disposition_count",
        "in_domain_redirection_disposition_keyset_sha256",
        "in_domain_redirection_disposition_domain_sha256",
        "global_relationship_rows",
        "global_relationship_count",
        "global_relationship_keyset_sha256",
        "global_relationship_domain_sha256",
        "catalog_only_job_disposition_rows",
        "catalog_only_job_disposition_count",
        "catalog_only_job_disposition_keyset_sha256",
        "catalog_only_job_disposition_domain_sha256",
        "questionnaire_page_count",
        "questionnaire_page_domain_sha256",
        "questionnaire_occurrence_count",
        "questionnaire_occurrence_domain_sha256",
        "flow_branch_count",
        "flow_branch_domain_sha256",
        "hierarchy_row_count",
        "hierarchy_keyset_sha256",
        "hierarchy_preproof_domain_sha256",
        "hierarchy_domain_sha256",
        "positive_occurrence_row_count",
        "positive_occurrence_keyset_sha256",
        "positive_occurrence_domain_sha256",
        "occurrence_raw_field_reference_count",
        "occurrence_raw_field_reference_keyset_sha256",
        "occurrence_raw_field_reference_domain_sha256",
        "positive_field_join_row_count",
        "positive_field_join_keyset_sha256",
        "positive_field_join_domain_sha256",
        "expanded_disposition_row_count",
        "expanded_disposition_keyset_sha256",
        "expanded_disposition_domain_sha256",
        "near_match_source_annotation_count",
        "near_match_source_annotation_keyset_sha256",
        "near_match_source_annotation_domain_sha256",
        "absence_proof_count",
        "absence_proof_domain_sha256",
    ]
    assert contract["forbidden_evaluation_or_serialization"] == [
        "O_H",
        "O_P",
        "H",
        "reverse_cover",
        "purpose_expansion",
        "semantic_bindings",
        "questionnaire_page_rows",
        "questionnaire_occurrence_rows",
        "flow_branch_rows",
        "role_node_rows",
        "role_label_class_rows",
        "role_assignment_rows",
        "job_slot_rows",
        "questionnaire_component_slot_rows",
        "component_parent_resolution_rows",
        "node_alias_rows",
        "outside_r_q_repeat_terminal_rows",
        "noncatalog_aggregate_relation_disposition_rows",
        "in_domain_redirection_disposition_rows",
        "global_relationship_rows",
        "catalog_only_job_disposition_rows",
        "whole_document_locators",
        "field_stream_locators",
        "hierarchy_preproof_rows",
        "hierarchy_preproof_domain_sha256",
        "hierarchy_rows",
        "hierarchy_domain_sha256",
        "positive_occurrence_rows",
        "occurrence_raw_field_reference_rows",
        "positive_field_join_rows",
        "expanded_disposition_rows",
        "near_match_source_annotation_rows",
        "absence_proofs",
        "all_pass_only_counts_keysets_and_domain_digests",
        "per_era_purpose_mapping_rows",
        "all_per_era_arrays_counts_keysets_and_domain_digests",
        "era_rows",
        "era_row_count",
        "era_id_order",
        "era_domain_sha256",
        "normal_authority_header",
        "A12-T2-R04_overall_gate",
        "Q5",
        "G17-C01",
        "official_inventory",
        "official_slot_registry",
        "authority_emission",
        "production_output",
    ]
    assert not set(contract["failure_member"]) & set(
        contract["forbidden_authority_header_keys"]
    )
    forbidden = set(contract["forbidden_evaluation_or_serialization"])
    assert {
        "O_H",
        "O_P",
        "H",
        "reverse_cover",
        "purpose_expansion",
        "semantic_bindings",
        "per_era_purpose_mapping_rows",
        "near_match_source_annotation_rows",
        "hierarchy_preproof_rows",
        "hierarchy_rows",
        "era_rows",
        "A12-T2-R04_overall_gate",
        "Q5",
        "G17-C01",
        "authority_emission",
        "production_output",
    } <= forbidden
    assert contract["r04_dual_reconstruction_required"] is True
    assert contract["r04_independent_reconstruction_subresult_count"] == 2
    assert contract["r04_independent_reconstruction_subresult_status"] == (
        "pass_independent_source_reconstruction"
    )
    assert (
        contract[
            "r04_independent_reconstruction_subresults_require_exact_selected_"
            "member_bytes"
        ]
        is True
    )
    assert contract["a12_t2_r04_overall_gate_preserved"] is True
    assert contract["a12_t2_r04_selected_failure_gate_pass_permitted"] is False
    assert contract["r05_requires_passing_normal_member"] is True
    assert contract["r05_pass_or_certification_emission_permitted"] is False
    assert contract["q5_or_authority_emission_permitted"] is False
    assert "a12_t2_r04_selected_failure_disposition" not in contract
    assert "r04_pass_definition" not in contract
    assert "r04_pass_requires_selected_member_status_pass" not in contract


@pytest.mark.parametrize(
    "mutation",
    (
        "selector_false",
        "selector_boolean_replaced_by_integer",
        "selection_after_pass_construction",
        "global_precursor_not_constructed",
        "per_era_rows_serialized",
        "a12_header_key_not_forbidden",
        "a12_family_evaluated",
        "missing_failure_key",
        "pass_header_continuation",
        "wrong_member_bytes",
        "boolean_member_bytes",
        "wrong_identity_bytes",
        "boolean_identity_bytes",
        "identity_claims_pass_authority",
        "wrong_r04_subresult_count",
        "boolean_r04_subresult_count",
        "wrong_r04_subresult_status",
        "r04_subresults_ignore_selected_bytes",
        "r04_overall_gate_not_preserved",
        "r04_overall_gate_passes",
        "r05_accepts_failure_member",
    ),
)
def test__amendment19__early_failure_variants_fail_closed(mutation):
    candidate = copy.deepcopy(a13.A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    if mutation == "selector_false":
        candidate["fixed_selector_value"] = False
    elif mutation == "selector_boolean_replaced_by_integer":
        candidate["fixed_selector_value"] = 1
    elif mutation == "selection_after_pass_construction":
        candidate["selection_stage"] = "after_all_pass_member_construction"
    elif mutation == "global_precursor_not_constructed":
        candidate[
            "global_purpose_mapping_rows_constructed_before_selection"
        ] = False
    elif mutation == "per_era_rows_serialized":
        candidate[
            "selected_failure_variant_serializes_per_era_purpose_mapping_rows"
        ] = True
    elif mutation == "a12_header_key_not_forbidden":
        candidate["forbidden_authority_header_keys"].remove(
            "role_label_class_rows"
        )
    elif mutation == "a12_family_evaluated":
        candidate["forbidden_evaluation_or_serialization"].remove(
            "component_parent_resolution_rows"
        )
    elif mutation == "missing_failure_key":
        del candidate["failure_member"]["purpose_mapping_domain_sha256"]
    elif mutation == "pass_header_continuation":
        candidate["failure_member"]["hierarchy_domain_sha256"] = "0" * 64
    elif mutation == "wrong_member_bytes":
        candidate["failure_member_canonical_byte_size"] = 878
    elif mutation == "boolean_member_bytes":
        candidate["failure_member_canonical_byte_size"] = True
    elif mutation == "wrong_identity_bytes":
        candidate["source_hierarchy_member_identity_canonical_byte_size"] = 352
    elif mutation == "boolean_identity_bytes":
        candidate["source_hierarchy_member_identity_canonical_byte_size"] = (
            True
        )
    elif mutation == "identity_claims_pass_authority":
        candidate["source_hierarchy_member_identity"][
            "authority_kind"
        ] = "prospective_g17_c01_source_member_pre_q5"
    elif mutation == "wrong_r04_subresult_count":
        candidate["r04_independent_reconstruction_subresult_count"] = 3
    elif mutation == "boolean_r04_subresult_count":
        candidate["r04_independent_reconstruction_subresult_count"] = True
    elif mutation == "wrong_r04_subresult_status":
        candidate["r04_independent_reconstruction_subresult_status"] = "pass"
    elif mutation == "r04_subresults_ignore_selected_bytes":
        candidate[
            "r04_independent_reconstruction_subresults_require_exact_selected_"
            "member_bytes"
        ] = False
    elif mutation == "r04_overall_gate_not_preserved":
        candidate["a12_t2_r04_overall_gate_preserved"] = False
    elif mutation == "r04_overall_gate_passes":
        candidate["a12_t2_r04_selected_failure_gate_pass_permitted"] = True
    else:
        candidate["r05_requires_passing_normal_member"] = False
    with pytest.raises(
        a13.LawError,
        match="Amendment-19 early source-hierarchy failure contract drift",
    ):
        a13._validate_a19_source_hierarchy_failure_contract(candidate)


def test__amendment19__successor_numbering_and_revision21_route_are_exact():
    routing = a13.A19_SUCCESSOR_ROUTING_CONTRACT
    activation = a13.A19_ACTIVATION_TRANSITION
    a13._validate_a19_successor_and_activation_contract(routing, activation)
    assert routing == {
        "historical_amendment18_next_required_state": (
            "A19_SUCCESSOR_PROGRAM_STOP"
        ),
        "active_next_required_state": "A20_SUCCESSOR_PROGRAM_STOP",
        "active_lifecycle_derivation": (
            "deep_copy_A18_R06_RESULT_CONTRACT_lifecycle_replace_only_"
            "next_required_state"
        ),
        "all_other_r06_members_unchanged": True,
        "current_amendment": 19,
        "current_revision": 21,
        "deferred_program_amendment": 20,
        "deferred_program_revision": 22,
        "deferred_campaign_substance": "OUT_OF_SCOPE",
        "historical_identifier_is_not_active_alias": True,
        "r06_artifact_blocked_while_r05_nonpass": True,
    }
    assert activation["terminal_revision"] == 21
    assert activation["terminal_amendment"] == 19
    assert activation["ordered_closure_domain"] == list(range(13, 20))
    assert activation["closure_count"] == 7 == 21 - 14
    assert activation["activation_affecting"] is True
    assert activation["same_state_required"] is True
    assert activation["full_pinned_battery_required"] is True
    assert activation["receipt_inside_candidate_bytes"] is False
    assert activation["activation_requires_later_registry_repin"] is True
    assert activation["production_registry_revision_in_draft"] == 20
    assert activation["production_oracle_changed_by_draft"] is False
    historical = copy.deepcopy(a13.A18_R06_RESULT_CONTRACT)
    active = copy.deepcopy(historical)
    active["lifecycle"]["next_required_state"] = routing[
        "active_next_required_state"
    ]
    assert historical["lifecycle"]["next_required_state"] == (
        routing["historical_amendment18_next_required_state"]
    )
    assert active["lifecycle"]["next_required_state"] == (
        "A20_SUCCESSOR_PROGRAM_STOP"
    )
    assert set(active) == set(historical)
    for key in set(active) - {"lifecycle"}:
        assert active[key] == historical[key]
    assert set(active["lifecycle"]) == set(historical["lifecycle"])
    for key in set(active["lifecycle"]) - {"next_required_state"}:
        assert active["lifecycle"][key] == historical["lifecycle"][key]


@pytest.mark.parametrize(
    ("object_name", "field", "value"),
    (
        (
            "routing",
            "active_next_required_state",
            "A19_SUCCESSOR_PROGRAM_STOP",
        ),
        ("routing", "historical_identifier_is_not_active_alias", False),
        ("routing", "all_other_r06_members_unchanged", False),
        ("routing", "deferred_program_amendment", 19),
        ("activation", "terminal_revision", 20),
        ("activation", "ordered_closure_domain", [13, 14, 15, 16, 17, 19, 18]),
        ("activation", "closure_count", True),
    ),
)
def test__amendment19__successor_and_activation_variants_fail_closed(
    object_name,
    field,
    value,
):
    routing = copy.deepcopy(a13.A19_SUCCESSOR_ROUTING_CONTRACT)
    activation = copy.deepcopy(a13.A19_ACTIVATION_TRANSITION)
    target = routing if object_name == "routing" else activation
    target[field] = value
    with pytest.raises(
        a13.LawError,
        match="Amendment-19 successor-stop or revision-21 routing drift",
    ):
        a13._validate_a19_successor_and_activation_contract(
            routing,
            activation,
        )


def test__amendment19__staged_hierarchy_worked_identity_is_exact():
    contract = a13.A19_HIERARCHY_CONSTRUCTION_CONTRACT
    a13._validate_a19_hierarchy_construction_contract(contract)
    assert (
        contract["applicability"] == "only_if_purpose_failure_selector_false"
    )
    assert (
        contract["selected_failure_variant_executes_hierarchy_construction"]
        is False
    )
    assert contract["per_era_insertion"] == "purpose_mapping_rows"
    assert contract["g17_c01_normal_projection_sides"] == [
        "expected",
        "actual",
    ]
    assert contract["g17_c01_normal_per_era_insertion_order"] == [
        "hierarchy_rows",
        "purpose_mapping_rows",
        "positive_occurrence_rows",
    ]
    assert contract["g17_c01_normal_direct_concatenation_header_members"] == [
        "purpose_mapping_row_count",
        "purpose_mapping_keyset_sha256",
        "purpose_mapping_domain_sha256",
        "purpose_mapping_disposition_counts",
    ]
    assert (
        contract["selected_failure_variant_executes_g17_c01_projection"]
        is False
    )
    row = a13._a19_worked_preproof_row()
    target = a13._a19_worked_proof_target()
    identity = a13._derive_a19_staged_hierarchy_identity([row], [target])
    a13._validate_a19_staged_hierarchy_identity(identity)

    d0 = hashlib.sha256(a13.canonical_json_bytes([row])).hexdigest()
    assert identity["hierarchy_preproof_domain_sha256"] == d0
    assert d0 == (
        "b3789fc44458bf3f361242ac3b891a357de9640eaf72f9ec4f103b7378f74af6"
    )
    assert list(row) == contract["preproof_row_keys"]
    assert row["relationship_id"] == (
        "psid-questionnaire-relationship:"
        "ff2a7f7263d10214f6868b9355f73a30b226ab2cb618dc89e03b96c8e8246159"
    )
    assert row["questionnaire_slot_id"] == (
        "psid-questionnaire-slot:"
        "58e93ce163bb81b1b7838cc36fef0994f207b05684d2a2bb571d5800f87ff7a9"
    )
    assert "hierarchy_absence_proof_id" not in row
    search = identity["search_implementation"]
    assert list(search) == contract["search_implementation_keys"]
    assert search["authority_kind"] == (
        "source_only_canonical_questionnaire_annotation"
    )
    empty_domain_sha256 = (
        "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
    )
    assert search["near_match_source_annotation_count"] == 0
    assert search["near_match_source_annotation_keyset_sha256"] == (
        empty_domain_sha256
    )
    assert search["near_match_source_annotation_domain_sha256"] == (
        empty_domain_sha256
    )
    assert search["hierarchy_preproof_domain_sha256"] == d0
    assert "hierarchy_domain_sha256" not in search
    assert target["target_predicate"] == {
        "roles": ["head_or_reference_person"],
        "job_slot_ids": ["psid-job-slot:role-total"],
        "questionnaire_component_slot_ids": ["psid-component-slot:role-total"],
        "slot_kinds": ["role_total"],
        "field_purposes": ["amount"],
        "quantifier": "no_matching_questionnaire_node_in_searched_domain",
    }
    preimage = [
        target[key] for key in contract["proof_id_preimage_order"][:-1]
    ] + [search]
    proof_id = (
        "psid-absence-proof:"
        + hashlib.sha256(a13.canonical_json_bytes(preimage)).hexdigest()
    )
    assert identity["absence_proof_ids"] == [proof_id]
    assert proof_id == (
        "psid-absence-proof:"
        "f374f82fcbbbc2757e85568e380a75061d4707a7467650ceb9f09382638e9101"
    )
    final_row = {**row, "hierarchy_absence_proof_id": proof_id}
    assert identity["final_hierarchy_rows"] == [final_row]
    d1 = hashlib.sha256(a13.canonical_json_bytes([final_row])).hexdigest()
    assert identity["hierarchy_domain_sha256"] == d1
    assert d1 == (
        "4dd38d95cb08aff565edce70b716bb9f30aef607dcddc2e0c1f51cb8a1bbf453"
    )
    assert d0 != d1
    assert contract["dependency_order"] == [
        "preproof_rows",
        "hierarchy_preproof_domain_sha256",
        "search_implementation",
        "absence_proof_ids",
        "final_hierarchy_rows",
        "hierarchy_domain_sha256",
        "dependent_proof_expanded_era_and_member_digests",
    ]
    assert set(contract["preproof_forbidden_dependencies"]).isdisjoint(row)
    assert contract["placeholder_forbidden"] is True
    assert contract["fixed_point_iteration_forbidden"] is True


@pytest.mark.parametrize(
    "mutation",
    (
        "d0_equals_d1",
        "search_binds_d1",
        "proof_id_forged",
        "final_row_omits_proof",
        "wrong_quantifier",
        "wrong_search_authority",
        "wrong_relationship_id",
        "wrong_slot_id",
        "extra_member",
    ),
)
def test__amendment19__staged_hierarchy_identity_variants_fail_closed(
    mutation,
):
    candidate = a13._derive_a19_staged_hierarchy_identity(
        [a13._a19_worked_preproof_row()],
        [a13._a19_worked_proof_target()],
    )
    if mutation == "d0_equals_d1":
        candidate["hierarchy_preproof_domain_sha256"] = candidate[
            "hierarchy_domain_sha256"
        ]
    elif mutation == "search_binds_d1":
        candidate["search_implementation"][
            "hierarchy_preproof_domain_sha256"
        ] = candidate["hierarchy_domain_sha256"]
    elif mutation == "proof_id_forged":
        candidate["absence_proof_ids"][0] = "psid-absence-proof:" + "0" * 64
    elif mutation == "final_row_omits_proof":
        candidate["final_hierarchy_rows"][0][
            "hierarchy_absence_proof_id"
        ] = None
    elif mutation == "wrong_quantifier":
        candidate["proof_targets"][0]["target_predicate"][
            "quantifier"
        ] = "none_exist"
    elif mutation == "wrong_search_authority":
        candidate["search_implementation"][
            "authority_kind"
        ] = "worked_identity_nonauthority"
    elif mutation == "wrong_relationship_id":
        candidate["preproof_rows"][0]["relationship_id"] = (
            "psid-questionnaire-relationship:" + "0" * 64
        )
    elif mutation == "wrong_slot_id":
        candidate["preproof_rows"][0]["questionnaire_slot_id"] = (
            "psid-questionnaire-slot:" + "0" * 64
        )
    else:
        candidate["unregistered_member"] = None
    with pytest.raises(
        a13.LawError,
        match="Amendment-19 staged hierarchy worked identity drift",
    ):
        a13._validate_a19_staged_hierarchy_identity(candidate)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("applicability", "unconditional"),
        ("selected_failure_variant_executes_hierarchy_construction", True),
        ("g17_c01_normal_projection_sides", ["expected"]),
        (
            "g17_c01_normal_per_era_insertion_order",
            [
                "hierarchy_rows",
                "positive_occurrence_rows",
                "purpose_mapping_rows",
            ],
        ),
        (
            "g17_c01_normal_direct_concatenation_header_members",
            [
                "purpose_mapping_row_count",
                "purpose_mapping_keyset_sha256",
                "purpose_mapping_domain_sha256",
            ],
        ),
        ("selected_failure_variant_executes_g17_c01_projection", True),
    ),
)
def test__amendment19__hierarchy_staging_is_normal_variant_only(field, value):
    candidate = copy.deepcopy(a13.A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    candidate[field] = value
    with pytest.raises(
        a13.LawError,
        match="Amendment-19 staged hierarchy construction contract drift",
    ):
        a13._validate_a19_hierarchy_construction_contract(candidate)


def test__amendment19__supersession_and_identifier_censuses_are_exact():
    assert len(a13.A19_SUPERSESSION_MAP) == 11
    assert len(set(a13.A19_SUPERSESSION_MAP)) == 11
    assert [row[0] for row in a13.A19_SUPERSESSION_MAP] == [
        (
            "§19.3.3 O_H-before-purpose-classification order and O_P "
            "prompt-classification and universal-consumption law"
        ),
        (
            "§§19.3.3 and 26.6.1 effective authority keyset, canonical_order, "
            "pass | fail status, per-era keysets, and direct-concatenation law"
        ),
        (
            "§19.3.3 independently reviewed complete semantic_bindings use "
            "and cross-check law"
        ),
        (
            "§19.3.3 hierarchy row proof-ID, hierarchy digest, search object, "
            "and proof serialization law"
        ),
        (
            "§19.3.3 raw-field ambiguity abort, occurrence-reference and "
            "positive-join nonempty/equal-count cover, and expanded-disposition "
            "join/proof tagged union"
        ),
        (
            "§19.3.3 two-literal proof conclusion and Class-A/Class-B/"
            "inventory keyed joins"
        ),
        (
            "§§19.4.2 and 26.10.1 G17-C01 expected/actual "
            "era_annotation_rows, Q5, inventory, slot, and authority "
            "projections"
        ),
        (
            "§26.11.2 A12-T2-R04 gate and §§29.4.4–29.4.5 source-member "
            "identity, R04, and passing R05 certificate"
        ),
        "§32.4.4, §32.7, and §32.8 active A19 successor-program stop",
        "§32.5.1 active implementation rows",
        "§31.3 executed-transition obligation and generalized oracle",
    ]
    assert a13.A19_NEW_IDENTIFIERS == {
        "schema": ["amendment_19_source_hierarchy_member_construction_law.v1"],
        "disposition_status_reason_lifecycle": [
            "complete_official_mapping",
            "partial_official_mapping_with_legacy_residue_underdetermined",
            "legacy_only_mapping_underdetermined",
            "missing_mapping_underdetermined",
            "fail_source_purpose_mapping_underdetermined",
            "A20_SUCCESSOR_PROGRAM_STOP",
        ],
        "authority_kind_and_canonical_order": [
            "pre_q5_source_hierarchy_failure_member_nonauthority",
            "questionnaire_occurrence_source_order",
        ],
        "member": [
            "hierarchy_preproof_domain_sha256",
            "purpose_mapping_rows",
            "source_classification_row_id",
            "serialized_source_literals",
            "explicit_official_purposes",
            "unresolved_legacy_literals",
            "purpose_mapping_disposition",
            "purpose_mapping_row_count",
            "purpose_mapping_keyset_sha256",
            "purpose_mapping_domain_sha256",
            "purpose_mapping_disposition_counts",
        ],
        "python": [
            "_validate_amendment19_ratification_design",
            "_validate_inherited_amendment19_ratification_design",
            "run_amendment19_member_law_mutation_tests",
        ],
    }


def test__document__amendment18_three_limb_values_are_exact():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    amendment18 = a13._parse_amendment18_projection(raw)
    assert (
        amendment18["build_input_domain_contract"]["schema_version"]
        == "amendment_12_tier2_build_input_domain.v1"
    )
    build_input = amendment18["build_input_domain_contract"]
    assert build_input["questionnaire_document_count"] == 81
    assert build_input["source_document_count"] == 257
    assert build_input["repair_seal_evidence_count"] == 22
    assert build_input["row_count"] == 279
    assert build_input["source_position_domain"] == [0, 256]
    assert build_input["repair_position_domain"] == [257, 278]
    assert build_input["dual_canonical_byte_equality_required"] is True
    assert build_input["artifact_persisted"] is False
    assert amendment18["historical_r05_binding"] == {
        "amendment_number": 15,
        "closure_byte_size": 842,
        "closure_path": (
            "docs/analysis/amendment_15_ratification/closure_v1.json"
        ),
        "closure_raw_sha256": (
            "f48ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a"
        ),
        "design_blob_oid": "50a2a14e1c8845d342dca83559688866e97dc4a7",
        "design_byte_size": 3_881_111,
        "design_path": "docs/design/covered_earnings_correction.md",
        "design_raw_sha256": (
            "556311b72ec6c8e30eeda4b0f602e0f7f43b9d080c2454966fa3dda3a561d16e"
        ),
        "design_revision": 17,
        "ratification_commit": ("c2ffe3e95152ff005485f55acaf75259e6095195"),
        "ratification_commit_sole_parent": (
            "a352e66284b60997210c634bb427141e7e523a75"
        ),
    }
    r06 = amendment18["r06_result_contract"]
    assert r06["path"] == (
        "docs/analysis/amendment_12_rq_catalog_tier2/certification/"
        "amendment11_expected_abort_result_v1.json"
    )
    assert r06["schema_version"] == (
        "amendment_12_tier2_r06_expected_abort_result.v1"
    )
    assert r06["top_level_keys"] == [
        "artifact_id",
        "artifact_role",
        "gate_id",
        "input_identities",
        "integrity",
        "lifecycle",
        "nonemission_evidence",
        "process_result",
        "schema_version",
        "status",
        "test_result",
    ]
    assert r06["integrity_keys"] == ["canonicalization", "payload_sha256"]
    assert r06["input_identity_keys"] == [
        "r05_certification",
        "amendment11_authority_artifact",
        "amendment11_replay_executable",
        "amendment11_source_registry",
    ]
    assert r06["input_identity_row_keys"] == [
        "path",
        "mode",
        "git_blob",
        "byte_size",
        "raw_sha256",
    ]
    for identity in r06["fixed_input_identities"].values():
        assert set(identity) == set(r06["input_identity_row_keys"])
        assert identity["mode"] == "100644"
    assert r06["process_result"]["exit_code"] == 2
    assert r06["process_result"]["stderr_byte_size"] == 174
    assert r06["process_command"] == [
        sys.executable,
        "scripts/replay_amendment11_no_movement.py",
    ]
    for field in r06["process_integer_fields"]:
        assert type(r06["process_result"][field]) is int
    assert r06["test_result"]["module_count"] == 6
    assert r06["test_result"]["collected"] == 223
    assert len(r06["test_module_paths"]) == 6
    assert r06["test_command"] == [
        sys.executable,
        "-m",
        "pytest",
        *r06["test_module_paths"],
    ]
    assert r06["test_environment"] == {"PYTHONPATH": "src:."}
    for field in r06["test_integer_fields"]:
        assert type(r06["test_result"][field]) is int
    assert set(r06["lifecycle"]) == set(r06["lifecycle_keys"])
    assert r06["lifecycle"]["nonauthority"] is True
    assert r06["lifecycle"]["q5_input_emitted"] is False
    assert r06["lifecycle"]["q5_first_add_performed"] is False
    assert r06["lifecycle"]["authority_emitted"] is False
    assert r06["lifecycle"]["next_required_state"] == (
        "A19_SUCCESSOR_PROGRAM_STOP"
    )
    assert r06["nonemission_evidence_keys"] == [
        "execution_commit",
        "execution_tree_oid",
        "repository_manifest_sha256_before",
        "repository_manifest_sha256_after",
        "repository_clean_before",
        "repository_clean_after",
        "repository_read_only",
        "network_disabled",
        "captured_streams",
        "result_path_absent_after_execution",
    ]
    assert r06["manifest_row_keys"] == [
        "path",
        "mode",
        "git_blob",
        "byte_size",
        "raw_sha256",
    ]
    assert r06["first_add_minimum_revision"] == 20
    assert r06["first_add_after_r05"] is True
    assert r06["first_add_name_status_delta"] == [["A", r06["path"]]]
    assert r06["immutable_after_first_add"] is True


def test__document__amendment15_mutation_binding_spec_is_exact():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    rows = a13._parse_amendment15_projection(raw)["mutation_bindings"]
    observed = tuple(
        (
            row["name"],
            row["prepare"],
            row["gate"],
            row["expected_exception"],
            row["expected_message"],
        )
        for row in rows
    )
    assert observed == (
        (
            "ordered_history_attestation_identity_forged",
            "_prepare_attestation_identity_mutation",
            "_gate_ordered_attestation",
            "PublicationError",
            "overlays commit identity drift",
        ),
        (
            "ordered_history_attestation_order_forged",
            "_prepare_attestation_order_mutation",
            "_gate_ordered_attestation_order",
            "PublicationError",
            "strict-ancestor chain drift",
        ),
        (
            "ordered_history_attestation_tree_identity_forged",
            "_prepare_attestation_tree_mutation",
            "_gate_ordered_attestation",
            "PublicationError",
            "tree identity drift",
        ),
        (
            "ordered_history_archive_ref_absent_or_unfetchable",
            "_prepare_absent_archive_mutation",
            "_gate_absent_archive_ref",
            "PublicationError",
            "archive ref is absent or was not fetched",
        ),
        (
            "ordered_history_first_add_exception_reused",
            "_prepare_exception_reuse_mutation",
            "_gate_first_add_exception_reuse",
            "PublicationError",
            "cannot reuse the tier-2 squash exception",
        ),
        (
            "tier2_certification_schema_keyset_drift",
            "_prepare_schema_keyset_mutation",
            "_validate_certification_top_level",
            "PublicationError",
            "keyset drift",
        ),
        (
            "tier2_certification_reconstruction_disagreement",
            "_prepare_reconstruction_disagreement_mutation",
            "_validate_certification_reconstructions",
            "PublicationError",
            "reconstruction disagreement",
        ),
        (
            "tier2_certification_referee_implementation_reused",
            "_prepare_reused_referee_mutation",
            "_validate_certification_reconstructions",
            "PublicationError",
            "not distinct",
        ),
        (
            "tier2_certification_forbidden_emission_forged",
            "_prepare_forbidden_emission_mutation",
            "_validate_certification_lifecycle",
            "PublicationError",
            "forbidden emission or lifecycle drift",
        ),
        (
            "tier2_certification_raw_byte_attestation_forged",
            "_prepare_raw_attestation_mutation",
            "_validate_certification_integrity",
            "PublicationError",
            "raw-byte payload attestation drift",
        ),
        (
            "ceremony_topology_bound_squash_selected",
            "_prepare_topology_squash_mutation",
            "_gate_topology_merge_mode",
            "PublicationError",
            "requires a no-fast-forward merge commit",
        ),
    )


@pytest.mark.parametrize(
    ("original", "forged", "row_index", "field", "forged_value"),
    (
        (
            b"| `ordered_history_attestation_identity_forged` | "
            b"`_prepare_attestation_identity_mutation` | "
            b"`_gate_ordered_attestation` | `PublicationError` | "
            b"`overlays commit identity drift` |",
            b"| `ordered_history_attestation_identity_substituted` | "
            b"`_prepare_attestation_identity_mutation` | "
            b"`_gate_ordered_attestation` | `PublicationError` | "
            b"`overlays commit identity drift` |",
            0,
            "name",
            "ordered_history_attestation_identity_substituted",
        ),
        (
            b"| `ordered_history_attestation_order_forged` | "
            b"`_prepare_attestation_order_mutation` | "
            b"`_gate_ordered_attestation_order` | `PublicationError` | "
            b"`strict-ancestor chain drift` |",
            b"| `ordered_history_attestation_order_forged` | "
            b"`_prepare_attestation_order_mutation` | "
            b"`_gate_ordered_attestation` | `PublicationError` | "
            b"`strict-ancestor chain drift` |",
            1,
            "gate",
            "_gate_ordered_attestation",
        ),
        (
            b"| `tier2_certification_schema_keyset_drift` | "
            b"`_prepare_schema_keyset_mutation` | "
            b"`_validate_certification_top_level` | `PublicationError` | "
            b"`keyset drift` |",
            b"| `tier2_certification_schema_keyset_drift` | "
            b"`_prepare_schema_keyset_mutation` | "
            b"`_validate_certification_top_level` | `ValueError` | "
            b"`keyset drift` |",
            5,
            "expected_exception",
            "ValueError",
        ),
    ),
)
def test__document__amendment15_binding_identity_is_semantically_bound(
    original,
    forged,
    row_index,
    field,
    forged_value,
):
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    baseline = a13._parse_amendment15_projection(raw)
    assert raw.count(original) == 1
    candidate = raw.replace(original, forged, 1)
    changed = a13._parse_amendment15_projection(candidate)
    assert changed["mutation_bindings"][row_index][field] == forged_value
    assert changed["mutation_bindings"] != baseline["mutation_bindings"]
    assert (
        changed["section_semantic_sha256"]
        != baseline["section_semantic_sha256"]
    )
    with pytest.raises(
        a13.LawError,
        match="Amendment-16 document violates immutable-prefix law",
    ):
        a13._validate_document_semantic_projection(candidate, {})


def test__document__amendment15_nonpin_semantics_are_hash_bound():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    original = b"| `source_document_count` | `257` |"
    forged = b"| `source_document_count` | `258` |"
    assert raw.count(original) == 1
    candidate = raw.replace(original, forged, 1)
    assert (
        a13._parse_amendment15_projection(candidate)["section_semantic_sha256"]
        != a13.A15_SECTION_SEMANTIC_SHA256
    )
    with pytest.raises(
        a13.LawError,
        match="Amendment-16 document violates immutable-prefix law",
    ):
        a13._validate_document_semantic_projection(candidate, {})


def test__implementation__active_pins_are_blob_bound_without_commit():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    pins = a13._parse_active_implementation_pins(raw)
    assert set(pins) == {"mode", "files"}
    assert "commit" not in pins
    assert [row["path"] for row in pins["files"]] == [
        "scripts/validate_amendment13_execution_law.py",
        "tests/test_validate_amendment13_execution_law.py",
        "scripts/build_amendment13_tier2_repairs.py",
    ]
    a13._verify_implementation_pins(pins)
    if len(raw) > a13.REVISION21_BYTE_SIZE:
        a19 = {
            row["path"]: row
            for row in a13._parse_amendment19_implementation_pins(
                raw[: a13.REVISION21_BYTE_SIZE]
            )["files"]
        }
        a20 = {row["path"]: row for row in pins["files"]}
        assert (
            a20["scripts/build_amendment13_tier2_repairs.py"]
            == a19["scripts/build_amendment13_tier2_repairs.py"]
        )
        assert (
            a20["scripts/validate_amendment13_execution_law.py"]
            != a19["scripts/validate_amendment13_execution_law.py"]
        )
        assert (
            a20["tests/test_validate_amendment13_execution_law.py"]
            != a19["tests/test_validate_amendment13_execution_law.py"]
        )
    elif len(raw) > a13.REVISION20_BYTE_SIZE:
        a18 = {
            row["path"]: row
            for row in a13._parse_amendment18_implementation_pins(raw)["files"]
        }
        a19 = {row["path"]: row for row in pins["files"]}
        assert (
            a19["scripts/build_amendment13_tier2_repairs.py"]
            == a18["scripts/build_amendment13_tier2_repairs.py"]
        )
        assert (
            a19["scripts/validate_amendment13_execution_law.py"]
            != a18["scripts/validate_amendment13_execution_law.py"]
        )
        assert (
            a19["tests/test_validate_amendment13_execution_law.py"]
            != a18["tests/test_validate_amendment13_execution_law.py"]
        )
    elif len(raw) > a13.REVISION19_BYTE_SIZE:
        a17 = {
            row["path"]: row
            for row in a13._parse_amendment17_implementation_pins(raw)["files"]
        }
        a18 = {row["path"]: row for row in pins["files"]}
        assert (
            a18["scripts/build_amendment13_tier2_repairs.py"]
            == a17["scripts/build_amendment13_tier2_repairs.py"]
        )
        assert (
            a18["scripts/validate_amendment13_execution_law.py"]
            != a17["scripts/validate_amendment13_execution_law.py"]
        )
        assert (
            a18["tests/test_validate_amendment13_execution_law.py"]
            != a17["tests/test_validate_amendment13_execution_law.py"]
        )
    elif len(raw) > a13.REVISION18_BYTE_SIZE:
        a16 = {
            row["path"]: row
            for row in a13._parse_amendment16_implementation_pins(raw)["files"]
        }
        a17 = {row["path"]: row for row in pins["files"]}
        assert (
            a17["scripts/build_amendment13_tier2_repairs.py"]
            == a16["scripts/build_amendment13_tier2_repairs.py"]
        )
        assert (
            a17["scripts/validate_amendment13_execution_law.py"]
            != a16["scripts/validate_amendment13_execution_law.py"]
        )
        assert (
            a17["tests/test_validate_amendment13_execution_law.py"]
            != a16["tests/test_validate_amendment13_execution_law.py"]
        )


def test__document__amendment16_through20_pin_values_are_normalized_only():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    baseline = a13._parse_amendment16_projection(raw)
    section = a13._amendment16_text(raw)
    match = a13._amendment16_implementation_pin_match(section)
    start, end = match.span("validator_sha256")
    absolute_start = a13.REVISION17_BYTE_SIZE + len(
        section[:start].encode("utf-8")
    )
    absolute_end = a13.REVISION17_BYTE_SIZE + len(
        section[:end].encode("utf-8")
    )
    replacement = (
        "1" if match.group("validator_sha256")[0] != "1" else "2"
    ) + match.group("validator_sha256")[1:]
    candidate = (
        raw[:absolute_start] + replacement.encode() + raw[absolute_end:]
    )
    changed = a13._parse_amendment16_projection(candidate)
    assert changed["implementation_pins"] != baseline["implementation_pins"]
    assert changed["section_semantic_sha256"] == (
        baseline["section_semantic_sha256"]
    )

    baseline = a13._parse_amendment19_projection(raw)
    section = a13._amendment19_text(raw)
    match = a13._amendment19_implementation_pin_match(section)
    start, end = match.span("validator_sha256")
    absolute_start = a13.REVISION20_BYTE_SIZE + len(
        section[:start].encode("utf-8")
    )
    absolute_end = a13.REVISION20_BYTE_SIZE + len(
        section[:end].encode("utf-8")
    )
    replacement = (
        "1" if match.group("validator_sha256")[0] != "1" else "2"
    ) + match.group("validator_sha256")[1:]
    candidate = (
        raw[:absolute_start] + replacement.encode() + raw[absolute_end:]
    )
    changed = a13._parse_amendment19_projection(candidate)
    assert changed["implementation_pins"] != baseline["implementation_pins"]
    assert changed["section_semantic_sha256"] == (
        baseline["section_semantic_sha256"]
    )

    baseline = a13._parse_amendment17_projection(raw)
    section = a13._amendment17_text(raw)
    match = a13._amendment17_implementation_pin_match(section)
    start, end = match.span("validator_sha256")
    absolute_start = a13.REVISION18_BYTE_SIZE + len(
        section[:start].encode("utf-8")
    )
    absolute_end = a13.REVISION18_BYTE_SIZE + len(
        section[:end].encode("utf-8")
    )
    replacement = (
        "1" if match.group("validator_sha256")[0] != "1" else "2"
    ) + match.group("validator_sha256")[1:]
    candidate = (
        raw[:absolute_start] + replacement.encode() + raw[absolute_end:]
    )
    changed = a13._parse_amendment17_projection(candidate)
    assert changed["implementation_pins"] != baseline["implementation_pins"]
    assert changed["section_semantic_sha256"] == (
        baseline["section_semantic_sha256"]
    )

    baseline = a13._parse_amendment18_projection(raw)
    section = a13._amendment18_text(raw)
    match = a13._amendment18_implementation_pin_match(section)
    start, end = match.span("validator_sha256")
    absolute_start = a13.REVISION19_BYTE_SIZE + len(
        section[:start].encode("utf-8")
    )
    absolute_end = a13.REVISION19_BYTE_SIZE + len(
        section[:end].encode("utf-8")
    )
    replacement = (
        "1" if match.group("validator_sha256")[0] != "1" else "2"
    ) + match.group("validator_sha256")[1:]
    candidate = (
        raw[:absolute_start] + replacement.encode() + raw[absolute_end:]
    )
    changed = a13._parse_amendment18_projection(candidate)
    assert changed["implementation_pins"] != baseline["implementation_pins"]
    assert changed["section_semantic_sha256"] == (
        baseline["section_semantic_sha256"]
    )

    baseline = a13._parse_amendment20_projection(raw)
    section = a13._amendment20_text(raw)
    match = a13._amendment20_implementation_pin_match(section)
    start, end = match.span("validator_sha256")
    absolute_start = a13.REVISION21_BYTE_SIZE + len(
        section[:start].encode("utf-8")
    )
    absolute_end = a13.REVISION21_BYTE_SIZE + len(
        section[:end].encode("utf-8")
    )
    replacement = (
        "1" if match.group("validator_sha256")[0] != "1" else "2"
    ) + match.group("validator_sha256")[1:]
    candidate = (
        raw[:absolute_start] + replacement.encode() + raw[absolute_end:]
    )
    changed = a13._parse_amendment20_projection(candidate)
    assert changed["implementation_pins"] != baseline["implementation_pins"]
    assert changed["section_semantic_sha256"] == (
        baseline["section_semantic_sha256"]
    )


def test__document__amendment16_nonpin_semantics_are_hash_bound():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    original = b"closure_count_subtrahend = 14"
    forged = b"closure_count_subtrahend = 15"
    assert raw.count(original) == 1
    candidate = raw.replace(original, forged, 1)
    changed = a13._parse_amendment16_projection(candidate)
    assert changed["ratification_law_values"]["closure_count_subtrahend"] == 15
    assert (
        changed["section_semantic_sha256"] != a13.A16_SECTION_SEMANTIC_SHA256
    )
    with pytest.raises(
        a13.LawError,
        match="Amendment-17 document violates immutable-prefix law",
    ):
        a13._validate_document_semantic_projection(candidate, {})


def test__document__successors_preserve_inherited_a17_projection():
    amendment19 = (ROOT / a13.DESIGN_PATH).read_bytes()[
        : a13.REVISION21_BYTE_SIZE
    ]
    amendment18 = amendment19[: a13.REVISION20_BYTE_SIZE]
    amendment17 = amendment18[: a13.REVISION19_BYTE_SIZE]
    forgeries = (
        (
            b"executed_transition_state.v1",
            b"executed_transition_state.v2",
        ),
        (
            b"expected operative domain = tuple(range(13, R - 1))",
            b"expected operative domain = tuple(range(14, R - 1))",
        ),
        (
            b"unverified demonstration makes the amendment unratifiable.",
            b"unverified demonstration makes the amendment ratifiable.",
        ),
    )
    for original, forged in forgeries:
        assert amendment17.count(original) == 1
        candidate = amendment17.replace(original, forged, 1)
        with pytest.raises(
            a13.LawError,
            match="governing Amendment-18 document violates immutable-prefix law",
        ):
            a13._validate_document_semantic_projection(candidate, {})
    for amendment_number, successor in ((17, amendment17), (18, amendment18)):
        a13._validate_non_a13_ratification_design(
            successor,
            amendment_number,
        )
        expected_message = (
            "Amendment-17 ratification design semantic projection drift"
            if amendment_number == 17
            else (
                "Amendment-18 ratification design lacks the immutable "
                "revision-19 prefix or Amendment-18 boundary"
            )
        )
        for original, forged in forgeries:
            assert successor.count(original) == 1
            candidate = successor.replace(original, forged, 1)
            with pytest.raises(
                a13.LawError,
                match=expected_message,
            ):
                a13._validate_non_a13_ratification_design(
                    candidate,
                    amendment_number,
                )


def test__document__historical_routes_and_a20_draft_route_are_closed():
    amendment19 = (ROOT / a13.DESIGN_PATH).read_bytes()[
        : a13.REVISION21_BYTE_SIZE
    ]
    amendment18 = amendment19[: a13.REVISION20_BYTE_SIZE]
    amendment20 = _amendment20_successor(amendment19)
    a13._validate_amendment18_ratification_design(amendment18)
    a13._validate_non_a13_ratification_design(amendment18, 18)
    a13._validate_inherited_amendment18_ratification_design(amendment19)
    a13._validate_non_a13_ratification_design(amendment19, 19)
    a13._validate_amendment19_ratification_design(amendment19)
    a13._validate_inherited_amendment19_ratification_design(amendment20)
    with pytest.raises(a13.LawError):
        a13._validate_non_a13_ratification_design(amendment20, 20)
    draft = (ROOT / a13.DESIGN_PATH).read_bytes()
    assert len(draft) > a13.REVISION21_BYTE_SIZE
    assert hashlib.sha256(draft[: a13.REVISION21_BYTE_SIZE]).hexdigest() == (
        a13.REVISION21_SHA256
    )
    assert a13._git_blob_oid(draft[: a13.REVISION21_BYTE_SIZE]) == (
        a13.REVISION21_BLOB_OID
    )
    assert draft.count(a13.AMENDMENT20_BOUNDARY) == 1
    assert a13._terminal_design_amendment(draft) == 20
    a13._validate_amendment20_draft_design(draft)
    if b"The exact Amendment-20 normative manifest is this one-line" in draft:
        projection = a13._parse_amendment20_projection(draft)
        assert projection["normative_manifest"] == a13.A20_NORMATIVE_MANIFEST
        assert projection["section_semantic_sha256"] == (
            a13.A20_SECTION_SEMANTIC_SHA256
        )
        assert (
            a13._parse_active_implementation_pins(draft)
            == projection["implementation_pins"]
        )
        original = b"Receipt result booleans are not self-authenticating."
        forged = b"Receipt result booleans are not independently binding."
        assert draft.count(original) == 1
        with pytest.raises(
            a13.LawError,
            match="draft semantic projection drift",
        ):
            a13._validate_amendment20_draft_design(
                draft.replace(original, forged, 1)
            )
    expected = (
        "evidence freeze is not ratification-ready"
        if b"The exact Amendment-20 normative manifest is this one-line"
        in draft
        else "Amendment-20 normative manifest marker drift"
    )
    with pytest.raises(a13.LawError, match=expected):
        a13._validate_amendment20_ratification_design(draft)


def test__document__arbitrary_amendment18_suffix_fails_both_routes():
    amendment19 = (ROOT / a13.DESIGN_PATH).read_bytes()[
        : a13.REVISION21_BYTE_SIZE
    ]
    arbitrary = amendment19[: a13.REVISION19_BYTE_SIZE] + (
        a13.AMENDMENT18_BOUNDARY + b"\nArbitrary unprojected law.\n"
    )
    with pytest.raises(a13.LawError):
        a13._validate_amendment18_ratification_design(arbitrary)
    with pytest.raises(a13.LawError):
        a13._validate_non_a13_ratification_design(arbitrary, 18)
    arbitrary_successor = _amendment19_successor(arbitrary)
    with pytest.raises(a13.LawError):
        a13._validate_inherited_amendment18_ratification_design(
            arbitrary_successor
        )
    with pytest.raises(a13.LawError):
        a13._validate_non_a13_ratification_design(arbitrary_successor, 19)


def test__document__arbitrary_amendment19_suffix_fails_all_routes():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()[: a13.REVISION21_BYTE_SIZE]
    arbitrary = raw[: a13.REVISION20_BYTE_SIZE] + (
        a13.AMENDMENT19_BOUNDARY + b"\nArbitrary unprojected law.\n"
    )
    with pytest.raises(a13.LawError):
        a13._validate_amendment19_ratification_design(arbitrary)
    with pytest.raises(a13.LawError):
        a13._validate_non_a13_ratification_design(arbitrary, 19)
    arbitrary_successor = _amendment20_successor(arbitrary)
    with pytest.raises(a13.LawError):
        a13._validate_inherited_amendment19_ratification_design(
            arbitrary_successor
        )
    with pytest.raises(a13.LawError):
        a13._validate_non_a13_ratification_design(arbitrary_successor, 20)


@pytest.mark.parametrize(
    ("original", "forged"),
    (
        (
            b'"field_purpose_prompt_count":21971',
            b'"field_purpose_prompt_count":21970',
        ),
        (
            b'"active_next_required_state":"A20_SUCCESSOR_PROGRAM_STOP"',
            b'"active_next_required_state":"A19_SUCCESSOR_PROGRAM_STOP"',
        ),
        (b'"terminal_revision":21', b'"terminal_revision":20'),
    ),
)
def test__document__amendment19_normative_forgeries_fail_routes(
    original,
    forged,
):
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()[: a13.REVISION21_BYTE_SIZE]
    suffix = raw[a13.REVISION20_BYTE_SIZE :]
    assert suffix.count(original) == 1
    candidate = raw[: a13.REVISION20_BYTE_SIZE] + suffix.replace(
        original,
        forged,
        1,
    )
    assert (
        a13._parse_amendment19_projection(candidate)["section_semantic_sha256"]
        != a13.A19_SECTION_SEMANTIC_SHA256
    )
    with pytest.raises(a13.LawError):
        a13._validate_amendment19_ratification_design(candidate)
    with pytest.raises(a13.LawError):
        a13._validate_inherited_amendment19_ratification_design(
            _amendment20_successor(candidate)
        )


@pytest.mark.parametrize(
    ("original", "forged"),
    (
        (
            b"504159116708ee4d5e2cc8abec130ca8679d22cce928dca42af12be305361c17",
            b"004159116708ee4d5e2cc8abec130ca8679d22cce928dca42af12be305361c17",
        ),
        (
            b"f48ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a",
            b"048ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a",
        ),
        (
            b"79c608eb8baf3b31ea8f14cf461cde27d8637e43602ead19e39dc5388ed9903b",
            b"09c608eb8baf3b31ea8f14cf461cde27d8637e43602ead19e39dc5388ed9903b",
        ),
    ),
)
def test__document__three_limb_forgeries_fail_terminal_and_inherited_routes(
    original,
    forged,
):
    amendment19 = (ROOT / a13.DESIGN_PATH).read_bytes()[
        : a13.REVISION21_BYTE_SIZE
    ]
    amendment18 = amendment19[: a13.REVISION20_BYTE_SIZE]
    prefix = amendment18[: a13.REVISION19_BYTE_SIZE]
    suffix = amendment18[a13.REVISION19_BYTE_SIZE :]
    assert suffix.count(original) == 1
    forged_amendment18 = prefix + suffix.replace(original, forged, 1)
    changed = a13._parse_amendment18_projection(forged_amendment18)
    assert changed["section_semantic_sha256"] != (
        a13.A18_SECTION_SEMANTIC_SHA256
    )
    with pytest.raises(
        a13.LawError,
        match="Amendment-18 ratification design semantic projection drift",
    ):
        a13._validate_amendment18_ratification_design(forged_amendment18)
    forged_amendment19 = _amendment19_successor(forged_amendment18)
    with pytest.raises(
        a13.LawError,
        match="Amendment-18 ratification design semantic projection drift",
    ):
        a13._validate_inherited_amendment18_ratification_design(
            forged_amendment19
        )


def test__amendment16_oracle_mutations_are_separate_and_exact():
    rejected = a13._run_amendment16_oracle_attacks()
    assert rejected == a13.A16_EXPECTED_MUTATIONS
    assert hashlib.sha256(
        a13.canonical_json_bytes(list(rejected))
    ).hexdigest() == (a13.A16_MUTATION_DOMAIN_SHA256)


def test__amendment16_public_runner_authenticates_inherited_census(
    monkeypatch,
):
    import build_amendment13_tier2_repairs as publisher

    expected = publisher._expected_mutation_census()
    monkeypatch.setattr(
        publisher,
        "run_complete_mutation_census",
        lambda: copy.deepcopy(expected),
    )
    assert a13.run_amendment16_oracle_mutation_tests() == (
        a13.A16_EXPECTED_MUTATIONS
    )


def test__amendment16_public_runner_stops_before_attacks_on_census_drift(
    monkeypatch,
):
    import build_amendment13_tier2_repairs as publisher

    forged = publisher._expected_mutation_census()
    forged["rejected_count"] = 99
    monkeypatch.setattr(
        publisher,
        "run_complete_mutation_census",
        lambda: forged,
    )
    monkeypatch.setattr(
        a13,
        "_run_amendment16_oracle_attacks",
        lambda: pytest.fail("A16 attacks ran after inherited census drift"),
    )
    with pytest.raises(
        a13.LawError,
        match="inherited complete mutation census drift",
    ):
        a13.run_amendment16_oracle_mutation_tests()


@pytest.fixture(scope="module")
def amendment18_rejected_mutations():
    return a13.run_amendment18_contract_mutation_tests()


def test__amendment18_contract_mutations_are_separate_and_exact(
    amendment18_rejected_mutations,
):
    rejected = amendment18_rejected_mutations
    assert rejected == a13.A18_EXPECTED_MUTATIONS == A18_TEST_MUTATIONS
    assert (
        hashlib.sha256(a13.canonical_json_bytes(list(rejected))).hexdigest()
        == a13.A18_MUTATION_DOMAIN_SHA256
        == (A18_MUTATION_DOMAIN_SHA256)
    )


def test__amendment18_battery_executes_all_four_mutation_domains(
    amendment18_rejected_mutations,
):
    assert a13.A18_MUTATION_CENSUS == {
        "inherited_complete_mutation_count": 100,
        "inherited_complete_mutation_domain_sha256": (
            "fe2efd7b96c24b7cbd3c6ce350d44906"
            "eb5a88b8b35ee77565c1b133cbf1f3e3"
        ),
        "amendment16_mutation_count": 7,
        "amendment16_mutation_domain_sha256": (
            "1e00099f636c1a727839ebc298b965cd"
            "0981e0ad8f23189367ba7dbd0eddb871"
        ),
        "amendment17_mutation_count": 3,
        "amendment17_mutation_domain_sha256": (
            "b19ebcbf47278d63e12bd8021334a889"
            "10895bdfe48caf2d49c6bbe3014417e6"
        ),
    }
    assert amendment18_rejected_mutations == a13.A18_EXPECTED_MUTATIONS
    assert len(amendment18_rejected_mutations) == 3
    assert a13.A18_MUTATION_DOMAIN_SHA256 == (
        "1bf9f6d30461d003cab597a405cb5cc9" "855273372ed3e7e5b36b1627eaa11108"
    )


@pytest.fixture(scope="module")
def amendment19_rejected_mutations():
    return a13.run_amendment19_member_law_mutation_tests()


def test__amendment19_member_law_mutations_are_separate_and_exact(
    amendment19_rejected_mutations,
):
    rejected = amendment19_rejected_mutations
    assert rejected == a13.A19_EXPECTED_MUTATIONS == A19_TEST_MUTATIONS
    raw = a13.canonical_json_bytes(list(rejected))
    assert len(raw) == a13.A19_MUTATION_DOMAIN_BYTE_SIZE
    assert len(raw) == A19_MUTATION_DOMAIN_BYTE_SIZE
    assert hashlib.sha256(raw).hexdigest() == (a13.A19_MUTATION_DOMAIN_SHA256)
    assert hashlib.sha256(raw).hexdigest() == A19_MUTATION_DOMAIN_SHA256
    assert len(rejected) == len(set(rejected)) == 3


def test__amendment19_battery_authenticates_all_inherited_censuses(
    amendment19_rejected_mutations,
):
    assert amendment19_rejected_mutations == A19_TEST_MUTATIONS
    assert a13.A19_MUTATION_CENSUS == {
        "inherited_complete_mutation_count": 100,
        "inherited_complete_mutation_domain_sha256": (
            "fe2efd7b96c24b7cbd3c6ce350d44906"
            "eb5a88b8b35ee77565c1b133cbf1f3e3"
        ),
        "amendment16_mutation_count": 7,
        "amendment16_mutation_domain_sha256": (
            "1e00099f636c1a727839ebc298b965cd"
            "0981e0ad8f23189367ba7dbd0eddb871"
        ),
        "amendment17_mutation_count": 3,
        "amendment17_mutation_domain_sha256": (
            "b19ebcbf47278d63e12bd8021334a889"
            "10895bdfe48caf2d49c6bbe3014417e6"
        ),
        "amendment18_mutation_count": 3,
        "amendment18_mutation_domain_sha256": (
            "1bf9f6d30461d003cab597a405cb5cc9"
            "855273372ed3e7e5b36b1627eaa11108"
        ),
    }


def test__amendment20_manifest_covers_dual_domains_and_campaign():
    design_raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    projection = a13._parse_amendment20_projection(design_raw)
    manifest = a13.A20_NORMATIVE_MANIFEST
    assert projection["normative_manifest"] == manifest
    a13._validate_a20_manifest_contract(manifest)
    assert manifest["controlling_external_records"] == [
        {
            "logical_path": "e8-ops/sol-ce-a20-charter.md",
            "byte_size": 27_368,
            "raw_sha256": (
                "5ecd4092f3fc62ef894866a1a5b505d6"
                "dba7bb04cde1360ff7134d7d8e927717"
            ),
            "authority": "NONAUTHORITY",
        },
        {
            "logical_path": ("e8-ops/sol-ce-law-gap-sweep-r21-2026-08-16.md"),
            "byte_size": 11_805,
            "raw_sha256": (
                "39887de99d75a395e97b04f33b4c5264"
                "a6828f56c9321cfe248b4ba11a7e5846"
            ),
            "authority": "NONAUTHORITY",
        },
    ]
    source = manifest["source_infrastructure"]
    assert source["semantic_domain_order"] == [
        "missing_reason_source_domain",
        "purpose_source_domain",
    ]
    keys = source["semantic_domain_identity_keys"]
    assert keys == a13.A20_SEMANTIC_DOMAIN_IDENTITY_KEYS
    assert {
        "included_source_rows",
        "included_source_count",
        "included_source_keyset_sha256",
        "included_source_domain_sha256",
        "excluded_source_rows",
        "excluded_source_count",
        "excluded_source_keyset_sha256",
        "excluded_source_domain_sha256",
        "admitted_statement_rows",
        "statement_count",
        "statement_keyset_sha256",
        "statement_domain_sha256",
        "status",
    }.issubset(keys)
    assert "missing_reason_rule_set_identity" in (
        source["successor_source_binding_keys"]
    )
    assert "missing_rule_set_identity" not in (
        source["successor_source_binding_keys"]
    )
    campaign = manifest["evidence_campaign"]
    assert campaign["rounds_formula"] == "ceil(2L/(3q))"
    assert campaign["forecast_as_of"] == "2026-08-15"
    assert campaign["conditional_p50"] == "2026-11-09"
    assert campaign["conditional_p80"] == "2027-01-22"
    assert len(campaign["fail_closed_kill_categories"]) == 15
    assert len(manifest["supersession_coverage"]) == 30
    assert any("30.2.2" in row for row in manifest["supersession_coverage"])
    fifteen_name_disposition = b"then its own fifteen-name inventory."
    assert design_raw.count(fifteen_name_disposition) == 1
    with pytest.raises(
        a13.LawError,
        match="mutation inventory prose disposition drift",
    ):
        a13._parse_amendment20_projection(
            design_raw.replace(
                fifteen_name_disposition,
                b"then its own fourteen-name inventory.",
                1,
            )
        )
    identifiers = manifest["new_identifiers"]
    assert "a20_prompt_field_candidate_sets.v1" in identifiers["schema"]
    assert "a20_semantic_bindings.v1" not in identifiers["schema"]
    assert identifiers["identity_prefix"] == [
        "psid-prompt-field-evidence:",
        "psid-prompt-field-candidate-set:",
        "psid-zero-candidate-positive-group:",
        "a20-lifecycle-output:",
    ]


def test__amendment20_evidence_freeze_is_exactly_unready_not_failed():
    freeze = a13.A20_NORMATIVE_MANIFEST["amendment20_evidence_freeze"]
    assert freeze == a13.A20_EVIDENCE_FREEZE
    assert freeze["schema_version"] == "a20_evidence_freeze.v1"
    assert freeze["amendment20_evidence_freeze_status"] == (
        "not_instantiated_a4_required_before_ratify"
    )
    assert freeze["missing_reason_authority_status"] is None
    assert freeze["purpose_authority_status"] is None
    assert freeze["prompt_field_semantic_binding_status"] is None
    assert list(freeze["expected_identity_bindings"]) == (
        a13.A20_EXPECTED_IDENTITY_NAMES
    )
    assert len(a13.A20_EXPECTED_IDENTITY_NAMES) == 21
    assert set(
        contract["failure_shadow_identity_name"]
        for contract in a13.A20_ARM_IDENTITY_CONTRACTS.values()
    ) == {
        "missing_reason_failure_shadow_identity",
        "purpose_failure_shadow_identity",
        "prompt_field_semantic_failure_shadow_identity",
    }
    assert all(
        value is None
        for value in freeze["expected_identity_bindings"].values()
    )
    assert freeze["amendment20_ratification_ready"] is False
    assert (
        a13.A20_EVIDENCE_FREEZE_CONTRACT[
            "semantic_arm_pass_required_for_ratification"
        ]
        is False
    )
    identity_contract = a13.A20_EVIDENCE_FREEZE_CONTRACT["identity_contract"]
    assert identity_contract["pass_identity_keys"] == (
        a13.A20_PASS_IDENTITY_KEYS
    )
    assert identity_contract["failure_shadow_identity_keys"] == (
        a13.A20_FAILURE_SHADOW_IDENTITY_KEYS
    )
    assert identity_contract["nonemission_complement_identity_keys"] == (
        a13.A20_NONEMISSION_COMPLEMENT_IDENTITY_KEYS
    )
    assert identity_contract["failure_nonemission_evidence_keys"] == (
        a13.A20_FAILURE_NONEMISSION_EVIDENCE_KEYS
    )
    assert {
        "repository_read_only",
        "network_disabled",
        "captured_streams",
    }.isdisjoint(identity_contract["failure_nonemission_evidence_keys"])
    assert identity_contract["repository_manifest_row_keys"] == (
        a13.A20_REPOSITORY_MANIFEST_ROW_KEYS
    )
    assert all(
        len(contract["pass_identity_names"])
        == len(contract["forbidden_output_paths"])
        for contract in a13.A20_ARM_IDENTITY_CONTRACTS.values()
    )
    assert all(
        identifier in a13.A20_NEW_IDENTIFIERS["python"]
        for identifier in (
            "_canonical_amendment20_repository_path",
            "_read_amendment20_worktree_file",
            "_reconstruct_amendment20_repository_manifest",
            "_validate_amendment20_nonemission_evidence",
        )
    )
    a13._validate_amendment20_evidence_freeze(
        freeze,
        a13.A20_EVIDENCE_FREEZE_CONTRACT,
        require_ratification_ready=False,
    )


def test__amendment20_nonemission_provenance_mutation_is_pinned():
    mutation_raw = a13.canonical_json_bytes(list(A20_TEST_MUTATIONS))
    assert A20_TEST_MUTATIONS[-5:] == (
        "determined_as_source_underdetermined_without_ruling_forged",
        "source_underdetermined_as_no_applicable_purpose_forged",
        "source_underdetermined_a4_census_binding_forged",
        "completed_ontology_new_arm_omitted",
        "coordinate_distinct_questionnaire_spans_collapsed_to_one_body_forged",
    )
    assert len(mutation_raw) == a13.A20_MUTATION_DOMAIN_BYTE_SIZE
    assert hashlib.sha256(mutation_raw).hexdigest() == (
        a13.A20_MUTATION_DOMAIN_SHA256
    )


def test__amendment20_completed_purpose_ontology_is_fail_closed():
    purpose = a13.A20_PURPOSE_AUTHORITY_CONTRACT
    assert purpose["completed_ontology_order"] == [
        *a13.A19_OFFICIAL_PURPOSES,
        "source_underdetermined",
    ]
    assert purpose["prompt_denominator_a4_freeze_slot"] is None
    assert purpose["required_disposition_counts"] == {
        "complete_official_mapping": None,
        "source_underdetermined": None,
        "U": 0,
    }
    assert purpose["source_underdetermined_count_a4_freeze_slot"] is None
    assert purpose[
        "source_underdetermined_requires_reconciled_adjudication_ruling"
    ]
    assert purpose[
        "source_underdetermined_uses_determined_row_provenance_authentication"
    ]
    assert not purpose["source_underdetermined_is_no_applicable_purpose"]
    assert purpose["source_backed_alternative_selected"] == (
        "ontology_projection"
    )
    assert not purpose["exact_row_agreement_is_authority_gate"]
    assert purpose[
        "macro_per_prompt_jaccard_minimum_calibration_diagnostic"
    ] == ("90%")
    r04 = a13.A20_R04_Q5_CONTRACT
    assert not r04["purpose_totality_alone_passes_r04"]
    assert r04["o_p_order"] == purpose["completed_ontology_order"]
    assert r04["selector_purpose_domain"] == "completed_purpose_ontology"


def test__amendment20_c68_and_zero_candidate_probes_fail_closed():
    contract = a13.A20_PROMPT_FIELD_SEMANTIC_BINDING_CONTRACT
    assert contract["collision_census"] == {
        "domain": "historical_same_coordinate_leading_question_token_conflicts",
        "complete_official_prompt_count": 818,
        "multiple_count": 46,
    }
    assert (
        contract["complete_official_prompt_candidate_census"]["multiple_count"]
        == 49
    )
    assert contract["full_prompt_candidate_census"] == {
        "domain": "multiple_candidates_over_full_prompt_denominator",
        "prompt_count": 21_971,
        "multiple_count": 2_349,
    }
    assert contract["prompt_field_row_keys"][3] == "questionnaire_span"
    assert contract["prompt_field_evidence_id_prefix"] == (
        "psid-prompt-field-evidence:"
    )
    assert contract["coordinate_distinct_span_collapse_aborts"]
    assert contract["c68_regression"] == {
        "source_prompt_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "4cd66190a898d568dd20c27140f44f1dff53d229f664f537722624d00c9b4b67"
        ),
        "interview_wave": 1985,
        "printed_direct_field_id": "V11804",
        "question_token": "C68.",
        "candidate_raw_field_ids": ["V11804", "V11805"],
        "draft_disposition": "unresolved_multiple",
    }
    probe = contract["zero_candidate_grouping_probe"]
    assert probe["sweep_zero_candidate_observation"] == 15_428
    assert probe["diagnostic_zero_candidate_observation"] == 14_450
    assert probe["difference_explained"] is False
    assert contract["direct_identifier_priority_forbidden"] is True
    assert contract["attachment_dispositions"] == [
        "accepted_exact_source_identifier",
        "accepted_expressly_admitted_official_alias",
        "unresolved_multiple",
    ]
    assert contract["prompt_field_candidate_set_row_keys"] == [
        "prompt_field_candidate_set_id",
        "source_prompt_occurrence_id",
        "interview_wave",
        "candidate_prompt_field_evidence_ids",
        "candidate_raw_field_ids",
        "candidate_count",
        "candidate_disposition",
    ]
    assert contract["prompt_field_candidate_set_dispositions"] == [
        "zero_candidates",
        "one_candidate",
        "multiple_candidates",
    ]
    assert contract["candidate_arrays_complete_stable_unique_source_order"]
    assert contract["candidate_disposition_is_iff_count_partition"]
    assert contract[
        "candidate_set_id_is_sha256_of_canonical_remaining_members"
    ]
    assert contract["candidate_set_row_ids_and_prompt_ids_unique"]
    assert contract["zero_candidate_positive_group_row_keys"] == [
        "zero_candidate_positive_group_id",
        "positive_occurrence_id",
        "zero_candidate_source_prompt_occurrence_ids",
        "all_source_prompt_occurrence_ids",
        "complete_reference_union_ids",
        "empty_reference_union",
        "group_disposition",
    ]
    assert contract["zero_candidate_positive_group_dispositions"] == [
        "complete_nonempty_reference_union",
        "fail_empty_reference_union",
    ]
    assert contract[
        "zero_candidate_group_one_per_qualifying_positive_occurrence"
    ]
    assert contract[
        "zero_candidate_prompt_arrays_complete_positive_row_projections"
    ]
    assert contract["zero_candidate_reference_union_complete_stable_unique"]
    assert contract["zero_candidate_group_disposition_is_iff_empty_boolean"]
    assert contract["semantic_binding_serialization"] == (
        "near_match_source_annotation_rows"
    )
    assert (
        contract["separate_semantic_binding_rows_serialization_permitted"]
        is False
    )


def test__amendment20_r06_and_lifecycle_bind_six_files_223_nodes_26_rows():
    contract = a13.A20_R06_LIFECYCLE_CONTRACT
    assert (
        contract["interpreter_selector"] == "executing_process_sys.executable"
    )
    assert contract["test_command_after_interpreter"][:2] == ["-m", "pytest"]
    assert len(contract["test_file_identities"]) == 6
    assert contract["collected_node_id_count"] == 223
    assert contract["collection_command_after_interpreter"] == [
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        *[row["path"] for row in a13.A20_R06_FILE_IDENTITIES],
    ]
    binding = a13._validate_amendment20_r06_collection_binding()
    assert binding["command"][0] == sys.executable
    assert len(binding["node_ids"]) == 223
    assert binding["node_id_array_canonical_byte_size"] == 28_268
    assert binding["node_id_array_raw_sha256"] == (
        "09071bf4d9a9a5ee8b9ccc4d8d5c0bd91705c04d3c7c99d6ef155dfdc0dfdf05"
    )
    assert contract["collected_node_id_array_canonical_byte_size"] == 28_268
    assert contract["collected_node_id_array_raw_sha256"] == (
        "09071bf4d9a9a5ee8b9ccc4d8d5c0bd91705c04d3c7c99d6ef155dfdc0dfdf05"
    )
    rows = contract["dormant_lifecycle_rows"]
    assert len(rows) == contract["dormant_lifecycle_row_count"] == 26
    assert [row["first_add_index"] for row in rows] == list(range(1, 27))
    assert all(row["output_identity_id"] is None for row in rows)
    assert all(row["selection_enabled"] is False for row in rows)
    assert all(row["status"] == "dormant_definition" for row in rows)
    assert rows[0]["input_identity_ids"] == [
        "revision22_registry_repin_identity",
        "a20_successor_source_binding_identity",
        "dormant_lifecycle_definition_identity",
    ]
    assert rows[3]["input_identity_ids"] == [
        "a20_r05_certificate_identity",
        "r06_six_module_identity",
        "r06_collected_node_id_identity",
        "historical_a11_replay_identity",
    ]
    assert rows[4]["lifecycle_stage_id"] == (
        "A20_MISSING_REASON_SUCCESSOR_ACTIVE"
    )
    assert rows[4]["input_identity_ids"] == [
        "a20_historical_r06_identity",
        "missing_reason_successor_relation_identity",
    ]
    consumed_freeze_identities = set(
        a13.A20_SOURCE_INFRASTRUCTURE_CONTRACT["successor_source_binding_keys"]
    ) | {identity for row in rows for identity in row["input_identity_ids"]}
    assert set(a13.A20_EXPECTED_IDENTITY_NAMES) <= consumed_freeze_identities


def test__amendment20_q5_shapes_replace_a19_purpose_rows_exactly():
    contract = a13.A20_R04_Q5_CONTRACT
    assert contract["source_document_manifest_additions"] == [
        "a20_successor_source_binding_identity",
        "missing_reason_source_domain_identity",
        "purpose_source_domain_identity",
        "missing_reason_rule_set_identity",
        "purpose_rule_set_identity",
        "prompt_field_evidence_identity",
        "semantic_binding_identity",
    ]
    assert contract["replaced_a19_effective_header_members"] == [
        "purpose_mapping_row_count",
        "purpose_mapping_keyset_sha256",
        "purpose_mapping_domain_sha256",
        "purpose_mapping_disposition_counts",
    ]
    assert contract["normal_era_successor_sequence"] == [
        "hierarchy_rows",
        "purpose_authority_mapping_rows",
        "prompt_field_evidence_rows",
        "prompt_field_candidate_set_rows",
        "zero_candidate_positive_group_rows",
        "positive_occurrence_rows",
    ]
    assert contract["inherited_semantic_relation_member"] == (
        "near_match_source_annotation_rows"
    )
    assert contract["inherited_semantic_relation_position"] == (
        "after_expanded_disposition_rows"
    )
    assert (
        contract[
            "a19_purpose_mapping_is_historical_nonconsumable_on_a20_normal_path"
        ]
        is True
    )


def _a20_qualifying_verdict(design_size="1,234", receipt_size="5,678"):
    return (
        "# RATIFY\n"
        f"attested_design_byte_size: {design_size}\n"
        f"attested_design_raw_sha256: {'a' * 64}\n"
        f"attested_design_blob_oid: {'b' * 40}\n"
        f"executed_transition_receipt_byte_size: {receipt_size}\n"
        f"executed_transition_receipt_raw_sha256: {'c' * 64}\n"
        "executed_transition_receipt_schema: executed_transition_state.v2\n"
        "---\n"
    ).encode()


def test__amendment20_qualifying_verdict_accepts_both_decimal_forms():
    for design_size, receipt_size in (("1234", "5678"), ("1,234", "5,678")):
        parsed = a13.validate_amendment20_qualifying_verdict(
            _a20_qualifying_verdict(design_size, receipt_size),
            design_byte_size=1_234,
            design_raw_sha256="a" * 64,
            design_blob_oid="b" * 40,
            receipt_byte_size=5_678,
            receipt_raw_sha256="c" * 64,
        )
        assert parsed["receipt_schema"] == "executed_transition_state.v2"


@pytest.mark.parametrize(
    ("original", "forged"),
    (
        (b"1,234", b"01,234"),
        (b"1,234", b"12,34"),
        (b"executed_transition_state.v2", b"executed_transition_state.v1"),
        (b"# RATIFY\n", b"preface\n# RATIFY\n"),
        (b"---\n", b"---\nextra\n"),
        (b"a" * 64, b"A" * 64),
    ),
)
def test__amendment20_qualifying_verdict_variants_fail_closed(
    original,
    forged,
):
    raw = _a20_qualifying_verdict()
    assert raw.count(original) == 1
    with pytest.raises(a13.LawError):
        a13.validate_amendment20_qualifying_verdict(
            raw.replace(original, forged, 1),
            design_byte_size=1_234,
            design_raw_sha256="a" * 64,
            design_blob_oid="b" * 40,
            receipt_byte_size=5_678,
            receipt_raw_sha256="c" * 64,
        )


def test__amendment20_historical_receipt_uses_a20_design_at_revision23(
    monkeypatch,
):
    historical_design = (ROOT / a13.DESIGN_PATH).read_bytes()
    historical_sha256 = hashlib.sha256(historical_design).hexdigest()
    historical_blob_oid = a13._git_blob_oid(historical_design)
    historical_commit = "c" * 40
    receipt = {
        "simulated_state_manifest": {
            "candidate_commit_identity": {"commit": historical_commit}
        }
    }
    receipt_raw = a13.canonical_json_bytes(receipt)
    verdict_raw = (
        "# RATIFY\n"
        f"attested_design_byte_size: {len(historical_design)}\n"
        f"attested_design_raw_sha256: {historical_sha256}\n"
        f"attested_design_blob_oid: {historical_blob_oid}\n"
        f"executed_transition_receipt_byte_size: {len(receipt_raw)}\n"
        "executed_transition_receipt_raw_sha256: "
        f"{hashlib.sha256(receipt_raw).hexdigest()}\n"
        "executed_transition_receipt_schema: executed_transition_state.v2\n"
        "---\n"
    ).encode()
    verdict_paths = [
        "docs/analysis/amendment_20_ratification/"
        "sol-ce-amend20-r1-verdict.md",
        "docs/analysis/amendment_20_ratification/"
        "sol-ce-amend20-r1b-verdict.md",
    ]
    closure = {
        "amendment_number": 20,
        "attested_candidate_design_blob_oid": historical_blob_oid,
        "attested_candidate_design_byte_size": len(historical_design),
        "attested_candidate_design_raw_sha256": historical_sha256,
        "operator_merge_commit": historical_commit,
        "ratification_commit": historical_commit,
        "ratification_commit_sole_parent": "d" * 40,
        "verdict_artifacts": [
            {
                "path": path,
                "byte_size": len(verdict_raw),
                "raw_sha256": hashlib.sha256(verdict_raw).hexdigest(),
            }
            for path in verdict_paths
        ],
    }
    closure_raw = a13.canonical_json_bytes(closure)
    closure_binding = a13._closure_binding(
        a13._ratification_closure_path(20), closure_raw
    )
    revision23_context = _synthetic_registry_context(23)
    revision23_context["ratification_closures"][20 - 13] = closure_binding
    assert revision23_context["ratification_commit"] != historical_commit
    assert revision23_context["blob_sha256"] != historical_sha256

    receipt_validations = []
    design_validations = []
    monkeypatch.setattr(
        a13,
        "_validate_amendment20_transition_receipt",
        lambda value: receipt_validations.append(copy.deepcopy(value))
        or value,
    )
    monkeypatch.setattr(
        a13,
        "_validate_amendment20_ratification_design",
        lambda raw: design_validations.append(raw),
    )

    def fake_git(*arguments, text=False):
        assert arguments == (
            "show",
            f"{historical_commit}:{a13.DESIGN_PATH}",
        )
        assert text is False
        return historical_design

    monkeypatch.setattr(a13, "_git", fake_git)
    validated = a13._validate_ratification_closure(
        closure_raw,
        closure_binding,
        {path: verdict_raw for path in verdict_paths},
        20,
        verify_git=False,
        ratification_design_raw=historical_design,
        registry_design_binding=revision23_context,
        amendment20_transition_receipt_raw=receipt_raw,
    )
    assert validated == closure
    assert receipt_validations == [receipt]
    assert design_validations == [historical_design]


def test__amendment20_standin_is_distinct_and_never_qualifying(monkeypatch):
    standin = (
        "# RATIFY\n"
        "attested_design_byte_size: 1,234\n"
        f"attested_design_raw_sha256: {'a' * 64}\n"
        f"attested_design_blob_oid: {'b' * 40}\n"
        "executed_transition_receipt_status: pending_same_state_execution\n"
        "simulation_context: amendment20_same_state_nonauthority_v1\n"
        "---\n"
    ).encode()
    parsed = a13._validate_amendment20_simulated_standin(
        standin,
        design_byte_size=1_234,
        design_raw_sha256="a" * 64,
        design_blob_oid="b" * 40,
    )
    assert parsed["executed_transition_receipt_status"] == (
        "pending_same_state_execution"
    )
    with pytest.raises(a13.LawError):
        a13.validate_amendment20_qualifying_verdict(
            standin,
            design_byte_size=1_234,
            design_raw_sha256="a" * 64,
            design_blob_oid="b" * 40,
            receipt_byte_size=5_678,
            receipt_raw_sha256="c" * 64,
        )

    verdict_paths = a13.A20_RECEIPT_SCHEMA["expected_changed_paths"][:2]
    closure = {
        "amendment_number": 20,
        "attested_candidate_design_blob_oid": "b" * 40,
        "attested_candidate_design_byte_size": 1_234,
        "attested_candidate_design_raw_sha256": "a" * 64,
        "operator_merge_commit": "d" * 40,
        "ratification_commit": "d" * 40,
        "ratification_commit_sole_parent": "e" * 40,
        "verdict_artifacts": [
            {
                "path": path,
                "byte_size": len(standin),
                "raw_sha256": hashlib.sha256(standin).hexdigest(),
            }
            for path in verdict_paths
        ],
    }
    closure_raw = a13.canonical_json_bytes(closure)
    context = _synthetic_registry_context(22)
    context["ratification_closures"][-1] = {
        "path": a13._ratification_closure_path(20),
        "raw_byte_size": len(closure_raw),
        "raw_sha256": hashlib.sha256(closure_raw).hexdigest(),
    }
    reads = {
        a13._ratification_closure_path(20): closure_raw,
        **{path: standin for path in verdict_paths},
    }
    monkeypatch.setattr(
        a13,
        "_read_public_repository_file",
        lambda path, label, require_regular_mode: reads[path],
    )
    calls = []
    monkeypatch.setattr(
        a13,
        "_validate_amendment20_scratch_transition_context",
        lambda verdicts: calls.append(dict(verdicts))
        or {"registry_binding": context, "closure": closure},
    )
    assert a13._validate_public_ratification_closure(20, context) == closure
    assert calls == [{path: standin for path in verdict_paths}]


def test__amendment20_receipt_v2_changed_path_identity_is_exact():
    paths = a13.A20_RECEIPT_SCHEMA["expected_changed_paths"]
    raw = a13.canonical_json_bytes(paths)
    assert len(paths) == 4
    assert len(raw) == 260
    assert hashlib.sha256(raw).hexdigest() == (
        "5a7912498c4d959fef337f2a1d1cf85a2f254fa29d825d365ccf4fe214ad48a7"
    )
    assert a13.A20_RECEIPT_SCHEMA["manifest_schema_version"] == (
        "executed_transition_state.v2"
    )
    assert "candidate_or_scratch_HEAD" not in (
        a13.A20_RECEIPT_SCHEMA["manifest_keys"]
    )
    receipt_contract = a13.A20_RATIFICATION_RECEIPT_CONTRACT
    assert receipt_contract["amendment20_external_receipt_path"] == (
        "docs/analysis/amendment_20_ratification/"
        "executed_transition_receipt_v2.json"
    )
    assert receipt_contract["external_receipt_mode"] == "100644"
    assert receipt_contract["external_receipt_candidate_ancestry_not_required"]
    assert receipt_contract[
        "receipt_candidate_design_exactly_cross_binds_historical_a20_closure_and_verdicts"
    ]
    assert receipt_contract[
        "current_terminal_registry_cross_binding_required_iff_a20_terminal_revision22"
    ]
    assert receipt_contract[
        "later_revision_authenticates_historical_a20_design_under_30_2_3"
    ]


def _synthetic_a20_receipt_v2():
    candidate = "c" * 40
    scratch = "d" * 40
    paths = list(a13.A20_RECEIPT_SCHEMA["expected_changed_paths"])
    candidate_raw = b"synthetic Amendment-20 candidate\n"
    test_path = "tests/test_validate_amendment13_execution_law.py"
    test_raw = b"synthetic pinned test\n"
    test_blob = a13._git_blob_oid(test_raw)
    pins = {
        "mode": "100644",
        "files": [
            {
                "path": test_path,
                "blob_oid": test_blob,
                "byte_size": len(test_raw),
                "sha256": hashlib.sha256(test_raw).hexdigest(),
            }
        ],
    }
    standin = (
        "# RATIFY\n"
        f"attested_design_byte_size: {len(candidate_raw)}\n"
        "attested_design_raw_sha256: "
        f"{hashlib.sha256(candidate_raw).hexdigest()}\n"
        f"attested_design_blob_oid: {a13._git_blob_oid(candidate_raw)}\n"
        "executed_transition_receipt_status: pending_same_state_execution\n"
        "simulation_context: amendment20_same_state_nonauthority_v1\n"
        "---\n"
    ).encode()
    closure_raws = {
        a13._ratification_closure_path(amendment_number): (
            f"synthetic closure {amendment_number}\n".encode()
        )
        for amendment_number in range(13, 20)
    }
    synthetic_closure = {
        "amendment_number": 20,
        "attested_candidate_design_blob_oid": a13._git_blob_oid(candidate_raw),
        "attested_candidate_design_byte_size": len(candidate_raw),
        "attested_candidate_design_raw_sha256": hashlib.sha256(
            candidate_raw
        ).hexdigest(),
        "ratification_commit": candidate,
        "ratification_commit_sole_parent": "e" * 40,
        "operator_merge_commit": candidate,
        "verdict_artifacts": [
            {
                "path": path,
                "byte_size": len(standin),
                "raw_sha256": hashlib.sha256(standin).hexdigest(),
            }
            for path in paths[:2]
        ],
    }
    closure_raws[a13._ratification_closure_path(20)] = (
        a13.canonical_json_bytes(synthetic_closure)
    )
    closure_identities = [
        {
            "path": path,
            "raw_byte_size": len(raw),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": a13._git_blob_oid(raw),
        }
        for path, raw in closure_raws.items()
    ]
    registry_binding = {
        "path": a13.DESIGN_PATH,
        "ratification_commit": candidate,
        "revision": 22,
        "blob_sha256": hashlib.sha256(candidate_raw).hexdigest(),
        "ratification_closures": [
            {
                "path": row["path"],
                "raw_byte_size": row["raw_byte_size"],
                "raw_sha256": row["raw_sha256"],
            }
            for row in closure_identities
        ],
    }
    registry_behavior = (
        "\ndef design_binding():\n"
        "    return {\n"
        "        'path': DESIGN_PATH,\n"
        "        'ratification_commit': DESIGN_RATIFICATION_COMMIT,\n"
        "        'revision': DESIGN_REVISION,\n"
        "        'blob_sha256': DESIGN_BLOB_SHA256,\n"
        "        'ratification_closures': [\n"
        "            dict(row) for row in RATIFICATION_CLOSURE_BINDINGS\n"
        "        ],\n"
        "    }\n"
    )
    candidate_registry_raw = (
        f"DESIGN_PATH = {a13.DESIGN_PATH!r}\n"
        "DESIGN_RATIFICATION_COMMIT = 'production-revision-21'\n"
        "DESIGN_REVISION = 21\n"
        "DESIGN_BYTE_SIZE = 1\n"
        "DESIGN_BLOB_SHA256 = 'production-revision-21'\n"
        "RATIFICATION_CLOSURE_BINDINGS = ()\n"
        f"{registry_behavior}"
    ).encode()
    scratch_registry_raw = (
        f"DESIGN_PATH = {a13.DESIGN_PATH!r}\n"
        f"DESIGN_RATIFICATION_COMMIT = {candidate!r}\n"
        "DESIGN_REVISION = 22\n"
        f"DESIGN_BYTE_SIZE = {len(candidate_raw)}\n"
        "DESIGN_BLOB_SHA256 = "
        f"{hashlib.sha256(candidate_raw).hexdigest()!r}\n"
        "RATIFICATION_CLOSURE_BINDINGS = "
        f"{tuple(registry_binding['ratification_closures'])!r}\n"
        "SIMULATED_STATE_AUTHORITY = 'NONAUTHORITY'\n"
        "SIMULATION_CONTEXT = "
        "'amendment20_same_state_nonauthority_v1'\n"
        f"{registry_behavior}"
    ).encode()
    scratch_raws = {
        paths[0]: standin,
        paths[1]: standin,
        paths[3]: scratch_registry_raw,
    }
    test_identity = {
        "path": test_path,
        "mode": "100644",
        "git_blob": test_blob,
        "raw_byte_size": len(test_raw),
        "raw_sha256": hashlib.sha256(test_raw).hexdigest(),
    }
    manifest = {
        "schema_version": "executed_transition_state.v2",
        "simulated_state_authority": "NONAUTHORITY",
        "candidate_commit_identity": {
            "commit": candidate,
            "tree": "a" * 40,
            "sole_parent": "e" * 40,
        },
        "scratch_transition": {
            "commit": scratch,
            "tree": "b" * 40,
            "sole_parent": candidate,
            "changed_paths": paths,
            "changed_path_domain_sha256": (
                a13.A20_RECEIPT_SCHEMA["expected_changed_path_domain_sha256"]
            ),
        },
        "terminal_revision": 22,
        "canonical_registry_binding": registry_binding,
        "ordered_closure_identities": closure_identities,
        "full_pinned_battery_test_identity": test_identity,
    }
    state_identity = hashlib.sha256(
        a13.canonical_json_bytes(manifest)
    ).hexdigest()
    receipt = {
        "simulated_state_authority": "NONAUTHORITY",
        "simulated_state_identity_sha256": state_identity,
        "simulated_state_manifest": manifest,
        "terminal_revision": 22,
        "public_oracle": {
            "entrypoint": "validate_ratification_operativity",
            "executed": True,
            "exit_code": 0,
            "operative_amendments": list(range(13, 21)),
            "simulated_state_identity_sha256": state_identity,
        },
        "full_pinned_battery": {
            "executed": True,
            "exit_code": 0,
            "test_path": test_path,
            "test_mode_blob_bytes_sha256": test_identity,
            "exact_command": a13.A20_FULL_PINNED_BATTERY_COMMAND,
            "collected": a13.A20_FULL_PINNED_BATTERY_COLLECTED,
            "passed": a13.A20_FULL_PINNED_BATTERY_COLLECTED,
            "failed": 0,
            "skipped": 0,
            "deselected": 0,
            "xfailed": 0,
            "xpassed": 0,
            "simulated_state_identity_sha256": state_identity,
        },
    }
    return (
        receipt,
        candidate_raw,
        test_raw,
        pins,
        closure_raws,
        candidate_registry_raw,
        scratch_raws,
    )


def test__amendment20_receipt_v2_rederives_both_git_identities(monkeypatch):
    (
        receipt,
        candidate_raw,
        test_raw,
        pins,
        closure_raws,
        candidate_registry_raw,
        scratch_raws,
    ) = _synthetic_a20_receipt_v2()
    candidate = "c" * 40
    scratch = "d" * 40
    paths = a13.A20_RECEIPT_SCHEMA["expected_changed_paths"]
    monkeypatch.setattr(
        a13,
        "A20_PRODUCTION_REGISTRY_IDENTITY",
        {
            "path": "scripts/covered_earnings_correction_registry.py",
            "mode": "100644",
            "git_blob": a13._git_blob_oid(candidate_registry_raw),
            "byte_size": len(candidate_registry_raw),
            "raw_sha256": hashlib.sha256(candidate_registry_raw).hexdigest(),
        },
    )

    def fake_git(*arguments, text=False):
        if arguments[:3] == ("rev-list", "--parents", "-n"):
            assert text is True
            commit = arguments[-1]
            if commit == candidate:
                return f"{candidate} {'e' * 40}\n"
            return f"{scratch} {candidate}\n"
        if arguments[:1] == ("rev-parse",):
            assert text is True
            return (
                ("a" * 40 + "\n")
                if candidate in arguments[1]
                else ("b" * 40 + "\n")
            )
        if arguments[:1] == ("diff-tree",):
            assert text is True
            return "\n".join(reversed(paths)) + "\n"
        if arguments[:1] == ("for-each-ref",):
            assert text is True
            return ""
        if arguments[:1] == ("log",):
            assert text is True
            path = arguments[-1]
            return (
                ("1" * 40 + "\n")
                if path == a13.A20_EXECUTED_TRANSITION_RECEIPT_PATH
                else ("2" * 40 + "\n")
            )
        if arguments[:1] == ("show",):
            assert text is False
            specification = arguments[1]
            _, path = specification.split(":", 1)
            if path == a13.DESIGN_PATH:
                return candidate_raw
            if path == "tests/test_validate_amendment13_execution_law.py":
                return test_raw
            if (
                path == "scripts/covered_earnings_correction_registry.py"
                and specification.startswith(f"{candidate}:")
            ):
                return candidate_registry_raw
            if path in closure_raws:
                return closure_raws[path]
            return scratch_raws[path]
        if arguments[:1] == ("ls-tree",):
            assert text is True
            commit, path = arguments[1], arguments[-1]
            if commit == candidate:
                if path == a13.DESIGN_PATH:
                    return (
                        f"100644 blob {a13._git_blob_oid(candidate_raw)}"
                        f"\t{path}\n"
                    )
                row = pins["files"][0]
                if path == row["path"]:
                    return f"100644 blob {row['blob_oid']}\t{path}\n"
                return (
                    "100644 blob "
                    f"{a13._git_blob_oid(candidate_registry_raw)}\t{path}\n"
                )
            raw = closure_raws.get(path, scratch_raws.get(path))
            assert raw is not None
            return f"100644 blob {a13._git_blob_oid(raw)}\t{path}\n"
        raise AssertionError(arguments)

    monkeypatch.setattr(a13, "_git", fake_git)

    def fake_run_git(*arguments, **kwargs):
        return_code = 1
        if arguments[:2] == ("merge-base", "--is-ancestor") and arguments[
            -2:
        ] == ("1" * 40, "2" * 40):
            return_code = 0
        return subprocess.CompletedProcess(
            arguments,
            return_code,
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(a13, "_run_git", fake_run_git)
    monkeypatch.setattr(
        a13,
        "_read_public_repository_file",
        lambda path, label, require_regular_mode: a13.canonical_json_bytes(
            receipt
        ),
    )
    monkeypatch.setattr(
        a13,
        "_validate_registry_ratification_context",
        lambda binding: dict(binding),
    )
    monkeypatch.setattr(
        a13,
        "_validate_amendment20_ratification_design",
        lambda raw: None,
    )
    monkeypatch.setattr(
        a13,
        "_parse_amendment20_implementation_pins",
        lambda raw: pins,
    )
    assert a13._validate_amendment20_transition_receipt(receipt) == receipt
    registry_path = "scripts/covered_earnings_correction_registry.py"
    valid_scratch_registry = scratch_raws[registry_path]
    scratch_raws[registry_path] = valid_scratch_registry.replace(
        b"        'revision': DESIGN_REVISION,\n",
        b"        'revision': 999,\n",
        1,
    )
    with pytest.raises(
        a13.LawError,
        match="scratch registry behavior differs from candidate",
    ):
        a13._validate_amendment20_transition_receipt(receipt)
    scratch_raws[registry_path] = valid_scratch_registry
    for forged_candidate_registry in (
        candidate_registry_raw + b"DESIGN_REVISION = 21\n",
        candidate_registry_raw.replace(
            b"DESIGN_REVISION = 21\n",
            b"DESIGN_REVISION = int('21')\n",
            1,
        ),
    ):
        with pytest.raises(
            a13.LawError,
            match="scratch registry behavior differs from candidate",
        ):
            a13._parse_amendment20_scratch_registry_binding(
                valid_scratch_registry,
                candidate_raw=forged_candidate_registry,
            )
    with pytest.raises(
        a13.LawError,
        match="mutates a closed binding name",
    ):
        a13._parse_amendment20_scratch_registry_binding(
            valid_scratch_registry + b"DESIGN_REVISION += 1\n",
            candidate_raw=candidate_registry_raw + b"DESIGN_REVISION += 1\n",
        )
    forged = copy.deepcopy(receipt)
    forged["simulated_state_manifest"]["candidate_commit_identity"]["tree"] = (
        "f" * 40
    )
    forged["simulated_state_identity_sha256"] = hashlib.sha256(
        a13.canonical_json_bytes(forged["simulated_state_manifest"])
    ).hexdigest()
    monkeypatch.setattr(
        a13,
        "_read_public_repository_file",
        lambda path, label, require_regular_mode: a13.canonical_json_bytes(
            forged
        ),
    )
    with pytest.raises(
        a13.LawError,
        match="Git-resolved C/S identity drift",
    ):
        a13._validate_amendment20_transition_receipt(forged)


def test__amendment20_mutations_run_only_after_inherited_116(monkeypatch):
    calls = []

    def inherited():
        calls.append("inherited")
        return a13.A19_EXPECTED_MUTATIONS

    monkeypatch.setattr(
        a13,
        "run_amendment19_member_law_mutation_tests",
        inherited,
    )
    monkeypatch.setattr(
        a13,
        "_validate_amendment20_r06_collection_binding",
        lambda: calls.append("r06") or {},
    )
    rejected = a13.run_amendment20_contract_mutation_tests()
    assert calls == ["inherited", "r06"]
    assert rejected == a13.A20_EXPECTED_MUTATIONS == A20_TEST_MUTATIONS
    assert (
        sum(row["count"] for row in a13.A20_INHERITED_MUTATION_CENSUSES) == 116
    )
    raw = a13.canonical_json_bytes(list(rejected))
    assert len(raw) == a13.A20_MUTATION_DOMAIN_BYTE_SIZE
    assert hashlib.sha256(raw).hexdigest() == (a13.A20_MUTATION_DOMAIN_SHA256)


def test__mutation_inventory__is_separate_and_exact(
    rejected_mutations,
    rejected_enforcement_mutations,
):
    assert rejected_mutations == a13.A13_EXPECTED_MUTATIONS
    assert (
        rejected_enforcement_mutations
        == a13.A13_ENFORCEMENT_EXPECTED_MUTATIONS
    )
    assert a13.REMOVED_PKI_MUTATIONS == (
        "dual_ratify_records_coherently_self_minted",
        "reviewer_registry_two_keys_one_actor_self_enrolled",
    )


@pytest.mark.parametrize("mutation", a13.A13_EXPECTED_MUTATIONS)
def test__mutation_inventory__rejects_each_named_forgery(
    rejected_mutations,
    mutation,
):
    assert mutation in rejected_mutations


@pytest.mark.parametrize("mutation", a13.A13_ENFORCEMENT_EXPECTED_MUTATIONS)
def test__enforcement_inventory__rejects_each_named_forgery(
    rejected_enforcement_mutations,
    mutation,
):
    assert mutation in rejected_enforcement_mutations


def test__document__preserves_revision15_as_exact_prefix():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    revision15 = a13._git(
        "show",
        f"{a13.A13_MERGED_RATIFICATION_COMMIT}:{a13.DESIGN_PATH}",
    )
    assert isinstance(revision15, bytes)
    assert len(revision15) == a13.REVISION15_BYTE_SIZE
    assert hashlib.sha256(revision15).hexdigest() == a13.REVISION15_SHA256
    assert a13._git_blob_oid(revision15) == a13.REVISION15_BLOB_OID
    assert raw[: a13.REVISION15_BYTE_SIZE] == revision15
    assert raw[a13.REVISION15_BYTE_SIZE :].startswith(a13.AMENDMENT14_BOUNDARY)


def test__document__preserves_revision17_as_exact_prefix():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    revision17 = a13._git(
        "show",
        f"{a13.A15_MERGED_RATIFICATION_COMMIT}:{a13.DESIGN_PATH}",
    )
    assert isinstance(revision17, bytes)
    assert len(revision17) == a13.REVISION17_BYTE_SIZE
    assert hashlib.sha256(revision17).hexdigest() == a13.REVISION17_SHA256
    assert a13._git_blob_oid(revision17) == a13.REVISION17_BLOB_OID
    assert raw[: a13.REVISION17_BYTE_SIZE] == revision17
    assert raw[a13.REVISION17_BYTE_SIZE :].startswith(a13.AMENDMENT16_BOUNDARY)


def test__document__preserves_revision19_as_exact_prefix():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    revision19 = raw[: a13.REVISION19_BYTE_SIZE]
    assert a13.REVISION19_BYTE_SIZE == 3_934_849
    assert a13.REVISION19_SHA256 == (
        "29055c5606a54587107498e8adcdbc8546f93caceabe89238975288db72e7fe1"
    )
    assert a13.REVISION19_BLOB_OID == (
        "84b31290ecd2d1001b6ea802b9a97a86260cdfda"
    )
    assert len(revision19) == a13.REVISION19_BYTE_SIZE
    assert hashlib.sha256(revision19).hexdigest() == a13.REVISION19_SHA256
    assert a13._git_blob_oid(revision19) == a13.REVISION19_BLOB_OID
    assert raw[a13.REVISION19_BYTE_SIZE :].startswith(a13.AMENDMENT18_BOUNDARY)
    assert raw.count(a13.AMENDMENT18_BOUNDARY) == 1


def test__document__preserves_revision20_and_exact_revision21_prefix():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    revision20 = raw[: a13.REVISION20_BYTE_SIZE]
    enacted_revision20 = a13._git("cat-file", "blob", a13.REVISION20_BLOB_OID)
    assert isinstance(enacted_revision20, bytes)
    assert revision20 == enacted_revision20
    assert a13.REVISION20_BYTE_SIZE == 3_964_278
    assert a13.REVISION20_SHA256 == (
        "631d3b2b8ecab1c29ec0595550a6d2b798f49ff96e74c722801d24c48ab111ec"
    )
    assert a13.REVISION20_BLOB_OID == (
        "016c0fff757b54da730ae0044216416cde2d2c33"
    )
    assert len(revision20) == a13.REVISION20_BYTE_SIZE
    assert hashlib.sha256(revision20).hexdigest() == a13.REVISION20_SHA256
    assert a13._git_blob_oid(revision20) == a13.REVISION20_BLOB_OID
    revision21 = raw[: a13.REVISION21_BYTE_SIZE]
    suffix = revision21[a13.REVISION20_BYTE_SIZE :]
    assert suffix.startswith(a13.AMENDMENT19_BOUNDARY)
    assert raw.count(a13.AMENDMENT19_BOUNDARY) == 1
    assert suffix.endswith(b"\n")
    assert len(revision21) == 4_025_587 == a13.REVISION21_BYTE_SIZE
    assert hashlib.sha256(revision21).hexdigest() == a13.REVISION21_SHA256
    assert a13._git_blob_oid(revision21) == a13.REVISION21_BLOB_OID
    assert raw[a13.REVISION21_BYTE_SIZE :].startswith(a13.AMENDMENT20_BOUNDARY)
    assert raw.count(a13.AMENDMENT20_BOUNDARY) == 1
    assert a13._terminal_design_amendment(raw) == 20
    projection = a13._parse_amendment19_projection(revision21)
    assert projection["section_semantic_sha256"] == (
        a13.A19_SECTION_SEMANTIC_SHA256
    )


def test__document__retains_nested_revision14_and_a13_boundaries():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    revision14 = a13._git(
        "show", f"{a13.RATIFICATION_COMMIT}:{a13.DESIGN_PATH}"
    )
    assert isinstance(revision14, bytes)
    assert len(revision14) == a13.DESIGN_BYTE_SIZE
    assert hashlib.sha256(revision14).hexdigest() == a13.DESIGN_SHA256
    assert raw[: a13.DESIGN_BYTE_SIZE] == revision14
    assert raw[a13.DESIGN_BYTE_SIZE :].startswith(a13.AMENDMENT13_BOUNDARY)
