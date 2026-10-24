"""Public parameter surfaces reject malformed bundles before coverage.

Verification class: statutory conformance. Invented bundles and families
only; no population, behavioral or forecast claim. A malformed consumed
parameter yields no outcome or denominator entry and leaves guard history
unchanged, including at otherwise unsupported statutory boundaries.
"""

from copy import deepcopy
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

MONTH = g.YearMonth(2023, 12)
WEIGHT = Fraction(7, 3)


def _valid_result(month=MONTH):
    return g.family_benefits(
        g.RecordState(
            g.FamilyKind.SURVIVOR,
            Fraction(1000),
            Fraction(1750),
            widow_drc_savings_clause=False,
        ),
        [],
        payment_month=month,
        params=ssa_params(),
        standalone=True,
    )


def _helper(field, bad_value, *, birth_year=1940):
    params = ssa_params(**{field: bad_value})
    if field == "nawi":
        return g.retirement_survivor_family_maximum(1000, 1982, params)
    return g.worker_age_adjusted(1000, 0, 1, birth_year, params)


def _assert_atomic_rejection(field, bad_value, *, birth_year=1940):
    guard = g.SavingsClauseGuard(
        MONTH,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    before = deepcopy(vars(guard))
    outcomes = []

    def compute():
        _helper(field, bad_value, birth_year=birth_year)
        return _valid_result()

    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(guard.evaluate("bad-parameters", WEIGHT, compute))
    assert vars(guard) == before
    assert outcomes == []
    denominator = g.count_family_outcomes(outcomes)
    assert denominator.rows == 0
    assert denominator.weight == 0
    assert denominator.unsupported_rows == 0
    assert denominator.unsupported_weight == 0


@pytest.mark.parametrize(
    "field,bad_value,birth_year",
    [
        pytest.param("nawi", None, 1940, id="nawi-before-1983-refusal"),
        pytest.param(
            "delayed_credit_by_birth_year",
            None,
            1940,
            id="null-drc-schedule",
        ),
        pytest.param(
            "delayed_credit_by_birth_year",
            [(1900, -0.01)],
            1940,
            id="negative-drc-rate",
        ),
        pytest.param(
            "delayed_credit_by_birth_year",
            [(True, 0.08)],
            1940,
            id="boolean-drc-year",
        ),
        pytest.param(
            "delayed_credit_by_birth_year",
            None,
            1915,
            id="drc-before-1917-refusal",
        ),
    ],
)
def test_malformed_parameters_cannot_become_outcomes_or_advance_guard(
    field, bad_value, birth_year
):
    _assert_atomic_rejection(field, bad_value, birth_year=birth_year)


@st.composite
def _corrupted_parameter_fields(draw):
    field = draw(st.sampled_from(["nawi", "delayed_credit_by_birth_year"]))
    mutation = draw(st.sampled_from(["shape", "key", "value", "entry"]))
    bad_year = st.one_of(
        st.booleans(),
        st.integers(max_value=0),
        st.integers(min_value=10000),
        st.sampled_from(["1900", None, 1900.5]),
    )
    bad_amount = st.one_of(
        st.booleans(),
        st.integers(max_value=-1),
        st.sampled_from([None, float("nan"), float("inf"), "not-a-rate"]),
    )
    if field == "nawi":
        value = dict(ssa_params().nawi)
        if mutation == "shape":
            value = draw(st.sampled_from([None, 1, "nawi", []]))
        elif mutation == "key":
            amount = value.pop(1977)
            value[draw(bad_year)] = amount
        else:
            value[1977] = draw(bad_amount)
    else:
        value = list(ssa_params().delayed_credit_by_birth_year)
        if mutation == "shape":
            value = draw(st.sampled_from([None, 1, "drc", {}]))
        elif mutation == "key":
            value[0] = (draw(bad_year), value[0][1])
        elif mutation == "value":
            value[0] = (value[0][0], draw(bad_amount))
        else:
            value[0] = draw(st.sampled_from([None, (1900,), (1900, 0.03, 1)]))
    return field, value


@given(_corrupted_parameter_fields())
@settings(max_examples=150, deadline=None)
def test_parameter_field_corruption_preserves_guard_and_denominator(case):
    _assert_atomic_rejection(*case)


def test_guard_admit_preserves_identity_but_stores_validated_history():
    first = _valid_result()
    guard = g.SavingsClauseGuard(
        MONTH,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    # Numeric strings remain valid inputs, but changing even an equivalent
    # field on a computed result violates its round-11 provenance seal.
    before = vars(guard).copy()
    object.__setattr__(first, "pia", "1000")
    with pytest.raises(g.InvalidFamilyInput):
        guard.admit(first)
    assert vars(guard) == before
    first = _valid_result()
    assert guard.admit(first) is first
    object.__setattr__(first, "beneficiaries", None)
    outcome = guard.evaluate(
        "next", WEIGHT, lambda: _valid_result(g.YearMonth(2024, 1))
    )
    assert outcome.supported
    assert guard.next_month == g.YearMonth(2024, 2)
