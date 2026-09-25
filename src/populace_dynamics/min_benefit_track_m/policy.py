"""Track M policy definitions, registered rows and open choices.

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
  MS0-MS6 and the consolidated decision card (cos decision d219, open).

``EV`` is ``~/microcosm-launch-evidence/dynasim-parity-20260909``.

Every choice that awaits Max (d219 items 1-9) or the specification freeze
is a field of :class:`TrackMPolicy` whose default is the plan's
recommendation; :func:`pending_decisions` lists each with its basis and
who must settle it.  :data:`REGISTERED_ROWS` holds the one-field changes of
the registered rows.  Nothing here is ratified.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import asdict, dataclass, fields, replace
from typing import Any

__all__ = [
    "COUNT_OWN_ONLY",
    "COUNT_OWN_OR_LINKED",
    "COVERED_LABOR_INCOME",
    "DECISION_RECORD",
    "DI_PIA_APPROXIMATE",
    "DI_PIA_STATUTORY",
    "DI_PRORATION_ELAPSED",
    "GAP_YEARS_NEIGHBOR",
    "GAP_YEARS_ZERO",
    "GENEROUS",
    "HEADLINE_CELL",
    "HEADLINE_POLICY_YEAR",
    "MINIMUM_ROUNDING_DIME",
    "MINIMUM_ROUNDING_NONE",
    "OPTIONS",
    "ORDER_CUT_AFTER_FLOOR",
    "ORDER_FLOOR_AFTER_CUT",
    "Option",
    "PendingDecision",
    "PIA_BENEFIT_IMPLIED",
    "PIA_HISTORY",
    "PRE_1978_SCALED_BY_AWI",
    "PRORATED_YEARS_EXACT",
    "PRORATED_YEARS_FLOOR",
    "REGISTERED_ROWS",
    "REPORT_POLICY_YEAR",
    "SNAPSHOT_INCOME_YEAR",
    "SNAPSHOT_WAVE",
    "SPECIFICATION_ID",
    "STANDARD",
    "Schedule",
    "TABLE6_OPTIONS",
    "TABLE6_ROWS",
    "THRESHOLD_CENSUS_ONE_PERSON_65_PLUS",
    "THRESHOLD_YEAR_ELIGIBILITY",
    "TrackMPolicy",
    "WINDOW_AFTER",
    "WINDOW_IN_OR_AFTER",
    "d219_items",
    "pending_decisions",
    "policy_for_row",
]

SPECIFICATION_ID = "urban2006_minimum_benefits_exercise4"
#: The consolidated decision card of the plan, registered with ``cos``.
DECISION_RECORD = "d219"

#: Table 6 prints its 2025 block for options 2-5 only (availability Y1).
TABLE6_OPTIONS: tuple[int, ...] = (2, 3, 4, 5)
#: Table 6's rows: All, with Men and Women nested under it.
TABLE6_ROWS: tuple[str, ...] = ("all", "men", "women")
#: Designated before any result (plan R2; d219 item 1, pending).
HEADLINE_CELL: tuple[int, str] = (2, "all")

#: The snapshot (plan G2; d219 item 2): the 2023 PSID wave reports income
#: year 2022.
SNAPSHOT_WAVE = 2023
SNAPSHOT_INCOME_YEAR = 2022
#: Plan G2 headline: every policy date moved back three years, so the 2022
#: snapshot exposes 19 entitlement cohorts as DYNASIM's 2025 does (d219
#: item 3, pending).
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
#: G4 primary: the PIA was first calculated in or after the policy year.
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
#: MS5: the PIA implied by the observed benefit.
PIA_BENEFIT_IMPLIED = "benefit_implied"
#: G5 primary for DI: the disclosed approximation of Track A.
DI_PIA_APPROXIMATE = "approximate_pia"
#: MS6: the statutory DI computation years (42 USC 415(b)(2)(A)(ii)).
DI_PIA_STATUTORY = "statutory_computation_years"
#: G12: Y* = Y * 40 / D, D the elapsed years from age 22 to onset.
DI_PRORATION_ELAPSED = "elapsed_years_from_age_22"
#: Builder default: Y* is not rounded (the plan's INVENTED case D).
PRORATED_YEARS_EXACT = "exact"
PRORATED_YEARS_FLOOR = "floor"
#: G8: the Census weighted-average threshold for one person aged 65+.
THRESHOLD_CENSUS_ONE_PERSON_65_PLUS = (
    "census_weighted_average_one_person_65_plus"
)
#: G8: the threshold of the eligibility year (a DI worker: onset year).
THRESHOLD_YEAR_ELIGIBILITY = "eligibility_year_di_onset_year"
#: d219 item 4: PSID labor income is treated as covered earnings.
COVERED_LABOR_INCOME = "psid_labor_income_treated_as_covered"
#: G6 builder default: before 1978, the 1978 annual amount scaled back by
#: the average wage index.
PRE_1978_SCALED_BY_AWI = "qc_1978_scaled_back_by_awi"
#: Builder reading of the plan's named delta "odd-year gap imputation from
#: 1997 on" (and M5's "odd-year gap law"): a biennial gap year takes the
#: immediate-neighbor law of ``estimates.career`` before the count.
GAP_YEARS_NEIGHBOR = "immediate_neighbor_mean"
#: Alternative: G6 read literally, a never-collected year counts as zero.
GAP_YEARS_ZERO = "zero"
#: Builder default: the monthly minimum is compared unrounded.
MINIMUM_ROUNDING_NONE = "none"
#: Alternative: floor the monthly minimum to a dime, as 415(g) rounds a PIA
#: (the oracle's ``ss.benefits.pia`` convention).
MINIMUM_ROUNDING_DIME = "dime_floor"

_CHOICES: dict[str, tuple[Any, ...]] = {
    "policy_year": (HEADLINE_POLICY_YEAR, REPORT_POLICY_YEAR),
    "window_rule": (WINDOW_IN_OR_AFTER, WINDOW_AFTER),
    "order": (ORDER_FLOOR_AFTER_CUT, ORDER_CUT_AFTER_FLOOR),
    "counting_rule": (COUNT_OWN_OR_LINKED, COUNT_OWN_ONLY),
    "pia_rule": (PIA_HISTORY, PIA_BENEFIT_IMPLIED),
    "di_pia_rule": (DI_PIA_APPROXIMATE, DI_PIA_STATUTORY),
    "death_pia_rule": (DI_PIA_APPROXIMATE,),
    "di_proration": (DI_PRORATION_ELAPSED,),
    "di_prorated_years_rounding": (
        PRORATED_YEARS_EXACT,
        PRORATED_YEARS_FLOOR,
    ),
    "threshold_rule": (THRESHOLD_CENSUS_ONE_PERSON_65_PLUS,),
    "threshold_year_rule": (THRESHOLD_YEAR_ELIGIBILITY,),
    "covered_earnings_rule": (COVERED_LABOR_INCOME,),
    "pre_1978_coverage_rule": (PRE_1978_SCALED_BY_AWI,),
    "gap_year_rule": (GAP_YEARS_NEIGHBOR, GAP_YEARS_ZERO),
    "minimum_rounding": (MINIMUM_ROUNDING_NONE, MINIMUM_ROUNDING_DIME),
    "couples_cap": ("none",),
    "unlinked_auxiliary": ("not_receiving_counted_separately",),
}


@dataclass(frozen=True)
class TrackMPolicy:
    """Every open Track M rule choice; the defaults are the plan's primary.

    Fields and their plan basis (section 7 of revision 2):

    * ``policy_year`` (G2, d219 item 3): 2004 in the headline, 2007 in MS1.
      The wage-indexed minimum's base year moves with it (G9).
    * ``window_rule`` (G4): PIA first calculated in or after the policy
      year; MS4 after it.
    * ``order`` (G10, d219 item 5): the minimum is a floor after the cut;
      MS2 applies the cut after the floor.
    * ``counting_rule`` (G23, d219 item 7): own or linked worker's PIA; MS3
      own only.
    * ``pia_rule`` (G5; MS5) and ``di_pia_rule`` (G5; MS6).
      ``death_pia_rule`` (builder default, the plan is silent): a worker
      who died before eligibility gets Track A's approximation too.
    * ``di_proration`` (G12, d219 item 6) with ``di_proration_start_age``
      (22), ``di_proration_cap_years`` (40) and the builder's
      ``di_prorated_years_rounding`` (exact, as in the plan's INVENTED case
      D).
    * ``threshold_rule`` and ``threshold_year_rule`` (G8),
      ``wage_index_lag_years`` (G9, builder default 2, as bend points
      use the second year before).
    * ``covered_earnings_rule`` (d219 item 4), ``pre_1978_coverage_rule``,
      ``gap_year_rule`` and ``unobserved_window_start_age`` (G6 and the
      named delta on odd-year gaps; builder defaults) and
      ``quarters_per_work_year`` (Table 5's column head: "work year = 4
      CQ").
    * ``minimum_rounding`` (builder default: none).
    * ``couples_cap`` and ``unlinked_auxiliary`` (G13).
    """

    policy_year: int = HEADLINE_POLICY_YEAR
    window_rule: str = WINDOW_IN_OR_AFTER
    order: str = ORDER_FLOOR_AFTER_CUT
    counting_rule: str = COUNT_OWN_OR_LINKED
    pia_rule: str = PIA_HISTORY
    di_pia_rule: str = DI_PIA_APPROXIMATE
    death_pia_rule: str = DI_PIA_APPROXIMATE
    di_proration: str = DI_PRORATION_ELAPSED
    di_proration_start_age: int = 22
    di_proration_cap_years: int = 40
    di_prorated_years_rounding: str = PRORATED_YEARS_EXACT
    threshold_rule: str = THRESHOLD_CENSUS_ONE_PERSON_65_PLUS
    threshold_year_rule: str = THRESHOLD_YEAR_ELIGIBILITY
    wage_index_lag_years: int = 2
    covered_earnings_rule: str = COVERED_LABOR_INCOME
    pre_1978_coverage_rule: str = PRE_1978_SCALED_BY_AWI
    gap_year_rule: str = GAP_YEARS_NEIGHBOR
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
    "MS6": {"di_pia_rule": DI_PIA_STATUTORY},
}


def policy_for_row(row: str, base: TrackMPolicy | None = None) -> TrackMPolicy:
    """The policy of registered row ``row``: ``base`` with its one change."""

    if row not in REGISTERED_ROWS:
        raise ValueError(f"row must be one of {sorted(REGISTERED_ROWS)}")
    return replace(base or TrackMPolicy(), **REGISTERED_ROWS[row])


@dataclass(frozen=True)
class PendingDecision:
    """One open choice: its default, alternatives, basis and owner.

    ``card_item`` is the d219 item that covers it, or ``None`` for a choice
    that awaits the specification freeze (the referee, then Max's
    ratification of the specification by merge).
    """

    field: str
    default: Any
    alternatives: tuple[Any, ...]
    basis: str
    awaiting: str
    card_item: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "default": self.default,
            "alternatives": list(self.alternatives),
            "basis": self.basis,
            "awaiting": self.awaiting,
            "card_item": self.card_item,
        }


#: The nine items of the consolidated decision card (plan, end of file),
#: paraphrased, with the parameter or process each governs.
_D219: dict[int, tuple[str, str]] = {
    1: (
        "target_cells",
        "score Table 6's 12 printed 2025 cells (options 2-5 by All, Men and "
        "Women; headline option 2, All) and hold the poverty effect for "
        "Track P (2050, Table 9)",
    ),
    2: (
        "claim_class",
        "a static PSID snapshot for income year 2022, labelled not a "
        "projection, not 2025 and not Axiom",
    ),
    3: (
        "policy_year",
        "move every policy date back three years in the headline (policy "
        "year 2004, 19 exposed entitlement cohorts); the Report's 2007 "
        "dating is row MS1",
    ),
    4: (
        "covered_earnings_rule",
        "years of coverage and the minimum rules in a new Python module "
        "outside ss/, calling the oracle unchanged; PSID labor income "
        "treated as covered earnings",
    ),
    5: (
        "order",
        "the minimum is a floor after the uniform cut; the reverse order "
        "is row MS2",
    ),
    6: (
        "di_proration",
        "DI work years prorated as Y * 40 / years elapsed from age 22 to "
        "onset, capped at 40",
    ),
    7: (
        "counting_rule",
        "anyone paid a benefit computed from a PIA that rests on the "
        "minimum (own or a linked worker's) counts; own-PIA-only is row "
        "MS3",
    ),
    8: (
        "acceptance_rule",
        "no numerical acceptance threshold; gaps are reported as results",
    ),
    9: (
        "ratification_and_registration",
        "Max ratifies the specification by merge, posts or authorizes the "
        "issue #42 registration, then merges the run PR; any request to "
        "Urban is optional and his to send",
    ),
}


def d219_items() -> dict[int, tuple[str, str]]:
    """The nine d219 items: ``{item: (field or process, paraphrase)}``."""

    return dict(_D219)


def pending_decisions() -> tuple[PendingDecision, ...]:
    """Every open choice with its default; nothing here is ratified."""

    policy = TrackMPolicy()
    max_ = f"Max, cos decision {DECISION_RECORD} item {{}} (open)"
    freeze = (
        "M1 specification freeze (referee, then Max's ratification by "
        "merge, d219 item 9)"
    )
    card: list[PendingDecision] = [
        PendingDecision(
            "target_cells",
            "table6_2025_options_2_to_5_by_all_men_women_headline_2_all",
            (),
            "plan R1-R2: the Report prints no 2025 poverty statistic; "
            "Table 6's 2025 block is the only printed 2025 outcome",
            max_.format(1),
            1,
        ),
        PendingDecision(
            "claim_class",
            "track_m_static_psid_snapshot_income_year_2022",
            (),
            "plan R2 and bottom line 2",
            max_.format(2),
            2,
        ),
        PendingDecision(
            "policy_year",
            policy.policy_year,
            (REPORT_POLICY_YEAR,),
            "plan G2: exposure aligned with DYNASIM's 2025 (19 cohorts); "
            "MS1 keeps the Report's 2007",
            max_.format(3),
            3,
        ),
        PendingDecision(
            "covered_earnings_rule",
            policy.covered_earnings_rule,
            (),
            "plan section 5: the PSID has no covered/noncovered split",
            max_.format(4),
            4,
        ),
        PendingDecision(
            "order",
            policy.order,
            (ORDER_CUT_AFTER_FLOOR,),
            "plan G10; D10 is a printed mechanism, not a printed rule",
            max_.format(5),
            5,
        ),
        PendingDecision(
            "di_proration",
            policy.di_proration,
            (),
            "plan G12; fn. 26 and D3 print the basis, not the formula",
            max_.format(6),
            6,
        ),
        PendingDecision(
            "counting_rule",
            policy.counting_rule,
            (COUNT_OWN_ONLY,),
            "plan G23; fn. 33 does not say which auxiliaries count",
            max_.format(7),
            7,
        ),
        PendingDecision(
            "acceptance_rule",
            None,
            (),
            "plan G20: gaps are results",
            max_.format(8),
            8,
        ),
        PendingDecision(
            "ratification_and_registration",
            "ratify_by_merge_then_issue_42_registration_then_one_shot",
            (),
            "plan section 11",
            max_.format(9),
            9,
        ),
    ]
    builder: list[PendingDecision] = [
        PendingDecision(
            "window_rule",
            policy.window_rule,
            (WINDOW_AFTER,),
            "plan G4 (2007 inclusive); MS4 is the 'entitled after' wording",
            freeze,
            None,
        ),
        PendingDecision(
            "pia_rule",
            policy.pia_rule,
            (PIA_BENEFIT_IMPLIED,),
            "plan G5; MS5",
            freeze,
            None,
        ),
        PendingDecision(
            "di_pia_rule",
            policy.di_pia_rule,
            (DI_PIA_STATUTORY,),
            "plan G5 (Track A's disclosed approximation); MS6",
            freeze,
            None,
        ),
        PendingDecision(
            "death_pia_rule",
            policy.death_pia_rule,
            (),
            "builder default: the plan does not say how to compute the "
            "PIA of a worker who died before eligibility, whose PIA is "
            "first calculated for a survivor; G5's DI approximation is "
            "used",
            freeze,
            None,
        ),
        PendingDecision(
            "di_proration_start_age",
            policy.di_proration_start_age,
            (),
            "plan G12 builder default; the Report prints no start age",
            freeze,
            None,
        ),
        PendingDecision(
            "di_prorated_years_rounding",
            policy.di_prorated_years_rounding,
            (PRORATED_YEARS_FLOOR,),
            "builder default: the plan's INVENTED case D applies the "
            "schedule to an unrounded Y* (27.27 years); G7's 'no partial "
            "years' is read as applying to Y itself",
            freeze,
            None,
        ),
        PendingDecision(
            "threshold_rule",
            policy.threshold_rule,
            (),
            "plan G8: fn. 25 prints Census thresholds for the aged; one "
            "person, the weighted average and the 65-and-over row are the "
            "plan's reading (the option 6 passage's 65+ wording; the fn. 27 "
            "blind check is M2's)",
            freeze,
            None,
        ),
        PendingDecision(
            "threshold_year_rule",
            policy.threshold_year_rule,
            (),
            "plan G8: the eligibility year's threshold (DI: onset year)",
            freeze,
            None,
        ),
        PendingDecision(
            "wage_index_lag_years",
            policy.wage_index_lag_years,
            (),
            "plan G9 builder default (as the bend points use the second "
            "year before)",
            freeze,
            None,
        ),
        PendingDecision(
            "pre_1978_coverage_rule",
            policy.pre_1978_coverage_rule,
            (),
            "plan G6 builder default; the statute (42 USC 413) is to be "
            "captured and read in M2 before the rules use it",
            freeze,
            None,
        ),
        PendingDecision(
            "gap_year_rule",
            policy.gap_year_rule,
            (GAP_YEARS_ZERO,),
            "builder reading: G6 counts unobserved years as zero, but the "
            "plan's named deltas list 'odd-year gap imputation from 1997 "
            "on' and M5 names 'the odd-year gap law'; the biennial gap "
            "years (1997-2021, odd) take the immediate-neighbor law of "
            "estimates.career before the count, and G6's zero applies to "
            "years still unobserved",
            freeze,
            None,
        ),
        PendingDecision(
            "unobserved_window_start_age",
            policy.unobserved_window_start_age,
            (),
            "builder default: G6 flags unobserved years but does not say "
            "from which age; 22 matches G12's start",
            freeze,
            None,
        ),
        PendingDecision(
            "couples_cap",
            policy.couples_cap,
            (),
            "plan G13: no cap on couples' minimum-based benefits (D7 is an "
            "inference that the simulated minimums had none)",
            freeze,
            None,
        ),
        PendingDecision(
            "unlinked_auxiliary",
            policy.unlinked_auxiliary,
            (),
            "plan G13: an auxiliary with no linked worker record cannot be "
            "flagged; counted as not receiving and reported separately",
            freeze,
            None,
        ),
        PendingDecision(
            "minimum_rounding",
            policy.minimum_rounding,
            (MINIMUM_ROUNDING_DIME,),
            "builder default: the Report prints no rounding of the "
            "minimum; the plan's INVENTED cases compare unrounded amounts",
            freeze,
            None,
        ),
    ]
    return (*card, *builder)


def _check_rows() -> None:
    names = {f.name for f in fields(TrackMPolicy)}
    for row, change in REGISTERED_ROWS.items():
        if len(change) > 1 or not set(change) <= names:
            raise AssertionError(f"row {row} is not a one-field change")
        policy_for_row(row)


_check_rows()
