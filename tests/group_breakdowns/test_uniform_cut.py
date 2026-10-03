"""G4b INVENTED-data tests, with pinned parameter/category captures.

All observations, incomes and attribute reports are invented. Public
builders transitively read committed "data" / "external" definitions;
the static tier classifier therefore assigns this module artifact.
No real-data entry point or microdata reader is executed.
"""

from __future__ import annotations

import copy
from dataclasses import replace

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import group_breakdown as gb
from populace_dynamics.group_breakdowns import uniform_cut as groups
from populace_dynamics.group_breakdowns.common import (
    GroupBreakdownRefusal,
    assert_exact_cells,
)
from populace_dynamics.uniform_cut_track_u import invented, runner
from scripts.track_u_groups_invented import (
    invented_attribute_loader,
    invented_lifetime_inputs,
)


@pytest.fixture(scope="module")
def replay():
    inputs = invented.invented_age67_inputs(supplement_waves_staged=True)
    parameters = runner.committed_parameters(
        invented.invented_poverty_thresholds()
    )
    committed = runner.run_track_u(
        inputs, parameters, data_provenance=ap.INVENTED
    )
    retained = groups.reexecute_track_u(
        inputs,
        parameters,
        data_provenance=ap.INVENTED,
        original_pointer=None,
    )
    return inputs, parameters, committed, retained


def test_every_frozen_row_and_f17_cell_differential(replay):
    _, _, committed, retained = replay
    check = assert_exact_cells(
        {key: committed[key] for key in retained.evidence},
        retained.evidence,
    )
    assert check.compared_leaf_cells > 1000
    assert set(retained.rows) == set(groups.REGISTERED_ROWS)
    assert set(retained.rows["U0"].members.member_age) == {67}
    assert set(retained.rows["U1"].members.member_age) <= {66, 67, 68}


