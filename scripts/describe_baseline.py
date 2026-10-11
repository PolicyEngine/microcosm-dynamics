"""Print a baseline's input paths for documentation (input values only).

Usage::

    python scripts/describe_baseline.py --baseline tr2026_intermediate \
        --years 2026-2035 [--sources]

Prints, for every year in the range, the baseline's COLA (determination
year, percent), annual CPI-W growth (percent), AWI growth over the prior
year (percent), the death probability at 65 by sex, the TFR and the ASFR
at ages 20, 30 and 40 (births per 1,000 women).  ``--sources`` adds each
value's source tag (derived values are tagged as derived).  These are
the baseline's inputs; nothing is projected and no outcome is computed.
A value the baseline does not supply prints as ``gap``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.baselines import (  # noqa: E402
    BASELINE_NAMES,
    DEFAULT_BASELINE,
    BaselineGapError,
    get_baseline,
)

COLUMNS = (
    ("year", 4),
    ("COLA%", 6),
    ("CPI-W%", 6),
    ("AWIg%", 6),
    ("q65 M", 8),
    ("q65 F", 8),
    ("TFR", 6),
    ("f20", 6),
    ("f30", 6),
    ("f40", 6),
)
_GAP = "gap"
#: The first determination year taken from the baseline's own tables, as
#: in the projections (``TrackAConfig.tr2008_first_rate_year``).
FIRST_RATE_YEAR = 2008


def _years(text: str) -> range:
    first, _, last = text.partition("-")
    try:
        start, stop = int(first), int(last or first)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"--years must look like 2026-2035, got {text!r}"
        ) from error
    if start > stop:
        raise argparse.ArgumentTypeError("--years must be increasing")
    return range(start, stop + 1)


def _value(function, fmt: str) -> str:
    try:
        return format(float(function()), fmt)
    except (BaselineGapError, KeyError, ValueError):
        return _GAP


def _series(function) -> dict:
    """A year-keyed path, or an empty one if the range is not covered."""
    try:
        path = function()
    except (BaselineGapError, KeyError, ValueError):
        return {}
    if hasattr(path, "by_determination_year"):
        return dict(path.by_determination_year)
    return dict(path)


def describe(name: str, years: range, *, sources: bool = False) -> str:
    """The text the CLI prints for ``name`` over ``years``."""
    baseline = get_baseline(name)
    first = min(FIRST_RATE_YEAR, years[-1])
    cola = _series(lambda: baseline.cola_rates(first, years[-1]))
    awi = _series(lambda: baseline.awi(years[0] - 1, years[-1]))
    lines = [
        f"Baseline: {baseline.name}",
        f"Vintage: {baseline.vintage}",
        "Input values only (no projection, no outcome).",
        "COLA% is the determination-year increase; AWIg% the AWI growth "
        "over the prior year; f20/f30/f40 are births per 1,000 women.",
        "",
        "  ".join(label.rjust(width) for label, width in COLUMNS),
    ]
    for year in years:
        cells = (
            str(year),
            _value(lambda year=year: 100.0 * cola[year], ".2f"),
            _value(lambda year=year: baseline.cpiw_growth(year), ".2f"),
            _value(
                lambda year=year: 100.0 * (awi[year] / awi[year - 1] - 1.0),
                ".2f",
            ),
            *(
                _value(
                    lambda year=year, sex=sex: baseline.qx(year)[sex][65],
                    ".6f",
                )
                for sex in ("male", "female")
            ),
            _value(lambda year=year: baseline.tfr(year), ".3f"),
            *(
                _value(
                    lambda year=year, age=age: 1000.0
                    * baseline.asfr(year)[age],
                    ".2f",
                )
                for age in (20, 30, 40)
            ),
        )
        lines.append(
            "  ".join(
                cell.rjust(width)
                for cell, (_, width) in zip(cells, COLUMNS, strict=True)
            )
        )
    if sources:
        lines += ["", "Sources by year:"]
        for year in years:
            try:
                tags = baseline.value_sources(year)
            except (BaselineGapError, KeyError, ValueError):
                lines.append(f"  {year}: {_GAP}")
                continue
            lines.append(
                f"  {year}: "
                + "; ".join(f"{key}={value}" for key, value in tags.items())
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--baseline", choices=BASELINE_NAMES, default=DEFAULT_BASELINE
    )
    parser.add_argument("--years", type=_years, default=_years("2026-2035"))
    parser.add_argument("--sources", action="store_true")
    args = parser.parse_args(argv)
    print(describe(args.baseline, args.years, sources=args.sources))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
