"""Track B milestone G: the gross-benefit layer (Python statutory reference).

Verification class: statutory conformance (Track B design revision 3, §3.2
row G). Success admits gross monthly benefits for the supported family
configurations below, and nothing else: no population claim, no payment
timing, no earnings-test deductions (R2), no ARF or recomputation (R3).
Max's ruling d515 (2026-09-28) adopted §10 question 9's default: a Python
reference now, with Axiom differential checks as diagnostics once a pinned
rule exists. At this module's creation rulespec-us had no 42 U.S.C. 403
encoding, so no Axiom differential is run.

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
   here is not a net check. Gross rates assume no beneficiary on the record
   has a deduction or suspension: 203(a)(4) makes the maximum reduction
   after deductions, so a deduction can raise the others' rates (POMS RS
   00615.766). That ordering belongs to the RET ledger (R2).

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
with ValueError before family or household coverage refusals. The exact
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
exact integer/Boolean types and all existing cross-field checks. Invalid
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

Not implemented, and refused rather than approximated: 403(a)(5). When two
or more persons are entitled for a month in which the maximum reduces
benefits, and the PIA rises for the next month, that month's total (after
403(a) and 402(q)) is protected for every later month. G computes one
month at a time. :class:`SavingsClauseGuard` carries the protected total
across one record's months and refuses any later governed month whose total
falls below it, and every governed month after that one.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from numbers import Rational
from types import MappingProxyType

from populace_dynamics.ss.params import SSAParameters

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
    "family_maximum_bend_points",
    "family_maximum_formula",
    "floor_dime",
    "household_benefits",
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
class InvalidFamilyInput(ValueError):
    """The inputs do not describe a legal family (not a coverage gap)."""


class _InvalidInputType(InvalidFamilyInput, TypeError):
    """An input error, also retaining the constructor's TypeError contract."""


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


