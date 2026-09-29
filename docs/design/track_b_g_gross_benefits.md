# Track B G: the gross-benefit layer

**Status: build-only, 2026-09-29. No real-data computation.** Inputs are
invented families and SSA's published worked examples.

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
    boundaries and refusals.
  - `tests/test_track_b_gross_benefits_properties.py` holds the Hypothesis
    invariants and the float-oracle differential.
  - `tests/test_track_b_gross_benefits_oracle.py` checks the policyengine-us
    bundle.
- Sources: `tests/data/track_b/gross_benefit_sources/` (the manifest pins URLs,
  UTC retrieval times, bytes and SHA-256).

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
     150% PIA), floored to the dime.
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
   - Aged spouses whose own benefit came first use method C (402(q)(3)(B)/(C);
     RS 00615.250). Delayed credits on the own RIB follow RS 00615.694.
   - Widow(er)s use method B: both benefits are reduced independently
     (RS 00615.020A.3).
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
then used as exact fractions. NAWI and the 402(w) credit schedule come from
that bundle.

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
| `combined_family_maximum` | A child entitled on another record (403(a)(3)(A)) |
| `deemed_or_putative_spouse` | 403(a)(3)(D) |
| `parent_benefit` | 402(h) |
| `disabled_widow_under_60` | Disabled widow(er)'s benefits before 60 |
| `dib_guarantee_pia` | RS 00615.736B.2, .738 |
| `dib_after_reduced_rib` | 402(q)(2) |
| `workers_compensation_offset` | Section 224 |
| `government_pension_offset` | 202(k)(5) |
| `administrative_finality` | Protected rates (RS 00615.754A.3) |
| `dual_entitlement_sequence` | Spouse B-then-A (method B), widow(er) with DIB, widow(er) born before 1929 |
| `parisi_redistribution_ambiguous` | The "payable before any age reduction" amount has two readings |
| `parisi_before_october_1999` | A binding maximum with dual entitlement before 10/99 |

`evaluate_family` and `count_family_outcomes` keep unsupported rows in every
denominator, by reason and weight. `weighted_record_total` and
`weighted_mean_record_total` raise `FamilyTargetBlocked` rather than drop them.
Invalid inputs raise `InvalidFamilyInput`; they are errors, not coverage gaps,
and are never absorbed as unsupported rows.

## Invariants (all executed as property tests)

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
   auxiliary amount is never negative. Under method B and for unreduced
   auxiliaries, the person receives the larger of the two benefits.
6. **Unsupported configurations always raise**, including when injected
   anywhere in a valid family, and the denominators always keep them.
7. **Results are deterministic and independent of beneficiary order.** Every
   amount is a dime multiple, and each whole-dollar payment is the floor of its
   amount.

## Worked examples reproduced exactly

| Source | Case |
| --- | --- |
| RS 00615.756 | $138.00 and $103.50 each, with 7 children (FMAX $862.60); the windexed widow and child, $260.70 / $189.20 |
| RS 00615.710 | Widow DRCs share the maximum: $404.20 / $295.70 |
| RS 00615.682 | $101.90 each; then the surviving divorced spouse at $145.70, outside the maximum, and children capped at $152.90 |
| RS 00615.768 | Examples 1 and 2 (the Parisi rule): $125.00 each; $30 / $270 |
| RS 00615.320 | RIB-LIM $350, with the $309.20 floor |
| RS 00615.694 | Spouse payment $290 after delayed credits on the own RIB |
| RS 00615.005, .101, .201, .301, .692 | $780.50 (not $780.40); every chart fraction; $819.60; $1,175 |
| RS 00615.736 | Unrounded $659.02 / $647.89 / $625.23 / $759.238, and the pre-1982 round-up that is refused |
| RS 00605.900, .910 | All bend points and chart constants, 1979-2026 |
| OACT family maximum | 2026 bend points from NAWI(2024) |
| SSB 75(3) | Tables 1, 2, A-1, A-2 (dollar presentation rounding) |

## Findings recorded along the way

- **Source erratum.** RS 00605.910 prints `899.52` for 1981's third constant.
  The statute gives `889.52`, and RS 00615.736's 1981 example agrees with the
  statute. The test pins both figures.
- **The float oracle is off by a dime about 3.5 percent of the time.** The
  existing `ss.benefits.early_reduction` uses policyengine-us's decimal
  `0.00555556`, and `estimates.ledgers.floor_to_dime`, applied to that
  product, lands a dime low in 11,685 of 334,320 (PIA, reduction-month) cells
  tried. POMS's own example is one of them ($802.80 over 5 months gives
  $780.40, not $780.50). G uses exact fractions and pins this example. The
  sealed ledger is not edited here.
- **No Axiom differential yet.** rulespec-us at `83abd9ece` (origin/main,
  2026-09-29) has no `us/statutes/42/403` encoding. Its 402(a)/(q)/(w) and
  415(a)/(b)/(i) encodings do not cover the maximum. Per d515 the
  differential waits for a pinned rule and stays diagnostic when it comes.

## Not in scope

- RET deductions and their ordering against the maximum (403(a)(4) first
  sentence) are R2's.
- ARF and recomputation are R3's.
- Monthly timing and event journals are I's.
- No population, behavioral or forecast claim is admitted.
- `engine/loop.py`, `engine/steps.py`, `gates.yaml` and committed `runs/` are
  untouched.
