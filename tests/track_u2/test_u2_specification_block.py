"""Section 20 step 5: the final section 15 block equals the code exactly.

The block, U2's rulings record and the TO VERIFY appendix are documentary:
these tests read the specification, the committed registries and the code,
and never a PSID file.  Invariants held here:

* the committed block equals :func:`rows.expected_specification_block`
  under ``==`` and as canonical JSON;
* :func:`rows.check_block_against_code` passes a block exactly when it is
  canonically equal to the code's, and otherwise names every differing
  path (every leaf, every added or dropped key, every JSON type change);
* the rulings record covers every U2 decision and agrees with the
  committed registries and the code;
* the block holds no open value, and every prose TO VERIFY line the
  specification keeps is mapped to its resolution.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import u2_source_registry as registry
from populace_dynamics.uniform_cut_track_u import rows as u1_rows
from populace_dynamics.uniform_cut_track_u2 import identity, rows, sources

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests" / "track_u2"


@pytest.fixture(scope="module")
def registries():
    return sources.RegistrySet.committed()


@pytest.fixture(scope="module")
def block():
    return rows.specification_block()


@pytest.fixture(scope="module")
def spec_lines():
    return identity.SPECIFICATION_PATH.read_text(encoding="utf-8").split("\n")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, allow_nan=False)


def _leaves(value: Any, path: tuple = ()) -> Iterator[tuple[tuple, Any]]:
    if isinstance(value, dict) and value:
        for key, item in value.items():
            yield from _leaves(item, (*path, key))
    elif isinstance(value, list) and value:
        for index, item in enumerate(value):
            yield from _leaves(item, (*path, index))
    else:
        yield path, value


def _mappings(value: Any, path: tuple = ()) -> Iterator[tuple[tuple, dict]]:
    if isinstance(value, dict):
        yield path, value
        for key, item in value.items():
            yield from _mappings(item, (*path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _mappings(item, (*path, index))


def _at(value: Any, path: tuple) -> Any:
    for step in path:
        value = value[step]
    return value


def _dotted(path: tuple) -> str:
    text = ""
    for step in path:
        if isinstance(step, int):
            text += f"[{step}]"
        else:
            text += f".{step}" if text else str(step)
    return text


def _changed(block: dict, path: tuple, value: Any) -> dict:
    changed = copy.deepcopy(block)
    _at(changed, path[:-1])[path[-1]] = value
    return changed


def _other(value: Any) -> Any:
    """A value whose canonical JSON differs from ``value``'s."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 0.25
    if isinstance(value, str):
        return value + "_changed"
    if value == []:
        return [None]
    if value == {}:
        return {"added": None}
    raise AssertionError(value)


def _refused(block: dict, registries, path: tuple) -> None:
    """The check refuses ``block`` and names ``path`` (or, where an empty
    mapping or list gained an element, a path inside it)."""
    with pytest.raises(ValueError, match="differs from the code") as error:
        rows.check_block_against_code(block, registries)
    named = ast.literal_eval(str(error.value).split(" at ", 1)[1])
    where = _dotted(path)
    assert any(
        name == where or name.startswith((f"{where}.", f"{where}["))
        for name in named
    ), (where, named)


# ---------------------------------------------------------------------------
# The block equals the code
# ---------------------------------------------------------------------------
def test_the_committed_block_equals_the_code(block, registries):
    expected = rows.expected_specification_block(registries)
    assert block == expected
    assert _canonical(block) == _canonical(expected)
    assert rows.check_block_against_code(block, registries) == {
        "specification_version": "u2-ratified-1",
        "block_equals_code": True,
    }
    assert block["version"] == rows.SPECIFICATION_VERSION
    assert block["status"] == rows.SPECIFICATION_STATUS


def test_every_leaf_change_is_refused_and_named(block, registries):
    leaves = list(_leaves(block))
    assert len(leaves) > 400
    for path, value in leaves:
        _refused(_changed(block, path, _other(value)), registries, path)


