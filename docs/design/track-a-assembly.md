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
labels instead.

Every convention is a `TrackAConfig` field, and two kinds are kept apart:

- **Max's rulings** (2026-09-23; decision records d074 and d075, A1
  section 22): the claim class (Track A is the first scored comparison),
  the oracle COLA horizon to 2030, the DI benefit level as a disclosed
  oracle approximation, no numerical acceptance threshold, and the
  opening-stock basis frozen at the opening year. `max_rulings()` reports
  each with the configured value and whether it follows the ruling. A
  `registered_real` run refuses a configuration that departs from one;
  the declined DI alternative (`di_benefit_level="exclude"`) still runs as
  an invented-data sensitivity.
- **Builder defaults** that no ruling covers (auxiliary entitlement and
  level rules, the mortality base year, the claim-table cap):
  `builder_defaults()` lists each with its source. They are fixed only by
  A1 ratification and the issue #42 registration.

A1 itself is a ratification candidate (`a1-ratified-candidate-1`); it is
ratified only when Max merges it.

## Pipeline

| Step | Module | What it reuses |
|---|---|---|
| Opening state (2010; 2008 for R6) | `opening.prepare_track_a_cohort` | A3 `Psid2010Cohort` (persons, careers, opening status and claim year, family unit, builder-set provenance) |
| Mortality | `mortality.Tr2008YearAwareMortality` inside A4 `apply_di_aware_mortality` | A2 `period_life_table_2004`, `mortality_improvement_ratio`; A4 DI death rates and non-DI netting |
| Aging | `engine.steps.advance_age` | as is |
| Marital core | `adapters.widowhood_marital_step` | pass-through; widowhood from the simulated death of a linked spouse in the opening roster |
| Fertility | `adapters.adopt_marital_state` | writes the step-3 marital state into the frame (the certified assembly's merge point); no births |
| Disability | A4 `apply_di_entitlement` | awards, recoveries, conversion at FRA |
| Earnings | `adapters.no_earnings` | none after 2010 |
| Claiming | `adapters.di_aware_claiming` | `engine.claiming.apply_claiming` on non-DI rows; `ClaimingSchedule` restricted to table rows at or before 2008 |
| Household composition | `adapters.no_household_composition` | none |
| Benefits | `benefits.reference_benefit_rows` | A6 `ScenarioCOLARates`, `increased_pia_path`, `monthly_benefit_path`, `spouse_excess_path`, `widow_benefit_path`, `eligibility_pia_for_clock`; oracle `claiming.benefit_factor` |
| Tabulation | `runner.run_track_a` | A7 `tabulate_cola_age_profile`, one call per registered row, with each person's opening-wave `family_unit_id` as the floor's split unit; the runner adds the A1 section 16 weighted component shares per cell (shares of the weighted baseline amount, which A7 does not compute) |

Draw `k` has root entropy `5200 + k`. Mortality and claiming use the loop's
person-ordinal streams, and DI uses A4's tagged person streams. Each
population is projected once per draw: the 2011-wave cohort (rows R0-R5,
2010 to 2030) and the 2009-wave cohort of R6 (2008 to 2030, passed in
`TrackAInputs.additional_cohorts`). Every row reads its population's
projection, so both scenarios share every simulated path. Nothing is
scheduled as an entrant and no step creates a person. The runner still
calls `entrant_schedule.validate_projection_allocator` on the projection
metadata, but that metadata carries no allocator, so the check has
nothing to test.

The configuration names the TR2008 alternative, the first TR2008 rate
year, the mortality base year, the DI specification and the claim-table
cap, while the inputs are built separately. Every result records whether
they agree (`parameter_consistency`). Without further request only the
labels are compared: the DI specification, the A2 model's alternative and
base year, and the A3 claim-table cap. When the caller asks
(`check_committed_parameters`, which the dry run sets), and always for a
`registered_real` cohort, the values are compared too: the COLA path and
AWI with the TR2008 capture, the population mortality with the A2
substitute for every projection year (any other model is a mismatch), the
DI rates with A4's fit from the committed inputs, and the claim-age rows
the projection reads with the A3-pinned table. `cola_track_a.statutory`
adds the rest of what the oracle reads, each bound to a committed source by
hash and value:

- the realized COLA history for every determination year before the first
  TR2008 rate year (1979-2007), against `data/external/ssa_cola_history.json`
  (loaded through its SHA-256 pin);
- the contribution and benefit base (1937 through the last opening year),
  the PIA factors, the FRA schedule, the early-retirement reduction, the
  delayed retirement credits and their cap, the AWI before 1975 and the
  spouse and survivor constants, against the committed capture
  `data/external/track_a_statutory_parameters.json` (pinned by SHA-256;
  written by `scripts/capture_track_a_statutory_parameters.py` from the
  policyengine-us files whose SHA-256s `estimates.parameters` already pins);
- the bend points for eligibility years 1979-2030, against 42 USC
  415(a)(1)(B) applied to the TR2008 AWI with the captured base amounts;
- the contribution and benefit base for 1975-2008 against TR2008 V.C1. V.C1
  prints projections from 2009, which differ from the realized bases the
  oracle reads for 2009 and 2010; they are listed as documented
  differences, not mismatches.

A `registered_real` run refuses any disagreement.

## Provenance guard

`prepare_track_a_cohort` refuses a `data_provenance` label that contradicts
the provenance the A3 builder recorded on the cohort: `invented` needs a
cohort built from the invented generator (its frames are re-generated from
the recorded seed and compared), and `registered_real` needs one built from
recorded PSID files. A cohort that was replaced, edited after the build or
assembled from caller frames is refused under either label. The runner
repeats the label check on every `TrackACohort` it projects, so relabelling
a prepared cohort cannot skip the issue #42 registration check either.

## Registered rows

`config.REGISTERED_ROWS` holds R0 to R6 of A1 (section 18). A test checks
them, populations included, against the section 21 JSON block. R3 uses
A7's alternative statistic. R4 reads the December 2030 amount (payment-year
key 2031) times 12. R5 passes A7 the worker components only. R6 projects
the A3 2009-wave cohort (weight `ER34046`, family unit `ER34001`) from its
2008 opening state over 22 periods; its opening-stock amounts are the
observed 2008 amounts carried forward from determination year 2008.

