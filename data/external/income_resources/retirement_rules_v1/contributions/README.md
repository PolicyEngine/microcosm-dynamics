# Contribution ceilings and statutory indexing

`contribution_limits.py` names the rule being computed: nominal dollar ceilings
on ordinary employer-plan deferrals, employer catch-ups, annual additions,
IRA contributions and IRA catch-ups. It fits no model and reads no microdata.
Compensation limits, deduction phase-outs, plan availability, SIMPLE plans,
starter plans, service-based catch-ups and contribution tax character remain
outside this dollar-ceiling interface. Section 414(v)(3)(A) excludes employer
catch-ups from the section 415(c) annual-additions ceiling.

## Published figures

`parameters.json` transcribes every year from 2002 through 2026. The IRS
historical COLA table independently supplies all five ordinary ceilings for
2002–2025 on PDF pages 1–6. Pages 7–9 supply the earlier employer ceilings
for 1989 and 1991–2001; the table omits 1990. The IRS IRA research paper,
Table 4 (printed page 17), supplies the IRA ceiling of $2,000 for 1999–2001.
Only its traditional/Roth IRA columns support this transcription. Its SEP
column's $35,500 for 2001 conflicts with the IRS historical COLA table's
$35,000 and is not used. The annual-additions transcription uses the latter.
Catch-ups began in 2002 under Pub. L. 107-16 sections 601 and 631; zero before
2002 means the statutory catch-up did not yet exist. Missing earlier IRA
observations raise, including when requested through the combined interface.

The `annual_announcements` mapping records an IRS annual announcement for
each year. The original bulletin PDFs supply older notices whose standalone
drop-directory URLs return HTTP 404. No automated-request refusal was retried.

| Effective year | IRS annual announcement | Capture |
|---|---|---|
| 2002 | Notice 2001-84 | `irb_2001_53.pdf` |
| 2003 | Notice 2002-71 | `irb_2002_45.pdf` |
| 2004 | Notice 2003-73 | `irb_2003_45.pdf` |
| 2005 | Notice 2004-72 | `irb_2004_46.pdf` |
| 2006 | Notice 2005-75 | `irb_2005_45.pdf` |
| 2007 | Notice 2006-98 | `irb_2006_46.pdf` |
| 2008 | Notice 2007-87 | `irb_2007_45.pdf` |
| 2009 | Notice 2008-102 | `notice_2008_102.pdf` |
| 2010 | Notice 2009-94 | `notice_2009_94.pdf` |
| 2011 | Notice 2010-78 | `irb_2010_49.pdf` |
| 2012 | Notice 2011-90 | `irb_2011_47.pdf` |
| 2013 | Notice 2012-67 | `irb_2012_50.pdf` |
| 2014 | Notice 2013-73 | `irb_2013_49.pdf` |
| 2015 | Notice 2014-70 | `irb_2014_48.pdf` |
| 2016 | Notice 2015-75 | `notice_2015_75.pdf` |
| 2017 | Notice 2016-62 | `notice_2016_62.pdf` |
| 2018 | Notice 2017-64 | `notice_2017_64.pdf` |
| 2019 | Notice 2018-83 | `notice_2018_83.pdf` |
| 2020 | Notice 2019-59 | `notice_2019_59.pdf` |
| 2021 | Notice 2020-79 | `notice_2020_79.pdf` |
| 2022 | Notice 2021-61 | `notice_2021_61.pdf` |
| 2023 | Notice 2022-55 | `notice_2022_55.pdf` |
| 2024 | Notice 2023-75 | `notice_2023_75.pdf` |
| 2025 | Notice 2024-80 | `notice_2024_80.pdf` |
| 2026 | Notice 2025-67 | `notice_2025_67.pdf` |

