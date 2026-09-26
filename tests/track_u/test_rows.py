"""The registered Track U rows equal the specification block.

Reads only the specification document and the code: no PSID value, no
model output and no comparator value.
"""

from __future__ import annotations

import copy
import datetime
import json

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u import rows


@pytest.fixture(scope="module")
def block() -> dict:
    return rows.specification_block()


def test_the_code_rows_equal_the_committed_block(block):
    check = rows.check_rows_against_block(block)
    assert check["rows_equal_the_block"]
    assert (
        check["specification_version"] == block["version"] == "u1-ratified-1"
    )
    assert check["rows_checked"] == sorted(rows.REGISTERED_ROWS)


def test_each_row_changes_the_field_the_plan_names():
    registered = rows.REGISTERED_ROWS
    assert registered["U0"].age67_spec() == age67.Age67Spec()
    assert registered["U0"].income_spec() == ap.AdjustedPovertySpec()
    assert registered["U1"].age67_spec().row == "U1"
    assert registered["U2"].income_spec().ssi_rule == "none"
    assert registered["U3"].income_spec().ssi_rule == (
        "full_static_recomputation"
    )
    assert registered["U4"].income_spec().income_unit == "head_wife"
    assert registered["U5"].income_spec().asset_income_rule == "keep"
    # u1-draft-5 (second referee S5, S7): U6 and U-inst are withdrawn; the
    # primary cuts from 2004, so U1 carries the 1936 birth year uncut
    assert "U6" not in registered and "U-inst" not in registered
    assert registered["U0"].income_spec().cut_start_year == 2004
    assert registered["U1"].income_spec().cut_start_year == 2004
    assert registered["U0"].age67_spec().presence == "in_family"
    # u1-draft-7: U7 is built (the PSID pension section's employer DC
    # balances added to WEALTH1)
    assert registered["U7"].built
    assert registered["U7"].income_spec() == ap.AdjustedPovertySpec(
        financial_assets="wealth1_plus_employer_dc"
    )
    assert registered["U0"].income_spec().financial_assets == "wealth1"
    assert all(row.built for row in registered.values())
    assert registered["U8"].income_spec().threshold_rule == (
        "psid_census_needs_standard"
    )
    assert registered["U9"].income_spec().mortality_basis == (
        "ssa_period_2004"
    )
    assert registered["U10"].income_spec().threshold_rule == (
        "census_matrix_65plus"
    )
    # U0-F is U0 on the fallback birth years; since u1-draft-7 the
    # fallback rule is resolved (U0 the headline) and no row awaits Max
    fallback = registered[rows.FALLBACK_ROW]
    assert fallback.age67_spec() == age67.Age67Spec(row="U0-F")
    assert fallback.income_spec() == ap.AdjustedPovertySpec()
    assert all(row.awaiting is None for row in registered.values())


def test_the_one_field_alternatives_are_registered_on_u0f_too():
    """Second referee S8: U2-F ... U10-F carry the field and value of U2
    ... U10 on U0-F's population (U7-F since u1-draft-7)."""

    registered = rows.REGISTERED_ROWS
    assert rows.FALLBACK_ALTERNATIVES == {
        "U2": "U2-F",
        "U3": "U3-F",
        "U4": "U4-F",
        "U5": "U5-F",
        "U7": "U7-F",
        "U8": "U8-F",
        "U9": "U9-F",
        "U10": "U10-F",
    }
    for base, alternative in rows.FALLBACK_ALTERNATIVES.items():
        row = registered[alternative]
        assert row.age67_spec() == age67.Age67Spec(row=rows.FALLBACK_ROW)
        assert row.income_spec() == registered[base].income_spec()
        assert row.field_changed == registered[base].field_changed
        assert row.awaiting is None
        assert row.built
    # the -F rows need no wave without WEALTH1
    assert {
        w
        for alternative in rows.FALLBACK_ALTERNATIVES.values()
        for _, w, _, _ in age67.observation_plan(
            registered[alternative].age67_spec()
        )
    } == {2009, 2011, 2013}


