# Census poverty thresholds, income years 1982-2022 (35 years)

The thirty-five U.S. Census Bureau workbooks of income years 1982, 1986,
1988, 1989, 1991, 1992 and 1994-2022 (`thresh82.xlsx` ... `thresh22.xlsx`),
from
`https://www2.census.gov/programs-surveys/cps/tables/time-series/historical-poverty-thresholds/`
(the file names the Census historical poverty thresholds page lists),
committed unchanged. The orchestrating Claude Code session fetched
`thresh03.xlsx` ... `thresh22.xlsx` with `curl` from that address into
`~/PolicyEngine/census-poverty-thresholds` after Max approved each download
in cos: `thresh03.xlsx` ... `thresh12.xlsx` on 2026-09-24 under decision
d194 (exercise 2, Track U), and `thresh13.xlsx` ... `thresh22.xlsx` on
2026-09-25 under decision d279 (exercise 4, Track M). Max ruled on the
downloads; he did not make them. That session also wrote the directory's
`SHA256SUMS`.

The fifteen workbooks before 2003 are the years M4's structural count
shows Track M's in-window records need (exercise-4 specification, sections
4, 7 and 10), which d279 covers ("any earlier year the build proves it
needs"). They were staged in the same directory on 2026-09-25, whose
`SHA256SUMS` lists all thirty-five digests; the builder lane that captured
them (2026-09-25) did not fetch them, and the staging record does not name
who did. Fourteen came from the Census address above. `thresh95.xlsx` did
not; the staging directory's `PROVENANCE-thresh95.md` records:

- On 2026-09-25 the Census server answered its URL, and only that one,
  with its WAF page "Request Rejected" (HTTP 200, 247 bytes of HTML), to
  curl with a browser user-agent string (and, in an earlier attempt, to a
  default one).
- The file is the Internet Archive's copy of that URL, fetched raw (`id_`)
  on 2026-09-25 from two captures 3.5 years apart:
  `http://web.archive.org/web/20230226205734id_/https://www2.census.gov/programs-surveys/cps/tables/time-series/historical-poverty-thresholds/thresh95.xlsx`
  (served gzip-encoded; decompressed) and
  `http://web.archive.org/web/20260820215832id_/https://www2.census.gov/programs-surveys/cps/tables/time-series/historical-poverty-thresholds/thresh95.xlsx`.
- The two are byte-identical after decompression (SHA-256
  `32bb678f3e0847b71c96c7c3c2b2ca8151a5c82307466df2807e9438ab2138f8`,
  12,868 bytes), and each matches the SHA-1 digest the Archive's CDX index
  records for it: `ZCDVY76QW2OH6NA6RLKWJPMJCNTMZIAQ` for the 2026 capture
  (the file itself) and `ARBZSSCAOHTKTGHH6INRSDDWBDJVFVAB` for the 2023
  capture (its gzip body as served).
- To do: retry the Census URL when its WAF allows it and confirm the hash.

The capture records this retrieval in `sources["1995"]["retrieval"]`
(`ARCHIVE_RETRIEVALS` in the capture script). Each file's SHA-256 is
pinned in `scripts/capture_track_u_parameters.py` (`CENSUS_WORKBOOK_SHA256`),
which refuses any other bytes before parsing.

| File | Bytes | SHA-256 | Staged under |
|---|---:|---|---|
| `thresh82.xlsx` | 13,934 | `88a5fb3aaba6008e430bce327b862fca03ba85340c32c1375b902dfb60093b78` | d279 (2026-09-25) |
| `thresh86.xlsx` | 12,232 | `49c00638209721b4cf25e4039728255b97874efd54f36ff085860113b2d077b2` | d279 (2026-09-25) |
| `thresh88.xlsx` | 12,194 | `f22fc66ea80677c34bf36d00f9c26aff3038a0f115f90673a1ebd42c7f19fd11` | d279 (2026-09-25) |
| `thresh89.xlsx` | 12,222 | `bed78af3dd2425349f33391163cc76a1218080403eeaa6e7c0de15d359847d73` | d279 (2026-09-25) |
| `thresh91.xlsx` | 12,937 | `a06989525bc712f609fa40cde808ec1cfb5bf8ce1d8194eeb362f2ec7847249c` | d279 (2026-09-25) |
| `thresh92.xlsx` | 12,148 | `ac5262b83d0f63cff97caa5ad8fb80096f8b16db501f79dd88cca19e9b4fd3d5` | d279 (2026-09-25) |
| `thresh94.xlsx` | 12,155 | `593b5a45109ed58ea35648e0f9c6ba749050741e4e935ab69cce9bbc15d38006` | d279 (2026-09-25) |
| `thresh95.xlsx` | 12,868 | `32bb678f3e0847b71c96c7c3c2b2ca8151a5c82307466df2807e9438ab2138f8` | d279 (2026-09-25; Internet Archive copy) |
| `thresh96.xlsx` | 12,142 | `28a0cb77b312f861dd55b51d68cf83452d8a17c93f7b111e1b6da9930e27db78` | d279 (2026-09-25) |
| `thresh97.xlsx` | 12,233 | `aa463ec2d30e7d89a8626cd0ea73caeb15e2351b566e20163625dff0d8389754` | d279 (2026-09-25) |
| `thresh98.xlsx` | 12,151 | `c8ab5b79a49a756952a31c684a961f5da7de8dce46ce60c50128c618618964bb` | d279 (2026-09-25) |
| `thresh99.xlsx` | 12,231 | `a513a440417c603a7db00dbec785cb5c23851bb156bc0bfc4fc28e460a2f3a63` | d279 (2026-09-25) |
| `thresh00.xlsx` | 13,080 | `46a08f5146c5cfdb6cc6c6fb9e2a50deb78e68acbfa5917fbd5bfaa2d211f3bb` | d279 (2026-09-25) |
| `thresh01.xlsx` | 12,122 | `ac7deb00d0feee4fe0ca8124ecb19ef85d87bf11fdc39ac608d078b5bfe468d2` | d279 (2026-09-25) |
| `thresh02.xlsx` | 12,221 | `40609e1d94d2e1972cfbab6904ebee9e03d94686eaf9af54dafe782d4d7f648d` | d279 (2026-09-25) |
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
  `data/external/census_poverty_thresholds_1982_2022.json` from all
  thirty-five (Track M; SHA-256 pinned as
  `min_benefit_track_m.thresholds.TRACK_M_THRESHOLDS_SHA256`). It lists the
  captured years and the years 1983-1985, 1987, 1990 and 1993 it does not
  capture. Track M reads the weighted average for one person aged 65 and
  over. See the exercise-4 specification,
  `docs/design/minimum_benefits_comparison.md`, section 7. It replaced
  `census_poverty_thresholds_2003_2022.json` (SHA-256 `65bbcd83…`) on
  2026-09-25; its 2003-2022 content (weighted averages, all-ages averages,
  matrix, sources and year-pair ratios) is unchanged.

**Layouts** (every workbook inspected cell by cell, 2026-09-25). All
thirty-five print one table in the same cells: the caption, title and "(In dollars)"
in A1-A3, the header in rows 5-6, the thirteen labelled rows in rows 8-22,
the source line in A23 and the note in A24, with 91 non-blank cells (92 in
1982 and 2000, which add a revision line). The differences, each pinned to
its year in the capture script:

- `thresh03.xlsx` ... `thresh06.xlsx` name their worksheet after the file
  (`thresh03` ...); the others name it `Sheet1`. The parser does not read
  the worksheet name.
- `thresh19.xlsx` carries two further worksheets, `Sheet2` and `Sheet3`,
  with no cell value (`EMPTY_EXTRA_SHEETS`).
- `thresh22.xlsx` prints every weighted average rounded to $10 (for one
  person 65 and over, 14,040, beside a single matrix cell of 14,036; under
  65, 15,230 beside 15,225), while its matrix cells stay whole dollars
  (`WEIGHTED_AVERAGE_UNIT`).

- The note names another survey before 2002 (`NOTE_SURVEY_BEFORE_2002`):
  "the March <year + 1> Current Population Survey (CPS)" in 1982-2000 and
  "the 2002 Current Population Survey Annual Demographic Supplement (CPS
  ADS)" in 2001. From 2002 it names the <year + 1> CPS ASEC.
