"""Statutory delayed-retirement credit fractions (42 USC 402(w)).

Verification class: statutory conformance. Admitted scope: the credit
fraction for births from 1917 on invented claims and captured SSA tables
and examples. No population, behavioral, or forecast claim is admitted.
This is a float reference beside Track B G's exact-fraction computation;
it does not apply payment rounding or calendar-year credit posting.

402(w)(2)(A) counts increment months that have elapsed "after the month
before the month in which such individual attained retirement age" and
"prior to the month in which such individual attained age 70". For a
first entitlement delayed from FRA, the window is therefore 840 minus
FRA in months (POMS RS 00615.692E). 402(w)(6) determines the monthly
percentage; the bundle's annual cohort rate divided by 12 agrees with
POMS RS 00615.692D for births from 1917. For earlier births,
402(w)(6)(A) instead gives "1 ⁄ 12 of 1 percent" a month. The bundle
carries 3 percent annually, and RS 00615.692E's historical windows can
also differ, so positive delayed credits for those births are refused.
Nonpositive delays return zero before any parameter lookup.

These quotations come from the manifest-pinned LII excerpt
``tests/data/track_b/gross_benefit_sources/lii_usc_402_415_excerpts.txt``;
the same manifest pins ``poms_rs_00615_692.html``. Source integrity,
verbatim rules and figures, and the $1,175 worked example are tested in
``tests/ss/test_delayed_credit_statute.py``.

The sealed oracle keeps its 48-month cap by design. ``ss/benefits.py``
and ``ss/params.py`` belong to the source identity sealed against reviewed
commit ``1c7f3540`` by ``scripts/first_estimates_birth_evidence.py``.
They remain byte-identical to their reviewed implementation. Registered
first estimates, Track A COLA, FRA 68, Track M, R7 earnings sharing, and
cost ordering's R7 component used that legacy computation and stand as
registered. R7's career-frame cutoff does not restrict linked PIA supply:
older deceased workers can reach the credit in baseline and 1a survivor
paths, including indexable births before 1917. No affected-person count
is known, and no committed artifact is edited or rerun. The static audit is
``docs/errata/2026-10-11-delayed-credit-window.md``. As with
``ss/statutory_aime.py``, this module sits beside the sealed oracle and
names both conventions. New work and any later registered rerun selects
``DelayedCreditWindow.STATUTORY`` explicitly through
:func:`oracle_delayed_credit` and declares that convention.

``months_late`` measures months from FRA to first entitlement. A lawful
claim after 70 earns no additional credit, so the delay is truncated to
the window. G instead accepts already-counted increment months and
rejects an excess. Both interfaces use POMS' January 2 to January 1
cohort bands: callers representing a January 1 birthday pass the
preceding cohort year. Suspensions, penalties and other interruptions
of credit accrual under 402(w)(2)(B) need an explicit month ledger and
are outside this reference.
"""

from __future__ import annotations

from enum import Enum

from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters

__all__ = ["DelayedCreditWindow", "delayed_credit", "oracle_delayed_credit"]

#: 402(w)(2)(A): increment months end before the month of attaining 70.
_AGE_70_MONTHS = 70 * 12
_MONTHS = 12
#: 402(w)(6)(A); POMS RS 00615.692D: earlier cohorts need a 1% annual rate.
_FIRST_SUPPORTED_BIRTH_YEAR = 1917


class DelayedCreditWindow(str, Enum):
    """The convention explicitly selected for a delayed-credit reference.

    ``STATUTORY``: 402(w)(2)(A)'s FRA-to-70 window, through
    :func:`delayed_credit`. ``LEGACY_48_MONTH_CAP``: the unchanged
    :func:`populace_dynamics.ss.benefits.delayed_credit`, including its
    bundle maximum (48 in the captured bundle) and historical rates.
    """

    STATUTORY = "statutory_402_w_2"
    LEGACY_48_MONTH_CAP = "legacy_48_month_cap"


def delayed_credit(
    months_late: int, birth_year: int, params: SSAParameters
) -> float:
    """402(w) credit fraction for a first claim delayed from FRA.

    Credit ``min(months_late, 840 - FRA)`` months at one twelfth of the
    bundle's cohort annual rate (402(w)(6); RS 00615.692D-E). Return
    float zero for nonpositive delays or an empty window. Positive
    delays before the 1917 cohort raise ``ValueError`` because the
    bundle does not supply 402(w)(6)(A)'s historical rate.
    """
    if months_late <= 0:
        return 0.0
    if birth_year < _FIRST_SUPPORTED_BIRTH_YEAR:
        raise ValueError(
            f"birth year {birth_year}: 402(w)(6)(A) gives 1/12 of 1 "
            "percent a month before first eligibility in 1979 (births "
            "before 01/02/1917, POMS RS 00615.692D); the parameter "
            "bundle instead carries 3 percent annually"
        )
    window = _AGE_70_MONTHS - params.fra_months(birth_year)
    credited = min(months_late, window)
    if credited <= 0:
        return 0.0
    return (credited / _MONTHS) * params.delayed_credit_annual_rate(birth_year)


def oracle_delayed_credit(
    months_late: int,
    birth_year: int,
    params: SSAParameters,
    *,
    window: DelayedCreditWindow,
) -> float:
    """Compute the delayed-credit fraction under an explicit convention.

    ``STATUTORY`` uses :func:`delayed_credit`; ``LEGACY_48_MONTH_CAP``
    uses the unchanged sealed ``benefits.delayed_credit``. There is no
    default convention, as in ``statutory_aime.oracle_aime``.
    """
    convention = DelayedCreditWindow(window)
    if convention is DelayedCreditWindow.LEGACY_48_MONTH_CAP:
        return benefits.delayed_credit(months_late, birth_year, params)
    return delayed_credit(months_late, birth_year, params)
