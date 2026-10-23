"""Track B milestone G: the gross-benefit layer (Python statutory reference).

Verification class: statutory conformance (Track B design revision 3, §3.2
row G). Success admits gross monthly benefits for the supported family
configurations below, and nothing else: no population claim, no payment
timing, no annual earnings or charge determination (R2), and no ARF or
recomputation (R3). The deduction entry points apply caller-declared monthly
deductions before redistributing the maximum (203(a)(4)).
Max's ruling d515 (2026-09-28) adopted §10 question 9's default: a Python
reference now, with Axiom differential checks as diagnostics once a pinned
rule exists. At this module's creation rulespec-us had no 42 U.S.C. 403
encoding, so no Axiom differential is run.

Input boundary: every public argument and declaration field has a schema.
It accepts exact built-in scalars of the declared kind, canonical enum
members by identity, exact declared classes, and exact built-in containers
whose raw contents are checked before reconstruction or hashing. Numeric
encodings become owned Fractions. Callbacks are checked with callable() and
never reconstructed; their results must carry the proper computation seal.
Ordered collections admit only tuple/list and become tuples, preserving
every event and row. Membership collections become frozensets. Evaluators
check provenance, layer and integrity, not freshness or attribution: a
callback may return an earlier genuine result or re-raise a genuine refusal.
The caller declares its family attribution, just as it declares key/weight.
Each public call owns one snapshot; internal helpers consume that snapshot.
This contract does not cover access to private names, monkeypatching modules,
or another thread mutating an input during the call. It admits no broader
security or population claim.

What this layer computes, for one insured worker's record and one month:

1. **Family maximum.** 42 U.S.C. 403(a)(1)-(2): 150/272/134/175 percent of
   the PIA across three bend points, the 1979 amounts $230/$332/$433 scaled
   by NAWI(eligibility year - 2) / NAWI(1977) and rounded to the nearest
   dollar with 50-cent ties upward (215(a)(1)(B)(iii)); the total is
   decreased to the next lower multiple of $0.10. The PIA used is the PIA
   for the year of first eligibility before COLAs, and the COLAs are then
   applied to the maximum (POMS RS 00615.736A.1; 215(i)(2)(A)(ii)(III),
   dime-floored after each increase). Disability families use 403(a)(6):
   the smaller of 85 percent of AIME (or 100 percent of the PIA, if larger)
   and 150 percent of the PIA, for initial DIB entitlement after June 1980
   (POMS RS 00615.740-.742). 403(a)(6) itself states no rounding; the
   result is rounded down to a dime because SSA
   states under "Rules for disability benefits": "The final amount is
   rounded to the next lowest ten cents" (Social Security Bulletin 75(3),
   2015; also Table 2 note), and every COLA on it is dime-floored.
2. **Original benefits.** 402(b)/(c)(2) spouse 1/2, 402(d)(2) child 1/2
   (3/4 of a deceased worker's PIA), 402(e)/(f)(2)(A) widow(er) 100 percent
   of the PIA as determined under (2)(B)-(C) (windexing, or the PIA deemed
   equal to the deceased's credit-increased benefit; RS 00615.301A.3),
   402(g)(2) mother/father 3/4; 402(h)(2) one parent 82.5 percent or
   two entitled parents 75 percent each; each rounded down to a dime.
3. **Family-maximum reduction.** 403(a)(4): every benefit other than the
   worker's own is decreased proportionately (POMS RS 00615.756: OB x
   available / total OB, not to exceed OB, dime-floored). In a life case the
   worker's PIA (never the DRC-increased benefit, RS 00615.695) is deducted
   from the maximum first. Divorced spouses and surviving divorced spouses
   are paid outside the maximum and ignored in everyone else's computation
   (403(a)(3)(C); RS 00615.680-.682).
4. **Dual-entitlement redistribution.** For payment months from October
   1999, other auxiliaries are reduced only by what a dually entitled
   beneficiary is actually paid before any age reduction; the maximum is
   redistributed to the others, each capped at their OB (POMS RS 00615.768,
   the Parisi rule). If every subject beneficiary is dually entitled, the
   rule is disregarded (RS 00615.768C). GN 02603.050C defines the pool as the maximum less the worker PIA,
   deductees' auxiliary age reductions and their partial payable amounts;
   GN 02603.060B.2 settles own RIB age reduction. Own delayed credits and
   an actually limiting RIB-LIM redistribution remain refused.
5. **Age reductions after the family maximum** (RS 00615.754A.1, .210,
   .301B.1.c): spouse 25/36 of 1 percent for 36 months and 5/12 of 1 percent
   beyond, dime-floored (RS 00615.201); widow(er) 28.5 percent spread over
   the reduction period, the reduction amount rounded *up* to a dime (RS
   00615.301); the RIB-LIM afterwards (402(e)(2)(D); RS 00615.320).
   Total possible widow(er) reduction periods are exactly 60, 62, ..., 84
   months (RS 00615.301B.2). In a month with an entitled child in care,
   reduced WIB is raised to the mother/father amount after the maximum,
   when larger (RS 00615.340/.010); the own-benefit offset still applies.
   The caller names that child on the same record or attests False. An
   entitled widow(er) with an entitled child and unknown care status
   refuses. This minimum applies from January 1973; G's payment scope
   starts in January 1983. Its floor months are ARF crediting months at
   FRA (RS 00615.340), recorded by R3 rather than this monthly snapshot.
6. **Dual entitlement.** 402(k)(3)(A): the auxiliary benefit, after 402(q)
   and 403(a), is reduced (not below zero) by the person's own old-age or
   disability benefit after 402(q). For an aged spouse entitled to the own
   benefit in or before the spouse benefit's first month, 402(q)(3)(B)/(C)
   reduce only the excess of the spouse benefit over the own PIA (POMS RS
   00615.250, method C), with delayed credits handled per RS 00615.694. A
   spouse entitled first and to the RIB later keeps the spouse benefit as
   reduced under 402(q)(1) and is paid its excess over the RIB (RS
   00615.240, method B). A widow(er)'s benefit and own benefit are reduced
   independently (method B, 402(q)(3)(E); RS 00615.020A.3). Own-RIB widow
   support begins with cohort 1929, an implementation boundary narrower
   than the January 2, 1928 source boundary (RS 00615.010/.020B); cohort
   1928 remains a known over-refusal pending expanded sequence coverage.
   A spouse with a child in care is never reduced for age (402(q)(5)(A)(ii))
   and is paid
   the excess over the reduced RIB (RS 00615.020A.3 note). This includes
   divorced spouses (RS 00615.010/.201A.2), who remain outside the maximum
   under 403(a)(3)(C). Their current care requires a named entitled child;
   unknown care with a child on the record refuses. Without current care,
   unknown or protected first-entitlement care history refuses when it
   could change the auxiliary payable (RS 00615.201A.2). When both
   histories settle the same payable despite different intermediate age
   rates, the ordinary intermediate rate is diagnostic and its note also
   records the care-exempt rate, preserving any earlier diagnostic note.
7. **Monthly family payment.** Every benefit amount is kept as an exact
   dime multiple; 215(g) rounds each monthly benefit down to a whole dollar.
   Gross means before 203(b) earnings-test deductions and the 1840(a)(1)
   Medicare premium; 215(g) rounds after those, so the whole-dollar gross
   here is not a net check. The ordinary entry points assume no declared
   deduction or suspension. The after-deductions entry points implement
   203(a)(4): deductions can raise the other beneficiaries' rates (POMS
   RS 00615.766; GN 02603.050C-D). R2 determines the monthly charges and
   carries the resulting rates through its annual ledger.

Which record and PIA to supply. The family maximum is computed once, from
the PIA for the year of first eligibility before COLAs (RS 00615.736A.1),
and COLAs then raise it with the PIA. The eligibility year is the year the
worker initially became eligible for old-age or disability benefits, or
died before becoming so eligible (403(a)(2)(A)-(B)), except that a worker
entitled to DIB in any of the 12 months before eligibility or death keeps
the DIB eligibility year (403(a)(2)(D)). The
403(a)(6) disability maximum applies only while DIB entitlement continues;
when the DIB converts to a RIB or the worker dies, build a retirement or
survivor record, whose maximum is the ordinary AIME maximum (RS
00615.742.2).

All arithmetic is exact (``fractions.Fraction``). SSA requires fractions,
not decimal equivalents, because decimals often yield an answer 10 cents
lower (POMS RS 00615.005B). Statutory rates are cross-checked at use
against the repository's parameter bundle (``ss.params.SSAParameters``,
loaded from policyengine-us), rejecting non-finite or mismatched rates
with InvalidFamilyInput (a ValueError subclass) before coverage refusals. The exact
statutory fraction is then used; NAWI, full retirement ages and
delayed-credit rates come from that bundle and must be finite when used.
Delayed-credit months run from full retirement age to age 70
(402(w)(2)(A)), at most ``840 - FRA`` months for each cohort (POMS RS
00615.692E); the bundle's four-year ``max_delayed_months`` is not used,
because it is short for births 1917-1942. Credits for births before 1917
are refused: 402(w)(6)(A) gives them 1/12 of 1 percent a month, and the
bundle does not.

Unsupported configurations raise :class:`FamilyConfigurationUnsupported`
(code ``FAMILY_CONFIG_UNSUPPORTED``, design §7) and never fall back to a
single-worker computation. :func:`household_benefits` is the integration
entry point: it computes every record in a household together and refuses
a person entitled as an auxiliary on more than one record (403(a)(3)(A)
combined maximums, RS 00615.768A), so a multi-worker family cannot be
computed one record at a time by accident. :func:`family_benefits`
computes one record only when the caller passes ``standalone=True``.
Input errors (:class:`InvalidFamilyInput`) are reported before any
coverage refusal, so :func:`evaluate_family` never counts an invalid row as
a coverage gap. Constructors and entry points share one field-validation
layer, including nested declarations, enum classes, calendar/cohort years,
exact integer/Boolean types and all existing cross-field checks. Public
result, refusal and outcome types are sealed with the package-private
Track B capability: each layer's computation creates its own types, and
direct construction, replacement or copying is an input error. Every layer
refuses through a declared FamilyConfigurationUnsupported subclass bound
to exactly its own reason enum. The shared denominator counts all sealed
layer outcomes; G money consumers and the 403(a)(5) guard require G results.
Sealing validates nested fields and derivable accounting identities;
consumers check provenance and unchanged fields before aggregation or guard
changes. Sealed values reject copy and every pickle protocol; persist
declared inputs and recompute. A shared boundary rejects numeric subclasses
and recursively rebuilds declarations through validating constructors. Guard
history and public state snapshots are detached. Every exported helper
validates its arguments before a coverage refusal. Invalid
outcome metadata is checked before invoking a computation; invalid monthly
inputs leave every savings-clause guard unchanged. Built and direct records
share refusal precedence: eligibility year, record conditions, initial DIB
history, then any remaining deferred refusal. All supplied birth years for a person, including their own
worker record, must agree; the household carries that cohort into every
own and auxiliary check (402(q)(6); RS 00615.003/.010) using immutable
copies. ``RecordState.worker_birth_year`` preserves the insured person's
cohort for every record kind, independently of own-benefit entitlement.
:func:`evaluate_family`, :func:`count_family_outcomes` and
the weighted aggregates keep unsupported rows in every denominator and
block totals that would need them.

Pub. L. 118-273 repealed GPO and WEP for benefits payable for months after
December 2023 (GN 02608.100; RS 00605.360). GPO flags are refused only
through December 2023. G takes the PIA as input: the caller supplies a
WEP-affected PIA before January 2024 and the regular-formula PIA from that
month, rebuilding the maximum from that eligibility-year PIA and COLAs.

Birth-year inputs denote SSA cohorts from January 2 through January 1 of
the following calendar year. A beneficiary has one effective cohort, from
either ``Beneficiary.birth_year`` or ``OwnBenefit.birth_year``; supplied
years must agree. That cohort bounds both own-RIB and auxiliary reduction
months before any coverage refusal (402(q)(6); RS 00615.003/.010), and fixes
the widow(er)'s RS 00615.301B.2 period, including every boundary cohort.
Normalization uses immutable copies and does not change the caller's inputs.

An own RIB with positive PIA and reduction months refuses for a known
cohort before 1916: first entitlement could precede January 1978, requiring
the reduction and PIA money history in RS 00615.005C.2. Reduced spouse
benefits likewise need that history before cohort 1916. Widow(er)s need
it before cohort 1928: DWB can begin at 50 and convert to aged WIB at FRA
(RS 00615.310A), and the inputs do not exclude that prior entitlement.
The specific post-1983 DWB .715 instruction in RS 00615.301B.1.e is an
alternative reading to the general historical-money rule; these known
historical cases conservatively refuse pending a ruling.

The inputs carry current rates and months after any ARF, which cannot
establish initial entitlement or money history. Zero reductions and rates,
current care exemptions, and amounts settled across a conservative full
historical-rate interval need no missing history. The interval is a
sufficient settlement check, not a claim that every endpoint is an
attainable historical award. Subject rates must also settle before the own
offset, because 403(a)(5) protects that amount. Omitted cohorts retain the
current-formula domain only; they do not establish statutory conformance
for an undated historical award.

RS 00615.712 protects survivors entitled for May 1978 from reductions due
to a widow(er)'s deceased-worker delayed credits. Protected cases are
refused. Direct survivor snapshots without eligibility metadata require
``widow_drc_savings_clause=False`` to attest that the clause cannot apply;
unknown history is refused separately. Current eligibility from 1983 is
insufficient when an earlier DIB could allow May 1978 entitlement
(RS 00615.736B.2b): an omitted first DIB date is unknown history. When a
subject widow(er)'s OB exceeds the death PIA and another survivor is
subject to the maximum, require the explicit False attestation or a known
first-ever DIB date after May 1978, in both built and direct snapshots.

The default 203(a)(5) reading follows SSA's operational procedure (d1338;
RS 00630.400): a qualifying prior month needs a binding maximum, two or
more entitled persons and an age reduction; the next month's PIA increase
must itself lower family payment. SavingsClauseGuard computes the protected
life-case rates, without changing formula FMAX, and carries the protection
under RS 00615.801B.2. Active-protection membership changes and payment
procedures not settled by the capture refuse by name. The explicit
SavingsClauseReading.LITERAL_REFUSAL switch retains the earlier broad
cross-month refusal reading. Both readings preserve unknown-history refusals.

"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from inspect import unwrap as _unwrap
from types import MappingProxyType

from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.track_b._provenance import (
    _RESULT_TYPES,
    InvalidFamilyInput,
    _check_denominator_reason,
    _check_outcome,
    _check_reason,
    _check_refusal,
    _check_seal,
    _checked_instance_dict,
    _checked_public_methods,
    _computed,
    _construct_declared,
    _declared_input,
    _detached_result,
    _exact_number,
    _has_declared_type,
    _InvalidInputType,
    _replace_declared,
    _sealed_refusal,
    _sealed_result,
    _SealedOutcome,
    _SealedResult,
    _validated_entry,
)

__all__ = [
    "BASE_NAWI_YEAR",
    "DI_MAXIMUM_FIRST_ENTITLEMENT",
    "FAMILY_MAXIMUM_BASE_BEND_POINTS",
    "FAMILY_MAXIMUM_PERCENTS",
    "FIRST_SUPPORTED_DELAYED_CREDIT_BIRTH_YEAR",
    "FIRST_SUPPORTED_ELIGIBILITY_YEAR",
    "FIRST_SUPPORTED_PAYMENT_MONTH",
    "GROSS_BENEFITS_VERSION",
    "PARISI_FIRST_PAYMENT_MONTH",
    "Beneficiary",
    "BeneficiaryBenefit",
    "BeneficiaryCondition",
    "BenefitDeduction",
    "DeductionReason",
    "FamilyBenefits",
    "FamilyConfigurationUnsupported",
    "FamilyDenominator",
    "FamilyKind",
    "FamilyOutcome",
    "FamilyTargetBlocked",
    "HouseholdBenefits",
    "HouseholdRecord",
    "InvalidFamilyInput",
    "OwnBenefit",
    "OwnBenefitKind",
    "RecordCondition",
    "RecordState",
    "Role",
    "SavingsClauseGuard",
    "SavingsClauseReading",
    "StatutoryRates",
    "UnsupportedReason",
    "WorkerRecord",
    "YearMonth",
    "applicable_cola_percents",
    "ceil_dime",
    "check_household_records",
    "count_family_outcomes",
    "delayed_credit_window_months",
    "disability_family_maximum",
    "evaluate_family",
    "family_benefits",
    "family_benefits_after_deductions",
    "family_maximum_bend_points",
    "family_maximum_formula",
    "floor_dime",
    "household_benefits",
    "household_benefits_after_deductions",
    "household_month_outcome",
    "increase_by_colas",
    "original_benefit",
    "maximum_redistribution_rates",
    "own_monthly_benefit",
    "record_state",
    "retirement_survivor_family_maximum",
    "savings_clause_total",
    "spouse_age_reduced",
    "spouse_reduction_fraction",
    "statutory_rates",
    "survivor_reduction_fraction",
    "survivor_age_reduced",
    "weighted_mean_record_total",
    "weighted_record_total",
    "whole_dollars",
    "widow_reduction_period_months",
    "worker_age_adjusted",
    "worker_reduction_fraction",
]

GROSS_BENEFITS_VERSION = "track-b-g-v2"

# ---------------------------------------------------------------------------
# Statutory constants (each cited; none is a fitted or chosen value)
# ---------------------------------------------------------------------------

#: 42 U.S.C. 403(a)(2)(A): the 1979 family-maximum bend points.
FAMILY_MAXIMUM_BASE_BEND_POINTS = (230, 332, 433)
#: 42 U.S.C. 403(a)(1)(A)-(D): 150, 272, 134 and 175 percent.
FAMILY_MAXIMUM_PERCENTS = (
    Fraction(150, 100),
    Fraction(272, 100),
    Fraction(134, 100),
    Fraction(175, 100),
)
#: 403(a)(2)(B) via 215(a)(1)(B)(ii): the base-year wage index.
BASE_NAWI_YEAR = 1977
#: 42 U.S.C. 403(a)(6): 85 percent of AIME, floor 100 and cap 150 percent
#: of the PIA.
_DI_AIME_SHARE = Fraction(85, 100)
_DI_PIA_CAP = Fraction(150, 100)
#: POMS RS 00615.740B: the 1980 disability maximum applies only to initial
#: DIB entitlement after June 1980.
DI_MAXIMUM_FIRST_ENTITLEMENT = (1980, 7)
#: Eligibility years before 1983 are refused: a maximum fixed before June
#: 1982 was rounded up to the next dime (POMS RS 00615.736B.3 examples;
#: RS 00615.201B.1.c), and pre-1979 eligibility used the table maximums.
FIRST_SUPPORTED_ELIGIBILITY_YEAR = 1983
#: Benefits for months after May 1982 round reductions down to the dime
#: (RS 00615.101, .201); this layer computes months from January 1983.
FIRST_SUPPORTED_PAYMENT_MONTH = (1983, 1)
#: POMS RS 00615.768D.2: the dual-entitlement redistribution applies to
#: benefits payable for 10/99 or later (First Circuit cases earlier are
#: not modeled; months before 10/99 that need the rule are refused).
PARISI_FIRST_PAYMENT_MONTH = (1999, 10)

#: 402(w)(6)(A): 1/12 of 1 percent a month for a person first eligible
#: before 1979, that is, born before 01/02/1917 (POMS RS 00615.692D). The
#: parameter bundle's schedule starts at 3 percent a year, so credits for
#: earlier births are refused.
FIRST_SUPPORTED_DELAYED_CREDIT_BIRTH_YEAR = 1917

_DIME = Fraction(1, 10)
_HALF = Fraction(1, 2)
#: 402(w)(2)(A): increment months end before the month of attaining 70.
_AGE_70_MONTHS = 70 * 12
#: POMS RS 00615.692E: the longest window on the chart (births before
#: 02/02/12), a bound on every cohort's delayed-credit months.
_MAX_DELAYED_CREDIT_MONTHS = 84
_MAX_WORKER_REDUCTION_MONTHS = 60
_MAX_SPOUSE_REDUCTION_MONTHS = 60
#: POMS RS 00615.301B.2: FRA rises in two-month increments from 65 to
#: 67, so total possible reduction months are exactly 60, 62, ..., 84.
_SURVIVOR_PERIODS = frozenset(range(60, 85, 2))
#: POMS RS 00615.020B chart: a widow(er) born before 1/2/1928 who took
#: widow(er)'s benefits before 62 and then RIB carries a reduction over
#: (method D). RS 00615.010 admits usual RIB reduction from 1/2/1928.
#: G retains its validated implementation boundary of cohort 1929 pending
#: expanded sequence coverage; cohort 1928 is a known over-refusal, not
#: a method-D source requirement or ambiguity in the SSA cohort input.
_FIRST_METHOD_B_WIDOW_BIRTH_YEAR = 1929


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class UnsupportedReason(Enum):
    """Why a statutory configuration is outside this layer (design §7)."""

    ELIGIBILITY_BEFORE_1983 = "eligibility_before_1983"
    PAYMENT_MONTH_BEFORE_1983 = "payment_month_before_1983"
    DI_ENTITLEMENT_BEFORE_JULY_1980 = "di_entitlement_before_july_1980"
    COMBINED_FAMILY_MAXIMUM = "combined_family_maximum"
    DEEMED_SPOUSE = "deemed_or_putative_spouse"
    PARENT_BENEFIT = "parent_benefit"
    DISABLED_WIDOW_UNDER_60 = "disabled_widow_before_1984"
    DIB_GUARANTEE_PIA = "dib_guarantee_pia"
    DIB_AFTER_REDUCED_RIB = "dib_after_reduced_rib"
    WORKERS_COMPENSATION_OFFSET = "workers_compensation_offset"
    GOVERNMENT_PENSION_OFFSET = "government_pension_offset"
    ADMINISTRATIVE_FINALITY = "administrative_finality"
    DUAL_ENTITLEMENT_SEQUENCE = "dual_entitlement_sequence"
    PARISI_AMBIGUOUS = "parisi_redistribution_ambiguous"
    PARISI_BEFORE_OCTOBER_1999 = "parisi_before_october_1999"
    INDEPENDENT_DIVORCED_SPOUSE = "independently_entitled_divorced_spouse"
    NON_AIME_FORMULA_PIA = "non_aime_formula_pia"
    MULTIPLE_AUXILIARY_RECORDS = "multiple_auxiliary_records"
    SAVINGS_CLAUSE = "savings_clause_403a5"
    SAVINGS_CLAUSE_HISTORY_UNKNOWN = "savings_clause_history_unknown"
    SAVINGS_CLAUSE_MEMBERSHIP_CHANGE = "savings_clause_membership_change"
    SAVINGS_CLAUSE_RATE_PROCEDURE = "savings_clause_rate_procedure"
    WIDOW_DRC_SAVINGS_CLAUSE = "widow_drc_savings_clause"
    WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN = (
        "widow_drc_savings_clause_history_unknown"
    )
    WIDOW_CHILD_IN_CARE_UNKNOWN = "widow_child_in_care_unknown"
    DIVORCED_SPOUSE_CHILD_IN_CARE_UNKNOWN = (
        "divorced_spouse_child_in_care_unknown"
    )
    DIVORCED_SPOUSE_CARE_HISTORY = "divorced_spouse_care_history"
    DELAYED_CREDITS_BEFORE_1917 = "delayed_credits_born_before_1917"
    OWN_RIB_HISTORY_BEFORE_1978 = "own_rib_history_before_1978"
    REDUCED_BENEFIT_HISTORY_BEFORE_1978 = "reduced_benefit_history_before_1978"
    PRISONER_SUSPENSION = "prisoner_suspension"
    DRUG_ADDICTION_SUSPENSION = "drug_addiction_suspension"
    FOREIGN_WORK_DEDUCTION = "foreign_work_deduction"
    PENALTY_DEDUCTION = "penalty_deduction"
    MARITIME_DEDUCTION = "maritime_deduction"
    ELECTION_CERTIFICATE_SUSPENSION = "election_certificate_suspension"
    DEDUCTION_AGE_WORK_INTERACTION = "deduction_age_work_interaction"


@_sealed_refusal(UnsupportedReason)
class FamilyConfigurationUnsupported(_SealedResult, Exception):
    """``FAMILY_CONFIG_UNSUPPORTED``: a configuration G cannot compute.

    Rows raising this stay in every denominator (use
    :func:`evaluate_family` and :func:`count_family_outcomes`); a target
    that needs them is blocked (:class:`FamilyTargetBlocked`).
    G creates this exact class with UnsupportedReason. R2 and R3 declare
    subclasses bound to their own exact reason enums. All layers catch this
    common family; consumers reject altered or unsealed exceptions.
    """

    code = "FAMILY_CONFIG_UNSUPPORTED"

    def __init__(
        self,
        reason: UnsupportedReason,
        detail: str,
        *,
        beneficiary_id: str | None = None,
        record_id: str | None = None,
    ):
        _check_reason(self, reason)
        _input_text(detail, "detail")
        for label, identifier in (
            ("beneficiary_id", beneficiary_id),
            ("record_id", record_id),
        ):
            if identifier is not None:
                _input_text(identifier, label)
        self.reason = reason
        self.detail = detail
        self.beneficiary_id = beneficiary_id
        self.record_id = record_id
        where = f" (beneficiary {beneficiary_id})" if beneficiary_id else ""
        super().__init__(f"{self.code}[{reason.value}]{where}: {detail}")


class FamilyTargetBlocked(RuntimeError):
    """An aggregate would need rows whose configuration is unsupported."""


# ---------------------------------------------------------------------------
# Exact money helpers
# ---------------------------------------------------------------------------
def _exact(value, label):
    """Use owned exact money without reconstructing it inside computation."""
    if type(value) is Fraction:
        return value
    return _exact_number(value, label)


def _dimes(value: object, label: str) -> Fraction:
    """A nonnegative amount that the statute keeps in whole dimes."""
    amount = _exact(value, label)
    if amount.numerator < 0:
        raise InvalidFamilyInput(f"{label} must be nonnegative")
    if (amount.numerator * 10) % amount.denominator:
        raise InvalidFamilyInput(f"{label} must be a multiple of $0.10")
    return amount


def _input_type(value: object, expected: type, label: str) -> None:
    if type(value) is not expected:
        raise _InvalidInputType(f"{label} must be an {expected.__name__}")


def _input_year(value: object, label: str) -> None:
    _input_type(value, int, label)
    if not 1 <= value <= 9999:
        raise InvalidFamilyInput(f"{label} must be between 1 and 9999")


def _input_text(value: object, label: str) -> None:
    _input_type(value, str, label)
    if not value:
        raise InvalidFamilyInput(f"{label} must be a nonempty str")


def _input_sequence(value: object, label: str) -> None:
    if type(value) is not tuple and type(value) is not list:
        raise _InvalidInputType(f"{label} must be a sequence")


def _input_iterable(value: object, label: str) -> tuple:
    """Materialize an iterable before validation, without treating text as rows."""
    if isinstance(value, (str, bytes, Mapping)):
        raise _InvalidInputType(f"{label} must be an iterable of values")
    try:
        return tuple(value)
    except TypeError as error:
        raise _InvalidInputType(f"{label} must be iterable") from error


def _input_conditions(value: object, enum: type) -> None:
    if not _has_declared_type(value, (set, frozenset, tuple, list)):
        raise _InvalidInputType("conditions must be a collection of enums")
    for condition in value:
        _input_type(condition, enum, "condition")


def _checked_input(value, expected: type, label: str):
    """Check the type of an already-owned declaration or a sealed result.

    Public boundaries have already detached declarations recursively. This
    private helper deliberately does not take another snapshot.
    """
    _input_type(value, expected, label)
    if type(value) in _RESULT_TYPES:
        _check_seal(value)
    return value


def _validated_refusal(error) -> FamilyConfigurationUnsupported:
    """Require a genuine, unaltered G refusal before recording coverage."""
    _input_type(error, FamilyConfigurationUnsupported, "unsupported")
    _check_seal(error)
    return error


def _nonnegative_integer(value, label: str) -> None:
    _input_type(value, int, label)
    if value < 0:
        raise InvalidFamilyInput(f"{label} must be nonnegative")


def _result_money_fields(value, names: tuple[str, ...]) -> None:
    """Normalize exact nonnegative dime amounts in immutable results."""
    for name in names:
        object.__setattr__(
            value, name, _dimes(object.__getattribute__(value, name), name)
        )


def _optional_result_money(value, amount_name: str, whole_name: str) -> None:
    amount, whole = object.__getattribute__(
        value, amount_name
    ), object.__getattribute__(value, whole_name)
    if amount is None:
        if whole is not None:
            raise InvalidFamilyInput(f"{whole_name} needs {amount_name}")
        return
    amount = _dimes(amount, amount_name)
    _nonnegative_integer(whole, whole_name)
    if whole != math.floor(amount):
        raise InvalidFamilyInput(f"{whole_name} must floor {amount_name}")
    object.__setattr__(value, amount_name, amount)


def _validate_input_fields(value) -> None:
    """The shared public-declaration schema, before any coverage refusal.

    Monetary inputs retain the documented exact-number conversions. Enums,
    booleans and integers require their exact classes. Calendar and cohort
    years use datetime's 1..9999 domain. Parameter-dependent month bounds
    and family/household consistency run after cohort resolution.
    """
    kind = type(value)
    # Public construction/snapshot already checked this exact declaration's
    # storage. Internal validation does not redispatch public attribute APIs.
    read = object.__getattribute__.__get__(value)
    if kind is YearMonth:
        _input_year(read("year"), "year")
        _input_type(read("month"), int, "month")
        if not 1 <= read("month") <= 12:
            raise InvalidFamilyInput("month must be 1-12")
        return
    if kind is OwnBenefit:
        _input_type(read("kind"), OwnBenefitKind, "kind")
        _dimes(read("pia"), "own PIA")
        for name in ("reduction_months", "delayed_credit_months"):
            number = read(name)
            _input_type(number, int, name)
            if number < 0:
                raise InvalidFamilyInput(f"{name} must be nonnegative")
        if read("birth_year") is not None:
            _input_year(read("birth_year"), "birth_year")
        return
    if kind is Beneficiary:
        _input_text(read("beneficiary_id"), "beneficiary_id")
        _input_type(read("role"), Role, "role")
        _input_type(read("reduction_months"), int, "reduction_months")
        if read("reduction_period_months") is not None:
            _input_type(
                read("reduction_period_months"), int, "reduction_period_months"
            )
        if read("birth_year") is not None:
            _input_year(read("birth_year"), "birth_year")
        _input_conditions(read("conditions"), BeneficiaryCondition)
        if (
            read("child_in_care") is not None
            and read("child_in_care") is not False
        ):
            _input_text(read("child_in_care"), "child_in_care")
        if read("own_benefit") is not None:
            object.__setattr__(
                value,
                "own_benefit",
                _checked_input(read("own_benefit"), OwnBenefit, "own_benefit"),
            )
        for name in ("own_benefit_first", "first_entitlement_child_in_care"):
            flag = read(name)
            if flag is not None:
                _input_type(flag, bool, name)
        # Role-specific care and OB-basis checks are shared by __post_init__.
        return
    if kind is WorkerRecord or kind is RecordState:
        _input_type(read("kind"), FamilyKind, "kind")
        if read("worker_birth_year") is not None:
            _input_year(read("worker_birth_year"), "worker_birth_year")
        if kind is WorkerRecord or read("eligibility_year") is not None:
            _input_year(read("eligibility_year"), "eligibility_year")
        _input_conditions(read("conditions"), RecordCondition)
        if read("first_dib_entitlement") is not None:
            _checked_input(
                read("first_dib_entitlement"),
                YearMonth,
                "first_dib_entitlement",
            )
        if kind is WorkerRecord:
            _input_sequence(read("cola_percents"), "cola_percents")
            for percent in read("cola_percents"):
                if _exact(percent, "COLA percent") < 0:
                    raise InvalidFamilyInput(
                        "A COLA percent cannot be negative"
                    )
            if read("aime") is not None:
                if not _has_declared_type(read("aime"), (int, Fraction)):
                    raise _InvalidInputType(
                        "AIME must be an int or an integral Fraction"
                    )
                if read("aime") < 0 or Fraction(read("aime")).denominator != 1:
                    raise InvalidFamilyInput(
                        "AIME must be a nonnegative whole dollar"
                    )
            for name in (
                "worker_reduction_months",
                "worker_delayed_credit_months",
            ):
                number = read(name)
                _input_type(number, int, name)
                if number < 0:
                    raise InvalidFamilyInput(f"{name} must be nonnegative")
        else:
            _input_text(read("source"), "source")
            if read("worker") is not None:
                object.__setattr__(
                    value,
                    "worker",
                    _checked_input(read("worker"), OwnBenefit, "worker"),
                )
            if read("widow_drc_savings_clause") is not None:
                _input_type(
                    read("widow_drc_savings_clause"),
                    bool,
                    "widow_drc_savings_clause",
                )
            if read("deferred_refusal") is not None:
                _input_type(
                    read("deferred_refusal"), tuple, "deferred_refusal"
                )
                if len(read("deferred_refusal")) != 2:
                    raise InvalidFamilyInput(
                        "deferred_refusal needs a reason and detail"
                    )
                reason, detail = read("deferred_refusal")
                _input_type(
                    reason, UnsupportedReason, "deferred_refusal reason"
                )
                _input_text(detail, "deferred_refusal detail")
        return
    if kind is HouseholdRecord:
        _input_text(read("worker_id"), "worker_id")
        object.__setattr__(
            value, "state", _checked_input(read("state"), RecordState, "state")
        )
        _input_sequence(read("beneficiaries"), "beneficiaries")
        object.__setattr__(
            value,
            "beneficiaries",
            tuple(
                _checked_input(b, Beneficiary, "beneficiary")
                for b in read("beneficiaries")
            ),
        )
        return
    raise _InvalidInputType("Unknown input declaration")


@_validated_entry
def floor_dime(amount: Fraction) -> Fraction:
    """Decrease to the next lower multiple of $0.10 (exact)."""
    amount = _exact(amount, "amount")
    return Fraction(math.floor(amount * 10), 10)


@_validated_entry
def ceil_dime(amount: Fraction) -> Fraction:
    """Increase to the next higher multiple of $0.10 (exact)."""
    amount = _exact(amount, "amount")
    return Fraction(math.ceil(amount * 10), 10)


@_validated_entry
def whole_dollars(amount: Fraction) -> int:
    """42 U.S.C. 415(g): round a monthly benefit down to a whole dollar."""
    amount = _exact(amount, "amount")
    if amount < 0:
        raise InvalidFamilyInput("A benefit amount cannot be negative")
    return math.floor(amount)


def _nearest_dollar_ties_up(amount: Fraction) -> int:
    """215(a)(1)(B)(iii): nearest $1; a multiple of $0.50 rounds up."""
    return math.floor(amount + _HALF)


@_declared_input
@dataclass(frozen=True, order=True)
class YearMonth:
    """A calendar month (the benefit month being computed)."""

    year: int
    month: int

    def __post_init__(self):
        _validate_input_fields(self)

    @_validated_entry
    def as_tuple(self) -> tuple[int, int]:
        month = _checked_input(self, YearMonth, "month")
        return (month.year, month.month)

    @_validated_entry
    def __str__(self) -> str:
        month = _checked_input(self, YearMonth, "month")
        return f"{month.year:04d}-{month.month:02d}"


# ---------------------------------------------------------------------------
# Statutory rates, cross-checked against the repository's parameter bundle
# ---------------------------------------------------------------------------
@_declared_input
@dataclass(frozen=True)
class StatutoryRates:
    """Exact 402(q), 402(b)-(g) and 402(e)(2)(D) fractions."""

    worker_first: Fraction
    worker_later: Fraction
    worker_bracket_months: int
    spouse_first: Fraction
    spouse_later: Fraction
    spouse_bracket_months: int
    survivor_max_reduction: Fraction
    rib_lim_share: Fraction
    spouse_share: Fraction
    widow_share: Fraction
    pe_us_revision: str

    def __post_init__(self):
        for name in (
            "worker_first",
            "worker_later",
            "spouse_first",
            "spouse_later",
            "survivor_max_reduction",
            "rib_lim_share",
            "spouse_share",
            "widow_share",
        ):
            value = _exact(getattr(self, name), name)
            if not 0 <= value <= 1:
                raise InvalidFamilyInput(f"{name} must be between 0 and 1")
            object.__setattr__(self, name, value)
        for name in ("worker_bracket_months", "spouse_bracket_months"):
            months = getattr(self, name)
            _input_type(months, int, name)
            if not 1 <= months <= _MAX_WORKER_REDUCTION_MONTHS:
                raise InvalidFamilyInput(f"{name} must be between 1 and 60")
        _input_text(self.pe_us_revision, "pe_us_revision")


_STATUTE = {
    # 402(q)(1)(A): 5/9 of 1 percent; 5/12 of 1 percent beyond 36 months
    # (POMS RS 00615.101B.1).
    "worker_first": Fraction(5, 900),
    "worker_later": Fraction(5, 1200),
    # 402(q)(1)(A): 25/36 of 1 percent; 5/12 of 1 percent beyond 36 months
    # (POMS RS 00615.201B.1).
    "spouse_first": Fraction(25, 3600),
    "spouse_later": Fraction(5, 1200),
    # A 28.5 percent maximum widow(er) reduction for every FRA: 402(q)(1)(A)'s
    # 19/40 of 1 percent over the 60 months from 60 to 65, kept at 28.5
    # percent as FRA rose (POMS RS 00615.301B.1).
    "survivor_max_reduction": Fraction(285, 1000),
    # 402(e)(2)(D)(ii): 82 1/2 percent.
    "rib_lim_share": Fraction(165, 200),
    # 402(b)(2)/(c)(2): one-half.
    "spouse_share": Fraction(1, 2),
    # 402(e)(2)(A)/(f)(3)(A): the PIA itself.
    "widow_share": Fraction(1),
}
_RATE_TOLERANCE = 1e-7


def _parameter_number(value: object, label: str):
    """Validate supplied bundle numbers without changing their encoding."""
    if type(value) is float:
        if not math.isfinite(value):
            raise InvalidFamilyInput(f"{label} must be finite")
        return value
    return _exact(value, label)


def _check_parameter_series(params: SSAParameters) -> None:
    """Check the G-consumed series before coverage, including unused entries.

    Missing observations remain the documented KeyError at lookup. Supplied
    observations must be valid even on a historically refused computation.
    Other SSAParameters fields are outside G's arithmetic surface.
    """
    _input_type(params, SSAParameters, "params")
    if not isinstance(params.nawi, Mapping):
        raise _InvalidInputType("nawi must be a mapping")
    for year, value in params.nawi.items():
        _input_year(year, "NAWI year")
        if _parameter_number(value, "NAWI") <= 0:
            raise InvalidFamilyInput("NAWI must be positive")
    for name in ("fra_months_by_birth_year", "delayed_credit_by_birth_year"):
        schedule = getattr(params, name)
        _input_sequence(schedule, name)
        previous = 0
        for entry in schedule:
            _input_sequence(entry, f"{name} entry")
            if len(entry) != 2:
                raise InvalidFamilyInput(f"{name} entry needs year and value")
            year, value = entry
            _input_year(year, f"{name} year")
            if year <= previous:
                raise InvalidFamilyInput(f"{name} years must increase")
            previous = year
            number = _parameter_number(value, name)
            if name == "fra_months_by_birth_year":
                _input_type(value, int, "Full retirement age months")
                if not 756 <= number <= 804:
                    raise InvalidFamilyInput("FRA months must be in 756..804")
            elif not 0 <= number <= 1:
                raise InvalidFamilyInput("DRC annual rate must be in 0..1")


def _agrees(observed: float, expected: Fraction, label: str) -> None:
    try:
        value = float(_exact(observed, label))
    except _InvalidInputType:
        raise
    except (InvalidFamilyInput, OverflowError) as error:
        raise InvalidFamilyInput(
            f"Parameter bundle {label}={observed} disagrees with the "
            f"statutory {expected}; refusing to compute gross benefits."
        ) from error
    if (
        not math.isfinite(value)
        or abs(value - float(expected)) > _RATE_TOLERANCE
    ):
        raise InvalidFamilyInput(
            f"Parameter bundle {label}={observed} disagrees with the "
            f"statutory {expected}; refusing to compute gross benefits."
        )


@_validated_entry
def statutory_rates(params: SSAParameters) -> StatutoryRates:
    """Cross-check the bundle against the statute; return exact fractions.

    policyengine-us stores 5/9 of 1 percent as the decimal 0.00555556, and
    SSA computes with the fraction (POMS RS 00615.005B), so the fraction is
    what is used once the bundle is confirmed to encode the same rate.
    Non-finite or mismatched rates raise InvalidFamilyInput, an error rather
    than a coverage refusal. Family and household entry points check them
    before any coverage refusal.
    """
    _input_type(params, SSAParameters, "params")
    _check_parameter_series(params)
    _input_text(params.pe_us_revision, "pe_us_revision")
    for name in ("early_monthly_rates", "spousal_early_monthly_rates"):
        pair = getattr(params, name)
        _input_sequence(pair, name)
        if len(pair) != 2:
            raise InvalidFamilyInput(f"{name} must contain two rates")
    worker_first, worker_later = params.early_monthly_rates
    _agrees(worker_first, _STATUTE["worker_first"], "early_monthly_rates[0]")
    _agrees(worker_later, _STATUTE["worker_later"], "early_monthly_rates[1]")
    spouse_first, spouse_later = params.spousal_early_monthly_rates
    _agrees(spouse_first, _STATUTE["spouse_first"], "spousal rate[0]")
    _agrees(spouse_later, _STATUTE["spouse_later"], "spousal rate[1]")
    _agrees(
        params.survivor_reduction_floor,
        1 - _STATUTE["survivor_max_reduction"],
        "survivor_reduction_floor",
    )
    _agrees(params.rib_lim_pia_share, _STATUTE["rib_lim_share"], "rib_lim")
    _agrees(params.spousal_pia_share, _STATUTE["spouse_share"], "spouse")
    _agrees(params.survivor_pia_share, _STATUTE["widow_share"], "widow")
    for name in (
        "early_first_bracket_months",
        "spousal_early_first_bracket_months",
    ):
        _input_type(getattr(params, name), int, name)
        if getattr(params, name) != 36:
            raise InvalidFamilyInput(f"{name} must be 36 (402(q))")
    # Source conflict us:oasdi-reduction-exact-fractions
    return _construct_declared(
        StatutoryRates,
        worker_first=_STATUTE["worker_first"],
        worker_later=_STATUTE["worker_later"],
        worker_bracket_months=36,
        spouse_first=_STATUTE["spouse_first"],
        spouse_later=_STATUTE["spouse_later"],
        spouse_bracket_months=36,
        survivor_max_reduction=_STATUTE["survivor_max_reduction"],
        rib_lim_share=_STATUTE["rib_lim_share"],
        spouse_share=_STATUTE["spouse_share"],
        widow_share=_STATUTE["widow_share"],
        pe_us_revision=params.pe_us_revision,
    )


# ---------------------------------------------------------------------------
# Family maximum
# ---------------------------------------------------------------------------
def _nawi(params: SSAParameters, year: int) -> Fraction:
    _input_type(params, SSAParameters, "params")
    if not isinstance(params.nawi, Mapping):
        raise _InvalidInputType("nawi must be a mapping")
    if year not in params.nawi:
        raise KeyError(
            f"NAWI for {year} is not in the parameter bundle "
            f"(revision {params.pe_us_revision})."
        )
    amount = _exact(params.nawi[year], f"NAWI({year})")
    if amount <= 0:
        raise InvalidFamilyInput("NAWI must be positive")
    return amount


@_validated_entry
def family_maximum_bend_points(
    eligibility_year: int, params: SSAParameters
) -> tuple[int, int, int]:
    """403(a)(2): the three family-maximum bend points for a year.

    Each 1979 amount times NAWI(year - 2) / NAWI(1977), rounded to the
    nearest dollar with 50-cent ties upward (215(a)(1)(B)(iii)).
    """
    _input_year(eligibility_year, "eligibility_year")
    _check_parameter_series(params)
    if eligibility_year < 1979:
        raise InvalidFamilyInput(
            "The 403(a)(1) formula starts with 1979 eligibility"
        )
    ratio = _nawi(params, eligibility_year - 2) / _nawi(params, BASE_NAWI_YEAR)
    first, second, third = (
        _nearest_dollar_ties_up(base * ratio)
        for base in FAMILY_MAXIMUM_BASE_BEND_POINTS
    )
    return first, second, third


@_validated_entry
def family_maximum_formula(
    pia: object, eligibility_year: int, params: SSAParameters
) -> Fraction:
    """403(a)(1)(A)-(D) before rounding: the exact formula amount."""
    amount = _dimes(pia, "PIA")
    points = _family_maximum_bend_points_validated(eligibility_year, params)
    lower = (0, *points)
    upper = (*points, None)
    total = Fraction(0)
    for percent, low, high in zip(
        FAMILY_MAXIMUM_PERCENTS, lower, upper, strict=True
    ):
        top = amount if high is None else min(amount, Fraction(high))
        if top > low:
            total += percent * (top - low)
    return total


@_validated_entry
def retirement_survivor_family_maximum(
    pia: object, eligibility_year: int, params: SSAParameters
) -> Fraction:
    """403(a)(1): the retirement/survivor maximum at eligibility.

    ``pia`` is the PIA for the year of first eligibility before any COLA
    (POMS RS 00615.736A.1). The result is dime-floored (403(a)(1), last
    sentence). Apply COLAs with :func:`increase_by_colas`.
    """
    amount = _dimes(pia, "PIA")
    _input_year(eligibility_year, "eligibility_year")
    _statutory_rates_validated(params)
    _require_supported_eligibility(eligibility_year)
    return _floor_dime_validated(
        _family_maximum_formula_validated(amount, eligibility_year, params)
    )


@_validated_entry
def disability_family_maximum(pia: object, aime: object) -> Fraction:
    """403(a)(6): min(max(85% AIME, PIA), 150% PIA), dime-floored.

    Both amounts are those before COLAs (POMS RS 00615.742.1); apply the
    intervening COLAs afterwards with :func:`increase_by_colas`.
    """
    amount = _dimes(pia, "PIA")
    earnings = _exact(aime, "AIME")
    if earnings < 0 or earnings.denominator != 1:
        raise InvalidFamilyInput("AIME must be a nonnegative whole dollar")
    # Source conflict us:oasdi-disability-family-maximum-rounding
    return _floor_dime_validated(
        min(max(_DI_AIME_SHARE * earnings, amount), _DI_PIA_CAP * amount)
    )


@_validated_entry
def increase_by_colas(amount: object, percents: Sequence[object]) -> Fraction:
    """215(i)(2)(A)(ii): apply each COLA in order, dime-floored each time.

    ``percents`` are percentages (``"2.8"`` for a 2.8 percent COLA), exact
    or float. A zero COLA leaves the amount unchanged; negative COLAs do
    not exist under 215(i) and are refused. Only tuple/list event sequences
    are admitted; sets cannot express statutory order and multiplicity.
    """
    value = _dimes(amount, "amount")
    for index, percent in enumerate(_input_iterable(percents, "percents")):
        rate = _exact(percent, f"COLA percent #{index}")
        if rate < 0:
            raise InvalidFamilyInput("A COLA percentage cannot be negative")
        value = _floor_dime_validated(value * (1 + rate / 100))
    return value


@_validated_entry
def applicable_cola_percents(
    eligibility_year: int,
    payment_month: YearMonth,
    december_cola_percent: Mapping[int, object],
) -> tuple[Fraction, ...]:
    """The COLAs that have raised a PIA and maximum by ``payment_month``.

    Increases start with the one effective in December of the eligibility
    year (215(i)(2)(A)(ii)-(iii), the convention
    ``scenario_benefits.increased_pia_path`` already uses); each is
    effective with December of its year. ``december_cola_percent`` maps
    that December's year to the percentage (for example R1's
    ``ret_history.json`` ``december_cola_percent``). A missing year raises
    rather than counting as zero, and an eligibility year after the
    payment month's year is an input error, not an empty list.
    """
    payment_month = _checked_input(payment_month, YearMonth, "payment_month")
    _input_year(eligibility_year, "eligibility_year")
    if not isinstance(december_cola_percent, Mapping):
        raise _InvalidInputType("december_cola_percent must be a mapping")
    validated = {}
    for year, percent in december_cola_percent.items():
        _input_year(year, "COLA year")
        percent = _exact(percent, f"COLA {year}")
        if percent < 0:
            raise InvalidFamilyInput("A COLA percentage cannot be negative")
        validated[year] = percent
    if eligibility_year > payment_month.year:
        raise InvalidFamilyInput(
            f"eligibility year {eligibility_year} is after the payment "
            f"month {_month_text_validated(payment_month)}"
        )
    _require_supported_eligibility(eligibility_year)
    last = payment_month.year - (0 if payment_month.month == 12 else 1)
    percents = []
    for year in range(eligibility_year, last + 1):
        if year not in validated:
            raise KeyError(f"No COLA percentage for December {year}")
        percents.append(validated[year])
    return tuple(percents)


def _require_supported_eligibility(eligibility_year: int) -> None:
    _input_year(eligibility_year, "eligibility_year")
    if eligibility_year < FIRST_SUPPORTED_ELIGIBILITY_YEAR:
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.ELIGIBILITY_BEFORE_1983,
            f"eligibility year {eligibility_year}: maximums fixed before "
            "June 1982 were rounded up to the dime (POMS RS 00615.736B.3) "
            "and pre-1979 eligibility used table maximums; neither is "
            "implemented",
        )


# ---------------------------------------------------------------------------
# Age adjustments (exact fractions, POMS RS 00615.101/.201/.301/.692)
# ---------------------------------------------------------------------------
def _months(value: int, label: str, upper: int) -> int:
    _input_type(value, int, label)
    if not 0 <= value <= upper:
        raise InvalidFamilyInput(f"{label} must be between 0 and {upper}")
    return value


def _worker_reduction(months: int, rates: StatutoryRates) -> Fraction:
    first = min(months, rates.worker_bracket_months)
    later = max(0, months - rates.worker_bracket_months)
    return first * rates.worker_first + later * rates.worker_later


def _spouse_reduction(months: int, rates: StatutoryRates) -> Fraction:
    first = min(months, rates.spouse_bracket_months)
    later = max(0, months - rates.spouse_bracket_months)
    return first * rates.spouse_first + later * rates.spouse_later


@_validated_entry
def worker_reduction_fraction(months: int, params: SSAParameters) -> Fraction:
    """402(q)(1) old-age reduction for ``months`` months (RS 00615.101)."""
    months = _months(months, "months", _MAX_WORKER_REDUCTION_MONTHS)
    return _worker_reduction(months, _statutory_rates_validated(params))


@_validated_entry
def spouse_reduction_fraction(months: int, params: SSAParameters) -> Fraction:
    """402(q)(1) spouse's reduction for ``months`` months (RS 00615.201)."""
    months = _months(months, "months", _MAX_SPOUSE_REDUCTION_MONTHS)
    return _spouse_reduction(months, _statutory_rates_validated(params))


