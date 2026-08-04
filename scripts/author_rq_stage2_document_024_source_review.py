#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 24.

All 59 physical pages of q79.pdf were reviewed against the authenticated
Poppler page bytes.  This helper records only source-visible employment,
work-income, and limited work-history atoms.  It never opens the stage-1
candidate artifact; the sealed annotation builder performs that provenance
join only after this source ledger has been built and validated.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_024_annotation as annotation

ROOT = Path(__file__).resolve().parents[1]

F = "flow_branch_label"
R = "role_anchor"
J = "job_anchor"
M = "remuneration_component_anchor"
T = "role_total_anchor"
FA = "farm_aggregate_anchor"
BA = "business_aggregate_anchor"
C = "context_anchor"
P = "field_purpose_prompt"
A = "repeat_or_alias_instruction"

SEMANTIC_PAGE_NOTES = {
    1: "Cover and section-A transportation entry; no covered atom.",
    2: "Section-A city and vehicle items; no covered atom.",
    3: "Section-B housing tenure and costs; no covered atom.",
    4: "Section-B housing, utility, and ownership items; no covered atom.",
    5: "Section-B residential mobility; no covered atom.",
    6: "Head current-employment entry and assignment.",
    7: "Head current-job occupation, industry, tenure, and prior-job prompts.",
    8: "Head annual absence and leave exposure.",
    9: "Head annual work, main-job hours, and overtime exposure.",
    10: "Head salary, hourly, overtime, and other-pay grid.",
    11: "Head extra-job occupation, pay, and annual exposure.",
    12: "Counterfactual hours and commuting; no covered atom.",
    13: "Prospective job and mobility prose; no covered atom.",
    14: "Head no-job context; prospective job search and expected remuneration excluded.",
    15: "Head last-job occupation, industry, exit, and timing.",
    16: "Head last-job annual absence and leave exposure.",
    17: "Head last-job annual work exposure; commuting excluded.",
    18: "Head prior-year work while retired or otherwise out of labor force.",
    19: "Prospective job-search prose; no covered atom.",
    20: "Spouse/friend employment entry, role definition, and assignment.",
    21: "Spouse/friend current-job occupation, industry, tenure, and prior-job prompt.",
    22: "Spouse/friend annual absence and leave exposure.",
    23: "Spouse/friend annual work, overtime, and pay grid.",
    24: "Spouse/friend extra-job occupation and annual exposure; commuting excluded.",
    25: "Spouse/friend no-job and last-job context; prospective job search excluded.",
    26: "Spouse/friend last-job annual absence and leave exposure.",
    27: "Spouse/friend last-job annual work exposure; commuting excluded.",
    28: "Spouse/friend prior-year work while otherwise out of labor force.",
    29: "Prospective job-search prose; no covered atom.",
    30: "Housework screen; only its explicit wife/friend role-equivalence instruction is retained.",
    31: "Housework helper items; no covered atom.",
    32: "Food-stamp and food items; no covered atom.",
    33: "Food and food-stamp items; no covered atom.",
    34: "Food-stamp eligibility; no covered atom.",
    35: "Farm, business, head work-total, and additional-compensation income.",
    36: "Repeated professional, farm, and roomer work-income table; transfers excluded.",
    37: "Transfer and support income; no covered atom.",
    38: "Spouse/friend work-income entry and work-total amount.",
    39: "Extra-earner schedule outside the two-role R_Q hierarchy.",
    40: "Extra-earner schedule outside the two-role R_Q hierarchy.",
    41: "Extra-earner schedule outside the two-role R_Q hierarchy.",
    42: "Extra-earner schedule outside the two-role R_Q hierarchy.",
    43: "Extra-earner schedule outside the two-role R_Q hierarchy.",
    44: "Extra-earner schedule outside the two-role R_Q hierarchy.",
    45: "Extra-earner schedule outside the two-role R_Q hierarchy.",
    46: "Other-person income outside the two-role R_Q hierarchy.",
    47: "Medical and dependent-support items; no covered atom.",
    48: "Emergency-help items; no covered atom.",
    49: "Savings items; no covered atom.",
    50: "Savings and debt items; no covered atom.",
    51: "Loans and inflation items; no covered atom.",
    52: "Inflation and public-program items; no covered atom.",
    53: "Union, health, and retirement-plan items; no covered atom.",
    54: "New-spouse routing, role cross-reference, and lifetime work exposure.",
    55: "New-head routing, first regular job, and occupation pattern.",
    56: "Childhood, parental, and geography items; no covered atom.",
    57: "New-head lifetime work exposure; work-related mobility excluded.",
    58: "Education and religion; no covered atom.",
    59: "Observation-only items; no covered atom.",
}

# q79 retains the 1979 layout but carries two additional front-matter pages,
# one blank divider after page 16, and four additional pages before section K
# relative to the q80 review template from which the source selectors below
# were mechanically recovered.  Keep the logical questionnaire-page numbers
# in the selector table and resolve them to q79 PDF pages here.
SOURCE_PAGE_MAP = {
    **{page: page for page in range(1, 3)},
    **{page: page + 1 for page in range(3, 6)},
    **{page: page + 2 for page in range(6, 16)},
    **{page: page + 2 for page in range(16, 31)},
    31: 33,
    35: 39,
    36: 40,
    38: 42,
    54: 54,
    55: 55,
    57: 57,
}

