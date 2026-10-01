# PolicyEngine-US population run

**INVENTED DATA - NOT A COMPARISON, NOT THE US.** This path runs on an
invented population by design. Its numbers describe that invented
population and nothing else.

The bridge (`docs/design/pe_us_bridge.md`) runs one household per
PolicyEngine-US simulation. This path runs a whole population through **one
weighted `Microsimulation` per scenario**, splits every household's change in
`household_net_income` exactly as the bridge does, and sums the households
with exact weights into totals by component and by level of government.
The scenario loop constructs the simulations in
`population.py:980-995`; weighted identities are checked in
`population_summary.py:310-363`.

The first use is exercise 4's headline minimum benefit (option 2 against
current-law benefits, Track M row MS0), as in the bridge, on invented
PSID-shaped family units at 300 and 3,000 family units.

Code:

- `src/populace_dynamics/bridge/population.py`: the array frame, the dataset
  layout, the runner, the vectorized decomposition, exact weights, levels of
  government and deciles. Pure Python; it imports no `policyengine_us`.
- `src/populace_dynamics/bridge/population_summary.py`: weighted totals, the
  share taken back, groupings and the Medicaid, CHIP and MSP cost split.
- `src/populace_dynamics/bridge/invented_population.py`: the invented
  population, from `invented_psid` through Track M's cohort, careers and
  rules.
- `scripts/pe_us_population_invented.py`: the run and its outputs.
- Outputs: `docs/analysis/pe_us_population_invented_20260930/`.

Run from a clean checkout with the approved dynamics interpreter selected
as `DYNAMICS_PYTHON`:

```sh
OMP_NUM_THREADS=1 PYTHONPATH="$PWD/src:$PWD" \
POPULACE_DYNAMICS_PE_US_PYTHON="$HOME/.venvs/policyengine-us-2.18.0/bin/python" \
"$DYNAMICS_PYTHON" scripts/pe_us_population_invented.py \
    --family-units 300 3000 --seed 20260930
```

The script records the code commit and whether `src/` or `scripts/` were
dirty (`scripts/pe_us_population_invented.py:633-647`). Runtime and memory
are measurements; deterministic reproduction compares inputs and outcomes,
not those measurements (`test_population_oracle.py:451-486`).

## Why invented data

The first attempt at a population run stopped at its protocol gate (its
Phase 0) before reading any PSID file or running any code. Max's d479 adopts the
phase-2 plan's rules for post hoc work on spent exercises, which say
"Development checks use invented cases." A run that produced new real-data
outcomes on test 4's cohort would be neither registered nor an invented
check, and the cohort overlaps U2's live blind target (births 1946-55).

So this path is built and tested on invented data only. Phase 0 is
**permitted**, with reasoning **option A: invented data only, per d479**.
The real-data analysis is queued as d727 and needs a new issue #42
registration with a frozen specification and one shot before computing
outcomes. This build provides no authorization for a real-data run.

The code enforces the invented-only rule before Track M's rules run and
before the cohort is used to compute or map benefits:

- `invented_population.require_invented` refuses records not marked
  `invented`, records whose source carries a PSID file-provenance key
  (`PSID_PROVENANCE_KEYS`: the file hashes key,
  `pipeline.PSID_FILES_SOURCE_KEY`, and `psid_data_dir`) at any depth, and
  records without the invented generator's label. Even an empty key is
  refused. `evaluate_headline` reaches this records check through the
  cohort guard before `evaluate`
  (`invented_population.py:287-290,325-370,525,576-582`).