@_validated_entry
def survivor_reduction_fraction(
    months: int, reduction_period_months: int, params: SSAParameters
) -> Fraction:
    """Widow(er)'s reduction: 28.5 percent spread over the period.

    This is the fraction before SSA's rounding of the reduction amount;
    :func:`survivor_age_reduced` applies it to a benefit.
    """
    period = _survivor_period(reduction_period_months)
    months = _months(months, "months", period)
    return (
        _statutory_rates_validated(params).survivor_max_reduction
        * months
        / period
    )


def _drc_monthly_rate(birth_year: int, params: SSAParameters) -> Fraction:
    """402(w) monthly credit: the cohort's annual rate over 12, exactly."""
    annual = _exact(
        params.delayed_credit_annual_rate(birth_year), "DRC annual rate"
    )
    return annual / 12


def _refuse_early_delayed_credits(birth_year: int) -> None:
    if birth_year < FIRST_SUPPORTED_DELAYED_CREDIT_BIRTH_YEAR:
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.DELAYED_CREDITS_BEFORE_1917,
            f"birth year {birth_year}: 402(w)(6)(A) gives 1/12 of 1 "
            "percent a month to a person first eligible before 1979 (born "
            "before 01/02/1917, POMS RS 00615.692D), and the parameter "
            "bundle's schedule does not",
        )


