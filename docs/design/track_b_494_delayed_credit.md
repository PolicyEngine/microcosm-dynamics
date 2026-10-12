# Track B #494: statutory delayed credits beside the sealed oracle

Verification class: **statutory conformance**. Admitted scope is the
402(w) delayed-credit fraction for births from 1917, using invented claims
and captured SSA examples. No population, behavioral or forecast claim is
admitted. Registered-result reachability is a static source audit.

## Authority and implementation

Track B design revision 3, §§3.1–3.2, 5.4, 6 and 7, and Max's ruling d515
authorize a Python statutory reference. Social Security Act §202(w)(2)(A)
(42 U.S.C. 402(w)(2)(A)) counts increment months "after the month before
the month in which such individual attained retirement age" and "prior
to the month in which such individual attained age 70". Section 202(w)(6)
supplies the cohort rate. POMS RS 00615.692D tabulates monthly and annual
rates; RS 00615.692E tabulates FRA, maximum months and maximum percentages.

`ss/statutory_delayed_credit.py` follows the precedent of
`ss/statutory_aime.py`: a statutory computation lives beside an unchanged
legacy oracle. Its `delayed_credit(months_late, birth_year, params)` returns
a float fraction. For supported births it uses the window
`840 - params.fra_months(birth_year)` and computes
`min(months_late, window) / 12 * annual_rate` for a positive window.
Zero or negative delay returns `0.0` before any parameter lookup; an empty
window also returns `0.0`. Positive delay for a birth before
1917 raises `ValueError` naming 402(w)(6)(A), because the supplied schedule
does not encode that cohort's rate and a year-only FRA-to-70 window does
not encode the early historical windows in RS 00615.692E.

`DelayedCreditWindow` names the two conventions. The keyword-only
`window` argument to `oracle_delayed_credit` is required:

| Convention | Computation and intended use |
| --- | --- |
| `STATUTORY` | The new function, for new statutory work and any explicitly registered later statutory rerun |
| `LEGACY_48_MONTH_CAP` | Unchanged `ss.benefits.delayed_credit`, for paths whose registered artifacts used the legacy convention |

The legacy name describes the standard parameter bundle, whose
`max_delayed_months` is 48. Its implementation continues to honor a
caller-supplied maximum exactly as before. The statutory computation ignores
that field. Both functions use the same float arithmetic order over their
shared surface, so agreement there is exact.

`months_late` measures months from FRA to the first month of entitlement.
A claim after 70 earns the full window credit and nothing for later months
(402(w)(2)(A)). G accepts an already-counted number of increment months and
rejects more than the window as `InvalidFamilyInput`. These input conventions
intentionally differ. Both use SSA's January 2 to January 1 birth bands;
callers pass the preceding cohort year for a January 1 birthday.

## Why the sealed oracle stays unchanged

The first-estimates birth-evidence reducer seals production sources against
reviewed commit `1c7f3540`, excluding only the explicit
`POST_REVIEW_SOURCE_EXCLUSIONS`. `ss/benefits.py` and `ss/params.py` remain
byte-identical to base commit `216acab1`; the reviewed pin is not moved.
`ss/__init__.py` is also unchanged. Users import the new module directly,
as users of `statutory_aime` already do.

The new module is excluded from the source seal, with a matching exclusion
tuple and module set in `tests/estimates/test_birth_evidence_artifact.py`.
The reachability test establishes that sealed production paths do not import
it transitively. No registered caller is retargeted. The
[erratum](../errata/2026-10-11-delayed-credit-window.md) preserves the
file-and-line audit of reachable registrations and the paths outside the
changed region. First estimates, Track A COLA, FRA 68 and Track M retain
their registered legacy computations and committed results. A later
registered rerun must select `DelayedCreditWindow.STATUTORY` explicitly and
state that choice.

## Supported and refused configurations

| Configuration | Statutory function result or reason |
| --- | --- |
| Birth from 1917, positive delay within the window | Cohort annual rate times credited months / 12, in floats |
| Birth from 1917, entitlement after 70 | Credit saturates at the FRA-to-70 window |
| Any birth, zero or negative delay | `0.0`, before parameter lookup |
| Supported birth, bundle FRA at or after age 70 | `0.0` for the empty credit window |
| Birth before 1917, positive delay | `ValueError` naming `402(w)(6)(A)`; the bundle's rate and the historical window are unsupported |
| G input with excess increment months | Existing `InvalidFamilyInput` |
| G positive credits before 1917 | Existing `FamilyConfigurationUnsupported`, reason `delayed_credits_born_before_1917` |

