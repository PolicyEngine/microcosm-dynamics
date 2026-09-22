# SSDI disabled-worker entitlement component (Track A item A4)

Status: built on branch `dynamics-di-entitlement-20260922` and fixed after
two independent agent reviews (the two mortality fixes are marked "Review
fix" below). A third review found no further code defect. It added the
termination-timing and select-gap notes under Named deltas, the
synthetic-age note on the diagnostic, and release-date and capture checks
to `data/external/di_asr_2008/provenance.md`. Not merged, not registered.
Every modeling choice below is a proposal awaiting the A1 specification
freeze. Nothing here computes the exercise 1 COLA statistic, reads DYNASIM
or Urban Institute values, or uses PSID data.

## Why it exists

The critical-path plan (`critical-path-cola-20260922.md`, section 1) finds
that the 2030 COLA age profile's 50–61 cell is driven by disability insurance
incidence by age and duration on the rolls, and that the 62–64 cell depends on
the disabled-worker share of beneficiaries. The certified M4 hazards model
self-reported work limitation, not SSA awards. This component models
disabled-worker entitlement itself.

## What it does

Code: `src/populace_dynamics/engine/di_entitlement.py` (adapters and
accounting) and `src/populace_dynamics/engine/di_entitlement_rates.py`
(rates, fit, and the explicit specification).

| Piece | Loop slot | Behavior |
|---|---|---|
| `prepare_opening_di_state` | `PeriodModules.initialize` | Requires an explicit boolean `di_entitled` opening stock (from A3); refuses entitled workers already past FRA, award years after the start year, conversion years before the earliest possible FRA year, and other inconsistent inputs; adds the DI state columns. |
| `apply_di_aware_mortality` | `PeriodModules.mortality` | Uses the same person-keyed MORTALITY uniform as `steps.apply_mortality`. Entitled workers (and, by default, converted former disabled workers) die at disabled-worker rates. By default everyone else's probability is scaled within each population age band and sex so that the cell's expected deaths stay at the population model's (see Everyone else below). It needs the population model's age bands and an explicit `weight_column`. Optionally logs every decedent and every cell. |
| `apply_di_entitlement` | `PeriodModules.disability` | At most one transition per person-year. Entitled workers convert in the calendar year they attain FRA (no draw) or face a recovery draw. Everyone else below FRA and aged 18 or older at the start of the year faces award incidence. One uniform per exposed or entitled person from a tagged, person-keyed DISABILITY stream. |
| `di_stock_flow` | after a run | Checks `stock_end = stock_start + awards + entrants − deaths − recoveries − conversions` for every year, counted and weighted, and cross-checks deaths against the mortality log. A scheduled entitled entrant who dies in its entry year is logged but never enters the stock; one who recovers or converts in its entry year counts as an entrant and as that termination. |

FRA comes from the statutory birth-year schedule (42 USC 416(l)), injected as
`SSAParameters.fra_months`; it is not re-typed in this component.

## Rates (data years 2008 and earlier)

Inputs are under `data/external/di_asr_2008/` (captures, hashes, and
table ids in its `provenance.md`), extracted by
`scripts/extract_di_asr_2008.py`.

- **Incidence per non-entitled population.** DI ASR 2008 Table 36 worker
  awards by age at entitlement, divided by the Census Vintage 2008 July 1,
  2008 resident population minus the ASR Table 20 December 2008 worker stock.
  Default annual probabilities per 1,000 (female, male): under 25: 1.07,
  1.44; 50–54: 7.90, 8.80; 55–59: 10.10, 13.41; 60–64: 7.71, 12.34; 65–FRA:
  1.55, 3.21.
- **Recovery.** Actuarial Study No. 118 (1996–2000 experience) Table 19 by
  attained age, times a level factor of 1.063 fitted so that expected 2008
  recoveries on the ASR 2008 exposure equal ASR Table 50 (59,643).
- **Death.** Actuarial Study No. 118 Table 12 (ages 16–74) and Table 7C (ages
  75–110). By default this is used as a multiplier on the engine's population
  mortality, with the NCHS 2000 life table as the base: the disabled-worker
  probability is `q_AS118 × q_population / q_NCHS2000`. The base is taken at
  the population model's own age resolution: the survivorship-weighted
  (`l_x`) mean of the NCHS 2000 probabilities over the population model's age
  band (its `bands`, or an explicit `population_age_bands`; a model with
  neither is refused). The multiplier is therefore constant within a band and
  carries only the engine's level relative to NCHS 2000. For a
  single-year-of-age model the base is the single-age probability. (Review
  fix: the base was single-age NCHS 2000 regardless of resolution. With a
  population model at NCHS 2000 levels averaged over the engine's 10-year
  PSID mortality bands, male DI mortality then came out about 52 percent
  above the Actuarial Study value at 55 and about 31 percent below it at 64,
  within the 55–64 band.)
  On the 2008 exposure the published 1996–2000 rates imply 252,925 deaths
  against ASR's 215,445, a factor of 0.852. That factor is applied only in
  the explicit `asr_fitted` alternative.
- **Everyone else.** The population mortality model is all-person mortality:
  the engine's band model (`engine.refit.fit_mortality_model`) is fit on
  PSID person-year exposure against NCHS rates with no disabled-worker
  split, and NCHS 2000 covers the whole population, so their deaths already
  include disabled workers'. By default
  (`non_di_mortality="net_of_di_origin"`) the mortality adapter keeps each
  population age band and sex cell's expected (weighted) deaths at
  the population model's: DI-origin persons take the disabled-worker
  probability, and every other person's population probability is multiplied
  by one factor per cell, `(E_population − E_DI) / E_other`. A cell whose
  DI-origin expected deaths alone exceed the population model's is flagged
  `infeasible` in the optional cell log, and its other members get
  probability zero. (Review fix: non-DI persons kept the population
  probability, which added the disabled-worker excess deaths on top of the
  population model. At the December 2008 DI prevalence and the Actuarial
  Study No. 118 rates over NCHS 2000, that raised expected deaths in each
  ASR age group from 45 to 64 by 25 to 35 percent. That behavior remains
  available as `population_total`.) Under the net default a person's
  uniform is still person-keyed, but a non-DI person's probability depends
  on the DI share of that person's cell.

## Choices awaiting the A1 freeze

`pending_decisions()` returns this list. Defaults are the plan's primary
where it names one, otherwise the builder's or a reviewer's proposal.

| Field | Default | Alternatives | Basis |
|---|---|---|---|
| `incidence_basis` | `per_population_non_entitled` | `per_insured` (refused: no per-insured rates or insured-status variable) | Plan section 4, A4 |
| `death_mode` | `multiplier` | `explicit` | Plan: "DI mortality multiplier or life table, frozen" |
| `fit_year` | `2008` | `2007` (published September 2008), `2007-2008` pooled | Task: 2008 (or 2007) ASR |
| `recovery_level` | `asr_fitted` | `as118_published` | Builder |
| `termination_basis` | `attained_age` | `select_and_ultimate` (needs award years for the whole DI-origin stock) | Builder: the PSID opening stock has no award year |
| `post_conversion_mortality` | `di_origin` | `population` | Builder: Actuarial Study No. 118 follows converted workers |
| `non_di_mortality` | `net_of_di_origin` | `population_total` | Review: the population model is all-person mortality, so the net default keeps each band-sex cell's expected deaths at the population model's |
| `death_level` (explicit mode only) | `as118_published` | `asr_fitted` | Builder |

Builder conventions, explicit in the code:

- Rates are looked up at the start-of-year age `year − 1 − birth_year`.
- Minimum award age is 18, the first fitted incidence age; a lower value is
  refused because it would have no effect.
- There are no awards in the calendar year of FRA attainment.
- When `birth_month` is absent, July is assumed for FRA attainment.
- Mortality precedes the DI step, so disabled-worker mortality starts the
  year after the award.
- An opening conversion year may not precede the earliest calendar year in
  which FRA can be attained: the birth month when known, otherwise January,
  with a birth on the first of the month.

## Validation-only diagnostic

`scripts/validate_di_entitlement_asr2023.py` writes
`runs/di_entitlement_asr2023_validation_v1.json`. It projects a synthetic
December 2008 population from 2009 to 2023:

- Census V2008 single ages, with the ASR 2008 Table 20 DI stock spread evenly
  within age groups. The July 1 ages are used as end-of-2008 ages
  (`birth_year = 2008 − age`), so the non-entitled records are about half a
  year younger than the December 2008 population;
- closed, with NCHS 2000 population mortality held constant (netted of
  DI-origin deaths within each single age and sex, the default);
- run through the real adapters, on their batch-generator path with fixed
  per-year seeds.

It then compares the projection with the 2023 DI ASR (Tables 19, 35, 49).
This is a reported diagnostic, not a fitting target, and not PSID or
Track A. Default variant:

| Year | Men, model (thousands) | Men, ASR | Ratio | Women, model | Women, ASR | Ratio | Awards, model | Awards, ASR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2010 | 4,093 | 4,310 | 0.95 | 3,761 | 3,894 | 0.97 | 869 | 1,027 |
| 2013 | 4,367 | 4,642 | 0.94 | 4,096 | 4,299 | 0.95 | 910 | 869 |
| 2016 | 4,573 | 4,511 | 1.01 | 4,303 | 4,298 | 1.00 | 910 | 706 |
| 2019 | 4,638 | 4,231 | 1.10 | 4,477 | 4,147 | 1.08 | 921 | 679 |
| 2022 | 4,654 | 3,808 | 1.22 | 4,482 | 3,796 | 1.18 | 855 | 509 |

These are the review-fix numbers (net-of-DI non-DI mortality). The earlier
numbers, with non-DI persons at the full NCHS 2000 level, are reproduced
exactly by the `non_di_population_total` variant. The stocks of the two
differ by at most 1.6 percent in any year and annual awards by at most 4.5
percent. The two runs do not share draws record by record (on the batch
path the uniforms shift across records when the set of survivors changes),
so those differences mix the mortality change with simulation noise.

Readings:

- **Level.** Awards held at the 2008 rates miss both the 2009–2011 rise and
  the decline that followed (ASR worker awards were 1.03 million in 2010 and
  0.51 million in 2022). The stock is 3 to 6 percent low in 2010–2013, then
  about 20 percent high by 2022.
- **Age distribution.** The mean absolute gap across the eight Table 19 age
  groups grows from about 0.4 percentage points in 2010 to about 2.4 in
  2022. The model under-represents the 60–FRA group; in 2023 that group is
  6.6 points low for men and 7.3 points low for women.
- **2023 artifact.** The July birth-month convention gives 2023 no model
  conversions, because the 1956 cohort converts in 2022 and the 1957 cohort
  in 2024. The 2023 model stock and termination counts carry that artifact.
  Cohorts aged under 70 in 2030 have an FRA of 67 and are unaffected.
- **Other variants.** The artifact also reports the explicit
  2008-death-level variant, the 2007 fit year, and `population_total`
  non-DI mortality.

## Integration notes for A3, A5, and A6

- **A3** supplies `di_entitled` for 2010 and, where observable,
  `di_award_year`, `di_conversion_year`, and `birth_month`.
- **A5** injects the two adapters. The claiming step must skip `di_entitled`
  rows, because entitled disabled workers must not draw a retirement claim
  plan. `di_converted` feeds `engine.claiming.apply_claiming` as a conversion
  in the FRA year. The mortality adapter needs the population model's age
  bands (a year-aware wrapper must expose `bands` or pass
  `population_age_bands`) and an explicit `weight_column` (the cohort
  weight, or `None` for equal weights); synthetic persons without a weight
  are refused.
- **A6** reads `di_award_year` or `di_award_age` for the disabled-worker
  exposure clock. The award year can follow the SSA entitlement date, which
  is a named delta.

## Named deltas

- Current-pay versus entitled.
- Rates are constant after the fit year, with no business cycle or
  administrative variation.
- No duration dependence in the default basis.
- ASR "other" and elected-reduced-retirement terminations are not modeled.
- Award year is used rather than entitlement date.
- Disabled widow(er)s and disabled adult children are not modeled; only
  disabled workers are.
- Non-DI mortality is netted of DI-origin deaths within population band-sex
  cells, so the population model's cell totals are kept, but within a cell
  the non-DI persons share one factor.
- No behavioral adjustment of incidence for the rising FRA. The 2008
  Trustees Report raises its incidence assumptions for workers expected to
  file for DI rather than reduced retirement benefits as the NRA rises
  (report page 119, footnote 1).
- Termination timing. The Actuarial Study No. 118 probabilities are
  multiple-decrement probabilities (the death tables' note: "the
  probability of death— in a multiple-decrement environment"). The loop
  applies death in step 1 and recovery to the survivors in step 5, so a
  continuing worker's realized recovery probability is
  `(1 − q_death) × q_recovery`. On the 2008 fit exposure, at the
  Actuarial Study death rates, that is 2.5 percent below the 59,643
  recoveries the `asr_fitted` level factor targets, because the fit
  multiplies exposure by `q_recovery` alone. The fit does not correct for
  it.
- Under `termination_basis="select_and_ultimate"`, recovery is zero where
  Actuarial Study No. 118 Tables 14A–14B show no value. Those cells are the
  select-age and duration pairs that reach attained age 65 or more (select
  age 56 at duration 9 through select age 64 at durations 1–9); the tables'
  note says "Recovery is not considered beyond normal retirement age",
  which was 65 in the 1996–2000 experience. Workers with an FRA above 65
  therefore have no recovery after 65 on that basis. The attained-age
  default holds the age-64 value instead (0.000455 for men, 0.000371 for
  women, before the level factor).
