# Minimum benefits comparison: specification draft for DynaSim scorecard exercise 4

- **Status:** draft with the referee's required changes applied
  (`EVID/minimum-benefits-referee-20260924.md`). Nothing here is ratified
  until the merge described next. Max ruled on exercise 4 on 2026-09-24:
  he accepted all nine defaults of the consolidated card (cos decision
  d219, status decided, ruled 2026-09-24 21:44; §20 records each item).
  Item 9 makes ratification a merge: merging the PR that carries the
  ratified text of this specification ratifies it, and the issue #42
  registration and the one-shot run follow. On 2026-09-25 he also ruled
  d279 (download the Census threshold workbooks for 2013-2022, plus any
  earlier year the build proves it needs) and d280 (PSID labor income
  treated as covered earnings, disclosed in the specification and every
  result); §20 records both. An independent check that this version
  applies the referee's required changes comes before the ratified text
  (§18). This draft authorizes no real-data run: the one-shot entry point
  (`scripts/run_track_m_registered.py`) refuses a block whose status or
  version is not ratified (§19).
- **Specification:** `urban2006_minimum_benefits_exercise4`, version
  `m1-draft-2`, drafted 2026-09-24 and revised 2026-09-25 to apply the
  independent referee's required changes R1-R10 (§21). §23 is the
  changelog.
- **Plan item:** M1 of the blind plan
  `EVID/critical-path-minimum-benefit-20260924.md`, revision 2
  (SHA-256 `976ec7f6…`), where `EVID` =
  `~/microcosm-launch-evidence/dynasim-parity-20260909`. The plan's
  section 7 (fields G1-G23, rows MS0-MS6) is the starting point. The
  plan names this file `urban2006_minimum_benefit_comparison.md`; the
  lane's brief named it `minimum_benefits_comparison.md`.
- **Template:** the structure of A1
  (`docs/design/urban2010_cola_comparison.md`, ratified), E1
  (`docs/design/urban2010_fra68_comparison.md`, `e1-ratified-1`, on the
  branch of PR #461, `dynamics-ex3-ratify-20260924`, not on master; its
  §22 "Decisions (ruled by Max)" is the form of §20 here) and U1
  (`docs/design/boomers2004_uniform_cut_comparison.md`).
- **Claim class (d219 item 2, accepted 2026-09-24):** a static
  measurement on a PSID snapshot for income year 2022, not a projection.
  It does not test the Dynamics projection engine.
- **Labels every output carries:** *PSID-realized outcomes (not a
  projection)*; *income year 2022 (not 2025)*; *Python rules (not
  Axiom)*; *static* (`min_benefit_track_m.OUTPUT_LABELS`). **Disclosure
  every result carries (d280):** PSID labor income is treated as covered
  earnings, because the PSID does not observe Social Security coverage
  (`min_benefit_track_m.COVERED_EARNINGS_DISCLOSURE`).
- **Builder boundary:**
  - A model-builder lane (Claude Code subagent, Opus 5.5) wrote
    `m1-draft-1`. It read `EVID/RESTRICTED-FILES.md` (SHA-256
    `b483d32d…`, last changelog entry 2026-09-24 19:20) before any other
    file and opened nothing it restricts. Of the Report it read PDF page
    29 only, as text (`pdftotext -layout -f 29 -l 29`), for formula unit
    tests (ruling C5). It did not open the Report's other pages or its
    `.txt` extraction, any comparator directory, seal, reconciliation or
    values scan, the uncleared sources of the two cleared files, or
    `EVID/scratchpad-archive-20260924/`. It computed no share receiving a
    minimum, no years of coverage and no PIA on real data.
  - A second builder lane (Claude Code subagent, Opus 5.5) wrote
    `m1-draft-2`. It read `EVID/RESTRICTED-FILES.md` (SHA-256
    `2fc9bdbf…`, last changelog entry 2026-09-25) before any other file
    and opened nothing it restricts. It did not open the Report in any
    copy, any comparator directory, seal, reconciliation or values scan,
    the uncleared sources of the cleared files, the scratchpad archive,
    or any exercise-1 result. It read no PSID file and computed no
    statistic on real data. §22 lists what each lane read.
- **Disclosure that travels with this specification (plan section 11,
  R5):** the clearance follow-up of 2026-09-24 14:15 found that the
  withheld Table 5 note sentence (ruling C2) lies inside the text lines
  the plan's first version says its author read. That sentence
  characterizes Table 10 (expenditure paths), which is not an exercise-4
  target. Neither builder lane read it. Of the first plan version
  (`EVID/revisions/critical-path-minimum-benefit-20260924-v1.md`,
  `7aa600e1…`) the `m1-draft-1` lane read only field rows G4, G5, G6, G8,
  G9, G11, G12 and G13 (v1 lines 374-376, 378-379 and 381-383), through
  one `grep` whose command and printed row labels its session record
  holds. The `m1-draft-2` lane recovered those labels from that record
  and printed nothing else of v1 but its field-row labels (G1-G21).

## 1. Target

The target is Table 6 of Favreault, Mermin and Steuerle, *Minimum
Benefits in Social Security* (Urban Institute, August 2006), its 2025
block, as the cleared availability statement
(`EVID/exercise4-target-availability-cleared-20260924.md`, `6db9b5bb…`,
item Y1) describes it. Neither builder lane has seen the table.

- **Measure:** the percentage of OASDI beneficiaries aged 62 and older
  who receive a minimum benefit (Table 6's title, cleared extract).
  Footnote 33 (cleared extract) says the measure identifies the people
  who receive the minimum, which is not the number of people whose
  benefit is higher than under the option-1 baseline.
- **Options:** Table 5's options 2-5 only, printed in the column order
  3, 2, 5, 4. There is no option-1 column and no change column: each
  cell is a level under one option.
- **Rows:** All, with Men and Women nested under All.
- **N:** one N column per row; no table states its unit. N is reported
  as a diagnostic and never scored.
- **Cells scored:** 12 (four options by three rows). **Headline,
  designated before any result:** option 2, All (plan R2; d219 item 1,
  accepted 2026-09-24).
- **Text restatements:** body text on PDF page 17 restates the four
  2025 All cells (Y2) and calls the denominator persons who have Social
  Security income (D2). One text-only 2025 ratio compares receipt of
  the minimum by women and by men under option 3 (Y3); the text does
  not say whether it is a ratio of rates or of recipient counts. Y3 is
  reported both ways and not scored separately.
- **What is not printed:** any 2025 poverty statistic, in any form, for
  any option (availability statement, bottom line 1). Quantified poverty
  outcomes of the options are printed for 2050 only (Table 9 and the
  Poverty Level rows of Tables 7 and 8); the Conclusions and the PDF
  abstract state poverty effects qualitatively, with no year
  (availability P6, P7). They belong to the projected Track P (plan
  section 12) and are out of this specification.

The comparator values are sealed on the comparator side
(`EVID/exercise4-comparator-seal-20260924.json`, not opened by either
builder lane).

## 2. Sources

| Source | Use | Status |
|---|---|---|
| Plan, revision 2 (`976ec7f6…`) | Fields G1-G23, rows MS0-MS6, the INVENTED cases, the decision card | Read in full (`m1-draft-1`) |
| Cleared definitions extract (`54279fd1…`) | Table 5 as transcribed; fn. 25-33; the population sentence; fn. 35; Table 6's title, labels and units; Table 2's limits; rulings C1-C5 | Read in full (`m1-draft-1`) |
| Cleared availability statement (`6db9b5bb…`) | Y1-Y3, D1-D16, the "not printed" checks | Read in full (`m1-draft-1`) |
| Report, PDF page 29 (Table 2) | Formula unit tests only (C5, §17) | Read as text (`m1-draft-1`) |
| Referee report, `EVID/minimum-benefits-referee-20260924.md` (`49091254…`) | Required changes R1-R10, answers to §21's questions | Read in full; applied (§21) |
| Oracle, `src/populace_dynamics/ss/` | AIME, PIA, reductions, credits, spouse's and widow(er)'s benefits | Read; called unchanged |
| `cola_track_a/benefits.approximate_pia` | The DI PIA under MS6 | Read; called unchanged |
| policyengine-us `quarters_of_coverage_threshold.yaml` at `a03e82e503` (SHA-256 `12354a05…`) | Quarter-of-coverage amounts, 1978 on | Read from the checkout; not a committed capture (M2) |
| PSID 2023 wave, family files 1968-2023, marriage history | Structural counts (§10) | Staged; labels verified |
| Census historical poverty-threshold workbooks `thresh03.xlsx`-`thresh22.xlsx` | The threshold that defines the minimum (G8, §7) | **Captured** 2003-2022 (d194, d279): `data/external/census_poverty_thresholds_2003_2022.json` (SHA-256 `65bbcd83…`) |
| 42 USC 413(a)-(d); 20 CFR 404.141 and 404.143 | Quarters of coverage (§5), DI coverage end (§4a) | **Not captured** (M2). Review copies: 413 and 20 CFR 404.141 and 404.143 in `EVID/track-m-review-20260924/`; 402 in `EVID/minimum-benefits-referee-20260924/`; the oracle's `statutory_aime` quotes 415(b) (text `5b41d1cd…`) |
| 42 USC 415(b)(2)(B)(ii) | The end of an old-age PIA's history (§4a) | Read in the text `5b41d1cd…` (encoder workspace copy) |
| 42 USC 402(k)(3)(A) | The survivor's own amount (§4b rule 5) | Read in the referee's extract (`43d5e10a…`) and its page copy (`e5bb977c…`) |
| 42 USC 415(i)(2)(A)(iii) | MS5's COLA factor (§6) | Read in `EVID/tr2008-inputs-20260922/usc-42-415-excerpts.txt` (`a323ca47…`) |

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

Options 6-10 are recorded for completeness; they belong to Track P.

**Rules common to every option** (paraphrased from the cleared
extract, with locators):

- **Effective date:** all options take effect in 2007 (Table 5 notes;
  PDF p. 15). The uniform cuts apply across the board to new entitlees
  and target cost equivalence in 2050 (Table 5 notes). The
  cost-neutrality passage on PDF p. 14 (cleared extract) words the
  covered years two ways: benefits reduced "for all persons becoming
  entitled starting in the year the simulations take effect (2007)", and
  cuts "for those entitled after 2007"; the results text has the same
  split (D9, paraphrased).
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
  including disabled workers aged 62-64 and formerly disabled workers
  converted to retired-worker benefits (PDF p. 20, cleared; D6).
- **Children's benefits:** DYNASIM has none (fn. 35). The family
  maximum is not mentioned anywhere (availability §6). No couples' cap
  on minimum-based benefits appears to have been simulated (D7, an
  inference).

**Track M's reading** (`min_benefit_track_m.policy`, the plan's
section 7): options 1-5 with the schedules and cuts above;
`TrackMPolicy` holds every choice, each at Max's ruling or at its frozen
value (§20); `REGISTERED_ROWS` holds MS0-MS6 (§14).

