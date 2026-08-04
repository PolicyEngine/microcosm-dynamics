#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 33.

The 184-page 1984 QxQ was reviewed page by page from authenticated Poppler
text. This helper records the retained employment, work-income, role, and
limited work-history source regions. It reruns the fixed lexical detectors
against source bytes but never opens the committed stage-1 candidate artifact;
candidate rows are joined only by the sealed annotation builder.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_033_annotation as annotation

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

# Whole-page review retained the two employment route families, the work-linked
# income pages, and narrow lifetime-work regions.  Cover, housing, housework,
# food, transfer, health, asset, education, and exercise pages contribute no
# occurrence merely because nearby prose contains worklike words.
HEAD_EMPLOYMENT_PAGES = frozenset(
    {*range(19, 65), *range(67, 85)} - {65, 66, 74}
)
WIFE_EMPLOYMENT_PAGES = frozenset(range(85, 116)) - {87, 105}
WORK_INCOME_PAGES = frozenset({*range(123, 134), 141, 142})
WORK_HISTORY_PAGES = frozenset({175, 176, 177, 178, 181, 182})
ROLE_ONLY_PAGES: frozenset[int] = frozenset()
FLOW_ONLY_PAGES = frozenset({117, 119, 121, 173})
SEMANTIC_PAGES = frozenset().union(
    HEAD_EMPLOYMENT_PAGES,
    WIFE_EMPLOYMENT_PAGES,
    WORK_INCOME_PAGES,
    WORK_HISTORY_PAGES,
    ROLE_ONLY_PAGES,
    FLOW_ONLY_PAGES,
)

EMPLOYMENT_KINDS = frozenset({F, R, J, M, C, P, A})
INCOME_KINDS = frozenset(annotation.OCCURRENCE_KINDS)
HISTORY_KINDS = frozenset({F, R, J, C, P, A})
ROLE_ONLY_KINDS = frozenset({R})

# Narrative Q-by-Q pages contain generic examples and interrogative prose.
# Only a source-visible singleton printed question identifier can select a
# purpose prompt on these pages; range objectives such as C116-C122 are not
# one-to-one field labels.
QBYQ_PAGES = frozenset(
    {
        20,
        22,
        24,
        25,
        28,
        30,
        32,
        34,
        36,
        38,
        40,
        42,
        44,
        46,
        48,
        49,
        52,
        54,
        56,
        58,
        60,
        62,
        64,
        68,
        70,
        72,
        76,
        78,
        80,
        82,
        84,
        86,
        104,
        114,
        124,
        126,
        128,
        130,
        132,
        142,
        176,
        178,
        182,
    }
)

PURPOSE_IDENTIFIER_ALLOWLIST = frozenset(
    {
        "D1",
        *{f"D{number}" for number in range(5, 19) if number not in {13, 15}},
        *{f"D{number}" for number in range(20, 54) if number != 53},
        *{f"E{number}" for number in range(3, 14)},
        *{f"F{number}" for number in range(2, 7)},
        *{f"F{number}" for number in range(9, 16)},
        *{
            "F22",
            "F27",
            "F29",
            "F31",
            "F35",
            "F37",
            "F40",
            "F42",
            "F43",
            "F47",
            "F52",
            "F56",
            "F61",
        },
        *{f"F{number}" for number in range(62, 72) if number != 64},
        *{f"F{number}" for number in range(74, 79)},
        *{f"F{number}" for number in range(83, 90)},
        *{f"F{number}" for number in range(91, 111)},
        *{f"F{number}" for number in range(112, 125)},
        "G1",
        *{f"G{number}" for number in range(4, 17) if number != 13},
        *{f"G{number}" for number in range(18, 51) if number != 50},
        *{f"H{number}" for number in range(3, 14)},
        *{f"K{number}" for number in range(2, 11)},
    }
)

# Exact semantic byte windows for the partially relevant income and
# background pages.  Pages absent here use their complete text.  Page 173 is
# handled as a flow-only exception below.
REVIEWED_BYTE_WINDOWS: dict[int, tuple[tuple[int, int], ...]] = {
    67: ((55, 2030),),
    68: ((56, 1043),),
    69: ((169, 2734),),
    70: ((39, 277),),
    71: ((61, 1910),),
    72: ((39, 284),),
    73: ((106, 2683),),
    75: ((65, 3309),),
    76: ((37, 307),),
    77: ((190, 2383),),
    78: ((33, 85),),
    79: ((65, 2500),),
    80: ((34, 60),),
    81: ((180, 1947),),
    82: ((36, 1426),),
    83: ((0, 1449),),
    84: ((40, 225),),
    85: ((178, 2811),),
    86: ((37, 813),),
    88: ((74, 1763),),
    89: ((185, 2992),),
    90: ((67, 2940),),
    91: ((196, 3948),),
    92: ((58, 2745),),
    93: ((171, 2537),),
    94: ((5, 2805),),
    95: ((178, 3248),),
    96: ((66, 4644),),
    97: ((170, 2975),),
    98: ((63, 3054),),
    99: ((100, 2093),),
    100: ((65, 2335),),
    101: ((102, 1432),),
    102: ((66, 2225),),
    103: ((168, 2224),),
    104: ((38, 131),),
    106: ((60, 2190),),
    107: ((150, 617),),
    108: ((62, 1953),),
    109: ((172, 2531),),
    110: ((65, 2589),),
    111: ((185, 2532),),
    112: ((57, 2062),),
    113: ((63, 2039),),
    114: ((37, 230),),
    115: ((59, 1597),),
    117: ((505, 999), (1688, 1977), (2069, 2245)),
    119: ((176, 235), (1495, 1601), (2773, 2918), (3680, 3720)),
    121: ((245, 324), (671, 1024)),
    123: ((57, 2467),),
    124: ((40, 2497),),
    125: ((316, 2945),),
    126: ((38, 1662),),
    127: ((113, 4143),),
    128: ((41, 2517),),
    129: ((670, 5319),),
    130: ((37, 2247),),
    131: ((118, 695),),
    132: ((40, 203),),
    133: ((76, 456),),
    141: ((446, 822), (1110, 1913)),
    142: ((524, 1019),),
    173: ((272, 449), (450, 528), (529, 704), (706, 792)),
    175: ((62, 604),),
    176: ((39, 807),),
    177: ((257, 514), (2448, 3140)),
    178: ((1184, 1550),),
    181: ((162, 629), (1219, 1787)),
    182: ((39, 614), (1400, 2155)),
}

