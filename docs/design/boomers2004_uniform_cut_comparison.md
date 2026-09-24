# Boomers 2004 uniform cut comparison: specification for DynaSim scorecard exercise 2

- **Status:** draft for the referee. Nothing here is ratified. Max has not
  ruled on exercise 2 (cos decision d189, open, default "yes to Track U
  with the proposed SSI rule; downloads needed from Max"). Every choice
  that awaits him or the specification freeze is an explicit parameter in
  the code with the plan's recommended default, and §16 lists them.
- **Specification:** `boomers2004_uniform_cut_exercise2`, version
  `u1-draft-1`, drafted 2026-09-24. §19 is the changelog.
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
- **Builder boundary:** a model-builder lane wrote this draft. It did not
  open the Report PDF (`REFS/900767-how-will-boomers-fare.pdf`), any
  results table of the Report, the exercise-2 or COLA comparator
  directories, any comparator seal or reconciliation file, the Track A
  comparison memo, the issue #42 result comments, or page 3 / Figure 2 of
  the Urban 2010 report. Every statement below about the Report is the
  plan's reading of its methods section (plan §2), cited as "plan §2".
  §18 lists what this draft read and what it did not verify.

## 1. Target

The target is the adjusted poverty rate at age 67 in Butrica and
Uccello, *How Will Boomers Fare at Retirement?* (AARP Public Policy
Institute #2004-05, May 2004), as the plan reads its methods and list of
tables (plan §2):

- **Tables:** 19, "Adjusted Poverty Rates at Age 67", and 21, "Adjusted
  Poverty Rates at Age 67, Assuming 13 Percent Reduction in Social
  Security Benefits". The comparator is the change from Table 19 to
  Table 21. Which rows those tables carry is unknown to this builder
  (plan §2 and §10, decision 2(b)).
- **Cohort:** persons born 1936–1945 ("near-retirees"), each analysed in
  the year they reach 67.
- **Model:** DYNASIM, from the 1990–93 SIPP, with the intermediate
  assumptions of the 2002 Trustees Report.
- **Income concept:** the Report's concept differs from Census money
  income: it imputes income from financial assets as the real annuity
  that 80 percent of financial assets would buy, with a 50 percent
  survivor annuity for couples (plan §2, citing Report p. 24 and fn. 10).
- **Threshold:** official Census poverty thresholds, "65-and-over"
  (plan §2, citing Report p. 24).
- **Cut:** a 13 percent reduction in Social Security benefits (plan §2,
  citing Report p. 22). Its start year, coverage, SSI treatment and any
  behavioural response are not in the methods section (plan §2 and §10,
  decisions 2 and 8).

The comparator values are sealed on the comparator side. This builder
has not seen them and does not know which cells they cover.

## 2. Sources

| Source | Use | Status |
|---|---|---|
| Plan, `critical-path-uniform-cut-20260923.md` | Every field proposal (§7), the Report's methods as the plan read them (§2) | Read in full |
| PSID family files 2005–2013 (`psid-data/family/<wave>/FAM<wave>ER.*`) | Family income components, Social Security, SSI, asset income, FU composition, PSID's needs standard; WEALTH1 in 2009–2013 | Staged; labels verified by `data/family_income.py` |
| PSID wealth supplements 2005 and 2007 | WEALTH1 for the 1937 and 1939 birth years (U0) and six U1 observation cells | **Not staged.** The reader refuses with the missing files named (§3) |
| PSID cross-year individual file (`ind2023er`) | Anchors per wave, cross-section weights, relationship to head, age, sampling-error stratum and cluster | Staged; labels verified by `cohorts/age67.py` |
| PSID marriage history (`mh85_23`) and earnings panel | Birth-year law and marital status | Existing readers |
| NCHS United States Life Tables, 2000 | Annuity mortality (F8) | Committed, `data/external/nchs_life_tables_2000.json`, SHA-256 pinned |
| SSA period life table for 2004 (2008 vintage) | Row U9 | Committed, `data/external/tr2008/ssa_2008_vintage.json` |
| SSI federal benefit rates 2004–2012, exclusions, resource limits | SSI response (F13) | Captured from policyengine-us revision `a03e82e503`: `data/external/track_u_ssi_parameters.json`, SHA-256 `79e641a1…3c523` |
| Census poverty thresholds 2004–2012 | Threshold (F10) | **Not captured** (§6) |

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
aggregates only, plan §3) with weight 1. The weight for 1936 is a builder
choice: the plan says only "1936 from 2004 only".

**Universe per wave (F2).** Sequence 1–20 (in a responding family) and a
positive core/immigrant cross-section weight. The cross-section weight
is also positive for movers-out (71–80) and decedents (81–89); neither
option admits them and the dispositions count them. Registered option
U-inst adds sequence 51–59 (institutions); institutionalized persons have
no family-file income and the plan gives them no income rule, so the
builder marks those observations `income_rule_missing` and no income
concept can be computed for them.

**Birth year.** `estimates.career.derive_birth_years` (the first-estimates
§3.1 law, as Track A uses), total over the union of the five waves'
universes. The law's seed coordinate (clause 3) is taken from the
earliest of the five waves in which the person is present (builder
choice; the plan names the law but not the seed wave).

**Weight.** The cross-section weight of the wave that reports the income
year, times the U1 multiplier. No reweighting or alignment.

**Family unit.** The wave's interview number
(`family_unit_id = wave × 100000 + interview`). The half-split floor
splits on it (§10).

**Attached per observation** (`cohorts/age67.build_age67_cohort`): sex
(ER32000 through the death-record reader), relationship to head (10
head, 20 legal wife, 22 cohabiting "wife", otherwise OFUM; the codes are
verified in `IND2023ER_formats.sas` for each wave), marital status at the
end of the income year from the marriage history (F12; separated counts
as married), whether a legal spouse lives in the same family unit, the
spouse's age and sex, whether the family has a legal wife, and the
sampling-error stratum and cluster (ER31996, ER31997).

**Structural counts** (staged PSID, counts only; `scripts/track_u_structure.py`,
evidence `EVID/track-u-structure-20260924/`):

| Row | Observations | Persons | Computable now | Blocked by the 2005/2007 wealth supplements |
|---|---|---|---|---|
| U0 | 483 | 483 | 320 (1941, 1943, 1945) | 163 (1937: 81; 1939: 82) |
| U1 | 1,349 | 970 | 857 | 492 |

U0 by birth year: 1937 81, 1939 82, 1941 93, 1943 116, 1945 111
observations. The rest of each birth year's universe persons were not
present at the observation wave (sequence 0, moved out or died); the
evidence file lists every disposition. No income, threshold or poverty
status was computed.

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
OFUM total asset income. Row U5: keep reported asset income and add the
annuity.

Finding while building the reader: `LABOR INCOME OF HEAD` and `OF WIFE`
exclude farm income and the labor part of business income. Head and wife
taxable income equals labor income plus farm income plus the head's and
wife's labor part of business income plus the ten asset items, exactly
for every family in 2007, 2011 and 2013, within $10 in 2009, and for all
but two 2005 families. The codebook says farm income "includes both labor
and asset portions"; its asset portion is not separated, so the primary
does not replace it (named delta, §12). The PSID splits a working owner's
business income equally between labor and asset parts (codebook text);
the asset part is what F4 removes.

**Financial assets (F5).** The family unit's WEALTH1, "IMP WEALTH W/O
EQUITY": the codebooks define it as seven asset values (farm or business,
checking and savings, other real estate, stocks, vehicles, other assets,
IRAs and annuities) net of debts (2009: one "other debt" item; 2011: five
debt types; 2013: farm/business and real-estate debt split out plus six
debt types). On the staged files the component identity holds exactly
for every family in 2009, 2011 and 2013. Row U7 (employer DC balances
outside IRAs) needs a label investigation and is not built.