class FamilyConfigurationUnsupported(Exception):
    """``FAMILY_CONFIG_UNSUPPORTED``: a configuration G cannot compute.

    Rows raising this stay in every denominator (use
    :func:`evaluate_family` and :func:`count_family_outcomes`); a target
    that needs them is blocked (:class:`FamilyTargetBlocked`).
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
def _exact(value: object, label: str) -> Fraction:
    """Convert to an exact Fraction; floats go through their shortest repr.

    ``repr(492.9)`` is ``'492.9'``, so a float PIA from the float oracle
    becomes the decimal it prints as, never its binary expansion.
    """
    if isinstance(value, bool):
        raise _InvalidInputType(f"{label} must be a number, not a bool")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, (int, Rational)):
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidFamilyInput(f"{label} must be finite")
        return Fraction(repr(value))
    if isinstance(value, (str, Decimal)):
        try:
            return Fraction(value)
        except (ValueError, OverflowError, ZeroDivisionError) as error:
            raise InvalidFamilyInput(
                f"{label} must be a finite number"
            ) from error
    raise _InvalidInputType(
        f"{label} must be an exact number, got {type(value)}"
    )


def _dimes(value: object, label: str) -> Fraction:
    """A nonnegative amount that the statute keeps in whole dimes."""
    amount = _exact(value, label)
    if amount < 0:
        raise InvalidFamilyInput(f"{label} must be nonnegative")
    if (amount * 10).denominator != 1:
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
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise _InvalidInputType(f"{label} must be a sequence")


def _input_conditions(value: object, enum: type) -> None:
    if type(value) not in (set, frozenset, tuple, list):
        raise _InvalidInputType("conditions must be a collection of enums")
    for condition in value:
        _input_type(condition, enum, "condition")


def _checked_input(value, expected: type, label: str):
    """Revalidate a declaration, including nested fields, on an immutable copy.

    Constructors and entry points use the same field validation. Rebuilding
    also repeats their cross-field checks and numeric normalization, so even
    a deserialized or altered frozen declaration cannot bypass validation.
    No coverage decision belongs in this pass.
    """
    _input_type(value, expected, label)
    return replace(value)


def _validate_input_fields(value) -> None:
    """The shared public-declaration schema, before any coverage refusal.

    Monetary inputs retain the documented exact-number conversions. Enums,
    booleans and integers require their exact classes. Calendar and cohort
    years use datetime's 1..9999 domain. Parameter-dependent month bounds
    and family/household consistency run after cohort resolution.
    """
    if isinstance(value, YearMonth):
        _input_year(value.year, "year")
        _input_type(value.month, int, "month")
        if not 1 <= value.month <= 12:
            raise InvalidFamilyInput("month must be 1-12")
        return
    if isinstance(value, OwnBenefit):
        _input_type(value.kind, OwnBenefitKind, "kind")
        _dimes(value.pia, "own PIA")
        for name in ("reduction_months", "delayed_credit_months"):
            number = getattr(value, name)
            _input_type(number, int, name)
            if number < 0:
                raise InvalidFamilyInput(f"{name} must be nonnegative")
        if value.birth_year is not None:
            _input_year(value.birth_year, "birth_year")
        return
    if isinstance(value, Beneficiary):
        _input_text(value.beneficiary_id, "beneficiary_id")
        _input_type(value.role, Role, "role")
        _input_type(value.reduction_months, int, "reduction_months")
        if value.reduction_period_months is not None:
            _input_type(
                value.reduction_period_months, int, "reduction_period_months"
            )
        if value.birth_year is not None:
            _input_year(value.birth_year, "birth_year")
        _input_conditions(value.conditions, BeneficiaryCondition)
        if (
            value.child_in_care is not None
            and value.child_in_care is not False
        ):
            _input_text(value.child_in_care, "child_in_care")
        if value.own_benefit is not None:
            object.__setattr__(
                value,
                "own_benefit",
                _checked_input(value.own_benefit, OwnBenefit, "own_benefit"),
            )
        for name in ("own_benefit_first", "first_entitlement_child_in_care"):
            flag = getattr(value, name)
            if flag is not None:
                _input_type(flag, bool, name)
        # Role-specific care and OB-basis checks are shared by __post_init__.
        return
    if isinstance(value, (WorkerRecord, RecordState)):
        _input_type(value.kind, FamilyKind, "kind")
        if value.worker_birth_year is not None:
            _input_year(value.worker_birth_year, "worker_birth_year")
        if (
            isinstance(value, WorkerRecord)
            or value.eligibility_year is not None
        ):
            _input_year(value.eligibility_year, "eligibility_year")
        _input_conditions(value.conditions, RecordCondition)
        if value.first_dib_entitlement is not None:
            _checked_input(
                value.first_dib_entitlement, YearMonth, "first_dib_entitlement"
            )
        if isinstance(value, WorkerRecord):
            _input_sequence(value.cola_percents, "cola_percents")
            for percent in value.cola_percents:
                if _exact(percent, "COLA percent") < 0:
                    raise InvalidFamilyInput(
                        "A COLA percent cannot be negative"
                    )
            if value.aime is not None:
                if type(value.aime) not in (int, Fraction):
                    raise _InvalidInputType(
                        "AIME must be an int or an integral Fraction"
                    )
                if value.aime < 0 or Fraction(value.aime).denominator != 1:
                    raise InvalidFamilyInput(
                        "AIME must be a nonnegative whole dollar"
                    )
            for name in (
                "worker_reduction_months",
                "worker_delayed_credit_months",
            ):
                number = getattr(value, name)
                _input_type(number, int, name)
                if number < 0:
                    raise InvalidFamilyInput(f"{name} must be nonnegative")
        else:
            _input_text(value.source, "source")
            if value.worker is not None:
                object.__setattr__(
                    value,
                    "worker",
                    _checked_input(value.worker, OwnBenefit, "worker"),
                )
            if value.widow_drc_savings_clause is not None:
                _input_type(
                    value.widow_drc_savings_clause,
                    bool,
                    "widow_drc_savings_clause",
                )
            if value.deferred_refusal is not None:
                _input_type(value.deferred_refusal, tuple, "deferred_refusal")
                if len(value.deferred_refusal) != 2:
                    raise InvalidFamilyInput(
                        "deferred_refusal needs a reason and detail"
                    )
                reason, detail = value.deferred_refusal
                _input_type(
                    reason, UnsupportedReason, "deferred_refusal reason"
                )
                _input_text(detail, "deferred_refusal detail")
        return
    if isinstance(value, HouseholdRecord):
        _input_text(value.worker_id, "worker_id")
        object.__setattr__(
            value, "state", _checked_input(value.state, RecordState, "state")
        )
        _input_sequence(value.beneficiaries, "beneficiaries")
        object.__setattr__(
            value,
            "beneficiaries",
            tuple(
                _checked_input(b, Beneficiary, "beneficiary")
                for b in value.beneficiaries
            ),
        )
        return
    raise _InvalidInputType("Unknown input declaration")


def floor_dime(amount: Fraction) -> Fraction:
    """Decrease to the next lower multiple of $0.10 (exact)."""
    return Fraction(math.floor(amount * 10), 10)


def ceil_dime(amount: Fraction) -> Fraction:
    """Increase to the next higher multiple of $0.10 (exact)."""
    return Fraction(math.ceil(amount * 10), 10)


def whole_dollars(amount: Fraction) -> int:
    """42 U.S.C. 415(g): round a monthly benefit down to a whole dollar."""
    if amount < 0:
        raise ValueError("A benefit amount cannot be negative")
    return math.floor(amount)


def _nearest_dollar_ties_up(amount: Fraction) -> int:
    """215(a)(1)(B)(iii): nearest $1; a multiple of $0.50 rounds up."""
    return math.floor(amount + _HALF)


@dataclass(frozen=True, order=True)
class YearMonth:
    """A calendar month (the benefit month being computed)."""

    year: int
    month: int

    def __post_init__(self):
        _validate_input_fields(self)

    def as_tuple(self) -> tuple[int, int]:
        return (self.year, self.month)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


# ---------------------------------------------------------------------------
# Statutory rates, cross-checked against the repository's parameter bundle
# ---------------------------------------------------------------------------
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


def _agrees(observed: float, expected: Fraction, label: str) -> None:
    value = float(observed)
    if (
        not math.isfinite(value)
        or abs(value - float(expected)) > _RATE_TOLERANCE
    ):
        raise ValueError(
            f"Parameter bundle {label}={observed!r} disagrees with the "
            f"statutory {expected}; refusing to compute gross benefits."
        )


def statutory_rates(params: SSAParameters) -> StatutoryRates:
    """Cross-check the bundle against the statute; return exact fractions.

    policyengine-us stores 5/9 of 1 percent as the decimal 0.00555556, and
    SSA computes with the fraction (POMS RS 00615.005B), so the fraction is
    what is used once the bundle is confirmed to encode the same rate.
    Non-finite or mismatched rates raise ValueError, an input error rather
    than a coverage refusal. Family and household entry points check them
    before any coverage refusal.
    """
    worker_first, worker_later = params.early_monthly_rates
    _agrees(worker_first, _STATUTE["worker_first"], "early_monthly_rates[0]")
    _agrees(worker_later, _STATUTE["worker_later"], "early_monthly_rates[1]")
    spouse_first, spouse_later = params.spousal_early_monthly_rates
    _agrees(spouse_first, _STATUTE["spouse_first"], "spousal rate[0]")
    _agrees(spouse_later, _STATUTE["spouse_later"], "spousal rate[1]")
    _agrees(
        1 - params.survivor_reduction_floor,
        _STATUTE["survivor_max_reduction"],
        "1 - survivor_reduction_floor",
    )
    _agrees(params.rib_lim_pia_share, _STATUTE["rib_lim_share"], "rib_lim")
    _agrees(params.spousal_pia_share, _STATUTE["spouse_share"], "spouse")
    _agrees(params.survivor_pia_share, _STATUTE["widow_share"], "widow")
    if params.early_first_bracket_months != 36:
        raise ValueError("early_first_bracket_months must be 36 (402(q))")
    if params.spousal_early_first_bracket_months != 36:
        raise ValueError("spousal first bracket must be 36 months (402(q))")
    return StatutoryRates(
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
    if year not in params.nawi:
        raise KeyError(
            f"NAWI for {year} is not in the parameter bundle "
            f"(revision {params.pe_us_revision})."
        )
    return _exact(params.nawi[year], f"NAWI({year})")


def family_maximum_bend_points(
    eligibility_year: int, params: SSAParameters
) -> tuple[int, int, int]:
    """403(a)(2): the three family-maximum bend points for a year.

    Each 1979 amount times NAWI(year - 2) / NAWI(1977), rounded to the
    nearest dollar with 50-cent ties upward (215(a)(1)(B)(iii)).
    """
    if type(eligibility_year) is not int or eligibility_year < 1979:
        raise ValueError("The 403(a)(1) formula starts with 1979 eligibility")
    ratio = _nawi(params, eligibility_year - 2) / _nawi(params, BASE_NAWI_YEAR)
    first, second, third = (
        _nearest_dollar_ties_up(base * ratio)
        for base in FAMILY_MAXIMUM_BASE_BEND_POINTS
    )
    return first, second, third


def family_maximum_formula(
    pia: object, eligibility_year: int, params: SSAParameters
) -> Fraction:
    """403(a)(1)(A)-(D) before rounding: the exact formula amount."""
    amount = _dimes(pia, "PIA")
    points = family_maximum_bend_points(eligibility_year, params)
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


def retirement_survivor_family_maximum(
    pia: object, eligibility_year: int, params: SSAParameters
) -> Fraction:
    """403(a)(1): the retirement/survivor maximum at eligibility.

    ``pia`` is the PIA for the year of first eligibility before any COLA
    (POMS RS 00615.736A.1). The result is dime-floored (403(a)(1), last
    sentence). Apply COLAs with :func:`increase_by_colas`.
    """
    _require_supported_eligibility(eligibility_year)
    return floor_dime(family_maximum_formula(pia, eligibility_year, params))


def disability_family_maximum(pia: object, aime: object) -> Fraction:
    """403(a)(6): min(max(85% AIME, PIA), 150% PIA), dime-floored.

    Both amounts are those before COLAs (POMS RS 00615.742.1); apply the
    intervening COLAs afterwards with :func:`increase_by_colas`.
    """
    amount = _dimes(pia, "PIA")
    earnings = _exact(aime, "AIME")
    if earnings < 0 or earnings.denominator != 1:
        raise InvalidFamilyInput("AIME must be a nonnegative whole dollar")
    return floor_dime(
        min(max(_DI_AIME_SHARE * earnings, amount), _DI_PIA_CAP * amount)
    )


def increase_by_colas(amount: object, percents: Iterable[object]) -> Fraction:
    """215(i)(2)(A)(ii): apply each COLA in order, dime-floored each time.

    ``percents`` are percentages (``"2.8"`` for a 2.8 percent COLA), exact
    or float. A zero COLA leaves the amount unchanged; negative COLAs do
    not exist under 215(i) and are refused.
    """
    value = _dimes(amount, "amount")
    for index, percent in enumerate(percents):
        rate = _exact(percent, f"COLA percent #{index}")
        if rate < 0:
            raise InvalidFamilyInput("A COLA percentage cannot be negative")
        value = floor_dime(value * (1 + rate / 100))
    return value


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
    if not isinstance(payment_month, YearMonth):
        raise TypeError("payment_month must be a YearMonth")
    if type(eligibility_year) is not int:
        raise TypeError("eligibility_year must be an int")
    if eligibility_year > payment_month.year:
        raise InvalidFamilyInput(
            f"eligibility year {eligibility_year} is after the payment "
            f"month {payment_month}"
        )
    _require_supported_eligibility(eligibility_year)
    last = payment_month.year - (0 if payment_month.month == 12 else 1)
    percents = []
    for year in range(eligibility_year, last + 1):
        if year not in december_cola_percent:
            raise KeyError(f"No COLA percentage for December {year}")
        percents.append(_exact(december_cola_percent[year], f"COLA {year}"))
    return tuple(percents)


def _require_supported_eligibility(eligibility_year: int) -> None:
    if type(eligibility_year) is not int:
        raise TypeError("eligibility_year must be an int")
    if eligibility_year < FIRST_SUPPORTED_ELIGIBILITY_YEAR:
        raise FamilyConfigurationUnsupported(
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
    if type(value) is not int:
        raise TypeError(f"{label} must be an int")
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


def worker_reduction_fraction(months: int, params: SSAParameters) -> Fraction:
    """402(q)(1) old-age reduction for ``months`` months (RS 00615.101)."""
    months = _months(months, "months", _MAX_WORKER_REDUCTION_MONTHS)
    return _worker_reduction(months, statutory_rates(params))


def spouse_reduction_fraction(months: int, params: SSAParameters) -> Fraction:
    """402(q)(1) spouse's reduction for ``months`` months (RS 00615.201)."""
    months = _months(months, "months", _MAX_SPOUSE_REDUCTION_MONTHS)
    return _spouse_reduction(months, statutory_rates(params))


