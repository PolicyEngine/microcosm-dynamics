#!/usr/bin/env python3
"""Build the nonauthority R_Q stage-1 source-replay parent receipt.

The replay is constructed from the two pinned roots and staged source bytes
before the committed source-manifest candidate is read.  The candidate must
then deep-equal that independently reconstructed denominator and page domain.
This script deliberately has no occurrence-candidate input or selection API.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_global_q5_intermediate_evidence as replay  # noqa: E402

OUTPUT_PATH = (
    ROOT / "docs" / "analysis" / "rq_stage1_evidence" / "source_replay_v1.json"
)
SOURCE_MANIFEST_PATH = replay.CATALOG_PATH
SCHEMA_VERSION = "rq_stage1_source_replay.v1"
ARTIFACT_ID = SCHEMA_VERSION
STATUS = "pass_nonauthority_source_replay"
CANONICALIZATION = replay.CANONICALIZATION

SOURCE_MANIFEST_RAW_SIZE = 7_472_778
SOURCE_MANIFEST_RAW_SHA256 = (
    "3cb612aa73388fa4929a5f5531d6ef2919bb2764a5150d3f3ea8ee75da6a0e2e"
)
SOURCE_MANIFEST_CONTENT_SHA256 = (
    "6b939e8aa7681469014aff5a87f9f925ab56acbace8bc2aecfffaad336fd0266"
)

QUESTIONNAIRE_ROOT = {
    "path": (
        "data/external/"
        "psid_questionnaire_corpus_authority_registration_attempt_v1.json"
    ),
    "source_commit": "c1899c9e3f156c411a6e62d2d9b57514c0d6bb2e",
    "tree_mode": "100644",
    "blob_oid": "825f6c61ef9d4a161886cbc44f5cc914d65160d2",
    "byte_size": 520_656,
    "raw_sha256": (
        "07c5bad57d702416da7ee668f504646ba85b9868a7f38819cdec85638c97558c"
    ),
    "content_sha256": (
        "4c91ae30ef8b7ab8c776d4372a4717e7352913e8dd825ba85181ff02b11cef27"
    ),
    "registry_pointer": "/accepted_authority_registry",
    "registry_artifact_id": "psid_questionnaire_corpus_authority_registry.v1",
    "registry_content_sha256": (
        "c82304267d254e81ab5d7e7e198f89d09056700a7429d7fcfa32fdab6bb99b03"
    ),
    "capture_input_identities_sha256": (
        "49246c91428394e3cad712d710b4dd976b95530cc68e076ddbd1c3009b45e877"
    ),
    "registry_document_count": 456,
    "registry_document_domain_sha256": (
        "fa4125a3f1d175628a1ab76dec43edde02960c2e0687b7a6ab9b7d90708133f3"
    ),
    "source_page_index_size_bytes": 668_104,
    "source_page_index_sha256": (
        "159ec5a660b2b302ef16153f6570f24252e2f77a2b9297dd111e39002846a5b7"
    ),
    "source_link_inventory_count": 465,
    "source_link_inventory_size_bytes": 58_679,
    "source_link_inventory_sha256": (
        "4c18313b66e3afa4737081d186deb9cf5a2cb7ff4355386cbd5c99bfa2fa21bd"
    ),
    "registry_status": "pass",
}

FIELD_ROOT = {
    "path": (
        "data/external/"
        "psid_questionnaire_dictionary_inventory_registration_required_v1.json"
    ),
    "source_commit": "b8e8e4f200b362a9661dbc6ef765852496608e49",
    "tree_mode": "100644",
    "blob_oid": "a2e6bfa8b19c35dfde235d8ece7e233a5d833e9e",
    "byte_size": 25_474_435,
    "raw_sha256": (
        "a974c6fb65a9f3d52387163f2e98b7cd8cfdbd57f5e95d1f766b3aa25d167ac0"
    ),
    "content_sha256": (
        "f1f13d9de7dcb2c8a26beafbc60a32390b5a5fb644abb68aeee8df3a5cd1b557"
    ),
    "manifest_pointer": "/source_authority_manifest",
    "manifest_count": 176,
    "manifest_domain_sha256": (
        "52906f7a36955d20282dbce2dd4bac260395d3ce3961bd0baf763290c3152116"
    ),
    "reported_reproduced_from_source_bytes": False,
    "reported_registration_status": "registration_required",
}

CANDIDATE_NONSELECTION_LAW = {
    "expected_source_domain_constructed_before_candidate_manifest_read": True,
    "candidate_manifest_deep_equality_required": True,
    "candidate_manifest_may_select_source_documents": False,
    "candidate_manifest_may_select_pages": False,
    "occurrence_candidates_are_source_replay_inputs": False,
    "flow_path_candidates_are_source_replay_inputs": False,
    "anchor_classification_candidates_are_source_replay_inputs": False,
    "stage2_candidate_auto_promotion_permitted": False,
    "stage2_explicit_adjudication_required_for_every_row": True,
    "status": "pass",
}

EXPECTED_LINK_DISPOSITION_COUNTS = {
    "included_family_questionnaire_flow": 81,
    "excluded_out_of_wave_2025_family_questionnaire": 1,
    "excluded_not_family_questionnaire_flow": 383,
}
EXPECTED_ACCEPTED_DISPOSITION_COUNTS = {
    "included_family_questionnaire_flow": 81,
    "excluded_out_of_wave_2025_family_questionnaire": 1,
    "excluded_not_family_questionnaire_flow": 374,
}
EXPECTED_LINK_DISPOSITION_DOMAIN_SHA256 = (
    "e77e51db23261017194f958e9286867a8627e44d61941898d529f10dddcefb55"
)
EXPECTED_ACCEPTED_DISPOSITION_DOMAIN_SHA256 = (
    "12668139d265d7cf8d0940b4d570b8312012cb65bee2cfa4a08a6755fd03f55e"
)
EXPECTED_PAGE_KEYSET_SHA256 = (
    "d09fa72787bb98c7bfb2a3a5e6621b1d12a6318aef17dac8ed3ed34403ea3638"
)
EXPECTED_PAGE_DOMAIN_SHA256 = (
    "c67f717764eeeb345862628358f174157e8f4942ceeb01acdf1cab9b804af7bc"
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _expect_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keyset drift")


def _verify_git_blob(identity: Mapping[str, Any]) -> None:
    raw = subprocess.run(
        [
            "git",
            "show",
            f"{identity['source_commit']}:{identity['path']}",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    tree_row = subprocess.run(
        [
            "git",
            "ls-tree",
            identity["source_commit"],
            "--",
            identity["path"],
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.rstrip("\n")
    expected_tree_row = (
        f"{identity['tree_mode']} blob {identity['blob_oid']}\t"
        f"{identity['path']}"
    )
    if (
        tree_row != expected_tree_row
        or len(raw) != identity["byte_size"]
        or _sha256(raw) != identity["raw_sha256"]
        or raw != (ROOT / identity["path"]).read_bytes()
    ):
        raise ValueError(f"pinned root Git identity drift: {identity['path']}")


def _verify_root_members(inputs: Mapping[str, Mapping[str, Any]]) -> None:
    questionnaire = inputs["questionnaire_corpus_root"]
    accepted = questionnaire["accepted_authority_registry"]
    questionnaire_observed = {
        "content_sha256": questionnaire["integrity"]["content_sha256"],
        "registry_artifact_id": accepted["artifact_id"],
        "registry_content_sha256": accepted["integrity"]["content_sha256"],
        "capture_input_identities_sha256": accepted[
            "capture_input_identities_sha256"
        ],
        "registry_document_count": accepted["document_count"],
        "registry_document_domain_sha256": accepted["document_rows_sha256"],
        "registry_status": accepted["status"],
    }
    for key, observed in questionnaire_observed.items():
        if observed != QUESTIONNAIRE_ROOT[key]:
            raise ValueError(f"questionnaire root member drift: {key}")
    if (
        replay._content_sha256(questionnaire)
        != QUESTIONNAIRE_ROOT["content_sha256"]
    ):
        raise ValueError("questionnaire root content digest drift")
    accepted_preimage = copy.deepcopy(accepted)
    accepted_preimage["integrity"]["content_sha256"] = "0" * 64
    if (
        replay._canonical_digest(accepted_preimage)
        != QUESTIONNAIRE_ROOT["registry_content_sha256"]
    ):
        raise ValueError("accepted questionnaire registry content drift")

    field = inputs["field_corpus_root"]
    field_observed = {
        "content_sha256": field["integrity"]["content_sha256"],
        "manifest_count": len(field["source_authority_manifest"]),
        "manifest_domain_sha256": field["evidence_summary"][
            "source_authority_manifest_sha256"
        ],
        "reported_reproduced_from_source_bytes": field["integrity"][
            "reproduced_from_source_bytes"
        ],
        "reported_registration_status": field["inventory_ratification_abort"][
            "status"
        ],
    }
    for key, observed in field_observed.items():
        if observed != FIELD_ROOT[key]:
            raise ValueError(f"field root member drift: {key}")


def _committed_source_manifest(
    independently_reconstructed: Mapping[str, Any],
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    raw = SOURCE_MANIFEST_PATH.read_bytes()
    if (
        len(raw) != SOURCE_MANIFEST_RAW_SIZE
        or _sha256(raw) != SOURCE_MANIFEST_RAW_SHA256
    ):
        raise ValueError("committed source-manifest candidate identity drift")
    candidate = replay.strict_parse_document(raw, "source-manifest candidate")
    if not isinstance(candidate, Mapping):
        raise ValueError("source-manifest candidate is not an object")
    replay.validate_catalog_evidence(candidate)
    if raw != replay.canonical_json_bytes(candidate):
        raise ValueError("source-manifest candidate is not canonical")
    if candidate["integrity"]["content_sha256"] != (
        SOURCE_MANIFEST_CONTENT_SHA256
    ):
        raise ValueError("source-manifest candidate content drift")
    for member in ("source_denominator", "questionnaire_page_evidence"):
        if candidate[member] != independently_reconstructed[member]:
            raise ValueError(
                f"candidate {member} does not deep-equal independent replay"
            )
    return candidate, {
        "path": str(SOURCE_MANIFEST_PATH.relative_to(ROOT)),
        "byte_size": len(raw),
        "raw_sha256": _sha256(raw),
        "content_sha256": candidate["integrity"]["content_sha256"],
        "source_denominator_pointer": "/source_denominator",
        "questionnaire_page_evidence_pointer": (
            "/questionnaire_page_evidence"
        ),
        "deep_equal_to_independent_replay": True,
        "read_after_independent_replay": True,
    }


def _document_page_rows(
    denominator: Mapping[str, Any], page_evidence: Mapping[str, Any]
) -> list[dict[str, Any]]:
    pages_by_document: dict[str, list[Mapping[str, Any]]] = {}
    for page in page_evidence["questionnaire_page_rows"]:
        pages_by_document.setdefault(page["source_document_id"], []).append(
            page
        )
    result: list[dict[str, Any]] = []
    for document in denominator["questionnaire_documents"]:
        rows = pages_by_document.get(document["source_document_id"], [])
        if not rows or [row["page_number"] for row in rows] != list(
            range(1, len(rows) + 1)
        ):
            raise ValueError("questionnaire document page cover drift")
        result.append(
            {
                "source_document_id": document["source_document_id"],
                "interview_wave": document["interview_waves"][0],
                "canonical_source_path": document["canonical_source_path"],
                "page_count": len(rows),
                "page_keyset_sha256": replay._canonical_digest(
                    [row["questionnaire_page_id"] for row in rows]
                ),
                "page_domain_sha256": replay._canonical_digest(rows),
            }
        )
    if sum(row["page_count"] for row in result) != 10_190:
        raise ValueError("document page relation does not cover 10,190 pages")
    return result


def _era_replay_rows(
    denominator: Mapping[str, Any], page_evidence: Mapping[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for spec in replay.ERA_SPECS:
        waves = set(spec["interview_waves"])
        documents = [
            row
            for row in denominator["questionnaire_documents"]
            if row["interview_waves"][0] in waves
        ]
        pages = [
            row
            for row in page_evidence["questionnaire_page_rows"]
            if row["interview_wave"] in waves
        ]
        if (
            len(documents) != spec["questionnaire_document_count"]
            or len(pages) != spec["questionnaire_page_count"]
        ):
            raise ValueError(f"{spec['era_id']} replay slice drift")
        result.append(
            {
                "era_id": spec["era_id"],
                "interview_waves": list(spec["interview_waves"]),
                "questionnaire_document_count": len(documents),
                "questionnaire_document_keyset_sha256": (
                    replay._canonical_digest(
                        [row["source_document_id"] for row in documents]
                    )
                ),
                "questionnaire_document_domain_sha256": (
                    replay._canonical_digest(documents)
                ),
                "questionnaire_page_count": len(pages),
                "questionnaire_page_keyset_sha256": replay._canonical_digest(
                    [row["questionnaire_page_id"] for row in pages]
                ),
                "questionnaire_page_domain_sha256": replay._canonical_digest(
                    pages
                ),
            }
        )
    return result


def _page_derivation_authority(
    legacy_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the exact 13-key section 19 derivation authority."""

    value = copy.deepcopy(legacy_identity)
    value["implementation_path"] = value.pop("path")
    if (
        len(replay.canonical_json_bytes(value)) != 566
        or replay._canonical_digest(value)
        != "8ce4d7e16753aa0a6c2220006c9aea60330acd62de809db5894ad03eb9123da3"
    ):
        raise ValueError("questionnaire page derivation authority drift")
    return value


