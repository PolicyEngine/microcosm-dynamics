"""Tests for the operative Amendment-13 tier-2 repair publisher."""

from __future__ import annotations

import copy
import functools
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_amendment13_tier2_repairs as publisher  # noqa: E402
import validate_amendment13_execution_law as a13  # noqa: E402


def _repin_certification(value):
    digest = publisher._certification_payload_sha256(value)
    value["artifact_id"] = publisher.CERTIFICATION_ARTIFACT_ID_PREFIX + digest
    value["integrity"] = {
        "canonicalization": (
            "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
        ),
        "payload_sha256": digest,
    }


@functools.cache
def _executed_mutation_outputs():
    """Return the four real runner outputs for fail-closed fault injection."""

    return publisher._execute_complete_mutation_names()


@functools.cache
def _executed_mutation_census():
    """Compose a census from the four real, fully executed runner outputs."""

    outputs = _executed_mutation_outputs()
    return publisher.run_complete_mutation_census(
        a12_runner=functools.partial(tuple, outputs[0]),
        a13_runner=functools.partial(tuple, outputs[1]),
        a14_runner=functools.partial(tuple, outputs[2]),
        a15_runner=functools.partial(tuple, outputs[3]),
    )


def _validate_fixture_contract(value):
    publisher._validate_tier2_certification_contract(
        value,
        executed_mutation_census=_executed_mutation_census(),
    )


def _raise_intended_mutation_error(binding):
    raise binding.expected_exception(binding.expected_message)


def _raise_mutation_error(exception, message):
    raise exception(message)


def _return_mutation_names(names):
    return names


def _intended_rejection_actions():
    return {
        binding.name: functools.partial(
            _raise_intended_mutation_error,
            binding,
        )
        for binding in publisher.A15_MUTATION_BINDINGS
    }


def _certification_fixture():
    member_sha = "1" * 64
    input_sha = "2" * 64
    value = {
        "artifact_id": "",
        "artifact_role": publisher.CERTIFICATION_ARTIFACT_ROLE,
        "gate_results": [
            {"gate_id": gate_id, "status": "pass"}
            for gate_id in publisher.CERTIFICATION_GATE_IDS
        ],
        "git_order_attestation": copy.deepcopy(
            publisher.CERTIFICATION_GIT_ATTESTATION
        ),
        "integrity": {},
        "lifecycle": copy.deepcopy(publisher.CERTIFICATION_LIFECYCLE),
        "mutation_census": copy.deepcopy(_executed_mutation_census()),
        "ratification_binding": {
            "amendment_number": 15,
            "closure_byte_size": 1_000,
            "closure_path": (
                "docs/analysis/amendment_15_ratification/closure_v1.json"
            ),
            "closure_raw_sha256": "3" * 64,
            "design_blob_oid": "4" * 40,
            "design_byte_size": 4_000_000,
            "design_path": "docs/design/covered_earnings_correction.md",
            "design_raw_sha256": "5" * 64,
            "design_revision": 17,
            "ratification_commit": "6" * 40,
            "ratification_commit_sole_parent": "7" * 40,
        },
        "reconstruction_rows": [
            {
                "implementation_blob_oid": "8" * 40,
                "implementation_byte_size": 10_000,
                "implementation_dependency_paths": [
                    publisher.CERTIFICATION_RECONSTRUCTION_PATHS[0]
                ],
                "implementation_dependency_policy": (
                    publisher.CERTIFICATION_RECONSTRUCTION_DEPENDENCY_POLICY
                ),
                "implementation_mode": "100644",
                "implementation_path": (
                    publisher.CERTIFICATION_RECONSTRUCTION_PATHS[0]
                ),
                "implementation_raw_sha256": "8" * 64,
                "member_canonical_byte_size": 123_456,
                "member_raw_sha256": member_sha,
                "reconstruction_id": (
                    publisher.CERTIFICATION_RECONSTRUCTION_IDS[0]
                ),
                "status": "pass_independent_source_reconstruction",
                "tier2_build_input_domain_sha256": input_sha,
            },
            {
                "implementation_blob_oid": "9" * 40,
                "implementation_byte_size": 11_000,
                "implementation_dependency_paths": [
                    publisher.CERTIFICATION_RECONSTRUCTION_PATHS[1]
                ],
                "implementation_dependency_policy": (
                    publisher.CERTIFICATION_RECONSTRUCTION_DEPENDENCY_POLICY
                ),
                "implementation_mode": "100644",
                "implementation_path": (
                    publisher.CERTIFICATION_RECONSTRUCTION_PATHS[1]
                ),
                "implementation_raw_sha256": "9" * 64,
                "member_canonical_byte_size": 123_456,
                "member_raw_sha256": member_sha,
                "reconstruction_id": (
                    publisher.CERTIFICATION_RECONSTRUCTION_IDS[1]
                ),
                "status": "pass_independent_source_reconstruction",
                "tier2_build_input_domain_sha256": input_sha,
            },
        ],
        "schema_version": publisher.CERTIFICATION_SCHEMA_VERSION,
        "source_build_identity": {
            **publisher.CERTIFICATION_SOURCE_COUNTS_AND_DOMAINS,
            "tier2_build_input_domain_sha256": input_sha,
        },
        "source_hierarchy_member_identity": {
            "authority_kind": "prospective_g17_c01_source_member_pre_q5",
            "canonical_byte_size": 123_456,
            "canonicalization": (
                "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
            ),
            "member_name": "hierarchy_annotation_authority",
            "raw_sha256": member_sha,
            "status": "pass",
        },
        "status": publisher.CERTIFICATION_STATUS,
    }
    _repin_certification(value)
    return value


