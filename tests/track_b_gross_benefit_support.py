"""Shared fixtures for the Track B milestone G tests (not a test module).

The parameter bundle here uses SSA's *published* national average wage
index (the R1 historical-source capture, ``ret_history.json``), not the
policyengine-us series, so the unit tier needs no checkout. The statutory
rates are the repository defaults. The full-retirement-age and 402(w)
delayed-credit schedules are the ones POMS RS 00615.692D-E tabulates for
births from 1917 (a test reads them from the capture), and both match
policyengine-us (``test_track_b_gross_benefits_oracle.py``). For births
before 1917 the bundle, like policyengine-us, gives 3 percent a year where
402(w)(6)(A) gives 1/12 of 1 percent a month, which is why G refuses
those credits.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import fields
from fractions import Fraction as F
from functools import cache
from pathlib import Path

from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.track_b import gross_benefits as g

TRACK_B_DATA = Path(__file__).with_name("data") / "track_b"
SOURCES = TRACK_B_DATA / "gross_benefit_sources"

#: Full retirement age in months by birth year (416(l); POMS RS
#: 00615.692E). SSA's bands run from January 2, so a January 1 birth
#: belongs to the previous year's row.
FULL_RETIREMENT_AGE_SCHEDULE = [
    (1900, 780),
    (1938, 782),
    (1939, 784),
    (1940, 786),
    (1941, 788),
    (1942, 790),
    (1943, 792),
    (1955, 794),
    (1956, 796),
    (1957, 798),
    (1958, 800),
    (1959, 802),
    (1960, 804),
]

#: 42 U.S.C. 402(w)(6): annual delayed-credit rate by birth year (from
#: 1917; the 1900 bracket is policyengine-us's, wrong before 1917).
DELAYED_CREDIT_SCHEDULE = [
    (1900, 0.03),
    (1925, 0.035),
    (1927, 0.04),
    (1929, 0.045),
    (1931, 0.05),
    (1933, 0.055),
    (1935, 0.06),
    (1937, 0.065),
    (1939, 0.07),
    (1941, 0.075),
    (1943, 0.08),
]


@cache
def published_nawi() -> dict[int, float]:
    """SSA's published NAWI, 1951-2024, from the R1 source capture."""
    history = json.loads((TRACK_B_DATA / "ret_history.json").read_text())
    return {int(year): float(value) for year, value in history["nawi"].items()}


def ssa_params(**overrides) -> SSAParameters:
    """A bundle whose NAWI is SSA's published series (no checkout needed).

    ``early_monthly_rates`` keep policyengine-us's stored decimals so the
    module's cross-check and fraction substitution are exercised.
    """
    values = dict(
        nawi=published_nawi(),
        wage_base={},
        pia_factors=(0.90, 0.32, 0.15),
        fra_months_by_birth_year=list(FULL_RETIREMENT_AGE_SCHEDULE),
        early_monthly_rates=(0.00555556, 0.00416667),
        early_first_bracket_months=36,
        pe_us_revision="ssa-published-nawi-test-bundle",
        delayed_credit_by_birth_year=list(DELAYED_CREDIT_SCHEDULE),
        max_delayed_months=48,
    )
    values.update(overrides)
    return SSAParameters(**values)


def result_fields(result, **overrides):
    """Compare every public result field without constructing another result."""
    return {
        **{item.name: getattr(result, item.name) for item in fields(result)},
        **overrides,
    }


def computed_refusal(reason):
    """Produce a refusal through G's computation on an invented family."""
    month = g.YearMonth(2023, 12)
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(0),
        F(0),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(0)),
        conditions=(
            {g.RecordCondition.ADMINISTRATIVE_FINALITY}
            if reason is g.UnsupportedReason.ADMINISTRATIVE_FINALITY
            else set()
        ),
    )
    members = (
        g.Beneficiary(
            "spouse",
            g.Role.SPOUSE,
            conditions={g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET},
        ),
    )
    if reason is g.UnsupportedReason.SAVINGS_CLAUSE:
        guard = g.SavingsClauseGuard(
            month,
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        )
        members = tuple(
            g.Beneficiary(f"child-{index}", g.Role.CHILD) for index in range(3)
        )
        state = g.RecordState(
            g.FamilyKind.SURVIVOR,
            F(1000),
            F(1500),
            widow_drc_savings_clause=False,
        )
        guard.admit(
            g.family_benefits(
                state,
                members,
                payment_month=month,
                params=ssa_params(),
                standalone=True,
            )
        )
        state = g.RecordState(
            g.FamilyKind.SURVIVOR,
            F("1000.1"),
            F("1500.1"),
            widow_drc_savings_clause=False,
        )
        month = g.YearMonth(2024, 1)
        members = members[:1]
        evaluate = guard.evaluate
    else:
        assert reason in {
            g.UnsupportedReason.ADMINISTRATIVE_FINALITY,
            g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET,
        }
        evaluate = g.evaluate_family
    outcome = evaluate(
        "invented-refusal",
        F(1),
        lambda: g.family_benefits(
            state,
            members,
            payment_month=month,
            params=ssa_params(),
            standalone=True,
        ),
    )
    assert outcome.unsupported.reason is reason
    return outcome.unsupported


