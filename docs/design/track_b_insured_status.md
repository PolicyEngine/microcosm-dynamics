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
supplying both is an input error. These legacy facts derive section
214(c) applicability unless an adjudicated exemption applies. The caller
declares that determination with `sspa211_applies`,
`sspa211_provenance`, and optional `sspa211_convention_id`. Applicability
is decided before the additional requirement is tested. RS 00301.102 B.1
exempts workers whose first SSN was assigned before January 1, 2004,
including nonwork SSNs. B.3 expressly includes workers not yet assigned an
SSN in their true identity. B.3.b also exempts a wrong-number SS-5 worker
who could legitimately have received an SSN before 2004. An observed or
convention-filled exemption therefore overrides the post-2003 or
never-assigned presumption, including before a proper true-identity SSN
has been assigned. The worker must have been born before January 1, 2004:
no legitimate pre2004 assignment is possible before birth. An alien born
on or after that date cannot declare an exemption, even without a supplied
assignment date. An actual pre-2004 assignment with declared
applicability remains contradictory because B.1 expressly exempts it.
B.4.b permits specified work-authorized workers without an SSN to meet
the requirement; it does not exempt all unassigned
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

`disability_onset` supplies the ordinary continuous-disability premise from
that day through the query month; the rule does not adjudicate recovery.
A declared historical period end can limit the alternate-pre1956 scan,
as required by 404.321(b) below. Onset may
be later within the query month, but not in a later month. Onset alone
never establishes a period or freezes elapsed years. With an onset, the
caller must explicitly declare `current_disability_period_provenance` and
`current_disability_period_established`: `True` or `False` for known facts,
or `None` with explicit `UNKNOWN`. Omitting this declaration is an input
error. `current_disability_period_convention_id` accompanies a convention.
The same canonical `EarningsProvenance` enum applies to these factual
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
Every fact-pattern establishment rejection uses one possibility check
across the ordinary route, automatically observable specialist routes,
and declared `CoverageCondition` routes. An unresolved specialist
possibility retains its named refusal. The automatically observable
alternate-pre1956 scan independently obeys the same immutable start
horizon: an ending or continuity observation before July 1952 cannot be
rescued by its first permitted July 1, 1952 start (RS .480 B.1). Explicit
specialist declarations remain separately preserved. RS .480 A also makes
that automatic alternate unavailable if even the lower-credit filling has
20/40 in a disabled quarter before October 1960. The test uses the ordinary
disability window, including favorable use or disregard of all prior
periods, from onset through the earliest of the query, 1960Q3, and the
quarter containing the last day of the month before FRA. For an established
current period it also stops at the declared end, or, with an UNKNOWN end,
the continuity date if supplied and otherwise onset. These are the dates
through which every ending completion still covers the period. The FRA
bound
applies regardless of whether a period is declared established: the
witness must support a freeze or DIB (Act 216(i)(2)(D); 404.315(a);
404.321(a)–(b)). A quarter beginning before the FRA month remains eligible
when FRA falls in its second or third month. A witness in the quarter
containing the covered date remains eligible because that quarter begins
on or before it; a witness in the next quarter does not exclude the route.
The captured 404.321(b), headed "When disability ended before December 1,
1980", governs this scan's era and says:

> Your period of disability ends on the last day of the month before the month in which you become 65 years old or, if earlier, the last day of the second month following the month in which your disability ended.

An earlier declared end in this era therefore reflects an ended disability;
it cannot be treated as an administrative fact independent of recovery.
Section 404.321(c) supplies different endings when disability ends after
November 1980. This note makes no claim about those endings beyond the
implemented date declarations and candidate evaluation.

RS .480 A permits two readings. Its "any quarter before 10/60" supports
the literal scan, while "though under a disability" and "for freeze or DIB"
support limiting a witness to the period it could establish. A witness
after a declared end cannot start that period. Where those readings differ,
the rule retains `disability_before_1956_unsupported`; it does not decide
between them. The same protection applies to UNKNOWN endings: an early
ending completion that preserves the route prevents a universal exclusion.
If some feasible fillings still lack 20/40, application facts remain absent
and the alternate possibility retains its refusal.
On the ordinary route, a valid
filling must supply one insured start that is at or before the declared
administrative end and clears every prior-period overlap. A later witness
at the query cannot rescue an immutable earlier end. The scan therefore
stops at that end, any continuity observation, death, or FRA cap, whichever
is earlier. Maximum credits decide the monotone insured-by-that-date
question. If that representative's derived start overlaps a prior period,
the rule checks lower-credit fillings and, when needed, enumerates the
bounded concrete fillings for a single valid period. It never combines
the end compliance of one filling with the overlap compliance of another.
Before that enumeration, it checks whether any candidate starting quarter
from onset through the fixed horizon clears all supplied prior periods.
If none does, no credit route can supply a nonoverlapping start.
Only when all routes and feasible fillings are impossible can the rule
raise `InvalidFamilyInput` before any coverage refusal. On the ordinary
supported QC surface, fewer than six maximum feasible lifetime QCs proves
impossibility: 404.130(a) requires
fully insured status, and 404.110(b)(1) says, "You need at least 6 QCs but
not more than 40 QCs to be fully insured." Period exclusions cannot supply
missing credits. That ordinary argument does not adjudicate deemed,
transitional, military, railroad, or other specialist routes. A flag or
observable specialist route that could validate the declaration prevents
that input error and preserves a refusal row.

When prior periods are UNKNOWN, favorable disregard of every period can
still decide the Boolean status even if the current period's derived
start is uncertain. `current_disability_period_start` is then `None`, and
`unknown_facts` includes `current_disability_period_start`; the established
fact itself remains known. If the disregard treatment already qualifies
at medical onset, onset is the certain start. Disregard is a permitted
statutory treatment, not an assertion that a known period never existed.

UNKNOWN prior history can be proved empty for establishment validation only
when no earliest period could fit. Its insured starting quarter has no
earlier exclusions (404.320(b)(2); 404.321(a)); it is on or after birth,
before FRA, and before current onset. The feasibility scan admits a period
lasting only one month. Act 216(i)(2)(A) permits "not less than five full
calendar months' duration or such individual was entitled to benefits
under section 423 of this title for one or more months in such period."
The five-month phrase in 404.320(b)(4) therefore supplies no universal
minimum. Section 404.315(a)(4) also says "or no waiting period is required"
and lists recent prior entitlement or a period of disability and ALS as
waiting-period exceptions. The interface does not adjudicate those
administrative facts for an already declared period; it imposes no
five-month validation on current or supplied prior periods.

The scan uses maximum feasible QCs for unknown years and does not try to
prove administrative feasibility. Any possible specialist starting route
also prevents an empty-history impossibility proof. If no quarter or route
survives, empty prior history is the only remaining case for current
establishment validation; only impossibility there permits an input error
and no denominator row. A surviving quarter establishes no actual history:
it merely prevents that error, preserving a named refusal when status is
unresolved. The caller's UNKNOWN provenance, uncertain start disclosure,
and universal count envelope remain conservative.

An observation month never establishes a period's ending month. The
statutory end is the earlier of a declared administrative end and the last
day of the month before FRA (416(i)(2)(D); 404.321(c)); death also bounds the
declared lifetime. `current_disability_period_end` optionally supplies that
administrative ending date, on the last day of a month, with
`current_disability_period_end_provenance` and, for a convention,
`current_disability_period_end_convention_id`. A default omitted end stays
unknown.
These three optional fields append after the original twenty `Person`
fields. Round 5 appends three continuity fields after all twenty-three
existing fields, preserving every existing positional argument.
With an UNKNOWN ending, the rule evaluates every candidate end quarter from
the derived period's start, restricted by any continuity observation,
through the last quarter allowed by the query and FRA/death cap. It
additionally considers continuation past the query when the cap permits.
Quarter representatives suffice because exclusions,
credited endpoints, and elapsed-year freezes change only at quarter/year
boundaries. It does not decide which candidates an administrative record
would establish. Continuous medical disability supplies no administrative
continuity: 404.321(c)(3) permits ending at "the last month for which you
received benefits" after substantial gainful activity, while Act
216(i)(2)(D) selects the earlier FRA or termination/no-benefit boundary.
Any candidate that changes a requested status retains
`ongoing_disability_period_end_decides_status`; a returned status agrees
across every candidate. Recent, prerequisite, annual-count, and DLI bounds
cover all those candidates. Reaching FRA supplies an upper bound on the
end, never its actual date; an UNKNOWN end stays in `unknown_facts` at
and after FRA, including when prior history is also UNKNOWN. Both missing
facts remain disclosed; UNKNOWN prior history uses the broader universal
envelopes rather than inventing a concrete current period for enumeration.
A supplied date retains the existing declaration semantics;
known ending provenance requires that date.

