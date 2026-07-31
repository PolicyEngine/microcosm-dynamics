"""Source-only audit of the staged PSID family dictionaries.

This module deliberately does not import the family reader, a correction
crosswalk, or any adjudication registry.  Its only inputs are the staged
family source files.  The ``.do`` and ``.sps`` dictionaries establish the
physical layout, while the raw ``.txt`` files are byte-pinned without being
parsed.  That separation enforces the independent-domain rule in
covered-earnings design section 4.2.

The staged setup dictionaries pin physical fields, short labels, and
fixed-width coordinates.  All 43 registered family codebooks add complete
displayed descriptions and value maps, each bound to authenticated PDF page
content-stream byte ranges.  Ancillary era artifacts preserve those positive
facts independently of the reader and correction crosswalk.

The sources still do not ratify ``psid_questionnaire_slot_specs.v1``: they
lack exact fixed-width token grammar for every sentinel, complete
questionnaire slot attachment, and questionnaire-exhaustive absence proofs.
The public builders therefore emit reproducible positive evidence and an
explicit registration-required adjudication while refusing to manufacture a
partial official inventory.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import zipfile
import zlib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA_VERSION = (
    "psid_questionnaire_dictionary_inventory.registration_required.v1"
)
ARTIFACT_ID = SCHEMA_VERSION
SLOT_SPECS_ID = "psid_questionnaire_slot_specs.v1"
SOURCE_INVENTORY_ID = "psid_covered_earnings_source_field_inventory.v1"
CODEBOOK_EVIDENCE_SCHEMA_VERSION = "psid_codebook_field_evidence.v1"
CODEBOOK_ADJUDICATION_SCHEMA_VERSION = (
    "psid_codebook_inventory_adjudication.v1"
)
PDF_TEXT_EXTRACTION_TOOL = "Poppler pdftotext"
PDF_TEXT_EXTRACTION_VERSION = "26.04.0"

INTERVIEW_WAVES: tuple[int, ...] = (
    *range(1968, 1998),
    *range(1999, 2024, 2),
)
FORMAT_MAP_IDENTITIES: tuple[tuple[int, int, int, int, str], ...] = (
    (
        2021,
        3_212,
        25_263,
        2_460,
        "39a29fa289ddd41852214e30bb7d77e41534c41efd21a75a68633282e808cfd2",
    ),
    (
        2023,
        3_078,
        23_374,
        2_327,
        "d58883d52bb8a76b64206ae36093563e6cbb9d6c542de2bb3189f0e4b70cc2f2",
    ),
)
FORMAT_MAP_WAVES: tuple[int, ...] = tuple(
    row[0] for row in FORMAT_MAP_IDENTITIES
)
FORMAT_SOURCE_IDENTITIES: tuple[
    tuple[int, str, str, str, int, str, str], ...
] = (
    (
        2021,
        "psid-family-2021-stata_value_labels",
        "stata_value_labels",
        "family/2021/FAM2021ER_formats.do",
        1_531_909,
        "c227518baa7ec94ed042aadfea42c4ed5bdd1b89df11c4bf4d578f4a4dd60e38",
        "windows-1252",
    ),
    (
        2021,
        "psid-family-2021-spss_value_labels",
        "spss_value_labels",
        "family/2021/FAM2021ER_formats.sps",
        1_151_352,
        "863f151a4cab1282060aa3bfe4f6648bbbc1822e6f739bcfd502ff13b40a952c",
        "windows-1252",
    ),
    (
        2023,
        "psid-family-2023-stata_value_labels",
        "stata_value_labels",
        "family/2023/FAM2023ER_formats.do",
        1_427_122,
        "7ecaa861c7e8afd80e579a0d04c9a8040ffeae42ad4a174acd8a8a0e558171eb",
        "windows-1252",
    ),
    (
        2023,
        "psid-family-2023-spss_value_labels",
        "spss_value_labels",
        "family/2023/FAM2023ER_formats.sps",
        1_084_066,
        "89e4f2be4bea66fe83e0f11682bdcfab2590c01310bd697833846377d64a59f2",
        "windows-1252",
    ),
)
CODEBOOK_AUTHORITY_FILE_COUNT = 43
CODEBOOK_AUTHORITY_TOTAL_SIZE_BYTES = 109_680_641
CODEBOOK_AUTHORITY_MANIFEST_SHA256 = (
    "b0ff4b6a09b5cb664ecd9c99a2de61f5c8a47cdb48889cd19f64f77bca11fd34"
)
SOURCE_AUTHORITY_FILE_COUNT = 176
SOURCE_AUTHORITY_TOTAL_SIZE_BYTES = 1_514_409_083
SOURCE_AUTHORITY_MANIFEST_SHA256 = (
    "52906f7a36955d20282dbce2dd4bac260395d3ce3961bd0baf763290c3152116"
)
CODEBOOK_TOTAL_FIELD_COUNT = 89_599
CODEBOOK_TOTAL_PAGE_COUNT = 29_897
CODEBOOK_TOTAL_MAP_ROW_COUNT = 479_345
CODEBOOK_TOTAL_CLOSED_RANGE_COUNT = 36_950
CODEBOOK_TOTAL_DESCRIPTION_LINE_COUNT = 219_518
FROZEN_INVENTORY_WAVE_ROWS_SHA256 = (
    "dd91873b7964afea577e094a2598e21ec8d3d14f977ab6ea688913d05045b2ab"
)
POST_CUTOFF_INVENTORY_WAVES: tuple[int, ...] = (
    2015,
    2017,
    2019,
    2021,
    2023,
)
CODEBOOK_ADJUDICATION_CONTENT_SHA256 = (
    "c8797f312ee24c63c00a4610106bae8a7c446a5a2158b953e38bda4b018e7496"
)
CODEBOOK_ERA_SPECS: tuple[tuple[str, tuple[int, ...]], ...] = (
    (
        "wave1968_ry1968_1974_early_totals",
        tuple(range(1968, 1976)),
    ),
    (
        "ry1975_1977_spouse_concept_seam",
        tuple(range(1976, 1979)),
    ),
    (
        "ry1978_1992_pre_er_totals",
        tuple(range(1979, 1994)),
    ),
    (
        "ry1993_2001_er_transition",
        (1994, 1995, 1996, 1997, 1999, 2001),
    ),
    (
        "ry2002_2014_modern_bc_de",
        tuple(range(2003, 2016, 2)),
    ),
    (
        "ry2015_2022_exclusion_lineage",
        tuple(range(2017, 2024, 2)),
    ),
)
CODEBOOK_ERA_IDENTITY_COLUMNS: tuple[str, ...] = (
    "era_id",
    "field_count",
    "description_line_count",
    "code_map_row_count",
    "closed_range_count",
    "page_stream_locator_count",
    "fact_count",
    "residual_count",
    "source_authority_manifest_sha256",
    "field_evidence_keyset_sha256",
    "source_locator_keyset_sha256",
    "content_sha256",
)
CODEBOOK_ERA_IDENTITIES: tuple[tuple[Any, ...], ...] = (
    (
        "wave1968_ry1968_1974_early_totals",
        3_868,
        10_184,
        22_328,
        1_666,
        1_197,
        64,
        5,
        "60e9fce4eaf372ee691f863b7f55f5fe1c6c627440f566adc0239f15c86030c0",
        "fc1307936490598a4f38b50f549e5c37ec8185eff11f0d21583e90981e0e09d7",
        "69b1d9af907657211c55bb7a8eb68def190b2c819e37ceb74560c68d7e52cbf1",
        "7eee6a88383df6aea6c4cf11a7190eeb51d1736ee469bd17439dd001140bf247",
    ),
    (
        "ry1975_1977_spouse_concept_seam",
        1_838,
        3_697,
        10_573,
        796,
        557,
        32,
        7,
        "962e7e97190906063f4f54c8a6b09704e14ed307bb5ac5a59d93b9bf83194abe",
        "f85f793d89bcbebd1f0c9a0e261296f583aca8bd7d2ee20a8b7973a7aadc9e4c",
        "7cc14d09f3b7391eb3ddd5967654ff02b269bc9a5db055c7d9f962e84dcad230",
        "a8b32316bf906ed8ac141fcaf2f871a5690ae22263562e35378b1b8f4547b7bd",
    ),
    (
        "ry1978_1992_pre_er_totals",
        15_745,
        48_103,
        88_545,
        9_230,
        5_261,
        60,
        4,
        "7f29ce21f9ab7f6f27d872716ccedf0edd83514756573d5e0e290a6404f9a987",
        "1727594490a69363ac4bb813906a1240d321f0ac31037393d438f880696dfe8c",
        "aeca075964acfdb73446f71c325b7820a131c9b28af93aadf1224eaf4ccdc240",
        "c9d7e6c8a7750688389e21930ce091cad4f4cc00ed7af40d489495afa940986b",
    ),
    (
        "ry1993_2001_er_transition",
        15_983,
        32_205,
        91_014,
        8_505,
        4_822,
        30,
        5,
        "e2c7c19047e595ec3472e022bc3bf196836a3cec371b6728322cf6192c51f7ac",
        "0145cad9993636651b3e4ef3cc3357b0e78bbf9e4350ada135cab5345f388f87",
        "159f64ea85e2ae5b0c84f1d1468278eb6854d6b715f5677d68f2bafcac4ccdcd",
        "cf48b3d4573f8f80b90f43eee6be2e076b821348c2431c9197c3f1ce1b1e8913",
    ),
    (
        "ry2002_2014_modern_bc_de",
        33_154,
        77_828,
        166_010,
        10_624,
        11_096,
        1_866,
        9,
        "d08cef8b0624cf2a162474ee83f4db0686c027df760fcf95267b9d93930445b2",
        "0b213f615da11804c18f870dd15a75f70c434fccd51a7e0aca77d0729be361d1",
        "006bf4bb002c4634db3b6c47a209cccd2fbe7319c8525701a6e39ea3695d38fb",
        "65e64050205e97cff41abcb683ab5f8b2d0f2af63d02d951cfe614835a8fd534",
    ),
    (
        "ry2015_2022_exclusion_lineage",
        19_011,
        47_501,
        100_875,
        6_129,
        6_964,
        1_064,
        8,
        "c92a0be88caf610d16ae97aa52ab0106f559e33dc678f0a97ec5385ff437254d",
        "8b8c62400f6f41ea0008340664b43c0f3105e3a1a5861cb3372dc7fff13f67f1",
        "e0d060bf924b0d3748b12ea384c43a79e8caebb5422ac48ef67b2fc78831423f",
        "217d0a7e09ff5f47e31dfd87f893bc1d6551c6fc2f09e2ba2fcf33497b753d59",
    ),
)
EARLY_ROLE_TOTAL_FIELDS: tuple[tuple[int, str, str], ...] = (
    (1968, "head_or_reference_person", "V74"),
    (1968, "spouse_or_partner", "V75"),
    (1969, "head_or_reference_person", "V514"),
    (1969, "spouse_or_partner", "V516"),
    (1970, "head_or_reference_person", "V1196"),
    (1970, "spouse_or_partner", "V1198"),
    (1971, "head_or_reference_person", "V1897"),
    (1971, "spouse_or_partner", "V1899"),
    (1972, "head_or_reference_person", "V2498"),
    (1972, "spouse_or_partner", "V2500"),
    (1973, "head_or_reference_person", "V3051"),
    (1973, "spouse_or_partner", "V3053"),
    (1974, "head_or_reference_person", "V3463"),
    (1974, "spouse_or_partner", "V3465"),
    (1975, "head_or_reference_person", "V3863"),
    (1975, "spouse_or_partner", "V3865"),
)
EARLY_OCCUPATION_INDUSTRY_FIELDS: tuple[
    tuple[int, str, str, str, str], ...
] = (
    (1968, "head_or_reference_person", "main_job", "occupation", "V197_A"),
    (1968, "head_or_reference_person", "main_job", "industry", "V197_B"),
    (1968, "spouse_or_partner", "main_job", "occupation", "V243_A"),
    (1968, "spouse_or_partner", "main_job", "industry", "V243_B"),
    (1969, "head_or_reference_person", "main_job", "occupation", "V640_A"),
    (1969, "head_or_reference_person", "main_job", "industry", "V640_B"),
    (1969, "spouse_or_partner", "main_job", "occupation", "V609_A"),
    (1969, "spouse_or_partner", "main_job", "industry", "V609_B"),
    (1970, "head_or_reference_person", "main_job", "occupation", "V1279_A"),
    (1970, "head_or_reference_person", "main_job", "industry", "V1279_B"),
    (1970, "spouse_or_partner", "main_job", "occupation", "V1367_A"),
    (1970, "spouse_or_partner", "main_job", "industry", "V1367_B"),
    (1971, "head_or_reference_person", "main_job", "occupation", "V1984_A"),
    (1971, "head_or_reference_person", "main_job", "industry", "V1985_A"),
    (1971, "spouse_or_partner", "main_job", "occupation", "V2074_A"),
    (1971, "spouse_or_partner", "main_job", "industry", "V2075_A"),
    (1972, "head_or_reference_person", "main_job", "occupation", "V2582_A"),
    (1972, "head_or_reference_person", "main_job", "industry", "V2583_A"),
    (1972, "spouse_or_partner", "main_job", "occupation", "V2672_A"),
    (1972, "spouse_or_partner", "main_job", "industry", "V2673_A"),
    (1973, "head_or_reference_person", "main_job", "occupation", "V3115_A"),
    (1973, "head_or_reference_person", "main_job", "industry", "V3116_A"),
    (1973, "spouse_or_partner", "main_job", "occupation", "V3183_A"),
    (1973, "spouse_or_partner", "main_job", "industry", "V3184_A"),
    (1974, "head_or_reference_person", "main_job", "occupation", "V3530_A"),
    (1974, "head_or_reference_person", "main_job", "industry", "V3531_A"),
    (1974, "spouse_or_partner", "main_job", "occupation", "V3601_A"),
    (1974, "spouse_or_partner", "main_job", "industry", "V3602_A"),
    (1975, "head_or_reference_person", "main_job", "occupation", "V3968_A"),
    (1975, "head_or_reference_person", "main_job", "industry", "V3969_A"),
    (1975, "spouse_or_partner", "main_job", "occupation", "V4055_A"),
    (1975, "spouse_or_partner", "main_job", "industry", "V4056_A"),
)
EARLY_SECONDARY_OCCUPATION_FIELDS: tuple[tuple[int, str], ...] = (
    (1968, "V228"),
    (1969, "V661"),
    (1970, "V1299"),
    (1971, "V2005"),
    (1972, "V2603"),
    (1973, "V3136"),
    (1974, "V3551"),
    (1975, "V4006"),
)
SPOUSE_SEAM_AMOUNT_FIELDS: tuple[tuple[int, str, str], ...] = (
    (1976, "V4379", "mixed"),
    (1977, "V5289", "not_established_wages_only_or_mixed"),
    (1978, "V5788", "not_established_wages_only_or_mixed"),
)
SPOUSE_1976_CONTEXT_FIELDS: tuple[tuple[str, str], ...] = (
    ("V4844", "employee_self_or_mixed"),
    ("V4845", "government_employer_indicator"),
    ("V4850", "government_employer_indicator"),
    ("V4855", "incorporation"),
    ("V4858", "incorporation"),
)
SPOUSE_SEAM_SECONDARY_JOB_FIELDS: tuple[tuple[int, str, str, str], ...] = (
    (1976, "head_or_reference_person", "V4518", "secondary_job_indicator"),
    (1976, "head_or_reference_person", "V4519", "occupation"),
    (1976, "head_or_reference_person", "V4520", "extra_job_count"),
    (1976, "head_or_reference_person", "V4521", "hourly_amount"),
    (1976, "head_or_reference_person", "V4522", "weeks_worked"),
    (1976, "head_or_reference_person", "V4523", "average_hours_per_week"),
    (1976, "spouse_or_partner", "V4901", "secondary_job_indicator"),
    (1976, "spouse_or_partner", "V4902", "occupation"),
    (1976, "spouse_or_partner", "V4903", "extra_job_count"),
    (1976, "spouse_or_partner", "V4904", "hourly_amount"),
    (1976, "spouse_or_partner", "V4905", "weeks_worked"),
    (1976, "spouse_or_partner", "V4906", "average_hours_per_week"),
    (1977, "head_or_reference_person", "V5428", "secondary_job_indicator"),
    (1977, "head_or_reference_person", "V5429", "occupation"),
    (1977, "head_or_reference_person", "V5430", "extra_job_count"),
    (1977, "head_or_reference_person", "V5431", "hourly_amount"),
    (1977, "head_or_reference_person", "V5432", "weeks_worked"),
    (1977, "head_or_reference_person", "V5433", "average_hours_per_week"),
    (1978, "head_or_reference_person", "V5915", "secondary_job_indicator"),
    (1978, "head_or_reference_person", "V5916", "occupation"),
    (1978, "head_or_reference_person", "V5917", "extra_job_count"),
    (1978, "head_or_reference_person", "V5918", "hourly_amount"),
    (1978, "head_or_reference_person", "V5919", "weeks_worked"),
    (1978, "head_or_reference_person", "V5920", "average_hours_per_week"),
)
PRE_ER_ROLE_TOTAL_FIELDS: tuple[tuple[int, str, str], ...] = (
    (1979, "head_or_reference_person", "V6767"),
    (1979, "spouse_or_partner", "V6398"),
    (1980, "head_or_reference_person", "V7413"),
    (1980, "spouse_or_partner", "V6988"),
    (1981, "head_or_reference_person", "V8066"),
    (1981, "spouse_or_partner", "V7580"),
    (1982, "head_or_reference_person", "V8690"),
    (1982, "spouse_or_partner", "V8273"),
    (1983, "head_or_reference_person", "V9376"),
    (1983, "spouse_or_partner", "V8881"),
    (1984, "head_or_reference_person", "V11023"),
    (1984, "spouse_or_partner", "V10263"),
    (1985, "head_or_reference_person", "V12372"),
    (1985, "spouse_or_partner", "V11404"),
    (1986, "head_or_reference_person", "V13624"),
    (1986, "spouse_or_partner", "V12803"),
    (1987, "head_or_reference_person", "V14671"),
    (1987, "spouse_or_partner", "V13905"),
    (1988, "head_or_reference_person", "V16145"),
    (1988, "spouse_or_partner", "V14920"),
    (1989, "head_or_reference_person", "V17534"),
    (1989, "spouse_or_partner", "V16420"),
    (1990, "head_or_reference_person", "V18878"),
    (1990, "spouse_or_partner", "V17836"),
    (1991, "head_or_reference_person", "V20178"),
    (1991, "spouse_or_partner", "V19136"),
    (1992, "head_or_reference_person", "V21484"),
    (1992, "spouse_or_partner", "V20436"),
    (1993, "head_or_reference_person", "V23323"),
    (1993, "spouse_or_partner", "V23324"),
)
ENROLLMENT_REGULAR_SCHOOL_FIELDS: tuple[tuple[int, str, str, str], ...] = (
    (2013, "spouse_or_partner", "continuing_role_update", "ER57616"),
    (2013, "head_or_reference_person", "continuing_role_update", "ER57726"),
    (2015, "spouse_or_partner", "new_role_background", "ER64709"),
    (2015, "spouse_or_partner", "continuing_role_update", "ER64767"),
    (2015, "head_or_reference_person", "new_role_background", "ER64848"),
    (2015, "head_or_reference_person", "continuing_role_update", "ER64906"),
    (2017, "spouse_or_partner", "new_role_background", "ER70782"),
    (2017, "spouse_or_partner", "continuing_role_update", "ER70839"),
    (2017, "head_or_reference_person", "new_role_background", "ER70920"),
    (2017, "head_or_reference_person", "continuing_role_update", "ER70977"),
    (2019, "spouse_or_partner", "new_role_background", "ER76794"),
    (2019, "spouse_or_partner", "continuing_role_update", "ER76854"),
    (2019, "head_or_reference_person", "new_role_background", "ER76939"),
    (2019, "head_or_reference_person", "continuing_role_update", "ER76999"),
    (2021, "spouse_or_partner", "new_role_background", "ER81059"),
    (2021, "spouse_or_partner", "continuing_role_update", "ER81100"),
    (2021, "head_or_reference_person", "new_role_background", "ER81186"),
    (2021, "head_or_reference_person", "continuing_role_update", "ER81227"),
    (2023, "spouse_or_partner", "new_role_background", "ER85036"),
    (2023, "spouse_or_partner", "continuing_role_update", "ER85077"),
    (2023, "head_or_reference_person", "new_role_background", "ER85163"),
    (2023, "head_or_reference_person", "continuing_role_update", "ER85204"),
)
NEW_ROLE_ENROLLMENT_BRANCH_FIELDS: tuple[
    tuple[int, str, str, str, str, str], ...
] = (
    (
        2015,
        "spouse_or_partner",
        "ER64630",
        "ER64694",
        "ER64695",
        "ER64709",
    ),
    (
        2015,
        "head_or_reference_person",
        "ER64769",
        "ER64833",
        "ER64834",
        "ER64848",
    ),
    (
        2017,
        "spouse_or_partner",
        "ER70703",
        "ER70767",
        "ER70768",
        "ER70782",
    ),
    (
        2017,
        "head_or_reference_person",
        "ER70841",
        "ER70905",
        "ER70906",
        "ER70920",
    ),
    (
        2019,
        "spouse_or_partner",
        "ER76711",
        "ER76775",
        "ER76776",
        "ER76794",
    ),
    (
        2019,
        "head_or_reference_person",
        "ER76856",
        "ER76920",
        "ER76921",
        "ER76939",
    ),
    (
        2021,
        "spouse_or_partner",
        "ER80976",
        "ER81040",
        "ER81041",
        "ER81059",
    ),
    (
        2021,
        "head_or_reference_person",
        "ER81103",
        "ER81167",
        "ER81168",
        "ER81186",
    ),
    (
        2023,
        "spouse_or_partner",
        "ER84953",
        "ER85017",
        "ER85018",
        "ER85036",
    ),
    (
        2023,
        "head_or_reference_person",
        "ER85080",
        "ER85144",
        "ER85145",
        "ER85163",
    ),
)
ROLES: tuple[str, ...] = (
    "head_or_reference_person",
    "spouse_or_partner",
)
FIELD_PURPOSES: tuple[str, ...] = (
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
)

PHYSICAL_FIELD_COLUMNS: tuple[str, ...] = (
    "source_field_key",
    "interview_wave",
    "earnings_reference_year",
    "raw_field_id",
    "start",
    "end",
    "raw_width",
    "spss_numeric_format",
    "exact_short_label",
    "source_document_ids",
)
FIELD_BOUND_FORMAT_MAP_COLUMNS: tuple[str, ...] = (
    "raw_field_id",
    "stata_value_label_id",
    "code_label_rows",
)
CODE_LABEL_COLUMNS: tuple[str, ...] = (
    "raw_code",
    "exact_stata_value_label",
)
CODEBOOK_CODE_MAP_COLUMNS: tuple[str, ...] = (
    "frequency",
    "percent",
    "raw_value_or_range",
    "source_meaning",
)
CODEBOOK_FIELD_EVIDENCE_COLUMNS: tuple[str, ...] = (
    "codebook_field_key",
    "interview_wave",
    "earnings_reference_year",
    "raw_field_id",
    "exact_codebook_short_label",
    "declared_format",
    "layout_start",
    "layout_end",
    "raw_width",
    "spss_numeric_format",
    "full_source_description",
    "code_map",
    "missing_code_map_indices",
    "missing_raw_token_grammar_status",
    "semantic_annotation_status",
    "source_document_ids",
    "source_locator_ids",
    "derived_field_block_sha256",
)

_LAYOUT_FIELD_RE = re.compile(
    r"(?:\b(?:byte|int|long|float|double)\s+)?"
    r"([A-Za-z][A-Za-z0-9_]*)\s+(\d+)\s*-\s*(\d+)"
)
_SPSS_FORMAT_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9_]*)\s+\(([A-Za-z]\d+(?:\.\d+)?)\)"
)
_ZERO_SHA256 = "0" * 64
_CODEBOOK_FIELD_HEADER_RE = re.compile(
    r'^([A-Z][A-Z0-9_]*)[ \t]+"([^"\r\n]*)"[ \t]+'
    r"((?:NUM\([1-9][0-9]*\.[0-9]+\))|"
    r"(?:CHR\([1-9][0-9]*\)))[ \t]*$"
)
_CODEBOOK_MAP_HEADER_RE = re.compile(
    r"^[ \t]*Count[ \t]+%[ \t]+Value/Range Code[ \t]+"
    r"Value/Range Text[ \t]*$"
)
_CODEBOOK_MAP_ROW_RE = re.compile(
    r"^\s*((?:\d{1,3}(?:,\d{3})*|-))\s+"
    r"((?:\d+(?:\.\d+)?|\.\d+|-))\s+(\S.*)$"
)
_CODEBOOK_NUMBER_PATTERN = r"-?(?:\d+(?:,\d{3})*(?:\.\d+)?|\.\d+)"
_CODEBOOK_VALUE_AND_MEANING_RE = re.compile(
    rf"^({_CODEBOOK_NUMBER_PATTERN}"
    rf"(?:\s+-\s+{_CODEBOOK_NUMBER_PATTERN}|\s+-)?)"
    r"(?:\s+(\S.*))?$"
)
_CODEBOOK_RANGE_CONTINUATION_RE = re.compile(
    rf"^\s*({_CODEBOOK_NUMBER_PATTERN})(?:\s+(\S.*))?\s*$"
)
_EXPLICIT_MISSING_MEANING_RE = re.compile(
    r"(?:\bDK\b|\bNA\b(?!\s+type\b)|\bN/A\b|\bRF\b|refus|missing|"
    r"\binap\b|not applicable|data suppressed|wild code|"
    r"don(?:'|’)?t know)",
    flags=re.IGNORECASE,
)
_NOT_ASCERTAINED_RE = re.compile(r"\bnot ascertained\b", re.IGNORECASE)


def _is_explicit_missing_meaning(meaning: str) -> bool:
    """Classify only source meanings that denote a missing disposition."""

    if _EXPLICIT_MISSING_MEANING_RE.search(meaning):
        return True
    match = _NOT_ASCERTAINED_RE.search(meaning)
    if match is None:
        return False
    normalized = f" {' '.join(meaning.lower().split())} "
    return not (
        " either " in normalized or " or " in normalized or ";" in normalized
    )


class DictionaryDriftError(ValueError):
    """Raised when paired dictionary files disagree or are ambiguous."""


class RegistrationRequiredError(RuntimeError):
    """Raised when code requests an artifact the sources cannot ratify."""

    def __init__(self, target_artifact_id: str, item_ids: Sequence[str]):
        self.target_artifact_id = target_artifact_id
        self.item_ids = tuple(item_ids)
        joined = ", ".join(self.item_ids)
        super().__init__(
            f"{target_artifact_id} ratification aborted; "
            f"registration_required: {joined}"
        )


def default_psid_root() -> Path:
    """Return the repository-convention PSID staging root."""

    return Path("~/PolicyEngine/psid-data").expanduser()


def canonical_json_bytes(value: Any) -> bytes:
    """Return the artifact's deterministic JSON encoding."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(value).hexdigest()