Undefined cells follow A1 section 7: A7 reports an undefined cell (no
members, zero weight or a non-positive baseline mean in some draw) with its
reason and keeps the rest of the row, and the run's row status names each
such cell ("tabulated with undefined cells: ..."). The floor follows A1
section 16: split by opening-wave family unit, undefined with fewer than two
usable seeds.

## Benefit rules (A5 conventions, A1 where it speaks)

- **Opening stock** (A1 section 11, rule 4; Max ruled on 2026-09-23 that
  the basis stays frozen at the opening year). The observed opening-year
  amount (2010, or 2008 for R6) is carried forward on the baseline path
  without dime flooring, and the reform ratio comes from the reformed
  increases on the A1 section 6 clock. The A6 function
  `opening_stock_scenario_paths` takes a `WorkerClock`, which cannot carry
  an entitlement exposure for a worker who died before eligibility. So the same arithmetic is composed from
  A6's pieces (`benefits.opening_stock_amounts`), and a test pins it to
  the A6 function wherever both apply. A simulated DI recovery ends a
  disabled worker's opening basis; rule 4 does not mention recovery.
- **Clocks.** Opening retired workers: birth year + 62. Disabled workers,
  and survivors or spouses under 62: the A3 receipt start. Aged survivors
  or spouses: the linked worker's clock (birth year + 62, or the year of
  death when the worker died before 62), falling back to the person's own
  birth year + 62. Projected disabled workers: the A4 award year, or
  birth year + 62 when the award comes later (A4 exposes retirement
  claimants below FRA). That exception is an A5 reading of the A1
  statute excerpts, which A1 has not ruled on: 415(a)(3)(B)(i) deems a
  worker eligible for old-age benefits from age 62, and 415(i)(2)(A)(iii)
  increases the PIA from the year of eligibility "without regard to the
  time of entitlement". Under R2 the award year stays the entitlement
  year. Projected retirement claimants: birth year + 62.
- **Components.** Opening-stock labels follow A1 section 11 in the
  reference year: a disabled worker converted at FRA is a retired worker,
  and a survivor labelled a disabled widow(er) in 2010 is an aged
  widow(er) once aged 60 or older. The amount and the reduced increases
  stay on the opening basis. R5 keeps or drops the same persons either
  way.
