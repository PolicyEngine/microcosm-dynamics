"""Bind the IC3 employer gate-block draft before it can lock.

ALWAYS-RUNNABLE (artifact tier): reads only the committed draft
block YAML and the design document. No microdata, no model, no
candidate run.

Closes blocking item B2 of the round-1 adversarial review, whose
finding was that the referee was asked to ratify prose plus PROPOSED
numbers while the actual ``gates.yaml`` text would first appear —
unrefereed — in the amendment PR, where transcription errors, silent
cell additions and derivation drift would never have been reviewed.

The tests here are the mutation pins the review asked for. Their
job is that a dropped, added, or renamed cell **fails**, rather than
passing silently into a locked contract:

* every gated family's cell list is pinned by exact count and
  membership;
* the calibration/gate partition is pinned as disjoint sets, with
  every gate registered on exactly one side (the round-1 defect was
  E6 and E7 appearing on neither);
* the demotions that round 1 forced — E1, E6, and both E9-stay
  statistics — are pinned as demoted, so a later edit cannot quietly
  re-gate a cell whose floor is degenerate or whose reference is a
  calibration target;
* the block cannot claim to be locked while its own prerequisites
  are unmet.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs" / "design" / "ic3_employer_gate_block_draft.yaml"
#: The registered design-document path. The rename to `ic3_` lands
#: with #230; the legacy name is listed only so a design document
#: arriving under it FAILS rather than leaving the agreement check
#: permanently skipped (the block's `design_filename_pin`).
DESIGN = ROOT / "docs" / "design" / "ic3_employer_gate_block.md"
LEGACY_DESIGN = ROOT / "docs" / "design" / "c3_employer_gate_block.md"

#: Exact gated cell counts. These numbers ARE the mutation pin: a
#: cell added or dropped anywhere changes one of them.
GATED_CELL_COUNTS = {
    "e2_sexage_rates": 16,  # 2 sexes x 8 age groups, margins excluded
    "e3_tenure_ecdf_by_age": 21,  # 3 supplement years x 7 BLS bands
    "e4_retention_by_age_sex": 12,  # 6 age bands x 2 sexes
    "e5_runs_by_age": 6,
    "e7_earns_relative_gradient_by_size": 5,
    "e8_nonemployment_by_age": 12,  # 6 age bands x 2 statistics
    "e9_j2j_earnings_change": 2,
    "e10_locked_psid_gates": 1,  # inherits; not enumerated here
    "e11_destination_size_margins": 5,
}

EXPECTED_CELLS = {
    "e2_sexage_rates": {
        f"sex{sex}_A{age:02d}" for sex in (1, 2) for age in range(1, 9)
    },
    "e3_tenure_ecdf_by_age": {
        f"{year}|{band}"
        for year in (2020, 2022, 2024)
        for band in (
            "16_19",
            "20_24",
            "25_34",
            "35_44",
            "45_54",
            "55_64",
            "65_200",
        )
    },
    "e4_retention_by_age_sex": {
        f"{age}|sex{sex}"
        for age in ("16_24", "25_34", "35_44", "45_54", "55_64", "65_99")
        for sex in (1, 2)
    },
    "e5_runs_by_age": {
        "16_24",
        "25_34",
        "35_44",
        "45_54",
        "55_64",
        "65_99",
    },
    "e7_earns_relative_gradient_by_size": {
        f"firmsize{size}" for size in range(1, 6)
    },
    "e8_nonemployment_by_age": {
        f"{age}|{stat}"
        for age in ("16_24", "25_34", "35_44", "45_54", "55_64", "65_99")
        for stat in ("any_nonemp", "long_nonemp")
    },
    "e9_j2j_earnings_change": {"median_log_change", "iqr_log_change"},
    "e10_locked_psid_gates": {"inherits_locked_gate_1_cells"},
    "e11_destination_size_margins": {
        f"firmsize{size}" for size in range(1, 6)
    },
}

ARTIFACT_SHA256 = {
    "runs/sipp_spell_floors_v1.json": "0110366a37a46fcc12b9a5665f3e6d5ea4c99fd2cabc4bf8cfc3fa8719890faf",
    "runs/tenure_floors_v1.json": "afbbb9ba38e0c69e78d94bd854c064dfae980f398092904b87b59a526a78e015",
    "runs/sipp_e8_e9_floors_v1.json": "28515717e83824056708a491b2702089cb439d5369deaff480f391c6f8862aa2",
    "runs/employer_firm_floors_v1.json": "eb58474b42166d51ccbe80a1c58d33ffb8a60a4a5ac097290fecc6c2a8b92f17",
}

#: Demoted by round 1. Re-gating any of these silently is the
#: failure mode this set exists to prevent.
MUST_STAY_REPORT_ONLY = {
    "e1_size_margin_and_sector_cross",  # B1: function of calibration targets
    "e6_size_margin_and_sector_cells",  # B1: linear functional of targets
    "e9_stay_median",  # degenerate floor
    "e9_stay_iqr",  # degenerate floor (B5)
    "e9_transition_rates",  # entry/exit/j2j/stay: on a partition side
    "firm_size_conditional_cells",  # no truth frame, permanent
    "e11_origin_x_destination_detail",  # one YoY pair per cell
}


@pytest.fixture(scope="module")
def block() -> dict:
    return yaml.safe_load(DRAFT.read_text(encoding="utf-8"))["gates"][
        "employer"
    ]


def _assert_contract_integrity(candidate: dict) -> None:
    """Fail closed on every mutation that could imply a premature lock."""
    assert candidate["locked"] is False
    assert candidate["status"] == "draft_round_1_continuing_blocked"
    assert candidate["design_commit"] == "PENDING"
    assert candidate["threshold_policy"]["status"] == "REFEREE_PENDING"
    assert candidate["scoring_frame"]["floor_scale_assertion"]["status"] == (
        "RECORDED_NOT_SATISFIED"
    )
    assert set(candidate["lock_blockers"]) == {
        "person_side_raw_input_sha256_and_measurement_environment",
        "e9_exact_distinct_person_population",
        "scoring_frame_floor_scale_resolution",
        "referee_choices_and_verification",
        "design_commit_and_required_merge_commits",
        "crosswave_and_seam_artifact_promotions",
    }
    assert candidate["evidence_provenance"][
        "person_side_raw_input_status"
    ] == ("BLOCKED_STRICT_STAGING")
    assert (
        candidate["evidence_provenance"]["artifact_sha256"] == ARTIFACT_SHA256
    )
    assert set(candidate["partition"]["gate_cells"]) == set(
        candidate["families"]
    )
    for name, expected in EXPECTED_CELLS.items():
        assert set(candidate["families"][name]["cells"]) == expected
    for name in (
        "e2_sexage_rates",
        "e7_earns_relative_gradient_by_size",
        "e11_destination_size_margins",
    ):
        assert candidate["families"][name]["floor_basis"] == "REFEREE"
        assert candidate["families"][name]["referee_status"] == "PENDING"
    assert candidate["families"]["e9_j2j_earnings_change"][
        "gate_eligibility"
    ].startswith("BLOCKED_")
    assert candidate["e12"]["status"] == "DEFERRED"
    assert (
        "certifies no person-employer link"
        in candidate["families"]["e11_destination_size_margins"][
            "certification_scope"
        ]
    )


def test_block_is_not_locked_and_edits_no_gate(block):
    _assert_contract_integrity(block)
    assert block["locked"] is False
    assert block["status"].startswith("draft")
    # The draft must never carry a concrete design_commit: it is
    # concretized only at the flip.
    assert block["design_commit"] == "PENDING"


def test_gated_cell_counts_are_pinned(block):
    families = block["families"]
    actual = {name: len(fam["cells"]) for name, fam in families.items()}
    assert actual == GATED_CELL_COUNTS


def test_every_gated_family_is_registered_in_the_partition(block):
    """The round-1 defect: E6 and E7 appeared on neither side."""
    families = set(block["families"])
    gate_cells = set(block["partition"]["gate_cells"])
    assert families == gate_cells


def test_partition_sides_are_disjoint(block):
    partition = block["partition"]
    gate = set(partition["gate_cells"])
    report = set(partition["report_only"])
    deferred = set(partition["deferred"])
    fitting = set(partition["fitting_consumes"])
    assert gate.isdisjoint(report)
    assert gate.isdisjoint(deferred)
    assert report.isdisjoint(deferred)
    # Nothing consumed by fitting may appear as a gated cell.
    assert gate.isdisjoint(fitting)


def test_round_1_demotions_cannot_be_silently_reverted(block):
    report_only = set(block["partition"]["report_only"])
    assert MUST_STAY_REPORT_ONLY <= report_only
    # And none of them may reappear as a gated family.
    assert MUST_STAY_REPORT_ONLY.isdisjoint(set(block["families"]))


def test_the_only_quantifier_binds_more_than_microcalibrate(block):
    """#192's hazards calibrate to QWI/J2J; that consumer was
    unregistered, which left the E2 and E11 holdouts unenforceable."""
    text = block["partition"]["only_quantifier"]
    for stage in ("microcalibrate", "hazard", "hyperparameter", "raking"):
        assert stage in text
    assert "whether or not it is called calibration" in text


def test_the_deterministic_function_corollary_is_registered(block):
    corollary = block["partition"]["deterministic_function_corollary"]
    assert "BY NAME" in corollary
    assert "linear functional" in corollary


def test_every_gated_family_cites_a_floor_or_declares_why_not(block):
    for name, family in block["families"].items():
        if family["floor_run"] is None:
            # Only E10 may lack a floor: it re-scores locked cells.
            assert name == "e10_locked_psid_gates"
            continue
        assert family["floor_run"].startswith("runs/")
        assert family["floor_run"].endswith("_v1.json")


def test_no_gated_family_rests_on_a_degenerate_floor(block):
    """B5's rule: a hand-set number may not be the whole gate.

    E9-stay was the violation — its IQR floor is 0.0/0.0 like its
    median, so 'IQR-only' was 100% the hand-set 0.02.
    """
    families = block["families"]
    assert "e9_stay" not in families
    assert "stay" not in families["e9_j2j_earnings_change"]["floor_path"]


def test_e11_carries_its_demotion_condition(block):
    condition = block["partition"]["e11_condition"]
    assert "J2JOD" in condition
    assert "no further referee round" in condition


def test_scoring_frame_registers_split_machine_fraction_and_seed(block):
    """S2: none of these were registered in the prose draft."""
    frame = block["scoring_frame"]["sipp_holdout"]
    assert frame["split_unit"] == "person"
    assert 0 < frame["holdout_fraction"] < 1
    assert isinstance(frame["seed"], int)
    assert frame["split_machine"]
    assert "disjoint" in frame["leakage_rule"]


def test_floor_scale_gap_is_recorded_as_unsatisfied(block):
    """S2's other half. Honest status beats a silent assertion."""
    scale = block["scoring_frame"]["floor_scale_assertion"]
    assert scale["status"] == "RECORDED_NOT_SATISFIED"
    assert scale["tolerance"] == "REFEREE"


