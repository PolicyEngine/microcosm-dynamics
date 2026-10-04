"""The EPUF floor builder's pipeline on synthetic panels.

No PSID and no EPUF: an invented panel in gate 1's panel shape runs
through the builder's own support, floor, partition and bite functions.
The artifact the builder writes from real data is bound separately.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.harness import epuf_gate as gate
from populace_dynamics.harness.epuf_cells import (
    COHORT_BANDS,
    WINDOW_YEARS,
    WindowArrays,
    cell_ids,
    transform,
)
from populace_dynamics.harness.panel import split_panel_by_person

ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    name = "build_epuf_gate_floors"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load_builder()
WAGE_BASES = builder.wage_bases()


def _invented_panel(n_persons=3000, seed=0):
    """An invented long panel in gate 1's panel shape (not PSID)."""
    rng = np.random.default_rng(seed)
    rows = []
    sexes = []
    for person in range(1, n_persons + 1):
        birth = int(rng.integers(1940, 1980))
        sexes.append(
            (person, rng.choice(["male", "female", "na"], p=[0.48, 0.5, 0.02]))
        )
        permanent = rng.normal(10.2, 0.6)
        last = int(rng.choice([2002, 2004, 2006, 2010, 2022]))
        skip = int(rng.choice([0, 0, 0, 2000]))
        for period in range(1998, last + 1, 2):
            if period == skip:
                continue
            age = period + 1 - birth
            if not 25 <= age <= 59:
                continue
            earnings = (
                0.0
                if rng.random() < 0.1
                else float(np.exp(permanent + rng.normal(0, 0.5)))
            )
            rows.append((person, period, earnings, age, rng.uniform(0.5, 2)))
    panel = pd.DataFrame(
        rows, columns=["person_id", "period", "earnings", "age", "weight"]
    )
    sex = pd.DataFrame(sexes, columns=["person_id", "sex"])
    return panel, sex


@pytest.fixture(scope="module")
def support():
    panel, sex = _invented_panel()
    frame, universe, counts = builder.support_from_panel(panel, sex)
    return panel, sex, frame, universe, counts


def test_holdout_mask_is_the_gate_one_split_function():
    universe = np.arange(1000, 3000, 3)
    ids = pd.DataFrame({"person_id": universe})
    for seed in (0, 7, 1019):
        for fraction in (0.2, 0.5):
            left, right = split_panel_by_person(
                ids, "person_id", fraction=fraction, seed=seed
            )
            mask = builder.holdout_mask(universe, seed=seed, fraction=fraction)
            assert set(left["person_id"]) == set(universe[mask])
            assert set(right["person_id"]) == set(universe[~mask])


def test_support_applies_every_rule(support):
    panel, sex, frame, universe, counts = support
    assert counts["n_universe_persons"] == panel["person_id"].nunique()
    assert len(frame) == counts["n_support_persons"] > 200
    assert (
        counts["n_present_all_four_years"]
        >= counts["n_and_anchor_2006_or_later"]
        >= counts["n_and_sex_coded"]
        >= counts["n_support_persons"]
    )
    periods = panel.groupby("person_id")["period"].agg(set)
    anchor = panel.groupby("person_id")["period"].max()
    coded = sex.set_index("person_id")["sex"]
    for person in frame["person_id"]:
        assert set(WINDOW_YEARS) <= periods[person]
        assert anchor[person] >= builder.MIN_ANCHOR_PERIOD
        assert coded[person] in ("male", "female")
    low = min(a for a, _ in COHORT_BANDS.values())
    high = max(b for _, b in COHORT_BANDS.values())
    assert frame["birth_year"].between(low, high).all()
    assert set(frame["sex"]) == {"men", "women"}
    assert sum(counts["by_sex_and_band"].values()) == len(frame)


def test_support_weight_is_the_2004_row_weight(support):
    panel, _, frame, _, _ = support
    weights = panel[panel["period"] == 2004].set_index("person_id")["weight"]
    assert (
        frame["weight"].to_numpy()
        == weights.reindex(frame["person_id"]).to_numpy()
    ).all()


