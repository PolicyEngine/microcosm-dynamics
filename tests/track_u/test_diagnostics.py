"""Hand-computed cases for the F17 component diagnostics.

Every frame, rate and published figure here is INVENTED (the arithmetic is
written next to each assertion); none is a PSID value, an SSA statistic or
a comparator value.  The published-source readers are tested against the
committed files in ``test_diagnostics_published.py``.
"""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.uniform_cut_track_u import diagnostics as dg
from populace_dynamics.uniform_cut_track_u import invented


def test_weighted_quantile_by_hand():
    # equal weights: cumulative shares .25 .5 .75 1
    assert dg.weighted_quantile([40, 10, 30, 20], [1, 1, 1, 1], 0.5) == 20
    assert dg.weighted_quantile([10, 20, 30, 40], [1, 1, 1, 1], 0.25) == 10
    assert dg.weighted_quantile([10, 20, 30, 40], [1, 1, 1, 1], 0.9) == 40
    # weights 1, 1, 1, 5: cumulative 1, 2, 3, 8; half of 8 is 4 -> 40
    assert dg.weighted_quantile([10, 20, 30, 40], [1, 1, 1, 5], 0.5) == 40
    # a zero weight never decides: cumulative 0, 1, 2 -> the median is 10
    assert dg.weighted_quantile([5, 10, 20], [0, 1, 1], 0.5) == 10
    with pytest.raises(ValueError):
        dg.weighted_quantile([], [], 0.5)
    with pytest.raises(ValueError):
        dg.weighted_quantile([1], [1], 0.0)
    with pytest.raises(ValueError):
        dg.weighted_quantile([1, 2], [0, 0], 0.5)


def _rows(**columns) -> pd.DataFrame:
    frame = pd.DataFrame(columns)
    n = len(frame)
    defaults = {
        "observation_id": [f"o{i}" for i in range(n)],
        "person_id": list(range(n)),
        "birth_year": [1943] * n,
        "income_year": [2010] * n,
        "wave": [2011] * n,
        "sex": ["male"] * n,
        "married": [False] * n,
        "own_ssi": [0.0] * n,
        "head_ssi": [0.0] * n,
        "wife_ssi": [0.0] * n,
        "ofum_ssi": [0.0] * n,
        "family_ssi": [0.0] * n,
        "wealth_available": [True] * n,
        "wealth1": [0.0] * n,
        "wealth1_acc": [0.0] * n,
    }
    for key, value in defaults.items():
        if key not in frame:
            frame[key] = value
    return frame


def test_social_security_summary_by_hand():
    rows = _rows(
        member_role=["head", "wife", "ofum", "head"],
        own_identified=[True, True, False, True],
        own_ss=[12_000.0, 6_000.0, np.nan, 0.0],
        family_ss=[12_000.0, 6_000.0, 5_000.0, 0.0],
        weight=[1.0, 3.0, 2.0, 4.0],
    )
    published = {
        2009: {
            "retired_workers": {"average_monthly": 500.0},
            "aged_types_combined": {"average_monthly": 400.0},
        },
        2010: {
            "retired_workers": {"average_monthly": 625.0},
            "aged_types_combined": {"average_monthly": 500.0},
        },
    }
    entry = dg.social_security_summary(rows, published)["2010"]
    # own: recipients weigh 1 + 3 of the 8 head/wife weight
    assert entry["own_receipt_share"] == pytest.approx(0.5)
    # (12,000 * 1 + 6,000 * 3) / 4 = 7,500 a year, 625 a month
    assert entry["own_mean_annual_among_recipients"] == pytest.approx(7_500)
    assert entry["own_mean_monthly_among_recipients"] == pytest.approx(625)
    # family: 1 + 3 + 2 of the total weight 10
    assert entry["family_receipt_share"] == pytest.approx(0.6)
    prior = entry["published"]["december_prior_year"]
    assert prior["december"] == 2009
    assert prior["psid_over_ssa_retired_worker"] == pytest.approx(1.25)
    assert prior["psid_over_ssa_aged_types"] == pytest.approx(1.5625)
    same = entry["published"]["december_income_year"]
    assert same["psid_over_ssa_retired_worker"] == pytest.approx(1.0)
    assert entry["n_own_recipients"] == 2