## 5. Annuity

- **Amount:** `0.8 × max(WEALTH1, 0) / price` (F6, F9).
- **Price** of a real level annuity of 1 per year, annuity-immediate,
  3 percent real, no load (F7): single life
  `a_x = Σ_{t≥1} v^t ₜp_x`; joint and 50 percent survivor, paying 1
  while both live and 0.5 to the survivor, with independent lives:
  `Σ_{t≥1} v^t (s·ₜp_x + s·ₜp_y + (1 − 2s)·ₜp_x·ₜp_y)`, which is
  `0.5·(a_x + a_y)` at s = 0.5.
- **Lives (F6 as written, `annuity_lives="member_rule"`):** joint on the
  member and a co-resident legal spouse if the member is married; single
  life on the member's age and sex otherwise. The plan does not say whose
  lives price an OFUM member's family wealth; the alternative
  `fu_head_rule` prices on the family head and a co-resident legal wife.
  Ages: the member's income-year age (income year − birth year); the
  spouse's individual-file age at the wave, which the repository's
  birth-year law treats as the income-year age.
- **Mortality (F8):** NCHS 2000 by sex. Survival stops with the table:
  the open interval "100 years and over" (qx = 1) is treated as death
  within the year at 100 (builder choice). Row U9: the SSA period life
  table for 2004 (ages 0–119).