An observed running period instead uses
`current_disability_period_continues_through: date | None`, with
`current_disability_period_continues_through_provenance` (default
`UNKNOWN`) and optional
`current_disability_period_continues_through_convention_id`. The same
provenance/value and convention-identifier contracts apply. This fact
requires an established period and says only that it was still in force
on that date. The date cannot precede onset or the possible insured start,
exceed the month-before-FRA cap or death, or follow a declared end. It may
follow the query. Candidate administrative ends must be on or after the
observation; the observation never becomes an end or a credited endpoint.
The caller still receives an UNKNOWN-end disclosure when no actual end
is declared. B6a, OP8(d), and OP12 should use these continuity fields for a
known running cash-benefit or no-cash disability freeze, rather than
inventing a future end. Continuity within the query quarter can leave its
endpoint ambiguous; continuity into a later quarter proves that the query
quarter is interior.

Established starts at or after FRA are invalid even if prior history is UNKNOWN, and every supplied prior period is capped at
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

An uncomputable raw-earnings row is treated as unknown only while checking
whether declared establishment is possible. Its minimum and maximum
feasible credits are bounded by the same allowed-quarter calendar. These
temporary fillings do not become a supported earnings result or a returned
count envelope: if the declaration survives, the original conversion
refusal fires with its unchanged reason and note. A refused row beyond an
immutable starting horizon cannot hide a declaration that every filling
proves impossible.

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
With unknown section 214(c) applicability, a decided false current status
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

The refusal order starts with full schema and history validation, including
every raw row. The establishment possibility proof then precedes coverage
refusals. Before that proof, raw conversion can encounter only four
reachable refusals: `qc_amount_year_unsupported`,
`1937_earnings_allocation_unsupported`,
`pre1955_agricultural_allocation_unsupported`, and
`pre1951_self_employment_unsupported`. These are deferred while possibility
is tested with each unresolved row's feasible credit fillings. If the
proof finds a possible filling or reaches an unresolved coverage limit,
the first original conversion refusal in year order is raised unchanged.
Proved impossibility instead raises `InvalidFamilyInput`. With no deferred
reason, the existing specialist, date, applicability, and requested-status
checks follow. The evaluator validates its
key, weight, and callback before invoking the callback; it adds no statutory
refusal of its own. It counts a genuine callback refusal only after the
callback's declaration validation has had this opportunity to reject the
input. An input error propagates and creates no row.

| Trigger | Reason code |
| --- | --- |
| Unknown-year bounds decide a requested status differently | `unknown_earnings_years_decide_status` |
| Unknown prior periods may change a requested status | `unknown_prior_disability_periods_decide_status` |
| Unknown current establishment may change a requested status | `unknown_current_disability_period_decides_status` |
| Any candidate end quarter for an UNKNOWN current ending changes a requested status | `ongoing_disability_period_end_decides_status` |
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
| More than 4,096 disability-boundary combinations, or unresolved ordinary-establishment overlap requiring more than 4,096 credit fillings after the candidate-quarter exclusion check | `disability_boundary_assignments_unsupported` |

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
| `DISABILITY_BEFORE_1956` | Medical onset and QCs reveal a possible RS .480 alternative: at least 20 total QCs and every quarter from 1951Q1 through the quarter before a qualifying 1952Q3–1955Q4 candidate quarter at or after onset, with at least six such quarters. For declared current establishment, that candidate must fit the immutable declared-end/continuity/death/FRA horizon. RS .480 A excludes the route when the lower-credit filling has 20/40 in the rule's disabled-quarter scan before October 1960; if only some fillings do, the alternate remains possible. Refuse automatically when this could change a failed disability predicate. Application conditions remain unmodeled. |
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

## Premises for rejection, unknown facts, and bounds

A fact-pattern rejection means every concrete completion is impossible
under every potential route. A named refusal remains whenever an ordinary,
automatically observable specialist, or flagged specialist route could
validate the declaration. Absence of an ordinary witness alone is no proof
against a specialist route. Conversely a later ordinary witness cannot
make an impossible declared end valid; validity must hold in a single
concrete filling. Unresolved specialist administration or an explicit
computational limit retains its named refusal. This distinction also
applies when the caller
requests a test other than disability: establishment is a fact of the
same declaration, not a conclusion restricted to the requested output.

The tables inventory the fact-pattern input errors, every UNKNOWN collapse,
and the mathematical or computational bounds. Exact-type, enum,
provenance/value, convention-identifier, amount-domain, and representation
errors are schema checks and do not assert statutory impossibility.
Calendar and chronology restrictions that also form part of the declared
interface are identified explicitly below. They do not adjudicate an
undeclared application, service, recovery, or administrative ending.

Capture shorthand refers only to files in
`tests/data/track_b/insured_status_sources/`: `B` is
`ecfr_20cfr404_subpart_b.xml`; `A216` is
`lii_usc_42_416_excerpts.txt`; `A213` and `A214` are the corresponding
`lii_usc_42_413_excerpts.txt` and `lii_usc_42_414_excerpts.txt`;
`C315`, `C320`, and `C321` are `ecfr_20cfr404_315.xml`,
`ecfr_20cfr404_320.xml`, and `ecfr_20cfr404_321.xml`;
`RS .nnn` means `poms_rs_00301_nnn.html`. Quoted text below is from those
captures. An interface premise is labeled as such rather than attributed
to a statutory sentence that does not state it.

