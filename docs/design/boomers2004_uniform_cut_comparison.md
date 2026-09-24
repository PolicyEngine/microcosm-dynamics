# Boomers 2004 uniform cut comparison: specification for DynaSim scorecard exercise 2

- **Status:** draft for the referee. Nothing here is ratified. One
  referee pass is recorded (§17); this draft applies it and awaits a
  second pass on what the first did not see. Max has not ruled on
  exercise 2 (cos decision d189, open, default "yes to Track U with the
  proposed SSI rule; downloads needed from Max") or on the fallback rule
  (§11). Every choice that awaits him or the specification freeze is an
  explicit parameter in the code with the recommended default, and §16
  lists them.
- **Specification:** `boomers2004_uniform_cut_exercise2`, version
  `u1-draft-4`, drafted 2026-09-24. §19 is the changelog.
- **Plan item:** U1 of the Track U plan,
  `EVID/critical-path-uniform-cut-20260923.md` (§7 fields F1–F17, §8
  work items), where `EVID` =
  `~/microcosm-launch-evidence/dynasim-parity-20260909`. This document
  mirrors the structure of the exercise-1 specification,
  `docs/design/urban2010_cola_comparison.md`.
- **Claim class (proposed, pending d189):** a realized-outcome
  measurement on PSID persons at age 67, not a projection. It does not
  test the Dynamics projection engine (plan, bottom line item 3).
- **Labels every output carries:** *PSID-realized outcomes (not a
  projection)*; *Python income concept (not Axiom)*; *mechanical
  incidence* (`adjusted_poverty.OUTPUT_LABELS`; the tabulation refuses
  labels without them).
- **Builder boundary:** model-builder lanes wrote this draft. Drafts 1–3
  did not open the Report PDF (`REFS/900767-how-will-boomers-fare.pdf`)
  and cited the plan's reading of its methods (plan §2). For
  `u1-draft-4`, to verify the referee's changes, the builder read the
  Report's table of contents, list of tables and list of appendix tables
  (PDF pages 5–7) and Section III, printed pages 19–24 (PDF pages 20–25),
  the range `EVID/RESTRICTED-FILES.md` clears; the page mapping (printed
  *n* = PDF *n* + 1) was checked from the footer digits of PDF pages 20
  and 25 alone. Statements checked there now cite the Report page. No
  lane opened printed page 25 or later for this draft, any results table
  of the Report, the exercise-2 or COLA comparator directories, any
  comparator seal or reconciliation file, the Track A comparison memo,
  the issue #42 result comments, or page 3 or later of the Urban 2010
  report. Through the plan, this draft inherits two things the plan
  disclosed or used: a qualitative fragment of printed page 41 (late
  boomers; no number; no exercise-2 cell), shown when the plan mapped
  page numbers (plan §14), and the plan's reading of printed page 25
  (reporting splits, 2003 dollars). `RESTRICTED-FILES.md` names printed
  pp. 19–24 as the readable methods range, so page-25 readings are cited
  here only where another readable source confirms them (the cells now
  cite the list of appendix tables). §18 lists what this draft read and
  what it did not verify.

## 1. Target

The target is the adjusted poverty rate at age 67 in Butrica and
Uccello, *How Will Boomers Fare at Retirement?* (AARP Public Policy
Institute #2004-05, May 2004):

- **Tables:** 19, "Adjusted Poverty Rates at Age 67", and 21, "Adjusted
  Poverty Rates at Age 67, Assuming 13 Percent Reduction in Social
  Security Benefits" (list of tables, printed p. 5). The comparator is
  the change from Table 19 to Table 21. Which rows those tables carry is
  unknown to this builder (plan §10, decision 2(b)).
- **Cohort:** persons born 1936–1945 ("near-retirees"), each analysed
  when they reach 67 (p. 24).
- **Model:** DYNASIM, from a sample of about 100,000 individuals from the
  1990–93 SIPP, aged in yearly steps to 2050 (p. 20), with OCACT
  projections from the intermediate scenario of the 2002 Trustees Report
  for mortality, wage growth and prices (p. 20, fn. 4).
- **Unit and income concept:** results are reported for individuals, but
  each individual's income and wealth are the household's, including the
  spouse's if married (p. 24). The income resources projected at 67
  include earnings, SSI and co-resident income, meaning income of
  non-spouse co-resident family members (p. 19). Whether co-residents
  count in family size is not stated in pp. 19–24. The Report's income
  differs from Census money income by imputing income from financial
  assets as the real (price-indexed) annuity that 80 percent of those
  assets would buy (p. 24), recalculated each year, with a 50 percent
  survivor annuity for married couples (fn. 10). The Census measure, by
  contrast, counts interest and dividends, and counts retirement-account
  income only when annuitized or otherwise withdrawn (p. 24; fn. 11
  lists its sources).
- **Financial assets:** non-pension wealth (vehicle, other real estate,
  farm and business equity, stock, mutual fund and bond values, and
  checking, savings, money market and certificate of deposit balances,
  less unsecured debt; p. 22) plus IRA, Keogh and 401(k) balances
  (p. 24). Home equity is projected separately (p. 23) and is not among
  the financial assets (pp. 22, 24).
- **Threshold:** "the official poverty thresholds of the U.S. Census
  Bureau", which "vary with family size and age"; "we use the
  65-and-over poverty threshold" (p. 24).
- **Cut:** a 13 percent reduction in Social Security benefits: OCACT
  "estimates that benefits would need to be reduced immediately by 13
  percent" (p. 22, citing the 2003 Trustees Report). Its start year,
  coverage, SSI treatment and any behavioural response are not in
  pp. 19–24 (plan §10, decisions 2 and 8).

The comparator values are sealed on the comparator side. This builder
has not seen them and does not know which cells they cover.

## 2. Sources

| Source | Use | Status |
|---|---|---|
| Plan, `critical-path-uniform-cut-20260923.md` | Every field proposal (§7) | Read in full |
| The Report: table of contents, lists of tables and appendix tables (PDF pp. 5–7); Section III, printed pp. 19–24 (PDF pp. 20–25) | §1, §4, §5 citations (u1-draft-4) | Read; nothing later |
| Referee report `EVID/boomers2004-referee-20260924.md` | §17 | Read in full; every required change checked against its source |
| PSID family files 2005–2013 (`psid-data/family/<wave>/FAM<wave>ER.*`) | Family income components, Social Security, SSI, asset income, the head's annuity and IRA income, farm income, FU composition, PSID's needs standard; WEALTH1 in 2009–2013 | Staged; labels verified by `data/family_income.py`; codebook entries for `HEAD ANNUITIES`, `HEAD IRAS`, `WIFE RETIREMENT/ANNUITIES`, `OTHER FU MEMBR RETIREMENT/ANNUITIES`, ER52214, ER52216, ER52368 and W21, W33 read |
| PSID wealth supplements 2005 and 2007 | WEALTH1 for the 1937 and 1939 birth years (U0) and six U1 observation cells | **Not staged.** The reader refuses with the missing files named (§3) |
| PSID cross-year individual file (`ind2023er`) | Anchors per wave, cross-section weights, relationship to head, age, sampling-error stratum and cluster | Staged; labels verified by `cohorts/age67.py`, including relationship code 90 ("Legal husband of Head") |
| PSID marriage history (`mh85_23`) and earnings panel | Birth-year law and marital status | Existing readers |
| NCHS United States Life Tables, 2000 | Annuity mortality (F8) | Committed, `data/external/nchs_life_tables_2000.json`, SHA-256 pinned |
| SSA period life table for 2004 (2008 vintage) | Row U9 | Committed, `data/external/tr2008/ssa_2008_vintage.json` |
| SSI federal benefit rates 2004–2012, exclusions, resource limits | SSI response (F13); F17 SSI diagnostic | Captured from policyengine-us revision `a03e82e503`: `data/external/track_u_ssi_parameters.json`, SHA-256 `79e641a1…3c523`; checked against the Federal Register and eCFR (§8) |
| Census poverty thresholds 2004–2012 | Threshold (F10) | **Not captured** (§6; cos decision d194) |
| SSA, *Annual Statistical Supplement, 2025*, Table 5.A4 | F17 Social Security diagnostic | Committed snapshot `data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_5a.html`, SHA-256 `d61e9484…aa8e` |
| Survey of Consumer Finances wealth tables | F17 WEALTH1 comparator (plan §11) | **Not committed or saved**: WEALTH1 is summarized without a published comparison |
| PSID 2011 User Guide §2.4; individual-file codebook (ER34102, ER34103, ER34137–ER34143); family-file codebook (`# IN FU`, the individual-record count) | The institution income rule (§3) | Staged documentation, read for the rule |

## 3. Population

**Primary (U0): exact age.** Persons born in 1937, 1939, 1941, 1943 and
1945, each observed in the income year they turn 67. The PSID is
biennial from 1999 and wave *W* reports calendar year *W* − 1, so only
even income years exist; an odd birth year turns 67 in an even year.

| Birth year | Income year | Wave | Weight | Family unit | WEALTH1 |
|---|---|---|---|---|---|
| 1937 | 2004 | 2005 | ER33849 | ER33801 | 2005 supplement, not staged |
| 1939 | 2006 | 2007 | ER33951 | ER33901 | 2007 supplement, not staged |
| 1941 | 2008 | 2009 | ER34046 | ER34001 | ER46968 |
| 1943 | 2010 | 2011 | ER34155 | ER34101 | ER52392 |
| 1945 | 2012 | 2013 | ER34269 | ER34201 | ER58209 |

**Alternative (U1): all ten birth years.** Odd birth years as in U0; each
even birth year 1938–1944 observed at 66 and at 68 (income years *b* + 66
and *b* + 68) with half weight each; 1936 observed at 68 only (income
year 2004; its age-66 year, 2002, is in the 2003 wave, which carries
aggregates only, plan §3) with weight 1. With weight 1 every birth year
enters U1 with one cross-section's worth of weight: even birth years from
two half-weighted observations, the odd years and 1936 from one
full-weighted observation; 0.5 would halve 1936's share of the cohort
(referee Q4). The 1936 observation is at 68, so it omits 1936-born
persons who died between 67 and 68, a survivor effect inside the
exact-age named delta.

**Fallback (U0-F): 1941, 1943 and 1945.** U0 restricted to the birth
years whose waves carry WEALTH1 in the family file; the blocked 1937 and
1939 are left out and counted. §11's fallback rule decides whether U0 or
U0-F is the headline, by staging status only.

**Universe per wave (F2).** Sequence 1–20 (in a responding family) and a
positive core/immigrant cross-section weight. The cross-section weight
is also positive for movers-out (71–80) and decedents (81–89); no row
admits them and the dispositions count them. Registered row U-inst adds
sequence 51–59 (institutions).

**Institution income rule (U-inst; builder default of `u1-draft-3`,
pending the freeze, not yet refereed).** The plan gives
institutionalized persons no income rule, and the PSID collects no
income for them: the individual-file Social Security items are "Inap.:
… in an institution" (codebook, ER34137–ER34143 for 2011). The PSID does
associate them with a family: when a sample member moves to an
institution it "attaches an institutional status data record to the
family they left" (2011 User Guide, §2.4), and the family file's
record-count variable counts "any institutionalized individuals
associated with the family" among the records "having the same
family-level data". The default `institution_income_rule =
family_of_record` therefore gives an institutionalized observation the
family unit whose interview number its record carries: that family's
income concept, wealth, size, children and threshold, and (under
`fu_head_rule`, §5) that family's annuity. Its role is OFUM: the
relationship code of a person in an institution is to the previous
wave's head (codebook note on ER34103), so it is neither the current
head nor the wife, and it has no co-resident spouse. The member's own
income is missing from the family's, and `# IN FU` ("the actual number
of persons currently in the FU") does not count them (§14). Both are
named deltas (§12). An institutionalized person whose interview number
has no family-file record that wave is a disposition
(`institution_family_of_record_missing`). The alternative `excluded`
keeps institutionalized persons out of the universe (disposition
`institution_excluded_by_rule`), which makes U-inst's population U0's.

**Birth year.** `estimates.career.derive_birth_years` (the first-estimates
§3.1 law, as Track A uses), total over the union of the five waves'
universes. The law's seed coordinate (clause 3) is taken from the
earliest of the five waves in which the person is present (builder
choice; the plan names the law but not the seed wave).

**Weight.** The cross-section weight of the wave that reports the income
year, times the U1 multiplier. No reweighting or alignment.

**Family unit.** The wave's interview number
(`family_unit_id = wave × 100000 + interview`). The half-split floor
splits on family units linked through shared persons (§10).

**Attached per observation** (`cohorts/age67.build_age67_cohort`): sex
(ER32000 through the death-record reader); relationship to head (10
head, 20 legal wife, 22 cohabiting "wife", 90 legal husband of head,
otherwise OFUM; the codes are verified in `IND2023ER_formats.sas` for
each wave); marital status at the end of the income year from the
marriage history (F12; separated counts as married); whether a legal
spouse lives in the same family unit, and the spouse's age and sex; the
family head and the head's co-resident legal spouse (code 20 or 90),
with their ages and sexes (the annuitants of §5); and the sampling-error
stratum and cluster (ER31996, ER31997). A member whose history cannot
date the state (`unknown`), or who has no marriage-history record
(`no_marriage_history`), is classified by
`unresolved_marital_status="relationship_code"` (pending the freeze;
referee Q7): married and co-resident when the member is head (10) with a
co-resident legal spouse (20 or 90), or is the head's legal wife (20) or
legal husband (90); otherwise non-married. The alternative `non_married`
classifies them all as non-married (the `u1-draft-3` rule). Each
resolution path is counted (`marital_resolution`). The marital pairs
indicator of the individual file is not used. An institutionalized
member is never resolved by code: its relationship code is to the
previous wave's head.

**Structural counts** (staged PSID, counts only; `scripts/track_u_structure.py`,
evidence `EVID/track-u-structure-20260924/`, code of `u1-draft-1`):

| Row | Observations | Persons | Computable now | Blocked by the 2005/2007 wealth supplements |
|---|---|---|---|---|
| U0 | 483 | 483 | 320 (1941, 1943, 1945) | 163 (1937: 81; 1939: 82) |
| U1 | 1,349 | 970 | 857 | 492 |

U0 by birth year: 1937 81, 1939 82, 1941 93, 1943 116, 1945 111
observations; U0-F is the last three, 320. The rest of each birth year's
universe persons were not present at the observation wave (sequence 0,
moved out or died); the evidence file lists every disposition. Of the
483 U0 observations, 35 are OFUMs (95 of 1,349 under U1), 457 have
marriage-history birth years, and 35 have an unresolved marital state
(26 `no_marriage_history`, 9 `unknown`), which `u1-draft-1` counted as
non-married. The counts under this draft's rules (resolution paths,
annuitant age sources, farm and head retirement-account income) are
recollected by the same script; §14 records them. No income, threshold
or poverty status was computed.

## 4. Income concept

**Money income (F3).** Primary: the family unit's `TOTAL FAMILY INCOME`
for the income year. The 2011 codebook defines it as the sum of head and
wife taxable income, head and wife transfer income, OFUM taxable income,
OFUM transfer income, and head, wife and OFUM Social Security. On the
staged files this identity holds exactly for every family in all five
waves (`reconcile_family_income`, counts only). Row U4: head and wife
income only (head and wife taxable and transfer income and Social
Security), size = the member plus a co-resident wife or partner; an OFUM
member keeps the family-unit basis.

**Asset income (F4).** Primary: remove the reported asset income of the
unit and add the annuity. Removed items (family file, every wave): head
and wife rent, dividends, interest, trusts/royalties and the asset part
of unincorporated-business income, and, under the family-unit basis, the
OFUM total asset income. Rent, business asset income and the OFUM total
can be negative (losses, per the codebooks); removing a loss raises
income. Row U5: keep reported asset income (and the F4a and F4b items)
and add the annuity.

**Retirement-account income (F4a, pending the freeze).**
`retirement_account_income_rule="remove_head"` (default): under
`replace`, the head's annuity and IRA income is removed with the asset
income. The item is `HEAD ANNUITIES`, "Head's Income from Annuities and
IRAs" in the 2005, 2007, 2009 and 2011 codebooks (ER27964, ER40954,
ER46862, ER52270); the 2013 file splits it into `HEAD ANNUITIES`
(ER58071, "Head's income from annuities") and `HEAD IRAS` (ER58073), and
both are removed. The balances that produce this income are in WEALTH1
(W21/W22, "private annuities or Individual Retirement Accounts") and
annuitized under F5–F6, and the Report contrasts its annuity with Census
income, which counts retirement-account income only when annuitized or
withdrawn (p. 24). The wife's item before 2013 (`WIFE
RETIREMENT/ANNUITIES`, "Income from Pensions and Annuities") and the
OFUMs' (`OTHER FU MEMBR RETIREMENT/ANNUITIES`, "Other Retirement,
Pensions, and Annuities") combine pensions with annuity income and are
kept in every wave, including 2013, so the rule is the same across waves
(named delta, §12). Alternative `keep`: no removal (the `u1-draft-3`
behaviour).

**Farm income (F4b, pending the freeze).** `LABOR INCOME OF HEAD` and
`OF WIFE` exclude farm income and the labor part of business income.
Head and wife taxable income equals labor income plus farm income plus
the head's and wife's labor part of business income plus the ten asset
items, exactly for every family in 2007, 2011 and 2013, within $10 in
2009, and for all but two 2005 families. Farm income (ER52214 in 2011,
"Head's and Wife's Income from Farming") "includes both labor and asset
portions of income"; its asset portion is not separated. F4 applies the
PSID's own business convention to it (`farm_asset_share`, default 0.5):
half of positive farm income, and the whole of a farm loss, count as
asset income and are removed under `replace`. The convention is the
codebook's for business income: "Total business income of the Head is
equally split between labor and asset income when the Head put in actual
work hours", and "If total farm or business income represents a loss …,
then the labor portion equals 0 and the loss is coded in the asset
portion" (ER52216). The Report's financial assets include farm equity
(p. 22), so its income is income from financial assets. Alternative 0:
farm income stays whole in income (the `u1-draft-3` behaviour). The
number of cohort observations with nonzero farm income is recollected
with the structural counts (§14).

**Financial assets (F5).** The family unit's WEALTH1, "IMP WEALTH W/O
EQUITY": the codebooks define it as seven asset values (farm or business,
checking and savings, other real estate, stocks, vehicles, other assets,
IRAs and annuities) net of debts (2009: one "other debt" item; 2011: five
debt types; 2013: farm/business and real-estate debt split out plus six
debt types). On the staged files the component identity holds exactly
for every family in 2009, 2011 and 2013. The Report's financial assets
include 401(k) balances (p. 24); WEALTH1's seven asset types do not
include employer DC balances held outside IRAs, so the primary
understates financial assets for families that hold them (named delta,
§12). Row U7 adds them where the PSID observes them (P-section items,
label investigation pending). U7 must be built, or removed from §11,
before registration; if the investigation shows the items are reliable
for 66–68-year-olds before the freeze, the freeze should consider making
WEALTH1 plus employer DC balances the primary (the Report's definition)
and WEALTH1 alone the alternative.

## 5. Annuity

- **Amount:** `0.8 × max(WEALTH1, 0) / price` (F6, F9).
- **Price** of a real level annuity of 1 per year, annuity-immediate,
  3 percent real, no load (F7). The 3 percent is the real return on
  government bonds that DYNASIM assumes after 2001 for DC and IRA
  accumulation (p. 22); the same paragraph subtracts 1 percentage point
  from stock and bond real returns for administrative costs, so the net
  government-bond return there is 2 percent. Neither is stated to be
  DYNASIM's annuity-pricing rate. The primary uses the gross 3 percent;
  `real_interest_rate=0.02` is a reported, unscored sensitivity. Single
  life `a_x = Σ_{t≥1} v^t ₜp_x`; joint and 50 percent survivor, paying 1
  while both live and 0.5 to the survivor, with independent lives:
  `Σ_{t≥1} v^t (s·ₜp_x + s·ₜp_y + (1 − 2s)·ₜp_x·ₜp_y)`, which is
  `0.5·(a_x + a_y)` at s = 0.5.
- **Lives (F6, `annuity_lives="fu_head_rule"`, pending the freeze;
  referee Q1):** the family unit's WEALTH1 is priced on the lives of its
  main owners: joint on the family head and the head's co-resident legal
  spouse (a legal wife, code 20, or a legal husband, code 90), single
  life on the head otherwise. For heads and legal spouses this equals
  pricing on the member and a co-resident legal spouse; it differs for
  OFUM members and cohabiting partners (code 22), whose family's wealth
  would otherwise be annuitized over their own lives (alternative
  `member_rule`, F6 as the plan wrote it). For example (NCHS 2000, 3
  percent), a 67-year-old OFUM woman's single-life price is 12.5868,
  while a family headed by a couple aged 40 (man) and 38 (woman) has a
  joint price of 22.0299, so `member_rule` would give that family's
  wealth an annuity 1.75 times as large.
- **Ages (`annuitant_age_source="derived_birth_year"`, pending the
  freeze; referee Q8):** every annuitant's income-year age, income year
  minus derived birth year, from `estimates.career.derive_birth_years`
  extended beyond the universe to in-family heads, legal wives,
  cohabitors (22, 88), legal husbands and marriage-history spouses of
  cohort members (typically zero-weight nonsample spouses; their seed
  coordinate is the earliest of the five waves in which they are in a
  family). Where the law leaves a person unresolved (including
  conflicting marriage-history birth years, which the extension leaves
  out rather than failing the build), the individual-file age at the
  wave is used and counted (`wave_age`). The law gives the
  marriage-history birth year precedence and treats `(wave − 1) − age`
  as the birth year only in its last clause; for people dated by
  marriage history, the wave age can exceed the income-year age by one
  year (NCHS 2000, 3 percent: m67 + f67 costs 11.7610, m67 + f68
  11.5487, a 1.8 percent larger annuity). Alternative `wave_age`: every
  annuitant at the individual-file age of the wave.
- **Mortality (F8):** NCHS 2000 by sex. Survival stops with the table:
  the open interval "100 years and over" (qx = 1) is treated as death
  within the year at 100 (builder choice). Row U9: the SSA period life
  table for 2004 (ages 0–119).
- **Negative WEALTH1 (F9):** buys no annuity and is not subtracted.

Annuity prices computed from the committed tables (immediate; not PSID
data, not comparator values; the 3 percent table recomputed by the
referee in independent code):

| Age | Rate | NCHS 2000 male | NCHS 2000 female | SSA 2004 male | SSA 2004 female |
|---|---|---|---|---|---|
| 66 | 3% | 11.3375 | 13.0092 | 11.6068 | 13.2336 |
| 67 | 3% | 10.9353 | 12.5868 | 11.1936 | 12.8042 |
| 68 | 3% | 10.5344 | 12.1622 | 10.7802 | 12.3725 |
| 67 | 2% | 11.9261 | 13.8562 | 12.2165 | 14.1120 |

Joint and 50 percent survivor, male 67 and female 67: 11.7610 (NCHS
2000, 3%), 11.9989 (SSA 2004, 3%), 12.8912 (NCHS 2000, 2%), 13.1643 (SSA
2004, 2%).

## 6. Thresholds

**Primary (F10):** the Census weighted-average poverty threshold of the
income year for the unit's size, using the "65 years and over" rows for
sizes 1 and 2 whatever the householder's age (the Report uses "the
65-and-over poverty threshold", p. 24); sizes 3 to 8 by size; 9 or more
share one row. Poor means income below the threshold. The capture uses
the weighted averages as printed in the historical workbooks
(`threshYY.xlsx`); the Census historical-thresholds page notes that
these may differ from Historical Poverty Table 1 because of later
weight-control updates (the referee's reading of the page; not re-read
for this draft).

**Row U10:** the Census size-by-related-children matrix, with the
householder-65-and-over rows for sizes 1 and 2; PSID `# CHILDREN IN FU`
stands in for related children, although it counts all persons under 18
other than head and wife, related or not. **Row U8:** PSID's `CENSUS
NEEDS STANDARD-<income year>`, which the codebook describes as the Census
matrix threshold by family size, number under 18 and householder age,
adjusted for composition changes during the year (householder age, not
the 65-and-over rule).

**Capture status: not captured.** The Census historical thresholds page
lists one spreadsheet per year, `thresh04.xlsx` … `thresh12.xlsx`, under
`https://www2.census.gov/programs-surveys/cps/tables/time-series/historical-poverty-thresholds/`.
The files have not been downloaded (downloads need Max's approval in
this environment, cos decision d194). Once the nine files are staged in
a directory, `scripts/capture_track_u_parameters.py --census-dir DIR`
parses them by their printed labels, checks that the 65-and-over rows
sit below the under-65 rows and that thresholds rise with size, records
each file's URL, bytes and SHA-256, and writes
`data/external/census_poverty_thresholds_2004_2012.json`; the pin
`adjusted_poverty.THRESHOLDS_SHA256` must then be set. The parser has run
only on invented workbooks, and the labels it expects ("65 years and
over", "Householder 65 years and over") have not been checked against
the real 2004–2012 files; the first real capture must be checked by eye.
Until then `load_poverty_thresholds` refuses and no primary threshold can
be assigned.

## 7. The cut

**Primary (F11):** reform income subtracts 13 percent of all Social
Security income of the unit (head, wife and OFUM amounts under the family
basis) in the income year. No behavioural response. Every U0 income year
is 2004 or later, so the unread start year matters only for U1's 1936
row: row U6 (on U1) leaves 1936 uncut if the cut starts in 2004. The
Report's methods say "reduced immediately" (p. 22); the scorecard's
"from 2004" has no source this builder could read (plan §10, decision
8).

**Row U6 (built; the start year awaits decision 8).**
`AdjustedPovertySpec.cut_start_year` (default `None`: every observation
is cut) is the row's parameter. With a start year, an observation is cut
only when its member turns 67 (birth year + 67) in or after it: the
observation stands for the member's status at 67, so the rule keys on
the age-67 year, not on the income year (U1 observes 1936 at 68, in
2004). With 2004, only the 1936 birth year (67 in 2003) is uncut; its
reform income equals its baseline, and with no fall in countable income
the SSI rules give it no offset and no new take-up.

## 8. SSI response

**Primary (F13, pending Max, d189): offset for existing recipients.** For
each SSI unit with baseline SSI, SSI rises by the fall in countable Social
Security income, capped so SSI does not exceed the federal benefit rate
(FBR); nobody newly enrols. With a cut rate c and the $20 monthly general
exclusion (G = $240 a year), the fall is
`max(0, S − G) − max(0, (1 − c)·S − G)` and the rise is
`min(fall, max(0, 12·FBR − SSI))`. The exclusion is applied against
Social Security alone; other unearned income would absorb it first, which
changes the fall only when (1 − c)·S is below $240 a year. The cap uses
the federal benefit rate, but the PSID's reported SSI may include a state
supplementary payment; where it does, the cap binds early and the offset
is understated (named delta, §12).

- **SSI units (builder approximation):** head and wife form one unit, a
  couple unit when both receive SSI (couple FBR) and an individual unit
  otherwise; its Social Security includes the spouse's (deeming
  approximated by full attribution; alternative `recipients_only`). All
  OFUMs together form one individual unit (PSID reports one OFUM total).
  Under 20 CFR 416.1163(d), nothing is deemed when the ineligible
  spouse's income after allocations is at most the couple-minus-individual
  FBR (2004: $846 − $564 = $282 a month), and otherwise the couple
  computation applies, capped (416.1163(e)(2)) at the benefit without
  deeming. Full attribution can therefore only overstate the offset;
  `recipients_only` errs the other way; the two bracket the rule (referee
  Q3). The cap `12·FBR_individual − SSI` is looser than the regulation's
  individual-computation cap but binds only in the no-deeming case.
