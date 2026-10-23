# Track B insured status and quarters of coverage

Verification class: **statutory conformance**. Version: `track-b-insured-v1`.
Admitted scope: invented declarations and published statutory examples only.
There is no population, behavioral, claiming-hazard, or forecast claim.
The governing reference is Act sections 213, 214, 216(i), 223(c)(1),
20 CFR part 404 subpart B, and POMS RS 00301. Sources are captured under
`tests/data/track_b/insured_status_sources/`; the example registry explicitly
separates reproduced computations from refused and unavailable examples.

## Interface for B6a, OP8(d), and OP12

The public module is `populace_dynamics.track_b.insured_status`.
B6a calls `insured_status(..., test=InsuredTest.FULLY)` for a person-month
risk set. OP8(d) uses the same call with explicitly declared pre-entry years;
OP12 supplies `coverage_end_month`. There is no projection-entry input and
no chosen pre-entry convention. Missing years are input errors, not zeros.

```python
insured_status(
    person: Person,
    years: Mapping[int, CoverageYear],
    month: date,
    *,
    test: InsuredTest = InsuredTest.ALL,
    coverage_end_month: date | None = None,
    totalization_credits: tuple[str, ...] = (),
) -> InsuredStatus

fully_insured_requirement(person: Person, month: date) -> int
qc_amount_from_nawi(nawi: Fraction, prior_amount: int) -> int
evaluate_insured_status(
    key: str, weight: Fraction, compute: Callable[[], InsuredStatus]
) -> InsuredOutcome
```

Months are exact `datetime.date` values with day 1. Dates of birth, death,
onset, and disability-period boundaries retain their actual days. Age is
attained on the day before the birthday (404.102). Integer quarter IDs in
windows and assignments are `4 * year + quarter - 1`, with quarter 1–4.
Status at a hypothetical entitlement/onset month takes effect on the first
day of its calendar quarter; it can cease at the next quarter boundary or
at January's change in the fully insured requirement. This is an insured
status calculation, not entitlement, medical disability, or a payment.
Currently insured uses the supplied death date, RIB entitlement month,
or most recent DIB entitlement month when available; any qualifying event
suffices. With none supplied it tests a hypothetical event in the query
quarter (214(b); RS 00301.110). Actual event dates are retained in later
queries; an emigrant with no entitlement event continues on the query clock.
Only disability periods ending before a historical event are prior periods
for its13-quarter window; the event’s own later-ending period is not excluded.

`Person` declares `birth_date`, optional `sex` (`Sex.MALE` or `Sex.FEMALE`,
required for pre-January-2-1913 cohorts), optional `death_date`, optional
`disability_onset`, ordered `prior_disability_periods`,
`statutory_blindness`, membership `conditions`, `alien_worker`, and optional
`ssn_assignment_date`, Boolean `ssn_never_assigned` (default `False`), and optional
`rib_entitlement_month` and `dib_entitlement_month` (the most recent DIB
entitlement). Supplied entitlement months must be within the lifetime and
no later than the query. An SSN assignment cannot precede birth. An alien
worker must declare either an assignment date or `ssn_never_assigned=True`;
supplying both is an input error. Never-assigned alien workers and those
whose first assignment was on or after January 1, 2004 receive the named
SSPA 211 refusal (RS 00301.102); missing SSN facts do not silently imply
that the additional requirement is satisfied.
A `DisabilityPeriod` declares
`start`, `end`, and `special_insured`: the latter is an adjudicated fact
that the earlier period qualified only under the special young-worker test.
Periods must not overlap calendar quarters. Onset may be later within the
query month, but not in a later month. A nonblind declared onset anchors the
disability witness; this preserves the onset test without claiming to
adjudicate the waiting period or a continuous disability freeze (.120).

Every year from `max(1937, birth_date.year)` through the earliest of query,
death, or coverage-end year must appear exactly once. Mapping iteration
order does not change a result. Years may declare either earnings or QCs,
never both. `CoverageYear` has a required canonical `EarningsProvenance`:

