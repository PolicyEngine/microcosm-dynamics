# Track B insured status and quarters of coverage

Verification class: **statutory conformance**. Version: `track-b-insured-v1`.
Admitted scope: invented declarations and published statutory examples only.
There is no population, behavioral, claiming-hazard, or forecast claim.
The governing reference is Act sections 213, 214, 216(i), 223(c)(1),
20 CFR part 404 subpart B and sections 404.315, .320, .321, and POMS
RS 00301. Sources are captured under
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
day of its calendar quarter. A quarter's ordinary predicate can cease at
the next quarter boundary or January's elapsed-year change. With declared
continuous medical disability, the disability decision retains the first
qualifying quarter through the query (404.131(a)). This is an insured
status calculation, not entitlement, medical disability, or a payment.
Currently insured uses the supplied death date, RIB entitlement month,
or most recent DIB entitlement month when available; any qualifying event
suffices. With none supplied it tests a hypothetical event in the query
quarter (214(b); RS 00301.110). Actual event dates are retained in later
queries; an emigrant with no entitlement event continues on the query clock.
Every established period intersecting that event's 13-quarter window is
considered, including a period containing or extending beyond the event.
The credited first and last quarters remain eligible (404.120(b); RS .110).

`Person` declares `birth_date`, optional `sex` (`Sex.MALE` or `Sex.FEMALE`,
required for pre-January-2-1913 cohorts), optional `death_date`, optional
`disability_onset`, ordered `prior_disability_periods`,
`statutory_blindness`, membership `conditions`, `alien_worker`, and optional
`ssn_assignment_date`, Boolean `ssn_never_assigned` (default `False`), and optional
`rib_entitlement_month` and `dib_entitlement_month` (the most recent DIB
entitlement). Supplied entitlement months must be within the lifetime and
no later than the query. An SSN assignment cannot precede birth. An alien
worker may supply an assignment date or `ssn_never_assigned=True`;
supplying both is an input error. These legacy facts derive known section
214(c) applicability. Alternatively the caller declares `sspa211_applies`
with `sspa211_provenance` and optional `sspa211_convention_id`. Applicability
is decided before the additional requirement is tested. RS 00301.102 B.1
exempts workers whose first SSN was assigned before January 1, 2004,
including nonwork SSNs. B.3 expressly includes workers not yet assigned an
SSN in their true identity. B.4.b permits specified work-authorized workers
without an SSN to meet the requirement; it does not exempt all unassigned
workers. Known applicability retains the named unimplemented SSPA 211
adjudication refusal. Unknown applicability returns a QC-only uninsured
answer when it is false either way, flagged as decided despite unknowns;
otherwise it raises `sspa211_applicability_unknown`. For example, zero
lifetime QCs cannot insure a worker whether section 214(c) applies or not.
A `DisabilityPeriod` declares
`start`, `end`, and `special_insured`: the latter is an adjudicated fact
that the earlier period qualified only under the special young-worker test.
Periods must not overlap calendar quarters. The ordered period sequence has
`prior_disability_periods_provenance` and optional
`prior_disability_periods_convention_id`; an observed empty sequence
explicitly means no established periods. The default provenance is
`UNKNOWN`, which must contain no periods and never silently means none.

`disability_onset` means medically disabled continuously from that day
through the query month; the rule does not adjudicate recovery. Onset may
be later within the query month, but not in a later month. Onset alone
never establishes a period or freezes elapsed years. With an onset, the
caller must explicitly declare `current_disability_period_provenance` and
`current_disability_period_established`: `True` or `False` for known facts,
or `None` with explicit `UNKNOWN`. Omitting this declaration is an input
error. `current_disability_period_convention_id` accompanies a convention.
The same canonical `EarningsProvenance` enum applies to all three factual
declarations: `OBSERVED`, `CONVENTION_FILLED` with a nonempty identifier,
or `UNKNOWN` without a value. The rule supplies no convention internally.

