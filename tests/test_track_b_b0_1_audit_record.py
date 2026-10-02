"""Pin the Track B B0.1 audit record to its frozen protocol and counts.

The audit (docs/design/track_b_b0_1_audit.md) quotes counts and power
figures from docs/design/track_b_b0_1_counts.json, which the count script
wrote once from the protocol-freeze commit. Revision 1 adds the exposure
inventory (docs/design/track_b_b0_1_exposure_inventory.json, written once
by scripts/track_b_b0_1_exposure_inventory.py) and basis-explicit power
figures (scripts/track_b_b0_1_review_power.py). These tests read those
committed files, the scripts, M6 v4's published floor table and, for the
differential rescan, the value-bearing files the inventory names. They
print nothing from those files.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_counts as script  # noqa: E402
import track_b_b0_1_exposure_inventory as inventory  # noqa: E402
import track_b_b0_1_review_power as review_power  # noqa: E402

AUDIT = ROOT / "docs" / "design" / "track_b_b0_1_audit.md"
COUNTS = ROOT / "docs" / "design" / "track_b_b0_1_counts.json"
SCRIPT = ROOT / "scripts" / "track_b_b0_1_counts.py"

#: The commit that froze the protocol before any count ran.
FREEZE_COMMIT = "e51216fd59230e7eab3992ee22d7c0bdf61bcca8"
#: SHA-256 of the protocol block at FREEZE_COMMIT, markers included.
PROTOCOL_SHA256 = (
    "345c82ee74dcf89f2ae7021751d71ec17992e30d7aa4a1fff9060dd4fd707f89"
)
BEGIN, END = "<!-- protocol:begin -->", "<!-- protocol:end -->"


@pytest.fixture(scope="module")
def record():
    return json.loads(COUNTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def audit_text():
    return AUDIT.read_text(encoding="utf-8")


def test_protocol_block_is_byte_identical_to_the_freeze(audit_text):
    start = audit_text.index(BEGIN)
    stop = audit_text.index(END) + len(END)
    block = audit_text[start:stop]
    assert hashlib.sha256(block.encode()).hexdigest() == PROTOCOL_SHA256
    assert audit_text.count(BEGIN) == 1 and audit_text.count(END) == 1


def test_counts_were_written_by_the_frozen_script(record):
    assert record["schema"] == script.SCHEMA
    assert record["repository_head"] == FREEZE_COMMIT
    assert record["worktree_clean"] is True
    digest = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert record["script_sha256"] == digest, (
        "the count script changed after the recorded run; a change is a "
        "new protocol version"
    )


def test_record_declares_no_outcome_was_computed(record):
    assert record["outcome_blind"] == {
        "b2_cell_or_floor_computed": False,
        "earnings_levels_read_into_counts": False,
        "projection_run": False,
        "zero_or_positive_earnings_counted": False,
    }


def test_nawi_prefix_matches_the_repository_pin(record):
    nawi = record["nawi"]
    assert nawi["checked"] is True
    assert nawi["matches_repository_pin"] is True
    assert nawi["maximum_admitted_key_year"] == script.BOUNDARY_YEAR
    assert nawi["fit_decade_keys_present"] is True


def test_read_set_covers_every_family_wave_through_2015(record):
    read_set = record["b2_read_set_sha256"]
    waves = [
        wave
        for wave in script.family.FAMILY_WAVES
        if wave - script.WAVE_OFFSET <= script.HORIZON_YEARS[-1]
    ]
    assert len(read_set) == 2 * len(waves) + 2
    for wave in waves:
        assert any(key.startswith(f"family/{wave}/") for key in read_set)
    for digest in read_set.values():
        assert len(digest) == 64
    for name, digest in record["psid_files_opened_sha256"].items():
        assert read_set[name] == digest


def test_counts_match_both_selector_ledgers(record):
    counts = record["counts"]
    by_period = {
        year: counts["scored_support"][year]["scored_rows"]
        for year in ("2010", "2012", "2014")
    }
    for ledger in record["ledger_support_counts"].values():
        assert ledger["anchor_wave"] == counts["anchor_wave"]
        assert ledger["n_full_anchor"] == counts["full_anchor_persons"]
        assert ledger["n_domain"] == counts["domain_persons"]
        assert ledger["truth_support_rows"] == counts["scored_rows_total"]
        assert ledger["truth_support_rows_by_period"] == by_period
        assert (
            ledger["endpoint_support_rows"]
            == counts["level_cells"]["pooled"]["rows"]
        )


def test_recorded_accounting_identities_hold(record):
    counts = record["counts"]
    domain = counts["domain_persons"]
    for year, labels in counts["domain_dispositions"].items():
        assert set(labels) == set(script.DISPOSITIONS)
        assert sum(labels.values()) == domain
        assert (
            labels["scored"] == counts["scored_support"][year]["scored_rows"]
        )
    for summary in (
        *counts["level_cells"].values(),
        *counts["change_pairs"].values(),
    ):
        assert summary["cluster_worst_n_eff"] <= summary["kish_n_eff"]
        assert summary["kish_n_eff"] <= summary["rows"]


def test_power_record_recomputes_exactly(record):
    assert script.power_record(record["counts"]) == record["power"]


def _thousands(value: float) -> str:
    return f"{round(value):,}"


def test_audit_quotes_the_recorded_figures(record, audit_text):
    counts = record["counts"]
    power = record["power"]
    prose = " ".join(audit_text.split())
    quoted = [
        counts["full_anchor_persons"],
        counts["domain_persons"],
        counts["domain_by_role"]["head"],
        counts["domain_by_role"]["spouse"],
        counts["domain_by_anchor_wave_age"]["under_25"],
        counts["domain_by_anchor_wave_age"]["65_plus"],
        counts["level_cells"]["pooled"]["rows"],
        counts["level_cells"]["pooled"]["kish_n_eff"],
        counts["level_cells"]["pooled"]["cluster_worst_n_eff"],
        counts["level_cells"]["prime"]["kish_n_eff"],
        counts["level_cells"]["older"]["kish_n_eff"],
        counts["level_cells"]["prime"]["cluster_worst_n_eff"],
        counts["level_cells"]["older"]["cluster_worst_n_eff"],
        counts["change_pairs"]["pooled_one_step"]["kish_n_eff"],
        counts["change_pairs"]["pooled_two_step"]["kish_n_eff"],
    ]
    for year in ("2010", "2012", "2014"):
        quoted.append(counts["scored_support"][year]["scored_rows"])
    for year in ("2012", "2014"):
        quoted.extend(
            value
            for value in counts["domain_dispositions"][year].values()
            if value >= 1_000
        )
    limits = power["section_5_3_limits_on_b2_support"]
    for m in ("1", "6", "16"):
        quoted.append(
            limits[m]["by_cohort"]["prime"][
                "participation_required_n_eff_worst_p"
            ]
        )
        quoted.append(
            limits[m]["persistence"]["lag1_pooled_one_step"][
                "required_positive_pair_n_eff"
            ]
        )
    missing = [
        _thousands(value) for value in quoted if _thousands(value) not in prose
    ]
    assert not missing, missing

    rule = power["m6_floor_rule"]
    for m, text in (("6", "0.9742"), ("16", "0.8590")):
        assert f"{rule['p_gate_by_family_size'][m]:.4f}" == text
        assert text in prose
    assert f"at most {rule['max_uncapped_cells_at_0_90']} uncapped" in (
        prose.lower()
    )


# --------------------------------------------------------------------------
# Revision 1: the exposure inventory and the basis-explicit power figures
# --------------------------------------------------------------------------

INVENTORY = ROOT / "docs" / "design" / "track_b_b0_1_exposure_inventory.json"
INVENTORY_SCRIPT = ROOT / "scripts" / "track_b_b0_1_exposure_inventory.py"
#: The commit that added the inventory script; it ran once from there.
INVENTORY_COMMIT = "de08c69f3383baa3159cba1dd6edd766a57f1c14"
QSTAR = "docs/analysis/m6_qstar_train_only_selection_results.json"
RHOSTAR = "docs/analysis/m6_rhostar_train_only_selection_results.json"
F1 = "docs/analysis/m6_c3_f1_mechanism_diagnostic_results.json"
M6_FLOORS = (
    ROOT
    / "docs"
    / "amendments"
    / ("gate_m6_amendment_1_closed_domain_floors.md")
)


@pytest.fixture(scope="module")
def exposure():
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_path(exposure):
    return {entry["path"]: entry for entry in exposure["files"]}


@pytest.fixture(scope="module")
def revision_power(record):
    return review_power.review_power_record(record["counts"])


def _prose(text: str) -> str:
    return " ".join(text.split())


def test_inventory_was_written_by_the_committed_script(exposure):
    assert exposure["schema"] == inventory.SCHEMA
    assert exposure["repository_head"] == INVENTORY_COMMIT
    assert exposure["worktree_clean"] is True
    digest = hashlib.sha256(INVENTORY_SCRIPT.read_bytes()).hexdigest()
    assert (
        exposure["script_sha256"] == digest
    ), "the inventory script changed after its recorded run"
    assert exposure["content_recorded"] is False


def test_inventory_geometry_and_totals(exposure):
    assert exposure["boundaries_touching_b2_targets"] == {
        "2008": [2012],
        "2010": [2012, 2014],
    }
    assert exposure["tracked_files_scanned"] == 1647
    assert exposure["tier_counts"] == {
        "boundary_values": 20,
        "code": 24,
        "marital": 45,
        "mentions": 31,
    }
    assert all("track_b_b0_1" in p for p in exposure["excluded_self_paths"])
    assert len(exposure["q6_exclusions"]) == 20


@pytest.mark.parametrize(("path", "rungs"), [(QSTAR, 21), (RHOSTAR, 17)])
def test_both_ledgers_hold_2008_and_2010_blocks(by_path, path, rungs):
    entry = by_path[path]
    assert entry["tier"] == "boundary_values"
    blocks = {
        block["path"]: block for block in entry["json"]["boundary_blocks"]
    }
    top = blocks["/boundaries/{year}"]
    assert top["years"] == [2006, 2008, 2010]
    assert top["earnings_cells"] and not top["marital"]
    assert {"2012", "2014"} <= set(top["descendant_year_keys"])
    rung = blocks["/rungs/{rung}/boundaries/{year}"]
    assert rung["years"] == [2006, 2008, 2010]
    assert rung["n_blocks"] == 3 * rungs
    assert {"aggregates", "truth_moments", "floor"} <= set(rung["field_names"])
    assert "/rungs/{rung}/objectives/all_20/by_boundary/{year}" in blocks


def test_f1_artifact_is_a_2010_boundary_record(by_path):
    entry = by_path[F1]
    assert entry["tier"] == "boundary_values"
    assert {
        "path": "/protocol",
        "values": [2010],
        "n": 1,
        "marital": False,
    } in entry["json"]["pseudo_boundary_fields"]


def _value_ranges(entry):
    return [
        (r["start"], r["end"])
        for r in entry["ranges"]
        if inventory.range_is_value_bearing(r)
    ]


def test_inventory_flags_the_prose_the_first_version_missed(by_path):
    engine = _value_ranges(by_path["docs/design/m6_projection_engine.md"])
    for line in (1266, 1290, 1311):
        assert any(start <= line <= end for start, end in engine), line
    paper = _value_ranges(by_path["paper/paper.qmd"])
    assert any(start <= 2238 and 2248 <= end for start, end in paper)
    for path in (
        "docs/amendments/m6_amendment_4_qstar_lock_addendum.md",
        "docs/design/m6_candidate3_lock_addendum.md",
        "docs/design/m6_candidate3_program.md",
        "docs/design/m6_candidate2_program.md",
        "docs/forecasts/timeline_ledger.json",
    ):
        assert by_path[path]["tier"] == "boundary_values", path


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_inventory_rescan_agrees_for_unchanged_files(exposure):
    """Differential: rescanning an unchanged value-bearing file reproduces
    its recorded entry."""
    checked = 0
    for entry in exposure["files"]:
        if entry["tier"] != "boundary_values":
            continue
        path = ROOT / entry["path"]
        if not path.exists() or _git_blob_sha1(path) != entry["blob_sha1"]:
            continue
        fresh = inventory.scan_file(
            entry["path"], path.read_text(encoding="utf-8")
        )
        expected = {k: v for k, v in entry.items() if k != "blob_sha1"}
        assert fresh == expected, entry["path"]
        checked += 1
    assert checked >= 3


def test_audit_lists_every_q6_exclusion(exposure, audit_text):
    for item in exposure["q6_exclusions"]:
        if item["scope"] == "whole_file":
            row = f"| `{item['path']}` | whole file |"
        else:
            spans = ", ".join(f"{a}-{b}" for a, b in item["lines"])
            row = f"| `{item['path']}` | lines {spans} |"
        assert row in audit_text, row


def test_audit_couples_figure(record, audit_text):
    counts = record["counts"]
    spouses = counts["domain_by_role"]["spouse"]
    persons = counts["domain_persons"]
    prose = _prose(audit_text)
    assert (
        f"{2 * spouses:,} persons ({round(100 * 2 * spouses / persons)}%)"
        in (prose)
    )


def test_m6_planning_constants_match_the_published_floor():
    row = M6_FLOORS.read_text(encoding="utf-8").splitlines()[69]
    assert row.startswith("| `earn_autocorr_lag2` |")
    assert str(review_power.M6_LAG2_FLOOR_SIGMA) in row
    assert f"{review_power.M6_LAG2_WEAKER_HALF_SUPPORT:,}" in row


def test_revision1_bound_rule_values(revision_power, record):
    bound = revision_power["bound_rule_at_k3"]
    frozen_rule = record["power"]["section_5_2_bound_rule"]
    pinned = {
        "1": (0.4819, 0.8984, 0.9982),
        "6": (0.0, 0.6623, 0.9857),
        "16": (0.0, 0.4791, 0.967),
    }
    for m, values in pinned.items():
        got = tuple(
            bound[m][basis]["pass_probability_no_estimation"]
            for basis in review_power.BASES
        )
        assert got == values
        assert bound[m]["m6_convention"][
            "pass_probability_no_estimation"
        ] == pytest.approx(
            frozen_rule[m][
                "pass_probability_at_m6_floor_tolerance_gap_sigma_half"
            ],
            abs=1e-4,
        )
    assert revision_power["full_support_headroom_share_of_se_full_sq"] == {
        "1": 1.041,
        "6": 0.4311,
        "16": 0.2341,
    }


def test_audit_quotes_the_revision1_power_figures(
    revision_power, record, audit_text
):
    prose = _prose(audit_text)
    bound = revision_power["bound_rule_at_k3"]
    frozen_rule = record["power"]["section_5_2_bound_rule"]
    for m in ("1", "6", "16"):
        cells = [
            f"{bound[m][basis]['pass_probability_no_estimation']:.3f}"
            for basis in review_power.BASES
        ]
        row = (
            f"| {m} | {frozen_rule[m]['bonferroni_z']:.3f} | "
            f"{frozen_rule[m]['required_tol_over_se']:.3f} | {cells[0]} | "
            f"{cells[1]} | {cells[2]} |"
        )
        assert row in audit_text, row
        ks = " | ".join(
            f"{bound[m][basis]['k_needed']:.2f}"
            for basis in review_power.BASES
        )
        assert f"| {m} | {ks} |" in audit_text
    over_gap = ", ".join(
        f"{round(100 * bound[m]['full_support']['estimation_headroom_share_of_gap_variance'])}%"
        for m in ("1", "6")
    )
    assert f"{over_gap} and 22%" in prose
    side_a = [
        bound[m]["side_a"]["estimation_headroom_share_of_gap_variance"]
        for m in ("1", "6", "16")
    ]
    assert f"−{abs(side_a[0]) * 100:.1f}%" == "−0.4%"
    assert [round(100 * v) for v in side_a[1:]] == [-29, -39]
    assert "−0.4%, −29% and −39%" in prose
    assert "104%, 43% and 23%" in prose

    participation = revision_power["participation_3pp"]["by_cell"]

    def thresholds(key):
        values = participation[key]["min_p"]
        return " / ".join(
            "any" if values[m] == 0.5 else f"{values[m]:.3f}"
            for m in ("1", "6", "16")
        )

    for cohort, label in (("prime", "Prime"), ("older", "Older")):
        for basis, basis_label in (
            ("full_support", "full support"),
            ("side_a", "side A"),
        ):
            kish = f"{cohort}.{basis}.kish_n_eff"
            worst = f"{cohort}.{basis}.cluster_worst_n_eff"
            row = (
                f"| {label}, {basis_label} | "
                f"{participation[kish]['n_eff']:,} | {thresholds(kish)} | "
                f"{participation[worst]['n_eff']:,} | {thresholds(worst)} |"
            )
            assert row in audit_text, row

    quantiles = revision_power["quantile_10pct_max_log_sd_m6"]
    for cohort, label in (("prime", "Prime"), ("older", "Older")):
        cells = []
        for q in ("p10", "p50"):
            kish = quantiles[f"{cohort}.{q}.kish_n_eff"]
            worst = quantiles[f"{cohort}.{q}.cluster_worst_n_eff"]
            cells.append(
                f"{kish['full_support']:.2f} / {worst['full_support']:.2f}"
            )
            cells.append(f"{kish['side_a']:.2f} / {worst['side_a']:.2f}")
        row = f"| {label} | " + " | ".join(cells) + " |"
        assert row in audit_text, row

    persistence = revision_power["persistence_0_05"]["by_pairs"]

    def rhos(values):
        return " / ".join(
            "any" if values[m] == 0.0 else f"{values[m]:.2f}"
            for m in ("1", "6", "16")
        )

    labels = {
        (
            "lag1",
            "full_support",
        ): "Lag 1 (two-year steps, pooled), full support",
        ("lag1", "side_a"): "Lag 1, side A",
        ("lag2", "full_support"): "Lag 2 (2010-2014), full support",
        ("lag2", "side_a"): "Lag 2, side A",
    }
    for (lag, basis), label in labels.items():
        kish = persistence[f"{lag}.{basis}.kish_n_eff"]
        worst = persistence[f"{lag}.{basis}.cluster_worst_n_eff"]
        first = (
            f"| {label} | Kish | {kish['n_eff']:,} | "
            f"{rhos(kish['min_rho_normal'])} | "
            f"{rhos(kish['min_rho_factor_2'])} |"
        )
        second = (
            f"| | household-worst | {worst['n_eff']:,} | "
            f"{rhos(worst['min_rho_normal'])} | "
            f"{rhos(worst['min_rho_factor_2'])} |"
        )
        assert first in audit_text, first
        assert second in audit_text, second

    plan = revision_power["m6_lag2_planning_illustration"]
    assert f"about {plan['se_per_half']:.4f}" in prose
    assert f"about {plan['se_full_support']:.4f}" in prose
    by_m = plan["by_family_size"]
    allowed = [f"{by_m[m]['se_full_allowed']:.4f}" for m in ("1", "6", "16")]
    assert f"{allowed[0]}, {allowed[1]} and {allowed[2]}" in prose
    full = [
        f"{by_m[m]['support_multiple_of_m6_needed_full_support']:.2f}"
        for m in ("1", "6", "16")
    ]
    side = [
        f"{by_m[m]['support_multiple_of_m6_needed_side_a']:.2f}"
        for m in ("1", "6", "16")
    ]
    assert f"{full[0]}, {full[1]} or {full[2]} times M6's" in prose
    assert f"{side[0]}, {side[1]} or {side[2]} times on side A" in prose
    pairs = plan["pairs_below_which_se_half_is_within_1_over_sqrt_n"]
    assert f"about {round(pairs, -2):,.0f} effective positive" in prose

    summary = {
        basis: [
            bound[m][basis]["pass_probability_no_estimation"]
            for m in ("1", "6", "16")
        ]
        for basis in review_power.BASES
    }
    assert "probability 0.48, 0 and 0" in prose
    side_a = summary["side_a"]
    assert side_a[0] < 0.90
    side_a_text = f"{side_a[0]:.3f}, {side_a[1]:.3f} and {side_a[2]:.3f}"
    assert (
        f"probability {side_a_text} at the reference standard error, so at "
        "that standard error it misses 0.90 even for one cell" in prose
    )
    assert f"{side_a_text} on side A" in prose
    full_summary = ", ".join(f"{v:.3f}" for v in summary["full_support"][:2])
    assert (
        f"probability {full_summary} and {summary['full_support'][2]:.3f} at "
        "its reference standard error" in prose
    )
    # Revision 2, after the addendum's run: these are not bounds.
    assert (
        "The reference standard errors are reference points, not bounds"
        in (prose)
    )
    assert "at least 0.898" not in prose and "≥ 0.898" not in prose


# --------------------------------------------------------------------------
# Revision 2 (round-2 finding N6): the figures revision 1 quoted only in prose
# --------------------------------------------------------------------------
def test_revision2_pins_the_prose_only_figures(record, audit_text):
    prose = _prose(audit_text)
    m6 = [
        round(review_power.bound_rule_pass("m6_convention", m), 2)
        for m in (2, 3, 4, 5)
    ]
    assert m6 == [0.28, 0.17, 0.09, 0.02]
    assert "0.28, 0.17, 0.09 and 0.02 at m = 2 to 5" in prose
    assert round(review_power.k_needed("side_a", 6), 1) == 3.8
    assert "a larger k, about 3.8 at m = 6" in prose

    counts = record["counts"]
    level = counts["level_cells"]

    def band(cohort, basis, size, m):
        share = review_power.SUPPORT_SHARE[basis]
        upper = review_power.participation_min_p(
            level[cohort][size] * share, m
        )
        return round(1.0 - upper, 2), round(upper, 2)

    assert band("prime", "full_support", "cluster_worst_n_eff", 1) == (
        0.19,
        0.81,
    )
    assert band("older", "full_support", "cluster_worst_n_eff", 1) == (
        0.17,
        0.83,
    )
    upper = review_power.participation_min_p(
        level["prime"]["cluster_worst_n_eff"] * 0.5, 16
    )
    assert (round(1 - upper, 3), round(upper, 3)) == (0.049, 0.951)
    upper = review_power.participation_min_p(
        level["older"]["cluster_worst_n_eff"] * 0.5, 16
    )
    assert (round(1 - upper, 3), round(upper, 3)) == (0.045, 0.955)
    assert band("prime", "side_a", "kish_n_eff", 1) == (0.28, 0.72)
    assert band("older", "side_a", "kish_n_eff", 1) == (0.27, 0.73)
    for text in (
        "about 0.19-0.81 (full support, m = 1) to about 0.049-0.951",
        "from about 0.17-0.83 to about 0.045-0.955",
        "about 0.28-0.72 (prime) and 0.27-0.73 (older) at m = 1",
        "in a band of about 0.28-0.72 at m = 1",
    ):
        assert text in prose

    effects = [
        cell["kish_n_eff"] / cell["cluster_worst_n_eff"]
        for group in ("level_cells", "change_pairs")
        for cell in counts[group].values()
        if isinstance(cell, dict) and "kish_n_eff" in cell
    ]
    assert round(min(effects), 1) == 1.5 and round(max(effects), 1) == 3.0
    assert "by a factor of 1.5 to 3.0" in prose

    assert script.max_uncapped_surface(2.35) == 6
    assert script.max_uncapped_surface(2.64) == 14
    assert "Those ratios allow 6 to 14 cells" in prose


def test_revision2_q2_correction_is_gate_level(audit_text):
    prose = _prose(audit_text)
    import track_b_b0_1_addendum_power as addendum_power

    record = addendum_power.structural_record()["by_family_size"]
    room = {
        m: record[m]["estimation_room_gate_bound_only"]
        for m in ("4", "5", "6", "16")
    }
    assert round(room["6"], 3) == 0.028
    assert round(room["4"], 3) == 0.160 and round(room["5"], 3) == 0.084
    assert room["16"] < 0
    assert round(record["6"]["p_bound_rule_only"], 3) == 0.917
    assert round(record["16"]["p_bound_rule_only"], 3) == 0.584
    assert "the room is 2.8% of the gap variance at m = 6 (16.0%" in prose
    assert "at m = 4, 8.4% at m = 5, none at m = 16)" in prose
    assert "the room is 99%, 2.8% and none" in prose
    assert "with probability 0.917 at 6 cells and 0.584 at 16" in prose
    tol_full = review_power.tol_over_gap_se("full_support")
    tol_side = review_power.tol_over_gap_se("side_a")
    assert round(tol_full, 1) == 5.1 and round(tol_side, 1) == 3.6
    assert round(tol_full / tol_side, 1) == 1.4
    assert "about 5.1 standard errors wide instead of about 3.6" in prose


def test_revision2_restores_the_citation(audit_text):
    source = (
        (ROOT / "scripts" / "select_m6_qstar_train_only.py")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert '"raw_source_is_retrospective_product": True' in source[644]
    assert "(`select_m6_qstar_train_only.py:645`)" in audit_text
    assert "(`select_m6_qstar_train_only.py:646`)" not in audit_text