def test_row_from_block_reads_populations_and_overrides():
    assert rows.row_from_block(
        "U1", {"population": "all_ten_birth_years"}
    ) == {
        "age67": {"row": "U1"},
        "income": {},
        "built": True,
        "awaiting": None,
    }
    parsed = rows.row_from_block(
        "X", {"on": "U1", "cut_start_year": 2004, "awaiting": "x"}
    )
    assert parsed["age67"] == {"row": "U1"}
    assert parsed["income"] == {"cut_start_year": 2004}
    assert parsed["awaiting"] == "x"
    assert rows.row_from_block(
        "U3-F",
        {
            "population": "birth_years_1941_1943_1945",
            "ssi_rule": "full_static_recomputation",
            "awaiting": "y",
        },
    ) == {
        "age67": {"row": "U0-F"},
        "income": {"ssi_rule": "full_static_recomputation"},
        "built": True,
        "awaiting": "y",
    }
    assert not rows.row_from_block("U7", {"status": "not_built"})["built"]
    # u1-draft-7: financial_assets is an income-concept field, not a
    # description
    assert rows.row_from_block(
        "U7-F",
        {
            "population": "birth_years_1941_1943_1945",
            "financial_assets": "wealth1_plus_employer_dc",
        },
    ) == {
        "age67": {"row": "U0-F"},
        "income": {"financial_assets": "wealth1_plus_employer_dc"},
        "built": True,
        "awaiting": None,
    }
    assert rows.row_from_block(
        "U0-F",
        {
            "population": "birth_years_1941_1943_1945",
            "on": "U0",
            "awaiting": "y",
        },
    ) == {
        "age67": {"row": "U0-F"},
        "income": {},
        "built": True,
        "awaiting": "y",
    }
    assert rows.row_from_block("U0", {"on": "U0"})["age67"] == {}
    with pytest.raises(ValueError, match="unknown block key"):
        rows.row_from_block("U9", {"mortality": "nchs_2000"})
    with pytest.raises(ValueError, match="not known"):
        rows.row_from_block("U1", {"on": "U2"})
    with pytest.raises(ValueError, match="not known"):
        rows.row_from_block("U1", {"population": "birth_years_1937"})
    with pytest.raises(ValueError, match="unknown status"):
        rows.row_from_block("U8", {"status": "counted_only"})


@pytest.mark.parametrize(
    ("row_id", "edit"),
    [
        ("U2", {"ssi_rule": "full_static_recomputation"}),
        ("U1", {"cut_start_year": 2005}),
        ("U4-F", {"income_unit": "family_unit"}),
        ("U9-F", {"population": "all_ten_birth_years"}),
        ("U0-F", {"population": "all_ten_birth_years"}),
        ("U7", {"status": "not_built"}),
        ("U7", {"financial_assets": "wealth1"}),
        ("U7-F", {"financial_assets": "wealth1"}),
    ],
)
def test_a_block_that_differs_from_the_code_is_refused(block, row_id, edit):
    changed = copy.deepcopy(block)
    changed["rows"][row_id].update(edit)
    with pytest.raises(ValueError, match=f"row {row_id} differs"):
        rows.check_rows_against_block(changed)


def test_a_resolved_awaiting_note_must_be_resolved_in_both_places(block):
    """An ``awaiting`` note on a block row that the code does not carry
    (or the reverse) is refused; since u1-draft-7 neither side carries one
    (the fallback rule is resolved)."""

    changed = copy.deepcopy(block)
    changed["rows"]["U10-F"]["awaiting"] = "Max (the fallback rule)"
    with pytest.raises(ValueError, match="row U10-F differs"):
        rows.check_rows_against_block(changed)
    withdrawn = copy.deepcopy(block)
    withdrawn["rows"]["U6"] = {"on": "U1", "cut_start_year": 2004}
    with pytest.raises(ValueError, match="differ from the block"):
        rows.check_rows_against_block(withdrawn)
    missing = copy.deepcopy(block)
    del missing["rows"]["U10"]
    with pytest.raises(ValueError, match="differ from the block"):
        rows.check_rows_against_block(missing)


def test_rows_validate_their_fields():
    with pytest.raises(ValueError, match="unknown fields"):
        rows.TrackURow("X", "-", "x", income={"cut": 0.2})
    with pytest.raises(ValueError, match="needs a reason"):
        rows.TrackURow("X", "-", "x", built=False)
    with pytest.raises(ap.AdjustedPovertyError):
        rows.TrackURow("X", "-", "x", income={"cut_start_year": 1900})