- `thresh01.xlsx` alone labels its size rows "Two persons" ... "Nine
  persons or more" (with dot leaders) where every other year prints
  "people" (`PERSONS_ROW_LABEL_YEARS`).
- `thresh82.xlsx` and `thresh00.xlsx` print one line below the note in
  A25: "Revised on 4/19/2022 due to rounding issues." and "Revised on
  2/1/2023 due to a formatting error." (`REVISION_LINES`). The parser
  accepts exactly that line in that year and nothing below it.
- `thresh88.xlsx`, `thresh94.xlsx` and `thresh98.xlsx` capitalize the
  header "Weighted Average Thresholds", and they and `thresh00.xlsx` print
  "None" without its leading space and "Eight or more" over three lines;
  labels are compared in lower case with whitespace collapsed, so these
  need no exception. `thresh82.xlsx` names its worksheet `Sheet1`; the
  others before 2003 name it after the file.

The 2009 note adds two sentences on the fall in the CPI-U; the parser
accepts them only when they name the table's year and the year before.

**Cross-check** (`crosscheck/hstpov1-20100209011620.html`). Census's own
HTML edition of its historical poverty Table 1, "Weighted Average Poverty
Thresholds for Families of Specified Size[d]: 1959 to 2006" (page last
modified September 29, 2009), is an independent publication of the
weighted averages, including the unrelated individual aged 65 or older,
and of the annual average CPI-U (1982-84 = 100). The current edition,
`hstpov1.xlsx`, is a workbook; it was not downloaded. The committed file is
the Internet Archive's raw copy
`http://web.archive.org/web/20100209011620id_/http://www.census.gov:80/hhes/www/poverty/histpov/hstpov1.html`,
fetched on 2026-09-25 by the builder lane: 22,535 bytes, SHA-256
`d219cb20f4a6978ffabf265e4feabe1ad02b5446705c5cc1bda73cb9c91f038f`, SHA-1
(base 32) `ZHBEEQW5NSNXMGIVCKZGS5ARJKHZS253`, the digest the Archive's CDX
index records for that capture. The capture of 2009-09-01 differs only in
its "Page Last Modified" line. Its footnotes page (capture of 2010-02-21)
says footnote 11/ on 1999 is the Census 2000 population controls, 12/ on
2000 those controls and a sample expanded by 28,000 households, and 14/ on
2004 a correction to the weights of the 2005 ASEC.
`tests/min_benefit_track_m/test_threshold_capture_before_2003.py` checks
every weighted average of the capture against it, 1982-2006, and every
year-pair matrix ratio against its CPI-U.
