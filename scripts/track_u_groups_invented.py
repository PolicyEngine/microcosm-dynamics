#!/usr/bin/env python3
# ruff: noqa: E402
"""INVENTED DATA - NOT A COMPARISON: G4b complete adapter dry run."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.cohorts import (
    age67,
)
from populace_dynamics.cohorts import (
    group_attributes as ga,
)
from populace_dynamics.data import group_attributes_psid as gap
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import lifetime_measures as lm
from populace_dynamics.group_breakdowns import (
    common,
)
from populace_dynamics.group_breakdowns import (
    uniform_cut as groups,
)
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.uniform_cut_track_u import (
    invented,
    runner,
)


def invented_attribute_loader(inputs: age67.Age67Inputs):
    """Build G1 side frames from explicit invented race/education reports."""

    universe = (
        inputs.death_records["person_id"].drop_duplicates().astype("int64")
    )
    report_columns = ["person_id", "wave", "role", *gap.REPORT_CODE_COLUMNS]
    reports, education = [], []
    for index, pid in enumerate(universe):
        row = dict.fromkeys(report_columns, pd.NA)
        row.update(
            person_id=int(pid),
            wave=2013,
            role="head",
            hispanic_code=int(index % 4 == 0),
            family_education_code=12,
            birth_state_code=1 if index % 2 else 0,
            year_came_code=0 if index % 2 else 1960,
        )
        for mention in range(1, len(gap.FAMILY_ITEMS[2013].race["head"]) + 1):
            row[f"race_code_{mention}"] = 1 + index % 3 if mention == 1 else 0
        reports.append(row)
        education.append(
            {
                "person_id": int(pid),
                "wave": 2005,
                "education_code": (10, 12, 14, 16, 17)[index % 5],
                "role": pd.NA,
                "family_education_code": pd.NA,
            }
        )
    reports = pd.DataFrame(reports, columns=report_columns)
    education = pd.DataFrame(education)
    for frame in (reports, education):
        for name in frame:
            frame[name] = frame[name].astype(
                "string" if name == "role" else "Int64"
            )
    side_inputs = ga.GroupAttributeInputs(
        reports=reports,
        education=education,
        universe=universe,
        provenance={
            "kind": "INVENTED",
            "fixture": "G4b deterministic categories, not PSID",
        },
    )

    def loader(person_ids, *, anchor_waves):
        return ga.build_group_attributes(
            side_inputs, person_ids, anchor_waves=anchor_waves
        )

    return loader


def invented_lifetime_inputs() -> groups.LifetimeInputs:
    """INVENTED wage indices, contribution bases, tax and interest rates."""

    params = SSAParameters(
        nawi={
            year: 1000.0 * 1.02 ** (year - 1951) for year in range(1951, 2024)
        },
        wage_base={1937: 50000.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )
    rates = lm.OASDITaxRates(
        combined_percent_by_year={1937: 10.0},
        open_ended_from=1938,
        open_ended_combined_percent=10.0,
        basis=lm.TaxRateBasis.EMPLOYEE_EMPLOYER_PAID,
        provenance={"source": "INVENTED"},
    )
    interest = lm.TrustFundInterestRates(
        percent_by_year={year: 3.0 for year in range(1937, 2024)},
        series="INVENTED",
        provenance={"source": "INVENTED"},
    )
    return groups.LifetimeInputs(params, rates, interest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "docs/analysis/nasi_group_breakdowns_invented_20261001"
        / "exercise_2_uniform_cut/track_u_groups_invented.json",
    )
    args = parser.parse_args(argv)
    inputs = invented.invented_age67_inputs(supplement_waves_staged=True)
    parameters = runner.committed_parameters(
        invented.invented_poverty_thresholds()
    )
    committed = runner.run_track_u(
        inputs, parameters, data_provenance=ap.INVENTED
    )
    artifact = groups.build_uniform_cut_groups(
        inputs,
        parameters,
        committed,
        data_provenance=ap.INVENTED,
        attribute_loader=invented_attribute_loader(inputs),
        lifetime_inputs=invented_lifetime_inputs(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    common.write_artifact_pair(
        output=args.output,
        artifact=artifact,
        environment={
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "kind": "INVENTED dry run; not recorded real-run environment",
        },
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