def test_k_basis_states_the_locked_band_honestly(block):
    """S1: the band is 1.8-8, and two locked ks sit below 4."""
    basis = block["threshold_policy"]["k_basis"]
    assert "1.8-8" in basis
    assert "POLICY CHOICE" in basis
    # The seed counts are NOT uniform across the SIPP side, and the
    # earlier "5 seeds" sentence pinned a misstatement of the E8/E9
    # artifact, whose method string says seeds 0-19.
    assert "5 seeds (0-4)" in basis
    assert "20 seeds (0-19)" in basis


def test_e3_registers_a_per_year_floor_rule(block):
    """The count pin may not harden an unwritten derivation rule.

    Round 1's draft pinned 7 age-band cells while the #230 design
    defines age bands x supplement years, and `floor_path` carried a
    free `<year>` placeholder with no rule saying which year's floor
    derives the threshold. Both halves are pinned here.
    """
    family = block["families"]["e3_tenure_ecdf_by_age"]
    years = {cell.split("|")[0] for cell in family["cells"]}
    bands = {cell.split("|")[1] for cell in family["cells"]}
    assert years == {"2020", "2022", "2024"}
    assert len(bands) == 7
    assert len(family["cells"]) == len(years) * len(bands)
    assert family["derivations"]["floor_selection"] == "per_cell_own_year"
    assert "NOT pooled" in family["year_rule"]