def test_support_earnings_are_in_epuf_units(support):
    panel, _, frame, _, _ = support
    for year in WINDOW_YEARS:
        raw = (
            panel[panel["period"] == year]
            .set_index("person_id")["earnings"]
            .reindex(frame["person_id"])
            .to_numpy()
        )
        assert (
            frame[f"e{year}"].to_numpy() == builder.epuf_measure(raw, year)
        ).all()


def test_support_refuses_conflicting_sex_and_duplicate_rows(support):
    panel, sex, *_ = support
    conflicted = pd.concat(
        [sex, pd.DataFrame({"person_id": [1], "sex": ["male"]})]
    )
    conflicted.loc[conflicted["person_id"] == 1, "sex"] = ["male", "female"]
    with pytest.raises(ValueError, match="two coded sexes"):
        builder.support_from_panel(panel, conflicted)
    with pytest.raises(ValueError, match="duplicate person-periods"):
        builder.support_from_panel(pd.concat([panel, panel.head(1)]), sex)


@pytest.fixture(scope="module")
def built(support):
    _, _, frame, universe, _ = support
    arrays = WindowArrays(frame, wage_bases=WAGE_BASES)
    # Use the support's own values as the "EPUF" reference, so that every
    # bridge is zero and the partition depends on noise and events alone.
    reference = {cell_id: c.value for cell_id, c in arrays.cells().items()}
    sd = dict.fromkeys(reference, 0.0)
    out = builder.build_floors(
        arrays, universe, reference, sd, n_replicates=12
    )
    return frame, universe, arrays, out


def test_floors_cover_every_cell_and_partition_it_once(built):
    _, _, _, out = built
    assert sorted(out["cells"]) == sorted(cell_ids())
    partition = out["gate_partition"]
    assert set(partition["gated"]) | set(partition["report_only"]) == set(
        cell_ids()
    )
    assert not set(partition["gated"]) & set(partition["report_only"])
    assert partition["n_gated"] == len(partition["gated"])
    assert set(out["registered"]) == set(partition["gated"])


def test_floor_values_follow_the_registered_algebra(built):
    _, _, _, out = built
    for cell_id, cell in out["cells"].items():
        floor = cell["floor"]
        if floor["tolerance"] is None:
            assert cell["eligibility"] == "undefined_on_some_split"
            continue
        replicates = floor["replicates"]
        assert len(replicates) == 12
        assert None not in replicates
        assert floor["tolerance"] == gate.tolerance(replicates)
        assert floor["realized_sigma"] == pytest.approx(
            gate.realized_sigma(replicates)
        )
        bridge = cell["bridge_psid_minus_epuf"]
        assert bridge == pytest.approx(
            transform(cell_id, cell["psid_value"])
            - transform(cell_id, cell["epuf_value"])
        )
        assert (cell["lower"], cell["upper"]) == gate.hull(
            bridge, floor["tolerance"]
        )
        expected = gate.demotion_reason(
            gate.CellFloor(
                cell_id,
                True,
                cell["min_events"],
                bridge,
                floor["tolerance"],
                floor["realized_sigma"],
                cell["epuf_sampling_sd"],
            )
        )
        assert cell["eligibility"] == (expected or "eligible")
        if cell["gated"]:
            assert expected is None
            assert cell["minimum_detectable_gap_80"] <= cell["cap"]


def test_real_data_pass_as_their_own_training_copy(built):
    _, _, _, out = built
    if out["gate_partition"]["gated"]:
        assert out["training_copy"]["pass"]
    oc = out["faithful_candidate_oc"]
    assert 0.0 <= oc["analytic_product"] <= 1.0


def test_build_floors_is_deterministic(built):
    frame, universe, arrays, out = built
    reference = {c: v["epuf_value"] for c, v in out["cells"].items()}
    again = builder.build_floors(
        arrays,
        universe,
        reference,
        dict.fromkeys(reference, 0.0),
        n_replicates=12,
    )
    assert again["cells"] == out["cells"]
    assert again["gate_partition"] == out["gate_partition"]


