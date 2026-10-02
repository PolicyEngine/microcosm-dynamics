# SSI's asset test and a Social Security cut at depletion, on a population

- **Status:** draft, not registered (`sa1-draft-4`). This specification is
  registered in two issue #42 comments, as Registration 18 is (§15).
  Before the first comment, this file changes only in its version
  (`sa1-ratified-1`), its status (`ratified_frozen`), the §18 block's
  `version` and `status`, the changelog (§19) and the ratification
  record (§20). That file is committed and pushed to branch
  `pe-us-depletion-cut-population-20261001`, and the first comment
  records its path, that commit and its SHA-256. That recording is the
  ratification. Max authorized the registration and the one-shot run in
  chat on 2026-10-01 (cos decision d806, quoted in §15); his ruling names
  no ratification mechanism, and merging cannot ratify, because the code
  stacks on PR #506, which is not merged. Any change to the ratified file
  ends the registration; a corrected version needs a new registration.
- **Specification:** `pe_us_depletion_cut_population_ssi_asset_test`,
  version `sa1-draft-4`.
- **Question.** At the NASI meeting on 2026-10-01, participants asked
  whether SSI would really replace the income a Social Security cut takes
  away, given that SSI's asset limit excludes many people. PR #506's
  illustrative households each hold $1,500 in the bank, under the limit,
  so SSI replaced the low earner's cut dollar for dollar. This analysis
  runs the same cut on a population that carries imputed assets and
  reports how often SSI would replace the lost benefit, in part or in
  full, with and without the asset test. Participants asked for results
  by age, sex, marital status, race and income quintile.
- **Claim class.** A static, one-year microsimulation on Microcosm's
  cross-sectional population frame, under 2026 law and prices. It is not
  a projection, it has no behavioral response, and it does not test the
  Dynamics projection engine. The frame is calibrated to some national
  totals but not to the ones this question turns on (§2.3), so every
  result is frame-relative.