An established current period begins at medical onset if insured then,
otherwise on the first day of the first later insured quarter
(416(i)(2)(C); 404.321(a)). Establishment additionally requires an
application and the statutory duration or DIB-entitlement alternative
(416(i)(2)(A)-(B); 404.320(b)); the caller's declaration supplies these
administrative facts. A known established period with no possible insured
disabled quarter is invalid. Its start is derived from the supplied QC
history, then its years are excluded like any other established period.
On the ordinary supported QC surface, this includes known current
establishment with fewer than six maximum feasible lifetime QCs even when
prior periods are UNKNOWN: 404.130(a)
requires fully insured status, and 404.110(b)(1) says, "You need at least
6 QCs but not more than 40 QCs to be fully insured." Excluding periods
cannot supply the missing credits. When declared QC facts prove this
contradiction, the input error precedes coverage refusals, including
foreign-credit, specialist, SSPA-applicability, and period-uncertainty
refusals. Other military, railroad, deemed, and transitional declarations
retain their specialist refusals; no alternate-credit regime is adjudicated.
When prior periods are UNKNOWN, favorable disregard of every period can
still decide the Boolean status even if the current period's derived
start is uncertain. `current_disability_period_start` is then `None`, and
`unknown_facts` includes `current_disability_period_start`; the established
fact itself remains known. If the disregard treatment already qualifies
at medical onset, onset is the certain start. Disregard is a permitted
statutory treatment, not an assertion that a known period never existed.

Round 3 additionally proves when UNKNOWN prior history can only be empty
for establishment validation. The earliest nonempty period would need an
insured starting quarter without any earlier period (404.320(b)(2),
404.321(a)), on or after birth, before FRA, with time for five months before
its ending month (404.320(b)(4)), and an end before the current onset.
The scan uses the highest feasible QCs for every unknown year and a
permissive partial-month duration bound. If no quarter survives, validate
the current declaration against empty prior history at those highest QCs.
If even that world has no insured current start, raise `InvalidFamilyInput`
before any coverage refusal. An evaluator then creates no denominator row.
If a quarter survives, feasibility is unproved and a named refusal remains
possible. This is a sufficient invalidity proof, not a complete history
solver. For valid declarations the caller's UNKNOWN provenance, uncertain
start disclosure, and universal count envelope remain conservative; the
validation collapse does not invent an observed history.

An observation month never establishes a period's ending month. The
statutory end is the earlier of a declared administrative end and the last
day of the month before FRA (416(i)(2)(D); 404.321(c)); death also bounds the
declared lifetime. `current_disability_period_end` optionally supplies that
administrative ending date, on the last day of a month, with
`current_disability_period_end_provenance` and, for a convention,
`current_disability_period_end_convention_id`. An omitted end stays unknown.
These three optional fields append after the original twenty `Person`
fields, preserving the existing positional facts as well as keyword calls.
For an ongoing period the rule compares an end in the observation month
with continuation through the statutory FRA limit. The observation quarter
may be credited as the last quarter in the former world but interior in
the latter (404.146(d); 404.120(b)). When a requested status differs, the
call refuses with `ongoing_disability_period_end_decides_status`; when it
agrees, counts contain both worlds and the unknown ending is disclosed.
At or beyond FRA the calendar supplies the actual cap rather than an
unknown ending. Established starts at or after FRA are invalid even if
prior history is UNKNOWN, and every supplied prior period is capped at
the month before FRA. The standalone requirement helper shares these
limits. A start in the FRA attainment month is also invalid because its
mandatory end would precede its start, including a first-day birthday
whose FRA is attained at the end of the previous month. The FRA date and
quarter share the 416(l)(1)–(3) cohort schedule;
January 1 birthdays use the preceding attainment year, and the date itself
is the day before the birthday at the statutory age.

The disability test scans the onset quarter through the query quarter.
Each candidate's 20/40 or special window ends in that candidate quarter,
and its fully insured prerequisite ends elapsed years before the
candidate's year (416(i)(3); 423(c)(1)(A)-(B); 404.130-.132). This permits a
later qualifying quarter for blind and nonblind workers. For example,
birth February 2, 2000, onset January 15, 2022, four QCs in 2021 and two
in 2022 produce five assignable recent QCs at 2022Q1 and six at 2022Q2.
The April query is disability insured with a 2022Q2 witness. The window
endpoint therefore follows the qualifying disabled quarter, rather than
remaining permanently at medical onset.