## 4. Who the reform reaches

- **Policy year (G2; d219 item 3, accepted 2026-09-24).** Every policy
  date moves back three years: the policy year *Y*₀ is 2004, and the
  wage-indexed minimum's base year moves with it. The 2022 snapshot then
  exposes 19 entitlement cohorts (2004-2022), as DYNASIM's 2025 exposes
  2007-2025. **MS1** keeps the Report's dating (*Y*₀ = 2007; 16
  cohorts). The cohort counts are the plan's deductions from the dating,
  not results.
- **Window (G4).** A PIA whose window year (§4a) is in or after *Y*₀ is
  cut and floored; **MS4** requires after *Y*₀. `rules.in_window`.
- **Scope (G11).** A PIA whose window year precedes *Y*₀ is untouched
  under every option (*O* = 0). An auxiliary is reached only through a
  worker whose PIA's window year is in the window. That the minimum
  reaches new entitlees only is an inference from fn. 26 and the
  effective date (plan R4).
- **DI conversion.** The flag is set at the DI PIA's calculation and
  carries over at conversion to a retired-worker benefit (G12; fn. 26:
  the minimum is set at PIA calculation).
- **Entitlement classification** is plan item M4. §4b freezes the rules
  it applies to the receipt histories (the person-level Social Security
  items of waves 1984-1992 and 2005-2023, the 2005 and 2007 "year before
  last" items, family-file head and wife items, and the age rule for
  later entrants). Nothing here classifies anyone.
- **Finding (threshold years before *Y*₀).** Under G4 the window keys
  on the year the PIA was first calculated, while G8 takes the threshold
  of the §4a threshold year. A worker who first claims in or after *Y*₀
  but became eligible before it is in the window with a threshold year
  before *Y*₀. With *Y*₀ = 2004 a worker entitled at 70 in 2004 became
  eligible in 1996; a worker who died before any entitlement (§4a) can
  have a threshold year earlier still. A disability-origin record cannot:
  its onset year is its entitlement year less one (§4b rule 4), so at
  *Y*₀ = 2004 its threshold year is 2003 or later. M2 has captured the
  Census one-person 65+ weighted-average thresholds for 2003-2022 (§7);
  M4's structural count of in-window records reports the earliest
  threshold year needed (a year, not a threshold). The registered run
  refuses, before computing anything, if a needed year is missing, and
  the M10 dry run checks that every threshold year the invented cohort
  needs is present.

### 4a. The years that define each record (frozen)

A worker record's basis comes from §4b. For each basis:

| Basis | Window year (G4: "first calculated") | Threshold year (G8) and PIA bend-point year | Last year of *Y* (G6) and of *P*'s history (G5) | *P* |
|---|---|---|---|---|
| Old age | The first year of the worker's own entitlement | The year of attaining 62 | The window year − 1 | `ss.statutory_aime.aime` over that history and `ss.benefits.pia` at the year of attaining 62 |
| Disability origin | The first year of the worker's own DI entitlement | The onset year | The onset year − 1 | §6 (statutory DI computation; MS6 the approximation) |
| Died before any own entitlement | The first year a person in the universe is entitled to a benefit on the record | The earlier of the death year and the year of attaining 62 | The death year − 1 | §6 (statutory death computation) |

- The old-age row follows 42 USC 415(b)(2)(B)(ii)(I): an old-age PIA's
  computation base years end before the year of first entitlement. That
  replaces the plan's G5 reading ("through the year before
  eligibility"). Earnings from the year of attaining 60 on enter
  unindexed (`ss.benefits.indexed_history`). There is still no
  recomputation for later earnings.
- The disability row follows G12 and 413(a)(2)(B)(i) (no quarter inside
  a period of disability, other than its first and last, is a quarter of
  coverage). The years before 22 count in *Y*, so *Y* may exceed *D*;
  *Y*\* is capped at 40 (d219 item 6).
- The death row counts through the year before death.
  415(b)(2)(B)(ii)(II) would include the death year in the base years; it
  is dropped as a named approximation, because a partial year rarely
  reaches four quarters' amount and the PSID reports it incompletely.
- A disability-origin record keeps its basis at conversion: the flag is
  set at the DI PIA's calculation and carries over (fn. 26).
- *Y* and *P* read one history per worker: observed years, then the
  next-wave odd-year items, then the gap rule (§5); a year still
  unobserved is zero in both.

`rules.record_years` implements the table; `rules.history_pia` cuts the
history at its last year and computes the PIA at its threshold year.

### 4b. Classification rules (frozen; M4 implements them)

1. **Basis.**
   - A worker record is *disability origin* if its first observed own
     receipt carries a disability type mention, or begins before the
     year of attaining 62. Otherwise it is *old age*.
   - A record whose type is unknown or "other" in every observed wave
     takes the age rule: old age if first receipt is at or after 62,
     disability origin if before.
   - A linked deceased worker with no observed own receipt, who died
     before the survivor's first entitlement on the record, is *died
     before any own entitlement*.
2. **Entitlement year (the window year of §4a).**
   - The first year consistent with the observations: the later of the
     earliest year the basis allows (the year of attaining 62 for old
     age; the onset year for disability origin) and the year after the
     last observed year without own receipt that precedes the first
     observed year with it.
   - A record with receipt in its first observed year has an unresolved
     entitlement year and is classified by rule 3.