- **Own benefit.** Entitled disabled worker, converted disabled worker
  (retired-worker component, disability clock kept) or retirement
  claimant (claim-age factor from the oracle).
- **Spouse's excess.** A claimant aged 62 or older, married in 2030 to a
  living worker in the opening roster who has an own benefit. Paid from
  the later of the claimant's own simulated claim year and the worker's
  entitlement year. A disabled worker still entitled to DI draws none.
  One converted at FRA claims at the conversion (the claiming step's
  `claim_year`), not at the DI award.
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
- **Levels the oracle does not compute.** DI levels (decision 2(b), ruled
  by Max on 2026-09-23 as a disclosed oracle approximation) and
  levels for workers who died before 62 follow `LevelPolicy`. The default
  `approximate_pia` is the oracle's AIME over the career through the onset
  or death year, indexed to the second year before that year (the oracle
  indexes to its birth-year argument's age-60 year, and the function
  passes onset or death year minus 62), with the PIA at that year's bend
  points. The divisor stays 35 years (no elapsed or dropout years), so
  it understates short careers. It is a weight, never a ratio.

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
- **Statutory parameters.** Bend points, FRA, reduction and credit rates
  and the wage base come from the oracle's `SSAParameters`; the result
  records its revision (`ssa_parameters_revision`), and the committed-value
  checks bind every value the oracle reads to the committed capture
  (above). `statutory.captured_ssa_parameters()` builds the same bundle
  from the capture alone, without a policyengine-us checkout.

## Dry run

`python scripts/track_a_dry_run.py --output-dir <dir> --draws 3` runs the
whole pipeline on the invented cohort
(`cola_track_a.invented.invented_psid2010_inputs`, 250 persons aged 30 to
80 in 2010, through the real A3 builder), read both as the 2011 wave (rows
R0-R5) and as the 2009 wave (row R6; the same invented people, with 2009
interview numbers and ages). It uses the committed parameters and the
oracle's statutory parameters from the local policyengine-us checkout, with
TR2008's AWI, and compares every one with its committed source. It writes
`result.json` and `RESULTS.md`, each headed `INVENTED DATA - NOT A
COMPARISON`. The runner refuses a `registered_real` cohort without the
issue #42 registration pointer.

## Named gaps

The dry run's `result.json` carries the full list: mortality substitute,
DI netting at single-year cells, no earnings after the opening year, no
pre-1968 earnings, approximated DI and pre-eligibility-death levels, the
disability clock for awards at 62 or later, insured status (not modeled
for retirement or survivor benefits), spouses outside the roster (never
widowed, and no spouse's benefit rests on their record; counted per row
as `spouse_outside_roster`, or `spouse_unlinked` for a married claimant
with no linked spouse), persons whose opening-year Social Security A3
could not observe (they open as non-recipients, so any benefit is
projected; counted as `beneficiaries_ss_opening_year_unobserved`),
widow(er)s of workers who died before the opening wave, no projected
disabled widow(er)s, no marriage dynamics, auxiliary entitlement timing,
the realized wage base (2009-2010 differ from TR2008's projections; R0-R5
only), R6's receipt start censored at 2008, R6's 2009-wave M4 status,
opening-stock DI recovery, and claiming.

Each row also carries `reduced_increases_by_age_group`, a diagnostic
whose `reduced_increases_definition` says which PIA's count it shows: a
dually entitled person's spouse's or widow(er)'s amount can rest on a
PIA with a different count.

Two A4 and A6 alternatives do not run as a registered choice would need:

- A4's `termination_basis="select_and_ultimate"` needs the award year of
  every opening disabled worker. A3 observes it only when first receipt is
  bracketed (none in 2008, some in 2010); otherwise only an upper bound is
  known, which the opening clock uses but which is not an award year. The
  initial slice therefore leaves `di_award_year` empty for those persons
  and A4 refuses the projection (`prepare_opening_di_state`).
- Under `auxiliary_entitlement_clock="worker"`, R2 has no exposure start
  for the widow(er) of a worker who was never entitled (A6 leaves it
  undefined). That widow(er)'s benefit is dropped from R2 only (counted as
  `entitlement_clock_undefined`), so R2's membership can differ from R0's.