def test_reweighting_targets_the_full_frame_including_the_seam(block):
    """The seam is the audit's risk locus, not an excluded tail.

    Restricting the target population to the within-wave part would
    make `seam_vs_within_indicator` — one of this block's own
    observables — constant, and silently drop it from the propensity
    model.
    """
    rw = block["linkage_qc"]["reweighting"]
    population = rw["target_reference_population"]
    assert "384,747" in population
    assert "10,828" in population
    assert "395,575" in population
    assert "seam_vs_within_indicator" in rw["observables"]


def test_thin_rules_cover_the_pair_unit_families(block):
    """Pairs are reported, but E9 eligibility needs distinct people."""
    thin = block["threshold_policy"]["thin_rules"]
    assert thin["sipp_side_min_persons"] == 200
    assert thin["sipp_side_min_pairs_reporting"] == 200
    family = block["families"]["e9_j2j_earnings_change"]
    assert (
        "exact distinct person count is not derivable"
        in family["thinnest_gated_cell_note"]
    )
    assert family["gate_eligibility"].startswith("BLOCKED_")


def test_e9_declares_its_linkage_status(block):
    """It gates at first lock while being job-ID-derived; silence
    on `linkage_prerequisite` was the round-1 gap."""
    family = block["families"]["e9_j2j_earnings_change"]
    assert family["linkage_prerequisite"] is True
    assert "6.4" in family["linkage_note"]
    assert block["linkage_qc"]["first_lock_scope"] == (
        "e4_e5_sipp_internal_only"
    )