| ID and input-error premise | Captured text and alternative-route defense |
| --- | --- |
| I1. A period cannot end before its onset or derived insured start; a supplied administrative end requires a declared established current period and closes a calendar month. | A216(i)(2)(C) says a period begins on the disability day or "the first day of the first quarter thereafter"; (D) says it ends "with the close" of the earlier listed month. C321(a), (c) agree. Every specialist route must still have a nonempty chronological period; no ordinary witness alone decides whether a specialist supplied the insured start. The end/established association is also a declaration contract. |
| I2. Birth, disability onset, death, prior periods, entitlement, and SSN assignment must have consistent lifetime ordering. A query or coverage end cannot precede birth; medical onset or supplied entitlement cannot follow the query month; onset cannot follow death. | B404.102 defines "You or your" as "the worker whose insured status is being considered"; A216(i)(2)(A) requires a period "during which an individual was under a disability". Dates refer to that same living worker. This lifetime and observation-calendar contract is independent of the insured route. It permits onset later within the query month and the quarter of death rather than imposing a day-of-query restriction. |
| I3. An established period must start before its FRA-ending boundary, including no start in the FRA month; all supplied prior periods are capped at the preceding month end. | A216(i)(2)(B): "no such period shall begin ... after such individual attains retirement age"; (D)(i) ends at "the month preceding the month" of FRA. C321(a), (c)(1) say the same. A start after the mandatory month-end is impossible under both clauses, including first-day birthdays. The cap supplies no evidence against an earlier UNKNOWN end. |
| I4. Supplied prior periods precede the current event/onset and query, do not overlap calendar quarters, and stay within the lifetime. | B404.130(f) refers to "a prior period of disability established for you". C321 gives chronological beginning and ending rules. Nonoverlapping quarter intervals are the declared history representation; specialist credits cannot change what "prior" or a unique represented quarter means. A known overlap is invalid, but overlap between a supplied prior period and a start derived in one UNKNOWN-earnings representative cannot disprove other fillings with a later nonoverlapping start. UNKNOWN history is not treated as supplied empty history. |
| I5. A supplied `special_insured` prior period begins before the age-31 attainment quarter. | B404.130(d)(1): a prior period "began before age 31" and the worker "were only insured under paragraph (c)"; (c)(1) requires age 31 not yet attained. A216(i)(3)(B)(iii) expressly uses "before the quarter" of age 31. The flag declares this particular adjudicated young-worker route, not every possible special credit regime. |
| I6. An alien worker's actual pre2004 SSN assignment conflicts with declared SSPA applicability; birth on/after January 1, 2004 conflicts with declared exemption. Both never-assigned and an assigned SSN, or assignment before birth, remain invalid. A worker born before 2004 may pair a post2003 assignment or never-assigned status with an adjudicated exemption. | RS .102 B.1 says an alien assigned an SSN before 2004 "is exempt", including a nonwork SSN. B.3.b says, "If an alien worker could have legitimately been assigned an SSN before 1/1/2004, the worker is exempt from the requirements of section 211 of the SSPA." Its wrong-number SS-5 scenario issued another person's number "instead of assigning the alien worker their own SSN". Thus observed or convention-filled exemption overrides either later-assignment or never-assigned presumptions when legitimate pre2004 assignment was possible. Birth on/after January 1, 2004 rules out that exception independently of the assignment record. B.4.b's worker without an SSN "is nevertheless considered to meet the work SSN requirement" when work-authorized; meeting that requirement alone supplies no exemption. |
| I7. Explicit quarterly QCs or positive quarterly wages cannot occur before birth, after the query/coverage-end quarter, or after the death quarter. Every required coverage year is declared exactly once through the earliest query, exit, or death year. | A213(a)(2)(B)(i), (v): "no quarter after the quarter in which an individual dies" and "no quarter shall be counted ... prior to the beginning of such quarter"; B404.146(a)-(b) agree. Birth and supplied-record exit caps, complete years, and no implicit zeros are interface premises. Annual counts are capped rather than dated after exit. Specialist earned-basis or additional-credit declarations remain refusals and do not reinterpret an explicit ordinary covered-quarter declaration. |
| I8. A declared current establishment with no possible insured start is invalid only after the shared possibility check excludes every route and every feasible prior/earnings filling. One ordinary filling must satisfy the start, declared end, continuity, and overlap constraints together. | C320(b)(2) requires insured disability "in the calendar quarter in which you became disabled, or in a later calendar quarter"; C321(a) chooses the first such quarter. B404.130(a) says "four different rules"; RS .480 supplies an additional historical test with "at least 20 quarters of coverage" and every qualifying 1951 quarter, subject to its own 20/40 exclusion through the quarter containing the last day of the month before FRA, for every person (A216(i)(2)(D), C315(a), C321(a)–(b)). Independent flagged and automatic guards preserve available routes; the automatic pre1956 scan obeys the same immutable starting horizon. The ordinary scan is capped by the declared end and continuity date as well as query/death/FRA. Maximum credits decide whether insurance by that fixed date is possible. A failure caused by a derived prior-quarter overlap first checks whether any candidate starting quarter clears the supplied periods, then requires a lower-credit or enumerated filling with a nonoverlapping first start by the same cap. An ordinary or alternate starting witness after the declared end never supplies possibility. Nor can a later 20/40 witness establish impossibility on every reading of RS .480 A: C321(b) makes the earlier pre-FRA ending evidence that disability ended in this era. The named alternate refusal preserves that defensible route. For an UNKNOWN end, only a witness through the continuity date, or onset when continuity is absent, is shared by every ending completion. |
| I9. Fewer than six maximum feasible ordinary lifetime QCs proves current establishment impossible only when all specialist possibilities have already been excluded. | B404.110(b)(1): "You need at least 6 QCs but not more than 40 QCs"; B404.130(a): "you must be fully insured". B404.110(a) separately names deemed veteran/nonprofit routes, and RS .131/.350 cover other credits. Those alternatives prevent applying the ordinary six-QC input-error proof to a potentially valid specialist declaration. A record composed entirely of direct final QC declarations (`qc_count` or `qc_quarters`) and UNKNOWN years already fixes or bounds all admissible QCs, including RR credits, so the RR flag cannot add quarters beyond that envelope. This is the direct-credit input contract, not a claim that ordinary RSDI credits always exhaust freeze credits: RS .131 expressly allows credits "not creditable for other" purposes. If earnings allocation or that final-credit declaration is unresolved, the RR route remains possible; RS .230 and .350 supply annual and historical RR credit rules. Period exclusions alone cannot add ordinary QCs. |
| I10. The supported calendar, mandatory historical sex, and explicit establishment declaration must be supplied: birth years 1870–9900, query years through 9990, sex for births before January 2, 1913, and establishment provenance whenever onset is present. | These are interface-domain requirements. B404.110(b)(2) and .132 apply different historical male/female endpoints; B404.110(c) excludes only a period "we established for you". Missing facts are not inferred. Calendar limits reserve space for date arithmetic and assert no legal incapacity outside the implementation domain; alternative credit routes cannot supply missing declared facts. |
| I11. A continues-through observation requires established disability, cannot precede medical onset or the first feasible insured start, cannot exceed the pre-FRA or death boundary, and cannot follow a declared administrative end. | C320(b)(2) and C321(a) require the insured start; A216(i)(2)(D) and C321(c) bound the period's end. A declaration that a period was in force on a date requires that date to lie within one possible period. This is a dated observation, not an asserted ending; a date later than the query is allowed. Provenance and convention identifiers follow the existing fact schema. |
| I12. A raw-credit conversion refusal cannot hide established-period impossibility that every feasible filling of that row preserves. | C320(b)(2), C321(a), and B404.110(b)(1) supply the insured-start and six-QC premises. The #530 input contract puts input errors before coverage refusals. Schema validation remains first; the four conversion refusals are deferred only for this proof, with unresolved rows bounded by feasible ordinary quarters. A surviving filling preserves the original refusal reason and note rather than manufacturing a supported status. |
| I13. If no starting quarter from onset through the immutable horizon clears all supplied prior-period quarters, current establishment is impossible independently of credit fillings, their count, or a specialist route. | C320(b)(2) and C321(a) require an insured beginning within that interval; I4's nonoverlapping-quarter representation applies to that same beginning. A credit route cannot move a candidate outside the fixed interval or remove a supplied prior quarter. This fixed contradiction is checked before specialist possibility and filling enumeration; it does not treat UNKNOWN prior history as supplied empty history. |

| ID and UNKNOWN collapse | Captured text and alternative-route defense |
| --- | --- |
| U1. UNKNOWN prior history can collapse to empty solely for impossibility validation when no earliest prior period could start insured, on/after birth, before current onset and the FRA end. | C320(b)(2) and C321(a) require an insured beginning without a still-earlier period. A216(i)(2)(A) permits "five full calendar months' duration or" DIB entitlement "for one or more months". The scan therefore admits a one-month period and maximum feasible earnings. Any possible ordinary or specialist starting route stops the proof. It establishes no observed empty-history fact. |
| U2. UNKNOWN current establishment needs no new-period alternative if there is no medical onset or onset is at/after the statutory latest starting month. | A216(i)(2)(A)-(D) and C321 prohibit a period without disability or a nonempty pre-FRA interval. This removes an impossible new-period alternative only; it does not remove UNKNOWN prior history or an existing period's UNKNOWN administrative end. |
| U3. With unknown prior/current periods, true ordinary status under favorable all-period disregard decides true. | C320(a): "If benefits ... would be denied or reduced because of a period of disability, the period of disability will not be taken into consideration." B404.130(f) also permits counting all prior quarters if favorable. RS .120 requires all periods used or all disregarded; selective exclusions are not assumed. Specialist credit regimes are refused first. |
| U4. With unknown periods, fewer than six maximum feasible QCs decides false only on the ordinary route after specialist possibilities are excluded. | B404.110(b)(1) and B404.130(a) supply the six-QC prerequisite. U3's disregard cannot manufacture credits. Deemed, transitional, foreign, military/railroad, and automatically revealed historical alternatives retain named refusals instead of using this ordinary collapse. |
| U5. UNKNOWN earnings decide a requested Boolean only if all lower/upper ordinary earnings witnesses agree, under the permitted fixed-period/all-period treatments; an uncertain established start refuses only after at least one feasible filling survives. | B404.143 credits one QC for each increment, maximum four; B404.130 and .146 supply assignment/exclusion rules. Adding ordinary QCs cannot invalidate a fixed treatment. A derived start cannot be silently held fixed when the completion changes it. If a lower or upper representative cannot construct the declared period, but another single filling meets its end, continuity, and prior-overlap constraints, the public result is `unknown_earnings_years_decide_status`. If no ordinary filling can qualify by the declared end and all independent routes are impossible, it is an input error and creates no row. A deferred raw-conversion row uses temporary unknown fillings only for possibility, then retains its conversion refusal. Specialist possibilities and administrative-end candidates are considered separately. |
| U6. UNKNOWN administrative end decides a status only when every end-quarter candidate from start through query/cap, plus permitted continuation, agrees, after applying any continuity lower bound. | A216(i)(2)(D) uses "whichever ... is the earlier"; C321(c)(3) includes "the last month for which you received benefits" after substantial gainful activity. Medical continuity cannot exclude early ends; a dated administrative continuity observation can. FRA/death caps limit the latest candidate and do not turn the unknown into a fact. Both ending and prior-history unknown facts remain disclosed when both are missing; UNKNOWN prior history uses the universal envelopes rather than inventing a derived current period to enumerate. An actual supplied end keeps its declared-date semantics; known ending provenance requires an ending date. |
| U7. UNKNOWN SSPA applicability preserves an ordinary QC-only false status, but never a QC-only true status. | RS .102 B.2 says the worker "must meet one of the following additional requirements" and may fail "even if" the QC requirement is met. Applicability can remove ordinary insurance and cannot supply missing QCs. Known applicability retains adjudication refusal; any separate specialist path is refused first. |
| U8. With UNKNOWN prior history, a known current period's start is certain onset only if the lower-credit favorable-disregard witness already insures at onset; otherwise the start stays unknown. | A216(i)(2)(C) and C321(a) make insured onset the earliest legal start. C320(a)'s disregard permits that witness, and no route can move this period before medical onset. Other potentially valid histories prevent an impossibility error but do not fabricate a start. |
| U9. A continues-through observation removes only candidate administrative ends before its date; it never supplies an ending endpoint or removes UNKNOWN-end disclosure. | C321(c) enumerates actual ending events. Observation of a period still in force supplies a lower bound on those events, not their occurrence. Same-quarter ends remain possible, while a later-quarter observation makes the query quarter interior. |
| U10. An automatic alternate-pre1956 possibility can be removed for every filling only when the lower-credit filling already has ordinary 20/40 in a quarter covered by every ending completion, before October 1960. | RS .480 A makes the test available only to a disabled worker who "does not have 20/40 for freeze or DIB in any quarter before 10/60". Ordinary fixed-treatment recent-credit counts are monotone in added credits. The scan uses the ordinary 40-quarter window with favorable all-period use/disregard, from onset through the earliest of query, 1960Q3, and the quarter containing the last day of the month before FRA, for every person (A216(i)(2)(D), C315(a), C321(a)–(b)). A quarter stays eligible if FRA falls in its second or third month. It does not substitute the young-worker or blindness rule. For established current periods it additionally ends at the declared end, or the continuity date when the end is UNKNOWN, or onset when both are UNKNOWN. C321(b) governs pre-December-1980 endings; its earlier ending is tied to ended disability rather than an independent administrative event. RS .480 A's "any quarter" supports a literal wider scan, but "though under a disability" and "for freeze or DIB" support excluding post-period witnesses. Where they differ, retain the named alternate refusal. Only a lower-credit 20/40 witness shared by every period-ending completion excludes the alternate for every completion; an upper-only witness cannot do so. Application facts remain absent and are not inferred from this exclusion. The same guard is used for current-establishment and earliest-prior-history possibilities. |

