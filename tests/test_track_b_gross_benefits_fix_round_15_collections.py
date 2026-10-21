"""Statutory conformance: collection order and multiplicity on invented cases.

These tests admit schema and statutory arithmetic claims only, with no
population, behavioral or forecast claim.
"""

import inspect
import math
from collections.abc import Iterable, Sequence
from dataclasses import fields, replace
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction as F
from typing import get_args, get_origin, get_type_hints

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import _provenance as provenance
from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as ret
from tests.test_track_b_gross_benefits_fix_round_12_contract import (
    COMPUTE,
    EVALUATE,
    LAYERS,
    PARAMS,
    RET_PARAMS,
)
from tests.test_track_b_input_schema import (
    DECLARATION_FIELDS,
    PUBLIC_FUNCTIONS,
    _arguments,
    _container_annotation,
    _sample_annotation,
)
from tests.test_track_b_input_schema import (
    declaration_samples as declaration_samples,
)
from tests.test_track_b_input_schema import (
    public_world as public_world,
)

ENCODINGS = (int, str, F, Decimal, float)


@settings(max_examples=150, deadline=None, derandomize=True)
@given(
    numerator=st.integers(-(10**18), 10**18),
    denominator=st.one_of(
        st.sampled_from((1, 2, 5, 10, 20, 100)),
        st.integers(1, 10**12),
    ),
)
def test_dime_validation_matches_legacy_fraction_arithmetic(
    numerator, denominator
):
    amount = F(numerator, denominator)
    # Preserve the previous implementation as an independent exact oracle.
    # The optimized check may avoid temporary Fraction objects, never change
    # which inputs are whole dimes or the returned exact amount.
    invalid = amount < 0 or (amount * 10).denominator != 1
    if invalid:
        with pytest.raises(g.InvalidFamilyInput):
            g._dimes(amount, "money")
    else:
        assert g._dimes(amount, "money") == amount


@pytest.mark.parametrize("container", (set, frozenset))
@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize("amount", (1, 100))
def test_review_cola_sets_reject_before_any_row(container, encoding, amount):
    rows = []

    def compute():
        g.increase_by_colas(amount, container((encoding(10), "10")))
        return COMPUTE["g"]()

    with pytest.raises(g.InvalidFamilyInput):
        rows.append(g.evaluate_family("unordered-colas", 1, compute))
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("container", (tuple, list))
@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize("amount,expected", ((1, F(6, 5)), (100, F(121))))
def test_review_cola_sequences_keep_equal_value_events(
    container, encoding, amount, expected
):
    assert (
        g.increase_by_colas(amount, container((encoding(10), "10")))
        == expected
    )


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    dimes=st.integers(0, 100000),
    rates=st.lists(st.integers(0, 1000), max_size=15),
    encoding=st.sampled_from(ENCODINGS),
    container=st.sampled_from((tuple, list)),
)
def test_ordered_colas_equal_the_element_by_element_dime_fold(
    dimes, rates, encoding, container
):
    amount = F(dimes, 10)
    expected = amount
    for rate in rates:
        expected = F(math.floor(expected * (100 + rate) / 10), 10)
    actual = g.increase_by_colas(
        amount, container(encoding(rate) for rate in rates)
    )
    assert actual == expected
    record = g.WorkerRecord(
        g.FamilyKind.RETIREMENT,
        2020,
        amount,
        cola_percents=container(encoding(rate) for rate in rates),
    )
    assert g.record_state(record, PARAMS).pia == expected


def test_cola_order_matters_after_each_statutory_dime_floor():
    assert g.increase_by_colas(1, [5, 10]) == F(11, 10)
    assert g.increase_by_colas(1, [10, 5]) == F(11, 10)
    # Distinct event orders need not commute once the intermediate dime is
    # discarded. Both orders are valid, and neither may be sorted away.
    assert g.increase_by_colas(1, [10, 50]) == F(8, 5)
    assert g.increase_by_colas(1, [50, 10]) == F(8, 5)
    assert g.increase_by_colas(F(11, 10), [10, 50]) == F(9, 5)
    assert g.increase_by_colas(F(11, 10), [50, 10]) == F(17, 10)


@pytest.mark.parametrize("layer", LAYERS)
@settings(max_examples=20, deadline=None, derandomize=True)
@given(copies=st.integers(1, 8), weight=st.integers(0, 10))
def test_denominator_sequences_preserve_duplicate_key_errors(
    layer, copies, weight
):
    outcome = EVALUATE[layer]("repeat", weight, COMPUTE[layer])
    if copies > 1:
        with pytest.raises(g.InvalidFamilyInput, match="Duplicate outcome"):
            g.count_family_outcomes([outcome] * copies)
        return
    counts = g.count_family_outcomes([outcome] * copies)
    assert counts.rows == counts.supported_rows == copies
    assert counts.weight == counts.supported_weight == copies * weight


def _sequence_annotation(annotation):
    annotation = _container_annotation(annotation)
    return (
        annotation
        if get_origin(annotation)
        in (Iterable, Sequence, tuple, list, set, frozenset)
        else None
    )


COLLECTION_FIELDS = tuple(
    (cls, name, annotation)
    for cls, name in DECLARATION_FIELDS
    if (annotation := _sequence_annotation(get_type_hints(cls)[name]))
    is not None
)
COLLECTION_ARGUMENTS = tuple(
    (module, name, argument, annotation)
    for module, name, function in PUBLIC_FUNCTIONS
    for argument, hint in get_type_hints(function).items()
    if argument != "return"
    and (annotation := _sequence_annotation(hint)) is not None
)


