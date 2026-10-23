"""The committed held-out data registry keeps its rules on every commit.

``docs/design/track_b_holdout_registry.json`` is the single registry of
the data that Track B's gates and the open-population lane's gates hold
out (dynamics coordinator, 2026-10-21). These tests check the committed
registry against the committed tree, including its scored-run artifacts
under ``runs/``, against its base commit, and between every first-parent
commit since that base. The rules themselves are exercised on invented
registries in ``test_track_b_holdout_registry.py``.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from populace_dynamics.track_b import holdout_registry as registry

ROOT = Path(__file__).resolve().parents[1]

#: The seeded entries' unit keys, specified here independently. They are
#: immutable once merged: PSID by interview wave, EPUF by the vintage in
#: its title, publications by edition.
EXPECTED_SEED_KEYS = {
    "H001": ["psid:2015-2023:held_out_window"],
    "H002": ["psid:2013:fam2013er", "psid:2015:fam2015er"],
    "H003": ["ssa_epuf:2006:test_partition"],
    "H004": [
        "psid:1982:employment_status",
        "psid:1983:employment_status",
        "psid:1993-1997:employment_status",
        "psid:1999-2023:employment_status",
        "ssa_di_asr:2023",
    ],
    "H005": [
        "ssa_supplement:2023:6.b5.1",
        "ssa_supplement:2023:6.b4",
        "ssa_supplement:2023:6.b3",
        "ssa_di_asr:2023:table_19",
        "census_cps_tables:2023:hh-4",
        "census_cps_tables:2023:ad-3",
        "populace_us_frame:2024:certified",
        "mermin_smith_anchors:undated",
    ],
}
#: Every disclosed pair: four shared units and two unresolved relations
#: between EPUF and the 2023 DI report and Supplement tables.
EXPECTED_DISCLOSURES = {
    ("H001", "H002"),
    ("H001", "H004"),
    ("H002", "H004"),
    ("H003", "H004"),
    ("H003", "H005"),
    ("H004", "H005"),
}
EXPECTED_FAMILIES = {
    "psid": "psid",
    "ssa_epuf": "ssa_administrative",
    "ssa_supplement": "ssa_administrative",
    "ssa_di_asr": "ssa_administrative",
    "census_cps_tables": "us_cross_section",
    "populace_us_frame": "us_cross_section",
    "mermin_smith_anchors": "literature",
}
EXPECTED_OUTSIDE_GATES_YAML = {"B2": ("B2", "6252388925")}
#: Every listed scored run and its gate, specified here independently.
EXPECTED_SCORED_RUN_GATES = {
    "runs/gate_m6_candidate1_v1.json": "gate_m6",
    "runs/gate_m6_candidate2_v1.json": "gate_m6",
    "runs/gate_m6_candidate3_v1.json": "gate_m6",
    "runs/track_b_b2_score.json": "B2",
    "runs/epuf_fill_gate_test_v1.json": "gate_epuf_fill",
    "runs/gate_m4_hazard_v1.json": "gate_m4",
    "runs/gate_w1_candidate1_v1.json": "gate_w1",
    "runs/gate_w1_candidate2_v1.json": "gate_w1",
    "runs/gate_w1_candidate3_v1.json": "gate_w1",
    "runs/gate_w1_candidate4_v1.json": "gate_w1",
}
EXPECTED_IMPORT_GATES = {
    "gate_m6",
    "B2",
    "gate_epuf_fill",
    "gate_m4",
    "gate_w1",
}


def committed() -> dict:
    return registry.load(ROOT)


def by_id(current: dict) -> dict:
    return {entry["id"]: entry for entry in current["entries"]}


def test_the_committed_registry_keeps_its_rules():
    assert registry.validate(committed(), ROOT) == []


def resolved_base():
    try:
        return registry.base_commit(ROOT)
    except LookupError as error:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail(f"CI must resolve the base commit: {error}")
        pytest.skip(f"no base commit here: {error}")


def test_the_committed_registry_only_appends_to_its_base():
    base_commit = resolved_base()
    base = registry.registry_at(ROOT, base_commit)
    current = committed()
    if base is None:
        assert (
            registry.append_only_problems(
                registry.empty_like(current), current
            )
            == []
        )
    else:
        assert registry.validate(base, vocabulary=base["sources"]) == []
        assert registry.append_only_problems(base, current) == []


def test_a_pull_requests_own_commits_append_only():
    head = registry.pull_request_head()
    if head is None:
        pytest.skip("not a pull_request event")
    base_commit = resolved_base()
    if registry.registry_at(ROOT, base_commit) is None:
        pytest.skip(
            "the registry is new in this pull request, which is merged with "
            "a merge commit; its endpoint is admitted against an empty "
            "registry above"
        )
    assert registry.history_problems(ROOT, base_commit, head, full=False) == []


def test_every_first_parent_commit_since_the_base_appends_only():
    if os.environ.get("GITHUB_EVENT_NAME") != "push":
        pytest.skip(
            "a pull request is checked at its merge commit; a branch's own "
            "draft commits are not the base branch's history"
        )
    assert registry.history_problems(ROOT, resolved_base()) == []


def test_the_registry_stays_incomplete_until_the_inventory_lands():
    current = committed()
    assert current["schema"] == registry.SCHEMA
    if not (ROOT / current["completion_record"]).is_file():
        assert current["complete"] is False
        assert any("incomplete" in rule for rule in current["rules"])


def test_the_seeded_unit_keys_are_as_specified():
    entries = by_id(committed())
    for name, keys in EXPECTED_SEED_KEYS.items():
        assert entries[name]["unit_keys"] == keys


def test_the_seeded_disclosures_are_as_specified():
    pairs = {
        tuple(sorted((entry["id"], other)))
        for entry in committed()["entries"]
        for other in entry["disclosed_overlaps"]
    }
    assert pairs == EXPECTED_DISCLOSURES
    entries = by_id(committed())
    for a, b in EXPECTED_DISCLOSURES - {("H003", "H004"), ("H003", "H005")}:
        assert registry.entries_overlap(entries[a], entries[b])


def test_the_vocabulary_and_registrations_are_as_specified():
    assert {
        source: declared["family"]
        for source, declared in registry.SOURCES.items()
    } == EXPECTED_FAMILIES
    assert dict(registry.REGISTRATIONS_OUTSIDE_GATES_YAML) == (
        EXPECTED_OUTSIDE_GATES_YAML
    )
    assert committed()["sources"] == {
        source: dict(declared) for source, declared in registry.SOURCES.items()
    }


def test_the_scored_runs_and_import_gates_are_as_specified():
    assert {
        path: gate for path, (gate, _) in registry.SCORED_RUNS.items()
    } == EXPECTED_SCORED_RUN_GATES
    assert set(registry.HISTORICAL_IMPORT_GATES) == EXPECTED_IMPORT_GATES
    for path, (_, digest) in registry.SCORED_RUNS.items():
        content = (ROOT / path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == digest, path


def test_every_used_entry_cites_committed_run_artifacts():
    for entry in committed()["entries"]:
        if entry["status"] == "used":
            assert entry["scored_evidence"], entry["id"]
            for item in entry["scored_evidence"]:
                relative = item["path"]
                assert relative.startswith("runs/"), relative
                assert relative.endswith(".json"), relative
                assert (ROOT / relative).is_file(), relative