@pytest.fixture(scope="module")
def publication():
    law, values = publisher.build_artifact_values()
    rendered = publisher.render_artifact_values(values)
    return law, values, rendered


def test__artifact_projection__has_exact_paths_and_deep_equal_rows(
    publication,
):
    law, values, rendered = publication
    assert len(values) == len(rendered) == 20
    assert {
        path for path in values if path.parent == publisher.OVERLAY_DIRECTORY
    } == {
        publisher.overlay_relative_path(position)
        for position in publisher.OVERLAY_POSITIONS
    }
    assert {
        path for path in values if path.parent == publisher.SEAL_DIRECTORY
    } == {publisher.seal_relative_path(position) for position in range(1, 7)}
    expected_rows = [
        *law["repair_overlay_rows"],
        *law["successor_era_seal_rows"],
    ]
    assert list(values.values()) == expected_rows
    for path, raw in rendered.items():
        assert raw == a13.canonical_json_bytes(values[path])
        assert a13._strict_canonical_json(raw, path.as_posix()) == values[path]


def test__artifact_projection__reconciles_exactly_46_repairs(publication):
    law, _, _ = publication
    publisher.validate_publication_law(law)
    assert law["integrity"]["repair_count"] == 28 + 8 + 2 + 8 == 46
    assert law["integrity"]["supersession_count"] == 46
    counts = {
        row["document_source_position"]: len(
            publisher._overlay_successors(row)
        )
        for row in law["repair_overlay_rows"]
    }
    assert counts == publisher.EXPECTED_REPAIR_COUNTS_BY_DOCUMENT


def test__artifact_projection__retains_empty_sixth_era_seal(publication):
    law, values, rendered = publication
    seal = law["successor_era_seal_rows"][-1]
    path = publisher.seal_relative_path(6)
    assert values[path] == seal
    assert a13._strict_canonical_json(rendered[path], path.as_posix()) == seal
    assert seal["era_order_position"] == 6
    assert seal["repair_overlay_ids"] == []
    assert seal["successor_row_ids"] == []
    assert seal["supersession_row_ids"] == []
    assert set(seal["repair_counts"].values()) == {0}
    assert seal["all_named_domains_present_even_when_empty"] is True


def test__artifact_validation__rejects_mutated_row(publication):
    _, values, rendered = publication
    actual = dict(rendered)
    path = publisher.overlay_relative_path(7)
    mutated = copy.deepcopy(values[path])
    mutated["authority_kind"] = "AUTHORITY"
    actual[path] = a13.canonical_json_bytes(mutated)
    with pytest.raises(
        publisher.PublicationError,
        match="differs from the operative reconstruction",
    ):
        publisher.validate_artifact_bundle(actual, values, artifacts="all")


def test__artifact_validation__rejects_dropped_overlay(publication):
    _, values, rendered = publication
    actual = dict(rendered)
    del actual[publisher.overlay_relative_path(10)]
    with pytest.raises(
        publisher.PublicationError,
        match="artifact path domain drift",
    ):
        publisher.validate_artifact_bundle(actual, values, artifacts="all")


