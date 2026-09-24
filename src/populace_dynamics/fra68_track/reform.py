"""The reform switch for DynaSim exercise 3: full retirement age to 68.

Python oracle (not Axiom).  Urban Institute (2010), Table 1: "Gradually
increase FRA beginning in 2010 until it reaches 68 for those turning 62 in
2022 and later."  Under the statute the full retirement age (42 USC
416(l), the "retirement age") enters a benefit only through the age
factor: the early-claiming reduction (402(q)) and the delayed retirement
credit (402(w)).  The oracle already encodes both from parameters
(:func:`populace_dynamics.ss.benefits.early_reduction`,
:func:`~populace_dynamics.ss.benefits.spousal_early_reduction`,
:func:`~populace_dynamics.ss.benefits.survivor_reduction`,
:func:`~populace_dynamics.ss.benefits.delayed_credit` and
:func:`populace_dynamics.claiming.benefit_factor`), and each reads the
retirement age from ``SSAParameters.fra_months`` or, for widow(er)s, the
span ``SSAParameters.survivor_reduction_period_months``.  So the reform is
two parameter overrides of the oracle's bundle and adds no statutory rule
coverage (``ss/__init__.py``: "Do not extend this module's rule
coverage"):

* :func:`reform_parameters` replaces ``fra_months_by_birth_year`` with a
  frozen phase-in schedule (:class:`FRASchedule`);
* :func:`survivor_parameters` sets ``survivor_reduction_period_months`` to
  the widow(er)'s retirement age minus 60 years, where the widow(er)'s
  retirement age is the worker schedule's value two birth cohorts earlier
  (:func:`survivor_retirement_age_months`).  416(l)(1) keys the schedule to
  the year a person attains "early retirement age", and 416(l)(2) makes
  that age 62 for old-age, wife's and husband's benefits and 60 for a
  widow(er)'s benefit, so a widow(er) born in ``b`` attains it in the year
  a worker born in ``b - 2`` does.

Whether this override is within the oracle's scope for exercise 3 awaits
Max's ruling (decision record d188, item (a); plan section 11, item 2(a)).
It is the plan's recommended default and a parameter of
:class:`~populace_dynamics.fra68_track.config.FRA68Config`.

The three phase-in readings (plan ``critical-path-fra68-20260923.md``
section 3), each by the year ``Y`` a worker turns 62 (birth year
``Y - 62``):

* **P3** (the plan's recommended primary, awaiting Max, d188 item (b)):
  66 years plus ``round(24 * (Y - 2009) / 13)`` months for 2010-2021 and
  68 from 2022.  The only whole-month path that meets both of Table 1's
  dates; no rounding tie arises (``48 k`` is even, ``13`` odd).
* **P1**: 66 plus ``2 * (Y - 2010)`` months for 2011-2021, 68 from 2022
  (the statutory two-month step; the first affected cohort turns 62 in
  2011).
* **P2**: 66 plus ``2 * (Y - 2009)`` months from 2010, capped at 68 (the
  statutory step; 68 is reached by the 2021 cohort).

Every schedule is the statute's (the baseline bundle's) value for cohorts
it does not reach, at or above the baseline for every cohort, and 68
(816 months) for everyone born in 1960 or later.  :func:`reform_parameters`
refuses a schedule or a baseline for which any of that fails.  Nothing
here reads PSID, projects a population or reads a comparator value.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from populace_dynamics import claiming
from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "AGE_60_MONTHS",
    "AGE_62_MONTHS",
    "AGE_70_MONTHS",
    "BASE_FRA_MONTHS",
    "CONVERSION_CLAIM_EXCESS_MONTHS_EARLY_RULE",
    "FINAL_YEAR_TURNING_62",
    "FIRST_OPTION_YEAR",
    "LAST_UNCHANGED_YEAR",
    "PLAN_RECOMMENDED_PRIMARY_SCHEDULE",
    "SCHEDULES",
    "SCHEDULE_ORDER",
    "SPOUSE_EXCESS_MONTHS_EARLY_RULE",
    "SURVIVOR_COHORT_OFFSET",
    "SURVIVOR_EARLY_RETIREMENT_AGE",
    "TARGET_FRA_MONTHS",
    "WORKER_EARLY_RETIREMENT_AGE",
    "FRASchedule",
    "conversion_claim_excess_months_early",
    "fra_increase_months",
    "opening_stock_factor_ratio",
    "parameters_fra_sha256",
    "reform_parameters",
    "spouse_age_factor",
    "spouse_excess_months_early",
    "survivor_parameters",
    "survivor_retirement_age_months",
    "worker_factor_ratio",
]

_MONTHS = 12
#: 416(l)(2): early retirement age is 62 for old-age, wife's and husband's
#: benefits and 60 for a widow(er)'s benefit.
WORKER_EARLY_RETIREMENT_AGE = 62
SURVIVOR_EARLY_RETIREMENT_AGE = 60
#: A widow(er) born in ``b`` attains early retirement age (60) in the year
#: a worker born in ``b - 2`` attains it (62).
SURVIVOR_COHORT_OFFSET = (
    WORKER_EARLY_RETIREMENT_AGE - SURVIVOR_EARLY_RETIREMENT_AGE
)
AGE_60_MONTHS = SURVIVOR_EARLY_RETIREMENT_AGE * _MONTHS
AGE_62_MONTHS = WORKER_EARLY_RETIREMENT_AGE * _MONTHS
AGE_70_MONTHS = 70 * _MONTHS
#: Table 1: FRA is 66 "for those age 62 today" (the 2009 cohort) ...
BASE_FRA_MONTHS = 66 * _MONTHS
LAST_UNCHANGED_YEAR = 2009
#: ... the increase begins "in 2010" ...
FIRST_OPTION_YEAR = 2010
#: ... "until it reaches 68 for those turning 62 in 2022 and later".
FINAL_YEAR_TURNING_62 = 2022
TARGET_FRA_MONTHS = 68 * _MONTHS
#: Plan section 3: the recommended primary.  Awaiting Max (d188 item (b));
#: a parameter of ``FRA68Config.primary_schedule_id``.
PLAN_RECOMMENDED_PRIMARY_SCHEDULE = "P3"
#: The order in which the two non-primary schedules fill rows F1 and F2.
SCHEDULE_ORDER = ("P1", "P2", "P3")
#: Birth years the guards scan (well past every cohort in the cohort).
_GUARD_BIRTH_YEARS = range(1900, 2031)
#: The spouse's-excess months-early rule, as the E1 section 21 block
#: states it (``claiming.spouse_excess_months_early``; E1 section 13).
SPOUSE_EXCESS_MONTHS_EARLY_RULE = (
    "max(0, reform_fra(b_s) - max(m_s, 12*(worker_reform_entitlement_year "
    "- b_s))); m_s = the spouse's own reform claim month, 12*a_s if not "
    "transformed; a converted worker's conversion claim follows "
    "amounts.conversion_claim_spouse_excess_months_early"
)
#: The months-early rule of a spouse's excess resting on a converted
#: disabled worker's conversion claim, as the E1 section 21 block states
#: it (``amounts.conversion_claim_spouse_excess_months_early``; E1
#: sections 11-13; the review of ``e1-draft-4``).
CONVERSION_CLAIM_EXCESS_MONTHS_EARLY_RULE = (
    "max(0, reform_fra(b_s) - (max(12*(y_conv_base - b_s), "
    "12*(worker_baseline_entitlement_year - b_s)) + D(b_s))), which equals "
    "Track A's baseline count in every scenario and under every claiming "
    "response; y_conv_base = Track A's own claim year of the converted "
    "worker (its baseline conversion year), "
    "worker_baseline_entitlement_year = the worker's entitlement year "
    "before any C1/C2 move, D(b_s) = reform_fra(b_s) - baseline_fra(b_s)"
)


@dataclass(frozen=True)
class FRASchedule:
    """A frozen reform FRA schedule by the year a worker turns 62.

    ``months_by_year_turning_62`` lists every year from
    :data:`FIRST_OPTION_YEAR` through :data:`FINAL_YEAR_TURNING_62`; later
    years take :data:`TARGET_FRA_MONTHS`.  Years before the first option
    year are not the reform's: the baseline (statutory) schedule applies.
    """

    schedule_id: str
    rule: str
    months_by_year_turning_62: Mapping[int, int]

    def __post_init__(self) -> None:
        table = {
            int(year): int(months)
            for year, months in self.months_by_year_turning_62.items()
        }
        expected = set(range(FIRST_OPTION_YEAR, FINAL_YEAR_TURNING_62 + 1))
        if set(table) != expected:
            raise ValueError(
                f"{self.schedule_id}: the schedule must list every year "
                f"{FIRST_OPTION_YEAR}-{FINAL_YEAR_TURNING_62}"
            )
        if table[FINAL_YEAR_TURNING_62] != TARGET_FRA_MONTHS:
            raise ValueError(
                f"{self.schedule_id}: FRA must be 68 for those turning 62 in "
                f"{FINAL_YEAR_TURNING_62} (Table 1)"
            )
        values = [table[year] for year in sorted(table)]
        if any(
            later < earlier
            for earlier, later in zip(values, values[1:], strict=False)
        ):
            raise ValueError(f"{self.schedule_id}: the schedule must not fall")
        if not all(
            BASE_FRA_MONTHS <= value <= TARGET_FRA_MONTHS for value in values
        ):
            raise ValueError(
                f"{self.schedule_id}: every value must lie between 66 and 68"
            )
        object.__setattr__(
            self, "months_by_year_turning_62", dict(sorted(table.items()))
        )

    def months_for_year_turning_62(self, year: int) -> int | None:
        """The reform FRA for a cohort turning 62 in ``year``, or ``None``.

        ``None`` means the reform does not set this cohort (it turned 62
        before the option's first year): the baseline schedule applies.
        """

        year = int(year)
        if year < FIRST_OPTION_YEAR:
            return None
        if year >= FINAL_YEAR_TURNING_62:
            return TARGET_FRA_MONTHS
        return self.months_by_year_turning_62[year]

    def months_for_birth_year(self, birth_year: int) -> int | None:
        return self.months_for_year_turning_62(
            int(birth_year) + WORKER_EARLY_RETIREMENT_AGE
        )

    def as_dict(self) -> dict[str, Any]:
        """The canonical record (the specification block's form)."""

        return {
            "schedule_id": self.schedule_id,
            "rule": self.rule,
            "months_by_year_turning_62": {
                str(year): months
                for year, months in self.months_by_year_turning_62.items()
            },
            "months_from_year_turning_62": {
                str(FINAL_YEAR_TURNING_62): TARGET_FRA_MONTHS
            },
        }

    def sha256(self) -> str:
        """SHA-256 of :meth:`as_dict` in canonical JSON (recorded per run)."""

        encoded = json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _p1() -> FRASchedule:
    return FRASchedule(
        schedule_id="P1",
        rule=(
            "66 years + 2*(Y-2010) months for Y (year turning 62) 2011-2021; "
            "68 from 2022; unchanged through 2010"
        ),
        months_by_year_turning_62={
            year: min(
                BASE_FRA_MONTHS + 2 * max(0, year - FIRST_OPTION_YEAR),
                TARGET_FRA_MONTHS,
            )
            for year in range(FIRST_OPTION_YEAR, FINAL_YEAR_TURNING_62 + 1)
        },
    )


def _p2() -> FRASchedule:
    return FRASchedule(
        schedule_id="P2",
        rule="66 years + 2*(Y-2009) months from Y = 2010, capped at 68",
        months_by_year_turning_62={
            year: min(
                BASE_FRA_MONTHS + 2 * (year - LAST_UNCHANGED_YEAR),
                TARGET_FRA_MONTHS,
            )
            for year in range(FIRST_OPTION_YEAR, FINAL_YEAR_TURNING_62 + 1)
        },
    )


def _p3_increase(year: int) -> int:
    """``round(24 * (Y - 2009) / 13)`` in whole months, exactly.

    ``floor(24 k / 13 + 1/2) = (48 k + 13) // 26``; a tie would need
    ``48 k`` to be congruent to 13 modulo 26, which no integer ``k``
    satisfies (``48 k`` is even), so this is the nearest whole month.
    """

    k = int(year) - LAST_UNCHANGED_YEAR
    span = FINAL_YEAR_TURNING_62 - LAST_UNCHANGED_YEAR
    increase = TARGET_FRA_MONTHS - BASE_FRA_MONTHS
    numerator = 2 * increase * k + span
    if (2 * increase * k) % (2 * span) == span:
        raise AssertionError("P3 rounding tie")  # cannot occur (docstring)
    return numerator // (2 * span)


def _p3() -> FRASchedule:
    return FRASchedule(
        schedule_id="P3",
        rule=(
            "66 years + round(24*(Y-2009)/13) months for Y (year turning "
            "62) 2010-2021, rounded to the nearest whole month (no ties); "
            "68 from 2022"
        ),
        months_by_year_turning_62={
            year: BASE_FRA_MONTHS + _p3_increase(year)
            for year in range(FIRST_OPTION_YEAR, FINAL_YEAR_TURNING_62 + 1)
        },
    )


#: The three frozen readings of Table 1 (plan section 3).
SCHEDULES: dict[str, FRASchedule] = {
    schedule.schedule_id: schedule for schedule in (_p1(), _p2(), _p3())
}


def _step_list(values: Mapping[int, int]) -> list[tuple[int, int]]:
    """A birth-year step list (the ``fra_months_by_birth_year`` shape)."""

    steps: list[tuple[int, int]] = []
    for birth_year in sorted(values):
        months = int(values[birth_year])
        if not steps or steps[-1][1] != months:
            steps.append((int(birth_year), months))
    return steps


def reform_parameters(
    baseline: SSAParameters, schedule: FRASchedule
) -> SSAParameters:
    """``baseline`` with its FRA schedule replaced by the reform schedule.

    A parameter override (``dataclasses.replace``): every other field,
    including the early-reduction rates, the credit schedule and its cap,
    the survivor constants and the AWI, is the baseline's.  For each birth
    year ``b`` the reform FRA is the schedule's value for the year
    ``b + 62`` when the schedule sets it, else the baseline's.

    Guards (a violation raises ``ValueError``):

    * the reform equals the baseline for every cohort that turns 62 before
      2010, the option's first year (:data:`FIRST_OPTION_YEAR`);
    * the reform is at or above the baseline for every birth year;
    * the reform is 68 (816 months) for every birth year from 1960
      (turning 62 in 2022);
    * every reform FRA lies between 62 and 70.
    """

    if not isinstance(schedule, FRASchedule):
        raise TypeError("schedule must be an FRASchedule")
    first = min(year for year, _ in baseline.fra_months_by_birth_year)
    final_birth = FINAL_YEAR_TURNING_62 - WORKER_EARLY_RETIREMENT_AGE
    by_birth: dict[int, int] = {}
    for birth_year in range(first, final_birth + 1):
        override = schedule.months_for_birth_year(birth_year)
        by_birth[birth_year] = (
            baseline.fra_months(birth_year) if override is None else override
        )
    # Every later cohort: 68, unless the baseline is already higher (the
    # guard below refuses that case).
    by_birth[final_birth] = TARGET_FRA_MONTHS
    later_thresholds = [
        year
        for year, _ in baseline.fra_months_by_birth_year
        if year > final_birth
    ]
    for year in later_thresholds:
        by_birth[year] = TARGET_FRA_MONTHS
    reform = dataclasses.replace(
        baseline,
        fra_months_by_birth_year=_step_list(by_birth),
        pe_us_revision=(
            f"{baseline.pe_us_revision}+fra68_{schedule.schedule_id}_"
            f"{schedule.sha256()[:12]}"
        ),
    )
    _check_reform(baseline, reform, schedule)
    return reform


def _check_reform(
    baseline: SSAParameters, reform: SSAParameters, schedule: FRASchedule
) -> None:
    first_raised = None
    for birth_year in _GUARD_BIRTH_YEARS:
        base = baseline.fra_months(birth_year)
        new = reform.fra_months(birth_year)
        if new < base:
            raise ValueError(
                f"{schedule.schedule_id}: the reform FRA for birth year "
                f"{birth_year} ({new}) is below the baseline ({base})"
            )
        if not AGE_62_MONTHS <= new <= AGE_70_MONTHS:
            raise ValueError(
                f"{schedule.schedule_id}: FRA {new} for birth year "
                f"{birth_year} is outside 62-70"
            )
        if new > base and first_raised is None:
            first_raised = birth_year
        birth_turns_62 = birth_year + WORKER_EARLY_RETIREMENT_AGE
        if birth_turns_62 < FIRST_OPTION_YEAR and new != base:
            raise ValueError(
                f"{schedule.schedule_id}: the cohort turning 62 in "
                f"{birth_turns_62} precedes the option and must keep the "
                "baseline FRA"
            )
        if birth_turns_62 >= FINAL_YEAR_TURNING_62 and (
            new != TARGET_FRA_MONTHS
        ):
            raise ValueError(
                f"{schedule.schedule_id}: FRA for birth year {birth_year} "
                f"is {new}, not 68 (Table 1)"
            )
    if first_raised is None:
        raise ValueError(f"{schedule.schedule_id}: the reform changes nothing")


def parameters_fra_sha256(params: SSAParameters) -> str:
    """SHA-256 of the fields exercise 3 reads for the age factor.

    The FRA schedule, the early-reduction rates, the spousal rates, the
    credit schedule and cap, and the survivor constants: recorded for the
    baseline and each reform bundle in every run.
    """

    record = {
        "fra_months_by_birth_year": [
            [int(year), int(months)]
            for year, months in params.fra_months_by_birth_year
        ],
        "early_monthly_rates": list(params.early_monthly_rates),
        "early_first_bracket_months": params.early_first_bracket_months,
        "spousal_early_monthly_rates": list(
            params.spousal_early_monthly_rates
        ),
        "spousal_early_first_bracket_months": (
            params.spousal_early_first_bracket_months
        ),
        "delayed_credit_by_birth_year": [
            [int(year), float(rate)]
            for year, rate in params.delayed_credit_by_birth_year
        ],
        "max_delayed_months": params.max_delayed_months,
        "survivor_reduction_floor": params.survivor_reduction_floor,
        "survivor_reduction_period_months": (
            params.survivor_reduction_period_months
        ),
        "survivor_earliest_claim_age": params.survivor_earliest_claim_age,
        "rib_lim_pia_share": params.rib_lim_pia_share,
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def fra_increase_months(
    baseline: SSAParameters, reform: SSAParameters, birth_year: int
) -> int:
    """Reform FRA minus baseline FRA, in months, for a birth year."""

    return int(reform.fra_months(birth_year)) - int(
        baseline.fra_months(birth_year)
    )


def survivor_retirement_age_months(
    schedule: SSAParameters, birth_year: int
) -> int:
    """A widow(er)'s retirement age under 416(l)(2), in months.

    The worker schedule's value for ``birth_year - 2``: a widow(er) born
    in ``b`` attains early retirement age (60) in the year a worker born in
    ``b - 2`` attains it (62), and 416(l)(1) keys the retirement age to
    that year.  Under the statutory baseline this is 67 (804 months) for
    widow(er)s born in 1962 or later, the oracle's default span of 84
    months.
    """

    return int(schedule.fra_months(int(birth_year) - SURVIVOR_COHORT_OFFSET))


def survivor_parameters(
    params: SSAParameters,
    birth_year: int,
    *,
    schedule: SSAParameters | None = None,
) -> SSAParameters:
    """``params`` with the widow(er)'s reduction span exact for a cohort.

    The oracle spreads the 28.5 percent maximum widow(er) reduction
    linearly over ``survivor_reduction_period_months``, the months from age
    60 to the survivor's retirement age (its docstring: "Build a bundle
    with a different value").  This sets that span to
    :func:`survivor_retirement_age_months` on ``schedule`` (``params`` when
    omitted) minus 60 years.  Row F7 passes the baseline schedule for the
    reform scenario (survivors' retirement age unchanged).
    """

    source = params if schedule is None else schedule
    span = survivor_retirement_age_months(source, birth_year) - AGE_60_MONTHS
    if span <= 0:
        raise ValueError(
            f"the survivor retirement age for birth year {birth_year} is not "
            "after 60"
        )
    if span == params.survivor_reduction_period_months:
        return params
    return dataclasses.replace(params, survivor_reduction_period_months=span)


def worker_factor_ratio(
    claim_age_months: int,
    birth_year: int,
    baseline: SSAParameters,
    reform: SSAParameters,
) -> float:
    """Reform over baseline old-age benefit-to-PIA factor (402(q), (w)).

    Both factors come from the oracle's ``claiming.benefit_factor``.
    """

    base = claiming.benefit_factor(claim_age_months, birth_year, baseline)
    new = claiming.benefit_factor(claim_age_months, birth_year, reform)
    return new / base


def spouse_age_factor(
    entitlement_age_months: int, birth_year: int, params: SSAParameters
) -> float:
    """One minus the spouse's 402(q) reduction at an entitlement age.

    Months early are counted against the spouse's own FRA
    (``params.fra_months(birth_year)``), as the Track A spouse's excess
    does; spouses earn no delayed credit.
    """

    months_early = max(
        0, int(params.fra_months(birth_year)) - int(entitlement_age_months)
    )
    return 1.0 - benefits.spousal_early_reduction(months_early, params)


def spouse_excess_months_early(
    *,
    own_claim_month: int,
    worker_entitlement_year: int,
    birth_year: int,
    params: SSAParameters,
) -> int:
    """Months early of a spouse's excess (402(q)(1); E1 section 13).

    The excess starts at the later of the spouse's own claim and the
    worker's entitlement, so its reduction runs from
    ``s = max(m_s, 12 (y_w - b_s))`` months of age to the spouse's FRA:
    ``max(0, FRA(b_s) - s)``.  ``own_claim_month`` (``m_s``) is the
    spouse's own claim month: the exact moved claim month when C1 or C2
    moved the claim (the month the spouse's own factor reads), else 12
    times the claim year minus the birth year.  The worker's entitlement
    is annual, so it enters as a whole year (``y_w``) at the spouse's
    birthday month.  Without a moved claim this equals Track A's count,
    ``FRA(b_s) - 12 (max(own claim year, y_w) - b_s)``, exactly.
    """

    birth_year = int(birth_year)
    start = max(
        int(own_claim_month),
        _MONTHS * (int(worker_entitlement_year) - birth_year),
    )
    return max(0, int(params.fra_months(birth_year)) - start)


def conversion_claim_excess_months_early(
    *,
    conversion_claim_year: int,
    worker_entitlement_year: int,
    birth_year: int,
    baseline: SSAParameters,
    params: SSAParameters,
) -> int:
    """Months early of a spouse's excess on a conversion claim (E1 s. 11).

    A disabled worker converted at FRA claims the spouse's excess at the
    conversion (Track A's rule), and by Track A's convention draws none
    while still entitled to DI, so the excess never starts before the
    month of attaining retirement age.  42 USC 402(q)(1) reduces a wife's
    or husband's benefit only "if the first month for which an individual
    is entitled to" it "is a month before the month in which such
    individual attains retirement age" (``usc42_402.txt`` line 371), and
    the reduction period ends "with the last day of the month before the
    month in which such individual attains retirement age" (402(q)(6)(B),
    line 406).  On that convention the statute's count is 0 in every
    scenario.

    Track A counts from the whole conversion year instead (A4's July birth
    month): ``conversion_claim_year`` (``y_c``, Track A's own claim year of
    the converted worker) stands for the month ``12 (y_c - b)``, which is
    ``FRA(b) mod 12`` months before the FRA when that remainder is below
    6.  Exercise 3 keeps Track A's baseline count bit for bit and moves
    the whole baseline start by ``D = FRA'(b) - FRA(b)`` months in a
    reform scenario (``params``):

        ``max(0, FRA'(b) - (max(12 (y_c - b), 12 (y_w - b)) + D))``

    which equals the baseline count ``max(0, FRA(b) - max(12 (y_c - b),
    12 (y_w - b)))`` for every ``D``, so the reform-to-baseline factor
    ratio is 1, the statute's answer.  ``worker_entitlement_year``
    (``y_w``) is the worker's baseline entitlement year: a worker's claim
    that C1 or C2 moved enters at its year before the move, so the count
    is the baseline's under every claiming response.  Where the
    conversion starts the baseline excess this is the conversion claim
    moved by exactly ``D`` months, ``12 (y_c - b) + D``, the device of the
    moved claims of C1 and C2 (:func:`spouse_excess_months_early`).  Where
    the worker's later entitlement starts it, the baseline count is 0 and
    so is this one; moving the conversion claim alone would count up to
    ``FRA(b) mod 12`` months there (2 for spouses born 1955, 4 for 1956),
    a reduction the statute does not make.  With ``params`` the baseline
    bundle the result is Track A's count exactly.
    """

    birth_year = int(birth_year)
    increase = fra_increase_months(baseline, params, birth_year)
    start = (
        max(
            _MONTHS * (int(conversion_claim_year) - birth_year),
            _MONTHS * (int(worker_entitlement_year) - birth_year),
        )
        + increase
    )
    return max(0, int(params.fra_months(birth_year)) - start)


def opening_stock_factor_ratio(
    component: str,
    claim_age_months: int | None,
    birth_year: int,
    baseline: SSAParameters,
    reform: SSAParameters,
) -> float:
    """The factor ratio applied to an opening-stock amount (plan section 8).

    The observed opening-year amount is scaled by the reform-to-baseline
    ratio of the component's age factor for a retired-worker or spouse
    record claimed at 62 or later; every other record (disabled worker,
    survivor, a spouse entitled before 62, an unknown claim age) has ratio
    1.  The ratio is exactly 1 for a cohort whose FRA the schedule does not
    raise.
    """

    if claim_age_months is None or claim_age_months < AGE_62_MONTHS:
        return 1.0
    if component == "retired_worker":
        return worker_factor_ratio(
            claim_age_months, birth_year, baseline, reform
        )
    if component == "spouse":
        return spouse_age_factor(
            claim_age_months, birth_year, reform
        ) / spouse_age_factor(claim_age_months, birth_year, baseline)
    return 1.0