Announcement 2014-37 (`irb_2014_51.pdf`, printed page 951) corrects a year in
Notice 2014-70's heading from 2014 to 2015. The dollar figures agree with the
IRS historical table. Notice 2025-67, PDF pages 1, 2 and 4, states the 2026
ordinary limits ($24,500; $8,000; $72,000; $7,500; $1,100), and the ages-60–63
employer catch-up of $11,250. Notice 2024-80 states the same enhanced amount
for 2025. All retrieval times, URLs, byte sizes and SHA-256 hashes, together
with failed URLs, are in `capture_manifest.json`.

## Projections

After 2026 the caller must supply index levels with the historical bases and
the 2025 index. The bases and 2025 index must reproduce the published 2026
ceiling after statutory rounding; an inconsistent anchor raises. This makes
the boundary from published to projected years explicit and prevents a
nonnegative forecast from lowering a ceiling through invented history.
The module refuses an unpublished year without the required series. It uses
exact fractions internally so an exact rounding threshold remains exact.
Published figures always take precedence over a supplied path.

| Ceiling | Statutory base | Index base | Rounding |
|---|---:|---|---:|
| Elective deferral | $15,000 | Q3 CPI-U, 2005 | $500 increase |
| Ordinary employer catch-up | $5,000 | Q3 CPI-U, 2005 | $500 increase |
| Annual additions | $40,000 | Q3 CPI-U, 2001 | $1,000 increase |
| Employer catch-up, ages 60–63 | $11,250 | Q3 CPI-U, 2024 | $500 increase |
| IRA | $5,000 | Section 1(f), 2007 | $500 total |
| IRA catch-up | $1,000 | Section 1(f), 2022 | $100 total |

Authorities: 26 U.S.C. 402(g)(4); 414(v)(2)(C)(i), (E)(i); 415(d)(2)–(4);
219(b)(5)(C); and 26 CFR 1.415(d)-1(b). The higher catch-up base follows
414(v)(2)(E)(i): the greater of $10,000 or 150% of the 2024 ordinary $7,500
catch-up, which gives $11,250. The statute rounds its *increase* in $500
units, so the enhanced total retains its $250 residue. It starts in 2025;
indexing starts in 2026 from Q3 2024. Its 2026 published amount is unchanged.

For the section 415(d) ceilings, the numerator is Q3 CPI-U in the year before
the contribution year. IRS Notice 2009-94, PDF page 1, says a decline in this
index cannot reduce a limitation. The module retains the highest computed or
published ceiling and therefore requires intervening projected index levels.
It computes each year's unrounded increase from the statutory base, avoiding
compounding already rounded limits.

Section 219 instead imports the section 1(f)(3) cost-of-living adjustment. Its
index is the average chained CPI-U for the 12 months ending August 31 in the
prior year, using the publication vintage specified by 1(f)(6)(A). For the
IRA's pre-2016 base, 1(f)(3)(B) splices ordinary and chained CPI:
`C-CPI-U[prior year] / (CPI-U[2007] * C-CPI-U[2016] / CPI-U[2016])`.
For the catch-up's post-2016 base, 1(f)(3)(C) gives
`C-CPI-U[prior year] / C-CPI-U[2022]`. These clauses floor the adjustment at
zero relative to the statutory base; they do not import section 415(d)'s
high-water protection. Therefore IRA ceilings may fall after deflation, while
all ceilings are nondecreasing under a nonnegative cost-of-living path.

## Invariants and verification

`test_contribution_limits.py` compares independently transcribed IRS rows for
all 25 years, tests the enhanced catch-up at each boundary age, and verifies
the annual announcement pins. Hypothesis checks published monotonicity,
projected monotonicity and rounding, the flat published/projected boundary,
exact rounding thresholds, under-50
ineligibility, and mandatory refusal of an unpublished year without a path.
A differential test compares the elective-deferral projector with a direct
Decimal implementation. Explicit refusal tests cover uncovered years, kinds,
ages, inconsistent historical anchors, missing bases or intermediate years,
malformed paths and invalid index
values. Invented paths distinguish Q3 CPI-U, annual CPI-U and annual chained
CPI-U so their statutory differences cannot disappear in the test fixtures.