@cache
def manifest() -> dict:
    return json.loads((SOURCES / "manifest.json").read_text())


@cache
def source_text(source_id: str) -> str:
    """Whitespace-normalized text of a captured source, by manifest id."""
    entry = next(s for s in manifest()["sources"] if s["id"] == source_id)
    raw = (SOURCES / entry["file"]).read_bytes().decode("utf-8")
    if entry["file"].endswith(".html"):
        raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = html.unescape(raw)
    for char in ("​", "\xa0"):
        raw = raw.replace(char, " ")
    raw = raw.replace("’", "'")
    return re.sub(r"\s+", " ", raw)


@cache
def poms_bend_point_table() -> dict[int, tuple[int, ...]]:
    """RS 00605.900: per year, the two PIA and three maximum bend points."""
    text = source_text("poms_rs_00605_900")
    rows = re.findall(
        r"\b((?:19|20)\d\d) ([\d,]+) and ([\d,]+) ([\d,]+), ([\d,]+) and ?"
        r"([\d,]+)\b",
        text,
    )
    return {
        int(year): tuple(int(v.replace(",", "")) for v in values)
        for year, *values in rows
    }


@cache
def poms_delayed_credit_chart(
    through_birth_year: int = 1960,
) -> dict[int, tuple[int, F, int, F]]:
    """RS 00615.692E's January 2 birth-year bands, through the given year.

    Each value is (FRA in months, monthly credit, maximum months, maximum
    credit in percent). A January 1 birth belongs to the previous year's
    row. ``through_birth_year`` expands the chart's open-ended 1960+ row;
    the default preserves G's original 1914-1960 source cross-check.
    """
    text = source_text("poms_rs_00615_692")
    chart = text[
        text.index("E. Chart for Maximum Delayed") : text.index(
            "To Link to this section"
        )
    ]
    rows = re.findall(
        r"(?:After 01/01/(60)|01/02/(\d\d) thru 01/01/(\d\d)) "
        r"(\d\d)(?:&(\d+))? (\d+/\d+)% [\d.]+% (\d+) ([\d.]+)%",
        chart,
    )
    cohorts = {}
    for after, start, end, years, months, monthly, most, percent in rows:
        first = 1900 + int(after or start)
        last = through_birth_year if after else 1900 + int(end) - 1
        for year in range(first, last + 1):
            cohorts[year] = (
                12 * int(years) + int(months or 0),
                F(monthly) / 100,
                int(most),
                F(percent),
            )
    return cohorts


@cache
def poms_delayed_credit_rates(
    through_birth_year: int = 1962,
) -> dict[int, tuple[F, F]]:
    """RS 00615.692D's exact (monthly, annual) rates by birth year.

    January 1 belongs to the preceding birth-year band. The chart's
    before-1917 row is expanded only from 1900, matching the test bundle.
    """
    text = source_text("poms_rs_00615_692")
    chart = text[
        text.index("D. Chart for Delayed") : text.index(
            "E. Chart for Maximum Delayed"
        )
    ]
    rows = re.findall(
        r"(?:After 01/01/(43)|Before 01/02/(17)|"
        r"01/02/(\d\d) thru 01/01/(\d\d)) "
        r"(\d+/\d+)% [\d.]+ ([\d.]+)%",
        chart,
    )
    cohorts = {}
    for after, before, start, end, monthly, annual in rows:
        first = 1900 if before else 1900 + int(after or start)
        last = (
            1916
            if before
            else through_birth_year if after else 1900 + int(end) - 1
        )
        for year in range(first, last + 1):
            cohorts[year] = (F(monthly) / 100, F(annual) / 100)
    return cohorts
