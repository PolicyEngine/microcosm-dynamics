"""Validate Amendment 13's Amendment-16-governed execution law.

This module emits no authority and writes no artifact.  It reconstructs the
proposed repair overlays from the six pinned stage-2 source seals, checks the
historical Amendment-12 ratification blob, authenticates the complete
revision-derived amendment-closure domain under Amendment 16's generalized
oracle, and exercises the separate adversarial mutation inventories.
Amendment 12's frozen pilot bundle and its 71 mutations are not changed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_amendment12_rq_catalog_pilot as a12  # noqa: E402


class LawError(RuntimeError):
    """Raised when a proposed Amendment-13 law fixture fails closed."""


SCHEMA_VERSION = "amendment_13_tier_2_execution_law.v1"
OVERLAY_SCHEMA_VERSION = "rq_stage2_document_repair_overlay.v1"
SUCCESSOR_SCHEMA_VERSION = "rq_stage2_local_evidence_repair_successor.v1"
SUPERSESSION_SCHEMA_VERSION = "rq_stage2_predecessor_supersession.v1"
ERA_SEAL_SCHEMA_VERSION = "rq_stage3_era_repair_successor_seal.v1"
GOVERNING_A13_IDENTITY_SCHEMA_VERSION = (
    "amendment_13_governing_ratification_identity.v1"
)
GOVERNING_A13_IDENTITY_STATUS = "RATIFIED_AMENDMENT_13_GOVERNING_EXECUTION_LAW"
CLOSURE_SCHEMA_IDENTIFIER = (
    "covered_earnings_amendment_ratification_closure.v1"
)
CLOSURE_TOP_LEVEL_KEYS = (
    "amendment_number",
    "attested_candidate_design_blob_oid",
    "attested_candidate_design_byte_size",
    "attested_candidate_design_raw_sha256",
    "operator_merge_commit",
    "ratification_commit",
    "ratification_commit_sole_parent",
    "verdict_artifacts",
)
CLOSURE_VERDICT_KEYS = ("byte_size", "path", "raw_sha256")
REGISTRY_CLOSURE_BINDING_KEYS = ("path", "raw_byte_size", "raw_sha256")
REGISTRY_DESIGN_BINDING_KEYS = (
    "path",
    "ratification_commit",
    "revision",
    "blob_sha256",
    "ratification_closures",
)
DRAFT_STATUS = "PROSPECTIVE_NONAUTHORITY_UNRATIFIED_DRAFT"
RATIFICATION_BOUND_TEMPLATE_STATUS = (
    "RATIFIED_LAW_BOUND_NONAUTHORITY_EXECUTION_TEMPLATE"
)
GOVERNING_A13_CANDIDATE_IDENTITY = {
    "schema_version": (
        "amendment_13_governing_ratification_identity_candidate.v1"
    ),
    "status": "UNAVAILABLE_BEFORE_AMENDMENT_13_RATIFICATION",
    "authority_emitted": False,
}

PROOF_TERMINAL_STATUS = (
    "terminal_semantically_incompatible_local_proof_no_alias_admitted"
)
INCOMPLETE_FRAGMENT_STATUS = (
    "terminal_incomplete_fragment_disclosed_no_alias_admitted"
)
COMPOSED_FRAGMENT_STATUS = (
    "complete_instruction_reading_by_exact_whitespace_composition"
)
DOC036_SUCCESSOR_STATUS = (
    "coherent_document_reseal_component_domain_corrected_to_aggregate"
)
SUPERSESSION_RELATION = "predecessor_row_superseded_by_named_successor"
SUPERSESSION_STATUS = "append_only_predecessor_retained_successor_selected"
STATUS_MAPPING_BY_FAMILY = {
    "modern_handoff_status": {
        "status_family": "modern_handoff_status",
        "status_field": "handoff_status",
        "predecessor_status": (
            "local_resolved_cross_reference_for_global_assembly"
        ),
    },
    "legacy_resolution_status": {
        "status_family": "legacy_resolution_status",
        "status_field": "resolution_status",
        "predecessor_status": "document_local_source_evidence_complete",
    },
    "document_036_special_resolution_status": {
        "status_family": "document_036_special_resolution_status",
        "status_field": "resolution_status",
        "predecessor_status": "locally_resolved_document_evidence",
    },
}
FRAGMENT_SELECTOR_RULE = (
    "unique_predecessor_alias_anchor_context_occurrence_at_duplicate_"
    "leading_span"
)
COMPOSITION_RULE = (
    "same_page_exact_leading_bytes_plus_whitespace_gap_plus_exact_"
    "continuation_bytes"
)

RATIFICATION_COMMIT = "29c593d1954d94795e9f092ec4333e7d60a6136f"
RATIFICATION_PARENT = "c033ee527809a220032d28e1c91345a64b221e32"
DESIGN_PATH = "docs/design/covered_earnings_correction.md"
DESIGN_MODE = "100644"
DESIGN_BLOB = "626213aa45bce6b8c94b36dcaded16800ce0323d"
DESIGN_BYTE_SIZE = 3_713_728
DESIGN_SHA256 = (
    "283a010c1bb135917fd8c1f1aebd1526165f829509d32e7689537167aa8818f5"
)
AMENDMENT13_BOUNDARY = (
    b"\n## 27. AMENDMENT SECTION \xe2\x80\x94 Amendment 13: ratification "
    b"identity and tier-2 repair-successor law\n"
)
REVISION15_BYTE_SIZE = 3_810_536
REVISION15_SHA256 = (
    "ae939693b8bcd99244135a170fdf268f0120d22a4d5cd857f5fcec525b5c859b"
)
REVISION15_BLOB_OID = "323ce94dafa70b4496f9e1eaa490f16e9707624b"
AMENDMENT14_BOUNDARY = (
    b"\n## 28. AMENDMENT SECTION \xe2\x80\x94 Amendment 14: closure-bound "
    b"ratification and blob-bound implementation\n"
)
REVISION16_BYTE_SIZE = 3_836_294
REVISION16_SHA256 = (
    "c4f3ae022d2e623f4316600e16ec3bded10f0160d197ce64e37f35015e55c92f"
)
REVISION16_BLOB_OID = "4a3280c849070359232ab445635e016e98de3981"
AMENDMENT15_BOUNDARY = (
    b"\n## 29. AMENDMENT SECTION \xe2\x80\x94 Amendment 15: ordered "
    b"publication attestation and tier-2 certification\n"
)
REVISION17_BYTE_SIZE = 3_881_111
REVISION17_SHA256 = (
    "556311b72ec6c8e30eeda4b0f602e0f7f43b9d080c2454966fa3dda3a561d16e"
)
REVISION17_BLOB_OID = "50a2a14e1c8845d342dca83559688866e97dc4a7"
AMENDMENT16_BOUNDARY = (
    b"\n## 30. AMENDMENT SECTION \xe2\x80\x94 Amendment 16: generalized "
    b"ratification oracle and combined revision-18 activation\n"
)
REVISION18_BYTE_SIZE = 3_915_641
REVISION18_SHA256 = (
    "17a4bc2b48bd48039ce0777dd22f265eff156fe2484efd6c7b106c5c642dd1b6"
)
REVISION18_BLOB_OID = "114089d99b83c5073e21b6fb64cd701719ac5741"
AMENDMENT17_BOUNDARY = (
    b"\n## 31. AMENDMENT SECTION \xe2\x80\x94 Amendment 17: test-pin "
    b"activation cure and executed-transition ratification\n"
)
FIRST_CLOSURE_AMENDMENT = 13
HISTORICAL_TERMINAL_REVISION = 16
FORBIDDEN_STANDALONE_REVISION = 17
COMBINED_ACTIVATION_REVISION = 18
A13_MERGED_RATIFICATION_COMMIT = "0cf2a90b1decaa52de4bcd1032227092ac9210c5"
A13_MERGED_RATIFICATION_PARENT = "a16f6089eca06e98bf18b8238f056bb6effae383"
A14_MERGED_RATIFICATION_COMMIT = "062d74187e3263cd4a7fad3851a9b8c699a2556c"
A14_MERGED_RATIFICATION_PARENT = "8f92d83a97398331411fc9aeb5bb748f16c065a7"
A15_MERGED_RATIFICATION_COMMIT = "c2ffe3e95152ff005485f55acaf75259e6095195"
A15_MERGED_RATIFICATION_PARENT = "a352e66284b60997210c634bb427141e7e523a75"
A13_CLOSURE_PATH = "docs/analysis/amendment_13_ratification/closure_v1.json"
A14_CLOSURE_PATH = "docs/analysis/amendment_14_ratification/closure_v1.json"
A15_CLOSURE_PATH = "docs/analysis/amendment_15_ratification/closure_v1.json"
A16_CLOSURE_PATH = "docs/analysis/amendment_16_ratification/closure_v1.json"
A14_HISTORICAL_CLOSURE_BINDING = {
    "path": A14_CLOSURE_PATH,
    "raw_byte_size": 842,
    "raw_sha256": (
        "0770fc470187d41bc32198b1acbad61927f07f27f26192cb5093a30e411d57d4"
    ),
}
A13_VERDICT_ARTIFACTS = (
    {
        "path": (
            "docs/analysis/amendment_13_ratification/"
            "sol-ce-amend13-r3-verdict.md"
        ),
        "byte_size": 6_207,
        "raw_sha256": (
            "7e0f1ad7faec611a08ed8f0123cc484fe981a0f9681e7cd144f4deafb128dc72"
        ),
    },
    {
        "path": (
            "docs/analysis/amendment_13_ratification/"
            "sol-ce-amend13-r3b-verdict.md"
        ),
        "byte_size": 5_379,
        "raw_sha256": (
            "6cd4b1e5689985685bf88100b78b20b676ae222a323cec20a6c9097799a75383"
        ),
    },
)
A13_EXPECTED_CLOSURE = {
    "amendment_number": 13,
    "attested_candidate_design_blob_oid": REVISION15_BLOB_OID,
    "attested_candidate_design_byte_size": REVISION15_BYTE_SIZE,
    "attested_candidate_design_raw_sha256": REVISION15_SHA256,
    "operator_merge_commit": A13_MERGED_RATIFICATION_COMMIT,
    "ratification_commit": A13_MERGED_RATIFICATION_COMMIT,
    "ratification_commit_sole_parent": A13_MERGED_RATIFICATION_PARENT,
    "verdict_artifacts": [dict(row) for row in A13_VERDICT_ARTIFACTS],
}
A15_VERDICT_ARTIFACTS = (
    {
        "path": (
            "docs/analysis/amendment_15_ratification/"
            "sol-ce-amend15-r4-verdict.md"
        ),
        "byte_size": 6_652,
        "raw_sha256": (
            "61e2943e27ae20e219fed5de8aaad86fe744904ab1c387484a2a5175c73fd11e"
        ),
    },
    {
        "path": (
            "docs/analysis/amendment_15_ratification/"
            "sol-ce-amend15-r4b-verdict.md"
        ),
        "byte_size": 6_141,
        "raw_sha256": (
            "df3302dbe06ced4b99bc1a6952d0f866f5ea6afa6ab2dcbe84ce68d26aa03bf6"
        ),
    },
)
A15_EXPECTED_CLOSURE = {
    "amendment_number": 15,
    "attested_candidate_design_blob_oid": REVISION17_BLOB_OID,
    "attested_candidate_design_byte_size": REVISION17_BYTE_SIZE,
    "attested_candidate_design_raw_sha256": REVISION17_SHA256,
    "operator_merge_commit": A15_MERGED_RATIFICATION_COMMIT,
    "ratification_commit": A15_MERGED_RATIFICATION_COMMIT,
    "ratification_commit_sole_parent": A15_MERGED_RATIFICATION_PARENT,
    "verdict_artifacts": [dict(row) for row in A15_VERDICT_ARTIFACTS],
}
RATIFICATION_CHANGED_PATH_COUNT = 17
ATTESTED_CANDIDATE_HEAD = "76acad02b0d519d12057b75ab7c21f2c2a4b2433"
A12_SWEEP_PATH = (
    "docs/analysis/amendment_12_rq_catalog_pilot/"
    "corpus_exhaustive_targeted_sweeps_v1.json"
)
A12_SWEEP_BYTE_SIZE = 37_001_180
A12_SWEEP_SHA256 = (
    "54ca1c347d5e77ee06dbb79ed8af3fc5db11d70f787724a9b85474c36a64888d"
)
A12_CONTINUATION_PROJECTION_BYTE_SIZE = 1_457
A12_CONTINUATION_PROJECTION_SHA256 = (
    "59e03dffa4564a202a39463b80ebb60bae641afc49b78bc42d93c201737116cf"
)
RATIFY_ATTESTATIONS = (
    {
        "record_name": "sol-ce-amend12-r5-verdict.md",
        "raw_byte_size": 4_394,
        "raw_sha256": (
            "9b407dcd7321da0350895e7798db3705d54be279fa69937cb8fea9a51f733961"
        ),
        "verdict_token": "RATIFY",
        "attested_candidate_head": ATTESTED_CANDIDATE_HEAD,
        "attested_document_byte_size": DESIGN_BYTE_SIZE,
        "attested_document_sha256": DESIGN_SHA256,
    },
    {
        "record_name": "sol-ce-amend12-r5b-verdict.md",
        "raw_byte_size": 3_396,
        "raw_sha256": (
            "7999f3188bf83bd2b9b520964a36fe7582f6af1217d11869e017f307bd88f145"
        ),
        "verdict_token": "RATIFY",
        "attested_candidate_head": ATTESTED_CANDIDATE_HEAD,
        "attested_document_byte_size": DESIGN_BYTE_SIZE,
        "attested_document_sha256": DESIGN_SHA256,
    },
)

AMENDMENT12_RATIFICATION_IDENTITY = {
    "ratification_commit": RATIFICATION_COMMIT,
    "ratification_parents": [RATIFICATION_PARENT],
    "document_path": DESIGN_PATH,
    "document_mode": DESIGN_MODE,
    "document_blob_oid": DESIGN_BLOB,
    "document_byte_size": DESIGN_BYTE_SIZE,
    "document_sha256": DESIGN_SHA256,
    "dual_ratify_attestations": [dict(row) for row in RATIFY_ATTESTATIONS],
}

INCOMPATIBLE_PROOF_IDS = tuple("""
rq-local-repeat-evidence:c93bb69e6a4c04717efd8b68e71799b5b4f3cb1c1c20a1b31afe2852d04dab67
rq-local-repeat-evidence:0c25501bcb134ddd36f5f076978ebd01a02d3e731772c4ae5de182d81a76a487
rq-local-repeat-alias-evidence:c7020c1c35780475871c3d0ddce0767b1fe22b6f6c45c79fbd03093519ffc716
rq-local-repeat-alias-evidence:b8ea2ca5e2b198e2c4f9ec8ef9608a68b53b8c7a0f76435f4c2ca0db3f57a456
rq-local-repeat-alias-evidence:78c2d51532910f9dbebaac790485bb20e2a0d907e632f4d32c327c185d52a34c
rq-local-repeat-alias-evidence:224c03c08758f9ea5f0e6920b949ff50afc42ef2165923be05fc7646b8249623
rq-local-repeat-alias-evidence:e3ca944c92c9a5053ff989551b47d8cfbe885565bfc6e0f59886c74a8b3a1331
rq-local-repeat-alias-evidence:238d3e9a1faceb345a3f13380b6cc04a97ed5c9a54d7fe931c178588415c9d11
rq-local-repeat-alias-evidence:6c1381f0c6a1ee424dc21dee75fde1263efbe2cdaa4d4b396a28847fea3b6b89
rq-local-repeat-alias-evidence:6d0ad010bf859e35f2d90ef9ba2dceaf60f4625dacac9cd6c4ed0ccdf814f526
rq-local-repeat-alias-evidence:122109cba974f0e5ed897f0236668a04ed2dca7e5c15f3fa2c47fbd69bec633a
rq-local-repeat:d20165da2c897270b8d8708bdd2ee7a860d6c3ac905c9e05dcc622a75b413a92
rq-local-repeat-alias-evidence:b2ff04405ce6c20fb6848441dd5fc249ac55b99c6ce21a60ff1ef331b42d8a19
rq-local-repeat-alias-evidence:e4b4c44f443929ce8facfa51ce2e318e201490d259b01e507d4dded083e8fba2
rq-local-repeat-alias-evidence:6c17ebd0a0c97a5b46fef9ff2c5326fe45acf482647c6a2fd0d3bf542be17b22
rq-local-repeat-alias-evidence:f44ce5328602c75bcde9b50b2de94d68582a6fe7080eea03b1de32e622171a22
rq-local-repeat-alias-evidence:f4de9f70a2b5a851a4d1e56c63dc7a35574c14d877122f6c0983d2e6268fb516
rq-local-repeat-evidence:d6f7cdeab7418133a2bb1ea992d0b42e0749079e1aa890e799f96310d690bd0c
rq-local-repeat-evidence:c9b24cb9e34a7050a567093ee0f0500df3e221dd2afa9adfdaba02010fd31509
rq-local-repeat-evidence:db438aefe04bee804bdc15f683dba9f90d0963871a6242217b18e09bdbed01c4
rq-local-repeat-evidence:6ce1ef4653dfa56a49ff6baf30052132630c1ed47dfb246dcf38c1e63a24f83f
rq-local-repeat-evidence:7e1395227e1f81c5fe864d17e319e56b724424eab5163df68109dd85f81ce5c7
rq-local-repeat-evidence:e1e5e2a1b422ae3334fd657b68dbd1922e56e36165b4913c8d309896ac72d6d4
rq-local-repeat-evidence:c207d07c88d2bef6b99a038d94a1f870ac038072de4c005241ab9ce3f79439c3
rq-local-repeat-evidence:fd7a9eebc0d44fe9cf4ba8795b478b2d6a933b8aa42dd45d52cb561328e86ada
rq-local-repeat-evidence:bb6ce7690468d1ef2e0d4a22bfa831bf9b81f7824db8a9dd59e06df44434c877
rq-local-repeat-evidence:525a55100f92a4f6f05e156d9d784029ea29126e2c5374195545513375b36e8c
rq-local-repeat-evidence:a06a1898968a9dc0d44b34bbd5ca9efc9bb856a56bde685815ff6621d1f82b39
""".split())
INCOMPATIBLE_PROOF_ID_DOMAIN_SHA256 = (
    "9c8cb11732939daac176275ae66dfa5a6ce61a2850c82087dd761a6431ac7412"
)
PROOF_FINDING_MIXED_ENDPOINT = (
    "cited_instruction_does_not_authenticate_the_mixed_or_misbound_"
    "endpoint_projection"
)
PROOF_FINDING_HETEROGENEOUS_PAGE = (
    "cited_repeat_text_does_not_authenticate_the_heterogeneous_page_wide_"
    "endpoint_projection"
)
PROOF_FINDING_JOB_CONTEXT = (
    "cited_same_occupation_text_asserts_semantics_but_the_job_context_"
    "endpoint_crossing_requires_reseal"
)
PROOF_FINDING_INCOMPLETE_CLAUSE = (
    "cited_instruction_is_an_incomplete_clause_and_cannot_authenticate_a_"
    "complete_redirection"
)
PROOF_FINDING_SHARED_INCOME_LIST = (
    "cited_income_list_is_shared_with_an_independent_alias_proof_and_does_"
    "not_authenticate_this_pairing"
)
PROOF_FINDING_MISPAIRED_CONTEXT = (
    "cited_see_instructions_text_is_mispaired_to_a_context_remuneration_"
    "endpoint_claim"
)
PROOF_PREDECESSOR_FINDING_BY_ID = dict(
    zip(
        INCOMPATIBLE_PROOF_IDS,
        (
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_HETEROGENEOUS_PAGE,
            PROOF_FINDING_JOB_CONTEXT,
            PROOF_FINDING_HETEROGENEOUS_PAGE,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_HETEROGENEOUS_PAGE,
            PROOF_FINDING_HETEROGENEOUS_PAGE,
            PROOF_FINDING_HETEROGENEOUS_PAGE,
            PROOF_FINDING_HETEROGENEOUS_PAGE,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_MIXED_ENDPOINT,
            PROOF_FINDING_INCOMPLETE_CLAUSE,
            PROOF_FINDING_SHARED_INCOME_LIST,
            PROOF_FINDING_INCOMPLETE_CLAUSE,
            PROOF_FINDING_SHARED_INCOME_LIST,
            PROOF_FINDING_SHARED_INCOME_LIST,
            PROOF_FINDING_SHARED_INCOME_LIST,
            PROOF_FINDING_SHARED_INCOME_LIST,
            PROOF_FINDING_MISPAIRED_CONTEXT,
            PROOF_FINDING_INCOMPLETE_CLAUSE,
            PROOF_FINDING_INCOMPLETE_CLAUSE,
        ),
        strict=True,
    )
)

FRAGMENT_SPECS = (
    (
        10,
        "rq-local-repeat-alias-evidence:47745f10b28added1b86a6132864c7283ef1ca618468e73ea4c5819fa8359fdf",
        "psid-questionnaire-occurrence:a37cf7dce81d69ba18e303afdd31a0825103c53d01398e644a312d55155150ba",
        "incomplete",
    ),
    (
        17,
        "rq-local-repeat-alias-evidence:ed65f56aae0cef0e9f3254bf30bf1f22a8b8b1a0bb8769fdcd3e7e3ed64920ca",
        "psid-questionnaire-occurrence:8b9c6613b23e83dd55af058542e6aec3be341440397c632d91c1b74f073291dd",
        "incomplete",
    ),
    (
        56,
        "rq-local-repeat-evidence:468d69712cdc3c252a164e25627dac13a8d88ba6fc757ebccd173fd6146dbf79",
        "psid-questionnaire-occurrence:b151de324a45124f27e1b426eb06b8a94ccb653cea7cb7af8dd402341d6b61c5",
        "incomplete",
    ),
    (
        56,
        "rq-local-repeat-evidence:ae1fe2b52813498193d184b8a35eb56e0ba5418358565974625fc17fb33b0da2",
        "psid-questionnaire-occurrence:e64ef592cbb11ef00efa78f26682094c8920a21960309c673bbff8008c99a5c8",
        "incomplete",
    ),
    (
        58,
        "rq-local-repeat-evidence:dd35a09d551e0beff7209a4f0dc0bc96b876b0047622343c964c8134ad96bce2",
        "psid-questionnaire-occurrence:9242a1af728bffad6ed96e7636bcaade0e31fe0a21561d97fe500c89cc9e5b12",
        "incomplete",
    ),
    (
        58,
        "rq-local-repeat-evidence:603d228cdb03d6c74221954662165e824edd2cf4775551c6f292ef8c23d398e7",
        "psid-questionnaire-occurrence:9969e959ae2d58b54b5fbdfc4f4e6e0f8141f628d67415370e1ccd129017a4fb",
        "incomplete",
    ),
    (
        58,
        "rq-local-repeat-evidence:12d99ddb4330bf509bf8e686078e98397dd5b3003c76f36fecd1f48303a087e1",
        "psid-questionnaire-occurrence:4b6c12f1e8e57edd45a3d43a772c69d923ec4c72d8292cdff1ca1f9c0a069e3b",
        "incomplete",
    ),
    (
        66,
        "rq-local-repeat-evidence:ed0c801ba48f634dac9e766d90116aab30f533f82aed9846af81aa739b059aba",
        "psid-questionnaire-occurrence:5eb05b791f0abad829debc9863433e0a8e7bd254aa18ac51b6c750caa48bb46a",
        "incomplete",
    ),
    (
        66,
        "rq-local-repeat-evidence:072f1a10af512096365db74950dbec13e0ee1d3e293004854d051840c252f3fb",
        "psid-questionnaire-occurrence:d662043b204306d6c052f412fe674574e80fd1a40aca75b1842a212bb1fe8f68",
        "composed",
    ),
    (
        70,
        "rq-local-repeat-evidence:c08d6d192cfc873940e5aed3ab53199f828160b3aaec0ce3591c4ce6807b1f71",
        "psid-questionnaire-occurrence:5e89bb2a5186c4afee4a6a2289a4686ddcee89aeeae089b42c24e3ce9ff72708",
        "composed",
    ),
)
FRAGMENT_EVIDENCE_ID_DOMAIN_SHA256 = (
    "e61a3f5c5dbdd90804aaea656b40336ff078d8cb8e010317c37e41a2e7dc54a9"
)
FRAGMENT_INSTRUCTION_ID_DOMAIN_SHA256 = (
    "74075ac0ca54eff2a9459d4e95f426195c9e01db78040025462aa2f57f486a09"
)

DOC036_CLASSIFICATION_IDS = tuple("""
rq-local-anchor:6b757b140c4fdbcfcfe8b974f7894ffc856ab3dca240b7eb61530adca0e2d12a
rq-local-anchor:11802d91128200f95abc1a42e5e39677f30c955da28e8b89bdc72e10ff8c11ef
rq-local-anchor:daae302f7bdebd7a8ab43d983faaedecb97ac22f8a7ca7c3af92dbff1cb76de5
rq-local-anchor:5d7ea81f571ca24a50d2a03acc07d605e49b7438233f63191fa98147e82f4a7a
rq-local-anchor:930c509fadfdc037d5e03d65422cc7c3d3b86a9ec3adb7553e86d9654632d4ca
rq-local-anchor:5a703e10bfd94a486c21d043d7ad980905870b908ea70b2f136c16e835e1a261
rq-local-anchor:d6d21da4a96eda0e310284ca6cebc059f340e2bdaf2da64f56286d65a03fa283
rq-local-anchor:93b5b7f3d32e6dda9e3fad1089fc4ba605502765e4de1735223637bc615fff29
""".split())
DOC036_CLASSIFICATION_ID_DOMAIN_SHA256 = (
    "1d2271438f3d9a7744e1379ed26ce565ff2731ed0dd8dec357c0bd8a9a271d23"
)

LAW_GAP_IDS = tuple("""
rq-local-repeat-evidence:0e380305f67b13fceef903d3e1c24590891a63e1beeefbc6953d58334baaf4e6
rq-local-repeat-evidence:f3b859c0dbda01517b66f70b0652a84d0c0b048a38c4deea4477ea05d3be5045
rq-local-repeat-evidence:da2954a94634f3371ef85000ce0db5f121f0968a6704264434573867c6522495
rq-local-repeat-evidence:e5ff3d4e974f7c527fd7be988d6075b152586ed1f6ec06f37711bb47667b191d
rq-local-repeat-alias-evidence:db641c23f0d13b3befcdde005cf6b3804cc85a7e3985804091a59d826584a0c1
rq-local-repeat-alias-evidence:e744b798ebfb58ba3b8e1c28c7b0c5cbeadfadd649b5951f25a9326b1dafc0bf
rq-local-repeat-alias-evidence:9aed9fbcbb6cbe3f0697b12e95522c1a9e539b5e4e2a031b3b2bb531b45f3ced
rq-local-repeat-alias-evidence:92db20a47e9e0771b874238f39d920d69203e822e5cb28cf461394fa9d8bf254
rq-local-repeat-alias-evidence:71cbb45447d775ba33f493a3e0ebe800226d463bf73905566216fcb53287512d
rq-local-repeat-evidence:4ac3d89c423be55bac47c13cced2fd92151014ef3a45d95fba4b2999cca518f2
rq-local-repeat-alias-evidence:1c3c1a81c8d783c04813b7e1c0a5654ecab4f43d0ffd290c95a391c5daf54547
rq-local-repeat-alias-evidence:c0fdbc2f6b82371351dbcf266ab083dba8c20cce3298e283012ec5c618bca868
rq-local-repeat-evidence:5977fa11c007f370ece29867bc0d2b6c5d492990396b50d86959b1ec5ec87927
rq-local-repeat-alias-evidence:1120df9c2c375e51c32b9a546f3dbbd176366ba6de7258c38c344dd84b5f0734
""".split())
LAW_GAP_ID_DOMAIN_SHA256 = (
    "f2e8a5001527eb975887828ba3e66c3eeac95ec0972454bcef509fba92149883"
)

EXPECTED_OVERLAY_DOMAIN_SHA256 = (
    "adee2e8320759ea709821d48af69ee2c12dec7499a9bef03de23f15c23ba79a5"
)
EXPECTED_SUCCESSOR_DOMAIN_SHA256 = (
    "63ff5646b640a4252d440810db77a862e2178fc74e61171d287d7984576dcbea"
)
EXPECTED_SUPERSESSION_DOMAIN_SHA256 = (
    "396395f20f984a58fc606ab66010fa06af79641c19f5afdc0605ce7b40aef709"
)
EXPECTED_ERA_SEAL_DOMAIN_SHA256 = (
    "f1c0f05543955ea13a9b1037f80609f30d681b0ea890620d89717beb6c4cac9d"
)

COMPOSITION_SPECS = {
    66: {
        "page_number": 40,
        "page_text_utf8_sha256": (
            "c15cbbe8277db5e1947a851a6e8825e6c744423553f1675b40d2506c64d78dba"
        ),
        "candidate_occurrences_in_source_order": [
            {
                "occurrence_id": (
                    "psid-questionnaire-occurrence:"
                    "9fc63af834ead33179a04f232c562cabf46ff899f260413f1722a9e634b2288b"
                ),
                "occurrence_kind": "context_anchor",
            },
            {
                "occurrence_id": (
                    "psid-questionnaire-occurrence:"
                    "c80d228a189f6717cb5e9a24039e9e4e91717230b628b16d66723869c988bf73"
                ),
                "occurrence_kind": "field_purpose_prompt",
            },
        ],
        "selected_leading_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "9fc63af834ead33179a04f232c562cabf46ff899f260413f1722a9e634b2288b"
        ),
        "leading_text": (
            "G75.            You may select as many codes as apply to the "
            "OFUM’s current situation. (See"
        ),
        "leading_utf8_sha256": (
            "1021f9d838c9c537f919c39151194f4a9a73b29e98062b3c6e6da6662d90ddb3"
        ),
        "combined_utf8_byte_start": 1163,
        "leading_utf8_byte_end": 1256,
        "gap_utf8_byte_start": 1256,
        "gap_utf8_byte_end": 1273,
        "gap_text": "\n                ",
        "gap_utf8_sha256": (
            "9085bed86afe0e5076de36797b5a6fb0568afee9757a3f128fccafd20073ed1d"
        ),
        "continuation_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "d662043b204306d6c052f412fe674574e80fd1a40aca75b1842a212bb1fe8f68"
        ),
        "continuation_utf8_byte_start": 1273,
        "combined_utf8_byte_end": 1332,
        "combined_text": (
            "G75.            You may select as many codes as apply to the "
            "OFUM’s current situation. (See\n                BC1-BC3/DE1-DE3 "
            "QxQs for definitions of employment status.)"
        ),
        "combined_utf8_sha256": (
            "b0464ed90ae6e945acb9266265be23de87ea4c71f3e3e1f64044efc4de7e35a3"
        ),
    },
    70: {
        "page_number": 50,
        "page_text_utf8_sha256": (
            "6af0a63fc43dd0a6ce85fde4531a1d663c936b757226fc47a77e1542aa85da37"
        ),
        "candidate_occurrences_in_source_order": [
            {
                "occurrence_id": (
                    "psid-questionnaire-occurrence:"
                    "e6c4259365c5e03ab88abd497ba90522191bdbe51922beb9387252fc97b56911"
                ),
                "occurrence_kind": "context_anchor",
            },
            {
                "occurrence_id": (
                    "psid-questionnaire-occurrence:"
                    "cc84a7597efc0f59d1b7960943aad2b3f6ed83bada2c022cc7149db79a7e3937"
                ),
                "occurrence_kind": "field_purpose_prompt",
            },
        ],
        "selected_leading_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "e6c4259365c5e03ab88abd497ba90522191bdbe51922beb9387252fc97b56911"
        ),
        "leading_text": (
            "G75.           You may select as many codes as apply to the "
            "OFUM’s current situation. (See"
        ),
        "leading_utf8_sha256": (
            "e73f4502ed097d89331d556ed2d2e3ff52f44b274b63f2f5ba0627182fac3303"
        ),
        "combined_utf8_byte_start": 2391,
        "leading_utf8_byte_end": 2483,
        "gap_utf8_byte_start": 2483,
        "gap_utf8_byte_end": 2499,
        "gap_text": "\n               ",
        "gap_utf8_sha256": (
            "c4c6af77697b2e9aa849e5930932e3c7917371dc46460bd15fe2dc0b3449b261"
        ),
        "continuation_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "5e89bb2a5186c4afee4a6a2289a4686ddcee89aeeae089b42c24e3ce9ff72708"
        ),
        "continuation_utf8_byte_start": 2499,
        "combined_utf8_byte_end": 2558,
        "combined_text": (
            "G75.           You may select as many codes as apply to the "
            "OFUM’s current situation. (See\n               BC1-BC3/DE1-DE3 "
            "QxQs for definitions of employment status.)"
        ),
        "combined_utf8_sha256": (
            "abb07e986b5f123ef36d9aad0b2ee4d25b4d57e8415ef8b67f995279734306f9"
        ),
    },
}

EXPECTED_ERA_COUNTS = {
    "wave1968_ry1968_1974_early_totals": (7, 1, 0, 0, 8),
    "ry1975_1977_spouse_concept_seam": (4, 1, 0, 0, 5),
    "ry1978_1992_pre_er_totals": (1, 0, 0, 8, 9),
    "ry1993_2001_er_transition": (14, 5, 0, 0, 19),
    "ry2002_2014_modern_bc_de": (2, 1, 2, 0, 5),
    "ry2015_2022_exclusion_lineage": (0, 0, 0, 0, 0),
}

PROSPECTIVE_ERA_SEAL_IDS = (
    "a13-successor-era-seal:0a638a9a1bdaf341653c5409b2395081e67657413244478846d3c60cdab377db",
    "a13-successor-era-seal:2a4d7f0553b9c76b6289b5e343371780cd2c6eccdd6466234307974b5b3c3fe4",
    "a13-successor-era-seal:531ea88addbc73f77323d7d873f939db0f773534dc04eeac6310c1ffb0e87902",
    "a13-successor-era-seal:7dcbfb47b7320bf8b7c147cf01b222a22fcdcf66cb92d2a781e296fc1139875c",
    "a13-successor-era-seal:810397821f6393ef051bef9afc2f4fe689104c0cafb6ac40a3c53ed91da00b51",
    "a13-successor-era-seal:0cdf284967712845c7fe37f8a292249e42a3e8303ac211d20ec26cbe948def6f",
)

PROSPECTIVE_DOMAIN_PINS = (
    (
        "Repair overlays",
        14,
        "adee2e8320759ea709821d48af69ee2c12dec7499a9bef03de23f15c23ba79a5",
    ),
    (
        "All repair successors",
        46,
        "63ff5646b640a4252d440810db77a862e2178fc74e61171d287d7984576dcbea",
    ),
    (
        "Supersession edges",
        46,
        "396395f20f984a58fc606ab66010fa06af79641c19f5afdc0605ce7b40aef709",
    ),
    (
        "Successor-era seal fixtures",
        6,
        "f1c0f05543955ea13a9b1037f80609f30d681b0ea890620d89717beb6c4cac9d",
    ),
)

A13_EXPECTED_MUTATIONS = (
    "ratification_identity_wrong_blob",
    "ratification_identity_wrong_commit",
    "ratification_identity_multiple_parents",
    "successor_terminal_status_forged",
    "predecessor_supersession_erasure",
    "fragment_duplicate_selector_forged",
    "fragment_composition_transformation_forged",
)
A13_ENFORCEMENT_EXPECTED_MUTATIONS = (
    "governing_document_semantics_forged_and_repinned",
    "implementation_pin_interval_override_forged_and_repinned",
    "enacted_identifier_absent_from_qualified_inventory",
    "git_replace_refs_substitute_parent_and_changed_paths",
    "verdict_artifact_missing",
    "ratification_closure_missing",
    "ratification_closure_verdict_byte_mismatch",
    "ratification_closure_attested_blob_mismatch",
    "ratification_closure_schema_keyset_violation",
    "implementation_pin_blob_mismatch",
    "ratification_closure_coherent_verdict_and_closure_substitution",
)
A13_HISTORICAL_ENFORCEMENT_MUTATIONS = (
    "governing_document_semantics_forged_and_repinned",
    "implementation_pin_interval_override_forged_and_repinned",
    "dual_ratify_records_coherently_self_minted",
    "reviewer_registry_two_keys_one_actor_self_enrolled",
    "enacted_identifier_absent_from_qualified_inventory",
    "git_replace_refs_substitute_parent_and_changed_paths",
)
REMOVED_PKI_MUTATIONS = (
    "dual_ratify_records_coherently_self_minted",
    "reviewer_registry_two_keys_one_actor_self_enrolled",
)

A13_SEARCH_AUGMENTATION = (
    "Amendment 13",
    "revision 15",
    RATIFICATION_COMMIT,
    DESIGN_BLOB,
    "exact_attested_document_blob_not_commit_path_shape",
    "amendment_13_governing_ratification_identity_candidate.v1",
    GOVERNING_A13_IDENTITY_SCHEMA_VERSION,
    "UNAVAILABLE_BEFORE_AMENDMENT_13_RATIFICATION",
    GOVERNING_A13_IDENTITY_STATUS,
    RATIFICATION_BOUND_TEMPLATE_STATUS,
    "amendment12_ratification_identity",
    "governing_amendment13_ratification_identity",
    OVERLAY_SCHEMA_VERSION,
    SUCCESSOR_SCHEMA_VERSION,
    SUPERSESSION_SCHEMA_VERSION,
    ERA_SEAL_SCHEMA_VERSION,
    PROOF_TERMINAL_STATUS,
    INCOMPLETE_FRAGMENT_STATUS,
    COMPOSED_FRAGMENT_STATUS,
    DOC036_SUCCESSOR_STATUS,
    "terminal_semantic_incompatibility_umbrella_with_exact_predecessor_finding_preserved",
    "semantically_incompatible_local_proof",
    "incomplete_fragment_terminal_disclosure",
    "composed_fragment_complete_instruction",
    "doc036_aggregate_domain_correction",
    SUPERSESSION_RELATION,
    FRAGMENT_SELECTOR_RULE,
    COMPOSITION_RULE,
    "A13_EXPECTED_MUTATIONS",
)

A13_SCHEMA_LITERALS = (
    SCHEMA_VERSION,
    "amendment_13_governing_ratification_identity_candidate.v1",
    GOVERNING_A13_IDENTITY_SCHEMA_VERSION,
    OVERLAY_SCHEMA_VERSION,
    SUCCESSOR_SCHEMA_VERSION,
    SUPERSESSION_SCHEMA_VERSION,
    ERA_SEAL_SCHEMA_VERSION,
)
A13_CONTENT_ID_PREFIXES = (
    "a13-document-repair-overlay:",
    "a13-repair-successor:",
    "a13-supersession:",
    "a13-successor-era-seal:",
)
A13_STATUS_RELATION_OPERATION_CODES = (
    DRAFT_STATUS,
    "PROSPECTIVE_NONAUTHORITY",
    "UNAVAILABLE_BEFORE_AMENDMENT_13_RATIFICATION",
    GOVERNING_A13_IDENTITY_STATUS,
    RATIFICATION_BOUND_TEMPLATE_STATUS,
    PROOF_TERMINAL_STATUS,
    "terminal_semantic_incompatibility_umbrella_with_exact_predecessor_finding_preserved",
    INCOMPLETE_FRAGMENT_STATUS,
    COMPOSED_FRAGMENT_STATUS,
    DOC036_SUCCESSOR_STATUS,
    SUPERSESSION_RELATION,
    SUPERSESSION_STATUS,
    "linked_successor_row",
    "repair_by_exact_span_disclosure_not_invention",
    "exact_same_page_whitespace_composition",
    "replace_only_node_domain_component_slot_with_aggregate",
    FRAGMENT_SELECTOR_RULE,
    COMPOSITION_RULE,
    "exact_attested_document_blob_not_commit_path_shape",
)
A13_SUCCESSOR_KIND_LITERALS = (
    "semantically_incompatible_local_proof",
    "incomplete_fragment_terminal_disclosure",
    "composed_fragment_complete_instruction",
    "doc036_aggregate_domain_correction",
)

A14_SCHEMA_BINDING_IDENTIFIERS = (
    CLOSURE_SCHEMA_IDENTIFIER,
    "ratification_closures",
)
A14_PATH_TEMPLATES = (
    "docs/analysis/amendment_N_ratification/closure_v1.json",
    "docs/analysis/amendment_N_ratification/",
)
A14_STATUS_OPERATION_IDENTIFIERS = (
    "OPERATIVE",
    "closure_bound_dual_ratify_operator_merge_registry_repin",
    "working_tree_head_and_enacted_blob_identity",
    DRAFT_STATUS,
    RATIFICATION_BOUND_TEMPLATE_STATUS,
)
A14_RATIFICATION_SEQUENCE = (
    "final candidate bytes",
    "two parallel affirmative RATIFY verdicts on those exact bytes",
    "operator merge of the design PR",
    "commit both exact verdict artifacts and both A13/A14 closure_v1.json files on the revision-16 repin branch",
    "merge the revision-16 registry repin that pins the design and both closure identities",
    "Amendments 13 and 14 become operative",
)
A16_RATIFICATION_LAW_VALUES = {
    "amendment_revision_offset": 2,
    "first_closure_amendment": 13,
    "closure_count_subtrahend": 14,
    "historical_terminal_revision": 16,
    "forbidden_standalone_revision": 17,
    "combined_activation_revision": 18,
    "combined_activation_closure_domain": [13, 14, 15, 16],
    "combined_activation_newly_operative_domain": [15, 16],
    "historical_r05_amendment_number": 15,
    "historical_r05_design_revision": 17,
    "historical_r05_snapshot_revision": 18,
    "inherited_complete_mutation_count": 100,
    "inherited_complete_mutation_domain_sha256": (
        "fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3"
    ),
}
A16_COMBINED_CLOSURE_PATHS = tuple(
    f"docs/analysis/amendment_{amendment_number}_ratification/closure_v1.json"
    for amendment_number in (13, 14, 15, 16)
)
A16_RATIFICATION_SEQUENCE = (
    "final Amendment-16 candidate bytes with the exact revision-17 prefix",
    "two parallel affirmative Amendment-16 RATIFY verdicts on those exact bytes",
    "operator merge of the Amendment-16 design PR",
    "commit the exact A15 verdict copies, the A15 closure, both exact A16 verdict artifacts, and the A16 closure on the revision-18 repin branch",
    "merge the revision-18 registry repin that pins the final design and ordered A13/A14/A15/A16 closure identities",
    "validate the complete four-closure snapshot under the generalized oracle",
    "Amendments 15 and 16 become operative simultaneously",
)
A16_HISTORICAL_R05_BINDING = {
    "amendment_number": 15,
    "design_revision": 17,
    "design_path": DESIGN_PATH,
    "closure_path": A15_CLOSURE_PATH,
}
A16_EXPECTED_MUTATIONS = (
    "ratification_operativity_wrong_closure_count_for_revision",
    "ratification_operativity_closure_order_forged",
    "ratification_operativity_non_a13_closure_forged_as_another",
    "ratification_operativity_nonterminal_registry_revision",
    "ratification_operativity_combined_activation_missing_closure",
    "ratification_operativity_amendment15_alone_activation",
    "ratification_operativity_amendment16_alone_activation",
)
A16_MUTATION_DOMAIN_SHA256 = (
    "1e00099f636c1a727839ebc298b965cd0981e0ad8f23189367ba7dbd0eddb871"
)
A16_SCHEMA_OPERATION_IDENTIFIERS = (
    "terminal_revision_general_ratification_operativity.v1",
    "combined_revision_18_amendments_15_16_activation",
    "historical_amendment_closure_selected_from_terminal_registry_snapshot",
    "complete_closure_domain_before_single_closure_selection",
    "terminal_closure_only_registry_cross_binding",
)
A16_STATUS_IDENTIFIERS = (
    "PROSPECTIVE_NONAUTHORITY_UNRATIFIED_AMENDMENT_16",
    "OPERATIVE_COMBINED_REVISION_18_AMENDMENTS_15_16",
    "FORBIDDEN_STANDALONE_REVISION_17",
)
A16_PYTHON_IDENTIFIERS = (
    "_ratification_amendment_numbers",
    "_validate_registry_ratification_context",
    "_terminal_design_amendment",
    "_validate_non_a13_ratification_design",
    "_validate_ratification_operativity_context",
    "run_amendment16_oracle_mutation_tests",
)
A17_SECTION_SEMANTIC_SHA256 = (
    "d522322f1f30256877c67b8cab02c513b4a2527c235d6f4faf3700b7a5b93fbd"
)
A17_REVISION_DOMAIN_RULES = (
    "permitted terminal R = 16 or any integer R >= 18",
    "expected operative domain = tuple(range(13, R - 1))",
    "revision 16 expected domain = (13, 14)",
    "revision 18 expected domain = (13, 14, 15, 16)",
    "revision 19 expected domain = (13, 14, 15, 16, 17)",
    "revision 17 = forbidden before any result comparison",
)
A17_EXECUTED_TRANSITION_OBLIGATION = {
    "scope": "Amendment 17 and every future activation-affecting amendment",
    "ambiguity_disposition": "fails closed into this obligation",
    "ratification_verdict": "# RATIFY",
    "invalid_demonstration_disposition": "unratifiable",
    "simulated_state_authority": "NONAUTHORITY",
    "execution_order": [
        "validate_ratification_operativity()",
        "tests/test_validate_amendment13_execution_law.py",
    ],
    "same_state_required": True,
    "implementation_pin_verification_required": True,
}
A17_RECEIPT_SCHEMA = {
    "top_level_keys": [
        "simulated_state_authority",
        "simulated_state_identity_sha256",
        "simulated_state_manifest",
        "terminal_revision",
        "public_oracle",
        "full_pinned_battery",
    ],
    "manifest_keys": [
        "schema_version",
        "simulated_state_authority",
        "candidate_or_scratch_HEAD",
        "terminal_revision",
        "canonical_registry_binding",
        "ordered_closure_identities",
        "full_pinned_battery_test_identity",
    ],
    "manifest_schema_version": "executed_transition_state.v1",
    "manifest_authority": "NONAUTHORITY",
    "closure_identity_keys": [
        "path",
        "raw_byte_size",
        "raw_sha256",
        "git_blob",
    ],
    "test_identity_keys": [
        "path",
        "mode",
        "git_blob",
        "raw_byte_size",
        "raw_sha256",
    ],
    "public_oracle_keys": [
        "entrypoint",
        "executed",
        "exit_code",
        "operative_amendments",
        "simulated_state_identity_sha256",
    ],
    "full_pinned_battery_keys": [
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
    ],
    "integer_fields": [
        "public_oracle.exit_code",
        "full_pinned_battery.exit_code",
        "full_pinned_battery.collected",
        "full_pinned_battery.passed",
        "full_pinned_battery.failed",
        "full_pinned_battery.skipped",
        "full_pinned_battery.deselected",
        "full_pinned_battery.xfailed",
        "full_pinned_battery.xpassed",
    ],
    "closed_without_defaults_or_extra_keys": True,
    "canonicalization": (
        "ascii_json_sorted_keys_no_insignificant_whitespace_"
        "no_nonfinite_values_one_terminal_lf"
    ),
    "nested_state_identities_equal_top_level": True,
}
A17_TRANSITION_REGISTRY_BINDING = {
    "path": DESIGN_PATH,
    "ratification_commit": "60289833febdf88cb9d8977ac1282a0f4b97b278",
    "revision": 18,
    "blob_sha256": REVISION18_SHA256,
}
A17_TRANSITION_CLOSURE_IDENTITIES = (
    {
        "amendment_number": 13,
        "path": A13_CLOSURE_PATH,
        "raw_byte_size": 842,
        "raw_sha256": (
            "fce13fc1e5e2b4026a34dab735ca36186b147260bd0a137979aa52711affabd7"
        ),
        "git_blob": "abc1145fec35af1673e7852d77f701828e3de139",
    },
    {
        "amendment_number": 14,
        "path": A14_CLOSURE_PATH,
        "raw_byte_size": 842,
        "raw_sha256": (
            "0770fc470187d41bc32198b1acbad61927f07f27f26192cb5093a30e411d57d4"
        ),
        "git_blob": "a13e1384d1f81d3072f7ac7af1c0fd547b9c5709",
    },
    {
        "amendment_number": 15,
        "path": A15_CLOSURE_PATH,
        "raw_byte_size": 842,
        "raw_sha256": (
            "f48ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a"
        ),
        "git_blob": "7ec67cbfa239b57e13f6b1d470c6e143a9be6f05",
    },
    {
        "amendment_number": 16,
        "path": A16_CLOSURE_PATH,
        "raw_byte_size": 842,
        "raw_sha256": (
            "5a39ba6965504db9b72a6057f1ac32e547487947662b3528a13ba17a5bab260c"
        ),
        "git_blob": "24422550fb7d1dc9c33074f2c0ac4ce0c28c6fa5",
    },
)
A17_TRANSITION_VERDICT_ARTIFACTS = (
    {
        "path": (
            "docs/analysis/amendment_16_ratification/"
            "sol-ce-amend16-r1-verdict.md"
        ),
        "byte_size": 3_525,
        "raw_sha256": (
            "68206da2c65de1b5334eca6207e1a9ebfd62c774d1a62db366ab275c28240723"
        ),
    },
    {
        "path": (
            "docs/analysis/amendment_16_ratification/"
            "sol-ce-amend16-r1b-verdict.md"
        ),
        "byte_size": 4_124,
        "raw_sha256": (
            "4c1ebf07f59bb78e9f629c3a7a0d5a6adc19fa63f612f77e1acea8feb296f3c9"
        ),
    },
)
A17_REQUIRED_PUBLIC_OUTPUT = (13, 14, 15, 16)
A17_FULL_PINNED_BATTERY = {
    "test_path": "tests/test_validate_amendment13_execution_law.py",
    "exit_code": 0,
    "collected": 76,
    "passed": 76,
    "failed": 0,
    "skipped": 0,
    "deselected": 0,
    "xfailed": 0,
    "xpassed": 0,
}
A17_EXPECTED_MUTATIONS = (
    "revision_general_test_expected_domain_forged",
    "revision_general_test_revision17_accepted",
    "activation_transition_full_pinned_battery_bypassed",
)
A17_MUTATION_DOMAIN_SHA256 = (
    "b19ebcbf47278d63e12bd8021334a88910895bdfe48caf2d49c6bbe3014417e6"
)
A17_MUTATION_CENSUS = {
    "inherited_complete_mutation_count": 100,
    "inherited_complete_mutation_domain_sha256": (
        "fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3"
    ),
    "amendment16_mutation_count": 7,
    "amendment16_mutation_domain_sha256": A16_MUTATION_DOMAIN_SHA256,
}
A17_SUPERSESSION_MAP = (
    (
        "§30.4.1 active implementation rows",
        "Superseded as active prospective-validation pins only by "
        "§31.2.2's complete table. Historical identities remain immutable.",
    ),
    (
        "§30.3.4 exact revision-18 result and §§30.2.1–30.2.4 general "
        "oracle",
        "Lawfully unchanged. The corrected test now expects their result.",
    ),
    (
        "A16 ratification demonstration and §30.3.3 sequence",
        "Composed with §31.3: every future activation-affecting amendment "
        "must execute both the public oracle and full pinned battery against "
        "one post-transition state before RATIFY.",
    ),
    (
        "§29.4.7 100-name census and §30.5 seven-name oracle inventory",
        "Lawfully unchanged and separately re-executed; the three A17 "
        "attacks remain outside both.",
    ),
    (
        "§§27.3–27.6, closure schemas and historical objects, census "
        "machinery, repair semantics, blockers, and out-of-scope work",
        "Byte-identical and lawfully unchanged.",
    ),
)

A13_SECTION_SEMANTIC_SHA256: Mapping[str, str] = {
    "27.2": "2e1d4e8282e393f2f8f8092c5b9823d69a4e6926fb5fbd753b77813e47f7941e",
    "27.3": "50b5a2e780a4b5b7152390e85e01df5f5397f5263fb2dd3dae43947a96f91ff0",
    "27.4": "ae7dd9ea588a2242f52d4e66bd3662909eee0f987a1d582db21786837c47253c",
    "27.5": "f5ee9246c5826b5b65e90149cc2e2c7574eb32f49df472ce528fc0690ab26d46",
    "27.6": "b8b23250e218093d892c6ad286f05226469d5abf08a1f87d8a0942bbbbef5d08",
    "27.7": "2dfcffcba99639a6d9b00efc6d0d06364a4c0e2fd522238f07dc715228d8ad2e",
    "27.8": "fdc5441ef8c2f60bb8334658b4c44bcd52f8355b4681a495e81c4b7aaaa5479e",
}
A14_SECTION_SEMANTIC_SHA256 = (
    "8d17464268b95d500dcc4d7640edee0f26180a70172cdb3a3966a8e6d2408062"
)
A15_SECTION_SEMANTIC_SHA256 = (
    "a1e7bcb2aabc2b43cc92b09e1d8bf96d644d377ae70d81d9c5f40d7fafa94f3b"
)
A16_SECTION_SEMANTIC_SHA256 = (
    "8ed37933bc04d9c2233d62c74385bd03d8e0862067147a295218e37bcd11125a"
)

A13_COMPARATOR_ROWS = (
    (
        "DC-72",
        "§§26.10.1–26.10.3, DC-64, §26.11, and §27.2 Amendment-12 ratification identity",
        "replaced-by-named-successor: every revision-14 D12 document-only locator and the obsolete no-ratification clause select actual Amendment-12 history by exact commit/blob/bytes/dual-attestation identity; every other ceremony, noninstantiation, and stop survives",
    ),
    (
        "DC-73",
        "§§26.7.2, 27.3, and 27.4 exact 28 incompatible proof rows",
        "replaced-by-named-successor: terminal no-alias successor, deterministic predecessor-family map, retained predecessor, supersession edge, overlay, and era membership",
    ),
    (
        "DC-74",
        "§§26.7, 26.11.2, and 27.5 exact ten incomplete fragments and five prior continuation citations",
        "replaced-by-named-successor for the ten only: eight disclosed terminal fragments plus two exact G75 compositions; five-citation Amendment-12 domain lawfully unchanged",
    ),
    (
        "DC-75",
        "§§26.7.1, 27.3, and 27.6 doc-036 and six-era reseal",
        "lawfully-unchanged-with-reason: eight sole-field changes were already determinate; the new proof successor now permits one coherent nine-row overlay and all six exact successor-seal domains",
    ),
    (
        "DC-76",
        "§§26.8–26.9 and 27.7 validation evidence, mutations, and 14 law gaps",
        "lawfully-unchanged-with-reason: 71 historical attacks remain exact; seven new attacks are separate; all 14 law gaps and every row outside 46 remain untouched",
    ),
    (
        "DC-77",
        "§§25.10, 26.10–26.11, and 27.8 lifecycle, authority, Q5, and production after applying DC-72's D12 locator",
        "lawfully-unchanged-with-reason: apart from the exact ratification locator named in DC-72, the draft emits no authority, tier-2 execution occurs later if ratified, and the independent Amendment-11 blocker remains controlling",
    ),
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LawError(message)


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    _require(set(value) == expected, f"{label} keyset drift")


def canonical_json_bytes(value: Any) -> bytes:
    """Return the law's compact, sorted, terminal-LF JSON bytes."""

    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise LawError("value is not strict canonical JSON") from error
    return text.encode("ascii") + b"\n"


