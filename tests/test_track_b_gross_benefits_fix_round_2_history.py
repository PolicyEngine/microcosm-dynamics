"""G round-2 regressions for unknown May 1978 survivor protection.

Verification class: statutory conformance. Invented families and captured
POMS rules admit no population, behavioral or forecast claim.
Built/direct snapshot differentials use exact Fractions, with zero tolerance.
"""

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)
UNKNOWN = g.UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN


def _state(prebuilt, year=1983, first_dib=None):
    built = g.record_state(
        g.WorkerRecord(
            g.FamilyKind.SURVIVOR,
            year,
            F(400),
            first_dib_entitlement=first_dib,
        ),
        PARAMS,
    )
    if not prebuilt:
        return built
    return g.RecordState(
        g.FamilyKind.SURVIVOR,
        built.pia,
        built.family_maximum,
        eligibility_year=year,
        first_dib_entitlement=first_dib,
    )


def _members():
    # Isolate the history guard: this widow does not have the child in care.
    return (
        g.Beneficiary(
            "w",
            g.Role.WIDOW,
            original_benefit_basis=F(410),
            child_in_care=False,
        ),
        g.Beneficiary("c", g.Role.CHILD),
    )


def _family(state, members=None):
    return g.family_benefits(
        state,
        _members() if members is None else members,
        payment_month=NOW,
        params=PARAMS,
        standalone=True,
    )


@pytest.mark.parametrize("prebuilt", [False, True])
def test_review_unknown_prior_dib_at_first_modern_eligibility_refuses(
    prebuilt,
):
    state = _state(prebuilt)
    assert state.first_dib_entitlement is None
    assert state.widow_drc_savings_clause is None
    assert state.family_maximum == F("692.70")
    with pytest.raises(g.FamilyConfigurationUnsupported) as exc:
        _family(state)
    assert exc.value.reason is UNKNOWN


@pytest.mark.parametrize("maximum", [F(700), F("704.20")])
def test_review_modern_direct_unknown_prior_dib_refuses_published_case(
    maximum,
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(400),
        maximum,
        eligibility_year=1983,
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as exc:
        _family(state)
    assert exc.value.reason is UNKNOWN


@pytest.mark.parametrize("prebuilt", [False, True])
def test_review_unknown_prior_dib_explicit_no_protection_retains_ordinary_rates(
    prebuilt,
):
    result = _family(replace(_state(prebuilt), widow_drc_savings_clause=False))
    assert result.by_id()["w"].auxiliary_payable == F(400)
    assert result.by_id()["c"].auxiliary_payable == F("292.60")
    assert result.record_total == F("692.60")
    assert result.record_total_whole_dollars == 692


@pytest.mark.parametrize("prebuilt", [False, True])
@pytest.mark.parametrize("month", [g.YearMonth(1978, 6), g.YearMonth(1983, 1)])
def test_review_known_first_ever_dib_after_protected_month_excludes_protection(
    prebuilt, month
):
    result = _family(_state(prebuilt, first_dib=month))
    assert result.record_total == F("692.60")


@pytest.mark.parametrize("prebuilt", [False, True])
def test_review_unknown_prior_dib_keeps_row_and_weight_and_blocks_totals(
    prebuilt,
):
    outcomes = [
        g.evaluate_family(
            "unknown", F(7, 2), lambda: _family(_state(prebuilt))
        )
    ]
    counts = g.count_family_outcomes(outcomes)
    assert (counts.rows, counts.weight) == (1, F(7, 2))
    assert counts.unsupported_by_reason == {UNKNOWN: (1, F(7, 2))}
    for aggregate in (g.weighted_record_total, g.weighted_mean_record_total):
        with pytest.raises(g.FamilyTargetBlocked):
            aggregate(outcomes)


@pytest.mark.parametrize("prebuilt", [False, True])
def test_review_unknown_prior_dib_still_reports_input_errors_first(prebuilt):
    members = _members()
    with pytest.raises(g.InvalidFamilyInput, match="unique"):
        g.evaluate_family(
            "invalid",
            1,
            lambda: _family(_state(prebuilt), (*members, members[1])),
        )


def test_review_unknown_prior_dib_rules_are_quoted_from_the_captures():
    assert (
        "The only criterion for this to apply is entitlement for the specific "
        "month of 5/78." in source_text("poms_rs_00615_712")
    )
    assert "Entitlement before or after 5/78 is immaterial." in source_text(
        "poms_rs_00615_712"
    )
    assert (
        "Prior DIB entitlement more than 12 months before the current "
        "eligibility or death - new eligibility after 1978."
        in source_text("poms_rs_00615_736")
    )


@pytest.mark.parametrize("prebuilt", [False, True])
@pytest.mark.parametrize(
    "configuration", ["ordinary", "alone", "outside", "not-entitled"]
)
def test_review_modern_unknown_dib_only_adds_refusal_when_clause_could_apply(
    prebuilt, configuration
):
    state = _state(prebuilt)
    if configuration == "ordinary":
        members = [
            g.Beneficiary("w", g.Role.WIDOW, child_in_care=False),
            _members()[1],
        ]
    elif configuration == "alone":
        members = [_members()[0]]
    elif configuration == "outside":
        members = [
            g.Beneficiary(
                "w",
                g.Role.SURVIVING_DIVORCED_SPOUSE,
                original_benefit_basis=F(410),
                child_in_care=False,
            ),
            _members()[1],
        ]
    else:
        members = [
            g.Beneficiary(
                "w",
                g.Role.WIDOW,
                original_benefit_basis=F(410),
                birth_year=1940,
                own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(410)),
                child_in_care=False,
            ),
            _members()[1],
        ]
    result = _family(state, members)
    assert result.record_total > 0


