"""Read EPUF's per-year disclosure constants off the pinned bytes.

SSA's disclosure operator (EPUF dictionary; Compson 2011) replaces every
annual value below $100 with one per-year mean, and every value within
one rounding base below the taxable maximum with one per-year band
mean. Neither constant is printed in the documentation, but each is
readable from the file: a year has exactly one distinct value below
$100, and exactly one value inside the band that is not a multiple of
the rounding base. This script records both for 1951-2006 so that
``populace_dynamics.harness.epuf_operator`` can apply the same operator
to survey-side and model-side earnings without the microdata staged.

Usage::

    uv run python scripts/extract_epuf_disclosure_constants.py

Writes ``data/external/epuf_2006/disclosure_constants.json``. It reads
EPUF only (no PSID, no model output).
"""

from __future__ import annotations

import json
from pathlib import Path

from populace_dynamics.cola_track_a.statutory import load_statutory_capture
from populace_dynamics.data import epuf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external" / "epuf_2006" / "disclosure_constants.json"

#: SSA's rounding bases by earnings level (Compson 2011, "Disclosure
#: protection"): $25 from $100 to $999, $100 from $1,000 to $49,999 and
#: $1,000 from $50,000.
BOTTOM_CODE_BELOW = 100
BASE_BREAKS = ((1_000, 25), (50_000, 100))
TOP_BASE = 1_000


def rounding_base(value: float) -> int:
    for upper, base in BASE_BREAKS:
        if value < upper:
            return base
    return TOP_BASE


def wage_base_by_year() -> dict[int, int]:
    points = {
        int(year): float(value)
        for year, value in load_statutory_capture()[
            "wage_base_change_points"
        ].items()
    }
    return {
        year: int(points[max(y for y in points if y <= year)])
        for year in range(epuf.EPUF_FIRST_YEAR, epuf.EPUF_LAST_YEAR + 1)
    }


def build() -> dict:
    annual = epuf.read_annual()
    caps = wage_base_by_year()
    years = {}
    for year, values in annual.groupby("year")["earnings"]:
        year = int(year)
        cap = caps[year]
        base = rounding_base(cap)
        below = sorted(
            int(v) for v in values[values < BOTTOM_CODE_BELOW].unique()
        )
        in_band = values[(values > cap - base) & (values < cap)]
        off_grid = sorted(
            int(v) for v in in_band[in_band % base != 0].unique()
        )
        if len(below) != 1 or len(off_grid) != 1:
            raise ValueError(
                f"{year}: expected one bottom code and one band mean, got "
                f"{below} and {off_grid}"
            )
        years[str(year)] = {
            "wage_base": cap,
            "band_base": base,
            "bottom_code": below[0],
            "band_mean": off_grid[0],
            "n_bottom_coded": int((values == below[0]).sum()),
            "n_band_mean": int((values == off_grid[0]).sum()),
            "n_at_wage_base": int((values == cap).sum()),
            "n_positive": int(len(values)),
        }
    return {
        "schema_version": "epuf_disclosure_constants.v1",
        "generator": "scripts/extract_epuf_disclosure_constants.py",
        "source": {
            "annual_sha256": epuf.EPUF_SHA256[epuf.ANNUAL_FILE],
            "wage_base": (
                "data/external/track_a_statutory_parameters.json "
                "wage_base_change_points"
            ),
        },
        "rule": {
            "bottom_code_below": BOTTOM_CODE_BELOW,
            "rounding_bases": [
                {"from": 100, "below": 1_000, "base": 25},
                {"from": 1_000, "below": 50_000, "base": 100},
                {"from": 50_000, "below": None, "base": 1_000},
            ],
            "band": (
                "values strictly between the wage base less one rounding "
                "base (the base at the wage base) and the wage base are "
                "replaced by band_mean"
            ),
        },
        "years": years,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
