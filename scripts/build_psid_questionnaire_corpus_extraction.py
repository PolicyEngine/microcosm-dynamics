#!/usr/bin/env python3
"""Build the source-bound PSID questionnaire extraction audit.

The source corpus is external to Git.  This builder accepts only individually
verified documents from the frozen registration artifact, verifies
every cited file and byte range, and records questionnaire evidence separately
from authority acceptance or operative membership adjudication.
"""

from __future__ import annotations

import argparse
import copy
import decimal
import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)
OUT_PATH = (
    ROOT / "data" / "external" / "psid_questionnaire_corpus_extraction_v1.json"
)

SCHEMA_VERSION = "psid_questionnaire_corpus_extraction.v1"
ARTIFACT_ID = "entry11_unit1b_psid_questionnaire_extraction_v1"
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"

AUTHORITY_DISPOSITION = {
    "corpus_registration_status": "pass",
    "accepted_corpus_authority": True,
    "verified_candidate_documents_may_support_nonoperative_audit": True,
    "membership_v3_or_supersession_effect": "none",
}

EXTRACTION_METHOD = {
    "method_id": "source_bound_questionnaire_page_and_flow_review_v1",
    "source_only": True,
    "semantic_review": "human_verified_rendered_questionnaire_pages_and_complete_flow_domains",
    "positive_locator_rule": "exact raw PDF content-stream range or contiguous content-stream envelope",
    "negative_locator_rule": "complete enumerated document or section domain with source-backed exclusion rules",
    "envelope_caveat": "An envelope is a contiguous source-file slice from the first to last page content stream and may include intervening PDF object bytes; it is not a concatenated stream.",
    "derived_text_retained": False,
}

FROZEN_INPUTS = {
    "corpus_registration_attempt": {
        "committed_path": "data/external/psid_questionnaire_corpus_authority_registration_attempt_v1.json",
        "size_bytes": 520_656,
        "sha256": "07c5bad57d702416da7ee668f504646ba85b9868a7f38819cdec85638c97558c",
        "schema_version": "psid_questionnaire_corpus_authority_registration_attempt.v1",
    },
    "psid_codebook_inventory_adjudication": {
        "committed_path": "data/external/psid_codebook_inventory_adjudication_v1.json",
        "size_bytes": 1_415_319,
        "sha256": "df73026bcf649d12ecb606501d64780f41567b6dc09d7029f9191111cab09c62",
        "schema_version": "psid_codebook_inventory_adjudication.v1",
    },
    "membership_adjudication_v2": {
        "committed_path": "data/external/covered_earnings_membership_adjudication_v2.json",
        "size_bytes": 57_125,
        "sha256": "7306c898d044df0ce86754b8468b26e32d8696027e8dde2f7d5935d79f1abb14",
        "schema_version": "covered_earnings_membership_adjudication.v2",
    },
}

TARGET_RESIDUAL_INDEXES = {
    "wave1968_ry1968_1974_early_totals:occupation_industry_attachment_closure": 3,
    "ry1975_1977_spouse_concept_seam:V-B6:V5289_V5788_concept": 6,
    "ry1975_1977_spouse_concept_seam:V-B6:1977_1978_spouse_current_job_context_absence": 7,
    "ry1975_1977_spouse_concept_seam:V-B6:government_level_absence": 8,
    "ry1975_1977_spouse_concept_seam:V-B6:secondary_job_attachment_and_absence": 9,
    "ry2002_2014_modern_bc_de:V-B8:branch_freshness": 23,
    "ry2002_2014_modern_bc_de:V-B8:pre_2013_questionnaire_absence_proof": 24,
    "ry2015_2022_exclusion_lineage:V-B8:branch_freshness": 31,
}