def _fra_months(birth_year: int, params: SSAParameters) -> int:
    """416(l): a finite bundle FRA before any month-bound comparison."""
    _input_year(birth_year, "birth_year")
    _input_type(params, SSAParameters, "params")
    schedule = params.fra_months_by_birth_year
    _input_sequence(schedule, "fra_months_by_birth_year")
    if not schedule:
        raise InvalidFamilyInput("Full retirement age schedule is empty")
    previous = 0
    for entry in schedule:
        _input_sequence(entry, "FRA schedule entry")
        if len(entry) != 2:
            raise InvalidFamilyInput("FRA entry needs year and months")
        year, months = entry
        _input_year(year, "FRA year")
        _exact(months, "Full retirement age months")
        _input_type(months, int, "Full retirement age months")
        if year <= previous or not 756 <= months <= 804:
            raise InvalidFamilyInput(
                "FRA schedule needs increasing years and months in 756..804"
            )
        previous = year
    months = params.fra_months(birth_year)
    if not math.isfinite(months):
        raise InvalidFamilyInput("Full retirement age months must be finite")
    return months


@_validated_entry
def delayed_credit_window_months(
    birth_year: int, params: SSAParameters
) -> int:
    """The most delayed-credit months a cohort can earn: 840 - FRA.

    402(w)(2)(A): increment months run from the month of attaining full
    retirement age (416(l), from the bundle) to the month before attaining
    70. POMS RS 00615.692E tabulates the result by date of birth; its
    bands run from January 2, so pass the previous year for a January 1
    birth. Births before 1917 are refused (402(w)(6)(A)).
    """
    _input_year(birth_year, "birth_year")
    _statutory_rates_validated(params)
    fra = _fra_months(birth_year, params)
    _refuse_early_delayed_credits(birth_year)
    return _AGE_70_MONTHS - fra


def _delayed_credit_months(
    months: int, birth_year: int | None, params: SSAParameters | None
) -> int:
    """Validate delayed-credit months; every failure is an input error.

    Without ``params`` only the checks that need no bundle run: an int,
    nonnegative, a birth year when positive, and at most 84 (the longest
    window on the RS 00615.692E chart). With it, the cohort's window
    ``840 - FRA`` bounds births from 1917; earlier births are refused
    later, when a benefit is computed.
    """
    _input_type(months, int, "delayed_credit_months")
    if birth_year is not None:
        _input_year(birth_year, "birth_year")
    if months < 0:
        raise InvalidFamilyInput("delayed_credit_months must be nonnegative")
    if months == 0:
        return 0
    if birth_year is None:
        raise InvalidFamilyInput("Delayed credits need the birth year")
    if months > _MAX_DELAYED_CREDIT_MONTHS:
        raise InvalidFamilyInput(
            f"delayed_credit_months {months} exceeds "
            f"{_MAX_DELAYED_CREDIT_MONTHS}, the longest window on the POMS "
            "RS 00615.692E chart"
        )
    if birth_year < FIRST_SUPPORTED_DELAYED_CREDIT_BIRTH_YEAR:
        # RS 00615.692E: year bands use January 2; January 1 takes
        # the preceding band, as for every cohort input in this module.
        window = (
            84 if birth_year <= 1912 else (72 if birth_year == 1913 else 60)
        )
        _months(months, "delayed_credit_months", window)
        return months
    if params is None:
        return months
    fra = _fra_months(birth_year, params)
    window = _AGE_70_MONTHS - fra
    if months > window:
        raise InvalidFamilyInput(
            f"delayed_credit_months must be between 0 and {window} for birth "
            f"year {birth_year}: credits run from full retirement age "
            f"({fra} months) to age 70 (402(w)(2)(A); POMS RS 00615.692E)"
        )
    return months


def _cohort_reduction_months(
    months: int, birth_year: int | None, params: SSAParameters, label: str
) -> int:
    """402(q)(6): months cannot precede age 62 (RS 00615.010)."""
    if birth_year is not None:
        _input_year(birth_year, "birth_year")
    upper = 60 if birth_year is None else _fra_months(birth_year, params) - 744
    return _months(months, label, upper)


def _check_own_benefit(own: OwnBenefit, params: SSAParameters) -> None:
    """The own-benefit input checks that need the parameter bundle."""
    own = _checked_input(own, OwnBenefit, "own")
    _cohort_reduction_months(
        own.reduction_months, own.birth_year, params, "reduction_months"
    )
    _delayed_credit_months(own.delayed_credit_months, own.birth_year, params)


def _refuse_historical_own_rib(
    pia: Fraction, reduction_months: int, birth_year: int | None
) -> None:
    """RS 00615.005C.2 needs money history for pre-1978 entitlement.

    A cohort before 1916 could take RIB before January 1978. Reduction
    months are after any ARF, so they cannot establish initial entitlement.
    Undated scalar inputs retain the current-formula domain; they do not
    validate a historical award. A zero PIA or no reduction needs no
    historical reduction amount.
    """
    if (
        pia > 0
        and reduction_months > 0
        and birth_year is not None
        and birth_year < 1916
    ):
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.OWN_RIB_HISTORY_BEFORE_1978,
            "own RIB with a positive reduction for a cohort before 1916 "
            "could have initial entitlement before January 1978; "
            "RS 00615.005C.2 requires the current money amount of "
            "reduction and historical PIA, which these inputs omit",
        )


@_validated_entry
def worker_age_adjusted(
    pia: object,
    reduction_months: int,
    delayed_credit_months: int,
    birth_year: int | None,
    params: SSAParameters,
) -> tuple[Fraction, Fraction]:
    """An old-age benefit before and after delayed credits.

    Reduction: PIA x (180 - RF)/180 or (192 - ARM)/240, dime-floored (POMS
    RS 00615.101). Credits: base x months x monthly rate, dime-floored and
    added to the base, which is the PIA or, after a reduced RIB, the MBA
    (RS 00615.692A, C). Returns ``(without_credits, with_credits)``.

    Credit months run from full retirement age to 70, at most
    :func:`delayed_credit_window_months`; more is an input error. Credits
    for births before 1917 are refused (402(w)(6)(A)).

    Positive reductions with positive PIA for cohorts before 1916 refuse:
    initial entitlement could precede January 1978, and RS 00615.005C.2
    needs reduction/PIA history absent here. Undated inputs use the current
    formula and do not establish conformance for historical awards.
    """
    rates = _statutory_rates_validated(params)
    amount = _dimes(pia, "PIA")
    reduction_months = _cohort_reduction_months(
        reduction_months, birth_year, params, "reduction_months"
    )
    delayed_credit_months = _delayed_credit_months(
        delayed_credit_months, birth_year, params
    )
    _refuse_historical_own_rib(amount, reduction_months, birth_year)
    base = _floor_dime_validated(
        amount * (1 - _worker_reduction(reduction_months, rates))
    )
    if delayed_credit_months == 0:
        return base, base
    _refuse_early_delayed_credits(birth_year)
    credit = _floor_dime_validated(
        base * delayed_credit_months * _drc_monthly_rate(birth_year, params)
    )
    return base, base + credit


@_validated_entry
def spouse_age_reduced(
    amount: object, reduction_months: int, params: SSAParameters
) -> Fraction:
    """A spouse's benefit (after the maximum) reduced for age, dime-floored.

    RF 1-36: x (144 - RF)/144; RF 37-60: x (180 - ARM)/240 (POMS RS
    00615.201B.1.c). ``amount`` is the OB, or the family-maximum share when
    the maximum applies.
    """
    rates = _statutory_rates_validated(params)
    value = _dimes(amount, "spouse benefit")
    months = _months(
        reduction_months, "reduction_months", _MAX_SPOUSE_REDUCTION_MONTHS
    )
    return _floor_dime_validated(
        value * (1 - _spouse_reduction(months, rates))
    )


@_validated_entry
def survivor_age_reduced(
    amount: object,
    reduction_months: int,
    reduction_period_months: int,
    params: SSAParameters,
) -> Fraction:
    """A widow(er)'s benefit (after the maximum) reduced for age.

    MAR = amount x RF x .285 / total possible RF, rounded *up* to the dime;
    MBA = amount - MAR (POMS RS 00615.301B.1.c-d).
    """
    rates = _statutory_rates_validated(params)
    value = _dimes(amount, "widow(er) benefit")
    period = _survivor_period(reduction_period_months)
    months = _months(reduction_months, "reduction_months", period)
    reduction = _ceil_dime_validated(
        value * months * rates.survivor_max_reduction / period
    )
    return value - reduction


def _survivor_period(value: int) -> int:
    if type(value) is not int or value not in _SURVIVOR_PERIODS:
        raise InvalidFamilyInput(
            "reduction_period_months must be a statutory cohort period "
            "(60, 62, ..., 84)"
        )
    return value


#: POMS RS 00615.301B.2: widow(er) full retirement age by date of birth,
#: as (last birth date in the band, months from age 60 to that FRA).
_WIDOW_PERIOD_BY_BIRTH = (
    (date(1940, 1, 1), 60),
    (date(1941, 1, 1), 62),
    (date(1942, 1, 1), 64),
    (date(1943, 1, 1), 66),
    (date(1944, 1, 1), 68),
    (date(1945, 1, 1), 70),
    (date(1957, 1, 1), 72),
    (date(1958, 1, 1), 74),
    (date(1959, 1, 1), 76),
    (date(1960, 1, 1), 78),
    (date(1961, 1, 1), 80),
    (date(1962, 1, 1), 82),
)


@_validated_entry
def widow_reduction_period_months(birth_date: date) -> int:
    """Total possible widow(er) reduction months for a date of birth.

    POMS RS 00615.301B.2: FRA 65 through 1/1/40, rising two months per
    year to 66 (born 1/2/45-1/1/57), then to 67 for births on or after
    1/2/62. The period runs from age 60 to that FRA.
    """
    _input_type(birth_date, date, "birth_date")
    for last_birth_date, period in _WIDOW_PERIOD_BY_BIRTH:
        if birth_date <= last_birth_date:
            return period
    return 84


# ---------------------------------------------------------------------------
# Family inputs
# ---------------------------------------------------------------------------
class FamilyKind(Enum):
    """Whose record: a living retired worker, a disabled worker, a death."""

    RETIREMENT = "retirement"
    DISABILITY = "disability"
    SURVIVOR = "survivor"


class Role(Enum):
    """The auxiliary or survivor benefit a beneficiary claims."""

    SPOUSE = "spouse"  # 402(b)/(c), aged
    SPOUSE_CHILD_IN_CARE = "spouse_child_in_care"  # 402(b)/(c), not reduced
    DIVORCED_SPOUSE = "divorced_spouse"  # outside the maximum
    CHILD = "child"  # 402(d)
    WIDOW = "widow"  # 402(e)/(f), aged widow(er)
    SURVIVING_DIVORCED_SPOUSE = "surviving_divorced_spouse"  # outside
    MOTHER_FATHER = "mother_father"  # 402(g), incl. surviving divorced
    PARENT = "parent"  # 402(h): one or two entitled parents
    DISABLED_WIDOW = "disabled_widow"  # 402(e)/(f): fixed 28.5% from 1/1984


@dataclass(frozen=True)
class _RoleCompatibility:
    """The record and OB arguments permitted by 402(b)-(h)."""

    record_kinds: frozenset[FamilyKind]
    accepts_basis: bool = False
    accepts_parent_count: bool = False


_LIFE_RECORDS = frozenset({FamilyKind.RETIREMENT, FamilyKind.DISABILITY})
_DEATH_RECORDS = frozenset({FamilyKind.SURVIVOR})
_ROLE_COMPATIBILITY = MappingProxyType(
    {
        Role.SPOUSE: _RoleCompatibility(_LIFE_RECORDS),
        Role.SPOUSE_CHILD_IN_CARE: _RoleCompatibility(_LIFE_RECORDS),
        Role.DIVORCED_SPOUSE: _RoleCompatibility(_LIFE_RECORDS),
        Role.CHILD: _RoleCompatibility(frozenset(FamilyKind)),
        Role.WIDOW: _RoleCompatibility(_DEATH_RECORDS, accepts_basis=True),
        Role.SURVIVING_DIVORCED_SPOUSE: _RoleCompatibility(
            _DEATH_RECORDS, accepts_basis=True
        ),
        Role.MOTHER_FATHER: _RoleCompatibility(_DEATH_RECORDS),
        Role.PARENT: _RoleCompatibility(
            _DEATH_RECORDS, accepts_parent_count=True
        ),
        Role.DISABLED_WIDOW: _RoleCompatibility(
            _DEATH_RECORDS, accepts_basis=True
        ),
    }
)


def _check_role_arguments(
    role: Role,
    *,
    kind: FamilyKind | None = None,
    basis: Fraction | None = None,
    parent_count: int | None = None,
) -> None:
    """One compatibility contract for declarations, helpers and families."""
    _input_type(role, Role, "role")
    rule = _ROLE_COMPATIBILITY[role]
    if kind is not None:
        _input_type(kind, FamilyKind, "kind")
        if kind not in rule.record_kinds:
            raise InvalidFamilyInput(
                f"A {role.value} cannot be entitled on a {kind.value} record"
            )
    if basis is not None and not rule.accepts_basis:
        raise InvalidFamilyInput(
            "Only a widow(er) OB can differ from the PIA share"
        )
    if parent_count is not None:
        _input_type(parent_count, int, "parent_count")
        if not rule.accepts_parent_count:
            raise InvalidFamilyInput("parent_count describes parents only")
        if parent_count not in (1, 2):
            raise InvalidFamilyInput("parent_count must be one or two")


_OUTSIDE_MAXIMUM = frozenset(
    {Role.DIVORCED_SPOUSE, Role.SURVIVING_DIVORCED_SPOUSE}
)
_SPOUSE_ROLES = frozenset(
    {Role.SPOUSE, Role.SPOUSE_CHILD_IN_CARE, Role.DIVORCED_SPOUSE}
)
_AGED_WIDOW_ROLES = frozenset({Role.WIDOW, Role.SURVIVING_DIVORCED_SPOUSE})
_WIDOW_ROLES = _AGED_WIDOW_ROLES | {Role.DISABLED_WIDOW}
_AGE_REDUCED_ROLES = frozenset({Role.SPOUSE, Role.DIVORCED_SPOUSE}) | (
    _AGED_WIDOW_ROLES
)


class RecordCondition(Enum):
    """Record-level conditions the caller must declare when present."""

    DIB_GUARANTEE_PIA = "dib_guarantee_pia"  # RS 00615.736B.2, .738
    DIB_AFTER_REDUCED_RIB = "dib_after_reduced_rib"  # 402(q)(2)
    WORKERS_COMPENSATION_OFFSET = "workers_compensation_offset"  # 224
    ADMINISTRATIVE_FINALITY = "administrative_finality"  # RS 00615.754A.3
    #: The living worker is not entitled to a RIB or DIB; only a divorced
    #: spouse can be entitled on the record (402(b)(4)(A), (c)(4)(A)).
    #: The caller attests insured eligibility and two continuous years
    #: of divorce (RS 00202.100); G computes payment, not entitlement facts.
    WORKER_NOT_ENTITLED = "worker_not_entitled"
    #: Pre-2024 WEP-affected IEDS computation is not implemented; IEDS
    #: must use the worker's WEP PIA when applicable (RS 00202.100).
    WINDFALL_ELIMINATION_PROVISION = "windfall_elimination_provision"
    #: The PIA is not an AIME-formula PIA (for example an old-start,
    #: special-minimum or frozen-minimum PIA; RS 00615.740B.1 lists them).
    NON_AIME_FORMULA_PIA = "non_aime_formula_pia"


class BeneficiaryCondition(Enum):
    """Beneficiary-level conditions the caller must declare when present."""

    ENTITLED_ON_ANOTHER_RECORD = "entitled_on_another_record"  # 203(a)(3)(A)
    DEEMED_OR_PUTATIVE_SPOUSE = "deemed_or_putative_spouse"  # 203(a)(3)(D)
    LEGAL_SPOUSE_WITH_DEEMED_SPOUSE = "legal_spouse_with_deemed_spouse"
    GOVERNMENT_PENSION_OFFSET = "government_pension_offset"  # 202(k)(5)
    RATE_PROTECTED_BY_FINALITY = "rate_protected_by_finality"
    #: A DIB between a reduced spouse's benefit and a later RIB, which
    #: changes the later spouse excess (RS 00615.260B.2).
    DIB_BETWEEN_SPOUSE_BENEFIT_AND_RIB = "dib_between_spouse_benefit_and_rib"
    #: Entitlement for May 1978 protects this survivor's rate from a
    #: widow(er)'s deceased-worker DRC increase (RS 00615.712).
    WIDOW_DRC_SAVINGS_CLAUSE = "widow_drc_savings_clause"


_RECORD_CONDITION_REASONS = {
    RecordCondition.DIB_GUARANTEE_PIA: (
        UnsupportedReason.DIB_GUARANTEE_PIA,
        "DIB guarantee PIA maximums (POMS RS 00615.736B.2, .738)",
    ),
    RecordCondition.DIB_AFTER_REDUCED_RIB: (
        UnsupportedReason.DIB_AFTER_REDUCED_RIB,
        "a DIB reduced for prior reduced RIB (402(q)(2))",
    ),
    RecordCondition.WORKERS_COMPENSATION_OFFSET: (
        UnsupportedReason.WORKERS_COMPENSATION_OFFSET,
        "the section 224 workers' compensation offset",
    ),
    RecordCondition.ADMINISTRATIVE_FINALITY: (
        UnsupportedReason.ADMINISTRATIVE_FINALITY,
        "rates protected by administrative finality (RS 00615.754A.3)",
    ),
    RecordCondition.NON_AIME_FORMULA_PIA: (
        UnsupportedReason.NON_AIME_FORMULA_PIA,
        "maximums for PIAs other than the AIME formula PIA (old-start, "
        "special minimum, frozen minimum; RS 00615.740B.1) are not "
        "implemented",
    ),
}
_BENEFICIARY_CONDITION_REASONS = {
    BeneficiaryCondition.WIDOW_DRC_SAVINGS_CLAUSE: (
        UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE,
        "a May 1978 beneficiary protected against the widow(er)'s "
        "deceased-worker DRC increase (RS 00615.712) is not implemented",
    ),
    BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD: (
        UnsupportedReason.COMBINED_FAMILY_MAXIMUM,
        "a child entitled on more than one record may need a combined "
        "family maximum (403(a)(3)(A); POMS RS 00615.770)",
    ),
    BeneficiaryCondition.DEEMED_OR_PUTATIVE_SPOUSE: (
        UnsupportedReason.DEEMED_SPOUSE,
        "deemed or putative spouse (403(a)(3)(D); RS 00615.684)",
    ),
    BeneficiaryCondition.LEGAL_SPOUSE_WITH_DEEMED_SPOUSE: (
        UnsupportedReason.DEEMED_SPOUSE,
        "legal spouse paid outside the maximum because a deemed spouse "
        "is entitled (403(a)(3)(D); RS 00615.684)",
    ),
    BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET: (
        UnsupportedReason.GOVERNMENT_PENSION_OFFSET,
        "the 402(k)(5) government pension offset",
    ),
    BeneficiaryCondition.RATE_PROTECTED_BY_FINALITY: (
        UnsupportedReason.ADMINISTRATIVE_FINALITY,
        "a rate protected by administrative finality (RS 00615.754A.3)",
    ),
    BeneficiaryCondition.DIB_BETWEEN_SPOUSE_BENEFIT_AND_RIB: (
        UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
        "a DIB between a reduced spouse's benefit and the RIB carries the "
        "RIB reduction into the spouse excess (RS 00615.260B.2); not "
        "implemented",
    ),
}


class OwnBenefitKind(Enum):
    OLD_AGE = "old_age"
    DISABILITY = "disability"


@_declared_input
@dataclass(frozen=True)
class OwnBenefit:
    """A person's own old-age (RIB) or disability (DIB) benefit.

    ``pia`` is that person's current PIA (after COLAs). Reduction months
    are the 402(q) worker months after any ARF. Delayed-credit months need
    ``birth_year`` for the 402(w) rate and window: at most ``840 - FRA``
    (:func:`delayed_credit_window_months`, checked when the benefit is
    computed), and refused for births before 1917. SSA's cohort bands run
    from January 2, so a January 1 birth takes the previous year. Positive
    own-RIB reductions with positive PIA for a known cohort before 1916
    need pre-1978 money history and refuse (RS 00615.005C.2). An omitted
    cohort invokes the current formula, not a historical award validation.
    A DIB is unreduced and has no credits here (402(q)(2) cases refuse when
    computed, after all family input checks, rather than in this constructor).
    """

    kind: OwnBenefitKind
    pia: Fraction
    reduction_months: int = 0
    delayed_credit_months: int = 0
    birth_year: int | None = None

    def __post_init__(self):
        _validate_input_fields(self)
        # Public wrappers check caller fields; private construction owns them.
        read = object.__getattribute__.__get__(self)
        object.__setattr__(self, "pia", _dimes(read("pia"), "own PIA"))
        _months(
            read("reduction_months"),
            "reduction_months",
            _MAX_WORKER_REDUCTION_MONTHS,
        )
        _delayed_credit_months(
            read("delayed_credit_months"), read("birth_year"), None
        )
        if read("kind") is OwnBenefitKind.DISABILITY:
            if read("delayed_credit_months"):
                raise InvalidFamilyInput("A DIB earns no delayed credits")


def _refuse_own_benefit(own: OwnBenefit) -> None:
    """Own-benefit coverage, after own/family input checks have completed."""
    if own.kind is OwnBenefitKind.DISABILITY and own.reduction_months:
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.DIB_AFTER_REDUCED_RIB,
            "a DIB reduced for prior reduced RIB (402(q)(2))",
        )
    if own.kind is OwnBenefitKind.OLD_AGE:
        _refuse_historical_own_rib(
            own.pia, own.reduction_months, own.birth_year
        )


@_validated_entry
def own_monthly_benefit(
    own: OwnBenefit, params: SSAParameters
) -> tuple[Fraction, Fraction]:
    """The own benefit ``(without_credits, with_credits)`` after 402(q)/(w)."""
    own = _checked_input(own, OwnBenefit, "own")
    _statutory_rates_validated(params)
    _check_own_benefit(own, params)
    _refuse_own_benefit(own)
    return _worker_age_adjusted_validated(
        own.pia,
        own.reduction_months,
        own.delayed_credit_months,
        own.birth_year,
        params,
    )


