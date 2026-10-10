"""Comparison-memo rules (section 13, group "Memo"; section 10a).

Small cells, no-switcher wording, undefined cells and rounding endpoints.
Every printed value below is INVENTED; no Report value is used.
"""

from __future__ import annotations

import pytest

from populace_dynamics.uniform_cut_track_u2 import memo


def _cell(**overrides):
    cell = {
        "cell": "all",
        "defined": True,
        "n_observations": 120,
        "n_switchers": 9,
        "baseline_rate": 10.2,
        "reform_rate": 12.7,
        "delta": 2.5,
        "design_se": {
            "delta": {"se": 0.8},
            "baseline_rate": {"se": 1.1},
            "reform_rate": {"se": 1.2},
        },
        "floor": {
            "delta": {"defined": True, "mean": 0.6},
            "baseline_rate": {"defined": True, "mean": 0.9},
            "reform_rate": {"defined": False, "mean": None},
        },
    }
    cell.update(overrides)
    return cell


def test_interval_identifier_ends_in_open():
    assert memo.INTERVAL_ID.endswith("_open")
    assert memo.INTERVAL_ID != "whole_number_rounding_level_0_5_difference_1"


def test_level_and_change_intervals():
    assert memo.level_interval(10) == (9.5, 10.5)
    assert memo.change_interval(10, 13) == (2.0, 4.0)
    with pytest.raises(ValueError):
        memo.level_interval(10.4)
    with pytest.raises(ValueError):
        memo.change_interval(True, 3)


@pytest.mark.parametrize(
    "value, expected",
    [
        (2.0, "on the edge"),
        (4.0, "on the edge"),
        (2.0000001, "inside"),
        (3.9999999, "inside"),
        (1.9999999, "outside"),
        (4.0000001, "outside"),
    ],
)
def test_exact_change_endpoint_is_on_the_edge(value, expected):
    assert memo.classify(value, memo.change_interval(10, 13)) == expected


def test_unrounded_values_decide():
    # 2.04 displays as 2.0 but is inside; 1.96 displays as 2.0 and is out.
    interval = memo.change_interval(10, 13)
    assert memo.classify(2.04, interval) == "inside"
    assert memo.classify(1.96, interval) == "outside"


def test_memo_cell_gaps_and_ratios():
    line = memo.memo_cell(_cell(), printed_baseline=10, printed_reform=13)
    assert line["small_cell"] is False
    assert line["delta"]["gap"] == pytest.approx(-0.5)
    assert line["delta"]["classification"] == "inside"
    assert line["delta"]["gap_over_design_se"] == pytest.approx(-0.5 / 0.8)
    assert line["reform_rate"]["gap_over_floor"] is None
    assert line["baseline_rate"]["classification"] == "inside"


def test_small_cells_are_flagged():
    assert memo.memo_cell(_cell(n_observations=29), 10, 13)["small_cell"]
    assert not memo.memo_cell(_cell(n_observations=30), 10, 13)["small_cell"]


def test_no_switcher_cell_reports_uncertainty_not_estimable():
    line = memo.memo_cell(
        _cell(
            n_switchers=0,
            delta=0.0,
            reform_rate=10.2,
            design_se={
                "delta": {"se": 0.0},
                "baseline_rate": {"se": 1.1},
                "reform_rate": {"se": 1.1},
            },
        ),
        10,
        11,
    )
    assert line["delta"]["uncertainty"] == "uncertainty not estimable"
    assert line["delta"]["gap_over_design_se"] is None
    assert line["delta"]["model"] == 0.0
    assert line["baseline_rate"]["design_se"] == 1.1


def test_zero_uncertainty_never_divides():
    line = memo.memo_cell(
        _cell(
            design_se={
                "delta": {"se": 0.0},
                "baseline_rate": {"se": None},
                "reform_rate": {"se": 1.2},
            }
        ),
        10,
        13,
    )
    assert line["delta"]["gap_over_design_se"] is None
    assert line["baseline_rate"]["gap_over_design_se"] is None


def test_undefined_cells_keep_their_reason():
    line = memo.memo_cell(
        {
            "cell": "men_widowed",
            "defined": False,
            "n_observations": 0,
            "undefined_reason": "empty cell",
        },
        10,
        13,
    )
    assert line["defined"] is False
    assert line["undefined_reason"] == "empty cell"
    assert line["classification"] is None
    assert line["small_cell"] is True
