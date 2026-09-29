"""The invented U2 pipeline, the runner's guards and the eventual artifact.

All ten rows on INVENTED data, the fixed U0 headline, the literal named
deltas, U2's rulings record, the unscored sensitivity, the F17
diagnostics; the runner's refusal of invented inputs on the registered
path; and the section 13 mirror of U1's
``test_nobody_leaves_poverty_under_the_cut`` for the eventual U2
artifact (skipped until it exists).  INVENTED DATA - NOT A COMPARISON.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import (
    DRY_RUN_HEADER,
    cohort,
    identity,
    invented,
    rows,
    runner,
    sources,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "runs" / "replication_boomers2004_1946_55_v1.json"
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)


def test_every_row_is_computed_with_the_u2_identity(u2_run):
    assert list(u2_run["rows"]) == list(rows.ROW_IDS)
    assert all(e["status"] == "computed" for e in u2_run["rows"].values())
    assert u2_run["labels"][0] == DRY_RUN_HEADER
    assert u2_run["headline"] == {
        "row": "U0",
        "rule": "fixed_u0_no_fallback",
        "fallback_row": None,
    }
    assert u2_run["comparator_column"] == "1946-55"
    assert u2_run["identity"] == identity.identity()
    assert u2_run["named_deltas"] == list(rows.NAMED_DELTAS)
    assert u2_run["rulings"]["decision_record"] == "d514"
    for entry in u2_run["rows"].values():
        table = entry["tabulation"]
        assert table["statistic_id"] == identity.STATISTIC_ID
        assert table["config"]["comparator_column"] == "1946-55"
        assert table["labels"][0] == DRY_RUN_HEADER
        cells = [c["cell"] for c in table["cells"]]
        assert cells[:15] == [
            "all",
            "women",
            "men",
            "married",
            "widowed",
            "divorced",
            "never_married",
            "women_married",
            "women_widowed",
            "women_divorced",
            "women_never_married",
            "men_married",
            "men_widowed",
            "men_divorced",
            "men_never_married",
        ]


def test_every_row_branch_changes_the_invented_outcome(u2_run):
    """Each one-field row moves something on invented data (branch check)."""

    counts = {
        row_id: entry["income_concept_counts"]
        for row_id, entry in u2_run["rows"].items()
    }
    assert counts["U2"]["n_ssi_offset_positive"] == 0
    assert counts["U0"]["n_ssi_offset_positive"] > 0
    assert counts["U3"]["n_ssi_new_positive"] > 0
    assert counts["U4"]["income_basis"].get("head_wife", 0) > 0
    assert counts["U7"]["n_employer_dc_added_positive"] > 0
    assert counts["U0"]["n_employer_dc_added_positive"] == 0
    assert counts["U5"]["n_retirement_account_income_removed_nonzero"] == 0
    assert any(
        key.startswith("psid_census_needs_standard")
        for key in counts["U8"]["threshold_cells"]
    )
    assert any(":" in key for key in counts["U10"]["threshold_cells"])
    assert u2_run["rows"]["U9"]["life_table"] == "ssa_period_2004"
    stats = {
        row_id: tuple(
            next(
                c for c in entry["tabulation"]["cells"] if c["cell"] == "all"
            )[key]
            for key in ("baseline_rate", "reform_rate", "delta")
        )
        for row_id, entry in u2_run["rows"].items()
    }
    # U4 moves both levels together on the invented code-90 family (the
    # head alone is poor before and after the cut): its levels differ.
    for row_id in ("U2", "U3", "U4", "U5", "U7", "U8"):
        assert stats[row_id] != stats["U0"], row_id
    assert stats["U4"][0] > stats["U0"][0]


def test_sensitivity_and_f17_diagnostics(u2_run):
    sensitivity = u2_run["sensitivities_unscored"]["real_interest_rate_0.02"]
    assert sensitivity["scored"] is False and sensitivity["row"] == "U0"
    f17 = u2_run["f17_diagnostics"]
    assert f17["row"] == "U0"
    assert set(f17["official_concept_poverty_rate"]["cells"]) == set(
        runner.OFFICIAL_CONCEPT_CELLS
    )
    components = f17["components"]
    assert components["target_id"] == "U2"
    assert set(components["social_security"]) == {
        "2014",
        "2016",
        "2018",
        "2020",
        "2022",
    }


def test_report_rows_not_computed_use_u2_reasons(u2_run):
    omitted = u2_run["report_rows_not_computed"]
    assert sum(len(v["rows"]) for v in omitted.values()) == 21
    for entry in omitted.values():
        assert "age 22" not in entry["reason"]
        assert "outside the U2 extension" in entry["reason"]


def test_registered_path_refuses_invented_inputs(u2_inputs, u2_params):
    registry = sources.RoleContext.from_registry()
    with pytest.raises(runner.U2RunError, match="loader"):
        runner.run_track_u2(
            u2_inputs,
            u2_params,
            data_provenance=ap.REGISTERED_REAL,
            role_context=registry,
            registration_pointer=POINTER,
        )


@pytest.mark.parametrize(
    "provenance, pointer, message",
    [
        ("bad", None, "data_provenance must be"),
        (ap.INVENTED, POINTER, "no registration pointer"),
        (ap.REGISTERED_REAL, "https://example.org/x", "issue #42 comment"),
        (ap.REGISTERED_REAL, POINTER, "loader"),
    ],
)
def test_input_guard_refusals(u2_inputs, provenance, pointer, message):
    with pytest.raises(runner.U2RunError, match=message):
        runner.check_inputs(
            u2_inputs, provenance, pointer, sources.RoleContext.declared()
        )


def test_declared_context_refused_for_registered_inputs(u2_inputs):
    sealed = cohort.replace_provenance(u2_inputs, kind="psid_files")
    with pytest.raises(runner.U2RunError, match="roles registry"):
        runner.check_inputs(
            sealed,
            ap.REGISTERED_REAL,
            POINTER,
            sources.RoleContext.declared(),
        )


def test_runner_refuses_a_partial_row_set(u2_inputs, u2_params, declared):
    partial = {k: v for k, v in rows.REGISTERED_ROWS.items() if k != "U7"}
    with pytest.raises(runner.U2RunError, match="ten rows"):
        runner.run_track_u2(
            u2_inputs,
            u2_params,
            data_provenance=ap.INVENTED,
            role_context=declared,
            row_set=partial,
        )


def test_runner_refuses_tampered_invented_inputs(
    u2_inputs, u2_params, declared
):
    changed = dataclasses.replace(
        u2_inputs, design=u2_inputs.design.assign(cluster=1)
    )
    # The invented label cannot be put back on changed frames ...
    with pytest.raises(cohort.U2CohortError, match="cannot label"):
        cohort.replace_provenance(
            changed,
            **{
                k: v
                for k, v in u2_inputs.provenance.items()
                if k != "input_frames_sha256"
            },
        )
    # ... and a hand-copied invented provenance carries no seal.
    copied = dataclasses.replace(
        changed,
        provenance={
            **u2_inputs.provenance,
            "input_frames_sha256": cohort.input_frames_sha256(changed),
        },
    )
    with pytest.raises(runner.U2RunError, match="not sealed"):
        runner.run_track_u2(
            copied,
            u2_params,
            data_provenance=ap.INVENTED,
            role_context=declared,
        )


def test_every_invented_variant_passes_the_regeneration_check(u2_inputs):
    for variant in invented.INVENTED_VARIANTS:
        inputs = invented.invented_variant(u2_inputs, variant)
        check = runner.check_inputs(
            inputs, ap.INVENTED, None, sources.RoleContext.declared()
        )
        assert check["invented_inputs"]["variant"] == variant
        assert check["invented_inputs"]["regenerated"] is True


def test_registered_run_records_only_the_registry_source_gate(
    u2_inputs, u2_params, committed_registries
):
    """Review finding 5: the invented declared source gate cannot be
    recorded on a registered run.  (The inputs are labelled psid_files
    without a loader seal only to pass the input guard; the gate check
    refuses next, before anything is computed.)"""

    labelled = cohort.replace_provenance(u2_inputs, kind="psid_files")
    declared_gate = sources.SourceGate(
        sources.INVENTED_DECLARED, committed_registries
    )
    with pytest.raises(runner.U2RunError, match="registry source gate"):
        runner.run_track_u2(
            labelled,
            u2_params,
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            source_gate=declared_gate,
        )
    with pytest.raises(runner.U2RunError, match="SourceGate"):
        runner.run_track_u2(
            labelled,
            u2_params,
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            source_gate="registry",
        )


def _cells_with_delta(node, path=""):
    stack = [(path, node)]
    while stack:
        path, node = stack.pop()
        if isinstance(node, dict):
            if "delta" in node and isinstance(node["delta"], (int, float)):
                yield path, node
            for key, value in node.items():
                stack.append((f"{path}/{key}", value))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                stack.append((f"{path}[{index}]", value))


@pytest.mark.parametrize("row", rows.ROW_IDS)
def test_nobody_leaves_poverty_under_the_cut_invented(u2_run, row):
    cells = list(_cells_with_delta(u2_run["rows"][row]["tabulation"]))
    assert cells
    for path, cell in cells:
        assert cell["delta"] >= -1e-9, (row, path)


@pytest.mark.parametrize("row", rows.ROW_IDS)
def test_nobody_leaves_poverty_under_the_cut(row):
    """Section 13: mirror of U1's artifact test for the eventual U2
    artifact."""

    if not ARTIFACT.exists():
        pytest.skip("the U2 registered artifact does not exist (not run)")
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    entry = artifact["rows"][row]
    cells = list(_cells_with_delta(entry["tabulation"]))
    assert cells, f"{row} records no cell with a change"
    for path, cell in cells:
        assert cell["delta"] >= -1e-9, (row, path)


def test_rows_join_only_the_inputs_the_cohort_was_built_from(
    u2_inputs, u0_cohort
):
    """Review 2, finding 1: the income rows and component rows carry the
    cohort's provenance and role context, so they refuse any other
    inputs -- another invented variant, or caller frames."""

    from populace_dynamics.uniform_cut_track_u2 import diagnostics

    variant = invented.invented_variant(
        u2_inputs, "spouse_slot_disagreement_2019"
    )
    scaled = cohort.replace_provenance(
        dataclasses.replace(
            u2_inputs,
            family_income={
                wave: frame.assign(
                    total_family_income=frame["total_family_income"] * 10
                )
                for wave, frame in u2_inputs.family_income.items()
            },
        ),
        kind="caller_frames",
    )
    for other in (variant, scaled):
        with pytest.raises(cohort.U2CohortError, match="built from"):
            cohort.income_rows(u0_cohort, other)
        with pytest.raises(cohort.U2CohortError, match="built from"):
            diagnostics.component_rows(u0_cohort, other)
    assert len(cohort.income_rows(u0_cohort, u2_inputs)) == len(
        u0_cohort.observations
    )