def survivor_reduction_fraction(
    months: int, reduction_period_months: int, params: SSAParameters
) -> Fraction:
    """Widow(er)'s reduction: 28.5 percent spread over the period.

    This is the fraction before SSA's rounding of the reduction amount;
    :func:`survivor_age_reduced` applies it to a benefit.
    """
    period = _survivor_period(reduction_period_months)
    months = _months(months, "months", period)
    return statutory_rates(params).survivor_max_reduction * months / period


def _drc_monthly_rate(birth_year: int, params: SSAParameters) -> Fraction:
    """402(w) monthly credit: the cohort's annual rate over 12, exactly."""
    annual = _exact(
        params.delayed_credit_annual_rate(birth_year), "DRC annual rate"
    )
    return annual / 12


def _refuse_early_delayed_credits(birth_year: int) -> None:
    if birth_year < FIRST_SUPPORTED_DELAYED_CREDIT_BIRTH_YEAR:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.DELAYED_CREDITS_BEFORE_1917,
            f"birth year {birth_year}: 402(w)(6)(A) gives 1/12 of 1 "
            "percent a month to a person first eligible before 1979 (born "
            "before 01/02/1917, POMS RS 00615.692D), and the parameter "
            "bundle's schedule does not",
        )


def _fra_months(birth_year: int, params: SSAParameters) -> int:
    """416(l): a finite bundle FRA before any month-bound comparison."""
    months = params.fra_months(birth_year)
    if not math.isfinite(months):
        raise ValueError("Full retirement age months must be finite")
    return months


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
    if type(birth_year) is not int:
        raise TypeError("birth_year must be an int")
    _refuse_early_delayed_credits(birth_year)
    return _AGE_70_MONTHS - _fra_months(birth_year, params)


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
    if type(months) is not int:
        raise TypeError("delayed_credit_months must be an int")
    if months < 0:
        raise InvalidFamilyInput("delayed_credit_months must be nonnegative")
    if months == 0:
        return 0
    if birth_year is None:
        raise InvalidFamilyInput("Delayed credits need the birth year")
    if type(birth_year) is not int:
        raise TypeError("birth_year must be an int")
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
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.OWN_RIB_HISTORY_BEFORE_1978,
            "own RIB with a positive reduction for a cohort before 1916 "
            "could have initial entitlement before January 1978; "
            "RS 00615.005C.2 requires the current money amount of "
            "reduction and historical PIA, which these inputs omit",
        )


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
    rates = statutory_rates(params)
    amount = _dimes(pia, "PIA")
    reduction_months = _cohort_reduction_months(
        reduction_months, birth_year, params, "reduction_months"
    )
    delayed_credit_months = _delayed_credit_months(
        delayed_credit_months, birth_year, params
    )
    _refuse_historical_own_rib(amount, reduction_months, birth_year)
    base = floor_dime(
        amount * (1 - _worker_reduction(reduction_months, rates))
    )
    if delayed_credit_months == 0:
        return base, base
    _refuse_early_delayed_credits(birth_year)
    credit = floor_dime(
        base * delayed_credit_months * _drc_monthly_rate(birth_year, params)
    )
    return base, base + credit


