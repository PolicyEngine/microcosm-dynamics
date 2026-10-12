# Track B R2 (part a): the retirement earnings test ledger

**Verification class: statutory conformance. Admitted scope: retirement
earnings test rule mechanics on invented record-years and published
statutory worked examples. No population, behavioral or forecast claim.**

**Status: build-only, revised 2026-10-12 after PR #528 review rounds 1–2.
No real-data computation.** This is the
single-record ledger core. Deduction before reduction, which can change
the other beneficiaries' gross rates, remains part (b).

The approved Track B design, revision 3, defines R2 in §3.1 as the
`apply_ret_year` ledger: entitlement, provisional suspension, final
deduction, grace year and family-record order. Sections 5.4 and 6 require
exact 1/2 and 1/3 rates, whole-dollar excess floors, the qualifying
divorced-spouse exception, chronological charging and explicit refusals.
Max's ruling d515 chose a Python statutory reference. This implementation
makes no Axiom or population conformance claim.

- Code: `src/populace_dynamics/track_b/ret_ledger.py` and
  `src/populace_dynamics/track_b/ret_grace.py`.
- Tests: `tests/test_track_b_ret_ledger.py` covers examples, boundaries,
  input validation, readings and refusals;
  `tests/test_track_b_ret_ledger_properties.py` executes Hypothesis
  invariants and R1 differentials; `tests/test_track_b_ret_grace.py`
  exercises carried state, all published grace examples and properties;
  `tests/test_track_b_ret_ledger_readings.py` checks the ledger money
  consequences and properties of simultaneous RIB/DIB readings;
  `tests/test_track_b_ret_ledger_sources.py` pins source bytes, quotations
  and monetary worked examples.
- Source helper: `tests/track_b_ret_ledger_support.py`.
- Captures: `tests/data/track_b/ret_ledger_sources/`. The manifest records
  the URL, UTC retrieval time, byte count and SHA-256 of each capture,
  with POMS transmittals and page dates. R1's full Act 203 capture remains
  at `tests/data/track_b/ret_sources/ssa_act_203.html`.

## Authority and inputs

