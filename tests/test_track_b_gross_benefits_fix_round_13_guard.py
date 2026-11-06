"""Guard regressions: statutory conformance on invented cases only.

No population, behavioral or forecast claim. Public snapshots and caller
objects cannot change the guard's later continuity or monetary decisions.
"""

import copyreg
import pickle
from collections.abc import Mapping
from copy import copy, deepcopy
from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests import test_track_b_gross_benefits_properties as properties
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()


def _family(month, pia=None, children=2):
    if pia is None:
        pia = F("1.10")
    return g.family_benefits(
        g.RecordState(
            g.FamilyKind.RETIREMENT,
            pia,
            F("1.90"),
            g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
        ),
        [g.Beneficiary(str(i), g.Role.CHILD) for i in range(children)],
        payment_month=g.YearMonth(2026, month),
        params=PARAMS,
        standalone=True,
    )


def _snapshot(guard):
    return (
        guard.next_month,
        guard.protected_total,
        guard.protected_since,
        guard.refused_since,
        guard.unknown_since,
    )


def _decision(guard, result):
    outcome = guard.evaluate("month", F(7, 3), lambda: result)
    if outcome.supported:
        return True, outcome.benefits.record_total
    return False, outcome.unsupported.reason, outcome.unsupported.detail


@pytest.mark.parametrize(
    "entry",
    (
        "next_month",
        "protected_total",
        "protected_since",
        "refused_since",
        "unknown_since",
        "admit",
        "skip",
        "evaluate",
    ),
)
def test_guard_rejects_uninitialized_instances_at_every_public_entry(entry):
    guard = object.__new__(g.SavingsClauseGuard)
    with pytest.raises(g.InvalidFamilyInput):
        if entry == "admit":
            guard.admit(_family(1))
        elif entry == "skip":
            guard.skip(g.YearMonth(2026, 1), pia=F("1.10"))
        elif entry == "evaluate":
            guard.evaluate("January", 1, lambda: _family(1))
        else:
            getattr(guard, entry)