- **Row U2:** no SSI response.
- **Row U3 (the largest SSI response of the three registered rules, so
  the smallest Δ):** the offset, plus take-up by every head/wife unit
  that the cut makes newly income-eligible and whose resource proxy
  `max(0, WEALTH1 − vehicles)` is within the resource limit. Countable
  income follows 20 CFR 416.1112 and 416.1124 in order: the $20 exclusion
  applies to unearned income first, then the $65 earned exclusion and half
  of the remaining earnings. Unearned income is head and wife transfer
  income other than SSI, TANF and other welfare, plus Social Security;
  asset income is left out; earned income is labor, farm and business
  labor income. A unit with a wife present is treated as a couple. OFUMs
  are never newly enrolled. Deterministic (every eligible unit takes up),
  so K stays 1. It is not a bound on DYNASIM's simulation: the referee
  notes that the resource proxy nets debts and drops every vehicle where
  20 CFR 416.1218 excludes one, and that SSI treats unmarried cohabitors
  as a couple only when they hold themselves out as married (416.1806);
  those two sections were not re-read for this draft.

SSI parameters (captured from policyengine-us revision `a03e82e503`,
`data/external/track_u_ssi_parameters.json`): FBR in force on January 1,
monthly, individual / couple — 2004 564 / 846; 2005 579 / 869; 2006 603
/ 904; 2007 623 / 934; 2008 637 / 956; 2009–2011 674 / 1,011; 2012 698 /
1,048. These equal the SSA notices "Cost-of-Living Increase and Other
Determinations" for each year: 68 FR 60437, 69 FR 62497, 70 FR 61677,
71 FR 62636, 72 FR 60703, 73 FR 64651, 74 FR 55614 and 75 FR 65696 (no
increase in 2010 or 2011), 76 FR 66111 (checked by the referee and again
for this draft on govinfo.gov, 2026-09-24; ssa.gov refuses programmatic
fetches). The $20 general exclusion applies to unearned income other
than income based on need (20 CFR 416.1124(c)(12), current text), with
any remainder applied to earnings (416.1112(c)(4), whose current text
cross-references the exclusion as "§ 416.1124(c)(10)"); then $65 and one
half of the rest of earnings (416.1112(c)(5), (c)(7)). Interest and
dividends on countable resources are excluded (416.1124(c)(22), current
text). Resource limits $2,000 / $3,000 from January 1989 (416.1205(c)).
Deeming from an ineligible spouse: 416.1163.