def test__artifact_validation__rejects_reordered_seal_domain(publication):
    _, values, rendered = publication
    actual = dict(rendered)
    path = publisher.seal_relative_path(1)
    reordered = copy.deepcopy(values[path])
    reordered["successor_row_ids"].reverse()
    actual[path] = a13.canonical_json_bytes(reordered)
    with pytest.raises(
        publisher.PublicationError,
        match="differs from the operative reconstruction",
    ):
        publisher.validate_artifact_bundle(actual, values, artifacts="all")


def test__write_and_read__round_trip_without_wrapper(publication, tmp_path):
    _, values, rendered = publication
    actual = publisher.write_artifact_bundle(tmp_path, values, artifacts="all")
    assert actual == rendered
    reread = publisher.read_artifact_bundle(tmp_path, values, artifacts="all")
    publisher.validate_artifact_bundle(reread, values, artifacts="all")
    assert not list(tmp_path.glob("*.json"))
    assert len(list((tmp_path / publisher.OVERLAY_DIRECTORY).iterdir())) == 14
    assert len(list((tmp_path / publisher.SEAL_DIRECTORY).iterdir())) == 6


def test__first_add_relationships__accept_each_publication_stage(
    publication,
):
    law, _, _ = publication
    overlay_commits = {
        position: None for position in publisher.OVERLAY_POSITIONS
    }
    seal_commits = {position: None for position in range(1, 7)}
    era_position_by_id = {
        row["era_id"]: row["era_order_position"]
        for row in law["successor_era_seal_rows"]
    }
    overlay_era_positions = {
        row["document_source_position"]: era_position_by_id[
            row["predecessor_era_id"]
        ]
        for row in law["repair_overlay_rows"]
    }
    graph = {("ratification", "overlays"), ("overlays", "seals")}

    def ancestor(earlier, later):
        return (earlier, later) in graph

    assert (
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=overlay_commits,
            seal_commits=seal_commits,
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=ancestor,
        )
        == "prospective"
    )
    overlay_commits = dict.fromkeys(overlay_commits, "overlays")
    assert (
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=overlay_commits,
            seal_commits=seal_commits,
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=ancestor,
            required="overlays",
        )
        == "overlays_committed"
    )
    seal_commits = dict.fromkeys(seal_commits, "seals")
    assert (
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=overlay_commits,
            seal_commits=seal_commits,
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=ancestor,
            required="all",
        )
        == "seals_committed"
    )


def test__first_add_relationships__reject_drop_and_same_commit(publication):
    law, _, _ = publication
    era_position_by_id = {
        row["era_id"]: row["era_order_position"]
        for row in law["successor_era_seal_rows"]
    }
    overlay_era_positions = {
        row["document_source_position"]: era_position_by_id[
            row["predecessor_era_id"]
        ]
        for row in law["repair_overlay_rows"]
    }
    complete_overlays = dict.fromkeys(publisher.OVERLAY_POSITIONS, "batch")
    complete_seals = dict.fromkeys(range(1, 7), "seal-batch")
    dropped = dict(complete_overlays)
    dropped[7] = None
    with pytest.raises(
        publisher.PublicationError,
        match="not one complete first-add batch",
    ):
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=dropped,
            seal_commits=dict.fromkeys(range(1, 7)),
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=lambda earlier, later: True,
        )
    with pytest.raises(
        publisher.PublicationError,
        match="not a strict ancestor",
    ):
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=complete_overlays,
            seal_commits=complete_seals,
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=lambda earlier, later: earlier != later
            and (earlier, later) == ("ratification", "batch"),
        )


def test__live_git_order__validates_before_and_after_publication(publication):
    law, values, _ = publication
    state = publisher.validate_git_publication_order(law, values)
    assert state["status"] in {
        "prospective",
        "overlays_committed",
        "seals_committed",
    }
    if state["status"] == "prospective":
        required = "overlays"
        message = "overlay batch is not committed"
    elif state["status"] == "overlays_committed":
        required = "all"
        message = "seal batch is not committed"
    else:
        required = None
        message = None
    if required is None:
        assert (
            publisher.validate_git_publication_order(
                law, values, required="all"
            )["status"]
            == "seals_committed"
        )
    else:
        with pytest.raises(publisher.PublicationError, match=message):
            publisher.validate_git_publication_order(
                law, values, required=required
            )


