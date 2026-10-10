"""Pinned 2026 Trustees Report intermediate baseline input accessors.

Data are transcribed from Tables V.C1, V.B1, VI.G1, V.A1 and V.A4 and
OACT DeathProbsE CSVs captured 2026-10-01. See
``data/external/tr2026/provenance.md`` for source URLs, locators, capture
SHA-256s, exact-byte reproduction and life-expectancy checks. Captured
HTML bytes are pinned, while live Akamai HTML hashes can change between
requests. Every JSON file read here is verified against FILE_SHA256.

Units: COLA and CPI-W growth are percentages (2.4 means 2.4%); AWI is
dollars; TFR is births per woman; ASADR is deaths per 100,000 standardized
to the April 1, 2010 population; q is a one-year probability at exact age.
Hist/Alt2 q is preserved, including q119 below one where OACT publishes it.

Builder default awaiting ratification: ``post_2035_cola_annual_cpiw`` uses
the V.B1 annual-average CPI-W growth as the COLA for determination years
2036-2100. This approximates the statutory Q3-to-Q3 adjustment and is tagged
``derived_annual_cpiw_cola``. No extension after 2100 is provided. Tables
otherwise have no inferred values, interpolation or silent fallback.

Value source classes distinguish historical, actual, estimated,
preliminary, provisional and projected rows. Path entries carry source classes;
:func:`value_provenance` adds the captured source hash, locator and units
for every scalar/path value and every sex-specific q vector.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache, lru_cache
from numbers import Integral
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

import numpy as np

__all__ = [
    "AwiEntry",
    "ColaEntry",
    "DATA_DIR",
    "FILE_SHA256",
    "PENDING_RULINGS",
    "ValueProvenance",
    "asadr",
    "awi",
    "cola_path",
    "cpiw_growth",
    "death_probability",
    "tfr",
    "value_provenance",
    "verify_files",
]

Sex = Literal["male", "female"]
AsadrGroup = Literal["total", "under_65", "65_and_over"]
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = _PROJECT_ROOT / "data" / "external" / "tr2026"
FILE_SHA256: Mapping[str, str] = MappingProxyType(
    {
        "tr2026_parameters.json": "15d890db61dc8cdcb4a22cc0427e091ee062d85f7265902d74362bd51c7525d8",
        "tr2026_death_probabilities.json": "f711c087bcf907a91b78b076a7fc340ffb931cc26453ace7965512152aeca424",
        "transcription_check.json": "5942720fc9ac7a633680279a2a3de0a4e973f1a9e0952cac2482c485eae245bb",
        "sources.json": "8f618f5deda22f65fdf0be010101af6170af86b965b6d531bb2366bf891295d3",
    }
)
PENDING_RULINGS = MappingProxyType(
    {
        "post_2035_cola_annual_cpiw": (
            "Use V.B1 annual-average CPI-W growth for COLA in 2036-2100; "
            "builder default awaiting ratification"
        ),
    }
)


@dataclass(frozen=True)
class ColaEntry:
    """Automatic benefit increase in percent, by determination year."""

    determination_year: int
    percent: float
    source: str
    effective_month: Literal["June", "December"]


@dataclass(frozen=True)
class AwiEntry:
    """One published national average wage index in dollars."""

    year: int
    amount: float
    source: str


@dataclass(frozen=True)
class ValueProvenance:
    """Source identity for one year's value or single-sex q vector."""

    series: str
    year: int
    source: str
    source_file: str
    source_sha256: str
    locator: str
    unit: str
    derived_rule: str | None = None


def _year(year: int) -> int:
    if isinstance(year, bool) or not isinstance(year, Integral):
        raise ValueError("year must be an integer (not bool or float)")
    return int(year)


def _range(first: int, last: int) -> range:
    first, last = _year(first), _year(last)
    if first > last:
        raise ValueError("first must not exceed last")
    return range(first, last + 1)


def _sex(sex: str) -> Sex:
    if sex not in ("male", "female"):
        raise ValueError("sex must be 'male' or 'female'")
    return sex


