# Track B G: the gross-benefit layer

**Verification class: statutory conformance. Admitted scope: gross monthly
benefits for supported invented or published statutory cases only; no
population, behavioral or forecast claim.**

**Status: build-only, 2026-09-29; review fixes 2026-10-11. No real-data
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
  them and never high. POMS's $802.80 example is low in the wider one-off
  count; it is outside the 334,320-cell ledger's PIA range.
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
- **It refuses any later governed month whose total falls below the protected total**
  (`savings_clause_403a5`), whether or not the PIA rose into it. It also
  refuses every later governed month after that one, because the clause stays in
  effect.
- **It refuses every later governed month once a protected total may exist that G
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

- **Any fall after any protected month, at any later time.** A beneficiary
  leaving six months after a December COLA triggers refusal of every later
  governed month on the record, including a widow month the next year. In
  `test_known_over_refusal_a_beneficiary_leaves_in_a_cola_month`, two of
  three children leave in December and the total falls from $1,750.00 to
  $1,537.50. G refuses December. No captured source says whether a change of
  membership triggers the clause.
- **A month in which the maximum does not bind.** 403(a)(4) only decreases
  benefits, so on the statute's text a larger maximum changes nothing there.
  But SSA's procedure in RS 00630.400 divides the protected payment among
  the auxiliaries without mentioning the OB cap.
- **Every governed month after a refused month** while a protected total is in force.
- **Every governed month of a path with unknown history.** A simulation that starts
  with families already on the rolls must either reconstruct each record
  from its first month of entitlement or accept these refusals.

RS 00630.400's summary also requires "at least one beneficiary is reduced for
age". G does not require it, which can only add refusals.

## Supported and refused configurations

| Record | Supported beneficiaries |
| --- | --- |
| Retirement (living worker on RIB, with any reduction or credits) | Aged spouse, spouse with child in care, divorced spouse, child |
| Disability (worker on DIB, entitled after June 1980) | The same |
| Survivor | Aged widow(er), disabled widow(er) from January 1984, surviving divorced spouse, mother or father, child, one or two parents |
| Retirement, eligible living worker not entitled (from January 1985) | Independently entitled divorced spouses only; no worker payment |

These role families are supported when inputs are valid and none of the
refusals below applies. Invalid inputs raise `InvalidFamilyInput` before
coverage refusals. Valid unsupported configurations raise
`FamilyConfigurationUnsupported` (code `FAMILY_CONFIG_UNSUPPORTED`, design §7).
G never falls back to a single-worker computation.

| Reason | Trigger |
| --- | --- |
| `eligibility_before_1983` | Pre-June-1982 maximums rounded up (RS 00615.736B.3); pre-1979 table maximums |
| `payment_month_before_1983` | Months outside the post-May-1982 rounding rules |
| `di_entitlement_before_july_1980` | The pre-1980 disability maximum |
| `combined_family_maximum` | A child entitled on another record (403(a)(3)(A)), declared or found by the household check |
| `multiple_auxiliary_records` | Anyone else entitled as an auxiliary or survivor on two records (household check) |
| `deemed_or_putative_spouse` | 403(a)(3)(D) |
| `parent_benefit` | More than two declared parents, or the circular own-RIB entitlement interval for two potential parents (RS 00209.001/.015) |
| `disabled_widow_before_1984` | DWB payment months before January 1984 (RS 00615.310B.1/B.3) |
| `dib_guarantee_pia` | RS 00615.736B.2, .738 |
| `dib_after_reduced_rib` | 402(q)(2) |
| `workers_compensation_offset` | Section 224 |
| `government_pension_offset` | 202(k)(5), only benefit months through December 2023 |
| `administrative_finality` | Protected rates (RS 00615.754A.3) |
| `dual_entitlement_sequence` | A spouse's DIB after the spouse benefit (RS 00615.260), an aged widow(er) with DIB or born before 1929 (RS 00615.020B method D), or DWB with own RIB or DIB |
| `parisi_redistribution_ambiguous` | Own delayed credits, RIB-LIM, or dual zero reached only after auxiliary age reduction remain unsettled by GN 02603.050A/C |
| `parisi_before_october_1999` | A binding maximum with dual entitlement before 10/99 |
| `independently_entitled_divorced_spouse` | IEDS before January 1985 or a WEP-affected worker record before January 2024 (RS 00202.100) |
| `non_aime_formula_pia` | Old-start, special-minimum and frozen-minimum PIAs (RS 00615.740B.1) |
| `savings_clause_403a5` | A governed month whose total fell below a 403(a)(5) protected total, and every later governed month |
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
  POMS's own example is low in that wider one-off count, outside the
  334,320-cell ledger ($802.80 over 5 months gives $780.40, not $780.50).
  G uses exact fractions and pins this example. The
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


