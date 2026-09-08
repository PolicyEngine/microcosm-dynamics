"""Tests for the claiming gate floors v1 artifact
(runs/claiming_gate_floors_v1.json): the THRESHOLD-BINDING derivation
from the verified publication floor runs/claiming_publication_floor_v1.json.

The artifact is a REPORTED record (reads no gate, changes no gate,
ratifies nothing): it derives the gate-schema blocks the packet's
section-5 draft needs -- the 42 tolerance derivations, the partition,
every filed alternative, the frontier scan, the deployed finding, the
certification scope, the circularity disclosure, fit isolation, the
rulings filed and priced -- and carries the DRAFT ``gate_b2_claiming``
block as a string. Every ruling is FILED and PRICED; none is made.

All tests are always runnable: they touch only committed files (the
floor, the two editions, the transcription script, the artifact itself)
and the two builders. The derivation bindings themselves (tolerances
recomputed from the floor's strata and trends, the perturbations, the
failure sets, the frontier scan, the mutated-builder test) live in
``tests/test_gates_derivations.py`` on the gate_m4 pattern; this file
pins the artifact, its builder and its internal consistency, and holds
the PRE-LOCK MARKER ``GATE_B2_CLAIMING_BLOCK_LANDED``.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "claiming_gate_floors_v1.json"
FLOOR = ROOT / "runs" / "claiming_publication_floor_v1.json"
GATES = ROOT / "gates.yaml"
SCRIPTS = ROOT / "scripts"
BUILDER = SCRIPTS / "build_claiming_gate_floors_v1.py"
FLOOR_BUILDER = SCRIPTS / "build_claiming_publication_floor.py"

#: The VERIFIED floor basis (floors v2 at cd8f167). Must not move.
FLOOR_COMMITTED = (
    227_079,
    "bd78d632219175d2ab47bc7a87661dde782a6a262a26add3a3be349618593ae1",
)
#: THIS artifact's committed bytes (size, sha256), re-stated in the same
#: commit as any rebuild (the gate-3 digest-pin precedent).
GATE_V1_COMMITTED = (
    309_781,
    "e1983ccaf880c15f9fcc331adaf723f64365c91de9dd73db13bc478e94303843",
)
#: PRE-LOCK MARKER (the mortality pattern). False until the commit that
#: inserts the gate_b2_claiming block flips it -- in every file the
#: artifact's flip_plan names, in the same commit -- and retires the
#: live-file guard test.
GATE_B2_CLAIMING_BLOCK_LANDED = False

T_MAX_PP = 3.0
N_GATED = 34
N_REPORT_ONLY = 8


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def _floor() -> dict:
    return json.loads(FLOOR.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _import_builder():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_claiming_gate_floors_v1 as builder

    return builder


def _block(art: dict) -> dict:
    text = art["draft_gates_yaml_fragment"]["text"]
    return yaml.safe_load("gates:\n" + text)["gates"]["gate_b2_claiming"]


# --------------------------------------------------------------------------
# Framing and pins
# --------------------------------------------------------------------------
def test_schema_reported_and_nothing_ruled():
    art = _artifact()
    assert art["schema_version"] == "claiming_gate_floors.v1"
    assert art["run"] == "claiming_gate_floors_v1"
    assert art["reported_not_gated"] is True
    assert art["ceremony"]["gates_yaml_untouched"] is True
    dnd = " ".join(art["does_not_do"])
    for phrase in (
        "edit gates.yaml",
        "score a candidate",
        "make any ruling",
        "ratify any threshold",
        "retire the two live-file",
    ):
        assert phrase in dnd, phrase
    assert art["open_questions_for_the_ceremony"][0]["status"].endswith(
        "not ruled"
    )


def test_artifact_bytes_are_pinned_to_the_committed_digest():
    assert ARTIFACT.stat().st_size == GATE_V1_COMMITTED[0]
    assert _sha(ARTIFACT) == GATE_V1_COMMITTED[1]


def test_source_floor_is_the_verified_v2_read_by_path():
    art = _artifact()
    assert FLOOR.stat().st_size == FLOOR_COMMITTED[0]
    assert _sha(FLOOR) == FLOOR_COMMITTED[1]
    src = art["source_floor"]
    assert (src["size_bytes"], src["sha256"]) == FLOOR_COMMITTED
    assert src["path"] == "runs/claiming_publication_floor_v1.json"
    assert "checked before any value is read" in src["read_by"]
    assert art["revision_pins"]["source_floor_sha256"] == FLOOR_COMMITTED[1]
    floor = _floor()
    assert src["built_utc"] == floor["build"]["built_utc"]
    assert (
        art["floor_does_not_establish_carried"] == floor["does_not_establish"]
    )
    assert (
        art["packet_reconciliation_carried"] == floor["packet_reconciliation"]
    )


def test_builders_are_sha_pinned_and_the_scoring_frame_is_the_floors():
    art = _artifact()
    pins = art["revision_pins"]
    assert pins["gate_builder_sha256"] == _sha(BUILDER)
    assert pins["floor_builder_sha256"] == _sha(FLOOR_BUILDER)
    floor = _floor()
    frame = art["scoring_frame"]
    for key in ("edition_2023", "edition_2014", "claiming_reference_v1"):
        assert frame[key]["sha256"] == floor["sources"][key]["sha256"]
        assert frame[key]["bytes"] == floor["sources"][key]["bytes"]
        assert _sha(ROOT / frame[key]["path"]) == frame[key]["sha256"]
    assert frame["fit_years"] == [1998, 2019]
    assert frame["holdout_years"] == {"h1": 2020, "h2": 2021, "h3": 2022}


def test_gates_yaml_pre_lock_guard():
    """While GATE_B2_CLAIMING_BLOCK_LANDED is False, gates.yaml is innocent
    of the gate and of both claiming artifacts; the citations block
    records the live file as byte-identical to the pinned blob."""
    text = GATES.read_text()
    art = _artifact()
    if not GATE_B2_CLAIMING_BLOCK_LANDED:
        for name in (
            "gate_b2_claiming",
            "claiming_gate_floors_v1",
            "claiming_publication_floor_v1",
        ):
            assert name not in text, name
        assert art["gates_yaml_citations"]["gate_b2_claiming_present"] is False
        assert art["gates_yaml_citations"]["artifact_named"] is False
        assert art["gates_yaml_citations"]["floor_named"] is False
        return
    assert "gate_b2_claiming" in yaml.safe_load(text)["gates"]


def test_gates_yaml_citations_hold_on_the_pinned_blob():
    art = _artifact()
    cites = art["gates_yaml_citations"]
    raw = GATES.read_bytes()
    blob = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    if blob == cites["git_blob_sha1"]:
        lines = raw.decode("utf-8").split("\n")
        assert cites["byte_identical_to_working_tree"] is True
    else:
        result = subprocess.run(
            ["git", "cat-file", "blob", cites["git_blob_sha1"]],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        lines = result.stdout.decode("utf-8").split("\n")
    for line_no, entry in cites["line_citations"].items():
        assert entry["expects"] in lines[int(line_no) - 1], line_no
        assert entry["holds"] is True


# --------------------------------------------------------------------------
# The derived blocks: internal consistency and the floor cross-checks
# --------------------------------------------------------------------------
def test_derivation_convention_and_cell_order():
    art = _artifact()
    floor = _floor()
    conv = art["derivation_convention"]
    assert conv["k_rev"] == 2.0
    assert conv["rounding_pp"] == 0.05
    assert conv["t_max_pp"] == T_MAX_PP
    assert conv["rounding_mode"] == "ROUND_HALF_UP"
    assert conv["sd_knob_pp"] == round(
        floor["strata"]["conditional_terminal_year"]["sd_pp"], 4
    )
    assert (
        conv["sd_full_precision_pp"]
        == floor["strata"]["conditional_terminal_year"]["sd_pp"]
    )
    assert conv["revision_term_pp"] == round(2.0 * conv["sd_knob_pp"], 6)
    assert conv["cell_order_equals_floor_derivations_order"] is True
    assert art["cell_order"] == list(floor["power_cap"]["derivations"])
    assert len(art["cell_order"]) == 42


def test_tolerance_derivations_are_complete_and_self_consistent():
    art = _artifact()
    floor = _floor()
    td = art["tolerance_derivations"]
    assert set(td) == set(art["cell_order"])
    for cell, entry in td.items():
        assert entry["rounding_mode"] == "ROUND_HALF_UP"
        assert entry["rounding"] == 2
        assert (
            entry["revision_term_pp"]
            == art["derivation_convention"]["revision_term_pp"]
        )
        assert entry["tolerance_pp"] == entry["tolerance_pp_round_half_up"]
        assert entry["gate_eligible"] is (entry["tolerance_pp"] <= T_MAX_PP)
        assert (
            entry["trend_pp_per_year"]
            == floor["power_cap"]["derivations"][cell]["trend_pp_per_year"]
        )
        assert entry["unrounded_tolerance_pp"] == float(
            entry["unrounded_tolerance_exact"]
        )
    ties = [
        c
        for c, e in td.items()
        if e["tolerance_pp_round_half_up"] != e["tolerance_pp_round_half_even"]
    ]
    assert ties == ["age70plus|female|h2"]


def test_gate_partition_is_the_gate_m4_shape_and_matches_the_floor():
    art = _artifact()
    floor = _floor()
    part = art["gate_partition"]
    for key in (
        "gate_eligible",
        "report_only",
        "n_gate_eligible",
        "n_report_only",
        "report_only_reasons",
        "out_of_module_scope",
        "eligibility_rule_applied",
        "rulings_that_can_move_it",
        "status",
    ):
        assert key in part, key
    assert (part["n_gate_eligible"], part["n_report_only"]) == (
        N_GATED,
        N_REPORT_ONLY,
    )
    assert set(part["gate_eligible"]) == set(
        floor["power_cap"]["gate_eligible_tolerances_pp"]
    )
    assert set(part["report_only"]) == set(
        floor["power_cap"]["report_only_tolerance_above_t_max"]
    )
    assert set(part["gate_eligible"]).isdisjoint(part["report_only"])
    assert set(part["gate_eligible"]) | set(part["report_only"]) == set(
        art["cell_order"]
    )
    for cell, reason in part["report_only_reasons"].items():
        assert reason["reason"] == "tolerance_above_t_max"
        assert reason["tolerance_pp_would_be"] > T_MAX_PP
        assert (
            reason["tolerance_pp_would_be"]
            == floor["power_cap"]["report_only_tolerance_above_t_max"][cell][
                "tolerance_pp_would_be"
            ]
        )
    assert (
        part["out_of_module_scope"]
        == floor["power_cap"]["out_of_module_scope"]
    )
    assert len(part["out_of_module_scope"]["cells"]) == 6
    assert "pending the rulings named" in part["status"]
    assert set(part["rulings_that_can_move_it"]) == {
        "1_grammar_and_k_rev",
        "2_horizon_pricing",
        "3_age66_female_h1",
        "4_rounding_mode",
        "5_d0_estimand",
        "6_d1_editions",
    }
    surface = art["gated_surface"]
    assert (
        surface["tolerances_pp"]
        == floor["power_cap"]["gate_eligible_tolerances_pp"]
    )
    assert surface["reference_values_pp"] == {
        c: floor["reference_values_pp"]["gate_eligible"][c]
        for c in part["gate_eligible"]
    }


def test_every_alternative_row_is_cross_checked_against_the_floor():
    art = _artifact()
    alt = art["alternatives"]
    assert alt["every_row_cross_checked_against_the_floor"] is True
    rows = []
    for grammar in alt["grammar_and_k_sweep"]["by_grammar"].values():
        rows.extend(grammar["by_k"].values())
    rows.append(alt["horizon_aware_pricing"]["result"])
    assert len(rows) == 12 + 1
    for row in rows:
        assert (
            "gate_eligible_tolerances_pp"
            in row["cross_check_against_floor"]["fields_compared"]
        )
    # the floor's K x rounding rows carry counts and failure sets only
    rounding_rows = list(
        alt["draft_grammar_k_by_rounding_sweep"]["rows"].values()
    )
    assert len(rounding_rows) == 12
    for row in rounding_rows:
        compared = row["cross_check_against_floor"]["fields_compared"]
        assert "n_gate_eligible" in compared
        assert "deployed_v1_failing_cells" in compared
        assert "age66_female_h1_tolerance_pp" in compared
    rows.extend(rounding_rows)
    for row in rows:
        assert row["cross_check_against_floor"]["equal"] is True
        assert row["deployed_v1_n_failed"] == len(
            row["deployed_v1_failing_cells"]
        )
        assert row["ols_full_fit_window_n_failed"] == len(
            row["ols_full_fit_window_failing_cells"]
        )
    draft_row = alt["grammar_and_k_sweep"]["by_grammar"][
        "k_times_sd_abs_DRAFT"
    ]["by_k"]["K_2.0"]
    assert draft_row["partition_identical_to_draft"] is True
    assert draft_row["n_tolerances_differing_from_draft"] == 0
    assert draft_row["deployed_v1_n_failed"] == 6
    assert draft_row["ols_full_fit_window_n_failed"] == 20
    half_even = alt["rounding_mode_round_half_even"]
    assert half_even["n_cells_differing_from_draft"] == 1
    assert half_even["result"]["partition_identical_to_draft"] is True
    assert (
        alt["knife_edge_class"]["n_cells"],
        alt["knife_edge_class"]["n_gate_eligible"],
    ) == (
        13,
        9,
    )


def test_frontier_scan_and_deployed_finding_equal_the_floor():
    art = _artifact()
    floor = _floor()
    scan = art["faithful_candidate_oc_substitute"]
    assert scan["recomputed_here_and_equal_to_the_floor"] is True
    committed = floor["candidate_rules_on_the_draft_surface"]
    assert set(scan["rules"]) == set(committed["rules"])
    for name, rule in scan["rules"].items():
        assert rule["n_failed"] == committed["rules"][name]["n_failed"]
        assert (
            rule["failing_cells"] == committed["rules"][name]["failing_cells"]
        )
        assert (
            rule["max_abs_deviation_pp"]
            == committed["rules"][name]["max_abs_deviation_pp"]
        )
        assert (
            rule["mean_abs_deviation_pp_4dp_rounded_convention"]
            == committed["rules"][name]["mean_abs_deviation_pp"]
        )
    for key in (
        "post_hoc_best_of_forecast_class_envelope",
        "envelope_at_the_packet_window_grid",
        "envelope_over_the_v1_eleven_rules_including_degenerate",
        "envelope_over_all_rules_including_degenerate",
    ):
        for field in (
            "n_failed",
            "failing_cells",
            "max_abs_deviation_pp",
            "mean_abs_deviation_pp",
            "per_cell_pp",
        ):
            assert scan[key][field] == committed[key][field], (key, field)
    assert (
        scan["ols_window_sweep"]["windows_clearing_age66_female_h1"]
        == committed["ols_window_sweep"]["windows_clearing_age66_female_h1"]
    )
    assert scan["every_gate_eligible_cell_failed_by_some_rule"] is True
    finding = art["deployed_v1_finding"]
    ff = floor["deployed_v1_finding"]
    assert finding["failing_cells"] == ff["failing_cells"]
    assert finding["n_failed"] == 6
    for cell, entry in finding["per_failing_cell"].items():
        assert (
            entry["deviation_pp"]
            == ff["per_failing_cell"][cell]["deviation_pp"]
        )
        assert entry["margin_pp"] == ff["per_failing_cell"][cell]["margin_pp"]
        assert entry["margin_pp"] == round(
            entry["deviation_pp"] - entry["tolerance_pp"], 4
        )
    assert finding["recomputed_here_and_equal_to_the_floor"] is True
    assert "C8" in finding["reading_C8"]


def test_record_hygiene_r1_r2_r3_r5():
    art = _artifact()
    rh = art["record_hygiene"]
    assert "literally ABOVE" in rh["R1_report_footer"]
    # referee B F2: the leaf now states what the thresholds report's footer
    # actually covers, and that THIS sitting's report is cut literally.
    assert "145,412" in rh["R1_report_footer"]
    assert "145,436" in rh["R1_report_footer"]
    r2 = rh["R2_per_rule_mean_convention"]
    assert r2["rules_where_the_two_conventions_differ"] == ["ols_last_5"]
    row = r2["by_rule"]["ols_last_5"]
    assert (
        row["mean_of_4dp_rounded_per_cell_deviations_pp"],
        row["mean_of_unrounded_per_cell_deviations_pp"],
    ) == (0.5843, 0.5844)
    assert row["floor_artifact_carries"] == 0.5843
    r3 = rh["R3_corrected_build_report_section_0b"]
    assert len(r3["rows_missing_from_the_map"]) == 4
    assert r3["disposition"].startswith("LEFT AS IS")
    assert "2,291 / 4,861" in rh["R5_leaf_counts"]


def test_fit_isolation_scan_names_every_channel_and_hits_only_named_ones():
    art = _artifact()
    iso = art["fit_isolation"]
    assert iso["n_channels"] == 5
    paths = [c["path"] for c in iso["channels_carrying_the_held_out_actuals"]]
    assert paths[3] == "scripts/build_ssa_claim_ages.py"
    # referee B F1 (iii): gates.yaml named as a POST-FLIP channel
    assert paths[-1] == "gates.yaml"
    contract = iso["channels_carrying_the_held_out_actuals"][-1]
    assert contract["carries_the_rows"] == {
        "pre_flip": False,
        "post_flip": True,
    }
    assert contract["hit_by_this_scan"] is False
    assert "gates.yaml" in iso["required_draft_clause"]
    assert "n_files_scanned_note" in iso["scan"]
    assert iso["scan"]["every_hit_is_a_named_channel"] is True
    assert set(iso["scan"]["files_hit"]) == {
        "data/external/ssa_claim_ages_2023supplement.json",
        "runs/claiming_publication_floor_v1.json",
        "scripts/build_ssa_claim_ages.py",
    }
    for channel in iso["channels_carrying_the_held_out_actuals"]:
        if "pin" in channel:
            assert _sha(ROOT / channel["path"]) == channel["pin"]["sha256"]
    script = iso["channels_carrying_the_held_out_actuals"][3]
    assert script["line_numbers"] == {
        "male": [159, 160, 161],
        "female": [185, 186, 187],
    }
    assert "EVERY committed copy" in iso["required_draft_clause"]


def test_certification_scope_and_circularity_disclosure_present():
    art = _artifact()
    # referee A D3: the block says which of its strings the tests bind
    assert (
        "TEST-BOUND strings"
        in art["certification_scope"]["binding_of_this_text"]
    )
    assert (
        _block(art)["thresholds"]["certification_scope"][
            "binding_of_this_text"
        ]
        == art["certification_scope"]["binding_of_this_text"]
    )
    scope = art["certification_scope"]
    assert scope["horizon_C11"]["priced_horizons_years"] == [1, 2, 3]
    assert "2030+" in scope["horizon_C11"]["deployment_note"]
    assert len(scope["scored_surface_C13"]["gate_eligible_cells"]) == N_GATED
    assert (
        "claiming.py:396-405"
        in scope["scored_surface_C13"]["claims_exactly_the_scored_surface"]
    )
    assert len(scope["out_of_scope_C10"]["cells"]) == 6
    assert len(scope["what_a_pass_authorises_C14"]["does_not_authorise"]) >= 5
    disc = art["temporal_holdout_circularity_disclosure"]
    assert "C2_is_the_holdout_a_holdout" in disc
    assert "C3_does_the_temporal_holdout_de_circularise" in disc
    assert (
        "residual_circularity_disclosed"
        in disc["C3_does_the_temporal_holdout_de_circularise"]
    )


# --------------------------------------------------------------------------
# The DRAFT block
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
    assert frag["status_in_text"] == "draft_pending_referee_round"
    block = _block(art)
    assert block["id"] == "b2_claiming_age_distribution"
    assert block["status"] == "draft_pending_referee_round"
    assert block["locked"] is False
    assert block["floor_run"] == "runs/claiming_gate_floors_v1.json"
    assert block["floor_run_sha256"] == "<FILLED AT RATIFICATION>"
    assert block["derived_from_floor_sha256"] == FLOOR_COMMITTED[1]
    t = block["thresholds"]
    assert t["locked"] is False
    assert len(t["gated_surface"]["tolerances_pp"]) == N_GATED
    assert len(t["gated_surface"]["report_only_tolerance_above_t_max"]) == (
        N_REPORT_ONLY
    )
    assert len(t["gated_surface"]["derivations"]["rules"]) == N_GATED
    assert (
        t["gated_surface"]["tolerances_pp"]
        == art["gated_surface"]["tolerances_pp"]
    )
    assert (
        t["gated_surface"]["reference_values_pp"]
        == art["gated_surface"]["reference_values_pp"]
    )
    assert t["floor"]["does_not_establish"] == _floor()["does_not_establish"]
    assert set(t["open_rulings"]) == {str(i) for i in range(1, 9)}
    tests = t["gated_surface"]["derivations"]["binding_tests"]
    source = (ROOT / "tests" / "test_gates_derivations.py").read_text()
    for name in tests:
        assert f"def {name}(" in source, name


def test_draft_block_wording_audit_recomputes():
    art = _artifact()
    text = art["draft_gates_yaml_fragment"]["text"]
    flat = " ".join(text.split()).lower()
    counts = {
        w: len(re.findall(rf"\b{w}\b", flat)) for w in ("anchored", "aligned")
    }
    assert counts == {"anchored": 0, "aligned": 0}
    audit = art["wording_audit"]
    assert audit["forbidden_words"] == ["anchored", "aligned"]
    assert all(
        v["fragment"] == 0 for v in audit["forbidden_word_counts"].values()
    )
    without = {k: v for k, v in art.items() if k != "wording_audit"}
    flat_art = " ".join(json.dumps(without).split()).lower()
    assert all(
        len(re.findall(rf"\b{w}\b", flat_art)) == 0
        for w in ("anchored", "aligned")
    )
    assert audit["forbidden_words_absent_from_artifact"] is True
    assert audit["all_required_phrases_present"] is True
    assert audit["circularity_disclosure_present"] is True


def test_open_questions_and_flip_plan():
    art = _artifact()
    ids = [q["id"] for q in art["open_questions_for_the_ceremony"]]
    assert ids == [str(i) for i in range(1, 9)]
    names = [q["name"] for q in art["open_questions_for_the_ceremony"]]
    assert names == [
        "grammar_and_k_rev",
        "horizon_pricing",
        "age66_female_h1_knife_edge",
        "rounding_mode",
        "d0_estimand_construct",
        "d1_missing_2021_2022_editions",
        "pia_sequencing_constraint",
        "e1_clause",
    ]
    plan = art["flip_plan"]
    assert plan["marker"] == "GATE_B2_CLAIMING_BLOCK_LANDED"
    assert set(plan["files_carrying_the_marker"]) == {
        "tests/test_gates_derivations.py",
        "tests/test_claiming_gate_floors_v1.py",
    }
    pattern = re.compile(
        r"^GATE_B2_CLAIMING_BLOCK_LANDED = (True|False)$", re.M
    )
    for rel in plan["files_carrying_the_marker"]:
        found = pattern.findall((ROOT / rel).read_text())
        assert found == [str(GATE_B2_CLAIMING_BLOCK_LANDED)], rel
    # referee B F1 (ii): the post-flip disposition is recorded, and the
    # artifact is NOT re-emitted at flip (floor_run_sha256 = AS RATIFIED)
    assert plan["artifact_re_emitted_at_flip"] is False
    disp = plan["post_flip_test_dispositions"]
    assert "option (b)" in disp["decision"]
    assert "weakening_stated" in disp
    assert "gates_yaml_as_a_fit_isolation_channel" in disp
    d45 = art["packet_open_draft_decisions_d4_d5"]
    assert set(d45) == {
        "source",
        "d4_raw_column_surface",
        "d5_aggregate_statistic",
    }
    assert art["referee_record"]["co_location_disclosure_verbatim"].startswith(
        "**Disclosure"
    )


# --------------------------------------------------------------------------
# Reproduction
# --------------------------------------------------------------------------
def _strip_volatile(art: dict, *, landed: bool | None = None) -> dict:
    """Build-time metadata a rebuild legitimately moves: the elapsed
    time, the HEAD the artifact was built at (the parent of the commit
    carrying it), and the fit-isolation scan's file COUNT (the number of
    git-tracked text files, which grows with the tree; the scan's HITS
    are compared).

    MARKER-AWARE (referee B F1 (ii), option (b), recorded in the
    artifact's flip_plan.post_flip_test_dispositions): while the marker
    is False nothing else is stripped. Once the block has landed, the
    flip commit does NOT re-emit the artifact (its bytes stay AS
    RATIFIED), so the in-memory rebuild legitimately differs in exactly
    two places, which ``test_build_reproduces_the_committed_artifact``
    ASSERTS rather than compares: the fit-isolation scan gains the one
    hit the landed block creates (gates.yaml under signature (a) for the
    two 2020 rows), and ``gates_yaml_citations.byte_identical_to_
    working_tree`` reads False. Those two leaves are removed here."""
    if landed is None:
        landed = GATE_B2_CLAIMING_BLOCK_LANDED
    out = json.loads(json.dumps(art))
    out.pop("elapsed_seconds", None)
    out["revision_pins"].pop("populace_dynamics_sha", None)
    out["fit_isolation"]["scan"].pop("n_files_scanned", None)
    if landed:
        out["gates_yaml_citations"].pop("byte_identical_to_working_tree")
        scan = out["fit_isolation"]["scan"]
        scan["hits_by_signature"]["conditional_4dp"].pop("gates.yaml", None)
        scan["files_hit"] = [f for f in scan["files_hit"] if f != "gates.yaml"]
        out["fit_isolation"]["channels_carrying_the_held_out_actuals"][-1][
            "hit_by_this_scan"
        ] = False
    return out


def test_build_reproduces_the_committed_artifact():
    """The builder, run in memory, reproduces the committed bytes on every
    key but elapsed_seconds, the HEAD sha it was built at and the scan's
    file count. Post-flip (marker True) the artifact is NOT re-emitted --
    it stays AS RATIFIED -- and the rebuild's two flip-created
    differences are asserted to their expected values instead of being
    compared (referee B F1 (ii); the weakening is stated in
    _strip_volatile and in flip_plan.post_flip_test_dispositions)."""
    builder = _import_builder()
    fresh = builder.run(verbose=False)
    committed = _artifact()
    assert _strip_volatile(fresh) == _strip_volatile(committed)
    if GATE_B2_CLAIMING_BLOCK_LANDED:
        assert fresh["gates_yaml_citations"][
            "byte_identical_to_working_tree"
        ] is (False)
        scan = fresh["fit_isolation"]["scan"]
        assert scan["hits_by_signature"]["conditional_4dp"]["gates.yaml"] == [
            "female|2020",
            "male|2020",
        ]
        assert scan["files_hit"] == sorted(
            committed["fit_isolation"]["scan"]["files_hit"] + ["gates.yaml"]
        )
        assert scan["every_hit_is_a_named_channel"] is True
        assert scan["files_hit_not_named_as_a_channel"] == []
        assert (
            fresh["fit_isolation"]["channels_carrying_the_held_out_actuals"][
                -1
            ]["hit_by_this_scan"]
            is True
        )
    else:
        assert fresh["gates_yaml_citations"][
            "byte_identical_to_working_tree"
        ] is (True)
        assert "gates.yaml" not in fresh["fit_isolation"]["scan"]["files_hit"]