def verify_files(data_dir: Path = DATA_DIR) -> None:
    """Verify every consumed artifact against its hard-coded SHA-256."""
    for name, expected in FILE_SHA256.items():
        observed = hashlib.sha256((data_dir / name).read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(
                f"{name} sha256 {observed} != pinned {expected}; rebuild and re-pin"
            )


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    verify_files(DATA_DIR)
    return {
        name: json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
        for name in FILE_SHA256
    }


@cache
def _table(table: str) -> dict[int, dict[str, Any]]:
    table_data = _data()["tr2026_parameters.json"]["tables"][table]
    return {
        int(row[0]): dict(zip(table_data["columns"], row, strict=True))
        for row in table_data["rows"]
    }


def _row(table: str, year: int) -> dict[str, Any]:
    year = _year(year)
    try:
        return _table(table)[year]
    except KeyError:
        raise KeyError(f"TR2026 {table} has no coverage for {year}") from None


def _row_source(table: str, year: int, column: str | None = None) -> str:
    _row(table, year)
    stem = "tr2026_" + table.lower().replace(".", "_")
    if table == "V.C1":
        standing = (
            "historical"
            if year <= 2024
            else "actual" if year == 2025 else "projected"
        )
    elif table == "VI.G1":
        standing = (
            "historical"
            if year <= 2024
            else "estimated" if year == 2025 else "projected"
        )
    elif table == "V.B1":
        standing = (
            "historical"
            if year <= 2024
            else "estimated" if year == 2025 else "projected"
        )
    else:
        table_data = _data()["tr2026_parameters.json"]["tables"][table]
        footnote = table_data["cell_footnotes"].get(str(year), {}).get(column)
        standing = (
            "preliminary"
            if footnote in ("d", "e")
            else (
                "provisional"
                if footnote == "f"
                else "historical" if year <= 2025 else "projected"
            )
        )
    return f"{stem}_{standing}"


def cola_path(first: int, last: int) -> tuple[ColaEntry, ...]:
    """COLA percent for determination years 1975-2100, inclusive.

    V.C1 through 2035; the named builder default uses annual-average CPI-W
    growth thereafter. June is effective in 1975-82, December thereafter
    (first paid January of the next year), following V.C1 footnote a.
    """
    out = []
    for year in _range(first, last):
        if year <= 2035:
            row = _row("V.C1", year)
            percent = float(row["cola_percent"])
            source = _row_source("V.C1", year)
        else:
            percent = cpiw_growth(year)
            source = "derived_annual_cpiw_cola"
        out.append(
            ColaEntry(
                year, percent, source, "June" if year <= 1982 else "December"
            )
        )
    return tuple(out)


def cpiw_growth(year: int) -> float:
    """Annual-average CPI-W growth in percent, 1960-2100 (V.B1)."""
    return float(_row("V.B1", year)["cpiw_growth_percent"])


def awi(first: int, last: int) -> tuple[AwiEntry, ...]:
    """Published VI.G1 AWI in dollars for 1970-2100, inclusive."""
    return tuple(
        AwiEntry(
            year, float(_row("VI.G1", year)["awi"]), _row_source("VI.G1", year)
        )
        for year in _range(first, last)
    )


def death_probability(year: int, sex: Sex) -> np.ndarray:
    """Published exact-age q for ages 0-119, 1900-2100; immutable array.

    Historical rows end in 2023; Alt2 starts in 2024. Terminal q is kept
    exactly as published. Sex must be the literal 'male' or 'female'.
    """
    year, sex = _year(year), _sex(sex)
    try:
        q = _data()["tr2026_death_probabilities.json"]["sexes"][sex]["q"][
            str(year)
        ]
    except KeyError:
        raise KeyError(
            f"TR2026 death probability has no coverage for {year}"
        ) from None
    # Bytes backing prevents callers from re-enabling write access.
    return np.frombuffer(
        np.array(q, dtype=np.float64).tobytes(), dtype=np.float64
    )


def tfr(year: int) -> float:
    """Period total fertility rate in births per woman, 1940-2100."""
    return float(_row("V.A1", year)["tfr"])


def asadr(year: int, group: AsadrGroup) -> float:
    """V.A1 deaths per 100,000, April 1 2010 standardized population.

    Group is 'total', 'under_65' or '65_and_over'; coverage is 1940-2100.
    """
    if group not in ("total", "under_65", "65_and_over"):
        raise ValueError("group must be 'total', 'under_65' or '65_and_over'")
    return float(_row("V.A1", year)[group])


def value_provenance(
    series: Literal[
        "cola", "cpiw_growth", "awi", "death_probability", "tfr", "asadr"
    ],
    year: int,
    *,
    sex: Sex | None = None,
    group: AsadrGroup | None = None,
) -> ValueProvenance:
    """Captured hash, source class, units and locator for every value.

    ``sex`` is required only for death_probability and ``group`` only for
    asadr; unused qualifiers are refused to catch mistaken selections.
    """
    year = _year(year)
    if series != "death_probability" and sex is not None:
        raise ValueError("sex applies only to death_probability provenance")
    if series != "asadr" and group is not None:
        raise ValueError("group applies only to asadr provenance")
    derived_rule = None
    if series == "death_probability":
        if sex is None:
            raise ValueError("death_probability provenance needs sex")
        death_probability(year, sex)
        code = "M" if sex == "male" else "F"
        variant = "Hist" if year <= 2023 else "Alt2"
        filename = f"DeathProbsE_{code}_{variant}_TR2026.csv"
        source = (
            f"tr2026_death_probs_{'historical' if year <= 2023 else 'alt2'}"
        )
        unit = "one-year probability at exact age"
    else:
        if series == "cola":
            entry = cola_path(year, year)[0]
            table = "V.C1" if year <= 2035 else "V.B1"
            source, unit = entry.source, "percent"
            if year > 2035:
                derived_rule = "post_2035_cola_annual_cpiw"
        elif series == "cpiw_growth":
            cpiw_growth(year)
            table, unit = "V.B1", "percent"
            source = _row_source(table, year)
        elif series == "awi":
            source = awi(year, year)[0].source
            table, unit = "VI.G1", "dollars"
        elif series == "tfr":
            tfr(year)
            table, unit = "V.A1", "births per woman"
            source = _row_source(table, year, "tfr")
        elif series == "asadr":
            if group is None:
                raise ValueError("asadr provenance needs group")
            asadr(year, group)
            table, unit = (
                "V.A1",
                "deaths per 100000; April 1 2010 standard population",
            )
            source = _row_source(table, year, group)
        else:
            raise ValueError(f"unknown series {series!r}")
        filename = _data()["tr2026_parameters.json"]["tables"][table][
            "source_file"
        ]
    record = _data()["sources.json"]["sources"][filename]
    locator = f"{record['locator']}; year {year}"
    if sex:
        locator += f"; sex {sex}; ages 0-119"
    if group:
        locator += f"; group {group}"
    return ValueProvenance(
        series,
        year,
        source,
        filename,
        record["sha256"],
        locator,
        unit,
        derived_rule,
    )
