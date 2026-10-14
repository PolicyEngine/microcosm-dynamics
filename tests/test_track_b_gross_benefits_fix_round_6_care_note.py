"""Preserve prior diagnostics when a care history has a settled payment.

Verification class: statutory conformance on invented cases; no population,
behavioral or forecast claim. The existing entitlement function emits notes
only for unentitled rows, so the earlier entitled-row diagnostic is injected
at that boundary to exercise the review's latent note-overwrite finding.
The real benefit computation and all payment rules remain in use.
"""

from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)
CARE_NOTE = (
    "care history does not affect auxiliary payable; "
    "age_adjusted_rate displays the ordinary diagnostic rate "
    "0; the care-exempt rate is 1/10"
)


def _settled_care_row(built, initial):
    pia = F("0.30")
    if built:
        state = g.record_state(
            g.WorkerRecord(g.FamilyKind.RETIREMENT, 2020, pia), PARAMS
        )
    else:
        state = g.RecordState(
            g.FamilyKind.RETIREMENT,
            pia,
            F("0.40"),
            worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
        )
    spouse = g.Beneficiary(
        "d",
        g.Role.DIVORCED_SPOUSE,
        own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F("0.10")),
        own_benefit_first=False,
        reduction_months=1,
        child_in_care=False,
        first_entitlement_child_in_care=initial,
    )
    return g.family_benefits(
        state, [spouse], payment_month=NOW, params=PARAMS, standalone=True
    ).by_id()["d"]


def _row_with_earlier_note(earlier_note, built, initial):
    original = g._is_entitled

    def noted_entitlement(*args, **kwargs):
        entitled, note = original(*args, **kwargs)
        assert entitled and not note
        return entitled, earlier_note

    with patch.object(g, "_is_entitled", noted_entitlement):
        return _settled_care_row(built, initial)


@pytest.mark.parametrize("built", [False, True])
@pytest.mark.parametrize("initial", [None, True])
def test_settled_care_history_appends_to_earlier_note(built, initial):
    row = _row_with_earlier_note(
        "earlier entitlement diagnostic", built, initial
    )
    assert row.note == "earlier entitlement diagnostic; " + CARE_NOTE
    assert row.age_adjusted_rate == row.auxiliary_payable == 0
    assert row.own_benefit == F("0.10")


@settings(max_examples=60, deadline=None, derandomize=True)
@example(earlier_note="", built=False, initial=None)
@given(
    earlier_note=st.text(max_size=80),
    built=st.booleans(),
    initial=st.one_of(st.none(), st.just(True)),
)
def test_property_care_diagnostic_preserves_prior_note_and_payment(
    earlier_note, built, initial
):
    baseline = _settled_care_row(built, initial)
    row = _row_with_earlier_note(earlier_note, built, initial)
    assert row.note == (
        (earlier_note + "; " if earlier_note else "") + CARE_NOTE
    )
    assert replace(row, note=baseline.note) == baseline