The authorities are [Act 203(b), (f), (h)](https://www.ssa.gov/OP_Home/ssact/title02/0203.htm),
[20 CFR part 404 subpart E](https://www.ecfr.gov/api/versioner/v1/full/2026-10-07/title-20.xml?part=404&subpart=E),
and the POMS sections identified below. Those section citations refer to
the manifest's captured bytes; no source was fetched during this build.
The eCFR capture is the version as of 2026-10-07. The SSA publication and
benefit-planner examples are their captured 2026 versions.

`WorkEarnings` contains twelve exact, nonnegative wage amounts in the
months earned, signed annual net earnings from self-employment (NESE),
the months of self-employment, and substantial-service months. The caller
has already determined countable earnings under RS 02505.005 and whether
services are substantial under RS 02505.065; this ledger does not derive
those classifications from an income threshold. Wages are counted when
earned, and annual NESE is counted in its reportable tax year (20 CFR
404.428(d), .429; RS 02501.080).

`RETBeneficiary` supplies an identity, twelve elected benefit types,
entitlement months, and each month's gross and original rates. G supplies
the gross dime rate after the maximum, age and dual-entitlement
reductions (RS 02501.095B.5.a), and the original benefit before those
reductions for partial-payment shares (RS 02501.110A.2). Rates may change
between months. A December COLA or a child's departure is an input rate
change; R2 does not recalculate the gross family.

Each beneficiary also supplies actual earnings, optional estimated
earnings, the RIB FRA month, the actual grace-helper decision and an
optional `estimated_grace` decision for the current-year forecast,
death and divorced-spouse facts, and flags for established statutory
own-work protections or entitlement on two records. For ledger inputs,
`fra_month=None` means FRA after the year, `0` means FRA before the year,
and `1` through `12` identifies the attainment month. Survivors use the
RIB FRA, even when their survivor-benefit FRA is earlier (RS
02501.021B.3; Publication 05-10069).

`RecordYear` identifies the number holder (NH), a living retirement or
disability record or a deceased record, all entitled and legally
deemed-entitled beneficiaries, and months with a binding maximum or
another deduction event. A living NH must be present and receive RIB or
DIB in entitled months. A deceased NH must be absent. Deemed entitlement
asserts the married-person facts of Act 203(b)(1) and 20 CFR 404.420;
the broader unmarried-child reading of RS 02501.140 is refused. An
ordinary deemed child's age-18 months must be explicit. Their Act/CFR
coverage difference is refused even with those facts established.
Deemed entitlement requires a different NH with RIB entitlement in each
applicable month. `own_work_exempt_months` accepts only CHILD or WIDOW
payment months and asserts respectively attainment of age 18 or initial
widow(er) entitlement before 60 (Act 203(f)(1)(C)-(D)); it cannot
arbitrarily protect a RIB or spouse payment.

Input errors raise `InvalidFamilyInput` before a coverage refusal. These
include floats, invalid months, negative or non-dime rates, nonzero gross
outside entitlement, duplicate identities, inconsistent death or divorce
facts, noniterable monthly inputs, infinite monetary values, invalid
own-exemption or deemed-entitlement facts, and grace evidence for another
year. Missing supported R1 parameter years raise `KeyError` before
coverage refusal; a missing parameter is never silently replaced by the
prior year's amount or relabelled as a statutory coverage refusal.

## What it computes, in statutory order

1. **Annual and monthly limits.** Every annual exempt amount and rate is
   loaded through R1's `RETParameters.for_year`; the ledger contains no
   hard-coded annual limit. Under FRA all year it uses the lower amount
   and exact 1/2 rate. In the FRA-attainment year it uses the full higher
   annual amount and exact 1/3 rate against pre-FRA-month earnings. From
   the FRA month there is no own earnings test (Act 203(f)(3); 20 CFR
   404.430, .434(c); RS 02501.021B.1, B.4, B.6 and .080). The full annual
   amount applies in the year of death, including death before FRA in
   the attainment year (20 CFR 404.428(c); RS 02501.025B.3). Monthly
   limits are exact annual/12, including the fractional higher amounts
   expressly set by Act 203(f)(8)(D)(v)-(vi) for 2000 and 2001. The
   rounded charts are an explicitly nonstatutory operational sensitivity;
   they never supply the default statutory result.
2. **Countable earnings.** All months' wages and annual NESE count under
   FRA, including pre-entitlement earnings. In an FRA year, wages in or
   after the attainment month are excluded. NESE is divided across the
   self-employment months, floored to whole monthly dollars, then
   multiplied by the number of those months before FRA. `FLOOR` follows
   the literal “round down” instruction, including for losses; it is not
   labelled conservative because floor can pay more when NESE is negative.
   An explicit `DROP_CENTS` alternative truncates signed monthly NESE toward zero;
   it differs from mathematical floor only for losses (RS
   02501.080B.2.b-e; 20 CFR 404.428-.430).
3. **Excess.** `calculated_excess` returns
   `floor(max(0, countable - annual_exempt) * statutory_rate)`. The
   whole-dollar excess is computed after exact Fraction arithmetic
   (RS 02501.080B.1.d and B.2.a; Act 203(f)(3); 20 CFR 404.430(b)). The
   scalar helper reproduces the published 1999 formula example, while
   the payment ledger refuses years before 2000.
4. **NH charging.** Charge the NH's excess first, chronologically from
   the first entitled, unprotected month until recovered or the year's
   chargeable benefits are exhausted. The pool includes every payable
   benefit on the record and legally deemed-entitled benefits. A
   qualifying divorced spouse is excluded from both withholding and
   the pool when divorce has lasted at least two years, or the NH was
   entitled to RIB before the divorce (Act 203(b)(1)-(2); 20 CFR
   404.415(b), .420, .434; RS 02501.021B.5.b, .095B.2 and .140).
5. **Other workers' charging.** After NH charging, charge each auxiliary
   or survivor's excess against that person's remaining benefit only.
   Do not charge an already exhausted month again. If this would free
   binding family-maximum room for another beneficiary, refuse the
   record for part (b) (20 CFR 404.434(b)(2)-(3); RS 02501.095B.3-4,
   .155A.3-4; GN 02603.020-.050).
6. **Protected months.** A worker's own excess cannot be charged in an
   unentitled month, a protected grace-year NSM, the FRA month or later,
   a DIB/DWB/CDB payment month, or an explicitly established own-work
   exemption under Act 203(f)(1)(C)-(D) (20 CFR 404.435; RS
   02501.095B.5.b and .021B.5.a). A person's own protection does not
   protect that person's benefit from another worker's excess: for
   example, the NH can charge a spouse at FRA or a married,
   deemed-entitled CDB recipient. If the NH's own excess is protected
   for a month, it cannot be charged to the family in that month (Act
   203(f)(1); RS 02501.140).
7. **Provisional suspensions.** Independently repeat the charging order
   using estimated earnings, or actual earnings when no separate
   estimate was supplied. Use `estimated_grace` for provisional grace
   eligibility when supplied, otherwise the actual grace decision.
   Withhold the entire last charged month even
   when only part of its rate is needed. The ledger records this
   withholding separately from final deductions (20 CFR 404.434;
   RS 02501.100B.2, .105; RS 02510.005 versus .015).
8. **Final partial payments.** With actual closed-year earnings, the
   last charged month can have a partial payment. For NH excess,
   apportion that partial pool by original benefit amounts, before the
   maximum, age reduction and dual-entitlement offset. Cap each share
   at its current pre-deduction rate and redistribute the excess by
   the remaining original shares. Do not round between iterations.
   An entitled beneficiary with a zero payable rate retains a positive
   original share and counts among the beneficiaries in that computation;
   post-reduction zero is not loss of entitlement.
   Two beneficiaries receive the capped rate and remaining balance as
   prescribed. With three or more beneficiaries, an overflow below $1
   ends reapportionment: retain that iteration's uncapped shares, cap
   the beneficiaries whose shares exceeded their rates, and record the
   unpaid overflow as `undistributed_subdollar_residual` (20 CFR
   404.439-.441; RS 02501.110A-B). `partial_payments` returns a
   mapping-compatible `PartialPaymentAllocation` of exact net amounts
   with an `undistributed_subdollar_residual` attribute.
   Completing redistribution after this mandatory stop is unavailable.
9. **Checks, reconciliation and crediting.** For every beneficiary-month,
   `gross = net_due + deduction`, and the 215(g) check is `floor(net_due)`.
   Check-rounding loss is not another work deduction. Reconciliation
   is the sum of final checks less provisional checks; it can be
   negative when the estimate was too low. Crediting months identify
   actual full or partial work deductions (RS 02501.021C; RS
   02501.120B.3). The residual field never creates a standalone crediting
   event; crediting follows each beneficiary-month's positive actual
   deduction. This is an R3 input; R2 does not calculate an ARF or a
   benefit increase.

For each worker, final deductions attributable to that worker equal
`charged + undistributed_subdollar_residual`. Charged excess is capped by
chargeable benefits; `charged + uncharged = excess`. The residual remains
separate from both charged and uncharged excess and is attributed to the
worker whose partial family allocation produced it. Each stopped partial
allocation has a residual strictly below $1. This does not change the
beneficiary-month identity or the final check floor.

Uncharged excess is disclosed in the worker result and expires at the
year boundary. It is not an input to another record-year. Requested
prorated or deferred work suspensions are a different administrative
path and are refused here (RS 02501.100B.1, B.4-5, .120-.125).

## Monthly limits prescribed by the Act

Act 203(f)(8)(D) opens: “Notwithstanding any other provision of this
subsection, the exempt amount which is applicable to an individual who
has attained retirement age (as defined in section 216(l)) before the
close of the taxable year involved shall be”. Its two historical clauses
expressly set:

- Clause (v): “for each month of any taxable year ending after 1999 and
  before 2001, $1,416.66 2/3”.
- Clause (vi): “for each month of any taxable year ending after 2000 and
  before 2002, $2,083.33 1/3”.

These are exact $17,000/12 and $25,000/12, respectively. RS
02501.025B.2 agrees: “The monthly exempt amount is equal to 1/12 of the
applicable annual exempt amount.” 20 CFR 404.430(a)(1) likewise says:
“The monthly exempt amount, (which is 1/12 of the annual exempt amount),
applies only in a beneficiary's grace year or years.” The statute
controls; `MonthlyLimitPolicy.EXACT_TWELFTH` is the default for every
supported year, with exact Fraction arithmetic and no monthly rounding.

The CFR 404.430(a)(2)(iii) and RS 02501.025D charts display the higher
annual/monthly pairs `$17,000 $1,417` and `25,000 2,084`. Their rounded
amounts are retained only as
`MonthlyLimitPolicy.NONSTATUTORY_CHART_CEILING`, an explicitly selected
operational sensitivity. A result obtained with it does not establish
statutory conformance at the conflicting 2000/2001 boundary. Later
bundled annual limits are exact multiples of twelve, so the two settings
coincide there.

The reviewer's minimized invented 2001 case has FRA in March, entitlement
only in February, a $1 February rate, $22,919 January wages and $2,084
February wages. Countable earnings $25,003 produce
`floor(($25,003 − $25,000)/3) = $1` excess. February wages exceed the
Act's exact monthly limit, so February payment is $0, deduction is $1
and uncharged excess is $0. The chart sensitivity protects February and
pays $1, leaving the $1 excess uncharged. The earlier invented June FRA
case at a $600 rate and $28,000 January/$2,084 February wages similarly
differs by a $600 February check. Both computations are explicitly
labelled; only the exact limit is the statutory default. Source tests
pin both fractional Act amounts verbatim against the reused Act capture.

## Mandatory sub-dollar reapportionment stop

20 CFR 404.440 says: “If the excess amount involved at any point totals
less than $1, it is not reapportioned; instead, each beneficiary is paid
on the basis of the last calculation.” RS 02501.110B.2 says: “Do not
reapportion the excess amount if at any point it totals less than $1; the
monthly benefit amount includes this last calculation.” Its instruction
“Do not round any share until the final apportionment or reapportionment
is completed” keeps all shares exact up to that stop.

The stop is the only statutory computation. A capped beneficiary keeps
its pre-deduction rate, and each uncapped beneficiary keeps its share
from the last calculation. Their exact nets plus the undistributed
residual equal the available partial pool. The residual is unpaid before
the distinct Act 215(g) check floor. It is disclosed in the allocation
and worker ledger, with attribution to the charging worker. It is not
additional excess earnings charged. Crediting follows actual full or
partial work deductions; the residual field never creates a standalone
crediting event. The former `subdollar_partial_reapportionment` refusal is retired:
the rule now computes the source-prescribed stopped allocation. There is
no complete-reapportionment policy in the statutory interface.

| Invented partial pool; caps $10/$1.90/$10; original shares 2:1:1 | Exact stopped shares | Undistributed residual | Checks |
| --- | --- | --- | --- |
| $8 | $4/$1.90/$2 | $0.10 | $4/$1/$2 |
| $9.90 | $4.95/$1.90/$2.475 | $0.575 | $4/$1/$2 |

The $9.90 case catches the settled-dollar error from continuing to
redistribute: doing so would incorrectly raise the first check to $5.
The reviewer's G-generated case likewise has rates $3.50/$0.10/$1,
originals $5/$2.50/$2.50, $3 NH excess and a $1.60 January partial pool.
It stops at $0.80/$0.10/$0.40, records $0.30 residual and pays checks
$0/$0/$0. Continued redistribution would incorrectly pay the NH $1.
The source-prescribed two-beneficiary rule is separate: a $6 pool with
caps $10/$1.90 and shares 2:1 pays exact $4.10/$1.90 without stopping
on the sub-dollar balance (20 CFR 404.440; RS 02501.110B.1).

RS 02501.110B.2 also covers a first apportionment exceeding the rates
for several beneficiaries simultaneously. All shares above their caps
contribute to that iteration's overflow before testing the $1 stop. The
invented $8 pool has caps NH $8, spouse $0 and child `599/300` dollars,
with original shares 2:1:1. Its initial shares are $4/$2/$2. The spouse
releases $2 and the child
releases `1/300` dollars, so the combined `601/300` dollars must be
reapportioned to the NH. Exact net shares are NH `1801/300` dollars,
spouse $0 and child `599/300` dollars, total $8, with no residual; the
checks are $6/$0/$1.
The deterministic regression is
`test_simultaneous_initial_caps_reapportion_combined_overflow`.

The stop-boundary property keeps both initial-cap and later-cap cases.
For a pool of `8 * scale`, spouse cap zero and child cap
`pool / 3 - overflow_cents / 100`, the child caps later only when its cap
is at least the initial `pool / 4` share. At `scale=1`, 66 cents preserves
that condition, while 67 and 68 cents cap both auxiliaries initially.
The property's exact monetary, residual and conservation assertions
follow the applicable iteration rather than assuming that only the
spouse caps first (RS 02501.110B.2).

RS 02501.110 Example 3 still reproduces exact $38.50/$16/$19.25/$19.25
and checks $38/$16/$19/$19: the spouse cap releases $2.60, so the next
reapportionment is required. The 20 CFR 404.440 worked example still
gives checks $75/$16/$16/$16, with the displayed-rate and printed-pool
discrepancy pinned side by side below. These examples exercise
reapportionment without a sub-dollar stop; the invented pools and
G-generated case execute the threshold itself.

## The pure grace-year state

`grace_year` takes twelve `GraceMonth` inputs, a carried `GraceYearState`,
the FRA month and explicit termination events. Entitlement and the elected
payment type are separate. The caller carries the returned `next_state`
through consecutive calendar years; an omitted year is an input error.
The helper uses no population data and performs no monetary calculation.

The initial grace year is the first year with an eligible NSM during
entitlement and before FRA. A new type of benefit after a break of at
least one entirely unentitled month can create another grace year when
its first NSM occurs. Pending eligibility survives a year with no NSM.
Changing spouse to divorced-spouse does not create a new legal benefit
type: both are Act 202(b)/(c) benefits (RS 02501.030B.1-2 and D).

Child, young-spouse and mother/father terminations can supply a termination
grace year. It belongs to the year of the last entitled month: a January
termination belongs to the preceding December's year. Death, contiguous
conversion, conversion to an aged spouse and mere child-in-care failure
do not qualify. A termination-only grace does not overwrite LMETY. Any
Social Security entitlement in the next month excludes the termination
grace when that next month is present in the current year's inputs,
even if a caller labels the ending event normal. For a December ending,
the caller must establish a January conversion exclusion through the
termination reason; this year's helper cannot infer next year's elected
benefit (20 CFR 404.435(b)(4); RS 02501.030B.3 and D).

`met_eligible_months` records months in which the monthly test can apply
under the selected disability reading; `protected_months` records the
actual NSMs used to establish the year's status. The ledger applies the
monthly wage and substantial-service facts separately to actual and
estimated earnings over the eligible months. It does not assume that
the same months are NSMs under two different earnings reports (RS
02501.030C; RS 02510.005, .015).

DIB/DWB/CDB-only years cannot create NSMs. The conservative default also
excludes simultaneous disability entitlement, following 20 CFR
404.435(b)(3). The named POMS alternative permits NSMs in months RIB is
elected while technical DIB entitlement continues, reproducing RS
02501.030B.4's published example. The money-changing difference is
recorded under Needs Max's judgment.

## Supported and refused configurations

The default R1 bundle supplies published annual values through 2026.
Later years need R1 parameters from an explicitly permitted input vintage;
the ledger does not project or fill missing years. The nonmonetary grace
helper can process earlier history so the state at a supported payment
year is explicit.

| Configuration | Result or refusal reason | Authority and boundary |
| --- | --- | --- |
| Calendar record-year from 2000 with an available R1 year | Supported | Act 203(f); RS 02501.021B.6 |
| Living RIB worker and spouse/divorced-spouse/child beneficiaries | Supported with the supplied G rates | RS 02501.095 |
| Disability NH, or DIB/DWB/CDB elected payment months | Supported own-work exemption; RIB elections remain tested | RS 02501.021B.5.a |
| Deceased record and widow(er), mother/father or child own work | Supported without binding-maximum readjustment | RS 02501.095B.3 |
| Variable monthly rates and entitlement | Supported; twelve months retained | RS 02501.100B.1 |
| Three-or-more-beneficiary partial pools with a sub-$1 capped overflow | Supported with the mandatory stop and an explicit undistributed residual | 20 CFR 404.440; RS 02501.110B.2 |
| Qualifying divorced spouse | Excluded from NH charging; own earnings still tested | Act 203(b)(2); RS 02501.021B.5.b |
| Legally married deemed-entitled CDB or mother/father recipient | Supported against NH excess when the legal facts are asserted | Act 203(b)(1); 20 CFR 404.420 |
| Two-record entitlement with no actual or estimated excess | Supported; no coordinated charging is needed | RS 02501.145-.150 |
| Payment year before 2000 | `YEAR_BEFORE_2000` / `payment_year_before_2000` | FRA-era charging rules differ; RS 02501.021B.6 |
| Fiscal taxable year | `FISCAL_YEAR` / `fiscal_taxable_year` | RS 02501.025C.2, .075 |
| Short taxable year | `SHORT_TAXABLE_YEAR` / `short_taxable_year` | RS 02501.025C.3; modern death years use the full annual exemption |
| Requested prorated suspensions | `PRORATED_SUSPENSION` / `prorated_work_suspension` | RS 02501.100B.5, .120-.125 |
| Requested deferred suspensions | `DEFERRED_SUSPENSION` / `deferred_work_suspension` | RS 02501.100B.4 |
| Protested partial current-year suspension | `PROTEST_PARTIAL_SUSPENSION` / `protested_partial_work_suspension` | RS 02501.100B.3 requires a different provisional path |
| Auxiliary/survivor own deduction with a binding maximum and another entitled positive original share, including a zero payable rate | `DEDUCTION_BEFORE_REDUCTION` / `deduction_before_reduction_part_b` | Others may gain gross rate; RS 02501.155A.3-4, GN 02603 |
| Two-record entitlement with actual or estimated excess | `TWO_RECORD_EARNINGS` / `excess_earnings_on_two_records` | RS 02501.145-.150 require coordinated records |
| Noncovered foreign work | `FOREIGN_WORK` / `noncovered_foreign_work` | Act 203(c); 20 CFR 404.417-.418 |
| Refusal of vocational rehabilitation | `VOCATIONAL_REHABILITATION` / `vocational_rehabilitation_refusal` | RS 02501.130 |
| Another deduction event on the record | `OTHER_DEDUCTION` / `other_deduction_event` | Act 203(c)/(d); RS 02501.130; GN 02603.040 |
| Unmarried purported deemed entitlement | `DEEMED_ENTITLEMENT_BASIS` / `deemed_entitlement_marriage_basis` | RS 02501.140's wording is broader than Act 203(b)(1)/20 CFR 404.420 |
| Ordinary deemed adult CHILD with asserted marriage and age facts | `DEEMED_ENTITLEMENT_BASIS` / `deemed_entitlement_marriage_basis` | Act 203(b)(1)'s adult-child wording is broader than CFR .420's disabled-child basis |

The binding-maximum guard is conservative. This annual interface accepts
a record-month binding flag but does not reconstruct each beneficiary's
maximum membership from post-reduction rates. It therefore refuses an
own deduction with any other entitled positive original share, including
mixed divorced-spouse configurations where a later G-aware interface
could establish that no room is released. Part (b) must retain G's
`subject_to_family_maximum` metadata to narrow that coverage boundary.

Each coverage refusal is a `RETConfigurationUnsupported`, a subclass of
G's `FamilyConfigurationUnsupported`, and has the common
`FAMILY_CONFIG_UNSUPPORTED` code plus the R2 reason. `evaluate_ret`
catches coverage refusals only; invalid input propagates.
`count_ret_outcomes` retains every supported or refused row and weight,
including counts by reason. `weighted_ret_total` raises
`FamilyTargetBlocked` if any row was refused. A refusal cannot improve
the apparent coverage denominator by disappearing.

## Executed invariants and differentials

The following are invariants of the admitted computation. Partial pools
conserve exact net shares plus the undistributed residual, rather than
requiring a redistribution forbidden by the sub-dollar rule. The
source-prescribed two-person balance rule is pinned separately. Exact
entitlements, undistributed residuals and whole-dollar checks are distinct
quantities.

In the table, unqualified property test names are in
`tests/test_track_b_ret_ledger_properties.py`.

| Invariant | Executing tests |
| --- | --- |
| Per beneficiary-month, `gross = net_due + deduction`; both actual and provisional deductions lie between zero and gross; the check floors net | `test_every_month_conserves_exact_money_and_checks_are_floored`; `test_auxiliary_own_excess_uses_earliest_entitled_unprotected_months` |
| A worker's charged excess is capped by chargeable benefits; charged plus uncharged equals excess; final deductions attributable to that worker equal charged plus the undistributed residual; no charge exceeds excess | `test_exact_final_charges_are_excess_capped_by_chargeable_benefits`; `test_number_holders_excess_is_charged_before_auxiliarys_own`; `test_auxiliary_own_deductions_are_monotone_with_protected_months_fixed` |
| Earlier chargeable months are exhausted before later months | `test_earlier_chargeable_months_are_exhausted_before_later_months`; `test_auxiliary_own_excess_uses_earliest_entitled_unprotected_months` |
| Excess cannot carry between years | `test_excess_is_year_local_and_cannot_change_a_clean_later_year`; unit `test_uncharged_excess_does_not_carry_into_the_next_year` |
| NH excess is applied before another beneficiary's own excess | `test_number_holders_excess_is_charged_before_auxiliarys_own`; source `test_poms_02501_095_number_holder_then_auxiliary_example`; source `test_cfr_404_441_number_holder_then_spouse_with_grace_month` |
| A beneficiary's own excess cannot reduce anyone else's benefit in part (a) | `test_auxiliarys_own_excess_cannot_reduce_any_other_beneficiary` |
| Excluding a qualifying divorced spouse leaves everyone else's deduction unchanged and protects that spouse from NH excess | `test_excluded_divorced_spouse_leaves_every_existing_deduction_unchanged`; unit `test_qualifying_divorced_spouse_is_outside_number_holders_test` |
| Fixed-rate, fixed-protection annual deductions are nondecreasing as countable earnings increase | `test_each_annual_deduction_is_nondecreasing_in_number_holders_earnings`; `test_auxiliary_own_deductions_are_monotone_with_protected_months_fixed` |
| With the same rates and protections, deductions are nonincreasing as the applicable exemption increases | `test_each_annual_deduction_is_nonincreasing_in_exempt_amount` |
| FRA-month and later wages change neither countable earnings nor deductions; those own-work months remain uncharged | `test_fra_month_and_later_wages_change_nothing`; unit `test_fra_month_wages_and_later_wages_are_not_counted`; source `test_poms_02501_080_fra_wage_and_nese_examples` |
| Grace-year NSMs are never charged to their worker's excess | `test_grace_year_nonservice_months_are_never_charged`; unit `test_grace_nonservice_months_protect_own_benefit` |
| DIB payment months are exempt from the NH's own work, and elected RIB months are tested | `test_disability_months_are_exempt_but_elected_rib_months_are_tested` |
| DWB/CDB payment months are exempt from that recipient's own work | `test_disabled_auxiliarys_own_excess_never_reduces_disabled_benefit`; unit `test_disability_benefits_are_exempt_from_their_own_work_test` |
| With identical actual and estimated earnings, grace status and protected-month facts, provisional suspensions are full months, cover final deductions in aggregate, and have nonnegative reconciliation | `test_equal_estimate_provisional_suspensions_are_full_and_cover_final`; source `test_publication_05_10069_current_year_suspension_and_next_year_repayment` |
| Crediting months reflect actual full or partial work deductions; the residual field never creates a standalone crediting event; reconciliation equals final less provisional checks | `test_crediting_months_come_from_actual_full_or_partial_deductions`; unit `test_actual_and_estimated_earnings_are_separate_inputs`; unit `test_entitled_zero_rate_auxiliary_keeps_its_original_partial_share` |
| Results are deterministic and beneficiary-order independent | `test_determinism_and_beneficiary_order_independence` |
| Partial net shares plus the residual conserve the pool, obey each cap and preserve original-share proportions among uncapped beneficiaries; each stopped allocation has a residual in [0, $1) | `test_partial_payments_preserve_total_with_residual_and_caps_and_proportions`; `test_subdollar_stop_keeps_exact_last_uncapped_shares_and_capped_rate`; source `test_cfr_404_440_and_poms_02501_110_stop_at_subdollar_last_calculation` |
| Partial reapportionment is deterministic and input-order independent | `test_partial_reapportionment_is_deterministic_and_order_independent` |
| An overflow of exactly $1 must be reapportioned; simultaneous caps contribute their combined overflow; later iterations retain every already-capped beneficiary and use the original entitled-participant count for the three-person stopping rule | `test_stop_threshold_and_later_iteration_keep_original_participant_count`; `test_simultaneous_initial_caps_reapportion_combined_overflow`; unit `test_exactly_one_dollar_overflow_is_reapportioned`; unit `test_later_subdollar_stop_retains_previously_capped_beneficiary` |
| R1 annual amounts and exact rates match every supported bundled year, with zero tolerance | `test_r1_differential_matches_every_supported_year_exactly`; `test_r1_differential_statutory_default_is_exactly_one_twelfth` |
| The default statutory monthly limit is exactly annual/12, with zero tolerance; wages above it cannot protect a grace month | `test_r1_differential_statutory_default_is_exactly_one_twelfth`; readings `test_property_default_monthly_limit_is_exact_twelfth_and_controls_grace_wages`; unit `test_act_203_f_8_d_vi_exact_limit_is_not_chart_ceiling`; source `test_act_203_f_8_d_v_vi_monthly_amounts_are_quoted_and_equal_annual_twelfths` |
| Missing R1 years raise rather than substitute | `test_r1_differential_missing_year_raises_without_substitution`; unit `test_missing_parameter_year_is_not_carried_forward` |
| Every outcome row and weight stays in the coverage denominator; any refusal blocks an aggregate | `test_coverage_denominators_keep_every_supported_or_refused_row`; unit `test_coverage_denominator_keeps_refusals_and_blocks_aggregate` |
| Exact 1/2 and 1/3 excess rates use an integer floor: excess is nonnegative and differs from the unrounded amount by less than $1 | readings `test_property_excess_uses_exact_statutory_rate_and_dollar_floor`; unit `test_lower_threshold_and_whole_dollar_floor`; unit `test_fra_threshold_uses_one_third_and_floors`; R1 differential above |
| Invalid input is never counted as a statutory coverage gap | `test_coverage_denominators_keep_every_supported_or_refused_row`; unit `test_invalid_wage_inputs_raise_before_coverage_refusal`; `test_invalid_rates_raise_before_coverage_refusal`; `test_duplicate_identity_is_invalid_even_in_an_unsupported_record`; `test_invalid_inputs_are_not_counted_as_coverage_gaps` |
| Under the explicit POMS election reading, only eligible elected RIB NSMs receive grace protection; the conservative CFR reading supplies none during concurrent disability entitlement | readings `test_property_explicit_poms_election_protects_only_eligible_rib_months`; `test_simultaneous_dib_rib_source_readings_change_4200_dollars` |
| Actual and estimated grace statuses are distinct; changed service facts can require recovery even when annual earnings coincide | readings `test_estimated_initial_grace_and_actual_grace_are_separate`; `test_property_changed_grace_estimate_can_require_recovery` |
| Zero payable caps retain their original shares and count toward the three-beneficiary sub-dollar stop; exact net shares plus the residual conserve the pool | `test_zero_cap_participants_preserve_total_and_trigger_source_stop`; unit `test_entitled_zero_rate_auxiliary_keeps_its_original_partial_share` |
| Explicit Act 203(f)(1)(C)-(D) protections exempt only the recipient's own work in asserted CHILD/WIDOW months | readings `test_property_other_statutory_own_exemptions_protect_only_that_workers_excess`; `test_own_work_exempt_flag_requires_a_statutory_benefit_type` |

The `ss/benefits.py` float oracle has no earnings-test ledger implementation,
so there is no second RET-payment implementation against which to invent a
float differential. The implemented shared surface is R1's parameters,
with exact comparisons and no tolerance. G's `whole_dollars` helper is
shared directly; the independently calculated example checks and property
floor assertions verify its use after net entitlement.

The grace-state invariants are executed in
`tests/test_track_b_ret_grace.py`:

| Invariant | Hypothesis test |
| --- | --- |
| Protected months are exactly eligible, entitled, non-disability, pre-FRA NSMs under the chosen reading | `test_property_only_entitled_nondisability_prefra_nonservice_months_protected` |
| Grace results are deterministic and benefit-type input order independent | `test_property_determinism_and_type_order_independence` |
| Continuous entitlement cannot create a second initial/after-break grace | `test_property_continuous_entitlement_cannot_create_second_grace` |
| A new after-break grace requires a gap and a different legal type; the same type never renews it | `test_property_new_type_requires_gap_but_same_type_never_renews` |
| A termination-only grace leaves LMETY unchanged | `test_property_termination_only_never_changes_lmety` |
| Termination-event order does not change the decision or next state | `test_property_termination_event_order_independence` |
| The POMS election reading uses RIB receipt while preserving technical disability entitlement history | `test_property_poms_rib_election_separates_entitlement_from_receipt` |
| Returned state advances exactly one year, without mutating the input state | `test_property_state_advances_exactly_one_year_without_hidden_mutation` |
| Pending after-break eligibility survives a year without an NSM | `test_property_after_break_eligibility_survives_year_without_nonservice` |
| A reentry involving only disability benefits cannot create pending different-type grace eligibility | `test_property_disability_reentry_after_break_cannot_create_pending_grace` |
| A second gap with the same benefit type cannot erase pending post-break eligibility before the first eligible NSM | `test_property_pending_grace_survives_another_same_type_gap`; `test_same_type_gap_does_not_erase_pending_grace` |

The source invariants are executed by
`test_manifest_pins_every_capture`,
`test_every_capture_is_used_by_a_conformance_quote`,
`test_rule_text_is_quoted_from_the_captures`,
`test_worked_example_figures_are_quoted_from_the_captures`, and
`test_pdf_excerpt_matches_the_captured_pdf_text`. Every capture's byte
count and SHA-256 is recomputed. The PDF helper uses `pdftotext -layout`
when available, otherwise the manifest-pinned verbatim excerpt from
those same PDF bytes. Neither branch fetches a source.

The captured XML was inspected across 20 CFR 404.415-.441. Its formal
RET worked examples are in .435 and .439-.441, all reproduced below;
.429's grain-broker illustration concerns countable-income classification,
which the caller supplies.

An estimated-versus-actual grace counterexample is intentional. With
$600 rates for all twelve months and annual earnings $24,480 + $14,400,
the beneficiary forecasts substantial services only January-May and
an initial grace with June-December NSMs. Actual substantial services
occur throughout the year, so no actual initial grace exists. Final
deductions are $7,200, provisional withholding is $3,000 and
reconciliation is −$4,200. Thus nonnegative reconciliation requires
identical protections as well as identical annual earnings. The named
example and Hypothesis property in the invariant table execute this
case; it is not labelled a defect or silently forced to zero.

A minimized grace-state counterexample exposed a defect in an early
implementation. A previously entitled CHILD recipient with LMETY 2000
entered spouse entitlement in January 2026, had no entitlement in
February, and returned to the same spouse type for a March NSM. The
second gap incorrectly erased the pending different-type grace. The
fixed transition retains pending eligibility until the first eligible
NSM, as RS 02501.030B.2 requires. Both the regression example and a
Hypothesis property execute this transition; the property minimized it
to a RIB reentry and a February gap. This was an implementation defect,
with no competing statutory reading.

Two G-generated counterexamples exposed coverage defects in the early
ledger. With PIA $1,000 and maximum $1,500, a reduced NH receives $700,
an entitled dual spouse has original $500 but payable $0 after one
delayed credit, and a dual child receives $150 with original $500. NH
excess $849 leaves a $1 January pool. Dropping the zero-rate spouse
incorrectly bypassed the three-beneficiary sub-dollar rule; retaining
all original shares now gives the mandatory stop at exact $0.50 to the
NH, $0.25 to the child and zero to the spouse, with a $0.25 undistributed
residual. The spouse has no actual deduction and no crediting month:
the residual field never creates a standalone crediting event.
`test_entitled_zero_rate_auxiliary_keeps_its_original_partial_share`
executes that zero-cap result. This example keeps the zero cap in the
allocation; the former complete-redistribution result is unavailable.
In a second G-generated survivor
record, PIA $1,000/max $1,500 gives a widow $796.40 and an entitled CDB
recipient $0 after a $650 own disability benefit, with originals $1,000
and $750. Widow excess $100 must refuse for part (b): the CDB recipient
can gain family-maximum room despite the current zero payable rate.
`test_entitled_zero_rate_auxiliary_keeps_its_original_partial_share`
and `test_binding_survivor_maximum_with_zero_rate_cdb_is_deferred_to_part_b`
both failed against the restored early implementation before the fixes.

## Monetary worked examples

Every quoted monetary figure and rule is checked verbatim against its
capture. Invented earnings distributions used to generate a source's
stated excess are identified in the fixtures; they are not represented
as additional source facts. Where a published example gives a partial
pool without a recoverable annual excess, the pure partial-payment
helper is used rather than inventing an inconsistent ledger.

| Source | Figures and reproduced result | Test in `test_track_b_ret_ledger_sources.py` |
| --- | --- | --- |
| RS 02501.080B.1.d | Age 64 in 1999; $12,121 earnings less $9,600 exempt, divided by two and floored = $1,260. Scalar formula only; the 1999 ledger is refused | `test_poms_02501_080_1999_formula_example_outside_ledger_scope` |
| RS 02501.080B.2.b | FRA 6/00; $30,000 January-May wages count; $10,000 June-December does not. ($30,000 − $17,000)/3 floors to $4,333 | `test_poms_02501_080_fra_wage_and_nese_examples` |
| RS 02501.080B.2.c | $24,000 NESE across 12 months, FRA June: $2,000 × 5 = $10,000; below $17,000, so no ET deduction | Same test |
| RS 02501.080B.2.d | $44,000 NESE April-December, FRA June: monthly $4,888 after dropping the fraction; × 2 = $9,776. No ET deduction; year/month/limit errata below | Same test and `test_poms_02501_080_nese_source_errata_are_pinned_side_by_side` |
| RS 02501.080B.2.e | FRA 7/00; $24,000 wages plus $7,000 NESE June-December / 7 = $1,000 pre-FRA NESE; total $25,000. ($25,000 − $17,000)/3 floors to $2,666 | Same FRA example test |
| RS 02501.095B.2 | NH $378, spouse and child $160 each, family $698. Excess $2,094 = three months; January-March fully withheld | `test_poms_02501_095_number_holder_family_example` |
| RS 02501.095B.4 | NH $346, spouse $173, family $519; NH excess $2,076 withholds January-April. Spouse excess $865 then withholds that spouse May-September | `test_poms_02501_095_number_holder_then_auxiliary_example` |
| RS 02501.100B.2 | Monthly $562, excess $2,880: January-May consume $2,810; provisional suspensions also withhold all June | `test_poms_02501_100_full_month_suspension_example` |
| RS 02501.110 example 1 | Monthly $562, excess $2,881: final January-May withheld, $71 June deduction and $491 June paid. Provisional January-June withheld; $491 reconciliation | `test_poms_02501_110_partial_benefit_example_1` |
| RS 02501.110 example 2 | NH $800, four auxiliaries $101 each, family $1,204; excess $6,624. June partial pool $600, NH 2/6 = $200 and each auxiliary 1/6 = $100 | `test_poms_02501_110_partial_benefit_example_2_original_shares` |
| RS 02501.110 example 3 | Partial pool $93; rates NH $117, spouse $16, children $19.90 each. Initial $37.20/$18.60 shares, spouse cap frees $2.60; NH gets $1.30 and each child $.65. Exact nets $38.50/$16/$19.25/$19.25; checks $38/$16/$19/$19 | `test_poms_02501_110_partial_benefit_example_3_capped_reapportionment` |
| Publication 05-10069, lower test | $600 monthly ($7,200 annual), $26,080 earnings, $1,600 above $24,480: $800 deduction. January-February provisionally suspended; February final check $400, repaid in 2027 | `test_publication_05_10069_current_year_suspension_and_next_year_repayment` |
| Publication 05-10069, FRA November | $68,520 January-October, $3,360 above $65,160: $1,120 deduction. At $600 monthly, January-February provisionally suspended; February final check $80, repaid in 2027 | Same test |
| Publication 05-10069 special first-year rule | Retires October 30, 2026 at 62; $45,000 before retirement, $500 monthly November/December. Both months paid as NSMs under $2,040 monthly limit. The benefit rate is unstated; test uses an invented $600 rate | `test_publication_05_10069_october_retirement_special_rule` |
| Receiving Benefits While Working, under FRA | $800 monthly, $9,600 annual, $33,400 earnings ($8,920 above $24,480), deduction $4,460; yearly benefits $5,140 | `test_receiving_benefits_while_working_examples` |
| Receiving Benefits While Working, FRA August | $72,000 annual wages, $66,000 January-July ($840 above $65,160); deduction $280. First-seven-month benefits $5,600 − $280 = $5,320; full $800 from August | Same test |
| Special Earnings Limit Rule | John Smith, age 62, retires June 30, 2026 after $37,000 wages; self-employment starts October 5 with $3,000 NESE, total $40,000. Paid July-September; substantial services make October-December chargeable and fully withheld at the invented $600 rate | `test_special_earnings_limit_john_smith_example` |
| 20 CFR 404.439 | Original benefits NH $165, spouse $82.50, total $247.50; October partial pool $200. Exact $400/3 and $200/3; checks $133/$66, total $199 | `test_cfr_404_439_original_benefit_partial_payment_example` |
| 20 CFR 404.440 | Stated maximum $150, NH excess $25, stated partial pool $125. Displayed gross rates $100/$16.60/$16.60/$16.60 total $149.80; actual dime-rate pool is $124.80. Both yield checks $75/$16/$16/$16; exact NH is $75.20 versus $75.00 | `test_cfr_404_440_dime_sum_and_printed_pool_are_pinned_side_by_side` |
| 20 CFR 404.441 | NH $176, wife $88, family $264; excesses $1,599/$265. NH has February NSM: January and March-July withheld; August partial $249 split $166/$83. Wife own deductions February $88, August $83, September $88, October $6; October check $82 | `test_cfr_404_441_number_holder_then_spouse_with_grace_month` |

Publication 05-10069's entire annual table is reproduced by
`test_publication_05_10069_annual_benefit_table`:

| Monthly benefit | Earnings $24,480 or less | Earnings $25,000 | Earnings $27,000 |
| --- | --- | --- | --- |
| $700 | $8,400 | $8,140 | $7,140 |
| $900 | $10,800 | $10,540 | $9,540 |
| $1,100 | $13,200 | $12,940 | $11,940 |

The CFR .441 source uses the historical $340 monthly limit. The test
preserves its benefits, excess amounts, charge order and partial checks
in a supported 2026 invented earnings distribution: $6,678 January, $0
February and $2,100 March-December produce the same $1,599 NH excess
under R1's 2026 limit and February as the only NH NSM. The historical
monthly limit is quoted, not substituted into a supported R1 year.

## Grace-year worked examples

These examples exercise `grace_year`; the tests quote the entire relevant
source passages, including each date and figure.

| Source and facts | Reproduced status | Test in `test_track_b_ret_grace.py` |
| --- | --- | --- |
| RS 02501.030B.1: entitlement 01/11, FRA 08/11, NSMs 06/11 and 07/11 | Initial grace 2011, June/July protected, LMETY 2011 | `test_initial_grace_2011_before_august_fra` |
| RS 02501.030B.2: mother's benefits and NSM in 2010, termination 06/10, RIB in 2011 after a break | Initial 2010; new after-break grace and LMETY 2011 | `test_mother_2010_break_then_rib_2011_has_another_grace` |
| RS 02501.030B.3: child DOB 01/20/92, age 18 in 01/10, benefits terminate 01/10 | Last entitled December 2009; termination grace 2009 | `test_january_2010_child_termination_belongs_to_2009` |
| RS 02501.030B.3: child age 16 and first NSM in 2008; termination 03/10, re-entitlement 09/10, another termination 04/11 | Initial 2008; termination graces 2010 and 2011; LMETY stays 2008 | `test_child_reentitlement_retains_2010_and_2011_termination_graces` |
| RS 02501.030B.4: concurrent RIB/DIB 06/10 at age 62, RIB elected June-December; DIB elected 01/11; RIB again 01/12 | POMS reading gives initial grace 2010 and June-December NSMs; technical entitlement preserves LMETY 2010, so no new 2012 grace | `test_simultaneous_rib_dib_elections_preserve_2010_lmety` |
| RS 02501.030C: entitlement 02/11, $40,000 earnings in 2011, June/July below the monthly limit | June/July NSMs protected | `test_retirement_2011_40000_earnings_june_july_nonservice` |
| RS 02501.030C: DIB in 2009, no work after 2008, FRA and RIB 02/11 | DIB months in 2009/2010/01/11 create no NSMs or LMETY; RIB from FRA creates none | `test_dib_2009_through_january_2011_then_fra_rib_creates_no_nsm` |
| RS 02501.030D: entitlement 2010 with annual deductions, stops work March 2011, FRA September 2011 | First initial grace and LMETY 2011; March-August NSMs protected | `test_initial_year_2011_after_full_year_work_2010` |
| RS 02501.030D: widow LMETY 2010, elects RIB in 2011 without a break | LMETY transfers unchanged; no fresh grace | `test_widow_to_rib_without_break_transfers_2010_lmety` |
| 20 CFR 404.435 example 1: Don, age 62, retires April after $15,000 January-April, part-time wages below limit after April | Initial grace, May-December paid. Year is unspecified in source; helper uses invented 2026, and monetary ledger uses 2000 so the annual excess is positive | `test_cfr_404435_don_april_retirement_initial_may_through_december`; source `test_cfr_404_435_don_initial_grace_example` |
| 20 CFR 404.435 example 2: Marion's initial mother's-benefit grace 1998; last entitlement April 2000; widow entitlement February 2001 after a gap | Termination grace 2000, LMETY stays 1998; after-break grace and LMETY 2001 when an NSM occurs | `test_cfr_404435_marion_termination_2000_widow_2001_after_gap` |

## Source findings

RS 02501.080B.2.d describes `$44,000` NESE in `2000` and FRA in June,
but its arithmetic refers to `4/99 and 5/99` and says `Since the exempt
amount is $15,500`. The correctly dated months are April/May 2000 and
the R1/CFR/POMS-chart 2000 higher annual amount is $17,000. The $9,776
countable NESE and no-deduction result reproduce under either printed
or correct limit. Both source figures remain pinned side by side;
the source was not edited to conceal the errata.

20 CFR 404.440 uses a nominal $150 maximum and says a $25 deduction
leaves $125, while its displayed dime rates total $149.80. Starting from
the printed rates leaves $124.80, which conserves ledger money. The
nominal pool gives an exact $75.20 NH partial rate; the dime pool gives
$75.00. Both produce the source's whole-dollar checks of
$75/$16/$16/$16. The test records the 20-cent difference explicitly.

RS 02501.110 example 3 supplies a $93 partial pool but no annual excess.
Constant $172.80 monthly rates would require $943.80 excess to yield
exactly $93 in June; annual excess is required to be whole dollars.
Accordingly the test reproduces the published partial-share computation
using the pure helper, without claiming a full annual ledger from facts
the source did not supply.

The CFR Marion narrative says the child's and mother's entitlements
terminated when the child turned 16. RS 02501.030B.3.b separately says:
“Failure to have an entitled “child-in-care” does not qualify the mother
or father, young wife or husband to a termination grace year since not
having a “child-in-care” causes a suspension of benefits rather than
termination.” The helper takes a legally established termination as
an input. It reproduces Marion using the source's explicit termination
fact and excludes `CHILD_IN_CARE_SUSPENSION`; it does not infer that
a child turning 16 terminates the parent's entitlement. Tests
`test_cfr_404435_marion_termination_2000_widow_2001_after_gap`,
`test_termination_excluded_causes_do_not_grant_grace`, and
`test_normal_termination_still_excludes_next_month_other_benefit` pin
the distinction.

## Needs Max's judgment

**Ruling d1418 (Max, 2026-10-12): keep the current defaults for these
readings, and reopen any one when a population target needs it.** The
computed defaults below (NESE losses floored; no non-service months during
simultaneous RIB and DIB entitlement, per 20 CFR 404.435(b)(3); own-work
protections limited to the CFR's disability-based wording) stand, and the
broader POMS deemed-entitlement reading stays refused.

The review resolved the historical monthly fractions and sub-dollar
reapportionment stop directly from the captured Act and CFR text. Those
rules are implemented above and are no longer judgment items. The
remaining money-changing readings are explicit below.

### Signed NESE: floor versus dropping cents

RS 02501.080B.2.c says: “prorate the net earnings (or loss) equally
over all months the beneficiary was engaged in self-employment”. Its
note says: “When cents are involved divide the amount by 12, then drop
the cents, then round down before multiplying by the months before
the beneficiary attains FRA.” For a negative monthly amount, “drop
the cents” supports truncation toward zero, while “round down” supports
mathematical floor. The two readings agree on the published positive
NESE examples.

`NESEProrationPolicy.FLOOR` follows the literal “round down” instruction;
`DROP_CENTS` is an explicit alternative. In an invented June FRA year,
annual NESE loss −$13 over twelve months becomes monthly −$2 and
five-month −$10 under floor, versus monthly −$1 and five-month −$5
under dropping cents. With pre-FRA wages equal to R1's higher exempt
amount plus $13, countable earnings are higher + $3 versus higher + $8;
excess is $1 versus $2. A $600 January rate produces checks $599 versus
$598. Floor pays $1 more in this loss case, so it is not described as
conservative. Tests `test_negative_nese_floor_and_drop_cents_readings_are_explicit`
and `test_negative_nese_reading_changes_final_deduction_by_one_dollar`
pin the one-dollar difference.

### Simultaneous RIB and DIB entitlement

20 CFR 404.435(b)(3) says: “we will not count as a non-service month,
a month that occurred while the beneficiary was entitled to disability
benefits under section 223 of the Social Security Act or as a disabled
widow, widower, or child under section 202.” RS 02501.030B.4 instead
says: “If the beneficiary becomes simultaneously entitled to RIB and
DIB benefits, the earnings test (ET) applies to any month they elect
to receive RIB.” It adds: “Count NSMs for any month the RIB applies.”

`DisabilityGraceReading.CFR_ENTITLEMENT_EXCLUSION` is the conservative
default: technical disability entitlement prevents those NSMs.
`POMS_RIB_ELECTION` follows the express operational exception and is
needed to reproduce the POMS 2010/2011/2012 election example. Both
preserve technical entitlement history; neither invents a break when
the elected payment changes. The grace properties and
`test_simultaneous_disability_cfr_default_and_poms_alternative_are_explicit`
pin both readings. In an invented 2026 ledger, $45,000 January wages
precede entitlement to both RIB and DIB in June. The beneficiary elects
RIB at $600 monthly June-December and has no wages or services in those
months. Under the conservative reading all $4,200 is deducted; under
the POMS reading all $4,200 is paid. Test
`test_simultaneous_dib_rib_source_readings_change_4200_dollars` executes
that money difference, and
`test_property_explicit_poms_election_protects_only_eligible_rib_months`
executes the related ledger property.

### Other own-work age clauses

Act 203(f)(1)(C) prohibits charging a month “in which such individual,
if a child entitled to child's insurance benefits, has attained the age
of 18”. Clause (D) prohibits charging a month “for which such individual
is entitled to widow's or widower's insurance benefits if such individual
became so entitled prior to attaining age 60”. The preceding sentence
expressly says “but subject to section 202(s)”. This lane has no full
capture of 202(s) and does not adjudicate that additional condition.

20 CFR 404.435(a)(5)-(6) instead list “Are age 18 or over and entitled
to a child's insurance benefit based on disability” and “Are entitled
to a widow's or widower's insurance benefit based on disability”. The
POMS payment-type exemption in RS 02501.021B.5.a also lists DIB/DWB/CDB.
The Act's express age clauses appear broader than those operational
disabled-benefit descriptions.

The automatic default exemptions therefore follow the explicit
disability types. The documented `own_work_exempt_months` parameter
defaults to empty and is the alternative Act-clause assertion: the
caller must establish lawful entitlement, the age facts and any 202(s)
condition before asserting it. The ledger validates CHILD/WIDOW types
but does not derive those exemptions silently from an inferred age.
Max must decide how monthly assembly will establish and select this
broader reading. In invented $200 monthly ordinary CHILD and WIDOW
cases, earnings equal R1's lower amount plus $1,200. Default own
deductions total $600; the explicitly asserted Act exemption pays the
additional $600. Both cases are executed by
`test_optional_act_age_exemptions_are_an_explicit_600_dollar_reading`,
with the general selected-exemption property in the invariant table.

### Broader POMS deemed entitlement

Act 203(b)(1)'s third sentence says a recipient of child's benefits who
has attained age 18, or mother's/father's benefits, “is married to an individual entitled to
old-age insurance benefits under section 202(a)”, and then deems the
benefit payable on that person's wages and self-employment income.
20 CFR 404.420 similarly says “a person who is married to an old-age
insurance beneficiary” with mother's/father's or disabled-child
benefits on a third person's record is deemed entitled on the spouse's
record. RS 02501.140 instead says: “deem a retirement beneficiary's
spouse or child entitled on their record if they are receiving CDB,
mother's or father's benefits, or child's benefits based on another
person's ER.” The POMS wording appears to reach an unmarried child
more broadly than the Act/CFR marriage requirement. The Act additionally
covers an entitled adult child without expressly requiring disability;
the CFR's stated child basis uses disability. This additional coverage
difference is refused for an ordinary CHILD even after the caller asserts
lawful age-18 and marriage facts, pending Max's reading.

The default requires `deemed_married_to_nh=True` to assert the legal
marriage facts; broader unmarried cases receive
`DEEMED_ENTITLEMENT_BASIS`, as do ordinary deemed adult CHILD cases.
No monetary answer is fabricated for a
refused configuration. The lawful married benchmark has NH $400,
deemed-entitled CDB $200 and NH excess $600; the NH charge includes
the recipient's full $200 January benefit even though CDB's own
earnings test is exempt. Applying the broader wording to an otherwise
identical unmarried recipient would likewise remove $200 from that
recipient; treating the unrelated record independently leaves it
untouched. `test_unmarried_deemed_entitlement_is_refused_pending_source_judgment`
and `test_married_deemed_disabled_child_is_charged_number_holders_excess`
pin the refusal and the statutory benchmark.
The Act's ordinary-adult-child wording would include the same $200 in
that benchmark. The CFR disability-only boundary refuses that ordinary
child case. `test_deemed_ordinary_child_requires_explicit_adult_age_facts`
pins invalid missing-age facts and the default coverage refusal with
established age facts; the married CDB benchmark pins the supported
$200 NH deduction.

### Scope wording for another deductee

The part-(a) brief asks for refusal when an auxiliary's own excess is
charged with a binding maximum “or any other deductee on the record
that month”. It also requires reproduction of 20 CFR 404.441, whose
rule expressly covers the same-month interaction: “Where both the
insured individual and another person entitled (or deemed entitled)
on the same earnings record have excess earnings”. Act 203(b)(1)
likewise charges a beneficiary's remaining benefits after an earlier
deduction, and 20 CFR 404.434(b)(3) specifies NH charging first.

This build interprets the other-deductee refusal as other deduction
events under Act 203(c)/(d)/222(b), represented by
`other_deduction_months`, which are always refused. Simultaneous NH
and auxiliary RET deductions without a binding maximum are supported
so the explicitly required CFR .441 example can be reproduced. That
example gives the wife's August $83 NH partial share, fully consumed
by her own excess, and her October $82 check. Interpreting the brief
as excluding any simultaneous RET deductee would instead refuse the
example, not produce a different computed amount. This scope reading
needs confirmation if the intended part-(a) boundary was broader.

## What part (b) needs from G

The current G entry point is:

```python
family_benefits(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    *,
    payment_month: YearMonth,
    params: SSAParameters,
    standalone: bool,
) -> FamilyBenefits
```

It computes gross rates on the assumption that no deduction event has
changed available maximum room. Part (a) uses its monthly results and
refuses deduction-before-reduction cases. No G function is changed here.

Part (b) needs an exact monthly entry point with the following proposed
contract, subject to the G lane's implementation:

```python
family_benefits_after_deductions(
    state,
    beneficiaries,
    *,
    payment_month,
    params,
    deduction_events,
    households,
    standalone,
) -> FamilyBenefits
```

It must retain G's original metadata rather than accepting only reduced
rates: `RecordState` contains PIA, family maximum, worker/RIB-LIM and
eligibility facts; each `Beneficiary` retains original-share role, age
reduction, dual-entitlement and maximum-membership facts. The R2 input
rate alone cannot recover that information.

For every deductee and month, `deduction_events` must identify the
beneficiary, reason, exact full or partial deduction and partial payable
amount, whether it is NH-wide or the beneficiary's own event, and
whether it is an estimated current-year suspension or an actual
closed-year permanent deduction. `households` must identify monthly
household membership, including any established historical configuration
needed for separate-household timing. `standalone` retains G's explicit
one-record assertion; two-record entitlement still needs the household
entry point rather than silent independent calculations.

The new function must apply Act 203(a)(4)'s first sentence and GN
02603.050C/D, including the differing permanent and temporary formula
inputs, full and partial deductee treatment, capped readjusted original
benefits and retained G age/dual-entitlement order. It must return
recomputed rates for all beneficiaries and the room released by the
deductions, preserving exact arithmetic and G's refusal and validation
contracts. R2 then charges eligible workers against the appropriate
readjusted rates in the statutory order (RS 02501.130, .155).

For separate households, increased amounts attributable to provisional
work deductions are delayed until the deductions become final, while
same-household increases can be paid sooner (RS 02501.160; GN
02603.090). The proposed contract must therefore preserve provisional
and final monthly states separately. Facility of payment itself ended
after December 1995 and is outside the supported payment years (GN
02603.075); it must not be restored from historical GN 02603.100 examples.

## Build verification

The original build's five R2 test files passed all 540 cases. Three
existing Hypothesis tests were then strengthened to check auxiliary excess accounting,
invalid-input propagation and NH charging during a child's asserted
own-work exemption; all three passed. Birth-evidence exclusion tests
passed all 13 cases. Every mathematical ledger and grace-state invariant
above has an executed Hypothesis test.

All 33 original-build deliberate one-line implementation mutations caused
a selected test to fail. Each was reverted before another check, and both modules'
restored SHA-256 values are recorded with the exact commands, changes and
failing nodes in `track_b_r2_ret_ledger_mutations.json`. Mutated
implementations are not committed. The source captures stayed unchanged.

Review fix round 1 ran all seven `test_track_b_ret_*.py` files: 738
tests passed. The four minimized historical-limit and sub-dollar
regressions failed first against the unchanged reviewed implementation,
then all four passed after the fixes. The full source file passed 290
tests, including the verbatim Act amounts and the CFR/POMS stop rules.
The exact-$1 and later-iteration stop boundaries also have named example
tests and an executed Hypothesis property. Black and Ruff passed for all
ten Python files touched by the PR. Verification admits statutory
mechanics only; no real data or population computation was used.

All seven fix-round mutations were killed, and the same targeted nodes
passed after byte restoration. They cover the monthly default, strict $1
threshold, mandatory stop, original participant count, separation of
residual from charged excess, residual reporting and signed NESE floor.
They were applied only to isolated scratch package copies whose import
paths were checked; tracked implementation bytes stayed unchanged. The
exact changes, commands, failing nodes, restored results and source hash
are in `track_b_r2_ret_ledger_fix_round_1_mutations.json`. A separate
incremental-overflow allocation implementation matched 10,000 invented
pools at zero tolerance (seed 528), including zero caps, and independently
reproduced the exactly-$1 and later-iteration hand fixtures.

Birth-evidence checks passed all 13 cases with the artifact rebuild
excluded. The five independent tier collections found 6,955 unit,
3,909 artifact, 1,346 integration-PSID, 520 legacy-reproduction and 220
PolicyEngine-oracle tests, for a total of 12,950. The tier-policy test
passed with 12,949 other tests deselected. Both microdata directory
overrides pointed to nonexistent paths during whole-suite collection.

Review fix round 2 reproduced the false later-cap fixture with explicit
`scale=1, overflow_cents=67` before correcting its expectations. The
property now covers both cap orders and pins the 66/67/68-cent boundary;
the separate simultaneous-cap regression checks every exact share,
the zero residual, the $8 pool and checks $6/$0/$1. All seven RET test
files passed 739 tests. The complete 9,900-case fixture grid also passed
at zero tolerance. Production implementation bytes stayed unchanged.

Three isolated one-line mutations each failed both the corrected
property and the new deterministic regression: ignoring child caps,
retaining capped beneficiaries' weights in the denominator and changing
the $1 stop threshold to $3. Both tests passed after each scratch copy
was restored. Black and Ruff passed for all ten PR Python files;
birth-evidence checks passed all 13 cases with the artifact rebuild
excluded. These checks use only invented cases and captured sources.

The round-2 tier recount found 6,968 unit, 3,925 artifact, 1,346
integration-PSID, 520 legacy-reproduction and 220 PolicyEngine-oracle
tests, totaling 12,979. The tier-policy test passed with 12,978 tests
deselected. Both microdata directory overrides pointed to nonexistent
paths during every whole-suite collection and the tier-policy run.

## Not in scope

No real microdata, population pipeline, behavioral response or forecast
validation is included. There is no tax-year choice procedure, fiscal
year or short-year implementation, estimate-administration interface,
foreign-work test, vocational rehabilitation adjudication or other
deduction-event computation. Claims withdrawal and changing the month
of entitlement are caller-established facts rather than a grace-year
optimization (RS 02501.070).

The ledger does not implement requested suspension prorating or
deferral, protested partial current-year withholding, two-record excess
charging, deduction before reduction, household readjustment timing,
Medicare premiums, overpayment collection, ARF calculation, DRCs,
recomputation, or monthly assembly I. It reports estimated-versus-actual
check differences and actual deduction months so later milestones can
implement their own cited rules. Axiom differentials remain diagnostics
after a pinned rule exists; this build's verification remains statutory
conformance within the stated supported scope.