# Candidate-free atomic re-review supersedes the initial semantic-block draft
# above.  Each tuple is one exact singleton-labeled prompt; range labels,
# checkpoint headers, unlabeled continuations, and merged Poppler columns are
# absent by construction.
PURPOSE_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    19: (
        (127, 271),
        (859, 1031),
        (1272, 1434),
        (1674, 1736),
        (1945, 2117),
        (2196, 2265),
        (2457, 2514),
    ),
    20: (),
    21: (
        (138, 281),
        (914, 1094),
        (1286, 1457),
        (1555, 1617),
        (1934, 2291),
        (2338, 2396),
        (2603, 2658),
    ),
    22: ((1055, 2311), (2325, 2676), (2690, 2830), (2844, 2983)),
    23: (
        (200, 306),
        (480, 567),
        (581, 619),
        (619, 977),
        (1024, 1252),
        (1334, 1642),
        (1758, 1991),
        (1991, 2396),
    ),
    24: (),
    25: ((941, 2697),),
    26: (),
    27: (
        (119, 211),
        (331, 349),
        (362, 439),
        (453, 484),
        (484, 830),
        (830, 1062),
        (1147, 1431),
        (1537, 1758),
        (1758, 2140),
    ),
    28: ((666, 1048), (1049, 1364), (1365, 1513), (1514, 1635)),
    29: (
        (208, 597),
        (676, 719),
        (853, 910),
        (990, 1106),
        (1185, 1297),
        (1444, 1523),
    ),
    30: ((52, 773), (775, 885), (886, 1109), (1110, 1218)),
    31: (
        (0, 290),
        (295, 345),
        (419, 610),
        (848, 1135),
        (1307, 1355),
        (1840, 2373),
    ),
    32: ((258, 484), (485, 1134), (1135, 1593), (1594, 1740), (1741, 1794)),
    33: (
        (64, 406),
        (504, 956),
        (1282, 1418),
        (1502, 1559),
        (1725, 1821),
        (2548, 2587),
        (2592, 2767),
    ),
    34: (),
    35: (
        (171, 614),
        (908, 986),
        (1136, 1260),
        (1392, 1544),
        (1601, 1699),
        (1815, 1939),
    ),
    36: ((34, 1540),),
    37: (
        (299, 518),
        (818, 841),
        (841, 864),
        (864, 905),
        (905, 927),
        (1205, 1370),
        (1597, 1900),
        (2200, 2223),
        (2223, 2246),
        (2246, 2284),
        (2284, 2309),
    ),
    38: ((1021, 1174),),
    39: (
        (190, 308),
        (497, 767),
        (926, 975),
        (1854, 2036),
        (2195, 2528),
        (2763, 2851),
        (3025, 3139),
    ),
    40: ((35, 325), (470, 578), (579, 1217)),
    41: (
        (71, 179),
        (290, 399),
        (1166, 1299),
        (1398, 1502),
        (1612, 1701),
        (1702, 1887),
        (2015, 2104),
        (2161, 2265),
        (2375, 2451),
        (2533, 2728),
    ),
    42: (
        (38, 99),
        (100, 456),
        (1212, 1402),
        (1403, 1488),
        (1489, 1610),
        (1717, 1815),
        (1816, 1875),
    ),
    43: (
        (183, 309),
        (361, 683),
        (1365, 1408),
        (1408, 1486),
        (1954, 2186),
        (2599, 2713),
        (3112, 3365),
        (3370, 3486),
    ),
    44: ((69, 286), (287, 724), (735, 956), (1113, 1250), (1261, 1403)),
    45: ((1106, 1208), (1315, 1417), (1524, 1594)),
    46: (),
    47: ((176, 421), (580, 633), (708, 822)),
    48: ((33, 83), (84, 142)),
    49: (),
    50: (
        (610, 730),
        (841, 1008),
        (1121, 1210),
        (1278, 1612),
        (2597, 2684),
        (2684, 2912),
        (3099, 3362),
        (3562, 3611),
    ),
    51: (
        (584, 721),
        (812, 946),
        (1026, 1171),
        (2267, 2388),
        (2508, 2605),
        (2728, 2846),
        (2847, 2958),
        (3053, 3164),
        (3247, 3437),
    ),
    52: (),
    53: (
        (1142, 1578),
        (1746, 1808),
        (1934, 1969),
        (1970, 2026),
        (2155, 2203),
        (2343, 2451),
        (2452, 2504),
        (2633, 2697),
        (2838, 2965),
        (3085, 3210),
        (3257, 3305),
        (3451, 3578),
    ),
    54: (),
    55: (
        (0, 118),
        (160, 201),
        (357, 491),
        (627, 730),
        (735, 771),
        (1050, 1184),
        (2099, 2243),
        (2719, 2960),
        (3807, 3929),
        (4094, 4154),
    ),
    56: ((1037, 1116), (1717, 2097), (2098, 2254), (2255, 2368)),
    57: (
        (66, 181),
        (369, 426),
        (558, 699),
        (910, 1162),
        (1262, 1297),
        (1444, 1634),
        (1809, 1894),
        (2200, 2453),
        (2530, 2575),
        (2648, 2721),
    ),
    58: ((1215, 1456), (1704, 2080)),
    59: (
        (160, 363),
        (388, 424),
        (498, 568),
        (641, 840),
        (855, 906),
        (906, 1111),
        (1393, 1442),
        (1442, 1557),
        (1798, 1847),
        (1847, 2051),
    ),
    60: ((77, 436), (437, 888)),
    61: ((58, 167), (918, 1013), (1014, 1172), (2030, 2084)),
    62: ((771, 1406), (1407, 1642)),
    63: ((450, 499), (499, 909), (1499, 1729), (1804, 1931), (2004, 2224)),
    64: (),
}

FLOW_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    19: (
        (617, 677),
        (1170, 1271),
        (1573, 1673),
        (1771, 1802),
        (1811, 1943),
        (2302, 2308),
        (2338, 2455),
    ),
    21: (
        (656, 719),
        (1176, 1285),
        (1539, 1554),
        (1748, 1779),
        (1791, 1931),
        (2436, 2446),
        (2475, 2601),
    ),
    23: ((1695, 1702), (1792, 1835), (2568, 2602)),
    27: ((1479, 1486), (1543, 1609), (2318, 2339)),
    29: ((109, 170), (193, 203), (1424, 1442)),
    31: ((1279, 1297), (1917, 1935), (2401, 2470)),
    33: ((1171, 1226), (1254, 1278), (1479, 1499), (1714, 1723), (2631, 2669)),
    35: ((859, 877), (887, 905), (1125, 1134)),
    37: ((116, 193), (195, 298), (799, 808), (1577, 1595), (2172, 2190)),
    39: ((882, 923), (1603, 1640), (1678, 1763), (2753, 2760), (3004, 3023)),
    41: ((828, 974), (998, 1165), (1995, 2013)),
    43: ((1115, 1235), (1735, 1854)),
    45: ((123, 248), (352, 411), (488, 536), (562, 598), (636, 681)),
    47: ((1293, 1551), (1569, 1689)),
    50: ((2276, 2399), (2985, 3011), (3964, 4381), (4382, 4544)),
    51: (
        (143, 197),
        (199, 253),
        (291, 421),
        (421, 583),
        (774, 811),
        (3832, 4198),
        (4198, 4294),
        (5259, 5278),
        (5293, 5315),
        (5327, 5344),
        (5357, 5374),
    ),
    53: ((2121, 2152), (2552, 2630)),
    55: ((2698, 2717), (4054, 4086)),
    57: ((183, 257), (2073, 2083), (2090, 2095)),
    59: ((1298, 1382), (1653, 1660), (1702, 1709), (2172, 2192)),
    61: ((178, 295), (1663, 1700), (1701, 1891)),
    63: ((207, 269), (271, 335), (337, 436), (1289, 1313)),
}

MIDDLE_FLOW_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    67: ((611, 637), (1564, 1604)),
    69: ((285, 315), (323, 560), (1670, 1784), (1812, 1959)),
    71: ((151, 386), (405, 507), (825, 876), (1352, 1373), (1679, 1739)),
    73: ((310, 338), (911, 941), (1562, 1588), (2298, 2316)),
    75: ((280, 289), (310, 342), (2113, 2118), (2533, 2538), (2938, 2999)),
    77: ((473, 503), (869, 905), (924, 1001), (1461, 1582)),
    79: (
        (136, 207),
        (259, 285),
        (371, 399),
        (1349, 1358),
        (1408, 1432),
        (2475, 2499),
    ),
    81: ((373, 393), (426, 535), (904, 996), (1714, 1816)),
    83: ((142, 270), (615, 759)),
    88: ((212, 241), (266, 304)),
    89: ((1027, 1067), (1319, 1328), (1718, 1784), (1802, 1822)),
    90: ((415, 424), (2024, 2042), (2859, 2939)),
    91: (
        (792, 801),
        (845, 854),
        (1432, 1495),
        (1518, 1557),
        (2073, 2091),
        (2419, 2428),
        (3546, 3564),
    ),
    92: ((638, 656), (789, 807), (1147, 1156)),
    93: (
        (241, 297),
        (319, 393),
        (663, 671),
        (685, 699),
        (718, 726),
        (801, 903),
        (1589, 1607),
        (1921, 1929),
        (1943, 1957),
        (1975, 1983),
        (2055, 2158),
    ),
    94: ((662, 685), (1280, 1309), (1441, 1512), (2541, 2558)),
    95: ((1512, 1709), (1742, 1882)),
    96: ((640, 656), (670, 687), (1054, 1061), (1129, 1147), (2505, 2639)),
    97: ((237, 394), (423, 587), (679, 727), (749, 785), (814, 865)),
    98: ((160, 381), (400, 526), (1414, 1444), (1770, 1801), (2592, 2601)),
    99: ((1392, 1410), (1850, 1927)),
    100: ((1482, 1487), (1510, 1518), (2011, 2019)),
    101: ((796, 887),),
    102: (
        (131, 177),
        (226, 250),
        (332, 458),
        (1379, 1386),
        (1464, 1489),
        (2200, 2224),
    ),
    103: ((704, 726), (1694, 1731)),
    106: ((172, 201), (209, 234), (1134, 1248), (1279, 1412)),
    107: ((234, 450), (470, 616)),
    108: ((381, 430), (878, 926), (1253, 1285), (1628, 1659)),
    109: ((439, 460), (1018, 1043), (1651, 1669)),
    110: ((412, 443), (1718, 1723), (1752, 1757), (2301, 2335)),
    111: ((489, 516), (899, 942), (966, 1051), (1461, 1579)),
    112: (
        (127, 189),
        (237, 270),
        (347, 462),
        (1404, 1409),
        (1454, 1478),
        (2037, 2061),
    ),
    113: ((333, 473), (504, 699), (1055, 1073), (1815, 1914)),
    115: ((219, 458), (792, 914)),
}
MIDDLE_FLOW_REVIEWED_PAGES = frozenset(MIDDLE_FLOW_SPANS) | {85}

REPEAT_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    20: ((278, 330),),
    39: ((2195, 2290),),
    42: ((1816, 1875),),
    46: ((348, 366), (367, 421)),
    47: ((1127, 1153),),
    49: ((368, 393), (394, 416), (417, 434)),
    52: ((59, 80), (81, 275), (898, 923)),
    56: ((2046, 2097),),
    57: ((2176, 2197),),
    60: ((37, 76),),
    62: ((1478, 1527),),
}

