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
* **Independent re-derivation (v2).** Every OLS trend, every holdout
  prediction, every alternative-grammar partition, the horizon-aware
  partition, the settle-age strata, the widened forecast envelope, the
  OLS window sweep, the knife-edge class and the exact tie are
  recomputed here with the test module's OWN arithmetic from the two
  committed editions -- not read back through the builder -- so a
  builder edit that moved any of them fails loudly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
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


FIT_YEARS = tuple(range(1998, 2020))
HOLDOUT = {1: 2020, 2: 2021, 3: 2022}
T_MAX = 3.0


def _ols(xs, ys):
    """The test module's own closed-form OLS (not the builder's)."""
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den
    return slope, mean_y - slope * mean_x


def _series(doc, construct, category, sex):
    shares = _conditional if construct == "conditional" else _published
    return [shares(doc["data"][sex][str(y)])[category] for y in FIT_YEARS]


def _actual(doc, construct, category, sex, horizon):
    shares = _conditional if construct == "conditional" else _published
    return shares(doc["data"][sex][str(HOLDOUT[horizon])])[category]


def _own_trends(doc):
    return {
        (c, s): round(_ols(FIT_YEARS, _series(doc, "conditional", c, s))[0], 4)
        for s in SEXES
        for c in CONDITIONAL_CATEGORIES
    }


def _own_tolerance(term, trend, horizon, rounding_pp, mode=ROUND_HALF_UP):
    exact = (
        Decimal(repr(term))
        + Decimal(repr(abs(trend))) * horizon
        + Decimal(repr(rounding_pp))
    )
    return float(exact.quantize(Decimal("0.01"), rounding=mode)), exact


def _own_partition(doc, term_by_h, rounding_pp):
    trends = _own_trends(doc)
    gated, report_only = {}, {}
    for s in SEXES:
        for c in CONDITIONAL_CATEGORIES:
            for h in (1, 2, 3):
                tol, _ = _own_tolerance(
                    term_by_h[h], trends[(c, s)], h, rounding_pp
                )
                (gated if tol <= T_MAX else report_only)[f"{c}|{s}|h{h}"] = tol
    failures = sorted(
        k
        for k, tol in gated.items()
        if abs(
            _series(doc, "conditional", *k.split("|")[:2])[-1]
            - _actual(
                doc, "conditional", *k.split("|")[:2], int(k.split("|")[2][1:])
            )
        )
        > tol
    )
    return gated, report_only, failures


def _own_ols_window_predict(doc, construct, window):
    def predict(category, sex, horizon):
        ys = _series(doc, construct, category, sex)[-window:]
        slope, intercept = _ols(FIT_YEARS[-window:], ys)
        return intercept + slope * (FIT_YEARS[-1] + horizon)

    return predict


def _own_damped_predict(doc, construct, window, delta):
    def predict(category, sex, horizon):
        series = _series(doc, construct, category, sex)
        slope, _ = _ols(FIT_YEARS[-window:], series[-window:])
        return series[-1] + delta * slope * horizon

    return predict


def _own_forecast_rules(doc, construct, windows):
    rules = {
        "deployed_v1_nearest_year": lambda c, s, h: _series(
            doc, construct, c, s
        )[-1],
        "damped_local_trend_w5_d0.5": _own_damped_predict(
            doc, construct, 5, 0.5
        ),
        "damped_local_trend_w5_d1.0": _own_damped_predict(
            doc, construct, 5, 1.0
        ),
        "damped_local_trend_w10_d0.5": _own_damped_predict(
            doc, construct, 10, 0.5
        ),
    }
    for w in windows:
        name = "ols_full_fit_window" if w == 22 else f"ols_last_{w}"
        rules[name] = _own_ols_window_predict(doc, construct, w)
    return rules


def _own_degenerate_rules(doc):
    return {
        "uniform_over_seven_categories": lambda c, s, h: 100.0 / 7,
        "fit_window_mean": lambda c, s, h: sum(
            _series(doc, "conditional", c, s)
        )
        / len(FIT_YEARS),
        "sex_pooled_nearest_year": lambda c, s, h: sum(
            _series(doc, "conditional", c, o)[-1] for o in SEXES
        )
        / 2,
    }


def _own_envelope(doc, rules, tolerances):
    env = {}
    for key in tolerances:
        c, s, h = key.split("|")
        h = int(h[1:])
        env[key] = min(
            abs(p(c, s, h) - _actual(doc, "conditional", c, s, h))
            for p in rules.values()
        )
    fails = sorted(k for k, v in env.items() if v > tolerances[k])
    return env, fails


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


def _own_predictor_for(doc, candidate_rule):
    if candidate_rule == "deployed_v1_nearest_year":
        return lambda c, s, h: _series(doc, "conditional", c, s)[-1]
    if candidate_rule == "ols_full_fit_window":
        return _own_ols_window_predict(doc, "conditional", 22)
    raise ValueError(candidate_rule)