def test_every_json_type_change_is_refused(block, registries):
    """``True`` is not ``1`` and ``1`` is not ``1.0``: equal under ``==``,
    different as canonical JSON, so the check compares types too."""
    swaps = 0
    for path, value in _leaves(block):
        if isinstance(value, bool):
            other: Any = int(value)
        elif isinstance(value, int):
            other = float(value)
        elif isinstance(value, float) and value.is_integer():
            other = int(value)
        else:
            continue
        assert other == value
        _refused(_changed(block, path, other), registries, path)
        swaps += 1
    assert swaps > 50


def test_every_added_or_dropped_key_is_refused(block, registries):
    mappings = list(_mappings(block))
    assert len(mappings) > 60
    for path, mapping in mappings:
        added = copy.deepcopy(block)
        _at(added, path)["unregistered_key"] = None
        _refused(added, registries, (*path, "unregistered_key"))
        for key in mapping:
            dropped = copy.deepcopy(block)
            del _at(dropped, path)[key]
            _refused(dropped, registries, (*path, key))


def test_a_reordered_list_is_refused(block, registries):
    path = ("cells", "scored")
    reordered = list(reversed(_at(block, path)))
    _refused(_changed(block, path, reordered), registries, (*path, 0))


_SCALARS = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**6), max_value=10**12),
    st.floats(allow_nan=False, allow_infinity=False, width=64),
    st.text(max_size=12),
)


@settings(max_examples=300, deadline=None)
@given(index=st.integers(min_value=0), value=_SCALARS)
def test_property_the_check_passes_exactly_the_canonical_block(index, value):
    """For any leaf and any JSON scalar, the check passes the changed block
    exactly when it is canonically the committed one."""
    block = rows.specification_block()
    registries = sources.RegistrySet.committed()
    leaves = list(_leaves(block))
    path, old = leaves[index % len(leaves)]
    changed = _changed(block, path, value)
    if _canonical(value) == _canonical(old):
        assert rows.check_block_against_code(changed, registries)[
            "block_equals_code"
        ]
    else:
        _refused(changed, registries, path)


# ---------------------------------------------------------------------------
# The materialized values
# ---------------------------------------------------------------------------
def _find(value: Any, needle: str) -> list[str]:
    return [
        _dotted(path)
        for path, leaf in _leaves(value)
        if isinstance(leaf, str) and needle in leaf.lower()
    ]


