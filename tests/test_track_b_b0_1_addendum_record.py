"""Pin the B0.1 addendum to its frozen protocol, constants and figures.

The addendum (docs/design/track_b_b0_1_addendum.md) freezes elements 5-9
for B2 and carries protocol v2, which was committed and pushed before any
planning value was computed. These tests read the addendum, the addendum
scripts, the frozen count record and the two records the run and the
power script wrote. They read no PSID file, no selection ledger and no
file on the audit's Q6 exclusion list.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_addendum_power as power  # noqa: E402
import track_b_b0_1_addendum_tables as tables  # noqa: E402
import track_b_b0_1_planning_values as pv  # noqa: E402

ADDENDUM = ROOT / "docs" / "design" / "track_b_b0_1_addendum.md"
GATE_LEAK = ROOT / "docs" / "design" / "track_b_b0_1_gate_leak_check.txt"

#: SHA-256 of the protocol-v2 block at the freeze commit, markers included.
PROTOCOL_V2_SHA256 = (
    "2a1681cdb3b6e28f30a8c1a319895b95f25c2fb27a175c50ded8a196d8488fe9"
)


@pytest.fixture(scope="module")
def text():
    return ADDENDUM.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def prose(text):
    return " ".join(text.split())


@pytest.fixture(scope="module")
def protocol(text):
    start = text.index(pv.PROTOCOL_BEGIN)
    stop = text.index(pv.PROTOCOL_END) + len(pv.PROTOCOL_END)
    return " ".join(text[start:stop].split())


def test_protocol_block_is_byte_identical_to_the_freeze(text):
    digest = pv.protocol_block_sha256(text)
    assert digest == PROTOCOL_V2_SHA256 == pv.PROTOCOL_V2_SHA256
    start = text.index(pv.PROTOCOL_BEGIN)
    stop = text.index(pv.PROTOCOL_END) + len(pv.PROTOCOL_END)
    assert digest == hashlib.sha256(text[start:stop].encode()).hexdigest()
    assert text.rstrip().endswith(pv.PROTOCOL_END)


def test_protocol_constants_equal_the_script_s(protocol):
    assert pv.PSEUDO_ORIGIN == 2006 and "b = 2006" in protocol
    assert f"seed={pv.FIT_SEED}, boundary_year={pv.PSEUDO_ORIGIN}" in protocol
    assert pv.DRAW_SEEDS == tuple(range(6200, 6220)) and pv.K == 20
    assert "| Fit seed; draw seeds | 5200; 6200-6219 |" in protocol
    assert (pv.B_F, pv.B_D) == (4000, 1000)
    assert "| Arm F, arm D replicates | 4,000; 1,000 |" in protocol
    assert (pv.B_R_MIN, pv.B_R_MAX) == (60, 200)
    assert "at most 200, at least 60 |" in protocol
    assert pv.ARM_R_BUDGET_SECONDS == 36 * 3600
    assert "| Arm R budget | 36 hours from arm R's first start" in protocol
    assert f"| Root seed | {pv.BOOTSTRAP_ROOT_SEED} |" in protocol
    assert pv.N_CI_RESAMPLES == 2000 and pv.CI_LEVELS == (0.05, 0.95)
    assert pv.UCL_LEVEL == 0.975
    assert (
        "| Limit resamples; percentiles | 2,000; 5th and 95th, and 97.5th"
        in protocol
    )
    assert pv.MIN_DEFINED_SHARE_F == 0.99
    assert "| Defined share needed in arm F | 0.99 |" in protocol
    assert pv.MAX_FAILED_SHARE == 0.10
    assert "above 0.10 of an arm |" in protocol
    assert pv.DESIGN_RATIO_LIMIT == 1.10
    assert "| Design-ratio limit | 1.10 |" in protocol
    assert pv.TRUTH_AGREEMENT_RTOL == 1e-9
    assert "| Truth-agreement tolerance | 1e-9 relative |" in protocol
    assert pv.ID_SCALE == 1000
    assert "| Identifier scale for copies | 1000 |" in protocol
    assert pv.REFIT_SCHEME == "half"
    assert "Arm R: refit, household half-samples, 60 to 200" in protocol
    assert max(pv.COLLECTION_WAVES) == 2011
    assert "collection waves 1969-2011" in protocol
    assert pv.B2_EXPECTED == {
        "fit_input_rows": 321_500,
        "n_full_anchor": 23_134,
        "n_domain": 13_542,
    }
    assert (
        "321,500 fit-input rows, 23,134 full-anchor persons and 13,542 "
        "domain persons" in protocol
    )
    assert pv.RUNTIME["python"] == "3.14.4"
    assert "Python 3.14.4, NumPy 2.5.1, pandas 3.0.3" in protocol
    assert pv.selector.EXPECTED_POPULACE_HEAD in protocol


def test_protocol_stream_words_match_the_code(protocol):
    assert (
        "[root, b, 0] arm F households; [root, b, 2] and [root, b, 3] arm R "
        "full-anchor and other half-samples; [root, b, 4] arm D; "
        "[root, 2^20] limits" in protocol
    )
    import inspect

    assert '"anchor", replicate, 0' in inspect.getsource(
        pv.anchor_multiplicities
    )
    source = inspect.getsource(pv.refit_multiplicities)
    assert '(("anchor", 2), ("other", 3))' in source
    assert "int(replicate), 4" in inspect.getsource(pv.design_multiplicities)


def test_protocol_power_constants_match_the_power_script(protocol):
    assert f"{power.TAU_UNCAPPED:.4f}" == "5.0870"
    assert "2.60632 × 2 / √(1 + 1/K) = 5.0870" in protocol
    assert round(power.FLOOR_RATIO, 5) == 2.60632
    assert power.seed_conjunction_bound(6) == pytest.approx(0.025)
    assert "C(5, 2) × 0.05² = 0.025" in protocol
    assert power.MIN_GATED_CELLS == 4 and power.POWER_TARGET == 0.90
    assert power.BASES[0] == "binding"
    assert "r_c = the arm-F point estimate and v_c = v_reg,c = s²_gate,c" in (
        protocol
    )


def test_gate_leak_evidence_matches_the_recorded_output(protocol):
    lines = GATE_LEAK.read_text(encoding="utf-8").splitlines()
    assert "pairs 37552" in lines[0]
    assert lines[1] == "full n_iter 23"
    assert lines[2].startswith("copies n_iter mean 100.0 min 100 max 100")
    assert lines[3].startswith("half n_iter mean 19.1 min 11 max 30")
    assert lines[4].endswith("median 3.04 geometric mean 3.45")
    assert (
        "(37,552 pairs, 24 refits per scheme) the full fit stopped at 23 "
        "boosting iterations, half-sample refits at 11-30, and every copied "
        "refit ran to the cap of 100, with about three times the prediction "
        "variance" in protocol
    )


def test_record_table_freezes_ten_elements_and_the_procedure(text):
    rows = re.findall(
        r"^\| (\d+\. [^|]+|Named power procedure) \| ([^|]+) \|", text, re.M
    )
    assert [name.split(".")[0] for name, _ in rows[:10]] == [
        str(n) for n in range(1, 11)
    ]
    assert rows[10][0] == "Named power procedure"
    assert {status.strip() for _, status in rows} == {"Frozen", "Rule frozen"}
    assert [s.strip() for n, s in rows if n.startswith(("6", "7"))] == [
        "Rule frozen",
        "Rule frozen",
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        # d693 as ruled
        "Yes: accept all eight B0.1 defaults with the riders in",
        # d622
        "a B1 v2 reconstructed-reproduction pass may unlock B2 (and H), "
        "with the weaker label carried into B2's registration.",
        # Q1 sub-question
        "These rulings cite no boundary-2008 or boundary-2010 candidate "
        "result. PRs #255 and #273, which published those results, merged "
        "under Max's account",
        # Q4
        "No Track B gate holds ages 25-61 earnings to a fixed limit",
        "§5.3 feasibility is reviewed once, for B3 and B3L",
        # Q5
        "M6's published floor is used only as a labelled illustration",
        # Q7
        "B2's bridge hands its frozen 13,542-person domain to H, and B2 "
        "scores no one outside ages 25-64 at the scored waves",
        "H's spec names and counts its 2010 start roster, and B4's coverage "
        "declaration cites it",
        # Q8
        "2010→2014 continuity on the stated surface, ages 25–64. Not a "
        "2010-vintage forecast",
        "H and B3L may rely on B2 only within that scope",
        "removing this statement after any candidate run requires a dated "
        "amendment",
        # d622 label
        "reconstructed reproduction (weaker than bit-for-bit)",
        # element 9
        "INVALID and INCONCLUSIVE are non-passes with FAIL's consequences",
        "no rerun, no new draw or bootstrap seed, no larger K, and no "
        "re-pruning, tolerance change or rescoping",
    ],
)
def test_addendum_carries_each_ruled_sentence(prose, sentence):
    assert sentence in prose


def test_structural_power_table_matches_the_power_script(text):
    record = power.structural_record()["by_family_size"]
    for m in (1, 4, 5, 6, 16):
        row = record[str(m)]
        room = row["estimation_room_gate_bound_only"]
        room_text = (
            "none"
            if room < 0
            else (
                f"{round(room * 100):d}%" if m == 1 else f"{room * 100:.1f}%"
            )
        )
        line = (
            f"| {m} | {row['p_bound_rule_only']:.3f} | "
            f"{row['p_gate_joint']:.3f} | {room_text} | "
            f"{row['m6_seed_convention_with_bound_rule']:.3f} |"
        )
        assert line in text, line
        assert row["p_seeds_fail_given_bound_passes"] < 0.001


def test_q2_correction_figures(prose):
    record = power.structural_record()["by_family_size"]
    assert round(record["6"]["estimation_room_per_cell"], 3) == 0.411
    assert "the room is 41.1% at m = 6" in prose
    assert (
        "for the whole gate it is 2.8% at six cells, 8.4% at five and 16.0% "
        "at four" in prose
    )
    assert (
        "the bound rule passes all six cells with probability 0.917, and "
        "all 16 with 0.584" in prose
    )


def test_concept_families_and_retained_six_match_m6():
    import ast

    source = (ROOT / "scripts" / "build_m6_holdout_floors_v2.py").read_text(
        encoding="utf-8"
    )
    literal = re.search(r"^CONCEPT_FAMILY = (\{.*?^\})", source, re.M | re.S)
    assert power.CONCEPT_FAMILY == ast.literal_eval(literal.group(1))
    assert set(power.CONCEPT_FAMILY_CELLS) == set(pv.CELLS)
    assert set(power.M6_RETAINED) <= set(pv.CELLS)
    assert len(power.M6_RETAINED) == 6


def test_exposure_labels_name_the_retained_six(prose):
    for cell in power.M6_RETAINED:
        assert f"`{cell}`" in prose


# --------------------------------------------------------------------------
# After the run: the planning-value record, the power record and the tables
# --------------------------------------------------------------------------
PLANNING = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"
POWER = ROOT / "docs" / "design" / "track_b_b0_1_addendum_power.json"
COUNTS = ROOT / "docs" / "design" / "track_b_b0_1_counts.json"
#: The commit that froze protocol v2, pushed before any planning value.
FREEZE_COMMIT = "0550d2f9e250792edf845288be29165149df14a2"


@pytest.fixture(scope="module")
def planning():
    return json.loads(PLANNING.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def power_record():
    return json.loads(POWER.read_text(encoding="utf-8"))


def test_planning_values_came_from_the_frozen_run(planning):
    assert planning["schema"] == pv.SCHEMA
    assert planning["repository_head"] == FREEZE_COMMIT
    assert planning["worktree_clean"] is True
    assert planning["protocol_v2_sha256"] == PROTOCOL_V2_SHA256
    assert planning["freeze_push"]["remote_head"] == FREEZE_COMMIT
    script = ROOT / "scripts" / "track_b_b0_1_planning_values.py"
    assert (
        planning["script_sha256"]
        == hashlib.sha256(script.read_bytes()).hexdigest()
    ), "the script changed after the run"
    pv.assert_record_shape(planning)
    assert set(planning["cells"]) == set(pv.CELLS)


def test_run_read_nothing_dated_after_2010(planning):
    opened = planning["psid_files_opened_sha256"]
    assert all(pv.psid_path_allowed(Path(name)) for name in opened)
    waves = {
        int(name.split("/")[1])
        for name in opened
        if name.startswith("family/")
    }
    assert waves == set(pv.COLLECTION_WAVES) and max(waves) == 2011
    assert planning["outcome_blind"] == {
        "reference_years_after_2010_read": False,
        "b2_cell_or_floor_computed": False,
        "levels_or_gaps_recorded": False,
        "raw_scale_variances_recorded": False,
    }
    assert planning["nawi"]["maximum_key_year"] == 2006
    assert planning["geometry"]["pseudo_origin"] == 2006


def test_opened_files_are_the_audit_s_pinned_bytes(planning):
    pinned = json.loads(COUNTS.read_text(encoding="utf-8"))[
        "b2_read_set_sha256"
    ]
    opened = planning["psid_files_opened_sha256"]
    shared = set(opened) & set(pinned)
    assert len(shared) == len(opened), "an opened file is outside the pin"
    assert all(opened[name] == pinned[name] for name in shared)


def test_run_checks_passed(planning):
    assert planning["source_reproduction"]["observed"] == pv.B2_EXPECTED
    assert planning["forest_skip_check"] == {
        "gate_states_and_surfaces_equal": True,
        "projections_equal_draw_seeds": [6200, 6201],
    }
    boot = planning["bootstrap"]
    assert boot["refit_scheme"] == "half"
    assert boot["paired_truth_agreement"] is True
    assert boot["arm_f"]["used"] == pv.B_F and boot["arm_d"]["used"] == pv.B_D
    assert pv.B_R_MIN <= boot["arm_r"]["used"] <= pv.B_R_MAX
    for arm in ("arm_f", "arm_d", "arm_r"):
        assert boot[arm]["void"] is False


def test_recorded_planning_values_are_coherent(planning):
    for cell in planning["cells"].values():
        if not cell["defined"]:
            assert cell["undefined_reason"] in tables.REASONS
            continue
        ratio = cell["shared_anchor_ratio"]
        est = cell["estimation_variance"]
        gap = cell["gap_variance"]
        assert ratio["ci"][0] <= ratio["r"] <= ratio["ci"][1]
        assert est["ci"][0] <= est["ci"][1] <= est["e_ucl"]
        assert est["transport_factor"] >= 1.0
        assert est["e_b2"] == pytest.approx(
            max(0.0, est["e_ucl"]) * est["transport_factor"]
        )
        assert gap["s2"] == pytest.approx(
            ratio["r"] ** 2 + est["transport_factor"] * max(0.0, est["e"])
        )
        assert gap["s2_gate"] >= gap["s2_ucl"] >= 0


def test_power_record_recomputes_from_the_planning_record(
    planning, power_record
):
    assert (
        power_record["planning_values_sha256"]
        == hashlib.sha256(PLANNING.read_bytes()).hexdigest()
    )
    fresh = power.power_record(planning)

    def close(a, b, path=""):
        if isinstance(a, dict):
            assert set(a) == set(b), path
            for key in a:
                close(a[key], b[key], f"{path}/{key}")
        elif isinstance(a, list):
            assert len(a) == len(b), path
            for index, (x, y) in enumerate(zip(a, b, strict=True)):
                close(x, y, f"{path}[{index}]")
        elif isinstance(a, float) and isinstance(b, float):
            assert a == pytest.approx(b, rel=1e-9, abs=1e-12), path
        else:
            assert a == b, path

    close(
        {
            k: v
            for k, v in power_record.items()
            if k != "planning_values_sha256"
        },
        json.loads(json.dumps(fresh)),
    )
    assert [
        basis
        for basis, record in power_record["bases"].items()
        if record["binding"]
    ] == ["binding"]


def test_addendum_holds_the_rendered_tables(text):
    for name, rendered in tables.render().items():
        assert rendered in text, f"the {name} table is not the rendered one"


def _figure_range(values, digits=2):
    return f"{min(values):.{digits}f} to {max(values):.{digits}f}"


def test_hand_written_figures_come_from_the_records(
    prose, planning, power_record
):
    """Every figure sections 1, 10, 11 and 13 state in prose."""
    cells = planning["cells"]
    counts = planning["counts"]
    r = {n: c["shared_anchor_ratio"]["r"] for n, c in cells.items()}
    e = {n: c["estimation_variance"]["e"] for n, c in cells.items()}
    d95 = {n: c["design_ratio"]["ci"][1] for n, c in cells.items()}
    diag = {n: c["diagnostics"] for n, c in cells.items()}
    levels = {
        n for n in cells if n.split(".")[0] in ("earn_p50", "earn_p90")
    } | {n for n in cells if n.startswith("earn_zero_rate")}
    others = set(cells) - levels
    over_one = sorted(n for n in cells if r[n] > 1)
    over_limit = sorted(n for n in cells if d95[n] > pv.DESIGN_RATIO_LIMIT)
    assert len(over_one) == 7 and len(over_limit) == 9
    assert max(r, key=r.get) == "earn_p10.prime"
    assert max(d95, key=d95.get) == "earn_p50.older"
    assert sorted(e, key=e.get)[-2:] == [
        "earn_p10.prime",
        "earn_dlog_sd.prime",
    ]
    assert max(r[n] for n in levels) < 0.80
    started = planning["freeze_push"]["utc"]
    ended = planning["checkpoint_events"][-1]
    assert ended["event"] == "completed"
    binding = power_record["bases"]["binding"]
    verdict = binding["verdict"]
    best_family = verdict["envelope"]["6"]["best"]
    per_cell = binding["per_cell"]
    family_min = {
        family: min(
            per_cell[n]["gap_variance"]
            for n in cells
            if power.concept(n) == family
        )
        for family in ("dispersion", "mobility")
    }
    inflated = power_record["decision_illustrations"][
        "design_inflated_verdict"
    ]
    pruned = power_record["decision_illustrations"]["families_may_be_pruned"]
    expected = [
        f"started at {started[11:19]} UTC on {started[:10]}",
        f"finished at {ended['utc'][11:19]} UTC, after "
        f"{round(planning['wall_seconds']):,} seconds",
        f"each of the {len(planning['psid_files_opened_sha256'])} PSID files",
        f"The fit used {counts['fit_input_rows']:,} rows",
        f"held {counts['n_full_anchor']:,} persons in "
        f"{counts['n_anchor_clusters']:,} households and the domain "
        f"{counts['n_domain']:,} persons",
        f"numbered {counts['anchor_forward_pairs']:,}, against "
        f"{planning['transport']['anchor_forward_pairs_2010']:,}",
        f"resampled {counts['design']['persons']:,} truth-support persons in "
        f"{counts['design']['strata']} strata, each with two clusters",
        f"{_figure_range(e.values())} times the truth statistic's sampling "
        "variance",
        f"`earn_dlog_sd.prime` ({e['earn_dlog_sd.prime']:.2f}) and "
        f"`earn_p10.prime` ({e['earn_p10.prime']:.2f})",
        f"It is {_figure_range([r[n] for n in others])} for the others, and "
        "above 1 for seven of them",
        f"up to {max(d95.values()):.3f} for `earn_p50.older`",
        "simulation noise is "
        + _figure_range(
            [
                round(100 * diag[n]["simulation_share_of_refit_variance"])
                for n in cells
            ],
            0,
        ).replace(" to ", "% to ")
        + "% of Var(δ)",
        "SD is "
        + _figure_range(
            [diag[n]["floor_sigma_over_twice_truth_sd"] for n in cells]
        ),
        "Monte Carlo error is "
        + _figure_range([diag[n]["mc_error_over_se_up"] for n in cells])
        + " se_up",
        f"up to {r['earn_p10.prime']:.2f} for `earn_p10.prime`",
        f"The best reaches {verdict['best_family_surface_p_gate']:.3f}, while "
        f"four level cells together reach "
        f"{verdict['best_four_cell_surface']['p_gate']:.3f}",
        f"`earn_zero_rate.older`, at {best_family['p_gate']:.3f}",
        f"dispersion cell alone passes the bound rule with probability "
        f"{per_cell['earn_dlog_sd.older']['bound_pass_at_m6']:.3f}, its "
        f"mobility cell {per_cell['earn_mob_h2_diag']['bound_pass_at_m6']:.3f}"
        f", its change-mean cell "
        f"{per_cell['earn_dlog_mean.prime']['bound_pass_at_m6']:.3f} and its "
        f"autocorrelation cell "
        f"{per_cell['earn_autocorr_lag2']['bound_pass_at_m6']:.3f}",
        f"are {family_min['dispersion']:.3f} and "
        f"{family_min['mobility']:.3f} se_up²",
        "On point variances the best family surface reaches "
        f"{power_record['bases']['central']['verdict']['best_family_surface_p_gate']:.3f}",
        "On the audit's basis (r = 1, e = 0) it reaches "
        f"{power_record['bases']['audit_upper_bound']['verdict']['best_family_surface_p_gate']:.3f}",
        f"surface reaches {inflated['best_four_cell_surface']['p_gate']:.3f} "
        f"and the best family surface "
        f"{inflated['best_family_surface_p_gate']:.3f}",
        "the largest surface that reaches 0.90 "
        f"({pruned['as_measured']['largest_surface']['p_gate']:.3f})",
        "`earn_zero_rate.older` "
        f"({pruned['as_measured']['by_family_count']['3']['p_gate']:.3f})",
        "falls from six cells to five",
    ]
    assert best_family["cells"] == [
        "earn_autocorr_lag2",
        "earn_dlog_mean.prime",
        "earn_dlog_sd.older",
        "earn_mob_h2_diag",
        "earn_p90.prime",
        "earn_zero_rate.older",
    ]
    assert len(pruned["as_measured"]["largest_surface"]["cells"]) == 6
    assert len(pruned["design_inflated"]["largest_surface"]["cells"]) == 5
    assert max(map(int, pruned["as_measured"]["by_family_count"])) == 3
    assert sorted(pruned["as_measured"]["largest_surface"]["cells"]) == sorted(
        levels
    )
    for phrase in expected:
        assert phrase in prose, phrase


def test_verdict_and_decisions_follow_the_records(prose, power_record):
    verdict = power_record["bases"]["binding"]["verdict"]
    flags = power_record["planning_flags"]
    assert verdict["family_floor_blocks"] and not verdict["feasible"]
    assert not verdict["d693_flip_fires"]
    assert flags["household_resampling_stands"] is False
    assert flags["cells_without_planning_values"] == []
    assert flags["cells_with_cross_term_resolved_positive"] == []
    for phrase in (
        "Decision d781 asks Max how to rescope it",
        "goes to Max (d782, section 13)",
        "Max has ruled on d781",
        "**d781: how to rescope B2.**",
        "**d782: how B2's standard error treats PSID's design.**",
        "B2 stops here.",
    ):
        assert phrase in prose, phrase