## Conformance review of October 11, 2026

Input checks precede coverage refusals for both direct `RecordState` inputs
and `WorkerRecord` inputs built inside `evaluate_family`. `record_state`
carries a deferred refusal; a pre-1983 maximum sentinel is never payable.
402(q)(6) and RS 00615.010 bound worker and spouse reductions at FRA minus
744 months when the cohort is given. RS 00615.692E bounds pre-1917 credits
at year-only maxima of 84 months through 1912, 72 for 1913, and 60 for
1914-1916 (the earlier bands depend on birth month);
legal credits remain refused because the bundle lacks their rate.

The own-benefit birth year must match the beneficiary's when both are
provided. RS 00615.301B.2 fixes a widow's reduction period when both ends
of her calendar birth year lie in the same band; boundary years require
the caller's period. Under 403(a)(2)(D), retirement eligibility cannot be
later than birth year plus 62, but an earlier DIB eligibility year is kept.
These bounds and input-before-refusal order extend invariants 6 and 11.

The final denominator audit executed another minimized instance of
invariant 6: a closure constructing an own DIB with one prior-RIB reduction
month and duplicate child ids returned `dib_after_reduced_rib`. OwnBenefit
now carries that valid unsupported configuration without refusing in its
constructor; the refusal is raised by `own_monthly_benefit` or the family
coverage stage after every input check (402(q)(2)). The standalone primitive
also validates impossible reduction months before refusing. The new
own-input-order tests execute both construction styles and Hypothesis
duplicate, wrong-role and invalid reduction-field cases. Valid reduced-DIB
configurations retain the same refusal and denominator.

`household_month_outcome` validates every input and guard before advancing
any guard. It advances every record for the month and returns one household
outcome, attaching the record id to a record refusal. This extends
invariants 7-9 to the monthly assembly entry point. The guard does not
compute the saving-clause raise. A child leaving in June after a December
COLA can trigger refusal, and every later governed month remains refused,
including an aged-widow month in the next year. The review's executed
survivor case begins with a 2020 record, PIA $1,500 and maximum $2,584.20,
a mother and two children. A December 2025 COLA raises the total to
$2,648.70; one child leaves in June 2026 and the total falls to $2,306.20.
`test_review_child_departure_six_months_after_cola_refuses_later_widow`
executes the entire path, including a refused 2027 widow month.


## Dual entitlement and deduction before reduction

GN 02603.045 applies the new rule to benefits payable from October 1999
(the earlier First Circuit cases remain refused). GN 02603.050C defines
PTAP as the family maximum less the life-case PIA, auxiliary age reduction
amounts for deductees, and their partial payable amounts. Other deductions
are R2's. Its non-deductee formula is OB times PTAP divided by TOTOB less
the deductees' OBs, capped at OB and dime-floored. GN 02603.050A.2 excludes
a dual rate reduced to zero; all-dual families retain the ordinary maximum.
`maximum_redistribution_rates` accepts payable amounts and separate age or
other deduction amounts so R2 can extend deduction handling without
rewriting distribution. GN 02603.050D's temporary cases require R2 to
select each eligible household's denominator and supply its OB mapping
separately. This helper computes rates, not work deductions.

GN 02603.060 examples A.5, A.8, A.9 and B.2 are reproduced. A.5 pays
children $125 each and spouse $0 plus own $100. A.8 pays children $125 each
and spouse $0 plus reduced own $80. A.9 pays the aged spouse $112.50, one
child $150, and a dual child $0 plus own DIB $200. B.2 pays spouse $2.40
plus own RIB $64 and children $123.30 each: PTAP is $750 minus $500 minus
$0.90 minus $2.40, or $246.70. The own-RIB $16 age reduction is not removed
from this pool. Both C examples involve work deductions and belong to R2.

Invariants 1, 2, 5 and 8 extend to own RIB age reduction. The pure PTAP
helper is deterministic and independent of mapping order, returns only
non-deductee ids, caps rates at OB, floors to dimes, and allocates at most
the nonnegative pool. Separate supplied deductions reduce that pool
monotonically. Its independent exact formula property provides a
differential with zero tolerance. Own delayed credits and RIB-LIM remain
`parisi_redistribution_ambiguous`: no captured example settles their
interaction with the PTAP age-reduction and partial-payable terms.


### Zero reached after auxiliary age reduction

