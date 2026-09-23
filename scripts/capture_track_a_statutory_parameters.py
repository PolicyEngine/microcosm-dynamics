"""Capture the statutory parameters the Track A oracle reads (plan A5/A9).

Writes ``data/external/track_a_statutory_parameters.json``: every
statutory parameter the Python oracle (``populace_dynamics.ss``) reads for
Track A beyond the AWI, which the assembly takes from TR2008 from 1975 on.
The values come from the policyengine-us parameter files through the
oracle's own loader (:func:`populace_dynamics.ss.params.load_ssa_parameters`)
after each file is checked against the SHA-256 pins the repository already
commits for those files
(:data:`populace_dynamics.estimates.parameters.SSA_PARAMETER_SHA256`, the
policyengine-us 1.752.2 parameter vintage of the first-estimates report).
The auxiliary constants are the statute-cited defaults of
:class:`populace_dynamics.ss.params.SSAParameters`, and the two bend-point
base amounts are the statute constants of 42 USC 415(a)(1)(B) that the
oracle hard-codes.

Before writing, the capture cross-checks the contribution and benefit base
for 1975-2008 against TR2008 Table V.C1 (historical rows through 2006 and
the rows footnote 7 marks as actual, 2007-2008) and refuses any
difference.  The registered run compares its runtime parameters with this
capture (:mod:`populace_dynamics.cola_track_a.statutory`).

Usage::

    python scripts/capture_track_a_statutory_parameters.py [--pe-us-dir DIR]
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.cola_track_a import statutory  # noqa: E402
from populace_dynamics.data import tr2008  # noqa: E402
from populace_dynamics.estimates import parameters  # noqa: E402
from populace_dynamics.ss import params as ss_params  # noqa: E402

#: The capture covers change points of the wage base through this year.
LAST_WAGE_BASE_YEAR = 2030


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _verified_files(root: Path) -> dict[str, str]:
    files = {}
    for relative, expected in parameters.SSA_PARAMETER_SHA256.items():
        observed = _sha256(root / relative)
        if observed != expected:
            raise ValueError(
                f"{root / relative} sha256 {observed} != the committed pin "
                f"{expected} (estimates.parameters.SSA_PARAMETER_SHA256)"
            )
        files[relative] = observed
    bundle = parameters._canonical_mapping_sha256(files)
    if bundle != parameters.SSA_PARAMETER_BUNDLE_SHA256:
        raise ValueError(f"parameter-file bundle sha256 {bundle} != pin")
    return files


def build_capture(pe_us_dir: Path | None = None) -> dict:
    root = ss_params._resolve_pe_us(pe_us_dir).resolve()
    files = _verified_files(root)
    loaded = ss_params.load_ssa_parameters(root)
    defaults = {
        field.name: field.default
        for field in dataclasses.fields(ss_params.SSAParameters)
        if field.name in statutory.AUXILIARY_CONSTANTS
    }
    wage_base = {
        str(year): value
        for year, value in sorted(loaded.wage_base.items())
        if year <= LAST_WAGE_BASE_YEAR
    }
    for entry in tr2008.contribution_benefit_base_path(1975, 2008):
        runtime = loaded.wage_base_for(entry.year)
        if entry.source == "tr2008_v_c1_projected" or runtime != entry.amount:
            raise ValueError(
                f"wage base {entry.year}: policyengine-us {runtime} vs "
                f"TR2008 V.C1 {entry.amount} ({entry.source})"
            )
    return {
        "schema_version": statutory.CAPTURE_SCHEMA_VERSION,
        "description": (
            "Statutory parameters the Track A Python oracle (not Axiom) "
            "reads beyond the AWI: the contribution and benefit base, the "
            "PIA formula factors, the bend-point base amounts, the full "
            "retirement age schedule, the early-retirement reduction, the "
            "delayed retirement credits, the AWI before 1975 and the "
            "auxiliary (spouse and survivor) constants"
        ),
        "source": {
            "loader": "populace_dynamics.ss.params.load_ssa_parameters",
            "policyengine_us_revision": loaded.pe_us_revision,
            "policyengine_us_files_sha256": files,
            "policyengine_us_files_bundle_sha256": (
                parameters.SSA_PARAMETER_BUNDLE_SHA256
            ),
            "files_pinned_by": (
                "populace_dynamics.estimates.parameters.SSA_PARAMETER_SHA256 "
                "(policyengine-us "
                f"{parameters.PINNED_PE_US_VERSION} parameter vintage)"
            ),
            "auxiliary_constants": (
                "statute-cited defaults of "
                "populace_dynamics.ss.params.SSAParameters"
            ),
            "bend_point_base": (
                "42 USC 415(a)(1)(B) constants hard-coded in "
                "populace_dynamics.ss.params"
            ),
            "generated_by": "scripts/capture_track_a_statutory_parameters.py",
        },
        "cross_checks": {
            "wage_base_equals_tr2008_v_c1_1975_2008": True,
            "tr2008_v_c1_rows": (
                "historical 1975-2006; footnote 7 actual 2007-2008"
            ),
        },
        "nawi_before_1975": {
            str(year): value
            for year, value in sorted(loaded.nawi.items())
            if year < statutory.FIRST_TR2008_AWI_YEAR
        },
        "wage_base_change_points": wage_base,
        "pia_factors": list(loaded.pia_factors),
        "bend_point_base": {
            "first": ss_params._BASE_FIRST_BEND,
            "second": ss_params._BASE_SECOND_BEND,
            "nawi_year": ss_params._BASE_NAWI_YEAR,
        },
        "fra_months_by_birth_year": [
            [int(year), int(months)]
            for year, months in loaded.fra_months_by_birth_year
        ],
        "early_monthly_rates": list(loaded.early_monthly_rates),
        "early_first_bracket_months": loaded.early_first_bracket_months,
        "delayed_credit_by_birth_year": [
            [int(year), float(rate)]
            for year, rate in loaded.delayed_credit_by_birth_year
        ],
        "max_delayed_months": loaded.max_delayed_months,
        "auxiliary_constants": {
            name: (list(value) if isinstance(value, tuple) else value)
            for name, value in sorted(defaults.items())
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pe-us-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=statutory.CAPTURE_PATH)
    args = parser.parse_args(argv)
    capture = build_capture(args.pe_us_dir)
    args.output.write_text(
        json.dumps(capture, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(args.output, _sha256(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