def spouse_age_reduced(
    amount: object, reduction_months: int, params: SSAParameters
) -> Fraction:
    """A spouse's benefit (after the maximum) reduced for age, dime-floored.

    RF 1-36: x (144 - RF)/144; RF 37-60: x (180 - ARM)/240 (POMS RS
    00615.201B.1.c). ``amount`` is the OB, or the family-maximum share when
    the maximum applies.
    """
    rates = statutory_rates(params)
    value = _dimes(amount, "spouse benefit")
    months = _months(
        reduction_months, "reduction_months", _MAX_SPOUSE_REDUCTION_MONTHS
    )
    return floor_dime(value * (1 - _spouse_reduction(months, rates)))


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
    rates = statutory_rates(params)
    value = _dimes(amount, "widow(er) benefit")
    period = _survivor_period(reduction_period_months)
    months = _months(reduction_months, "reduction_months", period)
    reduction = ceil_dime(
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


def widow_reduction_period_months(birth_date: date) -> int:
    """Total possible widow(er) reduction months for a date of birth.

    POMS RS 00615.301B.2: FRA 65 through 1/1/40, rising two months per
    year to 66 (born 1/2/45-1/1/57), then to 67 for births on or after
    1/2/62. The period runs from age 60 to that FRA.
    """
    if not isinstance(birth_date, date):
        raise TypeError("birth_date must be a datetime.date")
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


_LIFE_ROLES = frozenset(
    {Role.SPOUSE, Role.SPOUSE_CHILD_IN_CARE, Role.DIVORCED_SPOUSE, Role.CHILD}
)
_SURVIVOR_ROLES = frozenset(
    {
        Role.WIDOW,
        Role.SURVIVING_DIVORCED_SPOUSE,
        Role.MOTHER_FATHER,
        Role.CHILD,
        Role.PARENT,
        Role.DISABLED_WIDOW,
    }
)
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
        object.__setattr__(self, "pia", _dimes(self.pia, "own PIA"))
        if self.reduction_months < 0:
            raise InvalidFamilyInput("reduction_months must be nonnegative")
        _delayed_credit_months(
            self.delayed_credit_months, self.birth_year, None
        )
        if self.kind is OwnBenefitKind.DISABILITY:
            if self.delayed_credit_months:
                raise InvalidFamilyInput("A DIB earns no delayed credits")


def _refuse_own_benefit(own: OwnBenefit) -> None:
    """Own-benefit coverage, after own/family input checks have completed."""
    if own.kind is OwnBenefitKind.DISABILITY and own.reduction_months:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.DIB_AFTER_REDUCED_RIB,
            "a DIB reduced for prior reduced RIB (402(q)(2))",
        )
    if own.kind is OwnBenefitKind.OLD_AGE:
        _refuse_historical_own_rib(
            own.pia, own.reduction_months, own.birth_year
        )


def own_monthly_benefit(
    own: OwnBenefit, params: SSAParameters
) -> tuple[Fraction, Fraction]:
    """The own benefit ``(without_credits, with_credits)`` after 402(q)/(w)."""
    own = _checked_input(own, OwnBenefit, "own")
    _check_own_benefit(own, params)
    _refuse_own_benefit(own)
    return worker_age_adjusted(
        own.pia,
        own.reduction_months,
        own.delayed_credit_months,
        own.birth_year,
        params,
    )


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
        if self.child_in_care is not None:
            if self.role not in _WIDOW_ROLES | {Role.DIVORCED_SPOUSE}:
                raise InvalidFamilyInput(
                    "child_in_care is an input for widow(er) or divorced "
                    "spouse benefits"
                )
            if self.child_in_care is not False and (
                not isinstance(self.child_in_care, str)
                or not self.child_in_care
            ):
                raise InvalidFamilyInput(
                    "child_in_care must name an entitled child, or be "
                    "False or None"
                )
        if self.first_entitlement_child_in_care is not None:
            if self.role is not Role.DIVORCED_SPOUSE:
                raise InvalidFamilyInput(
                    "first_entitlement_child_in_care describes a divorced "
                    "spouse only"
                )
        object.__setattr__(self, "conditions", frozenset(self.conditions))
        if self.original_benefit_basis is not None:
            if self.role not in _WIDOW_ROLES:
                raise InvalidFamilyInput(
                    "Only a widow(er) OB can differ from the PIA share"
                )
            object.__setattr__(
                self,
                "original_benefit_basis",
                _dimes(self.original_benefit_basis, "OB basis"),
            )
        if self.own_benefit_first is not None:
            if self.own_benefit is None:
                raise InvalidFamilyInput(
                    "own_benefit_first describes an own benefit; there is "
                    "none"
                )
        elif (
            self.own_benefit is not None
            and self.role
            in (
                Role.SPOUSE,
                Role.DIVORCED_SPOUSE,
            )
            and not (
                self.role is Role.DIVORCED_SPOUSE
                and isinstance(self.child_in_care, str)
                and self.own_benefit.kind is OwnBenefitKind.OLD_AGE
            )
        ):
            raise InvalidFamilyInput(
                f"A dually entitled {self.role.value} needs own_benefit_first"
                ": method C (own benefit first, RS 00615.250) and method B "
                "(spouse benefit first, RS 00615.240) pay different amounts"
            )
        if self.reduction_months < 0:
            raise InvalidFamilyInput("reduction_months must be nonnegative")
        if self.reduction_months and self.role not in _AGE_REDUCED_ROLES:
            raise InvalidFamilyInput(
                f"A {self.role.value} benefit is not reduced for age"
            )
        if self.reduction_period_months is not None:
            if self.role is Role.DISABLED_WIDOW:
                raise InvalidFamilyInput(
                    "DWB uses a fixed reduction, not reduction months"
                )
            if self.role not in _WIDOW_ROLES:
                raise InvalidFamilyInput(
                    "Only a widow(er) has a survivor reduction period"
                )
            _survivor_period(self.reduction_period_months)


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
        object.__setattr__(
            self, "eligibility_pia", _dimes(self.eligibility_pia, "PIA")
        )
        object.__setattr__(
            self,
            "cola_percents",
            tuple(
                _exact(p, "COLA percent") for p in tuple(self.cola_percents)
            ),
        )
        object.__setattr__(self, "conditions", frozenset(self.conditions))
        if self.rib_lim_benefit is not None:
            if self.kind is not FamilyKind.SURVIVOR:
                raise InvalidFamilyInput("A RIB-LIM applies only to deaths")
            object.__setattr__(
                self,
                "rib_lim_benefit",
                _dimes(self.rib_lim_benefit, "RIB-LIM benefit"),
            )
        if self.kind is not FamilyKind.RETIREMENT and (
            self.worker_reduction_months or self.worker_delayed_credit_months
        ):
            raise InvalidFamilyInput(
                "Own-RIB months describe a living retired worker only"
            )
        _delayed_credit_months(
            self.worker_delayed_credit_months, self.worker_birth_year, None
        )


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
                    self, "worker", replace(self.worker, birth_year=year)
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
        raise FamilyConfigurationUnsupported(reason, detail)