def _identity_bytes(value: Any) -> bytes:
    return canonical_json_bytes(value)[:-1]


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _domain_sha(value: Any) -> str:
    return _sha256(canonical_json_bytes(value))


def _content_id(prefix: str, preimage: Any) -> str:
    return f"{prefix}:{_sha256(_identity_bytes(preimage))}"


_A13_SECTION_HEADINGS = (
    "### 27.2 Limb I — Amendment-12 ratification identity",
    "### 27.3 Limb II — append-only repair overlays and successor identity",
    "### 27.4 The 28 semantically incompatible local-proof successors",
    "### 27.5 The ten incomplete-fragment successors",
    "### 27.6 Doc-036 correction and the six-era cascade",
    "### 27.7 Scope boundary, executable pins, and attacks",
    "### 27.8 Replacement closure, comparator, identifiers, and inoperability",
)


def _unique_after(text: str, marker: str, label: str) -> str:
    _require(text.count(marker) == 1, f"{label} marker drift")
    return text.split(marker, 1)[1]


def _unique_between(
    text: str,
    start_marker: str,
    end_marker: str,
    label: str,
) -> str:
    """Return text between one exact start marker and its next end marker."""

    remainder = _unique_after(text, start_marker, label)
    _require(end_marker in remainder, f"{label} end marker drift")
    return remainder.split(end_marker, 1)[0]


def _code_tokens_between(
    text: str,
    start_marker: str,
    end_marker: str,
    expected: int,
    label: str,
) -> list[str]:
    return _code_tokens(
        _unique_between(text, start_marker, end_marker, label),
        expected,
        label,
    )


def _a13_sections(raw: bytes) -> dict[str, str]:
    """Decode revision 15 and split its uniquely ordered major sections."""

    _require(
        len(raw) >= REVISION15_BYTE_SIZE
        and _sha256(raw[:REVISION15_BYTE_SIZE]) == REVISION15_SHA256
        and raw[:REVISION15_BYTE_SIZE].endswith(b"\n")
        and raw[DESIGN_BYTE_SIZE:].startswith(AMENDMENT13_BOUNDARY),
        "governing Amendment-13 document violates immutable-prefix law",
    )
    try:
        text = raw[:REVISION15_BYTE_SIZE].decode("utf-8")
    except UnicodeDecodeError as error:
        raise LawError(
            "governing Amendment-13 document is not UTF-8"
        ) from error
    positions: list[int] = []
    for heading in _A13_SECTION_HEADINGS:
        marker = f"{heading}\n"
        _require(text.count(marker) == 1, f"{heading} boundary drift")
        positions.append(text.index(marker))
    _require(
        positions == sorted(positions), "Amendment-13 section order drift"
    )
    sections: dict[str, str] = {}
    for index, heading in enumerate(_A13_SECTION_HEADINGS):
        start = positions[index]
        end = positions[index + 1] if index + 1 < len(positions) else len(text)
        sections[heading.split()[1]] = text[start:end]
    return sections


def _markdown_table(
    section: str,
    header: str,
    separator: str,
    row_count: int,
    label: str,
) -> list[list[str]]:
    """Parse one exact, single-line Markdown table without cell normalization."""

    marker = f"{header}\n{separator}\n"
    remainder = _unique_after(section, marker, label)
    rows: list[list[str]] = []
    for line in remainder.splitlines():
        if not line.startswith("|"):
            break
        _require(line.endswith("|"), f"{label} row shape drift")
        rows.append([cell.strip(" ") for cell in line[1:-1].split("|")])
    expected_columns = len(header[1:-1].split("|"))
    _require(
        len(rows) == row_count
        and all(len(row) == expected_columns for row in rows),
        f"{label} row/column count drift",
    )
    return rows


def _fenced_lines_after(section: str, marker: str, label: str) -> list[str]:
    remainder = _unique_after(section, marker, label)
    _require(remainder.startswith("~~~text\n"), f"{label} fence start drift")
    fenced = remainder[len("~~~text\n") :]
    _require("\n~~~\n" in fenced, f"{label} fence end drift")
    body, _ = fenced.split("\n~~~\n", 1)
    return body.split("\n") if body else []


def _code_after(section: str, marker: str, label: str) -> str:
    remainder = _unique_after(section, marker, label)
    match = re.match(r"\s*`([^`]+)`", remainder)
    _require(match is not None, f"{label} literal drift")
    return match.group(1)


def _code_tokens(cell: str, expected: int, label: str) -> list[str]:
    tokens = re.findall(r"`([^`]*)`", cell)
    _require(len(tokens) == expected, f"{label} token count drift")
    return tokens


def _parse_span(value: str, label: str) -> tuple[int, int]:
    match = re.fullmatch(r"\[(\d+),(\d+)\)", value)
    _require(match is not None, f"{label} span drift")
    start, end = (int(part) for part in match.groups())
    _require(start < end, f"{label} span is empty or reversed")
    return start, end


def _parse_identity_projection(section: str) -> dict[str, Any]:
    """Parse only the surviving historical identity declarations."""

    historical_rows = _markdown_table(
        section,
        "| Identity member | Exact value |",
        "|---|---|",
        7,
        "Amendment-12 historical identity",
    )
    historical_values = {name: value for name, value in historical_rows}
    attestation_rows = _markdown_table(
        section,
        "| Record | Bytes | Raw SHA-256 | Exact first line | Attested candidate HEAD | Attested document bytes / SHA-256 |",
        "|---|---:|---|---|---|---|",
        2,
        "Amendment-12 attestation identities",
    )
    parsed_attestations: list[dict[str, Any]] = []
    for (
        record,
        size,
        raw_sha,
        first_line,
        candidate,
        document,
    ) in attestation_rows:
        document_match = re.fullmatch(r"([\d,]+) / `([0-9a-f]{64})`", document)
        _require(
            document_match is not None,
            "Amendment-12 attestation document identity drift",
        )
        parsed_attestations.append(
            {
                "record_name": _code_tokens(
                    record, 1, "Amendment-12 attestation record"
                )[0],
                "raw_byte_size": int(size.replace(",", "")),
                "raw_sha256": _code_tokens(
                    raw_sha, 1, "Amendment-12 attestation SHA-256"
                )[0],
                "verdict_token": _code_tokens(
                    first_line, 1, "Amendment-12 attestation verdict"
                )[0].removeprefix("# "),
                "attested_candidate_head": _code_tokens(
                    candidate, 1, "Amendment-12 attestation candidate"
                )[0],
                "attested_document_byte_size": int(
                    document_match.group(1).replace(",", "")
                ),
                "attested_document_sha256": document_match.group(2),
            }
        )
    governing_match = re.search(
        r"The actual identity schema is\n`([^`]+)`, with exact status\n"
        r"`([^`]+)` and exactly the keys\n",
        section,
    )
    draft_match = re.search(
        r"values `([^`]+)`,\n`([^`]+)`, and false\.",
        section,
    )
    history_match = re.search(
        r"object has exactly\n`changed_path_count: (\d+)` and\n"
        r"`commit_path_shape_is_identity_condition: (true|false)`\.",
        section,
    )
    bound_status_match = re.search(
        r"use fixture status\n`([^`]+)`, keep both authority",
        section,
    )
    _require(
        governing_match is not None
        and draft_match is not None
        and history_match is not None
        and bound_status_match is not None,
        "historical Amendment-13 identity declarations drift",
    )
    return {
        "amendment12_identity_keys": _code_tokens_between(
            section,
            "object has exactly the eight keys\n",
            ". Its members are\nconjunctive:",
            8,
            "Amendment-12 identity keys",
        ),
        "amendment12_identity": {
            "ratification_commit": _code_tokens(
                historical_values["Ratification commit"],
                1,
                "historical ratification commit",
            )[0],
            "ratification_parents": _code_tokens(
                historical_values["Exact parent array"],
                1,
                "historical parent array",
            ),
            "document_path": _code_tokens(
                historical_values["Document path"],
                1,
                "historical document path",
            )[0],
            "document_mode": _code_tokens(
                historical_values["Tree-entry mode"],
                1,
                "historical document mode",
            )[0],
            "document_blob_oid": _code_tokens(
                historical_values["Git blob OID"],
                1,
                "historical document blob",
            )[0],
            "document_byte_size": int(
                historical_values["Raw byte count"].replace(",", "")
            ),
            "document_sha256": _code_tokens(
                historical_values["Raw SHA-256"],
                1,
                "historical document SHA-256",
            )[0],
            "dual_ratify_attestations": parsed_attestations,
        },
        "amendment12_attestation_keys": _code_tokens_between(
            section,
            "Each `dual_ratify_attestations` member has exactly ",
            ". The candidate HEAD",
            7,
            "Amendment-12 attestation keys",
        ),
        "ratification_history_observation": {
            "changed_path_count": int(history_match.group(1)),
            "commit_path_shape_is_identity_condition": (
                history_match.group(2) == "true"
            ),
        },
        "legacy_governing_identity_schema_version": governing_match.group(1),
        "legacy_governing_identity_status": governing_match.group(2),
        "ratification_bound_template_status": bound_status_match.group(1),
        "draft_placeholder_keys": _code_tokens_between(
            section,
            "exact three-key object ",
            ", with\nvalues ",
            3,
            "governing Amendment-13 draft placeholder keys",
        ),
        "draft_placeholder_values": [
            draft_match.group(1),
            draft_match.group(2),
            False,
        ],
    }


def _parse_overlay_projection(section: str) -> dict[str, Any]:
    """Parse primary annotation, overlay, successor, and supersession law."""

    rows = _markdown_table(
        section,
        "| Doc | Annotation path | Artifact ID | Git blob | Bytes | Raw SHA-256 |",
        "|---:|---|---|---|---:|---|",
        14,
        "Amendment-13 annotation identity domain",
    )
    annotation_rows = []
    for document, path, artifact, blob, size, raw_sha in rows:
        annotation_rows.append(
            {
                "document_source_position": int(document),
                "annotation_path": _code_tokens(path, 1, "annotation path")[0],
                "artifact_id": _code_tokens(
                    artifact, 1, "annotation artifact ID"
                )[0],
                "git_blob_oid": _code_tokens(blob, 1, "annotation Git blob")[
                    0
                ],
                "byte_size": int(size.replace(",", "")),
                "raw_sha256": _code_tokens(
                    raw_sha, 1, "annotation raw SHA-256"
                )[0],
            }
        )
    overlay_retention_match = re.search(
        r"`predecessor_source_rows_retained` is (true|false) and\n"
        r"`predecessor_source_row_erasure_permitted` is (true|false)\.",
        section,
    )
    supersession_retention_match = re.search(
        r"`predecessor_retained` is (true|false); "
        r"`predecessor_erasure_permitted` is (true|false); and\n",
        section,
    )
    _require(
        overlay_retention_match is not None
        and supersession_retention_match is not None,
        "Amendment-13 retention/erasure declarations drift",
    )
    status_mapping_rule_match = re.search(
        r"Proof and fragment successors additionally and obligatorily carry\n"
        r"`([^`]+)`; doc-036 classification successors (forbid|require) it\.",
        section,
    )
    _require(
        status_mapping_rule_match is not None,
        "Amendment-13 successor status-mapping rule drift",
    )
    return {
        "source_tree": _code_after(
            section, "their pinned ", "Amendment-13 source tree"
        ),
        "annotation_mode": _code_after(
            section,
            "The mode for every row is ",
            "Amendment-13 annotation mode",
        ),
        "annotation_rows": annotation_rows,
        "overlay_schema_version": _code_after(
            section,
            "There is exactly one ",
            "Amendment-13 overlay schema",
        ),
        "overlay_keys": _fenced_lines_after(
            section,
            "Every overlay has exactly these keys:\n\n",
            "Amendment-13 overlay keys",
        ),
        "overlay_authority_kind": _code_after(
            section,
            "`authority_kind` is exactly\n",
            "Amendment-13 overlay authority kind",
        ),
        "predecessor_source_rows_retained": (
            overlay_retention_match.group(1) == "true"
        ),
        "predecessor_source_row_erasure_permitted": (
            overlay_retention_match.group(2) == "true"
        ),
        "overlay_id_prefix": _code_after(
            section,
            "Its ID prefix is ",
            "Amendment-13 overlay ID prefix",
        ),
        "overlay_identity_preimage": _fenced_lines_after(
            section,
            "Its ID prefix is `a13-document-repair-overlay:`. The exact ordered ID\npreimage is:\n\n",
            "Amendment-13 overlay identity preimage",
        ),
        "annotation_identity_keys": _code_tokens_between(
            section,
            "`predecessor_annotation_identity` has exactly ",
            ".\n`amendment12_ratification_identity`",
            8,
            "predecessor annotation identity keys",
        ),
        "overlay_integrity_keys": _code_tokens_between(
            section,
            "Overlay `integrity` has\nexactly ",
            ".\n\nEvery repair successor",
            4,
            "overlay integrity keys",
        ),
        "successor_schema_version": _code_after(
            section,
            "Every repair successor has schema\n",
            "Amendment-13 successor schema",
        ),
        "successor_id_prefix": _code_after(
            section,
            "ID prefix\n",
            "Amendment-13 successor ID prefix",
        ),
        "successor_common_keys": _code_tokens_between(
            section,
            "and exactly the common keys\n",
            ".\nProof and fragment successors",
            13,
            "Amendment-13 successor common keys",
        ),
        "successor_status_mapping_key": status_mapping_rule_match.group(1),
        "doc036_status_mapping_forbidden": (
            status_mapping_rule_match.group(2) == "forbid"
        ),
        "successor_identity_preimage": _fenced_lines_after(
            section,
            "The exact ordered successor ID preimage is:\n\n",
            "Amendment-13 successor identity preimage",
        ),
        "supersession_schema_version": _code_after(
            section,
            "Each of the 46 successors has exactly one\n",
            "Amendment-13 supersession schema",
        ),
        "supersession_keys": _code_tokens_between(
            section,
            "edge and no predecessor has two. Its\nexact keyset is ",
            ". Its\nID prefix",
            14,
            "Amendment-13 supersession keys",
        ),
        "supersession_id_prefix": _code_after(
            section,
            "Its\nID prefix is ",
            "Amendment-13 supersession ID prefix",
        ),
        "supersession_relation": _code_after(
            section,
            "; its exact relation is\n",
            "Amendment-13 supersession relation",
        ),
        "supersession_status": _code_after(
            section,
            "; its exact status is\n",
            "Amendment-13 supersession status",
        ),
        "predecessor_retained": (
            supersession_retention_match.group(1) == "true"
        ),
        "predecessor_erasure_permitted": (
            supersession_retention_match.group(2) == "true"
        ),
        "semantic_consumer_selection": _code_after(
            section,
            "`semantic_consumer_selection` is ",
            "Amendment-13 semantic consumer selection",
        ),
        "supersession_identity_preimage": _fenced_lines_after(
            section,
            "Its ordered ID\npreimage is:\n\n",
            "Amendment-13 supersession identity preimage",
        ),
    }


