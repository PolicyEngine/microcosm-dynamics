"""The Track U row pipeline on INVENTED data, and its guards.

The cohort, the thresholds and every amount are INVENTED (the generator of
:mod:`populace_dynamics.uniform_cut_track_u.invented`); the life tables and
the SSI parameters are the committed files under ``data/external``, and
the F17 component diagnostics read the committed SSA snapshot there.  No
PSID file and no comparator value is read.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u import invented, rows, runner
from tests.cohorts.test_age67 import _inputs

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "data" / "external"
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)


@pytest.fixture(scope="module")
def params() -> runner.TrackUParameters:
    assert (COMMITTED / "track_u_ssi_parameters.json").is_file()
    return runner.committed_parameters(invented.invented_poverty_thresholds())


@pytest.fixture(scope="module")
def staged() -> age67.Age67Inputs:
    return invented.invented_age67_inputs(supplement_waves_staged=True)


@pytest.fixture(scope="module")
def result(staged, params) -> dict:
    return runner.run_track_u(staged, params, data_provenance=ap.INVENTED)


def _all(entry: dict) -> dict:
    return next(
        cell for cell in entry["tabulation"]["cells"] if cell["cell"] == "all"
    )


def test_every_row_runs_and_u7_is_reported_not_built(result):
    assert list(result["rows"]) == list(rows.REGISTERED_ROWS)
    assert result["rows"]["U7"]["status"] == "not_built"
    assert result["rows"]["U7"]["tabulation"] is None
    for row_id, entry in result["rows"].items():
        if row_id == "U7":
            continue
        assert entry["status"] == "computed"
        assert entry["tabulation"]["data_provenance"] == ap.INVENTED
        assert entry["tabulation"]["labels"][0] == ut.INVENTED_DATA_LABEL
        cell = _all(entry)
        assert cell["defined"]
        # nobody leaves poverty under a cut (plan section 1)
        assert entry["income_concept_counts"]["n_leaving_poverty"] == 0
        assert cell["delta"] >= 0
    assert result["labels"][0] == ut.INVENTED_DATA_LABEL
    assert result["labels"][1:] == list(ap.OUTPUT_LABELS)
    assert result["headline"]["row"] == rows.PRIMARY_ROW
    assert {
        item["field"] for item in result["pending_decisions"]["tabulation"]
    } == {
        "design_se_domain",
        "cells",
    }
    for entry in result["rows"].values():
        if entry["status"] == "computed":
            assert entry["tabulation"]["design"]["domain"] == (
                "full_sample_design"
            )
            assert entry["tabulation"]["design"]["singleton_strata"] == []
    assert result["cohort_provenance"]["kind"] == age67.INVENTED
    assert result["psid_files_sha256"] == {}
    assert result["input_checks"]["invented_inputs"]["regenerated"]
    assert result["input_checks"]["invented_cohort"]["rebuilt"]


def test_rows_change_only_what_they_register(result):
    rows_ = result["rows"]
    u0, u1, u6 = rows_["U0"], rows_["U1"], rows_["U6"]
    # U2: no SSI response at all
    assert rows_["U2"]["income_concept_counts"]["n_ssi_offset_positive"] == 0
    assert rows_["U2"]["income_concept_counts"]["n_ssi_new_positive"] == 0
    # U0 never enrols anyone new
    assert u0["income_concept_counts"]["n_ssi_new_positive"] == 0
    # U4 puts the head and wife members on the head/wife basis
    assert "head_wife" in rows_["U4"]["income_concept_counts"]["income_basis"]
    # U5 removes no reported asset income
    counts = rows_["U5"]["income_concept_counts"]
    assert counts["n_asset_income_removed_nonzero"] == 0
    # U6 is U1 with the 1936 birth year uncut
    n_1936 = u1["population"]["observations_by_birth_year"]["1936"]
    assert u6["population"] == u1["population"]
    assert u6["income_concept_counts"]["n_cut_applies"] == (
        u1["income_concept_counts"]["n_cut_applies"] - n_1936
    )
    assert _all(u6)["baseline_rate"] == pytest.approx(
        _all(u1)["baseline_rate"]
    )
    assert _all(u6)["reform_rate"] <= _all(u1)["reform_rate"]
    cells = {cell["cell"]: cell for cell in u6["tabulation"]["cells"]}
    assert cells["birth_year_1936"]["delta"] == 0.0
    # U-inst adds the institutionalized members to U0's population
    inst = rows_["U-inst"]["population"]
    assert inst["n_in_institution"] > 0
    assert inst["n_observations_tabulated"] == (
        u0["population"]["n_observations_tabulated"] + inst["n_in_institution"]
    )
    # U9 prices on the SSA 2004 table
    assert rows_["U9"]["life_table"] == "ssa_period_2004"
    assert u0["life_table"] == "nchs_2000"
    # U5 keeps the F4a and F4b items too; U0 removes them
    counts = u0["income_concept_counts"]
    assert counts["n_retirement_account_income_removed_nonzero"] > 0
    assert counts["n_farm_asset_income_removed_nonzero"] > 0
    for key in (
        "n_retirement_account_income_removed_nonzero",
        "n_farm_asset_income_removed_nonzero",
    ):
        assert rows_["U5"]["income_concept_counts"][key] == 0
    # U0-F is U0 on 1941, 1943 and 1945
    fallback = rows_["U0-F"]["population"]["observations_by_birth_year"]
    assert fallback == {
        year: n
        for year, n in u0["population"]["observations_by_birth_year"].items()
        if year in ("1941", "1943", "1945")
    }


def test_f17_diagnostics_are_reported_for_u0(result):
    f17 = result["f17_diagnostics"]
    assert f17["row"] == "U0"
    official = f17["official_concept_poverty_rate"]["cells"]
    assert set(official) == set(runner.OFFICIAL_CONCEPT_CELLS)
    assert all(cell["defined"] for cell in official.values())
    components = f17["components"]
    assert components["population"]["provenance_kind"] == age67.INVENTED
    assert set(components["social_security"]) == {
        "2004",
        "2006",
        "2008",
        "2010",
        "2012",
    }


def test_official_concept_rates_by_hand():
    # INVENTED: weights 1, 1, 2, 4; poor under money income: rows a and d
    members = pd.DataFrame(
        {
            "observation_id": ["a", "b", "c", "d"],
            "weight": [1.0, 1.0, 2.0, 4.0],
            "sex": ["male", "female", "female", "male"],
            "married": [True, False, True, False],
        }
    )
    adjusted = pd.DataFrame(
        {
            "observation_id": ["a", "b", "c", "d"],
            "money_income": [900.0, 1_000.0, 2_000.0, 500.0],
            "threshold": [1_000.0, 1_000.0, 1_000.0, 1_000.0],
        }
    )
    cells = runner.official_concept_rates(members, adjusted)["cells"]
    # all: (1 + 4) / 8; b at the threshold is not poor
    assert cells["all"]["rate"] == pytest.approx(62.5)
    assert cells["men"]["rate"] == pytest.approx(100.0)
    assert cells["women"]["rate"] == pytest.approx(0.0)
    assert cells["married"]["rate"] == pytest.approx(100 / 3)
    assert cells["non_married"]["rate"] == pytest.approx(80.0)
    with pytest.raises(runner.TrackURunError, match="do not match"):
        runner.official_concept_rates(members, adjusted.iloc[:3])


def test_the_invented_label_needs_the_generators_inputs(params, staged):
    with pytest.raises(ValueError, match="not invented"):
        runner.run_track_u(_inputs(), params, data_provenance=ap.INVENTED)
    income = dict(staged.family_income)
    edited = income[2011].copy()
    edited.loc[0, "total_family_income"] += 5
    income[2011] = edited
    forged = dataclasses.replace(staged, family_income=income)
    forged = dataclasses.replace(
        forged,
        provenance={
            **staged.provenance,
            "input_frames_sha256": age67.input_frames_sha256(forged),
        },
    )
    with pytest.raises(ValueError, match="not the invented generator's"):
        runner.run_track_u(forged, params, data_provenance=ap.INVENTED)
    with pytest.raises(runner.TrackURunError, match="no registration"):
        runner.run_track_u(
            staged,
            params,
            data_provenance=ap.INVENTED,
            registration_pointer=POINTER,
        )


@pytest.mark.parametrize(
    "pointer",
    [
        None,
        "https://example.org/x",
        "https://github.com/PolicyEngine/microcosm-dynamics/issues/42",
        "https://github.com/PolicyEngine/microcosm-dynamics/issues/420"
        "#issuecomment-1",
    ],
)
def test_a_registered_run_needs_an_issue_42_comment(params, staged, pointer):
    with pytest.raises(runner.TrackURunError, match="issue #42"):
        runner.run_track_u(
            staged,
            params,
            data_provenance=ap.REGISTERED_REAL,
            registration_pointer=pointer,
        )


def test_a_registered_run_refuses_invented_or_blocked_inputs(params, staged):
    with pytest.raises(runner.TrackURunError, match="load_age67_inputs"):
        runner.run_track_u(
            staged,
            params,
            data_provenance=ap.REGISTERED_REAL,
            registration_pointer=POINTER,
        )
    claimed = dataclasses.replace(
        staged, provenance={**staged.provenance, "kind": age67.PSID_FILES}
    )
    with pytest.raises(runner.TrackURunError, match="blocked observations"):
        runner.run_track_u(
            claimed,
            params,
            data_provenance=ap.REGISTERED_REAL,
            registration_pointer=POINTER,
            allow_blocked=True,
        )
    # refused waves no longer stop a registered run at the input check
    # (the fallback rule applies); these inputs still fail the parameter
    # check, since no Census capture is pinned
    blocked = dataclasses.replace(
        invented.invented_age67_inputs(),
        provenance={**staged.provenance, "kind": age67.PSID_FILES},
    )
    with pytest.raises(runner.TrackURunError, match="Census threshold"):
        runner.run_track_u(
            blocked,
            params,
            data_provenance=ap.REGISTERED_REAL,
            registration_pointer=POINTER,
        )


def test_the_fallback_rule_as_staged_today(params):
    """Specification section 11: without the 2005/2007 wealth, U0-F is the
    headline and every row that needs those waves is reported blocked with
    its counts (INVENTED data)."""

    blocked = invented.invented_age67_inputs()
    assert runner.headline_row(blocked) == rows.FALLBACK_ROW
    result = runner.run_track_u(blocked, params, data_provenance=ap.INVENTED)
    assert result["headline"]["row"] == "U0-F"
    assert result["headline"]["rule"] == rows.HEADLINE_RULE
    assert result["headline"]["wealth_refused_waves"] == [2005, 2007]
    statuses = {row: entry["status"] for row, entry in result["rows"].items()}
    assert statuses.pop("U0-F") == "computed"
    assert statuses.pop("U7") == "not_built"
    assert set(statuses.values()) == {"blocked"}
    u0 = result["rows"]["U0"]
    assert u0["tabulation"] is None
    assert u0["blocked_waves"] == [2005, 2007]
    assert set(u0["population"]["blocked_by_birth_year"]) == {"1937", "1939"}
    u6 = result["rows"]["U6"]
    assert u6["blocked_waves"] == [2005, 2007]
    assert result["f17_diagnostics"]["row"] == "U0-F"
    tabulated = result["rows"]["U0-F"]["population"]
    assert set(tabulated["observations_by_birth_year"]) == {
        "1941",
        "1943",
        "1945",
    }
    assert tabulated["left_out"] == {"wealth_supplement_not_staged": 0}


def test_blocked_waves_and_design_frame():
    staged = invented.invented_age67_inputs(supplement_waves_staged=True)
    blocked = invented.invented_age67_inputs()
    registered = rows.REGISTERED_ROWS
    assert runner.headline_row(staged) == rows.PRIMARY_ROW
    assert runner.blocked_waves(registered["U0"], staged) == []
    assert runner.blocked_waves(registered["U0"], blocked) == [2005, 2007]
    assert runner.blocked_waves(registered["U0-F"], blocked) == []
    design = runner.design_frame(staged, registered["U0"].age67_spec())
    assert list(design.columns) == ["stratum", "cluster"]
    assert not design.duplicated().any()
    # the invented design: eight strata of two clusters
    assert design.groupby("stratum")["cluster"].nunique().to_dict() == (
        dict.fromkeys(range(1, 9), 2)
    )


def test_a_registered_run_needs_the_committed_pinned_parameters(params):
    with pytest.raises(runner.TrackURunError, match="Census threshold"):
        runner._check_parameters(params, ap.REGISTERED_REAL)
    fake_capture = dataclasses.replace(
        params,
        thresholds=dataclasses.replace(
            params.thresholds,
            provenance={"kind": "census_capture", "sha256": "0" * 64},
        ),
    )
    # the capture is not pinned yet (THRESHOLDS_SHA256 is None), so no
    # threshold table can pass
    assert ap.THRESHOLDS_SHA256 is None
    with pytest.raises(runner.TrackURunError, match="pinned"):
        runner._check_parameters(fake_capture, ap.REGISTERED_REAL)
    invented_table = ap.LifeTable(
        name=ap.INVENTED_LIFE_TABLE,
        qx={sex: (0.1,) * 110 + (1.0,) for sex in ("male", "female")},
    )
    with pytest.raises(runner.TrackURunError, match="filed under"):
        runner._check_parameters(
            dataclasses.replace(
                params,
                life_tables={
                    **params.life_tables,
                    "nchs_2000": invented_table,
                },
            ),
            ap.REGISTERED_REAL,
        )
    runner._check_parameters(
        dataclasses.replace(
            params,
            life_tables={**params.life_tables, "nchs_2000": invented_table},
        ),
        ap.INVENTED,
    )
