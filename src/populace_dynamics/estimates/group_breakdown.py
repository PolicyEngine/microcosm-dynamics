"""Group breakdowns of the blind tests by MINT8 characteristic subgroups.

NASI follow-up package G3 (orchestrating session 95606380, 2026-10-01).
After the NASI meeting of 2026-10-01 Max asked for each of the four
finished DYNASIM3 blind tests broken down by SSA's MINT categories.  This
module is the tabulation core of that request.  It takes the person rows a
blind test already produces, with each person's group attributes joined on
by cohort code, and reduces them to one cell per characteristic subgroup.
It reads no PSID file, projects nothing, computes no benefit, income or
poverty status, reads no comparator value, applies no acceptance rule and
writes no artifact.  A real-data breakdown is a post hoc analysis that runs
only under its own issue #42 registration: ``data_provenance=
"registered_real"`` requires the registration pointer, output labels and
the caller's post hoc labels.  Development and tests use INVENTED rows.

Category schemes (data, not code paths)
---------------------------------------
A :class:`CategoryScheme` is an ordered tuple of :class:`Dimension` (a row
group such as "Marital status"), each an ordered tuple of
:class:`Category` (a row such as "Widowed").  A dimension is one of four
kinds:

* ``total``: one row, every person;
* ``categorical``: each category lists the attribute codes it holds;
* ``band``: each category is an inclusive integer interval (age, years of
  education);
* ``quintile``: five categories ranked 1 (lowest) to 5 (highest) of a
  numeric measure, cut by weighted quintile thresholds
  (:func:`weighted_quintile_ranks`).

:data:`MINT8_SCHEME` holds the row groups and row labels of MINT8's annual
projected-effects tables for Social Security benefits and household income
(tables 1-3 and 7-9 of a MINT8 policy-option page; population: current-law
beneficiaries aged 60 or older), verbatim and in SSA's page order, taken
from the committed labels-only extract
``data/external/mint8_row_categories.json``.  :data:`MINT8_POVERTY_SCHEME`
is the official-poverty tables' scheme (tables 10-12), which carries no
household income quintile rows, and :data:`MINT8_COHORT_SCHEME` the cohort
tables' scheme (tables 13-20), whose three lifetime measures (initial AIME
quintile; lifetime payroll tax quintile, own and shared) serve as the
lifetime-earnings dimension the NASI request names.  The two
``*_WITH_LIFETIME`` schemes append those three measures to the annual
schemes; they are compositions of this module, not MINT8 table layouts,
and say so (``composite``).  Every definition string a MINT8 dimension
carries is a verbatim quote of SSA's MINT8 Table User Guide (committed
capture ``data/external/mint8_table_user_guide.source.html``), and
:func:`verify_mint8_sources` checks the files' SHA-256 pins, every label
against the label extract and every quote against the Guide's text.

Alternate schemes (for example the row labels of Butrica and Uccello 2004,
which ``uniform_cut_tabulation.NOT_COMPUTED_REPORT_ROWS`` already records)
are added with :func:`register_scheme`, and variants with
:func:`derive_scheme`; :func:`with_age_bands` swaps a scheme's age bands for
another set in :data:`AGE_BAND_SETS` (MINT8's beneficiary and taxpayer
bands, and exercises 1 and 3's registered bands ``50-61`` ... ``80+``,
taken from ``cola_age_profile.DEFAULT_AGE_GROUPS``).

Group assignment and unclassified rows
--------------------------------------
:func:`assign_groups` maps each row of a frame to one category per
dimension and returns a :class:`GroupAssignment`, whose long frame has one
row per (row id, dimension) with the label or ``unclassified``.  A row
whose attribute is missing (``None``, ``NaN``, ``pd.NA``), whose code the
caller declares unclassified (``unclassified_codes``, for example a
``separated`` marital status SSA does not place), or whose band value lies
outside every band is unclassified for that dimension: it is counted, by
reason, and enters Total only.  A present code that no category holds, and
was not declared, is refused, never silently dropped.  So within each
dimension the classified labels partition the classified rows, and
classified plus unclassified is Total, in counts and weights.

Statistics
----------
*Projection benefit change* (exercises 1 and 3;
:func:`tabulate_projection_breakdown`), per draw and cell, reusing
``cola_age_profile`` read-only (``_normalize``, ``_membership_masks``,
``_cell``, ``_draw_summary``, ``_floor_summary``, ``_side_mean``): the
ratio of scenario means ``100 * (mu_reform / mu_base - 1)`` and the mean
of individual ratios, with scenario memberships exactly as the
``ColaAgeProfileConfig`` defines them; and MINT8's benefit statistics over
the current-law beneficiaries with a positive selected benefit: percent
with a decrease, percent with an increase (and the unaffected rest), and
the weighted 10th, 50th and 90th percentiles of each person's percent
change.  Each is reported as the mean over draws with the draws' sample SD.

*Static* cells (exercises 2 and 4, one deterministic run): poverty
(:func:`tabulate_poverty_breakdown`: official poverty rate under current
law and with the proposal, the change in points, the number in poverty in
thousands under each and its change, and the percent change in the number
in poverty, rates through ``uniform_cut_tabulation._rates``); a weighted
share (:func:`tabulate_share_breakdown`, exercise 4's statistic); and the
MINT8 benefit statistics (:func:`tabulate_static_benefit_breakdown`).

Weighted percentile (:data:`PERCENTILE_DEFINITION`)
---------------------------------------------------
Zero-weight rows carry no mass and are dropped; values are sorted; with
``W_k`` the cumulative weight of the k smallest and ``W`` the total, the
level-p percentile is the smallest ``x_k`` with ``W_k >= p W``, and when
``W_k = p W`` holds exactly it is the midpoint of ``x_k`` and ``x_(k+1)``.
Levels are exact rationals and the comparison is exact rational arithmetic
on the float64 weights (integer numerators over one power-of-two
denominator), so "exactly" means exactly.  This is the rule the G3 brief
specifies (smallest value whose cumulative weight reaches p, midpoint at
an exact tie); its first half is the repository's existing rule
(``uniform_cut_track_u.diagnostics.weighted_quantile``).

Uncertainty
-----------
* Projection: the sample SD over the K draws, and the half-sample floor of
  ``cola_age_profile``: for each floor seed the split units
  (``config.floor_split_unit``, the opening-wave family unit by default)
  of **all** input rows are split once with
  ``harness.panel.split_panel_by_person`` (fraction 0.5), and each group
  uses that split intersected with its own mask -- never a re-split of the
  group's subset, which would put family units on different sides
  (:func:`half_split_masks`).  The floor is the summary of
  ``|side_a - side_b|`` over the usable seeds and is undefined, not zero,
  with fewer than two.
* Static: the design-based standard error of
  ``uniform_cut_tabulation._design_se`` (Taylor linearization of the
  weighted ratio over the full sample design's strata and clusters, the
  group as a domain) for rates, changes in rates and shares, and the same
  half-sample floor with the split computed once on all rows (default
  split unit: family units linked through shared persons,
  ``uniform_cut_tabulation.floor_split_units``).  No design SE is reported
  for weighted percentiles, weighted counts or the percent change in the
  number in poverty; each such cell says why.

Suppression flags (never drops)
-------------------------------
Every cell carries its unweighted n and flags: below SSA's disclosure
minimum of 100 cases, below 30 cases, and, for the percent-with-decrease
and percent-with-increase statistics, SSA's numerator rule (a numerator of
1-9 cases).  A dimension with any flagged row is flagged
``ssa_subgroup_suppressed``, because SSA would remove the whole subgroup.
Nothing is dropped.

Result schema
-------------
Every tabulator returns a :class:`GroupBreakdownResult` (frozen
dataclasses down to each :class:`StatisticCell`); ``as_dict()`` gives a
JSON-safe mapping (finite numbers only) carrying the labels, the caller's
post hoc labels, the scheme with its citations, every statistic's
definition and MINT8 column, and the conventions above.
"""

from __future__ import annotations

import bisect
import hashlib
import itertools
import json
import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from html.parser import HTMLParser
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.estimates import cola_age_profile as a7
from populace_dynamics.estimates import uniform_cut_tabulation as track_u
from populace_dynamics.harness.panel import split_panel_by_person

__all__ = [
    "AGE_BAND_SETS",
    "BAND",
    "CATEGORICAL",
    "DATA_PROVENANCES",
    "DEFAULT_FLOOR_SEEDS",
    "DIMENSION_KINDS",
    "FAMILY_UNIT",
    "FAMILY_UNIT_LINKED_BY_PERSON",
    "INVENTED",
    "INVENTED_DATA_LABEL",
    "MINT8_ANNUAL_WITH_LIFETIME_SCHEME",
    "MINT8_COHORT_SCHEME",
    "MINT8_POVERTY_SCHEME",
    "MINT8_POVERTY_WITH_LIFETIME_SCHEME",
    "MINT8_SCHEME",
    "MINT8_SOURCE_SHA256",
    "MINT_BENEFIT_STATISTICS",
    "P10",
    "P50",
    "P90",
    "PERCENTILE_DEFINITION",
    "PERSON",
    "POVERTY_STATISTICS",
    "PROJECTION_STATISTICS",
    "QUINTILE",
    "QUINTILE_LEVELS",
    "REGISTERED_REAL",
    "REGISTRATION_POINTER",
    "SCHEMA_VERSION",
    "SHARE_STATISTICS",
    "SMALL_CELL_MIN_N",
    "SSA_DISCLOSURE_MIN_N",
    "SSA_NUMERATOR_MIN",
    "STATIC_BENEFIT_STATISTICS",
    "STATISTIC_DEFINITIONS",
    "TOTAL",
    "UNCLASSIFIED",
    "Category",
    "CategoryScheme",
    "Dimension",
    "DimensionResult",
    "GroupAssignment",
    "GroupBreakdownError",
    "GroupBreakdownResult",
    "GroupCell",
    "StatisticCell",
    "assign_groups",
    "classify_changes",
    "derive_scheme",
    "get_scheme",
    "half_split_masks",
    "register_scheme",
    "registered_scheme_ids",
    "tabulate_poverty_breakdown",
    "tabulate_projection_breakdown",
    "tabulate_share_breakdown",
    "tabulate_static_benefit_breakdown",
    "verify_mint8_sources",
    "weighted_percentiles",
    "weighted_quintile_ranks",
    "with_age_bands",
]

SCHEMA_VERSION = "populace_dynamics.group_breakdown.v1"


class GroupBreakdownError(ValueError):
    """The scheme, the rows or the provenance cannot yield the breakdown."""


# =========================================================================
# Constants
# =========================================================================
TOTAL = "total"
CATEGORICAL = "categorical"
BAND = "band"
QUINTILE = "quintile"
DIMENSION_KINDS = (TOTAL, CATEGORICAL, BAND, QUINTILE)
TOTAL_KEY = "total"
TOTAL_LABEL = "Total"
#: The label a row takes, in the long frame, in a dimension it is not
#: classified in.  No category label may equal it.
UNCLASSIFIED = "unclassified"
MISSING_REASON = "missing"
OUTSIDE_BANDS_REASON = "outside_bands"

INVENTED = a7.INVENTED
REGISTERED_REAL = a7.REGISTERED_REAL
DATA_PROVENANCES = (INVENTED, REGISTERED_REAL)
#: The exercise-1 tabulation's invented-data label, reused verbatim.
INVENTED_DATA_LABEL = a7.INVENTED_DATA_LABEL
#: ``attrs["provenance_kind"]`` of rows built from staged PSID files (the
#: Track U and Track M convention).
PSID_FILES = "psid_files"
#: An issue #42 comment, the registration issue (the pattern of
#: ``min_benefit_track_m.tabulation.REGISTRATION_POINTER``, which a test
#: holds equal).
REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)

#: SSA's disclosure minimum (MINT8 Table User Guide, "Sample Size
#: Restrictions"), its numerator threshold, and the repository's small-cell
#: line.
SSA_DISCLOSURE_MIN_N = 100
SSA_NUMERATOR_MIN = 10
SMALL_CELL_MIN_N = 30

P10 = Fraction(1, 10)
P50 = Fraction(1, 2)
P90 = Fraction(9, 10)
QUINTILE_LEVELS = (
    Fraction(1, 5),
    Fraction(2, 5),
    Fraction(3, 5),
    Fraction(4, 5),
)

#: The floor seeds and fraction of every existing tabulator.
DEFAULT_FLOOR_SEEDS = a7.DEFAULT_FLOOR_SEEDS
FLOOR_FRACTION = a7.FLOOR_FRACTION
MIN_FLOOR_SEEDS = a7.MIN_FLOOR_SEEDS
FAMILY_UNIT_LINKED_BY_PERSON = "family_unit_linked_by_person"
FAMILY_UNIT = "family_unit_id"
PERSON = "person_id"
STATIC_FLOOR_SPLIT_UNITS: dict[str, str] = {
    FAMILY_UNIT_LINKED_BY_PERSON: (
        "family units merged through shared persons "
        "(uniform_cut_tabulation.floor_split_units; with one row per person "
        "these are the family units), the Track U and Track M floor unit"
    ),
    FAMILY_UNIT: "the family_unit_id column as given",
    PERSON: "the person_id column (not registered by any blind test)",
}

# ---- statistics -----------------------------------------------------------
RATIO_OF_SCENARIO_MEANS = a7.RATIO_OF_SCENARIO_MEANS
MEAN_OF_INDIVIDUAL_RATIOS = a7.MEAN_OF_INDIVIDUAL_RATIOS
PERCENT_DECREASE = "percent_with_decrease"
PERCENT_INCREASE = "percent_with_increase"
PERCENT_UNAFFECTED = "percent_unaffected"
CHANGE_P10 = "percent_change_p10"
CHANGE_MEDIAN = "percent_change_median"
CHANGE_P90 = "percent_change_p90"
PERCENTILE_STATISTICS: dict[str, Fraction] = {
    CHANGE_P10: P10,
    CHANGE_MEDIAN: P50,
    CHANGE_P90: P90,
}
MINT_BENEFIT_STATISTICS = (
    PERCENT_DECREASE,
    PERCENT_INCREASE,
    PERCENT_UNAFFECTED,
    CHANGE_P10,
    CHANGE_MEDIAN,
    CHANGE_P90,
)
PROJECTION_STATISTICS = (
    RATIO_OF_SCENARIO_MEANS,
    MEAN_OF_INDIVIDUAL_RATIOS,
    *MINT_BENEFIT_STATISTICS,
)
STATIC_BENEFIT_STATISTICS = MINT_BENEFIT_STATISTICS

POVERTY_RATE_CURRENT_LAW = "poverty_rate_current_law"
POVERTY_RATE_PROPOSAL = "poverty_rate_proposal"
POVERTY_RATE_CHANGE = "poverty_rate_change_pp"
NUMBER_POOR_CURRENT_LAW = "number_in_poverty_current_law_thousands"
NUMBER_POOR_PROPOSAL = "number_in_poverty_proposal_thousands"
NUMBER_POOR_CHANGE = "number_in_poverty_change_thousands"
NUMBER_POOR_PERCENT_CHANGE = "percent_change_number_in_poverty"
POVERTY_STATISTICS = (
    POVERTY_RATE_CURRENT_LAW,
    POVERTY_RATE_PROPOSAL,
    POVERTY_RATE_CHANGE,
    NUMBER_POOR_CURRENT_LAW,
    NUMBER_POOR_PROPOSAL,
    NUMBER_POOR_CHANGE,
    NUMBER_POOR_PERCENT_CHANGE,
)
SHARE = "weighted_share_percent"
SHARE_STATISTICS = (SHARE,)

PROJECTION_KIND = "projection_benefit_change"
POVERTY_KIND = "static_poverty"
SHARE_KIND = "static_share"
STATIC_BENEFIT_KIND = "static_benefit_change"

_MINT_POPULATION = (
    "P = rows that are current-law (baseline) recipients with a positive "
    "current-law amount B_current_law > 0 (MINT8: current-law "
    "beneficiaries)"
)
PERCENTILE_DEFINITION = (
    "weighted percentile at level p (exact rationals 1/10, 1/2, 9/10; "
    "quintile thresholds at 1/5, 2/5, 3/5, 4/5): rows with zero weight "
    "carry no mass and are dropped; the values are sorted ascending; with "
    "W_k the cumulative weight of the k smallest values and W the total, "
    "the percentile is the smallest value x_k with W_k >= p * W, except "
    "that when W_k = p * W holds exactly (exact rational arithmetic on the "
    "float64 weights) it is the midpoint (x_k + x_(k+1)) / 2 of that value "
    "and the next one; no other interpolation"
)
CHANGE_DEFINITION = (
    "individual percent change c_i = 100 * (B_option,i / B_current_law,i "
    "- 1) over P (SSA's formula '(option amount - current-law amount) / "
    "current-law amount', in percent); a decrease is c_i <= -1 and an "
    "increase c_i >= +1, decided in exact rational arithmetic on the "
    "float64 amounts (100 * B_option <= 99 * B_current_law; 100 * B_option "
    ">= 101 * B_current_law), so a change of exactly 1 percent counts; "
    "-1 < c_i < 1 is unaffected (MINT8 Table User Guide, 'Threshold for "
    "Categorization in the Decrease or Increase Groups')"
)
QUINTILE_RULE = (
    "the thresholds t_1..t_4 are the weighted percentiles (the percentile "
    "rule) at 1/5, 2/5, 3/5 and 4/5 of the measure over the partition's "
    "rows with a non-missing measure; a row's rank is 1 + the number of "
    "thresholds strictly below its value, so a value equal to t_k falls in "
    "the lower quintile; rank 1 is 'Lowest' and 5 'Highest'.  Quintiles "
    "are cut separately within each partition the caller names (for "
    "example each draw, or each birth cohort, as MINT8's cohort tables "
    "do).  SSA does not publish its tie rule ('The dollar ranges are "
    "available upon request'), so the tie rule is this module's"
)
UNCLASSIFIED_RULE = (
    "a row whose attribute is missing, whose code the caller declares "
    "unclassified, or whose band value lies outside every band is "
    "unclassified in that dimension: counted by reason and entering Total "
    "only; a present code no category holds and the caller did not "
    "declare is refused"
)

