"""The held-out data registry's rules, on invented registries.

``populace_dynamics.track_b.holdout_registry`` states the rules of the
single held-out data registry (dynamics coordinator, 2026-10-21). These
tests exercise them on invented registries and invented git repositories,
with the expected families and overlaps worked out here, independently
of the module. The committed registry itself is checked in
``test_track_b_holdout_registry_committed.py``.
"""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import holdout_registry as registry

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
VOCABULARY = {
    "s_a": {"family": "f1", "title": "A", "catalog": "cat a", "key_year": "y"},
    "s_b": {"family": "f1", "title": "B", "catalog": "cat b", "key_year": "y"},
    "s_c": {"family": "f2", "title": "C", "catalog": "cat c", "key_year": "y"},
}
#: The family of each invented source, independently of the module.
FAMILY = {"s_a": "f1", "s_b": "f1", "s_c": "f2"}
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
}
REASON = (
    "The two units come from different years of separate sources, so no "
    "observation is shared."
)


def run_path(name: str) -> str:
    return f"{registry.RUNS_DIR}/{name}.json"


def key_years(key: str):
    """The source and the inclusive year range of an invented key."""
    source, years = key.split(":")[:2]
    if years == "undated":
        return source, None
    start, _, end = years.partition("-")
    return source, (int(start), int(end or start))


def share_unit(a: dict, b: dict) -> bool:
    """Whether two entries share a unit, worked out independently."""
    for x in a["unit_keys"]:
        for y in b["unit_keys"]:
            (sx, yx), (sy, yy) = key_years(x), key_years(y)
            if sx != sy:
                continue
            if yx is None or yy is None or (yx[0] <= yy[1] and yy[0] <= yx[1]):
                return True
    return False


def family_of(entry: dict) -> set[str]:
    return {FAMILY[key_years(key)[0]] for key in entry["unit_keys"]}


def make_entry(index: int, keys, path=("registration", "candidate")):
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
            [{"path": run_path(f"s{index}"), "field": "gate", "equals": gate}]
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


def review(entry_id: str) -> dict:
    return {
        "id": entry_id,
        "outcome": "disjoint",
        "reason": REASON,
        "evidence": ["https://example.org/catalog"],
    }


def settle(entries: list[dict]) -> None:
    """Disclose every shared unit both ways and review every unshared
    same-family relation, as a careful registrant would."""
    live = [entry for entry in entries if entry["status"] != "withdrawn"]
    for index, entry in enumerate(live):
        for other in live[index + 1 :]:
            if share_unit(entry, other):
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
                and family_of(entry) & family_of(other)
                and not share_unit(entry, other)
                and other["id"] not in entry["disclosed_overlaps"]
                and other["id"] not in reviewed
            ):
                entry["overlap_review"].append(review(other["id"]))


def make_registry(entries: list[dict], complete=False) -> dict:
    return {
        "schema": registry.SCHEMA,
        "title": "invented",
        "purpose": "invented",
        "rules": ["rule one", "the registry is incomplete"],
        "status_values": {status: status for status in registry.STATUSES},
        "sources": copy.deepcopy(VOCABULARY),
        "complete": complete,
        "completion_record": "docs/design/inventory.json",
        "entries": entries,
    }


#: The invented scored runs, in place of the module's controlled list.
#: Without a repository no pin is checked.
SCORED_RUNS = {
    run_path(f"s{index}"): (f"gate_{index}", "0" * 64) for index in range(12)
}


def authorize(current) -> dict:
    """Authorize every well-formed historical import ``current`` holds as
    it stands, for tests about other rules; the authorization rule itself
    is tested against fixed authorizations."""
    entries = current.get("entries") if isinstance(current, dict) else None
    imports = {}
    for entry in entries if isinstance(entries, list) else []:
        try:
            if entry["provenance"] != "historical_import":
                continue
            imports[entry["id"]] = {
                "gate": entry["gate"],
                "unit_keys": tuple(entry["unit_keys"]),
                "scored_runs": tuple(
                    item["path"] for item in entry["scored_evidence"]
                ),
            }
        except (KeyError, TypeError):
            continue
    return imports


#: The legal transitions, specified independently of the module.
EXPECTED_TRANSITIONS = {
    "candidate": {"frozen", "withdrawn"},
    "frozen": {"used", "withdrawn"},
    "used": set(),
    "withdrawn": set(),
}


def validate(
    current, repository=None, scored_runs=None, commit="HEAD", imports=None
):
    return registry.validate(
        current,
        repository,
        vocabulary=VOCABULARY,
        commit=commit,
        scored_runs=SCORED_RUNS if scored_runs is None else scored_runs,
        imports=authorize(current) if imports is None else imports,
    )


entry_specs = st.lists(
    st.tuples(
        st.lists(
            st.sampled_from(KEY_POOL), min_size=1, max_size=3, unique=True
        ),
        st.sampled_from(sorted(PATHS)),
    ),
    max_size=6,
)
registration_specs = st.lists(
    st.lists(st.sampled_from(KEY_POOL), min_size=1, max_size=3, unique=True),
    max_size=4,
)


def build(specs, complete=False) -> dict:
    entries = [
        make_entry(i, keys, path) for i, (keys, path) in enumerate(specs)
    ]
    settle(entries)
    return make_registry(entries, complete)


def test_the_field_lists_are_as_specified():
    assert registry.IMMUTABLE == EXPECTED_IMMUTABLE
    assert registry.EXTENDING == EXPECTED_EXTENDING
    assert set(EXPECTED_IMMUTABLE) | set(EXPECTED_EXTENDING) | {
        "status",
    } == set(registry.ENTRY_KEYS)


@settings(max_examples=200, deadline=None)
@given(entry_specs)
def test_settled_registries_are_valid(specs):
    assert validate(build(specs)) == []


@settings(max_examples=200, deadline=None)
@given(entry_specs)
def test_shared_units_match_the_independent_rule(specs):
    current = build(specs)
    entries = current["entries"]
    for i, a in enumerate(entries):
        for b in entries[i + 1 :]:
            assert registry.entries_overlap(a, b) == share_unit(a, b)


@settings(max_examples=200, deadline=None)
@given(entry_specs, st.data())
def test_a_one_way_disclosure_is_refused(specs, data):
    current = build(specs)
    disclosing = [e for e in current["entries"] if e["disclosed_overlaps"]]
    if not disclosing:
        return
    data.draw(st.sampled_from(disclosing))["disclosed_overlaps"].pop()
    problems = validate(current)
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
        entry["overlap_review"] = []
    settle_reviews_only(current["entries"])
    live = [e for e in current["entries"] if e["status"] != "withdrawn"]
    shared = any(
        share_unit(a, b) for i, a in enumerate(live) for b in live[i + 1 :]
    )
    problems = validate(current)
    assert any("without disclosing" in p for p in problems) == shared