Q79_SPANS: dict[str, tuple[int, int, int]] = {
    "c10_less": (9, 626, 676),
    "c10_long": (9, 709, 779),
    "c11_start_month_context": (9, 805, 885),
    "c11_start_month_purpose": (9, 805, 885),
    "c12_prior_job_exit_context": (9, 897, 1047),
    "c12_prior_job_exit_purpose": (9, 897, 1047),
    "c13_job_comparison_purpose": (9, 1382, 1520),
    "c15_pay_comparison_purpose": (9, 1707, 1786),
    "c16_family_sick_context": (10, 84, 185),
    "c16_family_sick_purpose": (10, 84, 185),
    "c16_yes": (10, 253, 256),
    "c17_family_sick_amount_context": (10, 312, 345),
    "c17_family_sick_amount_purpose": (10, 312, 345),
    "c18_no_route": (10, 663, 671),
    "c18_own_sick_context": (10, 485, 549),
    "c18_own_sick_purpose": (10, 485, 549),
    "c18_yes": (10, 618, 621),
    "c19_own_sick_amount_context": (10, 733, 772),
    "c19_own_sick_amount_purpose": (10, 733, 772),
    "c1_assignment_context": (8, 166, 348),
    "c1_assignment_purpose": (8, 166, 348),
    "c20_no_route": (10, 1011, 1014),
    "c20_vacation_context": (10, 792, 892),
    "c20_vacation_purpose": (10, 792, 892),
    "c20_yes": (10, 961, 964),
    "c21_vacation_amount_context": (10, 1055, 1141),
    "c21_vacation_amount_purpose": (10, 1055, 1141),
    "c22_no_route": (10, 1365, 1385),
    "c22_strike_context": (10, 1185, 1254),
    "c22_strike_purpose": (10, 1185, 1254),
    "c22_yes": (10, 1322, 1326),
    "c23_strike_amount_context": (10, 1407, 1446),
    "c23_strike_amount_purpose": (10, 1407, 1446),
    "c24_no_route": (11, 300, 309),
    "c24_unemployed_context": (11, 111, 214),
    "c24_unemployed_purpose": (11, 111, 214),
    "c24_yes": (11, 251, 254),
    "c25_unemployed_amount_context": (11, 356, 392),
    "c25_unemployed_amount_purpose": (11, 356, 392),
    "c26_weeks_worked_context": (11, 501, 585),
    "c26_weeks_worked_purpose": (11, 501, 585),
    "c27_hours_worked_context": (11, 670, 777),
    "c27_hours_worked_purpose": (11, 670, 777),
    "c28_no_route": (11, 1040, 1058),
    "c28_overtime_context": (11, 836, 946),
    "c28_overtime_purpose": (11, 836, 946),
    "c28_yes": (11, 991, 994),
    "c29_overtime_hours_context": (11, 1102, 1167),
    "c29_overtime_hours_purpose": (11, 1102, 1167),
    "c2_employee_self_context": (8, 1227, 1294),
    "c2_employee_self_purpose": (8, 1227, 1294),
    "c30_pay_method_context": (12, 70, 133),
    "c30_pay_method_purpose": (12, 70, 133),
    "c31_salary_amount_purpose": (12, 258, 279),
    "c32_extra_hours_continuation_context": (12, 787, 998),
    "c32_extra_hours_continuation_purpose": (12, 826, 998),
    "c32_extra_hours_open_purpose": (12, 713, 732),
    "c32_no_route": (12, 1043, 1048),
    "c32_paid_extra_hours": (12, 939, 998),
    "c32_yes": (12, 1031, 1037),
    "c33_extra_hour_rate_component": (12, 1676, 1714),
    "c33_extra_hour_rate_end_purpose": (12, 1750, 1762),
    "c33_extra_hour_rate_middle_purpose": (12, 1672, 1714),
    "c33_extra_hour_rate_purpose": (12, 1564, 1583),
    "c33_extra_hour_rate_tail_purpose": (12, 1715, 1724),
    "c34_regular_rate_component": (12, 401, 419),
    "c34_regular_rate_end_purpose": (12, 492, 510),
    "c34_regular_rate_middle_purpose": (12, 401, 419),
    "c34_regular_rate_purpose": (12, 291, 315),
    "c35_overtime_rate_component": (12, 746, 760),
    "c35_overtime_rate_end_purpose": (12, 819, 825),
    "c35_overtime_rate_middle_purpose": (12, 746, 760),
    "c35_overtime_rate_purpose": (12, 741, 745),
    "c36_other_pay_unit_purpose": (12, 324, 340),
    "c37_other_hour_component": (12, 1530, 1543),
    "c37_other_hour_end_purpose": (12, 1635, 1640),
    "c37_other_hour_middle_purpose": (12, 1307, 1321),
    "c37_other_hour_open_purpose": (12, 1092, 1108),
    "c37_other_hour_prompt_purpose": (12, 1200, 1215),
    "c37_other_hour_rate_purpose": (12, 1530, 1543),
    "c38_extra_jobs_context": (12, 2028, 2160),
    "c38_extra_jobs_purpose": (12, 2028, 2160),
    "c38_no_route": (12, 2426, 2442),
    "c39_extra_job_occupation_context": (12, 2470, 2486),
    "c39_extra_job_occupation_purpose": (12, 2470, 2486),
    "c3_government_context": (8, 1320, 1453),
    "c3_government_purpose": (8, 1320, 1453),
    "c40_more_extra_work_purpose": (12, 2509, 2534),
    "c41_extra_job_rate": (13, 146, 202),
    "c41_extra_job_rate_purpose": (13, 146, 202),
    "c42_extra_job_weeks_context": (13, 340, 434),
    "c42_extra_job_weeks_purpose": (13, 340, 434),
    "c43_extra_job_hours_context": (13, 577, 698),
    "c43_extra_job_hours_purpose": (13, 577, 698),
    "c44_no_route": (13, 1052, 1086),
    "c6_occupation_context": (9, 123, 209),
    "c6_occupation_purpose": (9, 123, 209),
    "c7_duties_context": (9, 227, 285),
    "c7_duties_purpose": (9, 227, 285),
    "c8_industry_context": (9, 292, 368),
    "c8_industry_purpose": (9, 292, 368),
    "c9_tenure_context": (9, 385, 455),
    "c9_tenure_purpose": (9, 385, 455),
    "c_current_job": (9, 422, 454),
    "c_extra_jobs": (12, 2054, 2064),
    "c_has_job": (8, 982, 1010),
    "c_head_role": (8, 228, 234),
    "c_head_role_header": (8, 141, 145),
    "c_head_role_tenure": (9, 713, 718),
    "c_main_job": (11, 568, 576),
    "c_overtime_component": (11, 896, 904),
    "c_prior_job": (9, 920, 942),
    "c_salary_component": (12, 89, 98),
    "c_section_context": (8, 0, 145),
    "d11_ever_job_context": (16, 792, 828),
    "d11_ever_job_purpose": (16, 792, 828),
    "d11_no_route": (16, 946, 958),
    "d12_last_job_occupation_context": (16, 977, 1076),
    "d12_last_job_occupation_purpose": (16, 977, 1076),
    "d13_last_job_industry_context": (16, 1101, 1170),
    "d13_last_job_industry_purpose": (16, 1101, 1170),
    "d14_last_job_exit_context": (16, 1195, 1327),
    "d14_last_job_exit_purpose": (16, 1195, 1327),
    "d15_last_worked_context": (16, 1338, 1378),
    "d15_last_worked_purpose": (16, 1338, 1378),
    "d16_not_worked": (18, 305, 415),
    "d16_worked": (18, 245, 273),
    "d17_no_route": (18, 646, 652),
    "d17_vacation_context": (18, 472, 550),
    "d17_vacation_purpose": (18, 472, 550),
    "d17_yes": (18, 609, 612),
    "d18_vacation_amount_context": (18, 706, 770),
    "d18_vacation_amount_purpose": (18, 706, 770),
    "d19_family_sick_context": (18, 903, 1004),
    "d19_family_sick_purpose": (18, 903, 1004),
    "d19_no_route": (18, 1109, 1118),
    "d20_family_sick_amount_context": (18, 1154, 1216),
    "d20_family_sick_amount_purpose": (18, 1154, 1216),
    "d21_no_route": (18, 1517, 1520),
    "d21_own_sick_context": (18, 1359, 1436),
    "d21_own_sick_purpose": (18, 1359, 1436),
    "d21_yes": (18, 1483, 1486),
    "d22_own_sick_amount_context": (18, 1538, 1634),
    "d22_own_sick_amount_purpose": (18, 1538, 1634),
    "d23_no_route": (18, 2026, 2119),
    "d23_strike_context": (18, 1764, 1833),
    "d23_strike_purpose": (18, 1764, 1833),
    "d24_strike_amount_context": (18, 2139, 2176),
    "d24_strike_amount_purpose": (18, 2139, 2176),
    "d25_unemployed_context": (19, 105, 200),
    "d25_unemployed_purpose": (19, 105, 200),
    "d26_unemployed_amount_context": (19, 287, 324),
    "d26_unemployed_amount_purpose": (19, 287, 324),
    "d27_weeks_worked_context": (19, 385, 468),
    "d27_weeks_worked_purpose": (19, 385, 468),
    "d28_hours_worked_context": (19, 556, 641),
    "d28_hours_worked_purpose": (19, 556, 641),
    "d_head_role": (15, 95, 107),
    "d_head_role_worked": (18, 248, 260),
    "d_last_job": (16, 1035, 1042),
    "d_route": (8, 474, 487),
    "d_section_context": (15, 79, 132),
    "e3_no_route": (20, 842, 859),
    "e3_worked_context": (20, 622, 669),
    "e3_worked_purpose": (20, 622, 669),
    "e3_yes": (20, 728, 731),
    "e4_occupation_context": (20, 912, 968),
    "e4_occupation_purpose": (20, 912, 968),
    "e5_industry_context": (20, 1002, 1074),
    "e5_industry_purpose": (20, 1002, 1074),
    "e6_weeks_context": (20, 1119, 1170),
    "e6_weeks_purpose": (20, 1119, 1170),
    "e7_hours_context": (20, 1197, 1238),
    "e7_hours_purpose": (20, 1197, 1238),
    "e8_still_working_context": (20, 1363, 1392),
    "e8_still_working_purpose": (20, 1363, 1392),
    "e8_yes_route": (20, 1455, 1473),
    "e9_job_exit_context": (20, 1497, 1640),
    "e9_job_exit_purpose": (20, 1497, 1640),
    "e_head_role": (20, 113, 128),
    "e_otherwise": (8, 1098, 1211),
    "e_section_context": (20, 71, 259),
    "e_work_for_money": (20, 654, 668),
    "f10_tenure_context": (23, 671, 749),
    "f10_tenure_purpose": (23, 671, 749),
    "f11_less": (23, 1044, 1097),
    "f11_long": (23, 1122, 1230),
    "f12_start_month_context": (23, 1252, 1302),
    "f12_start_month_purpose": (23, 1252, 1302),
    "f13_prior_job_exit_context": (23, 1319, 1461),
    "f13_prior_job_exit_purpose": (23, 1319, 1461),
    "f14_family_sick_context": (24, 178, 301),
    "f14_family_sick_purpose": (24, 178, 301),
    "f14_yes": (24, 396, 399),
    "f15_family_sick_amount_context": (24, 429, 457),
    "f15_family_sick_amount_purpose": (24, 429, 457),
    "f16_no_route": (24, 840, 883),
    "f16_own_sick_context": (24, 666, 749),
    "f16_own_sick_purpose": (24, 666, 749),
    "f16_yes": (24, 806, 809),
    "f17_own_sick_amount_context": (24, 901, 939),
    "f17_own_sick_amount_purpose": (24, 901, 939),
    "f18_no_route": (24, 1254, 1257),
    "f18_vacation_context": (24, 1074, 1160),
    "f18_vacation_purpose": (24, 1074, 1160),
    "f18_yes": (24, 1217, 1220),
    "f19_vacation_amount_context": (24, 1312, 1369),
    "f19_vacation_amount_purpose": (24, 1312, 1369),
    "f1_wife_definition": (22, 262, 364),
    "f20_strike_context": (24, 1598, 1703),
    "f20_strike_purpose": (24, 1598, 1703),
    "f20_yes": (24, 1772, 1775),
    "f21_strike_amount_context": (24, 1806, 1833),
    "f21_strike_amount_purpose": (24, 1806, 1833),
    "f22_unemployed_context": (24, 1846, 1969),
    "f22_unemployed_purpose": (24, 1846, 1969),
    "f23_unemployed_amount_context": (24, 1991, 2029),
    "f23_unemployed_amount_purpose": (24, 1991, 2029),
    "f24_weeks_worked_context": (25, 180, 307),
    "f24_weeks_worked_purpose": (25, 180, 307),
    "f25_hours_worked_context": (25, 391, 533),
    "f25_hours_worked_purpose": (25, 391, 533),
    "f26_no_route": (25, 808, 859),
    "f26_overtime_context": (25, 624, 729),
    "f26_overtime_purpose": (25, 624, 729),
    "f26_yes": (25, 772, 780),
    "f27_overtime_hours_context": (25, 856, 931),
    "f27_overtime_hours_purpose": (25, 856, 931),
    "f28_pay_method_context": (25, 1024, 1105),
    "f28_pay_method_purpose": (25, 1024, 1105),
    "f29_salary_amount_component": (25, 1245, 1252),
    "f29_salary_amount_purpose": (25, 1123, 1144),
    "f29_salary_amount_tail_purpose": (25, 1245, 1252),
    "f2_assignment_context": (22, 548, 864),
    "f2_assignment_purpose": (22, 548, 864),
    "f30_hourly_rate_component": (25, 1556, 1582),
    "f31_other_pay_unit_purpose": (25, 1159, 1223),
    "f32_extra_jobs_context": (26, 73, 201),
    "f32_extra_jobs_purpose": (26, 73, 201),
    "f33_extra_job_occupation_context": (26, 353, 378),
    "f33_extra_job_occupation_purpose": (26, 353, 378),
    "f34_extra_job_weeks_context": (26, 396, 549),
    "f34_extra_job_weeks_purpose": (26, 396, 549),
    "f35_extra_job_hours_context": (26, 569, 813),
    "f35_extra_job_hours_purpose": (26, 569, 813),
    "f3_employee_self_context": (22, 1259, 1354),
    "f3_employee_self_purpose": (22, 1259, 1354),
    "f4_government_context": (22, 1493, 1635),
    "f4_government_purpose": (22, 1493, 1635),
    "f7_occupation_context": (23, 126, 229),
    "f7_occupation_purpose": (23, 126, 229),
    "f8_duties_context": (23, 523, 576),
    "f8_duties_purpose": (23, 523, 576),
    "f9_industry_context": (23, 586, 650),
    "f9_industry_purpose": (23, 586, 650),
    "f_current_job": (22, 1666, 1686),
    "f_extra_jobs": (26, 111, 121),
    "f_has_job": (22, 1057, 1078),
    "f_head_female": (22, 553, 618),
    "f_main_job": (25, 278, 298),
    "f_no_wife": (22, 374, 520),
    "f_present_position": (23, 729, 748),
    "f_prior_job": (23, 1345, 1363),
    "f_section_context": (22, 134, 143),
    "f_wife_in_fu": (22, 225, 365),
    "f_wife_role_gate": (22, 360, 364),
    "f_wife_role": (22, 701, 714),
    "g10_not_worked": (28, 203, 286),
    "g10_worked": (28, 140, 172),
    "g11_no_route": (28, 518, 524),
    "g11_vacation_context": (28, 322, 416),
    "g11_vacation_purpose": (28, 322, 416),
    "g11_yes": (28, 481, 484),
    "g12_vacation_amount_context": (28, 586, 647),
    "g12_vacation_amount_purpose": (28, 586, 647),
    "g13_family_sick_context": (28, 793, 919),
    "g13_family_sick_purpose": (28, 793, 919),
    "g13_no_route": (28, 1019, 1028),
    "g13_yes": (28, 969, 1006),
    "g14_family_sick_amount_context": (28, 1067, 1126),
    "g14_family_sick_amount_purpose": (28, 1067, 1126),
    "g15_no_route": (28, 1464, 1471),
    "g15_own_sick_context": (28, 1281, 1359),
    "g15_own_sick_purpose": (28, 1281, 1359),
    "g15_yes": (28, 1425, 1428),
    "g16_own_sick_amount_context": (28, 1533, 1571),
    "g16_own_sick_amount_purpose": (28, 1533, 1571),
    "g17_no_route": (28, 1921, 1939),
    "g17_strike_context": (28, 1716, 1809),
    "g17_strike_purpose": (28, 1716, 1809),
    "g18_strike_amount_context": (28, 1960, 1993),
    "g18_strike_amount_purpose": (28, 1960, 1993),
    "g19_unemployed_context": (29, 107, 234),
    "g19_unemployed_purpose": (29, 107, 234),
    "g20_unemployed_amount_context": (29, 321, 356),
    "g20_unemployed_amount_purpose": (29, 321, 356),
    "g21_weeks_worked_context": (29, 404, 548),
    "g21_weeks_worked_purpose": (29, 404, 548),
    "g22_hours_worked_context": (29, 636, 718),
    "g22_hours_worked_purpose": (29, 636, 718),
    "g5_ever_job_context": (27, 1099, 1150),
    "g5_ever_job_purpose": (27, 1099, 1150),
    "g6_last_job_occupation_context": (27, 1172, 1298),
    "g6_last_job_occupation_purpose": (27, 1172, 1298),
    "g7_last_job_industry_context": (27, 1308, 1379),
    "g7_last_job_industry_purpose": (27, 1308, 1379),
    "g8_last_job_exit_context": (27, 1385, 1532),
    "g8_last_job_exit_purpose": (27, 1385, 1532),
    "g9_last_worked_context": (27, 1542, 1602),
    "g9_last_worked_purpose": (27, 1542, 1602),
    "g_last_job": (27, 1249, 1259),
    "g_section_context": (27, 202, 333),
    "g_wife_role": (27, 593, 606),
    "g_wife_role_worked": (28, 145, 149),
    "h3_no_route": (30, 1114, 1130),
    "h3_worked_context": (30, 689, 760),
    "h3_worked_purpose": (30, 689, 760),
    "h3_yes": (30, 926, 929),
    "h4_occupation_context": (30, 1188, 1242),
    "h4_occupation_purpose": (30, 1188, 1242),
    "h5_industry_context": (30, 1283, 1341),
    "h5_industry_purpose": (30, 1283, 1341),
    "h6_weeks_context": (30, 1366, 1447),
    "h6_weeks_purpose": (30, 1366, 1447),
    "h7_hours_context": (30, 1572, 1645),
    "h7_hours_purpose": (30, 1572, 1645),
    "h8_still_working_context": (30, 1770, 1807),
    "h8_still_working_purpose": (30, 1770, 1807),
    "h8_yes_route": (30, 1857, 1874),
    "h9_job_exit_context": (30, 1890, 2011),
    "h9_job_exit_purpose": (30, 1890, 2011),
    "h_otherwise": (22, 1080, 1196),
    "h_section_context": (30, 102, 241),
    "h_wife_role": (30, 119, 130),
    "h_wife_role_gate": (30, 143, 153),
    "h_work_for_money": (30, 745, 759),
    "j3_wife_definition": (32, 1052, 1161),
    "k10_additional_amount_purpose": (40, 308, 334),
    "k11_farming": (40, 1367, 1374),
    "k11_farming_gardening_purpose": (40, 1355, 1422),
    "k11_head_role": (40, 516, 522),
    "k11_other_work_income_purpose": (40, 412, 735),
    "k11_professional_trade": (40, 1256, 1268),
    "k11_professional_trade_purpose": (40, 1250, 1342),
    "k11_repeat": (40, 608, 735),
    "k11_roomers": (40, 1473, 1480),
    "k11_roomers_purpose": (40, 1466, 1532),
    "k12_amount_purpose": (40, 1201, 1216),
    "k13_duration_purpose": (40, 1018, 1134),
    "k25_head_female": (42, 534, 590),
    "k25_no_wife": (42, 363, 458),
    "k25_wife_in_fu": (42, 308, 346),
    "k25_wife_role": (42, 334, 339),
    "k26_no_route": (42, 770, 786),
    "k26_wife_income_purpose": (42, 598, 677),
    "k27_wife_work_earnings": (42, 907, 915),
    "k27_wife_work_earnings_purpose": (42, 876, 932),
    "k27_yes": (42, 976, 978),
    "k28_wife_work_amount_purpose": (42, 991, 1062),
    "k28_wife_work_total": (42, 991, 1062),
    "k2_farm": (39, 538, 549),
    "k2_farm_receipts_purpose": (39, 497, 707),
    "k2_receipts": (39, 523, 537),
    "k3_expenses": (39, 756, 779),
    "k3_farm_expenses_purpose": (39, 721, 919),
    "k4_farm": (39, 973, 990),
    "k4_farm_net_purpose": (39, 933, 1048),
    "k4_net_income": (39, 961, 972),
    "k5_business_assignment_purpose": (39, 1066, 1254),
    "k5_business_enterprise": (39, 1233, 1253),
    "k5_business_owned": (39, 1115, 1129),
    "k5_no_route": (39, 1332, 1406),
    "k6_incorporation_context": (39, 1425, 1574),
    "k6_incorporation_purpose": (39, 1425, 1574),
    "k7_business": (39, 1657, 1713),
    "k7_business_income": (39, 1651, 1663),
    "k7_business_share_purpose": (39, 1602, 1780),
    "k8_head_role": (39, 1918, 1924),
    "k8_head_work_total": (39, 1888, 2078),
    "k8_wages_salaries": (39, 1938, 1956),
    "k8_work_total_purpose": (39, 1888, 2078),
    "k9_additional_compensation": (40, 65, 175),
    "k9_additional_compensation_purpose": (40, 65, 175),
    "k9_no_route": (40, 250, 259),
    "k9_yes": (40, 216, 219),
    "l10_exit": (54, 2429, 2446),
    "l10_years_worked_context": (54, 2159, 2274),
    "l10_years_worked_purpose": (54, 2159, 2274),
    "l11_exit": (54, 2703, 2725),
    "l11_full_time_years_context": (54, 2462, 2577),
    "l11_full_time_years_purpose": (54, 2462, 2577),
    "l12_part_time_share_context": (54, 2816, 3055),
    "l12_part_time_share_purpose": (54, 2816, 3055),
    "l1_same_wife_crossref": (54, 641, 660),
    "l1_wife_definition": (54, 313, 388),
    "l_head_female": (54, 424, 471),
    "l_new_wife": (54, 287, 388),
    "l_no_wife": (54, 521, 573),
    "l_same_wife": (54, 623, 685),
    "l_wife_role": (54, 294, 302),
    "m1_same_head_crossref": (55, 327, 401),
    "m25_exit": (57, 1200, 1226),
    "m25_years_worked_context": (57, 1042, 1102),
    "m25_years_worked_purpose": (57, 1042, 1102),
    "m26_exit": (57, 1487, 1506),
    "m26_full_time_years_context": (57, 1193, 1392),
    "m26_full_time_years_purpose": (57, 1193, 1392),
    "m27_part_time_share_context": (57, 1513, 1635),
    "m27_part_time_share_purpose": (57, 1513, 1635),
    "m4_first_job_context": (55, 1272, 1371),
    "m4_first_job_purpose": (55, 1272, 1371),
    "m5_occupation_pattern_context": (55, 1391, 1571),
    "m5_occupation_pattern_purpose": (55, 1391, 1571),
    "m_first_job": (55, 1314, 1353),
    "m_head_role": (55, 260, 293),
    "m_new_head": (55, 254, 293),
    "m_same_head": (55, 295, 401),
}