@_declared_input
@dataclass(frozen=True)
class Beneficiary:
    """One auxiliary or survivor on the worker's record for the month.

    * ``reduction_months``: 402(q) months (after any ARF) for an aged
      spouse, divorced spouse or widow(er); zero for other roles.
    * ``reduction_period_months``: a widow(er)'s total possible reduction
      months (60-84, :func:`widow_reduction_period_months`); required when
      ``reduction_months`` is positive.
    * ``original_benefit_basis``: a widow(er)'s OB when it exceeds the death
      PIA (deceased's delayed credits or windexing, POMS RS 00615.301A.3,
      .302, .710); defaults to the PIA.
    * ``own_benefit`` / ``own_benefit_first``: dual entitlement, and whether
      the own benefit began in or before the auxiliary benefit's first month.
      For an aged spouse or divorced spouse this selects method C (True: A
      then B, or A with B; RS 00615.250) or method B (False: B then A; RS
      00615.240), and it is required: the two differ in money, and there
      is no default. Current-care divorced spouses with own RIB do not
      need this order: RS 00615.201A.2 settles their amount either way.
      A spouse's DIB after the spouse benefit is refused (RS
      00615.260). Other roles do not use the order; it may be left None.
    * ``birth_year``: SSA cohort year (January 2 through the following
      January 1), shared with ``own_benefit.birth_year``. Either supplied
      field fixes both reduction bounds and the widow(er)'s period under
      RS 00615.301B.2; different supplied years are an input error. An aged
      widow(er) with own RIB needs a cohort in at least one field.
      A reduced spouse before cohort 1916 or a reduced widow(er) before
      1928 needs pre-1978 money history unless the amount is settled without
      it (RS 00615.005C.2). The latter includes possible prior DWB beginning
      at 50 and conversion to aged WIB at FRA (RS 00615.310A).
    * ``conditions``: declared special conditions; GPO is inoperative for
      benefit months from January 2024 (Pub. L. 118-273).
    * ``child_in_care``: the id of an entitled child on this record for
      this month, or False to attest no child in care. None is unknown;
      a widow(er) or divorced spouse with an entitled child then refuses.
      RS 00615.340 and .010 raise reduced WIB to the mother/father amount
      when larger. For a divorced spouse, current care exempts the spouse
      amount from age reduction and offsets the reduced own RIB, regardless
      of entitlement order (RS 00615.201A.2).
    * ``first_entitlement_child_in_care``: divorced-spouse-only attestation
      about care in the first month of divorced entitlement. False permits
      the ordinary aged formula when there is no current care; unknown
      history or True refuses if the continued exemption could change that
      auxiliary payable after the own-benefit offset and zero floor. This
      snapshot does not implement conversion/ARF history after care ends
      (202(k)(3)(A); RS 00615.201A.2; .010).
    """

    beneficiary_id: str
    role: Role
    reduction_months: int = 0
    reduction_period_months: int | None = None
    original_benefit_basis: Fraction | None = None
    own_benefit: OwnBenefit | None = None
    own_benefit_first: bool | None = None
    birth_year: int | None = None
    conditions: frozenset[BeneficiaryCondition] = field(
        default_factory=frozenset
    )
    child_in_care: str | bool | None = None
    first_entitlement_child_in_care: bool | None = None

    def __post_init__(self):
        _validate_input_fields(self)
        # Public wrappers check caller fields; private construction owns them.
        read = object.__getattribute__.__get__(self)
        if read("child_in_care") is not None:
            if read("role") not in _WIDOW_ROLES | {Role.DIVORCED_SPOUSE}:
                raise InvalidFamilyInput(
                    "child_in_care is an input for widow(er) or divorced "
                    "spouse benefits"
                )
            if read("child_in_care") is not False and (
                not isinstance(read("child_in_care"), str)
                or not read("child_in_care")
            ):
                raise InvalidFamilyInput(
                    "child_in_care must name an entitled child, or be "
                    "False or None"
                )
        if read("first_entitlement_child_in_care") is not None:
            if read("role") is not Role.DIVORCED_SPOUSE:
                raise InvalidFamilyInput(
                    "first_entitlement_child_in_care describes a divorced "
                    "spouse only"
                )
        object.__setattr__(self, "conditions", frozenset(read("conditions")))
        if read("original_benefit_basis") is not None:
            _check_role_arguments(
                read("role"), basis=read("original_benefit_basis")
            )
            object.__setattr__(
                self,
                "original_benefit_basis",
                _dimes(read("original_benefit_basis"), "OB basis"),
            )
        if read("own_benefit_first") is not None:
            if read("own_benefit") is None:
                raise InvalidFamilyInput(
                    "own_benefit_first describes an own benefit; there is "
                    "none"
                )
        elif (
            read("own_benefit") is not None
            and read("role")
            in (
                Role.SPOUSE,
                Role.DIVORCED_SPOUSE,
            )
            and not (
                read("role") is Role.DIVORCED_SPOUSE
                and isinstance(read("child_in_care"), str)
                and read("own_benefit").kind is OwnBenefitKind.OLD_AGE
            )
        ):
            raise InvalidFamilyInput(
                f"A dually entitled {read('role').value} needs own_benefit_first"
                ": method C (own benefit first, RS 00615.250) and method B "
                "(spouse benefit first, RS 00615.240) pay different amounts"
            )
        if read("reduction_months") < 0:
            raise InvalidFamilyInput("reduction_months must be nonnegative")
        _months(
            read("reduction_months"),
            "reduction_months",
            (
                84
                if read("role") in _WIDOW_ROLES
                else _MAX_SPOUSE_REDUCTION_MONTHS
            ),
        )
        if read("reduction_months") and read("role") not in _AGE_REDUCED_ROLES:
            raise InvalidFamilyInput(
                f"A {read('role').value} benefit is not reduced for age"
            )
        if read("reduction_period_months") is not None:
            if read("role") is Role.DISABLED_WIDOW:
                raise InvalidFamilyInput(
                    "DWB uses a fixed reduction, not reduction months"
                )
            if read("role") not in _WIDOW_ROLES:
                raise InvalidFamilyInput(
                    "Only a widow(er) has a survivor reduction period"
                )
            _survivor_period(read("reduction_period_months"))


@_declared_input
@dataclass(frozen=True)
class WorkerRecord:
    """The insured worker's record, from which the maximum is computed.

    ``eligibility_pia`` is the PIA for the year of first eligibility before
    COLAs; ``cola_percents`` are the increases from then through the
    payment month, in order (:func:`applicable_cola_percents` selects them
    from a December-COLA history). The eligibility year of a worker who was
    entitled to DIB within the 12 preceding months is the DIB eligibility
    year (403(a)(2)(D)); the caller supplies it. A disability record needs
    the AIME and the month of the worker's initial DIB entitlement ever
    (the RS 00615.740B test for the 1980 disability maximum). A DIB that
    has converted to a RIB, or a worker who has died, takes a retirement or
    survivor record (RS 00615.742.2). AIME is a nonnegative whole-dollar
    amount, supplied as an int or an integral Fraction. Worker reduction
    and credit months describe the living worker's own RIB (retirement
    records only).
    ``worker_birth_year`` describes the insured person's SSA cohort for
    every record kind, whether or not the worker is entitled. Delayed
    credits need that cohort and run from full retirement age to
    70 (:func:`delayed_credit_window_months`, checked by
    :func:`record_state`). ``rib_lim_benefit`` is, for a death, the
    reduced RIB or DIB the deceased would receive if alive (402(e)(2)(D));
    None when the deceased never received a reduced benefit.

    WORKER_NOT_ENTITLED attests the living worker's eligibility and a
    divorce of at least two continuous years for every divorced spouse
    supplied. Only those beneficiaries are admitted; no worker is paid.
    """

    kind: FamilyKind
    eligibility_year: int
    eligibility_pia: Fraction
    cola_percents: tuple[Fraction, ...] = ()
    aime: int | Fraction | None = None
    first_dib_entitlement: YearMonth | None = None
    worker_reduction_months: int = 0
    worker_delayed_credit_months: int = 0
    worker_birth_year: int | None = None
    rib_lim_benefit: Fraction | None = None
    conditions: frozenset[RecordCondition] = field(default_factory=frozenset)

    def __post_init__(self):
        _validate_input_fields(self)
        # Public wrappers check caller fields; private construction owns them.
        read = object.__getattribute__.__get__(self)
        _months(
            read("worker_reduction_months"),
            "worker_reduction_months",
            _MAX_WORKER_REDUCTION_MONTHS,
        )
        object.__setattr__(
            self, "eligibility_pia", _dimes(read("eligibility_pia"), "PIA")
        )
        object.__setattr__(
            self,
            "cola_percents",
            tuple(
                _exact(p, "COLA percent") for p in tuple(read("cola_percents"))
            ),
        )
        object.__setattr__(self, "conditions", frozenset(read("conditions")))
        if read("rib_lim_benefit") is not None:
            if read("kind") is not FamilyKind.SURVIVOR:
                raise InvalidFamilyInput("A RIB-LIM applies only to deaths")
            object.__setattr__(
                self,
                "rib_lim_benefit",
                _dimes(read("rib_lim_benefit"), "RIB-LIM benefit"),
            )
        if read("kind") is not FamilyKind.RETIREMENT and (
            read("worker_reduction_months")
            or read("worker_delayed_credit_months")
        ):
            raise InvalidFamilyInput(
                "Own-RIB months describe a living retired worker only"
            )
        _delayed_credit_months(
            read("worker_delayed_credit_months"),
            read("worker_birth_year"),
            None,
        )


@_declared_input
@dataclass(frozen=True)
class RecordState:
    """A record's current PIA and family maximum for the payment month.

    Built by :func:`record_state` from a :class:`WorkerRecord`, or directly
    when a published example (or SSA's master record) gives both amounts.
    For an entitled retirement worker ``worker`` is the worker's own RIB;
    it may be absent with WORKER_NOT_ENTITLED (IEDS, RS 00202.100).
    ``worker_birth_year`` retains the insured person's SSA cohort even
    without own-benefit entitlement. It must agree with ``worker`` when
    both supply a cohort; either supplies the other's missing cohort.
    ``eligibility_year`` and ``first_dib_entitlement`` are the record's
    dates when known (:func:`record_state` fills them in); a payment month
    before either is an :class:`InvalidFamilyInput`.
    Retirement eligibility cannot follow the insured person's age-62
    cohort year, including when the worker remains unclaimed. All entry
    points check this before coverage refusals or guard advancement
    (403(a)(2)(A), with earlier DIB eligibility under 403(a)(2)(D)).
    A known initial DIB entitlement before July 1980 is refused on a
    disability snapshot, as on a built record (RS 00615.740B.2).
    ``widow_drc_savings_clause`` attests whether any beneficiary is protected
    under RS 00615.712: entitlement for May 1978 with a widow(er) receiving
    the deceased's delayed credits. True is refused; None is unknown and
    refused for survivor snapshots without modern eligibility metadata.
    False explicitly attests that the clause cannot apply. Modern current
    eligibility is insufficient when prior DIB entitlement could allow
    May 1978 protection (RS 00615.736B.2b). An omitted first DIB date is
    unknown history: a subject widow(er) OB above the death PIA with
    another subject survivor needs False or a known first-ever DIB date
    after May 1978, equally for built and direct snapshots.
    """

    kind: FamilyKind
    pia: Fraction
    family_maximum: Fraction
    worker: OwnBenefit | None = None
    rib_lim_benefit: Fraction | None = None
    conditions: frozenset[RecordCondition] = field(default_factory=frozenset)
    source: str = "given"
    eligibility_year: int | None = None
    first_dib_entitlement: YearMonth | None = None
    deferred_refusal: tuple[UnsupportedReason, str] | None = None
    widow_drc_savings_clause: bool | None = None
    worker_birth_year: int | None = None

    def __post_init__(self):
        _validate_input_fields(self)
        if self.worker is not None:
            year = self.worker_birth_year
            own_year = self.worker.birth_year
            if year is not None and own_year is not None and year != own_year:
                raise InvalidFamilyInput(
                    "worker birth_year differs from the record cohort"
                )
            if year is None:
                object.__setattr__(self, "worker_birth_year", own_year)
            elif own_year is None:
                object.__setattr__(
                    self,
                    "worker",
                    _replace_declared(self.worker, birth_year=year),
                )
        pia = _dimes(self.pia, "PIA")
        maximum = _dimes(self.family_maximum, "family maximum")
        if maximum < pia:
            raise InvalidFamilyInput("The family maximum is below the PIA")
        object.__setattr__(self, "pia", pia)
        object.__setattr__(self, "family_maximum", maximum)
        object.__setattr__(self, "conditions", frozenset(self.conditions))
        if self.kind is FamilyKind.RETIREMENT:
            if self.worker is None and (
                RecordCondition.WORKER_NOT_ENTITLED not in self.conditions
            ):
                raise InvalidFamilyInput("A retirement record needs a worker")
            if (
                self.worker is not None
                and self.worker.kind is not OwnBenefitKind.OLD_AGE
            ):
                raise InvalidFamilyInput("A retired worker receives a RIB")
            if self.worker is not None and self.worker.pia != pia:
                raise InvalidFamilyInput("The worker's PIA must be the PIA")
        elif self.worker is not None:
            raise InvalidFamilyInput("Only a retirement record has a RIB")
        if self.rib_lim_benefit is not None:
            if self.kind is not FamilyKind.SURVIVOR:
                raise InvalidFamilyInput("A RIB-LIM applies only to deaths")
            object.__setattr__(
                self,
                "rib_lim_benefit",
                _dimes(self.rib_lim_benefit, "RIB-LIM benefit"),
            )


def _raise_record_conditions(conditions: Iterable[RecordCondition]) -> None:
    for condition in sorted(conditions, key=lambda c: c.value):
        if condition in {
            RecordCondition.WORKER_NOT_ENTITLED,
            RecordCondition.WINDFALL_ELIMINATION_PROVISION,
        }:
            continue
        reason, detail = _RECORD_CONDITION_REASONS[condition]
        raise _computed(FamilyConfigurationUnsupported, reason, detail)


def _refuse_record(record: WorkerRecord | RecordState) -> None:
    """One precedence for built and direct records, after all input checks."""
    if record.eligibility_year is not None:
        _require_supported_eligibility(record.eligibility_year)
    _raise_record_conditions(record.conditions)
    if (
        record.kind is FamilyKind.DISABILITY
        and record.first_dib_entitlement is not None
        and (
            record.first_dib_entitlement.year,
            record.first_dib_entitlement.month,
        )
        < DI_MAXIMUM_FIRST_ENTITLEMENT
    ):
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.DI_ENTITLEMENT_BEFORE_JULY_1980,
            "DIB first entitled before July 1980 keeps the pre-1980 "
            "maximum (POMS RS 00615.740B.2)",
        )


def _check_retirement_eligibility(
    kind: FamilyKind, eligibility_year: int | None, birth_year: int | None
) -> None:
    """403(a)(2): retirement eligibility is no later than the age-62 year.

    The insured person's cohort governs even without own entitlement.
    Earlier DIB eligibility can remain applicable under 403(a)(2)(D).
    Every builder and family/household route uses this same input check.
    """
    if (
        kind is FamilyKind.RETIREMENT
        and eligibility_year is not None
        and birth_year is not None
        and eligibility_year > birth_year + 62
    ):
        raise InvalidFamilyInput("eligibility_year exceeds birth year + 62")


@_validated_entry
def record_state(record: WorkerRecord, params: SSAParameters) -> RecordState:
    """Compute the record's current PIA and family maximum.

    Record input errors are raised here. Coverage refusals are carried on
    the RecordState and raised only after family input checks, even when
    this builder is called inside an evaluate_family closure.
    """
    record = _checked_input(record, WorkerRecord, "record")
    _statutory_rates_validated(params)
    disability_maximum = None
    if record.kind is FamilyKind.DISABILITY:
        if record.aime is None or record.first_dib_entitlement is None:
            raise InvalidFamilyInput(
                "A disability record needs aime and first_dib_entitlement"
            )
        # Computed here so that an invalid AIME is an input error first.
        disability_maximum = _disability_family_maximum_validated(
            record.eligibility_pia, record.aime
        )
    _cohort_reduction_months(
        record.worker_reduction_months,
        record.worker_birth_year,
        params,
        "worker_reduction_months",
    )
    _input_year(record.eligibility_year, "eligibility_year")
    _check_retirement_eligibility(
        record.kind, record.eligibility_year, record.worker_birth_year
    )
    _delayed_credit_months(
        record.worker_delayed_credit_months, record.worker_birth_year, params
    )
    pia = _increase_by_colas_validated(
        record.eligibility_pia, record.cola_percents
    )
    deferred = None
    try:
        _refuse_record(record)
    except FamilyConfigurationUnsupported as error:
        deferred = (error.reason, error.detail)
    if record.eligibility_year < FIRST_SUPPORTED_ELIGIBILITY_YEAR:
        # Sentinel, never payable: family inputs must be checked before
        # the historical-maximum refusal. No modern formula is substituted.
        base_maximum = record.eligibility_pia
    elif record.kind is FamilyKind.DISABILITY:
        base_maximum = disability_maximum
    else:
        base_maximum = _retirement_survivor_family_maximum_validated(
            record.eligibility_pia, record.eligibility_year, params
        )
    maximum = _increase_by_colas_validated(base_maximum, record.cola_percents)
    worker = None
    if record.kind is FamilyKind.RETIREMENT and (
        RecordCondition.WORKER_NOT_ENTITLED not in record.conditions
    ):
        worker = _construct_declared(
            OwnBenefit,
            kind=OwnBenefitKind.OLD_AGE,
            pia=pia,
            reduction_months=record.worker_reduction_months,
            delayed_credit_months=record.worker_delayed_credit_months,
            birth_year=record.worker_birth_year,
        )
    return _construct_declared(
        RecordState,
        kind=record.kind,
        pia=pia,
        family_maximum=maximum,
        worker=worker,
        rib_lim_benefit=record.rib_lim_benefit,
        conditions=record.conditions,
        source=(
            f"computed: eligibility {record.eligibility_year}, "
            f"{len(record.cola_percents)} COLA(s)"
        ),
        eligibility_year=record.eligibility_year,
        first_dib_entitlement=record.first_dib_entitlement,
        deferred_refusal=deferred,
        worker_birth_year=record.worker_birth_year,
    )


class DeductionReason(Enum):
    """Canonical GN 02603.040 deduction events; unknown reasons are invalid."""

    OWN_EARNINGS_TEST = "own_earnings_test"
    NO_CHILD_IN_CARE = "no_child_in_care"
    DUAL_ENTITLEMENT = "dual_entitlement"
    WORKERS_COMPENSATION = "workers_compensation"
    PRISONER_SUSPENSION = "prisoner_suspension"
    DRUG_ADDICTION_SUSPENSION = "drug_addiction_suspension"
    FOREIGN_WORK = "foreign_work"
    PENALTY = "penalty"
    MARITIME = "maritime"
    ELECTION_CERTIFICATE_SUSPENSION = "election_certificate_suspension"


@_declared_input
@dataclass(frozen=True)
class BenefitDeduction:
    """One month's deduction, keyed externally by beneficiary ID.

    ``payable`` is the exact nonnegative amount after deduction, not
    earnings or the amount withheld. Zero means a full deduction. Estimated
    own-work deductions have ``permanent=False``; all other supported events
    are permanent. Dual entitlement is already declared by ``OwnBenefit``;
    an explicit marker must agree with the ordinary G payable.
    """

    reason: DeductionReason
    payable: Fraction = Fraction(0)
    permanent: bool = True

    def __post_init__(self):
        _input_type(self.reason, DeductionReason, "deduction reason")
        _input_type(self.permanent, bool, "permanent")
        object.__setattr__(self, "payable", _exact(self.payable, "payable"))
        if self.payable < 0:
            raise InvalidFamilyInput("payable must be nonnegative")
        if self.reason is not DeductionReason.OWN_EARNINGS_TEST:
            if not self.permanent:
                raise InvalidFamilyInput(
                    "Only own-work deductions may be temporary"
                )
        # Source conflict us:oasdi-ret-temporary-partial-deduction: a
        # temporary own-work deduction may be partial (RS 02501.160 example
        # 2), although GN 02603.050D.2 says temporary deductions never are.
        if self.reason is DeductionReason.NO_CHILD_IN_CARE and self.payable:
            raise InvalidFamilyInput(
                "No-child-in-care deductions must be full"
            )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@_sealed_result
@dataclass(frozen=True)
class BeneficiaryBenefit(_SealedResult):
    """One beneficiary's gross amounts for the month (exact dimes).

    * ``original_benefit``: OB before the maximum.
    * ``standard_rate``: the proportional family-maximum share over every
      subject beneficiary (equal to OB when the maximum does not bind).
    * ``family_maximum_rate``: the rate after redistribution (differs from
      ``standard_rate`` only for non-dually-entitled beneficiaries when
      the RS 00615.768 rule redistributes).
    * ``counted_against_maximum``: what this beneficiary uses of the
      maximum; zero for a beneficiary outside it.
    * ``age_adjusted_rate``: after 402(q) and the RIB-LIM, before the
      dual-entitlement offset. For divorced-spouse care history that
      settles the same auxiliary payable under both histories, a differing
      ordinary intermediate rate is diagnostic; ``note`` explicitly
      identifies it and the alternate care-exempt intermediate rate.
    * ``auxiliary_payable``: paid on this record after 402(k)(3)(A).
    * ``own_benefit``: the own RIB/DIB paid on the person's own record.
    * ``reserved_work_deduction``: the NH charge, which releases no room.
      Redistributed ordinary rates already reflect this charge. Fixed dual,
      outside-maximum or nonbinding rates retain their dime gross amounts
      and report the exact NH charge also as ``deduction``; its absent
      ``deduction_reason`` marks a nonqualifying NH reservation. A nonzero
      deduction without a qualifying reason must equal this reservation.
    """

    beneficiary_id: str
    role: Role
    entitled: bool
    subject_to_family_maximum: bool
    original_benefit: Fraction
    standard_rate: Fraction
    family_maximum_rate: Fraction
    counted_against_maximum: Fraction
    age_adjusted_rate: Fraction
    auxiliary_payable: Fraction
    own_benefit: Fraction | None
    whole_dollar_auxiliary: int
    whole_dollar_own: int | None
    note: str = ""
    deduction: Fraction = Fraction(0)
    deduction_reason: DeductionReason | None = None
    reserved_work_deduction: Fraction = Fraction(0)
    age_reduction_factor: Fraction = Fraction(1)

    def __post_init__(self):
        _input_text(self.beneficiary_id, "beneficiary_id")
        _input_type(self.role, Role, "role")
        _input_type(self.entitled, bool, "entitled")
        _input_type(
            self.subject_to_family_maximum, bool, "subject_to_family_maximum"
        )
        _result_money_fields(
            self,
            (
                "original_benefit",
                "standard_rate",
                "family_maximum_rate",
                "age_adjusted_rate",
            ),
        )
        _nonnegative_integer(
            self.whole_dollar_auxiliary, "whole_dollar_auxiliary"
        )
        if self.whole_dollar_auxiliary != math.floor(self.auxiliary_payable):
            raise InvalidFamilyInput(
                "whole_dollar_auxiliary must floor auxiliary_payable"
            )
        _optional_result_money(self, "own_benefit", "whole_dollar_own")
        _input_type(self.note, str, "note")
        for name in (
            "deduction",
            "reserved_work_deduction",
            "counted_against_maximum",
            "auxiliary_payable",
        ):
            value = getattr(self, name)
            if type(value) is not Fraction or value < 0:
                raise InvalidFamilyInput(
                    f"{name} must be a nonnegative Fraction"
                )
        if self.deduction_reason is not None:
            _input_type(
                self.deduction_reason, DeductionReason, "deduction_reason"
            )
        elif self.deduction and self.deduction != self.reserved_work_deduction:
            raise InvalidFamilyInput(
                "A deduction needs a qualifying reason or its exact NH reservation"
            )
        factor = _exact(self.age_reduction_factor, "age_reduction_factor")
        if not 0 <= factor <= 1:
            raise InvalidFamilyInput("age_reduction_factor must be in [0, 1]")
        object.__setattr__(self, "age_reduction_factor", factor)
        if self.auxiliary_payable != max(
            Fraction(0),
            self.age_adjusted_rate - (self.own_benefit or 0) - self.deduction,
        ):
            raise InvalidFamilyInput(
                "auxiliary_payable must offset age_adjusted_rate by own benefit"
            )
        if (
            self.standard_rate > self.original_benefit
            or self.family_maximum_rate > self.original_benefit
            or self.counted_against_maximum
            > self.family_maximum_rate + self.reserved_work_deduction
        ):
            raise InvalidFamilyInput(
                "Result rates exceed their original benefit"
            )
        if self.subject_to_family_maximum != (
            self.entitled and self.role not in _OUTSIDE_MAXIMUM
        ):
            raise InvalidFamilyInput(
                "Result maximum membership is inconsistent"
            )
        if not self.subject_to_family_maximum and self.counted_against_maximum:
            raise InvalidFamilyInput("Outside beneficiaries use no maximum")
        if not self.entitled and any(
            (
                self.original_benefit,
                self.standard_rate,
                self.family_maximum_rate,
                self.age_adjusted_rate,
                self.auxiliary_payable,
            )
        ):
            raise InvalidFamilyInput(
                "Non-entitled beneficiaries have no auxiliary rate"
            )

    @property
    def total_received(self) -> Fraction:
        """Auxiliary plus own benefit (the person's gross monthly total)."""
        _check_seal(self)
        return self.auxiliary_payable + (self.own_benefit or Fraction(0))


@_sealed_result
@dataclass(frozen=True)
class FamilyBenefits(_SealedResult):
    """Gross monthly benefits on one record for one month.

    Only G's computation constructs this sealed result. Seal-time checks
    reconcile rates, maximum shares, payments and whole-dollar totals.
    Direct construction, replacement and copying are input errors.
    """

    kind: FamilyKind
    payment_month: YearMonth
    pia: Fraction
    family_maximum: Fraction
    available_for_auxiliaries: Fraction
    total_original_benefits: Fraction
    family_maximum_binding: bool
    redistribution_applied: bool
    worker_benefit: Fraction | None
    whole_dollar_worker: int | None
    beneficiaries: tuple[BeneficiaryBenefit, ...]
    record_total: Fraction
    record_total_whole_dollars: int
    subject_total: Fraction
    state_source: str
    pe_us_revision: str
    version: str = GROSS_BENEFITS_VERSION
    worker_reduced_for_age: bool = False
    worker_age_reduction_factor: Fraction = Fraction(1)

    def __post_init__(self):
        _input_type(self.kind, FamilyKind, "kind")
        object.__setattr__(
            self,
            "payment_month",
            _checked_input(self.payment_month, YearMonth, "payment_month"),
        )
        _result_money_fields(
            self,
            (
                "pia",
                "family_maximum",
                "available_for_auxiliaries",
                "total_original_benefits",
            ),
        )
        for name in (
            "family_maximum_binding",
            "redistribution_applied",
            "worker_reduced_for_age",
        ):
            _input_type(getattr(self, name), bool, name)
        _optional_result_money(self, "worker_benefit", "whole_dollar_worker")
        factor = _exact(
            self.worker_age_reduction_factor, "worker_age_reduction_factor"
        )
        if not 0 <= factor <= 1:
            raise InvalidFamilyInput(
                "worker_age_reduction_factor must be in [0, 1]"
            )
        if self.worker_reduced_for_age != (factor < 1):
            raise InvalidFamilyInput("Worker age metadata is inconsistent")
        object.__setattr__(self, "worker_age_reduction_factor", factor)
        _nonnegative_integer(
            self.record_total_whole_dollars, "record_total_whole_dollars"
        )
        _input_sequence(self.beneficiaries, "beneficiaries")
        beneficiaries = tuple(
            _checked_input(row, BeneficiaryBenefit, "beneficiary result")
            for row in self.beneficiaries
        )
        if len({row.beneficiary_id for row in beneficiaries}) != len(
            beneficiaries
        ):
            raise InvalidFamilyInput("Duplicate beneficiary result IDs")
        object.__setattr__(self, "beneficiaries", beneficiaries)
        for name in ("state_source", "pe_us_revision", "version"):
            _input_text(getattr(self, name), name)
        if self.family_maximum < self.pia:
            raise InvalidFamilyInput("The family maximum is below the PIA")
        if self.subject_total > self.family_maximum:
            raise InvalidFamilyInput("subject_total exceeds family_maximum")
        reserved = self.pia if self.worker_benefit is not None else Fraction(0)
        subject = [
            row for row in beneficiaries if row.subject_to_family_maximum
        ]
        if self.available_for_auxiliaries != self.family_maximum - reserved:
            raise InvalidFamilyInput(
                "Available maximum differs from worker reserve"
            )
        if self.total_original_benefits != sum(
            (row.original_benefit for row in subject), Fraction(0)
        ):
            raise InvalidFamilyInput(
                "Original benefits differ from subject rows"
            )
        if self.family_maximum_binding != (
            self.total_original_benefits > self.available_for_auxiliaries
        ):
            raise InvalidFamilyInput(
                "Binding flag differs from original benefits"
            )
        if self.redistribution_applied != bool(
            self.family_maximum_binding
            and (
                (
                    any(row.own_benefit is not None for row in subject)
                    and any(row.own_benefit is None for row in subject)
                )
                or any(row.deduction_reason is not None for row in subject)
            )
        ):
            raise InvalidFamilyInput(
                "Redistribution flag differs from subject rows"
            )
        if self.subject_total != reserved + sum(
            (row.counted_against_maximum for row in subject), Fraction(0)
        ):
            raise InvalidFamilyInput(
                "Subject total differs from counted rates"
            )
        for row in beneficiaries:
            _check_role_arguments(row.role, kind=self.kind)
            expected = row.original_benefit
            if row.subject_to_family_maximum and self.total_original_benefits:
                expected = _floor_dime_validated(
                    row.original_benefit
                    * min(
                        Fraction(1),
                        self.available_for_auxiliaries
                        / self.total_original_benefits,
                    )
                )
            if row.standard_rate != expected:
                raise InvalidFamilyInput(
                    "Standard rate differs from proportional maximum"
                )
            if (
                not self.redistribution_applied
                and row.family_maximum_rate != expected
            ):
                raise InvalidFamilyInput(
                    "Unredistributed rate differs from standard rate"
                )
            if (
                row.subject_to_family_maximum
                and (
                    not self.redistribution_applied or row.own_benefit is None
                )
                and row.deduction_reason is None
                and row.counted_against_maximum
                != row.family_maximum_rate
                + row.reserved_work_deduction
                - row.deduction
            ):
                raise InvalidFamilyInput(
                    "Counted rate differs from maximum rate"
                )
        expected_total = (self.worker_benefit or Fraction(0)) + sum(
            (row.auxiliary_payable for row in beneficiaries), Fraction(0)
        )
        expected_whole = (self.whole_dollar_worker or 0) + sum(
            row.whole_dollar_auxiliary for row in beneficiaries
        )
        if self.record_total != expected_total:
            raise InvalidFamilyInput("record_total differs from payments")
        if self.record_total_whole_dollars != expected_whole:
            raise InvalidFamilyInput(
                "record_total_whole_dollars differs from payments"
            )

    def by_id(self) -> Mapping[str, BeneficiaryBenefit]:
        _check_seal(self)
        return MappingProxyType(
            {
                row.beneficiary_id: _detached_result(row)
                for row in self.beneficiaries
            }
        )


