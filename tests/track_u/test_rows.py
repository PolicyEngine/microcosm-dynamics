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
    assert check["specification_version"] == block["version"] == "u1-draft-3"
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
    # U6 is defined on U1 and differs in the cut's start year only
    assert registered["U6"].age67_spec() == registered["U1"].age67_spec()
    assert registered["U6"].income_spec().cut_start_year == 2004
    assert registered["U6"].awaiting and "decision 8" in (
        registered["U6"].awaiting
    )
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
    inst = registered["U-inst"].age67_spec()
    assert inst.presence == "in_family_or_institution"
    assert inst.institution_income_rule == "family_of_record"
    assert "referee" in registered["U-inst"].awaiting


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
        "U6", {"on": "U1", "cut_start_year": 2004, "awaiting": "x"}
    )
    assert parsed["age67"] == {"row": "U1"}
    assert parsed["income"] == {"cut_start_year": 2004}
    assert parsed["awaiting"] == "x"
    assert not rows.row_from_block(
        "U7", {"financial_assets": "y", "status": "not_built"}
    )["built"]
    with pytest.raises(ValueError, match="unknown block key"):
        rows.row_from_block("U9", {"mortality": "nchs_2000"})
    with pytest.raises(ValueError, match="not known"):
        rows.row_from_block("U1", {"on": "U0"})
    with pytest.raises(ValueError, match="unknown status"):
        rows.row_from_block("U-inst", {"status": "counted_only"})


@pytest.mark.parametrize(
    ("row_id", "edit"),
    [
        ("U2", {"ssi_rule": "full_static_recomputation"}),
        ("U6", {"cut_start_year": 2005}),
        ("U-inst", {"institution_income_rule": "excluded"}),
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
    del changed["rows"]["U6"]["awaiting"]
    with pytest.raises(ValueError, match="row U6 differs"):
        rows.check_rows_against_block(changed)
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