- `invented_population.require_invented_cohort` applies the records'
  guard and also requires the cohort, the frames and their structural
  inputs (which hold the anchor) to carry the invented label and no PSID
  file-provenance key at any depth. It checks agreement of the cohort and
  frame provenance, the records' source, the seed and family count, the
  structural inputs' seed, and the records' person ids, family units and
  weights against the cohort's person frame. It requires the anchor to
  hold exactly the cohort's persons, each once and in the family unit the
  cohort gives them. Last, it rebuilds the frames and the M4 cohort from
  the cohort's seed and family count (the generator and M4 are
  deterministic) and refuses any frame, mapping or value that differs, so
  the columns the path reads (the anchor; the cohort's roles, birth years
  and 2022 amounts) are the invented generator's. That rebuild took 2.5 to
  6 seconds at 3,000 family units in measurements on one host, moving with
  its load; each of the three entry points pays it once.
  `evaluate_headline`, `person_benefits` and `build_population` call the
  guard before evaluation, benefit conversion or mapping. Evaluation and
  benefit conversion accept the whole `InventedCohort`; callers cannot
  supply an independent `persons` frame
  (`invented_population.py:373-566,576-582,602-608,646,922`).
- The guard does not rebuild the records' careers:
  `careers.build_track_m_inputs` needs the SSA parameters and COLA
  history, which the guard does not hold (`careers.py:226-235`). The
  records are tied to the checked cohort only by their provenance and by
  each person's id, family unit and weight.
- `person_benefits` takes no evaluation. It evaluates the cohort's records
  itself under row MS0, so an evaluation of other records, of another row
  or marked `psid_files` cannot be supplied
  (`invented_population.py:569-573,602-608,663`).
- `build_population` draws the invented inputs with the cohort's seed. A
  different `seed` argument is refused; the default is the cohort's
  (`invented_population.py:923-929`).
- `evaluation.evaluate` has no provenance guard of its own; the tabulation
  and the pipeline hold them (`min_benefit_track_m/evaluation.py:27-29`,
  `pipeline.py:205-224`). Calling it on invented records is what those
  guards allow: the pipeline refuses only records carrying PSID file hashes
  outside the registered run (`pipeline.py:214-225`).
- `careers.build_track_m_inputs` itself refuses to mark a cohort read from
  PSID files as invented, and needs the invented label to mark one invented
  (`careers.py:244-260`).

Nothing in this path reads a PSID file, a projection, a restricted file or
a comparator value. The registered-run guards are untouched.

## What the path does

### 1. The invented population

- **Cohort and careers.** `invented_psid.invented_cohort_inputs` draws seeded
  PSID-shaped frames with `n_family_units` family units (default 300,
  `invented_psid.py:443-448`). `build_invented_cohort` runs them through
  Track M's M4 cohort (`cohort.build_cohort`) and M5 careers
  (`careers.build_track_m_inputs`) with provenance `invented`
  (`invented_population.py:293-322`).
- **Benefits.** `evaluate_headline` applies Track M's rules under row MS0.
  `person_benefits` evaluates the same records under the same row itself
  and turns each worker record's PIA into each person's 2026
  benefit under current law (the history PIA), option 1 (a memo) and
  option 2. PIAs are carried to 2026 with statutory COLAs as the bridge
  carries them (`bridge.carry_pia_forward`), times the own claim factor and
  rounded down to the dollar, as the bridge's worker is
  (`scripts/pe_us_minimum_benefit_sample_households.py:789`,
  `invented_population.py:595-599,670-679,737-740`). Spouse's and
  widow(er)'s excesses come from the oracle's `spousal_benefit` and
  `widow_benefit` (`ss/benefits.py:205-241`, `:266-329`).
  A person marked as paid an own worker benefit without an own record
  among the cohort's records is explicitly refused before the evaluation
  and before any benefit is computed (`invented_population.py:649-662`).
- **Two groups keep their 2022 amount**, carried by the COLAs, in every
  scenario, because Track M computes no benefit for them: unlinked
  auxiliaries, and people paid an own benefit whose record holds no observed
  covered earnings (`invented_population.py:677-679,730-736,768-776`).
  The invented generator, like the PSID panel it mimics,
  draws labor income for reference persons and spouses only
  (`invented_psid.py:599-617` draws other members' receipt but no
  earnings), so without this PolicyEngine-US would pay them SSI as if they
  had no Social Security.