| Provenance | Values and treatment |
| --- | --- |
| `OBSERVED` | An explicit earnings or QC declaration; the rule does not verify how it was observed. |
| `CONVENTION_FILLED` | The same declaration plus a nonempty `convention_id`; amounts have identical statutory treatment. |
| `UNKNOWN` | No earnings or QC values allowed. Evaluate all-zero and maximum feasible-QC bounds. |

Before 1978, direct QCs require `qc_quarters`, exactly four Boolean flags;
otherwise use four `quarterly_wages`, optional `self_employment`, and
optional separate `agricultural_wages` for 1955–77. A bare pre-1978 count is
invalid. After 1977, direct input is `qc_count` (integer 0–4); earnings are
`wages` and/or `self_employment`, including covered agricultural wages in
`wages`. Unspecified components within a declared earnings record are zero;
an unspecified earnings year is never zero. Numbers use the shared exact
number schema, normalized to `Fraction`; floating earnings are invalid.
A declaration of zero earnings or zero QCs must still declare provenance.

All annual amounts are calendar-year covered amounts supplied by the caller.
For an exit year they must already be limited to covered work through the
exit month; the annual interface cannot reconstruct intra-year payment dates.
Subsequent years, and explicitly dated quarterly amounts or QCs after exit,
are input errors. Annual counts are capped by the number of assignable
quarters. No quarters after death, before birth, after exit, or not yet
begun at the query can be assigned. Disability interiors are excluded when
the prior periods are used (404.146; RS 00301.240).

For example, a person born February 2, 1980 with four QCs in each year
2011–2020 and an exit in December 2020 is fully, currently, and disability
insured at exit. Querying January 2031 preserves the same 40 QCs but returns
fully insured, not currently insured, and not disability insured. The
elapsed-year requirement continues to grow and the 13- and 40-quarter clocks
keep running. Foreign coverage is represented by optional ordered nonempty
string identifiers in `totalization_credits`; empty changes nothing and any
nonempty declaration receives `totalization_credits_unsupported`.

`InsuredStatus` reports `fully`, `currently`, and `disability` decisions
(unrequested decisions are `None`), `qcs_by_year` count ranges, a canonical
lower-bound `assigned_quarters` mapping, `unknown_years`,
`convention_years`, `decided_despite_unknowns`, `dli`, `month`, and `version`.
Each `StatusDecision` supplies `insured`, `qc_count_lower`, `qc_count_upper`,
`required`, `window`, `assigned_quarters`, and `rule`, with corresponding
`upper_required`, `upper_window`, `upper_assigned_quarters`, and `upper_rule`.
It also reports the fully insured prerequisite separately through
`fully_required`, `upper_fully_required`, `fully_qc_count_lower`, and
`fully_qc_count_upper`. Thus a disability witness can show 20 recent QCs
and still be uninsured because its duration-of-work requirement is not met.
The low and high witnesses each optimize assignment for that particular
test. They need not have the same assignment or prior-period treatment.
The per-year QC mapping uses the disability-excluded context; the witness
identifies credits actually used if disregarding the periods is favorable.

If either bound differs on a requested Boolean status, the call raises the
sealed `unknown_earnings_years_decide_status` refusal. If both agree, the
answer is decided despite unknown years and records all such years. A caller
interested only in fully insured status selects `FULLY`, so uncertainty in
another test cannot hide an otherwise decidable answer. No convention is
inferred. Every convention-filled year and its identifier is disclosed even
if it is outside the decisive recent-work window.

`DLIRange.lower` and `.upper` are last-quarter-end dates; `None` is the
bottom bound meaning no insured quarter. Without an exit declaration, this
is DLI **through the query**, with `right_censored=True` if still insured;
future undeclared work is not assumed zero. An uncensored historical result
still describes only the declared record through the query; later work can
reestablish insured status and move its eventual DLI. A future exit does
not remove censoring before that exit is reached. With an exit already reached,
coverage is frozen and the search can continue to the quarter before FRA
attainment, or death if earlier (RS 00301.148). DLI itself can remain a
range when the requested current statuses agree. Unknown future earnings
must not be inferred from this range or from a censored result.