3. **Window membership at *Y*₀ = 2004 (MS0) and 2007 (MS1)** (the plan's
   section 4 rules):
   - *Y*₀ = 2007. A person with no own receipt in income year 2006 and
     own receipt by 2022 is in the window. So is a later PSID entrant
     born 1945 or later with a retirement type.
   - *Y*₀ = 2004.
     - Receipt in 2004 comes from the 2005 wave's person-level items.
       Receipt in 2003 comes from the 2005 family file's year-before-last
       items, if M3 shows they identify the person.
     - A person with no own receipt in 2004 and own receipt by 2022 is
       in the window. A person with own receipt in 2004 and none in 2003
       is in the window, with 2004 as the entitlement year. A person
       with own receipt in both years is out.
     - A person with receipt in 2004 and unknown status in 2003 is in
       the window if born 1942 or later with a retirement type, and out
       otherwise. Either way the person is counted as unresolved.
     - A later PSID entrant born 1942 or later with a retirement type is
       in the window.
   - Unresolved counts are reported for each row.
4. **Onset year (disability origin).**
   - The entitlement year − 1 (builder default).
   - The DI waiting period puts onset in the entitlement year or earlier.
     Neither the referee nor the `m1-draft-2` lane read 42 USC 423; M2's
     statute capture confirms it.