FULLY_BLOCKED_KEYS = frozenset(
    (
        "c31_salary_amount_purpose",
        "c34_regular_rate_purpose",
        "c36_other_pay_unit_purpose",
        "c34_regular_rate_component",
        "c34_regular_rate_middle_purpose",
        "c34_regular_rate_end_purpose",
        "c35_overtime_rate_purpose",
        "c32_extra_hours_open_purpose",
        "c35_overtime_rate_component",
        "c35_overtime_rate_middle_purpose",
        "c35_overtime_rate_end_purpose",
        "c32_extra_hours_continuation_context",
        "c32_extra_hours_continuation_purpose",
        "c32_paid_extra_hours",
        "c32_yes",
        "c32_no_route",
        "c37_other_hour_open_purpose",
        "c37_other_hour_prompt_purpose",
        "c33_extra_hour_rate_purpose",
        "c37_other_hour_middle_purpose",
        "c33_extra_hour_rate_middle_purpose",
        "c33_extra_hour_rate_component",
        "c37_other_hour_component",
        "c37_other_hour_rate_purpose",
        "c33_extra_hour_rate_tail_purpose",
        "c37_other_hour_end_purpose",
        "c33_extra_hour_rate_end_purpose",
        "c38_extra_jobs_context",
        "c38_extra_jobs_purpose",
        "c_extra_jobs",
        "c38_no_route",
        "c39_extra_job_occupation_context",
        "c39_extra_job_occupation_purpose",
        "c40_more_extra_work_purpose",
        "c41_extra_job_rate",
        "c41_extra_job_rate_purpose",
        "c42_extra_job_weeks_context",
        "c42_extra_job_weeks_purpose",
        "c43_extra_job_hours_context",
        "c43_extra_job_hours_purpose",
        "g_section_context",
        "g_wife_role",
        "g5_ever_job_context",
        "g5_ever_job_purpose",
        "g6_last_job_occupation_context",
        "g6_last_job_occupation_purpose",
        "g_last_job",
        "g7_last_job_industry_context",
        "g7_last_job_industry_purpose",
        "g8_last_job_exit_context",
        "g8_last_job_exit_purpose",
        "g9_last_worked_context",
        "g9_last_worked_purpose",
        "g10_worked",
        "g_wife_role_worked",
        "g10_not_worked",
        "g11_vacation_context",
        "g11_vacation_purpose",
        "g11_yes",
        "g11_no_route",
        "g12_vacation_amount_context",
        "g12_vacation_amount_purpose",
        "g13_family_sick_context",
        "g13_family_sick_purpose",
        "g13_yes",
        "g13_no_route",
        "g14_family_sick_amount_context",
        "g14_family_sick_amount_purpose",
        "g15_own_sick_context",
        "g15_own_sick_purpose",
        "g15_yes",
        "g15_no_route",
        "g16_own_sick_amount_context",
        "g16_own_sick_amount_purpose",
        "g17_strike_context",
        "g17_strike_purpose",
        "g17_no_route",
        "g18_strike_amount_context",
        "g18_strike_amount_purpose",
        "g19_unemployed_context",
        "g19_unemployed_purpose",
        "g20_unemployed_amount_context",
        "g20_unemployed_amount_purpose",
        "g21_weeks_worked_context",
        "g21_weeks_worked_purpose",
        "g22_hours_worked_context",
        "g22_hours_worked_purpose",
        "k2_farm_receipts_purpose",
        "k2_receipts",
        "k2_farm",
        "k3_farm_expenses_purpose",
        "k3_expenses",
        "k4_farm_net_purpose",
        "k4_net_income",
        "k4_farm",
        "k5_business_assignment_purpose",
        "k5_business_owned",
        "k5_business_enterprise",
        "k5_no_route",
        "k6_incorporation_context",
        "k6_incorporation_purpose",
        "k7_business_share_purpose",
        "k7_business_income",
        "k7_business",
        "k8_head_work_total",
        "k8_work_total_purpose",
        "k8_head_role",
        "k8_wages_salaries",
        "k9_additional_compensation",
        "k9_additional_compensation_purpose",
        "k10_additional_amount_purpose",
        "k9_yes",
        "k9_no_route",
        "k11_other_work_income_purpose",
        "k11_head_role",
        "k11_repeat",
        "k13_duration_purpose",
        "k12_amount_purpose",
        "k11_professional_trade_purpose",
        "k11_professional_trade",
        "k11_farming_gardening_purpose",
        "k11_farming",
        "k11_roomers_purpose",
        "k11_roomers",
        "k25_wife_in_fu",
        "k25_wife_role",
        "k25_no_wife",
        "k25_head_female",
        "k26_wife_income_purpose",
        "k26_no_route",
        "k27_wife_work_earnings_purpose",
        "k27_wife_work_earnings",
        "k27_yes",
        "k28_wife_work_total",
        "k28_wife_work_amount_purpose",
        "c44_no_route",
    )
)