- **Everything else is invented.** The generator draws no state, income
  other than Social Security, assets or rent.
  `invented_other_inputs` draws them from `INVENTED_DISTRIBUTIONS`, each
  entry labelled `INVENTED`, on a seed stream apart from the cohort's
  (`invented_population.py:151-208,817-873`). Each maps to a
  PolicyEngine-US input by
  `estimates.adjusted_poverty`'s conventions where one exists
  (`INPUT_CONCEPTS`, `invented_population.py:213-265`): labor to
  `employment_income` (the earned items,
  `data/family_income.py:1148-1154`, `adjusted_poverty.py:118`), interest
  to `interest_income` (`family_income.py:1131-1143`), annuities to
  `taxable_private_pension_income` (`adjusted_poverty.py:28-33`),
  `max(0, WEALTH1 - vehicles)` to `bank_account_assets` (the resource proxy,
  `adjusted_poverty.py:118-119, 1469`; an SSI resource in 2.18.0,
  `parameters/gov/ssa/ssi/eligibility/resources/countable.yaml:7`), and
  twelve months' rent to `pre_subsidy_rent`.
- **Households.** Each family unit is one household, SPM unit and family.
  The reference person and spouse form one marital unit and one joint tax
  unit; every other member is a marital unit and tax unit of their own
  (`invented_population.py:888-1075`, `build_population`). Current family
  membership comes from the frames' anchor, which must contain exactly the
  cohort's universe persons, each in the same family unit. An anchor member
  outside that universe, or a missing or differently placed member, is refused
  because this path has no inputs for them. The cohort guard makes this
  check, so evaluation and benefit conversion refuse such a cohort too
  (`invented_population.py:405-442,563-565`). Medicare quarters of coverage
  stay at PolicyEngine-US's default
  of 40 (`variables/gov/hhs/medicare/eligibility/part_a/
  medicare_quarters_of_coverage.py:16`), the premium-free Part A threshold
  (`is_premium_free_part_a.py:17-20`): every person receives OASDI.

### 2. The population as arrays

`PopulationFrame` holds people (age, the bridge's `AMOUNT_FIELDS`, Medicare
quarters) and each person's unit of each of PolicyEngine-US's five group
entities as an index array, with each household's state and weight
(`population.py:224-350`). It enforces the invariants of the bridge's
`BridgeHousehold` over arrays:

- every person is in exactly one unit of each kind (by construction), and
  no unit is empty;
- a marital unit has at most two people;
- every unit lies inside the units that 2.18.0 declares as containing it
  (`containing_entities`, `policyengine_us/entities.py:35,53,71,89`);
- amounts are finite and nonnegative, weights positive, ids unique.

`from_households` and `to_households` convert to and from the bridge's
validated households, which validate each household again
(`population.py:417-604`). The mappings and their array buffers are
immutable, so validated values cannot be replaced or made writable
(`population.py:158-162,268-316`).

### 3. One simulation per scenario

`PopulationFrame.to_dataset` writes policyengine-core's `TIME_PERIOD_ARRAYS`
layout, `{variable: {period: array}}`, with an id array per entity, a
membership array and a role array per group entity, and the inputs
(`population.py:616-666`).

How policyengine-us 2.18.0 accepts it:

- policyengine-core's `Dataset` has a `TIME_PERIOD_ARRAYS` format
  (`policyengine_core/data/dataset.py:60-73`) saved by `save_dataset`
  (`:184-219`).
- `Simulation.build_from_dataset` builds each entity from its id array and
  each group from the `person_<entity>_id` membership arrays
  (`policyengine_core/simulations/simulation.py:405-562`). Without a
  `person_<entity>_role` array it gives a group one default role per
  *unit*, not per person (`simulation.py:482-483`), so the frame writes one
  role per person. An integer role indexes the entity's roles
  (`simulation_builder.py:294-295`); 0 is each entity's single role,
  `member` (`policyengine_us/entities.py:10-17`).
- policyengine-us's `Microsimulation` intercepts only a dataset given as a
  path or a `USSingleYearDataset`; a core `Dataset` instance passes through
  to core unchanged (`policyengine_us/system.py:462-495`).
- A `Microsimulation` weights results by `household_weight`
  (`policyengine_core/simulations/microsimulation.py:16-46,64-82`). The
  runner reads every value with `use_weights=False` and weights exactly
  itself (section 5).