# (locator id, source document id, page number, page object, contents object,
#  range kind, start, end, range SHA-256, semantic anchor)
PASSAGE_SPECS = (
    (
        "vb5_occind_p2",
        "psid-corpus-document-0001",
        2,
        12,
        13,
        "pdf_page_content_stream_raw_byte_range",
        1227,
        3864,
        "63ed225740d0da19b0d4a15c208b9062198d792c8b1de5e408c82ffd0fb9dbfd",
        "Merged retrospective occupation and industry variable naming.",
    ),
    (
        "vb5_occind_p3",
        "psid-corpus-document-0001",
        3,
        21,
        22,
        "pdf_page_content_stream_raw_byte_range",
        3957,
        6875,
        "01b4fdecdf487104db5396bc18763edfc75f84165c98d16cbc57218b978cf8ed",
        "Three-digit 1970 Census coding basis and selected original-sample main-job universe.",
    ),
    (
        "vb5_occind_p4",
        "psid-corpus-document-0001",
        4,
        26,
        27,
        "pdf_page_content_stream_raw_byte_range",
        6968,
        10114,
        "8cf88e0a0a61e1e5e6525bb2877bcd1f709aa3eb6e15cd642e2b69e1a7c0de36",
        "Beginning of exhaustive wave-by-role-by-employment attachment table.",
    ),
    (
        "vb5_occind_p5",
        "psid-corpus-document-0001",
        5,
        31,
        32,
        "pdf_page_content_stream_raw_byte_range",
        10207,
        11240,
        "6cc79aa586655d17d292c9b1de222900e661d23c8f111f989f7e8ba2899802c0",
        "Continuation of attachment table and unsupported slots.",
    ),
    (
        "vb5_occind_p6",
        "psid-corpus-document-0001",
        6,
        36,
        37,
        "pdf_page_content_stream_raw_byte_range",
        11333,
        12808,
        "ee8b88e07e3c0c9fedd75e99675bfb1594f255160b66ca4d58284297083b651f",
        "Attachment-table notes distinguish main, last, and usual jobs and prior-year zero hours.",
    ),
    (
        "vb5_codes_p649",
        "psid-corpus-document-0068",
        649,
        25533,
        25534,
        "pdf_page_content_stream_raw_byte_range",
        10152158,
        10153295,
        "1cff0fb597d6ff796371ea4b80b6a931c084eb60346f718982903d403676b23f",
        "Appendix 2 identifies the 1970 Census basis and PSID additions 600 and 999.",
    ),
    (
        "vb5_codes_p650",
        "psid-corpus-document-0068",
        650,
        25536,
        25538,
        "pdf_page_content_stream_envelope_raw_byte_range",
        10154299,
        10163658,
        "8db5c478321c4619267ab38744d0dee2fbe9b291d370a37d1a21c106fae7298c",
        "Exact three-digit industry meanings, part 1.",
    ),
    (
        "vb5_codes_p651",
        "psid-corpus-document-0068",
        651,
        25600,
        25602,
        "pdf_page_content_stream_envelope_raw_byte_range",
        10227380,
        10240211,
        "0430bf64d77c5a7888bc2eac23eba1eb26401e22857c731270f96f211030691a",
        "Exact three-digit industry meanings, part 2.",
    ),
    (
        "vb5_codes_p652",
        "psid-corpus-document-0068",
        652,
        25708,
        25710,
        "pdf_page_content_stream_envelope_raw_byte_range",
        10316091,
        10326930,
        "b20fa6cddd4b6cae6fe37dbe8ba6ad602d7d9b4addb4a9a2d3e73c24fd0af35f",
        "Exact three-digit industry meanings, part 3.",
    ),
    (
        "vb5_codes_p653",
        "psid-corpus-document-0068",
        653,
        25822,
        25824,
        "pdf_page_content_stream_envelope_raw_byte_range",
        10382570,
        10392064,
        "26576b5f8fb7d12e3a0075b0a4b3c95af537b1404b8197a7549abd0f8b82e3c7",
        "Exact three-digit occupation meanings, part 1.",
    ),
    (
        "vb5_codes_p654",
        "psid-corpus-document-0068",
        654,
        25930,
        25932,
        "pdf_page_content_stream_envelope_raw_byte_range",
        10447738,
        10458723,
        "e917ab83adc5e726f55607864b7e024e765bb4b380dcf58f80f778315f9579e9",
        "Exact three-digit occupation meanings, part 2.",
    ),
    (
        "vb5_codes_p655",
        "psid-corpus-document-0068",
        655,
        26038,
        26040,
        "pdf_page_content_stream_envelope_raw_byte_range",
        10518519,
        10530511,
        "ddb6a54cd325b12caff7c7c31d97b5d7e597355b9b26192572c0636f0570b4ee",
        "Exact three-digit occupation meanings, part 3.",
    ),
    (
        "vb5_codes_p656",
        "psid-corpus-document-0068",
        656,
        26148,
        26150,
        "pdf_page_content_stream_envelope_raw_byte_range",
        10595390,
        10606984,
        "554b3be5104bf468154bed204c1ab8c5d1c894ae1418c43185fd3dd99e0d2ba2",
        "Exact three-digit occupation meanings, part 4.",
    ),
    (
        "vb5_codes_p657",
        "psid-corpus-document-0068",
        657,
        26260,
        26262,
        "pdf_page_content_stream_envelope_raw_byte_range",
        10669153,
        10677297,
        "e79199b03c55ba038d3d5cb4ed6c5638377b8b645f92ccfa25409aec12c4f793",
        "Exact three-digit occupation meanings, part 5.",
    ),
    (
        "vb6_1977_worksheet_p55",
        "psid-corpus-document-0048",
        55,
        3382,
        3384,
        "pdf_page_content_stream_envelope_raw_byte_range",
        1671677,
        1678121,
        "d68cc36573cdcd671c4617929b28ed61f48677d4b59a9e57166b2bc1c3db2b2d",
        "Worksheet separates family-business labor and asset parts from Wife wages V5289.",
    ),
    (
        "vb6_1977_label_p84",
        "psid-corpus-document-0048",
        84,
        3794,
        3795,
        "pdf_page_content_stream_raw_byte_range",
        1836843,
        1838296,
        "3659a074c1127016802447d148e1bc7c17eb84c339fc8847194ba50936d41bdf",
        "Generated field label identifies V5289 as Wife labor income.",
    ),
    (
        "vb6_1978_worksheet_p74",
        "psid-corpus-document-0053",
        74,
        12108,
        12110,
        "pdf_page_content_stream_envelope_raw_byte_range",
        3892313,
        3900153,
        "11445c796f8783cf6430e32b45ed1d452a6e3ccc0543e5e76cf07732c3fc5fc1",
        "Worksheet separates V5781 family-business labor, V5788 Wife wages, and V5791 asset income.",
    ),
    (
        "vb6_1978_label_p232",
        "psid-corpus-document-0053",
        232,
        39149,
        39151,
        "pdf_page_content_stream_envelope_raw_byte_range",
        12734188,
        12743100,
        "f878f7c4db7a6897bde84d1b993ca5f1e448199ac788cfd05e6311ec9a54c6a9",
        "Generated field labels identify 1977 Wife labor income V5788 and hours.",
    ),
    (
        "vb6_1977_qxq_p54",
        "psid-corpus-document-0050",
        54,
        187,
        188,
        "pdf_page_content_stream_raw_byte_range",
        16548040,
        16552668,
        "14372a04784b4d9edc19dda18e9fae98c3919761399dd6fe812756390e99a45d",
        "Instruction records Wife income from all sources and marks family-business income already included in H7 to avoid duplication.",
    ),
    (
        "vb6_1978_qxq_p70",
        "psid-corpus-document-0055",
        70,
        242,
        243,
        "pdf_page_content_stream_raw_byte_range",
        18081742,
        18084806,
        "a3e1d35f057322f309df9a9022aecc08d96cbcd6966119073a3b10cb44a17709",
        "Instruction records Wife income from all sources and marks family-business income already included in H7 to avoid duplication.",
    ),
    (
        "vb6_q77_wife_p17",
        "psid-corpus-document-0049",
        17,
        723,
        725,
        "pdf_page_content_stream_envelope_raw_byte_range",
        611190,
        1327262,
        "7f1b8d519f987324c577ccc32aa1c8431c027e2e1e9d862dac2702152bb5a1bf",
        "Wife Section G annual-work and occupation flow, part 1.",
    ),
    (
        "vb6_q77_wife_p18",
        "psid-corpus-document-0049",
        18,
        768,
        770,
        "pdf_page_content_stream_envelope_raw_byte_range",
        644615,
        1327262,
        "afd9cd88675abea72b0177cb264d2ad1c96d1b2a5c09435464fc7daef02f2fbd",
        "Wife Section G annual-work and occupation flow, part 2.",
    ),
    (
        "vb6_q77_wife_p19",
        "psid-corpus-document-0049",
        19,
        813,
        815,
        "pdf_page_content_stream_envelope_raw_byte_range",
        685717,
        1328640,
        "bfbd9ee2433845ec4b82da975f4787f10d6958f3ba438f2150d7b6c663dbc097",
        "Wife Section G annual-work and hours flow, part 3.",
    ),
    (
        "vb6_q77_wife_p20",
        "psid-corpus-document-0049",
        20,
        858,
        860,
        "pdf_page_content_stream_envelope_raw_byte_range",
        731234,
        736288,
        "da997670abd3bb7364c6e02c63d06ff8dc0e7333fd088549337a887997038701",
        "End of exhaustive 1977 Wife Section G.",
    ),
    (
        "vb6_q78_wife_p22",
        "psid-corpus-document-0054",
        22,
        1763,
        1765,
        "pdf_page_content_stream_envelope_raw_byte_range",
        997094,
        1002670,
        "55aaa7fbe72330ac9bc0e36b76b8594cd606f4004c0a54f802b6f1a8420d6fb5",
        "Wife Section G annual-work and occupation flow, part 1.",
    ),
    (
        "vb6_q78_wife_p23",
        "psid-corpus-document-0054",
        23,
        1851,
        1853,
        "pdf_page_content_stream_envelope_raw_byte_range",
        1039547,
        1046268,
        "c52ee48bb32f2bb5f4d63ce052f154d3a10de3b023142367dfbbca84f2b9dd61",
        "Wife Section G annual-work and occupation flow, part 2.",
    ),
    (
        "vb6_q78_wife_p24",
        "psid-corpus-document-0054",
        24,
        1941,
        1943,
        "pdf_page_content_stream_envelope_raw_byte_range",
        1087162,
        1095244,
        "a4756e6c334d694dbffb790618fb2f687a3750b999b4351a4853e0add92af618",
        "Wife Section G annual-work, hours, commute, and tenure flow, part 3.",
    ),
    (
        "vb6_q78_wife_p25",
        "psid-corpus-document-0054",
        25,
        2029,
        2031,
        "pdf_page_content_stream_envelope_raw_byte_range",
        1145220,
        1152021,
        "fc1922970f9a715bfe51414e3beb0b9e830ff13a7e0c0daf50c19f2cba7b3c31",
        "End of exhaustive 1978 Wife Section G.",
    ),
    (
        "vb6_q76_government_p46",
        "psid-corpus-document-0044",
        46,
        2712,
        2714,
        "pdf_page_content_stream_envelope_raw_byte_range",
        1624986,
        1631766,
        "30a345bcd1b0bb90476a3a89bff7cdf234da5e7c64b8c1185e0132e78554e511",
        "V4844 role split, single federal/state/local government yes-no items V4845/V4850, and incorporation items V4855/V4858.",
    ),
    (
        "vb6_q76_extra_job_p50",
        "psid-corpus-document-0044",
        50,
        2966,
        2968,
        "pdf_page_content_stream_envelope_raw_byte_range",
        1796808,
        1802906,
        "0ed4477febbdba1b63c4fe9bb26b16c4ca1726c0f747b9de16975800c19b808b",
        "Within Wife Section D, V4901-V4906 ask about work beyond the main job during 1975.",
    ),
    (
        "vb6_q76_income_p25",
        "psid-corpus-document-0044",
        25,
        1400,
        1402,
        "pdf_page_content_stream_envelope_raw_byte_range",
        843302,
        849992,
        "b606cac8423ea88bfa58ef258548059a04da321d4934cf254d640fc54c121f8f",
        "H23-H25 record Wife 1975 income source and amount.",
    ),
    (
        "vb8_q2013_role_p212",
        "psid-corpus-document-0175",
        212,
        235,
        563,
        "pdf_page_content_stream_raw_byte_range",
        1639291,
        1644311,
        "bb554e145f6eab76ee6c0dcc6ce1ae165ff144ca53d954f84375b72527634884",
        "KL1CKPT distinguishes new from continuing role universes.",
    ),
    (
        "vb8_q2013_college_p221",
        "psid-corpus-document-0175",
        221,
        250,
        573,
        "pdf_page_content_stream_raw_byte_range",
        1702008,
        1709516,
        "b59bd763217400c28f1e76c863e87a225bb7ddc023215f6499037eb443868bf3",
        "KL52 month/year college timing and still-in-school codes, part 1.",
    ),
    (
        "vb8_q2013_college_p222",
        "psid-corpus-document-0175",
        222,
        251,
        574,
        "pdf_page_content_stream_raw_byte_range",
        1709593,
        1716332,
        "e550090cee0b43f2f137a69fe7ec97e9879da1ae682b4990d5274dd5893f43eb",
        "KL52 still-in-school codes, part 2.",
    ),
    (
        "vb8_q2013_rule_p225",
        "psid-corpus-document-0175",
        225,
        254,
        577,
        "pdf_page_content_stream_raw_byte_range",
        1730959,
        1739548,
        "a56a426bc99f9c56ec09719847283612c7263bc5241dd0c8d78827fc0dab3d6e",
        "KL73 exits new roles and continues same roles, excluding a new-role general-school question.",
    ),
    (
        "vb8_q2013_continuing_p226",
        "psid-corpus-document-0175",
        226,
        255,
        578,
        "pdf_page_content_stream_raw_byte_range",
        1739625,
        1747046,
        "fa3f7dcc0c9e5b5584d9d09d14857df78b4e324906d1c7d35bc9cc6e18cd9ff5",
        "Continuing-role KL74 still-in-school flow.",
    ),
    (
        "vb8_q2013_continuing_p227",
        "psid-corpus-document-0175",
        227,
        256,
        579,
        "pdf_page_content_stream_raw_byte_range",
        1747123,
        1754423,
        "3a54388dc8573e04895db47ce92bc5b9d5cbadd35af0810fe9fdf973bde6c3a5",
        "KL84 checkpoint prevents stale carried-forward answers.",
    ),
    (
        "vb8_q2013_continuing_p228",
        "psid-corpus-document-0175",
        228,
        257,
        580,
        "pdf_page_content_stream_raw_byte_range",
        1754500,
        1761695,
        "7b29723add24b91d2cbfa7091d21a5f58a06fe8d7cf24d9df8d519fcb63aed1e",
        "KL84 asks current regular-school enrollment.",
    ),
    (
        "vb8_q2015_new_p234",
        "psid-corpus-document-0179",
        234,
        1187,
        1188,
        "pdf_page_content_stream_raw_byte_range",
        1502755,
        1508474,
        "c3903366a055ff21d4065d83ff34653fad770623fcfa6079ef36345cc3728fcb",
        "New-role upstream college still-in-school branch.",
    ),
    (
        "vb8_q2015_new_p235",
        "psid-corpus-document-0179",
        235,
        1192,
        1193,
        "pdf_page_content_stream_raw_byte_range",
        1508573,
        1514863,
        "717015acdde826b0fe671238138e4735c884cfb194d8b5e7dd662bb833755046",
        "KL61ACKPT bypass plus KL61A current regular-school item forms the new-role composite.",
    ),
    (
        "vb8_q2015_role_p237",
        "psid-corpus-document-0179",
        237,
        1202,
        1203,
        "pdf_page_content_stream_raw_byte_range",
        1522873,
        1528637,
        "d9529c5f9c9441982dca3e6a98d82dae2621ea411b489f360fe6e5f208e95ac6",
        "Role-status split separates new and continuing branches.",
    ),
    (
        "vb8_q2015_continuing_p245",
        "psid-corpus-document-0179",
        245,
        1244,
        1245,
        "pdf_page_content_stream_raw_byte_range",
        1574247,
        1579894,
        "079873b73ddd895106bde0334992ff19871dc9a32706a570d0f07117add2e078",
        "Continuing-role KL74 still-in-school flow.",
    ),
    (
        "vb8_q2015_continuing_p246",
        "psid-corpus-document-0179",
        246,
        1249,
        1250,
        "pdf_page_content_stream_raw_byte_range",
        1579993,
        1583401,
        "f78029a4828f7ef747b702cf0120a8ade720435c00d60a882a12e9b84ccdee82",
        "KL84 checkpoint and current regular-school item form the continuing-role composite.",
    ),
    (
        "vb8_q2017_new_p226",
        "psid-corpus-document-0183",
        226,
        1151,
        1152,
        "pdf_page_content_stream_raw_byte_range",
        1456010,
        1462479,
        "b6411ab38f7ddc9da5048ac8c834198faf73dea43105214d6077db8279540479",
        "New-role upstream college still-in-school branch.",
    ),
    (
        "vb8_q2017_new_p227",
        "psid-corpus-document-0183",
        227,
        1156,
        1157,
        "pdf_page_content_stream_raw_byte_range",
        1462578,
        1469306,
        "abea11490760391ac8599cc60b8c67930db0bdf10fcfa4b61b10154738bc3b96",
        "KL61A and its checkpoint complete the new-role composite.",
    ),
    (
        "vb8_q2017_role_p229",
        "psid-corpus-document-0183",
        229,
        1166,
        1167,
        "pdf_page_content_stream_raw_byte_range",
        1476024,
        1483915,
        "111ce46fcb39da637ee316784aaa7a5dde24b0acbfc4be42e0328429910651af",
        "Role-status split separates new and continuing branches.",
    ),
    (
        "vb8_q2017_continuing_p236",
        "psid-corpus-document-0183",
        236,
        1203,
        1204,
        "pdf_page_content_stream_raw_byte_range",
        1523354,
        1530059,
        "0b3a7b5529ab6b79ce2a55172c011672a87a736eec271cba2bb0eeac2cbca7c0",
        "KL74/KL84 continuation checkpoint and current-school composite.",
    ),
    (
        "vb8_q2019_new_p242",
        "psid-corpus-document-0186",
        242,
        498,
        499,
        "pdf_page_content_stream_raw_byte_range",
        2090434,
        2097761,
        "bba46ac9bfe6ca6cfa261c83a84573bc0b4632643d65297dab65b54b11ff37be",
        "New-role upstream college still-in-school branch.",
    ),
    (
        "vb8_q2019_new_p243",
        "psid-corpus-document-0186",
        243,
        500,
        501,
        "pdf_page_content_stream_raw_byte_range",
        2098132,
        2107305,
        "3101bac9c9b6de360361ce1efcb4a363bdf3e3b2b95a440ecf8b0d6d21f12603",
        "KL61A and its checkpoint complete the new-role composite.",
    ),
    (
        "vb8_q2019_role_p245",
        "psid-corpus-document-0186",
        245,
        504,
        505,
        "pdf_page_content_stream_raw_byte_range",
        2115396,
        2123349,
        "813dfd0d5648e1ac4295396aabf92040ddb093b8f1c430a06cc6ee64669a6baf",
        "Role-status split separates new and continuing branches.",
    ),
    (
        "vb8_q2019_continuing_p252",
        "psid-corpus-document-0186",
        252,
        518,
        519,
        "pdf_page_content_stream_raw_byte_range",
        2175056,
        2183455,
        "2a50a0914f42abd5d6e2cd4e8d5f6602603f33fcb9f77890b25689fa33f76608",
        "KL74/KL84 continuation checkpoint and current-school composite.",
    ),
    (
        "vb8_q2021_new_p435",
        "psid-corpus-document-0189",
        435,
        2211,
        2212,
        "pdf_page_content_stream_raw_byte_range",
        2898019,
        2903287,
        "4b6644992af5fdda0020e83668b660b4c14c020d8aa7283193b846852092705e",
        "New-role upstream college still-in-school branch.",
    ),
    (
        "vb8_q2021_new_p436",
        "psid-corpus-document-0189",
        436,
        2216,
        2217,
        "pdf_page_content_stream_raw_byte_range",
        2903386,
        2913385,
        "84e798959f4366e3cb50e9139724348c874919f1fcb4ec44b30ae5c41317b130",
        "KL61A and its checkpoint complete the new-role composite.",
    ),
    (
        "vb8_q2021_role_p438",
        "psid-corpus-document-0189",
        438,
        2226,
        2227,
        "pdf_page_content_stream_raw_byte_range",
        2920727,
        2927811,
        "5fd1d5c85e381e4c185b37df4c4d93fd8ebedb17cc37edff7af7cfccd92c030c",
        "Role-status split separates new and continuing branches.",
    ),
    (
        "vb8_q2021_continuing_p450",
        "psid-corpus-document-0189",
        450,
        2286,
        2287,
        "pdf_page_content_stream_raw_byte_range",
        2990315,
        2996249,
        "20d133ab7b9347db8cea7e913591f0b94122474282ef22cd88ef6d221d3f14cf",
        "Continuing-role still-in-school flow.",
    ),
    (
        "vb8_q2021_continuing_p451",
        "psid-corpus-document-0189",
        451,
        2291,
        2292,
        "pdf_page_content_stream_raw_byte_range",
        2996348,
        3004605,
        "c3c9967126a9ad7ea1bbf4608ad9dc309f82586b4ac880ad605c5440115d80f0",
        "KL84 continuation checkpoint and current-school item.",
    ),
    (
        "vb8_q2023_new_p442",
        "psid-corpus-document-0192",
        442,
        466,
        1091,
        "pdf_page_content_stream_raw_byte_range",
        3540191,
        3545520,
        "30fd64cdf529d9598324cce37a2d6fe81e863812d2ac9b12754ce4a4f35208e7",
        "New-role upstream college still-in-school branch.",
    ),
    (
        "vb8_q2023_new_p443",
        "psid-corpus-document-0192",
        443,
        467,
        1092,
        "pdf_page_content_stream_raw_byte_range",
        3545599,
        3557481,
        "e978bb63909476d51e770ae32cb84bbfd2fb6ed0990ef1587d0b26f8795ec30e",
        "KL61A and its checkpoint complete the new-role composite.",
    ),
    (
        "vb8_q2023_role_p445",
        "psid-corpus-document-0192",
        445,
        469,
        1094,
        "pdf_page_content_stream_raw_byte_range",
        3566386,
        3573872,
        "0c3381ce11830e88e72635dd864c6443ee138fdb0276c1ae86ebd077e4762c21",
        "Role-status split separates new and continuing branches.",
    ),
    (
        "vb8_q2023_continuing_p457",
        "psid-corpus-document-0192",
        457,
        481,
        1106,
        "pdf_page_content_stream_raw_byte_range",
        3639421,
        3645975,
        "2ab48b343dcf5bee8d4e4831f40dd9ce71faa67587e371fa260fffaa9d3cb726",
        "Continuing-role still-in-school flow.",
    ),
    (
        "vb8_q2023_continuing_p458",
        "psid-corpus-document-0192",
        458,
        482,
        1107,
        "pdf_page_content_stream_raw_byte_range",
        3646053,
        3655056,
        "0b0d44dd7a76c181c91c43b09ef05f57f2daada7388d05986c010dc318cd533c",
        "KL84 continuation checkpoint and current-school item.",
    ),
)

