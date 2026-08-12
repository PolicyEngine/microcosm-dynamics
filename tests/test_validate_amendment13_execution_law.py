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
    "/Users/maxghenis/PolicyEngine/social-security-model/.venv/bin/python "
    "-m pytest -q tests/test_validate_amendment13_execution_law.py"
)
A17_FULL_PINNED_BATTERY_COLLECTED = 76


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
    return context


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


def _assert_executed_transition_evidence(evidence):
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
    assert manifest["terminal_revision"] == revision
    expected = _expected_terminal_operativity_domain(revision)
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
    pins = a13._parse_active_implementation_pins(
        (ROOT / a13.DESIGN_PATH).read_bytes()
    )
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
    assert battery["exact_command"] == A17_FULL_PINNED_BATTERY_COMMAND
    assert battery["collected"] == A17_FULL_PINNED_BATTERY_COLLECTED
    assert battery["passed"] == A17_FULL_PINNED_BATTERY_COLLECTED
    for outcome in (
        "failed",
        "skipped",
        "deselected",
        "xfailed",
        "xpassed",
    ):
        assert battery[outcome] == 0
    assert battery["simulated_state_identity_sha256"] == state_identity


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

    pins = a13._parse_active_implementation_pins(
        (ROOT / a13.DESIGN_PATH).read_bytes()
    )
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

    monkeypatch.setattr(
        a13,
        "_public_registry_ratification_context",
        lambda: context,
    )

    def validate(amendment_number, selected_context):
        assert selected_context == context
        observed.append(amendment_number)
        return {"amendment_number": amendment_number}

    monkeypatch.setattr(a13, "_validate_public_ratification_closure", validate)
    assert a13.validate_ratification_operativity() == {
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

    monkeypatch.setattr(
        a13,
        "_public_registry_ratification_context",
        lambda: context,
    )
    monkeypatch.setattr(a13, "_validate_public_ratification_closure", validate)
    public_closures = (
        _assert_public_oracle_reaches_implementation_pin_verifier(
            monkeypatch,
            (13, 14, 15, 16),
        )
    )
    assert tuple(public_closures) == (13, 14, 15, 16)


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

    expected_domain = _expected_terminal_operativity_domain(
        registry.DESIGN_REVISION
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


def test__document__semantic_projection_covers_amendments14_through17():
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
    if len(raw) > a13.REVISION18_BYTE_SIZE:
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


def test__document__amendment16_and17_pin_values_are_normalized_only():
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
    amendment17 = (ROOT / a13.DESIGN_PATH).read_bytes()
    amendment18 = amendment17 + (
        b"\n## 32. AMENDMENT SECTION \xe2\x80\x94 Amendment 18: "
        b"synthetic successor\n\nProspective successor.\n"
    )
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
            match=("Amendment-14/15/16/17 document semantic projection drift"),
        ):
            a13._validate_document_semantic_projection(candidate, {})
    for amendment_number, successor in ((17, amendment17), (18, amendment18)):
        a13._validate_non_a13_ratification_design(
            successor,
            amendment_number,
        )
        for original, forged in forgeries:
            assert successor.count(original) == 1
            candidate = successor.replace(original, forged, 1)
            with pytest.raises(
                a13.LawError,
                match=(
                    "Amendment-17 ratification design semantic projection "
                    "drift"
                ),
            ):
                a13._validate_non_a13_ratification_design(
                    candidate,
                    amendment_number,
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