def test_the_holdout_reverses_the_floor_scale_direction(block):
    """A 0.20 holdout is noisier than the half-split basis, so the
    artifacts' sqrt(2) conservatism note runs the wrong way."""
    scale = block["scoring_frame"]["floor_scale_assertion"]
    note = scale["holdout_reverses_the_ratio"]
    assert "ANTI-conservative" in note
    assert scale["status"] == "RECORDED_NOT_SATISFIED"


def test_the_holdout_seed_is_not_claimed_to_parameterize_the_split(block):
    frame = block["scoring_frame"]["sipp_holdout"]
    assert "salted hash" in frame["seed_note"] or (
        "salt" in frame["seed_note"]
    )
    assert "consumes no RNG stream" in frame["seed_note"]


def test_linkage_reweighting_is_instantiated(block):
    """B4: ADR 0004 §3 was dropped entirely from the prose draft."""
    rw = block["linkage_qc"]["reweighting"]
    assert rw["clustering"] == "worker"
    assert "seam_vs_within_indicator" in rw["observables"]
    # The numerics stay referee items, registered as such.
    for slot in (
        "propensity_spec",
        "overlap_balance_tolerance",
        "trimming_percentile",
        "operative_version",
    ):
        assert rw[slot] == "REFEREE"
    assert "weighted AND unweighted" in rw["publication_rule"]


def test_linkage_failure_never_weakens_e10(block):
    rule = block["families"]["e10_locked_psid_gates"]["hard_rule"]
    assert "NEVER WEAKENS E10" in rule


