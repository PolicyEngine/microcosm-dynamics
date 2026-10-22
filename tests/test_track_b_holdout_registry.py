"""The held-out data registry keeps its rules on every commit.

``docs/design/track_b_holdout_registry.json`` is the single registry of
the data that Track B's gates and the open-population lane's gates hold
out (dynamics coordinator, 2026-10-21).
``populace_dynamics.track_b.holdout_registry`` states the rules; these
tests run them on the committed registry, against its base commit, and as
properties over invented registries.
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

#: Specified here, independently of the module, so that dropping a field
#: from the module's lists fails a test.
EXPECTED_IMMUTABLE = (
    "id",
    "provenance",
    "gate",
    "lane",
    "source",
    "units",
    "unit_keys",
)
EXPECTED_EXTENDING = (
    "gate_identifiers",
    "evidence",
    "scored_evidence",
    "disclosed_overlaps",
    "overlap_review",
    "history",
)


def committed() -> dict:
    return registry.load(ROOT)


def by_id(current: dict) -> dict:
    return {entry["id"]: entry for entry in current["entries"]}


# The committed registry ----------------------------------------------------


def test_the_committed_registry_keeps_its_rules():
    assert registry.validate(committed(), ROOT) == []


def test_the_committed_registry_only_appends_to_its_base():
    try:
        base = registry.base_registry(ROOT)
    except LookupError as error:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail(f"CI must resolve the base registry: {error}")
        pytest.skip(f"no base commit here: {error}")
    if base is None:
        return
    assert registry.validate(base) == []
    assert registry.append_only_problems(base, committed()) == []


def test_the_registry_stays_incomplete_until_the_inventory_lands():
    current = committed()
    assert current["schema"] == registry.SCHEMA
    if not (ROOT / current["completion_record"]).is_file():
        assert current["complete"] is False
        assert any("incomplete" in rule for rule in current["rules"])


@pytest.mark.parametrize(
    "a, b",
    [("H001", "H002"), ("H001", "H004"), ("H002", "H004"), ("H004", "H005")],
)
def test_the_seeded_shared_units_are_disclosed_both_ways(a, b):
    entries = by_id(committed())
    assert registry.entries_overlap(entries[a], entries[b])
    assert b in entries[a]["disclosed_overlaps"]
    assert a in entries[b]["disclosed_overlaps"]


def test_the_field_lists_are_as_specified():
    assert registry.IMMUTABLE == EXPECTED_IMMUTABLE
    assert registry.EXTENDING == EXPECTED_EXTENDING
    assert set(EXPECTED_IMMUTABLE) | set(EXPECTED_EXTENDING) | {
        "status",
    } == set(registry.ENTRY_KEYS)


# Invented registries -------------------------------------------------------

SOURCES = {
    "s_a": {"family": "f1", "title": "A", "catalog": "cat a", "key_year": "y"},
    "s_b": {"family": "f1", "title": "B", "catalog": "cat b", "key_year": "y"},
    "s_c": {"family": "f2", "title": "C", "catalog": "cat c", "key_year": "y"},
}
KEY_POOL = (
    "s_a:2020",
    "s_a:2020-2022:x",
    "s_a:2023",
    "s_a:undated",
    "s_b:2021:t1",
    "s_b:2025",
    "s_c:2020",
    "s_c:2030-2031",
)
PATHS = {
    ("registration", "candidate"): ["candidate"],
    ("registration", "frozen"): ["candidate", "frozen"],
    ("registration", "used"): ["candidate", "frozen", "used"],
    ("registration", "withdrawn"): ["candidate", "withdrawn"],
    ("historical_import", "used"): ["used"],
    ("historical_import", "frozen"): ["frozen"],
    ("historical_import", "frozen_used"): ["frozen", "used"],
}


def make_entry(
    index: int, keys: list[str], path=("registration", "candidate")
):
    statuses = PATHS[path]
    gate = f"gate_{index}"
    return {
        "id": f"H{index + 1:03d}",
        "provenance": path[0],
        "gate": gate,
        "gate_identifiers": [gate],
        "lane": "invented",
        "status": statuses[-1],
        "source": "invented source",
        "units": {"years": [index]},
        "unit_keys": list(keys),
        "evidence": [f"evidence {index}"],
        "scored_evidence": (
            [
                {
                    "path": f"scores/s{index}.json",
                    "field": "gate",
                    "equals": gate,
                }
            ]
            if statuses[-1] == "used"
            else []
        ),
        "disclosed_overlaps": [],
        "overlap_review": [],
        "history": [
            {"date": f"2026-10-{20 + step:02d}", "status": s, "note": "n"}
            for step, s in enumerate(statuses)
        ],
    }


def settle(entries: list[dict], sources=SOURCES) -> None:
    """Disclose every shared unit both ways, and review every unshared
    same-family relation, as a careful registrant would."""
    live = [entry for entry in entries if entry["status"] != "withdrawn"]
    for index, entry in enumerate(live):
        for other in live[index + 1 :]:
            if registry.entries_overlap(entry, other):
                if other["id"] not in entry["disclosed_overlaps"]:
                    entry["disclosed_overlaps"].append(other["id"])
                if entry["id"] not in other["disclosed_overlaps"]:
                    other["disclosed_overlaps"].append(entry["id"])
    for index, entry in enumerate(entries):
        if entry["status"] == "withdrawn":
            continue
        reviewed = {item["id"] for item in entry["overlap_review"]}
        for other in entries[:index]:
            if (
                other["status"] != "withdrawn"
                and registry.families(entry, sources)
                & registry.families(other, sources)
                and not registry.entries_overlap(entry, other)
                and other["id"] not in entry["disclosed_overlaps"]
                and other["id"] not in reviewed
            ):
                entry["overlap_review"].append(
                    {"id": other["id"], "reason": "different years"}
                )


def make_registry(entries: list[dict], complete=False) -> dict:
    return {
        "schema": registry.SCHEMA,
        "title": "invented",
        "purpose": "invented",
        "rules": ["rule one", "the registry is incomplete"],
        "status_values": {status: status for status in registry.STATUSES},
        "sources": copy.deepcopy(SOURCES),
        "complete": complete,
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
registration_specs = st.lists(
    st.lists(st.sampled_from(KEY_POOL), min_size=1, max_size=3, unique=True),
    min_size=0,
    max_size=4,
)


def build(specs, complete=False) -> dict:
    entries = [
        make_entry(i, keys, path) for i, (keys, path) in enumerate(specs)
    ]
    settle(entries)
    return make_registry(entries, complete)


def shared_pairs(entries):
    live = [e for e in entries if e["status"] != "withdrawn"]
    return [
        (a, b)
        for i, a in enumerate(live)
        for b in live[i + 1 :]
        if registry.entries_overlap(a, b)
    ]


@settings(max_examples=200, deadline=None)
@given(entry_specs)
def test_settled_registries_are_valid(specs):
    assert registry.validate(build(specs)) == []


@settings(max_examples=200, deadline=None)
@given(entry_specs, st.data())
def test_a_one_way_disclosure_is_refused(specs, data):
    current = build(specs)
    disclosing = [e for e in current["entries"] if e["disclosed_overlaps"]]
    if not disclosing:
        return
    data.draw(st.sampled_from(disclosing))["disclosed_overlaps"].pop()
    problems = registry.validate(current)
    assert any(
        "does not disclose it back" in p or "without disclosing" in p
        for p in problems
    )


@settings(max_examples=200, deadline=None)
@given(entry_specs)
def test_a_silent_shared_unit_is_refused(specs):
    current = build(specs)
    for entry in current["entries"]:
        entry["disclosed_overlaps"] = []
    settle_reviews_only(current["entries"])
    problems = registry.validate(current)
    shared = bool(shared_pairs(current["entries"]))
    assert any("without disclosing" in p for p in problems) == shared


def settle_reviews_only(entries):
    for entry in entries:
        entry["overlap_review"] = []
    for index, entry in enumerate(entries):
        if entry["status"] == "withdrawn":
            continue
        for other in entries[:index]:
            if (
                other["status"] != "withdrawn"
                and registry.families(entry, SOURCES)
                & registry.families(other, SOURCES)
                and not registry.entries_overlap(entry, other)
            ):
                entry["overlap_review"].append(
                    {"id": other["id"], "reason": "different years"}
                )


@settings(max_examples=200, deadline=None)
@given(entry_specs)
def test_an_unreviewed_family_relation_is_refused(specs):
    current = build(specs)
    entries = current["entries"]
    needed = any(entry["overlap_review"] for entry in entries)
    for entry in entries:
        entry["overlap_review"] = []
    problems = registry.validate(current)
    assert any("neither discloses nor reviews" in p for p in problems) == (
        needed
    )


@settings(max_examples=200, deadline=None)
@given(entry_specs, registration_specs)
def test_appending_lone_candidates_keeps_every_rule(base_specs, more):
    base = build(base_specs)
    current = copy.deepcopy(base)
    start = len(current["entries"])
    for offset, keys in enumerate(more):
        current["entries"].append(make_entry(start + offset, keys))
    settle(current["entries"])
    assert registry.validate(current) == []
    assert registry.append_only_problems(base, current) == []


@settings(max_examples=100, deadline=None)
@given(
    entry_specs,
    st.sampled_from(
        [p for p in PATHS if p[0] == "registration" and p[1] != "candidate"]
    ),
)
def test_a_registration_cannot_arrive_already_frozen(base_specs, path):
    base = build(base_specs)
    current = copy.deepcopy(base)
    current["entries"].append(
        make_entry(len(current["entries"]), ["s_c:2099"], path)
    )
    settle(current["entries"])
    assert registry.validate(current) == []
    assert any(
        "lone candidate" in p
        for p in registry.append_only_problems(base, current)
    )


def test_imports_close_when_the_registry_is_complete():
    for complete in (False, True):
        base = build([(["s_a:2020"], ("historical_import", "used"))], complete)
        current = copy.deepcopy(base)
        current["entries"].append(
            make_entry(1, ["s_c:2099"], ("historical_import", "used"))
        )
        problems = registry.append_only_problems(base, current)
        assert bool(problems) == complete


IMMUTABLE_EDITS = {
    "id": "H999",
    "provenance": "registration",
    "gate": "gate_other",
    "lane": "other lane",
    "source": "other source",
    "units": {"years": [-1]},
    "unit_keys": ["s_c:2199"],
}


@settings(max_examples=150, deadline=None)
@given(
    entry_specs.filter(bool),
    st.sampled_from(sorted(IMMUTABLE_EDITS)),
    st.data(),
)
def test_changing_an_earlier_entry_is_refused(specs, key, data):
    base = build(specs)
    current = copy.deepcopy(base)
    entry = data.draw(st.sampled_from(current["entries"]))
    if entry[key] == IMMUTABLE_EDITS[key]:
        return
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
    st.sampled_from(EXPECTED_EXTENDING),
    st.data(),
)
def test_extending_lists_never_shrink(specs, key, data):
    base = build(specs)
    current = copy.deepcopy(base)
    index = data.draw(st.integers(0, len(specs) - 1))
    if not base["entries"][index][key]:
        base["entries"][index][key] = ["something old"]
        current["entries"][index][key] = ["something new"]
    else:
        current["entries"][index][key] = current["entries"][index][key][1:]
    assert registry.append_only_problems(base, current)


def test_sources_rules_and_completeness_only_move_forward():
    base = make_registry([])
    for change in ("remove", "edit"):
        edited = copy.deepcopy(base)
        if change == "remove":
            del edited["sources"]["s_b"]
        else:
            edited["sources"]["s_b"]["family"] = "f2"
        assert registry.append_only_problems(base, edited)
    added = copy.deepcopy(base)
    added["sources"]["s_d"] = {
        "family": "f3",
        "title": "D",
        "catalog": "cat d",
        "key_year": "y",
    }
    assert registry.append_only_problems(base, added) == []
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


def test_an_alias_source_is_refused():
    current = make_registry([])
    current["sources"]["s_d"] = dict(SOURCES["s_a"], catalog="  CAT   A ")
    assert any("alias" in p for p in registry.validate(current))


@given(
    st.sampled_from(sorted(SOURCES)),
    st.integers(1900, 2100),
    st.integers(0, 5),
    st.integers(1900, 2100),
    st.integers(0, 5),
    st.booleans(),
)
def test_keys_overlap_on_source_and_intersecting_years(s, y1, n1, y2, n2, x):
    a = f"{s}:{y1}-{y1 + n1}:alpha"
    b = f"{s}:{y2}-{y2 + n2}" + (":beta" if x else "")
    intersect = y1 <= y2 + n2 and y2 <= y1 + n1
    assert registry.keys_overlap(a, b) == intersect
    assert registry.keys_overlap(b, a) == intersect
    assert registry.keys_overlap(a, f"{s}:undated")
    other = "s_c" if s != "s_c" else "s_a"
    assert not registry.keys_overlap(a, f"{other}:{y1}")


@pytest.mark.parametrize(
    "key",
    [
        "s_a",
        "s_a:20",
        "s_a:2022-2020",
        "s_a:2020:Upper",
        "S_A:2020",
        "s_a:2020::x",
        "s_a:dated",
        7,
    ],
)
def test_malformed_unit_keys_are_refused(key):
    entry = make_entry(0, ["s_a:2020"])
    entry["unit_keys"] = [key]
    assert registry.validate(make_registry([entry]))


def test_a_key_naming_no_source_is_refused():
    entry = make_entry(0, ["s_z:2020"])
    problems = registry.validate(make_registry([entry]))
    assert any("names no source" in p for p in problems)


@pytest.mark.parametrize(
    "provenance, statuses, last, message",
    [
        ("registration", ["frozen"], "frozen", "starts as one of"),
        ("historical_import", ["candidate"], "candidate", "starts as one of"),
        ("registration", ["candidate", "used"], "used", "not a legal"),
        ("historical_import", ["used", "frozen"], "frozen", "not a legal"),
        ("registration", ["candidate", "frozen"], "candidate", "last status"),
    ],
)
def test_status_follows_a_legal_history(provenance, statuses, last, message):
    entry = make_entry(0, ["s_a:2020"])
    entry["provenance"] = provenance
    entry["history"] = [
        {"date": "2026-10-21", "status": s, "note": "n"} for s in statuses
    ]
    entry["status"] = last
    if last == "used":
        entry["scored_evidence"] = [
            {"path": "s.json", "field": "gate", "equals": "gate_0"}
        ]
    assert any(message in p for p in registry.validate(make_registry([entry])))


@pytest.mark.parametrize("date", ["2026-10-01", "2026-99-99", "yesterday"])
def test_history_dates_are_real_and_never_go_back(date):
    entry = make_entry(0, ["s_a:2020"], ("registration", "frozen"))
    entry["history"][1]["date"] = date
    assert registry.validate(make_registry([entry]))


def test_repeated_ids_and_shared_gate_identifiers_are_refused():
    current = build([(["s_a:2020"], ("registration", "candidate"))] * 2)
    current["entries"][1]["id"] = "H001"
    assert any("ids repeat" in p for p in registry.validate(current))
    current = build([(["s_a:2020"], ("registration", "candidate"))] * 2)
    current["entries"][1]["gate_identifiers"].append("gate_0")
    assert any("already identifies" in p for p in registry.validate(current))


def test_scored_evidence_must_name_this_gate():
    entry = make_entry(0, ["s_a:2020"], ("historical_import", "used"))
    entry["scored_evidence"][0]["equals"] = "gate_other"
    problems = registry.validate(make_registry([entry]))
    assert any("not this gate" in p for p in problems)
    entry["scored_evidence"] = []
    problems = registry.validate(make_registry([entry]))
    assert any("needs scored_evidence" in p for p in problems)


def test_a_review_must_name_an_earlier_entry():
    current = build(
        [(["s_a:2020"], ("registration", "candidate"))]
        + [(["s_b:2025"], ("registration", "candidate"))]
    )
    first = current["entries"][0]
    first["overlap_review"].append({"id": "H002", "reason": "later"})
    problems = registry.validate(current)
    assert any("not an earlier entry" in p for p in problems)


@pytest.mark.parametrize(
    "path, value",
    [
        ((), None),
        (("title",), None),
        (("purpose",), []),
        (("rules",), []),
        (("status_values", "used"), 3),
        (("sources", "s_a", "family"), ""),
        (("complete",), "no"),
        (("entries", 0, "scored_evidence"), 7),
        (("entries", 0, "history"), "used"),
        (("entries", 0, "history", 0), "used"),
        (("entries", 0, "units"), {}),
        (("entries", 0, "gate"), None),
        (("entries", 0, "overlap_review"), [{"id": "H001"}]),
        (("entries", 0, "disclosed_overlaps"), [3]),
    ],
)
def test_malformed_fields_are_reported_not_raised(path, value):
    current = build([(["s_a:2020"], ("historical_import", "used"))])
    if not path:
        current = value
    else:
        target = current
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
    problems = registry.validate(current)
    assert isinstance(problems, list) and problems


json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=8),
    lambda children: st.lists(children, max_size=4)
    | st.dictionaries(st.text(max_size=8), children, max_size=4),
    max_leaves=20,
)


@settings(max_examples=200, deadline=None)
@given(st.sampled_from(sorted(registry.ENTRY_KEYS) + ["entries"]), json_values)
def test_any_json_in_any_field_is_reported_not_raised(key, value):
    base = build([(["s_a:2020"], ("historical_import", "used"))])
    current = copy.deepcopy(base)
    if key == "entries":
        current["entries"] = value
    else:
        current["entries"][0][key] = value
    assert isinstance(registry.validate(current), list)
    assert isinstance(registry.append_only_problems(base, current), list)


# Committed files and base commits, through git ----------------------------


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


def write(repository: Path, relative: str, document) -> None:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    text = document if isinstance(document, str) else json.dumps(document)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def no_ci_env(monkeypatch):
    for name in ("GITHUB_BASE_REF", "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH"):
        monkeypatch.delenv(name, raising=False)


def test_scored_evidence_must_be_committed_and_identify_the_gate(
    tmp_path, no_ci_env
):
    repository = init_repository(tmp_path)
    entry = make_entry(0, ["s_a:2020"], ("historical_import", "used"))
    current = make_registry([entry])
    evidence = entry["scored_evidence"][0]
    write(repository, evidence["path"], {"gate": "gate_0"})
    assert any(
        "not committed" in p for p in registry.validate(current, repository)
    )
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "score")
    assert registry.validate(current, repository) == []
    write(repository, "scores/other.json", {"gate": "gate_9"})
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "other")
    evidence["path"] = "scores/other.json"
    assert any(
        "does not have gate" in p
        for p in registry.validate(current, repository)
    )
    write(repository, "scores/text.json", "not json")
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "text")
    evidence["path"] = "scores/text.json"
    assert any("not JSON" in p for p in registry.validate(current, repository))
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"gate": "gate_0"}), encoding="utf-8")
    (repository / "scores" / "link.json").symlink_to(outside)
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "link")
    evidence["path"] = "scores/link.json"
    assert any("symlink" in p for p in registry.validate(current, repository))
    for path in ("../outside.json", "/etc/hosts", "~/x.json"):
        evidence["path"] = path
        assert any(
            "outside the repository" in p
            for p in registry.validate(current, repository)
        )


def test_complete_needs_its_completion_record(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    current = make_registry([], complete=True)
    assert any(
        "does not exist" in p for p in registry.validate(current, repository)
    )
    write(repository, current["completion_record"], {})
    assert registry.validate(current, repository) == []


def commit_registry(repository: Path, current: dict, message: str) -> str:
    write(repository, registry.REGISTRY, current)
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", message)
    return git(repository, "rev-parse", "HEAD").strip()


def test_a_pull_request_compares_with_its_merge_base(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    git(repository, "checkout", "-q", "-b", "feature")
    write(repository, "notes.txt", "a commit of the branch's own")
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "feature work")
    assert registry.base_registry(repository) is None
    git(repository, "checkout", "-q", "master")
    first = build([(["s_a:2020"], ("historical_import", "used"))])
    commit_registry(repository, first, "registry")
    git(repository, "checkout", "-q", "-b", "feature-2")
    second = copy.deepcopy(first)
    second["entries"].append(make_entry(1, ["s_c:2099"]))
    commit_registry(repository, second, "append")
    assert registry.base_registry(repository) == first


def test_the_base_branch_compares_with_its_parent(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    first = build([(["s_a:2020"], ("historical_import", "used"))])
    commit_registry(repository, first, "registry")
    emptied = copy.deepcopy(first)
    emptied["entries"] = []
    commit_registry(repository, emptied, "delete H001")
    base = registry.base_registry(repository)
    assert base == first
    assert registry.append_only_problems(base, emptied)


def test_a_push_compares_with_its_before_commit(
    tmp_path, no_ci_env, monkeypatch
):
    repository = init_repository(tmp_path)
    first = build([(["s_a:2020"], ("historical_import", "used"))])
    before = commit_registry(repository, first, "registry")
    middle = copy.deepcopy(first)
    middle["entries"].append(make_entry(1, ["s_c:2099"]))
    commit_registry(repository, middle, "append")
    emptied = copy.deepcopy(first)
    emptied["entries"] = []
    commit_registry(repository, emptied, "delete everything")
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"before": before}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert registry.base_commit(repository) == before
    assert registry.append_only_problems(
        registry.base_registry(repository), emptied
    )
    event.write_text(json.dumps({"before": "0" * 40}), encoding="utf-8")
    assert registry.base_registry(repository) == middle


def test_no_base_raises_rather_than_passing(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.setenv("GITHUB_BASE_REF", "no-such-branch")
    repository = init_repository(tmp_path)
    with pytest.raises(LookupError):
        registry.base_registry(repository)
    monkeypatch.delenv("GITHUB_BASE_REF")
    with pytest.raises(LookupError):
        registry.base_registry(repository)