- **Labels on every output** (JSON, Markdown, chart titles and chart file
  metadata), held equal to the code's constants:
  - *FRAME-RELATIVE: Microcosm populace-us-2024 frame; liquid assets are
    imputed and not calibrated, and beneficiary counts are not calibrated
    to national totals.*
  - *Applied to 2026 law and prices: the cut would not happen in 2026,
    and this is not a projection.* (A population version of PR #506's
    `LAW_YEAR_NOTE`, which describes households.)
  - *Static: no behavioral response.*
  - *Registered one-shot, not blind: registered after PR #506's
    illustrative results and after real-data diagnostics on this frame
    were seen (issue #42, Registration 19).*
  - *Headline basis: potential federal SSI replacement, as if everyone
    eligible takes SSI up, under the row's modeled resource test; shares
    count cut beneficiaries by replacement of their marital unit's
    combined cut.*

Abbreviations: SS is Social Security; SSI is Supplemental Security
Income; OASI, DI and OASDI are the Old-Age and Survivors Insurance,
Disability Insurance and combined trust funds; ABD is aged, blind or
disabled (SSI's categorical test); PE-US is PolicyEngine-US; FBR is the
SSI federal benefit rate; SCF and SIPP are the Survey of Consumer
Finances and the Survey of Income and Program Participation; MINT is
SSA's Modeling Income in the Near Term model. `PEUS` below means the
installed `policyengine_us` package of PE-US 2.18.0, `CORE` its
`policyengine_core` 3.32.11, and line numbers are from those releases.
`EV` is `~/microcosm-launch-evidence/dynasim-parity-20260909`.

## 1. Estimands

For each cut scenario *r* (§3) and registered row (§7), over the
universe of beneficiaries whose benefit the cut reduces (§2.4):

1. **Replaced, under the row's resource test:** the weighted shares of
   beneficiaries whose marital unit's combined cut federal SSI replaces
   in full, in part, or not at all (§5). These are PE-US's modeled SSI
   responses under the row's resource test, not a complete implementation
   of federal law (§12).
2. **Replaced, no asset test:** the same three shares when SSI's resource
   test is removed (§4.3).
3. **Blocked by the asset test:** the weighted share whom SSI would
   replace, in part or in full, without the asset test but not at all
   with it: complete prevention of any replacement. A companion, **partly
   blocked**, is the share replaced in full without the asset test and
   only in part with it (§5).
4. **Blocked, conditional:** estimand 3 divided by the share replaced in
   part or in full without the asset test: of the beneficiaries SSI would
   otherwise compensate, the share the asset test stops.

**Headline**, designated before any result and never promoted
afterwards: row R0 under the 22 percent OASI cut, all beneficiaries,
estimands 1 to 4. Rows R3 (spousal deeming) and R4 (household pooling)
are reported beside it in every table. They show how the result depends
on where the frame places assets; they are not bounds on R0, which can
block more or less often than R3 (§7).

## 2. Population

### 2.1 The frame

- **Repository:** Hugging Face dataset `policyengine/populace-us`, file
  `populace_us_2024.h5`, tag `populace-us-2024-spm-20260909`, which
  resolves to commit `9a814a3b3b53c0ecd6e1737b6ec862c31300ef6f`. The run
  downloads by commit, not by tag.
- **Bytes:** 826,917,837. **SHA-256:**
  `6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84`.
  The run refuses any other bytes.
- PE-US 2.18.0's own default dataset URI names this blob by the
  `-20260909` tag (`PEUS/system.py:64`, SHA-256 at `:72-74`). The same
  blob is tagged `populace-us-2024-spm-20260915`, the default of
  policyengine.py's certified US bundle (origin/main `6a9c878`, certified
  there for PE-US 2.2.1).
- **Why not the pinned w1 frame.** The frame this repository pins for
  gate W1 (`src/populace_dynamics/data/deployment_frame.py:43-62`,
  revision `populace-us-2024-sparse-l0-refit-57k-71a0887-national-only-20260701`)
  has no `bank_account_assets`, `stock_assets` or `bond_assets` columns.
  It was built on 2026-07-01, before Microcosm's wealth stage existed
  (first commit 2026-07-09). PE-US would default those inputs to zero,
  and every person would pass the resource test.
- **Format:** pandas HDFStore entity tables (`/person`, `/household`,
  `/tax_unit`, `/spm_unit`, `/family`, `/marital_unit`), period 2024.
  PE-US 2.18.0 loads an HDFStore path directly and extends it to later
  years (`PEUS/system.py:462-475`), and checks the SHA-256 only for its
  own default URI (`:464-467`). The run checks it itself before loading.

### 2.2 Structural counts (pre-registration, disclosed)

Computed from the file without simulation:

- 57,240 households; 166,321 persons; 318 person columns. Household
  weights (`household_weight`) sum to 122,537,092; weighted persons
  340,077,323. A person's weight is their household's weight.
- 26,818 person records carry a Social Security component above zero,
  57.6 million weighted (2024 values).
- **Assets.** `bank_account_assets`, `stock_assets` and `bond_assets` are
  populated and never negative. Every household has at most one person
  with nonzero assets, always its lowest-`A_LINENO` person, which is the
  CPS reference person (`A_EXPRRP` 1 or 2) in 56,870 of the 57,240
  households; 52,637 households have such a person and 4,603 have none.
  Microcosm's wealth stage at the parent build's commit `cae8640`
  (`packages/populace-build/src/populace/build/us_runtime/scf_wealth.py`,
  docstring and line 150; the same code is at origin/main
  `packages/microcosm-build/src/microcosm/build/us_runtime/scf_wealth.py:50-57, 149-150`)
  draws each household's whole asset vector once, from SCF 2022 or SIPP
  2023 with equal probability, by quantile regression forest, and places
  it on the reference person. The frame's manifests do not record whether
  the SIPP donor was supplied, so whether these assets are that blend or
  SCF-only is not confirmed. Household `net_worth` is also imputed.
- **Demographics.** `age` (top-coded: ages above 79 are only 80 and 85,
  standing for 80-84 and 85+), `is_female`, `cps_race` (equal to the CPS
  `PRDTRACE` in every row), `is_hispanic`, and the CPS marital recode
  `A_MARITL` (codes 1-7) are populated in every row.
- **SSI inputs.** `meets_ssi_disability_criteria`, `is_blind`,
  `takes_up_ssi_if_eligible` and `immigration_status_str` are populated.
- **Marital composition** of beneficiaries aged 62 and over (frame
  weights): married 85.6 percent, widowed 7.9, divorced 4.0, never
  married 2.1, separated 0.4. Persons aged 65 and over live alone 9.1
  percent of the time. Both differ sharply from published figures (§12,
  difference 6).
- **Synthetic benefit splits.** 5,924 records (9.8 million weighted),
  all from Microcosm's PUF-support channel
  (`person_support_channel = puf_tax_detail`), carry all four Social
  Security components at once, in the same fixed proportions in every
  record: retirement 24.96, survivors 37.93, dependents 13.55 and
  disability 23.56 percent of the person's total. No other record has
  more than one positive component. The PUF-support stage splits a
  predicted total equally when its donor basis is zero
  (`puf_support.py:4223` at origin/main; `:2180` at `cae8640`); the
  frame's shares are not equal, so that step alone does not produce them,
  and the step that set them is not traced here. The run recomputes these
  shares as a structural check.
- **Child beneficiaries.** CPS asks income questions only of persons aged
  15 and over, but the PUF-support channel gives benefits to 25 records
  aged 0-14 (64,129 weighted, 2024). All are synthetic-split records.

### 2.3 What the frame is and is not calibrated to

- **Calibrated** (parent build
  `populace-us-2024-buildp-sparse-rmloss100-cae8640-20260728T011454Z`,
  5,659 targets, solved under PE-US 1.764.6): Social Security dollars by
  type against SSA's Annual Statistical Supplement 2025 (calendar 2024);
  IRS SOI taxable Social Security amounts and returns, nationally and by
  state; SSI dollars nationally and by state, and SSI recipients by state
  and by age group (December 2024); household net worth (Federal Reserve
  Z.1).
- **Not calibrated:** liquid asset holdings (bank, stock, bond), counts
  of Social Security beneficiaries, counts of people receiving both
  Social Security and SSI, and marital composition.
- Hence the FRAME-RELATIVE label. Shares are reported as the frame's
  shares; weighted counts are reported but labelled frame-relative.

### 2.4 The universe

- **Year:** 2026. PE-US 2.18.0 extends the 2024 frame to 2026: it uprates
  the Social Security components by the per-capita SOI Social Security
  series and the asset inputs by CPI-U, grows household weights with
  population, and carries forward inputs that have no uprating parameter
  (age included, so 2026 age equals frame age). The run records that
  2026 age equals the frame's age.
- **Universe for scenario *r*:** every person whose cut under *r* is
  positive (§3.2). Under the OASI cut that excludes beneficiaries whose
  only component is disability. All ages are included; under-18
  beneficiaries form their own age cell.
- **Weights:** PE-US's 2026 `household_weight`, applied to each member.
  Shares are ratios of weighted sums.

## 3. Policy: the cut

### 3.1 Payable shares

From PR #506, unchanged: the 2026 Trustees Report, section II.A,
intermediate assumptions, parsed by `trustees_citation` in
`scripts/pe_us_depletion_cut_sample_households.py` from the committed
page (`docs/analysis/pe_us_depletion_cut_20261001/sources/`).

- **Primary: a 22 percent OASI cut** (payable share 0.78, the `OASI`
  quote). It reduces the retirement, survivors and dependents components
  and leaves the disability component whole.
- **Sensitivity: a 17 percent OASDI cut** (payable share 0.83, the
  `OASDI` quote). It reduces all four components.

The run takes both shares from `trustees_citation(...)["quotes"]`, not
from constants, and records the citation.

### 3.2 Rounding and the per-component rule

For each person *i* and each component *k*, let *a<sub>ik</sub>* be the
value `calculate(component, 2026)` returns (float32) in a separate probe
simulation of the frame with no reform and no inputs set, converted to
float64. For each component the scenario cuts:

```text
m_ik = floor(a_ik / 12)                     whole-dollar monthly benefit
p_ik = floor(m_ik * s)                      PR #506's payable_monthly_benefit
c_ik = 12 * (m_ik - p_ik)                   annual cut
a'_ik = a_ik - c_ik                         the reform input
c_i  = sum over cut components of c_ik      the person's annual cut
```

- *s* is the payable share,
  `Decimal(citation["quotes"][fund]["payable_share"])` (the citation
  holds it as a string);
  `m_ik` is passed as a Python `int` to
  `depletion_cut.payable_monthly_benefit`, which rounds down to the whole
  dollar under PR #506's `ROUNDING_RULE` (modelled on 42 USC 415(g)). A
  vectorized version must equal it element by element. Taking
  `m_ik = floor(a_ik / 12)` is this analysis's choice; `floor` is exact
  (an integer `m` with `12m <= a_ik < 12(m + 1)`).
- The annualized monthly remainder, *a<sub>ik</sub>* − 12
  *m<sub>ik</sub>*, which lies in [0, 12), is preserved. The baseline is
  the frame's own 2026 values, untouched.
- Each component is cut and rounded on its own. That is this analysis's
  registered choice, following PR #506, which cuts each of a couple's
  benefits on its own.
- **Inputs set.** Every scenario's simulation, the baseline included,
  receives all four components for 2026 through `set_input` before
  anything is calculated on that simulation: the baseline gets
  *a<sub>ik</sub>* unchanged, a cut scenario gets *a′<sub>ik</sub>*.
  PE-US stores them as float32. Nothing else in the frame changes.

## 4. SSI as PE-US 2.18.0 encodes it

### 4.1 The resource test

- `ssi_countable_resources` (Person, year) adds the parameter list
  `gov.ssa.ssi.eligibility.resources.countable`, which names exactly
  `bank_account_assets`, `stock_assets` and `bond_assets`
  (`PEUS/parameters/gov/ssa/ssi/eligibility/resources/countable.yaml:5-9`).
  Homes, vehicles, household goods, burial plots and retirement accounts
  are not counted; PE-US has no retirement-account variable.
- `meets_ssi_resource_test` (Person, month;
  `PEUS/variables/gov/ssa/ssi/eligibility/resources/meets_ssi_resource_test.py:11-25`):
  when `ssi_claim_is_joint`, the marital unit's summed countable
  resources are compared with the couple limit; otherwise the person's
  own resources are compared with the individual limit. It passes at
  equality (`<=`).
- `ssi_claim_is_joint` (`PEUS/variables/gov/ssa/ssi/ssi_claim_is_joint.py:10-15`):
  more than one member of the marital unit is ABD and a head or spouse of
  their tax unit. PE-US gives the head role to the oldest adult of a tax
  unit and, when no member of the unit is separated, the spouse role to
  the oldest remaining adult
  (`PEUS/variables/household/demographic/tax_unit/is_tax_unit_head.py`,
  `is_tax_unit_spouse.py`), so a married couple living with an older
  adult in the same tax unit may not be a joint claim.
- Limits: $2,000 individual and $3,000 couple, unchanged since
  1989-01-01 and not indexed
  (`PEUS/parameters/gov/ssa/ssi/eligibility/resources/limit/individual.yaml`
  and `couple.yaml`; 20 CFR 416.1205(c)). Asset inputs are uprated by
  CPI-U to 2026; the limits are not.
- **No resource deeming.** PE-US 2.18.0 deems an ineligible spouse's and
  parent's income but not their resources
  (`PEUS/variables/gov/ssa/ssi/eligibility/income/deemed/` holds income
  files only). Federal regulation deems both: 20 CFR 416.1202(a) counts
  an ineligible spouse's resources (other than pension funds) toward the
  eligible individual living with them, and 416.1205(a) tests the pair
  against the couple limit; 416.1202(b) deems a parent's resources, above
  the limits, to a child under 18. Row R3 applies the spousal rule (§7).
  The text of both sections is saved, with SHA-256, in the evidence
  folder (§15).

### 4.2 The rest of federal SSI

- `is_ssi_eligible` (Person, month; `PEUS/variables/gov/ssa/ssi/is_ssi_eligible.py:10-18`)
  is ABD and `meets_ssi_resource_test` and (citizen or qualified
  noncitizen). It is the only place the resource test enters federal SSI.
- `uncapped_ssi` is `defined_for = "is_ssi_eligible"`: the benefit rate
  less countable income. `ssi_if_takes_up` floors it at zero and caps it
  at the individual FBR when spousal deeming applies. `ssi` is
  `ssi_if_takes_up` for people whose `takes_up_ssi_if_eligible` is true
  (default true; the frame sets it).
- **Identity.** Across the installed package, the only non-test readers
  of `meets_ssi_resource_test` are `is_ssi_eligible`,
  `ma_state_supplement.py` and `ca_state_supplement_eligible_person.py`,
  and nothing in the SSI amount, income, deeming, couple-computation or
  status chain reads `is_ssi_eligible`, `ssi` or the resource test.
  Resources do not respond to the cut. So, person by person and month by
  month,
  `ssi_if_takes_up(asset test as encoded) = ssi_if_takes_up(no asset test) × meets_ssi_resource_test`,
  and the same holds for `ssi`. The run checks this identity for every
  person in every scenario (§10, row validity (a)); rows R3 and R4 rest
  on it.

### 4.3 The no-asset-test counterfactual

- A structural reform replaces `meets_ssi_resource_test` with a formula
  that returns true for every person. It is applied to the baseline and
  to both cut scenarios.
- It changes only what reads that variable: federal SSI through
  `is_ssi_eligible`, and two state supplements that read the federal test
  directly (California, `ca_state_supplement_eligible_person.py`;
  Massachusetts, `ma_state_supplement.py`). Downstream programs that read
  `ssi` or `is_ssi_eligible` (Medicaid through SSI receipt, SNAP's
  treatment of SSI, other state supplements) follow. State programs with
  their own resource tests (Connecticut, Colorado OAP, Missouri,
  Minnesota MSA and Illinois AABD, among others) keep them. None of this
  enters the estimands, which use federal SSI only.
- Not used: `gov.abolitions.meets_ssi_resource_test`, which makes the
  variable return its default, false, so that everyone fails
  (`CORE/simulations/simulation.py:776-783`); and zeroing the asset
  inputs, which would also change SNAP, Medicaid and Medicare Savings
  Program asset tests.

## 5. The replacement measure

SSI's claim unit is the marital unit: under couple computation a
couple's SSI is pooled and split equally, and an ineligible spouse's
income is deemed. A beneficiary's cut can therefore be offset by SSI paid
to either spouse. For a person *i* in the universe of scenario *r*, with
marital unit *u(i)*, and for an SSI variant *v* (the row's asset test,
or no asset test):

```text
C_u   = sum over j in u of c_j                                (annual cut)
dS_u  = sum over j in u of [ S_j(r, v) - S_j(baseline, v) ]   (annual SSI change)
S     = ssi_if_takes_up, summed over the 12 months of 2026 (row R2: ssi)
tau   = $1.00 a year

full  if dS_u >= C_u - tau
part  if tau < dS_u < C_u - tau
none  if dS_u <= tau
```

- Every beneficiary in the universe takes the label of their marital
  unit. Persons with no cut are not in the universe, even when their
  spouse is.
- *τ* absorbs PE-US's float32 storage. Every positive cut is at least $12
  a year (a one-dollar monthly cut), so the three labels never overlap.
- SSI that rises by more than the cut is labelled full; the run counts
  units with `dS_u > C_u + tau`.
- The none label covers unchanged SSI and SSI that falls. PE-US's modeled
  SSI can fall after a cut (§12, difference 12); the run counts units
  with `dS_u < -tau` and their weighted SSI loss.
- Labels describe the marital unit's combined cut. A beneficiary labelled
  full is in a unit whose SSI rises by the unit's whole cut; the measure
  does not attribute SSI to one spouse's cut separately.
- Federal SSI only. State benefits are reported as an unscored diagnostic
  (§13).

**Blocked and partly blocked.** By §4.2, each person's SSI under any
asset test equals the no-test SSI times that person's pass indicator.
Rows R3 and R4 apply one indicator to every member of a marital unit, so
under them a label either stays or falls to none. Row R0's encoded test
is person-level outside joint claims (§4.1), so a marital unit with two
ABD members that is not a joint claim can move from full to part under
R0. For each row, a person is **blocked** when their label is part or
full with no asset test and none under the row's asset test, and **partly
blocked** when it is full with no asset test and part under the row's.
The run records the full three-by-three transition table for every row
and scenario.

**Why SSI does not replace, without the asset test** (secondary; on the
eligibility basis only, so for rows R0, R3, R4 and R5, not R2). A person
labelled none with no asset test is assigned the first reason that
applies to their marital unit: (a) no member of the unit is ABD for SSI
(`is_ssi_aged_blind_disabled`); (b) no ABD member meets SSI's immigration
condition (citizen, or `is_ssi_qualified_noncitizen`); (c) otherwise, no
positive modeled SSI response (income too high, or SSI falls).

## 6. Statistics

For scenario *r*, row *R* and cell *g* (§8), over persons *i* in the
universe and in *g*, with weights *w<sub>i</sub>*:

```text
n         = number of person records (unweighted)
W         = sum of w_i                                      (frame-relative)
F_test    = sum of w_i [L_i(R) = full] / W
P_test    = sum of w_i [L_i(R) = part] / W
N_test    = sum of w_i [L_i(R) = none] / W
F_no, P_no, N_no                                            (no asset test)
R_test    = F_test + P_test                                 (replaced in part or full)
R_no      = F_no + P_no
B         = sum of w_i [L_i(no) in {part, full} and L_i(R) = none] / W
B_part    = sum of w_i [L_i(no) = full and L_i(R) = part] / W
n_cond    = number of person records with L_i(no) in {part, full}
W_cond    = sum of w_i over those records
B_cond    = B / R_no          (not estimable when R_no = 0)
```

- `_test` means the row's modeled resource test (R0: as PE-US encodes it;
  R3, R4: the alternatives of §7). It does not claim a complete
  implementation of federal law.
