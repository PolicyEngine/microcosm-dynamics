"""Track M policy definitions, registered rows, Max's rulings and choices.

Python rules (not Axiom).  Sources, all builder-cleared:

* **Table 5** of the Report, as transcribed in the cleared definitions
  extract ``EV/exercise4-definitions-cleared-20260924.md`` (SHA-256
  ``54279fd1…``), "Options simulated": the schedule of each minimum as a
  percentage of poverty by work year (a work year is a year with four
  covered quarters) and each option's solvency mechanism.  Ruling C1: the
  uniform-cut sizes are policy inputs used exactly as printed, never tuning
  targets, and builders derive no cost-equivalent cuts of their own.
* The blind plan ``EV/critical-path-minimum-benefit-20260924.md``
  (revision 2), section 7: the proposed fields G1-G23, the registered rows
  MS0-MS6 and the consolidated decision card (cos decision d219).
* The independent referee report
  ``EV/minimum-benefits-referee-20260924.md`` (required changes R1-R10),
  which the M1 specification's ``m1-draft-2`` applies.

``EV`` is ``~/microcosm-launch-evidence/dynasim-parity-20260909``.

Two kinds of choice are kept apart, as exercise 3's
``fra68_track.config`` does:

* **Max's rulings** (:data:`MAX_RULINGS`).  Max ruled cos decision d219 on
  2026-09-24 (ruled 21:44: "Accept all nine"), adopting every default of
  the card, and on 2026-09-25 ruled d279 (download the 2013-2022 Census
  threshold workbooks, plus any earlier year the build proves it needs)
  and d280 (PSID labor income treated as covered earnings, disclosed in
  the specification and every result).  Each ruled field defaults to its
  ruling; :func:`max_rulings` reports whether a configuration follows each
  one, and a registered run refuses a configuration that departs from any.
* **Frozen choices** (:func:`frozen_choices`): the rules the plan leaves to
  the builder or the specification, frozen in ``m1-draft-2`` on the
  referee's answers.  The merge that ratifies the specification (d219 item
  9) fixes them; no ruling of Max's names them.

:data:`REGISTERED_ROWS` holds the one-field changes of the registered rows.
The specification itself is not ratified: ``m1-draft-2`` awaits an
independent check of the referee's changes, and then the merge.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import asdict, dataclass, fields, replace
from typing import Any

__all__ = [
    "ACCEPTANCE_RULE",
    "CENSUS_THRESHOLD_DOWNLOAD",
    "CLAIM_CLASS",
    "COUNT_OWN_ONLY",
    "COUNT_OWN_OR_LINKED",
    "COVERED_LABOR_INCOME",
    "DEATH_FIRST_PIA_ON_RECORD",
    "DEATH_PIA_STATUTORY",
    "DECISION_RECORD",
    "DI_COVERAGE_END_BEFORE_ONSET",
    "DI_PIA_APPROXIMATE",
    "DI_PIA_STATUTORY",
    "DI_PRORATION_ELAPSED",
    "Decision",
    "ENTITLEMENT_EARLIEST_CONSISTENT",
    "GAP_YEARS_NEIGHBOR",
    "GAP_YEARS_ZERO",
    "GENEROUS",
    "HEADLINE_CELL",
    "HEADLINE_POLICY_YEAR",
    "MAX_RULINGS",
    "MINIMUM_ROUNDING_DIME",
    "MINIMUM_ROUNDING_NONE",
    "ODD_YEARS_NEXT_WAVE",
    "OLD_AGE_HISTORY_BEFORE_ENTITLEMENT",
    "ONSET_ENTITLEMENT_MINUS_1",
    "OPTIONS",
    "ORDER_CUT_AFTER_FLOOR",
    "ORDER_FLOOR_AFTER_CUT",
    "Option",
    "PIA_BENEFIT_IMPLIED",
    "PIA_HISTORY",
    "PRE_1978_SCALED_BY_AWI",
    "PRE_1978_STATUTE_50_PER_QUARTER",
    "PRORATED_YEARS_EXACT",
    "PRORATED_YEARS_FLOOR",
    "RATIFICATION_AND_REGISTRATION",
    "REGISTERED_ROWS",
    "REPORT_POLICY_YEAR",
    "RULES_MODULE_PLACEMENT",
    "SNAPSHOT_INCOME_YEAR",
    "SNAPSHOT_WAVE",
    "SPECIFICATION_ID",
    "STANDARD",
    "SURVIVOR_OWN_BENEFIT_AFTER_402Q",
    "Schedule",
    "TABLE6_OPTIONS",
    "TABLE6_ROWS",
    "TARGET_CELLS",
    "THRESHOLD_CENSUS_ONE_PERSON_65_PLUS",
    "THRESHOLD_YEAR_SECTION_4A",
    "TrackMPolicy",
    "WINDOW_AFTER",
    "WINDOW_IN_OR_AFTER",
    "d219_items",
    "decision_register",
    "fixed_decision_value",
    "frozen_choices",
    "max_rulings",
    "policy_for_row",
    "rulings_departures",
]

SPECIFICATION_ID = "urban2006_minimum_benefits_exercise4"
#: The consolidated decision card of the plan, registered with ``cos``.
DECISION_RECORD = "d219"

#: Table 6 prints its 2025 block for options 2-5 only (availability Y1).
TABLE6_OPTIONS: tuple[int, ...] = (2, 3, 4, 5)
#: Table 6's rows: All, with Men and Women nested under it.
TABLE6_ROWS: tuple[str, ...] = ("all", "men", "women")
#: Designated before any result (plan R2; d219 item 1, ruled 2026-09-24:
#: default accepted).
HEADLINE_CELL: tuple[int, str] = (2, "all")

#: The snapshot (plan G2; d219 item 2): the 2023 PSID wave reports income
#: year 2022.
SNAPSHOT_WAVE = 2023
SNAPSHOT_INCOME_YEAR = 2022
#: Plan G2 headline: every policy date moved back three years, so the 2022
#: snapshot exposes 19 entitlement cohorts as DYNASIM's 2025 does (d219
#: item 3, ruled 2026-09-24: default accepted).
HEADLINE_POLICY_YEAR = 2004
#: The Report's own dating (Table 5 notes: all options take effect in
#: 2007); registered row MS1.
REPORT_POLICY_YEAR = 2007


@dataclass(frozen=True)
class Schedule:
    """A minimum schedule: a share of the threshold by work years.

    ``points`` are ``(work years, share)`` pairs in increasing years.  The
    share is zero below the first point's years (the floor), linear between
    points, and held at the last point's share beyond its years (the cap).
    Work years may be fractional (a DI worker's prorated count, plan G12);
    the schedule does not round them.
    """

    name: str
    points: tuple[tuple[int, float], ...]

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError("a schedule needs at least one point")
        years = [year for year, _ in self.points]
        shares = [share for _, share in self.points]
        if years != sorted(set(years)):
            raise ValueError("schedule years must be strictly increasing")
        if shares != sorted(shares) or shares[0] <= 0:
            raise ValueError("schedule shares must be positive, nondecreasing")

    @property
    def floor_years(self) -> int:
        """Work years below which the schedule pays nothing."""

        return self.points[0][0]

    @property
    def cap_years(self) -> int:
        """Work years beyond which the share no longer rises."""

        return self.points[-1][0]

    def share(self, work_years: float) -> float:
        """The share of the threshold at ``work_years`` (0 below the floor)."""

        years = float(work_years)
        if not math.isfinite(years):
            raise ValueError(f"work years must be finite, not {work_years!r}")
        if years < self.floor_years:
            return 0.0
        years = min(years, float(self.cap_years))
        for (y0, s0), (y1, s1) in itertools.pairwise(self.points):
            if years <= y1:
                return s0 + (s1 - s0) * (years - y0) / (y1 - y0)
        return self.points[-1][1]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "points": [[year, share] for year, share in self.points],
        }


#: Table 5, options 2 and 3: "55% at 10, increment by 1.5% to reach 100% at
#: 40" (percent of poverty by work year).
STANDARD = Schedule("standard", ((10, 0.55), (40, 1.00)))
#: Table 5, options 4 and 5: "80% at 10, increment by 2.0% to reach 100% at
#: 20, increment by 1.0% to reach 120% at 40".
GENEROUS = Schedule("generous", ((10, 0.80), (20, 1.00), (40, 1.20)))


@dataclass(frozen=True)
class Option:
    """One Table 5 option that Track M implements.

    ``indexing`` is ``"price"`` (the threshold of the year, which moves
    with prices) or ``"wage"`` (the policy year's threshold carried forward
    by the average wage index) for a minimum, and ``None`` for option 1.
    ``uniform_cut`` is the across-the-board cut for new entitlees, as
    printed (ruling C1).
    """

    number: int
    label: str
    schedule: Schedule | None
    indexing: str | None
    uniform_cut: float

    @property
    def has_minimum(self) -> bool:
        return self.schedule is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "label": self.label,
            "schedule": None if self.schedule is None else self.schedule.name,
            "indexing": self.indexing,
            "uniform_cut": self.uniform_cut,
        }


#: Table 5 options 1-5, labels and parameters as printed.  Options 6-10 are
#: not in Table 6 and are not implemented (plan section 2: Track P only).
OPTIONS: dict[int, Option] = {
    1: Option(1, "Reduced current law", None, None, 0.1245),
    2: Option(
        2, "Standard price-indexed minimum benefit", STANDARD, "price", 0.1281
    ),
    3: Option(
        3, "Standard wage-indexed minimum benefit", STANDARD, "wage", 0.1427
    ),
    4: Option(
        4, "Generous price-indexed minimum benefit", GENEROUS, "price", 0.1364
    ),
    5: Option(
        5, "Generous wage-indexed minimum benefit", GENEROUS, "wage", 0.1862
    ),
}

# ---- choice values ---------------------------------------------------------
#: G10 primary: the minimum is a floor after the cut, max((1 - c)P, M).
ORDER_FLOOR_AFTER_CUT = "floor_after_cut"
#: MS2: the cut applies after the floor, max(P, M)(1 - c).
ORDER_CUT_AFTER_FLOOR = "cut_after_floor"
#: G4 primary: the PIA's window year (section 4a) is in or after the policy
#: year.
WINDOW_IN_OR_AFTER = "in_or_after_policy_year"
#: MS4: after the policy year (the text's "entitled after" wording, D9).
WINDOW_AFTER = "after_policy_year"
#: G23 primary: paid a benefit computed from a PIA that rests on the
#: minimum, the person's own or a linked worker's.
COUNT_OWN_OR_LINKED = "own_or_linked_worker_pia"
#: MS3: the person's own worker PIA only.
COUNT_OWN_ONLY = "own_worker_pia_only"
#: G5 primary: the oracle AIME and PIA from the realized history.
PIA_HISTORY = "history_oracle"
#: MS5: the PIA implied by the observed benefit (inputs in section 6).
PIA_BENEFIT_IMPLIED = "benefit_implied"
#: G5 for DI, frozen by referee R5: the statutory DI computation years
#: (42 USC 415(b)(2)(A)(ii)) through the oracle.
DI_PIA_STATUTORY = "statutory_computation_years"
#: MS6: Track A's disclosed approximation (the 35-year divisor).
DI_PIA_APPROXIMATE = "approximate_pia"
#: Frozen by referee R5: a worker who died before any own entitlement gets
#: the statutory death computation (415(b)(2)(A)(i): elapsed years less 5).
DEATH_PIA_STATUTORY = "statutory_death_computation"
#: G12: Y* = Y * 40 / D, D the elapsed years from age 22 to onset.
DI_PRORATION_ELAPSED = "elapsed_years_from_age_22"
#: Frozen (referee Q3): Y* is not rounded (the plan's INVENTED case D).
PRORATED_YEARS_EXACT = "exact"
PRORATED_YEARS_FLOOR = "floor"
#: G8: the Census weighted-average threshold for one person aged 65+.
THRESHOLD_CENSUS_ONE_PERSON_65_PLUS = (
    "census_weighted_average_one_person_65_plus"
)
#: G8 as section 4a fixes it (referee R3): the year of attaining 62 for an
#: old-age record, the onset year for a disability-origin record, and the
#: earlier of the death year and the year of attaining 62 for a worker who
#: died before any own entitlement.
THRESHOLD_YEAR_SECTION_4A = (
    "attaining_62_or_di_onset_or_earlier_of_death_and_attaining_62"
)
#: d280 (ruled 2026-09-25): PSID labor income is treated as covered
#: earnings (the PSID does not observe coverage), disclosed in the
#: specification and every result.
COVERED_LABOR_INCOME = "psid_labor_income_treated_as_covered"
#: Frozen by referee R6: before 1978, 42 USC 413(a)(2)(A)(i) and 20 CFR
#: 404.141(b) credit a quarter of coverage for $50 of wages paid in it;
#: with annual amounts and wages taken as spread over the year, a year
#: counts at 4 x $50 = $200.
PRE_1978_STATUTE_50_PER_QUARTER = "statute_413_a_50_per_quarter"
#: The plan's G6 convention (the 1978 amount scaled back by the average
#: wage index).  It has no statutory basis and is not registered (referee
#: R6); it stays selectable only for the Table 2 formula check that shows
#: the difference (section 17, finding 3).
PRE_1978_SCALED_BY_AWI = "qc_1978_scaled_back_by_awi"
#: Frozen (referee R7): an odd year 1997-2021 still unobserved after the
#: next-wave items takes the immediate-neighbor law of ``estimates.career``.
GAP_YEARS_NEIGHBOR = "immediate_neighbor_mean"
#: G6 read literally (a gap year counts as zero); not registered.
GAP_YEARS_ZERO = "zero"
#: Frozen (referee R7): the odd years 2001-2021 come from the next wave's
#: year-before-last labor income of the reference person and the spouse,
#: before any imputation.
ODD_YEARS_NEXT_WAVE = "next_wave_reference_person_and_spouse"
#: Frozen (referee R3): an old-age PIA's history ends with the year before
#: the first year of the worker's own entitlement (42 USC
#: 415(b)(2)(B)(ii)(I)).
OLD_AGE_HISTORY_BEFORE_ENTITLEMENT = "year_before_first_entitlement"
#: Frozen (referee R3): a disability-origin record's Y and PIA history end
#: with the year before onset (413(a)(2)(B)(i); G12).
DI_COVERAGE_END_BEFORE_ONSET = "year_before_onset"
#: Frozen (referee R3): the window year of a worker who died before any
#: own entitlement is the first year a person in the universe is entitled
#: to a benefit on the record.
DEATH_FIRST_PIA_ON_RECORD = "first_entitlement_on_record"
#: Frozen (referee R4, section 4b rule 2): the entitlement year is the
#: earliest year consistent with the observed receipt history.
ENTITLEMENT_EARLIEST_CONSISTENT = "earliest_consistent"
#: Frozen (referee R4, section 4b rule 4): a disability-origin record's
#: onset year is its entitlement year less one (builder default).
ONSET_ENTITLEMENT_MINUS_1 = "entitlement_year_minus_1"
#: Frozen (referee R4, section 4b rule 5; 42 USC 402(k)(3)(A)): a
#: survivor's own amount is the own benefit after the 402(q) reduction.
SURVIVOR_OWN_BENEFIT_AFTER_402Q = "own_benefit_after_402q"
#: Frozen (referee Q7): the monthly minimum is compared unrounded.
MINIMUM_ROUNDING_NONE = "none"
#: Not registered: floor the monthly minimum to a dime, as 415(g) rounds a
#: PIA (the oracle's ``ss.benefits.pia`` convention).
MINIMUM_ROUNDING_DIME = "dime_floor"

_CHOICES: dict[str, tuple[Any, ...]] = {
    "policy_year": (HEADLINE_POLICY_YEAR, REPORT_POLICY_YEAR),
    "window_rule": (WINDOW_IN_OR_AFTER, WINDOW_AFTER),
    "order": (ORDER_FLOOR_AFTER_CUT, ORDER_CUT_AFTER_FLOOR),
    "counting_rule": (COUNT_OWN_OR_LINKED, COUNT_OWN_ONLY),
    "pia_rule": (PIA_HISTORY, PIA_BENEFIT_IMPLIED),
    "di_pia_rule": (DI_PIA_STATUTORY, DI_PIA_APPROXIMATE),
    "death_pia_rule": (DEATH_PIA_STATUTORY,),
    "di_proration": (DI_PRORATION_ELAPSED,),
    "di_prorated_years_rounding": (
        PRORATED_YEARS_EXACT,
        PRORATED_YEARS_FLOOR,
    ),
    "threshold_rule": (THRESHOLD_CENSUS_ONE_PERSON_65_PLUS,),
    "threshold_year_rule": (THRESHOLD_YEAR_SECTION_4A,),
    "covered_earnings_rule": (COVERED_LABOR_INCOME,),
    "pre_1978_coverage_rule": (
        PRE_1978_STATUTE_50_PER_QUARTER,
        PRE_1978_SCALED_BY_AWI,
    ),
    "gap_year_rule": (GAP_YEARS_NEIGHBOR, GAP_YEARS_ZERO),
    "odd_year_source": (ODD_YEARS_NEXT_WAVE,),
    "old_age_history_end": (OLD_AGE_HISTORY_BEFORE_ENTITLEMENT,),
    "di_coverage_end": (DI_COVERAGE_END_BEFORE_ONSET,),
    "death_first_pia_year": (DEATH_FIRST_PIA_ON_RECORD,),
    "entitlement_year_rule": (ENTITLEMENT_EARLIEST_CONSISTENT,),
    "onset_year_rule": (ONSET_ENTITLEMENT_MINUS_1,),
    "survivor_own_amount": (SURVIVOR_OWN_BENEFIT_AFTER_402Q,),
    "minimum_rounding": (MINIMUM_ROUNDING_NONE, MINIMUM_ROUNDING_DIME),
    "couples_cap": ("none",),
    "unlinked_auxiliary": ("not_receiving_counted_separately",),
}


@dataclass(frozen=True)
class TrackMPolicy:
    """Every Track M rule choice; each default is ruled or frozen.

    Fields and their basis (plan revision 2, section 7; the M1
    specification ``m1-draft-2``):

    * ``policy_year`` (G2; d219 item 3, ruled 2004): 2007 in MS1.  The
      wage-indexed minimum's base year moves with it (G9).
    * ``window_rule`` (G4, frozen): the window year in or after the policy
      year; MS4 after it.
    * ``order`` (G10; d219 item 5, ruled): the minimum is a floor after the
      cut; MS2 applies the cut after the floor.
    * ``counting_rule`` (G23; d219 item 7, ruled): own or linked worker's
      PIA; MS3 own only.
    * ``pia_rule`` (G5, frozen; MS5 benefit-implied), ``di_pia_rule`` (G5,
      frozen by R5: the statutory DI computation; MS6 Track A's
      approximation) and ``death_pia_rule`` (frozen by R5: the statutory
      death computation, the only value).
    * ``di_proration`` (G12; d219 item 6, ruled) with
      ``di_proration_start_age`` (22), ``di_proration_cap_years`` (40, part
      of the ruling) and ``di_prorated_years_rounding`` (frozen: exact).
    * ``threshold_rule`` and ``threshold_year_rule`` (G8, section 4a),
      ``wage_index_lag_years`` (G9, frozen: 2).
    * ``covered_earnings_rule`` (d280, ruled 2026-09-25),
      ``pre_1978_coverage_rule`` (frozen by R6: the statute),
      ``gap_year_rule`` and ``odd_year_source`` (frozen by R7),
      ``unobserved_window_start_age`` (frozen: 22) and
      ``quarters_per_work_year`` (Table 5's column head: "work year = 4
      CQ").
    * ``old_age_history_end``, ``di_coverage_end`` and
      ``death_first_pia_year`` (frozen by R3: section 4a);
      ``entitlement_year_rule``, ``onset_year_rule`` and
      ``survivor_own_amount`` (frozen by R4: section 4b).
    * ``minimum_rounding`` (frozen: none), ``couples_cap`` and
      ``unlinked_auxiliary`` (G13, frozen).
    """

    policy_year: int = HEADLINE_POLICY_YEAR
    window_rule: str = WINDOW_IN_OR_AFTER
    order: str = ORDER_FLOOR_AFTER_CUT
    counting_rule: str = COUNT_OWN_OR_LINKED
    pia_rule: str = PIA_HISTORY
    di_pia_rule: str = DI_PIA_STATUTORY
    death_pia_rule: str = DEATH_PIA_STATUTORY
    di_proration: str = DI_PRORATION_ELAPSED
    di_proration_start_age: int = 22
    di_proration_cap_years: int = 40
    di_prorated_years_rounding: str = PRORATED_YEARS_EXACT
    threshold_rule: str = THRESHOLD_CENSUS_ONE_PERSON_65_PLUS
    threshold_year_rule: str = THRESHOLD_YEAR_SECTION_4A
    wage_index_lag_years: int = 2
    covered_earnings_rule: str = COVERED_LABOR_INCOME
    pre_1978_coverage_rule: str = PRE_1978_STATUTE_50_PER_QUARTER
    gap_year_rule: str = GAP_YEARS_NEIGHBOR
    odd_year_source: str = ODD_YEARS_NEXT_WAVE
    old_age_history_end: str = OLD_AGE_HISTORY_BEFORE_ENTITLEMENT
    di_coverage_end: str = DI_COVERAGE_END_BEFORE_ONSET
    death_first_pia_year: str = DEATH_FIRST_PIA_ON_RECORD
    entitlement_year_rule: str = ENTITLEMENT_EARLIEST_CONSISTENT
    onset_year_rule: str = ONSET_ENTITLEMENT_MINUS_1
    survivor_own_amount: str = SURVIVOR_OWN_BENEFIT_AFTER_402Q
    quarters_per_work_year: int = 4
    unobserved_window_start_age: int = 22
    minimum_rounding: str = MINIMUM_ROUNDING_NONE
    couples_cap: str = "none"
    unlinked_auxiliary: str = "not_receiving_counted_separately"

    def __post_init__(self) -> None:
        for name, allowed in _CHOICES.items():
            value = getattr(self, name)
            if value not in allowed:
                raise ValueError(
                    f"{name} must be one of {allowed}, not {value!r}"
                )
        for name in (
            "policy_year",
            "di_proration_start_age",
            "di_proration_cap_years",
            "wage_index_lag_years",
            "quarters_per_work_year",
            "unobserved_window_start_age",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer, not {value!r}")
        if self.di_proration_cap_years != 40:
            raise ValueError(
                "di_proration_cap_years must be 40: the schedules end at "
                "40 work years (Table 5) and the plan caps Y* there (G12)"
            )
        if self.quarters_per_work_year != 4:
            raise ValueError(
                "quarters_per_work_year must be 4 (Table 5: work year = 4 CQ)"
            )
        if not 0 < self.wage_index_lag_years <= 5:
            raise ValueError("wage_index_lag_years must be 1-5")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


#: Each registered row changes one field from MS0 (plan section 7).  Every
#: row reports all 12 cells; MS0 is the scored row, designated in advance.
REGISTERED_ROWS: dict[str, dict[str, Any]] = {
    "MS0": {},
    "MS1": {"policy_year": REPORT_POLICY_YEAR},
    "MS2": {"order": ORDER_CUT_AFTER_FLOOR},
    "MS3": {"counting_rule": COUNT_OWN_ONLY},
    "MS4": {"window_rule": WINDOW_AFTER},
    "MS5": {"pia_rule": PIA_BENEFIT_IMPLIED},
    "MS6": {"di_pia_rule": DI_PIA_APPROXIMATE},
}


def policy_for_row(row: str, base: TrackMPolicy | None = None) -> TrackMPolicy:
    """The policy of registered row ``row``: ``base`` with its one change."""

    if row not in REGISTERED_ROWS:
        raise ValueError(f"row must be one of {sorted(REGISTERED_ROWS)}")
    return replace(base or TrackMPolicy(), **REGISTERED_ROWS[row])


# ---------------------------------------------------------------------------
# Max's rulings
# ---------------------------------------------------------------------------
#: Process decisions that are not :class:`TrackMPolicy` fields; their value
#: is fixed in code and only a code change can alter it.
TARGET_CELLS = "table6_2025_options_2_to_5_by_all_men_women_headline_2_all"
CLAIM_CLASS = "track_m_static_psid_snapshot_income_year_2022"
RULES_MODULE_PLACEMENT = (
    "new_python_module_outside_ss_calling_oracle_unchanged"
)
ACCEPTANCE_RULE = None
RATIFICATION_AND_REGISTRATION = (
    "ratify_by_merge_then_issue_42_registration_then_one_shot"
)
CENSUS_THRESHOLD_DOWNLOAD = (
    "thresh13_to_thresh22_and_any_earlier_year_the_build_proves_it_needs"
)
_FIXED_DECISION_VALUES: dict[str, Any] = {
    "target_cells": TARGET_CELLS,
    "claim_class": CLAIM_CLASS,
    "rules_module_placement": RULES_MODULE_PLACEMENT,
    "acceptance_rule": ACCEPTANCE_RULE,
    "ratification_and_registration": RATIFICATION_AND_REGISTRATION,
    "census_threshold_download": CENSUS_THRESHOLD_DOWNLOAD,
}

#: The nine items of cos decision d219 as filed (the cos record's text,
#: split at its item numbers), with the field or process each governs.
#: Item 4's text names the module placement only; the covered-earnings
#: convention the plan's card also placed there is ruled separately, in
#: d280 (2026-09-25).
_D219: dict[int, tuple[str, str]] = {
    1: (
        "target_cells",
        "the report prints no 2025 poverty effect (poverty only for 2050, "
        "Table 9), so score first on Table 6's 12 printed 2025 cells "
        "(share of beneficiaries 62+ receiving a minimum; options 2-5 by "
        "All/Men/Women; headline option 2, All), and hold poverty for a "
        "projected track scored against 2050",
    ),
    2: (
        "claim_class",
        "measure it as 'Track M', a static PSID snapshot for income year "
        "2022, labelled not a projection, not 2025 and not Axiom",
    ),
    3: (
        "policy_year",
        "move every policy date back three years in the headline so the "
        "snapshot spans 19 entitlement years like DYNASIM's 2025, with the "
        "report's own 2007 dating as a registered row",
    ),
    4: (
        "rules_module_placement",
        "years-of-coverage counting and the minimum rules in a new Python "
        "module outside ss/, calling the oracle unchanged (the "
        "covered-earnings convention is ruled separately: cos d280, "
        "2026-09-25)",
    ),
    5: (
        "order",
        "minimum applied as a floor after the uniform cut, reverse order "
        "registered",
    ),
    6: (
        "di_proration",
        "DI proration years x 40 / years elapsed from 22 to onset, capped "
        "at 40",
    ),
    7: (
        "counting_rule",
        "count as receiving the minimum anyone paid from a PIA resting on "
        "it, own-PIA-only registered",
    ),
    8: ("acceptance_rule", "no acceptance threshold"),
    9: (
        "ratification_and_registration",
        "ratify by merge, then the #42 registration and one-shot run",
    ),
}
_D219_RULING = (
    "Accept all nine (Max in chat 2026-09-24): score Table 6 2025 share "
    "first via Track M (PSID 2022 snapshot, policy dates shifted 3 years, "
    "literal 2007 dating registered); poverty later vs 2050; ratify by "
    "merge then #42 registration and one-shot."
)
_D219_RULED_ON = "2026-09-24"
_D27X_RULED_ON = "2026-09-25"
_D219_VALUES: dict[str, Any] = {
    "target_cells": TARGET_CELLS,
    "claim_class": CLAIM_CLASS,
    "policy_year": HEADLINE_POLICY_YEAR,
    "rules_module_placement": RULES_MODULE_PLACEMENT,
    "order": ORDER_FLOOR_AFTER_CUT,
    "di_proration": DI_PRORATION_ELAPSED,
    "counting_rule": COUNT_OWN_OR_LINKED,
    "acceptance_rule": ACCEPTANCE_RULE,
    "ratification_and_registration": RATIFICATION_AND_REGISTRATION,
}
#: Registered rows that keep an alternative the ruling did not choose.
_D219_REGISTERED_ROWS = {
    "policy_year": "MS1",
    "order": "MS2",
    "counting_rule": "MS3",
}


def _d219_entry(item: int) -> dict[str, Any]:
    field_name, as_filed = _D219[item]
    entry: dict[str, Any] = {
        "ruling": _D219_VALUES[field_name],
        "decision_record": DECISION_RECORD,
        "item": item,
        "ruled_on": _D219_RULED_ON,
        "as_filed": as_filed,
    }
    if field_name in _D219_REGISTERED_ROWS:
        entry["alternative_registered_as"] = _D219_REGISTERED_ROWS[field_name]
    return entry


#: Every field Max ruled on, keyed by field, as the M1 specification's
#: section 19 block records it under ``decisions``.  ``as_filed`` is the
#: decision text as filed in cos; the rulings are the cos records' (d219:
#: "Accept all nine", 2026-09-24 21:44; d279 and d280: 2026-09-25 06:24).
MAX_RULINGS: dict[str, dict[str, Any]] = {
    **{_D219[item][0]: _d219_entry(item) for item in sorted(_D219)},
    "covered_earnings_rule": {
        "ruling": COVERED_LABOR_INCOME,
        "decision_record": "d280",
        "item": None,
        "ruled_on": _D27X_RULED_ON,
        "as_filed": (
            "treat PSID labor income as covered earnings (PSID does not "
            "observe coverage), as exercises 1 and 3 and Track C do"
        ),
        "ruling_text": (
            "Accept (Max in chat 2026-09-25): same shared assumption, "
            "disclosed in the spec and every result"
        ),
        "disclosure": "specification_and_every_result",
    },
    "census_threshold_download": {
        "ruling": CENSUS_THRESHOLD_DOWNLOAD,
        "decision_record": "d279",
        "item": None,
        "ruled_on": _D27X_RULED_ON,
        "as_filed": (
            "download Census historical poverty-threshold workbooks "
            "thresh13-thresh22 (plus any earlier year the build proves it "
            "needs) from www2.census.gov"
        ),
        "ruling_text": (
            "Yes (Max in chat 2026-09-25): download thresh13-thresh22 and "
            "any earlier year the build proves it needs; capture, hash and "
            "pin like the 2003-2012 capture"
        ),
        "note": (
            "Max downloaded thresh13-thresh22; with thresh03-thresh12 "
            "(d194) they are captured as 2003-2022. No earlier year is "
            "captured: whether one is needed is M4's earliest-threshold-"
            "year count (M1 specification, section 7)"
        ),
    },
}
_RULED_BY = "Max"


def d219_items() -> dict[int, tuple[str, str]]:
    """The nine d219 items: ``{item: (field or process, text as filed)}``."""

    return dict(_D219)


def fixed_decision_value(name: str) -> Any:
    """The code's value of a ruled process decision (not a policy field)."""

    if name not in _FIXED_DECISION_VALUES:
        raise KeyError(f"{name!r} is not a fixed process decision")
    return _FIXED_DECISION_VALUES[name]


def _configured(policy: TrackMPolicy, name: str) -> Any:
    if hasattr(policy, name):
        return getattr(policy, name)
    return fixed_decision_value(name)


def max_rulings(policy: TrackMPolicy | None = None) -> list[dict[str, Any]]:
    """Max's rulings, each with the configured value and whether it follows.

    None is pending.  A configuration may depart from a ruling for an
    invented-data sensitivity (a registered row's one-field change), and
    the entry then says so; a registered run refuses it.
    """

    policy = policy or TrackMPolicy()
    out = []
    for name, ruling in MAX_RULINGS.items():
        value = _configured(policy, name)
        out.append(
            {
                "field": name,
                "value": value,
                **ruling,
                "ruled_by": _RULED_BY,
                "follows_ruling": value == ruling["ruling"],
            }
        )
    return out


def rulings_departures(policy: TrackMPolicy) -> list[str]:
    """The ruled fields whose configured value departs from the ruling."""

    return [
        item["field"]
        for item in max_rulings(policy)
        if not item["follows_ruling"]
    ]


@dataclass(frozen=True)
class Decision:
    """One Track M choice: its value, alternatives, basis and who fixed it.

    ``decided_by`` names Max's decision record for a ruled choice, or the
    specification freeze for the others.  ``card_item`` is the d219 item
    that covers it, or ``None``.
    """

    field: str
    value: Any
    alternatives: tuple[Any, ...]
    basis: str
    decided_by: str
    card_item: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "alternatives": list(self.alternatives),
            "basis": self.basis,
            "decided_by": self.decided_by,
            "card_item": self.card_item,
        }


_FROZEN = (
    "frozen in m1-draft-2 on the referee's answers; fixed by the merge "
    "that ratifies the M1 specification (d219 item 9)"
)


def frozen_choices() -> tuple[Decision, ...]:
    """The choices no ruling of Max's names, frozen in ``m1-draft-2``."""

    policy = TrackMPolicy()
    return tuple(
        Decision(
            name, getattr(policy, name), alternatives, basis, _FROZEN, None
        )
        for name, alternatives, basis in (
            (
                "window_rule",
                (WINDOW_AFTER,),
                "plan G4 (in or after Y0); MS4 is the 'entitled after' "
                "wording; the window year is section 4a's",
            ),
            ("pia_rule", (PIA_BENEFIT_IMPLIED,), "plan G5; MS5 (section 6)"),
            (
                "di_pia_rule",
                (DI_PIA_APPROXIMATE,),
                "referee R5: the statutory DI computation "
                "(415(b)(2)(A)(ii)) is primary; Track A's approximation, "
                "whose docstring says its 35-year divisor understates short "
                "careers, is MS6",
            ),
            (
                "death_pia_rule",
                (),
                "referee R5 and Q5: the statutory death computation "
                "(415(b)(2)(A)(i), elapsed years less 5)",
            ),
            (
                "di_proration_start_age",
                (),
                "plan G12; 415(b)(2)(B)(iii) counts elapsed years after the "
                "year of attaining 21 (referee Q9)",
            ),
            (
                "di_prorated_years_rounding",
                (PRORATED_YEARS_FLOOR,),
                "referee Q3: the plan's INVENTED case D applies the "
                "schedule to an unrounded Y* (27.27 years); not registered",
            ),
            (
                "threshold_rule",
                (),
                "plan G8: fn. 25 prints Census thresholds for the aged; one "
                "person, the weighted average and the 65-and-over row are "
                "the plan's reading (the option 6 passage's 65+ wording)",
            ),
            (
                "threshold_year_rule",
                (),
                "plan G8 as section 4a fixes it (referee R3 and Q2)",
            ),
            (
                "wage_index_lag_years",
                (),
                "plan G9 builder default (as the bend points use the second "
                "year before)",
            ),
            (
                "pre_1978_coverage_rule",
                (),
                "referee R6: 42 USC 413(a)(2)(A)(i) and 20 CFR 404.141(b) "
                "credit a quarter for $50 of wages paid in it; the plan's "
                "convention has no statutory basis and is not registered. "
                "Table 2's row-3 ratios agree with the statute, a unit-test "
                "finding under ruling C5 (section 17, finding 3), not the "
                "basis of the rule",
            ),
            (
                "gap_year_rule",
                (),
                "referee R7 and Q1: an odd year 1997-2021 still unobserved "
                "after the next-wave items takes the immediate-neighbor law "
                "of estimates.career; 'zero' is not registered",
            ),
            (
                "odd_year_source",
                (),
                "referee R7: the next wave's year-before-last labor income "
                "of the reference person and spouse, before any imputation",
            ),
            (
                "old_age_history_end",
                (),
                "referee R3: 42 USC 415(b)(2)(B)(ii)(I) ends an old-age "
                "PIA's computation base years before the year of first "
                "entitlement",
            ),
            (
                "di_coverage_end",
                (),
                "referee R3 and Q4: 413(a)(2)(B)(i); G12's D and the DI "
                "PIA's history end at onset less one",
            ),
            (
                "death_first_pia_year",
                (),
                "referee R3: a worker who died before any own entitlement "
                "has no entitlement year of their own",
            ),
            (
                "entitlement_year_rule",
                (),
                "referee R4 (section 4b rule 2)",
            ),
            (
                "onset_year_rule",
                (),
                "referee R4 (section 4b rule 4), builder default",
            ),
            (
                "survivor_own_amount",
                (),
                "referee R4 and Q8: 42 USC 402(k)(3)(A) reduces the other "
                "benefit by the own benefit after the 402(q) reduction",
            ),
            (
                "unobserved_window_start_age",
                (),
                "builder default: 22 matches G12's start",
            ),
            (
                "couples_cap",
                (),
                "plan G13: no cap on couples' minimum-based benefits (D7 is "
                "an inference that the simulated minimums had none)",
            ),
            (
                "unlinked_auxiliary",
                (),
                "plan G13: an auxiliary with no linked worker record cannot "
                "be flagged; counted as not receiving and reported "
                "separately",
            ),
            (
                "minimum_rounding",
                (MINIMUM_ROUNDING_DIME,),
                "referee Q7: the Report prints no rounding of the minimum; "
                "the comparison M > (1 - c)P rounds neither side",
            ),
        )
    )


def decision_register() -> tuple[Decision, ...]:
    """Every Track M choice: Max's rulings, then the frozen choices."""

    policy = TrackMPolicy()
    ruled = tuple(
        Decision(
            name,
            _configured(policy, name),
            (),
            entry["as_filed"],
            f"Max, cos decision {entry['decision_record']}"
            + (
                f" item {entry['item']} (ruled {entry['ruled_on']}: default "
                "accepted)"
                if entry["decision_record"] == DECISION_RECORD
                else f" (ruled {entry['ruled_on']})"
            ),
            entry["item"] if entry["decision_record"] == "d219" else None,
        )
        for name, entry in MAX_RULINGS.items()
    )
    return (*ruled, *frozen_choices())


def _check_rows() -> None:
    names = {f.name for f in fields(TrackMPolicy)}
    for row, change in REGISTERED_ROWS.items():
        if len(change) > 1 or not set(change) <= names:
            raise AssertionError(f"row {row} is not a one-field change")
        policy_for_row(row)
    for name, entry in MAX_RULINGS.items():
        if _configured(TrackMPolicy(), name) != entry["ruling"]:
            raise AssertionError(f"{name} does not default to Max's ruling")


_check_rows()
