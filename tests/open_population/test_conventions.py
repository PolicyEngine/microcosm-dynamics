"""Invented conventions for the demographic phase's shared inputs (§§5.4, 8)."""

import math
from types import MappingProxyType

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from populace_dynamics.baselines.fertility import ASFR_STREAM_TAG
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.open_population.conventions import (
    BIRTH_ORDER_COLUMN,
    LIVE_FERTILITY_STREAM_TAG,
    NEWBORN_SEX_STREAM_TAG,
    OUT_OF_DOMAIN_COLUMNS,
    PARITY_COLUMN,
    SECOND_PARENT_COLUMN,
    SECOND_PARENT_UNLINKED_COLUMN,
    SPOUSE_ABROAD_COLUMN,
    SPOUSE_ABROAD_YEAR_COLUMN,
    ComponentControls,
    ControlDirection,
    ControlUniverse,
    ConventionSource,
    ConventionStatus,
    ExitTimingConvention,
)
from populace_dynamics.open_population.errors import (
    ControlSourceUnavailable,
    TimingBridgeUnresolved,
    UniverseBridgeUnresolved,
)
from populace_dynamics.open_population.exits import EMIGRATION_STREAM_TAG
from populace_dynamics.open_population.streams import DirectRNGStreams

INVENTED = ConventionSource("invented fixture", ConventionStatus.INVENTED)
_AMOUNT = st.floats(min_value=0, max_value=1e6, allow_nan=False)
_PROBABILITY = st.floats(min_value=0, max_value=1, allow_nan=False)


def _controls(thousands, universe=ControlUniverse.RESIDENT_ROSTER):
    return ComponentControls(
        thousands, ControlDirection.OUTFLOW, universe, INVENTED
    )


@pytest.mark.parametrize("record", ("", "  ", 3, None))
def test_source_needs_a_named_record(record):
    with pytest.raises(ValueError, match="named source"):
        ConventionSource(record, ConventionStatus.PROPOSED)


def test_source_status_is_the_enum_and_not_its_text():
    with pytest.raises(TypeError, match="ConventionStatus"):
        ConventionSource("a record", "frozen")


@pytest.mark.parametrize(
    "status", (ConventionStatus.INVENTED, ConventionStatus.PROPOSED)
)
def test_only_a_frozen_source_passes(status):
    source = ConventionSource("a record", status)
    with pytest.raises(
        TimingBridgeUnresolved,
        match=rf"^TIMING_BRIDGE_UNRESOLVED: the bridge stays {status.value}",
    ):
        source.require_frozen(TimingBridgeUnresolved, "the bridge")
    ConventionSource("a record", ConventionStatus.FROZEN).require_frozen(
        TimingBridgeUnresolved, "the bridge"
    )


@pytest.mark.parametrize(
    "thousands",
    (
        {},
        {2030: 1.0},
        {(2030, "a", "b"): 1.0},
        {(True, "a"): 1.0},
        {(2030.0, "a"): 1.0},
        {(2030, ""): 1.0},
        {(2030, 7): 1.0},
        {(2030, "a"): -1.0},
        {(2030, "a"): math.nan},
        {(2030, "a"): math.inf},
        {(2030, "a"): True},
        {(2030, "a"): "1"},
    ),
)
def test_controls_refuse_a_malformed_table(thousands):
    with pytest.raises(ValueError):
        _controls(thousands)


@pytest.mark.parametrize(
    "bad",
    (
        {"direction": "outflow"},
        {"universe": "resident_roster"},
        {"source": "a record"},
    ),
)
def test_controls_refuse_untyped_labels(bad):
    fields = {
        "thousands": {(2030, "a"): 1.0},
        "direction": ControlDirection.OUTFLOW,
        "universe": ControlUniverse.RESIDENT_ROSTER,
        "source": INVENTED,
    }
    with pytest.raises(TypeError):
        ComponentControls(**{**fields, **bad})


def test_controls_copy_their_table():
    table = {(np.int64(2031), "b"): 2.0, (2030, "b"): 1.0}
    controls = _controls(table)
    table[(2030, "b")] = 9.0
    assert isinstance(controls.thousands, MappingProxyType)
    assert list(controls.thousands.items()) == [
        ((2030, "b"), 1.0),
        ((2031, "b"), 2.0),
    ]
    assert all(type(year) is int for year, _ in controls.thousands)


def test_a_known_zero_differs_from_a_missing_row():
    controls = _controls(
        {(2030, "a"): 0.0, (2030, "b"): 1.0, (2031, "b"): 1.0}
    )
    assert controls.for_year(2030) == {"a": 0.0, "b": 1.0}
    with pytest.raises(
        ControlSourceUnavailable,
        match=r"^CONTROL_SOURCE_UNAVAILABLE: no control for \['a'\] in 2031",
    ):
        controls.for_year(2031)
    with pytest.raises(ControlSourceUnavailable, match=r"\['a', 'b'\]"):
        controls.total(2032)


def test_controls_refuse_another_universe_by_name():
    area = _controls(
        {(2030, "a"): 1.0}, universe=ControlUniverse.SOCIAL_SECURITY_AREA
    )
    area.require_universe(ControlUniverse.SOCIAL_SECURITY_AREA)
    with pytest.raises(
        UniverseBridgeUnresolved,
        match=r"^UNIVERSE_BRIDGE_UNRESOLVED: these controls count social",
    ):
        area.require_universe(ControlUniverse.RESIDENT_ROSTER)