def test_the_code_rulings_equal_the_committed_block(block):
    """u1-ratified-1: the block's ``decisions`` equal ``MAX_RULINGS``
    (cos decisions d189 and d411)."""

    check = rows.check_rulings_against_block(block)
    assert check == {
        "rulings_checked": sorted(rows.MAX_RULINGS),
        "rulings_equal": True,
    }
    assert rows.MAX_RULINGS["rows"]["ruling"] == list(rows.REGISTERED_ROWS)
    assert rows.MAX_RULINGS["headline_row"]["ruling"] == rows.PRIMARY_ROW
    assert rows.MAX_RULINGS["headline_row"]["rule"] == rows.HEADLINE_RULE


def _without(mapping: dict, key: str) -> dict:
    out = copy.deepcopy(mapping)
    del out[key]
    return out


@pytest.mark.parametrize(
    ("edit", "match"),
    [
        (
            lambda d: d["ssi_rule"].update(ruling="none"),
            "differ from the code's MAX_RULINGS",
        ),
        (
            lambda d: d["memo_small_cells"]["ruling"].update(
                flag_unweighted_n_below=20
            ),
            "differ from the code's MAX_RULINGS",
        ),
        (
            lambda d: d["rows"]["ruling"].append("U6"),
            "differ from the code's MAX_RULINGS",
        ),
        (
            lambda d: d.pop("freeze_defaults"),
            r"\['freeze_defaults'\]",
        ),
        (
            lambda d: d.update(extra={"ruling": "x"}),
            r"\['extra'\]",
        ),
        (lambda d: d.pop("ruled_by"), "no ruling by Max"),
        (lambda d: d.update(ruled_by="the orchestrator"), "no ruling by Max"),
        (lambda d: d.pop("ruled_on"), "no ruling by Max"),
        (lambda d: d.clear(), "no ruling by Max"),
    ],
    ids=[
        "changed-ruling",
        "changed-memo-threshold",
        "withdrawn-row",
        "missing-field",
        "extra-field",
        "no-ruled-by",
        "other-ruler",
        "no-ruled-on",
        "no-decisions",
    ],
)
def test_a_block_whose_rulings_differ_is_refused(block, edit, match):
    changed = copy.deepcopy(block)
    edit(changed["decisions"])
    with pytest.raises(ValueError, match=match):
        rows.check_rulings_against_block(changed)
    with pytest.raises(ValueError, match="no ruling by Max"):
        rows.check_rulings_against_block(_without(block, "decisions"))


# Invariant of the rulings gate (u1-ratified-1, cos decision d411): for
# every block, ``check_rulings_against_block`` passes exactly when the
# block's ``decisions`` record ``ruled_by`` "Max", a ``YYYY-MM-DD``
# ``ruled_on`` and, besides those two keys, a mapping equal to
# ``MAX_RULINGS`` as JSON (key order free, list order and value types
# not); it never modifies the block.  The properties below execute both
# directions on generated blocks; no value in them is a PSID value.


def _paths(value, path=()):
    """Every key or index path into ``value``, leaves and containers."""

    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = enumerate(value)
    else:
        return
    for key, item in items:
        yield (*path, key)
        yield from _paths(item, (*path, key))


def _leaf_paths(value):
    def leaf(path):
        target = value
        for key in path:
            target = target[key]
        return not isinstance(target, dict | list)

    return tuple(path for path in _paths(value) if leaf(path))


_ALL_PATHS = tuple(_paths(rows.MAX_RULINGS))
_LEAF_PATHS = _leaf_paths(rows.MAX_RULINGS)
_JSON_VALUES = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(-5, 3000)
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=12),
    lambda children: st.lists(children, max_size=3)
    | st.dictionaries(st.text(max_size=6), children, max_size=3),
    max_leaves=6,
)


def _json(value) -> str:
    return json.dumps(value, sort_keys=True)


def _parent(decisions: dict, path: tuple):
    target = decisions
    for key in path[:-1]:
        target = target[key]
    return target