def settle_reviews_only(entries):
    for index, entry in enumerate(entries):
        if entry["status"] == "withdrawn":
            continue
        for other in entries[:index]:
            if (
                other["status"] != "withdrawn"
                and family_of(entry) & family_of(other)
                and not share_unit(entry, other)
            ):
                entry["overlap_review"].append(review(other["id"]))


@settings(max_examples=200, deadline=None)
@given(entry_specs)
def test_an_unreviewed_family_relation_is_refused(specs):
    current = build(specs)
    needed = any(entry["overlap_review"] for entry in current["entries"])
    for entry in current["entries"]:
        entry["overlap_review"] = []
    problems = validate(current)
    assert any("neither discloses nor reviews" in p for p in problems) == (
        needed
    )


def test_fixed_family_cases_follow_the_rule():
    # s_a and s_b share family f1 but no unit; s_c is another family.
    same = [make_entry(0, ["s_a:2020"]), make_entry(1, ["s_b:2025"])]
    assert any(
        "neither discloses nor reviews" in p
        for p in validate(make_registry(copy.deepcopy(same)))
    )
    reviewed = copy.deepcopy(same)
    reviewed[1]["overlap_review"].append(review("H001"))
    assert validate(make_registry(reviewed)) == []
    disclosed = copy.deepcopy(same)
    disclosed[0]["disclosed_overlaps"].append("H002")
    disclosed[1]["disclosed_overlaps"].append("H001")
    assert validate(make_registry(disclosed)) == []
    other = [make_entry(0, ["s_a:2020"]), make_entry(1, ["s_c:2025"])]
    assert validate(make_registry(other)) == []


@pytest.mark.parametrize(
    "change, message",
    [
        ({"outcome": "unresolved"}, "is disclosed"),
        (
            {"reason": "TODO: check later, once the inventory has landed."},
            "substantive",
        ),
        ({"reason": "short"}, "substantive"),
        ({"evidence": []}, "cites nothing"),
        ({"evidence": ["somewhere"]}, "not path:line or a URL"),
        ({"evidence": ["docs/x.md:0"]}, "bad line range"),
    ],
)
def test_a_review_needs_an_outcome_a_reason_and_citations(change, message):
    entries = [make_entry(0, ["s_a:2020"]), make_entry(1, ["s_b:2025"])]
    entries[1]["overlap_review"].append(dict(review("H001"), **change))
    problems = validate(make_registry(entries))
    assert any(message in p for p in problems)


@settings(max_examples=200, deadline=None)
@given(entry_specs, registration_specs)
def test_appending_lone_candidates_keeps_every_rule(base_specs, more):
    base = build(base_specs)
    current = copy.deepcopy(base)
    start = len(current["entries"])
    for offset, keys in enumerate(more):
        current["entries"].append(make_entry(start + offset, keys))
    settle(current["entries"])
    assert validate(current) == []
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
    assert validate(current) == []
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


def test_the_registry_must_carry_the_controlled_vocabulary():
    current = make_registry([])
    current["sources"]["s_d"] = dict(VOCABULARY["s_c"], catalog="cat d")
    assert any("controlled vocabulary" in p for p in validate(current))
    aliased = dict(VOCABULARY, s_d=dict(VOCABULARY["s_a"], catalog=" CAT  A"))
    problems = registry.validate(
        dict(current, sources=aliased), vocabulary=aliased
    )
    assert any("alias" in p for p in problems)


@given(
    st.sampled_from(sorted(VOCABULARY)),
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
    assert validate(make_registry([entry]))


def test_a_key_naming_no_source_is_refused():
    entry = make_entry(0, ["s_z:2020"])
    problems = validate(make_registry([entry]))
    assert any("names no source" in p for p in problems)


@pytest.mark.parametrize(
    "provenance, statuses, last, message",
    [
        ("registration", ["frozen"], "frozen", "starts as one of"),
        ("historical_import", ["candidate"], "candidate", "starts as one of"),
        ("historical_import", ["frozen"], "frozen", "starts as one of"),
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
            {"path": run_path("s"), "field": "gate", "equals": "gate_0"}
        ]
    assert any(message in p for p in validate(make_registry([entry])))


@pytest.mark.parametrize("date", ["2026-10-01", "2026-99-99", "yesterday"])
def test_history_dates_are_real_and_never_go_back(date):
    entry = make_entry(0, ["s_a:2020"], ("registration", "frozen"))
    entry["history"][1]["date"] = date
    assert validate(make_registry([entry]))


def test_repeated_ids_and_shared_gate_identifiers_are_refused():
    current = build([(["s_a:2020"], ("registration", "candidate"))] * 2)
    current["entries"][1]["id"] = "H001"
    assert any("ids repeat" in p for p in validate(current))
    current = build([(["s_a:2020"], ("registration", "candidate"))] * 2)
    current["entries"][1]["gate_identifiers"].append("gate_0")
    assert any("already identifies" in p for p in validate(current))


@pytest.mark.parametrize(
    "change, message",
    [
        ({"equals": "gate_other"}, "does not identify this gate"),
        ({"field": "title"}, "not an identity field"),
        ({"path": "docs/design/registry.json"}, "not a listed scored run"),
        ({"path": "../outside.json"}, "not a listed scored run"),
        ({"path": run_path("s1")}, "'gate_1''s scored run"),
    ],
)
def test_scored_evidence_must_be_a_run_artifact_naming_this_gate(
    change, message
):
    entry = make_entry(0, ["s_a:2020"], ("historical_import", "used"))
    entry["scored_evidence"][0].update(change)
    assert any(message in p for p in validate(make_registry([entry])))
    entry["scored_evidence"] = []
    problems = validate(make_registry([entry]))
    assert any("needs scored_evidence" in p for p in problems)


def test_the_transitions_are_as_specified():
    assert {
        status: set(following)
        for status, following in registry.TRANSITIONS.items()
    } == EXPECTED_TRANSITIONS


@pytest.mark.parametrize(
    "statuses",
    [
        ["candidate", "frozen", "used", "withdrawn"],
        ["candidate", "withdrawn", "frozen"],
        ["candidate", "frozen", "used", "frozen"],
        ["candidate", "frozen", "frozen"],
    ],
)
def test_terminal_and_repeated_statuses_are_refused(statuses):
    entry = make_entry(0, ["s_a:2020"])
    entry["history"] = [
        {"date": "2026-10-21", "status": s, "note": "n"} for s in statuses
    ]
    entry["status"] = statuses[-1]
    entry["scored_evidence"] = [
        {"path": run_path("s0"), "field": "gate", "equals": "gate_0"}
    ]
    assert any(
        "not a legal transition" in p for p in validate(make_registry([entry]))
    )


#: One fixed authorization: H001 imports gate_0's s_a:2020 with run s0.
AUTHORIZED = {
    "H001": {
        "gate": "gate_0",
        "unit_keys": ("s_a:2020",),
        "scored_runs": (run_path("s0"),),
    }
}


def import_with(change) -> dict:
    """gate_0's authorized import, then ``change`` applied to its entry."""
    entry = make_entry(0, ["s_a:2020"], ("historical_import", "used"))
    change(entry)
    return make_registry([entry])


def _rename(entry):
    entry["id"] = "H002"


def _regate(entry):
    entry.update(gate="gate_1", gate_identifiers=["gate_1"])
    entry["scored_evidence"][0].update(path=run_path("s1"), equals="gate_1")


def _more_units(entry):
    entry["unit_keys"].append("s_c:2099")


def _other_units(entry):
    entry["unit_keys"] = ["s_c:2099"]


def _more_runs(entry):
    entry["scored_evidence"].append(dict(entry["scored_evidence"][0]))


@pytest.mark.parametrize(
    "change, message",
    [
        (_rename, "not an authorized historical import"),
        (_regate, "is authorized for 'gate_0'"),
        (_more_units, "unit keys differ"),
        (_other_units, "unit keys differ"),
        (_more_runs, "differs from its authorized runs"),
    ],
)
def test_imports_must_match_their_authorization(change, message):
    assert validate(import_with(lambda entry: None), imports=AUTHORIZED) == []
    problems = validate(import_with(change), imports=AUTHORIZED)
    assert any(message in p for p in problems), problems


def test_an_authorization_admits_one_import_only():
    first = make_entry(0, ["s_a:2020"], ("historical_import", "used"))
    again = make_entry(0, ["s_a:2020"], ("historical_import", "used"))
    again["id"] = "H002"
    entries = [first, again]
    settle(entries)
    problems = validate(make_registry(entries), imports=AUTHORIZED)
    assert any(
        "H002: is not an authorized historical import" in p for p in problems
    )


def test_a_review_must_name_an_earlier_entry():
    entries = [make_entry(0, ["s_a:2020"]), make_entry(1, ["s_c:2025"])]
    entries[0]["overlap_review"].append(review("H002"))
    problems = validate(make_registry(entries))
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
    problems = validate(current)
    assert isinstance(problems, list) and problems


json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=8),
    lambda children: st.lists(children, max_size=4)
    | st.dictionaries(st.text(max_size=8), children, max_size=4),
    max_leaves=20,
)