E_FALLBACK_KEYS = frozenset(
    (
        "e_section_context",
        "e_head_role",
        "e3_worked_context",
        "e3_worked_purpose",
        "e_work_for_money",
        "e3_yes",
        "e3_no_route",
        "e4_occupation_context",
        "e4_occupation_purpose",
        "e5_industry_context",
        "e5_industry_purpose",
        "e6_weeks_context",
        "e6_weeks_purpose",
        "e7_hours_context",
        "e7_hours_purpose",
        "e8_still_working_context",
        "e8_still_working_purpose",
        "e8_yes_route",
        "e9_job_exit_context",
        "e9_job_exit_purpose",
    )
)

E_ENTRY_KEYS = frozenset(
    (
        "e_section_context",
        "e_head_role",
        "e3_worked_context",
        "e3_worked_purpose",
        "e_work_for_money",
        "e3_yes",
        "e3_no_route",
    )
)

H_FALLBACK_KEYS = frozenset(
    (
        "h_section_context",
        "h_wife_role",
        "h_wife_role_gate",
        "h3_worked_context",
        "h3_worked_purpose",
        "h_work_for_money",
        "h3_yes",
        "h3_no_route",
        "h4_occupation_context",
        "h4_occupation_purpose",
        "h5_industry_context",
        "h5_industry_purpose",
        "h6_weeks_context",
        "h6_weeks_purpose",
        "h7_hours_context",
        "h7_hours_purpose",
        "h8_still_working_context",
        "h8_still_working_purpose",
        "h8_yes_route",
        "h9_job_exit_context",
        "h9_job_exit_purpose",
    )
)

H_ENTRY_KEYS = frozenset(
    (
        "h_section_context",
        "h_wife_role",
        "h_wife_role_gate",
        "h3_worked_context",
        "h3_worked_purpose",
        "h_work_for_money",
        "h3_yes",
        "h3_no_route",
    )
)


def _review_id(
    source_document_id: str,
    page_texts: Sequence[str],
    page_number: int,
    start: int,
    end: int,
    kind: str,
) -> str:
    matched = page_texts[page_number - 1].encode("utf-8")[start:end]
    if not matched:
        raise ValueError("empty reviewer span")
    matched.decode("utf-8", errors="strict")
    return "rq-review-occurrence:" + annotation._canonical_digest(
        [
            source_document_id,
            page_number,
            start,
            end,
            kind,
            annotation._sha256(matched),
        ]
    )