def test_the_block_holds_no_open_value(block):
    assert block["blocked_by"] == []
    assert _find(block, "to_verify") == []
    assert _find(block, "to verify") == []
    assert _find(block, "pending") == []
    spec = importlib.util.spec_from_file_location(
        "u2_registered_for_block_test",
        ROOT / "scripts" / "run_track_u2_registered.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.check_specification_ratified(block)


def test_the_resolved_keys_name_the_code(block, registries):
    dc = block["income_concept"]["employer_dc"]
    reader = ROOT / "src" / "populace_dynamics" / dc["reader"]
    assert reader.resolve() == Path(sources.__file__).resolve()
    assert "def employer_dc_balances(" in reader.read_text(encoding="utf-8")
    assert all(
        entry["status"] == "RESOLVED"
        for entry in registries.entries("pension")
    )
    assert dc["later_wave_mapping_status"].startswith("resolved_")
    routes = dc["previous_routes"]
    assert {
        int(wave): tuple(items)
        for wave, items in routes["account_items_by_wave"].items()
    } == sources.DECLARED_PREVIOUS_ACCOUNT_ITEMS
    assert routes["refused_branches"] == {
        "2015": registry.RATIFIED_AMENDMENTS["5b"]["fields"]["refused_branch"]
    }
    assert block["ssi"]["parameters"]["sha256"] == (
        "a58d55c160b48cd3e21f730d45265374bd3c8a9eb7eae947469a5a5dc0b23762"
    )


def test_the_inherited_and_recorded_identities(spec_lines):
    assert rows._U1_VERSION == u1_rows.specification_block()["version"]
    text = "\n".join(spec_lines)
    section_13 = text[text.index("## 13. ") : text.index("## 14. ")]
    assert rows._U1_INPUT_FRAMES_SHA256 in section_13
    section_20 = text[text.index("## 20. ") : text.index("## Appendix")]
    assert rows._STEP_4_SECOND_HEAD in section_20
    assert str(rows._STEP_4_SECOND_TESTS_RUN) in section_20
    assert f"`{rows._STEP_4_FIRST_HEAD[:8]}`" in section_20


# ---------------------------------------------------------------------------
# U2's rulings record
# ---------------------------------------------------------------------------
def test_the_rulings_record_covers_every_ruling(block, registries):
    assert block["decisions"] == {
        "ruled_by": "Max",
        "ruled_on": "2026-09-28",
        **rows.U2_RULINGS,
    }
    assert rows.check_rulings_against_code(registries) == {
        "decisions": list(rows.RULING_DECISIONS),
        "entries": len(rows.U2_RULINGS),
        "rulings_equal_the_code": True,
    }
    assert rows.RULING_DECISIONS == (
        "d514",
        "d637",
        "d745",
        "d1090",
        "d1242",
        "d1597",
        "d1649",
        "d1724",
    )
    for decision in ("d637", "d1090", "d1724"):
        assert any(
            entry["decision_record"] == decision
            for entry in rows.U2_RULINGS.values()
        )
    assert {
        entry["confirmed_by"]
        for entry in rows.U2_RULINGS.values()
        if "confirmed_by" in entry
    } == {"d745"}


def test_every_section_16_ruling_is_a_d514_entry(spec_lines):
    """Section 16's decision table, ruled by d514: each row is an entry."""
    text = "\n".join(spec_lines)
    section = text[text.index("## 16. ") : text.index("## 16a. ")]
    names = re.findall(r"^\| ([A-Z][^|]+?) \| ", section, re.M)
    assert names[0] == "Decision"
    keys = {
        re.sub(r"[^a-z]+", "_", name.lower()).strip("_") for name in names[1:]
    }
    assert len(keys) == 8
    for key in keys:
        assert rows.U2_RULINGS[key]["decision_record"] == "d514", key


def test_registry_rulings_are_the_registry_scopes():
    for code, scope in registry.RATIFIED_AMENDMENTS.items():
        entries = [
            entry
            for entry in rows.U2_RULINGS.values()
            if entry.get("registry_entries")
            == [f"{scope['registry']}:{e}" for e in scope["entries"]]
        ]
        assert len(entries) == 1, code
        assert entries[0]["decision_record"] == scope["ruling"]["decision"]
        assert entries[0]["ruled_on"] == scope["ruling"]["date"]
    for disposition, scope in registry.RATIFIED_EXCLUSIONS.items():
        (entry,) = (
            e
            for e in rows.U2_RULINGS.values()
            if e.get("disposition") == disposition
        )
        assert entry["registry_entries"] == [
            f"roles:{e}" for e in scope["entries"]
        ]
        assert entry["amends_draft_3_lines"] == list(
            scope["ruling"]["amends_draft_3_lines"]
        )


def _without_reference(key: str, reference: str) -> dict:
    record = copy.deepcopy(rows.U2_RULINGS)
    record[key]["registry_entries"].remove(reference)
    return record


@pytest.mark.parametrize(
    "record, message",
    [
        (
            _without_reference(
                "amendment_1a_documented_routes", "roles:2017.relationship.92"
            ),
            "ratified scopes",
        ),
        (
            _without_reference(
                "blocker_b2_codes_90_92_2019_2023",
                "roles:2023.relationship.92",
            ),
            "roles registry carries it",
        ),
        (
            {
                **rows.U2_RULINGS,
                "unrecorded": {"ruling": "x", "decision_record": "d9999"},
            },
            "names",
        ),
        (
            {
                key: value
                for key, value in rows.U2_RULINGS.items()
                if value["decision_record"] != "d1597"
            },
            "names",
        ),
        (
            {
                **rows.U2_RULINGS,
                "amendment_5c_u7_2015_spouse_slot": {
                    **rows.U2_RULINGS["amendment_5c_u7_2015_spouse_slot"],
                    "decision_record": "d637",
                },
            },
            "records 'd1090'",
        ),
        (
            {
                **rows.U2_RULINGS,
                "amendment_5c_u7_2015_spouse_slot": {
                    **rows.U2_RULINGS["amendment_5c_u7_2015_spouse_slot"],
                    "registry_entries": ["pension:2015.route.no_such_entry"],
                },
            },
            "not a RESOLVED registry entry",
        ),
        (
            {
                **rows.U2_RULINGS,
                "blocker_b1_male_code_20_2015": {
                    **rows.U2_RULINGS["blocker_b1_male_code_20_2015"],
                    "option": "1d-1",
                },
            },
            "another option",
        ),
        (
            {
                **rows.U2_RULINGS,
                "amendment_6_blocker_b3_2017_weight": {
                    **rows.U2_RULINGS["amendment_6_blocker_b3_2017_weight"],
                    "option": "2",
                },
            },
            "another option",
        ),
        (
            {
                key: value
                for key, value in rows.U2_RULINGS.items()
                if key != "blocker_b1_male_code_20_2015"
            },
            "no entry for the d1090 exclusion",
        ),
        (
            {
                **rows.U2_RULINGS,
                "b2_disclosed_count": {
                    **rows.U2_RULINGS["b2_disclosed_count"],
                    "person_counted_exclusions": [sources.MALE_CODE_20_2015],
                },
            },
            "d1242",
        ),
        (
            {
                **rows.U2_RULINGS,
                "seed_birth_year_support": {
                    **rows.U2_RULINGS["seed_birth_year_support"],
                    "support": [1890, 2016],
                },
            },
            "d1724",
        ),
    ],
)
def test_a_changed_rulings_record_is_refused(
    monkeypatch, registries, record, message
):
    monkeypatch.setattr(rows, "U2_RULINGS", record)
    with pytest.raises(ValueError, match=message):
        rows.check_rulings_against_code(registries)


# ---------------------------------------------------------------------------
# The TO VERIFY appendix
# ---------------------------------------------------------------------------
_APPENDIX = "## Appendix: TO VERIFY item → where resolved"


def _appendix_rows(spec_lines: list[str]) -> list[list[str]]:
    start = spec_lines.index(_APPENDIX)
    table = [
        line
        for line in spec_lines[start:]
        if line.startswith("| ") and not line.startswith("|---")
    ]
    assert (
        table[0]
        == "| Line | Item left open in draft 3 | Resolution | Evidence |"
    )
    return [
        [cell.strip() for cell in line.strip("|").split(" | ")]
        for line in table[1:]
    ]


def test_the_to_verify_appendix_is_complete(spec_lines):
    """Every line before section 15 that still says TO VERIFY, and section
    17's closing line, has a row; every row names such a line."""
    section_15 = spec_lines.index("## 15. Machine-readable parameter block")
    open_lines = {
        number
        for number, line in enumerate(spec_lines[:section_15], 1)
        if "TO VERIFY" in line or "TO_VERIFY" in line
    }
    table = _appendix_rows(spec_lines)
    listed = [row[0] for row in table]
    assert listed[-1] == "§17's closing line"
    assert {int(line) for line in listed[:-1]} == open_lines
    assert listed[:-1] == sorted(listed[:-1], key=int)
    section_17 = spec_lines.index(
        next(x for x in spec_lines if x.startswith("## 17. "))
    )
    section_18 = spec_lines.index(
        next(x for x in spec_lines if x.startswith("## 18. "))
    )
    closing = [x for x in spec_lines[section_17:section_18] if x.strip()][-1]
    assert "TO VERIFY" in closing
    assert table[-1][1].replace("TO VERIFY", "**TO VERIFY**") in closing


def test_the_appendix_evidence_exists(spec_lines, registries):
    """Each test the appendix cites exists; each ``decisions`` key and
    ``income_concept`` path it names is in the block; and each registry
    entry it names (``roles:2017.relationship.92``) is RESOLVED."""
    block = rows.specification_block()
    tests = {
        path.name: path.read_text(encoding="utf-8")
        for path in TESTS.glob("test_*.py")
    }
    cited_tests = cited_paths = cited_entries = 0
    for row in _appendix_rows(spec_lines):
        evidence = row[3]
        module = None
        for name, test in re.findall(
            r"`(?:(test_[a-z0-9_]+\.py))?::(test_[a-z0-9_]+)`", evidence
        ):
            module = name or module
            assert module in tests, module
            assert f"def {test}(" in tests[module], (module, test)
            cited_tests += 1
        for key in re.findall(
            r"`decisions\.([a-z0-9_]+)`|`\.([a-z0-9_]+)`", evidence
        ):
            name = key[0] or key[1]
            assert name in block["decisions"], name
        for path in re.findall(
            r"`(income_concept(?:\.[a-z0-9_]+)+)`", evidence
        ):
            _at(block, tuple(path.split(".")))
            cited_paths += 1
        for name, entry_id in re.findall(
            r"`([a-z]+):(\d{4}\.[a-z_]+(?:\.\d+)?)`", evidence
        ):
            (entry,) = (
                e for e in registries.entries(name) if e["id"] == entry_id
            )
            assert entry["status"] == "RESOLVED", (name, entry_id)
            cited_entries += 1
    assert cited_tests >= 14
    assert cited_paths >= 1
    assert cited_entries >= 5


# ---------------------------------------------------------------------------
# Review of 690a1276: the gaps its mutants and probes found
# ---------------------------------------------------------------------------
class _Altered:
    """The committed registries with one entry's fields changed."""

    def __init__(self, base, name: str, entry_id: str, **changes: Any):
        self._base = base
        self._name = name
        self._id = entry_id
        self._changes = changes

    def entries(self, name: str) -> list[dict]:
        out = [dict(entry) for entry in self._base.entries(name)]
        if name == self._name:
            (entry,) = (e for e in out if e["id"] == self._id)
            entry.update(self._changes)
        return out


def test_a_repeated_key_is_refused(tmp_path):
    """Finding 2: ``json.loads`` keeps the last of a repeated key, so a
    draft value could stand in the text while the check saw the last."""
    text = identity.SPECIFICATION_PATH.read_text(encoding="utf-8")
    top = '  "version": "u2-ratified-1",'
    nested = '      "unreported_amount": "zero_counted",'
    for old, new, key in (
        (top, '  "version": "u2-draft-4",\n' + top, "version"),
        (
            nested,
            '      "unreported_amount": "not_counted",\n' + nested,
            "unreported_amount",
        ),
    ):
        assert text.count(old) == 1
        path = tmp_path / f"spec-{key}.md"
        path.write_text(text.replace(old, new), encoding="utf-8")
        with pytest.raises(ValueError, match=f"repeats keys \\['{key}'\\]"):
            rows.specification_block(path)


def test_dc_persons_and_plans_are_the_readers(monkeypatch, block, registries):
    """Finding 3: the block's employer-DC persons and previous plans are
    the ones the reader walks."""
    path = ("income_concept", "employer_dc")
    monkeypatch.setattr(sources, "DC_PERSONS", ("head",))
    _refused(block, registries, (*path, "persons"))
    monkeypatch.setattr(sources, "DC_PERSONS", ("head", "wife"))
    monkeypatch.setattr(sources, "DC_PLANS", (1, 2, 3))
    _refused(block, registries, (*path, "previous_plans"))


def test_the_reader_resolves_through_a_symlink(
    tmp_path, monkeypatch, block, registries
):
    """Finding 4: a checkout reached through a symlink (macOS ``/tmp``)
    names the same reader."""
    link = tmp_path / "linked-src"
    link.symlink_to(ROOT / "src", target_is_directory=True)
    linked = link / "populace_dynamics" / "uniform_cut_track_u2" / "sources.py"
    assert linked.resolve() == Path(sources.__file__).resolve()
    monkeypatch.setattr(rows.inspect, "getsourcefile", lambda _: str(linked))
    assert rows.check_block_against_code(block, registries)[
        "block_equals_code"
    ]


def test_negative_zero_is_refused(block, registries):
    """Finding 7: ``-0.0`` equals ``0.0`` under ``==`` but not as JSON."""
    path = ("income_concept", "annuity", "load")
    assert _at(block, path) == 0.0
    _refused(_changed(block, path, -0.0), registries, path)


def test_a_named_script_must_exist(monkeypatch):
    with pytest.raises(ValueError, match="does not exist"):
        rows._existing("scripts/no_such_u2_script.py")
    assert rows._existing("scripts/track_u2_structure.py") == (
        "scripts/track_u2_structure.py"
    )


@pytest.mark.parametrize(
    "name, entry_id, message",
    [
        ("pension", "2015.route.respondent_slots", "pension registry entry"),
        ("individual", "2017.weight", "2017.weight is not RESOLVED"),
        ("wealth", "wealth.2019.wealth1", "wealth1 is not RESOLVED"),
        ("design", "common.stratum", "stratum is not RESOLVED"),
    ],
)
def test_the_block_needs_resolved_registry_entries(
    registries, name, entry_id, message
):
    """Finding 5 (mutants M and N): the block is stated only from
    RESOLVED registry entries."""
    altered = _Altered(registries, name, entry_id, status="TO_VERIFY")
    with pytest.raises(ValueError, match=message):
        rows.expected_specification_block(altered)


def test_the_rulings_need_resolved_registry_entries(registries):
    """Finding 5 (mutant E): a named entry that is not RESOLVED refuses."""
    altered = _Altered(
        registries, "roles", "2017.relationship.92", status="TO_VERIFY"
    )
    with pytest.raises(ValueError, match="not a RESOLVED registry entry"):
        rows.check_rulings_against_code(altered)


def test_b2s_person_count_must_be_made(monkeypatch, registries):
    """Finding 5 (mutant C): d1242 needs B2 among the person counts."""
    monkeypatch.setattr(
        sources, "PERSON_COUNTED_EXCLUSIONS", (sources.MALE_CODE_20_2015,)
    )
    with pytest.raises(ValueError, match="d1242"):
        rows.check_rulings_against_code(registries)
    # Review of 9f79818a, finding 3: with the record changed to match, the
    # d1242 fact itself (B2 is a person count) still refuses.
    record = copy.deepcopy(rows.U2_RULINGS)
    record["b2_disclosed_count"]["person_counted_exclusions"] = [
        sources.MALE_CODE_20_2015
    ]
    monkeypatch.setattr(rows, "U2_RULINGS", record)
    with pytest.raises(ValueError, match="d1242"):
        rows.check_rulings_against_code(registries)


def test_each_authorization_records_every_use():
    """Finding 1: d1597's load ran before each step-4 pass; d1649's and
    d1724's passes ran once each."""
    uses = {
        key: rows.U2_RULINGS[key]["authorization_used"]
        for key in (
            "u1_input_pin_check",
            "preregistration_pass",
            "seed_birth_year_support",
        )
    }
    assert [(u["on"], u["head"]) for u in uses["u1_input_pin_check"]] == [
        ("2026-10-19", rows._STEP_4_FIRST_HEAD),
        ("2026-10-21", rows._STEP_4_SECOND_HEAD),
    ]
    assert {u["result"] for u in uses["u1_input_pin_check"]} == {"pin_matched"}
    assert [u["head"] for u in uses["preregistration_pass"]] == [
        rows._STEP_4_FIRST_HEAD
    ]
    assert [u["head"] for u in uses["seed_birth_year_support"]] == [
        rows._STEP_4_SECOND_HEAD
    ]
    assert not rows.U2_RULINGS["u1_input_pin_check"]["ruling"].endswith("once")
