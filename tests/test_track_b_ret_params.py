"""R1 statutory conformance and historical-source checks; no population data.

The published-history oracle is extracted directly from captured SSA HTML.
Forecast tests use explicitly labelled synthetic vintages, never that history
as an implicit source of missing inputs. These checks admit listed parameter
years and conditional projections only, not empirical population claims.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import FrozenInstanceError
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from populace_dynamics.track_b.ret_params import (
    ParameterValue,
    ProjectionInputs,
    SourcePin,
    load_ret_parameters,
    project_exempt_amount,
    project_ret_year,
)

DATA = Path(__file__).parent / "data" / "track_b"
CAPTURES = DATA / "ret_sources"
KINDS = ("lower", "higher")
VINTAGE = "synthetic-r1-tests-v1"
SYNTHETIC_PIN = SourcePin(
    url="https://example.org/invented-r1-vintage.json",
    retrieved_at="2026-09-28T00:00:00Z",
    sha256=hashlib.sha256(b"invented R1 projection input").hexdigest(),
)
SYNTHETIC_COLA_PIN = SourcePin(
    url="https://example.org/invented-r1-cola-vintage.json",
    retrieved_at="2026-09-28T00:00:00Z",
    sha256=hashlib.sha256(b"invented R1 COLA input").hexdigest(),
)


def _published_rows(filename):
    """Read numeric table rows without using the implementation's YAML."""
    html = (CAPTURES / filename).read_text()
    html = re.sub(r"<sup>.*?</sup>", "", html, flags=re.DOTALL)
    html = re.sub(r"</?small[^>]*>", "", html)
    result = {}
    for year, tail in re.findall(
        r"<tr[^>]*>\s*<td[^>]*>\s*(\d{4})\s*</td>(.*?)</tr>",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        values = []
        for cell in re.findall(r"<td[^>]*>(.*?)</td>", tail, re.DOTALL):
            cell = re.sub(r"<sup>.*?</sup>", "", cell, flags=re.DOTALL)
            cell = re.sub(r"<[^>]+>", "", cell)
            values.append(Fraction(cell.strip().replace(",", "").strip("$")))
        if values:
            assert int(year) not in result
            result[int(year)] = tuple(values)
    assert result, filename
    return result


@pytest.fixture(scope="module")
def parameters():
    return load_ret_parameters()


@pytest.fixture(scope="module")
def history():
    return _published_rows("ssa_ret_history.html")


def _value(value, *, pin=SYNTHETIC_PIN, status="projected"):
    return ParameterValue(value=value, status=status, sources=(pin,))


def _inputs(*, nawi=None, cola=None, vintage=VINTAGE):
    return ProjectionInputs(
        vintage=vintage,
        nawi={2025: _value("75000")} if nawi is None else nawi,
        december_cola_percent=(
            {2026: _value("2.5", pin=SYNTHETIC_COLA_PIN)}
            if cola is None
            else cola
        ),
    )


def test_every_captured_source_matches_manifest():
    manifest = json.loads((CAPTURES / "manifest.json").read_text())
    assert manifest["schema_version"] == 1
    sources = manifest["sources"]
    assert len(sources) >= 5
    assert len({source["id"] for source in sources}) == len(sources)
    assert {source["file"] for source in sources} == {
        path.name for path in CAPTURES.glob("*.html")
    }
    for source in sources:
        body = (CAPTURES / source["file"]).read_bytes()
        assert len(body) == source["bytes"]
        assert hashlib.sha256(body).hexdigest() == source["sha256"]
        assert source["url"].startswith("https://www.ssa.gov/")
        timestamp = datetime.fromisoformat(
            source["retrieved_at_utc"].replace("Z", "+00:00")
        )
        assert timestamp.utcoffset().total_seconds() == 0


def test_realized_table_covers_entire_captured_history(parameters, history):
    assert set(history) == set(range(2000, 2027))
    assert set(parameters.years) == set(history)


@pytest.mark.parametrize("year", range(2000, 2027))
def test_realized_amounts_equal_ssa_published_history(
    parameters, history, year
):
    actual = parameters.for_year(year)
    assert actual.year == year
    assert actual.lower_exempt_amount.value == history[year][0]
    assert actual.higher_exempt_amount.value == history[year][1]
    assert actual.lower_exempt_amount.status == "realized"
    assert actual.higher_exempt_amount.status == "realized"
    assert actual.vintage is None


def test_history_fixture_is_an_exact_extraction_of_captured_sources(history):
    fixture = json.loads((DATA / "ret_history.json").read_text())
    assert {
        int(year): (Fraction(row["lower"]), Fraction(row["higher"]))
        for year, row in fixture["exempt_amounts"].items()
    } == history
    assert {
        int(year): Fraction(value) for year, value in fixture["nawi"].items()
    } == {
        year: row[0]
        for year, row in _published_rows("ssa_nawi_history.html").items()
    }
    assert {
        int(year): Fraction(value)
        for year, value in fixture["december_cola_percent"].items()
    } == {
        year: row[0]
        for year, row in _published_rows("ssa_cola_history.html").items()
        if year >= 1983
    }


def test_every_realized_value_has_captured_provenance_and_exact_rates(
    parameters,
):
    manifest = json.loads((CAPTURES / "manifest.json").read_text())
    pins = {
        (row["url"], row["retrieved_at_utc"], row["sha256"])
        for row in manifest["sources"]
    }
    for year in parameters.years.values():
        assert year.lower_withholding_rate.value == Fraction(1, 2)
        assert year.higher_withholding_rate.value == Fraction(1, 3)
        for parameter in (
            year.lower_exempt_amount,
            year.higher_exempt_amount,
            year.lower_withholding_rate,
            year.higher_withholding_rate,
        ):
            assert parameter.status == "realized"
            assert parameter.sources
            assert all(
                (pin.url, pin.retrieved_at, pin.sha256) in pins
                for pin in parameter.sources
            )
        assert isinstance(year.higher_withholding_rate.value, Fraction)


@pytest.mark.parametrize("year", range(2003, 2027))
@pytest.mark.parametrize("kind", KINDS)
def test_statutory_projection_backtest_matches_published_history(
    history, year, kind
):
    # This is a historical back-test using published inputs, not a forecast
    # made with information available at an earlier forecasting boundary.
    nawi = _published_rows("ssa_nawi_history.html")
    cola = _published_rows("ssa_cola_history.html")
    column = 0 if kind == "lower" else 1
    actual = project_exempt_amount(
        kind=kind,
        nawi=nawi[year - 2][0],
        prior_amount=int(history[year - 1][column]),
        preceding_december_cola=cola[year - 1][0],
    )
    assert actual == history[year][column]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize(
    ("distance_from_tie", "expected"),
    [(Fraction(-1, 1000), 12000), (0, 12120), (Fraction(1, 1000), 12120)],
)
def test_rounding_to_nearest_120_ties_up(kind, distance_from_tie, expected):
    # A monthly $1005 tie becomes annual $12060. Inputs are derived using
    # exact fractions so no binary floating-point error decides the tie. The
    # prior amount sits below 12000 so the floor cannot mask a rounding bug.
    base_amount, base_nawi = (
        (8040, Fraction("22935.42"))
        if kind == "lower"
        else (30000, Fraction("32154.82"))
    )
    nawi = (12060 + distance_from_tie) * base_nawi / base_amount
    assert (
        project_exempt_amount(
            kind=kind,
            nawi=nawi,
            prior_amount=11880,
            preceding_december_cola="0.1",
        )
        == expected
    )


@pytest.mark.parametrize("kind", KINDS)
def test_no_preceding_december_cola_carries_prior_despite_wage_growth(kind):
    assert (
        project_exempt_amount(
            kind=kind,
            nawi=1000000,
            prior_amount=24000,
            preceding_december_cola=0,
        )
        == 24000
    )


@pytest.mark.parametrize("kind", KINDS)
def test_positive_cola_does_not_override_prior_amount_floor(kind):
    assert (
        project_exempt_amount(
            kind=kind,
            nawi=1,
            prior_amount=24000,
            preceding_december_cola=3,
        )
        == 24000
    )


@given(
    kind=st.sampled_from(KINDS),
    nawi=st.fractions(min_value=1, max_value=1000000, max_denominator=10000),
    prior_multiple=st.integers(min_value=1, max_value=10000),
    cola=st.fractions(min_value=0, max_value=100, max_denominator=1000),
)
def test_projection_floor_rounding_and_determinism(
    kind, nawi, prior_multiple, cola
):
    prior_amount = 120 * prior_multiple
    arguments = dict(
        kind=kind,
        nawi=nawi,
        prior_amount=prior_amount,
        preceding_december_cola=cola,
    )
    actual = project_exempt_amount(**arguments)
    assert isinstance(actual, int)
    assert actual >= prior_amount
    assert actual % 120 == 0
    assert project_exempt_amount(**arguments) == actual
    if cola == 0:
        assert actual == prior_amount


@given(
    kind=st.sampled_from(KINDS),
    wage_a=st.fractions(min_value=1, max_value=1000000, max_denominator=1000),
    wage_b=st.fractions(min_value=1, max_value=1000000, max_denominator=1000),
    prior_multiple=st.integers(min_value=1, max_value=10000),
)
def test_projection_is_monotone_in_nawi(kind, wage_a, wage_b, prior_multiple):
    low, high = sorted((wage_a, wage_b))
    common = dict(
        kind=kind,
        prior_amount=120 * prior_multiple,
        preceding_december_cola=2,
    )
    assert project_exempt_amount(nawi=low, **common) <= project_exempt_amount(
        nawi=high, **common
    )


@pytest.mark.parametrize("year", [1999, 2027, 2050])
def test_missing_parameter_year_raises_instead_of_carrying(parameters, year):
    with pytest.raises(KeyError):
        parameters.for_year(year)


def test_projected_year_keeps_status_exact_rates_vintage_and_sources(
    parameters,
):
    prior = parameters.for_year(2026)
    projected = project_ret_year(prior, _inputs(), permitted_vintage=VINTAGE)
    assert projected.year == 2027
    assert projected.vintage == VINTAGE
    assert projected.lower_exempt_amount.status == "projected"
    assert projected.higher_exempt_amount.status == "projected"
    for kind in KINDS:
        actual = getattr(projected, f"{kind}_exempt_amount")
        previous = getattr(prior, f"{kind}_exempt_amount")
        assert actual.value == project_exempt_amount(
            kind=kind,
            nawi="75000",
            prior_amount=int(previous.value),
            preceding_december_cola="2.5",
        )
        assert SYNTHETIC_PIN in actual.sources
        assert SYNTHETIC_COLA_PIN in actual.sources
        assert set(previous.sources).issubset(actual.sources)
        rate = getattr(projected, f"{kind}_withholding_rate")
        assert rate == getattr(prior, f"{kind}_withholding_rate")
        assert rate.status == "realized"


def test_projection_refuses_unpermitted_vintage(parameters):
    with pytest.raises(ValueError, match="vintage"):
        project_ret_year(
            parameters.for_year(2026),
            _inputs(),
            permitted_vintage="a-different-registered-vintage",
        )


@pytest.mark.parametrize("missing", ["nawi", "cola"])
def test_projection_refuses_missing_input_even_in_realized_history(
    parameters, missing
):
    # Both absent years exist in the published archive, which must never be
    # consulted to repair incomplete forecast-vintage inputs.
    arguments = dict(
        nawi={2024: _value("69846.57")},
        cola={2025: _value("2.8")},
    )
    arguments[missing] = {}
    with pytest.raises(KeyError):
        project_ret_year(
            parameters.for_year(2025),
            _inputs(**arguments),
            permitted_vintage=VINTAGE,
        )


def test_projection_reads_only_target_year_lags(parameters):
    prior = parameters.for_year(2026)
    expected = project_ret_year(prior, _inputs(), permitted_vintage=VINTAGE)
    # Poison future and irrelevant historical years, retaining only t-2
    # wages and t-1 December COLA. Neither changed data can affect t.
    perturbed = _inputs(
        nawi={2024: _value(1), 2025: _value("75000"), 2026: _value(999999)},
        cola={
            2025: _value(0),
            2026: _value("2.5", pin=SYNTHETIC_COLA_PIN),
            2027: _value(99),
        },
    )
    actual = project_ret_year(prior, perturbed, permitted_vintage=VINTAGE)
    assert actual.year == expected.year
    assert actual.vintage == expected.vintage
    for field in (
        "lower_exempt_amount",
        "higher_exempt_amount",
        "lower_withholding_rate",
        "higher_withholding_rate",
    ):
        assert getattr(actual, field) == getattr(expected, field)


def test_projection_uses_preceding_december_not_target_year_cola(parameters):
    inputs = _inputs(cola={2026: _value(0), 2027: _value(20)})
    prior = parameters.for_year(2026)
    result = project_ret_year(prior, inputs, permitted_vintage=VINTAGE)
    assert result.lower_exempt_amount.value == prior.lower_exempt_amount.value
    assert (
        result.higher_exempt_amount.value == prior.higher_exempt_amount.value
    )
    assert result.lower_exempt_amount.status == "projected"


def test_projection_inputs_copy_and_freeze_caller_mappings(parameters):
    wages = {2025: _value("75000")}
    cola = {2026: _value("2.5")}
    inputs = _inputs(nawi=wages, cola=cola)
    expected = project_ret_year(
        parameters.for_year(2026), inputs, permitted_vintage=VINTAGE
    )
    wages[2025] = _value("150000")
    cola.clear()
    assert inputs.nawi[2025].value == 75000
    assert inputs.december_cola_percent[2026].value == Fraction("2.5")
    with pytest.raises(TypeError):
        inputs.nawi[2025] = _value(1)
    with pytest.raises(TypeError):
        inputs.december_cola_percent[2026] = _value(0)
    assert (
        project_ret_year(
            parameters.for_year(2026), inputs, permitted_vintage=VINTAGE
        )
        == expected
    )


def test_parameter_records_and_mapping_are_immutable(parameters):
    prior = parameters.for_year(2026)
    with pytest.raises(TypeError):
        parameters.years[2027] = prior
    with pytest.raises(FrozenInstanceError):
        prior.year = 2027
    with pytest.raises(FrozenInstanceError):
        prior.lower_exempt_amount.value = 1
    with pytest.raises(FrozenInstanceError):
        prior.lower_exempt_amount.sources[0].sha256 = "0" * 64


def test_project_through_preserves_history_and_extends_exactly(parameters):
    inputs = _inputs(
        nawi={2025: _value("75000"), 2026: _value("80000")},
        cola={2026: _value("2.5"), 2027: _value(0)},
    )
    result = parameters.project_through(
        2028, inputs, permitted_vintage=VINTAGE
    )
    assert set(result.years) == set(range(2000, 2029))
    assert set(parameters.years) == set(range(2000, 2027))
    for year in parameters.years:
        assert result.for_year(year) == parameters.for_year(year)
    assert result.for_year(2028).lower_exempt_amount.value == (
        result.for_year(2027).lower_exempt_amount.value
    )
    assert result.for_year(2028).higher_exempt_amount.value == (
        result.for_year(2027).higher_exempt_amount.value
    )
    assert result == parameters.project_through(
        2028, inputs, permitted_vintage=VINTAGE
    )


def test_cannot_continue_projected_path_under_different_vintage(parameters):
    first = project_ret_year(
        parameters.for_year(2026), _inputs(), permitted_vintage=VINTAGE
    )
    different = _inputs(
        nawi={2026: _value("80000")},
        cola={2027: _value(2)},
        vintage="different-vintage",
    )
    with pytest.raises(ValueError, match="vintage"):
        project_ret_year(
            first, different, permitted_vintage="different-vintage"
        )


@pytest.mark.parametrize("changed", ["value", "provenance"])
def test_cannot_replace_input_payload_under_same_vintage_name(
    parameters, changed
):
    wages = {2025: _value("75000"), 2026: _value("80000")}
    cola = {2026: _value(2), 2027: _value(2)}
    inputs = _inputs(nawi=wages, cola=cola)
    first = project_ret_year(
        parameters.for_year(2026), inputs, permitted_vintage=VINTAGE
    )
    assert first.vintage_sha256 == inputs.fingerprint
    wages[2026] = (
        _value("90000")
        if changed == "value"
        else _value("80000", pin=SYNTHETIC_COLA_PIN)
    )
    replacement = _inputs(nawi=wages, cola=cola)
    assert replacement.vintage == inputs.vintage
    assert replacement.fingerprint != inputs.fingerprint
    with pytest.raises(ValueError, match="vintage|fingerprint|payload"):
        project_ret_year(first, replacement, permitted_vintage=VINTAGE)


def test_vintage_fingerprint_is_independent_of_mapping_insertion_order():
    wages = {2025: _value("75000"), 2026: _value("80000")}
    cola = {2026: _value(2), 2027: _value(3)}
    first = _inputs(nawi=wages, cola=cola)
    second = _inputs(
        nawi=dict(reversed(tuple(wages.items()))),
        cola=dict(reversed(tuple(cola.items()))),
    )
    assert first.fingerprint == second.fingerprint


def test_projection_refuses_years_before_indexed_higher_amount(parameters):
    with pytest.raises(ValueError):
        project_ret_year(
            parameters.for_year(2001),
            _inputs(nawi={2000: _value("32154.82")}, cola={2001: _value(2)}),
            permitted_vintage=VINTAGE,
        )


@pytest.mark.parametrize(
    "override",
    [
        {"kind": "unknown"},
        {"nawi": -1},
        {"nawi": 0},
        {"nawi": 75000.0},
        {"nawi": float("nan")},
        {"nawi": True},
        {"prior_amount": -120},
        {"prior_amount": 0},
        {"prior_amount": 24001},
        {"prior_amount": Fraction(24000)},
        {"preceding_december_cola": -1},
        {"preceding_december_cola": float("inf")},
    ],
)
def test_projection_refuses_invalid_values(override):
    arguments = dict(
        kind="lower",
        nawi="75000",
        prior_amount=24000,
        preceding_december_cola=2,
    )
    arguments.update(override)
    with pytest.raises((TypeError, ValueError)):
        project_exempt_amount(**arguments)


def test_zero_cola_does_not_hide_missing_wage_year(parameters):
    with pytest.raises(KeyError):
        project_ret_year(
            parameters.for_year(2026),
            _inputs(nawi={}, cola={2026: _value(0)}),
            permitted_vintage=VINTAGE,
        )


@pytest.mark.parametrize("override", [{"status": "unknown"}, {"sources": ()}])
def test_every_parameter_requires_status_and_provenance(override):
    arguments = dict(value=120, status="realized", sources=(SYNTHETIC_PIN,))
    arguments.update(override)
    with pytest.raises(ValueError):
        ParameterValue(**arguments)
