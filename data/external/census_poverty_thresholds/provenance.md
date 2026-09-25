# Census poverty thresholds, income years 2003-2022

The twenty U.S. Census Bureau workbooks `thresh03.xlsx` ... `thresh22.xlsx`,
from
`https://www2.census.gov/programs-surveys/cps/tables/time-series/historical-poverty-thresholds/`
(the file names the Census historical poverty thresholds page lists),
committed unchanged. The orchestrating Claude Code session fetched them
with `curl` from that address into `~/PolicyEngine/census-poverty-thresholds`
after Max approved each download in cos: `thresh03.xlsx` ...
`thresh12.xlsx` on 2026-09-24 under decision d194 (exercise 2, Track U),
and `thresh13.xlsx` ... `thresh22.xlsx` on 2026-09-25 under decision d279
(exercise 4, Track M). Max ruled on the downloads; he did not make them.
That session also wrote the directory's `SHA256SUMS`, which lists the same
twenty digests. Each file's SHA-256 is pinned in
`scripts/capture_track_u_parameters.py` (`CENSUS_WORKBOOK_SHA256`), which
refuses any other bytes before parsing.

| File | Bytes | SHA-256 | Staged under |
|---|---:|---|---|
| `thresh03.xlsx` | 12,179 | `f91f2a70062c52b21391e74dc0486bf9adc898c8c923212ecaa7db7a0db24895` | d194 (2026-09-24) |
| `thresh04.xlsx` | 12,163 | `9cae1bcff6c3ff80faedaa11c28068d9a640f10f5a7679e3cfb0430779bbb5b8` | d194 (2026-09-24) |
| `thresh05.xlsx` | 12,183 | `9c626a9757232d500167349c9c47dc254a5f1ac34c6ba3468acd1a624df52888` | d194 (2026-09-24) |
| `thresh06.xlsx` | 12,153 | `7ace9e1c3990348b252698da9026aea082c7a52bcc073c0315721b01b9c09a45` | d194 (2026-09-24) |
| `thresh07.xlsx` | 11,031 | `1209903a9c1071f9a76ee5a50dc9eb83faa93024134a72e73a3cdc6b558a4327` | d194 (2026-09-24) |
| `thresh08.xlsx` | 12,295 | `7e7222d431411aa82734d9580cc8f6bce246d1cd330e688a8306748bc46f09ae` | d194 (2026-09-24) |
| `thresh09.xlsx` | 13,612 | `7f997506d189bb1899bab1255ae5e991a384ffaf8d72d63ca4497d1912e1175e` | d194 (2026-09-24) |
| `thresh10.xlsx` | 13,592 | `75360b3d852669c76f77df20d2292d1abe1d90e1b58a9d3e0611bb37570a45b9` | d194 (2026-09-24) |
| `thresh11.xlsx` | 13,644 | `ec2758efc4b6797b171fbe4cda135e5f08396734bdc2d606f0b990219f42bab6` | d194 (2026-09-24) |
| `thresh12.xlsx` | 13,692 | `26da2dc48de0a0799905c15aa6634d5b942dd57b801bdaf9564eacf4cc365f36` | d194 (2026-09-24) |
| `thresh13.xlsx` | 11,833 | `4114b7a98043842fc6ec9cc688d6918ce1461f84ed5fc96ffe0c8a3076083f2b` | d279 (2026-09-25) |
| `thresh14.xlsx` | 21,121 | `c9fad68272d238036bf01e24ea33c1de97f71c6d56b310276f173b5b21153ce8` | d279 (2026-09-25) |
| `thresh15.xlsx` | 22,863 | `9658e7c7fa63fe25a396f1abfcc9c90db385edbeb19ffdabf5e6d14eaf650e41` | d279 (2026-09-25) |
| `thresh16.xlsx` | 14,284 | `5d16803e3904430564b7df980b7968563634a9e0619b96bcbc079b1dcb854e45` | d279 (2026-09-25) |
| `thresh17.xlsx` | 14,293 | `edf7af0544b48cd8de86cfd12d018c5dcc596677cc9f532c070eb18262db3e65` | d279 (2026-09-25) |
| `thresh18.xlsx` | 13,626 | `f1abec2ee137a39e04466ec5cf189412228d2c1e5a2d56fd5195bb90ca6ffa55` | d279 (2026-09-25) |
| `thresh19.xlsx` | 14,999 | `e9252e05ef17d0787243eeadec1228524170211f57ac3b58efe32ee909e8ff57` | d279 (2026-09-25) |
| `thresh20.xlsx` | 13,751 | `5739e473550312b7663479711f41d254b477a7d020d92847cb6164dc506767f8` | d279 (2026-09-25) |
| `thresh21.xlsx` | 13,581 | `9399f4564ed22776f286fbceb72bab288f0cf0c1a70181f3805b3321332734e5` | d279 (2026-09-25) |
| `thresh22.xlsx` | 13,573 | `5874eb8ecc525f5d26daab34b81165416c669daf62771e65ef52847bd3cbf89f` | d279 (2026-09-25) |

Two captures read them, and each reproduces byte for byte:

- `python scripts/capture_track_u_parameters.py --census-dir
  data/external/census_poverty_thresholds` writes
  `data/external/census_poverty_thresholds_2004_2012.json` from the nine
  workbooks 2004-2012 (Track U; SHA-256 pinned as
  `adjusted_poverty.THRESHOLDS_SHA256`). No registered Track U row reads
  income year 2003.
- `python scripts/capture_track_u_parameters.py --track-m-census-dir
  data/external/census_poverty_thresholds` writes
  `data/external/census_poverty_thresholds_2003_2022.json` from all twenty
  (Track M; SHA-256 pinned as
  `min_benefit_track_m.thresholds.TRACK_M_THRESHOLDS_SHA256`). Track M reads
  the weighted average for one person aged 65 and over. See the exercise-4
  specification, `docs/design/minimum_benefits_comparison.md`, section 7.

**Layouts** (every workbook inspected cell by cell, 2026-09-25). All twenty
print one table in the same cells: the caption, title and "(In dollars)"
in A1-A3, the header in rows 5-6, the thirteen labelled rows in rows 8-22,
the source line in A23 and the note in A24, with 91 non-blank cells. Three
differences, each pinned to its year in the capture script:

- `thresh03.xlsx` ... `thresh06.xlsx` name their worksheet after the file
  (`thresh03` ...); the others name it `Sheet1`. The parser does not read
  the worksheet name.
- `thresh19.xlsx` carries two further worksheets, `Sheet2` and `Sheet3`,
  with no cell value (`EMPTY_EXTRA_SHEETS`).
- `thresh22.xlsx` prints every weighted average rounded to $10 (for one
  person 65 and over, 14,040, beside a single matrix cell of 14,036; under
  65, 15,230 beside 15,225), while its matrix cells stay whole dollars
  (`WEIGHTED_AVERAGE_UNIT`).

The 2009 note adds two sentences on the fall in the CPI-U; the parser
accepts them only when they name the table's year and the year before.