def _parse_proof_projection(section: str) -> dict[str, Any]:
    rows = _markdown_table(
        section,
        "| Doc | Predecessor evidence ID | Exact JSON Pointer | Canonical predecessor-row SHA-256 | Family |",
        "|---:|---|---|---|---|",
        28,
        "Amendment-13 proof mapping",
    )
    family_match = re.search(
        r"For M their exact values are `([^`]+)`, `([^`]+)`, and\s+"
        r"`([^`]+)`; for L they are\s+`([^`]+)`, `([^`]+)`, and\s+"
        r"`([^`]+)`; for D they are\s+`([^`]+)`, `([^`]+)`, and\s+"
        r"`([^`]+)`\.",
        section,
    )
    _require(family_match is not None, "proof status-family mapping drift")
    values = family_match.groups()
    family_mappings = {
        code: {
            "status_family": values[offset],
            "status_field": values[offset + 1],
            "predecessor_status": values[offset + 2],
        }
        for code, offset in (("M", 0), ("L", 3), ("D", 6))
    }
    finding_rows = _markdown_table(
        section,
        "| Code | Count | Exact `predecessor_row_specific_semantic_finding` |",
        "|---|---:|---|",
        6,
        "Amendment-13 proof finding map",
    )
    findings: dict[str, dict[str, Any]] = {}
    for code, count, finding_cell in finding_rows:
        finding = _code_tokens(finding_cell, 1, "proof finding")[0]
        findings[code] = {"count": int(count), "finding": finding}
    selector_lines = _fenced_lines_after(
        section,
        "above; there is no inference, fallback, or artifact lookup:\n\n",
        "Amendment-13 proof finding selector",
    )
    _require(len(selector_lines) == 1, "proof finding selector shape drift")
    selector_text = selector_lines[0]
    _require(
        selector_text.startswith("[") and selector_text.endswith("]"),
        "proof finding selector bracket drift",
    )
    selector = selector_text[1:-1].split(",")
    _require(
        len(selector) == 28 and set(selector) == set(findings),
        "proof finding selector domain drift",
    )
    proof_rows: list[dict[str, Any]] = []
    for row, finding_code in zip(rows, selector, strict=True):
        document, predecessor, pointer, row_sha, family_code = row
        proof_rows.append(
            {
                "document_source_position": int(document),
                "predecessor_row_id": _code_tokens(
                    predecessor, 1, "proof predecessor"
                )[0],
                "predecessor_row_pointer": _code_tokens(
                    pointer, 1, "proof pointer"
                )[0],
                "predecessor_row_canonical_sha256": _code_tokens(
                    row_sha, 1, "proof row SHA-256"
                )[0],
                "predecessor_status_mapping": family_mappings[family_code],
                "predecessor_row_specific_semantic_finding": findings[
                    finding_code
                ]["finding"],
            }
        )
    return {
        "predecessor_id_domain_sha256": _code_after(
            section,
            "canonical\ndomain SHA-256\n",
            "proof predecessor domain SHA-256",
        ),
        "terminal_status": _code_after(
            section,
            "The exact new successor status is\n",
            "proof terminal status",
        ),
        "umbrella_reason_code": _code_after(
            section,
            "The exact new umbrella reason code is\n",
            "proof umbrella reason",
        ),
        "finding_counts": {
            value["finding"]: value["count"] for value in findings.values()
        },
        "rows": proof_rows,
    }


def _parse_fragment_table(section: str) -> list[dict[str, Any]]:
    rows = _markdown_table(
        section,
        "| Doc | Evidence ID / predecessor pointer / row SHA-256 | Instruction occurrence | Exact page, span, page-text SHA-256 | Exact current text / text SHA-256 | Repair |",
        "|---:|---|---|---|---|---|",
        10,
        "Amendment-13 fragment mapping",
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        evidence, pointer, row_sha = _code_tokens(
            row[1], 3, "fragment predecessor identity"
        )
        occurrence = _code_tokens(row[2], 1, "fragment occurrence")[0]
        span, page_sha = _code_tokens(row[3], 2, "fragment page identity")
        page_match = re.match(r"(\d+) `", row[3])
        _require(page_match is not None, "fragment page number drift")
        start, end = _parse_span(span, "fragment occurrence")
        matched_text, text_sha = _code_tokens(
            row[4], 2, "fragment text identity"
        )
        _require(
            row[5] in {"disclosure", "composition"},
            "fragment repair kind drift",
        )
        result.append(
            {
                "document_source_position": int(row[0]),
                "predecessor_row_id": evidence,
                "predecessor_row_pointer": pointer,
                "predecessor_row_canonical_sha256": row_sha,
                "source_occurrence_id": occurrence,
                "page_number": int(page_match.group(1)),
                "utf8_byte_start": start,
                "utf8_byte_end": end,
                "page_text_utf8_sha256": page_sha,
                "matched_text": matched_text,
                "matched_utf8_sha256": text_sha,
                "repair": row[5],
            }
        )
    return result


def _parse_composition_specs(
    section: str,
    fragment_rows: Sequence[Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    selector_rows = _markdown_table(
        section,
        "| Doc | Page / page SHA-256 | Duplicate leading span / text SHA-256 | Selected context occurrence | Rejected field-purpose occurrence | Continuation occurrence |",
        "|---:|---|---|---|---|---|",
        2,
        "Amendment-13 composition selector",
    )
    result: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(selector_rows):
        document = int(row[0])
        page_match = re.match(r"(\d+) / `([0-9a-f]{64})`", row[1])
        _require(page_match is not None, "composition page identity drift")
        span, leading_sha = _code_tokens(
            row[2], 2, "composition leading identity"
        )
        leading_start, leading_end = _parse_span(span, "composition leading")
        selected = _code_tokens(row[3], 1, "selected composition candidate")[0]
        rejected = _code_tokens(row[4], 1, "rejected composition candidate")[0]
        continuation = _code_tokens(row[5], 1, "composition continuation")[0]
        segment_start = section.index(f"For doc {document} the leading text")
        if index + 1 < len(selector_rows):
            next_document = int(selector_rows[index + 1][0])
            segment_end = section.index(
                f"For doc {next_document} the leading text"
            )
        else:
            segment_end = section.index(
                "The complete selector-plus-composition citation objects"
            )
        segment = section[segment_start:segment_end]
        leading_lines = _fenced_lines_after(
            segment,
            f"For doc {document} the leading text is exactly:\n\n",
            f"doc-{document} leading text",
        )
        _require(
            len(leading_lines) == 1, "composition leading text shape drift"
        )
        gap_match = re.search(
            r"The gap is `\[(\d+),(\d+)\)`, exactly LF followed by "
            r"(\d+) ASCII spaces, with\s+SHA-256\s+`([0-9a-f]{64})`\.",
            segment,
        )
        complete_match = re.search(
            r"The complete `\[(\d+),(\d+)\)` slice is (\d+) UTF-8 bytes:\n\n",
            segment,
        )
        _require(
            gap_match is not None and complete_match is not None,
            "composition gap or complete-span law drift",
        )
        complete_lines = _fenced_lines_after(
            segment,
            complete_match.group(0),
            f"doc-{document} combined text",
        )
        combined_text = "\n".join(complete_lines)
        raw_sha_match = re.search(
            r"Its raw SHA-256 is\s+`([0-9a-f]{64})`\.",
            segment,
        )
        _require(raw_sha_match is not None, "composition raw SHA-256 drift")
        continuation_row = next(
            row
            for row in fragment_rows
            if row["document_source_position"] == document
            and row["repair"] == "composition"
        )
        gap_start, gap_end, space_count, gap_sha = gap_match.groups()
        combined_start, combined_end, combined_size = complete_match.groups()
        gap_text = "\n" + " " * int(space_count)
        _require(
            int(gap_start) == leading_end
            and int(gap_end) == continuation_row["utf8_byte_start"]
            and int(combined_start) == leading_start
            and int(combined_end) == continuation_row["utf8_byte_end"]
            and len(combined_text.encode("utf-8")) == int(combined_size),
            "composition coordinate law drift",
        )
        result[document] = {
            "page_number": int(page_match.group(1)),
            "page_text_utf8_sha256": page_match.group(2),
            "candidate_occurrences_in_source_order": [
                {
                    "occurrence_id": selected,
                    "occurrence_kind": "context_anchor",
                },
                {
                    "occurrence_id": rejected,
                    "occurrence_kind": "field_purpose_prompt",
                },
            ],
            "selected_leading_occurrence_id": selected,
            "leading_text": leading_lines[0],
            "leading_utf8_sha256": leading_sha,
            "combined_utf8_byte_start": leading_start,
            "leading_utf8_byte_end": leading_end,
            "gap_utf8_byte_start": int(gap_start),
            "gap_utf8_byte_end": int(gap_end),
            "gap_text": gap_text,
            "gap_utf8_sha256": gap_sha,
            "continuation_occurrence_id": continuation,
            "continuation_utf8_byte_start": continuation_row[
                "utf8_byte_start"
            ],
            "combined_utf8_byte_end": int(combined_end),
            "combined_text": combined_text,
            "combined_utf8_sha256": raw_sha_match.group(1),
        }
    return result


def _parse_fragment_projection(section: str) -> dict[str, Any]:
    rows = _parse_fragment_table(section)
    disclosure_section = section[
        section.index(
            "#### 27.5.2 Eight terminal disclosures"
        ) : section.index("#### 27.5.3 Two exact G75 compositions")
    ]
    composition_section = section[
        section.index("#### 27.5.3 Two exact G75 compositions") :
    ]
    return {
        "evidence_id_domain_sha256": _code_after(
            section,
            "The ordered ten-evidence-ID array has canonical SHA-256\n",
            "fragment evidence domain SHA-256",
        ),
        "instruction_id_domain_sha256": _code_after(
            section,
            "the corresponding ordered instruction-occurrence array has canonical\nSHA-256\n",
            "fragment instruction domain SHA-256",
        ),
        "rows": rows,
        "disclosure_successor_kind": _code_after(
            disclosure_section,
            "Each receives successor kind\n",
            "fragment disclosure successor kind",
        ),
        "disclosure_repair_mode": _code_after(
            disclosure_section,
            "repair mode\n",
            "fragment disclosure repair mode",
        ),
        "disclosure_terminal_status": _code_after(
            disclosure_section,
            "and the new exact status\n",
            "fragment disclosure terminal status",
        ),
        "composition_successor_kind": _code_after(
            composition_section,
            "Only the last two table rows are composable. Their successor kind is\n",
            "fragment composition successor kind",
        ),
        "composition_repair_mode": _code_after(
            composition_section,
            "repair mode is\n",
            "fragment composition repair mode",
        ),
        "composition_terminal_status": _code_after(
            composition_section,
            "and exact status is\n",
            "fragment composition terminal status",
        ),
        "selector_rule": _code_after(
            composition_section,
            "The selector rule is the opaque exact code\n",
            "fragment selector rule",
        ),
        "composition_rule": _code_after(
            composition_section,
            "The exact composition code is\n",
            "fragment composition rule",
        ),
        "composition_specs": _parse_composition_specs(section, rows),
    }


def _parse_doc036_projection(section: str) -> dict[str, Any]:
    """Parse the primary doc-036 transformation and six-era cascade."""

    rows = _markdown_table(
        section,
        "| Classification ID | Pointer / row SHA-256 | Source occurrence | Page/span | Exact text / text SHA-256 |",
        "|---|---|---|---|---|",
        8,
        "Amendment-13 doc-036 mapping",
    )
    doc036_rows: list[dict[str, Any]] = []
    for classification, predecessor, occurrence, page_span, text_sha in rows:
        pointer, row_sha = _code_tokens(
            predecessor, 2, "doc-036 predecessor identity"
        )
        page_match = re.fullmatch(r"(\d+) `([^`]+)`", page_span)
        _require(page_match is not None, "doc-036 page/span drift")
        start, end = _parse_span(page_match.group(2), "doc-036 source span")
        matched_text, matched_sha = _code_tokens(
            text_sha, 2, "doc-036 source text identity"
        )
        doc036_rows.append(
            {
                "predecessor_row_id": _code_tokens(
                    classification, 1, "doc-036 classification ID"
                )[0],
                "predecessor_row_pointer": pointer,
                "predecessor_row_canonical_sha256": row_sha,
                "source_occurrence_id": _code_tokens(
                    occurrence, 1, "doc-036 source occurrence"
                )[0],
                "page_number": int(page_match.group(1)),
                "utf8_byte_start": start,
                "utf8_byte_end": end,
                "matched_text": matched_text,
                "matched_utf8_sha256": matched_sha,
            }
        )

    transformation_match = re.search(
        r"The exact transformation\nis `([^`]+)`; the status is\n`([^`]+)`\.",
        section,
    )
    _require(
        transformation_match is not None,
        "Amendment-13 doc-036 transformation/status drift",
    )
    era_rows = _markdown_table(
        section,
        "| Era | Exact era ID | Incompatible | Incomplete | Composed | Doc-036 | Supersession | Prospective nonauthority seal ID |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
        7,
        "Amendment-13 successor-era census",
    )
    parsed_eras: list[dict[str, Any]] = []
    for row in era_rows[:6]:
        parsed_eras.append(
            {
                "era_order_position": int(row[0]),
                "era_id": _code_tokens(row[1], 1, "successor-era ID")[0],
                "repair_counts": {
                    "semantically_incompatible_local_proof_count": int(row[2]),
                    "incomplete_fragment_terminal_count": int(row[3]),
                    "composed_fragment_count": int(row[4]),
                    "doc036_aggregate_domain_count": int(row[5]),
                    "supersession_count": int(row[6]),
                },
                "successor_era_seal_id": _code_tokens(
                    row[7], 1, "successor-era seal ID"
                )[0],
            }
        )
    total = [
        cell.removeprefix("**").removesuffix("**") for cell in era_rows[6]
    ]
    _require(
        total[0] == "Total" and total[1] == "—" and total[7] == "6 seals",
        "Amendment-13 successor-era total row drift",
    )
    return {
        "classification_id_domain_sha256": _code_after(
            section,
            "members and canonical SHA-256\n",
            "doc-036 classification domain SHA-256",
        ),
        "transformation_rule": transformation_match.group(1),
        "terminal_status": transformation_match.group(2),
        "rows": doc036_rows,
        "era_schema_version": _code_after(
            section,
            "has one\n",
            "successor-era schema version",
        ),
        "era_id_prefix": _code_after(
            section,
            "object with ID prefix\n",
            "successor-era seal ID prefix",
        ),
        "era_keys": _code_tokens_between(
            section,
            "Its exact keys are ",
            ". `repair_counts` has exactly\n",
            14,
            "successor-era seal keys",
        ),
        "repair_count_keys": _code_tokens_between(
            section,
            ". `repair_counts` has exactly\n",
            ". Its ordered ID\npreimage is:",
            5,
            "successor-era repair count keys",
        ),
        "era_identity_preimage": _fenced_lines_after(
            section,
            ". Its ordered ID\npreimage is:\n\n",
            "successor-era seal identity preimage",
        ),
        "era_rows": parsed_eras,
        "era_totals": {
            "semantically_incompatible_local_proof_count": int(total[2]),
            "incomplete_fragment_terminal_count": int(total[3]),
            "composed_fragment_count": int(total[4]),
            "doc036_aggregate_domain_count": int(total[5]),
            "supersession_count": int(total[6]),
            "successor_era_seal_count": 6,
        },
    }


def _parse_scope_projection(section: str) -> dict[str, Any]:
    """Parse scope exclusions, fixture schemas, and domain integrity pins."""

    domain_rows = _markdown_table(
        section,
        "| Domain | Count | Canonical domain SHA-256 |",
        "|---|---:|---|",
        4,
        "Amendment-13 prospective domain pins",
    )
    domains = []
    for name, count, domain_sha in domain_rows:
        domains.append(
            {
                "domain": name,
                "count": int(count),
                "sha256": _code_tokens(
                    domain_sha, 1, "prospective domain SHA-256"
                )[0],
            }
        )
    fixture_match = re.search(
        r"Its exact\nfixture status is `([^`]+)`; both\n"
        r"`authority_emitted` and `certification_emitted` are false\.",
        section,
    )
    _require(
        fixture_match is not None,
        "Amendment-13 fixture status/authority declaration drift",
    )
    return {
        "law_gap_ids": _fenced_lines_after(
            section,
            "member domain:\n\n",
            "Amendment-13 untouched law-gap IDs",
        ),
        "law_gap_id_domain_sha256": _code_after(
            section,
            "Their ordered ID-array domain SHA-256 is\n",
            "Amendment-13 law-gap domain SHA-256",
        ),
        "fixture_status": fixture_match.group(1),
        "authority_emitted": False,
        "certification_emitted": False,
        "top_level_keys": _fenced_lines_after(
            section,
            "24 keys:\n\n",
            "Amendment-13 execution-law top-level keys",
        ),
        "continuation_domain_keys": _code_tokens_between(
            section,
            "`amendment12_continuation_domain` has exactly\n",
            ".\n`source_artifact_identity`",
            9,
            "Amendment-12 continuation-domain keys",
        ),
        "source_artifact_identity_keys": _code_tokens_between(
            section,
            "`source_artifact_identity` has exactly ",
            ".\n`ratification_history_observation`",
            3,
            "Amendment-12 continuation source identity keys",
        ),
        "git_order_keys": _fenced_lines_after(
            section,
            "except `q5_first_add_permitted`, which is false:\n\n",
            "Amendment-13 Git-order keys",
        ),
        "integrity_keys": _code_tokens_between(
            section,
            "`integrity` has exactly ",
            ".\n\nThe complete reconstructed domains",
            18,
            "Amendment-13 integrity keys",
        ),
        "prospective_domain_pins": domains,
        "implementation_pins": _parse_legacy_implementation_pins(section),
        "semantic_mutations": _fenced_lines_after(
            section,
            "Amendment 13 adds a separate exact seven-name inventory:\n\n",
            "Amendment-13 semantic mutation inventory",
        ),
        "enforcement_mutations": _fenced_lines_after(
            section,
            "The enforcement layer has this separate exact six-name inventory:\n\n",
            "Amendment-13 enforcement mutation inventory",
        ),
    }


_LEGACY_IMPLEMENTATION_PIN_PATTERN = re.compile(
    r"The prospective nonauthority validator and focused test are fixed at\n"
    r"implementation commit `(?P<commit>[0-9a-f]{40})`, mode "
    r"`(?P<mode>[0-9]+)`:\n\n"
    r"\| Path \| Git blob \| Bytes \| Raw SHA-256 \|\n"
    r"\|---\|---\|---:\|---\|\n"
    r"\| `scripts/validate_amendment13_execution_law\.py` \| "
    r"`(?P<validator_blob>[0-9a-f]{40})` \| "
    r"(?P<validator_size>[0-9][0-9,]*) \| "
    r"`(?P<validator_sha256>[0-9a-f]{64})` \|\n"
    r"\| `tests/test_validate_amendment13_execution_law\.py` \| "
    r"`(?P<test_blob>[0-9a-f]{40})` \| "
    r"(?P<test_size>[0-9][0-9,]*) \| "
    r"`(?P<test_sha256>[0-9a-f]{64})` \|\n"
)
_LEGACY_IMPLEMENTATION_PIN_VALUE_GROUPS = (
    "commit",
    "mode",
    "validator_blob",
    "validator_size",
    "validator_sha256",
    "test_blob",
    "test_size",
    "test_sha256",
)


def _legacy_implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_LEGACY_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-13 implementation pin block grammar drift",
    )
    return matches[0]


def _parse_legacy_implementation_pins(section: str) -> dict[str, Any]:
    match = _legacy_implementation_pin_match(section)
    return {
        "commit": match.group("commit"),
        "mode": match.group("mode"),
        "files": [
            {
                "path": "scripts/validate_amendment13_execution_law.py",
                "blob_oid": match.group("validator_blob"),
                "byte_size": int(
                    match.group("validator_size").replace(",", "")
                ),
                "sha256": match.group("validator_sha256"),
            },
            {
                "path": "tests/test_validate_amendment13_execution_law.py",
                "blob_oid": match.group("test_blob"),
                "byte_size": int(match.group("test_size").replace(",", "")),
                "sha256": match.group("test_sha256"),
            },
        ],
    }


def _normalize_legacy_implementation_pin_values(section: str) -> str:
    """Normalize only the eight independently authenticated pin values."""

    match = _legacy_implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _LEGACY_IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "implementation pin capture ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


_ACTIVE_IMPLEMENTATION_PIN_PATTERN = re.compile(
    r"The\nactive Amendment-14-governed implementation identity is exactly mode\n"
    r"`(?P<mode>[0-9]+)` and these two path/blob/byte/hash rows:\n\n"
    r"\| Path \| Git blob \| Bytes \| Raw SHA-256 \|\n"
    r"\|---\|---\|---:\|---\|\n"
    r"\| `scripts/validate_amendment13_execution_law\.py` \| "
    r"`(?P<validator_blob>[0-9a-f]{40})` \| "
    r"(?P<validator_size>[0-9][0-9,]*) \| "
    r"`(?P<validator_sha256>[0-9a-f]{64})` \|\n"
    r"\| `tests/test_validate_amendment13_execution_law\.py` \| "
    r"`(?P<test_blob>[0-9a-f]{40})` \| "
    r"(?P<test_size>[0-9][0-9,]*) \| "
    r"`(?P<test_sha256>[0-9a-f]{64})` \|\n"
)
_ACTIVE_IMPLEMENTATION_PIN_VALUE_GROUPS = (
    "mode",
    "validator_blob",
    "validator_size",
    "validator_sha256",
    "test_blob",
    "test_size",
    "test_sha256",
)


def _active_implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_ACTIVE_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-14 implementation pin block grammar drift",
    )
    return matches[0]


def _parse_implementation_pins(section: str) -> dict[str, Any]:
    match = _active_implementation_pin_match(section)
    return {
        "mode": match.group("mode"),
        "files": [
            {
                "path": "scripts/validate_amendment13_execution_law.py",
                "blob_oid": match.group("validator_blob"),
                "byte_size": int(
                    match.group("validator_size").replace(",", "")
                ),
                "sha256": match.group("validator_sha256"),
            },
            {
                "path": "tests/test_validate_amendment13_execution_law.py",
                "blob_oid": match.group("test_blob"),
                "byte_size": int(match.group("test_size").replace(",", "")),
                "sha256": match.group("test_sha256"),
            },
        ],
    }


def _normalize_implementation_pin_values(section: str) -> str:
    """Normalize only the seven active file-pin values."""

    match = _active_implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _ACTIVE_IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "active implementation pin ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


_A15_IMPLEMENTATION_PIN_PATTERN = re.compile(
    r"The active Amendment-15 implementation identity for the Amendment-13/14\n"
    r"semantic validator and the census publisher is exactly mode "
    r"`(?P<mode>[0-9]+)`\n"
    r"and these three path/blob/byte/hash rows:\n\n"
    r"\| Path \| Git blob \| Bytes \| Raw SHA-256 \|\n"
    r"\|---\|---\|---:\|---\|\n"
    r"\| `scripts/validate_amendment13_execution_law\.py` \| "
    r"`(?P<validator_blob>[0-9a-f]{40})` \| "
    r"(?P<validator_size>[0-9][0-9,]*) \| "
    r"`(?P<validator_sha256>[0-9a-f]{64})` \|\n"
    r"\| `tests/test_validate_amendment13_execution_law\.py` \| "
    r"`(?P<test_blob>[0-9a-f]{40})` \| "
    r"(?P<test_size>[0-9][0-9,]*) \| "
    r"`(?P<test_sha256>[0-9a-f]{64})` \|\n"
    r"\| `scripts/build_amendment13_tier2_repairs\.py` \| "
    r"`(?P<publisher_blob>[0-9a-f]{40})` \| "
    r"(?P<publisher_size>[0-9][0-9,]*) \| "
    r"`(?P<publisher_sha256>[0-9a-f]{64})` \|\n"
)
_A15_IMPLEMENTATION_PIN_VALUE_GROUPS = (
    "mode",
    "validator_blob",
    "validator_size",
    "validator_sha256",
    "test_blob",
    "test_size",
    "test_sha256",
    "publisher_blob",
    "publisher_size",
    "publisher_sha256",
)

_A16_IMPLEMENTATION_PIN_PATTERN = re.compile(
    r"The Amendment-16-governed\n"
    r"identity is exactly mode `(?P<mode>[0-9]+)` and these three "
    r"path/blob/byte/hash rows:\n\n"
    r"\| Path \| Git blob \| Bytes \| Raw SHA-256 \|\n"
    r"\|---\|---\|---:\|---\|\n"
    r"\| `scripts/validate_amendment13_execution_law\.py` \| "
    r"`(?P<validator_blob>[0-9a-f]{40})` \| "
    r"(?P<validator_size>[0-9][0-9,]*) \| "
    r"`(?P<validator_sha256>[0-9a-f]{64})` \|\n"
    r"\| `tests/test_validate_amendment13_execution_law\.py` \| "
    r"`(?P<test_blob>[0-9a-f]{40})` \| "
    r"(?P<test_size>[0-9][0-9,]*) \| "
    r"`(?P<test_sha256>[0-9a-f]{64})` \|\n"
    r"\| `scripts/build_amendment13_tier2_repairs\.py` \| "
    r"`(?P<publisher_blob>[0-9a-f]{40})` \| "
    r"(?P<publisher_size>[0-9][0-9,]*) \| "
    r"`(?P<publisher_sha256>[0-9a-f]{64})` \|\n"
)
_A16_IMPLEMENTATION_PIN_VALUE_GROUPS = (
    "mode",
    "validator_blob",
    "validator_size",
    "validator_sha256",
    "test_blob",
    "test_size",
    "test_sha256",
    "publisher_blob",
    "publisher_size",
    "publisher_sha256",
)

_A17_IMPLEMENTATION_PIN_PATTERN = re.compile(
    r"The Amendment-17-governed active identity is exactly mode "
    r"`(?P<mode>[0-9]+)` and these\n"
    r"three path/blob/byte/hash rows:\n\n"
    r"\| Path \| Git blob \| Bytes \| Raw SHA-256 \|\n"
    r"\|---\|---\|---:\|---\|\n"
    r"\| `scripts/validate_amendment13_execution_law\.py` \| "
    r"`(?P<validator_blob>[0-9a-f]{40})` \| "
    r"(?P<validator_size>[0-9][0-9,]*) \| "
    r"`(?P<validator_sha256>[0-9a-f]{64})` \|\n"
    r"\| `tests/test_validate_amendment13_execution_law\.py` \| "
    r"`(?P<test_blob>[0-9a-f]{40})` \| "
    r"(?P<test_size>[0-9][0-9,]*) \| "
    r"`(?P<test_sha256>[0-9a-f]{64})` \|\n"
    r"\| `scripts/build_amendment13_tier2_repairs\.py` \| "
    r"`(?P<publisher_blob>[0-9a-f]{40})` \| "
    r"(?P<publisher_size>[0-9][0-9,]*) \| "
    r"`(?P<publisher_sha256>[0-9a-f]{64})` \|\n"
)
_A17_IMPLEMENTATION_PIN_VALUE_GROUPS = (
    "mode",
    "validator_blob",
    "validator_size",
    "validator_sha256",
    "test_blob",
    "test_size",
    "test_sha256",
    "publisher_blob",
    "publisher_size",
    "publisher_sha256",
)


def _amendment15_text(raw: bytes) -> str:
    _require(
        len(raw) > REVISION16_BYTE_SIZE
        and _sha256(raw[:REVISION16_BYTE_SIZE]) == REVISION16_SHA256
        and _git_blob_oid(raw[:REVISION16_BYTE_SIZE]) == REVISION16_BLOB_OID
        and raw[REVISION16_BYTE_SIZE:].startswith(AMENDMENT15_BOUNDARY)
        and raw.endswith(b"\n"),
        "governing Amendment-15 document violates immutable-prefix law",
    )
    suffix = raw[REVISION16_BYTE_SIZE:]
    if AMENDMENT16_BOUNDARY in suffix:
        _require(
            suffix.count(AMENDMENT16_BOUNDARY) == 1,
            "governing document has an ambiguous Amendment-16 boundary",
        )
        suffix = suffix[: suffix.index(AMENDMENT16_BOUNDARY)]
    try:
        return suffix.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LawError("governing Amendment-15 suffix is not UTF-8") from error


def _amendment15_implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_A15_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-15 implementation pin block grammar drift",
    )
    return matches[0]


def _normalize_amendment15_implementation_pin_values(section: str) -> str:
    """Normalize only the ten independently authenticated A15 pin values."""

    match = _amendment15_implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _A15_IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "Amendment-15 pin capture ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


def _parse_amendment15_implementation_pins(raw: bytes) -> dict[str, Any]:
    section = _amendment15_text(raw)
    match = _amendment15_implementation_pin_match(section)
    return {
        "mode": match.group("mode"),
        "files": [
            {
                "path": "scripts/validate_amendment13_execution_law.py",
                "blob_oid": match.group("validator_blob"),
                "byte_size": int(
                    match.group("validator_size").replace(",", "")
                ),
                "sha256": match.group("validator_sha256"),
            },
            {
                "path": "tests/test_validate_amendment13_execution_law.py",
                "blob_oid": match.group("test_blob"),
                "byte_size": int(match.group("test_size").replace(",", "")),
                "sha256": match.group("test_sha256"),
            },
            {
                "path": "scripts/build_amendment13_tier2_repairs.py",
                "blob_oid": match.group("publisher_blob"),
                "byte_size": int(
                    match.group("publisher_size").replace(",", "")
                ),
                "sha256": match.group("publisher_sha256"),
            },
        ],
    }


def _parse_amendment15_mutation_bindings(
    section: str,
) -> list[dict[str, str]]:
    """Parse the exact design-authoritative Amendment-15 binding table."""

    rows = _markdown_table(
        section,
        (
            "| Mutation name | Preparation callable | Operative gate callable "
            "| Intended exception class | Intended-message substring |"
        ),
        "|---|---|---|---|---|",
        11,
        "Amendment-15 mutation binding specification",
    )
    return [
        {
            "name": _code_tokens(name, 1, "A15 mutation name")[0],
            "prepare": _code_tokens(
                prepare, 1, "A15 mutation preparation callable"
            )[0],
            "gate": _code_tokens(gate, 1, "A15 mutation gate callable")[0],
            "expected_exception": _code_tokens(
                expected_exception,
                1,
                "A15 mutation intended exception class",
            )[0],
            "expected_message": _code_tokens(
                expected_message,
                1,
                "A15 mutation intended-message substring",
            )[0],
        }
        for name, prepare, gate, expected_exception, expected_message in rows
    ]


def _parse_amendment15_projection(raw: bytes) -> dict[str, Any]:
    section = _amendment15_text(raw)
    return {
        "section_semantic_sha256": _sha256(
            _normalize_amendment15_implementation_pin_values(section).encode(
                "utf-8"
            )
        ),
        "implementation_pins": _parse_amendment15_implementation_pins(raw),
        "mutation_bindings": _parse_amendment15_mutation_bindings(section),
    }


def _amendment16_text(raw: bytes) -> str:
    _require(
        len(raw) > REVISION17_BYTE_SIZE
        and _sha256(raw[:REVISION17_BYTE_SIZE]) == REVISION17_SHA256
        and _git_blob_oid(raw[:REVISION17_BYTE_SIZE]) == REVISION17_BLOB_OID
        and raw[REVISION17_BYTE_SIZE:].startswith(AMENDMENT16_BOUNDARY)
        and raw.count(AMENDMENT16_BOUNDARY) == 1
        and raw.endswith(b"\n"),
        "governing Amendment-16 document violates immutable-prefix law",
    )
    suffix = raw[REVISION17_BYTE_SIZE:]
    headings = list(_AMENDMENT_SECTION_PATTERN.finditer(suffix))
    _require(
        headings and int(headings[0].group("amendment")) == 16,
        "governing Amendment-16 boundary sequence drift",
    )
    if len(headings) > 1:
        next_boundary = headings[1].start()
        _require(
            next_boundary > 0
            and suffix[next_boundary - 1 : next_boundary] == b"\n",
            "governing Amendment-16 successor boundary drift",
        )
        suffix = suffix[: next_boundary - 1]
    try:
        return suffix.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LawError("governing Amendment-16 suffix is not UTF-8") from error


def _amendment16_implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_A16_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-16 implementation pin block grammar drift",
    )
    return matches[0]


def _normalize_amendment16_implementation_pin_values(section: str) -> str:
    """Normalize only the ten independently authenticated A16 pin values."""

    match = _amendment16_implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _A16_IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "Amendment-16 pin capture ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


def _parse_amendment16_implementation_pins(raw: bytes) -> dict[str, Any]:
    section = _amendment16_text(raw)
    match = _amendment16_implementation_pin_match(section)
    return {
        "mode": match.group("mode"),
        "files": [
            {
                "path": "scripts/validate_amendment13_execution_law.py",
                "blob_oid": match.group("validator_blob"),
                "byte_size": int(
                    match.group("validator_size").replace(",", "")
                ),
                "sha256": match.group("validator_sha256"),
            },
            {
                "path": "tests/test_validate_amendment13_execution_law.py",
                "blob_oid": match.group("test_blob"),
                "byte_size": int(match.group("test_size").replace(",", "")),
                "sha256": match.group("test_sha256"),
            },
            {
                "path": "scripts/build_amendment13_tier2_repairs.py",
                "blob_oid": match.group("publisher_blob"),
                "byte_size": int(
                    match.group("publisher_size").replace(",", "")
                ),
                "sha256": match.group("publisher_sha256"),
            },
        ],
    }


def _amendment17_text(raw: bytes) -> str:
    _require(
        len(raw) > REVISION18_BYTE_SIZE
        and _sha256(raw[:REVISION18_BYTE_SIZE]) == REVISION18_SHA256
        and _git_blob_oid(raw[:REVISION18_BYTE_SIZE]) == REVISION18_BLOB_OID
        and raw[REVISION18_BYTE_SIZE:].startswith(AMENDMENT17_BOUNDARY)
        and raw.count(AMENDMENT17_BOUNDARY) == 1
        and raw.endswith(b"\n"),
        "governing Amendment-17 document violates immutable-prefix law",
    )
    suffix = raw[REVISION18_BYTE_SIZE:]
    headings = list(_AMENDMENT_SECTION_PATTERN.finditer(suffix))
    _require(
        headings and int(headings[0].group("amendment")) == 17,
        "governing Amendment-17 boundary sequence drift",
    )
    if len(headings) > 1:
        next_boundary = headings[1].start()
        _require(
            next_boundary > 0
            and suffix[next_boundary - 1 : next_boundary] == b"\n",
            "governing Amendment-17 successor boundary drift",
        )
        suffix = suffix[: next_boundary - 1]
    try:
        return suffix.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LawError("governing Amendment-17 suffix is not UTF-8") from error


def _amendment17_implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_A17_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-17 implementation pin block grammar drift",
    )
    return matches[0]


def _normalize_amendment17_implementation_pin_values(section: str) -> str:
    """Normalize only the ten independently authenticated A17 pin values."""

    match = _amendment17_implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _A17_IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "Amendment-17 pin capture ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


def _parse_amendment17_implementation_pins(raw: bytes) -> dict[str, Any]:
    section = _amendment17_text(raw)
    match = _amendment17_implementation_pin_match(section)
    return {
        "mode": match.group("mode"),
        "files": [
            {
                "path": "scripts/validate_amendment13_execution_law.py",
                "blob_oid": match.group("validator_blob"),
                "byte_size": int(
                    match.group("validator_size").replace(",", "")
                ),
                "sha256": match.group("validator_sha256"),
            },
            {
                "path": "tests/test_validate_amendment13_execution_law.py",
                "blob_oid": match.group("test_blob"),
                "byte_size": int(match.group("test_size").replace(",", "")),
                "sha256": match.group("test_sha256"),
            },
            {
                "path": "scripts/build_amendment13_tier2_repairs.py",
                "blob_oid": match.group("publisher_blob"),
                "byte_size": int(
                    match.group("publisher_size").replace(",", "")
                ),
                "sha256": match.group("publisher_sha256"),
            },
        ],
    }