# ---------------------------------------------------------------------------
# The family computation
# ---------------------------------------------------------------------------
@_validated_entry
def original_benefit(
    role: Role,
    kind: FamilyKind,
    pia: Fraction,
    basis: Fraction | None = None,
    *,
    parent_count: int | None = None,
) -> Fraction:
    """The OB: the statutory share of the PIA, dime-floored.

    402(b)/(c)(2) 1/2; 402(d)(2) 1/2, or 3/4 after the worker's death;
    402(e)/(f)(2)(A) 100 percent (or the widow(er)'s larger OB basis);
    402(g)(2) 3/4; 402(h)(2) 82.5 percent for one entitled parent,
    75 percent for each of two (RS 00209.015).

    Role/record compatibility and argument applicability are identical to
    the family entry point. Only widow(er) roles accept ``basis``; only
    parents accept ``parent_count`` (omission means one entitled parent).
    Incompatible combinations are input errors, never coverage refusals.
    """
    _input_type(role, Role, "role")
    _input_type(kind, FamilyKind, "kind")
    pia = _dimes(pia, "PIA")
    if basis is not None:
        basis = _dimes(basis, "basis")
    _check_role_arguments(
        role, kind=kind, basis=basis, parent_count=parent_count
    )
    if role in _SPOUSE_ROLES:
        share = Fraction(1, 2)
    elif role is Role.CHILD:
        share = (
            Fraction(3, 4) if kind is FamilyKind.SURVIVOR else Fraction(1, 2)
        )
    elif role in _WIDOW_ROLES:
        if basis is not None:
            if basis < pia:
                raise InvalidFamilyInput(
                    "A widow(er) OB basis cannot be below the death PIA"
                )
            return basis
        share = Fraction(1)
    elif role is Role.MOTHER_FATHER:
        share = Fraction(3, 4)
    elif role is Role.PARENT:
        parent_count = 1 if parent_count is None else parent_count
        share = Fraction(165, 200) if parent_count == 1 else Fraction(3, 4)
    else:
        raise ValueError(f"No original benefit is defined for {role}")
    return _floor_dime_validated(share * pia)


def _with_effective_cohort(beneficiary: Beneficiary) -> Beneficiary:
    """Resolve one person's cohort without changing the caller's inputs.

    RS 00615.003/.010: a known FRA governs both own-RIB and spouse bounds;
    RS 00615.301B.2: a known widow cohort also fixes its reduction period.
    """
    own = beneficiary.own_benefit
    year = beneficiary.birth_year
    if (
        own is not None
        and own.birth_year is not None
        and year is not None
        and own.birth_year != year
    ):
        raise InvalidFamilyInput(
            "own_benefit.birth_year differs from birth_year"
        )
    if year is None and own is not None:
        year = own.birth_year
    if year is None:
        return beneficiary
    if own is not None and own.birth_year is None:
        own = _replace_declared(own, birth_year=year)
    if year == beneficiary.birth_year and own is beneficiary.own_benefit:
        return beneficiary
    return _replace_declared(beneficiary, birth_year=year, own_benefit=own)


def _check_beneficiary_inputs(
    beneficiary: Beneficiary, state: RecordState, params: SSAParameters
) -> None:
    """Input errors for a beneficiary with a resolved cohort, before refusal."""
    _check_role_arguments(
        beneficiary.role,
        kind=state.kind,
        basis=beneficiary.original_benefit_basis,
    )
    own = beneficiary.own_benefit
    if beneficiary.role in _WIDOW_ROLES:
        if beneficiary.birth_year is not None:
            # All birth-year inputs use SSA's January 2-January 1 cohort,
            # so even a boundary cohort fixes exactly one .301B.2 period.
            year = beneficiary.birth_year
            expected = _widow_reduction_period_months_validated(
                date(year, 1, 2)
            )
            period = beneficiary.reduction_period_months
            if period is not None and period != expected:
                raise InvalidFamilyInput(
                    "reduction period differs from birth cohort"
                )
            _months(beneficiary.reduction_months, "reduction_months", expected)
        if beneficiary.reduction_months and (
            beneficiary.reduction_period_months is None
        ):
            raise InvalidFamilyInput(
                "A reduced widow(er) needs reduction_period_months"
            )
        if (
            beneficiary.reduction_period_months is not None
            and beneficiary.reduction_months
            > beneficiary.reduction_period_months
        ):
            raise InvalidFamilyInput("reduction_months exceed the period")
        if (
            beneficiary.role in _AGED_WIDOW_ROLES
            and own is not None
            and own.kind is OwnBenefitKind.OLD_AGE
            and beneficiary.birth_year is None
        ):
            raise InvalidFamilyInput(
                "A dually entitled widow(er) needs birth_year"
            )
    if beneficiary.role in _AGE_REDUCED_ROLES and beneficiary.role not in (
        _WIDOW_ROLES
    ):
        _cohort_reduction_months(
            beneficiary.reduction_months,
            beneficiary.birth_year,
            params,
            "reduction_months",
        )
    basis = beneficiary.original_benefit_basis
    if basis is not None and basis < state.pia:
        raise InvalidFamilyInput(
            "A widow(er) OB basis cannot be below the death PIA"
        )
    if own is not None:
        _check_own_benefit(own, params)


def _refuse_beneficiary(
    beneficiary: Beneficiary, payment_month: YearMonth
) -> None:
    """Coverage refusals for one beneficiary whose inputs are valid."""
    bid = beneficiary.beneficiary_id
    if beneficiary.own_benefit is not None:
        _refuse_own_benefit(beneficiary.own_benefit)
    if beneficiary.role is Role.DISABLED_WIDOW:
        if payment_month < _construct_declared(YearMonth, 1984, 1):
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.DISABLED_WIDOW_UNDER_60,
                "DWB payment months before January 1984 used an additional "
                "pre-60 reduction (RS 00615.310B.1/B.3), not implemented",
                beneficiary_id=bid,
            )
        if beneficiary.own_benefit is not None:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
                "DWB with own RIB or DIB needs entitlement sequencing not "
                "settled by RS 00615.315 (which governs WIB/DWB election)",
                beneficiary_id=bid,
            )
    for condition in sorted(beneficiary.conditions, key=lambda c: c.value):
        if (
            condition is BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET
            and payment_month >= _construct_declared(YearMonth, 2024, 1)
        ):
            # Pub. L. 118-273; GN 02608.100: repeal is retroactive to
            # benefits for months after December 2023, not enactment month.
            continue
        reason, detail = _BENEFICIARY_CONDITION_REASONS[condition]
        raise _computed(
            FamilyConfigurationUnsupported, reason, detail, beneficiary_id=bid
        )
    own = beneficiary.own_benefit
    if beneficiary.role in _WIDOW_ROLES and own is not None:
        if own.kind is OwnBenefitKind.DISABILITY:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
                "a widow(er) also entitled to DIB (402(q)(3)(C); POMS "
                "RS 00615.350) is not implemented",
                beneficiary_id=bid,
            )
        if beneficiary.birth_year < _FIRST_METHOD_B_WIDOW_BIRTH_YEAR:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
                "own-RIB widow(er)s before cohort 1929 are outside G's "
                "implementation boundary; the source boundary is "
                "January 2, 1928 (POMS RS 00615.010/.020B), so cohort "
                "1928 is a known over-refusal",
                beneficiary_id=bid,
            )
    if (
        beneficiary.role in (Role.SPOUSE, Role.DIVORCED_SPOUSE)
        and own is not None
        and not beneficiary.own_benefit_first
        and own.kind is OwnBenefitKind.DISABILITY
    ):
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
            "a spouse entitled to spouse's benefits before a DIB (B then "
            "HA; POMS RS 00615.260: deemed RIB filing and a later RIB "
            "change the excess) is not implemented",
            beneficiary_id=bid,
        )


@dataclass
class _Row:
    beneficiary: Beneficiary
    entitled: bool
    subject: bool
    ob: Fraction
    own_base: Fraction | None
    own_mba: Fraction | None
    standard: Fraction = Fraction(0)
    rate: Fraction = Fraction(0)
    counted: Fraction = Fraction(0)
    mother_father_rate: Fraction = Fraction(0)
    note: str = ""
    dwb_under_60: bool = False

    @property
    def dual(self) -> bool:
        return self.own_mba is not None


def _dwb_under_60(beneficiary: Beneficiary, payment_month: YearMonth) -> bool:
    """A DWB month in which the SSA birth cohort cannot yet have attained 60.

    Cohort Y (born January 2, Y through January 1, Y+1) attains 60 during
    Y+60, so every month of Y+59 and earlier is under 60. Months of Y+60
    depend on the unsupplied birth month and are not treated as under 60.
    """
    return (
        beneficiary.role is Role.DISABLED_WIDOW
        and beneficiary.birth_year is not None
        and payment_month.year <= beneficiary.birth_year + 59
    )


def _is_entitled(
    beneficiary: Beneficiary,
    pia: Fraction,
    own_mba: Fraction | None,
    *,
    parent_ob: Fraction | None = None,
) -> tuple[bool, str]:
    own = beneficiary.own_benefit
    if own is None:
        return True, ""
    if beneficiary.role in _SPOUSE_ROLES and own.pia * 2 >= pia:
        return False, "own PIA at least one-half of the PIA (402(b)(1)(D))"
    if beneficiary.role in _WIDOW_ROLES and own.kind is (
        OwnBenefitKind.OLD_AGE
    ):
        # 402(e)(1)(D) compares with the PIA "as determined after
        # application of subparagraphs (B) and (C) of paragraph (2)": the
        # windexed PIA, or the PIA deemed equal to the deceased's
        # credit-increased benefit, i.e. the widow(er)'s OB basis.
        deemed_pia = beneficiary.original_benefit_basis or pia
        if own_mba >= deemed_pia:
            return False, "own RIB not less than the PIA (402(e)(1)(D))"
    if (
        beneficiary.role is Role.PARENT
        and own.kind is OwnBenefitKind.OLD_AGE
        and own_mba >= parent_ob
    ):
        return False, "own RIB not less than parent's OB (RS 00209.001)"
    if (
        beneficiary.role is Role.MOTHER_FATHER
        and own.kind is OwnBenefitKind.OLD_AGE
        and own_mba * 4 >= pia * 3
    ):
        return False, "own RIB not less than 3/4 of the PIA (402(g)(1)(C))"
    return True, ""


def _proportional(rows: Sequence[_Row], available: Fraction) -> list[Fraction]:
    """RS 00615.756: OB x available / total OB, not above OB, dime-floored."""
    total = sum((row.ob for row in rows), Fraction(0))
    if total <= available:
        return [row.ob for row in rows]
    return [
        max(
            Fraction(0),
            min(row.ob, _floor_dime_validated(row.ob * available / total)),
        )
        for row in rows
    ]


@_validated_entry
def maximum_redistribution_rates(
    original_benefits: Mapping[str, Fraction],
    available: Fraction,
    *,
    deductee_payables: Mapping[str, Fraction],
    age_reductions: Mapping[str, Fraction] | None = None,
    other_deductions: Mapping[str, Fraction] | None = None,
) -> Mapping[str, Fraction]:
    """GN 02603.050C: non-deductee OB x PTAP / non-deductee TOTOB.

    ``available`` is the maximum less the worker's PIA in life cases.
    PTAP subtracts deductees' payable amounts, auxiliary age reductions,
    and any other reserved deductions supplied by the caller. Rates are
    capped at OB and dime-floored. R2 may supply permanent or temporary
    deductees' payable amounts without changing this distribution formula;
    R2 remains responsible for deduction amounts and the household-specific
    denominator in GN 02603.050D's temporary cases: supply each eligible
    household's OB mapping separately. This helper applies no earnings-test
    or other deduction itself.
    """
    for name, mapping in (
        ("original_benefits", original_benefits),
        ("deductee_payables", deductee_payables),
        ("age_reductions", {} if age_reductions is None else age_reductions),
        (
            "other_deductions",
            {} if other_deductions is None else other_deductions,
        ),
    ):
        if not isinstance(mapping, Mapping):
            raise _InvalidInputType(f"{name} must be a mapping")
        for key in mapping:
            _input_text(key, f"{name} key")
    obs = {
        key: _dimes(value, "OB") for key, value in original_benefits.items()
    }
    payable = {
        key: _dimes(value, "deductee payable")
        for key, value in deductee_payables.items()
    }
    ages = {
        key: _dimes(value, "deductee age reduction")
        for key, value in (age_reductions or {}).items()
    }
    others = {
        key: _dimes(value, "other deduction")
        for key, value in (other_deductions or {}).items()
    }
    if not set(payable) <= set(obs) or not (set(ages) | set(others)) <= set(
        payable
    ):
        raise InvalidFamilyInput(
            "Deduction ids must identify deductees with OBs"
        )
    pool = _dimes(available, "available") - sum(payable.values(), Fraction(0))
    pool -= sum(ages.values(), Fraction(0)) + sum(others.values(), Fraction(0))
    nondual = {key: value for key, value in obs.items() if key not in payable}
    total = sum(nondual.values(), Fraction(0))
    if total == 0:
        return MappingProxyType({key: Fraction(0) for key in nondual})
    return MappingProxyType(
        {
            key: max(
                Fraction(0), min(ob, _floor_dime_validated(ob * pool / total))
            )
            for key, ob in nondual.items()
        }
    )


def _parisi_counted(
    row: _Row, state: RecordState, params: SSAParameters
) -> tuple[Fraction, Fraction]:
    """GN 02603.050A/C: partial payable plus auxiliary age reduction.

    The own-RIB reduction is not an auxiliary age reduction (GN
    02603.060B.2: $2.40 payable + $0.90 reduction, not the $16 own-RIB
    reduction). Together they are the .045 amount "before any applicable
    reduction for age"; GN 02603.050A.2 disregards a dual rate whose
    before-age amount is zero. Own delayed credits and redistribution with an actually limiting
    RIB-LIM remain refused: none of the captured worked cases settles
    those interacting amounts. A considered but nonlimiting RIB-LIM
    changes no rate (RS 00615.320A.3).
    """
    beneficiary = row.beneficiary
    own = beneficiary.own_benefit
    if own.delayed_credit_months:
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.PARISI_AMBIGUOUS,
            "redistribution around delayed credits on the own benefit is "
            "not settled by GN 02603.050C or the captured examples",
            beneficiary_id=beneficiary.beneficiary_id,
        )
    if beneficiary.role in _WIDOW_ROLES and state.rib_lim_benefit is not None:
        # RS 00615.320A.3: consideration alone does not impose a limit.
        # The WIB after the maximum and age reduction must exceed both
        # thresholds. A nonlimiting RIB-LIM changes no PTAP amount.
        unlimited, _ = _reduce_and_offset(
            row, state, params, apply_rib_lim=False
        )
        limit = max(
            state.rib_lim_benefit,
            _floor_dime_validated(
                _statutory_rates_validated(params).rib_lim_share * state.pia
            ),
        )
        if unlimited > limit:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.PARISI_AMBIGUOUS,
                "redistribution around a RIB-LIM limited widow(er)",
                beneficiary_id=beneficiary.beneficiary_id,
            )
    age_adjusted, payable = _reduce_and_offset(row, state, params)
    method_c = (
        beneficiary.role in (Role.SPOUSE, Role.DIVORCED_SPOUSE)
        and beneficiary.own_benefit_first
    )
    if payable == 0:
        before_age = row.standard - (own.pia if method_c else row.own_mba)
        # Source conflict us:oasdi-dual-entitlement-zero-after-age-reduction
        # GN 02603.050A applies its exceptions 2 and 3 under .045, which
        # counts the dual rate "before any applicable reduction for age".
        # A before-age zero is disregarded (.050A.2); a positive before-age
        # amount is a partial rate (.050A.3), counted whole as the age term.
        # A positive payable below counts the same total.
        return Fraction(0), max(Fraction(0), before_age)
    if method_c:
        excess = max(Fraction(0), row.standard - own.pia)
        age_reduction = excess - _spouse_age_reduced_validated(
            excess, beneficiary.reduction_months, params
        )
    else:
        age_reduction = row.standard - age_adjusted
    return payable, age_reduction


def _refuse_historical_auxiliary(
    row: _Row,
    state: RecordState,
    params: SSAParameters,
    *,
    apply_rib_lim: bool,
) -> None:
    """Refuse unresolved RS 00615.005C.2 money history after the maximum.

    Earliest reduced entitlement is 62 for spouses and 50 for DWB
    (402(b)/(c)/(e)/(f); RS 00615.005A/.310A). Aged WIB can carry earlier
    DWB history after conversion at FRA, so its possible age is also 50.
    Ordinary aged WIB starts at 60, but these inputs do not attest that
    there was no prior DWB. Current
    reduction months after an ARF cannot date the original entitlement.
    Historical current-money reductions are absent. The full interval
    from zero to the unreduced rate therefore supplies conservative bounds;
    a modern reduction fraction cannot bound its historical counterpart.
    Apply the same offset, RIB-LIM and care minimum to both endpoints.
    If both settle the amount, the missing history cannot change it.

    For beneficiaries subject to the maximum, the pre-offset rate must
    also be settled: 403(a)(5) carries that rate to later months. Outside
    the maximum, a settled payable suffices and any ordinary intermediate
    rate remains diagnostic, as with divorced-spouse care history.
    """
    beneficiary = row.beneficiary
    role = beneficiary.role
    if role in (Role.SPOUSE, Role.DIVORCED_SPOUSE):
        first_age = 62
        if isinstance(beneficiary.child_in_care, str):
            return
    elif role is Role.DISABLED_WIDOW:
        # Source conflict us:oasdi-dwb-1984-pre-1978-history
        # RS 00615.301B.1.e: "all disabled widow(er)s under age 60 receive
        # .715 of the full unreduced WIB for 1/84 and later", whatever the
        # entitlement date; .005C.2's money history governs only from 60.
        if row.dwb_under_60:
            return
        first_age = 50
    elif role in _AGED_WIDOW_ROLES:
        first_age = 50
    else:
        return
    year = beneficiary.birth_year
    if (
        year is None
        or year + first_age >= 1978
        or (
            role is not Role.DISABLED_WIDOW
            and not beneficiary.reduction_months
        )
    ):
        return

    own = beneficiary.own_benefit
    low, high = Fraction(0), row.rate
    if role in (Role.SPOUSE, Role.DIVORCED_SPOUSE):
        # Source conflict us:oasdi-dual-entitlement-pre-1978-history
        if own is not None and beneficiary.own_benefit_first:
            excess = max(Fraction(0), row.rate - own.pia)
            high = max(Fraction(0), row.rate - (own.pia - row.own_base))
            low = max(Fraction(0), high - excess)
    else:
        if apply_rib_lim and state.rib_lim_benefit is not None:
            limit = max(
                state.rib_lim_benefit,
                _floor_dime_validated(
                    _statutory_rates_validated(params).rib_lim_share
                    * state.pia
                ),
            )
            low, high = min(low, limit), min(high, limit)
        low = max(low, row.mother_father_rate)
        high = max(high, row.mother_father_rate)
    historical_age_interval = (low, high)
    if own is not None and not row.subject:
        low = max(Fraction(0), low - row.own_mba)
        high = max(Fraction(0), high - row.own_mba)
    if low == high:
        if historical_age_interval[0] != historical_age_interval[1]:
            note = (
                "pre-1978 history does not affect auxiliary payable; "
                "age_adjusted_rate displays an ordinary diagnostic rate "
                "within historical bounds "
                f"{historical_age_interval[0]} to {historical_age_interval[1]}"
            )
            if note not in row.note:
                row.note += ("; " if row.note else "") + note
        return
    raise _computed(
        FamilyConfigurationUnsupported,
        UnsupportedReason.REDUCED_BENEFIT_HISTORY_BEFORE_1978,
        f"a reduced {role.value} for cohort {year} could first be entitled "
        "before January 1978; RS 00615.005C.2 needs the historical money "
        "reduction and unreduced rate, and the supplied offsets, maximum "
        "and care minimum do not settle the amount without them",
        beneficiary_id=beneficiary.beneficiary_id,
    )


def _beneficiary_age_factor(
    beneficiary: Beneficiary, params: SSAParameters
) -> Fraction:
    """Declared 402(q) factor, retained before dime rounding for 203(a)(5)."""
    if beneficiary.role is Role.DIVORCED_SPOUSE and isinstance(
        beneficiary.child_in_care, str
    ):
        return Fraction(1)
    if beneficiary.role in _SPOUSE_ROLES:
        return 1 - _spouse_reduction_fraction_validated(
            beneficiary.reduction_months, params
        )
    if beneficiary.role is Role.DISABLED_WIDOW:
        return Fraction(715, 1000)
    if beneficiary.role in _WIDOW_ROLES and beneficiary.reduction_months:
        return 1 - _survivor_reduction_fraction_validated(
            beneficiary.reduction_months,
            beneficiary.reduction_period_months,
            params,
        )
    return Fraction(1)


def _reduce_and_offset(
    row: _Row,
    state: RecordState,
    params: SSAParameters,
    *,
    apply_rib_lim: bool = True,
) -> tuple[Fraction, Fraction]:
    """402(q) (and the RIB-LIM), then 402(k)(3)(A).

    Returns ``(age_adjusted, payable)``: the auxiliary benefit after its
    age reduction, and the amount payable on this record after the
    dual-entitlement offset. ``apply_rib_lim=False`` lets the Parisi
    coverage check establish whether a considered RIB-LIM actually limits
    the rate after the family maximum and age reduction (RS 00615.320A.3).
    """
    beneficiary = row.beneficiary
    own = beneficiary.own_benefit
    rate = row.rate
    _refuse_historical_auxiliary(
        row, state, params, apply_rib_lim=apply_rib_lim
    )
    if beneficiary.role is Role.DIVORCED_SPOUSE and isinstance(
        beneficiary.child_in_care, str
    ):
        # RS 00615.010/.201A.2: current care overrides both aged methods.
        # The role retains its 403(a)(3)(C) outside-maximum status.
        return rate, (
            rate if own is None else max(Fraction(0), rate - row.own_mba)
        )
    if beneficiary.role in (Role.SPOUSE, Role.DIVORCED_SPOUSE):
        if own is None or not beneficiary.own_benefit_first:
            reduced = _spouse_age_reduced_validated(
                rate, beneficiary.reduction_months, params
            )
            if own is None:
                return reduced, reduced
            # B then A (method B, POMS RS 00615.240): 402(q)(3)(A) does not
            # apply, so the spouse benefit keeps its 402(q)(1) reduction
            # and is paid in excess of the RIB (with any credits, RS
            # 00615.694A).
            return reduced, max(Fraction(0), reduced - row.own_mba)
        # 402(q)(3)(B)/(C), method C (POMS RS 00615.250): the spouse
        # benefit is reduced by the own benefit's 402(q) reduction plus the
        # spousal reduction of the excess over the own PIA.
        excess = max(Fraction(0), rate - own.pia)
        reduced_excess = _spouse_age_reduced_validated(
            excess, beneficiary.reduction_months, params
        )
        age_adjusted = max(
            Fraction(0),
            rate - (own.pia - row.own_base) - (excess - reduced_excess),
        )
        # 402(k)(3)(A) subtracts the own benefit with any delayed credits
        # (RS 00615.694: combined amount without credits, less the RIB
        # with credits).
        return age_adjusted, max(Fraction(0), age_adjusted - row.own_mba)
    if beneficiary.role in _WIDOW_ROLES:
        reduced = rate
        if beneficiary.role is Role.DISABLED_WIDOW:
            # 402(e)/(f), 402(q)(8); RS 00615.310B.1/B.3 and .301:
            # fixed 28.5% from January 1984, reduction rounded up to dime.
            reduced = rate - _ceil_dime_validated(rate * Fraction(285, 1000))
        elif beneficiary.reduction_months:
            reduced = _survivor_age_reduced_validated(
                rate,
                beneficiary.reduction_months,
                beneficiary.reduction_period_months,
                params,
            )
        if apply_rib_lim and state.rib_lim_benefit is not None:
            rates = _statutory_rates_validated(params)
            limit = max(
                state.rib_lim_benefit,
                _floor_dime_validated(rates.rib_lim_share * state.pia),
            )
            reduced = min(reduced, limit)
        # RS 00615.340/.010: compare with what a mother/father would
        # receive after the maximum. RIB-LIM cannot override this minimum.
        # 402(k)(3)(A) still offsets the own benefit below.
        reduced = max(reduced, row.mother_father_rate)
    else:
        reduced = rate
    if own is None:
        return reduced, reduced
    return reduced, max(Fraction(0), reduced - row.own_mba)