| ID and bound | Captured text and alternative-route defense |
| --- | --- |
| B1. UNKNOWN annual ordinary QCs range from zero through four, reduced by assignable birth/query/death/exit quarters. Deferred raw-conversion rows use their feasible minimum/maximum fillings only for establishment possibility. Exact annual amounts are monotone in earnings; every calendar year stays in 0–4. | B404.143: "we cannot credit you with more than four QCs for any calendar year"; A213(a)(2)(B)(vi) prohibits duplicate calendar-quarter QCs; B404.146 excludes unbegun/death quarters. Birth/exit are supplied-record premises. Additional-credit regimes retain refusal and cannot escape this bound through an ordinary result. Deferred rows still raise their original conversion refusal after a valid possibility survives; no temporary filling is exposed as a computed status. |
| B2. Ordinary fully insured requirements lie in 6–40 and exclude only established disability years. Every elapsed-year endpoint uses its relevant candidate year and the historical sex/cohort rule. | B404.110(b)(1), (b)(2), (c), .132; A214(a) says "not counting ... any year any part of which was included in a period of disability". Medical onset without establishment cannot freeze years. Deemed/transitional alternatives are refused before using the ordinary requirement as universal. |
| B3. A simplified-pre1951 possibility uses the smallest known freeze requirement, or six for unresolved establishment/history, and maximum post1950 ordinary credits without exclusions. UNKNOWN pre1951 raw wages remain potentially decisive. | A213(c) grants "one quarter of coverage for each $400" subject to resulting fully insured status; B404.110(c)-(d); RS .315 B.1-B.2 record alternate historical/application conditions. This is an over-approximation for refusal, not a computed deemed-credit answer. A favorable ordinary witness with a higher requirement cannot narrow it. |
| B4. An alternate-pre1956 possibility uses maximum feasible QCs and any eligible 1952Q3–1955Q4 quarter with at least 20 total QCs and every preceding 1951-onward quarter credited, minimum six, only if lower credits do not already establish 20/40 in its disabled-quarter scan before October 1960. Current establishment also requires the alternate quarter to fit every fixed starting bound. | RS .480 A requires "at least 20 quarters of coverage" and "all quarters beginning with 03/51 ... are QCs" with "at least six", and limits eligibility to workers without 20/40 before 10/60. B.1 gives first freeze day 07/01/52 and last 12/31/55. The first possible freeze day is July 1, 1952; an established current period already ended, or observed in force, before then cannot use a later automatic witness. The automatic scan shares the ordinary immutable end/continuity/death/FRA horizon. The exclusion ends no later than the quarter containing the last day of the month before FRA for every person, independently of established, absent, or UNKNOWN period status (A216(i)(2)(D), C315(a), C321(a)–(b)). An established current period further limits exclusion to the quarter containing the declared end; an UNKNOWN end limits it to the continuity date's quarter, or onset's quarter without continuity. These bounds preserve a named refusal when the literal any-quarter reading and the period-limited reading differ, and ensure that an UNKNOWN result holds for every declared-end completion. A successful ordinary DISABILITY witness beginning in or after the FRA month cannot bypass an otherwise possible alternate refusal. Pre-FRA ordinary witnesses retain their results when the applicable period-covered bound also permits exclusion. A lower-credit ordinary 20/40 witness removes the route for all fillings; an upper-only witness leaves it possible. Unmodeled application restrictions can only remove candidates, so they cannot justify an input error. Explicit specialist flags remain independent possibilities. |
| B5. Universal recent, fully-prerequisite, and annual count envelopes use zero through maximum feasible ordinary lifetime/year QCs whenever unknown periods/earnings can switch witnesses. | A213(a)(2)(B)(vi) prohibits double credit; B404.146(d) excludes interiors unless disregarded. Every concrete ordinary assignment is a subset of feasible unique lifetime quarters. The envelope permits every witness, even when adding QCs switches to a lower-count witness. Specialist possibilities remain refusals. |
| B6. With known earnings and an UNKNOWN ending, returned count bounds include all end-candidate counts admitted by continuity; with entirely known facts they remain exact. | B404.120(b), .130(f), .146(d) distinguish credited endpoints and excluded interiors. All candidate quarters are enumerated, including early endpoints and capped-FRA candidates, subject to any continues-through observation; extrema therefore cover each completion. A continuity date is never inserted as a credited endpoint. No monotonic endpoint-count premise is used. |
| B7. DLI lies through query without frozen exit, or through the pre-FRA-quarter/death horizon with frozen coverage; `None` is the bottom bound. A future exit cannot remove query censoring. | RS .148 defines DLI as "the last day in the last quarter" in which status is met and limits the search relative to FRA. B404.146(b) caps credits after death; A216(i)(2)(B) caps new periods. Future undeclared work is not assumed zero. Specialist routes are refused before this ordinary DLI calculation. |
| B8. For a nonblind ordinary worker with no prior period, no DLI can lie more than 39 quarters after the last credited quarter. | B404.130(b)(2) requires "at least 20 QCs in the 40-quarter period ... ending with that quarter". After 39 later quarters no original QC remains. Blindness and prior-period special/exclusion routes disable this search shortcut; flagged or observable specialist routes refuse. |
| B9. With unknown periods the disregard DLI is a lower bound and the permitted query/FRA/death horizon is the upper bound; unknown SSPA applicability reduces any positive DLI lower bound to `None`. | C320(a) permits favorable disregard; B404.130(f) permits counting all prior-period quarters; RS .102 B.2 imposes an additional requirement. The bound does not infer a particular recovery or history. Exemption can recover the ordinary upper witness but cannot exceed the calendar horizon. |
| B10. UNKNOWN-ending DLI bounds include every end candidate. With an unresolved ongoing end, known prior history, and frozen-exit future horizon beyond query, the named DLI-horizon refusal remains. | C321(c)'s alternative endings and RS .148's last qualifying quarter permit different historical DLI witnesses. The candidate extrema bound all declared endings; no recovery beyond the query is inferred. Refusal covers the unobserved future administrative fact. |
| B11. At most 4,096 combinations of disability endpoint assignments are searched exactly. | B404.143(b) and RS .230 permit favorable assignment; B404.130(f) makes endpoint credits decisive. The limit is computational coverage, not a statutory impossibility bound: exceeding it returns `disability_boundary_assignments_unsupported`, never a false status or input error. |
| B12. Ordinary counted windows have 13 quarters for current insurance and 40 for ordinary disability; young/subsequent special windows require half their elapsed quarters after dropping an odd remainder, with a six-QC minimum and 20/40 ceiling. | B404.120(a) says "13-quarter period"; .130(b) says "20 QCs in the 40-quarter period"; .130(c)-(d) and A216(i)(3)(B) supply the half-quarter, odd-remainder, and 6/12 alternatives. Blindness uses only the fully insured prerequisite, and pre1956/flagged specialist paths retain refusal rather than being forced through an ordinary window. |
| B13. Indexed annual QC amounts are at least the prior year's statutory increment and the rounded indexed 1978 amount, with nearest-$10 rounding and $5 ties upward. | A213(d)(2) chooses "the larger of" the prior increment and indexed amount, rounded to "the next higher multiple of $10" at a $5 tie. This exact parameter calculation has no disability or specialist alternative; input-domain checks require positive NAWI and a statutory prior increment. |
| B14. Declaring continuity never widens the administrative-end candidate set; every returned status and count envelope remains valid for every retained concrete ending. | C321(c)'s ending events still govern. Set intersection with ends on/after the observation can only remove candidates; it creates neither an ending nor a new credit. The universal envelope remains unchanged where other unknown facts require it. |
| B15. Ordinary establishment overlap resolution enumerates at most 4,096 unknown-credit fillings after its fixed-date monotonicity and candidate-quarter exclusion checks. | C320(b)(2) and C321(a) require one insured beginning consistent with the complete declaration. If every possible starting quarter overlaps a supplied prior period, I13 settles impossibility without enumeration. Otherwise this is a computational coverage bound. An unresolved search beyond the limit returns `disability_boundary_assignments_unsupported`; it never asserts that a concrete filling exists or proves an input error. |
| B16. A deferred raw-conversion row retains independently computable ordinary credits in its minimum and every enumerated filling, and cannot exceed feasible calendar-quarter credits in its maximum. | A213(d)(2)'s prior-increment floor bounds future annual credits above by the captured 2027 increment applied to the supplied wages plus SE income; the possibility-only lower bound is zero. Raw 1937 allocation remains zero through four because A213(b)'s half-year rule is unresolved. For separate pre1955 agriculture or pre1951 SE, supported quarterly wage credits and supported post1950 calendar-year SE credits remain fixed; unresolved additional allocation can fill only remaining allowed quarters. Both minimum and maximum fillings may violate derived overlap even when a middle filling is valid, so neither endpoint alone proves impossibility. These bounds do not adjudicate a specialist allocation or replace its refusal. |

