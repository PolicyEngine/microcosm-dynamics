"""Capture the quarter-of-coverage amounts for Track M (plan item M2).

Reads the policyengine-us parameter file
``policyengine_us/parameters/gov/ssa/social_security/
quarters_of_coverage_threshold.yaml`` (it cites 42 USC 413(d)(2), 20 CFR
404.143 and SSA's QC table, SSA.gov/OACT/COLA/QC.html) from the checkout
the oracle reads, and writes ``data/external/
ssa_quarter_of_coverage_amounts.json`` with the file's path, revision and
SHA-256.  Before writing it checks every value:

* **against the statute.**  42 USC 413(d)(1)-(2) sets $250 for 1978 and,
  for each later year, the larger of the preceding year's amount and $250
  times the national average wage index of two years before over that of
  1976, rounded to $10 (``min_benefit_track_m.coverage.
  statutory_qc_amounts``, with the oracle's wage index).  Every year of
  the file must equal the statute's amount; the script refuses to write
  otherwise and records the check;
* **against Table 2's label** (ruling C5, formula checks only): four
  times the 2006 amount is $3,880.

The capture records the policyengine-us ``nawi.yaml`` it checked with
(path and SHA-256) and the statute copy's locator.  Usage::

    python scripts/capture_track_m_quarter_of_coverage.py \\
        [--pe-us-dir DIR] [--output data/external/...json] [--check]

``--check`` recaptures in memory and refuses if the committed file
differs, byte for byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.min_benefit_track_m import coverage  # noqa: E402
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

DEFAULT_OUTPUT = coverage.QC_CAPTURE_PATH
NAWI_PATH = Path("policyengine_us/parameters/gov/ssa/nawi.yaml")
STATUTE = {
    "provision": "42 USC 413(d)(1)-(2)",
    "copy": "track-m-review-20260924/usc-42-413-cornell.txt",
    "copy_sha256": (
        "7d226c0a476d5bf83f07c06deef8b4563cbdc633a6ddf4b5921bc0afc654671c"
    ),
    "lines": "101-109",
    "evidence_root": "~/microcosm-launch-evidence/dynasim-parity-20260909",
}
TABLE2_CHECK = {"year": 2006, "four_quarters": 3_880.0}


def _pe_us_root(pe_us_dir: Path | None) -> Path:
    return coverage._resolve_pe_us(pe_us_dir)


def build(pe_us_dir: Path | None = None) -> dict[str, Any]:
    """The capture document; raises if any value fails its check."""

    qc = coverage.load_qc_amounts_from_checkout(pe_us_dir)
    root = _pe_us_root(pe_us_dir)
    document = yaml.safe_load(
        (root / coverage.QC_PARAMETER_PATH).read_text(encoding="utf-8")
    )
    params = load_ssa_parameters(pe_us_dir)
    years = sorted(qc.amounts)
    if years[0] != coverage.FIRST_QC_YEAR or years != list(
        range(years[0], years[-1] + 1)
    ):
        raise ValueError(f"quarter-of-coverage years are not 1978-: {years}")
    statute = coverage.statutory_qc_amounts(params.nawi, years[-1])
    differences = [
        {"year": year, "file": qc.amounts[year], "statute": statute[year]}
        for year in years
        if qc.amounts[year] != statute[year]
    ]
    if differences:
        raise ValueError(
            f"quarter-of-coverage amounts differ from 42 USC 413(d): "
            f"{differences}"
        )
    four = 4 * qc.amount(TABLE2_CHECK["year"])
    if four != TABLE2_CHECK["four_quarters"]:
        raise ValueError(f"4 x QC(2006) = {four}, not $3,880")
    nawi_raw = (root / NAWI_PATH).read_bytes()
    references = [
        {"title": ref.get("title"), "href": ref.get("href")}
        for ref in document.get("metadata", {}).get("reference", [])
    ]
    return {
        "schema_version": coverage.QC_CAPTURE_SCHEMA,
        "description": (
            "The amount of wages and self-employment income that credits "
            "one Social Security quarter of coverage, by calendar year "
            "(42 USC 413(d)); four times it is the covered earnings of a "
            "work year for Track M (M1 specification section 5)"
        ),
        "unit": "dollars",
        "years": [years[0], years[-1]],
        "amounts": {str(year): int(qc.amounts[year]) for year in years},
        "source": {
            "path": str(coverage.QC_PARAMETER_PATH),
            "pe_us_revision": qc.source["pe_us_revision"],
            "sha256": qc.source["sha256"],
            "description": document.get("description"),
            "references": references,
            "values_comment": "Historical values from SSA.gov/OACT/COLA/QC.html",
        },
        "value_check": {
            "statute": STATUTE,
            "rule": (
                "QC(1978) = 250; QC(y) = max(QC(y - 1), round_to_ten(250 * "
                "AWI(y - 2) / AWI(1976))), a multiple of $5 not of $10 "
                "rounding up (min_benefit_track_m.coverage."
                "statutory_qc_amounts)"
            ),
            "wage_index": {
                "path": str(NAWI_PATH),
                "sha256": hashlib.sha256(nawi_raw).hexdigest(),
                "pe_us_revision": params.pe_us_revision,
            },
            "years_checked": [years[0], years[-1]],
            "differences": differences,
            "table2_label_check": {
                **TABLE2_CHECK,
                "ruling": "C5 (formula unit tests only)",
                "passes": True,
            },
        },
        "captured_by": "scripts/capture_track_m_quarter_of_coverage.py",
    }


def serialize(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pe-us-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    raw = serialize(build(args.pe_us_dir))
    if args.check:
        committed = args.output.read_bytes()
        if committed != raw:
            raise SystemExit(f"{args.output} differs from a fresh capture")
        print(f"{args.output} matches ({hashlib.sha256(raw).hexdigest()})")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(args.output, hashlib.sha256(raw).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
