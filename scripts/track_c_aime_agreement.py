"""Track C step 1: per-person AIME agreement, Axiom engine vs the oracle.

For every person of the real Track A 2011-wave PSID cohort whose AIME the
transitional Python oracle computes in Track A, this script records

* the oracle's AIME over the person's Track A career, indexed to the year
  of attaining 60, under the computation-year convention chosen with
  ``--oracle-computation-years`` (every output names it):

  - ``statutory`` (the default): ``ss.statutory_aime.oracle_aime`` with
    ``ComputationYears.STATUTORY``, the 42 USC 415(b)(2) count (elapsed
    years less 5, at least 2), which is also the default of
    ``scenario_benefits.eligibility_pia_for_clock``;
  - ``legacy_fixed_35``: ``ComputationYears.LEGACY_FIXED_35``, the
    unchanged ``ss.benefits.aime`` (always 35 years).  This is the call
    ``eligibility_pia_for_clock`` makes for the age-62 clock under Track
    A's own convention (``cola_track_a.benefits.
    TRACK_A_COMPUTATION_YEARS``); it was the oracle of the 2026-09-23
    report (``track-c-aime-agreement-20260923``).

  The two can differ only for people born before 1929, who have fewer
  than 35 statutory computation years.  Track A's own AIME (the legacy
  convention) is recorded beside the chosen oracle's for every person.
  Both use Track A's statutory parameters (the committed capture before
  1975, the TR2008 intermediate AWI from 1975:
  ``cola_track_a.runner.tr2008_ssa_parameters``);
* the AIME the actual Axiom rules engine returns for the same person,
  through :mod:`populace_dynamics.axiom_benefit_bridge` (the pinned engine
  binary and compiled 415(b) candidate that reproduced SSA's published
  2026 Case A), with every declaration the bridge needs made explicitly
  and recorded;
* the difference, an attribution check, and every refusal with its
  reasons.

The Axiom RuleSpec candidates are UNACCEPTED encoder candidates; agreement
or disagreement is diagnostic only.  This is not the COLA statistic: the
script computes no benefit path, no reform and no age-profile value.

Transport conventions (every one recorded in the output):

* **Creditable earnings.**  Track A's oracle treats each career amount
  (PSID head/spouse labor income, 1968 through the opening year) as
  covered earnings limited to the contribution and benefit base
  (``ss.benefits.creditable_history``).  The same limited amounts are
  declared USD creditable earnings for the 415(b) candidate, whose input
  is creditable earnings.  The bridge then checks every nonzero amount
  against the same base (a check, never a cap).
* **Binary64 amounts** are sent in the bridge's
  ``shortest_round_trip_binary64`` encoding; every row records its bits.
* **Zero years outside the PSID panel.**  The oracle counts any year
  absent from a career as zero.  The bridge never pads, so the elapsed-
  window years before 1968 and after the opening year are sent as
  explicit zero rows labeled synthetic.  Career years the career law
  zero-filled (provenance ``unknown``) and gap-imputed years are also
  labeled synthetic; only observed years are not.
* **Indexing year**: the year of attaining 60 (birth year + 60), as the
  oracle and the bridge both fix it.
* **Entitlement year.**  The oracle's AIME ranks every career year through
  the opening year whatever the entitlement.  The candidate counts only
  computation base years before the entitlement year.  The primary pass
  therefore sends ``max(birth year + 62, opening year + 1)``, the one
  choice that gives the engine exactly the years the oracle ranks (plus
  zeros).  A diagnostic pass sends the entitlement year Track A records
  for each opening-stock retired worker (the A3 receipt start, clamped to
  the age-62 clock), which drops career years from entitlement on; it is
  compared with the oracle on the same truncated years, and the effect of
  the truncation on the oracle is reported separately.

The attribution check (verification only, not a third model) reruns the
oracle's own creditable and indexed history with the candidate's number
of benefit computation years instead of the oracle's.  Under the legacy
oracle (35 years) it can explain disagreements for people born before
1929; the statutory oracle already uses the candidate's count, so under
it no disagreement is attributed to the count.

Binding to the registered Track A run.  The cohort and parameters must be
those of ``runs/replication_urban2010_cola_v1.json``: every cohort
diagnostic the artifact records must be present with an equal value, and
its source provenance and parameter revision must be equal.  A
diagnostic the artifact does not record must be a reviewed one listed in
``KNOWN_ADDITIVE_DIAGNOSTICS`` (with the commit that added it); it is
recorded in the output and must reconcile with the recorded diagnostics it
breaks down (sum to the recorded total, fit within the recorded
per-category counts).  Any other new diagnostic refuses the run.

Usage::

    python scripts/track_c_aime_agreement.py \\
        --output-dir <evidence dir> [--workers 4] [--allow-dirty] \\
        [--oracle-computation-years statutory|legacy_fixed_35]
    python scripts/track_c_aime_agreement.py --render-only <evidence dir>

Writes ``result.json`` and ``RESULTS.md`` (and ``executions/``) there.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import threading
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics import axiom_benefit_bridge as bridge  # noqa: E402
from populace_dynamics import scenario_benefits as sb  # noqa: E402
from populace_dynamics.cola_track_a.benefits import (  # noqa: E402
    FIRST_ORACLE_ELIGIBILITY_YEAR,
    TRACK_A_COMPUTATION_YEARS,
)
from populace_dynamics.ss import benefits, statutory_aime  # noqa: E402
from populace_dynamics.ss.params import SSAParameters  # noqa: E402
from populace_dynamics.ss.statutory_aime import (  # noqa: E402
    ComputationYears,
)

#: v2 (2026-09-24, commit 71c94743): the oracle's computation years are a
#: recorded choice (``oracle``), ``oracle_aime`` is the chosen oracle's AIME
#: and ``track_a_oracle_aime`` always Track A's, and the Track A artifact
#: binding records the diagnostics compared and the additive ones.
#: v3 (2026-09-24): the binding admits only the additive diagnostics in
#: ``KNOWN_ADDITIVE_DIAGNOSTICS`` and records ``added_by``, the category
#: check and ``unknown_additive_diagnostic_keys``.
SCHEMA_VERSION = "populace_dynamics.track_c.aime_agreement.v3"
#: The first year of the PSID family earnings panel (career law).
PANEL_FIRST_YEAR = 1968
#: Track A's fixed benefit computation years (``ss.benefits.aime``).
LEGACY_COMPUTATION_YEARS = statutory_aime.LEGACY_FIXED_COMPUTATION_YEARS
#: ``--oracle-computation-years`` choices.
ORACLE_CHOICES: Mapping[str, ComputationYears] = {
    "statutory": ComputationYears.STATUTORY,
    "legacy_fixed_35": ComputationYears.LEGACY_FIXED_35,
}
#: The default oracle: the statutory 42 USC 415(b)(2) count.
DEFAULT_ORACLE = "statutory"
#: What each oracle is, in the words every output uses.
ORACLE_NAMES: Mapping[ComputationYears, str] = {
    ComputationYears.STATUTORY: (
        "statutory computation years (42 USC 415(b)(2), "
        "ss.statutory_aime), not Track A's fixed 35"
    ),
    ComputationYears.LEGACY_FIXED_35: (
        "Track A's legacy fixed 35 computation years (ss.benefits.aime)"
    ),
}
_RETIREMENT_AGE = 62
_INDEXING_AGE = 60
_MONTHS = 12

PASS_PRIMARY = "primary"
PASS_DIAGNOSTIC = "diagnostic_track_a_opening_entitlement"
PASS_STRICT = "strict_no_synthetic_rows"

ROUTE_OPENING_RETIRED = "opening_retired_worker"
ROUTE_PROJECTED = "projected_claimant_candidate"
ROUTE_OPENING_DI = "opening_disabled_worker"
ROUTE_OPENING_AUX = "opening_auxiliary"
ROUTES: Mapping[str, str] = {
    ROUTE_OPENING_RETIRED: (
        "opening-stock retired worker: the own benefit stays the observed "
        "2010 amount; the oracle computes this person's retirement PIA "
        "when the person is the worker behind a spouse's excess or a "
        "widow(er)'s benefit (cola_track_a.benefits worker_record and "
        "deceased_record)"
    ),
    ROUTE_PROJECTED: (
        "opening non-recipient (status none or unobserved): the oracle "
        "computes the retirement PIA at a simulated claim by the 2030 "
        "reference year, or for a death at 62 or older behind a "
        "widow(er)'s benefit"
    ),
    ROUTE_OPENING_DI: (
        "opening disabled worker: Track A's own level is the disclosed DI "
        "approximation (not compared); the oracle retirement PIA is "
        "reached only after a simulated DI recovery"
    ),
    ROUTE_OPENING_AUX: (
        "opening survivor, spouse, other or unclassified recipient: "
        "worker_record returns no own worker record; the oracle retirement "
        "PIA is reached only for a death at 62 or older behind a "
        "widow(er)'s benefit (deceased_record)"
    ),
}
PRIMARY_ROUTES = (ROUTE_OPENING_RETIRED, ROUTE_PROJECTED)
ROW_LABELS: tuple[tuple[str, str], ...] = (
    ("career_observed", "career year, observed in PSID"),
    (
        "career_gap_imputed",
        "career year, imputed by the biennial gap law (synthetic)",
    ),
    (
        "career_unknown",
        "career year, zero-filled by the career law (synthetic)",
    ),
    ("synthetic_zero_pre_panel", "zero row before 1968 (synthetic)"),
    (
        "synthetic_zero_post_cutoff",
        "zero row after the opening year (synthetic)",
    ),
    ("sent", "all rows sent"),
)
_AUX_STATUSES = ("survivor", "spouse", "other", "unclassified")

ATTR_EXACT = "exact_match"
ATTR_COUNT = "explained_by_computation_year_count"
ATTR_UNEXPLAINED = "unexplained"

COVERED_EARNINGS_DECLARATION = (
    "Track A's oracle treats each PSID career amount (head/spouse labor "
    "income from the family files, 1968 through the opening year, under "
    "the career law of estimates.career.build_career) as covered earnings "
    "limited to the contribution and benefit base "
    "(ss.benefits.creditable_history). The same limited amounts are "
    "declared USD creditable earnings for the Axiom 415(b) candidate. PSID "
    "observes no coverage status: this is an assumption both sides share, "
    "not a finding."
)
PRE_PANEL_LABEL = (
    "elapsed-window years before the 1968 start of the PSID earnings "
    "panel, sent as zero because the oracle counts every year absent from "
    "the career as zero"
)
POST_CUTOFF_LABEL = (
    "elapsed-window years after the opening-year information cutoff, "
    "sent as zero because Track A draws no earnings after the opening "
    "year and the oracle counts them as zero"
)


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------
EXCLUDED_BEFORE_1979 = "eligibility_before_1979"
EXCLUDED_AFTER_REFERENCE = "eligibility_after_reference_year"
EXCLUSIONS: Mapping[str, str] = {
    EXCLUDED_BEFORE_1979: (
        "the year of attaining 62 precedes 1979: Track A's oracle level is "
        "unavailable (_Calculator._level) and the bridge refuses (42 USC "
        "415(a)(3)(A))"
    ),
    EXCLUDED_AFTER_REFERENCE: (
        "the year of attaining 62 is after the 2030 reference year: Track A "
        "computes no retirement level for this person"
    ),
}


@dataclass(frozen=True)
class Selection:
    """One cohort member: the Track A route, or why none applies."""

    person_id: int
    birth_year: int
    opening_status: str
    route: str | None
    exclusion: str | None = None

    @property
    def selected(self) -> bool:
        return self.route is not None


def route_for_status(opening_status: str) -> str:
    """The Track A route to an oracle retirement AIME for a status."""

    if opening_status == "retired_worker":
        return ROUTE_OPENING_RETIRED
    if opening_status == "disabled_worker":
        return ROUTE_OPENING_DI
    if opening_status in _AUX_STATUSES:
        return ROUTE_OPENING_AUX
    if opening_status in ("none", "unobserved"):
        return ROUTE_PROJECTED
    raise ValueError(f"unknown opening status {opening_status!r}")


def select_persons(
    persons: Iterable[tuple[int, int, str]],
    *,
    reference_year: int,
    first_eligibility_year: int = FIRST_ORACLE_ELIGIBILITY_YEAR,
) -> tuple[Selection, ...]:
    """Every member whose oracle retirement AIME Track A can compute.

    ``persons`` yields ``(person_id, birth_year, opening_status)``.  Track A
    computes the retirement level at the year of attaining 62, refuses
    eligibility before 1979 (``_Calculator._level``) and projects to the
    reference year, so the eligibility year must lie in
    ``[first_eligibility_year, reference_year]``.
    """

    out = []
    for person_id, birth_year, status in persons:
        person_id, birth_year = int(person_id), int(birth_year)
        status = str(status)
        eligibility = birth_year + _RETIREMENT_AGE
        if eligibility < first_eligibility_year:
            out.append(
                Selection(
                    person_id, birth_year, status, None, EXCLUDED_BEFORE_1979
                )
            )
        elif eligibility > reference_year:
            out.append(
                Selection(
                    person_id,
                    birth_year,
                    status,
                    None,
                    EXCLUDED_AFTER_REFERENCE,
                )
            )
        else:
            out.append(
                Selection(
                    person_id, birth_year, status, route_for_status(status)
                )
            )
    return tuple(sorted(out, key=lambda s: s.person_id))


# --------------------------------------------------------------------------
# Conventions
# --------------------------------------------------------------------------
def primary_entitlement_year(birth_year: int, cutoff_year: int) -> int:
    """The entitlement year that sends the engine the oracle's years."""

    return max(int(birth_year) + _RETIREMENT_AGE, int(cutoff_year) + 1)