This reading needs Max's judgment. GN 02603.045 says the counted amount is
"before any applicable reduction for age". GN 02603.050C requires the
"Age reduction amount for all workers or deductees". GN 02603.050A.2
instead says "If dual entitlement reduces a beneficiary's rate to $0.00
(technically entitled)" to disregard that beneficiary. A method-B spouse
with PIA $500, maximum $750, own RIB $64 and 36 auxiliary reduction months
has standard rate $83.30, age-adjusted $62.40, and zero auxiliary payable.
Disregarding the spouse pays children $125 each; retaining the $20.90 age
term pays $114.50 each, a $21 record-total difference. A reading of the
before-age text alone counts $83.30 minus $64, or $19.30, paying children
$115.30 each and a record total of $730.60. G refuses this
case as `parisi_redistribution_ambiguous`, rather than selecting the higher
payment. Zero before auxiliary age reduction is supported, including A.5
and A.8. The alternatives and the refusal are executed by the Parisi tests.


## Disabled widow(er) benefits

402(e)(1)(B)(ii) and (f)(1)(B)(ii) provide disabled widow(er) entitlement
at 50-59. The caller attests that entitlement; G does not adjudicate medical
or insured status. RS 00615.310B.1 says "DWB are reduced by 28.5 percent.
No additional reduction applies for the period before age 60." B.3
recalculates earlier entitlements effective January 1984 without the pre-60
reduction. G therefore supports payment months from January 1984 and refuses
prior months as `disabled_widow_before_1984`.

DWB OBs use the widow basis, share the family maximum, then take a fixed
28.5 percent reduction whose amount rounds up to a dime (402(q)(8);
RS 00615.301). The RIB-LIM then applies under 402(e)(2)(D) and RS
00615.320's general widow(er) rule. Reduction-month inputs are invalid for
this fixed initial reduction; later ARF adjustments belong to R3.
RS 00615.315 discusses election between WIB and DWB, not sequencing of an
own RIB or DIB. Both own-benefit combinations remain refused as
`dual_entitlement_sequence`.

Captured DWB sources contain rules without monetary worked examples.
Invented hand references use a $1,000 OB: reduction $285 and payable $715.
A $1,000.10 OB has reduction $285.10 (up from $285.0285) and payable $715.
Invariants: the reduction is exactly ceil-dime of 28.5 percent of the
post-maximum rate, payments are nonnegative dime amounts, are monotone in
the rate, and equal the existing widow helper at a full reduction period
(zero-tolerance differential). Family-maximum bounds and beneficiary-order
independence continue to hold. The DWB example and Hypothesis tests execute
these rules and the January 1984 boundary.


## Social Security Fairness Act

Pub. L. 118-273 was enacted January 5, 2025. The captured GN 02608.100
and RS 00605.360 bodies state that it eliminates GPO and WEP "for benefits
payable for months after December 2023" and that regular payments begin
with benefits due for January 2024, paid in February 2024. This is the
benefit-month boundary, not the enactment month or check month. A declared
GPO condition remains `government_pension_offset` through December 2023;
from January 2024 it has no effect on G's computed benefit.

G takes a PIA; it does not compute WEP. Before January 2024 the caller is
responsible for the WEP-affected PIA and associated maximum (RS
00605.360C.3). From January 2024 supply the regular-formula eligibility-year
PIA and its COLAs to rebuild the regular maximum. Keeping a pre-repeal
WEP PIA as input would not implement the repeal. The captures have 2025
transmittals despite older displayed page dates; the pinned body supplies
the repeal text. Invariants: exact equality between flagged and unflagged
post-repeal families and households; refusal retention before repeal; and
input validation preceding either payment-month branch. SSFA example and
Hypothesis tests execute the December 2023 / January 2024 boundary.

## Independently entitled divorced spouses and parents

From January 1985, `WORKER_NOT_ENTITLED` identifies a living, insured,
eligible worker who has not claimed. The caller attests two continuous
years of divorce for each beneficiary (202(b)(4)(A), (c)(4)(A); RS
00202.005 and .100). Only divorced spouses are admitted on this retirement
record. Their OB is half the eligibility-year PIA after applicable COLAs,
with the ordinary spouse age reduction and dual-entitlement methods. They
are outside the maximum, and no worker payment is added. The public
`WorkerRecord` and `RecordState` accept this form; household checks distinguish
an unclaimed living worker from a deceased worker. A WEP-affected worker
record, declared with `WINDFALL_ELIMINATION_PROVISION`, is refused for IEDS
before January 2024 (RS 00202.100's WEP note). That flag has no effect from
January 2024 under Pub. L. 118-273. Ordinary records still take the caller's
correct PIA; this layer does not calculate WEP.

Parents on survivor records use 82.5 percent for one entitled parent and
75 percent each for two, floored to a dime (202(h)(2); RS 00209.015). The
maximum applies before 202(k)(3)(A)'s own-benefit offset. There is no age
reduction. A parent's own RIB must be less than the parent's OB to establish
entitlement (RS 00209.001). This compares the actual reduced or credited
own RIB and the dime-rounded OB, rather than the own PIA. An own-DIB parent
remains technically entitled even if no parent benefit is payable (RS
00209.015); that parent still counts for the two-parent rate. More than two
declared parents is refused as `parent_benefit`: the captured one/two-parent
rules do not settle that configuration.

Needs Max's judgment: the parent entitlement count can be circular. RS
00209.001 requires "not be entitled to retirement insurance benefit (RIB)
equal to or exceeding
the amount of the parent's original benefit (One parent = 82 1/2%; Two parents
= 75%);". RS 00209.015 distinguishes "2. One parent entitled" from
"3. Two parents entitled". For PIA $1,000 and maximum $1,750, two potential
parents, one with own RIB $780, qualify together at the one-parent OB of
$825 but that first parent's RIB exceeds the two-parent OB of $750. Counting
two first excludes that parent and pays the other $825; testing eligibility
at $825 first would count two and pay the other $750 (a $75 difference),
while paying no auxiliary to the $780 own-RIB parent. Neither fixed order
is silently selected: `parent_benefit` refuses the interval between the two
dime-rounded OBs when both parents are potential entitlements.