def test__ordered_history__authenticates_exact_collapsed_publication():
    attestation = publisher.validate_ordered_ceremony_attestation()
    assert attestation == {
        "archive_ref": publisher.ORDERED_CEREMONY_LOCAL_REF,
        "archive_tip_commit": publisher.ORDERED_CEREMONY_EVIDENCE_COMMIT,
        "tree_oid": publisher.ORDERED_CEREMONY_TREE_OID,
        "squash_commit": publisher.TIER2_SQUASH_COMMIT,
        "stage_commits": {
            "receipt": publisher.ORDERED_CEREMONY_RECEIPT_COMMIT,
            "overlays": publisher.ORDERED_CEREMONY_OVERLAY_COMMIT,
            "seals": publisher.ORDERED_CEREMONY_SEAL_COMMIT,
            "evidence": publisher.ORDERED_CEREMONY_EVIDENCE_COMMIT,
        },
    }


def test__ordered_history_mutation__rejects_identity_forgery(monkeypatch):
    candidate = copy.deepcopy(publisher.ORDERED_CEREMONY_ATTESTATION)
    candidate["stages"][1]["commit"] = publisher.TIER2_SQUASH_COMMIT
    with pytest.raises(
        publisher.PublicationError, match="overlays commit identity drift"
    ):
        publisher._validate_ordered_ceremony_attestation(
            repo_root=ROOT, attestation=candidate
        )

    candidate = copy.deepcopy(publisher.ORDERED_CEREMONY_ATTESTATION)
    candidate["stages"][1]["changed_paths"] = candidate["stages"][1][
        "changed_paths"
    ][:-1]
    with pytest.raises(
        publisher.PublicationError, match="changed-path attestation drift"
    ):
        publisher._validate_ordered_ceremony_attestation(
            repo_root=ROOT, attestation=candidate
        )

    original = publisher._run_git

    def wrong_tip(repo_root, *arguments):
        if arguments[:3] == ("show-ref", "--verify", "--hash"):
            return subprocess.CompletedProcess(
                arguments,
                0,
                stdout=(publisher.TIER2_SQUASH_COMMIT + "\n").encode(),
                stderr=b"",
            )
        return original(repo_root, *arguments)

    monkeypatch.setattr(publisher, "_run_git", wrong_tip)
    with pytest.raises(
        publisher.PublicationError, match="resolves to the wrong tip"
    ):
        publisher.validate_ordered_ceremony_attestation()


def test__ordered_history_mutation__rejects_wrong_order(monkeypatch):
    original = publisher._is_strict_ancestor

    def wrong_order(repo_root, ancestor, descendant):
        if (
            ancestor == publisher.ORDERED_CEREMONY_OVERLAY_COMMIT
            and descendant == publisher.ORDERED_CEREMONY_SEAL_COMMIT
        ):
            return False
        return original(repo_root, ancestor, descendant)

    monkeypatch.setattr(publisher, "_is_strict_ancestor", wrong_order)
    with pytest.raises(
        publisher.PublicationError, match="strict-ancestor chain drift"
    ):
        publisher.validate_ordered_ceremony_attestation()


def test__ordered_history_mutation__rejects_tree_mismatch(monkeypatch):
    candidate = copy.deepcopy(publisher.ORDERED_CEREMONY_ATTESTATION)
    candidate["tree_oid"] = "0" * 40
    with pytest.raises(
        publisher.PublicationError, match="tree identity drift"
    ):
        publisher._validate_ordered_ceremony_attestation(
            repo_root=ROOT, attestation=candidate
        )

    original = publisher._commit_tree

    def wrong_actual_tree(repo_root, commit):
        if commit == publisher.ORDERED_CEREMONY_EVIDENCE_COMMIT:
            return "f" * 40
        return original(repo_root, commit)

    monkeypatch.setattr(publisher, "_commit_tree", wrong_actual_tree)
    with pytest.raises(
        publisher.PublicationError, match="evidence actual tree drift"
    ):
        publisher.validate_ordered_ceremony_attestation()

    candidate = copy.deepcopy(publisher.ORDERED_CEREMONY_ATTESTATION)
    candidate["stages"][1]["tree_oid"] = "0" * 40
    with pytest.raises(
        publisher.PublicationError, match="overlays tree identity drift"
    ):
        publisher._validate_ordered_ceremony_attestation(
            repo_root=ROOT, attestation=candidate
        )


def test__ordered_history_mutation__rejects_absent_archive_ref(tmp_path):
    with pytest.raises(
        publisher.PublicationError, match="archive ref is absent"
    ):
        publisher.validate_ordered_ceremony_attestation(repo_root=tmp_path)


