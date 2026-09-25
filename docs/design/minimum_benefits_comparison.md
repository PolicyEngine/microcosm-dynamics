# Minimum benefits comparison: specification draft for DynaSim scorecard exercise 4

- **Status:** draft for the referee. Nothing here is ratified. Max has
  not ruled on exercise 4 (cos decision d219, open, deadline 2026-09-30,
  default "accept all nine"), and ratification by merge awaits him (d219
  item 9). Every choice that awaits him or the specification freeze is
  a field of `min_benefit_track_m.policy.TrackMPolicy` whose value is
  the plan's recommended default, and §20 lists them. This draft
  authorizes no real-data run: the one-shot entry point
  (`scripts/run_track_m_registered.py`) refuses a block whose status or
  version is not ratified, that lists a decision awaiting Max, or that
  records no ruling of his on a d219 field (§19).
- **Specification:** `urban2006_minimum_benefits_exercise4`, version
  `m1-draft-1`, drafted 2026-09-24. §23 is the changelog.
- **Plan item:** M1 of the blind plan
  `EVID/critical-path-minimum-benefit-20260924.md`, revision 2
  (SHA-256 `976ec7f6…`), where `EVID` =
  `~/microcosm-launch-evidence/dynasim-parity-20260909`. The plan's
  section 7 (fields G1–G23, rows MS0–MS6) is the starting point. The
  plan names this file `urban2006_minimum_benefit_comparison.md`; the
  lane's brief named it `minimum_benefits_comparison.md`.
- **Template:** the structure of A1
  (`docs/design/urban2010_cola_comparison.md`, ratified), E1
  (`docs/design/urban2010_fra68_comparison.md`, `e1-draft-6`, on branch
  `dynamics-ex3-fra68-20260924`, not on master) and U1
  (`docs/design/boomers2004_uniform_cut_comparison.md`).
- **Claim class (proposed, pending d219 item 2):** a static measurement
  on a PSID snapshot for income year 2022, not a projection. It does
  not test the Dynamics projection engine.
- **Labels every output carries:** *PSID-realized outcomes (not a
  projection)*; *income year 2022 (not 2025)*; *Python rules (not
  Axiom)*; *static* (`min_benefit_track_m.OUTPUT_LABELS`).
- **Builder boundary:** a model-builder lane (Claude Code subagent, Opus
  5.5) wrote this draft. It read `EVID/RESTRICTED-FILES.md` (SHA-256
  `b483d32d…`, last changelog entry 2026-09-24 19:20) before any other
  file and opened nothing it restricts. Of the Report it read PDF page
  29 only, as text (`pdftotext -layout -f 29 -l 29`), for formula unit
  tests (ruling C5). It did not open the Report's other pages or its
  `.txt` extraction, any comparator directory, seal, reconciliation or
  values scan, the uncleared sources of the two cleared files, or
  `EVID/scratchpad-archive-20260924/`. It computed no share receiving a
  minimum, no years of coverage and no PIA on real data. §22 lists what
  it read.
- **Disclosure that travels with this specification (plan section 11,
  R5):** the clearance follow-up of 2026-09-24 14:15 found that the
  withheld Table 5 note sentence (ruling C2) lies inside the text lines
  the plan's first version says its author read. That sentence
  characterizes Table 10 (expenditure paths), which is not an exercise-4
  target. This lane did not read it; of the first plan version
  (`EVID/revisions/critical-path-minimum-benefit-20260924-v1.md`,
  `7aa600e1…`) it read only the eight field rows G4–G13 that revision 2
  cites as "v1's", through `grep`.

## 1. Target

The target is Table 6 of Favreault, Mermin and Steuerle, *Minimum
Benefits in Social Security* (Urban Institute, August 2006), its 2025
block, as the cleared availability statement
(`EVID/exercise4-target-availability-cleared-20260924.md`, `6db9b5bb…`,
item Y1) describes it. This lane has not seen the table.