@pytest.mark.parametrize("populated", (False, True))
@pytest.mark.parametrize(
    "operation",
    ("copy", "deepcopy", "copyreg", *range(pickle.HIGHEST_PROTOCOL + 1)),
)
def test_guard_denies_copy_and_serialization(operation, populated):
    guard = g.SavingsClauseGuard(
        g.YearMonth(2026, 1),
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    if populated:
        guard.admit(_family(1))
    with pytest.raises(g.InvalidFamilyInput):
        if isinstance(operation, int):
            pickle.dumps(guard, protocol=operation)
        elif operation == "copyreg":
            copyreg._reduce_ex(guard, 0)
        else:
            {"copy": copy, "deepcopy": deepcopy}[operation](guard)


def test_guard_rejects_undeclared_subclasses():
    class OtherGuard(g.SavingsClauseGuard):
        pass

    with pytest.raises(g.InvalidFamilyInput):
        OtherGuard(g.YearMonth(2026, 1), earlier_months_unknown=False)


def test_review_next_month_mutation_cannot_skip_qualifying_february():
    guard = g.SavingsClauseGuard(
        g.YearMonth(2026, 1),
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    january, february, march = (
        _family(1, children=1),
        _family(2),
        _family(3, F("1.20")),
    )
    assert january.record_total == F("1.60")
    assert not january.family_maximum_binding
    assert february.record_total == F("1.90")
    assert february.family_maximum_binding
    assert march.record_total == F("1.80")
    guard.admit(january)
    object.__setattr__(guard.next_month, "month", 3)
    assert guard.next_month == g.YearMonth(2026, 2)
    with pytest.raises(g.InvalidFamilyInput):
        guard.evaluate("March too soon", 1, lambda: march)
    guard.admit(february)
    outcome = guard.evaluate("March", 1, lambda: march)
    assert outcome.unsupported.reason is g.UnsupportedReason.SAVINGS_CLAUSE
    assert guard.protected_total == F("1.90")
    assert g.count_family_outcomes([outcome]).unsupported_rows == 1
    skipped = g.SavingsClauseGuard(
        g.YearMonth(2026, 1),
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    skipped.admit(january)
    skipped.skip(g.YearMonth(2026, 2), pia=F("1.10"))
    outcome = skipped.evaluate("March after skip", 1, lambda: march)
    assert outcome.unsupported.reason is (
        g.UnsupportedReason.SAVINGS_CLAUSE_HISTORY_UNKNOWN
    )
    assert g.count_family_outcomes([outcome]).unsupported_rows == 1


@settings(max_examples=30, deadline=None, derandomize=True)
@given(
    st.sampled_from(
        [
            "next_month",
            "protected_total",
            "protected_since",
            "refused_since",
            "unknown_since",
        ]
    ),
    st.integers(4, 12),
)
def test_guard_every_public_snapshot_is_detached(accessor, changed_month):
    guards = [
        g.SavingsClauseGuard(
            g.YearMonth(2026, 1),
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        )
        for _ in range(2)
    ]
    for guard in guards:
        if accessor == "unknown_since":
            guard.skip(g.YearMonth(2026, 1), pia=F("1.10"))
        else:
            guard.admit(_family(1))
        _decision(guard, _family(2, F("1.20")))
    exposed = getattr(guards[0], accessor)
    assert exposed is not None
    if accessor == "protected_total":
        object.__setattr__(exposed, "_numerator", changed_month)
    else:
        object.__setattr__(exposed, "month", changed_month)
    assert _snapshot(guards[0]) == _snapshot(guards[1])
    assert _decision(guards[0], _family(3, F("1.20"))) == _decision(
        guards[1], _family(3, F("1.20"))
    )
    assert _snapshot(guards[0]) == _snapshot(guards[1])


@settings(max_examples=40, deadline=None, derandomize=True)
@given(
    st.sampled_from(
        [
            "constructor_month",
            "admit_month",
            "admit_pia",
            "admit_child",
            "skip_month",
            "skip_pia",
            "evaluate_result",
            "evaluate_pia",
        ]
    ),
    st.integers(4, 12),
)
def test_guard_admitted_objects_cannot_change_later_decisions(
    surface, changed_value
):
    first_month = g.YearMonth(2026, 1)
    guards = [
        g.SavingsClauseGuard(
            first_month,
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        ),
        g.SavingsClauseGuard(
            g.YearMonth(2026, 1),
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        ),
    ]
    january = _family(1)
    if surface.startswith("skip"):
        month, pia = g.YearMonth(2026, 1), F("1.10")
        guards[0].skip(month, pia=pia)
        guards[1].skip(g.YearMonth(2026, 1), pia=F("1.10"))
        changed = month if surface == "skip_month" else pia
        field = "month" if surface == "skip_month" else "_numerator"
    else:
        pia = F("1.10")
        if surface.startswith("evaluate"):
            outcome = guards[0].evaluate(
                "January", 1, lambda: january, pia=pia
            )
            guards[1].evaluate("January", 1, lambda: _family(1), pia=F("1.10"))
        else:
            guards[0].admit(january)
            guards[1].admit(_family(1))
        changed, field = {
            "constructor_month": (first_month, "month"),
            "admit_month": (january.payment_month, "month"),
            "admit_pia": (january.pia, "_numerator"),
            "admit_child": (january.beneficiaries[0], "age_adjusted_rate"),
            "evaluate_result": (
                outcome.benefits if surface == "evaluate_result" else None,
                "pia",
            ),
            "evaluate_pia": (pia, "_numerator"),
        }[surface]
    object.__setattr__(changed, field, changed_value)
    assert _snapshot(guards[0]) == _snapshot(guards[1])
    assert _decision(guards[0], _family(2, F("1.20"))) == _decision(
        guards[1], _family(2, F("1.20"))
    )
    assert _snapshot(guards[0]) == _snapshot(guards[1])


def test_review_live_fraction_cannot_change_qualifying_pia_increase():
    class LiveFraction(F):
        def __lt__(self, other):
            return self.value < other

        def __gt__(self, other):
            return self.value > other

    control = g.SavingsClauseGuard(
        g.YearMonth(2026, 1),
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    control.admit(_family(1))
    assert _decision(control, _family(2, F("1.20")))[1] is (
        g.UnsupportedReason.SAVINGS_CLAUSE
    )
    pia = LiveFraction("1.10")
    pia.value = F("1.10")
    try:
        january = _family(1, pia)
    except g.InvalidFamilyInput:
        return  # Numeric subclasses may be rejected at the first boundary.
    guard = g.SavingsClauseGuard(
        g.YearMonth(2026, 1),
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    guard.admit(january)
    pia.value = F("1.30")
    assert _decision(guard, _family(2, F("1.20")))[1] is (
        g.UnsupportedReason.SAVINGS_CLAUSE
    )
    assert guard.protected_total == F("1.90")


@settings(max_examples=25, deadline=None, derandomize=True)
@example(1, -1)
@given(st.integers(1, 100), st.sampled_from((0, -1, 1000)))
def test_guard_detaches_weight_before_calling_computation(numerator, changed):
    weight = F(numerator, 3)
    guard = g.SavingsClauseGuard(
        g.YearMonth(2026, 1),
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )

    def compute():
        object.__setattr__(weight, "_numerator", changed)
        return _family(1)

    outcome = guard.evaluate("January", weight, compute)
    assert outcome.supported
    assert outcome.weight == F(numerator, 3)
    assert g.count_family_outcomes([outcome]).supported_weight == F(
        numerator, 3
    )
    assert guard.next_month == g.YearMonth(2026, 2)


class _FixedDraws:
    """Replay the reviewer's exact draws through the property itself."""

    def __init__(self, members):
        self.values = iter([len(members), *members])

    def draw(self, strategy):
        return next(self.values)


@pytest.mark.parametrize("witness", ("widows", "parent"))
def test_review_formula_cola_rounded_decline_exercises_property(witness):
    if witness == "widows":
        year, pia, colas, tenths = 2026, F("4.40"), [], 23
        members = [
            g.Beneficiary(
                f"b{i}",
                g.Role.WIDOW,
                birth_year=1935,
                reduction_period_months=60,
                child_in_care=False,
            )
            for i in range(2)
        ] + [g.Beneficiary("b2", g.Role.MOTHER_FATHER)]
        expected = (
            (F("4.40"), F("6.60"), [F("2.40"), F("2.40"), F("1.80")]),
            (F("4.50"), F("6.70"), [F("2.40"), F("2.40"), F("1.70")]),
        )
    else:
        year, pia, colas, tenths = 2025, F("17.10"), [F("6.5")], 6
        members = [g.Beneficiary("b0", g.Role.PARENT)] + [
            g.Beneficiary(f"b{i}", g.Role.CHILD) for i in range(1, 4)
        ]
        expected = (
            (F("18.20"), F("27.20"), [F("7.30"), *[F("6.60")] * 3]),
            (F("18.30"), F("27.30"), [F("7.20"), *[F("6.60")] * 3]),
        )
    for index, increases in enumerate((colas, [*colas, F(tenths, 10)])):
        state = replace(
            g.record_state(
                g.WorkerRecord(
                    g.FamilyKind.SURVIVOR, year, pia, cola_percents=increases
                ),
                PARAMS,
            ),
            widow_drc_savings_clause=False,
        )
        result = g.family_benefits(
            state,
            members,
            payment_month=g.YearMonth(2026, 11 + index),
            params=PARAMS,
            standalone=True,
        )
        expected_pia, maximum, rates = expected[index]
        assert result.pia == expected_pia
        assert result.family_maximum == maximum
        assert [b.age_adjusted_rate for b in result.beneficiaries] == rates
        assert g.savings_clause_total(result) == sum(rates)
        if witness == "widows":
            original = [expected_pia, expected_pia, F("3.30")]
            assert result.record_total_whole_dollars == 5
        else:
            child_original = F("13.60") if index == 0 else F("13.70")
            original = [F("15.00"), *[child_original] * 3]
            assert result.record_total_whole_dollars == 25
        assert [b.original_benefit for b in result.beneficiaries] == original
    properties.test_formula_maximum_colas_preserve_available_room_and_guard_contract.hypothesis.inner_test(
        g.FamilyKind.SURVIVOR,
        year,
        pia,
        colas,
        tenths,
        _FixedDraws(members),
    )


def test_cyclic_declared_number_is_input_error():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, 1)
    object.__setattr__(own, "pia", own)
    with pytest.raises(g.InvalidFamilyInput):
        g.own_monthly_benefit(own, PARAMS)


def test_cyclic_cola_collection_is_input_error():
    colas = []
    colas.append(colas)
    with pytest.raises(g.InvalidFamilyInput):
        g.increase_by_colas(1, colas)


def test_cyclic_denominator_state_is_input_error():
    denominator = g.count_family_outcomes([])
    object.__setattr__(denominator, "unsupported_by_reason", denominator)
    with pytest.raises(g.InvalidFamilyInput):
        _ = denominator.supported_weight_share


@pytest.mark.parametrize("layer", ("ret", "arf", "recompute"))
def test_cyclic_r2_r3_declarations_are_input_errors_before_refusal(layer):
    from populace_dynamics.track_b import arf as a
    from populace_dynamics.track_b import ret_ledger as r
    from tests.test_track_b_r3_fix_round_13 import basis, claim, recompute
    from tests.test_track_b_ret_ledger import PARAMS as RET_PARAMS
    from tests.test_track_b_ret_ledger import record

    with pytest.raises(g.InvalidFamilyInput):
        if layer == "ret":
            value = record(foreign_work=True)
            object.__setattr__(value, "beneficiaries", value)
            r.apply_ret_year(value, RET_PARAMS)
        elif layer == "arf":
            value = claim()
            object.__setattr__(value, "unreduced_benefit", value)
            a.apply_arf(
                value, payment_month=g.YearMonth(2027, 1), params=PARAMS
            )
        else:
            value = basis()
            object.__setattr__(value, "eligibility_year", value)
            recompute(value)


@pytest.mark.parametrize("layer", ("g", "ret", "arf", "recompute"))
def test_cyclic_sealed_rows_are_input_errors_in_every_layer(layer):
    from populace_dynamics.track_b import arf as a
    from populace_dynamics.track_b import recompute as c
    from populace_dynamics.track_b import ret_ledger as r
    from tests.test_track_b_r3_provenance import (
        arf_result,
        recomputation_result,
    )
    from tests.test_track_b_ret_ledger import ledger

    evaluator, factory = {
        "g": (g.evaluate_family, lambda: _family(1)),
        "ret": (r.evaluate_ret, ledger),
        "arf": (a.evaluate_arf, arf_result),
        "recompute": (c.evaluate_recomputation, recomputation_result),
    }[layer]
    row = evaluator("cyclic", 1, factory)
    object.__setattr__(row, "weight", row)
    with pytest.raises(g.InvalidFamilyInput):
        g.count_family_outcomes([row])


def test_malformed_mapping_traversal_is_input_error():
    from populace_dynamics.track_b import recompute as c
    from tests.test_track_b_r3_fix_round_13 import basis

    class UnhashableItems(Mapping):
        def __len__(self):
            return 1

        def __iter__(self):
            return iter(())

        def __getitem__(self, key):
            raise KeyError(key)

        def items(self):
            return (([], 1),)

    with pytest.raises(g.InvalidFamilyInput):
        c.annual_recomputation(
            basis(), UnhashableItems(), 2020, 0, PARAMS, {2020: 0}
        )


def test_callback_recursion_error_remains_a_programming_error():
    def compute():
        raise RecursionError("callback programming error")

    with pytest.raises(RecursionError, match="callback programming error"):
        g.evaluate_family("callback", 1, compute)
