# Retirement-fund resources and DB pension COLAs

This note records the authority behind `retirement_resources.py` and
`pension_cola.py`. It encodes no state or local plan. The files in this
directory are pinned by URL, UTC retrieval time, byte size and SHA-256 in
[`capture_manifest.json`](capture_manifest.json). Unavailable and blocked
attempts remain in that manifest with their status; they supply no rules.

## SSI retirement-fund value

[POMS SI 01120.210](https://secure.ssa.gov/poms.nsf/lnx/0501120210)
A.3 values the amount currently withdrawable after an early-withdrawal
penalty, without deducting taxes. B and D.2 count a currently available lump
sum, including a partial withdrawal. C.1 excludes a fund when obtaining any
payment requires leaving the current job. C.3 counts a lump sum following
a denied periodic-benefit claim, subject to its next-month timing. E.1
requires an eligible owner to apply for periodic benefits and to choose
them over a lump sum. E.4 excludes funds owned by an ineligible spouse,
parent or spouse of a parent from deeming.

These provisions require current rights after any election. Periodic
eligibility alone cannot establish whether a separately available lump sum
survives the required election: B says that the fund may be uncountable,
while D.2 bases value on actual withdrawal access. The implementation
therefore refuses an unresolved election when lump-sum access remains;
it exposes the E.1 obligation when there is no lump-sum resource. It counts
the current accessible amount after a denied claim, and it requires the
caller to handle B's and C.3's month-of-availability rules. This is an
account-valuation function, not an SSI eligibility determination.

The source does not identify whether the 26 U.S.C. 72(t) additional tax is
the deductible early-withdrawal penalty in A.3 or a nondeductible tax.
`DEDUCT_AS_EARLY_WITHDRAWAL_PENALTY` and `DO_NOT_DEDUCT_TAX` preserve both
readings. Each call must explicitly choose one. SSI2 must resolve that
question from additional SSA guidance; WP2 selects neither. Ordinary
taxes never reduce value under either reading. The caller supplies the
additional-tax amount from the statutory distribution-tax layer, which
handles age and exceptions, rather than inferring a tax from age here.

POMS F supplies one example: Jeff Grant's $4,000 fund is currently
withdrawable while he remains employed, with a penalty and forfeiture of
a future annuity. SSA counts the amount after the penalty. Its example
supplies no penalty amount. The conformance test labels its $200 penalty
and age 45 as invented; it does not present $3,800 as SSA's own number.

## Federal DB rules

The encoded table is [`pension_cola_parameters.json`](pension_cola_parameters.json).
The function accepts a caller-computed fractional change in average
third-quarter CPI-W since the last adjustment base; it neither reads a CPI
series nor estimates a plan's terms. Supported adjustment years are
2002–2026. It refuses other years, unknown plans and unsupported annuity
categories. The current sections' amendment notes establish the core
formula during that interval; the FERS special-category name follows the
current 8412(d)(1) cross-reference. No pre-2002 delays or overrides are
silently extended into the supported interval.

| Plan | Authority | Full-year adjustment | Conditions |
|---|---|---|---|
| CSRS | [5 U.S.C. 8340(a)–(e), (g)](https://www.govinfo.gov/content/pkg/USCODE-2024-title5/html/USCODE-2024-title5-partIII-subpartG-chap83-subchapIII-sec8340.htm) | Positive CPI increase, rounded to the nearest tenth of a percentage point | Effective December 1; first increase prorated by months, counting any fraction; no increase on voluntary-contribution additional annuities; statutory cap applies |
| FERS | [5 U.S.C. 8462(a)–(d)](https://www.govinfo.gov/content/pkg/USCODE-2024-title5/html/USCODE-2024-title5-partIII-subpartG-chap84-subchapVI-sec8462.htm) | If raw CPI growth is at most 3%, the lesser of rounded CPI growth and 2%; above 3%, rounded CPI growth less one percentage point | Effective December 1; ordinary annuitants must be 62; first increase prorated and rounded |

Section 8462(c)(3)(B) excepts retirement under 8412(d)(1) or (e), the
specified military-reserve-technician disability retirement under 8414(c),
and annuitants outside 8412–8414 from the ordinary age restriction.
The supported categories include nonchild survivors and the disability
component under [8452(a)(1)(B)](https://www.govinfo.gov/content/pkg/USCODE-2024-title5/html/USCODE-2024-title5-partIII-subpartG-chap84-subchapV-sec8452.htm).
That disability component gets no increase during its initial 60%-of-pay
period and does afterward. Disability annuities require redetermination
at 62 under 8452(b), so the helper refuses the 8452(a) categories at that
age. It does not compute Social Security offsets, minimum disability
components, child annuities, survivor inheritance of prior adjustments,
or voluntary-contribution additional annuities.

For ordinary monthly annuities the amount helper applies the next-lowest
dollar rule and minimum $1 increase (8340(e), 8462(d)). CSRS callers must
supply their statutory monthly cap derived from 8340(g); an increase
cannot take the annuity above the cap or reduce the amount already
payable. The helper does not infer final pay or the GS-15 ceiling.

[OPM's COLA FAQ](https://www.opm.gov/frequently-asked-questions/retire-faq/post-retirement/how-is-the-cost-of-living-adjustment-cola-determined/)
confirms the formula, first-year proration and age/disability conditions.
[GAO/GGD-97-40](https://www.govinfo.gov/content/pkg/GAOREPORTS-GGD-97-40/pdf/GAOREPORTS-GGD-97-40.pdf),
printed p. 53 footnote 8 (PDF p. 55), supplies a worked assumption: with
4.5% CPI growth, FERS gets 3.5% and CSRS gets 4.5%. The tests reproduce it.

## State and local variation and proposed assumption

[NASRA's June 2026 COLA brief](https://www.nasra.org/files/Issue%20Briefs/NASRACOLABrief.pdf),
pp. 1–3 and appendix A, describes automatic and ad hoc increases,
inflation caps, fixed rates, simple or compound increases, funding and
investment conditions, delayed onset, limited benefit bases, and cases
without a COLA. Table 1 describes selected plans rather than a universal
state rule. Its appendix includes employment cohorts and employer
elections with no COLA. These differences preclude treating federal law
as the state/local rule.

Proposed option `STATE_LOCAL_CPI_CAPPED_AT_THREE_PERCENT` compounds an
annual positive caller-supplied CPI rate, capped at 3%, once the pension
is in payment. It offers a transparent approximation motivated by one
common design in NASRA, not an estimate of an average plan. It omits
eligibility delays, ad hoc decisions, funding conditions, simple COLAs
and partial benefit bases. WP4 must register a choice or use verified
plan terms before applying it. WP2 selects no default.

## Private DB prevalence and proposed assumption

The [DOL 2024 inflation report](https://www.dol.gov/sites/dolgov/files/ebsa/laws-and-regulations/laws/secure-2.0/report-to-congress-2024-impact-of-inflation-on-retirement-savings.pdf),
printed p. 12 (PDF p. 12), says private DB plans tend not to index benefits.
For a historical quantitative description, GAO/GGD-97-40 printed p. 114
Table IV.11 (PDF p. 116) reports that 43% of 497 plans in its contractor's
employer database provided at least one postretirement increase during
1983–1992; 44% did not and 13% did not respond. Any increase over a decade
is a different concept from automatic annual inflation indexing. These
figures describe a selected historical database and do not establish
current national prevalence. Printed pp. 28 and 51–52 also explain the
limits of available private COLA data and the ad hoc character of many
increases.

Proposed option `PRIVATE_FIXED_NOMINAL` holds an in-payment private DB
benefit fixed in nominal dollars. This choice follows DOL's qualitative
description while remaining an explicit assumption; it can miss ad hoc
increases and the minority of indexed contracts. WP4 must register a
choice before using it. WP2 selects no default.

Direct plain requests for the BLS National Compensation Survey overview,
BLS post-retirement pension increases paper, and GAO HEHS-95-219R PDF
returned HTTP 403. They are `SOURCE_BLOCKED` in the manifest, and no
request attempted to bypass those refusals. The accessible GAO/GGD-97-40
report is a different primary report, not a second capture of the blocked
report. A modern representative estimate of automatic private COLA
coverage remains unavailable in these captures.