@_validated_entry
def family_benefits(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    *,
    payment_month: YearMonth,
    params: SSAParameters,
    standalone: bool,
) -> FamilyBenefits:
    """Gross monthly benefits on one record for one payment month.

    Order (see the module docstring): OB, family-maximum reduction,
    RS 00615.768 redistribution, 402(q) age reduction and RIB-LIM,
    402(k)(3)(A) dual entitlement, 215(g) whole dollars.

    :func:`household_benefits` is the integration entry point. This
    single-record function runs only with ``standalone=True``, the
    caller's statement that the record stands alone: no beneficiary is
    entitled on another record (403(a)(3)(A); RS 00615.768A), and a worker
    who is an auxiliary elsewhere has declared that benefit. Anything else
    is a household, and computing it one record at a time is the silent
    single-worker answer G exists to refuse.

    Input errors (:class:`InvalidFamilyInput`) are raised before any
    coverage refusal, so an invalid family is never counted as a gap.
    """
    if standalone is not True:
        raise InvalidFamilyInput(
            "family_benefits computes one record in isolation; pass "
            "standalone=True only when no beneficiary is entitled on "
            "another record, and use household_benefits otherwise"
        )
    return _family_benefits(state, beneficiaries, payment_month, params)


def _check_family_inputs(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    payment_month: YearMonth,
    params: SSAParameters,
) -> tuple[Beneficiary, ...]:
    """Check every input before refusal; return copies with resolved cohorts."""
    # Household paths check every record here before household refusals.
    _statutory_rates_validated(params)
    state = _checked_input(state, RecordState, "state")
    _checked_input(payment_month, YearMonth, "payment_month")
    _input_sequence(beneficiaries, "beneficiaries")
    beneficiaries = tuple(
        _with_effective_cohort(_checked_input(b, Beneficiary, "beneficiary"))
        for b in beneficiaries
    )
    if (
        state.eligibility_year is not None
        and state.eligibility_year > payment_month.year
    ):
        raise InvalidFamilyInput(
            f"eligibility year {state.eligibility_year} is after the "
            f"payment month {_month_text_validated(payment_month)}"
        )
    if (
        state.first_dib_entitlement is not None
        and state.first_dib_entitlement > payment_month
    ):
        raise InvalidFamilyInput(
            "first DIB entitlement "
            f"{_month_text_validated(state.first_dib_entitlement)} is after "
            f"the payment month {_month_text_validated(payment_month)}"
        )
    _check_retirement_eligibility(
        state.kind, state.eligibility_year, state.worker_birth_year
    )
    if state.worker is not None:
        _check_own_benefit(state.worker, params)
    ids = [b.beneficiary_id for b in beneficiaries]
    if len(set(ids)) != len(ids):
        raise InvalidFamilyInput("beneficiary_id values must be unique")
    for beneficiary in beneficiaries:
        _check_beneficiary_inputs(beneficiary, state, params)
        if isinstance(beneficiary.child_in_care, str):
            child = next(
                (
                    b
                    for b in beneficiaries
                    if b.beneficiary_id == beneficiary.child_in_care
                ),
                None,
            )
            if child is None or child.role is not Role.CHILD:
                raise InvalidFamilyInput(
                    "child_in_care must name an entitled child on the "
                    "same record in the payment month"
                )
    if RecordCondition.WORKER_NOT_ENTITLED in state.conditions and (
        state.kind is not FamilyKind.RETIREMENT
        or any(b.role is not Role.DIVORCED_SPOUSE for b in beneficiaries)
    ):
        raise InvalidFamilyInput(
            "An eligible unclaimed worker record is retirement-only and "
            "admits only independently entitled divorced spouses"
        )
    return beneficiaries


def _entitled_parent_count(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    params: SSAParameters,
) -> tuple[int, frozenset[str]]:
    """Resolve 402(h)(2)'s count and the parents (h)(1)(D) excludes.

    402(h)(1)(D) tests an own RIB against 82.5 percent of the PIA when the
    parent's benefit "is determinable under paragraph (2)(A)", and against
    75 percent "in any other case". The entitled set must satisfy that test
    for every parent at once: each entitled parent at its own rate, and
    each excluded potential parent at the rate it would share. RS
    00209.015 counts an own-DIB parent as technically entitled. Returns
    the count and the ids excluded at the two-parent rate. More than two
    declared parents needs a separate rule.
    """
    parents = [b for b in beneficiaries if b.role is Role.PARENT]
    if len(parents) > 2:
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.PARENT_BENEFIT,
            "more than two declared parents is outside the one/two-parent "
            "rates settled by 402(h)(2) and RS 00209.015",
        )
    one_ob = _original_benefit_validated(
        Role.PARENT, FamilyKind.SURVIVOR, state.pia
    )
    two_ob = _original_benefit_validated(
        Role.PARENT, FamilyKind.SURVIVOR, state.pia, parent_count=2
    )
    potential = []
    for parent in parents:
        own = parent.own_benefit
        own_mba = (
            None
            if own is None
            else _own_monthly_benefit_validated(own, params)[1]
        )
        if own is not None and own.kind is OwnBenefitKind.OLD_AGE:
            if own_mba >= one_ob:
                continue
        potential.append((parent, own_mba))
    in_band = [
        parent
        for parent, own_mba in potential
        if parent.own_benefit is not None
        and parent.own_benefit.kind is OwnBenefitKind.OLD_AGE
        and own_mba >= two_ob
    ]
    if len(potential) < 2 or not in_band:
        return max(1, len(potential)), frozenset()
    # Source conflict us:oasdi-parent-entitlement-count-interval
    # A RIB in [75%, 82.5%) fails beside an entitled parent and passes
    # alone. With one such parent, only "the other parent alone" satisfies
    # 402(h)(1)(D) for both; with two, either parent alone does.
    if len(in_band) == 2:
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.PARENT_BENEFIT,
            "two parents with own RIB between the 75% and 82.5% OBs: "
            "402(h)(1)(D) is satisfied by either parent alone",
            beneficiary_id=in_band[0].beneficiary_id,
        )
    return 1, frozenset({in_band[0].beneficiary_id})


def _mother_father_care_rate(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    caregiver: Beneficiary,
    payment_month: YearMonth,
    params: SSAParameters,
) -> Fraction:
    """RS 00615.340 minimum, using the existing mother/father rules.

    Replace only the caregiver's entitlement for the comparison: 75% OB,
    its maximum share, and any settled Parisi redistribution. The
    hypothetical 202(g) mother/father is subject to the maximum, including
    for a surviving divorced caregiver (RS 00615.682). Only the actual
    202(e)/(f) surviving divorced spouse stays outside (403(a)(3)(C)).
    The comparison has no age reduction or RIB-LIM; its own-benefit offset
    is applied by the actual widow computation. Other care flags are
    cleared so this comparison cannot recursively compare widow floors.
    """
    comparison = []
    for member in beneficiaries:
        if member.beneficiary_id == caregiver.beneficiary_id:
            comparison.append(
                _replace_declared(
                    member,
                    role=Role.MOTHER_FATHER,
                    reduction_months=0,
                    reduction_period_months=None,
                    original_benefit_basis=None,
                    child_in_care=None,
                )
            )
        elif member.role in _WIDOW_ROLES:
            comparison.append(_replace_declared(member, child_in_care=False))
        else:
            comparison.append(member)
    result = _family_benefits(state, comparison, payment_month, params)
    return result.by_id()[caregiver.beneficiary_id].age_adjusted_rate


def _refuse_widow_drc_savings_clause(
    state: RecordState, rows: Sequence[_Row]
) -> None:
    """Refuse unresolved May 1978 protection before maximum apportionment.

    An omitted first-ever DIB date is unknown history, not proof that
    current eligibility was the worker's first eligibility. RS 00615.736B.2b
    permits modern eligibility after ended prior DIB. A known first-ever
    DIB date after May 1978 excludes that earlier DIB route; otherwise a
    subject widow(er)'s OB above the death PIA with another subject survivor
    requires the caller's explicit no-protection attestation. The schema
    does not distinguish deceased DRCs from windexing in that larger OB.
    Earlier snapshot/history refusals remain conservative.
    """
    if state.kind is not FamilyKind.SURVIVOR:
        return
    if state.widow_drc_savings_clause is True:
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE,
            "a May 1978 survivor protected by the widow(er)'s DRC "
            "saving clause (RS 00615.712) is not implemented",
        )
    if state.widow_drc_savings_clause is False:
        return
    subject = [row for row in rows if row.subject]
    possible_drc_protection = len(subject) > 1 and any(
        row.beneficiary.role in _WIDOW_ROLES and row.ob > state.pia
        for row in subject
    )
    if (
        state.eligibility_year is None
        or state.eligibility_year < FIRST_SUPPORTED_ELIGIBILITY_YEAR
        or (
            state.first_dib_entitlement is not None
            and state.first_dib_entitlement
            <= _construct_declared(YearMonth, 1978, 5)
        )
        or (state.first_dib_entitlement is None and possible_drc_protection)
    ):
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN,
            "a survivor snapshot must attest whether May 1978 "
            "entitlement and widow(er) deceased-worker DRCs invoke "
            "RS 00615.712; an omitted first DIB date is unknown history",
        )


def _family_benefits(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    payment_month: YearMonth,
    params: SSAParameters,
) -> FamilyBenefits:
    state = _checked_input(state, RecordState, "state")
    rates = _statutory_rates_validated(params)
    beneficiaries = _check_family_inputs(
        state, beneficiaries, payment_month, params
    )
    _refuse_record(state)
    if state.deferred_refusal is not None:
        raise _computed(
            FamilyConfigurationUnsupported, *state.deferred_refusal
        )
    if (
        payment_month.year,
        payment_month.month,
    ) < FIRST_SUPPORTED_PAYMENT_MONTH:
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.PAYMENT_MONTH_BEFORE_1983,
            "months before 1983 are outside the post-May-1982 rounding "
            "rules this layer implements",
        )
    for beneficiary in beneficiaries:
        _refuse_beneficiary(beneficiary, payment_month)
    ieds = RecordCondition.WORKER_NOT_ENTITLED in state.conditions
    if ieds and (
        payment_month < _construct_declared(YearMonth, 1985, 1)
        or (
            RecordCondition.WINDFALL_ELIMINATION_PROVISION in state.conditions
            and payment_month < _construct_declared(YearMonth, 2024, 1)
        )
    ):
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.INDEPENDENT_DIVORCED_SPOUSE,
            "IEDS before January 1985, or on a WEP-affected worker record "
            "before January 2024, is not implemented (RS 00202.100)",
        )
    parent_count, excluded_parents = _entitled_parent_count(
        state, beneficiaries, params
    )
    two_parent_ob = (
        _original_benefit_validated(
            Role.PARENT, FamilyKind.SURVIVOR, state.pia, parent_count=2
        )
        if excluded_parents
        else None
    )
    life_case = state.kind is not FamilyKind.SURVIVOR and not ieds
    worker_benefit = None
    if state.kind is FamilyKind.RETIREMENT and not ieds:
        worker_benefit = _own_monthly_benefit_validated(state.worker, params)[
            1
        ]
    elif state.kind is FamilyKind.DISABILITY:
        worker_benefit = state.pia

    rows: list[_Row] = []
    for beneficiary in beneficiaries:
        own_base = own_mba = None
        if beneficiary.own_benefit is not None:
            own_base, own_mba = _own_monthly_benefit_validated(
                beneficiary.own_benefit, params
            )
        ob = _original_benefit_validated(
            beneficiary.role,
            state.kind,
            state.pia,
            beneficiary.original_benefit_basis,
            parent_count=(
                parent_count if beneficiary.role is Role.PARENT else None
            ),
        )
        entitled, note = _is_entitled(
            beneficiary,
            state.pia,
            own_mba,
            parent_ob=(
                two_parent_ob
                if beneficiary.beneficiary_id in excluded_parents
                else ob
            ),
        )
        rows.append(
            _Row(
                beneficiary=beneficiary,
                entitled=entitled,
                subject=entitled and beneficiary.role not in _OUTSIDE_MAXIMUM,
                ob=ob if entitled else Fraction(0),
                own_base=own_base,
                own_mba=own_mba,
                note=note,
                dwb_under_60=_dwb_under_60(beneficiary, payment_month),
            )
        )

    _refuse_widow_drc_savings_clause(state, rows)
    available = state.family_maximum - (state.pia if life_case else 0)
    subject = [row for row in rows if row.subject]
    total_ob = sum((row.ob for row in subject), Fraction(0))
    binding = total_ob > available
    for row, share in zip(
        subject, _proportional(subject, available), strict=True
    ):
        row.standard = row.rate = row.counted = share
    for row in rows:
        if row.entitled and not row.subject:
            row.standard = row.rate = row.ob

    entitled_children = any(
        row.entitled and row.beneficiary.role is Role.CHILD for row in rows
    )
    for row in rows:
        beneficiary = row.beneficiary
        if row.entitled and beneficiary.role is Role.DIVORCED_SPOUSE:
            if entitled_children and beneficiary.child_in_care is None:
                raise _computed(
                    FamilyConfigurationUnsupported,
                    UnsupportedReason.DIVORCED_SPOUSE_CHILD_IN_CARE_UNKNOWN,
                    "a divorced spouse with an entitled child must attest "
                    "current child-in-care status (RS 00615.010/.201A.2)",
                    beneficiary_id=beneficiary.beneficiary_id,
                )
            if (
                not isinstance(beneficiary.child_in_care, str)
                and beneficiary.first_entitlement_child_in_care is not False
            ):
                ordinary = _reduce_and_offset(row, state, params)
                exempt = (
                    row.rate,
                    (
                        row.rate
                        if row.own_mba is None
                        else max(Fraction(0), row.rate - row.own_mba)
                    ),
                )
                # 202(k)(3)(A)'s zero floor can settle the payment even
                # when care history leaves the intermediate rate open.
                if ordinary[1] != exempt[1]:
                    raise _computed(
                        FamilyConfigurationUnsupported,
                        UnsupportedReason.DIVORCED_SPOUSE_CARE_HISTORY,
                        "without current care, unknown or protected first-"
                        "entitlement care history can change the auxiliary "
                        "payable; "
                        "continued exemption/conversion after care ends is "
                        "not implemented (RS 00615.201A.2/.010)",
                        beneficiary_id=beneficiary.beneficiary_id,
                    )
                if ordinary[0] != exempt[0]:
                    row.note += ("; " if row.note else "") + (
                        "care history does not affect auxiliary payable; "
                        "age_adjusted_rate displays the ordinary diagnostic "
                        f"rate {ordinary[0]}; the care-exempt rate is "
                        f"{exempt[0]}"
                    )
        if not row.entitled or beneficiary.role not in _WIDOW_ROLES:
            continue
        if entitled_children and beneficiary.child_in_care is None:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.WIDOW_CHILD_IN_CARE_UNKNOWN,
                "a widow(er) with an entitled child must attest child-in-care "
                "status for the month (RS 00615.340/.010)",
                beneficiary_id=beneficiary.beneficiary_id,
            )
        if isinstance(beneficiary.child_in_care, str):
            row.mother_father_rate = _mother_father_care_rate(
                state, beneficiaries, beneficiary, payment_month, params
            )

    dual = [row for row in subject if row.dual]
    nondual = [row for row in subject if not row.dual]
    redistributed = bool(binding and dual and nondual)
    if redistributed:
        if (
            payment_month.year,
            payment_month.month,
        ) < PARISI_FIRST_PAYMENT_MONTH:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.PARISI_BEFORE_OCTOBER_1999,
                "a binding maximum with dual entitlement before 10/99 used "
                "the pre-Parisi rule (POMS RS 00615.768D), not implemented",
            )
        deductee_payables = {}
        age_reductions = {}
        for row in dual:
            payable, age_reduction = _parisi_counted(row, state, params)
            bid = row.beneficiary.beneficiary_id
            deductee_payables[bid] = payable
            age_reductions[bid] = age_reduction
            row.counted = payable + age_reduction
        shares = _maximum_redistribution_rates_validated(
            {row.beneficiary.beneficiary_id: row.ob for row in subject},
            available,
            deductee_payables=deductee_payables,
            age_reductions=age_reductions,
        )
        for row in nondual:
            row.rate = row.counted = shares[row.beneficiary.beneficiary_id]

    results = []
    for row in rows:
        beneficiary = row.beneficiary
        if row.entitled:
            age_adjusted, payable = _reduce_and_offset(row, state, params)
        else:
            age_adjusted = payable = Fraction(0)
        results.append(
            _computed(
                BeneficiaryBenefit,
                beneficiary_id=beneficiary.beneficiary_id,
                role=beneficiary.role,
                entitled=row.entitled,
                subject_to_family_maximum=row.subject,
                original_benefit=row.ob,
                standard_rate=row.standard,
                family_maximum_rate=row.rate,
                counted_against_maximum=(
                    row.counted if row.subject else Fraction(0)
                ),
                age_adjusted_rate=age_adjusted,
                auxiliary_payable=payable,
                own_benefit=row.own_mba,
                whole_dollar_auxiliary=_whole_dollars_validated(payable),
                whole_dollar_own=(
                    None
                    if row.own_mba is None
                    else _whole_dollars_validated(row.own_mba)
                ),
                note=row.note,
                age_reduction_factor=_beneficiary_age_factor(
                    beneficiary, params
                ),
            )
        )

    subject_total = (state.pia if life_case else Fraction(0)) + sum(
        (row.counted for row in subject), Fraction(0)
    )
    if subject_total > state.family_maximum:
        raise AssertionError(
            "family-maximum invariant violated: "
            f"{subject_total} > {state.family_maximum}"
        )
    record_total = (worker_benefit or Fraction(0)) + sum(
        (row.auxiliary_payable for row in results), Fraction(0)
    )
    record_whole = (
        0
        if worker_benefit is None
        else _whole_dollars_validated(worker_benefit)
    ) + sum(row.whole_dollar_auxiliary for row in results)
    return _computed(
        FamilyBenefits,
        kind=state.kind,
        payment_month=payment_month,
        pia=state.pia,
        family_maximum=state.family_maximum,
        available_for_auxiliaries=available,
        total_original_benefits=total_ob,
        family_maximum_binding=binding,
        redistribution_applied=redistributed,
        worker_benefit=worker_benefit,
        whole_dollar_worker=(
            None
            if worker_benefit is None
            else _whole_dollars_validated(worker_benefit)
        ),
        beneficiaries=tuple(results),
        record_total=record_total,
        record_total_whole_dollars=record_whole,
        subject_total=subject_total,
        state_source=state.source,
        pe_us_revision=rates.pe_us_revision,
        worker_reduced_for_age=bool(
            worker_benefit is not None
            and state.worker is not None
            and state.worker.reduction_months
        ),
        worker_age_reduction_factor=(
            1
            - _worker_reduction_fraction_validated(
                state.worker.reduction_months, params
            )
            if worker_benefit is not None and state.worker is not None
            else Fraction(1)
        ),
    )


# GN 02603.040 event refusals deliberately retain distinct reason codes.
_DEDUCTION_REFUSALS = {
    DeductionReason.WORKERS_COMPENSATION: UnsupportedReason.WORKERS_COMPENSATION_OFFSET,
    DeductionReason.PRISONER_SUSPENSION: UnsupportedReason.PRISONER_SUSPENSION,
    DeductionReason.DRUG_ADDICTION_SUSPENSION: UnsupportedReason.DRUG_ADDICTION_SUSPENSION,
    DeductionReason.FOREIGN_WORK: UnsupportedReason.FOREIGN_WORK_DEDUCTION,
    DeductionReason.PENALTY: UnsupportedReason.PENALTY_DEDUCTION,
    DeductionReason.MARITIME: UnsupportedReason.MARITIME_DEDUCTION,
    DeductionReason.ELECTION_CERTIFICATE_SUSPENSION: UnsupportedReason.ELECTION_CERTIFICATE_SUSPENSION,
}


def _check_deduction_inputs(
    beneficiaries, deductions, households, worker_deductions
):
    members = {b.beneficiary_id: b for b in beneficiaries}
    for label, mapping in (
        ("deductions", deductions),
        ("households", households),
        ("worker_deductions", worker_deductions),
    ):
        if set(mapping) - set(members):
            raise InvalidFamilyInput(f"{label} names an unknown beneficiary")
    for key, value in households.items():
        _input_text(key, "household beneficiary ID")
        _input_text(value, "household ID")
    if any(not event.permanent for event in deductions.values()) and set(
        households
    ) != set(members):
        raise InvalidFamilyInput(
            "Temporary deductions require every beneficiary's household"
        )
    for key, event in deductions.items():
        member = members[key]
        if (
            event.reason is DeductionReason.DUAL_ENTITLEMENT
            and member.own_benefit is None
        ):
            raise InvalidFamilyInput(
                "A dual-entitlement marker needs an own benefit"
            )
        if event.reason is DeductionReason.NO_CHILD_IN_CARE:
            if member.role not in (
                Role.SPOUSE,
                Role.SPOUSE_CHILD_IN_CARE,
                Role.DIVORCED_SPOUSE,
                Role.MOTHER_FATHER,
            ):
                raise InvalidFamilyInput(
                    "No-child-in-care deduction needs a spouse or mother/father"
                )
            if isinstance(member.child_in_care, str):
                raise InvalidFamilyInput(
                    "No-child-in-care deduction conflicts with current care"
                )
    for value in worker_deductions.values():
        if value < 0:
            raise InvalidFamilyInput("Worker deductions must be nonnegative")


def _check_deduction_amount_bounds(
    state, beneficiaries, deductions, worker_deductions
):
    """Reject impossible amounts before any statutory coverage refusal.

    The original benefit is an unconditional upper bound on a post-work
    payable. For a parent, the one-parent OB is the conservative upper
    bound until a supported computation resolves entitlement/count.
    """
    for member in beneficiaries:
        bid = member.beneficiary_id
        original = _original_benefit_validated(
            member.role, state.kind, state.pia, member.original_benefit_basis
        )
        nh = worker_deductions.get(bid, Fraction(0))
        if nh > original:
            raise InvalidFamilyInput(
                "NH deduction exceeds the original benefit"
            )
        event = deductions.get(bid)
        if event is not None and event.payable + nh > original:
            raise InvalidFamilyInput(
                "Deductee payable and NH reservation exceed the original benefit"
            )


@_validated_entry
def family_benefits_after_deductions(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    *,
    payment_month: YearMonth,
    params: SSAParameters,
    deductions: Mapping[str, BenefitDeduction],
    households: Mapping[str, str],
    standalone: bool,
    worker_deductions: Mapping[str, Fraction] | None = None,
) -> FamilyBenefits:
    """203(a)(4), GN 02603.050C-D: deduct, then redistribute the maximum.

    Mappings preserve associations; beneficiaries is an ordered tuple/list.
    Households are monthly membership IDs, required for all beneficiaries
    whenever an own-work event is estimated. Empty deductions returns G's
    ordinary result. ``worker_deductions`` reserves NH work deductions;
    these never release room (GN 02603.040B; RS 02501.155B.3.c).
    R2 owns earnings, charge order, grace years and permanent determinations.
    """
    if standalone is not True:
        raise InvalidFamilyInput(
            "Use household_benefits_after_deductions unless standalone=True"
        )
    beneficiaries = _check_family_inputs(
        state, beneficiaries, payment_month, params
    )
    worker_deductions = {} if worker_deductions is None else worker_deductions
    _check_deduction_inputs(
        beneficiaries, deductions, households, worker_deductions
    )
    _check_deduction_amount_bounds(
        state, beneficiaries, deductions, worker_deductions
    )
    return _after_deductions(
        state,
        beneficiaries,
        payment_month,
        params,
        deductions,
        households,
        worker_deductions,
    )


