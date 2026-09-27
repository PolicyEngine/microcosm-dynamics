"""The Track M dry-run script on a small INVENTED cohort (plan item M10).

The cohort is **INVENTED**; the parameters are the oracle's from the
policyengine-us checkout (``POPULACE_DYNAMICS_PE_US_DIR`` or
``~/PolicyEngine/policyengine-us``), the committed Census capture and the
committed COLA history.  No PSID file is read.  The test skips without the
checkout.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_PE_US = Path(
    os.environ.get(
        "POPULACE_DYNAMICS_PE_US_DIR", "~/PolicyEngine/policyengine-us"
    )
).expanduser()
pytestmark = pytest.mark.skipif(
    not (_PE_US / "policyengine_us").is_dir(),
    reason="needs a policyengine-us checkout (POPULACE_DYNAMICS_PE_US_DIR)",
)


def _script():
    path = ROOT / "scripts" / "track_m_dry_run.py"
    spec = importlib.util.spec_from_file_location("_track_m_dry_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def document(tmp_path_factory):
    out = tmp_path_factory.mktemp("dry")
    _script().main(["--output-dir", str(out), "--family-units", "80"])
    return (
        json.loads((out / "result.json").read_text()),
        (out / "RESULTS.md").read_text(),
    )


def test_the_outputs_are_headed_invented(document):
    result, markdown = document
    assert result["header"] == "INVENTED DATA - NOT A COMPARISON"
    assert markdown.startswith("# INVENTED DATA - NOT A COMPARISON\n")
    assert result["result"]["labels"][0] == result["header"]
    assert result["result"]["data_provenance"] == "invented"
    assert "d280" in result["result"]["disclosure"]


def test_every_row_and_cell_is_reported(document):
    result, markdown = document
    assert list(result["summary"]) == [f"MS{i}" for i in range(7)]
    for row, cells in result["summary"].items():
        assert len([key for key in cells if key != "y3"]) == 12, row
        assert f"| {row} |" in markdown
    parameters = result["result"]["parameters"]
    assert parameters["thresholds"]["kind"] == "census_capture"
    assert parameters["quarter_of_coverage"]["kind"] == "committed_capture"
    assert result["result"]["inputs"]["provenance_kind"] == "invented"
    # The invented PSID-shaped cohort ran through M4 and M5 as well.
    m45 = result["m4_m5"]
    assert list(m45["summary"]) == [f"MS{i}" for i in range(7)]
    assert m45["result"]["inputs"]["provenance_kind"] == "invented"
    assert m45["result"]["inputs"]["source"]["careers"] == (
        "min_benefit_track_m.careers"
    )
    assert m45["cohort_structure"]["persons"] > 0
    assert set(m45["cohort_structure"]["records_by_basis"]) <= {
        "old_age",
        "disability",
        "death",
    }
    assert "## The invented PSID-shaped cohort through M4 and M5" in markdown


def test_the_checks_record_every_guard(document):
    checks = document[0]["checks"]
    assert checks["specification_block_equals_code"]["consistent"]
    # The committed block lists no blocker since the registered-commit
    # edit (2026-09-27), so the gate passes it; a copy that still lists the
    # blockers it was ratified with is refused.
    assert not checks["the_committed_block_passes_the_specification_gate"][
        "refused"
    ]
    assert checks["the_committed_block_equals_a_ratified_unblocked_copy"][
        "passed"
    ]
    blocked = checks["a_ratified_copy_still_listing_blockers_is_refused"]
    assert blocked["refused"] and "still blocked by" in blocked["message"]
    for name in (
        "registration_package_m10_needs_the_comparator_seal_hash",
        "issue_42_registration_absent",
    ):
        assert name in blocked["message"], name
    assert not checks["threshold_years_all_captured"]["refused"]
    years = checks["threshold_years_needed_by_the_invented_cohort"]
    assert min(int(year) for year in years) >= 2003
    captured = checks["threshold_years_all_captured"]["captured"]
    assert captured[:7] == [1982, 1986, 1988, 1989, 1990, 1991, 1992]
    assert captured[7:] == list(range(1994, 2023))
    # 1998 is captured (d279, 2026-09-25), and 1990, which d430's
    # sensitivity needs (d279, 2026-09-26); 1993 and 1981 are not.
    for year in (1998, 1990):
        passes = checks[f"a_record_needing_{year}_passes_the_threshold_check"]
        assert not passes["refused"] and passes["threshold_year"] == year
    for year in (1993, 1981):
        early = checks[
            f"a_record_needing_{year}_is_refused_before_any_computation"
        ]
        assert early["refused"], year
        assert early["error"] == "ThresholdYearMissingError", year
        assert f"threshold years {year} (1 records)" in early["message"]
    assert checks["ms5_reads_benefit_implied_pias_and_ms0_none"]["passed"]
    for name in (
        "registered_path_refuses_invented_records",
        "psid_kind_records_refused_as_invented",
        "psid_kind_records_refused_without_the_42_pointer",
        "psid_kind_records_refused_with_a_pointer_under_a_blocked_block",
        "a_registered_subset_of_rows_is_refused",
        "registered_floor_seeds_cannot_be_changed",
        "psid_hashed_records_refused_outside_the_registered_run",
        "psid_hashed_records_refused_with_a_supplied_block",
        "psid_hashed_records_refused_without_the_42_pointer",
        "psid_hashed_records_refused_with_a_pointer_to_another_issue",
        "a_psid_hashed_cohort_cannot_be_marked_invented",
        "an_unconstrained_m4_cohort_needing_years_not_captured_is_refused",
    ):
        assert checks[name]["refused"], name
    assert "every registered row" in (
        checks["a_registered_subset_of_rows_is_refused"]["message"]
    )
    assert "still blocked by" in (
        checks[
            "psid_kind_records_refused_with_a_pointer_under_a_blocked_block"
        ]["message"]
    )
    # PSID-built records still need the issue #42 comment pointer.
    for name in (
        "psid_kind_records_refused_without_the_42_pointer",
        "psid_hashed_records_refused_without_the_42_pointer",
        "psid_hashed_records_refused_with_a_pointer_to_another_issue",
    ):
        assert "registration pointer" in checks[name]["message"], name
    # A supplied block is refused for records carrying PSID file hashes
    # although the gate would pass it: it is not the committed block.
    supplied = checks["psid_hashed_records_refused_with_a_supplied_block"]
    assert "supplied block" in supplied["message"]
    assert supplied["supplied_block_passes_the_gate"]
    # Every component exists, and the entry point's preflight passes the
    # committed block at the registered commit on a clean tree (a stand-in
    # git; nothing is written) and refuses each departure from that state.
    assert checks["entry_point_missing_components"] == []
    assert not checks["entry_point_preflight_passes_the_registered_state"][
        "refused"
    ]
    for name, fragment in (
        ("a_pointer_to_another_issue", "issue #42"),
        ("another_head", "is not the registered commit"),
        ("a_dirty_tree", "clean"),
        ("an_existing_output", "one-shot"),
        ("a_blocked_block", "still blocked by"),
    ):
        refusal = checks[f"entry_point_preflight_refuses_{name}"]
        assert refusal["refused"], name
        assert fragment in refusal["message"], name
    unconstrained = checks[
        "an_unconstrained_m4_cohort_needing_years_not_captured_is_refused"
    ]
    assert unconstrained["error"] == "ThresholdYearMissingError"
    assert "captured: 1982, 1986, 1988-1992, 1994-2022" in (
        unconstrained["message"]
    )
    # the refusal names exactly the years the draw needs and lacks
    missing = unconstrained["needed_years_not_captured"]
    assert missing
    named = unconstrained["message"].split(" are not in the capture")[0]
    assert sorted(int(y) for y in re.findall(r"\b(\d{4})\b", named)) == (
        missing
    )
    assert checks["m4_universe_equals_the_structural_funnel"]["passed"]


def test_the_plan_cases_match_section_16(document):
    """The M1 specification's section 16 table, recomputed (INVENTED)."""

    cases = document[0]["checks"]["plan_invented_cases"]
    expected = {
        # case: (M option 2, flag 2 G10/MS2, flag 4 G10/MS2, against 1)
        "A": (708.33, (True, True), (True, True), 34.84),
        "B": (0.0, (False, False), (False, False), -0.41),
        "C": (833.33, (True, False), (True, True), 5.76),
        "D": (674.24, (True, True), (True, True), 54.02),
        "H": (833.33, (True, False), (True, True), -0.12),
        "I": (583.33, (False, False), (True, True), -0.41),
    }
    for name, (minimum, two, four, relative) in expected.items():
        case = cases[name]
        assert case["minimum_option_2"] == minimum, name
        assert tuple(case["flag_option_2"].values()) == two, name
        assert tuple(case["flag_option_4"].values()) == four, name
        assert case["option_2_against_option_1_percent"] == relative, name
    assert cases["D"]["work_years_star"] == 27.27