The scalar function adds no family reason code and no denominator. G's input
errors continue to precede coverage refusals and its refusals continue to
count in every denominator. The explicit legacy convention retains the
historical computation, including its pre-1917 nonconformance; it makes no
statutory-conformance claim for those inputs.

## Sources and cohort table

The existing gross-benefit source manifest pins RS 00615.692 and the LII
402(w)(2)/(6) excerpts. No source was fetched or added. Tests recompute
capture SHA-256 and byte counts, quote the governing text verbatim, and
verify every literal table row against its capture. Shared parsers in
`tests/track_b_gross_benefit_support.py` read the E windows and D rates
independently. The open-ended chart rows can be expanded through later
cohorts for testing.

The literal table in `tests/ss/test_delayed_credit_statute.py` includes
every combined rate/FRA band from 1917 through 1960 and an explicit 1961+
row. Every row cites 402(w)(2)(A), 402(w)(6) and RS 00615.692D/E.
Tests check every birth year 1917–1962, every month from zero through the
window, and each of the 24 following months. Windows are 60 months for
1917–1937; 58, 56, 54, 52 and 50 for 1938–1942; 48 for 1943–1954; 46,
44, 42, 40 and 38 for 1955–1959; and 36 from 1960.

## Invariants and their tests

Each behavioral invariant has a Hypothesis test beside its examples.
Supported-cohort properties apply separately to every birth year
1917–1960, with deterministic and provenance properties also sampling
later cohorts. This scalar function has no aggregation or ordering surface.
Its only round-trip surface is the named convention's string value.

1. The window identity is `840 - FRA`; FRA, rate and window equal both
   captured charts and the literal statutory table.
   `test_statutory_cohort_table_matches_both_captured_charts_and_bundle`
   exhausts years 1917–1962; `test_statutory_window_and_rate_identity`
   samples those source rows and the independent literal table.
2. Within the window credit is linear at the cohort's annual rate / 12,
   within `1e-12` of the exact fraction's float representation.
   `test_every_window_month_is_linear_and_age_70_has_the_full_credit` and
   `test_credit_is_linear_within_the_full_window` execute it.
3. Credit never decreases as entitlement is delayed.
   `test_credit_is_monotone_in_entitlement_month` executes it.
4. Credit is nonnegative and bounded by the age-70 credit.
   `test_credit_is_nonnegative_and_bounded_by_the_age_70_credit` executes it.
5. Every entitlement month after the window gives the same credit.
   `test_each_of_24_months_after_age_70_keeps_the_window_credit` and
   `test_entitlement_after_age_70_preserves_the_window_credit` execute it.
6. Nonpositive delay is neutral, including for births before 1917.
   `test_nonpositive_credit_months_return_float_zero` and
   `test_nonpositive_months_are_neutral_for_every_cohort` execute it,
   including bundles with no FRA or rate schedule. An empty credit window
   is also zero before rate lookup:
   `test_an_empty_window_returns_zero_without_a_credit_rate` and
   `test_every_empty_window_is_zero_before_the_rate_lookup` execute it.
7. Supported credits do not depend on the captured maximum field.
   `test_bundle_maximum_does_not_bound_the_statutory_credit` and
   `test_credit_is_independent_of_the_bundle_maximum` execute it.
8. Identical inputs and equivalent bundles give deterministic results.
   `test_credit_is_deterministic` executes it.
9. The statutory float fraction agrees with G's exact fraction throughout
   each cohort's whole window to `1e-12`.
   `test_credit_matches_gs_exact_fraction_over_the_whole_window` uses exact
   PIA $2,400, making every possible credit a whole dollar and eliminating
   monetary rounding from the differential.
   `test_delayed_credits_match_the_statutory_float_function_over_the_whole_window`
   also checks arbitrary dime PIAs within G's one-dime rounding tolerance.
10. Positive delay before 1917 always refuses in the statutory convention.
    `test_pre_1917_positive_credit_months_refuse_the_incorrect_bundle_rate`
    exhausts births 1900–1916; `test_pre_1917_positive_months_always_refuse`
    and `test_statutory_convention_preserves_the_pre_1917_refusal` sample
    positive delays. These pass as ordinary tests, not expected failures.
11. The legacy convention is exactly the sealed
    `ss.benefits.delayed_credit` for every tested input and bundle,
    including historical births.
    `test_legacy_convention_equals_the_sealed_oracle_everywhere` and
    `test_pre_1917_legacy_nonconformance_is_preserved_by_convention`
    execute it.