def build_source_replay(
    capture_root: Path = replay.DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    """Independently replay sources, then compare the committed manifest."""

    _verify_git_blob(QUESTIONNAIRE_ROOT)
    _verify_git_blob(FIELD_ROOT)
    inputs = replay._load_frozen_inputs()
    _verify_root_members(inputs)

    # This reconstruction must finish before _committed_source_manifest reads
    # the candidate source manifest.  Do not reorder these calls.
    expected = replay.build_catalog_evidence(capture_root)
    candidate, candidate_identity = _committed_source_manifest(expected)
    denominator = expected["source_denominator"]
    pages = expected["questionnaire_page_evidence"]
    dispositions = denominator["upstream_disposition_evidence"]

    link_rows = dispositions["source_link_disposition_rows"]
    accepted_rows = dispositions["accepted_document_disposition_rows"]
    document_page_rows = _document_page_rows(denominator, pages)
    page_derivation = _page_derivation_authority(
        pages["questionnaire_page_text_derivation"]
    )

    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "design_binding": copy.deepcopy(replay.DESIGN_BINDING),
        "upstream_corpus_registry_identity": {
            "questionnaire_corpus_root": copy.deepcopy(QUESTIONNAIRE_ROOT),
            "field_corpus_root": copy.deepcopy(FIELD_ROOT),
            "projection_law": (
                "fixed_two_root_complete_source_document_projection"
            ),
            "source_document_count": denominator["source_document_count"],
            "source_document_keyset_sha256": denominator[
                "source_document_keyset_sha256"
            ],
            "source_document_domain_sha256": denominator[
                "source_document_domain_sha256"
            ],
            "denominator_status": "pass",
        },
        "wave_replay": copy.deepcopy(expected["wave_domain"]),
        "upstream_disposition_replay": {
            "source_link_disposition_rows": copy.deepcopy(link_rows),
            "source_link_disposition_count": len(link_rows),
            "source_link_disposition_counts": dict(
                Counter(row["disposition"] for row in link_rows)
            ),
            "source_link_disposition_keyset_sha256": (
                replay._canonical_digest(
                    [row["link_position"] for row in link_rows]
                )
            ),
            "source_link_disposition_domain_sha256": replay._canonical_digest(
                link_rows
            ),
            "accepted_document_disposition_count": len(accepted_rows),
            "accepted_document_disposition_rows": copy.deepcopy(accepted_rows),
            "accepted_document_disposition_counts": dict(
                Counter(row["disposition"] for row in accepted_rows)
            ),
            "accepted_document_disposition_keyset_sha256": (
                replay._canonical_digest(
                    [row["source_document_id"] for row in accepted_rows]
                )
            ),
            "accepted_document_disposition_domain_sha256": (
                replay._canonical_digest(accepted_rows)
            ),
            "included_upstream_document_ids_source_order_sha256": (
                dispositions[
                    "included_upstream_document_ids_source_order_sha256"
                ]
            ),
            "status": "pass",
        },
        "source_document_replay": {
            "source_documents": copy.deepcopy(denominator["source_documents"]),
            "source_document_count": denominator["source_document_count"],
            "source_document_role_counts": denominator[
                "source_document_role_counts"
            ],
            "source_document_keyset_sha256": denominator[
                "source_document_keyset_sha256"
            ],
            "source_document_domain_sha256": denominator[
                "source_document_domain_sha256"
            ],
            "questionnaire_document_count": denominator[
                "questionnaire_document_count"
            ],
            "questionnaire_documents": copy.deepcopy(
                denominator["questionnaire_documents"]
            ),
            "questionnaire_document_keyset_sha256": denominator[
                "questionnaire_document_keyset_sha256"
            ],
            "questionnaire_document_domain_sha256": denominator[
                "questionnaire_document_domain_sha256"
            ],
            "source_bytes_reproduced": denominator["source_bytes_reproduced"],
            "canonical_order": denominator["canonical_order"],
            "status": "pass",
        },
        "questionnaire_page_replay": {
            "questionnaire_page_text_derivation": copy.deepcopy(
                page_derivation
            ),
            "questionnaire_page_text_derivation_byte_size": len(
                replay.canonical_json_bytes(page_derivation)
            ),
            "questionnaire_page_text_derivation_sha256": (
                replay._canonical_digest(page_derivation)
            ),
            "questionnaire_page_count": pages["questionnaire_page_count"],
            "questionnaire_page_rows": copy.deepcopy(
                pages["questionnaire_page_rows"]
            ),
            "questionnaire_page_keyset_sha256": pages[
                "questionnaire_page_keyset_sha256"
            ],
            "questionnaire_page_domain_sha256": pages[
                "questionnaire_page_domain_sha256"
            ],
            "document_page_rows": document_page_rows,
            "document_page_row_count": len(document_page_rows),
            "document_page_domain_sha256": replay._canonical_digest(
                document_page_rows
            ),
            "status": "pass",
        },
        "era_replay_rows": _era_replay_rows(denominator, pages),
        "source_manifest_candidate_identity": candidate_identity,
        "candidate_nonselection_law": copy.deepcopy(
            CANDIDATE_NONSELECTION_LAW
        ),
        "authority_disposition": {
            "authority_kind": "nonauthority_source_replay_parent",
            "canonical_q5_emitted": False,
            "canonical_annotation_rows_emitted": False,
            "candidate_occurrence_rows_emitted": False,
            "source_manifest_candidate_status": candidate["status"],
            "status": STATUS,
        },
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": STATUS,
    }
    value["integrity"]["content_sha256"] = replay._content_sha256(value)
    validate_source_replay(value)
    return value