@settings(max_examples=200, deadline=None)
@given(
    st.sampled_from(sorted(registry.ENTRY_KEYS) + ["entries"]),
    json_values,
    st.booleans(),
)
def test_any_json_in_any_field_is_reported_not_raised(key, value, append):
    base = build([(["s_a:2020"], ("historical_import", "used"))])
    current = copy.deepcopy(base)
    if key == "entries":
        current["entries"] = value
    elif append:
        added = make_entry(1, ["s_c:2099"])
        added[key] = value
        current["entries"].append(added)
    else:
        current["entries"][0][key] = value
    assert isinstance(validate(current), list)
    assert isinstance(registry.append_only_problems(base, current), list)


# Committed trees, scored runs and base commits, through git ----------------


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
    write(
        repository,
        registry.GATES,
        "gates:\n  gate_0:\n    id: zero_gate\n"
        "    registration_id: reg-zero\n",
    )
    commit_all(repository, "start")
    return repository


def write(repository: Path, relative: str, document) -> None:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(document, bytes):
        path.write_bytes(document)
        return
    text = document if isinstance(document, str) else json.dumps(document)
    path.write_text(text, encoding="utf-8")


def commit_all(repository: Path, message: str) -> str:
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "--allow-empty", "-m", message)
    return git(repository, "rev-parse", "HEAD").strip()


def pin(document, gate: str = "gate_0") -> dict:
    """The scored-run list for one artifact holding ``document``."""
    text = json.dumps(document).encode("utf-8")
    return {run_path("s0"): (gate, hashlib.sha256(text).hexdigest())}


@pytest.fixture
def no_ci_env(monkeypatch):
    for name in ("GITHUB_BASE_REF", "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH"):
        monkeypatch.delenv(name, raising=False)


SCORE = {"gate": "gate_0"}


def imported(document=SCORE) -> dict:
    entry = make_entry(0, ["s_a:2020"], ("historical_import", "used"))
    entry["gate_identifiers"] = ["gate_0", "zero_gate", "reg-zero"]
    return make_registry([entry])


