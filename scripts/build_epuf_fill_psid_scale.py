"""Count the PSID-2010 cohort's units behind each gate_epuf_fill cell.

The floors of ``gate_epuf_fill`` price each cell at the PSID's size
(``docs/amendments/gate_epuf_fill_registration_proposal.md``, section 5).
This script builds the default-spec PSID-2010 cohort
(:func:`populace_dynamics.cohorts.psid2010.build_psid2010_cohort`) from the
staged PSID and records, unweighted:

- per sex and age band of family ``odd`` (``a22_74`` pools the bands): the
  career years the assembler filled with the neighbour mean (provenance
  ``gap_imputed``) at an age in the band, among members positive in a
  recorded even year 1996-2010, and the number of distinct members behind
  them;
- per sex and cohort of every cohort group (pooled cohorts included):
  members positive in a recorded year from ``max(1968, birth_year + 22)``
  through 2010.

It reads no EPUF value. Usage::

    python scripts/build_epuf_fill_psid_scale.py \
        --output runs/epuf_fill_gate_psid_scale_v2.json
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

import numpy as np

from populace_dynamics.artifacts import write_new
from populace_dynamics.cohorts import psid2010
from populace_dynamics.harness import epuf_fill_gate as g

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "populace_dynamics.epuf_fill_gate_psid_scale.v2"
_SEX = {"men": "male", "women": "female"}
_RECORDED_EVEN = tuple(range(1996, 2011, 2))


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def scale(persons, careers) -> dict[str, dict[str, int]]:
    """The unit counts for every floor group (``epuf_fill_gate.groups``)."""

    rows = careers.merge(
        persons[["person_id", "sex", "birth_year"]], on="person_id"
    )
    rows["age"] = rows["year"] - rows["birth_year"]
    observed = rows[
        (rows["provenance"] == "observed") & (rows["earnings"] > 0)
    ]
    odd_universe = set(
        observed.loc[observed["year"].isin(_RECORDED_EVEN), "person_id"]
    )
    start = np.maximum(1968, observed["birth_year"] + 22)
    career_universe = set(observed.loc[observed["year"] >= start, "person_id"])
    filled = rows[
        (rows["provenance"] == "gap_imputed")
        & rows["person_id"].isin(odd_universe)
    ]
    cohorts = {
        **g.ODD_AIME_COHORTS,
        **g.PARTIAL_AIME_COHORTS,
        **g.PRE_CAREER_COHORTS,
        **g.YOUTH_COHORTS,
    }
    out: dict[str, dict[str, int]] = {}
    for group in g.groups():
        family, sex_label, stratum = group.split(".")
        sex_value = _SEX[sex_label]
        if family == "odd" and stratum in g.ODD_AGE_BANDS:
            low, high = g.ODD_AGE_BANDS[stratum]
            units = filled[
                (filled["sex"] == sex_value)
                & (filled["age"] >= low)
                & (filled["age"] <= high)
            ]
            out[group] = {
                "filled_person_years": int(len(units)),
                "persons": int(units["person_id"].nunique()),
            }
            continue
        low, high = cohorts[stratum]
        members = persons[
            (persons["sex"] == sex_value)
            & persons["person_id"].isin(career_universe)
            & persons["birth_year"].between(low, high)
        ]
        out[group] = {"persons": int(len(members))}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()
    started = time.time()
    inputs = psid2010.load_psid2010_inputs(data_dir=args.data_dir)
    spec = psid2010.Psid2010CohortSpec()
    cohort = psid2010.build_psid2010_cohort(inputs, spec)
    document = {
        "schema": SCHEMA,
        "registration_id": g.REGISTRATION_ID,
        "code_commit": _git_head(),
        "spec": spec.as_dict(),
        "psid_provenance": dict(inputs.provenance),
        "cohort_provenance": dict(cohort.provenance),
        "n_members": int(len(cohort.persons)),
        "weighting": "unweighted counts",
        "groups": scale(cohort.persons, cohort.careers),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_new(args.output, document, sidecar=True)


if __name__ == "__main__":
    main()