5. **Auxiliary benefits paid (G13).**
   - A spouse's benefit is possible only when the linked worker is alive
     and receives OASDI in 2022. It is paid when
     `ss.benefits.spousal_benefit` on the option PIAs is positive, the
     spouse's own amount being their own option PIA (0 with no own
     record).
   - A survivor's benefit is possible only when the linked worker is
     deceased. It is paid when `ss.benefits.widow_benefit` exceeds the
     survivor's own amount.
   - The own amount is the survivor's own old-age or disability benefit
     after the 402(q) reduction under the option: the own option PIA ×
     the own claim factor, or 0 when the survivor receives no own benefit
     in 2022 (42 USC 402(k)(3)(A); `rules.survivor_own_amount`).
   - Claim ages come from rule 2's entitlement years, as whole years
     (entitlement year − birth year), against the cohort's full
     retirement age (`rules.claim_factor` for a worker's own factor).
6. **Other family-unit members** stay in the universe with flagged
   histories (§21, Q6).
7. **Sex.** ER32000 code 9 counts in All and in neither Men nor Women.
   The current universe has none (§10).

## 5. Years of coverage

`min_benefit_track_m.coverage.count_coverage_years` (G6, G7):

- ***Y*** counts the years through the last year §4a gives for the
  record's basis whose covered earnings reach four times the year's
  quarter-of-coverage amount (Table 5: a work year is 4 covered
  quarters). All ages count. The caller passes the end year (M4).
- **Covered earnings (d280, ruled 2026-09-25):** PSID labor income is
  treated as covered earnings. The PSID has no covered/noncovered split
  (plan section 5); noncovered public employment therefore counts
  (named delta). Max's ruling adds that the convention is disclosed here
  and in every result; the tabulation carries
  `COVERED_EARNINGS_DISCLOSURE`.
- **Quarter-of-coverage amounts, 1978 on:** read from the
  policyengine-us checkout the oracle reads (the file cites 42 USC
  413(d)(2), 20 CFR 404.143 and SSA's QC table), with its revision and
  SHA-256 recorded (`load_qc_amounts`). This is not the committed
  capture M2 calls for. Check: four times the 2006 amount is $3,880,
  the figure Table 2 prints in the label of rows 3a-3d (§17).
- **Before 1978 (statute, frozen):** 42 USC 413(a)(2)(A)(i) and 20 CFR
  404.141(b) credit a quarter of coverage for $50 of wages paid in it or
  $100 of self-employment income credited to it. With annual amounts,
  and wages taken as spread over the year, a year counts as a work year
  at $200 (`pre_1978_coverage_rule = "statute_413_a_50_per_quarter"`).
  This reading does not separate self-employment income ($400 a year on
  the same reading) or agricultural wages (413(a)(2)(B)(iv); 20 CFR
  404.141(c)), and it credits four quarters to a year whose $200 was paid
  in fewer quarters (a named delta). 413(a)(2)(B)(ii) and 20 CFR
  404.141(d)(1) credit all four quarters when a year's wages reach the
  annual limitation. The plan's G6 convention (the 1978 amount scaled
  back by AWI: about $528 in 1968 and $926 in 1977 with the oracle's
  AWI) has no statutory basis and is not registered. It counts fewer
  pre-1978 years for low earners than the statute. Table 2's rows 3b-3d
  agree with the statutory reading (§17, finding 3); that is a unit-test
  finding under ruling C5, not the basis of this rule.
- **From 1978 (statute, as coded):** 413(a)(2)(A)(ii) and 20 CFR
  404.143(a) credit one quarter for each quarter-of-coverage amount of
  the year's wages and self-employment income, at most four, so a year
  with four quarters' amount is a work year.
- **Odd income years 1997-2021:** the earnings panel (`data/family.py`)
  carries no odd income year from 1997. **Correction (independent
  review):** the draft said the PSID never collected them. By the family
  files' labels, the labor income of 1997 and 1999 was never asked, but
  that of each odd year 2001-2021 was asked one wave later as the
  reference person's and the spouse's labor income of the year before
  last (for example ER85328 and ER85376 in the 2023 file, each with a
  time-unit and an accuracy variable);
  `structure.verify_prior_year_labor_income_labels` checks the labels
  wave by wave. Frozen: M3 reads, and M5 uses, the next-wave
  year-before-last labor income of the reference person and of the
  spouse for each odd year 2001-2021 (for example ER85328 and ER85376 in
  the 2023 file), annualized by its time-unit variable, before any
  imputation (`odd_year_source = "next_wave_reference_person_and_spouse"`).
  Before M5 uses them, M3 records from labels and codebook text only
  whether each item is the person's labor income of that year in the
  concept of the panel's constructed totals, and names any difference as
  a delta. An odd year 1997-2021 still unobserved then takes the
  immediate-neighbor law of `estimates.career` (`gap_year_rule =
  "immediate_neighbor_mean"`: the mean of the two neighboring years, or
  the one that exists; never a neighbor after the count's end year). A
  year still unobserved after that counts as zero and is flagged. The
  years of coverage and the PIA read this one history (§4a;
  `coverage.one_history`). The alternative `"zero"` is not registered.
- **Unobserved years** (neither observed nor imputed) count as zero
  and are flagged, over a flag window from the year of attaining 22
  (builder default, matching G12's start).
- **DI proration (G12; d219 item 6, accepted 2026-09-24):** *Y*\* =
  *Y*·40/*D*, where *D* counts the elapsed years from the year of
  attaining 22 through the year before onset, bounded to [1, 40]; the
  schedule applies to min(*Y*\*, 40), including the 10-year floor
  (`rules.prorated_work_years`). *Y*\* is not rounded (as in the plan's
  INVENTED case D, where 15 years of 22 possible give *Y*\* = 27.27 and a
  minimum of $674.24; referee Q3); the alternative floors it and is not
  registered.

## 6. The PIA

`rules.history_pia` calls the oracle unchanged (G5) over the one history
of §4a, cut at its last year. What the oracle does, as read:

- **Old age:** the history through the window year − 1 (§4a); the AIME
  by `ss.statutory_aime.aime` (42 USC 415(b)(2) computation years; its
  docstring says it equals `ss.benefits.aime` exactly for birth years
  1929 and later, and a test here confirms it on an invented history);
  the PIA by `ss.benefits.pia`: 90, 32 and 15 percent over the bend
  points of the year of attaining 62, rounded down to a dime. No
  recomputation for later earnings.
- **DI (G5, frozen):** `ss.statutory_aime.aime(..., disability_year=onset)`
  (42 USC 415(b)(2)(A)(ii): elapsed years less one-fifth, at most 5, at
  least 2) over the history through the year before onset, and
  `ss.benefits.pia` at the onset year's bend points. **MS6:** Track A's
  disclosed `approximate_pia` (the oracle's 35-year AIME through the year
  before onset, indexed to the second year before onset, at the onset
  year's bend points). Its docstring says the 35-year divisor
  understates short careers and that it sets a weight, never a reform
  ratio; on the tests' invented history it gives 51, 71 and 86 percent of
  the statutory DI PIA for onset at 34, 44 and 52, and an understated PIA
  flags too many workers (plan section 1).
- **A worker who died before any own entitlement (frozen):**
  `ss.statutory_aime.aime(..., death_year=death)` (415(b)(2)(A)(i):
  elapsed years less 5) over the history through the year before death
  (§4a), and `ss.benefits.pia` at the threshold year of §4a.
- **MS5 (frozen):** the PIA implied by the observed 2022 benefit, *B* /
  (claim factor × COLA factor) (`rules.benefit_implied_pia`), for a
  worker record whose 2022 person-level amount (ER35219) is its own
  worker benefit alone. A person with a spouse, survivor or dependent
  type mention in 2022, and a linked worker who is deceased or outside
  the universe, keeps the MS0 PIA. *B* is ER35219 converted to a monthly
  amount by the unit M3 verifies from the label and codebook. If M3's
  reading of the question wording finds amounts reported net of the
  Medicare premium, the premium is added back and the source recorded;
  otherwise the amount is taken as gross, and that reading is recorded.
  The claim factor is the 402(q) reduction or 402(w) credit for the
  claim age of §4b (1 for a disability-origin record;
  `rules.claim_factor`). The COLA factor is the product of the COLAs from
  the December of the threshold year of §4a through December 2021
  (`data/external/ssa_cola_history.json`; `rules.cola_factor`). The
  referee did not read 415(i); the `m1-draft-2` lane read
  415(i)(2)(A)(iii) in `EVID/tr2008-inputs-20260922/usc-42-415-excerpts.txt`
  (`a323ca47…`): an individual who becomes eligible for an old-age or
  disability benefit, or dies before becoming so eligible, in a year in
  which an increase occurs has the PIA raised by that increase and
  subsequent ones, "without regard to the time of entitlement". The COLA
  history file records that from 1983 each COLA is effective in December
  of its determination year and first reflected in January payments of
  the next, so benefits paid for 2022 reflect the COLAs determined
  through 2021.

*P* is monthly, in the threshold year's dollars, at the first
calculation. So is the minimum (§7), so the dollar level cancels (plan
section 3).

## 7. Threshold and indexing

- **Threshold (G8):** the Census weighted-average poverty threshold for
  one person aged 65 and older, of the record's threshold year (§4a).
  **Captured** (M2; cos decisions d194 and d279): the twenty Census
  workbooks `thresh03.xlsx`-`thresh22.xlsx` are committed in
  `data/external/census_poverty_thresholds/` and pinned by SHA-256, and
  `scripts/capture_track_u_parameters.py --track-m-census-dir` writes
  `data/external/census_poverty_thresholds_2003_2022.json` (SHA-256
  `65bbcd83…`, pinned in `min_benefit_track_m.thresholds`).
  `rules.load_aged_thresholds` reads its `one_65_plus` weighted average
  ("One person (unrelated individual)", "65 years and over") for
  2003-2022. Table 2's HHS threshold is not borrowed (D15).
- **Layouts** (every workbook inspected cell by cell, 2026-09-25): all
  twenty print one table in the same 91 cells. The parser, extended from
  Track U's rather than duplicated, accepts two departures, each pinned
  to its year: `thresh19.xlsx` carries two further worksheets that must
  be empty, and `thresh22.xlsx` prints every weighted average rounded to
  $10 while its matrix cells stay whole dollars. For one person 65+ it
  prints 14,040 beside a single matrix cell of 14,036; Track M reads the
  weighted average as printed (a $4 named delta in 2022 only). Every
  matrix cell moves from one year to the next by one ratio within $2,
  2003-2022.
- **Which threshold years Track M needs, and why:**
  - **Wage-indexed options 3 and 5** need the policy year's threshold:
    *T*(2004) for MS0 and MS2-MS6, and *T*(2007) for MS1.
  - **Price-indexed options 2 and 4** need the threshold of each
    in-window record's §4a threshold year, looked up only when *Y*\* ≥ 10
    (`rules.evaluate_worker`). The universe is born 1960 or earlier
    (§10), so no threshold year is later than 2022. At *Y*₀ = 2004:
    - an old-age record's threshold year is its year of attaining 62,
      2003 for one born in 1941 and earlier than 2003 for one born in
      1940 or earlier (first own entitlement at 64 or older, in 2004 or
      later);
    - a disability-origin record's is its onset year, the entitlement
      year less one (§4b rule 4), so 2003 or later (2006 or later at
      *Y*₀ = 2007);
    - a death-basis record's is the earlier of the death year and the
      year of attaining 62: earlier than 2003 when the worker died before
      2003 or was born in 1940 or earlier, although the survivor's first
      entitlement on the record, its window year, is 2004 or later.
  - **So 2003-2022 covers every in-window record except two kinds:**
    old-age records born in 1940 or earlier, and death-basis records whose
    worker died before 2003 or was born in 1940 or earlier. The universe
    holds 234 beneficiaries born in 1941 or earlier (§10), and 109 with a
    survivor type mention; those are candidates, not in-window counts.
    Whether any record of either kind is in the window is M4's structural
    count (the earliest threshold year among in-window records; a year,
    not a threshold), which needs M3's receipt readers.
  - **No year before 2003 is captured.** If M4 reports one, it needs a
    Census download before the registered run: d279 covers "any earlier
    year the build proves it needs", captured, hashed and pinned like the
    2003-2022 capture. `rules.check_threshold_years` refuses a cohort that
    needs a missing year before anything is computed, with a named error
    (`ThresholdYearMissingError`, not a `KeyError`), and
    `AgedThresholds.for_year` raises the same error.
- **Price indexing (options 2 and 4):** the threshold of the year
  itself (the thresholds move with prices, D5).
- **Wage indexing (options 3 and 5; G9):**
  *T*(*Y*₀)·AWI(*e* − 2)/AWI(*Y*₀ − 2). The two-year lag is a builder
  default (bend points use the second year before). At *e* = *Y*₀ the
  wage-indexed minimum equals the price-indexed one. The AWI is the
  oracle's `SSAParameters.nawi`.
- **Monthly minimum:** *M*ₖ = *s*ₖ(*Y*\*)·*T*/12, unrounded (frozen,
  referee Q7; the alternative floors it to a dime as 415(g) rounds a PIA,
  and is not registered).
- **No re-determination** after the first calculation (fn. 26(2)).

## 8. Order of the cut and the minimum, and the worker flag

- **Order (G10; d219 item 5, accepted 2026-09-24):** the minimum is a
  floor after the cut, max((1 − *c*ₖ)·*P*, *M*ₖ). **MS2:** the cut applies
  after the floor, max(*P*, *M*ₖ)·(1 − *c*ₖ). The Report prints no rule;
  the results text's mechanism sentence (D10: the benefit reduction
  itself makes more people qualify) supports G10 by the comparator side's
  inference.
- **Worker flag (G22):** *O*ₖ = 1 when the PIA's window year is in the
  window, *Y*\* ≥ 10 and *M*ₖ > (1 − *c*ₖ)·*P* (MS2: *M*ₖ > *P*), fixed at
  the first calculation (`rules.evaluate_worker`). Option 1 has no
  minimum and every flag is 0.
- **Deductions used as unit tests (plan section 1), not results:** at
  the same threshold year and PIA, option 2's flagged set lies inside
  option 4's and option 3's inside option 5's, under either order; a
  worker on option 2's minimum is on option 3's whenever option 3's
  wage-indexed threshold is at least option 2's price-indexed one
  (because *c*₃ > *c*₂).

## 9. Who counts as receiving the minimum

- **G23 (d219 item 7, accepted 2026-09-24):** *A*ₖ = 1 for a person paid,
  in 2022, a Title II benefit computed from a PIA that rests on the
  minimum: their own worker PIA (*O*ₖ = 1 and an own worker benefit
  paid), or a linked worker's PIA from which a spouse's or survivor's
  benefit they are paid is computed. **MS3:** own worker PIA only
  (`rules.receives_minimum`).
- **Whether an auxiliary benefit is paid (G13; §4b rule 5):** the oracle
  decides, on the worker's option PIA: `ss.benefits.spousal_benefit`
  (one-half of the worker's PIA less the spouse's own option PIA, reduced
  for early claiming; paid when positive) and `ss.benefits.widow_benefit`
  (paid on the deceased's record when it exceeds the survivor's own
  benefit after 402(q)). Dual entitlement is included; there is no
  couples' cap.
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
  year at all. For the 1,769 born 1945–1960, the odd years the panel
  lacks are 15,869 of 70,760 window person-years (22 percent).
- **Odd years split by what the family files ask** (independent
  review; `scripts/track_m_structure.py` rerun at commit `49f76d8f` on
  a clean tree, `EVID/track-m-structure-20260924-r2/track-m-structure.json`,
  SHA-256 `829ed395…`; every count above is unchanged and the same 91
  PSID files were read with the same hashes): of the 16,781 odd-year
  person-years, 4,064 fall in 1997 or 1999 (never asked) and 12,717 in
  2001–2021 (asked one wave later). For the 1,769 born 1945–1960: 3,538
  never asked (5 percent of 70,760) and 12,331 asked next wave (17
  percent). The rerun also records, from the labels of the 1999–2023
  family files, the next-wave variables for each odd year.
- **What the counts imply for M4 and M5 (not a result):** the earnings
  panel (`data/family.py`) carries head and spouse labor income only,
  so years spent as another family member are unobserved. Reading the
  next-wave items (M3, M5) would observe the odd years 2001–2021 of
  anyone who was the reference person or spouse in the following wave
  (how many is not counted here); the gap-year rule (§5) would then
  decide 1997, 1999 and the odd years of other members.

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

The Track U pattern (G19): deterministic (K = 1); a five-seed (0-4)
person-disjoint half-split floor on family units linked through shared
persons; a design-based standard error by Taylor linearization with
ER31996 and ER31997. **Not built** (plan item M8).

## 13. Acceptance rule

**None** (d219 item 8, accepted 2026-09-24). The comparison is reported,
not gated; it runs once and is published regardless. No rule may be set
after registration.

## 14. Registered rows

Each row changes one field from MS0 and reports all 12 cells; MS0 is
the scored row, designated before any result, and no row may be
promoted afterwards.

| Row | Field changed | Value | Rules built |
|---|---|---|---|
| **MS0** | — | §§4-9 primaries (*Y*₀ = 2004) | Yes |
| MS1 | `policy_year` | 2007 (the Report's dating; 16 cohorts) | Yes |
| MS2 | `order` | Cut after the floor | Yes |
| MS3 | `counting_rule` | Own worker PIA only | Yes |
| MS4 | `window_rule` | After *Y*₀ | Yes |
| MS5 | `pia_rule` | Benefit-implied PIA | Arithmetic yes; its inputs are M4's and M5's (§6) |
| MS6 | `di_pia_rule` | Track A's DI approximation (35-year divisor) | Yes |

## 15. Named deltas

Carried on every output (plan section 7), plus those found while
building:

- realized 2022 against DYNASIM's projected 2025;
- exposure: aligned in MS0 with a residual age-structure delta; 16
  against 19 cohorts in MS1;
- realized AWI and CPI against the 2005 Trustees paths;
- PSID against SIPP population and weights;
- labor income treated as covered earnings (d280, disclosed in every
  result);
- pre-1968 and pre-entry years;
- the odd income years: 1997 and 1999 never asked; 2001-2021 asked a
  wave later, for the reference person and spouse only (§5);
- pre-1978 quarters read from annual amounts ($200 a year spread over
  four quarters; §5);
- the death year dropped from a death-basis record's history (§4a);
- unlinked auxiliaries;
- entitlement classification at the 2004 boundary;
- no windfall-elimination rule applied to the minimum;
- no recomputation for later earnings;
- children's benefits: DYNASIM has none (fn. 35); a PSID beneficiary
  aged 62+ paid as a child is a delta;
- the stock date: persons who received OASDI in 2022 but died or moved
  out before the 2023 interview are outside the universe, while Table 6
  counts a point-in-time stock (referee O4);
- **found:** the earnings panel observes head and spouse labor income
  only, so a beneficiary's years as another family member are
  unobserved (§10);
- **found:** thresholds are needed for eligibility years before *Y*₀
  (§4, §7);
- **found:** the 2022 Census workbook prints weighted averages rounded to
  $10 (one person 65+: 14,040 against a matrix cell of 14,036; §7).

## 16. Invented worked cases

**INVENTED** inputs: a one-person aged threshold of $10,000 a year, an
invented wage index and made-up PIAs; no Census value, PSID value,
model output or comparator value. The schedules and cuts are Table 5's.
The plan's author computed cases A-I independently of this code; the
tests (`tests/min_benefit_track_m/test_rules.py`) recompute each, and
the referee recomputed each in a script that imports no repository code.

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
10,000 × 46,000 / 40,000 = $11,500; the statutory DI PIA (MS0) uses 18
computation years for onset at 44 (22 elapsed years less 4) and MS6's
approximation uses 35, which gives 51, 71 and 86 percent of the
statutory PIA for onset at 34, 44 and 52 on a flat $20,000 history; a
late claimer entitled at 65 whose earnings at 62-64 replace zeros among
the 35 years has a higher *P* than at 62 (§4a); a DI worker's earnings
in and after the onset year change neither *Y* nor *P*.

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
  policyengine-us series is $3,880, the page's figure for rows 3a-3d.

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

3. (Independent review, 2026-09-24.) Rows 3b-3d ("exactly 4 CQ
   threshold in all years", work from 1963 for the 1943 cohort) follow
   the statute's pre-1978 quarter of coverage, $50 of wages a quarter,
   and not the plan's G6 convention. With four quarters' amount from
   1978 and, before 1978, either reading, the oracle's statutory AIME
   and PIA at the 2005 bend points give PIA ratios 3b/3d = 0.132 and
   3c/3d = 0.338 under the statute, inside the printed rounding of
   columns 1 and 2 (3/20 and 3/27; 7/20 and 9/27), and 0.275 and 0.551
   under the convention, outside all four. Ratios within a column need
   neither the HHS threshold nor the claim-age factor. This is a formula
   check under ruling C5, not a calibration and not the basis of the
   rule: the statute decides (§5), and Table 2 agrees with it. The 3b/3d
   ratio under the statute, 0.1316, lies close to column 2's upper bound
   of 0.1321, so that comparison discriminates weakly; the other three
   are clear.

The SSI columns (3 and 4) are outside Track M and were not checked.

## 18. What is built and what is blocked

Built on branch `dynamics-ex4-track-m-2-20260925`, which carries PR
#460's Track M foundation and PR #462's Track U Census capture (all
opt-in; each module registered in `POST_REVIEW_SOURCE_EXCLUSIONS`, the
pinned tuple and the reachability guard):

- `src/populace_dynamics/min_benefit_track_m/policy.py`: options 1-5,
  `TrackMPolicy`, rows MS0-MS6, Max's rulings (`MAX_RULINGS`) and the
  frozen choices.
- `.../coverage.py`: years of coverage and the one history per worker
  (§5), the quarter-of-coverage loader.
- `.../thresholds.py`: the pinned 2003-2022 Census capture and the
  threshold-year check (§7).
- `.../rules.py`: §§4a and 6-9 (the record years, schedules, indexing,
  proration, window, order, flag, auxiliaries, receipt; the PIA through
  the oracle; the claim and COLA factors).
- `.../specification.py`: this block's reader and the registered-run
  gate.
- `.../structure.py` and `scripts/track_m_structure.py`: the structural
  counts of §10.
- `scripts/capture_track_u_parameters.py --track-m-census-dir` and the
  committed workbooks and capture (§7).
- `scripts/run_track_m_registered.py`: the one-shot entry point; it
  refuses this draft, and with a ratified block it refuses until the
  missing pieces below exist, before reading any PSID file.
- Tests: `tests/min_benefit_track_m/` and
  `tests/test_minimum_benefits_spec.py`.

Blocked, with the plan's effort estimates (lane-days):

1. **M2's remaining captures** (part of 1.5): a Census workbook for any
   threshold year before 2003 that M4's count shows is needed (d279
   covers the download); the quarter-of-coverage amounts as a committed
   capture with a hash; the statute text of 413, 415 (including 415(i)),
   402(k) and 423 (the waiting period), with SHA-256.
2. **M3 readers** (2.5): person-level Social Security amounts and types
   for waves 1984-1992 and 2005-2023; the 2005 and 2007 "year before
   last" items, including whose receipt they record; head and wife items
   for 1993-2003; the next-wave labor income for the odd years 2001-2021,
   with time units and accuracy codes, and its concept checked against
   the panel's totals; ER35219's unit and top code; whether amounts are
   net of the Medicare premium.
3. **M4 cohort** (5): §4b's rules at 2004 and 2007, DI origin and onset,
   spouse links (living and deceased), types, claim ages, provenance;
   structural counts of records by basis, unresolved counts and the
   earliest threshold year needed (§7).
4. **M5 careers** (4): realized histories 1968-2022 through
   `coverage.one_history`; *Y* and *P* per §4a; MS5's inputs (§6).
5. **M8 tabulation** (1.5), **M10 dry run and registration package**
   (1.5), **M11 registration and one-shot** (3).
6. **Ratification:** an independent check that `m1-draft-2` applies the
   referee's required changes, then the ratified text (`m1-ratified-1`,
   status and version only) merged under d219 item 9.

## 19. Machine-readable parameter block

Downstream code reads this block:
`min_benefit_track_m.specification.m1_parameter_block` and
`check_specification_for_registered_run` (the entry script), and
`tests/test_minimum_benefits_spec.py`, which holds it to the code.
`decisions` records Max's rulings, one entry per ruled field
(`{field: {"ruling": value, ...}}`): the nine d219 fields of 2026-09-24
and the d279 and d280 fields of 2026-09-25, each equal to the code's
record (`min_benefit_track_m.policy.MAX_RULINGS`); `decisions_awaiting_max`
is empty. A registered run still refuses unless the status and version
say ratified, nothing awaits Max, every ruled field carries a ruling
equal to the code's, the configuration follows each ruling and the
block equals the code.

```json
{
  "specification": "urban2006_minimum_benefits_exercise4",
  "version": "m1-draft-2",
  "status": "draft_referee_changes_applied",
  "claim_class": {
    "ruled": "track_m_static_psid_snapshot_income_year_2022",
    "decision_record": "d219",
    "item": 2
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
    "di_pia_rule": "statutory_computation_years",
    "death_pia_rule": "statutory_death_computation",
    "di_proration": "elapsed_years_from_age_22",
    "di_proration_start_age": 22,
    "di_proration_cap_years": 40,
    "di_prorated_years_rounding": "exact",
    "threshold_rule": "census_weighted_average_one_person_65_plus",
    "threshold_year_rule": "attaining_62_or_di_onset_or_earlier_of_death_and_attaining_62",
    "wage_index_lag_years": 2,
    "covered_earnings_rule": "psid_labor_income_treated_as_covered",
    "pre_1978_coverage_rule": "statute_413_a_50_per_quarter",
    "gap_year_rule": "immediate_neighbor_mean",
    "odd_year_source": "next_wave_reference_person_and_spouse",
    "old_age_history_end": "year_before_first_entitlement",
    "di_coverage_end": "year_before_onset",
    "death_first_pia_year": "first_entitlement_on_record",
    "entitlement_year_rule": "earliest_consistent",
    "onset_year_rule": "entitlement_year_minus_1",
    "survivor_own_amount": "own_benefit_after_402q",
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
      "di_pia_rule": "approximate_pia"
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
  "decisions_awaiting_max": {},
  "decisions": {
    "ruled_by": "Max",
    "target_cells": {
      "ruling": "table6_2025_options_2_to_5_by_all_men_women_headline_2_all",
      "decision_record": "d219",
      "item": 1,
      "ruled_on": "2026-09-24",
      "as_filed": "the report prints no 2025 poverty effect (poverty only for 2050, Table 9), so score first on Table 6's 12 printed 2025 cells (share of beneficiaries 62+ receiving a minimum; options 2-5 by All/Men/Women; headline option 2, All), and hold poverty for a projected track scored against 2050"
    },
    "claim_class": {
      "ruling": "track_m_static_psid_snapshot_income_year_2022",
      "decision_record": "d219",
      "item": 2,
      "ruled_on": "2026-09-24",
      "as_filed": "measure it as 'Track M', a static PSID snapshot for income year 2022, labelled not a projection, not 2025 and not Axiom"
    },
    "policy_year": {
      "ruling": 2004,
      "decision_record": "d219",
      "item": 3,
      "ruled_on": "2026-09-24",
      "as_filed": "move every policy date back three years in the headline so the snapshot spans 19 entitlement years like DYNASIM's 2025, with the report's own 2007 dating as a registered row",
      "alternative_registered_as": "MS1"
    },
    "rules_module_placement": {
      "ruling": "new_python_module_outside_ss_calling_oracle_unchanged",
      "decision_record": "d219",
      "item": 4,
      "ruled_on": "2026-09-24",
      "as_filed": "years-of-coverage counting and the minimum rules in a new Python module outside ss/, calling the oracle unchanged (the covered-earnings convention is ruled separately: cos d280, 2026-09-25)"
    },
    "order": {
      "ruling": "floor_after_cut",
      "decision_record": "d219",
      "item": 5,
      "ruled_on": "2026-09-24",
      "as_filed": "minimum applied as a floor after the uniform cut, reverse order registered",
      "alternative_registered_as": "MS2"
    },
    "di_proration": {
      "ruling": "elapsed_years_from_age_22",
      "decision_record": "d219",
      "item": 6,
      "ruled_on": "2026-09-24",
      "as_filed": "DI proration years x 40 / years elapsed from 22 to onset, capped at 40"
    },
    "counting_rule": {
      "ruling": "own_or_linked_worker_pia",
      "decision_record": "d219",
      "item": 7,
      "ruled_on": "2026-09-24",
      "as_filed": "count as receiving the minimum anyone paid from a PIA resting on it, own-PIA-only registered",
      "alternative_registered_as": "MS3"
    },
    "acceptance_rule": {
      "ruling": null,
      "decision_record": "d219",
      "item": 8,
      "ruled_on": "2026-09-24",
      "as_filed": "no acceptance threshold"
    },
    "ratification_and_registration": {
      "ruling": "ratify_by_merge_then_issue_42_registration_then_one_shot",
      "decision_record": "d219",
      "item": 9,
      "ruled_on": "2026-09-24",
      "as_filed": "ratify by merge, then the #42 registration and one-shot run"
    },
    "covered_earnings_rule": {
      "ruling": "psid_labor_income_treated_as_covered",
      "decision_record": "d280",
      "item": null,
      "ruled_on": "2026-09-25",
      "as_filed": "treat PSID labor income as covered earnings (PSID does not observe coverage), as exercises 1 and 3 and Track C do",
      "ruling_text": "Accept (Max in chat 2026-09-25): same shared assumption, disclosed in the spec and every result",
      "disclosure": "specification_and_every_result"
    },
    "census_threshold_download": {
      "ruling": "thresh13_to_thresh22_and_any_earlier_year_the_build_proves_it_needs",
      "decision_record": "d279",
      "item": null,
      "ruled_on": "2026-09-25",
      "as_filed": "download Census historical poverty-threshold workbooks thresh13-thresh22 (plus any earlier year the build proves it needs) from www2.census.gov",
      "ruling_text": "Yes (Max in chat 2026-09-25): download thresh13-thresh22 and any earlier year the build proves it needs; capture, hash and pin like the 2003-2012 capture",
      "note": "Max downloaded thresh13-thresh22; with thresh03-thresh12 (d194) they are captured as 2003-2022. No earlier year is captured: whether one is needed is M4's earliest-threshold-year count (M1 specification, section 7)"
    }
  },
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
    },
    "census_thresholds": {
      "file": "data/external/census_poverty_thresholds_2003_2022.json",
      "sha256": "65bbcd83cad97b94526b8c71417b9b4986a5bc878285b87832cfb102bc11e3c5",
      "years": [
        2003,
        2022
      ],
      "row": "one_65_plus",
      "workbooks": "data/external/census_poverty_thresholds/thresh03.xlsx-thresh22.xlsx",
      "decision_records": [
        "d194",
        "d279"
      ]
    },
    "referee_report": {
      "file": "minimum-benefits-referee-20260924.md",
      "required_changes": "R1-R10"
    }
  },
  "blocked_by": [
    "independent_check_of_m1_draft_2_then_ratification_by_merge",
    "census_thresholds_before_2003_if_m4_needs_them",
    "statute_413_415_402_423_not_captured_m2",
    "person_level_social_security_readers_m3",
    "beneficiary_cohort_m4",
    "realized_careers_m5",
    "tabulation_m8_and_dry_run_m10",
    "issue_42_registration_absent"
  ]
}
```

## 20. Decisions (ruled by Max, 2026-09-24 and 2026-09-25)

Max ruled decision record d219 on 2026-09-24 and d279 and d280 on
2026-09-25, in chat with the orchestrating session. The rulings are
recorded in Max's decision ledger
(`~/chief-of-staff/state/decisions/decisions.jsonl`, status `decided`;
d219 `ruled_at` 2026-09-24T21:44, d279 and d280 2026-09-25T06:24). d219's
ruling reads "Accept all nine (Max in chat 2026-09-24): score Table 6 2025
share first via Track M (PSID 2022 snapshot, policy dates shifted 3
years, literal 2007 dating registered); poverty later vs 2050; ratify by
merge then #42 registration and one-shot." §19 records the rulings under
`decisions`, keyed by the field each fixes, with each item's text as
filed (`as_filed`), and `min_benefit_track_m.policy.MAX_RULINGS` holds
the same rulings in code; a registered run refuses a block whose rulings
differ from the code's or a configuration that departs from one (§19).

Rulings 1-9 answer d219's items (1)-(9), each adopting the default the
card proposed.

1. **Target cells** (`target_cells`; d219 item 1). **Ruling:** Table 6's
   12 printed 2025 cells, options 2-5 by All, Men and Women; headline
   option 2, All; poverty held for a projected track scored against 2050.
2. **Claim class** (`claim_class`; d219 item 2). **Ruling:** a static
   PSID snapshot for income year 2022, labelled not a projection, not
   2025 and not Axiom.
3. **Policy year** (`policy_year`; d219 item 3). **Ruling:** 2004 (every
   policy date moved back three years); the Report's 2007 is row MS1.
4. **Module placement** (`rules_module_placement`; d219 item 4).
   **Ruling:** years-of-coverage counting and the minimum rules in a new
   Python module outside `ss/`, calling the oracle unchanged. The cos
   text of item 4, which Max accepted, reads "years-of-coverage counting
   and the minimum rules in a new Python module outside ss/, calling the
   oracle unchanged". The plan's card also placed "labor income treated
   as covered earnings" in item 4; the cos text does not, so this version
   does not record item 4 as ruling on it (referee R2). Max ruled that
   convention separately, in d280 (ruling 10).
5. **Order** (`order`; d219 item 5). **Ruling:** the minimum is a floor
   after the uniform cut; the reverse order is row MS2.
6. **DI proration** (`di_proration`; d219 item 6). **Ruling:** *Y* × 40 /
   years elapsed from age 22 to onset, capped at 40.
7. **Counting rule** (`counting_rule`; d219 item 7). **Ruling:** anyone
   paid a benefit computed from a PIA that rests on the minimum, their own
   or a linked worker's; own-PIA-only is row MS3.
8. **Acceptance rule** (`acceptance_rule`; d219 item 8). **Ruling:** none;
   gaps are reported as results.
9. **Ratification and registration** (`ratification_and_registration`;
   d219 item 9). **Ruling:** ratify by merge, then the issue #42
   registration and the one-shot run. A process step, not a content
   decision: merging the PR that carries `m1-ratified-1` under this
   authorization ratifies it. This version is not that text: an
   independent check of the referee's changes comes first (§18).
10. **Covered earnings** (`covered_earnings_rule`; d280, 2026-09-25).
    Filed as "treat PSID labor income as covered earnings (PSID does not
    observe coverage), as exercises 1 and 3 and Track C do". **Ruling:**
    "Accept (Max in chat 2026-09-25): same shared assumption, disclosed in
    the spec and every result". PSID labor income is treated as covered
    earnings (§5, a named delta, §15); every Track M result carries
    `COVERED_EARNINGS_DISCLOSURE`.