#: Each statistic's definition and its MINT8 column (``None`` where it is
#: not a MINT8 column).
STATISTIC_DEFINITIONS: dict[str, dict[str, Any]] = {
    RATIO_OF_SCENARIO_MEANS: {
        "formula": a7.STATISTIC_DEFINITIONS[RATIO_OF_SCENARIO_MEANS],
        "membership": (
            "scenario memberships S_base and S_reform exactly as "
            "cola_age_profile defines them for the ColaAgeProfileConfig "
            "passed (recipient_rule, membership_basis)"
        ),
        "unit": "percent change of the reform relative to the baseline",
        "mint8_column": None,
        "note": "the statistic of exercises 1 and 3 (cola_age_profile)",
    },
    MEAN_OF_INDIVIDUAL_RATIOS: {
        "formula": a7.STATISTIC_DEFINITIONS[MEAN_OF_INDIVIDUAL_RATIOS],
        "membership": "S_alt as cola_age_profile defines it",
        "unit": "percent",
        "mint8_column": None,
        "note": "cola_age_profile's registered alternative statistic",
    },
    PERCENT_DECREASE: {
        "formula": "100 * sum_{i in P} w_i 1{c_i <= -1} / sum_{i in P} w_i",
        "population": _MINT_POPULATION,
        "change": CHANGE_DEFINITION,
        "unit": "percent of the population",
        "mint8_column": "Percent of population with a— Benefit decrease",
    },
    PERCENT_INCREASE: {
        "formula": "100 * sum_{i in P} w_i 1{c_i >= 1} / sum_{i in P} w_i",
        "population": _MINT_POPULATION,
        "change": CHANGE_DEFINITION,
        "unit": "percent of the population",
        "mint8_column": "Percent of population with a— Benefit increase",
    },
    PERCENT_UNAFFECTED: {
        "formula": (
            "100 * sum_{i in P} w_i 1{-1 < c_i < 1} / sum_{i in P} w_i"
        ),
        "population": _MINT_POPULATION,
        "change": CHANGE_DEFINITION,
        "unit": "percent of the population",
        "mint8_column": None,
        "note": (
            "not a MINT8 column; reported so that decrease + unaffected + "
            "increase = 100 can be checked"
        ),
    },
    **{
        name: {
            "formula": (
                f"weighted percentile at level {level} of c_i over P "
                "(percentile_definition)"
            ),
            "population": _MINT_POPULATION,
            "change": CHANGE_DEFINITION,
            "unit": "percent change",
            "mint8_column": (
                "Percent change in Social Security benefits at the— " + label
            ),
        }
        for name, level, label in (
            (CHANGE_P10, P10, "10th %ile"),
            (CHANGE_MEDIAN, P50, "Median"),
            (CHANGE_P90, P90, "90th %ile"),
        )
    },
    POVERTY_RATE_CURRENT_LAW: {
        "formula": "100 * sum w 1{poor_baseline} / sum w",
        "unit": "percent",
        "mint8_column": "Official poverty rate: Under current law",
        "computed_by": "uniform_cut_tabulation._rates (baseline_rate)",
    },
    POVERTY_RATE_PROPOSAL: {
        "formula": "100 * sum w 1{poor_reform} / sum w",
        "unit": "percent",
        "mint8_column": "Official poverty rate: With proposal",
        "computed_by": "uniform_cut_tabulation._rates (reform_rate)",
    },
    POVERTY_RATE_CHANGE: {
        "formula": "poverty_rate_proposal - poverty_rate_current_law",
        "unit": "percentage points",
        "mint8_column": None,
        "note": (
            "not a MINT8 column; the exercise-2 headline "
            "(uniform_cut_tabulation 'delta')"
        ),
    },
    NUMBER_POOR_CURRENT_LAW: {
        "formula": "sum w 1{poor_baseline} / 1000",
        "unit": "thousands of persons (weighted)",
        "mint8_column": (
            "Number of population in poverty (in thousands): Under current "
            "law"
        ),
    },
    NUMBER_POOR_PROPOSAL: {
        "formula": "sum w 1{poor_reform} / 1000",
        "unit": "thousands of persons (weighted)",
        "mint8_column": (
            "Number of population in poverty (in thousands): With proposal"
        ),
    },
    NUMBER_POOR_CHANGE: {
        "formula": "(sum w 1{poor_reform} - sum w 1{poor_baseline}) / 1000",
        "unit": "thousands of persons (weighted)",
        "mint8_column": (
            "Number of population in poverty (in thousands): Change"
        ),
    },
    NUMBER_POOR_PERCENT_CHANGE: {
        "formula": (
            "100 * (sum w 1{poor_reform} - sum w 1{poor_baseline}) / sum w "
            "1{poor_baseline}; undefined when nobody is poor under current "
            "law"
        ),
        "unit": "percent change in the number in poverty",
        "mint8_column": "Percent change in the number in poverty",
        "source_quote": (
            "This percent change is calculated by dividing the change in "
            "thousands in poverty (5th column) by the thousands in poverty "
            "without the proposal (3rd column)."
        ),
    },
    SHARE: {
        "formula": "100 * sum w 1{indicator} / sum w",
        "unit": "percent",
        "mint8_column": None,
        "note": (
            "exercise 4's statistic (min_benefit_track_m.tabulation._share)"
        ),
    },
}


# =========================================================================
# Category schemes
# =========================================================================
_KEY_FORM = re.compile(r"[a-z][a-z0-9_]*")


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GroupBreakdownError(f"{label} must be a non-empty string")
    return value


def _key(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _KEY_FORM.fullmatch(value):
        raise GroupBreakdownError(
            f"{label} must be lower-case letters, digits and '_' starting "
            f"with a letter; got {value!r}"
        )
    return value


def _optional_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool | np.bool_) or not isinstance(value, Integral):
        raise GroupBreakdownError(f"{label} must be an integer or None")
    return int(value)