def test__ordered_history_mutation__rejects_artifact_mode_drift(monkeypatch):
    original = publisher._git_output
    selected = publisher.RECEIPT_PATH.as_posix()

    def wrong_mode(repo_root, *arguments):
        if arguments == ("ls-tree", "HEAD", "--", selected):
            actual = original(repo_root, *arguments)
            assert actual.startswith(b"100644 blob ")
            return actual.replace(b"100644 blob ", b"100755 blob ", 1)
        return original(repo_root, *arguments)

    monkeypatch.setattr(publisher, "_git_output", wrong_mode)
    with pytest.raises(
        publisher.PublicationError, match="artifact mode/blob drift"
    ):
        publisher.validate_ordered_ceremony_attestation()


def test__ordered_history_mutation__rejects_exception_reuse():
    attestation = {
        "stage_commits": {
            "receipt": publisher.ORDERED_CEREMONY_RECEIPT_COMMIT,
            "overlays": publisher.ORDERED_CEREMONY_OVERLAY_COMMIT,
            "seals": publisher.ORDERED_CEREMONY_SEAL_COMMIT,
            "evidence": publisher.ORDERED_CEREMONY_EVIDENCE_COMMIT,
        }
    }
    with pytest.raises(publisher.PublicationError, match="cannot reuse"):
        publisher._attested_order_commit_for_squashed_first_add(
            Path("scripts/build_amendment13_tier2_repairs.py"),
            publisher.TIER2_SQUASH_COMMIT,
            attestation,
        )
    with pytest.raises(
        publisher.PublicationError, match="exception commit drift"
    ):
        publisher._attested_order_commit_for_squashed_first_add(
            publisher.RECEIPT_PATH,
            publisher.ORDERED_CEREMONY_RECEIPT_COMMIT,
            attestation,
        )


def test__first_add_rule__still_rejects_two_live_adds(monkeypatch):
    def two_adds(repo_root, *arguments):
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout=(
                publisher.TIER2_SQUASH_COMMIT
                + "\n"
                + publisher.ORDERED_CEREMONY_OVERLAY_COMMIT
                + "\n"
            ).encode(),
            stderr=b"",
        )

    monkeypatch.setattr(publisher, "_run_git", two_adds)
    with pytest.raises(
        publisher.PublicationError, match="more than one first-add commit"
    ):
        publisher._first_add_commits(
            ROOT,
            publisher.ORDERED_OVERLAY_PATHS[0],
        )


def test__certification_contract__accepts_minimal_total_fixture():
    assert publisher.CERTIFICATION_BUILDER_FUNCTION == "build_certification"
    assert publisher.CERTIFICATION_RECONSTRUCTION_FUNCTION == (
        "reconstruct_source_hierarchy_member"
    )
    assert publisher.CERTIFICATION_VALIDATOR_FUNCTION == (
        "validate_committed_certification"
    )
    publisher.validate_tier2_certification_contract(_certification_fixture())


def test__certification_contract__does_not_trust_serialized_census(
    monkeypatch,
):
    candidate = _certification_fixture()
    executed = copy.deepcopy(_executed_mutation_census())
    executed["rejected_count"] = 99
    calls = []

    def forged_execution():
        calls.append(True)
        return executed

    monkeypatch.setattr(
        publisher,
        "run_complete_mutation_census",
        forged_execution,
    )
    with pytest.raises(
        publisher.PublicationError,
        match="mutation census drift",
    ):
        publisher.validate_tier2_certification_contract(candidate)
    assert calls == [True]


def test__certification_contract__future_paths_remain_uninstantiated():
    future_paths = (
        publisher.CERTIFICATION_PATH,
        Path(publisher.CERTIFICATION_BUILDER_PATH),
        Path(publisher.CERTIFICATION_VALIDATOR_PATH),
    )
    for relative_path in future_paths:
        assert not (ROOT / relative_path).exists()
        assert publisher._first_add_commits(ROOT, relative_path) == ()
        result = publisher._run_git(
            ROOT, "cat-file", "-e", f"HEAD:{relative_path.as_posix()}"
        )
        assert result.returncode != 0


def test__certification_mutation__rejects_schema_keyset_drift():
    candidates = []
    missing = _certification_fixture()
    missing.pop("status")
    _repin_certification(missing)
    candidates.append(missing)
    extra = _certification_fixture()
    extra["extra"] = None
    _repin_certification(extra)
    candidates.append(extra)
    nested = _certification_fixture()
    nested["reconstruction_rows"][0].pop("implementation_mode")
    _repin_certification(nested)
    candidates.append(nested)
    nested_census = _certification_fixture()
    nested_census["mutation_census"]["components"][0].pop("status")
    _repin_certification(nested_census)
    candidates.append(nested_census)
    for candidate in candidates:
        with pytest.raises(publisher.PublicationError, match="keyset drift"):
            _validate_fixture_contract(candidate)