The round-5 adversarial audit revisits each row in both directions in
`scratch/review/round5-premise-audit.md`: a valid filling cannot be rejected,
and a provably all-invalid declaration cannot become a denominator row.
The fixed-end counterexamples correct I1/I8/U5 and the automatic historical
cap in B4; the wrong-number SS-5 exception and its required possible pre2004
assignment correct I6; continuity adds I11/U9/B14. These are source and
interface requirements, with no new statutory reading.

Round 6 additionally checks both directions of refusal deferral (I12/B1),
the alternate test's own 20/40 exclusion (U10/B4), and fixed-quarter overlap
impossibility before a filling limit can apply (I13/B15). Deferred refusals
cannot supply evaluator rows for all-invalid declarations, while a
concrete valid filling retains the named refusal. The 20/40 exclusion
must preserve valid current establishment and possible earliest prior
periods. These changes apply the #530 input contract and captured rules;
they introduce no statutory reading.

The round-5 exactness grid checks both directions against every concrete
completion, rather than only checking that rejection is sound.
`test_unknown_declaration_exactly_matches_all_concrete_qc_fillings`
uses one or two UNKNOWN modern years (all five or 25 annual-count
fillings), known counts zero through four, January/March/June/December
ends, and blind/nonblind workers.
`test_overlap_declaration_exactly_matches_every_quarter_filling` uses
four missing-year shapes, prior endings in December 1971 or January 1972,
current endings in March/December 1972 or January 1973, and every one of the
16 pre1978 quarterly masks. The specialist grids retain the automatic
alternate-pre1956 route and every `CoverageCondition`.
`test_exact_classification_keeps_each_independent_flagged_route` also
disables the automatic pre1956 guard, proving that each flag preserves
its route independently; the RR case supplies unresolved pre1978
compensation rather than a final direct-QC envelope. The short-DIB grid
supplies empty and three one-month prior-history fillings.
Each concrete declaration either raises an input error or survives as a
status/refusal; the UNKNOWN declaration must be invalid exactly when all
concrete fillings are invalid. Every surviving UNKNOWN declaration is
also evaluated to assert one retained row and its exact weight.

Two corners are excluded by name from this exactness claim. Arbitrary
UNKNOWN prior history is not exhaustively enumerable in this bounded
grid: its earliest-period possibility proof intentionally leaves
unobserved administrative histories unresolved, while the explicit
short-DIB fillings test the retained existential witness. Large
ordinary-overlap searches remain excluded only when the fixed
candidate-quarter scan leaves a possible nonoverlapping starting quarter
and more than 4,096 credit fillings are still unresolved. They retain the
named computational refusal; that refusal asserts neither existence nor
impossibility. If every starting quarter overlaps a supplied prior period,
the declaration is invalid even above that filling limit. Specialist
administrative adjudication is outside the implemented ordinary surface;
the specialist grid checks preservation of a possible route and its
denominator, rather than claiming to adjudicate it. No bounded ordinary
grid case is silently excluded.

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
| A returned ongoing-period status agrees with concrete ending-quarter and continuing completions, and the returned recent/fully QC counts contain their counts; round 4 extends this to every candidate from the start through the cap, retaining UNKNOWN at FRA. | `test_ongoing_period_completion_status_and_count_bounds_are_sound` |
| Proving an UNKNOWN declaration invalid implies all enumerated valid-calendar, insured-start empty/one/two-period and annual-QC fillings are invalid; a valid filling prevents that error. | `test_invalid_unknown_declaration_has_no_valid_enumerated_filling` |
| A valid long prior special period can rescue current establishment; UNKNOWN history must retain that possibility even when observed empty history would be invalid. | `test_valid_prior_freeze_filling_prevents_false_invalidity` |
| Declared ending facts and provenance round-trip, inconsistent values/provenance/convention identifiers are invalid, and the original twenty positional Person fields keep their meaning. | `test_declared_period_end_provenance_roundtrip_and_invalid_combinations` |
| Automatic simplified pre1951 refusals obey exact $400 aggregate boundaries and arise without an opt-in specialist flag. | `test_pre1951_refusal_tracks_exact_400_dollar_status_boundary` |
| Mapping order and observed/convention provenance do not change the automatic simplified-pre1951 reason. | `test_pre1951_refusal_is_independent_of_mapping_order_and_provenance` |
| Automatic pre1951 detection bounds the lower fully insured requirement from a known disability freeze at exact aggregate-dollar boundaries, even when the ordinary witness selects a higher requirement. | `test_pre1951_refusal_bounds_every_known_freeze_requirement` |
| Automatic pre1956 alternative refusals require at least 20 possible QCs and the continuous qualifying 1951 window. | `test_pre1956_refusal_requires_twenty_qcs_and_the_continuous_window` |

Round 4 extends those invariants across every statutory alternative:

| Invariant | Hypothesis test |
| --- | --- |
| If an UNKNOWN administrative ending returns a requested status, every declared ending-quarter completion from the period's start through the query/cap has that status. Recent, fully-prerequisite, and annual QC ranges contain every completion, including earlier endings and FRA queries; ending uncertainty remains disclosed. | `test_unknown_end_status_and_every_count_cover_all_quarter_completions` |
| Every concrete administrative-ending DLI lies within the returned UNKNOWN-ending DLI range. | `test_unknown_end_dli_contains_every_administrative_end_completion` |
| An `InvalidFamilyInput` establishment conclusion excludes every enumerated ordinary, one-month/short-DIB-entitled, alternate-pre1956, and flagged-specialist filling; every valid refusal retains its evaluator row and weight. | `test_invalid_declaration_has_no_short_or_specialist_valid_filling` |
| An alternate-pre1956 earliest prior period prevents UNKNOWN prior history from being proved empty, even when the later current onset itself is after 1955. | `test_unknown_prior_history_preserves_pre1956_alternate_prior_start` |
| A valid UNKNOWN-earnings completion with its insured start on/before the declared period end prevents an input error, even if another representative starts after the end; uncertainty retains a refusal and denominator row. | `test_possible_unknown_earnings_filling_prevents_declared_end_input_error` |
| A valid lower-credit completion whose derived current start does not overlap a supplied prior period prevents an input error, even if the upper-credit representative overlaps its ending quarter; uncertainty retains a refusal and denominator row. | `test_possible_lower_earnings_filling_prevents_upper_overlap_input_error` |