- Tables call `B` "completely blocked, among all cut beneficiaries" and
  `B_cond` "completely blocked, among beneficiaries SSI would otherwise
  compensate".
- No-asset-test labels are identical across rows on common records,
  except R2 (which measures `ssi`). R5 changes the reporting denominators
  only: excluded persons' cuts and SSI changes remain in their marital
  unit's calculation.
- The run reports every quantity for every row, scenario and cell,
  including undefined values with their reason.

## 7. Registered rows

Each row differs from R0 in one field. Every row is computed under both
scenarios; the 17 percent OASDI cut is the registered sensitivity for
every row.

| Row | Field changed | Value |
|---|---|---|
| **R0** | (headline) | Resource test as PE-US 2.18.0 encodes it (§4.1); assets where the frame places them; eligibility basis (`ssi_if_takes_up`, as if everyone eligible takes SSI up); all beneficiaries in the universe |
| R2 | SSI measure | `ssi`: the frame's take-up flags (`takes_up_ssi_if_eligible`) |
| R3 | Resource test | Spousal deeming as in 20 CFR 416.1202(a) and 416.1205(a)-(b): a person in a two-person marital unit passes when the unit's summed countable resources are at most the couple limit, whether or not the spouse is ABD; anyone else passes when their own countable resources are at most the individual limit |
| R4 | Resource test | R3's limits applied to the whole household's countable resources: every person is tested on the sum over all members of their household, against the couple limit in a two-person marital unit and the individual limit otherwise |
| R5 | Universe | Excludes the synthetic-split records: persons whose four frame components are all positive (§2.2) |