def _parse_a17_executed_transition_obligation(
    section: str,
) -> dict[str, Any]:
    scope_match = re.search(
        r"For (?P<scope>Amendment 17 and every future activation-affecting "
        r"amendment), the\nfollowing is a \*\*RATIFICATION OBLIGATION\*\*\.",
        section,
    )
    ambiguity_match = re.search(
        r"Ambiguity is\nactivation-affecting and (?P<disposition>fails "
        r"closed into this obligation)\.",
        section,
    )
    failure_match = re.search(
        r"unverified demonstration makes the amendment "
        r"(?P<disposition>[a-z]+)\.",
        section,
    )
    _require(
        scope_match is not None
        and ambiguity_match is not None
        and failure_match is not None,
        "Amendment-17 executed-transition obligation grammar drift",
    )
    ratification_verdict = _code_after(
        section,
        "following is a **RATIFICATION OBLIGATION**. Before either referee "
        "may emit\n",
        "Amendment-17 ratification verdict",
    )
    authority = _code_after(
        section,
        "repository. The simulation is permanently ",
        "Amendment-17 simulated-state authority",
    )
    public_entrypoint = _code_after(
        section,
        "1. the unmodified public ",
        "Amendment-17 public entrypoint",
    )
    battery_path = _code_after(
        section,
        "2. the entire selected ",
        "Amendment-17 full pinned battery path",
    )
    _require(
        section.count(
            "Against one identical simulated-state identity it shall "
            "execute, in order:\n"
        )
        == 1
        and section.count(
            "with every ordinary Git, artifact, closure, design, and "
            "implementation-pin\n   verification enabled"
        )
        == 1,
        "Amendment-17 same-state execution rule drift",
    )
    return {
        "scope": scope_match.group("scope"),
        "ambiguity_disposition": ambiguity_match.group("disposition"),
        "ratification_verdict": ratification_verdict,
        "invalid_demonstration_disposition": failure_match.group(
            "disposition"
        ),
        "simulated_state_authority": authority,
        "execution_order": [public_entrypoint, battery_path],
        "same_state_required": True,
        "implementation_pin_verification_required": True,
    }


def _parse_a17_receipt_schema(section: str) -> dict[str, Any]:
    schema = {
        "top_level_keys": _fenced_lines_after(
            section,
            "receipt has exactly these six top-level keys:\n\n",
            "Amendment-17 receipt top-level keys",
        ),
        "manifest_keys": _fenced_lines_after(
            section,
            "Its `simulated_state_manifest` has exactly these seven "
            "keys:\n\n",
            "Amendment-17 simulated-state manifest keys",
        ),
        "manifest_schema_version": _code_after(
            section,
            "The manifest's `schema_version` is exactly\n",
            "Amendment-17 manifest schema version",
        ),
        "manifest_authority": _code_after(
            section,
            "and its `simulated_state_authority` is\nexactly ",
            "Amendment-17 manifest authority",
        ),
        "closure_identity_keys": _fenced_lines_after(
            section,
            "Each closure identity has exactly these four keys:\n\n",
            "Amendment-17 closure identity keys",
        ),
        "test_identity_keys": _fenced_lines_after(
            section,
            "The `full_pinned_battery_test_identity` has exactly these five "
            "keys:\n\n",
            "Amendment-17 test identity keys",
        ),
        "public_oracle_keys": _fenced_lines_after(
            section,
            "The `public_oracle` object has exactly these five keys:\n\n",
            "Amendment-17 public-oracle keys",
        ),
        "full_pinned_battery_keys": _fenced_lines_after(
            section,
            "The `full_pinned_battery` object has exactly these thirteen "
            "keys:\n\n",
            "Amendment-17 full-pinned-battery keys",
        ),
        "integer_fields": _fenced_lines_after(
            section,
            "booleans, and the exit codes and five nonpassing outcome counts "
            "are exactly\nzero:\n\n",
            "Amendment-17 receipt integer fields",
        ),
        "closed_without_defaults_or_extra_keys": True,
        "canonicalization": (
            "ascii_json_sorted_keys_no_insignificant_whitespace_"
            "no_nonfinite_values_one_terminal_lf"
        ),
        "nested_state_identities_equal_top_level": True,
    }
    _require(
        section.count(
            "Every key set above is closed: no key may be omitted or "
            "defaulted, and no\nadditional key is permitted."
        )
        == 1
        and section.count(
            "as ASCII JSON with keys sorted, no insignificant whitespace, "
            "no nonfinite\nvalues, and one terminal LF."
        )
        == 1
        and section.count(
            "The two nested state-identity values must equal\nthe top-level "
            "value."
        )
        == 1,
        "Amendment-17 exact receipt closure or identity rule drift",
    )
    return schema


def _parse_a17_transition_registry_binding(section: str) -> dict[str, Any]:
    rows = _markdown_table(
        section,
        "| Binding member | Exact value |",
        "|---|---|",
        4,
        "Amendment-17 transition registry binding",
    )
    values = {name: value for name, value in rows}
    _require(
        tuple(values)
        == ("`path`", "`ratification_commit`", "`revision`", "`blob_sha256`"),
        "Amendment-17 transition registry binding order drift",
    )
    return {
        "path": _code_tokens(values["`path`"], 1, "A17 design path")[0],
        "ratification_commit": _code_tokens(
            values["`ratification_commit`"],
            1,
            "A17 transition ratification commit",
        )[0],
        "revision": int(
            _code_tokens(
                values["`revision`"],
                1,
                "A17 transition revision",
            )[0]
        ),
        "blob_sha256": _code_tokens(
            values["`blob_sha256`"],
            1,
            "A17 transition design SHA-256",
        )[0],
    }


def _parse_a17_transition_closure_identities(
    section: str,
) -> list[dict[str, Any]]:
    rows = _markdown_table(
        section,
        "| Amendment | Exact path | Bytes | Raw SHA-256 | Git blob |",
        "|---:|---|---:|---|---|",
        4,
        "Amendment-17 transition closure identities",
    )
    identities = [
        {
            "amendment_number": int(amendment_number),
            "path": _code_tokens(path, 1, "A17 closure path")[0],
            "raw_byte_size": int(byte_size.replace(",", "")),
            "raw_sha256": _code_tokens(
                raw_sha256,
                1,
                "A17 closure SHA-256",
            )[0],
            "git_blob": _code_tokens(git_blob, 1, "A17 closure blob")[0],
        }
        for amendment_number, path, byte_size, raw_sha256, git_blob in rows
    ]
    _require(
        [row["amendment_number"] for row in identities] == [13, 14, 15, 16],
        "Amendment-17 transition closure order drift",
    )
    return identities


def _parse_a17_transition_verdict_artifacts(
    section: str,
) -> list[dict[str, Any]]:
    block = _unique_between(
        section,
        "The A16 closure binds\n",
        "Their canonical closure identities",
        "Amendment-17 transition verdict artifacts",
    )
    matches = re.findall(
        r"(?:the exact|and the exact) (?P<size>[0-9][0-9,]*)-byte\n"
        r"`(?P<path>[^`]+)`\nwith raw SHA-256\n"
        r"`(?P<raw_sha256>[0-9a-f]{64})`",
        block,
    )
    _require(
        len(matches) == 2,
        "Amendment-17 transition verdict identity grammar drift",
    )
    return [
        {
            "path": path,
            "byte_size": int(size.replace(",", "")),
            "raw_sha256": raw_sha256,
        }
        for size, path, raw_sha256 in matches
    ]


def _parse_a17_required_public_output(section: str) -> list[int]:
    serialized = _code_after(
        section,
        "The required public output is ordered ",
        "Amendment-17 required public output",
    )
    match = re.fullmatch(r"\(([0-9]+(?:, [0-9]+)*)\)", serialized)
    _require(match is not None, "Amendment-17 public output tuple drift")
    return [int(value) for value in match.group(1).split(", ")]


def _parse_a17_full_pinned_battery(
    section: str,
    obligation: Mapping[str, Any],
) -> dict[str, Any]:
    match = re.search(
        r"The required full\ncorrected battery result is all "
        r"(?P<count>[0-9]+) tests collected from the exact §31\.2\.2 test\n"
        r"file passing against that same revision-18 state, with zero "
        r"failed, skipped,\ndeselected, xfailed, or xpassed tests\.",
        section,
    )
    _require(
        match is not None
        and section.count(
            "verification enabled, and require exit zero plus the exact "
            "post-activation"
        )
        == 1
        and section.count("battery against that same simulated registry") == 1
        and section.count("`HEAD`, with exit zero") == 1,
        "Amendment-17 full pinned battery rule drift",
    )
    count = int(match.group("count"))
    return {
        "test_path": obligation["execution_order"][1],
        "exit_code": 0,
        "collected": count,
        "passed": count,
        "failed": 0,
        "skipped": 0,
        "deselected": 0,
        "xfailed": 0,
        "xpassed": 0,
    }


def _parse_a17_mutation_census(section: str) -> dict[str, Any]:
    inherited = re.search(
        r"exact (?P<count>[0-9]+)-name inherited census with\naggregate "
        r"digest\n`(?P<digest>[0-9a-f]{64})`\.",
        section,
    )
    amendment16 = re.search(
        r"The (?P<count>seven) A16 attacks remain separate, ordered, and "
        r"unchanged with digest\n`(?P<digest>[0-9a-f]{64})`\.",
        section,
    )
    _require(
        inherited is not None and amendment16 is not None,
        "Amendment-17 inherited mutation census grammar drift",
    )
    return {
        "inherited_complete_mutation_count": int(inherited.group("count")),
        "inherited_complete_mutation_domain_sha256": inherited.group("digest"),
        "amendment16_mutation_count": {"seven": 7}[amendment16.group("count")],
        "amendment16_mutation_domain_sha256": amendment16.group("digest"),
    }


def _parse_amendment17_projection(raw: bytes) -> dict[str, Any]:
    section = _amendment17_text(raw)
    obligation = _parse_a17_executed_transition_obligation(section)
    mutations = _fenced_lines_after(
        section,
        "The separate Amendment-17 test/ceremony mutation inventory is "
        "exactly:\n\n",
        "Amendment-17 test and ceremony mutations",
    )
    mutation_digest = _code_after(
        section,
        "Its ordered canonical name-array SHA-256 is\n",
        "Amendment-17 mutation domain SHA-256",
    )
    _require(
        _sha256(canonical_json_bytes(mutations)) == mutation_digest,
        "Amendment-17 mutation name-array digest drift",
    )
    return {
        "section_semantic_sha256": _sha256(
            _normalize_amendment17_implementation_pin_values(section).encode(
                "utf-8"
            )
        ),
        "implementation_pins": _parse_amendment17_implementation_pins(raw),
        "revision_domain_rules": _fenced_lines_after(
            section,
            "test independently derives the expected ordered operative "
            "domain as:\n\n",
            "Amendment-17 revision-domain rules",
        ),
        "executed_transition_obligation": obligation,
        "receipt_schema": _parse_a17_receipt_schema(section),
        "transition_registry_binding": (
            _parse_a17_transition_registry_binding(section)
        ),
        "transition_closure_identities": (
            _parse_a17_transition_closure_identities(section)
        ),
        "transition_verdict_artifacts": (
            _parse_a17_transition_verdict_artifacts(section)
        ),
        "required_public_output": _parse_a17_required_public_output(section),
        "full_pinned_battery": _parse_a17_full_pinned_battery(
            section,
            obligation,
        ),
        "test_ceremony_mutations": mutations,
        "test_ceremony_mutation_domain_sha256": mutation_digest,
        "mutation_census": _parse_a17_mutation_census(section),
        "supersession_map": _markdown_table(
            section,
            "| Earlier normative anchor | Amendment-17 disposition |",
            "|---|---|",
            5,
            "Amendment-17 supersession map",
        ),
    }


def _parse_active_implementation_pins(raw: bytes) -> dict[str, Any]:
    """Select the newest append-only implementation-pin successor."""

    if len(raw) > REVISION18_BYTE_SIZE:
        return _parse_amendment17_implementation_pins(raw)
    if len(raw) > REVISION17_BYTE_SIZE:
        return _parse_amendment16_implementation_pins(raw)
    if len(raw) > REVISION16_BYTE_SIZE:
        return _parse_amendment15_implementation_pins(raw)
    return _parse_amendment14_projection(raw)["implementation_pins"]


def _parse_amendment16_law_values(section: str) -> dict[str, Any]:
    lines = _fenced_lines_after(
        section,
        "The A16 projection exact-parses and independently compares at least "
        "these\nenacted values:\n\n",
        "Amendment-16 ratification law values",
    )
    expected_names = tuple(A16_RATIFICATION_LAW_VALUES)
    _require(
        len(lines) == len(expected_names),
        "Amendment-16 ratification law value count drift",
    )
    values: dict[str, Any] = {}
    for expected_name, line in zip(expected_names, lines, strict=True):
        _require(" = " in line, "Amendment-16 ratification law row drift")
        name, serialized = line.split(" = ", 1)
        _require(
            name == expected_name,
            "Amendment-16 ratification law value order drift",
        )
        if serialized.startswith("["):
            try:
                value = json.loads(serialized)
            except json.JSONDecodeError as error:
                raise LawError(
                    "Amendment-16 ratification law array drift"
                ) from error
        elif serialized.isdigit():
            value = int(serialized)
        else:
            value = serialized
        values[name] = value
    return values


def _parse_a16_verdict_artifacts(section: str) -> list[dict[str, Any]]:
    rows = _markdown_table(
        section,
        "| Path | Bytes | Raw SHA-256 |",
        "|---|---:|---|",
        2,
        "Amendment-15 verdict identities in Amendment 16",
    )
    return [
        {
            "path": _code_tokens(path, 1, "A15 verdict path")[0],
            "byte_size": int(size.replace(",", "")),
            "raw_sha256": _code_tokens(raw_sha, 1, "A15 verdict SHA-256")[0],
        }
        for path, size, raw_sha in rows
    ]


def _parse_a14_historical_binding_from_a16(section: str) -> dict[str, Any]:
    rows = _markdown_table(
        section,
        "| Historical closure | Exact path | Bytes | Raw SHA-256 |",
        "|---|---|---:|---|",
        1,
        "Amendment-14 historical closure binding in Amendment 16",
    )
    label, path, size, raw_sha = rows[0]
    _require(
        label == "Amendment 14",
        "Amendment-14 historical closure label drift",
    )
    return {
        "path": _code_tokens(path, 1, "historical A14 closure path")[0],
        "raw_byte_size": int(size.replace(",", "")),
        "raw_sha256": _code_tokens(
            raw_sha,
            1,
            "historical A14 closure SHA-256",
        )[0],
    }