## 9. Statistic

For cell c, with observation weights w, baseline adjusted income B,
reform income R and threshold T (family-level under `fu_head_rule`:
every member of a family unit gets the same B, R and T):

```text
P_B[c] = 100 × Σ_{i∈c} w_i·1{B_i < T_i} / Σ_{i∈c} w_i
P_R[c] = 100 × Σ_{i∈c} w_i·1{R_i < T_i} / Σ_{i∈c} w_i
Δ[c]   = P_R[c] − P_B[c]            (percentage points)
```

Δ is the headline; P_B and P_R are the secondary rows (the Table 19 and
Table 21 analogues). Under row U4, head and wife members use the
head-and-wife basis and OFUM members the family basis, so B and T differ
by role there.

**Cells.** `all` (headline); `men`, `women`, `married`, `non_married`
(the Report's list of appendix tables includes Appendix Table 17,
"Adjusted Poverty Rates at Age 67, by Gender and Marital Status"; which
of these splits Tables 19 and 21 carry is unknown, plan §10 decision
2(b)); the four sex-by-marital cells (optional); one diagnostic cell per
birth year (not scored). Only cells present in the sealed comparator are
scored; the others are reported as "not in comparator". The cell list
freezes at registration.

**Undefined cells.** An empty cell or one with zero total weight has no
statistic; it is reported with its reason and never imputed.