def test_scored_evidence_is_read_from_the_committed_tree(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    current = imported()
    evidence = current["entries"][0]["scored_evidence"][0]
    runs = pin(SCORE)
    write(repository, evidence["path"], SCORE)
    assert any(
        "not a committed file" in p
        for p in validate(current, repository, runs)
    )
    git(repository, "add", "-A")
    assert any(
        "not a committed file" in p
        for p in validate(current, repository, runs)
    )
    git(repository, "commit", "-q", "-m", "score")
    assert validate(current, repository, runs) == []
    write(repository, evidence["path"], {"gate": "gate_9"})
    assert validate(current, repository, runs) == []
    for field, equals in (
        ("registration_id", "reg-zero"),
        ("gate", "zero_gate"),
    ):
        evidence.update(field=field, equals=equals)
        assert any(
            "does not have" in p for p in validate(current, repository, runs)
        )


def test_a_scored_run_must_keep_its_pinned_bytes(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    current = imported()
    path = current["entries"][0]["scored_evidence"][0]["path"]
    write(repository, path, {"gate": "gate_0", "floor": True})
    commit_all(repository, "a floor, not the scored run")
    problems = validate(current, repository, pin(SCORE))
    assert any("differs from the listed scored run" in p for p in problems)


def test_identifiers_must_be_authoritative(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    current = imported()
    entry = current["entries"][0]
    document = {"gate": "x"}
    write(repository, entry["scored_evidence"][0]["path"], document)
    commit_all(repository, "score")
    entry["gate_identifiers"].append("x")
    entry["scored_evidence"][0].update(field="gate", equals="x")
    assert any(
        "does not identify this gate" in p
        for p in validate(current, repository, pin(document))
    )
    entry["gate"] = "gate_unknown"
    entry["gate_identifiers"] = ["gate_unknown"]
    entry["scored_evidence"][0]["equals"] = "gate_unknown"
    runs = pin(document, "gate_unknown")
    assert any(
        "neither a gates.yaml gate" in p
        for p in validate(current, repository, runs)
    )


def test_a_symlinked_or_non_json_artifact_is_refused(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    current = imported()
    path = current["entries"][0]["scored_evidence"][0]["path"]
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(SCORE), encoding="utf-8")
    link = repository / path
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    commit_all(repository, "link")
    assert any(
        "not a committed file" in p
        for p in validate(current, repository, pin(SCORE))
    )
    link.unlink()
    write(repository, path, b"\xff\xfe not json")
    commit_all(repository, "bytes")
    runs = {path: ("gate_0", hashlib.sha256(b"\xff\xfe not json").hexdigest())}
    assert any(
        "does not have" in p for p in validate(current, repository, runs)
    )


def registered(statuses) -> dict:
    """A registration of gate_0 at ``statuses``, citing s0 once used."""
    entry = make_entry(0, ["s_a:2020"])
    entry["gate_identifiers"] = ["gate_0", "zero_gate", "reg-zero"]
    entry["history"] = [
        {"date": f"2026-10-{21 + step:02d}", "status": s, "note": "n"}
        for step, s in enumerate(statuses)
    ]
    entry["status"] = statuses[-1]
    if statuses[-1] == "used":
        entry["scored_evidence"] = [
            {"path": run_path("s0"), "field": "gate", "equals": "gate_0"}
        ]
    return make_registry([entry])


def commit_registry(repository: Path, current: dict, message: str) -> str:
    write(repository, registry.REGISTRY, current)
    return commit_all(repository, message)


@pytest.mark.parametrize("registered_first", [True, False])
def test_a_registration_must_precede_its_scored_run(
    tmp_path, no_ci_env, registered_first
):
    repository = init_repository(tmp_path)
    if not registered_first:
        write(repository, run_path("s0"), SCORE)
        commit_all(repository, "score first")
    commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    if registered_first:
        write(repository, run_path("s0"), SCORE)
        commit_all(repository, "score")
    used = registered(["candidate", "frozen", "used"])
    commit_registry(repository, used, "used")
    problems = validate(used, repository, pin(SCORE))
    if registered_first:
        assert problems == []
    else:
        assert any("already committed" in p for p in problems)


def git_rename(repository: Path, old: str, new: str) -> None:
    (repository / new).parent.mkdir(parents=True, exist_ok=True)
    git(repository, "mv", old, new)


@pytest.mark.parametrize(
    "scenario", ["moved", "deleted_and_restored", "same_commit", "side_branch"]
)
def test_a_score_committed_anywhere_before_registration_is_refused(
    tmp_path, no_ci_env, scenario
):
    """The score's bytes were committed before the registration in every
    scenario: at another path then moved, at its path then deleted and
    restored, in the registering commit itself, or on the base branch
    while the registration waited on a side branch merged afterwards."""
    repository = init_repository(tmp_path)
    listed, elsewhere = run_path("s0"), run_path("original")
    if scenario == "moved":
        write(repository, elsewhere, SCORE)
        commit_all(repository, "score at another path")
    elif scenario == "deleted_and_restored":
        write(repository, listed, SCORE)
        commit_all(repository, "score")
        (repository / listed).unlink()
        commit_all(repository, "score deleted")
    if scenario == "same_commit":
        write(repository, listed, SCORE)
        commit_registry(repository, registered(["candidate"]), "both")
    elif scenario == "side_branch":
        git(repository, "checkout", "-q", "-b", "side")
        commit_registry(repository, registered(["candidate"]), "register")
        git(repository, "checkout", "-q", "master")
        write(repository, listed, SCORE)
        commit_all(repository, "score")
        git(repository, "merge", "-q", "--no-ff", "-m", "merge side", "side")
    else:
        commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    if scenario == "moved":
        git_rename(repository, elsewhere, listed)
        commit_all(repository, "moved to its listed path")
    elif scenario == "deleted_and_restored":
        write(repository, listed, SCORE)
        commit_all(repository, "score restored")
    used = registered(["candidate", "frozen", "used"])
    commit_registry(repository, used, "used")
    problems = validate(used, repository, pin(SCORE))
    assert any("already committed" in p for p in problems), problems


def test_a_shallow_clone_cannot_prove_a_score_was_not_committed(
    tmp_path, no_ci_env
):
    """A shallow clone that keeps the registry's history but not the
    score's first commit must not read an empty search as absence."""
    repository = init_repository(tmp_path)
    listed = run_path("s0")
    write(repository, listed, SCORE)
    commit_all(repository, "score")
    (repository / listed).unlink()
    commit_all(repository, "score deleted")
    commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    write(repository, listed, SCORE)
    commit_all(repository, "score restored")
    used = registered(["candidate", "frozen", "used"])
    commit_registry(repository, used, "used")
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "5", repository.as_uri(), shallow],
        check=True,
        capture_output=True,
    )
    assert git(shallow, "rev-parse", "--is-shallow-repository").strip() == (
        "true"
    )
    assert any(
        "already committed" in p
        for p in validate(used, repository, pin(SCORE))
    )
    problems = validate(used, shallow, pin(SCORE))
    assert any("cannot tell whether" in p for p in problems), problems


def test_a_replacement_ref_cannot_hide_a_committed_score(tmp_path, no_ci_env):
    """`git replace` can graft a parentless copy over a commit and hide
    its ancestors from ordinary log walks; the search ignores it."""
    repository = init_repository(tmp_path)
    listed = run_path("s0")
    write(repository, listed, SCORE)
    commit_all(repository, "score")
    (repository / listed).unlink()
    deleted = commit_all(repository, "score deleted")
    orphan = git(
        repository, "commit-tree", f"{deleted}^{{tree}}", "-m", "orphan"
    ).strip()
    git(repository, "replace", deleted, orphan)
    commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    write(repository, listed, SCORE)
    commit_all(repository, "score restored")
    used = registered(["candidate", "frozen", "used"])
    commit_registry(repository, used, "used")
    problems = validate(used, repository, pin(SCORE))
    assert any("already committed" in p for p in problems), problems


def test_a_score_added_only_in_a_merge_resolution_is_refused(
    tmp_path, no_ci_env
):
    """A score that enters only through a merge commit's own resolution,
    before the registration, was committed before it."""
    repository = init_repository(tmp_path)
    git(repository, "checkout", "-q", "-b", "side")
    write(repository, "docs/side.md", "side\n")
    commit_all(repository, "side work")
    git(repository, "checkout", "-q", "master")
    write(repository, "docs/main.md", "main\n")
    commit_all(repository, "main work")
    git(repository, "merge", "-q", "--no-ff", "--no-commit", "side")
    write(repository, run_path("s0"), SCORE)
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "merge, adding the score")
    commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    used = registered(["candidate", "frozen", "used"])
    commit_registry(repository, used, "used")
    problems = validate(used, repository, pin(SCORE))
    assert any("already committed" in p for p in problems), problems


