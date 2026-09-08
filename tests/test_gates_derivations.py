"""Bind every locked gate-1 threshold to its stated derivation.

Round-2 review finding 5b: derivations lived only in YAML comments, so
an artifact rebuild that shifted a floor could silently break the
stated rationale. Each view's ``derivations`` block in gates.yaml is
machine-checkable data: threshold == round(floor mean + k * floor sd)
at the stated rounding. These tests run everywhere — they touch only
committed files.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _gate_1() -> dict:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    return gates["gates"]["gate_1"]["thresholds"]


def _floor_stats(run_path: str, key: str) -> tuple[float, float]:
    artifact = json.loads((ROOT / run_path).read_text())
    stats = artifact["noise_floor_seeds_0_4"][key]
    return stats["mean"], stats["sd"]


def _derive(run_path: str, key: str, k: float, rounding: int) -> float:
    mean, sd = _floor_stats(run_path, key)
    return round(mean + k * sd, rounding)


def _view_cases():
    for view_name, view in _gate_1()["views"].items():
        derivations = view["derivations"]
        for threshold_name, rule in derivations["rules"].items():
            yield (
                view_name,
                threshold_name,
                derivations["floor_run"],
                rule,
                view["geometry"][threshold_name],
            )


@pytest.mark.parametrize(
    "view_name, threshold_name, floor_run, rule, locked",
    list(_view_cases()),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_locked_threshold_matches_stated_derivation(
    view_name, threshold_name, floor_run, rule, locked
):
    rounding = rule.get("rounding", 2)
    if isinstance(rule["k"], list):
        lower = _derive(floor_run, rule["key"], rule["k"][0], rounding)
        upper = _derive(floor_run, rule["key"], rule["k"][1], rounding)
        assert [lower, upper] == pytest.approx(locked), (
            f"{view_name}.{threshold_name}: derived [{lower}, {upper}] "
            f"!= locked {locked}"
        )
    else:
        derived = _derive(floor_run, rule["key"], rule["k"], rounding)
        assert derived == pytest.approx(locked), (
            f"{view_name}.{threshold_name}: derived {derived} "
            f"!= locked {locked}"
        )


def test_every_locked_geometry_threshold_has_a_derivation():
    for view in _gate_1()["views"].values():
        assert set(view["geometry"]) == set(view["derivations"]["rules"])


def test_battery_tolerances_have_committed_references():
    thresholds = _gate_1()
    reference = json.loads(
        (ROOT / "runs/noise_floor_psid_family_9822.json").read_text()
    )["battery_reference"]
    aliases = {"mobility_diagonal": "mobility_diagonal_mean"}
    for name in thresholds["battery"]:
        stat = name.removesuffix("_tolerance")
        stat = aliases.get(stat, stat)
        assert stat in reference, f"no committed reference for {stat}"


def test_zero_persistence_is_one_minus_exit_rate():
    """The lock annotates these as ONE constraint; pin the identity."""
    reference = json.loads(
        (ROOT / "runs/noise_floor_psid_family_9822.json").read_text()
    )["battery_reference"]
    assert math.isclose(
        reference["zero_persistence"],
        1.0 - reference["exit_rate"],
        rel_tol=0,
        abs_tol=1e-12,
    )


# --------------------------------------------------------------------------
# Amendment proposal binding (gate_1.amendment_proposed)
#
# The amendment proposal is an inert public OBJECT: it changes no locked
# value and no model reads it. These tests bind its arithmetic so a
# referee round (and any later ratification) inherits a proposal whose
# stated derivations already hold. They run everywhere -- they touch only
# committed files (gates.yaml plus the anchor artifact). All are no-ops
# (skip) until the amendment_proposed subsection exists.
# --------------------------------------------------------------------------
def _amendment() -> dict | None:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    return gates["gates"]["gate_1"].get("amendment_proposed")


def _benefit_space_change() -> dict | None:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    ratified = gates["gates"]["gate_1"]["thresholds"].get("benefit_space")
    if ratified is not None:
        return ratified
    amendment = _amendment()
    if amendment is None:
        return None
    for change in amendment["changes"]:
        if change.get("type") == "add_gated_block":
            return change
    return None


def _anchor_stats(run_path: str, key: str) -> tuple[float, float]:
    artifact = json.loads((ROOT / run_path).read_text())
    stats = artifact["noise_floor_seeds_0_4"][key]
    return stats["mean"], stats["sd"]


def test_amendment_ks_threshold_matches_committed_anchor():
    """Proposed KS band == round(anchor mean + k * anchor sd) at rounding.

    The one floor-DERIVED band in the proposal (every other band is the
    a-priori paper criterion). Mirrors the locked-geometry derivation
    test: the stated ``k`` and ``rounding`` must reproduce the value.
    """
    change = _benefit_space_change()
    if change is None:
        pytest.skip("no amendment_proposed benefit_space block")
    derivations = change["derivations"]
    run_path = derivations["anchor_run"]
    rule = derivations["rules"]["weighted_ks_max"]
    rounding = rule.get("rounding", 4)
    mean, sd = _anchor_stats(run_path, rule["key"])
    derived = round(mean + rule["k"] * sd, rounding)
    locked = change["metrics"]["weighted_ks_max"]["value"]
    assert derived == pytest.approx(
        locked
    ), f"proposed KS band derived {derived} != stated {locked}"


def test_amendment_gated_metrics_carry_derivation_or_a_priori_source():
    """Every proposed GATED metric is justified.

    Each metric in the proposed benefit_space block either derives from
    the committed anchor (a ``derivations.rules`` entry) or cites an
    a-priori source (an ``a_priori_source`` field). No proposed gated
    number is left unexplained.
    """
    change = _benefit_space_change()
    if change is None:
        pytest.skip("no amendment_proposed benefit_space block")
    derived_metrics = set(change["derivations"]["rules"])
    for name, spec in change["metrics"].items():
        has_derivation = name in derived_metrics
        has_a_priori = bool(spec.get("a_priori_source"))
        assert has_derivation or has_a_priori, (
            f"proposed gated metric {name} carries neither a derivation "
            f"nor an a_priori_source citation"
        )


def test_amendment_derived_metrics_are_not_also_flat_a_priori():
    """The floor-derived KS band is not mislabeled as an a-priori band.

    Derived and a-priori are mutually exclusive justifications; a metric
    with a ``derivations.rules`` entry must NOT also claim an a-priori
    source (that would hide that its value tracks the floor, not a fixed
    criterion).
    """
    change = _benefit_space_change()
    if change is None:
        pytest.skip("no amendment_proposed benefit_space block")
    derived_metrics = set(change["derivations"]["rules"])
    for name in derived_metrics:
        assert not change["metrics"][name].get("a_priori_source"), (
            f"{name} is floor-derived; it must not also cite an "
            f"a_priori_source"
        )


def test_amendment_anchor_stats_recompute_from_stored_per_seed_values():
    """The anchor artifact's pooled stats recompute from its per-seed data.

    An artifact rebuild that shifted the floor must not silently keep
    stale pooled numbers: every headline the proposal leans on (the KS
    mean/sd it derives from, the abs mean/median/Q0 gap magnitudes, the
    pooled Q0 magnitude, and the per-decile 5%-clip counts) recomputes
    from ``per_seed``.
    """
    change = _benefit_space_change()
    if change is None:
        pytest.skip("no amendment_proposed benefit_space block")
    run_path = change["derivations"]["anchor_run"]
    art = json.loads((ROOT / run_path).read_text())
    per_seed = art["per_seed"]
    floor = art["floor_seeds_0_4"]

    def dist(row: dict, path: list[str]):
        node = row["distribution"]
        for key in path:
            node = node[key]
        return node

    # KS block (the derived one) recomputes, and the headline
    # noise_floor_seeds_0_4 mirror equals it.
    ks_vals = [dist(r, ["ks_distance"]) for r in per_seed]
    assert floor["ks_distance"]["values"] == pytest.approx(ks_vals)
    assert floor["ks_distance"]["mean"] == pytest.approx(
        sum(ks_vals) / len(ks_vals)
    )
    n = len(ks_vals)
    mean_ks = sum(ks_vals) / n
    var_ks = sum((v - mean_ks) ** 2 for v in ks_vals) / (n - 1)
    assert floor["ks_distance"]["sd"] == pytest.approx(var_ks**0.5)
    assert art["noise_floor_seeds_0_4"]["ks_distance"] == (
        floor["ks_distance"]
    )

    # Absolute percent-gap magnitudes recompute from the signed per-seed
    # distribution gaps.
    abs_mean = [abs(dist(r, ["mean", "pct_diff"])) for r in per_seed]
    abs_median = [abs(dist(r, ["median", "pct_diff"])) for r in per_seed]
    assert floor["abs_mean_pct_diff"]["values"] == pytest.approx(abs_mean)
    assert floor["abs_median_pct_diff"]["values"] == pytest.approx(abs_median)

    # Q0: the pooled magnitude the gate is scored on equals the absolute
    # across-seed mean of the signed per-seed Q0 gaps.
    q0_signed = [r["q0_zero_anchor"]["mean_pct_diff"] for r in per_seed]
    pooled_abs_q0 = abs(sum(q0_signed) / len(q0_signed))
    assert floor["pooled_abs_q0_mean_pct_diff"] == pytest.approx(pooled_abs_q0)

    # Per-decile 5%-clip counts (the reported-not-gated evidence for d1,
    # d2) recompute from the signed per-seed decile gaps.
    for dkey, count in floor["decile_seeds_clipping_5pct"].items():
        vals = floor["signed_decile_pct_diff"][dkey]["values"]
        assert count == sum(abs(v) > 5.0 for v in vals), dkey


def test_amendment_reported_not_gated_deciles_are_denominator_fragile():
    """d1/d2 are reported-not-gated because the FLOOR itself clips 5%.

    The amendment reports-not-gates exactly the deciles whose
    real-vs-real floor exceeds the +/-5% band on a majority of seeds
    (denominator fragility), and gates exactly the deciles whose floor
    clips no seed. This binds that the reported/gated partition matches
    the committed anchor, not a hand-picked list.
    """
    change = _benefit_space_change()
    if change is None:
        pytest.skip("no amendment_proposed benefit_space block")
    run_path = change["derivations"]["anchor_run"]
    art = json.loads((ROOT / run_path).read_text())
    clip = art["floor_seeds_0_4"]["decile_seeds_clipping_5pct"]
    n_seeds = art["n_persons"] and len(
        art["floor_seeds_0_4"]["ks_distance"]["values"]
    )
    majority = n_seeds // 2 + 1

    reported = set(change["reported_not_gated"])
    gated = set(change["metrics"]["decile_pct_diff_max"]["deciles_gated"])
    assert reported.isdisjoint(gated)

    # Every reported-not-gated decile clips 5% on a majority of seeds.
    for dkey in reported:
        assert clip[dkey] >= majority, (
            f"{dkey} is reported-not-gated but its real-vs-real floor "
            f"clips only {clip[dkey]}/{n_seeds} seeds"
        )
    # Every gated decile clips 5% on no seed.
    for dkey in gated:
        assert clip[dkey] == 0, (
            f"{dkey} is gated but its real-vs-real floor clips "
            f"{clip[dkey]} seeds"
        )


# --------------------------------------------------------------------------
# Amendment proposal 2 binding (gate_1.amendment_proposed, proposal_number 2)
#
# Reworked per the adversarial referee's AMEND verdict (PR #67). The
# pairs-view c2st gate moves from per-seed on the locked 5 to the
# across-seed mean over 20 pre-registered seeds (fix B), guarded by a
# VERSION-MATCHED per-seed catastrophe cap (fix C), and the amendment
# rescues NO committed verdict (fix A). Like amendment 1 this proposal is
# an inert public OBJECT: it changes no locked value and no model reads it.
# These tests bind its arithmetic (the version-matched cap, the unchanged
# mean line, the 20-seed set, the operating-characteristic table, the
# considered-and-rejected lines) and verify the illustrative retroactive
# disclosure -- applied: false, no committed verdict changed -- against a
# fresh recomputation from the committed run artifacts. All are no-ops
# (skip) until the amendment_2 subsection exists. They touch only committed
# files.
# --------------------------------------------------------------------------
PAIRS_VIEW = "psid_family_earnings_pairs"


def _amendment_2() -> dict | None:
    amendment = _amendment()
    if amendment is None or amendment.get("proposal_number") != 2:
        return None
    return amendment


def _amend2_change(change_id: int) -> dict | None:
    amendment = _amendment_2()
    if amendment is None:
        return None
    for change in amendment["changes"]:
        if change.get("id") == change_id:
            return change
    return None


def _amend2_rejected(entry_id: str) -> dict | None:
    amendment = _amendment_2()
    if amendment is None:
        return None
    for entry in amendment.get("considered_and_rejected", []):
        if entry.get("id") == entry_id:
            return entry
    return None


def _floor_at_path(run_path: str, path: list[str]) -> tuple[float, float]:
    """Return (mean, sd) from a nested node that stores them directly."""
    node = json.loads((ROOT / run_path).read_text())
    for key in path:
        node = node[key]
    return node["mean"], node["sd"]


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def test_amendment2_cap_derivation_binds_to_version_matched_floor():
    """The per-seed cap == round(matched floor mean + 8*sd, 3) == 0.554.

    Fix C: the cap derives from the VERSION-MATCHED (sklearn 1.8.0) floor
    -- the 20-seed floor_c2st_distribution in the diagnostics artifact --
    not the committed 1.9.0 floor. The stated k/rounding and the floor at
    the stated path must reproduce 0.554 from the committed artifact, not
    the version-mismatched 0.547.
    """
    change = _amend2_change(2)
    if change is None:
        pytest.skip("no amendment_proposed proposal 2 with a cap change")
    deriv = change["proposed"]["derivation"]
    mean, sd = _floor_at_path(deriv["floor_run"], deriv["floor_path"])
    rule = deriv["rule"]
    derived = round(mean + rule["k"] * sd, rule.get("rounding", 3))
    stated = change["proposed"]["value"]
    assert derived == pytest.approx(
        stated
    ), f"cap derived {derived} != stated {stated}"
    assert stated == 0.554


def test_amendment2_mean_rule_keeps_ratified_line_new_estimator():
    """The mean line holds the ratified 0.53 with the ratified derivation.

    Change 1 re-reads the SAME line as an across-seed mean; its value and
    its floor/key/k derivation equal the ratified per-seed pairs-c2st
    derivation (unchanged number). The amendment must RECORD that only the
    estimator changed: per_seed -> across_seed_mean, same value.
    """
    change = _amend2_change(1)
    if change is None:
        pytest.skip("no amendment_proposed proposal 2 with a mean change")
    proposed = change["proposed"]
    rule = proposed["derivation"]["rule"]
    derived = _derive(
        proposed["derivation"]["floor_run"],
        rule["key"],
        rule["k"],
        rule.get("rounding", 2),
    )
    assert derived == pytest.approx(proposed["value"])
    assert proposed["value"] == 0.53

    ratified = _gate_1()["views"][PAIRS_VIEW]["derivations"]
    ratified_rule = ratified["rules"]["c2st_auc_max"]
    assert proposed["derivation"]["floor_run"] == ratified["floor_run"]
    assert rule["key"] == ratified_rule["key"]
    assert rule["k"] == ratified_rule["k"]
    # The amendment records an estimator change, not a new number.
    assert change["currently_locked"]["statistic"] == "per_seed"
    assert proposed["statistic"] == "across_seed_mean"
    assert change["currently_locked"]["value"] == proposed["value"]


def test_amendment2_mean_gates_over_twenty_preregistered_seeds():
    """Fix B: the mean is over exactly seeds 0-19, not the 5 locked."""
    change = _amend2_change(1)
    if change is None:
        pytest.skip("no amendment_proposed proposal 2 with a mean change")
    assert change["proposed"]["seed_set"] == list(range(20))


def test_amendment2_operating_characteristics_recompute():
    """Every OC pass-probability recomputes from the stated normal approx.

    Fix B evidence, as data: pass probability at each hypothetical true
    mean under the per-seed >=4/5 rule, the rejected mean-of-5, and the
    proposed mean-of-20, all at the 0.53 line. Recomputed with math.erf
    (no scipy) and rounded to 2 decimals, they must equal the stored
    table. The proposed mean-of-20 must SHARPEN the operating
    characteristic at the line (referee finding 2): 0.50 at 0.530, and
    TIGHTER than the per-seed rule above the line where a mean-of-5 would
    LOOSEN it.
    """
    change = _amend2_change(1)
    if change is None:
        pytest.skip("no amendment_proposed proposal 2 with a mean change")
    oc = change["operating_characteristics"]
    sd = oc["per_seed_sd"]
    line = oc["line"]
    means = oc["true_means"]

    def per_seed_ge_4_of_5(mu, n):
        p = _normal_cdf((line - mu) / sd)
        return p**5 + 5 * p**4 * (1 - p)

    def mean_le_line(mu, n):
        se = sd / math.sqrt(n)
        return _normal_cdf((line - mu) / se)

    fns = {
        "per_seed_ge_4_of_5": per_seed_ge_4_of_5,
        "mean_le_line": mean_le_line,
    }
    for name, spec in oc["estimators"].items():
        fn = fns[spec["statistic"]]
        recomputed = [round(fn(mu, spec["n"]), 2) for mu in means]
        assert recomputed == pytest.approx(spec["pass_prob"]), (
            f"OC {name}: recomputed {recomputed} != stored "
            f"{spec['pass_prob']}"
        )

    idx_line = means.index(0.530)
    idx_above = means.index(0.533)
    ps = oc["estimators"]["per_seed_4_of_5"]["pass_prob"]
    m20 = oc["estimators"]["mean_of_20_proposed"]["pass_prob"]
    m5 = oc["estimators"]["mean_of_5_rejected"]["pass_prob"]
    assert m20[idx_line] == 0.50  # 50% at the line by symmetry
    assert m20[idx_above] < ps[idx_above]  # mean-of-20 sharper (tighter)
    assert m5[idx_above] > ps[idx_above]  # mean-of-5 would loosen


def test_amendment2_considered_line_binds():
    """The rejected tighter mean-of-5 line reproduces exactly (0.5194).

    Even the line the amendment DECLINES to propose is machine-checked:
    round(floor mean + k * sd / sqrt(n), rounding). Kept in
    considered_and_rejected; a rounded-input hand computation reads
    ~0.5196, so the referee weighs the exact committed-artifact value.
    """
    entry = _amend2_rejected("mean_of_five_standard_error_line")
    if entry is None:
        pytest.skip("no amendment 2 rejected mean-of-5 line")
    rule = entry["derivation"]["rule"]
    mean, sd = _floor_stats(entry["derivation"]["floor_run"], rule["key"])
    derived = round(
        mean + rule["k"] * sd / math.sqrt(rule["divide_by_sqrt_n"]),
        rule["rounding"],
    )
    assert derived == pytest.approx(entry["value"])
    assert entry["value"] == 0.5194


def test_amendment2_rejected_cap_binds_to_unmatched_floor():
    """The rejected 0.547 cap reproduces from the 1.9.0 floor sd.

    Disclosure that the original cap was off the wrong version:
    round(1.9.0 floor mean + 8*sd, 3) = 0.547, which the version-matched
    0.554 (change 2) replaces per fix C.
    """
    entry = _amend2_rejected("cap_from_1_9_0_floor_sd")
    if entry is None:
        pytest.skip("no amendment 2 rejected 1.9.0 cap")
    rule = entry["derivation"]["rule"]
    derived = _derive(
        entry["derivation"]["floor_run"],
        rule["key"],
        rule["k"],
        rule.get("rounding", 3),
    )
    assert derived == pytest.approx(entry["value"])
    assert entry["value"] == 0.547
    # It must differ from the adopted, version-matched cap.
    assert _amend2_change(2)["proposed"]["value"] != entry["value"]


def test_amendment2_no_self_rescue_clause_present():
    """Fix A: the verbatim no-self-rescue principle is recorded."""
    amendment = _amendment_2()
    if amendment is None:
        pytest.skip("no amendment_proposed proposal 2")
    clause = amendment.get("no_self_rescue", "")
    assert (
        "committed run verdict changes under a rule proposed after" in clause
    )
    assert "applies only to runs registered after its ratification" in clause


def test_amendment2_illustrative_block_is_not_applied():
    """Fix A: the retroactive table is disclosure only -- applied: false.

    No committed verdict changes: every run's committed_verdict is FAIL,
    the old applied-recomputation key is gone, and candidate 10 -- the
    sole would-flip -- stays FAIL.
    """
    amendment = _amendment_2()
    if amendment is None:
        pytest.skip("no amendment_proposed proposal 2")
    # The old applied verdict-recomputation key must not exist.
    assert "verdict_recomputation" not in amendment
    block = amendment["illustrative_retroactive_application"]
    assert block["applied"] is False
    for entry in block["runs"]:
        assert entry["committed_verdict"] == "FAIL", entry["run"]
    assert block["would_flip_if_applied"]["runs"] == ["candidate 10 (PR #64)"]


def test_amendment2_path_to_pass_requires_fresh_registration():
    """Fix A: a pass needs a fresh registration on seeds 0-19."""
    amendment = _amendment_2()
    if amendment is None:
        pytest.skip("no amendment_proposed proposal 2")
    p = amendment["path_to_pass"]
    assert "FRESH" in p or "fresh" in p
    assert "runs/c10_diagnostics_v1.json" in p
    assert "0.5234" in p


def _recompute_amended_verdict(entry: dict, mean_line: float, cap: float):
    """Recompute the four amended sub-verdicts from a committed artifact.

    Pairs mean/max/battery come from the run's own gate artifact; pooled
    Q0 comes from that artifact's benefit_space_gated block (candidates
    9-10) or the committed downstream-relevance artifact (candidate 7).
    """
    art = json.loads((ROOT / entry["artifact"]).read_text())
    per_seed = art["per_seed"]
    c2st = [s["geometry"][PAIRS_VIEW]["scores"]["c2st_auc"] for s in per_seed]
    pairs_mean = sum(c2st) / len(c2st)
    pairs_max = max(c2st)
    n_battery = sum(bool(s["battery_pass"]) for s in per_seed)

    q0_source = entry.get("q0_source", "not_scored")
    pooled_q0 = None
    if q0_source == "benefit_space_gated":
        pooled_q0 = art["benefit_space_gated"]["pooled_q0_gate"][
            "pooled_q0_mean_pct_diff"
        ]
    elif q0_source == "downstream_relevance":
        q0_art = json.loads((ROOT / entry["q0_artifact"]).read_text())
        pooled_q0 = q0_art["candidate_pooled"]["by_anchor_quintile"]["Q0"][
            "mean_pct_diff"
        ]

    return {
        "pairs_mean": pairs_mean,
        "pairs_max": pairs_max,
        "mean_rule_pass": pairs_mean <= mean_line,
        "cap_pass": pairs_max <= cap,
        "battery_seeds_pass": n_battery,
        "battery_gate_pass": n_battery >= 4,
        "pooled_q0": pooled_q0,
        "q0_pass": None if pooled_q0 is None else abs(pooled_q0) <= 5,
        "old_gate_1_pass": art["verdict"]["gate_1_pass"],
    }


def test_amendment2_illustrative_recomputation_matches_artifacts():
    """Every disclosed number recomputes from the committed artifacts.

    The load-bearing honesty section, now disclosure-only (applied:
    false): for each committed run the disclosed pairs mean, pairs
    max/cap, battery pass count, and pooled Q0 (plus pass/fail) equal a
    fresh recomputation from the run's committed artifact under the
    amended rule (mean line 0.53, version-matched cap 0.554). The
    would-be verdict is consistent -- a PASS satisfies all four
    sub-verdicts; a FAIL is backed by >= 1 failing sub-verdict -- the
    sole would-flip is candidate 10, and NO committed verdict moves.
    """
    amendment = _amendment_2()
    if amendment is None:
        pytest.skip("no amendment_proposed proposal 2")
    block = amendment["illustrative_retroactive_application"]
    assert block["applied"] is False
    mean_line = block["mean_line"]
    cap = block["cap_value"]
    # The disclosure's own line/cap must equal the change derivations.
    assert mean_line == _amend2_change(1)["proposed"]["value"]
    assert cap == _amend2_change(2)["proposed"]["value"]

    flips = []
    for entry in block["runs"]:
        rc = _recompute_amended_verdict(entry, mean_line, cap)
        label = f"{entry['run']} (PR #{entry['pr']})"

        assert entry["pairs_c2st_mean"] == round(rc["pairs_mean"], 4), label
        assert entry["pairs_c2st_max"] == round(rc["pairs_max"], 4), label
        assert entry["mean_rule_pass"] == rc["mean_rule_pass"], label
        assert entry["cap_pass"] == rc["cap_pass"], label
        assert entry["battery_seeds_pass"] == rc["battery_seeds_pass"], label
        assert entry["battery_gate_pass"] == rc["battery_gate_pass"], label

        stated_q0 = entry.get("pooled_q0_mean_pct_diff")
        if rc["pooled_q0"] is None:
            assert stated_q0 is None, f"{label}: stated Q0 but none scored"
            assert entry.get("q0_pass") is None, label
        else:
            assert stated_q0 == round(rc["pooled_q0"], 4), label
            assert entry["q0_pass"] == rc["q0_pass"], label

        # Committed verdict is FAIL for every run and is NOT changed by
        # this amendment (no_self_rescue / applied: false).
        assert entry["committed_verdict"] == "FAIL", label
        assert rc["old_gate_1_pass"] is False, label

        # Would-be (illustrative) verdict consistency.
        sub_pass = [
            rc["mean_rule_pass"],
            rc["cap_pass"],
            rc["battery_gate_pass"],
        ]
        if rc["q0_pass"] is not None:
            sub_pass.append(rc["q0_pass"])
        if entry["would_be_verdict_if_applied"] == "PASS":
            assert all(
                sub_pass
            ), f"{label}: would-PASS but a sub-verdict fails"
            flips.append(label)
        else:
            assert entry["would_be_verdict_if_applied"] == "FAIL", label
            assert not all(
                sub_pass
            ), f"{label}: would-FAIL but every sub-verdict passes"

    # Exactly one committed run WOULD flip, and it is candidate 10 -- but
    # only illustratively; its committed verdict stays FAIL (asserted
    # above for every run).
    assert flips == ["candidate 10 (PR #64)"], flips
    assert flips == block["would_flip_if_applied"]["runs"]
    assert block["would_flip_if_applied"]["count"] == len(flips)


# --------------------------------------------------------------------------
# Amendment 2 RATIFIED bindings (live thresholds)
#
# Amendment 2 (proposed PR #67, referee AMEND -> fixes ae0c166 ->
# verification RATIFY AS-IS -> ratified by merge 4e06e244, flipped live
# 2026-07-07). The proposal-object tests above go dormant once the
# amendment_proposed subsection is removed; these tests bind the SAME
# guarantees at their ratified locations, so a rebuild that shifted a
# floor -- or an edit that quietly reapplied the amendment retroactively
# -- breaks loudly. They touch only committed files.
# --------------------------------------------------------------------------
def _pairs_view() -> dict:
    return _gate_1()["views"]["psid_family_earnings_pairs"]


def test_ratified_mean_rule_keeps_line_and_derivation():
    """The live 20-seed mean rule holds the ratified 0.53 derivation."""
    rule = _pairs_view()["c2st_mean_rule"]
    deriv = rule["derivations"]["rules"]["c2st_auc_mean_max"]
    derived = _derive(
        rule["derivations"]["floor_run"],
        deriv["key"],
        deriv["k"],
        deriv.get("rounding", 2),
    )
    assert derived == pytest.approx(rule["value_max"])
    assert rule["value_max"] == 0.53
    assert deriv["k"] == 4.2  # the ratified per-seed k, unchanged
    assert rule["statistic"] == "across_seed_mean"
    assert rule["seed_set"] == list(range(20))


def test_ratified_cap_binds_to_version_matched_floor():
    """The live per-seed cap == round(matched mean + 8*sd, 3) == 0.554."""
    cap = _pairs_view()["c2st_per_seed_cap"]
    deriv = cap["derivations"]
    mean, sd = _floor_at_path(deriv["floor_run"], deriv["floor_path"])
    rule = deriv["rules"]["c2st_auc_cap"]
    derived = round(mean + rule["k"] * sd, rule.get("rounding", 3))
    assert derived == pytest.approx(cap["value_max"])
    assert cap["value_max"] == 0.554
    assert derived != 0.547  # the rejected version-mismatched cap


def test_ratified_per_seed_c2st_is_superseded_not_gated():
    """c2st_auc left the per-seed geometry; the supersession is recorded."""
    view = _pairs_view()
    assert "c2st_auc_max" not in view["geometry"]
    assert "c2st_auc_max" not in view["derivations"]["rules"]
    assert view["per_seed_rule_superseded"] == ["c2st_auc"]
    # geometry <-> derivations equality still holds after the removal.
    assert set(view["geometry"]) == set(view["derivations"]["rules"])


def test_ratified_operating_characteristics_recompute():
    """Every live OC pass-probability recomputes via the normal approx."""
    oc = _pairs_view()["c2st_mean_rule"]["operating_characteristics"]
    sd, line = oc["per_seed_sd"], oc["line"]
    for name, est in oc["estimators"].items():
        for mu, stored in zip(oc["true_means"], est["pass_prob"], strict=True):
            p = _normal_cdf((line - mu) / sd)
            if est["statistic"] == "per_seed_ge_4_of_5":
                prob = p**5 + 5 * p**4 * (1 - p)
            else:
                se = sd / math.sqrt(est["n"])
                prob = _normal_cdf((line - mu) / se)
            assert round(prob, 2) == pytest.approx(stored), (name, mu)
    # The sharpening claim: above the line the 20-seed mean is
    # STRICTER than the old per-seed rule; the rejected mean-of-5
    # would have been looser.
    at_533 = {
        name: est["pass_prob"][-1] for name, est in oc["estimators"].items()
    }
    assert at_533["mean_of_20_proposed"] < at_533["per_seed_4_of_5"]
    assert at_533["per_seed_4_of_5"] < at_533["mean_of_5_rejected"]


def test_ratified_amendment_is_prospective_no_verdict_changed():
    """no_self_rescue: no PRE-amendment-2 run's verdict changed at the flip.

    The strongest live form of no_self_rescue is backward-looking: every
    gate-run artifact registered BEFORE amendment 2 -- i.e. scored under the
    per-seed pairs c2st rule, not the 20-seed mean rule -- still records
    gate_1_pass false, candidate 10 (run 12) included. A retroactive
    application would have flipped candidate 10; the flip did not touch it.

    A run registered AFTER the 2026-07-07 ratification is scored under the
    20-seed mean rule + per-seed cap (its verdict carries ``c2st_mean_rule_pass``)
    and MAY pass -- amendment_history says a first pass must come from exactly
    such a fresh one-shot registration (candidate 11 / run 13 is the first).
    Those prospective runs are outside this backward-looking guarantee, so the
    invariant is asserted on the pre-amendment set only.
    """
    runs = sorted(ROOT.glob("runs/gate1_*.json"))
    pre_amendment = [
        p
        for p in runs
        if json.loads(p.read_text())["verdict"].get("c2st_mean_rule_pass")
        is None
    ]
    # The committed pre-amendment runs are untouched by the flip: all 12 stand
    # FAIL (candidate 10 among them). Post-amendment runs are excluded.
    assert len(pre_amendment) == 12
    for path in pre_amendment:
        verdict = json.loads(path.read_text())["verdict"]
        assert verdict["gate_1_pass"] is False, path.name


def test_ratified_standing_rules_and_history_record():
    """no_self_rescue + version pin stand; history entry 2 is complete."""
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    gate_1 = gates["gates"]["gate_1"]
    rules = gate_1["amendment_rules"]
    assert "No candidate's committed run verdict changes" in (
        rules["no_self_rescue"]
    )
    assert "scikit-learn" in rules["classifier_version_pin"]
    entry = gate_1["amendment_history"][1]
    assert entry["id"] == "2026-07-07-mean-based-classifier-gating"
    for key in ("referee_round", "ratified", "flipped_live", "content"):
        assert entry[key], key
    assert "PROSPECTIVE ONLY" in entry["content"]
    assert "4904161939" in entry["referee_round"]["review"]
    assert "4905067301" in entry["referee_round"]["verification"]


# --------------------------------------------------------------------------
# Gate 2 DRAFT threshold binding (gate_2.thresholds, status draft, v2)
#
# The gate-2 pre-lock evidence fills the gate_2 stub with a DRAFT thresholds
# block (locked: false, status: draft_pending_referee_round) whose per-cell
# |ln ratio| tolerances are machine-bound to the committed 100-seed
# half-split floor runs/gate2_floors_v2.json exactly as the locked gate-1
# geometry thresholds bind to theirs: tolerance == round(floor mean + k *
# floor sd, rounding). v2 applies the round-1 referee amendments (PR #79
# comment 4910467957): the option-(a) protocol, the 100-seed floor, the
# T_max = ln(1.5) power cap with pre-registered aggregate supersession, the
# joint/sequence cells, the governance inheritance, and the scope map.
# These run everywhere (committed files only) and SKIP the moment gate_2
# leaves the draft status -- a ratification round replaces them with locked
# bindings, just as amendment 1/2's proposal-object tests went dormant.
# --------------------------------------------------------------------------
GATE2_FLOOR_RUN = "runs/gate2_floors_v2.json"
GATE2_FLOOR_KEY = "noise_floor_seeds_0_99"


def _gate_2() -> dict:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    return gates["gates"]["gate_2"]["thresholds"]


def _gate_2_if_draft() -> dict | None:
    """Retained name; post-lock the bindings run unconditionally.

    Amendment-2 lesson: derivation bindings must stay HOT after
    ratification, not go dormant with the draft status.
    """
    return _gate_2()


def _gate2_floor() -> dict:
    return json.loads((ROOT / GATE2_FLOOR_RUN).read_text())


def _gate2_derive(cell: str, k: float, rounding: int) -> float:
    stats = _gate2_floor()[GATE2_FLOOR_KEY][cell]
    return round(stats["mean"] + k * stats["sd"], rounding)


def test_gate2_locked_with_ratification_record():
    """Gate 2 is locked, with the full ceremony recorded in the contract."""
    g2 = _gate_2()
    assert g2["locked"] is True
    assert g2["status"] == "locked"
    record = g2["ratified"]
    for token in (
        "PR 79",
        "4910467957",  # round-1 adversarial review
        "4910712436",  # fixes summary
        "4910856982",  # verification LOCK AS-IS
        "no_self_rescue",
    ):
        assert token in record, token


def test_gate2_floor_run_is_a_reported_anchor():
    """The floor the locked thresholds cite reads no gate."""
    g2 = _gate_2_if_draft()
    assert g2["floor_run"] == GATE2_FLOOR_RUN
    floor = _gate2_floor()
    assert floor["reported_anchor_not_gated"] is True
    assert floor["schema_version"] == "gate2_floors.v2"
    assert "NOT RATIFIED" in floor["draft_thresholds_note"]


def test_gate2_locked_thresholds_bind_to_floor():
    """Every locked tolerance == round(100-seed floor mean + k*sd, rounding).

    The exact machine-binding the locked gate-1 geometry thresholds carry,
    applied to each gate-2 view's ``tolerances`` against the committed
    100-seed half-split floor. Every ``tolerances`` entry has a matching
    ``derivations.rules`` entry whose ``key`` is the floor cell itself.
    """
    g2 = _gate_2_if_draft()
    for view_name, view in g2["views"].items():
        rules = view["derivations"]["rules"]
        tolerances = view["tolerances"]
        assert set(rules) == set(tolerances), view_name
        assert view["derivations"]["floor_run"] == GATE2_FLOOR_RUN
        for cell, rule in rules.items():
            assert rule["key"] == cell, f"{view_name}.{cell}"
            derived = _gate2_derive(cell, rule["k"], rule.get("rounding", 3))
            assert derived == pytest.approx(tolerances[cell]), (
                f"{view_name}.{cell}: derived {derived} != tolerance "
                f"{tolerances[cell]}"
            )


def test_gate2_locked_k_matches_gate1_precedent():
    """Every locked k is the ~4-sigma gate-1 precedent."""
    g2 = _gate_2_if_draft()
    # Post amendment-2 flip: tranche 2a's holdout_basis is re-scoped to
    # mh85_23 + cah85_23 (MX23REL moved to the unlocked gate_2b tranche).
    assert g2["holdout_basis"] == ["mh85_23", "cah85_23"]
    assert g2["floor_run"] == GATE2_FLOOR_RUN
    for view in g2["views"].values():
        for rule in view["derivations"]["rules"].values():
            assert rule["k"] == 4


def test_gate2_power_cap_binds_every_gated_cell():
    """Finding 3: every gated tolerance <= T_max = ln(1.5), and the floor
    partitioned exactly on that cap (+ >=20 events + supersession)."""
    g2 = _gate_2_if_draft()
    if g2 is None:
        pytest.skip("gate_2 is not draft")
    assert g2["power_cap"]["t_max"] == "ln(1.5)"
    floor = _gate2_floor()
    t_max = floor["internal_noise_floor"]["t_max"]
    assert t_max == pytest.approx(math.log(1.5))
    for view in g2["views"].values():
        for cell, tol in view["tolerances"].items():
            assert tol <= t_max, f"{cell} tolerance {tol} exceeds T_max"


def test_gate2_report_only_matches_committed_floor_partition():
    """report_only / gated == the floor's derived partition (events + power
    cap + aggregate supersession), not hand-picked; the two are disjoint."""
    g2 = _gate_2_if_draft()
    if g2 is None:
        pytest.skip("gate_2 is not draft")
    floor = _gate2_floor()
    partition = floor["gate_partition"]
    assert set(g2["report_only"]) == set(partition["report_only"])

    gated = set()
    for view in g2["views"].values():
        gated |= set(view["tolerances"])
    assert gated == set(partition["gate_eligible"])
    assert gated.isdisjoint(set(g2["report_only"]))
    # Every gated cell carries a floor block; the partition covers all cells.
    for cell in gated:
        assert cell in floor[GATE2_FLOOR_KEY], cell


def test_gate2_aggregations_are_pre_registered_and_consistent():
    """Finding 3: the coverage-recovery aggregates match the floor, and a
    gating aggregate demotes every per-age member it spans."""
    g2 = _gate_2_if_draft()
    if g2 is None:
        pytest.skip("gate_2 is not draft")
    floor = _gate2_floor()
    yaml_aggs = g2["power_cap"]["aggregations"]
    art_aggs = floor["aggregations"]
    assert set(yaml_aggs) == set(art_aggs)
    report_only = set(g2["report_only"])
    gated = set()
    for view in g2["views"].values():
        gated |= set(view["tolerances"])
    for agg, spec in yaml_aggs.items():
        assert spec["gated"] == art_aggs[agg]["gated"], agg
        if spec["gated"]:
            assert agg in gated, agg
            for member in art_aggs[agg]["members"]:
                assert member in report_only, (agg, member)


def test_gate2_protocol_is_option_a_gate1_mirror():
    """Finding 1: one coherent protocol -- per-seed refit + simulate holdout,
    scored against the holdout half's own rate, 4-of-5 conjunction."""
    g2 = _gate_2_if_draft()
    if g2 is None:
        pytest.skip("gate_2 is not draft")
    proto = g2["protocol"]
    assert str(proto["option"]).strip().startswith("a")
    assert proto["gate_seeds"] == [0, 1, 2, 3, 4]
    for field in ("split", "candidate", "scored_against", "pass_rule"):
        assert proto[field].strip(), field
    # The finding-1 fix: the candidate is scored against the seed's HOLDOUT
    # half's OWN empirical rate (side A / rate_a), not the full-panel ref.
    assert "holdout" in proto["split"].lower()
    assert "own empirical rate" in proto["scored_against"].lower()
    assert "rate_a" in proto["scored_against"]
    assert ">=4 of 5" in proto["pass_rule"]
    # The OC recorded in the contract matches the artifact's recomputation.
    oc = proto["faithful_candidate_oc"]
    art_oc = _gate2_floor()["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == pytest.approx(art_oc["p_seed_pass"])
    assert oc["p_gate_pass_4_of_5"] == pytest.approx(
        art_oc["p_gate_pass_4_of_5"]
    )
    assert oc["n_gated_cells"] == art_oc["n_gated_cells"]


def test_gate2_governance_inherits_gate1_and_pins_specifics():
    """Finding 5: registration on #42, the inherited no_self_rescue + version
    pin, the holdout-id commitment, the pinned scale, and the in-block weight
    definition all reach gate 2."""
    g2 = _gate_2_if_draft()
    if g2 is None:
        pytest.skip("gate_2 is not draft")
    gov = g2["governance"]
    assert "issue #42" in gov["registration"]
    amend = gov["amendment_rules"]
    assert amend["inherits"] == "gate_1"
    assert "committed run verdict changes" in amend["no_self_rescue"]
    assert "runs registered after its ratification" in amend["no_self_rescue"]
    assert "version" in amend["classifier_version_pin"].lower()
    assert "referee round" in amend["amendments_only_via"]
    assert "holdout" in gov["candidate_scale"].lower()
    assert "sha256" in gov["holdout_id_commitment"]
    # The holdout ids are actually committed in the floor artifact.
    floor = _gate2_floor()
    assert floor["holdout_ids"]["gate_seeds"] == [0, 1, 2, 3, 4]
    assert len(floor["holdout_ids"]["per_seed"]) == 5
    weight = gov["weight_definition"]
    assert "most-recent positive" in weight
    assert "no unweighted gated statistic" in weight.lower()


def test_gate2_scope_declares_provision_classes_and_gaps():
    """Finding 7: the provision-class coverage map + the declared
    marriage x earnings dependence gap + the caregiver/MX23REL precondition."""
    g2 = _gate_2_if_draft()
    if g2 is None:
        pytest.skip("gate_2 is not draft")
    cov = g2["scope"]["provision_class_coverage"]
    assert "COVERED" in cov["marital_and_survivor_timing"]
    assert "MX23REL" in cov["caregiver_and_child_in_care_survivor"]
    assert "NOT COVERED" in cov["caregiver_and_child_in_care_survivor"]
    joint = cov["marriage_x_earnings_joint"]
    assert "NOT COVERED" in joint
    assert "earnings" in joint
    assert g2["scope"]["remarriage_numerator_note"].strip()


def test_gate2_external_anchor_is_period_matched_and_decomposed():
    """Finding 6: the ASFR anchor is period-matched and the marriage/divorce
    anchor is concept-decomposed, both reported not gated."""
    g2 = _gate_2_if_draft()
    if g2 is None:
        pytest.skip("gate_2 is not draft")
    checks = g2["external_anchor_shape_checks"]
    assert "period_matched" in checks["asfr"]
    assert "concept_decomposition" in checks["marriage_divorce"]
    floor = _gate2_floor()
    md = floor["external_anchor"]["marriage_divorce"]
    assert md["concept_decomposition"]["person_to_couple_factor"] == 2.0
    assert "period_matched" in floor["external_anchor"]["asfr"]


# --------------------------------------------------------------------------
# Gate-2 amendment proposal 1 binding (gate_2.amendment_proposed)
#
# The mean-over-draws estimator proposal, mirroring gate 1's amendment-2
# proposal-object tests: an inert public OBJECT that changes no locked value
# and no model reads. These tests bind its arithmetic (the per-cell operating
# characteristic recomputes from the committed forensics; K=20 and the
# 5200+k draw-seed convention are pinned; the k=100 rejection arithmetic and
# the compute cost recompute) and its honesty (applied: false, candidates 8/9
# stay FAIL, the outer verdict is marked not-computable, no locked gate-2
# value moved -- a parsed (structural) compare of the thresholds subtree
# against origin/master; the diff being a pure insertion, the subtree is also
# byte-identical at diff level).
#
# RATIFIED 2026-07-08 (PR #96, merge fec27eb51) and FLIPPED LIVE in the
# following PR: amendment_proposed is now REMOVED, so every test below skips
# (dormant). _gate2_amendment() additionally guards on proposal_number == 1
# (the gate-1 _amendment_2 pattern), so a FUTURE gate-2 proposal (number != 1)
# never reactivates these proposal-1-specific bindings either. The
# load-bearing guarantees these once carried against the pre-flip locked text
# are re-bound at their LIVE post-flip locations in the "Gate-2 amendment 1
# RATIFIED bindings" section at the end of this file. They touch only
# committed files.
# --------------------------------------------------------------------------
GATE2_FORENSICS_RUN = "runs/gate2_forensics_v1.json"


def _gate2_amendment() -> dict | None:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    amendment = gates["gates"]["gate_2"].get("amendment_proposed")
    if amendment is None or amendment.get("proposal_number") != 1:
        return None
    return amendment


def _gate2_amend_change(change_id: int) -> dict | None:
    amendment = _gate2_amendment()
    if amendment is None:
        return None
    for change in amendment["changes"]:
        if change.get("id") == change_id:
            return change
    return None


def _gate2_amend_rejected(entry_id: str) -> dict | None:
    amendment = _gate2_amendment()
    if amendment is None:
        return None
    for entry in amendment.get("considered_and_rejected", []):
        if entry.get("id") == entry_id:
            return entry
    return None


def _forensics_cell(cell: str) -> dict:
    art = json.loads((ROOT / GATE2_FORENSICS_RUN).read_text())
    return art["question_3_rng_stability"]["cells"][cell]


def _mean_clip_prob(cell: str, tol: float, k: int) -> float:
    """Mean over the 5 gate seeds of the per-seed clip probability at K draws.

    Rate-scale normal approximation: a K-draw mean rate ~
    N(train_rate_mean, (train_rate_sd / sqrt(K))**2); it clips when
    |ln(rate / rate_b)| > tol, i.e. the rate falls outside
    [rate_b * e**-tol, rate_b * e**tol]. At K=1 this reproduces the
    committed prob_train_draw_clips_tolerance to machine precision.
    """
    per_seed = _forensics_cell(cell)["per_seed"]
    probs = []
    for stats in per_seed.values():
        rate_b = stats["rate_b_train_reference"]
        mu = stats["train_rate_mean"]
        se = stats["train_rate_sd"] / math.sqrt(k)
        upper = rate_b * math.exp(tol)
        lower = rate_b * math.exp(-tol)
        p = (1.0 - _normal_cdf((upper - mu) / se)) + _normal_cdf(
            (lower - mu) / se
        )
        probs.append(p)
    return sum(probs) / len(probs)


def test_gate2_amendment_status_and_number():
    """Proposal 1 for gate 2, pending a referee round -- inert."""
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    assert amendment["proposal_number"] == 1
    assert amendment["status"] == "proposed_pending_referee_round"


def test_gate2_amendment_k_and_seed_convention():
    """Fix: K=20 and the 5200+k draw-seed convention bind to the forensics.

    The estimator averages the candidate RATE over 20 draws (not the |ln|
    scores), on the committed forensics' pre-registered draw seeds.
    """
    change = _gate2_amend_change(1)
    if change is None:
        pytest.skip("no gate_2 amendment change 1")
    proposed = change["proposed"]
    assert proposed["K"] == 20
    assert proposed["statistic"] == "mean_over_draws"
    assert "5200" in str(proposed["draw_seed_rule"])
    # the mean is of the RATE, not of the |ln| scores
    assert "mean of the candidate STATISTIC" in proposed["rule"]
    assert "NOT the mean" in proposed["rule"]
    # the draw seeds match the committed forensics convention exactly
    art = json.loads((ROOT / GATE2_FORENSICS_RUN).read_text())
    assert art["question_3_rng_stability"]["draw_seeds"] == [
        5200 + k for k in range(20)
    ]
    assert "5200 + k" in art["protocol"]["draw_rng_rule"]


def test_gate2_amendment_operating_characteristics_recompute():
    """Every per-cell OC probability recomputes from the committed forensics.

    Single-draw (K=1) reproduces the artifact's own
    prob_train_draw_clips_tolerance; mean-of-20 (K=20) is the same rate-scale
    model with sd/sqrt(20). The single-draw clips are the 0.49/0.34/0.10/
    0.03/0.00/0.00 the proposal cites. The estimator is NOT a pass-machine:
    the boundary cell mean_lifetime_marriages|male RISES (a real level error),
    while the four noise-dominated cells collapse toward 0.
    """
    change = _gate2_amend_change(1)
    if change is None:
        pytest.skip("no gate_2 amendment change 1")
    oc = change["proposed"]["operating_characteristics"]
    assert oc["K"] == 20
    by_cell = {}
    for entry in oc["per_cell"]:
        cell = entry["cell"]
        by_cell[cell] = entry
        tol = entry["tolerance"]
        # tolerance and tilt cross-check against the committed forensics.
        cd = _forensics_cell(cell)
        assert tol == cd["tolerance"], cell
        summary = cd["summary"]
        assert entry["tilt_over_tolerance"] == pytest.approx(
            round(summary["level_component_over_tolerance"], 3)
        ), cell
        assert entry["abs_tilt"] == pytest.approx(
            round(abs(summary["mean_train_signed_offset_over_seeds"]), 4)
        ), cell
        assert entry["verdict"] == summary["verdict"], cell
        # single-draw column recomputes AND equals the committed artifact.
        single = _mean_clip_prob(cell, tol, 1)
        assert entry["single_draw_clip_prob"] == pytest.approx(
            single, abs=1e-4
        ), cell
        art_single = sum(
            s["prob_train_draw_clips_tolerance"]
            for s in cd["per_seed"].values()
        ) / len(cd["per_seed"])
        assert entry["single_draw_clip_prob"] == pytest.approx(
            art_single, abs=1e-4
        ), cell
        # mean-of-20 column recomputes at K=20 (bound to the estimator).
        mean20 = _mean_clip_prob(cell, tol, 20)
        assert entry["mean_of_20_clip_prob"] == pytest.approx(
            mean20, abs=1e-4
        ), cell

    # The single-draw clips are the cited descending sequence.
    singles = sorted(
        (e["single_draw_clip_prob"] for e in oc["per_cell"]), reverse=True
    )
    assert [round(x, 2) for x in singles] == [0.49, 0.34, 0.10, 0.03, 0.0, 0.0]

    # A genuine super-tolerance level error fails HARDER under averaging;
    # noise-dominated single-draw clips collapse toward zero.
    male = by_cell["mean_lifetime_marriages|male"]
    assert male["verdict"] == "BOUNDARY"
    assert male["mean_of_20_clip_prob"] > male["single_draw_clip_prob"]
    for cell in (
        "mean_lifetime_marriages|female",
        "share_divorced.45-54|female",
        "widowhood.75+|female",
        "completed_fertility.c1970s",
    ):
        e = by_cell[cell]
        assert e["verdict"] == "NOISE-DOMINATED"
        assert e["mean_of_20_clip_prob"] < e["single_draw_clip_prob"]
        assert e["mean_of_20_clip_prob"] < 0.01


def test_gate2_amendment_tolerances_and_conjunction_unchanged():
    """The estimator changes; the error budget does not."""
    change = _gate2_amend_change(1)
    if change is None:
        pytest.skip("no gate_2 amendment change 1")
    proposed = change["proposed"]
    assert proposed["tolerances"] == "unchanged"
    assert "46" in proposed["conjunction"]
    assert "4 of 5" in proposed["conjunction"]


def test_gate2_amendment_changes_no_locked_value():
    """Parsed (structural) compare: gate_2.thresholds parses identical to
    origin/master.

    The proposal adds only the amendment_proposed sibling; every locked
    tolerance, the protocol, the power cap, the governance, and the scope
    map are unchanged. Compares the PARSED thresholds subtree against
    origin/master (structural equality, not a byte compare -- though the diff
    being a pure insertion, the subtree is byte-identical at diff level too);
    self-fetches the ref if needed, and skips only if the ref is unreachable.
    """
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")

    def _master_gates() -> dict | None:
        for attempt in range(2):
            try:
                text = subprocess.run(
                    ["git", "show", "origin/master:gates.yaml"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
                return yaml.safe_load(text)
            except (subprocess.CalledProcessError, FileNotFoundError):
                if attempt == 0:
                    subprocess.run(
                        ["git", "fetch", "origin", "master"],
                        cwd=ROOT,
                        capture_output=True,
                    )
                    continue
                return None
        return None

    master = _master_gates()
    if master is None:
        pytest.skip("origin/master gates.yaml unreachable")
    current = yaml.safe_load((ROOT / "gates.yaml").read_text())
    cur_g2 = current["gates"]["gate_2"]
    assert cur_g2["thresholds"] == master["gates"]["gate_2"]["thresholds"]
    assert cur_g2["thresholds"]["locked"] is True
    assert cur_g2["thresholds"]["status"] == "locked"
    # gate 2 differs from master ONLY by the added amendment_proposed key.
    assert set(cur_g2) - set(master["gates"]["gate_2"]) == {
        "amendment_proposed"
    }


def test_gate2_amendment_no_self_rescue_clause():
    """The verbatim no-self-rescue principle is recorded and inherited."""
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    clause = amendment.get("no_self_rescue", "")
    assert (
        "committed run verdict changes under a rule proposed after" in clause
    )
    assert "applies only to runs registered after its ratification" in clause
    # Matches the inherited gate-2 governance clause (which inherits gate 1).
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    gov = gates["gates"]["gate_2"]["thresholds"]["governance"][
        "amendment_rules"
    ]
    assert gov["inherits"] == "gate_1"
    assert "committed run verdict changes" in gov["no_self_rescue"]


def test_gate2_amendment_illustrative_is_not_applied():
    """applied: false; candidates 8/9 stay FAIL; the outer verdict is honest.

    The load-bearing honesty section: no committed verdict moves, and the
    proposal does NOT fabricate an outer flip -- the committed artifacts hold
    one outer draw per seed, so the amended (20-draw outer) verdict is marked
    not-computable. Each disclosed failing cell's committed outer score and
    tolerance match the run's artifact; each in-forensics cell's train-side
    mean-of-20 clip probability recomputes from the forensics.
    """
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    block = amendment["illustrative_retroactive_application"]
    assert block["applied"] is False
    assert (
        block["would_flip_if_applied"]["computable_from_committed_artifacts"]
        is False
    )

    runs_by = {r["run"]: r for r in block["runs"]}
    assert set(runs_by) == {"candidate 8", "candidate 9"}
    for entry in block["runs"]:
        art = json.loads((ROOT / entry["artifact"]).read_text())
        verdict = art["verdict"]
        assert entry["committed_verdict"] == "FAIL", entry["run"]
        assert verdict["gate_2_pass"] is False, entry["run"]
        assert verdict["n_seeds_pass"] == entry["n_seeds_pass"], entry["run"]
        assert (
            entry["outer_mean_of_20_verdict"] == "NOT_COMPUTABLE_OUTER"
        ), entry["run"]

        # The disclosed failing cells match the committed artifact exactly.
        committed = {
            (f["cell"], f["seed"]): f
            for f in verdict["all_failing_gated_cells"]
        }
        for fc in entry["failing_cells"]:
            key = (fc["cell"], fc["seed"])
            assert key in committed, (entry["run"], key)
            src = committed[key]
            assert fc["outer_score"] == round(src["score"], 4), key
            assert fc["tolerance"] == src["tolerance"], key
            assert fc["outer_mean_of_20_computable"] is False, key
            if fc["in_forensics"]:
                mean20 = _mean_clip_prob(fc["cell"], fc["tolerance"], 20)
                assert fc["train_mean_of_20_clip_prob"] == pytest.approx(
                    mean20, abs=1e-4
                ), key
            else:
                assert fc["train_mean_of_20_clip_prob"] is None, key
        # Every committed failing cell is disclosed (no cherry-picking).
        assert len(entry["failing_cells"]) == len(
            verdict["all_failing_gated_cells"]
        ), entry["run"]


def test_gate2_amendment_c2_gross_level_still_fails():
    """A model with genuine super-tolerance level errors fails at any K.

    The c2 illustration's examples recompute from candidate 2's committed
    artifact and clear tolerance by a wide, draw-noise-proof margin. Each
    stated outer_score binds EXACTLY to round(committed score, 4) -- the same
    convention the c8/c9 rows use in test_gate2_amendment_illustrative_is_not
    _applied -- not a loose abs=1e-3 tolerance, so no illustration digit can
    drift from the committed artifact (referee fix A).
    """
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    illo = amendment["illustrative_retroactive_application"][
        "c2_gross_level_illustration"
    ]
    art = json.loads((ROOT / illo["artifact"]).read_text())
    committed = {
        (f["cell"], f["seed"]): f
        for f in art["verdict"]["all_failing_gated_cells"]
    }
    for ex in illo["examples"]:
        key = (ex["cell"], ex["seed"])
        assert key in committed, key
        src = committed[key]
        assert ex["outer_score"] == round(src["score"], 4), key
        assert ex["tolerance"] == src["tolerance"], key
        # Orders of magnitude over tolerance: far beyond any draw-noise sd.
        assert src["score"] / src["tolerance"] > 2.0, key
        assert ex["score_over_tolerance"] == pytest.approx(
            src["score"] / src["tolerance"], abs=0.1
        ), key


def test_gate2_amendment_considered_and_rejected():
    """Three alternatives are recorded rejected; the k=100 math recomputes."""
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    ids = {e["id"] for e in amendment["considered_and_rejected"]}
    assert {"widen_tolerances", "unfreeze_rng_best_of_n", "k_100"} <= ids

    k100 = _gate2_amend_rejected("k_100")
    arith = k100["arithmetic"]
    assert arith["compute_multiplier"] == 5
    # Recompute the max precision gain sd(K=20)/sd(K=100) over the 6 cells.
    floor = _gate2_floor()[GATE2_FLOOR_KEY]
    art = json.loads((ROOT / GATE2_FORENSICS_RUN).read_text())
    cells = art["question_3_rng_stability"]["cells"]
    worst = 0.0
    for cell, cd in cells.items():
        floor_sd = floor[cell]["sd"]
        draw_sd = sum(
            s["train_signed_logratio_sd"] for s in cd["per_seed"].values()
        ) / len(cd["per_seed"])
        sd20 = math.sqrt(floor_sd**2 + (draw_sd / math.sqrt(20)) ** 2)
        sd100 = math.sqrt(floor_sd**2 + (draw_sd / math.sqrt(100)) ** 2)
        worst = max(worst, sd20 / sd100)
    assert worst < 1.1  # < 1.1x precision for 5x compute
    assert arith["precision_gain_max"] == pytest.approx(worst, abs=1e-3)


def test_gate2_amendment_compute_cost_recorded():
    """The ~20 min/candidate figure ties to candidate 8's committed runtime.

    Also binds the forensics compute field, relabeled (referee fix B) as the
    5-seed TOTAL: it recomputes as the forensics' total_per_seed_compute
    _seconds and as the sum of its per-seed breakdown, and the old
    per-seed-labelled key is gone.
    """
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    cc = amendment["compute_cost"]
    c8 = json.loads((ROOT / "runs/gate2_hazard_v8.json").read_text())
    assert cc["one_shot_seconds_candidate8"] == pytest.approx(
        c8["elapsed_seconds"], abs=0.05
    )
    assert cc["estimator_multiplier"] == 20
    expected_min = c8["elapsed_seconds"] * 20 / 60.0
    assert cc["estimated_minutes_per_candidate"] == pytest.approx(
        expected_min, abs=1.0
    )
    # Referee fix B: the 155.1 s field is the 5-seed TOTAL, honestly labelled.
    assert "forensics_measured_20draw_5seed_per_seed_compute_seconds" not in cc
    total = cc["forensics_measured_20draw_5seed_total_compute_seconds"]
    fx = json.loads((ROOT / GATE2_FORENSICS_RUN).read_text())
    assert total == fx["total_per_seed_compute_seconds"]
    assert total == pytest.approx(
        sum(fx["per_seed_compute_seconds"].values()), abs=0.05
    )


def test_gate2_amendment_path_to_pass_and_process_statement():
    """A pass needs a fresh candidate-10 registration; timing is disclosed."""
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    path = amendment["path_to_pass"]
    assert "FRESH" in path or "fresh" in path
    assert "candidate 10" in path
    ps = amendment["illustrative_retroactive_application"]["process_statement"]
    # The goalpost-timing question is named, not hidden.
    assert "after" in ps.lower()
    assert "goalpost" in ps.lower()


def test_gate2_amendment_registration_divergence_disclosed():
    """Referee fix B: currently_locked names the seed-convention divergence.

    The pre-flip locked text named only the simulation seed; every committed
    run v1-v9 uniformly registered default_rng(4200 + seed). The proposal's
    disclosure names both, and the cited protocol.sim_rng_rule recomputes
    identically across all nine committed artifacts. Proposal-object check;
    the POST-flip live candidate text (which now records the 4200+s history
    and the 5200+k convention explicitly) is asserted in
    test_gate2_ratified_registration_divergence_recorded.
    """
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    locked = _gate2_amend_change(1)["currently_locked"]
    rd = locked["registration_divergence"]
    # Names the locked-text seed s and the committed 4200 + s convention.
    assert "simulation seed s" in rd
    assert "4200 + seed" in rd
    assert "sim_rng_rule" in rd
    # The cited evidence recomputes: all nine committed runs are identical.
    rules = set()
    for v in range(1, 10):
        art = json.loads((ROOT / f"runs/gate2_hazard_v{v}.json").read_text())
        rules.add(art["protocol"]["sim_rng_rule"])
    assert rules == {"numpy.random.default_rng(4200 + seed)"}


def test_gate2_amendment_flip_edits_enumerated():
    """Referee fix B: the flip's locked-text edits are enumerated in advance.

    flip_on_ratification.flip_edits names every locked-TEXT change the flip PR
    makes (protocol.candidate, statistic, pass_rule, the faithful_candidate_oc
    basis note, and the stray DRAFT label). Proposal-object check on the five
    enumerated keys; the locked_text_now presence assertions this test once
    carried described the PRE-flip locked block, so the POST-flip live text
    (the amended estimator with the DRAFT label removed) is asserted instead in
    test_gate2_ratified_estimator_is_mean_over_k20_draws.
    """
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    edits = amendment["flip_on_ratification"]["flip_edits"]
    assert {e["key"] for e in edits} == {
        "candidate",
        "statistic",
        "pass_rule",
        "faithful_candidate_oc",
        "draft_label",
    }


def test_gate2_amendment_fresh_run_artifact_schema():
    """Referee fix C: the candidate-10 run contract is pinned prospectively.

    A fresh run must commit (i) per-draw per-cell rates (20 x 46 x 5) so rbar
    recomputes from the artifact, (ii) a pre-specified undefined-draw rule
    that invalidates the run rather than dropping a draw, and (iii) a
    report-only per-draw dispersion disclosure (per-cell per-draw sd and the
    max per-draw |ln| per cell), never gated. path_to_pass references it.
    """
    amendment = _gate2_amendment()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed")
    schema = amendment["fresh_run_artifact_schema"]

    # (i) per-draw per-cell rates committed so rbar recomputes.
    rates = schema["per_draw_per_cell_rates"]
    assert rates["required"] is True
    assert rates["shape"] == [20, 46, 5]
    assert "recomputes" in rates["rule"]

    # (ii) undefined-draw rule: run-invalidating, no silent drop.
    undef = schema["undefined_draw_rule"]
    assert undef["required"] is True
    assert undef["pre_specified"] is True
    rule = undef["rule"]
    assert "INVALIDATED" in rule
    assert "No draw may be dropped" in rule

    # (iii) report-only per-draw dispersion, never gated.
    disp = schema["per_draw_dispersion_disclosure"]
    assert disp["required"] is True
    assert disp["gated"] is False
    assert set(disp["commit"].keys()) == {
        "per_cell_per_draw_sd",
        "max_per_draw_abs_ln_per_cell",
    }

    # path_to_pass points a candidate-10 run at the schema.
    assert "fresh_run_artifact_schema" in amendment["path_to_pass"]


# --------------------------------------------------------------------------
# Gate-2 amendment proposal 2 binding (gate_2.amendment_proposed,
# proposal_number 2)
#
# The tranche-split proposal (external review #106 finding 4): re-scope the
# locked gate_2 block as tranche 2a_marital_fertility, declare
# 2b_relationship_household and 2c_marriage_earnings_joint as separate
# UNLOCKED tranches, and add a certification_scope map -- so the fresh gate-2
# PASS (candidate 16, PR #109) cannot be over-read as household /
# auxiliary-benefit readiness. Like amendment 1 it is an inert public OBJECT:
# it changes no locked value and no model reads it. Unlike amendment 1 it
# moves NO number at all (a structural amendment, not an estimator
# recalibration). These tests bind its structure (three tranches; 2a == the
# locked 46 gated + 16 report-only cells, byte-identical to origin/master;
# the certification_scope map covers every locked provision class) and its
# honesty (no threshold / verdict / scored-cell moves; candidate 16 PASS and
# candidates 1-15 FAIL stand unchanged; the flip edits cite text present in
# the locked block). All are no-ops (skip) until an amendment_proposed with
# proposal_number 2 exists -- so they stay dormant under amendment 1 and
# after this proposal is itself ratified and consumed. They touch only
# committed files.
# --------------------------------------------------------------------------
def _gate2_amendment2() -> dict | None:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    amendment = gates["gates"]["gate_2"].get("amendment_proposed")
    if amendment is None or amendment.get("proposal_number") != 2:
        return None
    return amendment


def _gate2_amend2_change(change_id: int) -> dict | None:
    amendment = _gate2_amendment2()
    if amendment is None:
        return None
    for change in amendment["changes"]:
        if change.get("id") == change_id:
            return change
    return None


def _master_gate2() -> dict | None:
    """origin/master gate_2, self-fetching the ref if needed."""
    for attempt in range(2):
        try:
            text = subprocess.run(
                ["git", "show", "origin/master:gates.yaml"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            return yaml.safe_load(text)["gates"]["gate_2"]
        except (subprocess.CalledProcessError, FileNotFoundError):
            if attempt == 0:
                subprocess.run(
                    ["git", "fetch", "origin", "master"],
                    cwd=ROOT,
                    capture_output=True,
                )
                continue
            return None
    return None


def _gated_report_sets(thresholds: dict) -> tuple[set, set]:
    gated = set()
    for view in thresholds["views"].values():
        gated |= set(view["tolerances"])
    return gated, set(thresholds["report_only"])


def test_gate2_amendment2_status_and_number():
    """Proposal 2 for gate 2, pending a referee round -- inert."""
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    assert amendment["proposal_number"] == 2
    assert amendment["status"] == "proposed_pending_referee_round"


def test_gate2_amendment2_is_structural_zero_threshold_movement():
    """Every change is structural: no threshold / verdict / cell move."""
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    types = {c["type"] for c in amendment["changes"]}
    assert types == {"structural_tranche_split", "language_rescope"}
    for change in amendment["changes"]:
        assert change["threshold_change"] is False, change["id"]
        assert change["verdict_change"] is False, change["id"]
        assert change["scored_cell_change"] is False, change["id"]


def test_gate2_amendment2_declares_three_tranches():
    """2a locked; 2b, 2c declared unlocked with no lock ceremony yet."""
    change = _gate2_amend2_change(1)
    if change is None:
        pytest.skip("no gate_2 amendment 2 change 1")
    a = change["tranche_2a"]
    b = change["tranche_2b"]
    c = change["tranche_2c"]
    assert a["id"] == "2a_marital_fertility"
    assert a["status"] == "locked"
    assert b["id"] == "2b_relationship_household"
    assert b["status"] == "unlocked"
    assert b["locked"] is False
    assert b["holdout_basis"] == ["MX23REL"]
    assert b["lock_ceremony"]["exists"] is False
    assert c["id"] == "2c_marriage_earnings_joint"
    assert c["status"] == "unlocked"
    assert c["locked"] is False
    assert c["lock_ceremony"]["exists"] is False


def test_gate2_amendment2_tranche_2a_is_the_locked_cells():
    """2a == the locked 46 gated + 16 report-only cells; not MX23REL.

    The counts recompute from the locked views' tolerances and the
    report_only list AND from the committed floor's gate_partition, and 2a's
    claimed holdouts are mh85_23 + cah85_23 (+ deaths), never MX23REL.
    """
    change = _gate2_amend2_change(1)
    if change is None:
        pytest.skip("no gate_2 amendment 2 change 1")
    a = change["tranche_2a"]
    assert a["gated_cells"] == 46
    assert a["report_only_cells"] == 16
    gated, report_only = _gated_report_sets(_gate_2())
    assert len(gated) == a["gated_cells"]
    assert len(report_only) == a["report_only_cells"]
    # the committed floor partition is the canonical source.
    partition = _gate2_floor()["gate_partition"]
    assert set(partition["gate_eligible"]) == gated
    assert set(partition["report_only"]) == report_only
    # 2a claims only mh85_23 + cah85_23 (+ deaths), NOT MX23REL.
    claims = a["claims_only"]
    assert claims["holdouts"] == ["mh85_23", "cah85_23"]
    assert claims["excludes"] == "MX23REL"


def test_gate2_amendment2_cell_sets_byte_identical_to_master():
    """The 46 gated + 16 report-only cell SETS equal origin/master's.

    Direct form of "no scored cell changed": the sets derived from the
    current locked block equal those derived from origin/master's locked
    block. Skips only if the ref is unreachable.
    """
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    master = _master_gate2()
    if master is None:
        pytest.skip("origin/master gates.yaml unreachable")
    cur_gated, cur_ro = _gated_report_sets(_gate_2())
    m_gated, m_ro = _gated_report_sets(master["thresholds"])
    assert cur_gated == m_gated
    assert cur_ro == m_ro
    assert len(cur_gated) == 46
    assert len(cur_ro) == 16


def test_gate2_amendment2_changes_no_locked_value():
    """Parsed compare: gate_2.thresholds parses identical to origin/master.

    The proposal adds only the amendment_proposed sibling; every locked
    tolerance, the protocol, the power cap, the governance, the report_only
    list, and the scope map are unchanged. gate_2 adds AT MOST the
    amendment_proposed key beyond master's (referee fix D1: subset, not
    equality -- at the ratifying merge both sides contain the object, the
    difference is empty, and the strict-equality form turned master CI red
    for ~68 minutes at amendment 1's ratification, run 28954709231 on
    fec27eb, until the flip landed. The thresholds-equality and locked-flag
    asserts hold in EVERY state, so they stay unconditional).
    """
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    master = _master_gate2()
    if master is None:
        pytest.skip("origin/master gates.yaml unreachable")
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    cur_g2 = gates["gates"]["gate_2"]
    assert cur_g2["thresholds"] == master["thresholds"]
    assert cur_g2["thresholds"]["locked"] is True
    assert cur_g2["thresholds"]["status"] == "locked"
    # subset: {} at the ratify-merge window, {amendment_proposed} before it;
    # anything else (a second added key, a removed key surfacing as a bogus
    # diff) still fails loudly.
    assert set(cur_g2) - set(master) <= {"amendment_proposed"}


def test_gate2_amendment2_certification_scope_covers_locked_classes():
    """The map covers every provision class in the locked scope_note.

    provision_class_map's classes equal the locked provision_class_coverage
    keys; each row's requires_tranche list and locked_coverage token are bound
    EXACTLY (referee fix B / P1: a one-token flip must break a test), and the
    map cites both the scope_note and #74.
    """
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    scope = amendment["certification_scope"]
    locked_cov = _gate_2()["scope"]["provision_class_coverage"]
    rows = scope["provision_class_map"]
    by_class = {r["provision_class"]: r for r in rows}
    assert set(by_class) == set(locked_cov)
    # EXACT per-class bindings. requires_tranche is order-sensitive and the
    # locked_coverage token is pinned, so caregiver [2a, 2b] -> [2a], or
    # "NOT COVERED HERE" -> "NOT COVERED" (in EITHER the map or the locked
    # note), breaks this test -- the P1 hole the <= / startswith form left.
    expected = {
        "marital_and_survivor_timing": {
            "locked_coverage": "COVERED",
            "requires_tranche": ["2a_marital_fertility"],
        },
        "caregiver_and_child_in_care_survivor": {
            "locked_coverage": "NOT COVERED HERE",
            "requires_tranche": [
                "2a_marital_fertility",
                "2b_relationship_household",
            ],
        },
        "marriage_x_earnings_joint": {
            "locked_coverage": "NOT COVERED",
            "requires_tranche": ["2c_marriage_earnings_joint"],
        },
    }
    assert set(by_class) == set(expected)
    declared = {
        "2a_marital_fertility",
        "2b_relationship_household",
        "2c_marriage_earnings_joint",
    }
    for cls, exp in expected.items():
        r = by_class[cls]
        # exact, order-sensitive list -- a single-token flip breaks it.
        assert r["requires_tranche"] == exp["requires_tranche"], cls
        assert set(r["requires_tranche"]) <= declared, cls
        # exact coverage token (not startswith).
        assert r["locked_coverage"] == exp["locked_coverage"], cls
        # and the token must EXACTLY reproduce the locked note's coverage
        # designation (before the " -- " gloss and any "(gated)" paren), so a
        # degrade in EITHER the map or the note breaks the test.
        note_cov = locked_cov[cls].split(" -- ")[0].split(" (")[0].strip()
        assert r["locked_coverage"] == note_cov, cls
    # both sources cited.
    basis = scope["derivation_basis"]
    assert "provision_class_coverage" in basis["locked_scope_note"]
    assert "#74" in basis["provision_matrix"]
    # 2a supports caregiver credits + survivor/spousal timing.
    supports = " ".join(scope["tranches"]["2a_marital_fertility"]["supports"])
    assert "caregiver credits" in supports
    assert "survivor" in supports and "spousal" in supports
    # 2b required for household poverty + child-in-care survivor; 2c joint.
    b = " ".join(
        scope["tranches"]["2b_relationship_household"]["required_for"]
    )
    assert "household-unit poverty" in b
    assert "child-in-care survivor" in b
    c = " ".join(
        scope["tranches"]["2c_marriage_earnings_joint"]["required_for"]
    )
    assert "earnings" in c and "marital" in c


def test_gate2_amendment2_verdict_preservation():
    """Candidate 16 PASS and candidates 1-15 FAIL stand -- no re-scoring.

    The disclosed verdicts equal the committed artifacts, and the amendment
    records no_rescoring / no_verdict_change.
    """
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    vp = amendment["verdict_preservation"]
    assert vp["no_rescoring"] is True
    assert vp["no_verdict_change"] is True
    # candidate 16 is a committed PASS 4/5.
    p = vp["passing_run"]
    assert p["run"] == "candidate 16"
    c16 = json.loads((ROOT / p["artifact"]).read_text())["verdict"]
    assert c16["gate_2_pass"] is True
    assert c16["n_seeds_pass"] == p["n_seeds_pass"] == 4
    # candidates 1-15 all committed FAIL.
    for v in range(1, 16):
        art = json.loads((ROOT / f"runs/gate2_hazard_v{v}.json").read_text())
        assert art["verdict"]["gate_2_pass"] is False, v


def test_gate2_amendment2_considered_and_rejected():
    """The three rejected alternatives are recorded."""
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    ids = {e["id"] for e in amendment["considered_and_rejected"]}
    assert {
        "leave_scope_in_prose",
        "unlock_2b_now",
        "rename_gate2_to_gate2a_repo_wide",
    } <= ids
    for entry in amendment["considered_and_rejected"]:
        assert entry["reason"].strip().startswith("REJECTED"), entry["id"]


def test_gate2_amendment2_process_statement_and_no_self_rescue():
    """Timing disclosed (first pass), no number moves, clause recorded."""
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    ps = amendment["process_statement"]
    assert "after" in ps.lower()
    assert "candidate 16" in ps
    assert "no number" in ps.lower()
    clause = amendment.get("no_self_rescue", "")
    assert (
        "committed run verdict changes under a rule proposed after" in clause
    )
    assert "applies only to runs registered after its ratification" in clause
    gov = _gate_2()["governance"]["amendment_rules"]
    assert gov["inherits"] == "gate_1"


def test_gate2_amendment2_flip_edits_enumerated():
    """The flip's locked-text edits cite text present in the locked block.

    Each flip_edit's locked_text_now appears at its locked_path in the
    current locked block, and flip_additions enumerate the new tranche stubs.
    Referee fixes C1-C3: the enumeration is COMPLETE -- the computes-exactly
    formula clause has an explicit disposition, the stale "This DRAFT
    tranche" label and the holdout_basis cross-reference are enumerated as
    edits, and gate_2.name carries a recommendation-level disposition.
    """
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    flip = amendment["flip_on_ratification"]
    edits = flip["flip_edits"]
    assert {e["key"] for e in edits} == {
        "description",
        "description_formula_clause",
        "holdout_basis",
        "scope_note",
        "scope_note_draft_label",
        "scope_note_holdout_xref",
    }
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())

    def _resolve(path: str):
        node = gates
        for part in path.split("."):
            node = node["gates"]["gate_2"] if part == "gate_2" else node[part]
        return node

    for e in edits:
        node = _resolve(e["locked_path"])
        hay = node if isinstance(node, str) else str(node)
        assert e["locked_text_now"] in hay, e["key"]
    by_key = {e["key"]: e for e in edits}
    # C1: the formula clause is RETAINED, not silently deleted or kept.
    assert "RETAINED" in by_key["description_formula_clause"]["flip_change"]
    # C2: the stale DRAFT label and the holdout_basis cross-reference.
    assert (
        "This DRAFT tranche"
        in by_key["scope_note_draft_label"]["locked_text_now"]
    )
    assert (
        "named in holdout_basis"
        in by_key["scope_note_holdout_xref"]["locked_text_now"]
    )
    # C3: gate_2.name has a recommendation-level disposition quoting the
    # live name exactly.
    nd = flip["name_disposition"]
    assert nd["recommendation"] == "retain"
    assert nd["gate_2_name_now"] == gates["gates"]["gate_2"]["name"]
    assert nd["reason"]
    # the additions name the three tranche structures the flip introduces,
    # plus the standing governance rule (finding 8).
    additions = " ".join(flip["flip_additions"])
    assert "2a_marital_fertility" in additions
    assert "gate_2b" in additions
    assert "gate_2c" in additions
    assert "standing_rule" in additions


def test_gate2_amendment2_formula_clause_disposition():
    """Fix C1: the computes-exactly clause has an explicit disposition.

    currently_locked.description quotes the live gate_2.description VERBATIM
    (folded to one line), proposed.description states the clause is RETAINED
    (statutory-formula oracle territory, outside the tranche split), and the
    live locked description still carries the clause the flip retains.
    """
    change = _gate2_amend2_change(2)
    if change is None:
        pytest.skip("no gate_2 amendment 2 change 2")
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    live_description = gates["gates"]["gate_2"]["description"]
    quoted = change["currently_locked"]["description"]
    # verbatim quote: the live description appears inside the quoted text,
    # quote marks and all (both are folded scalars -- single-line strings).
    assert live_description in quoted
    # the second clause is live, and its disposition is mirrored in
    # proposed.description (fix C1: no silent delete, no silent keep).
    assert 'per-rule "computes exactly"' in live_description
    proposed = change["proposed"]["description"]
    assert "computes exactly" in proposed
    assert "RETAINED" in proposed


def test_gate2_amendment2_standing_governance_rule():
    """Finding 8's standing rule, attributed to this referee round.

    A gate / tranche description and holdout_basis must claim EXACTLY the
    scored surface at lock time; the rule applies to 2b / 2c / gate 3 and is
    enumerated for promotion into the locked governance by the flip.
    """
    amendment = _gate2_amendment2()
    if amendment is None:
        pytest.skip("no gate_2 amendment_proposed proposal 2")
    rule = amendment["governance"]["standing_rule"]
    assert rule["id"] == "description_claims_exactly_the_scored_surface"
    assert "EXACTLY" in rule["rule"]
    assert "holdout_basis" in rule["rule"]
    assert set(rule["applies_to"]) == {
        "2b_relationship_household",
        "2c_marriage_earnings_joint",
        "gate_3",
    }
    # attributed to THIS round, not presented as pre-existing.
    assert "#106" in rule["attributed_to"]
    assert "#111" in rule["attributed_to"]
    assert rule["promoted_by_flip"]


# --------------------------------------------------------------------------
# Gate-2 amendment 1 RATIFIED bindings (live thresholds)
#
# Amendment 1 (proposed PR #96; referee AMEND comment 4915412987 -> fixes
# 5b70840 / comment 4916048161 -> verification RATIFY AS-IS comment
# 4916419901 -> ratified by merge fec27eb51; flipped live this PR). The
# proposal-object tests above go dormant once amendment_proposed is removed;
# these bind the SAME load-bearing guarantees at their LIVE locations, so a
# rebuild that shifted a floor -- or an edit that quietly reverted the flip or
# reapplied it retroactively -- breaks loudly. The gate-1 amendment-2 lesson:
# ratified bindings must stay HOT, not go dormant with the proposal object.
# They touch only committed files.
# --------------------------------------------------------------------------
def _gate2_proto() -> dict:
    return _gate_2()["protocol"]


def test_gate2_ratified_estimator_is_mean_over_k20_draws():
    """The live locked estimator is the mean over K=20 draws (5200+k), r->rbar.

    flip_edits candidate / statistic / pass_rule / draft_label, applied: the
    locked text now names K=20, default_rng(5200 + k), the 20-draw mean cell
    rate, and rbar_candidate,s; the pre-flip single-draw phrasing and the stray
    DRAFT label are gone. Tolerances and the 4-of-5 conjunction are unchanged.
    """
    proto = _gate2_proto()
    candidate = proto["candidate"]
    assert "K=20" in candidate
    assert "5200 + k" in candidate
    assert "20-draw mean cell rate" in candidate
    assert "one replicate, simulation seed s" not in candidate  # old text gone
    statistic = _gate_2()["statistic"]
    assert "rbar_candidate,s" in statistic
    assert "mean over K=20" in statistic
    assert "|ln(r_candidate,s" not in statistic  # bare single-draw form gone
    pass_rule = proto["pass_rule"]
    assert "rbar_candidate,s" in pass_rule
    assert "DRAFT" not in pass_rule  # stray draft label removed
    assert ">=4 of 5" in pass_rule  # conjunction unchanged
    # The mean is of the RATE then scored once, not the mean of |ln| scores.
    assert "NOT the mean of the per-draw" in pass_rule


def test_gate2_ratified_registration_divergence_recorded():
    """The amended locked candidate records the 4200+s history and 5200+k.

    Referee fix B, carried live: every committed run v1-v9 registered
    default_rng(4200 + seed); the flipped candidate text now names both that
    history and the new pre-registered 5200+k draw convention explicitly.
    """
    candidate = _gate2_proto()["candidate"]
    assert "4200 + seed" in candidate  # the committed registration history
    assert "5200 + k" in candidate  # the new pre-registered draw convention
    # The cited history recomputes: all nine committed runs are identical.
    rules = set()
    for v in range(1, 10):
        art = json.loads((ROOT / f"runs/gate2_hazard_v{v}.json").read_text())
        rules.add(art["protocol"]["sim_rng_rule"])
    assert rules == {"numpy.random.default_rng(4200 + seed)"}


def test_gate2_ratified_fresh_run_artifact_schema_is_live():
    """The candidate-10 run contract now lives in the locked protocol.

    per-draw per-cell rates (20 x 46 x 5) so rbar recomputes; a pre-specified
    undefined-draw rule that INVALIDATES the run rather than dropping a draw;
    and a report-only (never gated) per-draw dispersion disclosure.
    """
    schema = _gate2_proto()["fresh_run_artifact_schema"]
    rates = schema["per_draw_per_cell_rates"]
    assert rates["required"] is True
    assert rates["shape"] == [20, 46, 5]
    assert "recomputes" in rates["rule"]
    undef = schema["undefined_draw_rule"]
    assert undef["required"] is True
    assert undef["pre_specified"] is True
    assert "INVALIDATED" in undef["rule"]
    assert "No draw may be dropped" in undef["rule"]
    disp = schema["per_draw_dispersion_disclosure"]
    assert disp["gated"] is False
    assert disp["report_only"] is True
    assert set(disp["commit"]) == {
        "per_cell_per_draw_sd",
        "max_per_draw_abs_ln_per_cell",
    }


def test_gate2_ratified_faithful_oc_basis_matches_amended_estimator():
    """faithful_candidate_oc stands unchanged and its basis now MATCHES.

    The numbers (0.9404 / 0.9685) are byte-identical to the lock and to the
    floor artifact; the added basis note records that the draw-noise-free
    half-normal basis matches the mean-over-K estimator, whereas the
    single-draw estimator made them unachievable (finding 1).
    """
    oc = _gate2_proto()["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == 0.9404
    assert oc["p_gate_pass_4_of_5"] == 0.9685
    art_oc = _gate2_floor()["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == pytest.approx(art_oc["p_seed_pass"])
    assert oc["p_gate_pass_4_of_5"] == pytest.approx(
        art_oc["p_gate_pass_4_of_5"]
    )
    basis = oc["basis_note"].lower()
    assert "draw-noise-free" in basis
    assert "unachievable" in basis
    assert "amendment 1" in basis


def test_gate2_ratified_amendment_is_prospective_no_verdict_changed():
    """No committed run's verdict changed at the flip; candidate 16 is the first
    pass -- a model delta under the locked gate, NOT an amendment self-rescue.

    The strongest live form of no_self_rescue: no PRE-candidate-16 run's verdict
    was changed by the amendment-1 flip -- every gate-2 run through candidate 15
    still records gate_2_pass false. The nine pre-amendment single-draw
    candidates (v1-v9) AND candidates 10, 11, 12, 13, 14 and 15, the six fresh
    registrations under fresh_run_artifact_schema (the amended
    mean-over-K=20-draws estimator), all stand FAIL. Candidate 14 (FAIL 2/5)
    split the surviving-spouse widowhood table's pooled 75+ band into 75-84 and
    85+: it recovered the 75+ widowhood incidence toward reference (seed-mean
    sim/ref 0.929 -> 0.952), but the exposure-preserving reallocation left the
    aggregate 75+ widowed stock flat (0.841 -> 0.838). Candidate 15 (FAIL 3/5)
    removed the NCHS period-trend multiplier: it lifted the 75+ incidence past
    reference (0.952 -> 1.060) and cleared seed 0's stock, but the aggregate
    stock barely moved (0.838 -> 0.841) and share_widowed.75+|female still
    failed seeds 2 and 3 on the tolerance edge, so the gate held at 3/5 -- no
    passing run through candidate 15. The amendment rescued nothing.

    Candidate 16 (PASS 4/5) is the FIRST passing gate-2 run -- registered on
    issue #42 comment 4929419524 from forensics 4 (#108) and run ONCE under the
    LOCKED gate and the already-ratified amendment 1. It conditions the
    surviving-spouse widowhood hazard on the observed support-composition
    stratum (whether the observed support window reaches age 75), both strata
    train-estimated per band x sex, recombining to candidate 15's band aggregate
    by the exposure-weighted identity. That closed the forensics-4 Q9
    survival-to-75+ yield leak (75+ widowed stock 0.841 -> 0.914 of reference),
    clearing share_widowed.75+|female on all five seeds; the gate passes 4/5 on
    the registered pass path (seeds 0, 1, 3, 4), with seed 2 failing only the
    RNG-isolated completed_fertility.c1970s split artifact. This is a MODEL
    delta under the locked gate, not an amendment self-rescue: the gate
    thresholds, protocol and amendment 1 were all locked/ratified BEFORE
    candidate 16 was registered, so no committed verdict changed under a rule
    proposed after its run.
    """
    runs = sorted(ROOT.glob("runs/gate2_hazard_v*.json"))
    assert len(runs) == 16
    for path in runs:
        verdict = json.loads(path.read_text())["verdict"]
        if path.name == "gate2_hazard_v16.json":
            # candidate 16: the first passing run (a model delta, not a rescue).
            assert verdict["gate_2_pass"] is True, path.name
            assert verdict["n_seeds_pass"] == 4, path.name
        else:
            # every pre-candidate-16 run stands FAIL (the amendment rescued
            # nothing; no verdict changed at the flip).
            assert verdict["gate_2_pass"] is False, path.name


def test_gate2_ratified_history_record():
    """gate_2.amendment_history[0] is complete, with all four ceremony pointers.

    amendment 1's amendment_proposed was consumed by its flip; the history
    entry records the full ceremony (adversarial review / fixes /
    verification / ratifying merge) and the prospective-only content. A later
    proposal (number >= 2) MAY reintroduce amendment_proposed for its own
    ceremony -- it must be a strictly later proposal, never a re-presentation
    of the ratified amendment 1.
    """
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    gate_2 = gates["gates"]["gate_2"]
    # Amendment 1's object was consumed by the flip. If an amendment_proposed
    # is present, it is a STRICTLY LATER proposal than every ratified one --
    # the floor derives from the history length (referee fix D2), so the
    # invariant self-tightens at every future ratification instead of
    # admitting a re-presented consumed object once history grows past the
    # old hard-coded 2.
    proposed = gate_2.get("amendment_proposed")
    history_floor = len(gate_2["amendment_history"]) + 1
    assert (
        proposed is None or proposed.get("proposal_number", 0) >= history_floor
    )
    entry = gate_2["amendment_history"][0]
    assert entry["id"] == "2026-07-08-mean-over-draws-estimator"
    for key in ("referee_round", "ratified", "flipped_live", "content"):
        assert entry[key], key
    assert entry["flipped_live"] == "this pull request"
    rr = entry["referee_round"]
    assert "4915412987" in rr["review"]  # adversarial AMEND round
    assert "5b70840" in rr["fixes"]  # fix commit
    assert "4916048161" in rr["fixes"]  # fixes-summary comment
    assert "4916419901" in rr["verification"]  # verification RATIFY AS-IS
    assert "PR 96" in entry["ratified"]
    assert "fec27eb51" in entry["ratified"]  # ratifying merge commit
    assert "PROSPECTIVE ONLY" in entry["content"]
    assert "1-9 stand FAIL" in entry["content"]


# --------------------------------------------------------------------------
# Gate-2 amendment 2 RATIFIED bindings (live thresholds + tranche structure)
#
# Amendment 2 (the explicit tranche split; proposed PR #111; referee AMEND
# comment 4930448912 -> fixes 81ea41e / comment 4930615774 -> verification
# RATIFY AS-IS comment 4930753295 -> ratified by merge 8a4a240; flipped live
# this PR). The proposal-object tests above (guarded on proposal_number == 2)
# go dormant once amendment_proposed is removed; these bind the SAME
# load-bearing guarantees at their LIVE post-flip locations: the re-scoped
# description / holdout_basis, the tranche_id, the promoted certification
# _scope map (with the two verification-round nits), the gate_2b / gate_2c
# unlocked siblings, the promoted standing governance rule, and the second
# history entry with all four ceremony pointers. ZERO THRESHOLD MOVEMENT: the
# 46-cell scored surface stays byte-identical (also bound in the always-hot
# locked section above). They touch only committed files.
# --------------------------------------------------------------------------
def _gate_2_block() -> dict:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    return gates["gates"]["gate_2"]


def _gate2_scope() -> dict:
    return _gate_2()["scope"]


def test_gate2_tranche2a_description_and_holdout_basis_rescoped():
    """flip_edits description / holdout_basis + tranche_id, applied live.

    Tranche 2a claims only mh85_23 + cah85_23 (+ deaths); household
    composition / MX23REL is named as the separate UNLOCKED tranche 2b, not a
    2a holdout; the "computes exactly" statutory-formula oracle clause is
    RETAINED verbatim (fix C1); holdout_basis drops MX23REL; and thresholds
    carries tranche_id 2a_marital_fertility.
    """
    desc = _gate_2_block()["description"]
    assert "tranche 2a_marital_fertility scores" in desc
    assert "mh85_23 and cah85_23" in desc
    assert "UNLOCKED tranche 2b" in desc  # MX23REL re-homed, not a 2a holdout
    # fix C1: the second clause is RETAINED verbatim.
    assert 'benefit formulas earn per-rule "computes exactly" status' in desc
    thr = _gate_2()
    assert thr["tranche_id"] == "2a_marital_fertility"
    assert thr["holdout_basis"] == ["mh85_23", "cah85_23"]
    assert "MX23REL" not in thr["holdout_basis"]


def test_gate2_scope_note_draft_label_dropped_and_xref_repointed():
    """flip_edits scope_note_draft_label / scope_note_holdout_xref, applied.

    The stale pre-lock "This DRAFT tranche" heading is relabeled to tranche
    2a_marital_fertility; the caregiver cross-reference no longer cites the
    (now MX23REL-free) 2a holdout_basis but the unlocked gate_2b tranche.
    """
    scope = _gate2_scope()
    note = scope["note"]
    assert "This DRAFT tranche" not in note
    assert note.strip().startswith("tranche 2a_marital_fertility covers")
    care = scope["provision_class_coverage"][
        "caregiver_and_child_in_care_survivor"
    ]
    assert "2b_relationship_household" in care
    assert "gate_2b.holdout_basis" in care
    assert "not scored in this draft" not in care  # stale xref repointed


def test_gate2_certification_scope_is_live_and_bound_exactly():
    """certification_scope promoted into the locked scope; map bound EXACTLY.

    provision_class_map's classes equal the locked provision_class_coverage
    keys; each row's requires_tranche list (order-sensitive) and
    locked_coverage token are pinned AND cross-checked against the locked
    note's designation, so a one-token flip in EITHER breaks (referee fix B /
    P1). The two verification-round nits are asserted: the 2b legend quote
    matches the derivation_basis quote (nit 1), and COLA is qualified as
    riding CA/M/DI rather than a pure gate-1 + oracle surface (nit 2).
    """
    scope = _gate2_scope()
    csc = scope["certification_scope"]
    locked_cov = scope["provision_class_coverage"]
    rows = {r["provision_class"]: r for r in csc["provision_class_map"]}
    assert set(rows) == set(locked_cov)
    expected = {
        "marital_and_survivor_timing": {
            "locked_coverage": "COVERED",
            "requires_tranche": ["2a_marital_fertility"],
        },
        "caregiver_and_child_in_care_survivor": {
            "locked_coverage": "NOT COVERED HERE",
            "requires_tranche": [
                "2a_marital_fertility",
                "2b_relationship_household",
            ],
        },
        "marriage_x_earnings_joint": {
            "locked_coverage": "NOT COVERED",
            "requires_tranche": ["2c_marriage_earnings_joint"],
        },
    }
    assert set(rows) == set(expected)
    for cls, exp in expected.items():
        r = rows[cls]
        assert r["requires_tranche"] == exp["requires_tranche"], cls
        assert r["locked_coverage"] == exp["locked_coverage"], cls
        note_cov = locked_cov[cls].split(" -- ")[0].split(" (")[0].strip()
        assert r["locked_coverage"] == note_cov, cls
    basis = csc["derivation_basis"]
    assert "provision_class_coverage" in basis["locked_scope_note"]
    assert "#74" in basis["provision_matrix"]
    supports = " ".join(csc["tranches"]["2a_marital_fertility"]["supports"])
    assert "caregiver credits" in supports
    assert "survivor" in supports and "spousal" in supports
    b = " ".join(csc["tranches"]["2b_relationship_household"]["required_for"])
    assert "household-unit poverty" in b
    assert "child-in-care survivor" in b
    c = " ".join(csc["tranches"]["2c_marriage_earnings_joint"]["required_for"])
    assert "earnings" in c and "marital" in c
    # NIT 1: the 2b legend quote spacing matches the derivation_basis quote.
    assert "poverty/household" in b
    assert "poverty / household" not in b
    assert "poverty/household" in basis["provision_matrix"]
    # NIT 2: COLA qualified (rides CA/M/DI; #78 covers CA, M/DI uncertified),
    # while the tranche-boundary claim (OUTSIDE 2a/2b/2c) is preserved.
    dns = " ".join(csc["tranches"]["2a_marital_fertility"]["does_not_support"])
    assert "CA, M, DI" in dns
    assert "M / DI are uncertified" in dns
    assert "OUTSIDE 2a / 2b / 2c" in dns


def test_gate2b_2c_sibling_tranches_live():
    """gate_2b / gate_2c live as sibling tranches (amendment-2 flip_additions).

    Flip-time update: BOTH siblings are now LOCKED (each by its own lock
    ceremony on 2026-07-10). 2b carries locked: true / status: locked with a
    thresholds block and a completed lock_ceremony; 2c likewise carries
    locked: true / status: locked with a thresholds block and a completed
    lock_ceremony (the gate-2c lock flip updates this 2c half exactly as the
    gate-2b lock flip updated the 2b half). 2b holds the MX23REL holdout the
    amendment-2 flip moved out of tranche 2a. (The full gate-2b / gate-2c lock
    bindings live in the locked sections below.)
    """
    g2 = _gate_2_block()
    b = g2["gate_2b"]
    assert b["id"] == "2b_relationship_household"
    assert b["status"] == "locked"
    assert b["locked"] is True
    assert b["holdout_basis"] == ["MX23REL"]
    assert b["lock_ceremony"]["exists"] is True
    assert "thresholds" in b
    c = g2["gate_2c"]
    assert c["id"] == "2c_marriage_earnings_joint"
    assert c["status"] == "locked"
    assert c["locked"] is True
    assert c["lock_ceremony"]["exists"] is True
    assert "thresholds" in c


def test_gate2_standing_governance_rule_promoted_live():
    """The standing rule promoted into locked governance.amendment_rules.

    description_claims_exactly_the_scored_surface: a gate / tranche
    description and holdout_basis must claim EXACTLY the scored surface at
    lock time; applies to 2b / 2c / gate 3, attributed to the amendment-2
    referee round (#106 finding 4 / PR #111), not presented as pre-existing.
    The inherited rules are untouched by the promotion.
    """
    amend = _gate_2()["governance"]["amendment_rules"]
    rule = amend["description_claims_exactly_the_scored_surface"]
    assert "EXACTLY" in rule["rule"]
    assert "holdout_basis" in rule["rule"]
    assert set(rule["applies_to"]) == {
        "2b_relationship_household",
        "2c_marriage_earnings_joint",
        "gate_3",
    }
    assert "#106" in rule["attributed_to"]
    assert "#111" in rule["attributed_to"]
    assert amend["inherits"] == "gate_1"
    assert "committed run verdict changes" in amend["no_self_rescue"]


def test_gate2_tranche_split_history_record():
    """gate_2.amendment_history[1] records amendment 2 with all four pointers.

    amendment_proposed is consumed by the flip; the second history entry
    records the full ceremony (adversarial review 4930448912 / fixes 81ea41e
    + comment 4930615774 / verification 4930753295 / ratifying merge 8a4a240)
    and the zero-movement, structural-only content citing review #106 finding
    4 and the candidate-16 pass (#109).
    """
    g2 = _gate_2_block()
    assert "amendment_proposed" not in g2  # object consumed by the flip
    entry = g2["amendment_history"][1]
    assert entry["id"] == "2026-07-09-tranche-split"
    for key in ("referee_round", "ratified", "flipped_live", "content"):
        assert entry[key], key
    assert entry["flipped_live"] == "this pull request"
    rr = entry["referee_round"]
    assert "4930448912" in rr["review"]  # adversarial AMEND round
    assert "81ea41e" in rr["fixes"]  # fix commit
    assert "4930615774" in rr["fixes"]  # fixes-summary comment
    assert "4930753295" in rr["verification"]  # verification RATIFY AS-IS
    assert "PR 111" in entry["ratified"]
    assert "8a4a240" in entry["ratified"]  # ratifying merge commit
    content = entry["content"]
    assert "ZERO THRESHOLD MOVEMENT" in content
    assert "#106" in content and "#109" in content
    assert "v1-v15 stand FAIL" in content
    assert "v16 stands PASS" in content


def test_gate2_tranche_split_zero_threshold_movement_vs_master():
    """The tranche-2a scored surface is byte-identical to origin/master.

    The strongest live form of "zero threshold movement": the 46 gated + 16
    report-only cell SETS, every view's tolerances/derivations, the protocol,
    the power cap, and the report_only list equal origin/master's -- only the
    naming, scope prose, certification map, sibling stubs, governance rule,
    and history changed. Skips only if the ref is unreachable.
    """
    master = _master_gate2()
    if master is None:
        pytest.skip("origin/master gates.yaml unreachable")
    cur = _gate_2()
    mt = master["thresholds"]
    for key in ("views", "power_cap", "protocol", "report_only", "statistic"):
        assert cur[key] == mt[key], key
    cur_gated, cur_ro = _gated_report_sets(cur)
    m_gated, m_ro = _gated_report_sets(mt)
    assert cur_gated == m_gated and len(cur_gated) == 46
    assert cur_ro == m_ro and len(cur_ro) == 16


def test_gate2_amendment2_proposal_object_consumed_and_dormant():
    """The amendment-2 proposal object is consumed; its tests are dormant-safe.

    Post-flip amendment_proposed is gone, so _gate2_amendment2() returns None
    (every proposal-object test skips) and the merge-safe D1 guard
    (test_gate2_amendment2_changes_no_locked_value) no longer runs its
    thresholds-equality assertion against the now-restructured block -- the
    "naturally passes post-flip" state the referee's fix D1 anticipated.
    """
    assert _gate2_amendment2() is None
    assert "amendment_proposed" not in _gate_2_block()


# --------------------------------------------------------------------------
# Gate 2b LOCKED threshold binding (gate_2.gate_2b.thresholds, status locked)
#
# The gate-2b lock flip (2026-07-10) turns the amendment-2 unlocked stub into
# a LOCKED sibling tranche: it inserts a thresholds block whose 46 per-cell
# |ln ratio| tolerances are machine-bound to the RATIFIED, FROZEN 100-seed
# half-split floor runs/gate2b_floors_v1.json exactly as the locked gate-2a
# and gate-1 thresholds bind to theirs -- tolerance == round(floor mean + 4 *
# floor sd, 3), capped at T_max = ln(1.5), partitioned by the floor's own
# events + power-cap + aggregate-supersession rule. These are LOCKED-HOT (the
# 2a lesson: bindings never go dormant post-flip); they run everywhere
# (committed files only). They do NOT touch the locked tranche-2a section
# above, and a D1-style SUBSET master-compare proves the flip leaves
# gate_2.thresholds byte-identical to origin/master (no red-master window).
# --------------------------------------------------------------------------
GATE2B_FLOOR_RUN = "runs/gate2b_floors_v1.json"
GATE2B_ANCHOR_RUN = "runs/gate2b_anchor_v1.json"
GATE2B_FLOOR_KEY = "noise_floor_seeds_0_99"


def _gate_2b_block() -> dict:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    return gates["gates"]["gate_2"]["gate_2b"]


def _gate_2b() -> dict:
    """gate_2b.thresholds. Retained-name helper; post-lock the bindings run
    unconditionally (the amendment-2 locked-hot lesson)."""
    return _gate_2b_block()["thresholds"]


def _gate2b_floor() -> dict:
    return json.loads((ROOT / GATE2B_FLOOR_RUN).read_text())


def _gate2b_derive(cell: str, k: float, rounding: int) -> float:
    stats = _gate2b_floor()[GATE2B_FLOOR_KEY][cell]
    return round(stats["mean"] + k * stats["sd"], rounding)


def _gate2b_gated_set() -> set:
    gated = set()
    for view in _gate_2b()["views"].values():
        gated |= set(view["tolerances"])
    return gated


def test_gate2b_locked_with_ceremony_record():
    """Gate 2b is locked, with the full lock ceremony recorded in-contract.

    ceremony_record carries the three ceremony comment ids, the ratifying
    merge of PR 118 (commit 2b2f3cb), the standing delegated-authority note,
    and the no_self_rescue clause."""
    b = _gate_2b_block()
    assert b["locked"] is True
    assert b["status"] == "locked"
    g2b = _gate_2b()
    assert g2b["locked"] is True
    assert g2b["status"] == "locked"
    assert g2b["tranche_id"] == "2b_relationship_household"
    record = json.dumps(g2b["ceremony_record"])
    for token in (
        "4931849367",  # round-1 adversarial referee AMEND BEFORE LOCK
        "4932310897",  # fixes A-H
        "4932491912",  # verification LOCK AS-IS
        "PR 118",  # ratifying PR
        "2b2f3cb",  # ratifying merge commit
        "no_self_rescue",
    ):
        assert token in record, token
    assert "delegated" in record.lower()


def test_gate2b_floor_run_is_the_ratified_frozen_anchor():
    """The floor the locked thresholds cite reads no gate and is frozen."""
    g2b = _gate_2b()
    assert g2b["floor_run"] == GATE2B_FLOOR_RUN
    floor = _gate2b_floor()
    assert floor["reported_anchor_not_gated"] is True
    assert floor["schema_version"] == "gate2b_floors.v1"
    assert floor["holdout_basis"] == ["MX23REL"]


def test_gate2b_locked_thresholds_bind_to_floor():
    """Every locked tolerance == round(100-seed floor mean + k*sd, rounding).

    The exact machine-binding the locked gate-2a views carry, applied to each
    gate-2b view's tolerances against the committed 100-seed half-split floor.
    Every tolerances entry has a matching derivations.rules entry keyed on the
    floor cell itself."""
    g2b = _gate_2b()
    for view_name, view in g2b["views"].items():
        rules = view["derivations"]["rules"]
        tolerances = view["tolerances"]
        assert set(rules) == set(tolerances), view_name
        assert view["derivations"]["floor_run"] == GATE2B_FLOOR_RUN
        assert view["floor_run"] == GATE2B_FLOOR_RUN
        for cell, rule in rules.items():
            assert rule["key"] == cell, f"{view_name}.{cell}"
            derived = _gate2b_derive(cell, rule["k"], rule.get("rounding", 3))
            assert derived == pytest.approx(tolerances[cell]), (
                f"{view_name}.{cell}: derived {derived} != tolerance "
                f"{tolerances[cell]}"
            )


def test_gate2b_locked_k_is_4_and_holdout_is_mx23rel():
    """Every locked k is the ~4-sigma gate-1 / 2a precedent; holdout MX23REL."""
    g2b = _gate_2b()
    assert g2b["holdout_basis"] == ["MX23REL"]
    assert g2b["floor_run"] == GATE2B_FLOOR_RUN
    for view in g2b["views"].values():
        for rule in view["derivations"]["rules"].values():
            assert rule["k"] == 4


def test_gate2b_power_cap_binds_every_gated_cell():
    """Every gated tolerance <= T_max = ln(1.5); the floor partitioned exactly
    on that cap (+ >=20 events + supersession)."""
    g2b = _gate_2b()
    assert g2b["power_cap"]["t_max"] == "ln(1.5)"
    floor = _gate2b_floor()
    t_max = floor["internal_noise_floor"]["t_max"]
    assert t_max == pytest.approx(math.log(1.5))
    for view in g2b["views"].values():
        for cell, tol in view["tolerances"].items():
            assert tol <= t_max, f"{cell} tolerance {tol} exceeds T_max"


def test_gate2b_partition_matches_committed_floor_46_47():
    """gated / report_only == the floor's derived partition (events + power
    cap + aggregate supersession), not hand-picked; counts 46 / 47; disjoint;
    a real cover of every reference moment."""
    g2b = _gate_2b()
    floor = _gate2b_floor()
    partition = floor["gate_partition"]
    gated = _gate2b_gated_set()
    report_only = set(g2b["report_only"])
    assert gated == set(partition["gate_eligible"])
    assert report_only == set(partition["report_only"])
    assert len(gated) == 46
    assert len(report_only) == 47
    assert gated.isdisjoint(report_only)
    assert gated | report_only == set(floor["reference_moments"])
    for cell in gated:
        assert cell in floor[GATE2B_FLOOR_KEY], cell


def test_gate2b_aggregations_are_pre_registered_and_consistent():
    """The six coverage-recovery aggregates match the floor, and a gating
    aggregate demotes every per-age member it spans (no self-rescue by
    pooling). Only coresident_grandchild.55+|female gates (fix H: 5 of 6
    aggregates fail the cap)."""
    g2b = _gate_2b()
    floor = _gate2b_floor()
    yaml_aggs = g2b["power_cap"]["aggregations"]
    art_aggs = floor["aggregations"]
    assert set(yaml_aggs) == set(art_aggs)
    report_only = set(g2b["report_only"])
    gated = _gate2b_gated_set()
    n_gating = 0
    for agg, spec in yaml_aggs.items():
        assert spec["gated"] == art_aggs[agg]["gated"], agg
        if spec["gated"]:
            n_gating += 1
            assert agg in gated, agg
            for member in art_aggs[agg]["members"]:
                assert member in report_only, (agg, member)
        else:
            assert agg not in gated, agg
    assert n_gating == 1
    assert "coresident_grandchild.55+|female" in gated


def test_gate2b_multigen_5564_standalone_not_superseded():
    """Fix G lives in the lock: the multigen aggregate pools 65+ only, so
    multigen.55-64|{f,m} are judged standalone and are report-only via the
    cap, never superseded_by a gating pool."""
    g2b = _gate_2b()
    floor = _gate2b_floor()
    report_only = set(g2b["report_only"])
    aggs = g2b["power_cap"]["aggregations"]
    members = {
        m
        for spec in aggs.values()
        for m in _split_members(spec["members_demoted_to_report_only"])
    }
    for sex in ("female", "male"):
        cell = f"multigen.55-64|{sex}"
        assert cell in report_only, cell
        assert cell not in members, cell
        reason = floor["cell_stability"][cell]["report_reason"]
        assert not reason.startswith("superseded_by:"), reason


def _split_members(text: str) -> set:
    return {m.strip() for m in text.replace("\n", " ").split(",") if m.strip()}


def test_gate2b_protocol_is_the_ratified_k20_2a_estimator():
    """The scoring protocol is tranche 2a's ratified mean-over-K=20 estimator
    (amendment 1), not a single frozen draw; the estimator conventions
    (default_rng(5200 + k), K=20, scored once not mean-of-|ln|) match the
    locked gate_2 (2a) protocol text; the OC matches the floor."""
    g2b = _gate_2b()
    proto = g2b["protocol"]
    assert str(proto["option"]).strip().startswith("a")
    assert proto["gate_seeds"] == [0, 1, 2, 3, 4]
    assert proto["candidate_draws"] == 20
    assert "5200" in proto["candidate_draw_stream"]
    assert "K=20" in proto["estimator"]
    assert "NOT the mean of the per-draw" in proto["estimator"]
    basis = proto["faithful_candidate_oc"]["basis_note"]
    assert "DRAW-NOISE-FREE" in basis
    assert "UNACHIEVABLE" in basis
    # estimator-convention equality with the locked 2a protocol.
    g2a = _gate_2()
    a_candidate = g2a["protocol"]["candidate"]
    assert "5200 + k" in a_candidate
    assert "5200 + k" in proto["candidate_draw_stream"]
    assert "K=20" in g2a["statistic"] or "K=20" in a_candidate
    # fresh-run schema: per-draw rates [20, 46, 5], run-invalidation, report.
    schema = proto["fresh_run_artifact_schema"]
    assert schema["per_draw_per_cell_rates"]["shape"] == [20, 46, 5]
    assert schema["undefined_draw_rule"]["pre_specified"] is True
    assert schema["per_draw_dispersion_disclosure"]["report_only"] is True
    # The OC recorded in the contract matches the artifact's recomputation.
    oc = proto["faithful_candidate_oc"]
    art_oc = _gate2b_floor()["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == pytest.approx(art_oc["p_seed_pass"])
    assert oc["p_gate_pass_4_of_5"] == pytest.approx(
        art_oc["p_gate_pass_4_of_5"]
    )
    assert oc["n_gated_cells"] == art_oc["n_gated_cells"] == 46


def test_gate2b_oc_recomputes_from_tolerances_and_sigmas():
    """The faithful-candidate OC (0.9397 / 0.9678) recomputes from the locked
    tolerances and the floor sigmas on the draw-noise-free half-normal basis,
    independent of the stored value."""
    g2b = _gate_2b()
    floor = _gate2b_floor()[GATE2B_FLOOR_KEY]
    tolerances = {}
    for view in g2b["views"].values():
        tolerances.update(view["tolerances"])
    assert len(tolerances) == 46
    p_seed = 1.0
    for cell, tol in tolerances.items():
        sigma = floor[cell]["realized_sigma"]
        p_seed *= 2.0 * _normal_cdf(tol / sigma) - 1.0
    p_gate = p_seed**5 + 5 * p_seed**4 * (1.0 - p_seed)
    assert round(p_seed, 4) == 0.9397
    assert round(p_gate, 4) == 0.9678
    oc = g2b["protocol"]["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == round(p_seed, 4)
    assert oc["p_gate_pass_4_of_5"] == round(p_gate, 4)


def test_gate2b_governance_weight_definition_mirrors_2a():
    """flip-note 1: the lock carries a weight_definition block mirroring 2a's
    (person-constant most-recent positive PSID weight; no unweighted gated
    statistic), plus the inherited no_self_rescue and the promoted standing
    description-claims-exactly rule."""
    gov = _gate_2b()["governance"]
    weight = gov["weight_definition"]
    assert "most-recent positive" in weight
    assert "no unweighted gated statistic" in weight.lower()
    amend = gov["amendment_rules"]
    assert amend["inherits"] == "gate_1"
    assert "committed run verdict changes" in amend["no_self_rescue"]
    assert "runs registered after its ratification" in amend["no_self_rescue"]
    assert "EXACTLY" in amend["description_claims_exactly_the_scored_surface"]
    assert "issue #42" in gov["registration"]
    assert "sha256" in gov["holdout_id_commitment"]


def test_gate2b_estimand_named_effectively_1997_2023():
    """finding D: the pooled estimand is named effectively-1997-2023 (per the
    standing description-claims-exactly rule), explicitly NOT a 1969-2023
    average, and it matches the floor's data.estimand share."""
    g2b = _gate_2b()
    estimand = g2b["estimand"]
    assert "1997-2023" in estimand
    assert "99.81%" in estimand
    assert "NOT a 1969-2023 average" in estimand
    floor = _gate2b_floor()
    assert floor["data"]["post_1997_weight_share_pct"] > 99.0
    assert "1997-2023" in floor["data"]["estimand"]


def test_gate2b_external_anchor_is_bundled_before_the_flip():
    """flip-note 2 / round-1 finding F: the concept-decomposed Census/CPS
    shape/ratio anchor is bundled in this flip; the pointer resolves to a
    committed reported-not-gated artifact built from the frozen floor and the
    sha-pinned Census files, and it moves no floor value (no calibration)."""
    g2b = _gate_2b()
    assert g2b["external_anchor"] == GATE2B_ANCHOR_RUN
    report = g2b["external_anchor_report"]
    assert report["run"] == GATE2B_ANCHOR_RUN
    assert report["reported_anchor_not_gated"] is True
    assert "family unit" in report["concept_delta"].lower()
    assert "B11017" in report["multigen_bridge"]
    anchor = json.loads((ROOT / GATE2B_ANCHOR_RUN).read_text())
    assert anchor["schema_version"] == "gate2b_anchor.v1"
    assert anchor["gated"] is False
    assert anchor["reported_anchor_not_gated"] is True
    # the anchor reads the SAME frozen floor the lock cites.
    assert anchor["floor_source"] == GATE2B_FLOOR_RUN
    floor_sha = hashlib.sha256(
        (ROOT / GATE2B_FLOOR_RUN).read_bytes()
    ).hexdigest()
    assert anchor["floor_sha256"] == floor_sha
    # the census sources the report names are the ones the anchor consumed.
    anchor_files = {s["file"] for s in anchor["census_sources"]}
    assert set(report["census_sources"]) == anchor_files
    for rel in anchor_files:
        assert (ROOT / rel).exists(), rel


def test_gate2b_anchor_ratios_recompute_and_are_honest():
    """The anchor's PSID/Census ratios recompute from the frozen floor's
    reference_moments and the committed Census values; the coresident_spouse
    residuals collapse near 1 after the partner-inclusion concept factor (the
    2a named-delta pattern); nothing is calibrated."""
    anchor = json.loads((ROOT / GATE2B_ANCHOR_RUN).read_text())
    ref = _gate2b_floor()["reference_moments"]
    living = json.loads(
        (
            ROOT / "data/external/census_living_arrangements_2023.json"
        ).read_text()
    )
    band_map = {
        "15-24": "18-24",
        "25-34": "25-34",
        "35-44": "35-64",
        "45-54": "35-64",
        "55-64": "35-64",
        "65-74": "65-74",
        "75+": "75+",
    }
    resid = []
    for c in anchor["families"]["coresident_spouse"]["cells"]:
        cell = c["cell"]
        band = cell.split(".", 1)[1].split("|")[0]
        sex = cell.split("|")[1]
        cps = living["bands"][band_map[band]][sex]
        matched = (
            cps["living_with_spouse"] + cps["living_with_partner"]
        ) / 100
        # census anchor matches the committed Census table.
        assert c["census_spouse_plus_partner"] == pytest.approx(
            round(matched, 4)
        )
        # raw ratio recomputes from the FROZEN floor reference moment.
        psid = ref[cell]["rate"]
        assert c["residual_vs_spouse_plus_partner"] == pytest.approx(
            round(psid / matched, 4)
        )
        resid.append(c["residual_vs_spouse_plus_partner"])
    # the clean-band residuals (25-34, 65-74, 75+ excl. the widowhood tail)
    # land near 1 -- the anchor validates, it does not calibrate.
    assert all(0.7 < r < 1.2 for r in resid), resid
    assert anchor["summary"]["calibration"].startswith("none")


def test_gate2b_multigen_concept_records_b11017_bridge_notes():
    """flip-note 3: the lock records the in-law generation-count inclusion and
    the great-grand +/-2 lumping the B11017 bridge names."""
    mc = _gate_2b()["multigen_concept"]
    assert "B11017" in mc["rule"]
    assert "first_year_cohabitor" in mc["rule"]
    assert "88" in mc["rule"]
    inlaw = mc["in_law_generation_note"]
    assert "37 child-in-law" in inlaw and "57 parent-in-law" in inlaw
    great = mc["great_grand_note"]
    assert "811 person-waves" in great


def test_gate2b_certification_scope_consistent_with_locked_2a_map():
    """The 2b certification_scope certifies the household-composition stocks +
    the six gated transitions, and is consistent with the locked tranche-2a
    map's 2b_relationship_household.required_for; marriage x earnings stays
    2c, own-record levels stay gate1 + oracle."""
    csc = _gate_2b()["certification_scope"]
    assert csc["tranche"] == "2b_relationship_household"
    certifies = csc["certifies"]
    assert "STOCK" in certifies and "TRANSITION" in certifies
    assert "46 gated cells" in certifies
    supports = " ".join(csc["supports"])
    assert "household-UNIT poverty" in supports
    assert "child-in-care survivor" in supports
    dns = " ".join(csc["does_not_support"])
    assert "2c" in dns and "OUTSIDE" in dns
    # consistent with the locked 2a map's 2b required_for.
    locked_map = _gate_2()["scope"]["certification_scope"]["tranches"]
    b_required = " ".join(
        locked_map["2b_relationship_household"]["required_for"]
    )
    assert "household-unit poverty" in b_required
    assert "child-in-care survivor" in b_required


def test_gate2b_history_entry_records_the_lock():
    """gate_2b.history carries the 2026-07-10-gate2b-lock entry with the three
    ceremony comment ids, the ratifying merge (#118 / 2b2f3cb), and
    no_self_rescue."""
    hist = _gate_2b_block()["history"]
    entry = next(e for e in hist if e["id"] == "2026-07-10-gate2b-lock")
    assert entry["flipped_live"] == "this pull request"
    rr = entry["referee_round"]
    assert "4931849367" in rr["review"]
    assert "4932310897" in rr["fixes"]
    assert "4932491912" in rr["verification"]
    assert "2b2f3cb" in entry["ratified"]
    assert "PR 118" in entry["ratified"]
    assert "no_self_rescue" in entry["ratified"]
    assert "ZERO threshold movement" in entry["content"]


def test_gate2b_flip_notes_all_five_implemented():
    """The five verification-round flip-time notes are enumerated as
    implemented in the ceremony_record."""
    notes = _gate_2b()["ceremony_record"]["flip_notes_implemented"]
    assert set(notes) == {
        "note_1_weight_definition",
        "note_2_external_anchor_bundled",
        "note_3_b11017_bridge",
        "note_4_era_slices_transitions",
        "note_5_covers_stocks_and_transitions",
    }
    for key, text in notes.items():
        assert text.strip(), key


def test_gate2b_covers_names_stocks_and_transitions():
    """flip-note 5: the covers text names STOCKS and TRANSITIONS, not the
    amendment-2 stub's 'transitions' alone."""
    covers = _gate_2b_block()["covers"]
    assert "STOCKS" in covers
    assert "TRANSITIONS" in covers
    assert "tranche 2c" in covers


def test_gate2b_flip_leaves_locked_tranche_2a_byte_identical():
    """D1 SUBSET master-compare (the form that held at #112, no red-master
    window): the flip changes only gate_2b, so gate_2.thresholds (tranche 2a)
    stays byte-identical to origin/master and gate_2 gains no top-level key.
    The 2a-thresholds-equality and key-subset asserts hold in EVERY state
    (before and after the flip merges), so they are unconditional."""
    master = _master_gate2()
    if master is None:
        pytest.skip("origin/master gates.yaml unreachable")
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    cur_g2 = gates["gates"]["gate_2"]
    # locked tranche-2a thresholds unchanged (holds in every state).
    assert cur_g2["thresholds"] == master["thresholds"]
    assert cur_g2["thresholds"]["locked"] is True
    # the 2a scored surface is still 46 gated + 16 report-only.
    a_gated, a_report = _gated_report_sets(cur_g2["thresholds"])
    assert len(a_gated) == 46
    assert len(a_report) == 16
    # subset: the flip adds no gate_2 top-level key (gate_2b/gate_2c/
    # amendment_history all pre-exist); a bogus added/removed key fails loudly.
    assert set(cur_g2) - set(master) == set()
    assert set(master) - set(cur_g2) == set()


# --------------------------------------------------------------------------
# Gate 2c LOCKED threshold binding (gate_2.gate_2c.thresholds, status locked)
#
# The gate-2c lock flip (2026-07-10) turns the amendment-2 unlocked stub into
# a LOCKED sibling tranche: it inserts a thresholds block whose 27 per-cell
# |ln ratio| tolerances are machine-bound to the RATIFIED, FROZEN 100-seed
# COUPLE-DISJOINT half-split floor runs/gate2c_floors_v1.json exactly as the
# locked gate-2a / gate-2b / gate-1 thresholds bind to theirs -- tolerance ==
# round(floor mean + 4 * floor sd, 3), capped at T_max = ln(1.5), partitioned
# by the floor's own events + power-cap rule (27 gate / 22 report-only; no
# coverage-recovery aggregates). These are LOCKED-HOT (the 2a lesson: bindings
# never go dormant post-flip); they run everywhere (committed files only).
# They do NOT touch the locked tranche-2a / gate-2b sections above, and a
# D1-style SUBSET master-compare proves the flip leaves gate_2.thresholds AND
# gate_2b byte-identical to origin/master (no red-master window).
# --------------------------------------------------------------------------
GATE2C_FLOOR_RUN = "runs/gate2c_floors_v1.json"
GATE2C_ANCHOR_RUN = "runs/gate2c_anchor_v1.json"
GATE2C_FLOOR_KEY = "noise_floor_seeds_0_99"


def _gate_2c_block() -> dict:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    return gates["gates"]["gate_2"]["gate_2c"]


def _gate_2c() -> dict:
    """gate_2c.thresholds. Retained-name helper; post-lock the bindings run
    unconditionally (the amendment-2 locked-hot lesson)."""
    return _gate_2c_block()["thresholds"]


def _gate2c_floor() -> dict:
    return json.loads((ROOT / GATE2C_FLOOR_RUN).read_text())


def _gate2c_derive(cell: str, k: float, rounding: int) -> float:
    stats = _gate2c_floor()[GATE2C_FLOOR_KEY][cell]
    return round(stats["mean"] + k * stats["sd"], rounding)


def _gate2c_gated_set() -> set:
    gated = set()
    for view in _gate_2c()["views"].values():
        gated |= set(view["tolerances"])
    return gated


def test_gate2c_locked_with_ceremony_record():
    """Gate 2c is locked, with the full lock ceremony recorded in-contract.

    ceremony_record carries the three ceremony comment ids, the re-homing
    chain (#124 -> #128 -> #129), the ratifying squash merge 3053795, the
    delegated-authority note, and no_self_rescue."""
    b = _gate_2c_block()
    assert b["locked"] is True
    assert b["status"] == "locked"
    g2c = _gate_2c()
    assert g2c["locked"] is True
    assert g2c["status"] == "locked"
    assert g2c["tranche_id"] == "2c_marriage_earnings_joint"
    record = json.dumps(g2c["ceremony_record"])
    for token in (
        "4935540075",  # round-1 adversarial referee AMEND BEFORE LOCK
        "4937213555",  # fixes A-H
        "4937857811",  # verification LOCK AS-IS
        "PR 129",  # ratifying PR (re-homed head)
        "3053795",  # ratifying squash merge commit
        "#124",  # re-homing chain
        "#128",
        "no_self_rescue",
    ):
        assert token in record, token
    assert "delegated" in record.lower()
    assert "re-homed" in record.lower()


def test_gate2c_floor_run_is_the_ratified_frozen_anchor():
    """The floor the locked thresholds cite reads no gate and is frozen."""
    g2c = _gate_2c()
    assert g2c["floor_run"] == GATE2C_FLOOR_RUN
    floor = _gate2c_floor()
    assert floor["reported_anchor_not_gated"] is True
    assert floor["schema_version"] == "gate2c_floors.v1"
    assert floor["holdout_basis"] == [
        "mh85_23",
        "family_earnings_panel_gate1_certified",
    ]


def test_gate2c_locked_thresholds_bind_to_floor():
    """Every locked tolerance == round(100-seed floor mean + k*sd, rounding).

    The exact machine-binding the locked gate-2a / gate-2b views carry,
    applied to each gate-2c view's tolerances against the committed 100-seed
    couple-disjoint floor. Every tolerances entry has a matching
    derivations.rules entry keyed on the floor cell itself."""
    g2c = _gate_2c()
    for view_name, view in g2c["views"].items():
        rules = view["derivations"]["rules"]
        tolerances = view["tolerances"]
        assert set(rules) == set(tolerances), view_name
        assert view["derivations"]["floor_run"] == GATE2C_FLOOR_RUN
        assert view["floor_run"] == GATE2C_FLOOR_RUN
        for cell, rule in rules.items():
            assert rule["key"] == cell, f"{view_name}.{cell}"
            derived = _gate2c_derive(cell, rule["k"], rule.get("rounding", 3))
            assert derived == pytest.approx(tolerances[cell]), (
                f"{view_name}.{cell}: derived {derived} != tolerance "
                f"{tolerances[cell]}"
            )


def test_gate2c_locked_k_is_4_and_holdout_is_mh85_x_earnings():
    """Every locked k is the ~4-sigma gate-1 / 2a precedent; the holdout is
    mh85_23 crossed with the gate-1-certified earnings panel."""
    g2c = _gate_2c()
    assert g2c["holdout_basis"] == [
        "mh85_23",
        "family_earnings_panel_gate1_certified",
    ]
    assert g2c["floor_run"] == GATE2C_FLOOR_RUN
    for view in g2c["views"].values():
        for rule in view["derivations"]["rules"].values():
            assert rule["k"] == 4


def test_gate2c_power_cap_binds_every_gated_cell():
    """Every gated tolerance <= T_max = ln(1.5); the floor partitioned exactly
    on that cap (+ >=20 events); gate-2c declares NO aggregates."""
    g2c = _gate_2c()
    assert g2c["power_cap"]["t_max"] == "ln(1.5)"
    assert g2c["power_cap"]["aggregations"] == {}
    floor = _gate2c_floor()
    t_max = floor["internal_noise_floor"]["t_max"]
    assert t_max == pytest.approx(math.log(1.5))
    for view in g2c["views"].values():
        for cell, tol in view["tolerances"].items():
            assert tol <= t_max, f"{cell} tolerance {tol} exceeds T_max"


def test_gate2c_partition_matches_committed_floor_27_22():
    """gated / report_only == the floor's derived partition (events + power
    cap; no aggregates), not hand-picked; counts 27 / 22; disjoint; a real
    cover of every reference moment; and the report-only machine reasons are
    exactly 16 tolerance_above_t_max + 6 below_20_events."""
    g2c = _gate_2c()
    floor = _gate2c_floor()
    partition = floor["gate_partition"]
    gated = _gate2c_gated_set()
    report_only = set(g2c["report_only"])
    assert gated == set(partition["gate_eligible"])
    assert report_only == set(partition["report_only"])
    assert len(gated) == 27
    assert len(report_only) == 22
    assert gated.isdisjoint(report_only)
    assert gated | report_only == set(floor["reference_moments"])
    for cell in gated:
        assert cell in floor[GATE2C_FLOOR_KEY], cell
    # machine reasons for the demotions (16 cap + 6 events), from the floor.
    reasons = {}
    for cell in report_only:
        reasons.setdefault(floor["cell_stability"][cell]["report_reason"], 0)
        reasons[floor["cell_stability"][cell]["report_reason"]] += 1
    assert reasons == {"tolerance_above_t_max": 16, "below_20_events": 6}


def test_gate2c_no_aggregations_reason_is_power_not_masking():
    """gate-2c declares no coverage-recovery aggregates; the recorded reason
    the sparse cells are report-only is POWER (fix H(i)), matching the floor's
    pooled_age_power (no pooled t{o}.35+|sex aggregate is standalone-gateable
    either)."""
    g2c = _gate_2c()
    assert g2c["power_cap"]["aggregations"] == {}
    demoted = g2c["power_cap"]["demoted_and_report_only"]
    assert "POWER, not masking" in demoted
    assert "16 tolerance_above_t_max" in demoted or "16" in demoted
    floor = _gate2c_floor()
    assert floor["pooled_age_power"]["any_standalone_gateable"] is False


def test_gate2c_protocol_is_the_ratified_k20_2a_estimator():
    """The scoring protocol is tranche 2a's ratified mean-over-K=20 estimator
    (amendment 1), adopted from the START; the conventions (default_rng(5200 +
    k), K=20, scored once not mean-of-|ln|) match the locked gate_2 (2a)
    protocol; the fresh-run schema is [20, 27, 5]; the OC matches the floor."""
    g2c = _gate_2c()
    proto = g2c["protocol"]
    assert str(proto["option"]).strip().startswith("a")
    assert proto["gate_seeds"] == [0, 1, 2, 3, 4]
    assert proto["candidate_draws"] == 20
    assert "5200" in proto["candidate_draw_stream"]
    assert "K=20" in proto["estimator"]
    assert "NOT the mean of the per-draw" in proto["estimator"]
    basis = proto["faithful_candidate_oc"]["basis_note"]
    assert "DRAW-NOISE-FREE" in basis
    assert "UNACHIEVABLE" in basis
    # estimator-convention equality with the locked 2a protocol.
    g2a = _gate_2()
    a_candidate = g2a["protocol"]["candidate"]
    assert "5200 + k" in a_candidate
    assert "5200 + k" in proto["candidate_draw_stream"]
    assert "K=20" in g2a["statistic"] or "K=20" in a_candidate
    # fresh-run schema: per-draw rates [20, 27, 5], invalidation, report.
    schema = proto["fresh_run_artifact_schema"]
    assert schema["per_draw_per_cell_rates"]["shape"] == [20, 27, 5]
    assert schema["undefined_draw_rule"]["pre_specified"] is True
    assert schema["per_draw_dispersion_disclosure"]["report_only"] is True
    # The OC recorded in the contract matches the artifact's recomputation.
    oc = proto["faithful_candidate_oc"]
    art_oc = _gate2c_floor()["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == pytest.approx(art_oc["p_seed_pass"])
    assert oc["p_gate_pass_4_of_5"] == pytest.approx(
        art_oc["p_gate_pass_4_of_5"]
    )
    assert oc["n_gated_cells"] == art_oc["n_gated_cells"] == 27


def test_gate2c_oc_recomputes_from_tolerances_and_sigmas():
    """The faithful-candidate OC (0.9641 / 0.988) recomputes from the locked
    tolerances and the floor sigmas on the draw-noise-free half-normal basis,
    independent of the stored value."""
    g2c = _gate_2c()
    floor = _gate2c_floor()[GATE2C_FLOOR_KEY]
    tolerances = {}
    for view in g2c["views"].values():
        tolerances.update(view["tolerances"])
    assert len(tolerances) == 27
    p_seed = 1.0
    for cell, tol in tolerances.items():
        sigma = floor[cell]["realized_sigma"]
        p_seed *= 2.0 * _normal_cdf(tol / sigma) - 1.0
    p_gate = p_seed**5 + 5 * p_seed**4 * (1.0 - p_seed)
    assert round(p_seed, 4) == 0.9641
    assert round(p_gate, 4) == 0.988
    oc = g2c["protocol"]["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == round(p_seed, 4)
    assert oc["p_gate_pass_4_of_5"] == round(p_gate, 4)


def test_gate2c_candidate_construction_is_pinned():
    """fix D + flip-notes 3/4: the candidate-side couple universe and
    orientation are pinned -- directed both-orientation emission (single
    orientation NON-CONFORMANT), the committed-cut provenance (not recomputed
    on simulated output), and the CI-invisible A5b residual recorded."""
    cc = _gate_2c()["protocol"]["candidate_construction"]
    emission = cc["couple_emission"]
    assert "DIRECTED" in emission
    assert "BOTH directions" in emission
    assert "NON-CONFORMANT" in emission
    assert "4.9x" in emission
    # flip-note 4: committed cut provenance, not recomputed on sim output.
    cut = cc["cut_provenance"]
    assert "COMMITTED" in cut
    assert "NOT values recomputed on simulated output" in cut
    # flip-note 3: the A5b residual shape is documented with the PSID catch.
    a5b = cc["ci_invisible_a5b_residual"]
    assert "marriage.all" in a5b and "divorce.all" in a5b
    assert "0.3%" in a5b
    assert "1.0572" in a5b and "1.0542" in a5b
    assert "seed-0 reproduction pin" in a5b or "seed-0 repro" in a5b
    # the per-year axis + detrend pins are present.
    assert "per-year" in cc["earnings_axis"]
    assert "placebo deflator" in cc["event_window_support_and_detrend"]


def test_gate2c_governance_weight_definition_mirrors_2a():
    """The lock carries a weight_definition mirroring 2a/2b's (person-constant
    most-recent positive PSID weight; no unweighted gated statistic; every
    gated family incl. the event windows), plus inherited no_self_rescue and
    the promoted standing description-claims-exactly rule."""
    gov = _gate_2c()["governance"]
    weight = gov["weight_definition"]
    assert "most-recent positive" in weight
    assert "no unweighted gated statistic" in weight.lower()
    assert "event-window" in weight
    amend = gov["amendment_rules"]
    assert amend["inherits"] == "gate_1"
    assert "committed run verdict changes" in amend["no_self_rescue"]
    assert "runs registered after its ratification" in amend["no_self_rescue"]
    assert "EXACTLY" in amend["description_claims_exactly_the_scored_surface"]
    assert "issue #42" in gov["registration"]
    assert "sha256" in gov["holdout_id_commitment"]
    assert "component_id" in gov["holdout_id_commitment"]


def test_gate2c_estimand_named_selected_1968_2022_with_era_facts():
    """flip-note 5: the estimand is named as the SELECTED couple universe on
    the true 1968-2022 panel (per description-claims-exactly), and the
    enumerated window facts ride as NUMBERS, incl. the 41.8% pre-1993 overlap
    quantified (not the artifact's qualitative 'a substantial share')."""
    g2c = _gate_2c()
    estimand = g2c["estimand"]
    assert "SELECTED universe" in estimand
    assert "1968-2022" in estimand
    assert "NOT all PSID marriages" in estimand
    era = g2c["era_facts"]
    assert era["earnings_income_year_range"] == [1968, 2022]
    assert era["supported_marriage_windows_overlapping_pre_1993_pct"] == 41.8
    assert era["supply_persons_with_pre_1993_positive_year_pct"] == 69.0
    assert era["observed_positive_years_max"] == 42
    # the number is present where the floor carried only the qualitative text.
    floor = _gate2c_floor()
    conv = floor["panel_construction"]["event_window_convention"]
    assert "substantial share" in conv  # the floor's qualitative version
    assert "41.8" not in conv  # the number was NOT in the floor text


def test_gate2c_external_anchor_is_bundled_before_the_flip():
    """flip-note 7: the concept-bridged published assortative-mating anchor is
    bundled in this flip; the pointer resolves to a committed
    reported-not-gated artifact built from the frozen floor and the cited
    published benchmark files, and it moves no floor value (no calibration)."""
    g2c = _gate_2c()
    assert g2c["external_anchor"] == GATE2C_ANCHOR_RUN
    report = g2c["external_anchor_report"]
    assert report["run"] == GATE2C_ANCHOR_RUN
    assert report["reported_anchor_not_gated"] is True
    assert report["status"] == "bundled_before_flip"
    anchor = json.loads((ROOT / GATE2C_ANCHOR_RUN).read_text())
    assert anchor["schema_version"] == "gate2c_anchor.v1"
    assert anchor["gated"] is False
    assert anchor["reported_anchor_not_gated"] is True
    # the anchor reads the SAME frozen floor the lock cites.
    assert anchor["floor_source"] == GATE2C_FLOOR_RUN
    floor_sha = hashlib.sha256(
        (ROOT / GATE2C_FLOOR_RUN).read_bytes()
    ).hexdigest()
    assert anchor["floor_sha256"] == floor_sha
    # the published sources the report names are the ones the anchor consumed.
    anchor_files = {s["file"] for s in anchor["published_sources"]}
    assert set(report["published_sources"]) == anchor_files
    for rel in anchor_files:
        assert (ROOT / rel).exists(), rel
    assert anchor["summary"]["calibration"].startswith("none")


def test_gate2c_anchor_moments_recompute_and_are_honest():
    """The anchor's OUR-side moments recompute from the frozen floor: the
    per-year within-couple rank 0.4928 comes straight from the floor
    decomposition, and the contingency relative-diagonal delta recomputes from
    the frozen 3x3 assort_mating reference moments. Nothing is calibrated."""
    anchor = json.loads((ROOT / GATE2C_ANCHOR_RUN).read_text())
    floor = _gate2c_floor()
    decomp = floor["assortative_correlation_report_only"]["decomposition"]
    moments = anchor["our_moments"]
    assert moments["within_couple_earnings_rank_spearman"] == pytest.approx(
        decomp["earnings_axis_spearman"]
    )
    assert moments["within_sex_rank_spearman"] == pytest.approx(
        decomp["within_sex_aime_proxy_rank_spearman"]
    )
    # recompute delta_t (relative sum of diagonals) from the frozen 3x3.
    ref = floor["reference_moments"]
    matrix = [
        [ref[f"assort_mating.own{o}_spouse{s}"]["rate"] for s in (1, 2, 3)]
        for o in (1, 2, 3)
    ]
    total = sum(sum(r) for r in matrix)
    row = [sum(r) / total for r in matrix]
    col = [sum(matrix[o][s] for o in range(3)) / total for s in range(3)]
    obs = sum(matrix[i][i] for i in range(3)) / total
    exp = sum(row[i] * col[i] for i in range(3))
    delta = round(obs / exp, 4)
    assert moments["contingency_relative_diagonal_delta"] == pytest.approx(
        delta
    )
    # direction: our rank above the Schwartz annual-earnings Pearson, our
    # contingency delta above independence (1.0). Reported, not calibrated.
    assert moments["within_couple_earnings_rank_spearman"] > 0.23
    assert moments["contingency_relative_diagonal_delta"] > 1.0
    assert anchor["summary"]["any_level_calibrated"] is False


def test_gate2c_within_sex_rank_implementation_delta_recorded():
    """flip-note 6: the committed within-sex AIME-proxy rank rho 0.2165 is
    carried, and the 0.2165-vs-round-1-0.2133 implementation delta is
    documented as report-only / immaterial."""
    g2c = _gate_2c()
    assert g2c["assortative_decomposition"][
        "within_sex_aime_proxy_rank_spearman"
    ] == pytest.approx(0.2165)
    delta = g2c["external_anchor_report"][
        "within_sex_rank_implementation_delta"
    ]
    assert "0.2165" in delta
    assert "0.2133" in delta
    assert "immaterial" in delta
    # and it matches the frozen floor's committed decomposition value.
    floor = _gate2c_floor()
    decomp = floor["assortative_correlation_report_only"]["decomposition"]
    assert decomp["within_sex_aime_proxy_rank_spearman"] == pytest.approx(
        0.2165
    )


def test_gate2c_certification_scope_consistent_with_locked_2a_map():
    """The 2c certification_scope certifies the 27 gated marriage x earnings
    cells and supports spousal/survivor LEVELS; it is consistent with (and
    does not rewrite) the locked tranche-2a map's marriage_x_earnings_joint
    entry, which stays as-is."""
    csc = _gate_2c()["certification_scope"]
    assert csc["tranche"] == "2c_marriage_earnings_joint"
    certifies = csc["certifies"]
    assert "27 gated cells" in certifies
    assert "assortative-mating" in certifies or "JOINT" in certifies
    supports = " ".join(csc["supports"])
    assert "spousal / survivor benefit LEVELS" in supports
    dns = " ".join(csc["does_not_support"])
    assert "2b" in dns and "OUTSIDE" in dns
    # consistent with the locked 2a map's 2c required_for (NOT rewritten).
    locked_map = _gate_2()["scope"]["certification_scope"]["tranches"]
    c_required = " ".join(
        locked_map["2c_marriage_earnings_joint"]["required_for"]
    )
    assert "spousal / survivor benefit LEVELS" in c_required
    assert "who" in c_required and "marries whom" in c_required
    # the locked 2a provision map's marriage_x_earnings_joint entry is still
    # the amendment-2 text (NOT COVERED by 2a; requires 2c) -- untouched.
    pmap = {
        row["provision_class"]: row
        for row in _gate_2()["scope"]["certification_scope"][
            "provision_class_map"
        ]
    }
    mxe = pmap["marriage_x_earnings_joint"]
    assert mxe["locked_coverage"] == "NOT COVERED"
    assert mxe["requires_tranche"] == ["2c_marriage_earnings_joint"]


def test_gate2c_history_entry_records_the_lock():
    """gate_2c.history carries the 2026-07-10-gate2c-lock entry with the three
    ceremony comment ids, the ratifying merge (#129 / 3053795), and
    no_self_rescue."""
    hist = _gate_2c_block()["history"]
    entry = next(e for e in hist if e["id"] == "2026-07-10-gate2c-lock")
    assert entry["flipped_live"] == "this pull request"
    rr = entry["referee_round"]
    assert "4935540075" in rr["review"]
    assert "4937213555" in rr["fixes"]
    assert "4937857811" in rr["verification"]
    assert "3053795" in entry["ratified"]
    assert "PR 129" in entry["ratified"]
    assert "no_self_rescue" in entry["ratified"]
    assert "ZERO threshold movement" in entry["content"]


def test_gate2c_flip_notes_all_seven_implemented():
    """The seven verification-round flip-time notes are enumerated as
    implemented in the ceremony_record."""
    notes = _gate_2c()["ceremony_record"]["flip_notes_implemented"]
    assert set(notes) == {
        "note_1_corrected_warts_carried",
        "note_2_readme_tiers_rows_restored",
        "note_3_a5b_residual_documented",
        "note_4_candidate_cut_provenance_explicit",
        "note_5_window_overlap_quantified",
        "note_6_within_sex_rank_delta_recorded",
        "note_7_external_anchor_bundled",
    }
    for key, text in notes.items():
        assert text.strip(), key


def test_gate2c_covers_names_the_scored_surface():
    """The covers text names the marriage x earnings joint on the per-year
    axis and the scored surface (description-claims-exactly), not the
    amendment-2 stub's generic 'joint of marriage and earnings' alone."""
    covers = _gate_2c_block()["covers"]
    assert "MARRIAGE and EARNINGS" in covers
    assert "per-year" in covers
    assert "27 gated cells" in covers
    assert "description_claims_exactly_the_scored_surface" in covers


def test_gate2c_corrected_warts_carried_not_round1_submission():
    """flip-note 1: the flip carries the CORRECTED fixes-round warts, not
    #124's round-1 submission text. The record names couple-disjoint /
    1968-2022 / per-year axis / detrended / not-symmetric, and the #124-body
    pointer is annotated as superseded."""
    g2c = _gate_2c()
    rehome = g2c["ceremony_record"]["re_homing"]
    assert "superseded" in rehome
    assert "1993-2022" in rehome  # names the convicted text as superseded
    # corrected facts ride in the record, not the round-1 versions.
    dca = g2c["directed_couple_record_accuracy"]
    assert dca["one_directional_records"] == 237
    assert dca["start_year_mismatched_mirror_pairs"] == 144
    assert "NOT all PSID marriages" in g2c["estimand"]
    n1 = g2c["ceremony_record"]["flip_notes_implemented"][
        "note_1_corrected_warts_carried"
    ]
    assert "couple-disjoint" in n1
    assert "1968-2022" in n1
    assert "per-year earnings axis" in n1


def test_gate2c_flip_leaves_locked_2a_and_2b_byte_identical():
    """D1 SUBSET master-compare (the form that held at #112 / #122, no
    red-master window): the flip changes only gate_2c, so gate_2.thresholds
    (tranche 2a) AND gate_2b stay byte-identical to origin/master and gate_2
    gains no top-level key. These asserts hold in EVERY state (before and
    after the flip merges), so they are unconditional."""
    master = _master_gate2()
    if master is None:
        pytest.skip("origin/master gates.yaml unreachable")
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    cur_g2 = gates["gates"]["gate_2"]
    # locked tranche-2a thresholds unchanged (holds in every state).
    assert cur_g2["thresholds"] == master["thresholds"]
    assert cur_g2["thresholds"]["locked"] is True
    # the 2a scored surface is still 46 gated + 16 report-only.
    a_gated, a_report = _gated_report_sets(cur_g2["thresholds"])
    assert len(a_gated) == 46
    assert len(a_report) == 16
    # locked gate-2b block unchanged (holds in every state).
    assert cur_g2["gate_2b"] == master["gate_2b"]
    assert cur_g2["gate_2b"]["locked"] is True
    # subset: the flip adds no gate_2 top-level key (gate_2b/gate_2c/
    # amendment_history all pre-exist); a bogus added/removed key fails loudly.
    assert set(cur_g2) - set(master) == set()
    assert set(master) - set(cur_g2) == set()


# --------------------------------------------------------------------------
# gate_m4 (the M4 DI disability gate) LOCKED-HOT bindings. gate_m4 is ADDED
# fresh as a locked top-level gate (unlike gate_2b/2c, which pre-existed as
# unlocked stubs). Every internal tolerance is machine-bound to the ratified,
# FROZEN 100-seed PERSON-DISJOINT half-split floor runs/m4_gate_floors_v1.json:
# tolerance == round(floor mean + k * floor sd, 3) under the pre-registered
# MIXED k (FLOW k=3 / prevalence STOCK k=4), capped at T_max = ln(1.5). Each
# anchor cell gates on the candidate's own per-seed invariant with margin >=
# MARGIN_K=3 x the committed real half-split sd. These bindings are LOCKED-HOT
# (the 2a lesson) and run everywhere (committed files only). They touch NO
# locked sibling block, and a D1-style SUBSET master-compare proves the flip
# leaves gate_1 / gate_2 (2a + gate_2b + gate_2c) / gate_3 byte-identical to
# origin/master, gate_m4 the sole new key.
# --------------------------------------------------------------------------
M4_FLOOR_RUN = "runs/m4_gate_floors_v1.json"
M4_FLOOR_KEY = "noise_floor_seeds_0_99"
M4_ANCHOR_DIR = "data/external/di_asr_2023"


def _gate_m4_block() -> dict:
    gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
    return gates["gates"]["gate_m4"]


def _gate_m4() -> dict:
    """gate_m4.thresholds. Post-lock the bindings run unconditionally."""
    return _gate_m4_block()["thresholds"]


def _m4_floor() -> dict:
    return json.loads((ROOT / M4_FLOOR_RUN).read_text())


def _m4_internal_derive(cell: str, k: float, rounding: int) -> float:
    stats = _m4_floor()["internal_noise_floor"][M4_FLOOR_KEY][cell]
    return round(stats["mean"] + k * stats["sd"], rounding)


def _m4_internal_tolerances() -> dict:
    tolerances: dict = {}
    for view in _gate_m4()["internal_surface"]["views"].values():
        tolerances.update(view["tolerances"])
    return tolerances


def _master_gates_mapping() -> dict | None:
    """origin/master gates mapping, self-fetching the ref if needed."""
    for attempt in range(2):
        try:
            text = subprocess.run(
                ["git", "show", "origin/master:gates.yaml"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            return yaml.safe_load(text)["gates"]
        except (subprocess.CalledProcessError, FileNotFoundError):
            if attempt == 0:
                subprocess.run(
                    ["git", "fetch", "origin", "master"],
                    cwd=ROOT,
                    capture_output=True,
                )
                continue
            return None
    return None


def test_gate_m4_locked_added_as_anchor_based_top_level_gate():
    """gate_m4 is locked, kind anchor_based, and a NEW top-level gate (it did
    not pre-exist as an unlocked stub the way gate_2b/2c did)."""
    b = _gate_m4_block()
    assert b["locked"] is True
    assert b["status"] == "locked"
    assert b["kind"] == "anchor_based"
    assert b["id"] == "m4_disability"
    assert b["holdout_basis"] == [
        "ind2023er_employment_status",
        "di_asr_2023",
    ]
    g = _gate_m4()
    assert g["locked"] is True
    assert g["status"] == "locked"
    assert g["tranche_id"] == "m4_disability"
    assert g["kind"] == "anchor_based"


def test_gate_m4_locked_with_ceremony_record():
    """The full lock ceremony is recorded in-contract: the FOUR ceremony
    comment ids, the ratifying squash merge 0fa4a29 (PR 153), the
    delegated-authority note, and no_self_rescue."""
    record = json.dumps(_gate_m4()["ceremony_record"])
    for token in (
        "4950447491",  # round-1 adversarial referee AMEND BEFORE LOCK
        "4950571161",  # fixes A-F
        "4950648191",  # verification AMEND metadata-only
        "4950660426",  # body amendment executed
        "PR 153",  # ratifying PR
        "0fa4a29",  # ratifying squash merge commit
        "no_self_rescue",
    ):
        assert token in record, token
    assert "delegated" in record.lower()
    assert "metadata-only" in record.lower()


def test_gate_m4_floor_run_is_the_ratified_frozen_anchor():
    """The floor the locked thresholds cite is the ratified, frozen artifact
    that reads no gate."""
    g = _gate_m4()
    assert g["floor_run"] == M4_FLOOR_RUN
    floor = _m4_floor()
    assert floor["schema_version"] == "m4_gate_floors.v1"
    assert floor["holdout_basis"] == [
        "ind2023er_employment_status (PSID self-report)",
        "di_asr_2023 (in-repo SSA DI ASR tables, sha-pinned)",
    ]


def test_gate_m4_internal_tolerances_bind_to_floor():
    """Every locked internal tolerance == round(100-seed floor mean + k*sd,
    rounding) on the frozen floor, keyed on the floor cell itself."""
    g = _gate_m4()
    surface = g["internal_surface"]
    for view_name, view in surface["views"].items():
        rules = view["derivations"]["rules"]
        tolerances = view["tolerances"]
        assert set(rules) == set(tolerances), view_name
        assert view["derivations"]["floor_run"] == M4_FLOOR_RUN
        assert view["derivations"]["floor_key"] == M4_FLOOR_KEY
        for cell, rule in rules.items():
            assert rule["key"] == cell, f"{view_name}.{cell}"
            derived = _m4_internal_derive(
                cell, rule["k"], rule.get("rounding", 3)
            )
            assert derived == pytest.approx(tolerances[cell]), (
                f"{view_name}.{cell}: derived {derived} != tolerance "
                f"{tolerances[cell]}"
            )


def test_gate_m4_mixed_k_flow3_stock4():
    """The pre-registered MIXED k: FLOW hazards @k=3, prevalence STOCK @k=4;
    each cell's quantity_type matches its k, and the two views are homogeneous
    in k."""
    views = _gate_m4()["internal_surface"]["views"]
    flow = views["internal_flow_hazards"]
    stock = views["internal_prevalence_stock"]
    assert flow["quantity_type"] == "flow"
    assert stock["quantity_type"] == "stock"
    for rule in flow["derivations"]["rules"].values():
        assert rule["k"] == 3
        assert rule["quantity_type"] == "flow"
    for rule in stock["derivations"]["rules"].values():
        assert rule["k"] == 4
        assert rule["quantity_type"] == "stock"
    # exactly 6 flow + 2 stock = 8 internal gated cells.
    assert len(flow["tolerances"]) == 6
    assert len(stock["tolerances"]) == 2
    assert set(stock["tolerances"]) == {
        "prevalence.50-59|female",
        "prevalence.50-59|male",
    }


def test_gate_m4_power_cap_binds_every_gated_internal_cell():
    """Every gated internal tolerance <= T_max = ln(1.5); the floor partitioned
    exactly on that cap (+ >=20 events); M4 declares NO aggregates."""
    g = _gate_m4()
    assert g["power_cap"]["t_max"] == "ln(1.5)"
    assert g["power_cap"]["aggregations"] == {}
    floor = _m4_floor()
    t_max = floor["internal_noise_floor"]["t_max"]
    assert t_max == pytest.approx(math.log(1.5))
    for cell, tol in _m4_internal_tolerances().items():
        assert tol <= t_max, f"{cell} tolerance {tol} exceeds T_max"


def test_gate_m4_partition_matches_committed_floor_12_24():
    """gated / report_only == the floor's derived partition (events + power
    cap; no aggregates), not hand-picked; counts 12 (8 internal + 4 anchor) /
    24 report-only; disjoint; internal|report a real cover of the 32 reference
    moments; anchor cells separate from the reference moments."""
    g = _gate_m4()
    floor = _m4_floor()
    partition = floor["gate_partition"]
    gated_internal = set(_m4_internal_tolerances())
    gated_anchor = set(g["anchor_surface"]["cells"])
    report_only = set(g["report_only"])
    assert gated_internal == set(partition["internal_gate_eligible"])
    assert gated_anchor == set(partition["anchor_gate_eligible"])
    assert report_only == set(partition["report_only"])
    assert len(gated_internal) == 8
    assert len(gated_anchor) == 4
    assert len(report_only) == 24
    assert gated_internal.isdisjoint(report_only)
    reference = set(floor["reference_moments"])
    assert gated_internal | report_only == reference
    assert len(reference) == 32
    # the anchor cells are bounded invariants, not |ln| reference moments.
    assert gated_anchor.isdisjoint(reference)
    per_seed = floor["internal_noise_floor"][M4_FLOOR_KEY]
    for cell in gated_internal:
        assert cell in per_seed, cell


def test_gate_m4_report_only_reasons_all_tolerance_above_t_max():
    """All 24 report-only cells carry the floor's OWN machine reason
    tolerance_above_t_max (power); NO below_20_events demotions; and the two
    conversion cells demote on power, not the withdrawn family reason."""
    g = _gate_m4()
    floor = _m4_floor()
    cs = floor["internal_noise_floor"]["cell_stability"]
    reasons: dict = {}
    for cell in g["report_only"]:
        reason = cs[cell]["report_reason"]
        reasons[reason] = reasons.get(reason, 0) + 1
    assert reasons == {"tolerance_above_t_max": 24}
    for conv in (
        "conversion.retired_from_disabled|female",
        "conversion.retired_from_disabled|male",
    ):
        assert conv in g["report_only"]
        assert cs[conv]["report_reason"] == "tolerance_above_t_max"
        assert cs[conv]["tolerance"] > math.log(1.5)
    # the withdrawn category-error reason appears NOWHERE in the artifact.
    assert "level_bridged_via_anchor_shape" not in json.dumps(floor)


def test_gate_m4_protocol_is_the_ratified_k20_2a_estimator():
    """The scoring protocol is tranche 2a's ratified mean-over-K=20 estimator
    (amendment 1, 5200+k), adopted from the START; the conventions match the
    locked gate_2 (2a) protocol; the fresh-run schema is [20, 8, 5]; the OC
    matches the floor."""
    g = _gate_m4()
    proto = g["protocol"]
    assert proto["gate_seeds"] == [0, 1, 2, 3, 4]
    assert proto["candidate_draws"] == 20
    assert proto["draw_stream_base"] == 5200
    assert "5200 + k" in proto["candidate_draw_stream"]
    assert "K=20" in proto["estimator"]
    assert "NOT the mean of the per-draw" in proto["estimator"]
    # estimator-convention equality with the locked 2a protocol.
    g2a = _gate_2()
    a_candidate = g2a["protocol"]["candidate"]
    assert "5200 + k" in a_candidate
    assert "5200 + k" in proto["candidate_draw_stream"]
    # fresh-run schema: per-draw INTERNAL rates [20, 8, 5], invalidation.
    schema = proto["fresh_run_artifact_schema"]
    assert schema["per_draw_per_cell_rates"]["shape"] == [20, 8, 5]
    assert schema["undefined_draw_rule"]["pre_specified"] is True
    assert schema["per_draw_dispersion_disclosure"]["report_only"] is True
    # the OC recorded in the contract matches the artifact's recomputation.
    oc = proto["faithful_candidate_oc"]
    art_oc = _m4_floor()["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == pytest.approx(art_oc["p_seed_pass"])
    assert oc["p_gate_pass_4_of_5"] == pytest.approx(
        art_oc["p_gate_pass_4_of_5"]
    )
    assert oc["n_gated_internal_cells"] == art_oc["n_gated_internal_cells"]
    assert oc["n_gated_internal_cells"] == 8


def test_gate_m4_oc_recomputes_from_tolerances_and_sigmas():
    """The faithful-candidate OC (p_seed 0.9408 / p_gate 0.9689) recomputes
    from the 8 locked internal tolerances and the floor sigmas on the
    draw-noise-free half-normal basis, independent of the stored value."""
    g = _gate_m4()
    floor = _m4_floor()["internal_noise_floor"][M4_FLOOR_KEY]
    tolerances = _m4_internal_tolerances()
    assert len(tolerances) == 8
    p_seed = 1.0
    for cell, tol in tolerances.items():
        sigma = floor[cell]["realized_sigma"]
        p_seed *= 2.0 * _normal_cdf(tol / sigma) - 1.0
    p_gate = p_seed**5 + 5 * p_seed**4 * (1.0 - p_seed)
    assert round(p_seed, 4) == 0.9408
    assert round(p_gate, 4) == 0.9689
    oc = g["protocol"]["faithful_candidate_oc"]
    assert oc["p_seed_pass"] == round(p_seed, 4)
    assert oc["p_gate_pass_4_of_5"] == round(p_gate, 4)


def test_gate_m4_k_selection_rule_and_k2_oc_committed():
    """The k-selection rule is committed and machine-checkable: flow k=3 /
    stock k=4, the k=2 flow OC 0.2901 (unusable), the k=3 flow OC 0.9717, the
    uniform-k sensitivity 21/12/2, and option-(i) uniform-k3 0.9008 -- all
    bound to the floor's k_selection."""
    ks = _gate_m4()["k_selection"]
    aks = _m4_floor()["k_selection"]
    assert ks["chosen_flow_k"] == aks["chosen_flow_k"] == 3
    assert ks["chosen_stock_k"] == aks["chosen_stock_k"] == 4
    assert ks["k2_flow_oc_gate_4_of_5"] == aks["k2_flow_oc_gate_4_of_5"]
    assert ks["k2_flow_oc_gate_4_of_5"] == 0.2901
    assert ks["k3_flow_oc_gate_4_of_5"] == aks["k3_flow_oc_gate_4_of_5"]
    assert ks["k3_flow_oc_gate_4_of_5"] == 0.9717
    assert ks["alt_option_i_uniform_k3_oc"] == 0.9008
    assert ks["uniform_k_sensitivity"] == {"2": 21, "3": 12, "4": 2}
    assert (
        ks["uniform_k_sensitivity"]["3"]
        == aks["alt_option_i_uniform_k3_full_surface"]["n_cells"]
    )


def test_gate_m4_anchor_cells_margin_rule_and_recompute():
    """The 4 anchor cells gate on the candidate's own per-seed invariant with
    margin >= MARGIN_K=3 x the committed real half-split sd; every committed
    margin (6.099/5.298/4.797/12.806) recomputes from the frozen floor's
    anchor_checks, and each real-data margin clears 3 sigma by a wide gap."""
    g = _gate_m4()
    surface = g["anchor_surface"]
    assert surface["margin_k"] == 3
    floor = _m4_floor()
    ac = floor["anchor_checks"]
    seen = set()
    for cell, cfg in surface["cells"].items():
        a = ac[cell]
        if "prevalence_ageshape" in cell:
            gap = a["psid_min_adjacent_gap"]
            sd = a["half_split_floor"]["min_gap"]["sd"]
            assert cfg["margin_basis"] == "half_split_floor.min_gap.sd"
        else:
            gap = a["psid_dominance_margin"]
            sd = a["half_split_floor"]["share"]["sd"]
            assert cfg["margin_basis"] == "half_split_floor.share.sd"
        assert cfg["real_half_split_sd"] == pytest.approx(sd)
        margin = round(gap / sd, 3)
        assert margin == cfg["margin_sigma_units"], cell
        assert margin >= 3.0
        assert a["margin_sigma_units"] == cfg["margin_sigma_units"]
        seen.add(cell)
    assert seen == {
        "prevalence_ageshape.comonotone|female",
        "prevalence_ageshape.comonotone|male",
        "conversion_exit.retirement_dominant|female",
        "conversion_exit.retirement_dominant|male",
    }


def test_gate_m4_epsilon_tilt_degenerate_fails_the_pinned_margin():
    """The pinned MARGIN reading (finding 3): an epsilon-tilt candidate
    (+0.001/band) passes the bare ordinal but FAILS the margin -- margin_sigma
    0.0917 (f) / 0.0912 (m) = tilt / committed sd, << MARGIN_K=3."""
    et = _gate_m4()["degenerate_candidates"]["epsilon_tilt_prevalence"]
    floor_ac = _m4_floor()["anchor_checks"]
    sds = {
        "female": floor_ac["prevalence_ageshape.comonotone|female"][
            "half_split_floor"
        ]["min_gap"]["sd"],
        "male": floor_ac["prevalence_ageshape.comonotone|male"][
            "half_split_floor"
        ]["min_gap"]["sd"],
    }
    for sex in ("female", "male"):
        row = et[sex]
        assert row["real_half_split_sd"] == pytest.approx(sds[sex])
        recomputed = round(
            row["min_adjacent_gap"] / row["real_half_split_sd"], 4
        )
        assert recomputed == row["margin_sigma_units"], sex
        assert row["margin_sigma_units"] < 3
        assert row["passes_bare_ordinal"] is True
        assert row["passes_pinned_margin"] is False


def test_gate_m4_anchor_gate_rule_separates_candidate_from_evidence_time():
    """flip-note 3: each anchor gate_rule separates the candidate-voiced
    condition (the candidate's own margin, the ONLY thing it must satisfy)
    from the evidence-time cell conditions (holds on all 100 real halves; the
    >=20-exit floor gated the CELL, not the candidate). The sparse-exit
    all-retire candidate is pinned as caught INTERNALLY."""
    cells = _gate_m4()["anchor_surface"]["cells"]
    for cfg in cells.values():
        rule = cfg["gate_rule"]
        cand = rule["candidate_condition"]
        assert "ONLY" in cand
        assert "MARGIN_K=3" in cand or "3 sigma" in cand
        assert "4 of 5" in cand
        evid = rule["evidence_time_conditions"]
        assert "flip-note 3" in evid
        # the evidence-time conditions are floor properties, kept separate
        # from the candidate condition and not re-run on the candidate.
        assert "floor" in evid.lower()
        assert "candidate" in evid.lower()
    # the sparse-exit construction is foreclosed: caught internally.
    conv = cells["conversion_exit.retirement_dominant|female"]["gate_rule"]
    assert "recovery.60-66" in conv["evidence_time_conditions"]
    assert "INTERNALLY" in conv["evidence_time_conditions"]


def test_gate_m4_flip_notes_all_five_implemented():
    """The five verification-round flip-time notes are enumerated as
    implemented in the ceremony_record."""
    notes = _gate_m4()["ceremony_record"]["flip_notes_implemented"]
    assert set(notes) == {
        "note_1_tier_rerefresh",
        "note_2_oc_at_or_above_precedent",
        "note_3_anchor_gate_rule_prose_separated",
        "note_4_sigma_units_presentation",
        "note_5_bootstrap_optional_not_committed",
    }
    for key, text in notes.items():
        assert text.strip(), key


def test_gate_m4_oc_at_or_above_precedent_not_within():
    """flip-note 2: the OC-band wording is 'at or above precedent', not
    'within' -- 0.9689 sits above the 2a/2b/2c band top (0.9685); the band is
    a floor."""
    g = _gate_m4()
    oc_note = g["protocol"]["faithful_candidate_oc"]["oc_vs_precedent"]
    ks_note = g["k_selection"]["oc_vs_precedent"]
    for note in (oc_note, ks_note):
        assert "AT OR ABOVE" in note.upper()
        # the corrective note names the band top it sits above, not "within".
        assert "0.9685" in note or "band" in note.lower()
    band = g["k_selection"]["precedent_oc_band"]
    assert max(band.values()) == 0.9685
    p_gate = g["protocol"]["faithful_candidate_oc"]["p_gate_pass_4_of_5"]
    assert p_gate > 0.9685
    assert round(p_gate - 0.9685, 4) == 0.0004


def test_gate_m4_anchor_pins_di_asr_2023_match_disk():
    """The in-repo SSA DI ASR 2023 anchor is sha-pinned and REPORTED not gated;
    every pinned sha256 matches the file on disk; the anchor moves no floor
    value (no calibration)."""
    report = _gate_m4()["external_anchor_report"]
    assert report["reported_anchor_not_gated"] is True
    assert report["anchor_dir"] == M4_ANCHOR_DIR
    assert report["calibration"].startswith("none")
    pins = report["anchor_pins"]
    assert set(pins) == {
        f"{M4_ANCHOR_DIR}/tables.json",
        f"{M4_ANCHOR_DIR}/provenance.md",
    }
    for rel, meta in pins.items():
        payload = (ROOT / rel).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == meta["sha256"], rel
    # the tables sha matches the frozen floor's own anchor pin.
    floor = _m4_floor()
    assert (
        pins[f"{M4_ANCHOR_DIR}/tables.json"]["sha256"]
        == floor["anchor_tables"]["sha256"]
    )


def test_gate_m4_covers_names_the_scored_surface():
    """The covers text names the disability surface and the 12 gate-eligible
    cells (description-claims-exactly), and declares no SSA DI level is
    gated."""
    covers = _gate_m4_block()["covers"]
    assert "DISABILITY module" in covers
    assert "anchor-based" in covers.lower() or "ANCHOR-BASED" in covers
    assert "8 internal" in covers
    assert "4 anchor" in covers
    assert "no SSA DI LEVEL is gated" in covers


def test_gate_m4_certification_scope():
    """gate_m4 certifies the 12 gated disability cells and supports the
    disabled composition a payable DI baseline rides on; it does NOT support
    SSA DI benefit LEVELS (statutory-formula oracle, outside M4)."""
    csc = _gate_m4()["certification_scope"]
    assert csc["tranche"] == "m4_disability"
    assert "12 gated cells" in csc["certifies"]
    supports = " ".join(csc["supports"])
    assert "payable DI baseline" in supports or "disabled composition" in (
        supports
    )
    dns = " ".join(csc["does_not_support"])
    assert "LEVELS" in dns
    assert "oracle" in dns


def test_gate_m4_history_entry_records_the_lock():
    """gate_m4.history carries the 2026-07-12-m4-gate-lock entry with the four
    ceremony comment ids, the ratifying merge (PR 153 / 0fa4a29),
    no_self_rescue, and ZERO threshold movement."""
    hist = _gate_m4_block()["history"]
    entry = next(e for e in hist if e["id"] == "2026-07-12-m4-gate-lock")
    assert entry["flipped_live"] == "this pull request"
    rr = entry["referee_round"]
    assert "4950447491" in rr["review"]
    assert "4950571161" in rr["fixes"]
    assert "4950648191" in rr["verification"]
    assert "4950660426" in rr["verification"]
    assert "0fa4a29" in entry["ratified"]
    assert "PR 153" in entry["ratified"]
    assert "no_self_rescue" in entry["ratified"]
    assert "ZERO threshold movement" in entry["content"]


def test_gate_m4_flip_leaves_locked_siblings_byte_identical():
    """D1 SUBSET master-compare (the form that held at #122 / #130, no
    red-master window): the flip ADDS gate_m4 and changes nothing else, so
    gate_1 / gate_2 (2a + gate_2b + gate_2c) / gate_3 stay deep-equal to
    origin/master and gate_m4 is the SOLE new key. These asserts hold in every
    state (before and after the flip merges), so they are unconditional."""
    master = _master_gates_mapping()
    if master is None:
        pytest.skip("origin/master gates.yaml unreachable")
    current = yaml.safe_load((ROOT / "gates.yaml").read_text())["gates"]
    added = set(current) - set(master)
    removed = set(master) - set(current)
    # gate_m4 may already be on master once the flip merges; in that state the
    # set difference is empty. Before merge it is exactly {gate_m4}. A sibling
    # locked-gate flip (gate_w1, ratified the same day) may add its own sole
    # key on a coordinated both-blocks branch -- the tolerant form the W1
    # flip-fidelity referee verified (PR #160 comment); any OTHER addition
    # still fails.
    # The M6 lock flip (2026-07-13, this file's sibling gate_m6) adds gate_m6
    # as its own sole new key -- the same added-locked-gate tolerance, extended
    # for the gate_m6 flip exactly as it was for gate_w1 (empty once merged,
    # {gate_m6} while its flip PR is open). Any OTHER addition still fails.
    assert added in (
        set(),
        {"gate_m4"},
        {"gate_w1"},
        {"gate_m6"},
    ), added
    assert removed == set()
    for key in master:
        if key in ("gate_m4", "gate_w1", "gate_m6"):
            continue
        assert current[key] == master[key], f"{key} changed vs master!"
    # gate_2's locked tranche-2a thresholds + gate_2b + gate_2c untouched.
    assert current["gate_2"]["thresholds"]["locked"] is True
    assert current["gate_2"]["gate_2b"]["locked"] is True
    assert current["gate_2"]["gate_2c"]["locked"] is True


# --------------------------------------------------------------------------
# gate_b2_claiming (issue #74 component CA, Phase B) THRESHOLD BINDING --
# DRAFT, pre-lock. The block does not exist in gates.yaml yet: it is carried
# as a string in runs/claiming_gate_floors_v1.json
# (draft_gates_yaml_fragment.text), the gate-3 / gate_mortality precedent.
# While GATE_B2_CLAIMING_BLOCK_LANDED is False these bindings read the DRAFT
# block from the artifact and assert gates.yaml is innocent of it; the
# commit that inserts the block flips ONE constant and the same bindings run
# LOCKED-HOT against the live contract (the 2a lesson). Every tolerance is
# recomputed here from the VERIFIED floor basis
# runs/claiming_publication_floor_v1.json's STRATA and TRENDS with this
# module's own Decimal arithmetic -- never from a typed number and never
# from the gate artifact's own copy -- and every alternative the referees
# priced is recomputed as a perturbation that FAILS if any knob or the
# rounding mode changes.
# --------------------------------------------------------------------------
B2C_FLOOR_RUN = "runs/claiming_publication_floor_v1.json"
#: (size, sha256) of the VERIFIED floor basis (floors v2 at cd8f167;
#: verification VERIFIED -- READY FOR THRESHOLD BINDING). Must not move.
B2C_FLOOR_COMMITTED = (
    227_079,
    "bd78d632219175d2ab47bc7a87661dde782a6a262a26add3a3be349618593ae1",
)
B2C_GATE_RUN = "runs/claiming_gate_floors_v1.json"
#: (size, sha256) of the gate-schema artifact as committed; re-stated in
#: the same commit as any rebuild.
B2C_GATE_COMMITTED = (
    271_833,
    "7d4eb3e33920fbcf50fe28bc46370704bd282bb897148261314f50b05fe9a16c",
)
B2C_EDITION = "data/external/ssa_claim_ages_2023supplement.json"
B2C_TRANSCRIPTION = "scripts/build_ssa_claim_ages.py"
B2C_BUILDER = "scripts/build_claiming_gate_floors_v1.py"
B2C_K_REV = 2.0
B2C_ROUNDING_PP = 0.05
B2C_T_MAX_PP = 3.0
B2C_CATEGORIES = (
    "age62",
    "age63",
    "age64",
    "age65",
    "age66",
    "age67_69",
    "age70plus",
)
B2C_SEXES = ("female", "male")
B2C_FIT_YEARS = tuple(range(1998, 2020))
B2C_HOLDOUT = {1: 2020, 2: 2021, 3: 2022}
B2C_KNIFE = "age66|female|h1"
B2C_TIE = "age70plus|female|h2"
#: PRE-LOCK MARKER (the mortality pattern). Flipped to True in the SAME
#: commit that inserts the block, in every file that carries it (the
#: artifact's flip_plan lists them), which also retires the live-file
#: guard test tests/test_claiming_publication_floor.py::
#: test_no_gate_b2_claiming_exists_in_gates_yaml.
GATE_B2_CLAIMING_BLOCK_LANDED = False


def _b2c_floor() -> dict:
    return json.loads((ROOT / B2C_FLOOR_RUN).read_text())


def _b2c_gate() -> dict:
    return json.loads((ROOT / B2C_GATE_RUN).read_text())


def _b2c_edition() -> dict:
    return json.loads((ROOT / B2C_EDITION).read_text())


def _b2c_cells() -> list[str]:
    return [
        f"{c}|{s}|h{h}"
        for s in B2C_SEXES
        for c in B2C_CATEGORIES
        for h in (1, 2, 3)
    ]


def _b2c_tolerance(term_pp, trend, horizon, rounding_pp, mode):
    """This module's OWN evaluation of the tolerance rule: the exact
    decimal sum of the three summands quantised to 2 dp under ``mode``."""
    raw = (
        Decimal(repr(term_pp))
        + Decimal(repr(abs(trend))) * horizon
        + Decimal(repr(rounding_pp))
    )
    return float(raw.quantize(Decimal("0.01"), rounding=mode)), raw


def _b2c_sd_knob(floor: dict) -> float:
    return round(floor["strata"]["conditional_terminal_year"]["sd_pp"], 4)


def _b2c_trends(floor: dict) -> dict:
    derivations = floor["power_cap"]["derivations"]
    return {c: derivations[c]["trend_pp_per_year"] for c in _b2c_cells()}


def _b2c_derive(
    floor: dict,
    term_by_h=None,
    k=B2C_K_REV,
    rounding_pp=B2C_ROUNDING_PP,
    mode=ROUND_HALF_UP,
) -> dict:
    """Every cell's tolerance from the FLOOR's strata and trends."""
    if term_by_h is None:
        term = round(k * _b2c_sd_knob(floor), 6)
        term_by_h = {1: term, 2: term, 3: term}
    trends = _b2c_trends(floor)
    out = {}
    for cell in _b2c_cells():
        h = int(cell.split("|")[2][1:])
        tol, raw = _b2c_tolerance(
            term_by_h[h], trends[cell], h, rounding_pp, mode
        )
        out[cell] = {"tolerance_pp": tol, "raw": raw}
    return out


def _b2c_partition(tols: dict) -> tuple[dict, dict]:
    gated = {
        c: v["tolerance_pp"]
        for c, v in tols.items()
        if v["tolerance_pp"] <= B2C_T_MAX_PP
    }
    report = {
        c: v["tolerance_pp"]
        for c, v in tols.items()
        if v["tolerance_pp"] > B2C_T_MAX_PP
    }
    return gated, report


def _b2c_cond(row: dict) -> dict:
    cats = row["categories"]
    total = sum(cats[c] for c in B2C_CATEGORIES)
    return {c: 100.0 * cats[c] / total for c in B2C_CATEGORIES}


def _b2c_series(doc: dict, category: str, sex: str) -> list[float]:
    return [
        _b2c_cond(doc["data"][sex][str(y)])[category] for y in B2C_FIT_YEARS
    ]


def _b2c_actual(doc: dict, category: str, sex: str, h: int) -> float:
    return _b2c_cond(doc["data"][sex][str(B2C_HOLDOUT[h])])[category]


def _b2c_ols(xs, ys):
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    den = sum((x - mx) ** 2 for x in xs)
    slope = num / den
    return slope, my - slope * mx


def _b2c_predictors(doc: dict) -> dict:
    """The seventeen scanned rules, this module's own implementations."""

    def series(c, s):
        return _b2c_series(doc, c, s)

    def nearest(c, s, h):
        return series(c, s)[-1]

    def uniform(c, s, h):
        return 100.0 / len(B2C_CATEGORIES)

    def fit_mean(c, s, h):
        v = series(c, s)
        return sum(v) / len(v)

    def sex_pooled(c, s, h):
        return sum(series(c, o)[-1] for o in B2C_SEXES) / len(B2C_SEXES)

    def ols(window):
        def f(c, s, h):
            v = series(c, s)[-window:]
            slope, intercept = _b2c_ols(B2C_FIT_YEARS[-window:], v)
            return intercept + slope * (B2C_FIT_YEARS[-1] + h)

        return f

    def damped(window, delta):
        def f(c, s, h):
            v = series(c, s)[-window:]
            slope, _ = _b2c_ols(B2C_FIT_YEARS[-window:], v)
            return series(c, s)[-1] + delta * slope * h

        return f

    forecast = {
        "deployed_v1_nearest_year": nearest,
        "ols_full_fit_window": ols(22),
        "ols_last_10": ols(10),
        "ols_last_5": ols(5),
        "ols_last_3": ols(3),
        "damped_local_trend_w5_d0.5": damped(5, 0.5),
        "damped_local_trend_w5_d1.0": damped(5, 1.0),
        "damped_local_trend_w10_d0.5": damped(10, 0.5),
        **{f"ols_last_{w}": ols(w) for w in (13, 14, 15, 16, 17, 18)},
    }
    degenerate = {
        "uniform_over_seven_categories": uniform,
        "fit_window_mean": fit_mean,
        "sex_pooled_nearest_year": sex_pooled,
    }
    return {
        "forecast": forecast,
        "degenerate": degenerate,
        "all": {**forecast, **degenerate},
    }


def _b2c_deviations(predict, doc: dict, cells) -> dict:
    out = {}
    for cell in cells:
        c, s, h = cell.split("|")
        h = int(h[1:])
        out[cell] = abs(predict(c, s, h) - _b2c_actual(doc, c, s, h))
    return out


def _b2c_failures(devs: dict, gated: dict) -> list[str]:
    return sorted(c for c, d in devs.items() if d > gated[c])


def _gate_b2_claiming_block() -> dict:
    """The gate_b2_claiming block: the artifact's DRAFT fragment pre-flip,
    the live gates.yaml block post-flip."""
    if GATE_B2_CLAIMING_BLOCK_LANDED:
        gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
        return gates["gates"]["gate_b2_claiming"]
    text = _b2c_gate()["draft_gates_yaml_fragment"]["text"]
    return yaml.safe_load("gates:\n" + text)["gates"]["gate_b2_claiming"]


def _b2_tracked_text_files() -> list:
    try:
        listed = subprocess.check_output(
            ["git", "ls-files"], cwd=ROOT, text=True
        ).split("\n")
    except (OSError, subprocess.CalledProcessError):
        listed = [
            str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()
        ]
    keep = []
    for rel in listed:
        if not rel:
            continue
        if not (
            rel == "gates.yaml"
            or rel.startswith(
                ("docs/", "scripts/", "tests/", "src/", "runs/", "paper/")
            )
        ):
            continue
        if rel.endswith(
            (".png", ".pdf", ".pkl", ".parquet", ".zip", ".gz", ".h5")
        ):
            continue
        keep.append(ROOT / rel)
    return keep


def _b2_import_from_path(path: Path, name: str):
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    # the scratch copy resolves its repository root from its own location;
    # point every root-relative path at THIS repository
    module.ROOT = ROOT
    for attr, rel in (
        ("SOURCE_FLOOR_PATH", "SOURCE_FLOOR_REL"),
        ("ARTIFACT_PATH", "ARTIFACT_REL"),
        ("SOURCE_COVERAGE_PATH", "SOURCE_COVERAGE_REL"),
    ):
        if hasattr(module, rel):
            setattr(module, attr, ROOT / getattr(module, rel))
    return module


def test_gate_b2_claiming_floor_basis_bytes_are_pinned_and_read_by_path():
    """The verified floor's size + sha256 equal the constants here; the
    gate artifact records that it read exactly those bytes by path; the
    block derives from that floor and names its sha256."""
    path = ROOT / B2C_FLOOR_RUN
    assert path.stat().st_size == B2C_FLOOR_COMMITTED[0]
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest() == B2C_FLOOR_COMMITTED[1]
    )
    art = _b2c_gate()
    src = art["source_floor"]
    assert src["path"] == B2C_FLOOR_RUN
    assert (src["size_bytes"], src["sha256"]) == B2C_FLOOR_COMMITTED
    assert art["schema_version"] == "claiming_gate_floors.v1"
    assert art["reported_not_gated"] is True
    assert art["ceremony"]["gates_yaml_untouched"] is True
    block = _gate_b2_claiming_block()
    assert block["derived_from_floor"] == B2C_FLOOR_RUN
    assert block["derived_from_floor_sha256"] == B2C_FLOOR_COMMITTED[1]
    assert block["thresholds"]["derived_from"]["sha256"] == (
        B2C_FLOOR_COMMITTED[1]
    )
    assert block["thresholds"]["derived_from"]["size_bytes"] == (
        B2C_FLOOR_COMMITTED[0]
    )


def test_gate_b2_claiming_gate_artifact_bytes_are_pinned():
    """The gate artifact's committed bytes equal the constants here (the
    gate-3 digest-pin precedent: re-stated in the same commit as any
    rebuild), and its own builder sha equals the committed builder."""
    path = ROOT / B2C_GATE_RUN
    assert path.stat().st_size == B2C_GATE_COMMITTED[0]
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest() == B2C_GATE_COMMITTED[1]
    )
    art = _b2c_gate()
    assert (
        art["revision_pins"]["gate_builder_sha256"]
        == hashlib.sha256((ROOT / B2C_BUILDER).read_bytes()).hexdigest()
    )
    assert art["revision_pins"]["source_floor_sha256"] == (
        B2C_FLOOR_COMMITTED[1]
    )


def test_gate_b2_claiming_pre_lock_guard_or_live_block():
    """PRE-LOCK GUARD under GATE_B2_CLAIMING_BLOCK_LANDED. While False:
    gates.yaml names neither the gate nor either claiming artifact, and
    the DRAFT block says it is a draft with the ratification placeholder.
    Flipped: the block is a live top-level gate citing the gate artifact
    by path with its ratified sha256."""
    gates_text = (ROOT / "gates.yaml").read_text()
    block = _gate_b2_claiming_block()
    if not GATE_B2_CLAIMING_BLOCK_LANDED:
        assert "gate_b2_claiming" not in gates_text
        assert "claiming_gate_floors_v1" not in gates_text
        assert "claiming_publication_floor_v1" not in gates_text
        assert block["status"] == "draft_pending_referee_round"
        assert block["locked"] is False
        assert block["thresholds"]["locked"] is False
        assert block["thresholds"]["status"] == "draft_pending_referee_round"
        assert block["floor_run_sha256"] == "<FILLED AT RATIFICATION>"
        assert block["thresholds"]["floor_run_sha256"] == (
            "<FILLED AT RATIFICATION>"
        )
        assert block["lock_ceremony"]["exists"] is False
        return
    spec = yaml.safe_load(gates_text)
    assert "gate_b2_claiming" in spec["gates"]
    assert block["floor_run"] == B2C_GATE_RUN
    assert (
        block["floor_run_sha256"]
        == hashlib.sha256((ROOT / B2C_GATE_RUN).read_bytes()).hexdigest()
    )
    assert block["locked"] is True


def test_gate_b2_claiming_tolerances_bind_to_floor_strata_and_trends():
    """Every one of the 42 tolerances (34 gated + 8 report-only) ==
    quantize(K_REV * sd_knob + |trend| * h + rounding, 2, HALF_UP) with
    sd_knob = round(floor conditional_terminal_year.sd_pp, 4) and the
    trend the floor's derivations carry -- recomputed here, never read
    from the gate artifact, never typed. The block's derivations rules
    carry the same trend, horizon and unrounded value per cell."""
    floor = _b2c_floor()
    derived = _b2c_derive(floor)
    block = _gate_b2_claiming_block()
    surface = block["thresholds"]["gated_surface"]
    rules = surface["derivations"]["rules"]
    assert set(rules) == set(surface["tolerances_pp"])
    assert surface["derivations"]["floor_run"] == B2C_FLOOR_RUN
    knobs = surface["derivations"]["knobs"]
    assert knobs["k_rev"] == B2C_K_REV
    assert knobs["rounding_pp"] == B2C_ROUNDING_PP
    assert knobs["t_max_pp"] == B2C_T_MAX_PP
    assert knobs["revision_sd_terminal_pp"] == _b2c_sd_knob(floor)
    assert knobs["rounding_mode"] == "ROUND_HALF_UP"
    trends = _b2c_trends(floor)
    for cell, tol in surface["tolerances_pp"].items():
        assert derived[cell]["tolerance_pp"] == tol, cell
        rule = rules[cell]
        assert rule["trend_pp_per_year"] == trends[cell], cell
        assert rule["horizon_years"] == int(cell.split("|")[2][1:])
        assert Decimal(str(rule["unrounded_pp"])) == derived[cell]["raw"], cell
    for cell, entry in surface["report_only_tolerance_above_t_max"].items():
        assert derived[cell]["tolerance_pp"] == entry["tolerance_pp_would_be"]
        assert entry["trend_pp_per_year"] == trends[cell]
    # the gate artifact's own derivation block agrees cell for cell
    art = _b2c_gate()
    for cell in _b2c_cells():
        td = art["tolerance_derivations"][cell]
        assert td["tolerance_pp"] == derived[cell]["tolerance_pp"], cell
        assert Decimal(td["unrounded_tolerance_exact"]) == derived[cell]["raw"]
    # and the floor's DRAFT surface is byte-for-byte the same 42 values
    cap = floor["power_cap"]
    assert surface["tolerances_pp"] == cap["gate_eligible_tolerances_pp"]
    for cell, entry in cap["report_only_tolerance_above_t_max"].items():
        assert (
            surface["report_only_tolerance_above_t_max"][cell][
                "tolerance_pp_would_be"
            ]
            == entry["tolerance_pp_would_be"]
        )


def test_gate_b2_claiming_partition_34_8_recomputes():
    """gated / report-only == the partition the recomputed tolerances
    imply at T_max 3.0 (34 / 8), the six conversion cells out of scope by
    reason, and the reference values the floor's held-out conditional
    shares -- all recomputed, not hand-picked."""
    floor = _b2c_floor()
    gated, report = _b2c_partition(_b2c_derive(floor))
    assert len(gated) == 34 and len(report) == 8
    block = _gate_b2_claiming_block()
    surface = block["thresholds"]["gated_surface"]
    assert set(surface["tolerances_pp"]) == set(gated)
    assert set(surface["report_only_tolerance_above_t_max"]) == set(report)
    for entry in surface["report_only_tolerance_above_t_max"].values():
        assert entry["reason"] == "tolerance_above_t_max"
        assert entry["tolerance_pp_would_be"] > B2C_T_MAX_PP
    for tol in surface["tolerances_pp"].values():
        assert tol <= B2C_T_MAX_PP
    assert block["thresholds"]["power_cap"]["t_max_pp"] == B2C_T_MAX_PP
    art = _b2c_gate()
    part = art["gate_partition"]
    assert part["gate_eligible"] == [c for c in _b2c_cells() if c in gated]
    assert part["report_only"] == [c for c in _b2c_cells() if c in report]
    assert (part["n_gate_eligible"], part["n_report_only"]) == (34, 8)
    scope = block["thresholds"]["report_only"]["out_of_module_scope"]
    assert scope["reason"] == "conversion_flow_owned_by_di_surface"
    assert sorted(scope["cells"]) == sorted(
        f"disability_conversion|{s}|h{h}" for s in B2C_SEXES for h in (1, 2, 3)
    )
    assert set(scope["cells"]).isdisjoint(gated)
    doc = _b2c_edition()
    for cell, ref in surface["reference_values_pp"].items():
        c, s, h = cell.split("|")
        assert ref == round(_b2c_actual(doc, c, s, int(h[1:])), 4), cell
    assert set(surface["reference_values_pp"]) == set(gated)


def _b2c_rows_equal(row: dict, gated: dict, report: dict, draft_gated: dict):
    assert row["n_gate_eligible"] == len(gated)
    assert row["n_report_only_tolerance_above_t_max"] == len(report)
    assert row["gate_eligible_tolerances_pp"] == gated
    assert row["report_only_tolerance_above_t_max_pp"] == report
    assert row["cells_demoted_relative_to_draft"] == sorted(
        set(draft_gated) - set(gated)
    )
    assert row["cells_promoted_relative_to_draft"] == sorted(
        set(gated) - set(draft_gated)
    )
    assert row["partition_identical_to_draft"] is (
        set(gated) == set(draft_gated)
    )


def test_gate_b2_claiming_grammar_and_k_perturbation_fails_on_any_knob_change():
    """The twelve grammar x K rows recomputed from the floor's strata and
    trends with this module's arithmetic, equal to BOTH the gate
    artifact's alternatives and the floor's own power_cap_alternatives;
    and the perturbation: the DRAFT surface is reproduced ONLY under the
    drafted knobs -- every other grammar, K or rounding mode changes at
    least one tolerance or the partition, so an edited knob fails here."""
    floor = _b2c_floor()
    art = _b2c_gate()
    term = floor["strata"]["conditional_terminal_year"]
    sd_knob = _b2c_sd_knob(floor)
    mean_abs = term["mean_pp"]
    sd_signed = round(term["sd_signed_pp"], 4)
    max_abs = term["max_pp"]
    draft = _b2c_derive(floor)
    draft_gated, draft_report = _b2c_partition(draft)
    terms = {
        "k_times_sd_abs_DRAFT": lambda k: round(k * sd_knob, 6),
        "mean_plus_k_times_sd_abs": lambda k: round(mean_abs + k * sd_knob, 6),
        "k_times_sd_signed": lambda k: round(k * sd_signed, 6),
        "max_abs_revision_d2": lambda k: round(max_abs, 6),
    }
    gate_rows = art["alternatives"]["grammar_and_k_sweep"]["by_grammar"]
    floor_rows = floor["power_cap_alternatives"]["grammar_and_k_sweep"][
        "by_grammar"
    ]
    assert set(gate_rows) == set(terms) == set(floor_rows)
    seen_identical_to_draft = 0
    for grammar, term_of in terms.items():
        for k in (1.5, 2.0, 2.5):
            t = term_of(k)
            tols = _b2c_derive(floor, term_by_h={1: t, 2: t, 3: t})
            gated, report = _b2c_partition(tols)
            for rows in (gate_rows, floor_rows):
                row = rows[grammar]["by_k"][f"K_{k}"]
                _b2c_rows_equal(row, gated, report, draft_gated)
                assert row["age66_female_h1"]["tolerance_pp"] == (
                    gated.get(B2C_KNIFE, report.get(B2C_KNIFE))
                )
            if grammar == "k_times_sd_abs_DRAFT" and k == B2C_K_REV:
                assert gated == draft_gated and report == draft_report
                seen_identical_to_draft += 1
            else:
                # the perturbation: some tolerance or the partition moves
                assert gated != draft_gated or report != draft_report, (
                    grammar,
                    k,
                )
    assert seen_identical_to_draft == 1
    # the house grammars at K 2.0 demote exactly two cells; the max-based
    # term the same two at every K
    two = ["age65|male|h3", "age66|male|h1"]
    for grammar in ("mean_plus_k_times_sd_abs", "k_times_sd_signed"):
        row = gate_rows[grammar]["by_k"]["K_2.0"]
        assert row["cells_demoted_relative_to_draft"] == two
        assert row["n_gate_eligible"] == 32
    for k in (1.5, 2.0, 2.5):
        assert (
            gate_rows["max_abs_revision_d2"]["by_k"][f"K_{k}"][
                "cells_demoted_relative_to_draft"
            ]
            == two
        )
    # the rounding MODE perturbation: half-even moves exactly the tie cell
    even = _b2c_derive(floor, mode=ROUND_HALF_EVEN)
    moved = [
        c
        for c in _b2c_cells()
        if even[c]["tolerance_pp"] != draft[c]["tolerance_pp"]
    ]
    assert moved == [B2C_TIE]
    assert draft[B2C_TIE]["raw"] == Decimal("1.5250")
    assert (draft[B2C_TIE]["tolerance_pp"], even[B2C_TIE]["tolerance_pp"]) == (
        1.53,
        1.52,
    )
    # the block's knobs are the drafted ones and nothing else
    knobs = _gate_b2_claiming_block()["thresholds"]["gated_surface"][
        "derivations"
    ]["knobs"]
    assert (knobs["k_rev"], knobs["rounding_pp"], knobs["rounding_mode"]) == (
        2.0,
        0.05,
        "ROUND_HALF_UP",
    )


def test_gate_b2_claiming_k_by_rounding_sweep_recomputes():
    """K in {1.5, 2.0, 2.5, 3.0} x rounding in {0.01, 0.05, 0.10} under the
    drafted grammar: partition and tolerances recomputed and equal to the
    gate artifact and the floor; 34 / 8 everywhere except (2.5, 0.10) ->
    33 / 9 and K 3.0 -> 32 / 10 (the verified table)."""
    floor = _b2c_floor()
    art = _b2c_gate()
    sd_knob = _b2c_sd_knob(floor)
    draft_gated, _ = _b2c_partition(_b2c_derive(floor))
    gate_rows = art["alternatives"]["draft_grammar_k_by_rounding_sweep"][
        "rows"
    ]
    floor_rows = floor["power_cap_alternatives"][
        "draft_grammar_k_by_rounding_sweep"
    ]["rows"]
    expected = {}
    for k in (1.5, 2.0, 2.5, 3.0):
        for rounding_pp in (0.01, 0.05, 0.1):
            t = round(k * sd_knob, 6)
            tols = _b2c_derive(
                floor, term_by_h={1: t, 2: t, 3: t}, rounding_pp=rounding_pp
            )
            gated, report = _b2c_partition(tols)
            key = f"K_{k}|rounding_{rounding_pp}"
            _b2c_rows_equal(gate_rows[key], gated, report, draft_gated)
            frow = floor_rows[key]
            assert frow["n_gate_eligible"] == len(gated)
            assert frow["cells_demoted_relative_to_draft"] == sorted(
                set(draft_gated) - set(gated)
            )
            assert frow["age66_female_h1_tolerance_pp"] == gated.get(
                B2C_KNIFE, report.get(B2C_KNIFE)
            )
            expected[key] = (len(gated), len(report))
    assert expected["K_2.5|rounding_0.1"] == (33, 9)
    for rounding_pp in (0.01, 0.05, 0.1):
        assert expected[f"K_3.0|rounding_{rounding_pp}"] == (32, 10)
    assert all(
        v == (34, 8)
        for key, v in expected.items()
        if not key.startswith("K_3.0") and key != "K_2.5|rounding_0.1"
    )


def test_gate_b2_claiming_horizon_aware_pricing_recomputes():
    """h1 / h2 on the conditional settled-years sd (round 4), h3 on the
    terminal sd: 37 / 5 with exactly age62|female|h2, age62|male|h2 and
    age66|female|h2 promoted and 24 gated tolerances differing from the
    DRAFT -- recomputed and equal to the gate artifact and the floor."""
    floor = _b2c_floor()
    art = _b2c_gate()
    settled = round(floor["strata"]["conditional_settled_years"]["sd_pp"], 4)
    sd_knob = _b2c_sd_knob(floor)
    draft = _b2c_derive(floor)
    draft_gated, _ = _b2c_partition(draft)
    tols = _b2c_derive(
        floor,
        term_by_h={
            1: round(B2C_K_REV * settled, 6),
            2: round(B2C_K_REV * settled, 6),
            3: round(B2C_K_REV * sd_knob, 6),
        },
    )
    gated, report = _b2c_partition(tols)
    assert (len(gated), len(report)) == (37, 5)
    promoted = sorted(set(gated) - set(draft_gated))
    assert promoted == ["age62|female|h2", "age62|male|h2", "age66|female|h2"]
    assert set(draft_gated) <= set(gated)
    differing = sum(
        1 for c, t in gated.items() if c in draft_gated and draft_gated[c] != t
    )
    assert differing == 24
    for c in gated:
        if c.endswith("h3"):
            assert gated[c] == draft[c]["tolerance_pp"]
    row = art["alternatives"]["horizon_aware_pricing"]["result"]
    _b2c_rows_equal(row, gated, report, draft_gated)
    frow = floor["power_cap_alternatives"]["horizon_aware_pricing"]["result"]
    _b2c_rows_equal(frow, gated, report, draft_gated)
    assert art["alternatives"]["horizon_aware_pricing"]["knobs"] == {
        "k_rev": B2C_K_REV,
        "revision_sd_h1_h2_pp": settled,
        "revision_sd_h3_pp": sd_knob,
        "rounding_pp": B2C_ROUNDING_PP,
        "t_max_pp": B2C_T_MAX_PP,
    }


def test_gate_b2_claiming_rounding_mode_tie_and_knife_edge_class():
    """The 13-cell knife-edge class (unrounded tolerance within 0.002 pp
    of a 2-dp boundary; 9 gate-eligible) and the single exact tie
    recompute from this module's Decimal sums and equal the gate
    artifact, the floor and the block's disclosure."""
    floor = _b2c_floor()
    art = _b2c_gate()
    draft = _b2c_derive(floor)
    gated, _ = _b2c_partition(draft)
    band = Decimal("0.002")
    knife = {}
    for cell in _b2c_cells():
        raw = draft[cell]["raw"]
        scaled = raw / Decimal("0.01")
        frac = scaled - scaled.to_integral_value(rounding="ROUND_FLOOR")
        distance = abs(frac - Decimal("0.5")) * Decimal("0.01")
        if distance < band:
            knife[cell] = (float(distance), distance == 0, cell in gated)
    assert len(knife) == 13
    assert sum(1 for v in knife.values() if v[2]) == 9
    ties = [c for c, v in knife.items() if v[1]]
    assert ties == [B2C_TIE]
    kc = art["alternatives"]["knife_edge_class"]
    assert (kc["n_cells"], kc["n_gate_eligible"]) == (13, 9)
    assert (
        set(kc["cells"])
        == set(knife)
        == set(floor["power_cap"]["knife_edge_class"]["cells"])
    )
    for cell, (distance, tie, eligible) in knife.items():
        entry = kc["cells"][cell]
        assert entry["distance_to_boundary_pp"] == distance
        assert entry["is_exact_tie"] is tie
        assert entry["gate_eligible"] is eligible
    half_even = art["alternatives"]["rounding_mode_round_half_even"]
    assert half_even["n_cells_differing_from_draft"] == 1
    assert list(half_even["result"]["cells_differing_from_draft"]) == [B2C_TIE]
    block = _gate_b2_claiming_block()
    drafted = block["thresholds"]["power_cap"]["rounding_mode_drafted"]
    assert "ROUND_HALF_UP" in drafted and "1.5250" in drafted
    assert "13 cells, 9 gate-eligible" in " ".join(drafted.split())


def test_gate_b2_claiming_failure_sets_recompute_from_the_edition():
    """The deployed nearest-year rule and the full-window OLS, scored with
    this module's own arithmetic on the 2023 edition (pinned by the
    floor's sources): the DRAFT failure sets (6 and 20 cells, the exact
    cells and margins) and the failure sets under EVERY alternative row
    equal the gate artifact's; the deployed finding equals the floor's."""
    floor = _b2c_floor()
    art = _b2c_gate()
    doc = _b2c_edition()
    pin = floor["sources"]["edition_2023"]
    assert (
        hashlib.sha256((ROOT / B2C_EDITION).read_bytes()).hexdigest()
        == pin["sha256"]
    )
    preds = _b2c_predictors(doc)["all"]
    draft = _b2c_derive(floor)
    draft_gated, _ = _b2c_partition(draft)
    dep = _b2c_deviations(preds["deployed_v1_nearest_year"], doc, draft_gated)
    ols = _b2c_deviations(preds["ols_full_fit_window"], doc, draft_gated)
    dep_fail = _b2c_failures(dep, draft_gated)
    ols_fail = _b2c_failures(ols, draft_gated)
    assert dep_fail == [
        "age62|female|h1",
        "age62|male|h1",
        "age66|female|h1",
        "age70plus|female|h2",
        "age70plus|male|h2",
        "age70plus|male|h3",
    ]
    assert len(ols_fail) == 20
    finding = art["deployed_v1_finding"]
    assert finding["failing_cells"] == dep_fail
    assert finding["n_failed"] == 6
    assert finding["max_abs_deviation_pp"] == round(max(dep.values()), 4)
    for cell, entry in finding["per_failing_cell"].items():
        assert entry["deviation_pp"] == round(dep[cell], 4)
        assert entry["tolerance_pp"] == draft_gated[cell]
        assert entry["margin_pp"] == round(dep[cell] - draft_gated[cell], 4)
    ff = floor["deployed_v1_finding"]
    assert ff["failing_cells"] == dep_fail
    assert ff["max_abs_deviation_pp"] == finding["max_abs_deviation_pp"]
    assert ff["mean_abs_deviation_pp"] == finding["mean_abs_deviation_pp"]
    # every alternative row's two failure sets
    term = floor["strata"]["conditional_terminal_year"]
    sd_knob = _b2c_sd_knob(floor)
    settled = round(floor["strata"]["conditional_settled_years"]["sd_pp"], 4)
    variants = []
    terms = {
        "k_times_sd_abs_DRAFT": lambda k: round(k * sd_knob, 6),
        "mean_plus_k_times_sd_abs": lambda k: round(
            term["mean_pp"] + k * sd_knob, 6
        ),
        "k_times_sd_signed": lambda k: round(
            k * round(term["sd_signed_pp"], 4), 6
        ),
        "max_abs_revision_d2": lambda k: round(term["max_pp"], 6),
    }
    for grammar, term_of in terms.items():
        for k in (1.5, 2.0, 2.5):
            t = term_of(k)
            row = art["alternatives"]["grammar_and_k_sweep"]["by_grammar"][
                grammar
            ]["by_k"][f"K_{k}"]
            variants.append((row, {1: t, 2: t, 3: t}, B2C_ROUNDING_PP, None))
            frow = floor["power_cap_alternatives"]["grammar_and_k_sweep"][
                "by_grammar"
            ][grammar]["by_k"][f"K_{k}"]
            variants.append((frow, {1: t, 2: t, 3: t}, B2C_ROUNDING_PP, "f"))
    for k in (1.5, 2.0, 2.5, 3.0):
        for rounding_pp in (0.01, 0.05, 0.1):
            t = round(k * sd_knob, 6)
            key = f"K_{k}|rounding_{rounding_pp}"
            row = art["alternatives"]["draft_grammar_k_by_rounding_sweep"][
                "rows"
            ][key]
            variants.append((row, {1: t, 2: t, 3: t}, rounding_pp, None))
    variants.append(
        (
            art["alternatives"]["horizon_aware_pricing"]["result"],
            {
                1: round(B2C_K_REV * settled, 6),
                2: round(B2C_K_REV * settled, 6),
                3: round(B2C_K_REV * sd_knob, 6),
            },
            B2C_ROUNDING_PP,
            None,
        )
    )
    for row, term_by_h, rounding_pp, kind in variants:
        gated, _ = _b2c_partition(
            _b2c_derive(floor, term_by_h=term_by_h, rounding_pp=rounding_pp)
        )
        dep_v = _b2c_deviations(preds["deployed_v1_nearest_year"], doc, gated)
        assert row["deployed_v1_failing_cells"] == _b2c_failures(dep_v, gated)
        assert row["deployed_v1_n_failed"] == len(
            row["deployed_v1_failing_cells"]
        )
        if kind is None:
            ols_v = _b2c_deviations(preds["ols_full_fit_window"], doc, gated)
            assert row["ols_full_fit_window_failing_cells"] == _b2c_failures(
                ols_v, gated
            )
            knife_dev = round(ols_v.get(B2C_KNIFE, ols[B2C_KNIFE]), 4)
            assert row["age66_female_h1"][
                "ols_full_fit_window_deviation_pp"
            ] == (knife_dev)
            assert row["age66_female_h1"]["ols_full_fit_window_clears"] is (
                B2C_KNIFE in gated and knife_dev <= gated[B2C_KNIFE]
            )


def test_gate_b2_claiming_frontier_scan_recomputes():
    """C7: the rule-class frontier scan (the faithful_candidate_oc
    substitute) recomputes with this module's own seventeen rules: every
    rule's failure set and max, the four envelopes per cell (widened
    forecast class 0 failures / 1.2519 / 0.2330; packet grid 1 failure,
    age66|female|h1 at 2.3288 / 0.3150), and the OLS window sweep
    (windows 12-21 clear the knife cell; none clears all 34)."""
    floor = _b2c_floor()
    art = _b2c_gate()
    doc = _b2c_edition()
    preds = _b2c_predictors(doc)
    gated, _ = _b2c_partition(_b2c_derive(floor))
    scan = art["faithful_candidate_oc_substitute"]
    committed = floor["candidate_rules_on_the_draft_surface"]
    assert set(scan["rules"]) == set(preds["all"]) == set(committed["rules"])
    devs = {}
    for name, predict in preds["all"].items():
        d = _b2c_deviations(predict, doc, gated)
        devs[name] = d
        for block in (scan["rules"][name], committed["rules"][name]):
            assert block["failing_cells"] == _b2c_failures(d, gated), name
            assert block["n_failed"] == len(block["failing_cells"])
            assert block["max_abs_deviation_pp"] == round(max(d.values()), 4)
        rounded_mean = round(sum(round(v, 4) for v in d.values()) / len(d), 4)
        assert (
            scan["rules"][name]["mean_abs_deviation_pp_4dp_rounded_convention"]
            == rounded_mean
        )
        assert (
            committed["rules"][name]["mean_abs_deviation_pp"] == rounded_mean
        )

    def envelope(names):
        per_cell = {c: min(devs[n][c] for n in names) for c in sorted(gated)}
        return per_cell, _b2c_failures(per_cell, gated)

    forecast = sorted(preds["forecast"])
    grid = [
        "deployed_v1_nearest_year",
        "ols_full_fit_window",
        "ols_last_10",
        "ols_last_5",
        "ols_last_3",
        "damped_local_trend_w5_d0.5",
        "damped_local_trend_w5_d1.0",
        "damped_local_trend_w10_d0.5",
    ]
    eleven = grid + [
        "uniform_over_seven_categories",
        "fit_window_mean",
        "sex_pooled_nearest_year",
    ]
    cases = {
        "post_hoc_best_of_forecast_class_envelope": forecast,
        "envelope_at_the_packet_window_grid": grid,
        "envelope_over_the_v1_eleven_rules_including_degenerate": eleven,
        "envelope_over_all_rules_including_degenerate": sorted(preds["all"]),
    }
    for key, names in cases.items():
        per_cell, failures = envelope(names)
        for block in (scan[key], committed[key]):
            assert block["failing_cells"] == failures, key
            assert block["max_abs_deviation_pp"] == round(
                max(per_cell.values()), 4
            )
            assert block["mean_abs_deviation_pp"] == round(
                sum(per_cell.values()) / len(per_cell), 4
            )
            assert block["per_cell_pp"] == {
                c: round(v, 4) for c, v in per_cell.items()
            }
    assert scan["post_hoc_best_of_forecast_class_envelope"]["n_failed"] == 0
    assert scan["envelope_at_the_packet_window_grid"]["failing_cells"] == [
        B2C_KNIFE
    ]
    # the window sweep
    clearing = []
    zero = []
    for window in range(2, 23):
        d = {}
        for cell in gated:
            c, s, h = cell.split("|")
            h = int(h[1:])
            slope, intercept = _b2c_ols(
                B2C_FIT_YEARS[-window:], _b2c_series(doc, c, s)[-window:]
            )
            d[cell] = abs(
                intercept
                + slope * (B2C_FIT_YEARS[-1] + h)
                - _b2c_actual(doc, c, s, h)
            )
        failures = _b2c_failures(d, gated)
        row = scan["ols_window_sweep"]["rows"][f"ols_last_{window}"]
        assert row["n_failed"] == len(failures)
        assert row["age66_female_h1_deviation_pp"] == round(d[B2C_KNIFE], 4)
        if d[B2C_KNIFE] <= gated[B2C_KNIFE]:
            clearing.append(window)
        if not failures:
            zero.append(window)
    assert clearing == list(range(12, 22))
    assert scan["ols_window_sweep"]["windows_clearing_age66_female_h1"] == (
        clearing
    )
    assert (
        scan["ols_window_sweep"]["windows_with_zero_failures_on_all_34"]
        == (zero)
        == []
    )
    assert scan["ols_window_sweep"]["best_single_window_by_n_failed"] == (
        "ols_last_6"
    )
    assert scan["recomputed_here_and_equal_to_the_floor"] is True
    r2 = art["record_hygiene"]["R2_per_rule_mean_convention"]
    assert r2["rules_where_the_two_conventions_differ"] == ["ols_last_5"]


def test_gate_b2_claiming_mutated_builder_fails_the_binding(tmp_path):
    """SYNTHETIC: a scratch copy of the gate builder with a mutated
    tolerance rule (a doubled rounding allowance; separately, the
    quantisation mode changed inside the derivation) derives a different
    surface and its own check_against_committed RAISES against the
    verified floor -- so a builder edit that moved the rule cannot
    reproduce the committed artifact. The unmutated copy does not raise."""
    source = (ROOT / B2C_BUILDER).read_text()
    marker_a = "+ Decimal(repr(rounding_pp))"
    marker_b = "tolerance = quantize(raw, mode)"
    assert source.count(marker_a) == 1 and source.count(marker_b) == 1
    clean = tmp_path / "clean_builder.py"
    clean.write_text(source)
    module = _b2_import_from_path(clean, "b2c_clean_builder")
    floor = module.load_source_floor()
    module.check_against_committed(module.derive_tolerances(floor), floor)
    doubled = tmp_path / "mutated_rounding.py"
    doubled.write_text(
        source.replace(marker_a, "+ Decimal(repr(rounding_pp)) * 2")
    )
    mutated = _b2_import_from_path(doubled, "b2c_mutated_rounding")
    with pytest.raises(RuntimeError, match="differ from the floor"):
        mutated.check_against_committed(
            mutated.derive_tolerances(floor), floor
        )
    derived = mutated.derive_tolerances(floor)
    assert all(
        derived[c]["tolerance_pp"] != _b2c_derive(floor)[c]["tolerance_pp"]
        for c in _b2c_cells()
    )
    mode = tmp_path / "mutated_mode.py"
    mode.write_text(
        source.replace(
            marker_b, 'tolerance = quantize(raw, "ROUND_HALF_EVEN")'
        )
    )
    mutated_mode = _b2_import_from_path(mode, "b2c_mutated_mode")
    with pytest.raises(RuntimeError, match="1 cell"):
        mutated_mode.check_against_committed(
            mutated_mode.derive_tolerances(floor), floor
        )
    for name in (
        "b2c_clean_builder",
        "b2c_mutated_rounding",
        "b2c_mutated_mode",
    ):
        sys.modules.pop(name, None)


def test_gate_b2_claiming_certification_scope_and_circularity_disclosure():
    """C2 / C3 / C10 / C11 / C13 / C14: the block states the horizon
    (h in {1, 2, 3} = 2020-2022; gate_w1 deploys at delta 2), claims
    exactly the scored surface under the standing rule, excludes the six
    conversion cells by scope, discloses the loader / lookup mechanism and
    why the temporal holdout de-circularises, and says what a pass does
    NOT authorise."""
    block = _gate_b2_claiming_block()
    t = block["thresholds"]
    art = _b2c_gate()
    flat = " ".join(json.dumps(block).split())
    assert "h in {1, 2, 3}" in " ".join(
        t["certification_scope"]["horizon"].split()
    )
    assert "claim_age_delta_years 2" in flat
    assert "gates.yaml:1056, :3294, :4869" in flat
    assert (
        "description_claims_exactly_the_scored_surface"
        in t["governance"]["amendment_rules"]
    )
    assert "SINGLE-COHORT" in flat and "claiming.py:396-405" in flat
    assert "No benefit LEVEL is gated here" in " ".join(
        block["covers"].split()
    )
    assert "circularity_disclosure" in t["protocol"]
    circ = " ".join(t["protocol"]["circularity_disclosure"].split())
    assert "NEVER READ" in circ and "REPORT-ONLY" in circ
    assert "claiming.py:169-179" in " ".join(
        t["protocol"]["fit_isolation"]["rule"].split()
    )
    scope = art["certification_scope"]
    assert scope["horizon_C11"]["priced_horizons_years"] == [1, 2, 3]
    assert scope["horizon_C11"]["entitlement_years_scored"] == {
        "h1": 2020,
        "h2": 2021,
        "h3": 2022,
    }
    assert len(scope["scored_surface_C13"]["gate_eligible_cells"]) == 34
    assert len(scope["out_of_scope_C10"]["cells"]) == 6
    assert scope["out_of_scope_C10"]["reason"] == (
        "conversion_flow_owned_by_di_surface"
    )
    dna = " ".join(scope["what_a_pass_authorises_C14"]["does_not_authorise"])
    assert "re-gating gate_w1's 14 report-only" in dna
    assert "beyond h = 3" in dna
    disclosure = art["temporal_holdout_circularity_disclosure"]
    assert (
        "claiming.py:169-179"
        in disclosure["C2_is_the_holdout_a_holdout"]["mechanism"]
    )
    assert (
        "gates.yaml:3758-3761"
        in disclosure["C3_does_the_temporal_holdout_de_circularise"][
            "the_finding_it_answers"
        ]
    )
    cites = art["gates_yaml_citations"]["line_citations"]
    for line in ("1056", "3294", "4869", "4359", "3758", "4568", "565"):
        assert cites[line]["holds"] is True


def test_gate_b2_claiming_fit_isolation_names_every_channel():
    """F-A: fit_isolation names the three v2 channels AND the 2023
    edition's transcription script, whose 2020-2022 rows are re-located
    here by line (male 159-161, female 185-187 as committed); the scan hit
    no file that is not a named channel; the block's clause names every
    committed copy of the rows."""
    art = _b2c_gate()
    iso = art["fit_isolation"]
    paths = [c["path"] for c in iso["channels_carrying_the_held_out_actuals"]]
    assert paths == [
        B2C_FLOOR_RUN,
        "runs/claiming_reference_v1.json",
        B2C_EDITION,
        B2C_TRANSCRIPTION,
    ]
    assert iso["scan"]["every_hit_is_a_named_channel"] is True
    assert iso["scan"]["files_hit_not_named_as_a_channel"] == []
    assert set(iso["scan"]["files_hit"]) <= set(paths)
    script = (ROOT / B2C_TRANSCRIPTION).read_text().splitlines()
    doc = _b2c_edition()
    columns = doc["column_schema"]["raw_columns"]
    found = {}
    for sex in B2C_SEXES:
        for year in (2020, 2021, 2022):
            row = doc["data"][sex][str(year)]
            values = [
                str(year),
                f"{row['number_thousands']:,}",
                f"{row['average_age']:.1f}",
                f"{row['published_total']:.1f}",
            ] + [
                ". . ." if row["raw"][c] is None else f"{row['raw'][c]:.1f}"
                for c in columns
            ]
            needle = "\t".join(values)
            hits = [i + 1 for i, line in enumerate(script) if needle in line]
            assert len(hits) == 1, (sex, year)
            found.setdefault(sex, []).append(hits[0])
    channel = iso["channels_carrying_the_held_out_actuals"][-1]
    assert channel["line_numbers"] == {
        "male": sorted(found["male"]),
        "female": sorted(found["female"]),
    }
    assert (
        channel["pin"]["sha256"]
        == hashlib.sha256((ROOT / B2C_TRANSCRIPTION).read_bytes()).hexdigest()
    )
    clause = " ".join(
        _gate_b2_claiming_block()["thresholds"]["protocol"]["fit_isolation"][
            "channels_carrying_the_held_out_actuals"
        ].split()
    )
    for path in paths + [B2C_GATE_RUN]:
        assert path in clause, path
    assert "EVERY committed copy of its 2020-2022 rows" in clause
    assert f"{found['male'][0]}-{found['male'][-1]}" in clause
    assert f"{found['female'][0]}-{found['female'][-1]}" in clause


def test_gate_b2_claiming_draft_block_digest_placeholders_and_wording():
    """The fragment's sha256, line and byte counts recompute; the block
    parses as a draft; every placeholder the ceremony notes list is in
    the text; the forbidden words are absent; the floor's eight
    does_not_establish lines are carried verbatim; the wording audit's
    flags recompute."""
    art = _b2c_gate()
    floor = _b2c_floor()
    frag = art["draft_gates_yaml_fragment"]
    text = frag["text"]
    assert frag["text_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert frag["n_lines"] == len(text.splitlines())
    assert frag["n_bytes"] == len(text.encode("utf-8"))
    block = yaml.safe_load("gates:\n" + text)["gates"]["gate_b2_claiming"]
    assert block["status"] == "draft_pending_referee_round"
    assert block["locked"] is False
    assert block["kind"] == "external_reference_temporal_holdout"
    assert block["floor_run"] == B2C_GATE_RUN
    for marker in (
        "<RULING 1 grammar_and_k_rev>",
        "<RULING 2 horizon_pricing>",
        "<RULING 3 age66_female_h1>",
        "<RULING 4 rounding_mode>",
        "<RULING 5 d0_estimand>",
        "<RULING 6 d1_editions>",
        "<RULING S8 e1_clause>",
        "<FILLED AT RATIFICATION>",
    ):
        assert marker in text, marker
    notes = block["thresholds"]["ceremony_notes"]
    assert len(notes["placeholders_the_ratifying_round_must_fill"]) == 7
    assert "GATE_B2_CLAIMING_BLOCK_LANDED" in notes["flip_plan"]
    assert (
        "test_no_gate_b2_claiming_exists_in_gates_yaml" in notes["flip_plan"]
    )
    assert set(block["thresholds"]["open_rulings"]) == {
        str(i) for i in range(1, 9)
    }
    flat = " ".join(text.split())
    for word in ("anchored", "aligned"):
        assert not re.search(rf"\b{word}\b", flat.lower()), word
    for line in floor["does_not_establish"]:
        assert " ".join(line.split()) in flat, line[:40]
    assert (
        block["thresholds"]["floor"]["does_not_establish"]
        == floor["does_not_establish"]
    )
    audit = art["wording_audit"]
    assert audit["forbidden_words_absent_from_fragment"] is True
    assert audit["forbidden_words_absent_from_artifact"] is True
    assert audit["circularity_disclosure_present"] is True
    assert audit["all_required_phrases_present"] is True
    for item in audit["required_phrases"]:
        for phrase in item["required_phrases"]:
            assert phrase in flat, (item["item"], phrase)
    assert "UNAVAILABLE AS WRITTEN" in flat
    assert "packet correction 7" in flat


def test_gate_b2_claiming_draft_block_is_written_nowhere_else():
    """The draft block's text lives ONLY in the gate artifact: no other
    tracked file under gates.yaml / docs / scripts / tests / src / runs /
    paper contains it (pre-flip); gates.yaml is deep-equal to
    origin/master if that ref resolves."""
    art = _b2c_gate()
    text = art["draft_gates_yaml_fragment"]["text"]
    needle = json.dumps(text)[1:-1][:400]
    for path in _b2_tracked_text_files():
        if path.resolve() == (ROOT / B2C_GATE_RUN).resolve():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert text not in body, path
        assert needle not in body, path
    if not GATE_B2_CLAIMING_BLOCK_LANDED:
        master = _master_gates_mapping()
        if master is not None:
            current = yaml.safe_load((ROOT / "gates.yaml").read_text())[
                "gates"
            ]
            assert current == master
            assert "gate_b2_claiming" not in master


def test_gate_b2_claiming_open_questions_are_filed_not_ruled():
    """The eight rulings the verification's Verdict lists, in its order
    and form: 1 grammar / K_REV (four grammars x three K priced), 2 horizon
    pricing, 3 the knife edge with option (ii) UNAVAILABLE AS WRITTEN and
    the demotion consequence, 4 rounding mode, 5 the d0 estimand, 6 the
    d1 editions, 7 the sequencing constraint, 8 the E1 clause -- none
    made."""
    art = _b2c_gate()
    questions = {q["id"]: q for q in art["open_questions_for_the_ceremony"]}
    assert list(questions) == [str(i) for i in range(1, 9)]
    for qid, q in questions.items():
        assert any(
            token in q["status"]
            for token in (
                "not ruled",
                "RECORDED",
                "CLAUSE CARRIED",
                "not staged",
            )
        ), (qid, q["status"])
    q1 = questions["1"]
    assert set(q1["priced"]) == {
        "k_times_sd_abs_DRAFT",
        "mean_plus_k_times_sd_abs",
        "k_times_sd_signed",
        "max_abs_revision_d2",
    }
    assert all(len(v) == 3 for v in q1["priced"].values())
    assert (
        q1["priced"]["k_times_sd_abs_DRAFT"]["K_2.0"]["partition"] == "34 / 8"
    )
    assert q1["priced"]["mean_plus_k_times_sd_abs"]["K_2.0"]["partition"] == (
        "32 / 10"
    )
    assert (
        q1["priced"]["k_times_sd_abs_DRAFT"]["K_2.0"]["deployed_v1_n_failed"]
        == 6
    )
    assert (
        questions["2"]["priced"]["settled_sd_on_h1_h2"]["partition"]
        == "37 / 5"
    )
    assert (
        questions["2"]["priced"]["settled_sd_on_h1_h2"]["deployed_v1_n_failed"]
        == 15
    )
    q3 = questions["3"]
    assert q3["options"]["ii_structural_demotion_as_drafted"]["status"] == (
        "UNAVAILABLE AS WRITTEN"
    )
    assert (
        q3["options"]["ii_structural_demotion_as_drafted"]["basis"][
            "break_covers_age66_female_h1"
        ]
        is False
    )
    assert "from one failure to zero" in q3["consequence_of_demotion"]
    assert q3["envelopes"]["packet_window_grid"]["n_failed"] == 1
    assert q3["envelopes"]["widened_forecast_class"]["n_failed"] == 0
    assert q3["options"]["i_keep_as_teeth"]["priced"][
        "windows_clearing_this_cell"
    ] == list(range(12, 22))
    q4 = questions["4"]
    assert q4["priced"]["ROUND_HALF_EVEN"]["n_cells_differing_from_draft"] == 1
    assert (
        q4["priced"]["knife_edge_class_to_know_before_any_knob_is_fixed"][
            "n_cells"
        ]
        == 13
    )
    assert (
        "eight-category cap"
        in questions["5"]["what_a_published_choice_forces"]
    )
    assert questions["6"]["priced_interim_alternative"].startswith(
        "horizon_pricing"
    )
    q7 = questions["7"]["question"]
    assert "test_no_gate_b2_claiming_exists_in_gates_yaml" in q7
    assert "test_no_gate_b2_pia_oracle_exists_in_gates_yaml" in q7
    q8 = questions["8"]["clause"]
    assert "2026-07-05" in q8 and "ffef7b4" in q8 and "not re-executed" in q8
    assert "a03e82e5" in q8
    dnd = " ".join(art["does_not_do"])
    assert "edit gates.yaml" in dnd and "score a candidate" in dnd
    assert "make any ruling" in dnd


def test_gate_b2_claiming_flip_plan_marker_sites_and_guard_tests():
    """Every file the flip plan names exists and carries
    GATE_B2_CLAIMING_BLOCK_LANDED at the SAME value as this file; the
    live-file guard test the flip must retire exists pre-flip and is gone
    post-flip; the three master-compare sites the flip must widen exist."""
    art = _b2c_gate()
    plan = art["flip_plan"]
    assert plan["marker"] == "GATE_B2_CLAIMING_BLOCK_LANDED"
    assert (
        "tests/test_gates_derivations.py" in plan["files_carrying_the_marker"]
    )
    pattern = re.compile(
        r"^GATE_B2_CLAIMING_BLOCK_LANDED = (True|False)$", re.M
    )
    for rel in plan["files_carrying_the_marker"]:
        path = ROOT / rel
        assert path.is_file(), rel
        found = pattern.findall(path.read_text())
        assert len(found) == 1, rel
        assert (found[0] == "True") is GATE_B2_CLAIMING_BLOCK_LANDED, rel
    guard = (ROOT / "tests" / "test_claiming_publication_floor.py").read_text()
    defined = "def test_no_gate_b2_claiming_exists_in_gates_yaml" in guard
    assert defined is (not GATE_B2_CLAIMING_BLOCK_LANDED)
    assert plan["live_file_tests_the_flip_retires"][0].endswith(
        "test_no_gate_b2_claiming_exists_in_gates_yaml"
    )
    for site in plan["master_compare_sites_that_must_admit_the_new_key"]:
        rel = site.split("::")[0].split(" ")[0]
        assert (ROOT / rel).is_file(), site
    this = (ROOT / "tests" / "test_gates_derivations.py").read_text()
    assert "test_gate_m4_flip_leaves_locked_siblings_byte_identical" in this


# --------------------------------------------------------------------------
# gate_b2_pia_oracle (issue #74 component SF) THRESHOLD BINDING -- DRAFT,
# pre-lock, the same shape: the block is carried as a string in
# runs/pia_gate_partition_v1.json; the per-rule E1 / E2 / E3 partition is
# recomputed here from the VERIFIED coverage record
# runs/pia_rule_coverage_v1.json's status labels under this module's OWN
# mapping (the definition's letter), and under every filed alternative.
# --------------------------------------------------------------------------
B2P_COVERAGE_RUN = "runs/pia_rule_coverage_v1.json"
B2P_COVERAGE_COMMITTED = (
    75_382,
    "7517d27a78eaa85ec4a12f1dfe9663e535c4ea54ca3d6edf5648ea075dd6d25d",
)
B2P_GATE_RUN = "runs/pia_gate_partition_v1.json"
B2P_GATE_COMMITTED = (
    169_031,
    "d14b7192425cc1f91e0e853fd48bca5896f89b1ddb1d2f20cccec24f984735aa",
)
B2P_BUILDER = "scripts/build_pia_gate_partition_v1.py"
#: This module's own mapping -- the definition's letter.
B2P_E1 = {
    "satisfied": True,
    "policyengine_us_only": True,
    "degenerate": False,
    "unsatisfiable_today": False,
}
B2P_E2 = {
    "satisfied": True,
    "satisfied_with_a_constant_override": False,
    "weak": False,
    "partial": False,
    "implied": False,
    "absent": False,
}
B2P_E3 = {
    "all_branches_exercised": True,
    "exhaustive": True,
    "both_branches_reached": True,
    "partial": False,
    "partial_and_one_branch_unexercised": False,
    "partial_with_a_named_simplification": False,
    "branch_unexercised": False,
    "unexercised": False,
    "unit_test_only": False,
}
B2P_AUXILIARY = (
    "R11_402q1_spousal_early_reduction",
    "R12_402bc_402k3_spouse_benefit",
    "R13_402q_survivor_reduction_ramp",
    "R14_402ef_widow_riblim_drc_dual",
    "R15_402e3_f4_remarriage_protection",
)
GATE_B2_PIA_ORACLE_BLOCK_LANDED = False


def _b2p_coverage() -> dict:
    return json.loads((ROOT / B2P_COVERAGE_RUN).read_text())


def _b2p_gate() -> dict:
    return json.loads((ROOT / B2P_GATE_RUN).read_text())


def _gate_b2_pia_oracle_block() -> dict:
    if GATE_B2_PIA_ORACLE_BLOCK_LANDED:
        gates = yaml.safe_load((ROOT / "gates.yaml").read_text())
        return gates["gates"]["gate_b2_pia_oracle"]
    text = _b2p_gate()["draft_gates_yaml_fragment"]["text"]
    return yaml.safe_load("gates:\n" + text)["gates"]["gate_b2_pia_oracle"]


def _b2p_partition(coverage: dict, e1, e2, e3, waive_label=None) -> dict:
    """This module's own partition from the coverage record's labels."""
    out = {"all_three": [], "strict_subset": {}, "none": [], "per_rule": {}}
    for rule in coverage["rule_inventory"]:
        labels = (
            rule["e1"]["status"],
            rule["e2"]["status"],
            rule["e3"]["status"],
        )
        waived = waive_label is not None and labels[0] == waive_label
        holds = (
            True if waived else e1[labels[0]],
            e2[labels[1]],
            e3[labels[2]],
        )
        failing = [
            n for n, h in zip(("E1", "E2", "E3"), holds, strict=True) if not h
        ]
        if not failing:
            out["all_three"].append(rule["id"])
            cls = "all_three"
        elif len(failing) < 3:
            out["strict_subset"][rule["id"]] = failing
            cls = "strict_subset"
        else:
            out["none"].append(rule["id"])
            cls = "none"
        out["per_rule"][rule["id"]] = (cls, failing)
    return out


def test_gate_b2_pia_oracle_coverage_bytes_are_pinned_and_read_by_path():
    path = ROOT / B2P_COVERAGE_RUN
    assert path.stat().st_size == B2P_COVERAGE_COMMITTED[0]
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == B2P_COVERAGE_COMMITTED[1]
    )
    art = _b2p_gate()
    src = art["source_coverage"]
    assert src["path"] == B2P_COVERAGE_RUN
    assert (src["size_bytes"], src["sha256"]) == B2P_COVERAGE_COMMITTED
    assert art["schema_version"] == "pia_gate_partition.v1"
    assert art["reported_not_gated"] is True
    block = _gate_b2_pia_oracle_block()
    assert block["derived_from_coverage"] == B2P_COVERAGE_RUN
    assert block["derived_from_coverage_sha256"] == B2P_COVERAGE_COMMITTED[1]
    assert block["thresholds"]["coverage_run_sha256"] == (
        B2P_COVERAGE_COMMITTED[1]
    )
    # the coverage record's own source pins still hold on disk
    for rel, sha in src["its_source_pins_rechecked_on_disk"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == sha


def test_gate_b2_pia_oracle_gate_artifact_bytes_are_pinned():
    path = ROOT / B2P_GATE_RUN
    assert path.stat().st_size == B2P_GATE_COMMITTED[0]
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest() == B2P_GATE_COMMITTED[1]
    )
    art = _b2p_gate()
    assert (
        art["revision_pins"]["gate_builder_sha256"]
        == hashlib.sha256((ROOT / B2P_BUILDER).read_bytes()).hexdigest()
    )


def test_gate_b2_pia_oracle_pre_lock_guard_or_live_block():
    gates_text = (ROOT / "gates.yaml").read_text()
    block = _gate_b2_pia_oracle_block()
    if not GATE_B2_PIA_ORACLE_BLOCK_LANDED:
        assert "gate_b2_pia_oracle" not in gates_text
        assert "pia_gate_partition_v1" not in gates_text
        assert "pia_rule_coverage_v1" not in gates_text
        assert block["status"] == "draft_pending_referee_round"
        assert block["locked"] is False
        assert block["thresholds"]["locked"] is False
        assert block["floor_run_sha256"] == "<FILLED AT RATIFICATION>"
        assert block["lock_ceremony"]["exists"] is False
        return
    spec = yaml.safe_load(gates_text)
    assert "gate_b2_pia_oracle" in spec["gates"]
    assert block["floor_run"] == B2P_GATE_RUN
    assert (
        block["floor_run_sha256"]
        == hashlib.sha256((ROOT / B2P_GATE_RUN).read_bytes()).hexdigest()
    )
    assert block["locked"] is True


def test_gate_b2_pia_oracle_partition_recomputes_from_coverage_labels():
    """Under this module's own mapping (the definition's letter) exactly
    R10 holds E1+E2+E3; the strict-subset rules and their failing
    conditions, and the five rules holding none, equal the gate
    artifact's strict partition and the block's; every label the record
    uses is in the mapping."""
    coverage = _b2p_coverage()
    art = _b2p_gate()
    mine = _b2p_partition(coverage, B2P_E1, B2P_E2, B2P_E3)
    strict = art["partitions"]["strict"]
    assert (
        mine["all_three"] == strict["all_three"] == ["R10_416l_fra_schedule"]
    )
    assert mine["strict_subset"] == strict["strict_subset"]
    assert mine["none"] == strict["none"]
    assert set(mine["none"]) == {
        "R3_415b2B_computation_year_count",
        "R12_402bc_402k3_spouse_benefit",
        "R13_402q_survivor_reduction_ramp",
        "R14_402ef_widow_riblim_drc_dual",
        "R15_402e3_f4_remarriage_protection",
    }
    assert len(mine["strict_subset"]) == 10
    assert strict["mapping"]["e1"] == B2P_E1
    assert strict["mapping"]["e2"] == B2P_E2
    assert strict["mapping"]["e3"] == B2P_E3
    used = {
        c: {r[c]["status"] for r in coverage["rule_inventory"]}
        for c in ("e1", "e2", "e3")
    }
    assert used["e1"] <= set(B2P_E1)
    assert used["e2"] <= set(B2P_E2)
    assert used["e3"] <= set(B2P_E3)
    block = _gate_b2_pia_oracle_block()
    part = block["thresholds"]["partition"]["strict_reading"]
    assert part["all_three"] == mine["all_three"]
    assert part["none"] == mine["none"]
    assert {k: v for k, v in part["strict_subset"].items()} == mine[
        "strict_subset"
    ]
    inventory = block["thresholds"]["rule_inventory"]
    assert len(inventory) == 16
    for rule in coverage["rule_inventory"]:
        entry = inventory[rule["id"]]
        assert entry["e1"] == rule["e1"]["status"]
        assert entry["e2"] == rule["e2"]["status"]
        assert entry["e3"] == rule["e3"]["status"]
        cls, failing = mine["per_rule"][rule["id"]]
        assert entry["strict_reading"]["class"] == cls
        assert entry["strict_reading"]["failing"] == failing
        assert entry["packet_proposed_verdict"] == (
            rule["packet_proposed_verdict"]["verdict"]
        )
    gp = art["gate_partition"]
    assert (gp["n_all_three"], gp["n_strict_subset"], gp["n_none"]) == (
        1,
        10,
        5,
    )


def test_gate_b2_pia_oracle_alternative_readings_recompute():
    """Every filed alternative reading recomputes: Axiom-only E1 moves R8
    / R9 / R16 out of E1; the P6 waiver moves the five auxiliary rules'
    labels but none into all_three; the P9 override moves R13's label
    only; the all-three set is R10 under every reading."""
    coverage = _b2p_coverage()
    art = _b2p_gate()
    alts = art["partitions"]["alternatives"]
    axiom = _b2p_partition(
        coverage, {**B2P_E1, "policyengine_us_only": False}, B2P_E2, B2P_E3
    )
    assert axiom["all_three"] == alts["axiom_only_e1"]["all_three"]
    assert axiom["strict_subset"] == alts["axiom_only_e1"]["strict_subset"]
    assert set(alts["axiom_only_e1"]["moves_vs_strict"]) == {
        "R8_402q_worker_early_reduction",
        "R9_402w_delayed_retirement_credit",
        "R16_age62_composition",
    }
    p6 = _b2p_partition(
        coverage, B2P_E1, B2P_E2, B2P_E3, waive_label="unsatisfiable_today"
    )
    assert p6["all_three"] == alts["p6_e1_waiver_for_r11_r15"]["all_three"]
    assert (
        p6["strict_subset"]
        == alts["p6_e1_waiver_for_r11_r15"]["strict_subset"]
    )
    assert p6["none"] == alts["p6_e1_waiver_for_r11_r15"]["none"]
    assert set(alts["p6_e1_waiver_for_r11_r15"]["moves_vs_strict"]) == set(
        B2P_AUXILIARY
    )
    p9 = _b2p_partition(
        coverage,
        B2P_E1,
        {**B2P_E2, "satisfied_with_a_constant_override": True},
        B2P_E3,
    )
    assert (
        p9["strict_subset"]
        == alts["p9_constant_override_counts_as_e2"]["strict_subset"]
    )
    assert list(
        alts["p9_constant_override_counts_as_e2"]["moves_vs_strict"]
    ) == ["R13_402q_survivor_reduction_ramp"]
    inv = art["partitions"]["invariant_under_every_reading"]
    assert inv["rules_holding_all_three_under_every_variant"] == [
        "R10_416l_fra_schedule"
    ]
    # only R3 holds none under EVERY reading: the P6 waiver lifts R15's E1
    assert inv["rules_holding_none_under_every_variant"] == [
        "R3_415b2B_computation_year_count"
    ]
    assert "R15_402e3_f4_remarriage_protection" in p6["strict_subset"]
    packet = alts["packet_proposed_verdicts"]
    assert packet["rules_holding_all_three_under_the_strict_reading"] == [
        "R10_416l_fra_schedule"
    ]
    assert (
        "R7_415g_dime_floor"
        in packet[
            "packet_qualified_forms_that_the_strict_reading_does_not_award"
        ]
    )


def test_gate_b2_pia_oracle_precision_and_e1_clause():
    """P11: to the cent (0.005 dollars), the four observed deviations
    equal the coverage record's and the largest is within the bound. S8:
    the E1 clause names the commit date and engine revision for the Axiom
    half and records the policyengine-us half as re-executed by the
    verification."""
    coverage = _b2p_coverage()
    art = _b2p_gate()
    p = art["precision_claim_P11"]
    ce = coverage["evidence_inventory"]["cross_engine"]
    assert (
        p["agreement_tolerance_dollars"]
        == ce["agreement_tolerance_dollars"]
        == 0.005
    )
    assert (
        p["observed"]
        == coverage["computes_exactly_definition_proposal"][
            "precision_disclosure"
        ]
    )
    assert p["largest_observed_is_within_the_bound"] is True
    assert p["largest_observed_dollar_deviation"] <= 0.005
    assert "TO THE CENT" in p["claim"] and "NOT bit-exact" in p["claim"]
    clause = art["e1_clause_S8"]
    assert clause["clause"].startswith(
        "E1 as committed 2026-07-05 at engine ffef7b4"
    )
    assert "not re-executed" in clause["clause"]
    assert (
        clause["axiom_half"]["engine_revision"]
        == ce["engine_revision"]
        == "ffef7b4"
    )
    assert clause["axiom_half"]["re_executed_in_this_ceremony"] is False
    assert clause["axiom_half"]["rules"] == [
        r["id"]
        for r in coverage["rule_inventory"]
        if r["cross_engine"]["n_cases"] > 0
    ]
    pe = clause["policyengine_us_half"]
    assert pe["re_executed_in_this_ceremony"] is True
    assert pe["cases"] == 12 and pe["policyengine_us_checkout"] == "a03e82e5"
    assert pe["test"].endswith(
        "test_pe_us_simulation_matches_oracle_foundation_live"
    )
    block = _gate_b2_pia_oracle_block()
    carried = " ".join(block["thresholds"]["e1_clause_as_carried"].split())
    assert "E1 as committed 2026-07-05 at engine ffef7b4" in carried
    assert "a03e82e5" in carried and "PASSED" in carried
    assert block["thresholds"]["e1_clause"] == "<RULING S8 e1_clause>"


def test_gate_b2_pia_oracle_worked_example_classification():
    """P7: seven published-percentage rows and three arithmetic /
    branch-selection rows, the packet's split as the coverage record
    carries it; the ratios recompute; the per-rule E2 support follows."""
    coverage = _b2p_coverage()
    art = _b2p_gate()
    ex = art["worked_examples_classification_P7"]
    assert (
        ex["n_published_percentage"],
        ex["n_arithmetic_or_branch_selection"],
    ) == (
        7,
        3,
    )
    assert ex["all_agree_to_the_cent"] is True
    rows = coverage["evidence_inventory"]["ssa_worked_examples"]["examples"]
    cls = coverage["evidence_inventory"]["ssa_worked_examples"][
        "anchor_classification"
    ]
    for row in rows:
        entry = ex["examples"][row["name"]]
        assert entry["expected_over_base_pia"] == row["expected_over_base_pia"]
        assert entry["expected_over_base_pia"] == pytest.approx(
            row["expected"] / row["base_pia"]
        )
        expected_label = (
            "published_percentage"
            if row["name"] in cls["packet_published_percentage_anchors"]
            else "arithmetic_or_branch_selection"
        )
        assert entry["packet_classification"] == expected_label
    assert ex["by_rule"]["R14_402ef_widow_riblim_drc_dual"][
        "arithmetic_or_branch_selection"
    ] == ["rib_lim_deceased_actual_higher", "drc_pass_through"]
    assert ex["by_rule"]["R12_402bc_402k3_spouse_benefit"][
        "arithmetic_or_branch_selection"
    ] == ["spouse_dual_entitlement_excess"]
    assert (
        ex["by_rule"]["R11_402q1_spousal_early_reduction"][
            "arithmetic_or_branch_selection"
        ]
        == []
    )


def test_gate_b2_pia_oracle_family_maximum_and_frozen_scope_by_ast():
    """P10: the household consumer is CoupleBenefit.total, re-derived by
    ast here (class, property and function spans) and equal to the gate
    artifact and the coverage record; no plural name is defined. P15: the
    frozen-scope sentence is in the module and carried in the block."""
    import ast as _ast

    art = _b2p_gate()
    coverage = _b2p_coverage()
    tree = _ast.parse(
        (ROOT / "src/populace_dynamics/household.py").read_text()
    )
    spans = {}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ClassDef) and node.name == "CoupleBenefit":
            spans["class"] = [node.lineno, node.end_lineno]
            for item in node.body:
                if isinstance(item, _ast.FunctionDef) and item.name == "total":
                    spans["total"] = [item.lineno, item.end_lineno]
        if (
            isinstance(node, _ast.FunctionDef)
            and node.name == "couple_benefit"
        ):
            spans["function"] = [node.lineno, node.end_lineno]
        if isinstance(node, (_ast.ClassDef, _ast.FunctionDef)):
            assert node.name not in ("CoupleBenefits", "couple_benefits")
    fm = art["family_maximum_P10"]["consumer"]
    assert fm["class_lines"] == spans["class"]
    assert fm["total_property_lines"] == spans["total"]
    assert fm["couple_benefit_function_lines"] == spans["function"]
    cs = coverage["sources"]["consumer_symbols"]
    assert spans["class"] == [
        cs["class"]["first_line"],
        cs["class"]["last_line"],
    ]
    assert fm["plural_name_defined_anywhere_in_the_module"] is False
    text = (ROOT / "src/populace_dynamics/ss/__init__.py").read_text()
    sentence = art["frozen_scope_P15"]["key_sentence"]
    assert sentence in " ".join(text.split())
    block = _gate_b2_pia_oracle_block()
    flat = " ".join(json.dumps(block).split())
    assert "CoupleBenefit.total" in flat
    assert f"household.py:{spans['class'][0]}-{spans['class'][1]}" in flat
    assert sentence in flat
    assert "KNOWN UNCAUGHT class" in flat


def test_gate_b2_pia_oracle_draft_block_digest_placeholders_and_wording():
    """The fragment's digest and counts recompute; it parses as a draft;
    the placeholders are present; the definition of "computes exactly" is
    stated (P2); what a pass does not authorise is stated (P14); the
    forbidden words are absent; the coverage record's seven
    does_not_establish lines are carried verbatim."""
    art = _b2p_gate()
    coverage = _b2p_coverage()
    frag = art["draft_gates_yaml_fragment"]
    text = frag["text"]
    assert frag["text_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert frag["n_lines"] == len(text.splitlines())
    assert frag["n_bytes"] == len(text.encode("utf-8"))
    block = yaml.safe_load("gates:\n" + text)["gates"]["gate_b2_pia_oracle"]
    assert block["status"] == "draft_pending_referee_round"
    assert block["locked"] is False
    assert block["kind"] == "exact_agreement_per_rule"
    assert block["holdout_basis"] == []
    for marker in (
        "<RULING P1 gate_kind>",
        "<RULING P6 e1_waiver>",
        "<RULING P8 case_set>",
        "<RULING P9 survivor_period>",
        "<RULING P13 granularity>",
        "<RULING S8 e1_clause>",
        "<FILLED AT RATIFICATION>",
    ):
        assert marker in text, marker
    notes = block["thresholds"]["ceremony_notes"]
    assert len(notes["placeholders_the_ratifying_round_must_fill"]) == 7
    assert "GATE_B2_PIA_ORACLE_BLOCK_LANDED" in notes["flip_plan"]
    assert (
        "test_no_gate_b2_pia_oracle_exists_in_gates_yaml" in notes["flip_plan"]
    )
    assert set(block["thresholds"]["open_rulings"]) == {
        "P1",
        "P6",
        "P8",
        "P9",
        "P13",
        "S7",
        "S8",
    }
    flat = " ".join(text.split())
    for word in ("anchored", "aligned"):
        assert not re.search(rf"\b{word}\b", flat.lower()), word
    statistic = " ".join(block["thresholds"]["statistic"].split())
    for phrase in (
        "E1 INDEPENDENT RE-EXECUTION",
        "E2 EXTERNAL ANCHOR",
        "E3 EXERCISED BRANCHES AND BOUNDARIES",
        "X1 NAMED NON-COVERAGE",
        "X2 NAMED CONSTANTS",
        "TO THE CENT",
        "NOT bit-exactness",
    ):
        assert phrase in statistic, phrase
    dna = block["thresholds"]["certification_scope"]["does_not_authorise"]
    assert len(dna) >= 7
    assert any("household benefit TOTAL" in line for line in dna)
    assert any("aime()" in line for line in dna)
    assert any("gate_2c" in line for line in dna)
    for line in coverage["does_not_establish"]:
        assert " ".join(line.split()) in flat, line[:40]
    assert (
        block["thresholds"]["coverage_record_does_not_establish"]
        == coverage["does_not_establish"]
    )
    audit = art["wording_audit"]
    assert audit["forbidden_words_absent_from_fragment"] is True
    assert audit["forbidden_words_absent_from_artifact"] is True
    assert audit["all_required_phrases_present"] is True
    assert "gates.yaml:1056, :3294, :4869" in flat


def test_gate_b2_pia_oracle_draft_block_is_written_nowhere_else():
    art = _b2p_gate()
    text = art["draft_gates_yaml_fragment"]["text"]
    needle = json.dumps(text)[1:-1][:400]
    for path in _b2_tracked_text_files():
        if path.resolve() == (ROOT / B2P_GATE_RUN).resolve():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert text not in body, path
        assert needle not in body, path
    if not GATE_B2_PIA_ORACLE_BLOCK_LANDED:
        master = _master_gates_mapping()
        if master is not None:
            current = yaml.safe_load((ROOT / "gates.yaml").read_text())[
                "gates"
            ]
            assert current == master
            assert "gate_b2_pia_oracle" not in master


def test_gate_b2_pia_oracle_open_questions_are_filed_not_ruled():
    """P1, P6, P8, P9, P13 filed and priced from the coverage record as
    v2 leaves it; S7 the sequencing constraint; S8 the E1 clause; none
    made."""
    art = _b2p_gate()
    questions = {q["id"]: q for q in art["open_questions_for_the_ceremony"]}
    assert list(questions) == ["P1", "P6", "P8", "P9", "P13", "S7", "S8"]
    for qid, q in questions.items():
        assert any(
            token in q["status"]
            for token in ("not ruled", "RECORDED", "CLAUSE CARRIED")
        ), (qid, q["status"])
    p1 = questions["P1"]
    assert p1["options"]["a_accept_the_gate_kind"]["priced"][
        "rules_awarded_under_the_strict_reading"
    ] == ["R10_416l_fra_schedule"]
    assert "gates.yaml:917" in p1["the_one_outcome_the_standing_rule_forbids"]
    p6 = questions["P6"]
    assert p6["options"]["a_per_rule_e1_waiver"]["partition"]["all_three"] == [
        "R10_416l_fra_schedule"
    ]
    assert p6["options"]["b_split_the_gate_and_hold_the_auxiliary_half"][
        "held_rules"
    ] == list(B2P_AUXILIARY)
    p8 = questions["P8"]
    assert (
        p8["facts"]["couple_grid"][
            "n_rows_with_both_spouses_drawing_an_excess"
        ]
        == 0
    )
    assert p8["facts"]["cross_engine"]["eligibility_years"] == [2020, 2026]
    assert (
        "R3_would_be_SEPARATED_not_satisfied"
        in p8["priced"]["what_a_wider_set_could_move"]
    )
    p9 = questions["P9"]
    assert p9["options"]["a_constant_override_does_not_satisfy_e2"][
        "R13_class"
    ] == ("none")
    assert (
        p9["options"]["b_override_counts_as_e2_with_the_domain_named"][
            "R13_class"
        ]
        == "strict_subset"
    )
    assert "FORBIDDEN" in p9["options"]["c_add_a_survivor_fra_schedule"]
    assert questions["P13"]["facts"]["n_rules"] == 16
    assert (
        "test_no_gate_b2_pia_oracle_exists_in_gates_yaml"
        in questions["S7"]["question"]
    )
    assert "2026-07-05" in questions["S8"]["clause"]


def test_gate_b2_pia_oracle_flip_plan_marker_sites_and_guard_tests():
    art = _b2p_gate()
    plan = art["flip_plan"]
    assert plan["marker"] == "GATE_B2_PIA_ORACLE_BLOCK_LANDED"
    pattern = re.compile(
        r"^GATE_B2_PIA_ORACLE_BLOCK_LANDED = (True|False)$", re.M
    )
    for rel in plan["files_carrying_the_marker"]:
        path = ROOT / rel
        assert path.is_file(), rel
        found = pattern.findall(path.read_text())
        assert len(found) == 1, rel
        assert (found[0] == "True") is GATE_B2_PIA_ORACLE_BLOCK_LANDED, rel
    guard = (ROOT / "tests" / "test_pia_rule_coverage.py").read_text()
    defined = "def test_no_gate_b2_pia_oracle_exists_in_gates_yaml" in guard
    assert defined is (not GATE_B2_PIA_ORACLE_BLOCK_LANDED)
    assert "test_computes_exactly_citation_is_blob_pinned" in guard
    for site in plan["master_compare_sites_that_must_admit_the_new_key"]:
        rel = site.split("::")[0].split(" ")[0]
        assert (ROOT / rel).is_file(), site


def test_gate_b2_pia_oracle_mutated_builder_fails_the_binding(tmp_path):
    """SYNTHETIC: a scratch copy of the PIA gate builder whose strict E1
    mapping no longer counts policyengine_us_only derives a DIFFERENT
    strict partition (R8 / R9 / R16 move), and one whose E3 mapping counts
    'partial' awards rules the committed partition does not -- so an
    edited mapping cannot reproduce the committed artifact."""
    source = (ROOT / B2P_BUILDER).read_text()
    coverage = _b2p_coverage()
    committed = _b2p_gate()["partitions"]["strict"]
    clean = tmp_path / "clean_pia_builder.py"
    clean.write_text(source)
    module = _b2_import_from_path(clean, "b2p_clean_builder")
    strict = module.partitions(coverage)["strict"]
    assert strict["all_three"] == committed["all_three"]
    assert strict["strict_subset"] == committed["strict_subset"]
    marker = '    "policyengine_us_only": True,\n    "degenerate": False,\n    "unsatisfiable_today": False,\n}\nE1_AXIOM_ONLY'
    assert source.count(marker) == 1
    mutated = tmp_path / "mutated_e1.py"
    mutated.write_text(
        source.replace(
            marker,
            '    "policyengine_us_only": False,\n    "degenerate": False,\n    "unsatisfiable_today": False,\n}\nE1_AXIOM_ONLY',
        )
    )
    m1 = _b2_import_from_path(mutated, "b2p_mutated_e1")
    s1 = m1.partitions(coverage)["strict"]
    assert s1["strict_subset"] != committed["strict_subset"]
    moved = {
        r
        for r in committed["per_rule"]
        if s1["per_rule"][r]["failing_conditions"]
        != committed["per_rule"][r]["failing_conditions"]
    }
    assert moved == {
        "R8_402q_worker_early_reduction",
        "R9_402w_delayed_retirement_credit",
        "R16_age62_composition",
    }
    marker3 = '    "both_branches_reached": True,\n    "partial": False,'
    assert source.count(marker3) == 1
    mutated3 = tmp_path / "mutated_e3.py"
    mutated3.write_text(
        source.replace(
            marker3, '    "both_branches_reached": True,\n    "partial": True,'
        )
    )
    m3 = _b2_import_from_path(mutated3, "b2p_mutated_e3")
    s3 = m3.partitions(coverage)["strict"]
    assert set(s3["all_three"]) > set(committed["all_three"])
    for name in ("b2p_clean_builder", "b2p_mutated_e1", "b2p_mutated_e3"):
        sys.modules.pop(name, None)


def test_gate_b2_both_blocks_record_the_sequencing_constraint():
    """Ruling 7 / S7: both artifacts' flip plans name BOTH live-file guard
    tests; both tests exist today; gates.yaml carries neither gate name
    nor any of the four artifact names (pre-flip)."""
    for art in (_b2c_gate(), _b2p_gate()):
        retired = " ".join(
            art["flip_plan"]["live_file_tests_the_flip_retires"]
        )
        assert "test_no_gate_b2_claiming_exists_in_gates_yaml" in retired
        assert "test_no_gate_b2_pia_oracle_exists_in_gates_yaml" in retired
    assert (
        "def test_no_gate_b2_claiming_exists_in_gates_yaml"
        in (ROOT / "tests" / "test_claiming_publication_floor.py").read_text()
    )
    assert (
        "def test_no_gate_b2_pia_oracle_exists_in_gates_yaml"
        in (ROOT / "tests" / "test_pia_rule_coverage.py").read_text()
    )
    if not (GATE_B2_CLAIMING_BLOCK_LANDED or GATE_B2_PIA_ORACLE_BLOCK_LANDED):
        text = (ROOT / "gates.yaml").read_text()
        for name in (
            "gate_b2_claiming",
            "gate_b2_pia_oracle",
            "claiming_gate_floors_v1",
            "pia_gate_partition_v1",
            "claiming_publication_floor_v1",
            "pia_rule_coverage_v1",
        ):
            assert name not in text, name
