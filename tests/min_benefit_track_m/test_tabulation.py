"""The Track M tabulation (plan item M8) on INVENTED rows.

Every row here is **INVENTED**: no PSID value and no comparator value.
Each share is computed by hand beside it.  The provenance guard is
exercised on in-memory rows only; nothing reads a PSID file.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.estimates import uniform_cut_tabulation as tu
from populace_dynamics.min_benefit_track_m import (
    COVERED_EARNINGS_DISCLOSURE,
    OUTPUT_LABELS,
    specification,
)
from populace_dynamics.min_benefit_track_m import tabulation as tab

POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)


def rows(kind: str = "invented") -> pd.DataFrame:
    """Six INVENTED persons in four family units and two strata.

    Weights 1, 2, 3, 4, 5, 6; sexes F, F, M, M, F, unknown; option 2
    receipt for persons 1, 3 and 6.
    """

    frame = pd.DataFrame(
        {
            "person_id": [f"P{i}" for i in range(1, 7)],
            "family_unit_id": ["F1", "F1", "F2", "F3", "F4", "F4"],
            "weight": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "sex": ["female", "female", "male", "male", "female", "unknown"],
            "stratum": [1, 1, 1, 2, 2, 2],
            "cluster": [1, 1, 2, 1, 2, 2],
            "receives_2": [True, False, True, False, False, True],
            "receives_3": [True, True, True, False, False, True],
            "receives_4": [True, True, True, True, False, True],
            "receives_5": [True, True, True, True, True, True],
        }
    )
    frame.attrs["provenance_kind"] = kind
    return frame


DESIGN = pd.DataFrame(
    {"stratum": [1, 1, 2, 2, 3, 3], "cluster": [1, 2, 1, 2, 1, 2]}
)


def cell(result, option, row):
    return next(
        c for c in result["cells"] if (c["option"], c["row"]) == (option, row)
    )


def test_shares_by_hand():
    result = tab.tabulate_track_m(
        rows(), row_id="MS0", data_provenance="invented", design=DESIGN
    )
    # All: (1 + 3 + 6) / 21 = 47.62%; the unknown-sex person counts here.
    assert cell(result, 2, "all")["share_percent"] == pytest.approx(
        100 * 10 / 21
    )
    # Women: persons 1, 2, 5 -> 1 / 8; men: persons 3, 4 -> 3 / 7.
    assert cell(result, 2, "women")["share_percent"] == pytest.approx(12.5)
    assert cell(result, 2, "men")["share_percent"] == pytest.approx(
        100 * 3 / 7
    )
    assert cell(result, 5, "all")["share_percent"] == pytest.approx(100.0)
    assert cell(result, 2, "all")["headline"]
    assert sum(c["headline"] for c in result["cells"]) == 1
    assert len(result["cells"]) == 12
    assert result["n_column"]["all"] == {"unweighted": 6, "weighted": 21.0}
    assert result["n_column"]["women"]["unweighted"] == 3
    assert result["n_column"]["scored"] is False
    # Y3: women 3 / 8 = 37.5%, men 3 / 7; rates 0.375 / 0.4286 = 0.875;
    # weighted counts 3 / 3 = 1.
    y3 = result["y3_option_3_women_to_men"]
    assert y3["ratio_of_rates"] == pytest.approx((3 / 8) / (3 / 7))
    assert y3["ratio_of_weighted_counts"] == pytest.approx(1.0)
    assert y3["scored"] is False


def test_labels_disclosure_and_json():
    result = tab.tabulate_track_m(
        rows(), row_id="MS0", data_provenance="invented", design=DESIGN
    )
    assert result["labels"][0] == tab.INVENTED_DATA_LABEL
    assert result["labels"][1:] == list(OUTPUT_LABELS)
    assert result["disclosure"] == COVERED_EARNINGS_DISCLOSURE
    json.dumps(result, allow_nan=False)


def test_design_se_matches_the_track_u_helper():
    frame = rows()
    result = tab.tabulate_track_m(
        frame, row_id="MS0", data_provenance="invented", design=DESIGN
    )
    normalized = frame.reset_index(drop=True)
    clusters = tu._design_clusters(DESIGN)
    expected = tu._design_se(
        normalized,
        np.ones(len(frame), dtype=bool),
        normalized["receives_2"].to_numpy().astype(float),
        clusters,
    )
    assert cell(result, 2, "all")["design_se"] == expected
    assert result["uncertainty"]["design_se"]["n_clusters"] == 6
    # strata of the frame without a row still count (full sample design)
    assert result["uncertainty"]["design_se"]["n_strata"] == 3
    # Women: persons 1, 2, 5 (clusters (1, 1), (1, 1), (2, 2)); option 2
    # receipt for person 1 only.  By hand: r = 1 / 8; z = w (y - r) / 8
    # summed by cluster: (1, 1): (1 (7/8) + 2 (-1/8)) / 8 = 5/64;
    # (2, 2): 5 (-1/8) / 8 = -5/64; every other frame cluster 0.  Stratum
    # 1: values 5/64 and 0, stratum 2: 0 and -5/64, stratum 3: 0 and 0;
    # each stratum with two clusters adds 2 (d/2)^2 x 2 = d^2, so the
    # variance is 2 (5/64)^2 and the SE 100 sqrt(2) 5 / 64 points.
    women = cell(result, 2, "women")["design_se"]
    assert women["se"] == pytest.approx(100 * 2**0.5 * 5 / 64)
    assert women["n_strata"] == 3 and women["n_singleton_strata"] == 0


def test_floors_follow_the_track_u_pattern():
    result = tab.tabulate_track_m(
        rows(), row_id="MS0", data_provenance="invented", design=DESIGN
    )
    uncertainty = result["uncertainty"]
    assert uncertainty["floor_seeds"] == [0, 1, 2, 3, 4]
    assert uncertainty["floor_fraction"] == 0.5
    assert uncertainty["floor_split_unit"] == tab.FLOOR_SPLIT_UNIT
    assert uncertainty["registered"] == tab.UNCERTAINTY
    assert tab.UNCERTAINTY["floor"]["seeds"] == list(tu.DEFAULT_FLOOR_SEEDS)
    assert tab.UNCERTAINTY["floor"]["fraction"] == tu.FLOOR_FRACTION
    assert tab.UNCERTAINTY["floor"]["min_usable_seeds"] == (tu.MIN_FLOOR_SEEDS)
    assert result["statistic"] == tab.STATISTIC
    # the copies the specification check compares are copies
    copied = tab.uncertainty_block()
    copied["floor"]["seeds"].append(9)
    assert tab.UNCERTAINTY["floor"]["seeds"] == [0, 1, 2, 3, 4]
    floor = cell(result, 2, "all")["floor"]
    assert floor["n_seeds"] + len(floor["dropped_seeds"]) == 5
    if floor["defined"]:
        assert floor["min"] <= floor["mean"] <= floor["max"]


def test_each_seed_splits_whole_family_units():
    """The floor's halves recompute the share on person-disjoint halves of
    whole family units; each seed's gap is |a - b| of the two halves."""

    frame = rows()
    result = tab.tabulate_track_m(
        frame, row_id="MS0", data_provenance="invented", design=DESIGN
    )
    units = pd.DataFrame(
        {"split_unit": tu.floor_split_units(frame.reset_index(drop=True))}
    )
    gaps = []
    for seed in (0, 1, 2, 3, 4):
        side_a, _ = tab.split_panel_by_person(
            units, "split_unit", fraction=0.5, seed=seed
        )
        in_a = np.zeros(len(frame), dtype=bool)
        in_a[side_a.index.to_numpy()] = True
        halves = []
        for side in (in_a, ~in_a):
            weight = frame["weight"].to_numpy()[side]
            receiving = frame["receives_2"].to_numpy()[side]
            if side.any():
                halves.append(100 * weight[receiving].sum() / weight.sum())
        if len(halves) == 2:
            gaps.append(abs(halves[0] - halves[1]))
        # family unit F1 (persons 1 and 2) and F4 (5 and 6) never split
        for unit in ("F1", "F4"):
            members = frame["family_unit_id"].eq(unit).to_numpy()
            assert len(set(in_a[members])) == 1
    floor = cell(result, 2, "all")["floor"]
    assert floor["values"] == pytest.approx(gaps)