`run_population` (`population.py:1110-1273`) runs one simulation per
scenario (baseline, reform) and variant (health coverage outside net
income, and inside it as a sensitivity) in the policyengine-us interpreter,
after the bridge's source and version checks. It applies the bridge's
parameter override, California's published 2026 SSI payment standard. The
bridge applies it to California's cases only; one simulation holds every
state, so here it applies to all. That is safe because every variable that
reads the parameter is under `variables/gov/states/ca/` and defined for
California only (`ca_state_supplement.py:10`,
`ca_wdp_ssi_ssp_income_eligible.py:23`), and
`parameter_overrides` refuses any override outside its own states'
`gov.states.<state>.` namespace
(`scripts/pe_us_population_invented.py:141-160`). Reformed
`CountryTaxBenefitSystem` objects are constructed directly
(`population.py:983-986`; the same constructor used by the installed
`policyengine_us/spm.py:813-818`), without an extra simulation. The child
checks that each group's
membership is the dataset's, with one `member` role per person, and returns
every node of the net-income tree per household.

### 4. Formulas that aggregate across a simulation

The bridge runs one household per simulation because some 2.18.0 formulas
aggregate over a whole simulation (`pe_us_bridge.md`, "One simulation per
case"). A search of 2.18.0's `variables/` for simulation-wide reductions
(`sum_by_state`, weights, `np.unique`, `bincount`, ranks, quantiles,
`is_over_dataset`, reads of the simulation object) finds these formulas
whose value for one household depends on the others:

| Formula | What it aggregates | How the population path handles it |
|---|---|---|
| `medicaid_slcsp_state_average_cost_index` | The weighted average cost index over every person in the state (`medicaid_slcsp_state_average_cost_index.py:14-29`, `state_aggregate_helpers.py:11-26`) | Pinned to the household's own value (below) |
| `medicaid_slcsp_state_denominator` | Over a dataset, the weighted index summed over the state's enrollees, so a state's Medicaid cost sums to its calibrated spending (`medicaid_slcsp_state_denominator.py:21-26`); for a single household, state enrollment times the state-average index (`:28-33`) | Pinned to the single-household branch |
| `household_income_decile`, `spm_unit_income_decile` | Weighted decile ranks over the simulation (`household_income_decile.py:12-21`, `spm_unit_income_decile.py:14-15`) | Used only as a grouping, from the baseline simulation; recomputed and checked equal |

Medicaid at cost is the state's spending times the person's filled cost
index over the denominator (`medicaid_cost_if_enrolled.py:11-22`). By default
(`medicaid_valuation="household"`) the child pins the two Medicaid inputs,
before anything reads them, to the values policyengine-us computes for each
household simulated alone: the average of the positive cost indices of the
household's own members at weight 1, and the state's enrollment times that
average (`population.py:919-958`). The resulting value per enrollee is
state spending divided by state enrollment, multiplied by the enrollee's
filled cost index divided by their household's positive-index average
(which falls back to 1 when there is no positive index). A household's
results then do not depend on the rest of the population. `"native"` leaves
the dataset formulas in place, which spread each state's whole calibrated
spending over the simulated enrollees; for an invented population that is
meaningless.

Other reads across units are inactive or harmless here:

- the Medicaid claiming-tax-unit lookups match
  `medicaid_claiming_tax_unit_id` against every `tax_unit_id`
  (`variables/gov/hhs/medicaid/income/_claiming_tax_unit.py:7-51`, matching
  only a positive id, `:48-50`), and the id defaults to 0, "no known claiming tax unit"
  (`medicaid_claiming_tax_unit_id.py:10-14`);
- the behavioral responses read `simulation.baseline`, which is `None`
  when a reformed system is supplied without a `reform` argument (`capital_gains_responses.py:40-41`,
  `labor_supply_behavioral_response.py:18-19`); the runner passes reformed
  systems as `tax_benefit_system`, never as `reform`, and refuses a
  simulation with a baseline branch;
- `county` reads a stored county over a dataset
  (`county/county.py:25-33`); none is stored, so it falls through to the
  same `county_fips` mapping as a single household;
- `spm_unit_allocated_tenant_payment` returns zeros early when no unit in
  the simulation is awarded housing assistance
  (`spm_unit_allocated_tenant_payment.py:13-15`), the same values it would
  compute per household; housing-voucher take-up is off here.

The search found no random draws (`random(`) in 2.18.0's variables.

**The tests show it.** The differential runs the bridge's three
illustrative households, read back from their committed situations, as one
population, and every household's decomposition and memo values equal the
committed per-household results in integer cents. A second differential
runs twelve invented multi-person households (couples filing jointly, other
members filing alone, in six states chosen for their mechanisms) through the
bridge one household at a time and through the population path together;
they agree exactly (`tests/bridge/test_population_oracle.py:411-445`).
The illustrative differential covers three household types in three states,
nine households together (`test_population_oracle.py:181-232`). A third
test runs the native Medicaid formulas and shows
each state's cost summing to its calibrated spending, far from the
one-household values (`test_population_oracle.py:254-294`). A household
whose Social Security does not change must not change any component
(`household_checks`), which checks for leaks even when component changes
cancel in net income
(`scripts/pe_us_population_invented.py:263-297`,
`tests/bridge/test_population.py:1856-1875`).

### 5. Decomposition and exact weights

- `decompose_population` applies the bridge's decomposition to every
  household at once (`population.py:1522-1632`): the same tree and
  definition checks, every aggregate within $0.50 of its parts, finite
  values, leaves rounded to cents, and policyengine-us's own net change
  within $0.50 of the definition's. Every household's leaf changes sum
  exactly to its net change. A property test pins it to the bridge's
  `decompose`, household by household.
- `to_cents_array` is the bridge's `to_cents` vectorized. A float32 value
  has a 24-bit significand, so 100 times it is exact in float64, and
  rounding it half to even is the bridge's decimal rounding
  (`population.py:1380-1403`); other values take the bridge's function.
- `ExactWeights` writes each float weight as an exact integer over one
  power-of-two denominator (every finite float is a dyadic rational), so a
  weighted sum of integer cents is an exact rational
  (`population.py:1639-1698`). Leaves, the bridge's categories and levels of
  government are each partitions of the leaves, and households are
  partitioned by each grouping, so every total sums exactly to the weighted
  net change. `summarize` checks each identity and refuses to write if one
  fails (`population_summary.py:310-363`). JSON exports exact rational
  dollar values alongside rounded displays (`population_summary.py:61-73,264-302`),
  so its identities can be checked independently. Rounded tables can differ
  by cents when their entries are added.

### 6. Levels of government

`level_for` (`population.py:1353-1369`) assigns each leaf:

- **State:** every leaf under `household_state_benefits` ("Benefits paid
  by State agencies", `household_state_benefits.py:9-11`),
  `household_state_tax_before_refundable_credits` (state income and use tax,
  `household_state_tax_before_refundable_credits.py:10`) or
  `household_refundable_state_tax_credits`, and the Alaska Permanent Fund
  Dividend, which 2.18.0 lists as market income
  (`parameters/gov/household/market_income_sources.yaml:28`).
- **Local:** local income and occupational taxes
  (`household_tax_before_refundable_credits.py:17-18`).
- **Federal:** Social Security, SSI, SNAP, the other federal benefits in
  the tree, federal income tax and refundable credits, payroll taxes.
- **Health:** health benefits and costs, in net income only in the
  with-health variant; their federal and state split is reported
  separately.
- **Market income:** the other leaves of `household_market_income`, which
  no reform here changes. This accounting category is not a level of
  government.

A leaf with no level that changes for any household is refused
(`UnclassifiedChangeError`, `population.py:1619-1631`).

The **share taken back** is `(dSS - dNet) / dSS`: the part of the change in
Social Security that other programs and taxes offset. It splits exactly
into federal (every federal leaf but Social Security), state, local and
health parts (`population_summary.py:122-154`). For a cut it is the share
cushioned; for a group whose Social Security rises for some households and
falls for others it is a ratio of net sums, flagged in the outputs.

**Medicaid, CHIP and the Medicare Savings Programs.** 2.18.0 splits their
cost between the federal government and the state:
`medicaid_federal_cost` is `medicaid_cost` times the FMAP-based
`medicaid_federal_share` and `medicaid_state_cost` the rest
(`medicaid_federal_cost.py:17-20`, `medicaid_state_cost.py:17-20`); CHIP
likewise with its enhanced share (`chip_federal_cost.py:18-19`,
`chip_state_cost.py:18-21`); the MSP federal cost applies the FMAP to QMB
and SLMB and the QI federal share to QI, month by month, and is zero for a
Medicaid enrollee (`msp_federal_cost.py:24-50`), with the state paying the
rest (`msp_state_cost.py:17-21`). `health_split` reports each weighted
(`population_summary.py:388-450`); independently rounded float32 cost
parts can differ from the total. `max_split_gap_cents` records the largest
**per-person** gap; invented weights can magnify it in weighted tables.
These memo cost splits are separate from the exact net-income identity.

### 7. Outputs

`scripts/pe_us_population_invented.py` writes, for each size, through its
`markdown`, `draw_chart` and `write` functions (the JSON records mechanism
file:line references):

- JSON with every total, grouping, check, the invented distributions, the
  release's provenance and the runtime and memory;
- Markdown tables: totals, levels of government, components, groupings by
  SSI receipt, baseline income decile and direction of Social Security,
  the health cost split, runtime, checks and the invented inputs;
- a stacked-bar chart (PNG and SVG) of the mean change per household by
  component, by decile and by SSI receipt, with and without Social
  Security.

Every output and chart carries "INVENTED DATA - NOT A COMPARISON, NOT THE
US".

Measured PolicyEngine-US child runtime includes imports, source checks and
all four scenario/variant simulations (`population.py:980-995,1196-1200,1258-1266`;
`scripts/pe_us_population_invented.py:467-492`). Bounds are set in
`scripts/pe_us_population_invented.py:124-127`.

| INVENTED family units | People | Wall seconds | Peak RSS GiB | Bounds (seconds / GiB) |
|---|---:|---:|---:|---|
| 300 | 427 | 784.9 | 3.13 | 1200 / 8 |
| 3,000 | 4,305 | 492.7 | 6.48 | 2400 / 12 |

Both sizes satisfy their bounds. Regenerated outcomes are compared with
the prior artifacts at both sizes; the live oracle repeats the 300-family
run's outcome and check fields. Timing and memory vary with host load.

## Invariants

The mapper validates the input invariants below. The tests and runtime
checks establish the result identities for this supported invented
configuration, with housing-voucher take-up off and household Medicaid
valuation; they do not establish separability for arbitrary future inputs.

1. **Membership.** Every person is in exactly one unit of each of the five
   group entities; no unit is empty; marital units hold at most two people;
   every unit lies inside its containing units (Hypothesis,
   `tests/bridge/test_population.py`).
2. **Round trips.** The frame round-trips exactly through policyengine-core's
   dataset layout, through the bridge's households and through the bridge's
   situations; a subset keeps every household's people and amounts.
3. **Refusals.** A negative or non-finite amount, a non-integer unit index, an
   empty or overfull unit, a unit spanning two containers, an unknown state
   or a nonpositive weight is refused.
4. **Household identity.** Every household's leaf changes sum exactly, in
   integer cents, to its net change, and equal the bridge's `decompose`
   (differential, Hypothesis).
5. **Weighted identity.** Weighted leaves, categories and levels each sum
   exactly to the weighted net change; each grouping's groups sum exactly to
   the population's net and Social Security changes; the take-back parts sum
   exactly to the share.
6. **Exact weights.** `ExactWeights` represents every weight exactly and is
   linear.
7. **Separability.** A household whose Social Security does not change does
   not change at all (checked in every run).
8. **Population equals households.** The population path reproduces the
   bridge's one-household results exactly (the two differentials above).
9. **Social Security in equals Social Security out.** PolicyEngine-US's
   `social_security` leaf equals each household's sum of the four frame
   inputs (retirement, disability, survivors and dependents) in both
   scenarios and both net-income variants. These include Track M's
   computed benefits and the 2022 amounts carried by COLAs for unlinked
   auxiliaries and people paid an own benefit with no observed covered
   earnings (`scripts/pe_us_population_invented.py`,
   `social_security_check`).
10. **Deciles.** The recomputed deciles equal policyengine-us's
    `household_income_decile` in every household, and equal the weighted
    rank definition by brute force (Hypothesis).
11. **Determinism.** The same seed gives the same population, benefits and
    results; the committed 300-unit outputs are rebuilt live and must
    match.
12. **Invented only.** Records not marked invented, carrying a PSID
    file-provenance key at any depth or lacking the invented label are
    refused before `evaluate` runs. The cohort, frames and structural inputs
    must carry the invented label and no PSID file-provenance key, and the
    cohort's provenance and person ids, family units and weights must agree
    with the records before evaluation, benefit conversion or population
    mapping (Hypothesis: any combination of provenance faults is refused by
    every entry point before anything is computed).
13. **The generator's output.** A cohort passes the guard only if its
    frames and M4 cohort equal what the invented generator and M4 give for
    its seed and family count, and its anchor holds exactly its persons.
    Every cohort `build_invented_cohort` builds passes; the same cohort
    relabelled, consistently, as another seed or size does not; and
    dropping or repeating a row or changing a number in any frame is
    refused by every entry point before anything is computed (Hypothesis).
14. **One evaluation, one seed.** The benefits come from one evaluation of
    the cohort's own records under row MS0, and the invented inputs are
    drawn with the cohort's seed.

## What the real-data version must add

The registered post hoc analysis (d727) needs, at least:

- **Its registration first.** A new issue #42 registration with a frozen
  commit and specification, and one shot, under the phase-2 plan's rules
  that d479 adopts. It must enter through a registered entry point with its
  own guard keyed to the registration, as the pipeline's is
  (`pipeline.py:205-224`); `require_invented` must keep refusing real
  records on this invented path, and no guard may be bypassed.
- **What it may not report.** The per-person rows here carry each person's
  `receives_2`. On real data one weighted mean of it recomputes exercise 4's
  registered headline statistic outside the registered entry point
  (Phase 0 record), and the count here
  (`persons_receiving_minimum_option_2`) would be a real-data statistic.
  The specification must say what is reported, and every weighted
  distribution of the 1946-55 births stays restricted while U2 is blind.
- **Real inputs for what is invented here.** State, income other than
  Social Security, assets and rent from the 2023 PSID family file, through
  `estimates.adjusted_poverty`'s item conventions: labor, farm and business
  labor as earned income; asset income; annuities and IRAs; pensions and
  other unearned income; WEALTH1 less vehicles as liquid resources; rent
  or housing costs. County and municipality inputs are also needed to
  represent local tax exposure; this frame supplies only the state
  (`population.py:616-666`). The measured local change is zero in both
  invented runs.
- **Real family structure.** PSID family units include members outside the
  Track M universe (children, younger spouses, other relatives). This path
  refuses such current anchor members. The real version needs inputs for
  them, rules for dependents and filing status, and SPM units that may not
  match family units.
- **Weights and uncertainty.** The 2023 cross-sectional weights, and a
  variance method for the PSID design (strata and clusters), since the
  exact totals here carry no sampling error.
- **Benefits Track M does not compute.** A rule for people paid an own
  benefit with no observed covered earnings and for unlinked auxiliaries,
  who keep their 2022 amount here; and a choice about disability-origin
  benefits, entered here as retirement benefits.
- **Medicaid valuation.** A ruling on whether Medicaid is valued as for a
  household alone (here) or allocated from state spending.
- **The float32 trace guard.** The bridge traces one household at a time;
  the population run counts leaf changes under $2 instead. A real run
  should trace a sample of households whose changes are small or sit at an
  edge.
- **Take-up and behavior.** Take-up is policyengine-us's default (full for
  SSI, SNAP and Medicaid); there is no behavioral or claiming response.