def test_subprocess_failures_are_reported_not_raised(
    tmp_path, no_ci_env, monkeypatch
):
    repository = init_repository(tmp_path)
    huge = "a" * 3_000_000
    current = registered(["candidate"])
    current.update(completion_record=huge, complete=True)
    assert isinstance(validate(current, repository), list)
    for commit in (None, huge):
        with pytest.raises(LookupError):
            registry.registry_at(repository, commit)
    with pytest.raises(LookupError):
        registry.history_problems(repository, huge, imports={})
    monkeypatch.setenv("PATH", str(tmp_path / "no-git-here"))
    with pytest.raises(LookupError):
        registry.registry_at(repository, "HEAD")
    assert validate(imported(), repository, pin(SCORE))


@pytest.mark.parametrize(
    "imports, message",
    [
        (None, "must be a mapping"),
        ({"H001": {}}, "needs a gate"),
        (
            {"H001": {"gate": "g", "unit_keys": [1], "scored_runs": []}},
            "needs",
        ),
    ],
)
def test_malformed_authorizations_are_reported_not_raised(imports, message):
    problems = registry.validate(
        imported(), vocabulary=VOCABULARY, imports=imports
    )
    assert any(message in p for p in problems), problems


def test_sha256_object_ids_bound_histories(tmp_path, no_ci_env, monkeypatch):
    repository = tmp_path / "repo256"
    repository.mkdir()
    git(repository, "init", "-q", "-b", "master", "--object-format=sha256")
    git(repository, "config", "user.email", "t@example.com")
    git(repository, "config", "user.name", "t")
    first = registered(["candidate"])
    before = commit_registry(repository, first, "registry")
    assert len(before) == 64
    changed = copy.deepcopy(first)
    changed["entries"][0]["unit_keys"] = ["s_c:2199"]
    commit_registry(repository, changed, "an immutable key changes")
    commit_registry(repository, first, "and is restored")
    commit_all(repository, "an unchanged tip")
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {"before": before, "pull_request": {"head": {"sha": before}}}
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    assert registry.base_commit(repository) == before
    assert registry.history_problems(
        repository, registry.base_commit(repository), imports={}
    )
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    assert registry.pull_request_head() == before


def test_an_unanswerable_timing_check_fails_closed(
    tmp_path, no_ci_env, monkeypatch
):
    repository = init_repository(tmp_path)
    commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    write(repository, run_path("s0"), SCORE)
    commit_all(repository, "score")
    used = registered(["candidate", "frozen", "used"])
    commit_registry(repository, used, "used")
    assert validate(used, repository, pin(SCORE)) == []
    monkeypatch.setattr(
        registry.Committed, "committed_by", lambda self, content, at: None
    )
    problems = validate(used, repository, pin(SCORE))
    assert any("cannot tell whether" in p for p in problems)


@pytest.mark.parametrize(
    "failure",
    [
        OSError(errno.EMFILE, "Too many open files"),
        FileNotFoundError(errno.ENOENT, "git"),
        TypeError("expected str, bytes or os.PathLike object"),
        ValueError("embedded null byte"),
    ],
)
def test_a_failed_object_hash_fails_closed(
    tmp_path, no_ci_env, monkeypatch, failure
):
    repository = init_repository(tmp_path)
    commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    write(repository, run_path("s0"), SCORE)
    commit_all(repository, "score")
    used = registered(["candidate", "frozen", "used"])
    commit_registry(repository, used, "used")
    assert validate(used, repository, pin(SCORE)) == []
    run = subprocess.run

    def failing(command, *args, **kwargs):
        if "hash-object" in command:
            raise failure
        return run(command, *args, **kwargs)

    monkeypatch.setattr(registry.subprocess, "run", failing)
    committed = registry.Committed(repository)
    assert committed.committed_by(json.dumps(SCORE).encode(), "HEAD") is None
    problems = validate(used, repository, pin(SCORE))
    assert any("cannot tell whether" in p for p in problems), problems


