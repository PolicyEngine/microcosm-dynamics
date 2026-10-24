"""Outcome envelopes validate before computation or any guard advancement.

Verification class: statutory conformance. Invented cases only; no population,
behavioral or forecast claim. Malformed calls never enter a denominator.
"""

from copy import deepcopy
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import computed_refusal, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2023, 12)
WEIGHT = F(7, 3)


def _records():
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(1000),
        F(1500),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000)),
    )
    return {"record": g.HouseholdRecord("worker", state)}


def _benefits():
    return g.family_benefits(
        _records()["record"].state,
        (),
        payment_month=NOW,
        params=PARAMS,
        standalone=True,
    )


def _guard():
    return g.SavingsClauseGuard(
        NOW,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )


@pytest.mark.parametrize("guarded", (False, True))
@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("key", ""),
        ("key", True),
        ("key", []),
        ("weight", True),
        ("weight", F(-1)),
        ("weight", float("nan")),
        ("weight", object()),
    ),
)
def test_outcome_metadata_is_invalid_before_compute(guarded, field, invalid):
    guard = _guard()
    original = deepcopy(vars(guard))
    calls = []
    outcomes = []

    def compute():
        calls.append("called")
        raise computed_refusal(g.UnsupportedReason.ADMINISTRATIVE_FINALITY)

    fields = {"key": "family", "weight": WEIGHT, "compute": compute}
    fields[field] = invalid
    evaluate = guard.evaluate if guarded else g.evaluate_family
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(evaluate(**fields))
    assert calls == []
    assert outcomes == []
    assert g.count_family_outcomes(outcomes).rows == 0
    assert vars(guard) == original


@pytest.mark.parametrize("guarded", (False, True))
@pytest.mark.parametrize("compute", (None, 1, "compute"))
def test_outcome_callable_is_validated_before_computation(guarded, compute):
    guard = _guard()
    original = deepcopy(vars(guard))
    evaluate = guard.evaluate if guarded else g.evaluate_family
    with pytest.raises(g.InvalidFamilyInput):
        evaluate("family", WEIGHT, compute)
    assert vars(guard) == original


@pytest.mark.parametrize("pia", (True, F(-1), F(1, 100)))
def test_guard_pia_is_validated_before_compute(pia):
    guard = _guard()
    original = deepcopy(vars(guard))
    calls = []

    def compute():
        calls.append("called")
        return _benefits()

    with pytest.raises(g.InvalidFamilyInput):
        guard.evaluate("family", WEIGHT, compute, pia=pia)
    assert calls == []
    assert vars(guard) == original


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("key", ""),
        ("key", 1),
        ("weight", True),
        ("weight", F(-1)),
        ("weight", float("inf")),
    ),
)
def test_household_outcome_metadata_leaves_every_guard_unchanged(
    field, invalid
):
    guards = {"record": _guard()}
    original = deepcopy(vars(guards["record"]))
    fields = {"key": "household", "weight": WEIGHT}
    fields[field] = invalid
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(
            g.household_month_outcome(
                _records(),
                payment_month=NOW,
                params=PARAMS,
                guards=guards,
                **fields,
            )
        )
    assert outcomes == []
    assert g.count_family_outcomes(outcomes).unsupported_weight == 0
    assert vars(guards["record"]) == original


@pytest.mark.parametrize("record_id", ("", 1, True, None))
@pytest.mark.parametrize("guarded", (False, True))
def test_household_mapping_keys_are_nonempty_strings(record_id, guarded):
    record = _records()["record"]
    guard = _guard()
    original = deepcopy(vars(guard))
    records = {record_id: record}
    with pytest.raises(g.InvalidFamilyInput):
        if guarded:
            g.household_month_outcome(
                records,
                payment_month=NOW,
                params=PARAMS,
                guards={record_id: guard},
                weight=WEIGHT,
            )
        else:
            g.household_benefits(records, payment_month=NOW, params=PARAMS)
    assert vars(guard) == original


@pytest.mark.parametrize(
    "guards", (None, [], [("record", None)], {"record": None})
)
def test_guard_mapping_and_members_are_validated(guards):
    with pytest.raises(g.InvalidFamilyInput):
        g.household_month_outcome(
            _records(),
            payment_month=NOW,
            params=PARAMS,
            guards=guards,
            weight=WEIGHT,
        )


@pytest.mark.parametrize(
    "records", (None, [], [("record", None)], {"record": None})
)
@pytest.mark.parametrize("guarded", (False, True))
def test_household_mapping_and_members_are_validated(records, guarded):
    guard = _guard()
    original = deepcopy(vars(guard))
    with pytest.raises(g.InvalidFamilyInput):
        if guarded:
            g.household_month_outcome(
                records,
                payment_month=NOW,
                params=PARAMS,
                guards={"record": guard},
                weight=WEIGHT,
            )
        else:
            g.household_benefits(records, payment_month=NOW, params=PARAMS)
    assert vars(guard) == original


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    st.one_of(
        st.tuples(
            st.just("key"),
            st.one_of(st.just(""), st.integers(), st.lists(st.integers())),
        ),
        st.tuples(
            st.just("weight"),
            st.one_of(
                st.booleans(),
                st.fractions(max_value=F(-1, 1000)),
                st.sampled_from((float("nan"), float("inf"), None)),
            ),
        ),
    )
)
def test_property_malformed_outcomes_never_compute_count_or_advance(case):
    field, invalid = case
    for guarded in (False, True):
        guard = _guard()
        original = deepcopy(vars(guard))
        calls = []
        outcomes = []

        def compute(calls=calls):
            calls.append("called")
            raise computed_refusal(g.UnsupportedReason.ADMINISTRATIVE_FINALITY)

        fields = {"key": "family", "weight": WEIGHT, "compute": compute}
        fields[field] = invalid
        evaluate = guard.evaluate if guarded else g.evaluate_family
        with pytest.raises(g.InvalidFamilyInput):
            outcomes.append(evaluate(**fields))
        assert calls == []
        counts = g.count_family_outcomes(outcomes)
        assert counts.rows == counts.unsupported_rows == 0
        assert counts.weight == counts.unsupported_weight == 0
        assert vars(guard) == original


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("key", ""),
        ("key", 1),
        ("weight", True),
        ("weight", F(-1)),
        ("benefits", object()),
        ("unsupported", object()),
        ("unsupported", g.InvalidFamilyInput("not a coverage refusal")),
    ),
)
def test_family_outcome_validates_all_public_field_types(field, invalid):
    fields = {
        "key": "family",
        "weight": WEIGHT,
        "benefits": _benefits(),
        "unsupported": None,
    }
    if field == "unsupported":
        fields["benefits"] = None
    fields[field] = invalid
    with pytest.raises(g.InvalidFamilyInput):
        g.FamilyOutcome(**fields)


@pytest.mark.parametrize("both", (False, True))
def test_family_outcome_requires_exactly_one_result_or_refusal(both):
    with pytest.raises(g.InvalidFamilyInput):
        g.FamilyOutcome(
            "family",
            WEIGHT,
            _benefits() if both else None,
            (
                computed_refusal(g.UnsupportedReason.ADMINISTRATIVE_FINALITY)
                if both
                else None
            ),
        )