11. **Census threshold download** (`census_threshold_download`; d279,
    2026-09-25). Filed as "download Census historical poverty-threshold
    workbooks thresh13-thresh22 (plus any earlier year the build proves
    it needs) from www2.census.gov". **Ruling:** "Yes (Max in chat
    2026-09-25): download thresh13-thresh22 and any earlier year the
    build proves it needs; capture, hash and pin like the 2003-2012
    capture". Max downloaded `thresh13.xlsx`-`thresh22.xlsx` (his
    `SHA256SUMS` lists all twenty files, 2003-2022); with
    `thresh03.xlsx`-`thresh12.xlsx` (d194) they are captured, hashed and
    pinned as 2003-2022 (§7). No earlier year is captured, because the
    build has not yet shown one is needed: that is M4's count (§7).

**Frozen by this version on the referee's answers (§21), and ratified
with the specification by the merge** (`policy.frozen_choices()`; no
ruling of Max's names them):

- window rule: in or after *Y*₀ (MS4: after);
- PIA rule: the history through the oracle (MS5: benefit-implied, with
  the inputs in §6);
- DI PIA rule: the statutory computation years (MS6: Track A's
  approximation);
- death PIA rule: the statutory death computation;
- the years that define each record (§4a) and the classification rules
  (§4b): the old-age history end, the DI coverage end, the death-basis
  window year, the entitlement-year rule, the onset-year rule and the
  survivor's own amount;
- DI proration start age 22; prorated years unrounded;
- the threshold: the Census weighted average for one person aged 65 and
  older, of the threshold year in §4a;
- wage-index lag 2;
- pre-1978 coverage: the statute's $50 a quarter;
- odd-year source: next-wave labor income, then the neighbor law;
- unobserved-window start age 22;
- couples' cap: none;
- unlinked auxiliaries: not receiving, counted separately;
- minimum rounding: none.

## 21. Referee pass

An independent referee (a Claude Code subagent, Opus 5.5, independent of
the builder lane and of the 2026-09-24 review) refereed `m1-draft-1`
(SHA-256 `cdee926f…`) and the code at `f1a1aa8e`:
`EVID/minimum-benefits-referee-20260924.md` (SHA-256 `49091254…`), with
its check scripts and statute copies in
`EVID/minimum-benefits-referee-20260924/`. **Verdict:** not ratifiable as
it stood; ratifiable once required changes R1-R10 are made, with no second
full referee pass needed if an independent check confirms they were
applied as written, with the code, block and tests updated to match.

**The referee's answers to the questions `m1-draft-1` asked** (frozen in
this version; §20's frozen list):

| # | Question | Answer | Where |
|---|---|---|---|
| Q1 | Odd years | Read the next-wave labor income of 2001-2021 first; fill the rest with the neighbor law, not zero; one history for *Y* and *P* | R7; §§4a, 5 |
| Q2 | Threshold year of a late claimer | Keep the eligibility year; capture from the earliest year any in-window record needs | R8; §§4, 7 |
| Q3 | Prorated years | Unrounded | §5 |
| Q4 | The end of *Y* for a DI worker | The year before onset (413(a)(2)(B)(i)); *Y* may exceed *D*, capped at 40; report as a diagnostic | R3; §4a |
| Q5 | A worker who died before eligibility | The statutory death computation | R3, R5; §§4a, 6 |
| Q6 | Other family-unit members | Keep them in the universe; report their share among the flagged | §4b rule 6 |
| Q7 | Minimum rounding | None, on either side | §7 |
| Q8 | The widow(er) comparison | The survivor's own benefit after 402(q) (402(k)(3)(A)) | R4; §4b rule 5 |
| Q9 | The flag window's start age | 22 | §5 |
| Q10 | Before 1978 | The statute's $50 a quarter; the convention is neither the default nor a registered row; Table 2 is a finding, not a basis | R6; §§5, 17 |

**How this version applies R1-R10.** Each was checked against its source
before it was applied: the statute and regulation passages against the
saved copies (42 USC 413(a)(2)(A)(i), (B)(i), (B)(ii) and (B)(iv) in
`usc-42-413-cornell.txt`, `7d226c0a…`; 20 CFR 404.141(b), (c) and (d)(1)
in `cfr-20-404-141-cornell.txt`, `7b1b195c…`; 415(b)(2)(B)(ii) in the text
`5b41d1cd…`; 402(k)(3)(A) in the referee's extract `43d5e10a…` and its
page copy `e5bb977c…`; 415(i)(2)(A)(iii) in the COLA excerpt file
`a323ca47…`), the d219, d279 and d280 texts against the cos records, and
the numbers against the code (`tests/min_benefit_track_m/`). The Report
itself was not reopened by this lane; the R10 wording fixes that cite it
rest on the referee's reading of the cleared files.

| Change | Applied | Notes |
|---|---|---|
| R1. Record d219 as Max ruled it | Yes, with one update | Every "pending" marker, the header, §§1, 4, 5, 8, 9, 13, 18, 19, 20 and 22, the block and the code docstrings now record the ruling. **Update:** Max ruled d280 on 2026-09-25, after the report, so `decisions` records the covered-earnings convention under d280 and d219 item 4 under the field its cos text names (`rules_module_placement`), and adds d279. The entries follow E1's form (the ruling, the record, the item, the date and the text as filed) rather than R1's shorter one; the gate compares them with `policy.MAX_RULINGS` |
| R2. Record item 4 as the cos text words it | Yes, updated for d280 | §20 ruling 4 quotes the cos text and records that it does not rule on the convention. R2's resolution (the convention ratified by the merge under item 9) is superseded: Max ruled it himself in d280, which R2 anticipated ("it can ask Max to confirm it"). `policy._D219[4]` quotes the cos wording with a trailing clause naming d280 |
| R3. The years that define each record | Yes | §4a verbatim; `rules.record_years`; `history_pia` takes the window year and cuts the history at §4a's last year; the three frozen fields; tests of a late claimer and of a DI worker's post-onset years. 415(b)(2)(B)(ii)(I) and (II) read in the text `5b41d1cd…` |
| R4. Classification rules | Yes | §4b verbatim, except rule 4's note, which now says that neither the referee nor this lane read 42 USC 423. The three frozen fields; `rules.survivor_own_amount` and `rules.claim_factor` (M4 applies the rules) |
| R5. Statutory DI and death PIAs primary; MS6 the approximation | Yes | Defaults, `REGISTERED_ROWS["MS6"]`, the death rule's only value, §§6 and 14, the block. The referee's 51, 71 and 86 percent reproduce in `test_di_pia_is_statutory_and_ms6_the_approximation` (0.509, 0.712, 0.861) |
| R6. The statute before 1978 | Yes | §5 verbatim; §17 finding 3; §15's delta; the default. The convention stays selectable, unregistered, only for the Table 2 check that shows the difference |
| R7. The odd-year source | Yes | §5 verbatim; `odd_year_source`; `coverage.one_history`, which *Y* and the PIA read (a next-wave year the panel also observes is refused) |
| R8. The threshold capture | Yes, updated for d279 and in part declined | The capture now covers 2003-2022 (d279), so §18's blocked item and `blocked_by` name only a year before 2003 that M4 may show is needed, which d279 already covers. **Declined in part:** R8's sentence that "a disability-origin record whose onset precedes a late entitlement" can need a threshold year before about 1996 contradicts R4's rule 4 (onset = entitlement year − 1), under which a disability-origin record's threshold year is at least *Y*₀ − 1; §4's finding says so. The named error and the pre-computation check exist (`ThresholdYearMissingError`, `check_threshold_years`) |
| R9. MS5's inputs | Yes, with one addition | §6 verbatim, plus this lane's reading of 415(i)(2)(A)(iii), which R9 left to M2; `rules.cola_factor` and `rules.claim_factor` supply the factors |
| R10. Six citation and wording fixes | Yes | 1: §3's effective date. 2: §5's $3,880 check. 3: the annual-limitation clause now cites 413(a)(2)(B)(ii) and 20 CFR 404.141(d)(1) (R6's text). 4: the disclosure bullet names the exact rows the `grep` printed: G4, G5, G6, G8, G9, G11, G12 and G13. The count, eight, was right and the range G4-G13 loose; the labels come from the `m1-draft-1` lane's session record. 5: §1's "What is not printed". 6: §2's statute row |

**Optional suggestions:** O4 (a named delta for the stock date) is
applied in §15. O1 (more invented worked cases), O2 (more diagnostics),
O3 (receipt wording), O5 (the blind forecast) and O6 (an issue for
`estimates.career`'s odd-year imputation) are left to the builds and the
orchestrator.

## 22. What the drafts read and did not verify

**`m1-draft-1` read:** `EVID/RESTRICTED-FILES.md` first; the plan
(revision 2) in full; the two cleared files in full (hashes checked); the
Report's PDF page 29 as text; of the first plan version, the field rows
G4, G5, G6, G8, G9, G11, G12 and G13 by `grep`; the cos record of d219
(open when the draft was written; decided 2026-09-24 21:44, recorded in
`m1-draft-2`); in the repository, `ss/benefits.py`, `ss/params.py`,
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

**`m1-draft-2` read:** `EVID/RESTRICTED-FILES.md` first (`2fc9bdbf…`,
last changelog entry 2026-09-25); the referee report in full; the cos
records of d189, d194, d219, d279 and d280; E1's specification on the
#461 branch (`e1-ratified-1`: its header, §22 and the block's
`decisions`) and `fra68_track.config.MAX_RULINGS` there; this
specification and the Track M code and tests at `430507ae`; the Track U
capture script, capture and tests on the #462 branch; the referee's
`di_pia_gap_check.py` and its output; of the plan (revision 2) its
section 4 and the lines that cite v1; of the plan's first version its
field-row labels only; of the `m1-draft-1` lane's session record its
one `grep` of v1 and the row labels that grep printed; the statute
passages listed in §21; `ss/statutory_aime.py`'s docstring and
functions, `ss/benefits.py`'s PIA, reduction, credit, spouse's and
widow(er)'s functions and `ss/params.py`'s parameter bundle;
`estimates/parameters.load_cola_history` and the COLA history file's
timing note; the twenty Census workbooks, cell by cell. It read no PSID
file, ran no structural count and computed no statistic on real data.

**Ran on staged PSID (`m1-draft-1` and the review):** label and code
verification and the structural counts of §10. No years of coverage,
PIA, threshold, minimum, flag or share receiving a minimum was computed
on real data.

**Did not verify:** the statute text of 415(i) beyond (2)(A)(iii) and of
423; whose receipt the 2005 and 2007 "year before last" items record;
the PSID immigrant-refresher date; whether PSID Social Security amounts
are net of Medicare premiums; the top code of ER35219; the fn. 27 blind
check; the availability statement's findings against the Report (they
rest on the comparator side and the clearance review); anything in the
Report beyond PDF page 29 and the cleared files; the earliest threshold
year any in-window record needs (M4).

**Independent review (2026-09-24, Claude Code subagent, Opus 5.5):**
read `EVID/RESTRICTED-FILES.md` first and nothing it restricts; the
plan, both cleared files, PDF page 29 as text, this draft and the code
diff; 42 USC 413 and 20 CFR 404.141 and 404.143 (law.cornell.edu,
copies with SHA-256 in `EVID/track-m-review-20260924/`); PSID setup-file
labels of the 1999-2023 family files (labels only). It reran the
structural counts (§10) and computed no years of coverage, PIA,
threshold, minimum or share receiving a minimum on real data. Its report
is `EVID/track-m-review-20260924.md`.

## 23. Changelog

- `m1-draft-1` (2026-09-24): first draft, with the Track M rules module,
  the structural counts in `EVID/track-m-structure-20260924/`, the
  registered entry point and the tests, on branch
  `dynamics-ex4-track-m-20260924`.
- `m1-draft-1`, review corrections (2026-09-24; no default, row, cell or
  d219 item changed, so the version and the §19 block stand): the odd
  income years 2001-2021 were asked one wave later, not never (§5, §10,
  §15, §18, question 1; counts rerun to
  `EVID/track-m-structure-20260924-r2/`); the statute's pre-1978
  quarter of coverage and the alternative that implements it (§5, §20,
  question 10) with Table 2 finding 3 (§17); 413(a)(2)(B)(i) added to
  question 4; question 9's reading of 415(b) corrected.
- `m1-draft-2` (2026-09-25): records Max's d219 ruling (all nine defaults
  accepted, 2026-09-24 21:44) in the header, §§1, 4, 5, 8, 9, 13, 18, 19,
  20 and 22, and his d279 and d280 rulings (2026-09-25) in §§5, 7, 19 and
  20; applies the referee's required changes R2-R10
  (`EVID/minimum-benefits-referee-20260924.md`): §4a and §4b (the years
  and classification rules that define each record), §5 (pre-1978
  statute; odd-year source), §6 (statutory DI and death PIAs, *P*'s
  history end, MS5's inputs), §7 (the threshold captured 2003-2022, and
  which years Track M needs), §14 (MS6 is now the approximation), §18 and
  the §19 block; answers the §21 questions; records how each change was
  applied, updated or in part declined (§21). On branch
  `dynamics-ex4-track-m-2-20260925`.
