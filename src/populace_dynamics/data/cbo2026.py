"""Typed, SHA-pinned CBO2026 baseline input accessors.

Sources: CBO January 2026 demographic projections (57059/61879), February
2026 ten-year and long-term economics (51135/57054), and September 2026
covered workers/earnings (62556 Additional-Info sheets 1-2). The captured
bytes, Wayback IDs, CDX checks and locators are recorded in
``data/external/cbo2026/``. Rates are annual percentages unless an accessor
explicitly returns probabilities or births per woman. Demographic inputs
cover 2021-2099; there is no demographic extension after 2099.

Mortality ``deaths_per_1000_people / 1000`` is interpreted as q(x). This
is an inference tested against every published 2026-2099 life expectancy
at birth and 65: arithmetic mean of male/female period life expectancy,
uniform deaths within each age including infancy, reproduces CBO sheet 1
within 0.0011 year; central-m conversion does not. Age 119 is closed with
q=1 in every source row. See ``transcription_check.json`` for both checks.

Builder defaults awaiting ratification
-------------------------------------
``ten_year_cpiu_then_long_term_growth``: use ten-year CPI-U levels in
2023-2036; growth is their year-on-year ratio (2023 uses the 2022 LT
level). After 2036, compound the LT published annual growth on the last
ten-year level, avoiding a level jump between workbook vintages.
``hold_2056_economic_growth``: after 2056 hold each final LT economic
growth rate, through 2100; no new demographic rates are invented.
``cpiw_equals_cpiu_growth`` and ``cola_equals_annual_cpiu_growth``: CBO
publishes neither CPI-W nor COLA. Their annual growth proxy uses the
spliced CPI-U growth, not a statutory Q3-to-Q3 COLA calculation. The COLA
proxy is exposed only in 2024-2100, where that proxy is nonnegative.
``awi_bridge_2025_2026_real_earnings_times_cpiu``: start from the last
actual AWI (2024, TR2026 VI.G1); use compounded real earnings per worker
growth and CPI-U growth for 2025 and 2026, because covered earnings and
workers begin in 2026 and supply no earlier growth ratio.
``awi_growth_of_covered_earnings_per_worker``: from 2027 compound growth
in covered earnings/covered workers on that 2026 bridge. This is an AWI
analog, not a CBO-published AWI. The covered-input source runs to 2100,
so AWI needs no post-2056 economic extrapolation.
``tfr_sum_asfr_before_2026``: in 2021-2025, where sheet 1 publishes no
TFR, sum the all-women ASFRs. From 2026 use the printed summary TFR;
the ASFR sum matches within rounding (0.0023 births per woman).

Every scalar has a corresponding :func:`value_provenance` record. Path
entries also carry provenance-class tags directly. No fallback outside
these stated coverages is allowed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from numbers import Integral
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

import numpy as np

Sex = Literal["male", "female"]
Place = Literal["all", "native-born", "foreign-born"]

DATA_DIR = (
    Path(__file__).resolve().parents[3] / "data" / "external" / "cbo2026"
)
FILE_SHA256: Mapping[str, str] = MappingProxyType(
    {
        "cbo2026_demographics.json": "2d09b326bc1ac460ac038e4da3a8a37a12929b50173fa5cd6117bd9c904173fc",
        "cbo2026_economics.json": "314d5d10753ddb9c6aa124ec0ddbd3ed55ad9e5b0bd625138283dcc73927a43f",
        "transcription_check.json": "324dc88e305d48987846814c1594e0dd3a01d68ecac36b83ddcd62adf943f34e",
        "sources.json": "a00644af2aaa87fe4fbdd3fe72e5dd5b4ba7d0d76f6a74423094933552a6ded7",
    }
)
PLACES: tuple[Place, ...] = ("all", "native-born", "foreign-born")
SEXES: tuple[Sex, ...] = ("male", "female")
PENDING_RATIFICATION: tuple[str, ...] = (
    "ten_year_cpiu_then_long_term_growth",
    "hold_2056_economic_growth",
    "cpiw_equals_cpiu_growth",
    "cola_equals_annual_cpiu_growth",
    "awi_bridge_2025_2026_real_earnings_times_cpiu",
    "awi_growth_of_covered_earnings_per_worker",
    "tfr_sum_asfr_before_2026",
)


@dataclass(frozen=True)
class ColaEntry:
    """One derived CBO annual inflation proxy for a benefit increase."""

    determination_year: int
    percent: float
    source: str
    effective_month: Literal["December"] = "December"


@dataclass(frozen=True)
class AwiEntry:
    """Actual 2024 AWI or one CBO-derived AWI analog amount."""

    year: int
    amount: float
    source: str


@dataclass(frozen=True)
class ValueProvenance:
    """Source identities and named derivations for one returned value."""

    source: str
    source_keys: tuple[str, ...]
    locators: tuple[str, ...]
    sha256: tuple[str, ...]
    builder_defaults: tuple[str, ...] = ()


__all__ = [
    "AwiEntry",
    "ColaEntry",
    "DATA_DIR",
    "FILE_SHA256",
    "PENDING_RATIFICATION",
    "PLACES",
    "SEXES",
    "ValueProvenance",
    "asfr",
    "awi",
    "cola_path",
    "cpiu_growth",
    "cpiu_index",
    "cpiw_growth",
    "mortality",
    "real_earnings_growth",
    "tfr",
    "value_provenance",
    "verify_files",
]


def verify_files(data_dir: Path = DATA_DIR) -> None:
    """Refuse any changed input, check record or source identity bytes."""
    if not FILE_SHA256:
        raise ValueError("CBO2026 file pins have not been populated")
    for name, expected in FILE_SHA256.items():
        actual = hashlib.sha256((data_dir / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"{name} SHA-256 {actual} != pinned {expected}")


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    payloads = {}
    for name, expected in FILE_SHA256.items():
        raw = (DATA_DIR / name).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise ValueError(f"{name} SHA-256 {actual} != pinned {expected}")
        # Parse the same bytes whose identity was checked.
        payloads[name] = json.loads(raw)
    return payloads


def _demographics() -> dict[str, Any]:
    return _data()["cbo2026_demographics.json"]


def _economics() -> dict[str, Any]:
    return _data()["cbo2026_economics.json"]


def _year(year: int, first: int, last: int) -> int:
    if isinstance(year, bool) or not isinstance(year, Integral):
        raise ValueError("year must be an integer")
    result = int(year)
    if not first <= result <= last:
        raise ValueError(f"year {result} outside coverage {first}..{last}")
    return result


def _interval(first: int, last: int, start: int, stop: int) -> range:
    first = _year(first, start, stop)
    last = _year(last, start, stop)
    if first > last:
        raise ValueError("first year must not exceed last year")
    return range(first, last + 1)


def _sex(sex: str) -> None:
    if sex not in SEXES:
        raise ValueError(f"sex must be one of {SEXES}, got {sex!r}")


def _place(place: str) -> None:
    if place not in PLACES:
        raise ValueError(f"place must be one of {PLACES}, got {place!r}")


def asfr(year: int, place: Place = "all") -> dict[int, float]:
    """Single-year age 14-49 births per woman, not a birth probability.

    Values may exceed one birth per woman in principle; no clipping or
    conversion to a Bernoulli probability is part of this data accessor.
    """
    year = _year(year, 2021, 2099)
    _place(place)
    rates = _demographics()["asfr"][str(year)][place]
    return {age: float(value) / 1000.0 for age, value in enumerate(rates, 14)}


def mortality(year: int, sex: Sex) -> np.ndarray:
    """One-year q(x) for ages 0..119, as a fresh read-only float array."""
    year = _year(year, 2021, 2099)
    _sex(sex)
    q = np.array(_demographics()["mortality"][str(year)][sex], dtype=float)
    q /= 1000.0
    q.setflags(write=False)
    return q


def tfr(year: int) -> float:
    """Published 2026-2099 TFR; derived sum of ASFR for 2021-2025."""
    year = _year(year, 2021, 2099)
    if year < 2026:
        return sum(asfr(year).values())
    return float(_demographics()["published_summary"][str(year)]["tfr"])


def cpiu_growth(year: int) -> float:
    """Annual CPI-U growth in percent, with named splice/extension rules."""
    year = _year(year, 1996, 2100)
    econ = _economics()
    if 2023 <= year <= 2036:
        current = econ["ten_year_cpiu_index_1982_1984_100"][str(year)]
        previous = (
            econ["ten_year_cpiu_index_1982_1984_100"][str(year - 1)]
            if year > 2023
            else econ["long_term"]["2022"]["cpiu_index_1982_1984_100"]
        )
        return 100.0 * (current / previous - 1.0)
    source_year = min(year, 2056)
    return float(econ["long_term"][str(source_year)]["cpiu_growth_percent"])


def cpiu_index(year: int) -> float:
    """Spliced CPI-U level (1982-84=100), continuous at 2036 and 2056."""
    year = _year(year, 1996, 2100)
    econ = _economics()
    if year < 2023:
        return float(econ["long_term"][str(year)]["cpiu_index_1982_1984_100"])
    if year <= 2036:
        return float(econ["ten_year_cpiu_index_1982_1984_100"][str(year)])
    level = float(econ["ten_year_cpiu_index_1982_1984_100"]["2036"])
    for current in range(2037, year + 1):
        level *= 1.0 + cpiu_growth(current) / 100.0
    return level


def cpiw_growth(year: int) -> float:
    """CPI-U annual growth proxy for CPI-W; a builder default."""
    return cpiu_growth(year)


def real_earnings_growth(year: int) -> float:
    """Published LT real earnings per worker growth; hold 2056 thereafter."""
    year = _year(year, 1996, 2100)
    return float(
        _economics()["long_term"][str(min(year, 2056))][
            "real_earnings_growth_percent"
        ]
    )


def cola_path(first: int, last: int) -> tuple[ColaEntry, ...]:
    """Annual CPI-U proxy for December COLA, determination years 2024-2100."""
    years = _interval(first, last, 2024, 2100)
    return tuple(
        ColaEntry(
            determination_year=year,
            percent=cpiu_growth(year),
            source=value_provenance("cola", year).source,
        )
        for year in years
    )


def _covered_average(year: int) -> float:
    row = _economics()["covered"][str(year)]
    return 1_000_000_000.0 * (
        row["covered_earnings_trillions"] / row["total_workers_thousands"]
    )


def awi(first: int, last: int) -> tuple[AwiEntry, ...]:
    """2024 actual AWI and 2025-2100 CBO AWI analog, inclusive interval.

    Growth in covered earnings per worker is applied only after 2026;
    the explicit 2025-2026 bridge supplies the missing growth ratios.
    """
    years = _interval(first, last, 2024, 2100)
    amount = float(_economics()["awi_anchor"]["amount"])
    out = []
    for year in range(2024, years.stop):
        if year in (2025, 2026):
            amount *= (1.0 + real_earnings_growth(year) / 100.0) * (
                1.0 + cpiu_growth(year) / 100.0
            )
        elif year >= 2027:
            amount *= _covered_average(year) / _covered_average(year - 1)
        if year in years:
            out.append(
                AwiEntry(year, amount, value_provenance("awi", year).source)
            )
    return tuple(out)


def value_provenance(
    series: str,
    year: int,
    *,
    sex: Sex | None = None,
    place: Place = "all",
) -> ValueProvenance:
    """Frozen metadata for the named public series/year and group.

    Accepted names: asfr,mortality,tfr,cpiu_growth,cpiu_index,cpiw_growth,
    real_earnings_growth,cola,awi. Source tags distinguish all derivations.
    The complete source identities remain available through sources.json.
    """
    if sex is not None and series != "mortality":
        raise ValueError("sex qualifier is supported only for mortality")
    if place != "all" and series != "asfr":
        raise ValueError("place qualifier is supported only for asfr")
    defaults: tuple[str, ...] = ()
    keys: tuple[str, ...]
    if series in ("asfr", "mortality", "tfr"):
        year = _year(year, 2021, 2099)
        if series == "asfr":
            _place(place)
            keys = ("fertility",)
            source = f"cbo2026_asfr_{place}"
        elif series == "mortality":
            if sex is None:
                raise ValueError("mortality provenance needs sex")
            _sex(sex)
            keys = ("mortality", "demographic_workbook")
            source = "cbo2026_mortality_q_verified"
        elif year < 2026:
            keys = ("fertility",)
            source = "derived_cbo2026_tfr_asfr_sum"
            defaults = ("tfr_sum_asfr_before_2026",)
        else:
            keys = ("demographic_workbook",)
            source = "cbo2026_summary_tfr"
    elif series == "awi":
        year = _year(year, 2024, 2100)
        if year == 2024:
            keys = ("actual_awi_anchor",)
            source = "tr2026_vi_g1_actual"
        else:
            keys = (
                "actual_awi_anchor",
                "long_term_economics",
                "ten_year_economics",
            )
            defaults = ("awi_bridge_2025_2026_real_earnings_times_cpiu",)
            source = "derived_cbo2026_awi_bridge"
            if year >= 2027:
                keys += ("covered_earnings",)
                defaults += ("awi_growth_of_covered_earnings_per_worker",)
                source = "derived_cbo2026_awi_covered_earnings_per_worker"
    elif series in (
        "cpiu_growth",
        "cpiu_index",
        "cpiw_growth",
        "cola",
        "real_earnings_growth",
    ):
        year = _year(year, 2024 if series == "cola" else 1996, 2100)
        if series == "real_earnings_growth":
            keys = ("long_term_economics",)
            source = "cbo2026_real_earnings_growth"
        elif 2023 <= year <= 2036:
            keys = ("ten_year_economics",)
            if year == 2023:
                keys += ("long_term_economics",)
            source = (
                "cbo2026_ten_year_cpiu_level"
                if series == "cpiu_index"
                else "derived_cbo2026_ten_year_cpiu_growth"
            )
            defaults = ("ten_year_cpiu_then_long_term_growth",)
        else:
            keys = ("long_term_economics",)
            source = "cbo2026_long_term_cpiu"
            if series == "cpiu_index" and year >= 2037:
                keys += ("ten_year_economics",)
                defaults = ("ten_year_cpiu_then_long_term_growth",)
                source = "derived_cbo2026_spliced_cpiu_level"
        if year > 2056:
            defaults += ("hold_2056_economic_growth",)
            source = "derived_cbo2026_hold_2056_growth"
        if series == "cpiw_growth":
            defaults += ("cpiw_equals_cpiu_growth",)
            source = "derived_cbo2026_cpiw_from_cpiu"
        elif series == "cola":
            defaults += (
                "cpiw_equals_cpiu_growth",
                "cola_equals_annual_cpiu_growth",
            )
            source = "derived_cbo2026_cola_from_cpiu"
    else:
        raise ValueError(f"unknown CBO2026 series {series!r}")
    specs = _data()["sources.json"]["sources"]
    selection = f"requested series={series},year={year}"
    if series == "asfr":
        selection += f",place_of_birth={place},ages=14..49"
    elif series == "mortality":
        selection += f",sex={sex},ages=0..119"
    return ValueProvenance(
        source,
        keys,
        tuple(specs[key]["locator"] + "; " + selection for key in keys),
        tuple(specs[key]["sha256"] for key in keys),
        defaults,
    )