- **Measure:** the percentage of OASDI beneficiaries aged 62 and older
  who receive a minimum benefit (Table 6's title, cleared extract).
  Footnote 33 (cleared extract) says the measure identifies the people
  who receive the minimum, which is not the number of people whose
  benefit is higher than under the option-1 baseline.
- **Options:** Table 5's options 2–5 only, printed in the column order
  3, 2, 5, 4. There is no option-1 column and no change column: each
  cell is a level under one option.
- **Rows:** All, with Men and Women nested under All.
- **N:** one N column per row; no table states its unit. N is reported
  as a diagnostic and never scored.
- **Cells scored:** 12 (four options by three rows). **Headline,
  designated before any result:** option 2, All (plan R2; d219 item 1,
  pending).
- **Text restatements:** body text on PDF page 17 restates the four
  2025 All cells (Y2) and calls the denominator persons who have Social
  Security income (D2). One text-only 2025 ratio compares receipt of
  the minimum by women and by men under option 3 (Y3); the text does
  not say whether it is a ratio of rates or of recipient counts. Y3 is
  reported both ways and not scored separately.
- **What is not printed:** any 2025 poverty statistic, in any form, for
  any option (availability statement, bottom line 1). Poverty outcomes
  are printed for 2050 only (Table 9 and the Poverty Level rows of
  Tables 7 and 8); they belong to the projected Track P (plan section
  12) and are out of this specification.

The comparator values are sealed on the comparator side
(`EVID/exercise4-comparator-seal-20260924.json`, not opened by this
lane).

## 2. Sources

| Source | Use | Status |
|---|---|---|
| Plan, revision 2 (`976ec7f6…`) | Fields G1–G23, rows MS0–MS6, the INVENTED cases, the decision card | Read in full |
| Cleared definitions extract (`54279fd1…`) | Table 5 as transcribed; fn. 25–33; the population sentence; fn. 35; Table 6's title, labels and units; Table 2's limits; rulings C1–C5 | Read in full |
| Cleared availability statement (`6db9b5bb…`) | Y1–Y3, D1–D16, the "not printed" checks | Read in full |
| Report, PDF page 29 (Table 2) | Formula unit tests only (C5, §17) | Read as text |
| Oracle, `src/populace_dynamics/ss/` | AIME, PIA, reductions, spouse's and widow(er)'s benefits | Read this session; called unchanged |
| `cola_track_a/benefits.approximate_pia` | The DI PIA under G5 | Read this session; called unchanged |
| policyengine-us `quarters_of_coverage_threshold.yaml` at `a03e82e503` (SHA-256 `12354a05…`) | Quarter-of-coverage amounts, 1978 on | Read from the checkout; not a committed capture (M2) |
| PSID 2023 wave, family files 1968–2023, marriage history | Structural counts (§10) | Staged; labels verified |
| Census one-person 65+ weighted-average thresholds | The threshold that defines the minimum (G8) | **Not captured** (M2) |
| 42 USC 413(a)–(d); 415 elapsed and computation years | The statute behind G6 and MS6 | **Not captured** (M2); the oracle's `statutory_aime` module quotes 415(b) |

## 3. Policy

**Options** (Table 5 as transcribed in the cleared extract; the
solvency parameters are policy inputs used exactly as printed, never
tuning targets, ruling C1). "Share of the threshold" is the printed
"percent of poverty"; a work year is a year with four covered quarters.

| # | Option | Minimum: share of the threshold by work years | Solvency mechanism | In Table 6 | Implemented |
|---|---|---|---|---|---|
| 1 | Reduced current law | None | Uniform cut of 12.45% | No column | Yes (the cut) |
| 2 | Standard, price-indexed | 55% at 10 years, +1.5 points a year to 100% at 40 | Uniform cut of 12.81% | Yes | Yes |
| 3 | Standard, wage-indexed | As option 2 | Uniform cut of 14.27% | Yes | Yes |
| 4 | Generous, price-indexed | 80% at 10, +2.0 a year to 100% at 20, +1.0 a year to 120% at 40 | Uniform cut of 13.64% | Yes | Yes |
| 5 | Generous, wage-indexed | As option 4 | Uniform cut of 18.62% | Yes | Yes |
| 6 | A bend point where the benefit equals the poverty threshold | None (a formula change) | Upper two factors cut to 23.6125% and 9.445%; the first and new segments keep 90% and 32% | No | No |
| 7 | Option 3 with a chained CPI | As option 3 | COLA cut of 0.50% plus a uniform cut of 7.67% | No | No |
| 8 | Option 3 with 40 computation years | As option 3 | 40 computation years plus a uniform cut of 10.22% | No | No |
| 9 | Option 3, lowest bracket shielded | As option 3 | Upper two factors cut by 24.0% (the 90% bracket unchanged) | No | No |
| 10 | Option 3, DI work years not prorated | As option 3, except DI | Uniform cut of 13.7% | No | No |

Options 6–10 are recorded for completeness; they belong to Track P.

**Rules common to every option** (paraphrased from the cleared
extract, with locators):

- **Effective date:** all options take effect in 2007 (Table 5 notes;
  PDF p. 15). The uniform cuts apply across the board to new entitlees
  and target cost equivalence in 2050 (Table 5 notes). The results text
  words the covered years two ways, "entitled after 2007" and "from
  2007 onward" (D9).
- **Where the minimum is set:** at the point of PIA calculation (fn.
  26), with three stated consequences: early-claiming reductions and
  delayed credits apply to it; beneficiaries do not "age onto" it; and
  it can generate spouse's and survivor benefits.
- **DI:** work-year requirements are prorated for DI beneficiaries so
  that they stay proportionate to possible work years, except in option
  10 (fn. 26); the results text bases the proration on the years
  elapsed before disability (D3). No formula is printed.
- **The threshold:** Census Bureau thresholds for the aged (fn. 25);
  the option 6 passage speaks of the threshold for those aged 65 and
  older; the thresholds move with prices (D5).
- **Behaviour:** people work, earn and collect OASDI as under current
  law (PDF p. 16).
- **Population of the outcome tables:** people aged 62 and older,
  including disabled workers aged 62–64 and formerly disabled workers
  converted to retired-worker benefits (PDF p. 20, cleared; D6).
- **Children's benefits:** DYNASIM has none (fn. 35). The family
  maximum is not mentioned anywhere (availability §6). No couples' cap
  on minimum-based benefits appears to have been simulated (D7, an
  inference).

**Track M's reading** (`min_benefit_track_m.policy`, the plan's
section 7): options 1–5 with the schedules and cuts above;
`TrackMPolicy` holds every open choice; `REGISTERED_ROWS` holds MS0–MS6
(§14).

## 4. Who the reform reaches

- **Policy year (G2; d219 item 3, pending).** Every policy date moves
  back three years: the policy year *Y*₀ is 2004, and the wage-indexed
  minimum's base year moves with it. The 2022 snapshot then exposes 19
  entitlement cohorts (2004–2022), as DYNASIM's 2025 exposes 2007–2025.
  **MS1** keeps the Report's dating (*Y*₀ = 2007; 16 cohorts). The
  cohort counts are the plan's deductions from the dating, not results.
- **Window (G4).** A PIA first calculated in or after *Y*₀ is cut and
  floored; **MS4** requires after *Y*₀ (the "entitled after" wording).
  `rules.in_window`.
- **Scope (G11).** A PIA first calculated before *Y*₀ is untouched
  under every option (*O* = 0). An auxiliary is reached only through a
  worker whose PIA was first calculated in the window. That the minimum
  reaches new entitlees only is an inference from fn. 26 and the
  effective date (plan R4).
- **DI conversion.** The flag is set at the DI PIA's calculation and
  carries over at conversion to a retired-worker benefit (G12; fn. 26:
  the minimum is set at PIA calculation).
- **Entitlement classification** is plan item M4 (the plan's section
  4: receipt histories from the person-level Social Security items of
  waves 1984–1992 and 2005–2023, the 2005 and 2007 "year before last"
  items, family-file head and wife items, and the age rule for later
  entrants). Nothing here classifies anyone.