## Exact rules and supported configurations

| Part | Implemented rule and authority |
| --- | --- |
| Annual QCs, 1978–2027 | Floor total covered wages plus SE income by the captured QC increment, maximum four (213(a); 404.143; RS .220/.250). Direct counts also work after 2027. |
| QC index | $250 × NAWI(y−2)/$9,226.48, nearest $10, ties upward, no decrease from the previous amount (213(d); OACT). No float tolerance. |
| Pre-1978 wages | $50 in a quarter; maximum taxable wages or qualifying combined wages/SE give four gift QCs (213(a); 404.141; RS .310/.345). |
| Calendar-year SE | At least $400 gives four QCs from 1951; below $400 contributes only to the applicable maximum-earnings rule (RS .340/.345). |
| Agriculture | 1955–77 annual $100 increments, up to four, added to uncredited quarters. Covered 1951–54 agricultural wages must already be included in quarterly covered wages (RS .320/.325). |
| Flexible assignment | Assign annual credits to whichever allowed quarters favor each test. Distinct tests expose distinct witnesses (404.143/.145; RS .230). |
| Fully insured | One QC per elapsed year after 1950 or age 21 year, minimum six, maximum 40; stop before query, age 62, death, or applicable onset year; exclude years partially or wholly in a used disability period (214(a);404.110;RS .105). |
| Early male retirement cohorts | Before January 2, 1911 use age 65; January 2, 1911–January 1, 1913 use 1975, subject to earlier query/death (404.110; RS .105). |
| Early male disability prerequisite | For every man born before January 2, 1913, the disability-specific fully insured elapsed-year endpoint is 1975 or the earlier relevant disability year (404.132(b)). It can differ from the retirement fully insured decision. |
| Currently insured | Six QCs within 13 counted quarters ending with an actual declared death/RIB/DIB event, or the hypothetical query event (214(b);404.120;RS .110). |
| Disability | Fully insured plus 20 QCs in 40 counted quarters (223(c)(1);216(i)(3);404.130;RS .120/.130). |
| Young worker | Before the age 31 attainment quarter: half the quarters after the age 21 quarter, dropping an odd remainder, minimum six. Fewer than 12 elapsed quarters uses 6/12; age 24 attainment quarter still uses 6/12 (404.130(c);RS .140). |
| Subsequent disability | With declared earlier special insured status, the special test can apply after 31, up to 20/40. Prior periods are all used or all disregarded, whichever admits insured status; endpoints count in windows only if QCs (404.130(f);RS .120/.147). |
| Blindness | Fully insured only, with elapsed years continuing until the qualifying QC year if onset itself was not insured (RS .150). |
| DLI | Latest fully-and-disability-insured quarter end, with explicit query censoring or frozen-exit horizon and FRA cap (RS .148). |

For prior disability periods, only years containing their endpoint quarters
need assignment enumeration. Other annual credits maximize overlap directly.
The calculation considers all-used and all-disregarded contexts, never a
selectively chosen subset. More than 4,096 boundary combinations receive an
explicit computational-coverage refusal. No approximate search is used.

For example, a man born February 2, 1900 queried in December 1974 with
20 QCs from 1969–1973 needs 14 QCs under the retirement fully insured rule,
but 23 for the disability prerequisite. The result is fully insured and
meets the disability 20/40 test, while remaining disability uninsured.
`fully_insured_requirement` returns the retirement/general requirement;
the disability decision's prerequisite fields expose the separate 404.132
calculation. This example decides insurance tests only, not post-FRA benefit
entitlement.

## Refused configurations

Input errors are raised before any of these coverage decisions. The enum is
`InsuredUnsupportedReason`; the class is `InsuredConfigurationUnsupported`,
a subclass of the shared `FamilyConfigurationUnsupported`.