def _after_deductions(
    state,
    beneficiaries,
    payment_month,
    params,
    deductions,
    households,
    worker_deductions,
):
    baseline = _family_benefits(state, beneficiaries, payment_month, params)
    by_id = {row.beneficiary_id: row for row in baseline.beneficiaries}
    for bid, amount in worker_deductions.items():
        if amount > by_id[bid].auxiliary_payable:
            raise InvalidFamilyInput(
                "NH deduction exceeds the beneficiary's gross rate"
            )
    for bid, event in deductions.items():
        gross = by_id[bid].auxiliary_payable - worker_deductions.get(bid, 0)
        if not by_id[bid].entitled:
            raise InvalidFamilyInput(
                "A deduction needs an entitled beneficiary"
            )
        if event.payable > gross:
            raise InvalidFamilyInput(
                "Deductee payable exceeds the pre-deduction rate"
            )
        if (
            event.reason is DeductionReason.DUAL_ENTITLEMENT
            and event.payable != gross
        ):
            raise InvalidFamilyInput(
                "Dual-entitlement marker disagrees with the computed payable"
            )
    for bid in sorted(deductions):
        reason = _DEDUCTION_REFUSALS.get(deductions[bid].reason)
        if reason is not None:
            raise _computed(
                FamilyConfigurationUnsupported,
                reason,
                "This GN 02603.040 event is outside the implemented deduction scope",
                beneficiary_id=bid,
            )
    events = {
        bid: event
        for bid, event in deductions.items()
        if event.reason is not DeductionReason.DUAL_ENTITLEMENT
    }
    if not events:
        return baseline
    # Source conflict us:oasdi-nh-charge-age-reduction-interaction
    if any(worker_deductions.values()) and any(
        row.age_reduction_factor != 1 for row in baseline.beneficiaries
    ):
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.DEDUCTION_AGE_WORK_INTERACTION,
            "Concurrent NH reservations and age reductions need a pinned allocation reading",
        )
    subject = [
        row for row in baseline.beneficiaries if row.subject_to_family_maximum
    ]
    explicit = {
        row.beneficiary_id for row in subject if row.beneficiary_id in events
    }
    # The existing Parisi result fixes which dual beneficiaries are deductees.
    # In particular .050A.2 disregards a zero dual rate regardless of other events.
    dual = {
        row.beneficiary_id for row in subject if row.own_benefit is not None
    }
    permanent = dual | {bid for bid in explicit if events[bid].permanent}
    members = {b.beneficiary_id: b for b in beneficiaries}
    reserve = sum(
        (
            worker_deductions.get(row.beneficiary_id, Fraction(0))
            for row in subject
        ),
        Fraction(0),
    )
    # GN 02603.050A.1 expressly overrides the C formula for one full,
    # permanent deduction and no other deduction event: disregard the row.
    disregard_full = {
        bid
        for bid in explicit
        if len(events) == 1
        and not dual
        and not reserve
        and events[bid].permanent
        and events[bid].payable == 0
    }
    results = []
    for old in baseline.beneficiaries:
        bid = old.beneficiary_id
        values = {item.name: getattr(old, item.name) for item in fields(old)}
        if bid in events:
            event = events[bid]
            deduction = old.auxiliary_payable - event.payable
            values.update(
                auxiliary_payable=event.payable,
                whole_dollar_auxiliary=_whole_dollars_validated(event.payable),
                deduction=deduction,
                deduction_reason=event.reason,
            )
            if old.subject_to_family_maximum:
                age_reserve = max(
                    Fraction(0),
                    old.counted_against_maximum - old.auxiliary_payable,
                )
                if bid in disregard_full:
                    age_reserve = Fraction(0)
                values["counted_against_maximum"] = (
                    age_reserve + event.payable + worker_deductions.get(bid, 0)
                )
        elif (
            old.subject_to_family_maximum
            and bid not in dual
            and baseline.family_maximum_binding
            and explicit
        ):
            eligible = permanent | {
                other
                for other in explicit
                if households.get(other) == households.get(bid)
            }
            remaining_ob = sum(
                (
                    row.original_benefit
                    for row in subject
                    if row.beneficiary_id not in eligible
                ),
                Fraction(0),
            )
            reserved = Fraction(0)
            for other in subject:
                oid = other.beneficiary_id
                if oid not in eligible:
                    continue
                if oid in disregard_full:
                    continue
                if oid in events:
                    reserved += events[oid].payable + max(
                        Fraction(0),
                        other.counted_against_maximum
                        - other.auxiliary_payable,
                    )
                else:
                    # A fixed Parisi rate still bears its NH deduction.
                    # The NH amount is already in the global reserve.
                    reserved += (
                        other.counted_against_maximum
                        - worker_deductions.get(oid, Fraction(0))
                    )
            pool = baseline.available_for_auxiliaries
            if reserve:
                # RS 02501.155B.3.c caps readjustment at the auxiliary's
                # actual charge: NH partial months cannot release old slack.
                pool = sum(
                    (other.counted_against_maximum for other in subject),
                    Fraction(0),
                )
            available = max(Fraction(0), pool - reserve - reserved)
            rate = (
                _floor_dime_validated(
                    min(
                        old.original_benefit - worker_deductions.get(bid, 0),
                        old.original_benefit * available / remaining_ob,
                    )
                )
                if remaining_ob
                else old.family_maximum_rate
            )
            member = members[bid]
            row = _Row(
                member,
                old.entitled,
                old.subject_to_family_maximum,
                old.original_benefit,
                None,
                None,
                standard=old.standard_rate,
                rate=rate,
                counted=rate,
                dwb_under_60=_dwb_under_60(member, payment_month),
            )
            if (
                isinstance(member.child_in_care, str)
                and member.role in _WIDOW_ROLES
            ):
                row.mother_father_rate = _mother_father_care_rate(
                    state, beneficiaries, member, payment_month, params
                )
            age_adjusted, payable = _reduce_and_offset(row, state, params)
            values.update(
                family_maximum_rate=rate,
                counted_against_maximum=rate + worker_deductions.get(bid, 0),
                reserved_work_deduction=worker_deductions.get(
                    bid, Fraction(0)
                ),
                age_adjusted_rate=age_adjusted,
                auxiliary_payable=payable,
                whole_dollar_auxiliary=_whole_dollars_validated(payable),
            )
        elif worker_deductions.get(bid, Fraction(0)):
            # Fixed dual rates and outside-maximum rates do not receive
            # redistribution, but NH work still reduces their cash. Keep
            # dime gross rates and counted maximum room unchanged; the
            # separate exact deduction supports fractional NH proration.
            nh_deduction = worker_deductions[bid]
            payable = old.auxiliary_payable - nh_deduction
            values.update(
                auxiliary_payable=payable,
                whole_dollar_auxiliary=_whole_dollars_validated(payable),
                deduction=nh_deduction,
                reserved_work_deduction=nh_deduction,
            )
        results.append(_computed(BeneficiaryBenefit, **values))
    family = {
        item.name: getattr(baseline, item.name) for item in fields(baseline)
    }
    family.update(
        beneficiaries=tuple(results),
        redistribution_applied=bool(
            baseline.redistribution_applied
            or baseline.family_maximum_binding
            and explicit
        ),
        record_total=(baseline.worker_benefit or Fraction(0))
        + sum((row.auxiliary_payable for row in results), Fraction(0)),
        record_total_whole_dollars=(baseline.whole_dollar_worker or 0)
        + sum(row.whole_dollar_auxiliary for row in results),
        subject_total=(
            baseline.pia
            if baseline.worker_benefit is not None
            else Fraction(0)
        )
        + sum(
            (
                row.counted_against_maximum
                for row in results
                if row.subject_to_family_maximum
            ),
            Fraction(0),
        ),
    )
    return _computed(FamilyBenefits, **family)


# ---------------------------------------------------------------------------
# Households: every record a family draws on, computed together
# ---------------------------------------------------------------------------
@_declared_input
@dataclass(frozen=True)
class HouseholdRecord:
    """One insured worker's record within a household.

    ``worker_id`` is the insured worker (the deceased, on a survivor
    record). Each beneficiary's ``beneficiary_id`` must be that person's
    household-wide identifier, which is how :func:`check_household_records`
    recognizes a person entitled on more than one record, or a worker who
    is also an auxiliary on someone else's record.
    """

    worker_id: str
    state: RecordState
    beneficiaries: tuple[Beneficiary, ...] = ()

    def __post_init__(self):
        _validate_input_fields(self)
        object.__setattr__(self, "beneficiaries", tuple(self.beneficiaries))
        for beneficiary in self.beneficiaries:
            if beneficiary.beneficiary_id == self.worker_id:
                raise InvalidFamilyInput(
                    f"{self.worker_id} cannot be a beneficiary on their own "
                    "record"
                )


@_sealed_result
@dataclass(frozen=True)
class HouseholdBenefits(_SealedResult):
    """Gross monthly benefits on every record in a household for a month.

    Totals count what is paid on the household's records: each living
    worker's own benefit once (on their own record) and every auxiliary
    payment. A dually entitled person's own benefit from a record outside
    the household is reported on their row but not counted here.
    """

    payment_month: YearMonth
    records: Mapping[str, FamilyBenefits]

    def __post_init__(self):
        month = _checked_input(self.payment_month, YearMonth, "payment_month")
        if not isinstance(self.records, Mapping):
            raise _InvalidInputType("records must be a mapping")
        records = {}
        for key, result in self.records.items():
            _input_text(key, "record key")
            result = _checked_input(result, FamilyBenefits, "record result")
            if result.payment_month != month:
                raise InvalidFamilyInput(
                    "Every record must have the household payment_month"
                )
            records[key] = result
        object.__setattr__(self, "payment_month", month)
        object.__setattr__(self, "records", MappingProxyType(records))

    @property
    def record_total(self) -> Fraction:
        _check_seal(self)
        return sum(
            (result.record_total for result in self.records.values()),
            Fraction(0),
        )

    @property
    def record_total_whole_dollars(self) -> int:
        _check_seal(self)
        return sum(
            result.record_total_whole_dollars
            for result in self.records.values()
        )


def _own_benefit_on_record(state: RecordState) -> OwnBenefit | None:
    """The living worker's own RIB or DIB on their record."""
    if RecordCondition.WORKER_NOT_ENTITLED in state.conditions:
        return None
    if state.kind is FamilyKind.RETIREMENT:
        return state.worker
    if state.kind is FamilyKind.DISABILITY:
        return _construct_declared(
            OwnBenefit,
            OwnBenefitKind.DISABILITY,
            state.pia,
            birth_year=state.worker_birth_year,
        )
    return None


def _same_own_benefit(declared: OwnBenefit | None, actual: OwnBenefit) -> bool:
    if declared is None:
        return False
    names = ("kind", "pia", "reduction_months", "delayed_credit_months")
    if any(getattr(declared, n) != getattr(actual, n) for n in names):
        return False
    return (
        declared.birth_year is None
        or actual.birth_year is None
        or declared.birth_year == actual.birth_year
    )


@_validated_entry
def check_household_records(records: Mapping[str, HouseholdRecord]) -> None:
    """Refuse a household that one-record computations would misstate.

    * A person entitled as an auxiliary or survivor on two or more records
      raises :class:`FamilyConfigurationUnsupported`: a child on several
      records with ``combined_family_maximum`` (403(a)(3)(A); POMS RS
      00615.770), anyone else with ``multiple_auxiliary_records``
      (simultaneous or dual entitlement across records, RS 00615.768A).
    * A living worker who is also an auxiliary on another record must
      declare that record's RIB or DIB as ``own_benefit`` (402(k)(3)(A)).
      A mismatch, a worker with two records, or a deceased worker entered
      as someone's beneficiary raises :class:`InvalidFamilyInput`.
    * All supplied birth years for a person, including their worker
      record, must agree (RS 00615.003/.010). A known cohort is carried
      into immutable copies for subsequent family validation/computation.

    Input errors are raised before either refusal, so a coverage refusal
    never masks one.
    """
    _, held = _check_household_inputs(records)
    _refuse_household(held)


def _check_household_inputs(
    records: Mapping[str, HouseholdRecord],
) -> tuple[
    dict[str, HouseholdRecord], dict[str, list[tuple[str, Beneficiary]]]
]:
    """Check household inputs; return cohort-resolved records/entitlements.

    One person's FRA governs every record (402(q)(6); RS 00615.003/.010).
    Resolve all supplied years before any family check or coverage refusal,
    without changing caller inputs or depending on record order.
    """
    if not isinstance(records, Mapping) or not records:
        raise InvalidFamilyInput("A household needs at least one record")
    for record_id in records:
        _input_text(record_id, "record_id")
    records = {
        record_id: _checked_input(record, HouseholdRecord, "record")
        for record_id, record in records.items()
    }
    workers: dict[str, str] = {}
    for record_id, record in records.items():
        if record.worker_id in workers:
            raise InvalidFamilyInput(
                f"worker {record.worker_id} has two records "
                f"({workers[record.worker_id]}, {record_id})"
            )
        workers[record.worker_id] = record_id
    cohorts: dict[str, int] = {}

    def remember_cohort(person: str, year: int | None) -> None:
        if year is None:
            return
        if person in cohorts and cohorts[person] != year:
            raise InvalidFamilyInput(
                f"{person}'s birth_year differs across household records"
            )
        cohorts[person] = year

    for record in records.values():
        remember_cohort(record.worker_id, record.state.worker_birth_year)
        if record.state.worker is not None:
            remember_cohort(record.worker_id, record.state.worker.birth_year)
        for beneficiary in record.beneficiaries:
            remember_cohort(beneficiary.beneficiary_id, beneficiary.birth_year)
            if beneficiary.own_benefit is not None:
                remember_cohort(
                    beneficiary.beneficiary_id,
                    beneficiary.own_benefit.birth_year,
                )
    resolved = {}
    for record_id, record in records.items():
        state = record.state
        year = cohorts.get(record.worker_id)
        if year is not None:
            state = _replace_declared(state, worker_birth_year=year)
        beneficiaries = tuple(
            _with_effective_cohort(
                _replace_declared(b, birth_year=cohorts.get(b.beneficiary_id))
            )
            for b in record.beneficiaries
        )
        resolved[record_id] = _replace_declared(
            record, state=state, beneficiaries=beneficiaries
        )
    records = resolved
    held: dict[str, list[tuple[str, Beneficiary]]] = {}
    for record_id, record in records.items():
        for beneficiary in record.beneficiaries:
            held.setdefault(beneficiary.beneficiary_id, []).append(
                (record_id, beneficiary)
            )
    for person, entitlements in sorted(held.items()):
        own_record_id = workers.get(person)
        if own_record_id is None:
            continue
        actual = _own_benefit_on_record(records[own_record_id].state)
        for record_id, beneficiary in entitlements:
            if actual is None:
                if records[own_record_id].state.kind is FamilyKind.SURVIVOR:
                    raise InvalidFamilyInput(
                        f"{person} is the deceased worker on record "
                        f"{own_record_id} and a beneficiary on record {record_id}"
                    )
                if beneficiary.own_benefit is not None:
                    raise InvalidFamilyInput(
                        f"{person} is not entitled on record {own_record_id}; "
                        "their declared own_benefit must be absent"
                    )
                continue
            if not _same_own_benefit(beneficiary.own_benefit, actual):
                raise InvalidFamilyInput(
                    f"{person} is the worker on record {own_record_id}; on "
                    f"record {record_id} their own_benefit must be that "
                    "record's benefit (402(k)(3)(A))"
                )
    return resolved, held


def _refuse_household(
    held: Mapping[str, list[tuple[str, Beneficiary]]],
) -> None:
    """Refuse anyone entitled as an auxiliary on two or more records."""
    for person, entitlements in sorted(held.items()):
        if len(entitlements) < 2:
            continue
        ids = sorted(record_id for record_id, _ in entitlements)
        if all(b.role is Role.CHILD for _, b in entitlements):
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.COMBINED_FAMILY_MAXIMUM,
                f"a child entitled on records {ids}; 403(a)(3)(A) may "
                "combine their maximums (POMS RS 00615.770)",
                beneficiary_id=person,
            )
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.MULTIPLE_AUXILIARY_RECORDS,
            f"entitled as an auxiliary or survivor on records {ids} "
            "(simultaneous or dual entitlement across records, POMS RS "
            "00615.768A) is not implemented",
            beneficiary_id=person,
        )


@_validated_entry
def household_benefits(
    records: Mapping[str, HouseholdRecord],
    *,
    payment_month: YearMonth,
    params: SSAParameters,
) -> HouseholdBenefits:
    """Every record in a household for one month, checked together.

    This is G's integration entry point. Every input error, in the
    household, the statutory rate bundle and each record's family, is
    raised first. A person's cohort is shared across their worker and
    beneficiary records before family validation. Then come the
    household refusals of :func:`check_household_records`; then each
    record is computed as :func:`family_benefits` would, in sorted record
    order, matching :func:`household_month_outcome` when several refuse.
    """
    records, held = _check_household_inputs(records)
    for record in records.values():
        _check_family_inputs(
            record.state, record.beneficiaries, payment_month, params
        )
    _refuse_household(held)
    results = {
        record_id: _family_benefits(
            records[record_id].state,
            records[record_id].beneficiaries,
            payment_month,
            params,
        )
        for record_id in sorted(records)
    }
    return _computed(
        HouseholdBenefits, payment_month, MappingProxyType(results)
    )


@_validated_entry
def household_benefits_after_deductions(
    records: Mapping[str, HouseholdRecord],
    *,
    payment_month: YearMonth,
    params: SSAParameters,
    deductions: Mapping[str, BenefitDeduction],
    households: Mapping[str, str],
    worker_deductions: Mapping[str, Fraction] | None = None,
) -> HouseholdBenefits:
    """All records checked together; combined and multiple records refuse.

    Deduction and household dictionaries are keyed by person ID. All family
    and deduction input checks precede household or statutory refusals.
    """
    records, held = _check_household_inputs(records)
    worker_deductions = {} if worker_deductions is None else worker_deductions
    all_members = tuple(
        b for record in records.values() for b in record.beneficiaries
    )
    _check_deduction_inputs(
        all_members, deductions, households, worker_deductions
    )
    for record in records.values():
        _check_family_inputs(
            record.state, record.beneficiaries, payment_month, params
        )
        _check_deduction_amount_bounds(
            record.state, record.beneficiaries, deductions, worker_deductions
        )
    _refuse_household(held)
    results = {}
    for rid in sorted(records):
        record = records[rid]
        ids = {b.beneficiary_id for b in record.beneficiaries}
        results[rid] = _after_deductions(
            record.state,
            record.beneficiaries,
            payment_month,
            params,
            {bid: value for bid, value in deductions.items() if bid in ids},
            {bid: value for bid, value in households.items() if bid in ids},
            {
                bid: value
                for bid, value in worker_deductions.items()
                if bid in ids
            },
        )
    return _computed(
        HouseholdBenefits, payment_month, MappingProxyType(results)
    )


@_validated_entry
def household_month_outcome(
    records: Mapping[str, HouseholdRecord],
    *,
    payment_month: YearMonth,
    params: SSAParameters,
    guards: Mapping[str, SavingsClauseGuard],
    key: str = "household",
    weight: object = 1,
) -> FamilyOutcome:
    """Evaluate one household month with one 403(a)(5) guard per record.

    Resolve each person's cohort across all records and validate the whole
    household before any guard advances. Every record's
    guard advances even if another record refuses; a refusal carries its
    record id. The household outcome stays in the coverage denominator.
    """
    _input_text(key, "key")
    _outcome_weight(weight)
    _checked_input(payment_month, YearMonth, "payment_month")
    records, held = _check_household_inputs(records)
    if not isinstance(guards, Mapping):
        raise _InvalidInputType("guards must be a mapping")
    for record_id, guard in guards.items():
        _input_text(record_id, "guard record_id")
        _input_type(guard, SavingsClauseGuard, "guard")
    if set(guards) != set(records):
        raise InvalidFamilyInput("guards must match the household record ids")
    if len({id(guard) for guard in guards.values()}) != len(guards):
        raise InvalidFamilyInput("Each record needs its own guard")
    for record_id, record in records.items():
        _check_family_inputs(
            record.state, record.beneficiaries, payment_month, params
        )
        if not isinstance(guards[record_id], SavingsClauseGuard):
            raise _InvalidInputType("guards must be SavingsClauseGuards")
        guards[record_id]._expect(payment_month)
    try:
        _refuse_household(held)
    except FamilyConfigurationUnsupported as error:
        for record_id, record in records.items():
            guards[record_id]._skip_validated(
                payment_month, pia=record.state.pia
            )
        return _computed(FamilyOutcome, key, weight, None, error)
    results = {}
    refusal = None
    for record_id in sorted(records):
        record = records[record_id]
        outcome = guards[record_id]._evaluate_validated(
            record_id,
            weight,
            lambda record=record: _family_benefits(
                record.state, record.beneficiaries, payment_month, params
            ),
            pia=record.state.pia,
        )
        if outcome.unsupported is not None and refusal is None:
            error = outcome.unsupported
            refusal = _computed(
                FamilyConfigurationUnsupported,
                error.reason,
                error.detail,
                beneficiary_id=error.beneficiary_id,
                record_id=record_id,
            )
        elif outcome.supported:
            results[record_id] = outcome.benefits
    if refusal is not None:
        return _computed(FamilyOutcome, key, weight, None, refusal)
    return _computed(
        FamilyOutcome,
        key,
        weight,
        _computed(HouseholdBenefits, payment_month, MappingProxyType(results)),
        None,
    )


# ---------------------------------------------------------------------------
# 403(a)(5): operational payments or the explicit literal refusal reading
# ---------------------------------------------------------------------------
@_validated_entry
def savings_clause_total(result: FamilyBenefits) -> Fraction:
    """The total 403(a)(5) protects: after 403(a) and 402(q).

    The worker's own benefit plus each beneficiary subject to the maximum
    after age reduction and before the 402(k)(3)(A) offset. Divorced
    beneficiaries are outside 403(a) (403(a)(3)(C)).
    """
    result = _checked_input(result, FamilyBenefits, "result")
    return (result.worker_benefit or Fraction(0)) + sum(
        (
            row.age_adjusted_rate
            for row in result.beneficiaries
            if row.subject_to_family_maximum
        ),
        Fraction(0),
    )


def _next_month(month: YearMonth) -> YearMonth:
    if month.month == 12:
        return _construct_declared(YearMonth, month.year + 1, 1)
    return _construct_declared(YearMonth, month.year, month.month + 1)


def _previous_month(month: YearMonth) -> YearMonth:
    if month.month == 1:
        return _construct_declared(YearMonth, month.year - 1, 12)
    return _construct_declared(YearMonth, month.year, month.month - 1)


def _money_text(amount: Fraction) -> str:
    value = Decimal(amount.numerator) / Decimal(amount.denominator)
    return f"${value:,.2f}"


def _qualifies(result: FamilyBenefits) -> bool:
    """403(a)(5)(A) for one month: two or more persons are entitled on
    the record and the maximum reduces their benefits ("the provisions of
    this subsection are applicable"; RS 00630.400: "reduced for the
    MAX"). Divorced beneficiaries count as entitled persons."""
    persons = sum(row.entitled for row in result.beneficiaries) + (
        result.worker_benefit is not None
    )
    return result.family_maximum_binding and persons >= 2


def _governed(result: FamilyBenefits) -> bool:
    """Whether any benefit that month is one the maximum can change.

    403(a)(4) decreases only benefits "other than the old-age or
    disability insurance benefit", and divorced beneficiaries are outside
    the maximum (403(a)(3)(C)). With nobody subject to it, a larger
    permitted total has nothing to raise.
    """
    return any(row.subject_to_family_maximum for row in result.beneficiaries)


@dataclass(frozen=True)
class _PriorMonth:
    month: YearMonth
    result: FamilyBenefits | None  # None: G did not compute the month
    pia: Fraction | None  # None: unknown


class SavingsClauseReading(Enum):
    """Canonical 203(a)(5) interpretations; d1338 selects SSA's procedure."""

    SSA_OPERATIONAL = "ssa_operational"
    LITERAL_REFUSAL = "literal_refusal"


def _savings_membership(result: FamilyBenefits) -> tuple:
    """Membership is unordered; a change of record kind changes it too."""
    return (
        result.kind,
        result.worker_benefit is not None,
        frozenset(
            (row.beneficiary_id, row.role)
            for row in result.beneficiaries
            if row.entitled
        ),
    )


def _operational_age_reduced(result: FamilyBenefits) -> bool:
    return result.worker_reduced_for_age or any(
        row.entitled and row.age_reduction_factor < 1
        for row in result.beneficiaries
    )


def _savings_age_basis(result: FamilyBenefits) -> tuple:
    """Do not attribute a simultaneous change of age factors to the PIA."""
    return (
        result.worker_age_reduction_factor,
        frozenset(
            (row.beneficiary_id, row.age_reduction_factor)
            for row in result.beneficiaries
            if row.entitled
        ),
    )


def _savings_has_deductions(result: FamilyBenefits) -> bool:
    """Deduction metadata changes the meaning of pre-offset age rates."""
    return any(
        row.subject_to_family_maximum
        and (
            row.deduction_reason is not None
            or row.deduction
            or row.reserved_work_deduction
        )
        for row in result.beneficiaries
    )


