"""Reproduction tests for ``runs/claiming_publication_floor_v1.json``.

The artifact is a REPORTED publication floor (reads no gate, changes no
gate): the cross-edition revision of SSA Statistical Supplement Table
6.B5.1, the DRAFT power-cap partition derived from it, the held-out
reference values, and the two holdout rules' out-of-sample scores. It
is pinned like the other ``runs/`` floors.

Two kinds of test, both always runnable -- they touch only committed
files (the two Supplement editions, ``runs/claiming_reference_v1.json``
and the artifact itself) and the build script. No PSID, no
policyengine-us, no engine.

* **Internal consistency.** Every stratum statistic recomputes from the
  two committed editions; every tolerance recomputes from the stated
  rule and knobs; the gate-eligible / report-only partition is exactly
  what the power cap implies; the reference values are the 2023
  edition's own conditional shares; the deployed-v1 finding recomputes
  from the per-cell block.
* **Cross-artifact identity.** The published-construct holdout numbers
  reproduce ``runs/claiming_reference_v1.json`` exactly, and the
  artifact stays REPORTED -- ``gates.yaml`` carries no
  ``gate_b2_claiming`` and this artifact must not imply one.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "claiming_publication_floor_v1.json"
REFERENCE_2023 = (
    ROOT / "data" / "external" / "ssa_claim_ages_2023supplement.json"
)
REFERENCE_2014 = (
    ROOT / "data" / "external" / "ssa_claim_ages_2014supplement.json"
)
CLAIMING_REFERENCE = ROOT / "runs" / "claiming_reference_v1.json"
GATES = ROOT / "gates.yaml"
SCRIPTS = ROOT / "scripts"

PUBLISHED_CATEGORIES = (
    "age62",
    "age63",
    "age64",
    "age65",
    "age66",
    "disability_conversion",
    "age67_69",
    "age70plus",
)
CONDITIONAL_CATEGORIES = tuple(
    name for name in PUBLISHED_CATEGORIES if name != "disability_conversion"
)
SEXES = ("female", "male")
HORIZON_OF_YEAR = {2020: 1, 2021: 2, 2022: 3}


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def _edition(path: Path) -> dict:
    return json.loads(path.read_text())


def _import_builder():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_claiming_publication_floor as builder

    return builder


def _conditional(row: dict) -> dict[str, float]:
    categories = row["categories"]
    total = sum(categories[name] for name in CONDITIONAL_CATEGORIES)
    return {
        name: 100.0 * categories[name] / total
        for name in CONDITIONAL_CATEGORIES
    }


def _published(row: dict) -> dict[str, float]:
    return {name: row["categories"][name] for name in PUBLISHED_CATEGORIES}


def _revisions(construct: str, years: list[int]) -> list[float]:
    doc_2014, doc_2023 = _edition(REFERENCE_2014), _edition(REFERENCE_2023)
    shares = _conditional if construct == "conditional" else _published
    out = []
    for sex in SEXES:
        for year in years:
            old = shares(doc_2014["data"][sex][str(year)])
            new = shares(doc_2023["data"][sex][str(year)])
            for name in old:
                out.append(abs(new[name] - old[name]))
    return out


# --------------------------------------------------------------------------
# Schema and reported-floor framing
# --------------------------------------------------------------------------
def test_schema_and_reported_not_gated():
    art = _artifact()
    assert art["schema_version"] == "claiming_publication_floor.v1"
    assert art["run"] == "claiming_publication_floor_v1"
    assert art["reported_not_gated"] is True
    assert "Changes no gate" in art["purpose"]
    assert art["gate_status"]["gates_yaml_block"] is None


def test_no_gate_b2_claiming_exists_in_gates_yaml():
    """The artifact must not be readable as a gate that does not exist."""
    assert "gate_b2_claiming" not in GATES.read_text()


def test_sources_are_pinned_to_the_bytes_on_disk():
    art = _artifact()
    for key, path in (
        ("edition_2023", REFERENCE_2023),
        ("edition_2014", REFERENCE_2014),
        ("claiming_reference_v1", CLAIMING_REFERENCE),
    ):
        pin = art["sources"][key]
        assert pin["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert pin["bytes"] == path.stat().st_size


def test_no_sampling_floor_quotes_the_reference_verbatim():
    art = _artifact()
    doc_2023, doc_2014 = _edition(REFERENCE_2023), _edition(REFERENCE_2014)
    block = art["no_sampling_floor"]
    assert (
        block["mbr_100_percent_note"]
        == doc_2023["provenance"]["mbr_100_percent_note"]
    )
    assert (
        block["mbr_100_percent_note_2014_edition"]
        == doc_2014["provenance"]["mbr_100_percent_note"]
    )
    assert block["table_notes"] == doc_2023["provenance"]["table_notes"]
    assert (
        block["table_notes_2014_edition"]
        == doc_2014["provenance"]["table_notes"]
    )
    for note in (
        block["mbr_100_percent_note"],
        block["mbr_100_percent_note_2014_edition"],
    ):
        assert "not a sample" in note


def test_the_revision_mechanism_sentence_is_verbatim_in_both_editions():
    """The floor's whole basis is SSA's own retroactive-revision note.

    The editions' FULL table notes are not identical -- the 2023 edition
    adds an Office of the Chief Actuary sentence -- so the artifact
    claims the narrower, true thing.
    """
    art = _artifact()
    block = art["no_sampling_floor"]
    sentence = block["retroactive_revision_sentence"]
    assert block["retroactive_revision_sentence_in_both_editions"] is True
    assert block["table_notes_identical_across_editions"] is False
    for path in (REFERENCE_2014, REFERENCE_2023):
        assert sentence in _edition(path)["provenance"]["table_notes"]


# --------------------------------------------------------------------------
# The revision floor recomputes from the two committed editions
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "key,construct,years",
    [
        (
            "published_settled_years",
            "published",
            list(range(1998, 2013)),
        ),
        ("published_terminal_year", "published", [2013]),
        (
            "conditional_settled_years",
            "conditional",
            list(range(1998, 2013)),
        ),
        ("conditional_terminal_year", "conditional", [2013]),
        (
            "published_all_overlap",
            "published",
            list(range(1998, 2014)),
        ),
        (
            "conditional_all_overlap",
            "conditional",
            list(range(1998, 2014)),
        ),
    ],
)
def test_each_stratum_recomputes_from_the_committed_editions(
    key, construct, years
):
    block = _artifact()["strata"][key]
    magnitudes = _revisions(construct, years)
    mean = sum(magnitudes) / len(magnitudes)
    variance = sum((m - mean) ** 2 for m in magnitudes) / len(magnitudes)
    assert block["n_cells"] == len(magnitudes)
    assert block["nonzero_cells"] == sum(1 for m in magnitudes if m > 0.0)
    assert block["mean_pp"] == pytest.approx(round(mean, 6))
    assert block["sd_pp"] == pytest.approx(round(variance**0.5, 6))
    assert block["max_pp"] == pytest.approx(round(max(magnitudes), 6))


def test_average_age_column_did_not_move():
    block = _artifact()["strata"]["average_age_column"]
    doc_2014, doc_2023 = _edition(REFERENCE_2014), _edition(REFERENCE_2023)
    moved = [
        (sex, year)
        for sex in SEXES
        for year in range(1998, 2014)
        if doc_2014["data"][sex][str(year)]["average_age"]
        != doc_2023["data"][sex][str(year)]["average_age"]
    ]
    assert block["n_rows"] == 32
    assert block["nonzero_rows"] == len(moved) == 0
    assert block["max_years"] == 0.0


def test_nonzero_cells_are_exactly_the_cells_that_moved():
    art = _artifact()
    doc_2014, doc_2023 = _edition(REFERENCE_2014), _edition(REFERENCE_2023)
    for key, listed in art["nonzero_revision_cells"].items():
        construct, _, stratum = key.partition("_")
        shares = _conditional if construct == "conditional" else _published
        years = [2013] if stratum == "terminal_year" else range(1998, 2013)
        expected = {
            f"{name}|{sex}|{year}"
            for sex in SEXES
            for year in years
            for name in shares(doc_2023["data"][sex][str(year)])
            if shares(doc_2023["data"][sex][str(year)])[name]
            != shares(doc_2014["data"][sex][str(year)])[name]
        }
        assert {row["cell"] for row in listed} == expected
        assert len(listed) == art["strata"][key]["nonzero_cells"]


def test_revision_is_a_terminal_year_effect():
    art = _artifact()
    assert art["finding"]["revision_is_a_terminal_year_effect"] is True
    published_terminal = art["strata"]["published_terminal_year"]
    assert published_terminal["nonzero_cells"] == published_terminal["n_cells"]
    assert art["strata"]["published_settled_years"]["nonzero_cells"] == 1


# --------------------------------------------------------------------------
# The DRAFT tolerance surface is machine-derived, not hand-picked
# --------------------------------------------------------------------------
def test_every_tolerance_recomputes_from_the_stated_rule_and_knobs():
    art = _artifact()
    cap = art["power_cap"]
    knobs = cap["knobs"]
    sd = knobs["revision_sd_terminal_pp"]
    for key, block in cap["derivations"].items():
        expected = round(
            knobs["k_rev"] * sd
            + abs(block["trend_pp_per_year"]) * block["horizon_years"]
            + knobs["rounding_pp"],
            block["rounding"],
        )
        assert block["tolerance_pp"] == expected, key
        _, _, horizon = key.split("|")
        assert int(horizon.lstrip("h")) == block["horizon_years"]


def test_sd_knob_is_the_measured_terminal_stratum_rounded():
    art = _artifact()
    knobs = art["power_cap"]["knobs"]
    measured = art["strata"]["conditional_terminal_year"]["sd_pp"]
    assert knobs["revision_sd_terminal_pp_full_precision"] == measured
    assert knobs["revision_sd_terminal_pp"] == round(measured, 4)


def test_sd_knob_rounding_check_names_its_sensitive_cells():
    check = _artifact()["power_cap"]["sd_knob_rounding_check"]
    assert check["partition_identical"] is True
    assert check["gate_eligibility_flips"] == []
    assert check["n_cells_with_a_different_tolerance"] == len(
        check["cells_with_a_different_tolerance"]
    )
    for key, block in check["cells_with_a_different_tolerance"].items():
        assert (
            block["tolerance_pp_at_rounded_sd"]
            != block["tolerance_pp_at_full_precision_sd"]
        ), key


def test_partition_is_exactly_what_the_power_cap_implies():
    cap = _artifact()["power_cap"]
    t_max = cap["knobs"]["t_max_pp"]
    gated = cap["gate_eligible_tolerances_pp"]
    report_only = cap["report_only_tolerance_above_t_max"]
    assert cap["n_gate_eligible"] == len(gated) == 34
    assert cap["n_report_only_tolerance_above_t_max"] == len(report_only) == 8
    assert set(gated) | set(report_only) == set(cap["derivations"])
    assert not set(gated) & set(report_only)
    for key, tolerance in gated.items():
        assert tolerance <= t_max, key
        assert cap["derivations"][key]["tolerance_pp"] == tolerance
    for key, block in report_only.items():
        assert block["tolerance_pp_would_be"] > t_max, key
        assert block["reason"] == "tolerance_above_t_max"


def test_conversion_cells_are_out_of_scope_not_demoted():
    cap = _artifact()["power_cap"]
    out_of_scope = cap["out_of_module_scope"]["cells"]
    assert len(out_of_scope) == 6
    for key in out_of_scope:
        assert key.startswith("disability_conversion|")
        assert key not in cap["gate_eligible_tolerances_pp"]
        assert key not in cap["report_only_tolerance_above_t_max"]
        assert key not in cap["derivations"]
    assert (
        cap["out_of_module_scope"]["reason"]
        == "conversion_flow_owned_by_di_surface"
    )


def test_reference_values_are_the_editions_own_conditional_shares():
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    values = {
        **art["reference_values_pp"]["gate_eligible"],
        **art["reference_values_pp"]["report_only"],
    }
    assert len(values) == 42
    for key, value in values.items():
        category, sex, horizon = key.split("|")
        year = next(
            y
            for y, h in HORIZON_OF_YEAR.items()
            if h == int(horizon.lstrip("h"))
        )
        expected = _conditional(doc["data"][sex][str(year)])[category]
        assert value == pytest.approx(round(expected, 4))
    assert set(art["reference_values_pp"]["gate_eligible"]) == set(
        art["power_cap"]["gate_eligible_tolerances_pp"]
    )


# --------------------------------------------------------------------------
# The holdout rules, and identity with the committed reference artifact
# --------------------------------------------------------------------------
def test_published_holdout_reproduces_claiming_reference_v1():
    art = _artifact()
    committed = json.loads(CLAIMING_REFERENCE.read_text())
    check = art["reproduces_claiming_reference_v1"]
    assert check["all_match"] is True
    for rule in ("nearest_year", "linear_trend"):
        theirs = committed["results"][rule]
        ours = art["holdout_rules"]["published"][rule]
        assert ours["max_abs_deviation"] == theirs["max_abs_deviation"]
        assert ours["mean_abs_deviation"] == theirs["mean_abs_deviation"]
        assert ours["rmse"] == theirs["rmse"]
        assert ours["n_cells"] == theirs["n_cells"] == 48
    # The pinned headline of the committed artifact, restated here so a
    # drift in either file fails loudly.
    assert art["holdout_rules"]["published"]["nearest_year"][
        "max_abs_deviation"
    ] == pytest.approx(3.2)


def test_conditional_holdout_spans_the_seven_category_surface():
    art = _artifact()
    for rule in ("nearest_year", "linear_trend"):
        block = art["holdout_rules"]["conditional"][rule]
        assert block["n_cells"] == 2 * 3 * 7 == 42
        cells = art["holdout_rules"]["per_cell"]["conditional"][rule]
        magnitudes = [abs(cell["deviation"]) for cell in cells]
        assert block["max_abs_deviation"] == pytest.approx(
            round(max(magnitudes), 4)
        )
        assert block["mean_abs_deviation"] == pytest.approx(
            round(sum(magnitudes) / len(magnitudes), 4)
        )


def test_every_holdout_cell_actual_matches_the_reference():
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    for construct, blocks in art["holdout_rules"]["per_cell"].items():
        shares = _conditional if construct == "conditional" else _published
        for rule, cells in blocks.items():
            for cell in cells:
                expected = shares(doc["data"][cell["sex"]][str(cell["year"])])[
                    cell["category"]
                ]
                assert cell["actual"] == pytest.approx(round(expected, 4)), (
                    construct,
                    rule,
                    cell,
                )
                assert cell["deviation"] == pytest.approx(
                    round(cell["predicted"] - cell["actual"], 4)
                )
                assert cell["horizon"] == HORIZON_OF_YEAR[cell["year"]]


# --------------------------------------------------------------------------
# Candidate rules and the deployed-v1 finding
# --------------------------------------------------------------------------
def test_deployed_v1_finding_is_reported_not_gated_and_names_its_cells():
    art = _artifact()
    finding = art["deployed_v1_finding"]
    scored = art["candidate_rules_on_the_draft_surface"]["rules"][
        "deployed_v1_nearest_year"
    ]
    assert finding["reported_not_gated"] is True
    assert "not a gate verdict" in finding["statement"]
    assert finding["n_gate_eligible_cells"] == 34
    assert finding["n_failed"] == scored["n_failed"] == 6
    assert finding["failing_cells"] == scored["failing_cells"]
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    for key, block in finding["per_failing_cell"].items():
        assert key in tolerances
        assert block["tolerance_pp"] == tolerances[key]


def test_deployed_v1_failures_recompute_from_the_conditional_holdout():
    """The deployed rule IS the nearest-year holdout rule, so its
    failures must be exactly the gate-eligible cells whose nearest-year
    deviation exceeds their tolerance."""
    art = _artifact()
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    cells = art["holdout_rules"]["per_cell"]["conditional"]["nearest_year"]
    failures = sorted(
        f"{cell['category']}|{cell['sex']}|h{cell['horizon']}"
        for cell in cells
        if f"{cell['category']}|{cell['sex']}|h{cell['horizon']}" in tolerances
        and abs(cell["deviation"])
        > tolerances[f"{cell['category']}|{cell['sex']}|h{cell['horizon']}"]
    )
    assert failures == art["deployed_v1_finding"]["failing_cells"]


def test_deviation_arithmetic_names_every_cell_the_two_paths_disagree_on():
    """The artifact scores the nearest-year rule twice under different
    rounding, so the same cell can carry two values (3.8086 in the
    holdout block, 3.8087 in the deployed finding). The disclosure must
    name exactly the cells that differ -- re-derived here from the
    committed edition, not read back from the block."""
    builder = _import_builder()
    doc_2023 = _edition(REFERENCE_2023)
    fit = builder._fit_series(doc_2023, "conditional")
    actuals = builder._actuals(doc_2023, "conditional")
    predict = builder._candidate_predictors(fit)["deployed_v1_nearest_year"][
        "predict"
    ]

    art = _artifact()
    block = art["deviation_arithmetic"]
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    rounded = {
        f"{cell['category']}|{cell['sex']}|h{cell['horizon']}": abs(
            cell["deviation"]
        )
        for cell in art["holdout_rules"]["per_cell"]["conditional"][
            "nearest_year"
        ]
    }

    expected = {}
    for key in tolerances:
        category, sex, horizon = key.split("|")
        horizon_n = int(horizon[1:])
        unrounded = round(
            abs(
                predict(category, sex, horizon_n)
                - actuals[(category, sex, horizon_n)]
            ),
            4,
        )
        if unrounded != rounded[key]:
            expected[key] = (rounded[key], unrounded)

    assert set(block["cells"]) == set(expected)
    assert block["n_cells_differing"] == len(expected) == 10
    assert block["n_cells_compared"] == len(tolerances) == 34
    for key, (path_r, path_u) in expected.items():
        recorded = block["cells"][key]
        assert recorded["rounded_prediction_path_pp"] == path_r
        assert recorded["unrounded_prediction_path_pp"] == path_u
        assert recorded["difference_pp"] == 0.0001


def test_no_gate_eligible_verdict_depends_on_which_arithmetic_is_used():
    """The disclosure's load-bearing claim: the two paths disagree by at
    most one 4-decimal ulp, and no cell sits that close to its
    tolerance -- so the failure set is the same either way."""
    art = _artifact()
    block = art["deviation_arithmetic"]
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]

    assert block["max_abs_difference_pp"] == 0.0001
    assert block["n_verdict_flips"] == 0
    assert block["verdict_flips"] == []
    assert block["verdict_identical_under_both_paths"] is True
    for recorded in block["cells"].values():
        assert recorded["exceeds_tolerance_either_way"] is True

    margin = block["closest_any_cell_comes_to_its_tolerance_pp"]
    assert margin > block["max_abs_difference_pp"]

    rounded = {
        f"{cell['category']}|{cell['sex']}|h{cell['horizon']}": abs(
            cell["deviation"]
        )
        for cell in art["holdout_rules"]["per_cell"]["conditional"][
            "nearest_year"
        ]
    }
    closest = min(
        abs(rounded[key] - tolerance) for key, tolerance in tolerances.items()
    )
    assert round(closest, 4) == margin

    failures_rounded = sorted(
        key
        for key, tolerance in tolerances.items()
        if rounded[key] > tolerance
    )
    assert failures_rounded == art["deployed_v1_finding"]["failing_cells"]


def test_the_two_paths_headline_numbers_are_both_reachable():
    """3.8087 in the deployed finding and 3.8086 in the holdout block
    are the same cell under the two arithmetics -- pin both so neither
    can drift into looking like a discrepancy again."""
    art = _artifact()
    cell = art["deviation_arithmetic"]["cells"]["age62|female|h1"]
    assert cell["unrounded_prediction_path_pp"] == 3.8087
    assert cell["rounded_prediction_path_pp"] == 3.8086
    assert art["deployed_v1_finding"]["max_abs_deviation_pp"] == 3.8087
    per_cell = art["holdout_rules"]["per_cell"]["conditional"]["nearest_year"]
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    gate_eligible_max = max(
        abs(entry["deviation"])
        for entry in per_cell
        if f"{entry['category']}|{entry['sex']}|h{entry['horizon']}"
        in tolerances
    )
    assert gate_eligible_max == 3.8086


def test_frontier_envelope_uses_forecast_rules_only():
    block = _artifact()["candidate_rules_on_the_draft_surface"]
    envelope = block["post_hoc_best_of_forecast_class_envelope"]
    forecast = sorted(
        name
        for name, rule in block["rules"].items()
        if rule["rule_class"] == "forecast"
    )
    assert envelope["rules_in_envelope"] == forecast
    assert all(
        block["rules"][name]["rule_class"] == "forecast"
        for name in envelope["rules_in_envelope"]
    )
    # The envelope is a lower bound: no rule beats it on any cell.
    for name in forecast:
        assert (
            block["rules"][name]["max_abs_deviation_pp"]
            >= envelope["max_abs_deviation_pp"]
        )


def test_every_gate_eligible_cell_is_failed_by_some_candidate():
    """No cell is vacuous."""
    block = _artifact()["candidate_rules_on_the_draft_surface"]
    assert block["every_gate_eligible_cell_failed_by_some_rule"] is True
    failed = {
        key
        for rule in block["rules"].values()
        for key in rule["failing_cells"]
    }
    assert failed == set(
        _artifact()["power_cap"]["gate_eligible_tolerances_pp"]
    )


def test_packet_reconciliation_records_the_measured_value():
    art = _artifact()
    differences = art["packet_reconciliation"]["differences"]
    assert differences
    for row in differences:
        assert row["packet_states"] != row["measured"]
    conditional = next(
        row
        for row in differences
        if "conditional_settled_years" in row["field"]
    )
    assert (
        conditional["measured"]
        == art["strata"]["conditional_settled_years"]["nonzero_cells"]
    )


# --------------------------------------------------------------------------
# Byte-level reproduction
# --------------------------------------------------------------------------
def test_build_reproduces_the_committed_artifact():
    builder = _import_builder()
    rebuilt = builder.build()
    committed = _artifact()
    assert set(rebuilt) == set(committed)
    for key in committed:
        if key == "build":
            continue
        assert rebuilt[key] == committed[key], key


def test_build_is_deterministic_across_runs():
    builder = _import_builder()
    first, second = builder.build(), builder.build()
    first.pop("build")
    second.pop("build")
    assert json.dumps(first, sort_keys=True) == json.dumps(
        second, sort_keys=True
    )
