"""The held-out data registry keeps its rules on every commit.

``docs/design/track_b_holdout_registry.json`` is the single registry of
held-out years, editions, tables and partitions for Track B's gates and
the open-population lane's gates (dynamics coordinator, 2026-10-21).
``populace_dynamics.track_b.holdout_registry`` states the rules; these
tests run them on the committed registry, against its base branch, and
as properties over invented registries.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import holdout_registry as registry

ROOT = Path(__file__).resolve().parents[1]


def committed() -> dict:
    return registry.load(ROOT)


def test_the_committed_registry_keeps_its_rules():
    assert registry.validate(committed(), ROOT) == []


def test_the_committed_registry_only_appends_to_its_base():
    try:
        base = registry.base_registry(ROOT)
    except LookupError as error:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail(f"CI must resolve the base registry: {error}")
        pytest.skip(f"no base branch here: {error}")
    if base is None:
        return
    assert registry.validate(base) == []
    assert registry.append_only_problems(base, committed()) == []


def test_the_registry_stays_incomplete_until_the_inventory_lands():
    current = committed()
    assert current["schema"] == registry.SCHEMA
    record = ROOT / current["completion_record"]
    if not record.is_file():
        assert current["complete"] is False
        assert any("incomplete" in rule for rule in current["rules"])


def test_the_shared_di_report_edition_is_disclosed_both_ways():
    by_id = {entry["id"]: entry for entry in committed()["entries"]}
    m4, w1 = by_id["H004"], by_id["H005"]
    assert registry.entries_overlap(m4, w1)
    assert "H005" in m4["disclosed_overlaps"]
    assert "H004" in w1["disclosed_overlaps"]


def test_every_used_entry_names_committed_scored_artifacts():
    for entry in committed()["entries"]:
        if entry["status"] == "used":
            assert entry["scored_evidence"], entry["id"]
            for relative in entry["scored_evidence"]:
                assert (ROOT / relative).is_file(), relative


# Invented registries ------------------------------------------------------

KEY_POOL = (
    "alpha",
    "alpha:2020",
    "alpha:2021",
    "alpha:2021:t1",
    "beta:x",
    "beta:y",
    "beta:y:z",
    "gamma:p",
)
PATHS = {
    "candidate": ["candidate"],
    "frozen": ["candidate", "frozen"],
    "used": ["candidate", "frozen", "used"],
    "withdrawn": ["candidate", "withdrawn"],
    "seeded_used": ["used"],
}


def make_entry(index: int, keys: list[str], path: str) -> dict:
    statuses = PATHS[path]
    return {
        "id": f"H{index + 1:03d}",
        "gate": f"gate_{index}",
        "lane": "invented",
        "status": statuses[-1],
        "source": "invented source",
        "unit_kind": "reference_years",
        "units": {"years": [index]},
        "unit_keys": keys,
        "evidence": [f"evidence {index}"],
        "scored_evidence": (
            [f"scores/score_{index}.txt"] if statuses[-1] == "used" else []
        ),
        "disclosed_overlaps": [],
        "history": [
            {"date": f"2026-10-{20 + step:02d}", "status": s, "note": "n"}
            for step, s in enumerate(statuses)
        ],
    }


def disclose_all(entries: list[dict]) -> None:
    """Disclose every overlap between live entries, both ways."""
    live = [entry for entry in entries if entry["status"] != "withdrawn"]
    for index, entry in enumerate(live):
        for other in live[index + 1 :]:
            if registry.entries_overlap(entry, other):
                if other["id"] not in entry["disclosed_overlaps"]:
                    entry["disclosed_overlaps"].append(other["id"])
                if entry["id"] not in other["disclosed_overlaps"]:
                    other["disclosed_overlaps"].append(entry["id"])


def make_registry(entries: list[dict]) -> dict:
    return {
        "schema": registry.SCHEMA,
        "title": "invented",
        "purpose": "invented",
        "rules": ["rule one", "the registry is incomplete"],
        "status_values": {status: status for status in registry.STATUSES},
        "complete": False,
        "completion_record": "docs/design/inventory.json",
        "entries": entries,
    }


entry_specs = st.lists(
    st.tuples(
        st.lists(
            st.sampled_from(KEY_POOL), min_size=1, max_size=3, unique=True
        ),
        st.sampled_from(sorted(PATHS)),
    ),
    min_size=0,
    max_size=6,
)


def build(specs) -> dict:
    entries = [
        make_entry(i, keys, path) for i, (keys, path) in enumerate(specs)
    ]
    disclose_all(entries)
    return make_registry(entries)


@settings(max_examples=150, deadline=None)
@given(entry_specs)
def test_invented_registries_that_disclose_every_overlap_are_valid(specs):
    assert registry.validate(build(specs)) == []


@settings(max_examples=150, deadline=None)
@given(entry_specs, st.data())
def test_a_one_way_disclosure_is_refused(specs, data):
    current = build(specs)
    disclosing = [e for e in current["entries"] if e["disclosed_overlaps"]]
    if not disclosing:
        return
    entry = data.draw(st.sampled_from(disclosing))
    entry["disclosed_overlaps"].pop()
    problems = registry.validate(current)
    assert problems
    assert any(
        "does not disclose it back" in p or "without disclosing" in p
        for p in problems
    )


@settings(max_examples=150, deadline=None)
@given(entry_specs)
def test_a_silent_shared_unit_is_refused(specs):
    current = build(specs)
    for entry in current["entries"]:
        entry["disclosed_overlaps"] = []
    live = [e for e in current["entries"] if e["status"] != "withdrawn"]
    shared = any(
        registry.entries_overlap(a, b)
        for i, a in enumerate(live)
        for b in live[i + 1 :]
    )
    problems = registry.validate(current)
    assert bool(problems) == shared
    if shared:
        assert any("without disclosing" in p for p in problems)


@settings(max_examples=150, deadline=None)
@given(entry_specs, entry_specs)
def test_appending_disclosed_entries_keeps_every_rule(base_specs, more):
    base = build(base_specs)
    current = copy.deepcopy(base)
    start = len(current["entries"])
    for offset, (keys, path) in enumerate(more):
        current["entries"].append(make_entry(start + offset, keys, path))
    disclose_all(current["entries"])
    assert registry.validate(current) == []
    assert registry.append_only_problems(base, current) == []


IMMUTABLE_EDITS = {
    "id": "H999",
    "gate": "gate_other",
    "lane": "other lane",
    "source": "other source",
    "unit_kind": "person_partition",
    "units": {"years": [-1]},
    "unit_keys": ["delta:other"],
}


@settings(max_examples=150, deadline=None)
@given(
    entry_specs.filter(bool),
    st.sampled_from(registry.IMMUTABLE),
    st.data(),
)
def test_changing_an_earlier_entry_is_refused(specs, key, data):
    base = build(specs)
    current = copy.deepcopy(base)
    entry = data.draw(st.sampled_from(current["entries"]))
    entry[key] = IMMUTABLE_EDITS[key]
    assert registry.append_only_problems(base, current)


@settings(max_examples=150, deadline=None)
@given(entry_specs.filter(bool), st.data())
def test_removing_or_reordering_entries_is_refused(specs, data):
    base = build(specs)
    removed = copy.deepcopy(base)
    del removed["entries"][data.draw(st.integers(0, len(specs) - 1))]
    assert registry.append_only_problems(base, removed)
    if len(specs) > 1:
        reordered = copy.deepcopy(base)
        reordered["entries"].reverse()
        assert registry.append_only_problems(base, reordered)


@settings(max_examples=150, deadline=None)
@given(
    entry_specs.filter(bool),
    st.sampled_from(registry.EXTENDING),
    st.data(),
)
def test_extending_lists_never_shrink(specs, key, data):
    base = build(specs)
    current = copy.deepcopy(base)
    entry = data.draw(st.sampled_from(current["entries"]))
    if not entry[key]:
        entry[key] = ["something new"]
        base_entry = base["entries"][current["entries"].index(entry)]
        base_entry[key] = ["something old"]
    else:
        entry[key] = entry[key][1:]
    assert registry.append_only_problems(base, current)


def test_rules_and_completeness_only_move_forward():
    base = make_registry([])
    trimmed = copy.deepcopy(base)
    trimmed["rules"] = trimmed["rules"][1:]
    assert registry.append_only_problems(base, trimmed)
    done = copy.deepcopy(base)
    done["complete"] = True
    assert registry.append_only_problems(base, done) == []
    assert registry.append_only_problems(done, base)
    renamed = copy.deepcopy(base)
    renamed["schema"] = "track_b_holdout_registry.v2"
    assert registry.append_only_problems(base, renamed)


def test_repeated_ids_are_refused():
    current = build([(["alpha"], "candidate"), (["beta:x"], "candidate")])
    current["entries"][1]["id"] = "H001"
    assert any("ids repeat" in p for p in registry.validate(current))


@pytest.mark.parametrize(
    "statuses, last, message",
    [
        (["candidate", "used"], "used", "not a legal transition"),
        (["used", "candidate"], "candidate", "not a legal transition"),
        (["withdrawn", "frozen"], "frozen", "not a legal transition"),
        (["candidate", "frozen"], "candidate", "is not its history's last"),
    ],
)
def test_status_follows_a_legal_history(statuses, last, message):
    entry = make_entry(0, ["alpha"], "candidate")
    entry["history"] = [
        {"date": "2026-10-21", "status": s, "note": "n"} for s in statuses
    ]
    entry["status"] = last
    entry["scored_evidence"] = ["x"] if last == "used" else []
    assert any(message in p for p in registry.validate(make_registry([entry])))


def test_history_dates_never_go_back():
    entry = make_entry(0, ["alpha"], "frozen")
    entry["history"][1]["date"] = "2026-10-01"
    problems = registry.validate(make_registry([entry]))
    assert any("goes back in time" in p for p in problems)


def test_a_used_entry_needs_committed_scored_evidence(tmp_path):
    entry = make_entry(0, ["alpha"], "used")
    current = make_registry([entry])
    assert registry.validate(current) == []
    assert any(
        "not a committed file" in p
        for p in registry.validate(current, tmp_path)
    )
    score = tmp_path / entry["scored_evidence"][0]
    score.parent.mkdir(parents=True)
    score.write_text("scored", encoding="utf-8")
    assert registry.validate(current, tmp_path) == []
    entry["scored_evidence"] = []
    assert any(
        "needs scored_evidence" in p
        for p in registry.validate(current, tmp_path)
    )
    entry["scored_evidence"] = ["../outside.txt"]
    assert any(
        "not a committed file" in p
        for p in registry.validate(current, tmp_path)
    )


def test_complete_needs_its_completion_record(tmp_path):
    current = make_registry([])
    current["complete"] = True
    assert any(
        "does not exist" in p for p in registry.validate(current, tmp_path)
    )
    record = tmp_path / current["completion_record"]
    record.parent.mkdir(parents=True)
    record.write_text("{}", encoding="utf-8")
    assert registry.validate(current, tmp_path) == []


@given(st.sampled_from(KEY_POOL), st.sampled_from(KEY_POOL))
def test_key_overlap_is_symmetric_and_prefix_based(a, b):
    assert registry.keys_overlap(a, a)
    assert registry.keys_overlap(a, b) == registry.keys_overlap(b, a)
    left, right = a.split(":"), b.split(":")
    shorter = min(len(left), len(right))
    assert registry.keys_overlap(a, b) == (left[:shorter] == right[:shorter])


def test_an_edition_overlaps_its_tables_but_not_its_neighbours():
    assert registry.keys_overlap("ssa_di_asr:2023", "ssa_di_asr:2023:table_19")
    assert not registry.keys_overlap("ssa_di_asr:2023", "ssa_di_asr:2024")
    assert not registry.keys_overlap("alpha:2021", "alpha:2021x")


# The base registry, read through git --------------------------------------


def git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def init_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repo"
    repository.mkdir()
    git(repository, "init", "-q", "-b", "master")
    git(repository, "config", "user.email", "t@example.com")
    git(repository, "config", "user.name", "t")
    (repository / "README").write_text("r", encoding="utf-8")
    git(repository, "add", "README")
    git(repository, "commit", "-q", "-m", "start")
    return repository


def write_registry(repository: Path, current: dict) -> None:
    path = repository / registry.REGISTRY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current), encoding="utf-8")


def test_the_base_registry_is_read_at_the_merge_base(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    repository = init_repository(tmp_path)
    git(repository, "checkout", "-q", "-b", "feature")
    assert registry.base_registry(repository) is None
    git(repository, "checkout", "-q", "master")
    first = build([(["alpha"], "candidate")])
    write_registry(repository, first)
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "registry")
    git(repository, "checkout", "-q", "-b", "feature-2")
    second = copy.deepcopy(first)
    second["entries"].append(make_entry(1, ["beta:x"], "candidate"))
    write_registry(repository, second)
    git(repository, "commit", "-q", "-am", "append")
    assert registry.base_registry(repository) == first


def test_no_base_branch_raises_rather_than_passing(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_BASE_REF", "no-such-branch")
    repository = init_repository(tmp_path)
    with pytest.raises(LookupError):
        registry.base_registry(repository)