MIDDLE_REPEAT_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    68: ((130, 291), (992, 1043)),
    70: ((39, 80), (234, 277)),
    72: ((39, 242), (242, 284)),
    75: ((2539, 2654),),
    76: ((37, 252), (252, 307)),
    78: ((33, 59), (59, 85)),
    80: ((34, 60),),
    82: ((1406, 1426),),
    86: ((427, 813),),
    100: ((1414, 1623),),
    104: ((103, 131),),
    110: ((1644, 1871),),
    114: ((202, 230),),
}

# Complete identifier-bearing purpose blocks that the conservative OCR label
# grammar cannot delimit.  F56 and F68 are visible only in the raster and have
# no authenticated Poppler bytes, so they are intentionally absent.
MIDDLE_MANUAL_PURPOSE_SPANS: dict[int, tuple[tuple[int, int, str], ...]] = {
    67: ((129, 238, "D1"),),
    68: ((911, 992, "D6"),),
    70: ((199, 234, "D14"),),
    71: ((1168, 1263, "D23"),),
    73: ((1377, 1486, "D35"), (2319, 2427, "D39")),
    75: ((1075, 1190, "D43"),),
    77: ((515, 545, "D51"),),
    81: ((1649, 1677, "E10"),),
    82: ((886, 1092, "E3"), (1184, 1406, "E9")),
    83: ((290, 334, "E13"),),
    85: ((1621, 1734, "F3"), (1883, 2162, "F4")),
    88: ((1452, 1507, "F10"),),
    89: ((312, 339, "F13"), (350, 370, "F14")),
    90: ((437, 508, "F22"),),
    95: ((2504, 2572, "F69"), (2662, 2700, "F70")),
    96: (
        (1387, 1433, "F75"),
        (1436, 1469, "F76"),
        (2826, 3068, "F77"),
    ),
    97: ((890, 1018, "F83"), (2322, 2469, "F88")),
    98: (
        (1124, 1146, "F93"),
        (2466, 2619, "F100"),
    ),
    99: ((629, 730, "F106"), (1413, 1509, "F110")),
    100: ((1627, 1874, "F119"),),
    106: ((71, 130, "G9"), (256, 403, "G10")),
    110: ((1455, 1534, "G43"),),
    113: ((1167, 1228, "H5"),),
}

REMUNERATION_EXCLUDED_SPANS = frozenset(
    {
        (26, 393, 399),
        (30, 97, 109),
        (30, 316, 328),
        (30, 1205, 1217),
        (33, 370, 374),
        (33, 701, 705),
        (24, 269, 275),
        (35, 251, 257),
        (35, 545, 551),
        (39, 2309, 2321),
        (39, 2379, 2385),
        (40, 788, 794),
        (40, 826, 838),
        (40, 874, 879),
        (41, 2666, 2680),
        (82, 1053, 1060),
        (91, 500, 504),
        (91, 973, 977),
        (94, 2059, 2071),
        (94, 2140, 2146),
        (95, 3136, 3149),
        (127, 310, 314),
        (129, 866, 870),
        (131, 541, 545),
        (133, 338, 342),
        (141, 1471, 1475),
    }
)

PURPOSE_SPANS.update(
    {
        123: (
            (756, 933),
            (934, 1113),
            (1114, 1219),
            (1222, 1419),
            (1423, 1471),
            (1543, 1660),
            (1662, 1782),
            (2042, 2165),
            (2263, 2424),
        ),
        124: ((853, 1644), (1644, 2260), (2260, 2497)),
        125: (
            (806, 1004),
            (1020, 1215),
            (1231, 1346),
            (1387, 1557),
            (1654, 1701),
            (1715, 1826),
            (1841, 1968),
            (2437, 2569),
            (2696, 2862),
        ),
        126: ((38, 312), (312, 519), (519, 744), (744, 1037), (1037, 1662)),
        127: (
            (113, 263),
            (267, 641),
            (883, 1192),
            (1196, 1242),
            (1302, 1485),
            (1629, 1990),
            (2240, 2418),
            (2674, 2758),
            (3207, 3246),
            (3692, 4142),
        ),
        128: (
            (41, 191),
            (191, 452),
            (452, 878),
            (878, 1073),
            (1073, 1392),
            (1392, 1561),
            (1561, 1753),
            (1753, 1875),
            (1875, 2499),
        ),
        129: (
            (670, 820),
            (824, 1267),
            (1501, 1809),
            (1813, 1860),
            (1932, 2113),
            (2173, 2624),
            (2949, 3266),
            (3374, 3725),
            (3999, 4038),
            (4602, 5318),
        ),
        130: ((37, 453), (453, 1675), (1675, 2247)),
        131: ((140, 404), (513, 694)),
        132: ((40, 203),),
        133: ((86, 259), (309, 455)),
        141: ((1110, 1267), (1438, 1586)),
        142: ((524, 590), (590, 780)),
        175: ((62, 157), (263, 350), (476, 603)),
        176: ((39, 260), (260, 343), (343, 807)),
        177: ((2448, 2528), (2996, 3140)),
        178: ((1184, 1550),),
        181: (
            (162, 297),
            (488, 584),
            (1219, 1303),
            (1400, 1490),
            (1603, 1786),
        ),
        182: ((39, 614), (1400, 1616), (1616, 1700), (1700, 2155)),
    }
)

CONTEXT_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    19: PURPOSE_SPANS[19],
    23: ((480, 567),),
    123: ((1662, 1782),),
    124: ((2260, 2497),),
    125: ((1841, 1968),),
    126: PURPOSE_SPANS[126],
    127: ((2240, 2418), (2674, 2758), (3207, 3246), (3692, 4142)),
    128: PURPOSE_SPANS[128],
    129: ((2949, 3266), (3374, 3725), (3999, 4038), (4602, 5318)),
    130: PURPOSE_SPANS[130],
    132: PURPOSE_SPANS[132],
    141: ((1730, 1913),),
    142: ((590, 780),),
    175: PURPOSE_SPANS[175],
    176: PURPOSE_SPANS[176],
    177: PURPOSE_SPANS[177],
    178: PURPOSE_SPANS[178],
    181: PURPOSE_SPANS[181],
    182: PURPOSE_SPANS[182],
}

LATE_REPEAT_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    125: ((318, 375),),
    126: ((312, 519), (519, 744)),
    127: ((123, 189), (1495, 1542)),
    128: ((1073, 1392), (1392, 1561), (1561, 1753), (2341, 2432)),
    129: ((678, 744), (2122, 2172)),
    130: ((37, 453), (453, 1675)),
    131: ((140, 404),),
    133: ((86, 259),),
    142: ((590, 780), (780, 1019)),
}

LATE_FLOW_REVIEWED_PAGES = frozenset(
    {
        117,
        119,
        121,
        123,
        124,
        *range(125, 134),
        141,
        142,
        173,
        175,
        176,
        177,
        178,
        181,
        182,
    }
)
LATE_REPEAT_REVIEWED_PAGES = LATE_FLOW_REVIEWED_PAGES

MANUAL_ROLE_SPANS = (
    (141, 1128, 1139),
    (175, 110, 121),
    (176, 474, 485),
    (176, 516, 527),
    (176, 631, 640),
    (177, 2475, 2481),
    (178, 1258, 1262),
    (178, 1357, 1361),
    (181, 186, 190),
    (181, 520, 524),
    (182, 435, 439),
    (182, 1519, 1523),
    (182, 1826, 1830),
    (182, 1871, 1875),
)

MANUAL_JOB_SPANS = (
    (128, 148, 162),
    (128, 382, 404),
    (128, 934, 964),
    (128, 1337, 1364),
    (130, 109, 127),
    (130, 347, 357),
    (131, 202, 214),
    (131, 556, 566),
    (132, 147, 157),
    (133, 136, 148),
    (133, 353, 363),
    (177, 2499, 2510),
    (177, 3032, 3055),
    (177, 3099, 3114),
    (178, 1221, 1242),
    (178, 1306, 1317),
    (178, 1391, 1405),
    (181, 276, 296),
    (181, 533, 550),
    (182, 321, 346),
    (182, 448, 459),
    (182, 504, 520),
)

MANUAL_REMUNERATION_SPANS = (
    (123, 791, 805),
    (123, 969, 993),
    (123, 1150, 1160),
    (123, 2317, 2348),
    (123, 2408, 2414),
    (125, 832, 848),
    (125, 1046, 1071),
    (125, 1258, 1268),
    (125, 2746, 2776),
    (125, 2847, 2853),
    (130, 594, 604),
    (131, 183, 192),
    (133, 117, 126),
)

MANUAL_TOTAL_SPANS = (
    (127, 385, 406),
    (128, 806, 829),
    (129, 965, 986),
    (141, 1438, 1586),
)

MANUAL_AGGREGATE_SPANS = (
    (58, 1356, 1364, BA),
    (125, 419, 438, FA),
    (125, 855, 864, FA),
    (125, 1275, 1282, FA),
    (125, 1680, 1691, BA),
    (125, 2457, 2468, BA),
    (125, 2602, 2613, BA),
    (125, 2768, 2776, BA),
    (126, 846, 857, BA),
    (126, 952, 964, BA),
    (127, 2682, 2690, FA),
)