def test_a_large_bridge_demotes_instead_of_widening_the_gate(built):
    frame, universe, arrays, out = built
    reference = {c: v["epuf_value"] for c, v in out["cells"].items()}
    shifted = dict(reference)
    shifted["r6.men"] = reference["r6.men"] + 0.3
    shifted["r6.women"] = reference["r6.women"] + 0.3
    for band in COHORT_BANDS:
        shifted[f"r6.men.{band}"] = reference[f"r6.men.{band}"] + 0.3
    moved = builder.build_floors(
        arrays, universe, shifted, dict.fromkeys(shifted, 0.0), n_replicates=12
    )
    assert "r6.men" not in moved["gate_partition"]["gated"]
    assert moved["cells"]["r6.men"]["eligibility"] in (
        "bridge_exceeds_budget",
        "noise_exceeds_cap",
    )


def test_perturbations_change_only_the_early_years(support):
    _, _, frame, _, _ = support
    rng = np.random.default_rng(0)
    for perturbed in (
        builder.perturb_persistence(frame, rng, 0.5),
        builder.perturb_sex_blind(frame, rng, same_sex=False),
        builder.perturb_sex_blind(frame, rng, same_sex=True),
        builder.perturb_top_tail(frame, rng),
        builder.perturb_participation(frame, rng),
    ):
        fixed = ["person_id", "sex", "birth_year", "weight", "e2004"]
        pd.testing.assert_frame_equal(perturbed[fixed], frame[fixed])
        assert len(perturbed) == len(frame)
        for year in WINDOW_YEARS:
            assert perturbed[f"e{year}"].between(0, WAGE_BASES[year]).all()


def test_participation_loss_only_removes_earnings(support):
    _, _, frame, _, _ = support
    perturbed = builder.perturb_participation(frame, np.random.default_rng(1))
    for year in WINDOW_YEARS[:3]:
        before, after = frame[f"e{year}"], perturbed[f"e{year}"]
        changed = before != after
        assert (after[changed] == 0).all()
        assert 0 < changed.mean() < 0.1


def test_top_tail_compression_never_raises_a_value(support):
    _, _, frame, _, _ = support
    perturbed = builder.perturb_top_tail(frame, np.random.default_rng(2))
    for year in WINDOW_YEARS[:3]:
        assert (perturbed[f"e{year}"] <= frame[f"e{year}"]).all()


def test_same_sex_control_keeps_donors_within_sex(support):
    _, _, frame, _, _ = support
    # Tag every early-year value with its owner's sex, then permute.
    tagged = frame.copy()
    marker = np.where(tagged["sex"] == "men", 1.0, 2.0)
    for year in WINDOW_YEARS[:3]:
        tagged[f"e{year}"] = marker
    control = builder.perturb_sex_blind(
        tagged, np.random.default_rng(3), same_sex=True
    )
    pooled = builder.perturb_sex_blind(
        tagged, np.random.default_rng(3), same_sex=False
    )
    assert (control["e1998"].to_numpy() == marker).all()
    assert (pooled["e1998"].to_numpy() != marker).any()


def test_bite_demonstrations_report_every_perturbation(built):
    frame, universe, _, out = built
    bites = builder.bite_demonstrations(frame, universe, out["registered"])
    assert {
        "bd1_persistence_loss_0.10",
        "bd1_persistence_loss_0.05",
        "bd2_sex_blind_donors",
        "bd2c_same_sex_donors_control",
        "bd3_top_tail_compression",
        "bd4_participation_loss",
    } <= set(bites)
    for family, row in bites["requirements"].items():
        assert row["bite"] == builder.BITE_REQUIREMENT[family]
        assert row["met"] == (row["fail_share"] >= 0.90)
    assert bites["pause"] == any(
        not row["met"] for row in bites["requirements"].values()
    )


# --- from candidate panels to a report -----------------------------------