def test_every_collection_schema_declares_order_or_membership():
    for *_, annotation in (*COLLECTION_FIELDS, *COLLECTION_ARGUMENTS):
        assert get_origin(annotation) in (
            Sequence,
            tuple,
            list,
            set,
            frozenset,
        ), "Iterable leaves order and multiplicity undeclared"


@pytest.mark.parametrize("cls,name,annotation", COLLECTION_FIELDS)
@pytest.mark.parametrize("container", (list, tuple, set, frozenset))
def test_every_collection_field_has_canonical_container_semantics(
    cls, name, annotation, container, declaration_samples
):
    reader = provenance._declaration_schemas(cls)[name]
    valid = _sample_annotation(annotation, declaration_samples)
    raw = container(valid)
    membership = get_origin(annotation) in (set, frozenset)
    if not membership and container in (set, frozenset):
        with pytest.raises(g.InvalidFamilyInput):
            reader(raw, name)
        return
    normalized = reader(raw, name)
    assert type(normalized) is (frozenset if membership else tuple)
    assert len(normalized) == len(raw)


@pytest.mark.parametrize(
    "module,name,argument,annotation", COLLECTION_ARGUMENTS
)
@pytest.mark.parametrize("container", (list, tuple, set, frozenset))
def test_every_public_collection_argument_preserves_its_declared_semantics(
    module, name, argument, annotation, container, public_world
):
    function = getattr(module, name)
    arguments = _arguments(module, name, public_world)
    valid = arguments[argument]
    if type(valid) is g.YearMonth:
        valid = valid.as_tuple()
    if container in (set, frozenset):
        # Empty unordered containers must be refused even if there is no
        # element to hash (sealed rows may themselves contain mappings).
        arguments[argument] = container()
        with pytest.raises(g.InvalidFamilyInput):
            function(**arguments)
        return
    arguments[argument] = container(valid)
    expected = function(**_arguments(module, name, public_world))
    assert function(**arguments) == expected
    reader = provenance._argument_schemas(inspect.unwrap(function))[argument]
    assert type(reader(arguments[argument], argument)) is tuple


@pytest.mark.parametrize("container", (list, tuple, set, frozenset))
@given(month=st.integers(1, 12))
def test_membership_months_collapse_equivalent_month_encodings(
    container, month
):
    canonical = g.YearMonth(2022, month)
    raw = container((canonical, (2022, month)))
    claim = a.ARFClaim(
        a.ARFBenefitKind.RIB,
        date(1960, 1, 2),
        (2022, 1),
        1300,
        full_work_deduction_months=raw,
    )
    assert claim.full_work_deduction_months == frozenset((canonical,))


@pytest.mark.parametrize("cls,name,annotation", COLLECTION_FIELDS)
def test_membership_fields_contain_only_months_or_canonical_flags(
    cls, name, annotation, declaration_samples
):
    if get_origin(annotation) not in (set, frozenset):
        return
    element = get_args(annotation)[0]
    assert (
        element is int
        or element == a.MonthInput
        or (inspect.isclass(element) and issubclass(element, Enum))
    )
    inputs = {
        item.name: getattr(declaration_samples[cls], item.name)
        for item in fields(cls)
    }
    valid = list(_sample_annotation(annotation, declaration_samples))
    inputs[name] = valid * 2
    # Schema normalization, before domain-specific crosschecks, checks all
    # elements and deduplicates canonical membership only.
    reader = provenance._declaration_schemas(cls)[name]
    assert reader(inputs[name], name) == reader(valid, name)


@given(month=st.integers(1, 12))
def test_membership_numeric_aliases_are_rejected_not_collapsed(month):
    for alias in (str(month), F(month), Decimal(month), float(month), True):
        with pytest.raises(g.InvalidFamilyInput):
            ret.WorkEarnings(self_employment_months=[month, alias])
    original = ret.WorkEarnings(self_employment_months=[month, month])
    assert original.self_employment_months == frozenset((month,))
    assert replace(original, self_employment_months=[month]) == original


@pytest.mark.parametrize("container", (tuple, list, set, frozenset))
def test_external_parameter_collections_preserve_sources_and_table_order(
    container,
):
    amount = RET_PARAMS.for_year(2026).lower_exempt_amount
    source = amount.sources[0]
    samples = (
        (type(amount), "sources", (source, source)),
        (type(PARAMS), "fra_months_by_birth_year", ((1940, 786), (1960, 804))),
        (
            type(PARAMS),
            "delayed_credit_by_birth_year",
            ((1940, "0.07"), (1960, "0.08")),
        ),
    )
    for cls, name, valid in samples:
        reader = provenance._declaration_schemas(cls)[name]
        if container in (set, frozenset):
            with pytest.raises(g.InvalidFamilyInput):
                reader(container(valid), name)
        else:
            result = reader(container(valid), name)
            assert type(result) is tuple
            assert len(result) == len(valid)
            assert result == valid


@settings(max_examples=30, deadline=None, derandomize=True)
@given(
    wage=st.integers(0, 10000),
    encodings=st.lists(
        st.sampled_from(ENCODINGS[:4]), min_size=12, max_size=12
    ),
    fra_month=st.integers(1, 12),
)
def test_monthly_wages_keep_equal_value_events_in_the_pre_fra_fold(
    wage, encodings, fra_month
):
    work = ret.WorkEarnings(wages=[encode(wage) for encode in encodings])
    assert work.wages == (F(wage),) * 12
    assert ret.countable_earnings(work, fra_month) == (fra_month - 1) * wage
    assert ret.countable_earnings(work, None) == 12 * wage