Round 5 adds exact classification and administrative continuity:

| Invariant | Hypothesis test |
| --- | --- |
| Over the bounded modern and pre1978 overlap grids, `InvalidFamilyInput` occurs exactly when every concrete credit filling is invalid. A surviving filling prevents rejection, while an all-invalid declaration never acquires an evaluator row. | `test_unknown_declaration_exactly_matches_all_concrete_qc_fillings`, `test_overlap_declaration_exactly_matches_every_quarter_filling` |
| The automatically detected alternate-pre1956 start obeys the same fixed declared-end and continuity bounds as an ordinary start. A bound before July 1952 cannot use the first permitted July 1, 1952 freeze; a later permissible bound preserves the specialist refusal. | `test_automatic_pre1956_start_respects_immutable_bound_property` |
| An automatically detected historical start must fit before the actual month-before-FRA end, including when FRA and the first possible alternate start share July 1, 1952. | `test_automatic_pre1956_start_respects_fra_cap_property` |
| An adjudicated section 211 exemption preserves the ordinary status/count result and one evaluator row for source-permitted post2003 and never-assigned facts; observed and convention-filled facts have equal statutory treatment. Pre2004-assigned aliens accept exactly the exempt declaration and reject declared applicability. An alien born on/after January 1, 2004 cannot supply the required possible pre2004 assignment and therefore cannot declare exemption. | `test_adjudicated_exemption_preserves_ordinary_count_and_evaluator_row`, `test_pre2004_assignment_accepts_exactly_the_exempt_applicability`, `test_wrong_number_exemption_requires_possible_pre2004_assignment` |
| A continuity declaration never widens the candidate-ending set. Every returned status and count envelope agrees with or contains every retained concrete ending; no continuity observation becomes a credited endpoint. | `test_continuity_only_narrows_candidates_and_all_concrete_ends_agree` |

Round 6 adds refusal ordering and settled route exclusions:

| Invariant | Executing tests |
| --- | --- |
| Adding any of the four early raw-conversion refusal facts where it cannot change an all-invalid declaration preserves `InvalidFamilyInput`, zero rows, and zero weight, independently of mapping order. Placing it where concrete credit fillings can validate the declaration preserves the original refusal reason and note. Multiple deferred reasons retain sorted-year priority, including when an overlap search reaches its coverage limit. | `test_irrelevant_early_refusal_fact_preserves_all_invalid_grid_case`; `test_every_early_qc_refusal_preserves_possible_declaration`; `test_deferred_refusals_keep_original_sorted_year_priority`; `test_unresolved_overlap_keeps_original_deferred_refusal` |
| An unsupported future increment cannot hide a fixed earlier impossible end, for zero, one, or 10,000 raw wage dollars, including the age-62 and coverage-exit interfaces. The captured increment floor can prove too few possible credits; a sufficient possible filling keeps the original refusal. All schema/history errors still precede deferred refusals. | `test_unrelated_uncaptured_increment_cannot_hide_impossible_fixed_end`; `test_uncaptured_increment_bounds_preserve_both_classifications`; `test_schema_validation_precedes_deferred_qc_refusals` |
| A lower-credit 20/40 witness in a quarter covered by every ending completion, before October 1960, makes the automatic alternate unavailable under every added unknown-credit filling. The scan includes later disabled quarters and 1960Q3 only when covered by every ending completion, excludes 1960Q4 and quarters beginning in or after the FRA month for every person, and does not substitute blindness or the young-worker rule for 20/40. A declared end includes its own quarter; an UNKNOWN end permits exclusion only through the continuity date or, without continuity, onset. An upper-only witness preserves the alternate refusal and evaluator row. | `test_fixed_twenty_of_forty_exclusion_survives_extra_unknown_credits`; `test_twenty_of_forty_before_october_1960_excludes_alternate_refusal`; `test_twenty_of_forty_scan_includes_later_disabled_quarters_before_1960`; `test_twenty_of_forty_alternate_exclusion_stops_before_october_1960`; `test_alternate_exclusion_uses_existing_disability_scan_fra_boundary`; `test_other_ordinary_disability_routes_do_not_supply_twenty_of_forty`; `test_some_twenty_of_forty_fillings_keep_named_alternate_refusal`; `test_independent_date_oracle_classifies_both_alternate_scan_directions` |
| Excluding an unavailable alternate does not reject an ordinary current establishment or prove possible nonempty prior history empty. | `test_excluding_alternate_preserves_ordinary_current_establishment`; `test_excluding_alternate_preserves_possible_nonempty_prior_history` |
| If every possible starting quarter overlaps a supplied prior quarter, changing credit uncertainty cannot create a valid establishment or a refusal row, even above the filling limit. A neighboring nonoverlapping valid filling remains possible and retains the earnings refusal. | `test_immutable_overlap_is_independent_of_credit_uncertainty`; `test_fixed_same_quarter_overlap_precedes_large_filling_refusal`; `test_large_overlap_neighbour_keeps_valid_filling` |
| Deferred historical-credit fillings retain every independently guaranteed quarter. A valid middle filling prevents rejection even when both endpoints are invalid; fixing an overlapping first quarter can instead make every admissible filling invalid. Mapping order changes neither conclusion. | `test_deferred_quarter_fillings_keep_fixed_minimum_and_valid_middle` |

Round 7 pins the eligibility boundary independently of the ordinary scan:

| Invariant | Executing tests |
| --- | --- |
| For the round-7 cases, whose declared ends are the month before FRA, a 20/40 witness excludes the alternate exactly when its quarter begins before the FRA month and before October 1960, over all twelve FRA months and witness quarters. An earlier period-covered bound can further restrict exclusion, as pinned in round 8. Exclusion yields the ordinary result or a genuinely impossible declaration; non-exclusion preserves the named refusal, one evaluator row, and weight 7/3. | `test_independent_date_oracle_classifies_both_alternate_scan_directions` (Hypothesis with an independent date oracle); `test_fra_quarter_stays_only_when_it_begins_before_fra_month` |
| Established, absent, and UNKNOWN current-period declarations share the same FRA exclusion bound. Successful ordinary pre-FRA neighbours retain their results. | `test_unestablished_period_keeps_alternate_after_fra`; `test_unestablished_period_pre_fra_neighbour_keeps_ordinary_result`; `test_reviewed_fra_neighbours_preserve_their_public_results` |
| The reviewed FRA-month witness retains the historical refusal and exact denominator weight under the ordinary query and OP12 exit; a deferred 1937 conversion retains its original reason instead. | `test_fra_month_witness_keeps_reviewed_refusal_and_denominator` |

Round 8 limits exclusion to quarters covered by every ending completion:

| Invariant | Executing tests |
| --- | --- |
| A lower-credit 20/40 witness excludes the alternate exactly when its quarter begins on or before the established period's covered date, before the FRA month, and before October 1960. The covered date is the declared end, the continuity date for an UNKNOWN end, or onset when neither is supplied. The ending quarter remains eligible even when the end is in its middle month; the next quarter does not exclude. Both computed and refused outcomes retain one evaluator row and exact weight 11/5. | `test_declared_end_quarter_includes_witness_but_next_quarter_refuses`; `test_unknown_end_keeps_onset_witness_but_refuses_later_quarter`; `test_continuity_quarter_includes_witness_but_later_quarter_refuses`; `test_later_disabled_quarters_with_unknown_end_keep_named_refusal`; `test_october_1960_boundary_with_unknown_end_keeps_named_refusal`; `test_independent_date_oracle_classifies_covered_quarters_both_directions` (Hypothesis with an independent date oracle) |
| If any declared-end completion preserves the named alternate refusal, an UNKNOWN ending returns no status. An onset-quarter witness remains shared by every completion; a witness in a later quarter without continuity does not. | `test_unknown_end_cannot_return_status_when_declared_completion_refuses` (Hypothesis); `test_unknown_end_keeps_onset_witness_but_refuses_later_quarter` |
| The round-7 comparison's ordinary witness after the declared end preserves `disability_before_1956_unsupported`, one evaluator row, and exact weight 11/5. It cannot prove invalidity under every defensible reading. | `test_round_seven_declared_end_comparison_retains_named_refusal`; `test_alternate_exclusion_uses_existing_disability_scan_fra_boundary` |

