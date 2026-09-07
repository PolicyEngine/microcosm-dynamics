"""Tests for the mortality gate floors v1 artifact
(runs/mortality_gate_floors_v1.json): the THRESHOLD-BINDING derivation
from the verified floor basis runs/mortality_floors_v3.json.

The artifact is a REPORTED ANCHOR (reads no gate, changes no gate,
ratifies nothing): it derives the gate-schema blocks the packet's
section-1 draft needs -- the floor block, cell stability, the partition
under both eligibility rules (R3), k-sensitivity with the faithful OC
(R2), the anchor checks and the anchor operating characteristic with the
remedies priced (R5), the 85+ evidence (R4), the draw stream (R9), the
restricted-before-split perturbation (R10), the teeth table (R11), the
wording audit (R12), referee A's three additions -- and carries the DRAFT
``gate_mortality`` block as a string. Every ruling is FILED and PRICED;
none is made.

Two tiers, mirroring ``tests/test_mortality_floors_v3.py``:

* Always-runnable tests touching only committed files. Every derived
  number recomputes from the v3 artifact's own PER-SEED record (the
  floor block, the tolerances at every k, the eligibility partitions
  from the death counts, the OC from the tolerances and sigmas, the
  anchor margins from the per-half hazard vectors, the anchor OC from
  the margins, the teeth from the declared-window hazards, the 85+
  shares from the declared-window events, the stability clause from
  v3's bootstrap); the PSID-built blocks (R10, the censoring bracket,
  the gate-seed frames) are checked for internal consistency; THIS
  artifact and its source are byte-pinned (``GATE_V1_COMMITTED``,
  ``V3_COMMITTED``); both builders are sha-pinned; the draft block
  parses, its digest recomputes, its placeholders are present and the
  R12 words are absent; ``gates.yaml`` is checked under the PRE-LOCK
  MARKER ``GATE_MORTALITY_BLOCK_LANDED``.
* PSID-gated reproduction pins (skipped when the PSID individual file
  is absent) that rebuild the pinned frame and reproduce the
  restricted-before-split floor at ALL 100 seeds, the censoring bracket
  cell by cell, and the gate-seed scoring frames' person-id digests --
  with ``populace.fit`` never imported.

The derivation bindings themselves (tolerance == round(mean + 3*sd, 3)
from v3's per-seed values, the OC, the partition, the draw stream, the
perturbation test) live in ``tests/test_gates_derivations.py`` on the
gate_m4 pattern; this file pins the artifact and its internal
consistency.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "mortality_gate_floors_v1.json"
V3_ARTIFACT = ROOT / "runs" / "mortality_floors_v3.json"
GATES = ROOT / "gates.yaml"
SCRIPTS = ROOT / "scripts"
BUILDER = SCRIPTS / "build_mortality_gate_floors_v1.py"
BUILDER_V3 = SCRIPTS / "build_mortality_floors_v3.py"

#: The VERIFIED floor basis (floors v4 at 62d01d6). Must not move.
V3_COMMITTED = (
    2_711_564,
    "8998bca2d7026926cc44a199087810bc654863c12b2d14466ce0ff73f95e0776",
)
#: THIS artifact's committed bytes (size, sha256), re-stated in the same
#: commit as any rebuild (the gate-3 digest-pin precedent).
GATE_V1_COMMITTED = (
    284_425,
    "aa97e0e363ee9be7ec25fb5bad0b943e8371032573c9612e1b35d950accf1260",
)
#: PRE-LOCK MARKER (referee A addition (iii)). False until the commit
#: that inserts the gate_mortality block flips it -- in every file the
#: artifact's flip_plan names, in the same commit.
GATE_MORTALITY_BLOCK_LANDED = False

T_MAX = math.log(1.5)
CELLS_GATED = ["75-84|female", "75-84|male", "85+|female", "85+|male"]
REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()
needs_real_ind = pytest.mark.skipif(
    not (REAL_DATA / "ind2023er").is_dir(),
    reason="PSID ind2023er not staged",
)


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def _v3() -> dict:
    return json.loads(V3_ARTIFACT.read_text())


def _head(v3: dict) -> dict:
    return v3["internal_noise_floor"]["conventions"]["pinned_narrow_midpoint"][
        "universes"
    ]["declared_1997_plus"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _import_builder():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_mortality_gate_floors_v1 as builder

    return builder


def _block(art: dict) -> dict:
    text = art["draft_gates_yaml_fragment"]["text"]
    return yaml.safe_load("gates:\n" + text)["gates"]["gate_mortality"]


# --------------------------------------------------------------------------
# Framing and pins
# --------------------------------------------------------------------------
def test_schema_reported_anchor_and_nothing_ruled():
    art = _artifact()
    assert art["schema_version"] == "mortality_gate_floors.v1"
    assert art["run"] == "mortality_gate_floors_v1"
    assert art["reported_anchor_not_gated"] is True
    assert art["ceremony"]["gates_yaml_untouched"] is True
    dnd = " ".join(art["does_not_do"])
    for phrase in (
        "edit gates.yaml",
        "score a candidate",
        "make any ruling",
        "for writing",
        "move any floor value",
    ):
        assert phrase in dnd, phrase
    assert art["faithful_candidate_oc"]["binding_surface"] == "<RULING R4>"


def test_artifact_bytes_are_pinned_to_the_committed_digest():
    assert ARTIFACT.stat().st_size == GATE_V1_COMMITTED[0]
    assert _sha(ARTIFACT) == GATE_V1_COMMITTED[1]


def test_source_floor_is_the_verified_v3_read_by_path():
    art = _artifact()
    assert V3_ARTIFACT.stat().st_size == V3_COMMITTED[0]
    assert _sha(V3_ARTIFACT) == V3_COMMITTED[1]
    src = art["source_floor"]
    assert src["path"] == "runs/mortality_floors_v3.json"
    assert (src["size_bytes"], src["sha256"]) == V3_COMMITTED
    assert src["schema_version"] == "mortality_floors.v3"
    assert (
        src["built_on_commit"]
        == _v3()["revision_pins"]["populace_dynamics_sha"]
    )
    assert (
        "VERIFIED" in src["verified_by"]
        or "mortality-v4-verify" in src["verified_by"]
    )
    pins = art["revision_pins"]
    assert pins["source_floor_sha256"] == V3_COMMITTED[1]
    assert pins["source_floor_size_bytes"] == V3_COMMITTED[0]


def test_builders_are_sha_pinned():
    art = _artifact()
    pins = art["revision_pins"]
    assert pins["builder_gate_v1_sha256"] == _sha(BUILDER)
    assert pins["builder_v3_sha256"] == _sha(BUILDER_V3)
    assert (
        pins["builder_v3_sha256"]
        == _v3()["revision_pins"]["builder_v3_sha256"]
    )
    assert (
        pins["nchs_reference_sha256"]
        == _v3()["revision_pins"]["nchs_reference_sha256"]
    )
    assert re.fullmatch(r"[0-9a-f]{40}", pins["populace_dynamics_sha"])
    assert "NOT a freeze" in pins["gates_yaml_pin_semantics"]


def test_gates_yaml_pre_lock_guard():
    """While GATE_MORTALITY_BLOCK_LANDED is False, gates.yaml is innocent
    of the gate and of both mortality artifacts; flipped, the block exists
    and cites THIS artifact by path (the v3 pre-lock-guard shape)."""
    text = GATES.read_text()
    if not GATE_MORTALITY_BLOCK_LANDED:
        assert "gate_mortality" not in text
        assert "mortality_gate_floors_v1" not in text
        assert "mortality_floors_v3" not in text
        return
    spec = yaml.safe_load(text)
    assert "gate_mortality" in spec["gates"]
    assert "runs/mortality_gate_floors_v1.json" in text


# --------------------------------------------------------------------------
# The floor block and cell stability
# --------------------------------------------------------------------------
def test_floor_block_equals_v3_pooled_block_and_recomputes_from_per_seed():
    art = _artifact()
    v3 = _v3()
    head = _head(v3)
    floor = art["noise_floor_seeds_0_99"]
    assert set(floor) == set(v3["cell_order"]) == set(art["cell_order"])
    for cell in v3["cell_order"]:
        values = np.array(
            [s["cells"][cell]["log_ratio_abs"] for s in head["per_seed"]]
        )
        blk = floor[cell]
        assert blk["values"] == pytest.approx(values.tolist(), rel=1e-12)
        assert blk["mean"] == pytest.approx(values.mean(), rel=1e-12)
        assert blk["sd"] == pytest.approx(values.std(ddof=1), rel=1e-12)
        assert blk["realized_sigma"] == pytest.approx(
            np.sqrt((values**2).mean()), rel=1e-12
        )
        ref = head["noise_floor_seeds_0_99"][cell]
        for key in ("mean", "sd", "min", "max", "realized_sigma", "n_seeds"):
            assert blk[key] == pytest.approx(ref[key], rel=1e-12), (cell, key)


def test_cell_stability_is_internally_consistent_and_matches_v3():
    art = _artifact()
    v3 = _v3()
    head = _head(v3)
    stab = art["cell_stability"]
    floor = art["noise_floor_seeds_0_99"]
    boot = v3["seed_count_stability"]["per_cell"]
    for cell, e in stab.items():
        f = floor[cell]
        for k in (1, 2, 3, 4):
            assert e[f"tolerance_k{k}"] == round(f["mean"] + k * f["sd"], 3), (
                cell,
                k,
            )
            assert e["clears_t_max_by_k"][str(k)] == (
                e[f"tolerance_k{k}"] <= T_MAX
            )
        assert e["tolerance_sigma_units_k3"] == round(
            e["tolerance_k3"] / f["realized_sigma"], 3
        )
        assert e["clears_t_max_at_k3"] == (e["tolerance_k3"] <= T_MAX)
        v3_e = head["cell_stability"][cell]
        assert e["tolerance_k3"] == v3_e["tolerance_k3"]
        assert e["tolerance_k2"] == v3_e["tolerance_k2"]
        assert e["tolerance_k4"] == v3_e["tolerance_k4"]
        assert (
            e["min_deaths_either_half_unweighted"]
            == v3_e["min_deaths_either_half"]
        )
        assert (
            e["min_effective_deaths_kish"] == v3_e["min_effective_deaths_kish"]
        )
        p = boot[cell]["at_100_seeds_sigma_v3"][
            "p_tolerance_at_or_below_t_max"
        ]
        assert e["bootstrap_p_tolerance_at_or_below_t_max_100_seeds"] == p
        assert e["bootstrap_in_stability_band"] == (0.1 <= p <= 0.9)
        assert e["events_ge_20_unweighted_worst_seed"] == (
            e["min_deaths_either_half_unweighted"] >= 20
        )
        assert e["events_ge_20_kish_effective_worst_seed"] == (
            e["min_effective_deaths_kish"] >= 20
        )
        assert (
            e["report_reason_kish"]
            == art["eligibility_rules"]["kish_effective_ge_20"][
                "report_reason"
            ][cell]
        )
        assert (
            e["report_reason_unweighted"]
            == art["eligibility_rules"]["unweighted_worst_seed_ge_20"][
                "report_reason"
            ][cell]
        )


def test_eligibility_rules_partition_recomputes_and_gated_sets_agree():
    art = _artifact()
    stab = art["cell_stability"]
    rules = art["eligibility_rules"]
    for rule, count_key, reason in (
        (
            "unweighted_worst_seed_ge_20",
            "events_ge_20_unweighted_worst_seed",
            "below_20_deaths_weaker_half",
        ),
        (
            "kish_effective_ge_20",
            "events_ge_20_kish_effective_worst_seed",
            "below_20_effective_deaths_weaker_half",
        ),
    ):
        eligible = []
        for cell, e in stab.items():
            if not e["clears_t_max_at_k3"]:
                expected = "tolerance_above_t_max"
            elif not e[count_key]:
                expected = reason
            else:
                expected = "clears_t_max_at_k3"
                eligible.append(cell)
            assert rules[rule]["report_reason"][cell] == expected, (rule, cell)
        assert rules[rule]["gate_eligible_internal"] == sorted(eligible)
        assert rules[rule]["n_gate_eligible_internal"] == len(eligible)
        assert rules[rule]["n_report_only"] == 14 - len(eligible)
        assert rules[rule][
            "cells_passing_the_event_criterion_alone"
        ] == sorted(c for c, e in stab.items() if e[count_key])
    diff = rules["difference"]
    assert diff["gated_sets_identical"] is True
    assert diff["gated_set"] == CELLS_GATED
    assert diff["event_criterion_pass_unweighted_only"] == [
        "25-34|male",
        "45-54|female",
    ]
    assert diff["event_criterion_pass_kish_only"] == []
    assert diff["report_reason_differs_on"] == []
    assert "ZERO movement" in diff["price"]


def test_gate_partition_is_the_gate_m4_shape_and_derives_from_the_rules():
    art = _artifact()
    part = art["gate_partition"]
    for key in (
        "gate_eligible",
        "report_only",
        "n_gate_eligible",
        "n_report_only",
        "internal_gate_eligible",
        "anchor_gate_eligible",
    ):
        assert key in part, key
    assert part["internal_gate_eligible"] == [
        "death." + c for c in CELLS_GATED
    ]
    assert (
        part["gate_eligible"]
        == part["internal_gate_eligible"] + part["anchor_gate_eligible"]
    )
    assert part["n_gate_eligible"] == len(part["gate_eligible"])
    assert part["n_report_only"] == len(part["report_only"]) == 10
    assert set(part["internal_gate_eligible"]).isdisjoint(part["report_only"])
    assert set(part["internal_gate_eligible"]) | set(
        part["report_only"]
    ) == set(art["reference_moments"])
    assert len(art["reference_moments"]) == 14
    # anchor eligibility = evidence-time criteria under BOTH conventions.
    expected_anchor = [
        name
        for name, chk in art["anchor_checks"].items()
        if not name.endswith("five_band_alternative")
        and chk["side_a"]["holds_on_every_half"]
        and chk["both_sides"]["holds_on_every_half"]
        and chk["side_a"]["clears_margin_k"]
        and chk["both_sides"]["clears_margin_k"]
    ]
    assert part["anchor_gate_eligible"] == expected_anchor
    assert "sex_dominance.male_exceeds_female" in expected_anchor
    assert "sex_dominance.five_band_alternative" not in part["gate_eligible"]
    assert (
        "R4" in part["rulings_that_can_move_it"]
        and "R5" in part["rulings_that_can_move_it"]
    )
    assert part["r4_alternative_partition"]["internal_gate_eligible"] == [
        "death.75-84|female",
        "death.75-84|male",
    ]
    assert "pending" in part["status"]


# --------------------------------------------------------------------------
# k, OC, anchors, teeth
# --------------------------------------------------------------------------
def test_k_selection_and_oc_recompute_from_stability():
    art = _artifact()
    stab = art["cell_stability"]
    ks = art["k_selection"]
    assert ks["chosen_k"] == 3 and ks["k_grid"] == [1, 2, 3, 4]

    def oc(cells, k):
        p = 1.0
        for c in cells:
            p *= (
                2
                * _normal_cdf(
                    stab[c][f"tolerance_k{k}"] / stab[c]["realized_sigma"]
                )
                - 1
            )
        return (
            (round(p, 4), round(p**5 + 5 * p**4 * (1 - p), 4))
            if cells
            else (None, None)
        )

    for k in (1, 2, 3, 4):
        b = ks["by_k"][str(k)]
        clearing = sorted(
            c for c in stab if stab[c][f"tolerance_k{k}"] <= T_MAX
        )
        assert b["cells_incl_85plus"] == clearing
        assert b["cells_25_84"] == [
            c for c in clearing if not c.startswith("85+")
        ]
        assert (b["p_seed_incl_85plus"], b["p_gate_incl_85plus"]) == oc(
            clearing, k
        )
        assert (b["p_seed_25_84"], b["p_gate_25_84"]) == oc(
            b["cells_25_84"], k
        )
    foc = art["faithful_candidate_oc"]
    assert foc["surface_4_cell_incl_85plus"]["n_gated_internal_cells"] == 4
    assert (
        foc["surface_4_cell_incl_85plus"]["p_seed_pass"],
        foc["surface_4_cell_incl_85plus"]["p_gate_pass_4_of_5"],
    ) == oc(CELLS_GATED, 3)
    assert (
        foc["surface_2_cell_25_84"]["p_seed_pass"],
        foc["surface_2_cell_25_84"]["p_gate_pass_4_of_5"],
    ) == oc(CELLS_GATED[:2], 3)
    assert foc["surface_4_cell_incl_85plus"]["p_gate_pass_4_of_5"] == 0.9868
    assert foc["surface_2_cell_25_84"]["p_gate_pass_4_of_5"] == 0.9975
    for c, row in foc["surface_4_cell_incl_85plus"]["per_cell"].items():
        assert row["tolerance"] == stab[c]["tolerance_k3"]
        assert row["realized_sigma"] == stab[c]["realized_sigma"]
        assert row["cell_pass_prob"] == round(
            2 * _normal_cdf(row["tolerance"] / row["realized_sigma"]) - 1, 6
        )


def test_anchor_checks_recompute_from_per_seed_hazards_and_match_v3():
    art = _artifact()
    v3 = _v3()
    head = _head(v3)
    full = {
        k: v["psid_m"]
        for k, v in v3["external_anchor"]["windows"]["declared_1997_plus"][
            "by_band_sex"
        ].items()
    }
    side_a = [s["hazards_side_a"] for s in head["per_seed"]]
    both = [
        h
        for s in head["per_seed"]
        for h in (s["hazards_side_a"], s["hazards_side_b"])
    ]

    def check(stat, block):
        fullv = stat(full)
        for label, halves in (("side_a", side_a), ("both_sides", both)):
            vals = np.array(
                [v for v in (stat(h) for h in halves) if v is not None]
            )
            b = block[label]
            assert b["n_halves_scored"] == len(vals)
            assert b["real_full_panel_min"] == pytest.approx(fullv, rel=1e-12)
            assert b["half_split_mean"] == pytest.approx(
                vals.mean(), rel=1e-12
            )
            assert b["half_split_sd"] == pytest.approx(
                vals.std(ddof=1), rel=1e-12
            )
            assert b["min_over_halves"] == pytest.approx(vals.min(), rel=1e-12)
            assert b["holds_on_every_half"] == (vals.min() > 0)
            assert b["margin_sigma_units"] == round(
                fullv / vals.std(ddof=1), 3
            )
            assert b["clears_margin_k"] == (fullv / vals.std(ddof=1) >= 3)

    def dominance(bands):
        def stat(h):
            vals = []
            for b in bands:
                m, f = h.get(f"{b}|male", 0.0), h.get(f"{b}|female", 0.0)
                if m <= 0 or f <= 0:
                    return None
                vals.append(math.log(m / f))
            return min(vals)

        return stat

    def gradient(sex, bands=("55-64", "65-74", "75-84", "85+")):
        def stat(h):
            gaps = []
            for lo, hi in zip(bands[:-1], bands[1:], strict=True):
                a, b = h.get(f"{lo}|{sex}", 0.0), h.get(f"{hi}|{sex}", 0.0)
                if a <= 0 or b <= 0:
                    return None
                gaps.append(math.log(b / a))
            return min(gaps)

        return stat

    checks = art["anchor_checks"]
    check(
        dominance(("45-54", "55-64", "65-74")),
        checks["sex_dominance.male_exceeds_female"],
    )
    check(
        dominance(("25-34", "35-44", "45-54", "55-64", "65-74")),
        checks["sex_dominance.five_band_alternative"],
    )
    check(gradient("male"), checks["age_gradient.comonotone|male"])
    check(gradient("female"), checks["age_gradient.comonotone|female"])
    # v3's committed tables agree.
    v3_dom = v3["anchor_invariants"]["sex_dominance"]["margins_by_band_set"]
    for key, name in (
        ("45-54+55-64+65-74", "sex_dominance.male_exceeds_female"),
        (
            "25-34+35-44+45-54+55-64+65-74",
            "sex_dominance.five_band_alternative",
        ),
    ):
        for conv in ("side_a", "both_sides"):
            assert (
                checks[name][conv]["margin_sigma_units"]
                == v3_dom[key][conv]["margin_sigma_units"]
            )
            assert (
                checks[name][conv]["holds_on_every_half"]
                == v3_dom[key][conv]["holds_on_every_half"]
            )
    v3_grad = v3["anchor_invariants"]["age_gradient_companion"]["by_sex"]
    for sex in ("male", "female"):
        assert (
            checks[f"age_gradient.comonotone|{sex}"]["side_a"][
                "margin_sigma_units"
            ]
            == v3_grad[sex]["side_a_convention"]["margin_sigma_units"]
        )
        assert (
            checks[f"age_gradient.comonotone|{sex}"]["both_sides"][
                "margin_sigma_units"
            ]
            == v3_grad[sex]["both_sides_convention"]["margin_sigma_units"]
        )
    assert (
        checks["sex_dominance.five_band_alternative"]["both_sides"][
            "holds_on_every_half"
        ]
        is False
    )
    assert (
        checks["sex_dominance.five_band_alternative"]["both_sides"][
            "margin_sigma_units"
        ]
        == 2.927
    )


def test_anchor_operating_characteristic_recomputes_and_prices_the_remedies():
    art = _artifact()
    oc = art["anchor_operating_characteristic"]
    checks = art["anchor_checks"]
    margins = oc["margins_sigma_units"]
    assert (
        margins["headline_3_band_side_a"]
        == checks["sex_dominance.male_exceeds_female"]["side_a"][
            "margin_sigma_units"
        ]
    )
    assert (
        margins["headline_3_band_both_sides"]
        == checks["sex_dominance.male_exceeds_female"]["both_sides"][
            "margin_sigma_units"
        ]
    )
    assert (
        margins["five_band_both_sides"]
        == checks["sex_dominance.five_band_alternative"]["both_sides"][
            "margin_sigma_units"
        ]
    )
    assert margins["gate_m4_weakest_anchor"] == 4.797
    noise = {
        "draw_noise_only": 1 / math.sqrt(20),
        "fitted_excluding_holdout": math.sqrt(1.05),
    }

    def row(m, ratio, k):
        p = _normal_cdf((m - k) / ratio)
        c6 = _normal_cdf(-k / ratio)
        return {
            "faithful_p_seed": round(p, 4),
            "faithful_p_gate_4_of_5": round(p**5 + 5 * p**4 * (1 - p), 4),
            "sex_flat_c6_p_seed": round(c6, 4),
            "sex_flat_c6_p_gate_4_of_5": round(
                c6**5 + 5 * c6**4 * (1 - c6), 4
            ),
        }

    for mlabel, m in margins.items():
        for scen, ratio in noise.items():
            assert oc["inherited_rule_margin_k_3_candidate_side"][mlabel][
                scen
            ] == row(m, ratio, 3), (mlabel, scen)
    for label, k in (("a_bare_positivity_k0", 0), ("b_k1", 1), ("b_k2", 2)):
        rem = oc["remedies_priced"][label]
        assert rem["candidate_side_k"] == k
        for mlabel in ("headline_3_band_side_a", "headline_3_band_both_sides"):
            for scen, ratio in noise.items():
                assert rem["by_margin"][mlabel][scen] == row(
                    margins[mlabel], ratio, k
                ), (label, mlabel, scen)
    a = oc["referee_a_reported"]
    inh = oc["inherited_rule_margin_k_3_candidate_side"]
    assert (
        abs(
            inh["headline_3_band_side_a"]["draw_noise_only"][
                "faithful_p_gate_4_of_5"
            ]
            - a["side_a_draw_noise_only"]["p_gate"]
        )
        < 1e-3
    )
    assert (
        abs(
            inh["headline_3_band_side_a"]["fitted_excluding_holdout"][
                "faithful_p_gate_4_of_5"
            ]
            - a["side_a_fitted_excluding_holdout"]["p_gate"]
        )
        < 1e-3
    )
    assert (
        abs(
            inh["headline_3_band_both_sides"]["draw_noise_only"][
                "faithful_p_gate_4_of_5"
            ]
            - a["both_sides_draw_noise_only"]["p_gate"]
        )
        < 1e-3
    )
    assert (
        abs(
            inh["headline_3_band_both_sides"]["fitted_excluding_holdout"][
                "faithful_p_gate_4_of_5"
            ]
            - a["both_sides_fitted_excluding_holdout"]["p_gate"]
        )
        < 1e-3
    )
    assert "c_demote_and_rename" in oc["remedies_priced"]
    assert oc["half_convention_proposed"]["proposal"] == "both_sides"
    assert "stricter" in oc["half_convention_proposed"]["why"].lower()
    assert "FILED" in oc["status"] and "PRICED" in oc["status"]


def test_teeth_table_recomputes_from_declared_window_hazards():
    art = _artifact()
    v3 = _v3()
    by = v3["external_anchor"]["windows"]["declared_1997_plus"]["by_band_sex"]
    full = {k: v["psid_m"] for k, v in by.items()}
    nchs = {k: v["nchs_M"] for k, v in by.items()}
    teeth = art["degenerate_candidates"]
    gated = teeth["gated_4_cell_surface"]
    assert gated == CELLS_GATED
    assert teeth["gated_2_cell_surface_25_84"] == CELLS_GATED[:2]
    tol = {c: art["cell_stability"][c]["tolerance_k3"] for c in gated}

    def pooled(sex):
        keys = [k for k in by if sex is None or k.endswith(f"|{sex}")]
        return sum(by[k]["psid_deaths_wt"] for k in keys) / sum(
            by[k]["psid_exposure_py"] for k in keys
        )

    hazards = {
        "c1_external_levels": {c: nchs[c] for c in gated},
        "c2_age_flat_within_sex": {c: pooled(c.split("|")[1]) for c in gated},
        "c3_fully_flat": {c: pooled(None) for c in gated},
        "c4_uniform_level_plus_25pct": {c: full[c] * 1.25 for c in gated},
        "c5_uniform_level_minus_25pct": {c: full[c] * 0.75 for c in gated},
        "c6_sex_flat": {c: full[f"{c.split('|')[0]}|female"] for c in gated},
    }
    for name, cand in hazards.items():
        row = teeth["candidates"][name]
        scores = {c: round(abs(math.log(cand[c] / full[c])), 3) for c in gated}
        assert row["scores"] == scores, name
        assert row["tolerances"] == tol
        fail_4 = sorted(c for c in gated if scores[c] > tol[c])
        assert row["failing_cells_4_cell"] == fail_4
        assert row["failing_cells_2_cell"] == [
            c for c in fail_4 if not c.startswith("85+")
        ]
        assert row["verdict_4_cell_surface"] == ("FAIL" if fail_4 else "PASS")
        assert row["min_margin_to_failure_4_cell"] == round(
            min(tol[c] - scores[c] for c in gated), 3
        )
    assert (
        teeth["candidates"]["c4_uniform_level_plus_25pct"]["known_non_catch"]
        is True
    )
    assert (
        teeth["candidates"]["c6_sex_flat"][
            "known_non_catch_of_the_internal_surface"
        ]
        is True
    )
    assert (
        teeth["candidates"]["c6_sex_flat"]["caught_by"]
        == "sex_dominance.male_exceeds_female"
    )
    beside = teeth["candidates"]["c6_sex_flat"]["anchor_oc_beside_the_catch"]
    assert (
        beside["inherited_rule"]
        == art["anchor_operating_characteristic"][
            "inherited_rule_margin_k_3_candidate_side"
        ]["headline_3_band_both_sides"]
    )
    assert teeth["known_non_catches"]["whole_gate"] == [
        "c4_uniform_level_plus_25pct"
    ]
    assert (
        "NEVER be described as certifying differential mortality"
        in teeth["catch_structure"]
    )


# --------------------------------------------------------------------------
# R4, R9, R10, A(ii), scoring frame, flip plan, hygiene
# --------------------------------------------------------------------------
def test_r4_block_locates_the_27_percent_and_recomputes_the_shares():
    art = _artifact()
    v3 = _v3()
    item1 = art["r4_85plus"]["item_1_the_27_percent"]
    assert item1["located"] is True
    assert item1["where"].startswith("gates.yaml:5399-5402")
    quoted = " ".join(item1["quoted_text_at_the_blob"])
    assert "~27%" in quoted and "confounded 85+" in quoted
    assert item1["is_it_the_same_quantity_as_anything_here"] is False
    by = v3["external_anchor"]["windows"]["declared_1997_plus"]["by_band_sex"]
    bands = v3["age_bands"]
    deaths = {
        b: sum(
            v["psid_deaths_unwt"]
            for k, v in by.items()
            if k.startswith(f"{b}|")
        )
        for b in bands
    }
    shares = item1["shares_of_85plus_events_by_pool"]
    for i, start in enumerate(bands[:-1]):
        pool = bands[i:]
        key = f"{start.split('-')[0]}+"
        assert shares[key]["pool_bands"] == pool
        assert shares[key]["events_unwt"] == sum(deaths[b] for b in pool)
        assert shares[key]["events_85plus"] == deaths["85+"]
        assert shares[key]["share_from_85plus"] == round(
            deaths["85+"] / shares[key]["events_unwt"], 4
        )
    assert shares["25+"]["events_unwt"] == 2277
    assert "METADATA-ONLY" in item1["disposition"]
    ruling = art["r4_85plus"]["item_3_the_ruling_priced_both_ways"]
    assert (
        ruling["admit_85plus"]["faithful_oc_p_gate"]
        == art["k_selection"]["by_k"]["3"]["p_gate_incl_85plus"]
    )
    assert (
        ruling["exclude_85plus"]["faithful_oc_p_gate"]
        == art["k_selection"]["by_k"]["3"]["p_gate_25_84"]
    )
    for side in ("admit_85plus", "exclude_85plus"):
        assert ruling[side]["for"] and ruling[side]["against"]


def test_censoring_bracket_is_report_only_and_internally_consistent():
    art = _artifact()
    bracket = art["r4_85plus"][
        "item_2_sensitivity_of_85plus_to_the_censoring_convention"
    ]
    assert bracket["report_only"] is True and bracket["gates_nothing"] is True
    stab = art["cell_stability"]
    for variant in ("unlimited", "le_one_more_grid_interval"):
        v = bracket["variants"][variant]
        lns = []
        exceed = []
        for cell, row in v["per_cell"].items():
            assert row["tolerance_k3_pinned"] == stab[cell]["tolerance_k3"]
            assert row["bracket_over_tolerance_k3"] == round(
                row["ln_m_extended_over_m_pinned"]
                / row["tolerance_k3_pinned"],
                4,
            )
            assert row["ln_m_extended_over_m_pinned"] == pytest.approx(
                math.log(
                    row["psid_over_nchs_extended"]
                    / row["psid_over_nchs_pinned"]
                ),
                abs=2e-5,
            )
            assert row["exceeds_own_tolerance"] == (
                row["ln_m_extended_over_m_pinned"] > row["tolerance_k3_pinned"]
            )
            lns.append(row["ln_m_extended_over_m_pinned"])
            if row["exceeds_own_tolerance"]:
                exceed.append(cell)
            assert (
                abs(
                    row["ln_m_extended_over_m_pinned"]
                    - bracket["referee_a_reported"][variant][cell]
                )
                < 1e-3
            )
        assert v["range_of_ln_movement"] == {
            "min": round(min(lns), 3),
            "max": round(max(lns), 3),
        }
        assert v["cells_where_the_bracket_exceeds_the_tolerance"] == sorted(
            exceed
        )
        assert v["pinned_death_events_declared_window"] == 2277
    assert (
        bracket["variants"]["unlimited"]["added_death_events_declared_window"]
        == 982
    )
    assert (
        bracket["variants"]["le_one_more_grid_interval"][
            "added_death_events_declared_window"
        ]
        == 850
    )
    assert bracket["variants"]["unlimited"][
        "cells_where_the_bracket_exceeds_the_tolerance"
    ] == ["85+|female", "85+|male"]
    assert bracket["missed_exact_decedents"] == 2796
    assert bracket["missed_exact_decedents_last_wave_1997_plus"] == 1025
    assert (
        max(
            bracket["referee_a_reported"][
                "max_abs_difference_ln_vs_this_builder"
            ].values()
        )
        < 1e-3
    )


def test_draw_stream_enumeration_matches_the_live_contract_and_is_distinct():
    builder = _import_builder()
    art = _artifact()
    draw = art["draw_stream"]
    bases = builder.enumerate_gates_yaml_seed_bases(GATES.read_text())
    assert draw["proposed_base"] == builder.DRAW_STREAM_BASE == 7400
    if not GATE_MORTALITY_BLOCK_LANDED:
        assert draw["every_seed_base_named_in_gates_yaml"] == bases
    else:
        # LIVE: the artifact is not rebuilt at the flip; the live file
        # adds exactly the gate's own base (pre-guarded).
        assert "7400" in bases
        assert draw["every_seed_base_named_in_gates_yaml"] == {
            k: v for k, v in bases.items() if k != "7400"
        }
    stream = set(range(7400, 7420))
    occupied = set(range(100)) | set(range(20260906, 20261006))
    for b in bases:
        if GATE_MORTALITY_BLOCK_LANDED and b == "7400":
            continue  # the block's own stream is not a self-collision
        occupied |= set(range(int(b), int(b) + 100))
    assert not (stream & occupied)
    assert draw["distinct"] is True and draw["collisions"] == []
    if not GATE_MORTALITY_BLOCK_LANDED:
        assert draw["gates_yaml_mentions_the_base_today"] is False
        assert "7400" not in bases


def test_restricted_split_perturbation_block_is_consistent_and_flips_the_knife_edge():
    art = _artifact()
    v3 = _v3()
    head = _head(v3)
    r10 = art["restricted_split_perturbation"]
    assert "per_cell" in r10, "built with PSID staged"
    assert set(r10["per_cell"]) == {
        f"{b}|{s}"
        for b in v3["age_bands"]
        if b != "85+"
        for s in ("male", "female")
    }
    clearing_f, clearing_r = [], []
    for cell, e in r10["per_cell"].items():
        f = e["full_frame_before_split"]
        r = e["restricted_25_84_before_split"]
        assert (
            f["tolerance_k3"] == head["cell_stability"][cell]["tolerance_k3"]
        )
        assert f["equals_committed_v3"] is True
        assert f["tolerance_k3"] == round(f["mean"] + 3 * f["sd"], 3)
        vals = np.array(r["values"])
        assert len(vals) == 100
        assert r["mean"] == pytest.approx(vals.mean(), rel=1e-12)
        assert r["sd"] == pytest.approx(vals.std(ddof=1), rel=1e-12)
        assert r["realized_sigma"] == pytest.approx(
            np.sqrt((vals**2).mean()), rel=1e-12
        )
        assert r["tolerance_k3"] == round(r["mean"] + 3 * r["sd"], 3)
        assert r["clears_t_max_at_k3"] == (r["tolerance_k3"] <= T_MAX)
        assert e["delta_tolerance_k3_restricted_minus_full"] == round(
            r["tolerance_k3"] - f["tolerance_k3"], 3
        )
        if f["clears_t_max_at_k3"]:
            clearing_f.append(cell)
        if r["clears_t_max_at_k3"]:
            clearing_r.append(cell)
    assert (
        r10["clearing_set_k3_full_frame"]
        == sorted(clearing_f)
        == ["75-84|female", "75-84|male"]
    )
    assert (
        r10["clearing_set_k3_restricted"]
        == sorted(clearing_r)
        == ["75-84|female"]
    )
    knife = r10["knife_edge_cell"]
    assert knife["cell"] == "75-84|male"
    assert knife["tolerance_k3_full_frame_before_split"] == 0.328 <= T_MAX
    assert knife["tolerance_k3_restricted_25_84_before_split"] > T_MAX
    assert (
        r10["n_persons_restricted_frame"]
        < r10["n_persons_full_frame"]
        == v3["data"]["n_persons_with_exposure"]
    )


def test_stability_clause_is_filed_and_changes_nothing_today():
    art = _artifact()
    v3 = _v3()
    boot = v3["seed_count_stability"]["per_cell"]
    clause = art["stability_clause"]
    in_band = {
        c: boot[c]["at_100_seeds_sigma_v3"]["p_tolerance_at_or_below_t_max"]
        for c in v3["cell_order"]
        if 0.1
        <= boot[c]["at_100_seeds_sigma_v3"]["p_tolerance_at_or_below_t_max"]
        <= 0.9
    }
    assert (
        clause["cells_in_band_today"]
        == in_band
        == {"65-74|male": 0.44325, "65-74|female": 0.6054}
    )
    assert clause["clearing_cells_the_clause_would_demote_today"] == []
    assert clause["changes_nothing_today"] is True
    assert clause["nearest_clearing_cell_to_the_band"] == {
        "cell": "75-84|female",
        "p": 0.9456,
        "distance_to_upper_edge": 0.0456,
    }
    assert (
        "adopt_the_clause" in clause["priced"]
        and "decide_at_1000_seeds" in clause["priced"]
    )
    assert "not adopted" in clause["status"]


def test_candidate_scoring_frame_and_flip_plan():
    art = _artifact()
    frame = art["candidate_scoring_frame"]
    assert frame["deaths_counted_inside_those_intervals_only"] is True
    assert "HANDED" in frame["operational_definition"]
    assert "pad" in frame["pad_row_exclusion"].lower()
    seeds = frame["per_gate_seed"]
    assert list(seeds) == ["0", "1", "2", "3", "4"]
    digests = set()
    for row in seeds.values():
        assert re.fullmatch(r"[0-9a-f]{64}", row["side_a_person_ids_sha256"])
        digests.add(row["side_a_person_ids_sha256"])
        assert (
            row["n_persons_side_a_declared_window"]
            <= row["n_persons_side_a_full_frame"]
        )
        assert row["deaths_unwt_declared_window"] > 1000
        for c in CELLS_GATED:
            g = row["gated_cells"][c]
            assert g["psid_m_side_a"] > 0 and g["deaths_unwt_side_a"] > 0
    assert len(digests) == 5
    plan = art["flip_plan"]
    assert plan["marker"] == "GATE_MORTALITY_BLOCK_LANDED"
    assert set(plan["files_carrying_the_marker"]) == {
        "tests/test_mortality_floors_v2.py",
        "tests/test_mortality_floors_v3.py",
        "tests/test_gates_derivations.py",
        "tests/test_mortality_gate_floors_v1.py",
    }
    pattern = re.compile(r"^GATE_MORTALITY_BLOCK_LANDED = (True|False)$", re.M)
    for rel in plan["files_carrying_the_marker"]:
        found = pattern.findall((ROOT / rel).read_text())
        assert found == [str(GATE_MORTALITY_BLOCK_LANDED)], rel
    assert "SAME COMMIT" in plan["rule"]


def test_record_hygiene_certification_scope_and_open_questions():
    art = _artifact()
    v3 = _v3()
    assert art["certification_scope"] == v3["certification_scope"]
    hygiene = art["record_hygiene"]
    for token in ("0.413 → 0.408", "[0.1, 0.9]", "1,000", "P ≈ 0.6", "4.6 s"):
        assert token in hygiene["referee_a_finding_iii_verbatim"], token
    assert "condensed" in hygiene["v3_label_status"]
    ids = [q["id"] for q in art["open_questions_for_the_ceremony"]]
    assert ids == ["R3", "R4", "R5", "R9", "R10", "A(ii)", "R8"]
    for q in art["open_questions_for_the_ceremony"]:
        assert not re.search(r"\bRULED\b|\bADOPTED\b", q["status"]), q["id"]


# --------------------------------------------------------------------------
# The draft block
# --------------------------------------------------------------------------
def test_draft_block_parses_recomputes_its_digest_and_is_a_draft():
    art = _artifact()
    frag = art["draft_gates_yaml_fragment"]
    text = frag["text"]
    assert (
        frag["text_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    )
    assert frag["n_lines"] == len(text.splitlines())
    assert frag["n_bytes"] == len(text.encode("utf-8"))
    assert text.startswith("  gate_mortality:\n")
    block = _block(art)
    assert (
        block["status"]
        == frag["status_in_text"]
        == "draft_pending_referee_round"
    )
    assert block["locked"] is False and block["thresholds"]["locked"] is False
    assert block["floor_run"] == "runs/mortality_gate_floors_v1.json"
    assert block["floor_run_sha256"] == "<FILLED AT RATIFICATION>"
    assert block["derived_from_floor_sha256"] == V3_COMMITTED[1]
    assert block["thresholds"]["floor_key"] == "noise_floor_seeds_0_99"
    tol = {}
    for view in block["thresholds"]["internal_surface"]["views"].values():
        tol.update(view["tolerances"])
    assert tol == {
        "death." + c: art["cell_stability"][c]["tolerance_k3"]
        for c in CELLS_GATED
    }
    assert set(block["thresholds"]["report_only"]) == set(
        art["gate_partition"]["report_only"]
    )
    assert block["thresholds"]["protocol"]["draw_stream_base"] == 7400
    assert set(block["thresholds"]["anchor_surface"]["cells"]) == set(
        art["gate_partition"]["anchor_gate_eligible"]
    )
    for marker in ("<RULING R3", "<RULING R4", "<RULING R5", "<RULING A(ii)"):
        assert marker in text, marker
    assert (
        len(
            block["thresholds"]["ceremony_notes"][
                "placeholders_the_ratifying_round_must_fill"
            ]
        )
        >= 5
    )


def test_draft_block_wording_audit_recomputes():
    builder = _import_builder()
    art = _artifact()
    text = art["draft_gates_yaml_fragment"]["text"]
    flat = builder.normalized(text)
    stripped = dict(art)
    stripped.pop("wording_audit")
    recomputed = builder.wording_audit(text, json.dumps(stripped))
    assert recomputed == art["wording_audit"]
    assert recomputed["forbidden_words_absent_from_fragment"] is True
    assert recomputed["forbidden_words_absent_from_artifact"] is True
    assert recomputed["all_covers_prominence_items_hold"] is True
    for word in builder.FORBIDDEN_WORDS:
        assert word not in flat.lower()
    assert "1997-2023" not in flat
    assert "packet's literal extreme" not in flat


def test_draft_block_text_is_written_nowhere_else():
    art = _artifact()
    text = art["draft_gates_yaml_fragment"]["text"]
    try:
        listed = subprocess.check_output(
            ["git", "ls-files"], cwd=ROOT, text=True
        ).split("\n")
    except (OSError, subprocess.CalledProcessError):
        listed = [
            str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()
        ]
    for rel in listed:
        if not rel or not (
            rel == "gates.yaml"
            or rel.startswith(
                ("docs/", "scripts/", "tests/", "src/", "runs/", "paper/")
            )
        ):
            continue
        path = ROOT / rel
        if path.resolve() == ARTIFACT.resolve() or path.suffix in {
            ".png",
            ".pdf",
            ".pkl",
            ".parquet",
            ".zip",
            ".gz",
            ".h5",
            ".jpg",
            ".svg",
        }:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert text not in body, rel
        assert json.dumps(text)[1:-1][:400] not in body, rel


# --------------------------------------------------------------------------
# The pre-flip re-emission (referee A section 8 S1-S4, S6, S7; referee B
# conditions 3(i), 3(j), 4; the completed flip plan; the placeholder census)
# --------------------------------------------------------------------------
#: referee A's ratifying-round report (mortality-ratify-A/REPORT.md), by
#: whose digest the 1,000-seed DIAGNOSTIC figures (S1, S3, S4, S6) are
#: carried in the block. They rebuild nothing; every BOUND number is
#: still recomputed from v3's per-seed record by the tests above.
REFEREE_A_RATIFYING_SHA256 = (
    "c38826343303ed32da6820500881274fb82b82474ac6f1499dab970d1b68c103"
)


def test_pre_flip_substitutions_are_in_the_block_and_no_bound_number_moved():
    """S1 (split-frame pin reworded as the pre-registered sample), S2
    (teeth basis: the noise-free centre, with the per-seed side-A
    verdicts at the gate seeds recomputed here), S3 (the block-luck
    sentence), S4 (the 1,000-seed-sigma OC), S6 (the anchor's
    evidence-time margin at 1,000 seeds, by A's digest), S7 (margins
    rounded to 3 dp before Phi), B 3(i) (key-path citations;
    gate_m4's full no_self_rescue), B 3(j) (the knife-edge sentence).
    Every bound number is the same derivation as before."""
    builder = _import_builder()
    art = _artifact()
    v3 = _v3()
    text = art["draft_gates_yaml_fragment"]["text"]
    block = _block(art)
    th = block["thresholds"]
    # S1: the pin is the pre-registered sample; both tolerances still
    # equal the artifact's R10 block.
    assert "PRE-REGISTERED SAMPLE" in text
    pin = th["protocol"]["split_frame_pin"]
    knife = art["restricted_split_perturbation"]["knife_edge_cell"]
    assert (
        pin["full_frame_before_split_tolerance_75_84_male"]
        == knife["tolerance_k3_full_frame_before_split"]
        == art["cell_stability"]["75-84|male"]["tolerance_k3"]
    )
    assert (
        pin["restricted_25_84_before_split_tolerance_75_84_male"]
        == knife["tolerance_k3_restricted_25_84_before_split"]
    )
    # S2: the basis is the noise-free centre; the per-seed side-A
    # verdicts recompute from v3's per-seed hazards.
    teeth = art["degenerate_candidates"]
    assert "NOISE-FREE CENTRE" in teeth["basis"]
    assert "UPPER BOUND" not in json.dumps(art)
    head = _head(v3)
    full_window = v3["external_anchor"]["windows"]["declared_1997_plus"]
    summary = builder.gate_seed_teeth(
        full_window, art["cell_stability"], CELLS_GATED, head["per_seed"]
    )
    tol = {c: art["cell_stability"][c]["tolerance_k3"] for c in CELLS_GATED}
    for name, spec in builder.degenerate_candidate_hazards(
        full_window, CELLS_GATED
    ).items():
        g4 = sum(
            all(
                abs(math.log(spec["hazard"][c] / s["hazards_side_a"][c]))
                <= tol[c]
                for c in CELLS_GATED
            )
            for s in head["per_seed"][:5]
        )
        assert summary[name][0] == g4, name
        row = teeth["candidates"][name]["at_the_gate_seeds_per_seed_side_a"]
        assert row.startswith(f"4-cell surface: {g4}/5 gate seeds pass"), name
        assert (
            builder.gate_seed_summary_text(summary, name, 4) in teeth["basis"]
        ), name
    assert summary["c1_external_levels"][0] == 3
    assert summary["c4_uniform_level_plus_25pct"][0] == 1
    assert summary["c5_uniform_level_minus_25pct"][0] == 0
    assert summary["c6_sex_flat"][0] == 4
    assert teeth["known_non_catches"]["whole_gate"] == [
        "c4_uniform_level_plus_25pct"
    ]
    assert (
        "noise-free centre"
        in th["degenerate_candidates"]["c4_uniform_level_plus_25pct"][
            "verdict"
        ].lower()
    )
    # S3 / S4: the block-luck and 1,000-seed-sigma disclosures.
    margins = {m["margin"]: m["detail"] for m in block["not_certified"]}
    assert "0.375 / 0.398 / 0.344 / 0.269" in margins["cells_25_74"]
    assert "0.88 / 0.61" in margins["cells_25_74"]
    assert REFEREE_A_RATIFYING_SHA256[:16] in margins["cells_25_74"]
    oc_text = th["faithful_candidate_oc"]["oc_vs_precedent"]
    assert "0.936 (4 cells) / 0.990 (2 cells)" in oc_text
    assert "0.9998 / 1.0000" in oc_text
    # S6: the anchor's evidence-time margin at 1,000 seeds sits beside
    # the bound margin, attributed by digest; the bound margin is the
    # artifact's own recomputation and did not move.
    cell = th["anchor_surface"]["cells"]["sex_dominance.male_exceeds_female"]
    ev = cell["evidence_time_margin_at_1000_seeds"]
    assert REFEREE_A_RATIFYING_SHA256 in ev["source"]
    assert ev["both_sides_sd_2000_halves"] == 0.1055
    assert ev["margin_sigma_units"] == 2.939
    assert ev["inverting_halves_of_2000"] == 10
    assert ev["disjoint_100_seed_blocks_holding_on_every_half"] == "3 of 10"
    assert ev["disjoint_100_seed_blocks_with_margin_ge_3_sigma"] == "4 of 10"
    assert ev["disjoint_100_seed_blocks_meeting_both_conditions"] == "2 of 10"
    assert ev["p_eligible_random_100_seed_block_both_sides"] == 0.2
    bound = art["anchor_checks"]["sex_dominance.male_exceeds_female"]
    assert (
        cell["margin_sigma_units"]["both_sides"]
        == bound["both_sides"]["margin_sigma_units"]
    )
    assert (
        ev["margin_sigma_units"]
        < 3
        <= cell["margin_sigma_units"]["both_sides"]
    )
    assert "2.939 sigma" in margins["sex_differential_rides_on_the_anchor"]
    # S7: margins rounded to 3 dp before Phi.
    assert (
        "ROUNDED to 3 dp" in art["anchor_operating_characteristic"]["method"]
    )
    # B 3(i): no live line-number citation is left in the block; the
    # key paths resolve in the live gate_m6; no_self_rescue is gate_m4's.
    assert "gates.yaml:" not in text and "gate_m6:" not in text
    gates = yaml.safe_load(GATES.read_text())["gates"]
    m6 = gates["gate_m6"]
    assert m6["not_certified"][0]["margin"] == "mortality_drift"
    anchor = m6["deliverables"]["ssa_nchs_life_table_mortality_anchor"]
    assert "REJECTED" in anchor["gating"]
    assert "circularity_disclosure" in anchor
    assert "mortality" in m6["split_units"]["household_disjoint_families"]
    for path in (
        "gate_m6.not_certified[0].detail",
        "gate_m6.deliverables.ssa_nchs_life_table_mortality_anchor.gating",
        "gate_m6.deliverables.ssa_nchs_life_table_mortality_anchor.circularity_disclosure",
        "gate_m6.split_units.household_disjoint_families",
    ):
        assert path in text, path
    assert (
        th["governance"]["amendment_rules"]["no_self_rescue"]
        == gates["gate_m4"]["thresholds"]["governance"]["amendment_rules"][
            "no_self_rescue"
        ]
    )
    # B 3(j): the knife-edge sentence carries both tolerances.
    conv = margins["conventions_and_the_undercount"]
    assert "split-frame pin" in conv
    assert (
        f"{knife['tolerance_k3_full_frame_before_split']:.3f}" in conv
        and str(knife["tolerance_k3_restricted_25_84_before_split"]) in conv
    )
    # Nothing ruled: every placeholder family is still present.
    for marker in ("<RULING R3", "<RULING R4", "<RULING R5", "<RULING A(ii)"):
        assert marker in text, marker
    assert block["status"] == "draft_pending_referee_round"


def test_flip_plan_enumerates_every_assertion_site_and_each_is_guarded():
    """Referee A ratifying round sections 5.4 and 8; referee B section
    7.3 and condition 3: the flip plan names EVERY assertion site the
    flip touches with its pre-flip and post-flip form; each named test
    exists in the named file; each site marked marker-guarded reads the
    marker inside that function's body; the withdrawn sentence is gone;
    the block's ceremony_notes.flip_plan names every guarded test; the
    placeholder census names the non-proposed rulings' unmarked sites."""
    art = _artifact()
    plan = art["flip_plan"]
    assert "changes nothing else" not in plan["rule"]
    assert "SAME COMMIT" in plan["rule"]
    sites = plan["assertion_sites"]
    assert len(sites) >= 20
    notes = _block(art)["thresholds"]["ceremony_notes"]
    notes_plan = notes["flip_plan"]
    seen = set()
    for site in sites:
        for key in (
            "file",
            "test",
            "site_at_f8ccfe8",
            "pre_flip",
            "post_flip",
            "guard",
        ):
            assert site[key], (site, key)
        path = ROOT / site["file"]
        assert path.is_file(), site["file"]
        source = path.read_text(encoding="utf-8")
        name = site["test"]
        seen.add((site["file"], name))
        if name == "GATE_MORTALITY_BLOCK_LANDED":
            assert re.search(
                r"^GATE_MORTALITY_BLOCK_LANDED = (True|False)$", source, re.M
            )
            continue
        match = re.search(rf"^def {re.escape(name)}\(", source, re.M)
        assert match, (site["file"], name)
        body = source[match.start() :]
        nxt = re.search(r"^(def |@)", body[1:], re.M)
        body = body[: nxt.start() + 1] if nxt else body
        if site["guard"].startswith("marker-guarded"):
            assert "GATE_MORTALITY_BLOCK_LANDED" in body, (site["file"], name)
            assert name in notes_plan, name
    for rel in plan["files_carrying_the_marker"]:
        assert (rel, "GATE_MORTALITY_BLOCK_LANDED") in seen, rel
    for required in (
        "test_gate_m4_flip_leaves_locked_siblings_byte_identical",
        "test_gate_w1_flip_leaves_locked_siblings_byte_identical",
        "test_gate_mortality_draft_block_is_written_nowhere_else",
        "test_gate_mortality_draw_stream_base_is_distinct_and_not_yet_live",
        "test_draw_stream_enumeration_matches_the_live_contract_and_is_distinct",
        "test_gate_mortality_partition_under_both_eligibility_rules",
    ):
        assert any(t == required for _, t in seen), required
    assert "assertion_sites" in notes_plan
    assert set(plan["conditional_on_the_rulings"]) == {
        "R4_exclude",
        "R5_c_demote_and_rename",
        "R5_companions_report_only",
        "A_ii_any_outcome",
    }
    census = " ".join(notes["placeholders_the_ratifying_round_must_fill"])
    for phrase in (
        "UNMARKED under EXCLUDE",
        "UNMARKED under (c) DEMOTE",
        "UNMARKED under COMPANIONS REPORT-ONLY",
        "RULED A(ii)",
        "tranche_id",
        "certification_scope.tranche",
        "r4_alternative_partition",
        "header comment",
    ):
        assert phrase in census, phrase


# --------------------------------------------------------------------------
# PSID-gated reproduction
# --------------------------------------------------------------------------
@needs_real_ind
def test_psid_blocks_reproduce_without_populace_fit():
    """The restricted-before-split floor at ALL 100 seeds, the censoring
    bracket cell by cell and the gate-seed scoring frames' person-id
    digests reproduce from PSID; ``populace.fit`` is never imported."""
    assert "populace.fit" not in sys.modules
    builder = _import_builder()
    assert "populace.fit" not in sys.modules
    from populace_dynamics.data import deaths, panels

    art = _artifact()
    v3 = _v3()
    demo = panels.demographic_panel()
    dr = deaths.read_death_records()
    frames, _ = builder.v3b.build_convention_frames(demo, dr)
    pinned = frames[builder.v3b.CONVENTION_PINNED]
    assert len(pinned) == art["psid"]["frame_pinned_n_slices"]
    assert (
        float(pinned.death.sum()) == art["psid"]["frame_pinned_death_events"]
    )
    r10 = builder.restricted_split_perturbation(
        pinned, _head(v3)["cell_stability"], verbose=False
    )
    ref = art["restricted_split_perturbation"]
    for cell, e in ref["per_cell"].items():
        got = r10["per_cell"][cell]
        assert got["restricted_25_84_before_split"]["values"] == pytest.approx(
            e["restricted_25_84_before_split"]["values"], rel=1e-9, abs=1e-12
        ), cell
        assert (
            got["restricted_25_84_before_split"]["tolerance_k3"]
            == e["restricted_25_84_before_split"]["tolerance_k3"]
        )
        assert (
            got["full_frame_before_split"]["tolerance_k3"]
            == e["full_frame_before_split"]["tolerance_k3"]
        )
    assert (
        r10["n_persons_restricted_frame"] == ref["n_persons_restricted_frame"]
    )
    nchs_rates = builder.v1b.nchs_band_rates(
        json.loads(
            (ROOT / "data/external/nchs_life_tables_2023.json").read_text()
        )
    )
    bracket = builder.censoring_extension_bracket(
        demo,
        dr,
        pinned,
        nchs_rates,
        art["cell_stability"],
        v3["cell_order"],
        verbose=False,
    )
    ref_b = art["r4_85plus"][
        "item_2_sensitivity_of_85plus_to_the_censoring_convention"
    ]
    assert bracket["missed_exact_decedents"] == ref_b["missed_exact_decedents"]
    for variant in ("unlimited", "le_one_more_grid_interval"):
        assert (
            bracket["variants"][variant]["added_death_events_declared_window"]
            == ref_b["variants"][variant]["added_death_events_declared_window"]
        )
        for cell, row in ref_b["variants"][variant]["per_cell"].items():
            assert bracket["variants"][variant]["per_cell"][cell][
                "ln_m_extended_over_m_pinned"
            ] == pytest.approx(row["ln_m_extended_over_m_pinned"], abs=1e-9)
    seeds = builder.gate_seed_frames(pinned, CELLS_GATED)
    for seed, row in art["candidate_scoring_frame"]["per_gate_seed"].items():
        got = seeds[seed]
        assert (
            got["side_a_person_ids_sha256"] == row["side_a_person_ids_sha256"]
        )
        assert (
            got["n_slices_declared_window"] == row["n_slices_declared_window"]
        )
        assert (
            got["deaths_unwt_declared_window"]
            == row["deaths_unwt_declared_window"]
        )
        for c in CELLS_GATED:
            assert got["gated_cells"][c]["psid_m_side_a"] == pytest.approx(
                row["gated_cells"][c]["psid_m_side_a"], rel=1e-12
            )
    assert "populace.fit" not in sys.modules
