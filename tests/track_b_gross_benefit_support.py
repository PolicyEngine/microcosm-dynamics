"""Shared fixtures for the Track B milestone G tests (not a test module).

The parameter bundle here uses SSA's *published* national average wage
index (the R1 historical-source capture, ``ret_history.json``), not the
policyengine-us series, so the unit tier needs no checkout. The statutory
rates are the repository defaults; the 402(w) delayed-credit schedule is
the statute's, which POMS RS 00615.692D tabulates.
"""

from __future__ import annotations

import html
import json
import re
from functools import cache
from pathlib import Path

from populace_dynamics.ss.params import SSAParameters

TRACK_B_DATA = Path(__file__).with_name("data") / "track_b"
SOURCES = TRACK_B_DATA / "gross_benefit_sources"

#: 42 U.S.C. 402(w)(6): annual delayed-credit rate by birth year.
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
        fra_months_by_birth_year=[(1900, 780), (1943, 792), (1960, 804)],
        early_monthly_rates=(0.00555556, 0.00416667),
        early_first_bracket_months=36,
        pe_us_revision="ssa-published-nawi-test-bundle",
        delayed_credit_by_birth_year=list(DELAYED_CREDIT_SCHEDULE),
        max_delayed_months=48,
    )
    values.update(overrides)
    return SSAParameters(**values)


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
