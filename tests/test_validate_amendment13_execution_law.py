"""Tests for Amendment 13's prospective tier-2 execution law."""

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


def _synthetic_governing_identity_and_records():
    commit = "1" * 40
    candidate_head = "2" * 40
    document_sha256 = "3" * 64
    records = {}
    attestations = []
    for index in (1, 2):
        name = f"amendment-13-ratify-{index}.md"
        raw = (
            "# RATIFY\n"
            f"record_name: {name}\n"
            f"attested_candidate_head: {candidate_head}\n"
            f"attested_document_path: {a13.DESIGN_PATH}\n"
            "attested_document_byte_size: 4000000\n"
            f"attested_document_sha256: {document_sha256}\n"
        ).encode()
        records[name] = raw
        attestations.append(
            {
                "record_name": name,
                "raw_byte_size": len(raw),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "verdict_token": "RATIFY",
                "attested_candidate_head": candidate_head,
                "attested_document_byte_size": 4_000_000,
                "attested_document_sha256": document_sha256,
            }
        )
    identity = {
        "schema_version": a13.GOVERNING_A13_IDENTITY_SCHEMA_VERSION,
        "status": a13.GOVERNING_A13_IDENTITY_STATUS,
        "ratification_commit": commit,
        "ratification_parents": ["4" * 40],
        "ratification_commit_changed_paths": [a13.DESIGN_PATH],
        "document_path": a13.DESIGN_PATH,
        "document_mode": a13.DESIGN_MODE,
        "document_blob_oid": "5" * 40,
        "document_byte_size": 4_000_000,
        "document_sha256": document_sha256,
        "dual_ratify_attestations": attestations,
    }
    return identity, records