def test_ceremony_requires_merges_and_pinning(block):
    """B3: a block whose normative ADR is a branch file is not locked."""
    ceremony = block["ceremony"]
    merges = " ".join(ceremony["merges_required_before_amendment"])
    assert "#224" in merges
    assert "#277" in merges
    # The controlling design document must land before the block
    # that points at it can reach its amendment PR.
    assert "#230" in merges
    assert "AT ITS MERGE COMMIT" in ceremony["artifact_pinning"]
    assert ceremony["referee_verification_required"] is True
    assert ceremony["no_candidate_runs_before_lock"] is True


def test_the_block_states_what_it_cannot_certify(block):
    """The paper's rule: misses publish as prominently as hits."""
    not_certified = block["not_certified"]
    assert (
        "E2, E7 and E11-margins ONLY"
        in (not_certified["firm_side_gating_is_thin"])
    )
    assert "PERMANENTLY" in not_certified["imputed_band_conditioned_cells"]
    assert "Phase-2 no-go" in not_certified["e12_not_gated"]


def test_the_design_document_is_at_the_registered_path(block):
    """A design doc under the legacy name would silently disable the
    agreement check below and leave `design:` stale — the fragility
    the block's `design_filename_pin` records."""
    assert block["design"] == "docs/design/ic3_employer_gate_block.md"
    assert not LEGACY_DESIGN.exists(), (
        "the design document is at the unregistered legacy path "
        f"{LEGACY_DESIGN.name}; #230 renames it to {DESIGN.name}, "
        "which is the only name `design:` may carry."
    )


def test_draft_and_design_document_agree_on_the_demotions(block):
    """The YAML and the prose must not drift apart.

    B2 exists because the block text and the document the referee
    read were different artifacts. Pinning their agreement is the
    point, not a nicety.
    """
    design = DESIGN.read_text(encoding="utf-8")
    # The design doc must not still advertise E1/E6 as gated.
    assert "does not gate at first" in design
    assert "E2, E7 and E11-margins are firm-side" in design
    assert "BLOCKED_STRICT_STAGING" in design
    assert "certifies no person link" in design
    assert "strong E12 is **deferred**" in design


def test_exact_composed_heads_are_pinned_and_ancestral(block):
    assert block["composed_heads"] == {
        "master": "691901f2915865fceb906f1dc5f36c913a5e2675",
        "ic_naming_root_pr_277": "c5b4d11f1b3bd6b34a3de8ea1a1c8d72e6777ee0",
        "person_side_floors_pr_212": "211152bb506e08b0a8b39dcae1c255365a71df0d",
        "firm_side_floors_pr_223": "34a70fc8c809d23b4643588ca228565b1c7b6513",
        "controlling_design_pr_230": "037b43faec5e8b46f9d92a295ced792e602e5b6f",
    }


def test_artifact_provenance_and_cell_populations_are_real(block):
    pins = block["evidence_provenance"]["artifact_sha256"]
    assert pins == ARTIFACT_SHA256
    for relative, expected in ARTIFACT_SHA256.items():
        assert (
            hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            == expected
        )

    firm = json.loads((ROOT / "runs/employer_firm_floors_v1.json").read_text())
    e2 = firm["e2"]["by_sex_age"]["cells"]
    for cell in EXPECTED_CELLS["e2_sexage_rates"]:
        assert e2[cell]["min_denominator_jobs"] >= 10_000
        assert e2[cell]["thin"] is False
    for cell in EXPECTED_CELLS["e7_earns_relative_gradient_by_size"]:
        assert (
            firm["e6_e7"]["by_firmsize_all_industry"][cell][
                "min_denominator_jobs"
            ]
            >= 10_000
        )
    for cell in EXPECTED_CELLS["e11_destination_size_margins"]:
        assert cell in firm["e11"]["destination_size_margin"]

    spells = json.loads((ROOT / "runs/sipp_spell_floors_v1.json").read_text())
    assert (
        set(spells["e4_retention_by_age_sex"])
        == EXPECTED_CELLS["e4_retention_by_age_sex"]
    )
    assert set(spells["e5_runs_by_age"]) == EXPECTED_CELLS["e5_runs_by_age"]
    assert not any(
        cell["thin"] for cell in spells["e4_retention_by_age_sex"].values()
    )
    assert not any(cell["thin"] for cell in spells["e5_runs_by_age"].values())

    e8e9 = json.loads((ROOT / "runs/sipp_e8_e9_floors_v1.json").read_text())
    j2j = e8e9["e9_transitions"]["earnings_change"]["j2j"]
    assert j2j["pairs_unweighted"] == 545
    assert "persons_unweighted" not in j2j
    assert (
        "FOLLOW_UP_REQUIRED"
        in e8e9["promotion_integrity"]["e9_distinct_person_count_status"]
    )