def test_the_rulings_have_leaves_and_containers_to_mutate():
    assert len(_LEAF_PATHS) > 60
    assert len(_ALL_PATHS) > len(_LEAF_PATHS)
    assert ("rows", "ruling", 0) in _LEAF_PATHS
    assert ("memo_small_cells", "ruling", "flag_unweighted_n_below") in (
        _LEAF_PATHS
    )


@settings(max_examples=100, deadline=None)
@given(
    ruled_on=st.dates().map(datetime.date.isoformat),
    order=st.permutations(sorted(rows.MAX_RULINGS)),
)
def test_equal_rulings_pass_in_any_key_order_and_are_not_modified(
    ruled_on, order
):
    decisions = {"ruled_by": "Max", "ruled_on": ruled_on}
    for name in order:
        decisions[name] = copy.deepcopy(rows.MAX_RULINGS[name])
    candidate = {"decisions": decisions}
    before = _json(candidate)
    check = rows.check_rulings_against_block(candidate)
    assert check == {
        "rulings_checked": sorted(rows.MAX_RULINGS),
        "rulings_equal": True,
    }
    assert _json(candidate) == before


@settings(max_examples=200, deadline=None)
@given(path=st.sampled_from(_LEAF_PATHS), value=_JSON_VALUES)
def test_any_changed_ruling_value_is_refused(block, path, value):
    changed = copy.deepcopy(block)
    parent = _parent(changed["decisions"], path)
    assume(_json(parent[path[-1]]) != _json(value))
    parent[path[-1]] = value
    with pytest.raises(ValueError, match="differ from the code's MAX_RULINGS"):
        rows.check_rulings_against_block(changed)


@settings(max_examples=150, deadline=None)
@given(path=st.sampled_from(_ALL_PATHS))
def test_any_removed_ruling_key_or_item_is_refused(block, path):
    changed = copy.deepcopy(block)
    del _parent(changed["decisions"], path)[path[-1]]
    with pytest.raises(ValueError, match="differ from the code's MAX_RULINGS"):
        rows.check_rulings_against_block(changed)


@settings(max_examples=100, deadline=None)
@given(
    ruled_by=_JSON_VALUES.filter(lambda value: value != "Max"),
    ruled_on=_JSON_VALUES,
)
def test_a_ruling_not_by_max_or_undated_is_refused(block, ruled_by, ruled_on):
    by_other = copy.deepcopy(block)
    by_other["decisions"]["ruled_by"] = ruled_by
    with pytest.raises(ValueError, match="no ruling by Max"):
        rows.check_rulings_against_block(by_other)
    undated = copy.deepcopy(block)
    undated["decisions"]["ruled_on"] = ruled_on
    digits = set("0123456789")
    dated = (
        isinstance(ruled_on, str)
        and len(ruled_on) == 10
        and ruled_on[4] == ruled_on[7] == "-"
        and set(ruled_on[:4] + ruled_on[5:7] + ruled_on[8:]) <= digits
    )
    if dated:
        assert rows.check_rulings_against_block(undated)["rulings_equal"]
    else:
        with pytest.raises(ValueError, match="no ruling by Max"):
            rows.check_rulings_against_block(undated)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("ratification_and_registration", "publishes_regardless"), 1),
        (("cut_start_year", "ruling"), 2004.0),
        (("memo_small_cells", "ruling", "flag_unweighted_n_below"), 30.0),
        (("acceptance_rule", "ruling"), False),
        (("cut_start_year", "declined", 0), 0),
    ],
    ids=["true-as-1", "2004-as-float", "30-as-float", "null-as-false", "none"],
)
def test_a_ruling_equal_only_under_python_equality_is_refused(
    block, path, value
):
    """Python's ``==`` takes ``1`` for ``True`` and ``2004.0`` for
    ``2004``; the gate compares as JSON, so a block that changes a
    ruling's type is refused."""

    changed = copy.deepcopy(block)
    _parent(changed["decisions"], path)[path[-1]] = value
    with pytest.raises(ValueError, match="differ from the code's MAX_RULINGS"):
        rows.check_rulings_against_block(changed)


@pytest.mark.parametrize("decisions", [None, [], ["ab"], "Max", 0], ids=repr)
def test_decisions_that_are_not_a_mapping_are_refused(decisions):
    with pytest.raises(ValueError, match="no ruling by Max"):
        rows.check_rulings_against_block({"decisions": decisions})
