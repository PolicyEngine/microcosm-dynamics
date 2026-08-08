"""Validate Amendment 13's prospective tier-2 execution law.

This module emits no authority and writes no artifact.  It reconstructs the
proposed repair overlays from the six pinned stage-2 source seals, checks the
historical Amendment-12 ratification blob, and exercises Amendment 13's own
adversarial mutation inventory.  Amendment 12's frozen pilot bundle and its
71 mutations are deliberately not changed.
"""

from __future__ import annotations

import argparse
import ast
import base64
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

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
TRUSTED_RECORDING_MANIFEST_IDENTITY_SCHEMA_VERSION = (
    "amendment_13_dual_ratify_recording_manifest_identity.v1"
)
TRUSTED_RECORDING_MANIFEST_SCHEMA_VERSION = (
    "amendment_13_dual_ratify_recording_manifest.v1"
)
TRUSTED_RECORDING_MANIFEST_STATUS = (
    "INDEPENDENTLY_AUTHENTICATED_DUAL_RATIFY_RECORDING_MANIFEST"
)
TRUSTED_RECORDING_MANIFEST_PATH = (
    "docs/analysis/amendment_13_ratification/"
    "dual_ratify_recording_manifest_v1.json"
)
TRUSTED_REVIEWER_REGISTRY_IDENTITY_SCHEMA_VERSION = (
    "amendment_13_reviewer_key_registry_identity.v1"
)
TRUSTED_REVIEWER_REGISTRY_SCHEMA_VERSION = (
    "amendment_13_reviewer_key_registry.v1"
)
TRUSTED_REVIEWER_REGISTRY_STATUS = (
    "INDEPENDENTLY_AUTHENTICATED_PRE_CANDIDATE_REVIEWER_KEYS"
)
TRUSTED_REVIEWER_REGISTRY_PATH = (
    "docs/analysis/amendment_13_ratification/"
    "trusted_reviewer_key_registry_v1.json"
)
RATIFY_SIGNATURE_NAMESPACE = "policyengine-amendment13-ratify-v1"
ENROLLMENT_SIGNATURE_NAMESPACE = (
    "policyengine-amendment13-reviewer-enrollment-v1"
)
A13_DRAFT_AUTHOR_IDENTITY = "amendment-13-draft-author:max-ghenis"
# The authenticated implementation commit, not these live module attributes,
# is the production source of truth.  Its three literal None markers record
# that the immutable revision-14 prefix and the two Amendment-12 verdict bytes
# contain no cryptographic reviewer credential.  A separately ratified
# successor implementation must introduce an externally authenticated,
# pre-draft certifier root before the public path can become available.
PINNED_A13_EXTERNAL_CERTIFIER_ROOT_IDENTITY: Mapping[str, Any] | None = None
PINNED_A13_ENROLLMENT_AUTHORITY_ROOT_IDENTITY: Mapping[str, Any] | None = None
PINNED_A13_REVIEWER_REGISTRY_IDENTITY: Mapping[str, Any] | None = None
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
    "dual_ratify_records_coherently_self_minted",
    "reviewer_registry_two_keys_one_actor_self_enrolled",
    "enacted_identifier_absent_from_qualified_inventory",
    "git_replace_refs_substitute_parent_and_changed_paths",
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
A13_AUTHENTICATION_SCHEMA_LITERALS = (
    TRUSTED_REVIEWER_REGISTRY_IDENTITY_SCHEMA_VERSION,
    TRUSTED_REVIEWER_REGISTRY_SCHEMA_VERSION,
    TRUSTED_RECORDING_MANIFEST_IDENTITY_SCHEMA_VERSION,
    TRUSTED_RECORDING_MANIFEST_SCHEMA_VERSION,
)
A13_AUTHENTICATION_STATUS_LITERALS = (
    TRUSTED_REVIEWER_REGISTRY_STATUS,
    TRUSTED_RECORDING_MANIFEST_STATUS,
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
A13_TRUSTED_RECORDING_LITERALS = (
    TRUSTED_REVIEWER_REGISTRY_IDENTITY_SCHEMA_VERSION,
    TRUSTED_REVIEWER_REGISTRY_SCHEMA_VERSION,
    TRUSTED_REVIEWER_REGISTRY_STATUS,
    TRUSTED_REVIEWER_REGISTRY_PATH,
    TRUSTED_RECORDING_MANIFEST_IDENTITY_SCHEMA_VERSION,
    TRUSTED_RECORDING_MANIFEST_SCHEMA_VERSION,
    TRUSTED_RECORDING_MANIFEST_STATUS,
    TRUSTED_RECORDING_MANIFEST_PATH,
    "reviewer_identity",
    "ssh-ed25519",
    RATIFY_SIGNATURE_NAMESPACE,
    ENROLLMENT_SIGNATURE_NAMESPACE,
    A13_DRAFT_AUTHOR_IDENTITY,
    "git --no-replace-objects",
    "GIT_NO_REPLACE_OBJECTS=1",
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
    """Decode the exact suffix and split its uniquely ordered major sections."""

    _require(
        raw.endswith(b"\n")
        and len(raw) > DESIGN_BYTE_SIZE
        and _sha256(raw[:DESIGN_BYTE_SIZE]) == DESIGN_SHA256
        and raw[DESIGN_BYTE_SIZE:].startswith(AMENDMENT13_BOUNDARY),
        "governing Amendment-13 document violates immutable-prefix law",
    )
    try:
        text = raw.decode("utf-8")
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
    """Parse the primary historical and prospective recording declarations."""

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
    _require(
        governing_match is not None,
        "governing Amendment-13 primary schema/status drift",
    )
    draft_match = re.search(
        r"values `([^`]+)`,\n`([^`]+)`, and false\.",
        section,
    )
    _require(
        draft_match is not None,
        "governing Amendment-13 draft placeholder values drift",
    )
    history_match = re.search(
        r"object has exactly\n`changed_path_count: (\d+)` and\n"
        r"`commit_path_shape_is_identity_condition: (true|false)`\.",
        section,
    )
    _require(
        history_match is not None,
        "historical changed-path observation drift",
    )
    amendment12_attestation_keys = _code_tokens_between(
        section,
        "Each `dual_ratify_attestations` member has exactly ",
        ". The candidate HEAD",
        7,
        "Amendment-12 attestation keys",
    )
    manifest_status_match = re.search(
        r"The manifest object has\nexactly .*?\. Its exact\nstatus is\n"
        r"`([^`]+)`\.",
        section,
        flags=re.DOTALL,
    )
    _require(
        manifest_status_match is not None,
        "trusted recording manifest primary status drift",
    )
    registry_match = re.search(
        r"has exact canonical schema\n`([^`]+)`, exact status\n"
        r"`([^`]+)`, and path\n`([^`]+)`\.",
        section,
    )
    _require(
        registry_match is not None,
        "trusted reviewer registry primary identity drift",
    )
    recording_manifest_match = re.search(
        r"The manifest object's\nschema is `([^`]+)` and its path is\n"
        r"`([^`]+)`\.",
        section,
    )
    _require(
        recording_manifest_match is not None,
        "recording manifest primary schema/path drift",
    )
    bound_status_match = re.search(
        r"use fixture status\n`([^`]+)`, keep both authority",
        section,
    )
    _require(
        bound_status_match is not None,
        "ratification-bound template status drift",
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
        "amendment12_attestation_keys": amendment12_attestation_keys,
        "ratification_history_observation": {
            "changed_path_count": int(history_match.group(1)),
            "commit_path_shape_is_identity_condition": (
                history_match.group(2) == "true"
            ),
        },
        "governing_identity_schema_version": governing_match.group(1),
        "governing_identity_status": governing_match.group(2),
        "governing_identity_keys": _code_tokens_between(
            section,
            governing_match.group(0),
            ".\n`ratification_parents`",
            13,
            "governing Amendment-13 identity keys",
        ),
        "trusted_registry_identity_keys": _code_tokens_between(
            section,
            "`trusted_reviewer_registry_identity` has exactly ",
            ". Its schema is\n",
            8,
            "trusted reviewer registry identity keys",
        ),
        "trusted_registry_identity_schema_version": _code_after(
            section,
            ". Its schema is\n",
            "trusted reviewer registry identity schema",
        ),
        "trusted_registry_schema_version": registry_match.group(1),
        "trusted_registry_status": registry_match.group(2),
        "trusted_registry_path": registry_match.group(3),
        "trusted_registry_keys": _code_tokens_between(
            section,
            "The registry object has\nexactly ",
            ".\n\nThere are exactly two ordered reviewer rows.",
            9,
            "trusted reviewer registry keys",
        ),
        "trusted_reviewer_keys": _code_tokens_between(
            section,
            "There are exactly two ordered reviewer rows. Each has exactly\n",
            ". Each key is an\nEd25519",
            7,
            "trusted reviewer keys",
        ),
        "trusted_enrollment_authority_keys": _code_tokens_between(
            section,
            "Each enrollment-authority row has exactly\n",
            ". The ordered\n`prior_record_name`",
            6,
            "trusted enrollment-authority keys",
        ),
        "trusted_enrollment_authorization_keys": _code_tokens_between(
            section,
            "Each authorization row has exactly\n",
            ". Each `authorization_preimage`",
            6,
            "trusted enrollment-authorization keys",
        ),
        "trusted_enrollment_authorization_preimage_keys": (
            _code_tokens_between(
                section,
                "Each `authorization_preimage` has exactly\n",
                ". The last two values",
                12,
                "trusted enrollment-authorization preimage keys",
            )
        ),
        "enrollment_signature_namespace": _code_after(
            section,
            "including its terminal LF, is signed under enrollment "
            "signature namespace\n",
            "trusted enrollment signature namespace",
        ),
        "recording_manifest_identity_keys": _code_tokens_between(
            section,
            "`recording_manifest_identity` has exactly ",
            ". Its schema\nis ",
            8,
            "recording manifest identity keys",
        ),
        "recording_manifest_identity_schema_version": _code_after(
            section,
            ". Its schema\nis ",
            "recording manifest identity schema",
        ),
        "trusted_manifest_schema_version": recording_manifest_match.group(1),
        "trusted_manifest_path": recording_manifest_match.group(2),
        "trusted_manifest_keys": _code_tokens_between(
            section,
            "The manifest object has\nexactly ",
            ". Its exact\nstatus is",
            12,
            "recording manifest keys",
        ),
        "trusted_manifest_status": manifest_status_match.group(1),
        "governing_attestation_keys": _code_tokens_between(
            section,
            "Each of the exactly two attestation objects has exactly ",
            ". It has verdict token ",
            13,
            "governing Amendment-13 attestation keys",
        ),
        "record_template": _fenced_lines_after(
            section,
            "terminal LF and no additional line, under this seven-line template:\n\n",
            "governing Amendment-13 RATIFY record template",
        ),
        "trusted_recording_literals": _fenced_lines_after(
            section,
            "The exact trusted-recording validation literals are:\n\n",
            "Amendment-13 trusted recording literals",
        ),
        "authentication_schema_literals": _fenced_lines_after(
            section,
            "The exact\nauthentication schema-version inventory is:\n\n",
            "Amendment-13 authentication schema literals",
        ),
        "authentication_status_literals": _fenced_lines_after(
            section,
            "The exact authentication status inventory is:\n\n",
            "Amendment-13 authentication status literals",
        ),
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
    for row, finding_code in zip(rows, selector):
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
        "implementation_pins": _parse_implementation_pins(section),
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


_IMPLEMENTATION_PIN_PATTERN = re.compile(
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
_IMPLEMENTATION_PIN_VALUE_GROUPS = (
    "commit",
    "mode",
    "validator_blob",
    "validator_size",
    "validator_sha256",
    "test_blob",
    "test_size",
    "test_sha256",
)


def _implementation_pin_match(section: str) -> re.Match[str]:
    matches = list(_IMPLEMENTATION_PIN_PATTERN.finditer(section))
    _require(
        len(matches) == 1,
        "Amendment-13 implementation pin block grammar drift",
    )
    return matches[0]


def _parse_implementation_pins(section: str) -> dict[str, Any]:
    match = _implementation_pin_match(section)
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


def _normalize_implementation_pin_values(section: str) -> str:
    """Normalize only the eight independently authenticated pin values."""

    match = _implementation_pin_match(section)
    parts: list[str] = []
    cursor = 0
    for group in _IMPLEMENTATION_PIN_VALUE_GROUPS:
        start, end = match.span(group)
        _require(start >= cursor, "implementation pin capture ordering drift")
        parts.extend((section[cursor:start], f"<{group.upper()}>"))
        cursor = end
    parts.append(section[cursor:])
    return "".join(parts)


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
            semantic_text = _normalize_implementation_pin_values(semantic_text)
        result[section_name] = _sha256(semantic_text.encode("utf-8"))
    return result


def _validate_identifier_inventory_consistency(
    projection: Mapping[str, Any],
) -> None:
    """Require §27.2 authentication identifiers to close §27.8.3 exactly."""

    identity = projection["identity"]
    comparator = projection["comparator"]
    authentication_schemas = identity["authentication_schema_literals"]
    authentication_statuses = identity["authentication_status_literals"]
    execution_schemas = comparator["schema_literals"]
    execution_statuses = comparator["status_relation_operation_codes"]
    trusted_literals = identity["trusted_recording_literals"]
    enacted_schemas = {
        identity["governing_identity_schema_version"],
        identity["draft_placeholder_values"][0],
        identity["trusted_registry_identity_schema_version"],
        identity["trusted_registry_schema_version"],
        identity["recording_manifest_identity_schema_version"],
        identity["trusted_manifest_schema_version"],
    }
    enacted_statuses = {
        identity["governing_identity_status"],
        identity["draft_placeholder_values"][1],
        identity["ratification_bound_template_status"],
        identity["trusted_registry_status"],
        identity["trusted_manifest_status"],
    }
    _require(
        tuple(authentication_schemas) == A13_AUTHENTICATION_SCHEMA_LITERALS
        and tuple(authentication_statuses)
        == A13_AUTHENTICATION_STATUS_LITERALS
        and len(execution_schemas) == len(set(execution_schemas))
        and len(execution_statuses) == len(set(execution_statuses))
        and len(authentication_schemas) == len(set(authentication_schemas))
        and len(authentication_statuses) == len(set(authentication_statuses))
        and set(authentication_schemas).isdisjoint(execution_schemas)
        and set(authentication_statuses).isdisjoint(execution_statuses)
        and set(authentication_schemas).issubset(trusted_literals)
        and set(authentication_statuses).issubset(trusted_literals)
        and enacted_schemas - set(execution_schemas)
        == set(authentication_schemas)
        and enacted_statuses - set(execution_statuses)
        == set(authentication_statuses),
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
        "governing_identity_schema_version": (
            GOVERNING_A13_IDENTITY_SCHEMA_VERSION
        ),
        "governing_identity_status": GOVERNING_A13_IDENTITY_STATUS,
        "governing_identity_keys": [
            "schema_version",
            "status",
            "ratification_commit",
            "ratification_parents",
            "ratification_commit_changed_paths",
            "document_path",
            "document_mode",
            "document_blob_oid",
            "document_byte_size",
            "document_sha256",
            "trusted_reviewer_registry_identity",
            "recording_manifest_identity",
            "dual_ratify_attestations",
        ],
        "trusted_registry_identity_keys": [
            "schema_version",
            "registry_commit",
            "registry_parents",
            "registry_path",
            "registry_mode",
            "registry_blob_oid",
            "registry_byte_size",
            "registry_sha256",
        ],
        "trusted_registry_identity_schema_version": (
            TRUSTED_REVIEWER_REGISTRY_IDENTITY_SCHEMA_VERSION
        ),
        "trusted_registry_schema_version": (
            TRUSTED_REVIEWER_REGISTRY_SCHEMA_VERSION
        ),
        "trusted_registry_status": TRUSTED_REVIEWER_REGISTRY_STATUS,
        "trusted_registry_path": TRUSTED_REVIEWER_REGISTRY_PATH,
        "trusted_registry_keys": [
            "schema_version",
            "status",
            "signature_namespace",
            "enrollment_signature_namespace",
            "trusted_enrollment_authority_domain_sha256",
            "ordered_reviewers",
            "reviewer_domain_sha256",
            "ordered_enrollment_authorizations",
            "enrollment_authorization_domain_sha256",
        ],
        "trusted_reviewer_keys": [
            "reviewer_identity",
            "record_name",
            "record_path",
            "signature_path",
            "ssh_principal",
            "ssh_public_key",
            "ssh_key_fingerprint",
        ],
        "trusted_enrollment_authority_keys": [
            "authority_identity",
            "prior_record_name",
            "prior_record_raw_sha256",
            "ssh_principal",
            "ssh_public_key",
            "ssh_key_fingerprint",
        ],
        "trusted_enrollment_authorization_keys": [
            "authority_identity",
            "authority_ssh_key_fingerprint",
            "authorization_preimage",
            "signature_byte_size",
            "signature_sha256",
            "signature_base64",
        ],
        "trusted_enrollment_authorization_preimage_keys": [
            "authority_identity",
            "prior_record_name",
            "prior_record_raw_sha256",
            "registry_parent_commit",
            "registry_path",
            "reviewer_position",
            "reviewer_identity",
            "reviewer_row_sha256",
            "reviewer_domain_sha256",
            "trusted_enrollment_authority_domain_sha256",
            "draft_author_identity",
            "reviewer_independent_of_draft_author",
        ],
        "enrollment_signature_namespace": ENROLLMENT_SIGNATURE_NAMESPACE,
        "recording_manifest_identity_keys": [
            "schema_version",
            "manifest_commit",
            "manifest_parents",
            "manifest_path",
            "manifest_mode",
            "manifest_blob_oid",
            "manifest_byte_size",
            "manifest_sha256",
        ],
        "recording_manifest_identity_schema_version": (
            TRUSTED_RECORDING_MANIFEST_IDENTITY_SCHEMA_VERSION
        ),
        "trusted_manifest_schema_version": (
            TRUSTED_RECORDING_MANIFEST_SCHEMA_VERSION
        ),
        "trusted_manifest_path": TRUSTED_RECORDING_MANIFEST_PATH,
        "trusted_manifest_keys": [
            "schema_version",
            "status",
            "attested_candidate_head",
            "document_path",
            "document_mode",
            "document_blob_oid",
            "document_byte_size",
            "document_sha256",
            "trusted_reviewer_registry_identity",
            "ordered_reviewer_identities",
            "ordered_ratify_attestations",
            "attestation_domain_sha256",
        ],
        "trusted_manifest_status": TRUSTED_RECORDING_MANIFEST_STATUS,
        "governing_attestation_keys": [
            "reviewer_identity",
            "record_name",
            "record_path",
            "signature_path",
            "raw_byte_size",
            "raw_sha256",
            "signature_byte_size",
            "signature_sha256",
            "ssh_key_fingerprint",
            "verdict_token",
            "attested_candidate_head",
            "attested_document_byte_size",
            "attested_document_sha256",
        ],
        "record_template": [
            "# RATIFY",
            "reviewer_identity: <exact trusted reviewer identity>",
            "record_name: <exact record_name>",
            "attested_candidate_head: <exact 40-lowercase-hex commit>",
            f"attested_document_path: {DESIGN_PATH}",
            "attested_document_byte_size: <exact decimal byte count>",
            "attested_document_sha256: <exact 64-lowercase-hex SHA-256>",
        ],
        "trusted_recording_literals": list(A13_TRUSTED_RECORDING_LITERALS),
        "authentication_schema_literals": list(
            A13_AUTHENTICATION_SCHEMA_LITERALS
        ),
        "authentication_status_literals": list(
            A13_AUTHENTICATION_STATUS_LITERALS
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
            for row, prospective_id in zip(era_rows, PROSPECTIVE_ERA_SEAL_IDS)
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
        "enforcement_mutations": list(A13_ENFORCEMENT_EXPECTED_MUTATIONS),
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
    }


def _verify_implementation_pins(pins: Mapping[str, Any]) -> None:
    """Authenticate the two document-selected implementation byte identities."""

    _require(
        pins["mode"] == DESIGN_MODE
        and [row["path"] for row in pins["files"]]
        == [
            "scripts/validate_amendment13_execution_law.py",
            "tests/test_validate_amendment13_execution_law.py",
        ],
        "Amendment-13 implementation pin domain drift",
    )
    commit = pins["commit"]
    _require_exact_commit_object(commit, "Amendment-13 implementation commit")
    for row in pins["files"]:
        tree_line = str(
            _git("ls-tree", commit, "--", row["path"], text=True)
        ).strip()
        _require(
            tree_line
            == f"{pins['mode']} blob {row['blob_oid']}\t{row['path']}",
            "Amendment-13 implementation tree-entry pin drift",
        )
        raw = _git("show", f"{commit}:{row['path']}")
        _require(
            isinstance(raw, bytes)
            and len(raw) == row["byte_size"]
            and _sha256(raw) == row["sha256"]
            and hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest()
            == row["blob_oid"]
            and (ROOT / row["path"]).read_bytes() == raw,
            "Amendment-13 running implementation differs from document pin",
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
    _require(
        projection == expected,
        "governing Amendment-13 document semantic projection drift",
    )
    _verify_implementation_pins(projection["scope"]["implementation_pins"])
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


def _load_canonical_git_json(
    commit: str,
    path: str,
    label: str,
) -> dict[str, Any]:
    raw = _git("show", f"{commit}:{path}")
    _require(isinstance(raw, bytes), f"{label} read was not raw bytes")
    try:
        value = a12.strict_json_loads(raw, label)
    except a12.BuildError as error:
        raise LawError(f"{label} is invalid") from error
    _require(
        isinstance(value, dict) and raw == canonical_json_bytes(value),
        f"{label} is not canonical",
    )
    return value


_PINNED_PRODUCTION_TRUST_MARKER_NAMES = (
    "PINNED_A13_EXTERNAL_CERTIFIER_ROOT_IDENTITY",
    "PINNED_A13_ENROLLMENT_AUTHORITY_ROOT_IDENTITY",
    "PINNED_A13_REVIEWER_REGISTRY_IDENTITY",
)


def _literal_module_assignment(raw_source: bytes, name: str) -> Any:
    """Read one literal assignment without executing implementation bytes."""

    try:
        module = ast.parse(raw_source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as error:
        raise LawError(
            "authenticated Amendment-13 implementation is not parseable"
        ) from error
    values: list[ast.expr | None] = []
    for statement in module.body:
        if (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == name
        ):
            values.append(statement.value)
        elif isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in statement.targets
        ):
            values.append(statement.value)
    _require(
        len(values) == 1 and values[0] is not None,
        f"authenticated implementation trust marker drift: {name}",
    )
    try:
        return ast.literal_eval(values[0])
    except (ValueError, TypeError) as error:
        raise LawError(
            f"authenticated implementation trust marker is not literal: {name}"
        ) from error


def _authenticated_production_trust_markers(
    governing_identity: Mapping[str, Any],
) -> tuple[Any, Any, Any]:
    """Derive production enrollment state only from authenticated P bytes."""

    commit = governing_identity.get("ratification_commit")
    path = governing_identity.get("document_path")
    _require(
        _is_lower_hex(commit, 40) and path == DESIGN_PATH,
        "governing Amendment-13 identity cannot select trust state",
    )
    raw_document = _git("show", f"{commit}:{DESIGN_PATH}")
    _require(
        isinstance(raw_document, bytes),
        "governing Amendment-13 trust document read was not raw bytes",
    )
    pins = _parse_implementation_pins(_a13_sections(raw_document)["27.7"])
    _verify_implementation_pins(pins)
    implementation_path = "scripts/validate_amendment13_execution_law.py"
    raw_implementation = _git(
        "show", f"{pins['commit']}:{implementation_path}"
    )
    _require(
        isinstance(raw_implementation, bytes),
        "authenticated Amendment-13 implementation read was not raw bytes",
    )
    return tuple(
        _literal_module_assignment(raw_implementation, name)
        for name in _PINNED_PRODUCTION_TRUST_MARKER_NAMES
    )


def _load_trusted_reviewer_registry(
    governing_identity: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    tuple[dict[str, Any], ...],
]:
    """Fail closed until a successor law authenticates an external root."""

    certifier_root, authority_root, registry_identity = (
        _authenticated_production_trust_markers(governing_identity)
    )
    _require(
        certifier_root is not None
        and authority_root is not None
        and registry_identity is not None,
        "externally authenticated Amendment-13 reviewer root is unavailable",
    )
    raise LawError(
        "nonempty Amendment-13 reviewer roots require a separately ratified "
        "successor implementation"
    )


def _ssh_public_key_fingerprint(public_key: Any) -> str:
    _require(
        isinstance(public_key, str)
        and "\r" not in public_key
        and "\n" not in public_key,
        "trusted reviewer SSH public key is malformed",
    )
    parts = public_key.split()
    _require(
        len(parts) >= 2 and parts[0] == "ssh-ed25519",
        "trusted reviewer key is not Ed25519",
    )
    try:
        raw_key = base64.b64decode(parts[1], validate=True)
    except (ValueError, TypeError) as error:
        raise LawError(
            "trusted reviewer SSH public key is malformed"
        ) from error
    digest = base64.b64encode(hashlib.sha256(raw_key).digest()).decode("ascii")
    return f"SHA256:{digest.rstrip('=')}"


def _validate_enrollment_authorities(
    authorities: Sequence[Mapping[str, Any]],
) -> None:
    """Validate the fixed identities that may authorize reviewer enrollment."""

    _require(
        isinstance(authorities, (list, tuple)) and len(authorities) == 2,
        "trusted Amendment-13 enrollment authority root drift",
    )
    for authority, prior_record in zip(authorities, RATIFY_ATTESTATIONS):
        _require_exact_keys(
            authority,
            {
                "authority_identity",
                "prior_record_name",
                "prior_record_raw_sha256",
                "ssh_principal",
                "ssh_public_key",
                "ssh_key_fingerprint",
            },
            "trusted Amendment-13 enrollment authority",
        )
        for key in ("authority_identity", "ssh_principal"):
            _require(
                isinstance(authority[key], str)
                and bool(authority[key])
                and "\r" not in authority[key]
                and "\n" not in authority[key],
                f"trusted enrollment authority {key} is malformed",
            )
        _require(
            authority["authority_identity"] != A13_DRAFT_AUTHOR_IDENTITY
            and authority["prior_record_name"] == prior_record["record_name"]
            and authority["prior_record_raw_sha256"]
            == prior_record["raw_sha256"]
            and authority["ssh_key_fingerprint"]
            == _ssh_public_key_fingerprint(authority["ssh_public_key"]),
            "trusted Amendment-13 enrollment authority identity drift",
        )
    for key in (
        "authority_identity",
        "prior_record_name",
        "prior_record_raw_sha256",
        "ssh_principal",
        "ssh_public_key",
        "ssh_key_fingerprint",
    ):
        _require(
            len({row[key] for row in authorities}) == 2,
            f"trusted enrollment authority {key} values are not distinct",
        )


def _validate_trusted_reviewer_registry(
    registry_identity: Mapping[str, Any],
    registry: Mapping[str, Any],
    enrollment_authorities: Sequence[Mapping[str, Any]],
    *,
    verify_git: bool,
) -> None:
    """Authenticate the two reviewer identities and their signing keys."""

    _validate_enrollment_authorities(enrollment_authorities)
    _require_exact_keys(
        registry_identity,
        {
            "schema_version",
            "registry_commit",
            "registry_parents",
            "registry_path",
            "registry_mode",
            "registry_blob_oid",
            "registry_byte_size",
            "registry_sha256",
        },
        "trusted Amendment-13 reviewer registry identity",
    )
    _require(
        registry_identity["schema_version"]
        == TRUSTED_REVIEWER_REGISTRY_IDENTITY_SCHEMA_VERSION
        and _is_lower_hex(registry_identity["registry_commit"], 40)
        and isinstance(registry_identity["registry_parents"], list)
        and len(registry_identity["registry_parents"]) == 1
        and _is_lower_hex(registry_identity["registry_parents"][0], 40)
        and registry_identity["registry_path"]
        == TRUSTED_REVIEWER_REGISTRY_PATH
        and registry_identity["registry_mode"] == DESIGN_MODE
        and _is_lower_hex(registry_identity["registry_blob_oid"], 40)
        and isinstance(registry_identity["registry_byte_size"], int)
        and not isinstance(registry_identity["registry_byte_size"], bool)
        and registry_identity["registry_byte_size"] > 0
        and _is_lower_hex(registry_identity["registry_sha256"], 64),
        "trusted Amendment-13 reviewer registry identity drift",
    )
    _require_exact_keys(
        registry,
        {
            "schema_version",
            "status",
            "signature_namespace",
            "enrollment_signature_namespace",
            "trusted_enrollment_authority_domain_sha256",
            "ordered_reviewers",
            "reviewer_domain_sha256",
            "ordered_enrollment_authorizations",
            "enrollment_authorization_domain_sha256",
        },
        "trusted Amendment-13 reviewer registry",
    )
    reviewers = registry["ordered_reviewers"]
    authorizations = registry["ordered_enrollment_authorizations"]
    authority_domain_sha256 = _domain_sha(
        [dict(row) for row in enrollment_authorities]
    )
    _require(
        registry["schema_version"] == TRUSTED_REVIEWER_REGISTRY_SCHEMA_VERSION
        and registry["status"] == TRUSTED_REVIEWER_REGISTRY_STATUS
        and registry["signature_namespace"] == RATIFY_SIGNATURE_NAMESPACE
        and registry["enrollment_signature_namespace"]
        == ENROLLMENT_SIGNATURE_NAMESPACE
        and registry["trusted_enrollment_authority_domain_sha256"]
        == authority_domain_sha256
        and isinstance(reviewers, list)
        and len(reviewers) == 2
        and registry["reviewer_domain_sha256"] == _domain_sha(reviewers),
        "trusted Amendment-13 reviewer registry drift",
    )
    for reviewer in reviewers:
        _require_exact_keys(
            reviewer,
            {
                "reviewer_identity",
                "record_name",
                "record_path",
                "signature_path",
                "ssh_principal",
                "ssh_public_key",
                "ssh_key_fingerprint",
            },
            "trusted Amendment-13 reviewer",
        )
        for key in (
            "reviewer_identity",
            "record_name",
            "record_path",
            "signature_path",
            "ssh_principal",
        ):
            _require(
                isinstance(reviewer[key], str)
                and bool(reviewer[key])
                and "\r" not in reviewer[key]
                and "\n" not in reviewer[key],
                f"trusted reviewer {key} is malformed",
            )
        _require(
            reviewer["record_path"]
            == (
                "docs/analysis/amendment_13_ratification/records/"
                f"{reviewer['record_name']}"
            )
            and reviewer["signature_path"] == f"{reviewer['record_path']}.sig"
            and reviewer["ssh_key_fingerprint"]
            == _ssh_public_key_fingerprint(reviewer["ssh_public_key"]),
            "trusted reviewer path or SSH-key identity drift",
        )
    for key in (
        "reviewer_identity",
        "record_name",
        "record_path",
        "signature_path",
        "ssh_principal",
        "ssh_public_key",
        "ssh_key_fingerprint",
    ):
        _require(
            len({row[key] for row in reviewers}) == 2,
            f"trusted reviewer {key} values are not distinct",
        )
    _require(
        [row["reviewer_identity"] for row in reviewers]
        == [row["authority_identity"] for row in enrollment_authorities],
        "trusted reviewer identities are not externally anchored",
    )
    _require(
        isinstance(authorizations, list)
        and len(authorizations) == 2
        and registry["enrollment_authorization_domain_sha256"]
        == _domain_sha(authorizations),
        "trusted reviewer enrollment authorization domain drift",
    )
    reviewer_domain_sha256 = registry["reviewer_domain_sha256"]
    for position, (authorization, authority, reviewer) in enumerate(
        zip(authorizations, enrollment_authorities, reviewers),
        start=1,
    ):
        _require_exact_keys(
            authorization,
            {
                "authority_identity",
                "authority_ssh_key_fingerprint",
                "authorization_preimage",
                "signature_byte_size",
                "signature_sha256",
                "signature_base64",
            },
            "trusted reviewer enrollment authorization",
        )
        preimage = authorization["authorization_preimage"]
        _require(
            isinstance(preimage, Mapping),
            "trusted reviewer enrollment authorization preimage drift",
        )
        _require_exact_keys(
            preimage,
            {
                "authority_identity",
                "prior_record_name",
                "prior_record_raw_sha256",
                "registry_parent_commit",
                "registry_path",
                "reviewer_position",
                "reviewer_identity",
                "reviewer_row_sha256",
                "reviewer_domain_sha256",
                "trusted_enrollment_authority_domain_sha256",
                "draft_author_identity",
                "reviewer_independent_of_draft_author",
            },
            "trusted reviewer enrollment authorization preimage",
        )
        expected_preimage = {
            "authority_identity": authority["authority_identity"],
            "prior_record_name": authority["prior_record_name"],
            "prior_record_raw_sha256": authority["prior_record_raw_sha256"],
            "registry_parent_commit": registry_identity["registry_parents"][0],
            "registry_path": TRUSTED_REVIEWER_REGISTRY_PATH,
            "reviewer_position": position,
            "reviewer_identity": reviewer["reviewer_identity"],
            "reviewer_row_sha256": _sha256(canonical_json_bytes(reviewer)),
            "reviewer_domain_sha256": reviewer_domain_sha256,
            "trusted_enrollment_authority_domain_sha256": (
                authority_domain_sha256
            ),
            "draft_author_identity": A13_DRAFT_AUTHOR_IDENTITY,
            "reviewer_independent_of_draft_author": True,
        }
        _require(
            dict(preimage) == expected_preimage
            and authorization["authority_identity"]
            == authority["authority_identity"]
            and authorization["authority_ssh_key_fingerprint"]
            == authority["ssh_key_fingerprint"]
            and isinstance(authorization["signature_byte_size"], int)
            and not isinstance(authorization["signature_byte_size"], bool)
            and authorization["signature_byte_size"] > 0
            and _is_lower_hex(authorization["signature_sha256"], 64)
            and isinstance(authorization["signature_base64"], str),
            "trusted reviewer enrollment authorization drift",
        )
        try:
            raw_signature = base64.b64decode(
                authorization["signature_base64"], validate=True
            )
        except (ValueError, TypeError) as error:
            raise LawError(
                "trusted reviewer enrollment signature base64 drift"
            ) from error
        _require(
            base64.b64encode(raw_signature).decode("ascii")
            == authorization["signature_base64"]
            and len(raw_signature) == authorization["signature_byte_size"]
            and _sha256(raw_signature) == authorization["signature_sha256"],
            "trusted reviewer enrollment signature bytes drift",
        )
        _verify_ssh_signature(
            canonical_json_bytes(expected_preimage),
            raw_signature,
            authority,
            namespace=ENROLLMENT_SIGNATURE_NAMESPACE,
            label="reviewer enrollment authorization",
        )
    if not verify_git:
        return
    commit = registry_identity["registry_commit"]
    _require_exact_commit_object(
        commit, "trusted Amendment-13 reviewer registry commit"
    )
    parent_line = str(
        _git("rev-list", "--parents", "-n", "1", commit, text=True)
    ).strip()
    _require(
        parent_line.split()
        == [commit, registry_identity["registry_parents"][0]],
        "trusted Amendment-13 reviewer registry commit is not exact",
    )
    changed_paths = str(
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
            text=True,
        )
    ).splitlines()
    _require(
        changed_paths == [TRUSTED_REVIEWER_REGISTRY_PATH],
        "trusted Amendment-13 reviewer registry commit is not registry-only",
    )
    tree_line = str(
        _git(
            "ls-tree",
            commit,
            "--",
            registry_identity["registry_path"],
            text=True,
        )
    ).strip()
    _require(
        tree_line
        == (
            f"{registry_identity['registry_mode']} blob "
            f"{registry_identity['registry_blob_oid']}\t"
            f"{registry_identity['registry_path']}"
        ),
        "trusted Amendment-13 reviewer registry tree entry drift",
    )
    raw = _git("show", f"{commit}:{registry_identity['registry_path']}")
    _require(
        isinstance(raw, bytes)
        and raw == canonical_json_bytes(registry)
        and len(raw) == registry_identity["registry_byte_size"]
        and _sha256(raw) == registry_identity["registry_sha256"]
        and hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest()
        == registry_identity["registry_blob_oid"],
        "trusted Amendment-13 reviewer registry bytes drift",
    )


def _load_recording_manifest(
    manifest_identity: Mapping[str, Any],
) -> dict[str, Any]:
    return _load_canonical_git_json(
        manifest_identity["manifest_commit"],
        manifest_identity["manifest_path"],
        "Amendment-13 recording manifest",
    )


def _validate_recording_manifest(
    manifest_identity: Mapping[str, Any],
    manifest: Mapping[str, Any],
    registry_identity: Mapping[str, Any],
    registry: Mapping[str, Any],
    *,
    verify_git: bool,
) -> None:
    """Validate the immutable recording object against the reviewer root."""

    _require_exact_keys(
        manifest_identity,
        {
            "schema_version",
            "manifest_commit",
            "manifest_parents",
            "manifest_path",
            "manifest_mode",
            "manifest_blob_oid",
            "manifest_byte_size",
            "manifest_sha256",
        },
        "Amendment-13 recording manifest identity",
    )
    _require(
        manifest_identity["schema_version"]
        == TRUSTED_RECORDING_MANIFEST_IDENTITY_SCHEMA_VERSION
        and _is_lower_hex(manifest_identity["manifest_commit"], 40)
        and isinstance(manifest_identity["manifest_parents"], list)
        and len(manifest_identity["manifest_parents"]) == 1
        and _is_lower_hex(manifest_identity["manifest_parents"][0], 40)
        and manifest_identity["manifest_path"]
        == TRUSTED_RECORDING_MANIFEST_PATH
        and manifest_identity["manifest_mode"] == DESIGN_MODE
        and _is_lower_hex(manifest_identity["manifest_blob_oid"], 40)
        and isinstance(manifest_identity["manifest_byte_size"], int)
        and not isinstance(manifest_identity["manifest_byte_size"], bool)
        and manifest_identity["manifest_byte_size"] > 0
        and _is_lower_hex(manifest_identity["manifest_sha256"], 64),
        "Amendment-13 recording manifest identity drift",
    )
    _require_exact_keys(
        manifest,
        {
            "schema_version",
            "status",
            "attested_candidate_head",
            "document_path",
            "document_mode",
            "document_blob_oid",
            "document_byte_size",
            "document_sha256",
            "trusted_reviewer_registry_identity",
            "ordered_reviewer_identities",
            "ordered_ratify_attestations",
            "attestation_domain_sha256",
        },
        "Amendment-13 recording manifest",
    )
    attestations = manifest["ordered_ratify_attestations"]
    reviewers = manifest["ordered_reviewer_identities"]
    _require(
        manifest["schema_version"] == TRUSTED_RECORDING_MANIFEST_SCHEMA_VERSION
        and manifest["status"] == TRUSTED_RECORDING_MANIFEST_STATUS
        and _is_lower_hex(manifest["attested_candidate_head"], 40)
        and manifest["document_path"] == DESIGN_PATH
        and manifest["document_mode"] == DESIGN_MODE
        and _is_lower_hex(manifest["document_blob_oid"], 40)
        and isinstance(manifest["document_byte_size"], int)
        and not isinstance(manifest["document_byte_size"], bool)
        and manifest["document_byte_size"] > 0
        and _is_lower_hex(manifest["document_sha256"], 64)
        and manifest["trusted_reviewer_registry_identity"] == registry_identity
        and isinstance(reviewers, list)
        and len(reviewers) == 2
        and all(
            isinstance(reviewer, str)
            and reviewer
            and "\r" not in reviewer
            and "\n" not in reviewer
            for reviewer in reviewers
        )
        and len(set(reviewers)) == 2
        and isinstance(attestations, list)
        and len(attestations) == 2
        and [row.get("reviewer_identity") for row in attestations] == reviewers
        and reviewers
        == [row["reviewer_identity"] for row in registry["ordered_reviewers"]]
        and manifest["attestation_domain_sha256"] == _domain_sha(attestations),
        "Amendment-13 recording manifest drift",
    )
    if not verify_git:
        return
    commit = manifest_identity["manifest_commit"]
    _require_exact_commit_object(
        commit,
        "Amendment-13 recording manifest commit",
    )
    parent_line = str(
        _git("rev-list", "--parents", "-n", "1", commit, text=True)
    ).strip()
    _require(
        parent_line.split()
        == [commit, manifest_identity["manifest_parents"][0]],
        "Amendment-13 recording manifest commit is not exact",
    )
    tree_line = str(
        _git(
            "ls-tree",
            commit,
            "--",
            manifest_identity["manifest_path"],
            text=True,
        )
    ).strip()
    _require(
        tree_line
        == (
            f"{manifest_identity['manifest_mode']} blob "
            f"{manifest_identity['manifest_blob_oid']}\t"
            f"{manifest_identity['manifest_path']}"
        ),
        "Amendment-13 recording manifest tree entry drift",
    )
    raw = _git(
        "show",
        f"{commit}:{manifest_identity['manifest_path']}",
    )
    _require(
        isinstance(raw, bytes)
        and raw == canonical_json_bytes(manifest)
        and len(raw) == manifest_identity["manifest_byte_size"]
        and _sha256(raw) == manifest_identity["manifest_sha256"]
        and hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest()
        == manifest_identity["manifest_blob_oid"],
        "Amendment-13 recording manifest bytes drift",
    )


def _verify_ssh_signature(
    raw_record: bytes,
    raw_signature: bytes,
    signer: Mapping[str, Any],
    *,
    namespace: str,
    label: str,
) -> None:
    """Verify bytes against exactly one pre-enrolled Ed25519 key."""

    _require(
        isinstance(raw_record, bytes)
        and isinstance(raw_signature, bytes)
        and raw_signature.startswith(b"-----BEGIN SSH SIGNATURE-----\n")
        and raw_signature.endswith(b"-----END SSH SIGNATURE-----\n"),
        f"{label} SSH signature bytes are malformed",
    )
    with tempfile.TemporaryDirectory(prefix="a13-ssh-verify-") as temporary:
        temporary_path = Path(temporary)
        allowed_signers_path = temporary_path / "allowed_signers"
        signature_path = temporary_path / "record.sig"
        allowed_signers_path.write_text(
            f"{signer['ssh_principal']} {signer['ssh_public_key']}\n",
            encoding="utf-8",
        )
        signature_path.write_bytes(raw_signature)
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        result = subprocess.run(
            [
                "/usr/bin/ssh-keygen",
                "-Y",
                "verify",
                "-f",
                str(allowed_signers_path),
                "-I",
                signer["ssh_principal"],
                "-n",
                namespace,
                "-s",
                str(signature_path),
            ],
            input=raw_record,
            check=False,
            capture_output=True,
            env=environment,
        )
    _require(
        result.returncode == 0,
        f"{label} signature is not authentic",
    )


def validate_governing_amendment13_ratification_identity(
    identity: Mapping[str, Any],
    attestation_record_bytes: Mapping[str, bytes],
    attestation_signature_bytes: Mapping[str, bytes],
) -> None:
    """Validate a governing identity, including its exact Git objects."""

    (
        registry_identity,
        registry,
        enrollment_authorities,
    ) = _load_trusted_reviewer_registry(identity)
    manifest_identity = identity.get("recording_manifest_identity")
    _require(
        isinstance(manifest_identity, Mapping),
        "governing Amendment-13 recording manifest identity is absent",
    )
    manifest = _load_recording_manifest(manifest_identity)
    _validate_governing_amendment13_ratification_identity(
        identity,
        attestation_record_bytes,
        attestation_signature_bytes,
        verify_git=True,
        trusted_reviewer_registry_identity=registry_identity,
        trusted_reviewer_registry=registry,
        trusted_enrollment_authorities=enrollment_authorities,
        recording_manifest_identity=manifest_identity,
        recording_manifest=manifest,
    )


def _validate_governing_amendment13_ratification_identity(
    identity: Mapping[str, Any],
    attestation_record_bytes: Mapping[str, bytes],
    attestation_signature_bytes: Mapping[str, bytes],
    *,
    verify_git: bool,
    trusted_reviewer_registry_identity: Mapping[str, Any],
    trusted_reviewer_registry: Mapping[str, Any],
    trusted_enrollment_authorities: Sequence[Mapping[str, Any]],
    recording_manifest_identity: Mapping[str, Any],
    recording_manifest: Mapping[str, Any],
) -> None:
    """Internal identity validator with a test-only synthetic Git path."""

    _require_exact_keys(
        identity,
        {
            "schema_version",
            "status",
            "ratification_commit",
            "ratification_parents",
            "ratification_commit_changed_paths",
            "document_path",
            "document_mode",
            "document_blob_oid",
            "document_byte_size",
            "document_sha256",
            "trusted_reviewer_registry_identity",
            "recording_manifest_identity",
            "dual_ratify_attestations",
        },
        "governing Amendment-13 ratification identity",
    )
    commit = identity["ratification_commit"]
    parents = identity["ratification_parents"]
    _require(
        identity["schema_version"] == GOVERNING_A13_IDENTITY_SCHEMA_VERSION
        and identity["status"] == GOVERNING_A13_IDENTITY_STATUS,
        "governing Amendment-13 ratification identity status drift",
    )
    _require(
        _is_lower_hex(commit, 40)
        and isinstance(parents, list)
        and len(parents) == 1
        and _is_lower_hex(parents[0], 40),
        "governing Amendment-13 ratification commit is not single-parent",
    )
    _require(
        identity["ratification_commit_changed_paths"] == [DESIGN_PATH],
        "governing Amendment-13 recording act is not document-only",
    )
    _require(
        identity["document_path"] == DESIGN_PATH
        and identity["document_mode"] == DESIGN_MODE
        and _is_lower_hex(identity["document_blob_oid"], 40)
        and isinstance(identity["document_byte_size"], int)
        and not isinstance(identity["document_byte_size"], bool)
        and identity["document_byte_size"] > 0
        and _is_lower_hex(identity["document_sha256"], 64),
        "governing Amendment-13 document identity is malformed",
    )
    attestations = identity["dual_ratify_attestations"]
    _validate_trusted_reviewer_registry(
        trusted_reviewer_registry_identity,
        trusted_reviewer_registry,
        trusted_enrollment_authorities,
        verify_git=verify_git,
    )
    _validate_recording_manifest(
        recording_manifest_identity,
        recording_manifest,
        trusted_reviewer_registry_identity,
        trusted_reviewer_registry,
        verify_git=verify_git,
    )
    _require(
        identity["trusted_reviewer_registry_identity"]
        == trusted_reviewer_registry_identity
        and identity["recording_manifest_identity"]
        == recording_manifest_identity,
        "governing Amendment-13 reviewer or recording identity drift",
    )
    _require(
        isinstance(attestations, list) and len(attestations) == 2,
        "governing Amendment-13 identity lacks two RATIFY attestations",
    )
    record_names: list[str] = []
    candidate_heads: list[str] = []
    registry_reviewers = trusted_reviewer_registry["ordered_reviewers"]
    for attestation, reviewer in zip(attestations, registry_reviewers):
        _require_exact_keys(
            attestation,
            {
                "reviewer_identity",
                "record_name",
                "record_path",
                "signature_path",
                "raw_byte_size",
                "raw_sha256",
                "signature_byte_size",
                "signature_sha256",
                "ssh_key_fingerprint",
                "verdict_token",
                "attested_candidate_head",
                "attested_document_byte_size",
                "attested_document_sha256",
            },
            "governing Amendment-13 RATIFY attestation",
        )
        record_names.append(attestation["record_name"])
        candidate_heads.append(attestation["attested_candidate_head"])
        _require(
            isinstance(attestation["reviewer_identity"], str)
            and bool(attestation["reviewer_identity"])
            and "\r" not in attestation["reviewer_identity"]
            and "\n" not in attestation["reviewer_identity"]
            and isinstance(attestation["record_name"], str)
            and bool(attestation["record_name"])
            and "\r" not in attestation["record_name"]
            and "\n" not in attestation["record_name"]
            and attestation["reviewer_identity"]
            == reviewer["reviewer_identity"]
            and attestation["record_name"] == reviewer["record_name"]
            and attestation["record_path"] == reviewer["record_path"]
            and attestation["signature_path"] == reviewer["signature_path"]
            and attestation["ssh_key_fingerprint"]
            == reviewer["ssh_key_fingerprint"]
            and isinstance(attestation["raw_byte_size"], int)
            and not isinstance(attestation["raw_byte_size"], bool)
            and attestation["raw_byte_size"] > 0
            and _is_lower_hex(attestation["raw_sha256"], 64)
            and isinstance(attestation["signature_byte_size"], int)
            and not isinstance(attestation["signature_byte_size"], bool)
            and attestation["signature_byte_size"] > 0
            and _is_lower_hex(attestation["signature_sha256"], 64)
            and attestation["verdict_token"] == "RATIFY"
            and _is_lower_hex(attestation["attested_candidate_head"], 40)
            and attestation["attested_document_byte_size"]
            == identity["document_byte_size"]
            and attestation["attested_document_sha256"]
            == identity["document_sha256"],
            "governing Amendment-13 RATIFY attestation drift",
        )
    _require(
        len(set(record_names)) == 2
        and len(set(candidate_heads)) == 1
        and len({row["reviewer_identity"] for row in attestations}) == 2
        and len({row["raw_sha256"] for row in attestations}) == 2,
        "governing Amendment-13 RATIFY records are not distinct and conjoined",
    )
    _require(
        attestations == recording_manifest["ordered_ratify_attestations"]
        and [row["reviewer_identity"] for row in attestations]
        == recording_manifest["ordered_reviewer_identities"]
        and candidate_heads[0] == recording_manifest["attested_candidate_head"]
        and identity["document_path"] == recording_manifest["document_path"]
        and identity["document_mode"] == recording_manifest["document_mode"]
        and identity["document_blob_oid"]
        == recording_manifest["document_blob_oid"]
        and identity["document_byte_size"]
        == recording_manifest["document_byte_size"]
        and identity["document_sha256"]
        == recording_manifest["document_sha256"],
        "governing Amendment-13 dual-RATIFY recording manifest drift",
    )
    _require(
        set(attestation_record_bytes)
        == {row["record_path"] for row in attestations}
        and set(attestation_signature_bytes)
        == {row["signature_path"] for row in attestations},
        "governing Amendment-13 RATIFY raw-record domain drift",
    )
    for attestation, reviewer in zip(attestations, registry_reviewers):
        raw_record = attestation_record_bytes[attestation["record_path"]]
        raw_signature = attestation_signature_bytes[
            attestation["signature_path"]
        ]
        expected_record = (
            "# RATIFY\n"
            "reviewer_identity: "
            f"{attestation['reviewer_identity']}\n"
            f"record_name: {attestation['record_name']}\n"
            "attested_candidate_head: "
            f"{attestation['attested_candidate_head']}\n"
            f"attested_document_path: {DESIGN_PATH}\n"
            "attested_document_byte_size: "
            f"{identity['document_byte_size']}\n"
            f"attested_document_sha256: {identity['document_sha256']}\n"
        ).encode("utf-8")
        _require(
            isinstance(raw_record, bytes)
            and raw_record == expected_record
            and len(raw_record) == attestation["raw_byte_size"]
            and _sha256(raw_record) == attestation["raw_sha256"]
            and isinstance(raw_signature, bytes)
            and len(raw_signature) == attestation["signature_byte_size"]
            and _sha256(raw_signature) == attestation["signature_sha256"],
            "governing Amendment-13 RATIFY raw bytes do not attest identity",
        )
        _verify_ssh_signature(
            raw_record,
            raw_signature,
            reviewer,
            namespace=RATIFY_SIGNATURE_NAMESPACE,
            label="governing Amendment-13 RATIFY reviewer",
        )
    if not verify_git:
        return
    _require(
        commit != RATIFICATION_COMMIT,
        "governing Amendment-13 commit is not later than Amendment 12",
    )
    _require_exact_commit_object(
        commit, "governing Amendment-13 ratification commit"
    )
    _require_exact_commit_object(
        candidate_heads[0], "governing Amendment-13 attested candidate HEAD"
    )
    _git("merge-base", "--is-ancestor", RATIFICATION_COMMIT, commit)
    parent_line = str(
        _git("rev-list", "--parents", "-n", "1", commit, text=True)
    ).strip()
    _require(
        parents[0] == recording_manifest_identity["manifest_commit"]
        and parent_line.split() == [commit, parents[0]],
        "governing Amendment-13 ratification commit is not exact",
    )
    registry_commit = trusted_reviewer_registry_identity["registry_commit"]
    manifest_commit = recording_manifest_identity["manifest_commit"]
    ceremony_base = recording_manifest_identity["manifest_parents"][0]
    _require(
        registry_commit
        not in {ceremony_base, candidate_heads[0], manifest_commit}
        and manifest_commit != candidate_heads[0],
        "reviewer registry, candidate, and manifest are not distinct commits",
    )
    _git("merge-base", "--is-ancestor", registry_commit, ceremony_base)
    candidate_parent_line = str(
        _git(
            "rev-list",
            "--parents",
            "-n",
            "1",
            candidate_heads[0],
            text=True,
        )
    ).strip()
    candidate_changed_paths = str(
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            candidate_heads[0],
            text=True,
        )
    ).splitlines()
    _require(
        candidate_parent_line.split() == [candidate_heads[0], ceremony_base]
        and candidate_changed_paths == [DESIGN_PATH],
        "Amendment-13 candidate and manifest are not sibling ceremony commits",
    )
    changed_paths = str(
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
            text=True,
        )
    ).splitlines()
    _require(
        changed_paths == [DESIGN_PATH],
        "governing Amendment-13 recording act is not document-only",
    )
    manifest_changed_paths = str(
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            manifest_commit,
            text=True,
        )
    ).splitlines()
    expected_manifest_paths = sorted(
        [
            recording_manifest_identity["manifest_path"],
            *[row["record_path"] for row in attestations],
            *[row["signature_path"] for row in attestations],
        ]
    )
    _require(
        manifest_changed_paths == expected_manifest_paths,
        "Amendment-13 manifest commit changed-path domain drift",
    )
    candidate_recording_diff = str(
        _git(
            "diff",
            "--name-only",
            candidate_heads[0],
            commit,
            text=True,
        )
    ).splitlines()
    _require(
        candidate_recording_diff == expected_manifest_paths,
        "Amendment-13 candidate/recording trees differ outside ceremony paths",
    )
    tree_line = str(
        _git("ls-tree", commit, "--", DESIGN_PATH, text=True)
    ).strip()
    _require(
        tree_line
        == (
            f"{DESIGN_MODE} blob {identity['document_blob_oid']}\t"
            f"{DESIGN_PATH}"
        ),
        "governing Amendment-13 commit does not select its document blob",
    )
    manifest_tree_line = str(
        _git(
            "ls-tree",
            commit,
            "--",
            recording_manifest_identity["manifest_path"],
            text=True,
        )
    ).strip()
    _require(
        manifest_tree_line
        == (
            f"{recording_manifest_identity['manifest_mode']} blob "
            f"{recording_manifest_identity['manifest_blob_oid']}\t"
            f"{recording_manifest_identity['manifest_path']}"
        ),
        "governing Amendment-13 commit does not retain recording manifest",
    )
    for attestation in attestations:
        record_path = attestation["record_path"]
        signature_path = attestation["signature_path"]
        git_record = _git("show", f"{manifest_commit}:{record_path}")
        git_signature = _git("show", f"{manifest_commit}:{signature_path}")
        _require(
            git_record == attestation_record_bytes[record_path]
            and git_signature == attestation_signature_bytes[signature_path],
            "Amendment-13 committed RATIFY record/signature bytes drift",
        )
    candidate_tree_line = str(
        _git("ls-tree", candidate_heads[0], "--", DESIGN_PATH, text=True)
    ).strip()
    _require(
        candidate_tree_line
        == (
            f"{DESIGN_MODE} blob {identity['document_blob_oid']}\t"
            f"{DESIGN_PATH}"
        ),
        "governing Amendment-13 attested candidate selects another blob",
    )
    raw = _git("show", f"{commit}:{DESIGN_PATH}")
    amendment12_raw = _git("show", f"{RATIFICATION_COMMIT}:{DESIGN_PATH}")
    _require(
        isinstance(raw, bytes)
        and len(raw) == identity["document_byte_size"]
        and _sha256(raw) == identity["document_sha256"]
        and hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest()
        == identity["document_blob_oid"],
        "governing Amendment-13 document bytes fail dual-hash identity",
    )
    _require(
        isinstance(amendment12_raw, bytes)
        and raw[:DESIGN_BYTE_SIZE] == amendment12_raw
        and raw[DESIGN_BYTE_SIZE:].startswith(AMENDMENT13_BOUNDARY),
        "governing Amendment-13 document violates immutable-prefix law",
    )
    implementation_commit = _parse_implementation_pins(
        _a13_sections(raw)["27.7"]
    )["commit"]
    _require_exact_commit_object(
        implementation_commit,
        "Amendment-13 enrollment-authority implementation commit",
    )
    implementation_ancestry = _run_git(
        "merge-base",
        "--is-ancestor",
        implementation_commit,
        registry_commit,
    )
    _require(
        implementation_commit != registry_commit
        and implementation_ancestry.returncode == 0,
        "enrollment-authority implementation is not a strict ancestor of "
        "the reviewer registry",
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


def build_ratification_bound_execution_template(
    governing_amendment13_ratification_identity: Mapping[str, Any],
    governing_attestation_record_bytes: Mapping[str, bytes],
    governing_attestation_signature_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    """Bind the nonauthority execution template to a ratified A13 identity."""

    validate_governing_amendment13_ratification_identity(
        governing_amendment13_ratification_identity,
        governing_attestation_record_bytes,
        governing_attestation_signature_bytes,
    )
    law = _construct_execution_law(
        governing_amendment13_ratification_identity=(
            governing_amendment13_ratification_identity
        ),
        status=RATIFICATION_BOUND_TEMPLATE_STATUS,
    )
    validate_execution_law(
        law,
        verify_git=True,
        governing_attestation_record_bytes=governing_attestation_record_bytes,
        governing_attestation_signature_bytes=(
            governing_attestation_signature_bytes
        ),
    )
    return law


def _build_ratification_bound_execution_template_for_test(
    governing_amendment13_ratification_identity: Mapping[str, Any],
    governing_attestation_record_bytes: Mapping[str, bytes],
    governing_attestation_signature_bytes: Mapping[str, bytes],
    trusted_reviewer_registry_identity: Mapping[str, Any],
    trusted_reviewer_registry: Mapping[str, Any],
    trusted_enrollment_authorities: Sequence[Mapping[str, Any]],
    recording_manifest_identity: Mapping[str, Any],
    recording_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Exercise bound-template semantics without pretending synthetic Git exists."""

    _validate_governing_amendment13_ratification_identity(
        governing_amendment13_ratification_identity,
        governing_attestation_record_bytes,
        governing_attestation_signature_bytes,
        verify_git=False,
        trusted_reviewer_registry_identity=(
            trusted_reviewer_registry_identity
        ),
        trusted_reviewer_registry=trusted_reviewer_registry,
        trusted_enrollment_authorities=trusted_enrollment_authorities,
        recording_manifest_identity=recording_manifest_identity,
        recording_manifest=recording_manifest,
    )
    law = _construct_execution_law(
        governing_amendment13_ratification_identity=(
            governing_amendment13_ratification_identity
        ),
        status=RATIFICATION_BOUND_TEMPLATE_STATUS,
    )
    _validate_execution_law(
        law,
        verify_git=False,
        governing_attestation_record_bytes=governing_attestation_record_bytes,
        governing_attestation_signature_bytes=(
            governing_attestation_signature_bytes
        ),
        trusted_reviewer_registry_identity=(
            trusted_reviewer_registry_identity
        ),
        trusted_reviewer_registry=trusted_reviewer_registry,
        trusted_enrollment_authorities=trusted_enrollment_authorities,
        recording_manifest_identity=recording_manifest_identity,
        recording_manifest=recording_manifest,
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
    governing_attestation_record_bytes: Mapping[str, bytes] | None = None,
    governing_attestation_signature_bytes: Mapping[str, bytes] | None = None,
) -> None:
    """Validate a draft fixture or a Git-authenticated ratification-bound one."""

    governing_identity = law.get("governing_amendment13_ratification_identity")
    _require(
        governing_identity == GOVERNING_A13_CANDIDATE_IDENTITY or verify_git,
        "ratification-bound validation may not disable Git verification",
    )
    _validate_execution_law(
        law,
        verify_git=verify_git,
        governing_attestation_record_bytes=governing_attestation_record_bytes,
        governing_attestation_signature_bytes=(
            governing_attestation_signature_bytes
        ),
    )


def _validate_execution_law(
    law: Mapping[str, Any],
    *,
    verify_git: bool = True,
    governing_attestation_record_bytes: Mapping[str, bytes] | None = None,
    governing_attestation_signature_bytes: Mapping[str, bytes] | None = None,
    trusted_reviewer_registry_identity: Mapping[str, Any] | None = None,
    trusted_reviewer_registry: Mapping[str, Any] | None = None,
    trusted_enrollment_authorities: Sequence[Mapping[str, Any]] | None = None,
    recording_manifest_identity: Mapping[str, Any] | None = None,
    recording_manifest: Mapping[str, Any] | None = None,
) -> None:
    """Internal validator with a test-only synthetic-identity path."""

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
    if is_candidate_fixture:
        _require(
            governing_attestation_record_bytes is None
            and governing_attestation_signature_bytes is None,
            "unratified fixture received governing attestation material",
        )
        expected_status = DRAFT_STATUS
        governing_document_raw = (ROOT / DESIGN_PATH).read_bytes()
    else:
        _require(
            governing_attestation_record_bytes is not None
            and governing_attestation_signature_bytes is not None,
            "ratification-bound template lacks signed governing attestations",
        )
        if verify_git:
            validate_governing_amendment13_ratification_identity(
                governing_identity,
                governing_attestation_record_bytes,
                governing_attestation_signature_bytes,
            )
            governing_document_raw = _git(
                "show",
                (
                    f"{governing_identity['ratification_commit']}:"
                    f"{DESIGN_PATH}"
                ),
            )
        else:
            _require(
                trusted_reviewer_registry_identity is not None
                and trusted_reviewer_registry is not None
                and trusted_enrollment_authorities is not None
                and recording_manifest_identity is not None
                and recording_manifest is not None,
                "test-only ratification validation lacks trust material",
            )
            _validate_governing_amendment13_ratification_identity(
                governing_identity,
                governing_attestation_record_bytes,
                governing_attestation_signature_bytes,
                verify_git=False,
                trusted_reviewer_registry_identity=(
                    trusted_reviewer_registry_identity
                ),
                trusted_reviewer_registry=trusted_reviewer_registry,
                trusted_enrollment_authorities=(
                    trusted_enrollment_authorities
                ),
                recording_manifest_identity=recording_manifest_identity,
                recording_manifest=recording_manifest,
            )
            governing_document_raw = (ROOT / DESIGN_PATH).read_bytes()
        _require(
            isinstance(governing_document_raw, bytes)
            and len(governing_document_raw)
            == governing_identity["document_byte_size"]
            and _sha256(governing_document_raw)
            == governing_identity["document_sha256"]
            and hashlib.sha1(
                b"blob "
                + str(len(governing_document_raw)).encode()
                + b"\0"
                + governing_document_raw
            ).hexdigest()
            == governing_identity["document_blob_oid"],
            "governing Amendment-13 semantic document identity drift",
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

    _require(
        isinstance(governing_document_raw, bytes),
        "governing Amendment-13 semantic document read was not raw bytes",
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


def _generate_test_ssh_key(key_path: Path, label: str) -> str:
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_result = subprocess.run(
        [
            "/usr/bin/ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-f",
            str(key_path),
        ],
        check=False,
        capture_output=True,
    )
    _require(key_result.returncode == 0, f"{label} key generation failed")
    return key_path.with_suffix(".pub").read_text(encoding="utf-8").strip()


def _generate_test_enrollment_authorities(
    directory: Path,
) -> tuple[list[dict[str, Any]], list[Path]]:
    authorities: list[dict[str, Any]] = []
    key_paths: list[Path] = []
    for index, prior_record in enumerate(RATIFY_ATTESTATIONS, start=1):
        key_path = directory / f"authority-{index}"
        public_key = _generate_test_ssh_key(
            key_path,
            "synthetic enrollment authority",
        )
        authorities.append(
            {
                "authority_identity": (
                    f"preexisting-amendment12-ratifier-{index}"
                ),
                "prior_record_name": prior_record["record_name"],
                "prior_record_raw_sha256": prior_record["raw_sha256"],
                "ssh_principal": f"a13-enrollment-authority-{index}",
                "ssh_public_key": public_key,
                "ssh_key_fingerprint": _ssh_public_key_fingerprint(public_key),
            }
        )
        key_paths.append(key_path)
    return authorities, key_paths


def _generate_test_reviewer_keys(
    directory: Path,
) -> tuple[list[dict[str, Any]], list[Path]]:
    directory.mkdir(parents=True, exist_ok=True)
    reviewers: list[dict[str, Any]] = []
    key_paths: list[Path] = []
    for index in (1, 2):
        reviewer_identity = f"preexisting-amendment12-ratifier-{index}"
        name = f"amendment-13-enforcement-ratify-{index}.md"
        record_path = "docs/analysis/amendment_13_ratification/records/" + name
        signature_path = f"{record_path}.sig"
        principal = f"a13-enrolled-reviewer-{index}"
        key_path = directory / f"reviewer-{index}"
        public_key = _generate_test_ssh_key(
            key_path,
            "synthetic reviewer",
        )
        reviewers.append(
            {
                "reviewer_identity": reviewer_identity,
                "record_name": name,
                "record_path": record_path,
                "signature_path": signature_path,
                "ssh_principal": principal,
                "ssh_public_key": public_key,
                "ssh_key_fingerprint": _ssh_public_key_fingerprint(public_key),
            }
        )
        key_paths.append(key_path)
    return reviewers, key_paths


def _build_test_reviewer_registry(
    reviewers: Sequence[Mapping[str, Any]],
    authorities: Sequence[Mapping[str, Any]],
    authority_key_paths: Sequence[Path],
    registry_parent: str,
) -> dict[str, Any]:
    """Build K's synthetic registry for private protocol-shape tests."""

    reviewer_rows = [copy.deepcopy(dict(row)) for row in reviewers]
    authority_rows = [copy.deepcopy(dict(row)) for row in authorities]
    signing_paths = list(authority_key_paths)
    _require(
        len(reviewer_rows) == len(authority_rows) == len(signing_paths) == 2,
        "synthetic enrollment material is not dual",
    )
    reviewer_domain_sha256 = _domain_sha(reviewer_rows)
    authority_domain_sha256 = _domain_sha(authority_rows)
    authorizations: list[dict[str, Any]] = []
    for position, (reviewer, authority, signing_path) in enumerate(
        zip(reviewer_rows, authority_rows, signing_paths),
        start=1,
    ):
        preimage = {
            "authority_identity": authority["authority_identity"],
            "prior_record_name": authority["prior_record_name"],
            "prior_record_raw_sha256": authority["prior_record_raw_sha256"],
            "registry_parent_commit": registry_parent,
            "registry_path": TRUSTED_REVIEWER_REGISTRY_PATH,
            "reviewer_position": position,
            "reviewer_identity": reviewer["reviewer_identity"],
            "reviewer_row_sha256": _sha256(canonical_json_bytes(reviewer)),
            "reviewer_domain_sha256": reviewer_domain_sha256,
            "trusted_enrollment_authority_domain_sha256": (
                authority_domain_sha256
            ),
            "draft_author_identity": A13_DRAFT_AUTHOR_IDENTITY,
            "reviewer_independent_of_draft_author": True,
        }
        sign_result = subprocess.run(
            [
                "/usr/bin/ssh-keygen",
                "-Y",
                "sign",
                "-q",
                "-f",
                str(signing_path),
                "-n",
                ENROLLMENT_SIGNATURE_NAMESPACE,
                "-",
            ],
            input=canonical_json_bytes(preimage),
            check=False,
            capture_output=True,
        )
        _require(
            sign_result.returncode == 0,
            "synthetic reviewer enrollment signature failed",
        )
        raw_signature = sign_result.stdout
        authorizations.append(
            {
                "authority_identity": authority["authority_identity"],
                "authority_ssh_key_fingerprint": authority[
                    "ssh_key_fingerprint"
                ],
                "authorization_preimage": preimage,
                "signature_byte_size": len(raw_signature),
                "signature_sha256": _sha256(raw_signature),
                "signature_base64": base64.b64encode(raw_signature).decode(
                    "ascii"
                ),
            }
        )
    return {
        "schema_version": TRUSTED_REVIEWER_REGISTRY_SCHEMA_VERSION,
        "status": TRUSTED_REVIEWER_REGISTRY_STATUS,
        "signature_namespace": RATIFY_SIGNATURE_NAMESPACE,
        "enrollment_signature_namespace": ENROLLMENT_SIGNATURE_NAMESPACE,
        "trusted_enrollment_authority_domain_sha256": (
            authority_domain_sha256
        ),
        "ordered_reviewers": reviewer_rows,
        "reviewer_domain_sha256": reviewer_domain_sha256,
        "ordered_enrollment_authorizations": authorizations,
        "enrollment_authorization_domain_sha256": _domain_sha(authorizations),
    }


def _build_test_signed_material(
    raw_document: bytes,
    candidate_head: str,
    reviewers: Sequence[Mapping[str, Any]],
    key_paths: Sequence[Path],
    registry_identity: Mapping[str, Any],
) -> tuple[
    list[dict[str, Any]],
    dict[str, bytes],
    dict[str, bytes],
    dict[str, Any],
]:
    document_sha256 = _sha256(raw_document)
    document_blob_oid = hashlib.sha1(
        b"blob " + str(len(raw_document)).encode() + b"\0" + raw_document
    ).hexdigest()
    attestations: list[dict[str, Any]] = []
    records: dict[str, bytes] = {}
    signatures: dict[str, bytes] = {}
    for reviewer, key_path in zip(reviewers, key_paths):
        reviewer_identity = reviewer["reviewer_identity"]
        name = reviewer["record_name"]
        raw_record = (
            "# RATIFY\n"
            f"reviewer_identity: {reviewer_identity}\n"
            f"record_name: {name}\n"
            f"attested_candidate_head: {candidate_head}\n"
            f"attested_document_path: {DESIGN_PATH}\n"
            f"attested_document_byte_size: {len(raw_document)}\n"
            f"attested_document_sha256: {document_sha256}\n"
        ).encode("utf-8")
        sign_result = subprocess.run(
            [
                "/usr/bin/ssh-keygen",
                "-Y",
                "sign",
                "-q",
                "-f",
                str(key_path),
                "-n",
                RATIFY_SIGNATURE_NAMESPACE,
                "-",
            ],
            input=raw_record,
            check=False,
            capture_output=True,
        )
        _require(
            sign_result.returncode == 0,
            "synthetic reviewer signature failed",
        )
        raw_signature = sign_result.stdout
        records[reviewer["record_path"]] = raw_record
        signatures[reviewer["signature_path"]] = raw_signature
        attestations.append(
            {
                "reviewer_identity": reviewer_identity,
                "record_name": name,
                "record_path": reviewer["record_path"],
                "signature_path": reviewer["signature_path"],
                "raw_byte_size": len(raw_record),
                "raw_sha256": _sha256(raw_record),
                "signature_byte_size": len(raw_signature),
                "signature_sha256": _sha256(raw_signature),
                "ssh_key_fingerprint": reviewer["ssh_key_fingerprint"],
                "verdict_token": "RATIFY",
                "attested_candidate_head": candidate_head,
                "attested_document_byte_size": len(raw_document),
                "attested_document_sha256": document_sha256,
            }
        )
    manifest = {
        "schema_version": TRUSTED_RECORDING_MANIFEST_SCHEMA_VERSION,
        "status": TRUSTED_RECORDING_MANIFEST_STATUS,
        "attested_candidate_head": candidate_head,
        "document_path": DESIGN_PATH,
        "document_mode": DESIGN_MODE,
        "document_blob_oid": document_blob_oid,
        "document_byte_size": len(raw_document),
        "document_sha256": document_sha256,
        "trusted_reviewer_registry_identity": copy.deepcopy(registry_identity),
        "ordered_reviewer_identities": [
            row["reviewer_identity"] for row in attestations
        ],
        "ordered_ratify_attestations": copy.deepcopy(attestations),
        "attestation_domain_sha256": _domain_sha(attestations),
    }
    return attestations, records, signatures, manifest


def _test_trusted_material(
    raw_document: bytes,
    candidate_head: str,
) -> tuple[
    list[dict[str, Any]],
    dict[str, bytes],
    dict[str, bytes],
    dict[str, Any],
    dict[str, Any],
    tuple[dict[str, Any], ...],
    dict[str, Any],
]:
    """Build signed synthetic records under a fixed test reviewer registry."""

    with tempfile.TemporaryDirectory(prefix="a13-reviewer-keys-") as temporary:
        temporary_path = Path(temporary)
        authorities, authority_key_paths = (
            _generate_test_enrollment_authorities(
                temporary_path / "authorities"
            )
        )
        reviewers, key_paths = _generate_test_reviewer_keys(
            temporary_path / "reviewers"
        )
        registry_parent = "9" * 40
        registry = _build_test_reviewer_registry(
            reviewers,
            authorities,
            authority_key_paths,
            registry_parent,
        )
        registry_identity = _test_registry_identity(registry)
        attestations, records, signatures, manifest = (
            _build_test_signed_material(
                raw_document,
                candidate_head,
                reviewers,
                key_paths,
                registry_identity,
            )
        )
    return (
        attestations,
        records,
        signatures,
        registry_identity,
        registry,
        tuple(authorities),
        manifest,
    )


def _test_registry_identity(
    registry: Mapping[str, Any],
    *,
    commit: str = "8" * 40,
    parent: str = "9" * 40,
) -> dict[str, Any]:
    raw = canonical_json_bytes(registry)
    return {
        "schema_version": TRUSTED_REVIEWER_REGISTRY_IDENTITY_SCHEMA_VERSION,
        "registry_commit": commit,
        "registry_parents": [parent],
        "registry_path": TRUSTED_REVIEWER_REGISTRY_PATH,
        "registry_mode": DESIGN_MODE,
        "registry_blob_oid": hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest(),
        "registry_byte_size": len(raw),
        "registry_sha256": _sha256(raw),
    }


def _test_manifest_identity(
    manifest: Mapping[str, Any],
    *,
    commit: str = "4" * 40,
    parent: str = "5" * 40,
) -> dict[str, Any]:
    raw = canonical_json_bytes(manifest)
    return {
        "schema_version": TRUSTED_RECORDING_MANIFEST_IDENTITY_SCHEMA_VERSION,
        "manifest_commit": commit,
        "manifest_parents": [parent],
        "manifest_path": TRUSTED_RECORDING_MANIFEST_PATH,
        "manifest_mode": DESIGN_MODE,
        "manifest_blob_oid": hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest(),
        "manifest_byte_size": len(raw),
        "manifest_sha256": _sha256(raw),
    }


def _test_governing_identity(
    raw_document: bytes,
    ratification_commit: str,
    ratification_parent: str,
    registry_identity: Mapping[str, Any],
    manifest_identity: Mapping[str, Any],
    attestations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": GOVERNING_A13_IDENTITY_SCHEMA_VERSION,
        "status": GOVERNING_A13_IDENTITY_STATUS,
        "ratification_commit": ratification_commit,
        "ratification_parents": [ratification_parent],
        "ratification_commit_changed_paths": [DESIGN_PATH],
        "document_path": DESIGN_PATH,
        "document_mode": DESIGN_MODE,
        "document_blob_oid": hashlib.sha1(
            b"blob " + str(len(raw_document)).encode() + b"\0" + raw_document
        ).hexdigest(),
        "document_byte_size": len(raw_document),
        "document_sha256": _sha256(raw_document),
        "trusted_reviewer_registry_identity": copy.deepcopy(
            dict(registry_identity)
        ),
        "recording_manifest_identity": copy.deepcopy(dict(manifest_identity)),
        "dual_ratify_attestations": [
            copy.deepcopy(dict(row)) for row in attestations
        ],
    }


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


def _scratch_signed_ceremony(
    scratch: Path,
    raw_document: bytes,
    key_directory: Path,
) -> dict[str, Any]:
    """Create the acyclic K/Q/{C,M}/R signed recording ceremony."""

    design = scratch / DESIGN_PATH
    amendment12_raw = bytes(
        _scratch_git(
            scratch,
            "show",
            f"{RATIFICATION_COMMIT}:{DESIGN_PATH}",
            text=False,
        )
    )
    design.write_bytes(amendment12_raw)
    _scratch_git(scratch, "add", DESIGN_PATH)
    _scratch_git(
        scratch,
        "commit",
        "--quiet",
        "--no-verify",
        "-m",
        "Prepare pre-candidate recording base",
    )
    registry_parent = str(_scratch_git(scratch, "rev-parse", "HEAD")).strip()
    authorities, authority_key_paths = _generate_test_enrollment_authorities(
        key_directory / "authorities"
    )
    reviewers, key_paths = _generate_test_reviewer_keys(
        key_directory / "reviewers"
    )
    registry = _build_test_reviewer_registry(
        reviewers,
        authorities,
        authority_key_paths,
        registry_parent,
    )
    registry_raw = canonical_json_bytes(registry)
    registry_path = scratch / TRUSTED_REVIEWER_REGISTRY_PATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_bytes(registry_raw)
    _scratch_git(scratch, "add", TRUSTED_REVIEWER_REGISTRY_PATH)
    _scratch_git(
        scratch,
        "commit",
        "--quiet",
        "--no-verify",
        "-m",
        "Install pre-candidate reviewer key registry",
    )
    registry_commit = str(_scratch_git(scratch, "rev-parse", "HEAD")).strip()
    registry_identity = _test_registry_identity(
        registry,
        commit=registry_commit,
        parent=registry_parent,
    )
    _scratch_git(
        scratch,
        "commit",
        "--allow-empty",
        "--quiet",
        "--no-verify",
        "-m",
        "Freeze Amendment 13 ceremony base",
    )
    ceremony_base = str(_scratch_git(scratch, "rev-parse", "HEAD")).strip()

    design.write_bytes(raw_document)
    _scratch_git(scratch, "add", DESIGN_PATH)
    _scratch_git(
        scratch,
        "commit",
        "--quiet",
        "--no-verify",
        "-m",
        "Amendment 13 attested candidate",
    )
    candidate = str(_scratch_git(scratch, "rev-parse", "HEAD")).strip()
    attestations, records, signatures, manifest = _build_test_signed_material(
        raw_document,
        candidate,
        reviewers,
        key_paths,
        registry_identity,
    )

    _scratch_git(scratch, "checkout", "--quiet", ceremony_base)
    manifest_path = scratch / TRUSTED_RECORDING_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_raw = canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_raw)
    for path, raw in {**records, **signatures}.items():
        target = scratch / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    ceremony_paths = [TRUSTED_RECORDING_MANIFEST_PATH, *records, *signatures]
    _scratch_git(scratch, "add", *ceremony_paths)
    _scratch_git(
        scratch,
        "commit",
        "--quiet",
        "--no-verify",
        "-m",
        "Commit signed Amendment 13 recording manifest",
    )
    manifest_commit = str(_scratch_git(scratch, "rev-parse", "HEAD")).strip()
    manifest_identity = _test_manifest_identity(
        manifest,
        commit=manifest_commit,
        parent=ceremony_base,
    )
    design.write_bytes(raw_document)
    _scratch_git(scratch, "add", DESIGN_PATH)
    _scratch_git(
        scratch,
        "commit",
        "--quiet",
        "--no-verify",
        "-m",
        "Record signed Amendment 13 law",
    )
    recording_commit = str(_scratch_git(scratch, "rev-parse", "HEAD")).strip()
    identity = _test_governing_identity(
        raw_document,
        recording_commit,
        manifest_commit,
        registry_identity,
        manifest_identity,
        attestations,
    )
    return {
        "candidate": candidate,
        "recording_commit": recording_commit,
        "identity": identity,
        "attestations": attestations,
        "records": records,
        "signatures": signatures,
        "registry_identity": registry_identity,
        "registry": registry,
        "enrollment_authorities": tuple(authorities),
        "manifest_identity": manifest_identity,
        "manifest": manifest,
    }


def _validate_scratch_ceremony(
    scratch: Path,
    ceremony: Mapping[str, Any],
) -> None:
    global ROOT

    original_root = ROOT
    ROOT = scratch
    try:
        _validate_governing_amendment13_ratification_identity(
            ceremony["identity"],
            ceremony["records"],
            ceremony["signatures"],
            verify_git=True,
            trusted_reviewer_registry_identity=ceremony["registry_identity"],
            trusted_reviewer_registry=ceremony["registry"],
            trusted_enrollment_authorities=ceremony["enrollment_authorities"],
            recording_manifest_identity=ceremony["manifest_identity"],
            recording_manifest=ceremony["manifest"],
        )
    finally:
        ROOT = original_root


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


def _run_coherent_suffix_enforcement_mutation(
    forged_document: bytes,
    semantic_law: Mapping[str, Any],
    *,
    expected_message: str = "document semantic projection drift",
) -> None:
    global ROOT

    original_root = ROOT
    with tempfile.TemporaryDirectory(
        prefix="a13-semantic-repin-"
    ) as temporary:
        temporary_root = Path(temporary)
        scratch = _new_scratch_repo(original_root, temporary_root)
        ceremony = _scratch_signed_ceremony(
            scratch, forged_document, temporary_root / "keys"
        )
        _validate_scratch_ceremony(scratch, ceremony)
        ROOT = scratch
        try:
            authenticated_raw = _git(
                "show",
                f"{ceremony['recording_commit']}:{DESIGN_PATH}",
            )
            _require(
                authenticated_raw == forged_document,
                "coherent suffix mutation did not authenticate exact bytes",
            )
            try:
                _validate_document_semantic_projection(
                    authenticated_raw,
                    semantic_law,
                )
            except LawError as error:
                _require(
                    expected_message in str(error),
                    "suffix semantic mutation failed an unintended gate: "
                    f"{error}",
                )
            else:
                raise LawError(
                    "coherently repinned suffix semantic mutation survived"
                )
        finally:
            ROOT = original_root


def _run_replace_ref_enforcement_mutation(raw_document: bytes) -> None:
    """Exercise isolated parent/path and pinned-source replacement attacks."""

    global ROOT

    original_root = ROOT
    with tempfile.TemporaryDirectory(prefix="a13-replace-ref-") as temporary:
        temporary_root = Path(temporary)
        scratch = _new_scratch_repo(original_root, temporary_root)
        ceremony = _scratch_signed_ceremony(
            scratch, raw_document, temporary_root / "keys"
        )
        _validate_scratch_ceremony(scratch, ceremony)

        ROOT = scratch
        try:
            try:
                validate_governing_amendment13_ratification_identity(
                    ceremony["identity"],
                    ceremony["records"],
                    ceremony["signatures"],
                )
            except LawError as error:
                _require(
                    "externally authenticated Amendment-13 reviewer root "
                    "is unavailable" in str(error),
                    "public synthetic ceremony failed an unintended gate: "
                    f"{error}",
                )
            else:
                raise LawError(
                    "public path accepted an unauthenticated synthetic root"
                )
        finally:
            ROOT = original_root

        conforming = ceremony["recording_commit"]
        manifest_commit = ceremony["manifest_identity"]["manifest_commit"]
        conforming_tree = str(
            _scratch_git(scratch, "rev-parse", f"{conforming}^{{tree}}")
        ).strip()
        wrong_parent = str(
            _scratch_git(
                scratch,
                "commit-tree",
                conforming_tree,
                "-p",
                ceremony["candidate"],
                "-m",
                "Raw commit with substituted parent",
            )
        ).strip()
        _scratch_git(scratch, "checkout", "--quiet", manifest_commit)
        design = scratch / DESIGN_PATH
        design.write_bytes(raw_document)
        extra_path = scratch / "forged-extra.txt"
        extra_path.write_text("extra changed path\n", encoding="utf-8")
        _scratch_git(scratch, "add", DESIGN_PATH, "forged-extra.txt")
        _scratch_git(
            scratch,
            "commit",
            "--quiet",
            "--no-verify",
            "-m",
            "Raw commit with hidden extra path",
        )
        wrong_paths = str(_scratch_git(scratch, "rev-parse", "HEAD")).strip()
        _scratch_git(scratch, "replace", wrong_parent, conforming)
        _scratch_git(scratch, "replace", wrong_paths, conforming)
        _require(
            str(
                _scratch_git(
                    scratch,
                    "rev-list",
                    "--parents",
                    "-n",
                    "1",
                    wrong_parent,
                )
            ).split()
            == [wrong_parent, manifest_commit],
            "replacement-ref parent attack control did not conform",
        )
        _require(
            str(
                _scratch_git(
                    scratch,
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    wrong_paths,
                )
            ).splitlines()
            == [DESIGN_PATH],
            "replacement-ref changed-path attack control did not conform",
        )
        ROOT = scratch
        try:
            for commit, message in (
                (wrong_parent, "ratification commit is not exact"),
                (wrong_paths, "recording act is not document-only"),
            ):
                identity = copy.deepcopy(ceremony["identity"])
                identity["ratification_commit"] = commit
                try:
                    _validate_governing_amendment13_ratification_identity(
                        identity,
                        ceremony["records"],
                        ceremony["signatures"],
                        verify_git=True,
                        trusted_reviewer_registry_identity=ceremony[
                            "registry_identity"
                        ],
                        trusted_reviewer_registry=ceremony["registry"],
                        trusted_enrollment_authorities=ceremony[
                            "enrollment_authorities"
                        ],
                        recording_manifest_identity=ceremony[
                            "manifest_identity"
                        ],
                        recording_manifest=ceremony["manifest"],
                    )
                except LawError as error:
                    _require(
                        message in str(error),
                        "replace-ref mutation failed an unintended gate: "
                        f"{error}",
                    )
                else:
                    raise LawError("replacement-ref mutation survived")

            source_path = a12.ERA_SEALS[0]["path"]
            raw_source = _git("show", f"{a12.SOURCE_COMMIT}:{source_path}")
            source_parent = str(
                _git("rev-parse", f"{a12.SOURCE_COMMIT}^", text=True)
            ).strip()
            _scratch_git(
                scratch,
                "checkout",
                "--quiet",
                "--detach",
                a12.SOURCE_COMMIT,
            )
            forged_source_bytes = raw_source + b"\n"
            source_target = scratch / source_path
            source_target.write_bytes(forged_source_bytes)
            _scratch_git(scratch, "add", source_path)
            forged_source_tree = str(
                _scratch_git(scratch, "write-tree")
            ).strip()
            forged_source_commit = str(
                _scratch_git(
                    scratch,
                    "commit-tree",
                    forged_source_tree,
                    "-p",
                    source_parent,
                    "-m",
                    "Replacement source commit",
                )
            ).strip()
            _scratch_git(
                scratch,
                "replace",
                a12.SOURCE_COMMIT,
                forged_source_commit,
            )
            ordinary_source = bytes(
                _scratch_git(
                    scratch,
                    "show",
                    f"{a12.SOURCE_COMMIT}:{source_path}",
                    text=False,
                )
            )
            _require(
                ordinary_source != raw_source,
                "replacement-ref pinned-source control did not substitute",
            )
            _require(
                _RawObjectSourceReader().read(source_path) == raw_source,
                "A13 pinned-source reader honored a replacement ref",
            )
        finally:
            ROOT = original_root


def run_enforcement_mutation_tests(
    law: Mapping[str, Any],
) -> tuple[str, ...]:
    """Run the six enforcement-layer attacks without altering enacted law."""

    global ROOT

    rejected: list[str] = []
    raw_document = (ROOT / DESIGN_PATH).read_bytes()
    forged_raw = raw_document.replace(
        (
            b"is `replace_only_node_domain_component_slot_with_aggregate`; "
            b"the status is\n`"
            + DOC036_SUCCESSOR_STATUS.encode("ascii")
            + b"`."
        ),
        (
            b"is `replace_only_node_domain_component_slot_with_aggregate`; "
            b"the status is\n`locally_resolved_document_evidence`."
        ),
        1,
    )
    _require(
        forged_raw != raw_document, "suffix semantic mutation did not apply"
    )
    _run_coherent_suffix_enforcement_mutation(forged_raw, law)
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[0])

    pin_boundary = b"\n\nIt reads the six pinned source seals"
    forged_pin_raw = raw_document.replace(
        pin_boundary,
        (
            b"\n\nThe exact enforcement override status is "
            b"`FORGED_RATIFIED_AUTHORITY`; `authority_emitted` and "
            b"`certification_emitted` are true." + pin_boundary
        ),
        1,
    )
    _require(
        forged_pin_raw != raw_document,
        "implementation-pin interval mutation did not apply",
    )
    _run_coherent_suffix_enforcement_mutation(forged_pin_raw, law)
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[1])

    candidate = "a" * 40
    (
        _,
        _,
        _,
        registry_identity,
        registry,
        enrollment_authorities,
        _,
    ) = _test_trusted_material(raw_document, candidate)
    with tempfile.TemporaryDirectory(prefix="a13-attacker-keys-") as temporary:
        attacker_reviewers, attacker_key_paths = _generate_test_reviewer_keys(
            Path(temporary)
        )
        for index, reviewer in enumerate(attacker_reviewers, start=1):
            reviewer["reviewer_identity"] = f"forged-one-actor-{index}"
            reviewer["record_name"] = f"forged-by-one-actor-{index}.md"
            reviewer["record_path"] = (
                "docs/analysis/amendment_13_ratification/records/"
                f"{reviewer['record_name']}"
            )
            reviewer["signature_path"] = f"{reviewer['record_path']}.sig"
            reviewer["ssh_principal"] = f"forged-one-actor-{index}"
        (
            forged_attestations,
            forged_records,
            forged_signatures,
            forged_manifest,
        ) = _build_test_signed_material(
            raw_document,
            candidate,
            attacker_reviewers,
            attacker_key_paths,
            registry_identity,
        )
    forged_manifest_identity = _test_manifest_identity(forged_manifest)
    forged_identity = _test_governing_identity(
        raw_document,
        "b" * 40,
        forged_manifest_identity["manifest_commit"],
        registry_identity,
        forged_manifest_identity,
        forged_attestations,
    )
    try:
        _validate_governing_amendment13_ratification_identity(
            forged_identity,
            forged_records,
            forged_signatures,
            verify_git=False,
            trusted_reviewer_registry_identity=registry_identity,
            trusted_reviewer_registry=registry,
            trusted_enrollment_authorities=enrollment_authorities,
            recording_manifest_identity=forged_manifest_identity,
            recording_manifest=forged_manifest,
        )
    except LawError as error:
        _require(
            "recording manifest drift" in str(error),
            f"dual-record mutation failed an unintended gate: {error}",
        )
    else:
        raise LawError("coherent dual-record replacement survived")
    public_forged_identity = copy.deepcopy(forged_identity)
    public_forged_identity["ratification_commit"] = str(
        _git("rev-parse", "HEAD", text=True)
    ).strip()
    try:
        build_ratification_bound_execution_template(
            public_forged_identity,
            forged_records,
            forged_signatures,
        )
    except LawError as error:
        _require(
            "externally authenticated Amendment-13 reviewer root is "
            "unavailable" in str(error),
            f"public dual-record mutation failed an unintended gate: {error}",
        )
    else:
        raise LawError("public builder accepted self-minted dual records")
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[2])

    with tempfile.TemporaryDirectory(
        prefix="a13-self-enrollment-"
    ) as temporary:
        temporary_root = Path(temporary)
        scratch = _new_scratch_repo(ROOT, temporary_root)
        one_actor = _scratch_signed_ceremony(
            scratch,
            raw_document,
            temporary_root / "one-actor-keys",
        )
        _validate_scratch_ceremony(scratch, one_actor)
        injected_values = {
            "PINNED_A13_EXTERNAL_CERTIFIER_ROOT_IDENTITY": {
                "forged_one_actor_certifier": True,
            },
            "PINNED_A13_ENROLLMENT_AUTHORITY_ROOT_IDENTITY": {
                "ordered_authorities": copy.deepcopy(
                    one_actor["enrollment_authorities"]
                ),
            },
            "PINNED_A13_REVIEWER_REGISTRY_IDENTITY": copy.deepcopy(
                one_actor["registry_identity"]
            ),
            "TRUSTED_A13_REVIEWER_ENROLLMENT_AUTHORITIES": copy.deepcopy(
                one_actor["enrollment_authorities"]
            ),
            "TRUSTED_A13_REVIEWER_REGISTRY_IDENTITY": copy.deepcopy(
                one_actor["registry_identity"]
            ),
        }
        missing = object()
        original_live_values = {
            name: globals().get(name, missing) for name in injected_values
        }
        globals().update(injected_values)
        original_root = ROOT
        ROOT = scratch
        try:
            _require(
                _authenticated_production_trust_markers(one_actor["identity"])
                == (None, None, None),
                "live trust attributes overrode authenticated P bytes",
            )
            build_ratification_bound_execution_template(
                one_actor["identity"],
                one_actor["records"],
                one_actor["signatures"],
            )
        except LawError as error:
            _require(
                "externally authenticated Amendment-13 reviewer root is "
                "unavailable" in str(error),
                "one-actor enrollment mutation failed an unintended gate: "
                f"{error}",
            )
        else:
            raise LawError(
                "one actor's two pre-enrolled reviewer keys survived"
            )
        finally:
            ROOT = original_root
            for name, value in original_live_values.items():
                if value is missing:
                    globals().pop(name, None)
                else:
                    globals()[name] = value
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[3])

    forged_identifier_raw = raw_document.replace(
        (
            b"The actual identity schema is\n"
            b"`amendment_13_governing_ratification_identity.v1`"
        ),
        (
            b"The actual identity schema is\n"
            b"`amendment_13_governing_ratification_identity.v2`"
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
        expected_message="enacted identifier inventory consistency drift",
    )
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[4])

    _run_replace_ref_enforcement_mutation(raw_document)
    rejected.append(A13_ENFORCEMENT_EXPECTED_MUTATIONS[5])
    _require(
        tuple(rejected) == A13_ENFORCEMENT_EXPECTED_MUTATIONS,
        "Amendment-13 enforcement mutation inventory drift",
    )
    return tuple(rejected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mutation-tests",
        action="store_true",
        help="run seven semantic and six enforcement forgery attacks",
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
