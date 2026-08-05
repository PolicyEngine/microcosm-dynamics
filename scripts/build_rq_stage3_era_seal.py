#!/usr/bin/env python3
"""Build compact nonauthority preparation seals for the six R_Q eras.

The stage-2 document annotations remain the sole serialized source-local row
domains.  An era seal walks those committed rows in the fixed source order and
records counts, ordered keyset digests, and ordered row-domain digests.  It
does not duplicate the potentially very large page, occurrence, or flow arrays
and does not emit Q5, a global catalog, R_Q, hierarchy, slot, inventory, or
legal-registry rows.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from collections import defaultdict, deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_global_q5_intermediate_evidence as source_tools  # noqa: E402
import build_rq_stage1_candidates as stage1_candidates  # noqa: E402

SCHEMA_VERSION = "rq_stage3_era_preparation_seal_nonauthority.v1"
AUTHORITY_KIND = "era_source_annotation_preparation_seal_nonauthority"
STATUS = "sealed_complete_nonauthority_era_preparation"
CANONICALIZATION = source_tools.CANONICALIZATION
MAX_COMMITTED_FILE_BYTES = 50_000_000
FLOW_ROOT = "questionnaire-flow:root"
FORBIDDEN_PARENT_PATH_MARKER = "#parent" "-path-"

ANNOTATION_ROOT = ROOT / "docs" / "analysis" / "rq_stage2_annotations"
OUTPUT_ROOT = ROOT / "docs" / "analysis" / "rq_stage3_era_seals"
PROTOCOL_PATH = ROOT / "docs" / "analysis" / "rq_stage2_protocol.md"

LEGACY_SCHEMA = "rq_stage2_document_annotation_nonauthority.v1"
MODERN_SCHEMA = "rq_stage2_document_annotation.v1"
LOCAL_EDGE_SCHEMA = "rq_stage2_document_annotation_local_edges_nonauthority.v1"
ALLOWED_ANNOTATION_SCHEMAS = {
    LEGACY_SCHEMA,
    MODERN_SCHEMA,
    LOCAL_EDGE_SCHEMA,
}

ERA_SPECS = (
    {
        "era_id": "wave1968_ry1968_1974_early_totals",
        "era_order_position": 1,
        "interview_waves": tuple(range(1968, 1976)),
        "document_source_positions": tuple(range(1, 17)),
        "questionnaire_document_count": 16,
        "questionnaire_page_count": 842,
    },
    {
        "era_id": "ry1975_1977_spouse_concept_seam",
        "era_order_position": 2,
        "interview_waves": (1976, 1977, 1978),
        "document_source_positions": tuple(range(17, 23)),
        "questionnaire_document_count": 6,
        "questionnaire_page_count": 408,
    },
    {
        "era_id": "ry1978_1992_pre_er_totals",
        "era_order_position": 3,
        "interview_waves": tuple(range(1979, 1994)),
        "document_source_positions": tuple(range(23, 52)),
        "questionnaire_document_count": 29,
        "questionnaire_page_count": 3_349,
    },
    {
        "era_id": "ry1993_2001_er_transition",
        "era_order_position": 4,
        "interview_waves": (1994, 1995, 1996, 1997, 1999, 2001),
        "document_source_positions": tuple(range(52, 64)),
        "questionnaire_document_count": 12,
        "questionnaire_page_count": 1_622,
    },
    {
        "era_id": "ry2002_2014_modern_bc_de",
        "era_order_position": 5,
        "interview_waves": (2003, 2005, 2007, 2009, 2011, 2013, 2015),
        "document_source_positions": tuple(range(64, 78)),
        "questionnaire_document_count": 14,
        "questionnaire_page_count": 2_337,
    },
    {
        "era_id": "ry2015_2022_exclusion_lineage",
        "era_order_position": 6,
        "interview_waves": (2017, 2019, 2021, 2023),
        "document_source_positions": tuple(range(78, 82)),
        "questionnaire_document_count": 4,
        "questionnaire_page_count": 1_632,
    },
)
ERA_BY_ID = {row["era_id"]: row for row in ERA_SPECS}

# Extend this tuple by exactly one member in each later era-seal commit.
SEALED_ERA_IDS = (
    "wave1968_ry1968_1974_early_totals",
    "ry1975_1977_spouse_concept_seam",
    "ry1978_1992_pre_er_totals",
    "ry1993_2001_er_transition",
    "ry2002_2014_modern_bc_de",
    "ry2015_2022_exclusion_lineage",
)

EXPECTED_RASTER_SIDECAR_POSITIONS = frozenset({6, 10, 12, 24})
PINNED_RASTER_SIDECAR_SHA256_BY_POSITION = {
    6: "f8a6fa74c379ff2986c52b5c77b922e024232c3322388bd422ba1ee44621aaf7",
    10: "fe2a50869b7610cee9ec02714fa10167f539cd3a85405b0d2077d070f2510f0b",
    12: "4f801008396ba64d06e6d6f61acfb5c2c745df4fafcb694fc880d694f691c12d",
    24: "967664f79dfa223205cd0c315e9da7f56e3473d5a27580b9ec301ced309f8afb",
}
LOCAL_FLOW_EDGE_ORDER_BY_POSITION = {
    12: "direct_parents_precede_children_in_source_order",
    31: "logical_dag_may_reference_later_extracted_labels",
    53: "logical_dag_may_reference_later_extracted_labels",
    60: "logical_dag_may_reference_later_extracted_labels",
    80: "logical_dag_may_reference_later_extracted_labels",
}
PINNED_DECLARED_SCOPE_SHA256_BY_POSITION = {
    34: "ba9f347e7b242e0c322c70b728f0fc1adf3d76e1af0501ebb267c14c0229136e",
}

ROW_DOMAIN_SPECS = (
    ("document_source_rows", ("source_document_id",)),
    ("whole_document_locator_rows", ("locator_id",)),
    ("questionnaire_page_rows", ("questionnaire_page_id",)),
    (
        "questionnaire_occurrence_rows",
        ("questionnaire_occurrence_id",),
    ),
    ("flow_branch_rows", ("flow_branch_id",)),
)
ROW_DOMAIN_SEAL_KEYS = {
    "row_domain",
    "row_count",
    "row_key_fields",
    "row_keyset_sha256",
    "row_domain_sha256",
}

# These values are independently rederived from the fresh stage-2 seals and
# become immutable expectations when the corresponding era commit lands.
PINNED_ROW_DOMAIN_SEALS: dict[str, tuple[dict[str, Any], ...]] = {
    "wave1968_ry1968_1974_early_totals": (
        {
            "row_domain": "document_source_rows",
            "row_count": 16,
            "row_key_fields": ["source_document_id"],
            "row_keyset_sha256": (
                "0d2574867e9bac154f8775349aed51ff7d3aee59debc2e44c948014d27b6e5fe"
            ),
            "row_domain_sha256": (
                "8585fbe3d7901ff6633a79c46d8caf8b454c7638c2a0b732f0ede77f7d637a8c"
            ),
        },
        {
            "row_domain": "whole_document_locator_rows",
            "row_count": 16,
            "row_key_fields": ["locator_id"],
            "row_keyset_sha256": (
                "1acb2020ea9d40bec79578aedadef87ce83a9a404311958ae2721a71d24e1223"
            ),
            "row_domain_sha256": (
                "760f36c54f01205e9907fa404752303998bbf78ede7d809ce5b6b50e1ebbb4b8"
            ),
        },
        {
            "row_domain": "questionnaire_page_rows",
            "row_count": 842,
            "row_key_fields": ["questionnaire_page_id"],
            "row_keyset_sha256": (
                "b2182081d71c02dc0625fdfccda04a7fc91cfb2d9db3f289a974a7380a06546d"
            ),
            "row_domain_sha256": (
                "155e3b1e387fe96900e2a50d82b7321452e59b6a4560bee4cdb61bf7078b9f1e"
            ),
        },
        {
            "row_domain": "questionnaire_occurrence_rows",
            "row_count": 5_621,
            "row_key_fields": ["questionnaire_occurrence_id"],
            "row_keyset_sha256": (
                "9f7833c422780526089eef159ee4539fe384fdd437ff6dfa7c1ffd0b12c521d7"
            ),
            "row_domain_sha256": (
                "06ac02b711f30572cff1f4c6efd291d710d91b2a1ce3698315e73c9b031fffd7"
            ),
        },
        {
            "row_domain": "flow_branch_rows",
            "row_count": 1_531,
            "row_key_fields": ["flow_branch_id"],
            "row_keyset_sha256": (
                "ae1522724647d3ff43ff72095898f266d48a8dec3f34ae58c891bfd4b0c9bc19"
            ),
            "row_domain_sha256": (
                "f58717f3983180a4515afb47dca5bf1a44936db7e35f7d0db3e9a30c2c7e4931"
            ),
        },
    ),
    "ry1975_1977_spouse_concept_seam": (
        {
            "row_domain": "document_source_rows",
            "row_count": 6,
            "row_key_fields": ["source_document_id"],
            "row_keyset_sha256": (
                "a8272d7c89fed313b421c273f7f1990cae7c7a6278c934b24038813d87997efa"
            ),
            "row_domain_sha256": (
                "2d61e4a9664684e7c85fc99b049e13a2ee9147c2175cf8f9c2255cbeabca9b15"
            ),
        },
        {
            "row_domain": "whole_document_locator_rows",
            "row_count": 6,
            "row_key_fields": ["locator_id"],
            "row_keyset_sha256": (
                "781503ddb5c277bbdfc991ffaaa0cc5f5f501a07a82c0327b774c5ff0f85713b"
            ),
            "row_domain_sha256": (
                "143ee1802004812140ef5e019ab4eb422b0a850776e57308f85ae09c2ec1b522"
            ),
        },
        {
            "row_domain": "questionnaire_page_rows",
            "row_count": 408,
            "row_key_fields": ["questionnaire_page_id"],
            "row_keyset_sha256": (
                "695f1796cddcd2170e39b8d1e9ae550cdd0f0704326128cac72107309e633ce8"
            ),
            "row_domain_sha256": (
                "08d8421547486b1e657e5c55a578874ec6f4748bc62f0d5cccddcc355780c13e"
            ),
        },
        {
            "row_domain": "questionnaire_occurrence_rows",
            "row_count": 2_388,
            "row_key_fields": ["questionnaire_occurrence_id"],
            "row_keyset_sha256": (
                "4a1c87c734d05b858805dcb887c59447a15030deac45dc06077dd79723ec0f48"
            ),
            "row_domain_sha256": (
                "ad5873fc0d47e3717ca005fa0640fde6ec9141e05f282accbc5e57fb90935fdc"
            ),
        },
        {
            "row_domain": "flow_branch_rows",
            "row_count": 690,
            "row_key_fields": ["flow_branch_id"],
            "row_keyset_sha256": (
                "43faca7533afa1f4c77d72ebbca5e7c8798d442792b5143670ca75b955b0f253"
            ),
            "row_domain_sha256": (
                "e8d84b554887e2273dd6638d3d4b2f51b71c5cc16decb00ea663c6838a69cd4f"
            ),
        },
    ),
    "ry1978_1992_pre_er_totals": (
        {
            "row_domain": "document_source_rows",
            "row_count": 29,
            "row_key_fields": ["source_document_id"],
            "row_keyset_sha256": (
                "a717514fb6f05a89f15898dd17aaf43b680fedf5d0986c86d0d338ac54ed9584"
            ),
            "row_domain_sha256": (
                "afb13017f83162b2083880c415f4101874c3c27486400b85ddb214c92dfcf638"
            ),
        },
        {
            "row_domain": "whole_document_locator_rows",
            "row_count": 29,
            "row_key_fields": ["locator_id"],
            "row_keyset_sha256": (
                "31eafd801f18091603c7bcd69498b15e2447c2b240853abacd5ca11619dbdb62"
            ),
            "row_domain_sha256": (
                "3e9b9997dc446795086d92ce9fbef5807459de06647d3212f3e9eb90a3ca3737"
            ),
        },
        {
            "row_domain": "questionnaire_page_rows",
            "row_count": 3_349,
            "row_key_fields": ["questionnaire_page_id"],
            "row_keyset_sha256": (
                "66d78dd57d1f52a7b92be8864000a4d76775ecfb6e9cbc2eb58349894f51fe82"
            ),
            "row_domain_sha256": (
                "952591537be87d7d10a16835d1f431446ee50a08ff6fc4a5b72367d1ff7a9f26"
            ),
        },
        {
            "row_domain": "questionnaire_occurrence_rows",
            "row_count": 43_818,
            "row_key_fields": ["questionnaire_occurrence_id"],
            "row_keyset_sha256": (
                "5929d60435a4dcd479e0679a482dca954f6a68ce924482a589fceff11dd12ae1"
            ),
            "row_domain_sha256": (
                "5e90b8c6a2ef859839ef43319ebbcbe2f3cde156fb836271665aad2b65c39f7e"
            ),
        },
        {
            "row_domain": "flow_branch_rows",
            "row_count": 16_063,
            "row_key_fields": ["flow_branch_id"],
            "row_keyset_sha256": (
                "f9f545a9a95791a7bc0b629ce51b81320e42fc132936e797fc05026bdce56871"
            ),
            "row_domain_sha256": (
                "413fdc5b196c3962d5ec59d776b0da987f2c4ae826160d39f089b4279f0c59bf"
            ),
        },
    ),
    "ry1993_2001_er_transition": (
        {
            "row_domain": "document_source_rows",
            "row_count": 12,
            "row_key_fields": ["source_document_id"],
            "row_keyset_sha256": (
                "a599e537eb420a48df9b17ad6bcaec385b794291a67f2cfa439dc585375cb7c6"
            ),
            "row_domain_sha256": (
                "a67605f012fa6791ad40069815905f9515eb965aeec03d441fef4c50916024d4"
            ),
        },
        {
            "row_domain": "whole_document_locator_rows",
            "row_count": 12,
            "row_key_fields": ["locator_id"],
            "row_keyset_sha256": (
                "605b7932fbecc3a943b6feaee7720ba9ba8120e464e672e8e44ffe4f60a89913"
            ),
            "row_domain_sha256": (
                "7f4876a8aa83119f3f2e3fd543547fdd3459dc179b2b83c1124ff01024a6dc44"
            ),
        },
        {
            "row_domain": "questionnaire_page_rows",
            "row_count": 1_622,
            "row_key_fields": ["questionnaire_page_id"],
            "row_keyset_sha256": (
                "e15763d21fb84e43747205912ec80dea1b21783d95314233b16493e77bf58d3e"
            ),
            "row_domain_sha256": (
                "5f74c89b9f2b4607928b9a515f5c5d45e4834de0faa56d472f751ca0275e0b35"
            ),
        },
        {
            "row_domain": "questionnaire_occurrence_rows",
            "row_count": 41_209,
            "row_key_fields": ["questionnaire_occurrence_id"],
            "row_keyset_sha256": (
                "c4a89af35317d3155127cf705a4dd527eabcb5330501a42132c1e9bdfb1e7baa"
            ),
            "row_domain_sha256": (
                "33f2b1e6253f162156febb809bca577baad82ca016385f52347b4184df9b9181"
            ),
        },
        {
            "row_domain": "flow_branch_rows",
            "row_count": 23_335,
            "row_key_fields": ["flow_branch_id"],
            "row_keyset_sha256": (
                "abc8d0f8e78d9cd714f7bc42e336f5eda9b812fd0a823d2981069ab7495c38a5"
            ),
            "row_domain_sha256": (
                "e49c060e610eab68907a103ee883cb039abfcf55bad87f7fde78af45c261b3c3"
            ),
        },
    ),
    "ry2002_2014_modern_bc_de": (
        {
            "row_domain": "document_source_rows",
            "row_count": 14,
            "row_key_fields": ["source_document_id"],
            "row_keyset_sha256": (
                "bb6301141126f399467e090e62f735c0c9544d368b5184e2e8347032e617daea"
            ),
            "row_domain_sha256": (
                "abe116a5d7e264295112af3d3e372474d16d598117377c3652f84d4047ff2346"
            ),
        },
        {
            "row_domain": "whole_document_locator_rows",
            "row_count": 14,
            "row_key_fields": ["locator_id"],
            "row_keyset_sha256": (
                "03121662d3d57e7e7c4c96c1a5013fbbb1a71019a0fc3f10152cfcb86d34f811"
            ),
            "row_domain_sha256": (
                "1b3956b4364004c6ffaff8d23baf352967b2172e4e6c21ef40691222e6020195"
            ),
        },
        {
            "row_domain": "questionnaire_page_rows",
            "row_count": 2_337,
            "row_key_fields": ["questionnaire_page_id"],
            "row_keyset_sha256": (
                "75bb688e2ca49423ff629962e02cdc2f511796d67183eb4af810b3745a5178e0"
            ),
            "row_domain_sha256": (
                "db282df59a5e628510b9c51b89868a9ca5cc8da31ca769553c15b6855aaf3d93"
            ),
        },
        {
            "row_domain": "questionnaire_occurrence_rows",
            "row_count": 18_838,
            "row_key_fields": ["questionnaire_occurrence_id"],
            "row_keyset_sha256": (
                "38e488e9bb7239447f948f4fcf7b062e4360f195d2b08900d77dbc2ef717c223"
            ),
            "row_domain_sha256": (
                "e0b06ff355c783fafe38da9d3f7987fd18bd9bb67b6fedb7cab9420af54c8533"
            ),
        },
        {
            "row_domain": "flow_branch_rows",
            "row_count": 3_435,
            "row_key_fields": ["flow_branch_id"],
            "row_keyset_sha256": (
                "507291365f87f1872734fe4332637709e4575cbc900e206aadb10a48e4084a01"
            ),
            "row_domain_sha256": (
                "f9913515fb815c5c2c446bf6cc12ad915eee980c7f25ee475d1df4578b9176c5"
            ),
        },
    ),
    "ry2015_2022_exclusion_lineage": (
        {
            "row_domain": "document_source_rows",
            "row_count": 4,
            "row_key_fields": ["source_document_id"],
            "row_keyset_sha256": (
                "8a1bfa22689591cd529248f6c022e820b3319eb8f156573428d6a6dab007794a"
            ),
            "row_domain_sha256": (
                "de40e2118e6283b2cfc46d61648328705c316f82d7a21d6acc76148c07bb49f3"
            ),
        },
        {
            "row_domain": "whole_document_locator_rows",
            "row_count": 4,
            "row_key_fields": ["locator_id"],
            "row_keyset_sha256": (
                "2c4c67cd991a506c8079602e88f4ec2adff901c5bbf1c0797f05ef4aae92448b"
            ),
            "row_domain_sha256": (
                "1c85659fb8cd7e1f6f574233a3517594575da6a2e4eaff6c89b2ef169793e3fd"
            ),
        },
        {
            "row_domain": "questionnaire_page_rows",
            "row_count": 1_632,
            "row_key_fields": ["questionnaire_page_id"],
            "row_keyset_sha256": (
                "00d2788ce6053ba66565f8bc187ab09c90a4d1ad48fcd5be248c49de5190405e"
            ),
            "row_domain_sha256": (
                "d04f5ccd2fa2b35c7cf5999cbc9387c14a7503b447939df6098bf518ac22af7d"
            ),
        },
        {
            "row_domain": "questionnaire_occurrence_rows",
            "row_count": 11_275,
            "row_key_fields": ["questionnaire_occurrence_id"],
            "row_keyset_sha256": (
                "2552840639be17dc8b3726e60725fad95b13bcbef8e6e85fd3693626a8f29bc9"
            ),
            "row_domain_sha256": (
                "53ca3dd0d7ee0c674593f702161c19dc09a31a195ae22a3a87bbb9fde1929750"
            ),
        },
        {
            "row_domain": "flow_branch_rows",
            "row_count": 3_768,
            "row_key_fields": ["flow_branch_id"],
            "row_keyset_sha256": (
                "0fa06946c587b32987296027e1b38b3f2a5a4a0f58c2d826f0601d700eed2fe8"
            ),
            "row_domain_sha256": (
                "d8a91219f07a6a5b9987f2c4e674164f9188a98994c574acd2ae638d26eba93d"
            ),
        },
    ),
}

PINNED_ANNOTATION_INPUT_SEALS = {
    "wave1968_ry1968_1974_early_totals": {
        "document_annotation_input_count": 16,
        "document_annotation_input_keyset_sha256": (
            "4445ff182c45f4fe5bf7624a9cf147b453873e22aac6ba422a9e2ce5cb380634"
        ),
        "document_annotation_input_domain_sha256": (
            "a2036a8115cf35b8ed53c38275b385cf0cd8638f336c04231d083d0fae0ce40c"
        ),
    },
    "ry1975_1977_spouse_concept_seam": {
        "document_annotation_input_count": 6,
        "document_annotation_input_keyset_sha256": (
            "c49b940390be4302579a8780cf76f6e77c5451770f160b8ebb84d13e1738ce9c"
        ),
        "document_annotation_input_domain_sha256": (
            "871a44fa503d4b5ae26f6fdda981d6b2acae758fe37e384b90c48faa8495f27e"
        ),
    },
    "ry1978_1992_pre_er_totals": {
        "document_annotation_input_count": 29,
        "document_annotation_input_keyset_sha256": (
            "12e6037fa8b1b781b04373471f32d32cbf3e43f20d609d39b255f95c4f34d066"
        ),
        "document_annotation_input_domain_sha256": (
            "09e6c2e65180e70237a90eac6e67a9e010cf6d79e0a53bb35994cc3b90a5b477"
        ),
    },
    "ry1993_2001_er_transition": {
        "document_annotation_input_count": 12,
        "document_annotation_input_keyset_sha256": (
            "946ef6461b4c67f62dce1d2a79dc64a35f45ab234ca90bdfb115815a2c7224f1"
        ),
        "document_annotation_input_domain_sha256": (
            "72003c0ef143f954dcf76d5fb7eaf312030d141d0101990d0af7c49ab3fb71fd"
        ),
    },
    "ry2002_2014_modern_bc_de": {
        "document_annotation_input_count": 14,
        "document_annotation_input_keyset_sha256": (
            "67c89573c269fb4ab3928ffa431dae12c8e3dfdfe834d8b68b7507a9f5c4a154"
        ),
        "document_annotation_input_domain_sha256": (
            "88b806bfeea8eb074a3b2f4194d709f09599a89cf10dfdb07d7ca6e77ab1b420"
        ),
    },
    "ry2015_2022_exclusion_lineage": {
        "document_annotation_input_count": 4,
        "document_annotation_input_keyset_sha256": (
            "6e87da87c8e42bbe45f22cc5198e86e232dd4ce1b417ae9c967c3b98c669ac85"
        ),
        "document_annotation_input_domain_sha256": (
            "3d3c53e996ccb6670de679e93da3349bea5a5a0790644d1d6bf02c77327fd27b"
        ),
    },
}

PAGE_KEYS = {
    "questionnaire_page_id",
    "source_document_id",
    "source_locator_id",
    "interview_wave",
    "page_number",
    "page_text_utf8_sha256",
    "questionnaire_occurrence_ids",
    "annotation_status",
}
LEGACY_OCCURRENCE_KEYS = {
    "questionnaire_occurrence_id",
    "source_document_id",
    "source_locator_id",
    "source_locator_sha256",
    "interview_wave",
    "page_number",
    "utf8_byte_start",
    "utf8_byte_end",
    "occurrence_index_on_page",
    "semantic_ordinal_at_span",
    "occurrence_kind",
    "matched_text",
    "matched_utf8_sha256",
    "flow_branch_paths",
}
LOCAL_OCCURRENCE_KEYS = (LEGACY_OCCURRENCE_KEYS - {"flow_branch_paths"}) | {
    "parent_flow_occurrence_ids"
}
LEGACY_FLOW_KEYS = {
    "flow_branch_id",
    "parent_flow_branch_id",
    "source_occurrence_id",
    "branch_path",
    "interview_wave",
    "source_locator_id",
    "page_number",
    "occurrence_index_on_page",
    "branch_label",
    "branch_label_sha256",
}
LOCAL_FLOW_KEYS = (
    LEGACY_FLOW_KEYS - {"parent_flow_branch_id", "branch_path"}
) | {
    "parent_flow_branch_ids",
    "parent_source_occurrence_ids",
}
LOCATOR_KEYS = {
    "locator_id",
    "source_document_id",
    "interview_wave",
    "filename",
    "location_type",
    "byte_start",
    "byte_end",
    "size_bytes",
    "full_file_sha256",
    "range_sha256",
    "pdf_page_domain",
}
ANNOTATION_INPUT_KEYS = {
    "document_source_position",
    "source_document_id",
    "annotation_path",
    "schema_version",
    "artifact_id",
    "byte_size",
    "raw_sha256",
    "content_sha256",
    "status",
}
COMMON_MODERN_AUTHORITY_DISPOSITION = {
    "authority_kind": "sealed_document_annotation_nonauthority",
    "sealed_document_count": 1,
    "whole_document_page_review_complete": True,
    "candidate_auto_promotion_permitted": False,
    "downstream_authority_inputs_read": False,
    "global_resolution_performed": False,
    "canonical_q5_artifact_emitted": False,
    "canonical_era_seal_emitted": False,
    "status": "pass",
}
DECLARED_SCOPE_MODERN_AUTHORITY_DISPOSITION = {
    **COMMON_MODERN_AUTHORITY_DISPOSITION,
    "annotated_page_domain_complete": True,
    "document_annotation_completeness": "declared_domain_complete",
}
SHARD_MODERN_AUTHORITY_DISPOSITION = {
    "authority_kind": "nonauthority_document_shard",
    "closes_class_a_residual": False,
    "closes_class_b_residual": False,
    "emits_era_seal": False,
    "emits_global_alias_catalog": False,
    "emits_global_node_ids": False,
    "emits_q5_artifact": False,
    "emits_r_q": False,
    "read_inventory_crosswalk_reader_or_legal_registry": False,
    "sealed_document_count": 1,
}
DECLARED_SCOPE_KEYS = {
    "scope_declaration_status",
    "reviewed_page_domain",
    "annotated_page_domain",
    "annotated_printed_domain",
    "domain_selection_rule",
    "local_classification_rules",
    "recorded_unresolved_interpretations",
    "remaining_work_ledger",
}
LEGACY_ANNOTATION_KEYS = {
    "adjudication_note_rows",
    "artifact_id",
    "authority_kind",
    "candidate_artifact_identity",
    "candidate_disposition_rows",
    "candidate_index_identity",
    "document_source_position",
    "document_source_row",
    "flow_branch_rows",
    "integrity",
    "local_anchor_classification_rows",
    "local_repeat_alias_evidence_rows",
    "nonauthority_statement",
    "output_adjudication_rows",
    "questionnaire_occurrence_rows",
    "questionnaire_page_rows",
    "schema_version",
    "seal",
    "source_replay_identity",
    "source_review_identity",
    "status",
    "whole_document_locator",
}
MODERN_ANNOTATION_KEYS = {
    "artifact_id",
    "authority_disposition",
    "candidate_artifact_identity",
    "candidate_disposition_rows",
    "candidate_index_identity",
    "correction_note_rows",
    "document_source_position",
    "document_source_row",
    "flow_branch_rows",
    "integrity",
    "local_anchor_classification_rows",
    "local_field_purpose_classification_rows",
    "local_repeat_or_alias_evidence_rows",
    "output_adjudication_rows",
    "questionnaire_occurrence_rows",
    "questionnaire_page_rows",
    "questionnaire_page_text_derivation",
    "schema_version",
    "seal",
    "source_replay_identity",
    "status",
    "whole_document_locator_rows",
}
BASE_FLAT_SEAL_KEYS = {
    "adjudication_note_count",
    "adjudication_note_domain_sha256",
    "authority_status",
    "candidate_adjudication_census_by_kind",
    "candidate_disposition_count",
    "candidate_disposition_domain_sha256",
    "candidate_domain_exact_cover",
    "empty_occurrence_page_count",
    "flow_branch_count",
    "flow_branch_domain_sha256",
    "global_ids_assigned",
    "local_anchor_classification_count",
    "local_anchor_classification_domain_sha256",
    "local_repeat_alias_evidence_count",
    "local_repeat_alias_evidence_domain_sha256",
    "output_adjudication_census_by_kind",
    "output_adjudication_count",
    "output_adjudication_domain_sha256",
    "output_domain_exact_cover",
    "page_review_count",
    "questionnaire_occurrence_count",
    "questionnaire_occurrence_counts_by_kind",
    "questionnaire_occurrence_domain_sha256",
    "questionnaire_occurrence_keyset_sha256",
    "questionnaire_page_count",
    "questionnaire_page_domain_sha256",
    "questionnaire_page_keyset_sha256",
    "whole_document_locator_count",
    "whole_document_locator_domain_sha256",
    "whole_document_review_complete",
}
DOCUMENT_5_FLAT_SEAL_KEYS = (
    BASE_FLAT_SEAL_KEYS
    - {
        "adjudication_note_count",
        "adjudication_note_domain_sha256",
        "whole_document_locator_count",
        "whole_document_locator_domain_sha256",
        "whole_document_review_complete",
    }
) | {"whole_document_locator_id"}
LOCAL_EDGE_FLAT_SEAL_KEYS = {
    "flow_edge_order",
    "flow_parent_representation",
    "serialized_path_product_count",
}
RASTER_FLAT_SEAL_KEYS = {
    "raster_only_branch_exception_count",
    "raster_only_branch_exception_domain_sha256",
    "raster_only_branch_exception_keyset_sha256",
    "raster_only_dependent_atom_consequence_count",
    "raster_only_dependent_atom_consequence_domain_sha256",
    "raster_only_dependent_atom_consequence_keyset_sha256",
    "raster_only_incompleteness_census_sha256",
    "raster_only_page_census_count",
    "raster_only_page_census_domain_sha256",
    "raster_only_page_census_keyset_sha256",
}
RASTER_SIDECAR_KEYS = {
    "schema_version",
    "authority_kind",
    "branch_exception_records",
    "branch_exception_count",
    "dependent_atom_consequence_records",
    "dependent_atom_count",
    "page_census_rows",
    "closed_gap_disposition",
    "closed_gap_reason",
    "document_completeness_claim",
    "later_assembly_consequence",
    "status",
}
RASTER_EXCEPTION_KEYS = {
    "approximate_raster_location",
    "authority_text_statement",
    "disposition",
    "exception_index_on_page",
    "interview_wave",
    "page_number",
    "page_text_utf8_sha256",
    "questionnaire_page_id",
    "source_document_id",
    "visible_label_description",
}
RASTER_DEPENDENT_KEYS = {
    "blocking_exception_keys",
    "emitted_questionnaire_occurrence_ids",
    "interview_wave",
    "matched_text",
    "matched_utf8_sha256",
    "occurrence_kind",
    "page_number",
    "page_text_utf8_sha256",
    "path_consequence",
    "questionnaire_page_id",
    "reason",
    "source_document_id",
    "utf8_byte_end",
    "utf8_byte_start",
}
RASTER_PAGE_CENSUS_KEYS = {
    "branch_exception_count",
    "branch_exception_keys",
    "dependent_atom_count",
    "dependent_atom_keys",
    "interview_wave",
    "page_number",
    "page_text_utf8_sha256",
    "questionnaire_page_id",
    "source_document_id",
}
NONAUTHORITY_STATEMENT = {
    "status": "nonauthority",
    "preparation_seal_only": True,
    "canonical_era_row_emitted": False,
    "exhaustive_raster_flow_claimed": False,
    "q5_emitted": False,
    "global_catalog_emitted": False,
    "global_alias_resolution_emitted": False,
    "r_q_emitted": False,
    "hierarchy_emitted": False,
    "slot_emitted": False,
    "inventory_emitted": False,
    "legal_registry_read": False,
    "legal_registry_emitted": False,
    "canonical_authority_substitution_permitted": False,
}
TOP_LEVEL_KEYS = {
    "schema_version",
    "artifact_id",
    "authority_kind",
    "source_replay_identity",
    "candidate_index_identity",
    "stage2_protocol_identity",
    "era_id",
    "era_order_position",
    "interview_waves",
    "interview_wave_count",
    "interview_wave_domain_sha256",
    "document_source_positions",
    "document_source_position_count",
    "document_source_position_domain_sha256",
    "document_annotation_input_rows",
    "document_annotation_input_count",
    "document_annotation_input_keyset_sha256",
    "document_annotation_input_domain_sha256",
    "row_domain_seal_rows",
    "row_domain_seal_count",
    "row_domain_seal_domain_sha256",
    "nonauthority_statement",
    "integrity",
    "status",
}
FORBIDDEN_EMISSION_KEYS = {
    "q5_rows",
    "era_rows",
    "global_catalog_rows",
    "global_alias_rows",
    "r_q_rows",
    "global_relationship_rows",
    "hierarchy_rows",
    "slot_rows",
    "inventory_rows",
    "legal_registry_rows",
    "document_source_rows",
    "whole_document_locator_rows",
    "questionnaire_page_rows",
    "questionnaire_occurrence_rows",
    "flow_branch_rows",
}
SOURCE_FORBIDDEN_EMISSION_KEYS = FORBIDDEN_EMISSION_KEYS - {
    "document_source_rows",
    "whole_document_locator_rows",
    "questionnaire_page_rows",
    "questionnaire_occurrence_rows",
    "flow_branch_rows",
}
FORBIDDEN_GLOBAL_ID_PREFIXES = (
    "psid-questionnaire-relationship:",
    "psid-job-slot:",
    "psid-component-slot:",
    "psid-node-alias:",
    "psid-questionnaire-slot:",
)


@dataclass(frozen=True)
class AnnotationInput:
    """One validated committed stage-2 annotation and its raw identity."""

    path: Path
    raw: bytes
    value: Mapping[str, Any]
    document: Mapping[str, Any]
    input_row: Mapping[str, Any]
    locators: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class EraInputs:
    """Source-led fixed inputs for one era."""

    replay: Mapping[str, Any]
    index: Mapping[str, Any]
    index_identity: Mapping[str, Any]
    protocol_identity: Mapping[str, Any]
    spec: Mapping[str, Any]
    annotations: tuple[AnnotationInput, ...]


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize under the section-10.1 compact ASCII terminal-LF law."""

    return source_tools.canonical_json_bytes(value)


