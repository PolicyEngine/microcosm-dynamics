"""The committed outputs of the invented population run.

INVENTED DATA - NOT A COMPARISON, NOT THE US.  These tests read the files
``scripts/pe_us_population_invented.py`` wrote to
``docs/analysis/pe_us_population_invented_20260930/`` and need no
policyengine-us: every output carries the label, every invented input is
labelled, no private path leaks, the recorded identities and checks hold,
and both population sizes ran within the script's stated bounds.  The live
rebuild of the 300-unit run is in ``test_population_oracle.py``.
"""

from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "docs" / "analysis" / "pe_us_population_invented_20260930"
sys.path.insert(0, str(ROOT / "scripts"))

import pe_us_population_invented as script  # noqa: E402

LABEL = "INVENTED DATA - NOT A COMPARISON, NOT THE US"
SIZES = ("300", "3000")


@pytest.fixture(scope="module")
def document():
    return json.loads((OUTPUTS / f"{script.OUTPUT_STEM}.json").read_text())


@pytest.fixture(scope="module")
def report():
    return (OUTPUTS / f"{script.OUTPUT_STEM}.md").read_text()


@pytest.fixture(scope="module")
def completion_report():
    return (OUTPUTS / "completion-report.md").read_text()


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def test__outputs__then_every_file_carries_the_label(document, report):
    assert script.LABEL == LABEL
    assert document["label"] == LABEL
    assert document["schema_version"] == script.SCHEMA_VERSION
    assert document["phase0"] == "permitted"
    assert document["phase0_reasoning"] == (
        "option A: invented data only, per d479"
    )
    assert set(document["sizes"]) == set(SIZES)
    for size in SIZES:
        assert document["sizes"][size]["label"] == LABEL
    assert report.startswith(f"# {LABEL}\n")
    for size in SIZES:
        assert f"invented family units ({LABEL})" in report
        stem = OUTPUTS / f"{script.OUTPUT_STEM}_{size}_by_level"
        svg = stem.with_suffix(".svg").read_text()
        assert f"<dc:title>{LABEL}</dc:title>" in svg
        assert svg.endswith("\n")
        assert all(line == line.rstrip() for line in svg.splitlines())
        png = stem.with_suffix(".png").read_bytes()
        assert png.startswith(b"\x89PNG")
        assert b"Title\x00" + LABEL.encode() in png


def test__completion_report__then_it_carries_the_label(completion_report):
    assert completion_report.startswith(f"# {LABEL}\n")
    # Every table of results is of invented families.
    for line in completion_report.splitlines():
        if line.startswith("| ") and "families" in line:
            assert line.startswith("| INVENTED families"), line
    assert "**INVENTED**" in completion_report


def _blocks(markdown):
    """The report's blocks: runs of lines between blank lines."""

    blocks, block = [], []
    for line in markdown.splitlines():
        if line.strip():
            block.append(line)
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)
    return blocks


def test__report__then_the_dagger_note_follows_only_tables_with_a_dagger(
    report, document
):
    """A table with a \u2020 row is followed by the note; no other is."""

    blocks = _blocks(report)
    tables = 0
    for i, block in enumerate(blocks):
        if not block[0].startswith("|"):
            continue
        tables += 1
        marked = any(line.endswith("\u2020 |") for line in block)
        following = blocks[i + 1] if i + 1 < len(blocks) else []
        noted = any("\u2020 " in line for line in following)
        assert marked == noted, block[0]
    assert tables
    notes = sum(
        1 for block in blocks for line in block if line.startswith("\u2020 ")
    )
    assert notes == len(SIZES)  # the headline tables' mixed ratios

    # A mixed group with a zero aggregate Social Security change has no
    # defined share. Its displayed n/a must not acquire a dagger footnote.
    undefined_shares = json.loads(json.dumps(document))
    for run in undefined_shares["sizes"].values():
        default = run["results"]["default"]
        default["population"]["take_back"]["share"] = None
        for grouping in default["groupings"].values():
            for group in grouping["groups"].values():
                group["take_back"]["share"] = None
    assert "\u2020" not in script.markdown(undefined_shares)


def test__report__then_market_income_is_not_a_level_of_government(report):
    assert report.count(
        "| Market income (not a level of government) |"
    ) == len(SIZES)
    assert report.count("Market income is not a level of government") == (
        len(SIZES)
    )


def test__outputs__then_every_invented_input_is_labelled(document, report):
    inputs = document["invented_inputs"]
    assert set(inputs["distributions"]) == {
        "state",
        "renter",
        "monthly_rent",
        "wealth1",
        "vehicles",
        "labor",
        "annuities",
        "interest",
    }
    for spec in inputs["distributions"].values():
        assert spec["label"] == "INVENTED"
    for concept in inputs["input_concepts"]:
        assert concept["label"] == "INVENTED"
    assert "## Invented inputs" in report
    for item in inputs["distributions"]:
        assert f"| `{item}` | INVENTED |" in report


