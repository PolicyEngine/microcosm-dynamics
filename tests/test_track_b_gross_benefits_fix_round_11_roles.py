"""Statutory conformance: one role/record contract for every G entry point.

Invented inputs only. No population, behavioral or forecast claim.
"""

from fractions import Fraction as F
from inspect import isfunction
from typing import get_type_hints

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)
WIDOWS = {
    g.Role.WIDOW,
    g.Role.SURVIVING_DIVORCED_SPOUSE,
    g.Role.DISABLED_WIDOW,
}
SPOUSES = {
    g.Role.SPOUSE,
    g.Role.SPOUSE_CHILD_IN_CARE,
    g.Role.DIVORCED_SPOUSE,
}
# This independent expected table is the 402(b)-(h) entitlement surface.
RECORD_KINDS = {
    **{
        role: {g.FamilyKind.RETIREMENT, g.FamilyKind.DISABILITY}
        for role in SPOUSES
    },
    g.Role.CHILD: set(g.FamilyKind),
    **{
        role: {g.FamilyKind.SURVIVOR}
        for role in WIDOWS | {g.Role.MOTHER_FATHER, g.Role.PARENT}
    },
}
ROLE_KIND_HELPERS = {"original_benefit": g.original_benefit}
ROLE_KIND_CASES = [(role, kind) for role in g.Role for kind in g.FamilyKind]


def _members(role, basis, parent_count):
    values = {"original_benefit_basis": basis}
    if role in WIDOWS | {g.Role.DIVORCED_SPOUSE}:
        values["child_in_care"] = False
    if role is g.Role.DIVORCED_SPOUSE:
        values["first_entitlement_child_in_care"] = False
    count = (parent_count or 1) if role is g.Role.PARENT else 1
    return tuple(g.Beneficiary(f"b{i}", role, **values) for i in range(count))


def _family(kind, role, pia, basis=None, parent_count=None, *, refused=False):
    state = g.RecordState(
        kind,
        pia,
        4 * max(pia, basis or F(0)),
        worker=(
            g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia)
            if kind is g.FamilyKind.RETIREMENT
            else None
        ),
        conditions=(
            frozenset({g.RecordCondition.ADMINISTRATIVE_FINALITY})
            if refused
            else frozenset()
        ),
        widow_drc_savings_clause=False,
    )
    return g.family_benefits(
        state,
        _members(role, basis, parent_count),
        payment_month=NOW,
        params=PARAMS,
        standalone=True,
    )


def _expected_ob(role, kind, pia, basis, parent_count):
    if role in SPOUSES:
        share = F(1, 2)
    elif role is g.Role.CHILD:
        share = F(3, 4) if kind is g.FamilyKind.SURVIVOR else F(1, 2)
    elif role in WIDOWS:
        return pia if basis is None else basis
    elif role is g.Role.PARENT:
        share = F(3, 4) if parent_count == 2 else F(165, 200)
    else:
        assert role is g.Role.MOTHER_FATHER
        share = F(3, 4)
    return F((pia * share * 10).__floor__(), 10)


def test_review_widow_on_retirement_record_is_an_input_error():
    with pytest.raises(g.InvalidFamilyInput):
        g.original_benefit(g.Role.WIDOW, g.FamilyKind.RETIREMENT, 1000)


def test_review_child_basis_is_an_input_error_instead_of_ignored_money():
    with pytest.raises(g.InvalidFamilyInput):
        g.original_benefit(
            g.Role.CHILD, g.FamilyKind.SURVIVOR, 1000, basis=2000
        )


def test_every_exported_role_record_helper_has_a_compatibility_property():
    discovered = set()
    for name in g.__all__:
        function = getattr(g, name)
        if isfunction(function):
            annotations = set(get_type_hints(function).values())
            if {g.Role, g.FamilyKind} <= annotations:
                discovered.add(name)
    assert discovered == set(ROLE_KIND_HELPERS)
    assert set(RECORD_KINDS) == set(g.Role)