- **Finding (threshold years before *Y*₀).** Under G4 the window keys
  on the year the PIA was first calculated, the entitlement year, while
  G8 takes the threshold of the eligibility year. A worker who first
  claims in or after *Y*₀ but became eligible before it (a late
  claimer, or a DI entitlement whose onset year precedes it) is in the
  window with a threshold year before *Y*₀. With *Y*₀ = 2004 a worker
  entitled at 70 in 2004 was eligible in 1996. M2's capture therefore
  needs the thresholds from about 1996, not from 2004 as the plan's
  section 5 proposes (referee question 2).

## 5. Years of coverage

`min_benefit_track_m.coverage.count_coverage_years` (G6, G7):

- ***Y*** counts the years through the year before the entitlement
  year whose covered earnings reach four times the year's
  quarter-of-coverage amount (Table 5: a work year is 4 covered
  quarters). All ages count. The caller passes the end year (M4).
- **Covered earnings (d219 item 4, pending):** PSID labor income is
  treated as covered earnings. The PSID has no covered/noncovered split
  (plan section 5); noncovered public employment therefore counts
  (named delta).
- **Quarter-of-coverage amounts, 1978 on:** read from the
  policyengine-us checkout the oracle reads (the file cites 42 USC
  413(d)(2), 20 CFR 404.143 and SSA's QC table), with its revision and
  SHA-256 recorded (`load_qc_amounts`). This is not the committed
  capture M2 calls for. Check: four times the 2006 amount is $3,880,
  the figure Table 2's notes print (§17).
- **Before 1978 (builder default, G6):** the 1978 amount scaled back
  by the average wage index, QC(1978)·AWI(*y*)/AWI(1978). The statute
  (42 USC 413(a)–(d)) is to be captured and read in M2 before the rules
  rely on this; this draft states nothing about what it says.
- **Biennial gap years (builder reading, pending the freeze):** the
  PSID never collected income for the odd years 1997–2021. G6 counts
  unobserved years as zero, while the plan's named deltas list
  "odd-year gap imputation from 1997 on" and M5 names "the odd-year gap
  law". The default `gap_year_rule = "immediate_neighbor_mean"` fills a
  gap year with the immediate-neighbor law of `estimates.career`
  (`_impute_gap`: the mean of the two neighboring years, or the one
  that exists; never a neighbor after the count's end year) before the
  count; the alternative `"zero"` reads G6 literally. The choice is
  material: the gap years are 22 percent of the potential window
  person-years of the beneficiaries born 1945–1960 (§10).
- **Unobserved years** (neither observed nor imputed) count as zero
  and are flagged, over a flag window from the year of attaining 22
  (builder default, matching G12's start).
- **DI proration (G12; d219 item 6, pending):** *Y*\* = *Y*·40/*D*,
  where *D* counts the elapsed years from the year of attaining 22
  through the year before onset, bounded to [1, 40]; the schedule
  applies to min(*Y*\*, 40), including the 10-year floor
  (`rules.prorated_work_years`). *Y*\* is not rounded (builder default,
  as in the plan's INVENTED case D, where 15 years of 22 possible give
  *Y*\* = 27.27 and a minimum of $674.24); the alternative floors it
  (referee question 3).

## 6. The PIA

`rules.history_pia` calls the oracle unchanged (G5). What the oracle
does, as read in this session:

- **Retired workers:** the history through the year before the
  eligibility year (the year of attaining 62); the AIME by
  `ss.statutory_aime.aime` (42 USC 415(b)(2) computation years; its
  docstring says it equals `ss.benefits.aime` exactly for birth years
  1929 and later, and a test here confirms it on an invented history);
  the PIA by `ss.benefits.pia`: 90, 32 and 15 percent over the
  eligibility year's bend points, rounded down to a dime. No
  recomputation for later earnings.
- **DI (G5):** Track A's disclosed `approximate_pia`: the oracle's
  35-year AIME through the year before onset, indexed to the second
  year before onset, at the onset year's bend points. Its docstring
  says the 35-year divisor understates short careers. **MS6:**
  `ss.statutory_aime.aime(..., disability_year=onset)` (elapsed years
  less one-fifth, at most 5) and `ss.benefits.pia` at the onset year's
  bend points.
- **A worker who died before eligibility** (whose PIA is first
  calculated for a survivor): `approximate_pia` at the death year
  (`death_pia_rule`, builder default; the plan is silent; referee
  question 5).
- **MS5:** the PIA implied by the observed benefit,
  benefit / (claim factor · cumulative COLA factor)
  (`rules.benefit_implied_pia`). The claim factor and the COLA path
  come from M4 (first-receipt bracket) and `data/external/
  ssa_cola_history.json`.

*P* is monthly, in the eligibility year's dollars, at the first
calculation. So is the minimum (§7), so the dollar level cancels
(plan section 3).

## 7. Threshold and indexing

- **Threshold (G8):** the Census weighted-average poverty threshold for
  one person aged 65 and older, of the worker's threshold year: the
  eligibility year, or the onset year for a DI worker. It is **not
  captured**: `rules.load_aged_thresholds` refuses and names M2. Table
  2's HHS threshold is not borrowed (D15).
- **Price indexing (options 2 and 4):** the threshold of the year
  itself (the thresholds move with prices, D5).
- **Wage indexing (options 3 and 5; G9):**
  *T*(*Y*₀)·AWI(*e* − 2)/AWI(*Y*₀ − 2). The two-year lag is a builder
  default (bend points use the second year before). At *e* = *Y*₀ the
  wage-indexed minimum equals the price-indexed one. The AWI is the
  oracle's `SSAParameters.nawi`.
- **Monthly minimum:** *M*ₖ = *s*ₖ(*Y*\*)·*T*/12, unrounded (builder
  default; the alternative floors it to a dime as 415(g) rounds a PIA).
- **No re-determination** after the first calculation (fn. 26(2)).

## 8. Order of the cut and the minimum, and the worker flag

- **Order (G10; d219 item 5, pending):** the minimum is a floor after
  the cut, max((1 − *c*ₖ)·*P*, *M*ₖ). **MS2:** the cut applies after the
  floor, max(*P*, *M*ₖ)·(1 − *c*ₖ). The Report prints no rule; the
  results text's mechanism sentence (D10: the benefit reduction itself
  makes more people qualify) supports G10 by the comparator side's
  inference.
- **Worker flag (G22):** *O*ₖ = 1 when the PIA was first calculated in
  the window, *Y*\* ≥ 10 and *M*ₖ > (1 − *c*ₖ)·*P* (MS2: *M*ₖ > *P*),
  fixed at the first calculation (`rules.evaluate_worker`).
  Option 1 has no minimum and every flag is 0.
- **Deductions used as unit tests (plan section 1), not results:** at
  the same eligibility year and PIA, option 2's flagged set lies inside
  option 4's and option 3's inside option 5's, under either order; a
  worker on option 2's minimum is on option 3's whenever option 3's
  wage-indexed threshold is at least option 2's price-indexed one
  (because *c*₃ > *c*₂).

## 9. Who counts as receiving the minimum

- **G23 (d219 item 7, pending):** *A*ₖ = 1 for a person paid, in 2022,
  a Title II benefit computed from a PIA that rests on the minimum:
  their own worker PIA (*O*ₖ = 1 and an own worker benefit paid), or a
  linked worker's PIA from which a spouse's or survivor's benefit they
  are paid is computed. **MS3:** own worker PIA only
  (`rules.receives_minimum`).
- **Whether an auxiliary benefit is paid (G13):** the oracle decides,
  on the worker's option PIA: `ss.benefits.spousal_benefit` (one-half
  of the worker's PIA less the spouse's own PIA, reduced for early
  claiming; paid when positive) and `ss.benefits.widow_benefit` (paid
  on the deceased's record when it exceeds the survivor's own amount).
  Dual entitlement is included; there is no couples' cap.
- **Unlinked auxiliaries** (a spouse's or survivor's benefit with no
  linked worker record) cannot be flagged: counted as not receiving and
  reported separately.
- **Footnote 33:** receiving the minimum is not the same as being
  better off than under option 1. INVENTED case H (§16) is on option
  2's minimum and 0.12 percent below option 1.

## 10. Population and vintage

**Universe (G3; plan section 4):** persons of the 2023 PSID wave
(income year 2022) in a responding family unit (sequence 1–20) with a
positive 2023 cross-section weight (ER35265), born 1960 or earlier by
the first-estimates birth-year law (`estimates.career.derive_birth_years`,
seeded with the 2023 age), receiving OASDI in 2022 (person-level
ER35219 above zero; the reference person's and spouse's amounts
reconciled with the family file, ER85623 and ER85625). Sex is ER32000.
Movers-out and decedents are excluded, as Track U does.

**Structural counts** (staged PSID, unweighted persons, counts only;
`scripts/track_m_structure.py` at commit `2d449214` on a clean tree,
evidence `EVID/track-m-structure-20260924/track-m-structure.json`,
SHA-256 `3a6a2bb1…`, which also records the SHA-256 of each of the 91
PSID files read). No years of coverage, PIA, threshold, minimum or share
receiving a minimum was computed.

| Step | Persons |
|---|---|
| Records in the 2023 individual file | 85,536 |
| In a responding family unit (sequence 1–20) | 23,283 |
| Of whom zero 2023 weight | 0 |
| Aged 0–5 in 2023, counted out before the birth-year law (its derived-age clause supports birth years to 2016 only) | 2,046 |
| Birth year unresolved by the law | 32 |
| Born 1960 or earlier | 3,283 |
| Of whom person-level OASDI in 2022 (the universe) | **2,135** |
| Of whom none | 1,148 |

Other 2023 sequence groups: institution 298, moved out 831, died 124,
not in the wave 61,000.

- **Reconciliation with the family file:** for every reference person
  (2,112), spouse (873) and partner (48) born 1960 or earlier, the
  person-level receipt and the family-file amount agree on receipt: no
  person has one without the other. The 103 other family-unit members
  among the beneficiaries have no family-file person amount (the OFUM
  total is not attributable).
- **The 2,135 beneficiaries:** 1,236 women and 899 men; 1,404
  reference persons, 593 spouses, 35 partners, 103 other members; born
  1941 or earlier 234, 1942–1944 132, 1945–1960 1,769; birth year from
  the marriage history 2,076, from the 2023 age 57, from earnings ages
  2. Self-reported type mentions: retirement 1,772, disability 288,
  survivor 109, dependent of a retired worker 19, of a disabled worker
  5, other 39; each type is unknown for 19. Amount accuracy: reported
  1,933, imputed by PSID staff 27, median-imputed 175. 1,597 family
  units in 68 strata and 121 stratum-cluster pairs.
- **Availability of the years G6 counts** (the window from the year of
  attaining 22 through the year of attaining 61, capped at 2022, a
  structural stand-in for the entitlement year M4 will supply): 85,400
  person-years, of which 2,725 fall before 1968, 16,781 in the biennial
  gap years, 41,280 in collected years with an observation in the
  earnings panel and 24,614 in collected years without one. By
  observed years in the window, persons: none 130; 1–9 507; 10–19 372;
  20–29 442; 30–39 684. At any age, 65 beneficiaries have no observed
  year at all. For the 1,769 born 1945–1960, the gap years are 15,869
  of 70,760 window person-years (22 percent).
- **What the counts imply for M4 and M5 (not a result):** the earnings
  panel (`data/family.py`) carries head and spouse labor income only,
  so years spent as another family member are unobserved; the gap-year
  rule (§5) decides a fifth of the potential years of the headline's
  core cohorts.

**Deltas of the population** (named, not fixed): exposed cohorts born
1942–1960 against DYNASIM's 1945–1963; the whole 62+ age structure;
DYNASIM's 1992 noninstitutionalized base (D12) against the PSID weight;
immigrants after the PSID's latest refresher; attrition; pre-PSID
years.

## 11. Statistic

For option *k* and cell *c* (All, Men, Women):

```text
S_k[c] = 100 × Σ_{i∈c} w_i·A_k,i / Σ_{i∈c} w_i
```

over the universe (§10), with *w* the 2023 cross-section weight and
*A* from §9. The headline is *S*₂[All]. The N cells are not scored.
Y3 is reported as a ratio of rates and as a ratio of weighted counts
for option 3, and not scored.

**Diagnostics (registered run only; not scored; G21):** the exposed
share of the universe; *Y*\* in bands; *P*/*M* in bands; the DI-origin
share; the unlinked-auxiliary share; weighted and unweighted N; the
history PIA against the benefit-implied PIA; a check that the worker
flags are nested (§8). None may be computed on real data before the
registration.

## 12. Uncertainty

The Track U pattern (G19): deterministic (K = 1); a five-seed (0–4)
person-disjoint half-split floor on family units linked through shared
persons; a design-based standard error by Taylor linearization with
ER31996 and ER31997. **Not built** (plan item M8).

## 13. Acceptance rule

**Proposed: none** (d219 item 8, pending). The comparison is reported,
not gated; it runs once and is published regardless. No rule may be
set after registration.

## 14. Registered rows

Each row changes one field from MS0 and reports all 12 cells; MS0 is
the scored row, designated before any result, and no row may be
promoted afterwards.

| Row | Field changed | Value | Rules built |
|---|---|---|---|
| **MS0** | — | §§4–9 primaries (*Y*₀ = 2004) | Yes |
| MS1 | `policy_year` | 2007 (the Report's dating; 16 cohorts) | Yes |
| MS2 | `order` | Cut after the floor | Yes |
| MS3 | `counting_rule` | Own worker PIA only | Yes |
| MS4 | `window_rule` | After *Y*₀ | Yes |
| MS5 | `pia_rule` | Benefit-implied PIA | Arithmetic yes; its inputs are M4's |
| MS6 | `di_pia_rule` | Statutory DI computation years | Yes |

## 15. Named deltas

Carried on every output (plan section 7), plus those found while
building:

- realized 2022 against DYNASIM's projected 2025;
- exposure: aligned in MS0 with a residual age-structure delta; 16
  against 19 cohorts in MS1;
- realized AWI and CPI against the 2005 Trustees paths;
- PSID against SIPP population and weights;
- labor income treated as covered earnings;
- pre-1968 and pre-entry years;
- the biennial gap years 1997–2021 (§5);
- the DI PIA approximation;
- unlinked auxiliaries;
- entitlement classification at the 2004 boundary;
- no windfall-elimination rule applied to the minimum;
- no recomputation for later earnings;
- children's benefits: DYNASIM has none (fn. 35); a PSID beneficiary
  aged 62+ paid as a child is a delta;
- **found:** the earnings panel observes head and spouse labor income
  only, so a beneficiary's years as another family member are
  unobserved (§10);
- **found:** thresholds are needed for eligibility years before *Y*₀
  (§4).

## 16. Invented worked cases

**INVENTED** inputs: a one-person aged threshold of $10,000 a year, an
invented wage index and made-up PIAs; no Census value, PSID value,
model output or comparator value. The schedules and cuts are Table 5's.
The plan's author computed cases A–I independently of this code; the
tests (`tests/min_benefit_track_m/test_rules.py`) recompute each.

| Case | *Y* (*Y*\*) | *P* | *M*, option 2 | Option 2 flag (G10 / MS2) | Option 4 flag (G10 / MS2) | Option 2 against option 1 |
|---|---|---|---|---|---|---|
| A. Worker | 30 | $600 | $708.33 | 1 / 1 | 1 / 1 | +34.84% |
| B. Below the floor | 9 | $600 | none | 0 / 0 | 0 / 0 | −0.41% |
| C. Moved onto the minimum by the cut | 40 | $900 | $833.33 | 1 / 0 | 1 / 1 | +5.76% |
| D. DI, 15 years of 22 possible | 15 (27.27) | $500 | $674.24 | 1 / 1 | 1 / 1 | +54.02% |
| H. On the minimum, worse off than option 1 | 40 | $953 | $833.33 | 1 / 0 | 1 / 1 | −0.12% |
| I. Generous schedule only | 20 | $700 | $583.33 | 0 / 0 | 1 / 1 | −0.41% |
| F. Spouse of A, no own benefit | — | — | — | Counted under G23, not MS3 | Same | As A |
| G. PIA first calculated before *Y*₀ | — | — | — | 0 / 0 | 0 / 0 | 0 |

Hand computations: case A, 0.85 × 10,000 / 12 = 708.33 against
0.8719 × 600 = 523.14, and 708.33 / (0.8755 × 600) − 1 = +34.84%; case
C, 833.33 > 0.8719 × 900 = 784.71 but not > 900; case D,
15 × 40 / 22 = 27.27 and (0.55 + 0.015 × 17.27) × 10,000 / 12 = 674.24;
case H, 833.33 > 0.8719 × 953 = 830.92, while 0.8755 × 953 = 834.35.
The binding bound at *Y* = 40 is 833.33 / 0.8719 = $955.77 (option 2)
and 1,000 / 0.8636 = $1,157.94 (option 4).

Further invented cases in the tests: a DI worker with 6 years of 20
possible (*Y*\* = 12) crosses the floor that a retired worker with 6
years does not; with *T*(2004) = $10,000 and an invented AWI of 40,000
in 2002 rising 1,000 a year, the wage-indexed threshold for 2010 is
10,000 × 46,000 / 40,000 = $11,500; the DI PIA under MS6 uses 18
computation years for onset at 44 (22 elapsed years less 4) and
exceeds the 35-year approximation.

## 17. Table 2 formula checks (ruling C5)

Table 2 (PDF page 29, "Authors' calculations") gives stylized
combined benefits as a percent of the single-person HHS poverty
threshold for never-married workers born 1943 who claim at 62 in 2005,
under current law and under an NCRP-style minimum. Ruling C5 clears it
for formula unit tests only: it is never a comparator, a target or a
calibration input, and its NCRP-style schedule is not a Table 5
schedule. `tests/min_benefit_track_m/test_table2_formula_checks.py`
uses the oracle's parameters from the policyengine-us checkout.

**Checks that pass:**

- The oracle gives the 1943 cohort a full retirement age of 66, so a
  claim at 62 is 48 months early and the worker's reduction is
  36 × 5/9 + 12 × 5/12 = 25 percent (factor 0.75).
- With the text's NCRP schedule (60 percent of poverty at 20 work years
  plus 2 points a year to 100 percent at 40) and the minimum set at
  PIA calculation (fn. 26(1)), the NCRP-style cells at 62 are
  0.75 × 60 = 45 and 0.75 × 100 = 75, and at the NRA 60 and 100, as
  printed for rows 2c, 2d, 3c and 3d; below 20 years every cell is
  "no change", as printed; where current law exceeds the minimum the
  cell is "no change" (rows 1c and 1d at 62), and where the minimum
  exceeds it the minimum is printed (row 1d at the NRA: 100 against 99).
- The replacement-rate columns (68 and 90) are consistent with the 0.75
  factor within the printed rounding.
- Four times the 2006 quarter-of-coverage amount from the
  policyengine-us series is $3,880, the page's figure for rows 3a–3d.

**Findings (recorded, never tuned to):**

1. Row 1c, column 6 (NCRP-style minimum at the NRA) prints 82%. The
   schedule gives 60 percent at 20 years, below column 2's current-law
   80 percent, so max(current law, minimum) is "no change". 82% equals
   column 4's value for the row.
2. Columns 1 and 2 (current law, at 62 and at the NRA) are not related
   by the 25 percent reduction alone for rows 1c, 1d and 2d, even
   allowing for the printed rounding (for 1d the ratio of 76 to 99 lies
   between 0.759 and 0.777 once both are unrounded). The page does not
   say on which year's benefit and threshold the NRA columns are
   evaluated. The NCRP-style columns, whose minimum is a share of the
   threshold, show the exact 0.75.

The SSI columns (3 and 4) are outside Track M and were not checked.

## 18. What is built and what is blocked

Built on branch `dynamics-ex4-track-m-20260924` (all opt-in; registered
in `POST_REVIEW_SOURCE_EXCLUSIONS` and the reachability guard):

- `src/populace_dynamics/min_benefit_track_m/policy.py`: options 1–5,
  `TrackMPolicy`, rows MS0–MS6, `pending_decisions()`.
- `.../coverage.py`: years of coverage (§5), the quarter-of-coverage
  loader.
- `.../rules.py`: §§6–9 (schedules, indexing, proration, window, order,
  flag, auxiliaries, receipt; the PIA through the oracle).
- `.../specification.py`: this block's reader and the registered-run
  gate.
- `.../structure.py` and `scripts/track_m_structure.py`: the structural
  counts of §10.
- `scripts/run_track_m_registered.py`: the one-shot entry point; it
  refuses this draft, and with a ratified block it refuses until the
  missing pieces below exist, before reading any PSID file.
- Tests: `tests/min_benefit_track_m/` and
  `tests/test_minimum_benefits_spec.py`.

Blocked, with the plan's effort estimates (lane-days):

1. **Max's ruling on d219** (M0, 0.5).
2. **M2 captures** (1.5): the Census one-person 65+ thresholds (from
   about 1996, §4), the quarter-of-coverage amounts with a hash, and the
   statute text of 413(a)–(d) and 415; a public download needs the
   session's permission.
3. **M3 readers** (2.5): person-level Social Security amounts and types
   for waves 1984–1992 and 2005–2023; the 2005 and 2007 "year before
   last" items.
4. **M4 cohort** (5): entitlement classification at 2004 and 2007, DI
   origin and onset, spouse links (living and deceased), types,
   provenance.
5. **M5 careers** (4, part built here): realized histories 1968–2022
   with the gap rule; *Y* and *P* per worker through this module.
6. **M8 tabulation** (1.5), **M10 dry run** (1.5), **M11 registration
   and one-shot** (3).
7. **Referee pass** on this draft (1) and ratification by merge.

## 19. Machine-readable parameter block

Downstream code reads this block:
`min_benefit_track_m.specification.m1_parameter_block` and
`check_specification_for_registered_run` (the entry script), and
`tests/test_minimum_benefits_spec.py`, which holds it to the code.
`decisions_awaiting_max` lists the d219 items; a registered run refuses
while it is non-empty, and until `decisions` records Max's ruling on
each d219 field (`{field: {"ruling": value, ...}}`) with the
configuration following every ruling.

```json
{
  "specification": "urban2006_minimum_benefits_exercise4",
  "version": "m1-draft-1",
  "status": "draft_for_referee",
  "claim_class": {
    "proposed": "track_m_static_psid_snapshot_income_year_2022",
    "awaiting": "d219"
  },
  "target": {
    "report": "Favreault, Mermin and Steuerle (2006), Minimum Benefits in Social Security, Urban Institute",
    "report_pdf_sha256": "cc22db1d0040367671f397be6f5c0df2b06a529ec1193f5e136c499023baca67",
    "table": "6",
    "year": 2025,
    "measure": "percent_of_oasdi_beneficiaries_62_plus_receiving_a_minimum",
    "availability_item": "Y1",
    "n_column": "not_scored_unit_not_printed",
    "text_ratio_y3": "reported_as_ratio_of_rates_and_of_counts_not_scored",
    "comparator_values": "sealed_comparator_side_not_opened_by_builder"
  },
  "cells": {
    "options": [
      2,
      3,
      4,
      5
    ],
    "rows": [
      "all",
      "men",
      "women"
    ],
    "headline": {
      "option": 2,
      "row": "all"
    }
  },
  "options": {
    "1": {
      "number": 1,
      "label": "Reduced current law",
      "schedule": null,
      "indexing": null,
      "uniform_cut": 0.1245,
      "schedule_points": null
    },
    "2": {
      "number": 2,
      "label": "Standard price-indexed minimum benefit",
      "schedule": "standard",
      "indexing": "price",
      "uniform_cut": 0.1281,
      "schedule_points": [
        [
          10,
          0.55
        ],
        [
          40,
          1.0
        ]
      ]
    },
    "3": {
      "number": 3,
      "label": "Standard wage-indexed minimum benefit",
      "schedule": "standard",
      "indexing": "wage",
      "uniform_cut": 0.1427,
      "schedule_points": [
        [
          10,
          0.55
        ],
        [
          40,
          1.0
        ]
      ]
    },
    "4": {
      "number": 4,
      "label": "Generous price-indexed minimum benefit",
      "schedule": "generous",
      "indexing": "price",
      "uniform_cut": 0.1364,
      "schedule_points": [
        [
          10,
          0.8
        ],
        [
          20,
          1.0
        ],
        [
          40,
          1.2
        ]
      ]
    },
    "5": {
      "number": 5,
      "label": "Generous wage-indexed minimum benefit",
      "schedule": "generous",
      "indexing": "wage",
      "uniform_cut": 0.1862,
      "schedule_points": [
        [
          10,
          0.8
        ],
        [
          20,
          1.0
        ],
        [
          40,
          1.2
        ]
      ]
    }
  },
  "policy": {
    "policy_year": 2004,
    "window_rule": "in_or_after_policy_year",
    "order": "floor_after_cut",
    "counting_rule": "own_or_linked_worker_pia",
    "pia_rule": "history_oracle",
    "di_pia_rule": "approximate_pia",
    "death_pia_rule": "approximate_pia",
    "di_proration": "elapsed_years_from_age_22",
    "di_proration_start_age": 22,
    "di_proration_cap_years": 40,
    "di_prorated_years_rounding": "exact",
    "threshold_rule": "census_weighted_average_one_person_65_plus",
    "threshold_year_rule": "eligibility_year_di_onset_year",
    "wage_index_lag_years": 2,
    "covered_earnings_rule": "psid_labor_income_treated_as_covered",
    "pre_1978_coverage_rule": "qc_1978_scaled_back_by_awi",
    "gap_year_rule": "immediate_neighbor_mean",
    "quarters_per_work_year": 4,
    "unobserved_window_start_age": 22,
    "minimum_rounding": "none",
    "couples_cap": "none",
    "unlinked_auxiliary": "not_receiving_counted_separately"
  },
  "rows": {
    "MS0": {},
    "MS1": {
      "policy_year": 2007
    },
    "MS2": {
      "order": "cut_after_floor"
    },
    "MS3": {
      "counting_rule": "own_worker_pia_only"
    },
    "MS4": {
      "window_rule": "after_policy_year"
    },
    "MS5": {
      "pia_rule": "benefit_implied"
    },
    "MS6": {
      "di_pia_rule": "statutory_computation_years"
    }
  },
  "snapshot": {
    "wave": 2023,
    "income_year": 2022
  },
  "population": {
    "presence": "sequence_1_20",
    "weight": "ER35265",
    "birth_year_law": "estimates.career.derive_birth_years",
    "born_on_or_before": 1960,
    "receipt": {
      "person_level": "ER35219",
      "family_file": [
        "ER85623",
        "ER85625"
      ]
    },
    "sex": "ER32000",
    "design": {
      "stratum": "ER31996",
      "cluster": "ER31997"
    }
  },
  "statistic": {
    "id": "dynasim_exercise4_share_receiving_minimum_income_year_2022",
    "formula": "100 * sum_i w_i A_k,i / sum_i w_i over the universe, per cell",
    "unit": "percent",
    "n_scored": false
  },
  "uncertainty": {
    "draws": 1,
    "floor": {
      "seeds": [
        0,
        1,
        2,
        3,
        4
      ],
      "fraction": 0.5,
      "split_unit": "family_unit_linked_by_person"
    },
    "design_se": {
      "method": "taylor_linearization",
      "stratum": "ER31996",
      "cluster": "ER31997"
    },
    "status": "not_built_m8"
  },
  "acceptance_rule": null,
  "labels": [
    "PSID-realized outcomes (not a projection)",
    "income year 2022 (not 2025)",
    "Python rules (not Axiom)",
    "static"
  ],
  "decisions_awaiting_max": {
    "target_cells": {
      "proposed_default": "table6_2025_options_2_to_5_by_all_men_women_headline_2_all",
      "decision_record": "d219",
      "item": 1
    },
    "claim_class": {
      "proposed_default": "track_m_static_psid_snapshot_income_year_2022",
      "decision_record": "d219",
      "item": 2
    },
    "policy_year": {
      "proposed_default": 2004,
      "decision_record": "d219",
      "item": 3
    },
    "covered_earnings_rule": {
      "proposed_default": "psid_labor_income_treated_as_covered",
      "decision_record": "d219",
      "item": 4
    },
    "order": {
      "proposed_default": "floor_after_cut",
      "decision_record": "d219",
      "item": 5
    },
    "di_proration": {
      "proposed_default": "elapsed_years_from_age_22",
      "decision_record": "d219",
      "item": 6
    },
    "counting_rule": {
      "proposed_default": "own_or_linked_worker_pia",
      "decision_record": "d219",
      "item": 7
    },
    "acceptance_rule": {
      "proposed_default": null,
      "decision_record": "d219",
      "item": 8
    },
    "ratification_and_registration": {
      "proposed_default": "ratify_by_merge_then_issue_42_registration_then_one_shot",
      "decision_record": "d219",
      "item": 9
    }
  },
  "decisions": {},
  "sources": {
    "plan": {
      "file": "critical-path-minimum-benefit-20260924.md",
      "revision": 2,
      "sha256": "976ec7f69bc9cc4999e8c7a74a1656f604f6ac3f0e0268e0c20e5fd4c6850e24"
    },
    "definitions_extract": {
      "file": "exercise4-definitions-cleared-20260924.md",
      "sha256": "54279fd1b79cdcfd9a33cb8572b53c4b207c7f5392e4a73b6afc798a166a83d7"
    },
    "availability_statement": {
      "file": "exercise4-target-availability-cleared-20260924.md",
      "sha256": "6db9b5bb76f7ae503d4f609233ea10b971adbfc4d39efe60aab46b258d4b708e"
    },
    "table2_page": {
      "pdf_page": 29,
      "ruling": "C5",
      "use": "formula_unit_tests_only"
    },
    "quarter_of_coverage_amounts": {
      "file": "policyengine_us/parameters/gov/ssa/social_security/quarters_of_coverage_threshold.yaml",
      "pe_us_revision": "a03e82e503",
      "sha256": "12354a0585756dbffcd9fae6aa6b49b2420619e9ec8e47c5ef953c41693f242b",
      "status": "read_from_checkout_not_captured"
    }
  },
  "blocked_by": [
    "max_ruling_d219_open",
    "census_aged_thresholds_not_captured_m2",
    "statute_413_415_not_captured_m2",
    "person_level_social_security_readers_m3",
    "beneficiary_cohort_m4",
    "realized_careers_m5",
    "tabulation_m8",
    "issue_42_registration_absent"
  ]
}
```

## 20. Pending decisions

None of these is ratified. Each is a parameter whose default is the
plan's proposal (or a builder choice where the plan is silent);
`min_benefit_track_m.policy.pending_decisions()` returns them with their
basis.

**Awaiting Max (cos decision d219, open, deadline 2026-09-30):**

1. `target_cells`: score Table 6's 12 printed 2025 cells, headline
   option 2, All; hold poverty for Track P (default).
2. `claim_class`: a static PSID snapshot for income year 2022, labelled
   not a projection, not 2025 and not Axiom (default).
3. `policy_year`: 2004 (default) or 2007 (MS1).
4. `covered_earnings_rule`: the rules in a new Python module outside
   `ss/` calling the oracle unchanged, and PSID labor income treated as
   covered earnings (default).
5. `order`: floor after the cut (default) or cut after the floor (MS2).
6. `di_proration`: *Y*·40 / elapsed years from 22 to onset, capped at
   40 (default).
7. `counting_rule`: own or linked worker's PIA (default) or own only
   (MS3).
8. `acceptance_rule`: none (default).
9. `ratification_and_registration`: Max ratifies by merge, posts or
   authorizes the #42 registration, then merges the run PR (default).

**Awaiting the specification freeze (defaults shown):** window rule (in
or after *Y*₀; MS4 after), PIA rule (history; MS5 benefit-implied), DI
PIA rule (approximation; MS6 statutory), death PIA rule
(approximation), DI proration start age (22), prorated-years rounding
(exact; floor), threshold rule (Census one person 65+ weighted
average), threshold year (eligibility year; DI onset year), wage-index
lag (2), pre-1978 coverage rule (1978 amount scaled back by AWI),
gap-year rule (neighbor mean; zero), unobserved-window start age (22),
couples' cap (none), unlinked auxiliaries (not receiving, counted
separately), minimum rounding (none; dime floor).

## 21. Questions for the referee

1. **Gap years.** Should a biennial gap year (1997–2021, odd) take the
   immediate-neighbor law before *Y* is counted (the default), or count
   as zero as G6 reads literally? The gap years are 22 percent of the
   window person-years of the 1945–1960 beneficiaries.
2. **Threshold year of a late claimer.** G4 keys the window on the
   entitlement year and G8 takes the eligibility year's threshold, so
   workers eligible before *Y*₀ enter the window (§4). Keep the
   eligibility year (and capture from about 1996), or use the threshold
   of the first year in the window?
3. **Prorated years.** Apply the schedule to an unrounded *Y*\* (the
   plan's case D, the default) or to its floor (G7: no partial years)?
4. **The end of *Y* for a DI worker.** G6 counts years before the
   entitlement year while G12's *D* ends at the year before onset.
   Should *Y* also end at the year before onset?
5. **A worker who died before eligibility.** Track A's approximation
   (the default) or the statutory death computation
   (`ss.statutory_aime.aime(..., death_year=...)`)?
6. **Other family-unit members** (103 of the 2,135 beneficiaries): their
   years as other members are unobserved in the earnings panel. Keep
   them with flagged histories, or register a row without them?
7. **Minimum rounding.** Unrounded (default) or floored to a dime?
8. **The widow(er) comparison.** `ss.benefits.widow_benefit` takes the
   survivor's own amount, PIA or reduced benefit, as the caller decides.
   Which should decide whether a survivor's benefit on a flagged record
   is paid?
9. **The flag window's start age:** 22 (the default, matching G12) or
   21 (415(b)'s elapsed years start after the year of attaining 21)?
10. **Before 1978:** is the scaled-back 1978 amount acceptable until M2
    reads 413(a)?

## 22. What this draft read and did not verify

**Read:** `EVID/RESTRICTED-FILES.md` first; the plan (revision 2) in
full; the two cleared files in full (hashes checked); the Report's PDF
page 29 as text; of the first plan version, the field rows G4–G13 by
`grep`; the cos record of d219 (its fields, to confirm it is open); in
the repository, `ss/benefits.py`, `ss/params.py`,
`ss/statutory_aime.py`, `cola_track_a/benefits.approximate_pia`,
`data/family.py` (the earnings panel), `data/psid.py`,
`data/social_security_income.py` (its conventions),
`cohorts/age67.py` and `cohorts/psid2010.py` (patterns),
`estimates/career.py` (the birth-year law and the gap law),
`estimates/cola_age_profile.py` (the ratification test), the U1 and A1
specifications and E1's on its branch, `scripts/run_track_a_registered.py`
and E1's entry script, the birth-evidence guard; the policyengine-us
quarter-of-coverage file; PSID setup-file labels and value formats for
the 2023 individual file and the 2023 family file.

**Ran on staged PSID:** label and code verification and the structural
counts of §10. No years of coverage, PIA, threshold, minimum, flag or
share receiving a minimum was computed on real data.

**Did not verify:** the Census threshold values and the layouts of the
workbooks after 2012; the statute text (413, 415) beyond the oracle's
quotation of 415(b); whose receipt the 2005 and 2007 "year before last"
items record; the PSID immigrant-refresher date; whether PSID Social
Security amounts are net of Medicare premiums; the top code of ER35219;
the fn. 27 blind check; the availability statement's findings against
the Report (they rest on the comparator side and the clearance review);
anything in the Report beyond PDF page 29 and the cleared files.

## 23. Changelog

- `m1-draft-1` (2026-09-24): first draft, with the Track M rules module,
  the structural counts in `EVID/track-m-structure-20260924/`, the
  registered entry point and the tests, on branch
  `dynamics-ex4-track-m-20260924`.
