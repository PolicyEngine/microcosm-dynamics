# Census poverty thresholds, income years 2004-2012

The nine U.S. Census Bureau workbooks `thresh04.xlsx` ... `thresh12.xlsx`,
from
`https://www2.census.gov/programs-surveys/cps/tables/time-series/historical-poverty-thresholds/`
(the file names the Census historical poverty thresholds page lists),
staged on 2026-09-24 under cos decision d194 and committed unchanged.
Each file's SHA-256 is pinned in `scripts/capture_track_u_parameters.py`
(`CENSUS_WORKBOOK_SHA256`), which refuses any other bytes before parsing.

| File | Bytes | SHA-256 |
|---|---:|---|
| `thresh04.xlsx` | 12,163 | `9cae1bcff6c3ff80faedaa11c28068d9a640f10f5a7679e3cfb0430779bbb5b8` |
| `thresh05.xlsx` | 12,183 | `9c626a9757232d500167349c9c47dc254a5f1ac34c6ba3468acd1a624df52888` |
| `thresh06.xlsx` | 12,153 | `7ace9e1c3990348b252698da9026aea082c7a52bcc073c0315721b01b9c09a45` |
| `thresh07.xlsx` | 11,031 | `1209903a9c1071f9a76ee5a50dc9eb83faa93024134a72e73a3cdc6b558a4327` |
| `thresh08.xlsx` | 12,295 | `7e7222d431411aa82734d9580cc8f6bce246d1cd330e688a8306748bc46f09ae` |
| `thresh09.xlsx` | 13,612 | `7f997506d189bb1899bab1255ae5e991a384ffaf8d72d63ca4497d1912e1175e` |
| `thresh10.xlsx` | 13,592 | `75360b3d852669c76f77df20d2292d1abe1d90e1b58a9d3e0611bb37570a45b9` |
| `thresh11.xlsx` | 13,644 | `ec2758efc4b6797b171fbe4cda135e5f08396734bdc2d606f0b990219f42bab6` |
| `thresh12.xlsx` | 13,692 | `26da2dc48de0a0799905c15aa6634d5b942dd57b801bdaf9564eacf4cc365f36` |

`python scripts/capture_track_u_parameters.py --census-dir
data/external/census_poverty_thresholds` reproduces
`data/external/census_poverty_thresholds_2004_2012.json` byte for byte
(SHA-256 pinned as `adjusted_poverty.THRESHOLDS_SHA256`). The tenth staged
file, `thresh03.xlsx` (SHA-256
`f91f2a70062c52b21391e74dc0486bf9adc898c8c923212ecaa7db7a0db24895`), was
inspected for its layout only: no registered row reads income year 2003,
so it is not committed. See the exercise-2 specification,
`docs/design/boomers2004_uniform_cut_comparison.md`, section 6.