def test_the_provenance_pins_the_specification_and_parameters(document):
    result, markdown = document
    provenance = result["provenance"]
    spec = provenance["m1_specification"]
    assert spec["path"] == "docs/design/minimum_benefits_comparison.md"
    assert len(spec["sha256"]) == 64
    assert provenance["census_thresholds"]["sha256"].startswith("288399c4")
    assert provenance["census_thresholds"]["path"] == (
        "data/external/census_poverty_thresholds_1982_2022.json"
    )
    qc = provenance["quarter_of_coverage"]
    assert qc["sha256"].startswith("6f964e8f")
    assert qc["captured_from_sha256"].startswith("12354a05")
    assert "not opened" in provenance["comparator_seal"]
    assert "section 18 item 3" in provenance["comparator_seal"]
    # the dry run records the committed block's version and status
    assert (spec["version"], spec["status"]) == (
        "m1-ratified-1",
        "ratified_frozen",
    )
    assert spec["sha256"] in markdown


def test_d430s_sensitivity_runs_on_both_invented_cohorts(document):
    """Cos d430's sensitivity (M1 sections 4c, 11 and 19) on the invented
    PSID-shaped cohorts: no difference on the default draw (every type
    item known), and MS0 under both readings, with the resting share and
    its bound, on a draw with receipt of unknown or "other" type before
    62.  The rows MS0-MS6 are the same with and without the sensitivity,
    and the registered path refuses without it."""

    result, markdown = document
    checks = result["checks"]
    for name in (
        "d430_rows_ms0_to_ms6_identical_with_and_without_the_sensitivity",
        "d430_default_draw_no_record_or_person_differs",
        "d430_draw_with_unknown_or_other_receipt_differs",
        "d430_share_gap_within_the_resting_share",
        "d430_no_window_year_earlier_under_the_sensitivity",
    ):
        assert checks[name]["passed"], name
    for name, fragment in (
        (
            "d430_a_registered_run_without_the_sensitivity_is_refused",
            "d430 sensitivity",
        ),
        (
            "d430_scored_records_under_the_sensitivity_reading_are_refused",
            "scored under the own-receipt reading",
        ),
        ("d430_a_sensitivity_of_another_universe_is_refused", "same"),
        ("d430_a_sensitivity_under_the_scored_reading_is_refused", "built"),
        (
            "d430_a_sensitivity_record_needing_1993_is_refused_first",
            "threshold years 1993 (1 records) are not in the capture",
        ),
    ):
        assert checks[name]["refused"], name
        assert fragment in checks[name]["message"], name
    # the sensitivity's threshold-year check passes a record needing 1990
    # on the real capture (captured 2026-09-26 for d430's sensitivity)
    passes = checks[
        "d430_a_sensitivity_record_needing_1990_passes_the_threshold_check"
    ]
    assert not passes["refused"] and passes["threshold_year"] == 1990
    assert 1990 in passes["needed_before_2003"]
    refused = checks["d430_a_sensitivity_record_needing_1993_is_refused_first"]
    assert refused["error"] == "ThresholdYearMissingError"
    identifier = "own_receipt_reading_d430"
    default = result["m4_m5"]["result"]["sensitivities"][identifier]
    assert default["scored"] is False
    assert (
        default["reclassification"]["worker_records_classified_differently"]
        == 0
    )
    drawn = result["m4_m5_own_receipt_sensitivity"]
    assert drawn["persons_changed_by_the_draw"]["share"] == 0.5
    entry = drawn["result"]["sensitivities"][identifier]
    assert all(not cell["scored"] for cell in entry["tabulation"]["cells"])
    assert list(drawn["summary"]) == [f"MS{i}" for i in range(7)]
    assert set(drawn["sensitivity_summary"]["cells"]) <= {
        "all",
        "men",
        "women",
    }
    counts = drawn["first_own_receipt_type_before_62"]
    assert counts["first_own_receipt_before_62_unknown_or_other"] > 0
    assert "## Cos d430's sensitivity on invented data (unscored)" in markdown
