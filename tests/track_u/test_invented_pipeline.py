"""The whole Track U chain on INVENTED data (a miniature dry run).

Builder -> income rows -> adjusted income -> tabulation, on the invented
cohort frames of ``tests/cohorts/test_age67.py`` with invented family
income, wealth, life table, thresholds and SSI parameters. Every number is
made up; the result is labelled invented and is not a PSID statistic.
"""

from __future__ import annotations

import pandas as pd
import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.data import family_income
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from tests.cohorts.test_age67 import _ANCHOR_ROWS, _inputs

YEARS = range(2004, 2013)
#: INVENTED life table: 10 percent a year to 109, certain death at 110.
MOCK_LIFE_TABLE = ap.LifeTable(
    name=ap.INVENTED_LIFE_TABLE,
    qx={sex: (0.1,) * 110 + (1.0,) for sex in ("male", "female")},
)
_ROWS = dict.fromkeys(ap.THRESHOLD_ROW_KEYS, 0.0)
#: INVENTED thresholds (not Census values).
MOCK_THRESHOLDS = ap.PovertyThresholds(
    weighted_average={
        year: {
            key: 10_000.0 + 1_000.0 * i
            for i, key in enumerate(ap.THRESHOLD_ROW_KEYS)
        }
        for year in YEARS
    },
    matrix={year: {key: {0: 1.0} for key in _ROWS} for year in YEARS},
    provenance={"kind": "invented"},
)
#: INVENTED SSI parameters.
MOCK_SSI = ap.SsiParameters(
    fbr_individual_monthly=dict.fromkeys(YEARS, 600.0),
    fbr_couple_monthly=dict.fromkeys(YEARS, 900.0),
    general_income_exclusion_monthly=20.0,
    earned_income_exclusion_monthly=65.0,
    earned_income_share_excluded=0.5,
    resource_limit_individual=2000.0,
    resource_limit_couple=3000.0,
    provenance={"kind": "invented"},
)


def _full_family(wave: int) -> pd.DataFrame:
    interviews = sorted(
        {row[1] for row in _ANCHOR_ROWS.get(wave, []) if row[2] <= 20}
    )
    frame = pd.DataFrame({"interview": interviews})
    for concept in family_income.income_variables(wave):
        if concept != "interview":
            frame[concept] = 0
    frame["wave"] = wave
    frame["income_year"] = wave - 1
    frame["fu_size"] = 2
    frame["head_sex"] = "male"
    frame["head_age"] = pd.array([67] * len(frame), dtype="Int64")
    frame["wife_age"] = pd.array([65] * len(frame), dtype="Int64")
    frame["wife_present"] = True
    frame["census_needs_standard"] = 12_000
    frame["head_ss"] = 9_000
    frame["wife_ss"] = 4_000
    frame["total_family_income"] = 13_000
    return frame


def _full_wealth(wave: int) -> pd.DataFrame:
    frame = _full_family(wave)[["wave", "interview"]].copy()
    frame["wealth1"] = 20_000
    frame["wealth1_acc"] = 0
    frame["vehicles"] = 5_000
    return frame


def test_invented_chain_runs_end_to_end():
    inputs = _inputs(
        family_income={wave: _full_family(wave) for wave in age67.WAVES},
        family_wealth={
            wave: _full_wealth(wave) for wave in family_income.WEALTH_WAVES
        },
    )
    cohort = age67.build_age67_cohort(inputs)
    rows = age67.income_rows(cohort, inputs, allow_blocked=True)
    missing = [c for c in ap.REQUIRED_COLUMNS if c not in rows.columns]
    assert not missing
    adjusted = ap.adjusted_incomes(
        rows,
        data_provenance=ap.INVENTED,
        life_table=MOCK_LIFE_TABLE,
        thresholds=MOCK_THRESHOLDS,
        ssi=MOCK_SSI,
    )
    # every invented family: 13,000 money income, no asset income, a
    # threshold for two persons of 13,000 (the fourth invented row)
    assert set(adjusted["threshold"]) == {13_000.0}
    assert adjusted["cut"].tolist() == pytest.approx([0.13 * 13_000] * 3)
    joined = ut.tabulation_rows(rows, adjusted)
    result = ut.tabulate_uniform_cut(
        joined,
        data_provenance="invented",
        upstream_spec=adjusted.attrs["spec"],
        pending_decisions=[d.as_dict() for d in ap.pending_decisions()],
        design=inputs.design,
    )
    assert result["labels"][0] == ut.INVENTED_DATA_LABEL
    cells = {entry["cell"]: entry for entry in result["cells"]}
    assert cells["all"]["n_observations"] == 3
    assert cells["all"]["n_family_units"] == 2
    assert result["upstream_spec"]["ssi_rule"] == "offset_existing_recipients"
    assert any(
        item["field"] == "ssi_rule" for item in result["pending_decisions"]
    )


def test_tabulation_rows_carry_a_psid_provenance():
    members = pd.DataFrame(
        {
            column: [1]
            for column in ut.REQUIRED_COLUMNS
            if column not in ("poor_baseline", "poor_reform")
        }
    )
    members["observation_id"] = ["a"]
    members.attrs["provenance_kind"] = "psid_files"
    adjusted = pd.DataFrame(
        {
            "observation_id": ["a"],
            "poor_baseline": [False],
            "poor_reform": [True],
        }
    )
    joined = ut.tabulation_rows(members, adjusted)
    assert joined.attrs["provenance_kind"] == "psid_files"
    with pytest.raises(ut.UniformCutTabulationError, match="different"):
        ut.tabulation_rows(members, adjusted.assign(observation_id=["b"]))
