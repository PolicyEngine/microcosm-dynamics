"""Surviving-divorced caregiver floor regressions (statutory conformance).

Captured POMS examples and invented monthly families admit no population,
behavioral, or forecast claim. The hypothetical 202(g) mother/father is
subject to the maximum; the actual 202(e)/(f) divorced widow(er) is outside.
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


def _family(pia, maximum, members):
    return g.family_benefits(
        g.RecordState(
            g.FamilyKind.SURVIVOR,
            pia,
            maximum,
            widow_drc_savings_clause=False,
        ),
        members,
        payment_month=NOW,
        params=PARAMS,
        standalone=True,
    )


def _members(months=60, child_count=2):
    return [
        g.Beneficiary(
            "w",
            g.Role.SURVIVING_DIVORCED_SPOUSE,
            birth_year=1935,
            reduction_months=months,
            reduction_period_months=60,
            child_in_care="c0",
        ),
        *[g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(child_count)],
    ]


@pytest.mark.parametrize(
    "pia,maximum,widow,mother,child,total,whole",
    [
        ("1000", "1750", "715", "583.30", "750", "2215", 2215),
        ("203.90", "305.90", "145.70", "101.90", "152.90", "451.50", 449),
        ("0.40", "0.60", "0.20", "0.20", "0.30", "0.80", 0),
        ("2.70", "4.00", "1.90", "1.30", "2.00", "5.90", 5),
    ],
    ids=["review-full", "poms-682", "minimal-dime", "minimal-dollar"],
)
def test_review_divorced_care_floor_uses_subject_mother_maximum(
    pia, maximum, widow, mother, child, total, whole
):
    members = _members()
    result = _family(F(pia), F(maximum), members)
    comparison = _family(
        F(pia),
        F(maximum),
        [
            g.Beneficiary("w", g.Role.MOTHER_FATHER),
            *members[1:],
        ],
    )
    assert comparison.by_id()["w"].auxiliary_payable == F(mother)
    assert result.by_id()["w"].auxiliary_payable == F(widow)
    assert result.by_id()["w"].whole_dollar_auxiliary == int(F(widow))
    assert not result.by_id()["w"].subject_to_family_maximum
    assert result.by_id()["w"].counted_against_maximum == 0
    assert result.by_id()["c0"].auxiliary_payable == F(child)
    assert result.by_id()["c1"].auxiliary_payable == F(child)
    assert result.record_total == F(total)
    assert result.record_total_whole_dollars == whole


def test_review_682_care_path_figures_and_conversion_are_captured_verbatim():
    assert (
        "as a divorced spouse under section 202(b) or (c) or as a "
        "surviving divorced spouse under section 202(e) or (f) for any month"
    ) in source_text("ssa_act_203")
    text = source_text("poms_rs_00615_682")
    assert (
        "A surviving divorced mother (E1) and two children are entitled "
        "to $101.90 each, based on a PIA of $203.90 (Maximum $305.90)."
    ) in text
    assert (
        "At age 60, E1 becomes entitled as D6 and is paid outside the maximum."
    ) in text
    assert (
        "The benefits payable are $145.70 ($203.90 reduced 60 months) "
        "to D6 and $152.90 to each child."
    ) in text


@settings(max_examples=75, deadline=None, derandomize=True)
@given(
    dimes=st.integers(1, 3000),
    child_count=st.integers(1, 5),
    months=st.integers(0, 60),
    maximum_share=st.sampled_from([F(3, 2), F(7, 4), F(2)]),
)
def test_property_divorced_care_floor_matches_subject_mother_and_keeps_children(
    dimes, child_count, months, maximum_share
):
    pia = F(dimes, 10)
    maximum = g.floor_dime(pia * maximum_share)
    members = _members(months, child_count)
    result = _family(pia, maximum, members)
    ordinary = _family(
        pia,
        maximum,
        [replace(members[0], child_in_care=False), *members[1:]],
    )
    mother = _family(
        pia,
        maximum,
        [g.Beneficiary("w", g.Role.MOTHER_FATHER), *members[1:]],
    )
    assert result.by_id()["w"].auxiliary_payable == max(
        ordinary.by_id()["w"].auxiliary_payable,
        mother.by_id()["w"].auxiliary_payable,
    )
    assert not result.by_id()["w"].subject_to_family_maximum
    assert result.by_id()["w"].counted_against_maximum == 0
    for child in members[1:]:
        assert (
            result.by_id()[child.beneficiary_id]
            == ordinary.by_id()[child.beneficiary_id]
        )
    assert result.subject_total == ordinary.subject_total <= maximum
    assert result.record_total == sum(
        row.auxiliary_payable for row in result.beneficiaries
    )
    assert result.record_total_whole_dollars == sum(
        row.whole_dollar_auxiliary for row in result.beneficiaries
    )
    assert all(
        row.auxiliary_payable >= 0
        and (row.auxiliary_payable * 10).denominator == 1
        for row in result.beneficiaries
    )
    assert result == _family(pia, maximum, members)
    assert (
        result.by_id()
        == _family(pia, maximum, list(reversed(members))).by_id()
    )
