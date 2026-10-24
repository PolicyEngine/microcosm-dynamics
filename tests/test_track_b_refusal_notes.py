"""Statutory conformance: exception metadata on invented refusals only.

Notes do not affect money, provenance or denominator accounting. No
population, behavioral or forecast claim is admitted.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.test_track_b_gross_benefits_fix_round_12_contract import (
    EVALUATE,
    LAYERS,
    _outcome,
)


@pytest.mark.parametrize("layer", LAYERS)
@settings(max_examples=10, deadline=None, derandomize=True)
@given(notes=st.lists(st.text(), min_size=1, max_size=4))
def test_refusal_note_deletion_preserves_provenance_and_denominator(
    layer, notes
):
    refusal = _outcome(layer, refused=True).unsupported
    for note in notes:
        refusal.add_note(note)
    assert refusal.__notes__ == notes
    type(refusal).__delattr__(refusal, "__notes__")
    assert not hasattr(refusal, "__notes__")

    def refuse():
        raise refusal

    row = EVALUATE[layer]("notes-deleted", 1, refuse)
    assert row.unsupported is refusal
    counts = g.count_family_outcomes((row,))
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.unsupported_by_reason == {refusal.reason: (1, 1)}
    refusal.add_note("new note")
    assert refusal.__notes__ == ["new note"]


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("notes", ("not a list", [1], ("not a list",)))
def test_refusal_note_assignment_still_enforces_schema(layer, notes):
    refusal = _outcome(layer, refused=True).unsupported
    with pytest.raises(g.InvalidFamilyInput):
        type(refusal).__setattr__(refusal, "__notes__", notes)


@pytest.mark.parametrize("layer", LAYERS)
def test_missing_refusal_notes_deletion_keeps_attribute_error(layer):
    refusal = _outcome(layer, refused=True).unsupported
    with pytest.raises(AttributeError):
        type(refusal).__delattr__(refusal, "__notes__")