- **R3 and R4 are computed from the same simulations.** By the identity
  in §4.2, the SSI a row's asset test allows is
  `ssi_if_takes_up(no asset test) × T_R`, where `T_R` is the row's pass
  indicator. The run computes `T_R` in Python from PE-US's 2026
  `ssi_countable_resources`, marital-unit and household membership, and
  the limits PE-US reads (`gov.ssa.ssi.eligibility.resources.limit`). It
  also computes the encoded test the same way and compares it with
  PE-US's `meets_ssi_resource_test` (§10, row validity (b)).
- **Why R3 and R4.** The frame puts each household's assets on its
  lowest-`A_LINENO` person, and PE-US does not deem resources. A spouse
  who does not hold the assets, in a couple that is not a joint claim,
  therefore passes with $0, and so does a coresident parent or other
  relative. R3 applies the federal spousal rule PE-US omits. R4 assumes
  every coresident's assets are available to every claim unit in the
  household, which overstates them for coresidents who keep their own
  finances. R4 blocks at least as often as R3 (the same limit against at
  least as much in resources, given nonnegative resources and marital
  units nested in households, which the run checks). R0 can block more or
  less often than R3, because the encoded test applies the individual
  limit to an asset holder whose spouse is not ABD, where federal rules
  apply the couple limit. R3 and R4 are two alternative resource tests
  that show sensitivity to asset placement. Their range does not bound
  R0, and it does not bound blocking under the unknown actual ownership
  of household assets: both can overstate blocking when assets placed on
  a beneficiary belong to someone else in the household.
- No composite rows. No row may be added or promoted after registration.

## 8. Cells

One-way tables, each over the whole universe of the scenario:

- **All.**
- **Age** (PE-US's 2026 `age`, equal to frame age): under 18; 18-61;
  62-64; 65-69; 70-74; 75-79; 80-84 (frame age 80); 85 and over (frame
  age 85).
- **Sex:** female, male (`is_female`).
- **Marital status** (`A_MARITL`, through
  `deployment_frame.MARITAL_MAP`): married (codes 1-3), widowed (4),
  divorced (5), separated (6), never married (7).
- **Race and Hispanic origin:** Hispanic (`is_hispanic`, any race);
  otherwise by `cps_race`: White (1), Black (2), Asian (4), all other
  codes (other or multiple races).
- **Income quintile (primary).** Baseline pre-tax household income per
  person, including modeled noncash benefits and excluding health
  coverage:
  `(household_market_income + household_benefits − household_health_benefits) / household_count_people`,
  from the baseline simulation with the asset test as encoded. PE-US
  2.18.0 includes health coverage in `household_benefits` only when
  `gov.simulation.include_health_benefits_in_net_income` is set, which is
  off by default (`household_health_benefits.py`); the subtraction makes
  the exclusion explicit. Cutpoints are the weighted quintiles of this
  income over all Social Security beneficiaries in the baseline (persons
  whose four components sum above zero), the same cutpoints for both
  scenarios: `q_k` is the smallest income value at which the weighted
  share of beneficiaries with income at or below it reaches k/5, and a
  person's quintile is 1 + the number of `q_k` (k = 1 to 4) their income
  exceeds. Members of a household share a quintile.
- **Income quintile (secondary).** PE-US's `household_income_decile` in
  the baseline simulation with the asset test as encoded (deciles of
  household net income, person-weighted over all persons), collapsed to
  quintiles as ceil(decile / 2); decile −1 (negative household net
  income) is its own cell.

Every cell assignment, and both quintile systems, come from the baseline
simulation with the asset test as encoded and are the same for every
row and scenario.

## 9. Uncertainty and small cells

- **Interval.** A household bootstrap with 500 replicates. Households
  are sorted by household id (H of them). One generator,
  `numpy.random.default_rng(20261001)`, is created once; replicate *b* =
  0, …, 499 calls `rng.integers(0, H, size=H)` in order and counts each
  household's multiplicity. The same multiplicity vector serves every
  row, scenario and cell. Each replicate keeps the households' weights
  and recomputes every share in §6 with each person's labels and
  quintile held at their full-sample values. For each statistic, a
  replicate whose denominator is zero (`W`, or `R_no` for `B_cond`) is
  omitted and counted, never set to zero; the number of valid replicates
  is reported, and with none the interval is undefined with its reason.
  Endpoints are
  `numpy.quantile(valid_values, [0.025, 0.975], method="linear")`. The
  NumPy version is pinned by the frozen requirements. The interval is
  labelled *a frame-resampling interval: it excludes imputation,
  calibration and model uncertainty*.
- **Small cells.** The unconditional shares of a cell with `n < 50` are
  flagged *small cell (n < 50)*; `B_cond` is flagged when `n_cond < 50`.
  A denominator with no weight is *not estimable*. Every cell is reported
  (no-drop).
- No acceptance threshold, pass band or comparator exists. Nothing is
  graded.

## 10. Run-time checks

Each check's result is recorded in the artifact.

**Refusals.** The run writes no statistic if any of these fails (§14,
refusal):

1. The frame's bytes and SHA-256 equal §2.1.
2. PE-US is 2.18.0 installed from PyPI, every file matches its RECORD,
   and the RECORD's digest equals
   `9f9f090894638e3d0e0dd5ad8ab34f36cf8cb2134ef3627407d0653381906007`
   over 17,551 lines (`PE_US_RELEASE` in
   `scripts/pe_us_minimum_benefit_sample_households.py`, PR #496, which
   PR #506 reuses).
3. The baseline component arrays are identical in every child process.
4. For every person and component, the component a scenario's simulation
   calculates for 2026 equals the float32 of the input set (§3.2)
   exactly; components the scenario does not cut equal the baseline
   exactly, so under the OASI cut the disability component is unchanged.
5. Marital units have one or two members and lie within one household;
   every person belongs to exactly one household and one marital unit;
   countable resources are never negative; 2026 age equals frame age.
   The records whose four 2024 frame components are all positive number
   5,924, and for each of them the components, converted to float64 and
   divided by their sum, give `numpy.round(100 * share, 2)` equal to
   24.96, 37.93, 13.55 and 23.56 (retirement, survivors, dependents,
   disability).
6. For every row and cell with `W > 0`, the three labels' shares sum to
   one within 1e-12. Cells with `W = 0` keep undefined shares with their
   reason. Each one-way breakdown partitions its row's universe.
7. No output contains an absolute local path.

**Row validity.** These checks validate the machinery of rows R3 and R4
only. If either fails, R3 and R4 are reported as *invalid*, with the
check and the count of failing persons, and every other row stands:

- (a) The identity of §4.2 holds within $0.01 for every person in every
  scenario.
- (b) The Python version of the encoded resource test equals PE-US's
  `meets_ssi_resource_test` for every person whose pooled or own
  resources are not within $0.01 of the limit; persons within $0.01 are
  counted.

**Recorded, not refused:** the three-by-three transition tables (§5),
including any transition in which a label rises when the asset test is
added; the counts of over-replacing units and of units whose SSI falls;
and the SSI change outside the universe's marital units (§13).

## 11. Outputs

- `runs/pe_us_depletion_cut_population_v1.json` and its `.env.json`
  sidecar, created exclusively. The artifact begins with `header` (the
  five labels) and records `data_provenance: registered_real`, the
  publication block (§14), the registration pointer, the registered
  commit, PR #506's head at registration, this file's path, version,
  status and SHA-256, the frame pin, the PE-US installation and RECORD
  check, the Trustees citation, every statistic for every row, scenario
  and cell with *n*, *W*, the bootstrap interval and flags, the checks of
  §10, the diagnostics of §13, the named differences of §12, the Modal
  app, function-call and image IDs, the marker contents, timings and
  peak memory.
- `docs/analysis/pe_us_depletion_cut_population_20261001/`: a Markdown
  report and one chart (estimands 1 and 2 by cell for the headline row),
  PNG and SVG, each carrying the labels.
- A pin test, in the same local commit, fixes the registration URL, the
  registered commit, the artifact's SHA-256 and this file's SHA-256.
- Raw per-person arrays stay in the evidence folder, outside the
  repository.

## 12. Named differences, carried on every output

1. **Frame-relative.** Liquid assets are imputed (one draw per household,
   SCF 2022 or SIPP 2023 donors by Microcosm's code; the blend is not
   confirmed for this frame) and not calibrated; beneficiary counts and
   concurrent SS-SSI receipt are not calibrated.
2. **Asset placement.** Each household's assets sit on its
   lowest-`A_LINENO` person; other members hold none. Rows R3 and R4 are
   two alternative resource tests addressing this.
3. **No resource deeming in PE-US 2.18.0** (§4.1). Row R3 applies the
   spousal rule; the parent-to-child rule is not applied in any row.
4. **The fund of a dependent's benefit is unknown.** PE-US's single
   dependents component cannot separate dependents of disabled workers
   (DI) from dependents of retired workers (OASI), so the OASI cut
   reduces both.
5. **Synthetic splits.** 16.9 percent of beneficiaries (weighted) carry a
   synthetic fixed-proportion split across all four components (76.4
   percent of it in OASI components); row R5 excludes them.
6. **Marital and living-arrangement composition.** The frame's
   beneficiaries aged 62 and over are 85.6 percent married. Urban
   Institute tabulations of SSA's MINT model (MINTEX), published in
   2005/2006, project 60 percent of Social Security beneficiaries aged 62
   or older in 2022 to be married (Butrica, Cashin and Uccello, Social
   Security Bulletin 66(4), Table 1, row Married, column All, 2022).
   Widowed, divorced and never-married beneficiaries, and people living
   alone, are underrepresented in the frame. The all-beneficiary shares
   reflect this skew, and one-way breakdowns do not remove it: composition
   can also differ within age, sex, race and income cells.
7. **Model versions.** The weights were solved under PE-US 1.764.6; the
   data release declares compatibility with policyengine-us 2.0.0 (core
   3.32.5); policyengine.py certifies it for 2.2.1; the run uses 2.18.0
   (core 3.32.11).
8. **Year.** 2026 law, a 2024 frame extended by PE-US; asset inputs grow
   with CPI-U while the limits stay at $2,000 and $3,000.
9. **Take-up.** The headline assumes everyone eligible takes SSI up; row
   R2 uses the frame's take-up flags.
10. **Static.** No change in work, claiming, saving, asset spend-down or
    living arrangements.
11. **Age.** Top-coded at 80-84 and 85+. CPS does not collect a child's
    own Social Security income below age 15; beneficiaries under 15
    appear only as 25 synthetic PUF-support records, so the frame omits
    or misattributes child beneficiaries.
12. **The spousal-deeming cap.** When an ineligible spouse's income is
    deemed, 20 CFR 416.1163(e)(2) limits the benefit to the lesser of the
    deeming computation and the individual FBR less the person's own
    countable income. PE-US 2.18.0 caps it at the individual FBR only
    (`PEUS/variables/gov/ssa/ssi/ssi_if_takes_up.py:25-38`). A cut that
    ends deeming can therefore lower modeled SSI. Labels describe PE-US's
    modeled response, including this discrepancy.

## 13. Unscored diagnostics and context

Reported, not graded:

- Weighted totals for each scenario and each simulated variant (asset
  test as encoded, and no asset test; frame take-up for everything but
  `ssi_if_takes_up`): the cut, the change in federal SSI
  (`ssi_if_takes_up` and `ssi`), the change in all modeled state benefits
  (`household_state_benefits`), and the change in household net income
  (`household_net_income`), with PR #506's offset share, 1 − (net income
  change ÷ Social Security change). Totals run over beneficiary
  households: the distinct households holding a person in the scenario's
  universe, each weighted once. They do not cover rows R3 and R4, whose
  SSI is computed after the simulations.
- SSI that offsets a cut outside the beneficiary's marital unit: the
  beneficiary households' SSI change less the change in the distinct
  marital units holding a person in the universe, each unit counted once.
- Counts, unweighted and household-weighted, of distinct units with
  `dS_u > C_u + tau` and with `dS_u < -tau` (and the weighted SSI loss of
  the latter); the transition tables; the reason partition of §5.
- Context, unscored, read from the evidence folder's pinned copy:
  SSA's Monthly Statistical Snapshot, December 2024, Table 1 (in
  thousands; dual entitlement counted once; SSI includes federally
  administered state supplementation): 65,522 receiving Social Security
  only and 2,533 receiving both Social Security and SSI. The frame's
  weighted counts of beneficiaries and of beneficiaries receiving SSI
  (both `ssi_if_takes_up` and `ssi`, baseline, asset test as encoded) are
  reported beside them.