@pytest.mark.parametrize(
    ("kind", "provenance", "pointer", "match"),
    [
        ("psid_files", "invented", None, "cannot be tabulated as invented"),
        ("invented", "registered_real", None, "registration pointer"),
        (
            "psid_files",
            "registered_real",
            "https://github.com/PolicyEngine/microcosm-dynamics/issues/42",
            "registration pointer",
        ),
        (
            "psid_files",
            "registered_real",
            POINTER.replace("/42#", "/420#"),
            "registration pointer",
        ),
        ("invented", "registered_real", POINTER, "contradicts"),
        # the committed draft (m1-draft-2) authorizes no real-data run
        ("psid_files", "registered_real", POINTER, "does not authorize"),
        (None, "invented", None, "must say so"),
        ("invented", "published", None, "data_provenance"),
    ],
)
def test_the_provenance_guard_refuses(kind, provenance, pointer, match):
    frame = rows(kind)
    if kind is None:
        frame.attrs.pop("provenance_kind")
    with pytest.raises(tab.TrackMTabulationError, match=match):
        tab.tabulate_track_m(
            frame,
            row_id="MS0",
            data_provenance=provenance,
            registration_pointer=pointer,
            design=DESIGN,
        )


def test_the_guard_needs_a_ratified_unblocked_block_and_every_label():
    ratified = json.loads(json.dumps(specification.m1_parameter_block()))
    ratified["status"], ratified["version"] = (
        "ratified_frozen",
        "m1-ratified-1",
    )
    # A ratified copy that still lists the unbuilt readers is refused ...
    with pytest.raises(tab.TrackMTabulationError, match="blocked by"):
        tab.check_provenance(
            rows("psid_files"),
            data_provenance="registered_real",
            registration_pointer=POINTER,
            specification=ratified,
        )
    ratified["blocked_by"] = []
    # ... and with a ratified, unblocked copy the guard lets PSID-kind rows
    # through (checked on the guard alone: these rows are invented).
    tab.check_provenance(
        rows("psid_files"),
        data_provenance="registered_real",
        registration_pointer=POINTER,
        specification=ratified,
    )
    # A registered tabulation keeps the registered floor seeds.
    with pytest.raises(tab.TrackMTabulationError, match="floor seeds"):
        tab.tabulate_track_m(
            rows("psid_files"),
            row_id="MS0",
            data_provenance="registered_real",
            registration_pointer=POINTER,
            specification=ratified,
            design=DESIGN,
            floor_seeds=(0, 1, 2),
        )
    with pytest.raises(tab.TrackMTabulationError, match="invented label"):
        tab.check_provenance(
            rows("psid_files"),
            data_provenance="registered_real",
            registration_pointer=POINTER,
            labels=[*OUTPUT_LABELS, tab.INVENTED_DATA_LABEL],
            specification=ratified,
        )
    with pytest.raises(tab.TrackMTabulationError, match="labels"):
        tab.check_provenance(
            rows(),
            data_provenance="invented",
            registration_pointer=None,
            labels=OUTPUT_LABELS[:2],
        )