def test__outputs__then_no_private_path_leaks(
    document, report, completion_report
):
    for text in [report, completion_report, *_strings(document)]:
        assert "/Users/" not in text
        assert "microcosm-launch-evidence" not in text
        assert "psid-data" not in text
    for size in SIZES:
        stem = OUTPUTS / f"{script.OUTPUT_STEM}_{size}_by_level"
        assert "/Users/" not in stem.with_suffix(".svg").read_text()


def test__outputs__then_the_run_used_the_pinned_release(document):
    provenance = document["provenance"]
    assert provenance["microcosm_dynamics"]["code_dirty"] is False
    pe = provenance["policyengine_us"]
    assert pe["release"]["version"] == "2.18.0"
    assert provenance["payment_year"] == 2026
    ca = next(
        u
        for u in pe["parameter_updates"]
        if u["parameter"].startswith("gov.states.ca.")
    )
    assert pe["population_overrides"] == {ca["parameter"]: ca["value"]}


@pytest.mark.parametrize("size", SIZES)
def test__outputs__then_the_identities_and_checks_hold(document, size):
    run = document["sizes"][size]
    default = run["results"]["default"]
    population = default["population"]
    assert all(population["identity_exact"].values())
    assert all(run["results"]["with_health"]["identity_exact"].values())
    for grouping in (
        "ssi_status",
        "income_decile",
        "social_security_direction",
    ):
        entry = default["groupings"][grouping]
        assert entry["partition_exact"] is True
        for group in entry["groups"].values():
            assert all(group["identity_exact"].values())
    take_back = population["take_back"]
    assert take_back["exact_parts_sum_to_share"] is True
    assert math.isclose(
        sum(take_back["by_level"].values()),
        take_back["share"],
        rel_tol=1e-9,
    )
    # The rounded levels sum to the rounded net within a half cent each.
    levels = population["by_level"]
    assert abs(
        sum(entry["change"] for entry in levels.values())
        - population["net_change"]
    ) <= 0.005 * (len(levels) + 1)
    assert round(float(Fraction(population["net_change_exact"])), 2) == (
        population["net_change"]
    )
    # Verify the identity from exported fractions, independently of the
    # booleans recorded by the producer. Rounded display dollars may differ
    # by a cent when added.
    for result in (population, run["results"]["with_health"]):
        for key in ("by_level", "by_category", "by_leaf"):
            entries = result[key]
            if isinstance(entries, dict):
                entries = entries.values()
            assert sum(
                (Fraction(entry["change_exact"]) for entry in entries),
                Fraction(0),
            ) == Fraction(result["net_change_exact"])
        assert (
            Fraction(result["reform_net_income_exact"])
            - Fraction(result["baseline_net_income_exact"])
        ) == Fraction(result["net_change_exact"])
    for entry in default["groupings"].values():
        assert sum(
            (
                Fraction(group["net_change_exact"])
                for group in entry["groups"].values()
            ),
            Fraction(0),
        ) == Fraction(population["net_change_exact"])
    checks = run["checks"]
    assert set(checks["social_security_equals_inputs"]) == set(script.VARIANTS)
    for variant in script.VARIANTS:
        social_security = checks["social_security_equals_inputs"][variant]
        assert social_security["equal"] is True
        assert social_security["households_checked"] == (
            run["households"]["count"]
        )
    for variant in ("default", "with_health"):
        households = checks["households"][variant]
        assert (
            households["unchanged_social_security_households_that_change"] == 0
        )
    assert checks["deciles_match_policyengine_us"]["mismatches"] == 0
    assert checks["deciles_match_policyengine_us"]["households"] == (
        run["households"]["count"]
    )


@pytest.mark.parametrize("size", SIZES)
def test__outputs__then_each_size_ran_within_its_stated_bounds(document, size):
    scale = document["sizes"][size]["scale"]
    bounds = script.SCALE_BOUNDS[int(size)]
    assert scale["family_units"] == int(size)
    assert scale["bounds"] == bounds
    assert scale["within_bounds"] is True
    assert scale["pe_wall_seconds"] <= bounds["pe_wall_seconds"]
    assert scale["peak_rss_bytes"] <= bounds["peak_rss_bytes"]
    assert set(scale["pe_simulations"]) == set(script.VARIANTS)
    for variant in script.VARIANTS:
        # One simulation per scenario: baseline and reform, no more.
        assert set(scale["pe_simulations"][variant]) == {
            script.BASELINE,
            script.REFORM,
        }


def test__outputs__then_the_larger_population_is_about_ten_times_larger(
    document,
):
    small = document["sizes"]["300"]["households"]
    large = document["sizes"]["3000"]["households"]
    assert small["count"] == 300 and large["count"] == 3000
    assert 8 * small["people"] <= large["people"] <= 12 * small["people"]