12. With the standard 48-month legacy bundle, the two conventions agree
    exactly for supported delays through `min(48, window)` and, for births
    from 1943, at every delay.
    `test_conventions_agree_exactly_within_the_shared_window` and
    `test_conventions_agree_exactly_for_windows_at_most_48_months` execute
    the agreement. `test_pre_1943_conventions_differ_only_by_months_above_48`
    checks the difference, and
    `test_issue_494_differences_are_named_convention_choices` pins the three
    issue cases below.
13. Explicit convention selection dispatches to the selected function.
    `test_statutory_convention_equals_the_statutory_function` and
    `test_legacy_convention_equals_the_sealed_oracle_everywhere` execute
    it. `test_the_oracle_requires_an_explicit_window_convention` pins
    rejection of an omitted or invalid convention.
14. Serializing and reconstructing a convention's string value preserves
    its identity and results.
    `test_window_convention_string_round_trip_preserves_results` executes
    it.
15. For supported births before 1943 under the standard bundle, the
    additional statutory credit is at most `13/200` of PIA.
    `test_pre_1943_conventions_differ_only_by_months_above_48` checks this
    bound as a property; `test_the_largest_legacy_shortfall_is_1937_at_age_70`
    pins its maximum at 1937.

G's `test_delayed_credits_match_the_sealed_legacy_oracle_within_one_dime`
preserves its differential through `min(48, window)`.
`test_sealed_legacy_oracle_keeps_the_48_month_cap_issue_494` pins that
convention's intentional 1935 result. The live-bundle
`test_statutory_float_function_live_bundle_credits_every_captured_cohort_window`
checks the statutory computation when a policyengine-us parameter tree is
available.

## Worked examples and findings

RS 00615.692C gives PIA $1,000.00, birth date 06/15/1940, and 30 increment
months at 7/12 of 1 percent monthly. The increase is $175.00 and the new
amount is $1,175.00; 215(g)'s whole-dollar presentation is $1,175. Tests
reproduce the cents and whole dollar and quote the figures from the capture.
RS 00615.692C warns that its rounded decimal `.0058333` instead gives
$174.999, or $174.90 after dime flooring. The float function uses the
annual bundle rate / 12, while G computes the monthly fraction exactly;
this published example is reproduced by both.

The issue's cases are invented, with statutory rates and windows from
RS 00615.692D/E. The following fractions precede monetary rounding:

| Birth and delay | Sealed legacy fraction | Statutory fraction |
| --- | ---: | ---: |
| 1935, 60 months | 0.24 | 0.30 |
| 1938, 58 months | 0.26 | 377/1200, approximately 0.314167 |
| 1942, 50 months | 0.30 | 0.3125 |

On invented PIA $1,000, the 1935 case gives legacy $1,240.00 versus
statutory $1,300.00, and whole-dollar amounts $1,240 and $1,300. An invented
1960 birth entitled 48 months after FRA earns only its 36-month window at
8% annually, exactly 24%; both conventions give this plateau.

The largest supported-cohort difference is 6.5 percentage points of PIA
for a 1937 birth entitled at 70: 12 additional months at 6.5% annually.
On invented PIA $1,000 the credit is $260.00 under the legacy convention
and $325.00 under the statutory convention. No count of affected people,
aggregate effect or empirical result is computed.

## Parameter defect

For pre-1917 births, 402(w)(6)(A) says "1 ⁄ 12 of 1 percent" for first
eligibility before 1979; RS 00615.692D gives
"Before 01/02/17 1/12% .0008333 1%". The bundle's upstream
`policyengine_us/parameters/gov/ssa/social_security/retirement_age_adjustment/delayed_retirement/credit_rates.yaml`
instead gives births 1900–1916 3% annually. This is a parameter defect for
the orchestrator to file upstream, not an alternative statutory reading.
On invented PIA $1,000 for a 1916 birth with 48 increment months, the
legacy credit is $120.00; the statutory rate would give $40.00, an $80.00
monthly difference. The new function refuses rather than substituting an
uncaptured historical bundle; the sealed oracle keeps its registered
behavior.

## Needs Max's judgment

The captured statute and POMS agree on the supported-cohort window and
rates. No competing money-changing statutory reading is selected here.

Decision `d1408` is reserved for Max's judgment on a separately authorized
diagnostic of the registered paths. The erratum specifies the diagnostic
and the unknown population quantities. This decision does not block the
isolated statutory computation or authorize a registered rerun.

## Not in scope

Real-data diagnostics, registered reruns, edits to committed `runs/*.json`,
RET, ARF, monthly timing, suspended-benefit histories, and PolicyEngine-US
parameter edits are outside this change. The computation is a float
fraction reference; G supplies exact monetary arithmetic and dime and
whole-dollar rounding. `gates.yaml`, the engine loop, engine steps and the
birth-evidence reviewed commit remain unchanged.
