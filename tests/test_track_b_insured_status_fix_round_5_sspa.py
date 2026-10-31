"""Statutory conformance: source-required wrong-number SS-5 exemptions.

Invented declarations only; no population, behavioral, or forecast claim.
The applicability declaration represents the adjudicated Section 211 fact,
including the captured RS 00301.102 B.3.b wrong-number exception.
"""

from datetime import date
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_sources import source_text

OBSERVED = i.EarningsProvenance.OBSERVED
PROPERTY = settings(max_examples=30, deadline=None)


def _person(birth=date(1980, 2, 2), **values):
    facts = {
        "alien_worker": True,
        "prior_disability_periods_provenance": OBSERVED,
        "current_disability_period_established": False,
        "current_disability_period_provenance": OBSERVED,
        "sspa211_applies": False,
        "sspa211_provenance": OBSERVED,
    }
    facts.update(values)
    return i.Person(birth, **facts)


def _evaluate(person, counts=None, *, month=date(2006, 1, 1)):
    years = history(person, month, counts or {2004: 4, 2005: 2})
    return i.evaluate_insured_status(
        "wrong-number-ss5",
        Fraction(3, 2),
        lambda: i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY
        ),
    )


def test_reviewed_post2003_assignment_accepts_observed_wrong_number_exemption():
    person = _person(ssn_assignment_date=date(2004, 1, 1))
    row = _evaluate(person)
    assert row.supported
    assert row.result.fully.insured
    assert row.result.fully.required == 6
    assert row.result.fully.qc_count_lower == 6
    assert row.result.fully.qc_count_upper == 6
    count = count_family_outcomes((row,))
    assert count.rows == count.supported_rows == 1
    assert count.weight == Fraction(3, 2)


def test_never_assigned_true_identity_ssn_can_have_wrong_number_exemption():
    row = _evaluate(_person(ssn_never_assigned=True))
    assert row.supported
    assert row.result.fully.insured
    assert row.result.fully.required == 6
    assert row.result.fully.qc_count_lower == 6
    assert row.result.fully.qc_count_upper == 6


@pytest.mark.parametrize(
    "condition", [(), (i.CoverageCondition.MILITARY_CREDITS,)]
)
def test_pre2004_assignment_cannot_declare_section211_applicable(condition):
    person = _person(
        ssn_assignment_date=date(2003, 12, 31),
        sspa211_applies=True,
        conditions=condition,
    )
    with pytest.raises(
        i.InvalidFamilyInput, match="Conflicting SSPA211 applicability facts"
    ):
        _evaluate(person)


@pytest.mark.parametrize(
    "facts",
    [
        {"ssn_assignment_date": date(2004, 1, 1)},
        {"ssn_never_assigned": True},
    ],
)
def test_unadjudicated_date_and_never_assigned_presumptions_still_apply(facts):
    row = _evaluate(
        _person(
            **facts,
            sspa211_applies=None,
            sspa211_provenance=i.EarningsProvenance.UNKNOWN,
        )
    )
    assert not row.supported
    assert row.unsupported.reason is i.InsuredUnsupportedReason.ALIEN_WORKER
    assert count_family_outcomes((row,)).rows == 1


@PROPERTY
@given(
    first=st.integers(0, 4),
    second=st.integers(0, 4),
    never_assigned=st.booleans(),
    provenance=st.sampled_from(
        [OBSERVED, i.EarningsProvenance.CONVENTION_FILLED]
    ),
)
def test_adjudicated_exemption_preserves_ordinary_count_and_evaluator_row(
    first, second, never_assigned, provenance
):
    person = _person(
        ssn_assignment_date=None if never_assigned else date(2004, 1, 1),
        ssn_never_assigned=never_assigned,
        sspa211_provenance=provenance,
        sspa211_convention_id=(
            "invented-wrong-number-exemption"
            if provenance is i.EarningsProvenance.CONVENTION_FILLED
            else None
        ),
    )
    row = _evaluate(person, {2004: first, 2005: second})
    decision = row.result.fully
    assert decision.insured is (first + second >= 6)
    assert decision.required == 6
    assert decision.qc_count_lower == decision.qc_count_upper == first + second
    count = count_family_outcomes((row,))
    assert count.rows == count.supported_rows == 1
    assert count.weight == Fraction(3, 2)