**F17 diagnostics (not scored).** Two kinds, both reported for the
headline row (§11):

- *Official-concept poverty rate* for the same sample: money income
  (TOTAL FAMILY INCOME, reported asset income kept, no annuity, no cut)
  against the row's threshold, weighted per cell
  (`uniform_cut_track_u.runner.official_concept_rates`). It involves the
  threshold, so it runs only inside the registered run (and on invented
  data in the dry run), never on real data before registration.
- *Component summaries* (`uniform_cut_track_u.diagnostics`): per income
  year, the weighted share of head and wife members with their own
  Social Security, their weighted mean monthly amount set against SSA's
  December average retired-worker benefit (Annual Statistical Supplement
  2025, Table 5.A4, committed snapshot; total monthly benefits over
  number, a division made here; every age, retired workers only, December
  against a calendar-year total over twelve, unadjusted); SSI receipt,
  the mean among recipients and the recipients above twelve times the
  federal benefit rate for their unit; WEALTH1 weighted quantiles (the
  smallest value whose cumulative weight share reaches the level) and the
  shares at or below zero and imputed, with no published comparison (no
  SCF table is committed or saved); and counts of `# IN FU` against the
  individual records. These are component aggregates with no threshold,
  which plan §8 allows before registration; the module imports neither
  the income concept nor the tabulation.

## 10. Uncertainty

- **Draws:** K = 1 (deterministic).
- **Half-split floor:** seeds 0–4, fraction 0.5,
  `harness/panel.split_panel_by_person` on the split unit
  (`uniform_cut_tabulation.floor_split_units`): family units merged with
  every family unit that shares a person with them, labelled by the
  smallest `family_unit_id`. The halves are therefore disjoint in family
  units and in persons (plan F15). Under U0 each person is observed once,
  so the split units are the family units; under U1 an even birth year's
  observations at 66 and 68 sit in two waves' family units, which the
  merge keeps on one side. Each statistic is recomputed in each half; the
  floor is the mean and sample SD (ddof = 1) of |A − B| over seeds where
  both halves are defined; with fewer than two usable seeds it is
  undefined, never zero. Floors are at half sample and not rescaled.
