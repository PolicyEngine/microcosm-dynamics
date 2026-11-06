"""Invented newborn packets, parent states and design §7 properties."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, replace
from functools import partial

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal

from populace_dynamics.engine.accounting import PopulationEventKind
from populace_dynamics.engine.loop import (
    MaritalStepResult,
    PeriodContext,
    PeriodModules,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import (
    advance_age,
    materialize_maternal_births,
)
from populace_dynamics.open_population.conventions import (
    BIRTH_ORDER_COLUMN,
    FOREIGN_BORN_COLUMN,
    NEWBORN_SEX_STREAM_TAG,
    OUT_OF_DOMAIN_COLUMNS,
    PARITY_COLUMN,
    SECOND_PARENT_COLUMN,
    SECOND_PARENT_UNLINKED_COLUMN,
    SPOUSE_ABROAD_COLUMN,
    ConventionSource,
    ConventionStatus,
)
from populace_dynamics.open_population.errors import (
    ControlSourceUnavailable,
    IdOrStreamCollision,
)
from populace_dynamics.open_population.gates import GateRunRequest, run_gate
from populace_dynamics.open_population.newborn import (
    NEWBORN_G_FIELDS,
    NEWBORN_G_WORKER_LINKS,
    UNLINKED_PARTNER_OUTSIDE_ROSTER,
    UNLINKED_PARTNER_UNKNOWN,
    UNLINKED_REASONS,
    UNLINKED_UNPARTNERED,
    NewbornPacketRefused,
    NewbornPacketStep,
    SexRatioPin,
    append_newborn_packet,
    read_second_parents,
)
from populace_dynamics.open_population.streams import DirectRNGStreams

YEAR = 2026
MOTHERS = (11, 22, 33)
PERSONS = (*MOTHERS, 44, 55)


def _source(status=ConventionStatus.INVENTED):
    return ConventionSource("invented newborn convention", status)


def _pin(share=0.37, status=ConventionStatus.INVENTED):
    return SexRatioPin(share, _source(status))


def _frame():
    return pd.DataFrame(
        {
            "person_id": pd.Series(PERSONS, dtype="Int64"),
            "year": pd.Series([YEAR] * 5, dtype="Int64"),
            "age": pd.Series([27, 31, 35, 29, 34], dtype="Int64"),
            "birth_year": pd.Series(
                [1999, 1995, 1991, 1997, 1992], dtype="Int64"
            ),
            "sex": ["female", "female", "female", "female", "male"],
            "household_id": pd.Series(
                [101, 102, 103, 101, 102], dtype="Int64"
            ),
            "weight": [1.25, 2.5, 3.75, 1.25, 2.5],
            "start_weight": [1.0, 2.0, 3.0, 1.0, 2.0],
            "invented_state": ["a", "b", "c", "d", "e"],
        }
    )


def _births(mothers=MOTHERS, *, year=YEAR, orders=None):
    mothers = list(mothers)
    return pd.DataFrame(
        {
            "parent_person_id": pd.Series(mothers, dtype="Int64"),
            "birth_year": pd.Series([year] * len(mothers), dtype="Int64"),
            "birth_order": pd.Series(
                orders if orders is not None else [1] * len(mothers),
                dtype="Int64",
            ),
        }
    )


def _state():
    return pd.DataFrame(
        {
            "person_id": pd.Series(MOTHERS, dtype="Int64"),
            "spouse_person_id": pd.Series([44, pd.NA, pd.NA], dtype="Int64"),
            "partner_person_id": pd.Series([pd.NA, 55, pd.NA], dtype="Int64"),
            "marital_status": ["married", "partnered", pd.NA],
        }
    )


def _marital(births=None, state=None):
    return MaritalStepResult(
        sim_years=_state() if state is None else state,
        births=_births() if births is None else births,
    )


def _context(*, draw=0, registry=DirectRNGStreams, start=100):
    return PeriodContext(
        period_index=1,
        year=YEAR,
        draw_index=draw,
        metadata={"synthetic_id_allocator": SyntheticPersonIdAllocator(start)},
        rng_registry=registry(draw, 3),
        person_ordinals={
            person: index for index, person in enumerate(PERSONS)
        },
    )


def _append(frame=None, births=None, context=None, marital=None, **kwargs):
    frame = _frame() if frame is None else frame
    births = _births() if births is None else births
    context = _context() if context is None else context
    marital = _marital(births) if marital is None else marital
    return append_newborn_packet(
        frame,
        births,
        context,
        marital,
        np.random.default_rng(123),
        sex_ratio=kwargs.pop("sex_ratio", _pin()),
        **kwargs,
    )


def _canonical(frame):
    return frame.sort_values("person_id").reset_index(drop=True)


def _children(frame):
    return frame.loc[frame["synthetic_entry"].fillna(False)].reset_index(
        drop=True
    )


def _assert_parent(result, mother, *, link=None, reason=None):
    actual_link, actual_reason = result[mother]
    if link is None:
        assert pd.isna(actual_link)
        assert actual_reason == reason
    else:
        assert actual_link == link
        assert pd.isna(actual_reason)


def test_registered_unlinked_reasons_and_g_field_contract():
    from populace_dynamics.track_b.gross_benefits import Beneficiary, Role

    assert UNLINKED_REASONS == frozenset(
        {"unpartnered_mother", "partner_outside_roster", "partner_unknown"}
    )
    assert NEWBORN_G_FIELDS == {
        "person_id": "beneficiary_id",
        "birth_year": "birth_year",
    }
    assert set(NEWBORN_G_FIELDS.values()) <= {
        field.name for field in fields(Beneficiary)
    }
    assert NEWBORN_G_WORKER_LINKS == (
        "parent_person_id",
        SECOND_PARENT_COLUMN,
    )
    assert Role.CHILD.value == "child"


@pytest.mark.parametrize(
    "share",
    [
        0,
        1,
        -0.1,
        1.1,
        np.nan,
        np.inf,
        -np.inf,
        True,
        False,
        np.bool_(True),
        "0.4",
        None,
    ],
)
def test_sex_ratio_refuses_invalid_shares(share):
    with pytest.raises(ValueError):
        SexRatioPin(share, _source())


@pytest.mark.parametrize("source", [None, "invented", object()])
def test_sex_ratio_requires_a_convention_source(source):
    with pytest.raises(TypeError):
        SexRatioPin(0.37, source)


@pytest.mark.parametrize("status", list(ConventionStatus))
def test_each_source_status_can_be_supplied_but_only_frozen_can_be_required(
    status,
):
    step = NewbornPacketStep(_pin(status=status))
    if status is ConventionStatus.FROZEN:
        assert step.require_frozen() is None
    else:
        with pytest.raises(
            ControlSourceUnavailable, match="CONTROL_SOURCE_UNAVAILABLE"
        ):
            step.require_frozen()


def test_pin_is_required_at_both_entry_points():
    with pytest.raises(TypeError):
        NewbornPacketStep()
    with pytest.raises(TypeError):
        append_newborn_packet(
            _frame(),
            _births(),
            _context(),
            _marital(),
            np.random.default_rng(0),
        )
    with pytest.raises(TypeError):
        NewbornPacketStep(None)


@settings(max_examples=10, deadline=None, derandomize=True)
@given(
    share=st.floats(
        min_value=0.001, max_value=0.999, allow_nan=False, allow_infinity=False
    )
)
def test_every_admissible_invented_share_remains_an_explicit_input(share):
    pin = SexRatioPin(share, _source())
    assert pin.share_male == share
    assert NewbornPacketStep(pin).sex_ratio is pin


def test_parent_reader_missing_row_and_empty_state_are_unknown():
    frame = _frame()
    result = read_second_parents(
        frame, MOTHERS, _marital(state=pd.DataFrame())
    )
    for mother in MOTHERS:
        _assert_parent(result, mother, reason=UNLINKED_PARTNER_UNKNOWN)
    state = _state().loc[lambda row: row["person_id"] != 11]
    _assert_parent(
        read_second_parents(frame, [11], _marital(state=state)),
        11,
        reason=UNLINKED_PARTNER_UNKNOWN,
    )


@pytest.mark.parametrize(
    "spouse,partner", [(44, pd.NA), (pd.NA, 44), (44, 44)]
)
def test_parent_reader_uses_the_authoritative_spouse_or_partner_of_any_sex(
    spouse, partner
):
    frame = _frame()
    frame["spouse_person_id"] = 55
    state = pd.DataFrame(
        {
            "person_id": [11],
            "spouse_person_id": [spouse],
            "partner_person_id": [partner],
        }
    )
    result = read_second_parents(frame, [11], _marital(state=state))
    _assert_parent(result, 11, link=44)


@pytest.mark.parametrize("kind", ["duplicate", "conflict", "self"])
def test_parent_reader_refuses_ambiguous_or_self_parent_state(kind):
    state = pd.DataFrame({"person_id": [11], "spouse_person_id": [44]})
    if kind == "duplicate":
        state = pd.concat([state, state], ignore_index=True)
    elif kind == "conflict":
        state["partner_person_id"] = 55
    else:
        state["spouse_person_id"] = 11
    with pytest.raises(NewbornPacketRefused, match="NEWBORN_PACKET_REFUSED"):
        read_second_parents(_frame(), [11], _marital(state=state))


def test_parent_reader_links_on_roster_and_marks_an_off_roster_link():
    state = pd.DataFrame(
        {"person_id": [11, 22], "spouse_person_id": [44, 999]}
    )
    result = read_second_parents(_frame(), [11, 22], _marital(state=state))
    _assert_parent(result, 11, link=44)
    _assert_parent(result, 22, reason=UNLINKED_PARTNER_OUTSIDE_ROSTER)


def test_authoritative_on_roster_link_takes_precedence_over_abroad_marker():
    state = pd.DataFrame(
        {
            "person_id": [11],
            "spouse_person_id": [44],
            SPOUSE_ABROAD_COLUMN: [999],
            "marital_status": ["single"],
        }
    )
    result = read_second_parents(_frame(), [11], _marital(state=state))
    _assert_parent(result, 11, link=44)


@pytest.mark.parametrize("location", ["state", "frame"])
def test_parent_reader_marks_a_spouse_abroad_without_a_link(location):
    frame = _frame()
    state = pd.DataFrame({"person_id": [11], "marital_status": ["married"]})
    if location == "state":
        state[SPOUSE_ABROAD_COLUMN] = 999
    else:
        frame[SPOUSE_ABROAD_COLUMN] = pd.Series(
            [999, pd.NA, pd.NA, pd.NA, pd.NA], dtype="Int64"
        )
    result = read_second_parents(frame, [11], _marital(state=state))
    _assert_parent(result, 11, reason=UNLINKED_PARTNER_OUTSIDE_ROSTER)


def test_parent_reader_state_abroad_column_takes_precedence_over_frame():
    frame = _frame()
    frame[SPOUSE_ABROAD_COLUMN] = 999
    state = pd.DataFrame(
        {
            "person_id": [11],
            "marital_status": ["single"],
            SPOUSE_ABROAD_COLUMN: [pd.NA],
        }
    )
    result = read_second_parents(frame, [11], _marital(state=state))
    _assert_parent(result, 11, reason=UNLINKED_UNPARTNERED)


@pytest.mark.parametrize("status", [pd.NA, "married"])
def test_parent_reader_missing_or_married_status_without_link_is_unknown(
    status,
):
    state = pd.DataFrame({"person_id": [11], "marital_status": [status]})
    result = read_second_parents(_frame(), [11], _marital(state=state))
    _assert_parent(result, 11, reason=UNLINKED_PARTNER_UNKNOWN)


@pytest.mark.parametrize("status", ["single", "divorced", "invented_status"])
def test_parent_reader_other_status_without_link_is_unpartnered(status):
    state = pd.DataFrame({"person_id": [11], "marital_status": [status]})
    result = read_second_parents(_frame(), [11], _marital(state=state))
    _assert_parent(result, 11, reason=UNLINKED_UNPARTNERED)


@settings(max_examples=12, deadline=None, derandomize=True)
@given(
    mothers=st.lists(
        st.sampled_from(MOTHERS), unique=True, min_size=1, max_size=3
    ),
    orders=st.lists(st.integers(1, 8), min_size=3, max_size=3),
    draw=st.integers(0, 12),
)
def test_packet_invariants_preserve_mothers_weights_domains_and_parent_exclusivity(
    mothers, orders, draw
):
    frame = _frame()
    births = _births(mothers, orders=orders[: len(mothers)])
    context = _context(draw=draw)
    actual = _append(frame, births, context)
    children = _children(actual)
    assert len(actual) == len(frame) + len(mothers)
    assert context.synthetic_id_allocator.next_id == 100 + len(mothers)
    assert children["person_id"].tolist() == list(
        range(100, 100 + len(mothers))
    )
    assert children["parent_person_id"].tolist() == sorted(mothers)
    assert set(children["year"]) == {YEAR}
    assert set(children["birth_year"]) == {YEAR}
    assert set(children["age"]) == {0}
    assert set(children["sex"]) <= {"male", "female"}
    assert not children[FOREIGN_BORN_COLUMN].any()
    assert children["invented_state"].isna().all()
    assert "entry_kind" not in actual
    assert "entry_year" not in actual
    indexed = frame.set_index("person_id")
    order = births.set_index("parent_person_id")["birth_order"]
    authoritative = read_second_parents(frame, mothers, _marital())
    for _, child in children.iterrows():
        mother = child["parent_person_id"]
        assert mother in indexed.index
        assert indexed.loc[mother, "sex"] == "female"
        for column in ("household_id", "weight", "start_weight"):
            assert child[column] == indexed.loc[mother, column]
        assert child[BIRTH_ORDER_COLUMN] == order.loc[mother]
        link = child[SECOND_PARENT_COLUMN]
        reason = child[SECOND_PARENT_UNLINKED_COLUMN]
        assert pd.isna(link) != pd.isna(reason)
        if pd.notna(link):
            assert link in indexed.index
            assert link != mother
            assert link == authoritative[mother][0]
        else:
            assert reason in UNLINKED_REASONS
        if child["sex"] == "female":
            assert child[PARITY_COLUMN] == 0
        else:
            assert pd.isna(child[PARITY_COLUMN])
        for column in OUT_OF_DOMAIN_COLUMNS.values():
            assert child[column]
    incumbents = actual.iloc[: len(frame)]
    assert_frame_equal(incumbents[frame.columns], frame)
    for column in ("synthetic_entry", *OUT_OF_DOMAIN_COLUMNS.values()):
        assert not incumbents[column].any()
    for column in (
        "parent_person_id",
        SECOND_PARENT_COLUMN,
        SECOND_PARENT_UNLINKED_COLUMN,
        BIRTH_ORDER_COLUMN,
        PARITY_COLUMN,
        FOREIGN_BORN_COLUMN,
    ):
        assert incumbents[column].isna().all()
    for column in (
        "person_id",
        "year",
        "birth_year",
        "age",
        "household_id",
        "parent_person_id",
        SECOND_PARENT_COLUMN,
        BIRTH_ORDER_COLUMN,
        PARITY_COLUMN,
    ):
        assert str(actual[column].dtype) == "Int64"
    for column in (
        "synthetic_entry",
        *OUT_OF_DOMAIN_COLUMNS.values(),
        FOREIGN_BORN_COLUMN,
    ):
        assert str(actual[column].dtype) == "boolean"


def test_existing_packet_columns_preserve_incumbent_values():
    frame = _frame()
    frame["synthetic_entry"] = [False, True, False, False, False]
    for column in OUT_OF_DOMAIN_COLUMNS.values():
        frame[column] = [False, True, False, False, False]
    frame[PARITY_COLUMN] = pd.Series([2, 3, 4, pd.NA, pd.NA], dtype="Int64")
    frame[FOREIGN_BORN_COLUMN] = [True, False, True, False, True]
    frame["parent_person_id"] = pd.Series(
        [70, 71, pd.NA, pd.NA, pd.NA], dtype="Int64"
    )
    actual = _append(frame, _births([11]))
    assert_frame_equal(
        actual.iloc[: len(frame)][frame.columns], frame, check_dtype=False
    )


def test_existing_object_boolean_packet_columns_become_nullable_without_value_changes():
    frame = _frame()
    columns = (
        "synthetic_entry",
        *OUT_OF_DOMAIN_COLUMNS.values(),
        FOREIGN_BORN_COLUMN,
    )
    for column in columns:
        frame[column] = pd.Series(
            [False, pd.NA, True, False, False], dtype=object
        )
    actual = _append(frame, _births([11]))
    assert_frame_equal(
        actual.iloc[: len(frame)][frame.columns], frame, check_dtype=False
    )
    for column in columns:
        assert str(actual[column].dtype) == "boolean"
        assert actual.iloc[-1][column] == (column != FOREIGN_BORN_COLUMN)


@settings(max_examples=8, deadline=None, derandomize=True)
@given(offset=st.integers(0, 1000))
def test_large_identifiers_and_counts_never_pass_through_float(offset):
    large = 2**53 + 101 + offset * 2
    frame = _frame().iloc[:2].copy()
    frame["person_id"] = pd.Series([large, large + 1], dtype="Int64")
    frame["household_id"] = pd.Series([large + 10, large + 11], dtype="Int64")
    births = _births([large], orders=[large + 20])
    state = pd.DataFrame(
        {
            "person_id": pd.Series([large], dtype="Int64"),
            "spouse_person_id": pd.Series([large + 1], dtype="Int64"),
        }
    )
    context = replace(
        _context(start=large + 100), person_ordinals={large: 0, large + 1: 1}
    )
    actual = _append(frame, births, context, _marital(births, state))
    child = actual.iloc[-1]
    for column, expected in {
        "person_id": large + 100,
        "parent_person_id": large,
        SECOND_PARENT_COLUMN: large + 1,
        "household_id": large + 10,
        BIRTH_ORDER_COLUMN: large + 20,
    }.items():
        assert str(actual[column].dtype) == "Int64"
        assert child[column] == expected


@pytest.mark.parametrize("carried", ["household_id", "weight", "start_weight"])
def test_optional_maternal_columns_are_not_created_when_absent(carried):
    frame = _frame().drop(columns=[carried])
    actual = _append(frame, _births([11]))
    assert carried not in actual


@settings(max_examples=8, deadline=None, derandomize=True)
@given(
    mothers=st.lists(
        st.sampled_from(MOTHERS), unique=True, min_size=1, max_size=3
    ),
    draw=st.integers(0, 6),
)
def test_sealed_materializer_differential_matches_every_filled_column_except_sex(
    mothers, draw
):
    """Compare the independent packet at ``engine/steps.py:451–507``."""
    frame = _frame()
    births = _births(sorted(mothers))
    expected = materialize_maternal_births(
        frame, births, _context(draw=draw), np.random.default_rng(91)
    )
    actual = _append(frame, births, _context(draw=draw))
    columns = [column for column in expected.columns if column != "sex"]
    assert_frame_equal(actual[columns], expected[columns], check_dtype=False)


@settings(max_examples=8, deadline=None, derandomize=True)
@given(
    frame_order=st.permutations(tuple(range(5))),
    birth_order=st.permutations(MOTHERS),
    draw=st.integers(0, 8),
)
def test_packet_is_deterministic_and_invariant_to_roster_and_birth_order(
    frame_order, birth_order, draw
):
    expected = _append(context=_context(draw=draw))
    repeated = _append(context=_context(draw=draw))
    actual = _append(
        _frame().iloc[list(frame_order)],
        _births(birth_order),
        _context(draw=draw),
    )
    assert_frame_equal(expected, repeated)
    assert_frame_equal(_canonical(actual), _canonical(expected))


@settings(max_examples=6, deadline=None, derandomize=True)
@given(year=st.sampled_from([2024, 2025, 2027, 2028]), empty=st.booleans())
def test_no_current_births_copy_without_columns_rows_ids_or_stream_access(
    year, empty
):
    frame = _frame()
    context = replace(_context(), rng_registry=None, person_ordinals={})
    births = pd.DataFrame() if empty else _births([999], year=year)
    actual = _append(frame, births, context)
    assert actual is not frame
    assert_frame_equal(actual, frame)
    assert context.synthetic_id_allocator.next_id == 100


def test_only_the_current_year_is_selected_before_parent_checks():
    births = pd.concat(
        [
            _births([11]),
            _births([999], year=YEAR - 1),
            _births([55], year=YEAR + 1),
        ],
        ignore_index=True,
    )
    actual = _append(births=births)
    assert _children(actual)["parent_person_id"].tolist() == [11]


@settings(max_examples=8, deadline=None, derandomize=True)
@given(draw=st.integers(0, 12))
def test_module_generator_is_unconsumed_and_sex_uses_maternal_tagged_stream(
    draw,
):
    context = _context(draw=draw)
    rng = np.random.default_rng(draw)
    before = deepcopy(rng.bit_generator.state)
    actual = append_newborn_packet(
        _frame(), _births(), context, _marital(), rng, sex_ratio=_pin()
    )
    assert rng.bit_generator.state == before
    children = _children(actual).set_index("parent_person_id")
    for mother in MOTHERS:
        uniform = context.rng_registry.tagged_child_generator(
            context.period_index,
            ProjectionModule.FERTILITY,
            NEWBORN_SEX_STREAM_TAG,
            context.person_ordinals[mother],
        ).random()
        expected = "male" if uniform < _pin().share_male else "female"
        assert children.loc[mother, "sex"] == expected


@settings(max_examples=6, deadline=None, derandomize=True)
@given(percentage=st.integers(20, 80))
def test_sex_threshold_is_strict_at_the_supplied_share(percentage):
    share = percentage / 100

    class ScalarDraw:
        def __init__(self, value):
            self.value = value

        def random(self):
            return self.value

    class Streams:
        def tagged_child_generator(self, period, module, tag, ordinal):
            assert (period, module, tag) == (
                1,
                ProjectionModule.FERTILITY,
                NEWBORN_SEX_STREAM_TAG,
            )
            return ScalarDraw([share, share - 0.01, share + 0.01][ordinal])

    context = replace(_context(), rng_registry=Streams())
    children = _children(_append(context=context, sex_ratio=_pin(share)))
    assert children["sex"].tolist() == ["female", "male", "female"]


@settings(max_examples=10, deadline=None, derandomize=True)
@given(
    draw=st.integers(0, 20),
    shares=st.tuples(st.integers(1, 99), st.integers(1, 99)),
    removed=st.sampled_from(MOTHERS),
)
def test_coupled_sex_is_monotone_and_independent_of_other_births(
    draw, shares, removed
):
    low, high = sorted(value / 100 for value in shares)
    low_children = _children(
        _append(context=_context(draw=draw), sex_ratio=_pin(low))
    ).set_index("parent_person_id")
    high_children = _children(
        _append(context=_context(draw=draw), sex_ratio=_pin(high))
    ).set_index("parent_person_id")
    fewer = _children(
        _append(
            births=_births(
                [mother for mother in MOTHERS if mother != removed]
            ),
            context=_context(draw=draw),
            sex_ratio=_pin(low),
        )
    ).set_index("parent_person_id")
    for mother in MOTHERS:
        if low_children.loc[mother, "sex"] == "male":
            assert high_children.loc[mother, "sex"] == "male"
        if mother != removed:
            assert fewer.loc[mother, "sex"] == low_children.loc[mother, "sex"]


@settings(max_examples=6, deadline=None, derandomize=True)
@given(draw=st.integers(0, 10))
def test_direct_and_registry_streams_make_identical_packets(draw):
    direct = _append(context=_context(draw=draw))
    registered = _append(
        context=_context(draw=draw, registry=ProjectionRNGRegistry)
    )
    assert_frame_equal(direct, registered)


@pytest.mark.parametrize(
    "column", ["parent_person_id", "birth_year", "birth_order"]
)
def test_nonempty_births_require_the_packet_schema(column):
    with pytest.raises(NewbornPacketRefused, match="NEWBORN_PACKET_REFUSED"):
        _append(births=_births([11]).drop(columns=[column]))


@pytest.mark.parametrize("kind", ["absent", "male", "duplicate"])
def test_invalid_mother_births_are_refused_before_ids_are_allocated(kind):
    context = _context()
    births = _births(
        [999] if kind == "absent" else [55] if kind == "male" else [11, 11]
    )
    with pytest.raises(NewbornPacketRefused, match="NEWBORN_PACKET_REFUSED"):
        _append(births=births, context=context)
    assert context.synthetic_id_allocator.next_id == 100


@pytest.mark.parametrize("value", [None, "male", pd.NA])
def test_mother_must_be_explicitly_female(value):
    frame = _frame()
    frame.loc[0, "sex"] = value
    with pytest.raises(NewbornPacketRefused):
        _append(frame, _births([11]))


@pytest.mark.parametrize("column", ["person_id", "year", "age", "sex"])
def test_packet_refuses_a_roster_missing_required_columns(column):
    with pytest.raises(NewbornPacketRefused):
        _append(_frame().drop(columns=[column]), _births([11]))


@pytest.mark.parametrize("kind", ["duplicate", "missing"])
def test_packet_refuses_nonunique_or_missing_roster_identifiers(kind):
    frame = _frame()
    frame.loc[1, "person_id"] = 11 if kind == "duplicate" else pd.NA
    with pytest.raises(NewbornPacketRefused):
        _append(frame, _births([11]))


def test_parent_reader_requires_identifiers_on_nonempty_authoritative_state():
    with pytest.raises(NewbornPacketRefused):
        read_second_parents(
            _frame(),
            [11],
            _marital(state=pd.DataFrame({"status": ["single"]})),
        )


@pytest.mark.parametrize("value", [0, -1, pd.NA, 1.5, "invalid"])
def test_birth_order_must_be_a_positive_integer_count(value):
    births = _births([11])
    births["birth_order"] = [value]
    with pytest.raises(NewbornPacketRefused):
        _append(births=births)


@pytest.mark.parametrize(
    "column,value",
    [
        ("parent_person_id", pd.NA),
        ("parent_person_id", 11.5),
        ("birth_year", 2026.5),
        ("birth_year", "invalid"),
    ],
)
def test_mother_and_year_fields_require_exact_integer_values(column, value):
    births = _births([11])
    births[column] = [value]
    with pytest.raises(NewbornPacketRefused):
        _append(births=births)


@pytest.mark.parametrize("year", [YEAR - 1, pd.NA])
def test_mother_must_be_present_in_the_birth_year(year):
    frame = _frame()
    frame.loc[0, "year"] = year
    with pytest.raises(NewbornPacketRefused):
        _append(frame, _births([11]))


@pytest.mark.parametrize("start", [-(2**63) - 1, 2**63, 100.5, False])
def test_allocator_cannot_leave_the_nullable_integer_namespace(start):
    with pytest.raises(IdOrStreamCollision):
        _append(births=_births([11]), context=_context(start=start))


def test_packet_step_requires_a_callable_parent_reader():
    with pytest.raises(TypeError):
        NewbornPacketStep(_pin(), second_parents=None)


@pytest.mark.parametrize(
    "result",
    [
        {},
        {11: (pd.NA, pd.NA)},
        {11: (44, UNLINKED_PARTNER_UNKNOWN)},
        {11: (pd.NA, "invented_reason")},
        {11: (11, pd.NA)},
        {11: (999, pd.NA)},
    ],
)
def test_custom_parent_reader_cannot_bypass_packet_parent_guards(result):
    context = _context()
    with pytest.raises(NewbornPacketRefused, match="NEWBORN_PACKET_REFUSED"):
        _append(
            births=_births([11]),
            context=context,
            second_parents=lambda *args: result,
        )
    assert context.synthetic_id_allocator.next_id == 100


@pytest.mark.parametrize(
    "missing", ["registry", "ordinal", "allocator", "overlap", "reserved"]
)
def test_missing_or_colliding_ids_and_streams_use_the_named_refusal(missing):
    context = _context()
    if missing == "registry":
        context = replace(context, rng_registry=None)
    elif missing == "ordinal":
        context = replace(context, person_ordinals={})
    elif missing == "allocator":
        context = replace(context, metadata={})
    elif missing == "overlap":
        context = _context(start=11)
    else:
        context = replace(
            context,
            metadata={
                "synthetic_id_allocator": SyntheticPersonIdAllocator(
                    100, frozenset({100})
                )
            },
        )
    with pytest.raises(IdOrStreamCollision, match="ID_OR_STREAM_COLLISION"):
        _append(births=_births([11]), context=context)


def test_callable_step_reads_marital_births_and_supports_materializer_partial():
    births = _births([22])
    marital = _marital(births)
    step = NewbornPacketStep(_pin())
    actual = step(_frame(), _context(), marital, np.random.default_rng(5))
    materializer = partial(append_newborn_packet, sex_ratio=_pin())
    expected = materializer(
        _frame(), births, _context(), marital, np.random.default_rng(5)
    )
    assert_frame_equal(actual, expected)
    assert _children(actual)["parent_person_id"].tolist() == [22]


def _gate_modules(seen):
    def unchanged(frame, *args):
        return frame

    def mortality(frame, context, rng):
        for _, person in frame.iterrows():
            context.person_generator(
                ProjectionModule.MORTALITY, person["person_id"]
            ).random()
            seen.append((context.year, person["person_id"], person["age"]))
        return frame.loc[frame["person_id"].isin(PERSONS)].copy()

    def marital(frame, context, rng):
        mother = MOTHERS[context.year - YEAR]
        return _marital(_births([mother], year=context.year))

    return PeriodModules(
        mortality=mortality,
        aging=advance_age,
        marital_core=marital,
        fertility=NewbornPacketStep(_pin()),
        disability=unchanged,
        earnings=unchanged,
        claiming=unchanged,
        household_composition=unchanged,
    )


@settings(max_examples=4, deadline=None, derandomize=True)
@given(draw=st.integers(0, 5), horizon=st.sampled_from([2027, 2028]))
def test_gate_accounts_labels_delays_mortality_and_repeats_equal_slices(
    draw, horizon
):
    """Births follow mortality in ``engine/loop.py:297–323``."""
    initial = _frame()
    initial["year"] = YEAR - 1
    first_seen, second_seen = [], []
    request = GateRunRequest(horizon=horizon, draw_index=draw)
    first = run_gate(initial, _gate_modules(first_seen), request)
    second = run_gate(initial, _gate_modules(second_seen), request)
    assert first_seen == second_seen
    for actual, expected in zip(
        first.projection.slices, second.projection.slices, strict=True
    ):
        assert_frame_equal(actual, expected)
    births = [
        event
        for event in first.events
        if event.kind == PopulationEventKind.BIRTH
    ]
    deaths = [
        event
        for event in first.events
        if event.kind == PopulationEventKind.DEATH
    ]
    assert len(births) == horizon - (YEAR - 1)
    assert len(deaths) == len(births) - 1
    for period in first.accounting.periods:
        assert period.count_residual == 0
        assert period.weight_residual == 0
        assert period.weights.revaluation.total == 0
    for event in births:
        child = first.projection.slices[event.year - (YEAR - 1)]
        child = child.set_index("person_id").loc[event.person_id]
        assert child["entry_kind"] == "maternal_birth"
        assert child["entry_year"] == event.year
        assert event.entry_kind == "maternal_birth"
        draws = [
            (year, age)
            for year, person, age in first_seen
            if person == event.person_id
        ]
        assert draws == (
            [] if event.year == horizon else [(event.year + 1, 0)]
        )
