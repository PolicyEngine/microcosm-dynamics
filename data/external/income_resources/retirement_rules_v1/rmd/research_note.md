# Owner lifetime required minimum distributions

This rule covers ordinary owner-held IRA and employer DC balances for
distribution years from 2003 under the captured law. It excludes inherited
accounts, DB annuities, special pre-1987 403(b) balances, and QLAC or partial
annuitization adjustments. The caller supplies the adjusted prior year-end
balance. Complete primary-source captures accompany the extracted owner
table rows in `parameters.json`; `build_parameters.py` reproduces them.

## Applicable ages and the historical holdout

The statutory changes apply by cohort, rather than changing the beginning
age of someone already subject to RMDs:

| Birth date | Applicable age | Authority |
|---|---|---|
| Before 1949-07-01 | 70½ | Pre-SECURE IRC 401(a)(9)(C); TD 8987 |
| 1949-07-01 through 1950-12-31 | 72 | Pub. L. 116-94, division O §114, effective for people attaining 70½ after 2019 |
| 1951-01-01 through 1958-12-31 | 73 | Pub. L. 117-328, division T §107; IRC 401(a)(9)(C)(v)(I) |
| During 1959 | Open: 73 or 75, explicit named choice | TD 10001 footnote 7; proposed REG-103529-23 |
| On or after 1960-01-01 | 75 | IRC 401(a)(9)(C)(v)(II) |

The current captured 26 CFR 1.401(a)(9)-2(b)(2)(v) remains reserved.
REG-103529-23, 89 FR 58644–58645, proposes age 73 for 1959. The API
requires `Birth1959Rule.IRS_PROPOSED_73` or `STATUTORY_75` for that cohort;
it selects neither by default. IRS Announcement 2026-7 discusses the future
applicability of parts of the proposed regulations; it does not supply a
final replacement for the reserved paragraph. Both named readings preserve
nondecreasing applicable age by birth date.

For the proposed 2017–2023 holdout, 70½ applies to the older cohort in
2017–2019. The CARES Act, Pub. L. 116-136 §2203, waives owner DC/IRA
RMDs for 2020. The age-72 regime begins with the July–December 1949
birth cohort in 2021 and the 1950 cohort in 2022. The 1951 cohort has
its first age-73 obligation in 2024, rather than 2023. Existing older
owners continue annual obligations in 2023. Uniform and joint divisors
change for everyone covered from distribution year 2022. Pub. L. 110-458
§201 also waives 2009 DC/IRA RMDs.

## Beginning date and exemptions

IRC 401(a)(9)(C)(i) sets April 1 of the following calendar year as the
required beginning date. For an ordinary employer DC plan the year is
the later of the applicable-age year and retirement from the employer
maintaining that plan. IRC 401(a)(9)(C)(ii) removes that delay for IRAs and
5-percent owners. The caller must identify current-employer employment
and the applicable-year owner status; an employer plan can itself require
the age-based beginning date (26 CFR 1.401(a)(9)-2(b)(4)). Governmental
and church-plan special owner-status rules are outside this ordinary-plan
interface.

The RMD function returns the distribution-year obligation. Deferring the
first payment until the following April does not reduce either year's
obligation. The 2020 waiver of certain unpaid first-2019 payments is a
payment-timing rule outside this function, rather than a change to the
2019 obligation.

Roth IRAs have no owner lifetime RMD (IRC 408A(c)(5), also captured by
the early-distribution sublayer). SECURE 2.0 §325 exempts designated Roth
employer accounts from 2024. Its effective-date exception preserves
pre-2024 distribution-year obligations even when payable during 2024.

## Divisors and source defects outside covered ages

The earlier tables come from TD 8987, 67 FR 18988, April 17, 2002,
26 CFR 1.401(a)(9)-9 A-2 and A-3, mandatory from 2003. The new tables
come from TD 9930, 85 FR 72472, November 12, 2020, paragraphs (c), (d)
and (f), effective from 2022. The joint table applies only when the sole
beneficiary is a spouse more than ten calendar ages younger. Owner and
spouse ages are the ages attained on birthdays in the distribution year.

The parameter extraction covers owners 70–120 before 2022 and 72–120
thereafter, with spouse ages 0–120. The earlier terminal 115-and-over
cell applies through the API's age-120 ceiling. Earlier years, higher
ages, and table lookups below the covered owner ages raise.

The Federal Register HTML for the earlier joint table has conflicting
transposed entries at (22,23)/(23,22) and (23,25)/(25,23); the newer
HTML has conflicting (2,5)/(5,2) entries and a short row 19 for spouse
ages 27–35. These young-owner rows cannot enter a covered owner RMD.
They are excluded from the encoded parameters, without choosing or
repairing their values. Every encoded cell agrees with its transpose
where both are printed; missing triangular cells use the printed
transpose. Full original tables remain captured for audit.

An exhaustive check also finds a covered-age conflict: TD 8987's joint
table and the captured 2020 CFR, vol. 6, table 4, print **60.3** at owner
97/spouse 20; IRS Publication 590 (2013), Appendix C, prints **63.0**.
The Federal Register correction of May 24, 2002 (67 FR 36676, C2-8963)
addresses rows 25 and 63, not row 97. The 60.3 cell makes the RMD
fraction decrease between owner ages 97 and 98 for a fixed age-20 spouse.
This is the sole adjacent-age reversal in the covered extracted tables.
The API refuses this particular cell unless the caller chooses
`HistoricalJointTableReading.CFR_LITERAL_60_3` or
`IRS_PUBLICATION_63_0`. It selects neither and does not silently repair
the regulation. The monotonicity property holds for all other cells and
for the IRS-publication reading; a separate test preserves the literal
CFR counterexample. A final source-resolution decision remains open.

## Worked-example verification

The captured IRS Publication 590-B, “Which Table Do You Use To Determine
Your Required Minimum Distribution,” gives $100,000 at age 75 in 2026:
the six-years-younger sole spouse uses 24.6 ($4,065 rounded); the
eleven-years-younger spouse uses 25.3 ($3,953 rounded). Publication 590
(2013), printed p. 36, supplies the corresponding 2014 examples with
22.9 ($4,367) and 23.6 ($4,237). Its p. 40 Justin example exercises
70½ timing and the age-70 and age-71 divisors. The rule returns the
unrounded quotient; whole-dollar comparisons reproduce the publications.

The live Publication 590-B's separate Justin example repeats age 73 in
two successive years. It conflicts with its birthday-age instructions
and table; that example is not used. The internally consistent 2013
version is captured and tested instead.

The eCFR beginning-date URL returned a bot challenge and is recorded
`SOURCE_BLOCKED`; no bypass was attempted. The current Cornell rendition
of the same regulation and the Federal Register final rule supply the
reserved-paragraph and beginning-date evidence. See `capture_manifest.json`
for every URL, retrieval timestamp, size and hash.
