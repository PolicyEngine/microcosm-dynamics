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
import ast
import copy
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path, PurePosixPath
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
REVISION19_BYTE_SIZE = 3_934_849
REVISION19_SHA256 = (
    "29055c5606a54587107498e8adcdbc8546f93caceabe89238975288db72e7fe1"
)
REVISION19_BLOB_OID = "84b31290ecd2d1001b6ea802b9a97a86260cdfda"
AMENDMENT18_BOUNDARY = (
    b"\n## 32. AMENDMENT SECTION \xe2\x80\x94 Amendment 18: tier-2 "
    b"certification contract cure\n"
)
REVISION20_BYTE_SIZE = 3_964_278
REVISION20_SHA256 = (
    "631d3b2b8ecab1c29ec0595550a6d2b798f49ff96e74c722801d24c48ab111ec"
)
REVISION20_BLOB_OID = "016c0fff757b54da730ae0044216416cde2d2c33"
AMENDMENT19_BOUNDARY = (
    b"\n## 33. AMENDMENT SECTION \xe2\x80\x94 Amendment 19: source-"
    b"hierarchy member-construction cure\n"
)
REVISION21_BYTE_SIZE = 4_025_587
REVISION21_SHA256 = (
    "38139b8ddd24ef7be09e8f149960e8e0b6e39699d84f3783827eff6c294a9ae9"
)
REVISION21_BLOB_OID = "1eba7ff6366bad1999de36c9f7261ad6939ad86a"
AMENDMENT20_BOUNDARY = (
    b"\n## 34. AMENDMENT SECTION \xe2\x80\x94 Amendment 20: dual-authority "
    b"covered-earnings correction\n"
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
A15_HISTORICAL_CLOSURE_BINDING = {
    "path": A15_CLOSURE_PATH,
    "raw_byte_size": 842,
    "raw_sha256": (
        "f48ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a"
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
    "b2acce3c1e42d1e58b216cb8643fdc927c741b439621ed66053a1973ac092774"
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

A18_SECTION_SEMANTIC_SHA256 = (
    "44b547625392ecab203b03f68a217fc9f03c2a2ea7d3f9bd57b2ddc34bd72a4c"
)
A18_BUILD_INPUT_DOMAIN_CONTRACT = {
    "schema_version": "amendment_12_tier2_build_input_domain.v1",
    "canonicalization": "python-json-sort-keys-compact-ascii-no-nan-lf-v1",
    "envelope_keys": [
        "schema_version",
        "canonicalization",
        "questionnaire_document_count",
        "questionnaire_document_keyset_sha256",
        "questionnaire_document_domain_sha256",
        "source_document_count",
        "source_document_keyset_sha256",
        "source_document_domain_sha256",
        "repair_seal_evidence_count",
        "repair_seal_evidence_path_domain_sha256",
        "row_count",
        "rows",
    ],
    "row_keys": ["input_class", "input_identity"],
    "source_identity_keys": [
        "source_document_id",
        "document_role",
        "interview_waves",
        "canonical_source_path",
        "storage_disposition",
        "storage_identity",
        "byte_size",
        "sha256",
    ],
    "repair_identity_keys": [
        "path",
        "mode",
        "git_blob",
        "byte_size",
        "raw_sha256",
    ],
    "questionnaire_document_count": 81,
    "questionnaire_document_keyset_sha256": (
        "3326c9ba70b7f83f19b0ea934630d26ced73f230be1628cb74031d17160cb1a5"
    ),
    "questionnaire_document_domain_sha256": (
        "b06139b147391d06b4f90a8f28de472a936ec08b3e9eb37001a5a70e2b3c3543"
    ),
    "source_document_count": 257,
    "source_document_keyset_sha256": (
        "8b7cad855b791c5cd7d235a74d4a0f1ecc7511dc0458db11d6b04c1b6af2c36a"
    ),
    "source_document_domain_sha256": (
        "9d7a98db7c2889eba150f70935f492aebbc41cd521e4139dc1ec886ecd9945ce"
    ),
    "repair_seal_evidence_count": 22,
    "repair_seal_evidence_path_domain_sha256": (
        "504159116708ee4d5e2cc8abec130ca8679d22cce928dca42af12be305361c17"
    ),
    "row_count": 279,
    "input_classes": ["source_document", "repair_seal_evidence"],
    "source_position_domain": [0, 256],
    "repair_position_domain": [257, 278],
    "source_order": "document_role_wave_canonical_source_path_v1",
    "questionnaire_slice_role": "questionnaire_flow",
    "repair_order": "unsigned_utf8_repository_path",
    "digest_member": "tier2_build_input_domain_sha256",
    "dual_canonical_byte_equality_required": True,
    "artifact_persisted": False,
}
A18_HISTORICAL_R05_BINDING = {
    "amendment_number": 15,
    "closure_byte_size": 842,
    "closure_path": A15_CLOSURE_PATH,
    "closure_raw_sha256": (
        "f48ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a"
    ),
    "design_blob_oid": REVISION17_BLOB_OID,
    "design_byte_size": REVISION17_BYTE_SIZE,
    "design_path": DESIGN_PATH,
    "design_raw_sha256": REVISION17_SHA256,
    "design_revision": 17,
    "ratification_commit": A15_MERGED_RATIFICATION_COMMIT,
    "ratification_commit_sole_parent": A15_MERGED_RATIFICATION_PARENT,
}
A18_R06_RESULT_CONTRACT = {
    "path": (
        "docs/analysis/amendment_12_rq_catalog_tier2/certification/"
        "amendment11_expected_abort_result_v1.json"
    ),
    "mode": DESIGN_MODE,
    "schema_version": "amendment_12_tier2_r06_expected_abort_result.v1",
    "artifact_id_prefix": "a12-tier2-r06-expected-abort-result:",
    "artifact_role": (
        "evidence_expected_amendment11_abort_reproduced_nonauthority"
    ),
    "status": "pass_a12_t2_r06_expected_abort_reproduced",
    "gate_id": "A12-T2-R06",
    "canonicalization": "python-json-sort-keys-compact-ascii-no-nan-lf-v1",
    "top_level_keys": [
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
    ],
    "integrity_keys": ["canonicalization", "payload_sha256"],
    "payload_excluded_keys": ["artifact_id", "integrity"],
    "input_identity_keys": [
        "r05_certification",
        "amendment11_authority_artifact",
        "amendment11_replay_executable",
        "amendment11_source_registry",
    ],
    "input_identity_row_keys": [
        "path",
        "mode",
        "git_blob",
        "byte_size",
        "raw_sha256",
    ],
    "fixed_input_identities": {
        "amendment11_authority_artifact": {
            "path": "data/external/psid_missing_reason_code_authority_v1.json",
            "mode": DESIGN_MODE,
            "git_blob": "97e22fd1a91f521d7f7ac335fcd1212b3cb166ac",
            "byte_size": 709_526,
            "raw_sha256": (
                "833c8dca8cec6a44ea4fe6c65d3662ce8ef8b7da062350437cf4f538dc8b6dac"
            ),
        },
        "amendment11_replay_executable": {
            "path": "scripts/replay_amendment11_no_movement.py",
            "mode": DESIGN_MODE,
            "git_blob": "5fab6c62a3794b66ccb95599e409ccdf9a8b6044",
            "byte_size": 32_330,
            "raw_sha256": (
                "597670958b6609740eb4742c4144fb448026df82c767ece4db3e30777d6b77e6"
            ),
        },
        "amendment11_source_registry": {
            "path": (
                "data/external/"
                "psid_questionnaire_dictionary_inventory_registration_"
                "required_v1.json"
            ),
            "mode": DESIGN_MODE,
            "git_blob": "a2e6bfa8b19c35dfde235d8ece7e233a5d833e9e",
            "byte_size": 25_474_435,
            "raw_sha256": (
                "a974c6fb65a9f3d52387163f2e98b7cd8cfdbd57f5e95d1f766b3aa25d167ac0"
            ),
        },
    },
    "source_registry_projection": {
        "source_count": 47,
        "source_byte_size": 114_875_090,
        "registered_row_sha256": (
            "d5b67f8b6b95dded9d8987af5784ea93bdc4b05744c3338619dd3681b7e62957"
        ),
        "projected_row_sha256": (
            "0d27b2f940413d11727753a820360ac0a680eed503ea85bbe0a1344ed2f187e0"
        ),
    },
    "process_result_keys": [
        "command",
        "exit_code",
        "stdout_byte_size",
        "stdout_raw_sha256",
        "stderr_byte_size",
        "stderr_raw_sha256",
        "stderr_exact_text",
        "abort_code",
        "source_authorized_literal_count",
        "blocked_literal_count",
        "numeric_range_structural_null_count",
    ],
    "process_command": [
        sys.executable,
        "scripts/replay_amendment11_no_movement.py",
    ],
    "process_result": {
        "exit_code": 2,
        "stdout_byte_size": 0,
        "stdout_raw_sha256": (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ),
        "stderr_byte_size": 174,
        "stderr_raw_sha256": (
            "79c608eb8baf3b31ea8f14cf461cde27d8637e43602ead19e39dc5388ed9903b"
        ),
        "stderr_exact_text": (
            "blocked_source_missing_disposition_underdetermined: registered "
            "sources do not determine a missing disposition for 524538 "
            "literal entries; no complete settled relation exists\n"
        ),
        "abort_code": "blocked_source_missing_disposition_underdetermined",
        "source_authorized_literal_count": 52,
        "blocked_literal_count": 524_538,
        "numeric_range_structural_null_count": 37_283,
    },
    "process_integer_fields": [
        "exit_code",
        "stdout_byte_size",
        "stderr_byte_size",
        "source_authorized_literal_count",
        "blocked_literal_count",
        "numeric_range_structural_null_count",
    ],
    "test_result_keys": [
        "command",
        "environment",
        "module_paths",
        "module_path_domain_sha256",
        "module_count",
        "expected_collected",
        "exit_code",
        "collected",
        "passed",
        "failed",
        "skipped",
        "deselected",
        "xfailed",
        "xpassed",
    ],
    "test_module_paths": [
        "tests/data/test_psid_codebook_extraction_validation.py",
        "tests/data/test_psid_missing_reason_authority_artifact.py",
        "tests/data/test_psid_missing_reason_authority_unit.py",
        "tests/estimates/test_birth_evidence_artifact.py",
        "tests/test_rebuild_amendment11_missing_reason_authority.py",
        "tests/test_replay_amendment11_no_movement.py",
    ],
    "test_module_path_domain_sha256": (
        "a5099c464482c5b652e31e5dfa958703a4ae4c75c1dc1e4caa03cb2aef408063"
    ),
    "test_command": [
        sys.executable,
        "-m",
        "pytest",
        "tests/data/test_psid_codebook_extraction_validation.py",
        "tests/data/test_psid_missing_reason_authority_artifact.py",
        "tests/data/test_psid_missing_reason_authority_unit.py",
        "tests/estimates/test_birth_evidence_artifact.py",
        "tests/test_rebuild_amendment11_missing_reason_authority.py",
        "tests/test_replay_amendment11_no_movement.py",
    ],
    "test_environment": {"PYTHONPATH": "src:."},
    "test_result": {
        "module_count": 6,
        "expected_collected": 223,
        "exit_code": 0,
        "collected": 223,
        "passed": 223,
        "failed": 0,
        "skipped": 0,
        "deselected": 0,
        "xfailed": 0,
        "xpassed": 0,
    },
    "test_integer_fields": [
        "module_count",
        "expected_collected",
        "exit_code",
        "collected",
        "passed",
        "failed",
        "skipped",
        "deselected",
        "xfailed",
        "xpassed",
    ],
    "lifecycle_keys": [
        "nonauthority",
        "expected_abort_reproduced",
        "accepted_output_emitted",
        "production_replay_started",
        "movement_relation_emitted",
        "revision_13_relation_identity_emitted",
        "q5_input_emitted",
        "q5_first_add_performed",
        "full_g17_c01_row_emitted",
        "authority_emitted",
        "production_output_emitted",
        "next_required_state",
    ],
    "lifecycle": {
        "nonauthority": True,
        "expected_abort_reproduced": True,
        "accepted_output_emitted": False,
        "production_replay_started": False,
        "movement_relation_emitted": False,
        "revision_13_relation_identity_emitted": False,
        "q5_input_emitted": False,
        "q5_first_add_performed": False,
        "full_g17_c01_row_emitted": False,
        "authority_emitted": False,
        "production_output_emitted": False,
        "next_required_state": "A19_SUCCESSOR_PROGRAM_STOP",
    },
    "nonemission_evidence_keys": [
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
    ],
    "nonemission_true_fields": [
        "repository_clean_before",
        "repository_clean_after",
        "repository_read_only",
        "network_disabled",
        "result_path_absent_after_execution",
    ],
    "captured_streams": ["stdout", "stderr"],
    "manifest_row_keys": [
        "path",
        "mode",
        "git_blob",
        "byte_size",
        "raw_sha256",
    ],
    "first_add_after_r05": True,
    "first_add_minimum_revision": 20,
    "first_add_name_status_delta": [
        [
            "A",
            (
                "docs/analysis/amendment_12_rq_catalog_tier2/"
                "certification/amendment11_expected_abort_result_v1.json"
            ),
        ]
    ],
    "immutable_after_first_add": True,
}
A18_ACTIVATION_TRANSITION = {
    "activation_affecting": True,
    "ambiguity_fails_closed_into_obligation": True,
    "simulated_state_authority": "NONAUTHORITY",
    "terminal_revision": 20,
    "terminal_amendment": 18,
    "ordered_closure_domain": [13, 14, 15, 16, 17, 18],
    "closure_count": 6,
    "closure_count_subtrahend": 14,
    "public_entrypoint": "validate_ratification_operativity",
    "same_state_required": True,
    "full_pinned_battery_required": True,
    "all_nonpassing_counts": 0,
    "receipt_inside_candidate_bytes": False,
    "r05_public_entrypoint": "validate_ratification_operativity",
    "r05_minimum_terminal_revision": 18,
    "r05_expected_domain_expression": "tuple(range(13, R - 1))",
    "r05_selected_zero_based_position": 2,
    "r05_selected_amendment": 15,
}
A18_EXPECTED_MUTATIONS = (
    "tier2_build_input_domain_preimage_forged",
    "tier2_r05_current_snapshot_or_historical_binding_forged",
    "tier2_r06_result_or_lifecycle_forged",
)
A18_MUTATION_DOMAIN_SHA256 = (
    "1bf9f6d30461d003cab597a405cb5cc9855273372ed3e7e5b36b1627eaa11108"
)
A18_MUTATION_CENSUS = {
    "inherited_complete_mutation_count": 100,
    "inherited_complete_mutation_domain_sha256": (
        "fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3"
    ),
    "amendment16_mutation_count": 7,
    "amendment16_mutation_domain_sha256": A16_MUTATION_DOMAIN_SHA256,
    "amendment17_mutation_count": 3,
    "amendment17_mutation_domain_sha256": A17_MUTATION_DOMAIN_SHA256,
}
A18_SUPERSESSION_MAP = (
    (
        "§29.4.3 undefined `tier2_build_input_domain_sha256` sentence and "
        "§29.4.5 equality-only use",
        "Superseded and completed by §32.2's 279-row closed preimage, "
        "subset equations, ordering, canonicalization, and dual-byte "
        "equality. The predecessor text remains historical.",
    ),
    (
        "§29.4.3 operative revision-17 selector, §30.3.5 revision-18-literal "
        "R05 selector, and §30.4.2 `historical_r05_snapshot_revision=18`",
        "Superseded only as an active R05 locator by §32.3's complete "
        "current-revision selector for every terminal revision at least 18. "
        "The exact 11 historical A15 values, revision-18 first-operativity "
        "ancestry, and revision-18 historical receipt fact remain unchanged.",
    ),
    (
        "§26.11.2 A12-T2-R06 expected abort without a durable result contract "
        "and §§29.6/30.6 statements that R06 results remain undefined/out "
        "of scope",
        "Superseded only by §32.4's nonauthority result path, schema, "
        "first-add order, and A19 stop. The abort, six-module gate, blocker, "
        "and all prohibitions remain unchanged.",
    ),
    (
        "§31.2.2 active implementation rows",
        "Superseded as active prospective-validation pins only by §32.5.1. "
        "Historical identities and the three-path domain remain immutable.",
    ),
    (
        "§§30.2.1–30.2.4 general oracle and §31.3 executed-transition "
        "obligation",
        "Lawfully unchanged and composed with §32.3's R05 consumer and "
        "§32.5.3's mandatory revision-20 same-state demonstration.",
    ),
    (
        "§29.4 R04/R05 artifact schemas, isolation, five gates, lifecycle, "
        "Git order, 100-name census, integrity, and raw-byte attestation",
        "Lawfully unchanged except the exact preimage and selector "
        "successors named above. No R05 artifact is instantiated.",
    ),
    (
        "§§27.3–27.6 repair semantics and seals; 14 law gaps; 524,538 "
        "missing-reason dispositions; Q5; G17-C01; registries; receipts of "
        "record; and production",
        "Byte-identical and lawfully unchanged. The R06 evidence records a "
        "stop and grants no authority.",
    ),
)
A18_NEW_IDENTIFIERS = {
    "schema_and_path": [
        "amendment_12_tier2_build_input_domain.v1",
        "amendment_12_tier2_r06_expected_abort_result.v1",
        (
            "docs/analysis/amendment_12_rq_catalog_tier2/certification/"
            "amendment11_expected_abort_result_v1.json"
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

A19_SECTION_SEMANTIC_SHA256 = (
    "1af9e180f4467a2c1817a12b515112dfaf96e2bcc72519bc2bde4a0423e5296d"
)
A19_OFFICIAL_PURPOSES = [
    "interview_and_role_attachment",
    "amount",
    "reporting_unit",
    "month_or_exposure",
    "assignment",
    "employee_self_or_mixed",
    "incorporation",
    "government_level",
    "industry",
    "occupation",
    "enrollment",
    "job_identifier",
    "state_of_residence",
    "section_218_group",
    "section_218_position",
    "public_retirement_system_participation",
    "federal_retirement_system",
    "federal_service",
    "railroad_covered_employer",
    "railroad_covered_service",
    "ministerial_service",
    "clergy_remuneration",
    "church_employee_service",
    "religious_order_service",
    "clergy_or_religious_exemption",
    "domestic_service",
    "agricultural_service",
    "election_work",
    "family_service",
    "casual_service",
    "foreign_government_service",
    "international_organization_service",
    "nonresident_alien_status",
    "employer_school_nexus",
    "statutory_student_service",
]
A19_PURPOSE_MAPPING_CONTRACT = {
    "prompt_row_keys": [
        "source_prompt_occurrence_id",
        "source_classification_row_id",
        "serialized_source_literals",
        "explicit_official_purposes",
        "unresolved_legacy_literals",
        "purpose_mapping_disposition",
    ],
    "prompt_row_order": "questionnaire_occurrence_source_order",
    "construction_order": [
        "authenticate_fixed_prompt_denominator",
        "construct_complete_purpose_mapping_rows_keyset_domain_and_counts",
        "compute_U_underdetermined_mapping_prompt_count",
        "select_failure_or_normal_variant",
        "normal_variant_only_construct_O_H_purpose_independent",
        "normal_variant_only_evaluate_O_P_witnesses",
    ],
    "source_classification_resolution": (
        "zero_or_one_same_annotation_row_by_shape_specific_occurrence_id"
    ),
    "source_classification_join_keys": {
        "plural": "source_prompt_occurrence_id",
        "singular": "source_occurrence_id",
    },
    "source_classification_status_rules": {
        "plural": {
            "key": "annotation_status",
            "value": "complete",
        },
        "singular": {
            "key": "classification_status",
            "value": "complete_document_local_provisional",
        },
    },
    "plural_source_row_keys": [
        "annotation_status",
        "applicable_anchor_occurrence_ids",
        "exact_prompt",
        "exact_prompt_utf8_span",
        "field_purposes",
        "local_field_purpose_classification_id",
        "source_prompt_occurrence_id",
    ],
    "singular_source_row_keys": [
        "classification_status",
        "exact_prompt",
        "exact_prompt_sha256",
        "field_purpose",
        "local_field_purpose_classification_id",
        "source_occurrence_id",
        "supported_local_anchor_ids",
    ],
    "official_purpose_order": A19_OFFICIAL_PURPOSES,
    "official_projection_rule": (
        "stable_unique_intersection_with_official_purpose_order"
    ),
    "legacy_projection_rule": (
        "complete_stable_unique_source_literal_complement"
    ),
    "disposition_order": [
        "complete_official_mapping",
        "partial_official_mapping_with_legacy_residue_underdetermined",
        "legacy_only_mapping_underdetermined",
        "missing_mapping_underdetermined",
    ],
    "disposition_counts": {
        "complete_official_mapping": 818,
        "partial_official_mapping_with_legacy_residue_underdetermined": 14,
        "legacy_only_mapping_underdetermined": 56,
        "missing_mapping_underdetermined": 21_083,
    },
    "source_annotation_document_count": 81,
    "classification_document_count": 9,
    "classification_document_rows": [
        {
            "document_position": 7,
            "official_mapped_prompt_count": 43,
            "prompt_count": 99,
        },
        {
            "document_position": 14,
            "official_mapped_prompt_count": 50,
            "prompt_count": 50,
        },
        {
            "document_position": 34,
            "official_mapped_prompt_count": 5,
            "prompt_count": 5,
        },
        {
            "document_position": 36,
            "official_mapped_prompt_count": 133,
            "prompt_count": 133,
        },
        {
            "document_position": 40,
            "official_mapped_prompt_count": 174,
            "prompt_count": 174,
        },
        {
            "document_position": 56,
            "official_mapped_prompt_count": 128,
            "prompt_count": 128,
        },
        {
            "document_position": 58,
            "official_mapped_prompt_count": 149,
            "prompt_count": 149,
        },
        {
            "document_position": 66,
            "official_mapped_prompt_count": 85,
            "prompt_count": 85,
        },
        {
            "document_position": 70,
            "official_mapped_prompt_count": 65,
            "prompt_count": 65,
        },
    ],
    "field_purpose_prompt_count": 21_971,
    "first_source_prompt_occurrence_id": (
        "psid-questionnaire-occurrence:"
        "17d4dd6699adc429dc5548b30763fc11425469927c1f02c41c15ae6a93c3828a"
    ),
    "last_source_prompt_occurrence_id": (
        "psid-questionnaire-occurrence:"
        "d1c8bdfb99364eff8092c663c399e6e4391e6fcd9c6bb742bdda13f1df489980"
    ),
    "purpose_mapping_keyset_canonical_byte_size": 2_131_189,
    "purpose_mapping_keyset_sha256": (
        "2d1300eaae5c8259f1cda59907d2cf0b8174faf5a37a3549e6d6f3eec9618921"
    ),
    "purpose_mapping_domain_canonical_byte_size": 7_244_433,
    "purpose_mapping_domain_sha256": (
        "53158188e774c75fcbe6b7af57bfa747060c80193556eac7a0e289e02b63ed1e"
    ),
    "classification_row_count": 888,
    "unclassified_prompt_count": 21_083,
    "official_mapped_prompt_count": 832,
    "missing_official_mapping_prompt_count": 21_139,
    "official_only_prompt_count": 818,
    "mixed_official_legacy_prompt_count": 14,
    "legacy_only_prompt_count": 56,
    "underdetermined_mapping_prompt_count": 21_153,
    "official_edge_count": 980,
    "official_only_edge_count": 963,
    "mixed_official_edge_count": 17,
    "official_purpose_observed_count": 14,
    "legacy_edge_count": 74,
    "mixed_legacy_edge_count": 14,
    "legacy_only_edge_count": 60,
    "legacy_row_count": 70,
    "legacy_literals": [
        "business_share",
        "employment_status",
        "farm_operating_expenses",
        "farm_receipts",
        "hours_worked",
        "in_kind_receipt",
        "income_source",
        "job_tenure",
        "net_farm_income",
        "rate",
        "receipt_indicator",
        "time_not_worked",
        "weeks_worked",
    ],
    "no_current_prompt_source_proved_no_purpose": True,
    "normal_variant_known_positive_relation": (
        "existing_same_wave_branch_compatible_anchor_witness_using_only_"
        "explicit_official_purposes"
    ),
    "underdetermined_selects_early_failure_variant": True,
    "selected_failure_variant_evaluates_o_h": False,
    "selected_failure_variant_evaluates_o_p": False,
    "normal_variant_o_h_remains_purpose_independent": True,
    "normal_variant_o_h_precedes_o_p_witness_evaluation": True,
    "text_transfer_forbidden": True,
    "similarity_transfer_forbidden": True,
    "legacy_literal_promotion_forbidden": True,
    "manual_addition_forbidden": True,
    "exact_text_transfer_audit": {
        "missing_official_mapping_prompt_count": 21_139,
        "mapped_text_class_conflict_count": 8,
        "shared_text_ambiguous_prompt_count": 12,
        "shared_text_prompt_count": 246,
        "shared_text_unique_mapping_prompt_count": 234,
        "unmatched_text_prompt_count": 20_893,
    },
}
A19_SEMANTIC_BINDING_CONTRACT = {
    "authenticated_annotation_document_count": 81,
    "authenticated_complete_semantic_binding_relation_count": 0,
    "audit_is_discovery_evidence_not_selected_branch_member_input": True,
    "purpose_mapping_does_not_create_five_coordinate_binding": True,
    "candidate_binding_forbidden": True,
    "text_inference_forbidden": True,
    "failure_selector_precedes_semantic_binding_evaluation": True,
    "selected_failure_variant_serializes_near_match_rows": False,
    "normal_variant_requires_inherited_complete_semantic_bindings": True,
}
A19_SOURCE_HIERARCHY_FAILURE_MEMBER = {
    "authority_kind": "source_only_canonical_questionnaire_annotation",
    "questionnaire_document_count": 81,
    "questionnaire_document_keyset_sha256": (
        "3326c9ba70b7f83f19b0ea934630d26ced73f230be1628cb74031d17160cb1a5"
    ),
    "questionnaire_document_domain_sha256": (
        "b06139b147391d06b4f90a8f28de472a936ec08b3e9eb37001a5a70e2b3c3543"
    ),
    "purpose_mapping_row_count": 21_971,
    "purpose_mapping_keyset_sha256": (
        "2d1300eaae5c8259f1cda59907d2cf0b8174faf5a37a3549e6d6f3eec9618921"
    ),
    "purpose_mapping_domain_sha256": (
        "53158188e774c75fcbe6b7af57bfa747060c80193556eac7a0e289e02b63ed1e"
    ),
    "purpose_mapping_disposition_counts": {
        "complete_official_mapping": 818,
        "partial_official_mapping_with_legacy_residue_underdetermined": 14,
        "legacy_only_mapping_underdetermined": 56,
        "missing_mapping_underdetermined": 21_083,
    },
    "canonical_order": "questionnaire_occurrence_source_order",
    "status": "fail_source_purpose_mapping_underdetermined",
}
A19_SOURCE_HIERARCHY_MEMBER_IDENTITY = {
    "authority_kind": ("pre_q5_source_hierarchy_failure_member_nonauthority"),
    "canonical_byte_size": 877,
    "canonicalization": "python-json-sort-keys-compact-ascii-no-nan-lf-v1",
    "member_name": "hierarchy_annotation_authority",
    "raw_sha256": (
        "1651c50ff1f171ac420e55982cb060db70946f9283999c3d9edb2fa140d467c5"
    ),
    "status": "fail_source_purpose_mapping_underdetermined",
}
A19_A12_SUCCESSOR_AUTHORITY_HEADER_KEYS = [
    "authority_kind",
    "questionnaire_document_count",
    "questionnaire_document_keyset_sha256",
    "questionnaire_document_domain_sha256",
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
    "canonical_order",
    "status",
]
A19_SOURCE_HIERARCHY_FAILURE_CONTRACT = {
    "selection_stage": (
        "after_purpose_mapping_before_all_pass_member_construction"
    ),
    "selection_predicate": "underdetermined_mapping_prompt_count_gt_zero",
    "fixed_selector_value": True,
    "global_purpose_mapping_rows_constructed_before_selection": True,
    "selected_failure_variant_serializes_per_era_purpose_mapping_rows": False,
    "failure_member_keys": [
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
    ],
    "forbidden_authority_header_keys": [
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
    ],
    "forbidden_evaluation_or_serialization": [
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
    ],
    "failure_member": A19_SOURCE_HIERARCHY_FAILURE_MEMBER,
    "failure_member_canonical_byte_size": 877,
    "failure_member_raw_sha256": (
        "1651c50ff1f171ac420e55982cb060db70946f9283999c3d9edb2fa140d467c5"
    ),
    "source_hierarchy_member_identity_keys": [
        "authority_kind",
        "canonical_byte_size",
        "canonicalization",
        "member_name",
        "raw_sha256",
        "status",
    ],
    "source_hierarchy_member_identity": A19_SOURCE_HIERARCHY_MEMBER_IDENTITY,
    "source_hierarchy_member_identity_canonical_byte_size": 351,
    "source_hierarchy_member_identity_raw_sha256": (
        "077c6a19e44d8abdf96422a8d2d203fdf263ecbbfb70cb9bb3dc9522a3dcd2bd"
    ),
    "r04_dual_reconstruction_required": True,
    "r04_independent_reconstruction_subresult_count": 2,
    "r04_independent_reconstruction_subresult_status": (
        "pass_independent_source_reconstruction"
    ),
    "r04_independent_reconstruction_subresults_require_exact_selected_"
    "member_bytes": True,
    "a12_t2_r04_overall_gate_preserved": True,
    "a12_t2_r04_selected_failure_gate_pass_permitted": False,
    "r05_requires_passing_normal_member": True,
    "r05_pass_or_certification_emission_permitted": False,
    "q5_or_authority_emission_permitted": False,
}
A19_HIERARCHY_CONSTRUCTION_CONTRACT = {
    "canonicalization": ("python-json-sort-keys-compact-ascii-no-nan-lf-v1"),
    "applicability": "only_if_purpose_failure_selector_false",
    "selected_failure_variant_executes_hierarchy_construction": False,
    "preproof_row_keys": [
        "questionnaire_slot_id",
        "interview_wave",
        "role",
        "relationship_id",
        "job_slot",
        "questionnaire_component_slot",
        "slot_kind",
        "hierarchy_presence",
        "hierarchy_occurrence_ids",
        "flow_branch_ids",
        "flow_branch_paths",
        "source_locator_ids",
    ],
    "final_row_keys": [
        "questionnaire_slot_id",
        "interview_wave",
        "role",
        "relationship_id",
        "job_slot",
        "questionnaire_component_slot",
        "slot_kind",
        "hierarchy_presence",
        "hierarchy_occurrence_ids",
        "flow_branch_ids",
        "flow_branch_paths",
        "source_locator_ids",
        "hierarchy_absence_proof_id",
    ],
    "preproof_projection_rule": (
        "delete_only_hierarchy_absence_proof_id_without_placeholder"
    ),
    "header_insertions": [
        "hierarchy_preproof_domain_sha256",
        "purpose_mapping_row_count",
        "purpose_mapping_keyset_sha256",
        "purpose_mapping_domain_sha256",
        "purpose_mapping_disposition_counts",
    ],
    "per_era_insertion": "purpose_mapping_rows",
    "g17_c01_normal_projection_sides": ["expected", "actual"],
    "g17_c01_normal_per_era_insertion_order": [
        "hierarchy_rows",
        "purpose_mapping_rows",
        "positive_occurrence_rows",
    ],
    "g17_c01_normal_direct_concatenation_header_members": [
        "purpose_mapping_row_count",
        "purpose_mapping_keyset_sha256",
        "purpose_mapping_domain_sha256",
        "purpose_mapping_disposition_counts",
    ],
    "selected_failure_variant_executes_g17_c01_projection": False,
    "search_implementation_keys": [
        "authority_kind",
        "questionnaire_page_text_derivation_sha256",
        "questionnaire_page_domain_sha256",
        "questionnaire_occurrence_domain_sha256",
        "flow_branch_domain_sha256",
        "role_node_domain_sha256",
        "job_slot_domain_sha256",
        "questionnaire_component_slot_domain_sha256",
        "node_alias_domain_sha256",
        "global_relationship_domain_sha256",
        "hierarchy_preproof_domain_sha256",
        "positive_occurrence_domain_sha256",
        "near_match_source_annotation_count",
        "near_match_source_annotation_keyset_sha256",
        "near_match_source_annotation_domain_sha256",
    ],
    "replaced_search_key": "hierarchy_domain_sha256",
    "preproof_digest_formula": (
        "D0=SHA256(C(direct_era_order_concatenation_of_preproof_rows))"
    ),
    "proof_id_preimage_order": [
        "era_id",
        "target_predicate",
        "searched_interview_waves",
        "searched_locator_ids",
        "searched_layout_keyset_sha256",
        "searched_codebook_keyset_sha256",
        "search_implementation",
    ],
    "proof_id_formula": (
        "A_h=psid-absence-proof:+SHA256(C(proof_id_preimage))"
    ),
    "final_digest_formula": (
        "D1=SHA256(C(direct_era_order_concatenation_of_final_rows))"
    ),
    "dependency_order": [
        "preproof_rows",
        "hierarchy_preproof_domain_sha256",
        "search_implementation",
        "absence_proof_ids",
        "final_hierarchy_rows",
        "hierarchy_domain_sha256",
        "dependent_proof_expanded_era_and_member_digests",
    ],
    "preproof_forbidden_dependencies": [
        "hierarchy_absence_proof_id",
        "final_hierarchy_row",
        "hierarchy_domain_sha256",
        "absence_proof",
        "absence_proof_domain_sha256",
        "expanded_disposition_row",
        "expanded_disposition_domain_sha256",
        "era_digest",
        "member_digest",
    ],
    "placeholder_forbidden": True,
    "fixed_point_iteration_forbidden": True,
}
A19_SUCCESSOR_ROUTING_CONTRACT = {
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
A19_ACTIVATION_TRANSITION = {
    "activation_affecting": True,
    "ambiguity_fails_closed_into_obligation": True,
    "simulated_state_authority": "NONAUTHORITY",
    "terminal_revision": 21,
    "terminal_amendment": 19,
    "ordered_closure_domain": [13, 14, 15, 16, 17, 18, 19],
    "closure_count": 7,
    "closure_count_subtrahend": 14,
    "public_entrypoint": "validate_ratification_operativity",
    "same_state_required": True,
    "full_pinned_battery_required": True,
    "all_nonpassing_counts": 0,
    "receipt_inside_candidate_bytes": False,
    "activation_requires_later_registry_repin": True,
    "production_registry_revision_in_draft": 20,
    "production_oracle_changed_by_draft": False,
}
A19_EXPECTED_MUTATIONS = (
    "source_purpose_totality_or_binding_disposition_forged",
    "hierarchy_preproof_final_digest_order_forged",
    "r06_successor_program_stop_numbering_forged",
)
A19_MUTATION_DOMAIN_BYTE_SIZE = 151
A19_MUTATION_DOMAIN_SHA256 = (
    "002aa021325c18e311cc778562ad0e937468a90c378db0740290fcf617929101"
)
A19_MUTATION_CENSUS = {
    "inherited_complete_mutation_count": 100,
    "inherited_complete_mutation_domain_sha256": (
        "fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3"
    ),
    "amendment16_mutation_count": 7,
    "amendment16_mutation_domain_sha256": A16_MUTATION_DOMAIN_SHA256,
    "amendment17_mutation_count": 3,
    "amendment17_mutation_domain_sha256": A17_MUTATION_DOMAIN_SHA256,
    "amendment18_mutation_count": 3,
    "amendment18_mutation_domain_sha256": A18_MUTATION_DOMAIN_SHA256,
}
A19_SUPERSESSION_MAP = (
    (
        "§19.3.3 O_H-before-purpose-classification order and O_P "
        "prompt-classification and universal-consumption law",
        "Superseded in construction order: authenticate the fixed prompt "
        "denominator, build the complete purpose rows and census, compute U, "
        "and select the failure or normal variant before O_H. The selected "
        "failure arm stops without O_H. On the normal arm O_H remains "
        "purpose-independent and runs after the selector but before O_P "
        "witness evaluation. Only explicit official purposes can enter O_P; "
        "no missing or legacy value is defaulted or promoted.",
    ),
    (
        "§§19.3.3 and 26.6.1 effective authority keyset, canonical_order, "
        "pass | fail status, per-era keysets, and direct-concatenation law",
        "Superseded by the status-discriminated union. The selected failure "
        "arm is exactly the ten-key header and new failure status; all 73 "
        "pass-only effective header keys and every era row are forbidden. "
        "Its global purpose-mapping relation is a completed selector "
        "precursor, not a serialized per-era purpose_mapping_rows array. "
        "The normal arm composes §26.6.1's 78-key successor header with only "
        "the five named A19 header members and per-era purpose_mapping_rows, "
        "and otherwise retains the inherited status, keysets, and "
        "concatenation rules.",
    ),
    (
        "§19.3.3 independently reviewed complete semantic_bindings use "
        "and cross-check law",
        "Preserved on the normal arm. It is not evaluated on the selected "
        "failure arm, which serializes neither an empty binding nor a "
        "near-match row; candidate, text, inventory, crosswalk, or reader "
        "content remains forbidden.",
    ),
    (
        "§19.3.3 hierarchy row proof-ID, hierarchy digest, search object, "
        "and proof serialization law",
        "On the normal arm, superseded only in construction order by the D0 "
        "preproof-row projection, D0-bearing 15-key search object, proof IDs, "
        "final rows, and D1 final digest. On the selected failure arm every "
        "such member and digest is forbidden.",
    ),
    (
        "§19.3.3 raw-field ambiguity abort, occurrence-reference and "
        "positive-join nonempty/equal-count cover, and expanded-disposition "
        "join/proof tagged union",
        "Preserved on the normal arm. They are not executed on the selected "
        "failure arm; no empty, null, partial, or registration-required row "
        "may stand in for them.",
    ),
    (
        "§19.3.3 two-literal proof conclusion and Class-A/Class-B/"
        "inventory keyed joins",
        "Preserved on the normal arm. The failure arm creates no third proof "
        "conclusion and prohibits every proof, join, inventory key, or "
        "downstream projection.",
    ),
    (
        "§§19.4.2 and 26.10.1 G17-C01 expected/actual era_annotation_rows, "
        "Q5, inventory, slot, and authority projections",
        "On the normal arm, both expected and actual G17-C01 era projections "
        "insert per-era purpose_mapping_rows immediately after hierarchy_rows "
        "and before positive_occurrence_rows; direct era-order concatenation "
        "must reproduce purpose_mapping_row_count, "
        "purpose_mapping_keyset_sha256, purpose_mapping_domain_sha256, and "
        "purpose_mapping_disposition_counts in the authority header. All "
        "other projection law is preserved. The selected failure arm remains "
        "expressly prohibited, and its ten-key nonauthority header cannot "
        "occupy G17-C01.",
    ),
    (
        "§26.11.2 A12-T2-R04 gate and §§29.4.4–29.4.5 "
        "source-member identity, R04, and passing R05 certificate",
        "The overall §26.11.2 A12-T2-R04 gate is preserved and is not "
        "executed or passing on the selected failure arm because its H, O_H, "
        "reverse-cover, purpose-expansion, and field-join conjuncts are "
        "forbidden. Only its two independent reconstruction subresults may "
        "each return pass_independent_source_reconstruction by exactly "
        "reproducing the selected 877-byte failure member. The six-key "
        "identity uses the exact failure-specific authority kind and "
        "fail_source_purpose_mapping_underdetermined status. R05 and its "
        "certificate still require a passing normal member and cannot pass "
        "on the current input.",
    ),
    (
        "§32.4.4, §32.7, and §32.8 active A19 successor-program stop",
        "Historical A18 bytes remain exact; active post-A19 routing is "
        "A20_SUCCESSOR_PROGRAM_STOP with no alias, and the deferred campaign "
        "is Amendment 20/revision 22 and out of scope.",
    ),
    (
        "§32.5.1 active implementation rows",
        "Superseded as active prospective-validation pins only by the "
        "Amendment-19 table. Historical identities and the three-path domain "
        "remain immutable.",
    ),
    (
        "§31.3 executed-transition obligation and generalized oracle",
        "Lawfully unchanged and applied to the mandatory revision-21 "
        "same-state demonstration. Activation still requires a later real "
        "registry repin.",
    ),
)
A19_NEW_IDENTIFIERS = {
    "schema": [
        "amendment_19_source_hierarchy_member_construction_law.v1",
    ],
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
A19_NORMATIVE_MANIFEST = {
    "schema_version": (
        "amendment_19_source_hierarchy_member_construction_law.v1"
    ),
    "canonicalization": ("python-json-sort-keys-compact-ascii-no-nan-lf-v1"),
    "prefix_identity": {
        "blob_oid": REVISION20_BLOB_OID,
        "byte_size": REVISION20_BYTE_SIZE,
        "raw_sha256": REVISION20_SHA256,
    },
    "authenticated_build_input_envelope": {
        "canonical_byte_size": 168_504,
        "raw_sha256": (
            "f34ced6e80e1bf72e68635b4f729c5b983c094fd25d16105a6c161ccd52fff63"
        ),
        "row_count": 279,
    },
    "purpose_mapping_contract": A19_PURPOSE_MAPPING_CONTRACT,
    "semantic_binding_contract": A19_SEMANTIC_BINDING_CONTRACT,
    "source_hierarchy_failure_contract": (
        A19_SOURCE_HIERARCHY_FAILURE_CONTRACT
    ),
    "hierarchy_construction_contract": A19_HIERARCHY_CONSTRUCTION_CONTRACT,
    "successor_routing_contract": A19_SUCCESSOR_ROUTING_CONTRACT,
    "activation_transition": A19_ACTIVATION_TRANSITION,
    "mutation_inventory": list(A19_EXPECTED_MUTATIONS),
    "mutation_domain_byte_size": A19_MUTATION_DOMAIN_BYTE_SIZE,
    "mutation_domain_sha256": A19_MUTATION_DOMAIN_SHA256,
    "mutation_census": A19_MUTATION_CENSUS,
    "supersession_map": [list(row) for row in A19_SUPERSESSION_MAP],
    "new_identifiers": A19_NEW_IDENTIFIERS,
    "production_registry_boundary": {
        "closure_count": 6,
        "ordered_closure_domain": [13, 14, 15, 16, 17, 18],
        "revision": 20,
        "unchanged_by_draft": True,
    },
}

A20_SECTION_SEMANTIC_SHA256: str | None = (
    "32fdc956786f4d65dca75d38d553c7e04411e0a01ebe7d0e60cf11d046f80ff8"
)
A20_CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
A20_COMMON_IDENTITY_NAMES = [
    "physical_source_identity",
    "evidence_statement_identity",
    "missing_reason_source_domain_identity",
    "purpose_source_domain_identity",
    "a20_successor_source_binding_identity",
    "r04_q5_shape_identity",
    "r06_six_module_identity",
    "r06_collected_node_id_identity",
    "dormant_lifecycle_definition_identity",
]
A20_ARM_IDENTITY_CONTRACTS = {
    "missing_reason_authority_status": {
        "pass_status": "pass",
        "failure_status": "fail_permanent_missing_reason_authority_residue",
        "pass_identity_names": [
            "missing_reason_rule_set_identity",
            "missing_reason_successor_relation_identity",
            "missing_representation_bridge_identity",
        ],
        "forbidden_output_paths": [
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "missing_reason_rule_set_identity.json",
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "missing_reason_successor_relation_identity.json",
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "missing_representation_bridge_identity.json",
        ],
        "failure_shadow_identity_name": (
            "missing_reason_failure_shadow_identity"
        ),
    },
    "purpose_authority_status": {
        "pass_status": "pass",
        "failure_status": "fail_permanent_purpose_authority_residue",
        "pass_identity_names": [
            "purpose_rule_set_identity",
            "purpose_authority_mapping_identity",
        ],
        "forbidden_output_paths": [
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "purpose_rule_set_identity.json",
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "purpose_authority_mapping_identity.json",
        ],
        "failure_shadow_identity_name": "purpose_failure_shadow_identity",
    },
    "prompt_field_semantic_binding_status": {
        "pass_status": "pass",
        "failure_status": (
            "fail_permanent_prompt_field_or_semantic_binding_residue"
        ),
        "pass_identity_names": [
            "prompt_field_evidence_identity",
            "prompt_field_candidate_set_identity",
            "zero_candidate_positive_group_identity",
            "semantic_binding_identity",
        ],
        "forbidden_output_paths": [
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "prompt_field_evidence_identity.json",
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "prompt_field_candidate_set_identity.json",
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "zero_candidate_positive_group_identity.json",
            "docs/analysis/amendment_20_ratification/evidence_freeze/"
            "semantic_binding_identity.json",
        ],
        "failure_shadow_identity_name": (
            "prompt_field_semantic_failure_shadow_identity"
        ),
    },
}
A20_EXPECTED_IDENTITY_NAMES = [
    "physical_source_identity",
    "evidence_statement_identity",
    "missing_reason_source_domain_identity",
    "purpose_source_domain_identity",
    "a20_successor_source_binding_identity",
    "missing_reason_rule_set_identity",
    "missing_reason_successor_relation_identity",
    "missing_representation_bridge_identity",
    "purpose_rule_set_identity",
    "purpose_authority_mapping_identity",
    "prompt_field_evidence_identity",
    "prompt_field_candidate_set_identity",
    "zero_candidate_positive_group_identity",
    "semantic_binding_identity",
    "r04_q5_shape_identity",
    "r06_six_module_identity",
    "r06_collected_node_id_identity",
    "dormant_lifecycle_definition_identity",
    "missing_reason_failure_shadow_identity",
    "purpose_failure_shadow_identity",
    "prompt_field_semantic_failure_shadow_identity",
]
A20_PASS_IDENTITY_KEYS = [
    "identity_name",
    "row_count",
    "ordered_keyset_sha256",
    "row_domain_sha256",
    "status",
]
A20_ARM_PASS_IDENTITY_KEYS = [
    "identity_name",
    "arm_status_member",
    "arm_status",
    "row_count",
    "ordered_keyset_sha256",
    "row_domain_sha256",
    "status",
]
A20_SUCCESSOR_BINDING_IDENTITY_KEYS = [
    "identity_name",
    "row_count",
    "ordered_keyset_sha256",
    "row_domain_sha256",
    "arm_status_bindings",
    "active_identity_bindings_sha256",
    "status",
]
A20_FAILURE_SHADOW_IDENTITY_KEYS = [
    "schema_version",
    "identity_name",
    "arm_status_member",
    "arm_status",
    "shadow_row_count",
    "shadow_ordered_keyset_sha256",
    "shadow_row_domain_sha256",
    "complement_identity",
    "forbidden_output_identity_names",
    "forbidden_output_paths",
    "nonemission_evidence",
    "status",
]
A20_NONEMISSION_COMPLEMENT_IDENTITY_KEYS = [
    "schema_version",
    "complement_of_identity_names",
    "row_count",
    "ordered_keyset_sha256",
    "row_domain_sha256",
    "status",
]
A20_REPOSITORY_MANIFEST_ROW_KEYS = [
    "path",
    "mode",
    "git_blob",
    "byte_size",
    "raw_sha256",
]
A20_FAILURE_NONEMISSION_EVIDENCE_KEYS = [
    "execution_commit",
    "execution_tree_oid",
    "repository_manifest_rows_before",
    "repository_manifest_sha256_before",
    "repository_manifest_rows_after",
    "repository_manifest_sha256_after",
    "repository_clean_before",
    "repository_clean_after",
    "forbidden_outputs_absent_after_execution",
]
A20_EVIDENCE_FREEZE = {
    "schema_version": "a20_evidence_freeze.v1",
    "amendment20_evidence_freeze_status": (
        "not_instantiated_a4_required_before_ratify"
    ),
    "missing_reason_authority_status": None,
    "purpose_authority_status": None,
    "prompt_field_semantic_binding_status": None,
    "expected_identity_bindings": {
        name: None for name in A20_EXPECTED_IDENTITY_NAMES
    },
    "amendment20_ratification_ready": False,
}
A20_EVIDENCE_FREEZE_CONTRACT = {
    "object": A20_EVIDENCE_FREEZE,
    "final_required_evidence_freeze_status": "pass_a4_exact_freeze",
    "final_arm_status_domains": {
        "missing_reason_authority_status": [
            "pass",
            "fail_permanent_missing_reason_authority_residue",
        ],
        "purpose_authority_status": [
            "pass",
            "fail_permanent_purpose_authority_residue",
        ],
        "prompt_field_semantic_binding_status": [
            "pass",
            "fail_permanent_prompt_field_or_semantic_binding_residue",
        ],
    },
    "identity_contract": {
        "common_identity_names": A20_COMMON_IDENTITY_NAMES,
        "arm_identity_contracts": A20_ARM_IDENTITY_CONTRACTS,
        "pass_identity_keys": A20_PASS_IDENTITY_KEYS,
        "arm_pass_identity_keys": A20_ARM_PASS_IDENTITY_KEYS,
        "successor_binding_identity_keys": (
            A20_SUCCESSOR_BINDING_IDENTITY_KEYS
        ),
        "failure_shadow_identity_keys": A20_FAILURE_SHADOW_IDENTITY_KEYS,
        "nonemission_complement_identity_keys": (
            A20_NONEMISSION_COMPLEMENT_IDENTITY_KEYS
        ),
        "failure_nonemission_evidence_keys": (
            A20_FAILURE_NONEMISSION_EVIDENCE_KEYS
        ),
        "repository_manifest_row_keys": A20_REPOSITORY_MANIFEST_ROW_KEYS,
        "successor_binding_identity_name": (
            "a20_successor_source_binding_identity"
        ),
        "successor_binding_digest_excludes_self": True,
        "failure_shadow_rows_are_exact_forbidden_output_complement": True,
        "failure_shadow_paths_are_exact_arm_contract_paths": True,
        "lifecycle_booleans_are_not_accepted_as_self_attestation": True,
    },
    "ratification_readiness_iff_freeze_shape_statuses_and_identities": True,
    "semantic_arm_pass_required_for_ratification": False,
    "absent_identity_is_not_zero_digest_or_wildcard": True,
    "authority_selection_permitted": False,
    "r04_or_later_permitted": False,
}
A20_CONTROLLING_EXTERNAL_RECORDS = [
    {
        "logical_path": "e8-ops/sol-ce-a20-charter.md",
        "byte_size": 27_368,
        "raw_sha256": (
            "5ecd4092f3fc62ef894866a1a5b505d6dba7bb04cde1360ff7134d7d8e927717"
        ),
        "authority": "NONAUTHORITY",
    },
    {
        "logical_path": ("e8-ops/sol-ce-law-gap-sweep-r21-2026-08-16.md"),
        "byte_size": 11_805,
        "raw_sha256": (
            "39887de99d75a395e97b04f33b4c5264a6828f56c9321cfe248b4ba11a7e5846"
        ),
        "authority": "NONAUTHORITY",
    },
]
A20_EVIDENCE_CAMPAIGN_CONTRACT = {
    "stage_order": [
        "E0_banked_evidence_reauthentication",
        "E1_shared_source_closure_and_separate_domain_projections",
        "E2_compilers_representation_bridges_and_measured_pilots",
        "A1_concentrated_queues",
        "A2_recurring_remainder",
        "A3_occurrence_local_residue_with_capacity_kills",
        "A4_dual_review_reconciliation_and_exact_identity_freeze",
        "C20_ratification_and_revision_22_activation",
        "X1_authoritative_settlement_missing_dispatch_disabled",
        "X2_complete_normal_R04_and_R05",
        "historical_R06_replay_and_first_add",
        "fresh_reconstruction",
        "Q5",
        "slot_inventory_G17_C01_and_V_B6",
        "sealed_publication_chain",
    ],
    "rounds_formula": "ceil(2L/(3q))",
    "q_definition": (
        "observed_independently_reviewed_logical_decisions_per_lane_day"
    ),
    "forecast_as_of": "2026-08-15",
    "conditional_p50": "2026-11-09",
    "conditional_p80": "2027-01-22",
    "dates_are_nonauthority_conditional_planning_metadata": True,
    "fail_closed_kill_categories": [
        "source_admission",
        "missing_rule_scope",
        "purpose_entailment",
        "family_equivalence",
        "legacy_vocabulary",
        "circular_attachment",
        "prompt_field_ambiguity",
        "reviewer_origin",
        "cross_arm_contamination",
        "missing_convention_arm_capacity",
        "missing_ledger_capacity",
        "purpose_ledger_capacity",
        "acceptance_exact_cover_and_reconstruction",
        "complete_R04",
        "downstream_reconstruction_and_publication",
    ],
    "permanent_residue_remains_fail_closed": True,
}
A20_PHYSICAL_SOURCE_ROW_KEYS = [
    "evidence_source_id",
    "upstream_capture_or_registry_identity",
    "document_role",
    "release_or_wave",
    "representation",
    "official_url",
    "canonical_local_path",
    "storage_identity",
    "byte_size",
    "raw_sha256",
    "access_disposition",
    "licensing_disposition",
    "statement_locator_ids",
    "extraction_tool_identity",
    "recovered_source_provenance",
]
A20_EVIDENCE_STATEMENT_ROW_KEYS = [
    "evidence_statement_id",
    "evidence_source_id",
    "page_or_section_locator",
    "utf8_byte_start",
    "utf8_byte_end",
    "exact_statement_raw_sha256",
    "extraction_tool_identity",
    "recovery_provenance_id",
]
A20_SEMANTIC_DOMAIN_IDENTITY_KEYS = [
    "domain_id",
    "domain_version",
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
]
A20_SOURCE_INFRASTRUCTURE_CONTRACT = {
    "physical_relation": "a20_physical_source_rows",
    "physical_source_row_keys": A20_PHYSICAL_SOURCE_ROW_KEYS,
    "statement_relation": "a20_evidence_statement_rows",
    "evidence_statement_row_keys": A20_EVIDENCE_STATEMENT_ROW_KEYS,
    "semantic_domain_order": [
        "missing_reason_source_domain",
        "purpose_source_domain",
    ],
    "semantic_domain_identity_keys": A20_SEMANTIC_DOMAIN_IDENTITY_KEYS,
    "semantic_domains": {
        "missing_reason_source_domain": {
            "domain_id": "missing_reason_source_domain",
            "expected_identity": None,
            "required_final_status": "pass",
        },
        "purpose_source_domain": {
            "domain_id": "purpose_source_domain",
            "expected_identity": None,
            "required_final_status": "pass",
        },
    },
    "inclusion_exclusion_complete_and_disjoint": True,
    "included_and_excluded_counts_sum_to_physical_count": True,
    "domains_authenticate_foreign_keys_independently": True,
    "shared_physical_bytes_imply_shared_semantic_admission": False,
    "mixed_semantic_payload_or_shared_accepted_digest_aborts_both": True,
    "path_rule": "repository_relative_canonical_traversal_free",
    "machine_local_absolute_paths_forbidden": True,
    "current_url_or_latest_edition_substitution_forbidden": True,
    "historical_domains_preserved": {
        "a11_source_count": 47,
        "questionnaire_document_count": 81,
        "a19_build_input_source_document_count": 257,
        "a19_build_input_repair_seal_count": 22,
        "a19_build_input_row_count": 279,
    },
    "successor_source_binding_keys": [
        "historical_a19_build_input_identity",
        "physical_source_identity",
        "evidence_statement_identity",
        "missing_reason_source_domain_identity",
        "purpose_source_domain_identity",
        "missing_reason_authority_status",
        "purpose_authority_status",
        "prompt_field_semantic_binding_status",
        "missing_reason_rule_set_identity",
        "missing_reason_successor_relation_identity",
        "missing_representation_bridge_identity",
        "purpose_rule_set_identity",
        "purpose_authority_mapping_identity",
        "prompt_field_evidence_identity",
        "prompt_field_candidate_set_identity",
        "zero_candidate_positive_group_identity",
        "semantic_binding_identity",
        "r04_q5_shape_identity",
        "missing_reason_failure_shadow_identity",
        "purpose_failure_shadow_identity",
        "prompt_field_semantic_failure_shadow_identity",
        "active_identity_bindings_sha256",
        "canonicalization",
        "status",
    ],
    "successor_source_binding_expected_identity": None,
    "independent_reconstructor_count": 2,
    "reconstructors_require_count_order_keyset_rows_and_digest_equality": (
        True
    ),
}
A20_MISSING_REASON_AUTHORITY_CONTRACT = {
    "authority_rule_row_keys": [
        "authority_rule_id",
        "registered_evidence_source_ids",
        "registered_statement_ids",
        "rule_kind",
        "exact_scope_predicate",
        "explicit_exclusions",
        "strict_boolean_disposition",
        "projected_occurrence_count",
        "projected_occurrence_keyset_sha256",
        "overlap_conflict_complement_results",
    ],
    "occurrence_identity_position_order": [
        "schema_tag",
        "global_member_position",
        "source_document_position",
        "source_row_position",
        "entry_position",
        "source_document_id",
        "codebook_field_row_id",
        "ordered_nonempty_locator_id_array",
        "entry_reference",
        "entry_kind",
        "exact_source_value_or_range_lexeme",
        "exact_nonempty_source_meaning",
    ],
    "formerly_unresolved_literal_occurrence_count": 524_538,
    "inherited_source_authorized_literal_count": 52,
    "numeric_structural_null_range_count": 37_283,
    "claim_type": "strict_json_boolean_excluding_integer_coercion",
    "projection_requirements": [
        "exact",
        "nonzero",
        "disjoint",
        "collectively_exhaustive",
        "exception_complete",
    ],
    "conflict_precedes_incomplete_coverage": True,
    "agreeing_duplicate_rules_abort": True,
    "candidate_defaults_forbidden": True,
    "independent_compiler_count": 2,
    "transactional_atomic_nonemission": True,
    "missing_true_reason_id_prefix": "psid-source-missing-reason:",
    "missing_false_reason": None,
    "numeric_range_reason": None,
    "historical_a11_and_a18_results_preserved": True,
    "representation_bridge_probe": {
        "relation": "missing_representation_bridge_rows",
        "direct_field_ceiling_observation": 54_898,
        "gross_source_era_ceiling_observation": 71_635,
        "diagnostic_shadow_observation": 59_424,
        "zero_projection_observation": 87,
        "observations_are_nonauthority": True,
        "accepted_bridge_identity": None,
        "u24_e2_93md_claims_accepted": 0,
        "bridge_required_before_acceptance": True,
    },
}
A20_PURPOSE_AUTHORITY_CONTRACT = {
    "official_purpose_order": A19_OFFICIAL_PURPOSES,
    "completed_ontology_order": [
        *A19_OFFICIAL_PURPOSES,
        "source_underdetermined",
    ],
    "purpose_authority_rule_row_keys": [
        "purpose_authority_source_id",
        "rule_kind",
        "registered_evidence_statement_ids",
        "exact_prompt_scope_predicate",
        "explicit_exclusions",
        "explicit_official_purposes",
        "projected_prompt_count",
        "projected_prompt_keyset_sha256",
    ],
    "purpose_mapping_row_keys": [
        "source_prompt_occurrence_id",
        "authority_basis",
        "purpose_authority_source_id",
        "evidence_statement_ids",
        "explicit_official_purposes",
        "purpose_mapping_disposition",
        "reconciled_adjudication_ruling_id",
    ],
    "prompt_denominator_a4_freeze_slot": None,
    "required_disposition_counts": {
        "complete_official_mapping": None,
        "source_underdetermined": None,
        "U": 0,
    },
    "source_underdetermined_count_a4_freeze_slot": None,
    "source_underdetermined_requires_reconciled_adjudication_ruling": True,
    "source_underdetermined_uses_determined_row_provenance_authentication": True,
    "source_underdetermined_means_authenticated_sources_determine_no_nonempty_subset": True,
    "source_underdetermined_is_no_applicable_purpose": False,
    "disposition_relation_total_under_completed_ontology": True,
    "u_definition": "prompt_without_lawful_completed_ontology_disposition",
    "authority_gate_uses_reconciled_outcomes": True,
    "exact_row_agreement_is_authority_gate": False,
    "macro_per_prompt_jaccard_minimum_calibration_diagnostic": "90%",
    "inherited_complete_rows_requiring_source_regrounding": 818,
    "manual_origin_grandfathering_permitted": False,
    "source_conflict_reopens_row": True,
    "purpose_arrays_nonempty_stable_unique_in_official_order": True,
    "exact_prompt_cover_and_zero_gap_extra_duplicate_overlap_conflict": True,
    "independent_compiler_count": 2,
    "transactional_atomic_nonemission": True,
    "source_backed_alternatives": [
        "occurrence_kind_or_denominator_correction",
        "ontology_projection",
        "separately_tagged_no_applicable_purpose_arm",
    ],
    "source_backed_alternative_selected": "ontology_projection",
    "source_classification_row_id_overload_forbidden": True,
}
A20_PROMPT_FIELD_SEMANTIC_BINDING_CONTRACT = {
    "prompt_field_row_keys": [
        "prompt_field_evidence_id",
        "source_prompt_occurrence_id",
        "interview_wave",
        "questionnaire_span",
        "prompt_source_locator_ids",
        "field_source_document_id",
        "field_source_row_id",
        "field_source_member",
        "raw_field_id",
        "attachment_basis",
        "official_alias_statement_ids",
        "attachment_disposition",
        "candidate_raw_field_ids",
    ],
    "questionnaire_span_keys": ["utf8_byte_start", "utf8_byte_end"],
    "questionnaire_span_basis": "prompt_source_utf8_byte_half_open_interval",
    "questionnaire_span_minimal_exact_identifier_token_match": True,
    "questionnaire_span_bounds_strict_integers_excluding_booleans": True,
    "questionnaire_span_requires_0_le_start_lt_end_le_prompt_byte_length": True,
    "prompt_field_evidence_id_prefix": "psid-prompt-field-evidence:",
    "prompt_field_evidence_id_preimage": [
        "source_prompt_occurrence_id",
        "interview_wave",
        "questionnaire_span",
        "prompt_source_locator_ids",
        "field_source_document_id",
        "field_source_row_id",
        "field_source_member",
        "raw_field_id",
        "attachment_basis",
        "official_alias_statement_ids",
        "attachment_disposition",
        "candidate_raw_field_ids",
    ],
    "prompt_field_evidence_id_canonicalization": A20_CANONICALIZATION,
    "prompt_field_evidence_order": [
        "complete_prompt_source_position",
        "interview_wave",
        "source_prompt_occurrence_id",
        "questionnaire_span.utf8_byte_start",
        "questionnaire_span.utf8_byte_end",
        "attachment_branch_direct_before_question_token",
        "field_reconstruction_document_row_member_order",
    ],
    "exact_duplicate_evidence_emission_aborts": True,
    "coordinate_distinct_spans_must_have_distinct_row_bodies": True,
    "coordinate_distinct_span_collapse_aborts": True,
    "construction_stage": "before_O_P",
    "positive_attachment_bases": [
        "exact_source_identifier",
        "expressly_admitted_official_alias",
    ],
    "attachment_dispositions": [
        "accepted_exact_source_identifier",
        "accepted_expressly_admitted_official_alias",
        "unresolved_multiple",
    ],
    "candidate_sets_materialized": True,
    "zero_or_multiple_candidates_fail_without_source_resolution": True,
    "direct_identifier_priority_forbidden": True,
    "collision_census": {
        "domain": "historical_same_coordinate_leading_question_token_conflicts",
        "complete_official_prompt_count": 818,
        "multiple_count": 46,
    },
    "complete_official_prompt_candidate_census": {
        "domain": "prompt_level_stable_unique_complete_candidate_union",
        "complete_official_prompt_count": 818,
        "multiple_count": 49,
        "additional_noncollision_candidate_sets": [
            {
                "interview_wave": 1974,
                "candidate_raw_field_ids": ["V3585", "V3586"],
            },
            {
                "interview_wave": 1985,
                "candidate_raw_field_ids": ["V11649", "V11648"],
            },
            {
                "interview_wave": 1985,
                "candidate_raw_field_ids": ["V11616", "V11676"],
            },
        ],
    },
    "full_prompt_candidate_census": {
        "domain": "multiple_candidates_over_full_prompt_denominator",
        "prompt_count": 21_971,
        "multiple_count": 2_349,
    },
    "c68_regression": {
        "source_prompt_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "4cd66190a898d568dd20c27140f44f1dff53d229f664f537722624d00c9b4b67"
        ),
        "interview_wave": 1985,
        "printed_direct_field_id": "V11804",
        "question_token": "C68.",
        "candidate_raw_field_ids": ["V11804", "V11805"],
        "draft_disposition": "unresolved_multiple",
    },
    "prompt_field_candidate_set_row_keys": [
        "prompt_field_candidate_set_id",
        "source_prompt_occurrence_id",
        "interview_wave",
        "candidate_prompt_field_evidence_ids",
        "candidate_raw_field_ids",
        "candidate_count",
        "candidate_disposition",
    ],
    "prompt_field_candidate_set_id_prefix": (
        "psid-prompt-field-candidate-set:"
    ),
    "prompt_field_candidate_set_id_preimage": [
        "source_prompt_occurrence_id",
        "interview_wave",
        "candidate_prompt_field_evidence_ids",
        "candidate_raw_field_ids",
        "candidate_count",
        "candidate_disposition",
    ],
    "prompt_field_candidate_set_dispositions": [
        "zero_candidates",
        "one_candidate",
        "multiple_candidates",
    ],
    "prompt_field_candidate_set_order": "complete_prompt_source_order",
    "candidate_arrays_complete_stable_unique_source_order": True,
    "candidate_count_is_raw_field_array_length_strict_integer": True,
    "candidate_disposition_is_iff_count_partition": True,
    "candidate_set_id_is_sha256_of_canonical_remaining_members": True,
    "candidate_set_row_ids_and_prompt_ids_unique": True,
    "zero_candidate_positive_group_row_keys": [
        "zero_candidate_positive_group_id",
        "positive_occurrence_id",
        "zero_candidate_source_prompt_occurrence_ids",
        "all_source_prompt_occurrence_ids",
        "complete_reference_union_ids",
        "empty_reference_union",
        "group_disposition",
    ],
    "zero_candidate_positive_group_id_prefix": (
        "psid-zero-candidate-positive-group:"
    ),
    "zero_candidate_positive_group_id_preimage": [
        "positive_occurrence_id",
        "zero_candidate_source_prompt_occurrence_ids",
        "all_source_prompt_occurrence_ids",
        "complete_reference_union_ids",
        "empty_reference_union",
        "group_disposition",
    ],
    "zero_candidate_positive_group_dispositions": [
        "complete_nonempty_reference_union",
        "fail_empty_reference_union",
    ],
    "zero_candidate_positive_group_order": "positive_occurrence_order",
    "zero_candidate_group_one_per_qualifying_positive_occurrence": True,
    "zero_candidate_prompt_arrays_complete_positive_row_projections": True,
    "zero_candidate_reference_union_complete_stable_unique": True,
    "empty_reference_union_is_strict_boolean_zero_length_equality": True,
    "zero_candidate_group_disposition_is_iff_empty_boolean": True,
    "zero_candidate_group_id_is_sha256_of_canonical_remaining_members": True,
    "zero_candidate_group_ids_and_positive_ids_unique": True,
    "zero_candidate_grouping_probe": {
        "candidate_set_prompt_count": 21_971,
        "sweep_zero_candidate_observation": 15_428,
        "diagnostic_zero_candidate_observation": 14_450,
        "observations_are_nonauthority": True,
        "difference_explained": False,
        "accepted_positive_group_with_empty_reference_union_count": None,
        "accepted_attachment_required_for_codebook_supported_rule": True,
    },
    "semantic_binding_coordinates": [
        "role",
        "job_slot_id",
        "questionnaire_component_slot_id",
        "slot_kind",
        "field_purpose",
    ],
    "semantic_binding_dispositions": [
        "semantically_bound",
        "no_supported_predicate_dimension",
        "unresolved_semantic_binding",
    ],
    "required_unresolved_semantic_binding_count": 0,
    "semantic_binding_serialization": "near_match_source_annotation_rows",
    "separate_semantic_binding_rows_serialization_permitted": False,
    "semantic_binding_identity_requires_deep_equality": [
        "row_count",
        "ordered_keyset_sha256",
        "row_domain_sha256",
    ],
    "binding_built_before_candidate_rows_read": True,
    "joint_support_and_subsumption_maximality_required": True,
    "post_o_p_relations": [
        "occurrence_raw_field_reference_rows",
        "positive_field_join_rows",
        "nonempty_reference_and_raw_field_projections",
        "unique_same_wave_attachment",
        "purpose_expansion",
        "reverse_covers",
    ],
    "post_o_p_relations_use_completed_purpose_ontology": True,
    "post_o_p_exact_token_joins_without_silent_unions": True,
    "mandatory_ambiguity_regressions": ["Family", "Dl7./D17.", "D2."],
}
A20_R04_Q5_CONTRACT = {
    "construction_order": [
        "authenticate_fixed_historical_denominators_and_a20_source_domains",
        "construct_and_seal_missing_purpose_rules_and_successor_binding",
        "compile_purpose_prompt_field_and_semantic_inputs",
        "compute_purpose_U_and_independent_acceptance_results",
        "select_failure_or_normal_member",
        "normal_only_construct_H_and_source_only_O_H",
        "normal_only_require_O_H_before_O_P",
        "normal_only_construct_O_P_bindings_joins_covers_expansion_D0_search_D1_and_R04",
        "normal_only_R05_strict_certificate_and_dual_reconstruction",
    ],
    "purpose_totality_alone_passes_r04": False,
    "selector_purpose_domain": "completed_purpose_ontology",
    "o_p_order": [*A19_OFFICIAL_PURPOSES, "source_underdetermined"],
    "purpose_expansion_domain": "completed_purpose_ontology",
    "purpose_rule_projection_domain": "completed_purpose_ontology",
    "o_h_source_only": True,
    "o_h_precedes_o_p_on_normal_arm": True,
    "permitted_selector_input_reads": [
        "questionnaire_occurrence_rows",
        "fixed_prompt_denominator",
        "purpose_authority_mapping_rows",
        "prompt_field_candidate_set_rows",
        "selector_inputs",
    ],
    "forbidden_selected_failure_member_serialization": [
        "questionnaire_occurrence_rows",
        "all_pass_only_arrays",
        "Q5",
        "R05_certificate",
        "authority",
        "production_output",
    ],
    "historical_a19_failure_member_byte_size": 877,
    "historical_a19_failure_member_raw_sha256": (
        "1651c50ff1f171ac420e55982cb060db70946f9283999c3d9edb2fa140d467c5"
    ),
    "source_document_manifest_insert_after": "source_document_domain_sha256",
    "source_document_manifest_additions": [
        "a20_successor_source_binding_identity",
        "missing_reason_source_domain_identity",
        "purpose_source_domain_identity",
        "missing_reason_rule_set_identity",
        "purpose_rule_set_identity",
        "prompt_field_evidence_identity",
        "semantic_binding_identity",
    ],
    "replaced_a19_effective_header_members": [
        "purpose_mapping_row_count",
        "purpose_mapping_keyset_sha256",
        "purpose_mapping_domain_sha256",
        "purpose_mapping_disposition_counts",
    ],
    "normal_effective_header_successor_members": [
        "purpose_authority_mapping_row_count",
        "purpose_authority_mapping_keyset_sha256",
        "purpose_authority_mapping_domain_sha256",
        "purpose_authority_mapping_disposition_counts",
        "prompt_field_evidence_row_count",
        "prompt_field_evidence_keyset_sha256",
        "prompt_field_evidence_domain_sha256",
        "prompt_field_evidence_disposition_counts",
        "prompt_field_candidate_set_row_count",
        "prompt_field_candidate_set_keyset_sha256",
        "prompt_field_candidate_set_domain_sha256",
        "prompt_field_candidate_set_disposition_counts",
        "zero_candidate_positive_group_row_count",
        "zero_candidate_positive_group_keyset_sha256",
        "zero_candidate_positive_group_domain_sha256",
        "zero_candidate_positive_group_empty_union_count",
    ],
    "normal_effective_header_insert_before": "positive_occurrence_row_count",
    "replaced_a19_era_sequence": [
        "hierarchy_rows",
        "purpose_mapping_rows",
        "positive_occurrence_rows",
    ],
    "normal_era_successor_sequence": [
        "hierarchy_rows",
        "purpose_authority_mapping_rows",
        "prompt_field_evidence_rows",
        "prompt_field_candidate_set_rows",
        "zero_candidate_positive_group_rows",
        "positive_occurrence_rows",
    ],
    "inherited_semantic_relation_member": "near_match_source_annotation_rows",
    "inherited_semantic_relation_position": "after_expanded_disposition_rows",
    "per_era_rows_use_direct_era_order_concatenation": True,
    "g17_c01_expected_and_actual_shapes_equal": True,
    "failure_arms_serialize_a20_shape_additions": False,
    "a19_purpose_mapping_is_historical_nonconsumable_on_a20_normal_path": (
        True
    ),
    "a19_digest_dependency_order_preserved": [
        "D0",
        "search_implementation",
        "A_h",
        "final_rows",
        "D1",
    ],
}
A20_R06_FILE_IDENTITIES = [
    {
        "path": "tests/data/test_psid_codebook_extraction_validation.py",
        "mode": "100644",
        "git_blob": "7b2f33af3ff6a4e389a944e349aa222f6ca41519",
        "byte_size": 13_718,
        "raw_sha256": (
            "7af8a2847b4428fa7376598cc48333d008f225389eee461f3edae58ca624ff67"
        ),
    },
    {
        "path": "tests/data/test_psid_missing_reason_authority_artifact.py",
        "mode": "100644",
        "git_blob": "c8863f4a6a5e915666f0cce2cac4817e73839e9f",
        "byte_size": 18_129,
        "raw_sha256": (
            "4f425c776ddba30f3b861812cdcbd0abef5b10ae0f41608bcaa6d456c9cdcd85"
        ),
    },
    {
        "path": "tests/data/test_psid_missing_reason_authority_unit.py",
        "mode": "100644",
        "git_blob": "499aa397f75e1d2f62e7c91a929f9ecdcf71a478",
        "byte_size": 18_252,
        "raw_sha256": (
            "5e9b7cc33fd560ce5c472c6ac146f07a6b7b238003c6e96f715e417679149cda"
        ),
    },
    {
        "path": "tests/estimates/test_birth_evidence_artifact.py",
        "mode": "100644",
        "git_blob": "d4e838a1123d4e07c6f472ff64cfd6c11462f4a8",
        "byte_size": 25_883,
        "raw_sha256": (
            "70acf9c2f36f9f88a7e5e2c8c7b5825427d6a44cf1926b0a6c0c7cf4bbb7d5d5"
        ),
    },
    {
        "path": "tests/test_rebuild_amendment11_missing_reason_authority.py",
        "mode": "100644",
        "git_blob": "632357933ea37c982d18402d249b74147cd80823",
        "byte_size": 22_828,
        "raw_sha256": (
            "eedbab9e3ba3eaad19f08d36472b2fbc53cc5dc62b417a3600d5cb4360368dcb"
        ),
    },
    {
        "path": "tests/test_replay_amendment11_no_movement.py",
        "mode": "100644",
        "git_blob": "cc4c1c6d65c89ad97feb0b4f04e6c5d2ecd2405f",
        "byte_size": 19_309,
        "raw_sha256": (
            "0875ac524e0cd2e7f3cb6e601026b0d2db5b459c6f426fe5182ac08ebaef9ec1"
        ),
    },
]
_A20_LIFECYCLE_ROW_SPECS = (
    (
        "A20_SOURCE_RELATIONS_SETTLED_DISPATCH_DISABLED",
        "a20_source_settlement.v1",
        ["REVISION22_REGISTRY_REPIN"],
        [
            "revision22_registry_repin_identity",
            "a20_successor_source_binding_identity",
            "dormant_lifecycle_definition_identity",
        ],
    ),
    (
        "A20_NORMAL_R04_REQUIRED",
        "a20_normal_r04.v1",
        ["A20_SOURCE_RELATIONS_SETTLED_DISPATCH_DISABLED"],
        [
            "a20_source_settlement_identity",
            "historical_a19_build_input_identity",
        ],
    ),
    (
        "A20_R05_REQUIRED",
        "a20_r05_certificate.v1",
        ["A20_NORMAL_R04_REQUIRED"],
        ["a20_normal_r04_identity"],
    ),
    (
        "A20_HISTORICAL_R06_REQUIRED",
        "a20_historical_r06_binding.v1",
        ["A20_R05_REQUIRED"],
        [
            "a20_r05_certificate_identity",
            "r06_six_module_identity",
            "r06_collected_node_id_identity",
            "historical_a11_replay_identity",
        ],
    ),
    (
        "A20_MISSING_REASON_SUCCESSOR_ACTIVE",
        "a20_missing_reason_successor_relation.v1",
        ["A20_HISTORICAL_R06_REQUIRED"],
        [
            "a20_historical_r06_identity",
            "missing_reason_successor_relation_identity",
        ],
    ),
    (
        "A20_CLASSIFIER_REBUILD_REQUIRED",
        "a20_classifier_rebuild.v1",
        ["A20_MISSING_REASON_SUCCESSOR_ACTIVE"],
        [
            "a20_active_missing_reason_identity",
            "historical_classifier_input_identity",
        ],
    ),
    (
        "A20_TERMINAL_MOVEMENT_REQUIRED",
        "a20_terminal_movement.v1",
        ["A20_CLASSIFIER_REBUILD_REQUIRED"],
        ["a20_classifier_rebuild_identity"],
    ),
    (
        "A20_ASSIGNMENT_REBUILD_REQUIRED",
        "a20_assignment_rebuild.v1",
        ["A20_TERMINAL_MOVEMENT_REQUIRED"],
        ["a20_terminal_movement_identity"],
    ),
    (
        "A20_LOGICAL_RANGE_REBUILD_REQUIRED",
        "a20_logical_range_rebuild.v1",
        ["A20_ASSIGNMENT_REBUILD_REQUIRED"],
        ["a20_assignment_rebuild_identity"],
    ),
    (
        "A20_STORAGE_POPULATION_REBUILD_REQUIRED",
        "a20_storage_population_rebuild.v1",
        ["A20_LOGICAL_RANGE_REBUILD_REQUIRED"],
        ["a20_logical_range_rebuild_identity"],
    ),
    (
        "A20_CONSTRUCTIBILITY_REQUIRED",
        "a20_constructibility.v1",
        ["A20_STORAGE_POPULATION_REBUILD_REQUIRED"],
        ["a20_storage_population_rebuild_identity"],
    ),
    (
        "A20_FULL_RELATION_IDENTITY_REQUIRED",
        "a20_full_relation_identity.v1",
        ["A20_CONSTRUCTIBILITY_REQUIRED"],
        ["a20_constructibility_identity"],
    ),
    (
        "A20_COMPARATOR_REQUIRED",
        "a20_comparator_census.v1",
        ["A20_FULL_RELATION_IDENTITY_REQUIRED"],
        ["a20_full_relation_identity"],
    ),
    (
        "A20_Q5_REQUIRED",
        "a20_q5.v1",
        ["A20_COMPARATOR_REQUIRED"],
        ["a20_comparator_census_identity"],
    ),
    (
        "A20_SLOT_REBUILD_REQUIRED",
        "a20_slot_rebuild.v1",
        ["A20_Q5_REQUIRED"],
        ["a20_q5_identity"],
    ),
    (
        "A20_INVENTORY_REBUILD_REQUIRED",
        "a20_inventory_rebuild.v1",
        ["A20_SLOT_REBUILD_REQUIRED"],
        ["a20_slot_rebuild_identity"],
    ),
    (
        "A20_G17_C01_REBUILD_REQUIRED",
        "a20_g17_c01_rebuild.v1",
        ["A20_INVENTORY_REBUILD_REQUIRED"],
        ["a20_inventory_rebuild_identity"],
    ),
    (
        "A20_VB6_REQUIRED",
        "a20_vb6_successor.v1",
        ["A20_G17_C01_REBUILD_REQUIRED"],
        ["a20_g17_c01_rebuild_identity"],
    ),
    (
        "A20_SUCCESSOR_BUNDLES_REQUIRED",
        "a20_successor_bundles.v1",
        ["A20_VB6_REQUIRED"],
        ["a20_vb6_identity"],
    ),
    (
        "A20_MIGRATIONS_REQUIRED",
        "a20_migrations.v1",
        ["A20_SUCCESSOR_BUNDLES_REQUIRED"],
        ["a20_successor_bundles_identity"],
    ),
    (
        "A20_CAPTURE_REQUIRED",
        "a20_capture.v1",
        ["A20_MIGRATIONS_REQUIRED"],
        ["a20_migrations_identity"],
    ),
    (
        "A20_RECEIPT_REQUIRED",
        "a20_receipt.v1",
        ["A20_CAPTURE_REQUIRED"],
        ["a20_capture_identity"],
    ),
    (
        "A20_REGISTRATION_REQUIRED",
        "a20_registration.v1",
        ["A20_RECEIPT_REQUIRED"],
        ["a20_receipt_identity"],
    ),
    (
        "A20_SEALED_RUN_REQUIRED",
        "a20_sealed_run.v1",
        ["A20_REGISTRATION_REQUIRED"],
        ["a20_registration_identity"],
    ),
    (
        "A20_WALL_LEDGER_REQUIRED",
        "a20_wall_ledger.v1",
        ["A20_SEALED_RUN_REQUIRED"],
        ["a20_sealed_run_identity"],
    ),
    (
        "A20_PUBLICATION_REQUIRED",
        "a20_publication.v1",
        ["A20_WALL_LEDGER_REQUIRED"],
        ["a20_wall_ledger_identity"],
    ),
)
A20_DORMANT_LIFECYCLE_ROWS = [
    {
        "lifecycle_stage_id": stage_id,
        "schema_id": schema_id,
        "predecessor_stage_ids": predecessor_ids,
        "input_identity_ids": input_ids,
        "output_identity_id": None,
        "first_add_index": index,
        "selection_enabled": False,
        "status": "dormant_definition",
    }
    for index, (stage_id, schema_id, predecessor_ids, input_ids) in enumerate(
        _A20_LIFECYCLE_ROW_SPECS,
        start=1,
    )
]
A20_R06_LIFECYCLE_CONTRACT = {
    "interpreter_selector": "executing_process_sys.executable",
    "test_command_after_interpreter": [
        "-m",
        "pytest",
        *[row["path"] for row in A20_R06_FILE_IDENTITIES],
    ],
    "collection_command_after_interpreter": [
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        *[row["path"] for row in A20_R06_FILE_IDENTITIES],
    ],
    "test_environment": {"PYTHONPATH": "src:."},
    "inherited_git_environment_removed": True,
    "ambient_pytest_addopts_removed": True,
    "test_file_identities": A20_R06_FILE_IDENTITIES,
    "module_path_domain_sha256": (
        "a5099c464482c5b652e31e5dfa958703a4ae4c75c1dc1e4caa03cb2aef408063"
    ),
    "collected_node_id_count": 223,
    "collected_node_id_array_canonical_byte_size": 28_268,
    "collected_node_id_array_raw_sha256": (
        "09071bf4d9a9a5ee8b9ccc4d8d5c0bd91705c04d3c7c99d6ef155dfdc0dfdf05"
    ),
    "first_collected_node_id": (
        "tests/data/test_psid_codebook_extraction_validation.py::"
        "test_exact_nested_derivation_schemas_accept_generated_shapes"
        "[_text_derivation]"
    ),
    "last_collected_node_id": (
        "tests/test_replay_amendment11_no_movement.py::"
        "test_reason_mutation_changes_field_source_identity_but_not_terminal"
    ),
    "historical_r06_result_preserved": {
        "exit_code": 2,
        "source_authorized_literal_count": 52,
        "blocked_literal_count": 524_538,
        "numeric_range_structural_null_count": 37_283,
    },
    "dormant_definition_before_certification_permitted": True,
    "dormant_definition_creates_instance_or_selection": False,
    "evidence_settlement_before_r06_requires_dispatch_disabled": True,
    "lifecycle_envelope_keys": [
        "lifecycle_stage_id",
        "schema_id",
        "predecessor_stage_ids",
        "input_identity_ids",
        "output_identity_id",
        "first_add_index",
        "selection_enabled",
        "status",
    ],
    "lifecycle_statuses": [
        "dormant_definition",
        "blocked_predecessor",
        "pass",
        "fail_atomic_nonemission",
    ],
    "dormant_lifecycle_rows": A20_DORMANT_LIFECYCLE_ROWS,
    "dormant_lifecycle_row_count": 26,
    "output_identity_id_prefix": "a20-lifecycle-output:",
    "output_identity_preimage": [
        "lifecycle_stage_id",
        "schema_id",
        "predecessor_stage_ids",
        "input_identity_ids",
        "exact_output_payload_identity",
    ],
    "output_identity_preimage_canonicalization": A20_CANONICALIZATION,
    "selection_enabled_only_on_passing_first_add_index": 5,
    "blocked_predecessor_output_identity": None,
    "fail_atomic_nonemission_output_identity": None,
    "unratified_next_required_state": "A20_SUCCESSOR_PROGRAM_STOP",
    "revision22_repin_next_required_state": (
        "A20_SOURCE_RELATIONS_SETTLED_DISPATCH_DISABLED"
    ),
    "terminal_next_required_state": "A20_SUCCESSOR_LIFECYCLE_COMPLETE",
    "selection_first_add_dispatch_requires_r04_r05_r06_order": True,
    "fresh_recomputation_required": [
        "89599_field_classifier",
        "terminal_movement",
        "assignments_logical_ranges_storage",
        "constructibility_and_full_relation_identity",
        "comparator_census",
        "Q5",
        "slot_inventory_full_G17_C01_and_V_B6",
        "successor_bundles_through_publication",
    ],
    "historical_zero_movement_assumption_permitted": False,
}
A20_EXECUTED_TRANSITION_RECEIPT_PATH = (
    "docs/analysis/amendment_20_ratification/"
    "executed_transition_receipt_v2.json"
)
A20_PRODUCTION_REGISTRY_IDENTITY = {
    "path": "scripts/covered_earnings_correction_registry.py",
    "mode": "100644",
    "git_blob": "92a24e3af4358f75cbead00f223837a68c2f9da8",
    "byte_size": 55_473,
    "raw_sha256": (
        "bd60336e3e388e5ef12f3f204b9bb089" "38c27be4db57f9e6fca6582aed7efb16"
    ),
}
A20_RECEIPT_SCHEMA = {
    **A17_RECEIPT_SCHEMA,
    "manifest_keys": [
        "schema_version",
        "simulated_state_authority",
        "candidate_commit_identity",
        "scratch_transition",
        "terminal_revision",
        "canonical_registry_binding",
        "ordered_closure_identities",
        "full_pinned_battery_test_identity",
    ],
    "manifest_schema_version": "executed_transition_state.v2",
    "candidate_commit_identity_keys": ["commit", "tree", "sole_parent"],
    "scratch_transition_keys": [
        "commit",
        "tree",
        "sole_parent",
        "changed_paths",
        "changed_path_domain_sha256",
    ],
    "scratch_sole_parent_equals_candidate_commit": True,
    "expected_changed_paths": [
        (
            "docs/analysis/amendment_20_ratification/"
            "sol-ce-amend20-sim-r1-verdict.md"
        ),
        (
            "docs/analysis/amendment_20_ratification/"
            "sol-ce-amend20-sim-r2-verdict.md"
        ),
        "docs/analysis/amendment_20_ratification/closure_v1.json",
        "scripts/covered_earnings_correction_registry.py",
    ],
    "expected_changed_path_domain_canonical_byte_size": 260,
    "expected_changed_path_domain_sha256": (
        "5a7912498c4d959fef337f2a1d1cf85a2f254fa29d825d365ccf4fe214ad48a7"
    ),
    "changed_path_count": 4,
    "changed_path_roles": [
        "simulated_verdict_1",
        "simulated_verdict_2",
        "synthetic_amendment20_closure",
        "scratch_registry_binding",
    ],
    "candidate_or_scratch_HEAD_member_superseded": True,
}
A20_RATIFICATION_RECEIPT_CONTRACT = {
    "amendment20_external_receipt_path": (
        A20_EXECUTED_TRANSITION_RECEIPT_PATH
    ),
    "inherited_external_receipt_path_template": (
        "docs/analysis/amendment_<N>_ratification/"
        "executed_transition_receipt_v2.json"
    ),
    "external_receipt_mode": "100644",
    "candidate_production_registry_identity": A20_PRODUCTION_REGISTRY_IDENTITY,
    "external_receipt_outside_candidate_and_scratch": True,
    "external_receipt_strict_canonical_tracked_head_worktree_read": True,
    "external_receipt_candidate_ancestry_not_required": True,
    "external_receipt_first_add_precedes_or_equals_closure_first_add": True,
    "scratch_commit_forbidden_as_production_ancestor": True,
    "receipt_candidate_design_tree_mode_blob_rederived": True,
    "receipt_candidate_design_exactly_cross_binds_historical_a20_closure_and_verdicts": True,
    "current_terminal_registry_cross_binding_required_iff_a20_terminal_revision22": True,
    "later_revision_authenticates_historical_a20_design_under_30_2_3": True,
    "receipt_rederives_synthetic_closure_standins_and_registry_binding": True,
    "receipt_public_result_booleans_not_sufficient": True,
    "later_amendment_requires_own_exact_receipt_topology_projection": True,
    "qualifying_verdict_line_count": 8,
    "qualifying_verdict_lines": [
        "# RATIFY",
        "attested_design_byte_size: <decimal>",
        "attested_design_raw_sha256: <64 lowercase hex>",
        "attested_design_blob_oid: <40 lowercase hex>",
        "executed_transition_receipt_byte_size: <decimal>",
        "executed_transition_receipt_raw_sha256: <64 lowercase hex>",
        "executed_transition_receipt_schema: executed_transition_state.v2",
        "---",
    ],
    "decimal_grammar": ("[1-9][0-9]*|[1-9][0-9]{0,2}(,[0-9]{3})+"),
    "strict_utf8_no_bom_nul_cr": True,
    "lf_only_exactly_one_terminal_lf": True,
    "distinct_verdict_artifact_count": 2,
    "same_candidate_triple_and_receipt_pair_required": True,
    "scratch": {
        "candidate_commit_symbol": "C",
        "scratch_commit_symbol": "S",
        "scratch_is_strict_child_of_candidate": True,
        "terminal_revision": 22,
        "ordered_closure_domain": [13, 14, 15, 16, 17, 18, 19, 20],
        "allowed_changed_paths": A20_RECEIPT_SCHEMA["expected_changed_paths"],
        "standin_prefix_line_count": 4,
        "standin_terminal_lines": [
            (
                "executed_transition_receipt_status: "
                "pending_same_state_execution"
            ),
            ("simulation_context: " "amendment20_same_state_nonauthority_v1"),
            "---",
        ],
        "standin_is_qualifying_verdict": False,
        "standin_is_nonauthority_nonmergeable_noncopyable_nonreusable": True,
    },
    "receipt_schema": A20_RECEIPT_SCHEMA,
    "receipt_is_additional_operativity_condition": False,
    "public_oracle_validates_projection_verdicts_and_receipt": True,
}
A20_SUCCESSOR_ROUTING_CONTRACT = {
    "immutable_prefix_amendment": 19,
    "immutable_prefix_revision": 21,
    "terminal_amendment": 20,
    "proposed_revision": 22,
    "amendment20_boundary_count": 1,
    "a20_pins_selected_before_a19_pins": True,
    "a19_pin_fallback_for_terminal_a20_permitted": False,
    "later_amendment_validates_inherited_a20_projection_first": True,
    "current_production": {
        "revision": 21,
        "terminal_amendment": 19,
        "ordered_closure_domain": [13, 14, 15, 16, 17, 18, 19],
        "closure_count": 7,
        "reject_unratified_a20_suffix": True,
    },
    "terminal_successor_state": "A20_SUCCESSOR_LIFECYCLE_COMPLETE",
}
A20_FULL_PINNED_BATTERY_COLLECTED = 220
A20_FULL_PINNED_BATTERY_COMMAND = (
    "executing_process_sys.executable -m pytest -q "
    "tests/test_validate_amendment13_execution_law.py"
)
A20_ACTIVATION_TRANSITION = {
    "activation_affecting": True,
    "terminal_revision": 22,
    "terminal_amendment": 20,
    "ordered_closure_domain": [13, 14, 15, 16, 17, 18, 19, 20],
    "closure_count": 8,
    "closure_count_subtrahend": 14,
    "public_entrypoint": "validate_ratification_operativity",
    "same_state_required": True,
    "full_pinned_battery_required": True,
    "full_pinned_battery_collected": A20_FULL_PINNED_BATTERY_COLLECTED,
    "full_pinned_battery_exact_command": A20_FULL_PINNED_BATTERY_COMMAND,
    "all_nonpassing_counts": 0,
    "receipt_inside_candidate_bytes": False,
    "activation_requires_operator_integration_closure_and_registry_repin": (
        True
    ),
    "production_registry_changed_by_draft": False,
}
A20_EXPECTED_MUTATIONS = (
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
A20_MUTATION_DOMAIN_BYTE_SIZE = 738
A20_MUTATION_DOMAIN_SHA256 = (
    "eab546538a26abac04f559b73646bbca9d240832ae9d9ee82c6295a1462d0e2b"
)
A20_INHERITED_MUTATION_CENSUSES = [
    {
        "inventory": "inherited_complete_certificate",
        "count": 100,
        "raw_sha256": (
            "fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3"
        ),
    },
    {
        "inventory": "amendment16",
        "count": 7,
        "raw_sha256": A16_MUTATION_DOMAIN_SHA256,
    },
    {
        "inventory": "amendment17",
        "count": 3,
        "raw_sha256": A17_MUTATION_DOMAIN_SHA256,
    },
    {
        "inventory": "amendment18",
        "count": 3,
        "raw_sha256": A18_MUTATION_DOMAIN_SHA256,
    },
    {
        "inventory": "amendment19",
        "count": 3,
        "raw_sha256": A19_MUTATION_DOMAIN_SHA256,
    },
]
A20_NEW_IDENTIFIERS = {
    "schema": [
        "amendment_20_dual_authority_successor_law.v1",
        "executed_transition_state.v2",
        "a20_evidence_freeze.v1",
        "a20_failure_shadow_identity.v1",
        "a20_nonemission_complement_identity.v1",
        "a20_physical_source_registry.v1",
        "a20_evidence_statement_registry.v1",
        "a20_missing_reason_source_domain.v1",
        "a20_purpose_source_domain.v1",
        "a20_successor_source_binding.v1",
        "a20_missing_reason_authority_rules.v1",
        "a20_missing_reason_successor_relation.v1",
        "a20_missing_representation_bridge.v1",
        "a20_purpose_authority_rules.v1",
        "a20_purpose_authority_mapping.v1",
        "a20_prompt_field_evidence.v1",
        "a20_prompt_field_candidate_sets.v1",
        "a20_zero_candidate_positive_groups.v1",
        "a20_source_settlement.v1",
        "a20_normal_r04.v1",
        "a20_r05_certificate.v1",
        "a20_historical_r06_binding.v1",
        "a20_classifier_rebuild.v1",
        "a20_terminal_movement.v1",
        "a20_assignment_rebuild.v1",
        "a20_logical_range_rebuild.v1",
        "a20_storage_population_rebuild.v1",
        "a20_constructibility.v1",
        "a20_full_relation_identity.v1",
        "a20_comparator_census.v1",
        "a20_q5.v1",
        "a20_slot_rebuild.v1",
        "a20_inventory_rebuild.v1",
        "a20_g17_c01_rebuild.v1",
        "a20_vb6_successor.v1",
        "a20_successor_bundles.v1",
        "a20_migrations.v1",
        "a20_capture.v1",
        "a20_receipt.v1",
        "a20_registration.v1",
        "a20_sealed_run.v1",
        "a20_wall_ledger.v1",
        "a20_publication.v1",
    ],
    "status_lifecycle_authority": [
        "not_instantiated_a4_required_before_ratify",
        "pass_a4_exact_freeze",
        "fail_permanent_missing_reason_authority_residue",
        "fail_permanent_purpose_authority_residue",
        "fail_permanent_prompt_field_or_semantic_binding_residue",
        "dormant_definition",
        "blocked_predecessor",
        "fail_atomic_nonemission",
        "accepted_exact_source_identifier",
        "accepted_expressly_admitted_official_alias",
        "unresolved_multiple",
        "zero_candidates",
        "one_candidate",
        "multiple_candidates",
        "complete_nonempty_reference_union",
        "fail_empty_reference_union",
        "SIMULATED_NONAUTHORITY",
        "pending_same_state_execution",
        "amendment20_same_state_nonauthority_v1",
        "REVISION22_REGISTRY_REPIN",
        "A20_SOURCE_RELATIONS_SETTLED_DISPATCH_DISABLED",
        "A20_NORMAL_R04_REQUIRED",
        "A20_R05_REQUIRED",
        "A20_HISTORICAL_R06_REQUIRED",
        "A20_MISSING_REASON_SUCCESSOR_ACTIVE",
        "A20_CLASSIFIER_REBUILD_REQUIRED",
        "A20_TERMINAL_MOVEMENT_REQUIRED",
        "A20_ASSIGNMENT_REBUILD_REQUIRED",
        "A20_LOGICAL_RANGE_REBUILD_REQUIRED",
        "A20_STORAGE_POPULATION_REBUILD_REQUIRED",
        "A20_CONSTRUCTIBILITY_REQUIRED",
        "A20_FULL_RELATION_IDENTITY_REQUIRED",
        "A20_COMPARATOR_REQUIRED",
        "A20_Q5_REQUIRED",
        "A20_SLOT_REBUILD_REQUIRED",
        "A20_INVENTORY_REBUILD_REQUIRED",
        "A20_G17_C01_REBUILD_REQUIRED",
        "A20_VB6_REQUIRED",
        "A20_SUCCESSOR_BUNDLES_REQUIRED",
        "A20_MIGRATIONS_REQUIRED",
        "A20_CAPTURE_REQUIRED",
        "A20_RECEIPT_REQUIRED",
        "A20_REGISTRATION_REQUIRED",
        "A20_SEALED_RUN_REQUIRED",
        "A20_WALL_LEDGER_REQUIRED",
        "A20_PUBLICATION_REQUIRED",
        "A20_SUCCESSOR_LIFECYCLE_COMPLETE",
    ],
    "member": [
        "amendment20_evidence_freeze",
        "amendment20_evidence_freeze_status",
        "missing_reason_authority_status",
        "purpose_authority_status",
        "prompt_field_semantic_binding_status",
        "expected_identity_bindings",
        "amendment20_ratification_ready",
        "missing_reason_failure_shadow_identity",
        "purpose_failure_shadow_identity",
        "prompt_field_semantic_failure_shadow_identity",
        "arm_status_bindings",
        "active_identity_bindings_sha256",
        "arm_status_member",
        "arm_status",
        "shadow_row_count",
        "shadow_ordered_keyset_sha256",
        "shadow_row_domain_sha256",
        "complement_identity",
        "complement_of_identity_names",
        "forbidden_output_identity_names",
        "forbidden_output_paths",
        "nonemission_evidence",
        "repository_manifest_rows_before",
        "repository_manifest_rows_after",
        "forbidden_outputs_absent_after_execution",
        "a20_successor_source_binding_identity",
        "missing_reason_source_domain_identity",
        "purpose_source_domain_identity",
        "missing_reason_rule_set_identity",
        "purpose_rule_set_identity",
        "prompt_field_evidence_identity",
        "semantic_binding_identity",
        "purpose_authority_mapping_row_count",
        "purpose_authority_mapping_keyset_sha256",
        "purpose_authority_mapping_domain_sha256",
        "purpose_authority_mapping_disposition_counts",
        "prompt_field_evidence_row_count",
        "prompt_field_evidence_keyset_sha256",
        "prompt_field_evidence_domain_sha256",
        "prompt_field_evidence_disposition_counts",
        "prompt_field_candidate_set_row_count",
        "prompt_field_candidate_set_keyset_sha256",
        "prompt_field_candidate_set_domain_sha256",
        "prompt_field_candidate_set_disposition_counts",
        "zero_candidate_positive_group_row_count",
        "zero_candidate_positive_group_keyset_sha256",
        "zero_candidate_positive_group_domain_sha256",
        "zero_candidate_positive_group_empty_union_count",
        "purpose_authority_mapping_rows",
        "prompt_field_evidence_rows",
        "prompt_field_candidate_set_rows",
        "zero_candidate_positive_group_rows",
        "SIMULATED_STATE_AUTHORITY",
        "SIMULATION_CONTEXT",
        "candidate_commit_identity",
        "scratch_transition",
        "changed_paths",
        "changed_path_domain_sha256",
    ],
    "identity_prefix": [
        "psid-prompt-field-evidence:",
        "psid-prompt-field-candidate-set:",
        "psid-zero-candidate-positive-group:",
        "a20-lifecycle-output:",
    ],
    "python": [
        "_validate_amendment20_draft_design",
        "_validate_amendment20_ratification_design",
        "_validate_inherited_amendment20_ratification_design",
        "_validate_amendment20_evidence_freeze",
        "_canonical_amendment20_repository_path",
        "_read_amendment20_worktree_file",
        "_reconstruct_amendment20_repository_manifest",
        "_validate_amendment20_nonemission_evidence",
        "_parse_amendment20_implementation_pins",
        "_parse_amendment20_projection",
        "run_amendment20_contract_mutation_tests",
        "validate_amendment20_qualifying_verdict",
        "_validate_amendment20_scratch_transition_context",
        "_amendment20_registry_behavior_ast",
        "_parse_amendment20_scratch_registry_binding",
        "_validate_amendment20_transition_receipt",
        "_validate_amendment20_r06_collection_binding",
    ],
}
A20_SUPERSESSION_COVERAGE = [
    "19.3.3_prompt_purpose_manifest_era_semantic_and_post_o_p_joins",
    "20.4.2_and_33.2_33.3_33.7_frozen_q5_shapes",
    "19.4.2_26.6.1_26.10.1_g17_header_q5_inventory_slot_projections",
    "25.2_through_25.4_historical_missing_reason_census_and_settlement",
    "25.5_25.10.1_25.10.2_32.4.4_32.7_32.8_33.4_successor_stop",
    "25.6.6_32.4.2_32.4.3_32.7_r06_selector_input_and_result",
    "25.9_25.10_26.10.3_dc71_lifecycle_definition_timing",
    "26.6.3_26.10.1_33.2.2_33.2.3_33.7_construction_order",
    "26.11.2_complete_r04_r05_r06_gate",
    "28.2.1_28.4_verdict_operator_closure_order",
    "29.4.4_29.4.5_source_member_identity_and_reconstruction",
    "29.4.1_canonicalization_and_identity_equations",
    "30.2.3_30.2.4_verdict_checking_and_public_atomic_operativity",
    "30.2.2_five_key_registry_context_and_caller_context_prohibition",
    "30.2.1_amendment_revision_arithmetic",
    "31.3.1_31.3.2_31.3.3_receipt_and_nonexistent_31.5_anchor",
    "32.2.1_32.2.2_33.8_historical_279_build_input_envelope",
    "32.4.4_false_r06_lifecycle_booleans",
    "30.4.1_31.2.2_32.5.1_33.5.1_implementation_pins_and_review",
    "33.2.2_33.2.3_a19_purpose_rows_and_failure_member",
    "33.3.2_d0_search_proof_d1_construction",
    "33.4_obsolete_campaign_pin_and_a20_out_of_scope_label",
    "33.5.2_33.5.3_a19_projection_routing_and_activation",
    "33.6_mutation_inventory_and_inherited_census",
    "33.7_construction_ambiguity_q5_and_reconstruction_rows",
    "33.8_questionnaire_occurrence_read_vs_serialization_scope",
    "33.9_terminal_a19_prospective_effect",
    "20.3_21.3_21.5_22.2_22.5_23.2_23.5_24.2_24.6_algorithms",
    "19.6_19.8_20.7_20.8_21.8_21.9_22.8_22.9_23.8_23.9_24.9_24.10_25.9_25.10_artifacts",
    "27.3_27.6_28.2.2_29.4.7_seals_closures_and_census",
]
A20_NORMATIVE_MANIFEST = {
    "schema_version": "amendment_20_dual_authority_successor_law.v1",
    "canonicalization": A20_CANONICALIZATION,
    "prefix_identity": {
        "blob_oid": REVISION21_BLOB_OID,
        "byte_size": REVISION21_BYTE_SIZE,
        "raw_sha256": REVISION21_SHA256,
    },
    "controlling_external_records": A20_CONTROLLING_EXTERNAL_RECORDS,
    "amendment20_evidence_freeze": A20_EVIDENCE_FREEZE,
    "evidence_freeze_contract": A20_EVIDENCE_FREEZE_CONTRACT,
    "evidence_campaign": A20_EVIDENCE_CAMPAIGN_CONTRACT,
    "source_infrastructure": A20_SOURCE_INFRASTRUCTURE_CONTRACT,
    "missing_reason_authority": A20_MISSING_REASON_AUTHORITY_CONTRACT,
    "purpose_authority": A20_PURPOSE_AUTHORITY_CONTRACT,
    "prompt_field_semantic_binding": (
        A20_PROMPT_FIELD_SEMANTIC_BINDING_CONTRACT
    ),
    "r04_q5": A20_R04_Q5_CONTRACT,
    "r06_lifecycle": A20_R06_LIFECYCLE_CONTRACT,
    "ratification_receipt": A20_RATIFICATION_RECEIPT_CONTRACT,
    "successor_routing": A20_SUCCESSOR_ROUTING_CONTRACT,
    "activation_transition": A20_ACTIVATION_TRANSITION,
    "mutation_inventory": list(A20_EXPECTED_MUTATIONS),
    "mutation_domain_byte_size": A20_MUTATION_DOMAIN_BYTE_SIZE,
    "mutation_domain_sha256": A20_MUTATION_DOMAIN_SHA256,
    "inherited_mutation_censuses": A20_INHERITED_MUTATION_CENSUSES,
    "supersession_coverage": A20_SUPERSESSION_COVERAGE,
    "new_identifiers": A20_NEW_IDENTIFIERS,
}

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

_A18_IMPLEMENTATION_PIN_PATTERN = re.compile(
    r"The\nAmendment-18-governed active identity is exactly mode "
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
_A18_IMPLEMENTATION_PIN_VALUE_GROUPS = (
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

_A19_IMPLEMENTATION_PIN_PATTERN = re.compile(
    r"The Amendment-19-governed active identity is exactly mode "
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
_A19_IMPLEMENTATION_PIN_VALUE_GROUPS = (
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

_A20_IMPLEMENTATION_PIN_PATTERN = re.compile(
    r"The Amendment-20-governed active identity is exactly mode "
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
_A20_IMPLEMENTATION_PIN_VALUE_GROUPS = (
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


def _amendment18_text(raw: bytes) -> str:
    """Return only the A18 suffix while preserving every inherited byte."""

    _require(
        len(raw) > REVISION19_BYTE_SIZE
        and _sha256(raw[:REVISION19_BYTE_SIZE]) == REVISION19_SHA256
        and _git_blob_oid(raw[:REVISION19_BYTE_SIZE]) == REVISION19_BLOB_OID
        and raw[REVISION19_BYTE_SIZE:].startswith(AMENDMENT18_BOUNDARY)
        and raw.count(AMENDMENT18_BOUNDARY) == 1
        and raw.endswith(b"\n"),
        "governing Amendment-18 document violates immutable-prefix law",
    )
    suffix = raw[REVISION19_BYTE_SIZE:]
    headings = list(_AMENDMENT_SECTION_PATTERN.finditer(suffix))
    _require(
        headings and int(headings[0].group("amendment")) == 18,
        "governing Amendment-18 boundary sequence drift",
    )
    if len(headings) > 1:
        next_boundary = headings[1].start()
        _require(
            next_boundary > 0
            and suffix[next_boundary - 1 : next_boundary] == b"\n",
            "governing Amendment-18 successor boundary drift",
        )
        suffix = suffix[: next_boundary - 1]
    try:
        return suffix.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LawError("governing Amendment-18 suffix is not UTF-8") from error


def _amendment18_implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_A18_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-18 implementation pin block grammar drift",
    )
    return matches[0]


def _normalize_amendment18_implementation_pin_values(section: str) -> str:
    """Normalize only the ten independently authenticated A18 pin values."""

    match = _amendment18_implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _A18_IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "Amendment-18 pin capture ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


def _parse_amendment18_implementation_pins(raw: bytes) -> dict[str, Any]:
    section = _amendment18_text(raw)
    match = _amendment18_implementation_pin_match(section)
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


def _parse_a18_build_input_domain_contract(section: str) -> dict[str, Any]:
    comparands = re.search(
        r"The questionnaire values\nare integer `(?P<questionnaire_count>[0-9]+)`, "
        r"keyset SHA-256\n`(?P<questionnaire_keyset>[0-9a-f]{64})`,\n"
        r"and domain SHA-256\n`(?P<questionnaire_domain>[0-9a-f]{64})`\.\n"
        r"The source values are integer `(?P<source_count>[0-9]+)`, "
        r"keyset SHA-256\n`(?P<source_keyset>[0-9a-f]{64})`,\n"
        r"and domain SHA-256\n`(?P<source_domain>[0-9a-f]{64})`\.\n"
        r"The repair/seal/evidence count is integer `(?P<repair_count>[0-9]+)`; "
        r"its ordered path-array digest\nis "
        r"`(?P<repair_domain>[0-9a-f]{64})`;\nand `row_count` is integer "
        r"`(?P<row_count>[0-9]+)`\.",
        section,
    )
    _require(
        comparands is not None,
        "Amendment-18 build-input comparand grammar drift",
    )
    positions = re.search(
        r"For positions (?P<source_first>[0-9]+) through "
        r"(?P<source_last>[0-9]+), `input_class` is "
        r"`(?P<source_class>[^`]+)`.*?For positions "
        r"(?P<repair_first>[0-9]+) through (?P<repair_last>[0-9]+), "
        r"`input_class` is\n`(?P<repair_class>[^`]+)`",
        section,
        re.DOTALL,
    )
    _require(
        positions is not None,
        "Amendment-18 build-input class-boundary grammar drift",
    )
    source_order = _code_after(
        section,
        "The 257 identities deep-equal the complete independently "
        "reconstructed `U`\nrows, in §19.3.3's existing\n",
        "Amendment-18 source ordering law",
    )
    questionnaire_role_match = re.search(
        r"The complete 81-row\n`document_role == (?P<role>[^`]+)` slice",
        section,
    )
    _require(
        questionnaire_role_match is not None,
        "Amendment-18 questionnaire slice role grammar drift",
    )
    questionnaire_role = questionnaire_role_match.group("role")
    digest_member = _code_after(
        section,
        "The SHA-256 of exactly those bytes is\n",
        "Amendment-18 build-input digest member",
    )
    repair_order_match = re.search(
        r"They are sorted once by (?P<order>unsigned UTF-8 repository path);",
        section,
    )
    _require(
        repair_order_match is not None,
        "Amendment-18 repair ordering law grammar drift",
    )
    repair_order = (
        repair_order_match.group("order")
        .replace("UTF-8", "UTF8")
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )
    _require(
        "R04 requires their\nenvelope objects and canonical bytes to "
        "deep-equal byte-for-byte" in section
        and "it does not embed or persist this envelope" in section,
        "Amendment-18 byte-equality or ephemeral-envelope law drift",
    )
    value = {
        "schema_version": _code_after(
            section,
            "one ephemeral object with schema\n",
            "Amendment-18 build-input schema",
        ),
        "canonicalization": _code_after(
            section,
            "`canonicalization` is exactly\n",
            "Amendment-18 build-input canonicalization",
        ),
        "questionnaire_document_count": int(
            comparands.group("questionnaire_count")
        ),
        "questionnaire_document_keyset_sha256": comparands.group(
            "questionnaire_keyset"
        ),
        "questionnaire_document_domain_sha256": comparands.group(
            "questionnaire_domain"
        ),
        "source_document_count": int(comparands.group("source_count")),
        "source_document_keyset_sha256": comparands.group("source_keyset"),
        "source_document_domain_sha256": comparands.group("source_domain"),
        "repair_seal_evidence_count": int(comparands.group("repair_count")),
        "repair_seal_evidence_path_domain_sha256": comparands.group(
            "repair_domain"
        ),
        "row_count": int(comparands.group("row_count")),
        "input_classes": [
            positions.group("source_class"),
            positions.group("repair_class"),
        ],
        "source_position_domain": [
            int(positions.group("source_first")),
            int(positions.group("source_last")),
        ],
        "repair_position_domain": [
            int(positions.group("repair_first")),
            int(positions.group("repair_last")),
        ],
        "source_order": source_order,
        "questionnaire_slice_role": questionnaire_role,
        "repair_order": repair_order,
        "digest_member": digest_member,
        "dual_canonical_byte_equality_required": True,
        "artifact_persisted": False,
    }
    value["envelope_keys"] = _fenced_lines_after(
        section,
        "It has exactly these twelve keys:\n\n",
        "Amendment-18 build-input envelope keys",
    )
    value["row_keys"] = _fenced_lines_after(
        section,
        "Each of the 279 `rows` objects has exactly:\n\n",
        "Amendment-18 build-input row keys",
    )
    value["source_identity_keys"] = _fenced_lines_after(
        section,
        "`input_identity` has exactly the eight §19.3.3 source-document "
        "keys:\n\n",
        "Amendment-18 source identity keys",
    )
    value["repair_identity_keys"] = _fenced_lines_after(
        section,
        "`repair_seal_evidence` and `input_identity` has exactly:\n\n",
        "Amendment-18 repair identity keys",
    )
    return value


def _parse_a18_activation_transition(section: str) -> dict[str, Any]:
    r05_revision = re.search(
        r"The terminal revision \*R\*\nmust be an integer greater than or "
        r"equal to (?P<revision>[0-9]+) and the returned ordered\ndomain "
        r"must deep-equal `(?P<domain>[^`]+)`\.",
        section,
    )
    r05_selection = re.search(
        r"select Amendment (?P<amendment>[0-9]+) at proved zero-based\n"
        r"position (?P<position>[0-9]+)\.",
        section,
    )
    activation = re.search(
        r"Its simulated terminal registry revision is integer "
        r"`(?P<revision>[0-9]+)`; terminal Amendment\n"
        r"(?P<amendment>[0-9]+); ordered closure domain "
        r"`\((?P<domain>[0-9, ]+)\)`; and exact closure\ncount "
        r"`(?P<count>[0-9]+) = (?P<revision_again>[0-9]+) - "
        r"(?P<subtrahend>[0-9]+)`\.",
        section,
    )
    _require(
        r05_revision is not None
        and r05_selection is not None
        and activation is not None
        and activation.group("revision") == activation.group("revision_again"),
        "Amendment-18 activation or R05 selector grammar drift",
    )
    public_entrypoint = _code_after(
        section,
        "The unmodified public\n",
        "Amendment-18 activation public entrypoint",
    ).removesuffix("()")
    r05_entrypoint = _code_after(
        section,
        "The validator calls the unmodified\npublic ",
        "Amendment-18 R05 public entrypoint",
    ).removesuffix("()")
    _require(
        "Amendment 18 is **activation-affecting**" in section
        and "Ambiguity would independently fail closed into the same result."
        in section
        and "one executed\nsame-state NONAUTHORITY demonstration" in section
        and "complete final pinned test battery\nmust run against that "
        "identical state" in section
        and "with zero\nfailed, skipped, deselected, xfailed, or xpassed "
        "tests" in section
        and "receipt remains outside candidate bytes" in section,
        "Amendment-18 activation obligation prose drift",
    )
    return {
        "activation_affecting": True,
        "ambiguity_fails_closed_into_obligation": True,
        "simulated_state_authority": "NONAUTHORITY",
        "terminal_revision": int(activation.group("revision")),
        "terminal_amendment": int(activation.group("amendment")),
        "ordered_closure_domain": [
            int(value.strip())
            for value in activation.group("domain").split(",")
        ],
        "closure_count": int(activation.group("count")),
        "closure_count_subtrahend": int(activation.group("subtrahend")),
        "public_entrypoint": public_entrypoint,
        "same_state_required": True,
        "full_pinned_battery_required": True,
        "all_nonpassing_counts": 0,
        "receipt_inside_candidate_bytes": False,
        "r05_public_entrypoint": r05_entrypoint,
        "r05_minimum_terminal_revision": int(r05_revision.group("revision")),
        "r05_expected_domain_expression": r05_revision.group("domain"),
        "r05_selected_zero_based_position": int(
            r05_selection.group("position")
        ),
        "r05_selected_amendment": int(r05_selection.group("amendment")),
    }


def _parse_a18_historical_r05_binding(section: str) -> dict[str, Any]:
    rows = _markdown_table(
        section,
        "| Key | Exact value |",
        "|---|---|",
        11,
        "Amendment-18 historical R05 binding",
    )
    parsed: dict[str, Any] = {}
    integer_keys = {
        "amendment_number",
        "closure_byte_size",
        "design_byte_size",
        "design_revision",
    }
    for key_cell, value_cell in rows:
        key = _code_tokens(key_cell, 1, "A18 R05 key")[0]
        value = _code_tokens(value_cell, 1, "A18 R05 value")[0]
        parsed[key] = int(value) if key in integer_keys else value
    _require(
        tuple(parsed) == tuple(A18_HISTORICAL_R05_BINDING),
        "Amendment-18 historical R05 binding order drift",
    )
    return parsed


def _parse_a18_r06_result_contract(section: str) -> dict[str, Any]:
    value = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    value["top_level_keys"] = _fenced_lines_after(
        section,
        "It has\nexactly these eleven top-level keys:\n\n",
        "Amendment-18 R06 top-level keys",
    )
    value["input_identity_keys"] = _fenced_lines_after(
        section,
        "`input_identities` has exactly:\n\n",
        "Amendment-18 R06 input identities",
    )
    value["process_result_keys"] = _fenced_lines_after(
        section,
        "`process_result` has exactly:\n\n",
        "Amendment-18 R06 process-result keys",
    )
    value["test_result_keys"] = _fenced_lines_after(
        section,
        "`test_result` has exactly:\n\n",
        "Amendment-18 R06 test-result keys",
    )
    value["test_module_paths"] = _fenced_lines_after(
        section,
        "The exact ordered six module paths are:\n\n",
        "Amendment-18 R06 module paths",
    )
    value["lifecycle_keys"] = _fenced_lines_after(
        section,
        "`lifecycle` has exactly:\n\n",
        "Amendment-18 R06 lifecycle keys",
    )
    value["nonemission_evidence_keys"] = _fenced_lines_after(
        section,
        "`nonemission_evidence` has exactly:\n\n",
        "Amendment-18 R06 nonemission keys",
    )
    return value


def _parse_a18_mutation_census(section: str) -> dict[str, Any]:
    match = re.search(
        r"exact inherited\n100-name census with digest\n"
        r"`(?P<inherited>[0-9a-f]{64})`\.\n"
        r"Amendment 16's seven remain exact with digest\n"
        r"`(?P<a16>[0-9a-f]{64})`\.\n"
        r"Amendment 17's three remain exact with digest\n"
        r"`(?P<a17>[0-9a-f]{64})`\.",
        section,
    )
    _require(match is not None, "Amendment-18 mutation census grammar drift")
    return {
        "inherited_complete_mutation_count": 100,
        "inherited_complete_mutation_domain_sha256": match.group("inherited"),
        "amendment16_mutation_count": 7,
        "amendment16_mutation_domain_sha256": match.group("a16"),
        "amendment17_mutation_count": 3,
        "amendment17_mutation_domain_sha256": match.group("a17"),
    }


def _parse_a18_new_identifiers(section: str) -> dict[str, list[str]]:
    return {
        "schema_and_path": _fenced_lines_after(
            section,
            "The exact new schema and path identifiers are:\n\n",
            "Amendment-18 schema/path identifiers",
        ),
        "status_role_lifecycle": _fenced_lines_after(
            section,
            "The exact new status, role, and lifecycle identifiers are:\n\n",
            "Amendment-18 status/role/lifecycle identifiers",
        ),
        "input_class": _fenced_lines_after(
            section,
            "The exact new input-class identifiers are:\n\n",
            "Amendment-18 input-class identifiers",
        ),
        "python": _fenced_lines_after(
            section,
            "The exact new Python identifiers are:\n\n",
            "Amendment-18 Python identifiers",
        ),
    }


def _parse_amendment18_projection(raw: bytes) -> dict[str, Any]:
    section = _amendment18_text(raw)
    mutations = _fenced_lines_after(
        section,
        "The separate Amendment-18 contract-cure mutation inventory is "
        "exactly:\n\n",
        "Amendment-18 contract mutations",
    )
    mutation_digest = _code_after(
        section,
        "Its ordered canonical name-array is 142 bytes with SHA-256\n",
        "Amendment-18 mutation domain SHA-256",
    )
    _require(
        _sha256(canonical_json_bytes(mutations)) == mutation_digest,
        "Amendment-18 mutation name-array digest drift",
    )
    return {
        "section_semantic_sha256": _sha256(
            _normalize_amendment18_implementation_pin_values(section).encode(
                "utf-8"
            )
        ),
        "implementation_pins": _parse_amendment18_implementation_pins(raw),
        "build_input_domain_contract": (
            _parse_a18_build_input_domain_contract(section)
        ),
        "historical_r05_binding": _parse_a18_historical_r05_binding(section),
        "r06_result_contract": _parse_a18_r06_result_contract(section),
        "activation_transition": _parse_a18_activation_transition(section),
        "contract_mutations": mutations,
        "contract_mutation_domain_sha256": mutation_digest,
        "mutation_census": _parse_a18_mutation_census(section),
        "supersession_map": _markdown_table(
            section,
            "| Earlier normative anchor | Amendment-18 disposition |",
            "|---|---|",
            7,
            "Amendment-18 supersession map",
        ),
        "new_identifiers": _parse_a18_new_identifiers(section),
    }


def _amendment19_text(raw: bytes) -> str:
    """Return only the A19 suffix while preserving every inherited byte."""

    _require(
        len(raw) > REVISION20_BYTE_SIZE
        and _sha256(raw[:REVISION20_BYTE_SIZE]) == REVISION20_SHA256
        and _git_blob_oid(raw[:REVISION20_BYTE_SIZE]) == REVISION20_BLOB_OID
        and raw[REVISION20_BYTE_SIZE:].startswith(AMENDMENT19_BOUNDARY)
        and raw.count(AMENDMENT19_BOUNDARY) == 1
        and raw.endswith(b"\n"),
        "governing Amendment-19 document violates immutable-prefix law",
    )
    suffix = raw[REVISION20_BYTE_SIZE:]
    headings = list(_AMENDMENT_SECTION_PATTERN.finditer(suffix))
    _require(
        headings and int(headings[0].group("amendment")) == 19,
        "governing Amendment-19 boundary sequence drift",
    )
    if len(headings) > 1:
        next_boundary = headings[1].start()
        _require(
            next_boundary > 0
            and suffix[next_boundary - 1 : next_boundary] == b"\n",
            "governing Amendment-19 successor boundary drift",
        )
        suffix = suffix[: next_boundary - 1]
    try:
        return suffix.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LawError("governing Amendment-19 suffix is not UTF-8") from error


def _amendment19_implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_A19_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-19 implementation pin block grammar drift",
    )
    return matches[0]


def _normalize_amendment19_implementation_pin_values(section: str) -> str:
    """Normalize only the ten independently authenticated A19 pin values."""

    match = _amendment19_implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _A19_IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "Amendment-19 pin capture ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


def _parse_amendment19_implementation_pins(raw: bytes) -> dict[str, Any]:
    section = _amendment19_text(raw)
    match = _amendment19_implementation_pin_match(section)
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


def _parse_a19_normative_manifest(section: str) -> dict[str, Any]:
    marker = (
        "The exact Amendment-19 normative manifest is this one-line "
        "terminal-LF canonical JSON value:\n\n"
    )
    remainder = _unique_after(
        section,
        marker,
        "Amendment-19 normative manifest",
    )
    _require(
        remainder.startswith("~~~text\n"),
        "Amendment-19 normative manifest fence start drift",
    )
    fenced = remainder[len("~~~text\n") :]
    _require(
        "\n~~~\n" in fenced,
        "Amendment-19 normative manifest fence end drift",
    )
    body, _ = fenced.split("\n~~~\n", 1)
    _require(
        "\n" not in body and bool(body),
        "Amendment-19 normative manifest line shape drift",
    )
    return _strict_canonical_json(
        body.encode("ascii") + b"\n",
        "Amendment-19 normative manifest",
    )


def _parse_amendment19_projection(raw: bytes) -> dict[str, Any]:
    section = _amendment19_text(raw)
    return {
        "section_semantic_sha256": _sha256(
            _normalize_amendment19_implementation_pin_values(section).encode(
                "utf-8"
            )
        ),
        "implementation_pins": _parse_amendment19_implementation_pins(raw),
        "normative_manifest": _parse_a19_normative_manifest(section),
    }


def _amendment20_text(raw: bytes) -> str:
    """Return only A20 while authenticating the complete revision-21 prefix."""

    _require(
        len(raw) > REVISION21_BYTE_SIZE
        and _sha256(raw[:REVISION21_BYTE_SIZE]) == REVISION21_SHA256
        and _git_blob_oid(raw[:REVISION21_BYTE_SIZE]) == REVISION21_BLOB_OID
        and raw[REVISION21_BYTE_SIZE:].startswith(AMENDMENT20_BOUNDARY)
        and raw.count(AMENDMENT20_BOUNDARY) == 1
        and raw.endswith(b"\n"),
        "governing Amendment-20 document violates immutable-prefix law",
    )
    suffix = raw[REVISION21_BYTE_SIZE:]
    headings = list(_AMENDMENT_SECTION_PATTERN.finditer(suffix))
    _require(
        headings and int(headings[0].group("amendment")) == 20,
        "governing Amendment-20 boundary sequence drift",
    )
    if len(headings) > 1:
        next_boundary = headings[1].start()
        _require(
            next_boundary > 0
            and suffix[next_boundary - 1 : next_boundary] == b"\n",
            "governing Amendment-20 successor boundary drift",
        )
        suffix = suffix[: next_boundary - 1]
    try:
        return suffix.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LawError("governing Amendment-20 suffix is not UTF-8") from error


def _amendment20_implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_A20_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-20 implementation pin block grammar drift",
    )
    return matches[0]


def _normalize_amendment20_implementation_pin_values(section: str) -> str:
    """Normalize only the ten independently authenticated A20 pin values."""

    match = _amendment20_implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _A20_IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "Amendment-20 pin capture ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


def _parse_amendment20_implementation_pins(raw: bytes) -> dict[str, Any]:
    section = _amendment20_text(raw)
    match = _amendment20_implementation_pin_match(section)
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


def _parse_a20_normative_manifest(section: str) -> dict[str, Any]:
    marker = (
        "The exact Amendment-20 normative manifest is this one-line "
        "terminal-LF canonical JSON value:\n\n"
    )
    remainder = _unique_after(
        section,
        marker,
        "Amendment-20 normative manifest",
    )
    _require(
        remainder.startswith("~~~text\n"),
        "Amendment-20 normative manifest fence start drift",
    )
    fenced = remainder[len("~~~text\n") :]
    _require(
        "\n~~~\n" in fenced,
        "Amendment-20 normative manifest fence end drift",
    )
    body, _ = fenced.split("\n~~~\n", 1)
    _require(
        "\n" not in body and bool(body),
        "Amendment-20 normative manifest line shape drift",
    )
    return _strict_canonical_json(
        body.encode("ascii") + b"\n",
        "Amendment-20 normative manifest",
    )


def _validate_amendment20_evidence_freeze(
    freeze: Mapping[str, Any],
    freeze_contract: Mapping[str, Any],
    *,
    require_ratification_ready: bool,
) -> None:
    """Validate the closed drafting or status-dependent A4 identity shape."""

    _require_exact_keys(
        freeze,
        set(A20_EVIDENCE_FREEZE),
        "Amendment-20 evidence freeze",
    )
    identity_contract = freeze_contract.get("identity_contract")
    _require(
        isinstance(identity_contract, Mapping)
        and identity_contract.get("common_identity_names")
        == A20_COMMON_IDENTITY_NAMES
        and identity_contract.get("arm_identity_contracts")
        == A20_ARM_IDENTITY_CONTRACTS
        and identity_contract.get("pass_identity_keys")
        == A20_PASS_IDENTITY_KEYS
        and identity_contract.get("arm_pass_identity_keys")
        == A20_ARM_PASS_IDENTITY_KEYS
        and identity_contract.get("successor_binding_identity_keys")
        == A20_SUCCESSOR_BINDING_IDENTITY_KEYS
        and identity_contract.get("failure_shadow_identity_keys")
        == A20_FAILURE_SHADOW_IDENTITY_KEYS
        and identity_contract.get("nonemission_complement_identity_keys")
        == A20_NONEMISSION_COMPLEMENT_IDENTITY_KEYS
        and identity_contract.get("failure_nonemission_evidence_keys")
        == A20_FAILURE_NONEMISSION_EVIDENCE_KEYS
        and identity_contract.get("repository_manifest_row_keys")
        == A20_REPOSITORY_MANIFEST_ROW_KEYS
        and identity_contract.get("successor_binding_identity_name")
        == "a20_successor_source_binding_identity"
        and identity_contract.get("successor_binding_digest_excludes_self")
        is True
        and identity_contract.get(
            "failure_shadow_rows_are_exact_forbidden_output_complement"
        )
        is True
        and identity_contract.get(
            "failure_shadow_paths_are_exact_arm_contract_paths"
        )
        is True
        and identity_contract.get(
            "lifecycle_booleans_are_not_accepted_as_self_attestation"
        )
        is True,
        "Amendment-20 evidence-freeze identity contract drift",
    )
    bindings = freeze.get("expected_identity_bindings")
    _require(
        freeze.get("schema_version") == "a20_evidence_freeze.v1"
        and isinstance(bindings, Mapping)
        and len(bindings) == len(A20_EXPECTED_IDENTITY_NAMES)
        and set(bindings) == set(A20_EXPECTED_IDENTITY_NAMES)
        and type(freeze.get("amendment20_ratification_ready")) is bool,
        "Amendment-20 evidence-freeze object drift",
    )

    drafting_status = "not_instantiated_a4_required_before_ratify"
    freeze_status = freeze.get("amendment20_evidence_freeze_status")
    if freeze_status == drafting_status:
        _require(
            all(
                freeze.get(status_member) is None
                for status_member in A20_ARM_IDENTITY_CONTRACTS
            )
            and all(identity is None for identity in bindings.values())
            and freeze["amendment20_ratification_ready"] is False,
            "Amendment-20 drafting evidence-freeze shape drift",
        )
        _require(
            not require_ratification_ready,
            "Amendment-20 evidence freeze is not ratification-ready",
        )
        return

    status_domains = freeze_contract.get("final_arm_status_domains")
    _require(
        freeze_status
        == freeze_contract.get("final_required_evidence_freeze_status")
        and isinstance(status_domains, Mapping)
        and set(status_domains) == set(A20_ARM_IDENTITY_CONTRACTS)
        and all(
            freeze.get(status_member) in status_domains[status_member]
            for status_member in A20_ARM_IDENTITY_CONTRACTS
        )
        and freeze["amendment20_ratification_ready"] is True,
        "Amendment-20 evidence freeze is not ratification-ready",
    )

    def nonzero_lower_hex(value: Any, length: int) -> bool:
        return _is_lower_hex(value, length) and value != "0" * length

    def validate_digest_identity(
        identity: Any,
        identity_name: str,
        *,
        arm_status_member: str | None = None,
        arm_status: str | None = None,
    ) -> None:
        expected_keys = (
            A20_PASS_IDENTITY_KEYS
            if arm_status_member is None
            else A20_ARM_PASS_IDENTITY_KEYS
        )
        _require(
            isinstance(identity, Mapping),
            f"Amendment-20 {identity_name} identity is absent",
        )
        _require_exact_keys(
            identity,
            set(expected_keys),
            f"Amendment-20 {identity_name} identity",
        )
        _require(
            identity["identity_name"] == identity_name
            and type(identity["row_count"]) is int
            and identity["row_count"] > 0
            and nonzero_lower_hex(identity["ordered_keyset_sha256"], 64)
            and nonzero_lower_hex(identity["row_domain_sha256"], 64)
            and identity["status"] == "pass",
            f"Amendment-20 {identity_name} identity count/digest/status drift",
        )
        if arm_status_member is not None:
            _require(
                identity["arm_status_member"] == arm_status_member
                and identity["arm_status"] == arm_status == "pass",
                f"Amendment-20 {identity_name} arm-status cross-binding drift",
            )

    successor_binding_name = "a20_successor_source_binding_identity"
    for identity_name in A20_COMMON_IDENTITY_NAMES:
        if identity_name != successor_binding_name:
            validate_digest_identity(bindings[identity_name], identity_name)

    for status_member, arm_contract in A20_ARM_IDENTITY_CONTRACTS.items():
        arm_status = freeze[status_member]
        pass_identity_names = arm_contract["pass_identity_names"]
        forbidden_output_paths = arm_contract["forbidden_output_paths"]
        shadow_name = arm_contract["failure_shadow_identity_name"]
        if arm_status == arm_contract["pass_status"]:
            _require(
                bindings[shadow_name] is None,
                f"Amendment-20 {status_member} pass carries a failure shadow",
            )
            for identity_name in pass_identity_names:
                validate_digest_identity(
                    bindings[identity_name],
                    identity_name,
                    arm_status_member=status_member,
                    arm_status=arm_status,
                )
            continue

        _require(
            arm_status == arm_contract["failure_status"]
            and all(bindings[name] is None for name in pass_identity_names),
            f"Amendment-20 {status_member} failure emitted a forbidden identity",
        )
        shadow = bindings[shadow_name]
        _require(
            isinstance(shadow, Mapping),
            f"Amendment-20 {status_member} failure shadow is absent",
        )
        _require_exact_keys(
            shadow,
            set(A20_FAILURE_SHADOW_IDENTITY_KEYS),
            f"Amendment-20 {status_member} failure shadow",
        )
        complement_rows = [
            {"emitted": False, "identity_name": name}
            for name in pass_identity_names
        ]
        complement_keyset_sha256 = _sha256(
            canonical_json_bytes(pass_identity_names)
        )
        complement_domain_sha256 = _sha256(
            canonical_json_bytes(complement_rows)
        )
        _require(
            shadow["schema_version"] == "a20_failure_shadow_identity.v1"
            and shadow["identity_name"] == shadow_name
            and shadow["arm_status_member"] == status_member
            and shadow["arm_status"] == arm_status
            and shadow["forbidden_output_identity_names"]
            == pass_identity_names
            and shadow["forbidden_output_paths"] == forbidden_output_paths
            and len(forbidden_output_paths) == len(pass_identity_names)
            and type(shadow["shadow_row_count"]) is int
            and shadow["shadow_row_count"] == len(pass_identity_names)
            and shadow["shadow_ordered_keyset_sha256"]
            == complement_keyset_sha256
            and shadow["shadow_row_domain_sha256"] == complement_domain_sha256
            and shadow["status"] == arm_status,
            f"Amendment-20 {status_member} failure-shadow cross-binding drift",
        )

        complement = shadow["complement_identity"]
        _require(
            isinstance(complement, Mapping),
            f"Amendment-20 {status_member} nonemission complement is absent",
        )
        _require_exact_keys(
            complement,
            set(A20_NONEMISSION_COMPLEMENT_IDENTITY_KEYS),
            f"Amendment-20 {status_member} nonemission complement",
        )
        _require(
            complement["schema_version"]
            == "a20_nonemission_complement_identity.v1"
            and complement["complement_of_identity_names"]
            == pass_identity_names
            and type(complement["row_count"]) is int
            and complement["row_count"] == len(pass_identity_names)
            and complement["ordered_keyset_sha256"] == complement_keyset_sha256
            and complement["row_domain_sha256"] == complement_domain_sha256
            and complement["status"] == arm_status,
            f"Amendment-20 {status_member} nonemission complement drift",
        )

        nonemission = shadow["nonemission_evidence"]
        _require(
            isinstance(nonemission, Mapping),
            f"Amendment-20 {status_member} nonemission evidence is absent",
        )
        _require_exact_keys(
            nonemission,
            set(A20_FAILURE_NONEMISSION_EVIDENCE_KEYS),
            f"Amendment-20 {status_member} nonemission evidence",
        )
        _require(
            nonzero_lower_hex(nonemission["execution_commit"], 40)
            and nonzero_lower_hex(nonemission["execution_tree_oid"], 40),
            f"Amendment-20 {status_member} nonemission object identity drift",
        )
        _validate_amendment20_nonemission_evidence(
            nonemission,
            forbidden_output_paths,
            status_member=status_member,
        )

    successor_binding = bindings[successor_binding_name]
    _require(
        isinstance(successor_binding, Mapping),
        "Amendment-20 successor source-binding identity is absent",
    )
    _require_exact_keys(
        successor_binding,
        set(A20_SUCCESSOR_BINDING_IDENTITY_KEYS),
        "Amendment-20 successor source-binding identity",
    )
    arm_status_bindings = {
        status_member: freeze[status_member]
        for status_member in A20_ARM_IDENTITY_CONTRACTS
    }
    active_binding_preimage = {
        "arm_status_bindings": arm_status_bindings,
        "expected_identity_bindings": {
            identity_name: bindings[identity_name]
            for identity_name in A20_EXPECTED_IDENTITY_NAMES
            if identity_name != successor_binding_name
        },
    }
    _require(
        successor_binding["identity_name"] == successor_binding_name
        and type(successor_binding["row_count"]) is int
        and successor_binding["row_count"] > 0
        and nonzero_lower_hex(successor_binding["ordered_keyset_sha256"], 64)
        and nonzero_lower_hex(successor_binding["row_domain_sha256"], 64)
        and successor_binding["arm_status_bindings"] == arm_status_bindings
        and successor_binding["active_identity_bindings_sha256"]
        == _sha256(canonical_json_bytes(active_binding_preimage))
        and successor_binding["status"] == "pass",
        "Amendment-20 successor source-binding identity cross-binding drift",
    )


def _validate_a20_manifest_contract(
    manifest: Mapping[str, Any],
    *,
    require_ratification_ready: bool = False,
) -> None:
    """Validate every A20 limb from one closed normative projection."""

    _require(
        manifest["controlling_external_records"]
        == A20_CONTROLLING_EXTERNAL_RECORDS,
        "Amendment-20 controlling external-record pins drift",
    )

    source = manifest["source_infrastructure"]
    _require(
        source["physical_source_row_keys"] == A20_PHYSICAL_SOURCE_ROW_KEYS
        and source["evidence_statement_row_keys"]
        == A20_EVIDENCE_STATEMENT_ROW_KEYS
        and source["path_rule"]
        == "repository_relative_canonical_traversal_free"
        and source["machine_local_absolute_paths_forbidden"] is True
        and source["historical_domains_preserved"]
        == {
            "a11_source_count": 47,
            "questionnaire_document_count": 81,
            "a19_build_input_source_document_count": 257,
            "a19_build_input_repair_seal_count": 22,
            "a19_build_input_row_count": 279,
        }
        and source["semantic_domain_order"]
        == ["missing_reason_source_domain", "purpose_source_domain"]
        and source["semantic_domain_identity_keys"]
        == A20_SEMANTIC_DOMAIN_IDENTITY_KEYS
        and source["successor_source_binding_keys"]
        == A20_SOURCE_INFRASTRUCTURE_CONTRACT["successor_source_binding_keys"]
        and all(
            member in source["semantic_domain_identity_keys"]
            for member in (
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
            )
        ),
        "Amendment-20 separate semantic-domain contract drift",
    )
    missing = manifest["missing_reason_authority"]
    _require(
        missing["formerly_unresolved_literal_occurrence_count"] == 524_538
        and len(missing["occurrence_identity_position_order"]) == 12
        and missing["claim_type"]
        == "strict_json_boolean_excluding_integer_coercion"
        and missing["projection_requirements"]
        == [
            "exact",
            "nonzero",
            "disjoint",
            "collectively_exhaustive",
            "exception_complete",
        ]
        and missing["representation_bridge_probe"][
            "observations_are_nonauthority"
        ]
        is True
        and missing["representation_bridge_probe"]["accepted_bridge_identity"]
        is None
        and missing["representation_bridge_probe"][
            "bridge_required_before_acceptance"
        ]
        is True
        and missing["transactional_atomic_nonemission"] is True,
        "Amendment-20 missing-reason authority contract drift",
    )
    purpose = manifest["purpose_authority"]
    _require(
        purpose["official_purpose_order"] == A19_OFFICIAL_PURPOSES
        and purpose["completed_ontology_order"]
        == [*A19_OFFICIAL_PURPOSES, "source_underdetermined"]
        and purpose["prompt_denominator_a4_freeze_slot"] is None
        and purpose["required_disposition_counts"]
        == {
            "complete_official_mapping": None,
            "source_underdetermined": None,
            "U": 0,
        }
        and purpose["source_underdetermined_count_a4_freeze_slot"] is None
        and purpose[
            "source_underdetermined_requires_reconciled_adjudication_ruling"
        ]
        is True
        and purpose[
            "source_underdetermined_uses_determined_row_provenance_authentication"
        ]
        is True
        and purpose["source_underdetermined_is_no_applicable_purpose"] is False
        and purpose["disposition_relation_total_under_completed_ontology"]
        is True
        and purpose["authority_gate_uses_reconciled_outcomes"] is True
        and purpose["exact_row_agreement_is_authority_gate"] is False
        and purpose["source_backed_alternative_selected"]
        == "ontology_projection"
        and purpose["inherited_complete_rows_requiring_source_regrounding"]
        == 818
        and purpose["manual_origin_grandfathering_permitted"] is False
        and purpose["purpose_arrays_nonempty_stable_unique_in_official_order"]
        is True
        and purpose[
            "exact_prompt_cover_and_zero_gap_extra_duplicate_overlap_conflict"
        ]
        is True,
        "Amendment-20 purpose-authority totality contract drift",
    )
    prompt = manifest["prompt_field_semantic_binding"]
    _require(
        prompt["collision_census"]
        == {
            "domain": (
                "historical_same_coordinate_leading_question_token_conflicts"
            ),
            "complete_official_prompt_count": 818,
            "multiple_count": 46,
        }
        and prompt["complete_official_prompt_candidate_census"]
        == A20_PROMPT_FIELD_SEMANTIC_BINDING_CONTRACT[
            "complete_official_prompt_candidate_census"
        ]
        and prompt["full_prompt_candidate_census"]
        == {
            "domain": "multiple_candidates_over_full_prompt_denominator",
            "prompt_count": 21_971,
            "multiple_count": 2_349,
        }
        and len(prompt["prompt_field_row_keys"]) == 13
        and prompt["questionnaire_span_keys"]
        == ["utf8_byte_start", "utf8_byte_end"]
        and prompt["prompt_field_evidence_id_prefix"]
        == "psid-prompt-field-evidence:"
        and len(prompt["prompt_field_evidence_id_preimage"]) == 12
        and prompt["coordinate_distinct_span_collapse_aborts"] is True
        and prompt["exact_duplicate_evidence_emission_aborts"] is True
        and prompt["c68_regression"]["candidate_raw_field_ids"]
        == ["V11804", "V11805"]
        and prompt["c68_regression"]["draft_disposition"]
        == "unresolved_multiple"
        and prompt["direct_identifier_priority_forbidden"] is True
        and prompt["required_unresolved_semantic_binding_count"] == 0
        and prompt["attachment_dispositions"]
        == [
            "accepted_exact_source_identifier",
            "accepted_expressly_admitted_official_alias",
            "unresolved_multiple",
        ]
        and len(prompt["prompt_field_candidate_set_row_keys"]) == 7
        and prompt["prompt_field_candidate_set_dispositions"]
        == ["zero_candidates", "one_candidate", "multiple_candidates"]
        and prompt["candidate_arrays_complete_stable_unique_source_order"]
        is True
        and prompt["candidate_disposition_is_iff_count_partition"] is True
        and prompt["candidate_set_id_is_sha256_of_canonical_remaining_members"]
        is True
        and prompt["candidate_set_row_ids_and_prompt_ids_unique"] is True
        and prompt["candidate_count_is_raw_field_array_length_strict_integer"]
        is True
        and len(prompt["zero_candidate_positive_group_row_keys"]) == 7
        and prompt["zero_candidate_positive_group_dispositions"]
        == [
            "complete_nonempty_reference_union",
            "fail_empty_reference_union",
        ]
        and prompt[
            "zero_candidate_group_one_per_qualifying_positive_occurrence"
        ]
        is True
        and prompt[
            "zero_candidate_prompt_arrays_complete_positive_row_projections"
        ]
        is True
        and prompt["zero_candidate_reference_union_complete_stable_unique"]
        is True
        and prompt["zero_candidate_group_disposition_is_iff_empty_boolean"]
        is True
        and prompt[
            "zero_candidate_group_id_is_sha256_of_canonical_remaining_members"
        ]
        is True
        and prompt["zero_candidate_group_ids_and_positive_ids_unique"] is True
        and prompt[
            "empty_reference_union_is_strict_boolean_zero_length_equality"
        ]
        is True
        and prompt["zero_candidate_grouping_probe"]
        == {
            "candidate_set_prompt_count": 21_971,
            "sweep_zero_candidate_observation": 15_428,
            "diagnostic_zero_candidate_observation": 14_450,
            "observations_are_nonauthority": True,
            "difference_explained": False,
            "accepted_positive_group_with_empty_reference_union_count": None,
            "accepted_attachment_required_for_codebook_supported_rule": True,
        }
        and prompt["semantic_binding_serialization"]
        == "near_match_source_annotation_rows"
        and prompt["separate_semantic_binding_rows_serialization_permitted"]
        is False
        and prompt["semantic_binding_identity_requires_deep_equality"]
        == ["row_count", "ordered_keyset_sha256", "row_domain_sha256"]
        and prompt["binding_built_before_candidate_rows_read"] is True,
        "Amendment-20 prompt-field or semantic-binding contract drift",
    )
    r04 = manifest["r04_q5"]
    _require(
        r04["construction_order"] == A20_R04_Q5_CONTRACT["construction_order"]
        and r04["o_h_precedes_o_p_on_normal_arm"] is True
        and r04["purpose_totality_alone_passes_r04"] is False
        and r04["selector_purpose_domain"] == "completed_purpose_ontology"
        and r04["o_p_order"]
        == [*A19_OFFICIAL_PURPOSES, "source_underdetermined"]
        and r04["purpose_expansion_domain"] == "completed_purpose_ontology"
        and r04["purpose_rule_projection_domain"]
        == "completed_purpose_ontology"
        and "questionnaire_occurrence_rows"
        in r04["permitted_selector_input_reads"]
        and "questionnaire_occurrence_rows"
        in r04["forbidden_selected_failure_member_serialization"]
        and r04["source_document_manifest_additions"]
        == A20_R04_Q5_CONTRACT["source_document_manifest_additions"]
        and r04["normal_effective_header_successor_members"]
        == A20_R04_Q5_CONTRACT["normal_effective_header_successor_members"]
        and r04["normal_era_successor_sequence"]
        == A20_R04_Q5_CONTRACT["normal_era_successor_sequence"]
        and r04["a19_digest_dependency_order_preserved"]
        == ["D0", "search_implementation", "A_h", "final_rows", "D1"]
        and r04[
            "a19_purpose_mapping_is_historical_nonconsumable_on_a20_normal_path"
        ]
        is True,
        "Amendment-20 R04 order or Q5 shape contract drift",
    )
    r06 = manifest["r06_lifecycle"]
    _require(
        r06["interpreter_selector"] == "executing_process_sys.executable"
        and r06["ambient_pytest_addopts_removed"] is True
        and r06["collection_command_after_interpreter"]
        == [
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            *[row["path"] for row in A20_R06_FILE_IDENTITIES],
        ]
        and len(r06["test_file_identities"]) == 6
        and r06["test_file_identities"] == A20_R06_FILE_IDENTITIES
        and r06["collected_node_id_count"] == 223
        and r06["collected_node_id_array_canonical_byte_size"] == 28_268
        and r06["collected_node_id_array_raw_sha256"]
        == "09071bf4d9a9a5ee8b9ccc4d8d5c0bd91705c04d3c7c99d6ef155dfdc0dfdf05"
        and r06["dormant_definition_before_certification_permitted"] is True
        and r06["dormant_definition_creates_instance_or_selection"] is False
        and r06["dormant_lifecycle_row_count"] == 26
        and r06["dormant_lifecycle_rows"] == A20_DORMANT_LIFECYCLE_ROWS
        and [row["first_add_index"] for row in r06["dormant_lifecycle_rows"]]
        == list(range(1, 27))
        and r06["selection_first_add_dispatch_requires_r04_r05_r06_order"]
        is True,
        "Amendment-20 R06 collection or lifecycle contract drift",
    )
    freeze_contract = manifest["evidence_freeze_contract"]
    freeze = manifest["amendment20_evidence_freeze"]
    _require(
        freeze_contract == A20_EVIDENCE_FREEZE_CONTRACT
        and freeze == freeze_contract["object"],
        "Amendment-20 evidence-freeze object drift",
    )
    _validate_amendment20_evidence_freeze(
        freeze,
        freeze_contract,
        require_ratification_ready=require_ratification_ready,
    )
    receipt = manifest["ratification_receipt"]
    _require(
        receipt["amendment20_external_receipt_path"]
        == A20_EXECUTED_TRANSITION_RECEIPT_PATH
        and receipt["inherited_external_receipt_path_template"]
        == (
            "docs/analysis/amendment_<N>_ratification/"
            "executed_transition_receipt_v2.json"
        )
        and receipt["external_receipt_mode"] == "100644"
        and receipt["candidate_production_registry_identity"]
        == A20_PRODUCTION_REGISTRY_IDENTITY
        and receipt[
            "external_receipt_strict_canonical_tracked_head_worktree_read"
        ]
        is True
        and receipt["external_receipt_candidate_ancestry_not_required"] is True
        and receipt[
            "external_receipt_first_add_precedes_or_equals_closure_first_add"
        ]
        is True
        and receipt["scratch_commit_forbidden_as_production_ancestor"] is True
        and receipt["receipt_candidate_design_tree_mode_blob_rederived"]
        is True
        and receipt[
            "receipt_candidate_design_exactly_cross_binds_historical_a20_closure_and_verdicts"
        ]
        is True
        and receipt[
            "current_terminal_registry_cross_binding_required_iff_a20_terminal_revision22"
        ]
        is True
        and receipt[
            "later_revision_authenticates_historical_a20_design_under_30_2_3"
        ]
        is True
        and receipt[
            "receipt_rederives_synthetic_closure_standins_and_registry_binding"
        ]
        is True
        and receipt["receipt_public_result_booleans_not_sufficient"] is True
        and receipt[
            "later_amendment_requires_own_exact_receipt_topology_projection"
        ]
        is True
        and receipt["qualifying_verdict_line_count"] == 8
        and receipt["qualifying_verdict_lines"][-2]
        == "executed_transition_receipt_schema: executed_transition_state.v2"
        and receipt["scratch"]["standin_prefix_line_count"] == 4
        and receipt["receipt_schema"]["top_level_keys"]
        == A17_RECEIPT_SCHEMA["top_level_keys"]
        and receipt["receipt_schema"]["manifest_schema_version"]
        == "executed_transition_state.v2"
        and receipt["receipt_schema"][
            "candidate_or_scratch_HEAD_member_superseded"
        ]
        is True
        and len(
            canonical_json_bytes(
                receipt["receipt_schema"]["expected_changed_paths"]
            )
        )
        == 260
        and _sha256(
            canonical_json_bytes(
                receipt["receipt_schema"]["expected_changed_paths"]
            )
        )
        == "5a7912498c4d959fef337f2a1d1cf85a2f254fa29d825d365ccf4fe214ad48a7",
        "Amendment-20 verdict, receipt, or scratch contract drift",
    )
    campaign = manifest["evidence_campaign"]
    _require(
        campaign == A20_EVIDENCE_CAMPAIGN_CONTRACT
        and campaign["rounds_formula"] == "ceil(2L/(3q))"
        and campaign["forecast_as_of"] == "2026-08-15"
        and campaign["conditional_p50"] == "2026-11-09"
        and campaign["conditional_p80"] == "2027-01-22"
        and campaign["dates_are_nonauthority_conditional_planning_metadata"]
        is True,
        "Amendment-20 evidence-campaign contract drift",
    )
    mutations = manifest["mutation_inventory"]
    mutation_raw = canonical_json_bytes(mutations)
    _require(
        mutations == list(A20_EXPECTED_MUTATIONS)
        and len(mutation_raw) == A20_MUTATION_DOMAIN_BYTE_SIZE
        and _sha256(mutation_raw) == A20_MUTATION_DOMAIN_SHA256,
        "Amendment-20 mutation inventory drift",
    )
    routing = manifest["successor_routing"]
    activation = manifest["activation_transition"]
    _require(
        routing == A20_SUCCESSOR_ROUTING_CONTRACT
        and activation == A20_ACTIVATION_TRANSITION
        and routing["a20_pins_selected_before_a19_pins"] is True
        and routing["a19_pin_fallback_for_terminal_a20_permitted"] is False
        and activation["ordered_closure_domain"]
        == [13, 14, 15, 16, 17, 18, 19, 20]
        and activation["closure_count"] == 8,
        "Amendment-20 successor routing or activation contract drift",
    )
    _require(
        manifest["supersession_coverage"] == A20_SUPERSESSION_COVERAGE
        and len(manifest["supersession_coverage"]) == 30
        and any("30.2.2" in row for row in manifest["supersession_coverage"]),
        "Amendment-20 supersession coverage drift",
    )
    _require(
        all(
            "A21" not in identifier
            for values in manifest["new_identifiers"].values()
            for identifier in values
        )
        and all(
            len(values) == len(set(values))
            for values in manifest["new_identifiers"].values()
        )
        and sum(len(values) for values in manifest["new_identifiers"].values())
        == len(
            {
                identifier
                for values in manifest["new_identifiers"].values()
                for identifier in values
            }
        ),
        "Amendment-20 manifest invents an A21 identifier",
    )
    _require(
        manifest == A20_NORMATIVE_MANIFEST,
        "Amendment-20 normative manifest drift",
    )


def _parse_amendment20_projection(raw: bytes) -> dict[str, Any]:
    section = _amendment20_text(raw)
    manifest = _parse_a20_normative_manifest(section)
    _validate_a20_manifest_contract(manifest)
    supersession_rows = _markdown_table(
        section,
        "| Earlier normative anchor | Amendment-20 disposition |",
        "|---|---|",
        len(manifest["supersession_coverage"]),
        "Amendment-20 supersession disposition",
    )
    mutation_disposition_position = manifest["supersession_coverage"].index(
        "33.6_mutation_inventory_and_inherited_census"
    )
    _require(
        len(manifest["mutation_inventory"]) == 15
        and supersession_rows[mutation_disposition_position]
        == [
            "§33.6 mutation inventory and inherited census",
            "Preserved as three A19 names after the earlier 113 attacks. "
            "A20 runs the five inherited censuses separately, then its "
            "own fifteen-name inventory.",
        ],
        "Amendment-20 mutation inventory prose disposition drift",
    )
    return {
        "section_semantic_sha256": _sha256(
            _normalize_amendment20_implementation_pin_values(section).encode(
                "utf-8"
            )
        ),
        "implementation_pins": _parse_amendment20_implementation_pins(raw),
        "normative_manifest": manifest,
    }


def _parse_active_implementation_pins(raw: bytes) -> dict[str, Any]:
    """Select the newest append-only implementation-pin successor."""

    if len(raw) > REVISION21_BYTE_SIZE:
        return _parse_amendment20_implementation_pins(raw)
    if len(raw) > REVISION20_BYTE_SIZE:
        return _parse_amendment19_implementation_pins(raw)
    if len(raw) > REVISION19_BYTE_SIZE:
        return _parse_amendment18_implementation_pins(raw)
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
        "amendment18": _parse_amendment18_projection(raw),
        "amendment19": _parse_amendment19_projection(raw),
        "amendment20": _parse_amendment20_projection(raw),
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


def _canonical_amendment18_projection() -> dict[str, Any]:
    return {
        "section_semantic_sha256": A18_SECTION_SEMANTIC_SHA256,
        "implementation_pins": None,
        "build_input_domain_contract": copy.deepcopy(
            A18_BUILD_INPUT_DOMAIN_CONTRACT
        ),
        "historical_r05_binding": copy.deepcopy(A18_HISTORICAL_R05_BINDING),
        "r06_result_contract": copy.deepcopy(A18_R06_RESULT_CONTRACT),
        "activation_transition": copy.deepcopy(A18_ACTIVATION_TRANSITION),
        "contract_mutations": list(A18_EXPECTED_MUTATIONS),
        "contract_mutation_domain_sha256": A18_MUTATION_DOMAIN_SHA256,
        "mutation_census": copy.deepcopy(A18_MUTATION_CENSUS),
        "supersession_map": [list(row) for row in A18_SUPERSESSION_MAP],
        "new_identifiers": copy.deepcopy(A18_NEW_IDENTIFIERS),
    }


def _canonical_amendment19_projection() -> dict[str, Any]:
    return {
        "section_semantic_sha256": A19_SECTION_SEMANTIC_SHA256,
        "implementation_pins": None,
        "normative_manifest": copy.deepcopy(A19_NORMATIVE_MANIFEST),
    }


def _canonical_amendment20_projection() -> dict[str, Any]:
    return {
        "section_semantic_sha256": A20_SECTION_SEMANTIC_SHA256,
        "implementation_pins": None,
        "normative_manifest": copy.deepcopy(A20_NORMATIVE_MANIFEST),
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
        "amendment18": _canonical_amendment18_projection(),
        "amendment19": _canonical_amendment19_projection(),
        "amendment20": _canonical_amendment20_projection(),
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
    if len(current_design) > REVISION21_BYTE_SIZE:
        pins = _parse_amendment20_implementation_pins(current_design)
        label = "Amendment-20"
    elif len(current_design) > REVISION20_BYTE_SIZE:
        pins = _parse_amendment19_implementation_pins(current_design)
        label = "Amendment-19"
    elif len(current_design) > REVISION19_BYTE_SIZE:
        pins = _parse_amendment18_implementation_pins(current_design)
        label = "Amendment-18"
    elif len(current_design) > REVISION18_BYTE_SIZE:
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
    expected["amendment18"]["implementation_pins"] = projection["amendment18"][
        "implementation_pins"
    ]
    expected["amendment19"]["implementation_pins"] = projection["amendment19"][
        "implementation_pins"
    ]
    expected["amendment20"]["implementation_pins"] = projection["amendment20"][
        "implementation_pins"
    ]
    _require(
        projection == expected,
        "governing Amendment-14/15/16/17/18/19/20 document semantic projection "
        "drift",
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


def _canonical_amendment20_repository_path(path: Any) -> bool:
    """Recognize one canonical, traversal-free UTF-8 repository path."""

    if not isinstance(path, str) or not path:
        return False
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return False
    candidate = PurePosixPath(path)
    return (
        not candidate.is_absolute()
        and candidate.as_posix() == path
        and all(part not in {"", ".", ".."} for part in candidate.parts)
    )


def _read_amendment20_worktree_file(
    path: str,
    *,
    verification_root: Path,
) -> tuple[bytes, str]:
    """Reread one regular file or symlink from the execution worktree."""

    worktree_path = verification_root / path
    try:
        metadata = worktree_path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            return os.fsencode(os.readlink(worktree_path)), "120000"
        _require(
            stat.S_ISREG(metadata.st_mode),
            "Amendment-20 manifest member is not a file",
        )
        mode = "100755" if metadata.st_mode & 0o111 else "100644"
        return worktree_path.read_bytes(), mode
    except OSError as error:
        raise LawError(
            "Amendment-20 manifest working bytes cannot be reread"
        ) from error


def _reconstruct_amendment20_repository_manifest(
    execution_tree_oid: str,
    *,
    verification_root: Path,
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """Rebuild the complete tracked/untracked §29.4.1 manifest."""

    tree_listing = _run_git(
        "-C",
        str(verification_root),
        "ls-tree",
        "-rz",
        "--full-tree",
        execution_tree_oid,
    )
    _require(
        tree_listing.returncode == 0
        and isinstance(tree_listing.stdout, bytes),
        "Amendment-20 execution tree cannot be enumerated",
    )
    rows: list[dict[str, Any]] = []
    tracked_paths: set[str] = set()
    for raw_entry in tree_listing.stdout.split(b"\0"):
        if not raw_entry:
            continue
        try:
            raw_metadata, raw_path = raw_entry.split(b"\t", 1)
            mode, object_type, raw_oid = raw_metadata.split(b" ", 2)
            path = raw_path.decode("utf-8")
            object_id = raw_oid.decode("ascii")
            mode_text = mode.decode("ascii")
            object_type_text = object_type.decode("ascii")
        except (UnicodeDecodeError, ValueError) as error:
            raise LawError(
                "Amendment-20 execution tree has a noncanonical entry"
            ) from error
        _require(
            _canonical_amendment20_repository_path(path)
            and path not in tracked_paths
            and object_type_text == "blob"
            and mode_text in {"100644", "100755", "120000"}
            and _is_lower_hex(object_id, 40),
            "Amendment-20 execution tree has an unsupported entry",
        )
        blob_result = _run_git(
            "-C",
            str(verification_root),
            "cat-file",
            "blob",
            object_id,
        )
        _require(
            blob_result.returncode == 0
            and isinstance(blob_result.stdout, bytes)
            and _git_blob_oid(blob_result.stdout) == object_id,
            "Amendment-20 execution tree blob cannot be authenticated",
        )
        working_raw, working_mode = _read_amendment20_worktree_file(
            path,
            verification_root=verification_root,
        )
        _require(
            working_mode == mode_text and working_raw == blob_result.stdout,
            "Amendment-20 tracked working bytes do not exact-match the tree",
        )
        tracked_paths.add(path)
        rows.append(
            {
                "path": path,
                "mode": mode_text,
                "git_blob": object_id,
                "byte_size": len(blob_result.stdout),
                "raw_sha256": _sha256(blob_result.stdout),
            }
        )

    untracked_listing = _run_git(
        "-C",
        str(verification_root),
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )
    _require(
        untracked_listing.returncode == 0
        and isinstance(untracked_listing.stdout, bytes),
        "Amendment-20 nonignored untracked paths cannot be enumerated",
    )
    untracked_paths: list[str] = []
    for raw_path in untracked_listing.stdout.split(b"\0"):
        if not raw_path:
            continue
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError as error:
            raise LawError(
                "Amendment-20 untracked path is not UTF-8"
            ) from error
        _require(
            _canonical_amendment20_repository_path(path)
            and path not in tracked_paths
            and path not in untracked_paths,
            "Amendment-20 untracked path is noncanonical or duplicated",
        )
        raw, mode_text = _read_amendment20_worktree_file(
            path,
            verification_root=verification_root,
        )
        untracked_paths.append(path)
        rows.append(
            {
                "path": path,
                "mode": mode_text,
                "git_blob": _git_blob_oid(raw),
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
            }
        )

    rows.sort(key=lambda row: row["path"].encode("utf-8"))
    index_result = _run_git(
        "-C",
        str(verification_root),
        "diff",
        "--cached",
        "--quiet",
        execution_tree_oid,
        "--",
    )
    _require(
        index_result.returncode == 0,
        "Amendment-20 repository index does not exact-match the tree",
    )
    status_result = _run_git(
        "-C",
        str(verification_root),
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    _require(
        status_result.returncode == 0 and status_result.stdout == b"",
        "Amendment-20 repository is not exactly clean",
    )
    return rows, tuple(untracked_paths)


def _validate_amendment20_nonemission_evidence(
    nonemission: Mapping[str, Any],
    forbidden_output_paths: Sequence[str],
    *,
    status_member: str,
) -> None:
    """Authenticate failure nonemission without trusting lifecycle booleans."""

    label = f"Amendment-20 {status_member}"
    execution_commit = nonemission["execution_commit"]
    execution_tree_oid = nonemission["execution_tree_oid"]
    commit_result = _run_git(
        "rev-parse",
        "--verify",
        f"{execution_commit}^{{commit}}",
        text=True,
    )
    _require(
        commit_result.returncode == 0
        and commit_result.stdout.strip() == execution_commit,
        f"{label} execution commit is not an exact commit object",
    )
    tree_result = _run_git(
        "rev-parse",
        "--verify",
        f"{execution_tree_oid}^{{tree}}",
        text=True,
    )
    _require(
        tree_result.returncode == 0
        and tree_result.stdout.strip() == execution_tree_oid,
        f"{label} execution tree is not an exact tree object",
    )
    commit_tree_result = _run_git(
        "rev-parse",
        "--verify",
        f"{execution_commit}^{{tree}}",
        text=True,
    )
    _require(
        commit_tree_result.returncode == 0
        and commit_tree_result.stdout.strip() == execution_tree_oid,
        f"{label} execution commit/tree binding drift",
    )

    supplied_manifests: list[list[dict[str, Any]]] = []
    for phase in ("before", "after"):
        manifest = nonemission[f"repository_manifest_rows_{phase}"]
        _require(
            isinstance(manifest, list),
            f"{label} repository manifest {phase} is not an array",
        )
        paths: list[str] = []
        for row in manifest:
            _require(
                isinstance(row, Mapping),
                f"{label} repository manifest {phase} row is not an object",
            )
            _require_exact_keys(
                row,
                set(A20_REPOSITORY_MANIFEST_ROW_KEYS),
                f"{label} repository manifest {phase} row",
            )
            _require(
                _canonical_amendment20_repository_path(row["path"])
                and row["mode"] in {"100644", "100755", "120000"}
                and _is_lower_hex(row["git_blob"], 40)
                and type(row["byte_size"]) is int
                and row["byte_size"] >= 0
                and _is_lower_hex(row["raw_sha256"], 64),
                f"{label} repository manifest {phase} row identity drift",
            )
            paths.append(row["path"])
        _require(
            paths == sorted(paths, key=lambda path: path.encode("utf-8"))
            and len(paths) == len(set(paths)),
            f"{label} repository manifest {phase} order/domain drift",
        )
        supplied_manifests.append([dict(row) for row in manifest])

    before_rows, after_rows = supplied_manifests
    with tempfile.TemporaryDirectory(
        prefix="a20-verification-checkout-"
    ) as temporary:
        verification_root = Path(temporary) / "checkout"
        checkout_needs_cleanup = False
        try:
            checkout_result = _run_git(
                "worktree",
                "add",
                "--detach",
                "--quiet",
                str(verification_root),
                execution_commit,
            )
            checkout_needs_cleanup = (
                checkout_result.returncode == 0 or verification_root.exists()
            )
            _require(
                checkout_result.returncode == 0,
                f"{label} execution commit cannot be materialized",
            )
            checkout_head = _run_git(
                "-C",
                str(verification_root),
                "rev-parse",
                "--verify",
                "HEAD^{commit}",
                text=True,
            )
            _require(
                checkout_head.returncode == 0
                and checkout_head.stdout.strip() == execution_commit,
                f"{label} verification checkout identity drift",
            )
            reconstructed_rows, untracked_paths = (
                _reconstruct_amendment20_repository_manifest(
                    execution_tree_oid,
                    verification_root=verification_root,
                )
            )
        finally:
            if checkout_needs_cleanup:
                cleanup_result = _run_git(
                    "worktree",
                    "remove",
                    "--force",
                    str(verification_root),
                )
                _require(
                    cleanup_result.returncode == 0,
                    f"{label} verification checkout cleanup failed",
                )
    _require(
        before_rows == reconstructed_rows and after_rows == reconstructed_rows,
        f"{label} repository manifest authentication drift",
    )
    before_sha256 = _sha256(canonical_json_bytes(before_rows))
    after_sha256 = _sha256(canonical_json_bytes(after_rows))
    _require(
        nonemission["repository_manifest_sha256_before"] == before_sha256
        and nonemission["repository_manifest_sha256_after"] == after_sha256
        and before_rows == after_rows
        and before_sha256 == after_sha256,
        f"{label} repository manifest digest or equality drift",
    )
    _require(
        all(
            _canonical_amendment20_repository_path(path)
            for path in forbidden_output_paths
        )
        and len(forbidden_output_paths) == len(set(forbidden_output_paths)),
        f"{label} forbidden output path domain drift",
    )
    after_paths = {row["path"] for row in after_rows}
    forbidden_outputs_absent = all(
        path not in after_paths for path in forbidden_output_paths
    )
    repository_clean = not untracked_paths
    _require(
        repository_clean
        and forbidden_outputs_absent
        and nonemission["repository_clean_before"] is repository_clean
        and nonemission["repository_clean_after"] is repository_clean
        and nonemission["forbidden_outputs_absent_after_execution"]
        is forbidden_outputs_absent,
        f"{label} independently derived nonemission facts drift",
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


_A20_DECIMAL_GRAMMAR = r"(?:[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)"
_A20_QUALIFYING_VERDICT_PATTERN = re.compile(
    rf"\A# RATIFY\n"
    rf"attested_design_byte_size: (?P<design_size>{_A20_DECIMAL_GRAMMAR})\n"
    rf"attested_design_raw_sha256: (?P<design_sha>[0-9a-f]{{64}})\n"
    rf"attested_design_blob_oid: (?P<design_blob>[0-9a-f]{{40}})\n"
    rf"executed_transition_receipt_byte_size: "
    rf"(?P<receipt_size>{_A20_DECIMAL_GRAMMAR})\n"
    rf"executed_transition_receipt_raw_sha256: "
    rf"(?P<receipt_sha>[0-9a-f]{{64}})\n"
    rf"executed_transition_receipt_schema: executed_transition_state\.v2\n"
    rf"---\n\Z"
)
_A20_SIMULATED_STANDIN_PATTERN = re.compile(
    rf"\A# RATIFY\n"
    rf"attested_design_byte_size: (?P<design_size>{_A20_DECIMAL_GRAMMAR})\n"
    rf"attested_design_raw_sha256: (?P<design_sha>[0-9a-f]{{64}})\n"
    rf"attested_design_blob_oid: (?P<design_blob>[0-9a-f]{{40}})\n"
    rf"executed_transition_receipt_status: pending_same_state_execution\n"
    rf"simulation_context: amendment20_same_state_nonauthority_v1\n"
    rf"---\n\Z"
)


def _decode_amendment20_verdict(raw: bytes, label: str) -> str:
    _require(isinstance(raw, bytes), f"{label} is not bytes")
    _require(
        not raw.startswith(b"\xef\xbb\xbf")
        and b"\x00" not in raw
        and b"\r" not in raw
        and raw.endswith(b"\n")
        and not raw.endswith(b"\n\n"),
        f"{label} violates strict UTF-8/LF framing",
    )
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise LawError(f"{label} is not strict UTF-8") from error


def _a20_decimal(value: str, label: str) -> int:
    _require(
        re.fullmatch(_A20_DECIMAL_GRAMMAR, value) is not None,
        f"{label} decimal grammar drift",
    )
    parsed = int(value.replace(",", ""))
    _require(parsed > 0, f"{label} must be positive")
    return parsed


def validate_amendment20_qualifying_verdict(
    raw: bytes,
    *,
    design_byte_size: int,
    design_raw_sha256: str,
    design_blob_oid: str,
    receipt_byte_size: int,
    receipt_raw_sha256: str,
) -> dict[str, Any]:
    """Strict-parse one A20 qualifying verdict and verify its attestations."""

    _require(
        type(design_byte_size) is int
        and design_byte_size > 0
        and _is_lower_hex(design_raw_sha256, 64)
        and _is_lower_hex(design_blob_oid, 40),
        "Amendment-20 expected design attestation is malformed",
    )
    _require(
        type(receipt_byte_size) is int
        and receipt_byte_size > 0
        and _is_lower_hex(receipt_raw_sha256, 64),
        "Amendment-20 expected receipt attestation is malformed",
    )
    text = _decode_amendment20_verdict(
        raw,
        "Amendment-20 qualifying verdict",
    )
    match = _A20_QUALIFYING_VERDICT_PATTERN.fullmatch(text)
    _require(
        match is not None, "Amendment-20 qualifying verdict grammar drift"
    )
    parsed = {
        "design_byte_size": _a20_decimal(
            match.group("design_size"),
            "Amendment-20 design byte size",
        ),
        "design_raw_sha256": match.group("design_sha"),
        "design_blob_oid": match.group("design_blob"),
        "receipt_byte_size": _a20_decimal(
            match.group("receipt_size"),
            "Amendment-20 receipt byte size",
        ),
        "receipt_raw_sha256": match.group("receipt_sha"),
        "receipt_schema": "executed_transition_state.v2",
    }
    _require(
        parsed["design_byte_size"] == design_byte_size
        and parsed["design_raw_sha256"] == design_raw_sha256
        and parsed["design_blob_oid"] == design_blob_oid,
        "Amendment-20 verdict design attestation mismatch",
    )
    _require(
        parsed["receipt_byte_size"] == receipt_byte_size
        and parsed["receipt_raw_sha256"] == receipt_raw_sha256,
        "Amendment-20 verdict receipt attestation mismatch",
    )
    return parsed


def _validate_amendment20_simulated_standin(
    raw: bytes,
    *,
    design_byte_size: int,
    design_raw_sha256: str,
    design_blob_oid: str,
) -> dict[str, Any]:
    """Accept only the distinct seven-line scratch-construction stand-in."""

    _require(
        type(design_byte_size) is int
        and design_byte_size > 0
        and _is_lower_hex(design_raw_sha256, 64)
        and _is_lower_hex(design_blob_oid, 40),
        "Amendment-20 stand-in expected design attestation is malformed",
    )
    text = _decode_amendment20_verdict(
        raw,
        "Amendment-20 simulated stand-in",
    )
    match = _A20_SIMULATED_STANDIN_PATTERN.fullmatch(text)
    _require(
        match is not None, "Amendment-20 simulated stand-in grammar drift"
    )
    parsed = {
        "design_byte_size": _a20_decimal(
            match.group("design_size"),
            "Amendment-20 stand-in design byte size",
        ),
        "design_raw_sha256": match.group("design_sha"),
        "design_blob_oid": match.group("design_blob"),
        "executed_transition_receipt_status": ("pending_same_state_execution"),
        "simulation_context": "amendment20_same_state_nonauthority_v1",
    }
    _require(
        parsed["design_byte_size"] == design_byte_size
        and parsed["design_raw_sha256"] == design_raw_sha256
        and parsed["design_blob_oid"] == design_blob_oid,
        "Amendment-20 stand-in design attestation mismatch",
    )
    return parsed


def _validate_amendment20_r06_collection_binding() -> dict[str, Any]:
    """Reauthenticate the six pinned files and exact 223-node collection."""

    for row in A20_R06_FILE_IDENTITIES:
        path = row["path"]
        try:
            worktree_raw = (ROOT / path).read_bytes()
        except OSError as error:
            raise LawError(
                f"Amendment-20 R06 file is missing: {path}"
            ) from error
        head_raw = _git("show", f"HEAD:{path}")
        tree_line = str(_git("ls-tree", "HEAD", "--", path, text=True)).strip()
        _require(
            isinstance(head_raw, bytes)
            and worktree_raw == head_raw
            and tree_line == f"{row['mode']} blob {row['git_blob']}\t{path}"
            and len(worktree_raw) == row["byte_size"]
            and _sha256(worktree_raw) == row["raw_sha256"]
            and _git_blob_oid(worktree_raw) == row["git_blob"],
            f"Amendment-20 R06 pinned file identity drift: {path}",
        )

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "PYTEST_ADDOPTS"
    }
    environment["PYTHONPATH"] = "src:."
    command = [
        sys.executable,
        *A20_R06_LIFECYCLE_CONTRACT["collection_command_after_interpreter"],
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    _require(
        result.returncode == 0,
        "Amendment-20 R06 exact collection command failed",
    )
    node_ids = [
        line
        for line in result.stdout.splitlines()
        if "::" in line
        and any(
            line.startswith(f"{row['path']}::")
            for row in A20_R06_FILE_IDENTITIES
        )
    ]
    raw = canonical_json_bytes(node_ids)
    _require(
        len(node_ids) == A20_R06_LIFECYCLE_CONTRACT["collected_node_id_count"]
        and len(raw)
        == A20_R06_LIFECYCLE_CONTRACT[
            "collected_node_id_array_canonical_byte_size"
        ]
        and _sha256(raw)
        == A20_R06_LIFECYCLE_CONTRACT["collected_node_id_array_raw_sha256"]
        and node_ids[0]
        == A20_R06_LIFECYCLE_CONTRACT["first_collected_node_id"]
        and node_ids[-1]
        == A20_R06_LIFECYCLE_CONTRACT["last_collected_node_id"],
        "Amendment-20 R06 collected-node identity drift",
    )
    return {
        "command": command,
        "environment": {"PYTHONPATH": "src:."},
        "file_identities": [dict(row) for row in A20_R06_FILE_IDENTITIES],
        "node_ids": node_ids,
        "node_id_array_canonical_byte_size": len(raw),
        "node_id_array_raw_sha256": _sha256(raw),
    }


def _validate_amendment20_scratch_transition_context(
    standin_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    """Authenticate the one Git/registry context in which stand-ins exist."""

    expected_paths = A20_RECEIPT_SCHEMA["expected_changed_paths"]
    verdict_paths = expected_paths[:2]
    _require(
        set(standin_bytes) == set(verdict_paths),
        "Amendment-20 scratch stand-in path domain drift",
    )
    scratch_commit = str(_git("rev-parse", "HEAD", text=True)).strip()
    detached = _run_git("symbolic-ref", "-q", "HEAD", text=True)
    containing_refs = str(
        _git(
            "for-each-ref",
            "--format=%(refname)",
            "--contains",
            scratch_commit,
            text=True,
        )
    ).splitlines()
    replace_refs = str(
        _git("for-each-ref", "--format=%(refname)", "refs/replace", text=True)
    ).splitlines()
    status_rows = str(_git("status", "--porcelain", text=True)).splitlines()
    _require(
        detached.returncode != 0
        and containing_refs == []
        and replace_refs == []
        and status_rows == [],
        "Amendment-20 scratch must be detached, unreachable, replace-free, and clean",
    )
    parent_line = str(
        _git("rev-list", "--parents", "-n", "1", scratch_commit, text=True)
    ).strip()
    parent_tokens = parent_line.split()
    _require(
        len(parent_tokens) == 2 and parent_tokens[0] == scratch_commit,
        "Amendment-20 scratch commit does not have one candidate parent",
    )
    candidate_commit = parent_tokens[1]
    candidate_parent_line = str(
        _git("rev-list", "--parents", "-n", "1", candidate_commit, text=True)
    ).strip()
    candidate_parent_tokens = candidate_parent_line.split()
    _require(
        len(candidate_parent_tokens) == 2
        and candidate_parent_tokens[0] == candidate_commit,
        "Amendment-20 candidate commit does not have one parent",
    )
    candidate_tree = str(
        _git("rev-parse", f"{candidate_commit}^{{tree}}", text=True)
    ).strip()
    scratch_tree = str(
        _git("rev-parse", f"{scratch_commit}^{{tree}}", text=True)
    ).strip()
    changed_paths = str(
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            scratch_commit,
            text=True,
        )
    ).splitlines()
    _require(
        len(changed_paths) == A20_RECEIPT_SCHEMA["changed_path_count"]
        and len(set(changed_paths)) == A20_RECEIPT_SCHEMA["changed_path_count"]
        and set(changed_paths) == set(expected_paths)
        and len(canonical_json_bytes(expected_paths))
        == A20_RECEIPT_SCHEMA[
            "expected_changed_path_domain_canonical_byte_size"
        ]
        and _sha256(canonical_json_bytes(expected_paths))
        == A20_RECEIPT_SCHEMA["expected_changed_path_domain_sha256"],
        "Amendment-20 scratch changed-path domain drift",
    )
    candidate_raw = _git("show", f"{candidate_commit}:{DESIGN_PATH}")
    _require(
        isinstance(candidate_raw, bytes),
        "Amendment-20 candidate design read was not raw bytes",
    )
    candidate_design_tree_line = str(
        _git(
            "ls-tree",
            candidate_commit,
            "--",
            DESIGN_PATH,
            text=True,
        )
    ).strip()
    _require(
        candidate_design_tree_line
        == (
            f"{DESIGN_MODE} blob {_git_blob_oid(candidate_raw)}\t"
            f"{DESIGN_PATH}"
        ),
        "Amendment-20 candidate design tree identity drift",
    )
    _validate_amendment20_ratification_design(candidate_raw)
    candidate_pins = _parse_amendment20_implementation_pins(candidate_raw)
    for row in candidate_pins["files"]:
        tree_line = str(
            _git("ls-tree", candidate_commit, "--", row["path"], text=True)
        ).strip()
        file_raw = _git("show", f"{candidate_commit}:{row['path']}")
        _require(
            tree_line
            == (
                f"{candidate_pins['mode']} blob {row['blob_oid']}\t"
                f"{row['path']}"
            )
            and isinstance(file_raw, bytes)
            and len(file_raw) == row["byte_size"]
            and _sha256(file_raw) == row["sha256"]
            and _git_blob_oid(file_raw) == row["blob_oid"],
            "Amendment-20 candidate implementation pin mismatch",
        )

    import covered_earnings_correction_registry as registry

    _require(
        getattr(registry, "SIMULATED_STATE_AUTHORITY", None) == "NONAUTHORITY"
        and getattr(registry, "SIMULATION_CONTEXT", None)
        == "amendment20_same_state_nonauthority_v1",
        "Amendment-20 scratch registry context is absent",
    )
    registry_binding = _validate_registry_ratification_context(
        registry.design_binding()
    )
    _require(
        registry_binding["revision"] == 22
        and _ratification_amendment_numbers(22)
        == (13, 14, 15, 16, 17, 18, 19, 20)
        and registry_binding["ratification_commit"] == candidate_commit
        and registry_binding["blob_sha256"] == _sha256(candidate_raw),
        "Amendment-20 scratch registry does not bind candidate revision 22",
    )
    closure_raw = _git("show", f"{scratch_commit}:{expected_paths[2]}")
    _require(
        isinstance(closure_raw, bytes),
        "Amendment-20 synthetic closure read was not raw bytes",
    )
    closure = _strict_canonical_json(
        closure_raw,
        "Amendment-20 synthetic scratch closure",
    )
    _validate_closure_shape(closure, 20)
    _require(
        closure["attested_candidate_design_byte_size"] == len(candidate_raw)
        and closure["attested_candidate_design_raw_sha256"]
        == _sha256(candidate_raw)
        and closure["attested_candidate_design_blob_oid"]
        == _git_blob_oid(candidate_raw)
        and closure["ratification_commit"] == candidate_commit
        and closure["operator_merge_commit"] == candidate_commit
        and closure["ratification_commit_sole_parent"]
        == candidate_parent_tokens[1]
        and [row["path"] for row in closure["verdict_artifacts"]]
        == verdict_paths,
        "Amendment-20 synthetic closure does not bind candidate and stand-ins",
    )
    for row in closure["verdict_artifacts"]:
        raw = standin_bytes[row["path"]]
        _require(
            len(raw) == row["byte_size"] and _sha256(raw) == row["raw_sha256"],
            "Amendment-20 synthetic closure stand-in identity mismatch",
        )
        _validate_amendment20_simulated_standin(
            raw,
            design_byte_size=len(candidate_raw),
            design_raw_sha256=_sha256(candidate_raw),
            design_blob_oid=_git_blob_oid(candidate_raw),
        )
    return {
        "candidate_commit_identity": {
            "commit": candidate_commit,
            "tree": candidate_tree,
            "sole_parent": candidate_parent_tokens[1],
        },
        "scratch_transition": {
            "commit": scratch_commit,
            "tree": scratch_tree,
            "sole_parent": candidate_commit,
            "changed_paths": list(expected_paths),
            "changed_path_domain_sha256": _sha256(
                canonical_json_bytes(expected_paths)
            ),
        },
        "changed_paths": list(expected_paths),
        "registry_binding": registry_binding,
        "closure": closure,
    }


def _amendment20_registry_behavior_ast(
    raw: bytes,
    label: str,
) -> tuple[str, Counter[str], set[str]]:
    """Normalize only the closed scratch-binding assignment statements."""

    binding_names = {
        "DESIGN_PATH",
        "DESIGN_RATIFICATION_COMMIT",
        "DESIGN_REVISION",
        "DESIGN_BYTE_SIZE",
        "DESIGN_BLOB_SHA256",
        "RATIFICATION_CLOSURE_BINDINGS",
        "SIMULATED_STATE_AUTHORITY",
        "SIMULATION_CONTEXT",
    }
    try:
        module = ast.parse(raw.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as error:
        raise LawError(f"{label} is not valid UTF-8 Python") from error
    removed_counts: Counter[str] = Counter()
    literal_names: set[str] = set()
    retained: list[ast.stmt] = []
    for node in module.body:
        name: str | None = None
        value_node: ast.expr | None = None
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            name = node.target.id
            value_node = node.value
        if name in binding_names:
            removed_counts[name] += 1
            if value_node is not None:
                try:
                    ast.literal_eval(value_node)
                except (ValueError, TypeError):
                    pass
                else:
                    literal_names.add(name)
        else:
            retained.append(node)
    module.body = retained

    def mutated_binding_names(target: ast.AST) -> set[str]:
        if isinstance(target, ast.Name):
            return {target.id} if target.id in binding_names else set()
        if isinstance(target, (ast.Attribute, ast.Subscript)):
            return mutated_binding_names(target.value)
        if isinstance(target, (ast.Tuple, ast.List)):
            return {
                name
                for element in target.elts
                for name in mutated_binding_names(element)
            }
        if isinstance(target, ast.Starred):
            return mutated_binding_names(target.value)
        return set()

    mutated_names = {
        name
        for node in ast.walk(module)
        if isinstance(getattr(node, "ctx", None), (ast.Store, ast.Del))
        for name in mutated_binding_names(node)
    }
    _require(
        mutated_names == set(),
        f"{label} mutates a closed binding name outside its literal assignment",
    )
    return (
        ast.dump(module, include_attributes=False),
        removed_counts,
        literal_names,
    )


def _parse_amendment20_scratch_registry_binding(
    raw: bytes,
    *,
    candidate_raw: bytes,
) -> dict[str, Any]:
    """Extract the closed literal A20 scratch binding without executing it."""

    required_names = {
        "DESIGN_PATH",
        "DESIGN_RATIFICATION_COMMIT",
        "DESIGN_REVISION",
        "DESIGN_BYTE_SIZE",
        "DESIGN_BLOB_SHA256",
        "RATIFICATION_CLOSURE_BINDINGS",
        "SIMULATED_STATE_AUTHORITY",
        "SIMULATION_CONTEXT",
    }
    try:
        source = raw.decode("utf-8")
        module = ast.parse(source)
    except (UnicodeDecodeError, SyntaxError) as error:
        raise LawError(
            "Amendment-20 scratch registry source is not valid UTF-8 Python"
        ) from error
    assignments: dict[str, list[Any]] = {name: [] for name in required_names}
    for node in module.body:
        name: str | None = None
        value_node: ast.expr | None = None
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            name = node.target.id
            value_node = node.value
        if name not in required_names or value_node is None:
            continue
        try:
            assignments[name].append(ast.literal_eval(value_node))
        except (ValueError, TypeError) as error:
            raise LawError(
                f"Amendment-20 scratch registry {name} is not literal"
            ) from error
    _require(
        all(len(values) == 1 for values in assignments.values()),
        "Amendment-20 scratch registry literal assignment domain drift",
    )
    scratch_behavior, scratch_counts, scratch_literal_names = (
        _amendment20_registry_behavior_ast(
            raw,
            "Amendment-20 scratch registry source",
        )
    )
    candidate_behavior, candidate_counts, candidate_literal_names = (
        _amendment20_registry_behavior_ast(
            candidate_raw,
            "Amendment-20 candidate registry source",
        )
    )
    candidate_names = required_names - {
        "SIMULATED_STATE_AUTHORITY",
        "SIMULATION_CONTEXT",
    }
    _require(
        scratch_counts == Counter({name: 1 for name in required_names})
        and scratch_literal_names == required_names
        and candidate_counts == Counter({name: 1 for name in candidate_names})
        and candidate_literal_names == candidate_names
        and scratch_behavior == candidate_behavior,
        "Amendment-20 scratch registry behavior differs from candidate",
    )
    values = {name: rows[0] for name, rows in assignments.items()}
    closures = values["RATIFICATION_CLOSURE_BINDINGS"]
    _require(
        values["DESIGN_PATH"] == DESIGN_PATH
        and _is_lower_hex(values["DESIGN_RATIFICATION_COMMIT"], 40)
        and type(values["DESIGN_REVISION"]) is int
        and values["DESIGN_REVISION"] == 22
        and type(values["DESIGN_BYTE_SIZE"]) is int
        and values["DESIGN_BYTE_SIZE"] > 0
        and _is_lower_hex(values["DESIGN_BLOB_SHA256"], 64)
        and isinstance(closures, (list, tuple))
        and all(isinstance(row, Mapping) for row in closures)
        and values["SIMULATED_STATE_AUTHORITY"] == "NONAUTHORITY"
        and values["SIMULATION_CONTEXT"]
        == "amendment20_same_state_nonauthority_v1",
        "Amendment-20 scratch registry literal value drift",
    )
    return {
        "design_byte_size": values["DESIGN_BYTE_SIZE"],
        "binding": {
            "path": values["DESIGN_PATH"],
            "ratification_commit": values["DESIGN_RATIFICATION_COMMIT"],
            "revision": values["DESIGN_REVISION"],
            "blob_sha256": values["DESIGN_BLOB_SHA256"],
            "ratification_closures": [dict(row) for row in closures],
        },
        "simulated_state_authority": values["SIMULATED_STATE_AUTHORITY"],
        "simulation_context": values["SIMULATION_CONTEXT"],
    }


def _validate_amendment20_transition_receipt(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate receipt-v2 shape, results, and Git-derived identities."""

    schema = A20_RECEIPT_SCHEMA
    tracked_receipt_raw = _read_public_repository_file(
        A20_EXECUTED_TRANSITION_RECEIPT_PATH,
        "Amendment-20 executed-transition receipt",
        require_regular_mode=True,
    )
    _require(
        tracked_receipt_raw == canonical_json_bytes(receipt),
        "Amendment-20 receipt object differs from fixed tracked bytes",
    )
    _require_exact_keys(
        receipt,
        set(schema["top_level_keys"]),
        "Amendment-20 transition receipt",
    )
    manifest = receipt["simulated_state_manifest"]
    _require(
        isinstance(manifest, Mapping),
        "Amendment-20 receipt manifest is not an object",
    )
    _require_exact_keys(
        manifest,
        set(schema["manifest_keys"]),
        "Amendment-20 transition receipt manifest",
    )
    candidate = manifest["candidate_commit_identity"]
    scratch = manifest["scratch_transition"]
    _require(
        isinstance(candidate, Mapping) and isinstance(scratch, Mapping),
        "Amendment-20 receipt C/S identity is not an object",
    )
    _require_exact_keys(
        candidate,
        set(schema["candidate_commit_identity_keys"]),
        "Amendment-20 candidate commit identity",
    )
    _require_exact_keys(
        scratch,
        set(schema["scratch_transition_keys"]),
        "Amendment-20 scratch transition identity",
    )
    _require(
        manifest["schema_version"] == "executed_transition_state.v2"
        and manifest["simulated_state_authority"] == "NONAUTHORITY"
        and manifest["terminal_revision"] == 22
        and receipt["simulated_state_authority"] == "NONAUTHORITY"
        and receipt["terminal_revision"] == 22
        and all(
            _is_lower_hex(candidate[key], 40)
            for key in ("commit", "tree", "sole_parent")
        )
        and all(
            _is_lower_hex(scratch[key], 40)
            for key in ("commit", "tree", "sole_parent")
        )
        and scratch["sole_parent"] == candidate["commit"]
        and scratch["changed_paths"] == schema["expected_changed_paths"]
        and scratch["changed_path_domain_sha256"]
        == schema["expected_changed_path_domain_sha256"],
        "Amendment-20 receipt C/S topology or changed paths drift",
    )
    _require(
        receipt["simulated_state_identity_sha256"]
        == _sha256(canonical_json_bytes(manifest)),
        "Amendment-20 receipt state identity drift",
    )
    state_identity = receipt["simulated_state_identity_sha256"]
    candidate_parent = str(
        _git(
            "rev-list",
            "--parents",
            "-n",
            "1",
            candidate["commit"],
            text=True,
        )
    ).split()
    scratch_parent = str(
        _git(
            "rev-list",
            "--parents",
            "-n",
            "1",
            scratch["commit"],
            text=True,
        )
    ).split()
    resolved_candidate_tree = str(
        _git("rev-parse", f"{candidate['commit']}^{{tree}}", text=True)
    ).strip()
    resolved_scratch_tree = str(
        _git("rev-parse", f"{scratch['commit']}^{{tree}}", text=True)
    ).strip()
    resolved_paths = str(
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            scratch["commit"],
            text=True,
        )
    ).splitlines()
    containing_refs = str(
        _git(
            "for-each-ref",
            "--format=%(refname)",
            "--contains",
            scratch["commit"],
            text=True,
        )
    ).splitlines()
    replace_refs = str(
        _git(
            "for-each-ref",
            "--format=%(refname)",
            "refs/replace",
            text=True,
        )
    ).splitlines()
    _require(
        candidate_parent == [candidate["commit"], candidate["sole_parent"]]
        and scratch_parent == [scratch["commit"], candidate["commit"]]
        and resolved_candidate_tree == candidate["tree"]
        and resolved_scratch_tree == scratch["tree"]
        and len(resolved_paths) == schema["changed_path_count"]
        and len(set(resolved_paths)) == schema["changed_path_count"]
        and set(resolved_paths) == set(schema["expected_changed_paths"])
        and _sha256(canonical_json_bytes(schema["expected_changed_paths"]))
        == scratch["changed_path_domain_sha256"]
        and containing_refs == []
        and replace_refs == [],
        "Amendment-20 receipt Git-resolved C/S identity drift",
    )
    for commit in (candidate["commit"], scratch["commit"]):
        receipt_in_transition = _run_git(
            "cat-file",
            "-e",
            f"{commit}:{A20_EXECUTED_TRANSITION_RECEIPT_PATH}",
        )
        _require(
            receipt_in_transition.returncode != 0,
            "Amendment-20 external receipt is present inside C or S",
        )
    closure_path = _ratification_closure_path(20)
    receipt_first_adds = str(
        _git(
            "log",
            "--format=%H",
            "--diff-filter=A",
            "--",
            A20_EXECUTED_TRANSITION_RECEIPT_PATH,
            text=True,
        )
    ).splitlines()
    closure_first_adds = str(
        _git(
            "log",
            "--format=%H",
            "--diff-filter=A",
            "--",
            closure_path,
            text=True,
        )
    ).splitlines()
    _require(
        len(receipt_first_adds) == 1
        and len(closure_first_adds) == 1
        and _is_lower_hex(receipt_first_adds[0], 40)
        and _is_lower_hex(closure_first_adds[0], 40),
        "Amendment-20 receipt or closure first-add identity drift",
    )
    receipt_first_add = receipt_first_adds[0]
    closure_first_add = closure_first_adds[0]
    receipt_precedes_closure = _run_git(
        "merge-base",
        "--is-ancestor",
        receipt_first_add,
        closure_first_add,
    )
    scratch_precedes_head = _run_git(
        "merge-base",
        "--is-ancestor",
        scratch["commit"],
        "HEAD",
    )
    _require(
        receipt_precedes_closure.returncode == 0
        and scratch_precedes_head.returncode != 0,
        "Amendment-20 receipt chronology or scratch isolation drift",
    )
    registry_binding = _validate_registry_ratification_context(
        manifest["canonical_registry_binding"]
    )
    _require(
        registry_binding["revision"] == 22
        and registry_binding["ratification_commit"] == candidate["commit"],
        "Amendment-20 receipt registry candidate binding drift",
    )

    candidate_raw = _git("show", f"{candidate['commit']}:{DESIGN_PATH}")
    _require(
        isinstance(candidate_raw, bytes)
        and registry_binding["blob_sha256"] == _sha256(candidate_raw),
        "Amendment-20 receipt candidate design identity drift",
    )
    candidate_design_tree_line = str(
        _git(
            "ls-tree",
            candidate["commit"],
            "--",
            DESIGN_PATH,
            text=True,
        )
    ).strip()
    _require(
        candidate_design_tree_line
        == (
            f"{DESIGN_MODE} blob {_git_blob_oid(candidate_raw)}\t"
            f"{DESIGN_PATH}"
        ),
        "Amendment-20 receipt candidate design tree identity drift",
    )
    _validate_amendment20_ratification_design(candidate_raw)
    pins = _parse_amendment20_implementation_pins(candidate_raw)
    for row in pins["files"]:
        file_raw = _git("show", f"{candidate['commit']}:{row['path']}")
        tree_line = str(
            _git(
                "ls-tree",
                candidate["commit"],
                "--",
                row["path"],
                text=True,
            )
        ).strip()
        _require(
            isinstance(file_raw, bytes)
            and tree_line
            == f"{pins['mode']} blob {row['blob_oid']}\t{row['path']}"
            and len(file_raw) == row["byte_size"]
            and _sha256(file_raw) == row["sha256"]
            and _git_blob_oid(file_raw) == row["blob_oid"],
            "Amendment-20 receipt candidate implementation pin drift",
        )

    closure_identities = manifest["ordered_closure_identities"]
    _require(
        isinstance(closure_identities, list) and len(closure_identities) == 8,
        "Amendment-20 receipt ordered closure identity domain drift",
    )
    for amendment_number, row, binding in zip(
        range(13, 21),
        closure_identities,
        registry_binding["ratification_closures"],
        strict=True,
    ):
        _require(
            isinstance(row, Mapping),
            "Amendment-20 receipt closure identity is not an object",
        )
        _require_exact_keys(
            row,
            set(schema["closure_identity_keys"]),
            "Amendment-20 receipt closure identity",
        )
        expected_path = _ratification_closure_path(amendment_number)
        _require(
            row["path"] == expected_path
            and {
                "path": row["path"],
                "raw_byte_size": row["raw_byte_size"],
                "raw_sha256": row["raw_sha256"],
            }
            == binding
            and type(row["raw_byte_size"]) is int
            and row["raw_byte_size"] > 0
            and _is_lower_hex(row["raw_sha256"], 64)
            and _is_lower_hex(row["git_blob"], 40),
            "Amendment-20 receipt closure identity value drift",
        )
        closure_bytes = _git("show", f"{scratch['commit']}:{expected_path}")
        tree_line = str(
            _git(
                "ls-tree",
                scratch["commit"],
                "--",
                expected_path,
                text=True,
            )
        ).strip()
        _require(
            isinstance(closure_bytes, bytes)
            and len(closure_bytes) == row["raw_byte_size"]
            and _sha256(closure_bytes) == row["raw_sha256"]
            and _git_blob_oid(closure_bytes) == row["git_blob"]
            and tree_line
            == f"{DESIGN_MODE} blob {row['git_blob']}\t{expected_path}",
            "Amendment-20 receipt closure Git identity drift",
        )

    synthetic_closure_path = schema["expected_changed_paths"][2]
    synthetic_closure_raw = _git(
        "show", f"{scratch['commit']}:{synthetic_closure_path}"
    )
    _require(
        isinstance(synthetic_closure_raw, bytes),
        "Amendment-20 synthetic closure read was not raw bytes",
    )
    synthetic_closure = _strict_canonical_json(
        synthetic_closure_raw,
        "Amendment-20 receipt synthetic closure",
    )
    _validate_closure_shape(synthetic_closure, 20)
    standin_paths = schema["expected_changed_paths"][:2]
    _require(
        synthetic_closure["attested_candidate_design_blob_oid"]
        == _git_blob_oid(candidate_raw)
        and synthetic_closure["attested_candidate_design_byte_size"]
        == len(candidate_raw)
        and synthetic_closure["attested_candidate_design_raw_sha256"]
        == _sha256(candidate_raw)
        and synthetic_closure["ratification_commit"] == candidate["commit"]
        and synthetic_closure["operator_merge_commit"] == candidate["commit"]
        and synthetic_closure["ratification_commit_sole_parent"]
        == candidate["sole_parent"]
        and [row["path"] for row in synthetic_closure["verdict_artifacts"]]
        == standin_paths,
        "Amendment-20 receipt synthetic closure candidate binding drift",
    )
    for row in synthetic_closure["verdict_artifacts"]:
        path = row["path"]
        standin_raw = _git("show", f"{scratch['commit']}:{path}")
        tree_line = str(
            _git("ls-tree", scratch["commit"], "--", path, text=True)
        ).strip()
        _require(
            isinstance(standin_raw, bytes)
            and tree_line
            == f"{DESIGN_MODE} blob {_git_blob_oid(standin_raw)}\t{path}"
            and len(standin_raw) == row["byte_size"]
            and _sha256(standin_raw) == row["raw_sha256"],
            "Amendment-20 receipt synthetic stand-in identity drift",
        )
        _validate_amendment20_simulated_standin(
            standin_raw,
            design_byte_size=len(candidate_raw),
            design_raw_sha256=_sha256(candidate_raw),
            design_blob_oid=_git_blob_oid(candidate_raw),
        )

    scratch_registry_path = schema["expected_changed_paths"][3]
    candidate_registry_raw = _git(
        "show", f"{candidate['commit']}:{scratch_registry_path}"
    )
    scratch_registry_raw = _git(
        "show", f"{scratch['commit']}:{scratch_registry_path}"
    )
    candidate_registry_tree_line = str(
        _git(
            "ls-tree",
            candidate["commit"],
            "--",
            scratch_registry_path,
            text=True,
        )
    ).strip()
    scratch_registry_tree_line = str(
        _git(
            "ls-tree",
            scratch["commit"],
            "--",
            scratch_registry_path,
            text=True,
        )
    ).strip()
    _require(
        scratch_registry_path == A20_PRODUCTION_REGISTRY_IDENTITY["path"]
        and isinstance(candidate_registry_raw, bytes)
        and isinstance(scratch_registry_raw, bytes)
        and len(candidate_registry_raw)
        == A20_PRODUCTION_REGISTRY_IDENTITY["byte_size"]
        and _sha256(candidate_registry_raw)
        == A20_PRODUCTION_REGISTRY_IDENTITY["raw_sha256"]
        and _git_blob_oid(candidate_registry_raw)
        == A20_PRODUCTION_REGISTRY_IDENTITY["git_blob"]
        and candidate_registry_tree_line
        == (
            f"{A20_PRODUCTION_REGISTRY_IDENTITY['mode']} blob "
            f"{A20_PRODUCTION_REGISTRY_IDENTITY['git_blob']}\t"
            f"{scratch_registry_path}"
        )
        and scratch_registry_tree_line
        == (
            f"{DESIGN_MODE} blob {_git_blob_oid(scratch_registry_raw)}\t"
            f"{scratch_registry_path}"
        ),
        "Amendment-20 scratch registry tree identity drift",
    )
    scratch_registry = _parse_amendment20_scratch_registry_binding(
        scratch_registry_raw,
        candidate_raw=candidate_registry_raw,
    )
    _require(
        scratch_registry["binding"] == registry_binding
        and scratch_registry["binding"]["ratification_commit"]
        == candidate["commit"]
        and scratch_registry["design_byte_size"] == len(candidate_raw)
        and scratch_registry["binding"]["blob_sha256"]
        == _sha256(candidate_raw),
        "Amendment-20 scratch registry does not bind receipt candidate state",
    )

    test_identity = manifest["full_pinned_battery_test_identity"]
    _require(
        isinstance(test_identity, Mapping),
        "Amendment-20 receipt test identity is not an object",
    )
    _require_exact_keys(
        test_identity,
        set(schema["test_identity_keys"]),
        "Amendment-20 receipt test identity",
    )
    test_path = "tests/test_validate_amendment13_execution_law.py"
    test_pin = next(row for row in pins["files"] if row["path"] == test_path)
    expected_test_identity = {
        "path": test_path,
        "mode": pins["mode"],
        "git_blob": test_pin["blob_oid"],
        "raw_byte_size": test_pin["byte_size"],
        "raw_sha256": test_pin["sha256"],
    }
    _require(
        dict(test_identity) == expected_test_identity,
        "Amendment-20 receipt test identity differs from candidate pin",
    )

    public_oracle = receipt["public_oracle"]
    battery = receipt["full_pinned_battery"]
    _require(
        isinstance(public_oracle, Mapping) and isinstance(battery, Mapping),
        "Amendment-20 receipt executed result is not an object",
    )
    _require_exact_keys(
        public_oracle,
        set(schema["public_oracle_keys"]),
        "Amendment-20 receipt public oracle result",
    )
    _require_exact_keys(
        battery,
        set(schema["full_pinned_battery_keys"]),
        "Amendment-20 receipt full pinned battery result",
    )
    _require(
        public_oracle["entrypoint"] == "validate_ratification_operativity"
        and public_oracle["executed"] is True
        and type(public_oracle["exit_code"]) is int
        and public_oracle["exit_code"] == 0
        and public_oracle["operative_amendments"] == list(range(13, 21))
        and public_oracle["simulated_state_identity_sha256"] == state_identity,
        "Amendment-20 receipt public oracle result drift",
    )
    integer_fields = (
        "exit_code",
        "collected",
        "passed",
        "failed",
        "skipped",
        "deselected",
        "xfailed",
        "xpassed",
    )
    _require(
        battery["executed"] is True
        and all(type(battery[key]) is int for key in integer_fields)
        and battery["exit_code"] == 0
        and battery["test_path"] == test_path
        and battery["test_mode_blob_bytes_sha256"] == test_identity
        and battery["exact_command"] == A20_FULL_PINNED_BATTERY_COMMAND
        and battery["collected"] == A20_FULL_PINNED_BATTERY_COLLECTED
        and battery["passed"] == A20_FULL_PINNED_BATTERY_COLLECTED
        and all(
            battery[key] == 0
            for key in (
                "failed",
                "skipped",
                "deselected",
                "xfailed",
                "xpassed",
            )
        )
        and battery["simulated_state_identity_sha256"] == state_identity,
        "Amendment-20 receipt full pinned battery result drift",
    )
    return dict(receipt)


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


def _validate_inherited_amendment18_ratification_design(raw: bytes) -> None:
    """Preserve the revision-19 prefix and A18 semantics in every successor."""

    _require(
        len(raw) > REVISION19_BYTE_SIZE
        and _sha256(raw[:REVISION19_BYTE_SIZE]) == REVISION19_SHA256
        and _git_blob_oid(raw[:REVISION19_BYTE_SIZE]) == REVISION19_BLOB_OID
        and raw[REVISION19_BYTE_SIZE:].startswith(AMENDMENT18_BOUNDARY),
        "Amendment-18 ratification design lacks the immutable revision-19 "
        "prefix or Amendment-18 boundary",
    )
    projection = _parse_amendment18_projection(raw)
    expected = _canonical_amendment18_projection()
    expected["implementation_pins"] = projection["implementation_pins"]
    _require(
        projection == expected,
        "Amendment-18 ratification design semantic projection drift",
    )


def _validate_amendment18_ratification_design(raw: bytes) -> None:
    """Require an Amendment-18-terminal design with exact inherited law."""

    _require(
        _terminal_design_amendment(raw) == 18,
        "Amendment-18 ratification design is not terminal Amendment 18",
    )
    _validate_inherited_amendment18_ratification_design(raw)


def _validate_inherited_amendment19_ratification_design(raw: bytes) -> None:
    """Preserve the revision-20 prefix and A19 semantics in every successor."""

    _require(
        len(raw) > REVISION20_BYTE_SIZE
        and _sha256(raw[:REVISION20_BYTE_SIZE]) == REVISION20_SHA256
        and _git_blob_oid(raw[:REVISION20_BYTE_SIZE]) == REVISION20_BLOB_OID
        and raw[REVISION20_BYTE_SIZE:].startswith(AMENDMENT19_BOUNDARY),
        "Amendment-19 ratification design lacks the immutable revision-20 "
        "prefix or Amendment-19 boundary",
    )
    _validate_inherited_amendment18_ratification_design(raw)
    projection = _parse_amendment19_projection(raw)
    manifest = projection["normative_manifest"]
    _validate_a19_purpose_mapping_contract(
        manifest["purpose_mapping_contract"]
    )
    _validate_a19_semantic_binding_contract(
        manifest["semantic_binding_contract"]
    )
    _validate_a19_source_hierarchy_failure_contract(
        manifest["source_hierarchy_failure_contract"]
    )
    _validate_a19_hierarchy_construction_contract(
        manifest["hierarchy_construction_contract"]
    )
    _validate_a19_successor_and_activation_contract(
        manifest["successor_routing_contract"],
        manifest["activation_transition"],
        manifest["production_registry_boundary"],
    )
    _require(
        manifest["mutation_inventory"] == list(A19_EXPECTED_MUTATIONS)
        and len(canonical_json_bytes(manifest["mutation_inventory"]))
        == A19_MUTATION_DOMAIN_BYTE_SIZE
        and _sha256(canonical_json_bytes(manifest["mutation_inventory"]))
        == A19_MUTATION_DOMAIN_SHA256,
        "Amendment-19 mutation manifest drift",
    )
    expected = _canonical_amendment19_projection()
    expected["implementation_pins"] = projection["implementation_pins"]
    _require(
        projection == expected,
        "Amendment-19 ratification design semantic projection drift",
    )


def _validate_amendment19_ratification_design(raw: bytes) -> None:
    """Require an Amendment-19-terminal design with exact inherited law."""

    _require(
        _terminal_design_amendment(raw) == 19,
        "Amendment-19 ratification design is not terminal Amendment 19",
    )
    _validate_inherited_amendment19_ratification_design(raw)


def _validate_amendment20_draft_design(raw: bytes) -> None:
    """Accept the exact-prefix, fail-closed A20 drafting surface."""

    _require(
        _terminal_design_amendment(raw) == 20,
        "Amendment-20 draft design is not terminal Amendment 20",
    )
    section = _amendment20_text(raw)
    _validate_inherited_amendment19_ratification_design(raw)
    section_numbers = [
        int(match.group(1))
        for match in re.finditer(r"^### 34\.([0-9]+)\b", section, re.MULTILINE)
    ]
    _require(
        section_numbers == list(range(1, 14))
        and section.count(
            "`amendment20_evidence_freeze_status` is exactly\n"
            "`not_instantiated_a4_required_before_ratify`"
        )
        == 1
        and section.count("`amendment20_ratification_ready` is false") == 1,
        "Amendment-20 draft status or section structure drift",
    )
    final_manifest_marker = (
        "The exact Amendment-20 normative manifest is this one-line "
        "terminal-LF canonical JSON value:\n\n"
    )
    if final_manifest_marker in section:
        projection = _parse_amendment20_projection(raw)
        if A20_SECTION_SEMANTIC_SHA256 is not None:
            _require(
                projection["section_semantic_sha256"]
                == A20_SECTION_SEMANTIC_SHA256,
                "Amendment-20 draft semantic projection drift",
            )
    else:
        _require(
            section.count(
                "The exact Amendment-20 normative manifest will be inserted "
                "here as one-line\n"
            )
            == 1
            and section.count(
                "The exact A20 active three-path implementation pin table is "
                "deliberately\npending the final code/test freeze"
            )
            == 1,
            "Amendment-20 pending manifest or implementation-pin marker drift",
        )


def _validate_inherited_amendment20_ratification_design(raw: bytes) -> None:
    """Preserve exact revision-21 and ratification-ready A20 in successors."""

    _require(
        len(raw) > REVISION21_BYTE_SIZE
        and _sha256(raw[:REVISION21_BYTE_SIZE]) == REVISION21_SHA256
        and _git_blob_oid(raw[:REVISION21_BYTE_SIZE]) == REVISION21_BLOB_OID
        and raw[REVISION21_BYTE_SIZE:].startswith(AMENDMENT20_BOUNDARY),
        "Amendment-20 ratification design lacks the immutable revision-21 "
        "prefix or Amendment-20 boundary",
    )
    _validate_inherited_amendment19_ratification_design(raw)
    projection = _parse_amendment20_projection(raw)
    _validate_a20_manifest_contract(
        projection["normative_manifest"],
        require_ratification_ready=True,
    )
    _require(
        isinstance(A20_SECTION_SEMANTIC_SHA256, str)
        and projection["section_semantic_sha256"]
        == A20_SECTION_SEMANTIC_SHA256,
        "Amendment-20 ratification design semantic projection drift",
    )


def _validate_amendment20_ratification_design(raw: bytes) -> None:
    """Require terminal A20 and reject the current evidence-incomplete draft."""

    _require(
        _terminal_design_amendment(raw) == 20,
        "Amendment-20 ratification design is not terminal Amendment 20",
    )
    _validate_inherited_amendment20_ratification_design(raw)


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
    elif amendment_number == 18:
        _validate_amendment18_ratification_design(raw)
    elif amendment_number == 19:
        _validate_amendment19_ratification_design(raw)
    elif amendment_number == 20:
        _validate_amendment20_ratification_design(raw)
    elif amendment_number > 20:
        _validate_inherited_amendment20_ratification_design(raw)


def _validate_ratification_closure(
    closure_raw: bytes | None,
    closure_binding: Mapping[str, Any],
    verdict_bytes: Mapping[str, bytes],
    amendment_number: int,
    *,
    verify_git: bool,
    ratification_design_raw: bytes | None = None,
    registry_design_binding: Mapping[str, Any] | None = None,
    amendment20_transition_receipt_raw: bytes | None = None,
) -> dict[str, Any]:
    """Validate registry-selected closure bytes and their exact artifacts."""

    _require(
        amendment_number <= 20,
        "post-Amendment-20 receipt topology requires exact successor law",
    )

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
    is_terminal_closure = False
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
        is_terminal_closure = amendment_number == amendment_numbers[-1]
        if (
            amendment_number == 14
            and registry_design_binding["revision"]
            >= COMBINED_ACTIVATION_REVISION
        ):
            _require(
                dict(closure_binding) == A14_HISTORICAL_CLOSURE_BINDING,
                "Amendment-14 historical closure binding drift",
            )
        if is_terminal_closure:
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
    amendment20_attestations: list[dict[str, Any]] = []
    receipt_byte_size: int | None = None
    receipt_raw_sha256: str | None = None
    if amendment_number > 20:
        raise LawError(
            "post-Amendment-20 receipt topology requires exact successor law"
        )
    if amendment_number == 20:
        _require(
            isinstance(amendment20_transition_receipt_raw, bytes),
            "Amendment-20 external transition receipt is missing",
        )
        receipt = _strict_canonical_json(
            amendment20_transition_receipt_raw,
            A20_EXECUTED_TRANSITION_RECEIPT_PATH,
        )
        _validate_amendment20_transition_receipt(receipt)
        _require(
            isinstance(registry_design_binding, Mapping),
            "Amendment-20 closure lacks registry candidate cross-binding",
        )
        receipt_candidate_commit = receipt["simulated_state_manifest"][
            "candidate_commit_identity"
        ]["commit"]
        receipt_candidate_raw = _git(
            "show",
            f"{receipt_candidate_commit}:{DESIGN_PATH}",
        )
        _require(
            isinstance(receipt_candidate_raw, bytes)
            and len(receipt_candidate_raw)
            == closure["attested_candidate_design_byte_size"]
            and _sha256(receipt_candidate_raw)
            == closure["attested_candidate_design_raw_sha256"]
            and _git_blob_oid(receipt_candidate_raw)
            == closure["attested_candidate_design_blob_oid"]
            and (
                not is_terminal_closure
                or registry_design_binding["blob_sha256"]
                == _sha256(receipt_candidate_raw)
            ),
            "Amendment-20 receipt/closure/registry candidate cross-binding drift",
        )
        receipt_byte_size = len(amendment20_transition_receipt_raw)
        receipt_raw_sha256 = _sha256(amendment20_transition_receipt_raw)
    else:
        _require(
            amendment20_transition_receipt_raw is None,
            "pre-Amendment-20 closure received an inapplicable receipt",
        )
    for row in verdicts:
        raw = verdict_bytes[row["path"]]
        _require(
            isinstance(raw, bytes)
            and len(raw) == row["byte_size"]
            and _sha256(raw) == row["raw_sha256"],
            "ratification closure verdict byte mismatch",
        )
        if amendment_number >= 20:
            amendment20_attestations.append(
                validate_amendment20_qualifying_verdict(
                    raw,
                    design_byte_size=closure[
                        "attested_candidate_design_byte_size"
                    ],
                    design_raw_sha256=closure[
                        "attested_candidate_design_raw_sha256"
                    ],
                    design_blob_oid=closure[
                        "attested_candidate_design_blob_oid"
                    ],
                    receipt_byte_size=receipt_byte_size,
                    receipt_raw_sha256=receipt_raw_sha256,
                )
            )
        else:
            _verdict_attests_design(raw, closure)
    if amendment_number >= 20:
        _require(
            len(amendment20_attestations) == 2
            and amendment20_attestations[0] == amendment20_attestations[1],
            "Amendment-20 verdicts do not attest one candidate and receipt",
        )

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
        _require(
            normalized["ratification_closures"][2]
            == A15_HISTORICAL_CLOSURE_BINDING,
            "Amendment-15 historical R05 closure binding drift",
        )
    return normalized


def _interregnum_amendment20_design_binding() -> dict[str, Any]:
    """Resolve the registry identity across the Amendment-20 interregnum.

    The production registry stays fail-closed: ``design_binding`` still
    rejects every unratified Amendment-20 suffix and this resolver
    never widens that gate or registers anything. Between the
    Amendment-20 draft merge and the revision-22 repin the repository
    lawfully holds exactly one tree state the registry cannot
    register: the pinned revision-21 prefix plus one lawful
    Amendment-20 suffix. This resolver accepts that single state
    byte-exactly (worktree equal to ``HEAD`` plus the complete
    immutable-prefix authentication of ``_amendment20_text``) and
    answers with the registry's own revision-21 identity so A13-era
    consumers keep validating against ratified law. Any other
    deviation re-raises the registration abort unchanged, and the
    revision-22 repin disarms this branch permanently because the
    registry pins stop matching the revision-21 constants.
    """

    import covered_earnings_correction_registry as registry

    try:
        return registry.design_binding()
    except registry.RegistrationAborted:
        if not (
            registry.DESIGN_REVISION == 21
            and registry.DESIGN_PATH == DESIGN_PATH
            and registry.DESIGN_BYTE_SIZE == REVISION21_BYTE_SIZE
            and registry.DESIGN_BLOB_SHA256 == REVISION21_SHA256
        ):
            raise
        worktree_raw = (ROOT / DESIGN_PATH).read_bytes()
        head = registry._run_git("show", f"HEAD:{DESIGN_PATH}")
        if head.returncode != 0 or worktree_raw != head.stdout:
            raise
        _amendment20_text(worktree_raw)
        return {
            "path": registry.DESIGN_PATH,
            "ratification_commit": registry.DESIGN_RATIFICATION_COMMIT,
            "revision": registry.DESIGN_REVISION,
            "blob_sha256": registry.DESIGN_BLOB_SHA256,
            "ratification_closures": [
                dict(binding)
                for binding in registry.RATIFICATION_CLOSURE_BINDINGS
            ],
        }


def _public_registry_ratification_context() -> dict[str, Any]:
    """Load the current terminal registry-selected closure context."""

    try:
        design_binding = _interregnum_amendment20_design_binding()
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
    _require(
        amendment_number <= 20,
        "post-Amendment-20 receipt topology requires exact successor law",
    )
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
    if amendment_number == 20 and any(
        b"executed_transition_receipt_status:" in raw
        or b"simulation_context:" in raw
        for raw in verdict_bytes.values()
    ):
        scratch = _validate_amendment20_scratch_transition_context(
            verdict_bytes
        )
        _require(
            scratch["registry_binding"] == context
            and scratch["closure"] == closure,
            "Amendment-20 scratch public closure context drift",
        )
        return closure

    if amendment_number == 20:
        import covered_earnings_correction_registry as registry

        _require(
            not hasattr(registry, "SIMULATED_STATE_AUTHORITY")
            and not hasattr(registry, "SIMULATION_CONTEXT"),
            "Amendment-20 scratch constants are forbidden with real verdicts",
        )
        receipt_raw = _read_public_repository_file(
            A20_EXECUTED_TRANSITION_RECEIPT_PATH,
            "executed-transition receipt",
            require_regular_mode=True,
        )
    else:
        receipt_raw = None
    return _validate_ratification_closure(
        worktree_raw,
        binding,
        verdict_bytes,
        amendment_number,
        verify_git=True,
        registry_design_binding=context if amendment_number != 13 else None,
        amendment20_transition_receipt_raw=receipt_raw,
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
    design_raw = (ROOT / DESIGN_PATH).read_bytes()
    terminal_amendment = _terminal_design_amendment(design_raw)
    if terminal_amendment == context["revision"] - 1:
        _require(
            context["revision"] == 21
            and len(design_raw) > REVISION21_BYTE_SIZE,
            "ordinary registry/design terminal amendment mismatch",
        )
        _amendment20_text(design_raw)
    else:
        _require(
            terminal_amendment == context["revision"] - 2,
            "ordinary registry/design terminal amendment mismatch",
        )
    _verify_implementation_pins(_parse_active_implementation_pins(design_raw))
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
    result = {
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
    if revision >= COMBINED_ACTIVATION_REVISION:
        result["ratification_closures"][1] = copy.deepcopy(
            A14_HISTORICAL_CLOSURE_BINDING
        )
        result["ratification_closures"][2] = copy.deepcopy(
            A15_HISTORICAL_CLOSURE_BINDING
        )
    return result


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
    if revision >= COMBINED_ACTIVATION_REVISION and 15 in amendment_numbers:
        position = tuple(amendment_numbers).index(15)
        context["ratification_closures"][position] = copy.deepcopy(
            A15_HISTORICAL_CLOSURE_BINDING
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


def run_amendment18_contract_mutation_tests() -> tuple[str, ...]:
    """Execute inherited censuses, then the three grouped A18 attacks."""

    import build_amendment13_tier2_repairs as publisher

    inherited = publisher.run_complete_mutation_census()
    _require(
        inherited == publisher._expected_mutation_census()
        and inherited["rejected_count"]
        == A18_MUTATION_CENSUS["inherited_complete_mutation_count"]
        and inherited["rejected_domain_sha256"]
        == A18_MUTATION_CENSUS["inherited_complete_mutation_domain_sha256"],
        "Amendment-18 inherited complete mutation census drift",
    )
    amendment16 = _run_amendment16_oracle_attacks()
    _require(
        amendment16 == A16_EXPECTED_MUTATIONS
        and _sha256(canonical_json_bytes(list(amendment16)))
        == A18_MUTATION_CENSUS["amendment16_mutation_domain_sha256"],
        "Amendment-18 inherited Amendment-16 mutation census drift",
    )

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment["PYTHONPATH"] = "src:."
    amendment17_node = (
        "tests/test_validate_amendment13_execution_law.py::"
        "test__closure__revision17_standalone_activation_is_forbidden"
    )
    amendment17_result = subprocess.run(
        [
            A18_R06_RESULT_CONTRACT["process_command"][0],
            "-I",
            "-B",
            "-m",
            "pytest",
            "-q",
            amendment17_node,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    _require(
        amendment17_result.returncode == 0
        and re.search(r"(?:^|\s)1 passed(?:\s|$)", amendment17_result.stdout)
        is not None
        and all(
            marker not in amendment17_result.stdout
            for marker in (
                " failed",
                " skipped",
                " deselected",
                " xfailed",
                " xpassed",
            )
        )
        and len(A17_EXPECTED_MUTATIONS)
        == A18_MUTATION_CENSUS["amendment17_mutation_count"]
        and _sha256(canonical_json_bytes(list(A17_EXPECTED_MUTATIONS)))
        == A18_MUTATION_CENSUS["amendment17_mutation_domain_sha256"],
        "Amendment-18 inherited Amendment-17 mutation census drift",
    )

    def same_json_types(candidate: Any, expected: Any) -> bool:
        if type(candidate) is not type(expected):
            return False
        if isinstance(expected, Mapping):
            return set(candidate) == set(expected) and all(
                same_json_types(candidate[key], expected[key])
                for key in expected
            )
        if isinstance(expected, list):
            return len(candidate) == len(expected) and all(
                same_json_types(left, right)
                for left, right in zip(candidate, expected, strict=True)
            )
        return True

    def validate_exact_contract(
        raw: bytes,
        expected: Mapping[str, Any],
        message: str,
    ) -> dict[str, Any]:
        try:
            candidate = _strict_canonical_json(raw, message)
            _require(
                candidate == expected and same_json_types(candidate, expected),
                message,
            )
        except LawError as error:
            raise LawError(message) from error
        return candidate

    def reject_contract_variants(
        expected: Mapping[str, Any],
        variants: Sequence[Mapping[str, Any] | bytes],
        message: str,
        label: str,
    ) -> None:
        validate_exact_contract(
            canonical_json_bytes(expected), expected, message
        )
        for position, variant in enumerate(variants):
            raw = (
                variant
                if isinstance(variant, bytes)
                else canonical_json_bytes(variant)
            )
            _expect_law_error(
                lambda raw=raw: validate_exact_contract(
                    raw, expected, message
                ),
                message,
                f"{label} variant {position}",
            )

    def canonical_repository_path(path: Any) -> bool:
        if not isinstance(path, str) or not path:
            return False
        candidate = Path(path)
        return (
            not candidate.is_absolute()
            and candidate.as_posix() == path
            and all(part not in {"", ".", ".."} for part in candidate.parts)
        )

    def load_source_root(
        path: str,
        label: str,
        *,
        expected_blob: str,
        expected_byte_size: int,
        expected_sha256: str,
    ) -> Mapping[str, Any]:
        raw = _read_public_repository_file(
            path,
            label,
            require_regular_mode=True,
        )
        _require(
            len(raw) == expected_byte_size
            and _sha256(raw) == expected_sha256
            and _git_blob_oid(raw) == expected_blob,
            f"{label} enacted byte identity drift",
        )
        try:
            value = a12.strict_json_loads(raw, path)
        except a12.BuildError as error:
            raise LawError(f"{label} is invalid strict JSON") from error
        _require(isinstance(value, Mapping), f"{label} is not an object")
        return value

    def source_document_row(
        *,
        document_role: str,
        interview_wave: int,
        canonical_source_path: str,
        storage_authority: str,
        storage_document_id: str,
        byte_size: int,
        sha256: str,
    ) -> dict[str, Any]:
        _require(
            type(interview_wave) is int
            and canonical_repository_path(canonical_source_path)
            and isinstance(storage_document_id, str)
            and bool(storage_document_id)
            and type(byte_size) is int
            and byte_size > 0
            and _is_lower_hex(sha256, 64),
            "Amendment-18 reconstructed source row is malformed",
        )
        identity_preimage = [
            document_role,
            [interview_wave],
            canonical_source_path,
            byte_size,
            sha256,
        ]
        return {
            "source_document_id": (
                "psid-source-document:"
                + _sha256(canonical_json_bytes(identity_preimage))
            ),
            "document_role": document_role,
            "interview_waves": [interview_wave],
            "canonical_source_path": canonical_source_path,
            "storage_disposition": "external_registered_file",
            "storage_identity": {
                "authority_registry_id": storage_authority,
                "document_id": storage_document_id,
                "registered_path": canonical_source_path,
            },
            "byte_size": byte_size,
            "sha256": sha256,
        }

    def reconstruct_source_rows() -> list[dict[str, Any]]:
        questionnaire_root = load_source_root(
            "data/external/"
            "psid_questionnaire_corpus_authority_registration_attempt_v1.json",
            "Amendment-18 questionnaire source root",
            expected_blob="825f6c61ef9d4a161886cbc44f5cc914d65160d2",
            expected_byte_size=520_656,
            expected_sha256=(
                "07c5bad57d702416da7ee668f504646ba85b9868a7f38819cdec85638c97558c"
            ),
        )
        field_root = load_source_root(
            "data/external/"
            "psid_questionnaire_dictionary_inventory_registration_required_v1.json",
            "Amendment-18 field source root",
            expected_blob="a2e6bfa8b19c35dfde235d8ece7e233a5d833e9e",
            expected_byte_size=25_474_435,
            expected_sha256=(
                "a974c6fb65a9f3d52387163f2e98b7cd8cfdbd57f5e95d1f766b3aa25d167ac0"
            ),
        )
        waves = field_root.get("interview_waves")
        questionnaire_candidates = questionnaire_root.get(
            "document_candidates"
        )
        field_manifest = field_root.get("source_authority_manifest")
        _require(
            questionnaire_root.get("schema_version")
            == (
                "psid_questionnaire_corpus_authority_registration_"
                "attempt.v1"
            )
            and questionnaire_root.get("registration_status") == "pass"
            and isinstance(questionnaire_candidates, list)
            and len(questionnaire_candidates) == 456
            and isinstance(waves, list)
            and len(waves) == 43
            and all(type(wave) is int for wave in waves)
            and len(set(waves)) == len(waves)
            and isinstance(field_manifest, list)
            and len(field_manifest) == 176,
            "Amendment-18 source-root denominator drift",
        )
        rows: list[dict[str, Any]] = []
        for wave in waves:
            core_basename = (
                f"q{wave % 100:02d}.pdf"
                if wave <= 1997
                else f"q{wave:04d}.pdf"
            )
            source_specs = (
                (
                    "https://psidonline.isr.umich.edu/documents/psid/"
                    f"questionnaires/{core_basename}",
                    "Questionnaire",
                    False,
                ),
                (
                    "https://psidonline.isr.umich.edu/data/Documentation/"
                    f"Fam/{wave}/QxQs.pdf",
                    "QxQ",
                    True,
                ),
            )
            for source_url, link_text, optional in source_specs:
                matches = [
                    row
                    for row in questionnaire_candidates
                    if isinstance(row, Mapping)
                    and row.get("source_url") == source_url
                ]
                if optional and not matches:
                    continue
                _require(
                    len(matches) == 1,
                    "Amendment-18 questionnaire source selection drift",
                )
                source = matches[0]
                observed = source.get("observed_identity")
                locator = source.get("locator")
                _require(
                    isinstance(observed, Mapping)
                    and isinstance(locator, Mapping)
                    and source.get("availability") == "verified"
                    and source.get("source_link_text") == link_text
                    and source.get("digest_row_filename")
                    == source.get("on_disk_filename")
                    == observed.get("filename")
                    == locator.get("filename")
                    and type(source.get("expected_size_bytes")) is int
                    and source["expected_size_bytes"]
                    == observed.get("size_bytes")
                    == locator.get("size_bytes")
                    and _is_lower_hex(source.get("expected_sha256"), 64)
                    and source["expected_sha256"]
                    == observed.get("sha256")
                    == locator.get("full_file_sha256")
                    == locator.get("range_sha256"),
                    "Amendment-18 questionnaire source identity drift",
                )
                canonical_source_path = (
                    "documentation/capture1/" + source["on_disk_filename"]
                )
                rows.append(
                    source_document_row(
                        document_role="questionnaire_flow",
                        interview_wave=wave,
                        canonical_source_path=canonical_source_path,
                        storage_authority=(
                            "psid_questionnaire_corpus_authority_registry.v1"
                        ),
                        storage_document_id=source["source_document_id"],
                        byte_size=source["expected_size_bytes"],
                        sha256=source["expected_sha256"],
                    )
                )

        role_by_source_role = {
            "stata_setup": "dictionary_layout",
            "spss_setup": "dictionary_layout",
            "family_codebook": "codebook",
            "stata_value_labels": "codebook",
            "spss_value_labels": "codebook",
            "raw_fixed_width": "raw_fixed_width_data",
        }
        for source in field_manifest:
            _require(
                isinstance(source, Mapping)
                and {
                    "dictionary_role",
                    "document_id",
                    "encoding",
                    "interview_wave",
                    "path",
                    "sha256",
                    "size_bytes",
                }
                <= set(source)
                and source.get("dictionary_role") in role_by_source_role
                and source.get("interview_wave") in waves,
                "Amendment-18 field source manifest drift",
            )
            rows.append(
                source_document_row(
                    document_role=role_by_source_role[
                        source["dictionary_role"]
                    ],
                    interview_wave=source["interview_wave"],
                    canonical_source_path=source["path"],
                    storage_authority=(
                        "psid_questionnaire_dictionary_inventory."
                        "registration_required.v1"
                    ),
                    storage_document_id=source["document_id"],
                    byte_size=source["size_bytes"],
                    sha256=source["sha256"],
                )
            )

        role_order = {
            "questionnaire_flow": 0,
            "dictionary_layout": 1,
            "codebook": 2,
            "raw_fixed_width_data": 3,
        }
        wave_order = {wave: position for position, wave in enumerate(waves)}
        rows.sort(
            key=lambda row: (
                role_order[row["document_role"]],
                wave_order[row["interview_waves"][0]],
                row["canonical_source_path"].encode("utf-8"),
                row["source_document_id"],
            )
        )
        questionnaire_rows = [
            row
            for row in rows
            if row["document_role"]
            == A18_BUILD_INPUT_DOMAIN_CONTRACT["questionnaire_slice_role"]
        ]
        _require(
            len(rows)
            == A18_BUILD_INPUT_DOMAIN_CONTRACT["source_document_count"]
            and len(questionnaire_rows)
            == A18_BUILD_INPUT_DOMAIN_CONTRACT["questionnaire_document_count"]
            and _sha256(
                canonical_json_bytes(
                    [row["source_document_id"] for row in questionnaire_rows]
                )
            )
            == A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "questionnaire_document_keyset_sha256"
            ]
            and _sha256(canonical_json_bytes(questionnaire_rows))
            == A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "questionnaire_document_domain_sha256"
            ]
            and _sha256(
                canonical_json_bytes(
                    [row["source_document_id"] for row in rows]
                )
            )
            == A18_BUILD_INPUT_DOMAIN_CONTRACT["source_document_keyset_sha256"]
            and _sha256(canonical_json_bytes(rows))
            == A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "source_document_domain_sha256"
            ],
            "Amendment-18 independently reconstructed source domain drift",
        )
        return rows

    def reconstruct_repair_identities() -> list[dict[str, Any]]:
        tier2_root = "docs/analysis/amendment_12_rq_catalog_tier2"
        overlay_positions = (
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
        )
        paths = sorted(
            [
                f"{tier2_root}/fix5_rederivation_confirmation_v1.json",
                *(
                    f"{tier2_root}/amendment_13_repair_overlays_v1/"
                    f"document_{position:03d}_repair_overlay_v1.json"
                    for position in overlay_positions
                ),
                *(
                    f"{tier2_root}/amendment_13_successor_era_seals_v1/"
                    f"era_{position:02d}_successor_seal_v1.json"
                    for position in range(1, 7)
                ),
                f"{tier2_root}/targeted_sweeps/"
                "admission_rule_targeted_sweeps_v1.json",
            ],
            key=lambda path: path.encode("utf-8"),
        )
        _require(
            len(paths)
            == A18_BUILD_INPUT_DOMAIN_CONTRACT["repair_seal_evidence_count"]
            and _sha256(canonical_json_bytes(paths))
            == A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "repair_seal_evidence_path_domain_sha256"
            ],
            "Amendment-18 repair/seal path domain drift",
        )
        identities: list[dict[str, Any]] = []
        for path in paths:
            _require(
                canonical_repository_path(path),
                "Amendment-18 repair/seal path is noncanonical",
            )
            raw = _read_public_repository_file(
                path,
                "Amendment-18 repair/seal evidence",
                require_regular_mode=True,
            )
            identities.append(
                {
                    "path": path,
                    "mode": DESIGN_MODE,
                    "git_blob": _git_blob_oid(raw),
                    "byte_size": len(raw),
                    "raw_sha256": _sha256(raw),
                }
            )
        return identities

    expected_source_rows = reconstruct_source_rows()
    expected_repair_identities = reconstruct_repair_identities()

    def build_input_envelope() -> dict[str, Any]:
        return {
            "schema_version": A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "schema_version"
            ],
            "canonicalization": A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "canonicalization"
            ],
            "questionnaire_document_count": A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "questionnaire_document_count"
            ],
            "questionnaire_document_keyset_sha256": (
                A18_BUILD_INPUT_DOMAIN_CONTRACT[
                    "questionnaire_document_keyset_sha256"
                ]
            ),
            "questionnaire_document_domain_sha256": (
                A18_BUILD_INPUT_DOMAIN_CONTRACT[
                    "questionnaire_document_domain_sha256"
                ]
            ),
            "source_document_count": A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "source_document_count"
            ],
            "source_document_keyset_sha256": A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "source_document_keyset_sha256"
            ],
            "source_document_domain_sha256": A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "source_document_domain_sha256"
            ],
            "repair_seal_evidence_count": A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "repair_seal_evidence_count"
            ],
            "repair_seal_evidence_path_domain_sha256": (
                A18_BUILD_INPUT_DOMAIN_CONTRACT[
                    "repair_seal_evidence_path_domain_sha256"
                ]
            ),
            "row_count": A18_BUILD_INPUT_DOMAIN_CONTRACT["row_count"],
            "rows": [
                *(
                    {
                        "input_class": "source_document",
                        "input_identity": copy.deepcopy(identity),
                    }
                    for identity in expected_source_rows
                ),
                *(
                    {
                        "input_class": "repair_seal_evidence",
                        "input_identity": copy.deepcopy(identity),
                    }
                    for identity in expected_repair_identities
                ),
            ],
        }

    def validate_build_input_envelope(raw: bytes) -> str:
        try:
            candidate = _strict_canonical_json(
                raw,
                "Amendment-18 build-input-domain envelope",
            )
            _require_exact_keys(
                candidate,
                set(A18_BUILD_INPUT_DOMAIN_CONTRACT["envelope_keys"]),
                "Amendment-18 build-input-domain envelope",
            )
            for field in (
                "questionnaire_document_count",
                "source_document_count",
                "repair_seal_evidence_count",
                "row_count",
            ):
                _require(
                    type(candidate[field]) is int
                    and candidate[field]
                    == A18_BUILD_INPUT_DOMAIN_CONTRACT[field],
                    "Amendment-18 build-input-domain integer drift",
                )
            for field in (
                "schema_version",
                "canonicalization",
                "questionnaire_document_keyset_sha256",
                "questionnaire_document_domain_sha256",
                "source_document_keyset_sha256",
                "source_document_domain_sha256",
                "repair_seal_evidence_path_domain_sha256",
            ):
                _require(
                    candidate[field] == A18_BUILD_INPUT_DOMAIN_CONTRACT[field],
                    "Amendment-18 build-input-domain comparand drift",
                )
            rows = candidate["rows"]
            _require(
                isinstance(rows, list)
                and len(rows) == A18_BUILD_INPUT_DOMAIN_CONTRACT["row_count"],
                "Amendment-18 build-input-domain row count drift",
            )
            source_count = A18_BUILD_INPUT_DOMAIN_CONTRACT[
                "source_document_count"
            ]
            source_rows = rows[:source_count]
            repair_rows = rows[source_count:]
            for position, (row, expected_identity) in enumerate(
                zip(source_rows, expected_source_rows, strict=True)
            ):
                _require(
                    isinstance(row, Mapping),
                    "Amendment-18 source input row is not an object",
                )
                _require_exact_keys(
                    row,
                    set(A18_BUILD_INPUT_DOMAIN_CONTRACT["row_keys"]),
                    "Amendment-18 source input row",
                )
                identity = row["input_identity"]
                _require(
                    row["input_class"] == "source_document"
                    and isinstance(identity, Mapping),
                    "Amendment-18 source input class drift",
                )
                _require_exact_keys(
                    identity,
                    set(
                        A18_BUILD_INPUT_DOMAIN_CONTRACT["source_identity_keys"]
                    ),
                    "Amendment-18 source input identity",
                )
                _require(
                    type(identity["byte_size"]) is int
                    and identity["byte_size"] > 0
                    and _is_lower_hex(identity["sha256"], 64)
                    and identity["source_document_id"]
                    == (
                        "psid-source-document:"
                        + _sha256(
                            canonical_json_bytes(
                                [
                                    identity["document_role"],
                                    identity["interview_waves"],
                                    identity["canonical_source_path"],
                                    identity["byte_size"],
                                    identity["sha256"],
                                ]
                            )
                        )
                    )
                    and canonical_repository_path(
                        identity["canonical_source_path"]
                    )
                    and dict(identity) == expected_identity,
                    f"Amendment-18 source input identity drift at {position}",
                )
            for position, (row, expected_identity) in enumerate(
                zip(
                    repair_rows,
                    expected_repair_identities,
                    strict=True,
                ),
                start=source_count,
            ):
                _require(
                    isinstance(row, Mapping),
                    "Amendment-18 repair input row is not an object",
                )
                _require_exact_keys(
                    row,
                    set(A18_BUILD_INPUT_DOMAIN_CONTRACT["row_keys"]),
                    "Amendment-18 repair input row",
                )
                identity = row["input_identity"]
                _require(
                    row["input_class"] == "repair_seal_evidence"
                    and isinstance(identity, Mapping),
                    "Amendment-18 repair input class drift",
                )
                _require_exact_keys(
                    identity,
                    set(
                        A18_BUILD_INPUT_DOMAIN_CONTRACT["repair_identity_keys"]
                    ),
                    "Amendment-18 repair input identity",
                )
                _require(
                    canonical_repository_path(identity["path"])
                    and identity["mode"] == DESIGN_MODE
                    and _is_lower_hex(identity["git_blob"], 40)
                    and type(identity["byte_size"]) is int
                    and identity["byte_size"] > 0
                    and _is_lower_hex(identity["raw_sha256"], 64)
                    and dict(identity) == expected_identity,
                    f"Amendment-18 repair input identity drift at {position}",
                )
            source_identities = [
                dict(row["input_identity"]) for row in source_rows
            ]
            questionnaire_identities = [
                row
                for row in source_identities
                if row["document_role"] == "questionnaire_flow"
            ]
            repair_identities = [
                dict(row["input_identity"]) for row in repair_rows
            ]
            _require(
                len({row["source_document_id"] for row in source_identities})
                == len(source_identities)
                and len({row["path"] for row in repair_identities})
                == len(repair_identities)
                and _sha256(
                    canonical_json_bytes(
                        [
                            row["source_document_id"]
                            for row in questionnaire_identities
                        ]
                    )
                )
                == candidate["questionnaire_document_keyset_sha256"]
                and _sha256(canonical_json_bytes(questionnaire_identities))
                == candidate["questionnaire_document_domain_sha256"]
                and _sha256(
                    canonical_json_bytes(
                        [
                            row["source_document_id"]
                            for row in source_identities
                        ]
                    )
                )
                == candidate["source_document_keyset_sha256"]
                and _sha256(canonical_json_bytes(source_identities))
                == candidate["source_document_domain_sha256"]
                and _sha256(
                    canonical_json_bytes(
                        [row["path"] for row in repair_identities]
                    )
                )
                == candidate["repair_seal_evidence_path_domain_sha256"],
                "Amendment-18 build-input-domain membership equation drift",
            )
        except (KeyError, TypeError, LawError) as error:
            raise LawError(
                "Amendment-18 build-input-domain envelope drift"
            ) from error
        return _sha256(raw)

    rejected: list[str] = []

    expected_build_envelope = build_input_envelope()
    build_canonical = canonical_json_bytes(expected_build_envelope)
    build_digest = validate_build_input_envelope(build_canonical)
    _require(
        _is_lower_hex(build_digest, 64)
        and build_digest
        == validate_build_input_envelope(
            canonical_json_bytes(copy.deepcopy(expected_build_envelope))
        ),
        "Amendment-18 independent build-input canonical bytes disagree",
    )

    build_variants: list[Mapping[str, Any] | bytes] = []
    variant = copy.deepcopy(expected_build_envelope)
    variant.pop("schema_version")
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["unregistered_member"] = None
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"].pop(0)
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"].append(copy.deepcopy(variant["rows"][-1]))
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"][1] = copy.deepcopy(variant["rows"][0])
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"][0:2] = reversed(variant["rows"][0:2])
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"][0]["input_class"] = "repair_seal_evidence"
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"][0]["input_identity"]["sha256"] = "0" * 64
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"][0]["input_identity"]["byte_size"] = True
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"][257]["input_identity"]["path"] = "../forged.json"
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"][0]["unregistered_member"] = None
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["rows"][0]["input_identity"].pop("storage_identity")
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["source_document_domain_sha256"] = "0" * 64
    build_variants.append(variant)
    variant = copy.deepcopy(expected_build_envelope)
    variant["row_count"] = True
    build_variants.append(variant)
    build_variants.extend(
        (
            build_canonical[:-1] + b" \n",
            b'{"schema_version":1,"schema_version":2}\n',
        )
    )
    for position, variant in enumerate(build_variants):
        raw = (
            variant
            if isinstance(variant, bytes)
            else canonical_json_bytes(variant)
        )
        _expect_law_error(
            lambda raw=raw: validate_build_input_envelope(raw),
            "Amendment-18 build-input-domain envelope drift",
            f"Amendment-18 build-input-domain attack variant {position}",
        )
    rejected.append(A18_EXPECTED_MUTATIONS[0])

    def select_historical_r05(
        context: Mapping[str, Any],
        validated_closures: Mapping[int, Mapping[str, Any]],
        binding: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            normalized = _validate_registry_ratification_context(context)
            revision = normalized["revision"]
            amendment_numbers = _ratification_amendment_numbers(revision)
            _require(
                revision >= 18
                and amendment_numbers == tuple(range(13, revision - 1))
                and amendment_numbers[2] == 15
                and tuple(validated_closures) == amendment_numbers
                and dict(validated_closures[15]) == A15_EXPECTED_CLOSURE
                and normalized["ratification_closures"][2]
                == A15_HISTORICAL_CLOSURE_BINDING
                and dict(binding) == A18_HISTORICAL_R05_BINDING
                and tuple(binding) == tuple(A18_HISTORICAL_R05_BINDING),
                "Amendment-18 R05 selector or binding drift",
            )
        except (KeyError, IndexError, LawError) as error:
            raise LawError(
                "Amendment-18 R05 selector or binding drift"
            ) from error
        return copy.deepcopy(A18_HISTORICAL_R05_BINDING)

    contexts: dict[int, dict[str, Any]] = {}
    closures_by_revision: dict[int, dict[int, Mapping[str, Any]]] = {}
    for revision in (18, 19, 20, 21):
        amendment_numbers = tuple(range(13, revision - 1))
        contexts[revision] = _synthetic_oracle_context(
            revision,
            amendment_numbers,
        )
        closures_by_revision[revision] = {
            amendment_number: (
                copy.deepcopy(A15_EXPECTED_CLOSURE)
                if amendment_number == 15
                else {"amendment_number": amendment_number}
            )
            for amendment_number in amendment_numbers
        }
        _require(
            select_historical_r05(
                contexts[revision],
                closures_by_revision[revision],
                A18_HISTORICAL_R05_BINDING,
            )
            == A18_HISTORICAL_R05_BINDING,
            "Amendment-18 lawful R05 selector control drift",
        )

    r05_attacks: list[
        tuple[
            Mapping[str, Any],
            Mapping[int, Mapping[str, Any]],
            Mapping[str, Any],
        ]
    ] = []
    r05_attacks.append(
        (
            contexts[20],
            closures_by_revision[18],
            A18_HISTORICAL_R05_BINDING,
        )
    )
    context = copy.deepcopy(contexts[20])
    context["ratification_closures"].pop()
    r05_attacks.append(
        (context, closures_by_revision[20], A18_HISTORICAL_R05_BINDING)
    )
    context = copy.deepcopy(contexts[20])
    context["ratification_closures"][2:4] = reversed(
        context["ratification_closures"][2:4]
    )
    r05_attacks.append(
        (context, closures_by_revision[20], A18_HISTORICAL_R05_BINDING)
    )
    context = copy.deepcopy(contexts[20])
    context["ratification_closures"].pop(2)
    r05_attacks.append(
        (context, closures_by_revision[20], A18_HISTORICAL_R05_BINDING)
    )
    binding = copy.deepcopy(A18_HISTORICAL_R05_BINDING)
    binding["design_revision"] = 18
    r05_attacks.append((contexts[20], closures_by_revision[20], binding))
    closures = copy.deepcopy(closures_by_revision[20])
    closures[15]["attested_candidate_design_raw_sha256"] = "0" * 64
    r05_attacks.append((contexts[20], closures, A18_HISTORICAL_R05_BINDING))
    context16 = _synthetic_oracle_context(16, (13, 14))
    r05_attacks.append(
        (
            context16,
            {13: {"amendment_number": 13}, 14: {"amendment_number": 14}},
            A18_HISTORICAL_R05_BINDING,
        )
    )
    for position, (context, closures, binding) in enumerate(r05_attacks):
        _expect_law_error(
            lambda context=context, closures=closures, binding=binding: (
                select_historical_r05(context, closures, binding)
            ),
            "Amendment-18 R05 selector or binding drift",
            f"Amendment-18 R05 selector attack {position}",
        )
    rejected.append(A18_EXPECTED_MUTATIONS[1])

    r06_variants: list[Mapping[str, Any] | bytes] = []
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant.pop("schema_version")
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["unregistered_member"] = None
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["top_level_keys"].pop()
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["input_identity_row_keys"].append("reported_identity")
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["fixed_input_identities"]["amendment11_authority_artifact"][
        "raw_sha256"
    ] = ("0" * 64)
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["process_result"]["exit_code"] = True
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["process_result"]["stderr_exact_text"] = "substring only\n"
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["test_command"].pop()
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["test_environment"]["PYTHONPATH"] = "."
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["test_result"]["deselected"] = 1
    r06_variants.append(variant)
    for field in (
        "q5_input_emitted",
        "q5_first_add_performed",
        "authority_emitted",
        "production_output_emitted",
    ):
        variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
        variant["lifecycle"][field] = True
        r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["lifecycle"]["next_required_state"] = "CONTINUE"
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["captured_streams"].append("artifact")
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["first_add_minimum_revision"] = 19
    r06_variants.append(variant)
    variant = copy.deepcopy(A18_R06_RESULT_CONTRACT)
    variant["first_add_name_status_delta"].append(["M", DESIGN_PATH])
    r06_variants.append(variant)
    r06_canonical = canonical_json_bytes(A18_R06_RESULT_CONTRACT)
    r06_variants.extend(
        (
            r06_canonical[:-1] + b" \n",
            b'{"schema_version":1,"schema_version":2}\n',
        )
    )
    reject_contract_variants(
        A18_R06_RESULT_CONTRACT,
        r06_variants,
        "Amendment-18 R06 result or lifecycle contract drift",
        "Amendment-18 R06 contract attack",
    )
    rejected.append(A18_EXPECTED_MUTATIONS[2])

    rejected_tuple = tuple(rejected)
    _require(
        rejected_tuple == A18_EXPECTED_MUTATIONS
        and len(set(rejected_tuple)) == len(rejected_tuple)
        and _sha256(canonical_json_bytes(list(rejected_tuple)))
        == A18_MUTATION_DOMAIN_SHA256,
        "Amendment-18 mutation inventory drift",
    )
    return rejected_tuple


def _a19_same_json_types(candidate: Any, expected: Any) -> bool:
    if type(candidate) is not type(expected):
        return False
    if isinstance(expected, Mapping):
        return set(candidate) == set(expected) and all(
            _a19_same_json_types(candidate[key], expected[key])
            for key in expected
        )
    if isinstance(expected, list):
        return len(candidate) == len(expected) and all(
            _a19_same_json_types(left, right)
            for left, right in zip(candidate, expected, strict=True)
        )
    return True


def _validate_a19_purpose_mapping_contract(
    candidate: Mapping[str, Any],
) -> None:
    message = "Amendment-19 purpose-mapping totality contract drift"
    try:
        _require(
            isinstance(candidate, Mapping)
            and _a19_same_json_types(candidate, A19_PURPOSE_MAPPING_CONTRACT),
            message,
        )
        dispositions = candidate["disposition_counts"]
        document_rows = candidate["classification_document_rows"]
        underdetermined_count = sum(
            dispositions[key]
            for key in candidate["disposition_order"]
            if key != "complete_official_mapping"
        )
        _require(
            len(candidate["official_purpose_order"]) == 35
            and len(set(candidate["official_purpose_order"])) == 35
            and len(candidate["legacy_literals"]) == 13
            and len(set(candidate["legacy_literals"])) == 13
            and not set(candidate["legacy_literals"])
            & set(candidate["official_purpose_order"])
            and sum(dispositions.values())
            == candidate["field_purpose_prompt_count"]
            and dispositions["missing_mapping_underdetermined"]
            == candidate["unclassified_prompt_count"]
            and dispositions["complete_official_mapping"]
            + dispositions[
                "partial_official_mapping_with_legacy_residue_underdetermined"
            ]
            == candidate["official_mapped_prompt_count"]
            and dispositions["legacy_only_mapping_underdetermined"]
            + dispositions["missing_mapping_underdetermined"]
            == candidate["missing_official_mapping_prompt_count"]
            and candidate["official_only_edge_count"]
            + candidate["mixed_official_edge_count"]
            == candidate["official_edge_count"]
            and candidate["mixed_legacy_edge_count"]
            + candidate["legacy_only_edge_count"]
            == candidate["legacy_edge_count"]
            and len(document_rows)
            == candidate["classification_document_count"]
            and sum(row["prompt_count"] for row in document_rows)
            == candidate["classification_row_count"]
            and sum(
                row["official_mapped_prompt_count"] for row in document_rows
            )
            == candidate["official_mapped_prompt_count"]
            and candidate["classification_row_count"]
            + candidate["unclassified_prompt_count"]
            == candidate["field_purpose_prompt_count"]
            and candidate["source_classification_resolution"]
            == (
                "zero_or_one_same_annotation_row_by_shape_specific_"
                "occurrence_id"
            )
            and candidate["construction_order"]
            == [
                "authenticate_fixed_prompt_denominator",
                "construct_complete_purpose_mapping_rows_keyset_domain_"
                "and_counts",
                "compute_U_underdetermined_mapping_prompt_count",
                "select_failure_or_normal_variant",
                "normal_variant_only_construct_O_H_purpose_independent",
                "normal_variant_only_evaluate_O_P_witnesses",
            ]
            and candidate["source_classification_join_keys"]
            == {
                "plural": "source_prompt_occurrence_id",
                "singular": "source_occurrence_id",
            }
            and candidate["source_classification_status_rules"]
            == {
                "plural": {
                    "key": "annotation_status",
                    "value": "complete",
                },
                "singular": {
                    "key": "classification_status",
                    "value": "complete_document_local_provisional",
                },
            }
            and candidate["source_classification_join_keys"]["plural"]
            in candidate["plural_source_row_keys"]
            and candidate["source_classification_join_keys"]["singular"]
            in candidate["singular_source_row_keys"]
            and candidate["source_classification_status_rules"]["plural"][
                "key"
            ]
            in candidate["plural_source_row_keys"]
            and candidate["source_classification_status_rules"]["singular"][
                "key"
            ]
            in candidate["singular_source_row_keys"]
            and candidate["purpose_mapping_keyset_canonical_byte_size"]
            == 2_131_189
            and candidate["purpose_mapping_keyset_sha256"]
            == (
                "2d1300eaae5c8259f1cda59907d2cf0b8174faf5a37a3549e6d6f3eec9618921"
            )
            and candidate["purpose_mapping_domain_canonical_byte_size"]
            == 7_244_433
            and candidate["purpose_mapping_domain_sha256"]
            == (
                "53158188e774c75fcbe6b7af57bfa747060c80193556eac7a0e289e02b63ed1e"
            )
            and candidate["first_source_prompt_occurrence_id"]
            == (
                "psid-questionnaire-occurrence:"
                "17d4dd6699adc429dc5548b30763fc11425469927c1f02c41c15ae6a93c3828a"
            )
            and candidate["last_source_prompt_occurrence_id"]
            == (
                "psid-questionnaire-occurrence:"
                "d1c8bdfb99364eff8092c663c399e6e4391e6fcd9c6bb742bdda13f1df489980"
            )
            and candidate["underdetermined_mapping_prompt_count"]
            == underdetermined_count
            == 21_153
            and candidate["no_current_prompt_source_proved_no_purpose"] is True
            and candidate["underdetermined_selects_early_failure_variant"]
            is True
            and candidate["selected_failure_variant_evaluates_o_h"] is False
            and candidate["selected_failure_variant_evaluates_o_p"] is False
            and candidate["normal_variant_o_h_remains_purpose_independent"]
            is True
            and candidate["normal_variant_o_h_precedes_o_p_witness_evaluation"]
            is True
            and candidate == A19_PURPOSE_MAPPING_CONTRACT,
            message,
        )
    except (KeyError, TypeError, ValueError, LawError) as error:
        raise LawError(message) from error


def _validate_a19_semantic_binding_contract(
    candidate: Mapping[str, Any],
) -> None:
    message = "Amendment-19 semantic-binding totality contract drift"
    try:
        _require(
            isinstance(candidate, Mapping)
            and _a19_same_json_types(
                candidate,
                A19_SEMANTIC_BINDING_CONTRACT,
            )
            and candidate[
                "authenticated_complete_semantic_binding_relation_count"
            ]
            == 0
            and candidate[
                "audit_is_discovery_evidence_not_selected_branch_member_input"
            ]
            is True
            and candidate[
                "failure_selector_precedes_semantic_binding_evaluation"
            ]
            is True
            and candidate[
                "selected_failure_variant_serializes_near_match_rows"
            ]
            is False
            and candidate[
                "normal_variant_requires_inherited_complete_semantic_bindings"
            ]
            is True
            and candidate == A19_SEMANTIC_BINDING_CONTRACT,
            message,
        )
    except (KeyError, TypeError, LawError) as error:
        raise LawError(message) from error


def _validate_a19_source_hierarchy_failure_contract(
    candidate: Mapping[str, Any],
) -> None:
    message = "Amendment-19 early source-hierarchy failure contract drift"
    try:
        _require(
            isinstance(candidate, Mapping)
            and _a19_same_json_types(
                candidate,
                A19_SOURCE_HIERARCHY_FAILURE_CONTRACT,
            ),
            message,
        )
        failure_member = candidate["failure_member"]
        member_identity = candidate["source_hierarchy_member_identity"]
        failure_bytes = canonical_json_bytes(failure_member)
        identity_bytes = canonical_json_bytes(member_identity)
        underdetermined_count = A19_PURPOSE_MAPPING_CONTRACT[
            "underdetermined_mapping_prompt_count"
        ]
        shared_inherited_header_keys = {
            "authority_kind",
            "questionnaire_document_count",
            "questionnaire_document_keyset_sha256",
            "questionnaire_document_domain_sha256",
            "canonical_order",
            "status",
        }
        shared_purpose_summary_keys = {
            "purpose_mapping_row_count",
            "purpose_mapping_keyset_sha256",
            "purpose_mapping_domain_sha256",
            "purpose_mapping_disposition_counts",
        }
        effective_normal_header_keys = list(
            A19_A12_SUCCESSOR_AUTHORITY_HEADER_KEYS
        )
        hierarchy_domain_position = effective_normal_header_keys.index(
            "hierarchy_domain_sha256"
        )
        effective_normal_header_keys.insert(
            hierarchy_domain_position,
            "hierarchy_preproof_domain_sha256",
        )
        hierarchy_domain_position += 1
        for offset, key in enumerate(
            (
                "purpose_mapping_row_count",
                "purpose_mapping_keyset_sha256",
                "purpose_mapping_domain_sha256",
                "purpose_mapping_disposition_counts",
            ),
            start=1,
        ):
            effective_normal_header_keys.insert(
                hierarchy_domain_position + offset,
                key,
            )
        expected_forbidden_header_keys = [
            key
            for key in effective_normal_header_keys
            if key not in candidate["failure_member_keys"]
        ]
        a12_row_families = {
            "role_label_class_rows",
            "role_assignment_rows",
            "component_parent_resolution_rows",
            "outside_r_q_repeat_terminal_rows",
            "noncatalog_aggregate_relation_disposition_rows",
            "in_domain_redirection_disposition_rows",
            "catalog_only_job_disposition_rows",
        }
        _require(
            candidate["selection_stage"]
            == "after_purpose_mapping_before_all_pass_member_construction"
            and candidate["selection_predicate"]
            == "underdetermined_mapping_prompt_count_gt_zero"
            and candidate["fixed_selector_value"]
            is (underdetermined_count > 0)
            and candidate[
                "global_purpose_mapping_rows_constructed_before_selection"
            ]
            is True
            and candidate[
                "selected_failure_variant_serializes_per_era_purpose_"
                "mapping_rows"
            ]
            is False
            and underdetermined_count == 21_153
            and isinstance(failure_member, Mapping)
            and set(failure_member) == set(candidate["failure_member_keys"])
            and len(candidate["failure_member_keys"])
            == len(set(candidate["failure_member_keys"]))
            == 10
            and len(A19_A12_SUCCESSOR_AUTHORITY_HEADER_KEYS)
            == len(set(A19_A12_SUCCESSOR_AUTHORITY_HEADER_KEYS))
            == 78
            and set(A19_A12_SUCCESSOR_AUTHORITY_HEADER_KEYS)
            & set(candidate["failure_member_keys"])
            == shared_inherited_header_keys
            and shared_purpose_summary_keys
            <= set(candidate["failure_member_keys"])
            and not shared_purpose_summary_keys
            & set(A19_A12_SUCCESSOR_AUTHORITY_HEADER_KEYS)
            and len(effective_normal_header_keys)
            == len(set(effective_normal_header_keys))
            == 83
            and set(candidate["failure_member_keys"])
            <= set(effective_normal_header_keys)
            and candidate["forbidden_authority_header_keys"]
            == expected_forbidden_header_keys
            and len(candidate["forbidden_authority_header_keys"])
            == len(set(candidate["forbidden_authority_header_keys"]))
            == 73
            and set(candidate["forbidden_authority_header_keys"])
            == set(effective_normal_header_keys)
            - set(candidate["failure_member_keys"])
            and not set(failure_member)
            & set(candidate["forbidden_authority_header_keys"])
            and len(candidate["forbidden_evaluation_or_serialization"])
            == len(set(candidate["forbidden_evaluation_or_serialization"]))
            and a12_row_families
            <= set(candidate["forbidden_evaluation_or_serialization"])
            and "per_era_purpose_mapping_rows"
            in candidate["forbidden_evaluation_or_serialization"]
            and "era_rows"
            in candidate["forbidden_evaluation_or_serialization"]
            and "normal_authority_header"
            in candidate["forbidden_evaluation_or_serialization"]
            and "A12-T2-R04_overall_gate"
            in candidate["forbidden_evaluation_or_serialization"]
            and {"H", "O_H", "reverse_cover", "purpose_expansion"}
            <= set(candidate["forbidden_evaluation_or_serialization"])
            and {"Q5", "G17-C01", "authority_emission", "production_output"}
            <= set(candidate["forbidden_evaluation_or_serialization"])
            and failure_member["purpose_mapping_disposition_counts"]
            == A19_PURPOSE_MAPPING_CONTRACT["disposition_counts"]
            and failure_member["purpose_mapping_row_count"]
            == A19_PURPOSE_MAPPING_CONTRACT["field_purpose_prompt_count"]
            and failure_member["purpose_mapping_keyset_sha256"]
            == A19_PURPOSE_MAPPING_CONTRACT["purpose_mapping_keyset_sha256"]
            and failure_member["purpose_mapping_domain_sha256"]
            == A19_PURPOSE_MAPPING_CONTRACT["purpose_mapping_domain_sha256"]
            and failure_member == A19_SOURCE_HIERARCHY_FAILURE_MEMBER
            and len(failure_bytes)
            == candidate["failure_member_canonical_byte_size"]
            == member_identity["canonical_byte_size"]
            == 877
            and _sha256(failure_bytes)
            == candidate["failure_member_raw_sha256"]
            == member_identity["raw_sha256"]
            == (
                "1651c50ff1f171ac420e55982cb060db70946f9283999c3d9edb2fa140d467c5"
            )
            and isinstance(member_identity, Mapping)
            and set(member_identity)
            == set(candidate["source_hierarchy_member_identity_keys"])
            and len(candidate["source_hierarchy_member_identity_keys"])
            == len(set(candidate["source_hierarchy_member_identity_keys"]))
            and member_identity == A19_SOURCE_HIERARCHY_MEMBER_IDENTITY
            and member_identity["authority_kind"]
            == "pre_q5_source_hierarchy_failure_member_nonauthority"
            and member_identity["member_name"]
            == "hierarchy_annotation_authority"
            and member_identity["status"]
            == failure_member["status"]
            == "fail_source_purpose_mapping_underdetermined"
            and len(identity_bytes)
            == candidate[
                "source_hierarchy_member_identity_canonical_byte_size"
            ]
            == 351
            and _sha256(identity_bytes)
            == candidate["source_hierarchy_member_identity_raw_sha256"]
            == (
                "077c6a19e44d8abdf96422a8d2d203fdf263ecbbfb70cb9bb3dc9522a3dcd2bd"
            )
            and candidate["r04_dual_reconstruction_required"] is True
            and candidate["r04_independent_reconstruction_subresult_count"]
            == 2
            and candidate["r04_independent_reconstruction_subresult_status"]
            == "pass_independent_source_reconstruction"
            and candidate[
                "r04_independent_reconstruction_subresults_require_exact_"
                "selected_member_bytes"
            ]
            is True
            and candidate["a12_t2_r04_overall_gate_preserved"] is True
            and candidate["a12_t2_r04_selected_failure_gate_pass_permitted"]
            is False
            and candidate["r05_requires_passing_normal_member"] is True
            and candidate["r05_pass_or_certification_emission_permitted"]
            is False
            and candidate["q5_or_authority_emission_permitted"] is False
            and candidate == A19_SOURCE_HIERARCHY_FAILURE_CONTRACT,
            message,
        )
    except (KeyError, TypeError, LawError) as error:
        raise LawError(message) from error


def _validate_a19_hierarchy_construction_contract(
    candidate: Mapping[str, Any],
) -> None:
    message = "Amendment-19 staged hierarchy construction contract drift"
    try:
        _require(
            isinstance(candidate, Mapping)
            and _a19_same_json_types(
                candidate,
                A19_HIERARCHY_CONSTRUCTION_CONTRACT,
            ),
            message,
        )
        preproof_keys = candidate["preproof_row_keys"]
        final_keys = candidate["final_row_keys"]
        search_keys = candidate["search_implementation_keys"]
        _require(
            final_keys[:-1] == preproof_keys
            and final_keys[-1] == "hierarchy_absence_proof_id"
            and "hierarchy_absence_proof_id" not in preproof_keys
            and "hierarchy_preproof_domain_sha256" in search_keys
            and "hierarchy_domain_sha256" not in search_keys
            and len(search_keys) == 15
            and len(set(search_keys)) == 15
            and candidate["applicability"]
            == "only_if_purpose_failure_selector_false"
            and candidate[
                "selected_failure_variant_executes_hierarchy_construction"
            ]
            is False
            and candidate["per_era_insertion"] == "purpose_mapping_rows"
            and candidate["g17_c01_normal_projection_sides"]
            == ["expected", "actual"]
            and candidate["g17_c01_normal_per_era_insertion_order"]
            == [
                "hierarchy_rows",
                "purpose_mapping_rows",
                "positive_occurrence_rows",
            ]
            and candidate["g17_c01_normal_direct_concatenation_header_members"]
            == [
                "purpose_mapping_row_count",
                "purpose_mapping_keyset_sha256",
                "purpose_mapping_domain_sha256",
                "purpose_mapping_disposition_counts",
            ]
            and candidate[
                "selected_failure_variant_executes_g17_c01_projection"
            ]
            is False
            and candidate["dependency_order"]
            == [
                "preproof_rows",
                "hierarchy_preproof_domain_sha256",
                "search_implementation",
                "absence_proof_ids",
                "final_hierarchy_rows",
                "hierarchy_domain_sha256",
                "dependent_proof_expanded_era_and_member_digests",
            ]
            and candidate == A19_HIERARCHY_CONSTRUCTION_CONTRACT,
            message,
        )
    except (KeyError, TypeError, LawError) as error:
        raise LawError(message) from error


def _a19_worked_search_implementation(preproof_digest: str) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key in A19_HIERARCHY_CONSTRUCTION_CONTRACT[
        "search_implementation_keys"
    ]:
        if key == "authority_kind":
            value[key] = "source_only_canonical_questionnaire_annotation"
        elif key == "near_match_source_annotation_count":
            value[key] = 0
        elif key in {
            "near_match_source_annotation_keyset_sha256",
            "near_match_source_annotation_domain_sha256",
        }:
            value[key] = (
                "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
            )
        elif key == "hierarchy_preproof_domain_sha256":
            value[key] = preproof_digest
        else:
            value[key] = "0" * 64
    return value


def _derive_a19_staged_hierarchy_identity(
    preproof_rows: Sequence[Mapping[str, Any]],
    proof_targets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    message = "Amendment-19 staged hierarchy worked identity drift"
    preproof_keys = A19_HIERARCHY_CONSTRUCTION_CONTRACT["preproof_row_keys"]
    target_keys = A19_HIERARCHY_CONSTRUCTION_CONTRACT[
        "proof_id_preimage_order"
    ][:-1]
    _require(
        len(preproof_rows) == len(proof_targets) > 0,
        message,
    )
    normalized_rows: list[dict[str, Any]] = []
    normalized_targets: list[dict[str, Any]] = []
    for row, target in zip(preproof_rows, proof_targets, strict=True):
        _require(
            isinstance(row, Mapping)
            and list(row) == preproof_keys
            and isinstance(target, Mapping)
            and list(target) == target_keys,
            message,
        )
        normalized_rows.append(copy.deepcopy(dict(row)))
        normalized_targets.append(copy.deepcopy(dict(target)))
    preproof_digest = _sha256(canonical_json_bytes(normalized_rows))
    search = _a19_worked_search_implementation(preproof_digest)
    proof_ids = []
    final_rows = []
    for row, target in zip(
        normalized_rows,
        normalized_targets,
        strict=True,
    ):
        preimage = [target[key] for key in target_keys]
        preimage.append(search)
        proof_id = "psid-absence-proof:" + _sha256(
            canonical_json_bytes(preimage)
        )
        proof_ids.append(proof_id)
        final_row = copy.deepcopy(row)
        final_row["hierarchy_absence_proof_id"] = (
            proof_id
            if row["hierarchy_presence"] == "structural_hierarchy_node"
            else None
        )
        final_rows.append(final_row)
    final_digest = _sha256(canonical_json_bytes(final_rows))
    return {
        "preproof_rows": normalized_rows,
        "hierarchy_preproof_domain_sha256": preproof_digest,
        "proof_targets": normalized_targets,
        "search_implementation": search,
        "absence_proof_ids": proof_ids,
        "final_hierarchy_rows": final_rows,
        "hierarchy_domain_sha256": final_digest,
    }


def _validate_a19_staged_hierarchy_identity(
    candidate: Mapping[str, Any],
) -> None:
    message = "Amendment-19 staged hierarchy worked identity drift"
    try:
        _require_exact_keys(
            candidate,
            {
                "preproof_rows",
                "hierarchy_preproof_domain_sha256",
                "proof_targets",
                "search_implementation",
                "absence_proof_ids",
                "final_hierarchy_rows",
                "hierarchy_domain_sha256",
            },
            "Amendment-19 staged hierarchy worked identity",
        )
        expected = _derive_a19_staged_hierarchy_identity(
            candidate["preproof_rows"],
            candidate["proof_targets"],
        )
        row = candidate["preproof_rows"][0]
        target = candidate["proof_targets"][0]
        relationship_preimage = [
            row["job_slot"],
            row["questionnaire_component_slot"],
            row["slot_kind"],
        ]
        slot_preimage = [
            row["interview_wave"],
            1968,
            row["role"],
            row["job_slot"],
            row["questionnaire_component_slot"],
            row["slot_kind"],
        ]
        _require(
            candidate == expected
            and candidate["preproof_rows"] == [_a19_worked_preproof_row()]
            and candidate["proof_targets"] == [_a19_worked_proof_target()]
            and row["relationship_id"]
            == "psid-questionnaire-relationship:"
            + _sha256(canonical_json_bytes(relationship_preimage))
            and row["questionnaire_slot_id"]
            == "psid-questionnaire-slot:"
            + _sha256(canonical_json_bytes(slot_preimage))
            and target["target_predicate"]
            == {
                "roles": ["head_or_reference_person"],
                "job_slot_ids": ["psid-job-slot:role-total"],
                "questionnaire_component_slot_ids": [
                    "psid-component-slot:role-total"
                ],
                "slot_kinds": ["role_total"],
                "field_purposes": ["amount"],
                "quantifier": (
                    "no_matching_questionnaire_node_in_searched_domain"
                ),
            }
            and candidate["search_implementation"]["authority_kind"]
            == "source_only_canonical_questionnaire_annotation"
            and candidate["hierarchy_preproof_domain_sha256"]
            == (
                "b3789fc44458bf3f361242ac3b891a357de9640eaf72f9ec4f103b7378f74af6"
            )
            and candidate["absence_proof_ids"]
            == [
                "psid-absence-proof:"
                "f374f82fcbbbc2757e85568e380a75061d4707a7467650ceb9f09382638e9101"
            ]
            and candidate["hierarchy_domain_sha256"]
            == (
                "4dd38d95cb08aff565edce70b716bb9f30aef607dcddc2e0c1f51cb8a1bbf453"
            ),
            message,
        )
    except (KeyError, TypeError, LawError) as error:
        raise LawError(message) from error


def _validate_a19_successor_and_activation_contract(
    routing: Mapping[str, Any],
    activation: Mapping[str, Any],
    production_boundary: Mapping[str, Any] | None = None,
) -> None:
    message = "Amendment-19 successor-stop or revision-21 routing drift"
    if production_boundary is None:
        production_boundary = A19_NORMATIVE_MANIFEST[
            "production_registry_boundary"
        ]
    expected_production_boundary = A19_NORMATIVE_MANIFEST[
        "production_registry_boundary"
    ]
    try:
        _require(
            isinstance(routing, Mapping)
            and isinstance(activation, Mapping)
            and isinstance(production_boundary, Mapping)
            and _a19_same_json_types(routing, A19_SUCCESSOR_ROUTING_CONTRACT)
            and _a19_same_json_types(activation, A19_ACTIVATION_TRANSITION)
            and _a19_same_json_types(
                production_boundary,
                expected_production_boundary,
            )
            and routing["historical_amendment18_next_required_state"]
            == "A19_SUCCESSOR_PROGRAM_STOP"
            and routing["active_next_required_state"]
            == "A20_SUCCESSOR_PROGRAM_STOP"
            and routing["active_lifecycle_derivation"]
            == (
                "deep_copy_A18_R06_RESULT_CONTRACT_lifecycle_replace_only_"
                "next_required_state"
            )
            and routing["all_other_r06_members_unchanged"] is True
            and routing["current_amendment"] == 19
            and routing["current_revision"] == 21
            and routing["deferred_program_amendment"] == 20
            and routing["deferred_program_revision"] == 22
            and routing["deferred_campaign_substance"] == "OUT_OF_SCOPE"
            and routing["historical_identifier_is_not_active_alias"] is True
            and routing["r06_artifact_blocked_while_r05_nonpass"] is True
            and activation["terminal_revision"] == 21
            and activation["terminal_amendment"] == 19
            and activation["ordered_closure_domain"] == list(range(13, 20))
            and activation["closure_count"]
            == len(activation["ordered_closure_domain"])
            == activation["terminal_revision"]
            - activation["closure_count_subtrahend"]
            and activation["activation_affecting"] is True
            and activation["same_state_required"] is True
            and activation["full_pinned_battery_required"] is True
            and activation["receipt_inside_candidate_bytes"] is False
            and activation["activation_requires_later_registry_repin"] is True
            and activation["production_registry_revision_in_draft"] == 20
            and activation["production_oracle_changed_by_draft"] is False
            and production_boundary["revision"] == 20
            and production_boundary["ordered_closure_domain"]
            == list(range(13, 19))
            and production_boundary["closure_count"]
            == len(production_boundary["ordered_closure_domain"])
            == production_boundary["revision"]
            - activation["closure_count_subtrahend"]
            and production_boundary["revision"]
            == activation["production_registry_revision_in_draft"]
            == activation["terminal_revision"] - 1
            and production_boundary["unchanged_by_draft"] is True
            and routing == A19_SUCCESSOR_ROUTING_CONTRACT
            and activation == A19_ACTIVATION_TRANSITION
            and production_boundary == expected_production_boundary,
            message,
        )
    except (KeyError, TypeError, LawError) as error:
        raise LawError(message) from error


def _a19_worked_preproof_row() -> dict[str, Any]:
    values: dict[str, Any] = {
        "questionnaire_slot_id": (
            "psid-questionnaire-slot:"
            "58e93ce163bb81b1b7838cc36fef0994f207b05684d2a2bb571d5800f87ff7a9"
        ),
        "interview_wave": 1968,
        "role": "head_or_reference_person",
        "relationship_id": (
            "psid-questionnaire-relationship:"
            "ff2a7f7263d10214f6868b9355f73a30b226ab2cb618dc89e03b96c8e8246159"
        ),
        "job_slot": "psid-job-slot:role-total",
        "questionnaire_component_slot": "psid-component-slot:role-total",
        "slot_kind": "role_total",
        "hierarchy_presence": "structural_hierarchy_node",
        "hierarchy_occurrence_ids": [],
        "flow_branch_ids": [],
        "flow_branch_paths": [],
        "source_locator_ids": [],
    }
    return {
        key: values[key]
        for key in A19_HIERARCHY_CONSTRUCTION_CONTRACT["preproof_row_keys"]
    }


def _a19_worked_proof_target() -> dict[str, Any]:
    values: dict[str, Any] = {
        "era_id": "wave1968_ry1968_1974_early_totals",
        "target_predicate": {
            "roles": ["head_or_reference_person"],
            "job_slot_ids": ["psid-job-slot:role-total"],
            "questionnaire_component_slot_ids": [
                "psid-component-slot:role-total"
            ],
            "slot_kinds": ["role_total"],
            "field_purposes": ["amount"],
            "quantifier": (
                "no_matching_questionnaire_node_in_searched_domain"
            ),
        },
        "searched_interview_waves": [1968],
        "searched_locator_ids": ["psid-whole-document:" + "0" * 64],
        "searched_layout_keyset_sha256": "1" * 64,
        "searched_codebook_keyset_sha256": "2" * 64,
    }
    return {
        key: values[key]
        for key in A19_HIERARCHY_CONSTRUCTION_CONTRACT[
            "proof_id_preimage_order"
        ][:-1]
    }


def run_amendment19_member_law_mutation_tests() -> tuple[str, ...]:
    """Execute inherited censuses, then three grouped A19 law attacks."""

    amendment18 = run_amendment18_contract_mutation_tests()
    _require(
        amendment18 == A18_EXPECTED_MUTATIONS
        and len(amendment18)
        == A19_MUTATION_CENSUS["amendment18_mutation_count"]
        and _sha256(canonical_json_bytes(list(amendment18)))
        == A19_MUTATION_CENSUS["amendment18_mutation_domain_sha256"],
        "Amendment-19 inherited Amendment-18 mutation census drift",
    )
    _require(
        A18_MUTATION_CENSUS["inherited_complete_mutation_count"]
        == A19_MUTATION_CENSUS["inherited_complete_mutation_count"]
        and A18_MUTATION_CENSUS["inherited_complete_mutation_domain_sha256"]
        == A19_MUTATION_CENSUS["inherited_complete_mutation_domain_sha256"]
        and A18_MUTATION_CENSUS["amendment16_mutation_count"]
        == A19_MUTATION_CENSUS["amendment16_mutation_count"]
        and A18_MUTATION_CENSUS["amendment16_mutation_domain_sha256"]
        == A19_MUTATION_CENSUS["amendment16_mutation_domain_sha256"]
        and A18_MUTATION_CENSUS["amendment17_mutation_count"]
        == A19_MUTATION_CENSUS["amendment17_mutation_count"]
        and A18_MUTATION_CENSUS["amendment17_mutation_domain_sha256"]
        == A19_MUTATION_CENSUS["amendment17_mutation_domain_sha256"],
        "Amendment-19 inherited mutation census chain drift",
    )

    rejected: list[str] = []

    _validate_a19_purpose_mapping_contract(A19_PURPOSE_MAPPING_CONTRACT)
    _validate_a19_semantic_binding_contract(A19_SEMANTIC_BINDING_CONTRACT)
    _validate_a19_source_hierarchy_failure_contract(
        A19_SOURCE_HIERARCHY_FAILURE_CONTRACT
    )
    purpose_variants: list[tuple[str, Mapping[str, Any]]] = []
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["field_purpose_prompt_count"] = 21_970
    purpose_variants.append(("prompt denominator", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["disposition_counts"]["missing_mapping_underdetermined"] = 21_082
    purpose_variants.append(("disposition partition", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["official_purpose_order"][0:2] = reversed(
        variant["official_purpose_order"][0:2]
    )
    purpose_variants.append(("official purpose order", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["disposition_order"][-1] = "no_purpose"
    purpose_variants.append(("invented no-purpose default", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["text_transfer_forbidden"] = False
    purpose_variants.append(("text transfer", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["source_classification_join_keys"][
        "singular"
    ] = "source_prompt_occurrence_id"
    purpose_variants.append(("singular join key", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["source_classification_status_rules"]["plural"][
        "value"
    ] = "complete_document_local_provisional"
    purpose_variants.append(("plural source status", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["source_classification_status_rules"]["singular"][
        "value"
    ] = "complete"
    purpose_variants.append(("singular source status", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["purpose_mapping_domain_sha256"] = "0" * 64
    purpose_variants.append(("purpose domain identity", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["underdetermined_mapping_prompt_count"] = 21_152
    purpose_variants.append(("underdetermined selector count", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["construction_order"][1], variant["construction_order"][4] = (
        variant["construction_order"][4],
        variant["construction_order"][1],
    )
    purpose_variants.append(("O_H before purpose selector", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["selected_failure_variant_evaluates_o_h"] = True
    purpose_variants.append(("failure arm executes O_H", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["normal_variant_o_h_remains_purpose_independent"] = False
    purpose_variants.append(("purpose-dependent normal O_H", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["normal_variant_o_h_precedes_o_p_witness_evaluation"] = False
    purpose_variants.append(("normal O_P precedes O_H", variant))
    variant = copy.deepcopy(A19_PURPOSE_MAPPING_CONTRACT)
    variant["field_purpose_prompt_count"] = True
    purpose_variants.append(("boolean prompt count", variant))
    for label, variant in purpose_variants:
        _expect_law_error(
            lambda variant=variant: _validate_a19_purpose_mapping_contract(
                variant
            ),
            "Amendment-19 purpose-mapping totality contract drift",
            f"Amendment-19 purpose attack {label}",
        )
    binding_variants: list[Mapping[str, Any]] = []
    variant = copy.deepcopy(A19_SEMANTIC_BINDING_CONTRACT)
    variant["authenticated_complete_semantic_binding_relation_count"] = 1
    binding_variants.append(variant)
    variant = copy.deepcopy(A19_SEMANTIC_BINDING_CONTRACT)
    variant["failure_selector_precedes_semantic_binding_evaluation"] = False
    binding_variants.append(variant)
    variant = copy.deepcopy(A19_SEMANTIC_BINDING_CONTRACT)
    variant["selected_failure_variant_serializes_near_match_rows"] = True
    binding_variants.append(variant)
    for position, variant in enumerate(binding_variants):
        _expect_law_error(
            lambda variant=variant: _validate_a19_semantic_binding_contract(
                variant
            ),
            "Amendment-19 semantic-binding totality contract drift",
            f"Amendment-19 binding attack {position}",
        )
    failure_variants: list[Mapping[str, Any]] = []
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["fixed_selector_value"] = False
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["selection_stage"] = "after_all_pass_member_construction"
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    del variant["failure_member"]["purpose_mapping_domain_sha256"]
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["failure_member"]["hierarchy_domain_sha256"] = "0" * 64
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["failure_member_canonical_byte_size"] = 878
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["source_hierarchy_member_identity"][
        "authority_kind"
    ] = "prospective_g17_c01_source_member_pre_q5"
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["forbidden_authority_header_keys"].remove("role_assignment_rows")
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["forbidden_authority_header_keys"].append(
        "purpose_mapping_row_count"
    )
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["forbidden_evaluation_or_serialization"].remove(
        "catalog_only_job_disposition_rows"
    )
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["r04_independent_reconstruction_subresult_status"] = "pass"
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant[
        "r04_independent_reconstruction_subresults_require_exact_selected_"
        "member_bytes"
    ] = False
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["a12_t2_r04_overall_gate_preserved"] = False
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["a12_t2_r04_selected_failure_gate_pass_permitted"] = True
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["forbidden_evaluation_or_serialization"].remove(
        "A12-T2-R04_overall_gate"
    )
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant["r05_requires_passing_normal_member"] = False
    failure_variants.append(variant)
    variant = copy.deepcopy(A19_SOURCE_HIERARCHY_FAILURE_CONTRACT)
    variant[
        "selected_failure_variant_serializes_per_era_purpose_mapping_rows"
    ] = True
    failure_variants.append(variant)
    for position, variant in enumerate(failure_variants):
        _expect_law_error(
            lambda variant=variant: (
                _validate_a19_source_hierarchy_failure_contract(variant)
            ),
            "Amendment-19 early source-hierarchy failure contract drift",
            f"Amendment-19 early failure attack {position}",
        )
    rejected.append(A19_EXPECTED_MUTATIONS[0])

    _validate_a19_hierarchy_construction_contract(
        A19_HIERARCHY_CONSTRUCTION_CONTRACT
    )
    worked_identity = _derive_a19_staged_hierarchy_identity(
        [_a19_worked_preproof_row()],
        [_a19_worked_proof_target()],
    )
    _validate_a19_staged_hierarchy_identity(worked_identity)
    hierarchy_variants: list[Mapping[str, Any]] = []
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["preproof_row_keys"].append("hierarchy_absence_proof_id")
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    index = variant["search_implementation_keys"].index(
        "hierarchy_preproof_domain_sha256"
    )
    variant["search_implementation_keys"][index] = "hierarchy_domain_sha256"
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["dependency_order"][1:3] = reversed(
        variant["dependency_order"][1:3]
    )
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["placeholder_forbidden"] = False
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["applicability"] = "unconditional"
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["selected_failure_variant_executes_hierarchy_construction"] = True
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["g17_c01_normal_per_era_insertion_order"][1:3] = reversed(
        variant["g17_c01_normal_per_era_insertion_order"][1:3]
    )
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["g17_c01_normal_projection_sides"] = ["expected"]
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["g17_c01_normal_direct_concatenation_header_members"].remove(
        "purpose_mapping_disposition_counts"
    )
    hierarchy_variants.append(variant)
    variant = copy.deepcopy(A19_HIERARCHY_CONSTRUCTION_CONTRACT)
    variant["selected_failure_variant_executes_g17_c01_projection"] = True
    hierarchy_variants.append(variant)
    for position, variant in enumerate(hierarchy_variants):
        _expect_law_error(
            lambda variant=variant: (
                _validate_a19_hierarchy_construction_contract(variant)
            ),
            "Amendment-19 staged hierarchy construction contract drift",
            f"Amendment-19 hierarchy contract attack {position}",
        )
    identity_variants: list[Mapping[str, Any]] = []
    variant = copy.deepcopy(worked_identity)
    variant["hierarchy_preproof_domain_sha256"] = variant[
        "hierarchy_domain_sha256"
    ]
    identity_variants.append(variant)
    variant = copy.deepcopy(worked_identity)
    variant["search_implementation"]["hierarchy_preproof_domain_sha256"] = (
        variant["hierarchy_domain_sha256"]
    )
    identity_variants.append(variant)
    variant = copy.deepcopy(worked_identity)
    variant["absence_proof_ids"][0] = "psid-absence-proof:" + "0" * 64
    identity_variants.append(variant)
    variant = copy.deepcopy(worked_identity)
    variant["final_hierarchy_rows"][0]["hierarchy_absence_proof_id"] = None
    identity_variants.append(variant)
    variant = copy.deepcopy(worked_identity)
    variant["proof_targets"][0]["target_predicate"][
        "quantifier"
    ] = "none_exist"
    identity_variants.append(variant)
    variant = copy.deepcopy(worked_identity)
    variant["search_implementation"][
        "authority_kind"
    ] = "worked_identity_nonauthority"
    identity_variants.append(variant)
    variant = copy.deepcopy(worked_identity)
    variant["preproof_rows"][0]["relationship_id"] = (
        "psid-questionnaire-relationship:" + "0" * 64
    )
    identity_variants.append(variant)
    variant = copy.deepcopy(worked_identity)
    variant["preproof_rows"][0]["questionnaire_slot_id"] = (
        "psid-questionnaire-slot:" + "0" * 64
    )
    identity_variants.append(variant)
    for position, variant in enumerate(identity_variants):
        _expect_law_error(
            lambda variant=variant: _validate_a19_staged_hierarchy_identity(
                variant
            ),
            "Amendment-19 staged hierarchy worked identity drift",
            f"Amendment-19 hierarchy identity attack {position}",
        )
    rejected.append(A19_EXPECTED_MUTATIONS[1])

    _validate_a19_successor_and_activation_contract(
        A19_SUCCESSOR_ROUTING_CONTRACT,
        A19_ACTIVATION_TRANSITION,
        A19_NORMATIVE_MANIFEST["production_registry_boundary"],
    )
    successor_variants: list[
        tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]
    ] = []
    production_boundary = A19_NORMATIVE_MANIFEST[
        "production_registry_boundary"
    ]
    routing = copy.deepcopy(A19_SUCCESSOR_ROUTING_CONTRACT)
    routing["active_next_required_state"] = "A19_SUCCESSOR_PROGRAM_STOP"
    successor_variants.append(
        (routing, A19_ACTIVATION_TRANSITION, production_boundary)
    )
    routing = copy.deepcopy(A19_SUCCESSOR_ROUTING_CONTRACT)
    routing["historical_identifier_is_not_active_alias"] = False
    successor_variants.append(
        (routing, A19_ACTIVATION_TRANSITION, production_boundary)
    )
    routing = copy.deepcopy(A19_SUCCESSOR_ROUTING_CONTRACT)
    routing["deferred_campaign_substance"] = "IN_SCOPE"
    successor_variants.append(
        (routing, A19_ACTIVATION_TRANSITION, production_boundary)
    )
    activation = copy.deepcopy(A19_ACTIVATION_TRANSITION)
    activation["ordered_closure_domain"] = [13, 14, 15, 16, 17, 19, 18]
    successor_variants.append(
        (A19_SUCCESSOR_ROUTING_CONTRACT, activation, production_boundary)
    )
    activation = copy.deepcopy(A19_ACTIVATION_TRANSITION)
    activation["closure_count"] = True
    successor_variants.append(
        (A19_SUCCESSOR_ROUTING_CONTRACT, activation, production_boundary)
    )
    activation = copy.deepcopy(A19_ACTIVATION_TRANSITION)
    activation["terminal_revision"] = 20
    successor_variants.append(
        (A19_SUCCESSOR_ROUTING_CONTRACT, activation, production_boundary)
    )
    activation = copy.deepcopy(A19_ACTIVATION_TRANSITION)
    activation["production_registry_revision_in_draft"] = 19
    successor_variants.append(
        (A19_SUCCESSOR_ROUTING_CONTRACT, activation, production_boundary)
    )
    wrong_base_boundary = {
        "closure_count": 5,
        "ordered_closure_domain": [13, 14, 15, 16, 17],
        "revision": 19,
        "unchanged_by_draft": True,
    }
    successor_variants.append(
        (
            A19_SUCCESSOR_ROUTING_CONTRACT,
            A19_ACTIVATION_TRANSITION,
            wrong_base_boundary,
        )
    )
    for position, (routing, activation, production_boundary) in enumerate(
        successor_variants
    ):
        _expect_law_error(
            lambda routing=routing, activation=activation, production_boundary=production_boundary: (
                _validate_a19_successor_and_activation_contract(
                    routing,
                    activation,
                    production_boundary,
                )
            ),
            "Amendment-19 successor-stop or revision-21 routing drift",
            f"Amendment-19 successor attack {position}",
        )
    rejected.append(A19_EXPECTED_MUTATIONS[2])

    rejected_tuple = tuple(rejected)
    rejected_bytes = canonical_json_bytes(list(rejected_tuple))
    _require(
        rejected_tuple == A19_EXPECTED_MUTATIONS
        and len(set(rejected_tuple)) == len(rejected_tuple)
        and len(rejected_bytes) == A19_MUTATION_DOMAIN_BYTE_SIZE
        and _sha256(rejected_bytes) == A19_MUTATION_DOMAIN_SHA256,
        "Amendment-19 mutation inventory drift",
    )
    return rejected_tuple


def run_amendment20_contract_mutation_tests() -> tuple[str, ...]:
    """Authenticate inherited censuses, then run closed A20 mutations."""

    global ROOT

    amendment19 = run_amendment19_member_law_mutation_tests()
    expected_censuses = A20_INHERITED_MUTATION_CENSUSES
    _require(
        amendment19 == A19_EXPECTED_MUTATIONS
        and expected_censuses
        == [
            {
                "inventory": "inherited_complete_certificate",
                "count": 100,
                "raw_sha256": (
                    "fe2efd7b96c24b7cbd3c6ce350d44906"
                    "eb5a88b8b35ee77565c1b133cbf1f3e3"
                ),
            },
            {
                "inventory": "amendment16",
                "count": 7,
                "raw_sha256": A16_MUTATION_DOMAIN_SHA256,
            },
            {
                "inventory": "amendment17",
                "count": 3,
                "raw_sha256": A17_MUTATION_DOMAIN_SHA256,
            },
            {
                "inventory": "amendment18",
                "count": 3,
                "raw_sha256": A18_MUTATION_DOMAIN_SHA256,
            },
            {
                "inventory": "amendment19",
                "count": 3,
                "raw_sha256": A19_MUTATION_DOMAIN_SHA256,
            },
        ]
        and sum(row["count"] for row in expected_censuses) == 116,
        "Amendment-20 inherited mutation censuses drift",
    )

    rejected: list[str] = []

    def reject_manifest_variants(
        variants: Sequence[Mapping[str, Any]],
        expected_message: str,
        label: str,
    ) -> None:
        for position, candidate in enumerate(variants):
            _expect_law_error(
                lambda candidate=candidate: _validate_a20_manifest_contract(
                    candidate
                ),
                expected_message,
                f"{label} {position}",
            )

    def synthetic_identity_digest(label: str) -> str:
        return _sha256(canonical_json_bytes({"synthetic_identity": label}))

    def synthetic_pass_identity(
        identity_name: str,
        *,
        arm_status_member: str | None = None,
    ) -> dict[str, Any]:
        identity = {
            "identity_name": identity_name,
            "row_count": 1,
            "ordered_keyset_sha256": synthetic_identity_digest(
                f"{identity_name}:keyset"
            ),
            "row_domain_sha256": synthetic_identity_digest(
                f"{identity_name}:domain"
            ),
            "status": "pass",
        }
        if arm_status_member is not None:
            identity = {
                "identity_name": identity_name,
                "arm_status_member": arm_status_member,
                "arm_status": "pass",
                "row_count": identity["row_count"],
                "ordered_keyset_sha256": identity["ordered_keyset_sha256"],
                "row_domain_sha256": identity["row_domain_sha256"],
                "status": identity["status"],
            }
        return identity

    def synthetic_failure_shadow(
        status_member: str,
        arm_contract: Mapping[str, Any],
        nonemission_evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        pass_identity_names = arm_contract["pass_identity_names"]
        failure_status = arm_contract["failure_status"]
        complement_rows = [
            {"emitted": False, "identity_name": name}
            for name in pass_identity_names
        ]
        keyset_sha256 = _sha256(canonical_json_bytes(pass_identity_names))
        domain_sha256 = _sha256(canonical_json_bytes(complement_rows))
        return {
            "schema_version": "a20_failure_shadow_identity.v1",
            "identity_name": arm_contract["failure_shadow_identity_name"],
            "arm_status_member": status_member,
            "arm_status": failure_status,
            "shadow_row_count": len(pass_identity_names),
            "shadow_ordered_keyset_sha256": keyset_sha256,
            "shadow_row_domain_sha256": domain_sha256,
            "complement_identity": {
                "schema_version": "a20_nonemission_complement_identity.v1",
                "complement_of_identity_names": pass_identity_names,
                "row_count": len(pass_identity_names),
                "ordered_keyset_sha256": keyset_sha256,
                "row_domain_sha256": domain_sha256,
                "status": failure_status,
            },
            "forbidden_output_identity_names": pass_identity_names,
            "forbidden_output_paths": arm_contract["forbidden_output_paths"],
            "nonemission_evidence": copy.deepcopy(nonemission_evidence),
            "status": failure_status,
        }

    def synthetic_ready_freeze(
        failed_status_member: str | None = None,
        *,
        nonemission_evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        bindings: dict[str, Any] = {
            name: None for name in A20_EXPECTED_IDENTITY_NAMES
        }
        statuses = {
            status_member: (
                arm_contract["failure_status"]
                if status_member == failed_status_member
                else arm_contract["pass_status"]
            )
            for status_member, arm_contract in A20_ARM_IDENTITY_CONTRACTS.items()
        }
        successor_binding_name = "a20_successor_source_binding_identity"
        for identity_name in A20_COMMON_IDENTITY_NAMES:
            if identity_name != successor_binding_name:
                bindings[identity_name] = synthetic_pass_identity(
                    identity_name
                )
        for status_member, arm_contract in A20_ARM_IDENTITY_CONTRACTS.items():
            if statuses[status_member] == arm_contract["pass_status"]:
                for identity_name in arm_contract["pass_identity_names"]:
                    bindings[identity_name] = synthetic_pass_identity(
                        identity_name,
                        arm_status_member=status_member,
                    )
            else:
                _require(
                    nonemission_evidence is not None,
                    "Amendment-20 synthetic failure lacks real provenance",
                )
                bindings[arm_contract["failure_shadow_identity_name"]] = (
                    synthetic_failure_shadow(
                        status_member,
                        arm_contract,
                        nonemission_evidence,
                    )
                )
        active_binding_preimage = {
            "arm_status_bindings": statuses,
            "expected_identity_bindings": {
                identity_name: bindings[identity_name]
                for identity_name in A20_EXPECTED_IDENTITY_NAMES
                if identity_name != successor_binding_name
            },
        }
        bindings[successor_binding_name] = {
            "identity_name": successor_binding_name,
            "row_count": 1,
            "ordered_keyset_sha256": synthetic_identity_digest(
                f"{successor_binding_name}:keyset"
            ),
            "row_domain_sha256": synthetic_identity_digest(
                f"{successor_binding_name}:domain"
            ),
            "arm_status_bindings": statuses,
            "active_identity_bindings_sha256": _sha256(
                canonical_json_bytes(active_binding_preimage)
            ),
            "status": "pass",
        }
        return {
            "schema_version": "a20_evidence_freeze.v1",
            "amendment20_evidence_freeze_status": "pass_a4_exact_freeze",
            **statuses,
            "expected_identity_bindings": bindings,
            "amendment20_ratification_ready": True,
        }

    def rebind_synthetic_successor(freeze: Mapping[str, Any]) -> None:
        statuses = {
            status_member: freeze[status_member]
            for status_member in A20_ARM_IDENTITY_CONTRACTS
        }
        bindings = freeze["expected_identity_bindings"]
        successor_binding_name = "a20_successor_source_binding_identity"
        active_binding_preimage = {
            "arm_status_bindings": statuses,
            "expected_identity_bindings": {
                identity_name: bindings[identity_name]
                for identity_name in A20_EXPECTED_IDENTITY_NAMES
                if identity_name != successor_binding_name
            },
        }
        bindings[successor_binding_name]["arm_status_bindings"] = statuses
        bindings[successor_binding_name]["active_identity_bindings_sha256"] = (
            _sha256(canonical_json_bytes(active_binding_preimage))
        )

    source_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["source_infrastructure"]["semantic_domain_identity_keys"].remove(
        "excluded_source_rows"
    )
    source_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["source_infrastructure"]["evidence_statement_row_keys"].remove(
        "utf8_byte_start"
    )
    source_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["source_infrastructure"][
        "path_rule"
    ] = "machine_local_absolute_path"
    source_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    binding_keys = variant["source_infrastructure"][
        "successor_source_binding_keys"
    ]
    binding_keys[binding_keys.index("missing_reason_rule_set_identity")] = (
        "missing_rule_set_identity"
    )
    source_variants.append(variant)
    reject_manifest_variants(
        source_variants,
        "separate semantic-domain contract drift",
        "Amendment-20 source domain/statement/path attack",
    )
    rejected.append(A20_EXPECTED_MUTATIONS[0])

    missing_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["missing_reason_authority"][
        "formerly_unresolved_literal_occurrence_count"
    ] = 524_537
    missing_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["missing_reason_authority"]["projection_requirements"].remove(
        "collectively_exhaustive"
    )
    missing_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["missing_reason_authority"]["claim_type"] = "integer_coercible"
    missing_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["missing_reason_authority"]["representation_bridge_probe"][
        "bridge_required_before_acceptance"
    ] = False
    missing_variants.append(variant)
    reject_manifest_variants(
        missing_variants,
        "missing-reason authority contract drift",
        "Amendment-20 missing exact-cover/Boolean/MD attack",
    )
    rejected.append(A20_EXPECTED_MUTATIONS[1])

    purpose_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["purpose_authority"][
        "inherited_complete_rows_requiring_source_regrounding"
    ] = 817
    purpose_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["purpose_authority"]["required_disposition_counts"]["U"] = 1
    purpose_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["purpose_authority"][
        "exact_prompt_cover_and_zero_gap_extra_duplicate_overlap_conflict"
    ] = False
    purpose_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["purpose_authority"][
        "purpose_arrays_nonempty_stable_unique_in_official_order"
    ] = False
    purpose_variants.append(variant)
    reject_manifest_variants(
        purpose_variants,
        "purpose-authority totality contract drift",
        "Amendment-20 purpose 818/U/totality attack",
    )
    rejected.append(A20_EXPECTED_MUTATIONS[2])

    prompt_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["prompt_field_semantic_binding"]["c68_regression"][
        "candidate_raw_field_ids"
    ] = ["V11804"]
    prompt_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["prompt_field_semantic_binding"]["collision_census"][
        "multiple_count"
    ] = 45
    prompt_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["prompt_field_semantic_binding"][
        "candidate_disposition_is_iff_count_partition"
    ] = False
    prompt_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["prompt_field_semantic_binding"]["zero_candidate_grouping_probe"][
        "accepted_positive_group_with_empty_reference_union_count"
    ] = 1
    prompt_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["prompt_field_semantic_binding"][
        "required_unresolved_semantic_binding_count"
    ] = 1
    prompt_variants.append(variant)
    reject_manifest_variants(
        prompt_variants,
        "prompt-field or semantic-binding contract drift",
        "Amendment-20 C68/46/zero/semantic attack",
    )
    rejected.append(A20_EXPECTED_MUTATIONS[3])

    r04_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["r04_q5"]["construction_order"][5:7] = reversed(
        variant["r04_q5"]["construction_order"][5:7]
    )
    r04_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["r04_q5"]["normal_era_successor_sequence"].remove(
        "prompt_field_candidate_set_rows"
    )
    r04_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["r04_q5"]["a19_digest_dependency_order_preserved"][0] = "D1"
    r04_variants.append(variant)
    reject_manifest_variants(
        r04_variants,
        "R04 order or Q5 shape contract drift",
        "Amendment-20 order/Q5/D0 attack",
    )
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["source_infrastructure"]["historical_domains_preserved"][
        "a19_build_input_row_count"
    ] = 278
    _expect_law_error(
        lambda: _validate_a20_manifest_contract(variant),
        "separate semantic-domain contract drift",
        "Amendment-20 279-row source-binding attack",
    )
    rejected.append(A20_EXPECTED_MUTATIONS[4])

    _validate_amendment20_r06_collection_binding()
    r06_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["r06_lifecycle"][
        "interpreter_selector"
    ] = "fixed_interpreter_literal_forbidden"
    r06_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["r06_lifecycle"]["test_file_identities"][0]["byte_size"] += 1
    r06_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["r06_lifecycle"]["collected_node_id_count"] = 222
    r06_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["r06_lifecycle"]["dormant_lifecycle_rows"][4][
        "selection_enabled"
    ] = True
    r06_variants.append(variant)
    reject_manifest_variants(
        r06_variants,
        "R06 collection or lifecycle contract drift",
        "Amendment-20 interpreter/file/223/lifecycle attack",
    )
    rejected.append(A20_EXPECTED_MUTATIONS[5])

    valid_verdict = (
        "# RATIFY\n"
        "attested_design_byte_size: 1\n"
        f"attested_design_raw_sha256: {'a' * 64}\n"
        f"attested_design_blob_oid: {'b' * 40}\n"
        "executed_transition_receipt_byte_size: 2\n"
        f"executed_transition_receipt_raw_sha256: {'c' * 64}\n"
        "executed_transition_receipt_schema: executed_transition_state.v2\n"
        "---\n"
    ).encode()
    validate_amendment20_qualifying_verdict(
        valid_verdict,
        design_byte_size=1,
        design_raw_sha256="a" * 64,
        design_blob_oid="b" * 40,
        receipt_byte_size=2,
        receipt_raw_sha256="c" * 64,
    )
    _expect_law_error(
        lambda: validate_amendment20_qualifying_verdict(
            valid_verdict.replace(b"---\n", b"---\r\n"),
            design_byte_size=1,
            design_raw_sha256="a" * 64,
            design_blob_oid="b" * 40,
            receipt_byte_size=2,
            receipt_raw_sha256="c" * 64,
        ),
        "strict UTF-8/LF framing",
        "Amendment-20 verdict grammar attack",
    )
    receipt_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["ratification_receipt"]["receipt_schema"][
        "manifest_schema_version"
    ] = "executed_transition_state.v1"
    receipt_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["ratification_receipt"][
        "amendment20_external_receipt_path"
    ] = "docs/analysis/amendment_20_ratification/receipt.json"
    receipt_variants.append(variant)
    reject_manifest_variants(
        receipt_variants,
        "verdict, receipt, or scratch contract drift",
        "Amendment-20 receipt/fixed-path attack",
    )
    scratch_verdict_paths = A20_RECEIPT_SCHEMA["expected_changed_paths"][:2]
    try:
        _validate_amendment20_scratch_transition_context(
            {
                path: b"forged scratch stand-in\n"
                for path in scratch_verdict_paths
            }
        )
    except LawError:
        pass
    else:
        raise LawError("Amendment-20 live scratch-context attack survived")
    rejected.append(A20_EXPECTED_MUTATIONS[6])

    routing_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["successor_routing"][
        "a19_pin_fallback_for_terminal_a20_permitted"
    ] = True
    routing_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["successor_routing"]["terminal_amendment"] = 19
    routing_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["activation_transition"]["terminal_revision"] = 21
    routing_variants.append(variant)
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["activation_transition"]["ordered_closure_domain"] = list(
        range(13, 20)
    )
    routing_variants.append(variant)
    reject_manifest_variants(
        routing_variants,
        "successor routing or activation contract drift",
        "Amendment-20 pin/terminal/revision/domain attack",
    )
    rejected.append(A20_EXPECTED_MUTATIONS[7])

    original_root = ROOT
    with tempfile.TemporaryDirectory(
        prefix="a20-nonemission-provenance-"
    ) as temporary:
        temporary_root = Path(temporary)
        scratch = temporary_root / "repo"
        _scratch_git(temporary_root, "init", "--quiet", str(scratch))
        _scratch_git(scratch, "config", "user.name", "A20 mutation test")
        _scratch_git(
            scratch,
            "config",
            "user.email",
            "a20-mutation@example.invalid",
        )
        sentinel_path = scratch / "tracked-sentinel.txt"
        sentinel_path.write_bytes(b"authenticated A20 manifest state\n")
        _scratch_git(scratch, "add", "tracked-sentinel.txt")
        _scratch_git(
            scratch,
            "commit",
            "--quiet",
            "-m",
            "Authenticated A20 nonemission control",
        )
        execution_commit = str(
            _scratch_git(scratch, "rev-parse", "HEAD")
        ).strip()
        execution_tree_oid = str(
            _scratch_git(scratch, "rev-parse", "HEAD^{tree}")
        ).strip()
        ROOT = scratch
        try:
            manifest_rows, untracked_paths = (
                _reconstruct_amendment20_repository_manifest(
                    execution_tree_oid,
                    verification_root=scratch,
                )
            )
            _require(
                untracked_paths == ()
                and [row["path"] for row in manifest_rows]
                == ["tracked-sentinel.txt"],
                "Amendment-20 real scratch provenance control drift",
            )
            manifest_sha256 = _sha256(canonical_json_bytes(manifest_rows))
            nonemission_evidence = {
                "execution_commit": execution_commit,
                "execution_tree_oid": execution_tree_oid,
                "repository_manifest_rows_before": copy.deepcopy(
                    manifest_rows
                ),
                "repository_manifest_sha256_before": manifest_sha256,
                "repository_manifest_rows_after": copy.deepcopy(manifest_rows),
                "repository_manifest_sha256_after": manifest_sha256,
                "repository_clean_before": True,
                "repository_clean_after": True,
                "forbidden_outputs_absent_after_execution": True,
            }

            sentinel_path.write_bytes(b"later clean A20 manifest state\n")
            _scratch_git(scratch, "add", "tracked-sentinel.txt")
            _scratch_git(
                scratch,
                "commit",
                "--quiet",
                "-m",
                "Later clean A20 repository state",
            )
            later_commit = str(
                _scratch_git(scratch, "rev-parse", "HEAD")
            ).strip()
            later_tree_oid = str(
                _scratch_git(scratch, "rev-parse", "HEAD^{tree}")
            ).strip()
            worktree_state_before = _scratch_git(
                scratch,
                "worktree",
                "list",
                "--porcelain",
            )
            _require(
                later_commit != execution_commit
                and later_tree_oid != execution_tree_oid
                and sentinel_path.read_bytes()
                != b"authenticated A20 manifest state\n"
                and _scratch_git(
                    scratch,
                    "status",
                    "--porcelain=v1",
                    "-z",
                    text=False,
                )
                == b"",
                "Amendment-20 different-current-tree control drift",
            )

            ready_controls = [
                synthetic_ready_freeze(),
                *[
                    synthetic_ready_freeze(
                        status_member,
                        nonemission_evidence=nonemission_evidence,
                    )
                    for status_member in A20_ARM_IDENTITY_CONTRACTS
                ],
            ]
            for ready_freeze in ready_controls:
                _validate_amendment20_evidence_freeze(
                    ready_freeze,
                    A20_EVIDENCE_FREEZE_CONTRACT,
                    require_ratification_ready=True,
                )
            _require(
                _scratch_git(
                    scratch,
                    "worktree",
                    "list",
                    "--porcelain",
                )
                == worktree_state_before,
                "Amendment-20 verification checkout cleanup drift",
            )

            forged_shadow = synthetic_ready_freeze(
                "missing_reason_authority_status",
                nonemission_evidence=nonemission_evidence,
            )
            forged_shadow["expected_identity_bindings"][
                "missing_reason_failure_shadow_identity"
            ]["shadow_row_domain_sha256"] = ("f" * 64)
            _expect_law_error(
                lambda: _validate_amendment20_evidence_freeze(
                    forged_shadow,
                    A20_EVIDENCE_FREEZE_CONTRACT,
                    require_ratification_ready=True,
                ),
                "failure-shadow cross-binding drift",
                "Amendment-20 forged failure-shadow attack",
            )

            missing_complement = synthetic_ready_freeze(
                "purpose_authority_status",
                nonemission_evidence=nonemission_evidence,
            )
            del missing_complement["expected_identity_bindings"][
                "purpose_failure_shadow_identity"
            ]["complement_identity"]
            _expect_law_error(
                lambda: _validate_amendment20_evidence_freeze(
                    missing_complement,
                    A20_EVIDENCE_FREEZE_CONTRACT,
                    require_ratification_ready=True,
                ),
                "failure shadow keyset drift",
                "Amendment-20 missing nonemission-complement attack",
            )

            status_flip = synthetic_ready_freeze(
                "prompt_field_semantic_binding_status",
                nonemission_evidence=nonemission_evidence,
            )
            status_flip["prompt_field_semantic_binding_status"] = "pass"
            _expect_law_error(
                lambda: _validate_amendment20_evidence_freeze(
                    status_flip,
                    A20_EVIDENCE_FREEZE_CONTRACT,
                    require_ratification_ready=True,
                ),
                "pass carries a failure shadow",
                "Amendment-20 arm-status flip attack",
            )

            truthy_mapping = synthetic_ready_freeze()
            truthy_mapping["expected_identity_bindings"] = {
                name: {"truthy": True} for name in A20_EXPECTED_IDENTITY_NAMES
            }
            _expect_law_error(
                lambda: _validate_amendment20_evidence_freeze(
                    truthy_mapping,
                    A20_EVIDENCE_FREEZE_CONTRACT,
                    require_ratification_ready=True,
                ),
                "identity keyset drift",
                "Amendment-20 truthy-mapping regression attack",
            )
            rejected.append(A20_EXPECTED_MUTATIONS[8])

            coherent_forgery = synthetic_ready_freeze(
                "missing_reason_authority_status",
                nonemission_evidence=nonemission_evidence,
            )
            forged_nonemission = coherent_forgery[
                "expected_identity_bindings"
            ]["missing_reason_failure_shadow_identity"]["nonemission_evidence"]
            forged_nonemission.update(
                {
                    "execution_commit": "4" * 40,
                    "execution_tree_oid": "5" * 40,
                    "repository_manifest_sha256_before": "6" * 64,
                    "repository_manifest_sha256_after": "6" * 64,
                }
            )
            rebind_synthetic_successor(coherent_forgery)
            _require(
                _run_git("cat-file", "-e", f"{'4' * 40}^{{commit}}").returncode
                != 0
                and _run_git(
                    "cat-file", "-e", f"{'5' * 40}^{{tree}}"
                ).returncode
                != 0,
                "Amendment-20 forged object control unexpectedly exists",
            )
            _expect_law_error(
                lambda: _validate_amendment20_evidence_freeze(
                    coherent_forgery,
                    A20_EVIDENCE_FREEZE_CONTRACT,
                    require_ratification_ready=True,
                ),
                "execution commit is not an exact commit object",
                "Amendment-20 coherent nonemission provenance forgery",
            )
            rejected.append(A20_EXPECTED_MUTATIONS[9])
        finally:
            ROOT = original_root

    completed_ontology_variants = []
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["purpose_authority"][
        "source_underdetermined_requires_reconciled_adjudication_ruling"
    ] = False
    completed_ontology_variants.append(
        (
            variant,
            "determined row rewritten without an adjudication ruling",
            A20_EXPECTED_MUTATIONS[10],
        )
    )
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["purpose_authority"][
        "source_underdetermined_is_no_applicable_purpose"
    ] = True
    completed_ontology_variants.append(
        (
            variant,
            "source-underdetermined/no-applicable-purpose conflation",
            A20_EXPECTED_MUTATIONS[11],
        )
    )
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    variant["purpose_authority"][
        "source_underdetermined_count_a4_freeze_slot"
    ] = 1
    completed_ontology_variants.append(
        (
            variant,
            "underdetermined census disagreement with the A4 binding",
            A20_EXPECTED_MUTATIONS[12],
        )
    )
    variant = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    del variant["purpose_authority"]["required_disposition_counts"][
        "source_underdetermined"
    ]
    completed_ontology_variants.append(
        (
            variant,
            "completed disposition object missing the new arm",
            A20_EXPECTED_MUTATIONS[13],
        )
    )
    for variant, label, mutation_name in completed_ontology_variants:
        _expect_law_error(
            lambda variant=variant: _validate_a20_manifest_contract(variant),
            "purpose-authority totality contract drift",
            f"Amendment-20 {label}",
        )
        rejected.append(mutation_name)

    collapsed_span = copy.deepcopy(A20_NORMATIVE_MANIFEST)
    collapsed_span["prompt_field_semantic_binding"][
        "coordinate_distinct_span_collapse_aborts"
    ] = False
    _expect_law_error(
        lambda: _validate_a20_manifest_contract(collapsed_span),
        "prompt-field or semantic-binding contract drift",
        "Amendment-20 coordinate-distinct questionnaire spans collapsed",
    )
    rejected.append(A20_EXPECTED_MUTATIONS[14])

    rejected_tuple = tuple(rejected)
    rejected_raw = canonical_json_bytes(list(rejected_tuple))
    _require(
        rejected_tuple == A20_EXPECTED_MUTATIONS
        and len(rejected_raw) == A20_MUTATION_DOMAIN_BYTE_SIZE
        and _sha256(rejected_raw) == A20_MUTATION_DOMAIN_SHA256,
        "Amendment-20 mutation inventory execution drift",
    )
    return rejected_tuple


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
