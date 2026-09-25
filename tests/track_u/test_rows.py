"""The registered Track U rows equal the specification block.

Reads only the specification document and the code: no PSID value, no
model output and no comparator value.
"""

from __future__ import annotations

import copy

import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u import rows


@pytest.fixture(scope="module")
def block() -> dict:
    return rows.specification_block()


def test_the_code_rows_equal_the_committed_block(block):
    check = rows.check_rows_against_block(block)
    assert check["rows_equal_the_block"]
    assert check["specification_version"] == block["version"] == "u1-draft-5"
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
    assert not registered["U7"].built
    assert "label investigation" in registered["U7"].not_built_reason
    assert registered["U8"].income_spec().threshold_rule == (
        "psid_census_needs_standard"
    )
    assert registered["U9"].income_spec().mortality_basis == (
        "ssa_period_2004"
    )
    assert registered["U10"].income_spec().threshold_rule == (
        "census_matrix_65plus"
    )
    # U0-F is U0 on the fallback birth years; its headline status awaits
    # Max's ruling on the fallback rule
    fallback = registered[rows.FALLBACK_ROW]
    assert fallback.age67_spec() == age67.Age67Spec(row="U0-F")
    assert fallback.income_spec() == ap.AdjustedPovertySpec()
    assert "fallback rule" in fallback.awaiting


def test_the_one_field_alternatives_are_registered_on_u0f_too():
    """Second referee S8: U2-F ... U10-F carry the field and value of U2
    ... U10 on U0-F's population, each awaiting the fallback rule."""

    registered = rows.REGISTERED_ROWS
    assert rows.FALLBACK_ALTERNATIVES == {
        "U2": "U2-F",
        "U3": "U3-F",
        "U4": "U4-F",
        "U5": "U5-F",
        "U8": "U8-F",
        "U9": "U9-F",
        "U10": "U10-F",
    }
    for base, alternative in rows.FALLBACK_ALTERNATIVES.items():
        row = registered[alternative]
        assert row.age67_spec() == age67.Age67Spec(row=rows.FALLBACK_ROW)
        assert row.income_spec() == registered[base].income_spec()
        assert row.field_changed == registered[base].field_changed
        assert row.awaiting == registered[rows.FALLBACK_ROW].awaiting
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
    assert not rows.row_from_block(
        "U7", {"financial_assets": "y", "status": "not_built"}
    )["built"]
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
        ("U7", {"status": None}),
    ],
)
def test_a_block_that_differs_from_the_code_is_refused(block, row_id, edit):
    changed = copy.deepcopy(block)
    changed["rows"][row_id].update(edit)
    if edit.get("status", "keep") is None:
        del changed["rows"][row_id]["status"]
        del changed["rows"][row_id]["financial_assets"]
    with pytest.raises(ValueError, match=f"row {row_id} differs"):
        rows.check_rows_against_block(changed)


def test_a_resolved_awaiting_note_must_be_resolved_in_both_places(block):
    changed = copy.deepcopy(block)
    del changed["rows"]["U10-F"]["awaiting"]
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