@pytest.mark.parametrize("row_id", ["U0", "U10-F"])
def test_mismatched_committed_cell_refuses_before_load_or_write(
    replay,
    row_id,
    tmp_path,
    monkeypatch,
):
    inputs, parameters, committed, retained = replay
    mismatched = copy.deepcopy(committed)
    mismatched["rows"][row_id]["tabulation"]["cells"][0]["delta"] += 1.0
    calls = []

    def forbidden_loader(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("group attribute loader called before refusal")

    monkeypatch.setattr(
        groups.ga, "load_group_attribute_inputs", forbidden_loader
    )
    monkeypatch.setattr(groups, "lifetime_frame", forbidden_loader)
    with pytest.raises(GroupBreakdownRefusal, match="committed cell"):
        groups.build_uniform_cut_groups(
            inputs,
            parameters,
            mismatched,
            data_provenance=ap.INVENTED,
            reexecute=lambda *args, **kwargs: retained,
        )
    assert calls == []
    assert list(tmp_path.iterdir()) == []


def test_input_digest_refuses_before_reexecution(replay):
    inputs, parameters, committed, _ = replay
    mismatched = copy.deepcopy(committed)
    mismatched["cohort_provenance"]["input_frames_sha256"] = "0" * 64

    def forbidden(*args, **kwargs):
        raise AssertionError("reexecuted mismatched inputs")

    with pytest.raises(GroupBreakdownRefusal, match="digest"):
        groups.build_uniform_cut_groups(
            inputs,
            parameters,
            mismatched,
            data_provenance=ap.INVENTED,
            reexecute=forbidden,
            attribute_loader=forbidden,
        )


def test_missing_registered_row_refuses_before_attributes(replay):
    inputs, parameters, committed, retained = replay
    rows = dict(retained.rows)
    rows.pop("U10-F")
    with pytest.raises(GroupBreakdownRefusal, match="every registered"):
        groups.build_uniform_cut_groups(
            inputs,
            parameters,
            committed,
            data_provenance=ap.INVENTED,
            reexecute=lambda *args, **kwargs: replace(retained, rows=rows),
            attribute_loader=lambda *args, **kwargs: pytest.fail("loaded"),
        )


def test_held_out_births_refuse_before_attributes(replay):
    inputs, parameters, committed, retained = replay
    rows = dict(retained.rows)
    members = rows["U0"].members.copy()
    members.loc[members.index[0], "birth_year"] = 1946
    rows["U0"] = replace(rows["U0"], members=members)
    with pytest.raises(GroupBreakdownRefusal, match="1936--1945"):
        groups.build_uniform_cut_groups(
            inputs,
            parameters,
            committed,
            data_provenance=ap.INVENTED,
            reexecute=lambda *args, **kwargs: replace(retained, rows=rows),
            attribute_loader=lambda *args, **kwargs: pytest.fail("loaded"),
        )


@pytest.fixture(scope="module")
def u0_breakdown(replay):
    inputs, _, _, retained = replay
    return groups.tabulate_row_groups(
        "U0",
        retained.rows["U0"],
        inputs=inputs,
        attribute_loader=invented_attribute_loader(inputs),
        lifetime_inputs=invented_lifetime_inputs(),
        data_provenance=ap.INVENTED,
        registration_pointer=None,
    )


def _dimension(result, key):
    return next(d for d in result["dimensions"] if d["key"] == key)


def test_g3_total_agrees_with_frozen_rates_se_and_floor(replay, u0_breakdown):
    original = replay[2]["rows"]["U0"]["tabulation"]["cells"][0]
    result = u0_breakdown["groups"]["adjusted"]
    total = _dimension(result, "total")["cells"][0]
    statistics = {s["statistic"]: s for s in total["statistics"]}
    for statistic, field in (
        (gb.POVERTY_RATE_CURRENT_LAW, "baseline_rate"),
        (gb.POVERTY_RATE_PROPOSAL, "reform_rate"),
        (gb.POVERTY_RATE_CHANGE, "delta"),
    ):
        assert statistics[statistic]["value"] == original[field]
        assert statistics[statistic]["uncertainty"]["design_se"] == (
            original["design_se"][field]
        )
        assert statistics[statistic]["uncertainty"]["floor"] == (
            original["floor"][field]
        )


def test_mint_order_and_unclassified_retained(u0_breakdown):
    result = u0_breakdown["groups"]["adjusted"]
    marital = _dimension(result, "marital_status")
    assert [c["label"] for c in marital["cells"]][:4] == [
        "Married",
        "Divorced",
        "Widowed",
        "Never married",
    ]
    assert marital["unclassified"]["n_rows"] > 0
    assert "benefit_type" in u0_breakdown["not_computed"]
    assert result["post_hoc_labels"] == list(groups.POSTHOC_LABELS)
    assert gb.INVENTED_DATA_LABEL in result["labels"]


def test_missing_lifetime_is_unavailable_and_sources_are_unmutated(replay):
    inputs, _, _, retained = replay
    members = retained.rows["U0"].members
    before = members.copy(deep=True)
    side, provenance = groups.lifetime_frame(members, inputs, None)
    assert side[list(groups.MEASURES)].isna().all().all()
    assert provenance["status"] == "not computed"
    assert_frame_equal(members, before)


def test_side_frame_must_be_sealed(replay):
    inputs, _, _, retained = replay
    loader = invented_attribute_loader(inputs)

    def tampered(person_ids, *, anchor_waves):
        attributes = loader(person_ids, anchor_waves=anchor_waves)
        attributes.frame.loc[0, "education_years"] = 1
        return attributes

    with pytest.raises(GroupBreakdownRefusal, match="seal"):
        groups._attribute_frame(retained.rows["U0"].members, tampered)


def test_declared_official_style_concept_is_separate(u0_breakdown):
    adjusted = u0_breakdown["groups"]["adjusted"]
    official = u0_breakdown["groups"]["reported_money_official_style"]
    assert official["upstream"]["concept"] == "reported_money_official_style"
    assert "householder" in official["upstream"]["official_style_caveat"]
    assert official["statistics"] == adjusted["statistics"]


def test_observation_plan_does_not_extend_to_u2():
    births = {
        birth
        for row in groups.REGISTERED_ROWS.values()
        for birth, _, _, _ in age67.observation_plan(row.age67_spec())
    }
    assert min(births) == 1936
    assert max(births) == 1945


def test_missing_side_person_refuses():
    with pytest.raises(GroupBreakdownRefusal, match="missing"):
        groups._join(
            pd.DataFrame({"person_id": [1, 2]}),
            pd.DataFrame({"person_id": [1], "attr": [0]}),
            "person_id",
        )


def test_report_rows_use_the_cleared_labels_and_leave_open_definitions_unavailable(
    u0_breakdown,
):
    report = groups.ga.load_schemes()["schemes"]["boomers2004"]
    scheme = groups._scheme("U0")
    keys = {
        "Race/Ethnicity": "race_ethnicity_report4",
        "Education": "education_report3",
        "Labor Force Experience": "labor_force_experience_report",
        "Lifetime Earnings (Own)": "lifetime_earnings_own",
        "Lifetime Earnings (Shared)": "lifetime_earnings_shared",
    }
    for row in report["row_groups"]:
        dimension = scheme.dimension(keys[row["group"]])
        assert list(dimension.labels) == row["labels"]
        assert (
            "a3978b683b4275424b6d12e9fe45f021fae277ccf9731a7883952564b6ed0384"
            in dimension.source
        )
        assert row["locator"] in dimension.source
    assert (
        u0_breakdown["report_builder_defaults"] == report["builder_defaults"]
    )
    result = u0_breakdown["groups"]["adjusted"]
    n_rows = _dimension(result, "total")["cells"][0]["counts"]["n_rows"]
    for key in (
        "education_report3",
        "labor_force_experience_report",
        "lifetime_earnings_own",
        "lifetime_earnings_shared",
    ):
        assert _dimension(result, key)["unclassified"]["n_rows"] == n_rows
        assert key in u0_breakdown["not_computed"]