def _holdout_panels(panel, universe):
    return {
        seed: panel[
            panel["person_id"].isin(
                universe[
                    builder.holdout_mask(
                        universe, seed=seed, fraction=gate.HOLDOUT_FRACTION
                    )
                ]
            )
        ]
        for seed in gate.GATE_SEEDS
    }


def test_a_candidate_equal_to_the_real_panel_reports_the_real_values(
    support, built
):
    from populace_dynamics.harness.epuf_run import report_candidate

    panel, _, frame, universe, _ = support
    _, _, _, out = built
    report = report_candidate(
        _holdout_panels(panel, universe), frame, out["cells"]
    )
    # A report, not a verdict: every cell, and no pass or fail anywhere.
    assert report["status"] == "report_only"
    assert sorted(report["cells"]) == sorted(cell_ids())
    assert "pass" not in report
    assert all("pass" not in cell for cell in report["cells"].values())
    for cell_id, cell in out["training_copy"]["cells"].items():
        assert report["cells"][cell_id]["gap_from_epuf"] == pytest.approx(
            cell["gap_from_epuf"], abs=1e-12
        )
    for seed, values in out["real_gate_seed_values"].items():
        for cell_id, value in values.items():
            got = report["cells"][cell_id]["per_seed_values"][int(seed)]
            if value is None:
                assert np.isnan(got)
            else:
                assert got == pytest.approx(value, abs=1e-12)


def test_report_splits_each_gap_into_model_and_source_terms(support, built):
    from populace_dynamics.harness.epuf_run import report_candidate

    panel, _, frame, universe, _ = support
    _, _, _, out = built
    report = report_candidate(
        _holdout_panels(panel, universe), frame, out["cells"]
    )
    checked = 0
    for cell_id, cell in report["cells"].items():
        floor = out["cells"][cell_id]
        if floor["psid_value"] is None or np.isnan(cell["gap_from_epuf"]):
            continue
        assert cell["source_term_psid_minus_epuf"] == pytest.approx(
            floor["bridge_psid_minus_epuf"], abs=1e-12
        )
        assert cell["gap_from_epuf"] == pytest.approx(
            cell["source_term_psid_minus_epuf"]
            + cell["model_term_candidate_minus_psid"],
            abs=1e-12,
        )
        assert len(cell["per_seed_values"]) == len(gate.GATE_SEEDS)
        checked += 1
    assert checked >= 10


def test_report_requires_exactly_the_gate_seeds(support, built):
    from populace_dynamics.harness.epuf_run import report_candidate

    panel, _, frame, universe, _ = support
    _, _, _, out = built
    panels = _holdout_panels(panel, universe)
    del panels[19]
    with pytest.raises(ValueError, match="seeds 0-19"):
        report_candidate(panels, frame, out["cells"])


def test_a_candidate_missing_a_window_row_is_refused(support):
    from populace_dynamics.harness.epuf_run import candidate_window_cells

    panel, _, frame, universe, _ = support
    holdout = _holdout_panels(panel, universe)[0]
    person = frame.loc[
        frame["person_id"].isin(holdout["person_id"]), "person_id"
    ].iloc[0]
    broken = holdout[
        ~((holdout["person_id"] == person) & (holdout["period"] == 2000))
    ]
    with pytest.raises(ValueError, match="lacks a generated row"):
        candidate_window_cells(broken, frame)
    with pytest.raises(ValueError, match="holds no support person"):
        candidate_window_cells(holdout.iloc[0:0], frame)


def test_generated_earnings_change_the_score_but_not_the_support(
    support, built
):
    from populace_dynamics.harness.epuf_run import candidate_window_cells

    panel, _, frame, universe, _ = support
    holdout = _holdout_panels(panel, universe)[0]
    real = candidate_window_cells(holdout, frame)
    shuffled = holdout.copy()
    rng = np.random.default_rng(5)
    shuffled["earnings"] = rng.permutation(shuffled["earnings"].to_numpy())
    generated = candidate_window_cells(shuffled, frame)
    assert set(generated) == set(real)
    assert generated["r6.men"] != pytest.approx(real["r6.men"])