- **Design-based SE:** Taylor linearization of each weighted ratio with
  the PSID sampling-error stratum and cluster (ER31996, ER31997), as a
  domain estimator on the full sample design (referee Q5): every
  (stratum, cluster) pair among persons with a positive cross-section
  weight in the row's observation waves enters, with z = 0 for clusters
  holding no observation of the cell (`TabulationConfig.design_se_domain
  = "full_sample_design"`, the design frame from
  `uniform_cut_track_u.runner.design_frame`). On the staged individual
  file each of the five waves has 63 strata of exactly two clusters
  among persons with a positive cross-section weight (a structural count
  made for this draft, as the referee's), so no stratum is a singleton;
  if one arises it is left out, counted and listed, and the run records
  it. The `u1-draft-3` estimator, relative to the tabulated rows only,
  dropped every stratum with one cluster present (13 of 51 under U0's
  structural counts, 16 of 59 under U1) and so understated the
  variance; it remains a code option (`tabulated_rows`), not registered.

## 10a. Comparison and acceptance

- **Comparator:** for each scored cell, the Report's change from Table 19
  to Table 21 (and, as secondary rows, the two levels), sealed on the
  comparator side and opened only after the run artifact is committed.
- **Gap:** our Δ minus the Report's Δ, in percentage points, per cell
  and registered row; likewise for P_B and P_R.
- **Comparator interval:** the Report prints rates; if each is printed to
  d decimals, each level carries ±0.5·10^−d and the printed difference
  ±10^−d. The interval appears only in the comparison memo, never in the
  run artifact.
- **Acceptance:** none by default (plan §10 decision 6, pending Max): the
  memo reports our value, floor, design SE, the comparator with its
  interval, and the gap, and declares no pass or fail. A rule, if any,
  is set by Max before registration; none may be set after. No tuning,
  no re-run; a change is a new registered version.

## 11. Registered rows

Each alternative differs from U0 in one field, except U6 (defined on U1)
and U0-F. U0 is the headline row unless the fallback rule below makes
U0-F the headline; no row may be promoted after results exist. Every
registered row is computed in the same one-shot run and published with
the others. A row that is not built when the registration is posted is
removed from this table and listed as a named omission.

**Fallback rule (pending Max, with plan §10 decision 3).** If the 2005
and 2007 wealth supplements are staged, adjudicated and read before the
#42 registration is posted, U0 is the headline and U0-F an alternative;
otherwise U0-F is the headline, and U0 and U1 are reported as blocked
with their counts. The rule depends on staging status only. In code
(`uniform_cut_track_u.runner.headline_row`), every row whose observation
waves include a wave without WEALTH1 is reported as blocked with its
counts, which under the fallback is every row except U0-F and U7: the
one-field alternatives are defined on U0 and need 1937 and 1939 too.
Whether they should instead follow the headline to U0-F's population is
not decided (§16, §17). The registration comment states the headline
row, and the registered run refuses when the staged PSID gives a
different one (`scripts/run_track_u_registered.py --headline-row`).

| Row | Field | Value | Built |
|---|---|---|---|
| **U0** | — | §§3–10 | Yes; 1937 and 1939 blocked by the wealth supplements |
| U1 | Population | All ten birth years (§3) | Yes; six observation cells (waves 2005 and 2007) blocked |
| U2 | SSI | No response | Yes |
| U3 | SSI | Full static recomputation (the largest SSI response of the three) | Yes |
| U4 | Income unit | Head and wife only | Yes |
| U5 | Asset income | Keep reported asset income and add the annuity | Yes |
| U6 | Cut (on U1) | 1936 uncut if the cut starts in 2004 (`cut_start_year = 2004`) | Yes; the start year awaits decision 8 |
| U0-F | Population | Birth years 1941, 1943, 1945 only (the blocked 1937 and 1939 left out and counted) | Yes; the fallback rule awaits Max |
| U7 | Financial assets | Plus employer DC balances | **No** (label investigation); must be built before registration or removed |
| U8 | Threshold | PSID `CENSUS NEEDS STANDARD` | Yes |
| U9 | Mortality | SSA period life table 2004 | Yes |
| U10 | Threshold | Census size-by-children matrix | Yes (needs the capture) |
| U-inst | Universe | Add institutions (sequence 51–59), family-of-record income rule (§3) | Yes; the rule awaits the freeze and a referee |

## 12. Named deltas

Carried on every output (plan §7, the referee's additions and those
found while building). Each bullet is the text of
`uniform_cut_track_u.runner.NAMED_DELTAS`, held equal by
`tests/test_boomers2004_uniform_cut_spec.py`:

- PSID versus SIPP wealth measurement;
- realized 2004-2012 history versus DYNASIM's 1992-based projection, including the 2008-09 asset shock for the 1941-45 cohorts at 67;
- realized COLAs versus 2002 Trustees assumptions;
- immigrant under-coverage; institutionalized persons (row U-inst: the family-of-record rule assigns the family's income and threshold without the member's own income, which the PSID does not collect); attrition;
- OFUM-owned assets inside family wealth;
- the family's wealth stands in for an OFUM cohort member's own wealth (the Report's unit is the individual plus spouse, p. 24);
- imputed rent excluded;
- self-reported Social Security, possibly net of Medicare Part B premiums, so the 13 percent cut applies to a smaller base than the gross benefit (baseline income is lower too; the net direction on the change is not established);
- retirement-account income beside annuitized balances: the head's income from annuities and IRAs is removed (F4a), but the wife's (before 2013) and the OFUMs' items combine pensions with annuity income and stay, so any IRA or annuity income in them is counted twice; an annuity already in payment may have no balance in WEALTH1, so removing its income understates income;
- employer DC (401(k)) balances outside IRAs are not in WEALTH1 though the Report counts them (p. 24): the primary annuity is understated for their holders (row U7);
- PSID other assets (W34) include cash value of life insurance, collections and rights in a trust or estate, which the Report's list (p. 22) does not name;
- the annuity is priced on population period life tables by age and sex (NCHS 2000; U9 SSA 2004), while DYNASIM's mortality follows the 2002 Trustees projections (p. 20, fn. 4) and the Report ties the annuity to family life expectancy (p. 24): with falling mortality, period tables overstate the annuity;
- exact-age sampling of alternate birth years (mean birth year 1941 against 1940.5);
- U1 averages ages 66 and 68, and claiming between those ages is not linear in age;
- the universe is alive at the interview after the income year;
- farm income's asset portion is imputed by the PSID business convention (farm_asset_share); business income is split 50/50 between labor and asset parts by PSID convention for working owners;
- SSI units approximated from head, wife and OFUM totals (deeming by full attribution; OFUMs as one unit);
- SSI deeming by full attribution can only overstate the offset (so understate the change): under 20 CFR 416.1163 nothing is deemed when the ineligible spouse's income is at most the couple-minus-individual FBR;
- the SSI test uses annual amounts against 12 times the January FBR (SSI accounting is monthly), and U3 omits rent and royalties from countable income although 20 CFR 416.1121 counts them;
- reported SSI may include state supplementary payments, so capping the offset at the federal benefit rate less reported SSI can understate the offset;
- U0-F, if it is the headline: mean birth year 1943 against 1940.5, and every observation year at or after the 2008-09 asset shock.

## 13. Invented worked cases

These cases are **invented** for the unit tests
(`tests/estimates/test_adjusted_poverty.py`,
`tests/estimates/test_uniform_cut_tabulation.py`,
`tests/cohorts/test_age67.py`). They use no PSID data, no Census
threshold and no comparator value. The life table, interest rate,
thresholds, federal benefit rates and family amounts are invented; the
SSI exclusions ($20 and $65 a month, one half of remaining earnings) and
resource limits ($2,000 / $3,000) are the statutory values.

Invented life table (ages 0–4): male qx 0, 0, 0.2, 0.5, 1; female qx 0,
0, 0.1, 0.25, 1; invented rate 25 percent (v = 0.8).

| Case | Hand computation | Value |
|---|---|---|
| Single life, male 2 | 0.8·0.8 + 0.4·0.64 | 0.896 |
| Single life, female 2 | 0.9·0.8 + 0.675·0.64 | 1.152 |
| Joint, 50 percent survivor | 0.5·(0.896 + 1.152) | 1.024 |
| Last survivor (s = 1) | 0.98·0.8 + 0.805·0.64 | 1.2992 |
| Entry into poverty (T = 1,000) | B = 1,050 − 50 = 1,000 (not poor); R = 1,000 − 130 = 870 (poor) | poor only after the cut |
| SSI offset, uncapped (FBR 600 a year, SSI 100, SS 1,000) | (1,000 − 240) − (870 − 240) = 130 ≤ 500 | +130 |
| SSI offset, capped (SSI 550) | min(130, 600 − 550) | +50 |
| SSI, SS under the exclusion (SS 200) | 0 − 0 | 0 |
| U3 new take-up (SS 900, no other income) | before 660 ≥ 600; after 543 < 600 | +57 |
| U6, birth year 1936 (T = 1,000, SS 1,050) | primary: R = 1,050 − 136.5 = 913.5 (poor); `cut_start_year = 2004`: 1936 + 67 = 2003 < 2004, no cut, R = 1,050 | uncut |
| U6, SSI recipient born 1936 (SS 1,000, SSI 100) | primary offset 130; uncut: no fall | 0 |
| U-inst, member in an institution attached to family 11 | family 11's income 1,000 and WEALTH1 500; role OFUM; no co-resident spouse | assigned |
| F4a, head annuity and IRA income 200 (money income 1,200) | `remove_head`: B = 1,200 − 200 = 1,000; `keep`: B = 1,200 | 1,000 / 1,200 |
| F4a, 2013 file: `HEAD ANNUITIES` 150 and `HEAD IRAS` 50 | both removed | 200 removed |
| F4b, farm income 400 | share 0.5: remove 200; share 0: remove 0 | 200 / 0 |
| F4b, farm loss −300 | share 0.5: remove −300 (income rises by 300); share 0: 0 | −300 / 0 |
| Lives, OFUM woman aged 3 in a family headed by a man aged 2 and his legal wife aged 2 (WEALTH1 1,024) | `fu_head_rule`: joint 1.024, annuity 800; `member_rule`: single female 3, 0.75·0.8 = 0.6, annuity 1,365.3 | 800 / 1,365.3 |
| Lives, female head aged 2 with a legal husband (code 90) aged 2 | joint on the head and her legal husband | 1.024 |
| Unresolved marital state, head with a legal wife in the family | `relationship_code`: married, co-resident with the wife; `non_married`: non-married, no spouse | married / non-married |
| Spouse age, birth year 1943 by marriage history, individual-file age 66 at the 2009 interview | income year 2008: `derived_birth_year` 65; `wave_age` 66 | 65 / 66 |

Invented tabulation (five observations, weights 1, 1, 2, 4, 2): P_B = 20,
P_R = 70, Δ = 50 for `all`. Design SE of Δ for `all` with the design
the rows occupy (two strata of two clusters each; stratum contributions
0.01 and 0.09): 100·√0.1. On a full design that adds a third cluster to
stratum 2 and a third stratum of two clusters, none holding an
observation: stratum 2's cluster totals become 0.2, −0.1 and 0 (mean
1/30, contribution 1.5 × 0.04667 = 0.07), stratum 3 contributes 0, and
the SE is 100·√0.08.

F17 weighted quantile (invented values 10, 20, 30, 40 with weights 1, 1,
1, 1): the median is the smallest value whose cumulative weight share
reaches 0.5, 20; p90 is 40.

## 14. What is built and what is blocked

On master since #456 (merge `8d7e7431`; built on branch
`dynamics-ex2-track-u-20260924`), continued on
`dynamics-ex2-track-u-2-20260924` (`u1-draft-3` and this draft; not
merged); all opt-in; registered in `POST_REVIEW_SOURCE_EXCLUSIONS` and
the reachability guard:

- `src/populace_dynamics/data/family_income.py`: label-verified family
  income for waves 2005–2013 (81 items a wave, 85 in 2013, including the
  raw accuracy flags of the Social Security, SSI and asset items) and
  WEALTH1 with its components for 2009–2013; refusal naming the missing
  2005 and 2007 wealth supplements; reconciliation counts.
- `src/populace_dynamics/cohorts/age67.py`: the age-67 observations for
  U0, U1 and U0-F, dispositions, the relationship-code resolution of
  unresolved marital states, the head and head's legal spouse with their
  income-year ages (the birth-year law extended to in-family heads and
  spouses), provenance seal, structural summary.
- `src/populace_dynamics/estimates/adjusted_poverty.py`: annuity prices,
  threshold lookup, SSI rules, baseline and reform income (with F4a and
  F4b), poverty status; refuses PSID-built rows without a registration.
