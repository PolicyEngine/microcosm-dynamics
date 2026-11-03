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
queries, so a declared past DIB or RIB month replaces the query event even
where the worker has earned QCs since, and the result answers for the
declared event (round 23 states this). An emigrant with no entitlement
event continues on the query clock.
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
Periods must not share a day; each begins after the one before it ends.
A period may begin in the quarter the one before ended (404.321(a);
RS 00301.140 example 7), and that quarter is then an endpoint quarter of
both, which 404.146(d)(1) lets be a QC and 404.130(f) counts where it is
one (round 23). The ordered period sequence has
`prior_disability_periods_provenance` and optional
`prior_disability_periods_convention_id`; an observed empty sequence
explicitly means no established periods. The default provenance is
`UNKNOWN`, which must contain no periods and never silently means none.

`disability_onset` supplies the ordinary continuous-disability premise from
that day through the query month; the rule does not adjudicate recovery.
A declared historical period end can imply a recovery month under
404.321(b), and an UNKNOWN establishment completion can limit the
alternate-pre1956 scan as described below. Onset may
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
horizon. The first permitted alternate start is July 1, 1952 (RS .480 B.1).
An earlier fixed start horizon cannot be rescued by that later witness.
An explicit `DISABILITY_BEFORE_1956` declaration supplies no route beyond
that automatic alternate. Other specialist declarations retain only the
possibilities allowed by their flag classes below.

The captured 404.321(b), headed "When disability ended before December 1,
1980", says:

> Your period of disability ends on the last day of the month before the month in which you become 65 years old or, if earlier, the last day of the second month following the month in which your disability ended.

A declared end that can only be a recovery ending therefore implies that
disability ended two calendar months earlier. The helper returns that
recovery month only for an end before February 1981, before the month
preceding FRA, and before the month of death. January 31, 1981 is the last
ending to which this inference can apply: disability ending after November
1980 instead falls under paragraph (c), and February 1981 is the first
month an ending under that paragraph can reach. An end in the month before
FRA or later may be the FRA ending; an end in the death month or later may
be the death ending. Neither implies a recovery month. The rule infers no
recovery month for paragraph (c) endings and makes no claim about how those
endings are determined.

Validity asks for the latest date at which any route could hold. A recovery
month before the onset month is an input error. If the helper returns a
recovery month, that month caps the insured-start horizon and a derived
start after it is invalid. A quarter beginning in or before that month can
still count because the worker was disabled in that quarter
(404.320(b)(2); 404.131(a)). The calendar end alone does not make either of
the following two grace months a disabled starting quarter. FRA and death
endings keep their existing validity bound, because they do not imply a
recovery date. Continuity, query, death, and FRA retain their separate caps.

Alternate-route exclusion asks the opposite question: through what date
was the worker disabled in every completion? RS .480 A makes the automatic
alternate unavailable if even the lower-credit filling has 20/40 in a
shared disabled quarter before October 1960. The ordinary 40-quarter
window uses favorable use or disregard of all prior periods. For an
established period, the shared date is the declared end minus two months,
or, with an UNKNOWN end, the continuity date minus two months; without
either fact it is onset. It is never earlier than onset. Month subtraction
uses the calendar index `year * 12 + month - 1 - 2`.
This conservative exclusion bound also applies to FRA and death endings:
a recovery two months before such an ending remains a possible completion,
although the declaration does not imply that recovery occurred. UNKNOWN
establishment before FRA has neither an end nor a continuity declaration,
so its shared date is onset. Declared absence keeps its ordinary result.
The scan also stops at the query, 1960Q3, and the quarter containing the
last day of the month before FRA, for every person (Act 216(i)(2)(D);
404.315(a); 404.321(a)–(b)). A quarter remains eligible exactly when its
first month is on or before the shared date and before the FRA month.
These latest-validity and earliest-exclusion bounds deliberately go in
opposite directions: an input error excludes every possible route, while
a computed UNKNOWN result must survive every completion.

The alternate's continuous-QC clock also considers both use of every prior
period and disregard of every prior period. RS .132 B.2 excludes a quarter
all or part of which is in a used disability period, except a beginning or
ending quarter that is a QC, from the "period of continuous QCs under the
alternate insured status provision". C.2 requires all prior periods to be
used or all disregarded. The shared world, boundary-assignment, and credit
assignment helpers implement both treatments. The remaining clock must
contain at least six quarters, each credited, and at least 20 total QCs
must remain assignable (RS .480 A). A missing QC outside an excluded period
breaks continuity; an uncredited interior quarter of a used period does not.

RS .480 A permits two readings. Its "any quarter before 10/60" supports
the literal scan, while "though under a disability" and "for freeze or DIB"
support limiting a witness to the period it could establish. A witness
after a declared end cannot start that period. Where those readings differ,
the rule retains `disability_before_1956_unsupported`; it does not decide
between them. The same protection applies to UNKNOWN endings and UNKNOWN
establishment: an early ending completion that preserves the route prevents
a universal exclusion of that route for DISABILITY.
If some feasible fillings still lack 20/40, application facts remain absent
and the alternate possibility retains its refusal.
On the ordinary route, a valid
filling must supply one insured start at or before the applicable
recovery or administrative-end bound. A later witness at the query cannot
rescue an immutable earlier bound. The scan therefore stops at that bound,
any continuity observation, death, or FRA cap, whichever is earlier.
Maximum credits decide the monotone insured-by-that-date question. Every
prior period ends before onset, and a period may begin in the quarter a
prior ended, so no derived start overlaps a prior period (round 23).
Only when all routes and feasible fillings are impossible can the rule
raise `InvalidFamilyInput` before any coverage refusal, and a listed prior
that no completion supports refuses by name first (round 23; see the
refusal order below). On the ordinary
supported QC surface, fewer than six maximum feasible lifetime QCs proves
impossibility: 404.130(a) requires
fully insured status, and 404.110(b)(1) says, "You need at least 6 QCs but
not more than 40 QCs to be fully insured." Period exclusions cannot supply
missing credits. That ordinary argument does not adjudicate deemed,
transitional, military, railroad, or other specialist routes. A flag or
observable specialist route that could validate the declaration prevents
that input error and preserves a refusal row.

Declared foreign credits preserve their unmodeled route before every
credit-count proof. Credit-route flags,
or raw-earnings flags without a complete direct-QC envelope, do likewise.
The flag classes and their captured premises are listed below. The
minimum-requirement proof precedes every recent-rule or alternate scan,
boundary enumeration, and UNKNOWN-prior-history feasibility scan. It runs
only with known prior history and without statutory blindness. Every
remaining ordinary 20/40 or alternate route needs 20 QCs. If the earliest
candidate start permits the under-31 or subsequent-special rule, the proof
also takes that rule's requirement after removing every prior-period
quarter from elapsed time, including otherwise credited endpoints. This
gives no more elapsed quarters than any actual witness. The special
requirement never decreases as elapsed time rises, so the minimum of these
requirements cannot exceed the true requirement of any remaining route.
If maximum feasible lifetime QCs falls below that minimum, no filling can
establish the period. Fully insured prerequisites and actual credit-window
availability can only add constraints; omitting them cannot make this
lower bound too high (404.130(a)–(f); RS .480 A).

Blindness uses the fully insured prerequisite alone (`blindness_fully_only`),
so it disables the stronger proof. UNKNOWN prior history can supply
additional exclusions and also disables that proof. The next proof counts
maximum feasible QCs by the immutable start horizon, respecting death and
coverage exit. Fewer than six proves impossibility even with UNKNOWN
prior history and a fully-route flag. Section 404.130(b) requires twenty;
(c) and (d) retain at least six; (f) changes elapsed quarters rather than
that floor; RS .480 also requires twenty. Blindness with a fully-route
flag alone bypasses this proof because 404.130(e) has no recent-credit
test and the flag presumes its fully insured prerequisite. Blindness
without that flag still needs six ordinary fully insured QCs.
With known prior history, a nonblind fully-route flag also needs a
possible recent rule in a starting quarter from onset through the
immutable horizon, or a possible automatic pre1956 alternate.
The recent scan uses the same annual assignment, fixed all-period
use/disregard treatment, and special-window rules as the ordinary witness,
relaxing only its fully insured prerequisite (404.130(a)–(d), (f)). If maximum feasible credits
cannot satisfy any such recent rule and the alternate is unavailable, no
lower-credit filling can establish the period. A recent-only quarter
does not establish when the flag begins.
Blind fully-route declarations have no recent requirement and retain the
same free flag-start fact. A complexity refusal during this scan preserves
possibility so that the flag retains its own named refusal.

The horizon six-QC floor precedes the automatic alternate. The pre1956
alternate needs 20 QCs (RS .480 A) and
an eligible start no later than December 31, 1955 (RS .480 B.1). Its
establishment witness uses one quarter satisfying that date limit and the
immutable horizon together. This start check applies only to a declared
established period;
the continuous clock still uses or disregards all prior periods and
retains credited endpoints. The lower-credit 20/40 exclusion is unchanged.
Its explicit flag adds no credit, condition, or route beyond the automatic
check and therefore supplies no separate early return. Any declaration
that survives establishment validation still receives the flag's named
refusal. The rule does not test a flag's own conditions: for example, a
`DEEMED_FULLY_INSURED` declaration stays a declared fact even for a birth
year outside 404.112's nonprofit-worker condition. These proofs determine
only whether that fact could supply the missing prerequisite.

Declared foreign credits receive `totalization_credits_unsupported`, with
their evaluator row and weight, for zero, three, six, or ten own QCs once
fixed chronology clears. The rule makes no claim about any totalization
minimum, eligibility, foreign-credit count, or benefit. No totalization
source is used. The round 11 validation-order fixture ends a prior
period in the onset quarter. Round 23 makes that declaration valid, since
a period may begin in the quarter a prior ended, so foreign credits and
every `CoverageCondition` keep their named refusals there.

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

The scan uses maximum feasible QCs for unknown years and tests each
earliest prior as blind, regardless of current blindness (404.130(e);
RS 00301.150). A blind prior needs only fully insured status, so failing a
nonblind recent test cannot prove that prior history empty. The alternate
check before that witness is unchanged. The scan does not try to prove
administrative feasibility. Any possible specialist starting route
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
The `_current_period_completions` enumeration deliberately over-includes
some early UNKNOWN endings that the recovery-month reading would reject
if declared concretely. That widens the set whose requested results must
agree. It can preserve an extra refusal or widen a count envelope, but a
returned status that agrees on the larger set still agrees on every valid
completion. The enumeration is therefore left unchanged. A supplied date
retains the existing declaration semantics; known ending provenance
requires that date.

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
Subsequent years, and explicitly dated quarterly amounts or QCs before
birth or after exit, are input errors. Annual counts are capped by the
number of assignable quarters. Section 404.146 bars a quarter that has not
begun, one after the quarter of death, one already counted, and a
disability-period interior, and RS 00301.230 B says "We can assign a QC
to any quarter in the calendar year" subject to those limits. An annual QC
therefore takes any begun quarter of its year through the death quarter:
neither a coverage exit nor a birth bars a quarter of its own year
(round 23). Wages paid after the death quarter still count toward the
year's total (Act 213(a)(2)(A)(ii), (B)(ii)); only the later quarters
cannot be QCs ((B)(i)). Disability interiors are excluded when the prior
periods are used (404.146(d); RS 00301.240).

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
`upper_qualifying_quarter`, the latest and earliest first successful
disabled quarter the record leaves open. Each is the first such quarter in
its earnings-bound world, except that where a listed prior binds, the pair
spans every basis that prior can rest on, and under UNKNOWN priors an
insured `upper_qualifying_quarter` is the onset quarter, which some prior
history can make the first (round 23). Thus a disability witness can show
20 recent QCs and still be uninsured because its duration-of-work
requirement is not met.
The low and high witnesses each optimize assignment for that particular
test. They need not have the same assignment or prior-period treatment.
FULLY's witness keeps whichever treatment gives the larger margin, so where
QCs sit inside a listed prior it can report the disregarded treatment's
count and requirement beside a `qcs_by_year` mapping and a
`fully_insured_requirement` that consider the period. For a woman born
1960-02-02 with a 1995 prior and four QCs in each of 1985 to 2000, a
January 2005 FULLY result reports 64 of 23, while its mapping sums to 62
and the helper gives 22. 404.320(a) disregards a period only where
considering it would deny or reduce benefits; both treatments insure here,
so the status agrees, and the witness's count and requirement are a
diagnostic of the larger margin, not of that treatment (round 23).
Where the first start can move, each keeps a filling with the reported start,
and `qcs_by_year` and the top-level assignment describe the returned filling.
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

For unknown prior or current establishment facts, ordinary FULLY and
CURRENTLY covered-credit statuses under favorable disregard of those
periods are sound Boolean lower bounds, including when current establishment
is known but its start depends on unknown prior periods. A DISABILITY
witness additionally requires disability in its tested quarter. Section
404.130(f) permits favorable all-period disregard for the disability
window; 404.320(a) supplies the broader rule: "If benefits payable on your
earnings record would be denied or reduced because of a period of
disability, the period of disability will not be taken into consideration."
Railroad and noncreditable military credits remain refused, preserving
RS .120's exception. For FULLY and CURRENTLY, a true lower bound therefore
decides true: their ordinary covered-credit witness survives favorable
disregard regardless of a current period's ending. DISABILITY instead
requires disability in its witness quarter. With UNKNOWN establishment, an
early-ending completion can remove a later ordinary witness and leave only
the alternate route with unmodeled application conditions. The alternate
refusal precedes that prospective true result. For valid declarations, fewer
than six maximum feasible lifetime QCs decides false. Otherwise unknown
periods may change a false result, so the rule refuses by name. Current
establishment still supplies no exclusions to the ordinary disability
qualification scan that must prove its own start; using its own exclusion
would be circular. The alternate-route guard separately protects UNKNOWN
establishment completions with an early ending.

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
| Early male retirement cohorts | Before January 2, 1911 use age 65; January 2, 1911–January 1, 1913 use 1975 (404.110(b)(2)(iii)–(iv); RS .105). Before 62 the query year ends a living man's count; from the year he reaches 62 it runs to that retirement year whatever the query, and a death year ends it if earlier (404.110(b)(3); round 23). |
| Early male disability prerequisite | For every man born before January 2, 1913, the disability-specific fully insured elapsed-year endpoint is 1975 or the earlier relevant disability year (404.132(b)). It can differ from the retirement fully insured decision. |
| Currently insured | Six QCs within 13 counted quarters ending with an actual declared death/RIB/DIB event, or the hypothetical query event. Every intersecting established period can extend the window, including the event's own period (214(b);404.120;RS .110). |
| Disability | Scan onset through query for the first candidate quarter with the candidate-year fully insured prerequisite plus 20 QCs in 40 counted quarters, or a special rule (223(c)(1);216(i)(3);404.130-.132;RS .120/.130). |
| Young worker | Before the age 31 attainment quarter: half the quarters after the age 21 quarter, dropping an odd remainder, minimum six. Fewer than 12 elapsed quarters uses 6/12; age 24 attainment quarter still uses 6/12 (404.130(c);RS .140). |
| Subsequent disability | With declared earlier special insured status, the special test can apply after 31, up to 20/40. The rule records the same fact for a current period it begins: a nonblind holder's period that began before the age-31 quarter where 404.130(b) failed counts as such a prior for the quarters after it ends (404.130(d)(1); Act 223(c)(1)(B)(iii)). Where placement or an UNKNOWN year decides that basis, a date last insured the two bases put differently refuses by name (round 23). Prior periods are all used or all disregarded, whichever admits insured status; endpoints count in windows only if QCs (404.130(f);RS .120/.147). |
| Blindness | Only the fully insured prerequisite, evaluated at each candidate disabled quarter; it can first qualify after medical onset, as can nonblind status (404.130(e),404.131;RS .150). |
| DLI | Latest fully-and-disability-insured quarter end, with explicit query censoring or frozen-exit horizon and FRA cap (RS .148). With no established period, the DISABILITY decision itself scans quarters past FRA and only the date takes the cap, so a woman born 1950-02-02 with 40 QCs from 1975 to 1984, three in each of 2010 to 2014 and four in 2016 and 2017 is insured at 2017-01-01 in a January 2018 query, beside a date last insured of 1989-12-31 (round 23). |

For prior disability periods, only years containing their endpoint quarters
need assignment enumeration. Other annual credits maximize overlap directly.
The calculation considers all-used and all-disregarded contexts, never a
selectively chosen subset, including the alternate continuous-QC clock
(RS .132 B.2, C.2). More than 4,096 boundary combinations receive an explicit
computational-coverage refusal only after every applicable six-QC and
minimum-requirement impossibility proof (round 23 removed the fixed-overlap
proof with the overlap check). No approximate search is used.

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
every raw row. The establishment possibility checks then precede coverage
refusals. Within those checks, declared foreign credits come first,
followed by any credit-route flag or raw-earnings flag without a complete
direct-QC envelope. The known-history nonblind
minimum-requirement proof follows before every boundary enumeration.
A fully-route flag then preserves possibility immediately for blindness.
Otherwise fewer than six maximum QCs feasible by the immutable start
horizon proves impossibility, including UNKNOWN prior history. After
that floor, a fully-route flag preserves possibility for UNKNOWN priors;
with known priors it needs a recent-rule
witness from onset through the horizon, or the automatic pre1956
alternate. Neither route means impossibility even with that flag. An
explicit `DISABILITY_BEFORE_1956` flag supplies no separate route or early
return. The remaining ordinary boundary assignments, UNKNOWN prior-history
feasibility, and concrete earnings fillings follow unchanged. Neither
`_unknown_prior_history_is_empty` nor an alternate-path
`_boundary_variants` call can run ahead of the minimum-requirement proof.
A complexity refusal in the fully-route recent scan preserves possibility,
so it does not replace the declared flag's own refusal reason. Raw
conversion, before the establishment proofs, can encounter only four
reachable refusals: `qc_amount_year_unsupported`,
`1937_earnings_allocation_unsupported`,
`pre1955_agricultural_allocation_unsupported`, and
`pre1951_self_employment_unsupported`. These are deferred while possibility
is tested with each unresolved row's feasible credit fillings. If the
proof finds a possible filling or reaches an unresolved coverage limit,
the first original conversion refusal in year order is raised unchanged.
These refusals are conservative: they don't ask whether the conversion
could change the answer, so 2028 wages of $1,969 refuse for a worker born
1990-06-15 with four QCs in each of 2010 to 2027, where an UNKNOWN 2028
computes FULLY true at 72 of 16 (round 23). Each such row keeps its weight.
Proved impossibility instead raises `InvalidFamilyInput`, unless a listed
prior refuses first. A listed prior that no completion of the credits
supports shows the record omits credits or facts that could insure the
current period as well, so it refuses by its own name
(`disability_boundary_assignments_unsupported`, or
`disability_before_1956_unsupported` where RS .480 may have begun it),
after any deferred conversion refusal and before the input error. A
fully-route flag that can carry the prior suppresses that refusal. The
same check precedes the UNKNOWN-earnings refusal of an established period
whose validity rests on unknown credits (round 23). With no deferred
reason, the existing specialist, date, applicability, and requested-status
checks follow. In the requested-status checks, a positive ordinary
DISABILITY witness does not bypass the observable alternate route when
current establishment is UNKNOWN and onset precedes the FRA month. Its
20/40 exclusion must hold even for the earliest recovery completion
consistent with the declaration.
FULLY and CURRENTLY keep favorable-disregard true results; a false CURRENTLY
result can still refuse for unknown establishment before ALL reaches
DISABILITY. No established completion exists for onset in or after the FRA
month, so this correction does not apply there. The evaluator validates its
key, weight, and callback before invoking the callback; it adds no statutory
refusal of its own. It counts a genuine callback refusal only after the
callback's declaration validation has had this opportunity to reject the
input. An input error propagates and creates no row.

| Trigger | Reason code |
| --- | --- |
| Unknown-year bounds decide a requested status differently, an UNKNOWN year decides whether 404.130(b) began the current period where that moves the date last insured, or a flagged prior's first quarter has more than 4,096 completions | `unknown_earnings_years_decide_status` |
| Unknown prior periods may change a requested status | `unknown_prior_disability_periods_decide_status` |
| Unknown current establishment may change a requested status | `unknown_current_disability_period_decides_status` |
| Any candidate end quarter for an UNKNOWN current ending changes a requested status | `ongoing_disability_period_end_decides_status` |
| Unknown section 214(c) applicability may change a requested status | `sspa211_applicability_unknown` |
| Standalone requirement helper needs coverage history to derive a declared current period start | `current_disability_period_requires_history` |
| Ongoing established current period, known prior-period history, and a frozen-exit DLI horizon beyond query | `ongoing_disability_period_dli_horizon_unsupported` |
| Any foreign totalization credits after fixed chronology, before every credit-count proof; the route itself remains unmodeled and no totalization minimum is claimed | `totalization_credits_unsupported` |
| Declared deemed nonprofit/veteran fully insured path | `deemed_fully_insured_unsupported` |
| Declared transitional insured path | `transitional_insured_unsupported` |
| Known section 214(c) applicability needs unimplemented work-authorization/visa adjudication, including never-assigned alien SSNs | `alien_worker_sspa211_unsupported` |
| Railroad or military credits | `railroad_credits_unsupported`, `military_credits_unsupported` |
| Medicare-qualified government employment | `medicare_government_employment_unsupported` |
| Earned-basis wages or pre1956 alternate disability | `earned_basis_unsupported`, `disability_before_1956_unsupported` |
| Fiscal or short taxable-year public declaration | `fiscal_taxable_year_unsupported`, `short_taxable_year_unsupported` |
| Supplied pre1951 wages, or UNKNOWN pre1951 years, could make a failed fully insured test pass under the simplified method, including the fully insured prerequisite of DISABILITY, the current period, its first start and the date last insured; also an explicit specialist declaration | `simplified_pre1951_unsupported` |
| Positive raw1937 earnings needing half-year/age65 rules | `1937_earnings_allocation_unsupported` |
| Separate pre1955 agricultural annual wages | `pre1955_agricultural_allocation_unsupported` |
| Pre1951 self-employment income | `pre1951_self_employment_unsupported` |
| Earnings require an increment after 2027 | `qc_amount_year_unsupported` |
| Query before 1968; blind query before 1973; a query before May 1983 for the holder of a flagged prior whose age-31 quarter begins before then (round 23: 404.130(c) still covers an onset before 31) | `entitlement_before_1968_unsupported`, `blindness_before_1973_unsupported`, `subsequent_special_before_1983_unsupported` |
| A subsequent-special period past 40 counted quarters where half the whole period and 20 of the last 40 give different results | `subsequent_special_long_period_unsupported` |
| More than 4,096 disability-boundary combinations, a first start that placement or prior treatment can move with no one filling supporting the returned result, a lower date some ending can't reach on a filling with the reported start, a status or lower date some annual placement doesn't attain with no period in force under UNKNOWN priors or UNKNOWN establishment, a listed prior that annual placement decides where an UNKNOWN year stands open or no filling that keeps the prior attains the result, a listed prior that no completion supports (before any input error the record would raise), or a date last insured that turns on whether annual placement let 404.130(b) begin the current period, after every credit-count proof applicable to the surviving flag classes and foreign-credit declaration | `disability_boundary_assignments_unsupported` |

The round-3 observable-trigger audit covers every `CoverageCondition`.
An explicit condition continues to refuse under its own reason when the
declaration survives every applicable impossibility proof. The following
table supplies the classification premises used by those proofs. Section
404.130(a) requires one of its four rules "and you must be fully insured";
a rule changing only fully insured status cannot supply missing recent
credits. This classification does not adjudicate the flagged rules or
test whether a flag's own conditions are met. In particular, an otherwise
unreachable 404.112 birth cohort does not invalidate an explicitly declared
`DEEMED_FULLY_INSURED` fact.

| Flag | Captured premise and effect | Class |
| --- | --- | --- |
| `DEEMED_FULLY_INSURED` | RS .106 B.2 says "deemed fully insured for all title II purposes"; 404.110(a), .111, .112 and RS .470 concern the fully insured prerequisite. Every fully route retains the horizon six-QC floor except with statutory blindness (404.130(b)–(e)); UNKNOWN priors cannot remove it. | Fully route |
| `TRANSITIONAL_INSURED` | RS .101 B.1 lists "Transitional Insured Status" beside fully insured status for spouse benefits. It is absent from 404.130's four rules and supplies no recent QC. | Fully route |
| `EARNED_BASIS` | RS .475 A says "fully insured status could be established by crediting certain wages on an earned rather than a paid basis". Its stated special method changes the fully insured prerequisite. | Fully route |
| `SIMPLIFIED_PRE1951` | Act 213(c) says "For purposes of sections 414(a) and 415(d)"; 404.110(d)(1) says "For purposes of paragraph (b) of this section". Simplified credits affect fully insured status, not the independent recent test. | Fully route |
| `DISABILITY_BEFORE_1956` | RS .480 A requires "at least 20 quarters of coverage (QC) by the end of that quarter", the continuous-QC clock, and an eligible historical start; B.1 says "the last day on which it can begin is 12/31/55". For established periods that same start must fit the immutable horizon. The flag adds no credit or route beyond the automatic alternate check. A surviving declaration retains its named refusal. | Recent test |
| `RAILROAD_CREDITS` | RS .350 A says "we may use RR compensation in determining the number of quarters of coverage (QCs)"; RS .131 also identifies freeze credits. Compensation can add QCs before a final direct-QC declaration. | Raw earnings |
| `FISCAL_TAXABLE_YEAR` | RS .220 says "we will allocate the SEI proportionately to the two calendars years"; 404.142 and .144 govern taxable-year allocation. The rule acts on earnings, not an already declared final QC count. | Raw earnings |
| `SHORT_TAXABLE_YEAR` | RS .340 B.2.b says "credit SEI equally to the calendar quarter in which the TY ends" and preceding quarters in the taxable year; 404.142 and .144 govern allocation. | Raw earnings |
| `MILITARY_CREDITS` | 404.133 says "For purposes of establishing a period of disability only, we give you quarters of coverage". Freeze-only credits may lie outside the declared ordinary rows. | Credit route |
| `MEDICARE_GOVERNMENT_EMPLOYMENT` | RS .160 A says "Use GEQCs, DQCs, and regular QCs to establish the insured status requirements for Medicare purposes." Government QCs can supplement regular QCs. | Credit route |

