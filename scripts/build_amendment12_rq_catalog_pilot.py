#!/usr/bin/env python3
"""Build Amendment 12's nonauthority R_Q catalog-law pilot artifacts.

The source corpus is the exact Git tree at ``SOURCE_COMMIT``.  This builder
reads the six pinned era seals first, verifies every selected annotation blob
against the identities carried by those seals, and adapts the three sealed
stage-2 handoff shapes without changing source text.  It emits only pilot and
targeted-sweep evidence.  It never emits Q5, a global catalog, R_Q, hierarchy,
slot, inventory, registry, receipt, or production authority.
"""

from __future__ import annotations

import argparse
import copy
import decimal
import hashlib
import json
import math
import os
import subprocess
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "analysis" / "amendment_12_rq_catalog_pilot"
DESIGN_PATH = ROOT / "docs" / "design" / "covered_earnings_correction.md"
NONLEDGER_ALIAS_ADJUDICATION_PATH = (
    ROOT / "scripts" / "amendment12_alias_semantic_adjudication_v1.json"
)
COMPOSITE_ALIAS_ADJUDICATION_PATH = (
    ROOT / "scripts" / "amendment12_composite_import_adjudication_v1.json"
)
COMPOSITE_INSTRUCTION_LAW_PATH = (
    ROOT / "scripts" / "amendment12_composite_instruction_law_map_v1.json"
)
NONLEDGER_ALIAS_ADJUDICATION_BYTE_SIZE = 74_773
NONLEDGER_ALIAS_ADJUDICATION_SHA256 = (
    "733f6c88ca19226db713f437ccaed8e8dfe781957f04e2f164b0dfdedb8e9870"
)
COMPOSITE_ALIAS_ADJUDICATION_BYTE_SIZE = 462_192
COMPOSITE_ALIAS_ADJUDICATION_SHA256 = (
    "f7ece535faed311a0a863e1f19f6954a428e89d552341f9d88603fe9092072da"
)
COMPOSITE_INSTRUCTION_LAW_BYTE_SIZE = 17_768
COMPOSITE_INSTRUCTION_LAW_SHA256 = (
    "0f85663e9e9681dba405a5a104d6d581b892a6a0e9e3561bb608b2ec4366ebb7"
)

SOURCE_COMMIT = "19fa24c161e800e004320f0c10e81bce8831af68"
SOURCE_BRANCH_LABEL = "claude/ce-global-q5-extraction"
DESIGN_PREFIX_BYTES = 3_557_513
DESIGN_PREFIX_SHA256 = (
    "b06e64e314645300458b6e1c72df23c9bd5090b376f676d1e492312135782d87"
)
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
ARTIFACT_INTEGRITY_KEYS = frozenset(
    {
        "canonicalization",
        "payload_sha256",
    }
)
PINNED_SWEEP_DOMAIN_SHA256 = {
    "role_exact_label_class": (
        "9c2f36a9a4cdc9fde3d790b71498234efde5b17235b9a5023ca4c772ad633e8d"
    ),
    "outside_domain_repeat_shape": (
        "baf5475e21ef404b911a7d7ec6328771caa01961d185f684a3ed63c4fdd8c48a"
    ),
    "noncatalog_aggregate_relation_shape_keyset": (
        "15b56ba454cc972608c269efb0f1e20fe7d85c9a7e80a030f5de7667df0fe1fc"
    ),
    "noncatalog_aggregate_relation_shape": (
        "bb1b34fe97ba6cf7b0497aea5b3992c32419511994d02792b24a85740d3ebf83"
    ),
    "in_domain_redirection_shape_keyset": (
        "e32dccc80f88bbbbaf21deab8083607d263dc512abd253023155cb5521e2fa82"
    ),
    "in_domain_redirection_shape": (
        "da11c6af360f3709b14f1a8700900e9fcd0342926b48b8ed8d39c701f8e36aab"
    ),
    "exclusive_destination_redirection_lineage": (
        "7f561ce5f6e30e747f6983eff6ba894c3c457888a39bf1bc5615b06d8307ad8e"
    ),
    "exclusive_destination_redirection_lineage_keyset": (
        "069455f172490db3db04977542df1bbcda23c6a0350a739830188016622ea5be"
    ),
    "in_domain_component_cross_reference_sweep": (
        "3826ff26177f409b855eb3b2aae3e3e1ae4c255f7d8f3db53f15668855ce159d"
    ),
    "in_domain_component_cross_reference_sweep_keyset": (
        "fbddc6aacd86db2d93dc945ba2217c243b05c810f43172cba7aaa4261395daa7"
    ),
    "semantic_alias_adjudication_keyset": (
        "d6ef33918540636117740f1d3f8b671c71f18b05e452ae94b3cd8658c79f16f0"
    ),
    "semantic_alias_instruction_outcome": (
        "13751e724b5c8496c7490161d3ec4f89dc32f6f2097899e9d243f2b10fea601e"
    ),
    "semantic_alias_equivalence_instruction_keyset": (
        "f82b497a80e9939ee4b0e2bd07ff6b053b3fa526f982394fe0d22ab9b7fb3e0f"
    ),
    "semantic_alias_redirection_instruction_keyset": (
        "dc72be9182f5b50fd358e492b952ba83ac41ccd99ec3ba117c8fe075013e8f72"
    ),
    "semantic_alias_stop_instruction_keyset": (
        "17a517a6cca6d0bb5c0767de49cbdc9dbcc79c963f74e988878112538eae39bd"
    ),
    "semantic_alias_fragment_instruction_keyset": (
        "25c6f38c37df363edfccf5c25c59c98dd7f06753cf19374c808eb011f83fdace"
    ),
    "semantic_alias_round_four_new_fragment_keyset": (
        "74075ac0ca54eff2a9459d4e95f426195c9e01db78040025462aa2f57f486a09"
    ),
    "alias_semantic_input_identity": (
        "b646228632da7baaeaff2f581c64aad2c087fa56c4870478844abfeb82cafd11"
    ),
    "alias_evidence_semantic_adjudication_keyset": (
        "5b1a310efda8a7c74559c9c424ba72848d745dff9c0961e00095c130d4d8cd7d"
    ),
    "alias_evidence_semantic_adjudication": (
        "ebd4d021cd29549fa311ea45c16297f5368eccd42bd3174f536c1945ce7eb884"
    ),
    "approved_alias_pair_keyset": (
        "df298bef2192c88e009c459304eb919c759fd919a1cef6db1612d70cb95f5389"
    ),
    "approved_alias_pair": (
        "6190969e68031be1e3b938baae4fe39371eaed9c8f697f91e59fbbdc66f700c4"
    ),
    "component_parent_shape_keyset": (
        "b1aaad10fac7e3a6eb35edabd99c079137404109f0b912f8726446965a1d0524"
    ),
    "component_parent_shape": (
        "22506ce5d02d6ceee9fc1a51aee25949c5b91cf218355396910ebe8faf53c7a0"
    ),
    "parent_source_witness_keyset": (
        "e6cc0d564a407a3375975c5522180ad6ec871b3fdd410680b31690f7b24651a9"
    ),
    "parent_source_witness": (
        "a89a54310e86cd3d08c40d9fb9cedc9f25dd0069780ecc4e94f8ef596843ebd1"
    ),
    "component_class_admission_keyset": (
        "3abf42fb2a4dc3f30aec676054423aa546011d01118aafd8034fa7291b1f1c62"
    ),
    "component_class_admission": (
        "c52c4bcb4d20e216f3d84dac71ac375610b1ed393d5697538a3b5ddfd82821ef"
    ),
    "catalog_only_job_complement_keyset": (
        "5dda6acc66f6b742ecd3bf8d2ac819b6309a89c44c39d6dd7578ad8a7e9496c1"
    ),
    "catalog_only_job_complement": (
        "cef11412144bacb139c5034045b2b002eb6a898fb3ad736f6cdda3874c21138d"
    ),
    "doc036_aggregate_component_slot": (
        "7cbeacb1e431e4e1486c726863cdf4f1213a76e5ab7259c69d390adaae7c7727"
    ),
    "predecessor_proof_adjudication_keyset": (
        "12d4b72affcecd0f0899a5683a2e1ab9bbae3cb37850b572701490e6210e3d12"
    ),
    "predecessor_proof_adjudication": (
        "9ed12e44e3b9996f21e0eb150c7ab4c0ff117f12e29296d32141ca69b3425746"
    ),
}

ROLE_HEAD = "head_or_reference_person"
ROLE_SPOUSE = "spouse_or_partner"
ROLE_ORDER = (ROLE_HEAD, ROLE_SPOUSE)
ROLE_CANONICALS = {
    ROLE_HEAD: (
        "psid-questionnaire-occurrence:"
        "4226e8c05e9d4cb91c5a1586731d6815c96268cadaebf51b2733c3daf499eda4"
    ),
    ROLE_SPOUSE: (
        "psid-questionnaire-occurrence:"
        "b59425917fcfdf5d07adbb4341b86cb4d57d161d3de5fffa5c8338bc16ca63a1"
    ),
}

COMPONENT_KINDS = (
    "source_context",
    "source_remuneration_component",
)
COMPONENT_CLASSIFICATION_TO_KIND = {
    "source_context": "context_anchor",
    "source_remuneration_component": "remuneration_component_anchor",
}
AGGREGATE_CLASSIFICATIONS = (
    "source_role_total",
    "source_farm_aggregate",
    "source_business_aggregate",
)
AGGREGATE_OCCURRENCE_KINDS = (
    "role_total_anchor",
    "farm_aggregate_anchor",
    "business_aggregate_anchor",
)
AGGREGATE_CLASSIFICATION_TO_KIND = {
    "source_role_total": "role_total_anchor",
    "source_farm_aggregate": "farm_aggregate_anchor",
    "source_business_aggregate": "business_aggregate_anchor",
}
AGGREGATE_KIND_TO_CLASSIFICATIONS = {
    "role_total_anchor": frozenset({"role_total", "source_role_total"}),
    "farm_aggregate_anchor": frozenset(
        {"farm_aggregate", "source_farm_aggregate"}
    ),
    "business_aggregate_anchor": frozenset(
        {"business_aggregate", "source_business_aggregate"}
    ),
}
ALLOWED_REPEAT_RELATIONS = (
    "explicit_repeat_instruction",
    "explicit_cross_reference",
)
ALLOWED_LOCAL_EVIDENCE_RELATIONS = (
    *ALLOWED_REPEAT_RELATIONS,
    "same_printed_identifier_and_exact_label",
)
COMPLETE_LOCAL_EVIDENCE_STATUSES = (
    "document_local_source_evidence_complete",
    "local_exact_identifier_and_label_for_global_assembly",
    "local_resolved_cross_reference_for_global_assembly",
)

CONTINUATION_COMPOSITION_RULE = (
    "adjacent_same_page_occurrences_separated_by_whitespace_only_gaps_"
    "compose_into_one_instruction_reading"
)
CONTINUATION_ALIAS_CITATIONS_BY_INSTRUCTION = {
    (
        "psid-questionnaire-occurrence:"
        "c38bfe9eb40d5028cec6d604b144eb54eee451a810bae4fd289bca5eefa27a32"
    ): {
        "leading_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "1f27469d6372b82b52d00f73f1f66877ad0a3423c38eca6a89824524ff537fbc"
        ),
        "page_number": 40,
        "page_text_utf8_sha256": (
            "d4f0cd6d9dfe4874e4de66121f01aab3ee3fa6e5cce85705db6013dc68033df4"
        ),
        "combined_utf8_byte_start": 1554,
        "leading_utf8_byte_end": 1650,
        "gap_utf8_byte_start": 1650,
        "gap_utf8_byte_end": 1661,
        "continuation_utf8_byte_start": 1661,
        "combined_utf8_byte_end": 1740,
        "combined_text": (
            "G8 l .    If employment was irregular and R can't give hours "
            "per week, try to get an estimate of\n          the total number "
            "of hours worked in 1995 at that job. See instructions for B79."
        ),
        "combined_utf8_sha256": (
            "c9168a361df7dd99663d16b90e96c4f2da73e3dfe1412df1450d367800d6bf03"
        ),
    },
    (
        "psid-questionnaire-occurrence:"
        "e2a45222a0321da6e02f24873de45bfb4401cb12a315bdbd96750c6afcfc286f"
    ): {
        "leading_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "4e2e0b200ae3624da5e4807b853bb3116bd600ada076fc396ced67677cfb2517"
        ),
        "page_number": 43,
        "page_text_utf8_sha256": (
            "7099faca6691a74775cc3caaca33c6942045b5c0eb5ae744b935466331c41d6d"
        ),
        "combined_utf8_byte_start": 758,
        "leading_utf8_byte_end": 855,
        "gap_utf8_byte_start": 855,
        "gap_utf8_byte_end": 866,
        "continuation_utf8_byte_start": 866,
        "combined_utf8_byte_end": 941,
        "combined_text": (
            "G81.          If employment was irregular and R can't give "
            "hours per week, get an estimate of the\n          total number of "
            "hours worked in 1996 at that job. See instructions for B79."
        ),
        "combined_utf8_sha256": (
            "68eb356f655a6e0205991f68b2152f4b4d857aded464cc406e623c6b40f9247c"
        ),
    },
    (
        "psid-questionnaire-occurrence:"
        "cf07296eb4c2e4bf77a81fabe6ec3254e12debe22805dd0dec123a4370e87852"
    ): {
        "leading_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "2b9c3ab97eb7ae78af829098bd4ef7f2efff9f0b1a2e2248fc079f7a5229d0a8"
        ),
        "page_number": 17,
        "page_text_utf8_sha256": (
            "14d9843ed8e0ae9f53d30436aaa58a13bef79c40e11f490bfee9da048d050142"
        ),
        "combined_utf8_byte_start": 2247,
        "leading_utf8_byte_end": 2338,
        "gap_utf8_byte_start": 2338,
        "gap_utf8_byte_end": 2361,
        "continuation_utf8_byte_start": 2361,
        "combined_utf8_byte_end": 2438,
        "combined_text": (
            "B46-B47.              Again we' re looking for the most recent "
            "position change in 1995. See\n                      cautions "
            "and instructions at B25-B29 regarding detailing the position "
            "change."
        ),
        "combined_utf8_sha256": (
            "3bf7f7262536e7e063456bf7b55c713035c0fddfc2fac816eb57972eb7337762"
        ),
    },
    (
        "psid-questionnaire-occurrence:"
        "2a56a4440b9e5714367c02fa09a0a480d015258b5023ddf32de22bf6871d3ace"
    ): {
        "leading_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "0a487265c65376bfdd593fdf6bce57390eead67f5253990b723a0b6a2adfa5c2"
        ),
        "page_number": 40,
        "page_text_utf8_sha256": (
            "d4f0cd6d9dfe4874e4de66121f01aab3ee3fa6e5cce85705db6013dc68033df4"
        ),
        "combined_utf8_byte_start": 1434,
        "leading_utf8_byte_end": 1531,
        "gap_utf8_byte_start": 1531,
        "gap_utf8_byte_end": 1543,
        "continuation_utf8_byte_start": 1543,
        "combined_utf8_byte_end": 1552,
        "combined_text": (
            "G79 .      This figure should be the number of weeks in which "
            "any work was done. See instructions\n           for B78 ."
        ),
        "combined_utf8_sha256": (
            "cf2b2cea5293d143477b4853fa183725b0bf1592f16e127a0958ffa4b0594e32"
        ),
    },
    (
        "psid-questionnaire-occurrence:"
        "7bbe18e8a8c52ccfa5e4bfdfe884bc8829006e3a55cad2861b674621042f9233"
    ): {
        "leading_occurrence_id": (
            "psid-questionnaire-occurrence:"
            "5d366486b57b6b901a8f0532bbc99104f7d3c1f97275f1e49ef8b6e4c6283531"
        ),
        "page_number": 43,
        "page_text_utf8_sha256": (
            "7099faca6691a74775cc3caaca33c6942045b5c0eb5ae744b935466331c41d6d"
        ),
        "combined_utf8_byte_start": 637,
        "leading_utf8_byte_end": 724,
        "gap_utf8_byte_start": 724,
        "gap_utf8_byte_end": 735,
        "continuation_utf8_byte_start": 735,
        "combined_utf8_byte_end": 756,
        "combined_text": (
            "G79.          This figure should be the number of weeks in "
            "which any work was done. See\n          instructions for B78."
        ),
        "combined_utf8_sha256": (
            "fa53889247aef17ea216aa3200135ad519c0dedad239980fb31c349cf8b91b30"
        ),
    },
}
CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS = frozenset(
    CONTINUATION_ALIAS_CITATIONS_BY_INSTRUCTION
)
CONTINUATION_RESTORATION_INSTRUCTION_IDS = frozenset(
    {
        (
            "psid-questionnaire-occurrence:"
            "cf07296eb4c2e4bf77a81fabe6ec3254e12debe22805dd0dec123a4370e87852"
        ),
        (
            "psid-questionnaire-occurrence:"
            "2a56a4440b9e5714367c02fa09a0a480d015258b5023ddf32de22bf6871d3ace"
        ),
        (
            "psid-questionnaire-occurrence:"
            "7bbe18e8a8c52ccfa5e4bfdfe884bc8829006e3a55cad2861b674621042f9233"
        ),
    }
)
if (
    len(CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS) != 5
    or len(CONTINUATION_RESTORATION_INSTRUCTION_IDS) != 3
    or not CONTINUATION_RESTORATION_INSTRUCTION_IDS
    < CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS
):
    raise RuntimeError("continuation citation and restoration domains drift")

COMPOSITE_IMPORT_INSTRUCTION_IDS = frozenset(
    """
psid-questionnaire-occurrence:cb562486f76e7f4dcb2a4ef574a0ae413de9a2ede4d4450ad2e8cf96058e8b2d
psid-questionnaire-occurrence:d986ab2a3dfc95f31fda53fac4a23b7520ee9fd449d2ef501569afe651b3a369
psid-questionnaire-occurrence:dfd221be448ee0468cc480dde0566ce1ff56f88eae3c99709ef0ae81a1e72ef0
psid-questionnaire-occurrence:ceedb0f652116dcaaba199e11f90365e8bdaf0557d783e0adc5b3ddc3e3aa33b
psid-questionnaire-occurrence:357281a0ee7987a14867f92a263f3aa1097d8bb5202d45820e4e8af363a7157b
psid-questionnaire-occurrence:a769c4a969cdaca2142d0aab2e2cee8aa2f9f83d4fe1abf4235e4bd9acb5c9f5
psid-questionnaire-occurrence:455271aa575d2126ae53289ab69e2eeb4fb652c63cad693f8ce70208a351731f
psid-questionnaire-occurrence:35833279648220c82c4340b8a40d6823b3d3fc231eca8180cdd635479521a052
psid-questionnaire-occurrence:bbdbc781bb95e0d12442053e1bf4a84094b4b88c42c8e2edb728d659891ee5dc
psid-questionnaire-occurrence:e84a537936c186e2873ea2d79ff28ef6d9cec295b75db355ed318720ca661bac
psid-questionnaire-occurrence:586b32d3786d0c7e475e39b30cf3f5a081a5943bba6093c4bea5886af47812ff
psid-questionnaire-occurrence:879048f9a5169e56b506da7c84c7780e4da524927635ec6ae52dcbc43a467e5c
psid-questionnaire-occurrence:c020df281459e26b8415bdb22c92f9ce30a0302cc21732ddaad3039ddf77b610
psid-questionnaire-occurrence:c3275a8794901e02bc0e54360ec899e43e61838b586fcf4fd171dbadd368a3ef
psid-questionnaire-occurrence:7a8a6bb241c7caa6856a50674c1ca8b82b69cf366e1b982c2895bbd6578f3ac0
psid-questionnaire-occurrence:ff130ead6f6c53c4759fd4b3e90904e46223850e73772a94277448f7aeeaaa7d
psid-questionnaire-occurrence:e743178fd99199a9b422f04dc9a8c20a700a2d1f698c58fc87b60067a91e2f72
psid-questionnaire-occurrence:1e5f65bf74b51459b2db19f2c8b433a9df29a660fcb5bed021e98a71e4c8ff2f
psid-questionnaire-occurrence:4c354d978faf69b2a8e4f567e344b272c097bdc28cc6986adafcb2f8d38af3ab
psid-questionnaire-occurrence:c7bc4ab94c2320b283203e6d6d677c21f84b9d61e10880b5f9b4d9c0261386d0
psid-questionnaire-occurrence:3d43945eef7cdf54dab92db704b47843633833c3964dd5cfcce683ff5dee1a9e
""".split()
)
COMPOSITE_IMPORT_STOP_FINDING_BY_INSTRUCTION = {
    (
        "psid-questionnaire-occurrence:"
        "dfd221be448ee0468cc480dde0566ce1ff56f88eae3c99709ef0ae81a1e72ef0"
    ): "exact_selector_text_unavailable_no_pair",
    (
        "psid-questionnaire-occurrence:"
        "ceedb0f652116dcaaba199e11f90365e8bdaf0557d783e0adc5b3ddc3e3aa33b"
    ): "exact_selector_text_unavailable_no_pair",
    (
        "psid-questionnaire-occurrence:"
        "35833279648220c82c4340b8a40d6823b3d3fc231eca8180cdd635479521a052"
    ): "named_ranges_do_not_derive_a_bijection",
    (
        "psid-questionnaire-occurrence:"
        "586b32d3786d0c7e475e39b30cf3f5a081a5943bba6093c4bea5886af47812ff"
    ): "exact_selector_text_unavailable_no_pair",
    (
        "psid-questionnaire-occurrence:"
        "879048f9a5169e56b506da7c84c7780e4da524927635ec6ae52dcbc43a467e5c"
    ): "exact_selector_text_unavailable_no_pair",
    (
        "psid-questionnaire-occurrence:"
        "ff130ead6f6c53c4759fd4b3e90904e46223850e73772a94277448f7aeeaaa7d"
    ): "mixed_missing_selector_and_unnamed_type_no_pair",
    (
        "psid-questionnaire-occurrence:"
        "4c354d978faf69b2a8e4f567e344b272c097bdc28cc6986adafcb2f8d38af3ab"
    ): "comparability_does_not_prove_equivalence_or_pairing",
}
COMPOSITE_IMPORT_STOP_INSTRUCTION_IDS = frozenset(
    COMPOSITE_IMPORT_STOP_FINDING_BY_INSTRUCTION
)

# This is an independent, closed commitment to the exact selector law for
# each of the 21 composite instructions.  The tuple binds the instruction to
# the questionnaire in which its named question text must occur.  The digest
# binds every alias/canonical selector, selector member, typed pairing,
# evidence STOP, unmatched-selector STOP, and exact selector citation.  A
# refreshed semantic input therefore cannot silently substitute a selector,
# questionnaire, pairing, or missing-source claim while merely repinning its
# own internal IDs.
COMPOSITE_INSTRUCTION_SOURCE_POSITION_LAW = {
    70: (
        "psid-questionnaire-occurrence:"
        "cb562486f76e7f4dcb2a4ef574a0ae413de9a2ede4d4450ad2e8cf96058e8b2d",
        56,
        57,
    ),
    72: (
        "psid-questionnaire-occurrence:"
        "d986ab2a3dfc95f31fda53fac4a23b7520ee9fd449d2ef501569afe651b3a369",
        56,
        57,
    ),
    78: (
        "psid-questionnaire-occurrence:"
        "dfd221be448ee0468cc480dde0566ce1ff56f88eae3c99709ef0ae81a1e72ef0",
        56,
        57,
    ),
    81: (
        "psid-questionnaire-occurrence:"
        "ceedb0f652116dcaaba199e11f90365e8bdaf0557d783e0adc5b3ddc3e3aa33b",
        56,
        57,
    ),
    88: (
        "psid-questionnaire-occurrence:"
        "357281a0ee7987a14867f92a263f3aa1097d8bb5202d45820e4e8af363a7157b",
        56,
        57,
    ),
    90: (
        "psid-questionnaire-occurrence:"
        "a769c4a969cdaca2142d0aab2e2cee8aa2f9f83d4fe1abf4235e4bd9acb5c9f5",
        56,
        57,
    ),
    91: (
        "psid-questionnaire-occurrence:"
        "455271aa575d2126ae53289ab69e2eeb4fb652c63cad693f8ce70208a351731f",
        56,
        57,
    ),
    103: (
        "psid-questionnaire-occurrence:"
        "35833279648220c82c4340b8a40d6823b3d3fc231eca8180cdd635479521a052",
        56,
        57,
    ),
    107: (
        "psid-questionnaire-occurrence:"
        "bbdbc781bb95e0d12442053e1bf4a84094b4b88c42c8e2edb728d659891ee5dc",
        58,
        59,
    ),
    109: (
        "psid-questionnaire-occurrence:"
        "e84a537936c186e2873ea2d79ff28ef6d9cec295b75db355ed318720ca661bac",
        58,
        59,
    ),
    115: (
        "psid-questionnaire-occurrence:"
        "586b32d3786d0c7e475e39b30cf3f5a081a5943bba6093c4bea5886af47812ff",
        58,
        59,
    ),
    118: (
        "psid-questionnaire-occurrence:"
        "879048f9a5169e56b506da7c84c7780e4da524927635ec6ae52dcbc43a467e5c",
        58,
        59,
    ),
    125: (
        "psid-questionnaire-occurrence:"
        "c020df281459e26b8415bdb22c92f9ce30a0302cc21732ddaad3039ddf77b610",
        58,
        59,
    ),
    127: (
        "psid-questionnaire-occurrence:"
        "c3275a8794901e02bc0e54360ec899e43e61838b586fcf4fd171dbadd368a3ef",
        58,
        59,
    ),
    128: (
        "psid-questionnaire-occurrence:"
        "7a8a6bb241c7caa6856a50674c1ca8b82b69cf366e1b982c2895bbd6578f3ac0",
        58,
        59,
    ),
    134: (
        "psid-questionnaire-occurrence:"
        "ff130ead6f6c53c4759fd4b3e90904e46223850e73772a94277448f7aeeaaa7d",
        58,
        59,
    ),
    138: (
        "psid-questionnaire-occurrence:"
        "e743178fd99199a9b422f04dc9a8c20a700a2d1f698c58fc87b60067a91e2f72",
        58,
        59,
    ),
    139: (
        "psid-questionnaire-occurrence:"
        "1e5f65bf74b51459b2db19f2c8b433a9df29a660fcb5bed021e98a71e4c8ff2f",
        58,
        59,
    ),
    140: (
        "psid-questionnaire-occurrence:"
        "4c354d978faf69b2a8e4f567e344b272c097bdc28cc6986adafcb2f8d38af3ab",
        58,
        59,
    ),
    143: (
        "psid-questionnaire-occurrence:"
        "c7bc4ab94c2320b283203e6d6d677c21f84b9d61e10880b5f9b4d9c0261386d0",
        58,
        59,
    ),
    161: (
        "psid-questionnaire-occurrence:"
        "3d43945eef7cdf54dab92db704b47843633833c3964dd5cfcce683ff5dee1a9e",
        70,
        71,
    ),
}
COMPOSITE_INSTRUCTION_SELECTOR_LAW_SHA256 = {
    70: "f4b3235fd66b38e8dd39b229160c55101973d0f546a95d6f34e2a309f12548a7",
    72: "b01dfe54fa6870d260f6e83352c99eb65ae839f0f732629b9511fc5786a2cc01",
    78: "1664ea9187dae16d70cdba2292075212854233da875bce7b6ad7ae61bb36a30c",
    81: "867b5e39d5daeb1ed63bea1764bd7e1d185b469c04b7b0e4b39143991f27abe9",
    88: "8063b1ad4dece89bc4c7d4d85fb6bc71b2b633a7c571a8fbbdafa48008636159",
    90: "7bd1fe5f79ac9d39780024edae943559b22bc545c4d7c646344da2616bbc399d",
    91: "6414175c1507414164be3ec53779193f7b0a11683cd774014561111c1e90e5cc",
    103: "3226094beb56add43a4cf042fc143e2c5a37c6c25d58c369951632dd931781b9",
    107: "ad21ca8bc848680e27e4af7ddae6f018e1d101ad4bcf0f3948f25b85d6fa48f3",
    109: "0f559d8494ba40ce1ee4a72aeec212f4ae270376cd23064626e7f538127c9ea0",
    115: "980b8f7cd5d71101fd3865cd5bdd1e32e878695340ffb5e78a6f00619a0e045f",
    118: "9aefb9ee1a904e5d8b3860051951a1fe80e95ba674b813d00995225cff3d846c",
    125: "6eb06df5b3fe165791142dec1b569a1aae6e5d17e3314e523c865aacbd141345",
    127: "38ebb3fcbacc5c218280643de9f967bbefbbe56142e40d46b4ac7f9fc2705ab0",
    128: "b8c9d42d343603a56a0cce0de2fc817885ca0ea0031aa2c56b3143ae54ed506b",
    134: "8613ca102d03e6c73d9c6e13f8ad7128803682d2aed55b0bf7bec7c803a49d0d",
    138: "491a34fb3e139ccb4bd08754d15f55d8956879bea6ad20ddd585986f368f923a",
    139: "73aea47cd8ce2f92e0bf9f34a4ff00cf835f3d079e25410a425658a0c9b65fa0",
    140: "c131879ba6af730d8e0abca3c292c7b8d56ded9aa3b63c7ee12f3ebb24e3f539",
    143: "0a43bcf6528e2abcf269557f4645251422bf25b6acd954e4abbb3cf69d8b97cf",
    161: "957d72f7e7f1e7eb14caec2f747ca5347e9a9c903b3cd9ae97d2c7602961dc6e",
}
COMPOSITE_STOP_MISSING_SOURCE_ROW_KEYS = frozenset(
    {"finding", "reason_code", "selector", "side"}
)
COMPOSITE_STOP_MISSING_SOURCE_FINDING = (
    "The registered q96/q97 questionnaire refers the interviewer to a "
    "separate supplement, but no exact question text for this selector "
    "appears in the registered questionnaire PDF or its pinned stage-2 "
    "occurrences."
)
COMPOSITE_STOP_MISSING_SOURCE_REASON_CODES = frozenset(
    {
        "work_history_supplement_not_in_registered_questionnaire",
        "yellow_job_supplement_not_in_registered_questionnaire",
    }
)

AGGREGATE_RELATION_SUBKIND = "aggregate_or_repeated_instance"
REDIRECTION_RELATION_SUBKIND = "exclusive_destination_redirection"
IN_DOMAIN_NONALIAS_SUBKINDS = (
    AGGREGATE_RELATION_SUBKIND,
    REDIRECTION_RELATION_SUBKIND,
)

# This is a source-cited semantic ledger, not a structural fallback.  The
# complete 2,460-instruction placement sweep below finds 45 candidate texts.
# Five instruction-level dispositions survive source review.  One of them has
# two independently authenticated destination edges; grouping those two rows
# here is what keeps R(r) singleton at the instruction level.
EXCLUSIVE_DESTINATION_REDIRECTION_EVIDENCE_BY_INSTRUCTION = {
    (
        "psid-questionnaire-occurrence:"
        "5843e37c0edd529d4a20389341bc0d42a57ff241806821b6f7f49355f6ed5e0e"
    ): (
        "rq-local-repeat-alias-evidence:"
        "d703ee09088e3789c6c77b9a01bc7350062cb744295cce86dd3a0722317cbe2b",
    ),
    (
        "psid-questionnaire-occurrence:"
        "a60351fcb96320baae7367f589eb3a45f95f7db1bc6c6cf3fbc3fba897c0667e"
    ): (
        "rq-local-repeat-alias-evidence:"
        "390e91405eab59354cf25f3deb7cb02dfa5924c655c33272fd226d2f5ba7117f",
    ),
    (
        "psid-questionnaire-occurrence:"
        "a0ac9e5d30e32fb183a0dbd492e46ae4554ea8ec15337d8a3d2710f7195073bd"
    ): (
        "rq-local-repeat-alias-evidence:"
        "2d00c4bc66f3191d36f783de3a709adba07c3eb894a054d971d72d64ba2870af",
    ),
    (
        "psid-questionnaire-occurrence:"
        "1dc6faa8137b8a9b0ec95a605682d2982b9baf1eddd86dee961ea99d0ba4510a"
    ): (
        "rq-local-repeat-evidence:"
        "1851a59e23285cabe0fb25977286cccd786152885b0c8f60bb29517a21f61e23",
        "rq-local-repeat-evidence:"
        "191167ca76ad47c4334c5f3b014abd7d520944d9faadca4b4aa80e52766cd7e2",
    ),
    (
        "psid-questionnaire-occurrence:"
        "65f1752d0f6d39346c412c1d492e574979277aa6c78094f1ad79f0d53cf57452"
    ): (
        "rq-local-repeat-evidence:"
        "5977fa11c007f370ece29867bc0d2b6c5d492990396b50d86959b1ec5ec87927",
    ),
}
EXCLUSIVE_DESTINATION_REDIRECTION_INSTRUCTION_IDS = frozenset(
    EXCLUSIVE_DESTINATION_REDIRECTION_EVIDENCE_BY_INSTRUCTION
)

# Round four exact-covers every one of the 162 structurally complete
# component cross-reference groups.  These positive members were reviewed
# against their exact instruction and endpoint text; they are deliberately
# enumerated so that a new structural match cannot silently enter A.
_ROUND_FIVE_REVIEWED_ALIAS_INSTRUCTION_IDS = frozenset(
    """
psid-questionnaire-occurrence:b71d860ddb620bcecb24104963153dd9282b4ed1e0c4f41b92bdc8b9aa14e0c3
psid-questionnaire-occurrence:b646a5e30eedfb39db762f4af982fa54c670cac4135202d6e9e79bf4737172db
psid-questionnaire-occurrence:ace0a3dcf08a213a064bba184a64ec6027f03e0799808ba4112d9b2361255096
psid-questionnaire-occurrence:23c1cb26196bb52bbadfb4c2bae320d92f1b63e05cfccde3491a9580d19df31f
psid-questionnaire-occurrence:2b36ea82aa9574b929c7d09ce663c0fcb198167e26435e30827ab45a87ea2a9b
psid-questionnaire-occurrence:cd32b6a0dd24de3092847e55c4b0ae491552cdca2b0437bb40dcff801b896cd6
psid-questionnaire-occurrence:d3959f2729b620ffc0fcc7af8c011cbf7edaaf4f3e6b7106e7f466a0186ac5dd
psid-questionnaire-occurrence:5e4bf9342aed1c83143de14eb06f99d29d2ad9c3075b62dccedb46992f95df50
psid-questionnaire-occurrence:b60a46a9c2f06b886489ee50a56f5037fe01d2708dbe0af785124881930fb685
psid-questionnaire-occurrence:502594a73993385ed601ad2e76e74c63a7928d454a6bc81925e07488072d4ead
psid-questionnaire-occurrence:f9a997e2967869e1efcd4a394b9997f8653795b99b5b22ab98fb305f17c32ad2
psid-questionnaire-occurrence:6688012788a3847da00066ae36943d67b1155b68e250e2b442f30c27a04ca2c4
psid-questionnaire-occurrence:5c7ddb3d93be28af9d4f1e5277ab962ba1b2285631477c668599d7192db59c74
psid-questionnaire-occurrence:47f6485be7e5a54bc1337b2e007bf391d21ad8d1c3b6ac0b04b6eaebd07aaace
psid-questionnaire-occurrence:e33a0d7082ceb071b0dab2a43f839e72079e3f925d4f9dace3778ea64fb79adf
psid-questionnaire-occurrence:5a7aa91b0ba7705995498afba4e251af3910cf8aa0e986efdcf66c10a675be6c
psid-questionnaire-occurrence:33f131fdcaf0988e5204e4f77b137c84323720af25d468c906727ed8d0a859d6
psid-questionnaire-occurrence:b57f8314dfaa2d60f9c9b671d5f612ceba81041c55e3c58856c413b25276ea35
psid-questionnaire-occurrence:fbfa289fb84b68c7afef82104ffe5ce16f8effcbbdfde0dc33e813e33212d8f0
psid-questionnaire-occurrence:bed98c1f41988a65f3b12af219edb5742edbd585bf0b087fa49521614d28daf6
psid-questionnaire-occurrence:acfc2a236d349fca92974fdf3e4b57b86d4da3207bd586cf47bcdd8ace6d2d49
psid-questionnaire-occurrence:cbce94d06d4945e9895b939aa32225429e73889db73d742e81686d00e47004c6
psid-questionnaire-occurrence:5eca138b817e38f3184f038002413d0f262556b172956f0c883e7ad2abaa1b1e
psid-questionnaire-occurrence:b59df50d23598175746574bd35e62ea3b27526a0e91e1ca5811bde02384874de
psid-questionnaire-occurrence:503d2f11975bb557c3ddee6852a5a7a96063d93fac9fcc51b5af153a290c5255
psid-questionnaire-occurrence:edd4b5d3f1fec5163286338804a73ac79147236ce7578d65b984c95698843e35
psid-questionnaire-occurrence:c8b7abc67ec1d5bc02924ed2dad177f3dc4b9d46a3161c8076a72bcbc90acce9
psid-questionnaire-occurrence:0ae50306e835ee80fdfac1f32323ab6883513a8b1948551e056dbaaa6492427e
psid-questionnaire-occurrence:b5265cfb4a2a194d40395c82a0c5e384adddff2611530142cf2844ce6ed20cbe
psid-questionnaire-occurrence:9582333627cf26561426cef746e0ce6e66c6028d685f25468f2872baeb54c7dc
psid-questionnaire-occurrence:2a83990d8f2ad60edf9b64c080156663b61220f174a22570bcb51478a7ff4dec
psid-questionnaire-occurrence:447b1c259449d4ba795bef734e37bcca3b817b32fa72efe75c38c3c857dfaaa2
psid-questionnaire-occurrence:981e92dc4190d0125ce814b0d4fec1992c2a7ed8e4df3d60de67477ed5902c4a
psid-questionnaire-occurrence:83219d4dc54fc4aa11b49f5aa3ac89975be369c83e68591ccae5863cc53ebdc1
psid-questionnaire-occurrence:dd482131fb211af302c6a4b4b05e7fb44ee195cd3c77f0f0871838e54e1db52c
psid-questionnaire-occurrence:f10796d34dd98656653fed95f0048d0106439addf40e9eb9394b14e20f134a67
psid-questionnaire-occurrence:e4c83ee8bda422f68fd110b6cdbe97b383d5ea84f93c476af56cb4bd9825492c
psid-questionnaire-occurrence:aa9e44c051fb65cde8c6dca7f883aa862006842e81438ce70c85469abb836fb1
psid-questionnaire-occurrence:59d685fdc5bbaa67bffa065cde8409d1264ec555f7d479c5b3bdebf6ac4b5640
psid-questionnaire-occurrence:a3297062bff0329d8e9149066af31defa03fde342553d3e38cd6ac8437c2ef66
psid-questionnaire-occurrence:e997afbc88c24e5a8244f198b3fe39765d166eef0eb1a26144f9fcc760773cea
psid-questionnaire-occurrence:4b1feda2e3308bd0e59e4faacf3680a01971e85cb1ae58ea0ab1f0c515540226
psid-questionnaire-occurrence:9ddb34628348ec8029dd9fa212fec0d0fff8bad22f62a7a4c2ef2b172d31a837
psid-questionnaire-occurrence:94ee3e1f701f27f73e1650dfd3e6b79ce1f480243ed96c5fa05e8cff8b6a13d1
psid-questionnaire-occurrence:def2a0a4d835b0f7c9fe58edcba7f618140fdef3b7745dede245046161629774
psid-questionnaire-occurrence:e71225563df663f77e984d37f5220152d98acbcb45bc67b90aa39a7f2cf13e6c
psid-questionnaire-occurrence:fb5e1db03c9b582db8edee265f4ff9735a15a948edf8e2e092ae74219fd3065b
psid-questionnaire-occurrence:ad47c7b95b1e9d7db921126ec2c53bfa4cc9137b49906d3cdac0a9ccd205bd5d
psid-questionnaire-occurrence:706a8d8805b00d1f1e2116b007c8f8f66c20bf9b8ba5ee4886a9dbe1f4ca5d57
psid-questionnaire-occurrence:5bbde7467a270f9d58ad39758f5f6d808a648e79159819dcc1adddb8a5c6af51
psid-questionnaire-occurrence:85744e7a15ed651fcccdfa9026762911f73e50b9d290a60e4a303f4cd756ccde
psid-questionnaire-occurrence:941c5c606606a6755c837f29d29e42de9275964eddfe1a927b5a12abcb82939f
psid-questionnaire-occurrence:c2471ec725d9dd4eb963c722ec740c07ad28d160d956a2a2dea4437c5961afcc
psid-questionnaire-occurrence:e8363a76340b38ed8dee532049bac2ba079b7de037236b42ad1fd0125ce40851
psid-questionnaire-occurrence:aea661774ca470f67e7d2e0d1dc34d09d8f994a9c458ac46a57e9f4698c98bf3
psid-questionnaire-occurrence:7d639fe231212006803f3f9a772a74bb3305c0dfd36cd4cc8f7248b9cc076b23
psid-questionnaire-occurrence:8a5dcaefe37b6861fbb4fee5d717f2072249faa2b4d4f277590a1fbbff3d721f
psid-questionnaire-occurrence:9bef34987b7404c9a3c4474c5d8d28eb62cfcf45c90fdb470595db70863a167b
psid-questionnaire-occurrence:9194fea2c5ad9bf33533d8af336e78a717e33d35382876f8d43e6e4078c64378
psid-questionnaire-occurrence:e7da6ca9c76c14ee756a4fc04f4d99bfd56d24a005facc756f1d7c01c725b890
psid-questionnaire-occurrence:cb562486f76e7f4dcb2a4ef574a0ae413de9a2ede4d4450ad2e8cf96058e8b2d
psid-questionnaire-occurrence:116697de22b8368ba1f36cd21df28d50aa6a4c262f983ba40f0c72f45ad8dc42
psid-questionnaire-occurrence:d986ab2a3dfc95f31fda53fac4a23b7520ee9fd449d2ef501569afe651b3a369
psid-questionnaire-occurrence:60a0dbc799f71c571b98e98bba45446635ca486803937c9896b905f83b9f65f5
psid-questionnaire-occurrence:fc919fa7c0d989d1c628b311ab0ea9c18d1e9190d0d35b31a267d6ee6377ee58
psid-questionnaire-occurrence:84e86fd6a3e5717650d70c2e355bf4669767e1684a26ed517b410d5a8dc96590
psid-questionnaire-occurrence:8284bf87ee04825f5d65ee0ac043cdd219354245a6afb48683a3b8241a3da6e2
psid-questionnaire-occurrence:dfd221be448ee0468cc480dde0566ce1ff56f88eae3c99709ef0ae81a1e72ef0
psid-questionnaire-occurrence:e5c179e56e92961c819c835c813749dd43a2a6fcb43f367e99c45c732d4b12ee
psid-questionnaire-occurrence:192a7c973b2de1308c73185ebba4fe890d1cac7acda8d8a9ef6d48a9a3083838
psid-questionnaire-occurrence:ceedb0f652116dcaaba199e11f90365e8bdaf0557d783e0adc5b3ddc3e3aa33b
psid-questionnaire-occurrence:2e3c4ca992de63540d649d50c46453051caafc183091a09673a42e426bb45a25
psid-questionnaire-occurrence:38b4a4305699d9807fb95155c3a0d5ffb19292c5ecaec8130c04c183c697f504
psid-questionnaire-occurrence:14817ab74cf52ea08584954267e7c4b9f93c0197cc29b3e83cfe867bcffb5567
psid-questionnaire-occurrence:9d98f4d258e0c543a5903a7cb0d65ec6fcd7b15b69ab0c18b3f589fa01e065a5
psid-questionnaire-occurrence:0f251ffe95a6daf139bc11305e77cf63c1d973aaf28673f39d37ccd4d0369497
psid-questionnaire-occurrence:7f303a404440c48b5b3a5efb61afb0411eced9eeb8216e8573009bdd1b566332
psid-questionnaire-occurrence:357281a0ee7987a14867f92a263f3aa1097d8bb5202d45820e4e8af363a7157b
psid-questionnaire-occurrence:96e419fbdc9217abafba7cbb57ccbe8d8b7891d6983fb7605d93baf0d9f56ba0
psid-questionnaire-occurrence:a769c4a969cdaca2142d0aab2e2cee8aa2f9f83d4fe1abf4235e4bd9acb5c9f5
psid-questionnaire-occurrence:455271aa575d2126ae53289ab69e2eeb4fb652c63cad693f8ce70208a351731f
psid-questionnaire-occurrence:d1068771a81bfbe9e37dba76d7e0b0672712309e5f2d8c39b7af4e11e16352f4
psid-questionnaire-occurrence:8c356ea86bbe363dcd42fc27b0e9a8c6cd0be0af4b4dcaa2507d408e91c0eb11
psid-questionnaire-occurrence:499d1b00af29b5829c212f706bbcfb02780c344584b9b1e47cb3b693146ffd39
psid-questionnaire-occurrence:c38bfe9eb40d5028cec6d604b144eb54eee451a810bae4fd289bca5eefa27a32
psid-questionnaire-occurrence:35833279648220c82c4340b8a40d6823b3d3fc231eca8180cdd635479521a052
psid-questionnaire-occurrence:4d30184605579b75c3e2830294e611d79c4c58faee7419bebc24a28184d9f990
psid-questionnaire-occurrence:0ff86ec95077fbc08920a822b71066f1fd50e719d02f35598a22c85eb2ca6c4a
psid-questionnaire-occurrence:bbdbc781bb95e0d12442053e1bf4a84094b4b88c42c8e2edb728d659891ee5dc
psid-questionnaire-occurrence:691e75cf4e4cf1a6d1937617e816779e1648588d0d2d33ef9561dab1438e2f0a
psid-questionnaire-occurrence:e84a537936c186e2873ea2d79ff28ef6d9cec295b75db355ed318720ca661bac
psid-questionnaire-occurrence:652edb4ddb3489fc31f8deb25bc521a0187669ff3c3d55d41a18416239b1e100
psid-questionnaire-occurrence:e7ee4eae79a43a23db51343f8903c79ee8abab8aa39c6be213b8ef7458725be4
psid-questionnaire-occurrence:720037ffe9e0f5a20134679ee7b82f09a53500dd07bd8394f0a51fafa4e6ff94
psid-questionnaire-occurrence:3f61d2648af7a3ae2cce9cc83500385e8bc90f19ef684bedc3ae97a26c481ae7
psid-questionnaire-occurrence:586b32d3786d0c7e475e39b30cf3f5a081a5943bba6093c4bea5886af47812ff
psid-questionnaire-occurrence:1924cf68355a5de911bb714574ee4111fb817451c1327f4a76523dcea526e68f
psid-questionnaire-occurrence:026a15afbee5081ff2fc89f6eee812345f8d82301d5295ea059d4a111855ab28
psid-questionnaire-occurrence:879048f9a5169e56b506da7c84c7780e4da524927635ec6ae52dcbc43a467e5c
psid-questionnaire-occurrence:f23296c474a6307373681de81cd4dbe088c3c33369c209aa8b755460ffa04f48
psid-questionnaire-occurrence:c69bb0d19859f92a9be51e97762531f5640f4fdebb5590bb6da568b40cc32c54
psid-questionnaire-occurrence:6a57948d94a4ebd65684fdb8f571076a74f246dffdecd9fc31cb41f3d30a5105
psid-questionnaire-occurrence:b8846e646f7a98b01fff065a96eed6fc899b1c37303631af6ed4712d5fb6c609
psid-questionnaire-occurrence:c06b9de58e43b852420b618360abfcffc67100aedaa6fed3d3f806912df81fe5
psid-questionnaire-occurrence:1556aa9da4d35ad8e6cad69fd5ef7a779ee3cdadd2dc0c8b9156acd1857223fd
psid-questionnaire-occurrence:c020df281459e26b8415bdb22c92f9ce30a0302cc21732ddaad3039ddf77b610
psid-questionnaire-occurrence:f645f651f874f0fb5fc0eb207dce804a17a7b5741aa4cfa3df5364c1678cfeee
psid-questionnaire-occurrence:c3275a8794901e02bc0e54360ec899e43e61838b586fcf4fd171dbadd368a3ef
psid-questionnaire-occurrence:7a8a6bb241c7caa6856a50674c1ca8b82b69cf366e1b982c2895bbd6578f3ac0
psid-questionnaire-occurrence:345ba9c46d178a22f231942df14918350d2546b89e027ab09f835910adaab71a
psid-questionnaire-occurrence:a0e986272c699e38dfc5cea5846b62387f2ad3b4d3521fd7797f17abb3c6a2fb
psid-questionnaire-occurrence:ff130ead6f6c53c4759fd4b3e90904e46223850e73772a94277448f7aeeaaa7d
psid-questionnaire-occurrence:e2a45222a0321da6e02f24873de45bfb4401cb12a315bdbd96750c6afcfc286f
psid-questionnaire-occurrence:e743178fd99199a9b422f04dc9a8c20a700a2d1f698c58fc87b60067a91e2f72
psid-questionnaire-occurrence:1e5f65bf74b51459b2db19f2c8b433a9df29a660fcb5bed021e98a71e4c8ff2f
psid-questionnaire-occurrence:4c354d978faf69b2a8e4f567e344b272c097bdc28cc6986adafcb2f8d38af3ab
psid-questionnaire-occurrence:728167dc13914f5e6f5a740b22cca014e204476beb5b8ef52f3b90e8367e2251
psid-questionnaire-occurrence:4e01709eb740fdc9f6af5929ee8834f94aef9de3c52c6bbde1ba9fffca700b24
psid-questionnaire-occurrence:c7bc4ab94c2320b283203e6d6d677c21f84b9d61e10880b5f9b4d9c0261386d0
psid-questionnaire-occurrence:120db8f9fcfe512bda9ee1fc71ff05ef6dc628913c5ee9cc2a95c3822b8e54ec
psid-questionnaire-occurrence:0b3e6cb334c151e47ecc91f4f00703f02d5396a7a6d0a4cf55c2d7c9306fd83f
psid-questionnaire-occurrence:677f49917f36f8925b3129f47f93aa914ba9ae2fb6612a42839caac415d7a56e
psid-questionnaire-occurrence:61f38513d63c0700bddf9bee561b472c15d7d64efd12ca7ab544d281120f3790
psid-questionnaire-occurrence:3d43945eef7cdf54dab92db704b47843633833c3964dd5cfcce683ff5dee1a9e
psid-questionnaire-occurrence:cf07296eb4c2e4bf77a81fabe6ec3254e12debe22805dd0dec123a4370e87852
psid-questionnaire-occurrence:2a56a4440b9e5714367c02fa09a0a480d015258b5023ddf32de22bf6871d3ace
psid-questionnaire-occurrence:7bbe18e8a8c52ccfa5e4bfdfe884bc8829006e3a55cad2861b674621042f9233
""".split()
)
SEMANTIC_ALIAS_EQUIVALENCE_INSTRUCTION_IDS = (
    _ROUND_FIVE_REVIEWED_ALIAS_INSTRUCTION_IDS
    - COMPOSITE_IMPORT_STOP_INSTRUCTION_IDS
)
ROUND_FIVE_STRUCTURAL_ALIAS_CANDIDATE_INSTRUCTION_IDS = (
    SEMANTIC_ALIAS_EQUIVALENCE_INSTRUCTION_IDS
    | COMPOSITE_IMPORT_STOP_INSTRUCTION_IDS
)

SEMANTIC_ALIAS_STOP_INSTRUCTION_IDS_BY_FINDING = {
    "incomplete_fragment_does_not_prove_occurrence_equivalence": frozenset(
        """
psid-questionnaire-occurrence:a37cf7dce81d69ba18e303afdd31a0825103c53d01398e644a312d55155150ba
psid-questionnaire-occurrence:8b9c6613b23e83dd55af058542e6aec3be341440397c632d91c1b74f073291dd
psid-questionnaire-occurrence:b151de324a45124f27e1b426eb06b8a94ccb653cea7cb7af8dd402341d6b61c5
psid-questionnaire-occurrence:e64ef592cbb11ef00efa78f26682094c8920a21960309c673bbff8008c99a5c8
psid-questionnaire-occurrence:9242a1af728bffad6ed96e7636bcaade0e31fe0a21561d97fe500c89cc9e5b12
psid-questionnaire-occurrence:9969e959ae2d58b54b5fbdfc4f4e6e0f8141f628d67415370e1ccd129017a4fb
psid-questionnaire-occurrence:4b6c12f1e8e57edd45a3d43a772c69d923ec4c72d8292cdff1ca1f9c0a069e3b
psid-questionnaire-occurrence:5eb05b791f0abad829debc9863433e0a8e7bd254aa18ac51b6c750caa48bb46a
psid-questionnaire-occurrence:d662043b204306d6c052f412fe674574e80fd1a40aca75b1842a212bb1fe8f68
psid-questionnaire-occurrence:5e89bb2a5186c4afee4a6a2289a4686ddcee89aeeae089b42c24e3ce9ff72708
""".split()
    ),
    "anti_duplication_instruction_disproves_occurrence_equivalence": (
        frozenset(
            """
psid-questionnaire-occurrence:6ed791445d19c2af492a3571d5a0d4b7f635eaeaabb5f5f3abf5424b8d04c03a
psid-questionnaire-occurrence:124dd16396afb1eb91cdefdaf057c3e2450ca445b7a8ea5f788d472db80cc1ba
""".split()
        )
    ),
    "conditional_overlap_does_not_prove_occurrence_equivalence": frozenset(
        """
psid-questionnaire-occurrence:9a16ad56ed62fe94ea3e8e0c0c41686d7cabc6ee0c9c261549d6774974257bef
psid-questionnaire-occurrence:a70a44fb68cd2b0ceefb729ae616454f03d7e66fb2bfd088e13d46fc58f349d8
psid-questionnaire-occurrence:e7eeaf55540d8d463685e599cbcdb12e91b76652a1029311ef206b3183aada05
psid-questionnaire-occurrence:e44e06b2a1a7e984e7321edb4eac1f28824855c2e9bbfbb2bc099ff6e5e43446
""".split()
    ),
    "dependency_or_derivation_does_not_prove_occurrence_equivalence": (
        frozenset(
            """
psid-questionnaire-occurrence:128e68c5f8b2bb12a7a03f63910789effa54a1c40987efeda703132349b339da
psid-questionnaire-occurrence:f7c8757b9260deed7395c6d3a68c085df26c7759681cfa6dc1fab7affe8fba4e
psid-questionnaire-occurrence:074d2fcfa21aa7202ba3d203ee2bb7f60b57d95195b4110a28c725206583a453
psid-questionnaire-occurrence:1b8479b3776c5e44c6c993326560344b819cd5a8a15ac64264c58d3e6caf3e58
psid-questionnaire-occurrence:c4f0f31a3b48fdc6794b81acc506b3a40b754a092e3073cdec008faf0ac52a3b
psid-questionnaire-occurrence:ca223381e53188458633c9029f3df0371945453ead6cd5a736f3ddd29eedca36
psid-questionnaire-occurrence:86c314ec0cbf47b1935cc4efbbdd5a54f168602175ceb959bd18d887350cad30
psid-questionnaire-occurrence:6c4a56864bdab02d8e595962fb8f1a997c473f1eb765939ea384284f01f7a3e7
psid-questionnaire-occurrence:a391cdd9c11b2efa526ca3df01e0acdae2668adcdf00ad547c2e25a7feefbc44
""".split()
        )
    ),
    "routing_to_additional_sequence_does_not_prove_equivalence": frozenset(
        {
            "psid-questionnaire-occurrence:913192535eea428b2564426ecc0722bdf6b5c6166ef46d8f4547afb2882f5028"
        }
    ),
    "parallel_similarity_without_instruction_import_is_not_equivalence": (
        frozenset(
            {
                "psid-questionnaire-occurrence:3874a79cb10aea6c83c58f2b7fc80950b78e09ad893718dccb38f8ebb2da1e23"
            }
        )
    ),
    "additional_distinct_item_disproves_occurrence_equivalence": frozenset(
        {
            "psid-questionnaire-occurrence:7c402f2de259365c89ff3074ff9caf72130b35efce2559e9383a1d6ae8e347fe"
        }
    ),
    "arithmetic_composition_does_not_prove_occurrence_equivalence": (
        frozenset(
            {
                "psid-questionnaire-occurrence:2731f348724837fcf2e8be8fac3d039705671d63b5b4496b18c0a82694395e2f"
            }
        )
    ),
    "context_remuneration_mix_cannot_form_an_alias_class": frozenset(
        {
            "psid-questionnaire-occurrence:cb6e826b4cbe30c065bcad8740672327ac7e1b92c7b36ec418f366b2fa0f9d9c"
        }
    ),
}
SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION = {
    instruction_id: finding
    for finding, instruction_ids in (
        SEMANTIC_ALIAS_STOP_INSTRUCTION_IDS_BY_FINDING.items()
    )
    for instruction_id in instruction_ids
}
SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION.update(
    COMPOSITE_IMPORT_STOP_FINDING_BY_INSTRUCTION
)
if len(SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION) != sum(
    len(value)
    for value in SEMANTIC_ALIAS_STOP_INSTRUCTION_IDS_BY_FINDING.values()
) + len(COMPOSITE_IMPORT_STOP_FINDING_BY_INSTRUCTION):
    raise RuntimeError("semantic alias STOP ledger overlaps")

# A mid-sentence or unfinished source occurrence is still probative when its
# extant bytes settle the semantic question.  It is never silently promoted
# into positive alias proof.  This ledger separately records whether the
# predecessor's source seal must be repaired before tier 2.
ROUND_THREE_FRAGMENT_RESEAL_INSTRUCTION_IDS = frozenset(
    """
psid-questionnaire-occurrence:f7c8757b9260deed7395c6d3a68c085df26c7759681cfa6dc1fab7affe8fba4e
psid-questionnaire-occurrence:074d2fcfa21aa7202ba3d203ee2bb7f60b57d95195b4110a28c725206583a453
psid-questionnaire-occurrence:ca223381e53188458633c9029f3df0371945453ead6cd5a736f3ddd29eedca36
psid-questionnaire-occurrence:6c4a56864bdab02d8e595962fb8f1a997c473f1eb765939ea384284f01f7a3e7
""".split()
)
ROUND_FOUR_NEW_FRAGMENT_RESEAL_INSTRUCTION_IDS = frozenset(
    """
psid-questionnaire-occurrence:a37cf7dce81d69ba18e303afdd31a0825103c53d01398e644a312d55155150ba
psid-questionnaire-occurrence:8b9c6613b23e83dd55af058542e6aec3be341440397c632d91c1b74f073291dd
psid-questionnaire-occurrence:b151de324a45124f27e1b426eb06b8a94ccb653cea7cb7af8dd402341d6b61c5
psid-questionnaire-occurrence:e64ef592cbb11ef00efa78f26682094c8920a21960309c673bbff8008c99a5c8
psid-questionnaire-occurrence:9242a1af728bffad6ed96e7636bcaade0e31fe0a21561d97fe500c89cc9e5b12
psid-questionnaire-occurrence:9969e959ae2d58b54b5fbdfc4f4e6e0f8141f628d67415370e1ccd129017a4fb
psid-questionnaire-occurrence:4b6c12f1e8e57edd45a3d43a772c69d923ec4c72d8292cdff1ca1f9c0a069e3b
psid-questionnaire-occurrence:5eb05b791f0abad829debc9863433e0a8e7bd254aa18ac51b6c750caa48bb46a
psid-questionnaire-occurrence:d662043b204306d6c052f412fe674574e80fd1a40aca75b1842a212bb1fe8f68
psid-questionnaire-occurrence:5e89bb2a5186c4afee4a6a2289a4686ddcee89aeeae089b42c24e3ce9ff72708
""".split()
)
SEMANTICALLY_DECISIVE_FRAGMENT_INSTRUCTION_IDS = frozenset(
    """
psid-questionnaire-occurrence:9582333627cf26561426cef746e0ce6e66c6028d685f25468f2872baeb54c7dc
psid-questionnaire-occurrence:116697de22b8368ba1f36cd21df28d50aa6a4c262f983ba40f0c72f45ad8dc42
psid-questionnaire-occurrence:dfd221be448ee0468cc480dde0566ce1ff56f88eae3c99709ef0ae81a1e72ef0
psid-questionnaire-occurrence:38b4a4305699d9807fb95155c3a0d5ffb19292c5ecaec8130c04c183c697f504
psid-questionnaire-occurrence:357281a0ee7987a14867f92a263f3aa1097d8bb5202d45820e4e8af363a7157b
psid-questionnaire-occurrence:a769c4a969cdaca2142d0aab2e2cee8aa2f9f83d4fe1abf4235e4bd9acb5c9f5
psid-questionnaire-occurrence:128e68c5f8b2bb12a7a03f63910789effa54a1c40987efeda703132349b339da
psid-questionnaire-occurrence:499d1b00af29b5829c212f706bbcfb02780c344584b9b1e47cb3b693146ffd39
psid-questionnaire-occurrence:c38bfe9eb40d5028cec6d604b144eb54eee451a810bae4fd289bca5eefa27a32
psid-questionnaire-occurrence:35833279648220c82c4340b8a40d6823b3d3fc231eca8180cdd635479521a052
psid-questionnaire-occurrence:4d30184605579b75c3e2830294e611d79c4c58faee7419bebc24a28184d9f990
psid-questionnaire-occurrence:913192535eea428b2564426ecc0722bdf6b5c6166ef46d8f4547afb2882f5028
psid-questionnaire-occurrence:bbdbc781bb95e0d12442053e1bf4a84094b4b88c42c8e2edb728d659891ee5dc
psid-questionnaire-occurrence:691e75cf4e4cf1a6d1937617e816779e1648588d0d2d33ef9561dab1438e2f0a
psid-questionnaire-occurrence:c69bb0d19859f92a9be51e97762531f5640f4fdebb5590bb6da568b40cc32c54
psid-questionnaire-occurrence:c020df281459e26b8415bdb22c92f9ce30a0302cc21732ddaad3039ddf77b610
psid-questionnaire-occurrence:c3275a8794901e02bc0e54360ec899e43e61838b586fcf4fd171dbadd368a3ef
psid-questionnaire-occurrence:3874a79cb10aea6c83c58f2b7fc80950b78e09ad893718dccb38f8ebb2da1e23
psid-questionnaire-occurrence:ff130ead6f6c53c4759fd4b3e90904e46223850e73772a94277448f7aeeaaa7d
psid-questionnaire-occurrence:e2a45222a0321da6e02f24873de45bfb4401cb12a315bdbd96750c6afcfc286f
psid-questionnaire-occurrence:c7bc4ab94c2320b283203e6d6d677c21f84b9d61e10880b5f9b4d9c0261386d0
psid-questionnaire-occurrence:7c402f2de259365c89ff3074ff9caf72130b35efce2559e9383a1d6ae8e347fe
psid-questionnaire-occurrence:c4f0f31a3b48fdc6794b81acc506b3a40b754a092e3073cdec008faf0ac52a3b
psid-questionnaire-occurrence:2731f348724837fcf2e8be8fac3d039705671d63b5b4496b18c0a82694395e2f
psid-questionnaire-occurrence:1dc6faa8137b8a9b0ec95a605682d2982b9baf1eddd86dee961ea99d0ba4510a
psid-questionnaire-occurrence:e44e06b2a1a7e984e7321edb4eac1f28824855c2e9bbfbb2bc099ff6e5e43446
psid-questionnaire-occurrence:65f1752d0f6d39346c412c1d492e574979277aa6c78094f1ad79f0d53cf57452
psid-questionnaire-occurrence:677f49917f36f8925b3129f47f93aa914ba9ae2fb6612a42839caac415d7a56e
psid-questionnaire-occurrence:61f38513d63c0700bddf9bee561b472c15d7d64efd12ca7ab544d281120f3790
psid-questionnaire-occurrence:86c314ec0cbf47b1935cc4efbbdd5a54f168602175ceb959bd18d887350cad30
psid-questionnaire-occurrence:a391cdd9c11b2efa526ca3df01e0acdae2668adcdf00ad547c2e25a7feefbc44
psid-questionnaire-occurrence:cf07296eb4c2e4bf77a81fabe6ec3254e12debe22805dd0dec123a4370e87852
psid-questionnaire-occurrence:2a56a4440b9e5714367c02fa09a0a480d015258b5023ddf32de22bf6871d3ace
psid-questionnaire-occurrence:7bbe18e8a8c52ccfa5e4bfdfe884bc8829006e3a55cad2861b674621042f9233
""".split()
)
SOURCE_INSTRUCTION_FRAGMENT_IDS = (
    ROUND_THREE_FRAGMENT_RESEAL_INSTRUCTION_IDS
    | ROUND_FOUR_NEW_FRAGMENT_RESEAL_INSTRUCTION_IDS
    | SEMANTICALLY_DECISIVE_FRAGMENT_INSTRUCTION_IDS
)
if len(SOURCE_INSTRUCTION_FRAGMENT_IDS) != 48:
    raise RuntimeError("source-instruction fragment ledger does not cover 48")

SEMANTIC_ALIAS_EQUIVALENCE_FINDING = (
    "exact_source_text_proves_named_instruction_import_or_occurrence_"
    "equivalence"
)
SEMANTIC_ALIAS_REDIRECTION_FINDING = (
    "affirmative_named_destination_and_explicit_current_location_exclusion"
)
SEMANTIC_ALIAS_ADJUDICATED_INSTRUCTION_IDS = (
    SEMANTIC_ALIAS_EQUIVALENCE_INSTRUCTION_IDS
    | frozenset(SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION)
    | EXCLUSIVE_DESTINATION_REDIRECTION_INSTRUCTION_IDS
)
if (
    SEMANTIC_ALIAS_EQUIVALENCE_INSTRUCTION_IDS
    & frozenset(SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION)
    or SEMANTIC_ALIAS_EQUIVALENCE_INSTRUCTION_IDS
    & EXCLUSIVE_DESTINATION_REDIRECTION_INSTRUCTION_IDS
    or frozenset(SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION)
    & EXCLUSIVE_DESTINATION_REDIRECTION_INSTRUCTION_IDS
):
    raise RuntimeError("semantic alias adjudication arms overlap")

# Round three is a complete semantic ledger, not a fallback predicate.  The
# sets below exact-cover the 42 populated predecessor proof candidates when
# combined.  Their emitted rows carry each instruction and endpoint's exact
# text, digest, page, and byte span as the source citation for the decision.
AGGREGATE_RELATION_LAW_GAP_EVIDENCE_IDS = frozenset(
    {
        "rq-local-repeat-evidence:0e380305f67b13fceef903d3e1c24590891a63e1beeefbc6953d58334baaf4e6",
        "rq-local-repeat-evidence:f3b859c0dbda01517b66f70b0652a84d0c0b048a38c4deea4477ea05d3be5045",
        "rq-local-repeat-evidence:da2954a94634f3371ef85000ce0db5f121f0968a6704264434573867c6522495",
        "rq-local-repeat-evidence:e5ff3d4e974f7c527fd7be988d6075b152586ed1f6ec06f37711bb47667b191d",
        "rq-local-repeat-alias-evidence:db641c23f0d13b3befcdde005cf6b3804cc85a7e3985804091a59d826584a0c1",
        "rq-local-repeat-alias-evidence:e744b798ebfb58ba3b8e1c28c7b0c5cbeadfadd649b5951f25a9326b1dafc0bf",
        "rq-local-repeat-alias-evidence:9aed9fbcbb6cbe3f0697b12e95522c1a9e539b5e4e2a031b3b2bb531b45f3ced",
        "rq-local-repeat-alias-evidence:92db20a47e9e0771b874238f39d920d69203e822e5cb28cf461394fa9d8bf254",
        "rq-local-repeat-alias-evidence:71cbb45447d775ba33f493a3e0ebe800226d463bf73905566216fcb53287512d",
        "rq-local-repeat-evidence:4ac3d89c423be55bac47c13cced2fd92151014ef3a45d95fba4b2999cca518f2",
        "rq-local-repeat-alias-evidence:1c3c1a81c8d783c04813b7e1c0a5654ecab4f43d0ffd290c95a391c5daf54547",
        "rq-local-repeat-alias-evidence:c0fdbc2f6b82371351dbcf266ab083dba8c20cce3298e283012ec5c618bca868",
        "rq-local-repeat-alias-evidence:1120df9c2c375e51c32b9a546f3dbbd176366ba6de7258c38c344dd84b5f0734",
    }
)
REDIRECTION_LAW_GAP_EVIDENCE_IDS = frozenset(
    {
        "rq-local-repeat-evidence:5977fa11c007f370ece29867bc0d2b6c5d492990396b50d86959b1ec5ec87927",
    }
)
PREDECESSOR_SEAL_DEFECT_EVIDENCE_IDS = frozenset(
    {
        "rq-local-repeat-evidence:c93bb69e6a4c04717efd8b68e71799b5b4f3cb1c1c20a1b31afe2852d04dab67",
        "rq-local-repeat-evidence:0c25501bcb134ddd36f5f076978ebd01a02d3e731772c4ae5de182d81a76a487",
        "rq-local-repeat-alias-evidence:c7020c1c35780475871c3d0ddce0767b1fe22b6f6c45c79fbd03093519ffc716",
        "rq-local-repeat-alias-evidence:b8ea2ca5e2b198e2c4f9ec8ef9608a68b53b8c7a0f76435f4c2ca0db3f57a456",
        "rq-local-repeat-alias-evidence:78c2d51532910f9dbebaac790485bb20e2a0d907e632f4d32c327c185d52a34c",
        "rq-local-repeat-alias-evidence:224c03c08758f9ea5f0e6920b949ff50afc42ef2165923be05fc7646b8249623",
        "rq-local-repeat-alias-evidence:e3ca944c92c9a5053ff989551b47d8cfbe885565bfc6e0f59886c74a8b3a1331",
        "rq-local-repeat-alias-evidence:238d3e9a1faceb345a3f13380b6cc04a97ed5c9a54d7fe931c178588415c9d11",
        "rq-local-repeat-alias-evidence:6c1381f0c6a1ee424dc21dee75fde1263efbe2cdaa4d4b396a28847fea3b6b89",
        "rq-local-repeat-alias-evidence:6d0ad010bf859e35f2d90ef9ba2dceaf60f4625dacac9cd6c4ed0ccdf814f526",
        "rq-local-repeat-alias-evidence:122109cba974f0e5ed897f0236668a04ed2dca7e5c15f3fa2c47fbd69bec633a",
        "rq-local-repeat:d20165da2c897270b8d8708bdd2ee7a860d6c3ac905c9e05dcc622a75b413a92",
        "rq-local-repeat-alias-evidence:b2ff04405ce6c20fb6848441dd5fc249ac55b99c6ce21a60ff1ef331b42d8a19",
        "rq-local-repeat-alias-evidence:e4b4c44f443929ce8facfa51ce2e318e201490d259b01e507d4dded083e8fba2",
        "rq-local-repeat-alias-evidence:6c17ebd0a0c97a5b46fef9ff2c5326fe45acf482647c6a2fd0d3bf542be17b22",
        "rq-local-repeat-alias-evidence:f44ce5328602c75bcde9b50b2de94d68582a6fe7080eea03b1de32e622171a22",
        "rq-local-repeat-alias-evidence:f4de9f70a2b5a851a4d1e56c63dc7a35574c14d877122f6c0983d2e6268fb516",
        "rq-local-repeat-evidence:d6f7cdeab7418133a2bb1ea992d0b42e0749079e1aa890e799f96310d690bd0c",
        "rq-local-repeat-evidence:c9b24cb9e34a7050a567093ee0f0500df3e221dd2afa9adfdaba02010fd31509",
        "rq-local-repeat-evidence:db438aefe04bee804bdc15f683dba9f90d0963871a6242217b18e09bdbed01c4",
        "rq-local-repeat-evidence:6ce1ef4653dfa56a49ff6baf30052132630c1ed47dfb246dcf38c1e63a24f83f",
        "rq-local-repeat-evidence:7e1395227e1f81c5fe864d17e319e56b724424eab5163df68109dd85f81ce5c7",
        "rq-local-repeat-evidence:e1e5e2a1b422ae3334fd657b68dbd1922e56e36165b4913c8d309896ac72d6d4",
        "rq-local-repeat-evidence:c207d07c88d2bef6b99a038d94a1f870ac038072de4c005241ab9ce3f79439c3",
        "rq-local-repeat-evidence:fd7a9eebc0d44fe9cf4ba8795b478b2d6a933b8aa42dd45d52cb561328e86ada",
        "rq-local-repeat-evidence:bb6ce7690468d1ef2e0d4a22bfa831bf9b81f7824db8a9dd59e06df44434c877",
        "rq-local-repeat-evidence:525a55100f92a4f6f05e156d9d784029ea29126e2c5374195545513375b36e8c",
        "rq-local-repeat-evidence:a06a1898968a9dc0d44b34bbd5ca9efc9bb856a56bde685815ff6621d1f82b39",
    }
)

PARENT_KIND_TO_CATEGORY = {
    "job_anchor": "source_job",
    "role_total_anchor": "role_total_sentinel",
    "farm_aggregate_anchor": "farm_aggregate_sentinel",
    "business_aggregate_anchor": "business_aggregate_sentinel",
}
CANDIDATE_SENTINEL_PARENT_NODE_IDS = {
    "role_total_anchor": "a12-candidate-parent-node:role-total-sentinel",
    "farm_aggregate_anchor": "a12-candidate-parent-node:farm-aggregate-sentinel",
    "business_aggregate_anchor": (
        "a12-candidate-parent-node:business-aggregate-sentinel"
    ),
}
INELIGIBLE_PARENT_CATEGORY = {
    "role_anchor": "ineligible_role_anchor",
    "context_anchor": "ineligible_context_anchor",
    "remuneration_component_anchor": (
        "ineligible_remuneration_component_anchor"
    ),
}

PILOT_POSITIONS = (
    1,
    2,
    3,
    9,
    14,
    18,
    23,
    33,
    36,
    40,
    53,
    56,
    58,
    65,
    66,
    78,
)
CONTROL_POSITIONS = (3, 18, 23, 53, 65, 78)
PILOT_TAGS = {
    1: ("role_canonical_and_J8_head_witness",),
    2: ("null_identifier_she_role_witness",),
    3: ("era_1_control",),
    9: ("zero_parent_component_witness",),
    14: ("q74_outside_domain_repeat_carrier",),
    18: ("era_2_control",),
    23: ("era_3_control",),
    33: ("multi_parent_component_witness",),
    36: ("aggregate_as_component_slot_seal_defect",),
    40: ("q87_outside_domain_repeat_carrier",),
    53: ("era_4_local_edge_schema_control",),
    56: ("fam1996_outside_domain_repeat_carrier",),
    58: ("fam1997_outside_domain_and_aggregate_relation_carrier",),
    65: ("era_5_control",),
    66: ("fam2005_outside_domain_and_in_domain_redirection_carrier",),
    78: ("era_6_control",),
}

ERA_SEALS = (
    {
        "era_id": "wave1968_ry1968_1974_early_totals",
        "era_order_position": 1,
        "positions": tuple(range(1, 17)),
        "seal_commit": "a75151c42e4612a92de7946e2dbc835914f1bb0d",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "wave1968_ry1968_1974_early_totals_preparation_seal_v1.json"
        ),
        "byte_size": 14_480,
        "raw_sha256": (
            "bcc3c542bc7e8410e025e4a3aa23ea0bb42da5b579d0c4d346746a9632911a44"
        ),
        "content_sha256": (
            "b07906b0a0f62b2be2a0e3f5d68c5b10bd6f1b1d51d8b13d747603b47980d69a"
        ),
    },
    {
        "era_id": "ry1975_1977_spouse_concept_seam",
        "era_order_position": 2,
        "positions": tuple(range(17, 23)),
        "seal_commit": "9758ca7c013b144eb319ffe97f75b5817670603f",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry1975_1977_spouse_concept_seam_preparation_seal_v1.json"
        ),
        "byte_size": 7_883,
        "raw_sha256": (
            "5a954d5148706378df938231378a81af8f3412024e86c0ee9b1a4aec52f423aa"
        ),
        "content_sha256": (
            "3ac7136e2c8917b6ea0e1321f4a9f2dc6d8305d01f998d2bc4eddb009361413c"
        ),
    },
    {
        "era_id": "ry1978_1992_pre_er_totals",
        "era_order_position": 3,
        "positions": tuple(range(23, 52)),
        "seal_commit": "e06dd4498dfc7a3b2a2f259f4da2977bea94b949",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry1978_1992_pre_er_totals_preparation_seal_v1.json"
        ),
        "byte_size": 23_106,
        "raw_sha256": (
            "59ae2e095e079b16b91c1cf5138803939f7b65f951e3fff6b4f789d428c1dde2"
        ),
        "content_sha256": (
            "f1a80b78800acb7ce8e53f3db8422a9ccaad88673c924ae03420045201be0ee7"
        ),
    },
    {
        "era_id": "ry1993_2001_er_transition",
        "era_order_position": 4,
        "positions": tuple(range(52, 64)),
        "seal_commit": "b5dc849d8f82f54b46697808444517f26e4015c6",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry1993_2001_er_transition_preparation_seal_v1.json"
        ),
        "byte_size": 11_863,
        "raw_sha256": (
            "a58044964bea7bef6c71b28f5f408f658da17eb18e1563c213d4102c84654e9e"
        ),
        "content_sha256": (
            "a4d07990c2066e1e8362dc5339c5fca21bd5b96534781c5a8fe08e7a1dd4a291"
        ),
    },
    {
        "era_id": "ry2002_2014_modern_bc_de",
        "era_order_position": 5,
        "positions": tuple(range(64, 78)),
        "seal_commit": "872a27878a8beaab22c9871775416396ac3425d5",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry2002_2014_modern_bc_de_preparation_seal_v1.json"
        ),
        "byte_size": 13_171,
        "raw_sha256": (
            "221c28d010cb92a4566910515a9cbd0b342503452de9b9c8e1c223b6bf06cdc1"
        ),
        "content_sha256": (
            "c180fd79d9b89b5018d883ae0e4835913e994e5c11d2645ae1af63b8721c6a18"
        ),
    },
    {
        "era_id": "ry2015_2022_exclusion_lineage",
        "era_order_position": 6,
        "positions": tuple(range(78, 82)),
        "seal_commit": SOURCE_COMMIT,
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry2015_2022_exclusion_lineage_preparation_seal_v1.json"
        ),
        "byte_size": 6_574,
        "raw_sha256": (
            "3238516e70d8283fa7172308432e5bb1b4f710a06c758bdb51618aca627b1bd9"
        ),
        "content_sha256": (
            "cc38de5e0875f054a97b9b0c93d4a215d4b5616758e04fb58b6b55f91686c7e6"
        ),
    },
)

OUTPUT_FILENAMES = {
    "slice": "pilot_slice_manifest_v1.json",
    "sweeps": "corpus_exhaustive_targeted_sweeps_v1.json",
    "derived": "derived_class_complement_sweeps_v1.json",
    "predecessor": "predecessor_defect_adjudication_v1.json",
    "role": "role_assignment_pilot_v1.json",
    "repeat": "outside_domain_repeat_disposition_pilot_v1.json",
    "component": "component_parent_disposition_pilot_v1.json",
    "gate": "pilot_gate_result_v1.json",
}


class BuildError(RuntimeError):
    """Raised when a source or artifact law fails closed."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    """Return the campaign's terminal-LF canonical strict JSON bytes."""
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


def _reject_constant(value: str) -> None:
    raise BuildError(f"non-finite JSON constant: {value}")


def _finite_exact_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise BuildError(f"non-finite JSON number: {token}")
    if decimal.Decimal(token) != decimal.Decimal(str(value)):
        raise BuildError(f"inexact JSON number: {token}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(raw: bytes, label: str) -> Any:
    """Parse one UTF-8 strict JSON value and reject duplicate members."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BuildError(f"{label}: invalid UTF-8") from error
    try:
        if text.startswith("\ufeff"):
            raise BuildError(f"{label}: leading BOM")
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_exact_float,
        )
    except (
        BuildError,
        json.JSONDecodeError,
        OverflowError,
        RecursionError,
        decimal.DecimalException,
    ) as error:
        raise BuildError(f"{label}: invalid strict JSON") from error


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BuildError(message)


def _require_int(value: Any, label: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool),
        f"{label}: expected JSON integer",
    )
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    actual = frozenset(value)
    _require(
        actual == expected,
        f"{label}: keyset drift; missing={sorted(expected - actual)!r}, "
        f"extra={sorted(actual - expected)!r}",
    )


def _row_id(prefix: str, preimage: Sequence[Any]) -> str:
    return prefix + _sha256(canonical_bytes(list(preimage)))


def _domain_sha(rows: Sequence[Any]) -> str:
    return _sha256(canonical_bytes(list(rows)))


def _keyset_sha(ids: Sequence[str]) -> str:
    return _sha256(canonical_bytes(list(ids)))


def _load_pinned_semantic_specification(
    path: Path,
    *,
    expected_byte_size: int,
    expected_raw_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read one builder input only after its independent raw identity passes."""
    raw = path.read_bytes()
    _require(
        len(raw) == expected_byte_size,
        f"semantic specification byte-size drift: {path}",
    )
    _require(
        _sha256(raw) == expected_raw_sha256,
        f"semantic specification raw digest drift: {path}",
    )
    value = strict_json_loads(raw, str(path))
    _require(
        isinstance(value, dict),
        f"semantic specification is not object: {path}",
    )
    return value, {
        "path": path.relative_to(ROOT).as_posix(),
        "byte_size": len(raw),
        "raw_sha256": _sha256(raw),
    }


def _artifact(
    schema_version: str,
    id_prefix: str,
    authority_kind: str,
    body: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": schema_version,
        "authority_kind": authority_kind,
        **copy.deepcopy(dict(body)),
    }
    payload_sha = _sha256(canonical_bytes(payload))
    return {
        "schema_version": schema_version,
        "artifact_id": id_prefix + payload_sha,
        "authority_kind": authority_kind,
        **copy.deepcopy(dict(body)),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "payload_sha256": payload_sha,
        },
    }


def _validate_artifact_envelope(
    artifact: Mapping[str, Any],
    schema_version: str,
    id_prefix: str,
    authority_kind: str,
) -> None:
    _require(artifact.get("schema_version") == schema_version, "bad schema")
    _require(
        artifact.get("authority_kind") == authority_kind,
        "bad authority_kind",
    )
    artifact_id = artifact.get("artifact_id")
    _require(
        isinstance(artifact_id, str) and artifact_id.startswith(id_prefix),
        "bad artifact_id",
    )
    integrity = artifact.get("integrity")
    _require(isinstance(integrity, dict), "missing integrity")
    _require_exact_keys(
        integrity,
        ARTIFACT_INTEGRITY_KEYS,
        f"{schema_version} integrity",
    )
    _require(
        integrity.get("canonicalization") == CANONICALIZATION,
        "bad canonicalization",
    )
    payload = {
        key: copy.deepcopy(value)
        for key, value in artifact.items()
        if key not in {"artifact_id", "integrity"}
    }
    digest = _sha256(canonical_bytes(payload))
    _require(integrity.get("payload_sha256") == digest, "bad payload hash")
    _require(artifact_id == id_prefix + digest, "bad artifact ID digest")


def _nonauthority_statement() -> dict[str, Any]:
    return {
        "authority_admitted": False,
        "catalog_certified": False,
        "global_catalog_emitted": False,
        "hierarchy_emitted": False,
        "inventory_emitted": False,
        "legal_registry_emitted": False,
        "pilot_only": True,
        "q5_emitted": False,
        "r_q_emitted": False,
        "slot_emitted": False,
        "status": "PILOT_NONAUTHORITY",
        "wall_row_emitted": False,
    }


def _validate_design_prefix() -> dict[str, Any]:
    raw = DESIGN_PATH.read_bytes()
    _require(
        len(raw) >= DESIGN_PREFIX_BYTES,
        "revision-13 design prefix is truncated",
    )
    prefix = raw[:DESIGN_PREFIX_BYTES]
    _require(
        _sha256(prefix) == DESIGN_PREFIX_SHA256,
        "revision-13 design prefix drifted",
    )
    return {
        "path": "docs/design/covered_earnings_correction.md",
        "byte_size": DESIGN_PREFIX_BYTES,
        "sha256": DESIGN_PREFIX_SHA256,
        "identity_scope": "immutable_revision_13_prefix",
    }


class SourceReader:
    """Read exact files from either the pinned Git tree or a verified root."""

    def __init__(self, source_root: Path | None) -> None:
        self.source_root = source_root.resolve() if source_root else None
        if self.source_root is None:
            command = ["git", "cat-file", "-e", f"{SOURCE_COMMIT}^{{commit}}"]
            result = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            _require(
                result.returncode == 0,
                f"pinned source commit unavailable: {SOURCE_COMMIT}",
            )
        else:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.source_root,
                check=True,
                capture_output=True,
                text=True,
            )
            _require(
                result.stdout.strip() == SOURCE_COMMIT,
                "source root is not at the pinned corpus commit",
            )

    def read(self, path: str) -> bytes:
        if self.source_root is not None:
            candidate = (self.source_root / path).resolve()
            _require(
                candidate.is_relative_to(self.source_root),
                f"source path escaped root: {path}",
            )
            return candidate.read_bytes()
        result = subprocess.run(
            ["git", "show", f"{SOURCE_COMMIT}:{path}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        _require(result.returncode == 0, f"missing pinned source path: {path}")
        return result.stdout


@dataclass(frozen=True)
class NormalizedDocument:
    position: int
    era_id: str
    annotation_path: str
    annotation_identity: dict[str, Any]
    source_document_id: str
    source_document_row: Mapping[str, Any]
    candidate_artifact_identity: Mapping[str, Any]
    whole_document_locator: Mapping[str, Any] | None
    schema_version: str
    page_count: int
    page_text_utf8_sha256_by_number: Mapping[int, str]
    questionnaire_page_rows_by_number: Mapping[int, Mapping[str, Any]]
    questionnaire_occurrence_rows_by_id: Mapping[str, Mapping[str, Any]]
    occurrence_count: int
    flow_count: int
    field_purpose_count: int
    repeat_occurrence_ids: tuple[str, ...]
    repeat_occurrence_rows: tuple[dict[str, Any], ...]
    anchor_rows: tuple[dict[str, Any], ...]
    evidence_rows: tuple[dict[str, Any], ...]


def _classification(row: Mapping[str, Any]) -> str:
    value = row.get("classification", row.get("local_classification"))
    _require(isinstance(value, str) and value, "missing classification")
    return value


def _evidence_id(row: Mapping[str, Any]) -> str:
    for key in (
        "local_repeat_alias_evidence_id",
        "local_repeat_evidence_id",
        "local_repeat_or_alias_evidence_id",
    ):
        value = row.get(key)
        if value is not None:
            _require(isinstance(value, str) and value, "bad evidence ID")
            return value
    raise BuildError("missing local evidence ID")


def _evidence_relation(row: Mapping[str, Any]) -> str:
    value = row.get("relation", row.get("alias_relation"))
    _require(value in ALLOWED_LOCAL_EVIDENCE_RELATIONS, "bad repeat relation")
    return value


def _endpoint_ids(
    row: Mapping[str, Any],
    local_id_to_occurrence: Mapping[str, str],
) -> tuple[list[str], list[str]]:
    if "alias_anchor_source_occurrence_ids" in row:
        return (
            list(row["alias_anchor_source_occurrence_ids"]),
            list(row["canonical_anchor_source_occurrence_ids"]),
        )
    if "alias_anchor_occurrence_id" in row:
        alias = row["alias_anchor_occurrence_id"]
        canonical = row["referenced_anchor_occurrence_id"]
        return (
            [] if alias is None else [alias],
            [] if canonical is None else [canonical],
        )
    alias_local = row["alias_local_anchor_id"]
    canonical_local = row["canonical_local_anchor_id"]
    return (
        [] if alias_local is None else [local_id_to_occurrence[alias_local]],
        (
            []
            if canonical_local is None
            else [local_id_to_occurrence[canonical_local]]
        ),
    )


def _source_instruction_ids(row: Mapping[str, Any]) -> list[str]:
    if "source_instruction_occurrence_ids" in row:
        return list(row["source_instruction_occurrence_ids"])
    value = row.get("source_occurrence_id")
    return [] if value is None else [value]


def _occurrence_catalog_domain(kind: str) -> str:
    if kind == "role_anchor":
        return "role"
    if kind == "job_anchor":
        return "job_slot"
    if kind in {"context_anchor", "remuneration_component_anchor"}:
        return "component_slot"
    if kind in AGGREGATE_OCCURRENCE_KINDS:
        return "aggregate"
    return f"outside_catalog:{kind}"


def _normalize_document(
    raw: bytes,
    input_identity: Mapping[str, Any],
    era_id: str,
) -> NormalizedDocument:
    path = input_identity["annotation_path"]
    _require(len(raw) == input_identity["byte_size"], f"{path}: size drift")
    _require(
        _sha256(raw) == input_identity["raw_sha256"],
        f"{path}: raw SHA-256 drift",
    )
    data = strict_json_loads(raw, path)
    _require(isinstance(data, dict), f"{path}: top level is not object")
    position = _require_int(data.get("document_source_position"), path)
    _require(
        position == input_identity["document_source_position"],
        f"{path}: source position drift",
    )
    _require(
        data.get("schema_version") == input_identity["schema_version"],
        f"{path}: schema drift",
    )
    _require(
        data.get("artifact_id") == input_identity["artifact_id"],
        f"{path}: artifact ID drift",
    )
    source_row = data["document_source_row"]
    source_document_id = source_row["source_document_id"]
    _require(
        source_document_id == input_identity["source_document_id"],
        f"{path}: source document drift",
    )

    occurrences = data["questionnaire_occurrence_rows"]
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    occurrence_source_order = {
        row["questionnaire_occurrence_id"]: index
        for index, row in enumerate(occurrences)
    }
    _require(
        len(occurrence_by_id) == len(occurrences),
        f"{path}: duplicate occurrence ID",
    )
    anchors = data["local_anchor_classification_rows"]
    local_id_to_occurrence = {
        row["local_anchor_classification_id"]: row["source_occurrence_id"]
        for row in anchors
    }
    _require(
        len(local_id_to_occurrence) == len(anchors),
        f"{path}: duplicate local anchor ID",
    )

    normalized_anchors: list[dict[str, Any]] = []
    anchor_by_occurrence: dict[str, dict[str, Any]] = {}
    for source_row_index, row in enumerate(anchors):
        occurrence_id = row["source_occurrence_id"]
        _require(
            occurrence_id in occurrence_by_id,
            f"{path}: anchor occurrence is missing",
        )
        occurrence = occurrence_by_id[occurrence_id]
        raw_parent_ids = row.get(
            "parent_source_occurrence_ids",
            row.get(
                "parent_anchor_occurrence_ids",
                row.get("parent_local_anchor_ids", []),
            ),
        )
        parent_ids = [
            local_id_to_occurrence.get(parent_id, parent_id)
            for parent_id in raw_parent_ids
        ]
        for parent_id in parent_ids:
            _require(
                parent_id in occurrence_by_id,
                f"{path}: parent occurrence is missing",
            )
        normalized = {
            "source_row_index": source_row_index,
            "local_anchor_classification_id": row[
                "local_anchor_classification_id"
            ],
            "source_occurrence_id": occurrence_id,
            "node_domain": row["node_domain"],
            "classification": _classification(row),
            "occurrence_kind": occurrence["occurrence_kind"],
            "printed_identifier": row.get("printed_identifier"),
            "exact_label": row.get("exact_label"),
            "exact_label_sha256": row.get("exact_label_sha256"),
            "occurrence_matched_text": occurrence["matched_text"],
            "occurrence_matched_utf8_sha256": occurrence[
                "matched_utf8_sha256"
            ],
            "occurrence_page_number": occurrence["page_number"],
            "occurrence_utf8_byte_start": occurrence["utf8_byte_start"],
            "occurrence_utf8_byte_end": occurrence["utf8_byte_end"],
            "parent_occurrence_ids": parent_ids,
            "parent_occurrence_kinds": [
                occurrence_by_id[parent_id]["occurrence_kind"]
                for parent_id in parent_ids
            ],
        }
        _require(
            occurrence_id not in anchor_by_occurrence,
            f"{path}: occurrence has duplicate anchor classification",
        )
        normalized_anchors.append(normalized)
        anchor_by_occurrence[occurrence_id] = normalized

    evidence_input = data.get(
        "local_repeat_alias_evidence_rows",
        data.get("local_repeat_or_alias_evidence_rows", []),
    )
    normalized_evidence: list[dict[str, Any]] = []
    for source_row_index, row in enumerate(evidence_input):
        aliases, canonicals = _endpoint_ids(row, local_id_to_occurrence)
        endpoint_ids = [*aliases, *canonicals]
        endpoint_rows = [
            anchor_by_occurrence.get(value) for value in endpoint_ids
        ]
        _require(
            all(value is not None for value in endpoint_rows),
            f"{path}: local proof endpoint is not a classified anchor",
        )
        concrete_rows = [value for value in endpoint_rows if value is not None]
        occurrence_kinds = [
            value["occurrence_kind"] for value in concrete_rows
        ]
        raw_node_domains = [value["node_domain"] for value in concrete_rows]
        classifications = [value["classification"] for value in concrete_rows]
        catalog_domains = [
            _occurrence_catalog_domain(kind) for kind in occurrence_kinds
        ]
        flags = {
            "touches_noncatalog_aggregate_endpoint": any(
                kind in AGGREGATE_OCCURRENCE_KINDS for kind in occurrence_kinds
            ),
            "occurrence_derived_domain_crossing": (
                len(set(catalog_domains)) > 1
            ),
            "raw_node_domain_crossing": len(set(raw_node_domains)) > 1,
            "context_remuneration_mix": {
                "context_anchor",
                "remuneration_component_anchor",
            }.issubset(set(occurrence_kinds)),
            "head_spouse_mix": {
                ROLE_HEAD,
                ROLE_SPOUSE,
            }.issubset(set(classifications)),
        }
        flags["corrected_catalog_domain_crossing"] = flags[
            "occurrence_derived_domain_crossing"
        ]
        instructions = _source_instruction_ids(row)
        evidence_ids = list(row["evidence_occurrence_ids"])
        _require(
            all(
                value in occurrence_by_id
                for value in [*instructions, *evidence_ids]
            ),
            f"{path}: instruction or evidence occurrence is missing",
        )
        evidence_arrays_unique_disjoint = (
            len(aliases) == len(set(aliases))
            and len(canonicals) == len(set(canonicals))
            and not set(aliases) & set(canonicals)
            and len(instructions) == len(set(instructions))
            and len(evidence_ids) == len(set(evidence_ids))
        )
        evidence_arrays_source_ordered = all(
            values
            == sorted(values, key=lambda value: occurrence_source_order[value])
            for values in (aliases, canonicals, instructions, evidence_ids)
        )
        normalized_evidence.append(
            {
                "source_row_index": source_row_index,
                "local_evidence_id": _evidence_id(row),
                "relation": _evidence_relation(row),
                "handoff_status": row.get(
                    "handoff_status", row.get("resolution_status")
                ),
                "source_instruction_occurrence_ids": instructions,
                "source_instruction_occurrence_kinds": [
                    occurrence_by_id[value]["occurrence_kind"]
                    for value in instructions
                ],
                "source_instruction_matched_texts": [
                    occurrence_by_id[value]["matched_text"]
                    for value in instructions
                ],
                "source_instruction_matched_utf8_sha256s": [
                    occurrence_by_id[value]["matched_utf8_sha256"]
                    for value in instructions
                ],
                "source_instruction_page_numbers": [
                    occurrence_by_id[value]["page_number"]
                    for value in instructions
                ],
                "source_instruction_utf8_byte_starts": [
                    occurrence_by_id[value]["utf8_byte_start"]
                    for value in instructions
                ],
                "source_instruction_utf8_byte_ends": [
                    occurrence_by_id[value]["utf8_byte_end"]
                    for value in instructions
                ],
                "alias_anchor_occurrence_ids": aliases,
                "canonical_anchor_occurrence_ids": canonicals,
                "evidence_occurrence_ids": evidence_ids,
                "evidence_arrays_unique_disjoint": (
                    evidence_arrays_unique_disjoint
                ),
                "evidence_arrays_source_ordered": (
                    evidence_arrays_source_ordered
                ),
                "unresolved_target_reference": row.get(
                    "unresolved_target_reference"
                ),
                "endpoint_occurrence_kinds": occurrence_kinds,
                "endpoint_raw_node_domains": raw_node_domains,
                "endpoint_classifications": classifications,
                "endpoint_printed_identifiers": [
                    value["printed_identifier"] for value in concrete_rows
                ],
                "endpoint_matched_texts": [
                    value["occurrence_matched_text"] for value in concrete_rows
                ],
                "endpoint_matched_utf8_sha256s": [
                    value["occurrence_matched_utf8_sha256"]
                    for value in concrete_rows
                ],
                "endpoint_page_numbers": [
                    occurrence_by_id[value]["page_number"]
                    for value in endpoint_ids
                ],
                "endpoint_utf8_byte_starts": [
                    occurrence_by_id[value]["utf8_byte_start"]
                    for value in endpoint_ids
                ],
                "endpoint_utf8_byte_ends": [
                    occurrence_by_id[value]["utf8_byte_end"]
                    for value in endpoint_ids
                ],
                "defect_flags": flags,
            }
        )

    field_purpose_count = sum(
        row["occurrence_kind"] == "field_purpose_prompt" for row in occurrences
    )
    repeat_ids = tuple(
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    )
    repeat_rows = tuple(
        {
            "source_occurrence_id": row["questionnaire_occurrence_id"],
            "matched_text": row["matched_text"],
            "matched_utf8_sha256": row["matched_utf8_sha256"],
            "page_number": row["page_number"],
            "utf8_byte_start": row["utf8_byte_start"],
            "utf8_byte_end": row["utf8_byte_end"],
        }
        for row in occurrences
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    )
    identity = {
        "annotation_path": path,
        "artifact_id": input_identity["artifact_id"],
        "schema_version": input_identity["schema_version"],
        "source_document_id": source_document_id,
        "document_source_position": position,
        "byte_size": len(raw),
        "raw_sha256": _sha256(raw),
        "content_sha256": input_identity["content_sha256"],
    }
    return NormalizedDocument(
        position=position,
        era_id=era_id,
        annotation_path=path,
        annotation_identity=identity,
        source_document_id=source_document_id,
        source_document_row=source_row,
        candidate_artifact_identity=data["candidate_artifact_identity"],
        whole_document_locator=data.get(
            "whole_document_locator",
            next(iter(data.get("whole_document_locator_rows", [])), None),
        ),
        schema_version=data["schema_version"],
        page_count=len(data["questionnaire_page_rows"]),
        page_text_utf8_sha256_by_number={
            row["page_number"]: row["page_text_utf8_sha256"]
            for row in data["questionnaire_page_rows"]
        },
        questionnaire_page_rows_by_number={
            row["page_number"]: row for row in data["questionnaire_page_rows"]
        },
        questionnaire_occurrence_rows_by_id=occurrence_by_id,
        occurrence_count=len(occurrences),
        flow_count=len(data["flow_branch_rows"]),
        field_purpose_count=field_purpose_count,
        repeat_occurrence_ids=repeat_ids,
        repeat_occurrence_rows=repeat_rows,
        anchor_rows=tuple(normalized_anchors),
        evidence_rows=tuple(normalized_evidence),
    )


def _load_documents(
    reader: SourceReader,
) -> tuple[list[NormalizedDocument], dict[str, Any]]:
    annotation_inputs: list[tuple[dict[str, Any], str]] = []
    seal_identity_rows: list[dict[str, Any]] = []
    protocol_identity: dict[str, Any] | None = None
    seen_positions: list[int] = []
    for expected in ERA_SEALS:
        raw = reader.read(expected["path"])
        _require(len(raw) == expected["byte_size"], "era seal size drift")
        _require(
            _sha256(raw) == expected["raw_sha256"],
            "era seal raw SHA-256 drift",
        )
        seal = strict_json_loads(raw, expected["path"])
        _require(seal["era_id"] == expected["era_id"], "era ID drift")
        _require(
            seal["era_order_position"] == expected["era_order_position"],
            "era order drift",
        )
        positions = tuple(seal["document_source_positions"])
        _require(positions == expected["positions"], "era positions drift")
        _require(
            seal["integrity"]["content_sha256"] == expected["content_sha256"],
            "era seal content SHA-256 drift",
        )
        rows = seal["document_annotation_input_rows"]
        _require(len(rows) == len(positions), "era input count drift")
        _require(
            [row["document_source_position"] for row in rows]
            == list(positions),
            "era input order drift",
        )
        annotation_inputs.extend((row, expected["era_id"]) for row in rows)
        seen_positions.extend(positions)
        current_protocol = seal["stage2_protocol_identity"]
        if protocol_identity is None:
            protocol_identity = current_protocol
        else:
            _require(
                protocol_identity == current_protocol,
                "era seals disagree on stage-2 protocol identity",
            )
        seal_identity_rows.append(
            {
                "era_id": expected["era_id"],
                "era_order_position": expected["era_order_position"],
                "document_source_positions": list(positions),
                "seal_commit": expected["seal_commit"],
                "path": expected["path"],
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
                "content_sha256": expected["content_sha256"],
            }
        )
    _require(seen_positions == list(range(1, 82)), "incomplete corpus")
    _require(len(annotation_inputs) == 81, "annotation input count drift")

    documents = [
        _normalize_document(reader.read(row["annotation_path"]), row, era_id)
        for row, era_id in annotation_inputs
    ]
    _require(
        [document.position for document in documents] == list(range(1, 82)),
        "normalized document order drift",
    )
    source_identity = {
        "source_branch_label": SOURCE_BRANCH_LABEL,
        "source_commit": SOURCE_COMMIT,
        "document_count": 81,
        "stage2_protocol_identity": protocol_identity,
        "era_seal_rows": seal_identity_rows,
        "era_seal_count": len(seal_identity_rows),
        "era_seal_domain_sha256": _domain_sha(seal_identity_rows),
    }
    return documents, source_identity


def _source_component_rows(
    document: NormalizedDocument,
) -> list[dict[str, Any]]:
    return [
        row
        for row in document.anchor_rows
        if row["classification"] in COMPONENT_KINDS
    ]


def _role_anchor_rows(
    document: NormalizedDocument,
) -> list[dict[str, Any]]:
    return [
        row for row in document.anchor_rows if row["node_domain"] == "role"
    ]


def _parent_candidate_rows(
    component_kind: str,
    parent_ids: Sequence[str],
    parent_kinds: Sequence[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for parent_id, occurrence_kind in zip(
        parent_ids, parent_kinds, strict=True
    ):
        if occurrence_kind in PARENT_KIND_TO_CATEGORY:
            category = PARENT_KIND_TO_CATEGORY[occurrence_kind]
            eligible = True
            reason = None
            if category == "source_job":
                slot_kind = (
                    "context_only"
                    if component_kind == "source_context"
                    else "remuneration_component"
                )
            else:
                slot_kind = category.removesuffix("_sentinel")
        else:
            category = INELIGIBLE_PARENT_CATEGORY.get(
                occurrence_kind, f"ineligible_{occurrence_kind}"
            )
            eligible = False
            reason = "parent_occurrence_kind_outside_allowed_equations"
            slot_kind = None
        rows.append(
            {
                "parent_occurrence_id": parent_id,
                "parent_occurrence_kind": occurrence_kind,
                "parent_category": category,
                "eligible_parent": eligible,
                "derived_slot_kind": slot_kind,
                "ineligibility_reason": reason,
            }
        )
    return rows


def _component_shape_row(
    document: NormalizedDocument,
    anchor: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = _parent_candidate_rows(
        anchor["classification"],
        anchor["parent_occurrence_ids"],
        anchor["parent_occurrence_kinds"],
    )
    raw_count = len(candidates)
    eligible_count = sum(row["eligible_parent"] for row in candidates)
    if raw_count == 0:
        disposition = "zero_parent_terminal_disposition"
    elif raw_count == 1 and eligible_count == 1:
        disposition = "unique_parent_assignment"
    elif raw_count == 1:
        disposition = "zero_lawful_parent_terminal_disposition"
    else:
        disposition = "multi_parent_ambiguity_no_selection"
    categories = [row["parent_category"] for row in candidates]
    occurrence_id = anchor["source_occurrence_id"]
    resolution_id = _row_id(
        "a12-component-parent-resolution:",
        [
            document.source_document_id,
            occurrence_id,
            anchor["classification"],
            disposition,
            candidates,
        ],
    )
    return {
        "component_parent_resolution_id": resolution_id,
        "document_source_position": document.position,
        "source_document_id": document.source_document_id,
        "source_classification_id": anchor["local_anchor_classification_id"],
        "component_anchor_occurrence_id": occurrence_id,
        "component_kind": anchor["classification"],
        "serialized_parent_cardinality": raw_count,
        "eligible_parent_cardinality": eligible_count,
        "parent_candidate_rows": candidates,
        "parent_candidate_count": raw_count,
        "parent_candidate_domain_sha256": _domain_sha(candidates),
        "raw_parent_category_ambiguity": (
            raw_count > 1 and len(set(categories)) > 1
        ),
        "eligible_parent_category_ambiguity": (
            len(
                {
                    row["parent_category"]
                    for row in candidates
                    if row["eligible_parent"]
                }
            )
            > 1
        ),
        "eligible_ineligible_mixed_ambiguity": (
            raw_count > 1
            and any(row["eligible_parent"] for row in candidates)
            and any(not row["eligible_parent"] for row in candidates)
        ),
        "disposition": disposition,
        "forced_parent_selection": False,
        "tier_2_unique_parent_arm_eligible": (
            disposition == "unique_parent_assignment"
        ),
        "r_q_relationship_emitted": False,
        "status": "recorded_nonauthority_shape",
    }


TIER2_FIXTURE_MEMBER_KEYS = frozenset(
    {"component_anchor_occurrence_id", "parent_candidate_rows"}
)
TIER2_FIXTURE_CANDIDATE_KEYS = frozenset(
    {
        "source_parent_occurrence_id",
        "resolved_canonical_parent_node_id",
        "eligible_parent",
        "derived_slot_kind",
        "support_proof_id",
    }
)


def fold_component_class_fixture(
    component_kind: str,
    member_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Execute the prospective tier-2 class fold on synthetic source rows.

    This fixture mints no catalog, relationship, or authority identity.  It
    makes the class-level cardinality and no-selection law executable before
    ratification.  Callers remain responsible for proving that the supplied
    members and candidates exact-cover the pinned source domain.
    """
    _require(
        component_kind in COMPONENT_KINDS, "tier-2 fixture component kind"
    )
    _require(bool(member_rows), "tier-2 fixture empty component class")
    member_ids: list[str] = []
    raw_counts: list[int] = []
    all_candidates: list[Mapping[str, Any]] = []
    for member in member_rows:
        _require_exact_keys(
            member, TIER2_FIXTURE_MEMBER_KEYS, "tier-2 fixture member"
        )
        member_id = _require_string(
            member["component_anchor_occurrence_id"],
            "tier-2 fixture member occurrence",
        )
        member_ids.append(member_id)
        candidates = member["parent_candidate_rows"]
        _require(isinstance(candidates, list), "tier-2 fixture candidates")
        source_parent_ids: list[str] = []
        for candidate in candidates:
            _require_exact_keys(
                candidate,
                TIER2_FIXTURE_CANDIDATE_KEYS,
                "tier-2 fixture candidate",
            )
            source_parent_ids.append(
                _require_string(
                    candidate["source_parent_occurrence_id"],
                    "tier-2 fixture source parent",
                )
            )
            _require_boolean(
                candidate["eligible_parent"],
                "tier-2 fixture candidate eligibility",
            )
            _require_string(
                candidate["support_proof_id"],
                "tier-2 fixture support proof",
            )
            if candidate["eligible_parent"]:
                _require_string(
                    candidate["resolved_canonical_parent_node_id"],
                    "tier-2 fixture canonical parent",
                )
                _require_string(
                    candidate["derived_slot_kind"],
                    "tier-2 fixture slot kind",
                )
            else:
                _require(
                    candidate["resolved_canonical_parent_node_id"] is None
                    and candidate["derived_slot_kind"] is None,
                    "tier-2 fixture ineligible candidate resolved",
                )
        _require(
            len(set(source_parent_ids)) == len(source_parent_ids),
            "tier-2 fixture duplicate source parent",
        )
        raw_counts.append(len(candidates))
        all_candidates.extend(candidates)
    _require(
        len(set(member_ids)) == len(member_ids),
        "tier-2 fixture duplicate class member",
    )

    eligible_candidates = [
        candidate
        for candidate in all_candidates
        if candidate["eligible_parent"]
    ]
    canonical_parent_ids = list(
        dict.fromkeys(
            candidate["resolved_canonical_parent_node_id"]
            for candidate in eligible_candidates
        )
    )
    slot_kinds = list(
        dict.fromkeys(
            candidate["derived_slot_kind"] for candidate in eligible_candidates
        )
    )
    if all(count == 0 for count in raw_counts):
        disposition = "zero_parent_terminal_disposition"
    elif any(count > 1 for count in raw_counts):
        disposition = "multi_parent_ambiguity_no_selection"
    elif (
        all(count == 1 for count in raw_counts)
        and len(eligible_candidates) == len(member_rows)
        and len(canonical_parent_ids) == 1
        and len(slot_kinds) == 1
    ):
        disposition = "unique_parent_assignment"
    elif all(count == 1 for count in raw_counts) and not eligible_candidates:
        disposition = "zero_lawful_parent_terminal_disposition"
    else:
        disposition = "multi_parent_ambiguity_no_selection"

    unique = disposition == "unique_parent_assignment"
    return {
        "component_kind": component_kind,
        "member_occurrence_ids": member_ids,
        "member_count": len(member_ids),
        "member_raw_parent_cardinalities": raw_counts,
        "raw_parent_candidate_count": len(all_candidates),
        "eligible_parent_candidate_count": len(eligible_candidates),
        "resolved_canonical_parent_node_ids": canonical_parent_ids,
        "resolved_slot_kinds": slot_kinds,
        "disposition": disposition,
        "unique_parent_node_id": canonical_parent_ids[0] if unique else None,
        "unique_slot_kind": slot_kinds[0] if unique else None,
        "forced_parent_selection": False,
        "tier_2_relationship_arm_eligible": unique,
        "r_q_relationship_emitted": False,
        "status": "prospective_fixture_nonauthority",
    }


def fold_catalog_only_job_complement_fixture(
    candidate_job_class_id: str,
    candidate_relationship_component_class_ids: Sequence[str],
) -> dict[str, Any]:
    """Execute the catalog-only complement partition without minting it."""
    _require_string(candidate_job_class_id, "job complement fixture class")
    relationships = [
        _require_string(value, "job complement fixture relationship")
        for value in candidate_relationship_component_class_ids
    ]
    _require(
        len(set(relationships)) == len(relationships),
        "job complement fixture duplicate relationship",
    )
    catalog_only = not relationships
    return {
        "candidate_job_class_id": candidate_job_class_id,
        "candidate_relationship_component_class_ids": relationships,
        "candidate_relationship_count": len(relationships),
        "catalog_only_disposition_required": catalog_only,
        "coverage_arm": (
            "terminal_catalog_disposition"
            if catalog_only
            else "relationship_projection_nonempty"
        ),
        "catalog_only_disposition_emitted": False,
        "status": "prospective_fixture_nonauthority",
    }


def _candidate_alias_classes(
    documents: Sequence[NormalizedDocument],
    occurrence_kinds: frozenset[str],
    admitted_alias_pair_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build nonauthority classes from adjudicated atomic pairs only."""
    ordered_anchor_rows: list[dict[str, Any]] = []
    anchor_by_id: dict[str, dict[str, Any]] = {}
    for document in documents:
        for anchor in document.anchor_rows:
            if anchor["occurrence_kind"] not in occurrence_kinds:
                continue
            occurrence_id = anchor["source_occurrence_id"]
            ordered_anchor_rows.append(anchor)
            anchor_by_id[occurrence_id] = anchor

    parent = {occurrence_id: occurrence_id for occurrence_id in anchor_by_id}

    def find(occurrence_id: str) -> str:
        while parent[occurrence_id] != occurrence_id:
            parent[occurrence_id] = parent[parent[occurrence_id]]
            occurrence_id = parent[occurrence_id]
        return occurrence_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    source_order = {
        row["source_occurrence_id"]: index
        for index, row in enumerate(ordered_anchor_rows)
    }
    support_edges: list[tuple[list[str], dict[str, Any]]] = []

    exact_pair_groups: defaultdict[tuple[str, str, str], list[str]] = (
        defaultdict(list)
    )
    for anchor in ordered_anchor_rows:
        printed_identifier = anchor["printed_identifier"]
        exact_label = anchor["exact_label"]
        if not (
            isinstance(printed_identifier, str)
            and printed_identifier
            and isinstance(exact_label, str)
            and exact_label
        ):
            continue
        exact_pair_groups[
            (
                anchor["occurrence_kind"],
                printed_identifier,
                exact_label,
            )
        ].append(anchor["source_occurrence_id"])
    for (
        occurrence_kind,
        printed_identifier,
        exact_label,
    ), members in exact_pair_groups.items():
        if len(members) < 2:
            continue
        for member in members[1:]:
            union(members[0], member)
        support_edges.append(
            (
                members,
                {
                    "alias_support_proof_id": _row_id(
                        "a12-candidate-exact-pair-alias-support:",
                        [
                            occurrence_kind,
                            printed_identifier,
                            exact_label,
                            members[1:],
                            members[:1],
                            members,
                        ],
                    ),
                    "support_origin": "exact_pair_equality_sweep",
                    "relation": ("same_printed_identifier_and_exact_label"),
                    "member_occurrence_ids": members,
                    "alias_anchor_occurrence_ids": members[1:],
                    "canonical_anchor_occurrence_ids": members[:1],
                    "source_local_evidence_id": None,
                    "semantic_alias_pair_adjudication_id": None,
                    "pairing_basis_code": (
                        "byte_identical_printed_identifier_and_exact_label"
                    ),
                    "printed_identifier": printed_identifier,
                    "exact_label": exact_label,
                    "evidence_occurrence_ids": members,
                },
            )
        )

    pair_rows_by_evidence_id: defaultdict[str, list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    for pair_row in admitted_alias_pair_rows:
        _require(
            pair_row["pair_kind"] == "atomic_occurrence_pair"
            and pair_row["class_closure_eligible"] is True
            and pair_row["typed_projection_union_prohibited"] is False,
            "non-atomic or typed composite projection entered occurrence "
            "closure",
        )
        pair_rows_by_evidence_id[pair_row["source_local_evidence_id"]].append(
            pair_row
        )

    consumed_pair_ids: list[str] = []
    for document in documents:
        for evidence in document.evidence_rows:
            # Semantic arm selection and pair decomposition are already
            # complete. T, G, R, STOP, and typed composite projections never
            # reach occurrence-level union-find.
            evidence_pair_rows = pair_rows_by_evidence_id.get(
                evidence["local_evidence_id"], []
            )
            if not evidence_pair_rows:
                continue
            if not _compatible_direct_proof(evidence):
                raise BuildError(
                    "construction admitted structurally incomplete alias "
                    f"evidence: {evidence['local_evidence_id']}"
                )
            for pair_row in evidence_pair_rows:
                alias_id = pair_row["alias_occurrence_id"]
                canonical_id = pair_row["canonical_occurrence_id"]
                directional_endpoints = [alias_id, canonical_id]
                _require(
                    alias_id in evidence["alias_anchor_occurrence_ids"]
                    and canonical_id
                    in evidence["canonical_anchor_occurrence_ids"],
                    "adjudicated pair is absent from its source evidence",
                )
                if not all(
                    value in anchor_by_id for value in directional_endpoints
                ):
                    continue
                endpoints = sorted(
                    directional_endpoints,
                    key=lambda value: source_order[value],
                )
                endpoint_kinds = {
                    anchor_by_id[value]["occurrence_kind"]
                    for value in endpoints
                }
                if len(endpoint_kinds) != 1:
                    continue
                printed_identifier: str | None = None
                exact_label: str | None = None
                if (
                    evidence["relation"]
                    == "same_printed_identifier_and_exact_label"
                ):
                    printed_values = {
                        anchor_by_id[value]["printed_identifier"]
                        for value in endpoints
                    }
                    label_values = {
                        anchor_by_id[value]["exact_label"]
                        for value in endpoints
                    }
                    if (
                        len(printed_values) != 1
                        or len(label_values) != 1
                        or not all(
                            isinstance(value, str) and value
                            for value in [*printed_values, *label_values]
                        )
                    ):
                        continue
                    printed_identifier = next(iter(printed_values))
                    exact_label = next(iter(label_values))
                union(alias_id, canonical_id)
                consumed_pair_ids.append(
                    pair_row["semantic_alias_pair_adjudication_id"]
                )
                support_edges.append(
                    (
                        endpoints,
                        {
                            "alias_support_proof_id": _row_id(
                                "a12-candidate-local-alias-support:",
                                [
                                    pair_row[
                                        "semantic_alias_pair_adjudication_id"
                                    ],
                                    evidence["relation"],
                                    alias_id,
                                    canonical_id,
                                    evidence["evidence_occurrence_ids"],
                                ],
                            ),
                            "support_origin": "sealed_local_evidence",
                            "relation": evidence["relation"],
                            "member_occurrence_ids": endpoints,
                            "alias_anchor_occurrence_ids": [alias_id],
                            "canonical_anchor_occurrence_ids": [canonical_id],
                            "source_local_evidence_id": evidence[
                                "local_evidence_id"
                            ],
                            "semantic_alias_pair_adjudication_id": pair_row[
                                "semantic_alias_pair_adjudication_id"
                            ],
                            "pairing_basis_code": pair_row[
                                "pairing_basis_code"
                            ],
                            "printed_identifier": printed_identifier,
                            "exact_label": exact_label,
                            "evidence_occurrence_ids": evidence[
                                "evidence_occurrence_ids"
                            ],
                        },
                    )
                )

    _require(
        set(consumed_pair_ids)
        <= {
            row["semantic_alias_pair_adjudication_id"]
            for row in admitted_alias_pair_rows
        },
        "unknown semantic pair consumed by occurrence closure",
    )

    members_by_root: defaultdict[str, list[str]] = defaultdict(list)
    for anchor in ordered_anchor_rows:
        occurrence_id = anchor["source_occurrence_id"]
        members_by_root[find(occurrence_id)].append(occurrence_id)

    support_by_root: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for endpoints, support in support_edges:
        root = find(endpoints[0])
        if support not in support_by_root[root]:
            support_by_root[root].append(support)

    rows: list[dict[str, Any]] = []
    observed_roots: set[str] = set()
    for anchor in ordered_anchor_rows:
        root = find(anchor["source_occurrence_id"])
        if root in observed_roots:
            continue
        observed_roots.add(root)
        members = members_by_root[root]
        supports = support_by_root[root]
        rows.append(
            {
                "canonical_occurrence_id": members[0],
                "member_occurrence_ids": members,
                "alias_support_rows": supports,
                "alias_support_count": len(supports),
                "alias_support_domain_sha256": _domain_sha(supports),
            }
        )
    return rows


def _derived_class_complement_sweep_rows(
    documents: Sequence[NormalizedDocument],
    component_shapes: Sequence[Mapping[str, Any]],
    admitted_alias_pair_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run full-corpus candidate class and job-complement sweeps."""
    job_classes = _candidate_alias_classes(
        documents,
        frozenset({"job_anchor"}),
        admitted_alias_pair_rows,
    )
    candidate_job_id_by_occurrence: dict[str, str] = {}
    candidate_job_rows: list[dict[str, Any]] = []
    for value in job_classes:
        candidate_job_class_id = _row_id(
            "a12-candidate-job-class:",
            [
                value["canonical_occurrence_id"],
                value["member_occurrence_ids"],
            ],
        )
        candidate_job_rows.append(
            {**value, "candidate_job_class_id": candidate_job_class_id}
        )
        for occurrence_id in value["member_occurrence_ids"]:
            candidate_job_id_by_occurrence[occurrence_id] = (
                candidate_job_class_id
            )

    shape_by_occurrence = {
        row["component_anchor_occurrence_id"]: row for row in component_shapes
    }
    component_classes = _candidate_alias_classes(
        documents,
        frozenset({"context_anchor", "remuneration_component_anchor"}),
        admitted_alias_pair_rows,
    )
    component_class_rows: list[dict[str, Any]] = []
    for value in component_classes:
        members = value["member_occurrence_ids"]
        member_shapes = [shape_by_occurrence[member] for member in members]
        component_kinds = {row["component_kind"] for row in member_shapes}
        _require(
            len(component_kinds) == 1,
            "candidate component class crosses component kinds",
        )
        fixture_members: list[dict[str, Any]] = []
        for shape in member_shapes:
            fixture_candidates: list[dict[str, Any]] = []
            for candidate in shape["parent_candidate_rows"]:
                resolved_parent = None
                if candidate["eligible_parent"]:
                    parent_kind = candidate["parent_occurrence_kind"]
                    if parent_kind == "job_anchor":
                        resolved_parent = candidate_job_id_by_occurrence[
                            candidate["parent_occurrence_id"]
                        ]
                    else:
                        resolved_parent = CANDIDATE_SENTINEL_PARENT_NODE_IDS[
                            parent_kind
                        ]
                fixture_candidates.append(
                    {
                        "source_parent_occurrence_id": candidate[
                            "parent_occurrence_id"
                        ],
                        "resolved_canonical_parent_node_id": resolved_parent,
                        "eligible_parent": candidate["eligible_parent"],
                        "derived_slot_kind": candidate["derived_slot_kind"],
                        "support_proof_id": _row_id(
                            "a12-candidate-parent-support:",
                            [
                                shape["component_anchor_occurrence_id"],
                                candidate["parent_occurrence_id"],
                            ],
                        ),
                    }
                )
            fixture_members.append(
                {
                    "component_anchor_occurrence_id": shape[
                        "component_anchor_occurrence_id"
                    ],
                    "parent_candidate_rows": fixture_candidates,
                }
            )
        folded = fold_component_class_fixture(
            next(iter(component_kinds)), fixture_members
        )
        candidate_component_class_id = _row_id(
            "a12-candidate-component-class:",
            [value["canonical_occurrence_id"], members],
        )
        sweep_id = _row_id(
            "a12-component-class-admission-sweep:",
            [candidate_component_class_id, folded["disposition"]],
        )
        component_class_rows.append(
            {
                "component_class_admission_sweep_id": sweep_id,
                "candidate_component_class_id": candidate_component_class_id,
                "canonical_component_occurrence_id": value[
                    "canonical_occurrence_id"
                ],
                "component_class_member_occurrence_ids": members,
                "component_class_member_count": len(members),
                "component_kind": next(iter(component_kinds)),
                "member_raw_parent_cardinalities": folded[
                    "member_raw_parent_cardinalities"
                ],
                "raw_parent_candidate_count": folded[
                    "raw_parent_candidate_count"
                ],
                "eligible_canonical_parent_count": len(
                    folded["resolved_canonical_parent_node_ids"]
                ),
                "candidate_disposition": folded["disposition"],
                "candidate_unique_parent_node_id": folded[
                    "unique_parent_node_id"
                ],
                "candidate_unique_slot_kind": folded["unique_slot_kind"],
                "relationship_arm_eligible": folded[
                    "tier_2_relationship_arm_eligible"
                ],
                "r_q_relationship_emitted": False,
                "alias_support_rows": value["alias_support_rows"],
                "alias_support_count": value["alias_support_count"],
                "alias_support_domain_sha256": value[
                    "alias_support_domain_sha256"
                ],
                "predecessor_reseal_required": True,
                "status": (
                    "candidate_class_fold_nonauthority_"
                    "predecessor_reseal_required"
                ),
            }
        )

    candidate_job_class_ids = {
        row["candidate_job_class_id"] for row in candidate_job_rows
    }
    relationship_components_by_job: defaultdict[str, list[str]] = defaultdict(
        list
    )
    for row in component_class_rows:
        if not row["relationship_arm_eligible"]:
            continue
        parent_id = row["candidate_unique_parent_node_id"]
        if parent_id not in candidate_job_class_ids:
            continue
        relationship_components_by_job[parent_id].append(
            row["candidate_component_class_id"]
        )

    job_complement_rows: list[dict[str, Any]] = []
    for value in candidate_job_rows:
        candidate_job_class_id = value["candidate_job_class_id"]
        component_class_ids = relationship_components_by_job[
            candidate_job_class_id
        ]
        folded = fold_catalog_only_job_complement_fixture(
            candidate_job_class_id, component_class_ids
        )
        sweep_id = _row_id(
            "a12-catalog-only-job-complement-sweep:",
            [candidate_job_class_id, component_class_ids],
        )
        job_complement_rows.append(
            {
                "catalog_only_job_complement_sweep_id": sweep_id,
                "candidate_job_class_id": candidate_job_class_id,
                "canonical_job_occurrence_id": value[
                    "canonical_occurrence_id"
                ],
                "job_class_member_occurrence_ids": value[
                    "member_occurrence_ids"
                ],
                "job_class_member_count": len(value["member_occurrence_ids"]),
                "candidate_relationship_component_class_ids": (
                    component_class_ids
                ),
                "candidate_relationship_count": folded[
                    "candidate_relationship_count"
                ],
                "catalog_only_disposition_required": folded[
                    "catalog_only_disposition_required"
                ],
                "coverage_arm": folded["coverage_arm"],
                "catalog_only_disposition_emitted": False,
                "alias_support_rows": value["alias_support_rows"],
                "alias_support_count": value["alias_support_count"],
                "alias_support_domain_sha256": value[
                    "alias_support_domain_sha256"
                ],
                "predecessor_reseal_required": True,
                "status": (
                    "candidate_job_complement_nonauthority_"
                    "predecessor_reseal_required"
                ),
            }
        )
    return component_class_rows, job_complement_rows


def _role_classes(
    documents: Sequence[NormalizedDocument],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}
    observed_first: list[str] = []
    for document in documents:
        for anchor in _role_anchor_rows(document):
            label = anchor["exact_label"]
            _require(isinstance(label, str) and label, "empty role label")
            label_sha = _sha256(label.encode("utf-8"))
            _require(
                label == anchor["occurrence_matched_text"],
                "role exact label differs from occurrence bytes",
            )
            _require(
                label_sha == anchor["occurrence_matched_utf8_sha256"],
                "role exact label digest differs from occurrence digest",
            )
            stored_sha = anchor["exact_label_sha256"]
            _require(
                stored_sha is None or stored_sha == label_sha,
                "stored role label digest drift",
            )
            role = anchor["classification"]
            _require(role in ROLE_ORDER, "unknown role classification")
            if label not in grouped:
                grouped[label] = {
                    "roles": set(),
                    "members": [],
                    "label_sha": label_sha,
                }
                observed_first.append(label)
            grouped[label]["roles"].add(role)
            grouped[label]["members"].append(anchor["source_occurrence_id"])
    class_rows: list[dict[str, Any]] = []
    by_label: dict[str, dict[str, Any]] = {}
    for label in observed_first:
        value = grouped[label]
        _require(
            len(value["roles"]) == 1,
            f"role exact-label class crosses roles: {label!r}",
        )
        role = next(iter(value["roles"]))
        members = value["members"]
        class_id = _row_id(
            "a12-role-exact-label-class:",
            [role, value["label_sha"]],
        )
        row = {
            "role_label_class_id": class_id,
            "role": role,
            "exact_label": label,
            "exact_label_sha256": value["label_sha"],
            "member_occurrence_ids": members,
            "member_count": len(members),
            "member_keyset_sha256": _keyset_sha(members),
            "occurrence_equivalence_claimed": False,
            "alias_class_claimed": False,
            "status": "role_membership_class_only",
        }
        class_rows.append(row)
        by_label[label] = row
    return class_rows, by_label


def _role_assignment_rows(
    documents: Sequence[NormalizedDocument],
    classes_by_label: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    canonical_ids = set(ROLE_CANONICALS.values())
    for document in documents:
        for anchor in _role_anchor_rows(document):
            occurrence_id = anchor["source_occurrence_id"]
            if occurrence_id in canonical_ids:
                continue
            label = anchor["exact_label"]
            role = anchor["classification"]
            class_row = classes_by_label[label]
            _require(class_row["role"] == role, "role class mismatch")
            assignment_id = _row_id(
                "a12-pilot-role-assignment:",
                [
                    document.source_document_id,
                    occurrence_id,
                    role,
                    class_row["role_label_class_id"],
                    "exact_label_class_role_assignment_non_alias",
                ],
            )
            rows.append(
                {
                    "role_assignment_id": assignment_id,
                    "document_source_position": document.position,
                    "source_document_id": document.source_document_id,
                    "source_classification_id": anchor[
                        "local_anchor_classification_id"
                    ],
                    "role_anchor_occurrence_id": occurrence_id,
                    "assigned_role": role,
                    "printed_identifier": anchor["printed_identifier"],
                    "exact_label": label,
                    "exact_label_sha256": class_row["exact_label_sha256"],
                    "role_label_class_id": class_row["role_label_class_id"],
                    "proof_form": (
                        "exact_label_class_role_assignment_non_alias"
                    ),
                    "alias_admitted_by_assignment": False,
                    "occurrence_equivalence_claimed": False,
                    "status": "assigned_noncanonical_role_anchor",
                }
            )
    return rows


def _outside_repeat_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    all_instruction_to_evidence: defaultdict[str, list[str]] = defaultdict(
        list
    )
    all_endpoint_ids: set[str] = set()
    candidates: list[tuple[NormalizedDocument, dict[str, Any]]] = []
    for document in documents:
        for evidence in document.evidence_rows:
            for instruction_id in evidence[
                "source_instruction_occurrence_ids"
            ]:
                all_instruction_to_evidence[instruction_id].append(
                    evidence["local_evidence_id"]
                )
            all_endpoint_ids.update(evidence["alias_anchor_occurrence_ids"])
            all_endpoint_ids.update(
                evidence["canonical_anchor_occurrence_ids"]
            )
            if (
                evidence["handoff_status"]
                == "local_target_outside_rq_annotation_domain"
            ):
                candidates.append((document, evidence))
    rows: list[dict[str, Any]] = []
    for document, evidence in candidates:
        instructions = evidence["source_instruction_occurrence_ids"]
        _require(len(instructions) == 1, "outside repeat is not singleton")
        instruction_id = instructions[0]
        _require(
            not evidence["alias_anchor_occurrence_ids"]
            and not evidence["canonical_anchor_occurrence_ids"],
            "outside repeat has an alias endpoint",
        )
        _require(
            evidence["evidence_occurrence_ids"] == [instruction_id],
            "outside repeat evidence is not singleton self-evidence",
        )
        unresolved = evidence["unresolved_target_reference"]
        _require(isinstance(unresolved, dict) and unresolved, "empty target")
        _require(
            len(all_instruction_to_evidence[instruction_id]) == 1,
            "outside repeat occurs in another local evidence row",
        )
        _require(
            instruction_id not in all_endpoint_ids,
            "outside repeat occurs as an alias endpoint",
        )
        disposition_id = _row_id(
            "a12-outside-rq-repeat-disposition:",
            [
                document.source_document_id,
                instruction_id,
                evidence["local_evidence_id"],
                evidence["relation"],
                unresolved,
            ],
        )
        rows.append(
            {
                "outside_domain_repeat_disposition_id": disposition_id,
                "document_source_position": document.position,
                "source_document_id": document.source_document_id,
                "source_local_evidence_id": evidence["local_evidence_id"],
                "source_instruction_occurrence_id": instruction_id,
                "relation": evidence["relation"],
                "handoff_status": evidence["handoff_status"],
                "evidence_occurrence_ids": [instruction_id],
                "unresolved_target_reference": unresolved,
                "terminal_disposition": (
                    "outside_r_q_domain_no_alias_admitted"
                ),
                "alias_anchor_occurrence_id": None,
                "referenced_anchor_occurrence_id": None,
                "alias_admitted": False,
                "occurrence_equivalence_claimed": False,
                "universal_repeat_coverage_arm_satisfied": True,
                "status": "terminal_nonauthority_disposition",
            }
        )
    return rows


def _honest_noncatalog_aggregate_relation(
    evidence: Mapping[str, Any],
) -> bool:
    """Return the exact mechanical predicate for the third repeat arm."""
    aliases = evidence["alias_anchor_occurrence_ids"]
    canonicals = evidence["canonical_anchor_occurrence_ids"]
    instructions = evidence["source_instruction_occurrence_ids"]
    instruction_kinds = evidence["source_instruction_occurrence_kinds"]
    evidence_ids = evidence["evidence_occurrence_ids"]
    endpoint_ids = [*aliases, *canonicals]
    endpoint_kinds = evidence["endpoint_occurrence_kinds"]
    endpoint_domains = evidence["endpoint_raw_node_domains"]
    endpoint_classifications = evidence["endpoint_classifications"]
    instruction_texts = evidence["source_instruction_matched_texts"]
    instruction_digests = evidence["source_instruction_matched_utf8_sha256s"]
    instruction_pages = evidence["source_instruction_page_numbers"]
    instruction_starts = evidence["source_instruction_utf8_byte_starts"]
    instruction_ends = evidence["source_instruction_utf8_byte_ends"]
    endpoint_texts = evidence["endpoint_matched_texts"]
    endpoint_digests = evidence["endpoint_matched_utf8_sha256s"]
    endpoint_pages = evidence["endpoint_page_numbers"]
    endpoint_starts = evidence["endpoint_utf8_byte_starts"]
    endpoint_ends = evidence["endpoint_utf8_byte_ends"]
    aggregate_only_flags = {
        "touches_noncatalog_aggregate_endpoint": True,
        "occurrence_derived_domain_crossing": False,
        "corrected_catalog_domain_crossing": False,
        "raw_node_domain_crossing": False,
        "context_remuneration_mix": False,
        "head_spouse_mix": False,
    }
    return bool(
        aliases
        and canonicals
        and len(instructions) == 1
        and instruction_kinds == ["repeat_or_alias_instruction"]
        and len(endpoint_ids) == len(set(endpoint_ids))
        and not set(aliases) & set(canonicals)
        and not set(instructions) & set(endpoint_ids)
        and evidence_ids
        and len(evidence_ids) == len(set(evidence_ids))
        and len(evidence_ids) == len(endpoint_ids) + len(instructions)
        and set(evidence_ids) == {*endpoint_ids, *instructions}
        and evidence["evidence_arrays_unique_disjoint"]
        and evidence["evidence_arrays_source_ordered"]
        and evidence["relation"] in ALLOWED_REPEAT_RELATIONS
        and evidence["handoff_status"] in COMPLETE_LOCAL_EVIDENCE_STATUSES
        and evidence["unresolved_target_reference"] is None
        and endpoint_kinds
        and len(endpoint_kinds)
        == len(endpoint_domains)
        == len(endpoint_classifications)
        == len(endpoint_texts)
        == len(endpoint_digests)
        == len(endpoint_pages)
        == len(endpoint_starts)
        == len(endpoint_ends)
        == len(endpoint_ids)
        and all(kind in AGGREGATE_OCCURRENCE_KINDS for kind in endpoint_kinds)
        and all(domain == "aggregate" for domain in endpoint_domains)
        and all(
            classification in AGGREGATE_KIND_TO_CLASSIFICATIONS[kind]
            for kind, classification in zip(
                endpoint_kinds, endpoint_classifications, strict=True
            )
        )
        and len(instruction_texts)
        == len(instruction_digests)
        == len(instruction_pages)
        == len(instruction_starts)
        == len(instruction_ends)
        == 1
        and all(
            digest == _sha256(text.encode("utf-8"))
            for text, digest in zip(
                instruction_texts, instruction_digests, strict=True
            )
        )
        and all(
            page > 0
            and 0 <= start < end
            and end - start == len(text.encode("utf-8"))
            for text, page, start, end in zip(
                instruction_texts,
                instruction_pages,
                instruction_starts,
                instruction_ends,
                strict=True,
            )
        )
        and all(
            digest == _sha256(text.encode("utf-8"))
            for text, digest in zip(
                endpoint_texts, endpoint_digests, strict=True
            )
        )
        and all(
            page > 0
            and 0 <= start < end
            and end - start == len(text.encode("utf-8"))
            for text, page, start, end in zip(
                endpoint_texts,
                endpoint_pages,
                endpoint_starts,
                endpoint_ends,
                strict=True,
            )
        )
        and evidence["defect_flags"] == aggregate_only_flags
    )


def _exact_byte_projection(
    texts: Any,
    digests: Any,
    pages: Any,
    starts: Any,
    ends: Any,
    expected_count: int,
) -> bool:
    arrays = (texts, digests, pages, starts, ends)
    if not all(
        isinstance(values, list) and len(values) == expected_count
        for values in arrays
    ):
        return False
    return all(
        isinstance(text, str)
        and isinstance(digest, str)
        and digest == _sha256(text.encode("utf-8"))
        and isinstance(page, int)
        and not isinstance(page, bool)
        and page > 0
        and isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and 0 <= start < end
        and end - start == len(text.encode("utf-8"))
        for text, digest, page, start, end in zip(*arrays, strict=True)
    )


def _complete_redirection_evidence_member(
    evidence: Mapping[str, Any], instruction_id: str
) -> bool:
    aliases = evidence["alias_anchor_occurrence_ids"]
    canonicals = evidence["canonical_anchor_occurrence_ids"]
    endpoints = [*aliases, *canonicals]
    evidence_ids = evidence["evidence_occurrence_ids"]
    endpoint_kinds = evidence["endpoint_occurrence_kinds"]
    endpoint_classifications = evidence["endpoint_classifications"]
    endpoint_arrays = (
        endpoint_kinds,
        evidence["endpoint_raw_node_domains"],
        endpoint_classifications,
        evidence["endpoint_printed_identifiers"],
        evidence["endpoint_matched_texts"],
        evidence["endpoint_matched_utf8_sha256s"],
        evidence["endpoint_page_numbers"],
        evidence["endpoint_utf8_byte_starts"],
        evidence["endpoint_utf8_byte_ends"],
    )
    allowed_projection = {
        ("context_anchor", "source_context"),
        ("remuneration_component_anchor", "source_remuneration_component"),
    }
    context_mix = {kind for kind in endpoint_kinds} == {
        "context_anchor",
        "remuneration_component_anchor",
    }
    return bool(
        len(aliases) == len(canonicals) == 1
        and len(endpoints) == len(set(endpoints)) == 2
        and not set(aliases) & set(canonicals)
        and instruction_id not in set(endpoints)
        and evidence["source_instruction_occurrence_ids"] == [instruction_id]
        and evidence["source_instruction_occurrence_kinds"]
        == ["repeat_or_alias_instruction"]
        and len(evidence_ids) == len(set(evidence_ids)) == 3
        and set(evidence_ids) == {*endpoints, instruction_id}
        and evidence["evidence_arrays_unique_disjoint"]
        and evidence["evidence_arrays_source_ordered"]
        and evidence["relation"] == "explicit_cross_reference"
        and evidence["handoff_status"] in COMPLETE_LOCAL_EVIDENCE_STATUSES
        and evidence["unresolved_target_reference"] is None
        and all(
            isinstance(values, list) and len(values) == len(endpoints)
            for values in endpoint_arrays
        )
        and evidence["endpoint_raw_node_domains"]
        == ["component_slot", "component_slot"]
        and all(
            (kind, classification) in allowed_projection
            for kind, classification in zip(
                endpoint_kinds, endpoint_classifications, strict=True
            )
        )
        and _exact_byte_projection(
            evidence["source_instruction_matched_texts"],
            evidence["source_instruction_matched_utf8_sha256s"],
            evidence["source_instruction_page_numbers"],
            evidence["source_instruction_utf8_byte_starts"],
            evidence["source_instruction_utf8_byte_ends"],
            1,
        )
        and _exact_byte_projection(
            evidence["endpoint_matched_texts"],
            evidence["endpoint_matched_utf8_sha256s"],
            evidence["endpoint_page_numbers"],
            evidence["endpoint_utf8_byte_starts"],
            evidence["endpoint_utf8_byte_ends"],
            len(endpoints),
        )
        and evidence["defect_flags"]
        == {
            "touches_noncatalog_aggregate_endpoint": False,
            "occurrence_derived_domain_crossing": False,
            "corrected_catalog_domain_crossing": False,
            "raw_node_domain_crossing": False,
            "context_remuneration_mix": context_mix,
            "head_spouse_mix": False,
        }
    )


def _complete_cross_reference_evidence_member(
    evidence: Mapping[str, Any],
) -> bool:
    """Return whether a cross-reference carries an exact complete proof."""
    aliases = evidence["alias_anchor_occurrence_ids"]
    canonicals = evidence["canonical_anchor_occurrence_ids"]
    instructions = evidence["source_instruction_occurrence_ids"]
    endpoints = [*aliases, *canonicals]
    evidence_ids = evidence["evidence_occurrence_ids"]
    endpoint_arrays = (
        evidence["endpoint_occurrence_kinds"],
        evidence["endpoint_raw_node_domains"],
        evidence["endpoint_classifications"],
        evidence["endpoint_printed_identifiers"],
        evidence["endpoint_matched_texts"],
        evidence["endpoint_matched_utf8_sha256s"],
        evidence["endpoint_page_numbers"],
        evidence["endpoint_utf8_byte_starts"],
        evidence["endpoint_utf8_byte_ends"],
    )
    return bool(
        aliases
        and canonicals
        and len(instructions) == 1
        and evidence["source_instruction_occurrence_kinds"]
        == ["repeat_or_alias_instruction"]
        and len(endpoints) == len(set(endpoints))
        and not set(aliases) & set(canonicals)
        and not set(instructions) & set(endpoints)
        and len(evidence_ids) == len(set(evidence_ids)) == len(endpoints) + 1
        and set(evidence_ids) == {*endpoints, *instructions}
        and evidence["evidence_arrays_unique_disjoint"]
        and evidence["evidence_arrays_source_ordered"]
        and evidence["relation"] == "explicit_cross_reference"
        and evidence["handoff_status"] in COMPLETE_LOCAL_EVIDENCE_STATUSES
        and evidence["unresolved_target_reference"] is None
        and all(
            isinstance(values, list) and len(values) == len(endpoints)
            for values in endpoint_arrays
        )
        and _exact_byte_projection(
            evidence["source_instruction_matched_texts"],
            evidence["source_instruction_matched_utf8_sha256s"],
            evidence["source_instruction_page_numbers"],
            evidence["source_instruction_utf8_byte_starts"],
            evidence["source_instruction_utf8_byte_ends"],
            1,
        )
        and _exact_byte_projection(
            evidence["endpoint_matched_texts"],
            evidence["endpoint_matched_utf8_sha256s"],
            evidence["endpoint_page_numbers"],
            evidence["endpoint_utf8_byte_starts"],
            evidence["endpoint_utf8_byte_ends"],
            len(endpoints),
        )
    )


def _in_domain_nonaggregate_cross_reference_evidence_member(
    evidence: Mapping[str, Any],
) -> bool:
    """Return whether every complete endpoint is in-domain nonaggregate."""
    if not _complete_cross_reference_evidence_member(evidence):
        return False
    allowed_classifications = {
        "role_anchor": frozenset(ROLE_ORDER),
        "job_anchor": frozenset({"source_job"}),
        "context_anchor": frozenset({"source_context"}),
        "remuneration_component_anchor": frozenset(
            {"source_remuneration_component"}
        ),
    }
    return all(
        kind in allowed_classifications
        and raw_domain == _occurrence_catalog_domain(kind)
        and classification in allowed_classifications[kind]
        for kind, raw_domain, classification in zip(
            evidence["endpoint_occurrence_kinds"],
            evidence["endpoint_raw_node_domains"],
            evidence["endpoint_classifications"],
            strict=True,
        )
    )


def _component_cross_reference_evidence_member(
    evidence: Mapping[str, Any],
) -> bool:
    """Return whether all complete endpoints are component members."""
    if not _complete_cross_reference_evidence_member(evidence):
        return False
    allowed = {
        ("context_anchor", "source_context"),
        (
            "remuneration_component_anchor",
            "source_remuneration_component",
        ),
    }
    return bool(
        evidence["endpoint_occurrence_kinds"]
        and all(
            value == "component_slot"
            for value in evidence["endpoint_raw_node_domains"]
        )
        and all(
            (kind, classification) in allowed
            for kind, classification in zip(
                evidence["endpoint_occurrence_kinds"],
                evidence["endpoint_classifications"],
                strict=True,
            )
        )
    )


def _semantic_redirection_evidence_member(
    evidence: Mapping[str, Any],
) -> bool:
    instructions = evidence["source_instruction_occurrence_ids"]
    if len(instructions) != 1:
        return False
    expected_evidence_ids = (
        EXCLUSIVE_DESTINATION_REDIRECTION_EVIDENCE_BY_INSTRUCTION.get(
            instructions[0]
        )
    )
    return bool(
        expected_evidence_ids is not None
        and evidence["local_evidence_id"] in expected_evidence_ids
        and _complete_redirection_evidence_member(evidence, instructions[0])
    )


def _redirection_disposition_id(row: Mapping[str, Any]) -> str:
    return _row_id(
        "a12-in-domain-redirection-relation-disposition:",
        [
            row["source_document_id"],
            row["source_local_evidence_ids"],
            row["relation_subkind"],
            row["source_instruction_occurrence_ids"],
            row["relation"],
            row["handoff_status"],
            row["source_evidence_occurrence_id_arrays"],
            row["predecessor_alias_anchor_occurrence_ids"],
            row["predecessor_canonical_anchor_occurrence_ids"],
            row["evidence_occurrence_ids"],
            row["endpoint_occurrence_kinds"],
            row["endpoint_raw_node_domains"],
            row["endpoint_classifications"],
            row["endpoint_printed_identifiers"],
            row["source_instruction_matched_texts"],
            row["source_instruction_matched_utf8_sha256s"],
            row["source_instruction_page_numbers"],
            row["source_instruction_utf8_byte_starts"],
            row["source_instruction_utf8_byte_ends"],
            row["endpoint_matched_texts"],
            row["endpoint_matched_utf8_sha256s"],
            row["endpoint_page_numbers"],
            row["endpoint_utf8_byte_starts"],
            row["endpoint_utf8_byte_ends"],
        ],
    )


def _in_domain_redirection_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_instruction_ids: set[str] = set()
    selected_repeat_ids = {
        instruction_id
        for document in documents
        for instruction_id in document.repeat_occurrence_ids
        if instruction_id in EXCLUSIVE_DESTINATION_REDIRECTION_INSTRUCTION_IDS
    }
    endpoint_projection_keys = (
        "endpoint_occurrence_kinds",
        "endpoint_raw_node_domains",
        "endpoint_classifications",
        "endpoint_printed_identifiers",
        "endpoint_matched_texts",
        "endpoint_matched_utf8_sha256s",
        "endpoint_page_numbers",
        "endpoint_utf8_byte_starts",
        "endpoint_utf8_byte_ends",
    )
    for document in documents:
        evidence_by_instruction: defaultdict[str, list[dict[str, Any]]] = (
            defaultdict(list)
        )
        for evidence in document.evidence_rows:
            for instruction_id in evidence[
                "source_instruction_occurrence_ids"
            ]:
                evidence_by_instruction[instruction_id].append(evidence)
        occurrence_by_id = {
            row["source_occurrence_id"]: row
            for row in document.repeat_occurrence_rows
        }
        for instruction_id in document.repeat_occurrence_ids:
            expected_evidence_ids = (
                EXCLUSIVE_DESTINATION_REDIRECTION_EVIDENCE_BY_INSTRUCTION.get(
                    instruction_id
                )
            )
            if expected_evidence_ids is None:
                continue
            evidence_rows = evidence_by_instruction[instruction_id]
            _require(
                tuple(
                    evidence["local_evidence_id"] for evidence in evidence_rows
                )
                == expected_evidence_ids,
                f"redirection semantic evidence ledger drift: {instruction_id}",
            )
            _require(
                all(
                    _complete_redirection_evidence_member(
                        evidence, instruction_id
                    )
                    for evidence in evidence_rows
                ),
                f"redirection source proof is incomplete: {instruction_id}",
            )
            source_occurrence = occurrence_by_id[instruction_id]
            instruction_projection = (
                [source_occurrence["matched_text"]],
                [source_occurrence["matched_utf8_sha256"]],
                [source_occurrence["page_number"]],
                [source_occurrence["utf8_byte_start"]],
                [source_occurrence["utf8_byte_end"]],
            )
            _require(
                all(
                    (
                        evidence["source_instruction_matched_texts"],
                        evidence["source_instruction_matched_utf8_sha256s"],
                        evidence["source_instruction_page_numbers"],
                        evidence["source_instruction_utf8_byte_starts"],
                        evidence["source_instruction_utf8_byte_ends"],
                    )
                    == instruction_projection
                    for evidence in evidence_rows
                ),
                f"redirection instruction projection drift: {instruction_id}",
            )
            aliases = list(
                dict.fromkeys(
                    endpoint_id
                    for evidence in evidence_rows
                    for endpoint_id in evidence["alias_anchor_occurrence_ids"]
                )
            )
            canonicals = list(
                dict.fromkeys(
                    endpoint_id
                    for evidence in evidence_rows
                    for endpoint_id in evidence[
                        "canonical_anchor_occurrence_ids"
                    ]
                )
            )
            _require(
                len(aliases) == 1
                and canonicals
                and len(canonicals) == len(set(canonicals))
                and not set(aliases) & set(canonicals),
                f"redirection endpoint grouping drift: {instruction_id}",
            )
            projection_by_endpoint: dict[str, tuple[Any, ...]] = {}
            for evidence in evidence_rows:
                endpoint_ids = [
                    *evidence["alias_anchor_occurrence_ids"],
                    *evidence["canonical_anchor_occurrence_ids"],
                ]
                for values in zip(
                    endpoint_ids,
                    *(evidence[key] for key in endpoint_projection_keys),
                    strict=True,
                ):
                    endpoint_id, *projection = values
                    prior = projection_by_endpoint.setdefault(
                        endpoint_id, tuple(projection)
                    )
                    _require(
                        prior == tuple(projection),
                        f"redirection endpoint projection drift: {endpoint_id}",
                    )
            endpoint_ids = [*aliases, *canonicals]
            endpoint_projections = [
                projection_by_endpoint[endpoint_id]
                for endpoint_id in endpoint_ids
            ]
            handoff_statuses = {
                evidence["handoff_status"] for evidence in evidence_rows
            }
            _require(
                len(handoff_statuses) == 1,
                f"redirection handoff grouping drift: {instruction_id}",
            )
            row: dict[str, Any] = {
                "document_source_position": document.position,
                "source_document_id": document.source_document_id,
                "source_local_evidence_ids": list(expected_evidence_ids),
                "relation_subkind": REDIRECTION_RELATION_SUBKIND,
                "relation": "explicit_cross_reference",
                "handoff_status": next(iter(handoff_statuses)),
                "source_instruction_occurrence_ids": [instruction_id],
                "source_instruction_occurrence_kinds": [
                    "repeat_or_alias_instruction"
                ],
                "source_instruction_matched_texts": instruction_projection[0],
                "source_instruction_matched_utf8_sha256s": (
                    instruction_projection[1]
                ),
                "source_instruction_page_numbers": instruction_projection[2],
                "source_instruction_utf8_byte_starts": (
                    instruction_projection[3]
                ),
                "source_instruction_utf8_byte_ends": instruction_projection[4],
                "source_evidence_occurrence_id_arrays": [
                    evidence["evidence_occurrence_ids"]
                    for evidence in evidence_rows
                ],
                "evidence_occurrence_ids": list(
                    dict.fromkeys(
                        occurrence_id
                        for evidence in evidence_rows
                        for occurrence_id in evidence[
                            "evidence_occurrence_ids"
                        ]
                    )
                ),
                "predecessor_alias_anchor_occurrence_ids": aliases,
                "predecessor_canonical_anchor_occurrence_ids": canonicals,
                "current_location_occurrence_id": aliases[0],
                "destination_occurrence_ids": canonicals,
                **{
                    key: [
                        projection[index]
                        for projection in endpoint_projections
                    ]
                    for index, key in enumerate(endpoint_projection_keys)
                },
                "redirection_instruction_semantics": (
                    "affirmative_named_destination_and_explicit_current_"
                    "location_exclusion"
                ),
                "redirection_relation_disposition": (
                    "authenticated_in_domain_exclusive_destination_"
                    "relation_no_alias"
                ),
                "alias_admitted": False,
                "occurrence_equivalence_claimed": False,
                "universal_repeat_coverage_arm_satisfied": True,
                "status": "redirection_relation_nonauthority_disposition",
            }
            row["in_domain_redirection_relation_disposition_id"] = (
                _redirection_disposition_id(row)
            )
            rows.append(row)
            seen_instruction_ids.add(instruction_id)
    _require(
        seen_instruction_ids == selected_repeat_ids,
        "redirection semantic instruction ledger is not exact-covered",
    )
    return rows


def _cross_reference_structural_census(
    documents: Sequence[NormalizedDocument],
) -> dict[str, int]:
    """Count each narrowing stage of the complete cross-reference domain."""
    cross_reference_rows: list[dict[str, Any]] = []
    all_evidence_by_instruction: defaultdict[str, list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for document in documents:
        for evidence in document.evidence_rows:
            for instruction_id in evidence[
                "source_instruction_occurrence_ids"
            ]:
                all_evidence_by_instruction[instruction_id].append(evidence)
            if evidence["relation"] == "explicit_cross_reference":
                cross_reference_rows.append(evidence)

    complete_rows = [
        row
        for row in cross_reference_rows
        if _complete_cross_reference_evidence_member(row)
    ]
    nonaggregate_rows = [
        row
        for row in cross_reference_rows
        if _in_domain_nonaggregate_cross_reference_evidence_member(row)
    ]
    component_rows = [
        row
        for row in cross_reference_rows
        if _component_cross_reference_evidence_member(row)
    ]
    binary_component_rows = [
        row
        for row in cross_reference_rows
        if _complete_redirection_evidence_member(
            row, row["source_instruction_occurrence_ids"][0]
        )
    ]

    def instruction_ids(rows: Sequence[Mapping[str, Any]]) -> set[str]:
        return {row["source_instruction_occurrence_ids"][0] for row in rows}

    wholly_nonaggregate_instruction_ids = {
        instruction_id
        for instruction_id, evidence_rows in all_evidence_by_instruction.items()
        if evidence_rows
        and all(
            _in_domain_nonaggregate_cross_reference_evidence_member(row)
            for row in evidence_rows
        )
    }
    wholly_nonaggregate_evidence_count = sum(
        len(all_evidence_by_instruction[instruction_id])
        for instruction_id in wholly_nonaggregate_instruction_ids
    )
    return {
        "explicit_cross_reference_evidence_count": len(cross_reference_rows),
        "explicit_cross_reference_instruction_count": len(
            instruction_ids(cross_reference_rows)
        ),
        "complete_cross_reference_evidence_count": len(complete_rows),
        "complete_cross_reference_instruction_count": len(
            instruction_ids(complete_rows)
        ),
        "in_domain_nonaggregate_cross_reference_evidence_count": len(
            nonaggregate_rows
        ),
        "in_domain_nonaggregate_cross_reference_instruction_count": len(
            instruction_ids(nonaggregate_rows)
        ),
        "wholly_in_domain_nonaggregate_cross_reference_evidence_count": (
            wholly_nonaggregate_evidence_count
        ),
        "wholly_in_domain_nonaggregate_cross_reference_instruction_count": (
            len(wholly_nonaggregate_instruction_ids)
        ),
        "component_cross_reference_evidence_count": len(component_rows),
        "component_cross_reference_instruction_count": len(
            instruction_ids(component_rows)
        ),
        "binary_component_cross_reference_evidence_count": len(
            binary_component_rows
        ),
        "binary_component_cross_reference_instruction_count": len(
            instruction_ids(binary_component_rows)
        ),
    }


def _fragment_ledger_fields(instruction_id: str) -> dict[str, Any]:
    if instruction_id in ROUND_THREE_FRAGMENT_RESEAL_INSTRUCTION_IDS:
        return {
            "source_instruction_fragment": True,
            "tier_2_predecessor_seal_quality_issue": True,
            "tier_2_predecessor_ledger_note": (
                "round_three_reseal_ledger_already_covers_fragment"
            ),
        }
    if instruction_id in ROUND_FOUR_NEW_FRAGMENT_RESEAL_INSTRUCTION_IDS:
        return {
            "source_instruction_fragment": True,
            "tier_2_predecessor_seal_quality_issue": True,
            "tier_2_predecessor_ledger_note": (
                "new_tier_2_reseal_required_for_incomplete_fragment"
            ),
        }
    if instruction_id in SEMANTICALLY_DECISIVE_FRAGMENT_INSTRUCTION_IDS:
        return {
            "source_instruction_fragment": True,
            "tier_2_predecessor_seal_quality_issue": False,
            "tier_2_predecessor_ledger_note": (
                "fragment_semantically_decisive_no_reseal_required"
            ),
        }
    return {
        "source_instruction_fragment": False,
        "tier_2_predecessor_seal_quality_issue": False,
        "tier_2_predecessor_ledger_note": (
            "not_a_source_instruction_fragment"
        ),
    }


def _continuation_alias_citation(
    document: NormalizedDocument,
    evidence: Mapping[str, Any],
    instruction_id: str,
) -> dict[str, Any] | None:
    """Validate and serialize one whitespace-only continuation reading."""
    expected = CONTINUATION_ALIAS_CITATIONS_BY_INSTRUCTION.get(instruction_id)
    if expected is None:
        return None
    _require(
        evidence["source_instruction_occurrence_ids"] == [instruction_id],
        "continuation citation instruction drift",
    )
    leading_id = expected["leading_occurrence_id"]
    endpoints = [
        *evidence["alias_anchor_occurrence_ids"],
        *evidence["canonical_anchor_occurrence_ids"],
    ]
    _require(
        leading_id in endpoints,
        "continuation citation lacks its leading occurrence",
    )
    leading_index = endpoints.index(leading_id)
    page_number = expected["page_number"]
    _require(
        evidence["endpoint_page_numbers"][leading_index] == page_number
        and evidence["source_instruction_page_numbers"] == [page_number]
        and document.page_text_utf8_sha256_by_number[page_number]
        == expected["page_text_utf8_sha256"],
        "continuation citation page drift",
    )
    _require(
        evidence["endpoint_utf8_byte_starts"][leading_index]
        == expected["combined_utf8_byte_start"]
        and evidence["endpoint_utf8_byte_ends"][leading_index]
        == expected["leading_utf8_byte_end"]
        and evidence["source_instruction_utf8_byte_starts"]
        == [expected["continuation_utf8_byte_start"]]
        and evidence["source_instruction_utf8_byte_ends"]
        == [expected["combined_utf8_byte_end"]],
        "continuation citation span drift",
    )
    combined = expected["combined_text"].encode("utf-8")
    combined_start = expected["combined_utf8_byte_start"]
    _require(
        len(combined) == expected["combined_utf8_byte_end"] - combined_start
        and _sha256(combined) == expected["combined_utf8_sha256"],
        "continuation citation combined bytes drift",
    )

    def relative(absolute: int) -> int:
        return absolute - combined_start

    leading = evidence["endpoint_matched_texts"][leading_index].encode("utf-8")
    continuation = evidence["source_instruction_matched_texts"][0].encode(
        "utf-8"
    )
    gap = combined[
        relative(expected["gap_utf8_byte_start"]) : relative(
            expected["gap_utf8_byte_end"]
        )
    ]
    _require(
        combined[: relative(expected["leading_utf8_byte_end"])] == leading
        and combined[relative(expected["continuation_utf8_byte_start"]) :]
        == continuation
        and gap
        and gap.decode("utf-8").isspace(),
        "continuation citation gap is not whitespace-only",
    )
    return {
        "composition_rule": CONTINUATION_COMPOSITION_RULE,
        "leading_occurrence_id": leading_id,
        "continuation_occurrence_id": instruction_id,
        "page_number": page_number,
        "page_text_utf8_sha256": expected["page_text_utf8_sha256"],
        "combined_utf8_byte_start": combined_start,
        "leading_utf8_byte_end": expected["leading_utf8_byte_end"],
        "gap_utf8_byte_start": expected["gap_utf8_byte_start"],
        "gap_utf8_byte_end": expected["gap_utf8_byte_end"],
        "gap_text": gap.decode("utf-8"),
        "gap_utf8_sha256": _sha256(gap),
        "gap_is_whitespace_only": True,
        "continuation_utf8_byte_start": expected[
            "continuation_utf8_byte_start"
        ],
        "combined_utf8_byte_end": expected["combined_utf8_byte_end"],
        "combined_text": expected["combined_text"],
        "combined_utf8_sha256": expected["combined_utf8_sha256"],
    }


def _nonledger_alias_semantic_specification() -> (
    tuple[dict[str, Any], dict[str, Any]]
):
    value, identity = _load_pinned_semantic_specification(
        NONLEDGER_ALIAS_ADJUDICATION_PATH,
        expected_byte_size=NONLEDGER_ALIAS_ADJUDICATION_BYTE_SIZE,
        expected_raw_sha256=NONLEDGER_ALIAS_ADJUDICATION_SHA256,
    )
    _require(
        value["schema_version"]
        == "amendment12-alias-semantic-adjudication-spec-v1"
        and value["status"] == "complete_exact_cover_semantic_specification",
        "nonledger semantic specification status drift",
    )
    ordered_ids = value["ordered_nonledger_candidate_evidence_ids"]
    _require(
        isinstance(ordered_ids, list)
        and len(ordered_ids) == len(set(ordered_ids)) == 108
        and value["baseline_nonledger_candidate_domain_sha256"]
        == _domain_sha(ordered_ids),
        "nonledger semantic candidate domain drift",
    )
    single_rows = value["nonledger_single_pair_decisions"]
    pairwise_rows = value["nonledger_pairwise_decisions"]
    stop_rows = value["nonledger_stop_decisions"]
    for row in single_rows:
        _require_exact_keys(
            row,
            frozenset(
                {
                    "source_local_evidence_id",
                    "alias_occurrence_id",
                    "canonical_occurrence_id",
                    "pairing_basis_code",
                }
            ),
            "nonledger single-pair decision",
        )
    for row in pairwise_rows:
        _require_exact_keys(
            row,
            frozenset({"source_local_evidence_id", "pairs"}),
            "nonledger pairwise decision",
        )
        _require(isinstance(row["pairs"], list), "nonledger pair array")
        for pair in row["pairs"]:
            _require_exact_keys(
                pair,
                frozenset(
                    {
                        "alias_occurrence_id",
                        "canonical_occurrence_id",
                        "pairing_basis_code",
                    }
                ),
                "nonledger pairwise pair",
            )
    for row in stop_rows:
        _require_exact_keys(
            row,
            frozenset({"source_local_evidence_id", "semantic_finding"}),
            "nonledger STOP decision",
        )
    decision_domains = [
        {row["source_local_evidence_id"] for row in rows}
        for rows in (single_rows, pairwise_rows, stop_rows)
    ]
    _require(
        not decision_domains[0] & decision_domains[1]
        and not decision_domains[0] & decision_domains[2]
        and not decision_domains[1] & decision_domains[2]
        and set(ordered_ids) == set().union(*decision_domains)
        and [len(value) for value in decision_domains] == [75, 19, 14],
        "nonledger decisions do not explicitly exact-cover 108 candidates",
    )
    _require(
        value["nonledger_single_pair_domain_sha256"]
        == _domain_sha(single_rows),
        "nonledger single-pair decision domain drift",
    )
    return value, identity


COMPOSITE_DECISION_KEYS = frozenset(
    {
        "disposition",
        "instruction_decision_id",
        "instruction_id",
        "pair_producing_source_evidence_ids",
        "source_evidence_ids",
        "stop_evidence_rows",
        "stop_source_evidence_ids",
        "sweep_row_index",
        "typed_projection_pairs",
        "unmatched_selector_stop_rows",
    }
)
COMPOSITE_TYPED_PAIR_KEYS = frozenset(
    {
        "alias_combined_occurrence_id",
        "alias_question_selector",
        "canonical_combined_occurrence_id",
        "canonical_question_selector",
        "exact_pairing_citation",
        "instruction_citation",
        "instruction_id",
        "pairing_basis",
        "pairing_basis_code",
        "semantic_type",
        "source_evidence_id",
        "typed_projection_pair_id",
    }
)
COMPOSITE_EXACT_PAIRING_CITATION_KEYS = frozenset(
    {
        "alias_selector_citation_rows",
        "alias_selector_members",
        "canonical_selector_citation_rows",
        "canonical_selector_members",
        "citation_rule",
        "pairing_citation_id",
        "questionnaire_document_source_position",
        "selector_citation_domain_sha256",
        "semantic_type",
    }
)
COMPOSITE_STOP_KEYS = frozenset(
    {
        "alias_combined_occurrence_id",
        "alias_question_selector",
        "canonical_combined_occurrence_id",
        "canonical_question_selector",
        "finding",
        "finding_code",
        "instruction_citation",
        "instruction_id",
        "pairing_source_status",
        "selector_source_audit",
        "source_evidence_id",
        "stop_adjudication_id",
    }
)
COMPOSITE_STOP_SELECTOR_AUDIT_KEYS = frozenset(
    {
        "alias_selector_citation_rows",
        "canonical_selector_citation_rows",
        "missing_source_rows",
        "support_status",
    }
)
COMPOSITE_UNMATCHED_SELECTOR_STOP_KEYS = frozenset(
    {
        "finding",
        "finding_code",
        "question_selector",
        "represented_by_existing_stop_source_evidence",
        "required_disposition",
        "selector_citation_rows",
        "selector_side",
        "semantic_type",
        "stop_source_evidence_ids",
        "sweep_row_index",
        "unmatched_selector_stop_id",
    }
)
COMPOSITE_INSTRUCTION_LAW_TOP_KEYS = frozenset(
    {
        "instruction_group_count",
        "instruction_law_rows",
        "schema_version",
        "source_adjudication_path",
        "stop_pair_count",
        "typed_pair_count",
        "unmatched_selector_count",
    }
)
COMPOSITE_INSTRUCTION_LAW_ROW_KEYS = frozenset(
    {
        "allowed_typed_pair_triples",
        "expected_instruction_document_source_position",
        "expected_questionnaire_document_source_position",
        "expected_stop_pair_tuples",
        "expected_unmatched_selector_tuples",
        "instruction_id",
        "ordered_alias_selector_domain",
        "ordered_canonical_selector_domain",
        "sweep_row_index",
    }
)
COMPOSITE_INSTRUCTION_LAW_SELECTOR_KEYS = frozenset({"members", "selector"})
SELECTOR_STAGE2_CITATION_KEYS = frozenset(
    {
        "authority_registry_id",
        "citation_kind",
        "document_source_position",
        "matched_text",
        "matched_utf8_sha256",
        "page_number",
        "page_text_utf8_sha256",
        "questionnaire_occurrence_id",
        "questionnaire_page_id",
        "registered_path",
        "registered_pdf_byte_size",
        "registered_pdf_sha256",
        "registry_document_id",
        "selector_member",
        "source_document_id",
        "stage2_annotation_path",
        "stage2_annotation_source_commit",
        "utf8_byte_span",
    }
)
SELECTOR_STAGE1_CITATION_KEYS = frozenset(
    {
        "authority_registry_id",
        "candidate_artifact_content_sha256",
        "candidate_artifact_path",
        "candidate_artifact_payload_sha256",
        "candidate_artifact_raw_byte_size",
        "candidate_artifact_raw_sha256",
        "candidate_detector_rule_ids",
        "candidate_occurrence_id",
        "candidate_occurrence_kind",
        "citation_kind",
        "document_source_position",
        "evidence_part",
        "matched_text",
        "matched_utf8_sha256",
        "page_number",
        "page_text_utf8_sha256",
        "questionnaire_occurrence_id",
        "questionnaire_page_id",
        "registered_path",
        "registered_pdf_byte_size",
        "registered_pdf_sha256",
        "registry_document_id",
        "selector_member",
        "source_document_id",
        "stage2_annotation_path",
        "stage2_annotation_source_commit",
        "utf8_byte_span",
    }
)


def _validate_selector_citation_shape(
    citation: Mapping[str, Any], label: str
) -> tuple[str, str]:
    """Validate the sealed shape of one exact selector-text citation."""
    kind = citation.get("citation_kind")
    if kind == "pinned_stage2_questionnaire_occurrence":
        base_keys = SELECTOR_STAGE2_CITATION_KEYS
        allowed_keysets = {
            base_keys,
            base_keys | {"ocr_note"},
            base_keys | {"evidence_part"},
            base_keys | {"evidence_part", "variant_role"},
            base_keys | {"ocr_note", "variant_role"},
        }
    elif kind == "pinned_stage1_candidate_occurrence":
        base_keys = SELECTOR_STAGE1_CITATION_KEYS - {"evidence_part"}
        allowed_keysets = {
            base_keys,
            base_keys | {"evidence_part"},
            base_keys | {"ocr_note"},
            base_keys | {"evidence_part", "ocr_note"},
        }
    else:
        raise BuildError(f"{label}: unsupported selector citation kind")
    _require(
        frozenset(citation) in allowed_keysets,
        f"{label}: selector citation keyset",
    )
    if "ocr_note" in citation:
        _require_string(citation["ocr_note"], f"{label}: OCR note")
    if "evidence_part" in citation:
        _require_string(citation["evidence_part"], f"{label}: evidence part")
    if "variant_role" in citation:
        _require(
            citation["variant_role"] in {"head", "wife_or_wife"},
            f"{label}: variant role",
        )
    text = _require_string(citation["matched_text"], f"{label}: text")
    start = _require_int(
        citation["utf8_byte_span"]["start"], f"{label}: start"
    )
    end = _require_int(citation["utf8_byte_span"]["end"], f"{label}: end")
    _require(
        set(citation["utf8_byte_span"]) == {"start", "end"}
        and start >= 0
        and end > start
        and end - start == len(text.encode("utf-8"))
        and citation["matched_utf8_sha256"] == _sha256(text.encode("utf-8"))
        and citation["stage2_annotation_source_commit"] == SOURCE_COMMIT
        and (citation["questionnaire_occurrence_id"] is None)
        is (kind == "pinned_stage1_candidate_occurrence"),
        f"{label}: selector citation exact-byte shape",
    )
    selector_member = _require_string(
        citation["selector_member"], f"{label}: selector member"
    )
    source_id = _require_string(
        citation.get("questionnaire_occurrence_id")
        or citation.get("candidate_occurrence_id"),
        f"{label}: cited occurrence",
    )
    return selector_member, f"{kind}:{source_id}"


@cache
def _composite_instruction_law_specification() -> (
    tuple[dict[str, Any], dict[str, Any]]
):
    """Load the independent closed selector law for composite imports."""
    value, identity = _load_pinned_semantic_specification(
        COMPOSITE_INSTRUCTION_LAW_PATH,
        expected_byte_size=COMPOSITE_INSTRUCTION_LAW_BYTE_SIZE,
        expected_raw_sha256=COMPOSITE_INSTRUCTION_LAW_SHA256,
    )
    _require_exact_keys(
        value,
        COMPOSITE_INSTRUCTION_LAW_TOP_KEYS,
        "composite instruction selector law",
    )
    _require(
        value["schema_version"]
        == "amendment12-composite-instruction-law-map.audit-v1"
        and value["source_adjudication_path"]
        == COMPOSITE_ALIAS_ADJUDICATION_PATH.relative_to(ROOT).as_posix()
        and value["instruction_group_count"] == 21
        and value["typed_pair_count"] == 30
        and value["stop_pair_count"] == 22
        and value["unmatched_selector_count"] == 9,
        "composite instruction selector law census drift",
    )
    rows = value["instruction_law_rows"]
    _require(
        isinstance(rows, list) and len(rows) == 21,
        "composite instruction selector law row count",
    )
    for row in rows:
        _require_exact_keys(
            row,
            COMPOSITE_INSTRUCTION_LAW_ROW_KEYS,
            "composite instruction selector law row",
        )
        index = _require_int(
            row["sweep_row_index"], "composite instruction law index"
        )
        _require(
            (
                row["instruction_id"],
                row["expected_instruction_document_source_position"],
                row["expected_questionnaire_document_source_position"],
            )
            == COMPOSITE_INSTRUCTION_SOURCE_POSITION_LAW.get(index),
            "composite instruction source-position law drift",
        )
        for side in ("alias", "canonical"):
            selector_rows = row[f"ordered_{side}_selector_domain"]
            _require(
                isinstance(selector_rows, list) and selector_rows,
                f"composite {side} selector law domain",
            )
            selectors: list[str] = []
            members: list[str] = []
            for selector_row in selector_rows:
                _require_exact_keys(
                    selector_row,
                    COMPOSITE_INSTRUCTION_LAW_SELECTOR_KEYS,
                    f"composite {side} selector law row",
                )
                selectors.append(
                    _require_string(
                        selector_row["selector"],
                        f"composite {side} selector",
                    )
                )
                selector_members = selector_row["members"]
                _require(
                    isinstance(selector_members, list)
                    and selector_members
                    and all(
                        isinstance(member, str) and member
                        for member in selector_members
                    )
                    and len(selector_members) == len(set(selector_members)),
                    f"composite {side} selector member law",
                )
                members.extend(selector_members)
            _require(
                len(selectors) == len(set(selectors))
                and len(members) == len(set(members)),
                f"composite {side} selector law overlap",
            )
        _require(
            all(
                isinstance(triple, list)
                and len(triple) == 3
                and all(isinstance(item, str) and item for item in triple)
                for triple in row["allowed_typed_pair_triples"]
            )
            and all(
                isinstance(stop, list)
                and len(stop) == 4
                and all(isinstance(item, str) and item for item in stop)
                for stop in row["expected_stop_pair_tuples"]
            )
            and all(
                isinstance(stop, list)
                and len(stop) == 4
                and stop[0] in {"alias", "canonical"}
                and isinstance(stop[1], str)
                and isinstance(stop[2], str)
                and isinstance(stop[3], bool)
                for stop in row["expected_unmatched_selector_tuples"]
            ),
            "composite instruction selector law tuple shape",
        )
    _require(
        [row["sweep_row_index"] for row in rows]
        == list(COMPOSITE_INSTRUCTION_SOURCE_POSITION_LAW)
        and sum(len(row["allowed_typed_pair_triples"]) for row in rows)
        == value["typed_pair_count"]
        and sum(len(row["expected_stop_pair_tuples"]) for row in rows)
        == value["stop_pair_count"]
        and sum(len(row["expected_unmatched_selector_tuples"]) for row in rows)
        == value["unmatched_selector_count"],
        "composite instruction selector law exact-cover drift",
    )
    return value, identity


def _composite_instruction_selector_projection(
    decision: Mapping[str, Any],
) -> list[Any]:
    """Project every selector-relevance fact bound by the closed law."""
    return [
        decision["sweep_row_index"],
        decision["instruction_id"],
        [
            [
                pair["source_evidence_id"],
                pair["alias_combined_occurrence_id"],
                pair["canonical_combined_occurrence_id"],
                pair["alias_question_selector"],
                pair["canonical_question_selector"],
                pair["semantic_type"],
                pair["pairing_basis_code"],
                pair["exact_pairing_citation"],
            ]
            for pair in decision["typed_projection_pairs"]
        ],
        [
            [
                stop["source_evidence_id"],
                stop["alias_combined_occurrence_id"],
                stop["canonical_combined_occurrence_id"],
                stop["alias_question_selector"],
                stop["canonical_question_selector"],
                stop["finding_code"],
                stop["pairing_source_status"],
                stop["selector_source_audit"],
            ]
            for stop in decision["stop_evidence_rows"]
        ],
        [
            [
                stop["selector_side"],
                stop["question_selector"],
                stop["semantic_type"],
                stop["finding_code"],
                stop["represented_by_existing_stop_source_evidence"],
                stop["stop_source_evidence_ids"],
                stop["selector_citation_rows"],
            ]
            for stop in decision["unmatched_selector_stop_rows"]
        ],
    ]


def _validate_composite_instruction_selector_commitment(
    decision: Mapping[str, Any],
) -> None:
    """Reject any coherent rewrite of an instruction's selector law."""
    index = decision["sweep_row_index"]
    _require(
        index in COMPOSITE_INSTRUCTION_SELECTOR_LAW_SHA256
        and _domain_sha(_composite_instruction_selector_projection(decision))
        == COMPOSITE_INSTRUCTION_SELECTOR_LAW_SHA256[index],
        "composite instruction selector relevance/exact-cover law drift",
    )


def _make_composite_selector_coverer(
    selector_law_by_side: Mapping[str, Mapping[str, Sequence[str]]],
    selector_coverage_by_side: dict[str, dict[str, list[str]]],
) -> Callable[[str, str, Sequence[str], str], None]:
    """Bind one instruction's selector law and exact-cover accumulator."""

    def cover_selector(
        side: str, selector: str, members: Sequence[str], label: str
    ) -> None:
        expected_members = selector_law_by_side[side].get(selector)
        _require(
            expected_members is not None and list(members) == expected_members,
            f"{label}: selector/member law drift",
        )
        prior = selector_coverage_by_side[side].setdefault(
            selector, list(members)
        )
        _require(
            prior == list(members),
            f"{label}: conflicting selector coverage",
        )

    return cover_selector


def _composite_import_semantic_specification() -> (
    tuple[dict[str, Any], dict[str, Any]]
):
    value, identity = _load_pinned_semantic_specification(
        COMPOSITE_ALIAS_ADJUDICATION_PATH,
        expected_byte_size=COMPOSITE_ALIAS_ADJUDICATION_BYTE_SIZE,
        expected_raw_sha256=COMPOSITE_ALIAS_ADJUDICATION_SHA256,
    )
    _require(
        value["schema_version"]
        == "amendment12-composite-import-adjudication-v1"
        and value["status"] == "complete_exact_cover"
        and value["authority_kind"]
        == "nonauthority_semantic_adjudication_input",
        "composite semantic specification status drift",
    )
    expected_census = {
        "decomposed_instruction_group_count": 14,
        "decomposed_instruction_group_with_partial_stop_count": 7,
        "exact_pairing_selector_citation_row_count": 114,
        "full_stop_instruction_group_count": 7,
        "instruction_group_count": 21,
        "missing_pair_stop_available_selector_citation_row_count": 23,
        "pair_producing_evidence_with_multiple_pairs_count": 1,
        "pair_producing_source_evidence_count": 29,
        "pure_decomposed_instruction_group_count": 7,
        "selector_source_annotation_count": 3,
        "source_evidence_count": 51,
        "stop_source_evidence_count": 22,
        "typed_projection_pair_count": 30,
        "unmatched_selector_citation_row_count": 9,
        "unmatched_selector_stop_count": 9,
        "unmatched_selector_with_stop_evidence_count": 5,
        "unmatched_selector_without_candidate_evidence_count": 4,
    }
    _require(
        value["census"] == expected_census,
        "composite semantic specification census drift",
    )
    for domain_name, expected_digest in value["domain_sha256"].items():
        _require(
            expected_digest == _domain_sha(value[domain_name]),
            f"composite semantic specification domain drift: {domain_name}",
        )
    _require(
        set(value["ordered_instruction_domain"])
        == set(COMPOSITE_IMPORT_INSTRUCTION_IDS)
        and len(value["ordered_instruction_domain"]) == 21,
        "composite instruction domain drift",
    )
    decisions = value["instruction_decisions"]
    instruction_law, _instruction_law_identity = (
        _composite_instruction_law_specification()
    )
    instruction_law_by_index = {
        row["sweep_row_index"]: row
        for row in instruction_law["instruction_law_rows"]
    }
    _require(
        [row["instruction_id"] for row in decisions]
        == value["ordered_instruction_domain"],
        "composite decision ordering drift",
    )
    all_evidence_ids: list[str] = []
    pair_evidence_ids: list[str] = []
    stop_evidence_ids: list[str] = []
    pair_ids: list[str] = []
    stop_ids: list[str] = []
    unmatched_selector_stop_ids: list[str] = []
    exact_pairing_citation_count = 0
    missing_stop_citation_count = 0
    unmatched_selector_citation_count = 0
    for decision in decisions:
        _require_exact_keys(
            decision, COMPOSITE_DECISION_KEYS, "composite decision"
        )
        sweep_index = decision["sweep_row_index"]
        law = instruction_law_by_index.get(sweep_index)
        _require(
            law is not None
            and law["instruction_id"] == decision["instruction_id"],
            "composite instruction is absent from the closed selector law",
        )
        instruction_position = law[
            "expected_instruction_document_source_position"
        ]
        questionnaire_position = law[
            "expected_questionnaire_document_source_position"
        ]
        selector_law_by_side = {
            side: {
                row["selector"]: row["members"]
                for row in law[f"ordered_{side}_selector_domain"]
            }
            for side in ("alias", "canonical")
        }
        selector_coverage_by_side: dict[str, dict[str, list[str]]] = {
            "alias": {},
            "canonical": {},
        }
        paired_members_by_side: dict[str, set[str]] = {
            "alias": set(),
            "canonical": set(),
        }
        unmatched_members_by_side: dict[str, set[str]] = {
            "alias": set(),
            "canonical": set(),
        }
        cover_selector = _make_composite_selector_coverer(
            selector_law_by_side,
            selector_coverage_by_side,
        )

        source_ids = decision["source_evidence_ids"]
        approved_ids = decision["pair_producing_source_evidence_ids"]
        rejected_ids = decision["stop_source_evidence_ids"]
        _require(
            len(source_ids) == len(set(source_ids))
            and set(source_ids) == set(approved_ids) | set(rejected_ids)
            and not set(approved_ids) & set(rejected_ids),
            "composite decision does not exact-cover its source evidence",
        )
        pairs = decision["typed_projection_pairs"]
        stops = decision["stop_evidence_rows"]
        unmatched_stops = decision["unmatched_selector_stop_rows"]
        _require(
            {row["source_evidence_id"] for row in pairs} == set(approved_ids)
            and {row["source_evidence_id"] for row in stops}
            == set(rejected_ids),
            "composite pair/STOP rows do not match decision domains",
        )
        pair_ids_in_decision: list[str] = []
        for pair in pairs:
            _require_exact_keys(
                pair, COMPOSITE_TYPED_PAIR_KEYS, "composite typed pair"
            )
            _require(
                pair["instruction_id"] == decision["instruction_id"]
                and pair["instruction_citation"]["document_source_position"]
                == instruction_position,
                "composite pair instruction drift",
            )
            citation = pair["exact_pairing_citation"]
            _require_exact_keys(
                citation,
                COMPOSITE_EXACT_PAIRING_CITATION_KEYS,
                "composite exact pairing citation",
            )
            _require(
                citation["citation_rule"]
                == "exact_named_instruction_plus_selector_member_text_"
                "semantic_type_match_derives_only_this_pair"
                and citation["semantic_type"] == pair["semantic_type"],
                "composite exact pairing citation semantic rule drift",
            )
            citation_identity_rows: list[str] = []
            for side in ("alias", "canonical"):
                citation_rows = citation[f"{side}_selector_citation_rows"]
                _require(
                    isinstance(citation_rows, list) and citation_rows,
                    f"composite {side} selector citation rows",
                )
                member_rows = [
                    _validate_selector_citation_shape(
                        row, f"composite {side} selector citation"
                    )
                    for row in citation_rows
                ]
                members = citation[f"{side}_selector_members"]
                _require(
                    members
                    == list(
                        dict.fromkeys(member for member, _id in member_rows)
                    )
                    and len({identity for _member, identity in member_rows})
                    == len(member_rows),
                    f"composite {side} selector citation exact cover",
                )
                selector = pair[f"{side}_question_selector"]
                cover_selector(
                    side,
                    selector,
                    members,
                    f"composite typed {side} pair",
                )
                _require(
                    not paired_members_by_side[side] & set(members)
                    and all(
                        row["document_source_position"]
                        == questionnaire_position
                        for row in citation_rows
                    ),
                    f"composite typed {side} pair member or source reuse",
                )
                paired_members_by_side[side].update(members)
                citation_identity_rows.extend(
                    identity for _member, identity in member_rows
                )
            _require(
                citation["questionnaire_document_source_position"]
                == questionnaire_position
                == citation["alias_selector_citation_rows"][0][
                    "document_source_position"
                ]
                == citation["canonical_selector_citation_rows"][0][
                    "document_source_position"
                ]
                and citation["selector_citation_domain_sha256"]
                == _domain_sha(
                    [
                        citation["alias_selector_citation_rows"],
                        citation["canonical_selector_citation_rows"],
                        citation["semantic_type"],
                    ]
                )
                and citation["pairing_citation_id"]
                == _row_id(
                    "a12-composite-exact-pairing-citation:",
                    [
                        pair["instruction_id"],
                        pair["source_evidence_id"],
                        pair["alias_question_selector"],
                        pair["canonical_question_selector"],
                        pair["semantic_type"],
                        citation["alias_selector_citation_rows"],
                        citation["canonical_selector_citation_rows"],
                    ],
                ),
                "composite exact pairing citation identity drift",
            )
            expected_pair_id = _row_id(
                "a12-composite-typed-projection-pair:",
                [
                    pair["instruction_id"],
                    pair["source_evidence_id"],
                    pair["alias_combined_occurrence_id"],
                    pair["canonical_combined_occurrence_id"],
                    pair["alias_question_selector"],
                    pair["canonical_question_selector"],
                    pair["semantic_type"],
                    pair["pairing_basis_code"],
                    pair["instruction_citation"],
                    citation,
                ],
            )
            _require(
                pair["typed_projection_pair_id"] == expected_pair_id,
                "composite typed pair identity drift",
            )
            pair_ids_in_decision.append(expected_pair_id)
            exact_pairing_citation_count += len(citation_identity_rows)
        stop_ids_in_decision: list[str] = []
        for stop in stops:
            _require_exact_keys(
                stop, COMPOSITE_STOP_KEYS, "composite evidence STOP"
            )
            _require(
                stop["instruction_id"] == decision["instruction_id"]
                and stop["instruction_citation"]["document_source_position"]
                == instruction_position,
                "composite STOP instruction drift",
            )
            selector_audit = stop["selector_source_audit"]
            if selector_audit is None:
                _require(
                    stop["pairing_source_status"]
                    == "exact_instruction_text_does_not_derive_pair",
                    "composite evidence STOP source status drift",
                )
                for side in ("alias", "canonical"):
                    selector = stop[f"{side}_question_selector"]
                    members = selector_law_by_side[side].get(selector)
                    if members is not None:
                        cover_selector(
                            side,
                            selector,
                            members,
                            f"composite unaudited STOP {side}",
                        )
            else:
                _require_exact_keys(
                    selector_audit,
                    COMPOSITE_STOP_SELECTOR_AUDIT_KEYS,
                    "composite evidence STOP selector audit",
                )
                _require(
                    stop["pairing_source_status"]
                    == "missing_exact_selector_text"
                    and selector_audit["support_status"]
                    == "disclosed_stop_missing_registered_question_text"
                    and selector_audit["missing_source_rows"],
                    "composite missing-selector STOP drift",
                )
                missing_rows = selector_audit["missing_source_rows"]
                for missing in missing_rows:
                    _require_exact_keys(
                        missing,
                        COMPOSITE_STOP_MISSING_SOURCE_ROW_KEYS,
                        "composite STOP missing-source row",
                    )
                    _require(
                        missing["side"] in {"alias", "canonical"}
                        and missing["reason_code"]
                        in COMPOSITE_STOP_MISSING_SOURCE_REASON_CODES
                        and missing["finding"]
                        == COMPOSITE_STOP_MISSING_SOURCE_FINDING
                        and missing["selector"]
                        == stop[f"{missing['side']}_question_selector"],
                        "composite STOP missing-source row law drift",
                    )
                for side in ("alias", "canonical"):
                    selector = stop[f"{side}_question_selector"]
                    citation_rows = selector_audit[
                        f"{side}_selector_citation_rows"
                    ]
                    missing_side_rows = [
                        row for row in missing_rows if row["side"] == side
                    ]
                    member_rows = [
                        _validate_selector_citation_shape(
                            citation,
                            f"composite STOP {side} available citation",
                        )
                        for citation in citation_rows
                    ]
                    if citation_rows:
                        citation_members = list(
                            dict.fromkeys(
                                member for member, _identity in member_rows
                            )
                        )
                        _require(
                            not missing_side_rows
                            and all(
                                citation["document_source_position"]
                                == questionnaire_position
                                for citation in citation_rows
                            ),
                            f"composite STOP {side} citation source drift",
                        )
                        cover_selector(
                            side,
                            selector,
                            citation_members,
                            f"composite STOP {side} citation",
                        )
                    else:
                        _require(
                            len(missing_side_rows) == 1,
                            f"composite STOP {side} missing exact cover",
                        )
                        expected_members = selector_law_by_side[side].get(
                            selector
                        )
                        _require(
                            expected_members is not None,
                            f"composite STOP {side} missing selector law",
                        )
                        cover_selector(
                            side,
                            selector,
                            expected_members,
                            f"composite STOP {side} missing source",
                        )
                    for _citation in citation_rows:
                        missing_stop_citation_count += 1
            expected_stop_id = _row_id(
                "a12-composite-import-stop:",
                [
                    stop["instruction_id"],
                    stop["source_evidence_id"],
                    stop["alias_combined_occurrence_id"],
                    stop["canonical_combined_occurrence_id"],
                    stop["finding_code"],
                    stop["pairing_source_status"],
                    selector_audit,
                ],
            )
            _require(
                stop["stop_adjudication_id"] == expected_stop_id,
                "composite evidence STOP identity drift",
            )
            stop_ids_in_decision.append(expected_stop_id)
        unmatched_ids_in_decision: list[str] = []
        for stop in unmatched_stops:
            _require_exact_keys(
                stop,
                COMPOSITE_UNMATCHED_SELECTOR_STOP_KEYS,
                "composite unmatched selector STOP",
            )
            _require(
                stop["sweep_row_index"] == decision["sweep_row_index"]
                and stop["selector_side"] in {"alias", "canonical"}
                and stop["required_disposition"]
                == "disclosed_unmatched_selector_stop"
                and bool(stop["stop_source_evidence_ids"])
                is stop["represented_by_existing_stop_source_evidence"]
                and set(stop["stop_source_evidence_ids"])
                <= set(decision["stop_source_evidence_ids"]),
                "composite unmatched selector STOP disposition drift",
            )
            citation_rows = stop["selector_citation_rows"]
            _require(
                isinstance(citation_rows, list) and citation_rows,
                "composite unmatched selector citation rows",
            )
            member_rows: list[tuple[str, str]] = []
            for citation in citation_rows:
                member, _identity = _validate_selector_citation_shape(
                    citation, "composite unmatched selector citation"
                )
                member_rows.append((member, _identity))
                unmatched_selector_citation_count += 1
            side = stop["selector_side"]
            unmatched_members = list(
                dict.fromkeys(member for member, _identity in member_rows)
            )
            cover_selector(
                side,
                stop["question_selector"],
                unmatched_members,
                "composite unmatched selector STOP",
            )
            _require(
                not paired_members_by_side[side] & set(unmatched_members)
                and not unmatched_members_by_side[side]
                & set(unmatched_members)
                and all(
                    citation["document_source_position"]
                    == questionnaire_position
                    for citation in citation_rows
                ),
                "composite paired/unmatched selector domain overlap",
            )
            unmatched_members_by_side[side].update(unmatched_members)
            expected_unmatched_id = _row_id(
                "a12-composite-unmatched-selector-stop:",
                [
                    decision["instruction_id"],
                    stop["selector_side"],
                    stop["question_selector"],
                    stop["semantic_type"],
                    stop["finding_code"],
                    stop["stop_source_evidence_ids"],
                    citation_rows,
                ],
            )
            _require(
                stop["unmatched_selector_stop_id"] == expected_unmatched_id,
                "composite unmatched selector STOP identity drift",
            )
            unmatched_ids_in_decision.append(expected_unmatched_id)
        actual_typed_triples = [
            [
                pair["alias_question_selector"],
                pair["canonical_question_selector"],
                pair["semantic_type"],
            ]
            for pair in pairs
        ]
        actual_stop_tuples = [
            [
                stop["alias_question_selector"],
                stop["canonical_question_selector"],
                stop["finding_code"],
                stop["pairing_source_status"],
            ]
            for stop in stops
        ]
        actual_unmatched_tuples = [
            [
                stop["selector_side"],
                stop["question_selector"],
                stop["semantic_type"],
                stop["represented_by_existing_stop_source_evidence"],
            ]
            for stop in unmatched_stops
        ]
        _require(
            actual_typed_triples == law["allowed_typed_pair_triples"]
            and actual_stop_tuples == law["expected_stop_pair_tuples"]
            and actual_unmatched_tuples
            == law["expected_unmatched_selector_tuples"]
            and selector_coverage_by_side
            == {
                side: {
                    row["selector"]: row["members"]
                    for row in law[f"ordered_{side}_selector_domain"]
                }
                for side in ("alias", "canonical")
            },
            "composite instruction selector relevance/exact-cover law drift",
        )
        _validate_composite_instruction_selector_commitment(decision)
        expected_disposition = (
            "disclosed_stop"
            if not pairs
            else (
                "pairwise_decomposition_with_disclosed_stops"
                if stops or unmatched_stops
                else "pairwise_decomposition"
            )
        )
        _require(
            decision["disposition"] == expected_disposition
            and decision["instruction_decision_id"]
            == _row_id(
                "a12-composite-import-instruction-decision:",
                [
                    decision["sweep_row_index"],
                    decision["instruction_id"],
                    decision["disposition"],
                    source_ids,
                    pair_ids_in_decision,
                    stop_ids_in_decision,
                    unmatched_ids_in_decision,
                ],
            ),
            "composite instruction decision identity drift",
        )
        all_evidence_ids.extend(source_ids)
        pair_evidence_ids.extend(approved_ids)
        stop_evidence_ids.extend(rejected_ids)
        pair_ids.extend(row["typed_projection_pair_id"] for row in pairs)
        stop_ids.extend(row["stop_adjudication_id"] for row in stops)
        unmatched_selector_stop_ids.extend(unmatched_ids_in_decision)
    _require(
        all_evidence_ids == value["ordered_source_evidence_domain"]
        and pair_evidence_ids
        == value["ordered_pair_producing_source_evidence_domain"]
        and stop_evidence_ids == value["ordered_stop_source_evidence_domain"]
        and pair_ids == value["ordered_typed_projection_pair_domain"]
        and stop_ids == value["ordered_stop_adjudication_domain"],
        "composite semantic ordered-domain projection drift",
    )
    _require(
        unmatched_selector_stop_ids
        == value["ordered_unmatched_selector_stop_domain"]
        and exact_pairing_citation_count
        == expected_census["exact_pairing_selector_citation_row_count"]
        and missing_stop_citation_count
        == expected_census[
            "missing_pair_stop_available_selector_citation_row_count"
        ]
        and unmatched_selector_citation_count
        == expected_census["unmatched_selector_citation_row_count"],
        "composite exact selector citation census drift",
    )
    return value, identity


@cache
def _composite_import_decisions_by_instruction() -> dict[str, dict[str, Any]]:
    specification, _identity = _composite_import_semantic_specification()
    return {
        row["instruction_id"]: {
            **row,
            "approved_source_local_evidence_ids": row[
                "pair_producing_source_evidence_ids"
            ],
            "stop_source_local_evidence_ids": row["stop_source_evidence_ids"],
            "approved_pair_count": len(row["typed_projection_pairs"]),
        }
        for row in specification["instruction_decisions"]
    }


@cache
def _composite_adjudications_by_id() -> (
    tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]
):
    """Index the pinned composite pair and STOP decisions by sealed ID."""
    specification, _identity = _composite_import_semantic_specification()
    pairs: dict[str, Mapping[str, Any]] = {}
    stops: dict[str, Mapping[str, Any]] = {}
    for decision in specification["instruction_decisions"]:
        for pair in decision["typed_projection_pairs"]:
            pair_id = pair["typed_projection_pair_id"]
            _require(pair_id not in pairs, "duplicate composite pair ID")
            pairs[pair_id] = pair
        for stop in decision["stop_evidence_rows"]:
            stop_id = stop["stop_adjudication_id"]
            _require(stop_id not in stops, "duplicate composite STOP ID")
            stops[stop_id] = stop
    return pairs, stops


def _semantic_alias_pair_row(
    document: NormalizedDocument,
    evidence: Mapping[str, Any],
    pair_specification: Mapping[str, Any],
    *,
    pair_ordinal: int,
    pair_kind: str,
) -> dict[str, Any]:
    """Bind one approved semantic pair to exact source and endpoint bytes."""
    alias_id = pair_specification["alias_occurrence_id"]
    canonical_id = pair_specification["canonical_occurrence_id"]
    aliases = evidence["alias_anchor_occurrence_ids"]
    canonicals = evidence["canonical_anchor_occurrence_ids"]
    _require(
        alias_id in aliases and canonical_id in canonicals,
        "semantic pair endpoint is absent from cited evidence",
    )
    endpoint_ids = [*aliases, *canonicals]
    alias_index = endpoint_ids.index(alias_id)
    canonical_index = endpoint_ids.index(canonical_id)

    def endpoint_value(key: str, index: int) -> Any:
        return evidence[key][index]

    class_closure_eligible = pair_kind == "atomic_occurrence_pair"
    exact_pairing_citation = pair_specification.get("exact_pairing_citation")
    composite_typed_projection_pair_id = pair_specification.get(
        "composite_typed_projection_pair_id"
    )
    _require(
        (exact_pairing_citation is not None)
        is (pair_kind == "typed_instruction_import_projection")
        and (composite_typed_projection_pair_id is not None)
        is (pair_kind == "typed_instruction_import_projection"),
        "typed semantic pair lacks its exact selector citation",
    )
    row = {
        "source_local_evidence_id": evidence["local_evidence_id"],
        "pair_ordinal": pair_ordinal,
        "pair_kind": pair_kind,
        "pairing_basis_code": pair_specification["pairing_basis_code"],
        "semantic_type": pair_specification.get(
            "semantic_type", "occurrence_equivalence"
        ),
        "alias_occurrence_id": alias_id,
        "canonical_occurrence_id": canonical_id,
        "alias_question_selector": pair_specification.get(
            "alias_question_selector"
        ),
        "canonical_question_selector": pair_specification.get(
            "canonical_question_selector"
        ),
        "exact_pairing_citation": exact_pairing_citation,
        "composite_typed_projection_pair_id": (
            composite_typed_projection_pair_id
        ),
        "alias_endpoint_matched_text": endpoint_value(
            "endpoint_matched_texts", alias_index
        ),
        "alias_endpoint_matched_utf8_sha256": endpoint_value(
            "endpoint_matched_utf8_sha256s", alias_index
        ),
        "alias_endpoint_page_number": endpoint_value(
            "endpoint_page_numbers", alias_index
        ),
        "alias_endpoint_utf8_byte_start": endpoint_value(
            "endpoint_utf8_byte_starts", alias_index
        ),
        "alias_endpoint_utf8_byte_end": endpoint_value(
            "endpoint_utf8_byte_ends", alias_index
        ),
        "canonical_endpoint_matched_text": endpoint_value(
            "endpoint_matched_texts", canonical_index
        ),
        "canonical_endpoint_matched_utf8_sha256": endpoint_value(
            "endpoint_matched_utf8_sha256s", canonical_index
        ),
        "canonical_endpoint_page_number": endpoint_value(
            "endpoint_page_numbers", canonical_index
        ),
        "canonical_endpoint_utf8_byte_start": endpoint_value(
            "endpoint_utf8_byte_starts", canonical_index
        ),
        "canonical_endpoint_utf8_byte_end": endpoint_value(
            "endpoint_utf8_byte_ends", canonical_index
        ),
        "source_instruction_occurrence_ids": evidence[
            "source_instruction_occurrence_ids"
        ],
        "source_instruction_matched_texts": evidence[
            "source_instruction_matched_texts"
        ],
        "source_instruction_matched_utf8_sha256s": evidence[
            "source_instruction_matched_utf8_sha256s"
        ],
        "source_instruction_page_numbers": evidence[
            "source_instruction_page_numbers"
        ],
        "source_instruction_utf8_byte_starts": evidence[
            "source_instruction_utf8_byte_starts"
        ],
        "source_instruction_utf8_byte_ends": evidence[
            "source_instruction_utf8_byte_ends"
        ],
        "class_closure_eligible": class_closure_eligible,
        "typed_projection_union_prohibited": not class_closure_eligible,
        "status": "source_cited_semantic_pair_approved",
    }
    row["semantic_alias_pair_adjudication_id"] = _row_id(
        "a12-semantic-alias-pair-adjudication:",
        [
            document.source_document_id,
            evidence["local_evidence_id"],
            pair_ordinal,
            pair_kind,
            row["pairing_basis_code"],
            row["semantic_type"],
            alias_id,
            canonical_id,
            row["alias_question_selector"],
            row["canonical_question_selector"],
            row["alias_endpoint_matched_utf8_sha256"],
            row["canonical_endpoint_matched_utf8_sha256"],
            row["source_instruction_matched_utf8_sha256s"],
            exact_pairing_citation,
            composite_typed_projection_pair_id,
        ],
    )
    return row


def _semantic_alias_evidence_row(
    document: NormalizedDocument,
    evidence: Mapping[str, Any],
    *,
    candidate_origin: str,
    ca41663_admitted_alias_evidence: bool,
    semantic_finding: str,
    decision: str,
    pair_rows: Sequence[Mapping[str, Any]],
    continuation_citation: Mapping[str, Any] | None = None,
    composite_stop_citation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize one source-cited decision before any A-arm admission."""
    row = {
        "document_source_position": document.position,
        "source_document_id": document.source_document_id,
        "source_local_evidence_id": evidence["local_evidence_id"],
        "candidate_origin": candidate_origin,
        "ca41663_admitted_alias_evidence": ca41663_admitted_alias_evidence,
        "round_five_continuation_restoration": (
            candidate_origin == "round_five_continuation_restoration"
        ),
        "structural_filter_satisfied": _compatible_direct_proof(evidence),
        "relation": evidence["relation"],
        "handoff_status": evidence["handoff_status"],
        "source_instruction_occurrence_ids": evidence[
            "source_instruction_occurrence_ids"
        ],
        "source_instruction_matched_texts": evidence[
            "source_instruction_matched_texts"
        ],
        "source_instruction_matched_utf8_sha256s": evidence[
            "source_instruction_matched_utf8_sha256s"
        ],
        "source_instruction_page_numbers": evidence[
            "source_instruction_page_numbers"
        ],
        "source_instruction_utf8_byte_starts": evidence[
            "source_instruction_utf8_byte_starts"
        ],
        "source_instruction_utf8_byte_ends": evidence[
            "source_instruction_utf8_byte_ends"
        ],
        "alias_anchor_occurrence_ids": evidence["alias_anchor_occurrence_ids"],
        "canonical_anchor_occurrence_ids": evidence[
            "canonical_anchor_occurrence_ids"
        ],
        "evidence_occurrence_ids": evidence["evidence_occurrence_ids"],
        "endpoint_matched_texts": evidence["endpoint_matched_texts"],
        "endpoint_matched_utf8_sha256s": evidence[
            "endpoint_matched_utf8_sha256s"
        ],
        "endpoint_page_numbers": evidence["endpoint_page_numbers"],
        "endpoint_utf8_byte_starts": evidence["endpoint_utf8_byte_starts"],
        "endpoint_utf8_byte_ends": evidence["endpoint_utf8_byte_ends"],
        "semantic_adjudication_round": 5,
        "semantic_finding": semantic_finding,
        "decision": decision,
        "approved_pair_rows": list(pair_rows),
        "approved_pair_count": len(pair_rows),
        "continuation_composition_citation": continuation_citation,
        "composite_stop_citation": composite_stop_citation,
        "status": (
            "source_cited_semantic_alias_approved"
            if pair_rows
            else "source_cited_semantic_alias_disclosed_stop"
        ),
    }
    _require(
        row["structural_filter_satisfied"],
        "semantic ledger candidate fails structural filter",
    )
    _require(
        bool(pair_rows) == decision.startswith("approved_"),
        "semantic decision/pair mismatch",
    )
    row["semantic_alias_evidence_adjudication_id"] = _row_id(
        "a12-semantic-alias-evidence-adjudication:",
        [
            document.source_document_id,
            evidence["local_evidence_id"],
            candidate_origin,
            ca41663_admitted_alias_evidence,
            row["source_instruction_matched_utf8_sha256s"],
            row["endpoint_matched_utf8_sha256s"],
            semantic_finding,
            decision,
            [
                pair["semantic_alias_pair_adjudication_id"]
                for pair in pair_rows
            ],
            continuation_citation,
            composite_stop_citation,
        ],
    )
    return row


def _validate_composite_instruction_citation(
    document: NormalizedDocument,
    evidence: Mapping[str, Any],
    citation: Mapping[str, Any],
) -> None:
    _require(
        len(evidence["source_instruction_occurrence_ids"]) == 1
        and citation["document_source_position"] == document.position
        and citation["source_document_id"] == document.source_document_id
        and citation["matched_text"]
        == evidence["source_instruction_matched_texts"][0]
        and citation["matched_utf8_sha256"]
        == evidence["source_instruction_matched_utf8_sha256s"][0]
        and citation["page_number"]
        == evidence["source_instruction_page_numbers"][0]
        and citation["utf8_byte_span"]
        == {
            "start": evidence["source_instruction_utf8_byte_starts"][0],
            "end": evidence["source_instruction_utf8_byte_ends"][0],
        },
        "composite exact-text citation drift",
    )


SELECTOR_SOURCE_ANNOTATION_IDENTITY_KEYS = frozenset(
    {
        "candidate_artifact_identity",
        "document_source_position",
        "source_document_row",
        "stage2_annotation_artifact_id",
        "stage2_annotation_path",
        "stage2_annotation_raw_byte_size",
        "stage2_annotation_raw_sha256",
        "stage2_annotation_source_commit",
        "whole_document_locator",
    }
)


@cache
def _load_selector_candidate_artifact(
    path: str,
    byte_size: int,
    raw_sha256: str,
    content_sha256: str,
    candidate_payload_sha256: str,
) -> Mapping[str, Any]:
    """Load one stage-1 citation carrier from the pinned source commit."""
    raw = SourceReader(None).read(path)
    _require(
        len(raw) == byte_size and _sha256(raw) == raw_sha256,
        "selector candidate artifact raw identity drift",
    )
    value = strict_json_loads(raw, path)
    _require(
        isinstance(value, dict)
        and value["schema_version"]
        == "rq_stage1_document_annotation_candidates.v1"
        and value["integrity"]["content_sha256"] == content_sha256
        and value["candidate_manifest"]["candidate_payload_sha256"]
        == candidate_payload_sha256,
        "selector candidate artifact sealed identity drift",
    )
    return value


def _validate_selector_source_citation(
    citation: Mapping[str, Any],
    document_by_position: Mapping[int, NormalizedDocument],
) -> None:
    """Deep-match one selector citation to a pinned stage-2 or stage-1 row."""
    _validate_selector_citation_shape(citation, "selector source citation")
    position = citation["document_source_position"]
    _require(
        position in document_by_position,
        "selector citation document is absent from authenticated source set",
    )
    document = document_by_position[position]
    source = document.source_document_row
    storage = source["storage_identity"]
    page = document.questionnaire_page_rows_by_number.get(
        citation["page_number"]
    )
    _require(
        citation["source_document_id"] == document.source_document_id
        and citation["stage2_annotation_path"] == document.annotation_path
        and citation["stage2_annotation_source_commit"] == SOURCE_COMMIT
        and citation["registered_pdf_byte_size"] == source["byte_size"]
        and citation["registered_pdf_sha256"] == source["sha256"]
        and citation["registered_path"] == storage["registered_path"]
        and citation["authority_registry_id"]
        == storage["authority_registry_id"]
        and citation["registry_document_id"] == storage["document_id"]
        and source["canonical_source_path"] == citation["registered_path"]
        and source["storage_disposition"] == "external_registered_file"
        and page is not None
        and citation["questionnaire_page_id"] == page["questionnaire_page_id"]
        and citation["page_text_utf8_sha256"] == page["page_text_utf8_sha256"],
        "selector citation registered source or page identity drift",
    )
    kind = citation["citation_kind"]
    if kind == "pinned_stage2_questionnaire_occurrence":
        occurrence = document.questionnaire_occurrence_rows_by_id.get(
            citation["questionnaire_occurrence_id"]
        )
        _require(
            occurrence is not None
            and occurrence["source_document_id"] == document.source_document_id
            and occurrence["page_number"] == citation["page_number"]
            and occurrence["matched_text"] == citation["matched_text"]
            and occurrence["matched_utf8_sha256"]
            == citation["matched_utf8_sha256"]
            and occurrence["utf8_byte_start"]
            == citation["utf8_byte_span"]["start"]
            and occurrence["utf8_byte_end"]
            == citation["utf8_byte_span"]["end"],
            "selector stage-2 occurrence citation drift",
        )
        return

    candidate_identity = document.candidate_artifact_identity
    _require(
        citation["candidate_artifact_path"] == candidate_identity["path"]
        and citation["candidate_artifact_raw_byte_size"]
        == candidate_identity["byte_size"]
        and citation["candidate_artifact_raw_sha256"]
        == candidate_identity["raw_sha256"]
        and citation["candidate_artifact_content_sha256"]
        == candidate_identity["content_sha256"]
        and citation["candidate_artifact_payload_sha256"]
        == candidate_identity["candidate_payload_sha256"],
        "selector stage-1 candidate artifact citation drift",
    )
    candidate = _load_selector_candidate_artifact(
        candidate_identity["path"],
        candidate_identity["byte_size"],
        candidate_identity["raw_sha256"],
        candidate_identity["content_sha256"],
        candidate_identity["candidate_payload_sha256"],
    )
    _require(
        candidate["document_source_position"] == position
        and candidate["document_source_row"] == source,
        "selector candidate artifact document drift",
    )
    occurrence = next(
        (
            row
            for row in candidate["candidate_occurrence_rows"]
            if row["candidate_occurrence_id"]
            == citation["candidate_occurrence_id"]
        ),
        None,
    )
    candidate_page = next(
        (
            row
            for row in candidate["candidate_page_rows"]
            if row["page_number"] == citation["page_number"]
        ),
        None,
    )
    _require(
        occurrence is not None
        and candidate_page is not None
        and occurrence["source_document_id"] == document.source_document_id
        and occurrence["page_number"] == citation["page_number"]
        and occurrence["matched_text"] == citation["matched_text"]
        and occurrence["matched_utf8_sha256"]
        == citation["matched_utf8_sha256"]
        and occurrence["utf8_byte_start"]
        == citation["utf8_byte_span"]["start"]
        and occurrence["utf8_byte_end"] == citation["utf8_byte_span"]["end"]
        and occurrence["occurrence_kind_candidate"]
        == citation["candidate_occurrence_kind"]
        and occurrence["detector_rule_ids"]
        == citation["candidate_detector_rule_ids"]
        and candidate_page["replay_questionnaire_page_id"]
        == citation["questionnaire_page_id"]
        and candidate_page["page_text_utf8_sha256"]
        == citation["page_text_utf8_sha256"]
        and (
            "evidence_part" not in citation or bool(citation["evidence_part"])
        ),
        "selector stage-1 candidate occurrence citation drift",
    )


def _validate_composite_selector_sources(
    specification: Mapping[str, Any],
    citation_documents: Sequence[NormalizedDocument],
) -> None:
    """Authenticate every exact selector citation used by a composite ruling."""
    document_by_position = {
        document.position: document for document in citation_documents
    }
    source_rows = specification["selector_source_annotation_identity_rows"]
    _require(
        [row["document_source_position"] for row in source_rows]
        == [57, 59, 71],
        "selector source annotation domain drift",
    )
    for row in source_rows:
        _require_exact_keys(
            row,
            SELECTOR_SOURCE_ANNOTATION_IDENTITY_KEYS,
            "selector source annotation identity",
        )
        position = row["document_source_position"]
        _require(
            position in document_by_position,
            "selector source annotation document absent",
        )
        document = document_by_position[position]
        _require(
            row["stage2_annotation_source_commit"] == SOURCE_COMMIT
            and row["stage2_annotation_path"] == document.annotation_path
            and row["stage2_annotation_artifact_id"]
            == document.annotation_identity["artifact_id"]
            and row["stage2_annotation_raw_byte_size"]
            == document.annotation_identity["byte_size"]
            and row["stage2_annotation_raw_sha256"]
            == document.annotation_identity["raw_sha256"]
            and row["source_document_row"] == document.source_document_row
            and row["candidate_artifact_identity"]
            == document.candidate_artifact_identity
            and row["whole_document_locator"]
            == document.whole_document_locator,
            "selector source annotation identity drift",
        )

    citations: list[Mapping[str, Any]] = []
    for decision in specification["instruction_decisions"]:
        for pair in decision["typed_projection_pairs"]:
            exact = pair["exact_pairing_citation"]
            citations.extend(exact["alias_selector_citation_rows"])
            citations.extend(exact["canonical_selector_citation_rows"])
        for stop in decision["stop_evidence_rows"]:
            selector_audit = stop["selector_source_audit"]
            if selector_audit is not None:
                citations.extend(
                    selector_audit["alias_selector_citation_rows"]
                )
                citations.extend(
                    selector_audit["canonical_selector_citation_rows"]
                )
        for stop in decision["unmatched_selector_stop_rows"]:
            citations.extend(stop["selector_citation_rows"])
    seen: set[str] = set()
    for citation in citations:
        citation_digest = _domain_sha(citation)
        if citation_digest in seen:
            continue
        seen.add(citation_digest)
        _validate_selector_source_citation(citation, document_by_position)


def _alias_evidence_semantic_adjudication_rows(
    documents: Sequence[NormalizedDocument],
    *,
    outside_rows: Sequence[Mapping[str, Any]],
    aggregate_rows: Sequence[Mapping[str, Any]],
    redirection_rows: Sequence[Mapping[str, Any]],
    structural_rows: Sequence[Mapping[str, Any]],
    citation_documents: Sequence[NormalizedDocument] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Exact-cover every former A candidate before returning any A pair."""
    document_positions = tuple(document.position for document in documents)
    if document_positions == tuple(range(1, 82)):
        expected_census = {
            "structural_candidate_evidence_count": 157,
            "candidate_evidence_count": 265,
            "ca41663_admitted_evidence_count": 262,
            "approved_evidence_count": 229,
            "stop_evidence_count": 36,
            "approved_pair_count": 258,
            "closure_pair_count": 228,
        }
    elif document_positions == PILOT_POSITIONS:
        expected_census = {
            "structural_candidate_evidence_count": 100,
            "candidate_evidence_count": 125,
            "ca41663_admitted_evidence_count": 122,
            "approved_evidence_count": 100,
            "stop_evidence_count": 25,
            "approved_pair_count": 101,
            "closure_pair_count": 73,
        }
    else:
        raise BuildError(
            "semantic alias adjudication requires the complete corpus or "
            "the authenticated pilot slice"
        )
    nonledger_specification, nonledger_identity = (
        _nonledger_alias_semantic_specification()
    )
    composite_specification, composite_identity = (
        _composite_import_semantic_specification()
    )
    _validate_composite_selector_sources(
        composite_specification,
        documents if citation_documents is None else citation_documents,
    )
    evidence_by_id: dict[str, tuple[NormalizedDocument, Mapping[str, Any]]] = (
        {}
    )
    ordered_evidence_ids: list[str] = []
    for document in documents:
        for evidence in document.evidence_rows:
            evidence_id = evidence["local_evidence_id"]
            _require(
                evidence_id not in evidence_by_id,
                "duplicate local evidence ID in semantic candidate domain",
            )
            evidence_by_id[evidence_id] = (document, evidence)
            ordered_evidence_ids.append(evidence_id)

    structural_row_by_evidence_id: dict[str, Mapping[str, Any]] = {}
    structural_evidence_ids: list[str] = []
    structural_candidate_evidence_ids: list[str] = []
    for structural_row in structural_rows:
        instruction_id = structural_row["source_instruction_occurrence_id"]
        for evidence_id in structural_row["source_local_evidence_ids"]:
            _require(
                evidence_id not in structural_row_by_evidence_id,
                "structural semantic evidence belongs to multiple groups",
            )
            structural_row_by_evidence_id[evidence_id] = structural_row
            structural_evidence_ids.append(evidence_id)
            if (
                instruction_id
                in ROUND_FIVE_STRUCTURAL_ALIAS_CANDIDATE_INSTRUCTION_IDS
            ):
                structural_candidate_evidence_ids.append(evidence_id)
    _require(
        len(structural_candidate_evidence_ids)
        == expected_census["structural_candidate_evidence_count"],
        "round-five structural alias candidate census drift",
    )

    outside_evidence_ids = {
        row["source_local_evidence_id"] for row in outside_rows
    }
    aggregate_evidence_ids = {
        row["source_local_evidence_id"] for row in aggregate_rows
    }
    redirection_evidence_ids = {
        evidence_id
        for row in redirection_rows
        for evidence_id in row["source_local_evidence_ids"]
    }
    excluded_instruction_ids = {
        row["source_instruction_occurrence_id"] for row in outside_rows
    } | {
        instruction_id
        for row in [*aggregate_rows, *redirection_rows]
        for instruction_id in row["source_instruction_occurrence_ids"]
    }
    excluded_evidence_ids = (
        outside_evidence_ids
        | aggregate_evidence_ids
        | redirection_evidence_ids
        | set(structural_evidence_ids)
    )
    derived_nonledger_ids = [
        evidence_id
        for evidence_id in ordered_evidence_ids
        if evidence_id not in excluded_evidence_ids
        and _compatible_direct_proof(evidence_by_id[evidence_id][1])
        and not (
            set(
                evidence_by_id[evidence_id][1][
                    "source_instruction_occurrence_ids"
                ]
            )
            & excluded_instruction_ids
        )
    ]
    expected_nonledger_ids = [
        evidence_id
        for evidence_id in nonledger_specification[
            "ordered_nonledger_candidate_evidence_ids"
        ]
        if evidence_id in evidence_by_id
    ]
    _require(
        derived_nonledger_ids == expected_nonledger_ids,
        "structural filter changed the exact 108-row nonledger domain",
    )

    nonledger_single_by_id = {
        row["source_local_evidence_id"]: row
        for row in nonledger_specification["nonledger_single_pair_decisions"]
    }
    nonledger_pairwise_by_id = {
        row["source_local_evidence_id"]: row
        for row in nonledger_specification["nonledger_pairwise_decisions"]
    }
    nonledger_stop_by_id = {
        row["source_local_evidence_id"]: row
        for row in nonledger_specification["nonledger_stop_decisions"]
    }

    composite_pair_specs_by_evidence_id: defaultdict[
        str, list[dict[str, Any]]
    ] = defaultdict(list)
    composite_stop_specs_by_evidence_id: dict[str, dict[str, Any]] = {}
    for decision in composite_specification["instruction_decisions"]:
        for pair in decision["typed_projection_pairs"]:
            composite_pair_specs_by_evidence_id[
                pair["source_evidence_id"]
            ].append(pair)
        for stop in decision["stop_evidence_rows"]:
            evidence_id = stop["source_evidence_id"]
            _require(
                evidence_id not in composite_stop_specs_by_evidence_id,
                "duplicate composite STOP evidence decision",
            )
            composite_stop_specs_by_evidence_id[evidence_id] = stop

    candidate_ids = set(structural_candidate_evidence_ids) | set(
        expected_nonledger_ids
    )
    _require(
        len(candidate_ids) == expected_census["candidate_evidence_count"],
        "round-five semantic ledger does not cover 262 baseline plus 3 restorations",
    )
    adjudication_rows: list[dict[str, Any]] = []
    all_pair_rows: list[dict[str, Any]] = []
    for evidence_id in ordered_evidence_ids:
        if evidence_id not in candidate_ids:
            continue
        document, evidence = evidence_by_id[evidence_id]
        pair_rows: list[dict[str, Any]] = []
        continuation_citation: Mapping[str, Any] | None = None
        composite_stop_citation: Mapping[str, Any] | None = None
        if evidence_id in structural_row_by_evidence_id:
            structural_row = structural_row_by_evidence_id[evidence_id]
            instruction_id = structural_row["source_instruction_occurrence_id"]
            restored = (
                instruction_id in CONTINUATION_RESTORATION_INSTRUCTION_IDS
            )
            candidate_origin = (
                "round_five_continuation_restoration"
                if restored
                else "ca41663_structural_ledger_admission"
            )
            ca41663_admitted = not restored
            if instruction_id in COMPOSITE_IMPORT_INSTRUCTION_IDS:
                composite_pairs = composite_pair_specs_by_evidence_id.get(
                    evidence_id, []
                )
                composite_stop = composite_stop_specs_by_evidence_id.get(
                    evidence_id
                )
                _require(
                    bool(composite_pairs) != bool(composite_stop),
                    "composite evidence lacks exactly one semantic outcome",
                )
                if composite_pairs:
                    for ordinal, pair in enumerate(composite_pairs):
                        _validate_composite_instruction_citation(
                            document, evidence, pair["instruction_citation"]
                        )
                        pair_rows.append(
                            _semantic_alias_pair_row(
                                document,
                                evidence,
                                {
                                    "alias_occurrence_id": pair[
                                        "alias_combined_occurrence_id"
                                    ],
                                    "canonical_occurrence_id": pair[
                                        "canonical_combined_occurrence_id"
                                    ],
                                    "alias_question_selector": pair[
                                        "alias_question_selector"
                                    ],
                                    "canonical_question_selector": pair[
                                        "canonical_question_selector"
                                    ],
                                    "semantic_type": pair["semantic_type"],
                                    "pairing_basis_code": pair[
                                        "pairing_basis_code"
                                    ],
                                    "exact_pairing_citation": pair[
                                        "exact_pairing_citation"
                                    ],
                                    "composite_typed_projection_pair_id": (
                                        pair["typed_projection_pair_id"]
                                    ),
                                },
                                pair_ordinal=ordinal,
                                pair_kind="typed_instruction_import_projection",
                            )
                        )
                    semantic_finding = (
                        "exact_text_derives_typed_pairs_and_prohibits_"
                        "combined_occurrence_union"
                    )
                    decision = "approved_pairwise_typed_projection"
                else:
                    assert composite_stop is not None
                    _validate_composite_instruction_citation(
                        document,
                        evidence,
                        composite_stop["instruction_citation"],
                    )
                    composite_stop_citation = composite_stop
                    semantic_finding = composite_stop["finding_code"]
                    decision = "disclosed_stop"
            else:
                _require(
                    len(evidence["alias_anchor_occurrence_ids"]) == 1
                    and len(evidence["canonical_anchor_occurrence_ids"]) == 1,
                    "structural single-pair adjudication is not atomic",
                )
                continuation_citation = _continuation_alias_citation(
                    document, evidence, instruction_id
                )
                _require(
                    bool(continuation_citation)
                    is (
                        instruction_id
                        in CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS
                    ),
                    "continuation reading lacks its exact citation",
                )
                pair_rows.append(
                    _semantic_alias_pair_row(
                        document,
                        evidence,
                        {
                            "alias_occurrence_id": evidence[
                                "alias_anchor_occurrence_ids"
                            ][0],
                            "canonical_occurrence_id": evidence[
                                "canonical_anchor_occurrence_ids"
                            ][0],
                            "pairing_basis_code": (
                                CONTINUATION_COMPOSITION_RULE
                                if instruction_id
                                in CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS
                                else "round_four_exact_source_text_adjudication"
                            ),
                        },
                        pair_ordinal=0,
                        pair_kind="atomic_occurrence_pair",
                    )
                )
                semantic_finding = (
                    "whitespace_only_continuation_composes_named_import"
                    if instruction_id
                    in CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS
                    else SEMANTIC_ALIAS_EQUIVALENCE_FINDING
                )
                decision = "approved_single_pair"
        else:
            candidate_origin = "ca41663_nonledger_bypass_adjudication"
            ca41663_admitted = True
            if evidence_id in nonledger_single_by_id:
                single = nonledger_single_by_id[evidence_id]
                pair_specs = [single]
                semantic_finding = (
                    "exact_source_text_proves_explicit_single_pair"
                )
                decision = "approved_single_pair"
            elif evidence_id in nonledger_pairwise_by_id:
                pair_specs = nonledger_pairwise_by_id[evidence_id]["pairs"]
                semantic_finding = (
                    "exact_source_text_derives_only_the_enumerated_pairs"
                )
                decision = "approved_pairwise_decomposition"
            else:
                stop = nonledger_stop_by_id[evidence_id]
                pair_specs = []
                semantic_finding = stop["semantic_finding"]
                decision = "disclosed_stop"
            for ordinal, pair_specification in enumerate(pair_specs):
                pair_rows.append(
                    _semantic_alias_pair_row(
                        document,
                        evidence,
                        pair_specification,
                        pair_ordinal=ordinal,
                        pair_kind="atomic_occurrence_pair",
                    )
                )

        adjudication_rows.append(
            _semantic_alias_evidence_row(
                document,
                evidence,
                candidate_origin=candidate_origin,
                ca41663_admitted_alias_evidence=ca41663_admitted,
                semantic_finding=semantic_finding,
                decision=decision,
                pair_rows=pair_rows,
                continuation_citation=continuation_citation,
                composite_stop_citation=composite_stop_citation,
            )
        )
        all_pair_rows.extend(pair_rows)

    _require(
        len(adjudication_rows)
        == len(candidate_ids)
        == expected_census["candidate_evidence_count"]
        and len({row["source_local_evidence_id"] for row in adjudication_rows})
        == expected_census["candidate_evidence_count"]
        and sum(
            row["ca41663_admitted_alias_evidence"] for row in adjudication_rows
        )
        == expected_census["ca41663_admitted_evidence_count"]
        and sum(bool(row["approved_pair_rows"]) for row in adjudication_rows)
        == expected_census["approved_evidence_count"]
        and sum(not row["approved_pair_rows"] for row in adjudication_rows)
        == expected_census["stop_evidence_count"]
        and len(all_pair_rows) == expected_census["approved_pair_count"]
        and sum(row["class_closure_eligible"] for row in all_pair_rows)
        == expected_census["closure_pair_count"],
        "round-five semantic adjudication census drift",
    )
    _require(
        len(
            {
                row["semantic_alias_pair_adjudication_id"]
                for row in all_pair_rows
            }
        )
        == len(all_pair_rows),
        "duplicate semantic pair adjudication ID",
    )
    _instruction_law, instruction_law_identity = (
        _composite_instruction_law_specification()
    )
    return adjudication_rows, [
        nonledger_identity,
        composite_identity,
        instruction_law_identity,
    ]


def _in_domain_component_cross_reference_sweep_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    """Exact-walk every instruction-level structural candidate for R."""
    composite_decisions = _composite_import_decisions_by_instruction()
    redirection_by_instruction = {
        row["source_instruction_occurrence_ids"][0]: row
        for row in _in_domain_redirection_rows(documents)
    }
    endpoint_projection_keys = (
        "endpoint_occurrence_kinds",
        "endpoint_raw_node_domains",
        "endpoint_classifications",
        "endpoint_printed_identifiers",
        "endpoint_matched_texts",
        "endpoint_matched_utf8_sha256s",
        "endpoint_page_numbers",
        "endpoint_utf8_byte_starts",
        "endpoint_utf8_byte_ends",
    )
    nested_projection_keys = (
        "source_endpoint_occurrence_kind_arrays",
        "source_endpoint_raw_node_domain_arrays",
        "source_endpoint_classification_arrays",
        "source_endpoint_printed_identifier_arrays",
        "source_endpoint_matched_text_arrays",
        "source_endpoint_matched_utf8_sha256_arrays",
        "source_endpoint_page_number_arrays",
        "source_endpoint_utf8_byte_start_arrays",
        "source_endpoint_utf8_byte_end_arrays",
    )
    rows: list[dict[str, Any]] = []
    for document in documents:
        evidence_by_instruction: defaultdict[str, list[dict[str, Any]]] = (
            defaultdict(list)
        )
        for evidence in document.evidence_rows:
            for instruction_id in evidence[
                "source_instruction_occurrence_ids"
            ]:
                evidence_by_instruction[instruction_id].append(evidence)
        occurrence_by_id = {
            row["source_occurrence_id"]: row
            for row in document.repeat_occurrence_rows
        }
        for instruction_id in document.repeat_occurrence_ids:
            evidence_rows = evidence_by_instruction[instruction_id]
            if not evidence_rows or not all(
                _complete_redirection_evidence_member(evidence, instruction_id)
                for evidence in evidence_rows
            ):
                continue
            current_ids = [
                evidence["alias_anchor_occurrence_ids"][0]
                for evidence in evidence_rows
            ]
            destination_ids = [
                evidence["canonical_anchor_occurrence_ids"][0]
                for evidence in evidence_rows
            ]
            if len(set(current_ids)) != 1 or len(destination_ids) != len(
                set(destination_ids)
            ):
                continue
            current_id = current_ids[0]
            _require(
                current_id not in set(destination_ids),
                f"component cross-reference endpoint overlap: {instruction_id}",
            )
            source_occurrence = occurrence_by_id[instruction_id]
            instruction_projection = (
                [source_occurrence["matched_text"]],
                [source_occurrence["matched_utf8_sha256"]],
                [source_occurrence["page_number"]],
                [source_occurrence["utf8_byte_start"]],
                [source_occurrence["utf8_byte_end"]],
            )
            _require(
                all(
                    (
                        evidence["source_instruction_matched_texts"],
                        evidence["source_instruction_matched_utf8_sha256s"],
                        evidence["source_instruction_page_numbers"],
                        evidence["source_instruction_utf8_byte_starts"],
                        evidence["source_instruction_utf8_byte_ends"],
                    )
                    == instruction_projection
                    for evidence in evidence_rows
                ),
                f"component cross-reference instruction drift: {instruction_id}",
            )
            projection_by_endpoint: dict[str, tuple[Any, ...]] = {}
            for evidence in evidence_rows:
                endpoint_ids = [
                    *evidence["alias_anchor_occurrence_ids"],
                    *evidence["canonical_anchor_occurrence_ids"],
                ]
                for values in zip(
                    endpoint_ids,
                    *(evidence[key] for key in endpoint_projection_keys),
                    strict=True,
                ):
                    endpoint_id, *projection = values
                    prior = projection_by_endpoint.setdefault(
                        endpoint_id, tuple(projection)
                    )
                    _require(
                        prior == tuple(projection),
                        "component cross-reference endpoint projection drift: "
                        f"{endpoint_id}",
                    )
            handoff_statuses = {
                evidence["handoff_status"] for evidence in evidence_rows
            }
            _require(
                len(handoff_statuses) == 1,
                f"component cross-reference handoff drift: {instruction_id}",
            )
            evidence_ids = [
                evidence["local_evidence_id"] for evidence in evidence_rows
            ]
            _require(
                len(evidence_ids) == len(set(evidence_ids)),
                f"component cross-reference duplicate evidence: {instruction_id}",
            )
            redirection = redirection_by_instruction.get(instruction_id)
            compatible_alias_ids = [
                evidence["local_evidence_id"]
                for evidence in evidence_rows
                if _compatible_direct_proof(evidence)
            ]
            if redirection is not None:
                _require(
                    instruction_id
                    in EXCLUSIVE_DESTINATION_REDIRECTION_INSTRUCTION_IDS,
                    "component cross-reference unexpected R member: "
                    f"{instruction_id}",
                )
                _require(
                    redirection["source_local_evidence_ids"] == evidence_ids,
                    f"component cross-reference R ledger drift: {instruction_id}",
                )
                disposition = "admitted_exclusive_destination_redirection"
                semantic_finding = SEMANTIC_ALIAS_REDIRECTION_FINDING
                valid_alias_ids: list[str] = []
                redirection_id: str | None = redirection[
                    "in_domain_redirection_relation_disposition_id"
                ]
                status = "redirection_arm_member"
            elif instruction_id in COMPOSITE_IMPORT_INSTRUCTION_IDS:
                composite_decision = composite_decisions[instruction_id]
                valid_alias_ids = list(
                    composite_decision["approved_source_local_evidence_ids"]
                )
                _require(
                    set(valid_alias_ids) <= set(compatible_alias_ids)
                    and set(
                        composite_decision["stop_source_local_evidence_ids"]
                    )
                    == set(evidence_ids) - set(valid_alias_ids),
                    "composite semantic decision does not exact-cover source evidence",
                )
                if valid_alias_ids:
                    disposition = "existing_alias_arm"
                    semantic_finding = (
                        "exact_source_text_derives_pairwise_typed_instruction_"
                        "imports_without_composite_union"
                    )
                    status = (
                        "source_text_adjudicated_pairwise_alias_arm_member"
                    )
                else:
                    disposition = "disclosed_stop_no_redirection_semantics"
                    semantic_finding = (
                        COMPOSITE_IMPORT_STOP_FINDING_BY_INSTRUCTION[
                            instruction_id
                        ]
                    )
                    status = "source_text_adjudicated_disclosed_stop"
                redirection_id = None
            elif instruction_id in SEMANTIC_ALIAS_EQUIVALENCE_INSTRUCTION_IDS:
                _require(
                    compatible_alias_ids == evidence_ids,
                    "semantic alias member lacks structurally complete proof: "
                    f"{instruction_id}",
                )
                disposition = "existing_alias_arm"
                semantic_finding = (
                    "whitespace_only_continuation_composes_named_import"
                    if instruction_id
                    in CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS
                    else SEMANTIC_ALIAS_EQUIVALENCE_FINDING
                )
                valid_alias_ids = compatible_alias_ids
                redirection_id = None
                status = "source_text_adjudicated_alias_arm_member"
            elif instruction_id in SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION:
                disposition = "disclosed_stop_no_redirection_semantics"
                semantic_finding = SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION[
                    instruction_id
                ]
                valid_alias_ids = []
                redirection_id = None
                status = "source_text_adjudicated_disclosed_stop"
            else:
                raise BuildError(
                    "component cross-reference absent from semantic alias "
                    f"ledger: {instruction_id}"
                )
            fragment_fields = _fragment_ledger_fields(instruction_id)
            continuation_citations = [
                citation
                for evidence in evidence_rows
                if (
                    citation := _continuation_alias_citation(
                        document, evidence, instruction_id
                    )
                )
                is not None
            ]
            _require(
                len(continuation_citations)
                == int(
                    instruction_id
                    in CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS
                ),
                "continuation semantic citation coverage drift",
            )
            continuation_citation = (
                continuation_citations[0] if continuation_citations else None
            )
            row: dict[str, Any] = {
                "document_source_position": document.position,
                "source_document_id": document.source_document_id,
                "source_instruction_occurrence_id": instruction_id,
                "source_instruction_occurrence_kind": (
                    "repeat_or_alias_instruction"
                ),
                "source_instruction_matched_text": instruction_projection[0][
                    0
                ],
                "source_instruction_matched_utf8_sha256": (
                    instruction_projection[1][0]
                ),
                "source_instruction_page_number": instruction_projection[2][0],
                "source_instruction_utf8_byte_start": (
                    instruction_projection[3][0]
                ),
                "source_instruction_utf8_byte_end": instruction_projection[4][
                    0
                ],
                "source_local_evidence_ids": evidence_ids,
                "source_evidence_count": len(evidence_rows),
                "source_relations": [
                    evidence["relation"] for evidence in evidence_rows
                ],
                "source_handoff_statuses": [
                    evidence["handoff_status"] for evidence in evidence_rows
                ],
                "source_evidence_occurrence_id_arrays": [
                    evidence["evidence_occurrence_ids"]
                    for evidence in evidence_rows
                ],
                "source_alias_anchor_occurrence_id_arrays": [
                    evidence["alias_anchor_occurrence_ids"]
                    for evidence in evidence_rows
                ],
                "source_canonical_anchor_occurrence_id_arrays": [
                    evidence["canonical_anchor_occurrence_ids"]
                    for evidence in evidence_rows
                ],
                **{
                    output_key: [
                        evidence[source_key] for evidence in evidence_rows
                    ]
                    for output_key, source_key in zip(
                        nested_projection_keys,
                        endpoint_projection_keys,
                        strict=True,
                    )
                },
                "source_defect_flag_rows": [
                    evidence["defect_flags"] for evidence in evidence_rows
                ],
                "source_unresolved_target_references": [
                    evidence["unresolved_target_reference"]
                    for evidence in evidence_rows
                ],
                "current_location_occurrence_id": current_id,
                "destination_occurrence_ids": destination_ids,
                "structural_candidate_satisfied": True,
                "pilot_document_member": document.position in PILOT_POSITIONS,
                "semantic_alias_adjudication_round": 5,
                "semantic_alias_ledger_member": True,
                "semantic_alias_finding": semantic_finding,
                "named_instruction_import_or_occurrence_equivalence_proved": (
                    disposition == "existing_alias_arm"
                ),
                "occurrence_equivalence_proved": (
                    disposition == "existing_alias_arm"
                    and instruction_id not in COMPOSITE_IMPORT_INSTRUCTION_IDS
                ),
                "pairwise_decomposition_required": (
                    instruction_id in COMPOSITE_IMPORT_INSTRUCTION_IDS
                ),
                "approved_pair_count": (
                    composite_decisions[instruction_id]["approved_pair_count"]
                    if instruction_id in COMPOSITE_IMPORT_INSTRUCTION_IDS
                    else len(valid_alias_ids)
                ),
                "rejected_source_local_evidence_ids": [
                    evidence_id
                    for evidence_id in evidence_ids
                    if (
                        disposition
                        == "disclosed_stop_no_redirection_semantics"
                        or (
                            disposition == "existing_alias_arm"
                            and evidence_id not in set(valid_alias_ids)
                        )
                    )
                ],
                "continuation_composition_citation": continuation_citation,
                **fragment_fields,
                "semantic_redirection_ledger_member": (
                    disposition == "admitted_exclusive_destination_redirection"
                ),
                "semantic_redirection_finding": (
                    semantic_finding
                    if disposition
                    == "admitted_exclusive_destination_redirection"
                    else None
                ),
                "valid_alias_arm_evidence_ids": valid_alias_ids,
                "in_domain_redirection_relation_disposition_id": (
                    redirection_id
                ),
                "repeat_coverage_disposition": disposition,
                "status": status,
            }
            row["semantic_alias_adjudication_id"] = _row_id(
                "a12-semantic-alias-adjudication:",
                [
                    row["source_document_id"],
                    instruction_id,
                    evidence_ids,
                    row["source_instruction_matched_text"],
                    row["source_instruction_matched_utf8_sha256"],
                    row["source_instruction_page_number"],
                    row["source_instruction_utf8_byte_start"],
                    row["source_instruction_utf8_byte_end"],
                    row["source_endpoint_matched_text_arrays"],
                    row["source_endpoint_matched_utf8_sha256_arrays"],
                    row["source_endpoint_page_number_arrays"],
                    row["source_endpoint_utf8_byte_start_arrays"],
                    row["source_endpoint_utf8_byte_end_arrays"],
                    disposition,
                    semantic_finding,
                    row[
                        "named_instruction_import_or_occurrence_equivalence_proved"
                    ],
                    row["occurrence_equivalence_proved"],
                    row["pairwise_decomposition_required"],
                    row["approved_pair_count"],
                    row["rejected_source_local_evidence_ids"],
                    continuation_citation,
                    fragment_fields,
                ],
            )
            row["in_domain_component_cross_reference_sweep_id"] = _row_id(
                "a12-in-domain-component-cross-reference-sweep:",
                [
                    row["source_document_id"],
                    instruction_id,
                    evidence_ids,
                    row["source_evidence_occurrence_id_arrays"],
                    row["source_alias_anchor_occurrence_id_arrays"],
                    row["source_canonical_anchor_occurrence_id_arrays"],
                    disposition,
                    row["semantic_alias_adjudication_id"],
                ],
            )
            rows.append(row)
    selected_repeat_ids = {
        instruction_id
        for document in documents
        for instruction_id in document.repeat_occurrence_ids
    }
    expected_ids = (
        SEMANTIC_ALIAS_ADJUDICATED_INSTRUCTION_IDS & selected_repeat_ids
    )
    actual_ids = {row["source_instruction_occurrence_id"] for row in rows}
    _require(
        actual_ids == expected_ids and len(actual_ids) == len(rows),
        "semantic alias ledger does not exact-cover structural sweep",
    )
    return rows


def _component_cross_reference_sweep_counts(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Return instruction and evidence-edge counts for the exact partition."""
    disposition_names = {
        "alias": "existing_alias_arm",
        "redirection": "admitted_exclusive_destination_redirection",
        "stop": "disclosed_stop_no_redirection_semantics",
    }
    result = {
        "instruction_count": len(rows),
        "edge_count": sum(row["source_evidence_count"] for row in rows),
        **{
            f"{name}_instruction_count": sum(
                row["repeat_coverage_disposition"] == disposition
                for row in rows
            )
            for name, disposition in disposition_names.items()
        },
        "alias_edge_count": sum(
            len(row["valid_alias_arm_evidence_ids"]) for row in rows
        ),
        "alias_pair_count": sum(
            row["approved_pair_count"]
            for row in rows
            if row["repeat_coverage_disposition"] == "existing_alias_arm"
        ),
        "redirection_edge_count": sum(
            row["source_evidence_count"]
            for row in rows
            if row["repeat_coverage_disposition"]
            == "admitted_exclusive_destination_redirection"
        ),
        "stop_edge_count": sum(
            len(row["rejected_source_local_evidence_ids"]) for row in rows
        ),
    }
    _require(
        result["alias_edge_count"]
        + result["redirection_edge_count"]
        + result["stop_edge_count"]
        == result["edge_count"],
        "component cross-reference source-evidence partition drift",
    )
    return result


def _semantic_alias_outcome_code(row: Mapping[str, Any]) -> str:
    return {
        "existing_alias_arm": "A",
        "admitted_exclusive_destination_redirection": "R",
        "disclosed_stop_no_redirection_semantics": "S",
    }[row["repeat_coverage_disposition"]]


def _exclusive_placement_shape_kind(text: str) -> str | None:
    normalized = "".join(
        character for character in text.casefold() if character.isalnum()
    )
    business_owner_pay = (
        "paythemselves" in normalized
        and "notbelistedhere" in normalized
        and any(
            value in normalized
            for value in (
                "shouldberecorded",
                "shouldhavebeenrecorded",
                "shouldbetakencareof",
            )
        )
    )
    farm_primary_income = any(
        value in normalized
        for value in (
            "incomeshouldcome",
            "incomeshouldgo",
            "incomeshouldbelisted",
        )
    ) and any(
        value in normalized
        for value in (
            "notbeduplicatedhere",
            "notbeduplicatedher",
            "notberepeatedhere",
        )
    )
    labor_income_g78 = "shouldbeincludedatg78nothere" in normalized
    matches = (
        business_owner_pay,
        farm_primary_income,
        labor_income_g78,
    )
    if sum(matches) != 1:
        return None
    return (
        "business_owner_pay_exclusive_placement"
        if business_owner_pay
        else (
            "primary_farm_income_exclusive_placement"
            if farm_primary_income
            else "labor_income_g78_exclusive_placement"
        )
    )


def _exclusive_destination_redirection_lineage_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    """Exact-walk every source-text member of the placement shape."""
    disposition_by_instruction = {
        row["source_instruction_occurrence_ids"][0]: row
        for row in _in_domain_redirection_rows(documents)
    }
    aggregate_by_instruction = {
        row["source_instruction_occurrence_ids"][0]: row
        for row in _noncatalog_aggregate_relation_rows(documents)
    }
    rows: list[dict[str, Any]] = []
    for document in documents:
        evidence_by_instruction: defaultdict[str, list[dict[str, Any]]] = (
            defaultdict(list)
        )
        for evidence in document.evidence_rows:
            for instruction_id in evidence[
                "source_instruction_occurrence_ids"
            ]:
                evidence_by_instruction[instruction_id].append(evidence)
        for occurrence in document.repeat_occurrence_rows:
            shape_kind = _exclusive_placement_shape_kind(
                occurrence["matched_text"]
            )
            if shape_kind is None:
                continue
            instruction_id = occurrence["source_occurrence_id"]
            evidence_rows = evidence_by_instruction[instruction_id]
            disposition = disposition_by_instruction.get(instruction_id)
            eligible = disposition is not None
            aggregate_disposition = aggregate_by_instruction.get(
                instruction_id
            )
            aggregate_covered = aggregate_disposition is not None
            mixed_aggregate_component = (
                not eligible
                and not aggregate_covered
                and any(
                    "aggregate" in evidence["endpoint_raw_node_domains"]
                    and any(
                        domain != "aggregate"
                        for domain in evidence["endpoint_raw_node_domains"]
                    )
                    for evidence in evidence_rows
                )
            )
            evidence_ids = [
                evidence["local_evidence_id"] for evidence in evidence_rows
            ]
            row_id = _row_id(
                "a12-exclusive-destination-redirection-lineage:",
                [
                    document.source_document_id,
                    instruction_id,
                    occurrence["matched_text"],
                    evidence_ids,
                ],
            )
            rows.append(
                {
                    "exclusive_destination_redirection_lineage_id": row_id,
                    "document_source_position": document.position,
                    "source_document_id": document.source_document_id,
                    "source_instruction_occurrence_id": instruction_id,
                    "source_instruction_matched_text": occurrence[
                        "matched_text"
                    ],
                    "source_instruction_matched_utf8_sha256": occurrence[
                        "matched_utf8_sha256"
                    ],
                    "source_instruction_page_number": occurrence[
                        "page_number"
                    ],
                    "source_instruction_utf8_byte_start": occurrence[
                        "utf8_byte_start"
                    ],
                    "source_instruction_utf8_byte_end": occurrence[
                        "utf8_byte_end"
                    ],
                    "source_text_shape_kind": shape_kind,
                    "source_local_evidence_ids": evidence_ids,
                    "source_relations": [
                        evidence["relation"] for evidence in evidence_rows
                    ],
                    "source_handoff_statuses": [
                        evidence["handoff_status"]
                        for evidence in evidence_rows
                    ],
                    "source_alias_anchor_occurrence_id_arrays": [
                        evidence["alias_anchor_occurrence_ids"]
                        for evidence in evidence_rows
                    ],
                    "source_canonical_anchor_occurrence_id_arrays": [
                        evidence["canonical_anchor_occurrence_ids"]
                        for evidence in evidence_rows
                    ],
                    "source_endpoint_occurrence_kind_arrays": [
                        evidence["endpoint_occurrence_kinds"]
                        for evidence in evidence_rows
                    ],
                    "source_endpoint_raw_node_domain_arrays": [
                        evidence["endpoint_raw_node_domains"]
                        for evidence in evidence_rows
                    ],
                    "source_endpoint_classification_arrays": [
                        evidence["endpoint_classifications"]
                        for evidence in evidence_rows
                    ],
                    "source_endpoint_printed_identifier_arrays": [
                        evidence["endpoint_printed_identifiers"]
                        for evidence in evidence_rows
                    ],
                    "source_unresolved_target_references": [
                        evidence["unresolved_target_reference"]
                        for evidence in evidence_rows
                    ],
                    "in_domain_redirection_arm_eligible": eligible,
                    "in_domain_redirection_relation_disposition_id": (
                        disposition[
                            "in_domain_redirection_relation_disposition_id"
                        ]
                        if eligible
                        else None
                    ),
                    "existing_aggregate_relation_disposition_id": (
                        aggregate_disposition[
                            "noncatalog_aggregate_relation_disposition_id"
                        ]
                        if aggregate_covered
                        else None
                    ),
                    "lineage_disposition": (
                        "admitted_exclusive_destination_redirection"
                        if eligible
                        else (
                            "covered_by_existing_aggregate_nonalias_subkind"
                            if aggregate_covered
                            else (
                                "disclosed_stop_mixed_aggregate_component_"
                                "proof"
                                if mixed_aggregate_component
                                else "disclosed_stop_incomplete_local_proof"
                            )
                        )
                    ),
                    "status": (
                        "redirection_arm_member"
                        if eligible
                        else (
                            "existing_aggregate_arm_member"
                            if aggregate_covered
                            else "fail_closed_lineage_near_shape"
                        )
                    ),
                }
            )
    return rows


def _noncatalog_aggregate_relation_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for document in documents:
        for evidence in document.evidence_rows:
            if not _honest_noncatalog_aggregate_relation(evidence):
                continue
            instructions = evidence["source_instruction_occurrence_ids"]
            aliases = evidence["alias_anchor_occurrence_ids"]
            canonicals = evidence["canonical_anchor_occurrence_ids"]
            disposition_id = _row_id(
                "a12-noncatalog-aggregate-relation-disposition:",
                [
                    document.source_document_id,
                    evidence["local_evidence_id"],
                    instructions,
                    evidence["relation"],
                    evidence["handoff_status"],
                    aliases,
                    canonicals,
                    evidence["evidence_occurrence_ids"],
                    evidence["endpoint_occurrence_kinds"],
                    evidence["endpoint_raw_node_domains"],
                    evidence["endpoint_classifications"],
                    evidence["source_instruction_matched_texts"],
                    evidence["source_instruction_matched_utf8_sha256s"],
                    evidence["source_instruction_page_numbers"],
                    evidence["source_instruction_utf8_byte_starts"],
                    evidence["source_instruction_utf8_byte_ends"],
                    evidence["endpoint_matched_texts"],
                    evidence["endpoint_matched_utf8_sha256s"],
                    evidence["endpoint_page_numbers"],
                    evidence["endpoint_utf8_byte_starts"],
                    evidence["endpoint_utf8_byte_ends"],
                ],
            )
            rows.append(
                {
                    "noncatalog_aggregate_relation_disposition_id": (
                        disposition_id
                    ),
                    "document_source_position": document.position,
                    "source_document_id": document.source_document_id,
                    "source_local_evidence_id": evidence["local_evidence_id"],
                    "source_instruction_occurrence_ids": instructions,
                    "source_instruction_occurrence_kinds": evidence[
                        "source_instruction_occurrence_kinds"
                    ],
                    "source_instruction_matched_texts": evidence[
                        "source_instruction_matched_texts"
                    ],
                    "source_instruction_matched_utf8_sha256s": evidence[
                        "source_instruction_matched_utf8_sha256s"
                    ],
                    "source_instruction_page_numbers": evidence[
                        "source_instruction_page_numbers"
                    ],
                    "source_instruction_utf8_byte_starts": evidence[
                        "source_instruction_utf8_byte_starts"
                    ],
                    "source_instruction_utf8_byte_ends": evidence[
                        "source_instruction_utf8_byte_ends"
                    ],
                    "relation": evidence["relation"],
                    "handoff_status": evidence["handoff_status"],
                    "evidence_occurrence_ids": evidence[
                        "evidence_occurrence_ids"
                    ],
                    "source_alias_anchor_occurrence_ids": aliases,
                    "source_canonical_anchor_occurrence_ids": canonicals,
                    "endpoint_occurrence_kinds": evidence[
                        "endpoint_occurrence_kinds"
                    ],
                    "endpoint_raw_node_domains": evidence[
                        "endpoint_raw_node_domains"
                    ],
                    "endpoint_classifications": evidence[
                        "endpoint_classifications"
                    ],
                    "endpoint_matched_texts": evidence[
                        "endpoint_matched_texts"
                    ],
                    "endpoint_matched_utf8_sha256s": evidence[
                        "endpoint_matched_utf8_sha256s"
                    ],
                    "endpoint_page_numbers": evidence["endpoint_page_numbers"],
                    "endpoint_utf8_byte_starts": evidence[
                        "endpoint_utf8_byte_starts"
                    ],
                    "endpoint_utf8_byte_ends": evidence[
                        "endpoint_utf8_byte_ends"
                    ],
                    "aggregate_relation_disposition": (
                        "noncatalog_aggregate_or_repeated_instance_"
                        "relation_no_alias"
                    ),
                    "alias_admitted": False,
                    "occurrence_equivalence_claimed": False,
                    "universal_repeat_coverage_arm_satisfied": True,
                    "status": "aggregate_relation_nonauthority_disposition",
                }
            )
    return rows


def _proof_adjudication_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    semantic_ledger = (
        AGGREGATE_RELATION_LAW_GAP_EVIDENCE_IDS
        | REDIRECTION_LAW_GAP_EVIDENCE_IDS
        | PREDECESSOR_SEAL_DEFECT_EVIDENCE_IDS
    )
    _require(
        not AGGREGATE_RELATION_LAW_GAP_EVIDENCE_IDS
        & REDIRECTION_LAW_GAP_EVIDENCE_IDS
        and not AGGREGATE_RELATION_LAW_GAP_EVIDENCE_IDS
        & PREDECESSOR_SEAL_DEFECT_EVIDENCE_IDS
        and not REDIRECTION_LAW_GAP_EVIDENCE_IDS
        & PREDECESSOR_SEAL_DEFECT_EVIDENCE_IDS,
        "round-three semantic ledger overlaps",
    )
    observed_candidates = {
        evidence["local_evidence_id"]
        for document in documents
        for evidence in document.evidence_rows
        if evidence["alias_anchor_occurrence_ids"]
        and evidence["canonical_anchor_occurrence_ids"]
        and any(evidence["defect_flags"].values())
    }
    _require(
        observed_candidates == semantic_ledger,
        "round-three semantic ledger does not exact-cover proof candidates",
    )
    rows: list[dict[str, Any]] = []
    for document in documents:
        for evidence in document.evidence_rows:
            if not evidence["alias_anchor_occurrence_ids"]:
                continue
            if not evidence["canonical_anchor_occurrence_ids"]:
                continue
            flags = evidence["defect_flags"]
            if not any(flags.values()):
                continue
            evidence_id = evidence["local_evidence_id"]
            aggregate_eligible = (
                evidence_id in AGGREGATE_RELATION_LAW_GAP_EVIDENCE_IDS
            )
            redirection_eligible = (
                evidence_id in REDIRECTION_LAW_GAP_EVIDENCE_IDS
            )
            seal_defect = evidence_id in PREDECESSOR_SEAL_DEFECT_EVIDENCE_IDS
            _require(
                aggregate_eligible
                == _honest_noncatalog_aggregate_relation(evidence),
                f"semantic aggregate adjudication drift: {evidence_id}",
            )
            _require(
                redirection_eligible
                == _semantic_redirection_evidence_member(evidence),
                f"semantic redirection adjudication drift: {evidence_id}",
            )
            _require(
                sum((aggregate_eligible, redirection_eligible, seal_defect))
                == 1,
                f"semantic adjudication is not exact: {evidence_id}",
            )
            in_domain_eligible = aggregate_eligible or redirection_eligible
            if aggregate_eligible:
                disposition = (
                    "predecessor_law_gap_repaired_by_noncatalog_aggregate_"
                    "relation_arm"
                )
                law_gap_admitted = True
                required_action = (
                    "ratify_extended_in_domain_nonalias_law_before_tier_2"
                )
                rationale = (
                    "authenticated_aggregate_relation_is_honest_nonalias_"
                    "law_gap"
                )
                semantic_finding = (
                    "cited_instruction_and_aggregate_only_endpoints_"
                    "authenticate_a_nonalias_aggregate_relation"
                )
                relation_subkind: str | None = AGGREGATE_RELATION_SUBKIND
                status = "blocked_pending_extended_repeat_law_ratification"
            elif redirection_eligible:
                disposition = (
                    "predecessor_law_gap_repaired_by_in_domain_redirection_"
                    "relation_arm"
                )
                law_gap_admitted = True
                required_action = (
                    "ratify_extended_in_domain_nonalias_law_before_tier_2"
                )
                rationale = (
                    "authenticated_named_destination_and_not_here_"
                    "instruction_is_honest_nonalias_redirection_law_gap"
                )
                semantic_finding = (
                    "cited_text_names_G78_as_the_destination_and_excludes_"
                    "the_current_G83_location"
                )
                relation_subkind = REDIRECTION_RELATION_SUBKIND
                status = "blocked_pending_extended_repeat_law_ratification"
            else:
                disposition = "predecessor_seal_defect"
                law_gap_admitted = False
                required_action = (
                    "readjudicate_source_row_and_reseal_before_tier_2"
                )
                rationale = (
                    "incompatible_endpoint_claim_cannot_be_admitted_as_"
                    "alias_law_reseal_required"
                )
                relation_subkind = None
                if evidence_id in {
                    "rq-local-repeat-alias-evidence:c7020c1c35780475871c3d0ddce0767b1fe22b6f6c45c79fbd03093519ffc716",
                    "rq-local-repeat-alias-evidence:78c2d51532910f9dbebaac790485bb20e2a0d907e632f4d32c327c185d52a34c",
                    "rq-local-repeat-alias-evidence:b2ff04405ce6c20fb6848441dd5fc249ac55b99c6ce21a60ff1ef331b42d8a19",
                    "rq-local-repeat-alias-evidence:e4b4c44f443929ce8facfa51ce2e318e201490d259b01e507d4dded083e8fba2",
                    "rq-local-repeat-alias-evidence:6c17ebd0a0c97a5b46fef9ff2c5326fe45acf482647c6a2fd0d3bf542be17b22",
                    "rq-local-repeat-alias-evidence:f44ce5328602c75bcde9b50b2de94d68582a6fe7080eea03b1de32e622171a22",
                }:
                    semantic_finding = (
                        "cited_repeat_text_does_not_authenticate_the_"
                        "heterogeneous_page_wide_endpoint_projection"
                    )
                elif evidence_id in {
                    "rq-local-repeat-evidence:c9b24cb9e34a7050a567093ee0f0500df3e221dd2afa9adfdaba02010fd31509",
                    "rq-local-repeat-evidence:6ce1ef4653dfa56a49ff6baf30052132630c1ed47dfb246dcf38c1e63a24f83f",
                    "rq-local-repeat-evidence:525a55100f92a4f6f05e156d9d784029ea29126e2c5374195545513375b36e8c",
                    "rq-local-repeat-evidence:a06a1898968a9dc0d44b34bbd5ca9efc9bb856a56bde685815ff6621d1f82b39",
                }:
                    semantic_finding = (
                        "cited_instruction_is_an_incomplete_clause_and_"
                        "cannot_authenticate_a_complete_redirection"
                    )
                elif evidence_id in {
                    "rq-local-repeat-evidence:db438aefe04bee804bdc15f683dba9f90d0963871a6242217b18e09bdbed01c4",
                    "rq-local-repeat-evidence:7e1395227e1f81c5fe864d17e319e56b724424eab5163df68109dd85f81ce5c7",
                    "rq-local-repeat-evidence:e1e5e2a1b422ae3334fd657b68dbd1922e56e36165b4913c8d309896ac72d6d4",
                    "rq-local-repeat-evidence:c207d07c88d2bef6b99a038d94a1f870ac038072de4c005241ab9ce3f79439c3",
                    "rq-local-repeat-evidence:fd7a9eebc0d44fe9cf4ba8795b478b2d6a933b8aa42dd45d52cb561328e86ada",
                }:
                    semantic_finding = (
                        "cited_income_list_is_shared_with_an_independent_"
                        "alias_proof_and_does_not_authenticate_this_pairing"
                    )
                elif evidence_id == (
                    "rq-local-repeat-alias-evidence:b8ea2ca5e2b198e2c4f9ec8ef9608a68b53b8c7a0f76435f4c2ca0db3f57a456"
                ):
                    semantic_finding = (
                        "cited_same_occupation_text_asserts_semantics_but_"
                        "the_job_context_endpoint_crossing_requires_reseal"
                    )
                elif evidence_id == (
                    "rq-local-repeat-evidence:bb6ce7690468d1ef2e0d4a22bfa831bf9b81f7824db8a9dd59e06df44434c877"
                ):
                    semantic_finding = (
                        "cited_see_instructions_text_is_mispaired_to_a_"
                        "context_remuneration_endpoint_claim"
                    )
                else:
                    semantic_finding = (
                        "cited_instruction_does_not_authenticate_the_mixed_"
                        "or_misbound_endpoint_projection"
                    )
                status = "blocked_predecessor_row"
            row_id = _row_id(
                "a12-predecessor-local-proof-adjudication:",
                [
                    document.source_document_id,
                    evidence["local_evidence_id"],
                    flags,
                    disposition,
                ],
            )
            rows.append(
                {
                    "predecessor_adjudication_id": row_id,
                    "document_source_position": document.position,
                    "source_document_id": document.source_document_id,
                    "source_local_evidence_id": evidence["local_evidence_id"],
                    "relation": evidence["relation"],
                    "source_instruction_occurrence_ids": evidence[
                        "source_instruction_occurrence_ids"
                    ],
                    "source_instruction_matched_texts": evidence[
                        "source_instruction_matched_texts"
                    ],
                    "source_instruction_matched_utf8_sha256s": evidence[
                        "source_instruction_matched_utf8_sha256s"
                    ],
                    "source_instruction_page_numbers": evidence[
                        "source_instruction_page_numbers"
                    ],
                    "source_instruction_utf8_byte_starts": evidence[
                        "source_instruction_utf8_byte_starts"
                    ],
                    "source_instruction_utf8_byte_ends": evidence[
                        "source_instruction_utf8_byte_ends"
                    ],
                    "alias_anchor_occurrence_ids": evidence[
                        "alias_anchor_occurrence_ids"
                    ],
                    "canonical_anchor_occurrence_ids": evidence[
                        "canonical_anchor_occurrence_ids"
                    ],
                    "evidence_occurrence_ids": evidence[
                        "evidence_occurrence_ids"
                    ],
                    "endpoint_occurrence_kinds": evidence[
                        "endpoint_occurrence_kinds"
                    ],
                    "endpoint_raw_node_domains": evidence[
                        "endpoint_raw_node_domains"
                    ],
                    "endpoint_classifications": evidence[
                        "endpoint_classifications"
                    ],
                    "endpoint_printed_identifiers": evidence[
                        "endpoint_printed_identifiers"
                    ],
                    "endpoint_matched_texts": evidence[
                        "endpoint_matched_texts"
                    ],
                    "endpoint_matched_utf8_sha256s": evidence[
                        "endpoint_matched_utf8_sha256s"
                    ],
                    "endpoint_page_numbers": evidence["endpoint_page_numbers"],
                    "endpoint_utf8_byte_starts": evidence[
                        "endpoint_utf8_byte_starts"
                    ],
                    "endpoint_utf8_byte_ends": evidence[
                        "endpoint_utf8_byte_ends"
                    ],
                    "defect_flags": flags,
                    "semantic_adjudication_round": 3,
                    "source_text_citation_status": (
                        "exact_text_digest_page_and_utf8_span_cited"
                    ),
                    "in_domain_nonalias_relation_arm_eligible": (
                        in_domain_eligible
                    ),
                    "in_domain_nonalias_relation_subkind": relation_subkind,
                    "disposition": disposition,
                    "law_gap_admitted": law_gap_admitted,
                    "alias_admitted": False,
                    "required_action": required_action,
                    "adjudicative_rationale": rationale,
                    "row_specific_semantic_finding": semantic_finding,
                    "status": status,
                }
            )
    return rows


def _doc036_defect_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    document = next(value for value in documents if value.position == 36)
    rows: list[dict[str, Any]] = []
    for anchor in document.anchor_rows:
        if anchor["classification"] not in AGGREGATE_CLASSIFICATIONS:
            continue
        if anchor["node_domain"] != "component_slot":
            continue
        _require(
            anchor["occurrence_kind"] in AGGREGATE_OCCURRENCE_KINDS,
            "doc036 aggregate classification lacks aggregate occurrence",
        )
        row_id = _row_id(
            "a12-predecessor-doc036-aggregate-adjudication:",
            [
                document.source_document_id,
                anchor["local_anchor_classification_id"],
                anchor["source_occurrence_id"],
                anchor["classification"],
                "predecessor_seal_defect",
            ],
        )
        rows.append(
            {
                "predecessor_adjudication_id": row_id,
                "document_source_position": document.position,
                "source_document_id": document.source_document_id,
                "source_classification_id": anchor[
                    "local_anchor_classification_id"
                ],
                "source_occurrence_id": anchor["source_occurrence_id"],
                "source_occurrence_matched_text": anchor[
                    "occurrence_matched_text"
                ],
                "source_occurrence_matched_utf8_sha256": anchor[
                    "occurrence_matched_utf8_sha256"
                ],
                "source_occurrence_page_number": anchor[
                    "occurrence_page_number"
                ],
                "source_occurrence_utf8_byte_start": anchor[
                    "occurrence_utf8_byte_start"
                ],
                "source_occurrence_utf8_byte_end": anchor[
                    "occurrence_utf8_byte_end"
                ],
                "source_classification": anchor["classification"],
                "occurrence_kind": anchor["occurrence_kind"],
                "serialized_node_domain": anchor["node_domain"],
                "correct_node_domain": "aggregate",
                "disposition": "predecessor_seal_defect",
                "law_gap_admitted": False,
                "component_slot_admitted": False,
                "semantic_adjudication_round": 3,
                "source_text_citation_status": (
                    "exact_text_digest_page_and_utf8_span_cited"
                ),
                "required_action": (
                    "reseal_document_036_with_aggregate_anchor_domain"
                ),
                "adjudicative_rationale": (
                    "aggregate_occurrence_kind_controls_node_domain_"
                    "reseal_required"
                ),
                "row_specific_semantic_finding": (
                    "cited_anchor_text_denotes_an_aggregate_but_the_"
                    "predecessor_serialized_component_slot"
                ),
                "status": "blocked_predecessor_row",
            }
        )
    return rows


def _compatible_direct_proof(evidence: Mapping[str, Any]) -> bool:
    aliases = evidence["alias_anchor_occurrence_ids"]
    canonicals = evidence["canonical_anchor_occurrence_ids"]
    evidence_ids = evidence["evidence_occurrence_ids"]
    instructions = evidence["source_instruction_occurrence_ids"]
    endpoints = [*aliases, *canonicals]
    required_evidence = {*endpoints, *instructions}
    return bool(
        aliases
        and canonicals
        and len(endpoints) == len(set(endpoints))
        and not set(aliases) & set(canonicals)
        and evidence_ids
        and len(evidence_ids) == len(set(evidence_ids))
        and required_evidence <= set(evidence_ids)
        and evidence["evidence_arrays_unique_disjoint"]
        and evidence["evidence_arrays_source_ordered"]
        and evidence["handoff_status"] in COMPLETE_LOCAL_EVIDENCE_STATUSES
        and not any(evidence["defect_flags"].values())
    )


@dataclass(frozen=True)
class RepeatArmConstruction:
    """Construction-time partition and the sole admission set for A."""

    repeat_instruction_ids: frozenset[str]
    alias_instruction_ids: frozenset[str]
    alias_evidence_ids: frozenset[str]
    alias_pair_rows: tuple[Mapping[str, Any], ...]
    closure_alias_pair_rows: tuple[Mapping[str, Any], ...]
    semantic_adjudication_rows: tuple[Mapping[str, Any], ...]
    outside_instruction_ids: frozenset[str]
    aggregate_instruction_ids: frozenset[str]
    redirection_instruction_ids: frozenset[str]
    incompatible_instruction_ids: frozenset[str]
    structural_stop_instruction_ids: frozenset[str]
    excluded_nonalias_evidence_ids: frozenset[str]


def _repeat_arm_construction(
    documents: Sequence[NormalizedDocument],
    *,
    outside_rows: Sequence[Mapping[str, Any]] | None = None,
    aggregate_rows: Sequence[Mapping[str, Any]] | None = None,
    redirection_rows: Sequence[Mapping[str, Any]] | None = None,
    structural_rows: Sequence[Mapping[str, Any]] | None = None,
    semantic_rows: Sequence[Mapping[str, Any]] | None = None,
    citation_documents: Sequence[NormalizedDocument] | None = None,
) -> RepeatArmConstruction:
    """Select disjoint repeat arms through the sole semantic gate to A."""

    def exact_source_rows(
        supplied: Sequence[Mapping[str, Any]] | None,
        derived: list[dict[str, Any]],
        label: str,
    ) -> list[dict[str, Any]]:
        if supplied is not None:
            _require(
                canonical_bytes(list(supplied)) == canonical_bytes(derived),
                f"{label} injection differs from source-derived rows",
            )
        return derived

    # Optional row arguments are build-time caches, never authorities.  Each
    # one must byte-match a fresh derivation from the pinned documents before
    # the semantic ledger can admit any evidence to A.
    resolved_outside_rows = exact_source_rows(
        outside_rows,
        _outside_repeat_rows(documents),
        "outside-repeat row",
    )
    resolved_aggregate_rows = exact_source_rows(
        aggregate_rows,
        _noncatalog_aggregate_relation_rows(documents),
        "aggregate-relation row",
    )
    resolved_redirection_rows = exact_source_rows(
        redirection_rows,
        _in_domain_redirection_rows(documents),
        "redirection row",
    )
    resolved_structural_rows = exact_source_rows(
        structural_rows,
        _in_domain_component_cross_reference_sweep_rows(documents),
        "structural-filter row",
    )
    derived_semantic_rows, _semantic_input_identities = (
        _alias_evidence_semantic_adjudication_rows(
            documents,
            outside_rows=resolved_outside_rows,
            aggregate_rows=resolved_aggregate_rows,
            redirection_rows=resolved_redirection_rows,
            structural_rows=resolved_structural_rows,
            citation_documents=citation_documents,
        )
    )
    resolved_semantic_rows = exact_source_rows(
        semantic_rows,
        derived_semantic_rows,
        "semantic-adjudication row",
    )

    repeat_instruction_ids = {
        instruction_id
        for document in documents
        for instruction_id in document.repeat_occurrence_ids
    }
    outside_instruction_ids = {
        row["source_instruction_occurrence_id"]
        for row in resolved_outside_rows
    }
    aggregate_instruction_ids = {
        instruction_id
        for row in resolved_aggregate_rows
        for instruction_id in row["source_instruction_occurrence_ids"]
    }
    redirection_instruction_ids = {
        instruction_id
        for row in resolved_redirection_rows
        for instruction_id in row["source_instruction_occurrence_ids"]
    }
    outside_evidence_ids = {
        row["source_local_evidence_id"] for row in resolved_outside_rows
    }
    aggregate_evidence_ids = {
        row["source_local_evidence_id"] for row in resolved_aggregate_rows
    }
    redirection_evidence_ids = {
        evidence_id
        for row in resolved_redirection_rows
        for evidence_id in row["source_local_evidence_ids"]
    }

    structural_alias_evidence_ids: set[str] = set()
    structural_evidence_ids: set[str] = set()
    structural_stop_instruction_ids: set[str] = set()
    for row in resolved_structural_rows:
        evidence_ids = set(row["source_local_evidence_ids"])
        structural_evidence_ids.update(evidence_ids)
        disposition = row["repeat_coverage_disposition"]
        if disposition == "existing_alias_arm":
            _require(
                set(row["valid_alias_arm_evidence_ids"]) <= evidence_ids,
                "structural alias row admits evidence outside its group",
            )
            structural_alias_evidence_ids.update(
                row["valid_alias_arm_evidence_ids"]
            )
        elif disposition == "disclosed_stop_no_redirection_semantics":
            structural_stop_instruction_ids.add(
                row["source_instruction_occurrence_id"]
            )

    semantic_candidate_instruction_ids: set[str] = set()
    admitted_alias_evidence_ids: set[str] = set()
    alias_instruction_ids: set[str] = set()
    semantic_stop_evidence_ids: set[str] = set()
    alias_pair_rows: list[Mapping[str, Any]] = []
    for row in resolved_semantic_rows:
        evidence_id = row["source_local_evidence_id"]
        instruction_ids = set(row["source_instruction_occurrence_ids"])
        semantic_candidate_instruction_ids.update(instruction_ids)
        approved_pairs = row["approved_pair_rows"]
        if approved_pairs:
            admitted_alias_evidence_ids.add(evidence_id)
            alias_instruction_ids.update(instruction_ids)
            alias_pair_rows.extend(approved_pairs)
        else:
            semantic_stop_evidence_ids.add(evidence_id)
    closure_alias_pair_rows = [
        row for row in alias_pair_rows if row["class_closure_eligible"]
    ]
    semantic_fully_stopped_instruction_ids = (
        semantic_candidate_instruction_ids - alias_instruction_ids
    )

    excluded_nonalias_evidence_ids = (
        outside_evidence_ids
        | aggregate_evidence_ids
        | redirection_evidence_ids
        | (structural_evidence_ids - structural_alias_evidence_ids)
        | semantic_stop_evidence_ids
    )
    incompatible_instruction_ids: set[str] = set(
        structural_stop_instruction_ids
        | semantic_fully_stopped_instruction_ids
    )
    for document in documents:
        for evidence in document.evidence_rows:
            instructions = set(evidence["source_instruction_occurrence_ids"])
            has_directional_endpoints = bool(
                evidence["alias_anchor_occurrence_ids"]
                and evidence["canonical_anchor_occurrence_ids"]
            )
            if (
                has_directional_endpoints
                and not _compatible_direct_proof(evidence)
                and not _honest_noncatalog_aggregate_relation(evidence)
            ):
                incompatible_instruction_ids.update(
                    instructions - redirection_instruction_ids
                )

    alias_instruction_ids &= repeat_instruction_ids
    incompatible_instruction_ids &= repeat_instruction_ids
    outside_instruction_ids &= repeat_instruction_ids
    aggregate_instruction_ids &= repeat_instruction_ids
    redirection_instruction_ids &= repeat_instruction_ids
    admitted_arms = (
        alias_instruction_ids,
        outside_instruction_ids,
        aggregate_instruction_ids,
        redirection_instruction_ids,
    )
    arm_membership_count = Counter(
        instruction_id for arm in admitted_arms for instruction_id in arm
    )
    multiple_arm_ids = {
        instruction_id
        for instruction_id, count in arm_membership_count.items()
        if count > 1
    }
    _require(not multiple_arm_ids, "repeat claimed by multiple coverage arms")
    _require(
        not admitted_alias_evidence_ids & excluded_nonalias_evidence_ids,
        "nonalias evidence entered alias construction",
    )
    _require(
        structural_alias_evidence_ids <= admitted_alias_evidence_ids,
        "semantic alias evidence missing from construction",
    )
    _require(
        alias_instruction_ids <= semantic_candidate_instruction_ids
        and len(alias_pair_rows) >= len(admitted_alias_evidence_ids),
        "A arm escaped the semantic adjudication ledger",
    )
    return RepeatArmConstruction(
        repeat_instruction_ids=frozenset(repeat_instruction_ids),
        alias_instruction_ids=frozenset(alias_instruction_ids),
        alias_evidence_ids=frozenset(admitted_alias_evidence_ids),
        alias_pair_rows=tuple(alias_pair_rows),
        closure_alias_pair_rows=tuple(closure_alias_pair_rows),
        semantic_adjudication_rows=tuple(resolved_semantic_rows),
        outside_instruction_ids=frozenset(outside_instruction_ids),
        aggregate_instruction_ids=frozenset(aggregate_instruction_ids),
        redirection_instruction_ids=frozenset(redirection_instruction_ids),
        incompatible_instruction_ids=frozenset(incompatible_instruction_ids),
        structural_stop_instruction_ids=frozenset(
            structural_stop_instruction_ids
        ),
        excluded_nonalias_evidence_ids=frozenset(
            excluded_nonalias_evidence_ids
        ),
    )


def _repeat_coverage_census(
    documents: Sequence[NormalizedDocument],
    construction: RepeatArmConstruction | None = None,
) -> dict[str, int]:
    resolved = construction or _repeat_arm_construction(documents)
    lawful_covered_ids = set().union(
        resolved.alias_instruction_ids,
        resolved.outside_instruction_ids,
        resolved.aggregate_instruction_ids,
        resolved.redirection_instruction_ids,
    )
    otherwise_unresolved = resolved.repeat_instruction_ids - (
        lawful_covered_ids | resolved.incompatible_instruction_ids
    )
    return {
        "repeat_occurrence_count": len(resolved.repeat_instruction_ids),
        "valid_direct_proof_instruction_count": len(
            resolved.alias_instruction_ids
        ),
        "outside_domain_instruction_count": len(
            resolved.outside_instruction_ids
        ),
        "noncatalog_aggregate_relation_instruction_count": len(
            resolved.aggregate_instruction_ids
        ),
        "in_domain_redirection_instruction_count": len(
            resolved.redirection_instruction_ids
        ),
        "in_domain_nonalias_relation_instruction_count": len(
            resolved.aggregate_instruction_ids
            | resolved.redirection_instruction_ids
        ),
        "incompatible_proof_instruction_count": len(
            resolved.incompatible_instruction_ids
        ),
        "valid_and_incompatible_instruction_overlap_count": len(
            resolved.alias_instruction_ids
            & resolved.incompatible_instruction_ids
        ),
        "lawful_repeat_coverage_multiple_arm_instruction_count": 0,
        "disclosed_stop_instruction_count": len(
            resolved.repeat_instruction_ids - lawful_covered_ids
        ),
        "otherwise_unresolved_instruction_count": len(otherwise_unresolved),
    }


def _pilot_census(
    documents: Sequence[NormalizedDocument],
    *,
    citation_documents: Sequence[NormalizedDocument] | None = None,
) -> dict[str, Any]:
    classification_counts: Counter[str] = Counter()
    occurrence_kind_counts: Counter[str] = Counter()
    evidence_shape_counts: Counter[str] = Counter()
    for document in documents:
        for anchor in document.anchor_rows:
            classification_counts[anchor["classification"]] += 1
            occurrence_kind_counts[anchor["occurrence_kind"]] += 1
        for evidence in document.evidence_rows:
            has_alias = bool(evidence["alias_anchor_occurrence_ids"])
            has_canonical = bool(evidence["canonical_anchor_occurrence_ids"])
            if has_alias and has_canonical:
                evidence_shape_counts["both_endpoints"] += 1
            elif has_alias or has_canonical:
                evidence_shape_counts["partial_endpoints"] += 1
            else:
                evidence_shape_counts["no_endpoints"] += 1
    repeat_construction = _repeat_arm_construction(
        documents, citation_documents=citation_documents
    )
    repeat_census = _repeat_coverage_census(documents, repeat_construction)
    component_raw_cardinality: Counter[str] = Counter()
    component_dispositions: Counter[str] = Counter()
    raw_cross_category = 0
    eligible_cross_category = 0
    eligible_ineligible_mixed = 0
    invalid_parent_references = 0
    component_total = 0
    for document in documents:
        for anchor in _source_component_rows(document):
            shape = _component_shape_row(document, anchor)
            component_total += 1
            raw_count = shape["serialized_parent_cardinality"]
            raw_label = (
                "zero"
                if raw_count == 0
                else "one" if raw_count == 1 else "multiple"
            )
            component_raw_cardinality[raw_label] += 1
            component_dispositions[shape["disposition"]] += 1
            raw_cross_category += int(shape["raw_parent_category_ambiguity"])
            eligible_cross_category += int(
                shape["eligible_parent_category_ambiguity"]
            )
            eligible_ineligible_mixed += int(
                shape["eligible_ineligible_mixed_ambiguity"]
            )
            invalid_parent_references += sum(
                not row["eligible_parent"]
                for row in shape["parent_candidate_rows"]
            )
    role_total = (
        classification_counts[ROLE_HEAD] + classification_counts[ROLE_SPOUSE]
    )
    aggregate_total = sum(
        occurrence_kind_counts[value] for value in AGGREGATE_OCCURRENCE_KINDS
    )
    return {
        "document_count": len(documents),
        "questionnaire_page_count": sum(
            value.page_count for value in documents
        ),
        "questionnaire_occurrence_count": sum(
            value.occurrence_count for value in documents
        ),
        "flow_branch_count": sum(value.flow_count for value in documents),
        "local_anchor_count": sum(
            len(value.anchor_rows) for value in documents
        ),
        "field_purpose_count": sum(
            value.field_purpose_count for value in documents
        ),
        "role_anchor_count": role_total,
        "head_role_anchor_count": classification_counts[ROLE_HEAD],
        "spouse_role_anchor_count": classification_counts[ROLE_SPOUSE],
        "job_anchor_count": classification_counts["source_job"],
        "source_component_anchor_count": component_total,
        "source_context_anchor_count": classification_counts["source_context"],
        "source_remuneration_anchor_count": classification_counts[
            "source_remuneration_component"
        ],
        "aggregate_anchor_count": aggregate_total,
        **repeat_census,
        "local_evidence_row_count": sum(
            len(value.evidence_rows) for value in documents
        ),
        "local_evidence_shape_counts": dict(
            sorted(evidence_shape_counts.items())
        ),
        "serialized_component_parent_cardinality": {
            key: component_raw_cardinality[key]
            for key in ("zero", "one", "multiple")
        },
        "component_parent_disposition_counts": dict(
            sorted(component_dispositions.items())
        ),
        "raw_cross_category_multi_parent_count": raw_cross_category,
        "eligible_cross_category_multi_parent_count": (
            eligible_cross_category
        ),
        "eligible_ineligible_mixed_multi_parent_count": (
            eligible_ineligible_mixed
        ),
        "ineligible_parent_reference_count": invalid_parent_references,
    }


@cache
def _authenticated_pilot_census_bytes() -> bytes:
    """Rebuild the complete pilot census once from the pinned source bytes."""
    documents, _source_identity = _load_documents(SourceReader(None))
    pilot_documents = [
        document
        for document in documents
        if document.position in PILOT_POSITIONS
    ]
    _require(
        tuple(document.position for document in pilot_documents)
        == PILOT_POSITIONS,
        "authenticated pilot census membership drift",
    )
    return canonical_bytes(
        _pilot_census(pilot_documents, citation_documents=documents)
    )


def _build_bundle(
    documents: Sequence[NormalizedDocument],
    source_identity: Mapping[str, Any],
    design_prefix_identity: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    pilot_documents = [
        document
        for document in documents
        if document.position in PILOT_POSITIONS
    ]
    _require(
        tuple(document.position for document in pilot_documents)
        == PILOT_POSITIONS,
        "pilot membership drift",
    )
    pilot_rows: list[dict[str, Any]] = []
    for document in pilot_documents:
        pilot_rows.append(
            {
                "document_source_position": document.position,
                "era_id": document.era_id,
                "annotation_path": document.annotation_path,
                "source_document_id": document.source_document_id,
                "schema_version": document.schema_version,
                "annotation_byte_size": document.annotation_identity[
                    "byte_size"
                ],
                "annotation_raw_sha256": document.annotation_identity[
                    "raw_sha256"
                ],
                "annotation_content_sha256": document.annotation_identity[
                    "content_sha256"
                ],
                "pilot_role": (
                    "clean_era_control"
                    if document.position in CONTROL_POSITIONS
                    else "charter_pathology_carrier"
                ),
                "selection_tags": list(PILOT_TAGS[document.position]),
            }
        )
    pilot_census = _pilot_census(pilot_documents, citation_documents=documents)
    pilot_annotation_bytes = sum(
        row["annotation_byte_size"] for row in pilot_rows
    )
    slice_artifact = _artifact(
        "amendment_12_rq_catalog_pilot_slice_manifest.v1",
        "a12-rq-pilot-slice:",
        "amendment_12_tier_1_pilot_nonauthority",
        {
            "tier": 1,
            "design_prefix_identity": design_prefix_identity,
            "source_corpus_identity": source_identity,
            "control_selection_rule": (
                "earliest_source_order_noncarrier_in_each_era_with_zero_"
                "outside_domain_rows_zero_defective_populated_proof_rows_"
                "and_zero_aggregate_kind_component_slot_rows"
            ),
            "pilot_document_rows": pilot_rows,
            "pilot_document_count": len(pilot_rows),
            "pilot_document_positions": list(PILOT_POSITIONS),
            "pilot_document_position_domain_sha256": _domain_sha(
                list(PILOT_POSITIONS)
            ),
            "pilot_annotation_raw_byte_count": pilot_annotation_bytes,
            "pilot_census": pilot_census,
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_pilot_slice_fixed_nonauthority",
        },
    )

    all_role_classes, role_class_by_label = _role_classes(documents)
    full_component_shapes = [
        _component_shape_row(document, anchor)
        for document in documents
        for anchor in _source_component_rows(document)
    ]
    source_anchor_index = {
        (document.position, anchor["source_occurrence_id"]): (
            document,
            anchor,
        )
        for document in documents
        for anchor in document.anchor_rows
    }
    parent_source_witness_rows: list[dict[str, Any]] = []
    seen_parent_source_keys: set[tuple[int, str]] = set()
    for shape in full_component_shapes:
        for candidate in shape["parent_candidate_rows"]:
            source_key = (
                shape["document_source_position"],
                candidate["parent_occurrence_id"],
            )
            _require(
                source_key in source_anchor_index,
                "component parent is absent from the pinned source anchor domain",
            )
            document, source_anchor = source_anchor_index[source_key]
            _require(
                source_anchor["occurrence_kind"]
                == candidate["parent_occurrence_kind"],
                "component parent kind differs from pinned source anchor",
            )
            if source_key in seen_parent_source_keys:
                continue
            seen_parent_source_keys.add(source_key)
            witness_id = _row_id(
                "a12-parent-source-witness:",
                [
                    document.source_document_id,
                    source_anchor["local_anchor_classification_id"],
                    source_anchor["source_occurrence_id"],
                    source_anchor["occurrence_kind"],
                ],
            )
            parent_source_witness_rows.append(
                {
                    "parent_source_witness_id": witness_id,
                    "document_source_position": document.position,
                    "source_document_id": document.source_document_id,
                    "source_classification_id": source_anchor[
                        "local_anchor_classification_id"
                    ],
                    "parent_occurrence_id": source_anchor[
                        "source_occurrence_id"
                    ],
                    "parent_occurrence_kind": source_anchor["occurrence_kind"],
                    "parent_classification": source_anchor["classification"],
                    "status": "pinned_source_parent_witness",
                }
            )
    full_outside_rows = _outside_repeat_rows(documents)
    full_aggregate_relation_rows = _noncatalog_aggregate_relation_rows(
        documents
    )
    full_redirection_relation_rows = _in_domain_redirection_rows(documents)
    cross_reference_structural_census = _cross_reference_structural_census(
        documents
    )
    full_component_cross_reference_sweep_rows = (
        _in_domain_component_cross_reference_sweep_rows(documents)
    )
    (
        full_alias_semantic_adjudication_rows,
        alias_semantic_input_identity_rows,
    ) = _alias_evidence_semantic_adjudication_rows(
        documents,
        outside_rows=full_outside_rows,
        aggregate_rows=full_aggregate_relation_rows,
        redirection_rows=full_redirection_relation_rows,
        structural_rows=full_component_cross_reference_sweep_rows,
    )
    full_repeat_construction = _repeat_arm_construction(
        documents,
        outside_rows=full_outside_rows,
        aggregate_rows=full_aggregate_relation_rows,
        redirection_rows=full_redirection_relation_rows,
        structural_rows=full_component_cross_reference_sweep_rows,
        semantic_rows=full_alias_semantic_adjudication_rows,
    )
    component_cross_reference_sweep_counts = (
        _component_cross_reference_sweep_counts(
            full_component_cross_reference_sweep_rows
        )
    )
    pilot_component_cross_reference_sweep_counts = (
        _component_cross_reference_sweep_counts(
            [
                row
                for row in full_component_cross_reference_sweep_rows
                if row["pilot_document_member"]
            ]
        )
    )
    full_redirection_lineage_rows = (
        _exclusive_destination_redirection_lineage_rows(documents)
    )
    full_repeat_instruction_rows = [
        row
        for document in documents
        for row in document.repeat_occurrence_rows
    ]
    full_repeat_census = _repeat_coverage_census(
        documents, full_repeat_construction
    )
    raw_cardinality = Counter()
    disposition_counts = Counter()
    invalid_parent_refs = 0
    for row in full_component_shapes:
        raw_count = row["serialized_parent_cardinality"]
        raw_cardinality[
            (
                "zero"
                if raw_count == 0
                else "one" if raw_count == 1 else "multiple"
            )
        ] += 1
        disposition_counts[row["disposition"]] += 1
        invalid_parent_refs += sum(
            not value["eligible_parent"]
            for value in row["parent_candidate_rows"]
        )
    sweep_artifact = _artifact(
        "amendment_12_rq_catalog_corpus_exhaustive_targeted_sweeps.v1",
        "a12-rq-corpus-sweeps:",
        "amendment_12_corpus_exhaustive_shape_sweeps_nonauthority",
        {
            "tier": 1,
            "source_corpus_identity": source_identity,
            "document_positions_swept": list(range(1, 82)),
            "document_count": 81,
            "role_exact_label_class_rows": all_role_classes,
            "role_exact_label_class_count": len(all_role_classes),
            "role_exact_label_class_domain_sha256": _domain_sha(
                all_role_classes
            ),
            "role_anchor_count": sum(
                row["member_count"] for row in all_role_classes
            ),
            "role_noncanonical_assignment_reach_count": (
                sum(row["member_count"] for row in all_role_classes) - 2
            ),
            "role_cross_classification_label_count": 0,
            "role_unreached_anchor_rows": [],
            "role_unreached_anchor_count": 0,
            "outside_domain_repeat_shape_rows": full_outside_rows,
            "outside_domain_repeat_shape_count": len(full_outside_rows),
            "outside_domain_repeat_shape_domain_sha256": _domain_sha(
                full_outside_rows
            ),
            "noncatalog_aggregate_relation_shape_rows": (
                full_aggregate_relation_rows
            ),
            "noncatalog_aggregate_relation_shape_count": len(
                full_aggregate_relation_rows
            ),
            "noncatalog_aggregate_relation_shape_keyset_sha256": _keyset_sha(
                [
                    row["noncatalog_aggregate_relation_disposition_id"]
                    for row in full_aggregate_relation_rows
                ]
            ),
            "noncatalog_aggregate_relation_shape_domain_sha256": _domain_sha(
                full_aggregate_relation_rows
            ),
            "in_domain_redirection_shape_rows": (
                full_redirection_relation_rows
            ),
            "in_domain_redirection_shape_count": len(
                full_redirection_relation_rows
            ),
            "in_domain_redirection_shape_keyset_sha256": _keyset_sha(
                [
                    row["in_domain_redirection_relation_disposition_id"]
                    for row in full_redirection_relation_rows
                ]
            ),
            "in_domain_redirection_shape_domain_sha256": _domain_sha(
                full_redirection_relation_rows
            ),
            **cross_reference_structural_census,
            "in_domain_component_cross_reference_sweep_rows": (
                full_component_cross_reference_sweep_rows
            ),
            "in_domain_component_cross_reference_sweep_count": (
                component_cross_reference_sweep_counts["instruction_count"]
            ),
            "in_domain_component_cross_reference_sweep_edge_count": (
                component_cross_reference_sweep_counts["edge_count"]
            ),
            "in_domain_component_cross_reference_sweep_keyset_sha256": (
                _keyset_sha(
                    [
                        row["in_domain_component_cross_reference_sweep_id"]
                        for row in full_component_cross_reference_sweep_rows
                    ]
                )
            ),
            "in_domain_component_cross_reference_sweep_domain_sha256": (
                _domain_sha(full_component_cross_reference_sweep_rows)
            ),
            "semantic_alias_adjudication_count": len(
                full_component_cross_reference_sweep_rows
            ),
            "semantic_alias_adjudication_keyset_sha256": _keyset_sha(
                [
                    row["semantic_alias_adjudication_id"]
                    for row in full_component_cross_reference_sweep_rows
                ]
            ),
            "semantic_alias_adjudication_domain_sha256": _domain_sha(
                full_component_cross_reference_sweep_rows
            ),
            "alias_semantic_input_identity_rows": (
                alias_semantic_input_identity_rows
            ),
            "alias_semantic_input_identity_count": len(
                alias_semantic_input_identity_rows
            ),
            "alias_semantic_input_identity_domain_sha256": _domain_sha(
                alias_semantic_input_identity_rows
            ),
            "alias_evidence_semantic_adjudication_rows": (
                full_alias_semantic_adjudication_rows
            ),
            "alias_evidence_semantic_adjudication_count": len(
                full_alias_semantic_adjudication_rows
            ),
            "ca41663_alias_evidence_adjudication_count": sum(
                row["ca41663_admitted_alias_evidence"]
                for row in full_alias_semantic_adjudication_rows
            ),
            "round_five_continuation_restoration_count": sum(
                row["round_five_continuation_restoration"]
                for row in full_alias_semantic_adjudication_rows
            ),
            "continuation_composition_citation_count": sum(
                row["continuation_composition_citation"] is not None
                for row in full_alias_semantic_adjudication_rows
            ),
            "alias_evidence_semantic_adjudication_keyset_sha256": (
                _keyset_sha(
                    [
                        row["semantic_alias_evidence_adjudication_id"]
                        for row in full_alias_semantic_adjudication_rows
                    ]
                )
            ),
            "alias_evidence_semantic_adjudication_domain_sha256": (
                _domain_sha(full_alias_semantic_adjudication_rows)
            ),
            "alias_evidence_semantic_decision_counts": dict(
                sorted(
                    Counter(
                        row["decision"]
                        for row in full_alias_semantic_adjudication_rows
                    ).items()
                )
            ),
            "alias_evidence_semantic_candidate_origin_counts": dict(
                sorted(
                    Counter(
                        row["candidate_origin"]
                        for row in full_alias_semantic_adjudication_rows
                    ).items()
                )
            ),
            "approved_alias_evidence_count": len(
                full_repeat_construction.alias_evidence_ids
            ),
            "disclosed_stop_alias_evidence_count": sum(
                not row["approved_pair_rows"]
                for row in full_alias_semantic_adjudication_rows
            ),
            "approved_alias_pair_rows": list(
                full_repeat_construction.alias_pair_rows
            ),
            "approved_alias_pair_count": len(
                full_repeat_construction.alias_pair_rows
            ),
            "approved_alias_pair_keyset_sha256": _keyset_sha(
                [
                    row["semantic_alias_pair_adjudication_id"]
                    for row in full_repeat_construction.alias_pair_rows
                ]
            ),
            "approved_alias_pair_domain_sha256": _domain_sha(
                full_repeat_construction.alias_pair_rows
            ),
            "occurrence_closure_alias_pair_count": len(
                full_repeat_construction.closure_alias_pair_rows
            ),
            "typed_projection_alias_pair_count": sum(
                row["typed_projection_union_prohibited"]
                for row in full_repeat_construction.alias_pair_rows
            ),
            "semantic_alias_adjudication_outcome_counts": {
                key: component_cross_reference_sweep_counts[key]
                for key in (
                    "alias_instruction_count",
                    "alias_edge_count",
                    "alias_pair_count",
                    "redirection_instruction_count",
                    "redirection_edge_count",
                    "stop_instruction_count",
                    "stop_edge_count",
                )
            },
            "semantic_alias_instruction_outcome_domain_sha256": _domain_sha(
                [
                    [
                        row["source_instruction_occurrence_id"],
                        _semantic_alias_outcome_code(row),
                    ]
                    for row in full_component_cross_reference_sweep_rows
                ]
            ),
            "semantic_alias_equivalence_instruction_keyset_sha256": (
                _keyset_sha(
                    [
                        row["source_instruction_occurrence_id"]
                        for row in full_component_cross_reference_sweep_rows
                        if _semantic_alias_outcome_code(row) == "A"
                    ]
                )
            ),
            "semantic_alias_redirection_instruction_keyset_sha256": (
                _keyset_sha(
                    [
                        row["source_instruction_occurrence_id"]
                        for row in full_component_cross_reference_sweep_rows
                        if _semantic_alias_outcome_code(row) == "R"
                    ]
                )
            ),
            "semantic_alias_stop_instruction_keyset_sha256": _keyset_sha(
                [
                    row["source_instruction_occurrence_id"]
                    for row in full_component_cross_reference_sweep_rows
                    if _semantic_alias_outcome_code(row) == "S"
                ]
            ),
            "semantic_alias_source_instruction_fragment_count": sum(
                row["source_instruction_fragment"]
                for row in full_component_cross_reference_sweep_rows
            ),
            "semantic_alias_fragment_seal_quality_issue_count": sum(
                row["tier_2_predecessor_seal_quality_issue"]
                for row in full_component_cross_reference_sweep_rows
            ),
            "semantic_alias_round_three_fragment_reseal_count": sum(
                row["tier_2_predecessor_ledger_note"]
                == "round_three_reseal_ledger_already_covers_fragment"
                for row in full_component_cross_reference_sweep_rows
            ),
            "semantic_alias_round_four_new_fragment_reseal_count": sum(
                row["tier_2_predecessor_ledger_note"]
                == "new_tier_2_reseal_required_for_incomplete_fragment"
                for row in full_component_cross_reference_sweep_rows
            ),
            "semantic_alias_decisive_fragment_no_reseal_count": sum(
                row["tier_2_predecessor_ledger_note"]
                == "fragment_semantically_decisive_no_reseal_required"
                for row in full_component_cross_reference_sweep_rows
            ),
            "semantic_alias_fragment_instruction_keyset_sha256": _keyset_sha(
                [
                    row["source_instruction_occurrence_id"]
                    for row in full_component_cross_reference_sweep_rows
                    if row["source_instruction_fragment"]
                ]
            ),
            "semantic_alias_round_four_new_fragment_keyset_sha256": (
                _keyset_sha(
                    [
                        row["source_instruction_occurrence_id"]
                        for row in full_component_cross_reference_sweep_rows
                        if row["tier_2_predecessor_ledger_note"]
                        == "new_tier_2_reseal_required_for_incomplete_fragment"
                    ]
                )
            ),
            "in_domain_component_cross_reference_sweep_alias_instruction_count": (
                component_cross_reference_sweep_counts[
                    "alias_instruction_count"
                ]
            ),
            "in_domain_component_cross_reference_sweep_alias_edge_count": (
                component_cross_reference_sweep_counts["alias_edge_count"]
            ),
            "in_domain_component_cross_reference_sweep_alias_pair_count": (
                component_cross_reference_sweep_counts["alias_pair_count"]
            ),
            "in_domain_component_cross_reference_sweep_redirection_instruction_count": (
                component_cross_reference_sweep_counts[
                    "redirection_instruction_count"
                ]
            ),
            "in_domain_component_cross_reference_sweep_redirection_edge_count": (
                component_cross_reference_sweep_counts[
                    "redirection_edge_count"
                ]
            ),
            "in_domain_component_cross_reference_sweep_stop_instruction_count": (
                component_cross_reference_sweep_counts[
                    "stop_instruction_count"
                ]
            ),
            "in_domain_component_cross_reference_sweep_stop_edge_count": (
                component_cross_reference_sweep_counts["stop_edge_count"]
            ),
            "pilot_in_domain_component_cross_reference_sweep_count": (
                pilot_component_cross_reference_sweep_counts[
                    "instruction_count"
                ]
            ),
            "pilot_in_domain_component_cross_reference_sweep_edge_count": (
                pilot_component_cross_reference_sweep_counts["edge_count"]
            ),
            "pilot_in_domain_component_cross_reference_sweep_alias_instruction_count": (
                pilot_component_cross_reference_sweep_counts[
                    "alias_instruction_count"
                ]
            ),
            "pilot_in_domain_component_cross_reference_sweep_alias_edge_count": (
                pilot_component_cross_reference_sweep_counts[
                    "alias_edge_count"
                ]
            ),
            "pilot_in_domain_component_cross_reference_sweep_alias_pair_count": (
                pilot_component_cross_reference_sweep_counts[
                    "alias_pair_count"
                ]
            ),
            "pilot_in_domain_component_cross_reference_sweep_redirection_instruction_count": (
                pilot_component_cross_reference_sweep_counts[
                    "redirection_instruction_count"
                ]
            ),
            "pilot_in_domain_component_cross_reference_sweep_redirection_edge_count": (
                pilot_component_cross_reference_sweep_counts[
                    "redirection_edge_count"
                ]
            ),
            "pilot_in_domain_component_cross_reference_sweep_stop_instruction_count": (
                pilot_component_cross_reference_sweep_counts[
                    "stop_instruction_count"
                ]
            ),
            "pilot_in_domain_component_cross_reference_sweep_stop_edge_count": (
                pilot_component_cross_reference_sweep_counts["stop_edge_count"]
            ),
            "repeat_instruction_text_scan_count": len(
                full_repeat_instruction_rows
            ),
            "literal_cross_reference_instruction_count": sum(
                "cross-reference" in row["matched_text"].lower()
                for row in full_repeat_instruction_rows
            ),
            "exclusive_destination_redirection_lineage_rows": (
                full_redirection_lineage_rows
            ),
            "exclusive_destination_redirection_lineage_count": len(
                full_redirection_lineage_rows
            ),
            "exclusive_destination_redirection_lineage_keyset_sha256": (
                _keyset_sha(
                    [
                        row["exclusive_destination_redirection_lineage_id"]
                        for row in full_redirection_lineage_rows
                    ]
                )
            ),
            "exclusive_destination_redirection_lineage_domain_sha256": (
                _domain_sha(full_redirection_lineage_rows)
            ),
            "exclusive_destination_redirection_lineage_admitted_count": sum(
                row["in_domain_redirection_arm_eligible"]
                for row in full_redirection_lineage_rows
            ),
            "exclusive_destination_redirection_lineage_aggregate_count": sum(
                row["lineage_disposition"]
                == "covered_by_existing_aggregate_nonalias_subkind"
                for row in full_redirection_lineage_rows
            ),
            "exclusive_destination_redirection_lineage_stop_count": sum(
                row["lineage_disposition"].startswith("disclosed_stop_")
                for row in full_redirection_lineage_rows
            ),
            "exclusive_destination_redirection_lineage_mixed_stop_count": sum(
                row["lineage_disposition"]
                == "disclosed_stop_mixed_aggregate_component_proof"
                for row in full_redirection_lineage_rows
            ),
            "exclusive_destination_redirection_lineage_incomplete_stop_count": sum(
                row["lineage_disposition"]
                == "disclosed_stop_incomplete_local_proof"
                for row in full_redirection_lineage_rows
            ),
            "repeat_coverage_census": full_repeat_census,
            "component_parent_shape_rows": full_component_shapes,
            "component_parent_shape_count": len(full_component_shapes),
            "component_parent_shape_keyset_sha256": _keyset_sha(
                [
                    row["component_parent_resolution_id"]
                    for row in full_component_shapes
                ]
            ),
            "component_parent_shape_domain_sha256": _domain_sha(
                full_component_shapes
            ),
            "parent_source_witness_rows": parent_source_witness_rows,
            "parent_source_witness_count": len(parent_source_witness_rows),
            "parent_source_witness_keyset_sha256": _keyset_sha(
                [
                    row["parent_source_witness_id"]
                    for row in parent_source_witness_rows
                ]
            ),
            "parent_source_witness_domain_sha256": _domain_sha(
                parent_source_witness_rows
            ),
            "serialized_parent_cardinality_counts": {
                key: raw_cardinality[key]
                for key in ("zero", "one", "multiple")
            },
            "component_parent_disposition_counts": dict(
                sorted(disposition_counts.items())
            ),
            "raw_cross_category_multi_parent_count": sum(
                row["raw_parent_category_ambiguity"]
                for row in full_component_shapes
            ),
            "eligible_cross_category_multi_parent_count": sum(
                row["eligible_parent_category_ambiguity"]
                for row in full_component_shapes
            ),
            "eligible_ineligible_mixed_multi_parent_count": sum(
                row["eligible_ineligible_mixed_ambiguity"]
                for row in full_component_shapes
            ),
            "ineligible_parent_reference_count": invalid_parent_refs,
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_corpus_exhaustive_targeted_sweeps_nonauthority",
        },
    )

    proof_adjudications = _proof_adjudication_rows(documents)
    doc036_defects = _doc036_defect_rows(documents)
    proof_seal_defects = [
        row
        for row in proof_adjudications
        if row["disposition"] == "predecessor_seal_defect"
    ]
    proof_law_gaps = [
        row for row in proof_adjudications if row["law_gap_admitted"]
    ]
    predecessor_artifact = _artifact(
        "amendment_12_rq_catalog_predecessor_defect_adjudication.v1",
        "a12-rq-predecessor-adjudication:",
        "amendment_12_predecessor_adjudication_sweep_nonauthority",
        {
            "tier": 1,
            "source_corpus_identity": source_identity,
            "semantic_alias_sweep_artifact_id": sweep_artifact["artifact_id"],
            "doc036_aggregate_component_slot_rows": doc036_defects,
            "doc036_aggregate_component_slot_count": len(doc036_defects),
            "doc036_aggregate_component_slot_domain_sha256": _domain_sha(
                doc036_defects
            ),
            "populated_local_proof_adjudication_rows": proof_adjudications,
            "populated_local_proof_adjudication_count": len(
                proof_adjudications
            ),
            "populated_local_proof_adjudication_keyset_sha256": _keyset_sha(
                [
                    row["source_local_evidence_id"]
                    for row in proof_adjudications
                ]
            ),
            "populated_local_proof_adjudication_domain_sha256": _domain_sha(
                proof_adjudications
            ),
            "populated_local_proof_seal_defect_count": len(proof_seal_defects),
            "populated_local_proof_law_gap_count": len(proof_law_gaps),
            "source_flag_counts": {
                key: sum(
                    row["defect_flags"][key] for row in proof_adjudications
                )
                for key in (
                    "touches_noncatalog_aggregate_endpoint",
                    "occurrence_derived_domain_crossing",
                    "corrected_catalog_domain_crossing",
                    "raw_node_domain_crossing",
                    "context_remuneration_mix",
                    "head_spouse_mix",
                )
            },
            "seal_defect_flag_counts": {
                key: sum(
                    row["defect_flags"][key] for row in proof_seal_defects
                )
                for key in (
                    "touches_noncatalog_aggregate_endpoint",
                    "occurrence_derived_domain_crossing",
                    "corrected_catalog_domain_crossing",
                    "raw_node_domain_crossing",
                    "context_remuneration_mix",
                    "head_spouse_mix",
                )
            },
            "seal_defect_disposition_count": len(doc036_defects)
            + len(proof_seal_defects),
            "law_gap_disposition_count": len(proof_law_gaps),
            "in_domain_nonalias_law_gap_repair_count": len(proof_law_gaps),
            "in_domain_nonalias_law_gap_subkind_counts": dict(
                sorted(
                    Counter(
                        row["in_domain_nonalias_relation_subkind"]
                        for row in proof_law_gaps
                    ).items()
                )
            ),
            "round_four_new_fragment_seal_quality_issue_count": 10,
            "round_four_new_fragment_instruction_keyset_sha256": (
                sweep_artifact[
                    "semantic_alias_round_four_new_fragment_keyset_sha256"
                ]
            ),
            "tier_2_predecessor_seal_quality_issue_count": 46,
            "tier_2_precondition": (
                "all_36_round_three_defects_and_10_round_five_fragments_"
                "repaired_and_amendment_ratified_before_certification"
            ),
            "adjudication_rule": (
                "round_five_source_cited_semantic_ledger_is_the_only_A_"
                "admission_gate_and_exact_covers_262_baseline_rows_plus_"
                "3_continuation_restorations"
            ),
            "nonauthority_statement": _nonauthority_statement(),
            "status": (
                "pass_adjudication_with_46_predecessor_repairs_required"
            ),
        },
    )

    (
        component_class_admission_rows,
        catalog_only_job_complement_rows,
    ) = _derived_class_complement_sweep_rows(
        documents,
        full_component_shapes,
        full_repeat_construction.closure_alias_pair_rows,
    )
    derived_sweep_artifact = _artifact(
        "amendment_12_rq_catalog_derived_class_complement_sweeps.v1",
        "a12-rq-derived-sweeps:",
        "amendment_12_derived_class_complement_sweeps_nonauthority",
        {
            "tier": 1,
            "source_corpus_identity": source_identity,
            "corpus_sweep_artifact_id": sweep_artifact["artifact_id"],
            "predecessor_artifact_id": predecessor_artifact["artifact_id"],
            "predecessor_seal_defect_count": 36,
            "round_four_new_fragment_seal_quality_issue_count": 10,
            "tier_2_predecessor_seal_quality_issue_count": 46,
            "predecessor_reseal_required": True,
            "component_class_admission_sweep_rows": (
                component_class_admission_rows
            ),
            "component_class_admission_sweep_count": len(
                component_class_admission_rows
            ),
            "component_class_member_occurrence_count": sum(
                row["component_class_member_count"]
                for row in component_class_admission_rows
            ),
            "component_class_admission_sweep_keyset_sha256": _keyset_sha(
                [
                    row["component_class_admission_sweep_id"]
                    for row in component_class_admission_rows
                ]
            ),
            "component_class_admission_sweep_domain_sha256": _domain_sha(
                component_class_admission_rows
            ),
            "component_class_candidate_disposition_counts": dict(
                sorted(
                    Counter(
                        row["candidate_disposition"]
                        for row in component_class_admission_rows
                    ).items()
                )
            ),
            "component_class_relationship_arm_eligible_count": sum(
                row["relationship_arm_eligible"]
                for row in component_class_admission_rows
            ),
            "component_alias_support_origin_counts": dict(
                sorted(
                    Counter(
                        support["support_origin"]
                        for row in component_class_admission_rows
                        for support in row["alias_support_rows"]
                    ).items()
                )
            ),
            "catalog_only_job_complement_sweep_rows": (
                catalog_only_job_complement_rows
            ),
            "catalog_only_job_complement_sweep_count": len(
                catalog_only_job_complement_rows
            ),
            "job_class_member_occurrence_count": sum(
                row["job_class_member_count"]
                for row in catalog_only_job_complement_rows
            ),
            "catalog_only_job_complement_sweep_keyset_sha256": _keyset_sha(
                [
                    row["catalog_only_job_complement_sweep_id"]
                    for row in catalog_only_job_complement_rows
                ]
            ),
            "catalog_only_job_complement_sweep_domain_sha256": _domain_sha(
                catalog_only_job_complement_rows
            ),
            "catalog_only_job_coverage_arm_counts": dict(
                sorted(
                    Counter(
                        row["coverage_arm"]
                        for row in catalog_only_job_complement_rows
                    ).items()
                )
            ),
            "job_alias_support_origin_counts": dict(
                sorted(
                    Counter(
                        support["support_origin"]
                        for row in catalog_only_job_complement_rows
                        for support in row["alias_support_rows"]
                    ).items()
                )
            ),
            "nonauthority_statement": _nonauthority_statement(),
            "status": (
                "pass_derived_class_complement_sweeps_nonauthority_"
                "predecessor_reseal_required"
            ),
        },
    )

    pilot_role_classes: list[dict[str, Any]] = []
    pilot_member_ids = {
        anchor["source_occurrence_id"]
        for document in pilot_documents
        for anchor in _role_anchor_rows(document)
    }
    for row in all_role_classes:
        members = [
            value
            for value in row["member_occurrence_ids"]
            if value in pilot_member_ids
        ]
        if not members:
            continue
        projected = copy.deepcopy(row)
        projected["member_occurrence_ids"] = members
        projected["member_count"] = len(members)
        projected["member_keyset_sha256"] = _keyset_sha(members)
        pilot_role_classes.append(projected)
    role_assignments = _role_assignment_rows(
        pilot_documents, role_class_by_label
    )
    role_artifact = _artifact(
        "amendment_12_rq_catalog_role_assignment_pilot.v1",
        "a12-rq-role-pilot:",
        "amendment_12_tier_1_role_assignment_pilot_nonauthority",
        {
            "tier": 1,
            "source_slice_artifact_id": slice_artifact["artifact_id"],
            "corpus_sweep_artifact_id": sweep_artifact["artifact_id"],
            "canonical_role_occurrence_ids": ROLE_CANONICALS,
            "role_label_class_rows": pilot_role_classes,
            "role_label_class_count": len(pilot_role_classes),
            "role_label_class_domain_sha256": _domain_sha(pilot_role_classes),
            "role_assignment_rows": role_assignments,
            "role_assignment_count": len(role_assignments),
            "role_assignment_keyset_sha256": _keyset_sha(
                [row["role_assignment_id"] for row in role_assignments]
            ),
            "role_assignment_domain_sha256": _domain_sha(role_assignments),
            "unassigned_role_anchor_rows": [],
            "unassigned_role_anchor_count": 0,
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_role_assignment_law_pilot_nonauthority",
        },
    )

    pilot_outside_rows = _outside_repeat_rows(pilot_documents)
    pilot_aggregate_relation_rows = _noncatalog_aggregate_relation_rows(
        pilot_documents
    )
    pilot_redirection_relation_rows = _in_domain_redirection_rows(
        pilot_documents
    )
    repeat_artifact = _artifact(
        "amendment_12_rq_catalog_outside_domain_repeat_pilot.v1",
        "a12-rq-repeat-pilot:",
        "amendment_12_tier_1_repeat_disposition_pilot_nonauthority",
        {
            "tier": 1,
            "source_slice_artifact_id": slice_artifact["artifact_id"],
            "corpus_sweep_artifact_id": sweep_artifact["artifact_id"],
            "outside_domain_repeat_disposition_rows": pilot_outside_rows,
            "outside_domain_repeat_disposition_count": len(pilot_outside_rows),
            "outside_domain_repeat_disposition_keyset_sha256": _keyset_sha(
                [
                    row["outside_domain_repeat_disposition_id"]
                    for row in pilot_outside_rows
                ]
            ),
            "outside_domain_repeat_disposition_domain_sha256": _domain_sha(
                pilot_outside_rows
            ),
            "outside_domain_relation_counts": dict(
                sorted(
                    Counter(
                        row["relation"] for row in pilot_outside_rows
                    ).items()
                )
            ),
            "outside_domain_document_counts": {
                str(key): value
                for key, value in sorted(
                    Counter(
                        row["document_source_position"]
                        for row in pilot_outside_rows
                    ).items()
                )
            },
            "noncatalog_aggregate_relation_disposition_rows": (
                pilot_aggregate_relation_rows
            ),
            "noncatalog_aggregate_relation_disposition_count": len(
                pilot_aggregate_relation_rows
            ),
            "noncatalog_aggregate_relation_disposition_keyset_sha256": (
                _keyset_sha(
                    [
                        row["noncatalog_aggregate_relation_disposition_id"]
                        for row in pilot_aggregate_relation_rows
                    ]
                )
            ),
            "noncatalog_aggregate_relation_disposition_domain_sha256": (
                _domain_sha(pilot_aggregate_relation_rows)
            ),
            "aggregate_relation_counts": dict(
                sorted(
                    Counter(
                        row["relation"]
                        for row in pilot_aggregate_relation_rows
                    ).items()
                )
            ),
            "aggregate_document_counts": {
                str(key): value
                for key, value in sorted(
                    Counter(
                        row["document_source_position"]
                        for row in pilot_aggregate_relation_rows
                    ).items()
                )
            },
            "aggregate_handoff_status_counts": dict(
                sorted(
                    Counter(
                        row["handoff_status"]
                        for row in pilot_aggregate_relation_rows
                    ).items()
                )
            ),
            "in_domain_redirection_disposition_rows": (
                pilot_redirection_relation_rows
            ),
            "in_domain_redirection_disposition_count": len(
                pilot_redirection_relation_rows
            ),
            "in_domain_redirection_disposition_keyset_sha256": _keyset_sha(
                [
                    row["in_domain_redirection_relation_disposition_id"]
                    for row in pilot_redirection_relation_rows
                ]
            ),
            "in_domain_redirection_disposition_domain_sha256": _domain_sha(
                pilot_redirection_relation_rows
            ),
            "redirection_relation_counts": dict(
                sorted(
                    Counter(
                        row["relation"]
                        for row in pilot_redirection_relation_rows
                    ).items()
                )
            ),
            "redirection_document_counts": {
                str(key): value
                for key, value in sorted(
                    Counter(
                        row["document_source_position"]
                        for row in pilot_redirection_relation_rows
                    ).items()
                )
            },
            "redirection_handoff_status_counts": dict(
                sorted(
                    Counter(
                        row["handoff_status"]
                        for row in pilot_redirection_relation_rows
                    ).items()
                )
            ),
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_four_disposition_repeat_law_pilot_nonauthority",
        },
    )

    pilot_component_shapes = [
        _component_shape_row(document, anchor)
        for document in pilot_documents
        for anchor in _source_component_rows(document)
    ]
    zero_rows = [
        row
        for row in pilot_component_shapes
        if row["disposition"]
        in {
            "zero_parent_terminal_disposition",
            "zero_lawful_parent_terminal_disposition",
        }
    ]
    unique_rows = [
        row
        for row in pilot_component_shapes
        if row["disposition"] == "unique_parent_assignment"
    ]
    ambiguity_rows = [
        row
        for row in pilot_component_shapes
        if row["disposition"] == "multi_parent_ambiguity_no_selection"
    ]
    component_artifact = _artifact(
        "amendment_12_rq_catalog_component_parent_pilot.v1",
        "a12-rq-component-pilot:",
        "amendment_12_tier_1_component_parent_pilot_nonauthority",
        {
            "tier": 1,
            "source_slice_artifact_id": slice_artifact["artifact_id"],
            "corpus_sweep_artifact_id": sweep_artifact["artifact_id"],
            "zero_parent_disposition_rows": zero_rows,
            "zero_parent_disposition_count": len(zero_rows),
            "zero_parent_disposition_domain_sha256": _domain_sha(zero_rows),
            "unique_parent_assignment_rows": unique_rows,
            "unique_parent_assignment_count": len(unique_rows),
            "unique_parent_assignment_domain_sha256": _domain_sha(unique_rows),
            "multi_parent_ambiguity_rows": ambiguity_rows,
            "multi_parent_ambiguity_count": len(ambiguity_rows),
            "multi_parent_ambiguity_domain_sha256": _domain_sha(
                ambiguity_rows
            ),
            "complete_component_resolution_count": len(pilot_component_shapes),
            "complete_component_resolution_keyset_sha256": _keyset_sha(
                [
                    row["component_parent_resolution_id"]
                    for row in [*zero_rows, *unique_rows, *ambiguity_rows]
                ]
            ),
            "complete_component_resolution_domain_sha256": _domain_sha(
                [*zero_rows, *unique_rows, *ambiguity_rows]
            ),
            "serialized_parent_cardinality_counts": pilot_census[
                "serialized_component_parent_cardinality"
            ],
            "raw_cross_category_multi_parent_count": pilot_census[
                "raw_cross_category_multi_parent_count"
            ],
            "eligible_cross_category_multi_parent_count": pilot_census[
                "eligible_cross_category_multi_parent_count"
            ],
            "eligible_ineligible_mixed_multi_parent_count": pilot_census[
                "eligible_ineligible_mixed_multi_parent_count"
            ],
            "ineligible_parent_reference_count": pilot_census[
                "ineligible_parent_reference_count"
            ],
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_component_parent_law_pilot_nonauthority",
        },
    )

    preliminary = {
        "slice": slice_artifact,
        "sweeps": sweep_artifact,
        "derived": derived_sweep_artifact,
        "predecessor": predecessor_artifact,
        "role": role_artifact,
        "repeat": repeat_artifact,
        "component": component_artifact,
    }
    artifact_identity_rows = []
    for key, artifact in preliminary.items():
        raw = canonical_bytes(artifact)
        artifact_identity_rows.append(
            {
                "artifact_role": key,
                "path": (
                    "docs/analysis/amendment_12_rq_catalog_pilot/"
                    + OUTPUT_FILENAMES[key]
                ),
                "schema_version": artifact["schema_version"],
                "artifact_id": artifact["artifact_id"],
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
            }
        )
    gate_artifact = _artifact(
        "amendment_12_rq_catalog_pilot_gate_result.v1",
        "a12-rq-pilot-gate:",
        "amendment_12_tier_1_pilot_gate_result_nonauthority",
        {
            "tier": 1,
            "design_prefix_identity": design_prefix_identity,
            "source_slice_artifact_id": slice_artifact["artifact_id"],
            "artifact_identity_rows": artifact_identity_rows,
            "artifact_identity_count": len(artifact_identity_rows),
            "artifact_identity_domain_sha256": _domain_sha(
                artifact_identity_rows
            ),
            "pilot_census": pilot_census,
            "role_law_status": "pass",
            "four_disposition_repeat_law_status": "pass_law_shape_only",
            "component_parent_law_status": "pass",
            "predecessor_input_status": "reseal_required_before_tier_2",
            "overall_repeat_catalog_coverage_status": (
                "fail_closed_unresolved_rows_remain"
            ),
            "pilot_law_shape_status": "pass",
            "tier_2_protocol_status": (
                "not_started_requires_ratification_and_predecessor_reseals"
            ),
            "certification_status": "PILOT_NONAUTHORITY_CERTIFIES_NOTHING",
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_law_shapes_only_nonauthority",
        },
    )
    return {**preliminary, "gate": gate_artifact}


ARTIFACT_SPECS = {
    "slice": (
        "amendment_12_rq_catalog_pilot_slice_manifest.v1",
        "a12-rq-pilot-slice:",
        "amendment_12_tier_1_pilot_nonauthority",
    ),
    "sweeps": (
        "amendment_12_rq_catalog_corpus_exhaustive_targeted_sweeps.v1",
        "a12-rq-corpus-sweeps:",
        "amendment_12_corpus_exhaustive_shape_sweeps_nonauthority",
    ),
    "derived": (
        "amendment_12_rq_catalog_derived_class_complement_sweeps.v1",
        "a12-rq-derived-sweeps:",
        "amendment_12_derived_class_complement_sweeps_nonauthority",
    ),
    "predecessor": (
        "amendment_12_rq_catalog_predecessor_defect_adjudication.v1",
        "a12-rq-predecessor-adjudication:",
        "amendment_12_predecessor_adjudication_sweep_nonauthority",
    ),
    "role": (
        "amendment_12_rq_catalog_role_assignment_pilot.v1",
        "a12-rq-role-pilot:",
        "amendment_12_tier_1_role_assignment_pilot_nonauthority",
    ),
    "repeat": (
        "amendment_12_rq_catalog_outside_domain_repeat_pilot.v1",
        "a12-rq-repeat-pilot:",
        "amendment_12_tier_1_repeat_disposition_pilot_nonauthority",
    ),
    "component": (
        "amendment_12_rq_catalog_component_parent_pilot.v1",
        "a12-rq-component-pilot:",
        "amendment_12_tier_1_component_parent_pilot_nonauthority",
    ),
    "gate": (
        "amendment_12_rq_catalog_pilot_gate_result.v1",
        "a12-rq-pilot-gate:",
        "amendment_12_tier_1_pilot_gate_result_nonauthority",
    ),
}

_ENVELOPE_KEYS = {
    "schema_version",
    "artifact_id",
    "authority_kind",
    "integrity",
}
PILOT_CENSUS_KEYS = frozenset(
    {
        "aggregate_anchor_count",
        "component_parent_disposition_counts",
        "document_count",
        "eligible_cross_category_multi_parent_count",
        "eligible_ineligible_mixed_multi_parent_count",
        "field_purpose_count",
        "flow_branch_count",
        "head_role_anchor_count",
        "incompatible_proof_instruction_count",
        "in_domain_nonalias_relation_instruction_count",
        "in_domain_redirection_instruction_count",
        "ineligible_parent_reference_count",
        "job_anchor_count",
        "lawful_repeat_coverage_multiple_arm_instruction_count",
        "disclosed_stop_instruction_count",
        "local_anchor_count",
        "local_evidence_row_count",
        "local_evidence_shape_counts",
        "noncatalog_aggregate_relation_instruction_count",
        "otherwise_unresolved_instruction_count",
        "outside_domain_instruction_count",
        "questionnaire_occurrence_count",
        "questionnaire_page_count",
        "raw_cross_category_multi_parent_count",
        "repeat_occurrence_count",
        "role_anchor_count",
        "serialized_component_parent_cardinality",
        "source_component_anchor_count",
        "source_context_anchor_count",
        "source_remuneration_anchor_count",
        "spouse_role_anchor_count",
        "valid_and_incompatible_instruction_overlap_count",
        "valid_direct_proof_instruction_count",
    }
)
PILOT_CENSUS_NESTED_KEYS = {
    "component_parent_disposition_counts": frozenset(
        {
            "multi_parent_ambiguity_no_selection",
            "unique_parent_assignment",
            "zero_lawful_parent_terminal_disposition",
            "zero_parent_terminal_disposition",
        }
    ),
    "local_evidence_shape_counts": frozenset(
        {
            "both_endpoints",
            "no_endpoints",
            "partial_endpoints",
        }
    ),
    "serialized_component_parent_cardinality": frozenset(
        {
            "multiple",
            "one",
            "zero",
        }
    ),
}
ARTIFACT_TOP_LEVEL_KEYS = {
    "slice": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "design_prefix_identity",
            "source_corpus_identity",
            "control_selection_rule",
            "pilot_document_rows",
            "pilot_document_count",
            "pilot_document_positions",
            "pilot_document_position_domain_sha256",
            "pilot_annotation_raw_byte_count",
            "pilot_census",
            "nonauthority_statement",
            "status",
        }
    ),
    "sweeps": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_corpus_identity",
            "document_positions_swept",
            "document_count",
            "role_exact_label_class_rows",
            "role_exact_label_class_count",
            "role_exact_label_class_domain_sha256",
            "role_anchor_count",
            "role_noncanonical_assignment_reach_count",
            "role_cross_classification_label_count",
            "role_unreached_anchor_rows",
            "role_unreached_anchor_count",
            "outside_domain_repeat_shape_rows",
            "outside_domain_repeat_shape_count",
            "outside_domain_repeat_shape_domain_sha256",
            "noncatalog_aggregate_relation_shape_rows",
            "noncatalog_aggregate_relation_shape_count",
            "noncatalog_aggregate_relation_shape_keyset_sha256",
            "noncatalog_aggregate_relation_shape_domain_sha256",
            "in_domain_redirection_shape_rows",
            "in_domain_redirection_shape_count",
            "in_domain_redirection_shape_keyset_sha256",
            "in_domain_redirection_shape_domain_sha256",
            "explicit_cross_reference_evidence_count",
            "explicit_cross_reference_instruction_count",
            "complete_cross_reference_evidence_count",
            "complete_cross_reference_instruction_count",
            "in_domain_nonaggregate_cross_reference_evidence_count",
            "in_domain_nonaggregate_cross_reference_instruction_count",
            "wholly_in_domain_nonaggregate_cross_reference_evidence_count",
            "wholly_in_domain_nonaggregate_cross_reference_instruction_count",
            "component_cross_reference_evidence_count",
            "component_cross_reference_instruction_count",
            "binary_component_cross_reference_evidence_count",
            "binary_component_cross_reference_instruction_count",
            "in_domain_component_cross_reference_sweep_rows",
            "in_domain_component_cross_reference_sweep_count",
            "in_domain_component_cross_reference_sweep_edge_count",
            "in_domain_component_cross_reference_sweep_keyset_sha256",
            "in_domain_component_cross_reference_sweep_domain_sha256",
            "semantic_alias_adjudication_count",
            "semantic_alias_adjudication_keyset_sha256",
            "semantic_alias_adjudication_domain_sha256",
            "alias_semantic_input_identity_rows",
            "alias_semantic_input_identity_count",
            "alias_semantic_input_identity_domain_sha256",
            "alias_evidence_semantic_adjudication_rows",
            "alias_evidence_semantic_adjudication_count",
            "ca41663_alias_evidence_adjudication_count",
            "round_five_continuation_restoration_count",
            "continuation_composition_citation_count",
            "alias_evidence_semantic_adjudication_keyset_sha256",
            "alias_evidence_semantic_adjudication_domain_sha256",
            "alias_evidence_semantic_decision_counts",
            "alias_evidence_semantic_candidate_origin_counts",
            "approved_alias_evidence_count",
            "disclosed_stop_alias_evidence_count",
            "approved_alias_pair_rows",
            "approved_alias_pair_count",
            "approved_alias_pair_keyset_sha256",
            "approved_alias_pair_domain_sha256",
            "occurrence_closure_alias_pair_count",
            "typed_projection_alias_pair_count",
            "semantic_alias_adjudication_outcome_counts",
            "semantic_alias_instruction_outcome_domain_sha256",
            "semantic_alias_equivalence_instruction_keyset_sha256",
            "semantic_alias_redirection_instruction_keyset_sha256",
            "semantic_alias_stop_instruction_keyset_sha256",
            "semantic_alias_source_instruction_fragment_count",
            "semantic_alias_fragment_seal_quality_issue_count",
            "semantic_alias_round_three_fragment_reseal_count",
            "semantic_alias_round_four_new_fragment_reseal_count",
            "semantic_alias_decisive_fragment_no_reseal_count",
            "semantic_alias_fragment_instruction_keyset_sha256",
            "semantic_alias_round_four_new_fragment_keyset_sha256",
            "in_domain_component_cross_reference_sweep_alias_instruction_count",
            "in_domain_component_cross_reference_sweep_alias_edge_count",
            "in_domain_component_cross_reference_sweep_alias_pair_count",
            "in_domain_component_cross_reference_sweep_redirection_instruction_count",
            "in_domain_component_cross_reference_sweep_redirection_edge_count",
            "in_domain_component_cross_reference_sweep_stop_instruction_count",
            "in_domain_component_cross_reference_sweep_stop_edge_count",
            "pilot_in_domain_component_cross_reference_sweep_count",
            "pilot_in_domain_component_cross_reference_sweep_edge_count",
            "pilot_in_domain_component_cross_reference_sweep_alias_instruction_count",
            "pilot_in_domain_component_cross_reference_sweep_alias_edge_count",
            "pilot_in_domain_component_cross_reference_sweep_alias_pair_count",
            "pilot_in_domain_component_cross_reference_sweep_redirection_instruction_count",
            "pilot_in_domain_component_cross_reference_sweep_redirection_edge_count",
            "pilot_in_domain_component_cross_reference_sweep_stop_instruction_count",
            "pilot_in_domain_component_cross_reference_sweep_stop_edge_count",
            "repeat_instruction_text_scan_count",
            "literal_cross_reference_instruction_count",
            "exclusive_destination_redirection_lineage_rows",
            "exclusive_destination_redirection_lineage_count",
            "exclusive_destination_redirection_lineage_keyset_sha256",
            "exclusive_destination_redirection_lineage_domain_sha256",
            "exclusive_destination_redirection_lineage_admitted_count",
            "exclusive_destination_redirection_lineage_aggregate_count",
            "exclusive_destination_redirection_lineage_stop_count",
            "exclusive_destination_redirection_lineage_mixed_stop_count",
            "exclusive_destination_redirection_lineage_incomplete_stop_count",
            "repeat_coverage_census",
            "component_parent_shape_rows",
            "component_parent_shape_count",
            "component_parent_shape_keyset_sha256",
            "component_parent_shape_domain_sha256",
            "parent_source_witness_rows",
            "parent_source_witness_count",
            "parent_source_witness_keyset_sha256",
            "parent_source_witness_domain_sha256",
            "serialized_parent_cardinality_counts",
            "component_parent_disposition_counts",
            "raw_cross_category_multi_parent_count",
            "eligible_cross_category_multi_parent_count",
            "eligible_ineligible_mixed_multi_parent_count",
            "ineligible_parent_reference_count",
            "nonauthority_statement",
            "status",
        }
    ),
    "derived": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_corpus_identity",
            "corpus_sweep_artifact_id",
            "predecessor_artifact_id",
            "predecessor_seal_defect_count",
            "round_four_new_fragment_seal_quality_issue_count",
            "tier_2_predecessor_seal_quality_issue_count",
            "predecessor_reseal_required",
            "component_class_admission_sweep_rows",
            "component_class_admission_sweep_count",
            "component_class_member_occurrence_count",
            "component_class_admission_sweep_keyset_sha256",
            "component_class_admission_sweep_domain_sha256",
            "component_class_candidate_disposition_counts",
            "component_class_relationship_arm_eligible_count",
            "component_alias_support_origin_counts",
            "catalog_only_job_complement_sweep_rows",
            "catalog_only_job_complement_sweep_count",
            "job_class_member_occurrence_count",
            "catalog_only_job_complement_sweep_keyset_sha256",
            "catalog_only_job_complement_sweep_domain_sha256",
            "catalog_only_job_coverage_arm_counts",
            "job_alias_support_origin_counts",
            "nonauthority_statement",
            "status",
        }
    ),
    "predecessor": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_corpus_identity",
            "semantic_alias_sweep_artifact_id",
            "doc036_aggregate_component_slot_rows",
            "doc036_aggregate_component_slot_count",
            "doc036_aggregate_component_slot_domain_sha256",
            "populated_local_proof_adjudication_rows",
            "populated_local_proof_adjudication_count",
            "populated_local_proof_adjudication_keyset_sha256",
            "populated_local_proof_adjudication_domain_sha256",
            "populated_local_proof_seal_defect_count",
            "populated_local_proof_law_gap_count",
            "source_flag_counts",
            "seal_defect_flag_counts",
            "seal_defect_disposition_count",
            "law_gap_disposition_count",
            "in_domain_nonalias_law_gap_repair_count",
            "in_domain_nonalias_law_gap_subkind_counts",
            "round_four_new_fragment_seal_quality_issue_count",
            "round_four_new_fragment_instruction_keyset_sha256",
            "tier_2_predecessor_seal_quality_issue_count",
            "tier_2_precondition",
            "adjudication_rule",
            "nonauthority_statement",
            "status",
        }
    ),
    "role": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_slice_artifact_id",
            "corpus_sweep_artifact_id",
            "canonical_role_occurrence_ids",
            "role_label_class_rows",
            "role_label_class_count",
            "role_label_class_domain_sha256",
            "role_assignment_rows",
            "role_assignment_count",
            "role_assignment_keyset_sha256",
            "role_assignment_domain_sha256",
            "unassigned_role_anchor_rows",
            "unassigned_role_anchor_count",
            "nonauthority_statement",
            "status",
        }
    ),
    "repeat": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_slice_artifact_id",
            "corpus_sweep_artifact_id",
            "outside_domain_repeat_disposition_rows",
            "outside_domain_repeat_disposition_count",
            "outside_domain_repeat_disposition_keyset_sha256",
            "outside_domain_repeat_disposition_domain_sha256",
            "outside_domain_relation_counts",
            "outside_domain_document_counts",
            "noncatalog_aggregate_relation_disposition_rows",
            "noncatalog_aggregate_relation_disposition_count",
            "noncatalog_aggregate_relation_disposition_keyset_sha256",
            "noncatalog_aggregate_relation_disposition_domain_sha256",
            "aggregate_relation_counts",
            "aggregate_document_counts",
            "aggregate_handoff_status_counts",
            "in_domain_redirection_disposition_rows",
            "in_domain_redirection_disposition_count",
            "in_domain_redirection_disposition_keyset_sha256",
            "in_domain_redirection_disposition_domain_sha256",
            "redirection_relation_counts",
            "redirection_document_counts",
            "redirection_handoff_status_counts",
            "nonauthority_statement",
            "status",
        }
    ),
    "component": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_slice_artifact_id",
            "corpus_sweep_artifact_id",
            "zero_parent_disposition_rows",
            "zero_parent_disposition_count",
            "zero_parent_disposition_domain_sha256",
            "unique_parent_assignment_rows",
            "unique_parent_assignment_count",
            "unique_parent_assignment_domain_sha256",
            "multi_parent_ambiguity_rows",
            "multi_parent_ambiguity_count",
            "multi_parent_ambiguity_domain_sha256",
            "complete_component_resolution_count",
            "complete_component_resolution_keyset_sha256",
            "complete_component_resolution_domain_sha256",
            "serialized_parent_cardinality_counts",
            "raw_cross_category_multi_parent_count",
            "eligible_cross_category_multi_parent_count",
            "eligible_ineligible_mixed_multi_parent_count",
            "ineligible_parent_reference_count",
            "nonauthority_statement",
            "status",
        }
    ),
    "gate": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "design_prefix_identity",
            "source_slice_artifact_id",
            "artifact_identity_rows",
            "artifact_identity_count",
            "artifact_identity_domain_sha256",
            "pilot_census",
            "role_law_status",
            "four_disposition_repeat_law_status",
            "component_parent_law_status",
            "predecessor_input_status",
            "overall_repeat_catalog_coverage_status",
            "pilot_law_shape_status",
            "tier_2_protocol_status",
            "certification_status",
            "nonauthority_statement",
            "status",
        }
    ),
}

PILOT_DOCUMENT_ROW_KEYS = frozenset(
    {
        "document_source_position",
        "era_id",
        "annotation_path",
        "source_document_id",
        "schema_version",
        "annotation_byte_size",
        "annotation_raw_sha256",
        "annotation_content_sha256",
        "pilot_role",
        "selection_tags",
    }
)
ROLE_CLASS_ROW_KEYS = frozenset(
    {
        "role_label_class_id",
        "role",
        "exact_label",
        "exact_label_sha256",
        "member_occurrence_ids",
        "member_count",
        "member_keyset_sha256",
        "occurrence_equivalence_claimed",
        "alias_class_claimed",
        "status",
    }
)
ROLE_ASSIGNMENT_ROW_KEYS = frozenset(
    {
        "role_assignment_id",
        "document_source_position",
        "source_document_id",
        "source_classification_id",
        "role_anchor_occurrence_id",
        "assigned_role",
        "printed_identifier",
        "exact_label",
        "exact_label_sha256",
        "role_label_class_id",
        "proof_form",
        "alias_admitted_by_assignment",
        "occurrence_equivalence_claimed",
        "status",
    }
)
OUTSIDE_REPEAT_ROW_KEYS = frozenset(
    {
        "outside_domain_repeat_disposition_id",
        "document_source_position",
        "source_document_id",
        "source_local_evidence_id",
        "source_instruction_occurrence_id",
        "relation",
        "handoff_status",
        "evidence_occurrence_ids",
        "unresolved_target_reference",
        "terminal_disposition",
        "alias_anchor_occurrence_id",
        "referenced_anchor_occurrence_id",
        "alias_admitted",
        "occurrence_equivalence_claimed",
        "universal_repeat_coverage_arm_satisfied",
        "status",
    }
)
NONCATALOG_AGGREGATE_RELATION_ROW_KEYS = frozenset(
    {
        "noncatalog_aggregate_relation_disposition_id",
        "document_source_position",
        "source_document_id",
        "source_local_evidence_id",
        "source_instruction_occurrence_ids",
        "source_instruction_occurrence_kinds",
        "source_instruction_matched_texts",
        "source_instruction_matched_utf8_sha256s",
        "source_instruction_page_numbers",
        "source_instruction_utf8_byte_starts",
        "source_instruction_utf8_byte_ends",
        "relation",
        "handoff_status",
        "evidence_occurrence_ids",
        "source_alias_anchor_occurrence_ids",
        "source_canonical_anchor_occurrence_ids",
        "endpoint_occurrence_kinds",
        "endpoint_raw_node_domains",
        "endpoint_classifications",
        "endpoint_matched_texts",
        "endpoint_matched_utf8_sha256s",
        "endpoint_page_numbers",
        "endpoint_utf8_byte_starts",
        "endpoint_utf8_byte_ends",
        "aggregate_relation_disposition",
        "alias_admitted",
        "occurrence_equivalence_claimed",
        "universal_repeat_coverage_arm_satisfied",
        "status",
    }
)
IN_DOMAIN_REDIRECTION_ROW_KEYS = frozenset(
    {
        "in_domain_redirection_relation_disposition_id",
        "document_source_position",
        "source_document_id",
        "source_local_evidence_ids",
        "relation_subkind",
        "relation",
        "handoff_status",
        "source_instruction_occurrence_ids",
        "source_instruction_occurrence_kinds",
        "source_instruction_matched_texts",
        "source_instruction_matched_utf8_sha256s",
        "source_instruction_page_numbers",
        "source_instruction_utf8_byte_starts",
        "source_instruction_utf8_byte_ends",
        "source_evidence_occurrence_id_arrays",
        "evidence_occurrence_ids",
        "predecessor_alias_anchor_occurrence_ids",
        "predecessor_canonical_anchor_occurrence_ids",
        "current_location_occurrence_id",
        "destination_occurrence_ids",
        "endpoint_occurrence_kinds",
        "endpoint_raw_node_domains",
        "endpoint_classifications",
        "endpoint_printed_identifiers",
        "endpoint_matched_texts",
        "endpoint_matched_utf8_sha256s",
        "endpoint_page_numbers",
        "endpoint_utf8_byte_starts",
        "endpoint_utf8_byte_ends",
        "redirection_instruction_semantics",
        "redirection_relation_disposition",
        "alias_admitted",
        "occurrence_equivalence_claimed",
        "universal_repeat_coverage_arm_satisfied",
        "status",
    }
)
IN_DOMAIN_COMPONENT_CROSS_REFERENCE_SWEEP_ROW_KEYS = frozenset(
    {
        "in_domain_component_cross_reference_sweep_id",
        "document_source_position",
        "source_document_id",
        "source_instruction_occurrence_id",
        "source_instruction_occurrence_kind",
        "source_instruction_matched_text",
        "source_instruction_matched_utf8_sha256",
        "source_instruction_page_number",
        "source_instruction_utf8_byte_start",
        "source_instruction_utf8_byte_end",
        "source_local_evidence_ids",
        "source_evidence_count",
        "source_relations",
        "source_handoff_statuses",
        "source_evidence_occurrence_id_arrays",
        "source_alias_anchor_occurrence_id_arrays",
        "source_canonical_anchor_occurrence_id_arrays",
        "source_endpoint_occurrence_kind_arrays",
        "source_endpoint_raw_node_domain_arrays",
        "source_endpoint_classification_arrays",
        "source_endpoint_printed_identifier_arrays",
        "source_endpoint_matched_text_arrays",
        "source_endpoint_matched_utf8_sha256_arrays",
        "source_endpoint_page_number_arrays",
        "source_endpoint_utf8_byte_start_arrays",
        "source_endpoint_utf8_byte_end_arrays",
        "source_defect_flag_rows",
        "source_unresolved_target_references",
        "current_location_occurrence_id",
        "destination_occurrence_ids",
        "structural_candidate_satisfied",
        "pilot_document_member",
        "semantic_alias_adjudication_id",
        "semantic_alias_adjudication_round",
        "semantic_alias_ledger_member",
        "semantic_alias_finding",
        "named_instruction_import_or_occurrence_equivalence_proved",
        "occurrence_equivalence_proved",
        "pairwise_decomposition_required",
        "approved_pair_count",
        "rejected_source_local_evidence_ids",
        "continuation_composition_citation",
        "source_instruction_fragment",
        "tier_2_predecessor_seal_quality_issue",
        "tier_2_predecessor_ledger_note",
        "semantic_redirection_ledger_member",
        "semantic_redirection_finding",
        "valid_alias_arm_evidence_ids",
        "in_domain_redirection_relation_disposition_id",
        "repeat_coverage_disposition",
        "status",
    }
)
EXCLUSIVE_DESTINATION_REDIRECTION_LINEAGE_ROW_KEYS = frozenset(
    {
        "exclusive_destination_redirection_lineage_id",
        "document_source_position",
        "source_document_id",
        "source_instruction_occurrence_id",
        "source_instruction_matched_text",
        "source_instruction_matched_utf8_sha256",
        "source_instruction_page_number",
        "source_instruction_utf8_byte_start",
        "source_instruction_utf8_byte_end",
        "source_text_shape_kind",
        "source_local_evidence_ids",
        "source_relations",
        "source_handoff_statuses",
        "source_alias_anchor_occurrence_id_arrays",
        "source_canonical_anchor_occurrence_id_arrays",
        "source_endpoint_occurrence_kind_arrays",
        "source_endpoint_raw_node_domain_arrays",
        "source_endpoint_classification_arrays",
        "source_endpoint_printed_identifier_arrays",
        "source_unresolved_target_references",
        "in_domain_redirection_arm_eligible",
        "in_domain_redirection_relation_disposition_id",
        "existing_aggregate_relation_disposition_id",
        "lineage_disposition",
        "status",
    }
)
PARENT_CANDIDATE_ROW_KEYS = frozenset(
    {
        "parent_occurrence_id",
        "parent_occurrence_kind",
        "parent_category",
        "eligible_parent",
        "derived_slot_kind",
        "ineligibility_reason",
    }
)
COMPONENT_SHAPE_ROW_KEYS = frozenset(
    {
        "component_parent_resolution_id",
        "document_source_position",
        "source_document_id",
        "source_classification_id",
        "component_anchor_occurrence_id",
        "component_kind",
        "serialized_parent_cardinality",
        "eligible_parent_cardinality",
        "parent_candidate_rows",
        "parent_candidate_count",
        "parent_candidate_domain_sha256",
        "raw_parent_category_ambiguity",
        "eligible_parent_category_ambiguity",
        "eligible_ineligible_mixed_ambiguity",
        "disposition",
        "forced_parent_selection",
        "tier_2_unique_parent_arm_eligible",
        "r_q_relationship_emitted",
        "status",
    }
)
COMPONENT_CLASS_ADMISSION_SWEEP_ROW_KEYS = frozenset(
    {
        "component_class_admission_sweep_id",
        "candidate_component_class_id",
        "canonical_component_occurrence_id",
        "component_class_member_occurrence_ids",
        "component_class_member_count",
        "component_kind",
        "member_raw_parent_cardinalities",
        "raw_parent_candidate_count",
        "eligible_canonical_parent_count",
        "candidate_disposition",
        "candidate_unique_parent_node_id",
        "candidate_unique_slot_kind",
        "relationship_arm_eligible",
        "r_q_relationship_emitted",
        "alias_support_rows",
        "alias_support_count",
        "alias_support_domain_sha256",
        "predecessor_reseal_required",
        "status",
    }
)
ALIAS_SUPPORT_ROW_KEYS = frozenset(
    {
        "alias_support_proof_id",
        "support_origin",
        "relation",
        "member_occurrence_ids",
        "alias_anchor_occurrence_ids",
        "canonical_anchor_occurrence_ids",
        "source_local_evidence_id",
        "semantic_alias_pair_adjudication_id",
        "pairing_basis_code",
        "printed_identifier",
        "exact_label",
        "evidence_occurrence_ids",
    }
)
ALIAS_SEMANTIC_INPUT_IDENTITY_ROW_KEYS = frozenset(
    {"path", "byte_size", "raw_sha256"}
)
ALIAS_EVIDENCE_SEMANTIC_ADJUDICATION_ROW_KEYS = frozenset(
    {
        "semantic_alias_evidence_adjudication_id",
        "document_source_position",
        "source_document_id",
        "source_local_evidence_id",
        "candidate_origin",
        "ca41663_admitted_alias_evidence",
        "round_five_continuation_restoration",
        "structural_filter_satisfied",
        "relation",
        "handoff_status",
        "source_instruction_occurrence_ids",
        "source_instruction_matched_texts",
        "source_instruction_matched_utf8_sha256s",
        "source_instruction_page_numbers",
        "source_instruction_utf8_byte_starts",
        "source_instruction_utf8_byte_ends",
        "alias_anchor_occurrence_ids",
        "canonical_anchor_occurrence_ids",
        "evidence_occurrence_ids",
        "endpoint_matched_texts",
        "endpoint_matched_utf8_sha256s",
        "endpoint_page_numbers",
        "endpoint_utf8_byte_starts",
        "endpoint_utf8_byte_ends",
        "semantic_adjudication_round",
        "semantic_finding",
        "decision",
        "approved_pair_rows",
        "approved_pair_count",
        "continuation_composition_citation",
        "composite_stop_citation",
        "status",
    }
)
ALIAS_SEMANTIC_PAIR_ROW_KEYS = frozenset(
    {
        "semantic_alias_pair_adjudication_id",
        "source_local_evidence_id",
        "pair_ordinal",
        "pair_kind",
        "pairing_basis_code",
        "semantic_type",
        "alias_occurrence_id",
        "canonical_occurrence_id",
        "alias_question_selector",
        "canonical_question_selector",
        "exact_pairing_citation",
        "composite_typed_projection_pair_id",
        "alias_endpoint_matched_text",
        "alias_endpoint_matched_utf8_sha256",
        "alias_endpoint_page_number",
        "alias_endpoint_utf8_byte_start",
        "alias_endpoint_utf8_byte_end",
        "canonical_endpoint_matched_text",
        "canonical_endpoint_matched_utf8_sha256",
        "canonical_endpoint_page_number",
        "canonical_endpoint_utf8_byte_start",
        "canonical_endpoint_utf8_byte_end",
        "source_instruction_occurrence_ids",
        "source_instruction_matched_texts",
        "source_instruction_matched_utf8_sha256s",
        "source_instruction_page_numbers",
        "source_instruction_utf8_byte_starts",
        "source_instruction_utf8_byte_ends",
        "class_closure_eligible",
        "typed_projection_union_prohibited",
        "status",
    }
)
CATALOG_ONLY_JOB_COMPLEMENT_SWEEP_ROW_KEYS = frozenset(
    {
        "catalog_only_job_complement_sweep_id",
        "candidate_job_class_id",
        "canonical_job_occurrence_id",
        "job_class_member_occurrence_ids",
        "job_class_member_count",
        "candidate_relationship_component_class_ids",
        "candidate_relationship_count",
        "catalog_only_disposition_required",
        "coverage_arm",
        "catalog_only_disposition_emitted",
        "alias_support_rows",
        "alias_support_count",
        "alias_support_domain_sha256",
        "predecessor_reseal_required",
        "status",
    }
)
DOC036_DEFECT_ROW_KEYS = frozenset(
    {
        "predecessor_adjudication_id",
        "document_source_position",
        "source_document_id",
        "source_classification_id",
        "source_occurrence_id",
        "source_occurrence_matched_text",
        "source_occurrence_matched_utf8_sha256",
        "source_occurrence_page_number",
        "source_occurrence_utf8_byte_start",
        "source_occurrence_utf8_byte_end",
        "source_classification",
        "occurrence_kind",
        "serialized_node_domain",
        "correct_node_domain",
        "disposition",
        "law_gap_admitted",
        "component_slot_admitted",
        "semantic_adjudication_round",
        "source_text_citation_status",
        "required_action",
        "adjudicative_rationale",
        "row_specific_semantic_finding",
        "status",
    }
)
PROOF_ADJUDICATION_ROW_KEYS = frozenset(
    {
        "predecessor_adjudication_id",
        "document_source_position",
        "source_document_id",
        "source_local_evidence_id",
        "relation",
        "source_instruction_occurrence_ids",
        "source_instruction_matched_texts",
        "source_instruction_matched_utf8_sha256s",
        "source_instruction_page_numbers",
        "source_instruction_utf8_byte_starts",
        "source_instruction_utf8_byte_ends",
        "alias_anchor_occurrence_ids",
        "canonical_anchor_occurrence_ids",
        "evidence_occurrence_ids",
        "endpoint_occurrence_kinds",
        "endpoint_raw_node_domains",
        "endpoint_classifications",
        "endpoint_printed_identifiers",
        "endpoint_matched_texts",
        "endpoint_matched_utf8_sha256s",
        "endpoint_page_numbers",
        "endpoint_utf8_byte_starts",
        "endpoint_utf8_byte_ends",
        "defect_flags",
        "semantic_adjudication_round",
        "source_text_citation_status",
        "in_domain_nonalias_relation_arm_eligible",
        "in_domain_nonalias_relation_subkind",
        "disposition",
        "law_gap_admitted",
        "alias_admitted",
        "required_action",
        "adjudicative_rationale",
        "row_specific_semantic_finding",
        "status",
    }
)
ARTIFACT_IDENTITY_ROW_KEYS = frozenset(
    {
        "artifact_role",
        "path",
        "schema_version",
        "artifact_id",
        "byte_size",
        "raw_sha256",
    }
)

PARENT_SOURCE_WITNESS_ROW_KEYS = frozenset(
    {
        "parent_source_witness_id",
        "document_source_position",
        "source_document_id",
        "source_classification_id",
        "parent_occurrence_id",
        "parent_occurrence_kind",
        "parent_classification",
        "status",
    }
)
UNRESOLVED_TARGET_REFERENCE_KEYS = frozenset(
    {
        "matched_text",
        "matched_utf8_sha256",
        "page_number",
        "utf8_byte_start",
        "utf8_byte_end",
    }
)
DEFECT_FLAG_KEYS = frozenset(
    {
        "touches_noncatalog_aggregate_endpoint",
        "occurrence_derived_domain_crossing",
        "corrected_catalog_domain_crossing",
        "raw_node_domain_crossing",
        "context_remuneration_mix",
        "head_spouse_mix",
    }
)
DESIGN_PREFIX_IDENTITY_KEYS = frozenset(
    {"path", "byte_size", "sha256", "identity_scope"}
)
SOURCE_CORPUS_IDENTITY_KEYS = frozenset(
    {
        "source_branch_label",
        "source_commit",
        "document_count",
        "stage2_protocol_identity",
        "era_seal_rows",
        "era_seal_count",
        "era_seal_domain_sha256",
    }
)
STAGE2_PROTOCOL_IDENTITY_KEYS = frozenset({"path", "byte_size", "raw_sha256"})
ERA_SEAL_IDENTITY_ROW_KEYS = frozenset(
    {
        "era_id",
        "era_order_position",
        "document_source_positions",
        "seal_commit",
        "path",
        "byte_size",
        "raw_sha256",
        "content_sha256",
    }
)


def _validate_nonauthority(value: Any) -> None:
    _require(value == _nonauthority_statement(), "nonauthority drift")


def _validate_source_corpus_identity(value: Mapping[str, Any]) -> None:
    label = "source corpus identity"
    _require_exact_keys(value, SOURCE_CORPUS_IDENTITY_KEYS, label)
    _require(
        value["source_branch_label"] == SOURCE_BRANCH_LABEL, f"{label}: branch"
    )
    _require(value["source_commit"] == SOURCE_COMMIT, f"{label}: commit")
    _require(value["document_count"] == 81, f"{label}: document count")
    protocol = value["stage2_protocol_identity"]
    _require(isinstance(protocol, dict), f"{label}: protocol")
    _require_exact_keys(
        protocol, STAGE2_PROTOCOL_IDENTITY_KEYS, f"{label}: protocol"
    )
    _require(
        protocol
        == {
            "path": "docs/analysis/rq_stage2_protocol.md",
            "byte_size": 59_048,
            "raw_sha256": (
                "313234c381045f155b0acf9e0b35fd7818aa60e905e1a9934d2c4b5bec816bd7"
            ),
        },
        f"{label}: protocol identity",
    )
    seal_rows = value["era_seal_rows"]
    _require(isinstance(seal_rows, list), f"{label}: era seals")
    _require(
        value["era_seal_count"] == len(seal_rows) == 6, f"{label}: seal count"
    )
    _require(
        value["era_seal_domain_sha256"] == _domain_sha(seal_rows),
        f"{label}: seal digest",
    )
    for row, expected in zip(seal_rows, ERA_SEALS, strict=True):
        _require_exact_keys(
            row, ERA_SEAL_IDENTITY_ROW_KEYS, f"{label}: era seal"
        )
        expected_row = {
            "era_id": expected["era_id"],
            "era_order_position": expected["era_order_position"],
            "document_source_positions": list(expected["positions"]),
            "seal_commit": expected["seal_commit"],
            "path": expected["path"],
            "byte_size": expected["byte_size"],
            "raw_sha256": expected["raw_sha256"],
            "content_sha256": expected["content_sha256"],
        }
        _require(row == expected_row, f"{label}: era seal identity")


def _validate_row_digests(
    artifact: Mapping[str, Any],
    row_key: str,
    count_key: str,
    domain_key: str,
) -> list[dict[str, Any]]:
    rows = artifact[row_key]
    _require(isinstance(rows, list), f"{row_key}: not array")
    count = _require_int(artifact[count_key], count_key)
    _require(count == len(rows), f"{count_key}: drift")
    _require(artifact[domain_key] == _domain_sha(rows), f"{domain_key}: drift")
    return rows


def _require_string(value: Any, label: str) -> str:
    _require(
        isinstance(value, str) and value != "", f"{label}: expected string"
    )
    return value


def _require_boolean(value: Any, label: str) -> bool:
    _require(isinstance(value, bool), f"{label}: expected boolean")
    return value


def _validate_role_class_row(row: Mapping[str, Any], label: str) -> None:
    _require_exact_keys(row, ROLE_CLASS_ROW_KEYS, label)
    role = row["role"]
    _require(role in ROLE_ORDER, f"{label}: unknown role")
    exact_label = _require_string(row["exact_label"], f"{label}: exact label")
    label_sha = _sha256(exact_label.encode("utf-8"))
    _require(row["exact_label_sha256"] == label_sha, f"{label}: label digest")
    _require(
        row["role_label_class_id"]
        == _row_id("a12-role-exact-label-class:", [role, label_sha]),
        f"{label}: class ID",
    )
    members = row["member_occurrence_ids"]
    _require(isinstance(members, list) and members, f"{label}: empty members")
    _require(
        all(
            isinstance(value, str)
            and value.startswith("psid-questionnaire-occurrence:")
            for value in members
        ),
        f"{label}: invalid member ID",
    )
    _require(len(set(members)) == len(members), f"{label}: duplicate member")
    _require_int(row["member_count"], f"{label}: member count")
    _require(row["member_count"] == len(members), f"{label}: member count")
    _require(
        row["member_keyset_sha256"] == _keyset_sha(members),
        f"{label}: member digest",
    )
    _require(
        row["occurrence_equivalence_claimed"] is False,
        f"{label}: occurrence equivalence claimed",
    )
    _require(
        row["alias_class_claimed"] is False,
        f"{label}: alias class claimed",
    )
    _require(
        row["status"] == "role_membership_class_only",
        f"{label}: status",
    )


def _validate_role_assignment_row(
    row: Mapping[str, Any],
    class_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    label = "role assignment row"
    _require_exact_keys(row, ROLE_ASSIGNMENT_ROW_KEYS, label)
    role = row["assigned_role"]
    _require(role in ROLE_ORDER, f"{label}: unknown assigned role")
    class_id = row["role_label_class_id"]
    _require(class_id in class_by_id, f"{label}: dangling role class")
    class_row = class_by_id[class_id]
    _require(
        role == class_row["role"], f"{label}: assigned role/class mismatch"
    )
    _require(
        row["exact_label"] == class_row["exact_label"],
        f"{label}: exact label/class mismatch",
    )
    _require(
        row["exact_label_sha256"] == class_row["exact_label_sha256"],
        f"{label}: label digest/class mismatch",
    )
    occurrence_id = _require_string(
        row["role_anchor_occurrence_id"], f"{label}: occurrence ID"
    )
    _require(
        occurrence_id in class_row["member_occurrence_ids"],
        f"{label}: occurrence absent from role class",
    )
    _require(
        row["proof_form"] == "exact_label_class_role_assignment_non_alias",
        f"{label}: proof form",
    )
    _require(
        row["alias_admitted_by_assignment"] is False,
        f"{label}: alias admitted",
    )
    _require(
        row["occurrence_equivalence_claimed"] is False,
        f"{label}: occurrence equivalence claimed",
    )
    _require(
        row["status"] == "assigned_noncanonical_role_anchor",
        f"{label}: status",
    )
    _require(
        row["role_assignment_id"]
        == _row_id(
            "a12-pilot-role-assignment:",
            [
                row["source_document_id"],
                occurrence_id,
                role,
                class_id,
                row["proof_form"],
            ],
        ),
        f"{label}: assignment ID",
    )
    printed_identifier = row["printed_identifier"]
    _require(
        printed_identifier is None or isinstance(printed_identifier, str),
        f"{label}: printed identifier",
    )


def _validate_outside_repeat_row(row: Mapping[str, Any], label: str) -> None:
    _require_exact_keys(row, OUTSIDE_REPEAT_ROW_KEYS, label)
    instruction_id = _require_string(
        row["source_instruction_occurrence_id"], f"{label}: instruction"
    )
    _require(row["relation"] in ALLOWED_REPEAT_RELATIONS, f"{label}: relation")
    _require(
        row["handoff_status"] == "local_target_outside_rq_annotation_domain",
        f"{label}: handoff status",
    )
    _require(
        row["evidence_occurrence_ids"] == [instruction_id],
        f"{label}: evidence is not singleton self",
    )
    unresolved = row["unresolved_target_reference"]
    _require(isinstance(unresolved, dict), f"{label}: unresolved target")
    _require_exact_keys(
        unresolved,
        UNRESOLVED_TARGET_REFERENCE_KEYS,
        f"{label}: unresolved target",
    )
    matched_text = _require_string(
        unresolved["matched_text"], f"{label}: unresolved matched text"
    )
    _require(
        unresolved["matched_utf8_sha256"]
        == _sha256(matched_text.encode("utf-8")),
        f"{label}: unresolved text digest",
    )
    page_number = _require_int(unresolved["page_number"], f"{label}: page")
    byte_start = _require_int(
        unresolved["utf8_byte_start"], f"{label}: byte start"
    )
    byte_end = _require_int(unresolved["utf8_byte_end"], f"{label}: byte end")
    _require(page_number > 0 and 0 <= byte_start < byte_end, f"{label}: span")
    _require(
        byte_end - byte_start == len(matched_text.encode("utf-8")),
        f"{label}: span length",
    )
    _require(
        row["terminal_disposition"] == "outside_r_q_domain_no_alias_admitted",
        f"{label}: terminal disposition",
    )
    _require(row["alias_anchor_occurrence_id"] is None, f"{label}: alias")
    _require(
        row["referenced_anchor_occurrence_id"] is None,
        f"{label}: referenced anchor",
    )
    _require(row["alias_admitted"] is False, f"{label}: alias admitted")
    _require(
        row["occurrence_equivalence_claimed"] is False,
        f"{label}: occurrence equivalence claimed",
    )
    _require(
        row["universal_repeat_coverage_arm_satisfied"] is True,
        f"{label}: universal arm",
    )
    _require(
        row["status"] == "terminal_nonauthority_disposition",
        f"{label}: status",
    )
    _require(
        row["outside_domain_repeat_disposition_id"]
        == _row_id(
            "a12-outside-rq-repeat-disposition:",
            [
                row["source_document_id"],
                instruction_id,
                row["source_local_evidence_id"],
                row["relation"],
                unresolved,
            ],
        ),
        f"{label}: disposition ID",
    )


def _validate_noncatalog_aggregate_relation_row(
    row: Mapping[str, Any], label: str
) -> None:
    _require_exact_keys(row, NONCATALOG_AGGREGATE_RELATION_ROW_KEYS, label)
    _require_int(row["document_source_position"], f"{label}: position")
    _require_string(row["source_document_id"], f"{label}: source document")
    _require_string(
        row["source_local_evidence_id"], f"{label}: local evidence"
    )
    instructions = row["source_instruction_occurrence_ids"]
    instruction_kinds = row["source_instruction_occurrence_kinds"]
    aliases = row["source_alias_anchor_occurrence_ids"]
    canonicals = row["source_canonical_anchor_occurrence_ids"]
    endpoints = [*aliases, *canonicals]
    _require(
        isinstance(instructions, list)
        and len(instructions) == 1
        and instruction_kinds == ["repeat_or_alias_instruction"],
        f"{label}: singleton repeat instruction",
    )
    _require(
        isinstance(aliases, list)
        and aliases
        and isinstance(canonicals, list)
        and canonicals,
        f"{label}: populated endpoint sides",
    )
    _require(
        len(endpoints) == len(set(endpoints))
        and not set(aliases) & set(canonicals)
        and not set(instructions) & set(endpoints),
        f"{label}: endpoint or instruction disjointness",
    )
    evidence_ids = row["evidence_occurrence_ids"]
    _require(
        isinstance(evidence_ids, list)
        and len(evidence_ids) == len(endpoints) + 1
        and len(evidence_ids) == len(set(evidence_ids))
        and set(evidence_ids) == {*endpoints, *instructions},
        f"{label}: exact evidence cover",
    )
    _require(row["relation"] in ALLOWED_REPEAT_RELATIONS, f"{label}: relation")
    _require(
        row["handoff_status"] in COMPLETE_LOCAL_EVIDENCE_STATUSES,
        f"{label}: complete handoff",
    )
    endpoint_kinds = row["endpoint_occurrence_kinds"]
    endpoint_domains = row["endpoint_raw_node_domains"]
    endpoint_classifications = row["endpoint_classifications"]
    endpoint_projection_arrays = (
        endpoint_kinds,
        endpoint_domains,
        endpoint_classifications,
        row["endpoint_matched_texts"],
        row["endpoint_matched_utf8_sha256s"],
        row["endpoint_page_numbers"],
        row["endpoint_utf8_byte_starts"],
        row["endpoint_utf8_byte_ends"],
    )
    _require(
        all(
            isinstance(values, list) and len(values) == len(endpoints)
            for values in endpoint_projection_arrays
        ),
        f"{label}: endpoint projections",
    )
    _require(
        all(kind in AGGREGATE_OCCURRENCE_KINDS for kind in endpoint_kinds)
        and all(domain == "aggregate" for domain in endpoint_domains)
        and all(
            classification in AGGREGATE_KIND_TO_CLASSIFICATIONS[kind]
            for kind, classification in zip(
                endpoint_kinds, endpoint_classifications, strict=True
            )
        ),
        f"{label}: aggregate endpoint predicate",
    )
    byte_projection_groups = (
        (
            row["source_instruction_matched_texts"],
            row["source_instruction_matched_utf8_sha256s"],
            row["source_instruction_page_numbers"],
            row["source_instruction_utf8_byte_starts"],
            row["source_instruction_utf8_byte_ends"],
            1,
        ),
        (
            row["endpoint_matched_texts"],
            row["endpoint_matched_utf8_sha256s"],
            row["endpoint_page_numbers"],
            row["endpoint_utf8_byte_starts"],
            row["endpoint_utf8_byte_ends"],
            len(endpoints),
        ),
    )
    for (
        texts,
        digests,
        pages,
        starts,
        ends,
        expected_count,
    ) in byte_projection_groups:
        _require(
            all(
                isinstance(values, list) and len(values) == expected_count
                for values in (texts, digests, pages, starts, ends)
            ),
            f"{label}: exact-byte projection lengths",
        )
        for text, digest, page, start, end in zip(
            texts, digests, pages, starts, ends, strict=True
        ):
            _require_string(text, f"{label}: matched text")
            _require(
                digest == _sha256(text.encode("utf-8")),
                f"{label}: matched text digest",
            )
            _require(
                _require_int(page, f"{label}: page") > 0
                and 0 <= _require_int(start, f"{label}: byte start") < end
                and _require_int(end, f"{label}: byte end") - start
                == len(text.encode("utf-8")),
                f"{label}: exact byte span",
            )
    _require(
        row["aggregate_relation_disposition"]
        == "noncatalog_aggregate_or_repeated_instance_relation_no_alias",
        f"{label}: disposition",
    )
    _require(row["alias_admitted"] is False, f"{label}: alias admitted")
    _require(
        row["occurrence_equivalence_claimed"] is False,
        f"{label}: occurrence equivalence claimed",
    )
    _require(
        row["universal_repeat_coverage_arm_satisfied"] is True,
        f"{label}: universal arm",
    )
    _require(
        row["status"] == "aggregate_relation_nonauthority_disposition",
        f"{label}: status",
    )
    _require(
        row["noncatalog_aggregate_relation_disposition_id"]
        == _row_id(
            "a12-noncatalog-aggregate-relation-disposition:",
            [
                row["source_document_id"],
                row["source_local_evidence_id"],
                instructions,
                row["relation"],
                row["handoff_status"],
                aliases,
                canonicals,
                evidence_ids,
                row["endpoint_occurrence_kinds"],
                row["endpoint_raw_node_domains"],
                row["endpoint_classifications"],
                row["source_instruction_matched_texts"],
                row["source_instruction_matched_utf8_sha256s"],
                row["source_instruction_page_numbers"],
                row["source_instruction_utf8_byte_starts"],
                row["source_instruction_utf8_byte_ends"],
                row["endpoint_matched_texts"],
                row["endpoint_matched_utf8_sha256s"],
                row["endpoint_page_numbers"],
                row["endpoint_utf8_byte_starts"],
                row["endpoint_utf8_byte_ends"],
            ],
        ),
        f"{label}: disposition ID",
    )


def _validate_in_domain_redirection_row(
    row: Mapping[str, Any], label: str
) -> None:
    _require_exact_keys(row, IN_DOMAIN_REDIRECTION_ROW_KEYS, label)
    _require_int(row["document_source_position"], f"{label}: position")
    _require_string(row["source_document_id"], f"{label}: source document")
    source_evidence_ids = row["source_local_evidence_ids"]
    instructions = row["source_instruction_occurrence_ids"]
    aliases = row["predecessor_alias_anchor_occurrence_ids"]
    canonicals = row["predecessor_canonical_anchor_occurrence_ids"]
    _require(
        isinstance(instructions, list)
        and len(instructions) == 1
        and row["source_instruction_occurrence_kinds"]
        == ["repeat_or_alias_instruction"],
        f"{label}: singleton instruction",
    )
    instruction_id = instructions[0]
    expected_evidence_ids = (
        EXCLUSIVE_DESTINATION_REDIRECTION_EVIDENCE_BY_INSTRUCTION.get(
            instruction_id
        )
    )
    _require(
        isinstance(source_evidence_ids, list)
        and tuple(source_evidence_ids) == expected_evidence_ids
        and isinstance(aliases, list)
        and isinstance(canonicals, list)
        and len(aliases) == 1
        and canonicals
        and len(canonicals) == len(set(canonicals))
        and not set(aliases) & set(canonicals)
        and len(source_evidence_ids) == len(canonicals)
        and row["current_location_occurrence_id"] == aliases[0]
        and row["destination_occurrence_ids"] == canonicals,
        f"{label}: redirection endpoints",
    )
    source_evidence_arrays = row["source_evidence_occurrence_id_arrays"]
    evidence_ids = row["evidence_occurrence_ids"]
    _require(
        isinstance(source_evidence_arrays, list)
        and len(source_evidence_arrays) == len(source_evidence_ids)
        and all(
            isinstance(values, list)
            and len(values) == len(set(values)) == 3
            and set(values) == {instruction_id, aliases[0], destination_id}
            for values, destination_id in zip(
                source_evidence_arrays, canonicals, strict=True
            )
        )
        and isinstance(evidence_ids, list)
        and len(evidence_ids) == len(set(evidence_ids))
        and set(evidence_ids)
        == {
            occurrence_id
            for values in source_evidence_arrays
            for occurrence_id in values
        }
        == {instruction_id, *aliases, *canonicals},
        f"{label}: exact evidence cover",
    )
    _require(
        row["relation_subkind"] == REDIRECTION_RELATION_SUBKIND
        and row["relation"] == "explicit_cross_reference"
        and row["handoff_status"] in COMPLETE_LOCAL_EVIDENCE_STATUSES,
        f"{label}: relation identity",
    )
    endpoint_count = len(aliases) + len(canonicals)
    endpoint_arrays = (
        row["endpoint_occurrence_kinds"],
        row["endpoint_raw_node_domains"],
        row["endpoint_classifications"],
        row["endpoint_printed_identifiers"],
        row["endpoint_matched_texts"],
        row["endpoint_matched_utf8_sha256s"],
        row["endpoint_page_numbers"],
        row["endpoint_utf8_byte_starts"],
        row["endpoint_utf8_byte_ends"],
    )
    _require(
        all(
            isinstance(values, list) and len(values) == endpoint_count
            for values in endpoint_arrays
        )
        and row["endpoint_raw_node_domains"]
        == ["component_slot"] * endpoint_count
        and all(
            (kind, classification)
            in {
                ("context_anchor", "source_context"),
                (
                    "remuneration_component_anchor",
                    "source_remuneration_component",
                ),
            }
            for kind, classification in zip(
                row["endpoint_occurrence_kinds"],
                row["endpoint_classifications"],
                strict=True,
            )
        ),
        f"{label}: endpoint semantic projection",
    )
    identifiers = row["endpoint_printed_identifiers"]
    _require(
        isinstance(identifiers, list)
        and len(identifiers) == endpoint_count
        and all(
            value is None or isinstance(value, str) and value
            for value in identifiers
        ),
        f"{label}: endpoint printed identifiers",
    )
    _require(
        _exact_byte_projection(
            row["source_instruction_matched_texts"],
            row["source_instruction_matched_utf8_sha256s"],
            row["source_instruction_page_numbers"],
            row["source_instruction_utf8_byte_starts"],
            row["source_instruction_utf8_byte_ends"],
            1,
        )
        and _exact_byte_projection(
            row["endpoint_matched_texts"],
            row["endpoint_matched_utf8_sha256s"],
            row["endpoint_page_numbers"],
            row["endpoint_utf8_byte_starts"],
            row["endpoint_utf8_byte_ends"],
            endpoint_count,
        ),
        f"{label}: exact source projections",
    )
    _require(
        row["redirection_instruction_semantics"]
        == "affirmative_named_destination_and_explicit_current_location_"
        "exclusion"
        and row["redirection_relation_disposition"]
        == "authenticated_in_domain_exclusive_destination_relation_no_alias",
        f"{label}: redirection disposition",
    )
    _require(row["alias_admitted"] is False, f"{label}: alias admitted")
    _require(
        row["occurrence_equivalence_claimed"] is False,
        f"{label}: occurrence equivalence",
    )
    _require(
        row["universal_repeat_coverage_arm_satisfied"] is True,
        f"{label}: universal arm",
    )
    _require(
        row["status"] == "redirection_relation_nonauthority_disposition",
        f"{label}: status",
    )
    _require(
        row["in_domain_redirection_relation_disposition_id"]
        == _redirection_disposition_id(row),
        f"{label}: disposition ID",
    )


def _validate_in_domain_component_cross_reference_sweep_row(
    row: Mapping[str, Any], label: str
) -> None:
    _require_exact_keys(
        row, IN_DOMAIN_COMPONENT_CROSS_REFERENCE_SWEEP_ROW_KEYS, label
    )
    position = _require_int(
        row["document_source_position"], f"{label}: position"
    )
    _require(1 <= position <= 81, f"{label}: source position")
    _require_string(row["source_document_id"], f"{label}: source document")
    instruction_id = _require_string(
        row["source_instruction_occurrence_id"],
        f"{label}: source instruction",
    )
    _require(
        row["source_instruction_occurrence_kind"]
        == "repeat_or_alias_instruction",
        f"{label}: repeat instruction kind",
    )
    instruction_text = _require_string(
        row["source_instruction_matched_text"],
        f"{label}: instruction text",
    )
    _require(
        row["source_instruction_matched_utf8_sha256"]
        == _sha256(instruction_text.encode("utf-8")),
        f"{label}: instruction digest",
    )
    instruction_page = _require_int(
        row["source_instruction_page_number"],
        f"{label}: instruction page",
    )
    instruction_start = _require_int(
        row["source_instruction_utf8_byte_start"],
        f"{label}: instruction start",
    )
    instruction_end = _require_int(
        row["source_instruction_utf8_byte_end"],
        f"{label}: instruction end",
    )
    _require(
        instruction_page > 0
        and 0 <= instruction_start < instruction_end
        and instruction_end - instruction_start
        == len(instruction_text.encode("utf-8")),
        f"{label}: instruction byte projection",
    )

    evidence_ids = row["source_local_evidence_ids"]
    evidence_count = _require_int(
        row["source_evidence_count"], f"{label}: evidence count"
    )
    outer_array_keys = (
        "source_relations",
        "source_handoff_statuses",
        "source_evidence_occurrence_id_arrays",
        "source_alias_anchor_occurrence_id_arrays",
        "source_canonical_anchor_occurrence_id_arrays",
        "source_endpoint_occurrence_kind_arrays",
        "source_endpoint_raw_node_domain_arrays",
        "source_endpoint_classification_arrays",
        "source_endpoint_printed_identifier_arrays",
        "source_endpoint_matched_text_arrays",
        "source_endpoint_matched_utf8_sha256_arrays",
        "source_endpoint_page_number_arrays",
        "source_endpoint_utf8_byte_start_arrays",
        "source_endpoint_utf8_byte_end_arrays",
        "source_defect_flag_rows",
        "source_unresolved_target_references",
    )
    _require(
        evidence_count > 0
        and isinstance(evidence_ids, list)
        and len(evidence_ids) == len(set(evidence_ids)) == evidence_count
        and all(isinstance(value, str) and value for value in evidence_ids)
        and all(
            isinstance(row[key], list) and len(row[key]) == evidence_count
            for key in outer_array_keys
        ),
        f"{label}: parallel evidence projections",
    )
    _require(
        row["source_relations"]
        == ["explicit_cross_reference"] * evidence_count,
        f"{label}: explicit cross-reference relation",
    )
    handoffs = row["source_handoff_statuses"]
    _require(
        len(set(handoffs)) == 1
        and all(
            value in COMPLETE_LOCAL_EVIDENCE_STATUSES for value in handoffs
        ),
        f"{label}: complete consistent handoff",
    )
    _require(
        row["source_unresolved_target_references"] == [None] * evidence_count,
        f"{label}: unresolved target",
    )

    current_id = _require_string(
        row["current_location_occurrence_id"],
        f"{label}: current location",
    )
    destination_ids = row["destination_occurrence_ids"]
    alias_arrays = row["source_alias_anchor_occurrence_id_arrays"]
    canonical_arrays = row["source_canonical_anchor_occurrence_id_arrays"]
    _require(
        isinstance(destination_ids, list)
        and len(destination_ids) == len(set(destination_ids)) == evidence_count
        and all(isinstance(value, str) and value for value in destination_ids)
        and current_id not in set(destination_ids)
        and alias_arrays == [[current_id] for _ in range(evidence_count)]
        and canonical_arrays == [[value] for value in destination_ids],
        f"{label}: common current and unique destinations",
    )
    evidence_occurrence_arrays = row["source_evidence_occurrence_id_arrays"]
    _require(
        all(
            isinstance(values, list)
            and len(values) == len(set(values)) == 3
            and set(values) == {instruction_id, current_id, destination_id}
            for values, destination_id in zip(
                evidence_occurrence_arrays, destination_ids, strict=True
            )
        ),
        f"{label}: exact per-edge evidence cover",
    )

    endpoint_array_keys = (
        "source_endpoint_occurrence_kind_arrays",
        "source_endpoint_raw_node_domain_arrays",
        "source_endpoint_classification_arrays",
        "source_endpoint_printed_identifier_arrays",
        "source_endpoint_matched_text_arrays",
        "source_endpoint_matched_utf8_sha256_arrays",
        "source_endpoint_page_number_arrays",
        "source_endpoint_utf8_byte_start_arrays",
        "source_endpoint_utf8_byte_end_arrays",
    )
    _require(
        all(
            all(
                isinstance(values, list) and len(values) == 2
                for values in row[key]
            )
            for key in endpoint_array_keys
        ),
        f"{label}: binary endpoint projections",
    )
    allowed_endpoint_projections = {
        ("context_anchor", "source_context"),
        (
            "remuneration_component_anchor",
            "source_remuneration_component",
        ),
    }
    for edge_index in range(evidence_count):
        kinds = row["source_endpoint_occurrence_kind_arrays"][edge_index]
        domains = row["source_endpoint_raw_node_domain_arrays"][edge_index]
        classifications = row["source_endpoint_classification_arrays"][
            edge_index
        ]
        identifiers = row["source_endpoint_printed_identifier_arrays"][
            edge_index
        ]
        _require(
            domains == ["component_slot", "component_slot"]
            and all(
                (kind, classification) in allowed_endpoint_projections
                for kind, classification in zip(
                    kinds, classifications, strict=True
                )
            )
            and all(
                value is None or isinstance(value, str) and value
                for value in identifiers
            ),
            f"{label}: edge {edge_index} endpoint semantics",
        )
        _require(
            _exact_byte_projection(
                row["source_endpoint_matched_text_arrays"][edge_index],
                row["source_endpoint_matched_utf8_sha256_arrays"][edge_index],
                row["source_endpoint_page_number_arrays"][edge_index],
                row["source_endpoint_utf8_byte_start_arrays"][edge_index],
                row["source_endpoint_utf8_byte_end_arrays"][edge_index],
                2,
            ),
            f"{label}: edge {edge_index} exact endpoint bytes",
        )
        defect_flags = row["source_defect_flag_rows"][edge_index]
        _require_exact_keys(
            defect_flags, DEFECT_FLAG_KEYS, f"{label}: edge defect flags"
        )
        context_mix = set(kinds) == {
            "context_anchor",
            "remuneration_component_anchor",
        }
        _require(
            defect_flags
            == {
                "touches_noncatalog_aggregate_endpoint": False,
                "occurrence_derived_domain_crossing": False,
                "corrected_catalog_domain_crossing": False,
                "raw_node_domain_crossing": False,
                "context_remuneration_mix": context_mix,
                "head_spouse_mix": False,
            },
            f"{label}: edge {edge_index} complete source proof",
        )

    current_endpoint_projections = [
        tuple(row[key][edge_index][0] for key in endpoint_array_keys)
        for edge_index in range(evidence_count)
    ]
    _require(
        all(
            projection == current_endpoint_projections[0]
            for projection in current_endpoint_projections
        ),
        f"{label}: consistent current endpoint projection",
    )
    _require(
        row["structural_candidate_satisfied"] is True,
        f"{label}: structural candidate",
    )
    _require(
        row["pilot_document_member"] is (position in PILOT_POSITIONS),
        f"{label}: pilot membership",
    )

    _require(
        row["semantic_alias_adjudication_round"] == 5
        and row["semantic_alias_ledger_member"] is True,
        f"{label}: round-five semantic alias ledger",
    )
    expected_fragment_fields = _fragment_ledger_fields(instruction_id)
    _require(
        {
            key: row[key]
            for key in (
                "source_instruction_fragment",
                "tier_2_predecessor_seal_quality_issue",
                "tier_2_predecessor_ledger_note",
            )
        }
        == expected_fragment_fields,
        f"{label}: fragment seal-quality adjudication",
    )
    semantic_member = row["semantic_redirection_ledger_member"]
    _require(isinstance(semantic_member, bool), f"{label}: redirection ledger")
    valid_alias_ids = row["valid_alias_arm_evidence_ids"]
    _require(
        isinstance(valid_alias_ids, list)
        and len(valid_alias_ids) == len(set(valid_alias_ids))
        and set(valid_alias_ids) <= set(evidence_ids),
        f"{label}: alias evidence IDs",
    )
    disposition = row["repeat_coverage_disposition"]
    composite_decision = _composite_import_decisions_by_instruction().get(
        instruction_id
    )
    if instruction_id in EXCLUSIVE_DESTINATION_REDIRECTION_INSTRUCTION_IDS:
        expected_disposition = "admitted_exclusive_destination_redirection"
        expected_finding = SEMANTIC_ALIAS_REDIRECTION_FINDING
        expected_status = "redirection_arm_member"
        expected_valid_alias_ids: list[str] = []
        expected_pair_count = 0
    elif composite_decision is not None:
        expected_valid_alias_ids = list(
            composite_decision["approved_source_local_evidence_ids"]
        )
        expected_pair_count = composite_decision["approved_pair_count"]
        if expected_valid_alias_ids:
            expected_disposition = "existing_alias_arm"
            expected_finding = (
                "exact_source_text_derives_pairwise_typed_instruction_"
                "imports_without_composite_union"
            )
            expected_status = (
                "source_text_adjudicated_pairwise_alias_arm_member"
            )
        else:
            expected_disposition = "disclosed_stop_no_redirection_semantics"
            expected_finding = COMPOSITE_IMPORT_STOP_FINDING_BY_INSTRUCTION[
                instruction_id
            ]
            expected_status = "source_text_adjudicated_disclosed_stop"
    elif instruction_id in SEMANTIC_ALIAS_EQUIVALENCE_INSTRUCTION_IDS:
        expected_disposition = "existing_alias_arm"
        expected_finding = (
            "whitespace_only_continuation_composes_named_import"
            if instruction_id in CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS
            else SEMANTIC_ALIAS_EQUIVALENCE_FINDING
        )
        expected_status = "source_text_adjudicated_alias_arm_member"
        expected_valid_alias_ids = evidence_ids
        expected_pair_count = len(evidence_ids)
    elif instruction_id in SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION:
        expected_disposition = "disclosed_stop_no_redirection_semantics"
        expected_finding = SEMANTIC_ALIAS_STOP_FINDING_BY_INSTRUCTION[
            instruction_id
        ]
        expected_status = "source_text_adjudicated_disclosed_stop"
        expected_valid_alias_ids = []
        expected_pair_count = 0
    else:
        raise BuildError(f"{label}: instruction absent from semantic ledger")
    expected_rejected_evidence_ids = [
        evidence_id
        for evidence_id in evidence_ids
        if evidence_id not in set(expected_valid_alias_ids)
        and expected_disposition
        != "admitted_exclusive_destination_redirection"
    ]
    expected_named_import_or_equivalence = (
        expected_disposition == "existing_alias_arm"
    )
    expected_occurrence_equivalence = (
        expected_named_import_or_equivalence and composite_decision is None
    )
    _require(
        disposition == expected_disposition
        and row["semantic_alias_finding"] == expected_finding
        and row["occurrence_equivalence_proved"]
        is expected_occurrence_equivalence
        and row["named_instruction_import_or_occurrence_equivalence_proved"]
        is expected_named_import_or_equivalence
        and row["pairwise_decomposition_required"]
        is (composite_decision is not None)
        and row["approved_pair_count"] == expected_pair_count
        and row["rejected_source_local_evidence_ids"]
        == expected_rejected_evidence_ids
        and row["status"] == expected_status,
        f"{label}: source-text semantic adjudication",
    )
    continuation_citation = row["continuation_composition_citation"]
    if instruction_id in CONTINUATION_ALIAS_CITATION_INSTRUCTION_IDS:
        expected_continuation = CONTINUATION_ALIAS_CITATIONS_BY_INSTRUCTION[
            instruction_id
        ]
        _require(
            isinstance(continuation_citation, dict)
            and continuation_citation["composition_rule"]
            == CONTINUATION_COMPOSITION_RULE
            and continuation_citation["leading_occurrence_id"]
            == expected_continuation["leading_occurrence_id"]
            and continuation_citation["continuation_occurrence_id"]
            == instruction_id
            and continuation_citation["page_number"]
            == expected_continuation["page_number"]
            and continuation_citation["page_text_utf8_sha256"]
            == expected_continuation["page_text_utf8_sha256"]
            and continuation_citation["combined_utf8_byte_start"]
            == expected_continuation["combined_utf8_byte_start"]
            and continuation_citation["leading_utf8_byte_end"]
            == expected_continuation["leading_utf8_byte_end"]
            and continuation_citation["gap_utf8_byte_start"]
            == expected_continuation["gap_utf8_byte_start"]
            and continuation_citation["gap_utf8_byte_end"]
            == expected_continuation["gap_utf8_byte_end"]
            and continuation_citation["gap_is_whitespace_only"] is True
            and continuation_citation["gap_text"].isspace()
            and continuation_citation["gap_utf8_sha256"]
            == _sha256(continuation_citation["gap_text"].encode("utf-8"))
            and continuation_citation["continuation_utf8_byte_start"]
            == expected_continuation["continuation_utf8_byte_start"]
            and continuation_citation["combined_utf8_byte_end"]
            == expected_continuation["combined_utf8_byte_end"]
            and continuation_citation["combined_text"]
            == expected_continuation["combined_text"]
            and continuation_citation["combined_utf8_sha256"]
            == expected_continuation["combined_utf8_sha256"],
            f"{label}: continuation composition citation",
        )
    else:
        _require(
            continuation_citation is None,
            f"{label}: unexpected continuation composition citation",
        )
    if disposition == "admitted_exclusive_destination_redirection":
        _require(
            semantic_member is True
            and row["semantic_redirection_finding"]
            == SEMANTIC_ALIAS_REDIRECTION_FINDING
            and valid_alias_ids == expected_valid_alias_ids
            and isinstance(
                row["in_domain_redirection_relation_disposition_id"], str
            ),
            f"{label}: redirection partition member",
        )
    elif disposition == "existing_alias_arm":
        _require(
            semantic_member is False
            and row["semantic_redirection_finding"] is None
            and row["in_domain_redirection_relation_disposition_id"] is None
            and valid_alias_ids == expected_valid_alias_ids,
            f"{label}: alias partition member",
        )
    else:
        _require(
            semantic_member is False
            and row["semantic_redirection_finding"] is None
            and row["in_domain_redirection_relation_disposition_id"] is None
            and valid_alias_ids == expected_valid_alias_ids,
            f"{label}: STOP partition member",
        )
    _require(
        row["semantic_alias_adjudication_id"]
        == _row_id(
            "a12-semantic-alias-adjudication:",
            [
                row["source_document_id"],
                instruction_id,
                evidence_ids,
                instruction_text,
                row["source_instruction_matched_utf8_sha256"],
                instruction_page,
                instruction_start,
                instruction_end,
                row["source_endpoint_matched_text_arrays"],
                row["source_endpoint_matched_utf8_sha256_arrays"],
                row["source_endpoint_page_number_arrays"],
                row["source_endpoint_utf8_byte_start_arrays"],
                row["source_endpoint_utf8_byte_end_arrays"],
                disposition,
                expected_finding,
                expected_named_import_or_equivalence,
                expected_occurrence_equivalence,
                composite_decision is not None,
                expected_pair_count,
                expected_rejected_evidence_ids,
                continuation_citation,
                expected_fragment_fields,
            ],
        ),
        f"{label}: semantic alias adjudication ID",
    )
    _require(
        row["in_domain_component_cross_reference_sweep_id"]
        == _row_id(
            "a12-in-domain-component-cross-reference-sweep:",
            [
                row["source_document_id"],
                instruction_id,
                evidence_ids,
                evidence_occurrence_arrays,
                alias_arrays,
                canonical_arrays,
                disposition,
                row["semantic_alias_adjudication_id"],
            ],
        ),
        f"{label}: sweep ID",
    )


def _validate_redirection_lineage_row(
    row: Mapping[str, Any], label: str
) -> None:
    _require_exact_keys(
        row, EXCLUSIVE_DESTINATION_REDIRECTION_LINEAGE_ROW_KEYS, label
    )
    instruction_id = _require_string(
        row["source_instruction_occurrence_id"], f"{label}: instruction"
    )
    text = _require_string(
        row["source_instruction_matched_text"], f"{label}: text"
    )
    _require(
        row["source_text_shape_kind"] == _exclusive_placement_shape_kind(text),
        f"{label}: lineage source-text shape",
    )
    _require(
        row["source_instruction_matched_utf8_sha256"]
        == _sha256(text.encode("utf-8")),
        f"{label}: source digest",
    )
    page = _require_int(
        row["source_instruction_page_number"], f"{label}: page"
    )
    start = _require_int(
        row["source_instruction_utf8_byte_start"], f"{label}: start"
    )
    end = _require_int(
        row["source_instruction_utf8_byte_end"], f"{label}: end"
    )
    _require(
        page > 0
        and 0 <= start < end
        and end - start == len(text.encode("utf-8")),
        f"{label}: source span",
    )
    evidence_ids = row["source_local_evidence_ids"]
    outer_arrays = (
        row["source_relations"],
        row["source_handoff_statuses"],
        row["source_alias_anchor_occurrence_id_arrays"],
        row["source_canonical_anchor_occurrence_id_arrays"],
        row["source_endpoint_occurrence_kind_arrays"],
        row["source_endpoint_raw_node_domain_arrays"],
        row["source_endpoint_classification_arrays"],
        row["source_endpoint_printed_identifier_arrays"],
        row["source_unresolved_target_references"],
    )
    _require(
        isinstance(evidence_ids, list)
        and len(evidence_ids) == len(set(evidence_ids))
        and all(
            isinstance(values, list) and len(values) == len(evidence_ids)
            for values in outer_arrays
        ),
        f"{label}: source evidence projections",
    )
    eligible = row["in_domain_redirection_arm_eligible"]
    _require(isinstance(eligible, bool), f"{label}: eligibility")
    aggregate_id = row["existing_aggregate_relation_disposition_id"]
    if eligible:
        _require(
            aggregate_id is None
            and row["source_relations"]
            and all(
                relation == "explicit_cross_reference"
                for relation in row["source_relations"]
            )
            and row["source_alias_anchor_occurrence_id_arrays"]
            and all(
                len(values) == 1
                for values in row["source_alias_anchor_occurrence_id_arrays"]
            )
            and row["source_canonical_anchor_occurrence_id_arrays"]
            and all(
                len(values) == 1
                for values in row[
                    "source_canonical_anchor_occurrence_id_arrays"
                ]
            )
            and all(
                value is None
                for value in row["source_unresolved_target_references"]
            )
            and isinstance(
                row["in_domain_redirection_relation_disposition_id"], str
            )
            and row["lineage_disposition"]
            == "admitted_exclusive_destination_redirection"
            and row["status"] == "redirection_arm_member",
            f"{label}: admitted lineage member",
        )
    elif aggregate_id is not None:
        _require(
            row["in_domain_redirection_relation_disposition_id"] is None
            and isinstance(aggregate_id, str)
            and row["lineage_disposition"]
            == "covered_by_existing_aggregate_nonalias_subkind"
            and row["status"] == "existing_aggregate_arm_member",
            f"{label}: aggregate-covered lineage member",
        )
    else:
        _require(
            row["in_domain_redirection_relation_disposition_id"] is None
            and row["lineage_disposition"]
            in {
                "disclosed_stop_mixed_aggregate_component_proof",
                "disclosed_stop_incomplete_local_proof",
            }
            and row["status"] == "fail_closed_lineage_near_shape",
            f"{label}: STOP lineage member",
        )
    _require(
        row["exclusive_destination_redirection_lineage_id"]
        == _row_id(
            "a12-exclusive-destination-redirection-lineage:",
            [
                row["source_document_id"],
                instruction_id,
                text,
                evidence_ids,
            ],
        ),
        f"{label}: lineage ID",
    )


def _validate_parent_source_witness_row(row: Mapping[str, Any]) -> None:
    label = "parent source witness row"
    _require_exact_keys(row, PARENT_SOURCE_WITNESS_ROW_KEYS, label)
    _require_int(row["document_source_position"], f"{label}: position")
    _require(
        row["parent_occurrence_kind"]
        in {*PARENT_KIND_TO_CATEGORY, *INELIGIBLE_PARENT_CATEGORY},
        f"{label}: occurrence kind",
    )
    _require(
        row["status"] == "pinned_source_parent_witness",
        f"{label}: status",
    )
    _require(
        row["parent_source_witness_id"]
        == _row_id(
            "a12-parent-source-witness:",
            [
                row["source_document_id"],
                row["source_classification_id"],
                row["parent_occurrence_id"],
                row["parent_occurrence_kind"],
            ],
        ),
        f"{label}: witness ID",
    )


def _validate_parent_candidate_row(
    component_kind: str,
    document_source_position: int,
    candidate: Mapping[str, Any],
    source_witness_by_key: Mapping[tuple[int, str], Mapping[str, Any]],
) -> None:
    label = "parent candidate row"
    _require_exact_keys(candidate, PARENT_CANDIDATE_ROW_KEYS, label)
    occurrence_kind = candidate["parent_occurrence_kind"]
    _require(
        occurrence_kind
        in {*PARENT_KIND_TO_CATEGORY, *INELIGIBLE_PARENT_CATEGORY},
        f"{label}: unsupported occurrence kind",
    )
    source_key = (document_source_position, candidate["parent_occurrence_id"])
    _require(
        source_key in source_witness_by_key, f"{label}: no source witness"
    )
    _require(
        source_witness_by_key[source_key]["parent_occurrence_kind"]
        == occurrence_kind,
        f"{label}: source witness kind mismatch",
    )
    if occurrence_kind in PARENT_KIND_TO_CATEGORY:
        expected_category = PARENT_KIND_TO_CATEGORY[occurrence_kind]
        expected_slot = (
            "context_only"
            if expected_category == "source_job"
            and component_kind == "source_context"
            else (
                "remuneration_component"
                if expected_category == "source_job"
                else expected_category.removesuffix("_sentinel")
            )
        )
        _require(candidate["eligible_parent"] is True, f"{label}: eligibility")
        _require(
            candidate["parent_category"] == expected_category,
            f"{label}: category equation",
        )
        _require(
            candidate["derived_slot_kind"] == expected_slot,
            f"{label}: derived slot equation",
        )
        _require(
            candidate["ineligibility_reason"] is None,
            f"{label}: eligible reason",
        )
    else:
        _require(
            candidate["eligible_parent"] is False, f"{label}: eligibility"
        )
        _require(
            candidate["parent_category"]
            == INELIGIBLE_PARENT_CATEGORY[occurrence_kind],
            f"{label}: ineligible category equation",
        )
        _require(candidate["derived_slot_kind"] is None, f"{label}: slot")
        _require(
            candidate["ineligibility_reason"]
            == "parent_occurrence_kind_outside_allowed_equations",
            f"{label}: ineligibility reason",
        )


def _validate_component_shape_row(
    row: Mapping[str, Any],
    source_witness_by_key: Mapping[tuple[int, str], Mapping[str, Any]],
    label: str,
) -> None:
    _require_exact_keys(row, COMPONENT_SHAPE_ROW_KEYS, label)
    component_kind = row["component_kind"]
    _require(component_kind in COMPONENT_KINDS, f"{label}: component kind")
    position = _require_int(
        row["document_source_position"], f"{label}: source position"
    )
    candidates = row["parent_candidate_rows"]
    _require(isinstance(candidates, list), f"{label}: candidates")
    for candidate in candidates:
        _require(isinstance(candidate, dict), f"{label}: candidate object")
        _validate_parent_candidate_row(
            component_kind, position, candidate, source_witness_by_key
        )
    parent_ids = [
        candidate["parent_occurrence_id"] for candidate in candidates
    ]
    _require(
        len(set(parent_ids)) == len(parent_ids), f"{label}: duplicate parent"
    )
    raw_count = len(candidates)
    eligible_count = sum(
        candidate["eligible_parent"] for candidate in candidates
    )
    _require(
        row["serialized_parent_cardinality"] == raw_count,
        f"{label}: serialized cardinality",
    )
    _require(row["parent_candidate_count"] == raw_count, f"{label}: count")
    _require(
        row["eligible_parent_cardinality"] == eligible_count,
        f"{label}: eligible cardinality",
    )
    _require(
        row["parent_candidate_domain_sha256"] == _domain_sha(candidates),
        f"{label}: candidate domain",
    )
    expected_disposition = (
        "zero_parent_terminal_disposition"
        if raw_count == 0
        else (
            "unique_parent_assignment"
            if raw_count == 1 and eligible_count == 1
            else (
                "zero_lawful_parent_terminal_disposition"
                if raw_count == 1
                else "multi_parent_ambiguity_no_selection"
            )
        )
    )
    _require(
        row["disposition"] == expected_disposition,
        f"{label}: disposition equation",
    )
    categories = {candidate["parent_category"] for candidate in candidates}
    eligible_categories = {
        candidate["parent_category"]
        for candidate in candidates
        if candidate["eligible_parent"]
    }
    expected_raw_cross = raw_count > 1 and len(categories) > 1
    expected_eligible_cross = len(eligible_categories) > 1
    expected_mixed = (
        raw_count > 1
        and any(candidate["eligible_parent"] for candidate in candidates)
        and any(not candidate["eligible_parent"] for candidate in candidates)
    )
    _require(
        row["raw_parent_category_ambiguity"] is expected_raw_cross,
        f"{label}: raw category ambiguity",
    )
    _require(
        row["eligible_parent_category_ambiguity"] is expected_eligible_cross,
        f"{label}: eligible category ambiguity",
    )
    _require(
        row["eligible_ineligible_mixed_ambiguity"] is expected_mixed,
        f"{label}: eligible/ineligible ambiguity",
    )
    _require(
        row["forced_parent_selection"] is False, f"{label}: forced parent"
    )
    _require(
        row["tier_2_unique_parent_arm_eligible"]
        is (expected_disposition == "unique_parent_assignment"),
        f"{label}: tier-2 unique-parent arm",
    )
    _require(
        row["r_q_relationship_emitted"] is False,
        f"{label}: pilot emitted R_Q",
    )
    _require(
        row["status"] == "recorded_nonauthority_shape",
        f"{label}: status",
    )
    _require(
        row["component_parent_resolution_id"]
        == _row_id(
            "a12-component-parent-resolution:",
            [
                row["source_document_id"],
                row["component_anchor_occurrence_id"],
                component_kind,
                expected_disposition,
                candidates,
            ],
        ),
        f"{label}: resolution ID",
    )


def _validate_candidate_alias_support_rows(
    row: Mapping[str, Any],
    members: Sequence[str],
    occurrence_kind: str,
    label: str,
) -> None:
    supports = row["alias_support_rows"]
    _require(isinstance(supports, list), f"{label}: support rows")
    _require(
        row["alias_support_count"] == len(supports),
        f"{label}: support count",
    )
    _require(
        row["alias_support_domain_sha256"] == _domain_sha(supports),
        f"{label}: support domain",
    )
    member_set = set(members)
    roots = {member: member for member in members}

    def find(member: str) -> str:
        while roots[member] != member:
            roots[member] = roots[roots[member]]
            member = roots[member]
        return member

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            roots[right_root] = left_root

    proof_ids: list[str] = []
    for support in supports:
        _require_exact_keys(
            support, ALIAS_SUPPORT_ROW_KEYS, f"{label}: support"
        )
        proof_id = _require_string(
            support["alias_support_proof_id"], f"{label}: support ID"
        )
        proof_ids.append(proof_id)
        support_members = support["member_occurrence_ids"]
        _require(
            isinstance(support_members, list)
            and len(support_members) >= 2
            and len(set(support_members)) == len(support_members),
            f"{label}: support members",
        )
        _require(
            set(support_members) <= member_set,
            f"{label}: support member outside class",
        )
        aliases = support["alias_anchor_occurrence_ids"]
        canonicals = support["canonical_anchor_occurrence_ids"]
        _require(
            isinstance(aliases, list)
            and aliases
            and isinstance(canonicals, list)
            and canonicals
            and len(set(aliases)) == len(aliases)
            and len(set(canonicals)) == len(canonicals)
            and not set(aliases) & set(canonicals)
            and set([*aliases, *canonicals]) == set(support_members),
            f"{label}: directional endpoints",
        )
        evidence_ids = support["evidence_occurrence_ids"]
        _require(
            isinstance(evidence_ids, list)
            and evidence_ids
            and len(set(evidence_ids)) == len(evidence_ids)
            and set(support_members) <= set(evidence_ids),
            f"{label}: support evidence",
        )
        for member in support_members[1:]:
            union(support_members[0], member)
        relation = support["relation"]
        _require(
            relation in ALLOWED_LOCAL_EVIDENCE_RELATIONS,
            f"{label}: support relation",
        )
        origin = support["support_origin"]
        if origin == "exact_pair_equality_sweep":
            printed_identifier = _require_string(
                support["printed_identifier"],
                f"{label}: support printed identifier",
            )
            exact_label = _require_string(
                support["exact_label"], f"{label}: support exact label"
            )
            _require(
                relation == "same_printed_identifier_and_exact_label"
                and support["source_local_evidence_id"] is None
                and support["semantic_alias_pair_adjudication_id"] is None
                and support["pairing_basis_code"]
                == "byte_identical_printed_identifier_and_exact_label"
                and aliases == support_members[1:]
                and canonicals == support_members[:1]
                and evidence_ids == support_members,
                f"{label}: exact-pair support shape",
            )
            expected_proof_id = _row_id(
                "a12-candidate-exact-pair-alias-support:",
                [
                    occurrence_kind,
                    printed_identifier,
                    exact_label,
                    aliases,
                    canonicals,
                    evidence_ids,
                ],
            )
        elif origin == "sealed_local_evidence":
            _require_string(
                support["source_local_evidence_id"],
                f"{label}: source local evidence ID",
            )
            semantic_pair_id = _require_string(
                support["semantic_alias_pair_adjudication_id"],
                f"{label}: semantic pair adjudication ID",
            )
            _require_string(
                support["pairing_basis_code"],
                f"{label}: pairing basis",
            )
            _require(
                len(aliases) == len(canonicals) == 1,
                f"{label}: adjudicated support is not one atomic pair",
            )
            if relation == "same_printed_identifier_and_exact_label":
                _require_string(
                    support["printed_identifier"],
                    f"{label}: local support printed identifier",
                )
                _require_string(
                    support["exact_label"],
                    f"{label}: local support exact label",
                )
            else:
                _require(
                    support["printed_identifier"] is None
                    and support["exact_label"] is None,
                    f"{label}: non-equality support labels",
                )
            expected_proof_id = _row_id(
                "a12-candidate-local-alias-support:",
                [
                    semantic_pair_id,
                    relation,
                    aliases[0],
                    canonicals[0],
                    evidence_ids,
                ],
            )
        else:
            raise BuildError(f"{label}: support origin")
        _require(proof_id == expected_proof_id, f"{label}: support ID")
    _require(
        len(proof_ids) == len(set(proof_ids)),
        f"{label}: duplicate support ID",
    )
    _require(
        len({find(member) for member in members}) == 1,
        f"{label}: support graph does not connect class",
    )


def _validate_alias_semantic_pair_row(
    pair: Mapping[str, Any],
    evidence: Mapping[str, Any],
    label: str,
) -> None:
    """Validate one cited atomic or typed pair inside the sole A gate."""
    _require_exact_keys(pair, ALIAS_SEMANTIC_PAIR_ROW_KEYS, label)
    _require(
        pair["source_local_evidence_id"]
        == evidence["source_local_evidence_id"],
        f"{label}: source evidence",
    )
    ordinal = _require_int(pair["pair_ordinal"], f"{label}: ordinal")
    _require(ordinal >= 0, f"{label}: negative ordinal")
    pair_kind = pair["pair_kind"]
    _require(
        pair_kind
        in {"atomic_occurrence_pair", "typed_instruction_import_projection"},
        f"{label}: pair kind",
    )
    _require_string(pair["pairing_basis_code"], f"{label}: pairing basis")
    _require_string(pair["semantic_type"], f"{label}: semantic type")
    alias_id = _require_string(
        pair["alias_occurrence_id"], f"{label}: alias occurrence"
    )
    canonical_id = _require_string(
        pair["canonical_occurrence_id"],
        f"{label}: canonical occurrence",
    )
    aliases = evidence["alias_anchor_occurrence_ids"]
    canonicals = evidence["canonical_anchor_occurrence_ids"]
    _require(
        alias_id in aliases
        and canonical_id in canonicals
        and alias_id != canonical_id,
        f"{label}: directional endpoints",
    )
    endpoint_ids = [*aliases, *canonicals]
    alias_index = endpoint_ids.index(alias_id)
    canonical_index = endpoint_ids.index(canonical_id)
    for prefix, index in (
        ("alias", alias_index),
        ("canonical", canonical_index),
    ):
        _require(
            pair[f"{prefix}_endpoint_matched_text"]
            == evidence["endpoint_matched_texts"][index]
            and pair[f"{prefix}_endpoint_matched_utf8_sha256"]
            == evidence["endpoint_matched_utf8_sha256s"][index]
            and pair[f"{prefix}_endpoint_page_number"]
            == evidence["endpoint_page_numbers"][index]
            and pair[f"{prefix}_endpoint_utf8_byte_start"]
            == evidence["endpoint_utf8_byte_starts"][index]
            and pair[f"{prefix}_endpoint_utf8_byte_end"]
            == evidence["endpoint_utf8_byte_ends"][index],
            f"{label}: {prefix} endpoint projection",
        )
        text = pair[f"{prefix}_endpoint_matched_text"]
        _require(
            pair[f"{prefix}_endpoint_matched_utf8_sha256"]
            == _sha256(text.encode("utf-8"))
            and pair[f"{prefix}_endpoint_utf8_byte_end"]
            - pair[f"{prefix}_endpoint_utf8_byte_start"]
            == len(text.encode("utf-8")),
            f"{label}: {prefix} endpoint exact bytes",
        )
    instruction_keys = (
        "source_instruction_occurrence_ids",
        "source_instruction_matched_texts",
        "source_instruction_matched_utf8_sha256s",
        "source_instruction_page_numbers",
        "source_instruction_utf8_byte_starts",
        "source_instruction_utf8_byte_ends",
    )
    instruction_ids = evidence["source_instruction_occurrence_ids"]
    _require(
        all(pair[key] == evidence[key] for key in instruction_keys),
        f"{label}: source instruction projection",
    )
    closure_eligible = pair_kind == "atomic_occurrence_pair"
    exact_pairing_citation = pair["exact_pairing_citation"]
    composite_pair_id = pair["composite_typed_projection_pair_id"]
    if closure_eligible:
        _require(
            pair["alias_question_selector"] is None
            and pair["canonical_question_selector"] is None
            and exact_pairing_citation is None
            and composite_pair_id is None,
            f"{label}: atomic pair carries composite authority",
        )
    else:
        pinned_pairs, _pinned_stops = _composite_adjudications_by_id()
        pinned_pair = pinned_pairs.get(composite_pair_id)
        instruction_citation = {
            "document_source_position": evidence["document_source_position"],
            "matched_text": evidence["source_instruction_matched_texts"][0],
            "matched_utf8_sha256": evidence[
                "source_instruction_matched_utf8_sha256s"
            ][0],
            "page_number": evidence["source_instruction_page_numbers"][0],
            "source_document_id": evidence["source_document_id"],
            "utf8_byte_span": {
                "start": evidence["source_instruction_utf8_byte_starts"][0],
                "end": evidence["source_instruction_utf8_byte_ends"][0],
            },
        }
        _require(
            len(instruction_ids) == 1
            and pinned_pair is not None
            and pinned_pair["instruction_id"] == instruction_ids[0]
            and pinned_pair["source_evidence_id"]
            == evidence["source_local_evidence_id"]
            and pinned_pair["alias_combined_occurrence_id"] == alias_id
            and pinned_pair["canonical_combined_occurrence_id"] == canonical_id
            and pinned_pair["alias_question_selector"]
            == pair["alias_question_selector"]
            and pinned_pair["canonical_question_selector"]
            == pair["canonical_question_selector"]
            and pinned_pair["semantic_type"] == pair["semantic_type"]
            and pinned_pair["pairing_basis_code"] == pair["pairing_basis_code"]
            and pinned_pair["instruction_citation"] == instruction_citation
            and pinned_pair["exact_pairing_citation"]
            == exact_pairing_citation,
            f"{label}: typed pair lacks its pinned exact-text derivation",
        )
    _require(
        pair["class_closure_eligible"] is closure_eligible
        and pair["typed_projection_union_prohibited"] is (not closure_eligible)
        and pair["status"] == "source_cited_semantic_pair_approved",
        f"{label}: closure law",
    )
    _require(
        pair["semantic_alias_pair_adjudication_id"]
        == _row_id(
            "a12-semantic-alias-pair-adjudication:",
            [
                evidence["source_document_id"],
                evidence["source_local_evidence_id"],
                ordinal,
                pair_kind,
                pair["pairing_basis_code"],
                pair["semantic_type"],
                alias_id,
                canonical_id,
                pair["alias_question_selector"],
                pair["canonical_question_selector"],
                pair["alias_endpoint_matched_utf8_sha256"],
                pair["canonical_endpoint_matched_utf8_sha256"],
                pair["source_instruction_matched_utf8_sha256s"],
                exact_pairing_citation,
                composite_pair_id,
            ],
        ),
        f"{label}: pair adjudication ID",
    )


def _validate_alias_evidence_semantic_adjudication_row(
    row: Mapping[str, Any], label: str
) -> list[Mapping[str, Any]]:
    """Validate one source evidence decision and return its approved pairs."""
    _require_exact_keys(
        row, ALIAS_EVIDENCE_SEMANTIC_ADJUDICATION_ROW_KEYS, label
    )
    _require(
        1 <= _require_int(row["document_source_position"], label) <= 81,
        f"{label}: document position",
    )
    _require_string(row["source_document_id"], f"{label}: document")
    _require_string(
        row["source_local_evidence_id"], f"{label}: source evidence"
    )
    origin = row["candidate_origin"]
    _require(
        origin
        in {
            "ca41663_structural_ledger_admission",
            "ca41663_nonledger_bypass_adjudication",
            "round_five_continuation_restoration",
        }
        and row["round_five_continuation_restoration"]
        is (origin == "round_five_continuation_restoration")
        and row["ca41663_admitted_alias_evidence"]
        is (origin != "round_five_continuation_restoration")
        and row["structural_filter_satisfied"] is True,
        f"{label}: candidate provenance",
    )
    instruction_ids = row["source_instruction_occurrence_ids"]
    aliases = row["alias_anchor_occurrence_ids"]
    canonicals = row["canonical_anchor_occurrence_ids"]
    evidence_ids = row["evidence_occurrence_ids"]
    _require(
        isinstance(instruction_ids, list)
        and isinstance(aliases, list)
        and aliases
        and isinstance(canonicals, list)
        and canonicals
        and len([*aliases, *canonicals]) == len(set([*aliases, *canonicals]))
        and not set(aliases) & set(canonicals)
        and isinstance(evidence_ids, list)
        and len(evidence_ids) == len(set(evidence_ids))
        and set([*instruction_ids, *aliases, *canonicals])
        <= set(evidence_ids),
        f"{label}: structurally complete candidate",
    )
    endpoint_count = len(aliases) + len(canonicals)
    _require(
        _exact_byte_projection(
            row["source_instruction_matched_texts"],
            row["source_instruction_matched_utf8_sha256s"],
            row["source_instruction_page_numbers"],
            row["source_instruction_utf8_byte_starts"],
            row["source_instruction_utf8_byte_ends"],
            len(instruction_ids),
        )
        and _exact_byte_projection(
            row["endpoint_matched_texts"],
            row["endpoint_matched_utf8_sha256s"],
            row["endpoint_page_numbers"],
            row["endpoint_utf8_byte_starts"],
            row["endpoint_utf8_byte_ends"],
            endpoint_count,
        ),
        f"{label}: exact source bytes",
    )
    pairs = row["approved_pair_rows"]
    _require(
        isinstance(pairs, list)
        and row["approved_pair_count"] == len(pairs)
        and [pair["pair_ordinal"] for pair in pairs]
        == list(range(len(pairs))),
        f"{label}: approved pair array",
    )
    for pair in pairs:
        _validate_alias_semantic_pair_row(pair, row, f"{label}: pair")
    approved = bool(pairs)
    _require(
        row["semantic_adjudication_round"] == 5
        and row["decision"].startswith("approved_") is approved
        and row["status"]
        == (
            "source_cited_semantic_alias_approved"
            if approved
            else "source_cited_semantic_alias_disclosed_stop"
        ),
        f"{label}: semantic outcome",
    )
    _require_string(row["semantic_finding"], f"{label}: finding")
    continuation_citation = row["continuation_composition_citation"]
    _require(
        (continuation_citation is not None)
        is any(
            pair["pairing_basis_code"] == CONTINUATION_COMPOSITION_RULE
            for pair in pairs
        ),
        f"{label}: continuation citation/pair mismatch",
    )
    composite_stop_citation = row["composite_stop_citation"]
    composite_stop_expected = (
        not approved and origin != "ca41663_nonledger_bypass_adjudication"
    )
    _require(
        (composite_stop_citation is not None) is composite_stop_expected,
        f"{label}: composite STOP citation mismatch",
    )
    if composite_stop_citation is not None:
        _require_exact_keys(
            composite_stop_citation,
            COMPOSITE_STOP_KEYS,
            f"{label}: composite STOP citation",
        )
        _pinned_pairs, pinned_stops = _composite_adjudications_by_id()
        stop_id = composite_stop_citation["stop_adjudication_id"]
        pinned_stop = pinned_stops.get(stop_id)
        _require(
            len(instruction_ids) == 1
            and pinned_stop == composite_stop_citation
            and composite_stop_citation["source_evidence_id"]
            == row["source_local_evidence_id"]
            and composite_stop_citation["instruction_id"] == instruction_ids[0]
            and composite_stop_citation["alias_combined_occurrence_id"]
            == aliases[0]
            and composite_stop_citation["canonical_combined_occurrence_id"]
            == canonicals[0]
            and composite_stop_citation["finding_code"]
            == row["semantic_finding"],
            f"{label}: composite STOP lacks its pinned exact-text ruling",
        )
    _require(
        row["semantic_alias_evidence_adjudication_id"]
        == _row_id(
            "a12-semantic-alias-evidence-adjudication:",
            [
                row["source_document_id"],
                row["source_local_evidence_id"],
                origin,
                row["ca41663_admitted_alias_evidence"],
                row["source_instruction_matched_utf8_sha256s"],
                row["endpoint_matched_utf8_sha256s"],
                row["semantic_finding"],
                row["decision"],
                [
                    pair["semantic_alias_pair_adjudication_id"]
                    for pair in pairs
                ],
                continuation_citation,
                composite_stop_citation,
            ],
        ),
        f"{label}: evidence adjudication ID",
    )
    return pairs


def _validate_component_class_admission_sweep_row(
    row: Mapping[str, Any],
) -> None:
    label = "component class admission sweep row"
    _require_exact_keys(row, COMPONENT_CLASS_ADMISSION_SWEEP_ROW_KEYS, label)
    _require(row["component_kind"] in COMPONENT_KINDS, f"{label}: kind")
    members = row["component_class_member_occurrence_ids"]
    _require(isinstance(members, list) and members, f"{label}: members")
    _require(len(set(members)) == len(members), f"{label}: duplicate member")
    _require(
        row["component_class_member_count"] == len(members),
        f"{label}: member count",
    )
    _require(
        row["canonical_component_occurrence_id"] == members[0],
        f"{label}: canonical member",
    )
    raw_cardinalities = row["member_raw_parent_cardinalities"]
    _require(
        isinstance(raw_cardinalities, list)
        and len(raw_cardinalities) == len(members),
        f"{label}: raw cardinalities",
    )
    for value in raw_cardinalities:
        _require_int(value, f"{label}: raw cardinality")
        _require(value >= 0, f"{label}: negative cardinality")
    _require(
        row["raw_parent_candidate_count"] == sum(raw_cardinalities),
        f"{label}: raw candidate count",
    )
    eligible_count = _require_int(
        row["eligible_canonical_parent_count"],
        f"{label}: eligible canonical count",
    )
    _require(eligible_count >= 0, f"{label}: eligible canonical count")
    disposition = row["candidate_disposition"]
    _require(
        disposition
        in {
            "zero_parent_terminal_disposition",
            "zero_lawful_parent_terminal_disposition",
            "unique_parent_assignment",
            "multi_parent_ambiguity_no_selection",
        },
        f"{label}: disposition",
    )
    unique = disposition == "unique_parent_assignment"
    _require(
        row["relationship_arm_eligible"] is unique,
        f"{label}: candidate relationship arm",
    )
    _require(
        row["r_q_relationship_emitted"] is False,
        f"{label}: emitted R_Q",
    )
    if unique:
        _require(eligible_count == 1, f"{label}: unique eligible count")
        _require_string(
            row["candidate_unique_parent_node_id"],
            f"{label}: unique parent",
        )
        _require_string(
            row["candidate_unique_slot_kind"], f"{label}: unique slot"
        )
    else:
        _require(
            row["candidate_unique_parent_node_id"] is None
            and row["candidate_unique_slot_kind"] is None,
            f"{label}: nonunique selection",
        )
    _validate_candidate_alias_support_rows(
        row,
        members,
        COMPONENT_CLASSIFICATION_TO_KIND[row["component_kind"]],
        label,
    )
    _require(
        row["predecessor_reseal_required"] is True,
        f"{label}: predecessor prerequisite",
    )
    _require(
        row["status"]
        == "candidate_class_fold_nonauthority_predecessor_reseal_required",
        f"{label}: status",
    )
    expected_class_id = _row_id(
        "a12-candidate-component-class:",
        [row["canonical_component_occurrence_id"], members],
    )
    _require(
        row["candidate_component_class_id"] == expected_class_id,
        f"{label}: candidate class ID",
    )
    _require(
        row["component_class_admission_sweep_id"]
        == _row_id(
            "a12-component-class-admission-sweep:",
            [expected_class_id, disposition],
        ),
        f"{label}: sweep ID",
    )


def _validate_catalog_only_job_complement_sweep_row(
    row: Mapping[str, Any],
) -> None:
    label = "catalog-only job complement sweep row"
    _require_exact_keys(row, CATALOG_ONLY_JOB_COMPLEMENT_SWEEP_ROW_KEYS, label)
    members = row["job_class_member_occurrence_ids"]
    _require(isinstance(members, list) and members, f"{label}: members")
    _require(len(set(members)) == len(members), f"{label}: duplicate member")
    _require(
        row["job_class_member_count"] == len(members),
        f"{label}: member count",
    )
    _require(
        row["canonical_job_occurrence_id"] == members[0],
        f"{label}: canonical member",
    )
    expected_class_id = _row_id(
        "a12-candidate-job-class:",
        [row["canonical_job_occurrence_id"], members],
    )
    _require(
        row["candidate_job_class_id"] == expected_class_id,
        f"{label}: candidate class ID",
    )
    relationships = row["candidate_relationship_component_class_ids"]
    _require(isinstance(relationships, list), f"{label}: relationships")
    _require(
        len(set(relationships)) == len(relationships),
        f"{label}: duplicate relationship",
    )
    _require(
        row["candidate_relationship_count"] == len(relationships),
        f"{label}: relationship count",
    )
    catalog_only = not relationships
    _require(
        row["catalog_only_disposition_required"] is catalog_only,
        f"{label}: catalog-only biconditional",
    )
    expected_arm = (
        "terminal_catalog_disposition"
        if catalog_only
        else "relationship_projection_nonempty"
    )
    _require(row["coverage_arm"] == expected_arm, f"{label}: coverage arm")
    _require(
        row["catalog_only_disposition_emitted"] is False,
        f"{label}: emitted disposition",
    )
    _validate_candidate_alias_support_rows(row, members, "job_anchor", label)
    _require(
        row["predecessor_reseal_required"] is True,
        f"{label}: predecessor prerequisite",
    )
    _require(
        row["status"]
        == "candidate_job_complement_nonauthority_predecessor_reseal_required",
        f"{label}: status",
    )
    _require(
        row["catalog_only_job_complement_sweep_id"]
        == _row_id(
            "a12-catalog-only-job-complement-sweep:",
            [expected_class_id, relationships],
        ),
        f"{label}: sweep ID",
    )


def _validate_doc036_defect_row(row: Mapping[str, Any]) -> None:
    label = "doc036 defect row"
    _require_exact_keys(row, DOC036_DEFECT_ROW_KEYS, label)
    _require(row["document_source_position"] == 36, f"{label}: position")
    matched_text = _require_string(
        row["source_occurrence_matched_text"], f"{label}: source text"
    )
    _require(
        row["source_occurrence_matched_utf8_sha256"]
        == _sha256(matched_text.encode("utf-8")),
        f"{label}: source text digest",
    )
    page = _require_int(
        row["source_occurrence_page_number"], f"{label}: source page"
    )
    start = _require_int(
        row["source_occurrence_utf8_byte_start"], f"{label}: source start"
    )
    end = _require_int(
        row["source_occurrence_utf8_byte_end"], f"{label}: source end"
    )
    _require(
        page > 0
        and 0 <= start < end
        and end - start == len(matched_text.encode("utf-8")),
        f"{label}: exact source span",
    )
    expected_kind = AGGREGATE_CLASSIFICATION_TO_KIND.get(
        row["source_classification"]
    )
    _require(expected_kind == row["occurrence_kind"], f"{label}: kind")
    _require(
        row["serialized_node_domain"] == "component_slot",
        f"{label}: raw domain",
    )
    _require(
        row["correct_node_domain"] == "aggregate", f"{label}: corrected domain"
    )
    _require(
        row["disposition"] == "predecessor_seal_defect",
        f"{label}: disposition",
    )
    _require(row["law_gap_admitted"] is False, f"{label}: law gap admitted")
    _require(
        row["component_slot_admitted"] is False,
        f"{label}: component slot admitted",
    )
    _require(
        row["semantic_adjudication_round"] == 3
        and row["source_text_citation_status"]
        == "exact_text_digest_page_and_utf8_span_cited",
        f"{label}: round-three citation",
    )
    _require(
        row["required_action"]
        == "reseal_document_036_with_aggregate_anchor_domain",
        f"{label}: required action",
    )
    _require(
        row["adjudicative_rationale"]
        == "aggregate_occurrence_kind_controls_node_domain_reseal_required",
        f"{label}: rationale",
    )
    _require(
        row["row_specific_semantic_finding"]
        == "cited_anchor_text_denotes_an_aggregate_but_the_predecessor_"
        "serialized_component_slot",
        f"{label}: semantic finding",
    )
    _require(row["status"] == "blocked_predecessor_row", f"{label}: status")
    _require(
        row["predecessor_adjudication_id"]
        == _row_id(
            "a12-predecessor-doc036-aggregate-adjudication:",
            [
                row["source_document_id"],
                row["source_classification_id"],
                row["source_occurrence_id"],
                row["source_classification"],
                row["disposition"],
            ],
        ),
        f"{label}: adjudication ID",
    )


def _validate_proof_adjudication_row(row: Mapping[str, Any]) -> None:
    label = "proof adjudication row"
    _require_exact_keys(row, PROOF_ADJUDICATION_ROW_KEYS, label)
    _require(
        row["relation"] in ALLOWED_LOCAL_EVIDENCE_RELATIONS,
        f"{label}: relation",
    )
    aliases = row["alias_anchor_occurrence_ids"]
    canonicals = row["canonical_anchor_occurrence_ids"]
    endpoint_kinds = row["endpoint_occurrence_kinds"]
    raw_domains = row["endpoint_raw_node_domains"]
    classifications = row["endpoint_classifications"]
    printed_identifiers = row["endpoint_printed_identifiers"]
    _require(isinstance(aliases, list) and aliases, f"{label}: aliases")
    _require(
        isinstance(canonicals, list) and canonicals, f"{label}: canonicals"
    )
    endpoint_count = len(aliases) + len(canonicals)
    _require(
        len(endpoint_kinds)
        == len(raw_domains)
        == len(classifications)
        == len(printed_identifiers)
        == endpoint_count,
        f"{label}: endpoint projections",
    )
    _require(
        all(
            value is None or isinstance(value, str)
            for value in printed_identifiers
        ),
        f"{label}: printed identifiers",
    )
    instructions = row["source_instruction_occurrence_ids"]
    _require(
        isinstance(instructions, list) and instructions,
        f"{label}: instructions",
    )
    _require(
        _exact_byte_projection(
            row["source_instruction_matched_texts"],
            row["source_instruction_matched_utf8_sha256s"],
            row["source_instruction_page_numbers"],
            row["source_instruction_utf8_byte_starts"],
            row["source_instruction_utf8_byte_ends"],
            len(instructions),
        )
        and _exact_byte_projection(
            row["endpoint_matched_texts"],
            row["endpoint_matched_utf8_sha256s"],
            row["endpoint_page_numbers"],
            row["endpoint_utf8_byte_starts"],
            row["endpoint_utf8_byte_ends"],
            endpoint_count,
        ),
        f"{label}: exact source citations",
    )
    expected_flags = {
        "touches_noncatalog_aggregate_endpoint": any(
            kind in AGGREGATE_OCCURRENCE_KINDS for kind in endpoint_kinds
        ),
        "occurrence_derived_domain_crossing": len(
            {_occurrence_catalog_domain(kind) for kind in endpoint_kinds}
        )
        > 1,
        "raw_node_domain_crossing": len(set(raw_domains)) > 1,
        "context_remuneration_mix": {
            "context_anchor",
            "remuneration_component_anchor",
        }.issubset(set(endpoint_kinds)),
        "head_spouse_mix": {ROLE_HEAD, ROLE_SPOUSE}.issubset(
            set(classifications)
        ),
    }
    expected_flags["corrected_catalog_domain_crossing"] = expected_flags[
        "occurrence_derived_domain_crossing"
    ]
    flags = row["defect_flags"]
    _require(isinstance(flags, dict), f"{label}: defect flags")
    _require_exact_keys(flags, DEFECT_FLAG_KEYS, f"{label}: defect flags")
    _require(flags == expected_flags, f"{label}: defect flag equations")
    _require(any(flags.values()), f"{label}: no defect")
    evidence_id = row["source_local_evidence_id"]
    aggregate_eligible = evidence_id in AGGREGATE_RELATION_LAW_GAP_EVIDENCE_IDS
    redirection_eligible = evidence_id in REDIRECTION_LAW_GAP_EVIDENCE_IDS
    seal_defect = evidence_id in PREDECESSOR_SEAL_DEFECT_EVIDENCE_IDS
    _require(
        sum((aggregate_eligible, redirection_eligible, seal_defect)) == 1,
        f"{label}: source-reviewed semantic ledger",
    )
    _require(
        row["semantic_adjudication_round"] == 3
        and row["source_text_citation_status"]
        == "exact_text_digest_page_and_utf8_span_cited",
        f"{label}: round-three citation",
    )
    _require(
        row["in_domain_nonalias_relation_arm_eligible"]
        is (aggregate_eligible or redirection_eligible),
        f"{label}: in-domain nonalias disposition",
    )
    _require(row["alias_admitted"] is False, f"{label}: alias admitted")
    semantic_finding = _require_string(
        row["row_specific_semantic_finding"], f"{label}: semantic finding"
    )
    if aggregate_eligible:
        _require(
            row["in_domain_nonalias_relation_subkind"]
            == AGGREGATE_RELATION_SUBKIND
            and row["disposition"]
            == "predecessor_law_gap_repaired_by_noncatalog_aggregate_"
            "relation_arm"
            and row["law_gap_admitted"] is True
            and row["required_action"]
            == "ratify_extended_in_domain_nonalias_law_before_tier_2"
            and row["adjudicative_rationale"]
            == "authenticated_aggregate_relation_is_honest_nonalias_law_gap"
            and semantic_finding
            == "cited_instruction_and_aggregate_only_endpoints_authenticate_"
            "a_nonalias_aggregate_relation"
            and row["status"]
            == "blocked_pending_extended_repeat_law_ratification",
            f"{label}: aggregate law-gap adjudication",
        )
    elif redirection_eligible:
        _require(
            row["in_domain_nonalias_relation_subkind"]
            == REDIRECTION_RELATION_SUBKIND
            and row["disposition"]
            == "predecessor_law_gap_repaired_by_in_domain_redirection_"
            "relation_arm"
            and row["law_gap_admitted"] is True
            and row["required_action"]
            == "ratify_extended_in_domain_nonalias_law_before_tier_2"
            and row["adjudicative_rationale"]
            == "authenticated_named_destination_and_not_here_instruction_"
            "is_honest_nonalias_redirection_law_gap"
            and semantic_finding
            == "cited_text_names_G78_as_the_destination_and_excludes_the_"
            "current_G83_location"
            and row["status"]
            == "blocked_pending_extended_repeat_law_ratification",
            f"{label}: redirection law-gap adjudication",
        )
    else:
        allowed_defect_findings = {
            "cited_repeat_text_does_not_authenticate_the_heterogeneous_page_"
            "wide_endpoint_projection",
            "cited_instruction_is_an_incomplete_clause_and_cannot_"
            "authenticate_a_complete_redirection",
            "cited_income_list_is_shared_with_an_independent_alias_proof_and_"
            "does_not_authenticate_this_pairing",
            "cited_same_occupation_text_asserts_semantics_but_the_job_context_"
            "endpoint_crossing_requires_reseal",
            "cited_see_instructions_text_is_mispaired_to_a_context_"
            "remuneration_endpoint_claim",
            "cited_instruction_does_not_authenticate_the_mixed_or_misbound_"
            "endpoint_projection",
        }
        _require(
            row["in_domain_nonalias_relation_subkind"] is None
            and row["disposition"] == "predecessor_seal_defect"
            and row["law_gap_admitted"] is False
            and row["required_action"]
            == "readjudicate_source_row_and_reseal_before_tier_2"
            and row["adjudicative_rationale"]
            == "incompatible_endpoint_claim_cannot_be_admitted_as_alias_"
            "law_reseal_required"
            and semantic_finding in allowed_defect_findings
            and row["status"] == "blocked_predecessor_row",
            f"{label}: seal-defect adjudication",
        )
    _require(
        row["predecessor_adjudication_id"]
        == _row_id(
            "a12-predecessor-local-proof-adjudication:",
            [
                row["source_document_id"],
                row["source_local_evidence_id"],
                flags,
                row["disposition"],
            ],
        ),
        f"{label}: adjudication ID",
    )


def _validate_pilot_census(
    census: Mapping[str, Any],
    label: str,
) -> None:
    """Exact-walk and independently source-rebuild every census member."""
    _require(isinstance(census, dict), f"{label}: expected object")
    _require_exact_keys(census, PILOT_CENSUS_KEYS, label)
    for key, expected_keys in PILOT_CENSUS_NESTED_KEYS.items():
        nested = census[key]
        nested_label = f"{label} {key}"
        _require(isinstance(nested, dict), f"{nested_label}: expected object")
        _require_exact_keys(nested, expected_keys, nested_label)
        for member, value in nested.items():
            _require_int(value, f"{nested_label}.{member}")
    for key in PILOT_CENSUS_KEYS - frozenset(PILOT_CENSUS_NESTED_KEYS):
        _require_int(census[key], f"{label}.{key}")

    source_rebuilt = strict_json_loads(
        _authenticated_pilot_census_bytes(),
        "authenticated pilot census",
    )
    _require(isinstance(source_rebuilt, dict), "authenticated pilot census")
    _require_exact_keys(
        source_rebuilt,
        PILOT_CENSUS_KEYS,
        "authenticated pilot census",
    )
    for key in sorted(PILOT_CENSUS_KEYS):
        _require(
            census[key] == source_rebuilt[key],
            f"{label}: source reconstruction drift: {key}",
        )

    evidence_shapes = census["local_evidence_shape_counts"]
    raw_cardinality = census["serialized_component_parent_cardinality"]
    dispositions = census["component_parent_disposition_counts"]
    _require(
        census["role_anchor_count"]
        == census["head_role_anchor_count"]
        + census["spouse_role_anchor_count"],
        f"{label}: role count equation",
    )
    _require(
        census["source_component_anchor_count"]
        == census["source_context_anchor_count"]
        + census["source_remuneration_anchor_count"],
        f"{label}: component count equation",
    )
    _require(
        census["local_evidence_row_count"] == sum(evidence_shapes.values()),
        f"{label}: evidence-shape count equation",
    )
    _require(
        census["source_component_anchor_count"]
        == sum(raw_cardinality.values())
        == sum(dispositions.values()),
        f"{label}: component disposition total equation",
    )
    _require(
        raw_cardinality["zero"]
        == dispositions["zero_parent_terminal_disposition"]
        and raw_cardinality["one"]
        == dispositions["unique_parent_assignment"]
        + dispositions["zero_lawful_parent_terminal_disposition"]
        and raw_cardinality["multiple"]
        == dispositions["multi_parent_ambiguity_no_selection"],
        f"{label}: component disposition arm equations",
    )
    _require(
        census["lawful_repeat_coverage_multiple_arm_instruction_count"] == 0,
        f"{label}: repeat multiple-arm equation",
    )
    _require(
        census["in_domain_nonalias_relation_instruction_count"]
        == census["noncatalog_aggregate_relation_instruction_count"]
        + census["in_domain_redirection_instruction_count"],
        f"{label}: in-domain relation subkind equation",
    )
    _require(
        census["repeat_occurrence_count"]
        == census["valid_direct_proof_instruction_count"]
        + census["outside_domain_instruction_count"]
        + census["in_domain_nonalias_relation_instruction_count"]
        + census["disclosed_stop_instruction_count"],
        f"{label}: four-disposition repeat exact-cover equation",
    )
    _require(
        census["disclosed_stop_instruction_count"]
        == census["otherwise_unresolved_instruction_count"]
        + census["incompatible_proof_instruction_count"]
        - census["valid_and_incompatible_instruction_overlap_count"],
        f"{label}: unresolved repeat diagnostic equation",
    )


def validate_bundle(bundle: Mapping[str, Mapping[str, Any]]) -> None:
    """Validate a complete generated or committed pilot bundle."""
    _require(set(bundle) == set(OUTPUT_FILENAMES), "artifact bundle drift")
    for key, artifact in bundle.items():
        _require_exact_keys(
            artifact,
            ARTIFACT_TOP_LEVEL_KEYS[key],
            f"{key} artifact",
        )
        _validate_artifact_envelope(artifact, *ARTIFACT_SPECS[key])
        _validate_nonauthority(artifact["nonauthority_statement"])

    slice_artifact = bundle["slice"]
    _require_int(slice_artifact["tier"], "slice tier")
    _require(slice_artifact["tier"] == 1, "slice tier drift")
    design_identity = slice_artifact["design_prefix_identity"]
    _require(isinstance(design_identity, dict), "design prefix identity")
    _require_exact_keys(
        design_identity, DESIGN_PREFIX_IDENTITY_KEYS, "design prefix identity"
    )
    _require(
        design_identity
        == {
            "path": "docs/design/covered_earnings_correction.md",
            "byte_size": DESIGN_PREFIX_BYTES,
            "sha256": DESIGN_PREFIX_SHA256,
            "identity_scope": "immutable_revision_13_prefix",
        },
        "design prefix identity drift",
    )
    _validate_source_corpus_identity(slice_artifact["source_corpus_identity"])
    _require(
        slice_artifact["control_selection_rule"]
        == "earliest_source_order_noncarrier_in_each_era_with_zero_"
        "outside_domain_rows_zero_defective_populated_proof_rows_"
        "and_zero_aggregate_kind_component_slot_rows",
        "pilot control-selection rule drift",
    )
    _require(
        tuple(slice_artifact["pilot_document_positions"]) == PILOT_POSITIONS,
        "pilot positions drift",
    )
    pilot_rows = slice_artifact["pilot_document_rows"]
    _require(len(pilot_rows) == 16, "pilot document count drift")
    for row in pilot_rows:
        _require_exact_keys(row, PILOT_DOCUMENT_ROW_KEYS, "pilot document row")
        position = row["document_source_position"]
        _require(
            row["selection_tags"] == list(PILOT_TAGS[position]),
            "pilot tag drift",
        )
        _require(
            row["pilot_role"]
            == (
                "clean_era_control"
                if position in CONTROL_POSITIONS
                else "charter_pathology_carrier"
            ),
            "pilot role drift",
        )
    _require(
        [row["document_source_position"] for row in pilot_rows]
        == list(PILOT_POSITIONS),
        "pilot document order drift",
    )
    _require(
        slice_artifact["pilot_document_count"] == len(pilot_rows),
        "pilot document count mismatch",
    )
    _require(
        slice_artifact["pilot_document_position_domain_sha256"]
        == _domain_sha(list(PILOT_POSITIONS)),
        "pilot position digest drift",
    )
    _require(
        slice_artifact["pilot_annotation_raw_byte_count"]
        == sum(row["annotation_byte_size"] for row in pilot_rows),
        "pilot byte count drift",
    )
    _require(
        {
            row["document_source_position"]
            for row in pilot_rows
            if row["pilot_role"] == "clean_era_control"
        }
        == set(CONTROL_POSITIONS),
        "control membership drift",
    )

    census = slice_artifact["pilot_census"]
    _validate_pilot_census(census, "slice pilot census")
    expected_census = {
        "document_count": 16,
        "questionnaire_page_count": 1_571,
        "questionnaire_occurrence_count": 13_219,
        "flow_branch_count": 3_480,
        "local_anchor_count": 6_123,
        "field_purpose_count": 3_240,
        "role_anchor_count": 949,
        "head_role_anchor_count": 530,
        "spouse_role_anchor_count": 419,
        "job_anchor_count": 1_534,
        "source_component_anchor_count": 3_095,
        "source_context_anchor_count": 2_247,
        "source_remuneration_anchor_count": 848,
        "aggregate_anchor_count": 545,
        "repeat_occurrence_count": 376,
        "local_evidence_row_count": 418,
        "valid_direct_proof_instruction_count": 81,
        "outside_domain_instruction_count": 34,
        "noncatalog_aggregate_relation_instruction_count": 1,
        "in_domain_redirection_instruction_count": 2,
        "in_domain_nonalias_relation_instruction_count": 3,
        "incompatible_proof_instruction_count": 30,
        "valid_and_incompatible_instruction_overlap_count": 0,
        "lawful_repeat_coverage_multiple_arm_instruction_count": 0,
        "disclosed_stop_instruction_count": 258,
        "otherwise_unresolved_instruction_count": 228,
        "raw_cross_category_multi_parent_count": 86,
        "eligible_cross_category_multi_parent_count": 86,
        "eligible_ineligible_mixed_multi_parent_count": 0,
        "ineligible_parent_reference_count": 22,
    }
    for key, expected in expected_census.items():
        _require(census[key] == expected, f"pilot census drift: {key}")
    _require(
        census["local_evidence_shape_counts"]
        == {
            "both_endpoints": 156,
            "no_endpoints": 254,
            "partial_endpoints": 8,
        },
        "pilot evidence-shape census drift",
    )
    _require(
        census["serialized_component_parent_cardinality"]
        == {"zero": 1_466, "one": 1_329, "multiple": 300},
        "pilot raw parent census drift",
    )

    sweep = bundle["sweeps"]
    _require(
        sweep["document_positions_swept"] == list(range(1, 82))
        and sweep["document_count"] == 81,
        "corpus sweep document domain drift",
    )
    role_classes = _validate_row_digests(
        sweep,
        "role_exact_label_class_rows",
        "role_exact_label_class_count",
        "role_exact_label_class_domain_sha256",
    )
    _require(len(role_classes) == 273, "role class count drift")
    _require(
        sum(row["member_count"] for row in role_classes) == 10_521,
        "role sweep member count drift",
    )
    _require(
        sum(row["role"] == ROLE_HEAD for row in role_classes) == 86,
        "head label class count drift",
    )
    _require(
        sum(row["role"] == ROLE_SPOUSE for row in role_classes) == 187,
        "spouse label class count drift",
    )
    for row in role_classes:
        _validate_role_class_row(row, "role sweep class row")
    _require(
        len({row["exact_label"] for row in role_classes}) == len(role_classes),
        "role sweep duplicate exact-label class",
    )
    sweep_role_member_ids = [
        member
        for row in role_classes
        for member in row["member_occurrence_ids"]
    ]
    _require(
        len(set(sweep_role_member_ids)) == len(sweep_role_member_ids),
        "role sweep member occurs in multiple classes",
    )
    _require(
        sweep["role_anchor_count"] == len(sweep_role_member_ids),
        "role sweep anchor count drift",
    )
    _require(
        sweep["role_noncanonical_assignment_reach_count"]
        == len(sweep_role_member_ids) - len(ROLE_CANONICALS),
        "role sweep noncanonical reach drift",
    )
    _require(
        sweep["role_cross_classification_label_count"] == 0,
        "role sweep cross-classification label",
    )
    _require(sweep["role_unreached_anchor_rows"] == [], "unreached roles")
    _require(sweep["role_unreached_anchor_count"] == 0, "unreached count")
    _require(
        sweep["role_exact_label_class_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["role_exact_label_class"],
        "role sweep pinned source projection drift",
    )

    sweep_repeat_rows = _validate_row_digests(
        sweep,
        "outside_domain_repeat_shape_rows",
        "outside_domain_repeat_shape_count",
        "outside_domain_repeat_shape_domain_sha256",
    )
    _require(len(sweep_repeat_rows) == 34, "outside repeat sweep drift")
    for row in sweep_repeat_rows:
        _validate_outside_repeat_row(row, "repeat sweep row")
    _require(
        sweep["outside_domain_repeat_shape_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["outside_domain_repeat_shape"],
        "repeat sweep pinned source projection drift",
    )
    sweep_aggregate_rows = _validate_row_digests(
        sweep,
        "noncatalog_aggregate_relation_shape_rows",
        "noncatalog_aggregate_relation_shape_count",
        "noncatalog_aggregate_relation_shape_domain_sha256",
    )
    _require(len(sweep_aggregate_rows) == 13, "aggregate relation sweep drift")
    for row in sweep_aggregate_rows:
        _validate_noncatalog_aggregate_relation_row(
            row, "aggregate relation sweep row"
        )
    _require(
        sweep["noncatalog_aggregate_relation_shape_keyset_sha256"]
        == _keyset_sha(
            [
                row["noncatalog_aggregate_relation_disposition_id"]
                for row in sweep_aggregate_rows
            ]
        ),
        "aggregate relation sweep keyset drift",
    )
    _require(
        sweep["noncatalog_aggregate_relation_shape_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256[
            "noncatalog_aggregate_relation_shape_keyset"
        ]
        and sweep["noncatalog_aggregate_relation_shape_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["noncatalog_aggregate_relation_shape"],
        "aggregate relation sweep pinned source projection drift",
    )
    sweep_redirection_rows = _validate_row_digests(
        sweep,
        "in_domain_redirection_shape_rows",
        "in_domain_redirection_shape_count",
        "in_domain_redirection_shape_domain_sha256",
    )
    _require(len(sweep_redirection_rows) == 5, "redirection sweep drift")
    for row in sweep_redirection_rows:
        _validate_in_domain_redirection_row(row, "redirection sweep row")
    _require(
        sweep["in_domain_redirection_shape_keyset_sha256"]
        == _keyset_sha(
            [
                row["in_domain_redirection_relation_disposition_id"]
                for row in sweep_redirection_rows
            ]
        )
        == PINNED_SWEEP_DOMAIN_SHA256["in_domain_redirection_shape_keyset"]
        and sweep["in_domain_redirection_shape_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["in_domain_redirection_shape"],
        "redirection sweep pinned source projection drift",
    )
    expected_cross_reference_structural_census = {
        "explicit_cross_reference_evidence_count": 1_915,
        "explicit_cross_reference_instruction_count": 1_874,
        "complete_cross_reference_evidence_count": 309,
        "complete_cross_reference_instruction_count": 268,
        "in_domain_nonaggregate_cross_reference_evidence_count": 292,
        "in_domain_nonaggregate_cross_reference_instruction_count": 252,
        "wholly_in_domain_nonaggregate_cross_reference_evidence_count": 287,
        "wholly_in_domain_nonaggregate_cross_reference_instruction_count": 251,
        "component_cross_reference_evidence_count": 217,
        "component_cross_reference_instruction_count": 178,
        "binary_component_cross_reference_evidence_count": 205,
        "binary_component_cross_reference_instruction_count": 166,
    }
    _require(
        {key: sweep[key] for key in expected_cross_reference_structural_census}
        == expected_cross_reference_structural_census,
        "cross-reference structural narrowing census drift",
    )
    component_cross_reference_rows = _validate_row_digests(
        sweep,
        "in_domain_component_cross_reference_sweep_rows",
        "in_domain_component_cross_reference_sweep_count",
        "in_domain_component_cross_reference_sweep_domain_sha256",
    )
    _require(
        len(component_cross_reference_rows) == 162
        and sum(
            row["source_evidence_count"]
            for row in component_cross_reference_rows
        )
        == 195
        and Counter(
            row["source_evidence_count"]
            for row in component_cross_reference_rows
        )
        == {1: 138, 2: 15, 3: 9},
        "component cross-reference sweep census drift",
    )
    for row in component_cross_reference_rows:
        _validate_in_domain_component_cross_reference_sweep_row(
            row, "component cross-reference sweep row"
        )
    component_cross_reference_ids = [
        row["in_domain_component_cross_reference_sweep_id"]
        for row in component_cross_reference_rows
    ]
    component_cross_reference_instruction_ids = [
        row["source_instruction_occurrence_id"]
        for row in component_cross_reference_rows
    ]
    component_cross_reference_evidence_ids = [
        evidence_id
        for row in component_cross_reference_rows
        for evidence_id in row["source_local_evidence_ids"]
    ]
    _require(
        len(component_cross_reference_ids)
        == len(set(component_cross_reference_ids))
        and len(component_cross_reference_instruction_ids)
        == len(set(component_cross_reference_instruction_ids))
        and len(component_cross_reference_evidence_ids)
        == len(set(component_cross_reference_evidence_ids)),
        "component cross-reference sweep duplicate group or evidence edge",
    )
    _require(
        sweep["in_domain_component_cross_reference_sweep_keyset_sha256"]
        == _keyset_sha(component_cross_reference_ids)
        == PINNED_SWEEP_DOMAIN_SHA256[
            "in_domain_component_cross_reference_sweep_keyset"
        ]
        and sweep["in_domain_component_cross_reference_sweep_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256[
            "in_domain_component_cross_reference_sweep"
        ],
        "component cross-reference sweep pinned source projection drift",
    )
    component_cross_reference_counts = _component_cross_reference_sweep_counts(
        component_cross_reference_rows
    )
    for suffix in (
        "instruction_count",
        "edge_count",
        "alias_instruction_count",
        "alias_edge_count",
        "alias_pair_count",
        "redirection_instruction_count",
        "redirection_edge_count",
        "stop_instruction_count",
        "stop_edge_count",
    ):
        artifact_key = (
            "in_domain_component_cross_reference_sweep_count"
            if suffix == "instruction_count"
            else f"in_domain_component_cross_reference_sweep_{suffix}"
        )
        _require(
            sweep[artifact_key] == component_cross_reference_counts[suffix],
            f"component cross-reference sweep {suffix} drift",
        )
    _require(
        component_cross_reference_counts
        == {
            "instruction_count": 162,
            "edge_count": 195,
            "alias_instruction_count": 120,
            "redirection_instruction_count": 5,
            "stop_instruction_count": 37,
            "alias_edge_count": 135,
            "alias_pair_count": 136,
            "redirection_edge_count": 6,
            "stop_edge_count": 54,
        },
        "component cross-reference partition drift",
    )
    semantic_input_rows = sweep["alias_semantic_input_identity_rows"]
    expected_semantic_input_rows = [
        {
            "path": NONLEDGER_ALIAS_ADJUDICATION_PATH.relative_to(
                ROOT
            ).as_posix(),
            "byte_size": NONLEDGER_ALIAS_ADJUDICATION_BYTE_SIZE,
            "raw_sha256": NONLEDGER_ALIAS_ADJUDICATION_SHA256,
        },
        {
            "path": COMPOSITE_ALIAS_ADJUDICATION_PATH.relative_to(
                ROOT
            ).as_posix(),
            "byte_size": COMPOSITE_ALIAS_ADJUDICATION_BYTE_SIZE,
            "raw_sha256": COMPOSITE_ALIAS_ADJUDICATION_SHA256,
        },
        {
            "path": COMPOSITE_INSTRUCTION_LAW_PATH.relative_to(
                ROOT
            ).as_posix(),
            "byte_size": COMPOSITE_INSTRUCTION_LAW_BYTE_SIZE,
            "raw_sha256": COMPOSITE_INSTRUCTION_LAW_SHA256,
        },
    ]
    _require(
        isinstance(semantic_input_rows, list)
        and all(
            frozenset(row) == ALIAS_SEMANTIC_INPUT_IDENTITY_ROW_KEYS
            for row in semantic_input_rows
        )
        and semantic_input_rows == expected_semantic_input_rows
        and sweep["alias_semantic_input_identity_count"] == 3
        and sweep["alias_semantic_input_identity_domain_sha256"]
        == _domain_sha(semantic_input_rows)
        == PINNED_SWEEP_DOMAIN_SHA256["alias_semantic_input_identity"],
        "semantic alias input identities drift",
    )
    alias_evidence_adjudications = sweep[
        "alias_evidence_semantic_adjudication_rows"
    ]
    _require(
        isinstance(alias_evidence_adjudications, list),
        "alias evidence semantic adjudication rows",
    )
    embedded_pair_rows: list[Mapping[str, Any]] = []
    for row in alias_evidence_adjudications:
        embedded_pair_rows.extend(
            _validate_alias_evidence_semantic_adjudication_row(
                row, "alias evidence semantic adjudication row"
            )
        )
    evidence_adjudication_ids = [
        row["semantic_alias_evidence_adjudication_id"]
        for row in alias_evidence_adjudications
    ]
    evidence_ids = [
        row["source_local_evidence_id"] for row in alias_evidence_adjudications
    ]
    pair_ids = [
        row["semantic_alias_pair_adjudication_id"]
        for row in embedded_pair_rows
    ]
    expected_decisions = {
        "approved_pairwise_decomposition": 19,
        "approved_pairwise_typed_projection": 29,
        "approved_single_pair": 181,
        "disclosed_stop": 36,
    }
    expected_origins = {
        "ca41663_nonledger_bypass_adjudication": 108,
        "ca41663_structural_ledger_admission": 154,
        "round_five_continuation_restoration": 3,
    }
    _require(
        sweep["alias_evidence_semantic_adjudication_count"]
        == len(alias_evidence_adjudications)
        == len(evidence_adjudication_ids)
        == len(set(evidence_adjudication_ids))
        == len(evidence_ids)
        == len(set(evidence_ids))
        == 265
        and sweep["ca41663_alias_evidence_adjudication_count"] == 262
        and sweep["round_five_continuation_restoration_count"] == 3
        and sweep["continuation_composition_citation_count"] == 5
        and sweep["approved_alias_evidence_count"] == 229
        and sweep["disclosed_stop_alias_evidence_count"] == 36
        and sweep["alias_evidence_semantic_adjudication_keyset_sha256"]
        == _keyset_sha(evidence_adjudication_ids)
        == PINNED_SWEEP_DOMAIN_SHA256[
            "alias_evidence_semantic_adjudication_keyset"
        ]
        and sweep["alias_evidence_semantic_adjudication_domain_sha256"]
        == _domain_sha(alias_evidence_adjudications)
        == PINNED_SWEEP_DOMAIN_SHA256["alias_evidence_semantic_adjudication"]
        and sweep["alias_evidence_semantic_decision_counts"]
        == expected_decisions
        and sweep["alias_evidence_semantic_candidate_origin_counts"]
        == expected_origins,
        "sole semantic gate evidence census drift",
    )
    approved_pair_rows = sweep["approved_alias_pair_rows"]
    _require(
        isinstance(approved_pair_rows, list)
        and approved_pair_rows == embedded_pair_rows
        and len(pair_ids) == len(set(pair_ids)) == 258
        and sweep["approved_alias_pair_count"] == 258
        and sweep["approved_alias_pair_keyset_sha256"]
        == _keyset_sha(pair_ids)
        == PINNED_SWEEP_DOMAIN_SHA256["approved_alias_pair_keyset"]
        and sweep["approved_alias_pair_domain_sha256"]
        == _domain_sha(approved_pair_rows)
        == PINNED_SWEEP_DOMAIN_SHA256["approved_alias_pair"]
        and sweep["occurrence_closure_alias_pair_count"] == 228
        and sweep["typed_projection_alias_pair_count"] == 30
        and sum(row["class_closure_eligible"] for row in approved_pair_rows)
        == 228
        and sum(
            row["typed_projection_union_prohibited"]
            for row in approved_pair_rows
        )
        == 30,
        "sole semantic gate pair census drift",
    )
    semantic_row_by_evidence_id = {
        row["source_local_evidence_id"]: row
        for row in alias_evidence_adjudications
    }
    for structural_row in component_cross_reference_rows:
        for evidence_id in structural_row["source_local_evidence_ids"]:
            if evidence_id not in semantic_row_by_evidence_id:
                continue
            semantic_row = semantic_row_by_evidence_id[evidence_id]
            _require(
                semantic_row["continuation_composition_citation"]
                == structural_row["continuation_composition_citation"],
                "continuation citation differs across semantic ledgers",
            )
    semantic_adjudication_ids = [
        row["semantic_alias_adjudication_id"]
        for row in component_cross_reference_rows
    ]
    _require(
        sweep["semantic_alias_adjudication_count"]
        == len(semantic_adjudication_ids)
        == len(set(semantic_adjudication_ids))
        and sweep["semantic_alias_adjudication_keyset_sha256"]
        == _keyset_sha(semantic_adjudication_ids)
        and sweep["semantic_alias_adjudication_domain_sha256"]
        == _domain_sha(component_cross_reference_rows)
        and sweep["semantic_alias_adjudication_outcome_counts"]
        == {
            key: component_cross_reference_counts[key]
            for key in (
                "alias_instruction_count",
                "alias_edge_count",
                "alias_pair_count",
                "redirection_instruction_count",
                "redirection_edge_count",
                "stop_instruction_count",
                "stop_edge_count",
            )
        },
        "semantic alias adjudication aggregate drift",
    )
    outcome_rows = [
        [
            row["source_instruction_occurrence_id"],
            _semantic_alias_outcome_code(row),
        ]
        for row in component_cross_reference_rows
    ]
    outcome_instruction_ids = {
        outcome: [
            row["source_instruction_occurrence_id"]
            for row in component_cross_reference_rows
            if _semantic_alias_outcome_code(row) == outcome
        ]
        for outcome in ("A", "R", "S")
    }
    _require(
        sweep["semantic_alias_adjudication_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["semantic_alias_adjudication_keyset"]
        and sweep["semantic_alias_instruction_outcome_domain_sha256"]
        == _domain_sha(outcome_rows)
        == PINNED_SWEEP_DOMAIN_SHA256["semantic_alias_instruction_outcome"]
        and sweep["semantic_alias_equivalence_instruction_keyset_sha256"]
        == _keyset_sha(outcome_instruction_ids["A"])
        == PINNED_SWEEP_DOMAIN_SHA256[
            "semantic_alias_equivalence_instruction_keyset"
        ]
        and sweep["semantic_alias_redirection_instruction_keyset_sha256"]
        == _keyset_sha(outcome_instruction_ids["R"])
        == PINNED_SWEEP_DOMAIN_SHA256[
            "semantic_alias_redirection_instruction_keyset"
        ]
        and sweep["semantic_alias_stop_instruction_keyset_sha256"]
        == _keyset_sha(outcome_instruction_ids["S"])
        == PINNED_SWEEP_DOMAIN_SHA256[
            "semantic_alias_stop_instruction_keyset"
        ],
        "semantic alias adjudication source projection pin drift",
    )
    _require(
        Counter(
            row["tier_2_predecessor_ledger_note"]
            for row in component_cross_reference_rows
        )
        == {
            "round_three_reseal_ledger_already_covers_fragment": 4,
            "new_tier_2_reseal_required_for_incomplete_fragment": 10,
            "fragment_semantically_decisive_no_reseal_required": 34,
            "not_a_source_instruction_fragment": 114,
        },
        "semantic alias fragment ledger census drift",
    )
    fragment_instruction_ids = [
        row["source_instruction_occurrence_id"]
        for row in component_cross_reference_rows
        if row["source_instruction_fragment"]
    ]
    new_fragment_instruction_ids = [
        row["source_instruction_occurrence_id"]
        for row in component_cross_reference_rows
        if row["tier_2_predecessor_ledger_note"]
        == "new_tier_2_reseal_required_for_incomplete_fragment"
    ]
    _require(
        sweep["semantic_alias_source_instruction_fragment_count"] == 48
        and sweep["semantic_alias_fragment_seal_quality_issue_count"] == 14
        and sweep["semantic_alias_round_three_fragment_reseal_count"] == 4
        and sweep["semantic_alias_round_four_new_fragment_reseal_count"] == 10
        and sweep["semantic_alias_decisive_fragment_no_reseal_count"] == 34
        and sweep["semantic_alias_fragment_instruction_keyset_sha256"]
        == _keyset_sha(fragment_instruction_ids)
        == PINNED_SWEEP_DOMAIN_SHA256[
            "semantic_alias_fragment_instruction_keyset"
        ]
        and sweep["semantic_alias_round_four_new_fragment_keyset_sha256"]
        == _keyset_sha(new_fragment_instruction_ids)
        == PINNED_SWEEP_DOMAIN_SHA256[
            "semantic_alias_round_four_new_fragment_keyset"
        ],
        "semantic alias fragment source projection pin drift",
    )
    pilot_component_cross_reference_rows = [
        row
        for row in component_cross_reference_rows
        if row["pilot_document_member"]
    ]
    pilot_component_cross_reference_counts = (
        _component_cross_reference_sweep_counts(
            pilot_component_cross_reference_rows
        )
    )
    for suffix in (
        "instruction_count",
        "edge_count",
        "alias_instruction_count",
        "alias_edge_count",
        "alias_pair_count",
        "redirection_instruction_count",
        "redirection_edge_count",
        "stop_instruction_count",
        "stop_edge_count",
    ):
        artifact_key = (
            "pilot_in_domain_component_cross_reference_sweep_count"
            if suffix == "instruction_count"
            else "pilot_in_domain_component_cross_reference_sweep_" + suffix
        )
        _require(
            sweep[artifact_key]
            == pilot_component_cross_reference_counts[suffix],
            f"pilot component cross-reference sweep {suffix} drift",
        )
    _require(
        pilot_component_cross_reference_counts
        == {
            "instruction_count": 91,
            "edge_count": 123,
            "alias_instruction_count": 64,
            "redirection_instruction_count": 2,
            "stop_instruction_count": 25,
            "alias_edge_count": 78,
            "alias_pair_count": 79,
            "redirection_edge_count": 3,
            "stop_edge_count": 42,
        },
        "pilot component cross-reference partition drift",
    )
    _require(
        [
            row["in_domain_redirection_relation_disposition_id"]
            for row in component_cross_reference_rows
            if row["repeat_coverage_disposition"]
            == "admitted_exclusive_destination_redirection"
        ]
        == [
            row["in_domain_redirection_relation_disposition_id"]
            for row in sweep_redirection_rows
        ],
        "component cross-reference sweep does not exact-walk R members",
    )
    redirection_lineage_rows = _validate_row_digests(
        sweep,
        "exclusive_destination_redirection_lineage_rows",
        "exclusive_destination_redirection_lineage_count",
        "exclusive_destination_redirection_lineage_domain_sha256",
    )
    _require(
        len(redirection_lineage_rows) == 45
        and sum(
            len(row["source_local_evidence_ids"])
            for row in redirection_lineage_rows
        )
        == 46
        and Counter(
            row["source_text_shape_kind"] for row in redirection_lineage_rows
        )
        == {
            "business_owner_pay_exclusive_placement": 16,
            "primary_farm_income_exclusive_placement": 26,
            "labor_income_g78_exclusive_placement": 3,
        },
        "lexical redirection lineage regression census drift",
    )
    for row in redirection_lineage_rows:
        _validate_redirection_lineage_row(
            row, "lexical redirection lineage regression row"
        )
    _require(
        sweep["exclusive_destination_redirection_lineage_keyset_sha256"]
        == _keyset_sha(
            [
                row["exclusive_destination_redirection_lineage_id"]
                for row in redirection_lineage_rows
            ]
        )
        == PINNED_SWEEP_DOMAIN_SHA256[
            "exclusive_destination_redirection_lineage_keyset"
        ]
        and sweep["exclusive_destination_redirection_lineage_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256[
            "exclusive_destination_redirection_lineage"
        ],
        "lexical redirection lineage pinned source projection drift",
    )
    _require(
        sweep["repeat_instruction_text_scan_count"] == 2_460
        and sweep["literal_cross_reference_instruction_count"] == 8
        and sweep["exclusive_destination_redirection_lineage_admitted_count"]
        == 5
        and sweep["exclusive_destination_redirection_lineage_aggregate_count"]
        == 2
        and sweep["exclusive_destination_redirection_lineage_stop_count"] == 38
        and sweep["exclusive_destination_redirection_lineage_mixed_stop_count"]
        == 3
        and sweep[
            "exclusive_destination_redirection_lineage_incomplete_stop_count"
        ]
        == 35,
        "redirection source-text sweep counts drift",
    )
    admitted_lineage_rows = [
        row
        for row in redirection_lineage_rows
        if row["in_domain_redirection_arm_eligible"]
    ]
    _require(
        [
            row["in_domain_redirection_relation_disposition_id"]
            for row in admitted_lineage_rows
        ]
        == [
            row["in_domain_redirection_relation_disposition_id"]
            for row in sweep_redirection_rows
        ],
        "redirection lineage does not exact-walk admitted members",
    )
    aggregate_lineage_ids = {
        row["existing_aggregate_relation_disposition_id"]
        for row in redirection_lineage_rows
        if row["existing_aggregate_relation_disposition_id"] is not None
    }
    _require(
        aggregate_lineage_ids
        == {
            row["noncatalog_aggregate_relation_disposition_id"]
            for row in sweep_aggregate_rows
            if row["source_instruction_occurrence_ids"][0]
            in {
                lineage_row["source_instruction_occurrence_id"]
                for lineage_row in redirection_lineage_rows
            }
        },
        "redirection lineage does not exact-walk aggregate members",
    )
    _require(
        sweep["repeat_coverage_census"]
        == {
            "repeat_occurrence_count": 2_460,
            "valid_direct_proof_instruction_count": 207,
            "outside_domain_instruction_count": 34,
            "noncatalog_aggregate_relation_instruction_count": 13,
            "in_domain_redirection_instruction_count": 5,
            "in_domain_nonalias_relation_instruction_count": 18,
            "incompatible_proof_instruction_count": 69,
            "valid_and_incompatible_instruction_overlap_count": 0,
            "lawful_repeat_coverage_multiple_arm_instruction_count": 0,
            "disclosed_stop_instruction_count": 2_201,
            "otherwise_unresolved_instruction_count": 2_132,
        },
        "corpus repeat coverage census drift",
    )
    aggregate_instruction_ids = {
        row["source_instruction_occurrence_ids"][0]
        for row in sweep_aggregate_rows
    }
    outside_instruction_ids = {
        row["source_instruction_occurrence_id"] for row in sweep_repeat_rows
    }
    redirection_instruction_ids = {
        row["source_instruction_occurrence_ids"][0]
        for row in sweep_redirection_rows
    }
    _require(
        len(aggregate_instruction_ids) == len(sweep_aggregate_rows)
        and len(redirection_instruction_ids) == len(sweep_redirection_rows)
        and not aggregate_instruction_ids & outside_instruction_ids
        and not redirection_instruction_ids & outside_instruction_ids
        and not aggregate_instruction_ids & redirection_instruction_ids,
        "in-domain and outside repeat arms overlap",
    )

    parent_source_witness_rows = _validate_row_digests(
        sweep,
        "parent_source_witness_rows",
        "parent_source_witness_count",
        "parent_source_witness_domain_sha256",
    )
    for row in parent_source_witness_rows:
        _validate_parent_source_witness_row(row)
    _require(
        sweep["parent_source_witness_keyset_sha256"]
        == _keyset_sha(
            [
                row["parent_source_witness_id"]
                for row in parent_source_witness_rows
            ]
        ),
        "parent source witness keyset drift",
    )
    _require(
        sweep["parent_source_witness_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["parent_source_witness_keyset"]
        and sweep["parent_source_witness_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["parent_source_witness"],
        "parent witness pinned source projection drift",
    )
    source_witness_by_key = {
        (row["document_source_position"], row["parent_occurrence_id"]): row
        for row in parent_source_witness_rows
    }
    _require(
        len(source_witness_by_key) == len(parent_source_witness_rows),
        "duplicate parent source witness",
    )

    component_shapes = _validate_row_digests(
        sweep,
        "component_parent_shape_rows",
        "component_parent_shape_count",
        "component_parent_shape_domain_sha256",
    )
    _require(len(component_shapes) == 21_283, "component sweep count drift")
    for row in component_shapes:
        _validate_component_shape_row(
            row, source_witness_by_key, "component sweep row"
        )
    _require(
        sweep["component_parent_shape_keyset_sha256"]
        == _keyset_sha(
            [row["component_parent_resolution_id"] for row in component_shapes]
        ),
        "component sweep keyset drift",
    )
    _require(
        sweep["component_parent_shape_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["component_parent_shape_keyset"]
        and sweep["component_parent_shape_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["component_parent_shape"],
        "component sweep pinned source projection drift",
    )
    _require(
        sweep["serialized_parent_cardinality_counts"]
        == {"zero": 10_664, "one": 8_809, "multiple": 1_810},
        "full raw parent census drift",
    )
    _require(
        sweep["component_parent_disposition_counts"]
        == {
            "multi_parent_ambiguity_no_selection": 1_810,
            "unique_parent_assignment": 8_779,
            "zero_lawful_parent_terminal_disposition": 30,
            "zero_parent_terminal_disposition": 10_664,
        },
        "full parent disposition census drift",
    )
    referenced_parent_source_keys = {
        (row["document_source_position"], candidate["parent_occurrence_id"])
        for row in component_shapes
        for candidate in row["parent_candidate_rows"]
    }
    _require(
        referenced_parent_source_keys == set(source_witness_by_key),
        "parent source witness coverage drift",
    )
    _require(
        sweep["raw_cross_category_multi_parent_count"] == 466,
        "raw cross-category parent census drift",
    )
    _require(
        sweep["eligible_cross_category_multi_parent_count"] == 462,
        "eligible cross-category parent census drift",
    )
    _require(
        sweep["eligible_ineligible_mixed_multi_parent_count"] == 4,
        "eligible/ineligible parent census drift",
    )
    _require(
        sweep["ineligible_parent_reference_count"] == 34,
        "ineligible parent census drift",
    )

    derived = bundle["derived"]
    _require(derived["tier"] == 1, "derived sweep tier drift")
    job_complement_rows = _validate_row_digests(
        derived,
        "catalog_only_job_complement_sweep_rows",
        "catalog_only_job_complement_sweep_count",
        "catalog_only_job_complement_sweep_domain_sha256",
    )
    _require(len(job_complement_rows) == 12_378, "job class count drift")
    _require(
        derived["catalog_only_job_complement_sweep_keyset_sha256"]
        == _keyset_sha(
            [
                row["catalog_only_job_complement_sweep_id"]
                for row in job_complement_rows
            ]
        ),
        "job complement sweep keyset drift",
    )
    for row in job_complement_rows:
        _validate_catalog_only_job_complement_sweep_row(row)
    job_class_by_id = {
        row["candidate_job_class_id"]: row for row in job_complement_rows
    }
    _require(
        len(job_class_by_id) == len(job_complement_rows),
        "duplicate candidate job class ID",
    )
    candidate_job_id_by_occurrence: dict[str, str] = {}
    for row in job_complement_rows:
        for occurrence_id in row["job_class_member_occurrence_ids"]:
            _require(
                occurrence_id not in candidate_job_id_by_occurrence,
                "job occurrence belongs to multiple candidate classes",
            )
            candidate_job_id_by_occurrence[occurrence_id] = row[
                "candidate_job_class_id"
            ]
    _require(
        len(candidate_job_id_by_occurrence) == 14_326
        and derived["job_class_member_occurrence_count"] == 14_326,
        "job class member exact cover drift",
    )
    job_support_origin_counts = Counter(
        support["support_origin"]
        for row in job_complement_rows
        for support in row["alias_support_rows"]
    )
    _require(
        derived["job_alias_support_origin_counts"]
        == dict(sorted(job_support_origin_counts.items())),
        "job alias support census drift",
    )

    component_class_rows = _validate_row_digests(
        derived,
        "component_class_admission_sweep_rows",
        "component_class_admission_sweep_count",
        "component_class_admission_sweep_domain_sha256",
    )
    _require(
        len(component_class_rows) == 19_585,
        "component candidate class count drift",
    )
    _require(
        derived["component_class_admission_sweep_keyset_sha256"]
        == _keyset_sha(
            [
                row["component_class_admission_sweep_id"]
                for row in component_class_rows
            ]
        ),
        "component class admission sweep keyset drift",
    )
    component_class_by_id = {
        row["candidate_component_class_id"]: row
        for row in component_class_rows
    }
    _require(
        len(component_class_by_id) == len(component_class_rows),
        "duplicate candidate component class ID",
    )
    shape_by_occurrence = {
        row["component_anchor_occurrence_id"]: row for row in component_shapes
    }
    component_member_ids: list[str] = []
    for row in component_class_rows:
        _validate_component_class_admission_sweep_row(row)
        members = row["component_class_member_occurrence_ids"]
        component_member_ids.extend(members)
        _require(
            all(member in shape_by_occurrence for member in members),
            "candidate component class has unknown source member",
        )
        member_shapes = [shape_by_occurrence[member] for member in members]
        _require(
            {shape["component_kind"] for shape in member_shapes}
            == {row["component_kind"]},
            "candidate component class kind drift",
        )
        fixture_members: list[dict[str, Any]] = []
        for shape in member_shapes:
            fixture_candidates: list[dict[str, Any]] = []
            for candidate in shape["parent_candidate_rows"]:
                resolved_parent = None
                if candidate["eligible_parent"]:
                    parent_kind = candidate["parent_occurrence_kind"]
                    if parent_kind == "job_anchor":
                        _require(
                            candidate["parent_occurrence_id"]
                            in candidate_job_id_by_occurrence,
                            "candidate component parent has no job class",
                        )
                        resolved_parent = candidate_job_id_by_occurrence[
                            candidate["parent_occurrence_id"]
                        ]
                    else:
                        resolved_parent = CANDIDATE_SENTINEL_PARENT_NODE_IDS[
                            parent_kind
                        ]
                fixture_candidates.append(
                    {
                        "source_parent_occurrence_id": candidate[
                            "parent_occurrence_id"
                        ],
                        "resolved_canonical_parent_node_id": resolved_parent,
                        "eligible_parent": candidate["eligible_parent"],
                        "derived_slot_kind": candidate["derived_slot_kind"],
                        "support_proof_id": _row_id(
                            "a12-candidate-parent-support:",
                            [
                                shape["component_anchor_occurrence_id"],
                                candidate["parent_occurrence_id"],
                            ],
                        ),
                    }
                )
            fixture_members.append(
                {
                    "component_anchor_occurrence_id": shape[
                        "component_anchor_occurrence_id"
                    ],
                    "parent_candidate_rows": fixture_candidates,
                }
            )
        folded = fold_component_class_fixture(
            row["component_kind"], fixture_members
        )
        _require(
            row["member_raw_parent_cardinalities"]
            == folded["member_raw_parent_cardinalities"]
            and row["raw_parent_candidate_count"]
            == folded["raw_parent_candidate_count"]
            and row["eligible_canonical_parent_count"]
            == len(folded["resolved_canonical_parent_node_ids"])
            and row["candidate_disposition"] == folded["disposition"]
            and row["candidate_unique_parent_node_id"]
            == folded["unique_parent_node_id"]
            and row["candidate_unique_slot_kind"] == folded["unique_slot_kind"]
            and row["relationship_arm_eligible"]
            is folded["tier_2_relationship_arm_eligible"],
            "candidate component class fold drift",
        )
    _require(
        len(component_member_ids) == len(set(component_member_ids)) == 21_283
        and set(component_member_ids) == set(shape_by_occurrence)
        and derived["component_class_member_occurrence_count"] == 21_283,
        "component class member exact cover drift",
    )
    component_disposition_counts = dict(
        sorted(
            Counter(
                row["candidate_disposition"] for row in component_class_rows
            ).items()
        )
    )
    _require(
        derived["component_class_candidate_disposition_counts"]
        == component_disposition_counts,
        "component class disposition census drift",
    )
    relationship_eligible_count = sum(
        row["relationship_arm_eligible"] for row in component_class_rows
    )
    _require(
        derived["component_class_relationship_arm_eligible_count"]
        == relationship_eligible_count,
        "component relationship-arm census drift",
    )
    component_support_origin_counts = Counter(
        support["support_origin"]
        for row in component_class_rows
        for support in row["alias_support_rows"]
    )
    _require(
        derived["component_alias_support_origin_counts"]
        == dict(sorted(component_support_origin_counts.items())),
        "component alias support census drift",
    )
    sealed_alias_support_evidence_ids = {
        support["source_local_evidence_id"]
        for row in [*component_class_rows, *job_complement_rows]
        for support in row["alias_support_rows"]
        if support["support_origin"] == "sealed_local_evidence"
    }
    approved_pair_by_id = {
        row["semantic_alias_pair_adjudication_id"]: row
        for row in approved_pair_rows
    }
    sealed_alias_support_rows = [
        support
        for row in [*component_class_rows, *job_complement_rows]
        for support in row["alias_support_rows"]
        if support["support_origin"] == "sealed_local_evidence"
    ]
    for support in sealed_alias_support_rows:
        semantic_pair_id = support["semantic_alias_pair_adjudication_id"]
        _require(
            semantic_pair_id in approved_pair_by_id,
            "derived alias support lacks a semantic gate pair",
        )
        pair = approved_pair_by_id[semantic_pair_id]
        _require(
            pair["class_closure_eligible"] is True
            and pair["typed_projection_union_prohibited"] is False
            and support["source_local_evidence_id"]
            == pair["source_local_evidence_id"]
            and support["alias_anchor_occurrence_ids"]
            == [pair["alias_occurrence_id"]]
            and support["canonical_anchor_occurrence_ids"]
            == [pair["canonical_occurrence_id"]]
            and support["pairing_basis_code"] == pair["pairing_basis_code"],
            "typed or mismatched semantic pair entered occurrence closure",
        )
    semantic_stop_evidence_ids = {
        row["source_local_evidence_id"]
        for row in alias_evidence_adjudications
        if not row["approved_pair_rows"]
    }
    structural_alias_evidence_ids = {
        evidence_id
        for row in component_cross_reference_rows
        if row["repeat_coverage_disposition"] == "existing_alias_arm"
        for evidence_id in row["valid_alias_arm_evidence_ids"]
    }
    structural_nonalias_evidence_ids = {
        evidence_id
        for row in component_cross_reference_rows
        if row["repeat_coverage_disposition"] != "existing_alias_arm"
        for evidence_id in row["source_local_evidence_ids"]
    }
    explicit_nonalias_evidence_ids = (
        {row["source_local_evidence_id"] for row in sweep_repeat_rows}
        | {row["source_local_evidence_id"] for row in sweep_aggregate_rows}
        | {
            evidence_id
            for row in sweep_redirection_rows
            for evidence_id in row["source_local_evidence_ids"]
        }
    )
    _require(
        not sealed_alias_support_evidence_ids
        & (
            structural_nonalias_evidence_ids
            | explicit_nonalias_evidence_ids
            | semantic_stop_evidence_ids
        )
        and (
            sealed_alias_support_evidence_ids
            & {
                evidence_id
                for row in component_cross_reference_rows
                for evidence_id in row["source_local_evidence_ids"]
            }
        )
        <= structural_alias_evidence_ids,
        "R/G/T/STOP evidence entered derived alias support",
    )

    expected_relationship_components_by_job: defaultdict[str, list[str]] = (
        defaultdict(list)
    )
    for row in component_class_rows:
        parent_id = row["candidate_unique_parent_node_id"]
        if row["relationship_arm_eligible"] and parent_id in job_class_by_id:
            expected_relationship_components_by_job[parent_id].append(
                row["candidate_component_class_id"]
            )
    for row in job_complement_rows:
        _require(
            row["candidate_relationship_component_class_ids"]
            == expected_relationship_components_by_job[
                row["candidate_job_class_id"]
            ],
            "catalog-only job complement projection drift",
        )
    job_coverage_counts = dict(
        sorted(
            Counter(row["coverage_arm"] for row in job_complement_rows).items()
        )
    )
    _require(
        derived["catalog_only_job_coverage_arm_counts"] == job_coverage_counts,
        "catalog-only job coverage census drift",
    )
    _require(
        derived["component_class_admission_sweep_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["component_class_admission_keyset"]
        and derived["component_class_admission_sweep_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["component_class_admission"],
        "component class admission pinned source projection drift",
    )
    _require(
        derived["catalog_only_job_complement_sweep_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["catalog_only_job_complement_keyset"]
        and derived["catalog_only_job_complement_sweep_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["catalog_only_job_complement"],
        "catalog-only job complement pinned source projection drift",
    )

    predecessor = bundle["predecessor"]
    doc036_rows = _validate_row_digests(
        predecessor,
        "doc036_aggregate_component_slot_rows",
        "doc036_aggregate_component_slot_count",
        "doc036_aggregate_component_slot_domain_sha256",
    )
    proof_adjudications = _validate_row_digests(
        predecessor,
        "populated_local_proof_adjudication_rows",
        "populated_local_proof_adjudication_count",
        "populated_local_proof_adjudication_domain_sha256",
    )
    _require(len(doc036_rows) == 8, "doc036 defect count drift")
    _require(len(proof_adjudications) == 42, "proof adjudication count drift")
    for row in doc036_rows:
        _validate_doc036_defect_row(row)
    for row in proof_adjudications:
        _validate_proof_adjudication_row(row)
    _require(
        predecessor["doc036_aggregate_component_slot_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["doc036_aggregate_component_slot"],
        "doc036 adjudication pinned source projection drift",
    )
    _require(
        predecessor["populated_local_proof_adjudication_keyset_sha256"]
        == _keyset_sha(
            [row["source_local_evidence_id"] for row in proof_adjudications]
        ),
        "proof adjudication keyset drift",
    )
    _require(
        predecessor["populated_local_proof_adjudication_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["predecessor_proof_adjudication_keyset"]
        and predecessor["populated_local_proof_adjudication_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["predecessor_proof_adjudication"],
        "proof adjudication pinned source projection drift",
    )
    proof_seal_defects = [
        row
        for row in proof_adjudications
        if row["disposition"] == "predecessor_seal_defect"
    ]
    proof_law_gaps = [
        row for row in proof_adjudications if row["law_gap_admitted"]
    ]
    _require(
        predecessor["populated_local_proof_seal_defect_count"]
        == len(proof_seal_defects)
        == 28,
        "proof seal-defect count drift",
    )
    _require(
        predecessor["populated_local_proof_law_gap_count"]
        == len(proof_law_gaps)
        == 14,
        "proof law-gap count drift",
    )
    _require(
        predecessor["seal_defect_disposition_count"] == 36,
        "predecessor seal defect count drift",
    )
    _require(
        predecessor["law_gap_disposition_count"]
        == predecessor["in_domain_nonalias_law_gap_repair_count"]
        == 14,
        "predecessor law-gap count drift",
    )
    _require(
        predecessor["in_domain_nonalias_law_gap_subkind_counts"]
        == {
            AGGREGATE_RELATION_SUBKIND: 13,
            REDIRECTION_RELATION_SUBKIND: 1,
        },
        "predecessor law-gap subkind census drift",
    )
    _require(
        predecessor["semantic_alias_sweep_artifact_id"] == sweep["artifact_id"]
        and predecessor["round_four_new_fragment_seal_quality_issue_count"]
        == 10
        and predecessor["round_four_new_fragment_instruction_keyset_sha256"]
        == sweep["semantic_alias_round_four_new_fragment_keyset_sha256"]
        and predecessor["tier_2_predecessor_seal_quality_issue_count"] == 46,
        "predecessor round-four fragment linkage drift",
    )
    _require(
        predecessor["tier_2_precondition"]
        == "all_36_round_three_defects_and_10_round_five_fragments_repaired_"
        "and_amendment_ratified_before_certification",
        "predecessor tier-2 precondition drift",
    )
    _require(
        predecessor["adjudication_rule"]
        == "round_five_source_cited_semantic_ledger_is_the_only_A_admission_"
        "gate_and_exact_covers_262_baseline_rows_plus_3_continuation_"
        "restorations",
        "predecessor adjudication rule drift",
    )
    _require(
        all(
            row["disposition"] == "predecessor_seal_defect"
            for row in [*doc036_rows, *proof_seal_defects]
        ),
        "predecessor seal-defect disposition drift",
    )
    _require(
        predecessor["source_flag_counts"]
        == {
            "touches_noncatalog_aggregate_endpoint": 28,
            "occurrence_derived_domain_crossing": 19,
            "corrected_catalog_domain_crossing": 19,
            "raw_node_domain_crossing": 18,
            "context_remuneration_mix": 15,
            "head_spouse_mix": 4,
        },
        "predecessor source-flag census drift",
    )
    _require(
        predecessor["seal_defect_flag_counts"]
        == {
            "touches_noncatalog_aggregate_endpoint": 15,
            "occurrence_derived_domain_crossing": 19,
            "corrected_catalog_domain_crossing": 19,
            "raw_node_domain_crossing": 18,
            "context_remuneration_mix": 14,
            "head_spouse_mix": 4,
        },
        "predecessor seal-defect flag census drift",
    )
    _require(
        {row["source_local_evidence_id"] for row in proof_law_gaps}
        == {row["source_local_evidence_id"] for row in sweep_aggregate_rows}
        | (
            {
                evidence_id
                for row in sweep_redirection_rows
                for evidence_id in row["source_local_evidence_ids"]
            }
            & REDIRECTION_LAW_GAP_EVIDENCE_IDS
        ),
        "in-domain relation rows do not exact-cover predecessor law gaps",
    )

    role = bundle["role"]
    pilot_role_classes = _validate_row_digests(
        role,
        "role_label_class_rows",
        "role_label_class_count",
        "role_label_class_domain_sha256",
    )
    _require(len(pilot_role_classes) == 69, "pilot role class count drift")
    for row in pilot_role_classes:
        _validate_role_class_row(row, "pilot role class row")
    pilot_class_by_id = {
        row["role_label_class_id"]: row for row in pilot_role_classes
    }
    _require(
        len(pilot_class_by_id) == len(pilot_role_classes),
        "duplicate pilot role class ID",
    )
    assignments = _validate_row_digests(
        role,
        "role_assignment_rows",
        "role_assignment_count",
        "role_assignment_domain_sha256",
    )
    _require(len(assignments) == 947, "pilot role assignment count drift")
    for row in assignments:
        _validate_role_assignment_row(row, pilot_class_by_id)
    _require(
        role["role_assignment_keyset_sha256"]
        == _keyset_sha([row["role_assignment_id"] for row in assignments]),
        "role assignment keyset drift",
    )
    _require(
        len({row["role_anchor_occurrence_id"] for row in assignments})
        == len(assignments),
        "duplicate role assignment",
    )
    pilot_members = {
        member
        for row in pilot_role_classes
        for member in row["member_occurrence_ids"]
    }
    assignment_members = {
        row["role_anchor_occurrence_id"] for row in assignments
    }
    canonical_ids = set(role["canonical_role_occurrence_ids"].values())
    _require(
        role["canonical_role_occurrence_ids"] == ROLE_CANONICALS,
        "canonical role identities drift",
    )
    _require(
        assignment_members == pilot_members - canonical_ids,
        "pilot role class members are not assigned exactly once",
    )
    _require(
        canonical_ids <= pilot_members
        and not (canonical_ids & assignment_members),
        "canonical role partition drift",
    )
    full_class_by_id = {
        row["role_label_class_id"]: row for row in role_classes
    }
    for pilot_class in pilot_role_classes:
        class_id = pilot_class["role_label_class_id"]
        _require(
            class_id in full_class_by_id, "pilot role class absent from sweep"
        )
        full_class = full_class_by_id[class_id]
        _require(
            pilot_class["role"] == full_class["role"]
            and pilot_class["exact_label"] == full_class["exact_label"]
            and set(pilot_class["member_occurrence_ids"])
            <= set(full_class["member_occurrence_ids"]),
            "pilot role class is not a sweep projection",
        )
    _require(role["unassigned_role_anchor_rows"] == [], "unassigned roles")
    _require(role["unassigned_role_anchor_count"] == 0, "unassigned count")

    repeat = bundle["repeat"]
    repeat_rows = _validate_row_digests(
        repeat,
        "outside_domain_repeat_disposition_rows",
        "outside_domain_repeat_disposition_count",
        "outside_domain_repeat_disposition_domain_sha256",
    )
    _require(len(repeat_rows) == 34, "pilot repeat count drift")
    _require(
        repeat["outside_domain_relation_counts"]
        == {
            "explicit_cross_reference": 17,
            "explicit_repeat_instruction": 17,
        },
        "repeat relation census drift",
    )
    _require(
        repeat["outside_domain_document_counts"]
        == {"14": 2, "40": 22, "56": 5, "58": 4, "66": 1},
        "repeat document census drift",
    )
    for row in repeat_rows:
        _validate_outside_repeat_row(row, "repeat pilot row")
    _require(
        repeat["outside_domain_repeat_disposition_keyset_sha256"]
        == _keyset_sha(
            [
                row["outside_domain_repeat_disposition_id"]
                for row in repeat_rows
            ]
        ),
        "repeat pilot keyset drift",
    )
    _require(
        repeat_rows == sweep_repeat_rows,
        "pilot outside-domain repeat rows differ from exhaustive sweep",
    )
    pilot_aggregate_rows = _validate_row_digests(
        repeat,
        "noncatalog_aggregate_relation_disposition_rows",
        "noncatalog_aggregate_relation_disposition_count",
        "noncatalog_aggregate_relation_disposition_domain_sha256",
    )
    _require(len(pilot_aggregate_rows) == 1, "pilot aggregate relation drift")
    for row in pilot_aggregate_rows:
        _validate_noncatalog_aggregate_relation_row(
            row, "aggregate relation pilot row"
        )
    _require(
        repeat["noncatalog_aggregate_relation_disposition_keyset_sha256"]
        == _keyset_sha(
            [
                row["noncatalog_aggregate_relation_disposition_id"]
                for row in pilot_aggregate_rows
            ]
        ),
        "pilot aggregate relation keyset drift",
    )
    _require(
        repeat["aggregate_relation_counts"]
        == {"explicit_repeat_instruction": 1}
        and repeat["aggregate_document_counts"] == {"58": 1}
        and repeat["aggregate_handoff_status_counts"]
        == {"local_resolved_cross_reference_for_global_assembly": 1},
        "pilot aggregate relation census drift",
    )
    expected_pilot_aggregate_rows = [
        row
        for row in sweep_aggregate_rows
        if row["document_source_position"] in PILOT_POSITIONS
    ]
    _require(
        pilot_aggregate_rows == expected_pilot_aggregate_rows,
        "pilot aggregate relations differ from exhaustive sweep",
    )
    pilot_redirection_rows = _validate_row_digests(
        repeat,
        "in_domain_redirection_disposition_rows",
        "in_domain_redirection_disposition_count",
        "in_domain_redirection_disposition_domain_sha256",
    )
    _require(len(pilot_redirection_rows) == 2, "pilot redirection drift")
    for row in pilot_redirection_rows:
        _validate_in_domain_redirection_row(row, "redirection pilot row")
    _require(
        repeat["in_domain_redirection_disposition_keyset_sha256"]
        == _keyset_sha(
            [
                row["in_domain_redirection_relation_disposition_id"]
                for row in pilot_redirection_rows
            ]
        ),
        "pilot redirection keyset drift",
    )
    _require(
        repeat["redirection_relation_counts"]
        == {"explicit_cross_reference": 2}
        and repeat["redirection_document_counts"] == {"66": 2}
        and repeat["redirection_handoff_status_counts"]
        == {"local_resolved_cross_reference_for_global_assembly": 2},
        "pilot redirection census drift",
    )
    expected_pilot_redirection_rows = [
        row
        for row in sweep_redirection_rows
        if row["document_source_position"] in PILOT_POSITIONS
    ]
    _require(
        pilot_redirection_rows == expected_pilot_redirection_rows,
        "pilot redirections differ from exhaustive sweep",
    )
    _require(
        not (
            {
                row["source_instruction_occurrence_ids"][0]
                for row in pilot_aggregate_rows
            }
            | {
                row["source_instruction_occurrence_ids"][0]
                for row in pilot_redirection_rows
            }
        )
        & {row["source_instruction_occurrence_id"] for row in repeat_rows}
        and not {
            row["source_instruction_occurrence_ids"][0]
            for row in pilot_aggregate_rows
        }
        & {
            row["source_instruction_occurrence_ids"][0]
            for row in pilot_redirection_rows
        },
        "pilot repeat claimed by multiple disposition arms",
    )

    component = bundle["component"]
    zero_rows = _validate_row_digests(
        component,
        "zero_parent_disposition_rows",
        "zero_parent_disposition_count",
        "zero_parent_disposition_domain_sha256",
    )
    unique_rows = _validate_row_digests(
        component,
        "unique_parent_assignment_rows",
        "unique_parent_assignment_count",
        "unique_parent_assignment_domain_sha256",
    )
    ambiguity_rows = _validate_row_digests(
        component,
        "multi_parent_ambiguity_rows",
        "multi_parent_ambiguity_count",
        "multi_parent_ambiguity_domain_sha256",
    )
    _require(len(zero_rows) == 1_488, "pilot zero-parent count drift")
    _require(len(unique_rows) == 1_307, "pilot unique-parent count drift")
    _require(len(ambiguity_rows) == 300, "pilot ambiguity count drift")
    all_component_rows = [*zero_rows, *unique_rows, *ambiguity_rows]
    for row in all_component_rows:
        _validate_component_shape_row(
            row, source_witness_by_key, "component pilot row"
        )
    _require(
        component["complete_component_resolution_count"]
        == len(all_component_rows)
        == 3_095,
        "pilot component partition drift",
    )
    _require(
        len(
            {
                row["component_anchor_occurrence_id"]
                for row in all_component_rows
            }
        )
        == len(all_component_rows),
        "duplicate component resolution",
    )
    _require(
        component["complete_component_resolution_keyset_sha256"]
        == _keyset_sha(
            [
                row["component_parent_resolution_id"]
                for row in all_component_rows
            ]
        ),
        "pilot component complete keyset drift",
    )
    _require(
        component["complete_component_resolution_domain_sha256"]
        == _domain_sha(all_component_rows),
        "pilot component complete domain drift",
    )
    for row in zero_rows:
        _require(
            row["disposition"]
            in {
                "zero_parent_terminal_disposition",
                "zero_lawful_parent_terminal_disposition",
            },
            "zero disposition drift",
        )
    for row in unique_rows:
        _require(
            row["disposition"] == "unique_parent_assignment",
            "unique partition disposition drift",
        )
    for row in ambiguity_rows:
        _require(
            row["disposition"] == "multi_parent_ambiguity_no_selection",
            "ambiguity partition disposition drift",
        )
    pilot_component_by_id = {
        row["component_parent_resolution_id"]: row
        for row in all_component_rows
    }
    expected_pilot_component_rows = [
        row
        for row in component_shapes
        if row["document_source_position"] in PILOT_POSITIONS
    ]
    _require(
        pilot_component_by_id
        == {
            row["component_parent_resolution_id"]: row
            for row in expected_pilot_component_rows
        },
        "pilot component rows differ from exhaustive sweep projection",
    )
    _require(
        component["serialized_parent_cardinality_counts"]
        == {"zero": 1_466, "one": 1_329, "multiple": 300},
        "pilot component raw census drift",
    )
    _require(
        component["raw_cross_category_multi_parent_count"] == 86
        and component["eligible_cross_category_multi_parent_count"] == 86
        and component["eligible_ineligible_mixed_multi_parent_count"] == 0,
        "pilot component ambiguity census drift",
    )
    _require(
        component["ineligible_parent_reference_count"] == 22,
        "pilot component ineligible-parent census drift",
    )

    recomputed_role_counts = Counter(
        row["role"]
        for row in pilot_role_classes
        for _member in row["member_occurrence_ids"]
    )
    recomputed_raw_cardinality = Counter(
        (
            "zero"
            if row["serialized_parent_cardinality"] == 0
            else (
                "one"
                if row["serialized_parent_cardinality"] == 1
                else "multiple"
            )
        )
        for row in all_component_rows
    )
    recomputed_component_dispositions = dict(
        sorted(
            Counter(row["disposition"] for row in all_component_rows).items()
        )
    )
    _require(
        census["document_count"] == len(pilot_rows)
        and census["role_anchor_count"] == len(pilot_members)
        and census["head_role_anchor_count"]
        == recomputed_role_counts[ROLE_HEAD]
        and census["spouse_role_anchor_count"]
        == recomputed_role_counts[ROLE_SPOUSE]
        and census["source_component_anchor_count"] == len(all_component_rows),
        "pilot census artifact-cover equations drift",
    )
    _require(
        census["serialized_component_parent_cardinality"]
        == {
            key: recomputed_raw_cardinality[key]
            for key in ("zero", "one", "multiple")
        }
        and census["component_parent_disposition_counts"]
        == recomputed_component_dispositions,
        "pilot census component disposition recomputation drift",
    )
    _require(
        census["outside_domain_instruction_count"]
        == len(
            {row["source_instruction_occurrence_id"] for row in repeat_rows}
        )
        and census["noncatalog_aggregate_relation_instruction_count"]
        == len(
            {
                row["source_instruction_occurrence_ids"][0]
                for row in pilot_aggregate_rows
            }
        )
        and census["in_domain_redirection_instruction_count"]
        == len(
            {
                row["source_instruction_occurrence_ids"][0]
                for row in pilot_redirection_rows
            }
        )
        and census["in_domain_nonalias_relation_instruction_count"]
        == len(pilot_aggregate_rows) + len(pilot_redirection_rows),
        "pilot census repeat disposition recomputation drift",
    )

    gate = bundle["gate"]
    expected_statuses = {
        "slice": "pass_pilot_slice_fixed_nonauthority",
        "sweeps": "pass_corpus_exhaustive_targeted_sweeps_nonauthority",
        "derived": (
            "pass_derived_class_complement_sweeps_nonauthority_"
            "predecessor_reseal_required"
        ),
        "predecessor": (
            "pass_adjudication_with_46_predecessor_repairs_required"
        ),
        "role": "pass_role_assignment_law_pilot_nonauthority",
        "repeat": "pass_four_disposition_repeat_law_pilot_nonauthority",
        "component": "pass_component_parent_law_pilot_nonauthority",
        "gate": "pass_law_shapes_only_nonauthority",
    }
    _require(
        all(
            bundle[key]["status"] == status
            for key, status in expected_statuses.items()
        ),
        "artifact status drift",
    )
    _require(
        all(bundle[key]["tier"] == 1 for key in OUTPUT_FILENAMES),
        "artifact tier drift",
    )
    _require(
        sweep["source_corpus_identity"]
        == slice_artifact["source_corpus_identity"]
        == predecessor["source_corpus_identity"]
        == derived["source_corpus_identity"],
        "source corpus identity linkage drift",
    )
    _require(
        derived["corpus_sweep_artifact_id"] == sweep["artifact_id"]
        and derived["predecessor_artifact_id"] == predecessor["artifact_id"]
        and derived["predecessor_seal_defect_count"] == 36
        and derived["round_four_new_fragment_seal_quality_issue_count"] == 10
        and derived["tier_2_predecessor_seal_quality_issue_count"] == 46
        and derived["predecessor_reseal_required"] is True,
        "derived sweep predecessor linkage drift",
    )
    _require(
        all(
            bundle[key]["source_slice_artifact_id"]
            == slice_artifact["artifact_id"]
            for key in ("role", "repeat", "component")
        ),
        "pilot slice artifact linkage drift",
    )
    _require(
        all(
            bundle[key]["corpus_sweep_artifact_id"] == sweep["artifact_id"]
            for key in ("role", "repeat", "component")
        ),
        "corpus sweep artifact linkage drift",
    )
    _require(
        gate["source_slice_artifact_id"] == slice_artifact["artifact_id"],
        "gate slice linkage drift",
    )
    _require(
        gate["design_prefix_identity"]
        == slice_artifact["design_prefix_identity"],
        "gate design-prefix linkage drift",
    )
    _validate_pilot_census(gate["pilot_census"], "gate pilot census")
    _require(gate["pilot_census"] == census, "gate pilot census drift")
    _require(
        gate["certification_status"] == "PILOT_NONAUTHORITY_CERTIFIES_NOTHING",
        "pilot claims certification",
    )
    _require(gate["pilot_law_shape_status"] == "pass", "pilot law status")
    _require(
        gate["overall_repeat_catalog_coverage_status"]
        == "fail_closed_unresolved_rows_remain",
        "pilot falsely claims universal catalog coverage",
    )
    _require(gate["role_law_status"] == "pass", "gate role status")
    _require(
        gate["four_disposition_repeat_law_status"] == "pass_law_shape_only",
        "gate repeat status",
    )
    _require(
        gate["component_parent_law_status"] == "pass",
        "gate component status",
    )
    _require(
        gate["predecessor_input_status"] == "reseal_required_before_tier_2",
        "gate predecessor status",
    )
    _require(
        gate["tier_2_protocol_status"]
        == "not_started_requires_ratification_and_predecessor_reseals",
        "gate tier-2 status",
    )
    _require(
        gate["status"] == "pass_law_shapes_only_nonauthority",
        "gate status drift",
    )
    identity_rows = gate["artifact_identity_rows"]
    _require(len(identity_rows) == 7, "gate identity count drift")
    _require(
        gate["artifact_identity_count"] == len(identity_rows),
        "gate identity count mismatch",
    )
    _require(
        gate["artifact_identity_domain_sha256"] == _domain_sha(identity_rows),
        "gate identity digest drift",
    )
    expected_identity_roles = [
        "slice",
        "sweeps",
        "derived",
        "predecessor",
        "role",
        "repeat",
        "component",
    ]
    _require(
        [row["artifact_role"] for row in identity_rows]
        == expected_identity_roles,
        "gate identity role partition drift",
    )
    for identity in identity_rows:
        _require_exact_keys(
            identity,
            ARTIFACT_IDENTITY_ROW_KEYS,
            "gate artifact identity row",
        )
        key = identity["artifact_role"]
        raw = canonical_bytes(bundle[key])
        _require(identity["byte_size"] == len(raw), "gate artifact size drift")
        _require(identity["raw_sha256"] == _sha256(raw), "gate raw hash drift")
        _require(
            identity["artifact_id"] == bundle[key]["artifact_id"],
            "gate artifact ID drift",
        )
        _require(
            identity["path"]
            == "docs/analysis/amendment_12_rq_catalog_pilot/"
            + OUTPUT_FILENAMES[key],
            "gate artifact path drift",
        )
        _require(
            identity["schema_version"] == ARTIFACT_SPECS[key][0],
            "gate artifact schema drift",
        )


def _reseal_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    schema = artifact["schema_version"]
    authority_kind = artifact["authority_kind"]
    id_prefix = artifact["artifact_id"].rsplit(":", 1)[0] + ":"
    body = {
        key: copy.deepcopy(value)
        for key, value in artifact.items()
        if key
        not in {
            "schema_version",
            "artifact_id",
            "authority_kind",
            "integrity",
        }
    }
    return _artifact(schema, id_prefix, authority_kind, body)


def _repin_mutated_bundle(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Repin derived identities after an adversarial mutation."""
    bundle = copy.deepcopy(dict(value))

    for artifact_key, class_row_key in (
        ("sweeps", "role_exact_label_class_rows"),
        ("role", "role_label_class_rows"),
    ):
        for row in bundle[artifact_key][class_row_key]:
            row["exact_label_sha256"] = _sha256(
                row["exact_label"].encode("utf-8")
            )
            row["role_label_class_id"] = _row_id(
                "a12-role-exact-label-class:",
                [row["role"], row["exact_label_sha256"]],
            )
            row["member_count"] = len(row["member_occurrence_ids"])
            row["member_keyset_sha256"] = _keyset_sha(
                row["member_occurrence_ids"]
            )
    for row in bundle["role"]["role_assignment_rows"]:
        row["role_assignment_id"] = _row_id(
            "a12-pilot-role-assignment:",
            [
                row["source_document_id"],
                row["role_anchor_occurrence_id"],
                row["assigned_role"],
                row["role_label_class_id"],
                row["proof_form"],
            ],
        )

    for artifact_key, row_key in (
        ("sweeps", "outside_domain_repeat_shape_rows"),
        ("repeat", "outside_domain_repeat_disposition_rows"),
    ):
        for row in bundle[artifact_key][row_key]:
            row["outside_domain_repeat_disposition_id"] = _row_id(
                "a12-outside-rq-repeat-disposition:",
                [
                    row["source_document_id"],
                    row["source_instruction_occurrence_id"],
                    row["source_local_evidence_id"],
                    row["relation"],
                    row["unresolved_target_reference"],
                ],
            )
    for artifact_key, row_key in (
        ("sweeps", "noncatalog_aggregate_relation_shape_rows"),
        ("repeat", "noncatalog_aggregate_relation_disposition_rows"),
    ):
        for row in bundle[artifact_key][row_key]:
            row["noncatalog_aggregate_relation_disposition_id"] = _row_id(
                "a12-noncatalog-aggregate-relation-disposition:",
                [
                    row["source_document_id"],
                    row["source_local_evidence_id"],
                    row["source_instruction_occurrence_ids"],
                    row["relation"],
                    row["handoff_status"],
                    row["source_alias_anchor_occurrence_ids"],
                    row["source_canonical_anchor_occurrence_ids"],
                    row["evidence_occurrence_ids"],
                    row["endpoint_occurrence_kinds"],
                    row["endpoint_raw_node_domains"],
                    row["endpoint_classifications"],
                    row["source_instruction_matched_texts"],
                    row["source_instruction_matched_utf8_sha256s"],
                    row["source_instruction_page_numbers"],
                    row["source_instruction_utf8_byte_starts"],
                    row["source_instruction_utf8_byte_ends"],
                    row["endpoint_matched_texts"],
                    row["endpoint_matched_utf8_sha256s"],
                    row["endpoint_page_numbers"],
                    row["endpoint_utf8_byte_starts"],
                    row["endpoint_utf8_byte_ends"],
                ],
            )
    for artifact_key, row_key in (
        ("sweeps", "in_domain_redirection_shape_rows"),
        ("repeat", "in_domain_redirection_disposition_rows"),
    ):
        for row in bundle[artifact_key][row_key]:
            row["in_domain_redirection_relation_disposition_id"] = (
                _redirection_disposition_id(row)
            )
    for row in bundle["sweeps"][
        "in_domain_component_cross_reference_sweep_rows"
    ]:
        fragment_fields = {
            key: row[key]
            for key in (
                "source_instruction_fragment",
                "tier_2_predecessor_seal_quality_issue",
                "tier_2_predecessor_ledger_note",
            )
        }
        row["semantic_alias_adjudication_id"] = _row_id(
            "a12-semantic-alias-adjudication:",
            [
                row["source_document_id"],
                row["source_instruction_occurrence_id"],
                row["source_local_evidence_ids"],
                row["source_instruction_matched_text"],
                row["source_instruction_matched_utf8_sha256"],
                row["source_instruction_page_number"],
                row["source_instruction_utf8_byte_start"],
                row["source_instruction_utf8_byte_end"],
                row["source_endpoint_matched_text_arrays"],
                row["source_endpoint_matched_utf8_sha256_arrays"],
                row["source_endpoint_page_number_arrays"],
                row["source_endpoint_utf8_byte_start_arrays"],
                row["source_endpoint_utf8_byte_end_arrays"],
                row["repeat_coverage_disposition"],
                row["semantic_alias_finding"],
                row[
                    "named_instruction_import_or_occurrence_equivalence_proved"
                ],
                row["occurrence_equivalence_proved"],
                row["pairwise_decomposition_required"],
                row["approved_pair_count"],
                row["rejected_source_local_evidence_ids"],
                row["continuation_composition_citation"],
                fragment_fields,
            ],
        )
        row["in_domain_component_cross_reference_sweep_id"] = _row_id(
            "a12-in-domain-component-cross-reference-sweep:",
            [
                row["source_document_id"],
                row["source_instruction_occurrence_id"],
                row["source_local_evidence_ids"],
                row["source_evidence_occurrence_id_arrays"],
                row["source_alias_anchor_occurrence_id_arrays"],
                row["source_canonical_anchor_occurrence_id_arrays"],
                row["repeat_coverage_disposition"],
                row["semantic_alias_adjudication_id"],
            ],
        )
    for row in bundle["sweeps"][
        "exclusive_destination_redirection_lineage_rows"
    ]:
        row["exclusive_destination_redirection_lineage_id"] = _row_id(
            "a12-exclusive-destination-redirection-lineage:",
            [
                row["source_document_id"],
                row["source_instruction_occurrence_id"],
                row["source_instruction_matched_text"],
                row["source_local_evidence_ids"],
            ],
        )

    component_row_groups = (
        bundle["sweeps"]["component_parent_shape_rows"],
        bundle["component"]["zero_parent_disposition_rows"],
        bundle["component"]["unique_parent_assignment_rows"],
        bundle["component"]["multi_parent_ambiguity_rows"],
    )
    for rows in component_row_groups:
        for row in rows:
            candidates = row["parent_candidate_rows"]
            row["parent_candidate_count"] = len(candidates)
            row["serialized_parent_cardinality"] = len(candidates)
            row["eligible_parent_cardinality"] = sum(
                candidate["eligible_parent"] for candidate in candidates
            )
            row["parent_candidate_domain_sha256"] = _domain_sha(candidates)
            row["component_parent_resolution_id"] = _row_id(
                "a12-component-parent-resolution:",
                [
                    row["source_document_id"],
                    row["component_anchor_occurrence_id"],
                    row["component_kind"],
                    row["disposition"],
                    candidates,
                ],
            )

    for row in bundle["sweeps"]["parent_source_witness_rows"]:
        row["parent_source_witness_id"] = _row_id(
            "a12-parent-source-witness:",
            [
                row["source_document_id"],
                row["source_classification_id"],
                row["parent_occurrence_id"],
                row["parent_occurrence_kind"],
            ],
        )
    for row in bundle["predecessor"]["doc036_aggregate_component_slot_rows"]:
        row["predecessor_adjudication_id"] = _row_id(
            "a12-predecessor-doc036-aggregate-adjudication:",
            [
                row["source_document_id"],
                row["source_classification_id"],
                row["source_occurrence_id"],
                row["source_classification"],
                row["disposition"],
            ],
        )
    for row in bundle["predecessor"][
        "populated_local_proof_adjudication_rows"
    ]:
        row["predecessor_adjudication_id"] = _row_id(
            "a12-predecessor-local-proof-adjudication:",
            [
                row["source_document_id"],
                row["source_local_evidence_id"],
                row["defect_flags"],
                row["disposition"],
            ],
        )

    derived = bundle["derived"]
    for row in derived["component_class_admission_sweep_rows"]:
        members = row["component_class_member_occurrence_ids"]
        row["component_class_member_count"] = len(members)
        row["raw_parent_candidate_count"] = sum(
            row["member_raw_parent_cardinalities"]
        )
        row["candidate_component_class_id"] = _row_id(
            "a12-candidate-component-class:",
            [row["canonical_component_occurrence_id"], members],
        )
        row["component_class_admission_sweep_id"] = _row_id(
            "a12-component-class-admission-sweep:",
            [
                row["candidate_component_class_id"],
                row["candidate_disposition"],
            ],
        )
        for support in row["alias_support_rows"]:
            if support["support_origin"] == "exact_pair_equality_sweep":
                support["alias_support_proof_id"] = _row_id(
                    "a12-candidate-exact-pair-alias-support:",
                    [
                        COMPONENT_CLASSIFICATION_TO_KIND[
                            row["component_kind"]
                        ],
                        support["printed_identifier"],
                        support["exact_label"],
                        support["alias_anchor_occurrence_ids"],
                        support["canonical_anchor_occurrence_ids"],
                        support["evidence_occurrence_ids"],
                    ],
                )
            else:
                support["alias_support_proof_id"] = _row_id(
                    "a12-candidate-local-alias-support:",
                    [
                        support["semantic_alias_pair_adjudication_id"],
                        support["relation"],
                        support["alias_anchor_occurrence_ids"][0],
                        support["canonical_anchor_occurrence_ids"][0],
                        support["evidence_occurrence_ids"],
                    ],
                )
        row["alias_support_count"] = len(row["alias_support_rows"])
        row["alias_support_domain_sha256"] = _domain_sha(
            row["alias_support_rows"]
        )
    for row in derived["catalog_only_job_complement_sweep_rows"]:
        members = row["job_class_member_occurrence_ids"]
        relationships = row["candidate_relationship_component_class_ids"]
        row["job_class_member_count"] = len(members)
        row["candidate_relationship_count"] = len(relationships)
        row["candidate_job_class_id"] = _row_id(
            "a12-candidate-job-class:",
            [row["canonical_job_occurrence_id"], members],
        )
        row["catalog_only_job_complement_sweep_id"] = _row_id(
            "a12-catalog-only-job-complement-sweep:",
            [row["candidate_job_class_id"], relationships],
        )
        for support in row["alias_support_rows"]:
            if support["support_origin"] == "exact_pair_equality_sweep":
                support["alias_support_proof_id"] = _row_id(
                    "a12-candidate-exact-pair-alias-support:",
                    [
                        "job_anchor",
                        support["printed_identifier"],
                        support["exact_label"],
                        support["alias_anchor_occurrence_ids"],
                        support["canonical_anchor_occurrence_ids"],
                        support["evidence_occurrence_ids"],
                    ],
                )
            else:
                support["alias_support_proof_id"] = _row_id(
                    "a12-candidate-local-alias-support:",
                    [
                        support["semantic_alias_pair_adjudication_id"],
                        support["relation"],
                        support["alias_anchor_occurrence_ids"][0],
                        support["canonical_anchor_occurrence_ids"][0],
                        support["evidence_occurrence_ids"],
                    ],
                )
        row["alias_support_count"] = len(row["alias_support_rows"])
        row["alias_support_domain_sha256"] = _domain_sha(
            row["alias_support_rows"]
        )

    slice_artifact = bundle["slice"]
    pilot_rows = slice_artifact["pilot_document_rows"]
    slice_artifact["pilot_document_count"] = len(pilot_rows)
    slice_artifact["pilot_document_positions"] = [
        row["document_source_position"] for row in pilot_rows
    ]
    slice_artifact["pilot_document_position_domain_sha256"] = _domain_sha(
        slice_artifact["pilot_document_positions"]
    )
    slice_artifact["pilot_annotation_raw_byte_count"] = sum(
        row["annotation_byte_size"] for row in pilot_rows
    )

    sweep = bundle["sweeps"]
    role_classes = sweep["role_exact_label_class_rows"]
    sweep["role_exact_label_class_count"] = len(role_classes)
    sweep["role_exact_label_class_domain_sha256"] = _domain_sha(role_classes)
    sweep["role_anchor_count"] = sum(
        row["member_count"] for row in role_classes
    )
    sweep["role_noncanonical_assignment_reach_count"] = max(
        0, sweep["role_anchor_count"] - len(ROLE_CANONICALS)
    )
    sweep["role_unreached_anchor_count"] = len(
        sweep["role_unreached_anchor_rows"]
    )
    sweep_repeats = sweep["outside_domain_repeat_shape_rows"]
    sweep["outside_domain_repeat_shape_count"] = len(sweep_repeats)
    sweep["outside_domain_repeat_shape_domain_sha256"] = _domain_sha(
        sweep_repeats
    )
    sweep_aggregate_rows = sweep["noncatalog_aggregate_relation_shape_rows"]
    sweep["noncatalog_aggregate_relation_shape_count"] = len(
        sweep_aggregate_rows
    )
    sweep["noncatalog_aggregate_relation_shape_keyset_sha256"] = _keyset_sha(
        [
            row["noncatalog_aggregate_relation_disposition_id"]
            for row in sweep_aggregate_rows
        ]
    )
    sweep["noncatalog_aggregate_relation_shape_domain_sha256"] = _domain_sha(
        sweep_aggregate_rows
    )
    sweep_redirection_rows = sweep["in_domain_redirection_shape_rows"]
    sweep["in_domain_redirection_shape_count"] = len(sweep_redirection_rows)
    sweep["in_domain_redirection_shape_keyset_sha256"] = _keyset_sha(
        [
            row["in_domain_redirection_relation_disposition_id"]
            for row in sweep_redirection_rows
        ]
    )
    sweep["in_domain_redirection_shape_domain_sha256"] = _domain_sha(
        sweep_redirection_rows
    )
    component_cross_reference_rows = sweep[
        "in_domain_component_cross_reference_sweep_rows"
    ]
    component_cross_reference_counts = _component_cross_reference_sweep_counts(
        component_cross_reference_rows
    )
    sweep["in_domain_component_cross_reference_sweep_count"] = (
        component_cross_reference_counts["instruction_count"]
    )
    sweep["in_domain_component_cross_reference_sweep_edge_count"] = (
        component_cross_reference_counts["edge_count"]
    )
    sweep["in_domain_component_cross_reference_sweep_keyset_sha256"] = (
        _keyset_sha(
            [
                row["in_domain_component_cross_reference_sweep_id"]
                for row in component_cross_reference_rows
            ]
        )
    )
    sweep["in_domain_component_cross_reference_sweep_domain_sha256"] = (
        _domain_sha(component_cross_reference_rows)
    )
    sweep["semantic_alias_adjudication_count"] = len(
        component_cross_reference_rows
    )
    sweep["semantic_alias_adjudication_keyset_sha256"] = _keyset_sha(
        [
            row["semantic_alias_adjudication_id"]
            for row in component_cross_reference_rows
        ]
    )
    sweep["semantic_alias_adjudication_domain_sha256"] = _domain_sha(
        component_cross_reference_rows
    )
    sweep["semantic_alias_adjudication_outcome_counts"] = {
        key: component_cross_reference_counts[key]
        for key in (
            "alias_instruction_count",
            "alias_edge_count",
            "alias_pair_count",
            "redirection_instruction_count",
            "redirection_edge_count",
            "stop_instruction_count",
            "stop_edge_count",
        )
    }
    sweep["semantic_alias_instruction_outcome_domain_sha256"] = _domain_sha(
        [
            [
                row["source_instruction_occurrence_id"],
                _semantic_alias_outcome_code(row),
            ]
            for row in component_cross_reference_rows
        ]
    )
    for outcome, key in (
        ("A", "semantic_alias_equivalence_instruction_keyset_sha256"),
        ("R", "semantic_alias_redirection_instruction_keyset_sha256"),
        ("S", "semantic_alias_stop_instruction_keyset_sha256"),
    ):
        sweep[key] = _keyset_sha(
            [
                row["source_instruction_occurrence_id"]
                for row in component_cross_reference_rows
                if _semantic_alias_outcome_code(row) == outcome
            ]
        )
    sweep["semantic_alias_source_instruction_fragment_count"] = sum(
        row["source_instruction_fragment"]
        for row in component_cross_reference_rows
    )
    sweep["semantic_alias_fragment_seal_quality_issue_count"] = sum(
        row["tier_2_predecessor_seal_quality_issue"]
        for row in component_cross_reference_rows
    )
    note_count_fields = (
        (
            "round_three_reseal_ledger_already_covers_fragment",
            "semantic_alias_round_three_fragment_reseal_count",
        ),
        (
            "new_tier_2_reseal_required_for_incomplete_fragment",
            "semantic_alias_round_four_new_fragment_reseal_count",
        ),
        (
            "fragment_semantically_decisive_no_reseal_required",
            "semantic_alias_decisive_fragment_no_reseal_count",
        ),
    )
    for note, key in note_count_fields:
        sweep[key] = sum(
            row["tier_2_predecessor_ledger_note"] == note
            for row in component_cross_reference_rows
        )
    sweep["semantic_alias_fragment_instruction_keyset_sha256"] = _keyset_sha(
        [
            row["source_instruction_occurrence_id"]
            for row in component_cross_reference_rows
            if row["source_instruction_fragment"]
        ]
    )
    sweep["semantic_alias_round_four_new_fragment_keyset_sha256"] = (
        _keyset_sha(
            [
                row["source_instruction_occurrence_id"]
                for row in component_cross_reference_rows
                if row["tier_2_predecessor_ledger_note"]
                == "new_tier_2_reseal_required_for_incomplete_fragment"
            ]
        )
    )
    for suffix in (
        "alias_instruction_count",
        "alias_edge_count",
        "alias_pair_count",
        "redirection_instruction_count",
        "redirection_edge_count",
        "stop_instruction_count",
        "stop_edge_count",
    ):
        sweep[f"in_domain_component_cross_reference_sweep_{suffix}"] = (
            component_cross_reference_counts[suffix]
        )
    pilot_component_cross_reference_counts = (
        _component_cross_reference_sweep_counts(
            [
                row
                for row in component_cross_reference_rows
                if row["pilot_document_member"]
            ]
        )
    )
    sweep["pilot_in_domain_component_cross_reference_sweep_count"] = (
        pilot_component_cross_reference_counts["instruction_count"]
    )
    sweep["pilot_in_domain_component_cross_reference_sweep_edge_count"] = (
        pilot_component_cross_reference_counts["edge_count"]
    )
    for suffix in (
        "alias_instruction_count",
        "alias_edge_count",
        "alias_pair_count",
        "redirection_instruction_count",
        "redirection_edge_count",
        "stop_instruction_count",
        "stop_edge_count",
    ):
        sweep[f"pilot_in_domain_component_cross_reference_sweep_{suffix}"] = (
            pilot_component_cross_reference_counts[suffix]
        )
    semantic_rows = sweep["alias_evidence_semantic_adjudication_rows"]
    semantic_pair_rows: list[dict[str, Any]] = []
    for semantic_row in semantic_rows:
        for pair in semantic_row["approved_pair_rows"]:
            pair["semantic_alias_pair_adjudication_id"] = _row_id(
                "a12-semantic-alias-pair-adjudication:",
                [
                    semantic_row["source_document_id"],
                    semantic_row["source_local_evidence_id"],
                    pair["pair_ordinal"],
                    pair["pair_kind"],
                    pair["pairing_basis_code"],
                    pair["semantic_type"],
                    pair["alias_occurrence_id"],
                    pair["canonical_occurrence_id"],
                    pair["alias_question_selector"],
                    pair["canonical_question_selector"],
                    pair["alias_endpoint_matched_utf8_sha256"],
                    pair["canonical_endpoint_matched_utf8_sha256"],
                    pair["source_instruction_matched_utf8_sha256s"],
                    pair["exact_pairing_citation"],
                    pair["composite_typed_projection_pair_id"],
                ],
            )
        semantic_row["approved_pair_count"] = len(
            semantic_row["approved_pair_rows"]
        )
        semantic_row["semantic_alias_evidence_adjudication_id"] = _row_id(
            "a12-semantic-alias-evidence-adjudication:",
            [
                semantic_row["source_document_id"],
                semantic_row["source_local_evidence_id"],
                semantic_row["candidate_origin"],
                semantic_row["ca41663_admitted_alias_evidence"],
                semantic_row["source_instruction_matched_utf8_sha256s"],
                semantic_row["endpoint_matched_utf8_sha256s"],
                semantic_row["semantic_finding"],
                semantic_row["decision"],
                [
                    pair["semantic_alias_pair_adjudication_id"]
                    for pair in semantic_row["approved_pair_rows"]
                ],
                semantic_row["continuation_composition_citation"],
                semantic_row["composite_stop_citation"],
            ],
        )
        semantic_pair_rows.extend(semantic_row["approved_pair_rows"])
    semantic_adjudication_ids = [
        row["semantic_alias_evidence_adjudication_id"] for row in semantic_rows
    ]
    sweep["alias_semantic_input_identity_count"] = len(
        sweep["alias_semantic_input_identity_rows"]
    )
    sweep["alias_semantic_input_identity_domain_sha256"] = _domain_sha(
        sweep["alias_semantic_input_identity_rows"]
    )
    sweep["alias_evidence_semantic_adjudication_count"] = len(semantic_rows)
    sweep["ca41663_alias_evidence_adjudication_count"] = sum(
        row["ca41663_admitted_alias_evidence"] for row in semantic_rows
    )
    sweep["round_five_continuation_restoration_count"] = sum(
        row["round_five_continuation_restoration"] for row in semantic_rows
    )
    sweep["continuation_composition_citation_count"] = sum(
        row["continuation_composition_citation"] is not None
        for row in semantic_rows
    )
    sweep["alias_evidence_semantic_adjudication_keyset_sha256"] = _keyset_sha(
        semantic_adjudication_ids
    )
    sweep["alias_evidence_semantic_adjudication_domain_sha256"] = _domain_sha(
        semantic_rows
    )
    sweep["alias_evidence_semantic_decision_counts"] = dict(
        sorted(Counter(row["decision"] for row in semantic_rows).items())
    )
    sweep["alias_evidence_semantic_candidate_origin_counts"] = dict(
        sorted(
            Counter(row["candidate_origin"] for row in semantic_rows).items()
        )
    )
    sweep["approved_alias_evidence_count"] = sum(
        bool(row["approved_pair_rows"]) for row in semantic_rows
    )
    sweep["disclosed_stop_alias_evidence_count"] = sum(
        not row["approved_pair_rows"] for row in semantic_rows
    )
    sweep["approved_alias_pair_rows"] = semantic_pair_rows
    sweep["approved_alias_pair_count"] = len(semantic_pair_rows)
    sweep["approved_alias_pair_keyset_sha256"] = _keyset_sha(
        [
            row["semantic_alias_pair_adjudication_id"]
            for row in semantic_pair_rows
        ]
    )
    sweep["approved_alias_pair_domain_sha256"] = _domain_sha(
        semantic_pair_rows
    )
    sweep["occurrence_closure_alias_pair_count"] = sum(
        row["class_closure_eligible"] for row in semantic_pair_rows
    )
    sweep["typed_projection_alias_pair_count"] = sum(
        row["typed_projection_union_prohibited"] for row in semantic_pair_rows
    )
    lineage_rows = sweep["exclusive_destination_redirection_lineage_rows"]
    sweep["exclusive_destination_redirection_lineage_count"] = len(
        lineage_rows
    )
    sweep["exclusive_destination_redirection_lineage_keyset_sha256"] = (
        _keyset_sha(
            [
                row["exclusive_destination_redirection_lineage_id"]
                for row in lineage_rows
            ]
        )
    )
    sweep["exclusive_destination_redirection_lineage_domain_sha256"] = (
        _domain_sha(lineage_rows)
    )
    sweep["exclusive_destination_redirection_lineage_admitted_count"] = sum(
        row["in_domain_redirection_arm_eligible"] for row in lineage_rows
    )
    sweep["exclusive_destination_redirection_lineage_aggregate_count"] = sum(
        row["lineage_disposition"]
        == "covered_by_existing_aggregate_nonalias_subkind"
        for row in lineage_rows
    )
    sweep["exclusive_destination_redirection_lineage_stop_count"] = sum(
        row["lineage_disposition"].startswith("disclosed_stop_")
        for row in lineage_rows
    )
    sweep["exclusive_destination_redirection_lineage_mixed_stop_count"] = sum(
        row["lineage_disposition"]
        == "disclosed_stop_mixed_aggregate_component_proof"
        for row in lineage_rows
    )
    sweep[
        "exclusive_destination_redirection_lineage_incomplete_stop_count"
    ] = sum(
        row["lineage_disposition"] == "disclosed_stop_incomplete_local_proof"
        for row in lineage_rows
    )
    component_shapes = sweep["component_parent_shape_rows"]
    sweep["component_parent_shape_count"] = len(component_shapes)
    sweep["component_parent_shape_keyset_sha256"] = _keyset_sha(
        [row["component_parent_resolution_id"] for row in component_shapes]
    )
    sweep["component_parent_shape_domain_sha256"] = _domain_sha(
        component_shapes
    )
    raw_cardinality = Counter(
        (
            "zero"
            if row["serialized_parent_cardinality"] == 0
            else (
                "one"
                if row["serialized_parent_cardinality"] == 1
                else "multiple"
            )
        )
        for row in component_shapes
    )
    sweep["serialized_parent_cardinality_counts"] = {
        key: raw_cardinality[key] for key in ("zero", "one", "multiple")
    }
    sweep["component_parent_disposition_counts"] = dict(
        sorted(Counter(row["disposition"] for row in component_shapes).items())
    )
    sweep["raw_cross_category_multi_parent_count"] = sum(
        row["raw_parent_category_ambiguity"] for row in component_shapes
    )
    sweep["eligible_cross_category_multi_parent_count"] = sum(
        row["eligible_parent_category_ambiguity"] for row in component_shapes
    )
    sweep["eligible_ineligible_mixed_multi_parent_count"] = sum(
        row["eligible_ineligible_mixed_ambiguity"] for row in component_shapes
    )
    sweep["ineligible_parent_reference_count"] = sum(
        candidate["eligible_parent"] is False
        for row in component_shapes
        for candidate in row["parent_candidate_rows"]
    )
    source_witnesses = sweep["parent_source_witness_rows"]
    sweep["parent_source_witness_count"] = len(source_witnesses)
    sweep["parent_source_witness_keyset_sha256"] = _keyset_sha(
        [row["parent_source_witness_id"] for row in source_witnesses]
    )
    sweep["parent_source_witness_domain_sha256"] = _domain_sha(
        source_witnesses
    )

    predecessor = bundle["predecessor"]
    doc036_rows = predecessor["doc036_aggregate_component_slot_rows"]
    proof_rows = predecessor["populated_local_proof_adjudication_rows"]
    predecessor["doc036_aggregate_component_slot_count"] = len(doc036_rows)
    predecessor["doc036_aggregate_component_slot_domain_sha256"] = _domain_sha(
        doc036_rows
    )
    predecessor["populated_local_proof_adjudication_count"] = len(proof_rows)
    predecessor["populated_local_proof_adjudication_keyset_sha256"] = (
        _keyset_sha([row["source_local_evidence_id"] for row in proof_rows])
    )
    predecessor["populated_local_proof_adjudication_domain_sha256"] = (
        _domain_sha(proof_rows)
    )
    proof_seal_defects = [
        row
        for row in proof_rows
        if row["disposition"] == "predecessor_seal_defect"
    ]
    proof_law_gaps = [row for row in proof_rows if row["law_gap_admitted"]]
    predecessor["populated_local_proof_seal_defect_count"] = len(
        proof_seal_defects
    )
    predecessor["populated_local_proof_law_gap_count"] = len(proof_law_gaps)
    predecessor["source_flag_counts"] = {
        key: sum(row["defect_flags"][key] for row in proof_rows)
        for key in DEFECT_FLAG_KEYS
    }
    predecessor["seal_defect_flag_counts"] = {
        key: sum(row["defect_flags"][key] for row in proof_seal_defects)
        for key in DEFECT_FLAG_KEYS
    }
    all_predecessor_rows = [*doc036_rows, *proof_rows]
    predecessor["seal_defect_disposition_count"] = sum(
        row["disposition"] == "predecessor_seal_defect"
        for row in all_predecessor_rows
    )
    predecessor["law_gap_disposition_count"] = sum(
        row["law_gap_admitted"] for row in all_predecessor_rows
    )
    predecessor["in_domain_nonalias_law_gap_repair_count"] = len(
        proof_law_gaps
    )
    predecessor["in_domain_nonalias_law_gap_subkind_counts"] = dict(
        sorted(
            Counter(
                row["in_domain_nonalias_relation_subkind"]
                for row in proof_law_gaps
            ).items()
        )
    )
    predecessor["round_four_new_fragment_seal_quality_issue_count"] = sweep[
        "semantic_alias_round_four_new_fragment_reseal_count"
    ]
    predecessor["round_four_new_fragment_instruction_keyset_sha256"] = sweep[
        "semantic_alias_round_four_new_fragment_keyset_sha256"
    ]
    predecessor["tier_2_predecessor_seal_quality_issue_count"] = (
        predecessor["seal_defect_disposition_count"]
        + predecessor["round_four_new_fragment_seal_quality_issue_count"]
    )

    component_class_rows = derived["component_class_admission_sweep_rows"]
    derived["component_class_admission_sweep_count"] = len(
        component_class_rows
    )
    derived["component_class_member_occurrence_count"] = sum(
        row["component_class_member_count"] for row in component_class_rows
    )
    derived["component_class_admission_sweep_keyset_sha256"] = _keyset_sha(
        [
            row["component_class_admission_sweep_id"]
            for row in component_class_rows
        ]
    )
    derived["component_class_admission_sweep_domain_sha256"] = _domain_sha(
        component_class_rows
    )
    derived["component_class_candidate_disposition_counts"] = dict(
        sorted(
            Counter(
                row["candidate_disposition"] for row in component_class_rows
            ).items()
        )
    )
    derived["component_class_relationship_arm_eligible_count"] = sum(
        row["relationship_arm_eligible"] for row in component_class_rows
    )
    derived["component_alias_support_origin_counts"] = dict(
        sorted(
            Counter(
                support["support_origin"]
                for row in component_class_rows
                for support in row["alias_support_rows"]
            ).items()
        )
    )
    job_complement_rows = derived["catalog_only_job_complement_sweep_rows"]
    derived["catalog_only_job_complement_sweep_count"] = len(
        job_complement_rows
    )
    derived["job_class_member_occurrence_count"] = sum(
        row["job_class_member_count"] for row in job_complement_rows
    )
    derived["catalog_only_job_complement_sweep_keyset_sha256"] = _keyset_sha(
        [
            row["catalog_only_job_complement_sweep_id"]
            for row in job_complement_rows
        ]
    )
    derived["catalog_only_job_complement_sweep_domain_sha256"] = _domain_sha(
        job_complement_rows
    )
    derived["catalog_only_job_coverage_arm_counts"] = dict(
        sorted(
            Counter(row["coverage_arm"] for row in job_complement_rows).items()
        )
    )
    derived["job_alias_support_origin_counts"] = dict(
        sorted(
            Counter(
                support["support_origin"]
                for row in job_complement_rows
                for support in row["alias_support_rows"]
            ).items()
        )
    )

    role = bundle["role"]
    pilot_classes = role["role_label_class_rows"]
    assignments = role["role_assignment_rows"]
    role["role_label_class_count"] = len(pilot_classes)
    role["role_label_class_domain_sha256"] = _domain_sha(pilot_classes)
    role["role_assignment_count"] = len(assignments)
    role["role_assignment_keyset_sha256"] = _keyset_sha(
        [row["role_assignment_id"] for row in assignments]
    )
    role["role_assignment_domain_sha256"] = _domain_sha(assignments)
    role["unassigned_role_anchor_count"] = len(
        role["unassigned_role_anchor_rows"]
    )

    repeat = bundle["repeat"]
    repeat_rows = repeat["outside_domain_repeat_disposition_rows"]
    repeat["outside_domain_repeat_disposition_count"] = len(repeat_rows)
    repeat["outside_domain_repeat_disposition_keyset_sha256"] = _keyset_sha(
        [row["outside_domain_repeat_disposition_id"] for row in repeat_rows]
    )
    repeat["outside_domain_repeat_disposition_domain_sha256"] = _domain_sha(
        repeat_rows
    )
    repeat["outside_domain_relation_counts"] = dict(
        sorted(Counter(row["relation"] for row in repeat_rows).items())
    )
    repeat["outside_domain_document_counts"] = {
        str(key): count
        for key, count in sorted(
            Counter(
                row["document_source_position"] for row in repeat_rows
            ).items()
        )
    }
    aggregate_rows = repeat["noncatalog_aggregate_relation_disposition_rows"]
    repeat["noncatalog_aggregate_relation_disposition_count"] = len(
        aggregate_rows
    )
    repeat["noncatalog_aggregate_relation_disposition_keyset_sha256"] = (
        _keyset_sha(
            [
                row["noncatalog_aggregate_relation_disposition_id"]
                for row in aggregate_rows
            ]
        )
    )
    repeat["noncatalog_aggregate_relation_disposition_domain_sha256"] = (
        _domain_sha(aggregate_rows)
    )
    repeat["aggregate_relation_counts"] = dict(
        sorted(Counter(row["relation"] for row in aggregate_rows).items())
    )
    repeat["aggregate_document_counts"] = {
        str(key): count
        for key, count in sorted(
            Counter(
                row["document_source_position"] for row in aggregate_rows
            ).items()
        )
    }
    repeat["aggregate_handoff_status_counts"] = dict(
        sorted(
            Counter(row["handoff_status"] for row in aggregate_rows).items()
        )
    )
    redirection_rows = repeat["in_domain_redirection_disposition_rows"]
    repeat["in_domain_redirection_disposition_count"] = len(redirection_rows)
    repeat["in_domain_redirection_disposition_keyset_sha256"] = _keyset_sha(
        [
            row["in_domain_redirection_relation_disposition_id"]
            for row in redirection_rows
        ]
    )
    repeat["in_domain_redirection_disposition_domain_sha256"] = _domain_sha(
        redirection_rows
    )
    repeat["redirection_relation_counts"] = dict(
        sorted(Counter(row["relation"] for row in redirection_rows).items())
    )
    repeat["redirection_document_counts"] = {
        str(key): count
        for key, count in sorted(
            Counter(
                row["document_source_position"] for row in redirection_rows
            ).items()
        )
    }
    repeat["redirection_handoff_status_counts"] = dict(
        sorted(
            Counter(row["handoff_status"] for row in redirection_rows).items()
        )
    )

    component = bundle["component"]
    component_groups = (
        (
            "zero_parent_disposition_rows",
            "zero_parent_disposition_count",
            "zero_parent_disposition_domain_sha256",
        ),
        (
            "unique_parent_assignment_rows",
            "unique_parent_assignment_count",
            "unique_parent_assignment_domain_sha256",
        ),
        (
            "multi_parent_ambiguity_rows",
            "multi_parent_ambiguity_count",
            "multi_parent_ambiguity_domain_sha256",
        ),
    )
    complete_rows: list[dict[str, Any]] = []
    for row_key, count_key, domain_key in component_groups:
        rows = component[row_key]
        component[count_key] = len(rows)
        component[domain_key] = _domain_sha(rows)
        complete_rows.extend(rows)
    component["complete_component_resolution_count"] = len(complete_rows)
    component["complete_component_resolution_keyset_sha256"] = _keyset_sha(
        [row["component_parent_resolution_id"] for row in complete_rows]
    )
    component["complete_component_resolution_domain_sha256"] = _domain_sha(
        complete_rows
    )

    bundle["slice"] = _reseal_artifact(slice_artifact)
    bundle["sweeps"] = _reseal_artifact(sweep)
    predecessor["semantic_alias_sweep_artifact_id"] = bundle["sweeps"][
        "artifact_id"
    ]
    bundle["predecessor"] = _reseal_artifact(predecessor)
    derived["source_corpus_identity"] = bundle["sweeps"][
        "source_corpus_identity"
    ]
    derived["corpus_sweep_artifact_id"] = bundle["sweeps"]["artifact_id"]
    derived["predecessor_artifact_id"] = bundle["predecessor"]["artifact_id"]
    derived["round_four_new_fragment_seal_quality_issue_count"] = bundle[
        "predecessor"
    ]["round_four_new_fragment_seal_quality_issue_count"]
    derived["tier_2_predecessor_seal_quality_issue_count"] = bundle[
        "predecessor"
    ]["tier_2_predecessor_seal_quality_issue_count"]
    bundle["derived"] = _reseal_artifact(derived)
    for key in ("role", "repeat", "component"):
        bundle[key]["source_slice_artifact_id"] = bundle["slice"][
            "artifact_id"
        ]
        bundle[key]["corpus_sweep_artifact_id"] = bundle["sweeps"][
            "artifact_id"
        ]
        bundle[key] = _reseal_artifact(bundle[key])

    gate = bundle["gate"]
    gate["source_slice_artifact_id"] = bundle["slice"]["artifact_id"]
    gate["design_prefix_identity"] = bundle["slice"]["design_prefix_identity"]
    gate["pilot_census"] = bundle["slice"]["pilot_census"]
    gate["artifact_identity_rows"] = [
        {
            "artifact_role": key,
            "path": (
                "docs/analysis/amendment_12_rq_catalog_pilot/"
                + OUTPUT_FILENAMES[key]
            ),
            "schema_version": bundle[key]["schema_version"],
            "artifact_id": bundle[key]["artifact_id"],
            "byte_size": len(canonical_bytes(bundle[key])),
            "raw_sha256": _sha256(canonical_bytes(bundle[key])),
        }
        for key in (
            "slice",
            "sweeps",
            "derived",
            "predecessor",
            "role",
            "repeat",
            "component",
        )
    ]
    gate["artifact_identity_count"] = len(gate["artifact_identity_rows"])
    gate["artifact_identity_domain_sha256"] = _domain_sha(
        gate["artifact_identity_rows"]
    )
    bundle["gate"] = _reseal_artifact(gate)
    return bundle


def run_mutation_tests(
    original: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Require coherently repinned law-level mutations to fail semantically."""
    mutations: list[tuple[str, Any, str, bool]] = []

    def add(
        name: str,
        mutate: Any,
        expected_error: str,
        *,
        mutate_after_repin: bool = False,
    ) -> None:
        mutations.append((name, mutate, expected_error, mutate_after_repin))

    def forge_slice_integrity_extra(value: dict[str, Any]) -> None:
        value["slice"]["integrity"]["q5_emitted"] = True
        gate = value["gate"]
        identity = next(
            row
            for row in gate["artifact_identity_rows"]
            if row["artifact_role"] == "slice"
        )
        raw = canonical_bytes(value["slice"])
        identity["byte_size"] = len(raw)
        identity["raw_sha256"] = _sha256(raw)
        gate["artifact_identity_domain_sha256"] = _domain_sha(
            gate["artifact_identity_rows"]
        )
        value["gate"] = _reseal_artifact(gate)

    def forge_parent_and_source_witness(value: dict[str, Any]) -> None:
        pilot_row = value["component"]["unique_parent_assignment_rows"][0]
        position = pilot_row["document_source_position"]
        old_id = pilot_row["parent_candidate_rows"][0]["parent_occurrence_id"]
        new_id = "psid-questionnaire-occurrence:coherent-source-forgery"
        row_groups = [
            value["sweeps"]["component_parent_shape_rows"],
            value["component"]["zero_parent_disposition_rows"],
            value["component"]["unique_parent_assignment_rows"],
            value["component"]["multi_parent_ambiguity_rows"],
        ]
        for rows in row_groups:
            for row in rows:
                if row["document_source_position"] != position:
                    continue
                for candidate in row["parent_candidate_rows"]:
                    if candidate["parent_occurrence_id"] == old_id:
                        candidate["parent_occurrence_id"] = new_id
        witness = next(
            row
            for row in value["sweeps"]["parent_source_witness_rows"]
            if row["document_source_position"] == position
            and row["parent_occurrence_id"] == old_id
        )
        witness["parent_occurrence_id"] = new_id

    def forge_nonpilot_component_anchor(value: dict[str, Any]) -> None:
        row = next(
            item
            for item in value["sweeps"]["component_parent_shape_rows"]
            if item["document_source_position"] not in PILOT_POSITIONS
        )
        row["component_anchor_occurrence_id"] = (
            "psid-questionnaire-occurrence:coherent-component-forgery"
        )

    def forge_nonpilot_role_member(value: dict[str, Any]) -> None:
        pilot_members = {
            member
            for row in value["role"]["role_label_class_rows"]
            for member in row["member_occurrence_ids"]
        }
        row = next(
            item
            for item in value["sweeps"]["role_exact_label_class_rows"]
            if any(
                member not in pilot_members
                for member in item["member_occurrence_ids"]
            )
        )
        index = next(
            index
            for index, member in enumerate(row["member_occurrence_ids"])
            if member not in pilot_members
        )
        row["member_occurrence_ids"][
            index
        ] = "psid-questionnaire-occurrence:coherent-role-forgery"

    def append_reused_nonalias_support(
        value: dict[str, Any], evidence_id: str
    ) -> None:
        target_row = next(
            row
            for row in value["derived"]["component_class_admission_sweep_rows"]
            if any(
                support["support_origin"] == "sealed_local_evidence"
                for support in row["alias_support_rows"]
            )
        )
        support = copy.deepcopy(
            next(
                support
                for support in target_row["alias_support_rows"]
                if support["support_origin"] == "sealed_local_evidence"
            )
        )
        support["source_local_evidence_id"] = evidence_id
        support["semantic_alias_pair_adjudication_id"] = _row_id(
            "a12-semantic-alias-pair-adjudication-forgery:", [evidence_id]
        )
        target_row["alias_support_rows"].append(support)

    def reuse_redirection_evidence_as_alias_support(
        value: dict[str, Any],
    ) -> None:
        evidence_id = value["sweeps"]["in_domain_redirection_shape_rows"][0][
            "source_local_evidence_ids"
        ][0]
        append_reused_nonalias_support(value, evidence_id)

    def promote_fragment_stop_to_alias_support(
        value: dict[str, Any],
    ) -> None:
        stop_row = next(
            row
            for row in value["sweeps"][
                "in_domain_component_cross_reference_sweep_rows"
            ]
            if row["source_instruction_fragment"]
            and row["repeat_coverage_disposition"]
            == "disclosed_stop_no_redirection_semantics"
        )
        append_reused_nonalias_support(
            value, stop_row["source_local_evidence_ids"][0]
        )

    def forge_composite_typed_projection_union(
        value: dict[str, Any],
    ) -> None:
        pair = next(
            pair
            for row in value["sweeps"][
                "alias_evidence_semantic_adjudication_rows"
            ]
            for pair in row["approved_pair_rows"]
            if pair["pair_kind"] == "typed_instruction_import_projection"
        )
        pair["class_closure_eligible"] = True
        pair["typed_projection_union_prohibited"] = False

    def delete_composite_pair_citation(value: dict[str, Any]) -> None:
        pair = next(
            pair
            for row in value["sweeps"][
                "alias_evidence_semantic_adjudication_rows"
            ]
            for pair in row["approved_pair_rows"]
            if pair["pair_kind"] == "typed_instruction_import_projection"
        )
        pair["exact_pairing_citation"] = None

    def swap_composite_pair_citation(value: dict[str, Any]) -> None:
        pairs = [
            pair
            for row in value["sweeps"][
                "alias_evidence_semantic_adjudication_rows"
            ]
            for pair in row["approved_pair_rows"]
            if pair["pair_kind"] == "typed_instruction_import_projection"
        ]
        replacement = next(
            pair
            for pair in pairs[1:]
            if pair["semantic_type"] != pairs[0]["semantic_type"]
        )
        pairs[0]["exact_pairing_citation"] = copy.deepcopy(
            replacement["exact_pairing_citation"]
        )

    def delete_composite_stop_citation(value: dict[str, Any]) -> None:
        row = next(
            row
            for row in value["sweeps"][
                "alias_evidence_semantic_adjudication_rows"
            ]
            if row["composite_stop_citation"] is not None
        )
        row["composite_stop_citation"] = None

    def remove_nonledger_semantic_decision(
        value: dict[str, Any],
    ) -> None:
        rows = value["sweeps"]["alias_evidence_semantic_adjudication_rows"]
        index = next(
            index
            for index, row in enumerate(rows)
            if row["candidate_origin"]
            == "ca41663_nonledger_bypass_adjudication"
            and row["approved_pair_rows"]
        )
        rows.pop(index)

    def forge_continuation_composition_rule(
        value: dict[str, Any],
    ) -> None:
        semantic_row = next(
            row
            for row in value["sweeps"][
                "alias_evidence_semantic_adjudication_rows"
            ]
            if row["round_five_continuation_restoration"]
        )
        instruction_id = semantic_row["source_instruction_occurrence_ids"][0]
        structural_row = next(
            row
            for row in value["sweeps"][
                "in_domain_component_cross_reference_sweep_rows"
            ]
            if row["source_instruction_occurrence_id"] == instruction_id
        )
        for row in (semantic_row, structural_row):
            row["continuation_composition_citation"][
                "composition_rule"
            ] = "forged_non_whitespace_continuation_rule"

    def forge_outside_target_bytes(value: dict[str, Any]) -> None:
        for artifact_key, row_key in (
            ("sweeps", "outside_domain_repeat_shape_rows"),
            ("repeat", "outside_domain_repeat_disposition_rows"),
        ):
            unresolved = value[artifact_key][row_key][0][
                "unresolved_target_reference"
            ]
            forged = "X" * len(unresolved["matched_text"].encode("utf-8"))
            unresolved["matched_text"] = forged
            unresolved["matched_utf8_sha256"] = _sha256(forged.encode("utf-8"))

    def forge_aggregate_relation_source_text(value: dict[str, Any]) -> None:
        pilot_row = value["repeat"][
            "noncatalog_aggregate_relation_disposition_rows"
        ][0]
        evidence_id = pilot_row["source_local_evidence_id"]
        for artifact_key, row_key in (
            ("sweeps", "noncatalog_aggregate_relation_shape_rows"),
            ("repeat", "noncatalog_aggregate_relation_disposition_rows"),
        ):
            row = next(
                item
                for item in value[artifact_key][row_key]
                if item["source_local_evidence_id"] == evidence_id
            )
            raw_length = len(
                row["source_instruction_matched_texts"][0].encode("utf-8")
            )
            forged = "X" * raw_length
            row["source_instruction_matched_texts"][0] = forged
            row["source_instruction_matched_utf8_sha256s"][0] = _sha256(
                forged.encode("utf-8")
            )

    def mutate_redirection_rows(value: dict[str, Any], mutation: Any) -> None:
        for artifact_key, row_key in (
            ("sweeps", "in_domain_redirection_shape_rows"),
            ("repeat", "in_domain_redirection_disposition_rows"),
        ):
            mutation(value[artifact_key][row_key][0])

    def forge_redirection_source_text(value: dict[str, Any]) -> None:
        def forge(row: dict[str, Any]) -> None:
            raw_length = len(
                row["source_instruction_matched_texts"][0].encode("utf-8")
            )
            forged = "X" * raw_length
            row["source_instruction_matched_texts"][0] = forged
            row["source_instruction_matched_utf8_sha256s"][0] = _sha256(
                forged.encode("utf-8")
            )

        mutate_redirection_rows(value, forge)

    def forge_catalog_only_job_source_member(value: dict[str, Any]) -> None:
        referenced_job_occurrence_ids = {
            candidate["parent_occurrence_id"]
            for component_row in value["sweeps"]["component_parent_shape_rows"]
            for candidate in component_row["parent_candidate_rows"]
            if candidate["parent_occurrence_kind"] == "job_anchor"
        }
        row = next(
            item
            for item in value["derived"][
                "catalog_only_job_complement_sweep_rows"
            ]
            if item["job_class_member_count"] == 1
            and item["candidate_relationship_count"] == 0
            and item["alias_support_count"] == 0
            and not set(item["job_class_member_occurrence_ids"])
            & referenced_job_occurrence_ids
        )
        forged_id = "psid-questionnaire-occurrence:coherent-job-forgery"
        row["canonical_job_occurrence_id"] = forged_id
        row["job_class_member_occurrence_ids"] = [forged_id]

    add(
        "pilot_slice_reordered",
        lambda value: value["slice"]["pilot_document_rows"].reverse(),
        "pilot positions drift",
    )
    add(
        "pilot_claims_q5",
        lambda value: value["slice"]["nonauthority_statement"].__setitem__(
            "q5_emitted", True
        ),
        "nonauthority drift",
    )
    add(
        "slice_integrity_q5_emitted_extra",
        forge_slice_integrity_extra,
        "integrity: keyset drift",
        mutate_after_repin=True,
    )
    add(
        "pilot_census_required_key_omitted",
        lambda value: value["slice"]["pilot_census"].pop(
            "component_parent_disposition_counts"
        ),
        "slice pilot census: keyset drift",
    )
    add(
        "pilot_census_extra_member",
        lambda value: value["slice"]["pilot_census"].__setitem__(
            "forged_extra_member", 1
        ),
        "slice pilot census: keyset drift",
    )
    add(
        "pilot_census_parent_dispositions_forged",
        lambda value: value["slice"]["pilot_census"].__setitem__(
            "component_parent_disposition_counts", {"forged": 1}
        ),
        "component_parent_disposition_counts: keyset drift",
    )
    add(
        "role_assignment_omitted",
        lambda value: value["role"]["role_assignment_rows"].pop(),
        "pilot role assignment count drift",
    )
    add(
        "role_assignment_role_flipped",
        lambda value: value["role"]["role_assignment_rows"][0].__setitem__(
            "assigned_role", ROLE_SPOUSE
        ),
        "assigned role/class mismatch",
    )
    add(
        "role_assignment_class_invented",
        lambda value: value["role"]["role_assignment_rows"][0].__setitem__(
            "role_label_class_id", "a12-role-exact-label-class:invented"
        ),
        "dangling role class",
    )
    add(
        "role_assignment_alias_admitted",
        lambda value: value["role"]["role_assignment_rows"][0].__setitem__(
            "alias_admitted_by_assignment", True
        ),
        "alias admitted",
    )
    add(
        "role_assignment_equivalence_claimed",
        lambda value: value["role"]["role_assignment_rows"][0].__setitem__(
            "occurrence_equivalence_claimed", True
        ),
        "occurrence equivalence claimed",
    )
    add(
        "role_sweep_class_omitted",
        lambda value: value["sweeps"]["role_exact_label_class_rows"].pop(),
        "role class count drift",
    )
    add(
        "role_sweep_alias_class_claimed",
        lambda value: value["sweeps"]["role_exact_label_class_rows"][
            0
        ].__setitem__("alias_class_claimed", True),
        "alias class claimed",
    )
    add(
        "role_sweep_source_member_forged",
        forge_nonpilot_role_member,
        "role sweep pinned source projection drift",
    )
    add(
        "outside_repeat_target_emptied",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0].__setitem__("unresolved_target_reference", {}),
        "unresolved target: keyset drift",
    )
    add(
        "outside_repeat_terminal_changed",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0].__setitem__("terminal_disposition", "admit_alias"),
        "terminal disposition",
    )
    add(
        "outside_repeat_universal_arm_false",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0].__setitem__("universal_repeat_coverage_arm_satisfied", False),
        "universal arm",
    )
    add(
        "outside_repeat_alias_admitted",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0].__setitem__("alias_admitted", True),
        "alias admitted",
    )
    add(
        "outside_repeat_evidence_not_singleton",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0]["evidence_occurrence_ids"].append(
            "psid-questionnaire-occurrence:invented"
        ),
        "evidence is not singleton self",
    )
    add(
        "outside_repeat_source_target_forged",
        forge_outside_target_bytes,
        "repeat sweep pinned source projection drift",
    )
    add(
        "aggregate_relation_row_omitted",
        lambda value: value["repeat"][
            "noncatalog_aggregate_relation_disposition_rows"
        ].pop(),
        "pilot aggregate relation drift",
    )
    add(
        "aggregate_relation_required_key_omitted",
        lambda value: value["repeat"][
            "noncatalog_aggregate_relation_disposition_rows"
        ][0].pop("occurrence_equivalence_claimed"),
        "aggregate relation pilot row: keyset drift",
    )
    add(
        "aggregate_relation_alias_admitted",
        lambda value: value["repeat"][
            "noncatalog_aggregate_relation_disposition_rows"
        ][0].__setitem__("alias_admitted", True),
        "alias admitted",
    )
    add(
        "aggregate_relation_equivalence_claimed",
        lambda value: value["repeat"][
            "noncatalog_aggregate_relation_disposition_rows"
        ][0].__setitem__("occurrence_equivalence_claimed", True),
        "occurrence equivalence claimed",
    )
    add(
        "aggregate_relation_universal_arm_false",
        lambda value: value["repeat"][
            "noncatalog_aggregate_relation_disposition_rows"
        ][0].__setitem__("universal_repeat_coverage_arm_satisfied", False),
        "universal arm",
    )
    add(
        "aggregate_relation_endpoint_domain_changed",
        lambda value: value["repeat"][
            "noncatalog_aggregate_relation_disposition_rows"
        ][0]["endpoint_raw_node_domains"].__setitem__(0, "job_slot"),
        "aggregate endpoint predicate",
    )
    add(
        "aggregate_relation_source_text_forged",
        forge_aggregate_relation_source_text,
        "aggregate relation sweep pinned source projection drift",
    )
    add(
        "redirection_relation_row_omitted",
        lambda value: value["repeat"][
            "in_domain_redirection_disposition_rows"
        ].pop(),
        "pilot redirection drift",
    )
    add(
        "redirection_relation_subkind_changed",
        lambda value: mutate_redirection_rows(
            value,
            lambda row: row.__setitem__("relation_subkind", "invented"),
        ),
        "relation identity",
    )
    add(
        "redirection_relation_alias_admitted",
        lambda value: mutate_redirection_rows(
            value, lambda row: row.__setitem__("alias_admitted", True)
        ),
        "alias admitted",
    )
    add(
        "redirection_relation_equivalence_claimed",
        lambda value: mutate_redirection_rows(
            value,
            lambda row: row.__setitem__(
                "occurrence_equivalence_claimed", True
            ),
        ),
        "occurrence equivalence",
    )
    add(
        "redirection_relation_universal_arm_false",
        lambda value: mutate_redirection_rows(
            value,
            lambda row: row.__setitem__(
                "universal_repeat_coverage_arm_satisfied", False
            ),
        ),
        "universal arm",
    )

    def change_redirection_destination(value: dict[str, Any]) -> None:
        for artifact_key, row_key in (
            ("sweeps", "in_domain_redirection_shape_rows"),
            ("repeat", "in_domain_redirection_disposition_rows"),
        ):
            row = next(
                candidate
                for candidate in value[artifact_key][row_key]
                if candidate["source_local_evidence_ids"]
                == list(REDIRECTION_LAW_GAP_EVIDENCE_IDS)
            )
            row["endpoint_printed_identifiers"][1] = "G79."
            changed = "should be included at G79, not here."
            row["source_instruction_matched_texts"][0] = changed
            row["source_instruction_matched_utf8_sha256s"][0] = _sha256(
                changed.encode("utf-8")
            )

    add(
        "redirection_relation_destination_changed",
        change_redirection_destination,
        "redirection sweep pinned source projection drift",
    )
    add(
        "redirection_relation_source_text_forged",
        forge_redirection_source_text,
        "redirection sweep pinned source projection drift",
    )
    add(
        "redirection_lineage_row_omitted",
        lambda value: value["sweeps"][
            "in_domain_component_cross_reference_sweep_rows"
        ].pop(),
        "component cross-reference sweep census drift",
    )
    add(
        "redirection_law_gap_demoted_to_seal_defect",
        lambda value: next(
            row
            for row in value["predecessor"][
                "populated_local_proof_adjudication_rows"
            ]
            if row["in_domain_nonalias_relation_subkind"]
            == REDIRECTION_RELATION_SUBKIND
        ).__setitem__("disposition", "predecessor_seal_defect"),
        "redirection law-gap adjudication",
    )
    add(
        "zero_parent_emits_rq",
        lambda value: value["component"]["zero_parent_disposition_rows"][
            0
        ].__setitem__("r_q_relationship_emitted", True),
        "pilot emitted R_Q",
    )
    add(
        "unique_parent_forced",
        lambda value: value["component"]["unique_parent_assignment_rows"][
            0
        ].__setitem__("forced_parent_selection", True),
        "forced parent",
    )
    add(
        "unique_parent_derived_slot_invented",
        lambda value: value["component"]["unique_parent_assignment_rows"][0][
            "parent_candidate_rows"
        ][0].__setitem__("derived_slot_kind", "invented_slot"),
        "derived slot equation",
    )
    add(
        "unique_parent_source_invented",
        lambda value: value["component"]["unique_parent_assignment_rows"][0][
            "parent_candidate_rows"
        ][0].__setitem__(
            "parent_occurrence_id", "psid-questionnaire-occurrence:invented"
        ),
        "no source witness",
    )
    add(
        "parent_and_source_witness_forged",
        forge_parent_and_source_witness,
        "parent witness pinned source projection drift",
    )
    add(
        "ambiguity_forced_parent",
        lambda value: value["component"]["multi_parent_ambiguity_rows"][
            0
        ].__setitem__("forced_parent_selection", True),
        "forced parent",
    )
    add(
        "ambiguity_emits_rq",
        lambda value: value["component"]["multi_parent_ambiguity_rows"][
            0
        ].__setitem__("r_q_relationship_emitted", True),
        "pilot emitted R_Q",
    )
    add(
        "component_sweep_row_omitted",
        lambda value: value["sweeps"]["component_parent_shape_rows"].pop(),
        "component sweep count drift",
    )
    add(
        "component_sweep_source_anchor_forged",
        forge_nonpilot_component_anchor,
        "component sweep pinned source projection drift",
    )
    add(
        "component_row_extra_key",
        lambda value: value["component"]["zero_parent_disposition_rows"][
            0
        ].__setitem__("invented_key", True),
        "component pilot row: keyset drift",
    )
    add(
        "redirection_evidence_reused_as_alias_support",
        reuse_redirection_evidence_as_alias_support,
        "derived alias support lacks a semantic gate pair",
    )
    add(
        "fragment_stop_promoted_to_alias_support",
        promote_fragment_stop_to_alias_support,
        "derived alias support lacks a semantic gate pair",
    )
    add(
        "semantic_alias_adjudication_record_forged",
        lambda value: value["sweeps"][
            "in_domain_component_cross_reference_sweep_rows"
        ][0].__setitem__("semantic_alias_finding", "forged_semantic_finding"),
        "source-text semantic adjudication",
    )
    add(
        "composite_union_forgery",
        forge_composite_typed_projection_union,
        "closure law",
    )
    add(
        "composite_pair_citation_deleted",
        delete_composite_pair_citation,
        "typed pair lacks its pinned exact-text derivation",
    )
    add(
        "composite_pair_citation_swapped",
        swap_composite_pair_citation,
        "typed pair lacks its pinned exact-text derivation",
    )
    add(
        "composite_stop_citation_deleted",
        delete_composite_stop_citation,
        "composite STOP citation mismatch",
    )
    add(
        "nonledger_admission_without_semantic_decision",
        remove_nonledger_semantic_decision,
        "sole semantic gate evidence census drift",
    )
    add(
        "continuation_rule_forgery",
        forge_continuation_composition_rule,
        "continuation composition citation",
    )
    add(
        "component_class_sweep_row_omitted",
        lambda value: value["derived"][
            "component_class_admission_sweep_rows"
        ].pop(),
        "component candidate class count drift",
    )
    add(
        "component_class_sweep_relationship_arm_flipped",
        lambda value: next(
            row
            for row in value["derived"]["component_class_admission_sweep_rows"]
            if row["relationship_arm_eligible"]
        ).__setitem__("relationship_arm_eligible", False),
        "candidate relationship arm",
    )
    add(
        "job_complement_sweep_row_omitted",
        lambda value: value["derived"][
            "catalog_only_job_complement_sweep_rows"
        ].pop(),
        "job class count drift",
    )
    add(
        "job_complement_coverage_arm_flipped",
        lambda value: value["derived"][
            "catalog_only_job_complement_sweep_rows"
        ][0].__setitem__("coverage_arm", "invented_coverage_arm"),
        "coverage arm",
    )
    add(
        "exact_pair_support_label_forged",
        lambda value: next(
            support
            for row in value["derived"]["component_class_admission_sweep_rows"]
            for support in row["alias_support_rows"]
            if support["support_origin"] == "exact_pair_equality_sweep"
        ).__setitem__("exact_label", "invented exact label"),
        "component class admission pinned source projection drift",
    )
    add(
        "catalog_only_job_source_member_forged",
        forge_catalog_only_job_source_member,
        "catalog-only job complement pinned source projection drift",
    )
    add(
        "doc036_law_gap_admitted",
        lambda value: value["predecessor"][
            "doc036_aggregate_component_slot_rows"
        ][0].__setitem__("law_gap_admitted", True),
        "law gap admitted",
    )
    add(
        "doc036_component_slot_admitted",
        lambda value: value["predecessor"][
            "doc036_aggregate_component_slot_rows"
        ][0].__setitem__("component_slot_admitted", True),
        "component slot admitted",
    )
    add(
        "doc036_source_occurrence_forged",
        lambda value: value["predecessor"][
            "doc036_aggregate_component_slot_rows"
        ][0].__setitem__(
            "source_occurrence_id",
            "psid-questionnaire-occurrence:coherent-doc036-forgery",
        ),
        "doc036 adjudication pinned source projection drift",
    )
    add(
        "proof_defect_lawified",
        lambda value: value["predecessor"][
            "populated_local_proof_adjudication_rows"
        ][0].__setitem__("disposition", "law_gap"),
        "seal-defect adjudication",
    )
    add(
        "proof_defect_action_removed",
        lambda value: value["predecessor"][
            "populated_local_proof_adjudication_rows"
        ][0].__setitem__("required_action", "do_nothing"),
        "seal-defect adjudication",
    )
    add(
        "proof_defect_row_omitted",
        lambda value: value["predecessor"][
            "populated_local_proof_adjudication_rows"
        ].pop(),
        "proof adjudication count drift",
    )
    add(
        "aggregate_law_gap_demoted_to_seal_defect",
        lambda value: next(
            row
            for row in value["predecessor"][
                "populated_local_proof_adjudication_rows"
            ]
            if row["in_domain_nonalias_relation_subkind"]
            == AGGREGATE_RELATION_SUBKIND
        ).__setitem__("disposition", "predecessor_seal_defect"),
        "aggregate law-gap adjudication",
    )
    add(
        "aggregate_law_gap_source_projection_forged",
        lambda value: next(
            row
            for row in value["predecessor"][
                "populated_local_proof_adjudication_rows"
            ]
            if row["in_domain_nonalias_relation_subkind"]
            == AGGREGATE_RELATION_SUBKIND
        ).update(
            {
                "source_instruction_occurrence_ids": [],
                "evidence_occurrence_ids": [],
            }
        ),
        "proof adjudication row: instructions",
    )
    add(
        "gate_claims_certification",
        lambda value: value["gate"].__setitem__(
            "certification_status", "certified"
        ),
        "pilot claims certification",
    )
    add(
        "gate_claims_repeat_coverage",
        lambda value: value["gate"].__setitem__(
            "overall_repeat_catalog_coverage_status", "pass"
        ),
        "pilot falsely claims universal catalog coverage",
    )

    rejected: list[str] = []
    for name, mutation, expected_error, mutate_after_repin in mutations:
        candidate = copy.deepcopy(dict(original))
        if mutate_after_repin:
            candidate = _repin_mutated_bundle(candidate)
            mutation(candidate)
        else:
            mutation(candidate)
            candidate = _repin_mutated_bundle(candidate)
        try:
            validate_bundle(candidate)
        except BuildError as error:
            _require(
                expected_error in str(error),
                f"mutation {name} hit wrong gate: {error}",
            )
            rejected.append(name)
        else:
            raise BuildError(f"mutation survived validation: {name}")
    return rejected


def _artifact_paths(output_root: Path) -> dict[str, Path]:
    return {
        key: output_root / filename
        for key, filename in OUTPUT_FILENAMES.items()
    }


def load_committed_bundle(
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, dict[str, Any]]:
    bundle: dict[str, dict[str, Any]] = {}
    for key, path in _artifact_paths(output_root).items():
        raw = path.read_bytes()
        value = strict_json_loads(raw, str(path))
        _require(isinstance(value, dict), f"{path}: not object")
        _require(raw == canonical_bytes(value), f"{path}: noncanonical bytes")
        bundle[key] = value
    return bundle


@dataclass(frozen=True)
class _DestinationBackup:
    label: str
    destination: Path
    path: Path | None


def _fsync_directory(path: Path) -> None:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError as error:
        raise BuildError(
            f"cannot fsync output directory {path}: {error}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _preflight_output_paths(paths: Mapping[str, Path]) -> None:
    resolved: dict[Path, str] = {}
    inodes: dict[tuple[int, int], str] = {}
    for label, path in paths.items():
        target = path.resolve(strict=False)
        _require(
            target not in resolved,
            f"output path collision: {label} aliases {resolved.get(target)}",
        )
        resolved[target] = label
        try:
            status = os.lstat(path)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise BuildError(
                f"cannot inspect output {path}: {error}"
            ) from error
        _require(not path.is_symlink(), f"output path is a symlink: {path}")
        identity = (status.st_dev, status.st_ino)
        _require(
            identity not in inodes,
            f"output inode collision: {label} aliases {inodes.get(identity)}",
        )
        inodes[identity] = label


def _stage_output(label: str, destination: Path, raw: bytes) -> Path:
    descriptor = -1
    staged: Path | None = None
    valid = False
    try:
        descriptor, raw_path = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.a12-stage-",
        )
        staged = Path(raw_path)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _require(
            staged.read_bytes() == raw, f"staged output mismatch: {label}"
        )
        valid = True
        return staged
    except BuildError:
        raise
    except OSError as error:
        raise BuildError(f"cannot stage output {label}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if staged is not None and not valid:
            staged.unlink(missing_ok=True)


def _backup_destination(label: str, destination: Path) -> _DestinationBackup:
    if not destination.exists():
        return _DestinationBackup(label, destination, None)
    descriptor = -1
    backup: Path | None = None
    valid = False
    try:
        descriptor, raw_path = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.a12-backup-",
        )
        os.close(descriptor)
        descriptor = -1
        backup = Path(raw_path)
        backup.unlink()
        os.link(destination, backup, follow_symlinks=False)
        valid = True
        return _DestinationBackup(label, destination, backup)
    except OSError as error:
        raise BuildError(f"cannot back up output {label}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if backup is not None and not valid:
            backup.unlink(missing_ok=True)


def _restore_destination(backup: _DestinationBackup) -> None:
    if backup.path is None:
        backup.destination.unlink(missing_ok=True)
        return
    descriptor, raw_path = tempfile.mkstemp(
        dir=backup.destination.parent,
        prefix=f".{backup.destination.name}.a12-restore-",
    )
    os.close(descriptor)
    restore = Path(raw_path)
    try:
        restore.unlink()
        os.link(backup.path, restore, follow_symlinks=False)
        os.replace(restore, backup.destination)
    finally:
        restore.unlink(missing_ok=True)


def _write_bundle(
    bundle: Mapping[str, Mapping[str, Any]],
    output_root: Path,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    paths = _artifact_paths(output_root)
    _preflight_output_paths(paths)
    staged: list[tuple[str, Path, Path, bytes]] = []
    backups: list[_DestinationBackup] = []
    commit_succeeded = False
    rollback_succeeded = False
    try:
        for key, destination in paths.items():
            raw = canonical_bytes(bundle[key])
            temporary = _stage_output(key, destination, raw)
            staged.append((key, destination, temporary, raw))
        for key, destination, _temporary, _raw in staged:
            backups.append(_backup_destination(key, destination))
        for _key, destination, temporary, _raw in staged:
            os.replace(temporary, destination)
        for key, destination, _temporary, expected in staged:
            _require(
                destination.read_bytes() == expected,
                f"published output mismatch: {key}",
            )
        _fsync_directory(output_root)
        commit_succeeded = True
    except Exception as commit_error:
        rollback_errors: list[str] = []
        for backup in backups:
            try:
                _restore_destination(backup)
            except Exception as rollback_error:
                rollback_errors.append(f"{backup.label}: {rollback_error}")
        try:
            _fsync_directory(output_root)
        except BuildError as rollback_error:
            rollback_errors.append(str(rollback_error))
        rollback_succeeded = not rollback_errors
        if rollback_errors:
            raise BuildError(
                "output transaction failed and rollback is incomplete; "
                + "; ".join(rollback_errors)
            ) from commit_error
        raise BuildError(
            "output transaction failed; all prior destinations restored"
        ) from commit_error
    finally:
        for _key, _destination, temporary, _raw in staged:
            temporary.unlink(missing_ok=True)
        if commit_succeeded or rollback_succeeded:
            for backup in backups:
                if backup.path is not None:
                    backup.path.unlink(missing_ok=True)


def _check_bundle(
    expected: Mapping[str, Mapping[str, Any]],
    output_root: Path,
) -> None:
    actual = load_committed_bundle(output_root)
    validate_bundle(actual)
    for key in OUTPUT_FILENAMES:
        expected_raw = canonical_bytes(expected[key])
        actual_raw = canonical_bytes(actual[key])
        _require(expected_raw == actual_raw, f"artifact drift: {key}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        help=(
            "optional clean worktree at the pinned source commit; all read "
            "bytes are still checked against the era-seal identities"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=OUTPUT_ROOT,
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mutation-tests", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    design_prefix = _validate_design_prefix()
    if args.mutation_tests and not args.check:
        bundle = load_committed_bundle(args.output_root)
        validate_bundle(bundle)
    else:
        reader = SourceReader(args.source_root)
        documents, source_identity = _load_documents(reader)
        bundle = _build_bundle(documents, source_identity, design_prefix)
        validate_bundle(bundle)
        if args.check:
            _check_bundle(bundle, args.output_root)
        else:
            _write_bundle(bundle, args.output_root)
    mutation_names: list[str] = []
    if args.mutation_tests:
        mutation_names = run_mutation_tests(bundle)
    result = {
        "artifact_count": len(bundle),
        "check": bool(args.check),
        "mutation_test_count": len(mutation_names),
        "mutation_tests": mutation_names,
        "source_commit": SOURCE_COMMIT,
        "status": "pass",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