The waiting-period clause cannot produce an earlier elapsed-year endpoint
in this interface. Section 404.315(a)(4) states, "The 5-month waiting period
begins with a month in which you were both insured for disability and
disabled." Such a month cannot precede the first insured disabled quarter
that begins the period under 404.321(a). Filing can delay the waiting
period, but cannot move it before that first qualifying quarter. The
established-current-period property below executes this ordering.

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
It also reports `current_disability_period_start`, `unknown_facts`, and
the identifiers in `convention_facts` separately from earnings provenance.
Each `StatusDecision` supplies `insured`, `qc_count_lower`, `qc_count_upper`,
`required`, `window`, `assigned_quarters`, and `rule`, with corresponding
`upper_required`, `upper_window`, `upper_assigned_quarters`, and `upper_rule`.
It also reports the fully insured prerequisite separately through
`fully_required`, `upper_fully_required`, `fully_qc_count_lower`, and
`fully_qc_count_upper`, plus `qualifying_quarter` and
`upper_qualifying_quarter` for the first successful disabled quarter in
each earnings-bound world. Thus a disability witness can show 20 recent QCs
and still be uninsured because its duration-of-work requirement is not met.
The low and high witnesses each optimize assignment for that particular
test. They need not have the same assignment or prior-period treatment.
The per-year QC mapping uses the disability-excluded context; the witness
identifies credits actually used if disregarding the periods is favorable.
Witness fields describe selected computations; their endpoint counts are
not automatically guaranteed envelopes. A favorable treatment or endpoint
witness can switch as unknown QCs rise, reducing a selected count. Where
unknown years interact with periods or an onset, and where period facts
are unknown, count bounds use zero through the maximum feasible lifetime
QCs before period exclusions. Multiple historical event witnesses can
also switch as unknown credits rise, so they use the same envelope.
This universal envelope contains every
concrete recent and fully-prerequisite count. Complete observed inputs
with known period ends retain exact counts. An ongoing ending can widen
counts even when every earnings year is observed. No narrower
selected-witness bound is claimed.

If either bound differs on a requested Boolean status, the call raises the
sealed `unknown_earnings_years_decide_status` refusal. If both agree, the
answer is decided despite unknown years and records all such years. A caller
interested only in fully insured status selects `FULLY`, so uncertainty in
another test cannot hide an otherwise decidable answer. No convention is
inferred. Every convention-filled year and its identifier is disclosed even
if it is outside the decisive recent-work window.

For unknown prior or current establishment facts, ordinary covered-credit
status under favorable disregard of those periods is a sound Boolean
lower bound, including when current establishment is known but its start
depends on unknown prior periods. Section
404.130(f) permits favorable all-period disregard for the disability
window; 404.320(a) supplies the broader rule: "If benefits payable on your
earnings record would be denied or reduced because of a period of
disability, the period of disability will not be taken into consideration."
Railroad and noncreditable military credits remain refused, preserving
RS .120's exception. A true lower bound therefore decides true. For valid
declarations, fewer
than six maximum feasible lifetime QCs decides false. Otherwise unknown
periods may change a false result, so the rule refuses by name. Current
establishment does not change the disability qualification scan that must
prove its start; using its own exclusion would be circular.

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
With unknown section214(c) applicability, a decided false current status
does not prove that the additional fully insured requirement was met at a
historical witness (214(c); RS .102). The conservative DLI lower bound is
`None`, while the upper bound retains the QC-only date, including any
period and earnings uncertainty. For example, birth February 2, 1980,
20 QCs in 2000–2004, and a January 2026 query give false current statuses
but a QC-only DLI of December 31, 2009. Unknown applicability reports
`None` through that date; exemption can recover the exact date. This is
pinned by `test_unknown_sspa_applicability_does_not_block_qc_only_uninsured_result`
and `test_unknown_sspa_applicability_preserves_qc_impossibility`.
With unknown established periods the all-periods-disregarded DLI supplies
a lower bound,
while the upper bound is the allowed query/FRA/death horizon; an exit
already reached uses the frozen-coverage FRA/death horizon. This can be a
broad range even when status is decided. With known prior-period history,
a declared ongoing established current period and an exit already reached,
a future DLI
would depend on recovery beyond the query, which is unobserved. That
configuration receives `ongoing_disability_period_dli_horizon_unsupported`.

## Exact rules and supported configurations