# Pages 134-136 and 144-146 are transfers/general other income; pages 151-170
# are health/assets. Whole-page review rejected their worklike lexical hits.
# Within the retained income pages, aggregate anchors must name the work-income
# aggregate rather than a generic business/farm example.
FARM_INCOME_PAGES = frozenset(range(123, 133))
BUSINESS_INCOME_PAGES = frozenset({*range(123, 133), 141, 142})
ROLE_TOTAL_PAGES = frozenset({127, 128, 129, 131, 132, 133, 141})
INCOME_JOB_PAGES = frozenset({*range(127, 134), 141, 142})

COMPOSITE_WIFE_RE = re.compile(
    r"\(?(?:WIFE(?:S|['\u2019]S)?\s*/\s*[\"\u201c]\s*"
    r"WIFE(?:S|['\u2019]S)?[,\.]?\s*[\"\u201d])\)?",
    re.IGNORECASE,
)
# Poppler preserves the printed label bytes but this scan has recurrent OCR
# substitutions (``D]`` for D7, ``010`` for D10, ``Fl3`` for F13, and
# ``FJ`` for F1).  Normalize those bytes only to decide whether a source
# block is in the reviewed purpose allowlist; the occurrence itself retains
# the exact, unnormalized source bytes and hash.
FIELD_BLOCK_IDENTIFIER_RE = re.compile(
    r"(?<![A-Za-z0-9])([DEFGH0O])\s*"
    r"([0-9JILl\]][0-9A-Za-z\]]{0,3})\s*\.\s*",
    re.IGNORECASE,
)
FIELD_PAGE_BANDS = (
    ({67, 68}, "D", 1, 10),
    ({69, 70}, "D", 11, 18),
    ({71, 72}, "D", 19, 28),
    ({73}, "D", 29, 39),
    ({75, 76}, "D", 40, 49),
    ({77, 78}, "D", 50, 56),
    ({79, 80}, "D", 57, 63),
    ({81, 82}, "E", 1, 11),
    ({83, 84}, "E", 12, 16),
    ({85, 86}, "F", 1, 4),
    ({88}, "F", 5, 11),
    ({89}, "F", 12, 20),
    ({90}, "F", 21, 29),
    ({91}, "F", 30, 37),
    ({92}, "F", 38, 43),
    ({93}, "F", 44, 53),
    ({94}, "F", 54, 61),
    ({95}, "F", 62, 72),
    ({96}, "F", 73, 80),
    ({97}, "F", 81, 89),
    ({98}, "F", 90, 102),
    ({99}, "F", 103, 112),
    ({100}, "F", 113, 121),
    ({101}, "F", 122, 127),
    ({102}, "F", 128, 133),
    ({103}, "G", 1, 8),
    ({106}, "G", 9, 16),
    ({107}, "G", 17, 17),
    ({108}, "G", 18, 29),
    ({109}, "G", 30, 37),
    ({110}, "G", 38, 46),
    ({111}, "G", 47, 53),
    ({112}, "G", 54, 59),
    ({113}, "H", 1, 11),
    ({115}, "H", 12, 14),
)


def normalized_field_identifier(
    match: re.Match[str], page_number: int
) -> str | None:
    page_band = next(
        (band for band in FIELD_PAGE_BANDS if page_number in band[0]), None
    )
    if page_band is None:
        return None
    _pages, expected_section, first_number, last_number = page_band
    section = match.group(1).upper()
    if section in {"0", "O"}:
        section = expected_section or section
    if section != expected_section:
        return None
    suffix = (
        match.group(2)
        .upper()
        .translate(str.maketrans({"J": "1", "I": "1", "L": "1", "]": "7"}))
    )
    normalized = re.fullmatch(r"([0-9]{1,3})([A-Z]?)", suffix)
    if normalized is None:
        return None
    number = int(normalized.group(1))
    if not first_number <= number <= last_number:
        return None
    return f"{section}{number}{normalized.group(2)}"


MANUAL_REMUNERATION_RE = re.compile(
    r"\b(?:labor\s+income|income\s+from\s+(?:work|wages?|salar(?:y|ies)|"
    r"jobs?|business|farm)|wages?\s+and\s+salar(?:y|ies)|"
    r"hourly\s+wage\s+rate|net\s+income|operating\s+expenses)\b",
    re.IGNORECASE,
)