| Trigger | Reason code |
| --- | --- |
| Unknown-year bounds decide a requested status differently | `unknown_earnings_years_decide_status` |
| Any foreign totalization credits | `totalization_credits_unsupported` |
| Declared deemed nonprofit/veteran fully insured path | `deemed_fully_insured_unsupported` |
| Declared transitional insured path | `transitional_insured_unsupported` |
| Alien SSN never assigned, or first assigned on/after January 1, 2004 | `alien_worker_sspa211_unsupported` |
| Railroad or military credits | `railroad_credits_unsupported`, `military_credits_unsupported` |
| Medicare-qualified government employment | `medicare_government_employment_unsupported` |
| Earned-basis wages or pre1956 alternate disability | `earned_basis_unsupported`, `disability_before_1956_unsupported` |
| Fiscal or short taxable-year public declaration | `fiscal_taxable_year_unsupported`, `short_taxable_year_unsupported` |
| Simplified pre1951 aggregate computation | `simplified_pre1951_unsupported` |
| Positive raw1937 earnings needing half-year/age65 rules | `1937_earnings_allocation_unsupported` |
| Separate pre1955 agricultural annual wages | `pre1955_agricultural_allocation_unsupported` |
| Pre1951 self-employment income | `pre1951_self_employment_unsupported` |
| Earnings require an increment after 2027 | `qc_amount_year_unsupported` |
| Query before 1968; blind query before 1973; subsequent-special query before May 1983 | `entitlement_before_1968_unsupported`, `blindness_before_1973_unsupported`, `subsequent_special_before_1983_unsupported` |
| More than 4,096 disability-boundary combinations | `disability_boundary_assignments_unsupported` |

A `CoverageCondition` explicitly triggers each specialist refusal. The
module does not infer excluded specialist facts from ordinary earnings.
Fiscal/short-year allocation helpers execute source arithmetic privately
for conformance tests; they do not expand the public calendar-year API.

## Input and result contract

The shared `_provenance` schema checks exact built-in scalar types, canonical
enums, exact declared classes, and every raw mapping element before hashing.
Ordered `tuple`/`list` inputs become tuples; membership conditions become a
frozenset. Sets are not accepted for ordered quarters, periods, or credits.
Dates are exact dates, Boolean values cannot impersonate integers, and
floating earnings are rejected. Public calls validate and snapshot once.
A new schema entry marks this module's earnings as exact, alongside R2/R3.
No cached caller identity bypasses later validation.

All decisions, DLI ranges, aggregate results, refusals, outcomes, and shared
denominators are sealed. Public construction, copying, dataclass replacement,
serialization, and mutated result reuse fail. Persist declared inputs and
recompute. `evaluate_insured_status` accepts only genuine results from this
layer but retains genuine shared coverage refusals. `count_family_outcomes`
counts all supported and refused rows and weights. Invalid declarations
produce no outcome row. The seal is an API contract, not a security boundary
against callers reaching private Python names or monkeypatching modules.

## Executed invariants

The test modules named below provide example assertions and Hypothesis
properties. The final execution report lists exact commands and results.

- Annual QCs stay in 0–4 and never decrease as earnings increase:
  `test_qcs_bounded_and_monotone_in_earnings`,
  `test_pre1978_qcs_bounded_and_monotone`.
- Indexed QC amounts never fall below the previous increment and are
  monotone in NAWI: `test_qc_amount_prior_floor_and_nawi_monotonicity`.
- Assignments are deterministic, order independent, unique, allowed,
  preserve permitted fixed quarters, and maximize overlap with their window:
  `test_assignment_maximizes_window_and_is_order_independent`.
- Excluding disability interiors never adds a QC and preserves eligible
  endpoints: `test_disability_exclusion_never_adds_qc` and the public
  `test_property_disability_period_exclusion_never_adds_qcs`.
- Every insured status and DLI are monotone when a QC is added; disability
  insured implies fully insured:
  `test_property_status_and_dli_monotone_in_quarters` and
  `test_property_subsequent_special_and_dli_monotonic`.
- Unknown status, count, and DLI bounds contain every concrete filling or
  the rule refuses: `test_property_unknown_bounds_cover_every_filling`,
  `test_unknown_bounds_with_prior_disability_period`, and
  `test_unknown_birth_and_exit_year_cap_is_sound`.