@PROPERTY
@given(
    assignment=st.dates(date(1980, 2, 2), date(2003, 12, 31)),
    applies=st.booleans(),
)
def test_pre2004_assignment_accepts_exactly_the_exempt_applicability(
    assignment, applies
):
    person = _person(ssn_assignment_date=assignment, sspa211_applies=applies)
    if applies:
        with pytest.raises(
            i.InvalidFamilyInput,
            match="Conflicting SSPA211 applicability facts",
        ):
            _evaluate(person)
    else:
        row = _evaluate(person)
        assert row.supported
        assert row.result.fully.insured
        assert count_family_outcomes((row,)).rows == 1


@pytest.mark.parametrize("birth", [date(2005, 1, 1), date(2004, 1, 1)])
@pytest.mark.parametrize("assignment_facts", ["assigned", "never", "unknown"])
@pytest.mark.parametrize(
    "conditions", [(), (i.CoverageCondition.MILITARY_CREDITS,)]
)
def test_post2003_birth_cannot_declare_wrong_number_exemption(
    birth, assignment_facts, conditions
):
    """Executed audit case and exact cutoff: no legitimate prebirth SSN."""
    person = _person(
        birth,
        ssn_assignment_date=(
            birth if assignment_facts == "assigned" else None
        ),
        ssn_never_assigned=assignment_facts == "never",
        conditions=conditions,
    )
    with pytest.raises(
        i.InvalidFamilyInput, match="Conflicting SSPA211 applicability facts"
    ):
        _evaluate(person, {2023: 4, 2024: 2}, month=date(2026, 1, 1))


@PROPERTY
@given(
    birth=st.dates(date(2003, 1, 1), date(2005, 12, 31)),
    assignment_facts=st.sampled_from(["assigned", "never", "unknown"]),
    first=st.integers(0, 4),
    second=st.integers(0, 4),
)
def test_wrong_number_exemption_requires_possible_pre2004_assignment(
    birth, assignment_facts, first, second
):
    person = _person(
        birth,
        ssn_assignment_date=(
            max(birth, date(2004, 1, 1))
            if assignment_facts == "assigned"
            else None
        ),
        ssn_never_assigned=assignment_facts == "never",
    )

    def compute():
        return _evaluate(
            person, {2023: first, 2024: second}, month=date(2026, 1, 1)
        )

    if birth >= date(2004, 1, 1):
        with pytest.raises(
            i.InvalidFamilyInput,
            match="Conflicting SSPA211 applicability facts",
        ):
            compute()
    else:
        row = compute()
        assert row.supported
        assert row.result.fully.insured is (first + second >= 6)
        assert row.result.fully.required == 6
        assert (
            row.result.fully.qc_count_lower
            == row.result.fully.qc_count_upper
            == first + second
        )
        assert count_family_outcomes((row,)).rows == 1


@pytest.mark.parametrize(
    "quote",
    [
        "If an alien worker could have legitimately been assigned an SSN "
        "before 1/1/2004, the worker is exempt from the requirements of "
        "section 211 of the SSPA.",
        "SSA erroneously issued the alien worker an SSN with another "
        "person's SSN instead of assigning the alien worker their own SSN",
        "An alien worker whose SSN was assigned before January 1, 2004 is "
        "exempt from the requirements of Section 211 of the Social Security "
        "Protection Act, even if the SSN was not work authorized.",
        "An alien worker who does not have an SSN card for work purposes "
        "is nevertheless considered to meet the work SSN requirement of "
        "Section 211 of the SSPA if they meet one of the following profiles:",
    ],
)
def test_wrong_number_exception_and_retained_contradiction_quote_capture(
    quote,
):
    assert quote in source_text("poms_rs_00301_102")
