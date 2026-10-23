"""Statutory conformance: boundary work on invented R2/R3 inputs only."""

from collections import Counter
from contextlib import ExitStack
from fractions import Fraction
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import (
    _provenance,
    arf,
    recompute,
    ret_grace,
    ret_ledger,
)
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.test_track_b_arf import FRA, rib_claim
from tests.test_track_b_recompute import basis, explicit_early_zeros
from tests.test_track_b_ret_grace import month
from tests.test_track_b_ret_ledger import beneficiary, earnings, record
from tests.track_b_gross_benefit_support import ssa_params


@settings(deadline=None, max_examples=10)
@given(st.integers(0, 100_000), st.integers(1, 3))
def test_r2_r3_snapshot_each_parameter_bundle_once_per_public_call(
    amount, year_count
):
    """Private arithmetic/construction must not repeat public schema walks."""
    ssa = ssa_params(wage_base={1951: 1_000_000})
    ret = load_ret_parameters()
    claim = rib_claim(unreduced_benefit=Fraction(amount, 10))
    original = basis()
    years = list(range(2020, 2020 + year_count))
    history = explicit_early_zeros(
        {year: amount for year in range(2018, years[-1] + 1)}
    )
    colas = {year: 0 for year in years}
    declared_record = record(beneficiary(work=earnings(amount)))
    grace_state = ret_grace.GraceYearState()
    grace_months = [month()] * 12
    # This fallback lets the same regression expose the reviewed head's
    # repeated snapshots without importing a new implementation helper.
    snapshot_name = (
        "_snapshot_declaration"
        if hasattr(_provenance, "_snapshot_declaration")
        else "_rebuild_declared"
    )
    original_snapshot = getattr(_provenance, snapshot_name)
    counts = Counter()
    constructor_counts = Counter()
    internal_constructor_calls = {}

    def snapshot(value):
        counts[type(value)] += 1
        return original_snapshot(value)

    def observe_constructor(initialize):
        def observed(self, *args, **kwargs):
            constructor_counts[type(self)] += 1
            initialize(self, *args, **kwargs)

        return observed

    calls = (
        (
            "R2",
            lambda: ret_ledger.apply_ret_year(declared_record, ret),
            type(ret),
        ),
        (
            "ARF",
            lambda: arf.apply_arf(claim, payment_month=FRA, params=ssa),
            type(ssa),
        ),
        (
            "recomputation",
            lambda: recompute.recompute_sequence(
                original, history, years, 0, ssa, colas
            ),
            type(ssa),
        ),
        (
            "grace",
            lambda: ret_grace.grace_year(2020, grace_state, grace_months),
            None,
        ),
    )
    for layer, invoke, parameter_type in calls:
        counts.clear()
        constructor_counts.clear()
        with ExitStack() as spies:
            spies.enter_context(
                patch.object(_provenance, snapshot_name, side_effect=snapshot)
            )
            for declared_type in _provenance._DECLARATION_TYPES:
                spies.enter_context(
                    patch.object(
                        declared_type,
                        "__init__",
                        observe_constructor(declared_type.__init__),
                    )
                )
            invoke()
        if parameter_type is not None:
            assert counts[parameter_type] == 1, (layer, counts)
        assert counts[ret_ledger.RecordYear] <= 1, (layer, counts)
        assert counts[ret_ledger.WorkEarnings] <= 1, (layer, counts)
        if constructor_counts:
            internal_constructor_calls[layer] = dict(constructor_counts)
    assert not internal_constructor_calls, internal_constructor_calls