def candidate_computation_years(birth_year: int) -> int:
    """Benefit computation years under the 415(b) candidate's formulas.

    ``elapsed_years_for_old_age_benefit_computation`` is ``min(sentinel,
    yr62) - max(1950, yr21) - 1`` (no disability; the bridge's sentinel is
    the entitlement year, never before yr62), and
    ``old_age_benefit_computation_year_count`` is ``max(2, elapsed - 5)``.
    Recorded for attribution only; the engine computes its own count.
    """

    year62 = int(birth_year) + _RETIREMENT_AGE
    year21 = int(birth_year) + 21
    elapsed = max(0, year62 - max(1950, year21) - 1)
    return max(2, elapsed - 5)


def oracle_convention(choice: str | ComputationYears) -> ComputationYears:
    """The convention of an ``--oracle-computation-years`` choice."""

    if isinstance(choice, ComputationYears):
        return choice
    try:
        return ORACLE_CHOICES[str(choice)]
    except KeyError:
        raise ValueError(
            f"unknown oracle computation years {choice!r}; choose one of "
            f"{', '.join(ORACLE_CHOICES)}"
        ) from None


def oracle_choice(convention: ComputationYears) -> str:
    """The ``--oracle-computation-years`` value of a convention."""

    for choice, value in ORACLE_CHOICES.items():
        if value is ComputationYears(convention):
            return choice
    raise ValueError(f"no oracle choice for {convention!r}")


def header_for(convention: ComputationYears) -> str:
    """The result header, naming the oracle compared against."""

    return (
        "Track C step 1: per-person AIME agreement between the actual Axiom "
        "rules engine and the transitional Python oracle on the real Track "
        "A PSID cohort. Oracle: "
        + ORACLE_NAMES[ComputationYears(convention)]
        + ". The Axiom RuleSpec candidates are UNACCEPTED. This is not the "
        "COLA statistic: no benefit path, reform or age-profile value is "
        "computed."
    )


def labels_for(convention: ComputationYears) -> tuple[str, ...]:
    """The result labels, the oracle's among them."""

    return (
        "PSID-seeded closed cohort",
        "Axiom RuleSpec candidates unaccepted (diagnostic only)",
        "Python oracle: transitional, not Axiom",
        "oracle: " + ORACLE_NAMES[ComputationYears(convention)],
        "not the COLA statistic",
    )


def oracle_document(convention: ComputationYears) -> dict[str, Any]:
    """What ``result.json`` records about the oracle compared against."""

    convention = ComputationYears(convention)
    return {
        "choice": oracle_choice(convention),
        "computation_years": convention.value,
        "name": ORACLE_NAMES[convention],
        "call": (
            "ss.statutory_aime.oracle_aime(career, birth_year, params, "
            f"computation_years=ComputationYears.{convention.name})"
        ),
        "track_a_computation_years": TRACK_A_COMPUTATION_YEARS.value,
        "is_track_a_convention": convention is TRACK_A_COMPUTATION_YEARS,
        "choices": {
            choice: value.value for choice, value in ORACLE_CHOICES.items()
        },
        "default_choice": DEFAULT_ORACLE,
    }


def oracle_aime(
    career: Mapping[int, float],
    birth_year: int,
    params: SSAParameters,
    *,
    convention: ComputationYears,
) -> int:
    """The oracle's age-62 AIME under a named convention.

    ``ss.statutory_aime.oracle_aime``: ``STATUTORY`` is the 42 USC
    415(b)(2) count, ``LEGACY_FIXED_35`` is ``ss.benefits.aime`` (always
    35 years), Track A's.
    """

    return statutory_aime.oracle_aime(
        dict(career),
        int(birth_year),
        params,
        computation_years=ComputationYears(convention),
    )


def oracle_computation_year_count(
    birth_year: int, convention: ComputationYears
) -> int:
    """How many computation years the oracle divides by for a person."""

    if ComputationYears(convention) is ComputationYears.LEGACY_FIXED_35:
        return LEGACY_COMPUTATION_YEARS
    return statutory_aime.benefit_computation_years(int(birth_year))


def require_track_a_convention(
    track_a_convention: ComputationYears = TRACK_A_COMPUTATION_YEARS,
) -> None:
    """Refuse to run unless Track A still uses the legacy fixed 35.

    The report text names Track A's AIME as the fixed-35 one under either
    oracle choice, and the ``legacy_fixed_35`` choice is described as
    Track A's own.
    """

    convention = ComputationYears(track_a_convention)
    if convention is not ComputationYears.LEGACY_FIXED_35:
        raise SystemExit(
            f"Track A's oracle computation years are {convention.value}; "
            "this script describes Track A's AIME as "
            f"{ComputationYears.LEGACY_FIXED_35.value} "
            f"({LEGACY_COMPUTATION_YEARS} years) and must be updated first"
        )


def check_oracle_pia(
    inputs: Iterable[PersonInput],
    params: SSAParameters,
    convention: ComputationYears,
) -> dict[str, Any]:
    """Fail unless the oracle PIAs rest on the AIMEs this script records.

    For every person and for both the chosen convention and Track A's
    (``TRACK_A_COMPUTATION_YEARS``, as Track A's assembly passes it),
    ``eligibility_pia_for_clock`` with that ``computation_years`` must
    equal ``benefits.pia`` of :func:`oracle_aime` under it.  Under the
    legacy choice the two conventions are one.  The function's default is
    the statutory count, so a call that dropped ``computation_years``
    would fail the legacy check for people born before 1929.
    """

    conventions = tuple(
        dict.fromkeys(
            (ComputationYears(convention), TRACK_A_COMPUTATION_YEARS)
        )
    )
    persons = 0
    for person in inputs:
        persons += 1
        birth = person.selection.birth_year
        for checked in conventions:
            pia = sb.eligibility_pia_for_clock(
                sb.WorkerClock.at_age_62(birth),
                history=person.career,
                birth_year=birth,
                params=params,
                computation_years=checked,
            )
            if pia != benefits.pia(
                oracle_aime(person.career, birth, params, convention=checked),
                birth + _RETIREMENT_AGE,
                params,
            ):
                raise ValueError(
                    f"{person.selection.person_id}: PIA mismatch "
                    f"({checked.value})"
                )
    return {
        "persons": persons,
        "conventions_checked": [checked.value for checked in conventions],
        "check": (
            "scenario_benefits.eligibility_pia_for_clock(age-62 clock, "
            "computation_years=c) == ss.benefits.pia(oracle AIME under c, "
            "year of attaining 62) for every person and convention c"
        ),
    }


def oracle_arithmetic_with_count(
    career: Mapping[int, float],
    birth_year: int,
    params: SSAParameters,
    computation_years: int,
) -> int:
    """The oracle's own arithmetic with another number of computation years.

    Verification only: ``ss.benefits`` creditable and indexed histories,
    the highest ``computation_years`` values (zero-padded), divided by
    ``12 * computation_years`` and floored.  With 35 it is the legacy
    oracle, with the statutory count the statutory one.
    """

    creditable = benefits.creditable_history(dict(career), params)
    indexed = benefits.indexed_history(creditable, int(birth_year), params)
    top = sorted(indexed.values(), reverse=True)[:computation_years]
    top += [0.0] * (computation_years - len(top))
    return math.floor(sum(top) / (computation_years * _MONTHS))