def test_deviation_arithmetic_covers_every_rule_scored_under_both_paths():
    """Two rules appear under both arithmetics (referee B, D3): the
    nearest-year rule and the full-window OLS. The block must say so
    and cover both."""
    block = _artifact()["deviation_arithmetic"]
    assert block["rules_scored_under_both_paths"] == {
        "nearest_year": "deployed_v1_nearest_year",
        "linear_trend": "ols_full_fit_window",
    }
    assert set(block["by_rule"]) == {
        "deployed_v1_nearest_year",
        "ols_full_fit_window",
    }
    assert block["n_rules_scored_under_both_paths"] == 2
    assert "the one rule both paths score" not in block["surface"]
    assert "ols_full_fit_window" in block["surface"]


@pytest.mark.parametrize(
    "holdout_rule,candidate_rule",
    [
        ("nearest_year", "deployed_v1_nearest_year"),
        ("linear_trend", "ols_full_fit_window"),
    ],
)
def test_deviation_arithmetic_names_every_cell_the_two_paths_disagree_on(
    holdout_rule, candidate_rule
):
    """The artifact scores each of these rules twice under different
    rounding, so the same cell can carry two values (3.8086 in the
    holdout block, 3.8087 in the deployed finding). The disclosure must
    name exactly the cells that differ -- re-derived here with the test
    module's own predictor from the committed edition."""
    doc = _edition(REFERENCE_2023)
    predict = _own_predictor_for(doc, candidate_rule)
    art = _artifact()
    block = art["deviation_arithmetic"]["by_rule"][candidate_rule]
    assert block["holdout_rule"] == holdout_rule
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    rounded = {
        f"{cell['category']}|{cell['sex']}|h{cell['horizon']}": abs(
            cell["deviation"]
        )
        for cell in art["holdout_rules"]["per_cell"]["conditional"][
            holdout_rule
        ]
    }
    expected = {}
    for key in tolerances:
        c, s, h = key.split("|")
        h = int(h[1:])
        unrounded = round(
            abs(predict(c, s, h) - _actual(doc, "conditional", c, s, h)), 4
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


@pytest.mark.parametrize(
    "holdout_rule,candidate_rule",
    [
        ("nearest_year", "deployed_v1_nearest_year"),
        ("linear_trend", "ols_full_fit_window"),
    ],
)
def test_no_gate_eligible_verdict_depends_on_which_arithmetic_is_used(
    holdout_rule, candidate_rule
):
    """The disclosure's load-bearing claim, per rule: the two paths
    disagree by at most one 4-decimal ulp, and no cell sits that close
    to its tolerance -- so the failure set is the same either way."""
    art = _artifact()
    top = art["deviation_arithmetic"]
    block = top["by_rule"][candidate_rule]
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    assert block["max_abs_difference_pp"] == 0.0001
    assert block["n_verdict_flips"] == 0
    assert block["verdict_flips"] == []
    assert block["verdict_identical_under_both_paths"] is True
    assert block["failing_cells_identical"] is True
    assert block["n_failed_rounded_path"] == block["n_failed_unrounded_path"]
    for recorded in block["cells"].values():
        assert recorded["exceeds_tolerance_either_way"] is True
    margin = block["closest_any_cell_comes_to_its_tolerance_pp"]
    assert margin > block["max_abs_difference_pp"]
    rounded = {
        f"{cell['category']}|{cell['sex']}|h{cell['horizon']}": abs(
            cell["deviation"]
        )
        for cell in art["holdout_rules"]["per_cell"]["conditional"][
            holdout_rule
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
    scored = art["candidate_rules_on_the_draft_surface"]["rules"][
        candidate_rule
    ]
    assert failures_rounded == scored["failing_cells"]
    assert len(failures_rounded) == block["n_failed_rounded_path"]
    assert top["n_verdict_flips_all_rules"] == 0
    assert top["verdict_identical_under_both_paths_all_rules"] is True
    assert top["max_abs_difference_pp_all_rules"] == 0.0001


def test_the_two_paths_headline_numbers_are_both_reachable():
    """3.8087 in the deployed finding and 3.8086 in the holdout block
    are the same cell under the two arithmetics -- pin both so neither
    can drift into looking like a discrepancy again."""
    art = _artifact()
    block = art["deviation_arithmetic"]["by_rule"]["deployed_v1_nearest_year"]
    cell = block["cells"]["age62|female|h1"]
    assert cell["unrounded_prediction_path_pp"] == 3.8087
    assert cell["rounded_prediction_path_pp"] == 3.8086
    assert art["deployed_v1_finding"]["max_abs_deviation_pp"] == 3.8087
    assert block["closest_any_cell_comes_to_its_tolerance_pp"] == 0.0584
    assert block["n_failed_rounded_path"] == 6
    ols = art["deviation_arithmetic"]["by_rule"]["ols_full_fit_window"]
    assert ols["n_failed_rounded_path"] == 20
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
# v2: independent re-derivation of the trends and the holdout predictions
# --------------------------------------------------------------------------
def test_every_trend_rederives_from_the_2023_edition():
    """F2 (referee B, D2): the OLS trends were pinned only transitively
    through the builder. Recompute each with this module's own OLS."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    trends = _own_trends(doc)
    derivations = art["power_cap"]["derivations"]
    assert len(derivations) == 42
    for key, block in derivations.items():
        c, s, _ = key.split("|")
        assert block["trend_pp_per_year"] == trends[(c, s)], key
    for key, block in art["power_cap"][
        "report_only_tolerance_above_t_max"
    ].items():
        c, s, _ = key.split("|")
        assert block["trend_pp_per_year"] == trends[(c, s)], key


def test_every_holdout_prediction_rederives_from_the_2023_edition():
    """F2: both holdout rules' `predicted` re-derived from the edition,
    in both constructs, with this module's own arithmetic."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    for construct, blocks in art["holdout_rules"]["per_cell"].items():
        for rule, cells in blocks.items():
            assert len(cells) == (48 if construct == "published" else 42)
            for cell in cells:
                series = _series(doc, construct, cell["category"], cell["sex"])
                if rule == "nearest_year":
                    predicted = series[-1]
                else:
                    slope, intercept = _ols(FIT_YEARS, series)
                    predicted = intercept + slope * cell["year"]
                assert cell["predicted"] == pytest.approx(
                    round(predicted, 4)
                ), (
                    construct,
                    rule,
                    cell,
                )


# --------------------------------------------------------------------------
# v2: the rounding mode, the exact tie and the knife-edge class
# --------------------------------------------------------------------------
def test_every_tolerance_recomputes_in_decimal_under_the_stated_rounding_mode():
    art = _artifact()
    cap = art["power_cap"]
    assert cap["rounding_mode"]["mode"] == "ROUND_HALF_UP"
    assert (
        cap["rounding_mode"]["float_path_reproduces_every_tolerance"] is True
    )
    assert cap["rounding_mode"]["float_path_disagreements"] == []
    knobs = cap["knobs"]
    term = knobs["revision_term_pp"]
    assert term == round(knobs["k_rev"] * knobs["revision_sd_terminal_pp"], 6)
    for key, block in cap["derivations"].items():
        assert block["rounding_mode"] == "ROUND_HALF_UP"
        half_up, exact = _own_tolerance(
            term,
            block["trend_pp_per_year"],
            block["horizon_years"],
            knobs["rounding_pp"],
        )
        half_even, _ = _own_tolerance(
            term,
            block["trend_pp_per_year"],
            block["horizon_years"],
            knobs["rounding_pp"],
            ROUND_HALF_EVEN,
        )
        assert block["tolerance_pp"] == half_up, key
        assert block["tolerance_pp_round_half_even"] == half_even, key
        assert block["unrounded_tolerance_pp"] == float(exact), key


def test_the_exact_tie_cell_is_named_with_both_roundings():
    """age70plus|female|h2 is an exact 1.5250 tie (referee A, F5): the
    drafted 1.53 is ROUND_HALF_UP; ROUND_HALF_EVEN gives 1.52."""
    art = _artifact()
    cap = art["power_cap"]
    ties = cap["rounding_mode"]["exact_ties"]
    assert cap["rounding_mode"]["n_exact_ties"] == 1
    assert set(ties) == {"age70plus|female|h2"}
    tie = ties["age70plus|female|h2"]
    assert tie["unrounded_tolerance_pp"] == 1.525
    assert tie["round_half_up_pp"] == 1.53
    assert tie["round_half_even_pp"] == 1.52
    assert (
        tie["drafted_pp"]
        == cap["gate_eligible_tolerances_pp"]["age70plus|female|h2"]
        == 1.53
    )
    # The sd knob's rounding moves exactly this one cell and no other.
    assert set(
        cap["sd_knob_rounding_check"]["cells_with_a_different_tolerance"]
    ) == {"age70plus|female|h2"}
    # Re-derive: no other derivation is a tie.
    doc = _edition(REFERENCE_2023)
    trends = _own_trends(doc)
    tie_cells = []
    for key in cap["derivations"]:
        c, s, h = key.split("|")
        _, exact = _own_tolerance(
            cap["knobs"]["revision_term_pp"], trends[(c, s)], int(h[1:]), 0.05
        )
        if (exact * 1000) % 10 == 5:
            tie_cells.append(key)
    assert tie_cells == ["age70plus|female|h2"]
    # The deployed rule's verdict on the tie cell does not turn on the mode.
    failing = art["deployed_v1_finding"]["per_failing_cell"][
        "age70plus|female|h2"
    ]
    assert failing["deviation_pp"] > 1.53 > 1.52


def test_knife_edge_class_recomputes_and_has_thirteen_cells():
    """Referee B, D8: thirteen cells' unrounded tolerances sit within
    0.002 pp of a 2-decimal boundary, not only the tie."""
    art = _artifact()
    cap = art["power_cap"]
    band = Decimal(repr(cap["knife_edge_class"]["band_pp"]))
    doc = _edition(REFERENCE_2023)
    trends = _own_trends(doc)
    expected = {}
    for key in cap["derivations"]:
        c, s, h = key.split("|")
        _, exact = _own_tolerance(
            cap["knobs"]["revision_term_pp"], trends[(c, s)], int(h[1:]), 0.05
        )
        scaled = exact * 100
        frac = scaled - scaled.to_integral_value(rounding="ROUND_FLOOR")
        distance = abs(frac - Decimal("0.5")) / 100
        if distance < band:
            expected[key] = float(distance)
    assert set(cap["knife_edge_class"]["cells"]) == set(expected)
    assert cap["knife_edge_class"]["n_cells"] == len(expected) == 13
    for key, block in cap["knife_edge_class"]["cells"].items():
        assert block["distance_to_boundary_pp"] == pytest.approx(expected[key])
        assert block["is_exact_tie"] == (expected[key] == 0.0)
        assert block["tolerance_pp"] == cap["derivations"][key]["tolerance_pp"]
    assert (
        sum(
            1
            for b in cap["knife_edge_class"]["cells"].values()
            if b["is_exact_tie"]
        )
        == 1
    )


# --------------------------------------------------------------------------
# v2: the grammar / K sweep, the rounding sweep and horizon-aware pricing
# --------------------------------------------------------------------------
def test_signed_sd_equals_rms_on_every_conditional_stratum_and_recomputes():
    art = _artifact()
    doc_2014, doc_2023 = _edition(REFERENCE_2014), _edition(REFERENCE_2023)
    for key, years in (
        ("conditional_terminal_year", [2013]),
        ("conditional_settled_years", list(range(1998, 2013))),
        ("conditional_all_overlap", list(range(1998, 2014))),
    ):
        block = art["strata"][key]
        signed = [
            _conditional(doc_2023["data"][s][str(y)])[c]
            - _conditional(doc_2014["data"][s][str(y)])[c]
            for s in SEXES
            for y in years
            for c in CONDITIONAL_CATEGORIES
        ]
        mean = sum(signed) / len(signed)
        sd = (sum((v - mean) ** 2 for v in signed) / len(signed)) ** 0.5
        rms = (sum(v * v for v in signed) / len(signed)) ** 0.5
        assert block["mean_signed_pp"] == pytest.approx(round(mean, 6))
        assert block["sd_signed_pp"] == pytest.approx(round(sd, 6))
        assert block["rms_signed_pp"] == pytest.approx(round(rms, 6))
        assert block["sd_signed_pp"] == block["rms_signed_pp"]
        assert block["mean_signed_pp"] == 0.0
        assert "grammar_note" in block
    terminal = art["strata"]["conditional_terminal_year"]
    assert terminal["sd_signed_pp"] == 0.826427
    assert terminal["sd_pp"] == 0.492993
    # Four of the fourteen terminal revisions exceed the DRAFT 2 * sd.
    assert terminal["n_cells_with_abs_revision_above_k_rev_times_sd_pp"] == 4
    assert (
        "NEITHER of the two house grammars" in art["power_cap"]["grammar_note"]
    )


def test_grammar_and_k_sweep_recomputes_independently():
    """Referee A (2) and B (D1 / F3), reproduced with this module's own
    partition: the drafted grammar is 34 / 8 at K in {1.5, 2.0, 2.5};
    both house grammars are 32 / 10 with 4 deployed failures at K = 2."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    sweep = art["power_cap_alternatives"]["grammar_and_k_sweep"]
    terminal = art["strata"]["conditional_terminal_year"]
    sd = round(terminal["sd_pp"], 4)
    sd_signed = round(terminal["sd_signed_pp"], 4)
    terms = {
        "k_times_sd_abs_DRAFT": lambda k: round(k * sd, 6),
        "mean_plus_k_times_sd_abs": lambda k: round(
            terminal["mean_pp"] + k * sd, 6
        ),
        "k_times_sd_signed": lambda k: round(k * sd_signed, 6),
        "max_abs_revision_d2": lambda k: round(terminal["max_pp"], 6),
    }
    assert set(sweep["by_grammar"]) == set(terms)
    draft_gated = art["power_cap"]["gate_eligible_tolerances_pp"]
    for grammar, term_fn in terms.items():
        block = sweep["by_grammar"][grammar]
        assert block["is_the_draft_grammar"] == (
            grammar == "k_times_sd_abs_DRAFT"
        )
        for k in (1.5, 2.0, 2.5):
            row = block["by_k"][f"K_{k}"]
            term = term_fn(k)
            gated, report_only, failures = _own_partition(
                doc, {1: term, 2: term, 3: term}, 0.05
            )
            assert row["revision_term_pp_by_horizon"] == {
                "h1": term,
                "h2": term,
                "h3": term,
            }
            assert row["n_gate_eligible"] == len(gated), (grammar, k)
            assert row["n_report_only_tolerance_above_t_max"] == len(
                report_only
            )
            assert row["gate_eligible_tolerances_pp"] == gated
            assert row["deployed_v1_failing_cells"] == failures
            assert row["deployed_v1_n_failed"] == len(failures)
            assert row["cells_demoted_relative_to_draft"] == sorted(
                set(draft_gated) - set(gated)
            )
            assert row["partition_identical_to_draft"] == (
                set(gated) == set(draft_gated)
            )
    draft = sweep["by_grammar"]["k_times_sd_abs_DRAFT"]["by_k"]
    for k, fails in ((1.5, 10), (2.0, 6), (2.5, 5)):
        assert draft[f"K_{k}"]["n_gate_eligible"] == 34
        assert draft[f"K_{k}"]["deployed_v1_n_failed"] == fails
    assert draft["K_2.0"]["gate_eligible_tolerances_pp"] == draft_gated
    for grammar in (
        "mean_plus_k_times_sd_abs",
        "k_times_sd_signed",
        "max_abs_revision_d2",
    ):
        row = sweep["by_grammar"][grammar]["by_k"]["K_2.0"]
        assert row["n_gate_eligible"] == 32
        assert row["n_report_only_tolerance_above_t_max"] == 10
        assert row["deployed_v1_n_failed"] == 4
        assert row["cells_demoted_relative_to_draft"] == [
            "age65|male|h3",
            "age66|male|h1",
        ]
        assert row["age66_female_h1"]["ols_full_fit_window_clears"] is True
    assert (
        draft["K_2.0"]["age66_female_h1"]["ols_full_fit_window_clears"]
        is False
    )
    assert (
        draft["K_2.0"]["age66_female_h1"]["ols_full_fit_window_deviation_pp"]
        == 2.3288
    )


def test_draft_grammar_rounding_sweep_recomputes():
    """Referee A, section 2.d: stable at 34 / 8 for K in {1.5, 2.0,
    2.5} at rounding <= 0.05; 33 / 9 at (2.5, 0.10); 32 / 10 at K 3.0."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    sweep = art["power_cap_alternatives"]["draft_grammar_k_by_rounding_sweep"]
    sd = round(art["strata"]["conditional_terminal_year"]["sd_pp"], 4)
    assert len(sweep["rows"]) == 12
    for k in (1.5, 2.0, 2.5, 3.0):
        for rounding in (0.01, 0.05, 0.1):
            row = sweep["rows"][f"K_{k}|rounding_{rounding}"]
            term = round(k * sd, 6)
            gated, report_only, failures = _own_partition(
                doc, {1: term, 2: term, 3: term}, rounding
            )
            assert row["n_gate_eligible"] == len(gated), (k, rounding)
            assert row["n_report_only_tolerance_above_t_max"] == len(
                report_only
            )
            assert row["deployed_v1_failing_cells"] == failures
            assert row["deployed_v1_n_failed"] == len(failures)
    expect = {
        (1.5, 0.01): (34, 10),
        (1.5, 0.05): (34, 10),
        (1.5, 0.1): (34, 8),
        (2.0, 0.01): (34, 6),
        (2.0, 0.05): (34, 6),
        (2.0, 0.1): (34, 6),
        (2.5, 0.01): (34, 5),
        (2.5, 0.05): (34, 5),
        (2.5, 0.1): (33, 5),
        (3.0, 0.01): (32, 4),
        (3.0, 0.05): (32, 4),
        (3.0, 0.1): (32, 4),
    }
    for (k, rounding), (gated, fails) in expect.items():
        row = sweep["rows"][f"K_{k}|rounding_{rounding}"]
        assert (row["n_gate_eligible"], row["deployed_v1_n_failed"]) == (
            gated,
            fails,
        ), (k, rounding)
    assert sweep["rows"]["K_2.5|rounding_0.1"][
        "cells_demoted_relative_to_draft"
    ] == ["age66|male|h1"]


def test_horizon_aware_pricing_recomputes_to_37_5_and_15_failures():
    """Referee A, F4: h1 / h2 priced on the settled sd, h3 on the
    terminal sd gives 37 gate-eligible / 5 report-only and 15 deployed
    failures."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    block = art["power_cap_alternatives"]["horizon_aware_pricing"]
    settled = round(art["strata"]["conditional_settled_years"]["sd_pp"], 4)
    terminal = round(art["strata"]["conditional_terminal_year"]["sd_pp"], 4)
    assert block["knobs"]["revision_sd_h1_h2_pp"] == settled == 0.0089
    assert block["knobs"]["revision_sd_h3_pp"] == terminal == 0.493
    term_lo, term_hi = round(2.0 * settled, 6), round(2.0 * terminal, 6)
    gated, report_only, failures = _own_partition(
        doc, {1: term_lo, 2: term_lo, 3: term_hi}, 0.05
    )
    result = block["result"]
    assert result["gate_eligible_tolerances_pp"] == gated
    assert result["n_gate_eligible"] == len(gated) == 37
    assert (
        result["n_report_only_tolerance_above_t_max"] == len(report_only) == 5
    )
    assert result["deployed_v1_failing_cells"] == failures
    assert result["deployed_v1_n_failed"] == 15
    assert result["cells_promoted_relative_to_draft"] == [
        "age62|female|h2",
        "age62|male|h2",
        "age66|female|h2",
    ]
    assert result["cells_demoted_relative_to_draft"] == []


def test_settle_age_strata_recompute_and_rows_one_to_three_years_settled_did_not_move():
    art = _artifact()
    doc_2014, doc_2023 = _edition(REFERENCE_2014), _edition(REFERENCE_2023)
    for construct, block in art["strata_by_settle_age"].items():
        shares = _conditional if construct == "conditional" else _published
        assert set(block["by_settle_age"]) == {str(a) for a in range(1, 16)}
        for age, row in block["by_settle_age"].items():
            year = 2013 - int(age)
            assert row["entitlement_year"] == year
            magnitudes = [
                abs(
                    shares(doc_2023["data"][s][str(year)])[c]
                    - shares(doc_2014["data"][s][str(year)])[c]
                )
                for s in SEXES
                for c in shares(doc_2023["data"][s][str(year)])
            ]
            assert row["n_cells"] == len(magnitudes)
            assert row["nonzero_cells"] == sum(1 for m in magnitudes if m > 0)
            assert row["max_pp"] == pytest.approx(round(max(magnitudes), 6))
        assert block["rows_one_to_three_years_settled_moved"] is False
        assert block["settle_ages_with_any_revision"] == [5]
        assert 1 in block["settle_ages_with_zero_revision"]
        assert 2 in block["settle_ages_with_zero_revision"]
        assert 3 in block["settle_ages_with_zero_revision"]


def test_number_thousands_column_revisions_recompute():
    """Referee A, F11: the award-count column revised in six rows, four
    of them settled years."""
    art = _artifact()
    doc_2014, doc_2023 = _edition(REFERENCE_2014), _edition(REFERENCE_2023)
    block = art["number_thousands_column"]
    moved = [
        (s, y)
        for s in SEXES
        for y in range(1998, 2014)
        if doc_2014["data"][s][str(y)]["number_thousands"]
        != doc_2023["data"][s][str(y)]["number_thousands"]
    ]
    assert block["n_rows"] == 32
    assert block["nonzero_rows"] == len(moved) == 6
    assert (
        block["nonzero_settled_rows"]
        == sum(1 for _, y in moved if y < 2013)
        == 4
    )
    assert block["nonzero_terminal_rows"] == 2
    assert [(r["sex"], r["year"]) for r in block["moved_rows"]] == moved
    for row in block["moved_rows"]:
        old = doc_2014["data"][row["sex"]][str(row["year"])][
            "number_thousands"
        ]
        new = doc_2023["data"][row["sex"]][str(row["year"])][
            "number_thousands"
        ]
        assert row["revision_thousands"] == new - old
    assert 0 < block["max_abs_revision_share_settled"] < 0.002
    assert block["max_abs_revision_share_terminal"] > 0.04


# --------------------------------------------------------------------------
# v2: the widened forecast class, the envelopes and the window sweep
# --------------------------------------------------------------------------
def test_widened_forecast_envelope_has_zero_failures_and_packet_grid_envelope_one():
    """Referee A, F1 and section 5.c: the envelope result is the single
    most-cited number and was not test-pinned. Both envelopes are
    re-derived here with this module's own rules and pinned."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    block = art["candidate_rules_on_the_draft_surface"]
    assert block["rules_added_in_v2"] == [
        f"ols_last_{w}" for w in (13, 14, 15, 16, 17, 18)
    ]
    assert block["n_forecast_rules"] == 14
    widened = _own_forecast_rules(
        doc, "conditional", (22, 10, 5, 3, 13, 14, 15, 16, 17, 18)
    )
    env, fails = _own_envelope(doc, widened, tolerances)
    envelope = block["post_hoc_best_of_forecast_class_envelope"]
    assert envelope["rules_in_envelope"] == sorted(widened)
    assert envelope["n_failed"] == len(fails) == 0
    assert envelope["failing_cells"] == fails == []
    assert (
        envelope["max_abs_deviation_pp"]
        == round(max(env.values()), 4)
        == 1.2519
    )
    assert envelope["per_cell_pp"] == {k: round(v, 4) for k, v in env.items()}
    assert envelope["per_cell_pp"]["age66|female|h1"] == 0.0688
    packet = _own_forecast_rules(doc, "conditional", (22, 10, 5, 3))
    env_p, fails_p = _own_envelope(doc, packet, tolerances)
    grid = block["envelope_at_the_packet_window_grid"]
    assert grid["rules_in_envelope"] == sorted(packet)
    assert grid["n_failed"] == len(fails_p) == 1
    assert grid["failing_cells"] == fails_p == ["age66|female|h1"]
    assert (
        grid["max_abs_deviation_pp"] == round(max(env_p.values()), 4) == 2.3288
    )
    assert grid["mean_abs_deviation_pp"] == 0.315
    assert grid["per_cell_pp"] == {k: round(v, 4) for k, v in env_p.items()}
    assert tolerances["age66|female|h1"] == 2.24


def test_all_rule_envelopes_recompute_including_the_degenerate_rules():
    """The build report's 'all eleven rules, zero failures, max 1.2519'
    is now emitted and re-derived."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    block = art["candidate_rules_on_the_draft_surface"]
    eleven = {
        **_own_forecast_rules(doc, "conditional", (22, 10, 5, 3)),
        **_own_degenerate_rules(doc),
    }
    env, fails = _own_envelope(doc, eleven, tolerances)
    recorded = block["envelope_over_the_v1_eleven_rules_including_degenerate"]
    assert recorded["n_rules"] == 11
    assert recorded["n_failed"] == len(fails) == 0
    assert (
        recorded["max_abs_deviation_pp"]
        == round(max(env.values()), 4)
        == 1.2519
    )
    assert (
        recorded["mean_abs_deviation_pp"]
        == round(sum(env.values()) / len(env), 4)
        == 0.2021
    )
    everything = {
        **_own_forecast_rules(
            doc, "conditional", (22, 10, 5, 3, 13, 14, 15, 16, 17, 18)
        ),
        **_own_degenerate_rules(doc),
    }
    env_all, fails_all = _own_envelope(doc, everything, tolerances)
    recorded_all = block["envelope_over_all_rules_including_degenerate"]
    assert recorded_all["n_rules"] == len(block["rules"]) == 17
    assert recorded_all["n_failed"] == len(fails_all) == 0
    assert recorded_all["max_abs_deviation_pp"] == round(
        max(env_all.values()), 4
    )


def test_ols_window_sweep_recomputes_and_names_the_clearing_windows():
    """'Failed by every scanned rule' is a property of the window grid:
    OLS on the last 13 fit years clears age66|female|h1 at 0.0688 pp."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    sweep = art["candidate_rules_on_the_draft_surface"]["ols_window_sweep"]
    assert set(sweep["rows"]) == {f"ols_last_{w}" for w in range(2, 23)}
    clearing = []
    zero_fail = []
    for w in range(2, 23):
        predict = _own_ols_window_predict(doc, "conditional", w)
        devs = {}
        for key in tolerances:
            c, s, h = key.split("|")
            h = int(h[1:])
            devs[key] = abs(
                predict(c, s, h) - _actual(doc, "conditional", c, s, h)
            )
        fails = sorted(k for k, v in devs.items() if v > tolerances[k])
        row = sweep["rows"][f"ols_last_{w}"]
        assert row["window_years"] == w
        assert row["n_failed"] == len(fails)
        assert row["failing_cells"] == fails
        assert row["max_abs_deviation_pp"] == round(max(devs.values()), 4)
        assert row["age66_female_h1_deviation_pp"] == round(
            devs["age66|female|h1"], 4
        )
        assert row["age66_female_h1_clears"] == (
            devs["age66|female|h1"] <= tolerances["age66|female|h1"]
        )
        if row["age66_female_h1_clears"]:
            clearing.append(w)
        if not fails:
            zero_fail.append(w)
    assert (
        sweep["windows_clearing_age66_female_h1"]
        == clearing
        == list(range(12, 22))
    )
    assert sweep["windows_in_packet_grid_clearing_age66_female_h1"] == []
    assert sweep["windows_with_zero_failures_on_all_34"] == zero_fail == []
    assert (
        sweep["rows"]["ols_last_13"]["age66_female_h1_deviation_pp"] == 0.0688
    )
    assert (
        sweep["rows"]["ols_last_22"]["age66_female_h1_deviation_pp"] == 2.3288
    )
    for w in (13, 14, 15, 16, 17, 18):
        assert sweep["rows"][f"ols_last_{w}"]["named_as_a_rule"] is True
        rule = art["candidate_rules_on_the_draft_surface"]["rules"][
            f"ols_last_{w}"
        ]
        assert rule["rule_class"] == "forecast"
        assert rule["n_failed"] == sweep["rows"][f"ols_last_{w}"]["n_failed"]


def test_published_construct_envelope_recomputes_the_packets_section_4_numbers():
    """The packet's 2.40 / 0.52 (and the build report's 0.517 / 0.521)
    are now emitted and re-derived on the published construct."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    block = art["published_construct_forecast_envelope"]
    rules = _own_forecast_rules(doc, "published", (22, 10, 5, 3))
    cells = [
        (c, s, h)
        for s in SEXES
        for c in PUBLISHED_CATEGORIES
        for h in (1, 2, 3)
    ]
    assert block["n_cells"] == len(cells) == 48

    def envelope(names):
        values = [
            min(
                abs(rules[n](*cell) - _actual(doc, "published", *cell))
                for n in names
            )
            for cell in cells
        ]
        return round(max(values), 4), round(sum(values) / len(values), 4)

    max8, mean8 = envelope(list(rules))
    assert (
        block["envelope_over_eight_rules"]["max_abs_deviation_pp"]
        == max8
        == 2.4
    )
    assert (
        block["envelope_over_eight_rules"]["mean_abs_deviation_pp"]
        == mean8
        == 0.517
    )
    for name in rules:
        _, mean7 = envelope([n for n in rules if n != name])
        assert block["envelope_mean_dropping_each_rule"][name] == mean7
    assert (
        block["envelope_mean_dropping_each_rule"][
            "damped_local_trend_w10_d0.5"
        ]
        == 0.5208
    )
    for name, predict in rules.items():
        devs = [
            abs(predict(*cell) - _actual(doc, "published", *cell))
            for cell in cells
        ]
        assert block["rules"][name]["max_abs_deviation_pp"] == round(
            max(devs), 4
        )
    assert (
        block["rules"]["deployed_v1_nearest_year"]["max_abs_deviation_pp"]
        == 3.2
    )


# --------------------------------------------------------------------------
# v2: the knife-edge cell's record, the margins, the reconciliation rows
# --------------------------------------------------------------------------
def test_age66_before_fra_transition_rederives_from_the_edition():
    """Referee A (F2) and B (finding 2): the composition break the
    packet's d3(ii) names begins in 2021; the cell is 2020."""
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    block = art["age66_before_fra_transition"]
    for sex in SEXES:
        for year in range(2016, 2023):
            assert (
                block["values_by_sex_and_year"][sex][str(year)]
                == doc["data"][sex][str(year)]["raw"]["age66_before_fra"]
            )
        populated = [
            y
            for y in range(2016, 2023)
            if doc["data"][sex][str(y)]["raw"]["age66_before_fra"] is not None
        ]
        assert block["first_populated_year"][sex] == min(populated) == 2021
        assert block["last_null_year"][sex] == 2020
    assert block["age66_female_h1_entitlement_year"] == 2020
    assert block["break_covers_age66_female_h1"] is False
    assert block["holdout_horizons"]["h1"]["age66_before_fra_populated"] == {
        "female": False,
        "male": False,
    }
    assert block["holdout_horizons"]["h2"]["age66_before_fra_populated"] == {
        "female": True,
        "male": True,
    }


def test_per_failing_cell_deviations_and_margins_are_emitted_and_recompute():
    art = _artifact()
    doc = _edition(REFERENCE_2023)
    finding = art["deployed_v1_finding"]
    tolerances = art["power_cap"]["gate_eligible_tolerances_pp"]
    assert set(finding["per_failing_cell"]) == set(finding["failing_cells"])
    for key, block in finding["per_failing_cell"].items():
        c, s, h = key.split("|")
        h = int(h[1:])
        deviation = round(
            abs(
                _series(doc, "conditional", c, s)[-1]
                - _actual(doc, "conditional", c, s, h)
            ),
            4,
        )
        assert block["deviation_pp"] == deviation
        assert block["tolerance_pp"] == tolerances[key]
        assert block["margin_pp"] == round(deviation - tolerances[key], 4)
        assert block["margin_pp"] > 0
        assert block["tolerance_in_knife_edge_class"] == (
            key in art["power_cap"]["knife_edge_class"]["cells"]
        )
    assert (
        finding["per_failing_cell"]["age62|female|h1"]["margin_pp"] == 1.5087
    )
    assert (
        finding["per_failing_cell"]["age70plus|female|h2"]["margin_pp"]
        == 0.0682
    )
    assert (
        finding["per_failing_cell"]["age70plus|female|h2"][
            "tolerance_in_knife_edge_class"
        ]
        is True
    )


def test_packet_reconciliation_carries_the_table_notes_and_the_seventh_correction():
    art = _artifact()
    rows = {
        row["field"]: row
        for row in art["packet_reconciliation"]["differences"]
    }
    assert len(rows) == 3
    notes = rows["floor.no_sampling_floor.table_notes"]
    assert "False" in notes["measured"] and "True" in notes["measured"]
    assert (
        art["no_sampling_floor"]["table_notes_identical_across_editions"]
        is False
    )
    seventh = next(
        row
        for field, row in rows.items()
        if field.startswith("gate_b2_claiming.open_draft_decisions.d3")
    )
    assert seventh["correction_number"] == 7
    assert "2020" in seventh["measured"] and "2021" in seventh["measured"]
    assert "UNAVAILABLE AS WRITTEN" in seventh["note"].upper()


def test_fit_isolation_names_the_channels_carrying_the_held_out_actuals():
    art = _artifact()
    block = art["fit_isolation"]
    paths = [
        channel["path"]
        for channel in block["channels_carrying_the_held_out_actuals"]
    ]
    assert paths == [
        "runs/claiming_publication_floor_v1.json",
        "runs/claiming_reference_v1.json",
        "data/external/ssa_claim_ages_2023supplement.json",
    ]
    for channel in block["channels_carrying_the_held_out_actuals"][1:]:
        path = ROOT / channel["path"]
        assert (
            channel["pin"]["sha256"]
            == hashlib.sha256(path.read_bytes()).hexdigest()
        )
    assert (
        "runs/claiming_publication_floor_v1.json"
        in block["required_draft_clause"]
    )
    assert "runs/claiming_reference_v1.json" in block["required_draft_clause"]


def test_open_decisions_file_every_ruling_and_decide_none():
    art = _artifact()
    block = art["open_decisions"]
    assert block["status"].startswith("OPEN")
    assert set(block) == {
        "status",
        "grammar_and_k_rev",
        "horizon_pricing",
        "age66_female_h1_knife_edge",
        "rounding_mode",
        "d0_estimand_construct",
        "d1_missing_2021_2022_editions",
    }
    grammar = block["grammar_and_k_rev"]["summary_at_each_k"]
    assert grammar["k_times_sd_abs_DRAFT"]["K_2.0"]["partition"] == "34 / 8"
    assert (
        grammar["mean_plus_k_times_sd_abs"]["K_2.0"]["partition"] == "32 / 10"
    )
    assert grammar["k_times_sd_signed"]["K_2.0"]["partition"] == "32 / 10"
    knife = block["age66_female_h1_knife_edge"]
    assert knife["premise_check"]["structural_reason_covers_the_cell"] is False
    assert (
        "UNAVAILABLE AS WRITTEN"
        in knife["options_as_corrected"]["ii_structural_demotion_as_drafted"]
    )
    assert block["horizon_pricing"]["summary"]["horizon_aware"].startswith(
        "37 / 5"
    )
    assert block["rounding_mode"]["drafted"] == "ROUND_HALF_UP"
    # The DRAFT surface itself is unchanged by any of this.
    assert art["power_cap"]["n_gate_eligible"] == 34
    assert art["power_cap"]["knobs"]["k_rev"] == 2.0
    assert art["power_cap"]["knobs"]["rounding_pp"] == 0.05


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