The UNKNOWN-end completion invariant does not establish the corresponding
claim for UNKNOWN establishment. The round-7 pre-FRA neighbour born May 2,
1895, with onset July 15, 1955 and first 20/40 in 1960Q2 still computes
ordinary disability insurance when establishment is UNKNOWN. Its
established completion with an early September 30, 1955 end instead
retains the alternate refusal. The successful ordinary short circuit in
`_observable_coverage_paths` precedes that prospective established-period
check. `test_unestablished_period_pre_fra_neighbour_keeps_ordinary_result`
pins the unchanged UNKNOWN-establishment result; the round-8 report records
this separate discrepancy and its conflict with the instruction to preserve
that existing expectation.

The invented boundary example has birth April 2, 1895, female sex, onset
July 15, 1955, and an observed established period ending March 31, 1960.
It has one QC in 1940Q1, all quarters credited in 1951–1954, the first
three credited in 1955, one in 1960Q2, and explicit zeros elsewhere through
1968. It has 20 lifetime QCs and all 18 continuous quarters from 1951Q1
through 1955Q2 at the alternate 1955Q3 start. Ordinary recent counts are
19 at both 1955Q3 and 1960Q1, then 20 at 1960Q2. FRA is April 1, 1960;
1960Q2 begins too late to supply a freeze or DIB month. The January 1968
FULLY query therefore preserves `disability_before_1956_unsupported`, one
row, and weight 7/3. The June 1960 OP12 coverage exit gives the same result.
Replacing the zero 1937 row with quarterly wages of $50, $0, $0, $0 keeps
`1937_earnings_allocation_unsupported` with the same row and weight.
Each birth-month neighbour retains a declared end in the month before its
own FRA: February 29, 1960 for the March birth and April 30, 1960 for the
May birth. The March neighbour also refuses by name; the May neighbour
computes fully insured with ordinary start April 1, 1960. These are invented
cases, not published worked examples.

The round-7 comparison case has birth May 2, 1888, female sex, onset July
15, 1952, observed establishment ending September 30, 1952, and observed
empty prior history. Credits are two in 1938, four in each of 1944–1946,
four in 1951, 1952Q1, Q2, and Q4, and 1953Q2, with explicit zeros elsewhere
through the January 1968 FULLY query. At onset it has the alternate route's
20 lifetime QCs and all six 1951Q1–1952Q2 QCs. Its first ordinary 20/40
witness is April 1, 1953, before the May 1 FRA month but after the declared
ending quarter. The literal any-quarter reading removes the alternate and
raises `InvalidFamilyInput` with zero rows; the period-limited reading
preserves the declaration. The pinned result is therefore
`disability_before_1956_unsupported`, one row, and weight 11/5. Moving the
twentieth recent credit to 1953Q3 also refuses, independently of the FRA
bound. These are invented comparisons, not published worked examples.

The round-8 ending-quarter examples use birth May 2, 1895, onset July 15,
1955, and 19 ordinary recent QCs before a single later witness credit.
With a May 31 or June 30, 1956 declared end, an April 1, 1956 witness
excludes the alternate and computes the ordinary start; a July 1 witness
instead retains the named refusal. With an UNKNOWN end and a May 15,
1956 continuity observation, the April witness excludes and the July
witness refuses. Each outcome retains one row of weight 11/5. The
control born February 2, 1920 remains computed with a January 15, 1955
onset-quarter witness even when the end is UNKNOWN; moving its first
ordinary witness one quarter later without continuity retains the
alternate refusal.

No new death cap is needed. History validation rejects explicit credits
after the death quarter; `_world` and `_allowed_quarters` cap every fixed
and flexible assignment there. Prior periods end by death. After the death
quarter each 40-quarter window can only lose earlier credited quarters and
add uncredited quarters, under either all-period treatment. A post-death
20/40 witness therefore implies a death-quarter witness that the scan has
already visited; no first post-death witness can reach the exclusion.

The round-6 ordering example has birth February 2, 2000, onset January 15,
2022, observed establishment ending January 31, 2022, observed exemption
and empty prior history, zero QCs through 2027, and raw 2028 wages. At the
January 2028 FULLY query, raw wages of $0, $1, or $10,000 cannot change the
zero-QC insured-start history through the declared end. Each call raises
`InvalidFamilyInput` with no row or weight; every direct 2028 count from
zero through four does too. Birth February 2, 1965 and a declared January
2028 coverage exit preserve this conclusion. Conversely, a blind worker
born February 2, 2000, with January 15, 2028 onset, a December 2028 ending,
four QCs in 2026 and one in 2027, could establish a period if 2028 supplies
the sixth credit. Raw 2028 wages of $10,000 therefore retain
`qc_amount_year_unsupported` and the evaluator's weight 3/2. The other
three conversion reasons receive the same irrelevant/relevant-filling
checks. This applies C320(b)(2), C321(a), and the #530 input contract.

For the settled historical route, birth February 2, 1920, onset January
15, 1955, and all four quarters credited in each of 1950–1954 supply 20/40
at onset. All other 1937–1968 quarters are explicitly uncredited. The
January 1968 FULLY result is insured, with current start January 15, 1955;
RS .480 A excludes its alternate and application facts need not be guessed.
Moving the four 1950 credits to 1940 and supplying four in 1956 instead,
with a declared December 31, 1956 end after the witness, gives an ordinary
October 1, 1956 start within the exclusion scan. Leaving that end UNKNOWN
and supplying no continuity instead preserves
`disability_before_1956_unsupported`, one row, and weight 11/5: an ending
in the onset quarter remains possible. A 1960Q3 witness likewise excludes
with a declared end after it, while its UNKNOWN-end twin refuses; 1960Q4
still cannot exclude under either ending declaration.
With 1950 UNKNOWN and the extra four 1940 credits, enumeration finds one
ordinary filling and fifteen alternate-refused fillings; the UNKNOWN
declaration preserves `disability_before_1956_unsupported` and weight 11/5.

For the fixed-overlap example, birth February 2, 1940, onset February 15,
1977, a supplied January 1, 1970–January 31, 1977 prior period, and a March
31, 1977 current end leave only 1977Q1 as a current starting quarter. Four
QCs in each of 1968 and 1969, UNKNOWN 1974–1977, and zeros elsewhere cannot
clear that prior ending quarter. The January 1978 FULLY query raises
`InvalidFamilyInput` before the 8,192 combinations could trigger the
4,096-filling limit and create a row.
Moving only the prior ending to December 31, 1976 admits a valid filling:
all four quarters credited in each UNKNOWN year give an insured ordinary
current start on February 15, 1977. The UNKNOWN declaration therefore
retains `unknown_earnings_years_decide_status` (C320(b)(2); C321(a)).

A deferred-allocation control has birth February 2, 1920, onset February
15, 1954, a July 15, 1952–January 31, 1954 prior period, current end
December 31, 1954, and January 1968 FULLY query, with observed facts.
Credits are one in 1938,
four in each of 1946–1948, one in 1949, four in 1951, and two in 1952;
other years are zero. The prior has RS .480's 20 lifetime and six
continuous credits. Of the 16 concrete 1954 masks, both all-zero and
all-four are invalid; the seven with Q1 uncredited and some later credit
are valid. Raw agricultural wages of $100 preserve
`pre1955_agricultural_allocation_unsupported`. Adding $50 of independently
credited Q1 nonagricultural wages
requires Q1 in every filling: all eight are invalid and create no row.

The fixed-end example has birth February 2, 2000, medical onset January 15,
2022, observed establishment, a January 31, 2022 declared end, four QCs
in 2021, UNKNOWN 2022 credits, and zeros elsewhere. At an April 2022
FULLY query, only five QCs can be assigned by the end's quarter: four
earlier credits plus 2022Q1. All five concrete 2022 counts fail, so the
UNKNOWN declaration raises `InvalidFamilyInput` through the evaluator;
it cannot contribute a row of weight 3/2. The nine nearby combinations
of two, three, or four 2021 QCs with January, February, or March 2022
ends fail for the same reason at an October 2022 query. The existing
round-4 lower-filling overlap and earlier-valid-end cases remain valid
UNKNOWN declarations and retain their original numeric assertions.
The overlap grid additionally minimizes an intended valid case: with the
January 1972 prior ending and December 1972 current ending, seven of the
16 UNKNOWN-1972 quarter masks are valid. They leave Q1 uncredited and
credit at least one later quarter, permitting a nonoverlapping insured
start before the fixed end. Both all-zero and all-four representatives
are invalid there, so checking only those representatives would reject a
valid declaration. Moving the declared end to March 1972 instead leaves
all 16 masks invalid; separate fillings cannot each supply half the
chronological constraints.