- `src/populace_dynamics/estimates/uniform_cut_tabulation.py`: cells,
  Δ/P_B/P_R, half-split floors, design SE on the full sample design;
  refuses real data without a registration pointer.
- `scripts/capture_track_u_parameters.py` (SSI capture written; Census
  parser ready), `scripts/track_u_structure.py` (counts only).
- `src/populace_dynamics/uniform_cut_track_u/` (`u1-draft-3`, extended
  here): `rows.py` (the registered rows, held equal to §15's rows, and
  the headline rule); `invented.py` (U5: a seeded INVENTED age-67
  population in the reader shapes, the INVENTED threshold table and the
  re-generation checks; this draft adds couples resolved by relationship
  code, legal husbands, farm, annuity and IRA income, and interview ages
  that differ from income-year ages); `runner.py` (the row pipeline with
  its provenance guards, the fallback headline, the full-design SE and
  the official-concept diagnostic); `diagnostics.py` (the F17 component
  summaries).
- `scripts/track_u_dry_run.py` (U9): every row on the invented cohort
  with invented thresholds and the committed life tables and SSI
  capture, and the fallback rule on the invented cohort as staged today;
  evidence headed "INVENTED DATA - NOT A COMPARISON".
- `scripts/run_track_u_registered.py` (U10 entry point): refuses unless
  the pointer is an issue #42 comment, `HEAD` is the registered commit
  on a clean tree, §15 is ratified with nothing awaiting and nothing
  blocking, the Census capture is pinned, and `--headline-row` equals the
  fallback rule's row for the staged PSID; writes
  `runs/replication_boomers2004_uniform_cut_v1.json` and its `.env.json`
  exclusively.
- `scripts/track_u_component_diagnostics.py`: the F17 component
  summaries on the staged PSID (evidence
  `EVID/track-u-diagnostics-20260924/`). On the staged files every
  family's `# IN FU` equals its number of in-family records (sequence
  1–20) in all five waves, and none of the 389–426 families per wave
  with an attached institution record counts it in `# IN FU`: the
  reading the institution rule relies on.

Blocked:

1. **2005 and 2007 wealth supplements** (Max, simba login): U0 loses 1937
   and 1939 until staged, adjudicated and read; under the fallback rule
   U0-F is then the headline and the rows defined on U0 or U1 are
   reported as blocked.
2. **Census thresholds** (download approval, cos decision d194): no
   primary threshold until captured; the dry run uses an INVENTED table.
3. **Registration** on issue #42 after ratification; no real-data poverty
   statistic may be computed before it.
4. **Comparator coverage** of the frozen cells (comparator side, values
   redacted).
5. **Row U7** is not built (label investigation of the P-section
   employer DC items); it must be built or removed before registration.

## 15. Machine-readable parameter block

Downstream lanes read this block; `tests/test_boomers2004_uniform_cut_spec.py`
holds it to the code's defaults.

```json
{
  "specification": "boomers2004_uniform_cut_exercise2",
  "version": "u1-draft-4",
  "status": "draft_for_referee",
  "claim_class": {
    "proposed": "track_u_psid_realized_measurement_not_a_projection",
    "awaiting": "d189"
  },
  "target": {
    "report": "Butrica and Uccello (2004), How Will Boomers Fare at Retirement?, AARP PPI #2004-05",
    "tables": ["19", "21"],
    "birth_years": [1936, 1945],
    "age": 67,
    "cut_rate": 0.13,
    "unit": "individual_with_household_income_and_wealth_including_spouse",
    "financial_assets": "non_pension_wealth_plus_ira_keogh_401k_balances",
    "comparator_values": "sealed_comparator_side_not_opened_by_builder"
  },
  "population": {
    "primary_row": "U0",
    "headline": {
      "rule": "u0_if_2005_2007_wealth_staged_before_registration_else_u0f",
      "fallback_row": "U0-F",
      "awaiting": "Max (fallback rule, with plan section 10 decision 3)"
    },
    "primary_birth_years": [1937, 1939, 1941, 1943, 1945],
    "fallback_birth_years": [1941, 1943, 1945],
    "u1_birth_years": [1936, 1945],
    "u1_even_birth_year_weight": 0.5,
    "u1_single_observation_weight": 1.0,
    "waves": {
      "2005": {"income_year": 2004, "weight": "ER33849", "family_unit_id": "ER33801", "wealth1": null},
      "2007": {"income_year": 2006, "weight": "ER33951", "family_unit_id": "ER33901", "wealth1": null},
      "2009": {"income_year": 2008, "weight": "ER34046", "family_unit_id": "ER34001", "wealth1": "ER46968"},
      "2011": {"income_year": 2010, "weight": "ER34155", "family_unit_id": "ER34101", "wealth1": "ER52392"},
      "2013": {"income_year": 2012, "weight": "ER34269", "family_unit_id": "ER34201", "wealth1": "ER58209"}
    },
    "presence": "in_family",
    "birth_year_law": "estimates.career.derive_birth_years",
    "seed_wave_rule": "earliest_presence_wave",
    "separated_is_married": true,
    "unresolved_marital_status": "relationship_code",
    "annuitant_age_source": "derived_birth_year",
    "institution_income_rule": "family_of_record",
    "design": {"stratum": "ER31996", "cluster": "ER31997"}
  },
  "income_concept": {
    "income_unit": "family_unit",
    "money_income": "TOTAL FAMILY INCOME",
    "asset_income_rule": "replace",
    "asset_income_items": [
      "head_rent", "head_dividends", "head_interest", "head_trusts",
      "head_business_asset", "wife_rent", "wife_dividends",
      "wife_interest", "wife_trusts", "wife_business_asset", "ofum_asset"
    ],
    "retirement_account_income_rule": "remove_head",
    "retirement_account_income_items": ["head_annuities", "head_iras"],
    "farm_asset_share": 0.5,
    "farm_loss": "removed_whole_when_share_positive",
    "financial_assets": "WEALTH1",
    "annuitized_share": 0.8,
    "annuity": {
      "real_interest_rate": 0.03,
      "timing": "immediate",
      "load": 0.0,
      "survivor_share": 0.5,
      "mortality_basis": "nchs_2000",
      "terminal_closure": "table_end",
      "lives": "fu_head_rule",
      "negative_wealth": "annuity_floored_at_zero"
    },
    "sensitivities_unscored": {"real_interest_rate": [0.02]}
  },
  "threshold": {
    "rule": "census_weighted_average_65plus",
    "years": [2004, 2012],
    "values": "weighted_averages_as_printed_in_thresh_workbooks",
    "capture_status": "not_captured",
    "poor_if": "income_below_threshold"
  },
  "cut": {
    "rate": 0.13,
    "base": "all_social_security_of_the_unit",
    "behavior": "none",
    "start_year": null,
    "start_year_rule": "cut_when_birth_year_plus_67_at_or_after_start"
  },
  "ssi": {
    "rule": "offset_existing_recipients",
    "awaiting": "d189",
    "deeming": "spouse_social_security_counted",
    "ofum_unit": "single_individual",
    "parameters": {
      "file": "data/external/track_u_ssi_parameters.json",
      "sha256": "79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523",
      "checked_against": "federal_register_cola_notices_2003_2011"
    }
  },
  "statistic": {
    "headline": "delta",
    "secondary": ["baseline_rate", "reform_rate"],
    "unit": "percentage_points"
  },
  "cells": {
    "scored_candidates": ["all", "men", "women", "married", "non_married"],
    "optional": ["men_married", "men_non_married", "women_married", "women_non_married"],
    "diagnostic": "birth_year",
    "source": "appendix_table_17_title_by_gender_and_marital_status",
    "scored_only_if_in_comparator": true
  },
  "uncertainty": {
    "draws": 1,
    "floor": {
      "seeds": [0, 1, 2, 3, 4],
      "fraction": 0.5,
      "split_unit": "family_unit_id_linked_by_person_id",
      "summary": ["mean", "sample_sd"],
      "min_usable_seeds": 2
    },
    "design_se": {
      "method": "taylor_linearization",
      "domain": "full_sample_design",
      "outside_cell": "zero",
      "singleton_strata": "excluded_counted_and_listed"
    }
  },
  "comparison": {
    "gap": "model_minus_report",
    "comparator_interval": "display_rounding",
    "acceptance": {"rule": null, "awaiting": "Max (plan section 10 decision 6)"}
  },
  "rows": {
    "U0": {},
    "U1": {"population": "all_ten_birth_years"},
    "U2": {"ssi_rule": "none"},
    "U3": {"ssi_rule": "full_static_recomputation"},
    "U4": {"income_unit": "head_wife"},
    "U5": {"asset_income_rule": "keep"},
    "U6": {"on": "U1", "cut_start_year": 2004, "awaiting": "plan section 10 decision 8"},
    "U0-F": {"population": "birth_years_1941_1943_1945", "on": "U0", "awaiting": "Max (fallback rule, with plan section 10 decision 3)"},
    "U7": {"financial_assets": "wealth1_plus_employer_dc", "status": "not_built"},
    "U8": {"threshold_rule": "psid_census_needs_standard"},
    "U9": {"mortality_basis": "ssa_period_2004"},
    "U10": {"threshold_rule": "census_matrix_65plus"},
    "U-inst": {"presence": "in_family_or_institution", "institution_income_rule": "family_of_record", "awaiting": "specification freeze (rule not yet refereed)"}
  },
  "diagnostics_f17": {
    "row": "headline",
    "official_concept_poverty_rate": "registered_run_only",
    "components": ["social_security", "ssi", "wealth1", "fu_size_record_counts"],
    "social_security_published": "ssa_supplement_2025_table_5a4_december_retired_workers",
    "ssi_published": "federal_benefit_rate_capture_only",
    "wealth1_published": null
  },
  "entry_points": {
    "dry_run": "scripts/track_u_dry_run.py",
    "registered_run": "scripts/run_track_u_registered.py",
    "registered_artifact": "runs/replication_boomers2004_uniform_cut_v1.json",
    "component_diagnostics": "scripts/track_u_component_diagnostics.py"
  },
  "acceptance_rule": null,
  "labels": [
    "PSID-realized outcomes (not a projection)",
    "Python income concept (not Axiom)",
    "mechanical incidence"
  ],
  "referee_passes": [
    {
      "report": "EVID/boomers2004-referee-20260924.md",
      "sha256": "b083fb2638787c204d09324a16fbbc5fa09cfc191e0450bcadb7d44f1647b2b6",
      "object_version": "u1-draft-2",
      "object_commit": "8d7e7431",
      "verdict": "revise_before_ratification",
      "required_changes": 17,
      "applied_in": "u1-draft-4"
    }
  ],
  "blocked_by": [
    "psid_2005_2007_wealth_supplements_not_staged",
    "census_thresholds_not_captured",
    "issue_42_registration_absent",
    "max_ruling_d189_open",
    "row_u7_not_built"
  ]
}
```