- **Negative WEALTH1 (F9):** buys no annuity and is not subtracted.

Annuity prices computed by this draft from the committed tables (3
percent, immediate; not PSID data, not comparator values):

| Age | NCHS 2000 male | NCHS 2000 female | SSA 2004 male | SSA 2004 female |
|---|---|---|---|---|
| 66 | 11.3375 | 13.0092 | 11.6068 | 13.2336 |
| 67 | 10.9353 | 12.5868 | 11.1936 | 12.8042 |
| 68 | 10.5344 | 12.1622 | 10.7802 | 12.3725 |

Joint and 50 percent survivor, male 67 and female 67: 11.7610 (NCHS
2000), 11.9989 (SSA 2004).

## 6. Thresholds

**Primary (F10):** the Census weighted-average poverty threshold of the
income year for the unit's size, using the "65 years and over" rows for
sizes 1 and 2 whatever the householder's age (the Report uses the
65-and-over threshold, plan §2); sizes 3 to 8 by size; 9 or more share one
row. Poor means income below the threshold.

**Row U10:** the Census size-by-related-children matrix, with the
householder-65-and-over rows for sizes 1 and 2; PSID `# CHILDREN IN FU`
(persons under 18 other than head and wife) stands in for related
children. **Row U8:** PSID's `CENSUS NEEDS STANDARD-<income year>`, which
the codebook describes as the Census matrix threshold by family size,
number under 18 and householder age, adjusted for composition changes
during the year (householder age, not the 65-and-over rule).

**Capture status: not captured.** The Census historical thresholds page
lists one spreadsheet per year, `thresh04.xlsx` … `thresh12.xlsx`, under
`https://www2.census.gov/programs-surveys/cps/tables/time-series/historical-poverty-thresholds/`.
This builder read that page's link list and did not download the files
(downloads need Max's approval in this environment). Once the nine files
are staged in a directory, `scripts/capture_track_u_parameters.py
--census-dir DIR` parses them by their printed labels, checks that the
65-and-over rows sit below the under-65 rows and that thresholds rise with
size, records each file's URL, bytes and SHA-256, and writes
`data/external/census_poverty_thresholds_2004_2012.json`; the pin
`adjusted_poverty.THRESHOLDS_SHA256` must then be set. The parser has run
only on invented workbooks; the first real capture must be checked by eye.
Until then `load_poverty_thresholds` refuses and no primary threshold can
be assigned.

## 7. The cut

**Primary (F11):** reform income subtracts 13 percent of all Social
Security income of the unit (head, wife and OFUM amounts under the family
basis) in the income year. No behavioural response. Every U0 income year
is 2004 or later, so the unread start year matters only for U1's 1936
row: row U6 (on U1) leaves 1936 uncut if the cut starts in 2004. The
scorecard's "from 2004" has no source this builder could read (plan §10,
decision 8).