PRE2013_QUESTIONNAIRES = tuple(
    list(
        zip(
            range(1968, 1998),
            (
                "q68.pdf",
                "q69.pdf",
                "q70.pdf",
                "q71.pdf",
                "q72.pdf",
                "q73.pdf",
                "q74.pdf",
                "q75.pdf",
                "q76.pdf",
                "q77.pdf",
                "q78.pdf",
                "q79.pdf",
                "q80.pdf",
                "q81.pdf",
                "q82.pdf",
                "q83.pdf",
                "q84.pdf",
                "q85.pdf",
                "q86.pdf",
                "q87.pdf",
                "q88.pdf",
                "q89.pdf",
                "q90.pdf",
                "q91.pdf",
                "q92.pdf",
                "q93.pdf",
                "q94.pdf",
                "q95.pdf",
                "q96.pdf",
                "q97.pdf",
            ),
            strict=True,
        )
    )
    + list(
        zip(
            (1999, 2001, 2003, 2005, 2007, 2009, 2011),
            (
                "q1999.pdf",
                "q2001.pdf",
                "q2003.pdf",
                "q2005.pdf",
                "q2007.pdf",
                "q2009.pdf",
                "q2011.pdf",
            ),
            strict=True,
        )
    )
)


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _strictly_parsed_document(raw: bytes, label: str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(
                    f"{label} contains duplicate object key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> Any:
        raise ValueError(f"{label} contains non-finite constant {token}")

    def finite_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise ValueError(f"{label} contains non-finite number {token}")
        if decimal.Decimal(token) != decimal.Decimal(str(value)):
            raise ValueError(f"{label} contains inexact number {token}")
        return value

    try:
        text = raw.decode("utf-8")
        if text.startswith("\ufeff"):
            raise ValueError(f"{label} contains a leading U+FEFF BOM")
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
            parse_float=finite_float,
        )
    except (
        UnicodeError,
        ValueError,
        OverflowError,
        RecursionError,
        decimal.DecimalException,
    ) as error:
        raise ValueError(
            f"{label} is not a uniquely parseable JSON document"
        ) from error


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _frozen_inputs() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for input_id, spec in FROZEN_INPUTS.items():
        raw = (ROOT / spec["committed_path"]).read_bytes()
        if len(raw) != spec["size_bytes"] or _sha256(raw) != spec["sha256"]:
            raise ValueError(f"{input_id} frozen identity drift")
        value = _strictly_parsed_document(raw, input_id)
        if value.get("schema_version") != spec["schema_version"]:
            raise ValueError(f"{input_id} schema identity drift")
        values[input_id] = value
    return values


def _source_artifact_identities() -> list[dict[str, Any]]:
    return [
        {"source_artifact_id": input_id, **spec}
        for input_id, spec in FROZEN_INPUTS.items()
    ]


def _registration_documents(
    registration: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    accepted_registry = registration.get("accepted_authority_registry")
    if (
        registration.get("registration_status") != "pass"
        or registration.get("document_candidate_count") != 456
        or registration.get("verified_document_count") != 456
        or registration.get("failed_document_count") != 0
        or registration.get("failed_document_ids") != []
        or not isinstance(accepted_registry, Mapping)
        or accepted_registry.get("schema_version")
        != "psid_questionnaire_corpus_authority_registry.v1"
        or accepted_registry.get("artifact_id")
        != "psid_questionnaire_corpus_authority_registry.v1"
        or accepted_registry.get("document_count") != 456
        or accepted_registry.get("unique_document_identity_count") != 455
        or accepted_registry.get("authority_manifest_pointer")
        != "/document_candidates"
        or accepted_registry.get("ordered_document_ids")
        != registration.get("ordered_document_ids")
        or accepted_registry.get("document_rows_sha256")
        != registration.get("document_rows_sha256")
        or accepted_registry.get("status") != "pass"
    ):
        raise ValueError("corpus registration disposition drift")
    documents = registration.get("document_candidates")
    if not isinstance(documents, list):
        raise ValueError("registration document domain missing")
    by_id = {row["source_document_id"]: row for row in documents}
    if len(by_id) != len(documents):
        raise ValueError("registration document IDs are not unique")
    return by_id


def _verified_document_bytes(
    capture_root: Path,
    document: Mapping[str, Any],
) -> bytes:
    if document.get("availability") != "verified":
        raise ValueError(
            f"{document.get('source_document_id')} is not verified"
        )
    filename = document["on_disk_filename"]
    if Path(filename).name != filename or filename in {".", ".."}:
        raise ValueError("unsafe staged filename")
    path = capture_root / filename
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{filename} is unavailable or symlinked")
    raw = path.read_bytes()
    if (
        len(raw) != document["expected_size_bytes"]
        or _sha256(raw) != document["expected_sha256"]
    ):
        raise ValueError(f"{filename} staged identity drift")
    return raw


def _expected_passage_locators(
    documents: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        (
            locator_id,
            document_id,
            page_number,
            page_object,
            contents_object,
            location_type,
            byte_start,
            byte_end,
            range_sha256,
            semantic_anchor,
        ) = spec
        document = documents[document_id]
        rows.append(
            {
                "locator_id": locator_id,
                "location_type": location_type,
                "source_document_id": document_id,
                "filename": document["digest_row_filename"],
                "full_file_sha256": document["expected_sha256"],
                "size_bytes": document["expected_size_bytes"],
                "pdf_page_number_1_based": page_number,
                "pdf_page_object_number": page_object,
                "pdf_contents_object_number": contents_object,
                "byte_start": byte_start,
                "byte_end": byte_end,
                "range_sha256": range_sha256,
                "semantic_anchor": semantic_anchor,
            }
        )
    return rows


def _passage_locators(
    capture_root: Path,
    documents: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = _expected_passage_locators(documents)
    raw_cache: dict[str, bytes] = {}
    for row in rows:
        document_id = row["source_document_id"]
        document = documents[document_id]
        if document_id not in raw_cache:
            raw_cache[document_id] = _verified_document_bytes(
                capture_root, document
            )
        raw = raw_cache[document_id]
        byte_start = row["byte_start"]
        byte_end = row["byte_end"]
        locator_id = row["locator_id"]
        if not 0 <= byte_start < byte_end <= len(raw):
            raise ValueError(f"{locator_id} byte range outside source")
        if _sha256(raw[byte_start:byte_end]) != row["range_sha256"]:
            raise ValueError(f"{locator_id} range identity drift")
        page_object = row["pdf_page_object_number"]
        contents_object = row["pdf_contents_object_number"]
        if f"{page_object} 0 obj".encode() not in raw:
            raise ValueError(f"{locator_id} page object missing")
        if f"{contents_object} 0 obj".encode() not in raw:
            raise ValueError(f"{locator_id} contents object missing")
    return rows


def _questionnaire_rows(
    documents: Mapping[str, Mapping[str, Any]],
) -> list[tuple[int, Mapping[str, Any]]]:
    by_name = {row["digest_row_filename"]: row for row in documents.values()}
    rows: list[tuple[int, Mapping[str, Any]]] = []
    for wave, filename in PRE2013_QUESTIONNAIRES:
        document = by_name.get(filename)
        if document is None or document["availability"] != "verified":
            raise ValueError(
                f"pre-2013 questionnaire {filename} is not verified"
            )
        rows.append((wave, document))
    if len(rows) != 37:
        raise ValueError("pre-2013 questionnaire domain drift")
    return rows


def _expected_whole_document_locators(
    questionnaire_rows: list[tuple[int, Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wave, document in questionnaire_rows:
        rows.append(
            {
                "locator_id": f"questionnaire_full_document_{wave}",
                "location_type": "whole_document_exact_file_range",
                "source_document_id": document["source_document_id"],
                "filename": document["digest_row_filename"],
                "interview_wave": wave,
                "full_file_sha256": document["expected_sha256"],
                "size_bytes": document["expected_size_bytes"],
                "byte_start": 0,
                "byte_end": document["expected_size_bytes"],
                "range_sha256": document["expected_sha256"],
                "pdf_page_domain": "all_pages_and_flow_branches",
            }
        )
    return rows


def _whole_document_locators(
    capture_root: Path,
    questionnaire_rows: list[tuple[int, Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    rows = _expected_whole_document_locators(questionnaire_rows)
    by_id = {
        document["source_document_id"]: document
        for _, document in questionnaire_rows
    }
    for row in rows:
        document = by_id[row["source_document_id"]]
        raw = _verified_document_bytes(capture_root, document)
        if (
            len(raw) != row["size_bytes"]
            or _sha256(raw) != row["range_sha256"]
        ):
            raise ValueError(
                f"{row['locator_id']} whole-document identity drift"
            )
    return rows


def _membership_fact_extractions(
    membership: Mapping[str, Any],
) -> list[dict[str, Any]]:
    facts = membership.get("facts")
    if not isinstance(facts, list) or len(facts) != 30:
        raise ValueError("membership v2 fact domain drift")
    rows: list[dict[str, Any]] = []
    for index, fact in enumerate(facts):
        rows.append(
            {
                "source_pointer": f"/facts/{index}",
                "fact_id": fact["fact_id"],
                "requirement": fact["requirement"],
                "retained_v2_verdict": fact["verdict"],
                "source_disposition": "does_not_establish_membership_facts",
                "authority_scope": "psid_variable_semantics_only",
                "evidence_locator_ids": [],
                "reason": "The predicate concerns SSA B2/B11 publication membership; PSID questionnaire and codebook bytes cannot establish it.",
            }
        )
    return rows


def _target_residual(
    psid_adjudication: Mapping[str, Any], residual_id: str
) -> tuple[int, Mapping[str, Any]]:
    index = TARGET_RESIDUAL_INDEXES[residual_id]
    residuals = psid_adjudication.get("registration_required_residuals")
    if not isinstance(residuals, list) or index >= len(residuals):
        raise ValueError("PSID residual domain drift")
    residual = residuals[index]
    if residual.get("residual_id") != residual_id:
        raise ValueError(f"PSID residual pointer drift for {residual_id}")
    return index, residual


def _residual_extractions(
    psid_adjudication: Mapping[str, Any],
) -> list[dict[str, Any]]:
    vb5_passages = [
        row[0] for row in PASSAGE_SPECS if row[0].startswith("vb5_")
    ]
    q77_q78 = [
        row[0]
        for row in PASSAGE_SPECS
        if row[0].startswith(("vb6_q77_", "vb6_q78_"))
    ]
    definitions = (
        (
            "V-B5",
            "wave1968_ry1968_1974_early_totals:occupation_industry_attachment_closure",
            "established_by_questionnaire_corpus",
            vb5_passages,
            ["vb5_1968_1975_unsupported_slot_absence"],
            [
                "Exact three-digit occupation and industry meanings are supplied.",
                "The selected-sample and main/last/usual-job attachment is supplied.",
                "The complete 1968-1975 questionnaire domain supports structural absence of unsupported secondary-job industry and spouse-secondary slots.",
            ],
            [],
        ),
        (
            "V-B6",
            "ry1975_1977_spouse_concept_seam:V-B6:V5289_V5788_concept",
            "established_by_questionnaire_corpus",
            [
                "vb6_1977_worksheet_p55",
                "vb6_1977_label_p84",
                "vb6_1978_worksheet_p74",
                "vb6_1978_label_p232",
                "vb6_1977_qxq_p54",
                "vb6_1978_qxq_p70",
            ],
            [],
            [
                "V5289 and V5788 are Wife wage/labor-income totals; family-business labor and asset components are handled separately with duplicate-avoidance instructions."
            ],
            [],
        ),
        (
            "V-B6",
            "ry1975_1977_spouse_concept_seam:V-B6:1977_1978_spouse_current_job_context_absence",
            "established_by_questionnaire_corpus",
            q77_q78,
            ["vb6_1977_1978_wife_section_exhaustion"],
            [
                "The complete 1977 and 1978 Wife employment sections contain annual work, occupation, business, weeks, and hours but no equivalent employer/self/government/incorporation context branch."
            ],
            [],
        ),
        (
            "V-B6",
            "ry1975_1977_spouse_concept_seam:V-B6:government_level_absence",
            "established_by_questionnaire_corpus",
            ["vb6_q76_government_p46"],
            [],
            [
                "The 1976 spouse branch asks one combined federal/state/local government yes-no question and has no level follow-up."
            ],
            [],
        ),
        (
            "V-B6",
            "ry1975_1977_spouse_concept_seam:V-B6:secondary_job_attachment_and_absence",
            "partially_established_required_fact_unestablished",
            ["vb6_q76_income_p25", "vb6_q76_extra_job_p50", *q77_q78],
            ["vb6_1977_1978_wife_section_exhaustion"],
            [
                "The 1976 Wife secondary-job branch is attached to work beyond the main job during 1975; equivalent 1977-1978 Wife branches are structurally absent."
            ],
            [
                "No captured questionnaire or editing instruction supplies the exact allocation from V4901-V4906 components to annual V4379/V5289/V5788 totals."
            ],
        ),
        (
            "V-B8",
            "ry2002_2014_modern_bc_de:V-B8:branch_freshness",
            "established_by_questionnaire_corpus",
            [
                row[0]
                for row in PASSAGE_SPECS
                if row[0].startswith(("vb8_q2013_", "vb8_q2015_"))
            ],
            [],
            [
                "The 2013 role universe excludes a new-role general-school question and defines a freshness-safe continuing-role KL74/KL84 composite; 2015 adds the KL61A new-role composite with checkpoint bypass."
            ],
            [],
        ),
        (
            "V-B8",
            "ry2002_2014_modern_bc_de:V-B8:pre_2013_questionnaire_absence_proof",
            "established_by_questionnaire_corpus",
            [],
            ["vb8_pre_2013_current_regular_school_absence"],
            [
                "The complete 37-wave 1968-2011 official-family-questionnaire domain contains no current Head/Wife general regular-school predicate; college still-in-school, child status, and retrospective education items are excluded from that predicate."
            ],
            [],
        ),
        (
            "V-B8",
            "ry2015_2022_exclusion_lineage:V-B8:branch_freshness",
            "established_by_questionnaire_corpus",
            [
                row[0]
                for row in PASSAGE_SPECS
                if row[0].startswith(
                    ("vb8_q2017_", "vb8_q2019_", "vb8_q2021_", "vb8_q2023_")
                )
            ],
            [],
            [
                "The 2017-2023 flows repeat role-specific new-role and continuing-role checkpoint composites that prevent stale carried-forward school answers."
            ],
            [],
        ),
    )
    rows: list[dict[str, Any]] = []
    for (
        family_id,
        residual_id,
        verdict,
        locators,
        absence_ids,
        findings,
        remaining,
    ) in definitions:
        index, residual = _target_residual(psid_adjudication, residual_id)
        rows.append(
            {
                "family_id": family_id,
                "source_pointer": f"/registration_required_residuals/{index}",
                "source_residual_sha256": _sha256(
                    canonical_json_bytes(residual)
                ),
                "residual_id": residual_id,
                "source_missing_fact": residual["missing_fact"],
                "source_status": residual["status"],
                "evidentiary_verdict": verdict,
                "evidence_locator_ids": locators,
                "absence_proof_ids": absence_ids,
                "established_findings": findings,
                "remaining_unestablished_facts": remaining,
                "operative_effect": "none_accepted_corpus_and_frozen_design_domain",
            }
        )
    return rows


def _absence_proofs(
    questionnaire_rows: list[tuple[int, Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    locator_by_wave = {
        wave: f"questionnaire_full_document_{wave}"
        for wave, _ in questionnaire_rows
    }
    return [
        {
            "absence_proof_id": "vb5_1968_1975_unsupported_slot_absence",
            "conclusion": "No supported secondary-job industry or spouse-secondary occupation/industry slot exists in the 1968-1975 official questionnaires beyond the attachment table's enumerated cells.",
            "searched_interview_waves": list(range(1968, 1976)),
            "searched_locator_ids": [
                locator_by_wave[wave] for wave in range(1968, 1976)
            ],
            "search_domain": "Every page and flow branch of each official family questionnaire, reconciled to the retrospective attachment table.",
            "search_implementation": "questionnaire_whole_document_visual_and_flow_review_v1",
            "excluded_near_matches": [
                "head secondary-job occupation without industry",
                "main/last/usual-job fields",
                "spouse main-job fields",
            ],
        },
        {
            "absence_proof_id": "vb6_1977_1978_wife_section_exhaustion",
            "conclusion": "The exhaustive 1977-1978 Wife employment sections contain neither the 1976 current-job context branch nor an equivalent Wife secondary-job branch.",
            "searched_interview_waves": [1977, 1978],
            "searched_locator_ids": [
                row[0]
                for row in PASSAGE_SPECS
                if row[0].startswith(("vb6_q77_", "vb6_q78_"))
            ],
            "search_domain": "Every page and flow exit in the bounded Wife Section G employment sections.",
            "search_implementation": "questionnaire_section_visual_and_flow_review_v1",
            "excluded_near_matches": [
                "annual work and occupation",
                "business type",
                "weeks and hours",
                "Head secondary-job branch",
            ],
        },
        {
            "absence_proof_id": "vb8_pre_2013_current_regular_school_absence",
            "conclusion": "No current Head/Wife general regular-school predicate exists before 2013 in the complete official-family-questionnaire domain.",
            "searched_interview_waves": [
                wave for wave, _ in questionnaire_rows
            ],
            "searched_locator_ids": [
                locator_by_wave[wave] for wave, _ in questionnaire_rows
            ],
            "search_domain": "Every page and flow branch of all 37 official family questionnaires from 1968 through 2011, including biennial waves after 1997.",
            "search_implementation": "questionnaire_whole_document_visual_and_flow_review_v1",
            "target_predicate": "Head/Wife current regular-school or current general-enrollment item with role and universe attachment.",
            "excluded_near_matches": [
                "college last-attendance still-in-school codes 96/9996",
                "child or student-status items",
                "retrospective education",
                "new-role college background",
            ],
        },
    ]


def _family_summary(
    residual_rows: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family_id in ("V-B5", "V-B6", "V-B8"):
        selected = [
            row for row in residual_rows if row["family_id"] == family_id
        ]
        closed = sum(
            row["evidentiary_verdict"] == "established_by_questionnaire_corpus"
            for row in selected
        )
        partial = sum(
            row["evidentiary_verdict"]
            == "partially_established_required_fact_unestablished"
            for row in selected
        )
        rows.append(
            {
                "family_id": family_id,
                "targeted_residual_count": len(selected),
                "evidentially_closed_count": closed,
                "remaining_partial_count": partial,
                "remaining_residual_count": partial,
                "operative_verdict": "registration_required",
            }
        )
    return rows


def _content_sha256(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return _sha256(canonical_json_bytes(preimage))


def build_extraction(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    inputs = _frozen_inputs()
    registration = inputs["corpus_registration_attempt"]
    documents = _registration_documents(registration)
    questionnaire_rows = _questionnaire_rows(documents)
    passage_locators = _passage_locators(capture_root, documents)
    whole_document_locators = _whole_document_locators(
        capture_root, questionnaire_rows
    )
    residual_rows = _residual_extractions(
        inputs["psid_codebook_inventory_adjudication"]
    )
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "source_artifact_identities": _source_artifact_identities(),
        "authority_disposition": copy.deepcopy(AUTHORITY_DISPOSITION),
        "extraction_method": copy.deepcopy(EXTRACTION_METHOD),
        "passage_locators": passage_locators,
        "whole_document_locators": whole_document_locators,
        "absence_proofs": _absence_proofs(questionnaire_rows),
        "membership_fact_extractions": _membership_fact_extractions(
            inputs["membership_adjudication_v2"]
        ),
        "psid_vb_residual_extractions": residual_rows,
        "family_extraction_summary": _family_summary(residual_rows),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
            "structural_status": "pass",
            "source_byte_ranges_verified": True,
        },
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    validate_extraction(value, capture_root)
    return value


def validate_structure(value: Mapping[str, Any]) -> None:
    expected_keys = {
        "schema_version",
        "artifact_id",
        "source_artifact_identities",
        "authority_disposition",
        "extraction_method",
        "passage_locators",
        "whole_document_locators",
        "absence_proofs",
        "membership_fact_extractions",
        "psid_vb_residual_extractions",
        "family_extraction_summary",
        "integrity",
    }
    if set(value) != expected_keys:
        raise ValueError("extraction top-level schema drift")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["artifact_id"] != ARTIFACT_ID
    ):
        raise ValueError("extraction identity drift")
    inputs = _frozen_inputs()
    documents = _registration_documents(inputs["corpus_registration_attempt"])
    questionnaire_rows = _questionnaire_rows(documents)
    if value["source_artifact_identities"] != _source_artifact_identities():
        raise ValueError("extraction source-artifact identity drift")
    if value["authority_disposition"] != AUTHORITY_DISPOSITION:
        raise ValueError("extraction authority disposition drift")
    if value["extraction_method"] != EXTRACTION_METHOD:
        raise ValueError("extraction method drift")
    if value["passage_locators"] != _expected_passage_locators(documents):
        raise ValueError("passage locator rows drift")
    passage_ids = [row["locator_id"] for row in value["passage_locators"]]
    expected_passage_ids = [row[0] for row in PASSAGE_SPECS]
    if passage_ids != expected_passage_ids or len(passage_ids) != len(
        set(passage_ids)
    ):
        raise ValueError("passage locator domain drift")
    whole_rows = value["whole_document_locators"]
    if whole_rows != _expected_whole_document_locators(questionnaire_rows):
        raise ValueError("whole-questionnaire locator rows drift")
    if len(whole_rows) != 37 or [
        row["interview_wave"] for row in whole_rows
    ] != [row[0] for row in PRE2013_QUESTIONNAIRES]:
        raise ValueError("whole-questionnaire locator domain drift")
    all_locator_ids = set(passage_ids) | {
        row["locator_id"] for row in whole_rows
    }
    absence_rows = value["absence_proofs"]
    if absence_rows != _absence_proofs(questionnaire_rows):
        raise ValueError("absence-proof rows drift")
    if [row["absence_proof_id"] for row in absence_rows] != [
        "vb5_1968_1975_unsupported_slot_absence",
        "vb6_1977_1978_wife_section_exhaustion",
        "vb8_pre_2013_current_regular_school_absence",
    ]:
        raise ValueError("absence-proof domain drift")
    for absence in absence_rows:
        if (
            not absence["searched_locator_ids"]
            or not set(absence["searched_locator_ids"]) <= all_locator_ids
        ):
            raise ValueError(
                f"{absence['absence_proof_id']} locator domain failure"
            )
    facts = value["membership_fact_extractions"]
    if facts != _membership_fact_extractions(
        inputs["membership_adjudication_v2"]
    ):
        raise ValueError("membership extraction rows drift")
    if len(facts) != 30 or any(
        row["source_disposition"] != "does_not_establish_membership_facts"
        or row["authority_scope"] != "psid_variable_semantics_only"
        or row["evidence_locator_ids"]
        for row in facts
    ):
        raise ValueError("membership extraction scope drift")
    residuals = value["psid_vb_residual_extractions"]
    if residuals != _residual_extractions(
        inputs["psid_codebook_inventory_adjudication"]
    ):
        raise ValueError("PSID residual extraction rows drift")
    if [row["residual_id"] for row in residuals] != list(
        TARGET_RESIDUAL_INDEXES
    ):
        raise ValueError("target residual domain drift")
    allowed_verdicts = {
        "established_by_questionnaire_corpus",
        "partially_established_required_fact_unestablished",
    }
    absence_ids = {row["absence_proof_id"] for row in absence_rows}
    for row in residuals:
        if row["evidentiary_verdict"] not in allowed_verdicts:
            raise ValueError("residual evidentiary verdict drift")
        if not set(row["evidence_locator_ids"]) <= all_locator_ids:
            raise ValueError("residual evidence locator drift")
        if not set(row["absence_proof_ids"]) <= absence_ids:
            raise ValueError("residual absence-proof locator drift")
        if row["evidentiary_verdict"].startswith("partially_") != bool(
            row["remaining_unestablished_facts"]
        ):
            raise ValueError("residual verdict/remaining-fact mismatch")
        if (
            row["operative_effect"]
            != "none_accepted_corpus_and_frozen_design_domain"
        ):
            raise ValueError("residual operative-effect drift")
    if value["family_extraction_summary"] != _family_summary(residuals):
        raise ValueError("family extraction summary drift")
    integrity = value["integrity"]
    if set(integrity) != {
        "canonicalization",
        "content_sha256",
        "structural_status",
        "source_byte_ranges_verified",
    }:
        raise ValueError("extraction integrity schema drift")
    if (
        integrity["canonicalization"] != CANONICALIZATION
        or integrity["structural_status"] != "pass"
        or integrity["source_byte_ranges_verified"] is not True
        or integrity["content_sha256"] != _content_sha256(value)
    ):
        raise ValueError("extraction integrity failure")


def validate_extraction(
    value: Mapping[str, Any], capture_root: Path = DEFAULT_CAPTURE_ROOT
) -> None:
    validate_structure(value)
    inputs = _frozen_inputs()
    documents = _registration_documents(inputs["corpus_registration_attempt"])
    expected_passages = _passage_locators(capture_root, documents)
    questionnaire_rows = _questionnaire_rows(documents)
    expected_whole = _whole_document_locators(capture_root, questionnaire_rows)
    expected_membership = _membership_fact_extractions(
        inputs["membership_adjudication_v2"]
    )
    expected_residuals = _residual_extractions(
        inputs["psid_codebook_inventory_adjudication"]
    )
    if value["passage_locators"] != expected_passages:
        raise ValueError("passage locator reproduction drift")
    if value["whole_document_locators"] != expected_whole:
        raise ValueError("whole-document locator reproduction drift")
    if value["membership_fact_extractions"] != expected_membership:
        raise ValueError("membership fact extraction drift")
    if value["psid_vb_residual_extractions"] != expected_residuals:
        raise ValueError("PSID residual extraction drift")
    if value["absence_proofs"] != _absence_proofs(questionnaire_rows):
        raise ValueError("absence-proof reproduction drift")


def render(capture_root: Path = DEFAULT_CAPTURE_ROOT) -> bytes:
    return canonical_json_bytes(build_extraction(capture_root))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT
    )
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render(args.capture_root)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != rendered:
            raise SystemExit(f"artifact drift: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
