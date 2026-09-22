# SSDI disabled-worker entitlement component (Track A item A4)

Status: built on branch `dynamics-di-entitlement-20260922`, unreviewed, not
registered. Every modeling choice below is a proposal awaiting the A1
specification freeze. Nothing here computes the exercise 1 COLA statistic,
reads DYNASIM or Urban Institute values, or uses PSID data.

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
| `prepare_opening_di_state` | `PeriodModules.initialize` | Requires an explicit boolean `di_entitled` opening stock (from A3); refuses entitled workers already past FRA, award years after the start year, and other inconsistent inputs; adds the DI state columns. |
| `apply_di_aware_mortality` | `PeriodModules.mortality` | Uses the same person-keyed MORTALITY uniform as `steps.apply_mortality`, so non-DI people die exactly as before. Entitled workers (and, by default, converted former disabled workers) die at disabled-worker rates. In the multiplier mode it needs the population model's age bands (see Death below). Optionally logs every decedent. |
| `apply_di_entitlement` | `PeriodModules.disability` | At most one transition per person-year. Entitled workers convert in the calendar year they attain FRA (no draw) or face a recovery draw. Everyone else below FRA and aged 18 or older at the start of the year faces award incidence. One uniform per exposed or entitled person from a tagged, person-keyed DISABILITY stream. |
| `di_stock_flow` | after a run | Checks `stock_end = stock_start + awards + entrants − deaths − recoveries − conversions` for every year, counted and weighted, and cross-checks deaths against the mortality log (a scheduled entitled entrant who dies in its entry year is logged but never enters the stock). |

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

## Choices awaiting the A1 freeze

`pending_decisions()` returns this list. Defaults are the plan's primary
where it names one, otherwise the builder's proposal.

| Field | Default | Alternatives | Basis |
|---|---|---|---|
| `incidence_basis` | `per_population_non_entitled` | `per_insured` (refused: no per-insured rates or insured-status variable) | Plan section 4, A4 |
| `death_mode` | `multiplier` | `explicit` | Plan: "DI mortality multiplier or life table, frozen" |
| `fit_year` | `2008` | `2007` (published September 2008), `2007-2008` pooled | Task: 2008 (or 2007) ASR |
| `recovery_level` | `asr_fitted` | `as118_published` | Builder |
| `termination_basis` | `attained_age` | `select_and_ultimate` (needs award years for the whole DI-origin stock) | Builder: the PSID opening stock has no award year |
| `post_conversion_mortality` | `di_origin` | `population` | Builder: Actuarial Study No. 118 follows converted workers |
| `death_level` (explicit mode only) | `as118_published` | `asr_fitted` | Builder |

Builder conventions, explicit in the code:

- Rates are looked up at the start-of-year age `year − 1 − birth_year`.
- Minimum award age is 18, the first fitted incidence age; a lower value is
  refused because it would have no effect.
- There are no awards in the calendar year of FRA attainment.
- When `birth_month` is absent, July is assumed for FRA attainment.
- Mortality precedes the DI step, so disabled-worker mortality starts the
  year after the award.

## Validation-only diagnostic

`scripts/validate_di_entitlement_asr2023.py` writes
`runs/di_entitlement_asr2023_validation_v1.json`. It projects a synthetic
December 2008 population from 2009 to 2023:

- Census V2008 single ages, with the ASR 2008 Table 20 DI stock spread evenly
  within age groups;
- closed, with NCHS 2000 population mortality held constant;
- run through the real adapters.

It then compares the projection with the 2023 DI ASR (Tables 19, 35, 49).
This is a reported diagnostic, not a fitting target, and not PSID or
Track A. Default variant:

| Year | Men, model (thousands) | Men, ASR | Ratio | Women, model | Women, ASR | Ratio | Awards, model | Awards, ASR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2010 | 4,105 | 4,310 | 0.95 | 3,754 | 3,894 | 0.96 | 864 | 1,027 |
| 2013 | 4,343 | 4,642 | 0.94 | 4,101 | 4,299 | 0.95 | 882 | 869 |
| 2016 | 4,539 | 4,511 | 1.01 | 4,334 | 4,298 | 1.01 | 903 | 706 |
| 2019 | 4,604 | 4,231 | 1.09 | 4,493 | 4,147 | 1.08 | 881 | 679 |
| 2022 | 4,634 | 3,808 | 1.22 | 4,516 | 3,796 | 1.19 | 873 | 509 |

Readings:

- **Level.** Awards held at the 2008 rates miss both the 2009–2011 rise and
  the decline that followed (ASR worker awards were 1.03 million in 2010 and
  0.51 million in 2022). The stock is 4 to 7 percent low in 2010–2013, then
  about 20 percent high by 2022.
- **Age distribution.** The mean absolute gap across the eight Table 19 age
  groups grows from about 0.4 percentage points in 2010 to about 2.3 in
  2022. The model under-represents the 60–FRA group; in 2023 that group is
  6.4 points low for men and 6.9 points low for women.
- **2023 artifact.** The July birth-month convention gives 2023 no model
  conversions, because the 1956 cohort converts in 2022 and the 1957 cohort
  in 2024. The 2023 model stock and termination counts carry that artifact.
  Cohorts aged under 70 in 2030 have an FRA of 67 and are unaffected.
- **Other variants.** The artifact also reports the explicit
  2008-death-level variant and the 2007 fit year.

## Integration notes for A3, A5, and A6

- **A3** supplies `di_entitled` for 2010 and, where observable,
  `di_award_year`, `di_conversion_year`, and `birth_month`.
- **A5** injects the two adapters. The claiming step must skip `di_entitled`
  rows, because entitled disabled workers must not draw a retirement claim
  plan. `di_converted` feeds `engine.claiming.apply_claiming` as a conversion
  in the FRA year.
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