## 14. Rules

- **One shot.** No numerical threshold exists and none may be added.
- **No pre-run computation on the frame.** Nothing loads the frame
  through PolicyEngine-US outside the one shot. Container resources are
  set from the reader lane's disclosed smoke measurement (§16) and from a
  dry run of the registered entry point, at the registered commit, on an
  invented dataset with the frame's entity counts (57,240 households,
  166,321 persons). The second registration comment posts that dry run's
  timings and peak memory.
- **One disclosed re-execution** is allowed, only for an external
  infrastructure failure (for example a failed container or exhausted
  memory) before the `phase-statistics` marker (§15). It follows an
  issue #42 comment, and nobody reads the failed attempt's child outputs,
  which are deleted unread.
- **No tuning and no rerun otherwise.** A code or specification change is
  a new registered version and needs a new registration.
- **No-drop.** Every row, scenario, cell and statistic is computed and
  kept, including undefined or invalid values with their reason.
- **Refusal.** Failure of any check under §10's refusals ends
  Registration 19; a corrected version needs a new registration. Failure
  of a row-validity check invalidates only rows R3 and R4, as §10 says,
  and is not a refusal. The runner writes a refusal
  record (check number and name, the number of failing persons, the phase
  reached) with no §6 statistic and no per-person value, and that record
  is reported on issue #42 at once. If the refusal comes after the
  children have computed SSI outcomes, the next registration discloses
  that those outcomes were computed and discarded unwritten.
- **Publication.** The artifact, sidecar, report and chart are computed
  once and committed, unedited, in a local commit on the branch, whatever
  they show. Within 24 hours of the run, an issue #42 comment posts, with
  no statistic, the run's start and finish times, its exit status, and
  the SHA-256 of the artifact and the sidecar, so the bytes are fixed in
  public before anyone decides on release. Pushing that commit, opening
  or updating the pull request with it, posting the run-complete comment
  with numbers, and any outside use wait for Max's go on a cos decision
  filed when the run completes, without `--closes-with`. That decision
  governs timing, and the wording of the run-complete comment and outside
  communications, only. It never governs whether the numbers appear, and
  it cannot change the committed artifact, report or chart. Until the go,
  the issue #42 record shows the result as computed and not yet released.
  The artifact records
  `publication: {"computed_regardless": true, "release_held_for": "<decision id>", "release_scope": "timing and wording only"}`.

## 15. Topology and authorization

- **Code.** The registered commit descends from PR #506's head at
  registration, `363d9e81a8fa787c690085308d4f2e0602aed07a`. Before the
  second comment it is pushed to `PolicyEngine/microcosm-dynamics` on
  branch `pe-us-depletion-cut-population-20261001` and tagged with the
  annotated tag `registration-19-sa1`. Later changes to PR #506 do not
  change the registered run; the run-complete comment names any later
  change to the functions this run imports. Any merge carrying the
  registered commit uses a merge commit, never squash or rebase. Unlike
  Registrations 13-17, which ran at `master` commits, this commit is not
  on `master`.
- **Comments.** The first issue #42 comment fixes this specification: it
  restates the rows, statistics, cells and rules, and records the
  ratified file's path, commit and SHA-256. Its URL is the run's
  `--registration-pointer`. The code is built against this specification
  with invented data only, before or after the first comment, and never
  runs on the frame before the second; it pins this file's SHA-256. The second comment
  posts the registered commit's full SHA, the tag, the exact run command,
  a statement that this file is byte-identical to the SHA-256 the first
  comment recorded, the SHA-256 of the Modal runner script and both
  requirement files, the volume name, and the invented dry run's timings
  and peak memory. Immediately before the first comment, the drafter
  re-reads the last issue #42 comment; if 19 has been taken, the number
  in the labels, the block and the exposures file is changed first.
- **Entry point.** `scripts/run_pe_us_depletion_cut_population_registered.py`
  refuses: a registration pointer that is not an issue #42 comment URL; a
  commit that is not a full 40-character SHA or is not HEAD; a tree that
  is not clean; a specification whose status is not `ratified_frozen` or
  whose SHA-256 differs from the code's pin; and an output that already
  exists. In a freshly cloned container the last refusal cannot fire, so
  the volume marker below is the one-shot guard.
- **Real-frame guard.** The population code refuses to load any file
  whose SHA-256 is the frame's, and refuses a `Microsimulation` built
  without an explicit `dataset=` (PE-US 2.18.0 defaults to this frame:
  `PEUS/system.py:64, 444-450`), unless the registered entry point calls
  it after its preflight passes. Tests and CI use invented datasets only,
  and a test asserts that the guard refuses.
- **Platform.** Modal, workspace `policyengine`, following the runner of
  PR #506's regeneration
  (`EV/pe-us-depletion-cut-20261001/modal/regen_depletion_cut.py`). The
  runner lives in this analysis's evidence folder. The container rebuilds
  both interpreters from frozen requirements, bakes the frame from
  Hugging Face at the commit in §2.1 and checks its SHA-256, clones the
  repository, fetches the registered SHA, checks it out detached, and
  refuses unless HEAD equals the full SHA and the tag points to it. The
  function is declared `nonpreemptible=True` with `retries=0`, and the
  run is launched with `modal run --detach`. The installed Modal client
  retries a lost input on its own (`modal/_functions.py:456-489`), so the
  guard is a committed marker: before the entry point starts, the
  container refuses if `started` exists on the run's Modal volume, writes
  `started` with the registered SHA and the UTC time, and calls
  `volume.commit()`, so any automatic retry refuses. After every PE-US
  child has finished and before the first §6 statistic, the runner writes
  and commits `phase-statistics`. Each simulation runs in its own PE-US
  child process. The artifact and sidecar are created exclusively on the
  volume; the copy committed to the repository must equal the volume copy
  byte for byte.
