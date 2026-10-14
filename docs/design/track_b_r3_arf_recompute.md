# Track B R3: adjustment of the reduction factor and recomputation

**Verification class: statutory conformance. Build only, 2026-10-11;
review fixes 2026-10-12.**
Admitted scope is ARF credits and earnings recomputation mechanics for
supported cases. Inputs are invented histories and captured SSA examples.
There is no population, behavioral, forecast or payment-processing claim.

The governing Track B design is revision 3, approved under ruling d515,
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`.
Sections 3.1, 3.2, 5.4, 6 and 7 require separate ARF and recomputation
references, record-specific credits, preserved original computation factors,
no future earnings in earlier recomputations, and explicit unavailable
histories. Axiom comparisons remain diagnostics after a rule is pinned.

Code is `src/populace_dynamics/track_b/arf.py` and `recompute.py`. Example
and Hypothesis tests are `tests/test_track_b_arf.py`,
`tests/test_track_b_arf_properties.py`, `tests/test_track_b_recompute.py`
and `tests/test_track_b_recompute_properties.py`. Source integrity and
verbatim quotations are in `tests/test_track_b_r3_sources.py`.

## Statutory order

R2 supplies final full or partial work-deduction months for each benefit
record. R3 takes iterables of `YearMonth` or `(year, month)` values and
imports no R2 implementation. Provisional or prorated suspensions are not
final deduction months. Credits are a union, so overlapping categories
credit a month once. Only original reduction-window months count
(42 U.S.C. 402(q)(6)-(7); RS 00615.482).

Every iterable field in an ARF claim is snapshotted once at construction
into a tuple or frozenset. Month contents and condition types are still
validated before any coverage refusal. An ARF result freezes its crediting
months, and a recomputation basis freezes its conditions at construction;
its bend points require a tuple. Neither evaluating the original claim nor
inspecting a result can consume credits or erase an exceptional-history
refusal. Iterator and immutable-set inputs have exactly the same supported
results and refusal reasons. This implements deterministic record-specific
credits and retention of unsupported rows under design sections 6 and 7.

ARF input validation first rejects non-finite numeric statutory-rate,
benefit-share and bracket values, including NaN and either infinity, with
`ValueError`. It then calls G's unmodified `statutory_rates` to check the
complete shared rate bundle, including the RIB and spouse rates and their
36-month brackets (402(q)(1)(A); 20 CFR 404.410; RS 00615.101, .201).
A mismatched finite bundle retains G's original `ValueError`. Both errors
precede any explicit or automatic coverage refusal and benefit arithmetic,
and propagate through `apply_arf`, `evaluate_arf` and lazy inputs to
`count_arf_outcomes`; no unsupported outcome or denominator is constructed
for the invalid row. Valid coverage refusals still precede benefit
arithmetic. Recomputation uses a separate parameter surface: required NAWI
and contribution bases are already checked for finite positive values
before coverage; ARF age-reduction rates and benefit shares are not inputs
to its original 90/32/15-percent formula (415(a)(1), (f)(2)(C)).

ARF applies at FRA for RIB and spouses. Ordinary widow adjustments apply at
age 62 and again at widow FRA; credits recognized at 62 persist until FRA,
without adding intervening credits early (402(q)(1)(B)(ii); 20 CFR
404.412(b); RS 00615.490, .580, .582). SSA attains age the day before a
birthday, so a first-day birth attains FRA in the previous month. January 1
also belongs to the preceding birth-year cohort (RS 00615.003, .004, .015).
Initial RIB at 62 has the separate throughout-the-month requirement.

Reduction is recalculated on the current COLA-increased unreduced amount,
already adjusted for any family maximum. G's `worker_reduction_fraction`,
`spouse_reduction_fraction`, `survivor_reduction_fraction`, `ceil_dime`,
`floor_dime` and `whole_dollars` are reused. RIB uses 5/9 of one percent for
36 months and 5/12 thereafter; spouse uses 25/36 and 5/12; widow reduction
spreads 28.5 percent across the cohort's full reduction period. The money
reduction rounds upward to a dime, then the benefit rounds downward to a
whole dollar separately (402(q)(8)-(9); RS 00615.101, .201, .301).

When own entitlement starts after completed spouse ARF, retain the single
spouse adjustment and subtract the supplied independently adjusted own
payment, bounded below by zero (402(k)(3)(A); RS 00615.500A.1). Own PIA
and payable may differ, including because of delayed retirement credits.
Varying own PIA with that payment fixed leaves this spouse component
unchanged. Reapplication retains the supplied payment. Concurrent or
preceding own entitlement uses the excess over own PIA under .500A.2.

Recomputation extends computation base years through the earnings year,
while preserving the original indexing year, computation-year count and
eligibility-year bend points (415(f)(2)(B)-(C); CFR 404.281, .284). Every
base year from 1951 through that cutoff must have an explicit nonnegative
amount, including explicit zero. A missing key or `UNAVAILABLE` raises
`InvalidFamilyInput` before any coverage refusal. Later amount values are
not read. The adapter calls `ss.statutory_aime.aime_with_computation_years`
and guards its integer floor with exact Fraction indexing and selection.
The original ordinary RIB computation-year count must be consistent with
its eligibility cohort; R3 preserves it rather than recomputing it using
the later earnings year (415(b)(2), (f)(2)(C)). Original insured status and
entitlement are supplied as established facts; earnings arithmetic does
not verify insured status or quarters of coverage. Low-level arbitrary
computation counts and synthetic parameters are formula diagnostics, not
complete claimant cases.

Required NAWI and contribution-base availability, positivity and finite
values are validated separately from AIME capping, indexing and selection.
Complete earnings and COLA histories and all required parameters are checked
before coverage. Coverage refusals precede any ordinary AIME or PIA
calculation (415(f)(2)(B)-(C); CFR 404.283-.284). An annual sequence validates
every required year through its last cutoff before its first refusal,
without calculating AIME. Unsupported formulas retain their named reason
and produce no ordinary candidate; invalid required inputs still raise
`InvalidFamilyInput` rather than being counted as coverage gaps.

PIA is the exact 90/32/15-percent formula, floored to a dime. Original bend
points are $180 and $1,085 scaled by NAWI, with half-dollar ties upward
(415(a)(1)(B); G's RS 00605.900 capture). December COLAs from the
eligibility year through the effective month are applied one by one,
flooring each increase to a dime (415(i); existing G capture). A complete
COLA history must report zero increases explicitly. The $1 rule compares
actual dime PIAs after those COLAs; whole-dollar check amounts and
eligibility-level differences cannot substitute (415(f)(4); RS 00605.501).

An ordinary recomputation takes effect in January after the earnings year.
Death-year earnings take effect in the death month when death is at or
after FRA. The alternative death-before-FRA computation in 415(f)(5) is
refused (415(f)(2)(D); CFR 404.282; RS 00605.401). December processing in
Publication 05-10069 is distinct from January statutory effectiveness.
A sequence carries only accepted eligibility-level PIAs forward. A sub-$1
candidate remains pending; later positive earnings can produce an increase
against the PIA then in force. A year with zero earnings cannot trigger
reconsideration solely because additional COLAs have accrued (RS 00605.501).

## Supported and refused configurations

All refusals carry `FAMILY_CONFIG_UNSUPPORTED` and a named reason. Invalid
inputs raise first. Both modules retain refused rows and weights through
G's denominator counter. A recomputed PIA aggregate is blocked if any
required row is refused. No refused family is replaced by a worker-only
case or removed from a denominator.

| Configuration | Treatment and authority |
| --- | --- |
| Modern single RIB, spouse or ordinary widow ARF | Supported for original entitlement from January 1978 and payment months from January 1983; 402(q)(10), RS 00615.490 |
| Full or partial final work deduction | One full credit per qualifying month, separately per record; RS 00615.482 |
| Spouse child in care and terminating-event months | Explicit certified months supported at FRA; 402(q)(7)(B)-(C) |
| RIB simultaneously entitled to DIB | Explicit months supported as credits; 402(q)(7)(F), CFR 404.412(a)(6) |
| Widow terminating-event and actual mother/father-rate months | Explicit certified months supported; 402(q)(7)(D)-(E), RS 00615.482 |
| Spouse own RIB/DIB concurrent or preceding | Reduction applied to excess over own PIA; independently adjusted own amount supplied; RS 00615.500 |
| Own benefit first entitled after completed spouse ARF | Single spouse ARF retained, independently computed own payment offset; RS 00615.500A.1 |
| Deceased RIB number holder | Hypothetical adjustment at would-have-been FRA, final RIB deductions before death month; RS 00615.598. The result is a survivor-limit component, never payment to the deceased |
| Ordinary AIME RIB recomputation | Supported eligibility from 1983, complete original basis and histories, continuous declared entitlement; 415(f)(2), CFR 404.284 |
| Death-year recomputation at or after FRA | Supported, effective death month, COLAs cut off at that month; 415(f)(2)(D)(ii) |
| Earlier reentitled spouse adjustment | `arf_spouse_reentitlement_before_fra`; RS 00615.201A.1 conflicts with RS 00615.491A on whether nonentitlement months are removed at FRA or on earlier reentitlement. Both readings are quoted below. A known prior terminating month automatically triggers this refusal before FRA; neither reading is silently admitted |
| Own entitlement after spouse but before ARF | `arf_spouse_own_after_spouse_before_arf`; sequence not settled by the captured .500 procedures |
| Disabled widow and widow dual DIB or RIB | `arf_disabled_widow`, `arf_widow_dual_dib`, `arf_widow_dual_rib`; .590/.595 conversion and earlier reduction histories require additional state |
| RIB-LIM widow | `arf_widow_rib_limit`; .585 requires its separate cap and sometimes no increase despite ARF |
| Nonbinding widow child-in-care floor | `arf_widow_child_care_without_rate_increase`; conflicting readings below |
| Historical widow FRA | `arf_widow_fra_before_1911` or `arf_historical_widow_fra_conflict`; old FRA 62 lies outside G's survivor surface; disputed 1911 cohort below |
| Historical ARF rounding or other suspensions | `arf_initial_entitlement_before_1978`, `arf_payment_before_1983`, `arf_other_suspension`; historical reduction-ratio/rounding rules and nonwork suspensions require separate procedures |
| Historical recomputation eligibility | `recompute_eligibility_before_1983`; CFR .284's historical upward rounding differs from the shared modern helpers |
| AMW, old-start, special/frozen minimum or guarantee PIA | `recompute_non_aime_formula_pia`; CFR .283/.284(f), RS 00605.501D |
| DIB, disability freeze or prior DIB | `recompute_disability_entitlement`, `recompute_disability_freeze`, `recompute_prior_disability`; additional indexing/count, conversion and guarantee rules not implemented |
| WEP for months before 2024 | `recompute_wep_before_2024`; RS 00605.501B.2, CFR .288 |
| Administrative finality or corrections | `recompute_administrative_finality`; RS 00605.405/.580 distinguish a correct new computation from reopening/recalculation |
| Waived or disadvantageous recomputation | `recompute_waived_or_disadvantageous`; CFR .287, RS 00605.407. A higher PIA does not prove higher total family payment |
| Special earnings credits | `recompute_special_earnings_credits`; 415(f)(6) requires additional evidence |
| Death before FRA | `recompute_death_before_fra_415f5`; separate formula under 415(f)(5). Missing FRA is an input error |

## Executed invariants

Each row has a Hypothesis property test beside the example tests.

| Invariant | Property test |
| --- | --- |
| ARF is idempotent, deterministic and retains the original claim | `test_arf_is_idempotent_deterministic_and_preserves_original_claim` |
| Repeated evaluation of any supported or refused iterator ARF claim preserves results, reasons and denominator weights; result credits remain immutable on repeated inspection; immutable-set and iterator inputs agree exactly | `test_iterator_claim_evaluation_preserves_results_and_refusals` |
| Adjusted months + distinct credits = original months; credits are bounded and only original-window months count; input order does not matter | `test_credit_bounds_window_and_order_independence` |
| More credits never lower the nominal benefit factor, dime benefit or whole-dollar benefit; the factor is nonincreasing in adjusted months | `test_more_credits_never_lower_benefit_or_nominal_factor` |
| A partial deduction counts as a full month; duplicate full/partial inputs never double credit | `test_partial_deduction_equals_full_credit_and_duplicate_categories_do_not_add` |
| RIB and spouse credits do not apply before FRA | `test_no_rib_or_spouse_adjustment_before_fra` |
| Widow age-62 credits persist; intervening credits wait for FRA | `test_widow_age62_freezes_credits_until_fra` |
| Zero credits preserve G's benefit; benefits are dime multiples in [0, unreduced amount], factors in [0, 1] | `test_zero_credits_matches_g_exactly_and_remaining_months_differential` |
| FRA follows the original cohort schedule and SSA day-before-birthday calendar | `test_fra_calendar_differential_with_original_cohort_schedule` |
| Invalid age inputs remain errors even with an exceptional-history refusal flag | `test_invalid_age_precedes_any_disabled_widow_coverage_refusal` |
| G's statutory parameter errors propagate unchanged before explicit and automatic ARF refusals through application, evaluation and counting; invalid inputs never become unsupported rows | `test_invalid_statutory_parameters_never_become_arf_refusals` |
| Non-finite numeric rates, shares and brackets raise the same input error through application, evaluation and lazy counting, before ordinary arithmetic or explicit and automatic coverage refusals; invalid rows produce neither an ARF result nor an unsupported outcome | `test_nonfinite_statutory_fields_never_create_arf_results_or_refusals` |
| After completed spouse ARF, the benefit is the nonnegative excess of G's exact adjusted spouse amount over supplied own payable; own PIA changes alone do not affect it, whole dollars floor that excess, and reapplication preserves it | `test_post_arf_own_payable_offset_is_independent_of_pia_and_idempotent` |
| Every ARF row and its weight remains in the denominator | `test_refusal_denominator_keeps_every_weight` |
| Original indexing, computation count and per-year caps match an independent Fraction reference; later NAWI cannot change earlier indexing | `test_original_index_count_and_caps_against_independent_fraction_reference` |
| Original ordinary computation-year count agrees with the statutory count and stays frozen | `test_frozen_ordinary_year_count_matches_original_statutory_count` |
| Exact PIA agrees with the float oracle within $0.000000001 on its shared formula/bend-point surface | `test_exact_pia_matches_float_oracle_to_one_nanodollar` |
| Complete integer histories agree with reused statutory AIME on the shared integer surface | `test_complete_integer_aime_matches_reused_statutory_oracle` |
| Ordinary PIA never decreases even when the candidate is lower | `test_ordinary_recomputed_pia_never_decreases` |
| A chronological annual fold equals individual steps and is nondecreasing | `test_annual_fold_is_non_decreasing_and_matches_individual_steps` |
| Later earnings, including later unavailable values, never alter earlier results | `test_later_earnings_never_change_earlier_results` |
| Earnings are capped per year before indexing and selection | `test_aime_caps_each_year_before_selection` |
| Every year from 1951 through the cutoff requires explicit availability | `test_every_statutory_base_year_requires_explicit_availability` |
| An absent or unavailable base year never becomes zero | `test_unavailable_year_never_becomes_zero` |
| PIA is nonnegative, monotone in AIME and a dime multiple | `test_pia_is_dime_multiple_monotone_and_nonnegative` |
| Application is equivalent to positive earnings and at least $1 after COLAs; rejected candidates preserve the PIA | `test_dollar_rule_exact_equivalence` |
| Earnings map order does not change results; repeated evaluation is deterministic | `test_earnings_mapping_order_independent_and_deterministic` |
| Iterator conditions in a recomputation basis preserve repeated supported results and refused outcomes, with every weight retained | `test_iterator_conditions_preserve_repeated_results_and_outcomes` |
| Every recomputation coverage refusal precedes ordinary AIME/PIA arithmetic, in annual calls and sequences | `test_all_coverage_refusals_precede_ordinary_arithmetic` |
| Invalid required NAWI and contribution bases raise before any coverage refusal or ordinary arithmetic | `test_invalid_required_parameters_precede_refusal_without_arithmetic` |
| An invalid original ordinary computation count raises before a later death-before-FRA refusal in a sequence | `test_invalid_original_count_precedes_sequence_death_refusal` |
| Refusals retain every row and weight and block a PIA target | `test_refusals_retained_in_weighted_denominator` |
| Invalid histories are never counted as coverage gaps | `test_input_error_is_never_classified_as_coverage` |
| Death-month effectiveness excludes later COLAs | `test_death_effective_month_excludes_later_cola` |

Exact ARF comparisons against G have zero tolerance. Published-source
parameters are reused rather than fit. Deliberate rule mutations and their
failing tests are recorded in the completion report.

## Worked examples

Publication 05-10069 starts with PIA $1,300, FRA 67, claim age 62 and 60
reduction months: 30 percent reduction, $390, gives $910. Twelve crediting
months leave 48 months: 25 percent reduction, $325, gives $975. All 60
months credited give $1,300. Dime values are $910.00/$975.00/$1,300.00;
whole-dollar benefits are 910/975/1300. RS 00615.480-.598 contains no numeric
ARF worked examples, so the other ARF combinations are invented cases.

Two invented post-ARF own-entitlement cases distinguish own PIA from own
payable under RS 00615.500A.1. Both use birth January 2, 1960, first spouse
entitlement January 2022, no credits and payment January 2028: 60 RF gives
a 35-percent reduction. Unreduced spouse amount $26.20 has reduction
$9.17 rounded up to $9.20, leaving $17.00. Own PIA $15.00 with independently
adjusted own payable $15.10 leaves $1.90 and whole-dollar $1; using the
PIA as offset would instead give $2.00/$2. Unreduced $650.00 has reduction
$227.50 and adjusted spouse amount $422.50. Own PIA $200.00 and payable
$208.00 leave $214.50/$214; a PIA offset would give $222.50/$222. Both
cases and repeated application are pinned by
`test_own_entitlement_after_spouse_arf_offsets_own_payable_not_pia`. Their
figures are invented diagnostics, not published worked-example figures.

RS 00615.015 contains twelve birthday cases. Intermediate dime benefits
below are derived exactly; the source prints whole-dollar payments.

| Birth date | First month | PIA | Reduction months | Exact benefit | Whole dollars |
| --- | --- | ---: | ---: | ---: | ---: |
| 1935-05-31 | 1997-06 | 1207 | 35 | 972.30 | 972 |
| 1935-06-01 | 1997-06 | 1207 | 35 | 972.30 | 972 |
| 1935-06-02 | 1997-06 | 1207 | 36 | 965.60 | 965 |
| 1935-06-03 | 1997-07 | 1207 | 35 | 972.30 | 972 |
| 1935-12-31 | 1998-01 | 1232 | 35 | 992.40 | 992 |
| 1936-01-01 | 1998-01 | 1232 | 35 | 992.40 | 992 |
| 1936-01-02 | 1998-01 | 1266 | 36 | 1012.80 | 1012 |
| 1936-01-03 | 1998-02 | 1266 | 35 | 1019.80 | 1019 |
| 1937-12-31 | 2000-01 | 1372 | 35 | 1105.20 | 1105 |
| 1938-01-01 | 2000-01 | 1372 | 35 | 1105.20 | 1105 |
| 1938-01-02 | 2000-01 | 1410 | 38 | 1116.20 | 1116 |
| 1938-01-03 | 2000-02 | 1410 | 37 | 1122.10 | 1122 |

RS 00605.501's PIA-only examples are reproduced at the threshold interface,
because SSA supplies no earnings histories. $849.40 to $850.00 is only
$0.60 and is refused despite a whole-dollar increase; $850.40 meets $1.
The $445.50 December 1997 PIA with a $0.90 January 1998 increase remains
$445.50. December 1998's PIA is $451.20, and a $452.20 January 1999
candidate is accepted if there were 1998 earnings; without earnings it
remains $451.20. The inferred first candidate is $446.40.

An invented complete 35-year case has original AIME 100 and PIA $90.00.
Adding $420 earnings produces AIME 101 and $90.90, which is refused;
another $420 produces AIME 102 and $91.80, accepted against the PIA still
in force. With a 12-percent accrued COLA, $90.00/$90.90 become
$100.80/$101.80, so the $0.90 eligibility increase meets the actual $1 rule.
Other invented cases write every intermediate figure in their test
docstrings, including preserved 2020 bend points $960/$5,785 versus later
2021 points $996/$6,002 (AIME 1000: $876.80 versus $897.60).

CFR 404.284's 1979 example uses historical upward dime rounding. AIME 911
has raw PIA $395.92, rounded to $396.00; successive historical COLAs
9.9/14.3/11.2 percent give $435.30/$497.60/$553.40. These historical
arithmetic figures are pinned beside the modern API's explicit refusal.
The derived whole-dollar original is 432; the successive revised amounts
are 435/497/553, each explicitly asserted.
The legacy average-monthly-wage (AMW) example replaces $2,700 with $12,000,
giving $142,000 total versus the derived prior $132,700. Divisor 22*12=264
gives AMW $537 versus earlier $502, with supplied table PIA $407.70.
Historical COLAs give $448.10, $512.20 and
$569.60. Its initial $429.20 and table row are source-supplied inputs;
the captured material does not include the AMW table needed to
derive them. The modern API explicitly refuses that formula. The supplied initial
$429.20 is $21.50 above the $407.70 candidate. Applying the same historical
COLAs to the initial value produces $471.70/$539.20/$599.60, versus
$448.10/$512.20/$569.60 for the candidate. That is a $30.00 decrease by
June 1981, rather than an effective $1 increase. Tests preserve this
unexplained captured-source inconsistency side by side; no figure is
changed and no complete accepted recomputation is claimed. The captures
cannot settle whether the initial figure, table row or stated assumptions
need correction.
Tests also assert the derived whole-dollar amounts: 429 initially,
448/512/569 for the candidate and 471/539/599 for the original after COLAs.

## Findings and readings requiring judgment

**Ruling d1418 (Max, 2026-10-12): keep the current defaults, and reopen any
one when a population target needs it.** The three readings below that
change money (survivor FRA for births 1911-01-02 to 1912-01-01, nonbinding
widow(er) child-in-care credits, and the timing of a reentitled spouse's
termination credits) stay refused by name and counted in denominators.

RS 00615.015 says "In 2/1998 Demi has 37 RF." Its table and the same
example's payment text say "Demi - $1122 starting 2/2000". Tests pin both;
February 2000 produces the stated 37 months and $1,122.10/$1,122. This is a
source date erratum, not an altered monetary rule.

The reused float AIME floors zero for cent earnings $0.02, $2.07 and
$33.91 over three computation years: binary summation is
35.99999999999999 instead of exact $36. The exact guard yields AIME 1.
The executed counterexample was minimized over cent amounts; no two-year
cent-valued example summing $24 was found. This intended oracle divergence
is named `test_minimized_cent_earnings_float_aime_boundary_is_intended_correction`.
Python's ties-to-even bend-point rounding also differs from the statute at
an exact half dollar; the named tie test pins the statutory upward result.
These are arithmetic diagnostics, not competing statutory interpretations.

Three source readings change money and require Max's judgment:

1. **Historical widow cohort.** Source conflict
   `us:oasdi-survivor-fra-1911-births`. RS 00615.003 says "People Born Before
   1/2/1911" and "FRA for widow(er)'s benefits was age 62", then "People
   Born from 1/2/1911 Through 1/1/40" at age 65. CFR 404.409 says "Before
   1/2/1912 62 years." and "1/2/1912—1/1/1940 65 years." Births
   January 2, 1911 through January 1, 1912 are refused, including the
   public FRA helper. An invented January 2, 1911 birth claiming January
   1973 with PIA $1,000 gives $829 under FRA 65 (36/60 of 28.5 percent)
   versus $1,000 under FRA 62: $171 per month. Neither reading is silently
   admitted.
2. **Nonbinding widow child-in-care floor.** Source conflict
   `us:oasdi-arf-widow-child-in-care-credits`. CFR 404.412(a)(4) credits
   "any month in which she or he had in her or his care a child of the
   deceased insured individual and for which the child was entitled to
   child's benefits". RS 00615.482 instead specifies "widow(er)'s
   benefits were increased to the mother or father's rate." The Act
   402(q)(7)(D) refers to "any month in which the reduction in the amount
   of such benefit was determined under paragraph (5)(D)". The supported
   input certifies actual mother/father-rate months. Nonbinding caregiving
   histories require the named refusal flag. At age 64, FRA 67, PIA $1,000,
   36/84 of 28.5 percent gives $877.80. Crediting six nonbinding caregiving
   months under the broader CFR reading gives $898.20: $20.40 per month.
   Both counterfactual amounts and the explicit refusal are tested.
3. **Spouse reentitlement before FRA.** Source conflict
   `us:oasdi-arf-spouse-reentitlement-credits`. RS 00615.201A.1 says "After
   12/72 a spouse reentitled prior to FRA as a spouse on the same earnings
   is reduced the same number of months as the earlier entitlement. An
   ARF at FRA will remove all months of nonentitlement." RS 00615.491A
   says "Beginning in 1/78, if a reduced spouse is terminated and then
   reentitled, (months in which the spouse's benefits were terminated will
   be eliminated from the reduction factor when the spouse is reentitled."
   The unmatched parenthesis is present in the captured .491 text. The
   first reading keeps the original reduction months until FRA; the second
   removes terminated months on reentitlement. For an invented birth on
   January 2, 1960, first reduced entitlement in January 2022, termination
   in February 2022 and reentitlement in March 2022, unreduced benefit
   $650 and FRA in January 2027 give 60 original reduction months.
   Keeping all 60 under .201 gives $422.50 and whole-dollar $422.
   Removing February under .491 leaves 59 months and gives $425.20 and
   whole-dollar $425, a $2.70 monthly benefit difference and $3 difference
   after whole-dollar rounding. The named refusal
   `arf_spouse_reentitlement_before_fra` remains in force for the March
   2022 claim. Both counterfactual amounts and the refusal are pinned by
   `test_spouse_reentitlement_counterfactual_readings_keep_named_refusal`;
   the source and documentation quote test keeps both readings visible.

The $1-after-COLAs rule is settled expressly by RS 00605.501. Historical
upward rounding is different law, not a source erratum. No choice between
these rules is left implicit.

## Monthly assembly inputs

I must supply original benefit-record identity, benefit kind, exact date of
birth, original reduced-entitlement/election month, certified final work
deductions separated from provisional suspensions, and explicit category
credits. It must declare exceptional histories, maintain complete dated
entitlement and termination state, apply any current child-in-care payment
floor separately, and adjust the spouse's own benefit independently. For a
deceased worker it supplies date of death; hypothetical ARF does not imply
payment in or after the death month.

Recomputation needs the established eligibility year, original indexing
year and computation count, original bend points, eligibility-level PIA in
force, complete annual earnings from 1951 with unavailable years marked,
annual December COLA percentages including explicit zeros, entitlement
window, and death/FRA months. I supplies the earnings-year cutoff and must
retain each result's effective date. Death-year annual earnings may include
amounts paid after death (CFR 404.282); this is retrospective statutory
recomputation, not permission to use later-year earnings early.

Both modules are added to the historical birth-evidence exclusions and the
matching disjointness test. They remain opt-in references and are not
reachable from the frozen historical projection.

## Not in scope

No real microdata, population pipeline, claiming behavior, forecast,
monthly calendar assembly, final deduction calculation, automatic SSA
notices, processing-payment dates, family-payment monotonicity, disability
freeze or conversion machinery, AMW, old-start, guarantee and minimum formulas,
reopening, judicial review, death-before-FRA alternative computation, or
unsupported widow/spouse histories are admitted. Refusals block dependent
results until a separately sourced implementation exists.