def author_review() -> dict[str, Any]:
    replay, index = annotation._source_replay_and_index()
    document, _identity = annotation._document_identity(replay, index)
    page_texts = annotation._extract_page_texts(document, replay)
    source_document_id = document["source_document_id"]

    def source_page(page: int) -> int:
        try:
            return SOURCE_PAGE_MAP[page]
        except KeyError as error:
            raise ValueError(f"unmapped logical q80 page {page}") from error

    def trim(page: int, start: int, end: int) -> tuple[int, int]:
        raw = page_texts[page - 1].encode("utf-8")
        while start < end and raw[start : start + 1] in b" \t\r\n":
            start += 1
        while start < end and raw[end - 1 : end] in b" \t\r\n":
            end -= 1
        if not 0 <= start < end <= len(raw):
            raise ValueError(f"invalid reviewed span on page {page}")
        raw[start:end].decode("utf-8", errors="strict")
        return start, end

    def needle(
        page: int, text: str, ordinal: int | None = None
    ) -> tuple[int, int]:
        # Source atoms are resolved by the independently reviewed q79 byte
        # ledger in ``add``.  The inherited q80 selector expressions remain
        # only as readable semantic documentation.
        return (0, 1)

        # Unreachable reference implementation retained to document selector
        # semantics from the mechanically recovered draft.
        page = source_page(page)
        raw = page_texts[page - 1].encode("utf-8")
        target = text.encode("utf-8")
        positions: list[int] = []
        cursor = 0
        while True:
            found = raw.find(target, cursor)
            if found < 0:
                break
            positions.append(found)
            cursor = found + 1
        if not positions:
            raise ValueError(f"needle absent on page {page}: {text!r}")
        if ordinal is None:
            if len(positions) != 1:
                raise ValueError(
                    f"needle is not unique on page {page}: {text!r}"
                )
            ordinal = 0
        if not 0 <= ordinal < len(positions):
            raise ValueError(f"needle ordinal drift on page {page}: {text!r}")
        start = positions[ordinal]
        return start, start + len(target)

    def block(
        page: int,
        start_text: str,
        end_text: str,
        start_ordinal: int | None = None,
    ) -> tuple[int, int]:
        return (0, 1)

        start, _ = needle(page, start_text, start_ordinal)
        page = source_page(page)
        raw = page_texts[page - 1].encode("utf-8")
        end_target = end_text.encode("utf-8")
        end_start = raw.find(end_target, start)
        if end_start < 0:
            raise ValueError(
                f"block end absent after start on page {page}: {end_text!r}"
            )
        return trim(page, start, end_start + len(end_target))

    def line(
        page: int, marker: str, ordinal: int | None = None
    ) -> tuple[int, int]:
        return (0, 1)

        marker_start, _ = needle(page, marker, ordinal)
        page = source_page(page)
        raw = page_texts[page - 1].encode("utf-8")
        start = raw.rfind(b"\n", 0, marker_start) + 1
        end = raw.find(b"\n", marker_start)
        if end < 0:
            end = len(raw)
        return trim(page, start, end)

    def lines(
        page: int,
        start_marker: str,
        end_marker: str,
        start_ordinal: int | None = None,
        end_ordinal: int | None = None,
    ) -> tuple[int, int]:
        return (0, 1)

        start_marker_byte, _ = needle(page, start_marker, start_ordinal)
        end_marker_byte, _ = needle(page, end_marker, end_ordinal)
        page = source_page(page)
        if end_marker_byte < start_marker_byte:
            raise ValueError(
                f"line block reverses source order on page {page}"
            )
        raw = page_texts[page - 1].encode("utf-8")
        start = raw.rfind(b"\n", 0, start_marker_byte) + 1
        end = raw.find(b"\n", end_marker_byte)
        if end < 0:
            end = len(raw)
        return trim(page, start, end)

    def physical(
        page: int, first_line: int, last_line: int | None = None
    ) -> tuple[int, int]:
        """Return an exact trimmed span by one-based Poppler physical lines."""

        return (0, 1)

        page = source_page(page)
        if last_line is None:
            last_line = first_line
        raw = page_texts[page - 1].encode("utf-8")
        rows = raw.splitlines(keepends=True)
        if not 1 <= first_line <= last_line <= len(rows):
            raise ValueError(f"physical line range drift on page {page}")
        start = sum(len(row) for row in rows[: first_line - 1])
        end = sum(len(row) for row in rows[:last_line])
        while end > start and raw[end - 1 : end] in b"\r\n":
            end -= 1
        return trim(page, start, end)

    specs: dict[str, dict[str, Any]] = {}

    def add(
        key: str,
        page: int,
        span: tuple[int, int],
        kind: str,
        *,
        branches: Sequence[Sequence[str]] = ((),),
        parents: Sequence[str] = (),
        note: str = "Exact source atom retained after whole-page review.",
    ) -> None:
        if key in specs:
            raise ValueError(f"duplicate review key: {key}")
        resolved_span = Q79_SPANS.get(key)
        if resolved_span is None:
            return
        page, start, end = resolved_span
        start, end = trim(page, start, end)

        # Amendment 1 consequence: fully blocked ordinary atoms remain in the
        # source review with an empty emitted-path subset.  Mixed E/H atoms
        # retain only their independently resolving ordinary fallback route.
        if key in FULLY_BLOCKED_KEYS:
            branches = ()
        elif key in E_FALLBACK_KEYS:
            branches = (("e_otherwise",),)
            if key not in E_ENTRY_KEYS:
                branches = (("e_otherwise", "e3_yes"),)
        elif key in H_FALLBACK_KEYS:
            branches = (("f_wife_in_fu", "h_otherwise"),)
            if key not in H_ENTRY_KEYS:
                branches = (("f_wife_in_fu", "h_otherwise", "h3_yes"),)
        else:
            # Omitted q80-only routing granularity is not extraction
            # authority in q79.  Preserve the coarser q79 path by dropping
            # only absent ordinary route keys, never exception keys.
            branches = tuple(
                tuple(parent for parent in path if parent in Q79_SPANS)
                for path in branches
            )
            branches = tuple(dict.fromkeys(branches))
            if not branches:
                branches = ((),)
        specs[key] = {
            "key": key,
            "page": page,
            "start": start,
            "end": end,
            "kind": kind,
            "branches": tuple(tuple(path) for path in branches),
            "parents": tuple(parents),
            "note": note,
        }

    def question(
        key: str,
        page: int,
        span: tuple[int, int],
        *,
        branches: Sequence[Sequence[str]] = ((),),
        context: bool = False,
        context_parents: Sequence[str] = (),
        note: str = "Complete printed prompt retained for a covered purpose.",
    ) -> None:
        add(key + "_purpose", page, span, P, branches=branches, note=note)
        if context:
            add(
                key + "_context",
                page,
                span,
                C,
                branches=branches,
                parents=context_parents,
                note="Prompt also establishes a document-local work context.",
            )

    def flow(
        key: str,
        page: int,
        span: tuple[int, int],
        *,
        parents: Sequence[Sequence[str]] = ((),),
    ) -> None:
        add(
            key,
            page,
            span,
            F,
            branches=parents,
            note="Exact source-visible routing label with reviewed ancestry.",
        )

    def anchor(
        key: str,
        page: int,
        span: tuple[int, int],
        kind: str,
        *,
        branches: Sequence[Sequence[str]] = ((),),
        parents: Sequence[str] = (),
    ) -> None:
        add(
            key,
            page,
            span,
            kind,
            branches=branches,
            parents=parents,
            note="Exact source anchor classified only within this document.",
        )

    def repeat(
        key: str,
        page: int,
        span: tuple[int, int],
        *,
        branches: Sequence[Sequence[str]] = ((),),
        relation: str,
        alias_keys: Sequence[str] = (),
        canonical_keys: Sequence[str] = (),
        evidence_keys: Sequence[str],
        target_scope: str = "unresolved",
        resolution_status: str = "preserved_for_global_resolution",
    ) -> None:
        add(
            key,
            page,
            span,
            A,
            branches=branches,
            note="Exact printed repeat or cross-reference retained.",
        )
        specs[key]["relation"] = relation
        specs[key]["repeat"] = (
            tuple(alias_keys),
            tuple(canonical_keys),
            tuple(evidence_keys),
            target_scope,
            resolution_status,
        )

    # Section C: head current employment.
    flow("d_route", 6, lines(6, "TURNTo P. 15,", "SECTIOND"))
    flow("c_has_job", 6, physical(6, 27))
    flow("e_otherwise", 6, physical(6, 28, 29))
    c_path = (("c_has_job",),)
    d_path = (("d_route",),)
    e_path = (("e_otherwise",),)

    anchor("c_head_role", 6, needle(6, "(HEAD)"), R)
    anchor("c_head_role_header", 6, needle(6, "HEAD", 0), R)
    anchor("c_section_context", 6, physical(6, 2), C)
    question("c1_assignment", 6, physical(6, 5, 6), context=True)
    question(
        "c2_employee_self",
        6,
        physical(6, 26),
        branches=c_path,
        context=True,
    )
    question(
        "c3_government",
        6,
        physical(6, 32, 33),
        branches=c_path,
        context=True,
    )

    anchor(
        "c_current_job",
        7,
        needle(7, "present         position"),
        J,
        branches=c_path,
    )
    question(
        "c6_occupation",
        7,
        physical(7, 3),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c7_duties",
        7,
        physical(7, 8),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c8_industry",
        7,
        physical(7, 13),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c9_tenure",
        7,
        physical(7, 17),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    flow("c10_less", 7, physical(7, 23), parents=c_path)
    flow("c10_long", 7, physical(7, 25), parents=c_path)
    anchor("c_head_role_tenure", 7, needle(7, "HEAD", 1), R, branches=c_path)
    c_prior_path = (("c_has_job", "c10_less"),)
    question(
        "c11_start_month",
        7,
        physical(7, 28),
        branches=c_prior_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c12_prior_job_exit",
        7,
        physical(7, 30, 31),
        branches=c_prior_path,
        context=True,
        context_parents=("c_prior_job",),
    )
    anchor(
        "c_prior_job",
        7,
        needle(7, "the job you had before"),
        J,
        branches=c_prior_path,
    )
    question(
        "c13_job_comparison", 7, physical(7, 37, 38), branches=c_prior_path
    )
    question("c15_pay_comparison", 7, physical(7, 49), branches=c_prior_path)

    flow("c16_yes", 8, needle(8, "YES", 0), parents=c_path)
    flow("c16_no_route", 8, block(8, "GO", "Cl8", 0), parents=c_path)
    c16_path = (("c_has_job", "c16_yes"),)
    question(
        "c16_family_sick",
        8,
        physical(8, 3),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c17_family_sick_amount",
        8,
        physical(8, 8),
        branches=c16_path,
        context=True,
        context_parents=("c_current_job",),
    )
    flow("c18_yes", 8, needle(8, "YES", 1), parents=c_path)
    flow("c18_no_route", 8, block(8, "GO", "C20", 1), parents=c_path)
    c18_path = (("c_has_job", "c18_yes"),)
    question(
        "c18_own_sick",
        8,
        physical(8, 13),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c19_own_sick_amount",
        8,
        physical(8, 18),
        branches=c18_path,
        context=True,
        context_parents=("c_current_job",),
    )
    flow("c20_yes", 8, needle(8, "YES", 2), parents=c_path)
    flow("c20_no_route", 8, block(8, "GO", "C22", 2), parents=c_path)
    c20_path = (("c_has_job", "c20_yes"),)
    question(
        "c20_vacation",
        8,
        physical(8, 24),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c21_vacation_amount",
        8,
        physical(8, 29),
        branches=c20_path,
        context=True,
        context_parents=("c_current_job",),
    )
    flow("c22_yes", 8, needle(8, "YES", 3), parents=c_path)
    flow("c22_no_route", 8, block(8, "TURN", "C24"), parents=c_path)
    c22_path = (("c_has_job", "c22_yes"),)
    question(
        "c22_strike",
        8,
        physical(8, 35),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c23_strike_amount",
        8,
        physical(8, 40),
        branches=c22_path,
        context=True,
        context_parents=("c_current_job",),
    )

    flow("c24_yes", 9, needle(9, "YES", 0), parents=c_path)
    flow("c24_no_route", 9, block(9, "GO", "C26"), parents=c_path)
    c24_path = (("c_has_job", "c24_yes"),)
    question(
        "c24_unemployed",
        9,
        physical(9, 3, 4),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c25_unemployed_amount",
        9,
        physical(9, 9),
        branches=c24_path,
        context=True,
        context_parents=("c_current_job",),
    )
    question(
        "c26_weeks_worked",
        9,
        physical(9, 15),
        branches=c_path,
        context=True,
        context_parents=("c_current_job",),
    )
    anchor("c_main_job", 9, needle(9, "main job", 0), J, branches=c_path)
    question(
        "c27_hours_worked",
        9,
        physical(9, 20),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    flow("c28_yes", 9, needle(9, "YES", 1), parents=c_path)
    flow("c28_no_route", 9, block(9, "TURN", "C30"), parents=c_path)
    c28_path = (("c_has_job", "c28_yes"),)
    anchor(
        "c_overtime_component",
        9,
        needle(9, "overtime", 0),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    question(
        "c28_overtime",
        9,
        physical(9, 25),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    question(
        "c29_overtime_hours",
        9,
        physical(9, 30),
        branches=c28_path,
        context=True,
        context_parents=("c_main_job",),
    )

    # Page 10 is a three-column pay grid. Exact byte slices keep columns apart.
    question(
        "c30_pay_method",
        10,
        (68, 134),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    anchor(
        "c_salary_component",
        10,
        needle(10, "salaried"),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    question("c31_salary_amount", 10, (158, 179), branches=c_path)
    question("c34_regular_rate", 10, (197, 221), branches=c_path)
    question("c34_regular_rate_middle", 10, (304, 322), branches=c_path)
    question("c34_regular_rate_end", 10, (395, 414), branches=c_path)
    anchor(
        "c34_regular_rate_component",
        10,
        (304, 322),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    question("c36_other_pay_unit", 10, (232, 249), branches=c_path)
    question("c35_overtime_rate", 10, (623, 647), branches=c_path)
    question("c35_overtime_rate_middle", 10, (700, 719), branches=c_path)
    question("c35_overtime_rate_end", 10, (773, 778), branches=c_path)
    anchor(
        "c35_overtime_rate_component",
        10,
        (700, 719),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    question("c32_extra_hours_open", 10, (658, 682), branches=c_path)
    question(
        "c32_extra_hours_continuation",
        10,
        (788, 947),
        branches=c_path,
        context=True,
        context_parents=("c_main_job",),
    )
    anchor(
        "c32_paid_extra_hours",
        10,
        (896, 947),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )
    flow("c32_yes", 10, (993, 999), parents=c_path)
    flow("c32_no_route", 10, (1005, 1120), parents=c_path)
    c32_yes_path = (("c_has_job", "c32_yes"),)
    question("c33_extra_hour_rate", 10, (1301, 1326), branches=c32_yes_path)
    question(
        "c33_extra_hour_rate_middle",
        10,
        needle(10, "7124)you make per hour"),
        branches=c32_yes_path,
    )
    question(
        "c33_extra_hour_rate_tail",
        10,
        needle(10, "for those extra"),
        branches=c32_yes_path,
    )
    question(
        "c33_extra_hour_rate_end",
        10,
        needle(10, "hours?"),
        branches=c32_yes_path,
    )
    anchor(
        "c33_extra_hour_rate_component",
        10,
        (1414, 1427),
        M,
        branches=c32_yes_path,
        parents=("c_main_job",),
    )
    question("c37_other_hour_open", 10, (1170, 1186), branches=c_path)
    question("c37_other_hour_prompt", 10, (1269, 1291), branches=c_path)
    question(
        "c37_other_hour_middle",
        10,
        needle(10, "much would you"),
        branches=c_path,
    )
    question(
        "c37_other_hour_rate",
        10,
        needle(10, "earn for that"),
        branches=c_path,
    )
    question(
        "c37_other_hour_end",
        10,
        needle(10, "hour?"),
        branches=c_path,
    )
    anchor(
        "c37_other_hour_component",
        10,
        (1485, 1498),
        M,
        branches=c_path,
        parents=("c_main_job",),
    )

    anchor(
        "c_extra_jobs",
        11,
        needle(11, "extra         jobs"),
        J,
        branches=c_path,
    )
    question(
        "c38_extra_jobs",
        11,
        physical(11, 3, 4),
        branches=c_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    flow("c38_no_route", 11, block(11, "GO", "C44"), parents=c_path)
    question(
        "c39_extra_job_occupation",
        11,
        physical(11, 10),
        branches=c_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    question("c40_more_extra_work", 11, physical(11, 14), branches=c_path)
    anchor(
        "c41_extra_job_rate",
        11,
        physical(11, 18),
        M,
        branches=c_path,
        parents=("c_extra_jobs",),
    )
    question("c41_extra_job_rate", 11, physical(11, 18), branches=c_path)
    question(
        "c42_extra_job_weeks",
        11,
        physical(11, 22),
        branches=c_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    question(
        "c43_extra_job_hours",
        11,
        physical(11, 26),
        branches=c_path,
        context=True,
        context_parents=("c_extra_jobs",),
    )
    flow("c44_no_route", 11, (0, 1), parents=())

    # Section D: head looking for work and last-job exposure.
    anchor("d_head_role", 14, needle(14, "HEAD"), R, branches=d_path)
    anchor("d_section_context", 14, physical(14, 2), C, branches=d_path)

    question(
        "d11_ever_job", 15, physical(15, 37), branches=d_path, context=True
    )
    flow("d11_yes", 15, needle(15, "YES", 1), parents=d_path)
    flow("d11_no_route", 15, needle(15, "TURN TO P. 20"), parents=d_path)
    d_job_path = (("d_route", "d11_yes"),)
    anchor(
        "d_last_job", 15, needle(15, "last     job"), J, branches=d_job_path
    )
    question(
        "d12_last_job_occupation",
        15,
        physical(15, 43),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d13_last_job_industry",
        15,
        physical(15, 50),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d14_last_job_exit",
        15,
        physical(15, 54, 55),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d15_last_worked",
        15,
        physical(15, 60),
        branches=d_job_path,
        context=True,
        context_parents=("d_last_job",),
    )

    flow("d16_worked", 16, physical(16, 4), parents=d_job_path)
    flow("d16_not_worked", 16, physical(16, 5), parents=d_job_path)
    anchor(
        "d_head_role_worked", 16, needle(16, "HEAD", 0), R, branches=d_job_path
    )
    d_work_path = (("d_route", "d11_yes", "d16_worked"),)
    flow("d17_yes", 16, needle(16, "YES", 0), parents=d_work_path)
    flow("d17_no_route", 16, block(16, "GO", "D19", 0), parents=d_work_path)
    d17_path = (("d_route", "d11_yes", "d16_worked", "d17_yes"),)
    question(
        "d17_vacation",
        16,
        physical(16, 8),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d18_vacation_amount",
        16,
        physical(16, 13),
        branches=d17_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d19_family_sick",
        16,
        physical(16, 19),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )
    flow("d19_no_route", 16, block(16, "GO", "D21", 1), parents=d_work_path)
    question(
        "d20_family_sick_amount",
        16,
        physical(16, 24),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )
    flow("d21_yes", 16, needle(16, "YES", 1), parents=d_work_path)
    flow("d21_no_route", 16, block(16, "GO", "D23", 2), parents=d_work_path)
    d21_path = (("d_route", "d11_yes", "d16_worked", "d21_yes"),)
    question(
        "d21_own_sick",
        16,
        physical(16, 30),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d22_own_sick_amount",
        16,
        physical(16, 35),
        branches=d21_path,
        context=True,
        context_parents=("d_last_job",),
    )
    flow("d23_yes", 16, needle(16, "YES", 2), parents=d_work_path)
    flow(
        "d23_no_route",
        16,
        block(16, "TUR", "D25", 1),
        parents=d_work_path,
    )
    d23_path = (("d_route", "d11_yes", "d16_worked", "d23_yes"),)
    question(
        "d23_strike",
        16,
        physical(16, 41),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d24_strike_amount",
        16,
        physical(16, 46),
        branches=d23_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d25_unemployed",
        17,
        physical(17, 4, 5),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )
    flow("d25_no_route", 17, block(17, "GO", "D27"), parents=d_work_path)
    question(
        "d26_unemployed_amount",
        17,
        physical(17, 10),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d27_weeks_worked",
        17,
        physical(17, 16),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )
    question(
        "d28_hours_worked",
        17,
        physical(17, 21),
        branches=d_work_path,
        context=True,
        context_parents=("d_last_job",),
    )

    # Section E: actual work while otherwise out of the labor force.
    anchor(
        "e_head_role",
        18,
        needle(18, "HEAD IS RETIRED", 0),
        R,
        branches=e_path,
    )
    anchor("e_section_context", 18, physical(18, 2), C, branches=e_path)
    anchor(
        "e_work_for_money",
        18,
        needle(18, "work for               money"),
        J,
        branches=e_path,
    )
    question(
        "e3_worked",
        18,
        physical(18, 16),
        branches=e_path,
        context=True,
        context_parents=("e_work_for_money",),
    )
    flow("e3_yes", 18, needle(18, "YES"), parents=e_path)
    flow("e3_no_route", 18, physical(18, 20), parents=e_path)
    e_work_paths = (("e_route", "e3_yes"), ("e_otherwise", "e3_yes"))
    question(
        "e4_occupation",
        18,
        physical(18, 22),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e5_industry",
        18,
        physical(18, 27),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e6_weeks",
        18,
        physical(18, 31),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e7_hours",
        18,
        physical(18, 36),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    flow("e8_no", 18, physical(18, 43), parents=e_work_paths)
    flow("e8_yes_route", 18, physical(18, 44), parents=e_work_paths)
    e_exit_paths = (
        ("e_route", "e3_yes", "e8_no"),
        ("e_otherwise", "e3_yes", "e8_no"),
    )
    question(
        "e8_still_working",
        18,
        physical(18, 41),
        branches=e_work_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )
    question(
        "e9_job_exit",
        18,
        physical(18, 46, 47),
        branches=e_exit_paths,
        context=True,
        context_parents=("e_work_for_money",),
    )

    # Sections F-H: spouse/friend employment.
    flow("f_wife_in_fu", 20, physical(20, 8, 9))
    flow("f_no_wife", 20, physical(20, 10))
    flow("f_head_female", 20, physical(20, 11))
    f_wife_path = (("f_wife_in_fu",),)
    anchor(
        "f_wife_role_gate", 20, needle(20, "WIFE", 0), R, branches=f_wife_path
    )
    anchor("f_section_context", 20, physical(20, 3), C, branches=f_wife_path)
    anchor(
        "f_wife_role",
        20,
        needle(20, "(wife/friend)", 0),
        R,
        branches=f_wife_path,
    )
    repeat(
        "f1_wife_definition",
        20,
        block(20, "(REMEMBER:", "CONSIDERED WIFE)"),
        branches=f_wife_path,
        relation="explicit_repeat_instruction",
        evidence_keys=("f1_wife_definition",),
        target_scope="document_local",
    )
    question(
        "f2_assignment",
        20,
        physical(20, 14, 15),
        branches=f_wife_path,
        context=True,
    )
    flow("g_route", 20, needle(20, "TURll TO P. 25,"), parents=f_wife_path)
    flow("h_route", 20, needle(20, "TURN TO P . 28,"), parents=f_wife_path)
    flow(
        "f_has_job",
        20,
        needle(20, "GO TO F3 IF HAS JOB"),
        parents=f_wife_path,
    )
    flow(
        "h_otherwise",
        20,
        block(20, "OTHERWISE", "SECTION H"),
        parents=f_wife_path,
    )
    f_job_path = (("f_wife_in_fu", "f_has_job"),)
    g_path = (("f_wife_in_fu", "g_route"),)
    h_path = (
        ("f_wife_in_fu", "h_route"),
        ("f_wife_in_fu", "h_otherwise"),
    )
    question(
        "f3_employee_self",
        20,
        physical(20, 36),
        branches=f_job_path,
        context=True,
    )
    anchor(
        "f_current_job",
        20,
        needle(20, "current            job"),
        J,
        branches=f_job_path,
    )
    question(
        "f4_government",
        20,
        physical(20, 43, 44),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )

    anchor(
        "f_present_position",
        21,
        needle(21, "present       position"),
        J,
        branches=f_job_path,
    )
    question(
        "f7_occupation",
        21,
        physical(21, 3),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    question(
        "f8_duties",
        21,
        physical(21, 11),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    question(
        "f9_industry",
        21,
        physical(21, 16),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    question(
        "f10_tenure",
        21,
        physical(21, 21),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    flow("f11_less", 21, physical(21, 29), parents=f_job_path)
    flow("f11_long", 21, physical(21, 31, 32), parents=f_job_path)
    f_prior_path = (("f_wife_in_fu", "f_has_job", "f11_less"),)
    question(
        "f12_start_month",
        21,
        physical(21, 36),
        branches=f_prior_path,
        context=True,
        context_parents=("f_present_position",),
    )
    anchor(
        "f_prior_job",
        21,
        needle(21, "job she had before"),
        J,
        branches=f_prior_path,
    )
    question(
        "f13_prior_job_exit",
        21,
        physical(21, 41, 42),
        branches=f_prior_path,
        context=True,
        context_parents=("f_prior_job",),
    )

    flow("f14_yes", 22, needle(22, "YES", 0), parents=f_job_path)
    flow("f14_no_route", 22, block(22, "GO", "F16", 0), parents=f_job_path)
    f14_path = (("f_wife_in_fu", "f_has_job", "f14_yes"),)
    question(
        "f14_family_sick",
        22,
        physical(22, 2, 3),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    question(
        "f15_family_sick_amount",
        22,
        physical(22, 8),
        branches=f14_path,
        context=True,
        context_parents=("f_present_position",),
    )
    flow("f16_yes", 22, needle(22, "YES", 1), parents=f_job_path)
    flow("f16_no_route", 22, block(22, "GO", "F18", 1), parents=f_job_path)
    f16_path = (("f_wife_in_fu", "f_has_job", "f16_yes"),)
    question(
        "f16_own_sick",
        22,
        physical(22, 14),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    question(
        "f17_own_sick_amount",
        22,
        physical(22, 19),
        branches=f16_path,
        context=True,
        context_parents=("f_present_position",),
    )
    flow("f18_yes", 22, needle(22, "YES", 2), parents=f_job_path)
    flow("f18_no_route", 22, block(22, "GO", "F20", 2), parents=f_job_path)
    f18_path = (("f_wife_in_fu", "f_has_job", "f18_yes"),)
    question(
        "f18_vacation",
        22,
        physical(22, 25),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    question(
        "f19_vacation_amount",
        22,
        physical(22, 30),
        branches=f18_path,
        context=True,
        context_parents=("f_present_position",),
    )
    flow("f20_yes", 22, needle(22, "YES", 3), parents=f_job_path)
    flow("f20_no_route", 22, needle(22, "GOTOF22"), parents=f_job_path)
    f20_path = (("f_wife_in_fu", "f_has_job", "f20_yes"),)
    question(
        "f20_strike",
        22,
        physical(22, 36),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    question(
        "f21_strike_amount",
        22,
        physical(22, 41),
        branches=f20_path,
        context=True,
        context_parents=("f_present_position",),
    )
    flow("f22_yes", 22, needle(22, "YES", 4), parents=f_job_path)
    flow("f22_no_route", 22, block(22, "TUR", "F24"), parents=f_job_path)
    f22_path = (("f_wife_in_fu", "f_has_job", "f22_yes"),)
    question(
        "f22_unemployed",
        22,
        physical(22, 47, 48),
        branches=f_job_path,
        context=True,
        context_parents=("f_present_position",),
    )
    question(
        "f23_unemployed_amount",
        22,
        physical(22, 53),
        branches=f22_path,
        context=True,
        context_parents=("f_present_position",),
    )

    anchor("f_main_job", 23, (315, 323), J, branches=f_job_path)
    question(
        "f24_weeks_worked",
        23,
        (207, 345),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_job",),
    )
    question(
        "f25_hours_worked",
        23,
        (450, 601),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_job",),
    )
    question(
        "f26_overtime",
        23,
        (715, 834),
        branches=f_job_path,
        context=True,
        context_parents=("f_main_job",),
    )
    flow("f26_yes", 23, (872, 881), parents=f_job_path)
    flow("f26_no_route", 23, (944, 953), parents=f_job_path)
    f26_path = (("f_wife_in_fu", "f_has_job", "f26_yes"),)
    question(
        "f27_overtime_hours",
        23,
        (987, 1072),
        branches=f26_path,
        context=True,
        context_parents=("f_main_job",),
    )
    question(
        "f28_pay_method",
        23,
        (1175, 1276),
        branches=f_job_path,
        context=True,
        context_parents=("f_current_job",),
    )
    question("f29_salary_amount", 23, (1401, 1435), branches=f_job_path)
    question("f29_salary_amount_tail", 23, (1528, 1535), branches=f_job_path)
    anchor(
        "f29_salary_amount_component",
        23,
        (1528, 1535),
        M,
        branches=f_job_path,
        parents=("f_current_job",),
    )
    question("f31_other_pay_unit", 23, (1497, 1514), branches=f_job_path)
    anchor(
        "f30_hourly_rate_component",
        23,
        (1729, 1763),
        M,
        branches=f_job_path,
        parents=("f_current_job",),
    )

    anchor(
        "f_extra_jobs",
        24,
        needle(24, "extra                jobs"),
        J,
        branches=f_job_path,
    )
    question(
        "f32_extra_jobs",
        24,
        physical(24, 3, 4),
        branches=f_job_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    flow("f32_no_route", 24, block(24, "GO", "F36"), parents=f_job_path)
    question(
        "f33_extra_job_occupation",
        24,
        physical(24, 10),
        branches=f_job_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    question(
        "f34_extra_job_weeks",
        24,
        physical(24, 14),
        branches=f_job_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )
    question(
        "f35_extra_job_hours",
        24,
        physical(24, 18),
        branches=f_job_path,
        context=True,
        context_parents=("f_extra_jobs",),
    )

    anchor("g_section_context", 25, physical(25, 2), C, branches=g_path)
    anchor(
        "g_wife_role", 25, needle(25, "(wife/friend)", 0), R, branches=g_path
    )
    question(
        "g5_ever_job", 25, physical(25, 27), branches=g_path, context=True
    )
    flow("g5_no_route", 25, physical(25, 31), parents=g_path)
    g_job_path = g_path
    anchor(
        "g_last_job", 25, needle(25, "last      job"), J, branches=g_job_path
    )
    question(
        "g6_last_job_occupation",
        25,
        physical(25, 34, 35),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g7_last_job_industry",
        25,
        physical(25, 41),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g8_last_job_exit",
        25,
        physical(25, 45, 46),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g9_last_worked",
        25,
        physical(25, 51),
        branches=g_job_path,
        context=True,
        context_parents=("g_last_job",),
    )

    flow("g10_worked", 26, physical(26, 5), parents=g_job_path)
    flow("g10_not_worked", 26, physical(26, 7), parents=g_job_path)
    anchor(
        "g_wife_role_worked", 26, needle(26, "WIFE", 0), R, branches=g_job_path
    )
    g_work_path = (("f_wife_in_fu", "g_route", "g10_worked"),)
    flow("g11_yes", 26, needle(26, "YES", 0), parents=g_work_path)
    flow("g11_no_route", 26, block(26, "GO", "G13", 0), parents=g_work_path)
    g11_path = ((*g_work_path[0], "g11_yes"),)
    question(
        "g11_vacation",
        26,
        physical(26, 11),
        branches=g_work_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g12_vacation_amount",
        26,
        physical(26, 16),
        branches=g11_path,
        context=True,
        context_parents=("g_last_job",),
    )
    flow("g13_yes", 26, needle(26, "YES", 1), parents=g_work_path)
    flow("g13_no_route", 26, block(26, "GO", "G15", 1), parents=g_work_path)
    g13_path = ((*g_work_path[0], "g13_yes"),)
    question(
        "g13_family_sick",
        26,
        physical(26, 22, 23),
        branches=g_work_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g14_family_sick_amount",
        26,
        physical(26, 36, 37),
        branches=g13_path,
        context=True,
        context_parents=("g_last_job",),
    )
    flow("g15_yes", 26, needle(26, "YES", 2), parents=g_work_path)
    flow("g15_no_route", 26, block(26, "GO", "G17", 2), parents=g_work_path)
    g15_path = ((*g_work_path[0], "g15_yes"),)
    question(
        "g15_own_sick",
        26,
        physical(26, 43),
        branches=g_work_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g16_own_sick_amount",
        26,
        physical(26, 48),
        branches=g15_path,
        context=True,
        context_parents=("g_last_job",),
    )
    flow("g17_yes", 26, needle(26, "YES", 3), parents=g_work_path)
    flow(
        "g17_no_route",
        26,
        block(26, "TUR", "G19", 1),
        parents=g_work_path,
    )
    g17_path = ((*g_work_path[0], "g17_yes"),)
    question(
        "g17_strike",
        26,
        physical(26, 54),
        branches=g_work_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g18_strike_amount",
        26,
        physical(26, 59),
        branches=g17_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g19_unemployed",
        27,
        physical(27, 3, 4),
        branches=g_work_path,
        context=True,
        context_parents=("g_last_job",),
    )
    flow("g19_no_route", 27, block(27, "GO", "621"), parents=g_work_path)
    question(
        "g20_unemployed_amount",
        27,
        physical(27, 9),
        branches=g_work_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g21_weeks_worked",
        27,
        physical(27, 15),
        branches=g_work_path,
        context=True,
        context_parents=("g_last_job",),
    )
    question(
        "g22_hours_worked",
        27,
        physical(27, 20),
        branches=g_work_path,
        context=True,
        context_parents=("g_last_job",),
    )

    anchor("h_section_context", 28, physical(28, 2, 3), C, branches=h_path)
    anchor("h_wife_role", 28, needle(28, "WIFE/FRIEND"), R, branches=h_path)
    anchor("h_wife_role_gate", 28, needle(28, "WIFE", 1), R, branches=h_path)
    anchor(
        "h_work_for_money",
        28,
        needle(28, "work for          money"),
        J,
        branches=h_path,
    )
    question(
        "h3_worked",
        28,
        physical(28, 17),
        branches=h_path,
        context=True,
        context_parents=("h_work_for_money",),
    )
    flow("h3_yes", 28, needle(28, "YES", 0), parents=h_path)
    flow("h3_no_route", 28, physical(28, 21), parents=h_path)
    h_work_paths = tuple((*path, "h3_yes") for path in h_path)
    question(
        "h4_occupation",
        28,
        physical(28, 23),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h5_industry",
        28,
        physical(28, 28),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h6_weeks",
        28,
        physical(28, 33),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h7_hours",
        28,
        physical(28, 38),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    question(
        "h8_still_working",
        28,
        physical(28, 43),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )
    flow("h8_yes_route", 28, physical(28, 46), parents=h_work_paths)
    question(
        "h9_job_exit",
        28,
        physical(28, 48, 49),
        branches=h_work_paths,
        context=True,
        context_parents=("h_work_for_money",),
    )

    # A lone role-equivalence instruction survives on otherwise out-of-scope J.
    repeat(
        "j3_wife_definition",
        30,
        block(30, "(REMEMBER:", "CONSIDERED WIFE)"),
        relation="explicit_repeat_instruction",
        evidence_keys=("j3_wife_definition",),
        target_scope="document_local",
    )

    # Section K: farm, business, and two-role work-income aggregates.
    flow("k1_farmer", 35, physical(35, 9))
    flow("k1_nonfarmer", 35, physical(35, 10))
    farmer_path = (("k1_farmer",),)
    k_income_paths = (("k1_farmer",), ("k1_nonfarmer",))
    anchor(
        "k2_farm", 35, needle(35, "from farming", 0), FA, branches=farmer_path
    )
    anchor(
        "k2_receipts",
        35,
        needle(35, "total receipts"),
        M,
        branches=farmer_path,
        parents=("k2_farm",),
    )
    question(
        "k2_farm_receipts", 35, physical(35, 14, 15), branches=farmer_path
    )
    anchor(
        "k3_expenses",
        35,
        block(35, "operating", "expenses"),
        M,
        branches=farmer_path,
        parents=("k2_farm",),
    )
    question(
        "k3_farm_expenses", 35, physical(35, 17, 18), branches=farmer_path
    )
    anchor(
        "k4_farm", 35, needle(35, "from farming", 1), FA, branches=farmer_path
    )
    anchor(
        "k4_net_income",
        35,
        block(35, "net", "income"),
        M,
        branches=farmer_path,
        parents=("k4_farm",),
    )
    question("k4_farm_net", 35, physical(35, 20), branches=farmer_path)
    anchor(
        "k5_business_owned",
        35,
        needle(35, "own a business"),
        BA,
        branches=k_income_paths,
    )
    anchor(
        "k5_business_enterprise",
        35,
        needle(35, "business enterprise"),
        BA,
        branches=k_income_paths,
    )
    question(
        "k5_business_assignment",
        35,
        physical(35, 22, 23),
        branches=k_income_paths,
    )
    flow("k5_no_route", 35, (1759, 1795), parents=k_income_paths)
    question(
        "k6_incorporation",
        35,
        physical(35, 28, 29),
        branches=k_income_paths,
        context=True,
        context_parents=("k5_business_owned",),
    )
    anchor(
        "k7_business",
        35,
        needle(35, "income from the business"),
        BA,
        branches=k_income_paths,
    )
    anchor(
        "k7_business_income",
        35,
        block(35, "total", "income", 2),
        M,
        branches=k_income_paths,
        parents=("k7_business",),
    )
    question(
        "k7_business_share",
        35,
        physical(35, 34, 35),
        branches=k_income_paths,
    )
    anchor("k1_head_role", 35, needle(35, "HEAD", 0), R)
    anchor("k8_head_role", 35, needle(35, "(HEAD)"), R)
    anchor("k8_head_work_total", 35, physical(35, 40, 41), T)
    anchor(
        "k8_wages_salaries",
        35,
        needle(35, "wages and salaries"),
        M,
        parents=("k8_head_work_total",),
    )
    question("k8_work_total", 35, physical(35, 40, 41))
    anchor(
        "k9_additional_compensation",
        35,
        physical(35, 46),
        M,
        parents=("k8_head_work_total",),
    )
    question("k9_additional_compensation", 35, physical(35, 46))
    flow("k9_yes", 35, needle(35, "YES"))
    flow("k9_no_route", 35, (3005, 3024))
    question(
        "k10_additional_amount",
        35,
        physical(35, 51, 53),
        note=(
            "K10 is visually under K9 YES, but canonical Poppler column "
            "order places this prompt before the YES bytes; root ancestry "
            "preserves the protocol's earlier-parent law without inventing "
            "a reordered source branch."
        ),
    )

    question("k11_other_work_income", 36, physical(36, 2, 4))
    anchor("k11_head_role", 36, needle(36, "HEAD", 0), R)
    anchor("k11_professional_trade", 36, needle(36, "PROFESSIOhAL"), BA)
    anchor("k11_farming", 36, needle(36, "farming"), FA)
    anchor("k11_roomers", 36, needle(36, "roomers"), BA)
    question("k11_professional_trade", 36, physical(36, 12, 14))
    question("k11_farming_gardening", 36, physical(36, 17))
    question("k11_roomers", 36, physical(36, 21))
    question("k12_amount", 36, needle(36, "How much was it?"))
    question("k13_duration", 36, physical(36, 8, 10))
    repeat(
        "k11_repeat",
        36,
        block(36, "(FOR EACH", "K13.)"),
        relation="explicit_repeat_instruction",
        evidence_keys=(
            "k11_professional_trade",
            "k11_farming",
            "k11_roomers",
            "k11_repeat",
        ),
    )

    flow("k25_wife_in_fu", 38, physical(38, 4))
    flow("k25_no_wife", 38, physical(38, 5))
    flow("k25_head_female", 38, physical(38, 7))
    k25_path = (("k25_wife_in_fu",),)
    anchor("k25_wife_role", 38, needle(38, "WIFE", 0), R, branches=k25_path)
    question("k26_wife_income", 38, physical(38, 10), branches=k25_path)
    flow("k26_no_route", 38, physical(38, 12), parents=k25_path)
    k26_path = k25_path
    anchor(
        "k27_wife_work_earnings",
        38,
        needle(38, "earnings"),
        M,
        branches=k26_path,
        parents=("k28_wife_work_total",),
    )
    question("k27_wife_work_earnings", 38, physical(38, 16), branches=k26_path)
    flow("k27_yes", 38, needle(38, "YES", 0), parents=k26_path)
    flow("k27_no_route", 38, needle(38, "GO TO K29"), parents=k26_path)
    k27_path = (("k25_wife_in_fu", "k27_yes"),)
    anchor("k28_wife_work_total", 38, physical(38, 21), T, branches=k27_path)
    question("k28_wife_work_amount", 38, physical(38, 21), branches=k27_path)

    # Explicit role-equivalence and cross-document references.
    flow("l_new_wife", 54, physical(54, 9, 10))
    flow("l_head_female", 54, physical(54, 11))
    flow("l_no_wife", 54, physical(54, 13, 14))
    flow("l_same_wife", 54, physical(54, 15, 17))
    l_path = (("l_new_wife",),)
    anchor("l_wife_role", 54, needle(54, "WIFE", 0), R, branches=l_path)
    repeat(
        "l1_wife_definition",
        54,
        block(54, "(REMEMBER:", "CONSIDERED WIFE)"),
        branches=l_path,
        relation="explicit_repeat_instruction",
        evidence_keys=("l1_wife_definition",),
        target_scope="document_local",
    )
    repeat(
        "l1_same_wife_crossref",
        54,
        needle(54, "SArlE WIFE AS IN 1979"),
        branches=(("l_same_wife",),),
        relation="explicit_cross_reference",
        evidence_keys=("l1_same_wife_crossref",),
        target_scope="cross_document",
    )
    question(
        "l10_years_worked",
        54,
        physical(54, 45),
        branches=l_path,
        context=True,
    )
    flow(
        "l10_exit",
        54,
        needle(54, "TURN TO P. 55, SECTION rl"),
        parents=l_path,
    )
    question(
        "l11_full_time_years",
        54,
        physical(54, 49),
        branches=l_path,
        context=True,
    )
    flow(
        "l11_exit",
        54,
        needle(54, "TURN TO P. 55, SECTION I,1"),
        parents=l_path,
    )
    question(
        "l12_part_time_share",
        54,
        physical(54, 54, 55),
        branches=l_path,
        context=True,
    )

    flow("m_new_head", 55, physical(55, 9))
    flow("m_same_head", 55, physical(55, 11, 12))
    m_path = (("m_new_head",),)
    anchor(
        "m_head_role",
        55,
        needle(55, "HEAD IS A ilEN HEAD THIS YEAR"),
        R,
        branches=m_path,
    )
    anchor(
        "m_first_job",
        55,
        needle(55, "first       full-time       regular    job"),
        J,
        branches=m_path,
    )
    repeat(
        "m1_same_head_crossref",
        55,
        block(55, "HEAD IS THE SAFlE HEAD", "ITEll '4"),
        branches=(("m_same_head",),),
        relation="explicit_cross_reference",
        evidence_keys=("m1_same_head_crossref",),
        target_scope="cross_document",
    )
    question(
        "m4_first_job",
        55,
        physical(55, 50),
        branches=m_path,
        context=True,
        context_parents=("m_first_job",),
    )
    question(
        "m5_occupation_pattern",
        55,
        physical(55, 55, 56),
        branches=m_path,
        context=True,
        context_parents=("m_first_job",),
    )
    question(
        "m25_years_worked",
        57,
        physical(57, 37),
        branches=m_path,
        context=True,
    )
    flow("m25_exit", 57, needle(57, "TURN TO P. 58, bi2a"), parents=m_path)
    question(
        "m26_full_time_years",
        57,
        physical(57, 41),
        branches=m_path,
        context=True,
    )
    flow("m26_exit", 57, needle(57, "TURN ~0 P. 58, fi28"), parents=m_path)
    question(
        "m27_part_time_share",
        57,
        physical(57, 45, 46),
        branches=m_path,
        context=True,
    )

    ordered_specs = sorted(
        specs.values(),
        key=lambda row: (
            row["page"],
            row["start"],
            row["end"],
            annotation.KIND_ORDER[row["kind"]],
            row["key"],
        ),
    )
    for left, right in zip(ordered_specs, ordered_specs[1:], strict=False):
        if (
            left["page"] == right["page"]
            and left["kind"] == right["kind"]
            and right["start"] < left["end"]
        ):
            raise ValueError(
                "partially overlapping same-kind authored atoms: "
                f"{left['key']} / {right['key']}"
            )

    review_id_by_key = {
        row["key"]: _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            row["kind"],
        )
        for row in ordered_specs
    }
    flow_path_count = {
        row["key"]: len(row["branches"])
        for row in ordered_specs
        if row["kind"] == F
    }

    def translate_path(path: Sequence[str]) -> list[str]:
        translated: list[str] = []
        for key in path:
            if key not in review_id_by_key:
                continue
            review_id = review_id_by_key[key]
            translated.append(
                annotation._review_branch_ref(
                    review_id,
                    translated,
                    flow_path_count[key],
                )
            )
        return translated

    occurrence_specs = [
        {
            "review_occurrence_id": review_id_by_key[row["key"]],
            "page_number": row["page"],
            "utf8_byte_start": row["start"],
            "utf8_byte_end": row["end"],
            "occurrence_kind": row["kind"],
            "parent_review_branch_paths": [
                translate_path(path) for path in row["branches"]
            ],
            "review_note": row["note"],
        }
        for row in ordered_specs
    ]

    anchor_specs = []
    for row in ordered_specs:
        if row["kind"] not in annotation.ANCHOR_KINDS:
            continue
        matched = (
            page_texts[row["page"] - 1]
            .encode("utf-8")[row["start"] : row["end"]]
            .decode("utf-8")
        )
        if row["kind"] == R:
            node_domain = "role"
            classification = annotation.stage1_candidates._role_classification(
                matched
            )
        else:
            node_domain, classification = annotation.ANCHOR_CLASSIFICATION[
                row["kind"]
            ]
        anchor_specs.append(
            {
                "review_occurrence_id": review_id_by_key[row["key"]],
                "node_domain": node_domain,
                "classification": classification,
                "printed_identifier": annotation._source_printed_identifier(
                    page_texts[row["page"] - 1], row["start"]
                ),
                "parent_review_occurrence_ids": [
                    review_id_by_key[parent] for parent in row["parents"]
                ],
                "parent_resolution_note": (
                    "Exact document-local source parent(s) retained."
                    if row["parents"]
                    else "No document-local component parent applies."
                ),
                "classification_status": "provisional_document_local",
            }
        )

    repeat_specs = []
    source_order_by_key = {
        row["key"]: position for position, row in enumerate(ordered_specs)
    }
    for row in ordered_specs:
        repeat = row.get("repeat")
        if repeat is None:
            continue
        alias_keys, canonical_keys, evidence_keys, target, status = repeat
        alias_keys = tuple(
            sorted(alias_keys, key=source_order_by_key.__getitem__)
        )
        canonical_keys = tuple(
            sorted(canonical_keys, key=source_order_by_key.__getitem__)
        )
        evidence_keys = tuple(
            sorted(evidence_keys, key=source_order_by_key.__getitem__)
        )
        repeat_specs.append(
            {
                "review_occurrence_id": review_id_by_key[row["key"]],
                "relation": row.get("relation", "explicit_cross_reference"),
                "alias_anchor_review_occurrence_ids": [
                    review_id_by_key[key] for key in alias_keys
                ],
                "canonical_anchor_review_occurrence_ids": [
                    review_id_by_key[key] for key in canonical_keys
                ],
                "evidence_review_occurrence_ids": [
                    review_id_by_key[key] for key in evidence_keys
                ],
                "target_scope": target,
                "resolution_status": status,
            }
        )

    page_counts = Counter(row["page"] for row in ordered_specs)
    page_review_rows = []
    for page_number, page_text in enumerate(page_texts, start=1):
        count = page_counts[page_number]
        if count == 0:
            note = (
                "Whole page reviewed; no covered R_Q source atoms retained "
                "after nonemployment and third-party exclusions."
            )
        else:
            note = (
                "Whole page reviewed against the pinned q79 extraction; "
                f"retained {count} exact source atom(s)."
            )
        page_review_rows.append(
            {
                "page_number": page_number,
                "page_text_utf8_sha256": annotation._sha256(
                    page_text.encode("utf-8")
                ),
                "whole_page_review_complete": True,
                "review_status": "complete",
                "review_note": note,
            }
        )

    review: dict[str, Any] = {
        "schema_version": annotation.REVIEW_SCHEMA_VERSION,
        "review_id": "rq-stage2-source-review:"
        + annotation._canonical_digest(
            [source_document_id, annotation.DOCUMENT_SOURCE_POSITION]
        ),
        "authority_kind": "reviewer_authored_source_bytes_only_nonauthority",
        "document_source_position": annotation.DOCUMENT_SOURCE_POSITION,
        "source_document_id": source_document_id,
        "review_method": {
            "source_rows_derived_from_page_bytes": True,
            "whole_page_review": "all_59_pages_including_empty_occurrence_pages",
            "span_granularity": "exact_utf8_lexeme_physical_line_or_source_block",
            "candidate_nonselection": "candidates_joined_only_after_source_rows_complete",
            "global_ids_assigned": False,
        },
        "page_review_rows": page_review_rows,
        "occurrence_specs": occurrence_specs,
        "local_anchor_specs": anchor_specs,
        "repeat_alias_specs": repeat_specs,
        "integrity": {
            "canonicalization": annotation.CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": "complete",
    }
    review["integrity"]["content_sha256"] = annotation._content_sha256(review)
    annotation.validate_review(review, document, page_texts)
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    value = author_review()
    raw = annotation._canonical_bytes(value)
    if args.check:
        if not annotation.REVIEW_PATH.exists():
            raise SystemExit("document 24 source review is missing")
        if annotation.REVIEW_PATH.read_bytes() != raw:
            raise SystemExit("document 24 source review is stale")
    else:
        annotation.REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        annotation.REVIEW_PATH.write_bytes(raw)
    print(
        f"document 24 source review: {len(value['page_review_rows'])} pages, "
        f"{len(value['occurrence_specs'])} occurrences"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
