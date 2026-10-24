"""Exact null arithmetic and narrow approved baseline input extraction."""

import json
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.acola_track.nulls import (
    CONTEXT_CAPTION,
    NULLS_PATH,
    VC1_CAPTION,
    VC1_COLUMN,
    build_nulls,
    context_beneficiary_count,
    extract_context_count,
    extract_tr2026_rates,
    nulls_for_run,
    spec_null,
    tr2026_inputs,
)


@given(
    st.lists(st.integers(10, 1000), min_size=1, max_size=25),
    st.integers(1, 10),
)
@settings(deadline=None)
def test_null_is_exact_product_with_factors_less_than_one(rates, reduction):
    c = [Fraction(x, 1000) for x in rates]
    r = Fraction(reduction, 1000)
    product = Fraction(1)
    for rate in c:
        factor = (1 + rate - r) / (1 + rate)
        assert 0 < factor < 1
        product *= factor
    assert spec_null(c, r) == 100 * (product - 1)
    assert -100 < spec_null(c, r) < 0


@given(st.lists(st.integers(0, 1000), min_size=0, max_size=25))
@settings(deadline=None)
def test_zero_reform_is_exactly_zero(rates):
    assert spec_null([Fraction(x, 1000) for x in rates], 0) == 0


@given(st.integers(10, 1000), st.integers(1, 20))
@settings(deadline=None)
def test_more_reduced_increases_strictly_lowers_the_null(rate, count):
    rates = [Fraction(rate, 1000)] * count
    assert spec_null(rates + [rates[0]]) < spec_null(rates)


@given(st.integers(10, 1000), st.integers(1, 9))
@settings(deadline=None)
def test_larger_reduction_lowers_null_and_larger_cola_raises_it(rate, r):
    c = Fraction(rate, 1000)
    reduction = Fraction(r, 1000)
    assert spec_null([c], reduction + Fraction(1, 1000)) < spec_null(
        [c], reduction
    )
    assert spec_null([c + Fraction(1, 1000)], reduction) > spec_null(
        [c], reduction
    )


@pytest.mark.parametrize(
    "rates,reduction", [([-1], 0.01), ([0], 0.01), ([0.03], -0.01)]
)
def test_invalid_or_refused_null_inputs(rates, reduction):
    with pytest.raises(ValueError):
        spec_null(rates, reduction)


def _cola_table():
    groups = []
    for group, rate in [("Intermediate:", "2.7"), ("Low-cost:", "9.9")]:
        groups.append(f'<tr><th colspan="2">{group}</th></tr>')
        groups.extend(
            f"<tr><td>{year}</td><td>{rate}</td></tr>"
            for year in (2027, 2028, 2029)
        )
    return (
        f"<table><caption>{VC1_CAPTION}</caption>"
        '<tr><th rowspan="2">Calendar year</th>'
        f'<th rowspan="2">{VC1_COLUMN}</th></tr><tr></tr>'
        + "".join(groups)
        + "</table>"
    ).encode()


def test_literal_labels_select_only_registered_years_and_intermediate_cola():
    result = extract_tr2026_rates(_cola_table())
    assert list(result["cells"]) == ["2027", "2028", "2029"]
    assert all(c["rate"] == "0.027" for c in result["cells"].values())
    assert result["cells"]["2027"]["row_header_path"] == [
        "Intermediate:",
        "2027",
    ]


@pytest.mark.parametrize(
    "before,after",
    [
        ("Intermediate:", "Wrong assumption:"),
        (VC1_CAPTION, "Wrong table"),
        (VC1_COLUMN, "Wrong column"),
        ("2029", "2039"),
    ],
)
def test_cola_extractor_refuses_changed_source_identity(before, after):
    with pytest.raises(ValueError):
        extract_tr2026_rates(
            _cola_table().replace(before.encode(), after.encode())
        )


def test_context_extractor_returns_only_one_count_and_no_other_values():
    raw = (
        f"<table><caption>{CONTEXT_CAPTION}</caption>"
        '<tr><th rowspan="2">Calendar year</th>'
        '<th colspan="2">Beneficiaries b (in thousands)</th></tr>'
        "<tr><th>DI</th><th>OASDI c</th></tr>"
        '<tr><th colspan="3">Historical data:</th></tr>'
        "<tr><td>2030</td><td>111</td><td>222</td></tr>"
        '<tr><th colspan="3">Intermediate:</th></tr>'
        "<tr><td>2030</td><td>333</td><td>12,345</td></tr></table>"
    ).encode()
    result = extract_context_count(raw)
    assert result["beneficiary_count"] == 12_345_000
    assert result["as_published"] == "12,345"
    assert result["scaling_applied_to_model"] is False
    assert not any(str(x) in json.dumps(result) for x in (111, 222, 333))


def test_committed_nulls_reproduce_exactly_from_pinned_inputs():
    assert json.loads(NULLS_PATH.read_bytes()) == build_nulls()
    result = build_nulls()
    assert result["N"]["factor_count"] == 3
    assert result["N_model"]["factor_count"] == 3
    assert result["N_MINT"]["factor_count"] == 19
    assert result["N_M1"]["factor_count"] == 20
    assert result["N_M1"]["value"] < result["N_MINT"]["value"]
    assert result["N_MINT"]["value"] < result["N_model"]["value"] < 0
    assert result["december_null_registered"] is False
    for name in ("N", "N_model", "N_MINT", "N_M1"):
        exact = result[name]["exact"]
        rational = Fraction(int(exact["numerator"]), int(exact["denominator"]))
        assert float(rational) == result[name]["value"]
        assert float(Decimal(result[name]["value_decimal"])) == float(rational)
    json.dumps(result, allow_nan=False)


def test_build_zero_reform_nulls_are_all_exactly_zero():
    result = build_nulls(annual_reduction=0)
    for name in ("N", "N_model", "N_MINT", "N_M1", "N_minus_N_model"):
        assert result[name]["value"] == 0
        assert result[name]["exact"] == {"numerator": "0", "denominator": "1"}


def test_runtime_nulls_follow_the_same_invented_baseline_as_benefits():
    baseline = SimpleNamespace(rate_for_determination_year=lambda year: 0.04)
    result = nulls_for_run(baseline)
    expected = spec_null([Fraction(4, 100)] * 19)
    assert result["N_MINT"]["value"] == float(expected)
    assert (
        result["inputs"]["model_TR2008"]["runtime_matches_committed_tr2008"]
        is False
    )
    assert result["N"]["value"] == build_nulls()["N"]["value"]
    assert len(result["committed_file_sha256"]) == 64
    zero = nulls_for_run(baseline, annual_reduction=0)
    assert all(
        zero[key]["value"] == 0 for key in ("N", "N_model", "N_MINT", "N_M1")
    )


def test_approved_context_snapshot_has_a_pinned_single_cell_provenance():
    context = context_beneficiary_count()
    assert context["row_header_path"] == ["Intermediate:", "2030"]
    assert context["column_header_path"][-1] == "OASDI c"
    assert context["beneficiary_count"] > 0
    inputs = tr2026_inputs()
    assert inputs["fallback_used"] is False
    assert inputs["table"] == "Table V.C1"