The automatic historical-bound counterexample has a woman born February
2, 1900, current onset January 15, 1952, observed establishment and empty
prior history, fourteen older QCs, and six QCs in the mandatory
1951Q1–1952Q2 window. She has twenty lifetime QCs but
fails the ordinary recent-work test. A March or June 1952 declared end,
or a continuity observation in either month, cannot use RS .480's first
permitted July 1, 1952 start. The declaration is therefore input-invalid.
July and September bounds instead preserve the automatic historical
route and its named refusal. This source-required chronological check is
independent of the ordinary possibility scan and of explicit specialist
flags. A woman born July 2, 1887 reaches FRA in July 1952, so her
period's latest end is June 30 and the alternate July 1 start is already
too late. An August 2 birth instead permits that start. This actual
month-before-FRA limit is shared by the ordinary and automatic scans.

The wrong-number SS-5 example has birth February 2, 1980, alien-worker
status, assignment January 1, 2004, an observed `sspa211_applies=False`,
four QCs in 2004, and two in 2005. FULLY at January 2006 returns insured,
required six, count six. The exemption is an adjudicated input justified
by RS .102 B.3.b, not an inferred exemption for every later assignment.
The never-assigned/exempt pairing is also source-permitted. A declaration
of applicability with a pre2004 assignment remains an input error. The
independent I6 audit also tested birth and assignment January 1, 2005 with an observed
exemption and six QCs at January 2026. That worker cannot have received a
legitimate pre2004 SSN; the input is invalid. The same contradiction holds
at the exact January 1, 2004 birth boundary, with a never-assigned SSN,
or without an assignment declaration. B.4.b's work-authorization route
does not rescue exemption: it satisfies the additional requirement while
retaining applicability.

The continuity example has birth February 2, 2000, blind onset January
15, 2022, observed current establishment and empty prior history, and QCs
2017=1, 2020=4, 2021=1, 2026=1. At a March 2026 CURRENTLY query,
continuity through March still admits a March 31 end with six QCs and
later endings with five, so the rule refuses by name. Continuity into
April or later makes 2026Q1 interior, yielding uninsured with count five.
With only the six earlier credits, a February 2062 FULLY query and
continuity through that month returns insured, required six, count six;
the rule records an unknown actual ending throughout. These invented
cases compute insurance only, with no benefit-amount claim.

Round-4 example/evaluator regressions separately reproduce the reviewer's
short-DIB prior period, early end and FRA-end cases, and automatic
pre1956 establishment for every requested test with UNKNOWN prior history
and UNKNOWN establishment variants. The flagged RR regression
`test_unresolved_railroad_compensation_retains_independent_flagged_route`
pins unresolved additional credits, while earlier assertions retain the
explicit final-direct-QC envelope. The round-3 two-point completion
property is extended to the wider candidate range; its earlier concrete
completion assertions are preserved.

An additional invented completion case has birth February 2, 2000,
blindness onset January 15, 2022, declared establishment and a March 31,
2022 ending, queried January 2023. There are two QCs in 2020, three in
2021, one in 2023, and UNKNOWN 2022 credits. Zero QCs in 2022 first insure
the worker in 2023, after the declared end; each concrete count from one
through four can instead start the period at January 15, 2022. The
inconsistent lower representative therefore cannot prove the UNKNOWN
declaration invalid. The rule retains `unknown_earnings_years_decide_status`
and one evaluator row, as pinned by
`test_unknown_earnings_can_place_insured_start_before_declared_end` and
`test_unknown_earnings_before_declared_end_retains_denominator_row`.

A neighboring invented case has a woman born February 2, 1910, a supplied
July 15, 1952–January 31, 1972 prior period, current onset February 15,
1972, and query January 1973. Twenty historical QCs and all six continuous
1951Q1–1952Q2 QCs support the prior period under the alternate pre1956
route. Nineteen recent QCs in 1967–1971 and one in 1973, with UNKNOWN
1972 credits, give a valid January 1, 1973 current start when 1972 has
zero QCs. Positive 1972 fillings can instead derive a start in the prior
period's ending quarter and violate the quarter-overlap representation.
That invalid upper representative does not invalidate the UNKNOWN
declaration; `test_unknown_earnings_can_avoid_derived_prior_quarter_overlap`
and the lower-filling property retain the named earnings refusal and row.

The reviewer regressions additionally pin the 2026 blind-onset endpoint
case (five continuing QCs versus six if the period ends in the event
quarter), and the 1960 birth FRA case (UNKNOWN-ending count range [2, 5]
in October 2028, with five QCs for the concrete FRA-cap ending and false
status for every candidate). They also pin
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
of the 1973 taxable ceiling of $10,800 instead reproduces $3,600 exactly,
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
work-authorized exception concerns satisfying the requirement. B.3.b's
wrong-number SS-5 exemption separately requires accepting an adjudicated
exemption even with a later actual assignment or no proper assignment
yet, provided pre2004 legitimate assignment was possible. An alien born
on/after January 1, 2004 cannot meet that premise. An actual pre2004
assignment remains expressly exempt under B.1,
so a declaration that section 211 applies in that pairing stays invalid.
Known applicable cases remain refused until that adjudication is implemented.

For simplified pre1951 credits, Act 213(c) says an individual "shall be
deemed to have one quarter of coverage for each $400 of his total wages
prior to 1951", subject to becoming fully insured with the resulting
credits plus post1950 credits. It states no seven-elapsed-year minimum.
Historical amendments explain part of the apparent difference. RS .315
B.1.a says, "Under the 1967 Amendments, use the simplified method if:"
and requires at least seven elapsed years. B.1.b then states, "The 1990
Amendments eliminated the seven EY test." Its effective-date section
requires applications effectively filed in June 1992 or later and excludes
special age-72 or transitional insurance in the filing month. Section
404.110(d)(1)(ii) likewise supplies a June-1992-or-later application
exception, conditioned on no section 227 entitlement in the application
month; paragraph (d)(1)(i) retains the seven-year rule.

The evaluator keeps the below-seven named refusal because filing,
retroactivity, and section 227 facts remain absent. It does not claim an
unqualified conflict between current statute and all regulatory/POMS
routes. Both dates in
`test_potential_simplified_method_refuses_unresolved_seven_ey_applicability`
pin this refusal: an invented woman born February 2, 1895, with $2,400 in
1940Q1 has one ordinary QC, six deemed QCs, and a six-QC prerequisite at
February 1968. Applying only the seven-year route would return false;
a favorable applicable alternative could return true. The facts supplied
do not establish that historical entitlement. Conditional on an otherwise
payable invented $1,000 monthly benefit, those answers differ by $0 versus
$1,000; this module computes neither payment.

Short DIB-entitled periods, earlier administrative endings, the alternate
pre1956 test, and the wrong-number SS-5 exemption are captured source
requirements. Dated observed continuity supplies a missing input; it is
not a new statutory reading. They introduce no additional question for Max.
Round 6's deferred raw-credit refusals implement the #530 input contract;
the alternate-route exclusion and fixed-quarter overlap apply captured
RS .480 A, C320(b)(2), and C321(a). Round 7 corrects the FRA bound using
A216(i)(2)(D), C315(a), and C321(a)–(b). Its application to every person
follows RS .480 A's “for freeze or DIB”; establishment is not a condition.
The source conflict remains
`us:oasdi-insured-pre1956-alternate-any-quarter-scan`. RS .480 A says a
worker "though under a disability, does not have 20/40 for freeze or DIB in
any quarter before 10/60". "Any quarter" supports the literal scan;
"though under a disability" and "for freeze or DIB" support the narrower
scan through the declared period. C321(b), quoted above, governs these
pre-December-1980 endings and links an earlier ending to ended disability.
The former premise that an administrative end supplies no recovery evidence
was therefore wrong for this era. C321(c) can differ for post-November-1980
endings; no wider claim about those endings is made here.

The implementation keeps the named alternate refusal wherever those
readings differ. A classification as `InvalidFamilyInput` requires every
concrete filling to be invalid on every route, so a defensible reading that
preserves the declaration prevents that input error. An UNKNOWN end needs
the same restraint: a later witness cannot exclude a route preserved by an
early declared-end completion. The invented 1888 comparison above retains
one refused row of weight 11/5 instead of the literal scan's input error
and zero rows. This module computes no payment; conditional on an otherwise
payable invented $1,000 benefit, an unresolved insured route can determine
whether $0 or $1,000 is payable, but neither amount is adjudicated here.

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
