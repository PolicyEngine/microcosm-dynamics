"""Boundary invariants; statutory conformance on invented cases only."""

import copyreg
import pickle
from decimal import Decimal
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.test_track_b_gross_benefits_fix_round_11_seals import _outputs
from tests.test_track_b_gross_benefits_fix_round_12_contract import (
    COMPUTE,
    LAYERS,
    _outcome,
)


class MutableFraction(F):
    def __new__(cls, value):
        obj = super().__new__(cls, value)
        obj.value = F(value)
        return obj

    def __radd__(self, other):
        return other + self.value

    def __mul__(self, other):
        return self.value * other


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("refused", (False, True))
@settings(max_examples=8, deadline=None, derandomize=True)
@given(st.integers(0, 100))
def test_mutable_weight_cannot_change_denominator_or_aggregate(
    layer, refused, n
):
    weight = MutableFraction(n)
    try:
        row = _outcome(layer, refused=refused, weight=weight)
    except g.InvalidFamilyInput:
        return
    assert type(row.weight) is F
    before = g.count_family_outcomes([row])
    total = (
        g.weighted_record_total([row])
        if layer == "g" and not refused
        else None
    )
    weight.value = F(n + 100)
    assert g.count_family_outcomes([row]) == before
    if total is not None:
        assert g.weighted_record_total([row]) == total


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize(
    "kind", ("result", "outcome", "refusal", "denominator")
)
@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_sealed_values_reject_every_pickle_protocol(layer, kind, protocol):
    row = _outcome(layer)
    value = {
        "result": COMPUTE[layer](),
        "outcome": row,
        "refusal": _outcome(layer, refused=True).unsupported,
        "denominator": g.count_family_outcomes([row]),
    }[kind]
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(value, protocol=protocol)


@pytest.mark.parametrize("index", range(6))
@pytest.mark.parametrize("operation", ("reduce", "reduce_ex", "copyreg"))
def test_sealed_values_reject_public_reduction_paths(index, operation):
    value = _outputs()[index]
    with pytest.raises(g.InvalidFamilyInput):
        if operation == "reduce":
            value.__reduce__()
        elif operation == "reduce_ex":
            value.__reduce_ex__(0)
        else:
            copyreg._reduce_ex(value, 0)


@pytest.mark.parametrize("base", (int, F, Decimal))
@pytest.mark.parametrize("entry", (g.floor_dime, g.ceil_dime, g.whole_dollars))
@given(st.integers(0, 1000))
def test_numeric_subclasses_are_canonical_or_rejected(base, entry, n):
    subclass = type("MutableNumber", (base,), {})
    value = subclass(n)
    value.public = n
    try:
        result = entry(value)
    except g.InvalidFamilyInput:
        return
    assert type(result) in (F, int)
    value.public = n + 100
    assert result == entry(n)


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("refused", (False, True))
@settings(max_examples=8, deadline=None, derandomize=True)
@given(st.integers(0, 100))
def test_builtin_fraction_inputs_are_detached_before_admission(
    layer, refused, n
):
    weight = F(n, 7)
    row = _outcome(layer, refused=refused, weight=weight)
    expected = g.count_family_outcomes([row])
    object.__setattr__(weight, "_numerator", n + 100)
    assert g.count_family_outcomes([row]) == expected


@pytest.mark.parametrize("layer", LAYERS)
def test_uninitialized_refusal_is_an_input_error(layer):
    cls = type(_outcome(layer, refused=True).unsupported)
    refusal = cls.__new__(cls)

    def refuse():
        raise refusal

    with pytest.raises(g.InvalidFamilyInput):
        g.evaluate_family("uninitialized-refusal", 1, refuse)


def test_builtin_fraction_weight_snapshot_survives_original_mutation():
    weight = F(1, 3)
    row = _outcome("g", weight=weight)
    expected = g.count_family_outcomes([row])
    object.__setattr__(weight, "_numerator", 7)
    assert g.count_family_outcomes([row]) == expected


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("refused", (False, True))
@settings(max_examples=8, deadline=None, derandomize=True)
@given(st.integers(0, 100))
@example(1)
def test_seal_binds_the_declared_outcome_class(layer, refused, numerator):
    for other in LAYERS:
        if other == layer:
            continue
        row = _outcome(layer, refused=refused, weight=F(numerator, 7))
        other_class = type(_outcome(other, refused=refused))
        object.__setattr__(row, "__class__", other_class)
        with pytest.raises(g.InvalidFamilyInput):
            g.count_family_outcomes([row])
        with pytest.raises(g.InvalidFamilyInput):
            _ = row.supported