## 16. Pending decisions

None of these is ratified. Each is a code parameter whose default is the
plan's proposal, the referee's recommendation or a builder choice where
both are silent; `adjusted_poverty.pending_decisions()` and
`age67.pending_decisions()` return them with their basis.

**Awaiting Max (d189, open):**

1. Claim class: accept Track U as exercise 2's first score (plan §10,
   decision 1).
2. SSI rule F13: offset for existing recipients (default), no response
   (U2) or full recomputation (U3) (plan §10, decision 5).
3. Download the 2005 and 2007 PSID wealth supplements (plan §10,
   decision 3).

d189's text describes Track U as a "Python income concept, not Axiom",
so a yes on d189 may be read as covering plan decision 4; confirm when
ruling.

**Awaiting Max, not yet on a decision card (plan §10):** decision 2 (a
values-redacted definitions extract by the comparator side), decision 4
(Python SSI arithmetic labelled "not Axiom"), decision 6 (acceptance rule;
default none, report gaps, §10a), decision 7 (ratify this specification
by merge; post the #42 registration), decision 8 (the scorecard's "from
2004": row U6 is built with `cut_start_year = 2004`, and the primary's
`cut_start_year = None` cuts every observation), approval to download the
Census threshold files (cos decision d194), and the fallback rule of §11
(with decision 3), including whether the one-field alternatives follow
the headline to U0-F's population when the supplements are not staged
(default: they stay on U0 and are reported as blocked).