def _refuse_record(record: WorkerRecord | RecordState) -> None:
    """One precedence for built and direct records, after all input checks."""
    if record.eligibility_year is not None:
        _require_supported_eligibility(record.eligibility_year)
    _raise_record_conditions(record.conditions)
    if (
        record.kind is FamilyKind.DISABILITY
        and record.first_dib_entitlement is not None
        and record.first_dib_entitlement.as_tuple()
        < DI_MAXIMUM_FIRST_ENTITLEMENT
    ):
        raise FamilyConfigurationUnsupported(
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


def record_state(record: WorkerRecord, params: SSAParameters) -> RecordState:
    """Compute the record's current PIA and family maximum.

    Record input errors are raised here. Coverage refusals are carried on
    the RecordState and raised only after family input checks, even when
    this builder is called inside an evaluate_family closure.
    """
    record = _checked_input(record, WorkerRecord, "record")
    statutory_rates(params)
    disability_maximum = None
    if record.kind is FamilyKind.DISABILITY:
        if record.aime is None or record.first_dib_entitlement is None:
            raise InvalidFamilyInput(
                "A disability record needs aime and first_dib_entitlement"
            )
        # Computed here so that an invalid AIME is an input error first.
        disability_maximum = disability_family_maximum(
            record.eligibility_pia, record.aime
        )
    _cohort_reduction_months(
        record.worker_reduction_months,
        record.worker_birth_year,
        params,
        "worker_reduction_months",
    )
    if type(record.eligibility_year) is not int:
        raise TypeError("eligibility_year must be an int")
    _check_retirement_eligibility(
        record.kind, record.eligibility_year, record.worker_birth_year
    )
    _delayed_credit_months(
        record.worker_delayed_credit_months, record.worker_birth_year, params
    )
    pia = increase_by_colas(record.eligibility_pia, record.cola_percents)
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
        base_maximum = retirement_survivor_family_maximum(
            record.eligibility_pia, record.eligibility_year, params
        )
    maximum = increase_by_colas(base_maximum, record.cola_percents)
    worker = None
    if record.kind is FamilyKind.RETIREMENT and (
        RecordCondition.WORKER_NOT_ENTITLED not in record.conditions
    ):
        worker = OwnBenefit(
            kind=OwnBenefitKind.OLD_AGE,
            pia=pia,
            reduction_months=record.worker_reduction_months,
            delayed_credit_months=record.worker_delayed_credit_months,
            birth_year=record.worker_birth_year,
        )
    return RecordState(
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


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BeneficiaryBenefit:
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

    @property
    def total_received(self) -> Fraction:
        """Auxiliary plus own benefit (the person's gross monthly total)."""
        return self.auxiliary_payable + (self.own_benefit or Fraction(0))


@dataclass(frozen=True)
class FamilyBenefits:
    """Gross monthly benefits on one record for one month."""

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

    def by_id(self) -> Mapping[str, BeneficiaryBenefit]:
        return MappingProxyType(
            {row.beneficiary_id: row for row in self.beneficiaries}
        )


# ---------------------------------------------------------------------------
# The family computation
# ---------------------------------------------------------------------------
def original_benefit(
    role: Role,
    kind: FamilyKind,
    pia: Fraction,
    basis: Fraction | None = None,
    *,
    parent_count: int = 1,
) -> Fraction:
    """The OB: the statutory share of the PIA, dime-floored.

    402(b)/(c)(2) 1/2; 402(d)(2) 1/2, or 3/4 after the worker's death;
    402(e)/(f)(2)(A) 100 percent (or the widow(er)'s larger OB basis);
    402(g)(2) 3/4; 402(h)(2) 82.5 percent for one entitled parent,
    75 percent for each of two (RS 00209.015).
    """
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
        if kind is not FamilyKind.SURVIVOR:
            raise InvalidFamilyInput("A parent's benefit needs a death")
        if type(parent_count) is not int or parent_count not in (1, 2):
            raise InvalidFamilyInput("parent_count must be one or two")
        share = Fraction(165, 200) if parent_count == 1 else Fraction(3, 4)
    else:
        raise ValueError(f"No original benefit is defined for {role}")
    return floor_dime(share * pia)


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
        own = replace(own, birth_year=year)
    if year == beneficiary.birth_year and own is beneficiary.own_benefit:
        return beneficiary
    return replace(beneficiary, birth_year=year, own_benefit=own)


def _check_beneficiary_inputs(
    beneficiary: Beneficiary, state: RecordState, params: SSAParameters
) -> None:
    """Input errors for a beneficiary with a resolved cohort, before refusal."""
    kind = state.kind
    allowed = _SURVIVOR_ROLES if kind is FamilyKind.SURVIVOR else _LIFE_ROLES
    if beneficiary.role not in allowed:
        raise InvalidFamilyInput(
            f"A {beneficiary.role.value} cannot be entitled on a "
            f"{kind.value} record"
        )
    own = beneficiary.own_benefit
    if beneficiary.role in _WIDOW_ROLES:
        if beneficiary.birth_year is not None:
            # All birth-year inputs use SSA's January 2-January 1 cohort,
            # so even a boundary cohort fixes exactly one .301B.2 period.
            year = beneficiary.birth_year
            expected = widow_reduction_period_months(date(year, 1, 2))
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
        if payment_month < YearMonth(1984, 1):
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.DISABLED_WIDOW_UNDER_60,
                "DWB payment months before January 1984 used an additional "
                "pre-60 reduction (RS 00615.310B.1/B.3), not implemented",
                beneficiary_id=bid,
            )
        if beneficiary.own_benefit is not None:
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
                "DWB with own RIB or DIB needs entitlement sequencing not "
                "settled by RS 00615.315 (which governs WIB/DWB election)",
                beneficiary_id=bid,
            )
    for condition in sorted(beneficiary.conditions, key=lambda c: c.value):
        if (
            condition is BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET
            and payment_month >= YearMonth(2024, 1)
        ):
            # Pub. L. 118-273; GN 02608.100: repeal is retroactive to
            # benefits for months after December 2023, not enactment month.
            continue
        reason, detail = _BENEFICIARY_CONDITION_REASONS[condition]
        raise FamilyConfigurationUnsupported(
            reason, detail, beneficiary_id=bid
        )
    own = beneficiary.own_benefit
    if beneficiary.role in _WIDOW_ROLES and own is not None:
        if own.kind is OwnBenefitKind.DISABILITY:
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
                "a widow(er) also entitled to DIB (402(q)(3)(C); POMS "
                "RS 00615.350) is not implemented",
                beneficiary_id=bid,
            )
        if beneficiary.birth_year < _FIRST_METHOD_B_WIDOW_BIRTH_YEAR:
            raise FamilyConfigurationUnsupported(
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
        raise FamilyConfigurationUnsupported(
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

    @property
    def dual(self) -> bool:
        return self.own_mba is not None


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
        max(Fraction(0), min(row.ob, floor_dime(row.ob * available / total)))
        for row in rows
    ]


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
            key: max(Fraction(0), min(ob, floor_dime(ob * pool / total)))
            for key, ob in nondual.items()
        }
    )