def _float_text(value: float) -> str:
    """Shortest decimal text that round-trips ``value``, plain notation."""

    text = repr(float(value))
    if "e" in text or "E" in text or float(text) != value:
        raise ValueError(f"{value!r} has no plain round-trip decimal text")
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _mapping_sha256(values: Mapping[Any, Any]) -> str:
    encoded = json.dumps(
        {str(k): v for k, v in values.items()},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def track_a_wage_index(
    params: SSAParameters, *, first_year: int = 1951
) -> bridge.AnnualSeries:
    """The oracle's AWI (Track A: TR2008 from 1975) as exact decimals."""

    values = {
        int(year): _float_text(value)
        for year, value in sorted(params.nawi.items())
        if int(year) >= first_year
    }
    return bridge.AnnualSeries.from_mapping(
        "Track A oracle AWI "
        f"({params.pe_us_revision}): the committed capture before 1975, "
        "TR2008 intermediate from 1975 (TR2008 estimates from 2007)",
        values,
        source_sha256=_mapping_sha256(values),
    )


def track_a_contribution_base(
    params: SSAParameters, first_year: int, last_year: int
) -> bridge.AnnualSeries:
    """The oracle's contribution and benefit base, year by year."""

    values = {
        year: _float_text(params.wage_base_for(year))
        for year in range(first_year, last_year + 1)
    }
    return bridge.AnnualSeries.from_mapping(
        f"Track A oracle contribution and benefit base "
        f"({params.pe_us_revision})",
        values,
        source_sha256=_mapping_sha256(values),
    )


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class TransportPlan:
    """The rows sent for one person, with what each class of row is."""

    rows: tuple[bridge.EarningsRow, ...]
    counts: Mapping[str, int]
    excluded_career_years: tuple[int, ...]


def transport_rows(
    career: Mapping[int, float],
    provenance: Mapping[int, str],
    *,
    birth_year: int,
    entitlement_year: int,
    cutoff_year: int,
    params: SSAParameters,
    synthetic_zero_years: bool = True,
    panel_first_year: int = PANEL_FIRST_YEAR,
) -> TransportPlan:
    """Rows for the elapsed window and every career year before entitlement.

    Career amounts are limited to the base by the oracle's own
    ``creditable_history`` and sent in the shortest round-trip binary64
    encoding.  With ``synthetic_zero_years`` the window years before the
    panel and after the cutoff are explicit zero rows labeled synthetic;
    without it they are left out (the bridge then refuses).
    """

    birth_year, entitlement_year = int(birth_year), int(entitlement_year)
    years = sorted(int(y) for y in career)
    if years:
        if years[0] < panel_first_year or years[-1] > cutoff_year:
            raise ValueError(
                f"career years {years[0]}-{years[-1]} fall outside "
                f"{panel_first_year}-{cutoff_year}"
            )
        if years != list(range(years[0], years[-1] + 1)):
            raise ValueError("career years must be contiguous")
    creditable = benefits.creditable_history(dict(career), params)
    counts: Counter = Counter()
    rows: list[bridge.EarningsRow] = []
    excluded = tuple(y for y in years if y >= entitlement_year)
    encoding = bridge.BINARY64_SHORTEST_ROUND_TRIP
    for year in years:
        if year >= entitlement_year:
            continue
        value = float(creditable[year])
        kind = str(provenance.get(year, "missing_provenance"))
        amount_hex = value.hex()
        amount = bridge.binary64_decimal(amount_hex, encoding)
        rows.append(
            bridge.EarningsRow(
                year,
                amount,
                f"psid_career:{kind}",
                kind != "observed",
                amount_hex,
                encoding,
            )
        )
        counts[f"career_{kind}"] += 1
        if float(career[year]) > value:
            counts["limited_to_base"] += 1
        if amount != Decimal(value):
            counts["shortest_decimal_differs_from_binary"] += 1
    window_start = max(bridge.FIRST_COMPUTATION_BASE_YEAR, birth_year + 22)
    first_career = years[0] if years else entitlement_year
    pre = range(window_start, min(first_career, panel_first_year))
    post = range(cutoff_year + 1, entitlement_year)
    if synthetic_zero_years:
        for label, span, key in (
            (PRE_PANEL_LABEL, pre, "synthetic_zero_pre_panel"),
            (POST_CUTOFF_LABEL, post, "synthetic_zero_post_cutoff"),
        ):
            if len(span):
                supplied = bridge.CallerSuppliedHistory.from_mapping(
                    label, {year: 0 for year in span}, synthetic=True
                )
                rows.extend(supplied.rows())
                counts[key] += len(span)
    rows.sort(key=lambda row: row.year)
    counts["sent"] = len(rows)
    counts["synthetic"] = sum(row.synthetic for row in rows)
    return TransportPlan(tuple(rows), dict(sorted(counts.items())), excluded)


# --------------------------------------------------------------------------
# One person, one pass
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PersonInput:
    """What the comparison reads for one selected person."""

    selection: Selection
    career: Mapping[int, float]
    provenance: Mapping[int, str]
    opening_entitlement_year: int | None = None


@dataclass(frozen=True)
class PassContext:
    """Shared inputs of a pass."""

    name: str
    params: SSAParameters
    wage_index: bridge.AnnualSeries
    contribution_base: bridge.AnnualSeries
    binding: bridge.AxiomEngineBinding | None
    cutoff_year: int
    anchor_wave: int
    oracle_convention: ComputationYears
    runner: bridge.Runner | None = None
    pia_check_params: SSAParameters | None = None


def _entity_id(context: PassContext, person_id: int) -> str:
    return f"psid{context.anchor_wave}-person-{person_id}"


def _entitlement_for_pass(
    context: PassContext, person: PersonInput
) -> int | None:
    birth = person.selection.birth_year
    if context.name == PASS_DIAGNOSTIC:
        return person.opening_entitlement_year
    return primary_entitlement_year(birth, context.cutoff_year)


def _decimal_str(value: Decimal) -> str:
    """Plain decimal text without trailing zeros or exponent notation."""

    value = Decimal(value)
    if value == 0:
        return "0"
    if value == value.to_integral_value():
        return format(value.quantize(Decimal(1)), "f")
    return format(value.normalize(), "f")


def compare_person(
    person: PersonInput, context: PassContext
) -> tuple[dict[str, Any], bridge.AxiomBenefitResult | None]:
    """One person's record for one pass (engine executed unless strict)."""

    selection = person.selection
    birth = selection.birth_year
    entitlement = _entitlement_for_pass(context, person)
    if entitlement is None:
        raise ValueError(f"{selection.person_id}: no entitlement year")
    convention = ComputationYears(context.oracle_convention)
    full_oracle = oracle_aime(
        person.career, birth, context.params, convention=convention
    )
    oracle_count = oracle_computation_year_count(birth, convention)
    record: dict[str, Any] = {
        "person_id": selection.person_id,
        "birth_year": birth,
        "opening_status": selection.opening_status,
        "route": selection.route,
        "eligibility_year": birth + _RETIREMENT_AGE,
        "indexing_year": birth + _INDEXING_AGE,
        "entitlement_year_sent": entitlement,
        "oracle_computation_years": oracle_count,
        "oracle_aime": full_oracle,
        "track_a_oracle_aime": oracle_aime(
            person.career,
            birth,
            context.params,
            convention=TRACK_A_COMPUTATION_YEARS,
        ),
    }
    compared_career = {
        year: value
        for year, value in person.career.items()
        if int(year) < entitlement
    }
    comparison_oracle = full_oracle
    if len(compared_career) != len(person.career):
        comparison_oracle = oracle_aime(
            compared_career, birth, context.params, convention=convention
        )
        record["oracle_aime_on_sent_years"] = comparison_oracle
        record["truncation_effect_on_oracle"] = comparison_oracle - (
            full_oracle
        )
    count = candidate_computation_years(birth)
    record["candidate_computation_years"] = count
    plan = transport_rows(
        person.career,
        person.provenance,
        birth_year=birth,
        entitlement_year=entitlement,
        cutoff_year=context.cutoff_year,
        params=context.params,
        synthetic_zero_years=context.name != PASS_STRICT,
    )
    record["rows"] = dict(plan.counts)
    if plan.excluded_career_years:
        record["career_years_not_sent"] = bridge.year_ranges(
            plan.excluded_career_years
        )
        record["career_years_not_sent_nonzero"] = sum(
            float(person.career[y]) > 0 for y in plan.excluded_career_years
        )
    try:
        determinations = (
            bridge.OrdinaryRetirementDeterminations.from_birth_year(
                birth, entitlement
            )
        )
        prepared = bridge.prepare_request(
            _entity_id(context, selection.person_id),
            plan.rows,
            determinations,
            context.wage_index,
            contribution_base=context.contribution_base,
            notes=(
                f"pass {context.name}; route {selection.route}",
                "covered-earnings declaration: "
                + COVERED_EARNINGS_DECLARATION,
            ),
        )
    except bridge.BenefitBridgeRefusal as refusal:
        record.update(
            status="refused",
            reasons=list(refusal.reasons),
            gaps={
                name: bridge.year_ranges(years)
                for name, years in refusal.gaps.items()
            },
            refusal_classes=refusal_classes(
                refusal, context.cutoff_year, PANEL_FIRST_YEAR
            ),
        )
        return record, None
    record["request_sha256"] = prepared.request_sha256
    record["artifact_role"] = prepared.artifact_role
    if context.name == PASS_STRICT:
        record["status"] = "accepted_not_executed"
        return record, None
    if context.binding is None:
        raise ValueError("an engine binding is required to execute")
    try:
        result = bridge.execute_request(
            prepared, context.binding, runner=context.runner
        )
    except bridge.AxiomExecutionError as error:
        record.update(status="failed", reasons=[str(error)])
        return record, None
    difference = result.aime - Decimal(comparison_oracle)
    at_count = oracle_arithmetic_with_count(
        compared_career, birth, context.params, count
    )
    if difference == 0:
        attribution = ATTR_EXACT
    elif count != oracle_count and result.aime == Decimal(at_count):
        attribution = ATTR_COUNT
    else:
        attribution = ATTR_UNEXPLAINED
    record.update(
        status="executed",
        oracle_aime_compared=comparison_oracle,
        axiom_aime=_decimal_str(result.aime),
        difference=_decimal_str(difference),
        exact_match=difference == 0,
        oracle_arithmetic_at_candidate_count=at_count,
        attribution=attribution,
        stdout_sha256=result.stdout_sha256,
        engine_version=result.engine_version,
        engine_stderr=result.stderr,
    )
    if result.ordinary_pia_before_cola is not None:
        record["axiom_ordinary_pia_before_cola"] = _decimal_str(
            result.ordinary_pia_before_cola
        )
        record["pia_status"] = result.pia_status
        if context.pia_check_params is not None:
            oracle_pia = benefits.pia(
                float(result.aime),
                prepared.determinations.year_attained_age_62,
                context.pia_check_params,
            )
            record["oracle_pia_formula_at_axiom_aime"] = _float_text(
                oracle_pia
            )
            record["pia_formula_difference"] = _decimal_str(
                result.ordinary_pia_before_cola
                - Decimal(_float_text(oracle_pia))
            )
    return record, result


def refusal_classes(
    refusal: bridge.BenefitBridgeRefusal,
    cutoff_year: int,
    panel_first_year: int = PANEL_FIRST_YEAR,
) -> list[str]:
    """Coarse, person-independent classes of a refusal's gaps."""

    classes = set()
    for name, years in refusal.gaps.items():
        if name == "missing_required_years":
            if any(y < panel_first_year for y in years):
                classes.add("elapsed_window_years_before_the_psid_panel")
            if any(y > cutoff_year for y in years):
                classes.add("elapsed_window_years_after_the_cutoff")
            if any(panel_first_year <= y <= cutoff_year for y in years):
                classes.add("elapsed_window_years_inside_the_panel")
        else:
            classes.add(name)
    if not refusal.gaps:
        classes.add("determinations")
    return sorted(classes)


def run_pass(
    persons: Sequence[PersonInput],
    context: PassContext,
    *,
    workers: int = 1,
    on_result: (
        Callable[[dict, bridge.AxiomBenefitResult | None], None] | None
    ) = None,
) -> list[dict[str, Any]]:
    """Every person through one pass; refusals never stop the others.

    A changed or absent bound file raises ``BindingMismatch`` and stops
    the pass.
    """

    def one(person: PersonInput):
        record, result = compare_person(person, context)
        if on_result is not None:
            on_result(record, result)
        return record

    if workers <= 1:
        records = [one(person) for person in persons]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            records = list(pool.map(one, persons))
    return sorted(records, key=lambda r: r["person_id"])


# --------------------------------------------------------------------------
# Summaries
# --------------------------------------------------------------------------
def _share(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _quantile(sorted_values: Sequence[Decimal], q: float) -> str | None:
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1, int(q * (len(sorted_values) - 1)))
    return _decimal_str(sorted_values[index])


def summarize_records(records: Sequence[Mapping[str, Any]]) -> dict:
    """Counts, exact-match share and the distribution of differences."""

    status = Counter(r["status"] for r in records)
    executed = [r for r in records if r["status"] == "executed"]
    exact = sum(bool(r["exact_match"]) for r in executed)
    differences = sorted(Decimal(r["difference"]) for r in executed)
    nonzero = [d for d in differences if d != 0]
    refusal_reasons = Counter(
        cls for r in records for cls in r.get("refusal_classes", ())
    )
    failure_reasons = Counter(
        reason
        for r in records
        if r["status"] == "failed"
        for reason in r.get("reasons", ())
    )
    return {
        "persons": len(records),
        "oracle_aime_differs_from_track_a": sum(
            r["oracle_aime"] != r["track_a_oracle_aime"] for r in records
        ),
        "status": dict(sorted(status.items())),
        "executed": len(executed),
        "exact_matches": exact,
        "exact_match_share_of_executed": _share(exact, len(executed)),
        "attribution": dict(
            sorted(Counter(r["attribution"] for r in executed).items())
        ),
        "difference_counts": {
            _decimal_str(value): count
            for value, count in sorted(Counter(differences).items())
        },
        "nonzero_differences": {
            "count": len(nonzero),
            "min": _decimal_str(min(nonzero)) if nonzero else None,
            "max": _decimal_str(max(nonzero)) if nonzero else None,
            "median": _quantile(sorted(nonzero), 0.5),
            "p90_abs": _quantile(sorted(abs(d) for d in nonzero), 0.9),
            "mean_abs": (
                _decimal_str(
                    (sum(abs(d) for d in nonzero) / len(nonzero)).quantize(
                        Decimal("0.01")
                    )
                )
                if nonzero
                else None
            ),
            "positive": sum(d > 0 for d in nonzero),
            "negative": sum(d < 0 for d in nonzero),
        },
        "all_differences_quantiles": {
            str(q): _quantile(differences, q)
            for q in (0.0, 0.01, 0.1, 0.5, 0.9, 0.99, 1.0)
        },
        "refusal_classes": dict(sorted(refusal_reasons.items())),
        "failure_reasons": dict(sorted(failure_reasons.items())),
        "rows": dict(
            sorted(
                sum(
                    (Counter(r.get("rows", {})) for r in records),
                    Counter(),
                ).items()
            )
        ),
    }


def summarize_pass(records: Sequence[Mapping[str, Any]]) -> dict:
    """The pass summary overall, by route and by computation-year count."""

    by_route = {
        route: summarize_records([r for r in records if r["route"] == route])
        for route in ROUTES
        if any(r["route"] == route for r in records)
    }
    by_count = {
        "35_computation_years": summarize_records(
            [r for r in records if r["candidate_computation_years"] == 35]
        ),
        "fewer_than_35_computation_years": summarize_records(
            [r for r in records if r["candidate_computation_years"] != 35]
        ),
    }
    return {
        "overall": summarize_records(records),
        "primary_routes": summarize_records(
            [r for r in records if r["route"] in PRIMARY_ROUTES]
        ),
        "by_route": by_route,
        "by_candidate_computation_years": by_count,
        "by_computation_year_count": computation_count_detail(records),
    }


def computation_count_detail(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Per candidate computation-year count: who, and how they agree."""

    out = {}
    for count in sorted({r["candidate_computation_years"] for r in records}):
        group = [
            r for r in records if r["candidate_computation_years"] == count
        ]
        executed = [r for r in group if r["status"] == "executed"]
        births = [r["birth_year"] for r in group]
        out[str(count)] = {
            "persons": len(group),
            "birth_years": f"{min(births)}-{max(births)}",
            "executed": len(executed),
            "exact_matches": sum(bool(r["exact_match"]) for r in executed),
            "attribution": dict(
                sorted(Counter(r["attribution"] for r in executed).items())
            ),
            "max_difference": (
                _decimal_str(max(Decimal(r["difference"]) for r in executed))
                if executed
                else None
            ),
        }
    return out


#: Reporting bins for the difference (dollars, engine minus oracle).
DIFFERENCE_BINS: tuple[tuple[str, Decimal | None, Decimal | None], ...] = (
    ("below 0", None, Decimal(0)),
    ("0", Decimal(0), Decimal(1)),
    ("1 to 9", Decimal(1), Decimal(10)),
    ("10 to 49", Decimal(10), Decimal(50)),
    ("50 to 99", Decimal(50), Decimal(100)),
    ("100 to 199", Decimal(100), Decimal(200)),
    ("200 to 499", Decimal(200), Decimal(500)),
    ("500 and above", Decimal(500), None),
)


def difference_bins(difference_counts: Mapping[str, int]) -> dict[str, int]:
    """Bin the exact per-value counts (bins are [low, high))."""

    out = {label: 0 for label, _, _ in DIFFERENCE_BINS}
    for text, count in difference_counts.items():
        value = Decimal(text)
        for label, low, high in DIFFERENCE_BINS:
            if (low is None or value >= low) and (
                high is None or value < high
            ):
                out[label] += count
                break
    return out


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.2f}%"


def _row(*cells: Any) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def render_results(result: Mapping[str, Any]) -> str:
    """RESULTS.md from ``result.json`` (deterministic; no new numbers).

    Refuses a result of any other schema (v1 has no oracle choice, v2 an
    earlier artifact binding): its report text belongs to the script at
    the commit its provenance records.
    """

    if result.get("schema_version") != SCHEMA_VERSION or "oracle" not in (
        result
    ):
        raise ValueError(
            "result.json has schema "
            f"{result.get('schema_version', 'unknown')}, not {SCHEMA_VERSION};"
            " render it with the script at the commit its provenance records"
        )
    lines: list[str] = []
    add = lines.append
    passes = result["passes"]
    primary = passes[PASS_PRIMARY]["summary"]
    overall = primary["overall"]
    selection = result["selection"]
    cohort = result["cohort"]
    oracle = result["oracle"]
    convention = ComputationYears(oracle["computation_years"])
    statutory = convention is ComputationYears.STATUTORY
    title = (
        "# Track C step 1: AIME agreement, Axiom engine vs Python oracle "
        f"({'statutory' if statutory else 'legacy fixed-35'} computation "
        "years)"
    )
    add(title)
    add("")
    if result.get("partial"):
        add(
            "**PARTIAL SMOKE RUN** (`--limit`): not every selected person "
            "was compared. Do not cite these numbers."
        )
        add("")
    add(
        f"**Oracle: {oracle['name']}** "
        f"(`--oracle-computation-years {oracle['choice']}`)."
    )
    add("")
    add(
        "**The Axiom RuleSpec candidates are unaccepted.** Agreement is "
        "diagnostic only. The Python oracle is transitional (not Axiom). "
        "The people are the real Track A PSID-seeded closed cohort. This "
        "is **not** the COLA statistic: nothing here computes a benefit "
        "path, a reform or any age-profile value."
    )
    add("")
    add("## Result")
    add("")
    st = overall["status"]
    by_count = primary["by_candidate_computation_years"]
    count35 = by_count["35_computation_years"]
    fewer = by_count["fewer_than_35_computation_years"]
    attribution = overall["attribution"]
    if statutory:
        attribution_text = (
            "oracle's own arithmetic with the candidate's computation-year "
            "count (elapsed years minus 5, fewer than 35 for people born "
            "before 1929; the statutory oracle uses that count too, so no "
            "disagreement can be attributed to it) and "
        )
    else:
        attribution_text = (
            "oracle's own arithmetic with the candidate's computation-year "
            "count (elapsed years minus 5, fewer than 35 for people born "
            "before 1929; the legacy oracle always uses 35) and "
        )
    add(
        f"Primary pass, oracle with {oracle['name']}: "
        f"{overall['executed']} of {overall['persons']} "
        f"selected persons were executed on the engine "
        f"({st.get('refused', 0)} refused, {st.get('failed', 0)} failed). "
        f"The engine's AIME equals the oracle's for "
        f"{overall['exact_matches']} "
        f"({_pct(overall['exact_match_share_of_executed'])}); among the "
        f"{count35['executed']} executed people with 35 candidate "
        f"computation years (born 1929 or later) it equals the oracle's "
        f"for {count35['exact_matches']}, and among the "
        f"{fewer['executed']} with fewer (born before 1929) for "
        f"{fewer['exact_matches']}. Of the "
        f"{overall['nonzero_differences']['count']} disagreements, "
        f"{attribution.get(ATTR_COUNT, 0)} are reproduced exactly by the "
        + attribution_text
        + f"{attribution.get(ATTR_UNEXPLAINED, 0)} are unexplained."
    )
    add("")
    if "oracle_aime_differs_from_track_a" in overall:
        add(
            "This oracle's AIME differs from Track A's (the fixed-35 "
            "`LEGACY_FIXED_35` AIME, recorded per person as "
            f"`track_a_oracle_aime`) for "
            f"{overall['oracle_aime_differs_from_track_a']} of the "
            f"{overall['persons']} selected people: "
            f"{fewer.get('oracle_aime_differs_from_track_a', 0)} of the "
            f"{fewer['persons']} with fewer than 35 candidate computation "
            f"years and {count35.get('oracle_aime_differs_from_track_a', 0)}"
            f" of the {count35['persons']} with 35."
        )
        add("")
    add(
        "The inputs are the cohort's PSID careers under declarations both "
        "sides share (below); agreement shows the engine and the oracle "
        "compute the same AIME from the same rows, not that either AIME "
        "is a person's true AIME."
    )
    add("")
    add("## What was compared")
    add("")
    add(
        f"- Cohort: the {cohort['anchor_wave']}-wave Track A cohort "
        f"(opening {cohort['cutoff_year']}), {cohort['members']} members, "
        "built with `psid2010.load_psid2010_inputs` + "
        "`build_psid2010_cohort` + `prepare_track_a_cohort("
        "data_provenance='registered_real')`. Careers run from "
        "max(1968, birth year + 22) through "
        f"{cohort['cutoff_year']}."
    )
    add(
        f"- Selected: {selection['selected']} members whose year of "
        f"attaining 62 lies in {selection['eligibility_window']} (Track A "
        "computes the oracle retirement AIME at that year, refuses "
        "eligibility before 1979, and projects to 2030). Not selected: "
        + "; ".join(
            f"{count} ({selection['exclusion_definitions'][code]})"
            for code, count in selection["exclusions"].items()
        )
        + "."
    )
    add(
        "- Routes in the selection: "
        + ", ".join(
            f"`{route}` {count}"
            for route, count in selection["routes"].items()
        )
        + "."
    )
    if statutory:
        add(
            "- Oracle side: `ss.statutory_aime.oracle_aime(career, "
            "birth_year, params, computation_years=ComputationYears."
            "STATUTORY)`, the default of "
            "`scenario_benefits.eligibility_pia_for_clock` for the age-62 "
            "clock (Track A itself passes the legacy fixed 35), with Track "
            f"A's parameters (`{result['parameters']['track_a_revision']}`)."
            " It limits each year to the contribution and benefit base, "
            "indexes to the year of attaining 60, takes the highest n years "
            "(absent years count as zero), n being the elapsed years minus "
            "5 (42 USC 415(b)(2); 35 for people born 1929 or later), and "
            "floors the total over 12n months. Track A's fixed-35 AIME is "
            "recorded beside it for every person but is not what the engine "
            "is compared with."
        )
    else:
        add(
            "- Oracle side: `ss.benefits.aime(career, birth_year, params)` "
            "(`ss.statutory_aime.oracle_aime` with `computation_years="
            "ComputationYears.LEGACY_FIXED_35`), the call "
            "`scenario_benefits.eligibility_pia_for_clock` makes for Track "
            "A's age-62 clock under Track A's computation-year convention, "
            "with Track A's parameters "
            f"(`{result['parameters']['track_a_revision']}`). It limits "
            "each year to the contribution and benefit base, indexes to the "
            "year of attaining 60, takes the highest 35 years (absent years "
            "count as zero) and floors the total over 420 months. For "
            "people born before 1929, 42 USC 415(b)(2) gives fewer than 35 "
            "computation years (the `statutory` choice)."
        )
    add(
        "- Axiom side: `axiom_benefit_bridge` requests on the pinned "
        "engine (hashes below). The 415(b) candidate counts benefit "
        "computation years as elapsed years minus 5, at least 2 (elapsed "
        "years are the calendar years after the later of 1950 and the year "
        "of attaining 21 and before the year of attaining 62), indexes "
        "years up to the indexing year in the engine's decimal arithmetic "
        "(the request's `arithmetic: decimal`), ranks "
        "only computation base years before the entitlement year, and "
        "floors the total over 12 times that count."
    )
    add("")
    add("Declarations, all recorded per person in `result.json`:")
    add("")
    for key, text in result["declarations"].items():
        add(f"- **{key}**: {text}")
    add("")
    add("## Primary pass: engine agreement on identical years")
    add("")
    add(
        "Entitlement year sent: max(birth year + 62, "
        f"{cohort['cutoff_year'] + 1}), so the engine ranks exactly the "
        "career years the oracle ranks, plus explicit zero years."
    )
    add("")
    add(
        _row(
            "Group",
            "Persons",
            "Executed",
            "Refused",
            "Failed",
            "Exact matches",
            "Exact-match share",
        )
    )
    add(_row("---", "---:", "---:", "---:", "---:", "---:", "---:"))

    def summary_row(label: str, s: Mapping[str, Any]) -> str:
        st = s["status"]
        return _row(
            label,
            s["persons"],
            s["executed"],
            st.get("refused", 0),
            st.get("failed", 0),
            s["exact_matches"],
            _pct(s["exact_match_share_of_executed"]),
        )

    add(summary_row("**All selected**", overall))
    add(
        summary_row(
            "Retired-worker stock + projected claimants",
            primary["primary_routes"],
        )
    )
    for route, s in primary["by_route"].items():
        add(summary_row(f"route `{route}`", s))
    for key, s in primary["by_candidate_computation_years"].items():
        add(summary_row(f"candidate count: {key.replace('_', ' ')}", s))
    add("")
    add("Route definitions (from `cola_track_a/benefits.py`):")
    add("")
    for route, text in ROUTES.items():
        add(f"- `{route}`: {text}.")
    add("")
    add("### Distribution of differences (Axiom AIME minus oracle AIME)")
    add("")
    add(_row("Difference ($)", "Persons"))
    add(_row("---", "---:"))
    for label, count in difference_bins(overall["difference_counts"]).items():
        add(_row(label, count))
    add("")
    add("Per-dollar counts are under `difference_counts` in `result.json`.")
    add("")
    nz = overall["nonzero_differences"]
    add(
        f"Nonzero differences: {nz['count']} (positive {nz['positive']}, "
        f"negative {nz['negative']}; min {nz['min']}, median {nz['median']},"
        f" max {nz['max']}, mean absolute {nz['mean_abs']}, 90th percentile "
        f"of absolute {nz['p90_abs']})."
    )
    add("")
    add("### Attribution (verification only, not a third model)")
    add("")
    add(_row("Attribution", "Persons"))
    add(_row("---", "---:"))
    for key, count in overall["attribution"].items():
        add(_row(key, count))
    add("")
    add(
        f"`{ATTR_COUNT}` means the engine's AIME equals the oracle's own "
        "arithmetic (its creditable and indexed history) rerun with the "
        "candidate's number of computation years instead of the oracle's "
        + (
            "(the statutory oracle already uses the candidate's count, so "
            "no record can have this attribution). "
            if statutory
            else "(35, the legacy oracle's). "
        )
        + f"`{ATTR_UNEXPLAINED}` lists every other disagreement; their "
        "requests and engine outputs are in `executions/` (up to the cap "
        "recorded under `executions` in `result.json`; each written "
        "record names its files)."
    )
    detail = primary["by_computation_year_count"]
    add("")
    add("By the candidate's computation-year count:")
    add("")
    add(
        _row(
            "Count",
            "Born",
            "Persons",
            "Executed",
            "Exact",
            f"`{ATTR_COUNT}`",
            f"`{ATTR_UNEXPLAINED}`",
            "Max difference ($)",
        )
    )
    add(_row("---:", "---", "---:", "---:", "---:", "---:", "---:", "---:"))
    for count, row in detail.items():
        add(
            _row(
                count,
                row["birth_years"],
                row["persons"],
                row["executed"],
                row["exact_matches"],
                row["attribution"].get(ATTR_COUNT, 0),
                row["attribution"].get(ATTR_UNEXPLAINED, 0),
                row["max_difference"],
            )
        )
    add("")
    add(
        "An exact match with fewer than 35 years means both divisions "
        "floor to the same dollar (for example, a zero total)."
    )
    add("")
    add("### Rows sent to the engine (primary pass, all persons)")
    add("")
    rows = overall["rows"]
    add(_row("Row kind", "Rows"))
    add(_row("---", "---:"))
    for key, label in ROW_LABELS:
        add(_row(label, rows.get(key, 0)))
    add("")
    add(
        f"{rows.get('synthetic', 0)} of {rows.get('sent', 0)} rows are "
        "labeled synthetic. Career amounts above the contribution and "
        f"benefit base were limited to it in {rows.get('limited_to_base', 0)}"
        " rows (the oracle's own `creditable_history`); in "
        f"{rows.get('shortest_decimal_differs_from_binary', 0)} rows the "
        "shortest round-trip decimal differs from the exact binary64 value."
    )
    add("")
    add("### Refusals and failures")
    add("")
    add(
        f"Primary pass: {overall['status'].get('refused', 0)} refused, "
        f"{overall['status'].get('failed', 0)} failed."
    )
    if overall["refusal_classes"]:
        add("")
        add(_row("Refusal class", "Persons"))
        add(_row("---", "---:"))
        for key, count in overall["refusal_classes"].items():
            add(_row(key, count))
    if overall["failure_reasons"]:
        add("")
        for reason, count in overall["failure_reasons"].items():
            add(f"- {count} x {reason}")
    strict = passes[PASS_STRICT]["summary"]["overall"]
    add("")
    add(
        "Strict transport (no synthetic zero years; requests prepared, "
        f"nothing executed): {strict['status'].get('refused', 0)} of "
        f"{strict['persons']} refused, "
        f"{strict['status'].get('accepted_not_executed', 0)} accepted."
    )
    add("")
    add(_row("Strict refusal class", "Persons"))
    add(_row("---", "---:"))
    for key, count in strict["refusal_classes"].items():
        add(_row(key, count))
    add("")
    add(
        "The bridge never pads a year, so without the declared zero rows "
        "it refuses everyone whose elapsed window reaches before 1968 or "
        f"after {cohort['cutoff_year']}."
    )
    diag = passes.get(PASS_DIAGNOSTIC)
    if diag is not None:
        d = diag["summary"]["overall"]
        conv = diag["truncation_effect"]
        add("")
        add("## Diagnostic pass: Track A's recorded opening entitlement year")
        add("")
        add(
            "Opening-stock retired workers only. Entitlement year sent: the "
            "`OpeningStockRecord.entitlement_year` Track A records (the A3 "
            "receipt start, clamped to the age-62 clock). Career years from "
            "entitlement on are not computation base years and are not "
            "sent, so the engine is compared with the oracle on the same "
            "truncated years. This measures engine agreement on those "
            "inputs, not Track A's AIME."
        )
        add("")
        add(
            _row(
                "Persons",
                "Executed",
                "Refused",
                "Failed",
                "Exact matches",
                "Exact-match share",
            )
        )
        add(_row("---:", "---:", "---:", "---:", "---:", "---:"))
        add(
            _row(
                d["persons"],
                d["executed"],
                d["status"].get("refused", 0),
                d["status"].get("failed", 0),
                d["exact_matches"],
                _pct(d["exact_match_share_of_executed"]),
            )
        )
        add("")
        add(f"Attribution: {json.dumps(d['attribution'])}.")
        add("")
        add(
            "Effect of the truncation on the oracle itself (the oracle's "
            "AIME on the years before the recorded entitlement minus its "
            "full-career AIME, both with the oracle's computation years): "
            f"{conv['persons_with_career_years_dropped']} persons have "
            f"career years at or after entitlement, "
            f"{conv['persons_with_nonzero_years_dropped']} of them nonzero; "
            f"the oracle AIME changes for {conv['changed']} "
            f"(min {conv['min']}, median {conv['median']}, max "
            f"{conv['max']})."
        )
    pia = result.get("pia_check")
    add("")
    add("## PIA: what was and was not compared")
    add("")
    add(
        "The 415(a) candidate computes an ordinary PIA only for people "
        "first eligible in 2026 (born 1964); the bridge requests it for no "
        "one else. No Track A PIA was compared: Track A's oracle "
        "derives the 2026 bend points from the TR2008 AWI "
        f"({pia['track_a_bend_points_2026']}), while the candidate's "
        "bend-point module derives them from SSA's published 2024 AWI "
        "(69,846.57), which gives "
        f"{pia['published_bend_points_2026']}."
    )
    consistency = result.get("oracle_pia_consistency")
    if consistency is not None:
        add("")
        add(
            "Before any engine call the script checked, for all "
            f"{consistency['persons']} selected people, that "
            "`scenario_benefits.eligibility_pia_for_clock` rests on the "
            "AIMEs recorded here under "
            + " and ".join(
                f"`{value}`" for value in consistency["conventions_checked"]
            )
            + " (its PIA equals `ss.benefits.pia` of that AIME at the year "
            "of attaining 62). The legacy convention is the one Track A's "
            "assembly passes."
        )
    add("")
    add(
        f"Formula check only, not a Track A quantity: for the "
        f"{pia['persons']} executed people born 1964, the oracle's "
        "`ss.benefits.pia` at the engine's AIME with the published 2026 "
        "bend points (the untransformed policyengine-us bundle, "
        f"`{pia['check_params_revision']}`) agrees with the engine's "
        f"ordinary PIA for {pia['agree']} of {pia['persons']}"
        + (
            f"; differences: {json.dumps(pia['difference_counts'])}."
            if pia["persons"] != pia["agree"]
            else "."
        )
    )
    add("")
    add("## Not compared")
    add("")
    for item in result["not_compared"]:
        add(f"- {item}")
    add("")
    add("## Engine, artifacts and modules")
    add("")
    binding = result["provenance"]["engine_binding"]
    add(_row("Role", "SHA-256", "Path"))
    add(_row("---", "---", "---"))
    add(
        _row(
            "engine",
            f"`{binding['engine']['sha256']}`",
            f"`{binding['engine']['path']}`",
        )
    )
    for item in binding["artifacts"] + binding["supporting"]:
        add(_row(item["role"], f"`{item['sha256']}`", f"`{item['path']}`"))
    add("")
    prov = result["provenance"]
    add(
        f"- Engine source commit `{binding['engine_source_commit']}`; "
        f"engine versions reported: {', '.join(prov['engine_versions'])}; "
        f"candidates accepted: {binding['candidates_accepted']}."
    )
    add(f"- Candidate status: {binding['candidate_status']}.")
    add(
        f"- Repository commit `{prov['git']['head']}` (clean: "
        f"{prov['git']['clean']}); script SHA-256 "
        f"`{prov['source_sha256']['scripts/track_c_aime_agreement.py']}`; "
        "bridge SHA-256 "
        f"`{prov['source_sha256']['src/populace_dynamics/axiom_benefit_bridge.py']}`."
    )
    add(
        f"- PSID files bundle SHA-256 "
        f"`{cohort['psid_files_bundle_sha256']}`; A3 content SHA-256 "
        f"`{cohort['a3_content_sha256']}`; Track A cohort seal "
        f"`{cohort['track_a_seal']}`."
    )
    artifact = cohort.get("track_a_artifact")
    if artifact is not None:
        add(_artifact_binding_text(artifact))
    add(
        f"- Wage index series digest `{result['parameters']['wage_index']['source_sha256']}`"
        f" ({result['parameters']['wage_index']['years']}); contribution "
        "base digest "
        f"`{result['parameters']['contribution_base']['source_sha256']}`."
    )
    add("")
    add("## Files")
    add("")
    add(
        "- `result.json`: every selected person in every pass (status, "
        "the oracle's, Track A's and the engine's AIMEs, the difference, "
        "attribution, row counts by kind, "
        "request and stdout digests, refusal reasons), the summaries, the "
        "declarations and the provenance."
    )
    written = result.get("executions", {})
    add(
        "- `executions/`: the exact request and engine stdout for "
        f"`{ATTR_UNEXPLAINED}` persons (at most "
        f"{written.get('max_unexplained_per_pass', 'n/a')} per pass) and "
        f"for {written.get('examples_per_class', 'n/a')} examples of each "
        "other attribution class per pass (first to finish), "
        f"{written.get('persons_written', 'n/a')} persons in all. Failed "
        "persons have no engine stdout; their reasons and request digests "
        "are in `result.json`, and every request can be rebuilt from the "
        "script and the recorded inputs."
    )
    add(
        "- The script: `scripts/track_c_aime_agreement.py` at the "
        "repository commit above."
    )
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# The real run
# --------------------------------------------------------------------------
def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_SOURCES = (
    "scripts/track_c_aime_agreement.py",
    "src/populace_dynamics/axiom_benefit_bridge.py",
    "src/populace_dynamics/ss/benefits.py",
    "src/populace_dynamics/ss/statutory_aime.py",
    "src/populace_dynamics/ss/params.py",
    "src/populace_dynamics/scenario_benefits.py",
    "src/populace_dynamics/cola_track_a/benefits.py",
    "src/populace_dynamics/cola_track_a/opening.py",
    "src/populace_dynamics/cola_track_a/runner.py",
    "src/populace_dynamics/cola_track_a/statutory.py",
    "src/populace_dynamics/cohorts/psid2010.py",
    "src/populace_dynamics/estimates/career.py",
)


def _load_cohort(anchor_wave: int, reference_year: int):
    from populace_dynamics.cohorts import psid2010
    from populace_dynamics.cola_track_a import TrackAConfig
    from populace_dynamics.cola_track_a.opening import (
        prepare_track_a_cohort,
        track_a_cohort_sha256,
    )

    config = TrackAConfig()
    if config.reference_year != reference_year:
        raise ValueError("Track A's reference year changed")
    raw = psid2010.load_psid2010_inputs(anchor_wave=anchor_wave)
    a3 = psid2010.build_psid2010_cohort(
        raw, psid2010.Psid2010CohortSpec(anchor_wave=anchor_wave)
    )
    cohort = prepare_track_a_cohort(
        a3, data_provenance="registered_real", config=config
    )
    if cohort.seal != track_a_cohort_sha256(cohort):
        raise ValueError("the Track A cohort seal does not match")
    provenance: dict[str, dict[int, str]] = {}
    earnings_check: dict[int, dict[int, float]] = {}
    for pid, year, value, kind in a3.careers[
        ["person_id", "year", "earnings", "provenance"]
    ].itertuples(index=False, name=None):
        provenance.setdefault(int(pid), {})[int(year)] = str(kind)
        earnings_check.setdefault(int(pid), {})[int(year)] = float(value)
    for pid, career in cohort.careers.items():
        if dict(career) != earnings_check.get(int(pid), {}):
            raise ValueError(f"career of {pid} differs from the A3 frame")
    info = {
        "anchor_wave": anchor_wave,
        "cutoff_year": cohort.start_year,
        "members": int(len(cohort.persons)),
        "psid_files_bundle_sha256": raw.provenance["psid_files_bundle_sha256"],
        "psid_data_dir": raw.provenance["psid_data_dir"],
        "psid_file_count": len(raw.provenance["psid_files_sha256"]),
        "a3_provenance_kind": a3.provenance["kind"],
        "a3_content_sha256": a3.provenance["content_sha256"],
        "track_a_seal": cohort.seal,
        "career_provenance_rows": dict(
            sorted(Counter(a3.careers["provenance"].astype(str)).items())
        ),
    }
    return cohort, provenance, info


#: The committed Track A artifact whose cohort and parameters are matched.
TRACK_A_ARTIFACT = Path("runs/replication_urban2010_cola_v1.json")


def _json_normal(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


#: Cohort diagnostics the current code produces that the Track A artifact
#: does not record.  Each was added after the artifact was written (the
#: commit is named), and each is a count breakdown of recorded
#: diagnostics: its counts must sum to the recorded ``total`` and name only
#: categories the recorded ``categories`` mapping counts, none above its
#: recorded count.  Any other diagnostic the artifact lacks refuses the
#: run, as the whole-dict comparison did: a new key is reviewed and listed
#: here before Track C binds to a cohort that carries it.
KNOWN_ADDITIVE_DIAGNOSTICS: Mapping[str, Mapping[str, str]] = {
    "opening_stock_entitlement_clamped_by_clock_rule": {
        "added_by": "bfe9fa3e",
        "total": "opening_stock_entitlement_clamped",
        "categories": "opening_stock_clock_rules",
    },
}


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _breakdown_check(
    key: str, value: Any, recorded: Mapping[str, Any]
) -> dict[str, Any] | None:
    """How a known additive diagnostic reconciles; ``None`` if unknown."""

    known = KNOWN_ADDITIVE_DIAGNOSTICS.get(key)
    if known is None:
        return None
    total_key, categories_key = known["total"], known["categories"]
    total = recorded.get(total_key)
    categories = recorded.get(categories_key)
    parts = dict(value) if isinstance(value, Mapping) else None
    countable = (
        parts is not None
        and all(_is_count(count) and count >= 0 for count in parts.values())
        and _is_count(total)
    )
    within = (
        countable
        and isinstance(categories, Mapping)
        and all(
            name in categories
            and _is_count(categories[name])
            and count <= categories[name]
            for name, count in parts.items()
        )
    )
    return {
        "added_by": known["added_by"],
        "total_key": total_key,
        "recorded_total": total,
        "sum": sum(parts.values()) if countable else None,
        "sums_to_recorded_total": bool(
            countable and sum(parts.values()) == total
        ),
        "categories_key": categories_key,
        "within_recorded_categories": bool(within),
    }


def track_a_artifact_binding(
    artifact: Mapping[str, Any],
    *,
    anchor_wave: int,
    diagnostics: Mapping[str, Any],
    source_provenance: Mapping[str, Any],
    parameters_revision: str,
) -> dict[str, Any]:
    """Compare the cohort and parameters with the committed Track A run.

    Reads only the artifact's parameter revision and its cohort
    diagnostics and source provenance; nothing about benefits or age
    groups.  Every diagnostic the artifact records must be present in
    ``diagnostics`` with an equal value (compared as JSON); a missing or
    changed one fails ``cohort_diagnostics_equal_on_recorded_keys``.
    A diagnostic the artifact does not record must be one of
    :data:`KNOWN_ADDITIVE_DIAGNOSTICS` (``additive_diagnostic_keys_known``)
    and reconcile with the recorded diagnostics it breaks down: its counts
    sum to the recorded total (``additive_breakdowns_sum_to_recorded_
    totals``) and fit within the recorded per-category counts
    (``additive_breakdowns_within_recorded_categories``).  The source
    provenance and the parameter revision must be equal as a whole.

    Returns ``checks`` (all must be true) and what was compared.
    """

    recorded = _json_normal(dict(artifact["cohorts"][str(anchor_wave)]))
    recorded_source = recorded.pop("source_provenance")
    fresh = _json_normal(dict(diagnostics))
    missing = sorted(set(recorded) - set(fresh))
    changed = sorted(
        key for key in recorded if key in fresh and fresh[key] != recorded[key]
    )
    additive = {key: fresh[key] for key in sorted(set(fresh) - set(recorded))}
    breakdowns = {
        key: _breakdown_check(key, value, recorded)
        for key, value in additive.items()
    }
    known = [check for check in breakdowns.values() if check is not None]
    checks = {
        "ssa_parameters_revision_equal": (
            artifact["ssa_parameters_revision"] == parameters_revision
        ),
        "cohort_diagnostics_equal_on_recorded_keys": not missing
        and not changed,
        "additive_diagnostic_keys_known": len(known) == len(breakdowns),
        "additive_breakdowns_sum_to_recorded_totals": all(
            check["sums_to_recorded_total"] for check in known
        ),
        "additive_breakdowns_within_recorded_categories": all(
            check["within_recorded_categories"] for check in known
        ),
        "cohort_source_provenance_equal": (
            recorded_source == _json_normal(dict(source_provenance))
        ),
    }
    return {
        "checks": checks,
        "recorded_diagnostic_keys": sorted(recorded),
        "recorded_keys_missing": missing,
        "recorded_keys_changed": {
            key: {"recorded": recorded[key], "fresh": fresh[key]}
            for key in changed
        },
        "additive_diagnostic_keys": additive,
        "unknown_additive_diagnostic_keys": sorted(
            key for key, check in breakdowns.items() if check is None
        ),
        "additive_breakdowns": breakdowns,
    }


def require_track_a_artifact(
    artifact_bytes: bytes,
    *,
    path: Path | str = TRACK_A_ARTIFACT,
    anchor_wave: int,
    diagnostics: Mapping[str, Any],
    source_provenance: Mapping[str, Any],
    parameters_revision: str,
) -> dict[str, Any]:
    """The recorded binding, or ``SystemExit`` naming every failed check."""

    binding = track_a_artifact_binding(
        json.loads(artifact_bytes),
        anchor_wave=anchor_wave,
        diagnostics=diagnostics,
        source_provenance=source_provenance,
        parameters_revision=parameters_revision,
    )
    if not all(binding["checks"].values()):
        failed = sorted(k for k, ok in binding["checks"].items() if not ok)
        raise SystemExit(
            f"the cohort or parameters differ from {path}: failed {failed}; "
            f"recorded keys missing {binding['recorded_keys_missing']}; "
            f"recorded keys changed {binding['recorded_keys_changed']}; "
            "diagnostics neither recorded nor in "
            "KNOWN_ADDITIVE_DIAGNOSTICS "
            f"{binding['unknown_additive_diagnostic_keys']}; "
            f"additive breakdowns {binding['additive_breakdowns']}"
        )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        **binding,
    }


def _artifact_binding_text(artifact: Mapping[str, Any]) -> str:
    """The RESULTS.md line for the Track A artifact binding."""

    recorded = artifact.get("recorded_diagnostic_keys", ())
    text = (
        f"- Every cohort diagnostic recorded in `{artifact['path']}` "
        f"(SHA-256 `{artifact['sha256']}`; {len(recorded)} keys), its "
        "source provenance and its parameter revision equal the fresh "
        f"cohort's (checks {json.dumps(artifact['checks'])}); only those "
        "fields of the artifact were used."
    )
    additive = artifact.get("additive_diagnostic_keys") or {}
    if not additive:
        return text + " The fresh cohort records no other diagnostic."
    parts = []
    for key, value in additive.items():
        part = f"`{key}` = `{json.dumps(value, sort_keys=True)}`"
        check = (artifact.get("additive_breakdowns") or {}).get(key)
        if check is not None:
            part += (
                f" (added in `{check['added_by']}`; sum {check['sum']}, "
                f"recorded `{check['total_key']}` {check['recorded_total']};"
                f" within recorded `{check['categories_key']}`: "
                f"{'yes' if check['within_recorded_categories'] else 'no'})"
            )
        parts.append(part)
    return (
        text + " The fresh cohort also records diagnostics the artifact "
        "does not. Each is a reviewed breakdown listed in "
        "`KNOWN_ADDITIVE_DIAGNOSTICS` with the commit that added it; its "
        "counts must sum to the recorded total and name only recorded "
        "categories, none above its recorded count (an unlisted diagnostic "
        "refuses the run): " + "; ".join(parts) + "."
    )


def _parameters():
    from populace_dynamics.cola_track_a import TrackAConfig
    from populace_dynamics.cola_track_a.runner import tr2008_ssa_parameters
    from populace_dynamics.cola_track_a.statutory import (
        CAPTURE_SHA256,
        captured_ssa_parameters,
    )
    from populace_dynamics.ss.params import load_ssa_parameters

    config = TrackAConfig()
    base = load_ssa_parameters()
    params = tr2008_ssa_parameters(base, alternative=config.tr2008_alternative)
    captured = captured_ssa_parameters(alternative=config.tr2008_alternative)
    checks = {
        "nawi_equal_to_committed_capture": params.nawi == captured.nawi,
        "wage_base_equal_1937_2010": all(
            params.wage_base_for(y) == captured.wage_base_for(y)
            for y in range(1937, 2011)
        ),
        "pia_factors_equal": params.pia_factors == captured.pia_factors,
    }
    if not all(checks.values()):
        raise ValueError(
            f"Track A parameters differ from the capture: {checks}"
        )
    if base.bend_points(2026) != (1286.0, 7749.0):
        raise ValueError(
            "the untransformed bundle's 2026 bend points are not SSA's "
            f"published 1,286 / 7,749: {base.bend_points(2026)}"
        )
    return (
        params,
        base,
        {
            "track_a_revision": params.pe_us_revision,
            "capture_revision": captured.pe_us_revision,
            "capture_sha256": CAPTURE_SHA256,
            "capture_checks": checks,
            "tr2008_alternative": config.tr2008_alternative,
            "reference_year": config.reference_year,
        },
    )


def not_compared(convention: ComputationYears) -> list[str]:
    """What the run does not compare, for the chosen oracle."""

    items = [
        "PIA for anyone but the 1964 birth cohort, and Track A's own PIA "
        "for anyone: the 415(a) candidate covers only 2026 first "
        "eligibility, with 2026 bend points derived from SSA's "
        "published 2024 AWI rather than Track A's TR2008 AWI",
        "Track A's DI levels and pre-eligibility-death levels (the "
        "disclosed oracle approximation, approximate_pia): the bridge "
        "supports ordinary old-age entitlement without disability only",
        "COLA increases, early or delayed claiming adjustments, spouse "
        "and survivor benefits, and every Track A benefit path",
        "members born before 1917 or after 1968 (see selection "
        "exclusions) and the 2009-wave R6 population",
        "the five-group COLA age profile: not computed; of the Track "
        "A artifact the script uses only the parameter revision and the "
        "2011-wave cohort diagnostics and source provenance",
    ]
    if ComputationYears(convention) is not TRACK_A_COMPUTATION_YEARS:
        items.append(
            "Track A's own AIME against the engine: the oracle compared "
            f"is {ComputationYears(convention).value}, while Track A "
            "(cola_track_a.benefits.TRACK_A_COMPUTATION_YEARS) uses "
            f"{TRACK_A_COMPUTATION_YEARS.value}; Track A's AIME is "
            "recorded per person as track_a_oracle_aime, and "
            "--oracle-computation-years legacy_fixed_35 compares it"
        )
    return items


def _write_execution(directory: Path, stem: str, result) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stem}.request.json").write_bytes(result.prepared.wire)
    (directory / f"{stem}.stdout.json").write_bytes(result.stdout)


def _truncation_summary(records: Sequence[Mapping[str, Any]]) -> dict:
    dropped = [r for r in records if "career_years_not_sent" in r]
    effects = sorted(
        r["truncation_effect_on_oracle"]
        for r in records
        if "truncation_effect_on_oracle" in r
    )
    changed = [e for e in effects if e != 0]
    return {
        "persons": len(records),
        "persons_with_career_years_dropped": len(dropped),
        "persons_with_nonzero_years_dropped": sum(
            r.get("career_years_not_sent_nonzero", 0) > 0 for r in dropped
        ),
        "changed": len(changed),
        "min": min(changed) if changed else None,
        "median": changed[len(changed) // 2] if changed else None,
        "max": max(changed) if changed else None,
    }


def _pia_summary(
    records: Sequence[Mapping[str, Any]], params, base
) -> dict[str, Any]:
    with_pia = [r for r in records if "axiom_ordinary_pia_before_cola" in r]
    diffs = Counter(r["pia_formula_difference"] for r in with_pia)
    return {
        "persons": len(with_pia),
        "agree": sum(
            Decimal(r["pia_formula_difference"]) == 0 for r in with_pia
        ),
        "difference_counts": dict(sorted(diffs.items())),
        "published_bend_points_2026": "/".join(
            _float_text(v) for v in base.bend_points(2026)
        ),
        "track_a_bend_points_2026": "/".join(
            _float_text(v) for v in params.bend_points(2026)
        ),
        "check_params_revision": base.pe_us_revision,
    }


def build_parser() -> argparse.ArgumentParser:
    """The command line."""

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="evidence directory for a run (required unless --render-only)",
    )
    parser.add_argument("--anchor-wave", type=int, default=2011)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--render-only", type=Path, default=None)
    parser.add_argument("--examples-per-class", type=int, default=3)
    parser.add_argument("--max-unexplained-executions", type=int, default=500)
    parser.add_argument(
        "--oracle-computation-years",
        choices=tuple(ORACLE_CHOICES),
        default=DEFAULT_ORACLE,
        help=(
            "the oracle's benefit computation years: 'statutory' (42 USC "
            "415(b)(2), ss.statutory_aime; the default) or "
            "'legacy_fixed_35' (Track A's ss.benefits.aime, the oracle of "
            "the 2026-09-23 report)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.render_only is not None:
        result = json.loads((args.render_only / "result.json").read_text())
        (args.render_only / "RESULTS.md").write_text(render_results(result))
        print(args.render_only / "RESULTS.md")
        return 0

    if args.output_dir is None:
        raise SystemExit(
            "--output-dir is required for a run: name a new evidence "
            "directory (the script never overwrites a result.json)"
        )
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    head = _git("rev-parse", "HEAD")
    dirty = _git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is not clean; commit first (or pass "
            "--allow-dirty for a development run)"
        )
    output = args.output_dir.expanduser()
    if (output / "result.json").exists():
        raise SystemExit(f"{output / 'result.json'} exists; not overwriting")
    require_track_a_convention()
    convention = oracle_convention(args.oracle_computation_years)
    print(f"oracle: {ORACLE_NAMES[convention]}", file=sys.stderr)
    binding = bridge.reviewed_case_a_binding()
    binding.verify()
    params, base, parameter_info = _parameters()
    reference_year = parameter_info["reference_year"]
    cohort, provenance, cohort_info = _load_cohort(
        args.anchor_wave, reference_year
    )
    cohort_info["track_a_artifact"] = require_track_a_artifact(
        (ROOT / TRACK_A_ARTIFACT).read_bytes(),
        path=TRACK_A_ARTIFACT,
        anchor_wave=args.anchor_wave,
        diagnostics=cohort.diagnostics,
        source_provenance=cohort.source_provenance,
        parameters_revision=params.pe_us_revision,
    )
    cutoff = cohort.start_year
    persons = cohort.persons
    selections = select_persons(
        zip(
            persons["person_id"],
            persons["birth_year"],
            persons["opening_status"].astype(str),
            strict=True,
        ),
        reference_year=reference_year,
    )
    selected = [s for s in selections if s.selected]
    if args.limit is not None:
        selected = selected[: args.limit]
    opening_entitlement = {
        int(pid): int(record.entitlement_year)
        for pid, record in cohort.opening.items()
        if record.status == "retired_worker"
    }
    inputs = [
        PersonInput(
            s,
            cohort.careers[s.person_id],
            provenance[s.person_id],
            opening_entitlement.get(s.person_id),
        )
        for s in selected
    ]
    # The oracle PIAs rest on exactly these AIMEs (eligibility_pia_for_clock
    # under the chosen convention and under Track A's).
    pia_consistency = check_oracle_pia(inputs, params, convention)
    wage_index = track_a_wage_index(params)
    base_series = track_a_contribution_base(
        params, bridge.FIRST_COMPUTATION_BASE_YEAR, cutoff
    )
    executions = output / "executions"
    examples: Counter = Counter()
    engine_versions: set[str] = set()
    lock = threading.Lock()

    def keep(pass_name: str):
        def on_result(record, result):
            if result is None:
                return
            with lock:
                engine_versions.add(result.engine_version)
                key = (pass_name, record["attribution"])
                limit = (
                    args.max_unexplained_executions
                    if record["attribution"] == ATTR_UNEXPLAINED
                    else args.examples_per_class
                )
                wanted = examples[key] < limit
                if wanted:
                    examples[key] += 1
                    record["execution_files"] = (
                        f"executions/{pass_name}-{record['person_id']}"
                        ".{request,stdout}.json"
                    )
            if wanted:
                _write_execution(
                    executions,
                    f"{pass_name}-{record['person_id']}",
                    result,
                )

        return on_result

    output.mkdir(parents=True, exist_ok=True)
    contexts = {
        name: PassContext(
            name=name,
            params=params,
            wage_index=wage_index,
            contribution_base=base_series,
            binding=binding,
            cutoff_year=cutoff,
            anchor_wave=args.anchor_wave,
            oracle_convention=convention,
            pia_check_params=base,
        )
        for name in (PASS_PRIMARY, PASS_DIAGNOSTIC, PASS_STRICT)
    }
    passes: dict[str, Any] = {}
    for name in (PASS_STRICT, PASS_PRIMARY, PASS_DIAGNOSTIC):
        pass_inputs = (
            [p for p in inputs if p.opening_entitlement_year is not None]
            if name == PASS_DIAGNOSTIC
            else inputs
        )
        print(f"{name}: {len(pass_inputs)} persons", file=sys.stderr)
        records = run_pass(
            pass_inputs,
            contexts[name],
            workers=1 if name == PASS_STRICT else args.workers,
            on_result=keep(name),
        )
        passes[name] = {
            "persons": len(records),
            "summary": summarize_pass(records),
            "records": records,
        }
        if name == PASS_DIAGNOSTIC:
            passes[name]["truncation_effect"] = _truncation_summary(records)
    binding.verify()
    exclusions = Counter(s.exclusion for s in selections if not s.selected)
    result = {
        "schema_version": SCHEMA_VERSION,
        "header": header_for(convention),
        "labels": list(labels_for(convention)),
        "oracle": oracle_document(convention),
        "partial": args.limit is not None,
        "cohort": cohort_info,
        "selection": {
            "members": len(selections),
            "selected": len(selected),
            "eligibility_window": (
                f"{FIRST_ORACLE_ELIGIBILITY_YEAR}-{reference_year}"
            ),
            "exclusions": dict(sorted(exclusions.items())),
            "exclusion_definitions": dict(EXCLUSIONS),
            "routes": dict(sorted(Counter(s.route for s in selected).items())),
            "route_definitions": dict(ROUTES),
            "primary_routes": list(PRIMARY_ROUTES),
        },
        "declarations": {
            "covered earnings": COVERED_EARNINGS_DECLARATION,
            "binary64 encoding": (
                "career amounts sent as shortest_round_trip_binary64 "
                "(Python's shortest decimal that converts back to the same "
                "bits); every row records amount_hex and the encoding"
            ),
            "synthetic rows": (
                f"{PRE_PANEL_LABEL}; {POST_CUTOFF_LABEL}; career years the "
                "career law zero-filled (provenance unknown) or imputed "
                "(gap_imputed) are also labeled synthetic"
            ),
            "indexing year": (
                "birth year + 60 on both sides (the oracle's indexed_history "
                "and the bridge's OrdinaryRetirementDeterminations)"
            ),
            "entitlement year": (
                f"primary pass: max(birth year + 62, {cutoff + 1}); "
                "diagnostic pass: Track A's OpeningStockRecord."
                "entitlement_year for opening-stock retired workers"
            ),
            "wage index": wage_index.label,
            "scoped assumptions": (
                "the bridge's Case A assumptions: entitled to old-age "
                "benefits, never entitled to disability benefits, no period "
                "of disability"
            ),
        },
        "parameters": {
            **parameter_info,
            "wage_index": wage_index.document(),
            "contribution_base": base_series.document(),
        },
        "passes": passes,
        "executions": {
            "examples_per_class": args.examples_per_class,
            "max_unexplained_per_pass": args.max_unexplained_executions,
            "persons_written": sum(examples.values()),
            "written_by_pass_and_attribution": {
                f"{name}:{attribution}": count
                for (name, attribution), count in sorted(examples.items())
            },
        },
        "oracle_pia_consistency": pia_consistency,
        "pia_check": _pia_summary(
            passes[PASS_PRIMARY]["records"], params, base
        ),
        "not_compared": not_compared(convention),
        "provenance": {
            "engine_binding": binding.document(),
            "engine_versions": sorted(engine_versions),
            "git": {
                "head": head,
                "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
                "clean": not dirty,
            },
            "source_sha256": {
                path: _sha256_file(ROOT / path) for path in _SOURCES
            },
            "python": platform.python_version(),
            "platform": platform.platform(),
            "workers": args.workers,
            "started": started,
            "finished": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "command": " ".join(
                ["python", "scripts/track_c_aime_agreement.py"]
                + (sys.argv[1:] if argv is None else list(argv))
            ),
            "environment_threads": {
                key: os.environ.get(key)
                for key in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                )
            },
        },
    }
    (output / "result.json").write_text(
        json.dumps(result, indent=1, allow_nan=False) + "\n"
    )
    (output / "RESULTS.md").write_text(render_results(result))
    print(output / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
