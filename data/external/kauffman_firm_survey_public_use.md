# Kauffman Firm Survey public-use microdata

The Kauffman Firm Survey (KFS) is an observed-firm panel of 4,928
anonymized businesses founded in 2004 and followed through 2011. It is
not synthetic data. It is also not a current cross-section of all US
employers and contains neither employee rosters nor observed links to
SIPP or CPS respondents.

Raw files are staged outside this repository and must not be committed
or redistributed without explicit permission. The publisher describes
the files as public-use and permits download, but supplies no explicit
KFS redistribution license.

## Staged input

- Publisher: Ewing Marion Kauffman Foundation
- Landing page: <https://www.kauffman.org/resources/kauffman-firm-survey/>
- Archive: <https://kauffman-firm-survey.s3-us-west-2.amazonaws.com/Logically_Imputed_KFS_Public_Data.zip>
- Retrieved: 2026-07-30
- Archive bytes: 11,118,022
- Archive SHA-256:
  `2428d3197405a2436f49cadd03492057cf8b51fd9f8ee7be9a73d16156136bde`
- Long-file SHA-256:
  `a6042ad2be946b836e4f36a5e04d9d1fe5790387b252c7a256d0dc8a08140f8a`
- Default local long-file path:
  `~/PolicyEngine/kfs-data/logically-imputed/Public_Use_LI_Long.dta`

The archive's workbook and readme document logical imputation, soft and
hard missing values, renamed variables, newly constructed variables,
and conversions of range variables. The project reader deliberately
retains employment ranges as intervals instead of replacing them with
midpoints.

## Permitted project use before IC3 lock

KFS may support descriptive profiling of observed young-firm
trajectories and development of firm-record handling methods. It is not
an IC3 target, a substitute for SUSB/QWI/BDS/J2J margins, or an input to
candidate fitting. Any later calibration or model use requires a
post-lock design decision.

## Initial descriptive profile

The staged long file contains 39,424 unique firm-year rows: 4,928
anonymized firms in each of eight years. Employment is available as an
exact count or interval on 24,139 rows; 23,569 are exact and 570 are
interval- or top-coded. Completed records decline from 4,928 in 2004 to
2,007 in 2011 as the cohort exits, merges, pauses, or stops responding.

| Year | Firm rows | Complete records | Employment available | Exact zero employees |
|---:|---:|---:|---:|---:|
| 2004 | 4,928 | 4,928 | 4,823 | 2,838 |
| 2005 | 4,928 | 3,998 | 3,952 | 1,633 |
| 2006 | 4,928 | 3,390 | 3,353 | 1,267 |
| 2007 | 4,928 | 2,915 | 2,890 | 1,299 |
| 2008 | 4,928 | 2,606 | 2,602 | 1,170 |
| 2009 | 4,928 | 2,408 | 2,398 | 1,158 |
| 2010 | 4,928 | 2,126 | 2,121 | 1,044 |
| 2011 | 4,928 | 2,007 | 2,000 | 969 |

These values describe a startup cohort, not national firm counts.
Cross-sectional survey weights sum to approximately 73,278 cohort firms
in every year, but must not be interpreted as the number of all US
firms.