def _parisi_counted(
    row: _Row, state: RecordState, params: SSAParameters
) -> tuple[Fraction, Fraction]:
    """GN 02603.050A/C: partial payable plus auxiliary age reduction.

    The own-RIB reduction is not an auxiliary age reduction (GN
    02603.060B.2: $2.40 payable + $0.90 reduction, not the $16 own-RIB
    reduction). GN 02603.050A.2 disregards a dual rate reduced to zero.
    Own delayed credits and redistribution with an actually limiting
    RIB-LIM remain refused: none of the captured worked cases settles
    those interacting amounts. A considered but nonlimiting RIB-LIM
    changes no rate (RS 00615.320A.3).
    """
    beneficiary = row.beneficiary
    own = beneficiary.own_benefit
    if own.delayed_credit_months:
        raise FamilyConfigurationUnsupported(
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
            floor_dime(statutory_rates(params).rib_lim_share * state.pia),
        )
        if unlimited > limit:
            raise FamilyConfigurationUnsupported(
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
        if before_age > 0:
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.PARISI_AMBIGUOUS,
                "dual payable reaches zero only after auxiliary age reduction: "
                "GN 02603.045's before-age rule and GN 02603.050A.2's zero-rate "
                "exception do not settle whether the age amount stays in PTAP",
                beneficiary_id=beneficiary.beneficiary_id,
            )
        return Fraction(0), Fraction(0)
    if method_c:
        excess = max(Fraction(0), row.standard - own.pia)
        age_reduction = excess - spouse_age_reduced(
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
        if own is not None and beneficiary.own_benefit_first:
            excess = max(Fraction(0), row.rate - own.pia)
            high = max(Fraction(0), row.rate - (own.pia - row.own_base))
            low = max(Fraction(0), high - excess)
    else:
        if apply_rib_lim and state.rib_lim_benefit is not None:
            limit = max(
                state.rib_lim_benefit,
                floor_dime(statutory_rates(params).rib_lim_share * state.pia),
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
    raise FamilyConfigurationUnsupported(
        UnsupportedReason.REDUCED_BENEFIT_HISTORY_BEFORE_1978,
        f"a reduced {role.value} for cohort {year} could first be entitled "
        "before January 1978; RS 00615.005C.2 needs the historical money "
        "reduction and unreduced rate, and the supplied offsets, maximum "
        "and care minimum do not settle the amount without them",
        beneficiary_id=beneficiary.beneficiary_id,
    )


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
            reduced = spouse_age_reduced(
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
        reduced_excess = spouse_age_reduced(
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
            reduced = rate - ceil_dime(rate * Fraction(285, 1000))
        elif beneficiary.reduction_months:
            reduced = survivor_age_reduced(
                rate,
                beneficiary.reduction_months,
                beneficiary.reduction_period_months,
                params,
            )
        if apply_rib_lim and state.rib_lim_benefit is not None:
            rates = statutory_rates(params)
            limit = max(
                state.rib_lim_benefit,
                floor_dime(rates.rib_lim_share * state.pia),
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
    statutory_rates(params)
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
            f"payment month {payment_month}"
        )
    if (
        state.first_dib_entitlement is not None
        and state.first_dib_entitlement > payment_month
    ):
        raise InvalidFamilyInput(
            f"first DIB entitlement {state.first_dib_entitlement} is after "
            f"the payment month {payment_month}"
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
) -> int:
    """Resolve 402(h)(2)'s count, refusing the circular RIB threshold.

    RS 00209.001 excludes a parent whose own RIB is not less than the
    parent's benefit; RS 00209.015 counts an own-DIB parent as technically
    entitled. More than two declared parents needs a separate rule.
    """
    parents = [b for b in beneficiaries if b.role is Role.PARENT]
    if len(parents) > 2:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.PARENT_BENEFIT,
            "more than two declared parents is outside the one/two-parent "
            "rates settled by 402(h)(2) and RS 00209.015",
        )
    one_ob = original_benefit(Role.PARENT, FamilyKind.SURVIVOR, state.pia)
    two_ob = original_benefit(
        Role.PARENT, FamilyKind.SURVIVOR, state.pia, parent_count=2
    )
    potential = []
    for parent in parents:
        own = parent.own_benefit
        own_mba = None if own is None else own_monthly_benefit(own, params)[1]
        if own is not None and own.kind is OwnBenefitKind.OLD_AGE:
            if own_mba >= one_ob:
                continue
        potential.append((parent, own_mba))
    if len(potential) == 2:
        for parent, own_mba in potential:
            # Source conflict us:oasdi-parent-entitlement-count-interval
            if (
                parent.own_benefit is not None
                and parent.own_benefit.kind is OwnBenefitKind.OLD_AGE
                and own_mba >= two_ob
            ):
                raise FamilyConfigurationUnsupported(
                    UnsupportedReason.PARENT_BENEFIT,
                    "two potential parents with own RIB between the "
                    "75% and 82.5% OBs have a circular entitlement count "
                    "under RS 00209.001 and .015",
                    beneficiary_id=parent.beneficiary_id,
                )
    return max(1, len(potential))


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
                replace(
                    member,
                    role=Role.MOTHER_FATHER,
                    reduction_months=0,
                    reduction_period_months=None,
                    original_benefit_basis=None,
                    child_in_care=None,
                )
            )
        elif member.role in _WIDOW_ROLES:
            comparison.append(replace(member, child_in_care=False))
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
        raise FamilyConfigurationUnsupported(
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
            and state.first_dib_entitlement <= YearMonth(1978, 5)
        )
        or (state.first_dib_entitlement is None and possible_drc_protection)
    ):
        raise FamilyConfigurationUnsupported(
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
    rates = statutory_rates(params)
    beneficiaries = _check_family_inputs(
        state, beneficiaries, payment_month, params
    )
    _refuse_record(state)
    if state.deferred_refusal is not None:
        raise FamilyConfigurationUnsupported(*state.deferred_refusal)
    if payment_month.as_tuple() < FIRST_SUPPORTED_PAYMENT_MONTH:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.PAYMENT_MONTH_BEFORE_1983,
            "months before 1983 are outside the post-May-1982 rounding "
            "rules this layer implements",
        )
    for beneficiary in beneficiaries:
        _refuse_beneficiary(beneficiary, payment_month)
    ieds = RecordCondition.WORKER_NOT_ENTITLED in state.conditions
    if ieds and (
        payment_month < YearMonth(1985, 1)
        or (
            RecordCondition.WINDFALL_ELIMINATION_PROVISION in state.conditions
            and payment_month < YearMonth(2024, 1)
        )
    ):
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.INDEPENDENT_DIVORCED_SPOUSE,
            "IEDS before January 1985, or on a WEP-affected worker record "
            "before January 2024, is not implemented (RS 00202.100)",
        )
    parent_count = _entitled_parent_count(state, beneficiaries, params)
    life_case = state.kind is not FamilyKind.SURVIVOR and not ieds
    worker_benefit = None
    if state.kind is FamilyKind.RETIREMENT and not ieds:
        worker_benefit = own_monthly_benefit(state.worker, params)[1]
    elif state.kind is FamilyKind.DISABILITY:
        worker_benefit = state.pia

    rows: list[_Row] = []
    for beneficiary in beneficiaries:
        own_base = own_mba = None
        if beneficiary.own_benefit is not None:
            own_base, own_mba = own_monthly_benefit(
                beneficiary.own_benefit, params
            )
        ob = original_benefit(
            beneficiary.role,
            state.kind,
            state.pia,
            beneficiary.original_benefit_basis,
            parent_count=parent_count,
        )
        entitled, note = _is_entitled(
            beneficiary, state.pia, own_mba, parent_ob=ob
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
                raise FamilyConfigurationUnsupported(
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
                    raise FamilyConfigurationUnsupported(
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
            raise FamilyConfigurationUnsupported(
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
        if payment_month.as_tuple() < PARISI_FIRST_PAYMENT_MONTH:
            raise FamilyConfigurationUnsupported(
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
        shares = maximum_redistribution_rates(
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
            BeneficiaryBenefit(
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
                whole_dollar_auxiliary=whole_dollars(payable),
                whole_dollar_own=(
                    None if row.own_mba is None else whole_dollars(row.own_mba)
                ),
                note=row.note,
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
        0 if worker_benefit is None else whole_dollars(worker_benefit)
    ) + sum(row.whole_dollar_auxiliary for row in results)
    return FamilyBenefits(
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
            None if worker_benefit is None else whole_dollars(worker_benefit)
        ),
        beneficiaries=tuple(results),
        record_total=record_total,
        record_total_whole_dollars=record_whole,
        subject_total=subject_total,
        state_source=state.source,
        pe_us_revision=rates.pe_us_revision,
    )


# ---------------------------------------------------------------------------
# Households: every record a family draws on, computed together
# ---------------------------------------------------------------------------
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


@dataclass(frozen=True)
class HouseholdBenefits:
    """Gross monthly benefits on every record in a household for a month.

    Totals count what is paid on the household's records: each living
    worker's own benefit once (on their own record) and every auxiliary
    payment. A dually entitled person's own benefit from a record outside
    the household is reported on their row but not counted here.
    """

    payment_month: YearMonth
    records: Mapping[str, FamilyBenefits]

    @property
    def record_total(self) -> Fraction:
        return sum(
            (result.record_total for result in self.records.values()),
            Fraction(0),
        )

    @property
    def record_total_whole_dollars(self) -> int:
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
        return OwnBenefit(
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
            state = replace(state, worker_birth_year=year)
        beneficiaries = tuple(
            _with_effective_cohort(
                replace(b, birth_year=cohorts.get(b.beneficiary_id))
            )
            for b in record.beneficiaries
        )
        resolved[record_id] = replace(
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
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.COMBINED_FAMILY_MAXIMUM,
                f"a child entitled on records {ids}; 403(a)(3)(A) may "
                "combine their maximums (POMS RS 00615.770)",
                beneficiary_id=person,
            )
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.MULTIPLE_AUXILIARY_RECORDS,
            f"entitled as an auxiliary or survivor on records {ids} "
            "(simultaneous or dual entitlement across records, POMS RS "
            "00615.768A) is not implemented",
            beneficiary_id=person,
        )


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
    return HouseholdBenefits(payment_month, MappingProxyType(results))


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
            raise TypeError("guards must be SavingsClauseGuards")
        guards[record_id]._expect(payment_month)
    try:
        _refuse_household(held)
    except FamilyConfigurationUnsupported as error:
        for record_id, record in records.items():
            guards[record_id].skip(payment_month, pia=record.state.pia)
        return FamilyOutcome(key, weight, None, error)
    results = {}
    refusal = None
    for record_id in sorted(records):
        record = records[record_id]
        outcome = guards[record_id].evaluate(
            record_id,
            weight,
            lambda record=record: _family_benefits(
                record.state, record.beneficiaries, payment_month, params
            ),
            pia=record.state.pia,
        )
        if outcome.unsupported is not None and refusal is None:
            error = outcome.unsupported
            refusal = FamilyConfigurationUnsupported(
                error.reason,
                error.detail,
                beneficiary_id=error.beneficiary_id,
                record_id=record_id,
            )
        elif outcome.supported:
            results[record_id] = outcome.benefits
    if refusal is not None:
        return FamilyOutcome(key, weight, None, refusal)
    return FamilyOutcome(
        key,
        weight,
        HouseholdBenefits(payment_month, MappingProxyType(results)),
        None,
    )


# ---------------------------------------------------------------------------
# 403(a)(5): carried across a record's months, refused, never approximated
# ---------------------------------------------------------------------------
def savings_clause_total(result: FamilyBenefits) -> Fraction:
    """The total 403(a)(5) protects: after 403(a) and 402(q).

    The worker's own benefit plus each beneficiary subject to the maximum
    after age reduction and before the 402(k)(3)(A) offset. Divorced
    beneficiaries are outside 403(a) (403(a)(3)(C)).
    """
    if not isinstance(result, FamilyBenefits):
        raise TypeError("savings_clause_total takes one record's result")
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
        return YearMonth(month.year + 1, 1)
    return YearMonth(month.year, month.month + 1)


def _previous_month(month: YearMonth) -> YearMonth:
    if month.month == 1:
        return YearMonth(month.year - 1, 12)
    return YearMonth(month.year, month.month - 1)


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


class SavingsClauseGuard:
    """403(a)(5) for one insured worker's record, carried month to month.

    403(a)(5): when two or more persons are entitled for a month in which
    the maximum applies, and the PIA is increased for the following month,
    that month's total is treated as increased by the smallest amount that
    keeps "the total ... for any such subsequent month" from falling below
    it (both totals after 403(a) and 402(q)). The guarantee is not limited
    to the next month, and a saving clause, once established, "will
    continue in effect until the table or formula maximum becomes larger"
    and may become payable again (POMS RS 00615.801B.2). G computes one
    month at a time and does not compute the raise, so it refuses.

    Create one guard per record at its first month and give it every
    month in order, with :meth:`admit` (a result G computed),
    :meth:`skip` (a month G refused for another reason) or
    :meth:`evaluate` (which does either and returns a
    :class:`FamilyOutcome` for the denominators). The guard:

    * **protects** the total of a *qualifying* month: two or more persons
      entitled, the maximum reducing benefits (binding), and a higher PIA
      in the next month. The highest protected total is carried forward
      (:attr:`protected_total`);
    * **refuses** (``savings_clause_403a5``) any later governed month whose total
      falls below the protected total, whether or not the PIA rose into
      it and whether or not the maximum binds in it, and every governed month after
      the first such month, because the clause then stays in effect;
    * **refuses** (``savings_clause_history_unknown``) every later governed month
      once a protected total may exist that G cannot see: a path that does
      not start at the record's first month of entitlement
      (``earlier_months_unknown=True``), a skipped month while a protected
      total is in force (its total may have fallen below it), or a skipped
      month followed by a PIA increase or with no PIA given (it may have
      qualified);
    * **computes** a month in which no beneficiary is subject to the
      maximum, whatever came before, because 403(a)(4) reduces only
      benefits other than the worker's own and there is nothing to raise.
      Its total still counts: one below the protected total puts the
      clause into effect for later months.

    Known over-refusals, kept because they are conservative: a month in
    which the maximum does not bind (403(a)(4) only decreases benefits,
    so on the statute's text a larger maximum changes nothing there, but
    SSA's procedure in RS 00630.400 divides the protected payment among
    the auxiliaries without mentioning the OB cap); a total that falls
    because a beneficiary left at any later time, even six months after
    a December COLA; every later governed month is then refused (whether a
    change of membership triggers the clause is not settled by any
    captured source); and every governed month after a skipped one while a
    protected total is in force. The guard follows the record across a
    change of kind (a DIB converting to a RIB, or the worker's death),
    because 403(a)(5) speaks of the total "on the basis of such wages".
    """

    def __init__(
        self, first_month: YearMonth, *, earlier_months_unknown: bool
    ):
        first_month = _checked_input(first_month, YearMonth, "first_month")
        _input_type(earlier_months_unknown, bool, "earlier_months_unknown")
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

    @property
    def next_month(self) -> YearMonth:
        """The month the guard expects next."""
        return self._next

    @property
    def protected_total(self) -> Fraction | None:
        """The highest total protected so far (None: nothing protected)."""
        return self._floor

    @property
    def protected_since(self) -> YearMonth | None:
        """The qualifying month whose total is :attr:`protected_total`."""
        return self._floor_month

    @property
    def refused_since(self) -> YearMonth | None:
        """The first month whose total fell below the protected total."""
        return self._refused_since

    @property
    def unknown_since(self) -> YearMonth | None:
        """The month from which a protection G cannot see may exist."""
        return self._unknown_since

    def _expect(self, month: YearMonth) -> None:
        _checked_input(month, YearMonth, "month")
        _checked_input(self._next, YearMonth, "guard next_month")
        # Check advancement before carrying protection or changing any history.
        # December 9999 has no representable successor in the calendar domain.
        _next_month(month)
        if month != self._next:
            raise InvalidFamilyInput(
                f"the guard expects {self._next}, not {month}: give it "
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
        elif _qualifies(prior.result):
            total = savings_clause_total(prior.result)
            if self._floor is None or total > self._floor:
                self._floor, self._floor_month = total, prior.month

    def admit(self, result: FamilyBenefits) -> FamilyBenefits:
        """Carry the protection into ``result``'s month.

        Returns ``result`` when 403(a)(5) cannot change it; otherwise
        raises :class:`FamilyConfigurationUnsupported`. Either way the
        guard moves to the next month.
        """
        if not isinstance(result, FamilyBenefits):
            raise TypeError("admit takes one record's FamilyBenefits")
        month = result.payment_month
        self._expect(month)
        self._carry(result.pia)
        self._prior = _PriorMonth(month, result, result.pia)
        self._next = _next_month(month)
        total = savings_clause_total(result)
        # Source conflict us:oasdi-family-maximum-saving-clause
        below = self._floor is not None and total < self._floor
        first_fall = below and self._refused_since is None
        if first_fall:
            self._refused_since = month
        if not _governed(result):
            return result
        if self._refused_since is not None and not first_fall:
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.SAVINGS_CLAUSE,
                f"403(a)(5) took effect in {self._refused_since} and stays "
                "in effect (POMS RS 00615.801B.2); G does not compute the "
                "raised total",
            )
        if self._unknown_since is not None:
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.SAVINGS_CLAUSE_HISTORY_UNKNOWN,
                f"a protected total may exist from {self._unknown_since} "
                "that G did not see (a month it did not compute, or a path "
                "that does not start at entitlement)",
            )
        if first_fall:
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.SAVINGS_CLAUSE,
                f"the total after 403(a) and 402(q) is {_money_text(total)}"
                f", below the {_money_text(self._floor)} protected since "
                f"{self._floor_month}; 403(a)(5) would raise it (not "
                "implemented)",
            )
        return result

    def skip(self, month: YearMonth, *, pia: object = None) -> None:
        """Record a month of this record that G did not compute.

        ``pia`` is the record's PIA for that month, when the caller knows
        it; without it a PIA increase cannot be ruled out.
        """
        self._expect(month)
        amount = None if pia is None else _dimes(pia, "PIA")
        self._carry(amount)
        if self._floor is not None:
            # The skipped month's total may have fallen below the
            # protected total, putting the clause into effect.
            self._unknown_since = self._unknown_since or month
        self._prior = _PriorMonth(month, None, amount)
        self._next = _next_month(month)

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
        _check_evaluation_inputs(key, weight, compute)
        month = self._next
        self._expect(month)
        if pia is not None:
            pia = _dimes(pia, "PIA")
        try:
            result = compute()
        except FamilyConfigurationUnsupported as error:
            self.skip(month, pia=pia)
            return FamilyOutcome(key, weight, None, error)
        if not isinstance(result, FamilyBenefits):
            raise _InvalidInputType(
                "compute must return one record's FamilyBenefits"
            )
        if pia is not None and _dimes(pia, "PIA") != result.pia:
            raise InvalidFamilyInput(
                f"pia {pia} disagrees with the computed PIA {result.pia}"
            )
        try:
            self.admit(result)
        except FamilyConfigurationUnsupported as error:
            return FamilyOutcome(key, weight, None, error)
        return FamilyOutcome(key, weight, result, None)


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


@dataclass(frozen=True)
class FamilyOutcome:
    """One record-month: its benefits, or why it is unsupported."""

    key: str
    weight: Fraction
    benefits: FamilyBenefits | HouseholdBenefits | None
    unsupported: FamilyConfigurationUnsupported | None

    def __post_init__(self):
        _input_text(self.key, "key")
        if self.benefits is not None and type(self.benefits) not in (
            FamilyBenefits,
            HouseholdBenefits,
        ):
            raise _InvalidInputType(
                "benefits must be family or household benefits"
            )
        if self.unsupported is not None:
            _input_type(
                self.unsupported, FamilyConfigurationUnsupported, "unsupported"
            )
        if (self.benefits is None) == (self.unsupported is None):
            raise InvalidFamilyInput(
                "Exactly one of benefits/unsupported is set"
            )
        object.__setattr__(self, "weight", _outcome_weight(self.weight))

    @property
    def supported(self) -> bool:
        return self.benefits is not None


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
        return FamilyOutcome(key, weight, None, error)
    if not isinstance(benefits, (FamilyBenefits, HouseholdBenefits)):
        raise _InvalidInputType(
            "compute must return family or household benefits"
        )
    return FamilyOutcome(key, weight, benefits, None)


@dataclass(frozen=True)
class FamilyDenominator:
    """Counts over every outcome, supported or not."""

    rows: int
    weight: Fraction
    supported_rows: int
    supported_weight: Fraction
    unsupported_rows: int
    unsupported_weight: Fraction
    unsupported_by_reason: Mapping[UnsupportedReason, tuple[int, Fraction]]

    @property
    def supported_weight_share(self) -> Fraction:
        if self.weight == 0:
            raise ZeroDivisionError("No weight in the denominator")
        return self.supported_weight / self.weight


def count_family_outcomes(
    outcomes: Iterable[FamilyOutcome],
) -> FamilyDenominator:
    """Tabulate outcomes; unsupported rows are counted, never dropped."""
    outcomes = tuple(outcomes)
    keys = Counter(outcome.key for outcome in outcomes)
    duplicates = sorted(key for key, count in keys.items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate outcome keys: {duplicates[:5]}")
    by_reason: dict[UnsupportedReason, tuple[int, Fraction]] = {}
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
    return FamilyDenominator(
        rows=len(outcomes),
        weight=sum((o.weight for o in outcomes), Fraction(0)),
        supported_rows=len(supported),
        supported_weight=sum((o.weight for o in supported), Fraction(0)),
        unsupported_rows=len(unsupported),
        unsupported_weight=sum((o.weight for o in unsupported), Fraction(0)),
        unsupported_by_reason=MappingProxyType(dict(by_reason)),
    )


def _require_all_supported(outcomes: Sequence[FamilyOutcome]) -> None:
    blocked = [o for o in outcomes if not o.supported]
    if blocked:
        denominator = count_family_outcomes(outcomes)
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


def weighted_record_total(outcomes: Iterable[FamilyOutcome]) -> Fraction:
    """Weighted sum of record totals; blocked if any row is unsupported."""
    outcomes = tuple(outcomes)
    _require_all_supported(outcomes)
    return sum(
        (o.weight * o.benefits.record_total for o in outcomes), Fraction(0)
    )


def weighted_mean_record_total(outcomes: Iterable[FamilyOutcome]) -> Fraction:
    """Weighted mean over *all* rows; blocked if any row is unsupported."""
    outcomes = tuple(outcomes)
    denominator = count_family_outcomes(outcomes)
    _require_all_supported(outcomes)
    if denominator.weight == 0:
        raise ZeroDivisionError("No weight in the denominator")
    return weighted_record_total(outcomes) / denominator.weight