For raw-earnings flags, an envelope is complete when every supplied year
is a direct `qc_count`, direct `qc_quarters`, or UNKNOWN row. I9's
direct-credit contract then already fixes or bounds the final credits;
raw-amount allocation cannot add credits outside it. Military credits
are excluded from that contract because 404.133 expressly gives freeze-only
credits. Fully-route flags remain below the numerical recent-credit proof
and, with known prior history and no blindness, the candidate-quarter
recent scan. They bypass only the ordinary fully insured prerequisite and
its ordinary fully insured floor. Their named refusals survive blindness
at a clear onset, or UNKNOWN prior history surviving the horizon floor
and joint optimistic-clock proof, and any case with a possible first
recent or automatic alternate start. The pre1956 flag still obeys
the ordinary six-QC floor and automatic alternate conditions because it
adds no credit or route.

Automatic detection additionally applies where the ordinary
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
| `SIMPLIFIED_PRE1951` | Raw 1937–1950 quarterly wages provide an aggregate divided by $400; post1950 upper QCs and the fully insured prerequisite bound whether it could decide status (213(c); 404.110(d); RS .315). UNKNOWN pre1951 years can supply unbounded raw wages and therefore also trigger the refusal. Direct `qc_quarters` declare credited quarters rather than raw wages and add nothing to the aggregate, so declaring pre-1951 years as flags waives this route: RS 00301.315 C.1's John Doe, born 1926-09-08, with 1949 declared as four QC flags, computes FULLY false at 27 of 37 in September 1991, while $5,700 of 1949 wages or an UNKNOWN 1949 refuses by this name (round 23). The simplified method does not apply to a disability claim. Filing, retroactivity, and section 227 facts remain unmodeled. |
| `DISABILITY_BEFORE_1956` | The explicit flag adds no route beyond this automatic check. Medical onset and QCs reveal a possible RS .480 alternative: at least 20 total QCs and every counted quarter from 1951Q1 through the quarter before a qualifying 1952Q3–1955Q4 candidate quarter at or after onset, with at least six such quarters, under favorable all-period use or disregard (RS .132 B.2, C.2). For declared current establishment, that candidate must fit the immutable declared-end/continuity/death/FRA horizon. RS .480 A excludes the route when the lower-credit filling has 20/40 in the rule's disabled-quarter scan before October 1960; if only some fillings do, the alternate remains possible. Refuse automatically when this could change a failed disability predicate. Application conditions remain unmodeled. |
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

A `CoverageCondition` explicitly triggers its specialist refusal after
all applicable establishment-impossibility checks. The module does not
infer excluded specialist facts from ordinary earnings or adjudicate a
flag's own conditions.
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
| I2. Birth, disability onset, death, prior periods, entitlement, and SSN assignment must have consistent lifetime ordering. A query or coverage end cannot precede birth; medical onset or supplied entitlement cannot follow the query month; onset cannot follow death. A DIB entitlement month must precede the FRA month, and an RIB entitlement month cannot precede the month of attaining 62 (round 23). | B404.102 defines "You or your" as "the worker whose insured status is being considered"; A216(i)(2)(A) requires a period "during which an individual was under a disability". Dates refer to that same living worker. This lifetime and observation-calendar contract is independent of the insured route. It permits onset later within the query month and the quarter of death rather than imposing a day-of-query restriction. The entitlement bounds are an interface premise: the benefit calendar comes from Act 223(a)(1) and 202(a)(2), which are not captured, and an event outside it contradicts the declaration rather than posing an insured-status question. |
| I3. An established period must start before its FRA-ending boundary, including no start in the FRA month. A declared current-period end after the preceding month end is an input error, as a continuity date after it already was (round 23); supplied prior periods are capped at that month end. | A216(i)(2)(B): "no such period shall begin ... after such individual attains retirement age"; (D)(i) ends at "the month preceding the month" of FRA. C321(a), (c)(1) say the same. A start after the mandatory month-end is impossible under both clauses, including first-day birthdays. The cap supplies no evidence against an earlier UNKNOWN end. No completion ends the current period later, so a later declared end is a contradiction, not a value to cap. |
| I4. Supplied prior periods precede the current onset and query, share no day with each other, and stay within the lifetime. A period may begin in the quarter the one before ended (round 23). | B404.130(f) refers to "a prior period of disability established for you". C321(a) says "Your period of disability begins on the day your disability begins if you are insured for disability on that day", and C321(b)–(c) end a period on a month's last day, so a new period can begin in the quarter the last one ended; RS .140 example 7 is that case. The shared quarter is an endpoint quarter of both periods, which B404.146(d)(1) and B404.130(f) count where it is a QC. Days, not quarters, are the declared history representation; specialist credits cannot change what "prior" means. UNKNOWN history is not treated as supplied empty history. |
| I5. A supplied `special_insured` prior period begins before the age-31 attainment quarter. | B404.130(d)(1): a prior period "began before age 31" and the worker "were only insured under paragraph (c)"; (c)(1) requires age 31 not yet attained. A216(i)(3)(B)(iii) expressly uses "before the quarter" of age 31. The flag declares this particular adjudicated young-worker route, not every possible special credit regime. |
| I6. An alien worker's actual pre2004 SSN assignment conflicts with declared SSPA applicability; birth on/after January 1, 2004 conflicts with declared exemption. Both never-assigned and an assigned SSN, or assignment before birth, remain invalid. A worker born before 2004 may pair a post2003 assignment or never-assigned status with an adjudicated exemption. | RS .102 B.1 says an alien assigned an SSN before 2004 "is exempt", including a nonwork SSN. B.3.b says, "If an alien worker could have legitimately been assigned an SSN before 1/1/2004, the worker is exempt from the requirements of section 211 of the SSPA." Its wrong-number SS-5 scenario issued another person's number "instead of assigning the alien worker their own SSN". Thus observed or convention-filled exemption overrides either later-assignment or never-assigned presumptions when legitimate pre2004 assignment was possible. Birth on/after January 1, 2004 rules out that exception independently of the assignment record. B.4.b's worker without an SSN "is nevertheless considered to meet the work SSN requirement" when work-authorized; meeting that requirement alone supplies no exemption. |
| I7. Explicit quarterly QCs cannot occur before birth, after the query/coverage-end quarter, or after the death quarter; positive quarterly wages cannot occur before birth or after the query/coverage-end quarter. Every required coverage year is declared exactly once through the earliest query, exit, or death year. | A213(a)(2)(B)(i), (v): "no quarter after the quarter in which an individual dies" and "no quarter shall be counted ... prior to the beginning of such quarter"; B404.146(a)-(b) agree. Wages paid after the death quarter still count toward that year's total under A213(a)(2)(B)(ii), so they contradict nothing (round 23). Birth and supplied-record exit caps on dated rows, complete years, and no implicit zeros are interface premises. An annual count is undated, so neither cap bars a quarter of its year (round 23). Specialist earned-basis or additional-credit declarations remain refusals and do not reinterpret an explicit ordinary covered-quarter declaration. |
| I8. A declared current establishment is invalid only after the shared possibility check excludes every route and every feasible prior/earnings filling. One ordinary filling must satisfy its insured start, recovery or administrative end, and continuity constraints together. | C320(b)(2) requires insured disability "in the calendar quarter in which you became disabled, or in a later calendar quarter"; C321(a) chooses the first such quarter. B404.130(a) supplies four ordinary rules and RS .480 supplies the alternate historical rule. The start horizon uses an inferred recovery month when I14 permits one, otherwise the declared end, together with continuity/query/death/FRA caps. Maximum credits establish only monotone insurance by that fixed horizon; no derived start can overlap a prior (I4). A listed prior that no completion supports refuses by name before this input error (round 23). An ordinary start found only through placement or treatment search establishes possibility and retains a named refusal; it does not select a status witness. An ordinary or alternate witness after the horizon cannot supply possibility. Foreign credits and the flag classes determine which credit-count proofs apply, in the refusal order above, before any alternate or boundary enumeration. The alternate's 20/40 exclusion instead uses U10's earliest date shared by every completion; a later witness cannot prove impossibility under every defensible reading of RS .480 A. |
| I9. Except for blindness with a fully-route flag, fewer than six maximum feasible QCs by the immutable start horizon proves current establishment impossible after foreign credits, credit-route flags, and unresolved raw-earnings flags have preserved their possible routes. | B404.110(b)(1): "You need at least 6 QCs but not more than 40 QCs"; B404.130(a): "you must be fully insured". The flag table supplies each exception's captured premise. A record composed entirely of direct final QC declarations (`qc_count` or `qc_quarters`) and UNKNOWN years fixes or bounds all admissible final credits from RR compensation and fiscal/short taxable-year allocation. This is the direct-credit input contract, not a claim that ordinary RSDI credits exhaust freeze-only military credits: B404.133 expressly supplies the latter, so `MILITARY_CREDITS` remains a separate credit route even with direct rows. Any raw row leaves the raw-earnings route unresolved. Period exclusions alone cannot add ordinary QCs. RS .480 A separately requires 20 QCs and the explicit `DISABILITY_BEFORE_1956` flag adds no route beyond the automatic alternate, so it cannot rescue a below-six declaration. Fully-route flags replace only the fully insured prerequisite; nonblind recent rules retain the universal horizon floor in I17, even under UNKNOWN prior history. Blindness with a fully-route flag bypasses that floor under 404.130(e). No ordinary floor applies to the unmodeled foreign-credit route (U11). |
| I10. The supported calendar, mandatory historical sex, and explicit establishment declaration must be supplied: birth years 1870–9900, query years through 9990, sex for births before January 2, 1913, and establishment provenance whenever onset is present. | These are interface-domain requirements. B404.110(b)(2) and .132 apply different historical male/female endpoints; B404.110(c) excludes only a period "we established for you". Missing facts are not inferred. Calendar limits reserve space for date arithmetic and assert no legal incapacity outside the implementation domain; alternative credit routes cannot supply missing declared facts. |
| I11. A continues-through observation requires established disability, cannot precede medical onset or the first feasible insured start, cannot exceed the pre-FRA or death boundary, and cannot follow a declared administrative end. | C320(b)(2) and C321(a) require the insured start; A216(i)(2)(D) and C321(c) bound the period's end. A declaration that a period was in force on a date requires that date to lie within one possible period. This is a dated observation, not an asserted ending; a date later than the query is allowed. Provenance and convention identifiers follow the existing fact schema. |
| I12. A raw-credit conversion refusal cannot hide established-period impossibility that every feasible filling of that row preserves. | C320(b)(2), C321(a), and B404.110(b)(1) supply the insured-start and six-QC premises. The #530 input contract puts input errors before coverage refusals. Schema validation remains first; the four conversion refusals are deferred only for this proof, with unresolved rows bounded by feasible ordinary quarters. A surviving filling preserves the original refusal reason and note rather than manufacturing a supported status. |
| I13. Round 23 retires this premise. Every supplied prior ends before onset and a period may begin in the quarter a prior ended (I4), so no starting quarter from onset through the horizon can overlap a supplied prior period. | C321(a) begins a period on its onset day when insured then, and RS .140 example 7 begins one in the quarter a prior ended. The round 6 records whose only start shared a prior's ending quarter now stand or fall on their credits. |

| I14. A declared recovery-only historical end implies a recovery month two months earlier; recovery before the onset month or a derived start after that month is invalid. | C321(b) ends the period on "the last day of the second month following the month in which your disability ended". C320(b)(2) and B404.131(a) require an insured quarter in which the worker was disabled, so an administrative grace month cannot supply a new disabled quarter. The helper returns no recovery inference for an end on/after February 1, 1981, in/after the month preceding FRA, or in/after the death month. These carve-outs preserve the existing validity horizon and make no claim about paragraph (c) recovery or administrative ending rules. |
| I15. With known prior history, no blindness, no foreign credits, no credit-route flag, and no raw-earnings flag outside a complete direct-QC envelope, fewer maximum feasible lifetime QCs than the lowest remaining recent-rule requirement proves establishment impossible before fully-route refusals or coverage enumeration. | B404.130(a) requires a recent rule "and you must be fully insured". The flag table's fully-route rules cannot change the independent recent-credit requirement. B404.130(b) needs 20 QCs; (c)–(d) permit the special half-elapsed-quarter rule with six-QC floor and 20-QC ceiling; RS .480 A also needs 20. At the earliest candidate start, remove every prior-period quarter from special elapsed time, including credited endpoints. Every actual use/disregard witness has at least those elapsed quarters, and later starts cannot reduce them. Taking the smallest applicable requirement therefore cannot exceed any true route minimum. Ignoring the fully insured prerequisite and window availability only relaxes the bound. Blindness (B404.130(e)) needs only fully insured status, and UNKNOWN prior history could remove further quarters; both disable this stronger numerical proof. Blindness removes I16's recent-credit requirement; UNKNOWN prior history skips its known-history scan, but does not disable I17's six-QC horizon floor. The minimum remains ahead of every boundary enumeration, including the recent scan. |
| I16. With known prior history and no route adding credits outside the declared envelope, a fully-route flag needs a possible first insured start or the automatic pre1956 alternate. Nonblindness retains the recent rule; blindness has none. | B404.130(a) requires one rule "and you must be fully insured"; (b) requires 20 QCs in 40 quarters; (c) and (d) supply the under31 and subsequent-special recent alternatives. C320(b)(2) permits the onset quarter or a later disabled quarter, and C321(a) selects the first qualifying quarter. The scan includes onset and horizon. Recent-only insurance does not date the flag's fully insured status; the first flagged start may be later. Blindness similarly leaves the flag's start unknown, including with zero QCs. No start can overlap a prior (I4), so the upper-credit scan bounds every filling (round 23). It retains B404.130(f)'s favorable all-period use or disregard and annual assignment, and relaxes only the fully insured prerequisite. A fully-route flag that can carry a listed prior also suppresses that prior's unsupported-basis refusal (round 23). An open RS .480 route remains an independent possibility for a fully-route flag. A complexity refusal is not impossibility and preserves the flag's own named refusal. The scan tests no flag-specific condition. |
| I17. Every declared-envelope nonblind establishment route has at least six QCs feasible by its immutable start horizon, including fully-route flags and UNKNOWN prior histories. Blindness without a fully-route flag retains the ordinary fully insured floor. | B404.130(b)(2) requires "at least 20 QCs"; (c)(3)(ii) and (d)(2)(ii) require "at least 6 QCs in the 12-quarter period". Paragraph (f) changes the counted window, never this floor. Only (e) removes the recent requirement, retaining fully insured status. RS .480 A also needs twenty QCs by its start. UNKNOWN prior history may remove elapsed quarters or open a subsequent-special route, but cannot remove this minimum. Credits after the horizon cannot satisfy it. Foreign and unmodeled credit routes remain outside the declared envelope and precede the proof. |
| I18. An established pre1956 alternate uses one start quarter satisfying the immutable horizon and the historical date limit together. | C320(b)(2), C321(a) and RS .480 B.1 require an eligible insured start no later than 12/31/55. A later ordinary candidate cannot validate an alternate candidate that misses either limit. This check does not change the alternate continuous clock, credited endpoint treatment, lower-credit exclusion scan, or false/UNKNOWN establishment. Unlike a recent-only flagged candidate, an alternate candidate must itself satisfy every starting condition together; the flag-start correction does not move this candidate. |

| ID and UNKNOWN collapse | Captured text and alternative-route defense |
| --- | --- |
| U1. UNKNOWN prior history can collapse to empty solely for impossibility validation when no earliest prior period could start insured, on/after birth, before current onset and the FRA end. | C320(b)(2) and C321(a) require an insured beginning without a still-earlier period. A216(i)(2)(A) permits "five full calendar months' duration or" DIB entitlement "for one or more months". The scan therefore admits a one-month period and maximum feasible earnings. Any possible ordinary or specialist starting route stops the proof. It establishes no observed empty-history fact. |
| U2. UNKNOWN current establishment needs no new-period alternative if there is no medical onset or onset is at/after the statutory latest starting month. | A216(i)(2)(A)-(D) and C321 prohibit a period without disability or a nonempty pre-FRA interval. This removes an impossible new-period alternative only; it does not remove UNKNOWN prior history or an existing period's UNKNOWN administrative end. |
| U3. With unknown prior/current periods, true ordinary FULLY and CURRENTLY status under favorable all-period disregard decides true. A DISABILITY witness must also survive any current-establishment completion that ends the disability before that witness. Every annual placement must attain the status at the quarter it reports with no period in force, because a period's own start can rule a filling out (round 19). | C320(a): "If benefits ... would be denied or reduced because of a period of disability, the period of disability will not be taken into consideration." B404.130(f) also permits counting all prior quarters if favorable. RS .120 requires all periods used or all disregarded; selective exclusions are not assumed. Specialist credit regimes are refused first. |
| U4. With unknown periods, fewer than six maximum QCs feasible by the immutable horizon proves establishment impossible after routes adding undeclared credits are excluded, except for blindness with a fully-route flag; it supplies no foreign-credit impossibility proof. | B404.110(b)(1) and B404.130(a) supply the ordinary six-QC prerequisite. U3's disregard cannot manufacture credits. UNKNOWN prior history disables both I15 and I16; current nonblindness cannot exclude a past blind prior. The separate emptiness proof tests the earliest prior as blind, and proves emptiness only if no earlier quarter can supply fully insured status or the alternate. It can preserve a fully-route refusal with empty recent windows only after the universal six-QC horizon floor clears (I17). Foreign credits, credit-route flags, and raw-earnings flags outside a complete direct envelope also preserve named refusals. The direct-envelope contract and declared pre1956 alternate still obey I9; that alternate flag adds no route beyond B4. Blindness alone supplies no credits and does not replace the ordinary fully insured prerequisite. |
| U5. UNKNOWN earnings decide a requested Boolean only if all lower/upper ordinary earnings witnesses agree, under the permitted fixed-period/all-period treatments; an uncertain established start refuses only after at least one feasible filling survives. | B404.143 credits one QC for each increment, maximum four; B404.130 and .146 supply assignment/exclusion rules. Adding ordinary QCs cannot invalidate a fixed treatment. A derived start cannot be silently held fixed when the completion changes it. If a lower or upper representative cannot construct the declared period, but another single filling meets its end and continuity constraints, the public result is `unknown_earnings_years_decide_status`, unless a listed prior that no completion supports refuses first (round 23). If no ordinary filling can qualify by the declared end and all independent routes are impossible, it is an input error and creates no row. A deferred raw-conversion row uses temporary unknown fillings only for possibility, then retains its conversion refusal. Specialist possibilities and administrative-end candidates are considered separately. |
| U6. UNKNOWN administrative end decides a status only when every end-quarter candidate from start through query/cap, plus permitted continuation, agrees, after applying any continuity lower bound. | A216(i)(2)(D) uses "whichever ... is the earlier"; C321(c)(3) includes "the last month for which you received benefits" after substantial gainful activity. Medical continuity cannot exclude early ends; a dated administrative continuity observation can. FRA/death caps limit the latest candidate and do not turn the unknown into a fact. Both ending and prior-history unknown facts remain disclosed when both are missing; UNKNOWN prior history uses the universal envelopes rather than inventing a derived current period to enumerate. The unchanged completion enumeration can include early endings rejected by I14 if declared concretely. Agreement across that larger set still implies agreement across every valid completion, while disagreement can preserve an extra refusal. An actual supplied end keeps its declared-date semantics; known ending provenance requires an ending date. |
| U7. UNKNOWN SSPA applicability preserves an ordinary QC-only false status, but never a QC-only true status. | RS .102 B.2 says the worker "must meet one of the following additional requirements" and may fail "even if" the QC requirement is met. Applicability can remove ordinary insurance and cannot supply missing QCs. Known applicability retains adjudication refusal; any separate specialist path is refused first. |
| U8. With UNKNOWN prior history, a known current period's start is certain onset only if the lower credits insure the onset on every annual placement with no period in force (round 19); otherwise the start stays unknown. | A216(i)(2)(C) and C321(a) make insured onset the earliest legal start. C320(a)'s disregard permits that witness, and no route can move this period before medical onset. Other potentially valid histories prevent an impossibility error but do not fabricate a start. |
| U9. A continues-through observation removes only candidate administrative ends before its date; it never supplies an ending endpoint or removes UNKNOWN-end disclosure. | C321(c) enumerates actual ending events. Observation of a period still in force supplies a lower bound on those events, not their occurrence. Same-quarter ends remain possible, while a later-quarter observation makes the query quarter interior. |
| U10. An automatic alternate-pre1956 possibility can be removed for every filling only when the lower-credit filling has ordinary 20/40 in a quarter disabled in every ending completion, before October 1960. | RS .480 A says "does not have 20/40 for freeze or DIB in any quarter before 10/60". Counts under a fixed all-period use/disregard treatment are monotone in added QCs. The scan retains query, 1960Q3, and month-before-FRA caps for every person (A216(i)(2)(D); C315(a); C321(a)–(b)). For established current periods, its shared date is the declared end minus two calendar months, or continuity date minus two when the end is UNKNOWN, or onset if neither is supplied; it is never before onset. The same two-month exclusion offset applies to FRA/death endings because an earlier recovery remains a possible completion, without inferring that it occurred. UNKNOWN establishment before FRA uses onset. A quarter counts only if its first month is on or before that shared date. RS .480 A's "any quarter" supports a wider scan, while "though under a disability" and "for freeze or DIB" support the shared disabled-quarter scan. A difference preserves the named refusal. Young-worker or blindness witnesses are not substituted for 20/40, upper-only witnesses cannot exclude every filling, and application facts remain unmodeled. |

| U11. Declared foreign totalization credits preserve an unmodeled establishment route immediately after fixed chronology, before every credit-count proof, and retain the named totalization refusal with their row and weight. | No captured rule establishes an own-QC floor for this unmodeled route. Ordinary B404.110(b)(1) cannot prove invalidity under every route. Zero, three, six, and ten own QCs therefore retain `totalization_credits_unsupported`. The rule makes no claim about any totalization minimum, eligibility, foreign-credit count, or benefit amount and uses no totalization source. |