FLOW_EXCLUSION_MARKERS = (
    "IF NECESSARY",
    "IF POSSIBLE",
    "IF VOLUNTEERED",
    "GET DATE",
    "GET DATES",
    "IF NOT CLEAR",
    "IF R MENTIONS",
    "IF R DOESN'T",
    "IF R DOES NOT",
    "IF R RESPONDS",
    "IF R ASKS",
    "IF THE ANSWER",
    "IF HEAD",
    "IF WIFE",
    "IF NEW HEAD",
)
FLOW_ACTION_MARKERS = (
    "GO TO",
    "TURN TO",
    "ASK SECTION",
    "ASK C",
    "ASK D",
    "ASK E",
    "ASK F",
    "ASK G",
    "ASK H",
    "ASK K",
    "ALL OTHERS",
    "OTHERWISE",
    "DO NOT ASK",
    "DON'T ASK",
    "WORK HISTORY SUPPLEMENT",
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
    interview_wave = document["interview_waves"][0]

    def page_size(page: int) -> int:
        return len(page_texts[page - 1].encode("utf-8"))

    def reviewed_windows(page: int) -> tuple[tuple[int, int], ...]:
        return REVIEWED_BYTE_WINDOWS.get(page, ((0, page_size(page)),))

    def inside_reviewed_window(page: int, start: int, end: int) -> bool:
        return any(
            window_start <= start < end <= window_end
            for window_start, window_end in reviewed_windows(page)
        )

    def trim_span(page: int, start: int, end: int) -> tuple[int, int]:
        raw = page_texts[page - 1].encode("utf-8")
        while start < end and raw[start : start + 1] in b" \t\r\n":
            start += 1
        while start < end and raw[end - 1 : end] in b" \t\r\n":
            end -= 1
        if not 0 <= start < end <= len(raw):
            raise ValueError(f"invalid reviewed span on page {page}")
        raw[start:end].decode("utf-8", errors="strict")
        return start, end

    def line_span(page: int, first: int, last: int) -> tuple[int, int]:
        lines = page_texts[page - 1].splitlines(keepends=True)
        if not 1 <= first <= last <= len(lines):
            raise ValueError(f"line range drift on page {page}")
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line.encode("utf-8")))
        return trim_span(page, offsets[first - 1], offsets[last])

    specs: dict[tuple[int, int, int, str], dict[str, Any]] = {}

    def add(
        page: int,
        start: int,
        end: int,
        kind: str,
        routes: Sequence[Sequence[str]] = ((),),
        note: str = "Exact source atom retained after whole-page review.",
        *,
        replace_overlap: bool = False,
    ) -> bool:
        start, end = trim_span(page, start, end)
        key = (page, start, end, kind)
        current = specs.get(key)
        if current is not None:
            current["routes"].update(tuple(route) for route in routes)
            return True
        overlaps = [
            existing
            for existing in specs
            if existing[0] == page
            and existing[3] == kind
            and existing[1] < end
            and start < existing[2]
        ]
        if overlaps and not replace_overlap:
            return False
        for existing in overlaps:
            del specs[existing]
        specs[key] = {
            "page": page,
            "start": start,
            "end": end,
            "kind": kind,
            "routes": {tuple(route) for route in routes},
            "note": note,
        }
        return True

    # Source-visible routing is fixed from exact reviewer-selected bytes.  OCR-
    # absent answer labels are never reconstructed.
    flow_defs: list[dict[str, Any]] = []

    def flow(
        symbol: str,
        page: int,
        start: int,
        end: int,
        parents: Sequence[Sequence[str]] = ((),),
        note: str = "Exact source routing atom retained with reviewed ancestry.",
    ) -> None:
        start, end = trim_span(page, start, end)
        flow_defs.append(
            {
                "symbol": symbol,
                "page": page,
                "start": start,
                "end": end,
                "routes": [tuple(route) for route in parents],
                "note": note,
            }
        )

    flow("d_entry_p19", 19, 617, 677)
    flow("e_entry_c2_p19", 19, 1170, 1271)
    flow("e_entry_c3_p19", 19, 1573, 1673)
    flow("d_entry_p21", 21, 656, 719)
    flow("e_entry_c2_p21", 21, 1176, 1285)
    flow("e_entry_c3_p21", 21, 1539, 1554)

    named_flow_spans = {
        (row["page"], row["start"], row["end"]) for row in flow_defs
    }
    for page, spans in FLOW_SPANS.items():
        for start, end in spans:
            if (page, start, end) in named_flow_spans:
                continue
            parents: tuple[tuple[str, ...], ...] = ((),)
            if page == 24 and start in {1776, 1837, 1901}:
                parents = (("reviewed_flow_p24_1708",),)
            if page == 25 and start == 65:
                parents = (("reviewed_flow_p24_1708",),)
            flow(
                f"reviewed_flow_p{page}_{start}",
                page,
                start,
                end,
                parents,
            )

    def append_route_symbol(
        routes: Sequence[Sequence[str]], symbol: str
    ) -> tuple[tuple[str, ...], ...]:
        return tuple((*route, symbol) for route in routes)

    def middle_symbol(page: int, start: int) -> str:
        return f"reviewed_flow_p{page}_{start}"

    # Sections D and E begin at their exact C-section turns.  Later screens
    # are source-visible convergence points: a branch that only skips the
    # immediately intervening question block is no longer an applicable
    # condition after that convergence.  Preserve the section entry and the
    # handful of nested turns whose target remains inside the same screen.
    d_routes = (("d_entry_p19",), ("d_entry_p21",))
    e_routes = (
        ("e_entry_c2_p19",),
        ("e_entry_c3_p19",),
        ("e_entry_c2_p21",),
        ("e_entry_c3_p21",),
    )
    middle_flow_parent_routes: dict[
        tuple[int, int], tuple[tuple[str, ...], ...]
    ] = {
        (75, 2113): append_route_symbol(d_routes, middle_symbol(75, 280)),
        (75, 2533): append_route_symbol(d_routes, middle_symbol(75, 280)),
        (77, 1461): append_route_symbol(d_routes, middle_symbol(77, 869)),
        (79, 1349): append_route_symbol(d_routes, middle_symbol(79, 259)),
        (79, 1408): append_route_symbol(d_routes, middle_symbol(79, 371)),
        (79, 2475): append_route_symbol(
            append_route_symbol(d_routes, middle_symbol(79, 259)),
            middle_symbol(79, 1349),
        ),
    }
    # F1 is the source-visible universal checkpoint that begins the Wife role
    # section after the mutually exclusive Head schedules have completed.
    # It therefore establishes a new route root; its own no-Wife/female-Head
    # exits and the explicit G/H/F turns remain distinct source branches.
    head_to_f_routes = ((),)
    flow("f1_wife_present", 85, 297, 458, head_to_f_routes)
    flow("wife_no_wife_exit", 85, *line_span(85, 10, 12), head_to_f_routes)
    flow("wife_female_head_exit", 85, *line_span(85, 13, 14), head_to_f_routes)
    f1_routes = append_route_symbol(head_to_f_routes, "f1_wife_present")
    f2_other_spans = (
        ("f2_retired", 1085, 1095),
        ("f2_disabled", 1114, 1128),
        ("f2_keeping_house", 1435, 1454),
        ("f2_student", 1463, 1479),
        ("f2_other", 1543, 1561),
    )
    for symbol, start, end in f2_other_spans:
        flow(symbol, 85, start, end, f1_routes)
    f2_other_routes = tuple(
        (*route, symbol)
        for route in f1_routes
        for symbol, _start, _end in f2_other_spans
    )
    flow("g_entry", 85, *line_span(85, 27, 28), f1_routes)
    flow("h_entry_f3", 85, 1812, 1827, f2_other_routes)
    flow("f4_yes", 85, 2224, 2234, f2_other_routes)
    flow("h_entry_f4", 85, 2234, 2669, f2_other_routes)
    f_work_entry_parents = (
        *f1_routes,
        *tuple((*route, "f4_yes") for route in f2_other_routes),
    )
    flow("f_work_entry", 85, *line_span(85, 51, 52), f_work_entry_parents)

    f_routes = tuple(
        (*route, "f_work_entry") for route in f_work_entry_parents
    )
    g_routes = append_route_symbol(f1_routes, "g_entry")
    h_routes = (
        *tuple((*route, "h_entry_f3") for route in f2_other_routes),
        *tuple((*route, "h_entry_f4") for route in f2_other_routes),
    )

    # F, G, and H likewise use their universal section checkpoints as
    # convergence roots.  Nested labels are attached below when their printed
    # target remains inside the same screen; all other retained turns inherit
    # the complete section-entry family selected above.
    middle_flow_parent_routes.update(
        {
            (89, 1718): f_routes,
            (89, 1802): f_routes,
            (93, 663): f_routes,
            (93, 685): f_routes,
            (93, 718): f_routes,
            (93, 801): f_routes,
            (93, 1921): f_routes,
            (93, 1943): f_routes,
            (93, 1975): f_routes,
            (93, 2055): f_routes,
            (97, 679): f_routes,
            (97, 749): f_routes,
            (97, 814): f_routes,
            (107, 234): g_routes,
            (107, 470): g_routes,
            (111, 1461): append_route_symbol(
                g_routes, middle_symbol(111, 899)
            ),
            (113, 1055): h_routes,
            (113, 1815): h_routes,
        }
    )
    for page, spans in MIDDLE_FLOW_SPANS.items():
        if 67 <= page <= 80:
            parents = d_routes
        elif 81 <= page <= 84:
            parents = e_routes
        elif 88 <= page <= 102:
            parents = f_routes
        elif 103 <= page <= 112:
            parents = g_routes
        else:
            parents = h_routes
        for start, end in spans:
            parents = middle_flow_parent_routes.get((page, start), parents)
            flow(
                f"reviewed_flow_p{page}_{start}",
                page,
                start,
                end,
                parents,
            )

    # Section J is out of R_Q anchor scope but its printed route alternatives
    # are retained so the later Section K paths do not restart at root.
    flow("j1_wife_present", 117, 505, 746)
    flow("j1_no_wife", 117, 747, 916)
    flow("j1_female_head", 117, 918, 999)
    flow("j4_head_wife_only", 117, 1688, 1833)
    flow("j4_other_member", 117, 1835, 1977)
    flow("j5_no_to_j8", 117, 2069, 2245, (("j4_other_member",),))
    flow("j8_to_j9", 119, 176, 179)
    flow("j8_to_j16", 119, 231, 235)
    flow("j11_no_to_j13", 119, 1531, 1541, (("j8_to_j9",),))
    flow("j17_no_to_j19", 119, 1590, 1600, (("j8_to_j16",),))
    flow("j13_no_to_j15", 119, 2773, 2918, (("j8_to_j9",),))
    flow(
        "j15_to_j20",
        119,
        3680,
        3720,
        (("j8_to_j9",), ("j8_to_j9", "j13_no_to_j15")),
    )
    j_column_routes = (("j8_to_j9",), ("j8_to_j16",))
    flow("j20_skip_to_k", 121, 245, 324, j_column_routes)
    flow("j23_less_than_12_months", 121, 671, 754, j_column_routes)
    flow("j23_all_12_months_to_k", 121, 756, 1024, j_column_routes)
    j_to_k_routes = (
        ("j8_to_j9", "j20_skip_to_k"),
        ("j8_to_j16", "j20_skip_to_k"),
        ("j8_to_j9", "j23_less_than_12_months"),
        ("j8_to_j16", "j23_less_than_12_months"),
        ("j8_to_j9", "j23_all_12_months_to_k"),
        ("j8_to_j16", "j23_all_12_months_to_k"),
    )

    # The clean Section K copy and marked copy are distinct source witnesses.
    flow("k1_p123_farm_yes", 123, 330, 383, j_to_k_routes)
    flow("k1_p123_farm_no", 123, 582, 656, j_to_k_routes)
    k1_p123_routes = (
        *tuple((*route, "k1_p123_farm_yes") for route in j_to_k_routes),
        *tuple((*route, "k1_p123_farm_no") for route in j_to_k_routes),
    )
    k1_p123_yes_routes = tuple(
        (*route, "k1_p123_farm_yes") for route in j_to_k_routes
    )
    flow("k8_p123_yes", 123, 1803, 1809, k1_p123_routes)
    flow("k8_p123_no", 123, 1952, 1984, k1_p123_routes)
    k8_p123_routes = (
        *tuple((*route, "k8_p123_yes") for route in k1_p123_routes),
        *tuple((*route, "k8_p123_no") for route in k1_p123_routes),
    )
    flow("k9_p123_corporation", 123, 2183, 2197, k8_p123_routes)
    flow("k9_p123_unincorporated", 123, 2210, 2227, k8_p123_routes)
    k9_p123_corporation_routes = tuple(
        (*route, "k9_p123_corporation") for route in k8_p123_routes
    )
    k9_p123_unincorporated_routes = tuple(
        (*route, "k9_p123_unincorporated") for route in k8_p123_routes
    )
    flow(
        "k9_p123_corporation_to_k11",
        123,
        2243,
        2261,
        k9_p123_corporation_routes,
    )

    # Section K's farm/business grid exposes each printed branch explicitly.
    flow("k1_farm_yes", 125, 402, 438, j_to_k_routes)
    flow("k1_farm_no", 125, 593, 652, j_to_k_routes)
    k1_routes = (
        *tuple((*route, "k1_farm_yes") for route in j_to_k_routes),
        *tuple((*route, "k1_farm_no") for route in j_to_k_routes),
    )
    k1_yes_routes = tuple((*route, "k1_farm_yes") for route in j_to_k_routes)
    flow("k8_yes", 125, 2000, 2006, k1_routes)
    flow("k8_no", 125, 2201, 2245, k1_routes)
    k8_merge_routes = (
        *tuple((*route, "k8_yes") for route in k1_routes),
        *tuple((*route, "k8_no") for route in k1_routes),
    )
    flow("k9_corporation", 125, 2602, 2613, k8_merge_routes)
    flow("k9_unincorporated", 125, 2625, 2639, k8_merge_routes)
    k9_corporation_routes = tuple(
        (*route, "k9_corporation") for route in k8_merge_routes
    )
    k9_unincorporated_routes = tuple(
        (*route, "k9_unincorporated") for route in k8_merge_routes
    )
    flow("k9_corporation_to_k11", 125, 2664, 2682, k9_corporation_routes)
    k11_symbol_routes = (
        *tuple(
            (*route, "k9_p123_corporation_to_k11")
            for route in k9_p123_corporation_routes
        ),
        *k9_p123_unincorporated_routes,
        *tuple(
            (*route, "k9_corporation_to_k11")
            for route in k9_corporation_routes
        ),
        *k9_unincorporated_routes,
    )
    flow("k12_to_k16_p127", 127, 872, 881, k11_symbol_routes)
    k16_entry_p127_routes = (
        *k11_symbol_routes,
        *tuple((*route, "k12_to_k16_p127") for route in k11_symbol_routes),
    )
    flow("k16_each_yes_p127", 127, 1495, 1542, k16_entry_p127_routes)
    k16_yes_p127_routes = tuple(
        (*route, "k16_each_yes_p127") for route in k16_entry_p127_routes
    )
    flow("k12_to_k16_p129", 129, 1490, 1499, k11_symbol_routes)
    k16_entry_p129_routes = (
        *k11_symbol_routes,
        *tuple((*route, "k12_to_k16_p129") for route in k11_symbol_routes),
    )
    flow("k16_each_yes_p129", 129, 2122, 2172, k16_entry_p129_routes)
    k16_yes_p129_routes = tuple(
        (*route, "k16_each_yes_p129") for route in k16_entry_p129_routes
    )

    # Wife-income checkpoint and its two terminal outcomes.
    flow("k47_wife_present", 141, 499, 670)
    flow("k47_no_wife_exit", 141, 688, 763)
    flow("k47_female_head_exit", 141, 781, 821)
    flow("k48_no_income_exit", 141, 1331, 1355, (("k47_wife_present",),))
    flow("k49_no", 141, 1426, 1436, (("k47_wife_present",),))

    # Background routes retain only the source-visible checkpoint outcomes
    # needed to establish ancestry for the lifetime-work prompts.
    flow("new_wife_entry", 173, 272, 449)
    flow("new_wife_female_head_exit", 173, 450, 528)
    flow("new_wife_no_wife_exit", 173, 529, 704)
    flow("new_wife_same_wife_exit", 173, 706, 792)
    flow("l10_none_exit", 175, 183, 251, (("new_wife_entry",),))
    flow("l11_all_exit", 175, 372, 447, (("new_wife_entry",),))
    flow("new_head_entry", 177, *line_span(177, 8, 10))
    flow("same_head_exit", 177, *line_span(177, 11, 11))
    flow("never_worked_exit", 177, 2530, 2898, (("new_head_entry",),))
    flow("m17_yes_to_m19", 181, 345, 365, (("new_head_entry",),))
    m17_merge_routes = (
        ("new_head_entry",),
        ("new_head_entry", "m17_yes_to_m19"),
    )
    flow("m25_none_exit", 181, 1319, 1386, m17_merge_routes)
    flow("m26_all_exit", 181, 1526, 1585, m17_merge_routes)

    flow_defs.sort(
        key=lambda row: (row["page"], row["start"], row["end"], row["symbol"])
    )
    flow_by_symbol = {row["symbol"]: row for row in flow_defs}
    if len(flow_by_symbol) != len(flow_defs):
        raise ValueError("duplicate flow symbol")

    resolved_flow_paths: dict[str, tuple[tuple[str, ...], ...]] = {}
    resolved_flow_path_sets: dict[str, frozenset[tuple[str, ...]]] = {}
    branch_ref_cache: dict[tuple[str, tuple[str, ...]], str] = {}

    def resolved_branch_ref(symbol: str, prefix: tuple[str, ...]) -> str:
        key = (symbol, prefix)
        cached = branch_ref_cache.get(key)
        if cached is not None:
            return cached
        parent = flow_by_symbol[symbol]
        value = annotation._review_branch_ref(
            parent["review_id"], prefix, len(resolved_flow_paths[symbol])
        )
        branch_ref_cache[key] = value
        return value

    for row in flow_defs:
        review_occurrence_id = _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            F,
        )
        row["review_id"] = review_occurrence_id
        resolved: list[tuple[str, ...]] = []
        for symbolic_route in row["routes"]:
            prefix: tuple[str, ...] = ()
            for symbol in symbolic_route:
                if prefix not in resolved_flow_path_sets[symbol]:
                    raise ValueError(
                        f"flow ancestry for {row['symbol']} cannot resolve {symbol}"
                    )
                prefix = (*prefix, resolved_branch_ref(symbol, prefix))
            resolved.append(prefix)
        resolved_flow_paths[row["symbol"]] = tuple(resolved)
        resolved_flow_path_sets[row["symbol"]] = frozenset(resolved)

    resolved_route_cache: dict[tuple[str, ...], tuple[str, ...]] = {}

    def resolve_route(route: Sequence[str]) -> tuple[str, ...]:
        symbolic_route = tuple(route)
        cached = resolved_route_cache.get(symbolic_route)
        if cached is not None:
            return cached
        prefix: tuple[str, ...] = ()
        for symbol in symbolic_route:
            if prefix not in resolved_flow_path_sets[symbol]:
                raise ValueError(f"nonflow route cannot resolve {symbol}")
            prefix = (*prefix, resolved_branch_ref(symbol, prefix))
        resolved_route_cache[symbolic_route] = prefix
        return prefix

    def resolve_routes(routes: Sequence[Sequence[str]]) -> list[list[str]]:
        return [list(resolve_route(route)) for route in routes]

    for row in flow_defs:
        add(
            row["page"],
            row["start"],
            row["end"],
            F,
            row["routes"],
            row["note"],
            replace_overlap=True,
        )

    new_wife_routes = (("new_wife_entry",),)
    new_head_routes = (("new_head_entry",),)
    k11_routes = k11_symbol_routes

    def source_routes(
        page: int, start: int, _end: int, _kind: str
    ) -> tuple[tuple[str, ...], ...]:
        if 67 <= page <= 80:
            return d_routes
        if 81 <= page <= 84:
            return e_routes
        if 88 <= page <= 102:
            return f_routes
        if 103 <= page <= 112:
            return g_routes
        if 113 <= page <= 115:
            return h_routes
        if page == 123:
            if start < 756:
                return j_to_k_routes
            if 756 <= start < 1222:
                return k1_p123_yes_routes
            if 1222 <= start < 2042:
                return k1_p123_routes
            if 2042 <= start < 2263:
                return k8_p123_routes
            if start >= 2263:
                return k9_p123_unincorporated_routes
        if page == 124:
            return k1_p123_yes_routes
        if page == 125:
            if start < 806:
                return j_to_k_routes
            if 806 <= start < 1387:
                return k1_yes_routes
            if 1387 <= start < 2245:
                return k1_routes
            if 2245 <= start < 2696:
                return k8_merge_routes
            if start >= 2696:
                return k9_unincorporated_routes
        if page == 126:
            if start < 744:
                return k1_routes
            if start < 1037:
                return k8_merge_routes
            return k9_unincorporated_routes
        if page == 127:
            if 1302 <= start < 1495:
                return k16_entry_p127_routes
            if start == 1495 or start >= 1542:
                return k16_yes_p127_routes
            return k11_routes
        if page == 129:
            if 1932 <= start < 2122:
                return k16_entry_p129_routes
            if start == 2122 or start >= 2172:
                return k16_yes_p129_routes
            return k11_routes
        if page in {128, 130, 131, 132, 133}:
            return k11_routes
        if page in {141, 142}:
            return (("k47_wife_present",),)
        if page in {175, 176}:
            return new_wife_routes
        if page in {177, 178} and start >= 515:
            return new_head_routes
        if page == 181:
            if start >= 1219:
                return (
                    ("new_head_entry",),
                    ("new_head_entry", "m17_yes_to_m19"),
                )
            return new_head_routes
        if page == 182:
            if start >= 1400:
                return (
                    ("new_head_entry",),
                    ("new_head_entry", "m17_yes_to_m19"),
                )
            return new_head_routes
        return ((),)

    def allowed_kinds(page: int) -> frozenset[str]:
        if page in FLOW_ONLY_PAGES:
            return frozenset({F})
        if page in HEAD_EMPLOYMENT_PAGES or page in WIFE_EMPLOYMENT_PAGES:
            return EMPLOYMENT_KINDS
        if page in WORK_INCOME_PAGES:
            return INCOME_KINDS
        if page in WORK_HISTORY_PAGES:
            return HISTORY_KINDS
        return ROLE_ONLY_KINDS

    def singleton_printed_identifier(page: int, start: int) -> str | None:
        identifier = annotation._source_printed_identifier(
            page_texts[page - 1], start
        )
        if identifier is None or "-" in identifier:
            return None
        return identifier

    def in_relevant_window(
        page: int,
        start: int,
        end: int,
        kind: str,
        text: str,
        row: dict[str, Any] | None = None,
    ) -> bool:
        if page not in SEMANTIC_PAGES or kind not in allowed_kinds(page):
            return False
        if not inside_reviewed_window(page, start, end):
            return False
        folded = " ".join(text.upper().split())

        if kind == F:
            if (
                page in FLOW_SPANS
                or page in MIDDLE_FLOW_REVIEWED_PAGES
                or page in LATE_FLOW_REVIEWED_PAGES
            ):
                return False
            if any(marker in folded for marker in FLOW_EXCLUSION_MARKERS):
                return False
            return any(marker in folded for marker in FLOW_ACTION_MARKERS)

        if kind == P:
            if page in PURPOSE_SPANS:
                return False
            identifier = singleton_printed_identifier(page, start)
            if identifier is None:
                return False
            if (
                65 <= page <= 124
                and identifier not in PURPOSE_IDENTIFIER_ALLOWLIST
            ):
                return False
            if page in QBYQ_PAGES:
                return (
                    row is not None
                    and "purpose_identifier_line_v1"
                    in row["detector_rule_ids"]
                )
            return not any(
                marker in folded
                for marker in (
                    "INTERVIEWER CHECKPOINT",
                    "THIS IS A BLANK PAGE",
                    "CONVERSION TABLE",
                    "EXACT TIME NOW",
                    "FOR OFFICE USE ONLY",
                )
            )

        if kind == A:
            if 19 <= page <= 124 or page in LATE_REPEAT_REVIEWED_PAGES:
                return False
            return any(
                marker in folded
                for marker in (
                    "REPEAT",
                    "AGAIN",
                    "SAME JOB",
                    "SAME EMPLOYER",
                    "SEE C",
                    "SEE D",
                    "SEE E",
                    "SEE F",
                    "SEE G",
                    "SEE H",
                    "SEE K",
                    "REFER TO C",
                    "REFER TO D",
                    "REFER TO F",
                    "REFER TO G",
                    "WORK HISTORY SUPPLEMENT",
                )
            )

        if kind == J:
            if page in WORK_INCOME_PAGES and page not in INCOME_JOB_PAGES:
                return False
            if page in ROLE_ONLY_PAGES:
                return False
            if page in QBYQ_PAGES:
                printed = singleton_printed_identifier(page, start)
                bare = folded.strip(" .,;:?!()[]{}\"'") in {
                    "JOB",
                    "JOBS",
                    "EMPLOYER",
                    "EMPLOYERS",
                    "POSITION",
                    "POSITIONS",
                    "OCCUPATION",
                    "OCCUPATIONS",
                }
                if printed is None and bare:
                    return False

        if kind == M and (page, start, end) in REMUNERATION_EXCLUDED_SPANS:
            return False
        if kind == M and page == 124:
            return (start, end) in {
                (900, 908),
                (1660, 1678),
                (2296, 2304),
                (2331, 2349),
            }

        if kind == FA:
            if (page, start, end) == (125, 619, 625):
                return False
            if page == 124:
                return (start, end) in {
                    (933, 940),
                    (1655, 1659),
                    (2271, 2275),
                }
            return page in FARM_INCOME_PAGES and any(
                marker in folded
                for marker in (
                    "FARM",
                    "FARMING",
                    "FARM INCOME",
                    "MARKET GARDEN",
                )
            )
        if kind == BA:
            return page in BUSINESS_INCOME_PAGES and any(
                marker in folded
                for marker in (
                    "BUSINESS",
                    "SELF-EMPLOY",
                    "UNINCORPORATED",
                    "PROFESSIONAL PRACTICE",
                )
            )
        if kind == T:
            return page in ROLE_TOTAL_PAGES and any(
                marker in folded
                for marker in (
                    "TOTAL",
                    "ALTOGETHER",
                    "ALL JOB",
                    "COMBINED",
                    "AMOUNTS WE JUST",
                )
            )

        if kind == C and page in WORK_INCOME_PAGES:
            return any(
                marker in folded
                for marker in (
                    "WORK",
                    "JOB",
                    "EMPLOY",
                    "HOURS",
                    "WEEKS",
                    "BUSINESS",
                    "FARM",
                    "RETIRE",
                    "PENSION",
                )
            )

        return True

    # Composite Wife/quoted-Wife labels are one exact printed role atom.
    composite_role_ranges: dict[int, list[tuple[int, int]]] = {}
    for page in sorted(SEMANTIC_PAGES):
        page_text = page_texts[page - 1]
        offsets = annotation.stage1_candidates._utf8_offsets(page_text)
        for match in COMPOSITE_WIFE_RE.finditer(page_text):
            start = offsets[match.start()]
            end = offsets[match.end()]
            if not in_relevant_window(page, start, end, R, match.group()):
                continue
            composite_role_ranges.setdefault(page, []).append((start, end))
            add(
                page,
                start,
                end,
                R,
                source_routes(page, start, end, R),
                "Composite Wife/quoted-Wife role independently re-sliced as one source atom.",
            )

    # Candidate-free lexical enumeration over authenticated page bytes.
    for page, page_text in enumerate(page_texts, start=1):
        detected, _line_count = (
            annotation.stage1_candidates.detect_page_candidates(
                page_text,
                source_document_id=source_document_id,
                interview_wave=interview_wave,
                page_number=page,
            )
        )
        for row in detected:
            kind = row["occurrence_kind_candidate"]
            start = row["utf8_byte_start"]
            end = row["utf8_byte_end"]
            if kind == R and any(
                left < end and start < right
                for left, right in composite_role_ranges.get(page, ())
            ):
                continue
            if not in_relevant_window(
                page,
                start,
                end,
                kind,
                row["matched_text"],
                row,
            ):
                continue
            if kind == F and any(
                ep == page and ek == F and es < end and start < ee
                for ep, es, ee, ek in specs
            ):
                continue
            add(
                page,
                start,
                end,
                kind,
                source_routes(page, start, end, kind),
                "Reviewer-approved atom independently re-derived from exact page bytes.",
            )

    # Reconstruct identifier-bearing purpose blocks on the employment pages.
    # The range grammar is used only as a boundary: composite objectives such
    # as D20-D39 never become one-to-one field purposes.
    for page in sorted(
        (HEAD_EMPLOYMENT_PAGES | WIFE_EMPLOYMENT_PAGES)
        & frozenset(range(67, 116))
    ):
        page_text = page_texts[page - 1]
        offsets = annotation.stage1_candidates._utf8_offsets(page_text)
        identifier_matches = list(
            FIELD_BLOCK_IDENTIFIER_RE.finditer(page_text)
        )
        for position, match in enumerate(identifier_matches):
            identifier = normalized_field_identifier(match, page)
            if identifier not in PURPOSE_IDENTIFIER_ALLOWLIST:
                continue
            line_start = page_text.rfind("\n", 0, match.start()) + 1
            prefix = page_text[line_start : match.start()]
            trailing_space_count = len(prefix) - len(prefix.rstrip())
            if prefix.rstrip().endswith("-"):
                continue
            if (
                prefix.strip()
                and len(prefix) > 20
                and trailing_space_count < 3
            ):
                continue
            start = offsets[match.start(1)]
            containing_window = next(
                (
                    window
                    for window in reviewed_windows(page)
                    if window[0] <= start < window[1]
                ),
                None,
            )
            if containing_window is None:
                continue
            next_char_start = (
                identifier_matches[position + 1].start(1)
                if position + 1 < len(identifier_matches)
                else len(page_text)
            )
            search_end = min(next_char_start, match.start(1) + 700)
            question_mark = page_text.find("?", match.start(1), search_end)
            end_char = (
                question_mark + 1
                if question_mark >= 0
                else min(next_char_start, match.start(1) + 500)
            )
            end = min(offsets[end_char], containing_window[1])
            if start >= end:
                continue
            add(
                page,
                start,
                end,
                P,
                source_routes(page, start, end, P),
                "Complete source-visible singleton purpose block independently re-sliced from exact bytes.",
                replace_overlap=True,
            )

    for page, spans in MIDDLE_MANUAL_PURPOSE_SPANS.items():
        for start, end, _identifier in spans:
            add(
                page,
                start,
                end,
                P,
                source_routes(page, start, end, P),
                "Complete source-visible purpose block independently re-sliced from exact bytes; source label bytes are unnormalized.",
                replace_overlap=True,
            )

    # Replace line-level purpose/context candidates with the exact reviewed
    # semantic blocks.  These are source-byte decisions, not candidate joins.
    for page, spans in PURPOSE_SPANS.items():
        for start, end in spans:
            add(
                page,
                start,
                end,
                P,
                source_routes(page, start, end, P),
                "Complete field-purpose block independently sliced from source bytes.",
                replace_overlap=True,
            )
    for page, spans in CONTEXT_SPANS.items():
        for start, end in spans:
            add(
                page,
                start,
                end,
                C,
                source_routes(page, start, end, C),
                "Complete source-context block independently sliced from source bytes.",
                replace_overlap=True,
            )

    for span_table in (REPEAT_SPANS, MIDDLE_REPEAT_SPANS, LATE_REPEAT_SPANS):
        for page, spans in span_table.items():
            for start, end in spans:
                add(
                    page,
                    start,
                    end,
                    A,
                    source_routes(page, start, end, A),
                    "Explicit repeat/cross-reference instruction independently sliced from source bytes.",
                    replace_overlap=True,
                )

    for page, start, end in MANUAL_ROLE_SPANS:
        add(
            page,
            start,
            end,
            R,
            source_routes(page, start, end, R),
            "Composite or corrected role label independently re-sliced from source bytes.",
            replace_overlap=True,
        )
    for page, start, end in MANUAL_JOB_SPANS:
        add(
            page,
            start,
            end,
            J,
            source_routes(page, start, end, J),
            "Complete job anchor independently re-sliced from source bytes.",
            replace_overlap=True,
        )
    for page, start, end in MANUAL_REMUNERATION_SPANS:
        add(
            page,
            start,
            end,
            M,
            source_routes(page, start, end, M),
            "Complete remuneration anchor independently re-sliced from source bytes.",
            replace_overlap=True,
        )
    for page, start, end in MANUAL_TOTAL_SPANS:
        add(
            page,
            start,
            end,
            T,
            source_routes(page, start, end, T),
            "Complete role-total anchor independently re-sliced from source bytes.",
            replace_overlap=True,
        )
    for page, start, end, kind in MANUAL_AGGREGATE_SPANS:
        add(
            page,
            start,
            end,
            kind,
            source_routes(page, start, end, kind),
            "Complete aggregate anchor independently re-sliced from source bytes.",
            replace_overlap=True,
        )

    # Recover a narrow set of exact remuneration phrases outside the fixed
    # lexical grammar.
    for page in sorted(
        HEAD_EMPLOYMENT_PAGES | WIFE_EMPLOYMENT_PAGES | WORK_INCOME_PAGES
    ):
        page_text = page_texts[page - 1]
        offsets = annotation.stage1_candidates._utf8_offsets(page_text)
        for match in MANUAL_REMUNERATION_RE.finditer(page_text):
            start = offsets[match.start()]
            end = offsets[match.end()]
            if not in_relevant_window(page, start, end, M, match.group()):
                continue
            add(
                page,
                start,
                end,
                M,
                source_routes(page, start, end, M),
                "Source-explicit remuneration phrase manually recovered from exact bytes.",
            )

    ordered_specs = sorted(
        specs.values(),
        key=lambda item: (
            item["page"],
            item["start"],
            item["end"],
            annotation.KIND_ORDER[item["kind"]],
        ),
    )
    occurrence_specs: list[dict[str, Any]] = []
    for item in ordered_specs:
        occurrence_specs.append(
            {
                "review_occurrence_id": _review_id(
                    source_document_id,
                    page_texts,
                    item["page"],
                    item["start"],
                    item["end"],
                    item["kind"],
                ),
                "page_number": item["page"],
                "utf8_byte_start": item["start"],
                "utf8_byte_end": item["end"],
                "occurrence_kind": item["kind"],
                "parent_review_branch_paths": resolve_routes(
                    sorted(item["routes"])
                ),
                "review_note": item["note"],
            }
        )

    occurrence_by_review_id = {
        spec["review_occurrence_id"]: spec for spec in occurrence_specs
    }
    parent_anchor_specs = [
        spec
        for spec in occurrence_specs
        if spec["occurrence_kind"] in {J, T, FA, BA}
    ]

    def branch_compatible(
        source: dict[str, Any], parent: dict[str, Any]
    ) -> bool:
        return any(
            left[: min(len(left), len(right))]
            == right[: min(len(left), len(right))]
            for left in source["parent_review_branch_paths"]
            for right in parent["parent_review_branch_paths"]
        )

    local_anchor_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        kind = spec["occurrence_kind"]
        if kind not in annotation.ANCHOR_KINDS:
            continue
        page = spec["page_number"]
        label = (
            page_texts[page - 1]
            .encode("utf-8")[spec["utf8_byte_start"] : spec["utf8_byte_end"]]
            .decode("utf-8", errors="strict")
        )
        if kind == R:
            node_domain = "role"
            classification = annotation.stage1_candidates._role_classification(
                label
            )
        else:
            node_domain, classification = annotation.ANCHOR_CLASSIFICATION[
                kind
            ]
        parent_ids: list[str] = []
        if kind in {M, C}:
            compatible = [
                parent
                for parent in parent_anchor_specs
                if parent["page_number"] == page
                and branch_compatible(spec, parent)
            ]
            nested = [
                parent
                for parent in compatible
                if spec["utf8_byte_start"]
                <= parent["utf8_byte_start"]
                < parent["utf8_byte_end"]
                <= spec["utf8_byte_end"]
            ]
            if nested:
                selected = nested
            else:
                # Proximity and source order do not prove a parent.  Preserve
                # unresolved local attachment unless the exact reviewed block
                # physically contains the parent anchor.
                selected = []
            parent_ids = [
                parent["review_occurrence_id"] for parent in selected
            ]
            parent_ids.sort(
                key=lambda review_id: occurrence_specs.index(
                    occurrence_by_review_id[review_id]
                )
            )
        parent_note = (
            "Explicit source-local parent anchors were verified from the same source block."
            if parent_ids
            else (
                "Whole-page review found general or no-job context and asserted no "
                "unambiguous document-local parent anchor."
                if kind in {M, C}
                else "Parent resolution is not applicable to this non-component anchor."
            )
        )
        local_anchor_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "node_domain": node_domain,
                "classification": classification,
                "printed_identifier": annotation._source_printed_identifier(
                    page_texts[page - 1], spec["utf8_byte_start"]
                ),
                "parent_review_occurrence_ids": parent_ids,
                "parent_resolution_note": parent_note,
                "classification_status": "provisional_document_local",
            }
        )

    occurrence_order = {
        spec["review_occurrence_id"]: position
        for position, spec in enumerate(occurrence_specs)
    }
    repeat_alias_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        if spec["occurrence_kind"] != A:
            continue
        raw = page_texts[spec["page_number"] - 1].encode("utf-8")[
            spec["utf8_byte_start"] : spec["utf8_byte_end"]
        ]
        folded = raw.decode("utf-8", errors="strict").casefold()
        relation = (
            "explicit_repeat_instruction"
            if any(
                marker in folded
                for marker in (
                    "repeat",
                    "again",
                    "same job",
                    "same employer",
                    "for each",
                )
            )
            else "explicit_cross_reference"
        )
        evidence = [spec["review_occurrence_id"]]
        evidence.sort(key=occurrence_order.__getitem__)
        repeat_alias_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "relation": relation,
                "alias_anchor_review_occurrence_ids": [],
                "canonical_anchor_review_occurrence_ids": [],
                "evidence_review_occurrence_ids": evidence,
                "target_scope": "unresolved",
                "resolution_status": "preserved_for_global_resolution",
            }
        )

    counts_by_page = Counter(spec["page_number"] for spec in occurrence_specs)
    page_review_rows = [
        {
            "page_number": page_number,
            "page_text_utf8_sha256": annotation._sha256(
                page_text.encode("utf-8")
            ),
            "whole_page_review_complete": True,
            "review_status": "complete",
            "review_note": (
                "Whole page reviewed against exact source bytes; "
                f"{counts_by_page[page_number]} source occurrence atoms retained."
            ),
        }
        for page_number, page_text in enumerate(page_texts, start=1)
    ]
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
            "whole_page_review": "all_184_pages_including_empty_occurrence_pages",
            "span_granularity": "exact_utf8_lexeme_physical_line_or_source_block",
            "candidate_nonselection": "candidates_joined_only_after_source_rows_complete",
            "global_ids_assigned": False,
        },
        "page_review_rows": page_review_rows,
        "occurrence_specs": occurrence_specs,
        "local_anchor_specs": local_anchor_specs,
        "repeat_alias_specs": repeat_alias_specs,
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
    review = author_review()
    annotation._write_or_check(
        annotation.REVIEW_PATH, annotation._canonical_bytes(review), args.check
    )
    counts = Counter(
        row["occurrence_kind"] for row in review["occurrence_specs"]
    )
    print(
        f"{'checked' if args.check else 'wrote'} "
        f"{annotation.REVIEW_PATH.relative_to(ROOT)}: "
        f"{len(review['occurrence_specs'])} occurrences {dict(counts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
