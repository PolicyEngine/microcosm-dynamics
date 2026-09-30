# Track B G: the gross-benefit layer

**Status: build-only, 2026-09-29; review fixes 2026-09-30. No real-data
computation.** Inputs are invented families and SSA's published worked
examples.

The Track B design lives outside this repository, at
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`
(revision 3, SHA-256 prefix `6fd6f4aa5a83da80`). Its §3.1 row G asks for "family
maximum, age and dual-entitlement reductions, monthly family payment;
unsupported family configurations flagged", verified by "statutory worked
examples, Python reference cases, and an Axiom differential where a pinned
rule exists". §3.2 gives G the verification class **statutory conformance**
and admits "gross benefits for supported family configurations only". Max's
ruling d515 (2026-09-28) adopted §10 question 9's default: a Python reference
now, with Axiom differentials as diagnostics once a pinned rule exists.

- Code: `src/populace_dynamics/track_b/gross_benefits.py`.
- Tests:
  - `tests/test_track_b_gross_benefits.py` covers the worked examples,
    boundaries, households, the 403(a)(5) guard and refusals.
  - `tests/test_track_b_gross_benefits_properties.py` holds the Hypothesis
    invariants and the differentials against `ss/benefits.py` and the sealed
    ledger's rounding.
  - `tests/test_track_b_gross_benefits_oracle.py` checks the policyengine-us
    bundle (skipped without a checkout).
- Sources: `tests/data/track_b/gross_benefit_sources/`. The manifest pins each
  URL, UTC retrieval time, byte count and SHA-256.

## What it computes, in statutory order

For one worker's record and one benefit month:

1. **Family maximum.**
   - Retirement and survivor records use 403(a)(1)-(2). The three bend points
     are $230, $332 and $433 times NAWI(year - 2) / NAWI(1977), rounded to the
     nearest dollar with 50-cent ties up (215(a)(1)(B)(iii)).
   - The rates are 150, 272, 134 and 175 percent of the PIA for the year of
     first eligibility, before COLAs (RS 00615.736A.1). The total is floored to
     the dime.
   - Disability records use 403(a)(6) when initial DIB entitlement came after
     June 1980 (RS 00615.740-.742). The maximum is min(max(85% AIME, PIA),
     150% PIA).
   - 403(a)(6) itself states no rounding. The disability maximum is floored to
     the dime; the source is below, under "Disability-maximum rounding".
   - COLAs then raise the PIA and the maximum alike, dime-floored after each
     increase (215(i)(2)(A)(ii)).
2. **Original benefits (OB).**
   - Spouse 1/2; child 1/2, or 3/4 after the worker's death; widow(er) 100
     percent; mother or father 3/4. Each OB is dime-floored.
   - A widow(er)'s OB uses the PIA as determined under 202(e)(2)(B)-(C): the
     windexed PIA, or the PIA deemed equal to the deceased's credit-increased
     benefit.
3. **Reduction for the maximum** (403(a)(4); RS 00615.756).
   - Each OB is scaled by available / total OB and dime-floored. No share can
     exceed its OB.
   - In a life case the worker's PIA is deducted from the maximum first. The
     deduction is the PIA, never the credit-increased benefit (RS 00615.695).
   - Divorced spouses and surviving divorced spouses are paid outside the
     maximum. Everyone else is computed as if they were not entitled
     (403(a)(3)(C); RS 00615.680-.682).
4. **Dual-entitlement redistribution** (RS 00615.768, the Parisi rule).
   - This applies to benefits payable for October 1999 or later.
   - Other auxiliaries are reduced only by what a dually entitled beneficiary
     is actually paid before age reduction. The rest of the maximum is
     redistributed to them, capped at each OB.
   - If every beneficiary subject to the maximum is dually entitled, the rule
     is disregarded.
5. **Age reductions after the maximum** (RS 00615.210, .754A.1, .301B.1.c).
   - Spouse: exact 1/144 per month for 36 months, then 1/240 per month,
     dime-floored (RS 00615.201).
   - Widow(er): the 28.5 percent maximum spread over the reduction period, with
     the reduction amount rounded *up* to the dime (RS 00615.301).
   - The RIB-LIM applies next (402(e)(2)(D); RS 00615.320).
6. **Dual entitlement** (402(k)(3)(A)). The auxiliary benefit is reduced, but
   not below zero, by the own benefit after 402(q).
   - An aged spouse entitled to the own benefit in or before the spouse
     benefit's first month uses method C (402(q)(3)(B)/(C); RS 00615.250).
     Only the excess over the own PIA takes the spouse reduction. Delayed
     credits on the own RIB follow RS 00615.694.
   - A spouse entitled first, with the RIB later, uses method B
     (RS 00615.240). The spouse benefit keeps its 402(q)(1) reduction and is
     paid in excess of the RIB.
   - The caller must say which came first (`own_benefit_first`) for every
     dually entitled spouse or divorced spouse. There is no default: in the
     RS 00615.240 example the two methods pay $250.00 and $262.50.
   - Widow(er)s use method B: both benefits are reduced independently
     (402(q)(3)(E); RS 00615.020A.3).
   - A spouse with a child in care is never reduced for age (402(q)(5)(A)(ii))
     and is paid the excess over the reduced RIB (RS 00615.020A.3 note).
   - A spouse is not entitled when the own PIA is at least half the worker's
     PIA (202(b)(1)(D)).
   - A widow(er) is not entitled when the own RIB is at least the deemed PIA
     (202(e)(1)(D)).
   - A mother or father is not entitled when the own RIB is at least 3/4 of
     the PIA (202(g)(1)(C)).
7. **Monthly family payment.** Amounts stay exact dime multiples. 215(g) rounds
   each monthly benefit down to a dollar. "Gross" means before 203(b)
   earnings-test deductions and the 1840(a)(1) Medicare premium.

All arithmetic uses exact fractions: SSA's instruction is that decimal
equivalents "often" give an answer 10 cents lower (RS 00615.005B). Statutory
rates are cross-checked against the repository's policyengine-us bundle and
then used as exact fractions. NAWI, full retirement ages and the 402(w)
credit schedule come from that bundle.

## Why G reimplements the worker and auxiliary arithmetic

Design §6 suggests reusing the existing worker and auxiliary primitives in
`ss/benefits.py`. G does not: it recomputes the 402(q) reductions, the
402(w) credits and the auxiliary shares in exact fractions. The reasons:

- **POMS requires exact computation.** RS 00615.005B tells SSA staff to use
  the fraction, not its decimal equivalent, because the decimal "often"
  lands 10 cents lower. `ss/benefits.py` works in floats over
  policyengine-us's stored decimals (`0.00555556` for 5/9 of 1 percent).
- **The float path lands a dime low in 3.46 percent of cells.**
  `test_float_ledger_dime_errors_counted_exhaustively` covers every PIA
  from $0.10 to $557.20 by dime with 1-60 reduction months: 334,320 cells.
  `floor_to_dime` over `early_reduction` lands a dime low in 11,572 of
  them and never high. POMS's own $802.80 example is one of the low cells.
- **The float delayed credit is short for births 1917-1942.**
  `ss.benefits.delayed_credit` caps the window at 48 months (issue #494,
  below).
- **Its survivor path has one reduction period per parameter bundle.** The
  default spreads the widow(er) reduction over 84 months, exact only for
  survivors born 1962 or later (`ss/params.py`). G takes each widow(er)'s
  period as an input, and `widow_reduction_period_months` implements the
  RS 00615.301B.2 birth-date table.

The differential tests keep the two aligned where they overlap. The
reduction fractions, `spousal_benefit`, `widow_benefit` and
`delayed_credit` must agree with G within their documented rounding, and a
change to either side that breaks the agreement fails the suite. That is
invariant 10 below. The one pinned divergence is `delayed_credit` past 48
months for births 1917-1942, which is the oracle's bug (#494). This
reimplementation needs Max's ratification, because §6 asked for reuse.

## Delayed credits

402(w)(2)(A) counts increment months from the month of attaining full
retirement age to the month before attaining 70. So a cohort can earn at
most `840 - FRA` months.

- The window is 60 months for births 1917-1937 (FRA 65), and 58 down to 50
  months for 1938-1942. It is 48 for 1943-1954, 46 down to 38 for
  1955-1959, and 36 from 1960.
- `test_delayed_credit_window_matches_the_poms_chart_for_every_cohort`
  reads the RS 00615.692E chart from its capture. For every birth year from
  1917 to 1960 it checks the FRA, the monthly rate, the window, and that G
  accepts the whole window and rejects one month more.
- More months than the window is `InvalidFamilyInput`, wherever the months
  enter: `worker_age_adjusted`, an `OwnBenefit`, a `WorkerRecord` (checked by
  `record_state`), or a `RecordState` given directly (checked by
  `family_benefits`).
- The bundle's `max_delayed_months` (policyengine-us `max_delayed_years: 4`,
  so 48) is not used. It is short for births 1917-1942, and the FRA-to-70
  window bounds every later cohort anyway. `ss.benefits.delayed_credit`
  still applies it (issue #494).
- Credits for births before 1917 are refused
  (`delayed_credits_born_before_1917`). 402(w)(6)(A) gives 1/12 of 1 percent a month to a person first eligible
  before 1979. The bundle, like policyengine-us, starts its schedule at 3
  percent a year. RS 00615.692E also shows windows past 60 months for
  births before 01/02/1914. Retired workers on in-scope records are
  unaffected, because eligibility from 1983 implies a birth after 1917. A
  spouse's own RIB can reach the refusal.
- Birth years follow SSA's bands, which run from January 2 to January 1. A
  person born on January 1 takes the previous year.

## Disability-maximum rounding

403(a)(6) states no rounding for the disability maximum. G floors it to the
dime on two sources, both in the Social Security Bulletin 75(3) capture:

- the rules paragraph: "The final amount is rounded to the next lowest ten
  cents";
- the Table 2 note: amounts "would actually be rounded down to the nearest
  dime".

After that, 215(i)(2)(A)(ii) floors every COLA increase of the maximum to the
dime. The captured POMS sections on the disability maximum (RS 00615.740 and
.742) say nothing about rounding. Both quotes are pinned by
`test_worked_example_figures_are_quoted_from_the_captures`. The Bulletin is
an SSA research publication, not a program instruction, so resting the
rounding on it needs Max's acceptance.

## Households and the entry point

A family that draws on more than one record cannot be computed one record at
a time. `household_benefits` is the only integration entry point. It takes
every record in a household and runs `check_household_records` first. The
check does three things:

- A child entitled on two or more records raises `combined_family_maximum`,
  because 403(a)(3)(A) may combine the maximums (RS 00615.770).
- Anyone else entitled as an auxiliary or survivor on two or more records
  raises `multiple_auxiliary_records` (RS 00615.768A).
- A living worker who is also an auxiliary on another record must declare
  that record's RIB or DIB as `own_benefit`. The check compares kind, PIA,
  reduction months and credits. A mismatch, a worker with two records, or a
  deceased worker entered as a beneficiary raises `InvalidFamilyInput`.

`family_benefits` computes a single record only when the caller passes
`standalone=True`. That is the caller's statement that no beneficiary is
entitled on another record, and that a worker who is an auxiliary elsewhere
has declared that benefit. It is meant for SSA's single-record examples and
tests. Without it the call is a `TypeError`, and `standalone=False` is a
`ValueError` that names `household_benefits`. So "never default to
single-worker cases" holds at the API: a one-record computation happens only
by declaration.

Input errors are raised before any coverage refusal, in the household and
in every record's family. Input errors include:

- delayed-credit months past 70;
- a missing entitlement order;
- a payment month before the record's eligibility year or first DIB
  entitlement;
- a duplicate beneficiary id;
- a role the record cannot have.

This ordering means `evaluate_family` can never count an invalid row as a
coverage gap. `InvalidFamilyInput` propagates out of `evaluate_family` by
design. The aggregate stops, with no outcome to drop or half-count, and a
household with one bad record returns nothing at all.

## 403(a)(5)

The statute (captured in `ssa_act_203`) applies when two or more persons are
entitled for a month, the maximum applies to their benefits, and the PIA is
increased for the following month. That month's total is then treated as
increased by the smallest amount that keeps the total "for any such
subsequent month" from falling below it. Both totals are after 403(a) and
402(q). The guarantee is not limited to the next month. RS 00615.801B.2
adds that a saving clause, once established, "will continue in effect
until the table or formula maximum becomes larger", and may become payable
again.

G computes one month and does not compute the raise. It refuses instead.
`SavingsClauseGuard` carries the protection across one record's months:

- **It protects the total of a qualifying month.** A qualifying month has
  two or more persons entitled, a binding maximum, and a higher PIA the next
  month. The highest protected total is carried forward. RS 00630.400
  states SSA's version of this condition as "Benefits for that month are
  reduced for the MAX" (its 1972 Family Payment Saving Clause).
- **It refuses any later month whose total falls below the protected total**
  (`savings_clause_403a5`), whether or not the PIA rose into it. It also
  refuses every later month after that one, because the clause stays in
  effect.
- **It refuses every later month once a protected total may exist that G
  cannot see** (`savings_clause_history_unknown`). That covers:
  - a path that does not start at the record's first month of entitlement;
  - a month G refused for another reason while a protected total was in
    force;
  - a refused month followed by a PIA increase, or given without its PIA.
- **It computes a month in which nobody is subject to the maximum.**
  403(a)(4) decreases only benefits other than the worker's own, so there is
  nothing to raise. Such a month's total still counts. If it is below the
  protected total, the clause takes effect for later months.

Each refused month is a `FamilyOutcome` with its reason, so it stays in every
denominator. The review's counterexample is the unit test
`test_savings_clause_protects_every_later_month_not_just_the_next`:

1. November: $1,000 PIA and two children at $250, total $1,500.00.
2. December: a 2.5 percent COLA. PIA $1,025.00, maximum $1,537.50, children
   at $256.20, total $1,537.40.
3. January: no PIA increase. An aged spouse reduced for 60 months joins.
   Children at $170.80 and the spouse at $111.00, total $1,477.60.

A check of consecutive months alone passes both pairs. The guard refuses
January and every month after it. Two property tests restate the contract
independently:

- `test_savings_clause_guard_along_month_paths` runs random paths of COLAs,
  arrivals and departures.
- `test_a_reduced_joiner_after_a_cola_is_refused_iff_the_total_falls`
  generalizes the counterexample.

With the statutory maximum, a COLA alone never trips the guard for families
that are not dually entitled; a property test asserts this. A COLA raises
the maximum by at least as many dimes as the PIA, so the room left for
auxiliaries never shrinks.

**Known over-refusals.** Each is conservative and inflates the unsupported
rate:

- **A beneficiary who leaves, for example in the COLA month.** In
  `test_known_over_refusal_a_beneficiary_leaves_in_a_cola_month`, two of
  three children leave in December and the total falls from $1,750.00 to
  $1,537.50. G refuses December. No captured source says whether a change of
  membership triggers the clause.
- **A month in which the maximum does not bind.** 403(a)(4) only decreases
  benefits, so on the statute's text a larger maximum changes nothing there.
  But SSA's procedure in RS 00630.400 divides the protected payment among
  the auxiliaries without mentioning the OB cap.
- **Every month after a refused month** while a protected total is in force.
- **Every month of a path with unknown history.** A simulation that starts
  with families already on the rolls must either reconstruct each record
  from its first month of entitlement or accept these refusals.

RS 00630.400's summary also requires "at least one beneficiary is reduced for
age". G does not require it, which can only add refusals.

## Supported and refused configurations

| Record | Supported beneficiaries |
| --- | --- |
| Retirement (living worker on RIB, with any reduction or credits) | Aged spouse, spouse with child in care, divorced spouse, child |
| Disability (worker on DIB, entitled after June 1980) | The same |
| Survivor | Aged widow(er), surviving divorced spouse, mother or father, child |

Every configuration outside this table raises
`FamilyConfigurationUnsupported` (code `FAMILY_CONFIG_UNSUPPORTED`, design §7).
It never falls back to a single-worker computation.

| Reason | Trigger |
| --- | --- |
| `eligibility_before_1983` | Pre-June-1982 maximums rounded up (RS 00615.736B.3); pre-1979 table maximums |
| `payment_month_before_1983` | Months outside the post-May-1982 rounding rules |
| `di_entitlement_before_july_1980` | The pre-1980 disability maximum |
| `combined_family_maximum` | A child entitled on another record (403(a)(3)(A)), declared or found by the household check |
| `multiple_auxiliary_records` | Anyone else entitled as an auxiliary or survivor on two records (household check) |
| `deemed_or_putative_spouse` | 403(a)(3)(D) |
| `parent_benefit` | 402(h) |
| `disabled_widow_under_60` | Disabled widow(er)'s benefits before 60 |
| `dib_guarantee_pia` | RS 00615.736B.2, .738 |
| `dib_after_reduced_rib` | 402(q)(2) |
| `workers_compensation_offset` | Section 224 |
| `government_pension_offset` | 202(k)(5) |
| `administrative_finality` | Protected rates (RS 00615.754A.3) |
| `dual_entitlement_sequence` | A spouse's DIB after the spouse benefit (RS 00615.260), a widow(er) with DIB, a widow(er) born before 1929 (RS 00615.020B method D) |
| `parisi_redistribution_ambiguous` | The "payable before any age reduction" amount has two readings |
| `parisi_before_october_1999` | A binding maximum with dual entitlement before 10/99 |
| `independently_entitled_divorced_spouse` | A divorced spouse whose living ex-spouse is not entitled (402(b)(4)(A), (c)(4)(A)) |
| `non_aime_formula_pia` | Old-start, special-minimum and frozen-minimum PIAs (RS 00615.740B.1) |
| `savings_clause_403a5` | A month whose total fell below a 403(a)(5) protected total, and every month after it |
| `savings_clause_history_unknown` | A month for which a protected total G cannot see may exist (a path not started at entitlement, or a month G did not compute) |
| `delayed_credits_born_before_1917` | Delayed credits for births before 1917 (402(w)(6)(A)'s 1/12 of 1 percent) |

`evaluate_family` and `count_family_outcomes` keep unsupported rows, whether
single records or households, in every denominator by reason and weight.
`weighted_record_total` and `weighted_mean_record_total` raise
`FamilyTargetBlocked` rather than drop them. Invalid inputs raise
`InvalidFamilyInput`. They are errors, not coverage gaps, and are never
absorbed as unsupported rows.

## Invariants (all executed as tests)

1. **The family maximum binds only where the statute says it does.** The
   worker's PIA plus every amount subject to the maximum never exceeds it.
   Only the worker's own delayed credits (RS 00615.695) and divorced
   beneficiaries (403(a)(3)(C)) fall outside. The worker's benefit never
   depends on the auxiliaries.
2. **Shares stay proportional.** Each share lies within one dime below OB x
   available / total OB. After a redistribution, the shares of beneficiaries
   who are not dually entitled are proportional to the pool and are never
   below their standard shares.
3. **Raising the PIA never lowers the family maximum.** This holds for the
   retirement/survivor formula and after COLAs, and for the disability maximum
   in both the PIA and the AIME. That maximum stays between the PIA and 150
   percent of the PIA.
4. **Adding an auxiliary who is not dually entitled never raises another
   beneficiary's rate, payment or total.** Adding a divorced beneficiary
   changes nothing for anyone else.
   - *Intended violation:* adding a dually entitled auxiliary can raise
     another's benefit under RS 00615.768E. The minimized counterexample is
     pinned as intended.
5. **Dual entitlement never leaves a person below their own benefit.** The
   auxiliary amount is never negative, and the person receives the larger of
   the own benefit and the age-adjusted auxiliary benefit.
6. **Unsupported configurations always raise**, including when injected
   anywhere in a valid family or shared between two records of a household,
   and the denominators always keep them. **Invalid inputs are never
   absorbed as refusals.** Delayed credits past 70, a record date after the
   payment month, or a duplicate id always raise `InvalidFamilyInput`, even
   with a refused beneficiary or record condition in the same family.
7. **Households are their records.** A household of unrelated records gives
   each record's own result, and its total is their sum.
8. **Results are deterministic and independent of beneficiary order.** Every
   amount is a dime multiple, and each whole-dollar payment is the floor of its
   amount.
9. **403(a)(5).** Along any month path that starts at entitlement:
   - an admitted month with anyone under the maximum is never below an
     earlier protected total, and never follows such a fall;
   - a refused month has someone under the maximum and a fall behind it;
   - a month with nobody under the maximum is always computed;
   - a path whose PIA never rises is never refused.
10. **Differentials.** The reduction fractions, `spousal_benefit`,
   `widow_benefit` and `delayed_credit` in `ss/benefits.py` agree with G
   within their documented rounding. `delayed_credit` is compared only
   within its 48-month cap. Past it, for births 1917-1942, the divergence
   is pinned as the oracle's bug (#494). The sealed ledger's float path
   (`estimates.ledgers.floor_to_dime` over `early_reduction`) is never above
   G's exact amount, and never more than a dime below it.
11. **Delayed-credit windows.** For every cohort 1917-1960 on the RS
    00615.692E chart, the window is `840 - FRA` and the rate is the chart's.
    G accepts the whole window and rejects one month more.

## Worked examples reproduced exactly

| Source | Case |
| --- | --- |
| RS 00615.756 | $138.00 and $103.50 each, with 7 children (FMAX $862.60); the windexed widow and child, $260.70 / $189.20 |
| RS 00615.710 | Widow DRCs share the maximum: $404.20 / $295.70 |
| RS 00615.682 | $101.90 each; then the surviving divorced spouse at $145.70, outside the maximum, and children capped at $152.90 |
| RS 00615.768 | Examples 1 and 2 (the Parisi rule): $125.00 each; $30 / $270 |
| RS 00615.320 | RIB-LIM $350, with the $309.20 floor |
| RS 00615.240 | Spouse then RIB (method B): $450.00 spouse, $200.00 RIB, $250.00 paid as a spouse |
| RS 00615.694 | Spouse payment $290 after delayed credits on the own RIB |
| RS 00615.005, .101, .201, .301, .692 | $780.50 (not $780.40); every chart fraction; $819.60; $1,175; every RS 00615.692E cohort's maximum delayed-credit months |
| RS 00615.736 | Unrounded $659.02 / $647.89 / $625.23 / $759.238, and the pre-1982 round-up that is refused |
| RS 00605.900, .910 | All bend points and chart constants, 1979-2026 |
| OACT family maximum | 2026 bend points from NAWI(2024) |
| SSB 75(3) | Tables 1, 2, A-1, A-2 (dollar presentation rounding); A-2 also as a two-record household ($1,900) |

## Findings recorded along the way

- **Source erratum.** RS 00605.910 prints `899.52` for 1981's third constant.
  The statute gives `889.52`, and RS 00615.736's 1981 example agrees with the
  statute. The test pins both figures.
- **The sealed ledger's float path lands a dime low about 3.5 percent of the
  time.** `ss.benefits.early_reduction` uses policyengine-us's decimals
  `0.00555556` and `0.00416667`. `estimates.ledgers.floor_to_dime` applied to
  that product can therefore only land low. Over every PIA from $0.10 to
  $557.20 by dime and 1-60 reduction months (334,320 cells), it lands a dime
  low in 11,572 cells (3.46 percent) and never high. A test pins these
  counts. Over PIAs to $4,500.00 (2,700,000 cells) the count is 94,530
  (3.50 percent); that wider figure comes from a one-off script, not a test.
  POMS's own example is one of the low cells ($802.80 over 5 months gives
  $780.40, not $780.50). G uses exact fractions and pins this example. The
  sealed ledger is not edited here.
- **No Axiom differential yet.** rulespec-us at `83abd9ece` (origin/main,
  2026-09-29) has no `us/statutes/42/403` encoding. Its 402(a)/(q)/(w) and
  415(a)/(b)/(i) encodings do not cover the maximum. Per d515 the
  differential waits for a pinned rule and stays diagnostic when it comes.
- **Capture integrity.** Three POMS captures (RS 00605.900, RS 00615.756 and
  .768) were re-fetched on 2026-09-29 and matched their manifest SHA-256
  byte for byte. Every Bulletin figure the tests quote was found on the live
  page the same day.
- **Review round 1 (g-r1).** The review found two medium issues. First,
  legal delayed-credit months were refused under a 48-month cap, and
  impossible ones were accepted. Second, the 403(a)(5) detector compared
  only consecutive months. It also found four low issues:
  - the pre-1917 credit rate;
  - a silent default for the spouse entitlement order;
  - a public single-record entry point;
  - no check of record dates against the payment month.

  All six are fixed above, each pinned by a test written to fail first.
  RS 00615.801 and RS 00630.400 were captured on 2026-09-30, and 402(w)(2)
  and (w)(6) were added to the LII excerpts from a body that matched the
  pinned SHA-256.
- **Oracle bug filed.** `ss.benefits.delayed_credit` caps credits at 48
  months: PolicyEngine/microcosm-dynamics#494.

## Not in scope

- RET deductions and their ordering against the maximum (403(a)(4) first
  sentence) are R2's.
- ARF and recomputation are R3's.
- Monthly timing and event journals are I's. For 403(a)(5), I must feed
  every month of each record, from its first month of entitlement, to one
  `SavingsClauseGuard`, and keep the guard's refusals in its denominators.
- No population, behavioral or forecast claim is admitted.
- `engine/loop.py`, `engine/steps.py`, `gates.yaml` and committed `runs/` are
  untouched.