@given(st.integers(1983, 2026), st.booleans(), st.booleans())
@settings(deadline=None)
def test_property_unknown_dib_refusal_is_independent_of_metadata_and_order(
    year, prebuilt, reverse
):
    members = _members()[::-1] if reverse else _members()
    with pytest.raises(g.FamilyConfigurationUnsupported) as exc:
        _family(_state(prebuilt, year=year), members)
    assert exc.value.reason is UNKNOWN


@given(st.integers(1, 20), st.integers(1, 20), st.booleans())
@settings(deadline=None)
def test_property_unknown_dib_refusal_retains_full_weight_and_input_priority(
    numerator, denominator, prebuilt
):
    weight = F(numerator, denominator)
    state = _state(prebuilt)
    outcomes = [g.evaluate_family("unknown", weight, lambda: _family(state))]
    counts = g.count_family_outcomes(outcomes)
    assert (counts.rows, counts.weight) == (1, weight)
    assert counts.unsupported_by_reason == {UNKNOWN: (1, weight)}
    for aggregate in (g.weighted_record_total, g.weighted_mean_record_total):
        with pytest.raises(g.FamilyTargetBlocked):
            aggregate(outcomes)
    members = _members()
    with pytest.raises(g.InvalidFamilyInput):
        g.evaluate_family(
            "invalid", weight, lambda: _family(state, (*members, members[1]))
        )


@given(st.integers(1983, 2026), st.booleans())
@settings(deadline=None)
def test_property_explicit_history_attestation_matches_built_and_direct(
    year, reverse
):
    members = _members()[::-1] if reverse else _members()
    built = _family(
        replace(_state(False, year), widow_drc_savings_clause=False), members
    )
    direct = _family(
        replace(_state(True, year), widow_drc_savings_clause=False), members
    )
    assert built.by_id() == direct.by_id()
    assert built.record_total == direct.record_total
    assert (
        built.record_total_whole_dollars == direct.record_total_whole_dollars
    )


@given(st.integers(1970, 1983), st.integers(1, 12), st.booleans())
@settings(deadline=None)
def test_property_known_first_ever_dib_exclusion_has_may_1978_boundary(
    year, month, prebuilt
):
    first_dib = g.YearMonth(year, month)
    state = _state(prebuilt, first_dib=first_dib)
    if first_dib <= g.YearMonth(1978, 5):
        with pytest.raises(g.FamilyConfigurationUnsupported) as exc:
            _family(state)
        assert exc.value.reason is UNKNOWN
    else:
        assert _family(state) == _family(
            replace(state, widow_drc_savings_clause=False)
        )