@pytest.mark.parametrize("name", ROLE_KIND_HELPERS)
@pytest.mark.parametrize("role,kind", ROLE_KIND_CASES)
@given(
    dimes=st.integers(0, 1_000_000),
    extra_basis=st.one_of(st.none(), st.integers(0, 1_000_000)),
    parents=st.sampled_from([None, 1, 2]),
)
@settings(max_examples=30, deadline=None)
def test_role_record_helpers_match_family_original_amounts_or_input_errors(
    name, role, kind, dimes, extra_basis, parents
):
    pia = F(dimes, 10)
    basis = (
        pia + F(extra_basis, 10)
        if role in WIDOWS and extra_basis is not None
        else None
    )
    parent_count = parents if role is g.Role.PARENT else None
    helper = ROLE_KIND_HELPERS[name]
    if kind not in RECORD_KINDS[role]:
        with pytest.raises(g.InvalidFamilyInput):
            helper(role, kind, pia, basis, parent_count=parent_count)
        # A role mismatch must be found even on a record that would refuse.
        for refused in (False, True):
            with pytest.raises(g.InvalidFamilyInput):
                _family(kind, role, pia, basis, parent_count, refused=refused)
        return
    amount = helper(role, kind, pia, basis, parent_count=parent_count)
    expected = _expected_ob(role, kind, pia, basis, parent_count)
    assert amount == expected
    family = _family(kind, role, pia, basis, parent_count)
    assert all(row.original_benefit == amount for row in family.beneficiaries)


@pytest.mark.parametrize("name", ROLE_KIND_HELPERS)
@pytest.mark.parametrize(
    "role,kind", [(r, k) for r, k in ROLE_KIND_CASES if r not in WIDOWS]
)
@given(dimes=st.integers(0, 1_000_000), basis_dimes=st.integers(0, 1_000_000))
@settings(max_examples=20, deadline=None)
def test_every_nonwidow_basis_is_invalid_in_helpers_and_family_declarations(
    name, role, kind, dimes, basis_dimes
):
    pia, basis = F(dimes, 10), F(basis_dimes, 10)
    with pytest.raises(g.InvalidFamilyInput):
        ROLE_KIND_HELPERS[name](role, kind, pia, basis=basis)
    with pytest.raises(g.InvalidFamilyInput):
        _family(kind, role, pia, basis=basis)


@pytest.mark.parametrize("name", ROLE_KIND_HELPERS)
@pytest.mark.parametrize(
    "role,kind",
    [(r, k) for r, k in ROLE_KIND_CASES if r is not g.Role.PARENT],
)
@given(dimes=st.integers(0, 1_000_000), count=st.integers(1, 2))
@settings(max_examples=20, deadline=None)
def test_parent_count_is_invalid_for_every_nonparent_role(
    name, role, kind, dimes, count
):
    with pytest.raises(g.InvalidFamilyInput):
        ROLE_KIND_HELPERS[name](role, kind, F(dimes, 10), parent_count=count)


@pytest.mark.parametrize("role", sorted(WIDOWS, key=lambda role: role.value))
@given(dimes=st.integers(1, 1_000_000))
@settings(max_examples=20, deadline=None)
def test_widow_basis_below_pia_is_invalid_on_every_route(role, dimes):
    pia, basis = F(dimes, 10), F(dimes - 1, 10)
    for helper in ROLE_KIND_HELPERS.values():
        with pytest.raises(g.InvalidFamilyInput):
            helper(role, g.FamilyKind.SURVIVOR, pia, basis=basis)
    with pytest.raises(g.InvalidFamilyInput):
        _family(g.FamilyKind.SURVIVOR, role, pia, basis=basis)


@given(dimes=st.integers(0, 1_000_000))
@settings(max_examples=30, deadline=None)
def test_two_parents_do_not_pass_their_count_to_other_survivor_roles(dimes):
    pia = F(dimes, 10)
    members = (
        g.Beneficiary("p1", g.Role.PARENT),
        g.Beneficiary("p2", g.Role.PARENT),
        g.Beneficiary("child", g.Role.CHILD),
        g.Beneficiary("widow", g.Role.WIDOW, child_in_care=False),
    )
    result = g.family_benefits(
        g.RecordState(
            g.FamilyKind.SURVIVOR,
            pia,
            4 * pia,
            widow_drc_savings_clause=False,
        ),
        members,
        payment_month=NOW,
        params=PARAMS,
        standalone=True,
    )
    for row in result.beneficiaries:
        expected = _expected_ob(row.role, g.FamilyKind.SURVIVOR, pia, None, 2)
        assert row.original_benefit == expected