def test_a_used_registration_must_already_be_registered(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    write(repository, run_path("s0"), SCORE)
    commit_all(repository, "score")
    used = registered(["candidate", "frozen", "used"])
    problems = validate(used, repository, pin(SCORE))
    assert any("before it is registered" in p for p in problems)


def test_each_snapshot_is_validated_against_its_own_tree(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    base = git(repository, "rev-parse", "HEAD").strip()
    commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    used = registered(["candidate", "frozen", "used"])
    commit_registry(repository, used, "used before its score is committed")
    write(repository, run_path("s0"), SCORE)
    commit_all(repository, "the score, one commit late")
    runs = pin(SCORE)
    assert validate(used, repository, runs) == []
    problems = registry.history_problems(
        repository, base, scored_runs=runs, imports={}
    )
    assert any("not a committed file" in p for p in problems)


def test_a_new_registry_is_admitted_against_an_empty_one(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    base = git(repository, "rev-parse", "HEAD").strip()
    commit_registry(
        repository, registered(["candidate", "frozen"]), "arrives frozen"
    )
    problems = registry.history_problems(repository, base, imports={})
    assert any("lone candidate" in p for p in problems)


def test_a_clean_history_has_no_problems(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    base = git(repository, "rev-parse", "HEAD").strip()
    commit_registry(repository, registered(["candidate"]), "register")
    commit_registry(repository, registered(["candidate", "frozen"]), "freeze")
    write(repository, run_path("s0"), SCORE)
    commit_all(repository, "score")
    commit_registry(
        repository, registered(["candidate", "frozen", "used"]), "used"
    )
    assert (
        registry.history_problems(
            repository,
            base,
            scored_runs=pin(SCORE),
            imports={},
        )
        == []
    )


@pytest.mark.parametrize("undo", ["append_then_remove", "edit_then_restore"])
@pytest.mark.parametrize("full", [True, False])
def test_a_run_of_commits_cannot_hide_a_change_it_undoes(
    tmp_path, no_ci_env, undo, full
):
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    base = commit_registry(repository, first, "registry")
    changed = copy.deepcopy(first)
    if undo == "append_then_remove":
        changed["entries"].append(make_entry(1, ["s_c:2099"]))
    else:
        changed["entries"][0]["unit_keys"] = ["s_c:2199"]
    commit_registry(repository, changed, "change")
    commit_registry(repository, first, "undo")
    assert registry.append_only_problems(first, first) == []
    assert registry.history_problems(repository, base, full=full, imports={})


# A pull request's own commits, from its fork point -----------------------


def branch(repository: Path, name: str) -> None:
    git(repository, "checkout", "-q", "-b", name)


def switch(repository: Path, name: str) -> None:
    git(repository, "checkout", "-q", name)


def merge_with(repository: Path, other: str, resolution) -> str:
    """Merge ``other`` into the current branch, resolving the registry to
    ``resolution`` (``None`` leaves no registry)."""
    git(
        repository,
        "merge",
        "-q",
        "--no-ff",
        "--no-commit",
        "-s",
        "ours",
        other,
    )
    path = repository / registry.REGISTRY
    if resolution is not None:
        write(repository, registry.REGISTRY, resolution)
    elif path.exists():
        path.unlink()
    return commit_all(repository, f"merge {other}")


def grown(document, *indices: int) -> dict:
    """``document`` (or a new registry) with a lone candidate appended
    for each index."""
    entries = [make_entry(index, [f"s_c:{2000 + index}"]) for index in indices]
    if document is None:
        return make_registry(entries)
    document = copy.deepcopy(document)
    document["entries"].extend(entries)
    return document


def own_work(repository: Path, text: str) -> str:
    write(repository, "notes.md", text)
    return commit_all(repository, text)


def reported(problems: list[str]) -> set[str]:
    """The commits, as 12-character labels, that ``problems`` name."""
    return {problem.split(": ", 1)[0].split("..")[-1] for problem in problems}


def head_of(repository: Path) -> str:
    return git(repository, "rev-parse", "HEAD").strip()


@pytest.mark.parametrize("merged", [False, True])
def test_a_pull_request_from_before_the_registry_passes(
    tmp_path, no_ci_env, merged
):
    """A pull request branched before the registry existed has own
    commits without one. They are compared from the fork point, which
    had none, not with the base, which has one; a master merge brings
    the landed registry in unchanged."""
    repository = init_repository(tmp_path)
    branch(repository, "pr")
    own_work(repository, "one")
    own_work(repository, "two")
    switch(repository, "master")
    commit_registry(repository, registered(["candidate"]), "registry lands")
    landed = grown(registered(["candidate"]), 1)
    base = commit_registry(repository, landed, "master grows")
    switch(repository, "pr")
    if merged:
        merge_with(repository, "master", landed)
        own_work(repository, "three")
    problems = registry.history_problems(
        repository, base, head_of(repository), full=False
    )
    assert problems == []


@pytest.mark.parametrize("merged", [False, True])
def test_a_pull_request_passes_while_master_grows(tmp_path, no_ci_env, merged):
    """A pull request that adds its own registration is compared with
    the registry it was built on, not with a base that has since added
    others; a master merge must keep the landed entries first."""
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    commit_registry(repository, first, "registry")
    branch(repository, "pr")
    commit_registry(repository, grown(first, 5), "own registration")
    switch(repository, "master")
    landed = grown(first, 1)
    base = commit_registry(repository, landed, "master grows")
    switch(repository, "pr")
    if merged:
        merge_with(repository, "master", grown(landed, 5))
        own_work(repository, "after the merge")
    problems = registry.history_problems(
        repository, base, head_of(repository), full=False
    )
    assert problems == []


@pytest.mark.parametrize(
    "change", ["rewrite", "delete", "drop_landed", "merge_drops_landed"]
)
def test_own_commits_after_a_master_merge_are_checked(
    tmp_path, no_ci_env, change
):
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    commit_registry(repository, first, "registry")
    branch(repository, "pr")
    own_work(repository, "own")
    switch(repository, "master")
    landed = grown(first, 1)
    base = commit_registry(repository, landed, "master grows")
    switch(repository, "pr")
    if change == "merge_drops_landed":
        bad = merge_with(repository, "master", first)
    else:
        merge_with(repository, "master", landed)
        if change == "rewrite":
            rewritten = copy.deepcopy(landed)
            rewritten["entries"][0]["unit_keys"] = ["s_c:2199"]
            bad = commit_registry(repository, rewritten, "rewrite")
        elif change == "delete":
            git(repository, "rm", "-q", registry.REGISTRY)
            bad = commit_all(repository, "delete")
        else:
            bad = commit_registry(repository, first, "drop a landed entry")
    commit_registry(repository, landed, "restore")
    problems = registry.history_problems(
        repository, base, head_of(repository), full=False
    )
    assert reported(problems) == {bad[:12]}


@pytest.mark.parametrize("merged", [False, True])
def test_a_pull_request_cannot_hide_a_change_it_undoes(
    tmp_path, no_ci_env, merged
):
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    commit_registry(repository, first, "registry")
    branch(repository, "pr")
    switch(repository, "master")
    landed = grown(first, 1)
    base = commit_registry(repository, landed, "master grows")
    switch(repository, "pr")
    built_on = first
    if merged:
        merge_with(repository, "master", landed)
        built_on = landed
    changed = copy.deepcopy(built_on)
    changed["entries"][0]["unit_keys"] = ["s_c:2199"]
    bad = commit_registry(repository, changed, "change")
    commit_registry(repository, built_on, "undo")
    problems = registry.history_problems(
        repository, base, head_of(repository), full=False
    )
    assert reported(problems) == {bad[:12]}


@pytest.mark.parametrize("keeps_own_order", [True, False])
def test_a_merge_of_unlanded_history_extends_its_own_predecessor(
    tmp_path, no_ci_env, keeps_own_order
):
    """Only landed history (an ancestor of the base) replaces a merge's
    predecessor. Another unlanded branch is not trusted: the merge must
    extend the pull request's own last registry."""
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    base = commit_registry(repository, first, "registry")
    branch(repository, "side")
    commit_registry(repository, grown(first, 7), "side registration")
    switch(repository, "master")
    branch(repository, "pr")
    commit_registry(repository, grown(first, 5), "own registration")
    resolution = grown(first, 5, 7) if keeps_own_order else grown(first, 7, 5)
    merge = merge_with(repository, "side", resolution)
    problems = registry.history_problems(
        repository, base, head_of(repository), full=False
    )
    assert reported(problems) == (set() if keeps_own_order else {merge[:12]})


def test_a_merge_of_contained_history_keeps_its_own_predecessor(
    tmp_path, no_ci_env
):
    """A merge whose other parent is landed but already in its first
    parent brings nothing in, so it does not reset the predecessor to that
    older registry. Otherwise a crafted merge of the fork point could drop
    an entry a master merge brought in, and a later commit restore it,
    unseen."""
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    fork = commit_registry(repository, first, "registry")
    branch(repository, "pr")
    own_work(repository, "own")
    switch(repository, "master")
    landed = grown(first, 1)
    base = commit_registry(repository, landed, "master grows")
    switch(repository, "pr")
    merge_with(repository, "master", landed)
    write(repository, registry.REGISTRY, first)
    git(repository, "add", "-A")
    tree = git(repository, "write-tree").strip()
    crafted = git(
        repository,
        "commit-tree",
        tree,
        "-p",
        "HEAD",
        "-p",
        fork,
        "-m",
        "merge the fork point again, dropping a landed entry",
    ).strip()
    git(repository, "reset", "-q", "--hard", crafted)
    commit_registry(repository, landed, "restore")
    problems = registry.history_problems(
        repository, base, head_of(repository), full=False
    )
    assert reported(problems) == {crafted[:12]}


def test_a_first_commit_that_merges_unlanded_history_starts_at_the_fork(
    tmp_path, no_ci_env
):
    """The walk starts from the first listed commit's first parent. When
    that commit merges an unlanded branch, the branch's registry is not
    the predecessor, so a rewrite the branch carries is reported at the
    merge."""
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    base = commit_registry(repository, first, "registry")
    branch(repository, "side")
    rewritten = copy.deepcopy(first)
    rewritten["entries"][0]["unit_keys"] = ["s_c:2199"]
    commit_registry(repository, rewritten, "side rewrites an entry")
    switch(repository, "master")
    branch(repository, "pr")
    merge = merge_with(repository, "side", rewritten)
    problems = registry.history_problems(
        repository, base, head_of(repository), full=False
    )
    assert reported(problems) == {merge[:12]}


@pytest.mark.parametrize("where", ["fork", "landed_merge"])
def test_an_unreadable_predecessor_is_reported(tmp_path, no_ci_env, where):
    """A predecessor registry that is not JSON, at the fork point or at a
    landed parent a merge brings in, is reported under its commit."""
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    if where == "fork":
        write(repository, registry.REGISTRY, "not json")
        unreadable = commit_all(repository, "an unreadable registry")
    else:
        commit_registry(repository, first, "registry")
    branch(repository, "pr")
    commit_registry(repository, first, "own registry")
    switch(repository, "master")
    if where == "landed_merge":
        write(repository, registry.REGISTRY, "not json")
    base = own_work(repository, "master moves on")
    switch(repository, "pr")
    if where == "landed_merge":
        unreadable = base
        merge_with(repository, "master", first)
    problems = registry.history_problems(
        repository, base, head_of(repository), full=False
    )
    assert any(
        p.startswith(f"{unreadable[:12]}: ") and "is not JSON" in p
        for p in problems
    )


def test_a_merge_of_two_landed_lines_is_reported(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    commit_registry(repository, first, "registry")
    branch(repository, "pr")
    own_work(repository, "own")
    switch(repository, "master")
    older = commit_registry(repository, grown(first, 1), "master grows")
    base = commit_registry(repository, grown(first, 1, 2), "and again")
    switch(repository, "pr")
    tree = git(repository, "rev-parse", "HEAD^{tree}").strip()
    octopus = git(
        repository,
        "commit-tree",
        tree,
        "-p",
        "HEAD",
        "-p",
        older,
        "-p",
        base,
        "-m",
        "octopus",
    ).strip()
    git(repository, "update-ref", "refs/heads/pr", octopus)
    problems = registry.history_problems(repository, base, octopus, full=False)
    assert any("more than one line of landed history" in p for p in problems)
    assert reported(problems) == {octopus[:12]}


@pytest.mark.parametrize(
    "flag, code",
    [("--parents", 128), ("--parents", 0), ("--is-ancestor", 128)],
)
def test_unreadable_parents_or_ancestry_raise(
    tmp_path, no_ci_env, monkeypatch, flag, code
):
    """A git failure while reading a commit's parents or ancestry raises
    ``LookupError`` rather than choose a predecessor by default."""
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    commit_registry(repository, first, "registry")
    branch(repository, "pr")
    own_work(repository, "own")
    switch(repository, "master")
    landed = grown(first, 1)
    base = commit_registry(repository, landed, "master grows")
    switch(repository, "pr")
    merge_with(repository, "master", landed)
    head = head_of(repository)
    assert registry.history_problems(repository, base, head, full=False) == []
    real = registry._git

    def failing(repo, *args):
        if flag in args:
            return subprocess.CompletedProcess(args, code, "", "injected")
        return real(repo, *args)

    monkeypatch.setattr(registry, "_git", failing)
    with pytest.raises(LookupError):
        registry.history_problems(repository, base, head, full=False)


PR_STEPS = st.lists(
    st.sampled_from(
        ["master", "own", "noop", "rewrite", "delete", "restore", "merge"]
    ),
    max_size=7,
)


@settings(max_examples=25, deadline=None)
@given(registered_first=st.booleans(), steps=PR_STEPS)
def test_only_commits_that_remove_or_rewrite_entries_are_reported(
    tmp_path_factory, registered_first, steps
):
    """Over generated graphs of master commits, own commits and master
    merges, the pull request's own commits that are reported are exactly
    those whose registry removes or rewrites an entry of its predecessor
    (the last valid own registry, or the landed one a merge brings in)."""
    repository = init_repository(tmp_path_factory.mktemp("graph"))
    landed = registered(["candidate"]) if registered_first else None
    if landed is not None:
        commit_registry(repository, landed, "registry")
    branch(repository, "pr")
    valid, own, broken, behind, index = landed, [], False, False, 0
    expected = set()
    for step in steps:
        index += 1
        if step == "master":
            switch(repository, "master")
            landed = grown(landed, 100 + index)
            commit_registry(repository, landed, "master grows")
            switch(repository, "pr")
            behind = True
            continue
        if step == "rewrite" and valid is not None and valid["entries"]:
            rewritten = copy.deepcopy(valid)
            rewritten["entries"][0]["unit_keys"] = ["s_c:2199"]
            commit = commit_registry(repository, rewritten, "rewrite")
            broken = True
        elif step == "delete" and valid is not None:
            git(repository, "rm", "-q", "--ignore-unmatch", registry.REGISTRY)
            commit = commit_all(repository, "delete")
            broken = True
        elif step == "own":
            valid = grown(valid, index)
            own.append(index)
            commit = commit_registry(repository, valid, "own registration")
            broken = False
        elif step == "restore" and valid is not None:
            commit = commit_registry(repository, valid, "restore")
            broken = False
        elif step == "merge" and behind:
            valid = grown(landed, *own) if landed is not None else valid
            commit = merge_with(repository, "master", valid)
            broken, behind = False, False
        else:
            commit = own_work(repository, f"note {index}")
        if broken:
            expected.add(commit[:12])
    switch(repository, "master")
    base = head_of(repository)
    head = git(repository, "rev-parse", "pr").strip()
    problems = registry.history_problems(repository, base, head, full=False)
    assert reported(problems) == expected


def test_a_pull_request_head_is_read_from_its_event(tmp_path, monkeypatch):
    event = tmp_path / "event.json"
    sha = "a" * 40
    event.write_text(
        json.dumps({"pull_request": {"head": {"sha": sha}}}), encoding="utf-8"
    )
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    assert registry.pull_request_head() == sha
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    assert registry.pull_request_head() is None


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "not json",
        "[]",
        json.dumps({}),
        json.dumps({"pull_request": None}),
        json.dumps({"pull_request": {"head": "abc"}}),
        json.dumps({"pull_request": {"head": {"sha": "HEAD"}}}),
    ],
)
def test_an_unreadable_pull_request_event_raises(
    tmp_path, monkeypatch, payload
):
    event = tmp_path / "event.json"
    if payload is not None:
        event.write_text(payload, encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    with pytest.raises(LookupError):
        registry.pull_request_head()
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    assert registry.pull_request_head() is None


def test_malformed_snapshots_are_reported_not_raised(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    base = commit_registry(repository, registered(["candidate"]), "registry")
    for bad in ("not json", [], {"entries": None}):
        write(
            repository,
            registry.REGISTRY,
            bad if isinstance(bad, str) else json.dumps(bad),
        )
        commit_all(repository, "a malformed snapshot")
    commit_registry(repository, registered(["candidate"]), "repaired")
    problems = registry.history_problems(repository, base, imports={})
    assert len(problems) >= 3
    assert registry.append_only_problems(registered(["candidate"]), None)


def test_malformed_predecessors_and_parser_limits_are_reported(
    tmp_path, no_ci_env
):
    no_id = {"entries": [{}]}
    assert registry.append_only_problems(
        no_id, {"entries": [{"units": {"years": [2020]}}]}
    )
    repository = init_repository(tmp_path)
    base = commit_registry(repository, no_id, "a malformed predecessor")
    commit_registry(repository, registered(["candidate"]), "repaired")
    for full in (True, False):
        problems = registry.history_problems(
            repository, base, full=full, imports={}
        )
        assert isinstance(problems, list)
    huge = "9" * 5000
    write(repository, registry.GATES, f"gates:\n  gate_0:\n    id: {huge}\n")
    write(repository, run_path("s0"), SCORE)
    commit_all(repository, "an identifier past Python's integer limit")
    assert isinstance(validate(imported(), repository, pin(SCORE)), list)
    write(repository, registry.REGISTRY, '{"entries": [' + huge + "]}")
    huge_json = commit_all(repository, "a registry past the integer limit")
    with pytest.raises(ValueError, match="is not JSON"):
        registry.registry_at(repository, huge_json)
    nul = "HEAD\x00"
    assert validate(imported(), repository, pin(SCORE), commit=nul)
    with pytest.raises(LookupError):
        registry.registry_at(repository, nul)
    with pytest.raises(LookupError):
        registry.history_problems(repository, nul, imports={})


def test_review_citations_must_name_committed_text_lines(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    write(repository, "docs/note.md", "one\ntwo\nthree\n")
    write(repository, "docs/binary.md", b"\xff\xfe\x00\x01")
    commit_all(repository, "notes")
    entries = [make_entry(0, ["s_a:2020"]), make_entry(1, ["s_b:2025"])]
    entries[1]["overlap_review"].append(review("H001"))
    current = make_registry(entries)
    for citation, ok in (
        ("docs/note.md:2", True),
        ("docs/note.md:2-3", True),
        ("docs/note.md:4", False),
        ("docs/missing.md:1", False),
        ("docs/binary.md:1", False),
        ("docs/note.md:12345678", False),
        ("docs/../docs/note.md:2", False),
    ):
        entries[1]["overlap_review"][0]["evidence"] = [citation]
        assert (validate(current, repository) == []) == ok, citation


def test_complete_needs_its_committed_record(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    current = make_registry([], complete=True)
    assert any("not committed" in p for p in validate(current, repository))
    write(repository, current["completion_record"], {})
    commit_all(repository, "inventory")
    assert validate(current, repository) == []
    for path in ("docs/a\x00b.json", "docs/../docs/design/inventory.json"):
        current["completion_record"] = path
        problems = validate(current, repository)
        assert any("is not a path" in p for p in problems), path


def test_a_pull_request_compares_with_its_merge_base(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    git(repository, "checkout", "-q", "-b", "feature")
    write(repository, "notes.txt", "a commit of the branch's own")
    commit_all(repository, "feature work")
    assert registry.base_registry(repository) is None
    git(repository, "checkout", "-q", "master")
    first = registered(["candidate"])
    commit_registry(repository, first, "registry")
    git(repository, "checkout", "-q", "-b", "feature-2")
    second = copy.deepcopy(first)
    second["entries"].append(make_entry(1, ["s_c:2099"]))
    commit_registry(repository, second, "append")
    assert registry.base_registry(repository) == first


def test_the_base_branch_compares_with_its_parent(tmp_path, no_ci_env):
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
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
    first = registered(["candidate"])
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


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "not json",
        "[]",
        json.dumps({}),
        json.dumps({"before": None}),
        json.dumps({"before": "HEAD"}),
        json.dumps({"before": "b" * 40}),
    ],
)
def test_a_push_without_a_resolvable_before_raises(
    tmp_path, no_ci_env, monkeypatch, payload
):
    repository = init_repository(tmp_path)
    commit_registry(repository, registered(["candidate"]), "registry")
    event = tmp_path / "event.json"
    if payload is not None:
        event.write_text(payload, encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    with pytest.raises(LookupError):
        registry.base_commit(repository)
    with pytest.raises(LookupError):
        registry.base_registry(repository)


@pytest.mark.parametrize("errno_code", [errno.EAGAIN, errno.EMFILE])
def test_a_transient_failure_at_the_push_boundary_raises(
    tmp_path, no_ci_env, monkeypatch, errno_code
):
    repository = init_repository(tmp_path)
    first = registered(["candidate"])
    before = commit_registry(repository, first, "registry")
    changed = copy.deepcopy(first)
    changed["entries"][0]["unit_keys"] = ["s_c:2199"]
    commit_registry(repository, changed, "an immutable key changes")
    commit_registry(repository, first, "and is restored")
    commit_all(repository, "an unchanged tip")
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"before": before}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert registry.base_commit(repository) == before
    assert registry.history_problems(
        repository, registry.base_commit(repository), imports={}
    )
    run = subprocess.run

    def flaky(command, *args, **kwargs):
        if f"{before}^{{commit}}" in command:
            raise OSError(errno_code, os.strerror(errno_code))
        return run(command, *args, **kwargs)

    monkeypatch.setattr(registry.subprocess, "run", flaky)
    with pytest.raises(LookupError):
        registry.base_commit(repository)


def test_no_base_raises_rather_than_passing(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.setenv("GITHUB_BASE_REF", "no-such-branch")
    repository = init_repository(tmp_path)
    with pytest.raises(LookupError):
        registry.base_registry(repository)
    monkeypatch.delenv("GITHUB_BASE_REF")
    with pytest.raises(LookupError):
        registry.base_registry(repository)
