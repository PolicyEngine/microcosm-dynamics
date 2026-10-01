# A Social Security cut at depletion, through PolicyEngine-US

**ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA. Applied to 2026 law and prices;
not a projection.**

The second use of the PolicyEngine-US bridge (`docs/design/pe_us_bridge.md`,
PR #496). It asks what an across-the-board Social Security cut at trust fund
depletion does to a household once federal and state taxes and benefits
respond, and who pays the part that other programs offset.

Code: `src/populace_dynamics/bridge/depletion_cut.py` (pure Python) and
`scripts/pe_us_depletion_cut_sample_households.py`, which imports #496's
script for its reviewed pieces (the release pin, California's 2026 payment
standard, the low earner's benefit, the Medicaid valuation). Outputs:
`docs/analysis/pe_us_depletion_cut_20261001/`.

## The cut

The source is the 2026 Trustees Report, section II.A (Highlights), under
intermediate assumptions. The page and its fetch record are committed under
`docs/analysis/pe_us_depletion_cut_20261001/sources/`, byte-pinned by
`.gitattributes`; the full report (`tr2026.pdf`) and the statute pages are
not committed, and the JSON records their URLs, retrieval times and SHA-256.

- **The numbers come from the quotes.** `depletion_cut.depletion_quotes`
  finds the one sentence pair per fund on the page, and
  `parse_depletion_sentence` reads the depletion year and payable percent
  from it. The script requires Table II.A1 to state the same numbers, and
  each quote to appear once in the full report's text (page 12 of the
  extracted text). The quotes below straighten the page's curly
  apostrophes; the JSON keeps them as printed.
  - OASI: "The OASI Trust Fund is projected to become depleted in the fourth
    quarter of 2032, one quarter earlier than projected in last year's
    report. Upon reserve depletion in 2032, projected income is sufficient
    to pay 78 percent of scheduled benefits."
  - Combined OASDI: "The combined OASDI fund is projected to become depleted
    in the third quarter of 2034, the same quarter as in last year's report.
    Upon reserve depletion in 2034, projected income is sufficient to pay 83
    percent of scheduled benefits."
- **Primary and sensitivity.** "Retired workers, their families, and
  survivors of deceased workers receive monthly benefits under the Old-Age
  and Survivors Insurance (OASI) program" (the report's introduction), so
  the primary reform pays every benefit at 78 percent (a 22 percent cut).
  The sensitivity uses the 83 percent for the OASI and DI funds on a
  combined basis (a 17 percent cut).
- **The cut is an assumption.** The Trustees Report notes that at
  depletion "scheduled benefits could not be paid in full on a timely
  basis" and that "certain trust fund operations items are not well-defined
  under current law" (full-report text, page 53). An across-the-board cut
  at the payable share is this analysis's assumption.
- **Rounding** (`depletion_cut.ROUNDING_RULE`). Each beneficiary's payable
  monthly benefit is the scheduled 2026 monthly benefit (a whole dollar)
  times the payable share, rounded down to a whole dollar, as 42 USC 415(g)
  rounds a monthly benefit computed under section 402. 415(g) itself rounds
  once, so a share applied to the unrounded amount could pay a dollar a
  month more (for D and E at 78 percent it would); applying it to the
  whole-dollar benefit is this analysis's choice. A couple's benefits are
  each cut and rounded on their own. Annual amounts are twelve times
  monthly. The product is exact (`fractions.Fraction`).
- **2026 law.** The cut is applied to 2026 benefits and run through
  PolicyEngine-US for 2026. It would not happen in 2026. The point is how
  much of a cut of that size households absorb, and how much other programs
  and taxes offset, under current law.

## Households

Each household is run in California, Montana and Florida with #496's common
facts: $800 monthly rent, $1,500 in the bank, heating or cooling costs, food
preparation allowed, housing-voucher take-up off.

| Household | Social Security (monthly, scheduled) | Other income |
|---|---|---|
| A, B, C | #496's low earner: $743 | none; $4,800 pension; $31,200 pension |
| D | a medium earner: $2,351 | $31,200 pension (C's) |
| E | that medium earner, $2,351, and a spouse, $1,175 | $42,000 pension |

- **A-C** are #496's households at #496's current-law benefit: the script
  calls #496's `worker_benefits` unchanged and keeps its current-law part.
  The artifact and oracle tests check it against #496's committed JSON.
- **D** has covered earnings of 100 percent of the national average wage
  index in each of the 35 years 1980-2014, born in 1954 and entitled in 2020
  at full retirement age (66), so the claim factor is 1. The script follows
  #496's steps: `coverage.count_coverage_years`, `rules.history_pia` on the
  old-age basis (AIME $3,873, PIA $1,735.80 at the 2016 bend points), the
  statutory COLAs to 2026 (`bridge.carry_pia_forward`, $2,351.50) and the
  floor to the dollar. Its pension is household C's; C and D also differ
  in age (68 and 72) and Medicare quarters of coverage (88 and 140). Part
  of D's benefit is taxable before and after the cut.
- **E** adds a spouse a year older with no covered earnings, entitled to a
  spouse's benefit in 2020, after full retirement age, so it is not reduced
  for age. The benefit comes from the Track B gross-benefit layer
  (`track_b.gross_benefits.household_benefits`): one-half of the PIA rounded
  down to a dime ($1,175.70), the family maximum of 42 USC 403(a) ($4,294.80,
  not binding), and the floor to the dollar. The script requires Track B's
  worker benefit and PIA to equal D's, a differential check of the COLA
  carry-forward and the rounding (both start from the same PIA at
  eligibility), and every benefit month paid in 2026 to agree. The spouse's
  benefit enters PolicyEngine-US as `social_security_dependents`. In
  policyengine-us 2.18.0 it and `social_security_retirement` are inputs
  that `social_security` adds (`social_security.py:11-14`); outside that
  sum they differ only in child-care and CalWORKs income lists and Idaho's
  retirement-benefits deduction (`id_retirement_benefits_deduction.py:26`),
  none of which reaches a household without children in California,
  Montana or Florida. The spouse's Medicare quarters are left at
  PolicyEngine-US's default of 40 (`medicare_quarters_of_coverage.py:16`).
  PolicyEngine-US makes the older adult the tax-unit head
  (`is_tax_unit_head.py:10-15`), here the spouse; the couple files jointly
  (`filing_status.py:26-39`). The couple's pension is $42,000 so that part
  of their benefits is taxable and they owe federal income tax before and
  after the cut.

## Who pays the offset

The bridge splits the change in `household_net_income` into leaves that sum
exactly, in cents, to the net change. `depletion_cut.LEAF_LEVELS` assigns
each reviewed leaf to one level, and every other leaf is market income or
"unattributed". The script refuses a run in which a market-income or
unattributed leaf changes, so the offset is always the sum of three payer
groups:

- **Federal:** federal income tax and refundable credits; SSI ("there are
  authorized to be appropriated sums sufficient to carry out this
  subchapter", 42 USC 1381); SNAP ("Benefits issued and used as provided in
  this chapter shall be redeemable at face value by the Secretary through
  the facilities of the Treasury of the United States", 7 USC 2013(a)(1);
  the State cost share of 2013(a)(2)(B) begins in fiscal year 2028 at the
  earliest).
- **State:** state income tax and refundable credits; California's SSI state
  supplementary payment. 42 USC 1382e(a) describes a supplement as "cash
  payments which are made by a State" "in supplementation of such
  benefits"; where the Commissioner makes the payments on a State's behalf,
  the State "shall ... pay to the Commissioner of Social Security an amount
  equal to the expenditures made by the Commissioner of Social Security as
  such supplementary payments" (1382e(d)(1)). PolicyEngine-US lists it
  among "benefits paid by state agencies"
  (`parameters/gov/household/household_state_benefits.yaml:1,42`).
- **Joint:** Medicaid and the Medicare Savings Programs, in the health
  sensitivity only. PolicyEngine-US splits Medicaid by the federal medical
  assistance percentage (`medicaid_federal_cost.py`,
  `medicaid_federal_share.py`), and the Medicare Savings Programs by it for
  QMB and SLMB but at 100 percent for QI (`msp_federal_cost.py:35-47`). The
  script refuses a changed Medicare Savings Program value whose federal
  share is 100 percent, and the JSON's memo lines carry the federal
  costs.

The statute pages are the Legal Information Institute's, retrieved
2026-10-01; the script checks each quoted phrase against the saved page and
its recorded SHA-256.

The offset share is `1 - net change / Social Security change`; the payer
groups' shares sum to it exactly (`fractions.Fraction`). The script also
checks `LEAF_LEVELS` against the bridge's own display categories
(`category_for`, which names Social Security, SSI, SNAP and the income
taxes and places state benefits, state refundable credits and health by
their position in the tree): each group's change must equal its
categories' (federal: SSI, SNAP, federal income tax and credits; state:
state benefits, state income tax and credits; joint: health).

## Invariants

Hypothesis properties (`tests/bridge/test_depletion_cut.py`):

- a zero cut (a payable share of 1) changes no benefit, and identical runs
  decompose to zero changes with no offset share;
- the cut is the cut share times the benefit within the rounding: at least
  that, and less than $1 a month more;
- a deeper cut never leaves more Social Security, for one benefit or a
  household;
- the decomposition's components sum exactly to the net change;
- the levels partition the components (baseline, reform and change);
- the offset share is `1 - net / cut` exactly, and the levels' shares sum to
  it;
- any depletion sentence parses back to its fund, quarter, year and percent.

The script checks every comparison before writing (raising, never
asserting): the identities above, Social Security falling by exactly the
computed cut, no change outside the payer groups, no means-tested benefit or
refundable credit falling and no income tax rising when Social Security
falls, PolicyEngine-US's own net-income change within a cent of the
definition's sum, the float32 guard of #496, the payer groups against the
display categories, no all-federal (QI) Medicare Savings Program value
labelled joint, and Medicaid at cost a whole number of enrollees at the
release's ratio. Every with-health difference must match the one described
pattern: Medicaid starting, for a household of one, as countable income
for the state's optional aged pathway falls to its limit
(`is_optional_senior_or_disabled_income_eligible.py:22-32`: income at or
under the limit qualifies). Where SSI also begins in a state whose SSI
recipients get Medicaid in PolicyEngine-US
(`is_ssi_recipient_for_medicaid.py:20-34`; Montana is covered and
classified section 1634), the text names that route too.

Tests:

- `tests/bridge/test_depletion_cut.py` (unit): the module.
- `tests/bridge/test_pe_us_depletion_cut_script.py` (unit): the script's
  checks on invented inputs, with the tracer replaced by a fake, and the
  Trustees and statute checks on the committed and tampered sources.
- `tests/bridge/test_pe_us_depletion_cut_artifact.py` (unit): the committed
  JSON, Markdown and charts: labels, citation, identities, the cross-check
  against #496's committed benefit, a fresh run from clean code.
- `tests/bridge/test_pe_us_depletion_cut_oracle.py` (oracle tier): the
  benefit derivations live, a zero cut, SSI offsetting household A's cut
  dollar for dollar, and taxes offsetting part of household D's.

## How to run

```sh
POPULACE_DYNAMICS_PE_US_PYTHON=~/.venvs/policyengine-us-2.18.0/bin/python \
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
    scripts/pe_us_depletion_cut_sample_households.py
```

It runs 90 cases (five households, three states, baseline and two cuts, with
and without health coverage) and traces them. It needs the full report's
extracted text and the statute pages (`--full-report-text`, `--law-dir`),
which stay outside the repository, and keeps PolicyEngine-US's raw outputs
outside it too (`--raw`). `--reuse-raw` rereads them for development only;
the JSON records it, and the artifact test requires a fresh run.

## Caveats

- Illustrative households, not survey data: two invented workers in five
  living situations. They show mechanisms, not how many beneficiaries are in
  each situation.
- 2026 law and prices, not a projection. Some rules already in law differ
  by the depletion date (the SNAP State cost share, for one). The Trustees
  Report notes that the senior deduction is temporary; this analysis applies
  it as 2026 law does.
- No behavioral response; PolicyEngine-US's default take-up (full for SSI,
  SNAP and Medicaid).
- Part of the federal income tax on benefits is credited to the trust funds;
  it is grouped as federal here.
- Health coverage is outside default net income; the with-health figures
  value Medicaid at average program cost, as #496 does.