**Awaiting the specification freeze (defaults shown):** cut rate (0.13;
the code lists it), cut base (all Social Security of the unit; not a code
parameter, decision 2(a)), cut start year (none), income unit (family
unit), asset-income rule (replace), retirement-account income (remove
the head's), farm asset share (0.5 of positive income, whole loss),
annuitized share (0.8), real rate (3 percent; 2 percent sensitivity),
timing (immediate), load (0), survivor share (0.5, reduced on either
death), mortality (NCHS 2000), terminal closure (table end), annuity
lives (FU head rule), annuitant ages (derived birth year), negative
wealth (floor at zero), financial assets (WEALTH1; U7 pending), threshold
rule (weighted average, 65-and-over; weighted averages as printed in
`threshYY.xlsx`), SSI deeming (spouse's Social Security counted), OFUM
SSI unit (one individual unit), row (U0, with the U0-F fallback rule),
presence (in family), separated is married (true), unresolved marital
status (relationship code), U1 1936 weight (1: each birth year then
carries one cross-section's weight), seed wave (earliest presence wave),
design SE (full-design domain), cells (after decision 2(b)), and the
institution income rule (`institution_income_rule = family_of_record`;
alternative `excluded`; only row U-inst reads it, and no referee has
reviewed it yet).

A registered run refuses a §15 block that still names anything as
`awaiting`, so ratification must resolve each of these (and the code's
rows must be updated to match, `uniform_cut_track_u.rows`).

## 17. Referee record and open questions

### 17.1 First pass (applied in `u1-draft-4`)

- **Report:** `EVID/boomers2004-referee-20260924.md`, SHA-256
  `b083fb2638787c204d09324a16fbbc5fa09cfc191e0450bcadb7d44f1647b2b6`
  (independent referee lane, Claude Opus 5.5, 2026-09-24).
- **Object:** `u1-draft-2` on `origin/master` at `8d7e7431`, blob
  SHA-256 `3c0fc80d…6004f3d` (checked for this draft). The referee did
  not see `u1-draft-3` (row U-inst's income rule, row U6, the invented
  generator, the dry run and the registered entry point), which the
  continuation branch had added the same day; its R11 and R16 are read
  against that.
- **Verdict:** revise before ratification; 17 required changes (R1–R17),
  8 optional suggestions (O1–O8), answers to the draft's questions 1–8.
- **Version:** the referee asked for `u1-draft-3`; that number was
  already taken on the continuation branch, so this pass is `u1-draft-4`.

Each required change was checked against its source before it was
applied: the Report's pp. 19–24 and lists of tables; the PSID codebooks
and setup files; the eCFR current text of 20 CFR 416.1112, 416.1121,
416.1124, 416.1163 and 416.1205; the nine Federal Register notices;
the committed life tables (every price recomputed with the code); a
design-structure count on the staged individual file; and the
structural-count evidence.

| Change | Disposition |
|---|---|
| R1 (§1 unit, financial assets; cells) | Applied. Verified on pp. 19, 22–24 and the list of appendix tables. Two wording corrections: the retirement-account sentence is in p. 24's text, with fn. 11 listing the Census sources; home equity is "projected separately" (p. 23) and not among the financial assets (pp. 22, 24), rather than "excluded" by p. 23 |
| R2 (builder boundary) | Applied, and extended: this draft read the Report's cleared pages itself, and says so |
| R3 (head's annuity and IRA income) | Applied as F4a (`retirement_account_income_rule`, default `remove_head`) with code, JSON and tests. Verified: `HEAD ANNUITIES` is "Head's Income from Annuities and IRAs" in the 2005–2011 codebooks, split in 2013. Corrected: the wife's pre-2013 item is labelled "Income from Pensions and Annuities" and the OFUMs' "Other Retirement, Pensions, and Annuities"; neither label names IRAs, so where a wife's IRA income is recorded before 2013 is not established. Added: an annuity in payment may have no WEALTH1 balance, so removing its income can understate income (named delta) |
| R4 (farm asset share) | Applied as F4b (`farm_asset_share`, default 0.5; a loss is removed whole when the share is positive). Verified on ER52214, ER52216 and p. 22 |
| R5 (401(k), U7) | Applied (text, named deltas, §11: U7 must be built or removed before registration; `blocked_by`) |
| R6 (real rate, administrative costs) | Applied. Verified on p. 22; the 2 percent prices recomputed with the code and the SSA 2004 prices added; `real_interest_rate` lists 0.02 |
| R7 (annuity lives) | Applied: `fu_head_rule` is the default, B, R and T are family-level. Extended: the head's legal spouse includes a legal husband (code 90, "Legal husband of Head", verified in the 2005–2013 formats; 10–15 in-family records a wave on the whole staged file, a structural count), who R7's text ("legal wife") would have left out |
| R8 (annuitant ages) | Applied (`annuitant_age_source`, default `derived_birth_year`). Verified in `estimates.career.derive_birth_years`. The extension runs the law without a required population, so a conflicting marriage-history birth year leaves the person unresolved (wave age, counted) rather than failing the build |
| R9 (unresolved marital state) | Applied (`unresolved_marital_status`, default `relationship_code`), symmetric for a head with a legal husband; institutionalized members are not resolved by code; the marital pairs indicator is not used |
| R10 (design SE) | Applied (`design_se_domain = "full_sample_design"`, the runner's design frame). Verified: 63 strata of exactly two clusters in each of the five waves among positive-weight persons |
| R11 (rows) | Applied in part. U0-F and the fallback rule are registered and built; U6 is built (since `u1-draft-3`); U7 must be built before registration or removed. **Declined:** replacing row U-inst by a count and `"institutionalized": "counted_only_not_a_row"`. The referee's reason was that U-inst had no income rule; `u1-draft-3` gave it one (`family_of_record`, §3), so it is a computable row. It stays registered, pending the freeze, with the rule flagged as not refereed (question 9). The fallback leaves the one-field alternatives blocked with U0; whether they should follow the headline is put to Max (§16) |
| R12 (comparison and acceptance) | Applied as §10a. The JSON nests the pending acceptance rule as `comparison.acceptance.awaiting`, which the registered run's `awaiting` scan sees, instead of a flat `acceptance_rule_awaiting` key, which it would not |
| R13 (named deltas) | Applied, all five |
| R14 (SSI sources) | Applied. The nine FBR notices and the CFR paragraphs re-checked for this draft (govinfo.gov, eCFR); 416.1112(c)(4)'s current text cross-references the exclusion as 416.1124(c)(10), which now sits at (c)(12); the resource limits are 416.1205(c) |
| R15 (§13) | Applied, with a full-design case that adds clusters holding no observation |
| R16 (§14 status and blockers) | Applied as adapted: the registered runner and dry run exist since `u1-draft-3`, so the referee's blocker 5 no longer applies; U7 is the remaining unbuilt row |
| R17 (pending decisions, tests, version) | Applied; the spec test now holds `cut`, `statistic`, `threshold.years`, `comparison`, the new fields, `rows.U0-F` and the named deltas to the code |

| Suggestion | Disposition |
|---|---|
| O1 (416.1163 deeming threshold) | Not adopted in this draft. 416.1163(a)–(d) deems the ineligible spouse's earned and unearned income after the exclusions of 416.1161(a) and allocations for ineligible children; the suggested test counts only Social Security and other unearned income, and 416.1161(a) was not read. Full attribution and `recipients_only` still bracket the rule (§8) |
| O2 (weighted-average vintage) | Applied (§6), as the referee's reading of the Census page |
| O3 (U10 related children) | Applied (§6) |
| O4 (U3 wording) | Applied (§8, §11), citing 416.1218 and 416.1806 as the referee's reading |
| O5 (co-resident family size) | Not adopted, as the referee advised, until the definitions extract settles it |
| O6 (further named deltas) | Applied: alive at the interview, U1's 66/68 average, and the Part B base (with the caveat that the net direction on the change is not established) |
| O7 (page 25 governance note) | For the orchestrator, not the builder: the table of contents lists Section IV at p. 25 and the Sample Criteria subsection continues onto p. 25 (checked); `RESTRICTED-FILES.md` should say whether p. 25 is readable |
| O8 (brief names the version) | Noted: this pass's brief named `u1-draft-2` as the version to bump to, though the branch carried `u1-draft-3` |

The referee's answers to questions 1–8 are adopted: Q1 `fu_head_rule`
(R7); Q2 yes, as F4b (R4); Q3 full attribution as the default with its
direction stated (§8, §12); Q4 weight 1 (§3); Q5 the full design (R10);
Q6 register U0-F (R11); Q7 the relationship code (R9); Q8 derived
birth years (R8).

### 17.2 Questions for the next pass

9. Is `family_of_record` the right income rule for institutionalized
   members under U-inst (their family's income, annuity and threshold,
   without their own income, which the PSID does not collect), or should
   they be `excluded` from the universe, or get a rule not built here
   (for example a one-person unit)?
10. Row U6 keys the cut on the year the member turns 67, not on the
    income year observed (U1 observes 1936 at 68, in 2004). Is that the
    reading the plan's "the 1936 cohort unaffected" intends?
11. Is extending the head's legal spouse to code 90 (legal husband), in
    the annuity and in the relationship-code resolution, right, given
    that the family file's "wife" items' treatment of a code-90 husband
    was not checked?
12. Under the fallback rule, should the one-field alternatives follow the
    headline to U0-F's population (so that U2–U5 and U8–U10 are computed
    when the supplements are not staged), or stay on U0 and be reported
    as blocked (the default)?
13. The birth-year law extension leaves a person with conflicting
    marriage-history birth years unresolved and falls back to the wave
    age. Is that acceptable, or should the build fail closed as the law
    does for its required population?
14. F4a removes the head's annuity income, including annuities already
    in payment that may carry no WEALTH1 balance. Should the rule remove
    only `HEAD IRAS` in 2013 and keep `HEAD ANNUITIES` (not possible
    before 2013, where the item combines both)?

## 18. What this draft read and did not verify

**Read:** the plan in full; the cos records of d188 and d189 (their
text only); the repository code it builds on
(`data/social_security_income.py`, `data/family.py`, `data/psid.py`,
`cohorts/psid2010.py`, `estimates/cola_age_profile.py`,
`cola_track_a/statutory.py`, the exercise-1 specification and its test,
the birth-evidence guard); PSID setup-file labels for the 2005–2013
family files and `IND2023ER.sps`; the family codebook entries for the
variables it reads (these print PSID's unweighted frequency counts and
ranges, which were not used); the `IND2023ER_formats.sas` relationship
codes; the 2005, 2007 and 2009 family-file documentation on wealth; the
policyengine-us SSI parameter files; the Census historical thresholds
page's link list.

`u1-draft-3` also read: the PSID 2011 User Guide §2.4 (sample
following rules), the individual-file codebook entries for ER34102,
ER34103 and ER34137–ER34143, the 2011 family codebook entry for `# IN
FU`, the family-file record-count text quoted in
`data/psid_unit_predicate_authority.py`, the cos record of d194 (its
text only), and Table 5.A4 of the committed SSA supplement snapshot.

`u1-draft-4` also read: the referee report in full; the plan's §§2, 3,
7, 10, 13 and 14 again; `estimates.career.derive_birth_years`; relationship
code 90 in `IND2023ER_formats.sas` for 2005–2013; the Report's PDF
pages 5–7 and 20–25 (printed pp. 4–6 and 19–24); the family codebook
entries for `HEAD ANNUITIES` (2005–2013), `HEAD IRAS`, `WIFE ANNUITIES`
and `WIFE IRAS` (2013), `WIFE RETIREMENT/ANNUITIES` (2005, 2009, 2011),
`OTHER FU MEMBR RETIREMENT/ANNUITIES` (2005, 2011, 2013), ER52214,
ER52216, ER52217, ER52368, ER52392, and the W21 and W33 question text
(2011; their printed whole-sample counts were seen and not used); the
eCFR current text of 20 CFR 416.1112, 416.1121, 416.1124, 416.1163 and
416.1205; and the nine Federal Register notices of §8, fetched from
govinfo.gov into the session scratch directory to be read (not committed).

**Ran on staged PSID:** label verification, the component-identity
reconciliation counts and the structural counts of §3, the F17 component
summaries of §9 for row U0 (`u1-draft-3`), and (`u1-draft-4`) a design
count (strata and clusters among positive-weight persons per wave) and a
count of in-family code-90 records per wave. No income concept,
annuity, threshold assignment, poverty status or poverty rate was
computed on PSID data.

**Did not verify:** why OFUM taxable income differs from OFUM labor
plus asset income by more than $10 in 21 families (2005), 34 (2007) and
4 (2013) (the OFUM items enter the primary only through TOTAL FAMILY
INCOME and the OFUM asset total); the Census threshold values and the
real layout of the Census spreadsheets; the effective date of 20 CFR
416.1124(c)(22) for 2004–2012; 20 CFR 416.1161, 416.1218 and 416.1806;
the names, IDs and contents of the 2005 and 2007 wealth supplements;
whether PSID Social Security amounts are net of Medicare premiums;
whether SSI and Social Security are kept apart by respondents; where a
wife's IRA income is recorded before 2013; how the family file records a
code-90 legal husband's income; the P-section DC items for U7; the
coverage of the sealed comparator; anything in the Report on printed
page 25 or later; whether an institutionalized member's income enters
any family-file item (no documentation found that it does); DYNASIM's
actual annuity rate, mortality and survivor conventions beyond pp. 19–24;
the domain-estimation citation the referee gives (West, Berglund and
Heeringa 2008); any SCF wealth aggregate (none is committed or saved).

## 19. Changelog

- `u1-draft-4` (2026-09-24, first referee pass applied, §17): §1 states
  the Report's unit and financial-asset definition from pp. 19–24 and
  re-sources the cells to Appendix Table 17's title; F4a removes the
  head's annuity and IRA income and F4b imputes farm income's asset part
  (new parameters); the annuity prices the family head and the head's
  legal spouse (`fu_head_rule`, code 90 included) at income-year ages
  from derived birth years (`annuitant_age_source`); unresolved marital
  states are resolved by relationship code; the design SE is a domain
  estimator on the full sample design; row U0-F and the fallback rule are
  registered and built, with blocked rows reported with their counts and
  a `--headline-row` guard on the registered run; §10a (comparison and
  acceptance) is new; the named deltas gain the referee's and are held
  equal to the code; the SSI sources cite the Federal Register and eCFR;
  the invented generator adds couples resolved by relationship code,
  legal husbands, farm, annuity and IRA income, and interview ages; §15
  gains `referee_passes`, `comparison`, the headline rule and the new
  fields; §17 records the pass and the open questions.
- `u1-draft-3` (2026-09-24, continuation on
  `dynamics-ex2-track-u-2-20260924`): row U-inst gets an income rule
  (`family_of_record`) and row U6 is built (`cut_start_year`, the start
  year pending decision 8); the invented generator (U5), the dry run
  (U9), the registered entry point (U10) and the F17 component
  diagnostics are added; §15 gains `institution_income_rule`, the cut's
  `start_year`, the F17 block and the entry points, and U6 and U-inst
  record what they await; referee questions 9 and 10 are added.
- `u1-draft-2` (2026-09-24, independent review): the half-split floor
  splits on family units linked through shared persons, so it is
  person-disjoint under U1 as plan F15 requires (U0 is unchanged); the
  income concept and the tabulation refuse `registered_real` on rows not
  built from recorded PSID files; the unresolved-marital-status rule is a
  named, pending parameter; the state-supplement delta and referee
  questions 7 and 8 are added.
- `u1-draft-1` (2026-09-24): first draft, with the Track U readers,
  builder, income concept and tabulation on branch
  `dynamics-ex2-track-u-20260924` (commit `487c1aac`); structural counts
  in `EVID/track-u-structure-20260924/`.