def _parse_a15_expected_closure_from_a16(
    section: str,
    verdict_artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = _markdown_table(
        section,
        "| Closure member | Exact value |",
        "|---|---|",
        8,
        "Amendment-15 closure values in Amendment 16",
    )
    values = {name: value for name, value in rows}
    _require(
        values["`verdict_artifacts`"]
        == "the exact two ordered §30.3.2 path/byte/SHA objects",
        "Amendment-15 closure verdict reference drift",
    )
    return {
        "amendment_number": int(
            _code_tokens(
                values["`amendment_number`"],
                1,
                "A15 closure amendment number",
            )[0]
        ),
        "attested_candidate_design_blob_oid": _code_tokens(
            values["`attested_candidate_design_blob_oid`"],
            1,
            "A15 closure design blob",
        )[0],
        "attested_candidate_design_byte_size": int(
            _code_tokens(
                values["`attested_candidate_design_byte_size`"],
                1,
                "A15 closure design size",
            )[0]
        ),
        "attested_candidate_design_raw_sha256": _code_tokens(
            values["`attested_candidate_design_raw_sha256`"],
            1,
            "A15 closure design SHA-256",
        )[0],
        "ratification_commit": _code_tokens(
            values["`ratification_commit`"],
            1,
            "A15 closure ratification commit",
        )[0],
        "ratification_commit_sole_parent": _code_tokens(
            values["`ratification_commit_sole_parent`"],
            1,
            "A15 closure ratification parent",
        )[0],
        "operator_merge_commit": _code_tokens(
            values["`operator_merge_commit`"],
            1,
            "A15 closure operator merge",
        )[0],
        "verdict_artifacts": [dict(row) for row in verdict_artifacts],
    }


def _parse_a16_historical_r05_binding(section: str) -> dict[str, Any]:
    lines = _fenced_lines_after(
        section,
        "The serialized member remains historical Amendment-15 material:\n\n",
        "Amendment-16 historical R05 binding",
    )
    expected_names = tuple(A16_HISTORICAL_R05_BINDING)
    _require(
        len(lines) == len(expected_names),
        "Amendment-16 historical R05 binding count drift",
    )
    binding: dict[str, Any] = {}
    for expected_name, line in zip(expected_names, lines, strict=True):
        _require(" = " in line, "Amendment-16 historical R05 row drift")
        name, value = line.split(" = ", 1)
        _require(
            name == expected_name,
            "Amendment-16 historical R05 binding order drift",
        )
        binding[name] = int(value) if value.isdigit() else value
    return binding


def _parse_amendment16_projection(raw: bytes) -> dict[str, Any]:
    section = _amendment16_text(raw)
    verdict_artifacts = _parse_a16_verdict_artifacts(section)
    oracle_mutations = _fenced_lines_after(
        section,
        "The Amendment-16 operativity enforcement inventory is exactly:\n\n",
        "Amendment-16 oracle mutations",
    )
    mutation_digest = _code_after(
        section,
        "The ordered canonical name-array domain SHA-256 is\n",
        "Amendment-16 oracle mutation digest",
    )
    _require(
        _sha256(canonical_json_bytes(oracle_mutations)) == mutation_digest,
        "Amendment-16 oracle mutation name-array digest drift",
    )
    projection = {
        "section_semantic_sha256": _sha256(
            _normalize_amendment16_implementation_pin_values(section).encode(
                "utf-8"
            )
        ),
        "ratification_law_values": _parse_amendment16_law_values(section),
        "ordered_domain_expression": _code_after(
            section,
            "ordered closure domain is every integer amendment\nnumber in "
            "Python's half-open ",
            "Amendment-16 ordered domain expression",
        ),
        "generated_closure_path_rule": _code_after(
            section,
            "zero based, is Amendment `13 + i`; its generated path is\n",
            "Amendment-16 generated closure path rule",
        ),
        "combined_closure_paths": _fenced_lines_after(
            section,
            "The next lawful repin selects revision 18 and binds exactly "
            "these four ordered\npaths:\n\n",
            "Amendment-16 combined closure paths",
        ),
        "a14_historical_closure_binding": (
            _parse_a14_historical_binding_from_a16(section)
        ),
        "a15_verdict_artifacts": verdict_artifacts,
        "a15_expected_closure": _parse_a15_expected_closure_from_a16(
            section, verdict_artifacts
        ),
        "ratification_sequence": _fenced_lines_after(
            section,
            "The combined sequence is:\n\n",
            "Amendment-16 ratification sequence",
        ),
        "historical_r05_binding": _parse_a16_historical_r05_binding(section),
        "implementation_pins": _parse_amendment16_implementation_pins(raw),
        "oracle_mutations": oracle_mutations,
        "oracle_mutation_domain_sha256": mutation_digest,
        "supersession_map": _markdown_table(
            section,
            "| Earlier normative anchor | Amendment-16 disposition |",
            "|---|---|",
            11,
            "Amendment-16 supersession map",
        ),
        "schema_operation_identifiers": _fenced_lines_after(
            section,
            "The exact Amendment-16 schema and operation identifiers are:\n\n",
            "Amendment-16 schema and operation identifiers",
        ),
        "status_identifiers": _fenced_lines_after(
            section,
            "The exact Amendment-16 status identifiers are:\n\n",
            "Amendment-16 status identifiers",
        ),
        "python_identifiers": _fenced_lines_after(
            section,
            "The exact new public/private Python identifiers are:\n\n",
            "Amendment-16 Python identifiers",
        ),
    }
    inventories = (
        projection["schema_operation_identifiers"],
        projection["status_identifiers"],
        projection["python_identifiers"],
    )
    _require(
        all(len(values) == len(set(values)) for values in inventories)
        and set(inventories[0]).isdisjoint(inventories[1])
        and set(inventories[0]).isdisjoint(inventories[2])
        and set(inventories[1]).isdisjoint(inventories[2]),
        "Amendment-16 enacted identifier inventory consistency drift",
    )
    return projection


def _amendment14_text(raw: bytes) -> str:
    _require(
        len(raw) > REVISION15_BYTE_SIZE
        and _sha256(raw[:REVISION15_BYTE_SIZE]) == REVISION15_SHA256
        and raw[REVISION15_BYTE_SIZE:].startswith(AMENDMENT14_BOUNDARY)
        and raw.endswith(b"\n"),
        "governing Amendment-14 document violates immutable-prefix law",
    )
    suffix = raw[REVISION15_BYTE_SIZE:]
    if AMENDMENT15_BOUNDARY in suffix:
        _require(
            suffix.count(AMENDMENT15_BOUNDARY) == 1,
            "governing document has an ambiguous Amendment-15 boundary",
        )
        suffix = suffix[: suffix.index(AMENDMENT15_BOUNDARY)]
    try:
        return suffix.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LawError("governing Amendment-14 suffix is not UTF-8") from error


def _parse_a14_verdict_artifacts(section: str) -> list[dict[str, Any]]:
    rows = _markdown_table(
        section,
        "| Path | Bytes | Raw SHA-256 |",
        "|---|---:|---|",
        2,
        "Amendment-13 verdict identities",
    )
    return [
        {
            "path": _code_tokens(path, 1, "A13 verdict path")[0],
            "byte_size": int(size.replace(",", "")),
            "raw_sha256": _code_tokens(raw_sha, 1, "A13 verdict SHA-256")[0],
        }
        for path, size, raw_sha in rows
    ]


def _parse_a13_expected_closure(
    section: str,
    verdict_artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = _markdown_table(
        section,
        "| Closure member | Exact value |",
        "|---|---|",
        8,
        "Amendment-13 closure values",
    )
    values = {name: value for name, value in rows}
    _require(
        values["`verdict_artifacts`"]
        == "the exact two ordered \u00a728.3.1 path/byte/SHA objects",
        "Amendment-13 closure verdict reference drift",
    )
    return {
        "amendment_number": int(
            _code_tokens(
                values["`amendment_number`"],
                1,
                "A13 closure amendment number",
            )[0]
        ),
        "attested_candidate_design_blob_oid": _code_tokens(
            values["`attested_candidate_design_blob_oid`"],
            1,
            "A13 closure design blob",
        )[0],
        "attested_candidate_design_byte_size": int(
            _code_tokens(
                values["`attested_candidate_design_byte_size`"],
                1,
                "A13 closure design size",
            )[0]
        ),
        "attested_candidate_design_raw_sha256": _code_tokens(
            values["`attested_candidate_design_raw_sha256`"],
            1,
            "A13 closure design SHA-256",
        )[0],
        "ratification_commit": _code_tokens(
            values["`ratification_commit`"],
            1,
            "A13 closure ratification commit",
        )[0],
        "ratification_commit_sole_parent": _code_tokens(
            values["`ratification_commit_sole_parent`"],
            1,
            "A13 closure ratification parent",
        )[0],
        "operator_merge_commit": _code_tokens(
            values["`operator_merge_commit`"],
            1,
            "A13 closure operator merge",
        )[0],
        "verdict_artifacts": [dict(row) for row in verdict_artifacts],
    }


def _parse_amendment14_projection(raw: bytes) -> dict[str, Any]:
    section = _amendment14_text(raw)
    verdict_artifacts = _parse_a14_verdict_artifacts(section)
    projection = {
        "section_semantic_sha256": _sha256(
            _normalize_implementation_pin_values(section).encode()
        ),
        "closure_top_level_keys": _fenced_lines_after(
            section,
            "eight top-level keys in canonical sorted-key serialization:\n\n",
            "Amendment-14 closure top-level keys",
        ),
        "closure_verdict_keys": _fenced_lines_after(
            section,
            "object has exactly these three keys:\n\n",
            "Amendment-14 closure verdict keys",
        ),
        "registry_closure_binding_keys": _fenced_lines_after(
            section,
            "Each row has exactly:\n\n",
            "Amendment-14 registry closure binding keys",
        ),
        "a13_verdict_artifacts": verdict_artifacts,
        "a13_expected_closure": _parse_a13_expected_closure(
            section, verdict_artifacts
        ),
        "ratification_sequence": _fenced_lines_after(
            section,
            "The exact Amendment-14 sequence is:\n\n",
            "Amendment-14 ratification sequence",
        ),
        "implementation_pins": _parse_implementation_pins(section),
        "semantic_mutations": _fenced_lines_after(
            section,
            "Amendment 13's exact seven semantic mutations survive unchanged:\n\n",
            "Amendment-14 semantic mutations",
        ),
        "enforcement_mutations": _fenced_lines_after(
            section,
            "The Amendment-14 enforcement inventory is exactly:\n\n",
            "Amendment-14 enforcement mutations",
        ),
        "removed_mutations": _fenced_lines_after(
            section,
            "Two predecessor enforcement mutations are removed:\n\n",
            "Amendment-14 removed mutations",
        ),
        "schema_binding_identifiers": _fenced_lines_after(
            section,
            "The exact Amendment-14 schema and binding identifiers are:\n\n",
            "Amendment-14 schema and binding identifiers",
        ),
        "path_templates": _fenced_lines_after(
            section,
            "The exact Amendment-14 path templates are:\n\n",
            "Amendment-14 path templates",
        ),
        "status_operation_identifiers": _fenced_lines_after(
            section,
            "The exact Amendment-14 status and operation identifiers are:\n\n",
            "Amendment-14 status and operation identifiers",
        ),
    }
    _validate_a14_identifier_inventory(projection)
    return projection


def _validate_a14_identifier_inventory(
    projection: Mapping[str, Any],
) -> None:
    inventories = (
        projection["schema_binding_identifiers"],
        projection["path_templates"],
        projection["status_operation_identifiers"],
    )
    _require(
        tuple(inventories[0]) == A14_SCHEMA_BINDING_IDENTIFIERS
        and tuple(inventories[1]) == A14_PATH_TEMPLATES
        and tuple(inventories[2]) == A14_STATUS_OPERATION_IDENTIFIERS
        and all(len(values) == len(set(values)) for values in inventories)
        and set(inventories[0]).isdisjoint(inventories[1])
        and set(inventories[0]).isdisjoint(inventories[2])
        and set(inventories[1]).isdisjoint(inventories[2]),
        "Amendment-14 enacted identifier inventory consistency drift",
    )


def _parse_comparator_and_literals(section: str) -> dict[str, Any]:
    comparator_rows = _markdown_table(
        section,
        "| ID | Exact anchor | Prospective revision-15 disposition |",
        "|---|---|---|",
        6,
        "Amendment-13 comparator rows",
    )
    return {
        "search_augmentation": _fenced_lines_after(
            section,
            "The Amendment-13 search augmentation is this case-sensitive ordered array:\n\n",
            "Amendment-13 search augmentation",
        ),
        "comparator_rows": comparator_rows,
        "schema_literals": _fenced_lines_after(
            section,
            "The exact new schema-version literals are:\n\n",
            "Amendment-13 schema literals",
        ),
        "content_id_prefixes": _fenced_lines_after(
            section,
            "The exact new content-ID prefixes are:\n\n",
            "Amendment-13 content-ID prefixes",
        ),
        "status_relation_operation_codes": _fenced_lines_after(
            section,
            "The exact new status/relation/operation codes are:\n\n",
            "Amendment-13 status/relation/operation codes",
        ),
        "successor_kind_literals": _fenced_lines_after(
            section,
            "The exact serialized successor-kind literals are:\n\n",
            "Amendment-13 successor kinds",
        ),
    }


def _section_semantic_sha256s(
    sections: Mapping[str, str],
) -> dict[str, str]:
    """Bind every suffix byte, excluding only the separately verified pins."""

    result: dict[str, str] = {}
    for section_name in (
        "27.2",
        "27.3",
        "27.4",
        "27.5",
        "27.6",
        "27.7",
        "27.8",
    ):
        semantic_text = sections[section_name]
        if section_name == "27.7":
            semantic_text = _normalize_legacy_implementation_pin_values(
                semantic_text
            )
        result[section_name] = _sha256(semantic_text.encode("utf-8"))
    return result


def _validate_identifier_inventory_consistency(
    projection: Mapping[str, Any],
) -> None:
    """Require the surviving Amendment-13 inventories to remain exact."""

    comparator = projection["comparator"]
    schemas = comparator["schema_literals"]
    statuses = comparator["status_relation_operation_codes"]
    _require(
        tuple(schemas) == A13_SCHEMA_LITERALS
        and tuple(statuses) == A13_STATUS_RELATION_OPERATION_CODES
        and len(schemas) == len(set(schemas))
        and len(statuses) == len(set(statuses)),
        "Amendment-13 enacted identifier inventory consistency drift",
    )


def _parse_document_semantic_projection(raw: bytes) -> dict[str, Any]:
    """Derive the canonical enforced projection from the governing bytes."""

    sections = _a13_sections(raw)
    projection = {
        "section_semantic_sha256": _section_semantic_sha256s(sections),
        "identity": _parse_identity_projection(sections["27.2"]),
        "overlays": _parse_overlay_projection(sections["27.3"]),
        "proof": _parse_proof_projection(sections["27.4"]),
        "fragments": _parse_fragment_projection(sections["27.5"]),
        "doc036": _parse_doc036_projection(sections["27.6"]),
        "scope": _parse_scope_projection(sections["27.7"]),
        "comparator": _parse_comparator_and_literals(sections["27.8"]),
        "amendment14": _parse_amendment14_projection(raw),
        "amendment15": _parse_amendment15_projection(raw),
        "amendment16": _parse_amendment16_projection(raw),
        "amendment17": _parse_amendment17_projection(raw),
    }
    _validate_identifier_inventory_consistency(projection)
    return projection


def _execution_proof_projection(law: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    finding_counts: Counter[str] = Counter()
    for row in law["semantically_incompatible_local_proof_successor_rows"]:
        payload = row["successor_payload"]
        finding = payload["predecessor_row_specific_semantic_finding"]
        finding_counts[finding] += 1
        rows.append(
            {
                "document_source_position": row["document_source_position"],
                "predecessor_row_id": row["predecessor_row_id"],
                "predecessor_row_pointer": row["predecessor_row_pointer"],
                "predecessor_row_canonical_sha256": row[
                    "predecessor_row_canonical_sha256"
                ],
                "predecessor_status_mapping": row[
                    "predecessor_status_mapping"
                ],
                "predecessor_row_specific_semantic_finding": finding,
            }
        )
    return {
        "predecessor_id_domain_sha256": (INCOMPATIBLE_PROOF_ID_DOMAIN_SHA256),
        "terminal_status": PROOF_TERMINAL_STATUS,
        "umbrella_reason_code": (
            "terminal_semantic_incompatibility_umbrella_with_exact_"
            "predecessor_finding_preserved"
        ),
        "finding_counts": dict(finding_counts),
        "rows": rows,
    }


def _execution_fragment_projection(law: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    successor_rows = [
        *law["incomplete_fragment_terminal_successor_rows"],
        *law["composed_fragment_successor_rows"],
    ]
    for row in successor_rows:
        payload = row["successor_payload"]
        if row["successor_kind"] == "incomplete_fragment_terminal_disclosure":
            citation = payload["disclosed_incomplete_fragment_citation"]
            repair = "disclosure"
        else:
            citation = payload["predecessor_fragment_citation"]
            repair = "composition"
        rows.append(
            {
                "document_source_position": row["document_source_position"],
                "predecessor_row_id": row["predecessor_row_id"],
                "predecessor_row_pointer": row["predecessor_row_pointer"],
                "predecessor_row_canonical_sha256": row[
                    "predecessor_row_canonical_sha256"
                ],
                "source_occurrence_id": citation["source_occurrence_id"],
                "page_number": citation["page_number"],
                "utf8_byte_start": citation["utf8_byte_start"],
                "utf8_byte_end": citation["utf8_byte_end"],
                "page_text_utf8_sha256": citation["page_text_utf8_sha256"],
                "matched_text": citation["matched_text"],
                "matched_utf8_sha256": citation["matched_utf8_sha256"],
                "repair": repair,
            }
        )
    return {
        "evidence_id_domain_sha256": FRAGMENT_EVIDENCE_ID_DOMAIN_SHA256,
        "instruction_id_domain_sha256": (
            FRAGMENT_INSTRUCTION_ID_DOMAIN_SHA256
        ),
        "rows": rows,
        "disclosure_successor_kind": (
            "incomplete_fragment_terminal_disclosure"
        ),
        "disclosure_repair_mode": (
            "repair_by_exact_span_disclosure_not_invention"
        ),
        "disclosure_terminal_status": INCOMPLETE_FRAGMENT_STATUS,
        "composition_successor_kind": (
            "composed_fragment_complete_instruction"
        ),
        "composition_repair_mode": "exact_same_page_whitespace_composition",
        "composition_terminal_status": COMPOSED_FRAGMENT_STATUS,
        "selector_rule": FRAGMENT_SELECTOR_RULE,
        "composition_rule": COMPOSITION_RULE,
        "composition_specs": COMPOSITION_SPECS,
    }


def _execution_identity_projection(law: Mapping[str, Any]) -> dict[str, Any]:
    amendment12_identity = law["amendment12_ratification_identity"]
    return {
        "amendment12_identity_keys": list(amendment12_identity),
        "amendment12_identity": copy.deepcopy(amendment12_identity),
        "amendment12_attestation_keys": list(
            amendment12_identity["dual_ratify_attestations"][0]
        ),
        "ratification_history_observation": copy.deepcopy(
            law["ratification_history_observation"]
        ),
        "legacy_governing_identity_schema_version": (
            "amendment_13_governing_ratification_identity.v1"
        ),
        "legacy_governing_identity_status": (
            "RATIFIED_AMENDMENT_13_GOVERNING_EXECUTION_LAW"
        ),
        "ratification_bound_template_status": (
            RATIFICATION_BOUND_TEMPLATE_STATUS
        ),
        "draft_placeholder_keys": list(GOVERNING_A13_CANDIDATE_IDENTITY),
        "draft_placeholder_values": list(
            GOVERNING_A13_CANDIDATE_IDENTITY.values()
        ),
    }


def _source_annotation_blob_oid(path: str) -> str:
    line = str(
        _git("ls-tree", a12.SOURCE_COMMIT, "--", path, text=True)
    ).strip()
    match = re.fullmatch(
        rf"{DESIGN_MODE} blob ([0-9a-f]{{40}})\t{re.escape(path)}", line
    )
    _require(match is not None, "source annotation Git tree-entry drift")
    return match.group(1)


def _execution_overlay_projection(law: Mapping[str, Any]) -> dict[str, Any]:
    overlays = law["repair_overlay_rows"]
    annotation_by_position = {
        row["document_source_position"]: row["predecessor_annotation_identity"]
        for row in overlays
    }
    annotation_rows = []
    for position, identity in sorted(annotation_by_position.items()):
        annotation_rows.append(
            {
                "document_source_position": position,
                "annotation_path": identity["annotation_path"],
                "artifact_id": identity["artifact_id"],
                "git_blob_oid": _source_annotation_blob_oid(
                    identity["annotation_path"]
                ),
                "byte_size": identity["byte_size"],
                "raw_sha256": identity["raw_sha256"],
            }
        )
    all_successors = [
        *law["semantically_incompatible_local_proof_successor_rows"],
        *law["incomplete_fragment_terminal_successor_rows"],
        *law["composed_fragment_successor_rows"],
        *law["doc036_aggregate_domain_successor_rows"],
    ]
    proof_successor = law[
        "semantically_incompatible_local_proof_successor_rows"
    ][0]
    doc036_successor = law["doc036_aggregate_domain_successor_rows"][0]
    supersession = law["predecessor_supersession_rows"][0]
    return {
        "source_tree": a12.SOURCE_COMMIT,
        "annotation_mode": DESIGN_MODE,
        "annotation_rows": annotation_rows,
        "overlay_schema_version": law["overlay_schema_version"],
        "overlay_keys": list(overlays[0]),
        "overlay_authority_kind": overlays[0]["authority_kind"],
        "predecessor_source_rows_retained": all(
            row["predecessor_source_rows_retained"] for row in overlays
        ),
        "predecessor_source_row_erasure_permitted": any(
            row["predecessor_source_row_erasure_permitted"] for row in overlays
        ),
        "overlay_id_prefix": "a13-document-repair-overlay:",
        "overlay_identity_preimage": [
            f"[{OVERLAY_SCHEMA_VERSION},",
            " document_source_position,",
            " source_document_id,",
            " predecessor_annotation_identity,",
            " amendment12_ratification_identity,",
            " governing_amendment13_ratification_identity,",
            " predecessor_era_seal_content_sha256]",
        ],
        "annotation_identity_keys": list(
            overlays[0]["predecessor_annotation_identity"]
        ),
        "overlay_integrity_keys": list(overlays[0]["integrity"]),
        "successor_schema_version": law["successor_schema_version"],
        "successor_id_prefix": "a13-repair-successor:",
        "successor_common_keys": [
            key
            for key in proof_successor
            if key != "predecessor_status_mapping"
        ],
        "successor_status_mapping_key": "predecessor_status_mapping",
        "doc036_status_mapping_forbidden": (
            "predecessor_status_mapping" not in doc036_successor
            and all(
                "predecessor_status_mapping" in row
                for row in all_successors
                if row["successor_kind"]
                != "doc036_aggregate_domain_correction"
            )
        ),
        "successor_identity_preimage": [
            f"[{SUCCESSOR_SCHEMA_VERSION},",
            " successor_kind,",
            " repair_overlay_id,",
            " document_source_position,",
            " source_document_id,",
            " predecessor_annotation_artifact_id,",
            " predecessor_row_pointer,",
            " predecessor_row_id,",
            " predecessor_row_canonical_sha256,",
            " predecessor_status_mapping_or_null,",
            " successor_payload]",
        ],
        "supersession_schema_version": law["supersession_schema_version"],
        "supersession_keys": list(supersession),
        "supersession_id_prefix": "a13-supersession:",
        "supersession_relation": supersession["supersession_relation"],
        "supersession_status": supersession["status"],
        "predecessor_retained": all(
            row["predecessor_retained"]
            for row in law["predecessor_supersession_rows"]
        ),
        "predecessor_erasure_permitted": any(
            row["predecessor_erasure_permitted"]
            for row in law["predecessor_supersession_rows"]
        ),
        "semantic_consumer_selection": supersession[
            "semantic_consumer_selection"
        ],
        "supersession_identity_preimage": [
            f"[{SUPERSESSION_SCHEMA_VERSION},",
            " repair_overlay_id,",
            " predecessor_row_pointer,",
            " predecessor_row_id,",
            " predecessor_row_canonical_sha256,",
            " successor_row_id,",
            f" {SUPERSESSION_RELATION},",
            f" {SUPERSESSION_STATUS},",
            " true,",
            " false]",
        ],
    }


def _execution_doc036_projection(law: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for row in law["doc036_aggregate_domain_successor_rows"]:
        payload = row["successor_payload"]
        citation = payload["source_occurrence_citation"]
        rows.append(
            {
                "predecessor_row_id": row["predecessor_row_id"],
                "predecessor_row_pointer": row["predecessor_row_pointer"],
                "predecessor_row_canonical_sha256": row[
                    "predecessor_row_canonical_sha256"
                ],
                "source_occurrence_id": citation["source_occurrence_id"],
                "page_number": citation["page_number"],
                "utf8_byte_start": citation["utf8_byte_start"],
                "utf8_byte_end": citation["utf8_byte_end"],
                "matched_text": citation["matched_text"],
                "matched_utf8_sha256": citation["matched_utf8_sha256"],
            }
        )
    era_rows = law["successor_era_seal_rows"]
    totals = {
        key: sum(row["repair_counts"][key] for row in era_rows)
        for key in era_rows[0]["repair_counts"]
    }
    totals["successor_era_seal_count"] = len(era_rows)
    first_payload = law["doc036_aggregate_domain_successor_rows"][0][
        "successor_payload"
    ]
    return {
        "classification_id_domain_sha256": law["integrity"][
            "doc036_classification_id_domain_sha256"
        ],
        "transformation_rule": first_payload["transformation_rule"],
        "terminal_status": first_payload["terminal_status"],
        "rows": rows,
        "era_schema_version": law["era_successor_seal_schema_version"],
        "era_id_prefix": "a13-successor-era-seal:",
        "era_keys": list(era_rows[0]),
        "repair_count_keys": list(era_rows[0]["repair_counts"]),
        "era_identity_preimage": [
            f"[{ERA_SEAL_SCHEMA_VERSION},",
            " era_id,",
            " era_order_position,",
            " predecessor_era_seal_identity,",
            " ordered_repair_overlay_ids,",
            " ordered_successor_row_ids,",
            " ordered_supersession_row_ids,",
            " exact_repair_counts,",
            " amendment12_ratification_identity,",
            " governing_amendment13_ratification_identity]",
        ],
        "era_rows": [
            {
                "era_order_position": row["era_order_position"],
                "era_id": row["era_id"],
                "repair_counts": copy.deepcopy(row["repair_counts"]),
                "successor_era_seal_id": prospective_id,
            }
            for row, prospective_id in zip(
                era_rows, PROSPECTIVE_ERA_SEAL_IDS, strict=True
            )
        ],
        "era_totals": totals,
    }


def _execution_scope_projection(law: Mapping[str, Any]) -> dict[str, Any]:
    continuation = law["amendment12_continuation_domain"]
    integrity = law["integrity"]
    return {
        "law_gap_ids": copy.deepcopy(law["untouched_law_gap_predecessor_ids"]),
        "law_gap_id_domain_sha256": integrity["law_gap_id_domain_sha256"],
        "fixture_status": DRAFT_STATUS,
        "authority_emitted": False,
        "certification_emitted": False,
        "top_level_keys": list(law),
        "continuation_domain_keys": list(continuation),
        "source_artifact_identity_keys": list(
            continuation["source_artifact_identity"]
        ),
        "git_order_keys": list(law["git_order_law"]),
        "integrity_keys": list(integrity),
        "prospective_domain_pins": [
            {"domain": name, "count": count, "sha256": sha256}
            for name, count, sha256 in PROSPECTIVE_DOMAIN_PINS
        ],
        "semantic_mutations": list(A13_EXPECTED_MUTATIONS),
        "enforcement_mutations": list(A13_HISTORICAL_ENFORCEMENT_MUTATIONS),
    }


def _canonical_amendment14_projection() -> dict[str, Any]:
    return {
        "section_semantic_sha256": A14_SECTION_SEMANTIC_SHA256,
        "closure_top_level_keys": list(CLOSURE_TOP_LEVEL_KEYS),
        "closure_verdict_keys": list(CLOSURE_VERDICT_KEYS),
        "registry_closure_binding_keys": list(REGISTRY_CLOSURE_BINDING_KEYS),
        "a13_verdict_artifacts": [dict(row) for row in A13_VERDICT_ARTIFACTS],
        "a13_expected_closure": copy.deepcopy(A13_EXPECTED_CLOSURE),
        "ratification_sequence": list(A14_RATIFICATION_SEQUENCE),
        "implementation_pins": None,
        "semantic_mutations": list(A13_EXPECTED_MUTATIONS),
        "enforcement_mutations": list(A13_ENFORCEMENT_EXPECTED_MUTATIONS),
        "removed_mutations": list(REMOVED_PKI_MUTATIONS),
        "schema_binding_identifiers": list(A14_SCHEMA_BINDING_IDENTIFIERS),
        "path_templates": list(A14_PATH_TEMPLATES),
        "status_operation_identifiers": list(A14_STATUS_OPERATION_IDENTIFIERS),
    }


def _canonical_amendment15_projection() -> dict[str, Any]:
    return {
        "section_semantic_sha256": A15_SECTION_SEMANTIC_SHA256,
        "implementation_pins": None,
        "mutation_bindings": None,
    }


def _canonical_amendment16_projection() -> dict[str, Any]:
    return {
        "section_semantic_sha256": A16_SECTION_SEMANTIC_SHA256,
        "ratification_law_values": copy.deepcopy(A16_RATIFICATION_LAW_VALUES),
        "ordered_domain_expression": "range(13, R - 1)",
        "generated_closure_path_rule": (
            "docs/analysis/amendment_{13+i}_ratification/closure_v1.json"
        ),
        "combined_closure_paths": list(A16_COMBINED_CLOSURE_PATHS),
        "a14_historical_closure_binding": copy.deepcopy(
            A14_HISTORICAL_CLOSURE_BINDING
        ),
        "a15_verdict_artifacts": [dict(row) for row in A15_VERDICT_ARTIFACTS],
        "a15_expected_closure": copy.deepcopy(A15_EXPECTED_CLOSURE),
        "ratification_sequence": list(A16_RATIFICATION_SEQUENCE),
        "historical_r05_binding": copy.deepcopy(A16_HISTORICAL_R05_BINDING),
        "implementation_pins": None,
        "oracle_mutations": list(A16_EXPECTED_MUTATIONS),
        "oracle_mutation_domain_sha256": A16_MUTATION_DOMAIN_SHA256,
        "supersession_map": None,
        "schema_operation_identifiers": list(A16_SCHEMA_OPERATION_IDENTIFIERS),
        "status_identifiers": list(A16_STATUS_IDENTIFIERS),
        "python_identifiers": list(A16_PYTHON_IDENTIFIERS),
    }


def _canonical_amendment17_projection() -> dict[str, Any]:
    return {
        "section_semantic_sha256": A17_SECTION_SEMANTIC_SHA256,
        "implementation_pins": None,
        "revision_domain_rules": list(A17_REVISION_DOMAIN_RULES),
        "executed_transition_obligation": copy.deepcopy(
            A17_EXECUTED_TRANSITION_OBLIGATION
        ),
        "receipt_schema": copy.deepcopy(A17_RECEIPT_SCHEMA),
        "transition_registry_binding": copy.deepcopy(
            A17_TRANSITION_REGISTRY_BINDING
        ),
        "transition_closure_identities": [
            dict(row) for row in A17_TRANSITION_CLOSURE_IDENTITIES
        ],
        "transition_verdict_artifacts": [
            dict(row) for row in A17_TRANSITION_VERDICT_ARTIFACTS
        ],
        "required_public_output": list(A17_REQUIRED_PUBLIC_OUTPUT),
        "full_pinned_battery": copy.deepcopy(A17_FULL_PINNED_BATTERY),
        "test_ceremony_mutations": list(A17_EXPECTED_MUTATIONS),
        "test_ceremony_mutation_domain_sha256": (A17_MUTATION_DOMAIN_SHA256),
        "mutation_census": copy.deepcopy(A17_MUTATION_CENSUS),
        "supersession_map": [list(row) for row in A17_SUPERSESSION_MAP],
    }


@lru_cache(maxsize=1)
def _canonical_draft_document_projection() -> dict[str, Any]:
    """Build the immutable document cross-check independently of a caller law."""

    law = _construct_execution_law(
        governing_amendment13_ratification_identity=(
            GOVERNING_A13_CANDIDATE_IDENTITY
        ),
        status=DRAFT_STATUS,
    )
    integrity = law["integrity"]
    for name, count, sha256 in PROSPECTIVE_DOMAIN_PINS:
        count_key, sha_key = {
            "Repair overlays": ("overlay_count", "overlay_domain_sha256"),
            "All repair successors": (
                "repair_count",
                "successor_domain_sha256",
            ),
            "Supersession edges": (
                "supersession_count",
                "supersession_domain_sha256",
            ),
            "Successor-era seal fixtures": (
                "successor_era_seal_count",
                "successor_era_seal_domain_sha256",
            ),
        }[name]
        _require(
            integrity[count_key] == count and integrity[sha_key] == sha256,
            f"prospective {name} Python pin drift",
        )
    _require(
        tuple(
            row["successor_era_seal_id"]
            for row in law["successor_era_seal_rows"]
        )
        == PROSPECTIVE_ERA_SEAL_IDS,
        "prospective successor-era Python pin drift",
    )
    return {
        "section_semantic_sha256": dict(A13_SECTION_SEMANTIC_SHA256),
        "identity": _execution_identity_projection(law),
        "overlays": _execution_overlay_projection(law),
        "proof": _execution_proof_projection(law),
        "fragments": _execution_fragment_projection(law),
        "doc036": _execution_doc036_projection(law),
        "scope": _execution_scope_projection(law),
        "comparator": {
            "search_augmentation": list(A13_SEARCH_AUGMENTATION),
            "comparator_rows": [list(row) for row in A13_COMPARATOR_ROWS],
            "schema_literals": list(A13_SCHEMA_LITERALS),
            "content_id_prefixes": list(A13_CONTENT_ID_PREFIXES),
            "status_relation_operation_codes": list(
                A13_STATUS_RELATION_OPERATION_CODES
            ),
            "successor_kind_literals": list(A13_SUCCESSOR_KIND_LITERALS),
        },
        "amendment14": _canonical_amendment14_projection(),
        "amendment15": _canonical_amendment15_projection(),
        "amendment16": _canonical_amendment16_projection(),
        "amendment17": _canonical_amendment17_projection(),
    }


def _git_blob_oid(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()


def _verify_implementation_pins(pins: Mapping[str, Any]) -> None:
    """Authenticate active file identities against the worktree and HEAD."""

    _require_exact_keys(
        pins,
        {"mode", "files"},
        "Amendment-14 implementation pins",
    )
    current_design = (ROOT / DESIGN_PATH).read_bytes()
    label = "Amendment-14"
    if len(current_design) > REVISION18_BYTE_SIZE:
        pins = _parse_amendment17_implementation_pins(current_design)
        label = "Amendment-17"
    elif len(current_design) > REVISION17_BYTE_SIZE:
        pins = _parse_amendment16_implementation_pins(current_design)
        label = "Amendment-16"
    elif len(current_design) > REVISION16_BYTE_SIZE:
        pins = _parse_amendment15_implementation_pins(current_design)
        label = "Amendment-15"
    _require(
        pins["mode"] == DESIGN_MODE
        and [row["path"] for row in pins["files"]]
        == [
            "scripts/validate_amendment13_execution_law.py",
            "tests/test_validate_amendment13_execution_law.py",
            "scripts/build_amendment13_tier2_repairs.py",
        ],
        f"{label} implementation pin domain drift",
    )
    for row in pins["files"]:
        _require_exact_keys(
            row,
            {"path", "blob_oid", "byte_size", "sha256"},
            f"{label} implementation file pin",
        )
        _require(
            _is_lower_hex(row["blob_oid"], 40)
            and type(row["byte_size"]) is int
            and row["byte_size"] > 0
            and _is_lower_hex(row["sha256"], 64),
            f"{label} implementation file pin is malformed",
        )
        tree_line = str(
            _git("ls-tree", "HEAD", "--", row["path"], text=True)
        ).strip()
        _require(
            tree_line
            == f"{pins['mode']} blob {row['blob_oid']}\t{row['path']}",
            f"{label} implementation HEAD tree-entry pin drift",
        )
        head_raw = _git("show", f"HEAD:{row['path']}")
        worktree_raw = (ROOT / row["path"]).read_bytes()
        _require(
            isinstance(head_raw, bytes)
            and worktree_raw == head_raw
            and len(head_raw) == row["byte_size"]
            and _sha256(head_raw) == row["sha256"]
            and _git_blob_oid(head_raw) == row["blob_oid"],
            f"{label} implementation blob identity mismatch",
        )


def _validate_document_semantic_projection(
    raw: bytes,
    law: Mapping[str, Any],
) -> dict[str, Any]:
    """Require the governing bytes, Python controls, and fixture to agree."""

    projection = _parse_document_semantic_projection(raw)
    del law  # Never let a caller-mutated law redefine the governing bytes.
    expected = copy.deepcopy(_canonical_draft_document_projection())
    expected["scope"]["implementation_pins"] = projection["scope"][
        "implementation_pins"
    ]
    expected["amendment14"]["implementation_pins"] = projection["amendment14"][
        "implementation_pins"
    ]
    expected["amendment15"]["implementation_pins"] = projection["amendment15"][
        "implementation_pins"
    ]
    expected["amendment15"]["mutation_bindings"] = projection["amendment15"][
        "mutation_bindings"
    ]
    expected["amendment16"]["implementation_pins"] = projection["amendment16"][
        "implementation_pins"
    ]
    expected["amendment16"]["supersession_map"] = projection["amendment16"][
        "supersession_map"
    ]
    expected["amendment17"]["implementation_pins"] = projection["amendment17"][
        "implementation_pins"
    ]
    _require(
        projection == expected,
        "governing Amendment-14/15/16/17 document semantic projection drift",
    )
    _verify_implementation_pins(
        projection["amendment14"]["implementation_pins"]
    )
    return projection


@lru_cache(maxsize=1)
def _amendment12_continuation_projection() -> tuple[tuple[Any, ...], ...]:
    """Re-derive the five inherited continuation citations from pinned bytes."""

    raw = (ROOT / A12_SWEEP_PATH).read_bytes()
    _require(
        len(raw) == A12_SWEEP_BYTE_SIZE and _sha256(raw) == A12_SWEEP_SHA256,
        "Amendment-12 continuation source artifact identity drift",
    )
    artifact = a12.strict_json_loads(raw, A12_SWEEP_PATH)
    projection: list[tuple[Any, ...]] = []
    for row in artifact["alias_evidence_semantic_adjudication_rows"]:
        citation = row["continuation_composition_citation"]
        if citation is None:
            continue
        instruction_ids = row["source_instruction_occurrence_ids"]
        _require(
            len(instruction_ids) == 1,
            "Amendment-12 continuation citation has non-singleton instruction",
        )
        continuation_id = instruction_ids[0]
        expected_citation = (
            a12.CONTINUATION_ALIAS_CITATIONS_BY_INSTRUCTION.get(
                continuation_id
            )
        )
        _require(
            expected_citation is not None
            and all(
                citation[key] == value
                for key, value in expected_citation.items()
            )
            and citation["leading_occurrence_id"]
            == expected_citation["leading_occurrence_id"]
            and citation["continuation_occurrence_id"] == continuation_id,
            "Amendment-12 continuation citation projection drift",
        )
        projection.append(
            (
                row["document_source_position"],
                row["source_local_evidence_id"],
                citation["leading_occurrence_id"],
                continuation_id,
            )
        )
    canonical_projection = [list(row) for row in projection]
    raw_projection = canonical_json_bytes(canonical_projection)
    _require(
        len(raw_projection) == A12_CONTINUATION_PROJECTION_BYTE_SIZE
        and _sha256(raw_projection) == A12_CONTINUATION_PROJECTION_SHA256,
        "Amendment-12 continuation projection identity drift",
    )
    return tuple(projection)


def _run_git(
    *arguments: str,
    text: bool = False,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
    """Run raw-object Git with ambient Git controls removed."""

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=text,
        env=environment,
    )


def _git(*arguments: str, text: bool = False) -> bytes | str:
    result = _run_git(*arguments, text=text)
    _require(
        result.returncode == 0, f"git command failed: {' '.join(arguments)}"
    )
    return result.stdout


def _require_exact_commit_object(object_id: str, label: str) -> None:
    result = _run_git(
        "rev-parse",
        "--verify",
        f"{object_id}^{{commit}}",
        text=True,
    )
    _require(
        result.returncode == 0 and result.stdout.strip() == object_id,
        f"{label} is not an exact commit object",
    )


def _validate_amendment12_ratification_identity(
    identity: Mapping[str, Any],
) -> None:
    _require_exact_keys(
        identity,
        {
            "ratification_commit",
            "ratification_parents",
            "document_path",
            "document_mode",
            "document_blob_oid",
            "document_byte_size",
            "document_sha256",
            "dual_ratify_attestations",
        },
        "Amendment-12 ratification identity",
    )
    _require(
        identity["document_path"] == DESIGN_PATH
        and identity["document_mode"] == DESIGN_MODE,
        "ratification identity selects another document path or mode",
    )
    _require(
        isinstance(identity["ratification_parents"], list)
        and len(identity["ratification_parents"]) == 1,
        "ratification identity does not name one parent",
    )
    parent_line = str(
        _git(
            "rev-list",
            "--parents",
            "-n",
            "1",
            identity["ratification_commit"],
            text=True,
        )
    ).strip()
    _require(
        parent_line.split()
        == [
            identity["ratification_commit"],
            identity["ratification_parents"][0],
        ],
        "ratification commit is not the exact single-parent commit",
    )
    tree_line = str(
        _git(
            "ls-tree",
            identity["ratification_commit"],
            "--",
            identity["document_path"],
            text=True,
        )
    ).strip()
    _require(
        tree_line
        == (
            f"{identity['document_mode']} blob "
            f"{identity['document_blob_oid']}\t{identity['document_path']}"
        ),
        "ratification commit does not select the supplied document blob",
    )
    raw = _git(
        "show",
        f"{identity['ratification_commit']}:{identity['document_path']}",
    )
    _require(
        isinstance(raw, bytes), "ratification blob read was not raw bytes"
    )
    _require(
        len(raw) == identity["document_byte_size"]
        and _sha256(raw) == identity["document_sha256"]
        and hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest()
        == identity["document_blob_oid"],
        "ratification document bytes do not match the dual-hash identity",
    )
    _require(
        identity == AMENDMENT12_RATIFICATION_IDENTITY,
        "ratification identity is not the exact attested document identity",
    )


def _is_lower_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _strict_canonical_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = a12.strict_json_loads(raw, label)
    except a12.BuildError as error:
        raise LawError(f"{label} is invalid strict JSON") from error
    _require(
        isinstance(value, dict) and canonical_json_bytes(value) == raw,
        f"{label} is not canonical JSON",
    )
    _require_no_unpaired_surrogates(value, label)
    return value


def _require_no_unpaired_surrogates(value: Any, label: str) -> None:
    """Reject surrogate code points admitted by Python's JSON decoder."""

    if isinstance(value, str):
        _require(
            not any(0xD800 <= ord(character) <= 0xDFFF for character in value),
            f"{label} contains an unpaired Unicode surrogate",
        )
        return
    if isinstance(value, Mapping):
        for key, member in value.items():
            _require_no_unpaired_surrogates(key, label)
            _require_no_unpaired_surrogates(member, label)
        return
    if isinstance(value, list):
        for member in value:
            _require_no_unpaired_surrogates(member, label)


def _validate_closure_shape(
    closure: Mapping[str, Any],
    amendment_number: int,
) -> None:
    _require_exact_keys(
        closure,
        set(CLOSURE_TOP_LEVEL_KEYS),
        "ratification closure",
    )
    _require(
        type(closure["amendment_number"]) is int
        and closure["amendment_number"] == amendment_number
        and amendment_number > 0,
        "ratification closure amendment number drift",
    )
    _require(
        _is_lower_hex(closure["attested_candidate_design_blob_oid"], 40)
        and type(closure["attested_candidate_design_byte_size"]) is int
        and closure["attested_candidate_design_byte_size"] > 0
        and _is_lower_hex(closure["attested_candidate_design_raw_sha256"], 64)
        and _is_lower_hex(closure["ratification_commit"], 40)
        and _is_lower_hex(closure["ratification_commit_sole_parent"], 40)
        and _is_lower_hex(closure["operator_merge_commit"], 40),
        "ratification closure design or commit identity is malformed",
    )
    _require(
        closure["operator_merge_commit"] == closure["ratification_commit"],
        "ratification closure operator merge is not the ratification commit",
    )
    verdicts = closure["verdict_artifacts"]
    expected_directory = (
        f"docs/analysis/amendment_{amendment_number}_ratification"
    )
    _require(
        isinstance(verdicts, list) and len(verdicts) == 2,
        "ratification closure does not have exactly two verdict artifacts",
    )
    for verdict in verdicts:
        _require(
            isinstance(verdict, Mapping),
            "ratification closure verdict row is not an object",
        )
        _require_exact_keys(
            verdict,
            set(CLOSURE_VERDICT_KEYS),
            "ratification closure verdict artifact",
        )
        path = verdict["path"]
        _require(
            isinstance(path, str)
            and Path(path).as_posix() == path
            and Path(path).parent.as_posix() == expected_directory
            and Path(path).name != "closure_v1.json"
            and type(verdict["byte_size"]) is int
            and verdict["byte_size"] > 0
            and _is_lower_hex(verdict["raw_sha256"], 64),
            "ratification closure verdict identity is malformed",
        )
    _require(
        len({row["path"] for row in verdicts}) == 2,
        "ratification closure verdict paths are not distinct",
    )


def _verdict_attests_design(
    raw: bytes,
    closure: Mapping[str, Any],
) -> None:
    byte_size = closure["attested_candidate_design_byte_size"]
    decimal_forms = (str(byte_size).encode(), f"{byte_size:,}".encode())
    _require(
        raw.startswith(b"# RATIFY\n")
        and closure["attested_candidate_design_blob_oid"].encode() in raw
        and closure["attested_candidate_design_raw_sha256"].encode() in raw
        and any(value in raw for value in decimal_forms),
        "verdict artifact does not affirm the closure design attestation",
    )


_AMENDMENT_SECTION_PATTERN = re.compile(
    rb"^## (?P<section>[0-9]+)\. AMENDMENT SECTION \xe2\x80\x94 "
    rb"Amendment (?P<amendment>[0-9]+):[^\n]+$",
    re.MULTILINE,
)


def _terminal_design_amendment(raw: bytes) -> int:
    """Return the exact terminal amendment encoded by append-only headings."""

    rows = [
        (int(match.group("section")), int(match.group("amendment")))
        for match in _AMENDMENT_SECTION_PATTERN.finditer(raw)
    ]
    _require(
        rows
        and rows
        == [
            (amendment_number + 14, amendment_number)
            for amendment_number in range(1, rows[-1][1] + 1)
        ],
        "ratification design amendment heading sequence drift",
    )
    return rows[-1][1]


def _validate_amendment14_ratification_design(raw: bytes) -> None:
    """Require the exact revision-15 prefix and enacted A14 semantics."""

    _require(
        len(raw) == REVISION16_BYTE_SIZE
        and _sha256(raw) == REVISION16_SHA256
        and _git_blob_oid(raw) == REVISION16_BLOB_OID
        and _sha256(raw[:REVISION15_BYTE_SIZE]) == REVISION15_SHA256
        and _git_blob_oid(raw[:REVISION15_BYTE_SIZE]) == REVISION15_BLOB_OID
        and raw[REVISION15_BYTE_SIZE:].startswith(AMENDMENT14_BOUNDARY)
        and _terminal_design_amendment(raw) == 14,
        "Amendment-14 ratification design lacks the immutable revision-15 "
        "prefix, Amendment-14 boundary, or exact revision-16 identity",
    )
    projection = _parse_amendment14_projection(raw)
    expected = _canonical_amendment14_projection()
    expected["implementation_pins"] = projection["implementation_pins"]
    _require(
        projection == expected,
        "Amendment-14 ratification design semantic projection drift",
    )


def _validate_amendment15_ratification_design(raw: bytes) -> None:
    """Require the exact revision-17 identity and enacted A15 semantics."""

    _require(
        len(raw) == REVISION17_BYTE_SIZE
        and _sha256(raw) == REVISION17_SHA256
        and _git_blob_oid(raw) == REVISION17_BLOB_OID
        and _sha256(raw[:REVISION16_BYTE_SIZE]) == REVISION16_SHA256
        and _git_blob_oid(raw[:REVISION16_BYTE_SIZE]) == REVISION16_BLOB_OID
        and raw[REVISION16_BYTE_SIZE:].startswith(AMENDMENT15_BOUNDARY)
        and _terminal_design_amendment(raw) == 15,
        "Amendment-15 ratification design lacks the immutable revision-16 "
        "prefix, Amendment-15 boundary, or exact revision-17 identity",
    )
    projection = _parse_amendment15_projection(raw)
    expected = _canonical_amendment15_projection()
    expected["implementation_pins"] = projection["implementation_pins"]
    expected["mutation_bindings"] = projection["mutation_bindings"]
    _require(
        projection == expected,
        "Amendment-15 ratification design semantic projection drift",
    )


def _validate_inherited_amendment16_ratification_design(raw: bytes) -> None:
    """Preserve the revision-17 prefix and A16 semantics in every successor."""

    _require(
        len(raw) > REVISION17_BYTE_SIZE
        and _sha256(raw[:REVISION17_BYTE_SIZE]) == REVISION17_SHA256
        and _git_blob_oid(raw[:REVISION17_BYTE_SIZE]) == REVISION17_BLOB_OID
        and raw[REVISION17_BYTE_SIZE:].startswith(AMENDMENT16_BOUNDARY),
        "Amendment-16 ratification design lacks the immutable revision-17 "
        "prefix or Amendment-16 boundary",
    )
    projection = _parse_amendment16_projection(raw)
    expected = _canonical_amendment16_projection()
    expected["implementation_pins"] = projection["implementation_pins"]
    expected["supersession_map"] = projection["supersession_map"]
    _require(
        projection == expected,
        "Amendment-16 ratification design semantic projection drift",
    )


def _validate_amendment16_ratification_design(raw: bytes) -> None:
    """Require an Amendment-16-terminal design with exact inherited law."""

    _require(
        _terminal_design_amendment(raw) == 16,
        "Amendment-16 ratification design is not terminal Amendment 16",
    )
    _validate_inherited_amendment16_ratification_design(raw)


def _validate_inherited_amendment17_ratification_design(raw: bytes) -> None:
    """Preserve the revision-18 prefix and A17 semantics in every successor."""

    _require(
        len(raw) > REVISION18_BYTE_SIZE
        and _sha256(raw[:REVISION18_BYTE_SIZE]) == REVISION18_SHA256
        and _git_blob_oid(raw[:REVISION18_BYTE_SIZE]) == REVISION18_BLOB_OID
        and raw[REVISION18_BYTE_SIZE:].startswith(AMENDMENT17_BOUNDARY),
        "Amendment-17 ratification design lacks the immutable revision-18 "
        "prefix or Amendment-17 boundary",
    )
    projection = _parse_amendment17_projection(raw)
    expected = _canonical_amendment17_projection()
    expected["implementation_pins"] = projection["implementation_pins"]
    _require(
        projection == expected,
        "Amendment-17 ratification design semantic projection drift",
    )


def _validate_amendment17_ratification_design(raw: bytes) -> None:
    """Require an Amendment-17-terminal design with exact inherited law."""

    _require(
        _terminal_design_amendment(raw) == 17,
        "Amendment-17 ratification design is not terminal Amendment 17",
    )
    _validate_inherited_amendment17_ratification_design(raw)


def _validate_non_a13_ratification_design(
    raw: bytes,
    amendment_number: int,
) -> None:
    """Validate a closure's own N-to-revision-(N+2) design identity."""

    _require(
        amendment_number >= 14,
        "generic ratification design validator received Amendment 13",
    )
    terminal_amendment = _terminal_design_amendment(raw)
    _require(
        terminal_amendment == amendment_number,
        f"ratification closure for Amendment {amendment_number} attests "
        f"terminal Amendment {terminal_amendment} instead of Amendment "
        f"{amendment_number}",
    )
    if amendment_number == 14:
        _validate_amendment14_ratification_design(raw)
    elif amendment_number == 15:
        _validate_amendment15_ratification_design(raw)
    elif amendment_number == 16:
        _validate_amendment16_ratification_design(raw)
    elif amendment_number == 17:
        _validate_amendment17_ratification_design(raw)
    elif amendment_number > 17:
        _validate_inherited_amendment17_ratification_design(raw)


def _validate_ratification_closure(
    closure_raw: bytes | None,
    closure_binding: Mapping[str, Any],
    verdict_bytes: Mapping[str, bytes],
    amendment_number: int,
    *,
    verify_git: bool,
    ratification_design_raw: bytes | None = None,
    registry_design_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate registry-selected closure bytes and their exact artifacts."""

    _require(
        isinstance(closure_raw, bytes),
        "ratification closure is missing",
    )
    _require_exact_keys(
        closure_binding,
        set(REGISTRY_CLOSURE_BINDING_KEYS),
        "registry ratification closure binding",
    )
    expected_path = (
        f"docs/analysis/amendment_{amendment_number}_ratification/"
        "closure_v1.json"
    )
    _require(
        closure_binding["path"] == expected_path
        and type(closure_binding["raw_byte_size"]) is int
        and closure_binding["raw_byte_size"] > 0
        and _is_lower_hex(closure_binding["raw_sha256"], 64),
        "registry ratification closure binding drift",
    )
    _require(
        isinstance(closure_raw, bytes)
        and len(closure_raw) == closure_binding["raw_byte_size"]
        and _sha256(closure_raw) == closure_binding["raw_sha256"],
        "ratification closure bytes differ from the registry repin",
    )
    closure = _strict_canonical_json(closure_raw, expected_path)
    _validate_closure_shape(closure, amendment_number)
    if amendment_number == 13:
        _require(
            closure == A13_EXPECTED_CLOSURE,
            "Amendment-13 closure differs from directly enacted values",
        )
        _require(
            registry_design_binding is None,
            "Amendment-13 closure received an inapplicable design binding",
        )
    else:
        if amendment_number == 15:
            _require(
                closure == A15_EXPECTED_CLOSURE,
                "Amendment-15 closure differs from directly enacted values",
            )
        _require(
            isinstance(registry_design_binding, Mapping),
            "non-Amendment-13 closure lacks a terminal registry context",
        )
        registry_design_binding = _validate_registry_ratification_context(
            registry_design_binding
        )
        amendment_numbers = _ratification_amendment_numbers(
            registry_design_binding["revision"]
        )
        _require(
            amendment_number in amendment_numbers,
            "closure amendment is outside the terminal registry domain",
        )
        if (
            amendment_number == 14
            and registry_design_binding["revision"]
            >= COMBINED_ACTIVATION_REVISION
        ):
            _require(
                dict(closure_binding) == A14_HISTORICAL_CLOSURE_BINDING,
                "Amendment-14 historical closure binding drift",
            )
        if amendment_number == amendment_numbers[-1]:
            revision = registry_design_binding["revision"]
            _require(
                revision == amendment_number + 2
                and registry_design_binding["ratification_commit"]
                == closure["ratification_commit"]
                and registry_design_binding["blob_sha256"]
                == closure["attested_candidate_design_raw_sha256"],
                f"terminal Amendment-{amendment_number} closure does not "
                f"match the revision-{revision} registry design binding",
            )
        else:
            _require(
                amendment_number + 2 < registry_design_binding["revision"],
                "nonterminal closure revision relation drift",
            )

    verdicts = closure["verdict_artifacts"]
    _require(
        set(verdict_bytes) == {row["path"] for row in verdicts},
        "ratification closure verdict artifact domain drift",
    )
    for row in verdicts:
        raw = verdict_bytes[row["path"]]
        _require(
            isinstance(raw, bytes)
            and len(raw) == row["byte_size"]
            and _sha256(raw) == row["raw_sha256"],
            "ratification closure verdict byte mismatch",
        )
        _verdict_attests_design(raw, closure)

    commit = closure["ratification_commit"]
    if verify_git:
        _require_exact_commit_object(commit, "closure ratification commit")
        parent_line = str(
            _git("rev-list", "--parents", "-n", "1", commit, text=True)
        ).strip()
        _require(
            parent_line.split()
            == [commit, closure["ratification_commit_sole_parent"]],
            "closure ratification commit sole-parent mismatch",
        )
        tree_line = str(
            _git("ls-tree", commit, "--", DESIGN_PATH, text=True)
        ).strip()
        _require(
            tree_line
            == (
                f"{DESIGN_MODE} blob "
                f"{closure['attested_candidate_design_blob_oid']}\t"
                f"{DESIGN_PATH}"
            ),
            "closure attests a different design blob than the ratification commit",
        )
        ratification_design_raw = _git("show", f"{commit}:{DESIGN_PATH}")
    _require(
        isinstance(ratification_design_raw, bytes)
        and len(ratification_design_raw)
        == closure["attested_candidate_design_byte_size"]
        and _sha256(ratification_design_raw)
        == closure["attested_candidate_design_raw_sha256"]
        and _git_blob_oid(ratification_design_raw)
        == closure["attested_candidate_design_blob_oid"],
        "closure ratification design byte identity mismatch",
    )
    if amendment_number != 13:
        _validate_non_a13_ratification_design(
            ratification_design_raw,
            amendment_number,
        )
    return closure


def _validate_registry_closure_binding(
    binding: Mapping[str, Any],
    amendment_number: int,
) -> dict[str, Any]:
    _require_exact_keys(
        binding,
        set(REGISTRY_CLOSURE_BINDING_KEYS),
        "registry ratification closure binding",
    )
    expected_path = (
        f"docs/analysis/amendment_{amendment_number}_ratification/"
        "closure_v1.json"
    )
    _require(
        binding["path"] == expected_path
        and type(binding["raw_byte_size"]) is int
        and binding["raw_byte_size"] > 0
        and _is_lower_hex(binding["raw_sha256"], 64),
        "registry ratification closure binding drift",
    )
    return dict(binding)


def _ratification_closure_path(amendment_number: int) -> str:
    return (
        f"docs/analysis/amendment_{amendment_number}_ratification/"
        "closure_v1.json"
    )


def _ratification_amendment_numbers(revision: int) -> tuple[int, ...]:
    """Derive the complete closure domain for one terminal registry revision."""

    _require(
        type(revision) is int,
        "terminal ratification registry revision is not an integer",
    )
    _require(
        revision != FORBIDDEN_STANDALONE_REVISION,
        "revision 17 cannot be a terminal ratification registry; "
        "Amendments 15 and 16 require combined revision-18 activation",
    )
    _require(
        revision == HISTORICAL_TERMINAL_REVISION
        or revision >= COMBINED_ACTIVATION_REVISION,
        "registry revision is not a lawful terminal ratification revision",
    )
    terminal_amendment = revision - 2
    amendment_numbers = tuple(
        range(FIRST_CLOSURE_AMENDMENT, terminal_amendment + 1)
    )
    _require(
        len(amendment_numbers) == revision - 14,
        "terminal ratification closure-count law drift",
    )
    return amendment_numbers


def _validate_registry_ratification_context(
    design_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a revision-general terminal design and closure binding."""

    _require_exact_keys(
        design_binding,
        set(REGISTRY_DESIGN_BINDING_KEYS),
        "terminal registry design binding",
    )
    _require(
        design_binding["path"] == DESIGN_PATH
        and _is_lower_hex(design_binding["ratification_commit"], 40)
        and _is_lower_hex(design_binding["blob_sha256"], 64),
        "terminal registry design binding drift",
    )
    amendment_numbers = _ratification_amendment_numbers(
        design_binding["revision"]
    )
    closures = design_binding.get("ratification_closures")
    _require(
        isinstance(closures, list)
        and all(isinstance(row, Mapping) for row in closures),
        "registry ratification closure binding is missing",
    )
    _require(
        len(closures) == len(amendment_numbers),
        "registry ratification closure count drift",
    )
    expected_paths = [
        _ratification_closure_path(amendment_number)
        for amendment_number in amendment_numbers
    ]
    _require(
        [row.get("path") for row in closures] == expected_paths,
        "registry ratification closure binding order drift",
    )
    normalized = dict(design_binding)
    normalized["ratification_closures"] = [
        _validate_registry_closure_binding(row, amendment_number)
        for amendment_number, row in zip(
            amendment_numbers,
            closures,
            strict=True,
        )
    ]
    if design_binding["revision"] >= COMBINED_ACTIVATION_REVISION:
        _require(
            normalized["ratification_closures"][1]
            == A14_HISTORICAL_CLOSURE_BINDING,
            "Amendment-14 historical closure binding drift",
        )
    return normalized


def _public_registry_ratification_context() -> dict[str, Any]:
    """Load the current terminal registry-selected closure context."""

    try:
        import covered_earnings_correction_registry as registry

        design_binding = registry.design_binding()
    except Exception as error:
        raise LawError(
            "registry ratification closure binding is missing"
        ) from error
    _require(
        isinstance(design_binding, Mapping),
        "registry ratification closure binding is missing",
    )
    return _validate_registry_ratification_context(design_binding)


def _public_registry_closure_binding(
    amendment_number: int,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    amendment_numbers = _ratification_amendment_numbers(context["revision"])
    _require(
        amendment_number in amendment_numbers,
        "amendment is outside the terminal registry closure domain",
    )
    selected = context["ratification_closures"][
        amendment_number - FIRST_CLOSURE_AMENDMENT
    ]
    _require(
        isinstance(selected, Mapping)
        and selected.get("path")
        == _ratification_closure_path(amendment_number),
        "registry ratification closure binding is missing",
    )
    return _validate_registry_closure_binding(selected, amendment_number)


def _read_public_repository_file(
    path: str,
    label: str,
    *,
    require_regular_mode: bool,
) -> bytes:
    try:
        worktree_raw = (ROOT / path).read_bytes()
    except OSError as error:
        raise LawError(f"{label} is missing") from error
    result = _run_git("show", f"HEAD:{path}")
    _require(
        result.returncode == 0
        and isinstance(result.stdout, bytes)
        and result.stdout == worktree_raw,
        f"{label} is missing or differs between HEAD and worktree",
    )
    if require_regular_mode:
        tree_line = str(_git("ls-tree", "HEAD", "--", path, text=True)).strip()
        _require(
            tree_line
            == f"{DESIGN_MODE} blob {_git_blob_oid(worktree_raw)}\t{path}",
            f"{label} is not a mode-100644 regular file in HEAD",
        )
    return worktree_raw


def _validate_public_ratification_closure(
    amendment_number: int,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    binding = _public_registry_closure_binding(amendment_number, context)
    closure_path = binding["path"]
    worktree_raw = _read_public_repository_file(
        closure_path,
        "ratification closure",
        require_regular_mode=False,
    )
    _require(
        len(worktree_raw) == binding["raw_byte_size"]
        and _sha256(worktree_raw) == binding["raw_sha256"],
        "ratification closure bytes differ from the registry repin",
    )
    closure = _strict_canonical_json(worktree_raw, closure_path)
    _validate_closure_shape(closure, amendment_number)
    verdict_bytes = {
        row["path"]: _read_public_repository_file(
            row["path"],
            "verdict artifact",
            require_regular_mode=True,
        )
        for row in closure["verdict_artifacts"]
    }
    return _validate_ratification_closure(
        worktree_raw,
        binding,
        verdict_bytes,
        amendment_number,
        verify_git=True,
        registry_design_binding=context if amendment_number != 13 else None,
    )


def validate_amendment_ratification_closure(
    amendment_number: int,
) -> dict[str, Any]:
    """Select one closure only after validating the complete operative set."""

    closures = validate_ratification_operativity()
    _require(
        amendment_number in closures,
        "amendment is outside the terminal registry closure domain",
    )
    return closures[amendment_number]


def _validate_ratification_operativity_context(
    context: Mapping[str, Any],
    closure_validator: Callable[[int, Mapping[str, Any]], Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Validate one complete context through a privately supplied loader."""

    context = _validate_registry_ratification_context(context)
    amendment_numbers = _ratification_amendment_numbers(context["revision"])
    closures: dict[int, dict[str, Any]] = {}
    for amendment_number in amendment_numbers:
        closure = closure_validator(amendment_number, context)
        _require(
            isinstance(closure, Mapping)
            and closure.get("amendment_number") == amendment_number,
            "validated ratification closure amendment domain drift",
        )
        closures[amendment_number] = dict(closure)
    _require(
        tuple(closures) == amendment_numbers,
        "ratification operativity closure domain drift",
    )
    return closures


def validate_ratification_operativity() -> dict[int, dict[str, Any]]:
    """Validate the exact complete closure domain under one registry snapshot."""

    context = _public_registry_ratification_context()
    return _validate_ratification_operativity_context(
        context,
        _validate_public_ratification_closure,
    )


def _annotation_identity(document: a12.NormalizedDocument) -> dict[str, Any]:
    return dict(document.annotation_identity)


def _source_row_family(
    document: a12.NormalizedDocument,
    row_domain: str,
    row: Mapping[str, Any],
) -> dict[str, str]:
    if (
        document.schema_version == "rq_stage2_document_annotation.v1"
        and row_domain == "local_repeat_or_alias_evidence_rows"
        and row.get("handoff_status")
        == "local_resolved_cross_reference_for_global_assembly"
    ):
        return {
            "status_family": "modern_handoff_status",
            "status_field": "handoff_status",
            "predecessor_status": row["handoff_status"],
        }
    if (
        document.schema_version
        in {
            "rq_stage2_document_annotation_nonauthority.v1",
            "rq_stage2_document_annotation_local_edges_nonauthority.v1",
        }
        and row_domain == "local_repeat_alias_evidence_rows"
        and row.get("resolution_status")
        == "document_local_source_evidence_complete"
    ):
        return {
            "status_family": "legacy_resolution_status",
            "status_field": "resolution_status",
            "predecessor_status": row["resolution_status"],
        }
    if (
        document.position == 36
        and document.schema_version == "rq_stage2_document_annotation.v1"
        and row_domain == "local_repeat_or_alias_evidence_rows"
        and row.get("resolution_status")
        == "locally_resolved_document_evidence"
    ):
        return {
            "status_family": "document_036_special_resolution_status",
            "status_field": "resolution_status",
            "predecessor_status": row["resolution_status"],
        }
    raise LawError(
        f"document {document.position}: predecessor status family is not exact"
    )


def _raw_evidence_domain(data: Mapping[str, Any]) -> tuple[str, list[Any]]:
    if "local_repeat_alias_evidence_rows" in data:
        return (
            "local_repeat_alias_evidence_rows",
            data["local_repeat_alias_evidence_rows"],
        )
    _require(
        "local_repeat_or_alias_evidence_rows" in data,
        "annotation lacks a local evidence domain",
    )
    return (
        "local_repeat_or_alias_evidence_rows",
        data["local_repeat_or_alias_evidence_rows"],
    )


def _row_id(row: Mapping[str, Any]) -> str:
    for key in (
        "local_repeat_alias_evidence_id",
        "local_repeat_evidence_id",
        "local_repeat_or_alias_evidence_id",
    ):
        if key in row:
            return row[key]
    raise LawError("predecessor evidence row has no exact ID field")


def _overlay_preimage(
    document: a12.NormalizedDocument,
    predecessor_era_seal_content_sha256: str,
    governing_amendment13_ratification_identity: Mapping[str, Any],
) -> list[Any]:
    return [
        OVERLAY_SCHEMA_VERSION,
        document.position,
        document.source_document_id,
        _annotation_identity(document),
        AMENDMENT12_RATIFICATION_IDENTITY,
        governing_amendment13_ratification_identity,
        predecessor_era_seal_content_sha256,
    ]


def _successor_row(
    *,
    document: a12.NormalizedDocument,
    overlay_id: str,
    successor_kind: str,
    predecessor_row_domain: str,
    predecessor_row_index: int,
    predecessor_row_id: str,
    predecessor_row: Mapping[str, Any],
    successor_payload: Mapping[str, Any],
    family: Mapping[str, str] | None,
) -> dict[str, Any]:
    pointer = f"/{predecessor_row_domain}/{predecessor_row_index}"
    row_sha = _domain_sha(predecessor_row)
    status_mapping = None if family is None else dict(family)
    preimage = [
        SUCCESSOR_SCHEMA_VERSION,
        successor_kind,
        overlay_id,
        document.position,
        document.source_document_id,
        document.annotation_identity["artifact_id"],
        pointer,
        predecessor_row_id,
        row_sha,
        status_mapping,
        dict(successor_payload),
    ]
    row = {
        "schema_version": SUCCESSOR_SCHEMA_VERSION,
        "successor_row_id": _content_id("a13-repair-successor", preimage),
        "successor_identity_preimage": preimage,
        "successor_kind": successor_kind,
        "repair_overlay_id": overlay_id,
        "document_source_position": document.position,
        "source_document_id": document.source_document_id,
        "predecessor_annotation_identity": _annotation_identity(document),
        "predecessor_row_domain": predecessor_row_domain,
        "predecessor_row_pointer": pointer,
        "predecessor_row_id": predecessor_row_id,
        "predecessor_row_canonical_sha256": row_sha,
        "successor_payload": dict(successor_payload),
    }
    if family is not None:
        row["predecessor_status_mapping"] = status_mapping
    return row


def _supersession_row(successor: Mapping[str, Any]) -> dict[str, Any]:
    preimage = [
        SUPERSESSION_SCHEMA_VERSION,
        successor["repair_overlay_id"],
        successor["predecessor_row_pointer"],
        successor["predecessor_row_id"],
        successor["predecessor_row_canonical_sha256"],
        successor["successor_row_id"],
        SUPERSESSION_RELATION,
        SUPERSESSION_STATUS,
        True,
        False,
    ]
    return {
        "schema_version": SUPERSESSION_SCHEMA_VERSION,
        "supersession_row_id": _content_id("a13-supersession", preimage),
        "supersession_identity_preimage": preimage,
        "repair_overlay_id": successor["repair_overlay_id"],
        "document_source_position": successor["document_source_position"],
        "predecessor_row_pointer": successor["predecessor_row_pointer"],
        "predecessor_row_id": successor["predecessor_row_id"],
        "predecessor_row_canonical_sha256": successor[
            "predecessor_row_canonical_sha256"
        ],
        "successor_row_id": successor["successor_row_id"],
        "supersession_relation": SUPERSESSION_RELATION,
        "status": SUPERSESSION_STATUS,
        "predecessor_retained": True,
        "predecessor_erasure_permitted": False,
        "semantic_consumer_selection": "linked_successor_row",
    }


def _evidence_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "relation",
        "alias_relation",
        "source_occurrence_id",
        "source_instruction_occurrence_ids",
        "alias_anchor_source_occurrence_ids",
        "canonical_anchor_source_occurrence_ids",
        "alias_anchor_occurrence_id",
        "referenced_anchor_occurrence_id",
        "alias_local_anchor_id",
        "canonical_local_anchor_id",
        "evidence_occurrence_ids",
        "target_scope",
        "printed_target",
        "unresolved_target_reference",
    )
    return {key: copy.deepcopy(row[key]) for key in keys if key in row}


def _proof_payload(
    normalized: Mapping[str, Any],
    predecessor_row: Mapping[str, Any],
) -> dict[str, Any]:
    predecessor_finding = PROOF_PREDECESSOR_FINDING_BY_ID[
        normalized["local_evidence_id"]
    ]
    return {
        "terminal_status": PROOF_TERMINAL_STATUS,
        "terminal_reason_code": (
            "terminal_semantic_incompatibility_umbrella_with_exact_"
            "predecessor_finding_preserved"
        ),
        "predecessor_row_specific_semantic_finding": (predecessor_finding),
        "source_instruction_occurrence_ids": copy.deepcopy(
            normalized["source_instruction_occurrence_ids"]
        ),
        "source_instruction_matched_texts": copy.deepcopy(
            normalized["source_instruction_matched_texts"]
        ),
        "source_instruction_matched_utf8_sha256s": copy.deepcopy(
            normalized["source_instruction_matched_utf8_sha256s"]
        ),
        "source_instruction_page_numbers": copy.deepcopy(
            normalized["source_instruction_page_numbers"]
        ),
        "source_instruction_utf8_byte_starts": copy.deepcopy(
            normalized["source_instruction_utf8_byte_starts"]
        ),
        "source_instruction_utf8_byte_ends": copy.deepcopy(
            normalized["source_instruction_utf8_byte_ends"]
        ),
        "alias_anchor_occurrence_ids": copy.deepcopy(
            normalized["alias_anchor_occurrence_ids"]
        ),
        "canonical_anchor_occurrence_ids": copy.deepcopy(
            normalized["canonical_anchor_occurrence_ids"]
        ),
        "endpoint_occurrence_kinds": copy.deepcopy(
            normalized["endpoint_occurrence_kinds"]
        ),
        "endpoint_raw_node_domains": copy.deepcopy(
            normalized["endpoint_raw_node_domains"]
        ),
        "endpoint_matched_texts": copy.deepcopy(
            normalized["endpoint_matched_texts"]
        ),
        "endpoint_matched_utf8_sha256s": copy.deepcopy(
            normalized["endpoint_matched_utf8_sha256s"]
        ),
        "predecessor_preserved_claim_projection": _evidence_projection(
            predecessor_row
        ),
        "alias_admitted": False,
        "occurrence_equivalence_admitted": False,
        "repeat_coverage_arm_admitted": False,
    }


def _fragment_citation(
    document: a12.NormalizedDocument,
    instruction_id: str,
) -> dict[str, Any]:
    occurrence = document.questionnaire_occurrence_rows_by_id[instruction_id]
    page = occurrence["page_number"]
    return {
        "source_occurrence_id": instruction_id,
        "matched_text": occurrence["matched_text"],
        "matched_utf8_sha256": occurrence["matched_utf8_sha256"],
        "page_number": page,
        "page_text_utf8_sha256": document.page_text_utf8_sha256_by_number[
            page
        ],
        "utf8_byte_start": occurrence["utf8_byte_start"],
        "utf8_byte_end": occurrence["utf8_byte_end"],
    }


def _composition_citation(
    document: a12.NormalizedDocument,
    predecessor_row: Mapping[str, Any],
) -> dict[str, Any]:
    expected = copy.deepcopy(COMPOSITION_SPECS[document.position])
    selected = expected["selected_leading_occurrence_id"]
    candidates = expected["candidate_occurrences_in_source_order"]
    _require(len(candidates) == 2, "composition selector cardinality drift")
    _require(
        [row["occurrence_kind"] for row in candidates]
        == ["context_anchor", "field_purpose_prompt"],
        "composition selector kind order drift",
    )
    _require(
        predecessor_row.get("alias_anchor_occurrence_id") == selected,
        "composition selector is not the predecessor alias anchor",
    )
    for candidate in candidates:
        occurrence = document.questionnaire_occurrence_rows_by_id[
            candidate["occurrence_id"]
        ]
        _require(
            occurrence["occurrence_kind"] == candidate["occurrence_kind"]
            and occurrence["matched_text"] == expected["leading_text"]
            and occurrence["matched_utf8_sha256"]
            == expected["leading_utf8_sha256"]
            and occurrence["page_number"] == expected["page_number"]
            and occurrence["utf8_byte_start"]
            == expected["combined_utf8_byte_start"]
            and occurrence["utf8_byte_end"]
            == expected["leading_utf8_byte_end"],
            "composition leading occurrence citation drift",
        )
    _require(
        document.page_text_utf8_sha256_by_number[expected["page_number"]]
        == expected["page_text_utf8_sha256"],
        "composition page identity drift",
    )
    gap = expected["gap_text"].encode("utf-8")
    combined = expected["combined_text"].encode("utf-8")
    _require(
        gap.decode("utf-8").isspace()
        and len(gap)
        == expected["gap_utf8_byte_end"] - expected["gap_utf8_byte_start"]
        and _sha256(gap) == expected["gap_utf8_sha256"],
        "composition gap bytes drift",
    )
    _require(
        len(combined)
        == expected["combined_utf8_byte_end"]
        - expected["combined_utf8_byte_start"]
        and _sha256(combined) == expected["combined_utf8_sha256"],
        "composition transformation bytes drift",
    )
    continuation = document.questionnaire_occurrence_rows_by_id[
        expected["continuation_occurrence_id"]
    ]
    leading_length = (
        expected["leading_utf8_byte_end"]
        - expected["combined_utf8_byte_start"]
    )
    _require(
        combined[:leading_length] == expected["leading_text"].encode("utf-8")
        and combined[leading_length : leading_length + len(gap)] == gap
        and combined[leading_length + len(gap) :]
        == continuation["matched_text"].encode("utf-8")
        and continuation["utf8_byte_start"]
        == expected["continuation_utf8_byte_start"]
        and continuation["utf8_byte_end"]
        == expected["combined_utf8_byte_end"],
        "composition is not the exact contiguous three-slice transform",
    )
    return {
        "selector_rule": FRAGMENT_SELECTOR_RULE,
        "candidate_occurrences_in_source_order": candidates,
        "selected_leading_occurrence_id": selected,
        "composition_rule": COMPOSITION_RULE,
        "leading_occurrence_id": selected,
        "continuation_occurrence_id": expected["continuation_occurrence_id"],
        "page_number": expected["page_number"],
        "page_text_utf8_sha256": expected["page_text_utf8_sha256"],
        "combined_utf8_byte_start": expected["combined_utf8_byte_start"],
        "leading_utf8_byte_end": expected["leading_utf8_byte_end"],
        "gap_utf8_byte_start": expected["gap_utf8_byte_start"],
        "gap_utf8_byte_end": expected["gap_utf8_byte_end"],
        "gap_text": expected["gap_text"],
        "gap_utf8_sha256": expected["gap_utf8_sha256"],
        "gap_is_whitespace_only": True,
        "continuation_utf8_byte_start": expected[
            "continuation_utf8_byte_start"
        ],
        "combined_utf8_byte_end": expected["combined_utf8_byte_end"],
        "combined_text": expected["combined_text"],
        "combined_utf8_sha256": expected["combined_utf8_sha256"],
    }


def _fragment_payload(
    document: a12.NormalizedDocument,
    predecessor_row: Mapping[str, Any],
    instruction_id: str,
    disposition: str,
) -> dict[str, Any]:
    citation = _fragment_citation(document, instruction_id)
    if disposition == "incomplete":
        return {
            "terminal_status": INCOMPLETE_FRAGMENT_STATUS,
            "repair_mode": "repair_by_exact_span_disclosure_not_invention",
            "disclosed_incomplete_fragment_citation": citation,
            "continuation_citation": None,
            "alias_admitted": False,
            "occurrence_equivalence_admitted": False,
            "repeat_coverage_arm_admitted": False,
        }
    _require(disposition == "composed", "unknown fragment disposition")
    return {
        "terminal_status": COMPOSED_FRAGMENT_STATUS,
        "repair_mode": "exact_same_page_whitespace_composition",
        "predecessor_fragment_citation": citation,
        "composition_citation": _composition_citation(
            document, predecessor_row
        ),
        "alias_admitted": False,
        "occurrence_equivalence_admitted": False,
        "repeat_coverage_arm_admitted": False,
    }


def _doc036_payload(
    document: a12.NormalizedDocument,
    predecessor_row: Mapping[str, Any],
) -> dict[str, Any]:
    occurrence_id = predecessor_row["source_occurrence_id"]
    occurrence = document.questionnaire_occurrence_rows_by_id[occurrence_id]
    _require(
        predecessor_row["node_domain"] == "component_slot"
        and occurrence["occurrence_kind"]
        in {
            "farm_aggregate_anchor",
            "business_aggregate_anchor",
            "role_total_anchor",
        },
        "document-036 predecessor is not the determinate aggregate defect",
    )
    preserved = copy.deepcopy(dict(predecessor_row))
    corrected = copy.deepcopy(preserved)
    corrected["node_domain"] = "aggregate"
    return {
        "terminal_status": DOC036_SUCCESSOR_STATUS,
        "transformation_rule": (
            "replace_only_node_domain_component_slot_with_aggregate"
        ),
        "predecessor_classification_row": preserved,
        "successor_classification_row": corrected,
        "source_occurrence_citation": {
            "source_occurrence_id": occurrence_id,
            "occurrence_kind": occurrence["occurrence_kind"],
            "matched_text": occurrence["matched_text"],
            "matched_utf8_sha256": occurrence["matched_utf8_sha256"],
            "page_number": occurrence["page_number"],
            "page_text_utf8_sha256": document.page_text_utf8_sha256_by_number[
                occurrence["page_number"]
            ],
            "utf8_byte_start": occurrence["utf8_byte_start"],
            "utf8_byte_end": occurrence["utf8_byte_end"],
        },
    }


class _RawObjectSourceReader:
    """Read Amendment-12 source bytes through A13's raw-object Git view."""

    def __init__(self) -> None:
        _require_exact_commit_object(a12.SOURCE_COMMIT, "pinned source commit")

    def read(self, path: str) -> bytes:
        raw = _git("show", f"{a12.SOURCE_COMMIT}:{path}")
        _require(
            isinstance(raw, bytes), f"pinned source read was not raw: {path}"
        )
        return raw


def build_execution_law() -> dict[str, Any]:
    """Reconstruct the exact unratified prospective law fixture."""

    law = _construct_execution_law(
        governing_amendment13_ratification_identity=(
            GOVERNING_A13_CANDIDATE_IDENTITY
        ),
        status=DRAFT_STATUS,
    )
    validate_execution_law(law, verify_git=False)
    return law


def build_ratification_bound_execution_template() -> dict[str, Any]:
    """Bind the template only after both public closures validate."""

    closures = validate_ratification_operativity()
    closure = closures[13]
    law = _construct_execution_law(
        governing_amendment13_ratification_identity=closure,
        status=RATIFICATION_BOUND_TEMPLATE_STATUS,
    )
    _validate_execution_law(
        law,
        verify_git=True,
        verified_closures=closures,
    )
    return law


def _build_ratification_bound_execution_template_for_test(
    amendment13_material: tuple[
        Mapping[str, Any],
        bytes,
        Mapping[str, Any],
        Mapping[str, bytes],
        bytes,
    ],
    amendment14_material: tuple[
        Mapping[str, Any],
        bytes,
        Mapping[str, Any],
        Mapping[str, bytes],
        bytes,
    ],
) -> dict[str, Any]:
    """Exercise dual-closure operativity without creating authority."""

    (
        _,
        a13_raw,
        a13_binding,
        a13_verdicts,
        a13_design_raw,
    ) = amendment13_material
    (
        a14_expected,
        a14_raw,
        a14_binding,
        a14_verdicts,
        a14_design_raw,
    ) = amendment14_material
    closure13 = _validate_ratification_closure(
        a13_raw,
        a13_binding,
        a13_verdicts,
        13,
        verify_git=False,
        ratification_design_raw=a13_design_raw,
    )
    closure14 = _validate_ratification_closure(
        a14_raw,
        a14_binding,
        a14_verdicts,
        14,
        verify_git=False,
        ratification_design_raw=a14_design_raw,
        registry_design_binding=_synthetic_registry_design_binding(
            a14_expected
        ),
    )
    law = _construct_execution_law(
        governing_amendment13_ratification_identity=closure13,
        status=RATIFICATION_BOUND_TEMPLATE_STATUS,
    )
    _validate_execution_law(
        law,
        verify_git=False,
        verified_closures={13: closure13, 14: closure14},
    )
    return law


def _construct_execution_law(
    *,
    governing_amendment13_ratification_identity: Mapping[str, Any],
    status: str,
) -> dict[str, Any]:
    """Construct the source-derived law fixture for one governing identity."""

    governing_identity = copy.deepcopy(
        dict(governing_amendment13_ratification_identity)
    )

    reader = _RawObjectSourceReader()
    documents, source_identity = a12._load_documents(reader)
    document_by_position = {
        document.position: document for document in documents
    }
    predecessor_seal_by_era = {
        row["era_id"]: row for row in source_identity["era_seal_rows"]
    }
    affected_positions = sorted(
        {
            7,
            10,
            11,
            12,
            13,
            15,
            17,
            19,
            36,
            52,
            56,
            58,
            66,
            70,
        }
    )
    raw_by_position: dict[int, Mapping[str, Any]] = {}
    raw_evidence_by_position: dict[int, tuple[str, list[Any]]] = {}
    normalized_evidence_by_id: dict[str, Mapping[str, Any]] = {}
    for position in affected_positions:
        document = document_by_position[position]
        raw = a12.strict_json_loads(
            reader.read(document.annotation_path), document.annotation_path
        )
        raw_by_position[position] = raw
        raw_evidence_by_position[position] = _raw_evidence_domain(raw)
        for row in document.evidence_rows:
            normalized_evidence_by_id[row["local_evidence_id"]] = row

    overlay_id_by_position: dict[int, str] = {}
    overlay_preimage_by_position: dict[int, list[Any]] = {}
    for position in affected_positions:
        document = document_by_position[position]
        preimage = _overlay_preimage(
            document,
            predecessor_seal_by_era[document.era_id]["content_sha256"],
            governing_identity,
        )
        overlay_preimage_by_position[position] = preimage
        overlay_id_by_position[position] = _content_id(
            "a13-document-repair-overlay", preimage
        )

    proof_successors: list[dict[str, Any]] = []
    for evidence_id in INCOMPATIBLE_PROOF_IDS:
        normalized = normalized_evidence_by_id[evidence_id]
        position = next(
            document.position
            for document in documents
            if any(
                row["local_evidence_id"] == evidence_id
                for row in document.evidence_rows
            )
        )
        document = document_by_position[position]
        row_domain, rows = raw_evidence_by_position[position]
        index = normalized["source_row_index"]
        predecessor = rows[index]
        _require(_row_id(predecessor) == evidence_id, "proof row ID drift")
        family = _source_row_family(document, row_domain, predecessor)
        proof_successors.append(
            _successor_row(
                document=document,
                overlay_id=overlay_id_by_position[position],
                successor_kind="semantically_incompatible_local_proof",
                predecessor_row_domain=row_domain,
                predecessor_row_index=index,
                predecessor_row_id=evidence_id,
                predecessor_row=predecessor,
                successor_payload=_proof_payload(normalized, predecessor),
                family=family,
            )
        )

    incomplete_successors: list[dict[str, Any]] = []
    composed_successors: list[dict[str, Any]] = []
    for position, evidence_id, instruction_id, disposition in FRAGMENT_SPECS:
        document = document_by_position[position]
        normalized = normalized_evidence_by_id[evidence_id]
        _require(
            normalized["source_instruction_occurrence_ids"]
            == [instruction_id],
            "fragment predecessor instruction drift",
        )
        row_domain, rows = raw_evidence_by_position[position]
        index = normalized["source_row_index"]
        predecessor = rows[index]
        _require(_row_id(predecessor) == evidence_id, "fragment row ID drift")
        family = _source_row_family(document, row_domain, predecessor)
        successor = _successor_row(
            document=document,
            overlay_id=overlay_id_by_position[position],
            successor_kind=(
                "incomplete_fragment_terminal_disclosure"
                if disposition == "incomplete"
                else "composed_fragment_complete_instruction"
            ),
            predecessor_row_domain=row_domain,
            predecessor_row_index=index,
            predecessor_row_id=evidence_id,
            predecessor_row=predecessor,
            successor_payload=_fragment_payload(
                document, predecessor, instruction_id, disposition
            ),
            family=family,
        )
        if disposition == "incomplete":
            incomplete_successors.append(successor)
        else:
            composed_successors.append(successor)

    document = document_by_position[36]
    classification_rows = raw_by_position[36][
        "local_anchor_classification_rows"
    ]
    classification_index = {
        row["local_anchor_classification_id"]: index
        for index, row in enumerate(classification_rows)
    }
    doc036_successors: list[dict[str, Any]] = []
    for classification_id in DOC036_CLASSIFICATION_IDS:
        index = classification_index[classification_id]
        predecessor = classification_rows[index]
        doc036_successors.append(
            _successor_row(
                document=document,
                overlay_id=overlay_id_by_position[36],
                successor_kind="doc036_aggregate_domain_correction",
                predecessor_row_domain="local_anchor_classification_rows",
                predecessor_row_index=index,
                predecessor_row_id=classification_id,
                predecessor_row=predecessor,
                successor_payload=_doc036_payload(document, predecessor),
                family=None,
            )
        )

    all_successors = [
        *proof_successors,
        *incomplete_successors,
        *composed_successors,
        *doc036_successors,
    ]
    supersession_rows = [_supersession_row(row) for row in all_successors]
    successors_by_position: dict[int, list[dict[str, Any]]] = defaultdict(list)
    supersession_by_position: dict[int, list[dict[str, Any]]] = defaultdict(
        list
    )
    for row in all_successors:
        successors_by_position[row["document_source_position"]].append(row)
    for row in supersession_rows:
        supersession_by_position[row["document_source_position"]].append(row)

    overlay_rows: list[dict[str, Any]] = []
    domains = (
        (
            "semantically_incompatible_local_proof_successor_rows",
            "semantically_incompatible_local_proof",
        ),
        (
            "incomplete_fragment_terminal_successor_rows",
            "incomplete_fragment_terminal_disclosure",
        ),
        (
            "composed_fragment_successor_rows",
            "composed_fragment_complete_instruction",
        ),
        (
            "doc036_aggregate_domain_successor_rows",
            "doc036_aggregate_domain_correction",
        ),
    )
    for position in affected_positions:
        document = document_by_position[position]
        row = {
            "schema_version": OVERLAY_SCHEMA_VERSION,
            "repair_overlay_id": overlay_id_by_position[position],
            "overlay_identity_preimage": overlay_preimage_by_position[
                position
            ],
            "authority_kind": "PROSPECTIVE_NONAUTHORITY",
            "document_source_position": position,
            "source_document_id": document.source_document_id,
            "predecessor_annotation_identity": _annotation_identity(document),
            "amendment12_ratification_identity": copy.deepcopy(
                AMENDMENT12_RATIFICATION_IDENTITY
            ),
            "governing_amendment13_ratification_identity": copy.deepcopy(
                governing_identity
            ),
            "predecessor_era_id": document.era_id,
            "predecessor_era_seal_content_sha256": predecessor_seal_by_era[
                document.era_id
            ]["content_sha256"],
            "predecessor_source_rows_retained": True,
            "predecessor_source_row_erasure_permitted": False,
            "predecessor_supersession_rows": supersession_by_position[
                position
            ],
        }
        for key, kind in domains:
            row[key] = [
                successor
                for successor in successors_by_position[position]
                if successor["successor_kind"] == kind
            ]
        row["integrity"] = {
            "successor_count": len(successors_by_position[position]),
            "successor_domain_sha256": _domain_sha(
                successors_by_position[position]
            ),
            "supersession_count": len(supersession_by_position[position]),
            "supersession_domain_sha256": _domain_sha(
                supersession_by_position[position]
            ),
        }
        overlay_rows.append(row)

    era_rows: list[dict[str, Any]] = []
    for predecessor_seal in source_identity["era_seal_rows"]:
        era_id = predecessor_seal["era_id"]
        era_overlays = [
            row for row in overlay_rows if row["predecessor_era_id"] == era_id
        ]
        era_successors = [
            successor
            for successor in all_successors
            if document_by_position[
                successor["document_source_position"]
            ].era_id
            == era_id
        ]
        era_edges = [
            edge
            for edge in supersession_rows
            if document_by_position[edge["document_source_position"]].era_id
            == era_id
        ]
        kind_counts = Counter(row["successor_kind"] for row in era_successors)
        counts = {
            "semantically_incompatible_local_proof_count": kind_counts[
                "semantically_incompatible_local_proof"
            ],
            "incomplete_fragment_terminal_count": kind_counts[
                "incomplete_fragment_terminal_disclosure"
            ],
            "composed_fragment_count": kind_counts[
                "composed_fragment_complete_instruction"
            ],
            "doc036_aggregate_domain_count": kind_counts[
                "doc036_aggregate_domain_correction"
            ],
            "supersession_count": len(era_edges),
        }
        preimage = [
            ERA_SEAL_SCHEMA_VERSION,
            era_id,
            predecessor_seal["era_order_position"],
            predecessor_seal,
            [row["repair_overlay_id"] for row in era_overlays],
            [row["successor_row_id"] for row in era_successors],
            [row["supersession_row_id"] for row in era_edges],
            counts,
            AMENDMENT12_RATIFICATION_IDENTITY,
            governing_identity,
        ]
        era_rows.append(
            {
                "schema_version": ERA_SEAL_SCHEMA_VERSION,
                "successor_era_seal_id": _content_id(
                    "a13-successor-era-seal", preimage
                ),
                "successor_era_seal_identity_preimage": preimage,
                "authority_kind": "PROSPECTIVE_NONAUTHORITY",
                "era_id": era_id,
                "era_order_position": predecessor_seal["era_order_position"],
                "predecessor_era_seal_identity": predecessor_seal,
                "amendment12_ratification_identity": copy.deepcopy(
                    AMENDMENT12_RATIFICATION_IDENTITY
                ),
                "governing_amendment13_ratification_identity": copy.deepcopy(
                    governing_identity
                ),
                "repair_overlay_ids": [
                    row["repair_overlay_id"] for row in era_overlays
                ],
                "successor_row_ids": [
                    row["successor_row_id"] for row in era_successors
                ],
                "supersession_row_ids": [
                    row["supersession_row_id"] for row in era_edges
                ],
                "repair_counts": counts,
                "all_named_domains_present_even_when_empty": True,
            }
        )

    amendment12_continuation_projection = [
        list(row) for row in _amendment12_continuation_projection()
    ]
    amendment12_continuation_evidence_ids = {
        row[1] for row in amendment12_continuation_projection
    }
    amendment12_continuation_instruction_ids = {
        row[3] for row in amendment12_continuation_projection
    }
    new_fragment_evidence_ids = {row[1] for row in FRAGMENT_SPECS}
    new_fragment_instruction_ids = {row[2] for row in FRAGMENT_SPECS}
    _require(
        not amendment12_continuation_evidence_ids & new_fragment_evidence_ids
        and not amendment12_continuation_instruction_ids
        & new_fragment_instruction_ids,
        "Amendment-12 and Amendment-13 continuation domains overlap",
    )

    law = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "authority_emitted": False,
        "certification_emitted": False,
        "amendment12_ratification_identity": copy.deepcopy(
            AMENDMENT12_RATIFICATION_IDENTITY
        ),
        "ratification_history_observation": {
            "changed_path_count": RATIFICATION_CHANGED_PATH_COUNT,
            "commit_path_shape_is_identity_condition": False,
        },
        "governing_amendment13_ratification_identity": copy.deepcopy(
            governing_identity
        ),
        "governing_amendment13_identity_schema_version": (
            GOVERNING_A13_IDENTITY_SCHEMA_VERSION
        ),
        "ratification_identity_rule": (
            "exact_attested_document_blob_not_commit_path_shape"
        ),
        "overlay_schema_version": OVERLAY_SCHEMA_VERSION,
        "successor_schema_version": SUCCESSOR_SCHEMA_VERSION,
        "supersession_schema_version": SUPERSESSION_SCHEMA_VERSION,
        "era_successor_seal_schema_version": ERA_SEAL_SCHEMA_VERSION,
        "repair_overlay_rows": overlay_rows,
        "semantically_incompatible_local_proof_successor_rows": (
            proof_successors
        ),
        "incomplete_fragment_terminal_successor_rows": incomplete_successors,
        "composed_fragment_successor_rows": composed_successors,
        "doc036_aggregate_domain_successor_rows": doc036_successors,
        "predecessor_supersession_rows": supersession_rows,
        "successor_era_seal_rows": era_rows,
        "untouched_law_gap_predecessor_ids": list(LAW_GAP_IDS),
        "amendment12_continuation_domain": {
            "disjoint_and_unchanged": True,
            "continuation_citation_count": 5,
            "continuation_restoration_count": 3,
            "source_artifact_identity": {
                "path": A12_SWEEP_PATH,
                "byte_size": A12_SWEEP_BYTE_SIZE,
                "raw_sha256": A12_SWEEP_SHA256,
            },
            "continuation_projection_rows": (
                amendment12_continuation_projection
            ),
            "continuation_projection_byte_size": (
                A12_CONTINUATION_PROJECTION_BYTE_SIZE
            ),
            "continuation_projection_sha256": (
                A12_CONTINUATION_PROJECTION_SHA256
            ),
            "new_fragment_predecessor_evidence_ids_disjoint": True,
            "new_fragment_instruction_occurrence_ids_disjoint": True,
        },
        "git_order_law": {
            "amendment12_ratification_commit_must_be_strict_ancestor_of_"
            "governing_amendment13_ratification_commit": True,
            "governing_amendment13_ratification_commit_must_be_validated_"
            "and_strict_ancestor_of_every_overlay_first_add": True,
            "overlay_first_add_must_be_strict_ancestor_of_containing_era_"
            "successor_seal_first_add": True,
            "all_six_successor_seal_first_adds_must_be_strict_ancestors_of_"
            "tier2_evidence_first_add": True,
            "ratification_and_execution_record_commits_must_be_single_parent": (
                True
            ),
            "source_seal_identity_is_independently_authenticated_not_"
            "promoted_from_tier1": True,
            "dual_independent_reconstruction_required": True,
            "complete_raw_byte_attestation_required": True,
            "q5_first_add_permitted": False,
        },
        "integrity": {
            "incompatible_proof_count": len(proof_successors),
            "incompatible_proof_id_domain_sha256": _domain_sha(
                list(INCOMPATIBLE_PROOF_IDS)
            ),
            "incomplete_fragment_count": len(incomplete_successors),
            "composed_fragment_count": len(composed_successors),
            "fragment_evidence_id_domain_sha256": _domain_sha(
                [row[1] for row in FRAGMENT_SPECS]
            ),
            "fragment_instruction_id_domain_sha256": _domain_sha(
                [row[2] for row in FRAGMENT_SPECS]
            ),
            "doc036_aggregate_domain_count": len(doc036_successors),
            "doc036_classification_id_domain_sha256": _domain_sha(
                list(DOC036_CLASSIFICATION_IDS)
            ),
            "repair_count": len(all_successors),
            "supersession_count": len(supersession_rows),
            "overlay_count": len(overlay_rows),
            "successor_era_seal_count": len(era_rows),
            "law_gap_untouched_count": len(LAW_GAP_IDS),
            "law_gap_id_domain_sha256": _domain_sha(list(LAW_GAP_IDS)),
            "successor_domain_sha256": _domain_sha(all_successors),
            "supersession_domain_sha256": _domain_sha(supersession_rows),
            "overlay_domain_sha256": _domain_sha(overlay_rows),
            "successor_era_seal_domain_sha256": _domain_sha(era_rows),
        },
    }
    return law


def _all_overlay_successors(overlay: Mapping[str, Any]) -> list[Any]:
    return [
        *overlay["semantically_incompatible_local_proof_successor_rows"],
        *overlay["incomplete_fragment_terminal_successor_rows"],
        *overlay["composed_fragment_successor_rows"],
        *overlay["doc036_aggregate_domain_successor_rows"],
    ]


def validate_execution_law(
    law: Mapping[str, Any],
    *,
    verify_git: bool = True,
) -> None:
    """Validate a draft fixture or a public closure-bound template."""

    governing_identity = law.get("governing_amendment13_ratification_identity")
    _require(
        governing_identity == GOVERNING_A13_CANDIDATE_IDENTITY or verify_git,
        "ratification-bound validation may not disable Git verification",
    )
    _validate_execution_law(law, verify_git=verify_git)


def _validate_execution_law(
    law: Mapping[str, Any],
    *,
    verify_git: bool = True,
    verified_closures: Mapping[int, Mapping[str, Any]] | None = None,
) -> None:
    """Internal validator with one private dual-closure test path."""
    _require_exact_keys(
        law,
        {
            "schema_version",
            "status",
            "authority_emitted",
            "certification_emitted",
            "amendment12_ratification_identity",
            "ratification_history_observation",
            "governing_amendment13_ratification_identity",
            "governing_amendment13_identity_schema_version",
            "ratification_identity_rule",
            "overlay_schema_version",
            "successor_schema_version",
            "supersession_schema_version",
            "era_successor_seal_schema_version",
            "repair_overlay_rows",
            "semantically_incompatible_local_proof_successor_rows",
            "incomplete_fragment_terminal_successor_rows",
            "composed_fragment_successor_rows",
            "doc036_aggregate_domain_successor_rows",
            "predecessor_supersession_rows",
            "successor_era_seal_rows",
            "untouched_law_gap_predecessor_ids",
            "amendment12_continuation_domain",
            "git_order_law",
            "integrity",
        },
        "execution law",
    )
    _require(law["schema_version"] == SCHEMA_VERSION, "law schema drift")
    _require(
        law["overlay_schema_version"] == OVERLAY_SCHEMA_VERSION
        and law["successor_schema_version"] == SUCCESSOR_SCHEMA_VERSION
        and law["supersession_schema_version"] == SUPERSESSION_SCHEMA_VERSION
        and law["era_successor_seal_schema_version"]
        == ERA_SEAL_SCHEMA_VERSION,
        "declared repair schema version drift",
    )
    governing_identity = law["governing_amendment13_ratification_identity"]
    is_candidate_fixture = (
        governing_identity == GOVERNING_A13_CANDIDATE_IDENTITY
    )
    governing_document_raw = (ROOT / DESIGN_PATH).read_bytes()
    if is_candidate_fixture:
        _require(
            verified_closures is None,
            "unratified fixture received ratification closures",
        )
        expected_status = DRAFT_STATUS
    else:
        if verify_git and verified_closures is None:
            verified_closures = validate_ratification_operativity()
        closure_numbers = (
            tuple(verified_closures)
            if isinstance(verified_closures, Mapping)
            else ()
        )
        implied_revision = closure_numbers[-1] + 2 if closure_numbers else 0
        _require(
            isinstance(verified_closures, Mapping)
            and bool(closure_numbers)
            and closure_numbers
            == _ratification_amendment_numbers(implied_revision)
            and all(
                isinstance(closure, Mapping)
                and closure.get("amendment_number") == amendment_number
                for amendment_number, closure in verified_closures.items()
            ),
            "ratification validation lacks the exact verified closure domain",
        )
        closure = dict(verified_closures[13])
        _require(
            verified_closures[14]["amendment_number"] == 14,
            "ratification validation lacks the Amendment-14 closure",
        )
        _require(
            governing_identity == closure,
            "governing Amendment-13 closure identity drift",
        )
        expected_status = RATIFICATION_BOUND_TEMPLATE_STATUS
    _require(
        law["status"] == expected_status
        and law["authority_emitted"] is False
        and law["certification_emitted"] is False,
        "law fixture claims authority or certification",
    )
    _require(
        law["ratification_identity_rule"]
        == "exact_attested_document_blob_not_commit_path_shape",
        "ratification identity rule drift",
    )
    _require(
        law["ratification_history_observation"]
        == {
            "changed_path_count": RATIFICATION_CHANGED_PATH_COUNT,
            "commit_path_shape_is_identity_condition": False,
        },
        "ratification history observation became an identity condition",
    )
    _require(
        law["governing_amendment13_identity_schema_version"]
        == GOVERNING_A13_IDENTITY_SCHEMA_VERSION,
        "governing Amendment-13 identity schema drift",
    )
    if verify_git:
        _validate_amendment12_ratification_identity(
            law["amendment12_ratification_identity"]
        )
    else:
        _require(
            law["amendment12_ratification_identity"]
            == AMENDMENT12_RATIFICATION_IDENTITY,
            "ratification identity drift",
        )
    _validate_document_semantic_projection(governing_document_raw, law)
    proof_rows = law["semantically_incompatible_local_proof_successor_rows"]
    incomplete_rows = law["incomplete_fragment_terminal_successor_rows"]
    composed_rows = law["composed_fragment_successor_rows"]
    doc036_rows = law["doc036_aggregate_domain_successor_rows"]
    all_successors = [
        *proof_rows,
        *incomplete_rows,
        *composed_rows,
        *doc036_rows,
    ]
    _require(
        [row["predecessor_row_id"] for row in proof_rows]
        == list(INCOMPATIBLE_PROOF_IDS),
        "incompatible proof predecessor keyset/order drift",
    )
    _require(
        [row["predecessor_row_id"] for row in incomplete_rows]
        == [row[1] for row in FRAGMENT_SPECS if row[3] == "incomplete"],
        "incomplete fragment predecessor keyset/order drift",
    )
    _require(
        [row["predecessor_row_id"] for row in composed_rows]
        == [row[1] for row in FRAGMENT_SPECS if row[3] == "composed"],
        "composed fragment predecessor keyset/order drift",
    )
    _require(
        [row["predecessor_row_id"] for row in doc036_rows]
        == list(DOC036_CLASSIFICATION_IDS),
        "document-036 classification keyset/order drift",
    )
    _require(len(all_successors) == 46, "repair successor count is not 46")
    _require(
        len({row["successor_row_id"] for row in all_successors}) == 46,
        "repair successor IDs are not unique",
    )
    for row in all_successors:
        expected_keys = {
            "schema_version",
            "successor_row_id",
            "successor_identity_preimage",
            "successor_kind",
            "repair_overlay_id",
            "document_source_position",
            "source_document_id",
            "predecessor_annotation_identity",
            "predecessor_row_domain",
            "predecessor_row_pointer",
            "predecessor_row_id",
            "predecessor_row_canonical_sha256",
            "successor_payload",
        }
        if row["successor_kind"] != "doc036_aggregate_domain_correction":
            expected_keys.add("predecessor_status_mapping")
        _require_exact_keys(row, expected_keys, "repair successor row")
        _require_exact_keys(
            row["predecessor_annotation_identity"],
            {
                "annotation_path",
                "artifact_id",
                "schema_version",
                "source_document_id",
                "document_source_position",
                "byte_size",
                "raw_sha256",
                "content_sha256",
            },
            "predecessor annotation identity",
        )
        _require(
            row["schema_version"] == SUCCESSOR_SCHEMA_VERSION
            and row["successor_identity_preimage"]
            == [
                SUCCESSOR_SCHEMA_VERSION,
                row["successor_kind"],
                row["repair_overlay_id"],
                row["document_source_position"],
                row["source_document_id"],
                row["predecessor_annotation_identity"]["artifact_id"],
                row["predecessor_row_pointer"],
                row["predecessor_row_id"],
                row["predecessor_row_canonical_sha256"],
                row.get("predecessor_status_mapping"),
                row["successor_payload"],
            ]
            and row["successor_row_id"]
            == _content_id(
                "a13-repair-successor", row["successor_identity_preimage"]
            ),
            "successor identity preimage mismatch",
        )
        expected_mapping = row.get("predecessor_status_mapping")
        _require(
            row["successor_identity_preimage"][-2] == expected_mapping,
            "successor identity does not bind predecessor status mapping",
        )
    for row in proof_rows:
        payload = row["successor_payload"]
        _require_exact_keys(
            row["predecessor_status_mapping"],
            {"status_family", "status_field", "predecessor_status"},
            "proof predecessor status mapping",
        )
        _require_exact_keys(
            payload,
            {
                "terminal_status",
                "terminal_reason_code",
                "predecessor_row_specific_semantic_finding",
                "source_instruction_occurrence_ids",
                "source_instruction_matched_texts",
                "source_instruction_matched_utf8_sha256s",
                "source_instruction_page_numbers",
                "source_instruction_utf8_byte_starts",
                "source_instruction_utf8_byte_ends",
                "alias_anchor_occurrence_ids",
                "canonical_anchor_occurrence_ids",
                "endpoint_occurrence_kinds",
                "endpoint_raw_node_domains",
                "endpoint_matched_texts",
                "endpoint_matched_utf8_sha256s",
                "predecessor_preserved_claim_projection",
                "alias_admitted",
                "occurrence_equivalence_admitted",
                "repeat_coverage_arm_admitted",
            },
            "incompatible-proof successor payload",
        )
        _require(
            payload["terminal_status"] == PROOF_TERMINAL_STATUS
            and payload["terminal_reason_code"]
            == (
                "terminal_semantic_incompatibility_umbrella_with_exact_"
                "predecessor_finding_preserved"
            )
            and payload["predecessor_row_specific_semantic_finding"]
            == PROOF_PREDECESSOR_FINDING_BY_ID[row["predecessor_row_id"]]
            and payload["alias_admitted"] is False
            and payload["occurrence_equivalence_admitted"] is False
            and payload["repeat_coverage_arm_admitted"] is False,
            "forged incompatible-proof terminal status or admission",
        )
        _require(
            row["predecessor_status_mapping"]
            in tuple(STATUS_MAPPING_BY_FAMILY.values()),
            "proof predecessor status family is not deterministic",
        )
    _require(
        tuple(PROOF_PREDECESSOR_FINDING_BY_ID) == INCOMPATIBLE_PROOF_IDS,
        "incompatible-proof predecessor finding domain drift",
    )
    _require(
        Counter(
            row["predecessor_status_mapping"]["status_family"]
            for row in proof_rows
        )
        == Counter(
            {
                "modern_handoff_status": 13,
                "legacy_resolution_status": 14,
                "document_036_special_resolution_status": 1,
            }
        ),
        "proof predecessor status-family census drift",
    )
    for row in incomplete_rows:
        payload = row["successor_payload"]
        _require_exact_keys(
            row["predecessor_status_mapping"],
            {"status_family", "status_field", "predecessor_status"},
            "fragment predecessor status mapping",
        )
        _require(
            row["predecessor_status_mapping"]
            in tuple(STATUS_MAPPING_BY_FAMILY.values()),
            "fragment predecessor status family is not deterministic",
        )
        _require_exact_keys(
            payload,
            {
                "terminal_status",
                "repair_mode",
                "disclosed_incomplete_fragment_citation",
                "continuation_citation",
                "alias_admitted",
                "occurrence_equivalence_admitted",
                "repeat_coverage_arm_admitted",
            },
            "incomplete-fragment successor payload",
        )
        _require_exact_keys(
            payload["disclosed_incomplete_fragment_citation"],
            {
                "source_occurrence_id",
                "matched_text",
                "matched_utf8_sha256",
                "page_number",
                "page_text_utf8_sha256",
                "utf8_byte_start",
                "utf8_byte_end",
            },
            "incomplete-fragment disclosure citation",
        )
        _require(
            payload["terminal_status"] == INCOMPLETE_FRAGMENT_STATUS
            and payload["repair_mode"]
            == "repair_by_exact_span_disclosure_not_invention"
            and payload["continuation_citation"] is None
            and payload["alias_admitted"] is False
            and payload["occurrence_equivalence_admitted"] is False
            and payload["repeat_coverage_arm_admitted"] is False,
            "incomplete fragment is not terminal repair-by-disclosure",
        )
    for row in composed_rows:
        payload = row["successor_payload"]
        citation = payload["composition_citation"]
        expected = COMPOSITION_SPECS[row["document_source_position"]]
        _require_exact_keys(
            row["predecessor_status_mapping"],
            {"status_family", "status_field", "predecessor_status"},
            "fragment predecessor status mapping",
        )
        _require(
            row["predecessor_status_mapping"]
            in tuple(STATUS_MAPPING_BY_FAMILY.values()),
            "fragment predecessor status family is not deterministic",
        )
        _require_exact_keys(
            payload,
            {
                "terminal_status",
                "repair_mode",
                "predecessor_fragment_citation",
                "composition_citation",
                "alias_admitted",
                "occurrence_equivalence_admitted",
                "repeat_coverage_arm_admitted",
            },
            "composed-fragment successor payload",
        )
        _require_exact_keys(
            citation,
            {
                "selector_rule",
                "candidate_occurrences_in_source_order",
                "selected_leading_occurrence_id",
                "composition_rule",
                "leading_occurrence_id",
                "continuation_occurrence_id",
                "page_number",
                "page_text_utf8_sha256",
                "combined_utf8_byte_start",
                "leading_utf8_byte_end",
                "gap_utf8_byte_start",
                "gap_utf8_byte_end",
                "gap_text",
                "gap_utf8_sha256",
                "gap_is_whitespace_only",
                "continuation_utf8_byte_start",
                "combined_utf8_byte_end",
                "combined_text",
                "combined_utf8_sha256",
            },
            "composed-fragment citation",
        )
        _require(
            payload["terminal_status"] == COMPOSED_FRAGMENT_STATUS
            and citation["selector_rule"] == FRAGMENT_SELECTOR_RULE
            and citation["selected_leading_occurrence_id"]
            == expected["selected_leading_occurrence_id"]
            and citation["candidate_occurrences_in_source_order"]
            == expected["candidate_occurrences_in_source_order"],
            "fragment duplicate selector forgery",
        )
        _require(
            citation["composition_rule"] == COMPOSITION_RULE
            and citation["gap_text"] == expected["gap_text"]
            and citation["gap_utf8_sha256"] == expected["gap_utf8_sha256"]
            and citation["gap_is_whitespace_only"] is True
            and citation["combined_text"] == expected["combined_text"]
            and citation["combined_utf8_sha256"]
            == expected["combined_utf8_sha256"],
            "fragment composition transformation forgery",
        )
        _require(
            payload["alias_admitted"] is False
            and payload["occurrence_equivalence_admitted"] is False
            and payload["repeat_coverage_arm_admitted"] is False,
            "composed instruction silently claims alias semantics",
        )
    _require(
        Counter(
            row["predecessor_status_mapping"]["status_family"]
            for row in incomplete_rows
        )
        == Counter({"modern_handoff_status": 6, "legacy_resolution_status": 2})
        and Counter(
            row["predecessor_status_mapping"]["status_family"]
            for row in composed_rows
        )
        == Counter({"modern_handoff_status": 2}),
        "fragment predecessor status-family census drift",
    )
    for row in doc036_rows:
        payload = row["successor_payload"]
        _require_exact_keys(
            payload,
            {
                "terminal_status",
                "transformation_rule",
                "predecessor_classification_row",
                "successor_classification_row",
                "source_occurrence_citation",
            },
            "document-036 successor payload",
        )
        predecessor = payload["predecessor_classification_row"]
        successor = payload["successor_classification_row"]
        citation = payload["source_occurrence_citation"]
        _require_exact_keys(
            citation,
            {
                "source_occurrence_id",
                "occurrence_kind",
                "matched_text",
                "matched_utf8_sha256",
                "page_number",
                "page_text_utf8_sha256",
                "utf8_byte_start",
                "utf8_byte_end",
            },
            "document-036 source occurrence citation",
        )
        changed_keys = {
            key
            for key in predecessor
            if predecessor.get(key) != successor.get(key)
        }
        _require(
            payload["terminal_status"] == DOC036_SUCCESSOR_STATUS
            and payload["transformation_rule"]
            == "replace_only_node_domain_component_slot_with_aggregate"
            and set(successor) == set(predecessor)
            and predecessor["node_domain"] == "component_slot"
            and successor["node_domain"] == "aggregate"
            and changed_keys == {"node_domain"}
            and citation["source_occurrence_id"]
            == predecessor["source_occurrence_id"]
            and citation["occurrence_kind"]
            in {
                "farm_aggregate_anchor",
                "business_aggregate_anchor",
                "role_total_anchor",
            },
            "document-036 transformation is not the sole determinate field change",
        )

    supersession_rows = law["predecessor_supersession_rows"]
    _require(len(supersession_rows) == 46, "supersession edge count is not 46")
    successor_by_id = {row["successor_row_id"]: row for row in all_successors}
    _require(
        [row["successor_row_id"] for row in supersession_rows]
        == [row["successor_row_id"] for row in all_successors],
        "supersession edges do not exact-cover successors",
    )
    for row in supersession_rows:
        _require_exact_keys(
            row,
            {
                "schema_version",
                "supersession_row_id",
                "supersession_identity_preimage",
                "repair_overlay_id",
                "document_source_position",
                "predecessor_row_pointer",
                "predecessor_row_id",
                "predecessor_row_canonical_sha256",
                "successor_row_id",
                "supersession_relation",
                "status",
                "predecessor_retained",
                "predecessor_erasure_permitted",
                "semantic_consumer_selection",
            },
            "predecessor supersession row",
        )
        _require(
            row["schema_version"] == SUPERSESSION_SCHEMA_VERSION
            and row["supersession_identity_preimage"]
            == [
                SUPERSESSION_SCHEMA_VERSION,
                row["repair_overlay_id"],
                row["predecessor_row_pointer"],
                row["predecessor_row_id"],
                row["predecessor_row_canonical_sha256"],
                row["successor_row_id"],
                SUPERSESSION_RELATION,
                SUPERSESSION_STATUS,
                True,
                False,
            ]
            and row["supersession_row_id"]
            == _content_id(
                "a13-supersession", row["supersession_identity_preimage"]
            )
            and row["supersession_relation"] == SUPERSESSION_RELATION
            and row["status"] == SUPERSESSION_STATUS
            and row["predecessor_retained"] is True
            and row["predecessor_erasure_permitted"] is False
            and row["semantic_consumer_selection"] == "linked_successor_row",
            "supersession erases or fails to select the predecessor's successor",
        )

    overlays = law["repair_overlay_rows"]
    _require(len(overlays) == 14, "repair overlay count is not 14")
    _require(
        [row["document_source_position"] for row in overlays]
        == [7, 10, 11, 12, 13, 15, 17, 19, 36, 52, 56, 58, 66, 70],
        "repair overlay document order drift",
    )
    overlay_by_position = {
        row["document_source_position"]: row for row in overlays
    }
    overlay_successor_ids: list[str] = []
    overlay_supersession_ids: list[str] = []
    for overlay in overlays:
        _require_exact_keys(
            overlay,
            {
                "schema_version",
                "repair_overlay_id",
                "overlay_identity_preimage",
                "authority_kind",
                "document_source_position",
                "source_document_id",
                "predecessor_annotation_identity",
                "amendment12_ratification_identity",
                "governing_amendment13_ratification_identity",
                "predecessor_era_id",
                "predecessor_era_seal_content_sha256",
                "predecessor_source_rows_retained",
                "predecessor_source_row_erasure_permitted",
                "predecessor_supersession_rows",
                "semantically_incompatible_local_proof_successor_rows",
                "incomplete_fragment_terminal_successor_rows",
                "composed_fragment_successor_rows",
                "doc036_aggregate_domain_successor_rows",
                "integrity",
            },
            "document repair overlay",
        )
        _require(
            overlay["schema_version"] == OVERLAY_SCHEMA_VERSION
            and overlay["authority_kind"] == "PROSPECTIVE_NONAUTHORITY"
            and overlay["overlay_identity_preimage"]
            == [
                OVERLAY_SCHEMA_VERSION,
                overlay["document_source_position"],
                overlay["source_document_id"],
                overlay["predecessor_annotation_identity"],
                AMENDMENT12_RATIFICATION_IDENTITY,
                governing_identity,
                overlay["predecessor_era_seal_content_sha256"],
            ]
            and overlay["repair_overlay_id"]
            == _content_id(
                "a13-document-repair-overlay",
                overlay["overlay_identity_preimage"],
            )
            and overlay["amendment12_ratification_identity"]
            == AMENDMENT12_RATIFICATION_IDENTITY
            and overlay["governing_amendment13_ratification_identity"]
            == governing_identity
            and overlay["predecessor_source_rows_retained"] is True
            and overlay["predecessor_source_row_erasure_permitted"] is False,
            "overlay identity or append-only rule drift",
        )
        overlay_successors = _all_overlay_successors(overlay)
        overlay_edges = overlay["predecessor_supersession_rows"]
        expected_overlay_successors = [
            row
            for row in all_successors
            if row["document_source_position"]
            == overlay["document_source_position"]
        ]
        expected_overlay_edges = [
            row
            for row in supersession_rows
            if row["document_source_position"]
            == overlay["document_source_position"]
        ]
        _require(
            overlay_successors == expected_overlay_successors
            and overlay_edges == expected_overlay_edges,
            "overlay rows are not exact projections of top-level domains",
        )
        _require(
            overlay["integrity"]
            == {
                "successor_count": len(overlay_successors),
                "successor_domain_sha256": _domain_sha(overlay_successors),
                "supersession_count": len(overlay_edges),
                "supersession_domain_sha256": _domain_sha(overlay_edges),
            },
            "overlay integrity drift",
        )
        overlay_successor_ids.extend(
            row["successor_row_id"] for row in overlay_successors
        )
        overlay_supersession_ids.extend(
            row["supersession_row_id"] for row in overlay_edges
        )
    _require(
        Counter(overlay_successor_ids)
        == Counter({row_id: 1 for row_id in successor_by_id})
        and Counter(overlay_supersession_ids)
        == Counter(
            {row["supersession_row_id"]: 1 for row in supersession_rows}
        ),
        "overlays do not exact-cover repair and supersession rows",
    )
    for successor in all_successors:
        overlay = overlay_by_position[successor["document_source_position"]]
        _require(
            successor["repair_overlay_id"] == overlay["repair_overlay_id"]
            and successor["source_document_id"]
            == overlay["source_document_id"]
            and successor["predecessor_annotation_identity"]
            == overlay["predecessor_annotation_identity"],
            "successor cross-document overlay linkage drift",
        )
    for edge in supersession_rows:
        successor = successor_by_id[edge["successor_row_id"]]
        _require(
            edge["repair_overlay_id"] == successor["repair_overlay_id"]
            and edge["document_source_position"]
            == successor["document_source_position"]
            and edge["predecessor_row_pointer"]
            == successor["predecessor_row_pointer"]
            and edge["predecessor_row_id"] == successor["predecessor_row_id"]
            and edge["predecessor_row_canonical_sha256"]
            == successor["predecessor_row_canonical_sha256"],
            "supersession edge does not exact-link its successor",
        )

    era_rows = law["successor_era_seal_rows"]
    _require(len(era_rows) == 6, "all six successor era seals are required")
    _require(
        [row["era_id"] for row in era_rows] == list(EXPECTED_ERA_COUNTS),
        "successor era seal order drift",
    )
    for era_row in era_rows:
        _require_exact_keys(
            era_row,
            {
                "schema_version",
                "successor_era_seal_id",
                "successor_era_seal_identity_preimage",
                "authority_kind",
                "era_id",
                "era_order_position",
                "predecessor_era_seal_identity",
                "amendment12_ratification_identity",
                "governing_amendment13_ratification_identity",
                "repair_overlay_ids",
                "successor_row_ids",
                "supersession_row_ids",
                "repair_counts",
                "all_named_domains_present_even_when_empty",
            },
            "successor era seal row",
        )
        counts = era_row["repair_counts"]
        _require_exact_keys(
            counts,
            {
                "semantically_incompatible_local_proof_count",
                "incomplete_fragment_terminal_count",
                "composed_fragment_count",
                "doc036_aggregate_domain_count",
                "supersession_count",
            },
            "successor era repair counts",
        )
        observed = (
            counts["semantically_incompatible_local_proof_count"],
            counts["incomplete_fragment_terminal_count"],
            counts["composed_fragment_count"],
            counts["doc036_aggregate_domain_count"],
            counts["supersession_count"],
        )
        expected_era_overlays = [
            overlay
            for overlay in overlays
            if overlay["predecessor_era_id"] == era_row["era_id"]
        ]
        expected_overlay_ids = [
            overlay["repair_overlay_id"] for overlay in expected_era_overlays
        ]
        expected_successor_ids = [
            row["successor_row_id"]
            for row in all_successors
            if overlay_by_position[row["document_source_position"]][
                "predecessor_era_id"
            ]
            == era_row["era_id"]
        ]
        expected_supersession_ids = [
            row["supersession_row_id"]
            for row in supersession_rows
            if overlay_by_position[row["document_source_position"]][
                "predecessor_era_id"
            ]
            == era_row["era_id"]
        ]
        _require(
            era_row["schema_version"] == ERA_SEAL_SCHEMA_VERSION
            and era_row["authority_kind"] == "PROSPECTIVE_NONAUTHORITY"
            and era_row["successor_era_seal_identity_preimage"]
            == [
                ERA_SEAL_SCHEMA_VERSION,
                era_row["era_id"],
                era_row["era_order_position"],
                era_row["predecessor_era_seal_identity"],
                era_row["repair_overlay_ids"],
                era_row["successor_row_ids"],
                era_row["supersession_row_ids"],
                era_row["repair_counts"],
                AMENDMENT12_RATIFICATION_IDENTITY,
                governing_identity,
            ]
            and era_row["successor_era_seal_id"]
            == _content_id(
                "a13-successor-era-seal",
                era_row["successor_era_seal_identity_preimage"],
            )
            and era_row["amendment12_ratification_identity"]
            == AMENDMENT12_RATIFICATION_IDENTITY
            and era_row["governing_amendment13_ratification_identity"]
            == governing_identity
            and era_row["repair_overlay_ids"] == expected_overlay_ids
            and era_row["successor_row_ids"] == expected_successor_ids
            and era_row["supersession_row_ids"] == expected_supersession_ids
            and all(
                overlay["predecessor_era_seal_content_sha256"]
                == era_row["predecessor_era_seal_identity"]["content_sha256"]
                for overlay in expected_era_overlays
            )
            and observed == EXPECTED_ERA_COUNTS[era_row["era_id"]]
            and era_row["all_named_domains_present_even_when_empty"] is True,
            "successor era cascade or zero-era seal drift",
        )
    _require(
        Counter(
            row_id
            for era_row in era_rows
            for row_id in era_row["repair_overlay_ids"]
        )
        == Counter({row["repair_overlay_id"]: 1 for row in overlays})
        and Counter(
            row_id
            for era_row in era_rows
            for row_id in era_row["successor_row_ids"]
        )
        == Counter({row_id: 1 for row_id in successor_by_id})
        and Counter(
            row_id
            for era_row in era_rows
            for row_id in era_row["supersession_row_ids"]
        )
        == Counter(
            {row["supersession_row_id"]: 1 for row in supersession_rows}
        ),
        "repair rows lack unique era-seal membership",
    )

    _require(
        law["untouched_law_gap_predecessor_ids"] == list(LAW_GAP_IDS),
        "fourteen out-of-scope law-gap predecessors changed",
    )
    touched_ids = {row["predecessor_row_id"] for row in all_successors} | {
        row["predecessor_row_id"] for row in supersession_rows
    }
    _require(
        not touched_ids & set(LAW_GAP_IDS),
        "law-gap predecessor entered the repair or supersession domain",
    )
    _require(
        law["amendment12_continuation_domain"]
        == {
            "disjoint_and_unchanged": True,
            "continuation_citation_count": 5,
            "continuation_restoration_count": 3,
            "source_artifact_identity": {
                "path": A12_SWEEP_PATH,
                "byte_size": A12_SWEEP_BYTE_SIZE,
                "raw_sha256": A12_SWEEP_SHA256,
            },
            "continuation_projection_rows": [
                list(row) for row in _amendment12_continuation_projection()
            ],
            "continuation_projection_byte_size": (
                A12_CONTINUATION_PROJECTION_BYTE_SIZE
            ),
            "continuation_projection_sha256": (
                A12_CONTINUATION_PROJECTION_SHA256
            ),
            "new_fragment_predecessor_evidence_ids_disjoint": True,
            "new_fragment_instruction_occurrence_ids_disjoint": True,
        },
        "Amendment-12 continuation domain was disturbed",
    )
    order = law["git_order_law"]
    _require_exact_keys(
        order,
        {
            "amendment12_ratification_commit_must_be_strict_ancestor_of_governing_amendment13_ratification_commit",
            "governing_amendment13_ratification_commit_must_be_validated_and_strict_ancestor_of_every_overlay_first_add",
            "overlay_first_add_must_be_strict_ancestor_of_containing_era_successor_seal_first_add",
            "all_six_successor_seal_first_adds_must_be_strict_ancestors_of_tier2_evidence_first_add",
            "ratification_and_execution_record_commits_must_be_single_parent",
            "source_seal_identity_is_independently_authenticated_not_promoted_from_tier1",
            "dual_independent_reconstruction_required",
            "complete_raw_byte_attestation_required",
            "q5_first_add_permitted",
        },
        "Git-order law",
    )
    _require(
        all(
            value is True
            for key, value in order.items()
            if key != "q5_first_add_permitted"
        )
        and order["q5_first_add_permitted"] is False,
        "A12-T2-R05 ordering or pre-Q5 stop was weakened",
    )

    integrity = law["integrity"]
    _require_exact_keys(
        integrity,
        {
            "incompatible_proof_count",
            "incompatible_proof_id_domain_sha256",
            "incomplete_fragment_count",
            "composed_fragment_count",
            "fragment_evidence_id_domain_sha256",
            "fragment_instruction_id_domain_sha256",
            "doc036_aggregate_domain_count",
            "doc036_classification_id_domain_sha256",
            "repair_count",
            "supersession_count",
            "overlay_count",
            "successor_era_seal_count",
            "law_gap_untouched_count",
            "law_gap_id_domain_sha256",
            "successor_domain_sha256",
            "supersession_domain_sha256",
            "overlay_domain_sha256",
            "successor_era_seal_domain_sha256",
        },
        "execution-law integrity",
    )
    _require(
        integrity["incompatible_proof_count"] == 28
        and integrity["incompatible_proof_id_domain_sha256"]
        == INCOMPATIBLE_PROOF_ID_DOMAIN_SHA256
        and integrity["incomplete_fragment_count"] == 8
        and integrity["composed_fragment_count"] == 2
        and integrity["fragment_evidence_id_domain_sha256"]
        == FRAGMENT_EVIDENCE_ID_DOMAIN_SHA256
        and integrity["fragment_instruction_id_domain_sha256"]
        == FRAGMENT_INSTRUCTION_ID_DOMAIN_SHA256
        and integrity["doc036_aggregate_domain_count"] == 8
        and integrity["doc036_classification_id_domain_sha256"]
        == DOC036_CLASSIFICATION_ID_DOMAIN_SHA256
        and integrity["repair_count"] == 46
        and integrity["supersession_count"] == 46
        and integrity["overlay_count"] == 14
        and integrity["successor_era_seal_count"] == 6
        and integrity["law_gap_untouched_count"] == 14
        and integrity["law_gap_id_domain_sha256"] == LAW_GAP_ID_DOMAIN_SHA256
        and (
            not is_candidate_fixture
            or (
                integrity["overlay_domain_sha256"]
                == EXPECTED_OVERLAY_DOMAIN_SHA256
                and integrity["successor_domain_sha256"]
                == EXPECTED_SUCCESSOR_DOMAIN_SHA256
                and integrity["supersession_domain_sha256"]
                == EXPECTED_SUPERSESSION_DOMAIN_SHA256
                and integrity["successor_era_seal_domain_sha256"]
                == EXPECTED_ERA_SEAL_DOMAIN_SHA256
            )
        ),
        "fixed repair-domain integrity drift",
    )
    _require(
        integrity["successor_domain_sha256"] == _domain_sha(all_successors)
        and integrity["supersession_domain_sha256"]
        == _domain_sha(supersession_rows)
        and integrity["overlay_domain_sha256"] == _domain_sha(overlays)
        and integrity["successor_era_seal_domain_sha256"]
        == _domain_sha(era_rows),
        "derived execution-law integrity drift",
    )
    expected_law = _construct_execution_law(
        governing_amendment13_ratification_identity=governing_identity,
        status=expected_status,
    )
    _require(
        law == expected_law,
        "source-derived execution law drift",
    )


def _repin_successor(row: dict[str, Any]) -> None:
    row["successor_identity_preimage"][-1] = copy.deepcopy(
        row["successor_payload"]
    )
    row["successor_row_id"] = _content_id(
        "a13-repair-successor", row["successor_identity_preimage"]
    )


def run_mutation_tests(law: Mapping[str, Any]) -> tuple[str, ...]:
    """Run Amendment 13's separate seven-attack forgery inventory."""

    rejected: list[str] = []

    def reject(
        name: str,
        mutate: Any,
        expected_message: str,
        *,
        verify_git: bool = False,
    ) -> None:
        candidate = copy.deepcopy(law)
        mutate(candidate)
        try:
            validate_execution_law(candidate, verify_git=verify_git)
        except LawError as error:
            _require(
                expected_message in str(error),
                f"mutation failed an unintended gate: {name}: {error}",
            )
            rejected.append(name)
            return
        raise LawError(f"mutation survived: {name}")

    reject(
        "ratification_identity_wrong_blob",
        lambda value: value["amendment12_ratification_identity"].update(
            {
                "document_blob_oid": (
                    "dc0ce837e64239d16ea61c15d47450b7341d1ce8"
                ),
                "document_byte_size": 3_557_513,
                "document_sha256": (
                    "b06e64e314645300458b6e1c72df23c9bd5090b376f676d1e492312135782d87"
                ),
            }
        ),
        "ratification commit does not select the supplied document blob",
        verify_git=True,
    )
    reject(
        "ratification_identity_wrong_commit",
        lambda value: value["amendment12_ratification_identity"].update(
            {
                "ratification_commit": (
                    "a16f6089eca06e98bf18b8238f056bb6effae383"
                ),
                "ratification_parents": [RATIFICATION_COMMIT],
            }
        ),
        "ratification identity is not the exact attested document identity",
        verify_git=True,
    )
    reject(
        "ratification_identity_multiple_parents",
        lambda value: value["amendment12_ratification_identity"][
            "ratification_parents"
        ].append("0000000000000000000000000000000000000000"),
        "ratification identity does not name one parent",
        verify_git=True,
    )

    def forge_status(value: dict[str, Any]) -> None:
        row = value["semantically_incompatible_local_proof_successor_rows"][0]
        row["successor_payload"][
            "terminal_status"
        ] = "local_resolved_cross_reference_for_global_assembly"
        _repin_successor(row)

    reject(
        "successor_terminal_status_forged",
        forge_status,
        "forged incompatible-proof terminal status or admission",
    )

    def erase_predecessor(value: dict[str, Any]) -> None:
        row = value["predecessor_supersession_rows"][0]
        row["predecessor_retained"] = False
        row["predecessor_erasure_permitted"] = True
        row["supersession_identity_preimage"][-2:] = [False, True]
        row["supersession_row_id"] = _content_id(
            "a13-supersession", row["supersession_identity_preimage"]
        )

    reject(
        "predecessor_supersession_erasure",
        erase_predecessor,
        "supersession erases or fails to select",
    )

    def forge_selector(value: dict[str, Any]) -> None:
        row = value["composed_fragment_successor_rows"][0]
        citation = row["successor_payload"]["composition_citation"]
        citation["selected_leading_occurrence_id"] = citation[
            "candidate_occurrences_in_source_order"
        ][1]["occurrence_id"]
        citation["leading_occurrence_id"] = citation[
            "selected_leading_occurrence_id"
        ]
        _repin_successor(row)

    reject(
        "fragment_duplicate_selector_forged",
        forge_selector,
        "fragment duplicate selector forgery",
    )

    def forge_composition(value: dict[str, Any]) -> None:
        row = value["composed_fragment_successor_rows"][0]
        citation = row["successor_payload"]["composition_citation"]
        citation["gap_text"] = ""
        citation["gap_utf8_sha256"] = _sha256(b"")
        citation["combined_text"] = citation["combined_text"].replace(
            "\n                ", ""
        )
        citation["combined_utf8_sha256"] = _sha256(
            citation["combined_text"].encode("utf-8")
        )
        _repin_successor(row)

    reject(
        "fragment_composition_transformation_forged",
        forge_composition,
        "fragment composition transformation forgery",
    )
    _require(
        tuple(rejected) == A13_EXPECTED_MUTATIONS,
        "Amendment-13 mutation inventory drift",
    )
    return tuple(rejected)


def _scratch_git(
    cwd: Path,
    *arguments: str,
    text: bool = True,
) -> bytes | str:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=text,
        env=environment,
    )
    _require(
        result.returncode == 0,
        f"scratch git command failed: {' '.join(arguments)}: {result.stderr}",
    )
    return result.stdout


def _new_scratch_repo(original_root: Path, temporary_root: Path) -> Path:
    scratch = temporary_root / "repo"
    _scratch_git(
        temporary_root,
        "clone",
        "--quiet",
        "--no-hardlinks",
        str(original_root),
        str(scratch),
    )
    _scratch_git(scratch, "config", "user.name", "A13 mutation test")
    _scratch_git(
        scratch,
        "config",
        "user.email",
        "a13-mutation@example.invalid",
    )
    return scratch


def _expect_law_error(
    action: Callable[[], Any],
    expected_message: str,
    label: str,
) -> None:
    try:
        action()
    except LawError as error:
        _require(
            expected_message in str(error),
            f"{label} failed an unintended gate: {error}",
        )
    else:
        raise LawError(f"{label} survived")


def _run_coherent_suffix_enforcement_mutation(
    forged_document: bytes,
    semantic_law: Mapping[str, Any],
    *,
    expected_message: str = "Amendment-15 document violates immutable-prefix law",
) -> None:
    _expect_law_error(
        lambda: _validate_document_semantic_projection(
            forged_document, semantic_law
        ),
        expected_message,
        "coherently repinned suffix semantic mutation",
    )


def _synthetic_verdict_bytes(
    closure: Mapping[str, Any],
    reviewer: str,
) -> bytes:
    return (
        "# RATIFY\n"
        f"reviewer: {reviewer}\n"
        "attested_design_byte_size: "
        f"{closure['attested_candidate_design_byte_size']}\n"
        "attested_design_blob_oid: "
        f"{closure['attested_candidate_design_blob_oid']}\n"
        "attested_design_raw_sha256: "
        f"{closure['attested_candidate_design_raw_sha256']}\n"
    ).encode()


def _closure_binding(path: str, raw: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "raw_byte_size": len(raw),
        "raw_sha256": _sha256(raw),
    }


def _synthetic_registry_design_binding(
    closure: Mapping[str, Any],
    *,
    revision: int | None = None,
) -> dict[str, Any]:
    """Build one private terminal binding for pure closure tests."""

    if revision is None:
        revision = closure["amendment_number"] + 2
    amendment_numbers = _ratification_amendment_numbers(revision)
    return {
        "path": DESIGN_PATH,
        "ratification_commit": closure["ratification_commit"],
        "revision": revision,
        "blob_sha256": closure["attested_candidate_design_raw_sha256"],
        "ratification_closures": [
            {
                "path": _ratification_closure_path(amendment_number),
                "raw_byte_size": amendment_number,
                "raw_sha256": f"{amendment_number:064x}",
            }
            for amendment_number in amendment_numbers
        ],
    }


def _synthetic_closure_material(
    amendment_number: int = 14,
    *,
    design_raw: bytes | None = None,
) -> tuple[
    dict[str, Any],
    bytes,
    dict[str, Any],
    dict[str, bytes],
    bytes,
]:
    if design_raw is None:
        if amendment_number == 14:
            design_raw = _git(
                "show",
                f"{A14_MERGED_RATIFICATION_COMMIT}:{DESIGN_PATH}",
            )
        elif amendment_number == 15:
            design_raw = _git(
                "show",
                f"{A15_MERGED_RATIFICATION_COMMIT}:{DESIGN_PATH}",
            )
        else:
            design_raw = (ROOT / DESIGN_PATH).read_bytes()
    _require(
        isinstance(design_raw, bytes),
        "synthetic closure design bytes are unavailable",
    )
    closure = {
        "amendment_number": amendment_number,
        "attested_candidate_design_blob_oid": _git_blob_oid(design_raw),
        "attested_candidate_design_byte_size": len(design_raw),
        "attested_candidate_design_raw_sha256": _sha256(design_raw),
        "operator_merge_commit": A13_MERGED_RATIFICATION_COMMIT,
        "ratification_commit": A13_MERGED_RATIFICATION_COMMIT,
        "ratification_commit_sole_parent": A13_MERGED_RATIFICATION_PARENT,
        "verdict_artifacts": [],
    }
    directory = f"docs/analysis/amendment_{amendment_number}_ratification"
    verdict_bytes: dict[str, bytes] = {}
    for position in (1, 2):
        path = f"{directory}/synthetic-r{position}-verdict.md"
        raw = _synthetic_verdict_bytes(closure, f"synthetic-{position}")
        verdict_bytes[path] = raw
        closure["verdict_artifacts"].append(
            {
                "path": path,
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
            }
        )
    closure_raw = canonical_json_bytes(closure)
    closure_path = f"{directory}/closure_v1.json"
    return (
        closure,
        closure_raw,
        _closure_binding(closure_path, closure_raw),
        verdict_bytes,
        design_raw,
    )


def _synthetic_oracle_context(
    revision: int,
    amendment_numbers: Sequence[int],
    *,
    ratification_commit: str = A13_MERGED_RATIFICATION_COMMIT,
    blob_sha256: str = REVISION17_SHA256,
) -> dict[str, Any]:
    """Build a shape-valid private context without invoking the oracle."""

    context = {
        "path": DESIGN_PATH,
        "ratification_commit": ratification_commit,
        "revision": revision,
        "blob_sha256": blob_sha256,
        "ratification_closures": [
            {
                "path": _ratification_closure_path(amendment_number),
                "raw_byte_size": amendment_number,
                "raw_sha256": f"{amendment_number:064x}",
            }
            for amendment_number in amendment_numbers
        ],
    }
    if revision >= COMBINED_ACTIVATION_REVISION and 14 in amendment_numbers:
        position = tuple(amendment_numbers).index(14)
        context["ratification_closures"][position] = copy.deepcopy(
            A14_HISTORICAL_CLOSURE_BINDING
        )
    return context


def _run_amendment16_oracle_attacks() -> tuple[str, ...]:
    """Execute only A16's separate seven revision-general attacks."""

    rejected: list[str] = []

    ordinary_domain = tuple(range(13, 18))
    too_few = _synthetic_oracle_context(19, ordinary_domain)
    too_few["ratification_closures"].pop()
    _expect_law_error(
        lambda: _validate_registry_ratification_context(too_few),
        "registry ratification closure count drift",
        "revision-general too-few closure mutation",
    )
    too_many = _synthetic_oracle_context(19, ordinary_domain)
    too_many["ratification_closures"].append(
        {
            "path": _ratification_closure_path(18),
            "raw_byte_size": 18,
            "raw_sha256": f"{18:064x}",
        }
    )
    _expect_law_error(
        lambda: _validate_registry_ratification_context(too_many),
        "registry ratification closure count drift",
        "revision-general too-many closure mutation",
    )
    rejected.append(A16_EXPECTED_MUTATIONS[0])

    wrong_order = _synthetic_oracle_context(19, ordinary_domain)
    wrong_order["ratification_closures"][2:4] = reversed(
        wrong_order["ratification_closures"][2:4]
    )
    _expect_law_error(
        lambda: _validate_registry_ratification_context(wrong_order),
        "registry ratification closure binding order drift",
        "revision-general closure-order mutation",
    )
    rejected.append(A16_EXPECTED_MUTATIONS[1])

    revision17_raw = _git(
        "show",
        f"{A15_MERGED_RATIFICATION_COMMIT}:{DESIGN_PATH}",
    )
    _require(
        isinstance(revision17_raw, bytes),
        "Amendment-16 mutation setup lacks revision-17 design bytes",
    )
    (
        forged_a16,
        forged_a16_raw,
        forged_a16_binding,
        forged_a16_verdicts,
        forged_a16_design,
    ) = _synthetic_closure_material(16, design_raw=revision17_raw)
    forged_a16_context = _synthetic_oracle_context(
        18,
        tuple(range(13, 17)),
        ratification_commit=forged_a16["ratification_commit"],
        blob_sha256=forged_a16["attested_candidate_design_raw_sha256"],
    )
    _expect_law_error(
        lambda: _validate_ratification_closure(
            forged_a16_raw,
            forged_a16_binding,
            forged_a16_verdicts,
            16,
            verify_git=False,
            ratification_design_raw=forged_a16_design,
            registry_design_binding=forged_a16_context,
        ),
        "attests terminal Amendment 15 instead of Amendment 16",
        "non-A13 closure relabeling mutation",
    )
    rejected.append(A16_EXPECTED_MUTATIONS[2])

    revision18_raw = (ROOT / DESIGN_PATH).read_bytes()[:REVISION18_BYTE_SIZE]
    (
        forged_a17,
        forged_a17_raw,
        forged_a17_binding,
        forged_a17_verdicts,
        forged_a17_design,
    ) = _synthetic_closure_material(17, design_raw=revision18_raw)
    forged_a17_context = _synthetic_oracle_context(
        19,
        ordinary_domain,
        ratification_commit=forged_a17["ratification_commit"],
        blob_sha256=forged_a17["attested_candidate_design_raw_sha256"],
    )
    _expect_law_error(
        lambda: _validate_ratification_closure(
            forged_a17_raw,
            forged_a17_binding,
            forged_a17_verdicts,
            17,
            verify_git=False,
            ratification_design_raw=forged_a17_design,
            registry_design_binding=forged_a17_context,
        ),
        "attests terminal Amendment 16 instead of Amendment 17",
        "nonterminal registry/design relation mutation",
    )
    rejected.append(A16_EXPECTED_MUTATIONS[3])

    missing_combined = _synthetic_oracle_context(
        18,
        tuple(range(13, 17)),
    )
    missing_combined["ratification_closures"].pop(2)
    _expect_law_error(
        lambda: _validate_registry_ratification_context(missing_combined),
        "registry ratification closure count drift",
        "combined revision-18 missing-closure mutation",
    )
    rejected.append(A16_EXPECTED_MUTATIONS[4])

    amendment15_alone = _synthetic_oracle_context(
        17,
        tuple(range(13, 16)),
    )
    _expect_law_error(
        lambda: _validate_registry_ratification_context(amendment15_alone),
        "revision 17 cannot be a terminal ratification registry",
        "Amendment-15-alone activation mutation",
    )
    rejected.append(A16_EXPECTED_MUTATIONS[5])

    import covered_earnings_correction_registry as registry

    amendment16_alone = _synthetic_oracle_context(18, (16,))
    original_design_binding = registry.design_binding
    registry.design_binding = lambda: copy.deepcopy(amendment16_alone)
    try:
        _expect_law_error(
            lambda: validate_amendment_ratification_closure(16),
            "registry ratification closure count drift",
            "Amendment-16-alone selector mutation",
        )
    finally:
        registry.design_binding = original_design_binding
    rejected.append(A16_EXPECTED_MUTATIONS[6])

    rejected_tuple = tuple(rejected)
    _require(
        rejected_tuple == A16_EXPECTED_MUTATIONS
        and len(set(rejected_tuple)) == len(rejected_tuple)
        and _sha256(canonical_json_bytes(list(rejected_tuple)))
        == A16_MUTATION_DOMAIN_SHA256,
        "Amendment-16 oracle mutation inventory drift",
    )
    return rejected_tuple


def run_amendment16_oracle_mutation_tests() -> tuple[str, ...]:
    """Authenticate the inherited census, then execute seven A16 attacks."""

    import build_amendment13_tier2_repairs as publisher

    inherited_census = publisher.run_complete_mutation_census()
    _require(
        inherited_census == publisher._expected_mutation_census()
        and len(inherited_census["components"]) == 3
        and inherited_census["rejected_count"]
        == A16_RATIFICATION_LAW_VALUES["inherited_complete_mutation_count"]
        and inherited_census["rejected_domain_sha256"]
        == A16_RATIFICATION_LAW_VALUES[
            "inherited_complete_mutation_domain_sha256"
        ],
        "Amendment-16 inherited complete mutation census drift",
    )
    return _run_amendment16_oracle_attacks()


def _run_public_registry_replace_ref_enforcement_mutation() -> None:
    """Reject substituted HEAD design bytes at the public registry gate."""

    global ROOT

    import covered_earnings_correction_registry as registry

    original_root = ROOT
    original_registry_state = {
        "ROOT": registry.ROOT,
        "DESIGN_RATIFICATION_COMMIT": registry.DESIGN_RATIFICATION_COMMIT,
        "DESIGN_REVISION": registry.DESIGN_REVISION,
        "DESIGN_BLOB_SHA256": registry.DESIGN_BLOB_SHA256,
    }
    with tempfile.TemporaryDirectory(
        prefix="a14-public-replace-ref-"
    ) as temporary:
        temporary_root = Path(temporary)
        scratch = _new_scratch_repo(original_root, temporary_root)
        expected_design = (scratch / DESIGN_PATH).read_bytes()
        replacement_commit = str(
            _scratch_git(scratch, "rev-parse", "HEAD")
        ).strip()
        forged_design_path = temporary_root / "forged-head-design.md"
        forged_design = expected_design + b"forged raw HEAD design\n"
        forged_design_path.write_bytes(forged_design)
        forged_design_blob = str(
            _scratch_git(
                scratch,
                "hash-object",
                "-w",
                str(forged_design_path),
            )
        ).strip()
        _scratch_git(scratch, "read-tree", "HEAD")
        _scratch_git(
            scratch,
            "update-index",
            "--add",
            "--cacheinfo",
            f"{DESIGN_MODE},{forged_design_blob},{DESIGN_PATH}",
        )
        forged_tree = str(_scratch_git(scratch, "write-tree")).strip()
        forged_commit = str(
            _scratch_git(
                scratch,
                "commit-tree",
                forged_tree,
                "-p",
                replacement_commit,
                "-m",
                "Raw HEAD with forged design",
            )
        ).strip()
        _scratch_git(scratch, "update-ref", "HEAD", forged_commit)
        _scratch_git(scratch, "replace", forged_commit, replacement_commit)

        ordinary_head_design = _scratch_git(
            scratch,
            "show",
            f"HEAD:{DESIGN_PATH}",
            text=False,
        )
        ordinary_ratified_design = _scratch_git(
            scratch,
            "show",
            f"{forged_commit}:{DESIGN_PATH}",
            text=False,
        )
        raw_head_design = _scratch_git(
            scratch,
            "--no-replace-objects",
            "show",
            f"HEAD:{DESIGN_PATH}",
            text=False,
        )
        _require(
            ordinary_head_design == ordinary_ratified_design == expected_design
            and raw_head_design == forged_design,
            "public replacement-ref design attack control did not conform",
        )

        ROOT = scratch
        registry.ROOT = scratch
        registry.DESIGN_RATIFICATION_COMMIT = forged_commit
        registry.DESIGN_REVISION = 16
        registry.DESIGN_BLOB_SHA256 = _sha256(expected_design)
        try:
            _expect_law_error(
                _public_registry_ratification_context,
                "registry ratification closure binding is missing",
                "public registry replacement-ref design mutation",
            )
        finally:
            ROOT = original_root
            for name, value in original_registry_state.items():
                setattr(registry, name, value)


def _run_replace_ref_enforcement_mutation() -> None:
    """Exercise private closure and public registry replacement attacks."""

    global ROOT

    original_root = ROOT
    with tempfile.TemporaryDirectory(prefix="a14-replace-ref-") as temporary:
        temporary_root = Path(temporary)
        scratch = _new_scratch_repo(original_root, temporary_root)
        (
            closure,
            _,
            _,
            verdict_bytes,
            ratification_design,
        ) = _synthetic_closure_material()
        expected_design_path = temporary_root / "expected-design.md"
        expected_design_path.write_bytes(ratification_design)
        expected_design_blob = str(
            _scratch_git(
                scratch,
                "hash-object",
                "-w",
                str(expected_design_path),
            )
        ).strip()
        _scratch_git(scratch, "read-tree", "HEAD")
        _scratch_git(
            scratch,
            "update-index",
            "--add",
            "--cacheinfo",
            f"{DESIGN_MODE},{expected_design_blob},{DESIGN_PATH}",
        )
        expected_tree = str(_scratch_git(scratch, "write-tree")).strip()
        replacement_commit = str(
            _scratch_git(
                scratch,
                "commit-tree",
                expected_tree,
                "-p",
                A13_MERGED_RATIFICATION_PARENT,
                "-m",
                "Replacement-view ratification commit",
            )
        ).strip()
        forged_design_path = temporary_root / "forged-design.md"
        forged_design_path.write_bytes(ratification_design + b"forged\n")
        forged_design_blob = str(
            _scratch_git(
                scratch,
                "hash-object",
                "-w",
                str(forged_design_path),
            )
        ).strip()
        _scratch_git(
            scratch,
            "update-index",
            "--add",
            "--cacheinfo",
            f"{DESIGN_MODE},{forged_design_blob},{DESIGN_PATH}",
        )
        forged_tree = str(_scratch_git(scratch, "write-tree")).strip()
        wrong_parent = str(_scratch_git(scratch, "rev-parse", "HEAD")).strip()
        forged_commit = str(
            _scratch_git(
                scratch,
                "commit-tree",
                forged_tree,
                "-p",
                wrong_parent,
                "-m",
                "Raw commit with substituted parent",
            )
        ).strip()
        _scratch_git(
            scratch,
            "replace",
            forged_commit,
            replacement_commit,
        )
        ordinary_parent_line = str(
            _scratch_git(
                scratch,
                "rev-list",
                "--parents",
                "-n",
                "1",
                forged_commit,
            )
        ).split()
        _require(
            ordinary_parent_line
            == [forged_commit, A13_MERGED_RATIFICATION_PARENT],
            "replacement-ref parent attack control did not conform",
        )
        ordinary_tree_line = str(
            _scratch_git(
                scratch,
                "ls-tree",
                forged_commit,
                "--",
                DESIGN_PATH,
            )
        ).strip()
        _require(
            ordinary_tree_line
            == f"{DESIGN_MODE} blob {expected_design_blob}\t{DESIGN_PATH}",
            "replacement-ref design attack control did not conform",
        )
        closure["ratification_commit"] = forged_commit
        closure["operator_merge_commit"] = forged_commit
        ROOT = scratch
        try:
            parent_closure_raw = canonical_json_bytes(closure)
            _expect_law_error(
                lambda: _validate_ratification_closure(
                    parent_closure_raw,
                    _closure_binding(A14_CLOSURE_PATH, parent_closure_raw),
                    verdict_bytes,
                    14,
                    verify_git=True,
                    registry_design_binding=(
                        _synthetic_registry_design_binding(closure)
                    ),
                ),
                "sole-parent mismatch",
                "replacement-ref sole-parent mutation",
            )
            closure["ratification_commit_sole_parent"] = wrong_parent
            blob_closure_raw = canonical_json_bytes(closure)
            _expect_law_error(
                lambda: _validate_ratification_closure(
                    blob_closure_raw,
                    _closure_binding(A14_CLOSURE_PATH, blob_closure_raw),
                    verdict_bytes,
                    14,
                    verify_git=True,
                    registry_design_binding=(
                        _synthetic_registry_design_binding(closure)
                    ),
                ),
                "attests a different design blob",
                "replacement-ref selected-design mutation",
            )
        finally:
            ROOT = original_root

    _run_public_registry_replace_ref_enforcement_mutation()


def _run_implementation_blob_enforcement_mutation(
    implementation_pins: Mapping[str, Any],
) -> None:
    """Change one committed implementation blob behind the enacted pin."""

    global ROOT

    original_root = ROOT
    with tempfile.TemporaryDirectory(
        prefix="a14-implementation-"
    ) as temporary:
        temporary_root = Path(temporary)
        scratch = _new_scratch_repo(original_root, temporary_root)
        selected_path = implementation_pins["files"][0]["path"]
        selected_file = scratch / selected_path
        selected_file.write_bytes(selected_file.read_bytes() + b"# forged\n")
        _scratch_git(scratch, "add", selected_path)
        _scratch_git(
            scratch,
            "commit",
            "--quiet",
            "-m",
            "Forge implementation blob",
        )
        ROOT = scratch
        try:
            _expect_law_error(
                lambda: _verify_implementation_pins(implementation_pins),
                "HEAD tree-entry pin drift",
                "implementation blob mismatch mutation",
            )
        finally:
            ROOT = original_root


def run_enforcement_mutation_tests(
    law: Mapping[str, Any],
) -> tuple[str, ...]:
    """Run the exact Amendment-14 enforcement mutation inventory."""

    rejected: list[str] = []
    raw_document = (ROOT / DESIGN_PATH).read_bytes()
    (
        synthetic_closure,
        synthetic_raw,
        synthetic_binding,
        synthetic_verdicts,
        design_raw,
    ) = _synthetic_closure_material()
    synthetic_registry_binding = _synthetic_registry_design_binding(
        synthetic_closure
    )

    forged_raw = raw_document.replace(
        (
            b"The same operator\norchestrates both runs and performs the "
            b"merge and repin."
        ),
        (
            b"The same operator\norchestrates both runs and performs the "
            b"merge and repin and emits authority."
        ),
        1,
    )
    _require(
        forged_raw != raw_document,
        "suffix semantic mutation did not apply",
    )
    _run_coherent_suffix_enforcement_mutation(forged_raw, law)
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[0])

    pin_boundary = (
        b"\n\nFor each row, the validator requires the enacted path and mode"
    )
    forged_pin_raw = raw_document.replace(
        pin_boundary,
        (
            b"\n\nThe exact enforcement override status is "
            b"`FORGED_RATIFIED_AUTHORITY`; authority is emitted."
            + pin_boundary
        ),
        1,
    )
    _require(
        forged_pin_raw != raw_document,
        "implementation-pin interval mutation did not apply",
    )
    _run_coherent_suffix_enforcement_mutation(forged_pin_raw, law)
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[1])

    forged_identifier_raw = raw_document.replace(
        (
            b"The exact Amendment-14 schema and binding identifiers are:"
            b"\n\n~~~text\n"
            b"covered_earnings_amendment_ratification_closure.v1"
        ),
        (
            b"The exact Amendment-14 schema and binding identifiers are:"
            b"\n\n~~~text\n"
            b"covered_earnings_amendment_ratification_closure.v2"
        ),
        1,
    )
    _require(
        forged_identifier_raw != raw_document,
        "identifier-inventory mutation did not apply",
    )
    _run_coherent_suffix_enforcement_mutation(
        forged_identifier_raw,
        law,
        expected_message="identifier inventory consistency drift",
    )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[2])

    _run_replace_ref_enforcement_mutation()
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[3])

    missing_verdicts = dict(synthetic_verdicts)
    missing_verdicts.pop(next(iter(missing_verdicts)))
    _expect_law_error(
        lambda: _validate_ratification_closure(
            synthetic_raw,
            synthetic_binding,
            missing_verdicts,
            14,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=synthetic_registry_binding,
        ),
        "verdict artifact domain drift",
        "missing verdict artifact mutation",
    )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[4])

    _expect_law_error(
        lambda: _validate_ratification_closure(
            None,
            synthetic_binding,
            synthetic_verdicts,
            14,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=synthetic_registry_binding,
        ),
        "ratification closure is missing",
        "missing ratification closure mutation",
    )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[5])

    mismatched_verdicts = dict(synthetic_verdicts)
    first_path = synthetic_closure["verdict_artifacts"][0]["path"]
    mismatched_verdicts[first_path] += b"forged\n"
    _expect_law_error(
        lambda: _validate_ratification_closure(
            synthetic_raw,
            synthetic_binding,
            mismatched_verdicts,
            14,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=synthetic_registry_binding,
        ),
        "verdict byte mismatch",
        "closure verdict byte mismatch mutation",
    )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[6])

    wrong_blob = copy.deepcopy(synthetic_closure)
    wrong_blob["attested_candidate_design_blob_oid"] = "0" * 40
    wrong_blob_verdicts: dict[str, bytes] = {}
    for position, row in enumerate(wrong_blob["verdict_artifacts"], 1):
        raw = _synthetic_verdict_bytes(
            wrong_blob,
            f"wrong-blob-{position}",
        )
        wrong_blob_verdicts[row["path"]] = raw
        row["byte_size"] = len(raw)
        row["raw_sha256"] = _sha256(raw)
    wrong_blob_raw = canonical_json_bytes(wrong_blob)
    wrong_blob_binding = _closure_binding(A14_CLOSURE_PATH, wrong_blob_raw)
    _expect_law_error(
        lambda: _validate_ratification_closure(
            wrong_blob_raw,
            wrong_blob_binding,
            wrong_blob_verdicts,
            14,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=_synthetic_registry_design_binding(
                wrong_blob
            ),
        ),
        "design byte identity mismatch",
        "closure attested design blob mutation",
    )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[7])

    for schema_forgery in ("extra", "missing"):
        forged_schema = copy.deepcopy(synthetic_closure)
        if schema_forgery == "extra":
            forged_schema["extra"] = True
        else:
            del forged_schema["operator_merge_commit"]
        forged_schema_raw = canonical_json_bytes(forged_schema)
        forged_schema_binding = _closure_binding(
            A14_CLOSURE_PATH, forged_schema_raw
        )
        _expect_law_error(
            lambda raw=forged_schema_raw, binding=forged_schema_binding: (
                _validate_ratification_closure(
                    raw,
                    binding,
                    synthetic_verdicts,
                    14,
                    verify_git=False,
                    ratification_design_raw=design_raw,
                    registry_design_binding=synthetic_registry_binding,
                )
            ),
            "ratification closure keyset drift",
            f"closure schema {schema_forgery}-key mutation",
        )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[8])

    projection = _parse_amendment14_projection(raw_document)
    _run_implementation_blob_enforcement_mutation(
        projection["implementation_pins"]
    )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[9])

    substituted_verdicts = {
        path: raw + b"coherent substitution\n"
        for path, raw in synthetic_verdicts.items()
    }
    substituted_closure = copy.deepcopy(synthetic_closure)
    for row in substituted_closure["verdict_artifacts"]:
        raw = substituted_verdicts[row["path"]]
        row["byte_size"] = len(raw)
        row["raw_sha256"] = _sha256(raw)
    substituted_raw = canonical_json_bytes(substituted_closure)
    _expect_law_error(
        lambda: _validate_ratification_closure(
            substituted_raw,
            synthetic_binding,
            substituted_verdicts,
            14,
            verify_git=False,
            ratification_design_raw=design_raw,
            registry_design_binding=synthetic_registry_binding,
        ),
        "bytes differ from the registry repin",
        "coherent closure substitution against fixed repin",
    )

    a13_closure = copy.deepcopy(A13_EXPECTED_CLOSURE)
    a13_verdicts = {
        row["path"]: (ROOT / row["path"]).read_bytes()
        for row in a13_closure["verdict_artifacts"]
    }
    substituted_a13_verdicts = {
        path: raw + b"coherent substitution\n"
        for path, raw in a13_verdicts.items()
    }
    for row in a13_closure["verdict_artifacts"]:
        raw = substituted_a13_verdicts[row["path"]]
        row["byte_size"] = len(raw)
        row["raw_sha256"] = _sha256(raw)
    substituted_a13_raw = canonical_json_bytes(a13_closure)
    substituted_a13_binding = _closure_binding(
        A13_CLOSURE_PATH, substituted_a13_raw
    )
    _expect_law_error(
        lambda: _validate_ratification_closure(
            substituted_a13_raw,
            substituted_a13_binding,
            substituted_a13_verdicts,
            13,
            verify_git=False,
            ratification_design_raw=design_raw,
        ),
        "differs from directly enacted values",
        "coherent A13 substitution against direct design pins",
    )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[10])

    _require(
        tuple(rejected) == A13_ENFORCEMENT_EXPECTED_MUTATIONS,
        "Amendment-14 enforcement mutation inventory drift",
    )
    return tuple(rejected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mutation-tests",
        action="store_true",
        help="run seven semantic and eleven enforcement forgery attacks",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="print the nonauthority fixture's counts and derived pins",
    )
    arguments = parser.parse_args()
    law = build_execution_law()
    validate_execution_law(law)
    rejected = run_mutation_tests(law) if arguments.mutation_tests else ()
    enforcement_rejected = (
        run_enforcement_mutation_tests(law) if arguments.mutation_tests else ()
    )
    if arguments.print_summary or arguments.mutation_tests:
        print(
            json.dumps(
                {
                    "status": law["status"],
                    "authority_emitted": law["authority_emitted"],
                    "integrity": law["integrity"],
                    "mutation_test_count": len(rejected)
                    + len(enforcement_rejected),
                    "semantic_mutation_test_count": len(rejected),
                    "enforcement_mutation_test_count": len(
                        enforcement_rejected
                    ),
                    "mutations_rejected": [
                        *rejected,
                        *enforcement_rejected,
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