@settings(max_examples=60, deadline=None)
@given(
    amounts=st.dictionaries(
        st.tuples(st.integers(1940, 2100), st.sampled_from("abc")),
        _AMOUNT,
        min_size=1,
        max_size=12,
    ),
    factor=st.floats(min_value=0.25, max_value=4),
)
def test_a_complete_year_totals_its_components_and_scales(amounts, factor):
    """Any table round-trips, and scaling its rows scales each total."""
    controls = _controls(amounts)
    assert set(controls.thousands) == set(amounts)
    scaled = _controls({key: value * factor for key, value in amounts.items()})
    for year in controls.years():
        names = controls.components()
        assume(all((year, name) in amounts for name in names))
        assert controls.total(year) == math.fsum(
            amounts[(year, name)] for name in names
        )
        assert scaled.total(year) == pytest.approx(
            controls.total(year) * factor, rel=1e-12, abs=1e-12
        )


@pytest.mark.parametrize("share", (-0.1, 1.1, math.nan, math.inf, True, "1"))
def test_exit_share_lies_in_the_unit_interval(share):
    with pytest.raises(ValueError):
        ExitTimingConvention(share, INVENTED)


def test_exit_convention_needs_a_source():
    with pytest.raises(TypeError, match="ConventionSource"):
        ExitTimingConvention(0.5, "a record")


@pytest.mark.parametrize(
    "annual", ([-0.1], [1.1], [math.nan], [math.inf]), ids=str
)
def test_entry_year_probability_refuses_an_annual_outside_the_interval(annual):
    with pytest.raises(ValueError, match="annual exit"):
        ExitTimingConvention(0.5, INVENTED).entry_year_probability(annual)


@settings(max_examples=100, deadline=None)
@given(annual=st.lists(_PROBABILITY, min_size=1, max_size=20))
def test_share_ends_give_no_risk_and_the_full_year(annual):
    """Each end returns its exact value, a certainty included."""
    probabilities = np.asarray(annual)
    none = ExitTimingConvention(0, INVENTED)
    full = ExitTimingConvention(1, INVENTED)
    assert (none.entry_year_probability(probabilities) == 0).all()
    assert (full.entry_year_probability(probabilities) == probabilities).all()


@settings(max_examples=150, deadline=None)
@given(
    low=_PROBABILITY,
    high=_PROBABILITY,
    small=_PROBABILITY,
    large=_PROBABILITY,
)
def test_entry_year_probability_stays_bounded_and_monotone(
    low, high, small, large
):
    """It never tops the annual figure, and rises with annual and share."""
    low, high = sorted((low, high))
    small, large = sorted((small, large))
    less = ExitTimingConvention(small, INVENTED)
    more = ExitTimingConvention(large, INVENTED)
    results = less.entry_year_probability(np.asarray([low, high]))
    assert ((results >= 0) & (results <= [low, high])).all()
    # One unit of rounding is all the composed exp and log functions can lose.
    assert results[0] <= results[1] + 1e-15
    assert results[1] <= more.entry_year_probability([high])[0] + 1e-15


def test_a_certain_exit_stays_certain_at_any_positive_share():
    convention = ExitTimingConvention(0.25, INVENTED)
    with np.errstate(all="raise"):
        assert convention.entry_year_probability([1.0])[0] == 1.0


def test_entry_year_probability_reads_a_constant_hazard():
    """Exposure over half a year, twice over, gives the annual risk back."""
    half = ExitTimingConvention(0.5, INVENTED)
    once = half.entry_year_probability([0.36])[0]
    assert once == pytest.approx(0.2)
    assert 1 - (1 - once) ** 2 == pytest.approx(0.36)


def test_shared_columns_are_distinct():
    columns = (
        PARITY_COLUMN,
        BIRTH_ORDER_COLUMN,
        SECOND_PARENT_COLUMN,
        SECOND_PARENT_UNLINKED_COLUMN,
        SPOUSE_ABROAD_COLUMN,
        SPOUSE_ABROAD_YEAR_COLUMN,
        *OUT_OF_DOMAIN_COLUMNS.values(),
    )
    assert len(set(columns)) == len(columns)
    assert set(OUT_OF_DOMAIN_COLUMNS) == {
        "marital",
        "fertility",
        "disability",
        "earnings",
        "claiming",
    }


def test_stream_tags_are_distinct():
    tags = (
        ASFR_STREAM_TAG,
        EMIGRATION_STREAM_TAG,
        NEWBORN_SEX_STREAM_TAG,
        LIVE_FERTILITY_STREAM_TAG,
    )
    assert len(set(tags)) == len(tags)


@pytest.mark.parametrize(
    "tag", (NEWBORN_SEX_STREAM_TAG, LIVE_FERTILITY_STREAM_TAG)
)
def test_both_stream_classes_serve_a_shared_tag_alike(tag):
    """The sealed registry and OP1's direct class draw the same numbers."""
    registry = ProjectionRNGRegistry(0, 3)
    direct = DirectRNGStreams(0, 3)
    for ordinal in (0, 7):
        expected = registry.tagged_child_generator(
            2, ProjectionModule.FERTILITY, tag, ordinal
        ).random(3)
        actual = direct.tagged_child_generator(
            2, ProjectionModule.FERTILITY, tag, ordinal
        ).random(3)
        assert (expected == actual).all()