| ID and bound | Captured text and alternative-route defense |
| --- | --- |
| B1. UNKNOWN annual ordinary QCs range from zero through four, reduced to the year's quarters begun by the query and not after the death quarter; neither birth nor a coverage exit bars a quarter of its own year (round 23). Deferred raw-conversion rows use their feasible minimum/maximum fillings only for establishment possibility. Exact annual amounts are monotone in earnings; every calendar year stays in 0–4. | B404.143: "we cannot credit you with more than four QCs for any calendar year"; A213(a)(2)(B)(vi) prohibits duplicate calendar-quarter QCs; B404.146 excludes unbegun/death quarters, and RS .230 B lets a QC take "any quarter in the calendar year" subject to those limits. The exit bars only later years, which the history omits. Additional-credit regimes retain refusal and cannot escape this bound through an ordinary result. Deferred rows still raise their original conversion refusal after a valid possibility survives; no temporary filling is exposed as a computed status. |
| B2. Ordinary fully insured requirements lie in 6–40 and exclude only established disability years. Every elapsed-year endpoint uses its relevant candidate year and the historical sex/cohort rule. | B404.110(b)(1), (b)(2), (c), .132; A214(a) says "not counting ... any year any part of which was included in a period of disability". Medical onset without establishment cannot freeze years. Deemed/transitional alternatives are refused before using the ordinary requirement as universal. |
| B3. A simplified-pre1951 possibility uses the smallest known freeze requirement, or six for unresolved establishment/history, and maximum post1950 ordinary credits without exclusions. UNKNOWN pre1951 raw wages remain potentially decisive. DISABILITY compares the same bound at each quarter where the recent rule holds or blindness removes it. | A213(c) grants "one quarter of coverage for each $400" subject to resulting fully insured status; B404.110(c)-(d); RS .315 B.1-B.2 record alternate historical/application conditions. This is an over-approximation for refusal, not a computed deemed-credit answer. A favorable ordinary witness with a higher requirement cannot narrow it. |
| B4. An alternate-pre1956 possibility uses maximum feasible QCs and an eligible 1952Q3–1955Q4 start with at least 20 total QCs and at least six continuous credited clock quarters, under favorable all-period use or disregard. It survives unless lower credits establish 20/40 in U10's shared disabled-quarter scan. | RS .480 A requires "at least 20 quarters of coverage" and "all quarters beginning with 03/51 ... are QCs", with "at least six"; B.1 permits the first freeze day 07/01/52 through 12/31/55. RS .132 B.2 applies prior-period exclusions to the continuous alternate clock, retaining credited beginning/ending quarters; C.2 requires all periods used or all disregarded. Candidate starts obey I8/I14's latest permissible horizon, so recovery before July 1952 cannot be rescued by the first alternate start. Exclusion instead obeys U10's earliest shared date, including the two-month offset for declared ends and continuity. A lower-credit ordinary 20/40 witness in that shared interval removes the route for all credit fillings; an upper-only or later witness preserves the named refusal. Unmodeled application conditions can remove candidates but do not prove an input error. An explicit `DISABILITY_BEFORE_1956` flag adds no route beyond this check. A fully-route flag may rely on this same alternate possibility when its ordinary recent rules fail; neither flag adjudicates the alternate's application conditions. |
| B5. Universal recent, fully-prerequisite, and annual count envelopes use zero through maximum feasible ordinary lifetime/year QCs whenever unknown periods/earnings can switch witnesses. | A213(a)(2)(B)(vi) prohibits double credit; B404.146(d) excludes interiors unless disregarded. Every concrete ordinary assignment is a subset of feasible unique lifetime quarters. The envelope permits every witness, even when adding QCs switches to a lower-count witness. Specialist possibilities remain refusals. |
| B6. With known earnings and an UNKNOWN ending, returned count bounds include all end-candidate counts admitted by continuity; with entirely known facts they remain exact. | B404.120(b), .130(f), .146(d) distinguish credited endpoints and excluded interiors. All candidate quarters are enumerated, including early endpoints and capped-FRA candidates, subject to any continues-through observation; extrema therefore cover each completion. A continuity date is never inserted as a credited endpoint. No monotonic endpoint-count premise is used. |
| B7. DLI lies through query without frozen exit, or through the pre-FRA-quarter/death horizon with frozen coverage; `None` is the bottom bound. A future exit cannot remove query censoring. | RS .148 defines DLI as "the last day in the last quarter" in which status is met and limits the search relative to FRA. B404.146(b) caps credits after death; A216(i)(2)(B) caps new periods. Future undeclared work is not assumed zero. Specialist routes are refused before this ordinary DLI calculation. |
| B8. For a nonblind ordinary worker with no prior period, no DLI can lie more than 39 quarters after the last credited quarter. | B404.130(b)(2) requires "at least 20 QCs in the 40-quarter period ... ending with that quarter". After 39 later quarters no original QC remains. Blindness and prior-period special/exclusion routes disable this search shortcut; flagged or observable specialist routes refuse. |
| B9. With unknown periods the disregard DLI is a lower bound and the permitted query/FRA/death horizon is the upper bound; unknown SSPA applicability reduces any positive DLI lower bound to `None`. | C320(a) permits favorable disregard; B404.130(f) permits counting all prior-period quarters; RS .102 B.2 imposes an additional requirement. The bound does not infer a particular recovery or history. Exemption can recover the ordinary upper witness but cannot exceed the calendar horizon. Round 19 requires every annual placement to reach the lower bound with no period in force, and refuses by name otherwise. |
| B10. UNKNOWN-ending DLI bounds include every end candidate. With an unresolved ongoing end, known prior history, and frozen-exit future horizon beyond query, the named DLI-horizon refusal remains. | C321(c)'s alternative endings and RS .148's last qualifying quarter permit different historical DLI witnesses. The candidate extrema bound all declared endings; no recovery beyond the query is inferred. Refusal covers the unobserved future administrative fact. Round 17 requires every ending to reach the lower date on a filling with the reported start, and refuses by name otherwise. Under UNKNOWN priors every placement must reach it with no period in force, so no ending changes it (round 19). |
| B11. At most 4,096 combinations of disability endpoint assignments are searched exactly, after any applicable impossibility proof. | B404.143(b) and RS .230 permit favorable assignment; B404.130(f) makes credited endpoints decisive. Six-QC and I15's minimum-requirement checks precede `_boundary_variants`, including both alternate-path calls and UNKNOWN-prior-history feasibility. A remaining excess returns `disability_boundary_assignments_unsupported`; computational complexity is neither a statutory impossibility bound nor permission to retain an all-invalid declaration. |
| B12. Ordinary counted windows have 13 quarters for current insurance and 40 for ordinary disability; young/subsequent special windows require half their elapsed quarters after dropping an odd remainder, with a six-QC minimum. The young-worker window holds at most 39 quarters. A subsequent-special period past 40 quarters computes only where the Act's whole period and 404.130(d)(2)'s 20 of 40 agree (round 17). | B404.120(a) says "13-quarter period"; .130(b) says "20 QCs in the 40-quarter period"; .130(c)-(d) and A216(i)(3)(B) supply the half-quarter, odd-remainder, and 6/12 alternatives. Blindness uses only the fully insured prerequisite. A fully-route flag must still leave a recent-rule witness or possible automatic pre1956 alternate where I16 applies; the pre1956 flag adds no route beyond that alternate. Specialist paths retaining possibility receive their named refusal. |
| B13. Indexed annual QC amounts are at least the prior year's statutory increment and the rounded indexed 1978 amount, with nearest-$10 rounding and $5 ties upward. | A213(d)(2) chooses "the larger of" the prior increment and indexed amount, rounded to "the next higher multiple of $10" at a $5 tie. This exact parameter calculation has no disability or specialist alternative; input-domain checks require positive NAWI and a statutory prior increment. |
| B14. Declaring continuity never widens the administrative-end candidate set; every returned status and count envelope remains valid for every retained concrete ending. | C321(c)'s ending events still govern. Set intersection with ends on/after the observation can only remove candidates; it creates neither an ending nor a new credit. The universal envelope remains unchanged where other unknown facts require it. |
| B15. Round 23 retires the ordinary-establishment overlap search and its 4,096-filling limit: no derived start can overlap a prior (I4). | C320(b)(2) and C321(a) require one insured beginning consistent with the complete declaration, which maximum credits decide by the fixed horizon (I8). The remaining 4,096 limits are B11's and B17's searches and a flagged prior's first-quarter completions; each refuses by name and asserts neither a concrete filling nor an input error. |
| B16. A deferred raw-conversion row retains independently computable ordinary credits in its minimum, and cannot exceed feasible calendar-quarter credits in its maximum. | A213(d)(2)'s prior-increment floor bounds future annual credits above by the captured 2027 increment applied to the supplied wages plus SE income; the possibility-only lower bound is zero. Raw 1937 allocation remains zero through four because A213(b)'s half-year rule is unresolved. For separate pre1955 agriculture or pre1951 SE, supported quarterly wage credits and supported post1950 calendar-year SE credits remain fixed; unresolved additional allocation can fill only remaining allowed quarters. The maximum decides ordinary possibility, and the minimum the alternate's lower-credit exclusion (U10). These bounds do not adjudicate a specialist allocation or replace its refusal. |
| B17. The first-start check refuses when flexible credits allow a better result at any possible start, and it searches at most 4,096 placements of the annual years that can change a first insured quarter. | 404.321(a) gives a record one start, and RS .230 makes placement flexible. A year wholly inside every tested window and untouched by a period adds its full count wherever its QCs fall, so it stays flexible. Without prior periods, an insured worst filling proves no filling starts later, and the check stops. The bound can refuse a declaration that no concrete filling improves, and a search can reach its limit before it attains a result. Round 16's longer search for each status's witness and round 17's lower-date search can reach the same limit. All return `disability_boundary_assignments_unsupported`, so the row keeps its weight; none asserts a filling or an input error. |

The round-5 adversarial audit revisited each row in both directions: a
valid filling cannot be rejected,
and a provably all-invalid declaration cannot become a denominator row.
The fixed-end counterexamples correct I1/I8/U5 and the automatic historical
cap in B4; the wrong-number SS-5 exception and its required possible pre2004
assignment correct I6; continuity adds I11/U9/B14. These are source and
interface requirements, with no new statutory reading.

Round 6 additionally checks both directions of refusal deferral (I12/B1),
the alternate test's own 20/40 exclusion (U10/B4), and fixed-quarter overlap
impossibility before a filling limit can apply (I13/B15, both retired in
round 23). Deferred refusals
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
`test_shared_quarter_declaration_exactly_matches_every_quarter_filling`
(renamed in round 23) uses four missing-year shapes, prior endings in December 1971 or January 1972,
current endings in April/December 1972 or January 1973, and every one of the
16 pre1978 quarterly masks. The specialist grids retain the automatic
alternate-pre1956 route and every `CoverageCondition`.
The specialist test is split by flag class:
`test_exact_classification_keeps_raw_earnings_flagged_routes`,
`test_exact_classification_keeps_independent_credit_routes`, and
`test_exact_classification_bounds_flags_that_add_no_declared_credit`.
Each rules out an automatic pre1956 witness to isolate the flag classes.
Fully-route flags are paired at a proved recent-credit shortfall and the
exact minimum. Raw-earnings flags are paired with a complete direct
envelope and an
unresolved raw row. Credit-route flags retain refusals with a complete
direct envelope, while the declared pre1956 route cannot bypass a
below-six shortfall. Blindness and UNKNOWN prior history preserve the
fully-route flags where the recent-credit proof is inapplicable. The
short-DIB grid
supplies empty and three one-month prior-history fillings.
Each concrete declaration either raises an input error or survives as a
status/refusal; the UNKNOWN declaration must be invalid exactly when all
concrete fillings are invalid. Every surviving UNKNOWN declaration is
also evaluated to assert one retained row and its exact weight.

One corner is excluded by name from this exactness claim. Arbitrary
UNKNOWN prior history is not exhaustively enumerable in this bounded
grid: its earliest-period possibility proof intentionally leaves
unobserved administrative histories unresolved, while the explicit
short-DIB fillings test the retained existential witness. A second
corner, large ordinary-overlap searches, went with the overlap search in
round 23. Specialist
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
  One more QC can also bring a DLI earlier, as intended: it can let
  404.130(b) begin a current period that would otherwise rest on
  404.130(c) alone, and then 404.130(d) no longer reaches the quarters
  after it (round 23):
  `test_one_more_qc_can_bring_the_dli_earlier_intended`.
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
| Every concrete filling of an UNKNOWN onset year starts a valid period, including a start in the quarter the prior ended (round 23); the UNKNOWN year moves the start and retains a refusal and denominator row. | `test_every_onset_year_filling_starts_a_valid_period` |

Round 5 adds exact classification and administrative continuity:

| Invariant | Hypothesis test |
| --- | --- |
| Over the bounded modern and pre1978 shared-quarter grids, `InvalidFamilyInput` occurs exactly when every concrete credit filling is invalid. A surviving filling prevents rejection, while an all-invalid declaration never acquires an evaluator row. | `test_unknown_declaration_exactly_matches_all_concrete_qc_fillings`, `test_shared_quarter_declaration_exactly_matches_every_quarter_filling` |
| The automatically detected alternate-pre1956 start obeys the same fixed declared-end and continuity bounds as an ordinary start. A start horizon before July 1952 cannot use the first permitted July 1, 1952 freeze; a later permissible horizon preserves the specialist refusal. A recovery-only declared end must reach September to permit a July recovery month; a July continuity observation keeps the later UNKNOWN end possible. | `test_automatic_pre1956_start_respects_immutable_bound_property` |
| An automatically detected historical start must fit before the actual month-before-FRA end, including when FRA and the first possible alternate start share July 1, 1952. | `test_automatic_pre1956_start_respects_fra_cap_property` |
| An adjudicated section 211 exemption preserves the ordinary status/count result and one evaluator row for source-permitted post2003 and never-assigned facts; observed and convention-filled facts have equal statutory treatment. Pre2004-assigned aliens accept exactly the exempt declaration and reject declared applicability. An alien born on/after January 1, 2004 cannot supply the required possible pre2004 assignment and therefore cannot declare exemption. | `test_adjudicated_exemption_preserves_ordinary_count_and_evaluator_row`, `test_pre2004_assignment_accepts_exactly_the_exempt_applicability`, `test_wrong_number_exemption_requires_possible_pre2004_assignment` |
| A continuity declaration never widens the candidate-ending set. Every returned status and count envelope agrees with or contains every retained concrete ending; no continuity observation becomes a credited endpoint. | `test_continuity_only_narrows_candidates_and_all_concrete_ends_agree` |

Round 6 adds refusal ordering and settled route exclusions:

| Invariant | Executing tests |
| --- | --- |
| Adding any of the four early raw-conversion refusal facts where it cannot change an all-invalid declaration preserves `InvalidFamilyInput`, zero rows, and zero weight, independently of mapping order. Placing it where concrete credit fillings can validate the declaration preserves the original refusal reason and note. Multiple deferred reasons retain sorted-year priority, including with many UNKNOWN years. | `test_irrelevant_early_refusal_fact_preserves_all_invalid_grid_case`; `test_every_early_qc_refusal_preserves_possible_declaration`; `test_deferred_refusals_keep_original_sorted_year_priority`; `test_many_unknown_years_keep_original_deferred_refusal` |
| An unsupported future increment cannot hide a fixed earlier impossible end, for zero, one, or 10,000 raw wage dollars, including the age-62 and coverage-exit interfaces. The captured increment floor can prove too few possible credits; a sufficient possible filling keeps the original refusal. All schema/history errors still precede deferred refusals. | `test_unrelated_uncaptured_increment_cannot_hide_impossible_fixed_end`; `test_uncaptured_increment_bounds_preserve_both_classifications`; `test_schema_validation_precedes_deferred_qc_refusals` |
| A lower-credit 20/40 witness in a quarter disabled in every ending completion, before October 1960, makes the automatic alternate unavailable under every added unknown-credit filling. The scan includes later disabled quarters and 1960Q3 only when shared by every completion, excludes 1960Q4 and quarters beginning in or after the FRA month for every person, and does not substitute blindness or the young-worker rule for 20/40. Round 10 corrects the shared date to the declared end minus two months or continuity minus two months, never before onset; without either date it is onset. An upper-only witness preserves the alternate refusal and evaluator row. | `test_fixed_twenty_of_forty_exclusion_survives_extra_unknown_credits`; `test_twenty_of_forty_before_october_1960_excludes_alternate_refusal`; `test_twenty_of_forty_scan_includes_later_disabled_quarters_before_1960`; `test_twenty_of_forty_alternate_exclusion_stops_before_october_1960`; `test_alternate_exclusion_uses_existing_disability_scan_fra_boundary`; `test_other_ordinary_disability_routes_do_not_supply_twenty_of_forty`; `test_some_twenty_of_forty_fillings_keep_named_alternate_refusal`; `test_independent_date_oracle_classifies_both_alternate_scan_directions` |
| Excluding an unavailable alternate does not reject an ordinary current establishment or prove possible nonempty prior history empty. | `test_excluding_alternate_preserves_ordinary_current_establishment`; `test_excluding_alternate_preserves_possible_nonempty_prior_history` |
| A start may share the quarter a prior ended (round 23), so a record whose only possible start is that quarter stands or falls on its credits: UNKNOWN credits keep the earnings refusal and its row, every 1974–1977Q1 quarter credited starts the period on the onset day, and one fewer leaves no insured quarter. A prior ending in the onset quarter classifies like one ending the quarter before. | `test_a_shared_end_quarter_leaves_validity_to_unknown_credits`; `test_shared_end_quarter_validity_stays_with_unknown_credits`; `test_a_prior_ending_in_the_onset_quarter_classifies_like_one_before` |
| Deferred historical-credit fillings retain every independently guaranteed quarter. In the corrected continuous-clock case all 16 fillings keep a row with a named pre1956 refusal, since a credited Q1 starts the period on the onset day in the quarter the prior ended (round 23), and raw agricultural wages keep their deferred refusal with or without an independently credited Q1. Mapping order changes neither conclusion. | `test_deferred_quarter_fillings_survive_a_shared_onset_quarter` |

Round 7 pins the eligibility boundary independently of the ordinary scan:

| Invariant | Executing tests |
| --- | --- |
| For the round-7 cases, whose declared ends are the month before FRA, a 20/40 witness excludes the alternate exactly when its quarter begins by the earliest shared disabled date, before the FRA month, and before October 1960, over all twelve FRA months and witness quarters. Round 10 makes that shared date two months before the declared end even when the end itself implies no recovery. Exclusion yields the ordinary result or a genuinely impossible declaration; non-exclusion preserves the named refusal, one evaluator row, and weight 7/3. | `test_independent_date_oracle_classifies_both_alternate_scan_directions` (Hypothesis with an independent date oracle); `test_fra_quarter_stays_only_when_it_begins_before_fra_month` |
| Established, absent, and UNKNOWN current-period declarations share the same FRA exclusion bound. Declared-absent ordinary pre-FRA neighbours retain their results; round 9 corrects the UNKNOWN-establishment DISABILITY neighbour. | `test_unestablished_period_keeps_alternate_after_fra`; `test_unestablished_period_pre_fra_neighbour_keeps_ordinary_result`; `test_reviewed_fra_neighbours_preserve_their_public_results` |
| The reviewed FRA-month witness retains the historical refusal and exact denominator weight under the ordinary query and OP12 exit; a deferred 1937 conversion retains its original reason instead. | `test_fra_month_witness_keeps_reviewed_refusal_and_denominator` |

Round 8 limits exclusion to quarters covered by every ending completion;
round 10 corrects their shared disabled-date bound by two months:

| Invariant | Executing tests |
| --- | --- |
| A lower-credit 20/40 witness excludes the alternate exactly when its quarter begins on or before the established period's earliest shared disabled month, before the FRA month, and before October 1960. That month is two months before the declared end or, for an UNKNOWN end, the continuity date, never before onset; without either fact it is onset. The recovery month's quarter remains eligible, including a month in its middle; the following quarter does not exclude. Both computed and refused outcomes retain one evaluator row and exact weight 11/5. | `test_declared_end_quarter_includes_witness_but_next_quarter_refuses`; `test_unknown_end_keeps_onset_witness_but_refuses_later_quarter`; `test_continuity_quarter_includes_witness_but_later_quarter_refuses`; `test_later_disabled_quarters_with_unknown_end_keep_named_refusal`; `test_october_1960_boundary_with_unknown_end_keeps_named_refusal`; `test_independent_date_oracle_classifies_covered_quarters_both_directions` (Hypothesis with an independent date oracle) |
| If any declared-end completion preserves the named alternate refusal, an UNKNOWN ending returns no status. An onset-quarter witness remains shared by every completion; a witness in a later quarter without continuity does not. | `test_unknown_end_cannot_return_status_when_declared_completion_refuses` (Hypothesis); `test_unknown_end_keeps_onset_witness_but_refuses_later_quarter` |
| The round-7 comparison's ordinary witness after the declared end preserves `disability_before_1956_unsupported`, one evaluator row, and exact weight 11/5. It cannot prove invalidity under every defensible reading. | `test_round_seven_declared_end_comparison_retains_named_refusal`; `test_alternate_exclusion_uses_existing_disability_scan_fra_boundary` |

Round 9 extends the completion invariant to UNKNOWN establishment. The
invented round-7 neighbour has birth May 2, 1895, onset July 15, 1955 and
first 20/40 in 1960Q2. An established completion with an UNKNOWN end or an
early September 30, 1955 end retains the alternate refusal, because the
later witness does not cover every possible period. UNKNOWN establishment
therefore returns `disability_before_1956_unsupported` for DISABILITY,
retaining one row and weight 7/3. FULLY still computes true: its credit
witness survives favorable disregard under 404.130(f) and 404.320(a).
CURRENTLY and ALL retain
`unknown_current_disability_period_decides_status`; ALL encounters the
CURRENTLY refusal first. Declared absence keeps all four existing outcomes.
The split round-7 regression changes only its former `[unknown]` case.

Both new decision sites use the same UNKNOWN-establishment predicate as
`insured_status`, including onset before the FRA month. Onset at or after
that boundary admits no established completion (premise U2), so neither
site applies the new restriction there. Round 9 left the FRA bound, event
scan, and repeated-work cost unchanged.
Round 10 preserves those decisions and corrects only the shared disabled
month used for period-limited exclusion.
The rule continues to adopt neither reading of RS .480 A.

A separate prior-history audit found no corresponding disagreement. An
invented May 2, 1895 birth has two 1940Q1–Q2 credits, every 1951–1954
quarter, 1955Q1–Q3, and 1960Q2, with zeros elsewhere. A possible prior
April 15–June 30, 1955 period has 20 lifetime QCs, every preceding
post-1950 quarter, and fewer than 20/40, so its starting route can be the
alternate subject to unmodeled application conditions. With current
establishment declared absent and onset July 15, 1955 or January 15, 1956,
UNKNOWN prior history, known empty history, and that supplied prior period
all preserve true DISABILITY and FULLY witnesses. The supplied prior
period is an adjudicated input; favorable disregard under 404.130(f) does
not end the current disabled interval. UNKNOWN prior CURRENTLY and ALL
retain their named unknown-prior refusal. With current establishment
ending September 30, 1955, all three histories instead preserve the
alternate refusal. The reproducible invented probe checks 28 public rows,
including all refusal weights; it justifies no prior-history code change.

| Invariant | Executing tests |
| --- | --- |
| If any established completion retains the alternate refusal, UNKNOWN establishment returns no DISABILITY status. If every established completion computes the same DISABILITY status and declared absence agrees, UNKNOWN does not refuse the alternate route. Every outcome retains one row and exact weight 7/3. | `test_unknown_establishment_cannot_compute_when_completion_refuses`; `test_unknown_establishment_keeps_agreed_completion_status` (Hypothesis) |
| The independent date oracle excludes the alternate under UNKNOWN establishment exactly when the lower-credit 20/40 witness begins in the onset quarter, before the FRA month and October 1960. Later witnesses preserve the refusal. | `test_independent_date_oracle_classifies_unknown_establishment_both_ways` (Hypothesis and explicit boundary examples); `test_unknown_establishment_refuses_witness_one_quarter_after_onset` |
| On the reviewed neighbour, UNKNOWN DISABILITY refuses the alternate, FULLY remains true, CURRENTLY and ALL retain their existing unknown-current refusal, and declared absence keeps all four results. The onset-quarter witness, post-1955 onset, and onset at or after FRA retain their public outcomes. | `test_reviewed_status_table_retains_rows_and_weights`; `test_unknown_fully_keeps_favorable_ordinary_witness`; `test_unknown_establishment_keeps_round_five_onset_quarter_witness`; `test_unknown_establishment_post1955_onset_keeps_ordinary_status`; `test_unknown_establishment_at_or_after_fra_keeps_existing_refusal` |

Round 10 makes recovery chronology, the alternate clock, and proof ordering
explicit:

| Invariant | Executing tests |
| --- | --- |
| A recovery-only ending implies the month two months earlier. The recovery month cannot precede onset, and a first insured quarter beginning after that month cannot establish the period. A quarter beginning by that month can. Invalid declarations create no rows; valid outcomes retain exact weight 11/5. | `test_review_recovery_grace_quarter_cannot_establish_current_period`; `test_recovery_quarter_counts_but_next_quarter_cannot_start`; `test_recovery_month_onset_requires_smallest_two_month_gap`; `test_recovery_horizon_cannot_open_first_statutory_alternate_quarter` |
| The recovery inference stops at February 1981 and does not apply to an end in the FRA-ending month or death month. Neighboring earlier ends still infer recovery. This tests only the helper's scope and preserves existing paragraph (c) behavior. | `test_january_1981_recovery_bound_stops_at_first_paragraph_c_end`; `test_fra_ending_month_does_not_imply_recovery`; `test_death_ending_month_does_not_imply_recovery` |
| An independent plain-date oracle applies the two-month offset in both exclusion directions. A grace-month 20/40 witness cannot exclude every recovery completion; the named alternate refusal retains one row and exact weight. | `test_plain_date_oracle_applies_two_month_offset_in_both_directions` (Hypothesis); `test_review_recovery_grace_witness_keeps_alternate_refusal` |
| All-period use and disregard both apply to the alternate continuous-QC clock, with credited endpoints retained. Removing each one of the 20 QCs in the reviewed case destroys a required route condition and changes its classification to input-invalid with no row. | `test_review_prior_period_exclusions_open_alternate_continuous_clock`; `test_continuous_alternate_clock_requires_each_of_twenty_qcs` |
| A declaration with historical ends is input-invalid exactly when no enumerated concrete filling has a witness on any remaining route. The minimum-QC proof never rejects a generated declaration accepted by enumeration through the existing witness path. | `test_historical_end_exact_classification_matches_every_witness_filling`; `test_minimum_qc_proof_never_rejects_an_enumerated_witness` (Hypothesis) |
| A lifetime-QC shortfall proved before endpoint enumeration remains an input error with no evaluator row even when the boundary assignment product exceeds 4,096. A declaration at the exact minimum survives. Blindness and UNKNOWN prior exclusions retain their valid routes. | `test_impossible_fifteen_qcs_precede_boundary_complexity_without_a_row`; `test_exact_minimum_qcs_are_not_rejected_by_the_proof`; `test_blindness_keeps_six_qc_concrete_short_prior_period_route`; `test_unknown_prior_history_can_reduce_the_unseen_special_requirement` |
| Declared foreign credits retain `totalization_credits_unsupported`, one row, and exact weight once fixed chronology clears. Round 11 removes round 10's unsupported six-own-QC floor, including the three-own-QC case. No totalization minimum or substantive eligibility is inferred. | `test_ten_own_qcs_and_foreign_credits_keep_named_refusal_and_weight`; `test_six_own_qcs_foreign_credits_and_unknown_prior_keep_refusal`; `test_three_own_qcs_and_foreign_credits_keep_named_refusal_and_weight`; `test_foreign_credit_refusal_is_independent_of_own_qc_count` |

Round 11 applies the flag premises to the same proof and retains exact
denominators:

| Invariant | Executing tests |
| --- | --- |
| Adding foreign credits to a declaration clearing fixed chronology always preserves the totalization refusal, one row, and exact weight, independently of its own-QC count or flags. A prior ending in the onset quarter leaves a valid start, so every flag and foreign credits keep their named refusals there (round 23). | `test_foreign_credit_refusal_is_independent_of_own_qc_count` (Hypothesis); `test_foreign_credits_refuse_without_an_own_qc_floor`; `test_a_prior_ending_in_the_onset_quarter_leaves_a_valid_start`; `test_a_prior_ending_in_the_onset_quarter_keeps_every_route_refusal` |
| With known prior history and no blindness, any flag set supplying no additional credit under the complete direct-envelope contract leaves a total-QC shortfall below the recent-rule minimum input-invalid. The expected minimum is computed independently of `_minimum_current_period_qcs`; round 12 supplements this numerical proof with the candidate-quarter scan below. | `test_no_credit_flag_set_cannot_hide_independently_proved_shortfall` (Hypothesis); `test_no_credit_flag_shortfall_and_exact_minimum_pair`; `test_review_recent_credit_shortfall_cannot_be_cured_by_deeming` |
| A flag cannot turn a declaration meeting every ordinary requirement into an input error. At the exact ordinary or under31 minimum, each flag retains its own reason, one row, and exact weight. | `test_no_flag_rejects_declaration_meeting_every_requirement` (Hypothesis); `test_no_credit_flag_shortfall_and_exact_minimum_pair`; `test_credit_route_keeps_refusal_even_with_complete_direct_envelope` |
| Fully-route flags retain their named refusals with blindness below six actual QCs, or with UNKNOWN prior history and at least six QCs feasible by the horizon, surviving the joint optimistic-clock proof. The declared pre1956 alternate cannot bypass the ordinary six-QC floor even with blindness, but at 20 QCs retains its refusal. | `test_fully_route_refuses_when_recent_credit_proof_does_not_apply`; `test_pre1956_flag_with_blindness_keeps_ordinary_six_qc_floor` |
| A complete direct envelope bounds every raw-earnings flag, including UNKNOWN rows; a raw row preserves its unmodeled allocation route. Military and Medicare government credits preserve a separate route even with direct rows. Combining flags preserves each independent route. | `test_raw_earnings_flag_preserves_route_only_without_direct_envelope`; `test_exact_classification_bounds_flags_that_add_no_declared_credit`; `test_credit_route_keeps_refusal_even_with_complete_direct_envelope`; `test_two_flag_classes_preserve_each_independent_route` |

Round 12 closes round 11's temporal limitation. An invented worker born
February 2, 1960, with onset January 15, 2000, an established period ending
December 31, 2000, known empty prior history, no blindness, and 20 direct
QCs entirely in 1978–1982 has zero QCs in every candidate 40-quarter
window. The unflagged declaration and each fully-route declaration now
raise `InvalidFamilyInput`, with no evaluator row. Reducing the total to
19 remains invalid under the earlier numerical proof. The new recent scan
keeps both inclusive quarter edges, the immutable horizon and recovery
bound, favorable assignment, all-period use or disregard, and
under31/subsequent-special alternatives (round 23 removed its
prior-period overlap check). It ignores only
the fully insured prerequisite. A recent witness preserves the flag's
named refusal even when the ordinary fully insured requirement fails.
Blindness, UNKNOWN prior history, an open automatic pre1956 alternate, or
an unresolved scan complexity likewise preserves possibility. The
`DISABILITY_BEFORE_1956` flag has no separate early return: an onset after
1955 with neither an ordinary nor an alternate route is invalid, while
either possible route preserves the flag's named refusal. These are
establishment-classification corrections under 404.130(a)–(d), C320(b)(2),
C321(a), and RS .480 A–B.1, not adjudications of the flags' own conditions.

| Invariant | Executing tests |
| --- | --- |
| With known prior history, no blindness, and only flags adding no credits, a declaration with onset after 1955 is input-invalid when an independent plain-arithmetic assignment/window oracle finds no recent witness. The generated grid includes declarations before age 31. Every invalid declaration has no evaluator row or weight. | `test_independent_recent_oracle_proves_no_credit_flag_impossibility` (Hypothesis); `test_old_lifetime_credits_cannot_supply_any_recent_window` |
| A fully-route flag relaxes only the fully insured prerequisite. With the alternate absent, its establishment classification matches the independent recent oracle in both directions; a recent witness retains its named refusal even when the ordinary fully insured prerequisite fails. A possible alternate independently preserves that refusal. | `test_fully_flag_changes_fully_only_against_unflagged_recent_oracle` (Hypothesis); `test_fully_flag_exactness_includes_independent_alternate_oracle` (Hypothesis); `test_fully_route_relaxes_only_fully_insured_when_recent_rule_passes`; `test_fully_route_keeps_alternate_when_ordinary_recent_rule_is_closed` |
| At every tested quarter, a true ordinary DISABILITY witness stays true when only the fully insured prerequisite is relaxed on identical credits. | `test_witness_keyword_only_relaxes_fully_prerequisite` (Hypothesis) |
| The recent scan includes both the onset quarter and horizon quarter, and the horizon quarter counts even when the end falls inside it. It does not admit a witness beyond an inferred recovery bound. A credit one quarter too old cannot enter any candidate window. | `test_scan_includes_onset_and_the_earliest_quarter_of_forty`; `test_scan_includes_horizon_quarter_and_stops_at_recovery_bound`; `test_scan_reaches_last_candidate_quarter_even_with_end_inside_quarter` |
| The recent scan retains under-31 and subsequent-special requirements, favorable use of every prior period or disregard of every period, credited endpoints, and an onset in the quarter a prior ended, which can supply the witness (round 23). | `test_special_recent_requirement_and_one_short`; `test_subsequent_special_recent_rule_can_pass_below_twenty_qcs`; `test_recent_window_uses_all_prior_periods_or_disregards_all`; `test_an_onset_in_a_prior_end_quarter_can_supply_the_recent_witness` |
| Blindness and UNKNOWN prior history preserve fully-route refusals even with empty recent windows; UNKNOWN priors still require six horizon-feasible QCs and must survive the joint optimistic-clock proof. UNKNOWN recent years preserve possibility whenever an admissible filling supplies a recent witness, and every surviving concrete filling retains the flag's refusal. Complexity preserves that flag reason rather than substituting a computational refusal. | `test_empty_windows_keep_fully_route_blindness_and_unknown_prior_bypasses`; `test_unknown_recent_years_and_every_surviving_filling_keep_flag_reason`; `test_complexity_preserves_fully_route_reason` |
| A declared pre1956 flag adds no establishment route beyond the automatic alternate: onset after 1955 with no ordinary route is invalid; either an ordinary witness or the historical alternate retains the named refusal. Credit-route and unbounded raw-earnings flags remain capable of adding credits, and a deferred conversion keeps its original reason when a recent witness remains possible. Surviving outcomes retain one evaluator row and exact weight 11/5. | `test_pre1956_flag_cannot_open_a_route_after_1955`; `test_pre1956_flag_keeps_named_refusal_when_alternate_conditions_hold`; `test_pre1956_flag_keeps_named_refusal_when_ordinary_route_is_open`; `test_credit_and_unbounded_raw_earnings_flags_can_add_recent_credits`; `test_deferred_conversion_keeps_original_refusal_with_possible_recent_rule` |

The round-8 UNKNOWN-ending and round-9 UNKNOWN-establishment completion
properties above remain in force with the corrected shared disabled month.
The independent historical grid and generated witness enumeration do not
call the new proof to decide their expected valid fillings.

The reviewed recovery counterexample has birth January 2, 1906, female sex,
onset July 15, 1956, and an established end May 31, 1962. Credits are
1957Q1–Q3, every quarter in 1958–1961, and 1962Q2, with zeros elsewhere.
Recovery is March 1962, before the first 20/40 quarter begins in April.
The alternate cannot apply to a 1956 onset, so the declaration is invalid.
The neighboring pre1956 example has birth May 2, 1895, onset July 15,
1955, one 1940Q1 credit, every 1951–1954 quarter, 1955Q1–Q3, and 1957Q2.
An end May 31, 1957 or UNKNOWN end with continuity through May 15, 1957
permits recovery in March, before the first ordinary April witness.
Both FULLY and DISABILITY retain the alternate refusal and weight 11/5.

The reviewed continuous-clock case has birth February 2, 1906, female sex,
onset January 15, 1955, end July 31, 1956, and a prior July 1,
1952–December 31, 1954 period. Every quarter in 1938–1940 and 1951, plus
Q1–Q2 in 1941 and 1952, supplies exactly 20 total QCs. Using the prior
period removes the intervening uncredited quarters from the continuous
clock. The remaining six clock quarters are 1951Q1–1952Q2, all credited.
FULLY at February 1968 therefore retains the alternate refusal, one row,
and weight 11/5. Deleting any one credit leaves either fewer than 20 total
QCs or a broken continuous clock, so no route survives.

The UNKNOWN-prior-history continuous-clock check reuses that same invented
20-QC case. Supplying the prior period opens the alternate and refuses by
name for all four requested tests. Omitting its dates under UNKNOWN
provenance allows an unfilled prior period to remove those clock gaps,
but does not demonstrate a wrong computed Boolean: FULLY is already true
under favorable disregard, while CURRENTLY, DISABILITY, and ALL retain
`unknown_prior_disability_periods_decide_status`. `test_unknown_prior_continuous_clock_preserves_favorable_full_and_refuses_dib`
pins the public completion comparison. That eight-call comparison shows a possible alternate completion without justifying a
prior-history code change. It does not assert that UNKNOWN history is
empty or that the alternate clock is closed in every completion.

The post-1980 check compares a January 31, 1981 end with a February 28,
1981 end. The first can imply November 1980 recovery and cannot admit a
first January 1981 insured quarter; the second falls outside the inference
and preserves the existing January witness. Ordinary modern declarations,
UNKNOWN-end enumeration, and paragraph (c) endings are otherwise left
alone. This boundary comparison makes no claim about which paragraph (c)
ending an administrative record would establish.

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
May birth. Both neighbours refuse by name under round 10. The May neighbour
permits a recovery completion in February, before the first April 1960
ordinary witness, although its April FRA ending implies no recovery fact.
These are invented cases, not published worked examples.

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
Round 10 applies the two-month offset to these comparisons: an April 1,
1956 witness cannot exclude the alternate with a May 31, 1956 end or a
May 15 continuity observation, because the shared disabled month is March.
A June 30 end instead supplies April as the shared month, so the April
quarter can exclude while July cannot. Each surviving outcome retains one
row of weight 11/5. The control born February 2, 1920 remains computed
with a January 15, 1955 onset-quarter witness even when the end is UNKNOWN;
moving its first ordinary witness one quarter later without continuity
retains the alternate refusal.

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

Round 6's fixed-overlap example (birth February 2, 1940, onset February
15, 1977, a supplied January 1, 1970–January 31, 1977 prior period, four
QCs in each of 1968 and 1969, UNKNOWN 1974–1977, zeros elsewhere) no
longer turns on overlap. Its prior has no basis: she can reach 20 of 40
at 1970Q1 only with QCs before 1968, which the record lacks, and past
blindness counts only from 1973. With an April 30, 1977 current end,
every filling of the UNKNOWN years refuses by the prior's name before any
input error (round 23). The round 6 tests now use a prior from January 1,
1973 and four QCs in each of 1966–1968. Those 12 QCs give fully insured
status for her 11 elapsed years, so the prior rests on past blindness,
and only 1977Q1, the quarter it ended in, can start the current period
before the February recovery. There 20 of 40 needs the prior disregarded
and every 1974–1977Q1 quarter credited, so the UNKNOWN years decide
validity and the record retains `unknown_earnings_years_decide_status`
(C320(b)(2); C321(a)).

A deferred-allocation control has birth February 2, 1920, onset February
15, 1954, a July 15, 1952–January 31, 1954 prior period, current end
December 31, 1954, and January 1968 FULLY query, with observed facts.
Credits are one in 1938,
four in each of 1946–1948, one in 1949, four in 1951, and two in 1952;
other years are zero. The prior has RS .480's 20 lifetime and six
continuous credits. Round 10 opens the alternate current route when prior
periods are used for the continuous clock. All 16 concrete 1954 masks are
valid: a credited Q1 starts the period on the onset day, in the quarter
the prior ended in January (round 23; round 6 rejected those eight). The
all-zero outcome is a named alternate refusal, not an ordinary witness.
Raw agricultural wages of $100 preserve
`pre1955_agricultural_allocation_unsupported`, with or without $50 of
independently credited Q1 nonagricultural wages.

The fixed-end example has birth February 2, 2000, medical onset January 15,
2022, observed establishment, a January 31, 2022 declared end, four QCs
in 2021, UNKNOWN 2022 credits, and zeros elsewhere. At an April 2022
FULLY query, only five QCs can be assigned by the end's quarter: four
earlier credits plus 2022Q1. All five concrete 2022 counts fail, so the
UNKNOWN declaration raises `InvalidFamilyInput` through the evaluator;
it cannot contribute a row of weight 3/2. The nine nearby combinations
of two, three, or four 2021 QCs with January, February, or March 2022
ends fail for the same reason at an October 2022 query. The existing
round-4 onset-year and earlier-valid-end cases remain valid UNKNOWN
declarations. In the shared-quarter grid, with the January 1972 prior
ending, a December 1972 current ending leaves 15 of the 16 UNKNOWN-1972
quarter masks valid: any 1972 QC insures a quarter that begins by the
October recovery, and a 1972Q1 QC starts the period on the onset day in
the quarter the prior ended (round 23; round 5 found seven). An April
1972 ending puts recovery in February, so only the eight masks with a
1972Q1 QC are valid (round 5 found none).

The automatic historical-bound counterexample has a woman born February
2, 1900, current onset January 15, 1952, observed establishment and empty
prior history, fourteen older QCs, and six QCs in the mandatory
1951Q1–1952Q2 window. She has twenty lifetime QCs but
fails the ordinary recent-work test. A March or June 1952 declared end,
or a continuity observation in either month, cannot use RS .480's first
permitted July 1, 1952 start. The declaration is therefore input-invalid.
A July declared end now also fails, because it implies May recovery. A
September declared end implies July recovery and preserves the automatic
route. July and September continuity observations instead retain the
unknown-ending route and its named refusal. This source-required
chronological check applies to the automatic alternate even with an
explicit `DISABILITY_BEFORE_1956` declaration or a fully-route flag. A
woman born July 2, 1887 reaches FRA in July 1952, so her
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
zero QCs. Positive 1972 fillings instead start the period on the onset
day, in the quarter the prior ended, which round 23 accepts (RS .140
example 7). The UNKNOWN year therefore moves the start:
`test_unknown_onset_year_earnings_decide_the_current_start` and
`test_every_onset_year_filling_starts_a_valid_period` retain the named
earnings refusal and row.

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
(men born before January 2, 1911 at age 65 and men born January 2, 1911
through January 1, 1913 at 1975, under 404.110(b)(2)(iii)–(iv); women at
62), by footnote 1's January 1 rule, and by year of death for a worker who
attained 21 before 1951. They also compare every CFR 404.115 cohort row,
including January 1/January 2 boundaries and sex distinctions. Footnote 2
says "The determining age for men born before 1/2/31 is age 65", which
404.110(b)(2)(iv) contradicts: age 65 applies only to a man who reached
62 before 1973. The exhibit's table merges men born 1910–1913 into one
1975 row, which 404.110(b)(2)(ii) through (iv) all give. The January 2,
1913 date in 20 CFR 404.132(b) belongs to the disability prerequisite's
1975 cap. The GIF renderings' text is not captured, so the rule claims no
reading of them.
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
earnings. An exit year's annual amounts cover work through the exit month,
an interface convention rather than a statutory emigration exclusion, and
since round 23 the exit bars no quarter of its own year.

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
the alternate-route exclusion and, until round 23, the fixed-quarter
overlap check apply captured RS .480 A, C320(b)(2), and C321(a). Round 7
corrects the FRA bound using
A216(i)(2)(D), C315(a), and C321(a)–(b). Its application to every person
follows RS .480 A's “for freeze or DIB”; establishment is not a condition.
The source conflict remains
`us:oasdi-insured-pre1956-alternate-any-quarter-scan`. RS .480 A says a
worker "though under a disability, does not have 20/40 for freeze or DIB in
any quarter before 10/60". "Any quarter" supports the literal scan;
"though under a disability" and "for freeze or DIB" support the narrower
scan through the declared period. C321(b), quoted above, links a recovery
ending to the disability ending two months earlier. The former direct use of the administrative
end as the disabled date was two months too late. Validity uses the latest
possible disabled month, with FRA/death carve-outs; alternate exclusion
uses the earliest recovery completion, including at those carve-outs.
The conservative exclusion does not infer recovery from an FRA or death
ending. It preserves the named refusal because UNKNOWN must hold for every
completion. No recovery month is inferred for paragraph (c) endings, and
no wider claim about those endings is made here.

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

Declared totalization credits introduce no new substantive statutory
reading. Round 11 removes the unsupported own-six-QC floor: once fixed
chronology clears, the unmodeled route retains its named refusal for zero,
three, six, and ten own QCs, one row, and weight 11/5. This is a
classification correction. The rule makes no claim about any totalization
minimum, eligibility, foreign-credit count, or money and uses no
totalization source.

Round 11 also moves the recent-credit impossibility proof ahead of the
fully-route flags. Section 404.130(a) requires a recent rule "and you must
be fully insured"; RS .106 B.2's "deemed fully insured for all title II
purposes" changes the latter prerequisite only. For the reviewed worker
born January 2, 1924, six QCs in 1984–1985 cannot meet 20/40 for a 1985
established period, even with `DEEMED_FULLY_INSURED`. The corrected result
is an input error and zero rows; 20 recent QCs preserve the deemed-full
refusal, one row, and weight 11/5. The fully-route, recent-test,
raw-earnings, and credit-route classifications above follow the captured
premises and introduce no additional discretionary reading. Round 12
also applies the recent rule to the temporal location of those credits:
20 old lifetime QCs cannot cure an empty candidate window. RS .480 B.1's
"the last day on which it can begin is 12/31/55" also bars a separate
pre1956-flag escape for a later onset. The flag adds no route beyond the
automatic alternate check. Neither correction tests a flag's own
conditions; an explicitly declared fully insured route remains a supplied
fact even if its cohort would not satisfy 404.112. These corrections make
no payment adjudication and establish no dollar change.

## Source-conflict register

Each `# Source conflict <id>` marker in `insured_status.py` and
`_insured_status_qc.py` names one of these nine readings on the marker's own
line. `tests/test_track_b_insured_status_readings.py` holds the markers and
this list to the same ids. Each reading changes classification and row weight
and computes no payment.

- `us:oasdi-insured-prior-disability-favorable-disregard` (`_witness`). RS
  00301.140 example 9 prints that Sam isn't insured as of 5/93, and
  404.130(f) counts a prior period's quarters where that favors the worker.
  The rule computes each status twice, once using every prior period, which
  leaves its interior quarters out of the count, and once disregarding them
  all, and keeps the favorable result.
- `us:oasdi-insured-disability-period-endpoint-quarters` (`_allowed_quarters`
  in `_insured_status_qc.py`). 404.130(f) keeps a period's first and last
  quarters when each is a QC, and RS 00301.140 example 6 and RS 00301.147
  example 3 print counts without them. The rule keeps the endpoint quarters
  eligible, and neither printed case changes its insured answer.
- `us:oasdi-insured-pre1951-seven-elapsed-years`
  (`_pre1951_aggregate_possible`). Act 213(c) deems one QC for each $400 of
  pre-1951 wages and states no seven-elapsed-year minimum, and RS 00301.315
  B.1 records the minimum and its later repeal. The bound applies no minimum,
  and a potentially decisive aggregate refuses by name
  (`simplified_pre1951_unsupported`).
- `us:oasdi-insured-simplified-pre1951-disability-scope`
  (`_aggregate_could_insure`). Act 223(c)(1)(A), 216(i)(3)(A) and 404.132
  reach the fully insured prerequisite of disability insured status, and RS
  00301.315 B.1 says the simplified method doesn't apply to disability
  claims. The rule follows the statute and the regulation, credits no deemed
  quarter, and refuses by name where the aggregate could decide a disability
  result.
- `us:oasdi-insured-pre1956-alternate-any-quarter-scan`
  (`_pre1956_alternate_possible`, `_prior_basis`). RS 00301.480 A bars the
  pre-1956 alternate for a worker with 20/40 "in any quarter before 10/60",
  and its other words reach only quarters the period covers. The scan stops
  at the latest date every completion's period covers, and a possible route
  refuses by name (`disability_before_1956_unsupported`). A listed prior's
  establishment shows its holder met the route's application conditions, so
  B.1's counts on every completion, with 20/40 on none through September
  1960, hold such a prior. Where only one reading of A, or only some completion,
  allows it, it refuses by the route's name; where every completion has
  20/40 in a quarter the prior covers, both readings exclude the route
  (round 23).
- `us:oasdi-insured-historical-end-recovery-month`
  (`_historical_recovery_month`). 404.321(b) ends a period on the last day of
  the second month after the month the disability ended, and the interface
  declares no recovery month. For an end before February 1981 that precedes
  the FRA and death endings, recovery falls two months earlier, and that month
  bounds a valid onset and start. FRA, death and paragraph (c) endings infer
  no recovery.
- `us:oasdi-insured-unknown-prior-historical-blindness`
  (`_unknown_prior_joint_shortfall`). Person fields declare current blindness
  only, and 404.130(e) asks a blind worker for fully insured status alone. The
  proof that no UNKNOWN prior can insure the current period therefore lets the
  earliest prior rest on fully insured status, whatever `statutory_blindness`
  says.
- `us:oasdi-insured-one-filling-first-start` (`_settle_first_start`,
  `_settle_listed_priors`, `_settle_lower_date`, `_settle_every_history`). RS
  00301.230 makes annual placement flexible, and 404.321(a) gives a period one
  start. Where placement can move a start, a result stands only if one filling
  of the years that can move it keeps the start and attains the result. Other
  years stay flexible for each status. A record doesn't say which route began
  an unflagged prior, so that filling has to keep the prior on the strictest
  route some placement meets (round 21): 404.130(b), or 404.130(d) after a
  flagged prior, before past blindness, since 404.130(c) begins only a flagged
  prior. A listed prior's start reads as the favorable earliest insured quarter
  from an onset the record omits, so that onset adds no constraint on
  placement (round 22).
- `us:oasdi-insured-subsequent-special-long-period` (`_witness`,
  `_unknown_prior_joint_shortfall`). Act 223(c)(1)(B)(iii) asks for half the
  quarters after age 21 with no cap, and 404.130(d)(2) caps the test at 20 of
  40. `_witness` computes on the cap and refuses by name
  (`subsequent_special_long_period_unsupported`) where the uncapped count
  would insure, and the possibility proof takes the Act's reading. A third
  parse asks for half the whole period's quarters, at most 20 QCs, anywhere
  in the period, and the rule doesn't apply it. For a woman born 1960-02-02
  with a flagged prior from 1983-01-15 through 1983-06-30, QCs 1981:3,
  1982:3, four in each of 1984 to 1986, 1987:1 and 1993:1, and an onset
  1993-10-15, the Act asks 24 of the period's 48 counted quarters and finds
  20, the last 40 counted quarters hold 14 of 20, and only the third parse
  insures; DISABILITY computes false at that onset, and an established
  period raises `InvalidFamilyInput` (round 23). The refusal and this parse
  stand until Max rules the pattern in d1920.

## Round 13 joint classification audit

Sections 404.130(b)–(d) and (f) leave the recent floor intact when prior
history is UNKNOWN; paragraph (e) removes the recent requirement only for
blindness. RS .480 A separately requires twenty credits. The horizon
floor therefore runs after the stronger known-history numerical proof and
before UNKNOWN-prior, recent and alternate possibilities. Foreign credits
and routes adding credits outside the declared envelope still precede it.

The independent oracle found further instances of the same uncoupled
witness class. A prior period being possible does not show that any one
completion also insures the current period. With UNKNOWN priors, a new
necessary-condition proof permits historical blindness at the first
possible fully insured quarter, then deletes every later uncredited
quarter before the current candidate while retaining every QC, even
credits that a real freeze interior would remove. This clock is more
favorable than any real chain of prior periods. Restoring a QC adds at
most one elapsed quarter while adding one credit, so neither a half-clock
nor a 20/40 test becomes harder. All upper annual placements therefore
bound every lower filling. The proof also requires six credits before age
31 for any possible subsequent-special prior. It rejects only if every
relaxed placement fails. More than 4,096 placements leaves the history
unresolved. It does not construct a history or change the earlier
`_minimum_current_period_qcs` proof. This additional joint proof applies
to current onsets from 1956; earlier UNKNOWN current onsets keep the
existing conservative alternate/history machinery and are outside the
added UNKNOWN-history oracle lattice.

Round 23 retires the overlap cases in this paragraph and the next: a
period may begin in the quarter a prior ended, so no start overlaps a
prior. For known priors, 404.321(a) fixes onset when insured then,
otherwise the first insured quarter. The rule does not know when a fully-route flag's
status began. An overlapping quarter fixes the first start only when the
person is ordinarily insured there without any flag, for the same complete
annual filling and all-period treatment. A recent-only witness cannot
supply the missing fully insured prerequisite. The prior may supply that
prerequisite when used and fail to supply it when disregarded; persistence
under one treatment says nothing about the other. The flag can first hold
in a later clear quarter. Blindness removes the recent test under
404.130(e), but does not date the flag's fully insured status either.

When the initially favorable ordinary start overlaps a prior, construction
still searches at most 4,096 annual placements and both prior treatments.
Finding a clear first start proves possibility. It cannot settle the
elapsed-year freeze, FULLY, CURRENTLY, DISABILITY, and DLI for other lawful
fillings. Construction therefore retains
`disability_boundary_assignments_unsupported`, rather than selecting the
first success. Finding no clear start still proves an input error.
Possibility checks defer a construction refusal so that later input
validation remains first. This deliberately leaves some loose refusals:
keeping a possible lawful row and its weight is safer than rejecting it
without a proof that every filling fails. The historical alternate retains
its own eligible start candidates, continuous clock, and lower-credit
exclusion; no flag-specific substantive condition is adjudicated here.