@pytest.mark.parametrize(
    ("domain", "key"),
    (
        ("ratification_binding", "amendment_number"),
        ("ratification_binding", "design_revision"),
        ("source_build_identity", "questionnaire_document_count"),
        ("source_build_identity", "source_document_count"),
        ("mutation_census", "expected_count"),
        ("mutation_census", "rejected_count"),
        ("mutation_component", "expected_count"),
        ("mutation_component", "rejected_count"),
        ("reconstruction_row", "member_canonical_byte_size"),
    ),
)
def test__certification_mutation__rejects_numeric_type_drift(domain, key):
    candidate = _certification_fixture()
    if domain == "reconstruction_row":
        target = candidate["reconstruction_rows"][0]
    elif domain == "mutation_component":
        target = candidate["mutation_census"]["components"][0]
    else:
        target = candidate[domain]
    target[key] = float(target[key])
    _repin_certification(candidate)
    with pytest.raises(publisher.PublicationError):
        _validate_fixture_contract(candidate)


def test__certification_mutation__rejects_reconstruction_disagreement():
    candidate = _certification_fixture()
    candidate["reconstruction_rows"][1]["member_raw_sha256"] = "a" * 64
    _repin_certification(candidate)
    with pytest.raises(
        publisher.PublicationError, match="reconstruction disagreement"
    ):
        _validate_fixture_contract(candidate)


def test__certification_mutation__rejects_reused_implementation():
    candidate = _certification_fixture()
    left, right = candidate["reconstruction_rows"]
    right["implementation_blob_oid"] = left["implementation_blob_oid"]
    right["implementation_raw_sha256"] = left["implementation_raw_sha256"]
    _repin_certification(candidate)
    with pytest.raises(publisher.PublicationError, match="not distinct"):
        _validate_fixture_contract(candidate)

    candidate = _certification_fixture()
    candidate["reconstruction_rows"][1]["implementation_dependency_paths"] = [
        publisher.CERTIFICATION_VALIDATOR_PATH,
        publisher.CERTIFICATION_BUILDER_PATH,
    ]
    _repin_certification(candidate)
    with pytest.raises(
        publisher.PublicationError, match="implementation drift"
    ):
        _validate_fixture_contract(candidate)


def test__certification_mutation__rejects_forbidden_emission():
    candidates = []
    for key, forged_value in (
        ("authority_emitted", True),
        ("authority_emitted", 0),
        ("nonauthority", 1),
    ):
        candidate = _certification_fixture()
        candidate["lifecycle"][key] = forged_value
        _repin_certification(candidate)
        candidates.append(candidate)
    for candidate in candidates:
        with pytest.raises(
            publisher.PublicationError, match="forbidden emission"
        ):
            _validate_fixture_contract(candidate)


def test__certification_mutation__rejects_raw_byte_attestation_forgery():
    candidate = _certification_fixture()
    candidate["artifact_id"] = (
        publisher.CERTIFICATION_ARTIFACT_ID_PREFIX + "f" * 64
    )
    with pytest.raises(
        publisher.PublicationError, match="raw-byte payload attestation"
    ):
        _validate_fixture_contract(candidate)


def test__merge_mode__enforces_topology_and_blob_bound_matrix():
    publisher.validate_ceremony_merge_mode(
        ["strict_or_equal_ancestry_order"],
        "no_fast_forward_merge_commit",
    )
    publisher.validate_ceremony_merge_mode(
        ["path_mode_blob_byte_hash"], "squash"
    )
    publisher.validate_ceremony_merge_mode(
        ["path_mode_blob_byte_hash", "resulting_tree_identity"], "squash"
    )
    publisher.validate_ceremony_merge_mode(
        ["first_or_last_add_identity", "path_mode_blob_byte_hash"],
        "no_fast_forward_merge_commit",
    )
    for mode in ("squash", "rebase", "fast_forward"):
        with pytest.raises(publisher.PublicationError):
            publisher.validate_ceremony_merge_mode(
                ["first_or_last_add_identity"], mode
            )
    with pytest.raises(publisher.PublicationError, match="empty"):
        publisher.validate_ceremony_merge_mode([], "squash")
    with pytest.raises(publisher.PublicationError, match="unknown"):
        publisher.validate_ceremony_merge_mode(
            ["unclassified_requirement"], "squash"
        )
    with pytest.raises(publisher.PublicationError, match="order drift"):
        publisher.validate_ceremony_merge_mode(
            ["resulting_tree_identity", "path_mode_blob_byte_hash"],
            "squash",
        )
    with pytest.raises(publisher.PublicationError, match="requires"):
        publisher.validate_ceremony_merge_mode(
            ["first_or_last_add_identity", "path_mode_blob_byte_hash"],
            "squash",
        )