## 8. SSI response

**Primary (F13, pending Max, d189): offset for existing recipients.** For
each SSI unit with baseline SSI, SSI rises by the fall in countable Social
Security income, capped so SSI does not exceed the federal benefit rate
(FBR); nobody newly enrols. With a cut rate c and the $20 monthly general
exclusion (G = $240 a year), the fall is
`max(0, S − G) − max(0, (1 − c)·S − G)` and the rise is
`min(fall, max(0, 12·FBR − SSI))`. The exclusion is applied against
Social Security alone; other unearned income would absorb it first, which
changes the fall only when (1 − c)·S is below $240 a year.

- **SSI units (builder approximation):** head and wife form one unit, a
  couple unit when both receive SSI (couple FBR) and an individual unit
  otherwise; its Social Security includes the spouse's (deeming
  approximated by full attribution; alternative `recipients_only`). All
  OFUMs together form one individual unit (PSID reports one OFUM total).
- **Row U2:** no SSI response.
- **Row U3 (upper bound):** the offset, plus take-up by every head/wife
  unit that the cut makes newly income-eligible and whose resource proxy
  `max(0, WEALTH1 − vehicles)` is within the resource limit. Countable
  income follows 20 CFR 416.1112 and 416.1124 in order: the $20 exclusion
  applies to unearned income first, then the $65 earned exclusion and half
  of the remaining earnings. Unearned income is head and wife transfer
  income other than SSI, TANF and other welfare, plus Social Security;
  asset income is left out; earned income is labor, farm and business
  labor income. A unit with a wife present is treated as a couple. OFUMs
  are never newly enrolled. Deterministic (every eligible unit takes up),
  so K stays 1.