def test_ssi_summary_by_hand():
    rows = _rows(
        member_role=["head", "head", "wife", "head", "ofum"],
        own_identified=[True, True, True, True, False],
        own_ss=[0.0] * 5,
        family_ss=[0.0] * 5,
        # 0: individual 8,000 > 7,200 (above); 1-2: a couple unit whose
        # head and wife each report 5,000: 10,000 < 10,800 (not above);
        # 3: no SSI; 4: OFUM, own amount not identified
        own_ssi=[8_000.0, 5_000.0, 5_000.0, 0.0, np.nan],
        head_ssi=[8_000.0, 5_000.0, 5_000.0, 0.0, 0.0],
        wife_ssi=[0.0, 5_000.0, 5_000.0, 0.0, 0.0],
        family_ssi=[8_000.0, 10_000.0, 10_000.0, 0.0, 700.0],
        weight=[1.0, 1.0, 1.0, 1.0, 2.0],
    )
    rates = {"individual": {2010: 600.0}, "couple": {2010: 900.0}}
    entry = dg.ssi_summary(rows, rates)["2010"]
    assert entry["federal_maximum_annual"] == {
        "individual": 7_200.0,
        "couple": 10_800.0,
    }
    assert entry["n_own_recipients"] == 3
    assert entry["own_receipt_share"] == pytest.approx(3 / 4)
    # family: 1 + 1 + 1 + 2 of 6
    assert entry["family_receipt_share"] == pytest.approx(5 / 6)
    assert entry["own_mean_annual_among_recipients"] == pytest.approx(6_000)
    assert entry["n_recipients_above_federal_maximum"] == 1
    assert entry["recipient_share_above_federal_maximum"] == pytest.approx(
        1 / 3
    )


def test_wealth1_summary_by_hand():
    rows = _rows(
        member_role=["head"] * 5,
        own_identified=[True] * 5,
        own_ss=[0.0] * 5,
        family_ss=[0.0] * 5,
        wealth1=[-500.0, 0.0, 1_000.0, 5_000.0, 0.0],
        wealth1_acc=[0.0, 1.0, 0.0, 0.0, 0.0],
        wealth_available=[True, True, True, True, False],
        weight=[1.0, 1.0, 1.0, 1.0, 9.0],
    )
    entry = dg.wealth1_summary(rows)["2010"]
    # the unavailable row (weight 9) is left out
    assert entry["n_observations"] == 4
    assert entry["share_at_or_below_zero"] == pytest.approx(0.5)
    assert entry["share_below_zero"] == pytest.approx(0.25)
    assert entry["share_imputed"] == pytest.approx(0.25)
    assert entry["quantiles"] == {
        "p10": -500.0,
        "p25": -500.0,
        "p50": 0.0,
        "p75": 1_000.0,
        "p90": 5_000.0,
    }


def test_component_rows_on_invented_inputs():
    inputs = invented.invented_age67_inputs()
    cohort = age67.build_age67_cohort(inputs)
    rows = dg.component_rows(cohort, inputs)
    assert len(rows) == len(cohort.observations)
    heads = rows["member_role"].eq("head")
    assert rows.loc[rows["member_role"].eq("ofum"), "own_ss"].isna().all()
    assert rows.loc[heads, "own_ss"].notna().all()
    # waves 2005 and 2007 have no invented wealth unless staged
    blocked = rows["wave"].isin([2005, 2007])
    assert not rows.loc[blocked, "wealth_available"].any()
    assert rows.loc[~blocked, "wealth_available"].all()


def test_institution_record_counts_on_invented_inputs():
    inputs = invented.invented_age67_inputs()
    counts = dg.institution_record_counts(inputs)
    for entry in counts.values():
        assert entry["n_fu_size_equals_in_family_records"] == (
            entry["n_families"]
        )
        assert entry["of_which_fu_size_equals_in_family_plus_institution"] == 0
    assert counts["2013"]["n_institution_records"] > 0


def test_the_diagnostics_module_loads_no_income_concept():
    """Importing the diagnostics loads neither the income concept, the
    tabulation, the runner nor the invented generator."""

    code = (
        "import sys\n"
        "import populace_dynamics.uniform_cut_track_u.diagnostics\n"
        "bad = [m for m in (\n"
        "    'populace_dynamics.estimates.adjusted_poverty',\n"
        "    'populace_dynamics.estimates.uniform_cut_tabulation',\n"
        "    'populace_dynamics.uniform_cut_track_u.runner',\n"
        "    'populace_dynamics.uniform_cut_track_u.invented',\n"
        ") if m in sys.modules]\n"
        "assert not bad, bad\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