def test__amendment15_mutation_inventory__is_exact_and_disjoint():
    expected_bindings = (
        (
            "ordered_history_attestation_identity_forged",
            "ordered_ceremony_stage_identity",
            publisher.PublicationError,
            "overlays commit identity drift",
        ),
        (
            "ordered_history_attestation_order_forged",
            "ordered_ceremony_strict_ancestor_chain",
            publisher.PublicationError,
            "strict-ancestor chain drift",
        ),
        (
            "ordered_history_attestation_tree_identity_forged",
            "ordered_ceremony_tree_identity",
            publisher.PublicationError,
            "tree identity drift",
        ),
        (
            "ordered_history_archive_ref_absent_or_unfetchable",
            "ordered_ceremony_archive_ref",
            publisher.PublicationError,
            "archive ref is absent or was not fetched",
        ),
        (
            "ordered_history_first_add_exception_reused",
            "ordered_ceremony_first_add_exception_scope",
            publisher.PublicationError,
            "cannot reuse the tier-2 squash exception",
        ),
        (
            "tier2_certification_schema_keyset_drift",
            "tier2_certification_exact_schema",
            publisher.PublicationError,
            "keyset drift",
        ),
        (
            "tier2_certification_reconstruction_disagreement",
            "tier2_certification_independent_reconstruction",
            publisher.PublicationError,
            "reconstruction disagreement",
        ),
        (
            "tier2_certification_referee_implementation_reused",
            "tier2_certification_distinct_referees",
            publisher.PublicationError,
            "not distinct",
        ),
        (
            "tier2_certification_forbidden_emission_forged",
            "tier2_certification_lifecycle_stop",
            publisher.PublicationError,
            "forbidden emission or lifecycle drift",
        ),
        (
            "tier2_certification_raw_byte_attestation_forged",
            "tier2_certification_payload_identity",
            publisher.PublicationError,
            "raw-byte payload attestation drift",
        ),
        (
            "ceremony_topology_bound_squash_selected",
            "ceremony_merge_mode_topology_classifier",
            publisher.PublicationError,
            "requires a no-fast-forward merge commit",
        ),
    )
    assert tuple(publisher.A15_MUTATION_BINDINGS) == expected_bindings
    assert publisher.A15_EXPECTED_MUTATIONS == tuple(
        row[0] for row in expected_bindings
    )
    assert len(set(publisher.A15_EXPECTED_MUTATIONS)) == len(expected_bindings)
    assert publisher.A15_MUTATION_DOMAIN_SHA256 == (
        "285f4f349d27099b64053f88f5292890392fd547643b083410c30f0c5b93b1c8"
    )
    mutation_digest = hashlib.sha256(
        a13.canonical_json_bytes(list(publisher.A15_EXPECTED_MUTATIONS))
    ).hexdigest()
    assert mutation_digest == publisher.A15_MUTATION_DOMAIN_SHA256
    path_digest = hashlib.sha256(
        a13.canonical_json_bytes(
            sorted(
                path.as_posix()
                for path in publisher.ORDERED_ARTIFACT_COMMIT_BY_PATH
            )
        )
    ).hexdigest()
    assert len(publisher.ORDERED_ARTIFACT_COMMIT_BY_PATH) == 22
    assert path_digest == publisher.ORDERED_ARTIFACT_PATH_DOMAIN_SHA256


def test__amendment15_named_runner__executes_all_bound_attacks():
    assert (
        publisher.run_amendment15_mutation_tests()
        == publisher.A15_EXPECTED_MUTATIONS
    )


def test__amendment15_named_runner__accepts_only_exact_action_domain():
    actions = _intended_rejection_actions()
    assert (
        publisher.run_amendment15_mutation_tests(actions)
        == publisher.A15_EXPECTED_MUTATIONS
    )

    missing = dict(tuple(actions.items())[1:])
    extra = {**actions, "unexpected_mutation": next(iter(actions.values()))}
    reordered = dict(reversed(tuple(actions.items())))
    for candidate in (missing, extra, reordered):
        with pytest.raises(publisher.PublicationError):
            publisher.run_amendment15_mutation_tests(candidate)