def _normalise_label(value: str) -> str:
    return " ".join(value.split())


def _single_file(
    directory: Path,
    suffix: str,
    *,
    formats: bool,
) -> Path:
    candidates = sorted(directory.glob(f"*{suffix}"))
    candidates = [
        path
        for path in candidates
        if path.stem.lower().endswith("_formats") is formats
    ]
    if len(candidates) != 1:
        kind = "format" if formats else "main"
        raise DictionaryDriftError(
            f"{directory}: expected exactly one {kind} {suffix} file, "
            f"found {[path.name for path in candidates]}"
        )
    return candidates[0]


def _optional_format_pair(directory: Path) -> tuple[Path, Path] | None:
    do_files = sorted(
        path
        for path in directory.glob("*.do")
        if path.stem.lower().endswith("_formats")
    )
    sps_files = sorted(
        path
        for path in directory.glob("*.sps")
        if path.stem.lower().endswith("_formats")
    )
    if not do_files and not sps_files:
        return None
    if len(do_files) != 1 or len(sps_files) != 1:
        raise DictionaryDriftError(
            f"{directory}: format dictionaries must be an unambiguous "
            f".do/.sps pair; found do={len(do_files)}, sps={len(sps_files)}"
        )
    return do_files[0], sps_files[0]


def _single_codebook_file(directory: Path) -> Path:
    candidates = sorted(directory.glob("*codebook*.pdf"))
    if len(candidates) != 1:
        raise DictionaryDriftError(
            f"{directory}: expected exactly one codebook PDF, "
            f"found {[path.name for path in candidates]}"
        )
    return candidates[0]


def _single_family_archive(directory: Path) -> Path:
    candidates = sorted(directory.glob("*.zip"))
    if len(candidates) != 1:
        raise DictionaryDriftError(
            f"{directory}: expected exactly one family ZIP archive, "
            f"found {[path.name for path in candidates]}"
        )
    return candidates[0]


def _format_pair_for_wave(
    directory: Path,
    wave: int,
) -> tuple[Path, Path] | None:
    pair = _optional_format_pair(directory)
    if wave in FORMAT_MAP_WAVES and pair is None:
        raise DictionaryDriftError(
            f"{directory}: wave {wave} is missing its required field-bound "
            "format pair"
        )
    if wave not in FORMAT_MAP_WAVES and pair is not None:
        raise DictionaryDriftError(
            f"{directory}: unexpected field-bound format pair for wave {wave}"
        )
    return pair


