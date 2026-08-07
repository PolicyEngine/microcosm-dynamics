"""Validate Amendment 13's prospective tier-2 execution law.

This module emits no authority and writes no artifact.  It reconstructs the
proposed repair overlays from the six pinned stage-2 source seals, checks the
historical Amendment-12 ratification blob, and exercises Amendment 13's own
adversarial mutation inventory.  Amendment 12's frozen pilot bundle and its
71 mutations are deliberately not changed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
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
    b"\n## 27. Amendment 13 \xe2\x80\x94 ratification identity and tier-2 "
    b"repair-successor law\n"
)
RATIFICATION_CHANGED_PATH_COUNT = 17
ATTESTED_CANDIDATE_HEAD = "76acad02b0d519d12057b75ab7c21f2c2a4b2433"

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
    "0588e93fd84da1b949ec951b2c6c5f31f872f53980c333a21091141c774f7fbb"
)
EXPECTED_SUCCESSOR_DOMAIN_SHA256 = (
    "43fbdb31cdff9907ee985724c725ac453dc7134d8dd8e256e1aa6716f24fa029"
)
EXPECTED_SUPERSESSION_DOMAIN_SHA256 = (
    "9a5c1f1bd0871bd1fc60faed4c817b699b0ad571ee73b8b0ed07865db75195df"
)
EXPECTED_ERA_SEAL_DOMAIN_SHA256 = (
    "04b604d6a7c8009b7ebf7bc32e8985da6ab3150b8a4d2eb527e81d844bc7bd6f"
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

A13_EXPECTED_MUTATIONS = (
    "ratification_identity_wrong_blob",
    "ratification_identity_wrong_commit",
    "ratification_identity_multiple_parents",
    "successor_terminal_status_forged",
    "predecessor_supersession_erasure",
    "fragment_duplicate_selector_forged",
    "fragment_composition_transformation_forged",
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


def _git(*arguments: str, text: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=text,
    )
    _require(
        result.returncode == 0, f"git command failed: {' '.join(arguments)}"
    )
    return result.stdout


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


def validate_governing_amendment13_ratification_identity(
    identity: Mapping[str, Any],
    attestation_record_bytes: Mapping[str, bytes],
    *,
    verify_git: bool = True,
) -> None:
    """Validate the future identity that must govern an executed repair."""

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
    _require(
        isinstance(attestations, list) and len(attestations) == 2,
        "governing Amendment-13 identity lacks two RATIFY attestations",
    )
    record_names: list[str] = []
    candidate_heads: list[str] = []
    for attestation in attestations:
        _require_exact_keys(
            attestation,
            {
                "record_name",
                "raw_byte_size",
                "raw_sha256",
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
            isinstance(attestation["record_name"], str)
            and bool(attestation["record_name"])
            and isinstance(attestation["raw_byte_size"], int)
            and not isinstance(attestation["raw_byte_size"], bool)
            and attestation["raw_byte_size"] > 0
            and _is_lower_hex(attestation["raw_sha256"], 64)
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
        and len({row["raw_sha256"] for row in attestations}) == 2,
        "governing Amendment-13 RATIFY records are not distinct and conjoined",
    )
    _require(
        set(attestation_record_bytes) == set(record_names),
        "governing Amendment-13 RATIFY raw-record domain drift",
    )
    for attestation in attestations:
        raw_record = attestation_record_bytes[attestation["record_name"]]
        expected_record = (
            "# RATIFY\n"
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
            and _sha256(raw_record) == attestation["raw_sha256"],
            "governing Amendment-13 RATIFY raw bytes do not attest identity",
        )
    if not verify_git:
        return
    _require(
        commit != RATIFICATION_COMMIT,
        "governing Amendment-13 commit is not later than Amendment 12",
    )
    _git("merge-base", "--is-ancestor", RATIFICATION_COMMIT, commit)
    parent_line = str(
        _git("rev-list", "--parents", "-n", "1", commit, text=True)
    ).strip()
    _require(
        parent_line.split() == [commit, parents[0]],
        "governing Amendment-13 ratification commit is not exact",
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
) -> list[Any]:
    return [
        OVERLAY_SCHEMA_VERSION,
        document.position,
        document.source_document_id,
        _annotation_identity(document),
        AMENDMENT12_RATIFICATION_IDENTITY,
        GOVERNING_A13_CANDIDATE_IDENTITY,
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
    return {
        "terminal_status": PROOF_TERMINAL_STATUS,
        "terminal_reason_code": (
            "cited_instruction_does_not_authenticate_the_mixed_or_"
            "misbound_endpoint_projection"
        ),
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


def build_execution_law() -> dict[str, Any]:
    """Independently reconstruct the exact prospective execution-law fixture."""

    reader = a12.SourceReader(None)
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
                GOVERNING_A13_CANDIDATE_IDENTITY
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
            GOVERNING_A13_CANDIDATE_IDENTITY,
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
                    GOVERNING_A13_CANDIDATE_IDENTITY
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

    law = {
        "schema_version": SCHEMA_VERSION,
        "status": "PROSPECTIVE_NONAUTHORITY_UNRATIFIED_DRAFT",
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
            GOVERNING_A13_CANDIDATE_IDENTITY
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
    validate_execution_law(law, verify_git=False)
    return law


def _all_overlay_successors(overlay: Mapping[str, Any]) -> list[Any]:
    return [
        *overlay["semantically_incompatible_local_proof_successor_rows"],
        *overlay["incomplete_fragment_terminal_successor_rows"],
        *overlay["composed_fragment_successor_rows"],
        *overlay["doc036_aggregate_domain_successor_rows"],
    ]


def validate_execution_law(
    law: Mapping[str, Any], *, verify_git: bool = True
) -> None:
    """Fail closed unless ``law`` is the exact Amendment-13 proposal."""

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
    _require(
        law["status"] == "PROSPECTIVE_NONAUTHORITY_UNRATIFIED_DRAFT"
        and law["authority_emitted"] is False
        and law["certification_emitted"] is False,
        "draft claims authority or certification",
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
    _require(
        law["governing_amendment13_ratification_identity"]
        == GOVERNING_A13_CANDIDATE_IDENTITY,
        "unratified fixture claims a governing Amendment-13 identity",
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
                GOVERNING_A13_CANDIDATE_IDENTITY,
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
            == GOVERNING_A13_CANDIDATE_IDENTITY
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
                GOVERNING_A13_CANDIDATE_IDENTITY,
            ]
            and era_row["successor_era_seal_id"]
            == _content_id(
                "a13-successor-era-seal",
                era_row["successor_era_seal_identity_preimage"],
            )
            and era_row["amendment12_ratification_identity"]
            == AMENDMENT12_RATIFICATION_IDENTITY
            and era_row["governing_amendment13_ratification_identity"]
            == GOVERNING_A13_CANDIDATE_IDENTITY
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
        and integrity["overlay_domain_sha256"]
        == EXPECTED_OVERLAY_DOMAIN_SHA256
        and integrity["successor_domain_sha256"]
        == EXPECTED_SUCCESSOR_DOMAIN_SHA256
        and integrity["supersession_domain_sha256"]
        == EXPECTED_SUPERSESSION_DOMAIN_SHA256
        and integrity["successor_era_seal_domain_sha256"]
        == EXPECTED_ERA_SEAL_DOMAIN_SHA256,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mutation-tests",
        action="store_true",
        help="run the exact seven Amendment-13 forgery attacks",
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
    if arguments.print_summary or arguments.mutation_tests:
        print(
            json.dumps(
                {
                    "status": law["status"],
                    "authority_emitted": law["authority_emitted"],
                    "integrity": law["integrity"],
                    "mutation_test_count": len(rejected),
                    "mutations_rejected": list(rejected),
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