@pytest.mark.parametrize(
    "fault",
    ("non_rejection", "wrong_exception", "wrong_message", "wrong_gate"),
)
def test__amendment15_named_runner__fails_closed_on_unintended_result(fault):
    actions = _intended_rejection_actions()
    binding = publisher.A15_MUTATION_BINDINGS[0]

    if fault == "non_rejection":
        action = functools.partial(_return_mutation_names, None)
    elif fault == "wrong_exception":
        action = functools.partial(
            _raise_mutation_error,
            ValueError,
            binding.expected_message,
        )
    elif fault == "wrong_message":
        action = functools.partial(
            _raise_mutation_error,
            binding.expected_exception,
            "unintended rejection message",
        )
    else:
        wrong_gate = publisher.A15_MUTATION_BINDINGS[1]
        action = functools.partial(_raise_intended_mutation_error, wrong_gate)

    actions[binding.name] = action
    with pytest.raises(publisher.PublicationError):
        publisher.run_amendment15_mutation_tests(actions)


def test__complete_mutation_census__executes_and_binds_all_100_names():
    a12_names, a13_names, a14_names, a15_names = _executed_mutation_outputs()
    assert tuple(map(len, (a12_names, a13_names, a14_names, a15_names))) == (
        71,
        7,
        11,
        11,
    )
    assert a13_names == a13.A13_EXPECTED_MUTATIONS
    assert a14_names == a13.A13_ENFORCEMENT_EXPECTED_MUTATIONS
    assert a15_names == publisher.A15_EXPECTED_MUTATIONS

    complete_names = (*a12_names, *a13_names, *a14_names, *a15_names)
    assert len(complete_names) == len(set(complete_names)) == 100
    complete_digest = hashlib.sha256(
        a13.canonical_json_bytes(list(complete_names))
    ).hexdigest()
    assert complete_digest == (
        "fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3"
    )

    status = "pass_all_expected_mutations_rejected"
    census = _executed_mutation_census()
    assert census == {
        "components": [
            {
                "component_id": "amendment_12_historical",
                "expected_count": 71,
                "expected_domain_sha256": publisher.A12_MUTATION_DOMAIN_SHA256,
                "rejected_count": 71,
                "rejected_domain_sha256": publisher.A12_MUTATION_DOMAIN_SHA256,
                "status": status,
            },
            {
                "component_id": "amendments_13_14_inherited",
                "expected_count": 18,
                "expected_domain_sha256": (
                    publisher.A13_A14_MUTATION_DOMAIN_SHA256
                ),
                "rejected_count": 18,
                "rejected_domain_sha256": (
                    publisher.A13_A14_MUTATION_DOMAIN_SHA256
                ),
                "status": status,
            },
            {
                "component_id": "amendment_15",
                "expected_count": 11,
                "expected_domain_sha256": publisher.A15_MUTATION_DOMAIN_SHA256,
                "rejected_count": 11,
                "rejected_domain_sha256": publisher.A15_MUTATION_DOMAIN_SHA256,
                "status": status,
            },
        ],
        "expected_count": 100,
        "expected_domain_sha256": publisher.COMPLETE_MUTATION_DOMAIN_SHA256,
        "rejected_count": 100,
        "rejected_domain_sha256": publisher.COMPLETE_MUTATION_DOMAIN_SHA256,
        "status": status,
    }


@pytest.mark.parametrize(
    ("component_index", "fault"),
    (
        (0, "missing"),
        (1, "extra"),
        (2, "reordered"),
        (0, "same_count_duplicate"),
    ),
)
def test__complete_mutation_census__fails_closed_on_inherited_drift(
    component_index,
    fault,
):
    outputs = [tuple(names) for names in _executed_mutation_outputs()]
    selected = list(outputs[component_index])
    if fault == "missing":
        selected.pop()
    elif fault == "extra":
        selected.append("unexpected_inherited_mutation")
    elif fault == "reordered":
        selected[:2] = reversed(selected[:2])
    else:
        selected[0] = selected[1]
    outputs[component_index] = tuple(selected)

    runner_names = ("a12_runner", "a13_runner", "a14_runner", "a15_runner")
    runners = {
        name: functools.partial(_return_mutation_names, outputs[index])
        for index, name in enumerate(runner_names)
    }
    with pytest.raises(publisher.PublicationError):
        publisher.run_complete_mutation_census(**runners)