def _extract_statement(
    text: str,
    opening: str,
    *,
    terminator: str = r"^\s*\.\s*$",
) -> str:
    match = re.search(
        opening + r"(?P<body>.*?)" + terminator,
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise DictionaryDriftError(
            f"dictionary statement not found: {opening}"
        )
    return match.group("body")


def _parse_spss(text: str) -> tuple[list[tuple[str, int, int]], dict, dict]:
    layout_body = _extract_statement(
        text,
        r"^\s*DATA\s+LIST\b[^\n]*/",
    )
    layout = [
        (name, int(start), int(end))
        for name, start, end in _LAYOUT_FIELD_RE.findall(layout_body)
    ]
    label_body = _extract_statement(text, r"^\s*VARIABLE\s+LABELS\b")
    labels: dict[str, str] = {}
    for line in label_body.splitlines():
        match = re.fullmatch(
            r'\s*([A-Za-z][A-Za-z0-9_]*)\s+"(.*)"\s*',
            line,
        )
        if match is None:
            if line.strip():
                raise DictionaryDriftError(
                    f"unparsed SPSS variable-label line: {line!r}"
                )
            continue
        name, label = match.groups()
        if name in labels:
            raise DictionaryDriftError(f"duplicate SPSS label for {name}")
        labels[name] = label

    formats: dict[str, str] = {}
    for match in re.finditer(
        r"^\s*FORMATS\b(?P<body>.*?)^\s*\.\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ):
        for name, numeric_format in _SPSS_FORMAT_RE.findall(
            match.group("body")
        ):
            if name in formats:
                raise DictionaryDriftError(
                    f"duplicate SPSS numeric format for {name}"
                )
            formats[name] = numeric_format.upper()
    return layout, labels, formats


def _parse_stata(text: str) -> tuple[list[tuple[str, int, int]], dict]:
    layout_body = _extract_statement(
        text,
        r"^\s*infix\b",
        terminator=r"^\s*using\b.*?;\s*$",
    )
    layout = [
        (name, int(start), int(end))
        for name, start, end in _LAYOUT_FIELD_RE.findall(layout_body)
    ]
    labels: dict[str, str] = {}
    for match in re.finditer(
        r'^\s*label\s+variable\s+([A-Za-z][A-Za-z0-9_]*)\s+"(.*)"\s*;\s*$',
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        name, label = match.groups()
        if name in labels:
            raise DictionaryDriftError(f"duplicate Stata label for {name}")
        labels[name] = label
    return layout, labels


def _assert_layout_complete(
    wave: int,
    layout: Sequence[tuple[str, int, int]],
) -> None:
    if not layout:
        raise DictionaryDriftError(f"wave {wave}: empty physical layout")
    names = [row[0] for row in layout]
    if len(names) != len(set(names)):
        raise DictionaryDriftError(f"wave {wave}: duplicate field names")
    previous_end = 0
    for name, start, end in layout:
        if start != previous_end + 1:
            raise DictionaryDriftError(
                f"wave {wave}: layout gap/overlap before {name}: "
                f"{previous_end} -> {start}"
            )
        if end < start:
            raise DictionaryDriftError(
                f"wave {wave}: reversed coordinates for {name}"
            )
        previous_end = end


def _document_row(
    path: Path,
    data_root: Path,
    wave: int,
    dictionary_role: str,
    *,
    encoding: str = "windows-1252",
) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "document_id": f"psid-family-{wave}-{dictionary_role}",
        "interview_wave": wave,
        "dictionary_role": dictionary_role,
        "path": path.relative_to(data_root).as_posix(),
        "size_bytes": len(content),
        "sha256": sha256_bytes(content),
        "encoding": encoding,
    }


def _codebook_document_row(
    path: Path,
    data_root: Path,
    wave: int,
) -> dict[str, Any]:
    codebook_bytes = path.read_bytes()
    archive_path = _single_family_archive(path.parent)
    archive_bytes = archive_path.read_bytes()
    with zipfile.ZipFile(archive_path) as archive:
        matching_members: list[tuple[zipfile.ZipInfo, bytes]] = []
        for member in archive.infolist():
            if member.is_dir() or not member.filename.lower().endswith(".pdf"):
                continue
            member_bytes = archive.read(member)
            if member_bytes == codebook_bytes:
                matching_members.append((member, member_bytes))
    if len(matching_members) != 1:
        raise DictionaryDriftError(
            f"wave {wave}: codebook bytes match "
            f"{len(matching_members)} PDF members in {archive_path.name}"
        )
    archive_member, archive_member_bytes = matching_members[0]
    row = _document_row(
        path,
        data_root,
        wave,
        "family_codebook",
        encoding="binary",
    )
    row["document_id"] = f"psid-family-{wave}-codebook"
    row["provenance"] = {
        "source_organization": "Panel Study of Income Dynamics",
        "source_product": "Family File Codebook",
        "source_edition": str(wave),
        "local_staging_authentication": "path_size_sha256_verified",
        "local_family_archive": {
            "path": archive_path.relative_to(data_root).as_posix(),
            "size_bytes": len(archive_bytes),
            "sha256": sha256_bytes(archive_bytes),
            "member_path": archive_member.filename,
            "member_size_bytes": archive_member.file_size,
            "member_crc32": f"{archive_member.CRC:08x}",
            "member_sha256": sha256_bytes(archive_member_bytes),
            "membership_authentication": (
                "archive_member_bytes_equal_registered_codebook_bytes"
            ),
        },
        "network_capture_performed_in_unit": False,
        "retrieval_provenance_status": (
            "registration_required_missing_original_retrieval_url_timestamp"
        ),
    }
    return row


def _pdf_indirect_objects(
    raw: bytes,
) -> dict[tuple[int, int], tuple[int, bytes]]:
    matches = list(re.finditer(rb"(?m)^(\d+)\s+(\d+)\s+obj\r?\n", raw))
    objects: dict[tuple[int, int], tuple[int, bytes]] = {}
    for index, match in enumerate(matches):
        boundary = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(raw)
        )
        end = raw.find(b"endobj", match.end(), boundary)
        if end < 0:
            raise DictionaryDriftError(
                f"PDF object {match.group(1).decode()} has no endobj"
            )
        key = (int(match.group(1)), int(match.group(2)))
        if key in objects:
            raise DictionaryDriftError(f"duplicate PDF object {key}")
        objects[key] = (match.end(), raw[match.end() : end])
    if not objects:
        raise DictionaryDriftError("PDF contains no indirect objects")
    return objects


def _pdf_references(value: bytes) -> list[tuple[int, int]]:
    return [
        (int(object_number), int(generation))
        for object_number, generation in re.findall(
            rb"(\d+)\s+(\d+)\s+R",
            value,
        )
    ]


def _pdf_page_objects(
    objects: Mapping[tuple[int, int], tuple[int, bytes]],
) -> list[tuple[int, int]]:
    catalog = [
        (key, body)
        for key, (_, body) in objects.items()
        if re.search(rb"/Type\s*/Catalog\b", body)
    ]
    if len(catalog) != 1:
        raise DictionaryDriftError(
            f"PDF must have one catalog object, found {len(catalog)}"
        )
    pages_reference = re.search(
        rb"/Pages\s+(\d+)\s+(\d+)\s+R",
        catalog[0][1],
    )
    if pages_reference is None:
        raise DictionaryDriftError("PDF catalog has no Pages reference")
    root = (int(pages_reference.group(1)), int(pages_reference.group(2)))

    def children(reference: tuple[int, int]) -> list[tuple[int, int]]:
        try:
            body = objects[reference][1]
        except KeyError as error:
            raise DictionaryDriftError(
                f"PDF page tree references missing object {reference}"
            ) from error
        if re.search(rb"/Type\s*/Page(?!s)\b", body):
            return [reference]
        if not re.search(rb"/Type\s*/Pages\b", body):
            raise DictionaryDriftError(
                f"PDF page-tree object {reference} is not Page/Pages"
            )
        direct = re.search(rb"/Kids\s*(\[[^]]*\])", body, flags=re.DOTALL)
        if direct is not None:
            kids_value = direct.group(1)
        else:
            indirect = re.search(
                rb"/Kids\s+(\d+)\s+(\d+)\s+R",
                body,
            )
            if indirect is None:
                raise DictionaryDriftError(
                    f"PDF Pages object {reference} has no Kids"
                )
            kids_reference = (
                int(indirect.group(1)),
                int(indirect.group(2)),
            )
            try:
                kids_value = objects[kids_reference][1]
            except KeyError as error:
                raise DictionaryDriftError(
                    "PDF Kids array references a missing object"
                ) from error
        kids = _pdf_references(kids_value)
        if not kids:
            raise DictionaryDriftError(
                f"PDF Pages object {reference} has an empty Kids array"
            )
        return [page for child in kids for page in children(child)]

    pages = children(root)
    root_body = objects[root][1]
    count_match = re.search(rb"/Count\s+(\d+)\b", root_body)
    count_reference = re.search(
        rb"/Count\s+(\d+)\s+(\d+)\s+R",
        root_body,
    )
    if count_reference is not None:
        count_body = objects[
            (int(count_reference.group(1)), int(count_reference.group(2)))
        ][1]
        scalar = re.fullmatch(rb"\s*(\d+)\s*", count_body)
        if scalar is None:
            raise DictionaryDriftError("PDF indirect Count is not an integer")
        declared_count = int(scalar.group(1))
    elif count_match is not None:
        declared_count = int(count_match.group(1))
    else:
        raise DictionaryDriftError("PDF Pages object has no Count")
    if declared_count != len(pages):
        raise DictionaryDriftError(
            "PDF Pages Count does not match enumerated page objects"
        )
    if len(pages) != len(set(pages)):
        raise DictionaryDriftError("PDF page tree repeats a page object")
    return pages


def _pdf_stream_length(
    dictionary: bytes,
    objects: Mapping[tuple[int, int], tuple[int, bytes]],
) -> int:
    indirect = re.search(
        rb"/Length\s+(\d+)\s+(\d+)\s+R",
        dictionary,
    )
    if indirect is not None:
        reference = (int(indirect.group(1)), int(indirect.group(2)))
        try:
            body = objects[reference][1]
        except KeyError as error:
            raise DictionaryDriftError(
                "PDF stream Length references a missing object"
            ) from error
        scalar = re.fullmatch(rb"\s*(\d+)\s*", body)
        if scalar is None:
            raise DictionaryDriftError(
                "PDF indirect stream Length is not an integer"
            )
        return int(scalar.group(1))
    direct = re.search(rb"/Length\s+(\d+)\b", dictionary)
    if direct is None:
        raise DictionaryDriftError("PDF stream has no Length")
    return int(direct.group(1))


def _pdf_filter_chain(dictionary: bytes) -> list[str]:
    match = re.search(
        rb"/Filter\s*(\[[^]]*\]|/[A-Za-z0-9]+)",
        dictionary,
        flags=re.DOTALL,
    )
    if match is None:
        return []
    return [
        value.decode("ascii")
        for value in re.findall(rb"/([A-Za-z0-9]+)", match.group(1))
    ]


def _decode_pdf_stream(data: bytes, filter_chain: Sequence[str]) -> bytes:
    decoded = data
    for filter_name in filter_chain:
        if filter_name == "ASCII85Decode":
            try:
                decoded = base64.a85decode(decoded, adobe=True)
            except ValueError as error:
                raise DictionaryDriftError(
                    "PDF ASCII85 stream decode failed"
                ) from error
        elif filter_name == "FlateDecode":
            try:
                decoded = zlib.decompress(decoded)
            except zlib.error as error:
                raise DictionaryDriftError(
                    "PDF Flate stream decode failed"
                ) from error
        else:
            raise DictionaryDriftError(
                f"unsupported PDF stream filter: {filter_name}"
            )
    return decoded


def _pdf_page_stream_locators(
    raw: bytes,
    document_id: str,
    page_field_ids: Mapping[int, Sequence[str]],
    derived_pages: Sequence[str],
) -> list[dict[str, Any]]:
    objects = _pdf_indirect_objects(raw)
    pages = _pdf_page_objects(objects)
    if len(pages) != len(derived_pages):
        raise DictionaryDriftError(
            "PDF page tree and derived page-text count disagree"
        )
    locators: list[dict[str, Any]] = []
    content_references: list[tuple[int, int]] = []
    for page_number, page_reference in enumerate(pages, start=1):
        page_body = objects[page_reference][1]
        contents = re.findall(
            rb"/Contents\s+(\d+)\s+(\d+)\s+R",
            page_body,
        )
        if len(contents) != 1:
            raise DictionaryDriftError(
                f"PDF page {page_number} does not have one Contents stream"
            )
        content_reference = (int(contents[0][0]), int(contents[0][1]))
        content_references.append(content_reference)
        try:
            object_body_start, content_body = objects[content_reference]
        except KeyError as error:
            raise DictionaryDriftError(
                f"PDF page {page_number} Contents object is missing"
            ) from error
        marker = re.search(rb"stream\r?\n", content_body)
        if marker is None:
            raise DictionaryDriftError(
                f"PDF page {page_number} Contents object has no stream"
            )
        dictionary = content_body[: marker.start()]
        stream_length = _pdf_stream_length(dictionary, objects)
        byte_start = object_body_start + marker.end()
        byte_end = byte_start + stream_length
        if not 0 <= byte_start < byte_end <= len(raw):
            raise DictionaryDriftError(
                f"PDF page {page_number} stream range is outside the file"
            )
        stream_bytes = raw[byte_start:byte_end]
        filter_chain = _pdf_filter_chain(dictionary)
        decoded = _decode_pdf_stream(stream_bytes, filter_chain)
        anchors = list(page_field_ids.get(page_number, ()))
        missing_anchors = [
            field_id
            for field_id in anchors
            if field_id.encode("ascii") not in decoded
        ]
        if missing_anchors:
            raise DictionaryDriftError(
                f"PDF page {page_number} lacks decoded field anchors "
                f"{missing_anchors[:4]}"
            )
        range_sha256 = sha256_bytes(stream_bytes)
        locator_preimage = [
            document_id,
            page_number,
            f"{page_reference[0]} {page_reference[1]} R",
            f"{content_reference[0]} {content_reference[1]} R",
            byte_start,
            byte_end,
            range_sha256,
        ]
        locators.append(
            {
                "locator_id": (
                    "psid-codebook-page:"
                    f"{sha256_bytes(canonical_json_bytes(locator_preimage))}"
                ),
                "source_document_id": document_id,
                "location_type": ("pdf_page_content_stream_raw_byte_range"),
                "pdf_page": page_number,
                "page_object": (f"{page_reference[0]} {page_reference[1]} R"),
                "content_object": (
                    f"{content_reference[0]} {content_reference[1]} R"
                ),
                "filter_chain": filter_chain,
                "declared_stream_length": stream_length,
                "byte_start": byte_start,
                "byte_end": byte_end,
                "range_sha256": range_sha256,
                "decoded_stream_sha256": sha256_bytes(decoded),
                "decoded_raw_field_id_anchors": anchors,
                "derived_page_text_sha256": sha256_bytes(
                    derived_pages[page_number - 1].encode("utf-8")
                ),
            }
        )
    if len(content_references) != len(set(content_references)):
        raise DictionaryDriftError("PDF pages share a Contents stream")
    return locators


def _pdftotext_version() -> str:
    result = subprocess.run(
        ["pdftotext", "-v"],
        check=True,
        capture_output=True,
    )
    output = (result.stdout + result.stderr).decode(
        "utf-8",
        errors="strict",
    )
    match = re.search(r"pdftotext version ([0-9.]+)", output)
    if match is None:
        raise DictionaryDriftError("cannot resolve pdftotext version")
    version = match.group(1)
    if version != PDF_TEXT_EXTRACTION_VERSION:
        raise DictionaryDriftError(
            "pdftotext version drift: "
            f"{version} != {PDF_TEXT_EXTRACTION_VERSION}"
        )
    return version


def _pdftotext_pages(path: Path) -> list[str]:
    result = subprocess.run(
        [
            "pdftotext",
            "-layout",
            "-enc",
            "UTF-8",
            str(path),
            "-",
        ],
        check=True,
        capture_output=True,
    )
    text = result.stdout.decode("utf-8", errors="strict")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if not pages or any("\x00" in page for page in pages):
        raise DictionaryDriftError(f"{path}: invalid derived PDF text")
    return pages


def _codebook_content_lines(
    pages: Sequence[str],
    wave: int,
) -> list[tuple[int, str]]:
    """Validate page framing and return only substantive page lines."""

    flattened: list[tuple[int, str]] = []
    total_pages = len(pages)
    for page_number, page in enumerate(pages, start=1):
        lines = page.splitlines()
        excluded: set[int] = set()
        if page_number > 1:
            nonblank = [
                index for index, line in enumerate(lines) if line.strip()
            ]
            if len(nonblank) < 2:
                raise DictionaryDriftError(
                    f"codebook page {page_number} lacks framing"
                )
            header_index = nonblank[0]
            footer_index = nonblank[-1]
            header = " ".join(lines[header_index].split())
            footer = " ".join(lines[footer_index].split())
            expected_headers = {
                f"Filename = FAM{wave}",
                (
                    "PANEL STUDY OF INCOME DYNAMICS: "
                    f"{wave} PUBLIC RELEASE FAMILY FILE"
                ),
                f"Panel Study of Income Dynamics: {wave} Family File",
            }
            if header not in expected_headers:
                raise DictionaryDriftError(
                    f"codebook page {page_number} header drifted: "
                    f"{header!r}"
                )
            if footer != f"Page {page_number} of {total_pages}":
                raise DictionaryDriftError(
                    f"codebook page {page_number} footer drifted: "
                    f"{footer!r}"
                )
            excluded = {header_index, footer_index}
        flattened.extend(
            (page_number, line)
            for index, line in enumerate(lines)
            if index not in excluded and line.strip()
        )
    return flattened


def _parse_codebook_map(
    lines: Sequence[str],
    table_header: str,
) -> list[list[str]]:
    count_anchor = table_header.index("Count")
    rows: list[list[str]] = []
    for line in lines:
        if not line.strip():
            continue
        leading_spaces = len(line) - len(line.lstrip())
        match = (
            _CODEBOOK_MAP_ROW_RE.fullmatch(line)
            if leading_spaces <= count_anchor + 7
            else None
        )
        if match is None:
            if not rows:
                raise DictionaryDriftError(
                    f"code-map continuation precedes its first row: {line!r}"
                )
            if rows[-1][2].endswith(" -"):
                range_match = _CODEBOOK_RANGE_CONTINUATION_RE.fullmatch(line)
                if range_match is None:
                    raise DictionaryDriftError(
                        "open code-map range is not followed by its "
                        f"upper bound: {line!r}"
                    )
                rows[-1][2] = f"{rows[-1][2]} {range_match.group(1)}"
                suffix = range_match.group(2)
                if suffix:
                    rows[-1][3] = (
                        f"{rows[-1][3]} {' '.join(suffix.split())}"
                    ).strip()
                continue
            continuation = " ".join(line.split())
            rows[-1][3] = f"{rows[-1][3]} {continuation}".strip()
            continue
        if rows and rows[-1][2].endswith(" -"):
            raise DictionaryDriftError(
                "open code-map range reaches the next row without "
                "an upper bound"
            )
        value_match = _CODEBOOK_VALUE_AND_MEANING_RE.fullmatch(match.group(3))
        if value_match is None:
            raise DictionaryDriftError(
                f"invalid code-map value/meaning grammar: {line!r}"
            )
        source_meaning = value_match.group(2) or ""
        rows.append(
            [
                match.group(1),
                match.group(2),
                " ".join(value_match.group(1).split()),
                " ".join(source_meaning.split()),
            ]
        )
    if not rows:
        raise DictionaryDriftError("codebook field has an empty code map")
    if any(not row[3] for row in rows):
        raise DictionaryDriftError(
            "codebook field has a row without a final source meaning"
        )
    if any(row[2].endswith(" -") for row in rows):
        raise DictionaryDriftError(
            "codebook field has an unresolved open range"
        )
    return rows


def _codebook_field_key(
    wave: int,
    raw_field_id: str,
    start: int,
    end: int,
) -> str:
    preimage = [wave, raw_field_id, start, end]
    return (
        "psid-codebook-field:"
        f"{sha256_bytes(canonical_json_bytes(preimage))}"
    )


def _extract_wave_codebook_evidence(
    *,
    wave: int,
    codebook_path: Path,
    codebook_document: Mapping[str, Any],
    physical_rows: Sequence[Sequence[Any]],
) -> tuple[list[list[Any]], list[dict[str, Any]]]:
    derived_pages = _pdftotext_pages(codebook_path)
    flattened = _codebook_content_lines(derived_pages, wave)
    headings: list[tuple[int, re.Match[str]]] = []
    page_field_ids: dict[int, list[str]] = {}
    for position, (page_number, line) in enumerate(flattened):
        match = _CODEBOOK_FIELD_HEADER_RE.fullmatch(line)
        if match is not None:
            headings.append((position, match))
            page_field_ids.setdefault(page_number, []).append(match.group(1))
    if not headings:
        raise DictionaryDriftError(f"wave {wave}: no codebook fields")

    physical_columns = {
        name: index for index, name in enumerate(PHYSICAL_FIELD_COLUMNS)
    }
    physical_by_id = {
        row[physical_columns["raw_field_id"]]: row for row in physical_rows
    }
    heading_ids = [match.group(1) for _, match in headings]
    if len(heading_ids) != len(set(heading_ids)):
        raise DictionaryDriftError(
            f"wave {wave}: duplicate codebook field heading"
        )
    if set(heading_ids) != set(physical_by_id):
        raise DictionaryDriftError(
            f"wave {wave}: codebook and physical field domains disagree"
        )

    raw = codebook_path.read_bytes()
    locators = _pdf_page_stream_locators(
        raw,
        codebook_document["document_id"],
        page_field_ids,
        derived_pages,
    )
    locator_by_page = {row["pdf_page"]: row["locator_id"] for row in locators}
    rows: list[list[Any]] = []
    for heading_index, (position, match) in enumerate(headings):
        next_position = (
            headings[heading_index + 1][0]
            if heading_index + 1 < len(headings)
            else len(flattened)
        )
        block = flattened[position + 1 : next_position]
        table_headers = [
            (offset, line)
            for offset, (_, line) in enumerate(block)
            if _CODEBOOK_MAP_HEADER_RE.fullmatch(line)
        ]
        if len(table_headers) != 1:
            raise DictionaryDriftError(
                f"wave {wave} field {match.group(1)} has "
                f"{len(table_headers)} code-map headers"
            )
        table_offset, table_header = table_headers[0]
        description_lines = [
            " ".join(line.split()) for _, line in block[:table_offset]
        ]
        description = "\n".join(description_lines)
        code_map = _parse_codebook_map(
            [line for _, line in block[table_offset + 1 :]],
            table_header,
        )
        meaningful_pages = [page_number for page_number, line in block]
        heading_page = flattened[position][0]
        last_page = max(meaningful_pages, default=heading_page)
        source_locator_ids = [
            locator_by_page[page_number]
            for page_number in range(heading_page, last_page + 1)
        ]
        field_id, codebook_label, declared_format = match.groups()
        physical = physical_by_id[field_id]
        start = physical[physical_columns["start"]]
        end = physical[physical_columns["end"]]
        raw_width = physical[physical_columns["raw_width"]]
        format_match = re.fullmatch(
            r"(?:NUM|CHR)\((\d+)(?:\.\d+)?\)",
            declared_format,
        )
        if format_match is None or int(format_match.group(1)) != raw_width:
            raise DictionaryDriftError(
                f"wave {wave} field {field_id} codebook/layout width drift"
            )
        setup_label = physical[physical_columns["exact_short_label"]]
        if _normalise_label(codebook_label) != _normalise_label(setup_label):
            raise DictionaryDriftError(
                f"wave {wave} field {field_id} codebook/setup label drift"
            )
        missing_indices = [
            index
            for index, code_row in enumerate(code_map)
            if _is_explicit_missing_meaning(code_row[3])
        ]
        source_document_ids = [
            *physical[physical_columns["source_document_ids"]],
            codebook_document["document_id"],
        ]
        derived_block = [
            flattened[position][1],
            description,
            code_map,
        ]
        rows.append(
            [
                _codebook_field_key(wave, field_id, start, end),
                wave,
                wave - 1,
                field_id,
                codebook_label,
                declared_format,
                start,
                end,
                raw_width,
                physical[physical_columns["spss_numeric_format"]],
                description,
                code_map,
                missing_indices,
                "not_established_exact_fixed_width_raw_tokens",
                "fact_or_registration_required_residual",
                source_document_ids,
                source_locator_ids,
                sha256_bytes(canonical_json_bytes(derived_block)),
            ]
        )
    rows.sort(key=lambda row: row[6])
    return rows, locators


def _stata_statements(text: str) -> list[str]:
    statements: list[str] = []
    continued: list[str] = []
    for source_line in text.splitlines():
        line = source_line.strip()
        if not line and not continued:
            continue
        if line.endswith("///"):
            continued.append(line[:-3].rstrip())
            continue
        continued.append(line)
        statement = " ".join(part for part in continued if part)
        if statement:
            statements.append(statement)
        continued = []
    if continued:
        raise DictionaryDriftError("unterminated Stata line continuation")
    return statements


def _expand_stata_char_macros(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        code = int(match.group(1))
        if not 0 <= code <= 255:
            raise DictionaryDriftError(
                f"unsupported Stata char() code: {code}"
            )
        return bytes([code]).decode("cp1252")

    expanded = re.sub(r"`=char\((\d+)\)'", replace, value)
    if re.search(r"`[^']*'", expanded):
        raise DictionaryDriftError(
            f"unsupported Stata macro in value label: {expanded!r}"
        )
    return expanded


def _parse_stata_code_label_rows(
    body: str,
    *,
    loop_variable: str | None = None,
    loop_value: int | None = None,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    position = 0
    while position < len(body):
        while position < len(body) and body[position].isspace():
            position += 1
        if position == len(body):
            break
        integer_match = re.match(r"[+-]?\d+", body[position:])
        if integer_match is not None:
            raw_code = int(integer_match.group())
            position += len(integer_match.group())
        else:
            macro_match = re.match(
                r"`([A-Za-z][A-Za-z0-9_]*)'", body[position:]
            )
            if macro_match is None:
                raise DictionaryDriftError(
                    f"unparsed Stata value-label code near {body[position:]!r}"
                )
            if (
                loop_variable is None
                or macro_match.group(1) != loop_variable
                or loop_value is None
            ):
                raise DictionaryDriftError(
                    f"unbound Stata loop macro: {macro_match.group()!r}"
                )
            raw_code = loop_value
            position += len(macro_match.group())
        while position < len(body) and body[position].isspace():
            position += 1
        if body.startswith('`"', position):
            label_start = position + 2
            label_end = body.find("\"'", label_start)
            if label_end < 0:
                raise DictionaryDriftError(
                    "unterminated Stata compound-quoted value label"
                )
            label = body[label_start:label_end]
            position = label_end + 2
        elif position < len(body) and body[position] == '"':
            label_start = position + 1
            label_end = body.find('"', label_start)
            if label_end < 0:
                raise DictionaryDriftError("unterminated Stata value label")
            label = body[label_start:label_end]
            position = label_end + 1
        else:
            raise DictionaryDriftError(
                f"unparsed Stata value-label text near {body[position:]!r}"
            )
        rows.append([raw_code, _expand_stata_char_macros(label)])
    if not rows:
        raise DictionaryDriftError("empty Stata value-label definition")
    return rows


def _parse_stata_label_definition(
    statement: str,
    *,
    loop_variable: str | None = None,
    loop_value: int | None = None,
) -> tuple[str, list[list[Any]]]:
    match = re.fullmatch(
        r"label\s+define\s+([A-Za-z][A-Za-z0-9_]*)\s+"
        r"(?P<body>.*?)(?:\s*,\s*modify)?",
        statement,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise DictionaryDriftError(
            f"unparsed Stata label definition: {statement!r}"
        )
    return (
        match.group(1),
        _parse_stata_code_label_rows(
            match.group("body"),
            loop_variable=loop_variable,
            loop_value=loop_value,
        ),
    )


def _append_stata_label_rows(
    definitions: dict[str, list[list[Any]]],
    label_id: str,
    rows: Sequence[list[Any]],
) -> None:
    defined = definitions.setdefault(label_id, [])
    existing_codes = {row[0] for row in defined}
    incoming_codes = [row[0] for row in rows]
    if len(incoming_codes) != len(set(incoming_codes)):
        raise DictionaryDriftError(
            f"duplicate Stata codes in value-label definition {label_id}"
        )
    duplicates = existing_codes.intersection(incoming_codes)
    if duplicates:
        raise DictionaryDriftError(
            f"duplicate Stata value-label codes for {label_id}: "
            f"{sorted(duplicates)}"
        )
    defined.extend(rows)


def _parse_stata_format_maps(text: str) -> list[list[Any]]:
    statements = _stata_statements(text)
    definitions: dict[str, list[list[Any]]] = {}
    bindings: list[tuple[str, str]] = []
    bound_fields: set[str] = set()
    bound_label_ids: set[str] = set()
    index = 0
    while index < len(statements):
        statement = statements[index]
        loop_match = re.fullmatch(
            r"forvalues\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*"
            r"([+-]?\d+)\s*/\s*([+-]?\d+)\s*\{",
            statement,
            flags=re.IGNORECASE,
        )
        if loop_match is not None:
            if index + 2 >= len(statements) or statements[index + 2] != "}":
                raise DictionaryDriftError(
                    f"unclosed or multi-command Stata forvalues: {statement!r}"
                )
            variable, first_text, last_text = loop_match.groups()
            first = int(first_text)
            last = int(last_text)
            if first > last:
                raise DictionaryDriftError(
                    f"descending Stata forvalues range: {statement!r}"
                )
            for value in range(first, last + 1):
                label_id, rows = _parse_stata_label_definition(
                    statements[index + 1],
                    loop_variable=variable,
                    loop_value=value,
                )
                _append_stata_label_rows(definitions, label_id, rows)
            index += 3
            continue
        if re.match(r"label\s+define\b", statement, flags=re.IGNORECASE):
            label_id, rows = _parse_stata_label_definition(statement)
            _append_stata_label_rows(definitions, label_id, rows)
            index += 1
            continue
        binding_match = re.fullmatch(
            r"label\s+values\s+([A-Za-z][A-Za-z0-9_]*)\s+"
            r"([A-Za-z][A-Za-z0-9_]*)",
            statement,
            flags=re.IGNORECASE,
        )
        if binding_match is not None:
            field_id, label_id = binding_match.groups()
            if field_id in bound_fields:
                raise DictionaryDriftError(
                    f"duplicate Stata value-label binding for {field_id}"
                )
            if label_id in bound_label_ids:
                raise DictionaryDriftError(
                    f"Stata value-label definition bound twice: {label_id}"
                )
            bound_fields.add(field_id)
            bound_label_ids.add(label_id)
            bindings.append((field_id, label_id))
            index += 1
            continue
        raise DictionaryDriftError(
            f"unparsed Stata format statement: {statement!r}"
        )

    definition_ids = set(definitions)
    if definition_ids != bound_label_ids:
        raise DictionaryDriftError(
            "Stata value-label definitions and bindings disagree; "
            f"unbound={sorted(definition_ids - bound_label_ids)[:4]}, "
            f"undefined={sorted(bound_label_ids - definition_ids)[:4]}"
        )
    return [
        [field_id, label_id, definitions[label_id]]
        for field_id, label_id in bindings
    ]


def _parse_spss_format_domains(
    text: str,
) -> tuple[dict[str, tuple[int, ...]], int]:
    block_pattern = re.compile(
        r"^\s*VALUE\s+LABELS\s*$" r"(?P<body>.*?)" r"^\s*\.\s*$",
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    blocks = list(block_pattern.finditer(text))
    remainder = block_pattern.sub("", text)
    if remainder.strip().upper() not in {"", "EXECUTE."}:
        raise DictionaryDriftError(
            f"unparsed SPSS format content: {remainder.strip()[:80]!r}"
        )
    domains: dict[str, tuple[int, ...]] = {}
    truncation_count = 0
    for block in blocks:
        lines = [
            line.strip()
            for line in block.group("body").splitlines()
            if line.strip()
        ]
        if not lines:
            raise DictionaryDriftError("empty SPSS value-label block")
        header_match = re.fullmatch(
            r"([A-Za-z][A-Za-z0-9_]*)"
            r"(?:\s+/\*Truncated value label ends with \.\.\.\*/)?",
            lines[0],
            flags=re.IGNORECASE,
        )
        if header_match is None:
            raise DictionaryDriftError(
                f"unparsed SPSS value-label header: {lines[0]!r}"
            )
        field_id = header_match.group(1)
        if field_id in domains:
            raise DictionaryDriftError(
                f"duplicate SPSS value-label map for {field_id}"
            )
        if "/*" in lines[0]:
            truncation_count += 1
        codes: list[int] = []
        for line in lines[1:]:
            row_match = re.fullmatch(r"([+-]?\d+)\s+'(.*)'", line)
            if row_match is None:
                raise DictionaryDriftError(
                    f"unparsed SPSS value-label row: {line!r}"
                )
            codes.append(int(row_match.group(1)))
        if not codes or len(codes) != len(set(codes)):
            raise DictionaryDriftError(
                f"empty or duplicate SPSS code domain for {field_id}"
            )
        domains[field_id] = tuple(codes)
    if not domains:
        raise DictionaryDriftError("no SPSS field-bound value-label maps")
    return domains, truncation_count


def _format_evidence(
    stata_path: Path,
    spss_path: Path,
    physical_field_names: Iterable[str],
) -> dict[str, Any]:
    stata_maps = _parse_stata_format_maps(
        stata_path.read_bytes().decode("cp1252")
    )
    spss_domains, truncation_count = _parse_spss_format_domains(
        spss_path.read_bytes().decode("cp1252")
    )
    stata_domains = {
        row[0]: tuple(code_row[0] for code_row in row[2]) for row in stata_maps
    }
    if set(stata_domains) != set(spss_domains):
        raise DictionaryDriftError(
            "Stata and SPSS field-bound value-label domains disagree"
        )
    for field_id, stata_codes in stata_domains.items():
        if set(stata_codes) != set(spss_domains[field_id]):
            raise DictionaryDriftError(
                f"Stata and SPSS code domains disagree for {field_id}"
            )
    unknown_fields = set(stata_domains).difference(physical_field_names)
    if unknown_fields:
        raise DictionaryDriftError(
            "format maps bind fields outside the physical layout: "
            f"{sorted(unknown_fields)[:4]}"
        )
    row_count = sum(len(row[2]) for row in stata_maps)
    return {
        "field_bound_format_map_columns": list(FIELD_BOUND_FORMAT_MAP_COLUMNS),
        "code_label_columns": list(CODE_LABEL_COLUMNS),
        "field_bound_format_maps": stata_maps,
        "field_bound_format_maps_sha256": sha256_bytes(
            canonical_json_bytes(stata_maps)
        ),
        "value_label_map_count": len(stata_maps),
        "value_label_row_count": row_count,
        "explicit_truncation_count": truncation_count,
    }


def _compare_wave_dictionaries(
    wave: int,
    do_path: Path,
    sps_path: Path,
) -> tuple[list[tuple[str, int, int, str | None, str]], int, int]:
    do_text = do_path.read_bytes().decode("cp1252")
    sps_text = sps_path.read_bytes().decode("cp1252")
    do_layout, do_labels = _parse_stata(do_text)
    sps_layout, sps_labels, sps_formats = _parse_spss(sps_text)
    _assert_layout_complete(wave, do_layout)
    _assert_layout_complete(wave, sps_layout)
    if do_layout != sps_layout:
        raise DictionaryDriftError(
            f"wave {wave}: Stata and SPSS physical layouts disagree"
        )
    layout_names = [name for name, _, _ in sps_layout]
    if set(layout_names) != set(do_labels):
        raise DictionaryDriftError(
            f"wave {wave}: Stata label domain does not equal layout domain"
        )
    if set(layout_names) != set(sps_labels):
        raise DictionaryDriftError(
            f"wave {wave}: SPSS label domain does not equal layout domain"
        )
    unknown_formats = set(sps_formats).difference(layout_names)
    if unknown_formats:
        raise DictionaryDriftError(
            f"wave {wave}: formats for unknown fields "
            f"{sorted(unknown_formats)}"
        )

    rows: list[tuple[str, int, int, str | None, str]] = []
    for name, start, end in sps_layout:
        do_label = do_labels[name]
        sps_label = sps_labels[name]
        if _normalise_label(do_label) != _normalise_label(sps_label):
            raise DictionaryDriftError(
                f"wave {wave}: label disagreement for {name}: "
                f"{do_label!r} != {sps_label!r}"
            )
        rows.append(
            (
                name,
                start,
                end,
                sps_formats.get(name),
                sps_label,
            )
        )
    missing_declarations = len(
        re.findall(
            r"^\s*MISSING\s+VALUES\b",
            sps_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    value_label_declarations = len(
        re.findall(
            r"^\s*VALUE\s+LABELS\b",
            sps_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    return rows, missing_declarations, value_label_declarations


def _field_key(wave: int, name: str, start: int, end: int) -> str:
    digest = sha256_bytes(canonical_json_bytes([wave, name, start, end]))
    return f"psid-physical-field:{digest}"


def _keyset_hash(keys: Iterable[str]) -> str:
    return sha256_bytes(canonical_json_bytes(list(keys)))


def _registration_required_items() -> list[dict[str, Any]]:
    return [
        {
            "registration_item_id": "V-B5",
            "status": "registration_required",
            "required_evidence": (
                "Exact early-era main/spouse/secondary-job attachment, "
                "complete three-digit meanings, and exhaustive absence "
                "proofs for unsupported occupation/industry slots."
            ),
            "source_finding": (
                "Registered codebooks establish retrospective main-job "
                "fields for both roles and broad head secondary occupation, "
                "but explicitly defer exact three-digit listings to "
                "unregistered Appendix V2/retrospective documentation and "
                "cannot prove secondary-industry/spouse-secondary absence."
            ),
        },
        {
            "registration_item_id": "V-B6",
            "status": "registration_required",
            "required_evidence": (
                "Exact 1976/1977-reference-year spouse remuneration type "
                "plus complete main/secondary annual-job matching for "
                "employee/self/mixed, incorporation, government-employer "
                "status, and federal/state/local government level."
            ),
            "source_finding": (
                "V4382 proves that V4379 includes spouse unincorporated-"
                "business labor. V5289/V5788 have complete amount maps but "
                "do not establish wages-only versus mixed. Current-job and "
                "secondary-job concepts are source-bound, but are not "
                "matched to the annual spouse amounts. V4845/V4850 prove "
                "only a government-employer yes/no indicator, not the "
                "federal/state/local level, and codebooks alone cannot prove "
                "whether a spouse secondary-job branch is absent in 1977/78."
            ),
        },
        {
            "registration_item_id": "V-B8",
            "status": "registration_required",
            "required_evidence": (
                "A stable cross-era current regular-school mapping, branch "
                "and carry-forward logic, freshness rules, and exhaustive "
                "questionnaire absence proof."
            ),
            "source_finding": (
                "Complete K/L61A and K/L84 maps are preserved, but they are "
                "complementary new/continuing-role branches. Earlier "
                "background fields contain still-in-school/college codes, "
                "disproving blanket absence while failing to establish "
                "current-wave freshness or regular-school equivalence."
            ),
        },
    ]


def _target_artifacts() -> list[dict[str, str]]:
    return [
        {
            "schema_version": SLOT_SPECS_ID,
            "artifact_id": SLOT_SPECS_ID,
            "status": "not_emitted_registration_required",
        },
        {
            "schema_version": "psid_source_field_inventory.v1",
            "artifact_id": SOURCE_INVENTORY_ID,
            "status": "not_emitted_registration_required",
        },
    ]


def _inventory_ratification_abort(
    registration_items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "status": "registration_required",
        "failure_disposition": "abort_inventory_ratification",
        "missing_source_commitments": [
            "complete questionnaire job/component/context slot hierarchy",
            "exact fixed-width missing-token padding/sign/blank grammar",
            "role/job attachment where codebook descriptions are ambiguous",
            "source-backed cross-wave component and freshness mapping",
            "exhaustive questionnaire/layout absence proofs",
        ],
        "forbidden_fallbacks": [
            "derive the slot domain from the correction crosswalk",
            "infer structural_missing from a label keyword search",
            "treat a short label as a full source description",
            "infer a missing token or timing rule at runtime",
            "claim reproduced_from_source_bytes true",
        ],
        "registration_required_item_ids": [
            row["registration_item_id"] for row in registration_items
        ],
    }


def build_registration_required_audit(
    data_root: Path | None = None,
) -> dict[str, Any]:
    """Build the source-only physical-field audit.

    Raw microdata are byte-pinned for source identity but never parsed.  All
    physical-field metadata are derived independently from the dictionaries.
    """

    root = default_psid_root() if data_root is None else Path(data_root)
    family_root = root / "family"
    manifest: list[dict[str, Any]] = []
    physical_fields: list[list[Any]] = []
    format_file_evidence: list[dict[str, Any]] = []
    missing_declaration_count = 0
    main_value_label_count = 0
    explicit_numeric_format_count = 0
    wave_field_counts: list[list[int]] = []

    for wave in INTERVIEW_WAVES:
        directory = family_root / str(wave)
        if not directory.is_dir():
            raise DictionaryDriftError(
                f"missing staged family-wave directory: {directory}"
            )
        do_path = _single_file(directory, ".do", formats=False)
        sps_path = _single_file(directory, ".sps", formats=False)
        raw_path = _single_file(directory, ".txt", formats=False)
        codebook_path = _single_codebook_file(directory)
        do_document = _document_row(
            do_path,
            root,
            wave,
            "stata_setup",
        )
        sps_document = _document_row(
            sps_path,
            root,
            wave,
            "spss_setup",
        )
        raw_document = _document_row(
            raw_path,
            root,
            wave,
            "raw_fixed_width",
            encoding="binary",
        )
        codebook_document = _codebook_document_row(
            codebook_path,
            root,
            wave,
        )
        manifest.extend(
            [
                do_document,
                sps_document,
                raw_document,
                codebook_document,
            ]
        )
        rows, missing_count, value_label_count = _compare_wave_dictionaries(
            wave,
            do_path,
            sps_path,
        )
        missing_declaration_count += missing_count
        main_value_label_count += value_label_count
        explicit_numeric_format_count += sum(
            numeric_format is not None for _, _, _, numeric_format, _ in rows
        )
        wave_field_counts.append([wave, len(rows)])
        source_ids = [
            do_document["document_id"],
            sps_document["document_id"],
            raw_document["document_id"],
        ]
        for name, start, end, numeric_format, label in rows:
            physical_fields.append(
                [
                    _field_key(wave, name, start, end),
                    wave,
                    wave - 1,
                    name,
                    start,
                    end,
                    end - start + 1,
                    numeric_format,
                    label,
                    source_ids,
                ]
            )

        format_pair = _format_pair_for_wave(directory, wave)
        if format_pair is not None:
            format_do_path, format_sps_path = format_pair
            format_do_document = _document_row(
                format_do_path,
                root,
                wave,
                "stata_value_labels",
            )
            format_sps_document = _document_row(
                format_sps_path,
                root,
                wave,
                "spss_value_labels",
            )
            manifest.extend([format_do_document, format_sps_document])
            evidence = _format_evidence(
                format_do_path,
                format_sps_path,
                (name for name, *_ in rows),
            )
            evidence["interview_wave"] = wave
            evidence["source_document_ids"] = [
                format_do_document["document_id"],
                format_sps_document["document_id"],
            ]
            format_file_evidence.append(evidence)

    registration_items = _registration_required_items()
    dictionary_manifest = [
        row for row in manifest if row["dictionary_role"] != "raw_fixed_width"
    ]
    setup_dictionary_manifest = [
        row
        for row in dictionary_manifest
        if row["dictionary_role"] != "family_codebook"
    ]
    codebook_manifest = [
        row
        for row in dictionary_manifest
        if row["dictionary_role"] == "family_codebook"
    ]
    raw_manifest = [
        row for row in manifest if row["dictionary_role"] == "raw_fixed_width"
    ]
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "target_artifacts": _target_artifacts(),
        "source_authority_manifest": manifest,
        "interview_waves": list(INTERVIEW_WAVES),
        "roles": list(ROLES),
        "field_purposes": list(FIELD_PURPOSES),
        "physical_field_columns": list(PHYSICAL_FIELD_COLUMNS),
        "physical_fields": physical_fields,
        "physical_field_count": len(physical_fields),
        "physical_field_keyset_sha256": _keyset_hash(
            row[0] for row in physical_fields
        ),
        "evidence_summary": {
            "source_authority_file_count": len(manifest),
            "source_authority_total_size_bytes": sum(
                row["size_bytes"] for row in manifest
            ),
            "source_authority_manifest_sha256": sha256_bytes(
                canonical_json_bytes(manifest)
            ),
            "dictionary_file_count": len(dictionary_manifest),
            "dictionary_total_size_bytes": sum(
                row["size_bytes"] for row in dictionary_manifest
            ),
            "setup_dictionary_file_count": len(setup_dictionary_manifest),
            "setup_dictionary_total_size_bytes": sum(
                row["size_bytes"] for row in setup_dictionary_manifest
            ),
            "codebook_file_count": len(codebook_manifest),
            "codebook_total_size_bytes": sum(
                row["size_bytes"] for row in codebook_manifest
            ),
            "codebook_authority_manifest_sha256": sha256_bytes(
                canonical_json_bytes(codebook_manifest)
            ),
            "raw_fixed_width_file_count": len(raw_manifest),
            "raw_fixed_width_total_size_bytes": sum(
                row["size_bytes"] for row in raw_manifest
            ),
            "wave_field_counts": wave_field_counts,
            "main_dictionary_field_count": len(physical_fields),
            "explicit_spss_numeric_format_count": (
                explicit_numeric_format_count
            ),
            "main_spss_missing_values_declaration_count": (
                missing_declaration_count
            ),
            "main_spss_value_label_statement_count": main_value_label_count,
            "format_file_evidence": format_file_evidence,
        },
        "inventory_ratification_abort": _inventory_ratification_abort(
            registration_items
        ),
        "registration_required_items": registration_items,
        "canonical_order": [
            "interview_wave",
            "physical_layout_coordinate",
        ],
        "integrity": {
            "canonicalization": (
                "UTF-8 JSON; keys sorted; no insignificant whitespace; "
                "content_sha256 computed with itself set to 64 zeroes"
            ),
            "content_sha256": _ZERO_SHA256,
            "builder_source_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "reproduced_from_source_bytes": False,
        },
    }
    artifact["integrity"]["content_sha256"] = sha256_bytes(
        canonical_json_bytes(artifact)
    )
    return artifact


def _codebook_era_waves(era_id: str) -> tuple[int, ...]:
    matches = [
        waves for candidate, waves in CODEBOOK_ERA_SPECS if candidate == era_id
    ]
    if len(matches) != 1:
        raise DictionaryDriftError(f"unknown codebook era: {era_id}")
    return matches[0]


def _early_role_total_facts(
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    columns, by_coordinate = _codebook_fields_by_coordinate(field_rows)
    facts: list[dict[str, Any]] = []
    for wave, role, field_id in EARLY_ROLE_TOTAL_FIELDS:
        row = _required_codebook_field(
            by_coordinate,
            wave,
            field_id,
            "early role-total",
        )
        description = row[columns["full_source_description"]]
        lowered = description.lower()
        role_anchor = "head" if role == "head_or_reference_person" else "wife"
        if (
            "income" not in lowered
            or role_anchor not in lowered
            or not any(
                code_row[3].lower().startswith("actual amount")
                for code_row in row[columns["code_map"]]
            )
        ):
            raise DictionaryDriftError(
                f"early role-total source anchors drifted: {wave}/{field_id}"
            )
        remuneration_type = None
        if role == "head_or_reference_person":
            if (
                "farm income" not in lowered
                or "business income" not in lowered
            ):
                raise DictionaryDriftError(
                    f"early head mixed-income anchors drifted: {wave}/{field_id}"
                )
            remuneration_type = "mixed"
        facts.append(
            {
                "fact_id": f"early-role-total:{wave}:{role}",
                "fact_class": "role_total_amount_concept",
                "status": "established_from_codebook_bytes",
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": role,
                "job_slot": "role_total",
                "questionnaire_component_slot": "role_total_labor_income",
                "slot_kind": "role_total",
                "field_purpose": "amount",
                "raw_field_ids": [field_id],
                "codebook_field_keys": [row[columns["codebook_field_key"]]],
                "source_locator_ids": list(row[columns["source_locator_ids"]]),
                "reporting_unit": "dollars",
                "reference_periodicity": "annual",
                "information_date_basis": "reference_year_end",
                "job_match_timing": "not_applicable_role_total",
                "remuneration_type": remuneration_type,
            }
        )
    facts.extend(_early_occupation_industry_facts(field_rows))
    return facts


def _codebook_fields_by_coordinate(
    field_rows: Sequence[Sequence[Any]],
) -> tuple[
    dict[str, int],
    dict[tuple[int, str], Sequence[Any]],
]:
    columns = {
        name: index
        for index, name in enumerate(CODEBOOK_FIELD_EVIDENCE_COLUMNS)
    }
    by_coordinate = {
        (
            row[columns["interview_wave"]],
            row[columns["raw_field_id"]],
        ): row
        for row in field_rows
    }
    return columns, by_coordinate


def _required_codebook_field(
    by_coordinate: Mapping[tuple[int, str], Sequence[Any]],
    wave: int,
    field_id: str,
    fact_class: str,
) -> Sequence[Any]:
    try:
        return by_coordinate[(wave, field_id)]
    except KeyError as error:
        raise DictionaryDriftError(
            f"{fact_class} field is absent: {wave}/{field_id}"
        ) from error


def _fact_source_binding(
    rows: Sequence[Sequence[Any]],
    columns: Mapping[str, int],
) -> dict[str, list[str]]:
    locators: list[str] = []
    for row in rows:
        for locator_id in row[columns["source_locator_ids"]]:
            if locator_id not in locators:
                locators.append(locator_id)
    return {
        "raw_field_ids": [row[columns["raw_field_id"]] for row in rows],
        "codebook_field_keys": [
            row[columns["codebook_field_key"]] for row in rows
        ],
        "source_locator_ids": locators,
    }


def _early_occupation_industry_facts(
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    columns, by_coordinate = _codebook_fields_by_coordinate(field_rows)
    facts: list[dict[str, Any]] = []
    for (
        wave,
        role,
        job_slot,
        purpose,
        field_id,
    ) in EARLY_OCCUPATION_INDUSTRY_FIELDS:
        row = _required_codebook_field(
            by_coordinate,
            wave,
            field_id,
            "early occupation/industry",
        )
        searchable = " ".join(
            (
                row[columns["exact_codebook_short_label"]],
                row[columns["full_source_description"]],
            )
        ).lower()
        if purpose not in searchable:
            raise DictionaryDriftError(
                f"early {purpose} anchor drifted: {wave}/{field_id}"
            )
        facts.append(
            {
                "fact_id": f"early-{purpose}:{wave}:{role}:{field_id}",
                "fact_class": "occupation_industry_concept",
                "status": "established_from_codebook_bytes",
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": role,
                "job_slot": job_slot,
                "field_purpose": purpose,
                "code_system": "1970_census_three_digit_grouped_map",
                "universe_status": (
                    "selected_original_sample_subset_per_source_description"
                ),
                "complete_exact_code_system_status": (
                    "registration_required_external_appendix"
                ),
                "information_date_basis": "retrospective_reference_year",
                "job_match_timing": ("retrospective_main_job_selected_subset"),
                **_fact_source_binding([row], columns),
            }
        )
    for wave, field_id in EARLY_SECONDARY_OCCUPATION_FIELDS:
        row = _required_codebook_field(
            by_coordinate,
            wave,
            field_id,
            "early secondary occupation",
        )
        facts.append(
            {
                "fact_id": f"early-secondary-occupation:{wave}:{field_id}",
                "fact_class": "occupation_industry_concept",
                "status": "established_from_codebook_bytes",
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": "head_or_reference_person",
                "job_slot": "secondary_job",
                "field_purpose": "occupation",
                "code_system": "broad_one_digit_source_groups",
                "universe_status": "source_description_and_code_map",
                "complete_exact_code_system_status": (
                    "not_applicable_broad_source_groups"
                ),
                "information_date_basis": "retrospective_reference_year",
                "job_match_timing": "secondary_job_not_further_resolved",
                **_fact_source_binding([row], columns),
            }
        )
    return facts


def _spouse_seam_facts(
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    columns, by_coordinate = _codebook_fields_by_coordinate(field_rows)
    facts: list[dict[str, Any]] = []
    for wave, field_id, remuneration_type in SPOUSE_SEAM_AMOUNT_FIELDS:
        row = _required_codebook_field(
            by_coordinate,
            wave,
            field_id,
            "spouse seam amount",
        )
        bound_rows = [row]
        if field_id == "V4379":
            business_row = _required_codebook_field(
                by_coordinate,
                wave,
                "V4382",
                "spouse seam business link",
            )
            if (
                "labor part of unincorporated business income is in V4379"
                not in (business_row[columns["full_source_description"]])
            ):
                raise DictionaryDriftError(
                    "1976 spouse mixed-income source link drifted"
                )
            bound_rows.append(business_row)
        facts.append(
            {
                "fact_id": f"spouse-seam-amount:{wave}:{field_id}",
                "fact_class": "spouse_annual_amount_concept",
                "status": (
                    "established_from_codebook_bytes"
                    if remuneration_type == "mixed"
                    else "amount_established_remuneration_type_residual"
                ),
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": "spouse_or_partner",
                "job_slot": "role_total",
                "field_purpose": "amount",
                "reporting_unit": "dollars",
                "reference_periodicity": "annual",
                "information_date_basis": "reference_year_end",
                "job_match_timing": (
                    "annual_role_amount_not_matched_to_interview_job"
                ),
                "remuneration_type": remuneration_type,
                **_fact_source_binding(bound_rows, columns),
            }
        )
    for field_id, purpose in SPOUSE_1976_CONTEXT_FIELDS:
        row = _required_codebook_field(
            by_coordinate,
            1976,
            field_id,
            "1976 spouse context",
        )
        facts.append(
            {
                "fact_id": f"spouse-1976-context:{field_id}",
                "fact_class": "spouse_job_context_concept",
                "status": "established_from_codebook_bytes",
                "interview_wave": 1976,
                "earnings_reference_year": 1975,
                "role": "spouse_or_partner",
                "job_slot": "current_job_branch",
                "field_purpose": purpose,
                "reporting_unit": "complete_source_categorical_code_map",
                "reference_periodicity": "current_interview_job_status",
                "information_date_basis": "interview_time",
                "job_match_timing": (
                    "not_established_against_annual_V4379_amount"
                ),
                **_fact_source_binding([row], columns),
            }
        )
    secondary_units = {
        "secondary_job_indicator": "complete_source_boolean_code_map",
        "occupation": "legacy_occupation_category_code",
        "extra_job_count": "count_of_extra_jobs",
        "hourly_amount": "dollars_and_cents_per_hour",
        "weeks_worked": "weeks_in_reference_year",
        "average_hours_per_week": "hours_per_week",
    }
    secondary_periodicities = {
        "secondary_job_indicator": "any_during_reference_year",
        "occupation": "first_reported_extra_job",
        "extra_job_count": "reference_year_total",
        "hourly_amount": "hourly",
        "weeks_worked": "reference_year_weeks",
        "average_hours_per_week": "weekly_average",
    }
    for wave, role, field_id, purpose in SPOUSE_SEAM_SECONDARY_JOB_FIELDS:
        row = _required_codebook_field(
            by_coordinate,
            wave,
            field_id,
            "1976-1978 secondary-job context",
        )
        first_reported = purpose in {"occupation", "hourly_amount"}
        facts.append(
            {
                "fact_id": f"secondary-job-context:{wave}:{field_id}",
                "fact_class": "secondary_job_context_concept",
                "status": "established_from_codebook_bytes",
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": role,
                "job_slot": "secondary_job_branch",
                "field_purpose": purpose,
                "reporting_unit": secondary_units[purpose],
                "reference_periodicity": secondary_periodicities[purpose],
                "information_date_basis": "reference_year",
                "job_match_timing": (
                    "first_reported_extra_job"
                    if first_reported
                    else "aggregate_extra_job_branch"
                ),
                "annual_role_total_attachment_status": (
                    "registration_required"
                ),
                **_fact_source_binding([row], columns),
            }
        )
    return facts


def _pre_er_role_total_facts(
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    columns, by_coordinate = _codebook_fields_by_coordinate(field_rows)
    facts: list[dict[str, Any]] = []
    for wave, role, field_id in PRE_ER_ROLE_TOTAL_FIELDS:
        row = _required_codebook_field(
            by_coordinate,
            wave,
            field_id,
            "pre-ER role total",
        )
        description = row[columns["full_source_description"]].lower()
        explicit_inclusion = (
            role == "head_or_reference_person" and wave != 1982
        ) or (role == "spouse_or_partner" and wave >= 1984)
        if explicit_inclusion and not (
            "farm" in description and "business" in description
        ):
            raise DictionaryDriftError(
                f"pre-ER inclusion anchor drifted: {wave}/{field_id}"
            )
        facts.append(
            {
                "fact_id": f"pre-er-role-total:{wave}:{role}",
                "fact_class": "role_total_amount_concept",
                "status": (
                    "established_including_farm_business_once"
                    if explicit_inclusion
                    else "role_total_established_component_mix_residual"
                ),
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": role,
                "job_slot": "role_total",
                "field_purpose": "amount",
                "reporting_unit": "dollars",
                "reference_periodicity": "annual",
                "information_date_basis": "reference_year_end",
                "job_match_timing": "not_applicable_role_total",
                "farm_business_in_total_status": (
                    "explicitly_included_exactly_once"
                    if explicit_inclusion
                    else "not_established_by_total_description"
                ),
                **_fact_source_binding([row], columns),
            }
        )
    split_1983 = _required_codebook_field(
        by_coordinate,
        1984,
        "V10254",
        "RY1983 farm/business split",
    )
    facts.append(
        {
            "fact_id": "pre-er-split-rule:1984:V10254",
            "fact_class": "farm_business_labor_asset_split_rule",
            "status": "established_from_codebook_bytes",
            "interview_wave": 1984,
            "earnings_reference_year": 1983,
            "roles": list(ROLES),
            "information_date_basis": "reference_year_end",
            "rule_scope": "hours_based_rule_first_explicit_in_codebooks",
            **_fact_source_binding([split_1983], columns),
        }
    )
    seam_rows = [
        _required_codebook_field(
            by_coordinate,
            1993,
            field_id,
            "RY1992 ownership/work split",
        )
        for field_id in (
            "V21733",
            "V21738",
            "V21803",
            "V21806",
            "V21807",
            "V23323",
            "V23324",
        )
    ]
    facts.append(
        {
            "fact_id": "pre-er-split-rule:1993:ownership_work_seam",
            "fact_class": "farm_business_labor_asset_split_rule",
            "status": "established_from_codebook_bytes",
            "interview_wave": 1993,
            "earnings_reference_year": 1992,
            "roles": list(ROLES),
            "information_date_basis": "reference_year_end",
            "rule_scope": (
                "ownership_and_work_based_1992_rule_and_exact_once_totals"
            ),
            **_fact_source_binding(seam_rows, columns),
        }
    )
    return facts


def _er_total_role(label: str) -> str | None:
    normalized = " ".join(label.split())
    if (
        normalized.startswith("LABOR INCOME OF HEAD")
        or normalized == "LABOR INCOME-HEAD"
        or normalized.startswith("LABOR INCOME OF REF PERSON")
    ):
        return "head_or_reference_person"
    if (
        normalized.startswith("LABOR INCOME OF WIFE")
        or normalized == "LABOR INCOME-WIFE"
        or normalized.startswith("LABOR INCOME OF SPOUSE")
    ):
        return "spouse_or_partner"
    return None


def _bounded_description_segment(
    description: str,
    *,
    start_markers: Sequence[str],
    stop_markers: Sequence[str],
) -> str:
    """Return source prose between explicit semantic paragraph anchors."""

    lowered = description.lower()
    starts = [
        lowered.find(marker.lower())
        for marker in start_markers
        if lowered.find(marker.lower()) >= 0
    ]
    if not starts:
        return ""
    start = min(starts)
    stops = [
        lowered.find(marker.lower(), start + 1)
        for marker in stop_markers
        if lowered.find(marker.lower(), start + 1) >= 0
    ]
    end = min(stops) if stops else len(description)
    return description[start:end]


def _er_role_total_facts(
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    columns, by_coordinate = _codebook_fields_by_coordinate(field_rows)
    facts: list[dict[str, Any]] = []
    totals_by_wave: dict[int, set[str]] = {}
    for row in field_rows:
        label = row[columns["exact_codebook_short_label"]]
        role = _er_total_role(label)
        if role is None:
            continue
        wave = row[columns["interview_wave"]]
        description = row[columns["full_source_description"]]
        lowered = description.lower()
        if "labor income" not in lowered or not (
            "excluding" in lowered
            and "farm" in lowered
            and "business" in lowered
        ):
            raise DictionaryDriftError(
                "ER role-total exclusion lineage drifted: "
                f"{wave}/{row[columns['raw_field_id']]}"
            )
        totals_by_wave.setdefault(wave, set()).add(role)
        referenced_ids = [
            field_id
            for field_id in dict.fromkeys(
                re.findall(r"\b(?:ER|V)[0-9]+(?:_[A-Z0-9]+)?\b", description)
            )
            if (wave, field_id) in by_coordinate
            and field_id != row[columns["raw_field_id"]]
        ]
        included_text = _bounded_description_segment(
            description,
            start_markers=(
                "the income reported here",
                "this variable is the sum",
            ),
            stop_markers=(
                "note that",
                "all missing",
                "dollar amounts",
                "new immigrant",
                "values were",
            ),
        )
        excluded_text = _bounded_description_segment(
            description,
            start_markers=("note that",),
            stop_markers=(
                "all missing",
                "dollar amounts",
                "new immigrant",
                "values were",
            ),
        )
        included_reference_ids = set(
            re.findall(
                r"\b(?:ER|V)[0-9]+(?:_[A-Z0-9]+)?\b",
                included_text,
            )
        )
        excluded_reference_ids = set(
            re.findall(
                r"\b(?:ER|V)[0-9]+(?:_[A-Z0-9]+)?\b",
                excluded_text,
            )
        )
        included_ids = [
            field_id
            for field_id in referenced_ids
            if field_id in included_reference_ids
        ]
        excluded_ids = [
            field_id
            for field_id in referenced_ids
            if field_id in excluded_reference_ids
        ]
        if set(included_ids) & set(excluded_ids):
            raise DictionaryDriftError(
                "ER role-total component is both included and excluded: "
                f"{wave}/{row[columns['raw_field_id']]}"
            )
        component_ids = [*included_ids, *excluded_ids]
        bound_rows = [
            row,
            *[by_coordinate[(wave, field_id)] for field_id in component_ids],
        ]
        facts.append(
            {
                "fact_id": (
                    f"er-role-total:{wave}:{role}:"
                    f"{row[columns['raw_field_id']]}"
                ),
                "fact_class": "er_role_total_component_reconciliation",
                "status": "established_from_codebook_bytes",
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": role,
                "job_slot": "role_total",
                "field_purpose": "amount",
                "reporting_unit": "dollars",
                "reference_periodicity": "annual",
                "information_date_basis": "reference_year_tax_year",
                "job_match_timing": "not_applicable_role_total",
                "remuneration_type": "wage_type_excluding_farm_business",
                "inventory_year_disposition": (
                    "inventory_only_post_cutoff"
                    if wave in POST_CUTOFF_INVENTORY_WAVES
                    else "direct_questionnaire"
                ),
                "included_component_raw_field_ids": included_ids,
                "excluded_component_raw_field_ids": excluded_ids,
                "component_reconciliation_status": (
                    "raw_ids_enumerated_in_total_description"
                    if included_ids
                    else "concepts_only_or_total_only_in_source_description"
                ),
                **_fact_source_binding(bound_rows, columns),
            }
        )
    expected_waves = {row[columns["interview_wave"]] for row in field_rows}
    if totals_by_wave != {wave: set(ROLES) for wave in expected_waves}:
        raise DictionaryDriftError(
            "ER role-total domain is not exactly two roles per wave"
        )
    return facts


_MODERN_JOB_QUESTIONS = {
    "6",
    "20",
    "21",
    "22",
    "23",
    "24",
    "29",
    "30",
    "31",
    "32",
    "32A",
    "33",
    "34",
    "34A",
    "36",
    "37",
    "38",
    "39",
    "41",
    "42A",
    "43",
    "44",
    "45",
    "46",
}
_MODERN_JOB_LABEL_RE = re.compile(r"^(BC|DE)([0-9]+[A-Z]?)\s+(.+)$")
_MODERN_CURRENT_MAIN_JOB_QUESTIONS = {
    "29",
    "30",
    "31",
    "32",
    "32A",
    "33",
    "34",
    "34A",
    "36",
    "37",
    "38",
    "39",
    "41",
}
_MODERN_REFERENCE_YEAR_QUESTIONS = {
    "42A",
    "43",
    "44",
    "45",
    "46",
}


def _modern_is_reporting_unit_label(text: str) -> bool:
    return bool(
        " TIME UNIT" in f" {text}"
        or " PER WHAT" in f" {text}"
        or text.endswith(" PER")
        or " PER FOR " in f" {text}"
    )


def _modern_field_purpose(question: str, text: str) -> str:
    if question == "6":
        if "BEGINNING MONTH" in text:
            return "employment_spell_start_month"
        if "BEGINNING YEAR" in text:
            return "employment_spell_start_year"
        if "ENDING MONTH" in text:
            return "employment_spell_end_month"
        if "ENDING YEAR" in text:
            return "employment_spell_end_year"
        if "WTR EMPLOYED" in text:
            return "monthly_employment_indicator"
        raise DictionaryDriftError(
            f"unadjudicated modern question 6 subtype: {text}"
        )
    if question == "20":
        return "occupation"
    if question == "21":
        return "industry"
    if question == "22":
        return "employee_self_or_mixed"
    if question == "23":
        return "incorporation"
    if question == "24":
        return "government_level"
    if question == "29":
        return "pay_basis"
    if question == "30":
        return (
            "reporting_unit"
            if _modern_is_reporting_unit_label(text)
            else "salary_amount"
        )
    if question == "31":
        return "salaried_overtime_pay_indicator"
    if question == "32":
        return "salaried_overtime_pay_basis"
    if question == "32A":
        return (
            "reporting_unit"
            if _modern_is_reporting_unit_label(text)
            else "salaried_overtime_rate"
        )
    if question == "33":
        return "regular_hourly_wage_rate"
    if question == "34":
        return "hourly_overtime_pay_basis"
    if question == "34A":
        return (
            "reporting_unit"
            if _modern_is_reporting_unit_label(text)
            else "hourly_overtime_rate"
        )
    if question == "36":
        return (
            "reporting_unit"
            if _modern_is_reporting_unit_label(text)
            else "tips_amount"
        )
    if question == "37":
        return (
            "reporting_unit"
            if _modern_is_reporting_unit_label(text)
            else "commission_amount"
        )
    if question == "38":
        return "other_pay_basis"
    if question == "39":
        return "extra_hour_earnings_rate"
    if question == "41":
        for token, purpose in (
            ("YRS", "employer_tenure_years"),
            ("MOS", "employer_tenure_months"),
            ("WKS", "employer_tenure_weeks"),
        ):
            if re.search(rf"\b{token}\b", text):
                return purpose
        raise DictionaryDriftError(
            f"unadjudicated modern question 41 subtype: {text}"
        )
    if question == "42A":
        return "weeks_worked"
    if question == "43":
        return "average_hours_per_week"
    if question == "44":
        return "overtime_indicator"
    if question == "45":
        return (
            "reporting_unit"
            if _modern_is_reporting_unit_label(text)
            else "overtime_hours"
        )
    if question == "46":
        return (
            "reporting_unit"
            if _modern_is_reporting_unit_label(text)
            else "amount"
        )
    raise DictionaryDriftError(
        f"unadjudicated modern question subtype: {question}/{text}"
    )


def _modern_reporting_unit(
    question: str,
    purpose: str,
    row: Sequence[Any],
    columns: Mapping[str, int],
) -> str | list[str]:
    if purpose == "reporting_unit":
        missing_indices = set(row[columns["missing_code_map_indices"]])
        return [
            code_row[3]
            for index, code_row in enumerate(row[columns["code_map"]])
            if index not in missing_indices
        ]
    exact_units = {
        "employment_spell_start_month": "calendar_month_or_season",
        "employment_spell_end_month": "calendar_month_or_season",
        "employment_spell_start_year": "calendar_year",
        "employment_spell_end_year": "calendar_year",
        "monthly_employment_indicator": "complete_source_indicator_code_map",
        "weeks_worked": "weeks",
        "average_hours_per_week": "hours_per_week",
        "overtime_indicator": "complete_source_indicator_code_map",
        "overtime_hours": "hours",
        "occupation": "source_occupation_code",
        "industry": "source_industry_code",
        "employee_self_or_mixed": "complete_source_categorical_code_map",
        "incorporation": "complete_source_indicator_code_map",
        "government_level": "complete_source_government_level_code_map",
        "pay_basis": "complete_source_categorical_code_map",
        "salaried_overtime_pay_indicator": (
            "complete_source_indicator_code_map"
        ),
        "salaried_overtime_pay_basis": (
            "complete_source_categorical_code_map"
        ),
        "hourly_overtime_pay_basis": ("complete_source_categorical_code_map"),
        "other_pay_basis": "complete_source_categorical_code_map",
        "employer_tenure_years": "years",
        "employer_tenure_months": "months",
        "employer_tenure_weeks": "weeks",
        "salary_amount": (
            "dollars_and_cents_paired_with_source_reporting_unit"
        ),
        "salaried_overtime_rate": (
            "dollars_and_cents_paired_with_source_reporting_unit"
        ),
        "regular_hourly_wage_rate": "dollars_and_cents_per_hour",
        "hourly_overtime_rate": (
            "dollars_and_cents_paired_with_source_reporting_unit"
        ),
        "tips_amount": ("dollars_and_cents_paired_with_source_reporting_unit"),
        "commission_amount": (
            "source_monetary_amount_paired_with_reporting_unit"
        ),
        "extra_hour_earnings_rate": "dollars_and_cents_per_hour",
    }
    if purpose == "amount":
        if question == "46":
            return "signed_dollars_and_cents"
    return exact_units[purpose]


def _modern_reference_periodicity(question: str, purpose: str) -> str:
    if purpose in {
        "employment_spell_start_month",
        "employment_spell_start_year",
        "employment_spell_end_month",
        "employment_spell_end_year",
    }:
        return "employment_spell_event_date"
    if purpose == "monthly_employment_indicator":
        return "named_reference_year_month"
    if question in _MODERN_CURRENT_MAIN_JOB_QUESTIONS:
        if purpose.startswith("employer_tenure_"):
            return "current_employer_tenure_as_of_interview"
        return "current_main_job_pay_basis_at_interview"
    if question == "42A":
        return "reference_year_weeks"
    if question == "43":
        return "weekly_average_over_reference_year_job_period"
    if question == "44":
        return "any_during_reference_year_job_period"
    if question == "45":
        return "paired_source_time_unit_over_reference_year_job_period"
    if question == "46":
        return "paired_source_time_unit_for_reference_year_job_amount"
    if question in {"20", "21", "22", "23", "24"}:
        return "enumerated_source_job_identity_as_reported_at_interview"
    raise DictionaryDriftError(
        f"unadjudicated modern periodicity: {question}/{purpose}"
    )


def _modern_job_context_facts(
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    columns, _ = _codebook_fields_by_coordinate(field_rows)
    facts: list[dict[str, Any]] = []
    for row in field_rows:
        label = " ".join(row[columns["exact_codebook_short_label"]].split())
        match = _MODERN_JOB_LABEL_RE.fullmatch(label)
        if match is None or match.group(2) not in _MODERN_JOB_QUESTIONS:
            continue
        block, question, text = match.groups()
        purpose = _modern_field_purpose(question, text)
        wave = row[columns["interview_wave"]]
        field_id = row[columns["raw_field_id"]]
        description = row[columns["full_source_description"]]
        source_text = "\n".join(
            [
                description,
                *[code_row[3] for code_row in row[columns["code_map"]]],
            ]
        )
        job_match = re.search(r"(?:--|-)?JOB\s+([1-4])\b", text)
        if job_match is not None:
            job_slot = f"job_{job_match.group(1)}"
            job_match_timing = "explicit_source_job_number"
        elif question in _MODERN_CURRENT_MAIN_JOB_QUESTIONS:
            normalized_description = " ".join(description.split()).upper()
            if "CURRENT MAIN JOB" not in normalized_description:
                raise DictionaryDriftError(
                    "modern current-main-job anchor drifted: "
                    f"{wave}/{field_id}/{block}{question}"
                )
            job_slot = "current_main_job"
            job_match_timing = "explicit_current_main_job_wording"
        else:
            raise DictionaryDriftError(
                "modern job attachment is unadjudicated: "
                f"{wave}/{field_id}/{block}{question}"
            )
        reference_year_question = question in _MODERN_REFERENCE_YEAR_QUESTIONS
        if reference_year_question and str(wave - 1) not in source_text:
            raise DictionaryDriftError(
                "modern reference-year anchor drifted: "
                f"{wave}/{field_id}/{block}{question}"
            )
        if (
            purpose == "monthly_employment_indicator"
            and str(wave - 1) not in source_text
        ):
            raise DictionaryDriftError(
                "modern reference-year-month anchor drifted: "
                f"{wave}/{field_id}/{block}{question}"
            )
        event_date_question = question == "6" and purpose != (
            "monthly_employment_indicator"
        )
        facts.append(
            {
                "fact_id": f"modern-job-context:{wave}:{field_id}",
                "fact_class": "modern_bc_de_questionnaire_field",
                "status": "established_from_codebook_bytes",
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": (
                    "head_or_reference_person"
                    if block == "BC"
                    else "spouse_or_partner"
                ),
                "source_block": block,
                "source_question_id": f"{block}{question}",
                "job_slot": job_slot,
                "field_purpose": purpose,
                "reporting_unit": _modern_reporting_unit(
                    question,
                    purpose,
                    row,
                    columns,
                ),
                "reference_periodicity": _modern_reference_periodicity(
                    question,
                    purpose,
                ),
                "information_date_basis": (
                    "reference_year"
                    if reference_year_question
                    else (
                        "employment_spell_event_date"
                        if event_date_question
                        else (
                            "reference_year_month"
                            if purpose == "monthly_employment_indicator"
                            else "interview_time"
                        )
                    )
                ),
                "job_match_timing": job_match_timing,
                **_fact_source_binding([row], columns),
            }
        )
    if not facts:
        raise DictionaryDriftError("modern BC/DE fact domain is empty")
    return facts


def _regular_school_enrollment_facts(
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    columns, by_coordinate = _codebook_fields_by_coordinate(field_rows)
    present_waves = {row[columns["interview_wave"]] for row in field_rows}
    new_role_fields = {
        (wave, role, endpoint_field_id): (
            checkpoint_field_id,
            still_in_college_month_field_id,
            still_in_college_year_field_id,
        )
        for (
            wave,
            role,
            checkpoint_field_id,
            still_in_college_month_field_id,
            still_in_college_year_field_id,
            endpoint_field_id,
        ) in NEW_ROLE_ENROLLMENT_BRANCH_FIELDS
    }
    facts: list[dict[str, Any]] = []
    for wave, role, branch, field_id in ENROLLMENT_REGULAR_SCHOOL_FIELDS:
        if wave not in present_waves:
            continue
        row = _required_codebook_field(
            by_coordinate,
            wave,
            field_id,
            "regular-school enrollment",
        )
        description = row[columns["full_source_description"]]
        meanings = [
            code_row[3].lower() for code_row in row[columns["code_map"]]
        ]
        if (
            "regular school" not in description.lower()
            or not any(meaning == "yes" for meaning in meanings)
            or not any(meaning == "no" for meaning in meanings)
        ):
            raise DictionaryDriftError(
                f"regular-school source anchors drifted: {wave}/{field_id}"
            )
        bound_rows = [row]
        universe_status = "source_description_and_code_map"
        branch_binding: dict[str, Any] = {}
        if branch == "new_role_background":
            try:
                (
                    checkpoint_field_id,
                    still_in_college_month_field_id,
                    still_in_college_year_field_id,
                ) = new_role_fields[(wave, role, field_id)]
            except KeyError as error:
                raise DictionaryDriftError(
                    "new-role regular-school branch binding is absent: "
                    f"{wave}/{role}/{field_id}"
                ) from error
            checkpoint_row = _required_codebook_field(
                by_coordinate,
                wave,
                checkpoint_field_id,
                "new-role enrollment universe checkpoint",
            )
            still_in_college_month_row = _required_codebook_field(
                by_coordinate,
                wave,
                still_in_college_month_field_id,
                "new-role enrollment still-in-college month",
            )
            still_in_college_year_row = _required_codebook_field(
                by_coordinate,
                wave,
                still_in_college_year_field_id,
                "new-role enrollment still-in-college year",
            )
            checkpoint_description = " ".join(
                checkpoint_row[columns["full_source_description"]]
                .lower()
                .split()
            )
            if not all(
                anchor in checkpoint_description
                for anchor in (
                    "have not had a designation",
                    "split-off",
                    "recontact interviews",
                    "carried forward",
                )
            ):
                raise DictionaryDriftError(
                    "new-role enrollment universe anchors drifted: "
                    f"{wave}/{checkpoint_field_id}"
                )
            month_map = still_in_college_month_row[columns["code_map"]]
            year_map = still_in_college_year_row[columns["code_map"]]
            if not any(
                code_row[2] == "96"
                and code_row[3].lower() == "still in school"
                for code_row in month_map
            ) or not any(
                code_row[2] == "9,996"
                and code_row[3].lower() == "still in school"
                for code_row in year_map
            ):
                raise DictionaryDriftError(
                    "new-role still-in-college anchors drifted: "
                    f"{wave}/{role}"
                )
            inapplicable_meanings = [
                code_row[3]
                for code_row in row[columns["code_map"]]
                if code_row[2] == "0"
            ]
            normalized_inapplicable = " ".join(inapplicable_meanings).replace(
                ",", ""
            )
            if (
                len(inapplicable_meanings) != 1
                or f"{still_in_college_month_field_id}=96"
                not in normalized_inapplicable
                or f"{still_in_college_year_field_id}=9996"
                not in normalized_inapplicable
            ):
                raise DictionaryDriftError(
                    "new-role 61A inapplicability anchors drifted: "
                    f"{wave}/{field_id}"
                )
            bound_rows = [
                checkpoint_row,
                still_in_college_month_row,
                still_in_college_year_row,
                row,
            ]
            universe_status = (
                "checkpoint_establishes_new_splitoff_recontact_branch"
            )
            branch_binding = {
                "universe_checkpoint_raw_field_id": checkpoint_field_id,
                "upstream_still_in_college_raw_field_ids": [
                    still_in_college_month_field_id,
                    still_in_college_year_field_id,
                ],
                "endpoint_raw_field_id": field_id,
                "endpoint_inapplicability_status": (
                    "bound_to_upstream_still_in_college_codes"
                ),
            }
        facts.append(
            {
                "fact_id": f"regular-school:{wave}:{role}:{branch}",
                "fact_class": "regular_school_enrollment_branch",
                "status": "established_from_codebook_bytes",
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": role,
                "job_slot": "not_applicable_person_status",
                "field_purpose": "enrollment",
                "branch": branch,
                "universe_status": universe_status,
                "information_date_basis": (
                    "explicit_current_interview_time"
                    if wave >= 2019
                    else "current_label_question_wording_not_explicit"
                ),
                "job_match_timing": "not_applicable_person_status",
                "stable_cross_wave_mapping_status": (
                    "registration_required_branch_and_freshness_composite"
                ),
                **branch_binding,
                **_fact_source_binding(bound_rows, columns),
            }
        )
    return facts


def _pre_2013_enrollment_like_facts(
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    columns, _ = _codebook_fields_by_coordinate(field_rows)
    facts: list[dict[str, Any]] = []
    for row in field_rows:
        wave = row[columns["interview_wave"]]
        if wave >= 2013:
            continue
        matching_indices = [
            index
            for index, code_row in enumerate(row[columns["code_map"]])
            if re.search(
                r"\bstill in (?:school|college)\b",
                code_row[3],
                flags=re.IGNORECASE,
            )
        ]
        if not matching_indices:
            continue
        field_id = row[columns["raw_field_id"]]
        facts.append(
            {
                "fact_id": f"pre-2013-enrollment-like:{wave}:{field_id}",
                "fact_class": ("lexical_enrollment_like_code_non_evidentiary"),
                "status": ("observed_not_evidence_for_current_regular_school"),
                "interview_wave": wave,
                "earnings_reference_year": wave - 1,
                "role": "not_adjudicated_from_lexical_match",
                "job_slot": "not_applicable_person_status",
                "field_purpose": "lexical_search_lead",
                "matching_code_map_indices": matching_indices,
                "universe_status": "not_adjudicated_from_lexical_match",
                "information_date_basis": (
                    "background_or_last_attended_freshness_not_established"
                ),
                "job_match_timing": "not_applicable_person_status",
                "regular_school_equivalence_status": (
                    "non_evidentiary_not_established"
                ),
                **_fact_source_binding([row], columns),
            }
        )
    return facts


def _era_facts(
    era_id: str,
    field_rows: Sequence[Sequence[Any]],
) -> list[dict[str, Any]]:
    if era_id == "wave1968_ry1968_1974_early_totals":
        facts = _early_role_total_facts(field_rows)
    elif era_id == "ry1975_1977_spouse_concept_seam":
        facts = _spouse_seam_facts(field_rows)
    elif era_id == "ry1978_1992_pre_er_totals":
        facts = _pre_er_role_total_facts(field_rows)
    elif era_id == "ry1993_2001_er_transition":
        facts = _er_role_total_facts(field_rows)
    else:
        facts = [
            *_er_role_total_facts(field_rows),
            *_modern_job_context_facts(field_rows),
            *_regular_school_enrollment_facts(field_rows),
        ]
    facts.extend(_pre_2013_enrollment_like_facts(field_rows))
    return facts


def _era_residuals(
    era_id: str,
    waves: Sequence[int],
    field_rows: Sequence[Sequence[Any]],
    manifest: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    residuals = [
        {
            "residual_id": f"{era_id}:fixed_width_missing_token_grammar",
            "status": "registration_required",
            "missing_fact": (
                "Exact fixed-width raw tokens for every displayed missing, "
                "unknown, refused, and inapplicable code or uncoded blank."
            ),
            "registration_required_item": (
                "source grammar that proves padding, sign, blank, and "
                "sentinel bytes for every field"
            ),
            "searched_interview_waves": list(waves),
            "searched_codebook_field_count": len(field_rows),
        },
        {
            "residual_id": f"{era_id}:family_archive_capture_record",
            "status": "registration_required",
            "missing_fact": (
                "Original family-archive retrieval URL and exact retrieval "
                "timestamp."
            ),
            "registration_required_item": (
                "original family-archive network capture record"
            ),
            "searched_interview_waves": list(waves),
            "searched_codebook_document_ids": [
                row["document_id"]
                for row in manifest
                if row["dictionary_role"] == "family_codebook"
            ],
            "established_local_provenance": (
                "registered PDF bytes equal the sole matching PDF member "
                "of a path/size/SHA-256-pinned local family archive"
            ),
        },
        {
            "residual_id": f"{era_id}:questionnaire_slot_closure",
            "status": "registration_required",
            "missing_fact": (
                "Questionnaire-exhaustive role/job/component/context "
                "hierarchy and absence proof for every unsupported slot."
            ),
            "registration_required_item": (
                "official questionnaire/flow bytes and a ratified "
                "codebook-to-questionnaire slot taxonomy"
            ),
            "searched_interview_waves": list(waves),
            "searched_codebook_field_count": len(field_rows),
        },
    ]
    if era_id == "wave1968_ry1968_1974_early_totals":
        residuals.extend(
            [
                {
                    "residual_id": (
                        f"{era_id}:unsupported_job_context_absence_proofs"
                    ),
                    "status": "registration_required",
                    "missing_fact": (
                        "Questionnaire-exhaustive absence proof for every "
                        "unsupported early job, component, context, and "
                        "35-purpose slot."
                    ),
                    "registration_required_item": (
                        "complete early questionnaire bytes or a ratified "
                        "codebook-to-questionnaire slot taxonomy"
                    ),
                    "searched_interview_waves": list(waves),
                    "searched_codebook_field_count": len(field_rows),
                },
                {
                    "residual_id": (
                        f"{era_id}:occupation_industry_attachment_closure"
                    ),
                    "status": "registration_required",
                    "missing_fact": (
                        "Exact three-digit meanings, selected-sample "
                        "attachment, secondary-job industry, spouse-secondary "
                        "fields, and exhaustive absence for unsupported "
                        "occupation/industry slots."
                    ),
                    "registration_required_item": (
                        "V-B5: Appendix V2/Wave XIV, 1968-1980 "
                        "Retrospective Occupation-Industry Files "
                        "Documentation, and official questionnaires"
                    ),
                    "searched_interview_waves": list(waves),
                    "searched_codebook_field_count": len(field_rows),
                },
            ]
        )
    elif era_id == "ry1975_1977_spouse_concept_seam":
        residuals.extend(
            [
                {
                    "residual_id": f"{era_id}:V-B6:V5289_V5788_concept",
                    "status": "registration_required",
                    "missing_fact": (
                        "Whether V5289 and V5788 include spouse "
                        "unincorporated-business labor or are wages-only."
                    ),
                    "registration_required_item": (
                        "V-B6: official questionnaire/editing instructions"
                    ),
                    "searched_interview_waves": [1977, 1978],
                    "searched_raw_field_ids": ["V5289", "V5788"],
                },
                {
                    "residual_id": f"{era_id}:V-B6:annual_job_match",
                    "status": "registration_required",
                    "missing_fact": (
                        "Binding of 1976 interview-time current-job context "
                        "to annual V4379 and equivalent 1977/1978 spouse "
                        "current-job context or structural absence."
                    ),
                    "registration_required_item": (
                        "V-B6: questionnaire flow and timing/attachment "
                        "documentation"
                    ),
                    "searched_interview_waves": list(waves),
                    "searched_raw_field_ids": [
                        "V4844",
                        "V4845",
                        "V4850",
                        "V4855",
                        "V4858",
                    ],
                },
                {
                    "residual_id": f"{era_id}:V-B6:government_level_absence",
                    "status": "registration_required",
                    "missing_fact": (
                        "Federal/state/local government level for the spouse "
                        "job, or questionnaire-exhaustive proof that only a "
                        "government-employer yes/no distinction was asked."
                    ),
                    "registration_required_item": (
                        "V-B6: official questionnaire flow and exhaustive "
                        "government-level absence proof"
                    ),
                    "searched_interview_waves": [1976],
                    "searched_raw_field_ids": ["V4845", "V4850"],
                    "established_codebook_finding": (
                        "Both fields are yes/no government-employer "
                        "indicators and do not encode the level."
                    ),
                },
                {
                    "residual_id": (
                        f"{era_id}:V-B6:secondary_job_attachment_and_absence"
                    ),
                    "status": "registration_required",
                    "missing_fact": (
                        "Attachment of the 1976 spouse secondary-job branch "
                        "to annual V4379/V5289/V5788, plus whether an "
                        "equivalent spouse branch is structurally absent in "
                        "1977/1978 and the allocation of its components."
                    ),
                    "registration_required_item": (
                        "V-B6: official questionnaire/flow/editing bytes for "
                        "secondary-job attachment and absence proof"
                    ),
                    "searched_interview_waves": list(waves),
                    "searched_raw_field_ids": [
                        "V4518",
                        "V4519",
                        "V4520",
                        "V4521",
                        "V4522",
                        "V4523",
                        "V4901",
                        "V4902",
                        "V4903",
                        "V4904",
                        "V4905",
                        "V4906",
                        "V5428",
                        "V5429",
                        "V5430",
                        "V5431",
                        "V5432",
                        "V5433",
                        "V5915",
                        "V5916",
                        "V5917",
                        "V5918",
                        "V5919",
                        "V5920",
                    ],
                },
            ]
        )
    elif era_id == "ry1978_1992_pre_er_totals":
        residuals.append(
            {
                "residual_id": f"{era_id}:early_split_and_inclusion",
                "status": "registration_required",
                "missing_fact": (
                    "RY1978-1982 labor/asset split algorithm and spouse "
                    "farm/business inclusion, plus RY1981 V8690 component "
                    "composition."
                ),
                "registration_required_item": (
                    "PSID processing/editing instructions for RY1978-1982"
                ),
                "searched_interview_waves": list(range(1979, 1984)),
                "searched_raw_field_ids": [
                    "V6398",
                    "V6988",
                    "V7580",
                    "V8273",
                    "V8881",
                    "V8690",
                ],
            }
        )
    elif era_id == "ry1993_2001_er_transition":
        residuals.extend(
            [
                {
                    "residual_id": f"{era_id}:role_farm_labor_allocation",
                    "status": "registration_required",
                    "missing_fact": (
                        "Pure head/spouse farm-labor amounts: each ER farm "
                        "field combines labor and asset income and its "
                        "published role-allocation cross-reference uses an "
                        "unavailable code."
                    ),
                    "registration_required_item": (
                        "corrected PSID farm allocation/editing source"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": f"{era_id}:edited_total_reconciliation",
                    "status": "registration_required",
                    "missing_fact": (
                        "A source rule resolving rounding/editing/sample-gap "
                        "differences between edited role totals and detailed "
                        "components."
                    ),
                    "registration_required_item": (
                        "PSID processing/editing instructions; edited total "
                        "must remain authoritative meanwhile"
                    ),
                    "searched_interview_waves": list(waves),
                },
            ]
        )
    elif era_id == "ry2002_2014_modern_bc_de":
        residuals.extend(
            [
                {
                    "residual_id": (
                        f"{era_id}:job_chronology_exposure_attachment"
                    ),
                    "status": "registration_required",
                    "missing_fact": (
                        "Questionnaire-flow attachment among Q6 employment "
                        "spell dates/months, Q42A weeks, Q43 hours, Q44 "
                        "overtime, Q45 overtime hours/unit, and each stable "
                        "main/secondary job slot."
                    ),
                    "registration_required_item": (
                        "official BC/DE questionnaire branch flow and "
                        "main/secondary-job attachment rules"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": (
                        f"{era_id}:job_amount_role_total_reconciliation"
                    ),
                    "status": "registration_required",
                    "missing_fact": (
                        "Exact reconciliation of Q32A/Q34A current-job "
                        "overtime pay and Q46 reference-year job amounts to "
                        "the edited head/spouse role totals."
                    ),
                    "registration_required_item": (
                        "PSID editing/component allocation instructions "
                        "binding job amounts to role totals"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": f"{era_id}:role_farm_labor_allocation",
                    "status": "registration_required",
                    "missing_fact": (
                        "Pure role-specific farm labor carried outside the "
                        "farm/business-excluding edited role totals; "
                        "available aggregate fields do not establish the "
                        "role allocation."
                    ),
                    "registration_required_item": (
                        "corrected PSID farm allocation/editing source"
                    ),
                    "searched_interview_waves": list(waves),
                    "searched_aggregate_raw_field_ids": [
                        "ER21855",
                        "ER21870",
                        "ER24109",
                        "ER24111",
                    ],
                },
                {
                    "residual_id": f"{era_id}:edited_total_reconciliation",
                    "status": "registration_required",
                    "missing_fact": (
                        "A source rule resolving rounding, editing, and "
                        "sample-gap differences between edited role totals "
                        "and detailed BC/DE/job components."
                    ),
                    "registration_required_item": (
                        "PSID processing/editing instructions; edited total "
                        "must remain authoritative meanwhile"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": f"{era_id}:V-B8:branch_freshness",
                    "status": "registration_required",
                    "missing_fact": (
                        "2013 new-role non-college enrollment coverage and "
                        "a freshness-safe composite of 61A, 84, and upstream "
                        "still-in-school/college codes."
                    ),
                    "registration_required_item": (
                        "V-B8: questionnaire branch/carry-forward rules and "
                        "ratified composite mapping"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": (
                        f"{era_id}:V-B8:"
                        "pre_2013_questionnaire_absence_proof"
                    ),
                    "status": "registration_required",
                    "missing_fact": (
                        "Questionnaire-exhaustive proof that no current "
                        "head/spouse regular-school item exists before 2013; "
                        "lexical still-in-school/college code hits are "
                        "background search leads, not role/universe evidence."
                    ),
                    "registration_required_item": (
                        "V-B8: official questionnaires and flow/universe "
                        "documentation for every 1968-2011 interview wave"
                    ),
                    "searched_interview_waves": [
                        wave for wave in INTERVIEW_WAVES if wave < 2013
                    ],
                    "searched_codebook_evidence_eras": [
                        era_name
                        for era_name, era_waves in CODEBOOK_ERA_SPECS
                        if any(wave < 2013 for wave in era_waves)
                    ],
                    "codebook_lexical_search_evidentiary_status": (
                        "non_evidentiary_for_questionnaire_absence"
                    ),
                },
            ]
        )
    elif era_id == "ry2015_2022_exclusion_lineage":
        residuals.extend(
            [
                {
                    "residual_id": (
                        f"{era_id}:job_chronology_exposure_attachment"
                    ),
                    "status": "registration_required",
                    "missing_fact": (
                        "Questionnaire-flow attachment among Q6 employment "
                        "spell dates/months, Q43 hours, Q44 overtime, Q45 "
                        "overtime hours/unit, and each stable job slot."
                    ),
                    "registration_required_item": (
                        "official BC/DE questionnaire branch flow and "
                        "main/secondary-job attachment rules"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": (
                        f"{era_id}:job_amount_role_total_reconciliation"
                    ),
                    "status": "registration_required",
                    "missing_fact": (
                        "Exact reconciliation of Q32A/Q34A current-job "
                        "overtime pay and Q46 reference-year job amounts to "
                        "the edited head/spouse role totals."
                    ),
                    "registration_required_item": (
                        "PSID editing/component allocation instructions "
                        "binding job amounts to role totals"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": f"{era_id}:role_farm_labor_allocation",
                    "status": "registration_required",
                    "missing_fact": (
                        "Role-specific farm labor carried outside the "
                        "explicitly farm/business-excluding role totals."
                    ),
                    "registration_required_item": (
                        "corrected PSID farm allocation/editing source"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": f"{era_id}:edited_total_reconciliation",
                    "status": "registration_required",
                    "missing_fact": (
                        "A source rule resolving rounding, editing, and "
                        "sample-gap differences between edited role totals "
                        "and detailed BC/DE/job components."
                    ),
                    "registration_required_item": (
                        "PSID processing/editing instructions; edited total "
                        "must remain authoritative meanwhile"
                    ),
                    "searched_interview_waves": list(waves),
                },
                {
                    "residual_id": f"{era_id}:V-B8:branch_freshness",
                    "status": "registration_required",
                    "missing_fact": (
                        "Freshness-safe composite of new-role 61A, "
                        "continuing-role 84, role-status branches, and "
                        "upstream still-in-school/college codes."
                    ),
                    "registration_required_item": (
                        "V-B8: questionnaire branch/carry-forward rules and "
                        "ratified composite mapping"
                    ),
                    "searched_interview_waves": list(waves),
                },
            ]
        )
    return residuals


def build_codebook_era_evidence(
    era_id: str,
    data_root: Path | None = None,
) -> dict[str, Any]:
    """Extract one complete era's codebook fields from pinned PDF bytes."""

    _pdftotext_version()
    root = default_psid_root() if data_root is None else Path(data_root)
    waves = _codebook_era_waves(era_id)
    audit = build_registration_required_audit(root)
    manifest = [
        row
        for row in audit["source_authority_manifest"]
        if row["interview_wave"] in waves
    ]
    physical_columns = {
        name: index for index, name in enumerate(PHYSICAL_FIELD_COLUMNS)
    }
    physical_by_wave = {
        wave: [
            row
            for row in audit["physical_fields"]
            if row[physical_columns["interview_wave"]] == wave
        ]
        for wave in waves
    }
    manifest_by_id = {row["document_id"]: row for row in manifest}
    field_rows: list[list[Any]] = []
    locators: list[dict[str, Any]] = []
    for wave in waves:
        codebook_document_id = f"psid-family-{wave}-codebook"
        codebook_document = manifest_by_id[codebook_document_id]
        codebook_path = root / codebook_document["path"]
        wave_fields, wave_locators = _extract_wave_codebook_evidence(
            wave=wave,
            codebook_path=codebook_path,
            codebook_document=codebook_document,
            physical_rows=physical_by_wave[wave],
        )
        field_rows.extend(wave_fields)
        locators.extend(wave_locators)

    field_keys = [
        row[CODEBOOK_FIELD_EVIDENCE_COLUMNS.index("codebook_field_key")]
        for row in field_rows
    ]
    locator_ids = [row["locator_id"] for row in locators]
    facts = _era_facts(era_id, field_rows)
    field_columns = {
        name: index
        for index, name in enumerate(CODEBOOK_FIELD_EVIDENCE_COLUMNS)
    }
    code_map_rows = [
        code_row
        for row in field_rows
        for code_row in row[field_columns["code_map"]]
    ]
    extraction_summary = {
        "field_count": len(field_rows),
        "description_line_count": sum(
            len(row[field_columns["full_source_description"]].splitlines())
            for row in field_rows
        ),
        "code_map_row_count": len(code_map_rows),
        "closed_range_count": sum(
            " - " in code_row[2] for code_row in code_map_rows
        ),
        "field_with_explicit_missing_count": sum(
            bool(row[field_columns["missing_code_map_indices"]])
            for row in field_rows
        ),
        "explicit_missing_code_row_count": sum(
            len(row[field_columns["missing_code_map_indices"]])
            for row in field_rows
        ),
        "multi_page_field_count": sum(
            len(row[field_columns["source_locator_ids"]]) > 1
            for row in field_rows
        ),
        "page_stream_locator_count": len(locators),
    }
    artifact: dict[str, Any] = {
        "schema_version": CODEBOOK_EVIDENCE_SCHEMA_VERSION,
        "artifact_id": f"{CODEBOOK_EVIDENCE_SCHEMA_VERSION}:{era_id}",
        "era_id": era_id,
        "interview_waves": list(waves),
        "earnings_reference_years": [wave - 1 for wave in waves],
        "source_authority_manifest": manifest,
        "source_authority_manifest_sha256": sha256_bytes(
            canonical_json_bytes(manifest)
        ),
        "extraction_method": {
            "tool": PDF_TEXT_EXTRACTION_TOOL,
            "tool_version": PDF_TEXT_EXTRACTION_VERSION,
            "command": (
                "pdftotext -layout -enc UTF-8 " "<registered-codebook-path> -"
            ),
            "derived_text_retained": True,
            "derived_text_evidentiary_status": ("locator_only_not_evidence"),
            "fact_binding": (
                "pinned_pdf_sha256_size_page_object_content_object_"
                "raw_stream_byte_range"
            ),
            "network_capture": False,
        },
        "extraction_summary": extraction_summary,
        "code_map_columns": list(CODEBOOK_CODE_MAP_COLUMNS),
        "field_evidence_columns": list(CODEBOOK_FIELD_EVIDENCE_COLUMNS),
        "field_evidence": field_rows,
        "field_evidence_count": len(field_rows),
        "field_evidence_keyset_sha256": sha256_bytes(
            canonical_json_bytes(field_keys)
        ),
        "source_locators": locators,
        "source_locator_count": len(locators),
        "source_locator_keyset_sha256": sha256_bytes(
            canonical_json_bytes(locator_ids)
        ),
        "era_facts": facts,
        "era_fact_count": len(facts),
        "registration_required_residuals": _era_residuals(
            era_id,
            waves,
            field_rows,
            manifest,
        ),
        "canonical_order": [
            "interview_wave",
            "physical_layout_coordinate",
        ],
        "integrity": {
            "canonicalization": (
                "UTF-8 JSON; keys sorted; no insignificant whitespace; "
                "content_sha256 computed with itself set to 64 zeroes"
            ),
            "content_sha256": _ZERO_SHA256,
            "reproduced_from_source_bytes": True,
        },
    }
    artifact["integrity"]["content_sha256"] = sha256_bytes(
        canonical_json_bytes(artifact)
    )
    validate_codebook_era_evidence(artifact)
    return artifact


def _validate_codebook_locator(locator: Mapping[str, Any]) -> None:
    required = {
        "locator_id",
        "source_document_id",
        "location_type",
        "pdf_page",
        "page_object",
        "content_object",
        "filter_chain",
        "declared_stream_length",
        "byte_start",
        "byte_end",
        "range_sha256",
        "decoded_stream_sha256",
        "decoded_raw_field_id_anchors",
        "derived_page_text_sha256",
    }
    if set(locator) != required:
        raise DictionaryDriftError("codebook locator schema drifted")
    if locator["location_type"] != "pdf_page_content_stream_raw_byte_range":
        raise DictionaryDriftError("codebook locator type drifted")
    if (
        isinstance(locator["pdf_page"], bool)
        or not isinstance(locator["pdf_page"], int)
        or locator["pdf_page"] < 1
    ):
        raise DictionaryDriftError("codebook locator page is invalid")
    if (
        locator["byte_end"] - locator["byte_start"]
        != locator["declared_stream_length"]
    ):
        raise DictionaryDriftError("codebook locator stream length drifted")
    preimage = [
        locator["source_document_id"],
        locator["pdf_page"],
        locator["page_object"],
        locator["content_object"],
        locator["byte_start"],
        locator["byte_end"],
        locator["range_sha256"],
    ]
    expected_id = (
        "psid-codebook-page:" f"{sha256_bytes(canonical_json_bytes(preimage))}"
    )
    if locator["locator_id"] != expected_id:
        raise DictionaryDriftError("codebook locator identity drifted")
    for name in (
        "range_sha256",
        "decoded_stream_sha256",
        "derived_page_text_sha256",
    ):
        if re.fullmatch(r"[0-9a-f]{64}", locator[name]) is None:
            raise DictionaryDriftError(
                f"codebook locator {name} is not SHA-256"
            )


def validate_codebook_era_evidence(artifact: Mapping[str, Any]) -> None:
    """Validate one ancillary codebook extraction without a crosswalk."""

    top_level_keys = {
        "schema_version",
        "artifact_id",
        "era_id",
        "interview_waves",
        "earnings_reference_years",
        "source_authority_manifest",
        "source_authority_manifest_sha256",
        "extraction_method",
        "extraction_summary",
        "code_map_columns",
        "field_evidence_columns",
        "field_evidence",
        "field_evidence_count",
        "field_evidence_keyset_sha256",
        "source_locators",
        "source_locator_count",
        "source_locator_keyset_sha256",
        "era_facts",
        "era_fact_count",
        "registration_required_residuals",
        "canonical_order",
        "integrity",
    }
    if set(artifact) != top_level_keys:
        raise DictionaryDriftError(
            "codebook evidence top-level schema drifted"
        )
    era_id = artifact["era_id"]
    waves = _codebook_era_waves(era_id)
    if artifact["schema_version"] != CODEBOOK_EVIDENCE_SCHEMA_VERSION:
        raise DictionaryDriftError("codebook evidence schema version drifted")
    if artifact["artifact_id"] != (
        f"{CODEBOOK_EVIDENCE_SCHEMA_VERSION}:{era_id}"
    ):
        raise DictionaryDriftError("codebook evidence artifact ID drifted")
    if artifact["interview_waves"] != list(waves):
        raise DictionaryDriftError("codebook evidence wave domain drifted")
    if artifact["earnings_reference_years"] != [wave - 1 for wave in waves]:
        raise DictionaryDriftError(
            "codebook evidence reference-year domain drifted"
        )
    manifest = artifact["source_authority_manifest"]
    if artifact["source_authority_manifest_sha256"] != sha256_bytes(
        canonical_json_bytes(manifest)
    ):
        raise DictionaryDriftError(
            "codebook evidence authority manifest hash drifted"
        )
    if artifact["code_map_columns"] != list(CODEBOOK_CODE_MAP_COLUMNS):
        raise DictionaryDriftError("codebook map columns drifted")
    if artifact["field_evidence_columns"] != list(
        CODEBOOK_FIELD_EVIDENCE_COLUMNS
    ):
        raise DictionaryDriftError("codebook field columns drifted")
    fields = artifact["field_evidence"]
    if artifact["field_evidence_count"] != len(fields):
        raise DictionaryDriftError("codebook field count drifted")
    columns = {
        name: index
        for index, name in enumerate(CODEBOOK_FIELD_EVIDENCE_COLUMNS)
    }
    field_keys = [row[columns["codebook_field_key"]] for row in fields]
    if len(field_keys) != len(set(field_keys)):
        raise DictionaryDriftError("duplicate codebook field key")
    if artifact["field_evidence_keyset_sha256"] != sha256_bytes(
        canonical_json_bytes(field_keys)
    ):
        raise DictionaryDriftError("codebook field keyset hash drifted")
    locators = artifact["source_locators"]
    if artifact["source_locator_count"] != len(locators):
        raise DictionaryDriftError("codebook locator count drifted")
    for locator in locators:
        _validate_codebook_locator(locator)
    locator_ids = [row["locator_id"] for row in locators]
    if len(locator_ids) != len(set(locator_ids)):
        raise DictionaryDriftError("duplicate codebook locator ID")
    locator_by_id = {row["locator_id"]: row for row in locators}
    if artifact["source_locator_keyset_sha256"] != sha256_bytes(
        canonical_json_bytes(locator_ids)
    ):
        raise DictionaryDriftError("codebook locator keyset hash drifted")
    locator_id_set = set(locator_ids)
    manifest_ids = {row["document_id"] for row in manifest}
    manifest_by_id = {row["document_id"]: row for row in manifest}
    if any(
        locator["source_document_id"] not in manifest_ids
        for locator in locators
    ):
        raise DictionaryDriftError(
            "codebook locator cites an unknown source document"
        )
    code_map_rows: list[Sequence[Any]] = []
    for row in fields:
        if len(row) != len(CODEBOOK_FIELD_EVIDENCE_COLUMNS):
            raise DictionaryDriftError("codebook field row schema drifted")
        if row[columns["interview_wave"]] not in waves:
            raise DictionaryDriftError("codebook field wave is outside era")
        if row[columns["earnings_reference_year"]] != (
            row[columns["interview_wave"]] - 1
        ):
            raise DictionaryDriftError(
                "codebook field reference-year mapping drifted"
            )
        code_map = row[columns["code_map"]]
        code_map_rows.extend(code_map)
        if not code_map or any(
            not isinstance(code_row, list)
            or len(code_row) != len(CODEBOOK_CODE_MAP_COLUMNS)
            for code_row in code_map
        ):
            raise DictionaryDriftError("codebook field code map drifted")
        expected_missing = [
            index
            for index, code_row in enumerate(code_map)
            if _is_explicit_missing_meaning(code_row[3])
        ]
        if row[columns["missing_code_map_indices"]] != expected_missing:
            raise DictionaryDriftError(
                "codebook missing-code classification drifted"
            )
        if row[columns["missing_raw_token_grammar_status"]] != (
            "not_established_exact_fixed_width_raw_tokens"
        ):
            raise DictionaryDriftError(
                "codebook raw-token grammar status drifted"
            )
        if row[columns["semantic_annotation_status"]] != (
            "fact_or_registration_required_residual"
        ):
            raise DictionaryDriftError(
                "codebook semantic annotation status drifted"
            )
        source_document_ids = row[columns["source_document_ids"]]
        if not set(source_document_ids).issubset(manifest_ids):
            raise DictionaryDriftError(
                "codebook field cites an unknown source document"
            )
        source_locator_ids = row[columns["source_locator_ids"]]
        if not source_locator_ids or not set(source_locator_ids).issubset(
            locator_id_set
        ):
            raise DictionaryDriftError(
                "codebook field cites an unknown/empty locator"
            )
        for locator_id in source_locator_ids:
            locator = locator_by_id[locator_id]
            source_document_id = locator["source_document_id"]
            if (
                source_document_id not in source_document_ids
                or manifest_by_id[source_document_id]["interview_wave"]
                != row[columns["interview_wave"]]
            ):
                raise DictionaryDriftError(
                    "codebook field locator wave/document binding drifted"
                )
    extraction_summary = artifact["extraction_summary"]
    expected_summary = {
        "field_count": len(fields),
        "description_line_count": sum(
            len(row[columns["full_source_description"]].splitlines())
            for row in fields
        ),
        "code_map_row_count": len(code_map_rows),
        "closed_range_count": sum(
            " - " in code_row[2] for code_row in code_map_rows
        ),
        "field_with_explicit_missing_count": sum(
            bool(row[columns["missing_code_map_indices"]]) for row in fields
        ),
        "explicit_missing_code_row_count": sum(
            len(row[columns["missing_code_map_indices"]]) for row in fields
        ),
        "multi_page_field_count": sum(
            len(row[columns["source_locator_ids"]]) > 1 for row in fields
        ),
        "page_stream_locator_count": len(locators),
    }
    if extraction_summary != expected_summary:
        raise DictionaryDriftError("codebook extraction summary drifted")
    facts = artifact["era_facts"]
    if artifact["era_fact_count"] != len(facts):
        raise DictionaryDriftError("codebook era fact count drifted")
    fact_ids = [fact["fact_id"] for fact in facts]
    if len(fact_ids) != len(set(fact_ids)):
        raise DictionaryDriftError("duplicate codebook era fact ID")
    field_key_set = set(field_keys)
    field_by_key = dict(zip(field_keys, fields, strict=True))
    for fact in facts:
        fact_field_keys = fact["codebook_field_keys"]
        if not fact_field_keys or not set(fact_field_keys).issubset(
            field_key_set
        ):
            raise DictionaryDriftError(
                "codebook era fact cites an unknown field"
            )
        if not fact["source_locator_ids"] or not set(
            fact["source_locator_ids"]
        ).issubset(locator_id_set):
            raise DictionaryDriftError(
                "codebook era fact cites an unknown locator"
            )
        bound_fields = [field_by_key[key] for key in fact_field_keys]
        expected_source_binding = _fact_source_binding(
            bound_fields,
            columns,
        )
        if any(
            fact[name] != expected_source_binding[name]
            for name in (
                "raw_field_ids",
                "codebook_field_keys",
                "source_locator_ids",
            )
        ):
            raise DictionaryDriftError(
                "codebook era fact source binding is not the exact field "
                "union"
            )
        if {row[columns["interview_wave"]] for row in bound_fields} != {
            fact["interview_wave"]
        }:
            raise DictionaryDriftError(
                "codebook era fact field-wave binding drifted"
            )
    residuals = artifact["registration_required_residuals"]
    residual_ids = [row["residual_id"] for row in residuals]
    if not residuals or len(residual_ids) != len(set(residual_ids)):
        raise DictionaryDriftError(
            "codebook residual domain is empty or duplicated"
        )
    if any(
        row["status"] != "registration_required"
        or not row["missing_fact"]
        or not row["registration_required_item"]
        for row in residuals
    ):
        raise DictionaryDriftError(
            "codebook residual is not an exact fail-closed disposition"
        )
    identity_rows = [
        row for row in CODEBOOK_ERA_IDENTITIES if row[0] == era_id
    ]
    if len(identity_rows) != 1:
        raise DictionaryDriftError(
            "codebook era frozen identity is absent or duplicated"
        )
    expected_identity = dict(
        zip(CODEBOOK_ERA_IDENTITY_COLUMNS, identity_rows[0], strict=True)
    )
    observed_identity = {
        "era_id": era_id,
        "field_count": len(fields),
        "description_line_count": extraction_summary["description_line_count"],
        "code_map_row_count": extraction_summary["code_map_row_count"],
        "closed_range_count": extraction_summary["closed_range_count"],
        "page_stream_locator_count": len(locators),
        "fact_count": len(facts),
        "residual_count": len(residuals),
        "source_authority_manifest_sha256": artifact[
            "source_authority_manifest_sha256"
        ],
        "field_evidence_keyset_sha256": artifact[
            "field_evidence_keyset_sha256"
        ],
        "source_locator_keyset_sha256": artifact[
            "source_locator_keyset_sha256"
        ],
        "content_sha256": artifact["integrity"]["content_sha256"],
    }
    if observed_identity != expected_identity:
        raise DictionaryDriftError(
            f"codebook era frozen identity drifted: {era_id}"
        )
    if artifact["canonical_order"] != [
        "interview_wave",
        "physical_layout_coordinate",
    ]:
        raise DictionaryDriftError("codebook canonical order drifted")
    integrity = artifact["integrity"]
    if integrity["reproduced_from_source_bytes"] is not True:
        raise DictionaryDriftError(
            "codebook evidence lacks source-byte reproduction status"
        )
    expected_content_sha = integrity["content_sha256"]
    candidate = json.loads(json.dumps(artifact))
    candidate["integrity"]["content_sha256"] = _ZERO_SHA256
    if expected_content_sha != sha256_bytes(canonical_json_bytes(candidate)):
        raise DictionaryDriftError("codebook evidence content hash drifted")


def render_codebook_era_evidence(artifact: Mapping[str, Any]) -> bytes:
    """Render canonical codebook evidence with one trailing newline."""

    validate_codebook_era_evidence(artifact)
    return canonical_json_bytes(artifact) + b"\n"


def default_codebook_evidence_path(era_id: str) -> Path:
    """Return the committed ancillary evidence path for one era."""

    return (
        Path("data")
        / "external"
        / "psid_codebook_field_evidence"
        / f"{era_id}_v1.json"
    )


def build_codebook_inventory_adjudication(
    era_artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Adjudicate all six codebook eras without inventing absence proofs."""

    expected_eras = [era_id for era_id, _ in CODEBOOK_ERA_SPECS]
    by_era: dict[str, Mapping[str, Any]] = {}
    for era_artifact in era_artifacts:
        validate_codebook_era_evidence(era_artifact)
        era_id = era_artifact["era_id"]
        if era_id in by_era:
            raise DictionaryDriftError(
                f"duplicate codebook era artifact: {era_id}"
            )
        by_era[era_id] = era_artifact
    if list(by_era) != expected_eras:
        raise DictionaryDriftError(
            "codebook adjudication era order/domain drifted"
        )

    evidence_artifacts: list[dict[str, Any]] = []
    present_facts: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []
    facts_by_id: dict[str, Mapping[str, Any]] = {}
    for era_id in expected_eras:
        era_artifact = by_era[era_id]
        rendered = render_codebook_era_evidence(era_artifact)
        evidence_artifacts.append(
            {
                "era_id": era_id,
                "artifact_id": era_artifact["artifact_id"],
                "committed_path": default_codebook_evidence_path(
                    era_id
                ).as_posix(),
                "content_sha256": era_artifact["integrity"]["content_sha256"],
                "rendered_sha256": sha256_bytes(rendered),
                "field_count": era_artifact["field_evidence_count"],
                "page_stream_locator_count": era_artifact[
                    "source_locator_count"
                ],
                "code_map_row_count": era_artifact["extraction_summary"][
                    "code_map_row_count"
                ],
                "closed_range_count": era_artifact["extraction_summary"][
                    "closed_range_count"
                ],
                "description_line_count": era_artifact["extraction_summary"][
                    "description_line_count"
                ],
                "fact_count": era_artifact["era_fact_count"],
            }
        )
        for fact in era_artifact["era_facts"]:
            fact_id = fact["fact_id"]
            if fact_id in facts_by_id:
                raise DictionaryDriftError(
                    f"duplicate codebook fact ID: {fact_id}"
                )
            facts_by_id[fact_id] = fact
            present_facts.append(
                {
                    "fact_id": fact_id,
                    "era_id": era_id,
                    "disposition": "present",
                    "source_status": fact["status"],
                    "raw_field_ids": fact["raw_field_ids"],
                    "codebook_field_keys": fact["codebook_field_keys"],
                    "source_locator_ids": fact["source_locator_ids"],
                }
            )
        for residual in era_artifact["registration_required_residuals"]:
            residuals.append({"era_id": era_id, **residual})

    totals = {
        "interview_wave_count": sum(
            len(artifact["interview_waves"]) for artifact in era_artifacts
        ),
        "codebook_authority_count": sum(
            sum(
                row["dictionary_role"] == "family_codebook"
                for row in artifact["source_authority_manifest"]
            )
            for artifact in era_artifacts
        ),
        "field_count": sum(
            artifact["field_evidence_count"] for artifact in era_artifacts
        ),
        "page_stream_locator_count": sum(
            artifact["source_locator_count"] for artifact in era_artifacts
        ),
        "code_map_row_count": sum(
            artifact["extraction_summary"]["code_map_row_count"]
            for artifact in era_artifacts
        ),
        "closed_range_count": sum(
            artifact["extraction_summary"]["closed_range_count"]
            for artifact in era_artifacts
        ),
        "description_line_count": sum(
            artifact["extraction_summary"]["description_line_count"]
            for artifact in era_artifacts
        ),
        "present_fact_count": len(present_facts),
        "structural_missing_count": 0,
        "registration_required_residual_count": len(residuals),
    }
    expected_totals = {
        "interview_wave_count": len(INTERVIEW_WAVES),
        "codebook_authority_count": CODEBOOK_AUTHORITY_FILE_COUNT,
        "field_count": CODEBOOK_TOTAL_FIELD_COUNT,
        "page_stream_locator_count": CODEBOOK_TOTAL_PAGE_COUNT,
        "code_map_row_count": CODEBOOK_TOTAL_MAP_ROW_COUNT,
        "closed_range_count": CODEBOOK_TOTAL_CLOSED_RANGE_COUNT,
        "description_line_count": CODEBOOK_TOTAL_DESCRIPTION_LINE_COUNT,
    }
    if {name: totals[name] for name in expected_totals} != expected_totals:
        raise DictionaryDriftError(
            "complete codebook adjudication totals drifted"
        )

    def source_fact_ids(prefixes: Sequence[str]) -> list[str]:
        result = [
            fact_id
            for fact_id in facts_by_id
            if any(fact_id.startswith(prefix) for prefix in prefixes)
        ]
        if not result:
            raise DictionaryDriftError(
                f"no codebook facts match prefixes {prefixes}"
            )
        return result

    cross_era_facts = [
        {
            "fact_id": "cross-era:ry1992_1993_component_seam",
            "disposition": "present",
            "finding": (
                "RY1992 role totals include role farm/business labor "
                "exactly once; RY1993 ER role totals explicitly exclude "
                "farm and unincorporated-business income."
            ),
            "source_fact_ids": [
                "pre-er-split-rule:1993:ownership_work_seam",
                "er-role-total:1994:head_or_reference_person:ER4140",
                "er-role-total:1994:spouse_or_partner:ER4144",
            ],
        },
        {
            "fact_id": "cross-era:ry2016_2022_exclusion_lineage",
            "disposition": "present",
            "finding": (
                "Every 2017-2023 role total preserves the prior-tax-year "
                "wage-type sum and explicitly excludes separately carried "
                "farm and unincorporated-business income."
            ),
            "source_fact_ids": source_fact_ids(
                [
                    "er-role-total:2017:",
                    "er-role-total:2019:",
                    "er-role-total:2021:",
                    "er-role-total:2023:",
                ]
            ),
        },
        {
            "fact_id": "cross-era:wave2015_postcutoff_inventory_boundary",
            "disposition": "present",
            "finding": (
                "The frozen unit-2 year registry classifies interview wave "
                "2015 (reference year 2014) and every later staged wave as "
                "inventory-only post-cutoff; their codebook facts preserve "
                "lineage but are inadmissible as direct production sources."
            ),
            "source_fact_ids": source_fact_ids(
                [
                    "er-role-total:2015:",
                    "er-role-total:2017:",
                    "er-role-total:2019:",
                    "er-role-total:2021:",
                    "er-role-total:2023:",
                ]
            ),
            "source_registry": (
                "populace_dynamics.data.psid_covered_earnings_registry"
            ),
            "inventory_wave_rows_sha256": (FROZEN_INVENTORY_WAVE_ROWS_SHA256),
            "codebook_or_crosswalk_inference_used": False,
        },
    ]
    for fact in cross_era_facts:
        if not set(fact["source_fact_ids"]).issubset(facts_by_id):
            raise DictionaryDriftError(
                "cross-era fact cites an unknown source fact"
            )

    vb5_facts = source_fact_ids(
        ["early-occupation:", "early-industry:", "early-secondary-occupation:"]
    )
    vb6_facts = source_fact_ids(
        [
            "spouse-seam-amount:",
            "spouse-1976-context:",
            "secondary-job-context:",
        ]
    )
    vb8_facts = source_fact_ids(["regular-school:"])
    adjudication: dict[str, Any] = {
        "schema_version": CODEBOOK_ADJUDICATION_SCHEMA_VERSION,
        "artifact_id": CODEBOOK_ADJUDICATION_SCHEMA_VERSION,
        "source_evidence_artifacts": evidence_artifacts,
        "complete_domain_totals": totals,
        "fact_dispositions": {
            "allowed_values": ["present", "structural_missing"],
            "present": present_facts,
            "structural_missing": [],
            "structural_missing_status": (
                "none_adjudicated_codebook_search_is_not_questionnaire_"
                "absence_proof"
            ),
        },
        "cross_era_facts": cross_era_facts,
        "verdicts": [
            {
                "registration_item_id": "V-B5",
                "verdict": "registration_required",
                "established_subclaims": (
                    "Retrospective main-job occupation/industry fields for "
                    "both roles and broad head secondary occupation are "
                    "present. Complete grouped maps displayed by the "
                    "codebooks are preserved; exact three-digit meanings "
                    "remain unestablished."
                ),
                "established_fact_ids": vb5_facts,
                "residual_ids": [
                    (
                        "wave1968_ry1968_1974_early_totals:"
                        "occupation_industry_attachment_closure"
                    )
                ],
            },
            {
                "registration_item_id": "V-B6",
                "verdict": "registration_required",
                "established_subclaims": (
                    "V4379 is mixed; V5289/V5788 amount concepts and 1976 "
                    "interview-time spouse context maps are present. The "
                    "1976 head and spouse, and 1977-1978 head, secondary-job "
                    "fields and displayed maps are source-bound without "
                    "claiming annual role-total attachment or 1977-1978 "
                    "spouse-branch absence."
                ),
                "established_fact_ids": vb6_facts,
                "residual_ids": [
                    (
                        "ry1975_1977_spouse_concept_seam:"
                        "V-B6:V5289_V5788_concept"
                    ),
                    (
                        "ry1975_1977_spouse_concept_seam:"
                        "V-B6:annual_job_match"
                    ),
                    (
                        "ry1975_1977_spouse_concept_seam:"
                        "V-B6:government_level_absence"
                    ),
                    (
                        "ry1975_1977_spouse_concept_seam:"
                        "V-B6:secondary_job_attachment_and_absence"
                    ),
                ],
            },
            {
                "registration_item_id": "V-B8",
                "verdict": "registration_required",
                "established_subclaims": (
                    "The two 2013 continuing-role K/L84 fields and the "
                    "2015-2023 new-role 61A plus continuing-role 84 fields "
                    "for both roles are present with complete displayed "
                    "maps. Earlier lexical still-in-school/college hits "
                    "remain explicitly non-evidentiary for role, universe, "
                    "or current status."
                ),
                "established_fact_ids": vb8_facts,
                "residual_ids": [
                    ("ry2002_2014_modern_bc_de:" "V-B8:branch_freshness"),
                    (
                        "ry2002_2014_modern_bc_de:"
                        "V-B8:pre_2013_questionnaire_absence_proof"
                    ),
                    ("ry2015_2022_exclusion_lineage:" "V-B8:branch_freshness"),
                ],
            },
        ],
        "registration_required_residuals": residuals,
        "production_admissibility": {
            "source_registry": (
                "populace_dynamics.data.psid_covered_earnings_registry"
            ),
            "source_registry_status": "frozen_unit_2_independent_registry",
            "inventory_wave_rows_sha256": (FROZEN_INVENTORY_WAVE_ROWS_SHA256),
            "boundary_earnings_reference_year": 2014,
            "first_inventory_only_interview_wave": 2015,
            "inventory_only_post_cutoff_waves": list(
                POST_CUTOFF_INVENTORY_WAVES
            ),
            "inventory_year_disposition": "inventory_only_post_cutoff",
            "production_use": "lineage_only",
            "derived_from_codebook_bytes": False,
            "crosswalk_inference_used": False,
        },
        "official_inventory_ratification": {
            "status": "registration_required",
            "failure_disposition": "abort_inventory_ratification",
            "target_artifacts": _target_artifacts(),
            "official_partial_artifact_emitted": False,
            "reason": (
                "The complete physical/codebook domain establishes positive "
                "facts but cannot establish questionnaire-exhaustive "
                "structural absence or every required attachment/timing "
                "rule."
            ),
        },
        "independence": {
            "inventory_source": (
                "registered codebook/setup/raw identities and pinned PDF "
                "content streams"
            ),
            "crosswalk_used": False,
            "reader_used": False,
            "derived_text_evidentiary_status": ("locator_only_not_evidence"),
        },
        "integrity": {
            "canonicalization": (
                "UTF-8 JSON; keys sorted; no insignificant whitespace; "
                "content_sha256 computed with itself set to 64 zeroes"
            ),
            "content_sha256": _ZERO_SHA256,
        },
    }
    adjudication["integrity"]["content_sha256"] = sha256_bytes(
        canonical_json_bytes(adjudication)
    )
    validate_codebook_inventory_adjudication(adjudication)
    return adjudication


def validate_codebook_inventory_adjudication(
    adjudication: Mapping[str, Any],
) -> None:
    """Validate the complete ancillary adjudication and its fail-close."""

    if adjudication["schema_version"] != (
        CODEBOOK_ADJUDICATION_SCHEMA_VERSION
    ) or adjudication["artifact_id"] != (CODEBOOK_ADJUDICATION_SCHEMA_VERSION):
        raise DictionaryDriftError("codebook adjudication identity drifted")
    evidence = adjudication["source_evidence_artifacts"]
    if [row["era_id"] for row in evidence] != [
        era_id for era_id, _ in CODEBOOK_ERA_SPECS
    ]:
        raise DictionaryDriftError(
            "codebook adjudication evidence domain drifted"
        )
    identity_by_era = {
        row[0]: dict(zip(CODEBOOK_ERA_IDENTITY_COLUMNS, row, strict=True))
        for row in CODEBOOK_ERA_IDENTITIES
    }
    for row in evidence:
        identity = identity_by_era[row["era_id"]]
        if (
            row["content_sha256"] != identity["content_sha256"]
            or row["field_count"] != identity["field_count"]
            or row["page_stream_locator_count"]
            != identity["page_stream_locator_count"]
            or row["code_map_row_count"] != identity["code_map_row_count"]
            or row["closed_range_count"] != identity["closed_range_count"]
            or row["description_line_count"]
            != identity["description_line_count"]
            or row["fact_count"] != identity["fact_count"]
        ):
            raise DictionaryDriftError(
                "codebook adjudication evidence identity drifted"
            )
    totals = adjudication["complete_domain_totals"]
    expected = {
        "interview_wave_count": len(INTERVIEW_WAVES),
        "codebook_authority_count": CODEBOOK_AUTHORITY_FILE_COUNT,
        "field_count": CODEBOOK_TOTAL_FIELD_COUNT,
        "page_stream_locator_count": CODEBOOK_TOTAL_PAGE_COUNT,
        "code_map_row_count": CODEBOOK_TOTAL_MAP_ROW_COUNT,
        "closed_range_count": CODEBOOK_TOTAL_CLOSED_RANGE_COUNT,
        "description_line_count": CODEBOOK_TOTAL_DESCRIPTION_LINE_COUNT,
    }
    if {name: totals[name] for name in expected} != expected:
        raise DictionaryDriftError("codebook adjudication totals drifted")
    dispositions = adjudication["fact_dispositions"]
    if dispositions["allowed_values"] != [
        "present",
        "structural_missing",
    ]:
        raise DictionaryDriftError("codebook disposition law drifted")
    if any(row["disposition"] != "present" for row in dispositions["present"]):
        raise DictionaryDriftError("non-present fact in present domain")
    present_ids = [row["fact_id"] for row in dispositions["present"]]
    if len(present_ids) != len(set(present_ids)):
        raise DictionaryDriftError("duplicate fact in present domain")
    if dispositions["structural_missing"]:
        raise DictionaryDriftError(
            "codebook-only adjudication invented structural absence"
        )
    if dispositions["structural_missing_status"] != (
        "none_adjudicated_codebook_search_is_not_questionnaire_absence_proof"
    ):
        raise DictionaryDriftError(
            "codebook structural-missing explanation drifted"
        )
    if totals["present_fact_count"] != len(dispositions["present"]):
        raise DictionaryDriftError("codebook present-fact total drifted")
    if totals["structural_missing_count"] != 0:
        raise DictionaryDriftError("codebook structural-missing total drifted")
    residuals = adjudication["registration_required_residuals"]
    residual_ids = [row["residual_id"] for row in residuals]
    if (
        totals["registration_required_residual_count"] != len(residuals)
        or len(residual_ids) != len(set(residual_ids))
        or any(row["status"] != "registration_required" for row in residuals)
    ):
        raise DictionaryDriftError(
            "codebook adjudication residual domain drifted"
        )
    cross_era_facts = adjudication["cross_era_facts"]
    if [row["fact_id"] for row in cross_era_facts] != [
        "cross-era:ry1992_1993_component_seam",
        "cross-era:ry2016_2022_exclusion_lineage",
        "cross-era:wave2015_postcutoff_inventory_boundary",
    ]:
        raise DictionaryDriftError("codebook cross-era fact domain drifted")
    present_id_set = set(present_ids)
    if any(
        row["disposition"] != "present"
        or not set(row["source_fact_ids"]).issubset(present_id_set)
        for row in cross_era_facts
    ):
        raise DictionaryDriftError("codebook cross-era source binding drifted")
    verdicts = adjudication["verdicts"]
    if [(row["registration_item_id"], row["verdict"]) for row in verdicts] != [
        ("V-B5", "registration_required"),
        ("V-B6", "registration_required"),
        ("V-B8", "registration_required"),
    ]:
        raise DictionaryDriftError("V-B verdict domain drifted")
    residual_id_set = set(residual_ids)
    for verdict in verdicts:
        established_ids = verdict["established_fact_ids"]
        verdict_residual_ids = verdict["residual_ids"]
        if (
            not established_ids
            or len(established_ids) != len(set(established_ids))
            or not set(established_ids).issubset(present_id_set)
            or not verdict_residual_ids
            or len(verdict_residual_ids) != len(set(verdict_residual_ids))
            or not set(verdict_residual_ids).issubset(residual_id_set)
        ):
            raise DictionaryDriftError("V-B verdict source binding drifted")
    vb8 = verdicts[2]
    if not all(
        fact_id.startswith("regular-school:")
        for fact_id in vb8["established_fact_ids"]
    ):
        raise DictionaryDriftError(
            "V-B8 treated a lexical search lead as established"
        )
    production = adjudication["production_admissibility"]
    if production != {
        "source_registry": (
            "populace_dynamics.data.psid_covered_earnings_registry"
        ),
        "source_registry_status": "frozen_unit_2_independent_registry",
        "inventory_wave_rows_sha256": FROZEN_INVENTORY_WAVE_ROWS_SHA256,
        "boundary_earnings_reference_year": 2014,
        "first_inventory_only_interview_wave": 2015,
        "inventory_only_post_cutoff_waves": list(POST_CUTOFF_INVENTORY_WAVES),
        "inventory_year_disposition": "inventory_only_post_cutoff",
        "production_use": "lineage_only",
        "derived_from_codebook_bytes": False,
        "crosswalk_inference_used": False,
    }:
        raise DictionaryDriftError(
            "codebook production-admissibility boundary drifted"
        )
    ratification = adjudication["official_inventory_ratification"]
    if (
        ratification["status"] != "registration_required"
        or ratification["failure_disposition"]
        != "abort_inventory_ratification"
        or ratification["target_artifacts"] != _target_artifacts()
    ):
        raise DictionaryDriftError("official inventory did not fail closed")
    if ratification["official_partial_artifact_emitted"] is not False:
        raise DictionaryDriftError(
            "official partial inventory was impermissibly emitted"
        )
    if adjudication["independence"] != {
        "inventory_source": (
            "registered codebook/setup/raw identities and pinned PDF "
            "content streams"
        ),
        "crosswalk_used": False,
        "reader_used": False,
        "derived_text_evidentiary_status": "locator_only_not_evidence",
    }:
        raise DictionaryDriftError("codebook adjudication lost independence")
    expected_content_sha = adjudication["integrity"]["content_sha256"]
    candidate = json.loads(json.dumps(adjudication))
    candidate["integrity"]["content_sha256"] = _ZERO_SHA256
    if expected_content_sha != sha256_bytes(canonical_json_bytes(candidate)):
        raise DictionaryDriftError(
            "codebook adjudication content hash drifted"
        )
    if expected_content_sha != CODEBOOK_ADJUDICATION_CONTENT_SHA256:
        raise DictionaryDriftError(
            "codebook adjudication frozen identity drifted"
        )


def render_codebook_inventory_adjudication(
    adjudication: Mapping[str, Any],
) -> bytes:
    """Render the complete ancillary adjudication canonically."""

    validate_codebook_inventory_adjudication(adjudication)
    return canonical_json_bytes(adjudication) + b"\n"


def default_codebook_adjudication_path() -> Path:
    """Return the committed complete codebook adjudication path."""

    return (
        Path("data")
        / "external"
        / "psid_codebook_inventory_adjudication_v1.json"
    )


def require_ratified_slot_specs(
    audit: dict[str, Any],
) -> None:
    """Fail closed instead of returning invented slot specifications."""

    item_ids = audit["inventory_ratification_abort"][
        "registration_required_item_ids"
    ]
    raise RegistrationRequiredError(SLOT_SPECS_ID, item_ids)


def require_ratified_source_inventory(
    audit: dict[str, Any],
) -> None:
    """Fail closed instead of returning an invented field inventory."""

    item_ids = audit["inventory_ratification_abort"][
        "registration_required_item_ids"
    ]
    raise RegistrationRequiredError(SOURCE_INVENTORY_ID, item_ids)


def _validate_format_file_evidence(
    evidence: Mapping[str, Any],
    physical_fields_by_wave: Mapping[int, set[str]],
) -> None:
    if evidence.get("field_bound_format_map_columns") != list(
        FIELD_BOUND_FORMAT_MAP_COLUMNS
    ):
        raise DictionaryDriftError("field-bound format-map columns drifted")
    if evidence.get("code_label_columns") != list(CODE_LABEL_COLUMNS):
        raise DictionaryDriftError("format code-label columns drifted")
    maps = evidence.get("field_bound_format_maps")
    if not isinstance(maps, list):
        raise DictionaryDriftError("field-bound format maps are not a list")
    field_ids: list[str] = []
    label_ids: list[str] = []
    code_label_row_count = 0
    for field_map in maps:
        if not isinstance(field_map, list) or len(field_map) != 3:
            raise DictionaryDriftError("field-bound format-map row drifted")
        field_id, label_id, code_rows = field_map
        if not isinstance(field_id, str) or not isinstance(label_id, str):
            raise DictionaryDriftError(
                "field-bound format-map identity is not textual"
            )
        if not isinstance(code_rows, list) or not code_rows:
            raise DictionaryDriftError(
                f"empty format code-label rows for {field_id}"
            )
        codes: list[int] = []
        for code_row in code_rows:
            if not isinstance(code_row, list) or len(code_row) != 2:
                raise DictionaryDriftError(
                    f"format code-label row drifted for {field_id}"
                )
            raw_code, label = code_row
            if (
                isinstance(raw_code, bool)
                or not isinstance(raw_code, int)
                or not isinstance(label, str)
            ):
                raise DictionaryDriftError(
                    f"invalid format code-label types for {field_id}"
                )
            codes.append(raw_code)
        if len(codes) != len(set(codes)):
            raise DictionaryDriftError(
                f"duplicate format-map raw code for {field_id}"
            )
        code_label_row_count += len(code_rows)
        field_ids.append(field_id)
        label_ids.append(label_id)
    if len(field_ids) != len(set(field_ids)):
        raise DictionaryDriftError("duplicate field-bound format-map field")
    if len(label_ids) != len(set(label_ids)):
        raise DictionaryDriftError("duplicate field-bound Stata label ID")
    if evidence.get("value_label_map_count") != len(maps):
        raise DictionaryDriftError("field-bound format-map count mismatch")
    if evidence.get("value_label_row_count") != code_label_row_count:
        raise DictionaryDriftError("format code-label row count mismatch")
    if evidence.get("field_bound_format_maps_sha256") != sha256_bytes(
        canonical_json_bytes(maps)
    ):
        raise DictionaryDriftError("field-bound format-map hash mismatch")
    wave = evidence.get("interview_wave")
    if wave not in physical_fields_by_wave:
        raise DictionaryDriftError(
            "format-map wave is outside physical domain"
        )
    unknown_fields = set(field_ids).difference(physical_fields_by_wave[wave])
    if unknown_fields:
        raise DictionaryDriftError(
            "format maps bind fields outside the artifact physical layout"
        )


def _validate_physical_field_integrity(
    artifact: Mapping[str, Any],
) -> list[list[Any]]:
    rows = artifact["physical_fields"]
    if artifact["physical_field_count"] != len(rows):
        raise DictionaryDriftError("physical field count mismatch")
    keys = [row[0] for row in rows]
    if len(keys) != len(set(keys)):
        raise DictionaryDriftError("duplicate physical field key")
    if artifact["physical_field_keyset_sha256"] != _keyset_hash(keys):
        raise DictionaryDriftError("physical field keyset hash mismatch")
    return rows


def _validate_content_integrity(artifact: Mapping[str, Any]) -> None:
    expected_content_sha = artifact["integrity"]["content_sha256"]
    candidate = json.loads(json.dumps(artifact))
    candidate["integrity"]["content_sha256"] = _ZERO_SHA256
    if expected_content_sha != sha256_bytes(canonical_json_bytes(candidate)):
        raise DictionaryDriftError("artifact content hash mismatch")


def _validate_fail_closed_status(artifact: Mapping[str, Any]) -> None:
    registration_items = _registration_required_items()
    if artifact.get("target_artifacts") != _target_artifacts():
        raise DictionaryDriftError(
            "registered audit target-artifact status drifted"
        )
    if artifact.get("registration_required_items") != registration_items:
        raise DictionaryDriftError(
            "registered audit registration-required findings drifted"
        )
    if artifact.get(
        "inventory_ratification_abort"
    ) != _inventory_ratification_abort(registration_items):
        raise DictionaryDriftError(
            "registered audit fail-closed disposition drifted"
        )
    integrity = artifact.get("integrity")
    if not isinstance(integrity, Mapping):
        raise DictionaryDriftError("registered audit integrity is not a map")
    if integrity.get("reproduced_from_source_bytes") is not False:
        raise DictionaryDriftError(
            "registered audit falsely claims source-byte reproduction"
        )


def _validate_codebook_authority_manifest(
    artifact: Mapping[str, Any],
) -> None:
    manifest = artifact.get("source_authority_manifest")
    if not isinstance(manifest, list):
        raise DictionaryDriftError(
            "registered audit source manifest is not a list"
        )
    if len(manifest) != SOURCE_AUTHORITY_FILE_COUNT:
        raise DictionaryDriftError(
            "complete source authority manifest file count drifted"
        )
    if (
        sum(row.get("size_bytes", 0) for row in manifest)
        != SOURCE_AUTHORITY_TOTAL_SIZE_BYTES
    ):
        raise DictionaryDriftError(
            "complete source authority manifest total size drifted"
        )
    if (
        sha256_bytes(canonical_json_bytes(manifest))
        != SOURCE_AUTHORITY_MANIFEST_SHA256
    ):
        raise DictionaryDriftError(
            "complete source authority manifest hash drifted"
        )
    codebooks = [
        row
        for row in manifest
        if isinstance(row, Mapping)
        and row.get("dictionary_role") == "family_codebook"
    ]
    if len(codebooks) != CODEBOOK_AUTHORITY_FILE_COUNT:
        raise DictionaryDriftError(
            "codebook authority manifest file count drifted"
        )
    if (
        sum(row.get("size_bytes", 0) for row in codebooks)
        != CODEBOOK_AUTHORITY_TOTAL_SIZE_BYTES
    ):
        raise DictionaryDriftError(
            "codebook authority manifest total size drifted"
        )
    if (
        sha256_bytes(canonical_json_bytes(codebooks))
        != CODEBOOK_AUTHORITY_MANIFEST_SHA256
    ):
        raise DictionaryDriftError("codebook authority manifest hash drifted")
    expected_waves = list(INTERVIEW_WAVES)
    if [row.get("interview_wave") for row in codebooks] != expected_waves:
        raise DictionaryDriftError("codebook authority wave order drifted")
    for row in codebooks:
        wave = row["interview_wave"]
        if row.get("document_id") != f"psid-family-{wave}-codebook":
            raise DictionaryDriftError(
                f"wave {wave}: codebook document ID drifted"
            )
        if row.get("encoding") != "binary":
            raise DictionaryDriftError(
                f"wave {wave}: codebook encoding drifted"
            )
        if Path(row.get("path", "")).suffix.lower() != ".pdf":
            raise DictionaryDriftError(f"wave {wave}: codebook path drifted")
        provenance = row.get("provenance")
        if not isinstance(provenance, Mapping):
            raise DictionaryDriftError(
                f"wave {wave}: codebook provenance is not a map"
            )
        expected_provenance = {
            "source_organization": "Panel Study of Income Dynamics",
            "source_product": "Family File Codebook",
            "source_edition": str(wave),
            "local_staging_authentication": "path_size_sha256_verified",
            "local_family_archive": provenance.get("local_family_archive"),
            "network_capture_performed_in_unit": False,
            "retrieval_provenance_status": (
                "registration_required_missing_original_retrieval_url_"
                "timestamp"
            ),
        }
        if provenance != expected_provenance:
            raise DictionaryDriftError(
                f"wave {wave}: codebook provenance drifted"
            )
        archive = provenance["local_family_archive"]
        if not isinstance(archive, Mapping) or set(archive) != {
            "path",
            "size_bytes",
            "sha256",
            "member_path",
            "member_size_bytes",
            "member_crc32",
            "member_sha256",
            "membership_authentication",
        }:
            raise DictionaryDriftError(
                f"wave {wave}: codebook archive provenance drifted"
            )
        if (
            not archive["path"].startswith(f"family/{wave}/")
            or Path(archive["path"]).suffix.lower() != ".zip"
            or archive["size_bytes"] <= 0
            or re.fullmatch(r"[0-9a-f]{64}", archive["sha256"]) is None
            or Path(archive["member_path"]).suffix.lower() != ".pdf"
            or archive["member_size_bytes"] != row["size_bytes"]
            or archive["member_sha256"] != row["sha256"]
            or re.fullmatch(r"[0-9a-f]{8}", archive["member_crc32"]) is None
            or archive["membership_authentication"]
            != "archive_member_bytes_equal_registered_codebook_bytes"
        ):
            raise DictionaryDriftError(
                f"wave {wave}: codebook archive membership drifted"
            )


def validate_integrity(artifact: dict[str, Any]) -> None:
    """Validate every frozen identity and positive-evidence commitment."""

    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise DictionaryDriftError("registered audit schema version drifted")
    if artifact.get("artifact_id") != ARTIFACT_ID:
        raise DictionaryDriftError("registered audit artifact ID drifted")
    _validate_fail_closed_status(artifact)
    _validate_codebook_authority_manifest(artifact)
    rows = _validate_physical_field_integrity(artifact)
    summary = artifact.get("evidence_summary")
    if not isinstance(summary, Mapping):
        raise DictionaryDriftError(
            "registered audit lacks its evidence summary"
        )
    columns = artifact["physical_field_columns"]
    wave_index = columns.index("interview_wave")
    field_index = columns.index("raw_field_id")
    physical_fields_by_wave: dict[int, set[str]] = {}
    for row in rows:
        physical_fields_by_wave.setdefault(row[wave_index], set()).add(
            row[field_index]
        )
    format_evidence = summary.get("format_file_evidence", [])
    if not isinstance(format_evidence, list):
        raise DictionaryDriftError("format file evidence is not a list")
    format_waves = [row.get("interview_wave") for row in format_evidence]
    if len(format_waves) != len(set(format_waves)):
        raise DictionaryDriftError("duplicate format evidence wave")
    if format_waves != list(FORMAT_MAP_WAVES):
        raise DictionaryDriftError(
            "registered field-bound format evidence waves drifted"
        )
    for evidence in format_evidence:
        if not isinstance(evidence, Mapping):
            raise DictionaryDriftError("format evidence row is not a map")
        _validate_format_file_evidence(
            evidence,
            physical_fields_by_wave,
        )
    expected_by_wave = {row[0]: row[1:] for row in FORMAT_MAP_IDENTITIES}
    manifest = artifact.get("source_authority_manifest")
    if not isinstance(manifest, list):
        raise DictionaryDriftError(
            "registered audit source manifest is not a list"
        )
    if not all(isinstance(row, Mapping) for row in manifest):
        raise DictionaryDriftError(
            "source-authority manifest row is not a map"
        )
    manifest_by_id = {row.get("document_id"): row for row in manifest}
    manifest_ids = list(manifest_by_id)
    if len(manifest_by_id) != len(manifest):
        raise DictionaryDriftError("duplicate source-authority document ID")
    if not all(isinstance(document_id, str) for document_id in manifest_ids):
        raise DictionaryDriftError("invalid source-authority document ID")
    format_sources_by_wave: dict[int, list[dict[str, Any]]] = {}
    for (
        wave,
        document_id,
        source_role,
        path,
        size_bytes,
        sha256,
        encoding,
    ) in FORMAT_SOURCE_IDENTITIES:
        expected_source = {
            "document_id": document_id,
            "interview_wave": wave,
            "dictionary_role": source_role,
            "path": path,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "encoding": encoding,
        }
        if manifest_by_id.get(document_id) != expected_source:
            raise DictionaryDriftError(
                f"wave {wave}: frozen {source_role} source identity drifted"
            )
        format_sources_by_wave.setdefault(wave, []).append(expected_source)
    for evidence in format_evidence:
        wave = evidence["interview_wave"]
        expected_identity = expected_by_wave[wave]
        observed_identity = (
            evidence.get("value_label_map_count"),
            evidence.get("value_label_row_count"),
            evidence.get("explicit_truncation_count"),
            evidence.get("field_bound_format_maps_sha256"),
        )
        if observed_identity != expected_identity:
            raise DictionaryDriftError(
                f"wave {wave}: frozen field-bound format evidence "
                "identity drifted"
            )
        expected_source_ids = [
            source["document_id"] for source in format_sources_by_wave[wave]
        ]
        if evidence.get("source_document_ids") != expected_source_ids:
            raise DictionaryDriftError(
                f"wave {wave}: format evidence source identities drifted"
            )
        if not set(expected_source_ids).issubset(manifest_ids):
            raise DictionaryDriftError(
                f"wave {wave}: format evidence sources are absent "
                "from the authority manifest"
            )
    _validate_content_integrity(artifact)


def render_artifact(artifact: dict[str, Any]) -> bytes:
    """Render the canonical committed file, including one trailing newline."""

    validate_integrity(artifact)
    return canonical_json_bytes(artifact) + b"\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=default_psid_root(),
        help="PSID staging root (default: ~/PolicyEngine/psid-data)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/external/"
            "psid_questionnaire_dictionary_inventory_"
            "registration_required_v1.json"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare generated bytes with --output instead of writing",
    )
    args = parser.parse_args(argv)
    rendered = render_artifact(
        build_registration_required_audit(args.data_root)
    )
    if args.check:
        if not args.output.is_file():
            raise SystemExit(f"missing committed artifact: {args.output}")
        if args.output.read_bytes() != rendered:
            raise SystemExit(
                f"committed artifact differs from source build: {args.output}"
            )
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
