# Track A assembly (plan item A5)

`populace_dynamics.cola_track_a` joins the six Track A work items for
DynaSim scorecard exercise 1 (COLA reduced by one percentage point, 2030
age profile) on the unmodified `engine.loop.ProjectionEngine`. It is
opt-in: nothing in the historical projection, the estimates or the
evidence reducers imports it, and the birth-evidence reachability test
guards that.

Every output is labelled *Python oracle (not Axiom)* and *fixed-path
mechanical incidence*. Outputs on the PSID cohort also carry *PSID-seeded
closed cohort*. Outputs on the invented cohort carry the invented-data
labels instead. Nothing here is ratified. Every open choice is a
`TrackAConfig` field; `pending_decisions()` lists each one with its
source.

## Pipeline

| Step | Module | What it reuses |
|---|---|---|
| Opening state (2010) | `opening.prepare_track_a_cohort` | A3 `Psid2010Cohort` (persons, careers, opening status and claim year) |
| Mortality | `mortality.Tr2008YearAwareMortality` inside A4 `apply_di_aware_mortality` | A2 `period_life_table_2004`, `mortality_improvement_ratio`; A4 DI death rates and non-DI netting |
| Aging | `engine.steps.advance_age` | as is |
| Marital core | `adapters.widowhood_marital_step` | pass-through; widowhood from the simulated death of a linked spouse in the opening roster |
| Fertility | `adapters.adopt_marital_state` | writes the step-3 marital state into the frame (the certified assembly's merge point); no births |
| Disability | A4 `apply_di_entitlement` | awards, recoveries, conversion at FRA |
| Earnings | `adapters.no_earnings` | none after 2010 |
| Claiming | `adapters.di_aware_claiming` | `engine.claiming.apply_claiming` on non-DI rows; `ClaimingSchedule` restricted to table rows at or before 2008 |
| Household composition | `adapters.no_household_composition` | none |
| Benefits | `benefits.reference_benefit_rows` | A6 `ScenarioCOLARates`, `increased_pia_path`, `monthly_benefit_path`, `spouse_excess_path`, `widow_benefit_path`, `eligibility_pia_for_clock`; oracle `claiming.benefit_factor` |
| Tabulation | `runner.run_track_a` | A7 `tabulate_cola_age_profile`, one call per registered row |

Draw `k` has root entropy `5200 + k`. Mortality and claiming use the loop's
person-ordinal streams, and DI uses A4's tagged person streams. Each draw
is projected once. Every registered row reads that same projection, so
both scenarios share every simulated path. Nothing is scheduled as an
entrant. The runner still calls `entrant_schedule.validate_projection_allocator`
on the projection metadata.

## Registered rows

`config.REGISTERED_ROWS` holds R0 to R5 of the A1 draft (section 18). A
test checks them against the draft's section 21 JSON block. R6 (the PSID
2009 wave) is not built, because the A3 builder materializes only the 2011
wave. R3 uses A7's alternative statistic. R4 reads the December 2030
amount (payment-year key 2031) times 12. R5 passes A7 the worker
components only.

## Benefit rules (A5 conventions, A1 where it speaks)

- **Opening stock** (A1 section 11, rule 4). The observed 2010 amount is
  carried forward on the baseline path without dime flooring, and the
  reform ratio comes from the reformed increases on the A1 section 6
  clock. The A6 function `opening_stock_scenario_paths` takes a
  `WorkerClock`, which cannot carry an entitlement exposure for a worker
  who died before eligibility. So the same arithmetic is composed from
  A6's pieces (`benefits.opening_stock_amounts`), and a test pins it to
  the A6 function wherever both apply. A simulated DI recovery ends a
  disabled worker's opening basis; rule 4 does not mention recovery.
- **Clocks.** Opening retired workers: birth year + 62. Disabled workers,
  and survivors or spouses under 62: the A3 receipt start. Aged survivors
  or spouses: the linked worker's clock (birth year + 62, or the year of
  death when the worker died before 62), falling back to the person's own
  birth year + 62. Projected disabled workers: the A4 award year. Projected
  retirement claimants: birth year + 62.
- **Own benefit.** Entitled disabled worker, converted disabled worker
  (retired-worker component, disability clock kept) or retirement
  claimant (claim-age factor from the oracle).
- **Spouse's excess.** A claimant aged 62 or older, married in 2030 to a
  living worker who has an own benefit. Paid from the later of the two
  entitlement years.
- **Aged widow(er)'s benefit.** A widow(er) of a worker in the opening
  roster, from the later of widowhood and age 60. It is paid as the excess
  over the survivor's own benefit (dual entitlement through the oracle's
  `widow_benefit`). The deceased's PIA comes from the last state before
  death.
- **Entitlement clock (R2).** The reform reaches increases from the
  beneficiary's own entitlement year. For auxiliaries this defaults to the
  auxiliary's own entitlement year (the A1 section 6 text). The A6
  docstring's worker-entitlement reading is the alternative
  (`auxiliary_entitlement_clock`).
- **Levels the oracle does not compute.** DI levels (decision 2(b)) and
  levels for workers who died before 62 follow `LevelPolicy`. The default
  `approximate_pia` is the oracle's retirement AIME through the onset or
  death year, with the PIA at that year's bend points. It is a weight,
  never a ratio.

## Parameters

- **COLA.** The realized history, with TR2008 intermediate rates from
  determination year 2008 (`runner.tr2008_baseline_cola`). The runner
  refuses a row whose lowest reduced rate through 2030 is not positive.
- **AWI.** TR2008 from 1975 (`runner.tr2008_ssa_parameters`, the A2
  default). Earlier years keep the oracle's series.
- **DI.** A4 `load_di_entitlement_rates` with the A4 default
  specification.
- **Claiming.** The claim-age table pinned by A3
  (`runner.load_claiming_pmf`).

## Dry run

`python scripts/track_a_dry_run.py --output-dir <dir> --draws 3` runs the
whole pipeline on the invented cohort
(`cola_track_a.invented.invented_psid2010_inputs`, 250 persons through the
real A3 builder). It uses the committed parameters and the oracle's
statutory parameters from the local policyengine-us checkout, with TR2008's
AWI. It writes `result.json` and `RESULTS.md`, each headed
`INVENTED DATA - NOT A COMPARISON`. The runner refuses a
`registered_real` cohort without the issue #42 registration pointer.

## Named gaps

The dry run's `result.json` carries the full list: mortality substitute,
DI netting at single-year cells, no post-2010 earnings, no pre-1968
earnings, approximated DI and pre-eligibility-death levels, spouses
outside the roster, widow(er)s of workers who died before 2011, no
projected disabled widow(er)s, no marriage dynamics, auxiliary
entitlement timing, the realized wage base, A7's person-level floor split
(A1 section 16 asks for the family unit), A7's one-seed floor (A1 section
16 asks for undefined), R6, opening-stock DI recovery, and claiming.
