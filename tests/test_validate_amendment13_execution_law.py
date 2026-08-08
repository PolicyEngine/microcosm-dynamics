"""Tests for Amendment 13's Amendment-14-governed execution law."""

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
    context = {"revision": 16}
    observed = []

    monkeypatch.setattr(
        a13,
        "_public_registry_ratification_context",
        lambda: context,
    )

    def validate(amendment_number, selected_context):
        assert selected_context is context
        observed.append(amendment_number)
        return {"amendment_number": amendment_number}

    monkeypatch.setattr(a13, "_validate_public_ratification_closure", validate)
    assert a13.validate_ratification_operativity() == {
        13: {"amendment_number": 13},
        14: {"amendment_number": 14},
    }
    assert observed == [13, 14]


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


def test__document__semantic_projection_covers_amendment14():
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


def test__implementation__active_pins_are_blob_bound_without_commit():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    pins = a13._parse_amendment14_projection(raw)["implementation_pins"]
    assert set(pins) == {"mode", "files"}
    assert "commit" not in pins
    a13._verify_implementation_pins(pins)


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