Invented hand references (the captures publish rules without monetary
worked examples for these classes): PIA $1,000 pays a solo parent $825 or
two parents $750 each. An own RIB of $1,000 reduced for 36 months is $800
and leaves a solo-parent auxiliary of $25. Two parents and a child with
maximum $1,500 and one parent's own DIB $600 pay $0/$750/$750; own DIB $100
pays $400/$550/$550 after redistribution. IEDS OB $500 reduces to $375
for 36 months. With method C, own PIA $200 reduced to $160 leaves the
$300 spouse excess reduced to $225; the own record is counted once when
present in the household.

Additional executed invariants are: parent rates follow the entitled count;
own DIB remains technical while disqualifying own RIB does not count;
parent allocations retain exact dime arithmetic, maximum bounds and order
independence; adding a subject child cannot increase an existing payment;
IEDS has no worker payment, ignores the maximum, and adding another divorced
spouse leaves existing payments unchanged; dual offsets remain nonnegative
and exact; January 1985 and January 2024 boundaries are deterministic;
refusals remain in denominators and every invalid family is checked first.
The new parent/IEDS tests execute examples and Hypothesis checks beside them.

## Registry, coverage and invented denominators

`tests/data/track_b/gross_benefit_examples.yaml` is the single statutory
worked-example registry. Its 27 entries reproduce 205 figures quoted from
the manifest's captures and 53 separately labelled derived rates or
whole-dollar floors. Each figure links an output path, exact expected value
and verbatim capture literal. The .910 erratum retains published $899.52
beside the formula's $889.52. Bulletin presentation rounding is separate:
Table 1's displayed $659 is an exact $658.50 rate and a statutory $658
whole-dollar payment, with whole-dollar family total $1,974. These derived
figures are not represented as printed source figures.

The tag vocabulary enumerates record kind, every role, reductions, credits,
dual method, binding/disability maxima, redistribution, outside-maximum
roles, RIB-LIM, COLA, DWB, parent, IEDS and SSFA classes. All 42 supported
classes have a registered example or one of 17 explicit invented-only
explanations with test references. The coverage test derives kind and role
classes from G's enums; a missing supported class, figure or source literal
fails. Hypothesis tests execute completeness, class loss, determinism and
scenario order independence.

`scripts/track_b_g_conformance_report.py` writes the canonical JSON report
under this design directory. The exhaustive declared product is three
record kinds, all 55 role multisets of sizes zero through two, eight dual
modes, two reduction flags, three payment eras and fourteen single-condition
choices. Flags apply to the first beneficiary in Role enum order; empty
multisets with a beneficiary flag are invalid. Fixed invented money, cohort,
and snapshot assumptions are stated in the artifact. Conditions are none
or one declared record/beneficiary flag; combinations beyond that finite
axis and larger families are not claimed as enumerated.

There are 110,880 cells: 3,640 supported, 22,106 refused and 85,134 invalid.
All cells stay in the denominator. Twenty-one named invented witnesses form
a separate denominator, one executed refusal for every retained reason,
including historical, multi-record and protected-path cases absent from the
lattice. Statutory registry counts are separate again. These are invented
configuration counts, with no population weights or population claim.

Report invariants are unique/exhaustive declared cells, supported/refused/
invalid conservation, reason and era conservation, deterministic/order
independent classification, invalid-before-refusal order, separate
denominators and canonical byte equality on regeneration. Each is executed
by example and Hypothesis checks in the conformance-report tests. All ten
deliberate mutations failed and were restored; the commands and failing
tests are listed in the pull request (#530).