- **Authorization.** Cos decision d806, ruled 2026-10-01T18:14, records
  Max's words in chat verbatim: "Max in chat 2026-10-01 (Claude session
  45a0ea0e): 'Register the analysis first, the way this repo registers
  tests: cells, population, the 22% OASI cut, and the 17% OASDI
  sensitivity.' 'Run the cut on a population that carries assets, through
  PolicyEngine-US.' 'Label results as frame-relative unless calibrated to
  national totals.' 'Open a PR, get an independent review, and keep
  published numbers behind Max's go (cos add-decision).' 'Run
  compute-heavy work on Modal.' Authorizes the #42 registration and the
  one-shot run; publication of numbers needs a separate go." Max's ruling
  fixes the population, the two cuts, the cell dimensions, the label
  rule, the platform, the independent review and the publication hold.
  Every other choice here is the orchestrating session's, made after the
  exposures of §16: the frame, the headline row and its SSI measure, rows
  R2-R5, the replacement measure and tolerance, the quintile concept, the
  bootstrap, the small-cell rule, and ratification by registration
  comment. The independent reviews are recorded in §20.
- **Evidence folder:** `EV/pe-us-depletion-cut-population-20261001/`,
  holding the reader reports (`understand/`) and scripts
  (`scratch-readers/`), the spec reviews (`spec-review/`), the exposure
  record of §16, and the pinned sources:
  - `sources/lii_416_1202.html`, SHA-256
    `18c1283e264db97d67fb7a38d2caa41262032957989d4b46bbc44774092fd6ef`;
  - `sources/lii_416_1205.html`, SHA-256
    `83192ca4293e48d653d9cb21e1a6625da18d23aea86c6d43a96393bc3e448833`;
  - `sources/ssa_stat_snapshot_2024-12.html` (Wayback capture
    20260606142730 of SSA's Monthly Statistical Snapshot, December 2024),
    SHA-256 `e488dce9bac3b1645813440acc73e7bd93e60e70a7e1ba4d902ed83f088b81d0`;
  - `sources/ssb_v66n4p1.html` (Wayback capture 20241214013530 of Social
    Security Bulletin 66(4)), SHA-256
    `c8671a359b71212219a0f5c8480c5eddadb2d5da1c2609af239319e8d0b230e2`;
  - `sources/lii_416_1163.html`, SHA-256
    `f3ba220819cd3b71d083b4f1e5c591c65cef4a9415da9164a362a2ef6ff16c2d`.

  `SHA256SUMS` in that folder fixes the reader reports, the reader
  scripts, the exposure record and the sources; the first comment records
  its SHA-256.

## 16. Disclosure

- **Not blind, and not fully register-first.** PR #506's illustrative
  results are visible on its open, unmerged pull request in this public
  repository (its merge decision, d775, is open). Before this
  specification was written, six reader lanes and a critic lane of the
  orchestrating session's understand workflow (Claude Code workflow
  agents, Opus 5.5, 2026-10-01) worked on this frame. They edited
  nothing. One (`scratch-readers/smoke.py`) ran a PolicyEngine-US 2.18.0
  microsimulation of the baseline, asset test as encoded and frame
  take-up, for 2024 and 2026, and computed SSI receipt and totals,
  `meets_ssi_resource_test`, `is_ssi_eligible` and ABD status. Others
  tabulated beneficiaries' countable assets against the $2,000 and $3,000
  limits on this frame and on five other candidate frames
  (`tab_frames.py`), take-up flags, CPS-reported SSI receipt and asset
  holding by marital status. These were real-data outcome computations,
  not explicitly authorized structural checks. They depart from the
  repository's register-first rule for post hoc analyses (P:76, adopted
  by d479: "Development checks use invented cases or explicitly
  authorized structural checks") and from Max's instruction to register
  first (d806; the departure is noted on that decision). The
  orchestrating session (Claude Code, Opus 5.5) read every value before
  choosing the frame, the headline row and its SSI measure, the universe,
  the replacement measure and rows R2-R5.
  `EV/pe-us-depletion-cut-population-20261001/exposures-before-registration.md`
  (SHA-256 recorded in the first comment) names every quantity, and
  `SHA256SUMS` fixes the lanes' reports and scripts. All are released
  with the results.
- **Review lanes.** The round-1 referees of `sa1-draft-1` (§20) were
  Claude Code workflow agents (Opus 5.5) and Subfleet lanes. Two of them
  read the exposure record and the reader reports. They computed nothing
  on the frame beyond structural counts; their live PE-US runs used
  invented households only.
- No statistic of §6 has been computed on the frame, for any row, before
  registration.
- No forecast is registered. d806 does not call for one, there is no
  comparator, and the orchestrating session's exposures would make its
  forecast uninformative.

## 17. Worked cases (invented)

PR #506's household A: one person aged 68, retired-worker benefit $743 a
month, $1,500 in the bank, renting for $800 a month, no other income,
Florida, 2026.

- 22 percent OASI cut: m = 743, p = floor(743 × 0.78) = 579, cut = 12 ×
  164 = $1,968 a year.