def _string_tuple(values: Any, label: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise GroupBreakdownError(f"{label} must be a sequence of strings")
    items = tuple(values)
    for item in items:
        _nonempty_text(item, label)
    return items


@dataclass(frozen=True)
class Category:
    """One table row: its stable ``key``, printed ``label`` and rule.

    ``codes`` (categorical), ``lower``/``upper`` (band; inclusive integer
    bounds, ``None`` open) or ``rank`` (quintile; 1 lowest, 5 highest)
    say which rows it holds; the dimension's kind decides which applies.
    ``definition`` is a verbatim quote of the dimension's source, or empty.
    """

    key: str
    label: str
    codes: tuple[str, ...] = ()
    lower: int | None = None
    upper: int | None = None
    rank: int | None = None
    definition: str = ""

    def __post_init__(self) -> None:
        _key(self.key, "category key")
        _nonempty_text(self.label, f"category {self.key} label")
        if self.label == UNCLASSIFIED:
            raise GroupBreakdownError(
                f"a category label may not be {UNCLASSIFIED!r}"
            )
        codes = _string_tuple(self.codes, f"category {self.key} codes")
        if len(set(codes)) != len(codes):
            raise GroupBreakdownError(f"category {self.key} repeats a code")
        object.__setattr__(self, "codes", codes)
        object.__setattr__(
            self, "lower", _optional_int(self.lower, f"{self.key} lower")
        )
        object.__setattr__(
            self, "upper", _optional_int(self.upper, f"{self.key} upper")
        )
        object.__setattr__(
            self, "rank", _optional_int(self.rank, f"{self.key} rank")
        )
        if not isinstance(self.definition, str):
            raise GroupBreakdownError(
                f"category {self.key} definition must be a string"
            )

    def contains(self, value: int) -> bool:
        """Whether an integer lies in this band (inclusive bounds)."""

        return (self.lower is None or value >= self.lower) and (
            self.upper is None or value <= self.upper
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "codes": list(self.codes),
            "lower": self.lower,
            "upper": self.upper,
            "rank": self.rank,
            "definition": self.definition,
        }


#: The identifier of a quote source that :func:`verify_mint8_sources`
#: checks verbatim.
MINT8_GUIDE = "mint8_table_user_guide"


@dataclass(frozen=True)
class Dimension:
    """One row group (characteristic subgroup) of a table.

    ``definition`` holds verbatim quotes of ``source`` (checked against the
    committed capture when ``quote_source`` is :data:`MINT8_GUIDE`);
    ``notes`` hold this module's conventions, never presented as quotes.
    """

    key: str
    label: str
    kind: str
    categories: tuple[Category, ...]
    definition: tuple[str, ...] = ()
    source: str = ""
    quote_source: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _key(self.key, "dimension key")
        _nonempty_text(self.label, f"dimension {self.key} label")
        if self.kind not in DIMENSION_KINDS:
            raise GroupBreakdownError(
                f"dimension {self.key} kind must be one of "
                f"{list(DIMENSION_KINDS)}"
            )
        categories = tuple(self.categories)
        if not categories or not all(
            isinstance(c, Category) for c in categories
        ):
            raise GroupBreakdownError(
                f"dimension {self.key} needs a non-empty tuple of Category"
            )
        object.__setattr__(self, "categories", categories)
        keys = [c.key for c in categories]
        labels = [c.label for c in categories]
        if len(set(keys)) != len(keys) or len(set(labels)) != len(labels):
            raise GroupBreakdownError(
                f"dimension {self.key} repeats a category key or label"
            )
        object.__setattr__(
            self,
            "definition",
            _string_tuple(self.definition, f"{self.key} definition"),
        )
        object.__setattr__(
            self, "notes", _string_tuple(self.notes, f"{self.key} notes")
        )
        if not isinstance(self.source, str):
            raise GroupBreakdownError(f"{self.key} source must be a string")
        if self.quote_source is not None and self.quote_source != (
            MINT8_GUIDE
        ):
            raise GroupBreakdownError(
                f"{self.key} quote_source must be None or {MINT8_GUIDE!r}"
            )
        getattr(self, f"_validate_{self.kind}")(categories)

    def _no_rule(self, category: Category, *, allow: str = "") -> None:
        fields = {
            "codes": bool(category.codes),
            "bounds": category.lower is not None or category.upper is not None,
            "rank": category.rank is not None,
        }
        extra = [
            name for name, used in fields.items() if used and name != allow
        ]
        if extra:
            raise GroupBreakdownError(
                f"{self.kind} dimension {self.key}: category "
                f"{category.key} may not carry {extra}"
            )

    def _validate_total(self, categories: tuple[Category, ...]) -> None:
        if self.key != TOTAL_KEY or len(categories) != 1:
            raise GroupBreakdownError(
                f"the total dimension has key {TOTAL_KEY!r} and one category"
            )
        if categories[0].key != TOTAL_KEY:
            raise GroupBreakdownError(
                f"the total category has key {TOTAL_KEY!r}"
            )
        self._no_rule(categories[0])

    def _validate_categorical(self, categories: tuple[Category, ...]) -> None:
        seen: set[str] = set()
        for category in categories:
            self._no_rule(category, allow="codes")
            if not category.codes:
                raise GroupBreakdownError(
                    f"categorical dimension {self.key}: category "
                    f"{category.key} needs codes"
                )
            overlap = seen.intersection(category.codes)
            if overlap:
                raise GroupBreakdownError(
                    f"dimension {self.key}: codes {sorted(overlap)} map to "
                    "two categories"
                )
            seen.update(category.codes)

    def _validate_band(self, categories: tuple[Category, ...]) -> None:
        for category in categories:
            self._no_rule(category, allow="bounds")
            if category.lower is None and category.upper is None:
                raise GroupBreakdownError(
                    f"band {category.key} needs at least one bound"
                )
            if (
                category.lower is not None
                and category.upper is not None
                and category.upper < category.lower
            ):
                raise GroupBreakdownError(
                    f"band {category.key} has upper < lower"
                )
        for a, b in itertools.combinations(categories, 2):
            low = max(
                -math.inf if a.lower is None else a.lower,
                -math.inf if b.lower is None else b.lower,
            )
            high = min(
                math.inf if a.upper is None else a.upper,
                math.inf if b.upper is None else b.upper,
            )
            if low <= high:
                raise GroupBreakdownError(
                    f"dimension {self.key}: bands {a.key} and {b.key} overlap"
                )

    def _validate_quintile(self, categories: tuple[Category, ...]) -> None:
        for category in categories:
            self._no_rule(category, allow="rank")
        ranks = sorted(c.rank for c in categories if c.rank is not None)
        if ranks != [1, 2, 3, 4, 5]:
            raise GroupBreakdownError(
                f"quintile dimension {self.key} needs ranks 1-5 once each"
            )

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(c.label for c in self.categories)

    def category(self, key: str) -> Category:
        for category in self.categories:
            if category.key == key:
                return category
        raise GroupBreakdownError(
            f"dimension {self.key} has no category {key!r}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "categories": [c.as_dict() for c in self.categories],
            "definition": list(self.definition),
            "source": self.source,
            "quote_source": self.quote_source,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class CategoryScheme:
    """An ordered set of dimensions with its population and citations.

    The first dimension is the total.  ``composite`` marks a scheme this
    module composed (it is not a published table layout).
    """

    scheme_id: str
    title: str
    population: str
    dimensions: tuple[Dimension, ...]
    citations: tuple[str, ...]
    notes: tuple[str, ...] = ()
    composite: bool = False

    def __post_init__(self) -> None:
        _key(self.scheme_id, "scheme_id")
        _nonempty_text(self.title, "scheme title")
        _nonempty_text(self.population, "scheme population")
        dimensions = tuple(self.dimensions)
        if not dimensions or not all(
            isinstance(d, Dimension) for d in dimensions
        ):
            raise GroupBreakdownError(
                "a scheme needs a non-empty tuple of Dimension"
            )
        if dimensions[0].kind != TOTAL:
            raise GroupBreakdownError("a scheme's first dimension is Total")
        if sum(d.kind == TOTAL for d in dimensions) != 1:
            raise GroupBreakdownError("a scheme has exactly one total")
        keys = [d.key for d in dimensions]
        if len(set(keys)) != len(keys):
            raise GroupBreakdownError("a scheme repeats a dimension key")
        object.__setattr__(self, "dimensions", dimensions)
        citations = _string_tuple(self.citations, "scheme citations")
        if not citations:
            raise GroupBreakdownError("a scheme needs at least one citation")
        object.__setattr__(self, "citations", citations)
        object.__setattr__(
            self, "notes", _string_tuple(self.notes, "scheme notes")
        )
        if not isinstance(self.composite, bool):
            raise GroupBreakdownError("composite must be a bool")

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(d.key for d in self.dimensions)

    def dimension(self, key: str) -> Dimension:
        for dimension in self.dimensions:
            if dimension.key == key:
                return dimension
        raise GroupBreakdownError(
            f"scheme {self.scheme_id} has no dimension {key!r}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "title": self.title,
            "population": self.population,
            "composite": self.composite,
            "citations": list(self.citations),
            "notes": list(self.notes),
            "dimensions": [d.as_dict() for d in self.dimensions],
        }


# ---- MINT8 sources ---------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
MINT8_GUIDE_FILE = "data/external/mint8_table_user_guide.source.html"
MINT8_LABELS_FILE = "data/external/mint8_row_categories.json"
#: SHA-256 pins of the committed MINT8 sources (see each file's
#: ``.provenance.json``).
MINT8_SOURCE_SHA256: dict[str, str] = {
    MINT8_GUIDE_FILE: (
        "278d5d19c1b50f1d354db1ada515288af563c035a67eb16fb971d25700fb94e9"
    ),
    MINT8_LABELS_FILE: (
        "23fbfbc8dbc14b06144a83bf0583ea0a6c89505638f3f7dc5fd6b34a3a4ac650"
    ),
}
_GUIDE_URL = "https://www.ssa.gov/policy/docs/projections/user-guide.html"
_OPTION_URL = (
    "https://www.ssa.gov/policy/docs/projections/policy-options/"
    "increase-payroll-tax-rate.html"
)
MINT8_GUIDE_CITATION = (
    "Social Security Administration, 'Table User Guide—Modeling Income "
    f"in the Near Term (MINT) 8', {_GUIDE_URL}, section 'Definitions—"
    "Table Rows and Columns' > 'Characteristic Subgroups—Table Rows' "
    "(DCTERMS:dateCertified 2025-10-01); committed capture "
    f"{MINT8_GUIDE_FILE} (SHA-256 {MINT8_SOURCE_SHA256[MINT8_GUIDE_FILE]}), "
    "Internet Archive capture 20260419231110"
)


def _row_label_citation(tables: str) -> str:
    return (
        "Social Security Administration, MINT8 projected-effects tables on "
        f"the policy-option page {_OPTION_URL} (DCTERMS:dateCertified "
        f"2026-04-01), row-group headings and row labels of tables {tables} "
        "in document order, labels only (raw page SHA-256 "
        "3cfb6eb636cad6d062eb22734c533fb349a0bc4761014eee8f2ccb0eb6e28d8c, "
        "Internet Archive capture 20260519190449); committed extract "
        f"{MINT8_LABELS_FILE} (SHA-256 "
        f"{MINT8_SOURCE_SHA256[MINT8_LABELS_FILE]})"
    )


_GUIDE_SECTION = (
    "MINT8 Table User Guide, 'Definitions—Table Rows and Columns' > "
    "'Characteristic Subgroups—Table Rows'"
)

# Verbatim quotes of the MINT8 Table User Guide (checked by
# verify_mint8_sources).
_Q_TOTAL = "Total: Refers to the total population of the table."
_Q_SEX = "Sex: Female or Male."
_Q_RACE = (
    "Race/Ethnicity: We list “Hispanic or Latino, any race” first; "
    "the rest of the groups (White, Black or African American, and All "
    "other races) are non-Hispanic. Additional racial or ethnic "
    "identifications are not covered because they are not in the datasets "
    "used to build the MINT8 model."
)
_Q_COUNTRY = (
    "Country of Birth: We differentiate between the United States and "
    "other countries."
)
_Q_AGE_BENEFICIARY = (
    "The beneficiary population includes those aged 60 or older because 60 "
    "is the earliest eligibility age for any aged benefits under current "
    "law."
)
_Q_AGE_TAXPAYER = (
    "The taxpayer population includes those aged 31 or older because 31 is "
    "the earliest age in MINT for household income and poverty "
    "information."
)
_Q_MARITAL = (
    "Marital Status: Refers to the marital status in the year of analysis "
    "only. An individual's marital status can change in the future and may "
    "have been different in the past."
)
_Q_EDUCATION = (
    "Highest Education Level: Reported number of years of education."
)
_Q_POVERTY = (
    "Current-Law Poverty Status: Indicates whether the person is in a "
    "household that has income above (“above poverty”) or below "
    "(“in poverty”) the official poverty line under current law. "
    "The household income used for the official poverty measure is the "
    "same as the household income used in our results except for how asset "
    "income is counted."
)
_Q_INCOME = (
    "Current-Law Household Income Quintile: Represents an individual's "
    "annual household income under current law, including: household "
    "earnings; asset income (annuitized), which includes income from "
    "defined contribution plans (such as 401(k) accounts) and personal "
    "savings; defined benefit pensions; means-tested income; "
    "non-means-tested income; Social Security; Supplemental Security "
    "Income; and non-spousal co-residents' income."
)
_Q_INCOME_QUINTILES = (
    "We calculate the income quintiles for each year (e.g., 2030, 2050, or "
    "2070) for the population analyzed, determine the dollar thresholds for "
    "each income quintile, and assign each beneficiary to the appropriate "
    "quintile. The dollar ranges are available upon request."
)
_Q_BENEFIT_TYPE = (
    "Current-Law Benefit Type: Some Social Security benefits are based on "
    "one's own work, while others are based on the work of a current, "
    "divorced, or deceased spouse. The current-law benefit type refers to "
    "one of the following benefit types received in the specified analysis "
    "year:"
)
_Q_BENEFIT_TYPE_NOTE = (
    "Our results do not show different benefit types a beneficiary might "
    "receive under a policy option/proposal or in a different year under "
    "current law."
)
_Q_AIME = (
    "Current-Law Initial AIME Quintile: Represents an individual's average "
    "indexed monthly earnings (AIME) under current law at age 62, the "
    "earliest eligibility age for retired-worker benefits. We calculate the "
    "AIME quintiles for each birth cohort. The dollar ranges are available "
    "upon request."
)
_Q_PAYROLL = (
    "Lifetime Payroll Tax Quintile: Represents the present value of an "
    "individual's current-law payroll taxes at age 62. We calculate the "
    "payroll tax quintiles for each birth cohort. The dollar ranges are "
    "available upon request."
)
_Q_PAYROLL_SHARED = (
    "Lifetime Payroll Tax Quintile (Shared): Represents the present value "
    "of an individual's current-law payroll taxes at age 62. For married "
    "couples, the payroll taxes paid while married are shared equally "
    "between them. For never-married individuals, this is the same as the "
    "lifetime payroll tax. In any year where an individual is not married, "
    "we count only their individual payroll taxes. We calculate the "
    "quintiles for each birth cohort. The dollar ranges are available upon "
    "request."
)
_Q_PRESENT_VALUE = (
    "We use the Social Security Trust Fund interest rate to adjust benefits "
    "and taxes to their present values at age 62."
)
_Q_COHORT_FOOTNOTE = (
    "Birth cohort tables (benefit/tax ratios and initial replacement rates) "
    "do not have age or marital status breakouts."
)
_Q_DISCLOSURE = (
    "To maintain the privacy of survey respondents, our tables have "
    "built-in disclosure avoidance protections that suppress an entire "
    "characteristic subgroup if the sample size for any row in that "
    "subgroup is less than 100 individuals."
)
_Q_NUMERATOR = (
    "The numerator must have either zero cases or meet a minimum numerator "
    "threshold of 10 for the table to display it. The table would suppress "
    "any characteristic subgroup that has a percentage based on a numerator "
    "of 1–9 cases."
)
_Q_THRESHOLD = (
    "We categorize individuals as having a “decrease” in the amount "
    "being analyzed (benefits, taxes, income, etc.) when a proposal would "
    "reduce the analyzed quantity by 1% or more. Individuals are "
    "categorized as having an “increase” when a proposal would "
    "raise the analyzed quantity by 1% or more. We consider individuals "
    "with differences between −1% and 1% to be unaffected."
)
_Q_FORMULA = "(option amount − current-law amount) ÷ current-law amount"
_Q_POVERTY_PERCENT = STATISTIC_DEFINITIONS[NUMBER_POOR_PERCENT_CHANGE][
    "source_quote"
]
#: Quotes outside the dimensions that this module relies on.
MINT8_GUIDE_QUOTES: tuple[str, ...] = (
    _Q_PRESENT_VALUE,
    _Q_COHORT_FOOTNOTE,
    _Q_DISCLOSURE,
    _Q_NUMERATOR,
    _Q_THRESHOLD,
    _Q_FORMULA,
    _Q_POVERTY_PERCENT,
)


def _quintile_categories() -> tuple[Category, ...]:
    """MINT8's quintile rows in SSA's page order (Highest first)."""

    return (
        Category("highest", "Highest", rank=5),
        Category("second_highest", "Second highest", rank=4),
        Category("middle", "Middle", rank=3),
        Category("second_lowest", "Second lowest", rank=2),
        Category("lowest", "Lowest", rank=1),
    )


def _mint8(key: str, label: str, kind: str, categories, *quotes, notes=()):
    return Dimension(
        key=key,
        label=label,
        kind=kind,
        categories=tuple(categories),
        definition=tuple(quotes),
        source=_GUIDE_SECTION,
        quote_source=MINT8_GUIDE,
        notes=tuple(notes),
    )


TOTAL_DIMENSION = _mint8(
    TOTAL_KEY,
    TOTAL_LABEL,
    TOTAL,
    (Category(TOTAL_KEY, TOTAL_LABEL),),
    _Q_TOTAL,
)
SEX_DIMENSION = _mint8(
    "sex",
    "Sex",
    CATEGORICAL,
    (
        Category("female", "Female", codes=("female",)),
        Category("male", "Male", codes=("male",)),
    ),
    _Q_SEX,
)
RACE_ETHNICITY_DIMENSION = _mint8(
    "race_ethnicity",
    "Race and ethnicity",
    CATEGORICAL,
    (
        Category(
            "hispanic_any_race",
            "Hispanic or Latino, any race",
            codes=("hispanic_any_race",),
        ),
        Category(
            "white_non_hispanic",
            "White, non-Hispanic",
            codes=("white_non_hispanic",),
        ),
        Category(
            "black_non_hispanic",
            "Black or African American, non-Hispanic",
            codes=("black_non_hispanic",),
        ),
        Category(
            "other_non_hispanic",
            "All other races, non-Hispanic",
            codes=("other_non_hispanic",),
        ),
    ),
    _Q_RACE,
)
COUNTRY_OF_BIRTH_DIMENSION = _mint8(
    "country_of_birth",
    "Country of birth",
    CATEGORICAL,
    (
        Category("united_states", "United States", codes=("united_states",)),
        Category(
            "other_countries", "Other countries", codes=("other_countries",)
        ),
    ),
    _Q_COUNTRY,
)
_AGE_NOTES = (
    "age is the integer in the caller's age column; the G3 brief defines "
    "it as age in the analysis year (the Guide states each population's "
    "age floor, not the date at which age is measured)",
    "an age outside every band is unclassified for this dimension and "
    "still enters Total",
)
MINT8_BENEFICIARY_AGE = _mint8(
    "age",
    "Age",
    BAND,
    (
        Category("age_60_69", "60–69", lower=60, upper=69),
        Category("age_70_79", "70–79", lower=70, upper=79),
        Category("age_80_89", "80–89", lower=80, upper=89),
        Category("age_90_plus", "90 or older", lower=90),
    ),
    _Q_AGE_BENEFICIARY,
    notes=_AGE_NOTES,
)
MINT8_TAXPAYER_AGE = _mint8(
    "age",
    "Age",
    BAND,
    (
        Category("age_31_39", "31–39", lower=31, upper=39),
        Category("age_40_49", "40–49", lower=40, upper=49),
        Category("age_50_59", "50–59", lower=50, upper=59),
        Category("age_60_69", "60–69", lower=60, upper=69),
        Category("age_70_plus", "70 or older", lower=70),
    ),
    _Q_AGE_TAXPAYER,
    notes=_AGE_NOTES,
)


def _a7_band_key(label: str) -> str:
    return "age_" + label.replace("+", "_plus").replace("-", "_")


#: Exercises 1 and 3's registered age groups, from cola_age_profile.
DYNASIM3_EXERCISES_1_3_AGE = Dimension(
    key="age",
    label="Age",
    kind=BAND,
    categories=tuple(
        Category(
            _a7_band_key(group.label),
            group.label,
            lower=group.lower,
            upper=group.upper,
        )
        for group in a7.DEFAULT_AGE_GROUPS
    ),
    source=(
        "estimates/cola_age_profile.py DEFAULT_AGE_GROUPS: the registered "
        "age groups of exercise 1 (A1 section 9) and exercise 3 (E1), with "
        "age = 2030 - birth year"
    ),
    notes=(
        "age is the integer in the caller's age column; to reproduce the "
        "registered groups pass reference_year - birth_year (the "
        "cola_age_profile age rule)",
        "an age under 50 is unclassified for this dimension and still "
        "enters Total",
    ),
)
MARITAL_STATUS_DIMENSION = _mint8(
    "marital_status",
    "Marital status",
    CATEGORICAL,
    (
        Category("married", "Married", codes=("married",)),
        Category("divorced", "Divorced", codes=("divorced",)),
        Category("widowed", "Widowed", codes=("widowed",)),
        Category("never_married", "Never married", codes=("never_married",)),
    ),
    _Q_MARITAL,
    notes=(
        "SSA does not say where separated people go: a 'separated' code is "
        "refused unless the caller maps it to a category upstream or "
        "declares it unclassified (cohorts/psid2010.marital_state_at counts "
        "separated as married by default, separated_is_married=True)",
    ),
)
EDUCATION_DIMENSION = _mint8(
    "education",
    "Highest education level",
    BAND,
    (
        Category(
            "graduate",
            "Graduate",
            lower=17,
            definition="Graduate means more than 16 years of education",
        ),
        Category(
            "bachelor",
            "Bachelor",
            lower=16,
            upper=16,
            definition="Bachelor means 16 years of education",
        ),
        Category(
            "associate",
            "Associate",
            lower=14,
            upper=15,
            definition="Associate means 14–15 years of education",
        ),
        Category(
            "high_school",
            "High school",
            lower=12,
            upper=13,
            definition="High school means 12–13 years of education",
        ),
        Category(
            "less_than_high_school",
            "Less than high school",
            upper=11,
            definition=(
                "Less than high school means less than 12 years of education"
            ),
        ),
    ),
    _Q_EDUCATION,
    notes=(
        "years of education must be integers; a non-integer value is "
        "refused",
    ),
)
POVERTY_STATUS_DIMENSION = _mint8(
    "poverty_status",
    "Current-law poverty status",
    CATEGORICAL,
    (
        Category("above_poverty", "Above poverty", codes=("above_poverty",)),
        Category("in_poverty", "In poverty", codes=("in_poverty",)),
    ),
    _Q_POVERTY,
)
HOUSEHOLD_INCOME_QUINTILE_DIMENSION = _mint8(
    "household_income_quintile",
    "Current-law household income quintile",
    QUINTILE,
    _quintile_categories(),
    _Q_INCOME,
    _Q_INCOME_QUINTILES,
    notes=(QUINTILE_RULE,),
)
BENEFIT_TYPE_DIMENSION = _mint8(
    "benefit_type",
    "Current-law benefit type",
    CATEGORICAL,
    (
        Category(
            "retired_worker_only",
            "Retired worker only",
            codes=("retired_worker_only",),
            definition=(
                "Retired-worker only: receives only a retired-worker benefit "
                "based on his or her earnings record."
            ),
        ),
        Category(
            "widower",
            "Widow(er) (includes dually entitled)",
            codes=("widower",),
            definition=(
                "Widow(er) (includes dually entitled): receives a survivor "
                "benefit (may or may not also receive a lower worker benefit "
                "from his or her own earnings record, known as dually "
                "entitled)."
            ),
        ),
        Category(
            "spousal",
            "Spousal (includes dually entitled)",
            codes=("spousal",),
            definition=(
                "Spousal (includes dually entitled): receives a spousal "
                "benefit (may or may not also receive a lower worker benefit "
                "from his or her own earnings record, known as dually "
                "entitled)."
            ),
        ),
        Category(
            "disabled_worker_only",
            "Disabled worker only",
            codes=("disabled_worker_only",),
            definition=(
                "Disabled-worker only: receives a disabled-worker benefit on "
                "his or her earnings record and is under the full retirement "
                "age (FRA). Disabled workers convert to retired workers at "
                "FRA."
            ),
        ),
    ),
    _Q_BENEFIT_TYPE,
    _Q_BENEFIT_TYPE_NOTE,
)
_LIFETIME_NOTES = (
    QUINTILE_RULE,
    "the measure itself (AIME at 62, or the present value at 62 of "
    "current-law payroll taxes, own or shared) is computed upstream by "
    "cohort code; this module only cuts its quintiles",
)
INITIAL_AIME_QUINTILE_DIMENSION = _mint8(
    "initial_aime_quintile",
    "Current-law initial AIME quintile",
    QUINTILE,
    _quintile_categories(),
    _Q_AIME,
    notes=_LIFETIME_NOTES,
)
LIFETIME_PAYROLL_TAX_QUINTILE_DIMENSION = _mint8(
    "lifetime_payroll_tax_quintile",
    "Lifetime payroll tax quintile",
    QUINTILE,
    _quintile_categories(),
    _Q_PAYROLL,
    _Q_PRESENT_VALUE,
    notes=_LIFETIME_NOTES,
)
LIFETIME_PAYROLL_TAX_QUINTILE_SHARED_DIMENSION = _mint8(
    "lifetime_payroll_tax_quintile_shared",
    "Lifetime payroll tax quintile (shared)",
    QUINTILE,
    _quintile_categories(),
    _Q_PAYROLL_SHARED,
    _Q_PRESENT_VALUE,
    notes=_LIFETIME_NOTES,
)
LIFETIME_DIMENSIONS = (
    INITIAL_AIME_QUINTILE_DIMENSION,
    LIFETIME_PAYROLL_TAX_QUINTILE_DIMENSION,
    LIFETIME_PAYROLL_TAX_QUINTILE_SHARED_DIMENSION,
)

#: Age-band dimensions a scheme's ``age`` dimension can be swapped for.
AGE_BAND_SETS: dict[str, Dimension] = {
    "mint8_beneficiary": MINT8_BENEFICIARY_AGE,
    "mint8_taxpayer": MINT8_TAXPAYER_AGE,
    "dynasim3_exercises_1_3": DYNASIM3_EXERCISES_1_3_AGE,
}

_BENEFICIARY_POPULATION = (
    "MINT8: current-law beneficiaries aged 60 or older in the analysis year "
    "(2030, 2050, 2070); a blind test's own population is the caller's rows"
)
MINT8_SCHEME = CategoryScheme(
    scheme_id="mint8_beneficiary_annual",
    title=(
        "MINT8 projected effects on Social Security benefits and household "
        "income (tables 1-3 and 7-9)"
    ),
    population=_BENEFICIARY_POPULATION,
    dimensions=(
        TOTAL_DIMENSION,
        SEX_DIMENSION,
        RACE_ETHNICITY_DIMENSION,
        COUNTRY_OF_BIRTH_DIMENSION,
        MINT8_BENEFICIARY_AGE,
        MARITAL_STATUS_DIMENSION,
        EDUCATION_DIMENSION,
        POVERTY_STATUS_DIMENSION,
        HOUSEHOLD_INCOME_QUINTILE_DIMENSION,
        BENEFIT_TYPE_DIMENSION,
    ),
    citations=(MINT8_GUIDE_CITATION, _row_label_citation("1-3 and 7-9")),
)
MINT8_POVERTY_SCHEME = CategoryScheme(
    scheme_id="mint8_beneficiary_poverty",
    title=(
        "MINT8 projected effects on the official poverty measure (tables "
        "10-12)"
    ),
    population=_BENEFICIARY_POPULATION,
    dimensions=tuple(
        d
        for d in MINT8_SCHEME.dimensions
        if d.key != HOUSEHOLD_INCOME_QUINTILE_DIMENSION.key
    ),
    citations=(MINT8_GUIDE_CITATION, _row_label_citation("10-12")),
    notes=(
        "MINT8's official-poverty tables carry no household income "
        "quintile rows (row labels of tables 10-12)",
    ),
)
MINT8_COHORT_SCHEME = CategoryScheme(
    scheme_id="mint8_cohort",
    title=(
        "MINT8 projected effects on benefit/tax ratios and initial "
        "replacement rates (tables 13-20)"
    ),
    population=(
        "MINT8: workers with a benefit/tax ratio, or current-law "
        "beneficiaries with an initial replacement rate, born 1960–1969, "
        "1980–1989, 2000–2009 or 2020–2029"
    ),
    dimensions=(
        TOTAL_DIMENSION,
        SEX_DIMENSION,
        RACE_ETHNICITY_DIMENSION,
        COUNTRY_OF_BIRTH_DIMENSION,
        EDUCATION_DIMENSION,
        *LIFETIME_DIMENSIONS,
    ),
    citations=(MINT8_GUIDE_CITATION, _row_label_citation("13-20")),
    notes=(_Q_COHORT_FOOTNOTE,),
)
_LIFETIME_COMPOSITE_NOTE = (
    "composite of this module: MINT8's annual tables carry no "
    "lifetime-earnings dimension, so the three quintile measures of MINT8's "
    "cohort tables (tables 13-20) are appended as the lifetime-earnings "
    "dimension the NASI request names (G3 brief, 2026-10-01); MINT8 cuts "
    "them per birth cohort, and the caller names the partitions"
)
MINT8_ANNUAL_WITH_LIFETIME_SCHEME = CategoryScheme(
    scheme_id="mint8_beneficiary_annual_with_lifetime",
    title=f"{MINT8_SCHEME.title}, with MINT8's lifetime-earnings quintiles",
    population=_BENEFICIARY_POPULATION,
    dimensions=(*MINT8_SCHEME.dimensions, *LIFETIME_DIMENSIONS),
    citations=(
        MINT8_GUIDE_CITATION,
        _row_label_citation("1-3 and 7-9"),
        _row_label_citation("13-20"),
    ),
    notes=(_LIFETIME_COMPOSITE_NOTE,),
    composite=True,
)
MINT8_POVERTY_WITH_LIFETIME_SCHEME = CategoryScheme(
    scheme_id="mint8_beneficiary_poverty_with_lifetime",
    title=(
        f"{MINT8_POVERTY_SCHEME.title}, with MINT8's lifetime-earnings "
        "quintiles"
    ),
    population=_BENEFICIARY_POPULATION,
    dimensions=(*MINT8_POVERTY_SCHEME.dimensions, *LIFETIME_DIMENSIONS),
    citations=(
        MINT8_GUIDE_CITATION,
        _row_label_citation("10-12"),
        _row_label_citation("13-20"),
    ),
    notes=(*MINT8_POVERTY_SCHEME.notes, _LIFETIME_COMPOSITE_NOTE),
    composite=True,
)
#: Which label-file tables each MINT8 scheme reproduces exactly
#: (:func:`verify_mint8_sources`).
MINT8_SCHEME_TABLES: dict[str, tuple[str, ...]] = {
    MINT8_SCHEME.scheme_id: ("1", "2", "3", "7", "8", "9"),
    MINT8_POVERTY_SCHEME.scheme_id: ("10", "11", "12"),
    MINT8_COHORT_SCHEME.scheme_id: tuple(str(n) for n in range(13, 21)),
}
#: Composite MINT8 schemes: (base scheme, appended-dimension tables).
MINT8_COMPOSITES: dict[str, tuple[str, str]] = {
    MINT8_ANNUAL_WITH_LIFETIME_SCHEME.scheme_id: (
        MINT8_SCHEME.scheme_id,
        "13",
    ),
    MINT8_POVERTY_WITH_LIFETIME_SCHEME.scheme_id: (
        MINT8_POVERTY_SCHEME.scheme_id,
        "13",
    ),
}

# ---- registry -------------------------------------------------------------
_REGISTRY: dict[str, CategoryScheme] = {}


def register_scheme(
    scheme: CategoryScheme, *, replace: bool = False
) -> CategoryScheme:
    """Register an alternate scheme under its ``scheme_id``.

    An id already registered is refused unless ``replace`` is true; the
    MINT8 schemes this module defines can never be replaced.
    """

    if not isinstance(scheme, CategoryScheme):
        raise GroupBreakdownError("register_scheme needs a CategoryScheme")
    existing = _REGISTRY.get(scheme.scheme_id)
    if existing is not None and existing is not scheme:
        if not replace or scheme.scheme_id in _BUILTIN_IDS:
            raise GroupBreakdownError(
                f"scheme {scheme.scheme_id!r} is already registered"
            )
    _REGISTRY[scheme.scheme_id] = scheme
    return scheme


def get_scheme(scheme_id: str) -> CategoryScheme:
    """The registered scheme ``scheme_id``."""

    try:
        return _REGISTRY[scheme_id]
    except KeyError as error:
        raise GroupBreakdownError(
            f"no registered scheme {scheme_id!r}; registered: "
            f"{sorted(_REGISTRY)}"
        ) from error


def registered_scheme_ids() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def derive_scheme(
    base: CategoryScheme,
    *,
    scheme_id: str,
    title: str,
    replace: Mapping[str, Dimension] | None = None,
    append: Sequence[Dimension] = (),
    drop: Sequence[str] = (),
    population: str | None = None,
    citations: Sequence[str] = (),
    notes: Sequence[str] = (),
) -> CategoryScheme:
    """A composite variant of ``base`` (not registered).

    ``replace`` maps an existing dimension key to its replacement (which
    must keep the key), ``drop`` removes dimensions (never the total) and
    ``append`` adds dimensions at the end.  Citations and notes are
    appended to the base's; the result is marked ``composite``.
    """

    if not isinstance(base, CategoryScheme):
        raise GroupBreakdownError("derive_scheme needs a CategoryScheme")
    replace = dict(replace or {})
    for key, dimension in replace.items():
        base.dimension(key)
        if not isinstance(dimension, Dimension) or dimension.key != key:
            raise GroupBreakdownError(
                f"the replacement for {key!r} must be a Dimension with that "
                "key"
            )
    drop = tuple(drop)
    for key in drop:
        if key == TOTAL_KEY:
            raise GroupBreakdownError("the total dimension cannot be dropped")
        base.dimension(key)
    dimensions = [
        replace.get(d.key, d) for d in base.dimensions if d.key not in drop
    ]
    dimensions.extend(append)
    return CategoryScheme(
        scheme_id=scheme_id,
        title=title,
        population=base.population if population is None else population,
        dimensions=tuple(dimensions),
        citations=(*base.citations, *_string_tuple(citations, "citations")),
        notes=(*base.notes, *_string_tuple(notes, "notes")),
        composite=True,
    )


def with_age_bands(
    base: CategoryScheme,
    band_set: str,
    *,
    scheme_id: str | None = None,
) -> CategoryScheme:
    """``base`` with its ``age`` dimension replaced by an age-band set."""

    if band_set not in AGE_BAND_SETS:
        raise GroupBreakdownError(
            f"band_set must be one of {sorted(AGE_BAND_SETS)}"
        )
    bands = AGE_BAND_SETS[band_set]
    return derive_scheme(
        base,
        scheme_id=scheme_id or f"{base.scheme_id}__{band_set}_age",
        title=f"{base.title}, age bands {list(bands.labels)}",
        replace={"age": bands},
        citations=(bands.source,) if bands.quote_source is None else (),
        notes=(
            f"age bands replaced by the {band_set!r} set: "
            f"{list(bands.labels)}",
        ),
    )


_BUILTIN_SCHEMES = (
    MINT8_SCHEME,
    MINT8_POVERTY_SCHEME,
    MINT8_COHORT_SCHEME,
    MINT8_ANNUAL_WITH_LIFETIME_SCHEME,
    MINT8_POVERTY_WITH_LIFETIME_SCHEME,
)
_BUILTIN_IDS = frozenset(s.scheme_id for s in _BUILTIN_SCHEMES)
for _scheme in _BUILTIN_SCHEMES:
    register_scheme(_scheme)
del _scheme


# =========================================================================
# MINT8 source verification
# =========================================================================
class _GuideText(HTMLParser):
    """The visible text of the committed Guide (scripts and styles left
    out), whitespace-normalized by :func:`_guide_text`."""

    _BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "br", "div", "tr", "td"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        if tag in self._BLOCKS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _guide_text(raw: bytes) -> str:
    parser = _GuideText()
    parser.feed(raw.decode("utf-8"))
    return _normalize_whitespace("".join(parser.parts))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dimension_quotes(scheme: CategoryScheme) -> list[str]:
    quotes = []
    for dimension in scheme.dimensions:
        if dimension.quote_source != MINT8_GUIDE:
            continue
        quotes.extend(dimension.definition)
        quotes.extend(
            c.definition for c in dimension.categories if c.definition
        )
    return quotes


def _table_groups(table: Mapping[str, Any]) -> list[tuple[str, list[str]]]:
    return [(g["group"], list(g["labels"])) for g in table["groups"]]


def _scheme_groups(
    dimensions: Iterable[Dimension],
) -> list[tuple[str, list[str]]]:
    return [
        (d.label, [] if d.kind == TOTAL else list(d.labels))
        for d in dimensions
    ]


def verify_mint8_sources(root: Path | str | None = None) -> dict[str, Any]:
    """Check the MINT8 schemes against the committed sources.

    Verifies both files' SHA-256 pins; that each MINT8 scheme's row-group
    headings and row labels equal, verbatim and in order, those of every
    label-file table it stands for (:data:`MINT8_SCHEME_TABLES`); that each
    composite scheme is its base plus dimensions of the cohort tables; and
    that every MINT8 definition quote appears verbatim (whitespace
    normalized) in the Guide's text.  Raises :class:`GroupBreakdownError`
    on the first mismatch; returns a record of what was checked.
    """

    base = _PROJECT_ROOT if root is None else Path(root)
    hashes = {}
    for relative, expected in MINT8_SOURCE_SHA256.items():
        actual = _sha256(base / relative)
        if actual != expected:
            raise GroupBreakdownError(
                f"{relative} SHA-256 {actual} differs from the pin {expected}"
            )
        hashes[relative] = actual
    labels = json.loads((base / MINT8_LABELS_FILE).read_text("utf-8"))
    tables = labels["tables"]
    checked: dict[str, list[str]] = {}
    for scheme_id, numbers in MINT8_SCHEME_TABLES.items():
        expected_groups = _scheme_groups(get_scheme(scheme_id).dimensions)
        for number in numbers:
            if _table_groups(tables[number]) != expected_groups:
                raise GroupBreakdownError(
                    f"scheme {scheme_id} differs from label-file table "
                    f"{number}"
                )
        checked[scheme_id] = list(numbers)
    for scheme_id, (base_id, extra_table) in MINT8_COMPOSITES.items():
        scheme = get_scheme(scheme_id)
        base_scheme = get_scheme(base_id)
        n_base = len(base_scheme.dimensions)
        if scheme.dimensions[:n_base] != base_scheme.dimensions:
            raise GroupBreakdownError(
                f"composite {scheme_id} does not start with {base_id}"
            )
        cohort_groups = _table_groups(tables[extra_table])
        for group in _scheme_groups(scheme.dimensions[n_base:]):
            if group not in cohort_groups:
                raise GroupBreakdownError(
                    f"composite {scheme_id} appends {group[0]!r}, which "
                    f"label-file table {extra_table} does not carry"
                )
        checked[scheme_id] = [f"{base_id} + table {extra_table}"]
    text = _guide_text((base / MINT8_GUIDE_FILE).read_bytes())
    quotes = list(MINT8_GUIDE_QUOTES)
    for scheme in _BUILTIN_SCHEMES:
        quotes.extend(_dimension_quotes(scheme))
    for band in AGE_BAND_SETS.values():
        if band.quote_source == MINT8_GUIDE:
            quotes.extend(band.definition)
    unique = list(dict.fromkeys(quotes))
    for quote in unique:
        if _normalize_whitespace(quote) not in text:
            raise GroupBreakdownError(
                f"quote not found verbatim in the MINT8 Guide: {quote!r}"
            )
    return {
        "files_sha256": hashes,
        "schemes_checked": checked,
        "n_quotes_checked": len(unique),
    }


# =========================================================================
# Weighted percentiles, quintiles and change classes
# =========================================================================
def _exact_numerators(weights: np.ndarray) -> np.ndarray:
    """Each float64 weight as an exact integer over one common
    power-of-two denominator (an object array of Python ints)."""

    ratios = [float(w).as_integer_ratio() for w in weights.tolist()]
    out = np.empty(len(ratios), dtype=object)
    if ratios:
        common = max(den for _, den in ratios)
        out[:] = [num * (common // den) for num, den in ratios]
    return out


def _midpoint(a: float, b: float) -> float:
    if a == b:
        return a
    middle = (a + b) / 2.0
    if not math.isfinite(middle):
        middle = a / 2.0 + b / 2.0
    return middle


def _percentiles_of(
    values: np.ndarray,
    numerators: np.ndarray,
    levels: Sequence[Fraction],
) -> list[float]:
    """The percentile rule on positive-numerator rows (none empty)."""

    order = np.argsort(values, kind="stable")
    ordered = values[order]
    cumulative = list(itertools.accumulate(numerators[order].tolist()))
    total = cumulative[-1]
    out = []
    for level in levels:
        target = level.numerator * total
        threshold = -(-target // level.denominator)
        k = bisect.bisect_left(cumulative, threshold)
        value = float(ordered[k])
        tie = cumulative[k] * level.denominator == target
        if tie and k + 1 < len(cumulative):
            value = _midpoint(value, float(ordered[k + 1]))
        out.append(value)
    return out


def _levels(levels: Iterable[Any]) -> tuple[Fraction, ...]:
    out = tuple(levels)
    if not out:
        raise GroupBreakdownError("percentile levels must not be empty")
    for level in out:
        if not isinstance(level, Fraction) or not 0 < level < 1:
            raise GroupBreakdownError(
                "percentile levels must be fractions.Fraction in (0, 1), "
                f"not {level!r} (exact levels keep exact ties exact)"
            )
    return out


def _real_array(values: Any, label: str) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype == bool or array.ndim != 1:
        raise GroupBreakdownError(f"{label} must be a 1-D numeric sequence")
    try:
        array = array.astype(np.float64)
    except (TypeError, ValueError) as error:
        raise GroupBreakdownError(f"{label} must be numeric") from error
    if not np.all(np.isfinite(array)):
        raise GroupBreakdownError(f"{label} must be finite")
    return array


def weighted_percentiles(
    values: Any, weights: Any, levels: Sequence[Fraction]
) -> list[float]:
    """The weighted percentiles of ``values`` at ``levels``.

    The rule is :data:`PERCENTILE_DEFINITION`.  ``weights`` must be finite,
    non-negative and not all zero; ``levels`` are
    :class:`fractions.Fraction` in (0, 1).
    """

    values = _real_array(values, "values")
    weights = _real_array(weights, "weights")
    if values.size == 0 or values.size != weights.size:
        raise GroupBreakdownError(
            "values and weights must be non-empty and the same length"
        )
    if (weights < 0).any():
        raise GroupBreakdownError("weights must be non-negative")
    keep = weights > 0
    if not keep.any():
        raise GroupBreakdownError("weights must not all be zero")
    return _percentiles_of(
        values[keep], _exact_numerators(weights[keep]), _levels(levels)
    )


def weighted_quintile_ranks(
    values: Any, weights: Any
) -> tuple[np.ndarray, list[float]]:
    """Each value's quintile rank (1 lowest, 5 highest) and the thresholds.

    The rule is :data:`QUINTILE_RULE`: thresholds are the weighted
    percentiles at 1/5 ... 4/5 and a value equal to a threshold falls in
    the lower quintile.  Zero-weight rows are ranked but do not move the
    thresholds.
    """

    array = _real_array(values, "values")
    thresholds = weighted_percentiles(array, weights, QUINTILE_LEVELS)
    ranks = 1 + (array[:, None] > np.asarray(thresholds)[None, :]).sum(axis=1)
    return ranks.astype(np.int64), thresholds


#: A change this close to a +-1 percent threshold is classified exactly.
_CHANGE_MARGIN = 1e-9


def classify_changes(
    base: Any, reform: Any
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Individual percent changes and MINT8's change classes.

    Returns ``(population, change, decrease, increase)``: ``population`` is
    ``base > 0``; ``change`` is ``100 * (reform / base - 1)`` there and NaN
    elsewhere; ``decrease`` and ``increase`` follow
    :data:`CHANGE_DEFINITION`, decided exactly (rational arithmetic on the
    float64 amounts) for every change within ``1e-9`` of a threshold.
    """

    base = _real_array(base, "base amounts")
    reform = _real_array(reform, "reform amounts")
    if base.size != reform.size:
        raise GroupBreakdownError("base and reform amounts differ in length")
    if (base < 0).any() or (reform < 0).any():
        raise GroupBreakdownError("benefit amounts must be non-negative")
    population = base > 0
    change = np.full(base.size, np.nan)
    with np.errstate(over="ignore", invalid="ignore"):
        change[population] = 100.0 * (
            reform[population] / base[population] - 1.0
        )
    if not np.all(np.isfinite(change[population])):
        raise GroupBreakdownError("a percent change overflows float64")
    decrease = population & (change <= -1.0)
    increase = population & (change >= 1.0)
    near = population & (
        (np.abs(change + 1.0) <= _CHANGE_MARGIN)
        | (np.abs(change - 1.0) <= _CHANGE_MARGIN)
    )
    for index in np.flatnonzero(near):
        b_num, b_den = float(base[index]).as_integer_ratio()
        r_num, r_den = float(reform[index]).as_integer_ratio()
        scaled_reform = 100 * r_num * b_den
        decrease[index] = scaled_reform <= 99 * b_num * r_den
        increase[index] = scaled_reform >= 101 * b_num * r_den
    return population, change, decrease, increase


# =========================================================================
# Group assignment
# =========================================================================
def _is_missing(value: Any) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, float | np.floating):
        return math.isnan(value)
    return False


def _plain(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def _key_digest(frame: pd.DataFrame, key_columns: tuple[str, ...]) -> str:
    keys = []
    for row in frame[list(key_columns)].itertuples(index=False, name=None):
        if any(_is_missing(v) for v in row):
            raise GroupBreakdownError(
                f"key columns {list(key_columns)} must not be missing"
            )
        keys.append(tuple(_plain(v) for v in row))
    if len(set(keys)) != len(keys):
        raise GroupBreakdownError(
            f"key columns {list(key_columns)} must identify each row"
        )
    return hashlib.sha256(repr(keys).encode("utf-8")).hexdigest()


def _band_value(value: Any, label: str) -> int:
    if isinstance(value, bool | np.bool_):
        raise GroupBreakdownError(f"{label}: a boolean is not a band value")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real) and math.isfinite(float(value)):
        if float(value).is_integer():
            return int(value)
    raise GroupBreakdownError(
        f"{label}: band values must be integers; got {value!r}"
    )


def _measure_value(value: Any, label: str) -> float:
    if isinstance(value, bool | np.bool_) or not isinstance(value, Real):
        raise GroupBreakdownError(f"{label}: measures must be real numbers")
    number = float(value)
    if not math.isfinite(number):
        raise GroupBreakdownError(f"{label}: measures must be finite")
    return number


@dataclass(frozen=True, eq=False)
class GroupAssignment:
    """Each row's category per dimension of a scheme.

    ``long`` has one row per (``row_id``, ``dimension``) with ``label``
    (the category's printed label, or ``unclassified``), ``category`` (its
    key, or ``unclassified``) and ``classified``.  ``row_id`` is the
    row's position in the frame passed to :func:`assign_groups`, and
    ``key_digest`` fingerprints its ``key_columns`` so a tabulator can
    refuse changed row identities or order.  Classifications are a fixed
    snapshot: recreate the assignment to change attributes, quintile
    partitions or quintile thresholds.  Tabulators can use the snapshot
    with alternative outcome columns or analysis weights for those same
    identified rows; they do not recompute classifications.
    """

    scheme: CategoryScheme
    n_rows: int
    key_columns: tuple[str, ...]
    key_digest: str
    columns: Mapping[str, str]
    weight_column: str | None
    quintile_partition: tuple[str, ...]
    quintile_partitions: Mapping[str, tuple[str, ...]]
    long: pd.DataFrame
    dimension_summaries: tuple[Mapping[str, Any], ...]
    _category_index: Mapping[str, np.ndarray]

    def _codes(self, dimension: str) -> np.ndarray:
        try:
            return self._category_index[dimension]
        except KeyError as error:
            raise GroupBreakdownError(
                f"scheme {self.scheme.scheme_id} has no dimension "
                f"{dimension!r}"
            ) from error

    def mask(self, dimension: str, category: str) -> np.ndarray:
        """The rows of ``category`` (a key) in ``dimension``."""

        self.scheme.dimension(dimension).category(category)
        return self._codes(dimension) == category

    def unclassified_mask(self, dimension: str) -> np.ndarray:
        return self._codes(dimension) == UNCLASSIFIED

    def as_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "scheme_id": self.scheme.scheme_id,
                "n_rows": self.n_rows,
                "key_columns": list(self.key_columns),
                "key_digest": self.key_digest,
                "columns": dict(self.columns),
                "weight_column": self.weight_column,
                "quintile_partition": list(self.quintile_partition),
                "quintile_partitions": {
                    key: list(columns)
                    for key, columns in self.quintile_partitions.items()
                },
                "unclassified_rule": UNCLASSIFIED_RULE,
                "dimensions": [dict(s) for s in self.dimension_summaries],
            }
        )


def _categorical_codes(
    dimension: Dimension,
    values: list[Any],
    extra: frozenset[str],
    column: str,
) -> tuple[np.ndarray, dict[str, int]]:
    lookup = {
        code: category.key
        for category in dimension.categories
        for code in category.codes
    }
    out = np.empty(len(values), dtype=object)
    reasons: dict[str, int] = {}
    for index, value in enumerate(values):
        if _is_missing(value):
            reason = MISSING_REASON
        elif not isinstance(value, str):
            raise GroupBreakdownError(
                f"column {column!r} ({dimension.key}) row {index}: codes "
                f"must be strings or missing; got {value!r}"
            )
        elif value in lookup:
            out[index] = lookup[value]
            continue
        elif value in extra:
            reason = f"code:{value}"
        else:
            raise GroupBreakdownError(
                f"column {column!r} ({dimension.key}) row {index}: code "
                f"{value!r} is in no category and was not declared "
                "unclassified"
            )
        out[index] = UNCLASSIFIED
        reasons[reason] = reasons.get(reason, 0) + 1
    return out, reasons


def _band_codes(
    dimension: Dimension, values: list[Any], column: str
) -> tuple[np.ndarray, dict[str, int]]:
    out = np.empty(len(values), dtype=object)
    reasons: dict[str, int] = {}
    for index, value in enumerate(values):
        reason = None
        if _is_missing(value):
            reason = MISSING_REASON
        else:
            number = _band_value(
                value, f"column {column!r} ({dimension.key}) row {index}"
            )
            hits = [c.key for c in dimension.categories if c.contains(number)]
            if hits:
                out[index] = hits[0]
            else:
                reason = OUTSIDE_BANDS_REASON
        if reason is not None:
            out[index] = UNCLASSIFIED
            reasons[reason] = reasons.get(reason, 0) + 1
    return out, reasons


def _quintile_codes(
    dimension: Dimension,
    frame: pd.DataFrame,
    column: str,
    weights: np.ndarray,
    partition: tuple[str, ...],
) -> tuple[np.ndarray, dict[str, int], list[dict[str, Any]]]:
    values = frame[column].tolist()
    present = np.zeros(len(values), dtype=bool)
    numbers = np.zeros(len(values), dtype=np.float64)
    for index, value in enumerate(values):
        if _is_missing(value):
            continue
        numbers[index] = _measure_value(
            value, f"column {column!r} ({dimension.key}) row {index}"
        )
        present[index] = True
    if partition:
        keys = list(frame[list(partition)].itertuples(index=False, name=None))
    else:
        keys = [()] * len(values)
    groups: dict[tuple, list[int]] = {}
    for index, key in enumerate(keys):
        if present[index]:
            plain = tuple(_plain(v) for v in key)
            groups.setdefault(plain, []).append(index)
    by_rank = {c.rank: c.key for c in dimension.categories}
    out = np.empty(len(values), dtype=object)
    out[:] = UNCLASSIFIED
    records = []
    for key, members in groups.items():
        index = np.asarray(members, dtype=np.int64)
        member_weights = weights[index]
        if not (member_weights > 0).any():
            raise GroupBreakdownError(
                f"{dimension.key}: partition "
                f"{dict(zip(partition, key, strict=True))} has no positive "
                "weight, so its quintile thresholds are undefined"
            )
        ranks, thresholds = weighted_quintile_ranks(
            numbers[index], member_weights
        )
        for row, rank in zip(index.tolist(), ranks.tolist(), strict=True):
            out[row] = by_rank[rank]
        records.append(
            {
                "partition": dict(zip(partition, key, strict=True)),
                "n_rows": int(index.size),
                "n_positive_weight": int((member_weights > 0).sum()),
                "weighted_n": math.fsum(member_weights.tolist()),
                "thresholds": thresholds,
            }
        )
    n_missing = int((~present).sum())
    reasons = {MISSING_REASON: n_missing} if n_missing else {}
    return out, reasons, records


def assign_groups(
    frame: pd.DataFrame,
    scheme: CategoryScheme,
    columns_map: Mapping[str, str],
    *,
    key_columns: Sequence[str],
    weight_column: str | None = "weight",
    quintile_partition: Sequence[str] = (),
    quintile_partitions: Mapping[str, Sequence[str]] | None = None,
    unclassified_codes: Mapping[str, Sequence[str]] | None = None,
) -> GroupAssignment:
    """Assign every row of ``frame`` to one category per dimension.

    ``columns_map`` maps each non-total dimension key of ``scheme`` to the
    column holding its attribute: codes (categorical), integers (band) or
    a numeric measure (quintile).  ``key_columns`` identify each row (for
    example ``("draw", "person_id")`` for projection rows);
    ``weight_column`` gives the weights quintile thresholds use (required
    only when the scheme has a quintile dimension); ``quintile_partition``
    names the columns within whose values quintiles are cut separately;
    ``quintile_partitions`` overrides those columns per dimension, for
    example household income within each draw/year and lifetime payroll
    taxes within each draw/birth cohort in a composite scheme;
    ``unclassified_codes`` declares, per categorical dimension, present
    codes that are unclassified.  See :data:`UNCLASSIFIED_RULE`.
    """

    if not isinstance(frame, pd.DataFrame):
        raise GroupBreakdownError("frame must be a DataFrame")
    if not frame.columns.is_unique:
        raise GroupBreakdownError("frame has repeated column names")
    if frame.empty:
        raise GroupBreakdownError("frame has no rows")
    if not isinstance(scheme, CategoryScheme):
        raise GroupBreakdownError("scheme must be a CategoryScheme")
    if not isinstance(columns_map, Mapping):
        raise GroupBreakdownError("columns_map must be a mapping")
    needed = {d.key for d in scheme.dimensions if d.kind != TOTAL}
    unknown = sorted(set(columns_map) - needed)
    missing = sorted(needed - set(columns_map))
    if unknown or missing:
        raise GroupBreakdownError(
            f"columns_map must name exactly the scheme's non-total "
            f"dimensions; unknown {unknown}, missing {missing}"
        )
    for dimension, column in columns_map.items():
        if column not in frame.columns:
            raise GroupBreakdownError(
                f"column {column!r} for {dimension} is not in the frame"
            )
    key_columns = _string_tuple(key_columns, "key_columns")
    if not key_columns:
        raise GroupBreakdownError("key_columns must not be empty")
    absent = [c for c in key_columns if c not in frame.columns]
    if absent:
        raise GroupBreakdownError(f"key columns {absent} are not in frame")
    frame = frame.reset_index(drop=True)
    digest = _key_digest(frame, key_columns)
    partition = _string_tuple(quintile_partition, "quintile_partition")
    absent = [c for c in partition if c not in frame.columns]
    if absent:
        raise GroupBreakdownError(f"partition columns {absent} are absent")
    if partition and frame[list(partition)].isna().any(axis=None):
        raise GroupBreakdownError("partition columns must not be missing")
    if quintile_partitions is not None and not isinstance(
        quintile_partitions, Mapping
    ):
        raise GroupBreakdownError("quintile_partitions must be a mapping")
    partitions = {
        d.key: partition for d in scheme.dimensions if d.kind == QUINTILE
    }
    for key, columns in (quintile_partitions or {}).items():
        dimension = scheme.dimension(key)
        if dimension.kind != QUINTILE:
            raise GroupBreakdownError(
                f"quintile_partitions applies to quintile dimensions; "
                f"{key} is {dimension.kind}"
            )
        columns = _string_tuple(columns, f"{key} partition columns")
        absent = [c for c in columns if c not in frame.columns]
        if absent:
            raise GroupBreakdownError(f"partition columns {absent} are absent")
        if columns and frame[list(columns)].isna().any(axis=None):
            raise GroupBreakdownError("partition columns must not be missing")
        partitions[key] = columns
    declared = dict(unclassified_codes or {})
    for key, codes in declared.items():
        dimension = scheme.dimension(key)
        if dimension.kind != CATEGORICAL:
            raise GroupBreakdownError(
                f"unclassified_codes applies to categorical dimensions; "
                f"{key} is {dimension.kind}"
            )
        codes = frozenset(_string_tuple(codes, f"{key} unclassified codes"))
        held = codes.intersection(
            code for c in dimension.categories for code in c.codes
        )
        if held:
            raise GroupBreakdownError(
                f"{key}: codes {sorted(held)} are a category's and cannot "
                "be declared unclassified"
            )
        declared[key] = codes
    has_quintile = any(d.kind == QUINTILE for d in scheme.dimensions)
    weights = None
    if has_quintile:
        if weight_column is None or weight_column not in frame.columns:
            raise GroupBreakdownError(
                "a quintile dimension needs the weight column"
            )
        weights = _real_array(frame[weight_column].to_numpy(), "weights")
        if (weights < 0).any():
            raise GroupBreakdownError("weights must be non-negative")

    n = len(frame)
    index: dict[str, np.ndarray] = {}
    summaries = []
    long_parts = []
    for dimension in scheme.dimensions:
        records: list[dict[str, Any]] = []
        column = columns_map.get(dimension.key)
        if dimension.kind == TOTAL:
            codes = np.empty(n, dtype=object)
            codes[:] = TOTAL_KEY
            reasons: dict[str, int] = {}
        elif dimension.kind == CATEGORICAL:
            codes, reasons = _categorical_codes(
                dimension,
                frame[column].tolist(),
                declared.get(dimension.key, frozenset()),
                column,
            )
        elif dimension.kind == BAND:
            codes, reasons = _band_codes(
                dimension, frame[column].tolist(), column
            )
        else:
            codes, reasons, records = _quintile_codes(
                dimension, frame, column, weights, partitions[dimension.key]
            )
        index[dimension.key] = codes
        label_of = {c.key: c.label for c in dimension.categories}
        label_of[UNCLASSIFIED] = UNCLASSIFIED
        classified = codes != UNCLASSIFIED
        long_parts.append(
            pd.DataFrame(
                {
                    "row_id": np.arange(n, dtype=np.int64),
                    "dimension": dimension.key,
                    "label": [label_of[c] for c in codes.tolist()],
                    "category": codes.tolist(),
                    "classified": classified,
                }
            )
        )
        summary = {
            "key": dimension.key,
            "label": dimension.label,
            "kind": dimension.kind,
            "column": column,
            "n_rows": n,
            "n_classified": int(classified.sum()),
            "n_unclassified": int((~classified).sum()),
            "unclassified_reasons": dict(sorted(reasons.items())),
            "n_by_category": {
                c.key: int((codes == c.key).sum())
                for c in dimension.categories
            },
        }
        if dimension.kind == QUINTILE:
            summary["quintile_rule"] = QUINTILE_RULE
            summary["quintile_partitions"] = records
        summaries.append(summary)
    return GroupAssignment(
        scheme=scheme,
        n_rows=n,
        key_columns=key_columns,
        key_digest=digest,
        columns=dict(columns_map),
        weight_column=weight_column,
        quintile_partition=partition,
        quintile_partitions=partitions,
        long=pd.concat(long_parts, ignore_index=True),
        dimension_summaries=tuple(summaries),
        _category_index=index,
    )


def _check_assignment(
    assignment: Any,
    rows: pd.DataFrame,
    key_columns: tuple[str, ...],
) -> None:
    if not isinstance(assignment, GroupAssignment):
        raise GroupBreakdownError("assignment must be a GroupAssignment")
    if assignment.key_columns != key_columns:
        raise GroupBreakdownError(
            f"the assignment was keyed on {list(assignment.key_columns)}, "
            f"not {list(key_columns)}"
        )
    if assignment.n_rows != len(rows):
        raise GroupBreakdownError(
            f"the assignment covers {assignment.n_rows} rows, not "
            f"{len(rows)}"
        )
    missing = [c for c in key_columns if c not in rows.columns]
    if missing:
        raise GroupBreakdownError(f"rows lack key columns {missing}")
    digest = _key_digest(rows.reset_index(drop=True), key_columns)
    if digest != assignment.key_digest:
        raise GroupBreakdownError(
            "the rows are not the rows the assignment was built from (key "
            "digest differs): same rows, same order"
        )


# =========================================================================
# Shared tabulation pieces
# =========================================================================
def half_split_masks(
    unit_values: Sequence[Any], seeds: Sequence[int]
) -> dict[int, np.ndarray]:
    """Side-A membership of every row, per floor seed.

    The split is computed once over the split units of all rows passed, as
    ``cola_age_profile`` and ``uniform_cut_tabulation`` compute it
    (``split_panel_by_person`` with fraction 0.5 over the sorted unique
    units); a group's halves are this split intersected with its mask.
    """

    seeds = tuple(_floor_seeds(seeds))
    frame = pd.DataFrame({"split_unit": list(unit_values)})
    out = {}
    for seed in seeds:
        side_a, _ = split_panel_by_person(
            frame, "split_unit", fraction=FLOOR_FRACTION, seed=seed
        )
        in_a = np.zeros(len(frame), dtype=bool)
        in_a[side_a.index.to_numpy()] = True
        out[seed] = in_a
    return out


def _floor_seeds(seeds: Iterable[Any]) -> list[int]:
    out = []
    for seed in seeds:
        if isinstance(seed, bool | np.bool_) or not isinstance(seed, Integral):
            raise GroupBreakdownError("floor seeds must be integers")
        out.append(int(seed))
    if not out or len(set(out)) != len(out) or min(out) < 0:
        raise GroupBreakdownError(
            "floor seeds must be a non-empty set of distinct integers >= 0"
        )
    return out


def _labels(labels: Any, label: str) -> tuple[str, ...]:
    if isinstance(labels, str):
        raise GroupBreakdownError(f"{label} must be a sequence of strings")
    out = tuple(labels)
    if not all(isinstance(item, str) and item.strip() for item in out):
        raise GroupBreakdownError(f"{label} must be non-empty strings")
    return out


def _validate_provenance(
    rows: pd.DataFrame,
    data_provenance: Any,
    registration_pointer: Any,
    labels: Any,
    post_hoc_labels: Any,
) -> tuple[list[str], tuple[str, ...]]:
    if data_provenance not in DATA_PROVENANCES:
        raise GroupBreakdownError(
            f"data_provenance must be one of {list(DATA_PROVENANCES)}"
        )
    labels = _labels(labels, "labels")
    post_hoc = _labels(post_hoc_labels, "post_hoc_labels")
    kind = rows.attrs.get("provenance_kind")
    if data_provenance == REGISTERED_REAL:
        if not isinstance(
            registration_pointer, str
        ) or not REGISTRATION_POINTER.fullmatch(registration_pointer):
            raise GroupBreakdownError(
                "a real-data breakdown requires its issue #42 registration "
                "pointer (https://github.com/PolicyEngine/microcosm-"
                "dynamics/issues/42#issuecomment-<id>), which must exist "
                "before the run"
            )
        if not labels:
            raise GroupBreakdownError("a real-data breakdown needs labels")
        if not post_hoc:
            raise GroupBreakdownError(
                "a real-data breakdown needs the caller's post hoc labels "
                "(for example 'registered, one-shot, post hoc, not blind')"
            )
        if INVENTED_DATA_LABEL in labels:
            raise GroupBreakdownError(
                "a registered_real result cannot carry the invented label"
            )
        if kind == INVENTED:
            raise GroupBreakdownError(
                "rows marked invented cannot be tabulated as registered_real"
            )
    else:
        if registration_pointer is not None and not isinstance(
            registration_pointer, str
        ):
            raise GroupBreakdownError(
                "registration_pointer must be a string or None"
            )
        if kind == PSID_FILES:
            raise GroupBreakdownError(
                "rows built from staged PSID files cannot be tabulated as "
                "invented data"
            )
    output = [label for label in labels if label != INVENTED_DATA_LABEL]
    if data_provenance == INVENTED:
        output.insert(0, INVENTED_DATA_LABEL)
    return output, post_hoc


def _fsum(values: np.ndarray) -> float:
    try:
        total = math.fsum(values.tolist())
    except OverflowError as error:
        raise GroupBreakdownError(
            "a weighted sum overflows float64"
        ) from error
    if not math.isfinite(total):
        raise GroupBreakdownError("a weighted sum is not finite")
    return total


def _n_flags(n: int) -> dict[str, bool]:
    return {
        "ssa_disclosure_below_100": n < SSA_DISCLOSURE_MIN_N,
        "below_30": n < SMALL_CELL_MIN_N,
    }


def _numerator_flag(numerators: Sequence[int]) -> dict[str, Any]:
    low = [int(n) for n in numerators if 1 <= n < SSA_NUMERATOR_MIN]
    return {"ssa_numerator_1_to_9": bool(low)}


SUPPRESSION_RULES: dict[str, Any] = {
    "applied": (
        "flags only: no cell or dimension is dropped; a reader applies "
        "SSA's suppression by the flags"
    ),
    "ssa_disclosure_below_100": {
        "threshold": SSA_DISCLOSURE_MIN_N,
        "rule": "the cell's unweighted n is below 100",
        "dimension_flag": (
            "ssa_subgroup_suppressed: any category of the dimension is "
            "flagged, since SSA removes the whole subgroup"
        ),
        "source_quote": _Q_DISCLOSURE,
    },
    "below_30": {
        "threshold": SMALL_CELL_MIN_N,
        "rule": "the cell's unweighted n is below 30",
    },
    "ssa_numerator_1_to_9": {
        "threshold": SSA_NUMERATOR_MIN,
        "rule": (
            "percent with a decrease / increase only: an unweighted "
            "numerator of 1-9 cases (in any draw, for projections); SSA's "
            "low-numerator display exception is not modelled"
        ),
        "source_quote": _Q_NUMERATOR,
    },
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise GroupBreakdownError(f"non-string key {key!r}")
            out[key] = _json_safe(item)
        return out
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GroupBreakdownError("a result number is not finite")
        return value
    if value is None or isinstance(value, str | bool | int):
        return value
    raise GroupBreakdownError(f"value {value!r} is not JSON-safe")


# =========================================================================
# Result schema
# =========================================================================
@dataclass(frozen=True)
class StatisticCell:
    """One statistic of one group cell.

    ``value`` is the reported value (the mean over draws for projections),
    ``None`` when undefined with ``undefined_reason``; ``unweighted_n`` and
    ``weighted_n`` are the statistic's population in the cell (projections:
    the minimum over draws and the mean over draws); ``uncertainty`` holds
    the draw SD, design SE and floor as applicable; ``flags`` the
    suppression flags.
    """

    statistic: str
    value: float | None
    defined: bool
    undefined_reason: str | None
    unweighted_n: int
    weighted_n: float
    uncertainty: Mapping[str, Any]
    flags: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "statistic": self.statistic,
            "value": self.value,
            "defined": self.defined,
            "undefined_reason": self.undefined_reason,
            "unweighted_n": self.unweighted_n,
            "weighted_n": self.weighted_n,
            "uncertainty": dict(self.uncertainty),
            "flags": dict(self.flags),
        }


@dataclass(frozen=True)
class GroupCell:
    """One row of the breakdown: a category of a dimension."""

    dimension: str
    dimension_label: str
    category: str
    label: str
    counts: Mapping[str, Any]
    statistics: tuple[StatisticCell, ...]
    flags: Mapping[str, Any]

    def statistic(self, name: str) -> StatisticCell:
        for cell in self.statistics:
            if cell.statistic == name:
                return cell
        raise GroupBreakdownError(f"no statistic {name!r}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "dimension_label": self.dimension_label,
            "category": self.category,
            "label": self.label,
            "counts": dict(self.counts),
            "flags": dict(self.flags),
            "statistics": [s.as_dict() for s in self.statistics],
        }


@dataclass(frozen=True)
class DimensionResult:
    """A dimension's cells, its unclassified rows and its SSA flag."""

    key: str
    label: str
    kind: str
    cells: tuple[GroupCell, ...]
    unclassified: Mapping[str, Any]
    ssa_subgroup_suppressed: bool
    suppressed_by: tuple[str, ...]

    def cell(self, category: str) -> GroupCell:
        for cell in self.cells:
            if category in (cell.category, cell.label):
                return cell
        raise GroupBreakdownError(f"{self.key} has no category {category!r}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "ssa_subgroup_suppressed": self.ssa_subgroup_suppressed,
            "suppressed_by": list(self.suppressed_by),
            "unclassified": dict(self.unclassified),
            "cells": [c.as_dict() for c in self.cells],
        }


@dataclass(frozen=True)
class GroupBreakdownResult:
    """A complete breakdown; ``as_dict()`` is its JSON-safe form."""

    kind: str
    statistic_id: str
    data_provenance: str
    registration_pointer: str | None
    labels: tuple[str, ...]
    post_hoc_labels: tuple[str, ...]
    scheme: CategoryScheme
    statistics: tuple[str, ...]
    conventions: Mapping[str, Any]
    dimensions: tuple[DimensionResult, ...]
    assignment: Mapping[str, Any]
    input_summary: Mapping[str, Any]
    upstream: Mapping[str, Any]
    schema_version: str = SCHEMA_VERSION

    def dimension(self, key: str) -> DimensionResult:
        for dimension in self.dimensions:
            if dimension.key == key:
                return dimension
        raise GroupBreakdownError(f"no dimension {key!r}")

    def cell(self, dimension: str, category: str) -> GroupCell:
        return self.dimension(dimension).cell(category)

    def as_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "schema_version": self.schema_version,
                "kind": self.kind,
                "statistic_id": self.statistic_id,
                "data_provenance": self.data_provenance,
                "registration_pointer": self.registration_pointer,
                "labels": list(self.labels),
                "post_hoc_labels": list(self.post_hoc_labels),
                "scheme": self.scheme.as_dict(),
                "statistics": list(self.statistics),
                "statistic_definitions": {
                    name: STATISTIC_DEFINITIONS[name]
                    for name in self.statistics
                },
                "conventions": dict(self.conventions),
                "assignment": dict(self.assignment),
                "input_summary": dict(self.input_summary),
                "upstream": dict(self.upstream),
                "dimensions": [d.as_dict() for d in self.dimensions],
            }
        )


def _cell_flags(
    n: int, statistics: Sequence[StatisticCell]
) -> dict[str, bool]:
    flags = _n_flags(n)
    for name in flags:
        flags[name] = flags[name] or any(
            s.flags.get(name, False) for s in statistics
        )
    if any(s.flags.get("ssa_numerator_1_to_9", False) for s in statistics):
        flags["ssa_numerator_1_to_9"] = True
    return flags


def _dimension_result(
    dimension: Dimension,
    cells: list[GroupCell],
    unclassified: Mapping[str, Any],
) -> DimensionResult:
    flagged = tuple(
        cell.label
        for cell in cells
        if cell.flags.get("ssa_disclosure_below_100")
        or cell.flags.get("ssa_numerator_1_to_9")
    )
    return DimensionResult(
        key=dimension.key,
        label=dimension.label,
        kind=dimension.kind,
        cells=tuple(cells),
        unclassified=dict(unclassified),
        ssa_subgroup_suppressed=bool(flagged),
        suppressed_by=flagged,
    )


def _upstream(upstream: Mapping[str, Any] | None) -> dict[str, Any]:
    try:
        return a7._json_scalar_mapping(upstream, "upstream")
    except a7.ColaTabulationError as error:
        raise GroupBreakdownError(str(error)) from error


def _statistic_id(value: Any) -> str:
    return _nonempty_text(value, "statistic_id")


def _base_conventions() -> dict[str, Any]:
    return {
        "unclassified_rule": UNCLASSIFIED_RULE,
        "percentile_definition": PERCENTILE_DEFINITION,
        "quintile_rule": QUINTILE_RULE,
        "suppression": SUPPRESSION_RULES,
        "acceptance_rule": None,
        "acceptance_rule_note": (
            "none: a breakdown reports values only; it scores nothing"
        ),
    }


# =========================================================================
# Projection breakdown (exercises 1 and 3)
# =========================================================================
_PROJECTION_POPULATIONS = {
    RATIO_OF_SCENARIO_MEANS: ("n_base", "weight_base"),
    MEAN_OF_INDIVIDUAL_RATIOS: ("n_alternative", "weight_alternative"),
    **{
        name: ("n_current_law", "weight_current_law")
        for name in MINT_BENEFIT_STATISTICS
    },
}
_NUMERATORS = {PERCENT_DECREASE: "n_decrease", PERCENT_INCREASE: "n_increase"}


@dataclass(frozen=True, eq=False)
class _Projection:
    rows: Any  # cola_age_profile._Rows
    config: a7.ColaAgeProfileConfig
    masks: tuple[np.ndarray, np.ndarray, np.ndarray]
    by_draw: Mapping[int, np.ndarray]
    population: np.ndarray
    change: np.ndarray
    decrease: np.ndarray
    increase: np.ndarray
    numerators: np.ndarray
    positive: np.ndarray


def _mint_values(
    weights: np.ndarray,
    change: np.ndarray,
    decrease: np.ndarray,
    increase: np.ndarray,
    numerators: np.ndarray,
    positive: np.ndarray,
    in_population: np.ndarray,
) -> tuple[dict[str, Any], dict[str, str]]:
    """MINT8's benefit statistics over ``in_population`` (P in the cell)."""

    n = int(np.count_nonzero(in_population))
    total = _fsum(weights[in_population])
    counts = {
        "n_current_law": n,
        "weight_current_law": total,
        "n_decrease": int(np.count_nonzero(in_population & decrease)),
        "n_increase": int(np.count_nonzero(in_population & increase)),
    }
    if n == 0 or total <= 0.0:
        reason = (
            "empty_current_law_population"
            if n == 0
            else "zero_current_law_weight"
        )
        values = {name: None for name in MINT_BENEFIT_STATISTICS}
        return {**values, **counts}, {
            name: reason for name in MINT_BENEFIT_STATISTICS
        }
    unaffected = in_population & ~decrease & ~increase
    with_mass = in_population & positive
    p10, p50, p90 = _percentiles_of(
        change[with_mass], numerators[with_mass], (P10, P50, P90)
    )
    values = {
        PERCENT_DECREASE: 100.0
        * _fsum(weights[in_population & decrease])
        / total,
        PERCENT_INCREASE: 100.0
        * _fsum(weights[in_population & increase])
        / total,
        PERCENT_UNAFFECTED: 100.0 * _fsum(weights[unaffected]) / total,
        CHANGE_P10: p10,
        CHANGE_MEDIAN: p50,
        CHANGE_P90: p90,
    }
    return {**values, **counts}, {}


def _projection_draw(
    context: _Projection, subset: np.ndarray, draw: int
) -> dict[str, Any]:
    try:
        cell = a7._cell(context.rows, subset, context.masks, draw)
    except a7.ColaTabulationError as error:
        raise GroupBreakdownError(str(error)) from error
    mint, reasons = _mint_values(
        context.rows.weight,
        context.change,
        context.decrease,
        context.increase,
        context.numerators,
        context.positive,
        subset & context.population,
    )
    merged = dict(cell["undefined_reasons"])
    merged.update(reasons)
    return {**cell, **mint, "undefined_reasons": merged}


def _projection_side(
    context: _Projection, subset: np.ndarray
) -> dict[str, float | None]:
    """The reported values recomputed on one half (cola_age_profile's
    ``_side_values``: the mean over all draws, null if any is undefined)."""

    cells = [
        _projection_draw(context, subset & context.by_draw[d], d)
        for d in context.config.draw_indices
    ]
    out: dict[str, float | None] = {}
    for statistic in PROJECTION_STATISTICS:
        values = [cell[statistic] for cell in cells]
        if any(v is None for v in values):
            out[statistic] = None
        else:
            try:
                out[statistic] = a7._side_mean(values)
            except a7.ColaTabulationError as error:
                raise GroupBreakdownError(str(error)) from error
    return out


def _projection_cell(
    context: _Projection,
    split: Mapping[int, np.ndarray],
    dimension: Dimension,
    category: Category,
    mask: np.ndarray,
) -> GroupCell:
    draws = context.config.draw_indices
    cells = [
        _projection_draw(context, context.by_draw[d] & mask, d) for d in draws
    ]
    sides = {
        seed: (
            _projection_side(context, mask & in_a),
            _projection_side(context, mask & ~in_a),
        )
        for seed, in_a in split.items()
    }
    statistics = []
    for statistic in PROJECTION_STATISTICS:
        summary = a7._draw_summary(cells, statistic)
        gaps, dropped = [], []
        for seed, (side_a, side_b) in sides.items():
            a, b = side_a[statistic], side_b[statistic]
            if a is None or b is None:
                dropped.append(seed)
            else:
                gaps.append(abs(a - b))
        try:
            floor = {**a7._floor_summary(gaps), "dropped_seeds": dropped}
        except a7.ColaTabulationError as error:
            raise GroupBreakdownError(str(error)) from error
        n_key, w_key = _PROJECTION_POPULATIONS[statistic]
        per_draw_n = [int(c[n_key]) for c in cells]
        if statistic == RATIO_OF_SCENARIO_MEANS:
            per_draw_n = [min(c["n_base"], c["n_reform"]) for c in cells]
        per_draw_w = [float(c[w_key]) for c in cells]
        flags: dict[str, Any] = _n_flags(min(per_draw_n))
        if statistic in _NUMERATORS:
            flags.update(
                _numerator_flag([c[_NUMERATORS[statistic]] for c in cells])
            )
        undefined = summary["undefined_draws"]
        statistics.append(
            StatisticCell(
                statistic=statistic,
                value=summary["mean"],
                defined=summary["defined"],
                undefined_reason=(
                    None
                    if summary["defined"]
                    else (
                        f"undefined in {len(undefined)} of "
                        f"{summary['n_draws']} draws: "
                        f"{sorted({u['reason'] for u in undefined})}"
                    )
                ),
                unweighted_n=min(per_draw_n),
                weighted_n=math.fsum(per_draw_w) / len(per_draw_w),
                uncertainty={
                    "method": "draws_and_half_split_floor",
                    "per_draw": summary["per_draw"],
                    "sample_sd": summary["sample_sd"],
                    "n_draws": summary["n_draws"],
                    "n_defined_draws": summary["n_defined_draws"],
                    "undefined_draws": undefined,
                    "unweighted_n_per_draw": per_draw_n,
                    "weighted_n_per_draw": per_draw_w,
                    "floor": floor,
                },
                flags=flags,
            )
        )
    n_current = [int(c["n_current_law"]) for c in cells]
    counts = {
        "n_rows": int(np.count_nonzero(mask)),
        "n_persons": int(len(set(context.rows.person_id[mask].tolist()))),
        "unweighted_n_current_law_per_draw": n_current,
        "weighted_n_current_law_per_draw": [
            float(c["weight_current_law"]) for c in cells
        ],
        "unweighted_n_base_per_draw": [int(c["n_base"]) for c in cells],
        "weighted_n_base_per_draw": [float(c["weight_base"]) for c in cells],
        "unweighted_n_reform_per_draw": [int(c["n_reform"]) for c in cells],
        "weighted_n_reform_per_draw": [
            float(c["weight_reform"]) for c in cells
        ],
        "unweighted_n": min(n_current),
        "unweighted_n_rule": (
            "minimum over draws of the cell's current-law beneficiaries "
            "with a positive selected benefit"
        ),
    }
    return GroupCell(
        dimension=dimension.key,
        dimension_label=dimension.label,
        category=category.key,
        label=category.label,
        counts=counts,
        statistics=tuple(statistics),
        flags=_cell_flags(min(n_current), statistics),
    )


def _projection_unclassified(
    context: _Projection, mask: np.ndarray, summary: Mapping[str, Any]
) -> dict[str, Any]:
    per_draw = []
    for d in context.config.draw_indices:
        subset = mask & context.by_draw[d]
        base = subset & context.masks[0]
        current = subset & context.population
        per_draw.append(
            {
                "draw": int(d),
                "n_rows": int(np.count_nonzero(subset)),
                "n_current_law": int(np.count_nonzero(current)),
                "weight_current_law": _fsum(context.rows.weight[current]),
                "n_base": int(np.count_nonzero(base)),
                "weight_base": _fsum(context.rows.weight[base]),
            }
        )
    return {
        "n_rows": int(np.count_nonzero(mask)),
        "reasons": dict(summary["unclassified_reasons"]),
        "per_draw": per_draw,
        "statistics": None,
        "note": "unclassified rows enter Total only; counts are reported",
    }


PROJECTION_STATISTIC_ID = "group_breakdown_projection_benefit_change"
_PROJECTION_KEYS = ("draw", "person_id")


def tabulate_projection_breakdown(
    rows: pd.DataFrame,
    assignment: GroupAssignment,
    *,
    data_provenance: str,
    config: a7.ColaAgeProfileConfig | None = None,
    registration_pointer: str | None = None,
    labels: Sequence[str] = (),
    post_hoc_labels: Sequence[str] = (),
    statistic_id: str = PROJECTION_STATISTIC_ID,
    upstream: Mapping[str, Any] | None = None,
) -> GroupBreakdownResult:
    """Break a projection's per-person-per-draw rows down by group.

    ``rows`` are ``cola_age_profile`` input rows (its
    ``REQUIRED_COLUMNS``; attribute columns are ignored here) and
    ``assignment`` is :func:`assign_groups` of the same frame keyed on
    ``("draw", "person_id")``.  ``config`` is the
    ``ColaAgeProfileConfig`` of the run (exercise 3 passes
    ``allow_membership_difference=True``); scenario memberships, draws,
    floor seeds and the floor's split unit all come from it, and rows
    whose memberships differ are refused unless it allows them, as
    ``tabulate_cola_age_profile`` does.  Every cell carries
    :data:`PROJECTION_STATISTICS`.
    """

    config = a7.ColaAgeProfileConfig() if config is None else config
    if not isinstance(config, a7.ColaAgeProfileConfig):
        raise GroupBreakdownError("config must be a ColaAgeProfileConfig")
    if not isinstance(rows, pd.DataFrame):
        raise GroupBreakdownError("rows must be a DataFrame")
    output_labels, post_hoc = _validate_provenance(
        rows, data_provenance, registration_pointer, labels, post_hoc_labels
    )
    statistic_id = _statistic_id(statistic_id)
    recorded_upstream = _upstream(upstream)
    _check_assignment(assignment, rows, _PROJECTION_KEYS)
    try:
        normalized = a7._normalize(rows.reset_index(drop=True), config)
    except a7.ColaTabulationError as error:
        raise GroupBreakdownError(str(error)) from error
    differs = normalized.recipient_base != normalized.recipient_reform
    if differs.any() and not config.allow_membership_difference:
        raise GroupBreakdownError(
            f"{int(np.count_nonzero(differs))} rows are recipients in only "
            "one scenario; pass a config with allow_membership_difference "
            "to tabulate them under its membership_basis"
        )
    population_base = normalized.recipient_base & (
        normalized.selected_base > 0.0
    )
    _, change, decrease, increase = classify_changes(
        np.where(population_base, normalized.selected_base, 0.0),
        normalized.selected_reform,
    )
    context = _Projection(
        rows=normalized,
        config=config,
        masks=a7._membership_masks(normalized, config.membership_basis),
        by_draw={d: normalized.draw == d for d in config.draw_indices},
        population=population_base,
        change=change,
        decrease=decrease & population_base,
        increase=increase & population_base,
        numerators=_exact_numerators(normalized.weight),
        positive=normalized.weight > 0.0,
    )
    unit_values = (
        normalized.family_unit_id
        if config.floor_split_unit == a7.FAMILY_UNIT
        else normalized.person_id
    )
    split = half_split_masks(unit_values.tolist(), config.floor_seeds)
    summaries = {s["key"]: s for s in assignment.dimension_summaries}
    dimensions = []
    for dimension in assignment.scheme.dimensions:
        cells = [
            _projection_cell(
                context,
                split,
                dimension,
                category,
                assignment.mask(dimension.key, category.key),
            )
            for category in dimension.categories
        ]
        unclassified = _projection_unclassified(
            context,
            assignment.unclassified_mask(dimension.key),
            summaries[dimension.key],
        )
        dimensions.append(_dimension_result(dimension, cells, unclassified))
    conventions = {
        **_base_conventions(),
        "change_definition": CHANGE_DEFINITION,
        "cola_age_profile_config": config.as_dict(),
        "membership": {
            "recipient_rule": config.recipient_rule,
            "recipient_rule_definition": a7.RECIPIENT_RULE_DEFINITIONS[
                config.recipient_rule
            ],
            "membership_basis": config.membership_basis,
            "membership_basis_definition": a7.MEMBERSHIP_BASIS_DEFINITIONS[
                config.membership_basis
            ],
            "allow_membership_difference": (
                config.allow_membership_difference
            ),
            "mint_population": _MINT_POPULATION,
        },
        "uncertainty": {
            "draws": (
                "the reported value is the mean over the configured draws "
                "of the per-draw statistic, with the ddof=1 sample SD "
                "(cola_age_profile._draw_summary); a statistic undefined in "
                "any draw has no mean"
            ),
            "floor": (
                "for each floor seed the split units "
                f"({config.floor_split_unit}) of all input rows are split "
                "once (half_split_masks); each group's halves are that "
                "split intersected with the group's mask, never a re-split "
                "of the group; the side value is the mean over draws; the "
                "floor summarizes |side_a - side_b| over usable seeds "
                "(cola_age_profile._floor_summary) and is undefined, not "
                "zero, with fewer than two"
            ),
            "floor_seeds": list(config.floor_seeds),
            "floor_split_unit": config.floor_split_unit,
            "scale": "half sample; not rescaled",
        },
        "unweighted_n": (
            "per statistic: the minimum over draws of the per-draw count "
            "of the statistic's population in the cell (the smaller of "
            "S_base and S_reform for the ratio of means, S_alt for the "
            "mean of ratios, P for the MINT8 "
            "statistics); the cell's flags include any statistic's "
            "small-population or numerator flag"
        ),
        "weighted_n": (
            "per statistic: mean over draws of population weight; the "
            "ratio of means reports baseline weight, with both scenarios' "
            "counts and weights also retained in each cell's counts"
        ),
    }
    input_summary = {
        "n_rows": normalized.n,
        "n_persons": int(len(set(normalized.person_id.tolist()))),
        "n_family_units": int(len(set(normalized.family_unit_id.tolist()))),
        "draws": list(config.draw_indices),
        "n_rows_per_draw": {
            str(d): int(np.count_nonzero(mask))
            for d, mask in context.by_draw.items()
        },
        "n_rows_membership_differs": int(np.count_nonzero(differs)),
        "n_current_law_rows": int(np.count_nonzero(population_base)),
        "extra_columns_ignored": list(normalized.extra_columns),
    }
    return GroupBreakdownResult(
        kind=PROJECTION_KIND,
        statistic_id=statistic_id,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        labels=tuple(output_labels),
        post_hoc_labels=post_hoc,
        scheme=assignment.scheme,
        statistics=PROJECTION_STATISTICS,
        conventions=conventions,
        dimensions=tuple(dimensions),
        assignment=assignment.as_dict(),
        input_summary=input_summary,
        upstream=recorded_upstream,
    )


# =========================================================================
# Static breakdowns (exercises 2 and 4)
# =========================================================================
_STATIC_BASE_COLUMNS = (
    "person_id",
    "family_unit_id",
    "weight",
    "stratum",
    "cluster",
)


def _design_identifiers(frame: pd.DataFrame) -> pd.DataFrame:
    """Preserve integer survey identifiers; refuse lossy coercions.

    Track U normalizes design identifiers to int64.  Check the values
    before calling it so a fractional cluster cannot silently merge with
    another cluster, and a boolean cannot be mistaken for an identifier.
    """

    out = frame.copy()
    limits = np.iinfo(np.int64)
    for column in ("stratum", "cluster"):
        values = [
            _band_value(value, f"{column} identifier")
            for value in frame[column].tolist()
        ]
        if any(value < limits.min or value > limits.max for value in values):
            raise GroupBreakdownError(f"{column} identifiers exceed int64")
        out[column] = np.asarray(values, dtype=np.int64)
    return out


def _static_frame(
    rows: Any,
    *,
    id_column: str,
    bool_columns: Sequence[str] = (),
    amount_columns: Sequence[str] = (),
) -> pd.DataFrame:
    if not isinstance(rows, pd.DataFrame):
        raise GroupBreakdownError("rows must be a DataFrame")
    if not rows.columns.is_unique:
        raise GroupBreakdownError("rows have repeated column names")
    required = list(
        dict.fromkeys(
            (id_column, *_STATIC_BASE_COLUMNS, *bool_columns, *amount_columns)
        )
    )
    missing = [c for c in required if c not in rows.columns]
    if missing:
        raise GroupBreakdownError(f"rows lack columns {missing}")
    out = rows[required].reset_index(drop=True).copy()
    if out.empty:
        raise GroupBreakdownError("no rows")
    if out[id_column].isna().any() or out[id_column].duplicated().any():
        raise GroupBreakdownError(f"{id_column} must be present and unique")
    identifiers = ["person_id", "family_unit_id", "stratum", "cluster"]
    if out[identifiers].isna().any(axis=None):
        raise GroupBreakdownError(
            "person_id, family_unit_id, stratum and cluster must be present"
        )
    out["weight"] = _real_array(out["weight"].to_numpy(), "weights")
    if (out["weight"] < 0).any():
        raise GroupBreakdownError("weights must be non-negative")
    for column in bool_columns:
        values = out[column]
        if not values.map(lambda v: isinstance(v, bool | np.bool_)).all():
            raise GroupBreakdownError(f"{column} must be boolean")
        out[column] = values.astype(bool)
    for column in amount_columns:
        amounts = _real_array(out[column].to_numpy(), column)
        if (amounts < 0).any():
            raise GroupBreakdownError(f"{column} must be non-negative")
        out[column] = amounts
    return _design_identifiers(out)


def _design(
    normalized: pd.DataFrame, design: Any
) -> tuple[pd.MultiIndex, dict[str, Any]]:
    try:
        if isinstance(design, pd.DataFrame) and all(
            c in design.columns for c in ("stratum", "cluster")
        ):
            design = _design_identifiers(design)
        clusters_all = track_u._design_clusters(design)
    except track_u.UniformCutTabulationError as error:
        raise GroupBreakdownError(str(error)) from error
    if clusters_all is None:
        raise GroupBreakdownError(
            "the design-based standard error needs the design frame (every "
            "stratum and cluster of the sample's positive-weight persons)"
        )
    present = pd.MultiIndex.from_frame(normalized[["stratum", "cluster"]])
    outside = present[~present.isin(clusters_all)].unique()
    if len(outside):
        raise GroupBreakdownError(
            f"{len(outside)} (stratum, cluster) pairs of the rows are not in "
            "the design frame"
        )
    sizes = pd.Series(1, index=clusters_all).groupby(level=0).sum()
    return clusters_all, {
        "method": "taylor_linearization",
        "estimator": "uniform_cut_tabulation._design_se",
        "domain": "full_sample_design",
        "n_strata": int(len(sizes)),
        "n_clusters": int(sizes.sum()),
        "singleton_strata": [int(s) for s in sizes[sizes < 2].index],
        "unit": "percentage points",
    }


def _static_split(
    normalized: pd.DataFrame, floor_split_unit: str, seeds: Sequence[int]
) -> dict[int, np.ndarray]:
    if floor_split_unit not in STATIC_FLOOR_SPLIT_UNITS:
        raise GroupBreakdownError(
            f"floor_split_unit must be one of {sorted(STATIC_FLOOR_SPLIT_UNITS)}"
        )
    if floor_split_unit == FAMILY_UNIT_LINKED_BY_PERSON:
        units = track_u.floor_split_units(normalized)
    else:
        units = normalized[floor_split_unit].to_numpy()
    return half_split_masks(list(units), seeds)


def _design_se(
    frame: pd.DataFrame,
    mask: np.ndarray,
    indicator: np.ndarray,
    clusters_all: pd.MultiIndex,
) -> dict[str, Any]:
    try:
        return track_u._design_se(frame, mask, indicator, clusters_all)
    except track_u.UniformCutTabulationError as error:
        raise GroupBreakdownError(str(error)) from error


def _static_floor(gaps: list[float], dropped: list[int]) -> dict[str, Any]:
    try:
        return {**track_u._floor_summary(gaps), "dropped_seeds": dropped}
    except track_u.UniformCutTabulationError as error:
        raise GroupBreakdownError(str(error)) from error


@dataclass(frozen=True, eq=False)
class _StaticSpec:
    """How one static kind computes its statistics on a row mask."""

    statistics: tuple[str, ...]
    #: mask -> (values, undefined reasons, counts with unweighted_n,
    #: weighted_n and numerators).
    compute: Callable[[np.ndarray], tuple[dict, dict, dict]]
    #: (mask, statistic) -> (design SE record or None, note or None).
    design_se: Callable[[np.ndarray, str], tuple[dict | None, str | None]]
    floor_notes: Mapping[str, str]
    population: np.ndarray


def _static_cell(
    spec: _StaticSpec,
    split: Mapping[int, np.ndarray],
    dimension: Dimension,
    category: Category,
    mask: np.ndarray,
) -> GroupCell:
    values, reasons, counts = spec.compute(mask)
    sides = {
        seed: (spec.compute(mask & in_a)[0], spec.compute(mask & ~in_a)[0])
        for seed, in_a in split.items()
    }
    statistics = []
    n = counts["unweighted_n"]
    for statistic in spec.statistics:
        value = values[statistic]
        defined = value is not None
        floor_note = spec.floor_notes.get(statistic)
        gaps, dropped = [], []
        for seed, (side_a, side_b) in sides.items():
            a, b = side_a[statistic], side_b[statistic]
            if a is None or b is None:
                dropped.append(seed)
            else:
                gaps.append(abs(a - b))
        floor = _static_floor(gaps, dropped)
        if defined:
            se, se_note = spec.design_se(mask, statistic)
        else:
            se, se_note = None, "statistic undefined"
        flags: dict[str, Any] = _n_flags(n)
        if statistic in _NUMERATORS:
            flags.update(
                _numerator_flag([counts["numerators"][_NUMERATORS[statistic]]])
            )
        statistics.append(
            StatisticCell(
                statistic=statistic,
                value=value,
                defined=defined,
                undefined_reason=None if defined else reasons[statistic],
                unweighted_n=n,
                weighted_n=counts["weighted_n"],
                uncertainty={
                    "method": "design_se_and_half_split_floor",
                    "design_se": se,
                    "design_se_note": se_note,
                    "floor": floor,
                    "floor_note": floor_note,
                },
                flags=flags,
            )
        )
    return GroupCell(
        dimension=dimension.key,
        dimension_label=dimension.label,
        category=category.key,
        label=category.label,
        counts={
            "n_rows": int(np.count_nonzero(mask)),
            **counts,
        },
        statistics=tuple(statistics),
        flags=_cell_flags(n, statistics),
    )


def _static_result(
    *,
    kind: str,
    rows: pd.DataFrame,
    assignment: GroupAssignment,
    normalized: pd.DataFrame,
    spec: _StaticSpec,
    id_column: str,
    design_summary: Mapping[str, Any],
    floor_seeds: Sequence[int],
    floor_split_unit: str,
    data_provenance: str,
    registration_pointer: str | None,
    output_labels: list[str],
    post_hoc: tuple[str, ...],
    statistic_id: str,
    upstream: Mapping[str, Any],
    extra_conventions: Mapping[str, Any],
) -> GroupBreakdownResult:
    split = _static_split(normalized, floor_split_unit, floor_seeds)
    summaries = {s["key"]: s for s in assignment.dimension_summaries}
    weights = normalized["weight"].to_numpy()
    dimensions = []
    for dimension in assignment.scheme.dimensions:
        cells = [
            _static_cell(
                spec,
                split,
                dimension,
                category,
                assignment.mask(dimension.key, category.key),
            )
            for category in dimension.categories
        ]
        unclassified = assignment.unclassified_mask(dimension.key)
        in_population = unclassified & spec.population
        dimensions.append(
            _dimension_result(
                dimension,
                cells,
                {
                    "n_rows": int(np.count_nonzero(unclassified)),
                    "unweighted_n": int(np.count_nonzero(in_population)),
                    "weighted_n": _fsum(weights[in_population]),
                    "reasons": dict(
                        summaries[dimension.key]["unclassified_reasons"]
                    ),
                    "statistics": None,
                    "note": (
                        "unclassified rows enter Total only; counts are "
                        "reported over the statistics' population"
                    ),
                },
            )
        )
    conventions = {
        **_base_conventions(),
        **extra_conventions,
        "uncertainty": {
            "draws": 1,
            "design_se": dict(design_summary),
            "floor": (
                "for each floor seed the split units "
                f"({floor_split_unit}: "
                f"{STATIC_FLOOR_SPLIT_UNITS[floor_split_unit]}) of all rows "
                "are split once (half_split_masks); each group's halves are "
                "that split intersected with the group's mask; the floor "
                "summarizes |side_a - side_b| over usable seeds "
                "(uniform_cut_tabulation._floor_summary) and is undefined, "
                "not zero, with fewer than two"
            ),
            "floor_seeds": list(_floor_seeds(floor_seeds)),
            "floor_split_unit": floor_split_unit,
            "scale": "half sample; not rescaled",
        },
        "unweighted_n": (
            "the number of rows of the statistics' population in the cell"
        ),
        "id_column": id_column,
    }
    input_summary = {
        "n_rows": int(len(normalized)),
        "n_persons": int(normalized["person_id"].nunique()),
        "n_family_units": int(normalized["family_unit_id"].nunique()),
        "n_zero_weight": int((normalized["weight"] == 0).sum()),
        "n_population_rows": int(np.count_nonzero(spec.population)),
        "extra_columns_ignored": sorted(
            str(c) for c in rows.columns if c not in normalized.columns
        ),
    }
    return GroupBreakdownResult(
        kind=kind,
        statistic_id=statistic_id,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        labels=tuple(output_labels),
        post_hoc_labels=post_hoc,
        scheme=assignment.scheme,
        statistics=spec.statistics,
        conventions=conventions,
        dimensions=tuple(dimensions),
        assignment=assignment.as_dict(),
        input_summary=input_summary,
        upstream=upstream,
    )


def _static_prelude(
    rows: Any,
    assignment: Any,
    *,
    id_column: str,
    data_provenance: Any,
    registration_pointer: Any,
    labels: Any,
    post_hoc_labels: Any,
    statistic_id: Any,
    upstream: Any,
    bool_columns: Sequence[str] = (),
    amount_columns: Sequence[str] = (),
) -> tuple[pd.DataFrame, list[str], tuple[str, ...], str, dict[str, Any]]:
    if not isinstance(rows, pd.DataFrame):
        raise GroupBreakdownError("rows must be a DataFrame")
    _nonempty_text(id_column, "id_column")
    output_labels, post_hoc = _validate_provenance(
        rows, data_provenance, registration_pointer, labels, post_hoc_labels
    )
    statistic_id = _statistic_id(statistic_id)
    recorded_upstream = _upstream(upstream)
    _check_assignment(assignment, rows, (id_column,))
    normalized = _static_frame(
        rows,
        id_column=id_column,
        bool_columns=bool_columns,
        amount_columns=amount_columns,
    )
    return normalized, output_labels, post_hoc, statistic_id, recorded_upstream


POVERTY_STATISTIC_ID = "group_breakdown_static_poverty"
_NOT_A_RATIO = (
    "not computed: uniform_cut_tabulation._design_se linearizes a weighted "
    "ratio, and this statistic is a weighted count or a ratio of two "
    "weighted counts"
)
_COUNT_FLOOR = (
    "raw half-to-half gap in thousands, not rescaled: each half's weighted "
    "count is on half the full sample's scale; this describes the split "
    "diagnostic and is not a full-sample count standard error"
)


def tabulate_poverty_breakdown(
    rows: pd.DataFrame,
    assignment: GroupAssignment,
    *,
    design: pd.DataFrame,
    data_provenance: str,
    id_column: str = "person_id",
    floor_seeds: Sequence[int] = DEFAULT_FLOOR_SEEDS,
    floor_split_unit: str = FAMILY_UNIT_LINKED_BY_PERSON,
    registration_pointer: str | None = None,
    labels: Sequence[str] = (),
    post_hoc_labels: Sequence[str] = (),
    statistic_id: str = POVERTY_STATISTIC_ID,
    upstream: Mapping[str, Any] | None = None,
) -> GroupBreakdownResult:
    """Break static poverty flags down by group (exercise 2).

    ``rows`` carry ``id_column`` (unique), ``person_id``,
    ``family_unit_id``, ``weight``, ``stratum``, ``cluster`` and the
    booleans ``poor_baseline`` and ``poor_reform`` (for example
    ``uniform_cut_tabulation.tabulation_rows`` output, ``id_column=
    "observation_id"``); ``assignment`` is keyed on ``(id_column,)``.
    Rates and their change come from ``uniform_cut_tabulation._rates`` and
    their design SEs from its ``_design_se`` on the full design frame
    (``design``), so the Total cell equals ``tabulate_uniform_cut``'s
    ``all`` cell.
    """

    normalized, output_labels, post_hoc, statistic_id, recorded_upstream = (
        _static_prelude(
            rows,
            assignment,
            id_column=id_column,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
            labels=labels,
            post_hoc_labels=post_hoc_labels,
            statistic_id=statistic_id,
            upstream=upstream,
            bool_columns=("poor_baseline", "poor_reform"),
        )
    )
    clusters_all, design_summary = _design(normalized, design)
    weights = normalized["weight"].to_numpy()
    poor_base = normalized["poor_baseline"].to_numpy()
    poor_reform = normalized["poor_reform"].to_numpy()
    base_f = poor_base.astype(np.float64)
    reform_f = poor_reform.astype(np.float64)
    indicators = {
        POVERTY_RATE_CURRENT_LAW: base_f,
        POVERTY_RATE_PROPOSAL: reform_f,
        POVERTY_RATE_CHANGE: reform_f - base_f,
    }

    def compute(mask: np.ndarray) -> tuple[dict, dict, dict]:
        try:
            rates = track_u._rates(normalized, mask)
        except track_u.UniformCutTabulationError as error:
            raise GroupBreakdownError(str(error)) from error
        counts = {
            "unweighted_n": int(np.count_nonzero(mask)),
            "weighted_n": _fsum(weights[mask]),
            "numerators": {
                "n_poor_current_law": int(np.count_nonzero(mask & poor_base)),
                "n_poor_proposal": int(np.count_nonzero(mask & poor_reform)),
            },
        }
        if not rates["defined"]:
            reason = rates["undefined_reason"]
            return (
                {s: None for s in POVERTY_STATISTICS},
                {s: reason for s in POVERTY_STATISTICS},
                counts,
            )
        number_base = _fsum(weights[mask & poor_base])
        number_reform = _fsum(weights[mask & poor_reform])
        values = {
            POVERTY_RATE_CURRENT_LAW: rates["baseline_rate"],
            POVERTY_RATE_PROPOSAL: rates["reform_rate"],
            POVERTY_RATE_CHANGE: rates["delta"],
            NUMBER_POOR_CURRENT_LAW: number_base / 1000.0,
            NUMBER_POOR_PROPOSAL: number_reform / 1000.0,
            NUMBER_POOR_CHANGE: (number_reform - number_base) / 1000.0,
            NUMBER_POOR_PERCENT_CHANGE: (
                100.0 * (number_reform - number_base) / number_base
                if number_base > 0.0
                else None
            ),
        }
        reasons = {}
        if values[NUMBER_POOR_PERCENT_CHANGE] is None:
            reasons[NUMBER_POOR_PERCENT_CHANGE] = (
                "nobody in the cell is poor under current law"
            )
        return values, reasons, counts

    def design_se(mask: np.ndarray, statistic: str):
        if statistic in indicators:
            return (
                _design_se(
                    normalized, mask, indicators[statistic], clusters_all
                ),
                None,
            )
        return None, _NOT_A_RATIO

    spec = _StaticSpec(
        statistics=POVERTY_STATISTICS,
        compute=compute,
        design_se=design_se,
        floor_notes={
            NUMBER_POOR_CURRENT_LAW: _COUNT_FLOOR,
            NUMBER_POOR_PROPOSAL: _COUNT_FLOOR,
            NUMBER_POOR_CHANGE: _COUNT_FLOOR,
        },
        population=np.ones(len(normalized), dtype=bool),
    )
    return _static_result(
        kind=POVERTY_KIND,
        rows=rows,
        assignment=assignment,
        normalized=normalized,
        spec=spec,
        id_column=id_column,
        design_summary=design_summary,
        floor_seeds=floor_seeds,
        floor_split_unit=floor_split_unit,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        output_labels=output_labels,
        post_hoc=post_hoc,
        statistic_id=statistic_id,
        upstream=recorded_upstream,
        extra_conventions={"population": "every row"},
    )


SHARE_STATISTIC_ID = "group_breakdown_static_share"


def tabulate_share_breakdown(
    rows: pd.DataFrame,
    assignment: GroupAssignment,
    *,
    indicator_column: str,
    design: pd.DataFrame,
    data_provenance: str,
    id_column: str = "person_id",
    floor_seeds: Sequence[int] = DEFAULT_FLOOR_SEEDS,
    floor_split_unit: str = FAMILY_UNIT_LINKED_BY_PERSON,
    registration_pointer: str | None = None,
    labels: Sequence[str] = (),
    post_hoc_labels: Sequence[str] = (),
    statistic_id: str = SHARE_STATISTIC_ID,
    upstream: Mapping[str, Any] | None = None,
) -> GroupBreakdownResult:
    """Break a static weighted share down by group (exercise 4).

    The share is ``100 * sum w 1{indicator} / sum w``, the formula of
    ``min_benefit_track_m.tabulation._share``, with the design SE of
    ``uniform_cut_tabulation._design_se`` and the half-sample floor; the
    Total cell equals ``tabulate_track_m``'s ``all`` cell for the same
    indicator.
    """

    _nonempty_text(indicator_column, "indicator_column")
    normalized, output_labels, post_hoc, statistic_id, recorded_upstream = (
        _static_prelude(
            rows,
            assignment,
            id_column=id_column,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
            labels=labels,
            post_hoc_labels=post_hoc_labels,
            statistic_id=statistic_id,
            upstream=upstream,
            bool_columns=(indicator_column,),
        )
    )
    clusters_all, design_summary = _design(normalized, design)
    weights = normalized["weight"].to_numpy()
    receiving = normalized[indicator_column].to_numpy()

    def compute(mask: np.ndarray) -> tuple[dict, dict, dict]:
        total = _fsum(weights[mask])
        counts = {
            "unweighted_n": int(np.count_nonzero(mask)),
            "weighted_n": total,
            "numerators": {
                "n_indicator": int(np.count_nonzero(mask & receiving))
            },
        }
        if not mask.any():
            return {SHARE: None}, {SHARE: "empty cell"}, counts
        if total <= 0:
            return {SHARE: None}, {SHARE: "zero total weight"}, counts
        numerator = _fsum(weights[mask & receiving])
        counts["weighted_indicator"] = numerator
        return {SHARE: 100.0 * numerator / total}, {}, counts

    def design_se(mask: np.ndarray, statistic: str):
        return (
            _design_se(
                normalized, mask, receiving.astype(np.float64), clusters_all
            ),
            None,
        )

    spec = _StaticSpec(
        statistics=SHARE_STATISTICS,
        compute=compute,
        design_se=design_se,
        floor_notes={},
        population=np.ones(len(normalized), dtype=bool),
    )
    return _static_result(
        kind=SHARE_KIND,
        rows=rows,
        assignment=assignment,
        normalized=normalized,
        spec=spec,
        id_column=id_column,
        design_summary=design_summary,
        floor_seeds=floor_seeds,
        floor_split_unit=floor_split_unit,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        output_labels=output_labels,
        post_hoc=post_hoc,
        statistic_id=statistic_id,
        upstream=recorded_upstream,
        extra_conventions={
            "population": "every row",
            "indicator_column": indicator_column,
        },
    )


STATIC_BENEFIT_STATISTIC_ID = "group_breakdown_static_benefit_change"
_NO_PERCENTILE_SE = (
    "not computed: a design-based standard error of a weighted percentile "
    "needs a density estimate or replicate weights, which this module does "
    "not implement"
)


def tabulate_static_benefit_breakdown(
    rows: pd.DataFrame,
    assignment: GroupAssignment,
    *,
    design: pd.DataFrame,
    data_provenance: str,
    base_column: str = "benefit_base",
    reform_column: str = "benefit_reform",
    id_column: str = "person_id",
    floor_seeds: Sequence[int] = DEFAULT_FLOOR_SEEDS,
    floor_split_unit: str = FAMILY_UNIT_LINKED_BY_PERSON,
    registration_pointer: str | None = None,
    labels: Sequence[str] = (),
    post_hoc_labels: Sequence[str] = (),
    statistic_id: str = STATIC_BENEFIT_STATISTIC_ID,
    upstream: Mapping[str, Any] | None = None,
) -> GroupBreakdownResult:
    """MINT8's benefit statistics for a static test, by group.

    Over the rows with a positive current-law amount (``base_column``):
    percent with a decrease / increase (and the unaffected rest), each
    with the design SE of ``uniform_cut_tabulation._design_se`` (the group
    and population as the domain), and the weighted 10th, 50th and 90th
    percentiles of the individual percent change, which carry no design
    SE (each cell says why).  Every statistic has the half-sample floor.
    """

    normalized, output_labels, post_hoc, statistic_id, recorded_upstream = (
        _static_prelude(
            rows,
            assignment,
            id_column=id_column,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
            labels=labels,
            post_hoc_labels=post_hoc_labels,
            statistic_id=statistic_id,
            upstream=upstream,
            amount_columns=(base_column, reform_column),
        )
    )
    clusters_all, design_summary = _design(normalized, design)
    weights = normalized["weight"].to_numpy()
    population, change, decrease, increase = classify_changes(
        normalized[base_column].to_numpy(),
        normalized[reform_column].to_numpy(),
    )
    numerators = _exact_numerators(weights)
    positive = weights > 0.0
    unaffected = population & ~decrease & ~increase
    indicators = {
        PERCENT_DECREASE: decrease.astype(np.float64),
        PERCENT_INCREASE: increase.astype(np.float64),
        PERCENT_UNAFFECTED: unaffected.astype(np.float64),
    }

    def compute(mask: np.ndarray) -> tuple[dict, dict, dict]:
        values, reasons = _mint_values(
            weights,
            change,
            decrease,
            increase,
            numerators,
            positive,
            mask & population,
        )
        counts = {
            "unweighted_n": values.pop("n_current_law"),
            "weighted_n": values.pop("weight_current_law"),
            "numerators": {
                "n_decrease": values.pop("n_decrease"),
                "n_increase": values.pop("n_increase"),
            },
        }
        return values, reasons, counts

    def design_se(mask: np.ndarray, statistic: str):
        if statistic in indicators:
            return (
                _design_se(
                    normalized,
                    mask & population,
                    indicators[statistic],
                    clusters_all,
                ),
                None,
            )
        return None, _NO_PERCENTILE_SE

    spec = _StaticSpec(
        statistics=STATIC_BENEFIT_STATISTICS,
        compute=compute,
        design_se=design_se,
        floor_notes={},
        population=population,
    )
    return _static_result(
        kind=STATIC_BENEFIT_KIND,
        rows=rows,
        assignment=assignment,
        normalized=normalized,
        spec=spec,
        id_column=id_column,
        design_summary=design_summary,
        floor_seeds=floor_seeds,
        floor_split_unit=floor_split_unit,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        output_labels=output_labels,
        post_hoc=post_hoc,
        statistic_id=statistic_id,
        upstream=recorded_upstream,
        extra_conventions={
            "population": (
                f"rows with {base_column} > 0 (current-law beneficiaries)"
            ),
            "change_definition": CHANGE_DEFINITION,
            "base_column": base_column,
            "reform_column": reform_column,
        },
    )