def _savings_payment(
    result: FamilyBenefits, protected: Fraction
) -> FamilyBenefits:
    """RS 00630.400's two life-case procedures, retaining formula FMAX.

    The page says only 'rounded'. Equal auxiliary rates round upward to
    the smallest dime that preserves 203(a)(5)'s protected family total;
    a spouse's age reduction rounds down under RS 00615.201. The explicit
    literal reading remains a refusal. The design records this rounding
    interpretation and the procedures the capture does not settle.
    """
    subject = [
        row for row in result.beneficiaries if row.subject_to_family_maximum
    ]
    reduced = [row for row in subject if row.age_reduction_factor < 1]
    # Source conflict us:oasdi-saving-clause-procedure-gaps
    if (
        result.kind is FamilyKind.SURVIVOR
        or any(row.own_benefit is not None for row in subject)
        or _savings_has_deductions(result)
        or len(reduced) > 1
        or any(row.role is not Role.SPOUSE for row in reduced)
        or (reduced and len(subject) == 1)
    ):
        raise _computed(
            FamilyConfigurationUnsupported,
            UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE,
            "RS 00630.400 supplies the life-case procedure with no reduced "
            "auxiliary or one reduced spouse plus other auxiliaries; "
            "survivors, dual entitlement, deductions, and other reduced "
            "auxiliary configurations need a captured payment procedure",
        )
    # Source conflict us:oasdi-saving-clause-operational-rate-rounding: the
    # least equal dime rates that keep the protected total (Act 203(a)(5)).
    worker = result.worker_benefit or Fraction(0)
    rates = {}
    if reduced:
        spouse = reduced[0]
        increase = _ceil_dime_validated(
            (protected - _savings_clause_total_validated(result))
            / len(subject)
        )
        rates[spouse.beneficiary_id] = (
            spouse.age_adjusted_rate
            + _floor_dime_validated(increase * spouse.age_reduction_factor)
        )
        available = protected - worker - rates[spouse.beneficiary_id]
        share = _ceil_dime_validated(available / (len(subject) - 1))
    else:
        share = _ceil_dime_validated((protected - worker) / len(subject))
    for row in subject:
        if row.beneficiary_id not in rates:
            rates[row.beneficiary_id] = share
    rows = []
    for row in result.beneficiaries:
        if row.beneficiary_id not in rates:
            rows.append(row)
            continue
        rate = rates[row.beneficiary_id]
        if rate > row.original_benefit:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE,
                "the protected rate would exceed the original benefit; "
                "203(a)(4) only decreases benefits and RS 00630.400 does "
                "not settle an above-OB carried payment",
                beneficiary_id=row.beneficiary_id,
            )
        values = {item.name: getattr(row, item.name) for item in fields(row)}
        values.update(
            age_adjusted_rate=rate,
            auxiliary_payable=rate,
            whole_dollar_auxiliary=_whole_dollars_validated(rate),
            note=(row.note + "; " if row.note else "")
            + "203(a)(5) operational protected payment; formula FMAX unchanged",
        )
        rows.append(_computed(BeneficiaryBenefit, **values))
    values = {item.name: getattr(result, item.name) for item in fields(result)}
    values.update(
        beneficiaries=tuple(rows),
        record_total=worker
        + sum((row.auxiliary_payable for row in rows), Fraction(0)),
        record_total_whole_dollars=(result.whole_dollar_worker or 0)
        + sum(row.whole_dollar_auxiliary for row in rows),
    )
    return _computed(FamilyBenefits, **values)


@_checked_public_methods
class SavingsClauseGuard:
    """203(a)(5) for one insured worker's record, carried month to month.

    ``reading`` is an exact canonical SavingsClauseReading enum; its default
    SSA_OPERATIONAL follows d1338 and POMS RS 00630.400. Protection starts
    only after an age-reduced, maximum-reduced month with at least two
    entitled persons, followed by a PIA increase that lowers payment with
    unchanged membership. The two captured life-case procedures compute
    protected auxiliary payments. Formula FMAX and its counted shares stay
    unchanged. RS 00615.801B.2 carries the protected total, including a
    period when the formula payment overtakes it and it later becomes
    payable again. Membership changes during that carried protection refuse
    with SAVINGS_CLAUSE_MEMBERSHIP_CHANGE. Survivor, dual-entitlement,
    deduction and unspecified reduced-auxiliary procedures refuse with
    SAVINGS_CLAUSE_RATE_PROCEDURE when protection would change money.

    LITERAL_REFUSAL retains G v2: every qualifying month followed by a PIA
    increase protects its total, without an age condition or immediate fall.
    Every later governed month below that total, and every governed month
    after the first fall, refuses with SAVINGS_CLAUSE. This includes later
    membership-driven declines that do not trigger SSA_OPERATIONAL.

    Both readings require every calendar month, via admit, skip or evaluate.
    Earlier entitlement or skipped qualifying history that may hide a
    protection retains SAVINGS_CLAUSE_HISTORY_UNKNOWN. Invalid public inputs
    leave the guard unchanged. Prior results and snapshots are detached;
    evaluations establish provenance, not freshness or attribution.
    """

    @_validated_entry
    def __init__(
        self,
        first_month: YearMonth,
        *,
        earlier_months_unknown: bool,
        reading: SavingsClauseReading = SavingsClauseReading.SSA_OPERATIONAL,
    ):
        if type(self) is not SavingsClauseGuard:
            raise InvalidFamilyInput(
                "Undeclared savings-clause guard subclass"
            )
        first_month = _checked_input(first_month, YearMonth, "first_month")
        _input_type(earlier_months_unknown, bool, "earlier_months_unknown")
        _input_type(reading, SavingsClauseReading, "reading")
        self._reading = reading
        self._protected_membership: tuple | None = None
        self._next = first_month
        self._prior: _PriorMonth | None = (
            _PriorMonth(_previous_month(first_month), None, None)
            if earlier_months_unknown
            else None
        )
        self._floor: Fraction | None = None
        self._floor_month: YearMonth | None = None
        self._unknown_since: YearMonth | None = None
        self._refused_since: YearMonth | None = None

    def _check_initialized(self) -> None:
        if type(self) is not SavingsClauseGuard:
            raise InvalidFamilyInput(
                "Expected an initialized savings-clause guard"
            )
        attributes = _checked_instance_dict(self)
        if any(
            name not in attributes
            for name in (
                "_next",
                "_prior",
                "_floor",
                "_floor_month",
                "_unknown_since",
                "_refused_since",
                "_reading",
                "_protected_membership",
            )
        ):
            raise InvalidFamilyInput(
                "Expected an initialized savings-clause guard"
            )

    def __copy__(self):
        raise InvalidFamilyInput("Savings-clause guards cannot be copied")

    def __deepcopy__(self, memo):
        raise InvalidFamilyInput("Savings-clause guards cannot be copied")

    def __getstate__(self):
        raise InvalidFamilyInput("Savings-clause guards cannot be serialized")

    def __reduce__(self):
        raise InvalidFamilyInput("Savings-clause guards cannot be serialized")

    def __reduce_ex__(self, protocol):
        raise InvalidFamilyInput("Savings-clause guards cannot be serialized")

    @property
    @_validated_entry
    def next_month(self) -> YearMonth:
        """The month the guard expects next."""
        return _replace_declared(self._next)

    @property
    @_validated_entry
    def reading(self) -> SavingsClauseReading:
        """The canonical interpretation fixed when this guard was created."""
        return self._reading

    @property
    @_validated_entry
    def protected_total(self) -> Fraction | None:
        """The highest total protected so far (None: nothing protected)."""
        return (
            None
            if self._floor is None
            else _exact_number(self._floor, "total")
        )

    @property
    @_validated_entry
    def protected_since(self) -> YearMonth | None:
        """The qualifying month whose total is :attr:`protected_total`."""
        return (
            None
            if self._floor_month is None
            else _replace_declared(self._floor_month)
        )

    @property
    @_validated_entry
    def refused_since(self) -> YearMonth | None:
        """The first month whose total fell below the protected total."""
        return (
            None
            if self._refused_since is None
            else _replace_declared(self._refused_since)
        )

    @property
    @_validated_entry
    def unknown_since(self) -> YearMonth | None:
        """The month from which a protection G cannot see may exist."""
        return (
            None
            if self._unknown_since is None
            else _replace_declared(self._unknown_since)
        )

    def _expect(self, month: YearMonth) -> None:
        self._check_initialized()
        _checked_input(month, YearMonth, "month")
        _checked_input(self._next, YearMonth, "guard next_month")
        # Check advancement before carrying protection or changing any history.
        # December 9999 has no representable successor in the calendar domain.
        _next_month(month)
        if month != self._next:
            raise InvalidFamilyInput(
                f"the guard expects {_month_text_validated(self._next)}, "
                f"not {_month_text_validated(month)}: give it "
                "every month of the record, in order"
            )

    def _carry(self, pia: Fraction | None) -> None:
        """What the previous month protects, now that this PIA is known."""
        prior = self._prior
        if prior is None:
            return
        rose = pia is None or prior.pia is None or pia > prior.pia
        if not rose:
            return
        if prior.result is None:
            # A month G did not compute may have qualified, with a total
            # G never saw.
            self._unknown_since = self._unknown_since or prior.month
        elif (
            self._reading is SavingsClauseReading.LITERAL_REFUSAL
            and _qualifies(prior.result)
        ):
            total = _savings_clause_total_validated(prior.result)
            if self._floor is None or total > self._floor:
                self._floor, self._floor_month = total, prior.month

    @_validated_entry
    def admit(self, result: FamilyBenefits) -> FamilyBenefits:
        """Carry the protection into ``result``'s month.

        Returns ``result`` when 403(a)(5) cannot change it; otherwise
        raises :class:`FamilyConfigurationUnsupported`. Either way the
        guard moves to the next month.
        """
        original = result
        result = _checked_input(result, FamilyBenefits, "result")
        result = _detached_result(result)
        month = result.payment_month
        self._expect(month)
        total = _savings_clause_total_validated(result)
        self._carry(result.pia)
        prior = self._prior
        self._prior = _PriorMonth(month, result, result.pia)
        self._next = _next_month(month)
        if self._reading is SavingsClauseReading.SSA_OPERATIONAL:
            return self._operational_admit(original, result, prior, total)
        # Source conflict us:oasdi-family-maximum-saving-clause
        below = self._floor is not None and total < self._floor
        first_fall = below and self._refused_since is None
        if first_fall:
            self._refused_since = month
        if not _governed(result):
            return original
        if self._refused_since is not None and not first_fall:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.SAVINGS_CLAUSE,
                "403(a)(5) took effect in "
                f"{_month_text_validated(self._refused_since)} and stays "
                "in effect (POMS RS 00615.801B.2); G does not compute the "
                "raised total",
            )
        if self._unknown_since is not None:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.SAVINGS_CLAUSE_HISTORY_UNKNOWN,
                "a protected total may exist from "
                f"{_month_text_validated(self._unknown_since)} "
                "that G did not see (a month it did not compute, or a path "
                "that does not start at entitlement)",
            )
        if first_fall:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.SAVINGS_CLAUSE,
                f"the total after 403(a) and 402(q) is {_money_text(total)}"
                f", below the {_money_text(self._floor)} protected since "
                f"{_month_text_validated(self._floor_month)}; "
                "403(a)(5) would raise it (not "
                "implemented)",
            )
        return original

    def _operational_admit(
        self,
        original: FamilyBenefits,
        result: FamilyBenefits,
        prior: _PriorMonth | None,
        total: Fraction,
    ) -> FamilyBenefits:
        membership = _savings_membership(result)
        # Source conflict us:oasdi-saving-clause-procedure-gaps
        if (
            self._protected_membership is not None
            and membership != self._protected_membership
        ):
            self._refused_since = self._refused_since or result.payment_month
        if self._refused_since is not None:
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.SAVINGS_CLAUSE_MEMBERSHIP_CHANGE,
                "membership changed while 203(a)(5) protection was active; "
                "RS 00630.400 does not establish the successor protection",
            )
        if self._unknown_since is not None and _governed(result):
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.SAVINGS_CLAUSE_HISTORY_UNKNOWN,
                "a skipped or pre-entitlement month may carry an unknown "
                "203(a)(5) protection",
            )
        if self._floor is not None and (
            _savings_has_deductions(result)
            or (
                prior is not None
                and prior.result is not None
                and _savings_has_deductions(prior.result)
            )
        ):
            self._unknown_since = self._unknown_since or result.payment_month
            raise _computed(
                FamilyConfigurationUnsupported,
                UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE,
                "deductions in the current or prior month interact with "
                "carried protection; pre-offset age rates do not establish "
                "the protected payment under RS 00630.400",
            )
        if (
            prior is not None
            and prior.result is not None
            and _qualifies(prior.result)
            and _operational_age_reduced(prior.result)
            and result.pia > prior.pia
            and membership == _savings_membership(prior.result)
            and total < _savings_clause_total_validated(prior.result)
        ):
            if (
                _savings_age_basis(result) != _savings_age_basis(prior.result)
                or result.family_maximum < prior.result.family_maximum
                or _savings_has_deductions(result)
                or _savings_has_deductions(prior.result)
            ):
                self._unknown_since = (
                    self._unknown_since or result.payment_month
                )
                raise _computed(
                    FamilyConfigurationUnsupported,
                    UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE,
                    "age factors changed, the formula maximum fell, or "
                    "either month has deductions, with a PIA increase and "
                    "lower pre-offset total; the snapshots do not isolate "
                    "the PIA's effect or establish the protected payment",
                )
            protected = _savings_clause_total_validated(prior.result)
            if self._floor is None or protected > self._floor:
                self._floor = protected
                self._floor_month = prior.month
                self._protected_membership = membership
        if self._floor is not None and total < self._floor:
            # The protected total remains recorded when the formula payment
            # overtakes it; .801B.2 permits it to become payable again.
            protected = _savings_payment(result, self._floor)
            self._prior = _PriorMonth(
                result.payment_month, _detached_result(protected), result.pia
            )
            return protected
        return original

    @_validated_entry
    def skip(self, month: YearMonth, *, pia: object = None) -> None:
        """Record a month of this record that G did not compute.

        ``pia`` is the record's PIA for that month, when the caller knows
        it; without it a PIA increase cannot be ruled out.
        """
        month = _checked_input(month, YearMonth, "month")
        self._expect(month)
        amount = None if pia is None else _dimes(pia, "PIA")
        self._carry(amount)
        if self._floor is not None:
            # The skipped month's total may have fallen below the
            # protected total, putting the clause into effect.
            self._unknown_since = self._unknown_since or month
        self._prior = _PriorMonth(month, None, amount)
        self._next = _next_month(month)

    @_validated_entry
    def evaluate(
        self,
        key: str,
        weight: object,
        compute: Callable[[], FamilyBenefits],
        *,
        pia: object = None,
    ) -> FamilyOutcome:
        """:func:`evaluate_family` for the record's next month.

        A configuration ``compute`` refuses is kept with its own reason and
        skipped (``pia`` is that month's PIA, when known); a month 403(a)(5)
        could change is kept with its savings-clause reason. Invalid inputs
        still raise and leave the guard where it was.
        """
        self._check_initialized()
        _check_evaluation_inputs(key, weight, compute)
        weight = _outcome_weight(weight)
        month = self._next
        self._expect(month)
        if pia is not None:
            pia = _dimes(pia, "PIA")
        try:
            result = compute()
        except FamilyConfigurationUnsupported as error:
            error = _validated_refusal(error)
            self._skip_validated(month, pia=pia)
            return _computed(FamilyOutcome, key, weight, None, error)
        result = _checked_input(result, FamilyBenefits, "compute result")
        if pia is not None and _dimes(pia, "PIA") != result.pia:
            raise InvalidFamilyInput(
                f"pia {pia} disagrees with the computed PIA {result.pia}"
            )
        try:
            result = self._admit_validated(result)
        except FamilyConfigurationUnsupported as error:
            return _computed(FamilyOutcome, key, weight, None, error)
        return _computed(FamilyOutcome, key, weight, result, None)


# ---------------------------------------------------------------------------
# Denominators: unsupported rows stay in, and block totals that need them
# ---------------------------------------------------------------------------
def _outcome_weight(weight: object) -> Fraction:
    value = _exact(weight, "weight")
    if value < 0:
        raise InvalidFamilyInput("weight must be nonnegative")
    return value


def _check_evaluation_inputs(
    key: str, weight: object, compute: object
) -> None:
    """Reject outcome metadata before invoking a potentially stateful closure."""
    _input_text(key, "key")
    _outcome_weight(weight)
    if not callable(compute):
        raise _InvalidInputType("compute must be callable")


@_sealed_result
@dataclass(frozen=True)
class FamilyOutcome(_SealedOutcome):
    """One record-month: validated benefits or a validated coverage refusal.

    Nested declarations are revalidated on construction, including a
    refusal's reason, so a malformed result contributes no denominator row.
    """

    key: str
    weight: Fraction
    benefits: FamilyBenefits | HouseholdBenefits | None
    unsupported: FamilyConfigurationUnsupported | None

    def __post_init__(self):
        _input_text(self.key, "key")
        if self.benefits is not None and not _has_declared_type(
            self.benefits, (FamilyBenefits, HouseholdBenefits)
        ):
            raise _InvalidInputType(
                "benefits must be family or household benefits"
            )
        if self.benefits is not None:
            object.__setattr__(
                self,
                "benefits",
                _checked_input(self.benefits, type(self.benefits), "benefits"),
            )
        if self.unsupported is not None:
            object.__setattr__(
                self, "unsupported", _check_refusal(self.unsupported)
            )
        if (self.benefits is None) == (self.unsupported is None):
            raise InvalidFamilyInput(
                "Exactly one of benefits/unsupported is set"
            )
        object.__setattr__(self, "weight", _outcome_weight(self.weight))

    @property
    def supported(self) -> bool:
        _check_seal(self)
        return self.benefits is not None


@_validated_entry
def evaluate_family(
    key: str,
    weight: object,
    compute: Callable[[], FamilyBenefits | HouseholdBenefits],
) -> FamilyOutcome:
    """Run ``compute``; keep an unsupported configuration as an outcome.

    ``compute`` returns one record's :class:`FamilyBenefits` or a whole
    household's :class:`HouseholdBenefits`. Only
    :class:`FamilyConfigurationUnsupported` is caught. Invalid inputs and
    bugs still raise, so an error never masquerades as a coverage gap.
    """
    _check_evaluation_inputs(key, weight, compute)
    try:
        benefits = compute()
    except FamilyConfigurationUnsupported as error:
        return _computed(FamilyOutcome, key, weight, None, error)
    if not _has_declared_type(benefits, (FamilyBenefits, HouseholdBenefits)):
        raise _InvalidInputType(
            "compute must return family or household benefits"
        )
    return _computed(FamilyOutcome, key, weight, benefits, None)


@_sealed_result
@dataclass(frozen=True)
class FamilyDenominator(_SealedResult):
    """Validated counts over every outcome, supported or not.

    Both counts and weights reconcile supported, unsupported and per-reason
    totals. The reason mapping is an immutable snapshot of its input.
    """

    rows: int
    weight: Fraction
    supported_rows: int
    supported_weight: Fraction
    unsupported_rows: int
    unsupported_weight: Fraction
    unsupported_by_reason: Mapping[Enum, tuple[int, Fraction]]

    def __post_init__(self):
        for name in ("rows", "supported_rows", "unsupported_rows"):
            _nonnegative_integer(getattr(self, name), name)
        for name in ("weight", "supported_weight", "unsupported_weight"):
            object.__setattr__(
                self, name, _outcome_weight(getattr(self, name))
            )
        if not isinstance(self.unsupported_by_reason, Mapping):
            raise _InvalidInputType("unsupported_by_reason must be a mapping")
        reasons = {}
        for reason, value in self.unsupported_by_reason.items():
            _check_denominator_reason(reason)
            _input_type(value, tuple, "unsupported count and weight")
            if len(value) != 2:
                raise InvalidFamilyInput("Each reason needs count and weight")
            count, weight = value
            _nonnegative_integer(count, "unsupported reason count")
            reasons[reason] = (count, _outcome_weight(weight))
        if self.rows != self.supported_rows + self.unsupported_rows:
            raise InvalidFamilyInput(
                "rows differ from supported + unsupported"
            )
        if self.weight != self.supported_weight + self.unsupported_weight:
            raise InvalidFamilyInput(
                "weight differs from supported + unsupported"
            )
        if self.unsupported_rows != sum(
            count for count, _ in reasons.values()
        ):
            raise InvalidFamilyInput("unsupported rows differ from reasons")
        if self.unsupported_weight != sum(
            (weight for _, weight in reasons.values()), Fraction(0)
        ):
            raise InvalidFamilyInput("unsupported weight differs from reasons")
        object.__setattr__(
            self, "unsupported_by_reason", MappingProxyType(reasons)
        )

    @property
    def supported_weight_share(self) -> Fraction:
        _check_seal(self)
        if self.weight == 0:
            raise ZeroDivisionError("No weight in the denominator")
        return self.supported_weight / self.weight


@_validated_entry
def count_family_outcomes(
    outcomes: Sequence[_SealedOutcome],
) -> FamilyDenominator:
    """Tabulate every layer's sealed outcomes; never drop refused rows.

    This counter reads coverage metadata only. Monetary aggregators still
    require their own layer's outcome and result classes."""
    outcomes = _checked_outcomes(outcomes, common=True)
    by_reason: dict[Enum, tuple[int, Fraction]] = {}
    for outcome in outcomes:
        if outcome.unsupported is not None:
            count, weight = by_reason.get(
                outcome.unsupported.reason, (0, Fraction(0))
            )
            by_reason[outcome.unsupported.reason] = (
                count + 1,
                weight + outcome.weight,
            )
    supported = [outcome for outcome in outcomes if outcome.supported]
    unsupported = [outcome for outcome in outcomes if not outcome.supported]
    return _computed(
        FamilyDenominator,
        rows=len(outcomes),
        weight=sum((o.weight for o in outcomes), Fraction(0)),
        supported_rows=len(supported),
        supported_weight=sum((o.weight for o in supported), Fraction(0)),
        unsupported_rows=len(unsupported),
        unsupported_weight=sum((o.weight for o in unsupported), Fraction(0)),
        unsupported_by_reason=MappingProxyType(dict(by_reason)),
    )


def _checked_outcomes(
    outcomes: Sequence[_SealedOutcome], *, common: bool = False
) -> tuple:
    """Validate every observation before coverage or denominator decisions."""
    outcomes = tuple(
        (
            _check_outcome(outcome)
            if common
            else _checked_input(outcome, FamilyOutcome, "outcome")
        )
        for outcome in _input_iterable(outcomes, "outcomes")
    )
    keys = Counter(outcome.key for outcome in outcomes)
    duplicates = sorted(key for key, count in keys.items() if count > 1)
    if duplicates:
        raise InvalidFamilyInput(f"Duplicate outcome keys: {duplicates[:5]}")
    return outcomes


def _require_all_supported(outcomes: Sequence[FamilyOutcome]) -> None:
    blocked = [o for o in outcomes if not o.supported]
    if blocked:
        denominator = _count_family_outcomes_validated(outcomes)
        reasons = ", ".join(
            f"{reason.value}={count}"
            for reason, (count, _) in sorted(
                denominator.unsupported_by_reason.items(),
                key=lambda item: item[0].value,
            )
        )
        raise FamilyTargetBlocked(
            f"{len(blocked)} of {len(outcomes)} rows are "
            f"FAMILY_CONFIG_UNSUPPORTED ({reasons}); the total would drop "
            "them from its denominator"
        )


@_validated_entry
def weighted_record_total(outcomes: Sequence[FamilyOutcome]) -> Fraction:
    """Weighted sum of record totals; blocked if any row is unsupported."""
    outcomes = _checked_outcomes(outcomes)
    _require_all_supported(outcomes)
    return sum(
        (o.weight * o.benefits.record_total for o in outcomes), Fraction(0)
    )


@_validated_entry
def weighted_mean_record_total(outcomes: Sequence[FamilyOutcome]) -> Fraction:
    """Weighted mean over *all* rows; blocked if any row is unsupported."""
    outcomes = _checked_outcomes(outcomes)
    denominator = _count_family_outcomes_validated(outcomes)
    _require_all_supported(outcomes)
    if denominator.weight == 0:
        raise ZeroDivisionError("No weight in the denominator")
    return _weighted_record_total_validated(outcomes) / denominator.weight


# Private implementations consume the snapshot owned by their public caller.
_applicable_cola_percents_validated = applicable_cola_percents.__wrapped__
_ceil_dime_validated = ceil_dime.__wrapped__
_check_household_records_validated = check_household_records.__wrapped__
_count_family_outcomes_validated = count_family_outcomes.__wrapped__
_delayed_credit_window_months_validated = (
    delayed_credit_window_months.__wrapped__
)
_disability_family_maximum_validated = disability_family_maximum.__wrapped__
_evaluate_family_validated = evaluate_family.__wrapped__
_family_benefits_validated = family_benefits.__wrapped__
_family_benefits_after_deductions_validated = (
    family_benefits_after_deductions.__wrapped__
)
_household_benefits_after_deductions_validated = (
    household_benefits_after_deductions.__wrapped__
)
_family_maximum_bend_points_validated = family_maximum_bend_points.__wrapped__
_family_maximum_formula_validated = family_maximum_formula.__wrapped__
_floor_dime_validated = floor_dime.__wrapped__
_household_benefits_validated = household_benefits.__wrapped__
_household_month_outcome_validated = household_month_outcome.__wrapped__
_increase_by_colas_validated = increase_by_colas.__wrapped__
_maximum_redistribution_rates_validated = (
    maximum_redistribution_rates.__wrapped__
)
_original_benefit_validated = original_benefit.__wrapped__
_own_monthly_benefit_validated = own_monthly_benefit.__wrapped__
_record_state_validated = record_state.__wrapped__
_retirement_survivor_family_maximum_validated = (
    retirement_survivor_family_maximum.__wrapped__
)
_savings_clause_total_validated = savings_clause_total.__wrapped__
_spouse_age_reduced_validated = spouse_age_reduced.__wrapped__
_spouse_reduction_fraction_validated = spouse_reduction_fraction.__wrapped__


def _statutory_rates_validated(params):
    rates = getattr(params, "_track_b_statutory_rates", None)
    if rates is None:
        rates = statutory_rates.__wrapped__(params)
        object.__setattr__(params, "_track_b_statutory_rates", rates)
    return rates


_survivor_age_reduced_validated = survivor_age_reduced.__wrapped__
_survivor_reduction_fraction_validated = (
    survivor_reduction_fraction.__wrapped__
)
_weighted_mean_record_total_validated = weighted_mean_record_total.__wrapped__
_weighted_record_total_validated = weighted_record_total.__wrapped__
_whole_dollars_validated = whole_dollars.__wrapped__
_widow_reduction_period_months_validated = (
    widow_reduction_period_months.__wrapped__
)
_worker_age_adjusted_validated = worker_age_adjusted.__wrapped__
_worker_reduction_fraction_validated = worker_reduction_fraction.__wrapped__

# Reader guards add another public decorator. Private owned-value calls
# retain the original one-boundary schema contract across all layers.
_month_text_validated = _unwrap(YearMonth.__str__)

SavingsClauseGuard._admit_validated = _unwrap(SavingsClauseGuard.admit)
SavingsClauseGuard._evaluate_validated = _unwrap(SavingsClauseGuard.evaluate)
SavingsClauseGuard._skip_validated = _unwrap(SavingsClauseGuard.skip)