def test_malformed_rows_are_refused():
    frame = rows()
    with pytest.raises(tab.TrackMTabulationError, match="duplicate"):
        doubled = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
        doubled.attrs["provenance_kind"] = "invented"
        tab.tabulate_track_m(
            doubled, row_id="MS0", data_provenance="invented", design=DESIGN
        )
    odd = rows()
    odd["receives_3"] = odd["receives_3"].astype(int)
    with pytest.raises(tab.TrackMTabulationError, match="boolean"):
        tab.tabulate_track_m(
            odd, row_id="MS0", data_provenance="invented", design=DESIGN
        )
    outside = rows()
    outside.loc[0, "stratum"] = 9
    with pytest.raises(tab.TrackMTabulationError, match="design frame"):
        tab.tabulate_track_m(
            outside, row_id="MS0", data_provenance="invented", design=DESIGN
        )
    # a malformed design frame is a Track M error, not Track U's
    with pytest.raises(tab.TrackMTabulationError, match="design lacks"):
        tab.tabulate_track_m(
            rows(),
            row_id="MS0",
            data_provenance="invented",
            design=DESIGN[["stratum"]],
        )
    with pytest.raises(tab.TrackMTabulationError, match="seeds"):
        tab.tabulate_track_m(
            rows(),
            row_id="MS0",
            data_provenance="invented",
            design=DESIGN,
            floor_seeds=(1, 1),
        )
    with pytest.raises(tab.TrackMTabulationError, match="sex"):
        odd_sex = rows()
        odd_sex.loc[0, "sex"] = "F"
        tab.tabulate_track_m(
            odd_sex, row_id="MS0", data_provenance="invented", design=DESIGN
        )


def test_an_empty_sex_cell_is_reported_not_raised():
    only_women = rows().iloc[:2].copy()
    only_women.attrs["provenance_kind"] = "invented"
    result = tab.tabulate_track_m(
        only_women, row_id="MS0", data_provenance="invented", design=DESIGN
    )
    men = cell(result, 2, "men")
    assert not men["defined"] and men["undefined_reason"] == "empty cell"
    assert "design_se" not in men
    assert result["y3_option_3_women_to_men"]["defined"] is False
    json.dumps(result, allow_nan=False)