- Convention labels change no statutory answer and input order changes no
  result; complete observed histories follow the ordinary path:
  `test_property_convention_equal_amounts_and_order_independence`.
- Current/ordinary disability windows contain exactly 13/40 counted
  quarters, fully insured requirements stay in 6–40, the initial special
  test applies only before the age 31 attainment quarter, and blindness
  requires only fully insured:
  `test_property_windows_and_blindness_rule`, with the boundary example
  `test_special_insured_quarter_before_31_boundary`.
- Invalid input cannot become a refusal row; every valid refusal remains
  in the shared row and weight denominator:
  `test_property_input_errors_are_atomic_before_refusal` and
  `test_property_refusal_denominator_conserves_rows_and_weights`.
- Exact fiscal allocation conserves supplied income:
  `test_exact_sei_allocation_conserves_income`. This is private worked
  arithmetic, not an expansion of the public supported configuration.

Boundary examples additionally pin actual-event windows and future-exit
censoring: `test_currently_insured_uses_death_quarter_after_death`,
`test_currently_insured_preserves_actual_entitlement_event`,
`test_currently_insured_accepts_any_statutory_event`, and
`test_future_exit_does_not_remove_dli_censoring`. The separate early-male
disability prerequisite is pinned by
`test_pre1911_male_dib_fully_requirement_uses_1975_cap_cfr_404_132`.

## Worked examples and source findings

The YAML registry records source literals, expectations, coverage labels,
and any divergence. Source tests hash every capture and verify every quoted
rule and every example figure verbatim after documented text normalization.
The QC table matches POMS 1978–2026 and OACT 1978–2027 exactly. The repository
NAWI bundle reproduces every computable increment 1979–2026 with zero
arithmetic tolerance. OACT 2027 gives $250 × $72,800.33 / $9,226.48 =
$1,972.59 as printed, then rounds to $1,970, above 2026's $1,890.

RS .140 Fred Brown has 35 elapsed quarters, drops the odd quarter to 34,
and needs 17 QCs. Sam White has seven elapsed quarters and needs six QCs
in the 12-quarter 1981Q3–1984Q2 window. Mary Smith's examples 3–5 test six
recent credits, insufficiently recent credits, and favorable reassignment
of a 1982 credit to Q4. RS .148's person born March 9, 1954 has 30 total QCs,
needs 14 for fully insured in 1990, and has DLI June 30, 1990 by assigning
1980's two annual credits to Q3/Q4. RS .150 Calvin Hill needs seven QCs in
1986; the sixth in Q1 is insufficient and the seventh makes him insured
April 1, 1986. These calculations are pinned directly in the public tests.

RS .800's capture is an HTML shell linking uncaptured GIF/PDF exhibits.
The claimed all-cohort POMS differential cannot be performed offline.
Instead the tests compare every captured CFR 404.115 cohort row, including
January 1/January 2 boundaries and sex distinctions. RS .149 similarly links
an uncaptured worksheet. Neither missing attachment is represented as read.

RS .340 prints $10,900 in SEI but allocates $3,600 to each of three
quarters. Literal covered SEI divides as $10,900/3. An unstated application
of the1973 taxable ceiling of $10,800 instead reproduces $3,600 exactly,
if $10,900 meant net earnings before that ceiling. Tests execute both
readings; both give three QCs. The public short-year path remains refused. RS .345 prints an impossible “after 1975 and before 1975”
SE fiscal bracket; the calendar 1975 maximum of $14,100 is independently
clear in its wage table. No fiscal interpretation is silently inferred.
The subsequent-disability examples are also checked against the operative
endpoint and all-periods-disregarded rules; the final report records any
executed divergence and the exact supporting text for review.

## Not in scope

No real data, population evaluation, baseline claiming hazard, behavioral
response, benefit amount, administrative entitlement adjudication, medical
finding, original SSN evidence, or totalization agreement is implemented.
This module supplies B6a's statutory insured-status predicate; it does not
establish the empirical risk denominator or admit B6a forecasting. OP8(d)'s
pre-entry convention remains Max's decision. No Axiom differential is
claimed: the companion issue draft requests pinned413/414/423(c)(1) rules.