- Asset test as encoded: $1,500 ≤ $2,000, so the test passes; SSI rises
  from $3,252 to $5,220, by $1,968 (PR #506's results). Label full, with
  and without the asset test; not blocked.
- The same person with $50,000 in the bank: the test fails, SSI is zero
  before and after the cut, label none; without the asset test SSI rises
  by $1,968, label full. Blocked.
- The same person with $2,500 in stocks: the test fails ($2,500 >
  $2,000); blocked.
- A couple, both 70, the asset holder holding $2,500 and the spouse $0:
  a joint claim, so the encoded test sums to $2,500 ≤ $3,000 and passes.
  If the spouse were 64 and not disabled, the claim would not be joint:
  the encoded test compares the holder's $2,500 with $2,000 and fails,
  while R3 compares $2,500 with $3,000 and passes.
- A married ABD couple sharing a tax unit with an older parent, the
  husband holding $5,000: the parent and the husband are the tax unit's
  head and spouse, the couple is not a joint claim, and the encoded test
  fails the husband and passes the wife. With no asset test both spouses'
  SSI rises; with the encoded test only the wife's does. The couple's
  label moves from full to part: partly blocked under R0. Under R3 both
  are tested on $5,000 against $3,000 and fail: blocked.

## 18. Machine-readable block

`tests/bridge/test_depletion_cut_population_spec.py` holds this block to
the code's constants.

```json
{
  "specification": "pe_us_depletion_cut_population_ssi_asset_test",
  "version": "sa1-draft-4",
  "status": "draft",
  "decisions": {
    "authorization": {
      "decision": "d806",
      "ruled_at": "2026-10-01T18:14",
      "ruling": "Max in chat 2026-10-01 (Claude session 45a0ea0e): 'Register the analysis first, the way this repo registers tests: cells, population, the 22% OASI cut, and the 17% OASDI sensitivity.' 'Run the cut on a population that carries assets, through PolicyEngine-US.' 'Label results as frame-relative unless calibrated to national totals.' 'Open a PR, get an independent review, and keep published numbers behind Max's go (cos add-decision).' 'Run compute-heavy work on Modal.' Authorizes the #42 registration and the one-shot run; publication of numbers needs a separate go."
    }
  },
  "blocked_by": [],
  "frame": {
    "repo_id": "policyengine/populace-us",
    "repo_type": "dataset",
    "filename": "populace_us_2024.h5",
    "tag": "populace-us-2024-spm-20260909",
    "revision": "9a814a3b3b53c0ecd6e1737b6ec862c31300ef6f",
    "bytes": 826917837,
    "sha256": "6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84",
    "period": "2024"
  },
  "pr506_head": "363d9e81a8fa787c690085308d4f2e0602aed07a",
  "year": 2026,
  "policyengine_us": {
    "version": "2.18.0",
    "package_record_digest": "9f9f090894638e3d0e0dd5ad8ab34f36cf8cb2134ef3627407d0653381906007",
    "package_record_lines": 17551
  },
  "scenarios": {
    "oasi22": {"role": "primary", "payable_share_source": "trustees_citation OASI", "components": ["social_security_retirement", "social_security_survivors", "social_security_dependents"]},
    "oasdi17": {"role": "sensitivity", "payable_share_source": "trustees_citation OASDI", "components": ["social_security_retirement", "social_security_survivors", "social_security_dependents", "social_security_disability"]}
  },
  "variants": ["asset_test_as_encoded", "no_asset_test"],
  "replacement": {
    "unit": "marital_unit",
    "ssi_measure": "ssi_if_takes_up",
    "tolerance_dollars_per_year": 1.0
  },
  "headline": {"row": "R0", "scenario": "oasi22", "cell": "all", "statistics": ["F_test", "P_test", "N_test", "F_no", "P_no", "N_no", "R_test", "R_no", "B", "B_part", "B_cond"]},
  "rows": {
    "R0": {"field": null, "value": "encoded resource test; frame asset placement; ssi_if_takes_up; all beneficiaries"},
    "R2": {"field": "ssi_measure", "value": "ssi"},
    "R3": {"field": "resource_test", "value": "spousal_deeming_couple_limit"},
    "R4": {"field": "resource_test", "value": "household_pooling_couple_limit"},
    "R5": {"field": "universe", "value": "exclude_four_component_records"}
  },
  "cells": {
    "all": ["all"],
    "age": ["under_18", "18_61", "62_64", "65_69", "70_74", "75_79", "80_84", "85_plus"],
    "sex": ["female", "male"],
    "marital": ["married", "widowed", "divorced", "separated", "never_married"],
    "race": ["hispanic", "white", "black", "asian", "other"],
    "income_quintile": ["q1", "q2", "q3", "q4", "q5"],
    "income_quintile_pe_decile": ["negative", "q1", "q2", "q3", "q4", "q5"]
  },
  "uncertainty": {"method": "household_bootstrap", "replicates": 500, "seed": 20261001, "interval": [0.025, 0.975], "quantile_method": "linear"},
  "small_cell_n": 50,
  "small_cell_n_cond": 50,
  "acceptance": null,
  "forecast": null,
  "publication": {"computed_regardless": true, "release_scope": "timing and wording only"},
  "labels": [
    "FRAME-RELATIVE: Microcosm populace-us-2024 frame; liquid assets are imputed and not calibrated, and beneficiary counts are not calibrated to national totals.",
    "Applied to 2026 law and prices: the cut would not happen in 2026, and this is not a projection.",
    "Static: no behavioral response.",
    "Registered one-shot, not blind: registered after PR #506's illustrative results and after real-data diagnostics on this frame were seen (issue #42, Registration 19).",
    "Headline basis: potential federal SSI replacement, as if everyone eligible takes SSI up, under the row's modeled resource test; shares count cut beneficiaries by replacement of their marital unit's combined cut."
  ]
}
```

## 19. Changelog

- `sa1-draft-1` (2026-10-01): first draft.
- `sa1-draft-2` (2026-10-01): round-1 review fixes (§20). The synthetic
  splits are fixed unequal proportions, not quarters; partly blocked
  (`B_part`) added, because R0's labels can move from full to part; the
  checks of §10 split into refusals, row validity and records; 25 child
  beneficiaries under 15 disclosed; the SCF/SIPP blend marked unconfirmed
  for this frame; the secondary quintile's baseline fixed; the
  ratification protocol, publication rule, refusal rule, real-frame
  guard, Modal guards, registered-commit tag and full authorization
  quote added; the real-frame pre-run check dropped; disclosure
  itemized; sources pinned; meeting participants not named.
- `sa1-draft-3` (2026-10-02): methodology-review fixes (§20). `_law`
  renamed `_test`; `n_cond`, `W_cond` and a small-cell rule for `B_cond`
  added; the bootstrap fully specified, with undefined replicates omitted
  and counted; the none label states that it includes SSI decreases, and
  the spousal-deeming cap discrepancy is named difference 12; the reason
  partition limited to the eligibility basis; diagnostic aggregation
  defined; R5 stated as a reporting restriction; a fifth label states the
  headline's basis; R3 and R4 stated not to bound actual ownership.
- `sa1-draft-4` (2026-10-02): implementability-review fixes (§20). §14's
  refusal rule limited to §10's refusals; the partition check exempts
  cells with no weight; the baseline components come from a separate
  probe simulation; the cut check is exact per component, replacing a
  $0.05 tolerance that float32 rounding alone could exceed; the
  synthetic-split check given an exact rule; stale check references and
  the head and spouse rule corrected.

## 20. Review and ratification record

- **Round 1** on `sa1-draft-1` (2026-10-01), four referees with distinct
  lenses; reports in `EV/pe-us-depletion-cut-population-20261001/spec-review/`:
  - mechanisms and citations (Claude Code workflow agent, Opus 5.5):
    2 blocking, 3 major, 12 minor; all resolved in `sa1-draft-2`.
  - registration and process (Claude Code workflow agent, Opus 5.5):
    2 blocking, 8 major, 8 minor; all resolved in `sa1-draft-2`.
  - methodology (Subfleet lane, GPT-6.1 Sol; it read `sa1-draft-1`):
    5 blocking, 9 major, 2 minor. Six were already resolved in
    `sa1-draft-2`; the rest are resolved in `sa1-draft-3`.
  - implementability (Subfleet lane, GPT-6.1 Sol; live checks on
    invented data; it read `sa1-draft-3`): 2 blocking, 2 major, 3 minor,
    all resolved in `sa1-draft-4`. Its live checks confirmed that an
    invented frame-layout file loads, that `set_input` overrides the
    extended 2026 components, that age carries forward, the exact
    vectorized rounding and the release pin. The structural reform, the
    annual SSI sums, the household outputs and the identity did not finish
    on a loaded host; the code's oracle tests on invented data cover them
    and are recorded in the registered-commit review.
- **Ratification check:** to be recorded. The ratified file must differ
  from the last reviewed draft only in version, status, the block's
  version and status, the changelog and this section.
- **Registered-commit review:** to be recorded before the second comment.
- **Comment drafts:** each reviewed independently, with a values scan,
  before posting.
- **After the run:** an independent check of the artifact against this
  file before the local commit.
- **What the drafter read and did not verify.** The drafter (the
  orchestrating session) read the reader reports, the referee reports,
  the PE-US source files cited, the regulation pages, the SSA snapshot,
  the Social Security Bulletin table and PR #506's code and design note.
  It did not read Microcosm's build logs for the frame, so the asset
  donor blend and the origin of the fixed synthetic-split proportions
  are not verified.
