"""Publication-revision floor for the SSA claim-age reference (#74, B2).

This builds ``runs/claiming_publication_floor_v1.json`` -- a REPORTED,
not gated, artifact. Changes no gate. It exists because the DRAFT
``gate_b2_claiming`` packet (lane ``cap-claiming-pia-gates``) derives
every tolerance it proposes from a floor artifact that did not exist:
the packet's own numbers were computed in that lane and labelled as
such. This builder measures the same quantities from committed inputs
so the packet rests on committed, test-pinned bytes.

Why a PUBLICATION floor and not a sampling floor
================================================
Every locked gate in ``gates.yaml`` prices its tolerances off sampling
noise (person-disjoint splits). Table 6.B5.1 admits no such floor: the
reference's own provenance records it as ``"Master Beneficiary Record,
100 percent data (not a sample) for these entitlement years
1998-2022"``. There is no sample, so no half-split null exists. The
measurable noise is REVISION plus ROUNDING, and SSA states the
mechanism in the table notes carried by both editions: *"Because
entitlements can be awarded retroactively, data for current and prior
years are subject to revision with each annual update of this table."*

What is measured
================
1. **Cross-edition revision.** The committed 2014 edition (entitlement
   years 1998-2013) against the committed 2023 edition on the 1998-2013
   overlap, in two spaces: the PUBLISHED eight-category shares and the
   CONDITIONAL seven-category shares (disability conversions dropped and
   the remainder renormalised to 100 -- the object
   :func:`populace_dynamics.claiming.claim_age_pmf` emits). Stratified
   into settled years (1998-2012) and the terminal year (2013), plus the
   ``average_age`` column.
2. **The derived power cap.** The DRAFT tolerance rule
   ``round(K_REV * revision_sd_terminal + |trend| * horizon + rounding,
   2)`` with the DRAFT knobs, and the gate-eligible / report-only
   partition it produces at ``T_max_pp = 3.0``. Which cells demote is
   DERIVED from the trend term, never hand-picked.
3. **Reference values.** The held-out conditional shares each cell would
   score against, for all 42 (category x sex x horizon) cells.
4. **Both holdout rules.** ``nearest_year`` and ``linear_trend`` fit on
   1998-2019 and scored on 2020-2022, in both spaces, with an explicit
   equality check against the committed ``runs/claiming_reference_v1.json``
   on the published construct the two share.
5. **Candidate rules on the DRAFT gated surface.** The deployed v1
   nearest-year rule fails 6 of the 34 DRAFT gate-eligible cells. That
   finding is REPORTED, NOT GATED -- there is no ``gate_b2_claiming``
   in ``gates.yaml``, this artifact proposes none, and no threshold
   here is ratified.

What the v2 revision adds (the two adversarial referees' lists)
===============================================================
The floors-v2 revision answers the referees' construction findings by
EMITTING every alternative they priced, so that the threshold-binding
ruling reads bytes rather than a referee's scratch script. Nothing in
the DRAFT ``gated_surface`` moves: the 42 tolerances and the 34 / 8
partition are the drafted grammar's and are unchanged. Added:

* ``sd_signed_pp`` (= the RMS of the signed revisions, since the
  conditional shares sum to 100 per row and the signed revisions sum to
  zero) on every stratum, a ``grammar_note``, and the partition and
  deployed-rule failure set under THREE grammars x K in {1.5, 2.0,
  2.5} plus the drafted grammar's K x rounding sweep
  (``power_cap_alternatives.grammar_and_k_sweep``).
* Settled years stratified by their settle age at the 2014 edition, and
  a horizon-aware pricing variant that prices h1 / h2 on the settled sd
  (``power_cap_alternatives.horizon_aware_pricing``).
* The OLS fit-window class widened (windows 13-18 named as rules; all
  windows 2-22 swept), the forecast envelope re-emitted over the
  widened class, and the packet's original window grid's envelope kept
  beside it.
* A stated rounding mode (Decimal ROUND_HALF_UP) evaluated in Decimal,
  the one exact tie (``age70plus|female|h2`` at 1.5250) named with both
  its half-up and half-even values, and the knife-edge class of cells
  whose unrounded tolerance sits within 0.002 pp of a 2-decimal
  boundary.
* The ``age66_before_fra`` transition year per sex, read from the 2023
  edition, and a seventh packet correction: the packet's d3(ii)
  demotion reason names the 2021 composition break for a cell that is
  entitlement year 2020.
* Per-failing-cell deviations and margins; the all-rules envelope; the
  published-construct forecast envelope; ``deviation_arithmetic``
  extended to every rule scored under both paths; a ``fit_isolation``
  block naming the channels that carry the held-out actuals; the
  ``number_thousands`` column's revision; and an ``open_decisions``
  block filing every ruling with its table beside it.

Nothing here is a threshold. No ``gates.yaml`` block is written, read
for binding, or implied to be locked.

Run from the repository root::

    .venv/bin/python scripts/build_claiming_publication_floor.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "runs" / "claiming_publication_floor_v1.json"

EDITION_2023_REL = "data/external/ssa_claim_ages_2023supplement.json"
EDITION_2014_REL = "data/external/ssa_claim_ages_2014supplement.json"
CLAIMING_REFERENCE_REL = "runs/claiming_reference_v1.json"

SCHEMA_VERSION = "claiming_publication_floor.v1"
RUN = "claiming_publication_floor_v1"

#: The stable eight-way published partition (Table 6.B5.1 collapsed).
PUBLISHED_CATEGORIES = (
    "age62",
    "age63",
    "age64",
    "age65",
    "age66",
    "disability_conversion",
    "age67_69",
    "age70plus",
)
#: The seven non-conversion categories the module's PMF spans.
CONDITIONAL_CATEGORIES = tuple(
    category
    for category in PUBLISHED_CATEGORIES
    if category != "disability_conversion"
)

SEXES = ("female", "male")

OVERLAP_YEARS = tuple(range(1998, 2014))
SETTLED_YEARS = tuple(range(1998, 2013))
TERMINAL_YEARS = (2013,)

FIT_YEARS = tuple(range(1998, 2020))
HOLDOUT_YEARS = (2020, 2021, 2022)
HORIZON_OF_YEAR = {2020: 1, 2021: 2, 2022: 3}

#: DRAFT tolerance knobs, quoted from the cap-claiming-pia-gates packet
#: (`gate_b2_claiming.thresholds.gated_surface.derivations.knobs`). They
#: are a PROPOSAL: no referee round has run and `gates.yaml` carries no
#: `gate_b2_claiming`.
K_REV = 2.0
ROUNDING_PP = 0.05
T_MAX_PP = 3.0
TOLERANCE_DECIMALS = 2
STAT_DECIMALS = 6

#: The rounding mode the DRAFT tolerance rule is evaluated under (v2).
#: The rule's three summands are each decimal quantities with at most
#: four decimals, so the sum is an exact decimal; one cell
#: (``age70plus|female|h2``, 1.5250) sits on an exact 2-decimal tie and
#: the drafted 1.53 is ROUND_HALF_UP's answer. Python's float ``round``
#: happened to agree only because of operand order, so the tolerance is
#: now evaluated in Decimal under the stated mode.
TOLERANCE_ROUNDING_MODE = "ROUND_HALF_UP"
#: Cells whose unrounded tolerance lies within this distance of a
#: 2-decimal rounding boundary are disclosed as the knife-edge class.
KNIFE_EDGE_BAND_PP = 0.002

#: The alternative grammars and knobs emitted for the threshold-binding
#: ruling. The DRAFT surface stays the drafted grammar's.
ALTERNATIVE_K_VALUES = (1.5, 2.0, 2.5)
ROUNDING_SWEEP_PP = (0.01, 0.05, 0.10)
K_SWEEP_VALUES = (1.5, 2.0, 2.5, 3.0)
#: The OLS fit-window rules the v2 revision names in the scanned class
#: (referee A: the class definition admits them; the enumeration omitted
#: them). Every window 2-22 is additionally swept in ols_window_sweep.
WIDENED_OLS_WINDOWS = (13, 14, 15, 16, 17, 18)
OLS_WINDOW_SWEEP = tuple(range(2, 23))
#: The raw column whose null-to-populated transition is the FRA
#: composition break the packet's d3(ii) names.
AGE66_BEFORE_FRA_COLUMN = "age66_before_fra"
TRANSITION_YEARS = tuple(range(2016, 2023))

PACKET = "cap-claiming-pia-gates REPORT.md (2026-09-06, drafting lane)"

#: The sentence in SSA's own table notes that states the revision
#: mechanism this floor measures. Verbatim in BOTH committed editions
#: (their full notes are not otherwise identical).
RETROACTIVE_SENTENCE = (
    "Because entitlements can be awarded retroactively, data for "
    "current and prior years are subject to revision with each annual "
    "update of this table."
)


# --------------------------------------------------------------------------
# Committed-byte helpers
# --------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text())


def _pin(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    return {
        "path": relative,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


# --------------------------------------------------------------------------
# The two share constructs
# --------------------------------------------------------------------------
def published_shares(row: dict[str, Any]) -> dict[str, float]:
    """The published eight-category collapsed shares, as published."""
    return {
        category: float(row["categories"][category])
        for category in PUBLISHED_CATEGORIES
    }


def conditional_shares(row: dict[str, Any]) -> dict[str, float]:
    """The seven non-conversion shares renormalised to sum to 100.

    This is the object ``claim_age_pmf`` emits, re-aggregated to the
    reference's own category partition: the disability-conversion
    column is dropped (an auto-conversion at FRA, not a claiming
    choice; source footnote b) and the remainder is renormalised.
    """
    categories = row["categories"]
    total = sum(categories[name] for name in CONDITIONAL_CATEGORIES)
    return {
        name: 100.0 * float(categories[name]) / total
        for name in CONDITIONAL_CATEGORIES
    }


CONSTRUCTS = {
    "published": (PUBLISHED_CATEGORIES, published_shares),
    "conditional": (CONDITIONAL_CATEGORIES, conditional_shares),
}


# --------------------------------------------------------------------------
# Statistics (closed form; no numpy, so the artifact is bit-stable)
# --------------------------------------------------------------------------
def _round(value: float, decimals: int = STAT_DECIMALS) -> float:
    return round(float(value), decimals)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _population_sd(values: list[float]) -> float:
    mean = _mean(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def _sample_sd(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5


def _ols_slope(xs: tuple[int, ...], ys: list[float]) -> tuple[float, float]:
    """Closed-form OLS slope and intercept (deterministic, no numpy)."""
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum(
        (x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)
    )
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = numerator / denominator
    return slope, mean_y - slope * mean_x


# --------------------------------------------------------------------------
# Cross-edition revision
# --------------------------------------------------------------------------
def _revision_cells(
    doc_2014: dict[str, Any],
    doc_2023: dict[str, Any],
    construct: str,
    years: tuple[int, ...],
) -> list[dict[str, Any]]:
    categories, shares = CONSTRUCTS[construct]
    cells: list[dict[str, Any]] = []
    for sex in SEXES:
        for year in years:
            old = shares(doc_2014["data"][sex][str(year)])
            new = shares(doc_2023["data"][sex][str(year)])
            for category in categories:
                raw = new[category] - old[category]
                cells.append(
                    {
                        "sex": sex,
                        "year": year,
                        "category": category,
                        "edition_2014_pp": _round(old[category]),
                        "edition_2023_pp": _round(new[category]),
                        "revision_pp": _round(raw),
                        # The UNROUNDED comparison, so the nonzero count
                        # uses the same predicate the reproduction test
                        # uses (referee B, D10): a revision below 5e-7 pp
                        # would otherwise round to 0.0 here and count as
                        # moved there.
                        "moved": raw != 0.0,
                        "revision_raw_pp": raw,
                    }
                )
    return cells


GRAMMAR_NOTE = (
    "The DRAFT revision term is K_REV * sd(|revision|): K multiplies the "
    "population sd of the ABSOLUTE per-cell revisions (sd_pp), a folded "
    "quantity whose own mean is mean_pp. That follows NEITHER of the two "
    "house grammars. gate-1 (tests/test_gates_derivations.py) derives "
    "every locked threshold as round(floor mean + k * floor sd, "
    "rounding) -- a mean term the DRAFT rule drops. gate_w1 family B "
    "(gates.yaml, family_b.tolerance_rule) derives round(K_VINTAGE * "
    "detrended_residual_sd + |trend| * delta + MEASUREMENT_PP, 2) with "
    "no mean term, but K there multiplies the sd of a zero-mean "
    "residual; the zero-mean analogue here is the SIGNED revision, "
    "whose sd equals its RMS (sd_signed_pp) because the conditional "
    "shares sum to 100 in every (sex, year) row and the signed revisions "
    "therefore sum to zero. On the terminal stratum sd_signed_pp is "
    "roughly 1.7x sd_pp. power_cap_alternatives.grammar_and_k_sweep "
    "emits the partition and the deployed-rule failure set under all "
    "three grammars so the ruling reads bytes; the DRAFT gated_surface "
    "stays the drafted grammar's until that ruling."
)


def _stratum(cells: list[dict[str, Any]]) -> dict[str, Any]:
    magnitudes = [abs(cell["revision_pp"]) for cell in cells]
    signed = [cell["revision_pp"] for cell in cells]
    argmax = max(cells, key=lambda cell: abs(cell["revision_pp"]))
    return {
        "n_cells": len(cells),
        "nonzero_cells": sum(1 for cell in cells if cell["moved"]),
        "mean_pp": _round(_mean(magnitudes)),
        "sd_pp": _round(_population_sd(magnitudes)),
        "sd_sample_pp": _round(_sample_sd(magnitudes)),
        "max_pp": _round(max(magnitudes)),
        "mean_signed_pp": _round(_mean(signed)),
        "sd_signed_pp": _round(_population_sd(signed)),
        "rms_signed_pp": _round(
            (sum(v * v for v in signed) / len(signed)) ** 0.5
        ),
        "n_cells_with_abs_revision_above_k_rev_times_sd_pp": sum(
            1 for m in magnitudes if m > K_REV * _population_sd(magnitudes)
        ),
        "argmax": {
            "sex": argmax["sex"],
            "year": argmax["year"],
            "category": argmax["category"],
            "revision_pp": argmax["revision_pp"],
        },
        "sd_convention": (
            "sd_pp is the POPULATION standard deviation (ddof=0) of the "
            "absolute per-cell revisions; sd_sample_pp is the ddof=1 "
            "value. The DRAFT tolerance knob quotes sd_pp. sd_signed_pp "
            "is the population sd of the SIGNED revisions and "
            "rms_signed_pp their root-mean-square; the two coincide "
            "exactly wherever the signed revisions sum to zero "
            "(mean_signed_pp == 0), which holds on every conditional "
            "stratum by construction. "
            "n_cells_with_abs_revision_above_k_rev_times_sd_pp counts "
            "the stratum's own cells whose revision exceeds the DRAFT "
            "K_REV * sd_pp allowance."
        ),
        "grammar_note": GRAMMAR_NOTE,
    }


def _settle_age_strata(
    doc_2014: dict[str, Any], doc_2023: dict[str, Any], construct: str
) -> dict[str, Any]:
    """The settled years stratified by their settle age at publication.

    The 2014 edition publishes through entitlement year 2013, so a
    settled year y had (2013 - y) years of settling when that edition
    was published. Stratifying by settle age shows what the pair
    already measures about the settle PATH (referee A, F4): the rows
    that were one, two and three years settled at publication moved
    by exactly 0.0 in every conditional cell between the editions.
    That bears on horizon pricing, because in the 2023 edition h1 =
    2020 is three years settled and h2 = 2021 is two.
    """
    by_age: dict[str, Any] = {}
    for year in sorted(SETTLED_YEARS, reverse=True):
        settle_age = TERMINAL_YEARS[0] - year
        cells = _revision_cells(doc_2014, doc_2023, construct, (year,))
        magnitudes = [abs(cell["revision_pp"]) for cell in cells]
        by_age[str(settle_age)] = {
            "entitlement_year": year,
            "settle_age_years_at_2014_publication": settle_age,
            "n_cells": len(cells),
            "nonzero_cells": sum(1 for cell in cells if cell["moved"]),
            "mean_pp": _round(_mean(magnitudes)),
            "sd_pp": _round(_population_sd(magnitudes)),
            "max_pp": _round(max(magnitudes)),
        }
    zero_ages = sorted(
        int(age) for age, block in by_age.items() if block["max_pp"] == 0.0
    )
    return {
        "definition": (
            "settle_age = 2013 - entitlement_year: how many annual "
            "updates the row had received when the 2014 edition was "
            "published (its terminal year 2013 had zero)"
        ),
        "by_settle_age": by_age,
        "settle_ages_with_zero_revision": zero_ages,
        "settle_ages_with_any_revision": sorted(
            int(age) for age, block in by_age.items() if block["max_pp"] > 0
        ),
        "rows_one_to_three_years_settled_moved": any(
            by_age[str(age)]["nonzero_cells"] > 0 for age in (1, 2, 3)
        ),
        "finding": (
            "The rows that were one, two and three years settled at the "
            "2014 publication (entitlement years 2012, 2011, 2010) show "
            "zero revision in every cell of this construct; the only "
            "settled row that moved is 2008 (five years settled), by one "
            "0.1 pp published rounding tick. So the pair already "
            "measures the first steps of the settle path, at share "
            "resolution, even though the 2021 and 2022 editions are not "
            "staged."
        ),
    }


def _number_thousands_stratum(
    doc_2014: dict[str, Any], doc_2023: dict[str, Any]
) -> dict[str, Any]:
    """The award-count column's revision (referee A, F11).

    The share table is what the floor prices, but the ``number_thousands``
    column is in the committed bytes too and it DID revise in settled
    years -- below the share table's rounding, but it is the underlying
    record the shares are computed from, so the claim 'revision is
    entirely a terminal-year effect' is recorded here as a statement
    about rounded shares, with the count column measured beside it.
    """
    rows = []
    for sex in SEXES:
        for year in OVERLAP_YEARS:
            old = int(doc_2014["data"][sex][str(year)]["number_thousands"])
            new = int(doc_2023["data"][sex][str(year)]["number_thousands"])
            rows.append(
                {
                    "sex": sex,
                    "year": year,
                    "settle_age_years_at_2014_publication": (
                        TERMINAL_YEARS[0] - year
                    ),
                    "edition_2014_thousands": old,
                    "edition_2023_thousands": new,
                    "revision_thousands": new - old,
                    "revision_share_of_2014_count": _round((new - old) / old),
                }
            )
    moved = [row for row in rows if row["revision_thousands"] != 0]
    settled_moved = [row for row in moved if row["year"] in SETTLED_YEARS]
    terminal_moved = [row for row in moved if row["year"] in TERMINAL_YEARS]
    return {
        "column": "number_thousands",
        "n_rows": len(rows),
        "nonzero_rows": len(moved),
        "nonzero_settled_rows": len(settled_moved),
        "nonzero_terminal_rows": len(terminal_moved),
        "max_abs_revision_share_settled": _round(
            max(
                (
                    abs(row["revision_share_of_2014_count"])
                    for row in settled_moved
                ),
                default=0.0,
            )
        ),
        "max_abs_revision_share_terminal": _round(
            max(
                (
                    abs(row["revision_share_of_2014_count"])
                    for row in terminal_moved
                ),
                default=0.0,
            )
        ),
        "moved_rows": moved,
        "finding": (
            "The award counts revised in settled years too (by about a "
            "tenth of a percent, two to four years after publication) "
            "and by several percent in the terminal year. 'Revision is "
            "entirely a terminal-year effect' is therefore a statement "
            "about the published shares at 0.1 pp resolution, not about "
            "the underlying record; the share-table floor is unaffected "
            "because the count revisions sit below the share rounding."
        ),
    }


def _average_age_stratum(
    doc_2014: dict[str, Any], doc_2023: dict[str, Any]
) -> dict[str, Any]:
    rows = []
    for sex in SEXES:
        for year in OVERLAP_YEARS:
            old = float(doc_2014["data"][sex][str(year)]["average_age"])
            new = float(doc_2023["data"][sex][str(year)]["average_age"])
            rows.append(
                {
                    "sex": sex,
                    "year": year,
                    "edition_2014_years": old,
                    "edition_2023_years": new,
                    "revision_years": _round(new - old),
                }
            )
    magnitudes = [abs(row["revision_years"]) for row in rows]
    return {
        "n_rows": len(rows),
        "nonzero_rows": sum(1 for m in magnitudes if m > 0.0),
        "mean_years": _round(_mean(magnitudes)),
        "max_years": _round(max(magnitudes)),
    }


# --------------------------------------------------------------------------
# The DRAFT tolerance surface
# --------------------------------------------------------------------------
def _cell_key(category: str, sex: str, horizon: int) -> str:
    return f"{category}|{sex}|h{horizon}"


def _fit_series(
    doc_2023: dict[str, Any], construct: str
) -> dict[tuple[str, str], list[float]]:
    _, shares = CONSTRUCTS[construct]
    return {
        (category, sex): [
            shares(doc_2023["data"][sex][str(year)])[category]
            for year in FIT_YEARS
        ]
        for sex in SEXES
        for category in CONSTRUCTS[construct][0]
    }


def _actuals(
    doc_2023: dict[str, Any], construct: str
) -> dict[tuple[str, str, int], float]:
    _, shares = CONSTRUCTS[construct]
    return {
        (category, sex, HORIZON_OF_YEAR[year]): shares(
            doc_2023["data"][sex][str(year)]
        )[category]
        for sex in SEXES
        for category in CONSTRUCTS[construct][0]
        for year in HOLDOUT_YEARS
    }


_ROUNDING_MODES = {
    "ROUND_HALF_UP": ROUND_HALF_UP,
    "ROUND_HALF_EVEN": ROUND_HALF_EVEN,
}
_QUANTUM = Decimal(1).scaleb(-TOLERANCE_DECIMALS)


def _decimal(value: float) -> Decimal:
    """The exact decimal a float knob was written as (via repr)."""
    return Decimal(repr(value))


def _unrounded_tolerance(
    revision_term_pp: float, trend: float, horizon: int, rounding_pp: float
) -> Decimal:
    """The exact decimal sum of the three tolerance summands."""
    return (
        _decimal(revision_term_pp)
        + _decimal(abs(trend)) * horizon
        + _decimal(rounding_pp)
    )


def _quantize(value: Decimal, mode: str = TOLERANCE_ROUNDING_MODE) -> float:
    return float(value.quantize(_QUANTUM, rounding=_ROUNDING_MODES[mode]))


def _tolerance_from_term(
    revision_term_pp: float,
    trend: float,
    horizon: int,
    rounding_pp: float = ROUNDING_PP,
) -> float:
    """round(revision_term + |trend| * h + rounding, 2) in Decimal under
    the stated rounding mode; the revision term is whatever grammar the
    caller prices (the DRAFT's is K_REV * sd_knob)."""
    return _quantize(
        _unrounded_tolerance(revision_term_pp, trend, horizon, rounding_pp)
    )


def _tolerance(sd_pp: float, trend: float, horizon: int) -> float:
    return _tolerance_from_term(round(K_REV * sd_pp, 6), trend, horizon)


def _float_path_tolerance(sd_pp: float, trend: float, horizon: int) -> float:
    """The v1 builder's float evaluation, kept so the artifact records
    that the stated Decimal mode reproduces it on every cell."""
    return round(
        K_REV * sd_pp + abs(trend) * horizon + ROUNDING_PP,
        TOLERANCE_DECIMALS,
    )


def _distance_to_rounding_boundary(value: Decimal) -> Decimal:
    """Distance from ``value`` to the nearest x.xx5 boundary."""
    scaled = value / _QUANTUM
    fractional = scaled - scaled.to_integral_value(rounding="ROUND_FLOOR")
    return abs(fractional - Decimal("0.5")) * _QUANTUM


def _power_cap(
    fit_series: dict[tuple[str, str], list[float]],
    sd_knob: float,
    sd_full: float,
) -> dict[str, Any]:
    gated: dict[str, float] = {}
    report_only: dict[str, dict[str, Any]] = {}
    derivations: dict[str, dict[str, Any]] = {}
    knob_sensitive: dict[str, dict[str, Any]] = {}
    eligibility_flips: list[str] = []
    knife_edge: dict[str, dict[str, Any]] = {}
    exact_ties: dict[str, dict[str, Any]] = {}
    float_path_disagreements: list[str] = []
    for sex in SEXES:
        for category in CONDITIONAL_CATEGORIES:
            slope, _ = _ols_slope(FIT_YEARS, fit_series[(category, sex)])
            trend = round(slope, 4)
            for horizon in (1, 2, 3):
                key = _cell_key(category, sex, horizon)
                unrounded = _unrounded_tolerance(
                    round(K_REV * sd_knob, 6), trend, horizon, ROUNDING_PP
                )
                tolerance = _quantize(unrounded)
                half_even = _quantize(unrounded, "ROUND_HALF_EVEN")
                float_path = _float_path_tolerance(sd_knob, trend, horizon)
                if float_path != tolerance:
                    float_path_disagreements.append(key)
                # The full-precision sd is a float, not a decimal knob;
                # its tolerance is the v1 float evaluation, as before.
                at_full = _float_path_tolerance(sd_full, trend, horizon)
                if (tolerance <= T_MAX_PP) != (at_full <= T_MAX_PP):
                    eligibility_flips.append(key)
                if tolerance != at_full:
                    knob_sensitive[key] = {
                        "tolerance_pp_at_rounded_sd": tolerance,
                        "tolerance_pp_at_full_precision_sd": at_full,
                        "unrounded_pp": float(unrounded),
                    }
                distance = _distance_to_rounding_boundary(unrounded)
                if distance < _decimal(KNIFE_EDGE_BAND_PP):
                    knife_edge[key] = {
                        "unrounded_tolerance_pp": float(unrounded),
                        "tolerance_pp": tolerance,
                        "distance_to_boundary_pp": float(distance),
                        "is_exact_tie": distance == 0,
                        "gate_eligible": tolerance <= T_MAX_PP,
                    }
                if distance == 0:
                    exact_ties[key] = {
                        "unrounded_tolerance_pp": float(unrounded),
                        "round_half_up_pp": tolerance,
                        "round_half_even_pp": half_even,
                        "drafted_pp": tolerance,
                    }
                derivations[key] = {
                    "trend_pp_per_year": trend,
                    "horizon_years": horizon,
                    "rounding": TOLERANCE_DECIMALS,
                    "rounding_mode": TOLERANCE_ROUNDING_MODE,
                    "unrounded_tolerance_pp": float(unrounded),
                    "tolerance_pp": tolerance,
                    "tolerance_pp_round_half_even": half_even,
                    "tolerance_pp_at_full_precision_sd": at_full,
                }
                if tolerance <= T_MAX_PP:
                    gated[key] = tolerance
                else:
                    report_only[key] = {
                        "tolerance_pp_would_be": tolerance,
                        "trend_pp_per_year": trend,
                        "reason": "tolerance_above_t_max",
                    }
    return {
        "rule": (
            "tolerance_pp == round(K_REV * revision_sd_terminal_pp + "
            "abs(trend_pp_per_year) * horizon_years + rounding_pp, 2); "
            "a cell is gate-eligible iff tolerance_pp <= t_max_pp"
        ),
        "rounding_mode": {
            "mode": TOLERANCE_ROUNDING_MODE,
            "arithmetic": (
                "the three summands are exact decimals (the sd knob has "
                "4 decimals, the trend 4, the rounding allowance 2), so "
                "the sum is formed in Decimal and quantized to 2 "
                "decimals under the stated mode; the v1 builder's float "
                "evaluation reproduced the same 42 values only because "
                "of operand order on the one exact tie"
            ),
            "float_path_reproduces_every_tolerance": (
                not float_path_disagreements
            ),
            "float_path_disagreements": float_path_disagreements,
            "exact_ties": exact_ties,
            "n_exact_ties": len(exact_ties),
            "tie_note": (
                "An exact tie is a cell whose unrounded tolerance ends in "
                "5 at the third decimal. ROUND_HALF_UP and ROUND_HALF_EVEN "
                "differ there and nowhere else; both values are recorded "
                "per tie cell, and the drafted value is ROUND_HALF_UP's."
            ),
        },
        "knife_edge_class": {
            "band_pp": KNIFE_EDGE_BAND_PP,
            "definition": (
                "cells whose UNROUNDED tolerance lies within band_pp of "
                "a 2-decimal rounding boundary (x.xx5). Any change to "
                "the fourth decimal of the sd knob, to the trend "
                "rounding or to rounding_pp can move these tolerances "
                "by one cent; the sd knob's own rounding happens to "
                "move exactly one of them (see sd_knob_rounding_check)."
            ),
            "n_cells": len(knife_edge),
            "cells": knife_edge,
        },
        "grammar_note": GRAMMAR_NOTE,
        "knobs": {
            "k_rev": K_REV,
            "revision_sd_terminal_pp": sd_knob,
            "revision_sd_terminal_pp_full_precision": _round(sd_full),
            "revision_term_pp": round(K_REV * sd_knob, 6),
            "rounding_pp": ROUNDING_PP,
            "t_max_pp": T_MAX_PP,
            "fit_window": [FIT_YEARS[0], FIT_YEARS[-1]],
            "horizon_years": [1, 2, 3],
            "trend_estimator": (
                "closed-form OLS slope of the conditional share on the "
                "fit years, rounded to 4 decimals"
            ),
        },
        "knobs_are_a_draft_proposal": (
            "K_REV, the rounding allowance and T_max_pp are quoted from "
            f"the {PACKET} DRAFT gate_b2_claiming block. gates.yaml "
            "carries no gate_b2_claiming; nothing here is ratified and "
            "this artifact proposes no threshold."
        ),
        "sd_knob_rounding_check": {
            "note": (
                "The DRAFT knob rounds the measured terminal-year sd to "
                "4 decimals. This block records every cell whose "
                "2-decimal tolerance changes when the full-precision sd "
                "is used instead, and whether any cell's gate-eligible "
                "status changes with it."
            ),
            "partition_identical": not eligibility_flips,
            "n_gate_eligibility_flips": len(eligibility_flips),
            "gate_eligibility_flips": sorted(eligibility_flips),
            "n_cells_with_a_different_tolerance": len(knob_sensitive),
            "cells_with_a_different_tolerance": knob_sensitive,
        },
        "n_gate_eligible": len(gated),
        "n_report_only_tolerance_above_t_max": len(report_only),
        "gate_eligible_tolerances_pp": gated,
        "report_only_tolerance_above_t_max": report_only,
        "derivations": derivations,
        "out_of_module_scope": {
            "cells": [
                _cell_key("disability_conversion", sex, horizon)
                for sex in SEXES
                for horizon in (1, 2, 3)
            ],
            "reason": "conversion_flow_owned_by_di_surface",
            "basis": (
                "The conditional construct excludes the "
                "disability-conversion column before any tolerance is "
                "derived, so these six cells never enter the surface. "
                "They are named here so the exclusion is visible as a "
                "SCOPE decision taken before any candidate runs, not a "
                "power-cap demotion and not a candidate's performance."
            ),
        },
    }


# --------------------------------------------------------------------------
# Alternatives the referees priced (emitted, not chosen)
# --------------------------------------------------------------------------
def _trends(
    fit_series: dict[tuple[str, str], list[float]],
) -> dict[tuple[str, str], float]:
    return {
        (category, sex): round(
            _ols_slope(FIT_YEARS, fit_series[(category, sex)])[0], 4
        )
        for sex in SEXES
        for category in CONDITIONAL_CATEGORIES
    }


def _partition_under(
    trends: dict[tuple[str, str], float],
    revision_term_by_horizon: dict[int, float],
    rounding_pp: float,
    fit_series: dict[tuple[str, str], list[float]],
    actuals: dict[tuple[str, str, int], float],
    draft_gated: dict[str, float],
) -> dict[str, Any]:
    """The partition, tolerances and deployed-rule failure set that a
    given revision term (per horizon) and rounding allowance imply,
    under the DRAFT rule's other parts (the |trend| * h term, T_max, the
    2-decimal Decimal ROUND_HALF_UP quantisation)."""
    gated: dict[str, float] = {}
    report_only: dict[str, float] = {}
    for sex in SEXES:
        for category in CONDITIONAL_CATEGORIES:
            for horizon in (1, 2, 3):
                key = _cell_key(category, sex, horizon)
                tolerance = _tolerance_from_term(
                    revision_term_by_horizon[horizon],
                    trends[(category, sex)],
                    horizon,
                    rounding_pp,
                )
                (gated if tolerance <= T_MAX_PP else report_only)[
                    key
                ] = tolerance
    failures = []
    for key, tolerance in gated.items():
        category, sex, horizon = key.split("|")
        horizon_n = int(horizon[1:])
        deviation = abs(
            fit_series[(category, sex)][-1]
            - actuals[(category, sex, horizon_n)]
        )
        if deviation > tolerance:
            failures.append(key)
    knife = _cell_key("age66", "female", 1)
    ols_full = _candidate_predictors(fit_series)["ols_full_fit_window"][
        "predict"
    ]
    ols_full_deviation = round(
        abs(ols_full("age66", "female", 1) - actuals[("age66", "female", 1)]),
        4,
    )
    return {
        "revision_term_pp_by_horizon": {
            f"h{h}": term
            for h, term in sorted(revision_term_by_horizon.items())
        },
        "rounding_pp": rounding_pp,
        "n_gate_eligible": len(gated),
        "n_report_only_tolerance_above_t_max": len(report_only),
        "partition_identical_to_draft": set(gated) == set(draft_gated),
        "cells_demoted_relative_to_draft": sorted(
            set(draft_gated) - set(gated)
        ),
        "cells_promoted_relative_to_draft": sorted(
            set(gated) - set(draft_gated)
        ),
        "n_tolerances_differing_from_draft": sum(
            1
            for key, tolerance in gated.items()
            if key in draft_gated and draft_gated[key] != tolerance
        ),
        "deployed_v1_n_failed": len(failures),
        "deployed_v1_failing_cells": sorted(failures),
        "age66_female_h1": {
            "gate_eligible": knife in gated,
            "tolerance_pp": gated.get(knife, report_only.get(knife)),
            "ols_full_fit_window_deviation_pp": ols_full_deviation,
            "ols_full_fit_window_clears": (
                knife in gated and ols_full_deviation <= gated[knife]
            ),
        },
        "gate_eligible_tolerances_pp": gated,
        "report_only_tolerance_above_t_max_pp": report_only,
    }


def _power_cap_alternatives(
    fit_series: dict[tuple[str, str], list[float]],
    actuals: dict[tuple[str, str, int], float],
    terminal: dict[str, Any],
    settled: dict[str, Any],
    draft_gated: dict[str, float],
) -> dict[str, Any]:
    trends = _trends(fit_series)
    sd_abs = terminal["sd_pp"]
    sd_knob = round(sd_abs, 4)
    mean_abs = terminal["mean_pp"]
    sd_signed_knob = round(terminal["sd_signed_pp"], 4)
    max_abs = terminal["max_pp"]
    settled_knob = round(settled["sd_pp"], 4)

    grammars = {
        "k_times_sd_abs_DRAFT": {
            "formula": "K * sd(|revision|)",
            "is_the_draft_grammar": True,
            "house_precedent": None,
            "term": lambda k: round(k * sd_knob, 6),
        },
        "mean_plus_k_times_sd_abs": {
            "formula": "mean(|revision|) + K * sd(|revision|)",
            "is_the_draft_grammar": False,
            "house_precedent": (
                "gate-1: tests/test_gates_derivations.py derives every "
                "locked threshold as round(floor mean + k * floor sd, "
                "rounding)"
            ),
            "term": lambda k: round(mean_abs + k * sd_knob, 6),
        },
        "k_times_sd_signed": {
            "formula": "K * sd(signed revision) (== K * RMS here)",
            "is_the_draft_grammar": False,
            "house_precedent": (
                "gate_w1 family B: K multiplies the sd of a zero-mean "
                "(detrended) residual; the zero-mean analogue of the "
                "revision is the SIGNED revision, whose row sums are zero"
            ),
            "term": lambda k: round(k * sd_signed_knob, 6),
        },
        "max_abs_revision_d2": {
            "formula": "max(|revision|) (K does not enter)",
            "is_the_draft_grammar": False,
            "house_precedent": (
                "the packet's own open decision d2 names a max-based "
                "alternative to K_REV"
            ),
            "term": lambda k: round(max_abs, 6),
        },
    }
    by_grammar: dict[str, Any] = {}
    for name, spec in grammars.items():
        rows = {}
        for k in ALTERNATIVE_K_VALUES:
            term = spec["term"](k)
            rows[f"K_{k}"] = _partition_under(
                trends,
                {1: term, 2: term, 3: term},
                ROUNDING_PP,
                fit_series,
                actuals,
                draft_gated,
            )
        by_grammar[name] = {
            "formula": spec["formula"],
            "is_the_draft_grammar": spec["is_the_draft_grammar"],
            "house_precedent": spec["house_precedent"],
            "inputs": {
                "mean_abs_pp": mean_abs,
                "sd_abs_knob_pp": sd_knob,
                "sd_signed_knob_pp": sd_signed_knob,
                "max_abs_pp": max_abs,
            },
            "by_k": rows,
        }

    rounding_sweep = {}
    for k in K_SWEEP_VALUES:
        for rounding_pp in ROUNDING_SWEEP_PP:
            term = round(k * sd_knob, 6)
            row = _partition_under(
                trends,
                {1: term, 2: term, 3: term},
                rounding_pp,
                fit_series,
                actuals,
                draft_gated,
            )
            rounding_sweep[f"K_{k}|rounding_{rounding_pp}"] = {
                key: row[key]
                for key in (
                    "n_gate_eligible",
                    "n_report_only_tolerance_above_t_max",
                    "partition_identical_to_draft",
                    "cells_demoted_relative_to_draft",
                    "deployed_v1_n_failed",
                    "deployed_v1_failing_cells",
                )
            }
            rounding_sweep[f"K_{k}|rounding_{rounding_pp}"][
                "age66_female_h1_tolerance_pp"
            ] = row["age66_female_h1"]["tolerance_pp"]

    horizon_aware = _partition_under(
        trends,
        {
            1: round(K_REV * settled_knob, 6),
            2: round(K_REV * settled_knob, 6),
            3: round(K_REV * sd_knob, 6),
        },
        ROUNDING_PP,
        fit_series,
        actuals,
        draft_gated,
    )

    return {
        "purpose": (
            "Every alternative the two adversarial referees priced, "
            "EMITTED so the threshold-binding ruling compares committed "
            "bytes rather than a referee's scratch script. Nothing here "
            "is chosen: the DRAFT gated_surface (power_cap) stays the "
            "drafted grammar's at K_REV 2.0 and rounding 0.05 until the "
            "ruling filed in open_decisions."
        ),
        "shared_machinery": (
            "each variant keeps the DRAFT rule's |trend| * h term, its "
            "T_max_pp, its 2-decimal Decimal ROUND_HALF_UP quantisation "
            "and its trend estimator; only the revision term (and, in "
            "the rounding sweep, rounding_pp) changes. The deployed-v1 "
            "failure set is the nearest-year rule scored with the "
            "unrounded-prediction arithmetic against each variant's "
            "gate-eligible tolerances."
        ),
        "grammar_and_k_sweep": {
            "k_values": list(ALTERNATIVE_K_VALUES),
            "rounding_pp": ROUNDING_PP,
            "by_grammar": by_grammar,
        },
        "draft_grammar_k_by_rounding_sweep": {
            "k_values": list(K_SWEEP_VALUES),
            "rounding_values_pp": list(ROUNDING_SWEEP_PP),
            "rows": rounding_sweep,
        },
        "horizon_aware_pricing": {
            "derivation": (
                "In the 2023 edition h1 = 2020 is three years settled "
                "and h2 = 2021 two years settled; only h3 = 2022 is "
                "terminal. The 2014/2023 pair shows zero share revision "
                "for every row one or more years settled except the "
                "2008 row's single rounding tick "
                "(strata_by_settle_age). This variant therefore prices "
                "h1 and h2 on the conditional SETTLED-years sd "
                f"({settled_knob} pp, the rounded "
                "conditional_settled_years.sd_pp) and h3 on the "
                f"terminal sd ({sd_knob} pp), with K_REV, rounding_pp, "
                "the trend term and T_max unchanged. The settled sd is "
                "itself conservative for h1 / h2: the rows exactly "
                "three and two years settled (2010, 2011) moved by 0.0."
            ),
            "knobs": {
                "k_rev": K_REV,
                "revision_sd_h1_h2_pp": settled_knob,
                "revision_sd_h3_pp": sd_knob,
                "rounding_pp": ROUNDING_PP,
                "t_max_pp": T_MAX_PP,
            },
            "result": horizon_aware,
            "reading": (
                "Pricing all three horizons on the terminal sd hands h1 "
                "and h2 about "
                f"{round(K_REV * (sd_knob - settled_knob), 4)} pp of "
                "allowance the pair says they do not need; the DRAFT "
                "calls that conservative, and this block prices what "
                "'conservative' costs in cells and in deployed-rule "
                "failures. It does not decide: the 2021 and 2022 "
                "editions would measure the settle path of a terminal "
                "year directly, and the ruling is filed in "
                "open_decisions."
            ),
        },
    }


# --------------------------------------------------------------------------
# Holdout rules
# --------------------------------------------------------------------------
def _predict(
    rule: str,
    fit_values: list[float],
    slope: float,
    intercept: float,
    year: int,
) -> float:
    if rule == "nearest_year":
        return fit_values[-1]
    if rule == "linear_trend":
        return intercept + slope * year
    raise ValueError(rule)


def _holdout_block(
    doc_2023: dict[str, Any], construct: str, rule: str
) -> dict[str, Any]:
    categories, shares = CONSTRUCTS[construct]
    per_cell: list[dict[str, Any]] = []
    # The published-construct arithmetic is byte-identical to
    # scripts/build_claiming_reference.py: predictions are rounded to 4
    # decimals and the deviation is the rounded difference, so the two
    # artifacts' headline numbers are comparable without translation.
    for sex in ("male", "female") if construct == "published" else SEXES:
        for category in categories:
            fit_values = [
                shares(doc_2023["data"][sex][str(year)])[category]
                for year in FIT_YEARS
            ]
            slope, intercept = _ols_slope(FIT_YEARS, fit_values)
            for year in HOLDOUT_YEARS:
                actual = shares(doc_2023["data"][sex][str(year)])[category]
                predicted = _predict(rule, fit_values, slope, intercept, year)
                per_cell.append(
                    {
                        "sex": sex,
                        "year": year,
                        "horizon": HORIZON_OF_YEAR[year],
                        "category": category,
                        "predicted": round(predicted, 4),
                        "actual": round(actual, 4),
                        "deviation": round(round(predicted, 4) - actual, 4),
                    }
                )
    magnitudes = [abs(cell["deviation"]) for cell in per_cell]
    argmax = max(per_cell, key=lambda cell: abs(cell["deviation"]))
    return {
        "n_cells": len(per_cell),
        "max_abs_deviation": round(max(magnitudes), 4),
        "mean_abs_deviation": round(_mean(magnitudes), 4),
        "rmse": round(
            (sum(m * m for m in magnitudes) / len(magnitudes)) ** 0.5, 4
        ),
        "argmax": argmax,
        "per_cell": per_cell,
    }


def _reference_cross_check(published: dict[str, Any]) -> dict[str, Any]:
    """Equality check against the committed claiming_reference_v1."""
    committed = _load(CLAIMING_REFERENCE_REL)
    checks = {}
    matches = True
    for rule in ("nearest_year", "linear_trend"):
        theirs = committed["results"][rule]
        ours = published[rule]
        row = {
            "committed_max_abs_deviation": theirs["max_abs_deviation"],
            "rebuilt_max_abs_deviation": ours["max_abs_deviation"],
            "committed_mean_abs_deviation": theirs["mean_abs_deviation"],
            "rebuilt_mean_abs_deviation": ours["mean_abs_deviation"],
            "committed_rmse": theirs["rmse"],
            "rebuilt_rmse": ours["rmse"],
            "committed_n_cells": theirs["n_cells"],
            "rebuilt_n_cells": ours["n_cells"],
        }
        row["match"] = (
            theirs["max_abs_deviation"] == ours["max_abs_deviation"]
            and theirs["mean_abs_deviation"] == ours["mean_abs_deviation"]
            and theirs["rmse"] == ours["rmse"]
            and theirs["n_cells"] == ours["n_cells"]
        )
        matches = matches and row["match"]
        checks[rule] = row
    return {
        "artifact": CLAIMING_REFERENCE_REL,
        "artifact_pin": _pin(CLAIMING_REFERENCE_REL),
        "overlap": (
            "the PUBLISHED eight-category construct and the same "
            "fit 1998-2019 / predict 2020-2022 protocol; "
            "claiming_reference_v1 scores only that construct"
        ),
        "all_match": matches,
        "rules": checks,
    }


# --------------------------------------------------------------------------
# Candidate rules on the DRAFT gate-eligible surface
# --------------------------------------------------------------------------
def _candidate_predictors(
    fit_series: dict[tuple[str, str], list[float]],
) -> dict[str, Any]:
    """Named rules, each a callable (category, sex, horizon) -> pp."""

    def nearest_year(category, sex, horizon):
        return fit_series[(category, sex)][-1]

    def uniform(category, sex, horizon):
        return 100.0 / len(CONDITIONAL_CATEGORIES)

    def fit_window_mean(category, sex, horizon):
        return _mean(fit_series[(category, sex)])

    def sex_pooled_nearest_year(category, sex, horizon):
        return _mean([fit_series[(category, other)][-1] for other in SEXES])

    def ols(window):
        def predict(category, sex, horizon):
            values = fit_series[(category, sex)][-window:]
            years = FIT_YEARS[-window:]
            slope, intercept = _ols_slope(years, values)
            return intercept + slope * (FIT_YEARS[-1] + horizon)

        return predict

    def damped(window, delta):
        def predict(category, sex, horizon):
            values = fit_series[(category, sex)][-window:]
            years = FIT_YEARS[-window:]
            slope, _ = _ols_slope(years, values)
            return fit_series[(category, sex)][-1] + delta * slope * horizon

        return predict

    return {
        "deployed_v1_nearest_year": {
            "rule_class": "forecast",
            "description": (
                "the module's documented default: predict every "
                "out-of-range year with the last fit year (2019) "
                "(populace_dynamics.claiming._resolve_year)"
            ),
            "predict": nearest_year,
        },
        "uniform_over_seven_categories": {
            "rule_class": "degenerate",
            "description": "every category 100/7 pp",
            "predict": uniform,
        },
        "fit_window_mean": {
            "rule_class": "degenerate",
            "description": "predict each cell by its own 1998-2019 mean",
            "predict": fit_window_mean,
        },
        "sex_pooled_nearest_year": {
            "rule_class": "degenerate",
            "description": "nearest-year with the two sexes averaged",
            "predict": sex_pooled_nearest_year,
        },
        "ols_full_fit_window": {
            "rule_class": "forecast",
            "description": "OLS on all 22 fit years, extrapolated",
            "predict": ols(22),
        },
        "ols_last_10": {
            "rule_class": "forecast",
            "description": "OLS on the last ten fit years",
            "predict": ols(10),
        },
        "ols_last_5": {
            "rule_class": "forecast",
            "description": "OLS on the last five fit years (2015-2019)",
            "predict": ols(5),
        },
        "ols_last_3": {
            "rule_class": "forecast",
            "description": "OLS on the last three fit years",
            "predict": ols(3),
        },
        "damped_local_trend_w5_d0.5": {
            "rule_class": "forecast",
            "description": "last fit value plus half the 5-year slope",
            "predict": damped(5, 0.5),
        },
        "damped_local_trend_w5_d1.0": {
            "rule_class": "forecast",
            "description": "last fit value plus the full 5-year slope",
            "predict": damped(5, 1.0),
        },
        "damped_local_trend_w10_d0.5": {
            "rule_class": "forecast",
            "description": "last fit value plus half the 10-year slope",
            "predict": damped(10, 0.5),
        },
        **{
            f"ols_last_{window}": {
                "rule_class": "forecast",
                "description": (
                    f"OLS on the last {window} fit years "
                    f"({FIT_YEARS[-window]}-{FIT_YEARS[-1]}); added in "
                    "v2 -- the class definition admits every fit "
                    "window and the packet's grid scanned only "
                    "{3, 5, 10, 22}"
                ),
                "added_in": "v2",
                "predict": ols(window),
            }
            for window in WIDENED_OLS_WINDOWS
        },
    }


#: The forecast-class rules the packet's window grid enumerated (v1).
PACKET_WINDOW_GRID_FORECAST_RULES = (
    "deployed_v1_nearest_year",
    "ols_full_fit_window",
    "ols_last_10",
    "ols_last_5",
    "ols_last_3",
    "damped_local_trend_w5_d0.5",
    "damped_local_trend_w5_d1.0",
    "damped_local_trend_w10_d0.5",
)
#: The eleven rules the v1 artifact scored (forecast + degenerate).
V1_ELEVEN_RULES = PACKET_WINDOW_GRID_FORECAST_RULES + (
    "uniform_over_seven_categories",
    "fit_window_mean",
    "sex_pooled_nearest_year",
)


def _envelope(
    predictors: dict[str, Any],
    names: tuple[str, ...] | list[str],
    actuals: dict[tuple[str, str, int], float],
    tolerances: dict[str, float],
) -> dict[str, Any]:
    """Per cell, the smallest absolute deviation any named rule achieves
    on the gate-eligible surface; post hoc, not prospectively achievable."""
    envelope: dict[str, float] = {}
    for key in sorted(tolerances):
        category, sex, horizon = key.split("|")
        horizon_n = int(horizon[1:])
        envelope[key] = min(
            abs(
                predictors[name]["predict"](category, sex, horizon_n)
                - actuals[(category, sex, horizon_n)]
            )
            for name in names
        )
    failures = sorted(
        key for key, value in envelope.items() if value > tolerances[key]
    )
    argmax = max(envelope, key=envelope.get)
    return {
        "rules_in_envelope": sorted(names),
        "n_rules": len(names),
        "n_failed": len(failures),
        "failing_cells": failures,
        "max_abs_deviation_pp": round(max(envelope.values()), 4),
        "argmax_cell": argmax,
        "mean_abs_deviation_pp": round(_mean(list(envelope.values())), 4),
        "per_cell_pp": {
            key: round(value, 4) for key, value in envelope.items()
        },
    }


def _ols_window_sweep(
    fit_series: dict[tuple[str, str], list[float]],
    actuals: dict[tuple[str, str, int], float],
    tolerances: dict[str, float],
) -> dict[str, Any]:
    """Every OLS fit window 2..22 scored on the gate-eligible surface,
    with the knife-edge cell's deviation beside each (referee A, F1)."""
    knife = _cell_key("age66", "female", 1)
    rows = {}
    for window in OLS_WINDOW_SWEEP:
        values_by_key = {}
        for key in tolerances:
            category, sex, horizon = key.split("|")
            horizon_n = int(horizon[1:])
            years = FIT_YEARS[-window:]
            slope, intercept = _ols_slope(
                years, fit_series[(category, sex)][-window:]
            )
            predicted = intercept + slope * (FIT_YEARS[-1] + horizon_n)
            values_by_key[key] = abs(
                predicted - actuals[(category, sex, horizon_n)]
            )
        failures = sorted(
            key
            for key, value in values_by_key.items()
            if value > tolerances[key]
        )
        rows[f"ols_last_{window}"] = {
            "window_years": window,
            "fit_years": [FIT_YEARS[-window], FIT_YEARS[-1]],
            "in_packet_window_grid": window in (3, 5, 10, 22),
            "named_as_a_rule": window in (3, 5, 10, 22)
            or window in WIDENED_OLS_WINDOWS,
            "n_failed": len(failures),
            "failing_cells": failures,
            "max_abs_deviation_pp": round(max(values_by_key.values()), 4),
            "mean_abs_deviation_pp": round(
                _mean(list(values_by_key.values())), 4
            ),
            "age66_female_h1_deviation_pp": round(values_by_key[knife], 4),
            "age66_female_h1_clears": (
                values_by_key[knife] <= tolerances[knife]
            ),
        }
    clearing = sorted(
        row["window_years"]
        for row in rows.values()
        if row["age66_female_h1_clears"]
    )
    single_rule_clears_all = sorted(
        row["window_years"] for row in rows.values() if row["n_failed"] == 0
    )
    return {
        "definition": (
            "OLS on the last w fit years (w = 2..22), extrapolated to "
            "2019 + h; scored on the 34 DRAFT gate-eligible cells with "
            "the unrounded-prediction arithmetic"
        ),
        "age66_female_h1_tolerance_pp": tolerances[knife],
        "windows_clearing_age66_female_h1": clearing,
        "windows_in_packet_grid_clearing_age66_female_h1": sorted(
            w for w in clearing if w in (3, 5, 10, 22)
        ),
        "windows_with_zero_failures_on_all_34": single_rule_clears_all,
        "best_single_window_by_n_failed": min(
            rows, key=lambda name: (rows[name]["n_failed"], name)
        ),
        "rows": rows,
        "reading": (
            "'Failed by every scanned rule' (the packet's d3 premise for "
            "the age66|female|h1 knife edge) is a property of the "
            "window grid {3, 5, 10, 22}: the windows named in "
            "windows_clearing_age66_female_h1 clear the cell, some by "
            "an order of magnitude, and the class definition admits "
            "them. No single window clears all 34 cells "
            "(windows_with_zero_failures_on_all_34), so the surface is "
            "neither vacuous nor a wall for a single rule; the post-hoc "
            "per-cell envelope over the widened class has zero failures."
        ),
    }


def _published_construct_envelope(
    doc_2023: dict[str, Any],
) -> dict[str, Any]:
    """The packet's section-4 numbers (max 2.40, mean 0.52), EMITTED.

    The packet scored 'seven' forecast rules (it lists eight) on the
    48-cell PUBLISHED-share holdout with no tolerance, reporting the
    post-hoc envelope's max and mean. Both are recomputed here from the
    published construct with the same predictors, plus the mean under
    every single-rule omission, because the packet's 'seven' does not
    say which of its eight rules it drops.
    """
    fit = _fit_series(doc_2023, "published")
    actuals = _actuals(doc_2023, "published")
    published_fit_years = FIT_YEARS

    def ols(window):
        def predict(category, sex, horizon):
            years = published_fit_years[-window:]
            slope, intercept = _ols_slope(
                years, fit[(category, sex)][-window:]
            )
            return intercept + slope * (published_fit_years[-1] + horizon)

        return predict

    def damped(window, delta):
        def predict(category, sex, horizon):
            years = published_fit_years[-window:]
            slope, _ = _ols_slope(years, fit[(category, sex)][-window:])
            return fit[(category, sex)][-1] + delta * slope * horizon

        return predict

    rules = {
        "deployed_v1_nearest_year": lambda c, s, h: fit[(c, s)][-1],
        "ols_full_fit_window": ols(22),
        "ols_last_10": ols(10),
        "ols_last_5": ols(5),
        "ols_last_3": ols(3),
        "damped_local_trend_w5_d0.5": damped(5, 0.5),
        "damped_local_trend_w5_d1.0": damped(5, 1.0),
        "damped_local_trend_w10_d0.5": damped(10, 0.5),
    }
    cells = [
        (category, sex, horizon)
        for sex in SEXES
        for category in PUBLISHED_CATEGORIES
        for horizon in (1, 2, 3)
    ]

    def envelope_of(names):
        values = {
            cell: min(abs(rules[n](*cell) - actuals[cell]) for n in names)
            for cell in cells
        }
        argmax = max(values, key=values.get)
        return {
            "max_abs_deviation_pp": round(max(values.values()), 4),
            "mean_abs_deviation_pp": round(_mean(list(values.values())), 4),
            "argmax_cell": _cell_key(*argmax),
        }

    per_rule = {}
    for name, predict in rules.items():
        deviations = [abs(predict(*cell) - actuals[cell]) for cell in cells]
        per_rule[name] = {
            "max_abs_deviation_pp": round(max(deviations), 4),
            "mean_abs_deviation_pp": round(_mean(deviations), 4),
        }
    all_eight = envelope_of(list(rules))
    return {
        "surface": (
            "all 48 (category x sex x horizon) cells of the PUBLISHED "
            "eight-category construct, no tolerance (the packet's "
            "section 4 table); unrounded-prediction arithmetic"
        ),
        "n_cells": len(cells),
        "rules": per_rule,
        "envelope_over_eight_rules": all_eight,
        "envelope_mean_dropping_each_rule": {
            name: envelope_of([n for n in rules if n != name])[
                "mean_abs_deviation_pp"
            ]
            for name in rules
        },
        "envelope_max_dropping_each_rule": {
            name: envelope_of([n for n in rules if n != name])[
                "max_abs_deviation_pp"
            ]
            for name in rules
        },
        "note": (
            "The packet's section 4 says 'seven rules' over a table of "
            "eight and reports the envelope as 2.40 / 0.52. The "
            "eight-rule envelope is emitted above; the mean under every "
            "single omission is emitted so the packet's 'seven' can be "
            "matched to whichever rule it dropped. This is a "
            "published-construct scan with no tolerance: the DRAFT "
            "surface is the conditional construct's."
        ),
    }


#: The rules scored under BOTH arithmetics: holdout block name -> the
#: candidate-scan rule that is the same predictor.
RULES_SCORED_UNDER_BOTH_PATHS = {
    "nearest_year": "deployed_v1_nearest_year",
    "linear_trend": "ols_full_fit_window",
}


def _deviation_arithmetic_for_rule(
    holdout_per_cell: list[dict[str, Any]],
    predict,
    actuals: dict[tuple[str, str, int], float],
    tolerances: dict[str, float],
) -> dict[str, Any]:
    rounded = {
        _cell_key(cell["category"], cell["sex"], cell["horizon"]): abs(
            cell["deviation"]
        )
        for cell in holdout_per_cell
    }
    differing: dict[str, Any] = {}
    flips: list[str] = []
    closest_margin: float | None = None
    failures_rounded: list[str] = []
    failures_unrounded: list[str] = []
    for key, tolerance in sorted(tolerances.items()):
        category, sex, horizon = key.split("|")
        horizon_n = int(horizon[1:])
        unrounded = round(
            abs(
                predict(category, sex, horizon_n)
                - actuals[(category, sex, horizon_n)]
            ),
            4,
        )
        margin = min(abs(rounded[key] - tolerance), abs(unrounded - tolerance))
        closest_margin = (
            margin if closest_margin is None else min(closest_margin, margin)
        )
        fails_rounded = rounded[key] > tolerance
        fails_unrounded = unrounded > tolerance
        if fails_rounded:
            failures_rounded.append(key)
        if fails_unrounded:
            failures_unrounded.append(key)
        if unrounded == rounded[key]:
            continue
        if fails_rounded != fails_unrounded:
            flips.append(key)
        differing[key] = {
            "rounded_prediction_path_pp": rounded[key],
            "unrounded_prediction_path_pp": unrounded,
            "difference_pp": _round(abs(unrounded - rounded[key]), 4),
            "tolerance_pp": tolerance,
            "exceeds_tolerance_either_way": fails_rounded == fails_unrounded,
        }
    differences = [block["difference_pp"] for block in differing.values()]
    return {
        "n_cells_compared": len(tolerances),
        "n_cells_differing": len(differing),
        "max_abs_difference_pp": (
            _round(max(differences), 4) if differences else 0.0
        ),
        "n_verdict_flips": len(flips),
        "verdict_flips": flips,
        "verdict_identical_under_both_paths": not flips,
        "n_failed_rounded_path": len(failures_rounded),
        "n_failed_unrounded_path": len(failures_unrounded),
        "failing_cells_identical": failures_rounded == failures_unrounded,
        "closest_any_cell_comes_to_its_tolerance_pp": _round(
            closest_margin if closest_margin is not None else 0.0, 4
        ),
        "cells": differing,
    }


def _deviation_arithmetic(
    holdout_conditional: dict[str, dict[str, Any]],
    fit_series: dict[tuple[str, str], list[float]],
    actuals: dict[tuple[str, str, int], float],
    tolerances: dict[str, float],
) -> dict[str, Any]:
    """Reconcile the two deviation arithmetics this artifact carries.

    ``holdout_rules`` rounds each prediction to 4 decimals BEFORE
    differencing, because that is byte-for-byte what
    ``scripts/build_claiming_reference.py`` does and the published
    construct has to reproduce that committed artifact exactly.
    ``candidate_rules_on_the_draft_surface`` -- and the
    ``deployed_v1_finding`` that reads its numbers -- differences the
    unrounded prediction and rounds once at the end, a candidate scan
    being under no such constraint.

    TWO rules appear under both: the nearest-year rule (``nearest_year``
    / ``deployed_v1_nearest_year``) and the full-window OLS
    (``linear_trend`` / ``ols_full_fit_window``), so the SAME cell can
    carry two values one 4-decimal ulp apart (``age62|female|h1`` is
    3.8086 in one and 3.8087 in the other under the nearest-year rule).
    This block names every cell where they differ, per rule, so a
    referee reading the JSON is not left to reconcile that unaided, and
    records whether any gate-eligible verdict depends on the choice.
    The v1 artifact described the nearest-year rule as "the one rule
    both paths score"; that was false (referee B, D3) and the block now
    covers both.
    """
    predictors = _candidate_predictors(fit_series)
    per_rule = {
        candidate_name: {
            "holdout_rule": holdout_name,
            "candidate_rule": candidate_name,
            **_deviation_arithmetic_for_rule(
                holdout_conditional[holdout_name]["per_cell"],
                predictors[candidate_name]["predict"],
                actuals,
                tolerances,
            ),
        }
        for holdout_name, candidate_name in RULES_SCORED_UNDER_BOTH_PATHS.items()
    }
    all_flips = sorted(
        key for block in per_rule.values() for key in block["verdict_flips"]
    )
    return {
        "note": (
            "Two arithmetics, both deliberate, reported side by side. "
            "holdout_rules rounds the prediction to 4 decimals before "
            "differencing (matching scripts/build_claiming_reference.py "
            "so the published construct reproduces the committed "
            "artifact exactly); candidate_rules_on_the_draft_surface "
            "and deployed_v1_finding difference the unrounded "
            "prediction and round once. They differ by at most one "
            "4-decimal ulp."
        ),
        "rounded_prediction_path": (
            "holdout_rules.per_cell.*, holdout_rules.published.*, "
            "holdout_rules.conditional.*, reproduces_claiming_reference_v1"
        ),
        "unrounded_prediction_path": (
            "candidate_rules_on_the_draft_surface.*, deployed_v1_finding"
        ),
        "surface": (
            "the 34 DRAFT gate-eligible cells, under every rule both "
            "paths score: the deployed nearest-year rule "
            "(holdout_rules nearest_year == candidate "
            "deployed_v1_nearest_year) and the full-window OLS "
            "(holdout_rules linear_trend == candidate "
            "ols_full_fit_window)"
        ),
        "rules_scored_under_both_paths": dict(RULES_SCORED_UNDER_BOTH_PATHS),
        "n_rules_scored_under_both_paths": len(RULES_SCORED_UNDER_BOTH_PATHS),
        "n_verdict_flips_all_rules": len(all_flips),
        "verdict_flips_all_rules": all_flips,
        "verdict_identical_under_both_paths_all_rules": not all_flips,
        "max_abs_difference_pp_all_rules": max(
            block["max_abs_difference_pp"] for block in per_rule.values()
        ),
        "why_no_flip_is_possible_here": (
            "the largest disagreement between the paths is one "
            "4-decimal ulp, and under neither rule does a gate-eligible "
            "cell sit within that of its tolerance -- see each rule's "
            "closest_any_cell_comes_to_its_tolerance_pp"
        ),
        "by_rule": per_rule,
    }


def _score_candidates(
    fit_series: dict[tuple[str, str], list[float]],
    actuals: dict[tuple[str, str, int], float],
    tolerances: dict[str, float],
) -> dict[str, Any]:
    candidates = _candidate_predictors(fit_series)
    scored: dict[str, Any] = {}
    envelope: dict[str, float] = {}
    for name, spec in candidates.items():
        deviations: dict[str, float] = {}
        failures: list[str] = []
        for sex in SEXES:
            for category in CONDITIONAL_CATEGORIES:
                for horizon in (1, 2, 3):
                    key = _cell_key(category, sex, horizon)
                    if key not in tolerances:
                        continue
                    predicted = spec["predict"](category, sex, horizon)
                    deviation = abs(
                        predicted - actuals[(category, sex, horizon)]
                    )
                    deviations[key] = round(deviation, 4)
                    if deviation > tolerances[key]:
                        failures.append(key)
                    if spec["rule_class"] == "forecast":
                        envelope[key] = min(
                            envelope.get(key, deviation), deviation
                        )
        magnitudes = list(deviations.values())
        scored[name] = {
            "rule_class": spec["rule_class"],
            "description": spec["description"],
            "n_gate_eligible_cells": len(magnitudes),
            "n_failed": len(failures),
            "failing_cells": sorted(failures),
            "max_abs_deviation_pp": round(max(magnitudes), 4),
            "mean_abs_deviation_pp": round(_mean(magnitudes), 4),
        }
    forecast_names = sorted(
        name
        for name, spec in candidates.items()
        if spec["rule_class"] == "forecast"
    )
    forecast_envelope = _envelope(
        candidates, forecast_names, actuals, tolerances
    )
    packet_grid_envelope = _envelope(
        candidates, PACKET_WINDOW_GRID_FORECAST_RULES, actuals, tolerances
    )
    all_eleven_envelope = _envelope(
        candidates, V1_ELEVEN_RULES, actuals, tolerances
    )
    all_rules_envelope = _envelope(
        candidates, tuple(candidates), actuals, tolerances
    )
    return {
        "surface": (
            "the 34 DRAFT gate-eligible (category x sex x horizon) "
            "cells of the conditional construct"
        ),
        "rule_classes": {
            "forecast": (
                "rules that predict a held-out year from the fit "
                "window's own level and trend. The envelope over the "
                "named forecast rules bounds the frontier of THIS "
                "enumeration only: the class as defined admits every "
                "fit window (see ols_window_sweep) and further "
                "estimators (Holt, log-share OLS) that are not "
                "enumerated here."
            ),
            "degenerate": (
                "shapeless, level-only and sex-blind rules, included "
                "to show which dimensions the surface has bite on. "
                "They are NOT part of the frontier envelope: a "
                "degenerate rule that lands near a cell by accident "
                "would otherwise flatter it."
            ),
        },
        "n_rules": len(scored),
        "n_forecast_rules": len(forecast_names),
        "rules_added_in_v2": sorted(
            name for name, spec in candidates.items() if "added_in" in spec
        ),
        "rules": scored,
        "post_hoc_best_of_forecast_class_envelope": {
            "description": (
                "per cell, the smallest absolute deviation achieved by "
                "any FORECAST-class rule above (the widened class: the "
                "packet's window grid plus OLS windows 13-18). NOT "
                "prospectively achievable -- it picks the best rule per "
                "cell after the fact -- and reported only to bound the "
                "frontier of this enumeration."
            ),
            **forecast_envelope,
        },
        "envelope_at_the_packet_window_grid": {
            "description": (
                "the same envelope over the eight forecast rules the "
                "packet's window grid {3, 5, 10, 22} enumerated (the v1 "
                "artifact's envelope), kept so the packet's knife-edge "
                "statement -- one surviving failure, age66|female|h1 at "
                "2.3288 against 2.24 -- stays emitted and pinned beside "
                "the widened result"
            ),
            **packet_grid_envelope,
        },
        "envelope_over_the_v1_eleven_rules_including_degenerate": {
            "description": (
                "the envelope over all eleven v1 rules, degenerate "
                "included; the build's first pass took this envelope "
                "and it is recorded here because a shapeless rule "
                "landing near a cell by accident flatters the "
                "frontier, which is why the frontier envelope is "
                "forecast-class only"
            ),
            **all_eleven_envelope,
        },
        "envelope_over_all_rules_including_degenerate": {
            "description": "the envelope over every rule scored above",
            **all_rules_envelope,
        },
        "ols_window_sweep": _ols_window_sweep(fit_series, actuals, tolerances),
        "every_gate_eligible_cell_failed_by_some_rule": sorted(tolerances)
        == sorted(
            {
                key
                for block in scored.values()
                for key in block["failing_cells"]
            }
        ),
    }


# --------------------------------------------------------------------------
# The age66_before_fra transition and the open decisions
# --------------------------------------------------------------------------
def _age66_before_fra_transition(doc_2023: dict[str, Any]) -> dict[str, Any]:
    """The null-to-populated year of the raw ``age66_before_fra`` column
    per sex, read from the 2023 edition (referee A, F2; referee B,
    finding 2). The packet's d3(ii) names this composition break as a
    reason to demote ``age66|female|h1``; that cell is entitlement year
    2020 and the break begins in 2021."""
    by_sex: dict[str, Any] = {}
    first_populated: dict[str, int | None] = {}
    last_null: dict[str, int | None] = {}
    for sex in SEXES:
        values = {
            str(year): doc_2023["data"][sex][str(year)]["raw"][
                AGE66_BEFORE_FRA_COLUMN
            ]
            for year in TRANSITION_YEARS
        }
        populated = [
            year for year in TRANSITION_YEARS if values[str(year)] is not None
        ]
        nulls = [
            year for year in TRANSITION_YEARS if values[str(year)] is None
        ]
        by_sex[sex] = values
        first_populated[sex] = min(populated) if populated else None
        last_null[sex] = max(nulls) if nulls else None
    holdout_years_before_break = {
        f"h{HORIZON_OF_YEAR[year]}": {
            "entitlement_year": year,
            "age66_before_fra_populated": {
                sex: by_sex[sex][str(year)] is not None for sex in SEXES
            },
        }
        for year in HOLDOUT_YEARS
    }
    return {
        "column": AGE66_BEFORE_FRA_COLUMN,
        "source": EDITION_2023_REL,
        "years_read": [TRANSITION_YEARS[0], TRANSITION_YEARS[-1]],
        "values_by_sex_and_year": by_sex,
        "first_populated_year": first_populated,
        "last_null_year": last_null,
        "holdout_horizons": holdout_years_before_break,
        "age66_female_h1_entitlement_year": 2020,
        "break_covers_age66_female_h1": (by_sex["female"]["2020"] is not None),
        "era_map_note": (
            "the edition's own column_schema.era_map places entitlement "
            "years 2009-2020 in the FRA = 66y0m regime (no "
            "66-before-FRA column) and 2021-2022 in the FRA = 66y2m+ "
            "regime where age 66 splits three ways"
        ),
        "finding": (
            "age66_before_fra is null through entitlement year 2020 for "
            "both sexes and first populated in 2021 (female 1.0, male "
            "1.1) and 2022 (2.0 / 2.1). The h1 = 2020 cell precedes the "
            "break; the break covers h2 and h3, which the power cap "
            "already demotes for age66."
        ),
    }


def _open_decisions(
    power_cap: dict[str, Any],
    alternatives: dict[str, Any],
    candidates: dict[str, Any],
    age66_transition: dict[str, Any],
) -> dict[str, Any]:
    """Every ruling the DRAFT needs, filed with the emitted table it
    reads from. This artifact decides none of them."""
    sweep = alternatives["grammar_and_k_sweep"]["by_grammar"]

    def summary(grammar: str, k: float) -> dict[str, Any]:
        row = sweep[grammar]["by_k"][f"K_{k}"]
        return {
            "partition": (
                f"{row['n_gate_eligible']} / "
                f"{row['n_report_only_tolerance_above_t_max']}"
            ),
            "deployed_v1_n_failed": row["deployed_v1_n_failed"],
            "age66_female_h1_tolerance_pp": row["age66_female_h1"][
                "tolerance_pp"
            ],
        }

    knife = candidates["ols_window_sweep"]
    horizon = alternatives["horizon_aware_pricing"]["result"]
    return {
        "status": "OPEN -- this artifact files the decisions and decides none",
        "grammar_and_k_rev": {
            "question": (
                "which revision term the tolerance rule binds: the "
                "drafted K * sd(|revision|), gate-1's mean + K * "
                "sd(|revision|), gate_w1's analogue K * sd(signed "
                "revision), or the packet's d2 max-based term; and at "
                "which K"
            ),
            "table": "power_cap_alternatives.grammar_and_k_sweep",
            "summary_at_each_k": {
                grammar: {
                    f"K_{k}": summary(grammar, k) for k in ALTERNATIVE_K_VALUES
                }
                for grammar in sweep
            },
            "what_moves": (
                "the partition (34 / 8 under the drafted grammar at "
                "every K in the sweep; 32 / 10 under either house "
                "grammar or the max-based term at K = 2.0), the deployed "
                "rule's failure count (5-10 under the drafted grammar "
                "across K; 4 under the alternatives at K = 2.0) and the "
                "age66|female|h1 knife edge (the full-window OLS clears "
                "the cell under either house grammar at K = 2.0)"
            ),
            "draft_stays": "K * sd(|revision|), K_REV 2.0, rounding 0.05",
        },
        "horizon_pricing": {
            "question": (
                "whether h1 and h2 are priced on the terminal-year sd "
                "(the DRAFT, 'conservative') or on the settled-years sd "
                "the pair measures for rows one or more years settled"
            ),
            "table": "power_cap_alternatives.horizon_aware_pricing",
            "summary": {
                "draft": (
                    f"{power_cap['n_gate_eligible']} / "
                    f"{power_cap['n_report_only_tolerance_above_t_max']}, "
                    "deployed v1 fails 6"
                ),
                "horizon_aware": (
                    f"{horizon['n_gate_eligible']} / "
                    f"{horizon['n_report_only_tolerance_above_t_max']}, "
                    f"deployed v1 fails {horizon['deployed_v1_n_failed']}"
                ),
                "cells_promoted_under_horizon_aware": horizon[
                    "cells_promoted_relative_to_draft"
                ],
            },
            "related": "d1_missing_editions -- staging 2021 / 2022 would "
            "measure a terminal year's own settle path",
        },
        "age66_female_h1_knife_edge": {
            "question": (
                "keep the cell as teeth, demote it on a pre-registered "
                "candidate-independent reason, or re-price it"
            ),
            "options_as_corrected": {
                "i_keep_as_teeth": (
                    "gate-eligible at the drafted 2.24 pp; no single OLS "
                    "window clears all 34 cells, and the best single "
                    "windows fail exactly this cell"
                ),
                "ii_structural_demotion_as_drafted": (
                    "UNAVAILABLE AS WRITTEN: the 2021 age66_before_fra "
                    "composition break does not cover entitlement year "
                    "2020 (age66_before_fra_transition; packet "
                    "correction 7)"
                ),
                "ii_prime_a_different_pre_registered_reason_for_2020": (
                    "none is established by any source read here; the "
                    "2020 level shift's cause is undetermined "
                    "(does_not_establish)"
                ),
                "iii_re_price": (
                    "under either house grammar at K = 2.0 the cell's "
                    "tolerance is about 2.9 pp and the full-window OLS "
                    "(2.3288) clears it while the deployed rule (3.728) "
                    "does not; see grammar_and_k_rev"
                ),
            },
            "premise_check": {
                "failed_by_every_scanned_rule": (
                    "true of the packet's window grid {3, 5, 10, 22} and "
                    "false of the class as defined: OLS windows "
                    f"{knife['windows_clearing_age66_female_h1']} clear "
                    "the cell (candidate_rules_on_the_draft_surface."
                    "ols_window_sweep)"
                ),
                "structural_reason_covers_the_cell": age66_transition[
                    "break_covers_age66_female_h1"
                ],
            },
            "consequence_the_packet_did_not_state": (
                "if the cell is demoted, the packet-grid envelope goes "
                "from one failure to zero: a per-cell selector over the "
                "eight enumerated rules passes 33 / 33"
            ),
        },
        "rounding_mode": {
            "question": (
                "the arithmetic the tolerance rule is evaluated under; "
                "one cell is an exact 2-decimal tie"
            ),
            "table": "power_cap.rounding_mode and power_cap.knife_edge_class",
            "drafted": TOLERANCE_ROUNDING_MODE,
            "tie_cells": power_cap["rounding_mode"]["exact_ties"],
            "knife_edge_class_size": power_cap["knife_edge_class"]["n_cells"],
        },
        "d0_estimand_construct": {
            "question": (
                "published 8-category vs conditional 7-category "
                "construct; the DRAFT chooses the conditional"
            ),
            "what_the_artifact_carries_for_each": {
                "conditional": (
                    "the revision strata, the power cap, the candidate "
                    "scan, the deployed finding and every alternative"
                ),
                "published": (
                    "the revision strata, both holdout rules, the "
                    "claiming_reference_v1 identity and the "
                    "forecast-class envelope with no tolerance "
                    "(published_construct_forecast_envelope)"
                ),
            },
            "if_published_is_chosen": (
                "a v2 build must derive an eight-category cap, and the "
                "six disability-conversion cells re-enter as cells to be "
                "demoted by power rather than excluded by scope"
            ),
        },
        "d1_missing_2021_2022_editions": {
            "question": (
                "stage the 2021 and 2022 Supplement editions to measure "
                "a terminal year's settle path directly"
            ),
            "what_the_pair_already_shows": (
                "rows one, two and three years settled at the 2014 "
                "publication moved by 0.0 in every conditional cell "
                "(strata_by_settle_age); the count column revised below "
                "share resolution (number_thousands_column)"
            ),
            "status": "editions not staged; horizon_pricing is the priced "
            "interim alternative",
        },
    }


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build() -> dict[str, Any]:
    doc_2014 = _load(EDITION_2014_REL)
    doc_2023 = _load(EDITION_2023_REL)

    revision_cells = {
        construct: {
            "settled_years": _revision_cells(
                doc_2014, doc_2023, construct, SETTLED_YEARS
            ),
            "terminal_year": _revision_cells(
                doc_2014, doc_2023, construct, TERMINAL_YEARS
            ),
            "all_overlap": _revision_cells(
                doc_2014, doc_2023, construct, OVERLAP_YEARS
            ),
        }
        for construct in CONSTRUCTS
    }
    strata = {
        f"{construct}_{name}": _stratum(cells)
        for construct, blocks in revision_cells.items()
        for name, cells in blocks.items()
    }
    strata["average_age_column"] = _average_age_stratum(doc_2014, doc_2023)
    strata_by_settle_age = {
        construct: _settle_age_strata(doc_2014, doc_2023, construct)
        for construct in CONSTRUCTS
    }
    number_thousands = _number_thousands_stratum(doc_2014, doc_2023)

    nonzero = {
        f"{construct}_{name}": [
            {
                "cell": f"{cell['category']}|{cell['sex']}|{cell['year']}",
                "edition_2014_pp": cell["edition_2014_pp"],
                "edition_2023_pp": cell["edition_2023_pp"],
                "revision_pp": cell["revision_pp"],
            }
            for cell in cells
            if cell["moved"]
        ]
        for construct, blocks in revision_cells.items()
        for name, cells in blocks.items()
        if name != "all_overlap"
    }

    sd_full = _population_sd(
        [
            abs(cell["revision_pp"])
            for cell in revision_cells["conditional"]["terminal_year"]
        ]
    )
    sd_knob = round(sd_full, 4)

    conditional_fit = _fit_series(doc_2023, "conditional")
    conditional_actuals = _actuals(doc_2023, "conditional")
    power_cap = _power_cap(conditional_fit, sd_knob, sd_full)
    alternatives = _power_cap_alternatives(
        conditional_fit,
        conditional_actuals,
        strata["conditional_terminal_year"],
        strata["conditional_settled_years"],
        power_cap["gate_eligible_tolerances_pp"],
    )
    published_envelope = _published_construct_envelope(doc_2023)
    age66_transition = _age66_before_fra_transition(doc_2023)

    reference_values = {
        _cell_key(category, sex, horizon): _round(
            conditional_actuals[(category, sex, horizon)], 4
        )
        for sex in SEXES
        for category in CONDITIONAL_CATEGORIES
        for horizon in (1, 2, 3)
    }

    holdout = {
        construct: {
            rule: _holdout_block(doc_2023, construct, rule)
            for rule in ("nearest_year", "linear_trend")
        }
        for construct in CONSTRUCTS
    }
    cross_check = _reference_cross_check(holdout["published"])
    table_notes_identical = (
        doc_2014["provenance"]["table_notes"]
        == doc_2023["provenance"]["table_notes"]
    )
    retroactive_in_both = (
        RETROACTIVE_SENTENCE in doc_2014["provenance"]["table_notes"]
        and RETROACTIVE_SENTENCE in doc_2023["provenance"]["table_notes"]
    )

    candidates = _score_candidates(
        conditional_fit,
        conditional_actuals,
        power_cap["gate_eligible_tolerances_pp"],
    )
    deployed = candidates["rules"]["deployed_v1_nearest_year"]
    deviation_arithmetic = _deviation_arithmetic(
        holdout["conditional"],
        conditional_fit,
        conditional_actuals,
        power_cap["gate_eligible_tolerances_pp"],
    )
    deployed_predict = _candidate_predictors(conditional_fit)[
        "deployed_v1_nearest_year"
    ]["predict"]

    def _deployed_deviation(key: str) -> float:
        category, sex, horizon = key.split("|")
        horizon_n = int(horizon[1:])
        return round(
            abs(
                deployed_predict(category, sex, horizon_n)
                - conditional_actuals[(category, sex, horizon_n)]
            ),
            4,
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "run": RUN,
        "reported_not_gated": True,
        "purpose": (
            "Publication-revision floor for the SSA claim-age reference "
            "(Table 6.B5.1). Changes no gate. Measures, from committed "
            "inputs, the quantities the DRAFT gate_b2_claiming packet "
            "derives its proposed tolerances from: the cross-edition "
            "revision floor (no sampling floor exists -- the table is "
            "100 percent Master Beneficiary Record data), the derived "
            "power-cap partition, the held-out reference values, and "
            "the two holdout rules' out-of-sample scores. Proposes no "
            "threshold and ratifies none."
        ),
        "component": "claiming-age distribution (#74 component CA)",
        "gate_status": {
            "gates_yaml_block": None,
            "note": (
                "gates.yaml carries no gate_b2_claiming. Every knob and "
                "partition below is a DRAFT proposal from "
                f"{PACKET}; none has been through a referee round and "
                "none is locked."
            ),
        },
        "sources": {
            "edition_2023": _pin(EDITION_2023_REL),
            "edition_2014": _pin(EDITION_2014_REL),
            "claiming_reference_v1": _pin(CLAIMING_REFERENCE_REL),
            "edition_2023_supplement_year": doc_2023["supplement_year"],
            "edition_2014_supplement_year": doc_2014["supplement_year"],
            "table": doc_2023["table"],
            "schema_versions": [
                doc_2014["schema_version"],
                doc_2023["schema_version"],
            ],
        },
        "no_sampling_floor": {
            "mbr_100_percent_note": doc_2023["provenance"][
                "mbr_100_percent_note"
            ],
            "mbr_100_percent_note_2014_edition": doc_2014["provenance"][
                "mbr_100_percent_note"
            ],
            "table_notes": doc_2023["provenance"]["table_notes"],
            "table_notes_2014_edition": doc_2014["provenance"]["table_notes"],
            "table_notes_identical_across_editions": (
                doc_2014["provenance"]["table_notes"]
                == doc_2023["provenance"]["table_notes"]
            ),
            "retroactive_revision_sentence": RETROACTIVE_SENTENCE,
            "retroactive_revision_sentence_in_both_editions": (
                RETROACTIVE_SENTENCE in doc_2014["provenance"]["table_notes"]
                and RETROACTIVE_SENTENCE
                in doc_2023["provenance"]["table_notes"]
            ),
            "table_notes_difference_note": (
                "The two editions' full table notes are NOT identical: "
                "the 2023 edition adds a sentence about differences "
                "from Office of the Chief Actuary statistics and "
                "reorders the footnote key. The sentence this floor "
                "rests on -- retroactive entitlement causing revision "
                "with each annual update -- is verbatim in both, which "
                "is what "
                "retroactive_revision_sentence_in_both_editions "
                "records."
            ),
            "consequence": (
                "Table 6.B5.1 is a 100 percent count, not a sample, so "
                "no person-disjoint half-split null exists and the "
                "sampling-floor construction every locked gate in "
                "gates.yaml uses is inapplicable. The measurable noise "
                "is REVISION plus ROUNDING, which is what this artifact "
                "measures."
            ),
        },
        "construction": {
            "overlap_years": [OVERLAP_YEARS[0], OVERLAP_YEARS[-1]],
            "settled_years": [SETTLED_YEARS[0], SETTLED_YEARS[-1]],
            "terminal_year": TERMINAL_YEARS[0],
            "terminal_year_definition": (
                "the last entitlement year the 2014 edition publishes, "
                "and therefore the year in that edition most exposed to "
                "retroactive revision at the time it was published"
            ),
            "sexes": list(SEXES),
            "published_categories": list(PUBLISHED_CATEGORIES),
            "conditional_categories": list(CONDITIONAL_CATEGORIES),
            "conditional_construct": (
                "the disability-conversion column is dropped and the "
                "remaining seven categories renormalised to sum to 100 "
                "-- the object populace_dynamics.claiming.claim_age_pmf "
                "emits, re-aggregated to the reference's own partition"
            ),
            "metric": (
                "absolute revision in published percentage points "
                "(share on a 0-100 scale), 2023 edition minus 2014 "
                "edition, per (sex, entitlement year, category) cell"
            ),
        },
        "strata": strata,
        "strata_by_settle_age": strata_by_settle_age,
        "number_thousands_column": number_thousands,
        "nonzero_revision_cells": nonzero,
        "finding": {
            "revision_is_a_terminal_year_effect": (
                strata["published_terminal_year"]["nonzero_cells"]
                == strata["published_terminal_year"]["n_cells"]
                and strata["published_settled_years"]["nonzero_cells"] <= 1
            ),
            "statement": (
                "Every published terminal-year cell moved; across the "
                "fifteen settled years a single published cell moved, "
                "by one 0.1 pp rounding tick; the average_age column "
                "did not move at all. In the conditional construct that "
                "one published movement propagates through the "
                "renormalising denominator to all seven categories of "
                "its (sex, year) row, which is why the conditional "
                "settled stratum has more nonzero cells than the "
                "published one at the same mean magnitude."
            ),
        },
        "power_cap": power_cap,
        "power_cap_alternatives": alternatives,
        "age66_before_fra_transition": age66_transition,
        "reference_values_pp": {
            "definition": (
                "the held-out conditional share each cell scores "
                "against: 100 x category share / sum of the seven "
                "non-conversion shares, for entitlement years 2020 "
                "(h1), 2021 (h2) and 2022 (h3) of the 2023 edition"
            ),
            "gate_eligible": {
                key: value
                for key, value in reference_values.items()
                if key in power_cap["gate_eligible_tolerances_pp"]
            },
            "report_only": {
                key: value
                for key, value in reference_values.items()
                if key not in power_cap["gate_eligible_tolerances_pp"]
            },
        },
        "holdout_rules": {
            "protocol": {
                "fit_years": [FIT_YEARS[0], FIT_YEARS[-1]],
                "holdout_years": list(HOLDOUT_YEARS),
                "horizons": {
                    str(year): horizon
                    for year, horizon in HORIZON_OF_YEAR.items()
                },
                "rules": {
                    "nearest_year": (
                        "predict each held-out year with the last "
                        "in-sample year (2019); the module's documented "
                        "default fallback"
                    ),
                    "linear_trend": (
                        "per (sex, category) OLS on the fit years, "
                        "extrapolated to each held-out year"
                    ),
                },
                "arithmetic_note": (
                    "predictions are rounded to 4 decimals before the "
                    "deviation is taken, matching "
                    "scripts/build_claiming_reference.py exactly so the "
                    "published-construct numbers are comparable"
                ),
            },
            "published": {
                rule: {
                    key: value
                    for key, value in block.items()
                    if key != "per_cell"
                }
                for rule, block in holdout["published"].items()
            },
            "conditional": {
                rule: {
                    key: value
                    for key, value in block.items()
                    if key != "per_cell"
                }
                for rule, block in holdout["conditional"].items()
            },
            "per_cell": {
                construct: {
                    rule: block["per_cell"] for rule, block in blocks.items()
                }
                for construct, blocks in holdout.items()
            },
        },
        "reproduces_claiming_reference_v1": cross_check,
        "candidate_rules_on_the_draft_surface": candidates,
        "published_construct_forecast_envelope": published_envelope,
        "deployed_v1_finding": {
            "reported_not_gated": True,
            "statement": (
                "Under the DRAFT gate_b2_claiming tolerances the "
                "CURRENTLY DEPLOYED v1 nearest-year claiming rule fails "
                f"{deployed['n_failed']} of "
                f"{deployed['n_gate_eligible_cells']} gate-eligible "
                "cells. This is a measurement against a DRAFT surface, "
                "not a gate verdict: gates.yaml carries no "
                "gate_b2_claiming, no candidate has been registered, "
                "and no run has been scored."
            ),
            "n_gate_eligible_cells": deployed["n_gate_eligible_cells"],
            "n_failed": deployed["n_failed"],
            "failing_cells": deployed["failing_cells"],
            "max_abs_deviation_pp": deployed["max_abs_deviation_pp"],
            "mean_abs_deviation_pp": deployed["mean_abs_deviation_pp"],
            "per_failing_cell": {
                key: {
                    "deviation_pp": _deployed_deviation(key),
                    "tolerance_pp": power_cap["gate_eligible_tolerances_pp"][
                        key
                    ],
                    "margin_pp": round(
                        _deployed_deviation(key)
                        - power_cap["gate_eligible_tolerances_pp"][key],
                        4,
                    ),
                    "reference_pp": reference_values[key],
                    "tolerance_is_sd_knob_sensitive": key
                    in power_cap["sd_knob_rounding_check"][
                        "cells_with_a_different_tolerance"
                    ],
                    "tolerance_in_knife_edge_class": key
                    in power_cap["knife_edge_class"]["cells"],
                }
                for key in deployed["failing_cells"]
            },
            "margin_arithmetic": (
                "margin_pp = deviation_pp - tolerance_pp, both on the "
                "unrounded-prediction path (deviation_arithmetic); a "
                "positive margin is a failure by that many pp"
            ),
            "sd_knob_sensitive_failing_cells": sorted(
                key
                for key in deployed["failing_cells"]
                if key
                in power_cap["sd_knob_rounding_check"][
                    "cells_with_a_different_tolerance"
                ]
            ),
        },
        "deviation_arithmetic": deviation_arithmetic,
        "packet_reconciliation": {
            "packet": PACKET,
            "purpose": (
                "Where this build's measurement differs from the number "
                "the DRAFT packet states, the difference is recorded "
                "here rather than silently adopted."
            ),
            "differences": [
                {
                    "field": (
                        "floor.strata.conditional_settled_years."
                        "nonzero_cells"
                    ),
                    "packet_states": 1,
                    "measured": strata["conditional_settled_years"][
                        "nonzero_cells"
                    ],
                    "note": (
                        "The packet carries the PUBLISHED stratum's "
                        "nonzero count (1) on the CONDITIONAL row. One "
                        "published cell moving renormalises its whole "
                        "(sex, year) row, so all seven conditional "
                        "categories of that row move. The packet's "
                        "mean, sd and max for the same stratum "
                        "reproduce exactly, so only the count is "
                        "affected and no proposed tolerance changes."
                    ),
                },
                {
                    "field": "floor.no_sampling_floor.table_notes",
                    "packet_states": (
                        "'provenance.table_notes (both editions)' -- the "
                        "full table notes read as one text carried "
                        "identically by both editions"
                    ),
                    "measured": (
                        "table_notes_identical_across_editions: "
                        f"{table_notes_identical}; the retroactive-"
                        "revision sentence is verbatim in both editions: "
                        f"{retroactive_in_both}"
                    ),
                    "note": (
                        "The two editions' full table notes are NOT "
                        "identical: the 2023 edition adds a sentence "
                        "about differences from Office of the Chief "
                        "Actuary statistics and reorders the footnote "
                        "key. The load-bearing sentence is verbatim in "
                        "both. Recorded in no_sampling_floor (both notes "
                        "quoted, the shared sentence, and the two "
                        "booleans) and, since v2, here as well so every "
                        "packet correction is in this block."
                    ),
                },
                {
                    "field": (
                        "gate_b2_claiming.open_draft_decisions.d3 -- "
                        "option (ii), the structural demotion reason for "
                        "age66|female|h1"
                    ),
                    "packet_states": (
                        "the age66 category 'mixes before-FRA and at-FRA "
                        "claims from entitlement year 2021', visible as "
                        "age66_before_fra turning from null to "
                        "populated, offered as a candidate-independent "
                        "reason to demote age66|female|h1"
                    ),
                    "measured": (
                        "age66|female|h1 is entitlement year 2020 "
                        "(horizon 1 == 2020); age66_before_fra is null "
                        "through entitlement year "
                        f"{age66_transition['last_null_year']['female']} "
                        "for females and "
                        f"{age66_transition['last_null_year']['male']} "
                        "for males and first populated in "
                        f"{age66_transition['first_populated_year']['female']}"
                        " / "
                        f"{age66_transition['first_populated_year']['male']}"
                        " (2023 edition, raw column)"
                    ),
                    "note": (
                        "The composition break the packet names begins "
                        "in entitlement year 2021 and therefore covers "
                        "h2 and h3 (both already report-only for age66 "
                        "under the power cap), not the h1 = 2020 cell it "
                        "is offered for. The 2020 movement in age66 is "
                        "the level shift whose cause the packet's own "
                        "section 13 records as undetermined. Option (ii) "
                        "of d3 is therefore unavailable AS WRITTEN; the "
                        "cell's ruling is filed in open_decisions with "
                        "the option list corrected."
                    ),
                    "correction_number": 7,
                },
            ],
        },
        "fit_isolation": {
            "purpose": (
                "The DRAFT gate_b2_claiming block isolates the reference "
                "DOCUMENT (the 2023 Supplement) from the candidate's fit. "
                "This artifact and runs/claiming_reference_v1.json are "
                "second and third channels carrying the held-out "
                "actuals, and the DRAFT's fit_isolation clause must name "
                "them (referee A, section 2.f)."
            ),
            "channels_carrying_the_held_out_actuals": [
                {
                    "path": "runs/claiming_publication_floor_v1.json",
                    "fields": [
                        "reference_values_pp.*",
                        "holdout_rules.per_cell.*.*.actual",
                        "power_cap.gate_eligible_tolerances_pp",
                        "candidate_rules_on_the_draft_surface.*",
                    ],
                    "note": "this artifact",
                },
                {
                    "path": CLAIMING_REFERENCE_REL,
                    "fields": ["results.*.per_cell.*.actual"],
                    "pin": _pin(CLAIMING_REFERENCE_REL),
                },
                {
                    "path": EDITION_2023_REL,
                    "fields": ["data.*.2020|2021|2022"],
                    "pin": _pin(EDITION_2023_REL),
                    "note": (
                        "the reference document itself, already named by "
                        "the DRAFT's fit_isolation"
                    ),
                },
            ],
            "consequence": (
                "Physical isolation is impossible for public data and "
                "for an artifact that publishes every held-out actual and "
                "every tolerance. The defence is procedural: the rule "
                "class and fit window are registered on issue #42 with a "
                "justification independent of this artifact, before any "
                "scoring, one shot; a rule class chosen because it lands "
                "under a published tolerance on a named cell is what "
                "no_self_rescue and registration-before-scoring exist to "
                "exclude. The candidate scan above is post hoc and says "
                "so; the moment one of its rules is registered as a "
                "candidate, its scores here are prior knowledge."
            ),
            "required_draft_clause": (
                "gate_b2_claiming.fit_isolation must name "
                "runs/claiming_publication_floor_v1.json and "
                "runs/claiming_reference_v1.json as channels carrying "
                "the held-out actuals, and the registration must fix the "
                "rule class and fit window before scoring."
            ),
        },
        "open_decisions": _open_decisions(
            power_cap, alternatives, candidates, age66_transition
        ),
        "does_not_establish": [
            "any threshold: no tolerance here is ratified and gates.yaml "
            "carries no gate_b2_claiming",
            "that the DRAFT tolerances are insensitive to the sd knob's "
            "4-decimal rounding: see power_cap.sd_knob_rounding_check, "
            "which names every cell whose 2-decimal tolerance moves "
            "when the full-precision sd is used",
            "the revision settle path: the 2021 and 2022 Supplement "
            "editions are not staged, so the terminal-year stratum is "
            "measured on ONE edition pair and one year (14 conditional "
            "cells)",
            "that the scanned rule class is complete: the candidate "
            "rules above are a scan, not a proof that no admissible "
            "rule does better",
            "any cause for the 2020 level shift in the reference: not "
            "established by any source read here",
            "which revision grammar, K_REV, rounding mode or horizon "
            "pricing the gate should bind: power_cap_alternatives emits "
            "every variant the referees priced and open_decisions files "
            "each ruling; the DRAFT gated_surface is the drafted "
            "grammar's until then",
            "that the widened forecast class is complete: OLS windows "
            "13-18 are named and every window 2-22 is swept, but Holt, "
            "log-share OLS and cross-sex borrowing are not enumerated",
            "that the number_thousands revisions in settled years are "
            "immaterial for any construct other than the rounded share "
            "table (they sit below the share rounding; the count column "
            "is measured, not priced)",
        ],
        "build": {
            "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "built_by": "scripts/build_claiming_publication_floor.py",
        },
    }


def main() -> None:
    artifact = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    cap = artifact["power_cap"]
    deployed = artifact["deployed_v1_finding"]
    terminal = artifact["strata"]["conditional_terminal_year"]
    print(
        f"wrote {OUT_PATH}\n"
        f"  conditional terminal-year revision: mean "
        f"{terminal['mean_pp']} pp, sd {terminal['sd_pp']} pp, max "
        f"{terminal['max_pp']} pp over {terminal['n_cells']} cells\n"
        f"  power cap: {cap['n_gate_eligible']} gate-eligible, "
        f"{cap['n_report_only_tolerance_above_t_max']} report-only\n"
        f"  claiming_reference_v1 reproduced: "
        f"{artifact['reproduces_claiming_reference_v1']['all_match']}\n"
        f"  deployed v1 nearest-year: {deployed['n_failed']} of "
        f"{deployed['n_gate_eligible_cells']} gate-eligible cells fail "
        "(REPORTED, NOT GATED)"
    )


if __name__ == "__main__":
    main()