def validate_source_replay(value: Mapping[str, Any]) -> None:
    """Validate the receipt and its SHA-pinned committed manifest."""

    _expect_keys(
        value,
        {
            "schema_version",
            "artifact_id",
            "design_binding",
            "upstream_corpus_registry_identity",
            "wave_replay",
            "upstream_disposition_replay",
            "source_document_replay",
            "questionnaire_page_replay",
            "era_replay_rows",
            "source_manifest_candidate_identity",
            "candidate_nonselection_law",
            "authority_disposition",
            "integrity",
            "status",
        },
        "source replay",
    )
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["artifact_id"] != ARTIFACT_ID
        or value["design_binding"] != replay.DESIGN_BINDING
        or value["status"] != STATUS
        or value["candidate_nonselection_law"] != CANDIDATE_NONSELECTION_LAW
        or value["integrity"]
        != {
            "canonicalization": CANONICALIZATION,
            "content_sha256": replay._content_sha256(value),
        }
    ):
        raise ValueError("source-replay identity or nonselection-law drift")

    root = value["upstream_corpus_registry_identity"]
    if (
        set(root)
        != {
            "questionnaire_corpus_root",
            "field_corpus_root",
            "projection_law",
            "source_document_count",
            "source_document_keyset_sha256",
            "source_document_domain_sha256",
            "denominator_status",
        }
        or root["questionnaire_corpus_root"] != QUESTIONNAIRE_ROOT
        or root["field_corpus_root"] != FIELD_ROOT
        or root["projection_law"]
        != "fixed_two_root_complete_source_document_projection"
        or root["source_document_count"] != 257
        or root["source_document_keyset_sha256"]
        != replay.EXPECTED_U_KEYSET_SHA256
        or root["source_document_domain_sha256"]
        != replay.EXPECTED_U_DOMAIN_SHA256
        or root["denominator_status"] != "pass"
    ):
        raise ValueError("root replay drift")

    if value["wave_replay"] != {
        "interview_waves": list(replay.INTERVIEW_WAVES),
        "interview_wave_count": len(replay.INTERVIEW_WAVES),
        "interview_wave_domain_sha256": replay.EXPECTED_WAVE_DOMAIN_SHA256,
    }:
        raise ValueError("wave replay drift")

    disposition = value["upstream_disposition_replay"]
    _expect_keys(
        disposition,
        {
            "source_link_disposition_rows",
            "source_link_disposition_count",
            "source_link_disposition_counts",
            "source_link_disposition_keyset_sha256",
            "source_link_disposition_domain_sha256",
            "accepted_document_disposition_rows",
            "accepted_document_disposition_count",
            "accepted_document_disposition_counts",
            "accepted_document_disposition_keyset_sha256",
            "accepted_document_disposition_domain_sha256",
            "included_upstream_document_ids_source_order_sha256",
            "status",
        },
        "disposition replay",
    )
    link_rows = disposition["source_link_disposition_rows"]
    accepted_rows = disposition["accepted_document_disposition_rows"]
    if (
        len(link_rows) != disposition["source_link_disposition_count"]
        or disposition["source_link_disposition_count"] != 465
        or any(
            set(row) != {"link_position", "disposition"} for row in link_rows
        )
        or [row["link_position"] for row in link_rows] != list(range(1, 466))
        or disposition["source_link_disposition_counts"]
        != EXPECTED_LINK_DISPOSITION_COUNTS
        or disposition["source_link_disposition_keyset_sha256"]
        != replay._canonical_digest(
            [row["link_position"] for row in link_rows]
        )
        or disposition["source_link_disposition_domain_sha256"]
        != replay._canonical_digest(link_rows)
        or disposition["source_link_disposition_domain_sha256"]
        != EXPECTED_LINK_DISPOSITION_DOMAIN_SHA256
        or len(accepted_rows)
        != disposition["accepted_document_disposition_count"]
        or disposition["accepted_document_disposition_count"] != 456
        or any(
            set(row) != {"source_document_id", "disposition"}
            for row in accepted_rows
        )
        or disposition["accepted_document_disposition_counts"]
        != EXPECTED_ACCEPTED_DISPOSITION_COUNTS
        or disposition["accepted_document_disposition_keyset_sha256"]
        != replay._canonical_digest(
            [row["source_document_id"] for row in accepted_rows]
        )
        or disposition["accepted_document_disposition_domain_sha256"]
        != replay._canonical_digest(accepted_rows)
        or disposition["accepted_document_disposition_domain_sha256"]
        != EXPECTED_ACCEPTED_DISPOSITION_DOMAIN_SHA256
        or disposition["included_upstream_document_ids_source_order_sha256"]
        != replay.EXPECTED_UPSTREAM_QUESTIONNAIRE_ID_SHA256
        or disposition["status"] != "pass"
    ):
        raise ValueError("disposition replay drift")

    source = value["source_document_replay"]
    _expect_keys(
        source,
        {
            "source_documents",
            "source_document_count",
            "source_document_role_counts",
            "source_document_keyset_sha256",
            "source_document_domain_sha256",
            "questionnaire_documents",
            "questionnaire_document_count",
            "questionnaire_document_keyset_sha256",
            "questionnaire_document_domain_sha256",
            "source_bytes_reproduced",
            "canonical_order",
            "status",
        },
        "source document replay",
    )
    source_rows = source["source_documents"]
    questionnaire_rows = source["questionnaire_documents"]
    source_row_keys = {
        "source_document_id",
        "document_role",
        "interview_waves",
        "canonical_source_path",
        "storage_disposition",
        "storage_identity",
        "byte_size",
        "sha256",
    }
    allowed_roles = set(replay.ROLE_ORDER)
    source_ids: list[str] = []
    for row in source_rows:
        if (
            set(row) != source_row_keys
            or row["document_role"] not in allowed_roles
            or not isinstance(row["interview_waves"], list)
            or len(row["interview_waves"]) != 1
            or row["interview_waves"][0] not in replay.INTERVIEW_WAVES
            or row["storage_disposition"] != "external_registered_file"
            or set(row["storage_identity"])
            != {"authority_registry_id", "document_id", "registered_path"}
            or row["storage_identity"]["registered_path"]
            != row["canonical_source_path"]
            or not isinstance(row["byte_size"], int)
            or isinstance(row["byte_size"], bool)
            or row["byte_size"] <= 0
            or not isinstance(row["sha256"], str)
            or len(row["sha256"]) != 64
        ):
            raise ValueError("source-document row schema or value drift")
        expected_id = "psid-source-document:" + replay._canonical_digest(
            [
                row["document_role"],
                row["interview_waves"],
                row["canonical_source_path"],
                row["byte_size"],
                row["sha256"],
            ]
        )
        if row["source_document_id"] != expected_id:
            raise ValueError("source-document ID preimage drift")
        source_ids.append(row["source_document_id"])
    expected_questionnaire_rows = [
        row
        for row in source_rows
        if row["document_role"] == "questionnaire_flow"
    ]
    if (
        len(source_rows) != source["source_document_count"]
        or source["source_document_count"] != 257
        or len(set(source_ids)) != len(source_ids)
        or source_rows != sorted(source_rows, key=replay._source_order)
        or source["source_document_role_counts"]
        != dict(Counter(row["document_role"] for row in source_rows))
        or source["source_document_role_counts"]
        != {
            "questionnaire_flow": 81,
            "dictionary_layout": 86,
            "codebook": 47,
            "raw_fixed_width_data": 43,
        }
        or source["source_document_keyset_sha256"]
        != replay._canonical_digest(
            [row["source_document_id"] for row in source_rows]
        )
        or source["source_document_keyset_sha256"]
        != replay.EXPECTED_U_KEYSET_SHA256
        or source["source_document_domain_sha256"]
        != replay._canonical_digest(source_rows)
        or source["source_document_domain_sha256"]
        != replay.EXPECTED_U_DOMAIN_SHA256
        or len(questionnaire_rows) != source["questionnaire_document_count"]
        or source["questionnaire_document_count"] != 81
        or questionnaire_rows != expected_questionnaire_rows
        or source["questionnaire_document_keyset_sha256"]
        != replay._canonical_digest(
            [row["source_document_id"] for row in questionnaire_rows]
        )
        or source["questionnaire_document_keyset_sha256"]
        != replay.EXPECTED_QUESTIONNAIRE_KEYSET_SHA256
        or source["questionnaire_document_domain_sha256"]
        != replay._canonical_digest(questionnaire_rows)
        or source["questionnaire_document_domain_sha256"]
        != replay.EXPECTED_QUESTIONNAIRE_DOMAIN_SHA256
        or source["source_bytes_reproduced"] is not True
        or source["canonical_order"]
        != "document_role_wave_canonical_source_path_v1"
        or source["status"] != "pass"
    ):
        raise ValueError("source-document replay drift")

    if (
        root["source_document_count"] != source["source_document_count"]
        or root["source_document_keyset_sha256"]
        != source["source_document_keyset_sha256"]
        or root["source_document_domain_sha256"]
        != source["source_document_domain_sha256"]
    ):
        raise ValueError("upstream identity and U replay disagree")

    pages = value["questionnaire_page_replay"]
    _expect_keys(
        pages,
        {
            "questionnaire_page_text_derivation",
            "questionnaire_page_text_derivation_byte_size",
            "questionnaire_page_text_derivation_sha256",
            "questionnaire_page_rows",
            "questionnaire_page_count",
            "questionnaire_page_keyset_sha256",
            "questionnaire_page_domain_sha256",
            "document_page_rows",
            "document_page_row_count",
            "document_page_domain_sha256",
            "status",
        },
        "questionnaire page replay",
    )
    page_rows = pages["questionnaire_page_rows"]
    expected_derivation = _page_derivation_authority(
        replay.PAGE_IMPLEMENTATION
    )
    questionnaire_by_id = {
        row["source_document_id"]: row for row in questionnaire_rows
    }
    page_ids: list[str] = []
    page_coordinates: list[tuple[str, int]] = []
    page_counts: Counter[str] = Counter()
    page_row_keys = {
        "questionnaire_page_id",
        "source_document_id",
        "canonical_source_path",
        "corpus_digest_row_locator",
        "interview_wave",
        "page_number",
        "page_text_utf8_size_bytes",
        "page_text_utf8_sha256",
    }
    for row in page_rows:
        document = questionnaire_by_id.get(row["source_document_id"])
        locator = row["corpus_digest_row_locator"]
        if (
            set(row) != page_row_keys
            or set(locator)
            != {
                "source_document_id",
                "digest_row_filename",
                "digest_row_number",
                "expected_size_bytes",
                "expected_sha256",
            }
            or document is None
            or row["canonical_source_path"]
            != document["canonical_source_path"]
            or row["interview_wave"] != document["interview_waves"][0]
            or locator["source_document_id"]
            != document["storage_identity"]["document_id"]
            or locator["expected_size_bytes"] != document["byte_size"]
            or locator["expected_sha256"] != document["sha256"]
            or Path(row["canonical_source_path"]).name
            != locator["digest_row_filename"]
            or not isinstance(row["page_number"], int)
            or isinstance(row["page_number"], bool)
            or row["page_number"] <= 0
            or not isinstance(row["page_text_utf8_size_bytes"], int)
            or isinstance(row["page_text_utf8_size_bytes"], bool)
            or row["page_text_utf8_size_bytes"] < 0
            or not isinstance(row["page_text_utf8_sha256"], str)
            or len(row["page_text_utf8_sha256"]) != 64
        ):
            raise ValueError("questionnaire page replay row drift")
        expected_page_id = (
            "psid-questionnaire-page:"
            + replay._canonical_digest(
                [
                    row["source_document_id"],
                    row["interview_wave"],
                    row["page_number"],
                    row["page_text_utf8_sha256"],
                ]
            )
        )
        if row["questionnaire_page_id"] != expected_page_id:
            raise ValueError("questionnaire page ID preimage drift")
        page_ids.append(row["questionnaire_page_id"])
        page_coordinates.append(
            (row["source_document_id"], row["page_number"])
        )
        page_counts[row["source_document_id"]] += 1
    expected_page_coordinates = [
        (document["source_document_id"], page_number)
        for document in questionnaire_rows
        for page_number in range(
            1, page_counts[document["source_document_id"]] + 1
        )
    ]
    if (
        pages["questionnaire_page_text_derivation"] != expected_derivation
        or pages["questionnaire_page_text_derivation_byte_size"] != 566
        or pages["questionnaire_page_text_derivation_sha256"]
        != "8ce4d7e16753aa0a6c2220006c9aea60330acd62de809db5894ad03eb9123da3"
        or len(page_rows) != pages["questionnaire_page_count"]
        or pages["questionnaire_page_count"] != 10_190
        or len(set(page_ids)) != len(page_ids)
        or page_coordinates != expected_page_coordinates
        or pages["questionnaire_page_keyset_sha256"]
        != replay._canonical_digest(
            [row["questionnaire_page_id"] for row in page_rows]
        )
        or pages["questionnaire_page_keyset_sha256"]
        != EXPECTED_PAGE_KEYSET_SHA256
        or pages["questionnaire_page_domain_sha256"]
        != replay._canonical_digest(page_rows)
        or pages["questionnaire_page_domain_sha256"]
        != EXPECTED_PAGE_DOMAIN_SHA256
        or pages["document_page_row_count"] != 81
        or pages["document_page_rows"] != _document_page_rows(source, pages)
        or sum(row["page_count"] for row in pages["document_page_rows"])
        != 10_190
        or pages["document_page_domain_sha256"]
        != replay._canonical_digest(pages["document_page_rows"])
        or pages["status"] != "pass"
    ):
        raise ValueError("questionnaire page replay drift")

    era_rows = value["era_replay_rows"]
    if (
        len(era_rows) != 6
        or sum(row["questionnaire_document_count"] for row in era_rows) != 81
        or sum(row["questionnaire_page_count"] for row in era_rows) != 10_190
        or [row["era_id"] for row in era_rows]
        != [spec["era_id"] for spec in replay.ERA_SPECS]
        or era_rows != _era_replay_rows(source, pages)
    ):
        raise ValueError("era replay rows drift")

    manifest = value["source_manifest_candidate_identity"]
    if manifest != {
        "path": str(SOURCE_MANIFEST_PATH.relative_to(ROOT)),
        "byte_size": SOURCE_MANIFEST_RAW_SIZE,
        "raw_sha256": SOURCE_MANIFEST_RAW_SHA256,
        "content_sha256": SOURCE_MANIFEST_CONTENT_SHA256,
        "source_denominator_pointer": "/source_denominator",
        "questionnaire_page_evidence_pointer": (
            "/questionnaire_page_evidence"
        ),
        "deep_equal_to_independent_replay": True,
        "read_after_independent_replay": True,
    }:
        raise ValueError("source-manifest candidate identity drift")
    authority = value["authority_disposition"]
    if authority != {
        "authority_kind": "nonauthority_source_replay_parent",
        "canonical_q5_emitted": False,
        "canonical_annotation_rows_emitted": False,
        "candidate_occurrence_rows_emitted": False,
        "source_manifest_candidate_status": replay.BLOCKED_STATUS,
        "status": STATUS,
    }:
        raise ValueError("source-replay authority disposition drift")


def render_source_replay(
    capture_root: Path = replay.DEFAULT_CAPTURE_ROOT,
) -> bytes:
    return replay.canonical_json_bytes(build_source_replay(capture_root))


def _write_or_check(path: Path, raw: bytes, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_bytes() != raw:
            raise ValueError(f"{path} does not reproduce")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capture-root", type=Path, default=replay.DEFAULT_CAPTURE_ROOT
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _write_or_check(
        args.output, render_source_replay(args.capture_root), args.check
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