def test__draft__emits_neither_authority_nor_certification(execution_law):
    assert execution_law["status"] == (
        "PROSPECTIVE_NONAUTHORITY_UNRATIFIED_DRAFT"
    )
    assert execution_law["authority_emitted"] is False
    assert execution_law["certification_emitted"] is False
    assert (
        execution_law["governing_amendment13_ratification_identity"]
        == a13.GOVERNING_A13_CANDIDATE_IDENTITY
    )
    assert (
        execution_law["governing_amendment13_identity_schema_version"]
        == a13.GOVERNING_A13_IDENTITY_SCHEMA_VERSION
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
    assert Counter(
        row["predecessor_status_mapping"]["status_family"] for row in rows
    ) == Counter(
        {
            "modern_handoff_status": 13,
            "legacy_resolution_status": 14,
            "document_036_special_resolution_status": 1,
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
        assert payload["terminal_status"] == a13.INCOMPLETE_FRAGMENT_STATUS
        assert payload["continuation_citation"] is None
        assert payload["alias_admitted"] is False
        citation = payload["disclosed_incomplete_fragment_citation"]
        assert citation["utf8_byte_end"] > citation["utf8_byte_start"]
        assert hashlib.sha256(
            citation["matched_text"].encode()
        ).hexdigest() == (citation["matched_utf8_sha256"])


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
        assert payload["transformation_rule"] == (
            "replace_only_node_domain_component_slot_with_aggregate"
        )
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
        match="document-036 transformation is not the sole determinate field change",
    ):
        a13.validate_execution_law(candidate, verify_git=False)


def test__governing_ratification__requires_raw_dual_records():
    identity, records = _synthetic_governing_identity_and_records()
    a13._validate_governing_amendment13_ratification_identity(
        identity, records, verify_git=False
    )
    forged_records = dict(records)
    forged_records[next(iter(records))] += b"forged\n"
    with pytest.raises(
        a13.LawError,
        match="RATIFY raw bytes do not attest identity",
    ):
        a13._validate_governing_amendment13_ratification_identity(
            identity, forged_records, verify_git=False
        )
    forged_identity = copy.deepcopy(identity)
    forged_identity["dual_ratify_attestations"][0][
        "record_name"
    ] = "injected\nrecord.md"
    with pytest.raises(
        a13.LawError,
        match="governing Amendment-13 RATIFY attestation drift",
    ):
        a13._validate_governing_amendment13_ratification_identity(
            forged_identity,
            records,
            verify_git=False,
        )
    reversed_identity = copy.deepcopy(identity)
    reversed_identity["dual_ratify_attestations"].reverse()
    with pytest.raises(
        a13.LawError,
        match="not in record-name byte order",
    ):
        a13._validate_governing_amendment13_ratification_identity(
            reversed_identity,
            records,
            verify_git=False,
        )


def test__governing_ratification__candidate_head_must_be_commit_object():
    tree_object = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    with pytest.raises(
        a13.LawError,
        match="attested candidate HEAD is not an exact commit object",
    ):
        a13._require_exact_commit_object(
            tree_object,
            "governing Amendment-13 attested candidate HEAD",
        )


def test__ratification_bound_template__replaces_placeholder_everywhere(
    execution_law,
):
    identity, records = _synthetic_governing_identity_and_records()
    template = a13._build_ratification_bound_execution_template_for_test(
        identity,
        records,
    )
    assert template["status"] == a13.RATIFICATION_BOUND_TEMPLATE_STATUS
    assert template["authority_emitted"] is False
    assert template["certification_emitted"] is False
    assert template["governing_amendment13_ratification_identity"] == identity
    assert all(
        overlay["governing_amendment13_ratification_identity"] == identity
        and overlay["overlay_identity_preimage"][-2] == identity
        for overlay in template["repair_overlay_rows"]
    )
    assert all(
        seal["governing_amendment13_ratification_identity"] == identity
        and seal["successor_era_seal_identity_preimage"][-1] == identity
        for seal in template["successor_era_seal_rows"]
    )
    assert (
        b"UNAVAILABLE_BEFORE_AMENDMENT_13_RATIFICATION"
        not in a13.canonical_json_bytes(template)
    )
    assert (
        template["integrity"]["overlay_domain_sha256"]
        != execution_law["integrity"]["overlay_domain_sha256"]
    )


def test__ratification_bound_template__public_validator_cannot_bypass_git():
    identity, records = _synthetic_governing_identity_and_records()
    template = a13._build_ratification_bound_execution_template_for_test(
        identity,
        records,
    )
    with pytest.raises(
        a13.LawError,
        match="ratification-bound validation may not disable Git verification",
    ):
        a13.validate_execution_law(
            template,
            verify_git=False,
            governing_attestation_record_bytes=records,
        )


def test__ratification_bound_template__rejects_coherently_repinned_forgery():
    identity, records = _synthetic_governing_identity_and_records()
    template = a13._build_ratification_bound_execution_template_for_test(
        identity,
        records,
    )
    row = template["semantically_incompatible_local_proof_successor_rows"][0]
    old_successor_id = row["successor_row_id"]
    row["successor_payload"][
        "terminal_reason_code"
    ] = "forged_but_coherently_repinned_reason"
    a13._repin_successor(row)
    new_successor_id = row["successor_row_id"]
    edge = next(
        edge
        for edge in template["predecessor_supersession_rows"]
        if edge["successor_row_id"] == old_successor_id
    )
    old_supersession_id = edge["supersession_row_id"]
    edge["successor_row_id"] = row["successor_row_id"]
    edge["supersession_identity_preimage"][5] = row["successor_row_id"]
    edge["supersession_row_id"] = a13._content_id(
        "a13-supersession", edge["supersession_identity_preimage"]
    )
    new_supersession_id = edge["supersession_row_id"]

    for overlay in template["repair_overlay_rows"]:
        successors = a13._all_overlay_successors(overlay)
        edges = overlay["predecessor_supersession_rows"]
        overlay["integrity"] = {
            "successor_count": len(successors),
            "successor_domain_sha256": a13._domain_sha(successors),
            "supersession_count": len(edges),
            "supersession_domain_sha256": a13._domain_sha(edges),
        }

    for era in template["successor_era_seal_rows"]:
        era["successor_row_ids"] = [
            new_successor_id if value == old_successor_id else value
            for value in era["successor_row_ids"]
        ]
        era["supersession_row_ids"] = [
            new_supersession_id if value == old_supersession_id else value
            for value in era["supersession_row_ids"]
        ]
        era["successor_era_seal_identity_preimage"][5] = era[
            "successor_row_ids"
        ]
        era["successor_era_seal_identity_preimage"][6] = era[
            "supersession_row_ids"
        ]
        era["successor_era_seal_id"] = a13._content_id(
            "a13-successor-era-seal",
            era["successor_era_seal_identity_preimage"],
        )

    template["integrity"]["successor_domain_sha256"] = a13._domain_sha(
        [
            *template["semantically_incompatible_local_proof_successor_rows"],
            *template["incomplete_fragment_terminal_successor_rows"],
            *template["composed_fragment_successor_rows"],
            *template["doc036_aggregate_domain_successor_rows"],
        ]
    )
    template["integrity"]["supersession_domain_sha256"] = a13._domain_sha(
        template["predecessor_supersession_rows"]
    )
    template["integrity"]["overlay_domain_sha256"] = a13._domain_sha(
        template["repair_overlay_rows"]
    )
    template["integrity"]["successor_era_seal_domain_sha256"] = (
        a13._domain_sha(template["successor_era_seal_rows"])
    )

    with pytest.raises(
        a13.LawError,
        match="forged incompatible-proof terminal status or admission",
    ):
        a13._validate_execution_law(
            template,
            verify_git=False,
            governing_attestation_record_bytes=records,
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
    assert (
        continuation["new_fragment_predecessor_evidence_ids_disjoint"] is True
    )
    assert (
        continuation["new_fragment_instruction_occurrence_ids_disjoint"]
        is True
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


def test__mutation_inventory__is_separate_and_exact(
    rejected_mutations,
    rejected_enforcement_mutations,
):
    assert rejected_mutations == a13.A13_EXPECTED_MUTATIONS
    assert (
        rejected_enforcement_mutations
        == a13.A13_ENFORCEMENT_EXPECTED_MUTATIONS
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


def test__document__preserves_revision14_as_exact_prefix():
    raw = (ROOT / a13.DESIGN_PATH).read_bytes()
    ratified = subprocess.run(
        ["git", "show", f"{a13.RATIFICATION_COMMIT}:{a13.DESIGN_PATH}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert len(ratified) == a13.DESIGN_BYTE_SIZE
    assert hashlib.sha256(ratified).hexdigest() == a13.DESIGN_SHA256
    assert raw[: a13.DESIGN_BYTE_SIZE] == ratified
    assert raw[a13.DESIGN_BYTE_SIZE :].startswith(a13.AMENDMENT13_BOUNDARY)
