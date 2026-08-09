"""Tests for the operative Amendment-13 tier-2 repair publisher."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_amendment13_tier2_repairs as publisher  # noqa: E402
import validate_amendment13_execution_law as a13  # noqa: E402


@pytest.fixture(scope="module")
def publication():
    law, values = publisher.build_artifact_values()
    rendered = publisher.render_artifact_values(values)
    return law, values, rendered


def test__artifact_projection__has_exact_paths_and_deep_equal_rows(
    publication,
):
    law, values, rendered = publication
    assert len(values) == len(rendered) == 20
    assert {
        path for path in values if path.parent == publisher.OVERLAY_DIRECTORY
    } == {
        publisher.overlay_relative_path(position)
        for position in publisher.OVERLAY_POSITIONS
    }
    assert {
        path for path in values if path.parent == publisher.SEAL_DIRECTORY
    } == {publisher.seal_relative_path(position) for position in range(1, 7)}
    expected_rows = [
        *law["repair_overlay_rows"],
        *law["successor_era_seal_rows"],
    ]
    assert list(values.values()) == expected_rows
    for path, raw in rendered.items():
        assert raw == a13.canonical_json_bytes(values[path])
        assert a13._strict_canonical_json(raw, path.as_posix()) == values[path]


def test__artifact_projection__reconciles_exactly_46_repairs(publication):
    law, _, _ = publication
    publisher.validate_publication_law(law)
    assert law["integrity"]["repair_count"] == 28 + 8 + 2 + 8 == 46
    assert law["integrity"]["supersession_count"] == 46
    counts = {
        row["document_source_position"]: len(
            publisher._overlay_successors(row)
        )
        for row in law["repair_overlay_rows"]
    }
    assert counts == publisher.EXPECTED_REPAIR_COUNTS_BY_DOCUMENT


def test__artifact_projection__retains_empty_sixth_era_seal(publication):
    law, values, rendered = publication
    seal = law["successor_era_seal_rows"][-1]
    path = publisher.seal_relative_path(6)
    assert values[path] == seal
    assert a13._strict_canonical_json(rendered[path], path.as_posix()) == seal
    assert seal["era_order_position"] == 6
    assert seal["repair_overlay_ids"] == []
    assert seal["successor_row_ids"] == []
    assert seal["supersession_row_ids"] == []
    assert set(seal["repair_counts"].values()) == {0}
    assert seal["all_named_domains_present_even_when_empty"] is True


def test__artifact_validation__rejects_mutated_row(publication):
    _, values, rendered = publication
    actual = dict(rendered)
    path = publisher.overlay_relative_path(7)
    mutated = copy.deepcopy(values[path])
    mutated["authority_kind"] = "AUTHORITY"
    actual[path] = a13.canonical_json_bytes(mutated)
    with pytest.raises(
        publisher.PublicationError,
        match="differs from the operative reconstruction",
    ):
        publisher.validate_artifact_bundle(actual, values, artifacts="all")


def test__artifact_validation__rejects_dropped_overlay(publication):
    _, values, rendered = publication
    actual = dict(rendered)
    del actual[publisher.overlay_relative_path(10)]
    with pytest.raises(
        publisher.PublicationError,
        match="artifact path domain drift",
    ):
        publisher.validate_artifact_bundle(actual, values, artifacts="all")


def test__artifact_validation__rejects_reordered_seal_domain(publication):
    _, values, rendered = publication
    actual = dict(rendered)
    path = publisher.seal_relative_path(1)
    reordered = copy.deepcopy(values[path])
    reordered["successor_row_ids"].reverse()
    actual[path] = a13.canonical_json_bytes(reordered)
    with pytest.raises(
        publisher.PublicationError,
        match="differs from the operative reconstruction",
    ):
        publisher.validate_artifact_bundle(actual, values, artifacts="all")


def test__write_and_read__round_trip_without_wrapper(publication, tmp_path):
    _, values, rendered = publication
    actual = publisher.write_artifact_bundle(tmp_path, values, artifacts="all")
    assert actual == rendered
    reread = publisher.read_artifact_bundle(tmp_path, values, artifacts="all")
    publisher.validate_artifact_bundle(reread, values, artifacts="all")
    assert not list(tmp_path.glob("*.json"))
    assert len(list((tmp_path / publisher.OVERLAY_DIRECTORY).iterdir())) == 14
    assert len(list((tmp_path / publisher.SEAL_DIRECTORY).iterdir())) == 6


def test__first_add_relationships__accept_each_publication_stage(
    publication,
):
    law, _, _ = publication
    overlay_commits = {
        position: None for position in publisher.OVERLAY_POSITIONS
    }
    seal_commits = {position: None for position in range(1, 7)}
    era_position_by_id = {
        row["era_id"]: row["era_order_position"]
        for row in law["successor_era_seal_rows"]
    }
    overlay_era_positions = {
        row["document_source_position"]: era_position_by_id[
            row["predecessor_era_id"]
        ]
        for row in law["repair_overlay_rows"]
    }
    graph = {("ratification", "overlays"), ("overlays", "seals")}

    def ancestor(earlier, later):
        return (earlier, later) in graph

    assert (
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=overlay_commits,
            seal_commits=seal_commits,
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=ancestor,
        )
        == "prospective"
    )
    overlay_commits = dict.fromkeys(overlay_commits, "overlays")
    assert (
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=overlay_commits,
            seal_commits=seal_commits,
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=ancestor,
            required="overlays",
        )
        == "overlays_committed"
    )
    seal_commits = dict.fromkeys(seal_commits, "seals")
    assert (
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=overlay_commits,
            seal_commits=seal_commits,
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=ancestor,
            required="all",
        )
        == "seals_committed"
    )


def test__first_add_relationships__reject_drop_and_same_commit(publication):
    law, _, _ = publication
    era_position_by_id = {
        row["era_id"]: row["era_order_position"]
        for row in law["successor_era_seal_rows"]
    }
    overlay_era_positions = {
        row["document_source_position"]: era_position_by_id[
            row["predecessor_era_id"]
        ]
        for row in law["repair_overlay_rows"]
    }
    complete_overlays = dict.fromkeys(publisher.OVERLAY_POSITIONS, "batch")
    complete_seals = dict.fromkeys(range(1, 7), "seal-batch")
    dropped = dict(complete_overlays)
    dropped[7] = None
    with pytest.raises(
        publisher.PublicationError,
        match="not one complete first-add batch",
    ):
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=dropped,
            seal_commits=dict.fromkeys(range(1, 7)),
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=lambda earlier, later: True,
        )
    with pytest.raises(
        publisher.PublicationError,
        match="not a strict ancestor",
    ):
        publisher._validate_first_add_relationships(
            governing_commit="ratification",
            overlay_commits=complete_overlays,
            seal_commits=complete_seals,
            overlay_era_positions=overlay_era_positions,
            strict_ancestor=lambda earlier, later: earlier != later
            and (earlier, later) == ("ratification", "batch"),
        )


def test__live_git_order__validates_before_and_after_publication(publication):
    law, values, _ = publication
    state = publisher.validate_git_publication_order(law, values)
    assert state["status"] in {
        "prospective",
        "overlays_committed",
        "seals_committed",
    }
    if state["status"] == "prospective":
        required = "overlays"
        message = "overlay batch is not committed"
    elif state["status"] == "overlays_committed":
        required = "all"
        message = "seal batch is not committed"
    else:
        required = None
        message = None
    if required is None:
        assert (
            publisher.validate_git_publication_order(
                law, values, required="all"
            )["status"]
            == "seals_committed"
        )
    else:
        with pytest.raises(publisher.PublicationError, match=message):
            publisher.validate_git_publication_order(
                law, values, required=required
            )