| Part | Implemented rule and authority |
| --- | --- |
| Annual QCs, 1978–2027 | Floor total covered wages plus SE income by the captured QC increment, maximum four (213(a); 404.143; RS .220/.250). Direct counts also work after 2027. |
| QC index | $250 × NAWI(y−2)/$9,226.48, nearest $10, ties upward, no decrease from the previous amount (213(d); OACT). No float tolerance. |
| Pre-1978 wages | $50 in a quarter; maximum taxable wages or qualifying combined wages/SE give four gift QCs (213(a); 404.141; RS .310/.345). |
| Calendar-year SE | At least $400 gives four QCs from 1951; below $400 contributes only to the applicable maximum-earnings rule (RS .340/.345). |
| Agriculture | 1955–77 annual $100 increments, up to four, added to uncredited quarters. Covered 1951–54 agricultural wages must already be included in quarterly covered wages (RS .320/.325). |
| Flexible assignment | Assign annual credits to whichever allowed quarters favor each test. Distinct tests expose distinct witnesses (404.143/.145; RS .230). |
| Fully insured | One QC per elapsed year after 1950 or age 21 year, minimum six, maximum 40; stop before query, age 62, or death. Exclude only years partially or wholly in an established period; medical onset alone never caps elapsed years (214(a);404.110;RS .105). |
| Early male retirement cohorts | Before January 2, 1911 use age 65; January 2, 1911–January 1, 1913 use 1975, subject to earlier query/death (404.110; RS .105). |
| Early male disability prerequisite | For every man born before January 2, 1913, the disability-specific fully insured elapsed-year endpoint is 1975 or the earlier relevant disability year (404.132(b)). It can differ from the retirement fully insured decision. |
| Currently insured | Six QCs within 13 counted quarters ending with an actual declared death/RIB/DIB event, or the hypothetical query event. Every intersecting established period can extend the window, including the event's own period (214(b);404.120;RS .110). |
| Disability | Scan onset through query for the first candidate quarter with the candidate-year fully insured prerequisite plus 20 QCs in 40 counted quarters, or a special rule (223(c)(1);216(i)(3);404.130-.132;RS .120/.130). |
| Young worker | Before the age 31 attainment quarter: half the quarters after the age 21 quarter, dropping an odd remainder, minimum six. Fewer than 12 elapsed quarters uses 6/12; age 24 attainment quarter still uses 6/12 (404.130(c);RS .140). |
| Subsequent disability | With declared earlier special insured status, the special test can apply after 31, up to 20/40. Prior periods are all used or all disregarded, whichever admits insured status; endpoints count in windows only if QCs (404.130(f);RS .120/.147). |
| Blindness | Only the fully insured prerequisite, evaluated at each candidate disabled quarter; it can first qualify after medical onset, as can nonblind status (404.130(e),404.131;RS .150). |
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
| Unknown prior periods may change a requested status | `unknown_prior_disability_periods_decide_status` |
| Unknown current establishment may change a requested status | `unknown_current_disability_period_decides_status` |
| Ongoing current period's observation-quarter ending versus continuation changes a requested status | `ongoing_disability_period_end_decides_status` |
| Unknown section 214(c) applicability may change a requested status | `sspa211_applicability_unknown` |
| Standalone requirement helper needs coverage history to derive a declared current period start | `current_disability_period_requires_history` |
| Ongoing established current period, known prior-period history, and a frozen-exit DLI horizon beyond query | `ongoing_disability_period_dli_horizon_unsupported` |
| Any foreign totalization credits | `totalization_credits_unsupported` |
| Declared deemed nonprofit/veteran fully insured path | `deemed_fully_insured_unsupported` |
| Declared transitional insured path | `transitional_insured_unsupported` |
| Known section 214(c) applicability needs unimplemented work-authorization/visa adjudication, including never-assigned alien SSNs | `alien_worker_sspa211_unsupported` |
| Railroad or military credits | `railroad_credits_unsupported`, `military_credits_unsupported` |
| Medicare-qualified government employment | `medicare_government_employment_unsupported` |
| Earned-basis wages or pre1956 alternate disability | `earned_basis_unsupported`, `disability_before_1956_unsupported` |
| Fiscal or short taxable-year public declaration | `fiscal_taxable_year_unsupported`, `short_taxable_year_unsupported` |
| Supplied pre1951 wages, or UNKNOWN pre1951 years, could make a failed fully insured test pass under the simplified method; also an explicit specialist declaration | `simplified_pre1951_unsupported` |
| Positive raw1937 earnings needing half-year/age65 rules | `1937_earnings_allocation_unsupported` |
| Separate pre1955 agricultural annual wages | `pre1955_agricultural_allocation_unsupported` |
| Pre1951 self-employment income | `pre1951_self_employment_unsupported` |
| Earnings require an increment after 2027 | `qc_amount_year_unsupported` |
| Query before 1968; blind query before 1973; subsequent-special query before May 1983 | `entitlement_before_1968_unsupported`, `blindness_before_1973_unsupported`, `subsequent_special_before_1983_unsupported` |
| More than 4,096 disability-boundary combinations | `disability_boundary_assignments_unsupported` |