def test_current_and_future_ceremony_paths_are_not_conflated(block):
    ceremony = block["ceremony"]
    for relative in ceremony["current_composed_evidence"]:
        assert (ROOT / relative).is_file()
    future = set(ceremony["pre_lock_artifacts_required"])
    assert "runs/crosswave_jobid_check_v1.json" in future
    assert "runs/seam_reconciliation_v1.json" in future
    assert not (ROOT / "runs/crosswave_jobid_check_v1.json").exists()
    assert not (ROOT / "runs/seam_reconciliation_v1.json").exists()
    assert "crosswave_and_seam_artifact_promotions" in block["lock_blockers"]


@pytest.mark.parametrize(
    "mutation",
    (
        "lock",
        "drop_cell",
        "rename_cell",
        "partition_drift",
        "artifact_digest_drift",
        "remove_raw_blocker",
        "premature_floor_choice",
        "promote_e9",
        "expand_e11_claim",
        "promote_e12",
    ),
)
def test_contract_mutations_fail_closed(block, mutation):
    candidate = copy.deepcopy(block)
    if mutation == "lock":
        candidate["locked"] = True
    elif mutation == "drop_cell":
        candidate["families"]["e2_sexage_rates"]["cells"].pop()
    elif mutation == "rename_cell":
        candidate["families"]["e4_retention_by_age_sex"]["cells"][0] = (
            "renamed"
        )
    elif mutation == "partition_drift":
        candidate["partition"]["gate_cells"].remove(
            "e7_earns_relative_gradient_by_size"
        )
    elif mutation == "artifact_digest_drift":
        candidate["evidence_provenance"]["artifact_sha256"][
            "runs/tenure_floors_v1.json"
        ] = "0" * 64
    elif mutation == "remove_raw_blocker":
        candidate["lock_blockers"].remove(
            "person_side_raw_input_sha256_and_measurement_environment"
        )
    elif mutation == "premature_floor_choice":
        candidate["families"]["e11_destination_size_margins"][
            "floor_basis"
        ] = "ex_pandemic"
    elif mutation == "promote_e9":
        candidate["families"]["e9_j2j_earnings_change"]["gate_eligibility"] = (
            "ELIGIBLE"
        )
    elif mutation == "expand_e11_claim":
        candidate["families"]["e11_destination_size_margins"][
            "certification_scope"
        ] = "certifies worker sorting"
    elif mutation == "promote_e12":
        candidate["e12"]["status"] = "GATED"
    with pytest.raises(AssertionError):
        _assert_contract_integrity(candidate)


def test_naming_uses_the_interface_contract_prefix():
    """A bare C1/C2 in gates.yaml means the LOCKED gate_w1
    fingerprints. This block must never use the colliding form."""
    text = DRAFT.read_text(encoding="utf-8")
    body = text.split("# NAMING.")[1].split("\n\n", 1)[1]
    import re

    # Case-insensitive: the colliding gates.yaml fingerprint keys are
    # lowercase (`fingerprints.c1`), and a `c3_`-prefixed design path
    # is exactly the drift this pin should catch.
    assert not re.search(r"\bC[123]\b", body, re.IGNORECASE)
    assert not re.search(r"\bc[123]_", body)