def strict_parse_document(raw: bytes, label: str) -> Any:
    """Reject duplicate keys and all ambiguous JSON encodings."""

    return source_tools.strict_parse_document(raw, label)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256(canonical_json_bytes(value))


def _stream_array_digest(values: Sequence[Any]) -> str:
    """Hash a canonical JSON array without constructing its full bytes."""

    digest = hashlib.sha256()
    digest.update(b"[")
    for index, value in enumerate(values):
        if index:
            digest.update(b",")
        digest.update(canonical_json_bytes(value)[:-1])
    digest.update(b"]\n")
    return digest.hexdigest()


def _content_sha256(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return _canonical_digest(preimage)


def _expect_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{label} keyset drift")


def _valid_nonnegative_integer(value: Any) -> bool:
    return (
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
    )


def _valid_positive_integer(value: Any) -> bool:
    return _valid_nonnegative_integer(value) and value > 0


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _candidate_index_identity(
    value: Mapping[str, Any], raw: bytes
) -> dict[str, Any]:
    return {
        "path": str(stage1_candidates.INDEX_PATH.relative_to(ROOT)),
        "schema_version": value["schema_version"],
        "byte_size": len(raw),
        "raw_sha256": _sha256(raw),
        "content_sha256": value["integrity"]["content_sha256"],
    }


def _protocol_identity() -> dict[str, Any]:
    raw = PROTOCOL_PATH.read_bytes()
    if not raw or len(raw) >= MAX_COMMITTED_FILE_BYTES:
        raise ValueError("stage-2 protocol byte domain is unavailable")
    return {
        "path": str(PROTOCOL_PATH.relative_to(ROOT)),
        "byte_size": len(raw),
        "raw_sha256": _sha256(raw),
    }


def _load_candidate_index(
    replay: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = stage1_candidates.INDEX_PATH.read_bytes()
    if len(raw) >= MAX_COMMITTED_FILE_BYTES:
        raise ValueError("R_Q stage-1 candidate index exceeds the scale law")
    value = strict_parse_document(raw, "R_Q stage-1 candidate index")
    if not isinstance(value, dict):
        raise ValueError("R_Q stage-1 candidate index is not an object")
    if raw != canonical_json_bytes(value):
        raise ValueError("R_Q stage-1 candidate index is not canonical")
    stage1_candidates.validate_candidate_index(value, replay)
    return value, _candidate_index_identity(value, raw)


def _annotation_path(candidate_row: Mapping[str, Any], position: int) -> Path:
    name = Path(candidate_row["path"]).name
    suffix = "_candidates_v1.json"
    if not name.startswith(f"document_{position:03d}_") or not name.endswith(
        suffix
    ):
        raise ValueError("candidate path cannot identify its stage-2 seal")
    return ANNOTATION_ROOT / f"{name[:-len(suffix)]}_annotation_v1.json"


def _annotation_content_sha256(value: Mapping[str, Any]) -> str:
    if (
        value["schema_version"] == MODERN_SCHEMA
        and "document_local_annotation_scope" in value
    ):
        preimage = {
            key: member for key, member in value.items() if key != "integrity"
        }
    else:
        preimage = copy.deepcopy(value)
        preimage["integrity"]["content_sha256"] = "0" * 64
    return _canonical_digest(preimage)


def _normalized_locators(
    value: Mapping[str, Any], document: Mapping[str, Any]
) -> tuple[Mapping[str, Any], ...]:
    schema = value["schema_version"]
    if schema == MODERN_SCHEMA:
        if "whole_document_locator" in value:
            raise ValueError("modern annotation uses a singular locator")
        rows = value.get("whole_document_locator_rows")
    else:
        if "whole_document_locator_rows" in value:
            raise ValueError("legacy-family annotation uses plural locators")
        singular = value.get("whole_document_locator")
        rows = [singular] if isinstance(singular, Mapping) else None
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("document does not have exactly one whole locator")
    locator = rows[0]
    _expect_keys(locator, LOCATOR_KEYS, "whole-document locator")
    wave = document["interview_waves"][0]
    expected_id = "psid-whole-document:" + _canonical_digest(
        [
            document["source_document_id"],
            wave,
            document["sha256"],
            document["byte_size"],
        ]
    )
    if locator != {
        "locator_id": expected_id,
        "source_document_id": document["source_document_id"],
        "interview_wave": wave,
        "filename": Path(document["canonical_source_path"]).name,
        "location_type": "whole_document_exact_file_range",
        "byte_start": 0,
        "byte_end": document["byte_size"],
        "size_bytes": document["byte_size"],
        "full_file_sha256": document["sha256"],
        "range_sha256": document["sha256"],
        "pdf_page_domain": "all_pages_and_flow_branches",
    }:
        raise ValueError("whole-document locator equation drift")
    return (locator,)


def _verify_annotation_integrity(value: Mapping[str, Any]) -> None:
    integrity = value.get("integrity")
    if (
        not isinstance(integrity, Mapping)
        or set(integrity) != {"canonicalization", "content_sha256"}
        or integrity["canonicalization"] != CANONICALIZATION
        or integrity["content_sha256"] != _annotation_content_sha256(value)
    ):
        raise ValueError("stage-2 annotation content identity drift")


def _modern_annotation_family(value: Mapping[str, Any]) -> str:
    disposition = value.get("authority_disposition")
    has_scope = "document_local_annotation_scope" in value
    if disposition == COMMON_MODERN_AUTHORITY_DISPOSITION and not has_scope:
        return "complete"
    if (
        disposition == DECLARED_SCOPE_MODERN_AUTHORITY_DISPOSITION
        and has_scope
    ):
        return "declared_scope"
    if disposition == SHARD_MODERN_AUTHORITY_DISPOSITION and not has_scope:
        return "shard"
    raise ValueError("modern annotation authority family drift")


def _expected_annotation_keys(
    value: Mapping[str, Any], position: int
) -> set[str]:
    """Return one of the seven sealed stage-2 outer schemas."""

    schema = value.get("schema_version")
    if schema == MODERN_SCHEMA:
        expected = set(MODERN_ANNOTATION_KEYS)
        if _modern_annotation_family(value) == "declared_scope":
            expected.add("document_local_annotation_scope")
        return expected
    if schema not in {LEGACY_SCHEMA, LOCAL_EDGE_SCHEMA}:
        raise ValueError("stage-2 annotation schema is not sealed")
    expected = set(LEGACY_ANNOTATION_KEYS)
    if position == 5:
        expected.remove("adjudication_note_rows")
    if position in EXPECTED_RASTER_SIDECAR_POSITIONS:
        expected.add("raster_only_incompleteness_census")
    return expected


def _contains_source_forbidden_emission(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in SOURCE_FORBIDDEN_EMISSION_KEYS
            or _contains_source_forbidden_emission(member)
            for key, member in value.items()
        )
    if isinstance(value, list):
        return any(
            _contains_source_forbidden_emission(member) for member in value
        )
    return isinstance(value, str) and value.startswith(
        FORBIDDEN_GLOBAL_ID_PREFIXES
    )


def _expected_embedded_identity(
    expected: Mapping[str, Any], value: Mapping[str, Any]
) -> dict[str, Any]:
    if value["schema_version"] != MODERN_SCHEMA:
        return dict(expected)
    if _modern_annotation_family(value) == "shard":
        return {
            key: expected[key]
            for key in ("path", "raw_sha256", "content_sha256")
        }
    return {**expected, "artifact_id": expected["schema_version"]}


def _verify_annotation_nonauthority(value: Mapping[str, Any]) -> None:
    if value["schema_version"] == MODERN_SCHEMA:
        family = _modern_annotation_family(value)
        expected_status = (
            "pass_sealed_declared_domain_nonauthority_annotation"
            if family == "declared_scope"
            else "pass_sealed_complete_nonauthority_annotation"
        )
        if value["status"] != expected_status:
            raise ValueError("modern annotation nonauthority status drift")
        return
    statement = value.get("nonauthority_statement")
    _expect_keys(
        statement,
        {
            "status",
            "one_document_only",
            "q5_emitted",
            "era_seal_emitted",
            "global_catalog_emitted",
            "global_alias_resolution_emitted",
            "r_q_emitted",
            "hierarchy_emitted",
            "slot_or_inventory_emitted",
            "legal_registry_read",
        },
        "legacy-family nonauthority statement",
    )
    if (
        value["status"] != "sealed_complete_nonauthority_document_annotation"
        or value["authority_kind"]
        != "document_local_source_annotation_nonauthority"
        or statement.get("status") != "nonauthority"
        or statement.get("one_document_only") is not True
        or statement.get("q5_emitted") is not False
        or statement.get("era_seal_emitted") is not False
        or statement.get("global_catalog_emitted") is not False
        or statement.get("global_alias_resolution_emitted") is not False
        or statement.get("r_q_emitted") is not False
        or statement.get("hierarchy_emitted") is not False
        or statement.get("slot_or_inventory_emitted") is not False
        or statement.get("legal_registry_read") is not False
    ):
        raise ValueError("legacy-family annotation nonauthority drift")


def _verify_annotation_seal(
    value: Mapping[str, Any], locators: Sequence[Mapping[str, Any]]
) -> None:
    rows_by_domain = {
        "whole_document_locator_rows": list(locators),
        "questionnaire_page_rows": value["questionnaire_page_rows"],
        "questionnaire_occurrence_rows": value[
            "questionnaire_occurrence_rows"
        ],
        "flow_branch_rows": value["flow_branch_rows"],
    }
    keys_by_domain = {
        "whole_document_locator_rows": "locator_id",
        "questionnaire_page_rows": "questionnaire_page_id",
        "questionnaire_occurrence_rows": "questionnaire_occurrence_id",
        "flow_branch_rows": "flow_branch_id",
    }
    seal = value.get("seal")
    if not isinstance(seal, Mapping):
        raise ValueError("stage-2 annotation seal is absent")
    if value["schema_version"] == MODERN_SCHEMA:
        seal_rows = seal.get("row_domain_seal_rows")
        if (
            set(seal)
            != {
                "row_domain_seal_rows",
                "row_domain_seal_count",
                "row_domain_seal_domain_sha256",
                "seal_status",
            }
            or not isinstance(seal_rows, list)
            or seal["row_domain_seal_count"] != len(seal_rows)
            or seal["row_domain_seal_domain_sha256"]
            != _stream_array_digest(seal_rows)
            or seal["seal_status"] != "pass_complete"
            or any(
                not isinstance(row, Mapping)
                or set(row) != ROW_DOMAIN_SEAL_KEYS
                for row in seal_rows
            )
        ):
            raise ValueError("modern stage-2 row seals are not an array")
        seals_by_domain = {
            row.get("row_domain"): row
            for row in seal_rows
            if isinstance(row, Mapping)
        }
        if len(seals_by_domain) != len(seal_rows):
            raise ValueError("modern stage-2 row seal domain is duplicated")
        shard_keysets = _modern_annotation_family(value) == "shard"
        for domain, rows in rows_by_domain.items():
            row_seal = seals_by_domain.get(domain)
            key = keys_by_domain[domain]
            keyset = (
                [[row[key]] for row in rows]
                if shard_keysets
                else [row[key] for row in rows]
            )
            if (
                not isinstance(row_seal, Mapping)
                or set(row_seal) != ROW_DOMAIN_SEAL_KEYS
                or row_seal["row_count"] != len(rows)
                or row_seal["row_key_fields"] != [key]
                or row_seal["row_keyset_sha256"]
                != _stream_array_digest(keyset)
                or row_seal["row_domain_sha256"] != _stream_array_digest(rows)
            ):
                raise ValueError(f"modern {domain} seal drift")
        return

    position = value["document_source_position"]
    expected_flat_keys = (
        set(DOCUMENT_5_FLAT_SEAL_KEYS)
        if position == 5
        else set(BASE_FLAT_SEAL_KEYS)
    )
    if value["schema_version"] == LOCAL_EDGE_SCHEMA:
        expected_flat_keys.update(LOCAL_EDGE_FLAT_SEAL_KEYS)
    if position in EXPECTED_RASTER_SIDECAR_POSITIONS:
        expected_flat_keys.update(RASTER_FLAT_SEAL_KEYS)
    _expect_keys(seal, expected_flat_keys, "flat stage-2 seal")
    if (
        seal["authority_status"] != "nonauthority"
        or seal["global_ids_assigned"] is not False
    ):
        raise ValueError("flat stage-2 seal authority drift")

    flat_specs = {
        "whole_document_locator_rows": (
            "whole_document_locator_count",
            None,
            "whole_document_locator_domain_sha256",
        ),
        "questionnaire_page_rows": (
            "questionnaire_page_count",
            "questionnaire_page_keyset_sha256",
            "questionnaire_page_domain_sha256",
        ),
        "questionnaire_occurrence_rows": (
            "questionnaire_occurrence_count",
            "questionnaire_occurrence_keyset_sha256",
            "questionnaire_occurrence_domain_sha256",
        ),
        "flow_branch_rows": (
            "flow_branch_count",
            None,
            "flow_branch_domain_sha256",
        ),
    }
    for domain, (count_key, keyset_key, domain_key) in flat_specs.items():
        rows = rows_by_domain[domain]
        key = keys_by_domain[domain]
        if (
            domain == "whole_document_locator_rows"
            and "whole_document_locator_id" in seal
        ):
            if (
                len(rows) != 1
                or seal["whole_document_locator_id"] != rows[0]["locator_id"]
            ):
                raise ValueError("flat whole-document locator ID drift")
            continue
        if (
            seal.get(count_key) != len(rows)
            or seal.get(domain_key) != _stream_array_digest(rows)
            or (
                keyset_key is not None
                and seal.get(keyset_key)
                != _stream_array_digest([row[key] for row in rows])
            )
        ):
            raise ValueError(f"flat {domain} seal drift")


def _occurrence_locator_sha256(
    document: Mapping[str, Any], row: Mapping[str, Any]
) -> str:
    return _canonical_digest(
        [
            document["source_document_id"],
            document["canonical_source_path"],
            "questionnaire_page_utf8_span",
            [
                document["interview_waves"][0],
                row["page_number"],
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                row["occurrence_index_on_page"],
                row["semantic_ordinal_at_span"],
                row["occurrence_kind"],
            ],
        ]
    )


def _verify_occurrence_source_order(
    rows: Sequence[Mapping[str, Any]],
) -> None:
    """Enforce full semantic order and the independent sparse-index order."""

    prior_coordinate: tuple[int, int, int, int, int] | None = None
    prior_sparse_index: tuple[int, int] | None = None
    for row in rows:
        coordinate = (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            stage1_candidates.KIND_ORDER[row["occurrence_kind"]],
            row["semantic_ordinal_at_span"],
        )
        sparse_index = (
            row["page_number"],
            row["occurrence_index_on_page"],
        )
        if (
            prior_coordinate is not None and coordinate <= prior_coordinate
        ) or (
            prior_sparse_index is not None
            and sparse_index <= prior_sparse_index
        ):
            raise ValueError("questionnaire occurrence source order drift")
        prior_coordinate = coordinate
        prior_sparse_index = sparse_index


def _verify_occurrences(
    value: Mapping[str, Any],
    document: Mapping[str, Any],
    locator_id: str,
) -> dict[str, Mapping[str, Any]]:
    local_edges = value["schema_version"] == LOCAL_EDGE_SCHEMA
    expected_keys = (
        LOCAL_OCCURRENCE_KEYS if local_edges else LEGACY_OCCURRENCE_KEYS
    )
    rows = value["questionnaire_occurrence_rows"]
    if not isinstance(rows, list):
        raise ValueError("questionnaire occurrences are not an array")
    occurrence_by_id: dict[str, Mapping[str, Any]] = {}
    coordinates: set[tuple[Any, ...]] = set()
    wave = document["interview_waves"][0]
    for row in rows:
        _expect_keys(row, expected_keys, "questionnaire occurrence")
        row_id = row["questionnaire_occurrence_id"]
        coordinate = (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            stage1_candidates.KIND_ORDER.get(row["occurrence_kind"]),
            row["semantic_ordinal_at_span"],
        )
        parent_value = (
            row["parent_flow_occurrence_ids"]
            if local_edges
            else row["flow_branch_paths"]
        )
        remaining = [
            document["source_document_id"],
            locator_id,
            row["source_locator_sha256"],
            wave,
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_index_on_page"],
            row["semantic_ordinal_at_span"],
            row["occurrence_kind"],
            row["matched_text"],
            row["matched_utf8_sha256"],
            parent_value,
        ]
        if (
            not isinstance(row_id, str)
            or not row_id.startswith("psid-questionnaire-occurrence:")
            or row_id in occurrence_by_id
            or coordinate in coordinates
            or row["source_document_id"] != document["source_document_id"]
            or row["source_locator_id"] != locator_id
            or row["interview_wave"] != wave
            or not _valid_positive_integer(row["page_number"])
            or not _valid_nonnegative_integer(row["utf8_byte_start"])
            or not _valid_positive_integer(row["utf8_byte_end"])
            or row["utf8_byte_start"] >= row["utf8_byte_end"]
            or not _valid_nonnegative_integer(row["occurrence_index_on_page"])
            or not _valid_nonnegative_integer(row["semantic_ordinal_at_span"])
            or row["occurrence_kind"] not in stage1_candidates.OCCURRENCE_KINDS
            or not isinstance(row["matched_text"], str)
            or not row["matched_text"]
            or row["matched_utf8_sha256"]
            != _sha256(row["matched_text"].encode("utf-8"))
            or row["source_locator_sha256"]
            != _occurrence_locator_sha256(document, row)
            or row_id
            != "psid-questionnaire-occurrence:" + _canonical_digest(remaining)
        ):
            raise ValueError(
                "questionnaire occurrence equation or order drift"
            )
        if local_edges:
            parents = row["parent_flow_occurrence_ids"]
            if (
                not isinstance(parents, list)
                or len(parents) != len(set(parents))
                or row["semantic_ordinal_at_span"] != 0
            ):
                raise ValueError("local occurrence parent relation drift")
        else:
            paths = row["flow_branch_paths"]
            if (
                not isinstance(paths, list)
                or not paths
                or any(
                    not isinstance(path, list) or not path for path in paths
                )
                or paths != sorted(paths)
                or len({tuple(path) for path in paths}) != len(paths)
            ):
                raise ValueError("legacy occurrence path domain drift")
        occurrence_by_id[row_id] = row
        coordinates.add(coordinate)
    _verify_occurrence_source_order(rows)
    return occurrence_by_id


def _declared_scope_annotated_pages(
    value: Mapping[str, Any], replay_pages: Sequence[Mapping[str, Any]]
) -> set[int]:
    scope = value.get("document_local_annotation_scope")
    _expect_keys(scope, DECLARED_SCOPE_KEYS, "declared annotation scope")
    position = value["document_source_position"]
    if _canonical_digest(
        scope
    ) != PINNED_DECLARED_SCOPE_SHA256_BY_POSITION.get(position):
        raise ValueError("declared annotation scope identity drift")
    reviewed_pages = [row["page_number"] for row in replay_pages]
    annotated_pages = scope["annotated_page_domain"]
    unresolved = scope["recorded_unresolved_interpretations"]
    ledger = scope["remaining_work_ledger"]
    if (
        scope["scope_declaration_status"]
        != "additive_lane_local_declaration_compatible_with_v1_row_schemas"
        or not isinstance(scope["reviewed_page_domain"], list)
        or any(
            not _valid_positive_integer(page)
            for page in scope["reviewed_page_domain"]
        )
        or scope["reviewed_page_domain"] != reviewed_pages
        or not isinstance(annotated_pages, list)
        or not annotated_pages
        or any(not _valid_positive_integer(page) for page in annotated_pages)
        or annotated_pages != sorted(set(annotated_pages))
        or not set(annotated_pages) <= set(reviewed_pages)
        or not isinstance(scope["annotated_printed_domain"], list)
        or not scope["annotated_printed_domain"]
        or any(
            not isinstance(member, str) or not member
            for member in scope["annotated_printed_domain"]
        )
        or not isinstance(scope["domain_selection_rule"], str)
        or not scope["domain_selection_rule"]
        or not isinstance(scope["local_classification_rules"], list)
        or not scope["local_classification_rules"]
        or any(
            not isinstance(member, str) or not member
            for member in scope["local_classification_rules"]
        )
        or not isinstance(unresolved, list)
        or any(
            not isinstance(entry, Mapping)
            or set(entry)
            != {
                "interpretation_id",
                "printed_evidence",
                "statement",
                "disposition",
            }
            or not isinstance(entry["interpretation_id"], str)
            or not entry["interpretation_id"]
            or not isinstance(entry["statement"], str)
            or not entry["statement"]
            or entry["disposition"] != "recorded_for_review_not_annotated"
            or not isinstance(entry["printed_evidence"], list)
            or not entry["printed_evidence"]
            or any(
                not isinstance(evidence, Mapping)
                or set(evidence)
                != {"page_number", "utf8_byte_start", "utf8_byte_end"}
                or not _valid_positive_integer(evidence["page_number"])
                or evidence["page_number"] not in reviewed_pages
                or not _valid_nonnegative_integer(evidence["utf8_byte_start"])
                or not _valid_positive_integer(evidence["utf8_byte_end"])
                or evidence["utf8_byte_start"] >= evidence["utf8_byte_end"]
                for evidence in entry["printed_evidence"]
            )
            for entry in unresolved
        )
        or not isinstance(ledger, list)
        or not ledger
        or any(
            not isinstance(entry, Mapping)
            or set(entry) != {"page_domain", "printed_domain", "reason_code"}
            or not isinstance(entry["page_domain"], list)
            or not entry["page_domain"]
            or any(
                not _valid_positive_integer(page)
                for page in entry["page_domain"]
            )
            or entry["page_domain"] != sorted(set(entry["page_domain"]))
            or not isinstance(entry["printed_domain"], str)
            or not entry["printed_domain"]
            or not isinstance(entry["reason_code"], str)
            or not entry["reason_code"]
            for entry in ledger
        )
    ):
        raise ValueError("declared annotation page domain drift")
    ledger_pages = [page for entry in ledger for page in entry["page_domain"]]
    if sorted(ledger_pages) != reviewed_pages:
        raise ValueError(
            "declared remaining-work ledger is not an exact cover"
        )
    return set(annotated_pages)


def _verify_pages(
    value: Mapping[str, Any],
    document: Mapping[str, Any],
    locator_id: str,
    replay_pages: Sequence[Mapping[str, Any]],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    rows = value["questionnaire_page_rows"]
    if not isinstance(rows, list) or len(rows) != len(replay_pages):
        raise ValueError("stage-2 page count differs from source replay")
    expected_page_ids = [row["questionnaire_page_id"] for row in replay_pages]
    actual_page_ids = [row.get("questionnaire_page_id") for row in rows]
    if actual_page_ids != expected_page_ids:
        raise ValueError("stage-2 page keyset or order differs from replay")
    if (
        value["schema_version"] == MODERN_SCHEMA
        and _modern_annotation_family(value) == "declared_scope"
    ):
        annotated_pages = _declared_scope_annotated_pages(value, replay_pages)
        if any(
            occurrence["page_number"] not in annotated_pages
            for occurrence in occurrence_by_id.values()
        ):
            raise ValueError(
                "occurrence lies outside the declared page domain"
            )
    else:
        annotated_pages = {row["page_number"] for row in replay_pages}
    seen_occurrences: list[str] = []
    for row, replay_row in zip(rows, replay_pages, strict=True):
        _expect_keys(row, PAGE_KEYS, "questionnaire page")
        expected_projection = {
            key: replay_row[key]
            for key in (
                "questionnaire_page_id",
                "source_document_id",
                "interview_wave",
                "page_number",
                "page_text_utf8_sha256",
            )
        }
        if (
            any(
                row[key] != member
                for key, member in expected_projection.items()
            )
            or row["source_locator_id"] != locator_id
            or row["annotation_status"]
            != (
                "complete"
                if row["page_number"] in annotated_pages
                else "declared_domain_deferred"
            )
            or not isinstance(row["questionnaire_occurrence_ids"], list)
            or len(row["questionnaire_occurrence_ids"])
            != len(set(row["questionnaire_occurrence_ids"]))
        ):
            raise ValueError("stage-2 page projection drift")
        expected_occurrence_ids = [
            occurrence_id
            for occurrence_id, occurrence in occurrence_by_id.items()
            if occurrence["page_number"] == row["page_number"]
        ]
        if row["questionnaire_occurrence_ids"] != expected_occurrence_ids:
            raise ValueError("page occurrence reverse projection drift")
        seen_occurrences.extend(row["questionnaire_occurrence_ids"])
    if seen_occurrences != list(occurrence_by_id):
        raise ValueError("page rows do not exactly cover occurrences")


def _verify_raster_sidecar(
    value: Mapping[str, Any],
    document: Mapping[str, Any],
    position: int,
    replay_pages: Sequence[Mapping[str, Any]],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    """Validate the four Amendment-1 raster-only census sidecars."""

    if position not in EXPECTED_RASTER_SIDECAR_POSITIONS:
        if "raster_only_incompleteness_census" in value:
            raise ValueError("unexpected raster-only sidecar")
        return
    sidecar = value.get("raster_only_incompleteness_census")
    _expect_keys(sidecar, RASTER_SIDECAR_KEYS, "raster-only sidecar")
    exceptions = sidecar["branch_exception_records"]
    dependents = sidecar["dependent_atom_consequence_records"]
    page_census = sidecar["page_census_rows"]
    if (
        sidecar["schema_version"]
        != "rq_stage2_raster_only_incompleteness_census_nonauthority.v1"
        or sidecar["authority_kind"] != "sealed_nonauthority_sidecar"
        or sidecar["closed_gap_disposition"] != "CLOSED GAP"
        or sidecar["closed_gap_reason"] != "raster_visible_text_absent"
        or sidecar["document_completeness_claim"]
        != (
            "complete-under-extraction-authority with "
            f"{sidecar['branch_exception_count']} raster-only exceptions"
        )
        or sidecar["later_assembly_consequence"]
        != (
            "fail_or_withhold_exhaustive_flow_outputs_without_global_gap_"
            "rows_nodes_or_ids"
        )
        or sidecar["status"] != "complete"
        or not isinstance(exceptions, list)
        or not isinstance(dependents, list)
        or not isinstance(page_census, list)
        or sidecar["branch_exception_count"] != len(exceptions)
        or sidecar["dependent_atom_count"] != len(dependents)
    ):
        raise ValueError("raster-only sidecar declaration drift")

    wave = document["interview_waves"][0]
    replay_by_page = {row["page_number"]: row for row in replay_pages}
    exception_by_key: dict[tuple[str, int], Mapping[str, Any]] = {}
    prior_exception_order: tuple[int, int] | None = None
    for row in exceptions:
        _expect_keys(row, RASTER_EXCEPTION_KEYS, "raster branch exception")
        page_number = row["page_number"]
        exception_index = row["exception_index_on_page"]
        replay_page = (
            replay_by_page.get(page_number)
            if _valid_positive_integer(page_number)
            else None
        )
        key = (row["questionnaire_page_id"], exception_index)
        order = (page_number, exception_index)
        if (
            replay_page is None
            or not _valid_nonnegative_integer(exception_index)
            or key in exception_by_key
            or (
                prior_exception_order is not None
                and order <= prior_exception_order
            )
            or row["source_document_id"] != document["source_document_id"]
            or row["interview_wave"] != wave
            or row["questionnaire_page_id"]
            != replay_page["questionnaire_page_id"]
            or row["page_text_utf8_sha256"]
            != replay_page["page_text_utf8_sha256"]
            or row["disposition"] != "raster_visible_text_absent"
            or row["authority_text_statement"]
            != "no_label_level_span_or_hash_emitted"
            or not isinstance(row["approximate_raster_location"], str)
            or not row["approximate_raster_location"]
            or not isinstance(row["visible_label_description"], str)
            or not row["visible_label_description"]
        ):
            raise ValueError("raster branch exception equation drift")
        exception_by_key[key] = row
        prior_exception_order = order

    dependent_by_key: dict[tuple[str, int, int, str], Mapping[str, Any]] = {}
    prior_dependent_order: tuple[int, int, int, int] | None = None
    for row in dependents:
        _expect_keys(
            row, RASTER_DEPENDENT_KEYS, "raster dependent consequence"
        )
        page_number = row["page_number"]
        replay_page = (
            replay_by_page.get(page_number)
            if _valid_positive_integer(page_number)
            else None
        )
        kind = row["occurrence_kind"]
        kind_order = stage1_candidates.KIND_ORDER.get(kind)
        key = (
            row["questionnaire_page_id"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            kind,
        )
        order = (
            page_number,
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            kind_order if kind_order is not None else -1,
        )
        blockers = row["blocking_exception_keys"]
        emitted_ids = row["emitted_questionnaire_occurrence_ids"]
        blockers_valid = isinstance(blockers, list) and bool(blockers)
        if blockers_valid:
            blockers_valid = (
                all(
                    isinstance(member, list)
                    and len(member) == 2
                    and isinstance(member[0], str)
                    and _valid_nonnegative_integer(member[1])
                    for member in blockers
                )
                and len({tuple(member) for member in blockers})
                == len(blockers)
                and all(
                    tuple(member) in exception_by_key for member in blockers
                )
            )
        emitted_valid = (
            isinstance(emitted_ids, list)
            and len(emitted_ids) == len(set(emitted_ids))
            and all(
                isinstance(occurrence_id, str)
                and occurrence_id in occurrence_by_id
                for occurrence_id in emitted_ids
            )
        )
        expected_consequence = (
            "emitted_with_all_resolving_extraction_authority_paths"
            if emitted_ids
            else "withheld_no_resolving_extraction_authority_path"
        )
        if (
            replay_page is None
            or kind_order is None
            or not _valid_nonnegative_integer(row["utf8_byte_start"])
            or not _valid_positive_integer(row["utf8_byte_end"])
            or row["utf8_byte_start"] >= row["utf8_byte_end"]
            or key in dependent_by_key
            or (
                prior_dependent_order is not None
                and order <= prior_dependent_order
            )
            or not blockers_valid
            or not emitted_valid
            or row["source_document_id"] != document["source_document_id"]
            or row["interview_wave"] != wave
            or row["questionnaire_page_id"]
            != replay_page["questionnaire_page_id"]
            or row["page_text_utf8_sha256"]
            != replay_page["page_text_utf8_sha256"]
            or not isinstance(row["matched_text"], str)
            or not row["matched_text"]
            or row["matched_utf8_sha256"]
            != _sha256(row["matched_text"].encode("utf-8"))
            or row["reason"] != "raster_visible_text_absent"
            or row["path_consequence"] != expected_consequence
        ):
            raise ValueError("raster dependent consequence equation drift")
        for occurrence_id in emitted_ids:
            occurrence = occurrence_by_id[occurrence_id]
            if any(
                occurrence[field] != row[field]
                for field in (
                    "source_document_id",
                    "interview_wave",
                    "page_number",
                    "utf8_byte_start",
                    "utf8_byte_end",
                    "occurrence_kind",
                    "matched_text",
                    "matched_utf8_sha256",
                )
            ):
                raise ValueError("raster emitted occurrence projection drift")
        dependent_by_key[key] = row
        prior_dependent_order = order

    if len(page_census) != len(replay_pages):
        raise ValueError("raster page census does not cover the document")
    for row, replay_page in zip(page_census, replay_pages, strict=True):
        _expect_keys(row, RASTER_PAGE_CENSUS_KEYS, "raster page census")
        page_number = replay_page["page_number"]
        exception_keys = [
            [exception["questionnaire_page_id"], exception_index]
            for (
                _page_id,
                exception_index,
            ), exception in exception_by_key.items()
            if exception["page_number"] == page_number
        ]
        dependent_keys = [
            [page_id, byte_start, byte_end, kind]
            for (
                page_id,
                byte_start,
                byte_end,
                kind,
            ), dependent in dependent_by_key.items()
            if dependent["page_number"] == page_number
        ]
        if (
            row["source_document_id"] != document["source_document_id"]
            or row["interview_wave"] != wave
            or row["page_number"] != page_number
            or row["questionnaire_page_id"]
            != replay_page["questionnaire_page_id"]
            or row["page_text_utf8_sha256"]
            != replay_page["page_text_utf8_sha256"]
            or row["branch_exception_count"] != len(exception_keys)
            or row["branch_exception_keys"] != exception_keys
            or row["dependent_atom_count"] != len(dependent_keys)
            or row["dependent_atom_keys"] != dependent_keys
        ):
            raise ValueError("raster page census projection drift")

    exception_keyset = [
        [row["questionnaire_page_id"], row["exception_index_on_page"]]
        for row in exceptions
    ]
    dependent_keyset = [
        [
            row["questionnaire_page_id"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
        ]
        for row in dependents
    ]
    page_keyset = [[row["questionnaire_page_id"]] for row in page_census]
    seal = value["seal"]
    expected_seal = {
        "raster_only_branch_exception_count": len(exceptions),
        "raster_only_branch_exception_keyset_sha256": _stream_array_digest(
            exception_keyset
        ),
        "raster_only_branch_exception_domain_sha256": _stream_array_digest(
            exceptions
        ),
        "raster_only_dependent_atom_consequence_count": len(dependents),
        "raster_only_dependent_atom_consequence_keyset_sha256": (
            _stream_array_digest(dependent_keyset)
        ),
        "raster_only_dependent_atom_consequence_domain_sha256": (
            _stream_array_digest(dependents)
        ),
        "raster_only_page_census_count": len(page_census),
        "raster_only_page_census_keyset_sha256": _stream_array_digest(
            page_keyset
        ),
        "raster_only_page_census_domain_sha256": _stream_array_digest(
            page_census
        ),
        "raster_only_incompleteness_census_sha256": _canonical_digest(sidecar),
    }
    if any(seal.get(key) != member for key, member in expected_seal.items()):
        raise ValueError("raster-only sidecar seal drift")
    if expected_seal["raster_only_incompleteness_census_sha256"] != (
        PINNED_RASTER_SIDECAR_SHA256_BY_POSITION[position]
    ):
        raise ValueError("raster-only sidecar pinned identity drift")


def _verify_legacy_flow(
    rows: Sequence[Mapping[str, Any]],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    branch_by_id: dict[str, Mapping[str, Any]] = {}
    occurrence_position = {
        occurrence_id: position
        for position, occurrence_id in enumerate(occurrence_by_id)
    }
    prior_source_position = -1
    for row in rows:
        _expect_keys(row, LEGACY_FLOW_KEYS, "legacy flow branch")
        source = occurrence_by_id.get(row["source_occurrence_id"])
        expected_id = "questionnaire-flow:" + _canonical_digest(
            [
                row["parent_flow_branch_id"],
                row["interview_wave"],
                row["source_occurrence_id"],
            ]
        )
        source_position = occurrence_position.get(
            row["source_occurrence_id"], -1
        )
        parent_id = row["parent_flow_branch_id"]
        parent_path = (
            [FLOW_ROOT]
            if parent_id == FLOW_ROOT
            else branch_by_id.get(parent_id, {}).get("branch_path")
        )
        if (
            source is None
            or source["occurrence_kind"] != "flow_branch_label"
            or source_position <= prior_source_position
            or row["flow_branch_id"] in branch_by_id
            or row["flow_branch_id"] != expected_id
            or parent_path is None
            or row["branch_path"] != [*parent_path, row["flow_branch_id"]]
            or source["flow_branch_paths"] != [parent_path]
            or row["interview_wave"] != source["interview_wave"]
            or row["source_locator_id"] != source["source_locator_id"]
            or row["page_number"] != source["page_number"]
            or row["occurrence_index_on_page"]
            != source["occurrence_index_on_page"]
            or row["branch_label"] != source["matched_text"]
            or row["branch_label_sha256"] != source["matched_utf8_sha256"]
        ):
            raise ValueError("legacy flow branch equation or order drift")
        branch_by_id[row["flow_branch_id"]] = row
        prior_source_position = source_position
    label_ids = [
        occurrence_id
        for occurrence_id, row in occurrence_by_id.items()
        if row["occurrence_kind"] == "flow_branch_label"
    ]
    if [row["source_occurrence_id"] for row in rows] != label_ids:
        raise ValueError("legacy flow rows do not exactly cover labels")
    for occurrence in occurrence_by_id.values():
        for path in occurrence["flow_branch_paths"]:
            if path[0] != FLOW_ROOT:
                raise ValueError("legacy path does not begin at root")
            for parent, child in zip(path, path[1:], strict=False):
                branch = branch_by_id.get(child)
                if branch is None or branch["parent_flow_branch_id"] != parent:
                    raise ValueError("legacy path contains an unresolved edge")


def _verify_local_occurrence_parent_order(
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
    branch_by_occurrence: Mapping[str, Mapping[str, Any]],
    flow_edge_order: str,
) -> None:
    occurrence_position = {
        occurrence_id: position
        for position, occurrence_id in enumerate(occurrence_by_id)
    }
    for occurrence_id, occurrence in occurrence_by_id.items():
        parents = occurrence["parent_flow_occurrence_ids"]
        if any(parent_id not in branch_by_occurrence for parent_id in parents):
            raise ValueError("local occurrence has an unresolved flow parent")
        if parents != sorted(parents, key=occurrence_position.__getitem__):
            raise ValueError("local occurrence parent source order drift")
        if flow_edge_order == (
            "direct_parents_precede_children_in_source_order"
        ) and any(
            occurrence_position[parent_id]
            >= occurrence_position[occurrence_id]
            for parent_id in parents
        ):
            raise ValueError("local occurrence has a later direct parent")


def _verify_local_flow(
    rows: Sequence[Mapping[str, Any]],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
    flow_edge_order: str,
) -> None:
    branch_by_id: dict[str, Mapping[str, Any]] = {}
    branch_by_occurrence: dict[str, Mapping[str, Any]] = {}
    occurrence_position = {
        occurrence_id: position
        for position, occurrence_id in enumerate(occurrence_by_id)
    }
    prior_source_position = -1
    for row in rows:
        _expect_keys(row, LOCAL_FLOW_KEYS, "local-edge flow branch")
        source = occurrence_by_id.get(row["source_occurrence_id"])
        parent_branch_ids = row["parent_flow_branch_ids"]
        parent_occurrence_ids = row["parent_source_occurrence_ids"]
        expected_id = "questionnaire-flow:" + _canonical_digest(
            [
                parent_branch_ids,
                row["interview_wave"],
                row["source_occurrence_id"],
            ]
        )
        source_position = occurrence_position.get(
            row["source_occurrence_id"], -1
        )
        if (
            source is None
            or source["occurrence_kind"] != "flow_branch_label"
            or source_position <= prior_source_position
            or row["flow_branch_id"] in branch_by_id
            or row["source_occurrence_id"] in branch_by_occurrence
            or not isinstance(parent_branch_ids, list)
            or not isinstance(parent_occurrence_ids, list)
            or len(parent_branch_ids) != len(set(parent_branch_ids))
            or len(parent_occurrence_ids) != len(set(parent_occurrence_ids))
            or row["flow_branch_id"] != expected_id
            or source["parent_flow_occurrence_ids"] != parent_occurrence_ids
            or row["interview_wave"] != source["interview_wave"]
            or row["source_locator_id"] != source["source_locator_id"]
            or row["page_number"] != source["page_number"]
            or row["occurrence_index_on_page"]
            != source["occurrence_index_on_page"]
            or row["branch_label"] != source["matched_text"]
            or row["branch_label_sha256"] != source["matched_utf8_sha256"]
        ):
            raise ValueError(
                "local flow branch equation or source order drift"
            )
        branch_by_id[row["flow_branch_id"]] = row
        branch_by_occurrence[row["source_occurrence_id"]] = row
        prior_source_position = source_position
    label_ids = [
        occurrence_id
        for occurrence_id, row in occurrence_by_id.items()
        if row["occurrence_kind"] == "flow_branch_label"
    ]
    if [row["source_occurrence_id"] for row in rows] != label_ids:
        raise ValueError("local flow rows do not exactly cover labels")

    children: dict[str, list[str]] = defaultdict(list)
    indegree = {branch_id: 0 for branch_id in branch_by_id}
    for branch_id, branch in branch_by_id.items():
        parent_occurrence_ids = branch["parent_source_occurrence_ids"]
        expected_parent_branch_ids = (
            [FLOW_ROOT]
            if not parent_occurrence_ids
            else [
                branch_by_occurrence[parent_id]["flow_branch_id"]
                for parent_id in parent_occurrence_ids
                if parent_id in branch_by_occurrence
            ]
        )
        if (
            len(expected_parent_branch_ids)
            != (1 if not parent_occurrence_ids else len(parent_occurrence_ids))
            or branch["parent_flow_branch_ids"] != expected_parent_branch_ids
        ):
            raise ValueError("local flow parent projection is unresolved")
        for parent_id in branch["parent_flow_branch_ids"]:
            if parent_id == FLOW_ROOT:
                continue
            if parent_id not in branch_by_id:
                raise ValueError("local flow parent branch is unresolved")
            children[parent_id].append(branch_id)
            indegree[branch_id] += 1
    ready = deque(
        branch_id for branch_id, degree in indegree.items() if degree == 0
    )
    visited = 0
    while ready:
        branch_id = ready.popleft()
        visited += 1
        for child_id in children[branch_id]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                ready.append(child_id)
    if visited != len(branch_by_id):
        raise ValueError("local flow parent relation is cyclic")

    _verify_local_occurrence_parent_order(
        occurrence_by_id, branch_by_occurrence, flow_edge_order
    )


def _contains_forbidden_path_product(value: Any) -> bool:
    if isinstance(value, Mapping):
        forbidden_keys = {"branch_" + "path", "flow_branch_" + "paths"}
        return any(
            key in forbidden_keys or _contains_forbidden_path_product(member)
            for key, member in value.items()
        )
    if isinstance(value, list):
        return any(
            _contains_forbidden_path_product(member) for member in value
        )
    return isinstance(value, str) and FORBIDDEN_PARENT_PATH_MARKER in value


def _verify_flow(
    value: Mapping[str, Any],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    rows = value["flow_branch_rows"]
    if not isinstance(rows, list):
        raise ValueError("flow branches are not an array")
    if value["schema_version"] == LOCAL_EDGE_SCHEMA:
        seal = value["seal"]
        position = value["document_source_position"]
        flow_edge_order = LOCAL_FLOW_EDGE_ORDER_BY_POSITION.get(position)
        if (
            flow_edge_order is None
            or seal.get("flow_edge_order") != flow_edge_order
            or seal.get("flow_parent_representation")
            != "direct_parent_occurrence_ids_no_path_products"
            or seal.get("serialized_path_product_count") != 0
            or _contains_forbidden_path_product(
                {
                    "questionnaire_occurrence_rows": value[
                        "questionnaire_occurrence_rows"
                    ],
                    "flow_branch_rows": rows,
                }
            )
        ):
            raise ValueError("local-edge artifact serialized a path product")
        _verify_local_flow(rows, occurrence_by_id, flow_edge_order)
        return
    _verify_legacy_flow(rows, occurrence_by_id)


def _verify_annotation(
    path: Path,
    raw: bytes,
    value: Mapping[str, Any],
    document: Mapping[str, Any],
    position: int,
    replay_pages: Sequence[Mapping[str, Any]],
    source_replay_identity: Mapping[str, Any],
    candidate_index_identity: Mapping[str, Any],
) -> tuple[tuple[Mapping[str, Any], ...], dict[str, Any]]:
    if (
        value.get("schema_version") not in ALLOWED_ANNOTATION_SCHEMAS
        or len(raw) >= MAX_COMMITTED_FILE_BYTES
        or raw != canonical_json_bytes(value)
    ):
        raise ValueError("stage-2 annotation identity or scale drift")
    _expect_keys(
        value,
        _expected_annotation_keys(value, position),
        "stage-2 annotation",
    )
    artifact_id = value["artifact_id"]
    if (
        value["document_source_position"] != position
        or value["document_source_row"] != document
        or not isinstance(artifact_id, str)
        or not artifact_id.startswith("rq-stage2-document-annotation:")
        or not _valid_sha256(
            artifact_id.removeprefix("rq-stage2-document-annotation:")
        )
        or _contains_source_forbidden_emission(value)
    ):
        raise ValueError("stage-2 annotation source-domain drift")
    for actual, expected, label in (
        (value["source_replay_identity"], source_replay_identity, "replay"),
        (value["candidate_index_identity"], candidate_index_identity, "index"),
    ):
        if not isinstance(actual, Mapping) or dict(actual) != (
            _expected_embedded_identity(expected, value)
        ):
            raise ValueError(f"stage-2 annotation {label} identity drift")
    _verify_annotation_integrity(value)
    _verify_annotation_nonauthority(value)
    locators = _normalized_locators(value, document)
    occurrence_by_id = _verify_occurrences(
        value, document, locators[0]["locator_id"]
    )
    _verify_pages(
        value,
        document,
        locators[0]["locator_id"],
        replay_pages,
        occurrence_by_id,
    )
    _verify_raster_sidecar(
        value,
        document,
        position,
        replay_pages,
        occurrence_by_id,
    )
    _verify_flow(value, occurrence_by_id)
    _verify_annotation_seal(value, locators)
    input_row = {
        "document_source_position": position,
        "source_document_id": document["source_document_id"],
        "annotation_path": str(path.relative_to(ROOT)),
        "schema_version": value["schema_version"],
        "artifact_id": value["artifact_id"],
        "byte_size": len(raw),
        "raw_sha256": _sha256(raw),
        "content_sha256": value["integrity"]["content_sha256"],
        "status": value["status"],
    }
    _expect_keys(input_row, ANNOTATION_INPUT_KEYS, "annotation input row")
    return locators, input_row


def load_era_inputs(era_id: str) -> EraInputs:
    """Load and validate the fixed source-led inputs for one defined era."""

    if era_id not in ERA_BY_ID:
        raise ValueError(f"unknown fixed era: {era_id!r}")
    spec = ERA_BY_ID[era_id]
    if (
        stage1_candidates.SOURCE_REPLAY_PATH.stat().st_size
        >= MAX_COMMITTED_FILE_BYTES
    ):
        raise ValueError("R_Q source replay exceeds the scale law")
    replay = stage1_candidates.load_source_replay()
    index, index_identity = _load_candidate_index(replay)
    protocol_identity = _protocol_identity()
    replay_era = next(
        row for row in replay["era_replay_rows"] if row["era_id"] == era_id
    )
    if (
        replay_era["interview_waves"] != list(spec["interview_waves"])
        or replay_era["questionnaire_document_count"]
        != spec["questionnaire_document_count"]
        or replay_era["questionnaire_page_count"]
        != spec["questionnaire_page_count"]
    ):
        raise ValueError("stage-1 era replay differs from the fixed era spec")

    all_documents = replay["source_document_replay"]["questionnaire_documents"]
    candidate_rows = index["document_candidate_manifest_rows"]
    selected_positions = spec["document_source_positions"]
    selected_documents = [
        all_documents[position - 1] for position in selected_positions
    ]
    selected_ids = {row["source_document_id"] for row in selected_documents}
    selected_pages = [
        row
        for row in replay["questionnaire_page_replay"][
            "questionnaire_page_rows"
        ]
        if row["source_document_id"] in selected_ids
    ]
    if (
        [row["interview_waves"][0] for row in selected_documents]
        != sorted(row["interview_waves"][0] for row in selected_documents)
        or set(row["interview_waves"][0] for row in selected_documents)
        != set(spec["interview_waves"])
        or len(selected_pages) != spec["questionnaire_page_count"]
        or _stream_array_digest(
            [row["source_document_id"] for row in selected_documents]
        )
        != replay_era["questionnaire_document_keyset_sha256"]
        or _stream_array_digest(selected_documents)
        != replay_era["questionnaire_document_domain_sha256"]
        or _stream_array_digest(
            [row["questionnaire_page_id"] for row in selected_pages]
        )
        != replay_era["questionnaire_page_keyset_sha256"]
        or _stream_array_digest(selected_pages)
        != replay_era["questionnaire_page_domain_sha256"]
    ):
        raise ValueError("source replay era document or page domain drift")

    pages_by_document: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for page in selected_pages:
        pages_by_document[page["source_document_id"]].append(page)
    annotations: list[AnnotationInput] = []
    sidecar_positions: set[int] = set()
    source_replay_identity = stage1_candidates.source_replay_identity()
    for position, document in zip(
        selected_positions, selected_documents, strict=True
    ):
        candidate_row = candidate_rows[position - 1]
        if (
            candidate_row["document_source_position"] != position
            or candidate_row["source_document_id"]
            != document["source_document_id"]
            or candidate_row["era_id"] != era_id
        ):
            raise ValueError("candidate index era projection drift")
        path = _annotation_path(candidate_row, position)
        raw = path.read_bytes()
        value = strict_parse_document(raw, f"stage-2 annotation {position}")
        if not isinstance(value, Mapping):
            raise ValueError("stage-2 annotation is not an object")
        locators, input_row = _verify_annotation(
            path,
            raw,
            value,
            document,
            position,
            pages_by_document[document["source_document_id"]],
            source_replay_identity,
            index_identity,
        )
        if "raster_only_incompleteness_census" in value:
            sidecar_positions.add(position)
        annotations.append(
            AnnotationInput(
                path=path,
                raw=raw,
                value=value,
                document=document,
                input_row=input_row,
                locators=locators,
            )
        )
    expected_sidecars = EXPECTED_RASTER_SIDECAR_POSITIONS.intersection(
        selected_positions
    )
    if sidecar_positions != expected_sidecars:
        raise ValueError("era raster-only sidecar input domain drift")
    return EraInputs(
        replay=replay,
        index=index,
        index_identity=index_identity,
        protocol_identity=protocol_identity,
        spec=spec,
        annotations=tuple(annotations),
    )


def _row_keyset(
    rows: Sequence[Mapping[str, Any]], key_fields: Sequence[str]
) -> list[Any]:
    if len(key_fields) == 1:
        return [row[key_fields[0]] for row in rows]
    return [[row[field] for field in key_fields] for row in rows]


def _era_domains(inputs: EraInputs) -> dict[str, list[Mapping[str, Any]]]:
    domains: dict[str, list[Mapping[str, Any]]] = {
        "document_source_rows": [],
        "whole_document_locator_rows": [],
        "questionnaire_page_rows": [],
        "questionnaire_occurrence_rows": [],
        "flow_branch_rows": [],
    }
    for annotation in inputs.annotations:
        domains["document_source_rows"].append(annotation.document)
        domains["whole_document_locator_rows"].extend(annotation.locators)
        domains["questionnaire_page_rows"].extend(
            annotation.value["questionnaire_page_rows"]
        )
        domains["questionnaire_occurrence_rows"].extend(
            annotation.value["questionnaire_occurrence_rows"]
        )
        domains["flow_branch_rows"].extend(
            annotation.value["flow_branch_rows"]
        )
    for domain, key_fields in ROW_DOMAIN_SPECS:
        keyset = _row_keyset(domains[domain], key_fields)
        if len(keyset) != len({str(member) for member in keyset}):
            raise ValueError(f"{domain} contains a duplicate key")
    return domains


def _row_domain_seals(inputs: EraInputs) -> list[dict[str, Any]]:
    domains = _era_domains(inputs)
    rows: list[dict[str, Any]] = []
    for domain, key_fields in ROW_DOMAIN_SPECS:
        domain_rows = domains[domain]
        rows.append(
            {
                "row_domain": domain,
                "row_count": len(domain_rows),
                "row_key_fields": list(key_fields),
                "row_keyset_sha256": _stream_array_digest(
                    _row_keyset(domain_rows, key_fields)
                ),
                "row_domain_sha256": _stream_array_digest(domain_rows),
            }
        )
    pinned = PINNED_ROW_DOMAIN_SEALS.get(inputs.spec["era_id"])
    if pinned is None or rows != list(pinned):
        raise ValueError(
            "era logical row domains differ from their pinned seal"
        )
    return rows


def _artifact_id_preimage(value: Mapping[str, Any]) -> list[Any]:
    return [
        value.get("era_id"),
        value.get("source_replay_identity", {}).get("content_sha256"),
        value.get("candidate_index_identity", {}).get("content_sha256"),
        value.get("stage2_protocol_identity", {}).get("raw_sha256"),
        value.get("document_annotation_input_domain_sha256"),
        value.get("row_domain_seal_domain_sha256"),
    ]


def _constructed_era_seal(inputs: EraInputs) -> dict[str, Any]:
    spec = inputs.spec
    waves = list(spec["interview_waves"])
    positions = list(spec["document_source_positions"])
    input_rows = [
        dict(annotation.input_row) for annotation in inputs.annotations
    ]
    input_seal = {
        "document_annotation_input_count": len(input_rows),
        "document_annotation_input_keyset_sha256": _stream_array_digest(
            [
                [
                    row["document_source_position"],
                    row["source_document_id"],
                ]
                for row in input_rows
            ]
        ),
        "document_annotation_input_domain_sha256": _stream_array_digest(
            input_rows
        ),
    }
    if input_seal != PINNED_ANNOTATION_INPUT_SEALS.get(spec["era_id"]):
        raise ValueError(
            "era annotation inputs differ from their pinned identity seal"
        )
    row_seals = _row_domain_seals(inputs)
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "",
        "authority_kind": AUTHORITY_KIND,
        "source_replay_identity": dict(
            stage1_candidates.source_replay_identity()
        ),
        "candidate_index_identity": dict(inputs.index_identity),
        "stage2_protocol_identity": dict(inputs.protocol_identity),
        "era_id": spec["era_id"],
        "era_order_position": spec["era_order_position"],
        "interview_waves": waves,
        "interview_wave_count": len(waves),
        "interview_wave_domain_sha256": _stream_array_digest(waves),
        "document_source_positions": positions,
        "document_source_position_count": len(positions),
        "document_source_position_domain_sha256": _stream_array_digest(
            positions
        ),
        "document_annotation_input_rows": input_rows,
        **input_seal,
        "row_domain_seal_rows": row_seals,
        "row_domain_seal_count": len(row_seals),
        "row_domain_seal_domain_sha256": _stream_array_digest(row_seals),
        "nonauthority_statement": copy.deepcopy(NONAUTHORITY_STATEMENT),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": STATUS,
    }
    value["artifact_id"] = (
        "rq-stage3-era-preparation-seal:"
        + _canonical_digest(_artifact_id_preimage(value))
    )
    value["integrity"]["content_sha256"] = _content_sha256(value)
    return value


def _contains_forbidden_emission(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in FORBIDDEN_EMISSION_KEYS
            or _contains_forbidden_emission(member)
            for key, member in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_emission(member) for member in value)
    return isinstance(value, str) and value.startswith(
        FORBIDDEN_GLOBAL_ID_PREFIXES
    )


def validate_era_seal(
    value: Mapping[str, Any], inputs: EraInputs | None = None
) -> None:
    """Reconstruct one fixed logical era domain before reading its seal."""

    era_id = value.get("era_id")
    if era_id not in SEALED_ERA_IDS:
        raise ValueError("era seal ID is absent or not yet committed")
    if inputs is None:
        inputs = load_era_inputs(era_id)
    if inputs.spec["era_id"] != era_id:
        raise ValueError("era seal and source inputs disagree")
    expected = _constructed_era_seal(inputs)
    _expect_keys(value, TOP_LEVEL_KEYS, "era preparation seal")
    for key, expected_member in expected.items():
        if key == "integrity":
            continue
        if value[key] != expected_member:
            raise ValueError(f"era preparation seal {key} drift")
    for row in value["document_annotation_input_rows"]:
        _expect_keys(row, ANNOTATION_INPUT_KEYS, "annotation input row")
    for row in value["row_domain_seal_rows"]:
        _expect_keys(row, ROW_DOMAIN_SEAL_KEYS, "row-domain seal")
    if value["integrity"] != {
        "canonicalization": CANONICALIZATION,
        "content_sha256": _content_sha256(value),
    } or _contains_forbidden_emission(value):
        raise ValueError("era integrity or forbidden-emission law drift")


def build_era_seal(
    era_id: str, inputs: EraInputs | None = None
) -> dict[str, Any]:
    """Build and mirror one compact nonauthority era preparation seal."""

    if inputs is None:
        inputs = load_era_inputs(era_id)
    value = _constructed_era_seal(inputs)
    validate_era_seal(value, inputs)
    return value


def _reseal_mutation(value: dict[str, Any]) -> None:
    """Coherently reseal candidate-described domains for strong mutations."""

    waves = value.get("interview_waves")
    if isinstance(waves, list):
        value["interview_wave_count"] = len(waves)
        value["interview_wave_domain_sha256"] = _stream_array_digest(waves)
    positions = value.get("document_source_positions")
    if isinstance(positions, list):
        value["document_source_position_count"] = len(positions)
        value["document_source_position_domain_sha256"] = _stream_array_digest(
            positions
        )
    inputs = value.get("document_annotation_input_rows")
    if isinstance(inputs, list):
        value["document_annotation_input_count"] = len(inputs)
        value["document_annotation_input_keyset_sha256"] = (
            _stream_array_digest(
                [
                    [
                        row.get("document_source_position"),
                        row.get("source_document_id"),
                    ]
                    for row in inputs
                ]
            )
        )
        value["document_annotation_input_domain_sha256"] = (
            _stream_array_digest(inputs)
        )
    seals = value.get("row_domain_seal_rows")
    if isinstance(seals, list):
        value["row_domain_seal_count"] = len(seals)
        value["row_domain_seal_domain_sha256"] = _stream_array_digest(seals)
    value["artifact_id"] = (
        "rq-stage3-era-preparation-seal:"
        + _canonical_digest(_artifact_id_preimage(value))
    )
    if isinstance(value.get("integrity"), dict):
        value["integrity"]["content_sha256"] = _content_sha256(value)


def _mutation_specs(
    value: Mapping[str, Any],
) -> list[tuple[str, Callable[[dict[str, Any]], None], bool]]:
    def reorder(rows: list[Any]) -> None:
        rows[0], rows[1] = rows[1], rows[0]

    return [
        (
            "omitted_top_level_key",
            lambda row: row.pop("authority_kind"),
            True,
        ),
        (
            "omitted_input_key_fully_rehashed",
            lambda row: row["document_annotation_input_rows"][0].pop(
                "raw_sha256"
            ),
            True,
        ),
        (
            "extra_input_key_fully_rehashed",
            lambda row: row["document_annotation_input_rows"][0].__setitem__(
                "extra", None
            ),
            True,
        ),
        (
            "missing_document_input_fully_rehashed",
            lambda row: row["document_annotation_input_rows"].pop(),
            True,
        ),
        (
            "duplicate_document_input_fully_rehashed",
            lambda row: row["document_annotation_input_rows"].append(
                copy.deepcopy(row["document_annotation_input_rows"][0])
            ),
            True,
        ),
        (
            "reordered_document_inputs_fully_rehashed",
            lambda row: reorder(row["document_annotation_input_rows"]),
            True,
        ),
        (
            "adjacent_era_document_substitution_fully_rehashed",
            lambda row: row["document_annotation_input_rows"][-1].update(
                {
                    "document_source_position": 17,
                    "source_document_id": "psid-source-document:" + "0" * 64,
                }
            ),
            True,
        ),
        (
            "wave_domain_drift_fully_rehashed",
            lambda row: row["interview_waves"].__setitem__(-1, 1976),
            True,
        ),
        (
            "document_position_domain_drift_fully_rehashed",
            lambda row: row["document_source_positions"].__setitem__(-1, 17),
            True,
        ),
        (
            "missing_row_domain_seal_fully_rehashed",
            lambda row: row["row_domain_seal_rows"].pop(),
            True,
        ),
        (
            "omitted_row_domain_seal_key_fully_rehashed",
            lambda row: row["row_domain_seal_rows"][0].pop(
                "row_domain_sha256"
            ),
            True,
        ),
        (
            "reordered_row_domain_seals_fully_rehashed",
            lambda row: reorder(row["row_domain_seal_rows"]),
            True,
        ),
        (
            "row_count_drift_fully_rehashed",
            lambda row: row["row_domain_seal_rows"][2].__setitem__(
                "row_count", row["row_domain_seal_rows"][2]["row_count"] - 1
            ),
            True,
        ),
        (
            "row_keyset_drift_fully_rehashed",
            lambda row: row["row_domain_seal_rows"][3].__setitem__(
                "row_keyset_sha256", "0" * 64
            ),
            True,
        ),
        (
            "row_domain_digest_drift_fully_rehashed",
            lambda row: row["row_domain_seal_rows"][4].__setitem__(
                "row_domain_sha256", "0" * 64
            ),
            True,
        ),
        (
            "forbidden_hierarchy_emission_fully_rehashed",
            lambda row: row.__setitem__("hierarchy_rows", []),
            True,
        ),
        (
            "q5_claim_fully_rehashed",
            lambda row: row["nonauthority_statement"].__setitem__(
                "q5_emitted", True
            ),
            True,
        ),
        (
            "canonical_era_claim_fully_rehashed",
            lambda row: row["nonauthority_statement"].__setitem__(
                "canonical_era_row_emitted", True
            ),
            True,
        ),
        (
            "status_drift_fully_rehashed",
            lambda row: row.__setitem__("status", "pass"),
            True,
        ),
        (
            "stale_integrity",
            lambda row: row["integrity"].__setitem__(
                "content_sha256", "0" * 64
            ),
            False,
        ),
    ]


def run_mutation_tests(value: Mapping[str, Any], inputs: EraInputs) -> None:
    """Require every coherently resealed candidate mutation to fail closed."""

    names: set[str] = set()
    for name, mutate, reseal in _mutation_specs(value):
        if name in names:
            raise ValueError(f"duplicate mutation name: {name}")
        names.add(name)
        mutation = copy.deepcopy(value)
        mutate(mutation)
        if reseal:
            _reseal_mutation(mutation)
        try:
            validate_era_seal(mutation, inputs)
        except ValueError:
            continue
        raise ValueError(f"era mutation was not rejected: {name}")


def era_output_path(era_id: str) -> Path:
    if era_id not in SEALED_ERA_IDS:
        raise ValueError(f"era is not yet sealed: {era_id!r}")
    return OUTPUT_ROOT / f"{era_id}_preparation_seal_v1.json"


def render_era(era_id: str, inputs: EraInputs | None = None) -> bytes:
    return canonical_json_bytes(build_era_seal(era_id, inputs))


def _write_or_check(path: Path, raw: bytes, check: bool) -> None:
    if len(raw) >= MAX_COMMITTED_FILE_BYTES:
        raise ValueError("era preparation seal exceeds artifact-scale law")
    if check:
        if not path.is_file() or path.read_bytes() != raw:
            raise ValueError(f"era preparation seal drift: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--era", required=True, choices=SEALED_ERA_IDS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mutation-tests", action="store_true")
    args = parser.parse_args()
    inputs = load_era_inputs(args.era)
    value = build_era_seal(args.era, inputs)
    if args.mutation_tests:
        run_mutation_tests(value, inputs)
    output = args.output or era_output_path(args.era)
    _write_or_check(output, canonical_json_bytes(value), args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