The round-3 observable-trigger audit covers every `CoverageCondition`.
An explicit condition continues to refuse independently of its ordinary
status result. Automatic detection additionally applies where the ordinary
declarations reveal a potentially decisive specialist route:

The pre1951 bound compares the deemed-credit aggregate with the smallest
fully insured requirement across permitted freeze treatments, including
the derived current period (213(c); 404.110(c)–(d); 404.130(f)). The selected
ordinary witness can have more QCs and a higher requirement, so its
requirement alone is insufficient. UNKNOWN prior or current establishment
uses the universal six-QC requirement as a conservative possibility bound.
Post1950 upper credits are counted without period exclusions for this
refusal check; this may refuse extra cases but cannot silently deny a
potentially favorable specialist path. It does not compute deemed-credit
allocation or adjudicate application facts.

| Condition | Observable trigger or absent fact |
| --- | --- |
| `SIMPLIFIED_PRE1951` | Raw 1937–1950 quarterly wages provide an aggregate divided by $400; post1950 upper QCs and the fully insured prerequisite bound whether it could decide status (213(c); 404.110(d); RS .315). UNKNOWN pre1951 years can supply unbounded raw wages and therefore also trigger the refusal. Direct `qc_quarters` declare credited quarters rather than raw wages. The simplified method does not apply to a disability claim. Filing, retroactivity, and section 227 facts remain unmodeled. |
| `DISABILITY_BEFORE_1956` | Medical onset and QCs reveal a possible RS .480 alternative: at least 20 total QCs and every quarter from 1951Q1 through the quarter before a qualifying 1952Q3–1955Q4 candidate quarter at or after onset, with at least six such quarters. Refuse automatically when this could change a failed disability predicate. Application conditions remain unmodeled. |
| `DEEMED_FULLY_INSURED` | Wages and dates do not identify covered nonprofit employment or veteran status; retain the explicit flag (404.111–.112; RS .106/.107/.470). |
| `TRANSITIONAL_INSURED` | Cohort dates alone do not identify the necessary historical benefit/application facts; retain the explicit flag (RS .101's transitional-benefit referrals). |
| `RAILROAD_CREDITS`, `MILITARY_CREDITS` | Ordinary covered earnings do not identify railroad or military service and additional credits; retain explicit flags (RS .350; RS .120/.470). |
| `MEDICARE_GOVERNMENT_EMPLOYMENT` | Covered amounts do not identify government employment or Medicare-only coverage; retain the explicit flag (RS .160/.161). |
| `EARNED_BASIS` | Paid calendar-quarter amounts do not disclose when those wages were earned; retain the explicit flag (213(a); RS .475). |
| `FISCAL_TAXABLE_YEAR`, `SHORT_TAXABLE_YEAR` | Calendar-year self-employment totals do not disclose the taxpayer's fiscal or short taxable-year dates; retain explicit flags (404.142/.144; RS .220/.340/.345). |

Raw1937 earnings, separate pre1955 agriculture, and pre1951 self-employment
already have automatic refusals in the QC conversion layer. Historical
query/blindness/subsequent-special dates and uncaptured future increments
also already trigger their refusals without a specialist flag.

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
- With fixed declared disability-period boundaries, insured status and DLI
  are monotone when a QC is added; disability
  insured implies the fully insured prerequisite at its qualifying
  quarter. Without an established period, the query's later old-age
  requirement can differ:
  `test_property_status_and_dli_monotone_in_quarters` and
  `test_property_subsequent_special_and_dli_monotonic`. The separate
  intended query-fully/onset-disability distinction is pinned by
  `test_unknown_current_period_refuses_when_establishment_changes_full_status`.
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

Round 2 adds these executed invariants and interface properties:

| Invariant | Hypothesis test |
| --- | --- |
| Declared continuous-disability status equals the disjunction of plain candidate-quarter predicates from onset through query; the first qualifying witness and window endpoint agree. DLI reaches the onset quarter exactly when this scan succeeds. Derived period start is onset day or the first later qualifying quarter's first day; no waiting period can start earlier. | `test_continuous_onset_status_and_dli_equal_plain_quarter_scan` |
| The same scan, first-witness, and DLI identity holds with an established prior period and its favorable treatment. | `test_continuous_onset_with_prior_period_matches_plain_predicate_scan` |
| Recent and fully-prerequisite QC envelopes contain every concrete unknown-year filling even when periods are present and the selected witness switches; supported Boolean results agree with every filling. | `test_unknown_recent_and_fully_counts_contain_concrete_period_fillings` |
| Supported statuses and DLI bounds with UNKNOWN prior/current periods contain all generated concrete established-period fillings; favorable no-period lower bounds never overstate status or DLI. | `test_unknown_period_status_and_dli_bounds_contain_concrete_fillings` |
| Replacing observed fact provenance with convention-filled provenance and identifiers changes no status or DLI; all identifiers remain disclosed. | `test_declared_fact_provenance_preserves_computed_status` |
| UNKNOWN section 214(c) applicability preserves decided false current statuses and discloses that unknown fact. Historical DLI is bounded by None through the QC-only upper date; the envelope contains the exempt filling even with old insured work histories. A true current QC predicate requires the named applicability refusal. | `test_unknown_sspa_applicability_preserves_qc_impossibility` |

Round 3 adds these invariants:

| Invariant | Hypothesis test |
| --- | --- |
| FRA date and quarter equal an independent implementation of Act 216(l), including both step-up bands and first/second-day birthdays. | `test_fra_date_and_quarter_match_independent_act_calendar` |
| Every supplied prior period ends no later than the month before FRA. | `test_every_supplied_prior_period_has_the_statutory_fra_cap` |
| A known current establishment at or after FRA is invalid for observed and UNKNOWN prior histories. | `test_known_establishment_at_or_after_fra_is_always_invalid` |
| A returned ongoing-period status agrees with concrete ending-quarter and continuing completions, and the returned recent/fully QC counts contain their counts; otherwise the named ending refusal applies. | `test_ongoing_period_completion_status_and_count_bounds_are_sound` |
| Proving an UNKNOWN declaration invalid implies all enumerated valid-calendar, insured-start empty/one/two-period and annual-QC fillings are invalid; a valid filling prevents that error. | `test_invalid_unknown_declaration_has_no_valid_enumerated_filling` |
| A valid long prior special period can rescue current establishment; UNKNOWN history must retain that possibility even when observed empty history would be invalid. | `test_valid_prior_freeze_filling_prevents_false_invalidity` |
| Declared ending facts and provenance round-trip, inconsistent values/provenance/convention identifiers are invalid, and the original twenty positional Person fields keep their meaning. | `test_declared_period_end_provenance_roundtrip_and_invalid_combinations` |
| Automatic simplified pre1951 refusals obey exact $400 aggregate boundaries and arise without an opt-in specialist flag. | `test_pre1951_refusal_tracks_exact_400_dollar_status_boundary` |
| Mapping order and observed/convention provenance do not change the automatic simplified-pre1951 reason. | `test_pre1951_refusal_is_independent_of_mapping_order_and_provenance` |
| Automatic pre1951 detection bounds the lower fully insured requirement from a known disability freeze at exact aggregate-dollar boundaries, even when the ordinary witness selects a higher requirement. | `test_pre1951_refusal_bounds_every_known_freeze_requirement` |
| Automatic pre1956 alternative refusals require at least 20 possible QCs and the continuous qualifying 1951 window. | `test_pre1956_refusal_requires_twenty_qcs_and_the_continuous_window` |

The reviewer regressions additionally pin the 2026 blind-onset endpoint
case (five continuing QCs versus six if the period ends in the event
quarter), the 1960 birth FRA case (five QCs and false in October 2028),
post-FRA establishment errors, invalid-before-refusal and zero evaluator
rows, and Sam's seven elapsed-year prerequisite. Source literal tests
retain the statutory end, duration, cohort, and simplified-credit clauses.
The ending example additionally checks equal statutory status for observed
and convention-filled endings:
`test_declared_period_end_resolves_the_query_quarter_ambiguity`.

An additional invented pre1951 case has birth February 2, 1920, eight QCs
before a valid January 1945 period, twelve QCs inside the period, and an
ending in December 1960. At February 1990 the ordinary witness has 20 QCs
against 31 required. The freeze reduces the requirement to 21, while total
pre1951 wages of $9,200 could supply 23 deemed credits. Both a supplied
prior period and a declared current period with that end automatically
refuse; neither silently returns the ordinary false result. Generated
ending years and exact cents pin the boundary, including $8,399.99 versus
$8,400 for the 21-credit requirement. This is a conservative refusal, not
a claim to adjudicate the interaction of deemed allocation and a freeze.

The reviewer's examples separately pin onset without establishment,
later-quarter qualification, the event's own established period, and the
24/26 endpoint-count counterexample containing a concrete count of 23:
`test_medical_onset_alone_never_freezes_fully_insured_elapsed_years`,
`test_continuous_disability_can_first_qualify_after_medical_onset`,
`test_currently_insured_excludes_period_containing_dib_event`, and
`test_unknown_prerequisite_count_bounds_contain_witness_switch_fillings`.
Before the reviewed `d21ece2d` head, round 2 corrected an original assertion
that excluded an event's own later-ending period. That correction implements
404.120(b)'s exclusion of every intersecting established period. Round 3
preserves the reviewed assertion.

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
The manifest retains 48 captures. The registry contains 48 entries: 27
computed cases, 12 named refusals, three source-rule divergences, one
source ambiguity, three table differentials, and two administrative
inventory entries. Inventory and refused entries are not claimed as
reproduced statutory calculations.
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
The added Sam White registry case quotes the source's statement that he
may become insured later. The source supplies no later history or date;
the explicitly invented completion of three QCs in each of 1983 and 1984
gives five assignable QCs at 1984Q2 and six at 1984Q3. This demonstrates the
published later-status rule without presenting the invented date as a
published numerical result.

The reviewer's uninsured-onset case has birth February 2, 1980, medical
onset January 15, 2007, no established period, four 2008 QCs and two 2009
QCs. At April 2009 the old-age/survivor elapsed years 2002–2008 require
seven QCs, so six do not insure. Medical onset cannot replace that seven
with six. The current-period example has DIB entitlement July 2004 inside
an established January–December 2004 period and three QCs in each of 2001
and 2002. Excluding the event's own period extends the 13-quarter window
to 2000Q4–2003Q4 and yields six QCs, hence currently insured.

RS .800's exhibit is a PDF and two GIF renderings of the same table. Its
text was extracted from the PDF with pdftotext; the PDF and both GIFs are
pinned by hash. The tests compare every one of its 38 rows: by birth cohort
(men before January 2, 1913 at age 65, women at 62), by footnote 1's
January 1 rule, and by year of death for a worker who attained 21 before
1951. They also compare every CFR 404.115 cohort row, including January
1/January 2 boundaries and sex distinctions. The PDF's footnote misprints
the male age-65 cohort as "born before 1/2/31"; its GIF rendering, its own
table and 20 CFR 404.132(b) say January 2, 1913, which the rule follows.
RS .149 links an uncaptured worksheet, which is not represented as read.

RS .340 prints $10,900 in SEI but allocates $3,600 to each of three
quarters. Literal covered SEI divides as $10,900/3. An unstated application
of the1973 taxable ceiling of $10,800 instead reproduces $3,600 exactly,
if $10,900 meant net earnings before that ceiling. Tests execute both
readings; both give three QCs. The public short-year path remains refused. RS .345 prints an impossible “after 1975 and before 1975”
SE fiscal bracket; the calendar 1975 maximum of $14,100 is independently
clear in its wage table. No fiscal interpretation is silently inferred.
The subsequent-disability examples retain both the source's printed result
and the operative regulation. RS .140 example 6 prints 18 elapsed
quarters/nine required QCs; retaining credited endpoint quarters under
404.130(f) gives 20/10 with 16 available, still insured. RS .147 example 3
prints 33 elapsed/16 required/eight available; favorable annual assignment
to the 1978Q4 endpoint gives 34/17/nine, still uninsured. RS .147 example 2
says John "requires and has 16" although the full record contains 18;
its statement that two additional QCs would reach 20 confirms the latter.

## Readings for the orchestrator

These readings apply the statute first, then the regulation, with agency
guidance resolving remaining questions. They do not request an additional
reading from Max.

For RS .140 example 9, the printed conclusion says, "Sam requires 8 QC's
but has only 7 QC's and does not meet insured status as of 5/93." Section
404.130(f) instead says, "However, we will count all the quarters in the
prior period of disability established for you if by doing so you would
be entitled to benefits or the amount of the benefit would be larger."
RS .120 B.1.b also requires all prior periods to be used or all
disregarded. Disregarding the freeze gives 20 QCs in the 40-quarter
1983Q3–1993Q2 window and the fully insured prerequisite of seven (the
elapsed years 1986–1992), so the implemented result is insured. The printed
eight is the used-freeze special-window requirement: that treatment has
17 elapsed quarters, eight required, and seven available. An otherwise
payable invented $1,000 monthly benefit would differ by $1,000 versus
zero under these insurance answers; this module computes no payment.

The credited-endpoint and favorable-assignment readings above are retained:
404.130(f) keeps an endpoint if it is a QC, and RS .230 permits favorable
annual assignment. They change intermediate counts in RS .140 example 6
and RS .147 example 3, but neither example's insured conclusion. The
short-tax-year $10,900 versus $10,800 reading remains a named public
refusal; both readings give three QCs but differ by $100 in allocated
earnings. The exit-year annual-count cap remains an explicit interface
convention, not a statutory emigration exclusion.

Medical onset versus administrative establishment and the event's own
period are corrections required by 416(i)(2), 404.110(c), 404.120(b), and
404.320-.321. The never-assigned-SSN applicability text in RS .102 B.3
also controls over the coordinator's reported blanket exemption; B.4.b's
work-authorized exception concerns satisfying the requirement. Known
applicable cases remain refused until that adjudication is implemented.

For simplified pre1951 credits, Act 213(c) says an individual "shall be
deemed to have one quarter of coverage for each $400 of his total wages
prior to 1951", subject to becoming fully insured with the resulting
credits plus post1950 credits. It states no seven-elapsed-year minimum.
RS .315 instead says "Under the 1967 Amendments, use the simplified method
if:" and "there are at least seven EYs; and"; CFR 404.110(d) uses permissive
"we may use the following rules" and also has the seven-year condition.
The evaluator refuses a potentially decisive aggregate even below seven
elapsed years. That avoids silently denying the statutory path while
filing, retroactivity, and section 227 facts remain absent. Both dates in
`test_potential_simplified_method_refuses_unresolved_seven_ey_applicability`
pin this refusal: an invented woman born February 2, 1895, with $2,400 in
1940Q1 has one ordinary QC, six deemed QCs, and a six-QC prerequisite at
February 1968. A strict seven-year eligibility reading would return false;
the broader statutory reading could return true. If an otherwise payable
invented monthly benefit were $1,000, that would be $0 versus $1,000;
this module computes neither payment and retains the named refusal.

Mutation checks are recorded in
[`track_b_insured_status_mutations.json`](track_b_insured_status_mutations.json).
Every recorded implementation mutation was caught and reverted.

## Not in scope

No real data, population evaluation, baseline claiming hazard, behavioral
response, benefit amount, administrative entitlement adjudication, medical
finding, original SSN evidence, or totalization agreement is implemented.
This module supplies B6a's statutory insured-status predicate; it does not
establish the empirical risk denominator or admit B6a forecasting. OP8(d)'s
pre-entry convention remains Max's decision. No Axiom differential is
claimed: the companion issue draft requests pinned413/414/423(c)(1) rules.