| Invariant | Executed tests |
| --- | --- |
| Nonblind declared-envelope routes need six credits by the immutable horizon, including UNKNOWN prior history and every fully route; later credits cannot repair a shortfall. | `test_unknown_prior_fully_route_floor_uses_horizon_credits`; `test_twenty_future_credits_cannot_repair_zero_by_start_horizon`; `test_classification_oracle_hypothesis`; `test_classification_oracle_unknown_years_straddle_start_horizon` |
| Blind fully routes without prior overlap preserve their zero-credit named refusal; foreign and credit-adding routes precede the floor. | `test_blind_fully_route_with_zero_credits_keeps_named_refusal`; `test_foreign_and_credit_adding_routes_precede_floor`; `test_classification_oracle_modern_lattice` |
| One alternate start fits the horizon and the 1955 limit together, and may share the quarter a prior ended (round 23); credited endpoints and false/UNKNOWN establishment retain their treatment. | `test_an_alternate_start_can_share_the_quarter_a_prior_ended`; `test_alternate_uses_one_clear_candidate_after_prior_ending_quarter`; `test_unestablished_alternate_keeps_prior_treatment`; `test_classification_oracle_historical_boundary_lattice` |
| UNKNOWN priors cannot supply a special route without six credits before age 31, or couple incompatible earliest-prior and current windows. | `test_classification_oracle_unknown_prior_cannot_invent_special_eligibility`; `test_classification_oracle_unknown_prior_must_jointly_insure_current`; `test_classification_oracle_unknown_twenty_qcs_need_one_joint_start`; generated `test_classification_oracle_hypothesis` |
| Each known-prior filling and treatment has one first insured start. A start requiring a different placement or treatment keeps a named refusal, rather than settling statuses by iteration order, and a fully-route flag keeps an insured onset (round 23 renamed these tests). | `test_classification_oracle_fully_flag_keeps_an_insured_onset`; `test_classification_oracle_blind_fully_flag_still_has_one_first_start`; `test_classification_oracle_annual_placement_can_delay_first_insured_quarter`; `test_classification_oracle_annual_placement_boundary_lattice`; `test_disability_witness_counts_the_quarter_a_prior_ended` |
| Invalid declarations have zero rows and weight; each valid computed or named-refusal outcome has exactly one row and its full rational weight. | Every new regression and lattice evaluation; `test_classification_oracle_hypothesis` |

### Independent oracle and bounds

`tests/test_track_b_insured_status_classification_oracle.py` uses public
input/evaluator types and plain arithmetic. It calls no private rule
helper. Its modern lattice has 3,168 declarations. Together with the
historical and boundary lattices and 48 generated examples plus an explicit
example, it varies modern ages 24, 29, 42 and 60; historical births 1890, 1900 and 1910; onset and end quarters around 1952–1956;
recovery, continuity, death and exit bounds; none, one, two, special and
UNKNOWN priors; blindness; all four fully routes, the alternate and flag
pairs; credits 0, 5, 6, 19, 20 and 24 in old, recent and boundary placements;
and UNKNOWN credit years before and after the start horizon. Four focused
controls also cover adjacent age-31 quarters and 1952Q2/Q3 start horizons.

For every selected declaration it enumerates annual placements, every
UNKNOWN-year subset, start quarters, fixed all-use/all-disregard prior
treatments retaining credited endpoints, and UNKNOWN month endings through
query plus the FRA/death continuation cap. At most two observed annual
totals are partial and two years UNKNOWN; the largest selected placement
space is 192. UNKNOWN history includes every empty/one-period quarter
interval in its stated range, with exact endings before onset, plus a
bounded two-period class consisting of an independently fully insured
blind prefix, with or without a fully-route flag, ending immediately before
a subsequent special period. Gapped or arbitrary two-period histories are
not exhausted. The earlier flagged birth-to-before-first-QC blind prefix
followed by a later special interval is preserved as a separate gapped
representative class. A prior start must itself be insured. This
preserves the defensible historical-blindness completion even when current
blindness is false. The oracle does not exhaust arbitrary two-period or
three-or-more UNKNOWN histories, alternate-founded UNKNOWN prior starts,
raw earnings, credit-adding flags, foreign routes, administrative filing
facts or SSPA211. Negative UNKNOWN examples have separate impossibility
proofs that also exclude extra periods. A fully-route flag's first quarter
is free: every candidate start, one quarter before onset, and a quarter after the start horizon are considered.
UNKNOWN history also admits historical candidates and a before-birth
sentinel, with one common flag start for the entire history. The modern
288-base deterministic flag-relaxation property checks four flags per base
(1,152 implications) using the same cached public outcomes. Classification
is this oracle's tested principle; returned DLI and per-test diagnostic
assignment coherence are outside its claim. The separate status oracle
below checks returned Booleans, and the reversal properties check complete
public results including deterministic diagnostic witnesses.

### Executed counterexamples and corrected oracle assumptions

The original zero-credit UNKNOWN-prior finding and the prior ending in
1955Q4 both now raise input errors. The independent audit additionally
found a young no-flag six-credit prefix requiring seven current credits;
an over-31 fully-route case with no six credits before 31; a twenty-credit
record whose earliest prior and current 40-quarter windows cannot share
the oldest credit; fully-route first-onset overlaps, including blindness;
and a valid annual Q2 placement rejected by a greedy Q1 assignment. Each
has a named regression in the oracle file. Their exact invented dates,
credits, first failures and dispositions are retained in the round-13
report. These corrections change classification and denominator inclusion,
not a computed payment.

Round 13 corrected an oracle that permitted a later ordinary start after
an insured overlapping onset. Round 14 corrects the remaining flag premise:
a flag is not fully insured in every quarter. Its first fully insured
quarter is a free fact, shared by a complete history. The oracle also
admits a single no-flag blind prior and blind-then-special prefixes wherever
ordinary fully insured status permits their first start. Current
nonblindness cannot exclude past blindness. The separate status oracle
checks favorable returned Booleans rather than classification alone.

The round-11 four fully-route assertions for six credits first earned
after age 31 now require `InvalidFamilyInput`: those late credits cannot
supply the necessary special prior. The early six-credit control retains
its named refusal because an under-31 special prior remains possible.
These final assertions strengthen classification coverage; the earlier
claim that they were left unchanged was incorrect.

Mutation checks are recorded in
[`track_b_insured_status_mutations.json`](track_b_insured_status_mutations.json).
Every recorded implementation mutation was caught and reverted.


## Round 14 lawful fillings and returned statuses

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.

The 1951-born nonblind worker's six earlier QCs permit a blind prior from
1973-04-01 through 1975-12-31, followed by under-31 special insurance at the
1976 onset. The joint optimistic proof already permitted that history;
the later emptiness check now permits it too. The UNKNOWN-prior row and
weight 17/9 survive, including an explicit exit, a claiming-age query,
and the 1995 blind-then-special variant.

For the 1924-born worker, disregarding the 1979–1985 prior gives 20 recent
QCs in 1985Q1 but only 33 of 34 fully insured QCs. In Q2, 34 of 34 fully
insured QCs and the recent rule hold together. Thus the four fully-route
flags cannot reject a declaration that is ordinary-valid without them.
Each retains its own named refusal and weight 3/2. The no-flag control
computes FULLY true. This fixes a false rejection rather than choosing a
new reading of 404.321(a).

For the 1960-born worker, annual QCs 1990:1, 1995–1998:4 each, 1999:2,
2000:1, and 2002:1 admit 1990Q3, 1999Q1/Q2, 2000Q2, and 2002Q4. Favorable
prior disregard starts the current period in 2000Q2 and computes FULLY
20/20 at 2006-01-01; the previously selected 2002Q1 start computed 20/21.
The implementation now refuses that unresolved start for every requested
test, with one row and its full weight. Adding four QCs in each year
2003–2006 and querying at 2022-03-01 similarly exposes 36/36 versus 36/37.
No benefit amount is computed in either case.

Reversing annual boundary candidates also exposed equal-score diagnostic
witnesses selected by iteration order, with unchanged statuses. Boundary
options now use canonical tuple order so the complete public result remains
deterministic; no statutory amount or status calculation changes.

The invariants added in this round are executed by public example and
Hypothesis tests in `test_track_b_insured_status_fix_round_14.py` and the
independent status oracle: adding a fully-route flag preserves every row;
reversing annual-placement and prior-treatment iteration preserves public
results; admitting past blindness preserves UNKNOWN-history rows; every
computed status equals the most favorable lawful filling in the oracle's
bounded space. Existing six-QC, horizon, recovery, continuous-clock, and
FRA invariants remain in force; round 23 retired the impossible-overlap
one.

### Premise attacks and source readings

The pre-1913 male cohort attacks include a prior needed to recover old
20/40 QCs, and the blind-then-special attack independently computes six
recent QCs and a seven-of-six fully insured prerequisite. Both preserve
UNKNOWN-history rows. The disability elapsed-year rule in 404.132(b),
rather than the retirement calendar in 404.110(b), governs a prior that
must begin before FRA.

An attempted aggregate-funded blind prior was also executed and minimized.
Round 14 left it an input error, following RS 00301.315 B.1. Round 15
replaces that reading; the section below gives the sources.

Eleven isolated implementation mutations were caught, including all ten
requested rules and the additional canonical diagnostic tie rule. Exact
commands, failing test nodes, zero-open audit counts, and the final
implementation hash are retained in `track_b_insured_status_mutations.json`.

### Independent status oracle and bounds

`tests/test_track_b_insured_status_status_oracle.py` calls public types and
function entry points, with no rule helpers. It enumerates known annual
QC totals, no prior or one known prior, known ends, no flags, both medical
blindness states, and all-use/all-disregard treatment. Each fixed filling
finds its first insured start before building the period and independently
computing FULLY, CURRENTLY, and DISABILITY. Computed public Booleans must
match the componentwise most favorable answer over lawful fillings; a
named refusal preserves a row. Query cases include dates well after the
period ends and a claiming-age query. At most 576 placements, two
establishment treatments and two status treatments are considered per declaration. The 36 deterministic lattice
cases, the reviewer case, and 24 generated examples plus the explicit
reviewer example cover women born 1960-02-02. The executable module header
gives the remaining finite bounds.
DLI, raw earnings, UNKNOWN earnings/ends, foreign routes, and specialist
flags are outside this oracle's claim.

## Round 15 the aggregate and each filling's own start

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.
Session checks found both defects after round 14, before the next review.

### The pre-1951 aggregate on disability routes

Act 223(c)(1)(A) and Act 216(i)(3)(A) each ask whether "he would have been
a fully insured individual" under section 214. Act 213(c) applies "For
purposes of sections 414(a) and 415(d)". Section 404.132 says "we use the
fully insured status requirements in § 404.110, but apply the following
rules in determining when the period of elapsed years ends", and 404.110(d)
is one of those requirements. RS 00301.315 B.1 alone says, "The simplified
method does not apply to disability claims." The statute and the regulation
therefore reach the disability prerequisite (P1, P2). Filing facts stay
unmodeled, so the rule credits no deemed quarter. It refuses by name where
an aggregate of declared raw wages or of an UNKNOWN year could decide an
answer (pre-1951 years declared as QC flags add nothing to it; round 23),
and it never rejects such a
declaration or answers it false. A row that a defensible reading keeps
stays a row. Source conflict
`us:oasdi-insured-simplified-pre1951-disability-scope`.

The executed record is an invented woman born 1926-02-02 with $2,400 in the
first quarter of each of 1948, 1949 and 1950, 22 later QCs and onset on
1989-01-15. She has 25 ordinary QCs, or 40 with the aggregate, against 37
required. At round 14, FULLY refused by name, DISABILITY computed false, and
an established period raised `InvalidFamilyInput`. All three now retain the
row with `simplified_pre1951_unsupported`. The boundary is exact: $6,000 in
total gives 15 + 22 = 37 and refuses, and $5,997 gives 14 + 22 = 36 and
computes false. The aggregate also reaches a first start that an ordinary
credit would otherwise date later, and a date last insured that ordinary
fully insured status would otherwise end sooner. Blindness removes the
recent rule here as elsewhere. Simplified credits never count toward the
recent rule, because 404.110(d) applies "For purposes of paragraph (b) of
this section". A true ordinary status stays computed.

An UNKNOWN-history declaration whose only fully insured route for a prior
is the aggregate now keeps its row under
`unknown_prior_disability_periods_decide_status`. The automatic aggregate
acts as a fully-route condition in the establishment proofs, so its
six-QC floor and recent-rule scan match the declared flag.

### One filling carries its own start

Each status places annual QCs favorably for its own window, and the
established start does the same (RS 00301.230). Round 14 stopped those
placements from mixing only where the favorable start overlapped a prior.
Random invented declarations found the same mix without overlap, and with
no prior at all. A woman born 1956-02-02 has annual QCs 1987:2, 1988:4,
1989:3, 1990:4, 1991:4, 1992:2 and 1994:1, onset 1992-01-15, and a period
ending 1994-09-30. The 1994 QC must sit in the first insured quarter, so at
most two later quarters leave the 13-quarter window and CURRENTLY finds at
most five of the six QCs at 1995-01-01 in every lawful filling. The rule
took its start from 1994Q1, moved the same QC to 1994Q4 for CURRENTLY, and
answered true.

404.321(a) gives one record one start, and that period's exclusions then
shape FULLY, CURRENTLY and the date last insured. Where annual placement or
prior treatment can move the start, the returned result stands only if one
filling attains it with the reported start as its own, and no filling can
improve on it.
`_settle_first_start` checks the second condition first. Flexible credits
bound every filling at each possible start, so a bound that allows a better
status or a later date last insured refuses the row with
`disability_boundary_assignments_unsupported`. It then looks for an
attaining filling, starting from the filling that insures the reported
start and varying the latest years first, because those years conflict
with the later windows. Round 15 stopped at the first attaining filling, and
round 16 searches on for each status's count. A year
that can't move the start stays flexible, so each status still places it
favorably. The check joins each status to the start, not the statuses to one
another. This keeps the favorable answer of RS 00301.230 and replaces an
answer no single record supports.

A status window can also end before the onset. `_events` tests CURRENTLY at
a declared RIB or DIB entitlement month, so a year at the back edge of a
recent-rule window can want its QC early for the status and late for the
start. An invented woman born 1960-02-02 has annual QCs 1990:4, 1991:4,
1998:3, 1999:2, 2000:1, four in each of 2001 to 2004, and 2005:3, onset
2010-01-15 and a DIB entitlement month of 2000-01. The 2000 QC reaches the
20 of 40 at the onset only in 2000Q2 or later, and it reaches six of 13 at
the entitlement month only in 2000Q1. No filling holds both, so the row
refuses, and the same record without the entitlement month computes false.
`_start_sensitive_years` keeps the 40-quarter and 12-quarter back edges, the
age-21 edge and prior-period years enumerated for this reason. A filling
whose own start falls later can also hold the status, and it doesn't count:
the search requires the reported start. `ENTITLEMENT_CONFLICTS` in
`tests/test_track_b_insured_status_fix_round_15.py` pins one declaration for
each of those lines.

The bound refuses without enumerating, so it can refuse a declaration that
no concrete filling improves. That direction is deliberate: the row keeps
its weight under a named refusal, and proving every filling false would
cost far more than the row gives back. Bound B17 records the limit.

### Status stress oracle and bounds

`tests/test_track_b_insured_status_status_stress.py` widens the status
oracle with the same plain arithmetic. Births run from 1940 to 1979, and
ages at onset from 31 to 58. Onsets start in 1992. Endings, queries,
annual totals with at most four partial years, and no prior, a clear prior
or an overlapping prior vary by seed, and blindness holds in a quarter of
cases. The session ran 28,000 such declarations at round 14's head. It
found 13 status disagreements and no false rejection, and each of the 13
had more than one possible first start. The committed test pins all 13
seeds and generates more. Two more generators add a DIB entitlement month,
drawn mostly from partial years up to the onset, and ages 22 to 30 at onset
under 404.130(c) and (d). UNKNOWN facts and flags stay outside its claim,
and round 16 adds the date last insured and the subsequent-special route.
Round 19 holds a declared prior's own start (`prior_holds`).

After the fix, the same 28,000 and 14,000 fresh declarations give no
disagreement, no false rejection and no computed row without a lawful
filling. On the 28,000, rows refused by name that have a lawful filling
rise from 435 to 562. Thirteen of the 127 are the disagreements. The other
114 computed agreeing answers at round 14, and they are the cost of the
loose bound: about 1% of computed rows, in a space drawn to hold partial
years. Rejected rows stay at 15,785.

Five surviving mutations then showed the generator had never drawn an
entitlement month or an under-31 row. The session widened the oracle with
both, and it added a stricter check: each true status must hold on a filling
whose own first start is the reported start. Across 14,000 declarations with
a DIB entitlement month and 14,000 under-31 declarations, 18,754 rows computed
and agreed, 349 refused by name with a lawful filling, and 8,894 raised
`InvalidFamilyInput` with no lawful filling. Nothing disagreed, and no status
lacked its start. One row the oracle called lawful raised
`InvalidFamilyInput`. It ends a period in December 1980, the month of its
onset, so 404.321(b)'s implied recovery precedes the onset on every filling.
The oracle doesn't model that rule, and the committed generator starts
onsets in 1981.

The invariants added in this round are executed by these tests:

- every computed status equals the favorable Boolean over lawful fillings,
  each carried through its own start
  (`test_status_stress_matches_the_favorable_filling`,
  `test_status_stress_with_an_entitlement_month`,
  `test_status_stress_under_31`, and the status oracle's declarations);
- a reported start is the start of a filling that attains the result, and
  each true status holds on a filling with that start (the same three
  properties, `test_status_stress_refuses_a_start_no_filling_supports`,
  `test_a_moving_start_keeps_a_result_one_filling_attains`,
  `test_an_entitlement_window_cannot_borrow_the_starts_placement`);
- raw pre-1951 wages never turn a row into an input error
  (`test_pre1951_wages_only_add_rows`);
- a refused FULLY and a met recent rule never compute DISABILITY false
  (`test_fully_refusal_and_a_met_recent_rule_never_compute_false`);
- the DISABILITY refusal tracks the exact aggregate
  (`test_disability_refusal_tracks_the_exact_aggregate`).

## Round 16 diagnostics on the reported start

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.
Sol's eleventh review of `c28bb1dd` raised two mediums, and both reproduced.

### Exact diagnostics rest on the reported start

Round 15 joined each status's Boolean to the reported start. Its count and
assignment kept the status's own favorable placement, so an exact diagnostic
could describe a filling that 404.321(a) excludes. An invented woman born
1962-02-02 has annual QCs 1998:4, 1999:2, 2000:1, four in each of 2001 to
2004 and 2005:3, onset 2010-01-15, a period ending 2010-12-31 and a DIB
entitlement month of 2000-01. The 2000 QC reaches 20 of 40 at the onset only
in 2000Q2 or later, so every lawful filling finds six of 13 at the entitlement
month. At `c28bb1dd` CURRENTLY reported seven, and both its assignment and
the top-level `assigned_quarters` put that QC in 2000Q1. The status stayed
true, and the count and quarter were wrong. The review's record adds a prior
period and earlier work, with the same result.

`_settle_first_start` now takes each status's witness for each period ending.
It searches past the first attaining filling until every witness recurs with
the reported start or the placements run out. It then returns the filling
that attained the result and each status's best witness among the fillings
that keep the reported start. `_witness_rank` orders them as `_witness`
scores them, by status, then margin over the requirement, then count. Every
ending must still agree once its witness keeps the reported start, and a
status only a moved placement met keeps its
`disability_boundary_assignments_unsupported` refusal. The top-level
`assigned_quarters` and `qcs_by_year` describe the returned filling. Where
the same record has no moving start, `_start_fixed` holds and each status
keeps its own favorable placement. So does an UNKNOWN year or prior, whose
envelope states an outer bound rather than a filling. This changes no reading. It carries the logged reading
`us:oasdi-insured-one-filling-first-start` from the Boolean to the fields
that report it.

Three records pin the edges. With nineteen QCs through 1999, one 2000 QC, an
onset of 1999-06-15 and a query of 2003-04-01, a declared ending in 2000Q2 or
later meets CURRENTLY at the reported start with the 2000 QC in 2000Q1. An
ending in 2000Q1 needs that QC in a later quarter, so it refuses. An UNKNOWN
ending includes that one, so it refuses too, although its other endings
agree. With 19 QCs from 2001 through 2005, the latest date last insured needs
the 2000 QC in 2000Q2 or later and the row refuses. With 20, the date doesn't
need that QC, and it computes 2010-12-31.

The returned filling is one lawful filling, not a proof that it credits the
most quarters. The search tries the start's witness first and then the
quarters `_world` credits in the excluded context, so a year keeps its
credits where it can. A disregard-periods witness can still hold a year's QCs
inside a prior, and the year count then falls below what another filling with
the same start gives. This limit touches only that diagnostic: no status,
count, start or date depends on it, and no module reads `qcs_by_year` or the
top-level `assigned_quarters`. An exact row keeps
`qcs_by_year[y] == (len(assigned_quarters[y]),) * 2`.

Sol's record moves a count, and the random generators rarely reach one. On
1,200 stress declarations, `c28bb1dd` and this head agree on every outcome
class, status, count, start and date, and 67 rows change only where their QCs
sit. The exhaustive placements in
`test_a_computed_count_is_the_best_lawful_count` check the rule's count against
plain arithmetic for the no-prior record, and each stress generator now checks
counts on every computed row.

### The aggregate below six ordinary QCs

`_last_insured` returned no date last insured below six ordinary QCs, on the
premise that every route needs them. A blind person's fully insured route
doesn't: blindness removes the recent rule, and Act 213(c)'s aggregate can
supply the fully insured quarters. An invented blind woman born 1926-02-02 has $8,800 in
single quarters across 1948 to 1950 and three ordinary QCs. Her 22 aggregate
credits match the 22 of 1973, so at 1974-01-01 the aggregate could date her
last insured quarter, while `c28bb1dd` reported none. The row now refuses
with `simplified_pre1951_unsupported`, with or without an exit. The same
holds for 52 quarters of $49, which earn no ordinary QC. The shortcut still
answers every nonblind record, because each nonblind route needs six ordinary
QCs in its own window. A blind record with no wages reaches the scan and finds
no date.

`test_blind_aggregate_decides_below_six_ordinary_qcs` in round 15 asserted
that $8,700, or 21 credits, computed false. Those credits meet 1972's 21 for a
historical date, so that row now refuses, and $2,397, or five credits, takes
its place as the row that computes.

### Oracle reach and bounds

The status oracle and stress generators drew neither the date last insured nor
the subsequent-special route, and they checked no count. Both claims now
execute. `favorable_statuses` and `lawful_fillings` return each lawful
filling's own first start, and `_check_diagnostics` and `check_diagnostics`
hold every computed count and date to the best filling with the reported
start. `subsequent_declaration` draws a special prior from ages 24 to 30 and
an onset from ages 32 to 40, so 404.130(d) now runs alongside 404.130(c).
The session drew 4,800 fresh declarations across the four generators at the
final source. Of these, 3,131 computed and agreed on status, count and date, 62
refused by name, 1,607 raised `InvalidFamilyInput` with no lawful filling, and
nothing disagreed.

Ten mutations survived a first pass, and execution settled each one. Eight
were test gaps, and named tests now kill them. The first fix returned the first
attaining filling, and a differential against `c28bb1dd` found that it lowered
the year count in 62 of 712 computed rows. The `favored` tie-break brings
that to 8. Reversing every candidate list changes no output on those
declarations. Without the sort's last key, the same reversal changes 72.
`unknown_current_treated_as_exact` showed that an UNKNOWN current period can't
reach `_settle_first_start`, because its start stays `None`, so that condition
left the code. `rank_ignores_status` is equivalent: the search ranks only
FULLY and CURRENTLY witnesses, whose `insured` is exactly `count >= required`,
and all 9,892 witnesses ranked in a stress run agree. All 23 mutations in the
ledger ran against the final source, with 22 killed and that one equivalent.

The longer search can reach the 4,096 limit where the first attaining
filling once stopped it. Such a row refuses by name and keeps its weight, as
B17 records.

The invariants added in this round are executed by these tests:

- a computed count and assignment rest on a filling with the reported start
  (`test_count_and_assignment_keep_the_reported_start`,
  `test_every_exact_diagnostic_rests_on_one_filling`,
  `test_a_computed_count_is_the_best_lawful_count`, and both oracles);
- a fixed start and an UNKNOWN envelope keep the favorable count
  (`test_a_fixed_start_keeps_the_favorable_count`,
  `test_unknown_years_keep_the_universal_envelope`,
  `test_an_unknown_ending_keeps_each_endings_witness`);
- the year counts match the returned filling
  (`test_status_stress_year_counts_follow_the_returned_filling`,
  `check_diagnostics`), and that filling keeps credited endpoints
  (`test_status_stress_returned_filling_keeps_credited_endpoints`);
- each ending must hold at the reported start, and so must the date last
  insured (`test_an_ending_the_reported_start_fails_refuses`,
  `test_a_later_ending_meets_currently_at_the_reported_start`,
  `test_a_date_only_a_moved_placement_reaches_refuses`,
  `test_a_date_the_reported_start_reaches_computes`);
- a date last insured below six ordinary QCs refuses exactly where the
  aggregate reaches six or more (`test_the_dli_refusal_tracks_six_aggregate_qcs`,
  `test_aggregate_below_six_ordinary_qcs_refuses_the_dli`,
  `test_aggregate_with_no_ordinary_qc_refuses_the_dli`).

## Round 17 the long subsequent-special period and the lower date

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.
Sol's twelfth review of `e9f4140c` raised two mediums, and both reproduced.

### The cap on a long subsequent-special period

Clause (iii) of Act 223(c)(1)(B) and 216(i)(3)(B) asks for "not less than
one-half of the quarters beginning after such individual attained age 21",
with no cap. 404.130(d)(2) asks for one-half of the same period "up to a
maximum of 20 QCs out of 40 calendar quarters", and RS 00301.147 B.2.a repeats
those words. RS 00301.147's three examples stop at 33 quarters, so no capture
shows SSA applying the cap. Past 40 counted quarters the sources give two
readings:

- half the whole period, as the Act says;
- 20 of the 40 counted quarters ending with the tested one. 404.130(d)(2)
  says "out of 40 calendar quarters" without saying which; every period in
  404.130 ends with the tested quarter, and those are the quarters of
  404.130(b), so this reading adds nothing to that rule.

A third parse takes 20 QCs anywhere in the period. The session rejected it
on arguable grounds, and round 23 lists it in the register for Max. It
drops "out of 40 calendar quarters", the denominator 404.130(d)(2) states, and
every period in 404.130 ends with the tested quarter, so the test would stop
asking about recent work. RS 00301.147 doesn't decide this parse. It prints
Mary Brown's result at the November 1982 onset and no date last insured. This
rule derives her 1983-03-31 date: counting the prior's quarters under
404.130(f) leaves 20 QCs in 48 quarters at 1983Q2, and that parse alone would
move the derived date past 1983-03-31.

Through round 16 the rule took the capped reading without logging it, and the
stress oracle repeated it. An invented woman born 1960-02-02 has a special
prior from 1983-01-15 through 1983-06-30, annual QCs 1981:3, 1982:3, four in
each of 1984 to 1986 and 1987:2, and onset 1991-10-15. The period holds 41
counted quarters, so the test needs 20, and all 20 QCs sit in it. Its last 40
quarters hold 19. At `e9f4140c` DISABILITY computed false with a date last
insured of 1991-09-30, where the Act's reading insures this record through
1991-12-31.
With an established period the same record raised `InvalidFamilyInput`, even
for an age-62 FULLY request.

The rule now computes only where the two readings agree. `_witness` refuses
with `subsequent_special_long_period_unsupported` when no candidate insures and
the whole period holds at least half its quarters after dropping an odd
remainder. The refusal needs no fully insured test: half a long period's
counted quarters is at least the 404.132 requirement over births, priors and
query dates, which `test_half_a_long_period_clears_the_fully_insured_count`
holds. At 40 counted quarters or fewer the readings match. A FULLY
request with no established period reads no disability test, so it still
computes. The refusal reaches a date last insured that the 40-quarter rule
ends before the Act's reading would, because the date scan calls the same
witness. It also reaches
the period that 404.130(f) counts in full, where the prior's quarters take a
period past 40. `_unknown_prior_joint_shortfall` proves impossibility, so its
`special_recent` takes the Act's whole period, and its own 40-quarter test
carries the capped reading. The last-40 form raised an input error on a record
with fixed QCs from 1965, where the proof's clock holds 21 QCs in 42 quarters
and only 19 in the last 40. `_minimum_current_period_qcs` already took 20 as a
ceiling. The session logged this as
`us:oasdi-insured-subsequent-special-long-period`. It is a statute against a
regulation, which is the pattern in d1920, so the refusal stands until Max
rules that pattern.

### The lower date on an unknown ending

Round 16 held the upper date to a filling with the reported start, and left
the lower date as each ending's favorable placement. An invented woman born
1960-02-02 has annual QCs 1995:3, four in each of 1996 to 1999, 2000:1, four
in each of 2001 to 2004 and 2005:3, an established period from 2000-01-01 and
an UNKNOWN ending. Of 64 placements, 16 keep the 2000Q1 start, and each puts
the 2000 QC in that quarter. An ending of 2005-12-31 then leaves those
placements a best date of 2009-12-31. At `e9f4140c` DISABILITY reported a lower
date of 2010-03-31, which needs that QC after 2000Q1 and so a later start. A
frozen OP12 exit overstates its lower date the same way.

`_settle_lower_date` now searches fillings that keep the reported start, and
refuses by name unless each ending reaches the lower date. It runs on the
lower credits, because a lower date comes from those credits, so an UNKNOWN
year reaches the same check. UNKNOWN priors reach it too, and round 19 holds
them to every placement with no period in force.
`_fillings_keeping_start` holds the search that `_settle_first_start` already
ran.

### Oracle reach and bounds

`test_computed_exactly_when_every_reading_agrees` writes the two readings out
from the source text, with no production helper, and requires a computed
result exactly where they agree on the status and the date. The stress
oracle's `under_31` now takes a reading, and `check` holds a computed result
to both on every subsequent-special declaration. The classification oracle
treats a filling as lawful if either reading insures it.
`test_poms_mary_brown_keeps_a_computed_date_last_insured` and
`test_twenty_qcs_short_of_half_the_period_compute` hold the rejected parse out
of the rule. A new
`check_unknown_ending` exhausts each ending's fillings on the reported start,
and requires the upper date to equal the best of them and the lower date not
to exceed the worst.

A probe drew 4,500 stress declarations with an UNKNOWN ending, each with known
and UNKNOWN priors, and they ran the search 1,440 times. One record needs a
different filling for each ending, and
`test_a_record_can_need_a_different_filling_for_each_ending` pins it. No search
reached an ending with no date, so
`test_an_ending_with_no_date_reaches_nothing` runs on written-out dates.

A wide search drew 5,100 invented declarations from fresh seeds across the four
stress generators and both unknown-ending checks, and every check held: 3,014
computed, 1,903 raised `InvalidFamilyInput`, and 183 refused by name.

All 22 mutations of this round die at the final source bytes
(`round_17_mutations` in `docs/design/track_b_insured_status_mutations.json`),
and they ran against every insured status module. They include the three that
survived Sol's twelfth review: `count_upper_uses_minimum`,
`fully_count_lower_uses_maximum` and `omit_last_witness_for_ending`. Two early
mutations, `long_ignores_fully` and `long_drops_ignore_flag`, proved equivalent
across the 166,080 combinations above, so the clause they changed left the
source and they left the list. Against `e9f4140c`, 38 of the 261 tests in the
three changed modules fail.

These tests execute the invariants this round adds:

- a long subsequent-special period computes exactly where both readings
  agree, and otherwise refuses by name with its row and weight
  (`test_computed_exactly_when_every_reading_agrees`,
  `test_a_long_period_refuses_where_its_readings_differ`,
  `test_a_later_date_last_insured_can_turn_on_a_reading`,
  `test_counting_the_prior_quarters_reaches_the_same_refusal`, and both
  oracles);
- no reading's conflict becomes an input error
  (`test_an_established_period_keeps_its_row`,
  `test_an_age_62_fully_request_keeps_its_row`,
  `test_unknown_prior_history_keeps_its_row_on_the_whole_period`,
  `test_classification_oracle_subsequent_long_period`);
- every period ending reaches the reported lower date on a filling with the
  reported start (`test_every_ending_must_reach_the_lower_date`,
  `test_a_frozen_exit_reaches_the_same_check`,
  `test_unknown_years_reach_the_same_check`,
  `test_unknown_prior_history_reaches_the_same_check`,
  `test_each_ending_can_reach_the_date_on_its_own_filling`,
  `test_a_record_can_need_a_different_filling_for_each_ending`,
  `test_an_ending_with_no_date_reaches_nothing`, `check_unknown_ending`);
- a fixed start needs no placement search
  (`test_a_fixed_start_needs_no_placement_search`).

## Round 18 the current freeze under UNKNOWN priors

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.
Sol's thirteenth review of `88a0e7bc` raised one medium and one low, and both
reproduced. The session's search for the same defect then found it in the
status search.

### The lower date on every prior history

A declaration with UNKNOWN priors lists no period, and it stands for every
prior history. 404.130(f) and RS 00301.120 count all periods or disregard all
of them. `_settle_lower_date` read the current period back into its search, so
a filling could reach the lower date through the current freeze. Counting an
added prior can take a credited interior quarter from that filling, and
disregarding the added prior drops the freeze too.

An invented woman born 1960-02-02 has annual QCs 1995:3, four in each of 1996
to 1999, 2000:1, four in each of 2001 to 2004 and 2005:3, an established period
from 2000-01-01 through 2007-12-31, and UNKNOWN priors. For a January 2010
query, `88a0e7bc` reported a date last insured of 2010-03-31 as the lower date.
A prior from 1999-04-01 through 1999-12-31 fits this record, because 17 QCs at
1999Q2 meet the fully insured test that historical blindness needs. Of 64
placements, 16 keep the 2000Q1 start, and each puts the 2000 QC in that
quarter. Counting both periods leaves 19 QCs. Disregarding both leaves 19 in
the 40 quarters through 2010Q1 and 20 through 2009Q4, so that history's exact
date is 2009-12-31. A known ending, an UNKNOWN ending, UNKNOWN 2007 credits and
a frozen OP12 exit all reported a date past it.

`_fillings_keeping_start` gave each filling the record with no period in force
under UNKNOWN priors, and `_settle_lower_date` needed one such filling to keep
the start and reach the date. This round claimed that filling spoke for every
history. Sol's fourteenth review refuted the claim, because a period's own start
can rule that filling out, and round 19 replaced this check with every
placement. Where no filling reached the date, the row refused with
`disability_boundary_assignments_unsupported` and kept its weight. Lowering the
date instead would also be safe, and the session kept round 17's refusal.
The lower date itself needed no change: UNKNOWN priors already left it as the
date with no period in force, as B9 states.

### The same search reached the statuses

U3 lets a status under UNKNOWN priors stand on the all-period disregard.
`_settle_first_start` read the same search, so a filling with the reported
start could attain the status through the freeze. An invented woman born
1970-02-02 has annual QCs 1986:4, 1987:4, 1992:1, four in each of 1996 to 1999,
2000:1, 2001:4 and 2002:1, an established period from 2000-01-01 through
2002-12-31, and UNKNOWN priors. The 2000Q1 start needs the 2000 QC in that
quarter under the half-the-quarters test, and then the 13 quarters through
2003Q2 hold five QCs. For an April 2003 query, `88a0e7bc` reported CURRENTLY
true, because the freeze reaches QCs before 2000. A prior from 1996-01-01
through 1999-12-31 takes all but its endpoint QCs, and no filling with the
2000Q1 start stays currently insured on that history. The shared change covered
this record: a filling attained a status with no period in force, or the row
refused by name, and round 19 asks that of every placement. An OBSERVED empty
history keeps the freeze, and both the status and the date compute there.

### The Mary Brown capture

Round 17 leaned on RS 00301.147's Mary Brown to reject a third parse of the
long subsequent-special period. The capture prints her November 1982 onset
result and no date last insured, so the 1983-03-31 date is this rule's own
derivation and can't support the rejection. The text does: 404.130(d)(2) states
a denominator, "out of 40 calendar quarters", and the third parse drops it. The
round 17 section, its test comment and the logged row now say so, and the
ruling stands.

### Oracle reach and bounds

`check_every_history` adds three lawful priors to each record, exhausts the
placements with the reported start on each history and ending, and requires one
of them to hold each true status and reach the lower date. It imports no
production helper, and it requires a prior to begin fully insured.
`start_edge_declaration` redraws the tail of the two records above, so the
search runs near their boundary, and the oracle takes DISABILITY, CURRENTLY and
ALL requests, because an ALL request can refuse on another status first.
`test_status_stress_every_history_at_the_start_edge` fails at `88a0e7bc`. Its
first version drew records too far from that boundary and passed there, so
the generator changed. `test_status_stress_every_history` also passes at
`88a0e7bc`, so it stands only as a broad guard.
`test_status_stress_the_exact_date_on_that_history` and
`test_status_stress_the_status_on_that_history` hold both invented histories on
exhaustive placements.

The wide search drew 550 invented declarations from fresh seeds, 400 from
`start_edge_declaration` and 150 from `declaration`, and ran each on both
ending kinds and three requests. All 3,300 checks held: 1,454 computed, 1,498
refused by name, 318 raised `InvalidFamilyInput`, and 30 reported no start.

All 11 mutations of this round die at the final source and test bytes
(`round_18_mutations` in `docs/design/track_b_insured_status_mutations.json`)
with no restricted open, and each ran through the insured status modules until
its first failure. `freeze_carries_unknown_priors` restores the search at
`88a0e7bc`, and `status_search_keeps_the_freeze` and
`date_search_keeps_the_freeze` restore it in one settlement function each.
Against `88a0e7bc`, 13 of the 85 tests in the three changed modules fail.

These tests execute the invariants this round adds:

- under UNKNOWN priors, a computed status or lower date holds on every lawful
  prior history with the reported start
  (`check_every_history` and its stress tests);
- a result resting on the freeze refuses by name and keeps its weight
  (`test_the_freeze_cannot_carry_a_lower_date`,
  `test_a_frozen_exit_cannot_carry_it_either`,
  `test_a_status_resting_on_the_freeze_refuses`);
- round 19 holds a result to every placement, so a date on one filling refuses
  on each ending (`test_a_date_on_one_filling_refuses`,
  `test_every_ending_refuses_that_date`);
- a status on every placement computes
  (`test_a_status_on_every_placement_computes`);
- a known history keeps the freeze (`test_a_known_history_keeps_the_freeze`,
  `test_a_known_history_keeps_the_status`);
- a fixed start needs no placement search
  (`test_a_fixed_start_needs_no_search_on_unknown_priors`).

## Round 19 a period's own start limits the placements

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.
Sol's fourteenth review of `129d44bd` raised one medium, and it reproduced. The
session then found the same defect on listed priors and under UNKNOWN
establishment. Its first fix for listed priors refused a printed POMS record,
so that fix changed before this round closed.

### One filling doesn't speak for every history

A period begins in an insured quarter (404.320(b)(2), 404.321(a)), so a prior
can force an annual QC into one quarter. Disregarding a
period removes its exclusions, and its start still has to stand on the
placement. Round 18 asked for one filling with no period in force, and a
history can rule that filling out.

An invented person born 1961-02-02 has annual QCs 1991:2, four in each of 1992
to 1994, 1998:1, four in each of 1999 to 2002 and 2003:3, an established period
from 2000-01-01 through 2000-12-31, and UNKNOWN priors. For a January 2008
query, `129d44bd` reported a lower date of 2008-03-31. A prior from 1998-01-01
through 1999-12-31 fits this record: past blindness asks for 15 QCs at 1998Q1,
14 precede 1998, and so the 1998 QC falls in that quarter. All 24 of the 96
placements that keep the prior leave 19 QCs in the 40 quarters through 2008Q1
with no period in force, and 15 with both periods, so that history's exact date
is 2007-12-31.

An invented person born 1965-02-02 has annual QCs 1986:4, 1987:1, 1990:1,
1995:3, four in each of 1996 to 1999, 2000:1, 2001:4 and 2002:1, an established
period from 2000-01-01 through 2002-12-31, and UNKNOWN priors. For an April 2003
query, `129d44bd` reported CURRENTLY true. A prior from 1990-01-01 through
1999-12-31 asks for six QCs at 1990Q1 and finds five before 1990, so it holds
the 1990 QC there. A 2000Q1 start then holds the 2000 QC there too, and each of
the 64 of 1,024 placements that keep both leaves fewer than six QCs in the 13
quarters through 2003Q2.

### Every placement carries a result

`_every_placement_passes` answers for all placements at one quarter. With no
period in force every window ends at the tested quarter, so placing annual QCs
as early as possible before that quarter's year and as late as possible in it
costs the most from every window at once. That worst filling is itself a
filling, so the answer is exact, and
`test_the_worst_filling_matches_every_placement` holds it to exhaustive
placements.

Disregarding all periods stays open on any placement (404.130(f), RS 00301.120).
A result that every placement attains with no period in force therefore holds
on every completion, and it needs no search of histories. Under UNKNOWN priors
or UNKNOWN establishment, `_settle_every_history` asks that of each true status
at the quarter it reports and of the lower date. Anything less refuses with
`disability_boundary_assignments_unsupported` and keeps its weight. This
replaces round 18's check.

`_start_fixed` applies the same test to the start under UNKNOWN priors. A start
some placement moves reports `None` and names `current_disability_period_start`
in `unknown_facts`. DISABILITY reports its first favorable quarter, so it
refuses where that quarter fails on some placement, even when a later quarter
holds on all of them (`test_a_status_stands_at_the_quarter_it_reports`).

This over-refuses a record no lawful history can move. The session accepted
that cost, because a refusal keeps the row and its weight, and Sol's fix text
asks for the refusal until a universal proof exists. Every placement is that
proof, and it asks more than a tighter search of histories would.

### UNKNOWN establishment

UNKNOWN establishment stands for a period no one has placed, so it raises the
same question with no prior at all. An invented person born 1965-02-02 has
annual QCs of four in each of 1990 to 1994, 2000:1, 2001:4 and 2002:1, an onset
of 2000-01-01, and UNKNOWN establishment. `129d44bd` reported CURRENTLY true
for an April 2003 query. Only the 2000 QC in 2000Q1 reaches 20 of 40 in any
quarter through 2003Q2, so a period needs that placement. On it, a period
through 2003-03-31 leaves five QCs in the 13 quarters with no period in force
and one with it.

`_settle_every_history` covers this case, and it reads no listed period, because
the period no one has placed joins any listed prior in a count. A listed prior
alone therefore can't carry such a result
(`test_unknown_establishment_needs_the_disregard`).

### Listed priors

The two records above computed the same wrong results at `129d44bd` with the
prior listed OBSERVED. A listed prior differs from an unknown one in one way:
the record names it, so the search can hold it.

`_prior_start_binds` asks whether placement decides a prior's own start. A prior
that holds on every placement leaves them all open. A flagged prior's holder
"were only insured under paragraph (c)" (404.130(d)(1)), so that holder passes
a special route and not 404.130(b). A prior that every placement carries past
404.130(b) therefore holds on none. At this round the predicate read every
unflagged prior as resting on past blindness, and it let a prior that holds on
none pass. Round 21 replaces both: `_prior_basis` holds an unflagged prior on
404.130(b), or 404.130(d) after a flagged prior, wherever a placement meets
them (round 22 took 404.130(c) out), and a prior no placement supports refuses
by name.

Otherwise the prior picks among placements, and the logged first-start reading
applies to its start: one filling of the years that can move that start must
keep it and attain the result, and other years stay flexible for each status.
`_keeps_priors` tests one filling. `_settle_listed_priors` searches when no
current period exists, and `_fillings_keeping_start` holds the same priors when
one does. The result then comes from the best witnesses those fillings allow,
and DISABILITY joins that search, reading the person without the period's own
exclusion. For the 1965-born record with a second 2002 QC, the prior holds the
1990 QC in 1990Q1, and DISABILITY reports 20 QCs where `129d44bd` reported 21.

The first version of this fix refused whenever placement split a prior. That
refused the record of POMS example 8
(`test_subsequent_under31_poms_140_examples_7_and_8`), whose result rests on
1993 to 1996 and holds on the placement its prior needs. The search computes it
and reports the 1988 QC in 1988Q1 (`test_a_prior_holds_a_qc_in_its_first_quarter`).

Three limits remain, and each refuses by name. An UNKNOWN year with a prior that
picks among placements refuses, because lower and upper credits then bound
different placements. A filling must attain every reported status and the date
together, so a result resting on two placements refuses even where each status
alone could stand. The search stops at 4,096 placements. UNKNOWN establishment
skips the search, because a result that passes every placement can't move on
a subset of them (`test_unknown_establishment_leaves_a_split_prior_to_the_proof`).

### Oracle reach and bounds

`check_every_history` now adds a January and a July prior in each partial year
before the onset, reads every start where the start stays open, and holds a
filling only where each added prior can begin on it. `prior_edge_declaration`
redraws the two records above near their boundary, and
`test_status_stress_every_open_period` does the same under UNKNOWN establishment.
`check` holds a declared prior through `fillings_keeping_priors`, and each prior
now counts the periods before it or disregards them.

`check_no_period` is new. It exhausts the placements of a record with no current
period, and requires each status, each exact count and the date last insured to
equal the best the declared priors allow, on both readings of a flagged prior.
`listed_prior_declaration`, `two_prior_declaration` and
`special_prior_declaration` feed it. The oracle imports no production helper,
and it doesn't check DISABILITY's count, which its arithmetic doesn't report.
`test_a_prior_limits_what_a_status_reports` pins that count by hand.

The wide search drew 250 invented declarations from fresh seeds, 150 from
`prior_edge_declaration` and 100 from `declaration`. Each edge seed ran
`check_every_history` on both ending kinds and three requests and again on an
open period, then ran `check` on its listed and two-prior records and
`check_no_period` on those and a flagged record. Each declared seed ran the same
requests and one listed-prior check, and the search skipped 65 declared seeds
with more than 96 placements. All 2,450 checks held: 1,034 computed, 1,164
refused by name and 252 raised `InvalidFamilyInput`.

The first pass of this round's 40 listed mutations
(`round_19_mutations` in `track_b_insured_status_mutations.json`) ran through the insured status modules with
no restricted open, and 38 failed a named test. `start_search_skips_prior_years`
and `date_search_drops_binding` survived, and
`test_a_prior_reaches_a_year_the_start_cannot` and
`test_a_listed_prior_holds_every_ending_to_the_date` now kill them. Two stress
tests gained `@example` pins while that pass ran, so its results rest on mixed
test bytes. A cloud session reran all 40 at the final bytes, `168bb3a8`,
through every insured status module (`round_19_mutations` in
`docs/design/track_b_insured_status_mutations.json`). Thirty-six failed a
named test. Four passed every test, and round 20 kills them.

Against `129d44bd`, 44 of the 162 tests then in the five changed modules fail.
Three tests arrived later and two stress tests gained `@example` pins, and four
of those five fail there. The fifth checks only the arithmetic of an invented
history.

These tests execute the invariants this round adds:

- under UNKNOWN priors or UNKNOWN establishment, a computed status or lower date
  holds on every annual placement with no period in force, and otherwise the row
  refuses by name and keeps its weight (`check_every_history` and its stress
  tests, `test_a_prior_can_undercut_the_date`,
  `test_a_prior_can_undercut_the_status`,
  `test_unknown_establishment_alone_refuses`);
- the worst filling matches exhaustive placements at every tested quarter
  (`test_the_worst_filling_matches_every_placement`);
- a start some placement moves stays open, and a start every placement holds
  stands (`test_a_start_some_placement_moves_stays_open`,
  `test_a_fixed_start_is_the_onset`);
- `_prior_start_binds` answers true only where placement splits the prior on
  the basis it holds or a later prior rests on an earlier one
  (`test_placement_binds_a_prior_only_when_it_splits_them`);
- a computed result on a listed prior is the best the prior allows, for each
  status, count and date, and round 21 asks this of each basis the prior can
  rest on (`check`, `check_no_period`, and their stress tests);
- a listed prior that placement decides never moves a result it can't reach, and
  a result no kept filling attains refuses by name
  (`test_a_listed_prior_can_undercut_the_date`,
  `test_a_listed_prior_can_undercut_the_status`,
  `test_a_listed_prior_binds_without_a_current_period`);
- a flagged prior keeps its route and stays short of 404.130(b)
  (`test_a_special_prior_needs_a_quarter_of_its_route`,
  `test_a_special_prior_stays_short_of_the_ordinary_rule`).

## Round 20 a start's later years stay open

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.
A run of round 2's property test drew an invented input that `168bb3a8`
refuses, and the rerun of round 19's mutations left four alive. This round
fixes the first and kills the four.

### Later years can't move a start

An invented person born 1970-02-02 has four QCs in each of 1990 to 1999 and 2,
3, 2, 2 and 2 QCs in 2016 to 2020, a listed prior from 2000-04-02 through
2003-09-30, and an established period from an onset of 2004-01-15. For a
December 2020 query, `168bb3a8` refused the record with "More than 4096
first-start annual placements". Round 17's `_fillings_keeping_start` asked
`_start_sensitive_years` for the years through the latest possible start
(`_current_period_start_horizon`), here the query month, so it counted the
5,184 placements of 2016 to 2020. The 2004 start rests on 1990 to 1999.

A period begins at the onset or in the first later quarter that insures its
holder (404.321(a)), and each insured test at a quarter counts QCs through
that quarter only. Whether a
filling keeps a start therefore turns only on quarters through it, and no
later year can move it. `_fillings_keeping_start` now passes the reported
start in place of that horizon, so it enumerates only years through the
start, with the years a binding prior needs. Later years stay flexible, and
each status places them favorably (RS 00301.230), as the
logged reading `us:oasdi-insured-one-filling-first-start` says. The record
computes: with the period through the query, its 40 QCs of 1990 to 1999 meet
the eight elapsed years 1992 to 1999
(`test_partial_years_after_the_start_stay_open`).
`test_a_filling_keeps_its_start_whatever_later_years_hold` draws records near
the 20-of-40 edge and checks that two fixed fillings that agree through a
start's year give that start.

### Four survivors

The rerun ran all 40 mutations through every insured status module, with no
restricted open. Four passed every test, and each now fails a test of this
round:

- `binding_reaches_open_period` asks `_prior_start_binds` about a listed prior
  under UNKNOWN establishment too. There `_settle_every_history` proves a
  result every placement attains with no period in force, so a prior that
  placement splits can't move it. The record of
  `test_unknown_establishment_leaves_a_split_prior_to_the_proof`, with an
  UNKNOWN 1997, computes a lower date of 2008-03-31 and fully and currently
  insured status. The mutant refuses it by name
  (`test_an_unknown_year_leaves_a_proven_result_to_the_proof`).
- `disability_reads_the_completion` has DISABILITY's search read the person
  with the current period added, so the period's establishment skips the
  period's own first quarter. Take round 19's 1961-born record with its 1998
  to 1999 prior listed and an established period from 2004-01-01 through
  2004-12-31. The prior holds the 1998 QC in 1998Q1, and the 40 counted
  quarters through 2004Q1 hold 26 QCs. The mutant also skips 2004Q1, which
  holds no QC, reaches back one more quarter and counts 27
  (`test_an_establishment_counts_no_quarter_of_its_own_period`).
- `every_reads_listed_periods` has `_prior_start_binds` test every placement
  with the earlier priors in force. `_every_placement_passes` finds the worst
  filling exactly only with no period in force, as its docstring says. A
  period keeps its first and last quarters when they are QCs (404.130(f),
  404.146(d)), so an early QC can land on a credited endpoint and count where
  a later one falls inside the period. An invented person born 1961-02-02 has
  four QCs in each of 1987 and 1992 to 1994 and one in 1999, a prior from
  1999-01-01 through 2000-09-30, and a later prior from 2002-04-01 through
  2003-09-30. Past blindness asks the later prior for fully insured status
  (404.130(e)). Counting the earlier period leaves 17 elapsed years, and
  disregarding it leaves 19. The 1999 QC counts only in 1999Q1, so only that
  placement reaches 17, and placement splits the later prior. The mutant's
  worst filling puts the QC in 1999Q1 and finds every placement passing.
  With an UNKNOWN 1997 the rule refuses the record by name, and the mutant
  computes it (`test_a_later_prior_on_an_earlier_endpoint_binds`,
  `test_an_unknown_year_refuses_that_later_prior`).
  `test_a_later_prior_placement_splits_binds` draws pairs of priors. It checks
  `_prior_passes` on each fixed filling against the oracle, and it checks that
  `_prior_start_binds` answers true wherever those fillings split.
- `flagged_refuses_every_placement` drops the clause that releases a flagged
  prior every placement carries. That prior's holder "were only insured under
  paragraph (c)" (404.130(d)(1)). When every placement passes its route and
  none reaches 20 of 40, the prior holds on every placement and binds nothing.
  Round 19's 1960-born record has a flagged prior from 1990-04-01 through
  1991-12-31, two QCs in 1985, four in each of 1986 to 1989 and one in 1990.
  With an UNKNOWN 1993 the rule computes fully insured status, and the mutant
  refuses the record by name
  (`test_an_unknown_year_leaves_a_special_prior_every_placement_carries`).
  `test_a_special_prior_every_placement_carries_binds_nothing` checks the
  predicate against the oracle on drawn records.

Restoring the horizon (`fix_reverted`) makes
`test_partial_years_after_the_start_stay_open` refuse again. Each of the four
survivors and `fix_reverted` fails at least one of this round's nine tests,
and the unmodified source passes all nine. Each ran in its own process on
invented data, with both data roots set to a nonexistent path. A cloud session
then reran round 19's 40 mutations and `fix_reverted` at `38a573a8`, through
every insured status module. All 41 failed a named test, with no restricted
open (`round_20_mutations`, PR #562 comment 6589941045).

Against `168bb3a8`, 6 of the 32 tests in the three changed modules fail:
round 2's pinned record, `test_partial_years_after_the_start_stay_open`, and
the four register tests, since that head has no register.

These tests execute the invariants this round adds:

- placement of the years after a start never moves it: two fixed fillings
  that agree through a start's year give that start
  (`test_a_filling_keeps_its_start_whatever_later_years_hold`), and a record
  whose later years hold more than 4,096 placements computes
  (`test_partial_years_after_the_start_stay_open`);
- under UNKNOWN establishment, a result every placement attains with no period
  in force stands, however placement splits a listed prior
  (`test_an_unknown_year_leaves_a_proven_result_to_the_proof`);
- DISABILITY's count for a period's establishment skips no quarter of that
  period (`test_an_establishment_counts_no_quarter_of_its_own_period`);
- `_prior_passes` on a fixed filling agrees with the oracle for a later prior
  counted with an earlier one, and `_prior_start_binds` answers true wherever
  placement splits the prior
  (`test_a_later_prior_placement_splits_binds`,
  `test_a_later_prior_on_an_earlier_endpoint_binds`);
- a flagged prior that every placement carries on its route, short of 20 of
  40, binds nothing
  (`test_a_special_prior_every_placement_carries_binds_nothing`,
  `test_an_unknown_year_leaves_a_special_prior_every_placement_carries`).

## Round 21 a listed prior's basis

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.
An independent review of `38a573a8` reported one medium and one low (PR #562
comment 6589002155). Both ask what a listed prior says about placement.

### The record doesn't say why a prior began

A period begins in a quarter its holder was insured (404.320(b)(2),
404.321(a)). `DisabilityPeriod` records no blindness, and
`Person.statutory_blindness` speaks only for the present. An unflagged prior
could rest on past blindness, which asks only for fully insured status
(404.130(e)), or on a rule that asks for that and more: 404.130(b), or
404.130(d) after a flagged prior (round 22 took 404.130(c) out). `38a573a8`
held every unflagged prior to fully insured status alone. That weakest test
suits a possibility proof, but it let a true status or a date stand where only
the blind reading reaches it.

An invented person born 1955-02-02 has four QCs in each of 1980 to 1984 and
1989 to 1992, three in 1993, one in 1998, four in each of 1999 to 2002 and three
in 2003, with a listed prior from 1998-01-01 through 1999-12-31. For a January
2008 query, `38a573a8` reported a date last insured of 2008-03-31.

The arithmetic runs by hand. The 39 QCs before 1998 clear the 21 that fully
insured status asks at the prior's start (the elapsed years 1977 to 1997), so
past blindness leaves the 1998 QC in any quarter. 404.130(b) also asks 20 of 40.
The quarters from 1988Q2 through 1997Q4 hold 19 QCs, so it needs the 1998 QC in
1998Q1. The 40 quarters through 2008Q1 then hold 19 QCs with the period's
quarters counted, and 17 with its exclusion. The 40 quarters through 2007Q4 hold
20. The date falls on 2007-12-31 on 404.130(b) and on 2008-03-31 on past
blindness. With an onset in January 2008, `38a573a8` reported DISABILITY true,
which only past blindness reaches.

### Each basis the record allows

404.130(b) and (d) each ask for fully insured status too, so every filling that
begins a prior on them also begins it on past blindness. The rule's results take
the best lawful filling. A filling that begins the prior on the strictest basis
and attains a result therefore proves that result on the other basis too, and a
result no such filling attains differs between them. False results stay false
on any subset of placements.

`_prior_basis` picks that strictest basis, one prior at a time. It returns false
where some placement meets 404.130(b), or 404.130(d) after a flagged prior, with
the earlier priors, and true where only past blindness can begin the prior.
`_prior_start_binds` then asks whether placement decides the prior on that
basis, and `_keeps_priors` tests each filling on it, so `binding` now pairs each
prior with its basis. A result none of those fillings attains refuses by name
and keeps the row's weight (`test_a_date_only_blindness_reaches_refuses`,
`test_a_status_only_blindness_reaches_refuses`,
`test_that_refusal_keeps_the_row`). Round 19's limits apply unchanged: an UNKNOWN
year with a prior that placement decides refuses
(`test_an_unknown_year_refuses_a_prior_placement_decides`), and a current period
after the prior searches the same fillings
(`test_a_current_period_after_that_prior_refuses`). A frozen exit reaches the same
refusal (`test_a_frozen_exit_after_that_prior_refuses`).

This treats a missing fact. It adds no reading of the law, so it adds no entry to
the register, and the one-filling reading now names the basis. Counts and
assignments come from the strict basis's fillings, while statuses and the date
match on every basis. Two priors whose strict bases no one filling can meet
together refuse, though a weaker basis for one could compute. Refusing keeps the
row.

### A prior no placement supports

`38a573a8` also computed a record whose listed prior no placement can begin,
treating that prior as unconstrained. Such a prior rests on credits or facts the
record omits, and those could move other results, so `_prior_basis` now refuses
it by name for every test, with or without an established current period
(`test_a_prior_no_placement_supports_refuses_for_each_test`,
`test_unknown_establishment_refuses_a_prior_no_placement_supports`). A flagged
prior's holder passed a special route and not 404.130(b), so that prior refuses
this way if no placement passes either or every placement passes 404.130(b)
(`test_a_flagged_prior_no_placement_supports_names_why`). Upper credits speak for
the first and lower credits for the second, so an UNKNOWN year that could support
the prior leaves the decision to placement
(`test_an_unknown_year_can_support_a_prior`,
`test_an_unknown_year_can_leave_a_flagged_prior_short_of_the_ordinary_rule`,
`test_an_unknown_year_can_carry_a_flagged_prior_past_the_ordinary_rule`).

This changed six older invented records that listed a prior their credits
couldn't begin. Their tests ask about other things, so each record gained the QCs
its prior needs, and each test still reaches its own boundary: round 15's "prior
period year" (`test_an_entitlement_window_cannot_borrow_the_starts_placement`),
`test_the_date_last_insured_alone_can_refuse_a_moving_start`, which also gave up a
2008 QC so the current start still moves,
`test_unknown_bounds_with_prior_disability_period`,
`test_sam_favorable_disregard_counterexample_one_qc_boundary`,
`test_property_disability_period_exclusion_never_adds_qcs` and
`test_property_subsequent_special_and_dli_monotonic`. Three round 19 tests that
pinned the old answer now pin the refusal.

### Oracle and generators

`basis_worlds` replaces `fillings_keeping_priors`. It lists the fillings each
combination of bases allows, strictest first, and drops an empty combination.
`check` and `check_no_period` now require each status and the date on every
combination, the counts on the first, and at least one combination behind any
computed result. `check_every_history` also reads the fillings that keep a prior
on 404.130(b). `basis_prior_declaration` redraws the record above around
its edge, and `two_basis_declaration` adds a prior with its own basis, in either
order. `test_each_basis_matches_every_placement` compares `_prior_passes`,
`_prior_basis` and `_prior_start_binds` on both bases with every placement of the
drawn records, and that test also checks that each filling passing 404.130(b) or
(d) passes past blindness.

Refusing a prior no placement supports left 62 percent of
`subsequent_declaration`'s draws refusing, so that generator now places the QCs
its prior needs and keeps `declaration`'s limit of four partial years, because
the oracle lists every placement. It computes on 285 of 400 draws, with 11
refusing for want of support.
`test_status_stress_candidate_order_changes_nothing` moved from seed 5000019,
which now refuses, to 5000059.

The wide search drew 150 fresh seeds for each of eight checks on
`basis_prior_declaration`, that record with a current period,
`two_basis_declaration`, `listed_prior_declaration` and
`two_prior_declaration` (each with and without a current period) and
`special_prior_declaration`, plus 150 draws each from `declaration` and
`subsequent_declaration`, skipping 224 draws with more than 96 placements. All
1,276 checks held: 884 computed, 286 refused by name and 106 raised
`InvalidFamilyInput`.

The list of mutations (`round_21_mutations` in
`track_b_insured_status_mutations.json`) re-derives round 20's
41 at this round's source, less `unflagged_refuses_unsupported_prior`, whose
branch the rule no longer has, and adds 17 of this round's own. A first pass of
all 57 through rounds 19 to 21 ran with no restricted open, and 54 failed a named
test. Round 2's `test_unknown_period_status_and_dli_bounds_contain_concrete_fillings`
kills `date_tested_at_query`. `proof_keeps_listed_priors` survived because
`test_unknown_establishment_needs_the_disregard` had begun to pass on this
round's new refusal, so that record gained the QCs its prior needs and reaches
the proof again. `test_an_unknown_year_can_carry_a_flagged_prior_past_the_ordinary_rule`
now kills `binds_flag_on_lower_credits`.

A log of every refusal `_prior_basis` raised, across the insured status modules
other than the stress module, then found one more test resting on the new refusal:
`test_the_date_last_insured_alone_can_refuse_a_moving_start`. Its new record
reaches the moving start again, and the test now pins that refusal's detail. The
list takes round 15's five mutants of that path, re-derived at this source, for
62 in all. Through round 15's module alone all five fail, four of them first on
this test and `remove_first_start_check` first on
`test_no_filling_carries_the_start_and_the_status_together`. The log's other
entries are the tests that pin this refusal,
`test_placement_binds_a_prior_only_when_it_splits_them`, which calls `_prior_basis`
directly, and `test_classification_oracle_prior_and_unknown_completions`, which
checks only that a row and its weight survive. Over the stress tests that expect a
refusal, the log found ten of `test_status_stress_refuses_a_start_no_filling_supports`'s
13 seeds refusing for want of support. That test now draws 13 seeds on which the
oracle shows no filling with both the earliest start and the best status or date,
and it pins the moving start's detail.

A cloud session then ran all 62 at `f37f7f79`, through every insured status
module. All 62 failed a named test, with no restricted open
(`round_21_mutations`, PR #562 comment 6594394873).

These tests execute the invariants this round adds:

- a computed status, date or result on a listed prior holds on each basis some
  placement allows, and otherwise the row refuses by name and keeps its weight
  (`check`, `check_no_period`, `test_status_stress_a_prior_on_either_basis`,
  `test_status_stress_priors_on_different_bases`,
  `test_status_stress_a_current_period_after_either_basis`,
  `test_a_date_only_blindness_reaches_refuses`,
  `test_that_refusal_keeps_the_row`);
- every filling that passes 404.130(b) or (d) at a prior's start passes past
  blindness, and `_prior_basis` and `_prior_passes` agree with every placement on
  both bases (`test_each_basis_matches_every_placement`,
  `test_a_filling_keeps_a_prior_on_its_own_basis`);
- `_prior_basis` returns false wherever a placement meets 404.130(b), or
  404.130(d) after a flagged prior, including with an earlier prior, and true
  only where past blindness alone can begin the prior
  (`test_each_basis_matches_every_placement`,
  `test_a_prior_only_blindness_can_begin_keeps_that_basis`,
  `test_a_later_prior_can_rest_on_an_earlier_one_on_either_basis`);
- `_prior_start_binds` on the first prior answers true exactly where some
  placement fails its basis, and on a later prior wherever one does
  (`test_each_basis_matches_every_placement`,
  `test_every_nonblind_placement_binds_nothing`,
  `test_one_placement_can_decide_a_nonblind_prior_alone`);
- a prior no placement supports refuses by name for every test, and an UNKNOWN
  year that could support it leaves the decision to placement
  (`test_a_prior_no_placement_supports_refuses_for_each_test`,
  `test_a_flagged_prior_no_placement_supports_names_why`,
  `test_unknown_establishment_refuses_a_prior_no_placement_supports`,
  `test_an_unknown_year_can_support_a_prior`);
- a flagged prior has one basis (`test_a_flagged_prior_has_one_basis`).

## Round 22 an unflagged prior before age 31

Verification class: statutory conformance on invented declarations only.
This correction admits no population, behavioral, payment, or forecast claim.
An independent review of `f37f7f79` reported one medium and one low (PR #562
comment 6592883037).

### What the flag says

404.130(d)(1) reaches someone "disabled again at age 31 or later after having
had a prior period of disability established which began before age 31 and for
which you were only insured under paragraph (c)". `special_insured` records
that fact, so an unflagged prior's holder wasn't only insured under 404.130(c),
and that paragraph can't begin the prior alone. A nonblind unflagged prior
rests on 404.130(b), or on 404.130(d) where it begins at 31 or later after a
flagged prior, and past blindness stays open as before. Round 21 let
404.130(c) begin an unflagged prior. Before age 31, 404.130(c) can hold a prior
on every placement while 404.130(b) holds a QC in the prior's first quarter,
and the prior then bound nothing.

The review's record is round 21's for a woman born 1968-02-02, without the 1980
to 1984 QCs: four QCs in each of 1989 to 1992, three in 1993, one in 1998, four
in each of 1999 to 2002 and three in 2003, with a listed prior from 1998-01-01
through 1999-12-31, before the 1999Q1 quarter she attains 31. The 36 quarters
from 1989Q2 through 1998Q1 hold 18 QCs, half of them, so 404.130(c) holds the
prior on every placement. 404.130(b) finds 19 of 40 there and needs the 1998 QC
in 1998Q1. On that placement the date falls on 2007-12-31, and on past
blindness on 2008-03-31. `f37f7f79` reported 2008-03-31 for a January 2008
query, DISABILITY true at a January 2008 onset, and 2008-09-30 for a 2027 query
with an exit frozen after 2003. Each now refuses by name, as do an UNKNOWN 2005
and a current period over 2004 (`test_a_date_only_blindness_reaches_refuses`,
`test_that_refusal_keeps_the_row`, `test_with_no_onset_the_date_refuses`,
`test_a_frozen_exit_refuses`, `test_an_unknown_year_refuses`,
`test_a_current_period_after_that_prior_refuses`). A flagged prior can't meet
404.130(b), so there the 1998 QC falls later, and the record computes
2008-03-31 (`test_a_flagged_prior_there_computes`).

### The change

`_witness` takes `under31_route`, and `_prior_passes` and
`_every_placement_begins` pass it the prior's flag. An unflagged prior before
31 then has no special route, and one at 31 or later keeps 404.130(d) after a
flagged prior. The current period and every other caller keep 404.130(c) as
before.

The change moves two other kinds of record. Where only 404.130(c) could begin
an unflagged prior, the record now implies past blindness
(`test_a_prior_only_paragraph_c_begins_rests_on_past_blindness`). Where
404.130(c) held such a prior to some placements, round 21 searched them and
could refuse. Past blindness now holds the prior on every placement, and with
two 1993 QCs the record computes 2008-03-31
(`test_a_prior_paragraph_c_splits_computes_on_past_blindness`).

After a flagged 1995 prior, the 1998Q1 prior still rests on 404.130(b), because
404.130(d) opens only at 31
(`test_a_young_prior_after_a_flagged_one_rests_on_paragraph_b`). A prior from
1999Q2 after a flagged 1993 prior rests on 404.130(d), which counts 37 quarters
with the earlier period's four set aside, and finds 18 only with the 1999 QC by
then (`test_a_prior_past_31_after_a_flagged_one_can_rest_on_paragraph_d`).
Without the flag that prior rests on past blindness
(`test_without_the_flag_that_prior_rests_on_past_blindness`).

The change applies the field's definition. It adds no reading of the law, so it
adds no register entry, and the one-filling entry now names the bases. The
review offered a second course, reading the flag as unknown, which would also
open 404.130(d) for later statuses. The interface declares the flag an
adjudicated fact, so the rule takes an OBSERVED false flag as false.

### A listed prior's onset

A listed prior records its start, not its onset. The rule reads that start as
the favorable earliest insured quarter from the onset (RS 00301.230,
404.321(a)). Had any placement insured an earlier quarter from the onset, the
period would have begun there, so every placement leaves the quarters between an
earlier onset and the start uninsured, and the onset adds no constraint on
placement. The review's probe found no wrong output under this reading. For a
woman born 1970-07-15 with a prior from 1995-04-01 through 1995-12-31, a later
status turns false only on a completion that leaves 1995Q1 uninsured, and that
completion sets aside the favorable placement that insures 1995Q1.

### Oracle and generators

The stress oracle's `prior_holds` now holds an unflagged prior to 404.130(b),
or 404.130(d) after a flagged prior, and `prior_can_begin` holds an added prior
to 404.130(b) on its nonblind basis. `disability` takes `paragraph_c`, and
`flags` reads each prior's flag, so a record can mix flagged and unflagged
priors. `two_basis_declaration` now draws a 1984Q1 prior that only past
blindness begins, though 404.130(c) alone would, a 1985Q1 prior on 404.130(b),
or round 21's 1986Q2 prior. `young_basis_declaration` redraws the review's
record around its edges and flags a quarter of the draws, and
`mixed_flag_declaration` adds an unflagged prior after
`subsequent_declaration`'s flagged one. Round 22's
`test_each_basis_matches_every_placement` compares `_keeps_priors`,
`_prior_basis` and `_prior_start_binds` with every placement of those draws, and
`test_a_later_prior_after_a_flagged_one_matches_every_placement` does the same
for a later prior on either side of 31.

Over seeds 0 to 59, `young_basis_declaration` computes 45 draws and refuses 15
by name with no current period. With a current period over 2004 it computes 42,
refuses 17 and draws one record the interface rejects. At `f37f7f79` the oracle
fails two of the 60 draws on both checks. Over seeds 0 to
39, `mixed_flag_declaration` puts 32 later priors at 31 or later and 8 before,
and no draw separates `f37f7f79` from this round, so that generator checks
404.130(d) for an unflagged prior end to end, and the round's own tests carry
the case before 31.

Round 19's `test_placement_binds_a_prior_only_when_it_splits_them` let a
flagged prior begin in 1991Q1, the quarter she attains 31, which the interface
rejects, and CI drew that case at `f37f7f79`. The test now draws flagged starts
through 1990Q4, and its oracle holds an unflagged prior to 404.130(b).

The list of mutations (`round_22_mutations` in
`track_b_insured_status_mutations.json`) takes round 21's 62
at this round's source and re-derives `ordinary_keeps_special_route`, which
drops `not ordinary_only`, against the new condition. It adds eight of this
round's own, for 70. `unflagged_reads_paragraph_c` in `_witness`, and
`route_reads_paragraph_c` and `every_reads_paragraph_c` in `_prior_passes` and
`_every_placement_begins`, give an unflagged prior 404.130(c) again.
`young_takes_subsequent_route` gives an unflagged prior before 31 the special
route once a flagged prior precedes it, and `unflagged_drops_paragraph_d` takes
404.130(d) from an unflagged prior. `route_drops_flagged_paragraph_c` and
`every_drops_flagged_paragraph_c` take 404.130(c) from a flagged prior, and
`current_drops_paragraph_c` takes it from the current period.

A first pass of all 70 through rounds 19 to 22 ran with no restricted open, and
66 failed a named test, 34 of them first in round 22's module. Round 22's tests
kill six of the eight new mutants first. Round 21's
`test_an_unknown_year_can_carry_a_flagged_prior_past_the_ordinary_rule` kills
`every_drops_flagged_paragraph_c`, and round 19's
`test_a_prior_holds_a_qc_in_its_first_quarter` kills
`current_drops_paragraph_c`. As at round 21, round 15's module kills the three
moving-start mutants that pass rounds 19 to 22: `remove_first_start_check`
first on `test_no_filling_carries_the_start_and_the_status_together`, and
`drop_bound_refusal` and `bound_stops_at_reported_start` on
`test_the_date_last_insured_alone_can_refuse_a_moving_start`. Round 2's
`test_unknown_period_status_and_dli_bounds_contain_concrete_fillings` kills
`date_tested_at_query`.

A cloud session then ran all 70 at `7b5b126a`, through every insured status
module. All 70 failed a named test, with no restricted open
(`round_22_mutations`, PR #562 comment 6596641719).

Against `f37f7f79`, 13 of round 22's 17 tests fail, as do
`test_status_stress_a_young_prior_on_either_basis` and round 21's
`test_each_basis_matches_every_placement`. The four that pass check the
arithmetic, the flagged record, 404.130(d) after a flagged prior and the record
at 31 without a flag, which the change leaves alone.

These tests execute the invariants this round adds:

- an unflagged prior's nonblind basis is 404.130(b), or 404.130(d) at 31 or
  later after a flagged prior, never 404.130(c) alone, and `_keeps_priors`,
  `_prior_basis` and `_prior_start_binds` agree with every placement on each
  basis (`test_each_basis_matches_every_placement`,
  `test_a_later_prior_after_a_flagged_one_matches_every_placement`,
  `test_a_young_prior_after_a_flagged_one_rests_on_paragraph_b`,
  `test_a_prior_past_31_after_a_flagged_one_can_rest_on_paragraph_d`,
  `test_only_paragraph_b_binds_the_prior`);
- a flagged prior keeps 404.130(c) (`test_a_flagged_prior_there_computes`,
  `test_a_prior_only_paragraph_c_begins_rests_on_past_blindness`);
- a computed status or date on an unflagged prior before 31 holds on each basis
  some placement allows, and otherwise the row refuses by name and keeps its
  weight (`check`, `check_no_period`,
  `test_status_stress_a_young_prior_on_either_basis`,
  `test_a_date_only_blindness_reaches_refuses`,
  `test_that_refusal_keeps_the_row`);
- the current period keeps 404.130(c) (`test_status_stress_under_31`).

## Round 23 a period keeps the basis it began on

Verification class: statutory conformance on invented declarations only. This
correction admits no population, behavioral, payment, or forecast claim. An
independent review of `7b5b126a` reported seven mediums, 17 lows and six nits
(PR #562 comment 6596920658). The rows and passages above now state the rule as
it stands, and this section records what changed and why.

### A current period begun on 404.130(c) alone

404.130(d)(1) reaches someone "disabled again at age 31 or later after having
had a prior period of disability established which began before age 31 and for
which you were only insured under paragraph (c)", and Act 223(c)(1)(B)(iii)
says the same. A listed prior carries that fact as `special_insured`, but
`7b5b126a` appended the current period it began without it, so the quarters
after that period lost 404.130(d). The review's record is a woman born
1980-02-02 with an onset on 2003-01-15 and a period that ends 2004-12-31, two
QCs in 2001, four in 2002, four in each of 2009 to 2011 and one in 2012,
queried in January 2013. At 2003Q1 the 12 quarters from 2000Q2 hold the six QCs
of 2001 and 2002, so 404.130(c) holds, and 404.130(b) finds six of 40. At
2012Q4, past the 2011Q1 quarter she attains 31, 404.130(d) counts the 47
quarters from 2001Q2 less the period's eight, an odd 39 it reduces to 38, and
the 19 QCs meet half. `7b5b126a` reported 2006-06-30 as an exact date last
insured, and the rule now reports 2012-12-31
(`test_a_period_begun_on_paragraph_c_alone_opens_paragraph_d_after_it`). A
frozen exit keeps that date, a second record holds through its 2016Q1 query
quarter (`test_the_flag_reaches_a_frozen_exit_and_a_later_record`), and an
UNKNOWN end gives the range from 2004-12-31 to 2013-03-31
(`test_an_unknown_end_spans_the_flagged_period_lengths`).

`_current_period_special` now records that fact for a period the rule begins:
the period began before the quarter its holder attains 31, its holder wasn't
blind, and 404.130(b) failed in its first quarter. `_complete_current_period`
writes the flag on the period it appends, and `_current_period_completions`
keeps it on each ending. Where annual placement decides whether 404.130(b) held
in that quarter, the function returns None, and with listed priors it stays
open whenever some placement meets 404.130(b). `_settle_current_basis` then
computes the date on both bases and refuses by name where they differ, with
ASSIGNMENT_COMPLEXITY where placement decides and UNKNOWN_EARNINGS where an
UNKNOWN year does. With one 1997 QC and four in each of 1998 to 2000 added,
404.130(b) finds 19 of 40 at 2003Q1. A 1993 QC counts there only in 1993Q2 to
Q4, and no later window counts it, so its placement decides between the two
dates, as an UNKNOWN 1997 does
(`test_a_placement_or_year_that_decides_the_basis_refuses`). The flag adds
404.130(d) only for quarters after the period, so only the date last insured
can move, and FULLY computes on either basis.

One more QC can bring the date earlier, as the law reads. With 19 QCs before
the onset, 404.130(b) fails at 2003Q1, the period rests on 404.130(c) alone,
and 404.130(d) holds through 2012Q4. A second 1997 QC makes 20 of 40 at 2003Q1,
so 404.130(b) began the period, 404.130(d) never applies, and 20 of 40 last
holds at 2012Q3 (`test_one_more_qc_can_bring_the_dli_earlier_intended`). The
test labels this violation of QC monotonicity intended.

`test_an_ended_current_period_counts_as_the_prior_it_becomes` lists the period
the rule begins as a prior, with the flag 404.130(b) implies, and checks that
both give the same date. Its records put every 1997 to 2002 QC in the 40
quarters ending 2003Q1, so 404.130(b) holds there on every placement or on
none. A run over its whole strategy space, 11,700 records, computed 11,599 that
agree and refused the other 101 by the long-period register entry's name.
`7b5b126a` gives a different date for 568 of those records, so 25 random draws
miss them all in about 29% of runs. The test now always runs one of them: the
review's record with four QCs in each of 1998 to 2000, where `7b5b126a` ended
the date at 2012-09-30 and the rule gives 2012-12-31.

### A period that shares the quarter a prior ended in

404.321(a) begins a period on the onset day if its holder had insured status
then. In RS 00301.140's example 7, Jane's prior period ended on October 31,
1990, and she became disabled again on December 3, 1990, in the same quarter.
`7b5b126a` required each period to begin in a quarter after the one before it
ended, so her established record raised `InvalidFamilyInput` and lost its row,
and I13 called the case impossible. Periods may now share a quarter but not a
day (I4). Jane's period begins on 1990-12-03
(`test_rs00301_140_example_7_begins_on_the_onset_day`,
`test_any_onset_after_the_prior_day_keeps_its_own_start`), and a day two
periods both cover stays an input error
(`test_periods_still_may_not_share_a_day`). No candidate start can overlap a
prior now, so round 23 removes the overlap search, its 4,096-filling limit and
the fixed-overlap proof, and retires I13 and B15. 404.321(b) and (c) end a
period on a month's last day, so under UNKNOWN priors a prior can end in the
onset quarter only before a February or March onset
(`test_unknown_priors_may_end_before_a_later_onset_in_its_quarter`).

The register entry `us:oasdi-insured-flag-first-insured-quarter` read a
recent-rule quarter inside a prior period, where no start could fall, as
leaving a flag's start open. A start may now fall in any quarter from the
onset, so round 23 drops the entry and its marker in `_recent_rule_possible`,
and the register holds nine readings.

### A coverage exit bars only later years

RS 00301.230 B lets an annual QC go to "any quarter in the calendar year",
subject to RS 00301.240, which bars a quarter not yet begun, one after death
and a disability period's interior (404.146). `7b5b126a` also barred an exit
year's quarters after the exit quarter, and a birth year's quarters before the
birth quarter, and the law has neither bar. With a February 2020 exit, $6,000
of 2020 wages give four QCs, but `7b5b126a` left them one quarter, and FULLY
failed at 3 of 6, where the law gives 6 of 6
(`test_an_exit_year_credits_any_begun_quarter`). An exit now bars only the
years after it, which the history leaves out, and a quarterly QC or earnings a
caller declares after the exit quarter stays an input error
(`test_quarterly_bounds_name_themselves`). Every exit month of a year gives the
December exit's result (`test_the_exit_month_moves_nothing_in_its_year`, whose
example is a February exit with four 2020 QCs that `7b5b126a` cut to one), 40
QCs need no later quarter (`test_forty_qcs_need_no_later_quarter`), an UNKNOWN
exit year refuses whatever its exit month
(`test_an_unknown_exit_year_refuses_whatever_its_exit_month`), and an
established period keeps its row after a February exit
(`test_an_established_period_keeps_its_row_after_a_february_exit`). Dropping
the birth bar answers low 13: $3,120 of wages in the year of a December 2000
birth gives four QCs (`test_a_birth_year_credits_quarters_before_the_birth`).

### The first insured quarter on every basis

DISABILITY reports its first insured quarter (404.131(a), 404.321(a)). Where a
listed prior binds the placement, `7b5b126a` took that quarter from whichever
kept filling first tied on count. For a woman born 1959-02-28 with a prior from
2000-04-01 to 2005-03-31 and an onset on 2007-01-01, it reported 2010-07-01,
though the filling that begins the prior on 404.130(b) at 2000Q2 holds 20 of 40
at 2007Q1 (`test_a_binding_prior_keeps_the_earliest_qualifying_quarter`).
`_witness_rank` now ranks an earlier insured quarter above a larger count for
DISABILITY.

Where a binding prior's two bases, 404.130(b) and past blindness, give
different witnesses, each status now reports the range they give, and the
result lists `prior_disability_period_basis` among its unknown facts. Take
round 22's record with two QCs in 2003 rather than three, two in 2008 and an
onset on 2008-01-01. On 404.130(b) the 1998 QC sits in 1998Q1, and 2008Q2 first
holds 20 of 40; on past blindness it may sit later, and 2008Q1 holds 20. The
result reports 2008-04-01 with an upper qualifying quarter of 2008-01-01
(`test_a_prior_basis_split_widens_the_qualifying_quarters`), and a 1955 birth
widens the count to 20 to 21 the same way
(`test_a_prior_basis_split_widens_the_count`). Established, the split moves the
period's start, and the refusal now names the listed prior rather than
placement in general (`test_a_split_start_names_the_listed_prior`, nit 29).

Under UNKNOWN priors, `7b5b126a` reported DISABILITY's qualifying quarter as
exact bounds from the world with no prior. An UNKNOWN prior can set quarters
aside and reach earlier QCs (404.130(f)), so the first insured quarter can fall
as early as the onset quarter (404.131(a)). For a woman born 1961-02-02 with an
onset on 2007-01-01, no prior gives 2007-04-01, and a prior from 1990 through
1999 that begins on 404.130(b) gives 2007-01-01. The result now reports
2007-04-01 with an upper qualifying quarter of 2007-01-01
(`test_unknown_priors_reach_the_onset_quarter`).

### A man's elapsed years

404.110(b)(2)(iv) ends a man's count at "the year you became age 65" if he
became 62 before 1973, and (iii) ends it at 1975 if he became 62 in 1973 or
1974. `7b5b126a` ended a living man's count at the query year, so a man born
1908-07-01 with 20 QCs from 1951 to 1970 was fully insured in December 1971 at
20 of 20. His count runs from 1951 through 1972, so he needs 22
(`test_a_man_who_reached_62_before_1973_counts_to_65`). From the year he
reaches 62 the count now runs to that retirement year whatever the query, and a
death year ends it if earlier (404.110(b)(3)); disability keeps its count to
the onset year (404.132). `test_the_404_115_table_gives_each_cohort_its_count`
reads 404.115's table from the captured regulation and checks column II for a
living man and woman of every cohort at 62, 63, 64 and 66, and the death
columns of the 33 rows from 1893 through 1925.

### A flagged prior needs one placement for both halves

A flag records a prior "for which you were only insured under paragraph (c)",
so one placement has to pass a special route and fail 404.130(b) in the prior's
first quarter. `7b5b126a` checked the two halves apart, 404.130(c) on upper
credits and 404.130(b)'s failure on some placement. For a woman born 1962-06-28
with a flagged prior in 1990Q2, 404.130(c) counts 28 quarters there and asks
14, and every placement reaches at most 11, while 404.130(b) holds on some
placements. Under UNKNOWN establishment `7b5b126a` computed her insured on the
subsequent-special rule, though either declared establishment refused.
`_flag_fits` now asks for one placement that does both, on every completion of
each year still open by the prior's start, and refuses by name where none does
(`test_a_flagged_prior_needs_paragraph_c_without_paragraph_b`). 404.130(b)
fails as credits fall and the route passes as they rise, so a middle completion
can fit where neither bound does (`test_only_a_middle_completion_fits_a_flag`).
Where every placement of the lower credits meets 404.130(b), the flag can't
stand, and the refusal names it before any count of completions
(`test_a_flag_every_completion_contradicts_refuses_by_that_name`).

### A listed prior's basis and its refusal

Past blindness with fully insured status alone dates from benefits payable in
January 1973 (RS 00301.150 A), so `_blind_basis` lets it begin a listed prior
only from then (low 21). A prior from December 1972 on 12 QCs from 1962 to 1964
refuses by name, one from January 1973 computes
(`test_past_blindness_begins_a_prior_only_from_1973`), and a 1965 prior refuses
for FULLY as well (`test_a_1965_prior_cannot_rest_on_past_blindness`).

Without that basis, a listed prior from July 1952 through 1955 can still rest
on RS 00301.480 B.1, which begins a period on its own counts. A listed prior's
establishment shows its holder met the route's application conditions, so such
a prior holds where B.1's counts hold at its start on every completion and no
completion has 20 of 40 in a quarter from its start through September 1960,
which RS 00301.480 A would read as excluding the route. Where only some
completion or one reading of A supports it, it refuses by that route's name,
and where every completion has 20 of 40 in a quarter the prior covers, both
readings exclude the route
(`test_a_pre1956_listed_prior_rests_on_rs00301_480`). A current period can then
begin after such a prior
(`test_a_listed_alternate_prior_lets_a_later_period_begin`). The reading
belongs to the register entry
`us:oasdi-insured-pre1956-alternate-any-quarter-scan`, whose marker now also
sits in `_prior_basis`.

A listed prior that no completion supports rests on credits or facts the record
omits, and those could insure the current period as well.
`_refuse_unsupported_priors` now runs before the rule calls an established
period impossible or leaves its validity to UNKNOWN earnings, after any
deferred conversion's refusal, so the prior's named refusal keeps the row. A
woman born 1940-02-02 with eight QCs in 1968 and 1969, a 1970 prior and an
established 1977 period raised `InvalidFamilyInput` at `7b5b126a`, which let
past blindness begin the prior, and lost the row whatever 1974 to 1977 held.
She now refuses by the prior's name
(`test_an_unsupported_prior_refuses_before_unknown_earnings`). A fully-route
flag supplies fully insured status from a start the record doesn't give, so a
prior the flag can carry shows nothing missing (`_flag_carries_prior`,
`test_classification_oracle_fully_flag_can_carry_a_listed_prior`).

### The other lows and nits

These lows and nits change code, each with a test:

- low 12: a declared period end after the statutory FRA end raises
  `InvalidFamilyInput`, as a continuity date after it already did, where
  `7b5b126a` capped it silently
  (`test_declared_dates_past_the_statutory_end_are_input_errors`);
- low 16: a DIB entitlement month at or after FRA, and an RIB month before the
  one in which the holder attains 62, raise `InvalidFamilyInput` (Act
  223(a)(1), 202(a)(2)), where `7b5b126a` let them decide CURRENTLY
  (`test_entitlement_months_must_be_possible`);
- low 19: the pre-May-1983 refusal for a flagged prior fires only where the
  holder's age-31 quarter begins before May 1983, since 404.130(c) decided an
  onset before 31 under the earlier law too
  (`test_the_pre_1983_refusal_needs_31_before_may_1983`);
- low 23: `fully_insured_requirement` runs the person and query checks
  `insured_status` runs
  (`test_the_requirement_helper_checks_what_insured_status_checks`);
- low 24: Act 213(a)(2)(B) bars a quarter after the death quarter from being a
  QC, but wages paid then still count toward the year's total, so $7,770 paid
  in 1968Q2 after a February death brings the year to the $7,800 maximum and
  makes 1968Q1 a QC, where `7b5b126a` raised an input error
  (`test_wages_paid_after_death_count_toward_the_year`);
- nit 25: the error for a quarterly QC or earnings before birth now names the
  birth bound (`test_quarterly_bounds_name_themselves`).

The rest change text: the `SIMPLIFIED_PRE1951` row says pre-1951 QC flags add
nothing to the 213(c) aggregate (low 8); the RS 00301.800 cohort reads from
404.110(b)(2)(ii) through (iv) (low 9); the witness passage states FULLY's
larger-margin convention (low 10); the DLI row states that DISABILITY can hold
at a quarter past FRA while the date takes the cap (low 11); the deferred
refusals read as conservative (low 14); the module docstring and the event
passage say a declared DIB or RIB month replaces the query event (low 15); the
sources README narrows what its tests check (low 17); the Joseph and Frank
entries read as placement-dependent intermediate counts (low 18); the
long-period register entry adds the third parse (low 22); the fiscal-year
helper names the 1971 to 1972 gap (nit 26); the examples cite RS 00301.345
B.2.g and log Mary Brown's count (nit 27); and the note corrects the round 21
and 22 slips the review found (nit 28).
`test_the_note_cites_only_tests_that_exist` checks that every test this note
cites exists and that it cites no scratch file, and the PR body carries the
ledger path and current counts (low 20, nit 30). Blind roles run these
modules, so the check lists only the tests folder and opens only this note and
the insured status modules; at `8522452c` it searched every folder under
`tests/` and read each module it found.
`test_the_note_check_reads_only_the_note_and_insured_modules` checks each Path
listing and open before it runs.

### Renamed, retired and superseded

Round 23 renames these tests, whose old names described the overlap bar or a
reading this round corrects:

| Module | Name at `7b5b126a` | Round 23 name |
| --- | --- | --- |
| base | test_joseph_subsequent_poms_140_example_6_endpoint_erratum | `test_joseph_subsequent_poms_140_example_6_endpoint_placement` |
| base | test_unknown_upper_bound_respects_exit_quarter | `test_unknown_exit_year_keeps_every_quarter_of_its_year` |
| classification oracle | test_classification_oracle_alternate_needs_clear_start_before_1956 | `test_classification_oracle_alternate_can_start_in_a_prior_end_quarter` |
| classification oracle | test_classification_oracle_blind_ordinary_onset_cannot_be_delayed | `test_classification_oracle_blind_ordinary_onset_starts_after_prior` |
| classification oracle | test_classification_oracle_fully_flag_cannot_delay_an_insured_onset | `test_classification_oracle_fully_flag_keeps_an_insured_onset` |
| round 11 | test_fixed_overlap_precedes_every_flag_and_foreign_route | `test_a_prior_ending_in_the_onset_quarter_leaves_a_valid_start`; `test_a_prior_ending_in_the_onset_quarter_keeps_every_route_refusal` |
| round 12 | test_candidate_inside_prior_period_does_not_supply_recent_witness | `test_an_onset_in_a_prior_end_quarter_can_supply_the_recent_witness` |
| round 13 | test_disability_witness_uses_the_legal_annual_start_filling | `test_disability_witness_counts_the_quarter_a_prior_ended` |
| round 13 | test_post1955_clear_start_cannot_replace_overlapped_alternate | `test_every_test_refuses_a_shared_quarter_alternate_by_name` |
| round 13 | test_review_alternate_start_must_clear_same_prior_overlap | `test_an_alternate_start_can_share_the_quarter_a_prior_ended` |
| round 4 routes | test_possible_lower_earnings_filling_prevents_upper_overlap_input_error | `test_every_onset_year_filling_starts_a_valid_period` |
| round 4 routes | test_unknown_earnings_can_avoid_derived_prior_quarter_overlap | `test_unknown_onset_year_earnings_decide_the_current_start` |
| round 6 ordering | test_deferred_quarter_fillings_keep_fixed_minimum_and_valid_middle | `test_deferred_quarter_fillings_survive_a_shared_onset_quarter` |
| round 6 ordering | test_unresolved_overlap_keeps_original_deferred_refusal | `test_many_unknown_years_keep_original_deferred_refusal` |
| QC | test_death_future_exit_and_disability_endpoint_exclusions | `test_death_future_and_disability_endpoint_exclusions` |
| sources | test_rs00301_800_pdf_footnote_misprints_the_1913_male_age_65_cohort | `test_rs00301_800_pdf_footnote_misdates_the_male_age_65_cohort` |

Old names appear without code marks, so the citation test reads only live
names. The classification oracle adds
`test_classification_oracle_fully_flag_can_carry_a_listed_prior`.

Fourteen tests held the overlap bar, and round 23 retires them with it. Round
14's seven (first_successful_placement_cannot_settle_status,
one_treatment_overlaps_and_the_other_leaves_a_clear_start,
round_thirteen_annual_start_needs_named_refusal and four unchanged_..._overlap
cases) give way to eight on the shared quarter:
`test_a_shared_onset_quarter_is_a_valid_start`,
`test_one_onset_year_qc_starts_the_period_on_the_onset_day`,
`test_two_onset_year_qcs_leave_the_start_to_placement`,
`test_round_thirteen_annual_start_computes_in_the_shared_quarter`,
`test_ordinary_insurance_in_a_shared_onset_quarter_keeps_flag_refusal`,
`test_1962_ordinary_insurance_in_a_shared_quarter_fixes_start`,
`test_blind_fully_insured_onset_in_a_shared_quarter_starts_there` and
`test_the_treatment_that_insures_the_shared_quarter_fixes_the_start`. Round 5's
four overlap searches give way to
`test_shared_quarter_declaration_exactly_matches_every_quarter_filling`,
`test_an_april_end_needs_the_onset_quarter_insured`,
`test_any_1972_qc_starts_a_period_before_a_december_end` and
`test_many_unknown_years_keep_one_earnings_refusal_row`, and round 6's three
fixed-overlap orderings give way to
`test_a_prior_ending_in_the_onset_quarter_classifies_like_one_before`,
`test_a_shared_end_quarter_leaves_validity_to_unknown_credits` and
`test_shared_end_quarter_validity_stays_with_unknown_credits`.

These passages above record earlier rounds and stay as written, and round 23
supersedes them: round 13's list of fully-route first-onset overlaps and its
oracle's later ordinary start after an overlapping onset; round 15's remark
that round 14 stopped placements mixing only where the favorable start
overlapped a prior; round 16's stress generator, whose overlapping prior now
ends in the onset quarter (`shared`); and round 19's statement that the round
17 ruling stands, since round 23 lists the third parse in the register for Max
(d1920). Round 23 rewrites the round 5 and round 6 grids and examples in place,
and retires I13 and B15.

### Mutations

The list of mutations (`round_23_mutations` in
`track_b_insured_status_mutations.json`) takes round 22's 70 and adds 29 of
this round's own, for 99. Round 22's anchors still hold for 53 of the 70. The
other 17 touched code round 23 rewrote, and each keeps its intent at the code
that now does that job: two at the binding check, which now also asks for a
basis; five in `_keeps_priors` and nine in `_prior_basis`, which now pass
`options` and whose unflagged loop reads `_blind_basis`; and
`first_search_drops_binding`, since the first search now runs once with the
binding priors and once without. Each of the 70 ran through the tests that
killed it in round 22, and through their modules and round 23's where those
passed, and 69 failed a named test. `flagged_ignores_ordinary_rule`, which
drops a flagged prior's every-placement 404.130(b) check, now differs from the
rule only where more than 4,096 completions stand open: it refuses on their
number instead of the flag, and
`test_a_flag_every_completion_contradicts_refuses_by_that_name` kills it.

Round 23's own 29 undo one change each. `m1_flag`, `m1_open_basis` and
`m1_settle` drop the current period's flag, close an open basis, or skip the
basis check. `m2_listed` and `m2_current` bar a shared quarter again. `m3_exit`
and `m13_birth` restore the exit-quarter and birth-quarter bars. `m4_rank`
drops the earlier-quarter rank, `m5_earliest` the onset-quarter bound under
UNKNOWN priors, and `basis_split_unreported` and `basis_split_always` misreport
the basis split. `m6_men` ends a living man's count at the query. `m7_flagfits`
drops the one-placement check, and `flag_middle` searches only the bounds.
`precedence_possible` and `precedence_unknown` let the input error or the
UNKNOWN-earnings refusal come first. `pre1956_scan` scans past the quarters the
prior covers, and `pre1956_none` refuses the B.1 prior. `low21` lets past
blindness begin a prior before 1973, and `nit29` restores the general detail.
`low12`, `low16_dib`, `low16_rib`, `low19`, `low23`, `low24` and `nit25` undo
each low's check. `first_onset_short` and `first_onset_odd` move 404.130(c)'s
12-quarter floor or round its half up. Each of the 29 fails round 23's module.

Six local mutations of the note check each fail its read guard before the check
opens a file outside this note and the insured status modules: a recursive
`rglob`, a `**` glob, a subfolder glob, and a flat glob, a byte read and an
`iterdir` over every module in `tests/`. The list holds mutations of the rule's
source only, so it leaves these six out.

Against `7b5b126a`, 42 of round 23's 67 cases fail. The 25 that pass hold
behavior `7b5b126a` already had: the example 7 quote, the seven middle
completions and the two contradicted flags, the January 1973 prior, the
pre-1956 prior that computes, the seven published first onsets, the two valid
entitlement months, two quarterly bounds, the note's citations and its read
guard. The 42 fail on every run: `7b5b126a` raises an input error on all 61
onsets of `test_any_onset_after_the_prior_day_keeps_its_own_start`, and the
other two property tests each run an example `7b5b126a` fails. All three pass
on every input of their strategies at this head, 11,700, 61 and 300 of them.

These tests execute the invariants this round adds:

- a current period that began before 31 on 404.130(c) alone, its holder not
  blind, counts as a flagged prior for the quarters after it and gives the same
  date as that prior listed
  (`test_an_ended_current_period_counts_as_the_prior_it_becomes`,
  `test_a_period_begun_on_paragraph_c_alone_opens_paragraph_d_after_it`, and
  the stress oracle through `check`);
- where placement or an UNKNOWN year decides that basis and the bases give
  different dates, the date refuses by name and keeps its row
  (`test_a_placement_or_year_that_decides_the_basis_refuses`);
- periods share no day, and a period may begin in the quarter a prior ended
  (`test_rs00301_140_example_7_begins_on_the_onset_day`,
  `test_any_onset_after_the_prior_day_keeps_its_own_start`,
  `test_periods_still_may_not_share_a_day`);
- the exit month moves no result within its year, and neither a birth nor an
  exit bars an annual QC from a begun quarter of its own year
  (`test_the_exit_month_moves_nothing_in_its_year`,
  `test_an_exit_year_credits_any_begun_quarter`,
  `test_a_birth_year_credits_quarters_before_the_birth`);
- DISABILITY reports the earliest first insured quarter a kept filling attains,
  and its range spans every basis a binding prior can rest on and, under
  UNKNOWN priors, reaches the onset quarter
  (`test_a_binding_prior_keeps_the_earliest_qualifying_quarter`,
  `test_a_prior_basis_split_widens_the_qualifying_quarters`,
  `test_unknown_priors_reach_the_onset_quarter`);
- a living man born before January 2, 1913 counts elapsed years to 65 or 1975
  from the year he reaches 62, and each 404.115 cohort gets its column
  (`test_the_404_115_table_gives_each_cohort_its_count`,
  `test_a_man_who_reached_62_before_1973_counts_to_65`);
- a flagged prior stands only on a placement where a special route passes and
  404.130(b) fails
  (`test_a_flagged_prior_needs_paragraph_c_without_paragraph_b`,
  `test_only_a_middle_completion_fits_a_flag`,
  `test_a_flag_every_completion_contradicts_refuses_by_that_name`);
- a listed prior no completion supports refuses by name before any input error
  or UNKNOWN-earnings refusal, and the row keeps its weight
  (`test_an_unsupported_prior_refuses_before_unknown_earnings`,
  `test_past_blindness_begins_a_prior_only_from_1973`,
  `test_a_1965_prior_cannot_rest_on_past_blindness`);
- the note check lists only the tests folder and opens only this note and the
  insured status modules
  (`test_the_note_check_reads_only_the_note_and_insured_modules`).

## Not in scope

No real data, population evaluation, baseline claiming hazard, behavioral
response, benefit amount, administrative entitlement adjudication, medical
finding, original SSN evidence, or totalization agreement is implemented.
This module supplies B6a's statutory insured-status predicate; it does not
establish the empirical risk denominator or admit B6a forecasting. OP8(d)'s
pre-entry convention remains Max's decision. No Axiom differential is
claimed: the companion issue draft requests pinned 413, 414 and 423(c)(1)
rules.