SSI parameters (captured from policyengine-us; the files cite SSA's "SSI
Federal Payment Amounts" and 20 CFR 416.1112 and 416.1205): FBR in force
on January 1, monthly, individual / couple — 2004 564 / 846; 2005 579 /
869; 2006 603 / 904; 2007 623 / 934; 2008 637 / 956; 2009–2011 674 /
1,011; 2012 698 / 1,048. General exclusion $20, earned exclusion $65,
half of remaining earnings excluded, resource limits $2,000 / $3,000.
This builder did not check these against ssa.gov (the plan records that
ssa.gov refuses programmatic fetches).

## 9. Statistic

For cell c, with observation weights w, baseline adjusted income B,
reform income R and threshold T (all family-level, assigned to each
member observation):

```text
P_B[c] = 100 × Σ_{i∈c} w_i·1{B_i < T_i} / Σ_{i∈c} w_i
P_R[c] = 100 × Σ_{i∈c} w_i·1{R_i < T_i} / Σ_{i∈c} w_i
Δ[c]   = P_R[c] − P_B[c]            (percentage points)
```

Δ is the headline; P_B and P_R are the secondary rows (the Table 19 and
Table 21 analogues).

**Cells.** `all` (headline); `men`, `women`, `married`, `non_married`
(the Report's stated splits, plan §7); the four sex-by-marital cells
(optional); one diagnostic cell per birth year (not scored). Only cells
present in the sealed comparator are scored; the others are reported as
"not in comparator". The cell list freezes at registration.

**Undefined cells.** An empty cell or one with zero total weight has no
statistic; it is reported with its reason and never imputed.

## 10. Uncertainty

- **Draws:** K = 1 (deterministic).
- **Half-split floor:** seeds 0–4, fraction 0.5,
  `harness/panel.split_panel_by_person` on `family_unit_id`, so members of
  one family unit fall on one side; each statistic recomputed in each
  half; the floor is the mean and sample SD (ddof = 1) of |A − B| over
  seeds where both halves are defined; with fewer than two usable seeds
  it is undefined, never zero. Floors are at half sample and not
  rescaled. Under U1 a person's two observations can fall in different
  halves because each wave is a different family unit.
- **Design-based SE:** Taylor linearization of each weighted ratio with
  the PSID stratum and cluster; the subpopulation estimator relative to
  the tabulated rows (clusters with no tabulated row do not enter);
  single-cluster strata are left out and counted.

## 11. Registered rows

Each alternative differs from U0 in one field, except U6, which is
defined on U1. U0 is the headline row; no row may be promoted after
results exist.

| Row | Field | Value | Built |
|---|---|---|---|
| **U0** | — | §§3–10 | Yes; 1937 and 1939 blocked by the wealth supplements |
| U1 | Population | All ten birth years (§3) | Yes; six observation cells (waves 2005 and 2007) blocked |
| U2 | SSI | No response | Yes |
| U3 | SSI | Full static recomputation (upper bound) | Yes |
| U4 | Income unit | Head and wife only | Yes |
| U5 | Asset income | Keep reported asset income and add the annuity | Yes |
| U6 | Cut (on U1) | 1936 uncut if the cut starts in 2004 | Not built (needs decision 8) |
| U7 | Financial assets | Plus employer DC balances | Not built (label investigation) |
| U8 | Threshold | PSID `CENSUS NEEDS STANDARD` | Yes |
| U9 | Mortality | SSA period life table 2004 | Yes |
| U10 | Threshold | Census size-by-children matrix | Yes (needs the capture) |
| U-inst | Universe | Add institutions (sequence 51–59) | Counted only; no income rule |

## 12. Named deltas

Carried on every output (plan §7), plus those found while building:

- PSID versus SIPP wealth measurement;
- realized 2004–2012 history versus DYNASIM's 1992-based projection,
  including the 2008–09 asset shock for the 1941–45 cohorts at 67;
- realized COLAs versus 2002 Trustees assumptions;
- immigrant under-coverage; institutionalized persons; attrition;
- OFUM-owned assets inside family wealth;
- imputed rent excluded;
- self-reported Social Security, possibly net of Medicare premiums;
- pension income that may include account withdrawals (the 2013 file adds
  explicit head and wife IRA items; earlier files fold withdrawals into
  retirement income);
- exact-age sampling of alternate birth years (mean birth year 1941
  against 1940.5);
- **found:** farm income's asset portion is not separable and stays in
  income; business income is split 50/50 between labor and asset parts by
  PSID convention for working owners;
- **found:** SSI units are approximated from head, wife and OFUM totals
  (deeming by full attribution; OFUMs as one unit).

## 13. Invented worked cases

These cases are **invented** for the unit tests
(`tests/estimates/test_adjusted_poverty.py`,
`tests/estimates/test_uniform_cut_tabulation.py`). They use no PSID
data, no Census threshold, no SSA parameter and no comparator value.

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

Invented tabulation (five observations, weights 1, 1, 2, 4, 2): P_B = 20,
P_R = 70, Δ = 50 for `all`; design SE = 100·√0.1 with two strata of two
clusters each.

## 14. What is built and what is blocked

Built on branch `dynamics-ex2-track-u-20260924` (all opt-in; registered
in `POST_REVIEW_SOURCE_EXCLUSIONS` and the reachability guard):

- `src/populace_dynamics/data/family_income.py`: label-verified family
  income for waves 2005–2013 (81 items a wave, 85 in 2013, including the
  raw accuracy flags of the Social Security, SSI and asset items) and
  WEALTH1 with its components for 2009–2013; refusal naming the missing
  2005 and 2007 wealth supplements; reconciliation counts.
- `src/populace_dynamics/cohorts/age67.py`: the age-67 observations for U0
  and U1, dispositions, provenance seal, structural summary.
- `src/populace_dynamics/estimates/adjusted_poverty.py`: annuity prices,
  threshold lookup, SSI rules, baseline and reform income, poverty status;
  refuses PSID-built rows without a registration.
- `src/populace_dynamics/estimates/uniform_cut_tabulation.py`: cells,
  Δ/P_B/P_R, half-split floors, design SE; refuses real data without a
  registration pointer.
- `scripts/capture_track_u_parameters.py` (SSI capture written; Census
  parser ready), `scripts/track_u_structure.py` (counts only).

Blocked:

1. **2005 and 2007 wealth supplements** (Max, simba login): U0 loses 1937
   and 1939 until staged, adjudicated and read. A fallback row on 1941–45
   only would need registering in advance (plan §13); `income_rows(...,
   allow_blocked=True)` supports it.
2. **Census thresholds** (download approval or Max): no primary threshold
   until captured.
3. **Registration** on issue #42 after ratification; no real-data poverty
   statistic may be computed before it.
4. **Comparator coverage** of the frozen cells (comparator side, values
   redacted).

## 15. Machine-readable parameter block

Downstream lanes read this block; `tests/test_boomers2004_uniform_cut_spec.py`
holds it to the code's defaults.

```json
{
  "specification": "boomers2004_uniform_cut_exercise2",
  "version": "u1-draft-1",
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
    "comparator_values": "sealed_comparator_side_not_opened_by_builder"
  },
  "population": {
    "primary_row": "U0",
    "primary_birth_years": [1937, 1939, 1941, 1943, 1945],
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
    "financial_assets": "WEALTH1",
    "annuitized_share": 0.8,
    "annuity": {
      "real_interest_rate": 0.03,
      "timing": "immediate",
      "load": 0.0,
      "survivor_share": 0.5,
      "mortality_basis": "nchs_2000",
      "terminal_closure": "table_end",
      "lives": "member_rule",
      "negative_wealth": "annuity_floored_at_zero"
    }
  },
  "threshold": {
    "rule": "census_weighted_average_65plus",
    "years": [2004, 2012],
    "capture_status": "not_captured",
    "poor_if": "income_below_threshold"
  },
  "cut": {"rate": 0.13, "base": "all_social_security_of_the_unit", "behavior": "none"},
  "ssi": {
    "rule": "offset_existing_recipients",
    "awaiting": "d189",
    "deeming": "spouse_social_security_counted",
    "ofum_unit": "single_individual",
    "parameters": {
      "file": "data/external/track_u_ssi_parameters.json",
      "sha256": "79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523"
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
    "scored_only_if_in_comparator": true
  },
  "uncertainty": {
    "draws": 1,
    "floor": {
      "seeds": [0, 1, 2, 3, 4],
      "fraction": 0.5,
      "split_unit": "family_unit_id",
      "summary": ["mean", "sample_sd"],
      "min_usable_seeds": 2
    },
    "design_se": {"method": "taylor_linearization", "singleton_strata": "excluded_and_counted"}
  },
  "rows": {
    "U0": {},
    "U1": {"population": "all_ten_birth_years"},
    "U2": {"ssi_rule": "none"},
    "U3": {"ssi_rule": "full_static_recomputation"},
    "U4": {"income_unit": "head_wife"},
    "U5": {"asset_income_rule": "keep"},
    "U6": {"on": "U1", "cut_start_year": 2004, "status": "not_built"},
    "U7": {"financial_assets": "wealth1_plus_employer_dc", "status": "not_built"},
    "U8": {"threshold_rule": "psid_census_needs_standard"},
    "U9": {"mortality_basis": "ssa_period_2004"},
    "U10": {"threshold_rule": "census_matrix_65plus"},
    "U-inst": {"presence": "in_family_or_institution", "status": "counted_only_no_income_rule"}
  },
  "acceptance_rule": null,
  "labels": [
    "PSID-realized outcomes (not a projection)",
    "Python income concept (not Axiom)",
    "mechanical incidence"
  ],
  "blocked_by": [
    "psid_2005_2007_wealth_supplements_not_staged",
    "census_thresholds_not_captured",
    "issue_42_registration_absent",
    "max_ruling_d189_open"
  ]
}
```

## 16. Pending decisions

None of these is ratified. Each is a code parameter whose default is the
plan's proposal (or a builder choice where the plan is silent);
`adjusted_poverty.pending_decisions()` and `age67.pending_decisions()`
return them with their basis.

**Awaiting Max (d189, open):**

1. Claim class: accept Track U as exercise 2's first score (plan §10,
   decision 1).
2. SSI rule F13: offset for existing recipients (default), no response
   (U2) or full recomputation (U3) (plan §10, decision 5).
3. Download the 2005 and 2007 PSID wealth supplements (plan §10,
   decision 3).

**Awaiting Max, not yet on a decision card (plan §10):** decision 2 (a
values-redacted definitions extract by the comparator side), decision 4
(Python SSI arithmetic labelled "not Axiom"), decision 6 (acceptance rule;
default none, report gaps), decision 7 (ratify this specification by
merge; post the #42 registration), decision 8 (the scorecard's "from
2004"), and approval to download the Census threshold files.

**Awaiting the specification freeze (defaults shown):** income unit
(family unit), asset-income rule (replace), annuitized share (0.8), real
rate (3 percent), timing (immediate), load (0), survivor share (0.5,
reduced on either death), mortality (NCHS 2000), terminal closure (table
end), annuity lives (member rule), negative wealth (floor at zero),
threshold rule (weighted average, 65-and-over), SSI deeming (spouse's
Social Security counted), OFUM SSI unit (one individual unit), row (U0),
presence (in family), separated is married (true), U1 1936 weight (1),
seed wave (earliest presence wave).

## 17. Questions for the referee

1. Is `member_rule` right for OFUM members (annuitize the family's wealth
   on the OFUM member's own life), or should the family head's lives price
   it (`fu_head_rule`)?
2. Should the reported asset income removed under F4 include an imputed
   asset share of farm income?
3. Is full attribution of the spouse's Social Security an acceptable
   stand-in for SSI deeming, given the offset rule touches only baseline
   recipients?
4. Should U1's 1936 observation carry weight 1 or 0.5?
5. Should the design SE include every PSID cluster of the stratum (zeros
   outside the cohort) rather than only the clusters in the tabulated
   rows?
6. Is a fallback row on 1941–45 worth registering now, in case the
   wealth supplements are late?

## 18. What this draft read and did not verify

**Read:** the plan in full; the cos records of d188 and d189 (their
text only); the
repository code it builds on (`data/social_security_income.py`,
`data/family.py`, `data/psid.py`, `cohorts/psid2010.py`,
`estimates/cola_age_profile.py`, `cola_track_a/statutory.py`, the
exercise-1 specification and its test, the birth-evidence guard); PSID
setup-file labels for the 2005–2013 family files and `IND2023ER.sps`; the
family codebook entries for the variables it reads (these print PSID's
unweighted frequency counts and ranges, which were not used); the
`IND2023ER_formats.sas` relationship codes; the 2005, 2007 and 2009
family-file documentation on wealth; the policyengine-us SSI parameter
files; the Census historical thresholds page's link list.

**Ran on staged PSID:** label verification, the component-identity
reconciliation counts and the structural counts of §3. No income concept,
annuity, threshold assignment, poverty status or poverty rate was
computed on PSID data.

**Did not verify:** the Census threshold values and the real layout of the
Census spreadsheets; the SSI parameters against ssa.gov; the names, IDs
and contents of the 2005 and 2007 wealth supplements; whether PSID Social
Security amounts are net of Medicare premiums; whether SSI and Social
Security are kept apart by respondents; the P-section DC items for U7; the
coverage of the sealed comparator; anything in the Report beyond the
plan's reading of its methods.

## 19. Changelog

- `u1-draft-1` (2026-09-24): first draft, with the Track U readers,
  builder, income concept and tabulation on branch
  `dynamics-ex2-track-u-20260924`.
