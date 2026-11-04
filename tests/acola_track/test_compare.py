"""Registration 18 comparison rules, using wholly invented source values."""

from __future__ import annotations

import ast
import decimal
import hashlib
import importlib.util
import itertools
import json
import re
import sys
from collections import Counter
from copy import deepcopy
from decimal import ROUND_HALF_UP, Decimal, getcontext, localcontext
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "_compare_acola", ROOT / "scripts" / "compare_acola.py"
)
compare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compare)
D = Decimal


def invented_cell(**changes):
    cell = {
        "html_display": "-7.3",
        "html_value": "-7.3",
        "html_decimals": 1,
        "xlsx_cell": "D7",
        "xlsx_raw": "-0.073200000000000001",
        "xlsx_number_format": "0.0%",
        "xlsx_value_pct": "-7.3200000000000001",
        "xlsx_decimals_pct": 16,
        "pdf_display": "-7.3",
    }
    cell.update(changes)
    return cell


def invented_comparator():
    """Schema-only fixture; these values describe no published comparator."""
    timing = {
        "reading": "not_stated",
        "evidence_verbatim": "INVENTED timing note",
        "evidence_source": "invented.txt",
    }
    return {
        "schema_version": "acola-comparator-v1",
        "producer": "invented",
        "sources": {},
        "oact": {
            "footer_verbatim": compare.OACT_FOOTER + ".",
            "footer_matches_registration": True,
            "provision_text_matches_registration": True,
            "row_label_verbatim": "2030",
            "columns": [
                {
                    "key": key,
                    "header_verbatim": "INVENTED " + key,
                    "display": value,
                    "value": value,
                    "decimals": 2,
                }
                for key, value in (
                    ("proposal_cost_rate", "21.75"),
                    ("change_cost_rate", "-0.75"),
                    ("proposal_income_rate", "18.25"),
                    ("change_income_rate", "-0.25"),
                )
            ],
            "prints_oasi_di_split_2030": False,
            "cost_includes_admin_expenses": "yes",
            "cost_includes_railroad_interchange": "yes",
            "december_2030_timing": timing,
        },
        "pwbm": {
            "last_modified": "INVENTED",
            "last_modified_matches_registration": True,
            "row_2030": {
                "year": "2030",
                "Baseline income rate": "14.000000",
                "Baseline cost rate": "25.000000",
                "A1 income rate": "13.500000",
                "A1 cost rate": "24.000000",
            },
            "stored_decimals": {
                key: 6
                for key in (
                    "Baseline income rate",
                    "Baseline cost rate",
                    "A1 income rate",
                    "A1 cost rate",
                )
            },
            "prints_oasi_di_split_2030": False,
            "cost_includes_admin_expenses": "not_stated",
            "cost_includes_railroad_interchange": "not_stated",
            "december_2030_timing": timing,
        },
        "mint5": {
            "table1": {
                "rows": {
                    band: {
                        "median_diff_pct": invented_cell(),
                        "median_diff_dollars": None,
                        "median_monthly_scheduled": {"html_value": "1600"},
                        "median_monthly_option": {"html_value": "1500"},
                        "median_monthly_payable": None,
                        "pct_population_affected": {"html_value": "75"},
                    }
                    for band in compare.BANDS
                }
            },
            "table2": {"rows": {"Total": {"invented_memo": None}}},
            "median_type": "median_of_individual_differences",
            "start_date_reading": "unsettled",
            "december_2030_timing": timing,
            "prints_oasi_di_split": False,
        },
    }


def invented_summary(mean=-5):
    return {
        "mean": mean,
        "sample_sd": 0.125,
        "per_draw": [mean, mean],
        "floor": {
            "mean": None,
            "defined": False,
            "undefined_reason": "INVENTED empty half",
        },
        "undefined_reason": None if mean is not None else "empty band",
    }


def invented_artifact():
    summary = invented_summary()
    mint_stats = {stat: deepcopy(summary) for stat in compare.MINT_STATISTICS}
    mint_stats.update(
        {
            key: invented_summary(1000)
            for key in (
                "baseline_falling_share",
                "median_benefit_base",
                "median_benefit_reform",
            )
        }
    )
    rows = {
        row: {"statistics": {"P": deepcopy(summary)}} for row in ("C0", "C1")
    }
    rows.update(
        {
            row: {
                "bands": {
                    band: {"statistics": deepcopy(mint_stats)}
                    for band in compare.BANDS
                }
            }
            for row in ("M0", "M1", "M2", "M3", "M4")
        }
    )
    return {
        "schema_version": "acola-track-v1",
        "rows": rows,
        "nulls": {
            key: {"value": value}
            for key, value in (
                ("N", -3),
                ("N_model", -2),
                ("N_MINT", -17),
                ("N_M1", -18),
            )
        },
        "deferred_rows": {
            "C0-D": {"status": "deferred", "reason": "INVENTED"}
        },
    }


def write_inputs(tmp_path, artifact=None, comparator=None):
    artifact_path, record_path = (
        tmp_path / "invented.json",
        tmp_path / "reconciled.json",
    )
    artifact_path.write_text(json.dumps(artifact or invented_artifact()))
    sidecar = {
        "artifact": artifact_path.name,
        "artifact_sha256": hashlib.sha256(
            artifact_path.read_bytes()
        ).hexdigest(),
    }
    artifact_path.with_suffix(".env.json").write_text(json.dumps(sidecar))
    record_path.write_text(json.dumps(comparator or invented_comparator()))
    extra = tmp_path / "invented.txt"
    extra.write_text("INVENTED source bytes")
    files = {
        path.name: {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        for path in (record_path, extra)
    }
    seal = tmp_path / "seal.json"
    seal.write_text(json.dumps({"files": files}))
    return artifact_path, record_path, seal


def test_oact_conversion_uses_proposal_minus_change_and_decimal_corners():
    result = compare.oact_comparison(invented_comparator()["oact"])
    with localcontext() as context:
        context.prec = compare.PRECISION
        assert result["value"]["point"] == D(100) * D("-0.75") / D("22.50")
    assert result["current_law_cost_rate"] == D("22.50")
    assert (
        result["value"]["lower"]
        < result["value"]["point"]
        < result["value"]["upper"]
    )
    assert result["precision_gate"] == "OACT_primary_PWBM_secondary"
    assert result["income_rate_memo"]["change_income_rate"]["value"] == "-0.25"


@given(
    p=st.integers(1, 10000), d=st.integers(-1000, 0), places=st.integers(1, 5)
)
@settings(max_examples=60, deadline=None)
def test_oact_corners_contain_point_and_monotonicity(p, d, places):
    record = invented_comparator()["oact"]
    record["columns"][0].update(value=str(p), decimals=places)
    record["columns"][1].update(value=str(d), decimals=places)
    interval = compare.oact_comparison(record)["value"]
    assert interval["lower"] <= interval["point"] <= interval["upper"]
    with localcontext() as context:
        context.prec = compare.PRECISION
        proposal, change, delta = D(p), D(d), D("0.001")
        base = compare._oact_formula(proposal, change)
        assert compare._oact_formula(proposal, change + delta) >= base
        assert compare._oact_formula(proposal + delta, change) >= base


@pytest.mark.parametrize(
    "value,expected",
    [
        ("-0.09", "PWBM_primary_OACT_report_only"),
        ("-0.10", "OACT_primary_PWBM_secondary"),
    ],
)
def test_oact_precision_gate_boundary(value, expected):
    record = invented_comparator()["oact"]
    record["columns"][1]["value"] = value
    assert compare.oact_comparison(record)["precision_gate"] == expected
    record["columns"][1]["value"] = "-0.09999999999999999999999999999999999"
    assert (
        compare.oact_comparison(record)["precision_gate"]
        == "PWBM_primary_OACT_report_only"
    )


def test_oact_decimals_are_not_hard_coded_and_every_corner_positive():
    record = invented_comparator()["oact"]
    record["columns"][0]["decimals"] = 0
    wider = compare.oact_comparison(record)["value"]
    original = compare.oact_comparison(invented_comparator()["oact"])["value"]
    assert wider["lower"] < original["lower"]
    assert wider["upper"] > original["upper"]
    record["columns"][0].update(value="0.01", decimals=2)
    record["columns"][1].update(value="0", decimals=0)
    with pytest.raises(ValueError, match="every corner"):
        compare.oact_comparison(record)


def test_oact_wrong_year_refuses():
    record = invented_comparator()["oact"]
    record["row_label_verbatim"] = "2031"
    with pytest.raises(ValueError, match="2030"):
        compare.oact_comparison(record)


@pytest.mark.parametrize(
    "bd,rd,branch",
    [
        (6, 6, "point"),
        (15, 15, "point"),
        (5, 6, "four_corners"),
        (6, 5, "four_corners"),
    ],
)
def test_pwbm_decimal_branches_and_point_containment(bd, rd, branch):
    record = invented_comparator()["pwbm"]
    record["stored_decimals"].update(
        {"Baseline cost rate": bd, "A1 cost rate": rd}
    )
    result = compare.pwbm_comparison(record)
    value = result["value"]
    assert result["branch"] == branch
    assert value["point"] == -4
    assert value["lower"] <= value["point"] <= value["upper"]
    assert (value["lower"] == value["upper"]) == (branch == "point")


@given(b=st.integers(1, 10000), r=st.integers(0, 10000))
@settings(max_examples=50, deadline=None)
def test_pwbm_corner_interval_contains_point(b, r):
    record = invented_comparator()["pwbm"]
    record["row_2030"].update(
        {"Baseline cost rate": str(b), "A1 cost rate": str(r)}
    )
    record["stored_decimals"].update(
        {"Baseline cost rate": 2, "A1 cost rate": 2}
    )
    value = compare.pwbm_comparison(record)["value"]
    assert value["lower"] <= value["point"] <= value["upper"]


def test_pwbm_refuses_nonpositive_corner_and_wrong_year():
    record = invented_comparator()["pwbm"]
    record["row_2030"]["Baseline cost rate"] = "0.001"
    record["stored_decimals"]["Baseline cost rate"] = 0
    with pytest.raises(ValueError, match="every corner"):
        compare.pwbm_comparison(record)
    record["row_2030"]["year"] = "2029"
    with pytest.raises(ValueError, match="2030"):
        compare.pwbm_comparison(record)


def test_mint_shortest_reading_S_and_literal_sensitivity_L():
    shortest = compare.mint_interval(invented_cell())
    literal = compare.mint_interval(invented_cell(), "L")
    assert shortest["branch"] == literal["branch"] == "xlsx"
    assert shortest["value"]["point"] == D("-7.32")
    assert shortest["stored_decimals_pct"] == 2
    assert literal["value"]["point"] == D("-7.3200000000000001")
    assert literal["stored_decimals_pct"] == 16
    assert shortest["matching_modes"] == ["half_up", "half_even"]
    assert shortest["value"]["lower"] == D("-7.325")
    assert shortest["value"]["upper"] == D("-7.315")


@pytest.mark.parametrize(
    "raw,html,expected_modes",
    [("-0.0725", "-7.3", ["half_up"]), ("-0.0725", "-7.2", ["half_even"])],
)
def test_negative_tie_discloses_agreeing_modes(raw, html, expected_modes):
    result = compare.mint_interval(
        invented_cell(xlsx_raw=raw, html_value=html)
    )
    assert result["branch"] == "xlsx"
    assert result["matching_modes"] == expected_modes


@pytest.mark.parametrize(
    "changes,point,branch",
    [
        ({"xlsx_raw": "-0.073"}, D("-7.3"), "html"),
        ({"xlsx_raw": "-0.0853"}, D("-7.3"), "html"),
        ({"xlsx_raw": None}, D("-7.3"), "html"),
        ({"xlsx_number_format": None}, D("-7.3"), "html"),
        (
            {"xlsx_raw": "-7.32", "xlsx_number_format": "0.00"},
            D("-7.32"),
            "xlsx",
        ),
        (
            {"xlsx_raw": "-7.32", "xlsx_number_format": '0.00"%"'},
            D("-7.32"),
            "xlsx",
        ),
        (
            {"xlsx_raw": "-7.32", "xlsx_number_format": "0.00\\%"},
            D("-7.32"),
            "xlsx",
        ),
        ({"xlsx_raw": "-7.32e-2"}, D("-7.32"), "xlsx"),
    ],
)
def test_mint_interval_branches_and_formats(changes, point, branch):
    result = compare.mint_interval(invented_cell(**changes))
    assert result["branch"] == branch
    assert result["value"]["point"] == point


def test_literal_branch_uses_recorded_count_and_fallback():
    cell = invented_cell(xlsx_value_pct="-7.35", xlsx_decimals_pct=2)
    assert compare.mint_interval(cell, "L")["branch"] == "html"
    cell["xlsx_value_pct"] = None
    assert compare.mint_interval(cell, "L")["missing_xlsx"] is True


def test_reading_s_counts_no_decimal_for_an_integral_stored_double():
    """Review r1b finding 1: repr's ".0" is not a stored decimal.

    INVENTED cell values. Under a non-percent format the shortest string
    of the double -17.0 is "-17", with no decimal, so the HTML display is
    registered, and reading L with the same count agrees.
    """
    cell = {
        "html_value": "-17",
        "html_decimals": 0,
        "xlsx_raw": "-17",
        "xlsx_number_format": "0",
    }
    shortest = compare.mint_interval(cell)
    assert shortest["branch"] == "html"
    assert shortest["stored_decimals_pct"] == 0
    assert shortest["stored_value_pct"] == D("-17")
    assert (shortest["value"]["lower"], shortest["value"]["upper"]) == (
        D("-17.5"),
        D("-16.5"),
    )
    literal = compare.mint_interval(
        {**cell, "xlsx_value_pct": "-17", "xlsx_decimals_pct": 0}, "L"
    )
    assert literal["branch"] == "html"
    assert literal["value"] == shortest["value"]
    finer = compare.mint_interval(
        {**cell, "html_value": "-17.0", "html_decimals": 1}
    )
    assert finer["branch"] == "html"
    assert finer["stored_decimals_pct"] == 0
    assert (finer["value"]["lower"], finer["value"]["upper"]) == (
        D("-17.05"),
        D("-16.95"),
    )


@st.composite
def invented_shortest_decimals(draw):
    """INVENTED decimal strings, each the shortest form of its double.

    At most 15 significant digits survive a round trip through a binary64
    double, so ``repr`` of the double has exactly these digits (and a
    ".0" when the value is integral). No zero ends a fraction.
    """
    places = draw(st.integers(0, 10))
    if places:
        coefficient = 10 * draw(st.integers(0, 10**14 - 1)) + draw(
            st.integers(1, 9)
        )
    else:
        coefficient = draw(st.integers(0, 10**15 - 1))
    sign = draw(st.sampled_from((1, -1)))
    return format(D(sign * coefficient).scaleb(-places), "f")


@given(
    text=invented_shortest_decimals(),
    percent=st.booleans(),
    html_places=st.integers(0, 6),
)
@settings(max_examples=300, deadline=None)
def test_reading_s_counts_the_shortest_string_of_the_stored_double(
    text, percent, html_places
):
    """Reading S's count is the shortest string's, so S and L agree.

    The HTML display is the stored value rounded half-up to
    ``html_places``, so the XLSX branch applies exactly when the shortest
    string, shifted two places for a percent format, has more decimals.
    """
    value = D(text)
    places = max(0, -value.as_tuple().exponent)
    stored = value.scaleb(2) if percent else value
    stored_places = max(0, places - 2) if percent else places
    with localcontext() as context:
        context.prec = compare.PRECISION
        display = stored.quantize(
            D(1).scaleb(-html_places), rounding=ROUND_HALF_UP
        )
    cell = invented_cell(
        html_display=str(display),
        html_value=str(display),
        html_decimals=html_places,
        xlsx_raw=text,
        xlsx_number_format="0.0%" if percent else "0.00",
        xlsx_value_pct=format(stored, "f"),
        xlsx_decimals_pct=stored_places,
    )
    shortest = compare.mint_interval(cell)
    assert shortest["stored_decimals_pct"] == stored_places
    assert shortest["stored_value_pct"] == stored
    assert shortest["branch"] == (
        "xlsx" if stored_places > html_places else "html"
    )
    literal = compare.mint_interval(cell, "L")
    for key in ("value", "branch", "stored_decimals_pct"):
        assert literal[key] == shortest[key]


def test_reading_s_counts_decimals_under_a_small_ambient_precision():
    """Review r2 finding 3: normalization runs at PRECISION.

    INVENTED cell. An ambient precision of 6 is too small for the 12
    significant digits of the stored double; the count stays 11. The
    ``with`` block restores the test's own context on exit, whether the
    assertions pass or fail, and the call leaves the ambient one alone.
    """
    cell = invented_cell(xlsx_raw="-7.32123456789", xlsx_number_format="0.00")
    expected = compare.mint_interval(cell)
    outer = getcontext().prec
    with localcontext() as context:
        context.prec = 6
        shortest = compare.mint_interval(cell)
        ambient = getcontext().prec
    assert getcontext().prec == outer
    assert ambient == 6
    assert expected["stored_decimals_pct"] == 11
    assert shortest["stored_decimals_pct"] == 11
    assert repr(shortest) == repr(expected)


ROUNDINGS = (
    decimal.ROUND_05UP,
    decimal.ROUND_CEILING,
    decimal.ROUND_DOWN,
    decimal.ROUND_FLOOR,
    decimal.ROUND_HALF_DOWN,
    decimal.ROUND_HALF_EVEN,
    decimal.ROUND_HALF_UP,
    decimal.ROUND_UP,
)


DECIMAL_SIGNALS = (
    decimal.Clamped,
    decimal.DivisionByZero,
    decimal.FloatOperation,
    decimal.Inexact,
    decimal.InvalidOperation,
    decimal.Overflow,
    decimal.Rounded,
    decimal.Subnormal,
    decimal.Underflow,
)
CONTEXT_FIELDS = ("prec", "rounding", "Emin", "Emax", "capitals", "clamp")


def standard_context(precision=28):
    """The default decimal context's fields, written out (review r3, 2)."""
    return decimal.Context(
        prec=precision,
        rounding=decimal.ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[
            decimal.InvalidOperation,
            decimal.DivisionByZero,
            decimal.Overflow,
        ],
    )


@st.composite
def invented_decimal_contexts(draw):
    """Decimal contexts with every field drawn; small exponent limits often."""
    return decimal.Context(
        prec=draw(st.integers(1, 99)),
        rounding=draw(st.sampled_from(ROUNDINGS)),
        Emin=draw(
            st.one_of(st.integers(-60, 0), st.integers(decimal.MIN_EMIN, 0))
        ),
        Emax=draw(
            st.one_of(st.integers(0, 60), st.integers(0, decimal.MAX_EMAX))
        ),
        capitals=draw(st.integers(0, 1)),
        clamp=draw(st.integers(0, 1)),
        flags=draw(st.lists(st.sampled_from(DECIMAL_SIGNALS), unique=True)),
        traps=draw(st.lists(st.sampled_from(DECIMAL_SIGNALS), unique=True)),
    )


def copy_context_fields(target, source):
    """Give ``target`` every field of ``source``, flags and traps included."""
    for field in CONTEXT_FIELDS:
        setattr(target, field, getattr(source, field))
    for signal in DECIMAL_SIGNALS:
        target.flags[signal] = source.flags[signal]
        target.traps[signal] = source.traps[signal]


def load_compare(name):
    """Load the comparison script afresh, under the current contexts."""
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / "compare_acola.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mint_context_is_the_default_context_at_fifty_digits():
    """Review r3 finding 2: every field of the MINT context is set.

    Each value is the one the default context gives, at PRECISION digits,
    so no output at the default context changes. ``standard_context``
    writes those values out, and here they match ``DefaultContext``.
    """
    assert repr(standard_context()) == repr(decimal.DefaultContext)
    assert repr(compare.MINT_CONTEXT) == repr(
        standard_context(compare.PRECISION)
    )


def test_mint_readings_ignore_ambient_exponent_limits_and_clamping():
    """Review r3 finding 2's reproduction: an ambient Emax of 0, clamped.

    INVENTED cells. Before this fix, that context made reading S count 49
    decimals in both cells, so each fell back to HTML. ``invented_cell()``
    keeps its default-context count of 2 and point -7.32, and the review's
    minimized cell keeps its count of 1 and XLSX point 0.1.
    """
    minimized = {
        "html_value": "0",
        "html_decimals": 0,
        "xlsx_raw": "0.1",
        "xlsx_number_format": "0",
    }
    cells = (invented_cell(), minimized)
    expected = [compare.mint_interval(cell) for cell in cells]
    with localcontext() as context:
        context.Emax = 0
        context.clamp = 1
        got = [compare.mint_interval(cell) for cell in cells]
    assert [result["stored_decimals_pct"] for result in got] == [2, 1]
    assert [result["value"]["point"] for result in got] == [
        D("-7.32"),
        D("0.1"),
    ]
    assert [result["branch"] for result in got] == ["xlsx", "xlsx"]
    assert repr(got) == repr(expected)


@given(
    text=invented_shortest_decimals(),
    percent=st.booleans(),
    html_places=st.integers(0, 6),
    ambient=invented_decimal_contexts(),
    default=invented_decimal_contexts(),
)
@settings(max_examples=200, deadline=None)
def test_mint_readings_do_not_depend_on_the_ambient_decimal_context(
    text, percent, html_places, ambient, default
):
    """Property: readings S and L give one result under any context.

    INVENTED stored doubles and literal pairs, as in the shortest-string
    property. Review r2 finding 3 varied the ambient precision and
    rounding; review r3 finding 2 showed that exponent limits and clamping
    still reached both of ``mint_interval``'s Decimal blocks. Here every
    field of the ambient context varies: precision, rounding, exponent
    limits, capitals, clamping, flags and traps. Every field of
    ``DefaultContext`` varies too, and a copy of the script loaded afresh
    under it is called as well. Each reading's result equals its result
    at the standard context, the default context's fields. A ``finally``
    restores both contexts.
    """
    value = D(text)
    places = max(0, -value.as_tuple().exponent)
    stored = value.scaleb(2) if percent else value
    with localcontext() as context:
        context.prec = compare.PRECISION
        display = stored.quantize(
            D(1).scaleb(-html_places), rounding=ROUND_HALF_UP
        )
    cell = invented_cell(
        html_value=str(display),
        html_decimals=html_places,
        xlsx_raw=text,
        xlsx_number_format="0.0%" if percent else "0.00",
        xlsx_value_pct=format(stored, "f"),
        xlsx_decimals_pct=max(0, places - 2) if percent else places,
    )
    with localcontext(standard_context()):
        expected = [compare.mint_interval(cell, reading) for reading in "SL"]
    saved, saved_default = decimal.getcontext(), decimal.DefaultContext.copy()
    try:
        decimal.setcontext(ambient)
        copy_context_fields(decimal.DefaultContext, default)
        fresh = load_compare("_compare_acola_fresh")
        got = [
            module.mint_interval(cell, reading)
            for module in (compare, fresh)
            for reading in "SL"
        ]
    finally:
        decimal.setcontext(saved)
        copy_context_fields(decimal.DefaultContext, saved_default)
    assert repr(got) == repr(expected * 2)


def test_interval_subtraction_and_null_propagation():
    left = compare._interval(D(2), D(1), D(3))
    right = compare._interval(D(6), D(4), D(8))
    assert compare.subtract_interval(left, right) == compare._interval(
        D(-4), D(-7), D(-1)
    )
    assert (
        compare.subtract_interval(left, compare._undefined("missing"))[
            "undefined_reason"
        ]
        == "missing"
    )


def test_null_uses_exact_rational_then_decimal_before_float_approximation():
    record = {
        "exact": {"numerator": "-1", "denominator": "3"},
        "value_decimal": "-0.3333",
        "value": -0.33,
    }
    with localcontext() as context:
        context.prec = compare.PRECISION
        expected = -D(1) / D(3)
    assert compare._null_interval({"N": record}, "N")["point"] == expected
    record.pop("exact")
    assert compare._null_interval({"N": record}, "N")["point"] == D("-0.3333")
    record.pop("value_decimal")
    assert compare._null_interval({"N": record}, "N")["point"] == D("-0.33")


def test_real_spec_only_null_records_keep_exact_precision():
    from populace_dynamics.acola_track.nulls import build_nulls

    nulls = build_nulls()
    for key in ("N", "N_model", "N_MINT", "N_M1"):
        record = nulls[key]
        with localcontext() as context:
            context.prec = compare.PRECISION
            exact = D(record["exact"]["numerator"]) / D(
                record["exact"]["denominator"]
            )
        assert compare._null_interval(nulls, key)["point"] == exact


@pytest.mark.parametrize(
    "median_type,headline",
    [
        ("median_of_individual_differences", "median_individual_pct_change"),
        ("difference_of_medians", "difference_of_weighted_medians_pct"),
        ("unsettled", None),
        (None, None),
    ],
)
def test_headline_follows_record_and_all_rows_bands_statistics_survive(
    median_type, headline
):
    record = invented_comparator()
    record["mint5"]["median_type"] = median_type
    result = compare.build_comparison(invented_artifact(), record)
    assert result["mint5"]["headline_statistic"] == headline
    for row in ("M0", "M1", "M2", "M3", "M4"):
        bands = result["mint5"]["rows"][row]["bands"]
        assert set(bands) == set(compare.BANDS)
        for cell in bands.values():
            assert set(cell["statistics"]) == set(compare.MINT_STATISTICS)
            assert cell["headline_statistic"] == headline
            assert cell["dollar_levels_compared"] is False
            null_key = "N_M1" if row == "M1" else "N_MINT"
            value = cell["statistics"][compare.MINT_STATISTICS[0]]
            assert value["null_key"] == null_key
            assert value["model_minus_null"]["point"] == (
                13 if row == "M1" else 12
            )
    for source in result["cost"].values():
        assert set(source["rows"]) == {"C0", "C1"}
        for cell in source["rows"].values():
            assert cell["model_minus_null"]["point"] == -2
            assert cell["model_minus_model_null"]["point"] == -3


def test_null_fields_are_reported_never_guessed_and_empty_band_serializes():
    artifact, record = invented_artifact(), invented_comparator()
    artifact["rows"]["M0"]["bands"]["90+"]["statistics"][
        compare.MINT_STATISTICS[0]
    ] = invented_summary(None)
    record["oact"]["columns"][0]["value"] = None
    record["pwbm"]["stored_decimals"]["A1 cost rate"] = None
    record["mint5"]["table1"]["rows"]["90+"]["median_diff_pct"] = None
    record["mint5"]["start_date_reading"] = None
    result = compare.build_comparison(artifact, record)
    assert result["cost"]["OACT"]["conversion"]["value"]["point"] is None
    assert result["cost"]["PWBM"]["conversion"]["value"]["point"] is None
    cell = result["mint5"]["rows"]["M0"]["bands"]["90+"]
    assert cell["registered_reading_S"]["value"]["point"] is None
    assert cell["statistics"][compare.MINT_STATISTICS[0]][
        "model_minus_comparator"
    ]["undefined_reason"]
    serialized = compare.json_result(result)
    assert "empty band" in serialized
    assert "INVENTED empty half" in serialized
    assert "NaN" not in serialized


def test_flags_timing_memos_and_split_are_read_from_records():
    record = invented_comparator()
    record["mint5"]["start_date_reading"] = "M1"
    record["oact"]["december_2030_timing"][
        "reading"
    ] = "excludes_dec2030_increase"
    result = compare.build_comparison(invented_artifact(), record)
    assert result["cost"]["PWBM"]["flags"]["dilution"] == "unsigned"
    assert (
        result["cost"]["OACT"]["flags"]["december_2030_timing"]["reading"]
        == "excludes_dec2030_increase"
    )
    assert result["mint5"]["start_date_reading"] == "M1"
    assert result["mint5"]["table2_memo"] == record["mint5"]["table2"]
    assert (
        result["cost"]["OACT"]["oasi_di_split"]["note"]
        == "not printed by the comparator"
    )
    record["oact"]["prints_oasi_di_split_2030"] = True
    record["oact"]["invented_split_fields"] = {"retained": "123"}
    result = compare.build_comparison(invented_artifact(), record)
    assert (
        result["cost"]["OACT"]["oasi_di_split"]["undefined_reason"]
        == "numeric split schema unspecified"
    )
    assert result["cost"]["OACT"]["comparator_record"][
        "invented_split_fields"
    ] == {"retained": "123"}


@pytest.mark.parametrize(
    "admin,railroad,dilution",
    [
        ("no", "no", "none from these cost items"),
        ("yes", "no", "toward zero"),
        ("no", "yes", "unsigned"),
        ("yes", "not_stated", "unsigned"),
    ],
)
def test_dilution_claims_follow_each_flag(admin, railroad, dilution):
    flags = compare._flags(
        {
            "cost_includes_admin_expenses": admin,
            "cost_includes_railroad_interchange": railroad,
        }
    )
    assert flags["dilution"] == dilution
    assert (flags["administrative_expenses_effect"] == "excluded") == (
        admin == "no"
    )
    if railroad == "no":
        assert flags["railroad_interchange_effect"] == "excluded"


def test_missing_registration_flags_have_explicit_unknown_status():
    record = invented_comparator()
    record["oact"]["footer_matches_registration"] = None
    record["oact"]["provision_text_matches_registration"] = None
    result = compare.build_comparison(invented_artifact(), record)
    for check in result["cost"]["OACT"]["registration_checks"].values():
        assert check["matches"] is None
        assert check["undefined_reason"]


@pytest.mark.parametrize(
    "key",
    ["footer_matches_registration", "provision_text_matches_registration"],
)
def test_oact_registration_mismatch_refuses(key):
    record = invented_comparator()
    record["oact"][key] = False
    with pytest.raises(ValueError, match=key):
        compare.build_comparison(invented_artifact(), record)


def test_wrong_oact_footer_refuses_without_substitution():
    record = invented_comparator()
    record["oact"]["footer_verbatim"] = "INVENTED wrong vintage"
    with pytest.raises(ValueError, match="footer"):
        compare.build_comparison(invented_artifact(), record)


@pytest.mark.parametrize(
    "footer",
    [
        compare.OACT_FOOTER + ".\n",
        compare.OACT_FOOTER + ". ",
        compare.OACT_FOOTER.replace(" ", "\xa0") + ".",
        compare.OACT_FOOTER + " .",
    ],
    ids=[
        "trailing_newline",
        "trailing_space",
        "no_break_spaces",
        "space_before_period",
    ],
)
def test_oact_footer_accepts_transcribed_whitespace(footer):
    """Whitespace on either side of the final period is not refused.

    Review r1b finding 2 named the first three cases; review r2 finding 1
    named the fourth, which fix r1's check refused.
    """
    record = invented_comparator()
    record["oact"]["footer_verbatim"] = footer
    compare.build_comparison(invented_artifact(), record)


FOOTER_TOKENS = compare.OACT_FOOTER.split()
FOOTER_SPACES = (" ", "  ", "\t", "\n", "\r\n", "\xa0", "\u2009", "\u202f")


@given(
    gaps=st.lists(
        st.sampled_from(FOOTER_SPACES),
        min_size=len(FOOTER_TOKENS) - 1,
        max_size=len(FOOTER_TOKENS) - 1,
    ),
    lead=st.sampled_from(("",) + FOOTER_SPACES),
    before=st.sampled_from(("",) + FOOTER_SPACES),
    tail=st.sampled_from(("",) + FOOTER_SPACES),
    periods=st.integers(0, 2),
    changed=st.one_of(st.none(), st.integers(0, len(FOOTER_TOKENS) - 1)),
)
@settings(max_examples=150, deadline=None)
def test_oact_footer_check_ignores_only_whitespace_and_final_periods(
    gaps, lead, before, tail, periods, changed
):
    """Any whitespace run and final periods pass; a changed word refuses.

    INVENTED transcriptions of the registered footer: whitespace of any
    kind and length between, before and after its words, before and
    after up to two final periods. Changing one word (an appended "X")
    always refuses.
    """
    tokens = list(FOOTER_TOKENS)
    if changed is not None:
        tokens[changed] += "X"
    words = "".join(
        token + gap for token, gap in zip(tokens, [*gaps, ""], strict=True)
    )
    record = invented_comparator()
    record["oact"]["footer_verbatim"] = (
        lead + words + before + "." * periods + tail
    )
    if changed is None:
        compare.build_comparison(invented_artifact(), record)
    else:
        with pytest.raises(ValueError, match="footer"):
            compare.build_comparison(invented_artifact(), record)


def pre_r1_footer_matches(footer):
    """The footer check before fix r1, copied as the reference.

    ``scripts/compare_acola.py:399`` at ``6abb6726`` refused a footer
    unless ``footer.rstrip(".").strip() == OACT_FOOTER``.
    """
    return footer.rstrip(".").strip() == compare.OACT_FOOTER


def r1_footer_matches(footer):
    """Fix r1's footer check (``0a3299df``), kept to pin its regression."""
    return (
        " ".join(footer.replace("\xa0", " ").split()).rstrip(".")
        == compare.OACT_FOOTER
    )


def test_footer_whitespace_before_final_periods_passes_again():
    """Review r2 finding 1: the pre-r1 check accepted these, r1 refused.

    INVENTED footers: whitespace of several kinds directly before the
    final period or periods. The new check accepts them again.
    """
    for space in (" ", "\t", "\n", "\xa0", "\u2009", " \t "):
        for periods in (".", ".."):
            footer = compare.OACT_FOOTER + space + periods
            assert pre_r1_footer_matches(footer)
            assert not r1_footer_matches(footer)
            assert compare.oact_footer_matches(footer)


FOOTER_LEADS = ("", " ", "\t\n", "\xa0", ".", "X")
FOOTER_JOINERS = (
    (" ",),
    ("\xa0",),
    ("\t",),
    ("  \n",),
    (" ", "\u2009", "\r\n"),
)
FOOTER_BEFORES = ("", " ", "\xa0", "\n")
FOOTER_PERIODS = ("", ".", "..")
FOOTER_TAILS = ("", " ", "\r\n", " .", "X")


def footer_word_variants():
    """The registered words, then 52 ways to change, drop or add a word.

    Each word changed (an appended "X"), dropped or recased (the year has
    no case, so 8 recasings); a period after each word but the last; an
    "X" added at each of the 10 positions; and each adjacent pair joined.
    """
    tokens = list(FOOTER_TOKENS)
    yield tokens
    for index, token in enumerate(tokens):
        yield tokens[:index] + [token + "X"] + tokens[index + 1 :]
        yield tokens[:index] + tokens[index + 1 :]
        if token.swapcase() != token:
            yield tokens[:index] + [token.swapcase()] + tokens[index + 1 :]
        if index < len(tokens) - 1:
            yield tokens[:index] + [token + "."] + tokens[index + 1 :]
    for index in range(len(tokens) + 1):
        yield tokens[:index] + ["X"] + tokens[index:]
    for index in range(len(tokens) - 1):
        joined = tokens[index] + tokens[index + 1]
        yield tokens[:index] + [joined] + tokens[index + 2 :]


def enumerated_footers():
    """Every INVENTED footer from the small alphabets above."""
    for lead, tokens, joiner, before, periods, tail in itertools.product(
        FOOTER_LEADS,
        list(footer_word_variants()),
        FOOTER_JOINERS,
        FOOTER_BEFORES,
        FOOTER_PERIODS,
        FOOTER_TAILS,
    ):
        gaps = [joiner[index % len(joiner)] for index in range(len(tokens))]
        words = "".join(
            token + gap
            for token, gap in zip(tokens, [*gaps[:-1], ""], strict=True)
        )
        end = before + periods + tail
        yield lead + words + end, tokens == FOOTER_TOKENS, lead, end


def test_footer_check_keeps_everything_the_pre_r1_check_accepted():
    """Enumerated: whatever the pre-r1 check accepted still passes.

    The intended difference between the pre-r1 check (``6abb6726``) and
    this one, in both directions:

    - **Accepted before, refused now: none.** The pre-r1 check accepted
      exactly the registered words joined by single ASCII spaces, with any
      whitespace before them and any whitespace, then any periods, after
      them. Each such footer passes now. Fix r1 meant to refuse changed,
      added, dropped and joined words, and the pre-r1 check refused those
      too, so no accepted case needs an exception.
    - **Refused before, accepted now:** any whitespace run between words
      other than one ASCII space (tabs, line breaks, no-break, thin and
      narrow no-break spaces, or runs of them), whitespace after a final
      period (``"Report.\\n"``, ``"Report. "``), and periods separated by
      whitespace (``"Report. ."``).

    The INVENTED footers combine 6 leads, 53 word sequences
    (:func:`footer_word_variants`), 5 joiners, 4 gaps before the
    periods, 3 period runs and 5 tails, 95,400 in all. The check accepts
    exactly the registered words with only whitespace before them and
    only whitespace and periods after them.
    """
    outcomes = Counter()
    for footer, registered, lead, end in enumerated_footers():
        old = pre_r1_footer_matches(footer)
        new = compare.oact_footer_matches(footer)
        expected = (
            registered
            and not lead.strip()
            and not end.replace(".", "").strip()
        )
        assert new == expected, repr(footer)
        assert new or not old, repr(footer)
        outcomes[old, new] += 1
    assert sum(outcomes.values()) == 95_400
    assert outcomes[True, False] == 0
    assert outcomes[True, True] > 0
    assert outcomes[False, True] > 0
    assert outcomes[False, False] > 0


UNICODE_SPACES = tuple(
    chr(code) for code in range(sys.maxunicode + 1) if chr(code).isspace()
)
NOT_SPACES = ("\u200b", "\u2060", "\ufeff", "\u00ad", "\u180e")


def test_footer_check_and_pre_r1_check_share_one_whitespace_set():
    """Every character ``str.isspace`` accepts is whitespace to both.

    INVENTED footers put each Unicode whitespace character before the
    words, between them, after them and around the final period. Zero-width
    and format characters are not whitespace, so both checks refuse them.
    """
    footer = compare.OACT_FOOTER
    assert not any(char.isspace() for char in NOT_SPACES)
    for space in UNICODE_SPACES:
        accepted_before = (
            space + footer,
            footer + space,
            footer + space + ".",
        )
        for case in accepted_before:
            assert pre_r1_footer_matches(case), repr(case)
            assert compare.oact_footer_matches(case), repr(case)
        for case in (footer.replace(" ", space), footer + "." + space):
            assert compare.oact_footer_matches(case), repr(case)
    for char in NOT_SPACES:
        cases = (
            char + footer,
            footer + char,
            footer.replace(" ", char),
            footer + "." + char,
        )
        for case in cases:
            assert not pre_r1_footer_matches(case), repr(case)
            assert not compare.oact_footer_matches(case), repr(case)


@given(
    lead=st.text(st.sampled_from(UNICODE_SPACES), max_size=3),
    before=st.text(st.sampled_from(UNICODE_SPACES), max_size=3),
    periods=st.integers(0, 3),
    prefix=st.text(
        st.sampled_from(UNICODE_SPACES + NOT_SPACES + (".", "X")), max_size=3
    ),
    suffix=st.text(
        st.sampled_from(UNICODE_SPACES + NOT_SPACES + (".", "X")), max_size=4
    ),
    gap=st.text(
        st.sampled_from(UNICODE_SPACES + NOT_SPACES), min_size=1, max_size=2
    ),
)
@settings(max_examples=300, deadline=None)
def test_footer_check_accepts_whatever_the_pre_r1_check_accepted(
    lead, before, periods, prefix, suffix, gap
):
    """Property: the pre-r1 accept set is inside the new one.

    INVENTED footers. ``lead + footer + before + periods`` is the shape of
    every footer the pre-r1 check accepted, so both checks accept it. On
    a footer with arbitrary leading, joining and trailing characters, the
    pre-r1 check's acceptance implies the new check's.
    """
    footer = compare.OACT_FOOTER
    accepted = lead + footer + before + "." * periods
    assert pre_r1_footer_matches(accepted)
    assert compare.oact_footer_matches(accepted)
    noisy = prefix + footer.replace(" ", gap, 1) + suffix
    assert compare.oact_footer_matches(noisy) or not pre_r1_footer_matches(
        noisy
    )


DECIMAL_COUNT_CELLS = {
    "oact_proposal": ("oact.columns.proposal_cost_rate", "decimals"),
    "oact_change": ("oact.columns.change_cost_rate", "decimals"),
    "pwbm_baseline": ("pwbm.row_2030.Baseline cost rate", "stored_decimals"),
    "pwbm_reform": ("pwbm.row_2030.A1 cost rate", "stored_decimals"),
    "mint": ("mint5.table1.rows.70-79.median_diff_pct", "html_decimals"),
    "mint_xlsx": (
        "mint5.table1.rows.70-79.median_diff_pct",
        "xlsx_decimals_pct",
    ),
}


def write_value(record, field, value, count):
    """Set one counted INVENTED value and its decimal count in a record."""
    if field.startswith("oact"):
        index = 0 if field == "oact_proposal" else 1
        record["oact"]["columns"][index].update(value=value, decimals=count)
    elif field.startswith("pwbm"):
        key = (
            "Baseline cost rate"
            if field == "pwbm_baseline"
            else "A1 cost rate"
        )
        record["pwbm"]["row_2030"][key] = value
        record["pwbm"]["stored_decimals"][key] = count
    else:
        cell = record["mint5"]["table1"]["rows"]["70-79"]["median_diff_pct"]
        if field == "mint_xlsx":
            cell.update(xlsx_value_pct=value, xlsx_decimals_pct=count)
        else:
            cell.update(html_value=value, html_decimals=count)
    return record


@pytest.mark.parametrize("field", sorted(DECIMAL_COUNT_CELLS))
@pytest.mark.parametrize(
    "value,count",
    [
        ("12.30", 2),
        ("12.300", 3),
        ("0.750", 3),
        ("12", 0),
        ("12.", 0),
        (D("12.30"), 2),
        (D("12.300"), 3),
        (12, 0),
    ],
)
def test_decimal_count_matches_the_value_as_written(field, value, count):
    """Review r2 finding 4: the check counts trailing zeros as written.

    INVENTED values. "12.30" with a count of 2 passes, and so does
    "12.300" with a count of 3, as a string or a Decimal; an integer
    writes no decimal.
    """
    record = write_value(invented_comparator(), field, value, count)
    assert compare.decimal_count_mismatches(record) == []
    compare.build_comparison(invented_artifact(), record)


@pytest.mark.parametrize("field", sorted(DECIMAL_COUNT_CELLS))
@pytest.mark.parametrize(
    "value,count",
    [
        ("12.30", 1),
        ("12.30", 3),
        ("12.300", 2),
        ("12.3", 0),
        ("12", 1),
        (D("12.30"), 1),
        (12, 2),
    ],
)
def test_wrong_decimal_count_refuses_naming_the_cell_only(field, value, count):
    """A count unlike the written decimals refuses, with no value shown."""
    record = write_value(invented_comparator(), field, value, count)
    locator = DECIMAL_COUNT_CELLS[field]
    assert compare.decimal_count_mismatches(record) == [locator]
    with pytest.raises(ValueError, match="decimal counts") as error:
        compare.build_comparison(invented_artifact(), record)
    assert f"{locator[0]} ({locator[1]})" in str(error.value)
    assert str(value) not in str(error.value)


@pytest.mark.parametrize("field", ["mint", "mint_xlsx"])
@pytest.mark.parametrize(
    "value,count",
    [
        ("12.30", -1),
        ("12.30", 2.5),
        ("12.30", "two"),
        ("12.30", True),
        ("NaN", 0),
        ("Infinity", 0),
        ("twelve", 0),
        (True, 0),
        (12.3, 1),
    ],
)
def test_unreadable_count_or_value_never_matches(field, value, count):
    """INVENTED unreadable entries are mismatches, never guesses.

    Both MINT counts are covered: HTML, and reading L's (review r3,
    finding 1). Each of these but the last already refused before the
    check, when the conversion parsed it; the check now names its cell
    first. The last is a float: it has lost its written digits, so it
    never matches. ``_load`` yields none, since it reads each JSON number
    as an int or a Decimal; only a record built in memory can hold one.
    """
    record = write_value(invented_comparator(), field, value, count)
    assert compare.decimal_count_mismatches(record) == [
        DECIMAL_COUNT_CELLS[field]
    ]


@given(
    field=st.sampled_from(sorted(DECIMAL_COUNT_CELLS)),
    whole=st.integers(0, 10**9),
    fraction=st.text(st.sampled_from("0123456789"), max_size=12),
    negative=st.booleans(),
    form=st.sampled_from(("string", "decimal", "json")),
    other=st.integers(0, 20),
)
@settings(max_examples=300, deadline=None)
def test_value_written_with_n_decimals_matches_only_a_count_of_n(
    field, whole, fraction, negative, form, other
):
    """Property (review r2, finding 4): n written decimals need count n.

    INVENTED values with n written decimals, trailing zeros included,
    written as a string, as a Decimal, or as a JSON number read the way
    ``_load`` reads one. Each passes with a count of n and refuses with
    any other count, naming only its cell and field.
    """
    text = ("-" if negative else "") + str(whole)
    if fraction:
        text += "." + fraction
    value = {
        "string": text,
        "decimal": D(text),
        "json": json.loads(text, parse_float=D),
    }[form]
    written = len(fraction)
    record = write_value(invented_comparator(), field, value, written)
    assert compare.decimal_count_mismatches(record) == []
    record = write_value(invented_comparator(), field, value, other)
    if other == written:
        assert compare.decimal_count_mismatches(record) == []
    else:
        assert compare.decimal_count_mismatches(record) == [
            DECIMAL_COUNT_CELLS[field]
        ]
        with pytest.raises(ValueError, match="decimal counts"):
            compare.build_comparison(invented_artifact(), record)


def minimized_literal_cell(count):
    """Review r3 finding 1's minimized INVENTED cell, with a given count."""
    return {
        "html_value": "0",
        "html_decimals": 0,
        "xlsx_value_pct": "0.1",
        "xlsx_decimals_pct": count,
    }


@pytest.mark.parametrize("band", compare.BANDS)
def test_reading_l_count_unlike_its_value_refuses_in_a_whole_record(band):
    """Review r3 finding 1: reading L's count is checked in every band.

    INVENTED whole record holding the review's minimized cell: "0.1" with
    a count of 0. That record passed, and reading L gave the HTML point 0;
    a count of 2 passed too, with an interval ten times too narrow. Both
    now refuse, naming the cell and field and no value. The corrected
    count of 1 passes, and reading L gives the XLSX point 0.1 with a
    half-unit of 0.05.
    """
    cell = f"mint5.table1.rows.{band}.median_diff_pct"
    for count in (0, 2):
        record = invented_comparator()
        record["mint5"]["table1"]["rows"][band]["median_diff_pct"] = (
            minimized_literal_cell(count)
        )
        assert compare.decimal_count_mismatches(record) == [
            (cell, "xlsx_decimals_pct")
        ]
        with pytest.raises(ValueError, match="decimal counts") as error:
            compare.build_comparison(invented_artifact(), record)
        assert f"{cell} (xlsx_decimals_pct)" in str(error.value)
        assert "0.1" not in str(error.value)
    record = invented_comparator()
    record["mint5"]["table1"]["rows"][band]["median_diff_pct"] = (
        minimized_literal_cell(1)
    )
    result = compare.build_comparison(invented_artifact(), record)
    literal = result["mint5"]["rows"]["M0"]["bands"][band][
        "sensitivity_reading_L"
    ]
    assert literal["branch"] == "xlsx"
    assert literal["value"] == compare._interval(
        D("0.1"), D("0.05"), D("0.15")
    )


@given(
    band=st.sampled_from(compare.BANDS),
    whole=st.integers(0, 10**9),
    fraction=st.text(st.sampled_from("0123456789"), max_size=12),
    negative=st.booleans(),
    form=st.sampled_from(("string", "decimal", "json")),
    other=st.integers(0, 20),
    null=st.sampled_from((None, "value", "count", "both", "cell")),
)
@settings(max_examples=300, deadline=None)
def test_reading_l_count_matches_only_its_written_decimals_in_every_band(
    band, whole, fraction, negative, form, other, null
):
    """Property (review r3, finding 1): reading L's count, in every band.

    INVENTED literal values with n written decimals, trailing zeros
    included, written as a string, as a Decimal, or as a JSON number read
    the way ``_load`` reads one. In each of the five bands the value
    passes with a count of n and refuses with any other count, naming
    only its cell and field. A missing value, count or cell is not
    checked, as before: the record passes, and reading L falls back to
    HTML, or is undefined when the cell is missing.
    """
    text = ("-" if negative else "") + str(whole)
    if fraction:
        text += "." + fraction
    value = {
        "string": text,
        "decimal": D(text),
        "json": json.loads(text, parse_float=D),
    }[form]
    cell = f"mint5.table1.rows.{band}.median_diff_pct"

    def record_with(count):
        record = invented_comparator()
        row = record["mint5"]["table1"]["rows"][band]
        if null == "cell":
            row["median_diff_pct"] = None
        else:
            row["median_diff_pct"].update(
                xlsx_value_pct=None if null in ("value", "both") else value,
                xlsx_decimals_pct=None if null in ("count", "both") else count,
            )
        return record

    if null is not None:
        record = record_with(other)
        assert compare.decimal_count_mismatches(record) == []
        result = compare.build_comparison(invented_artifact(), record)
        literal = result["mint5"]["rows"]["M0"]["bands"][band][
            "sensitivity_reading_L"
        ]
        if null == "cell":
            assert literal["branch"] is None
            assert literal["value"]["point"] is None
        else:
            assert literal["branch"] == "html"
            assert literal["missing_xlsx"] is True
        return
    written = len(fraction)
    record = record_with(written)
    assert compare.decimal_count_mismatches(record) == []
    compare.build_comparison(invented_artifact(), record)
    record = record_with(other)
    if other == written:
        assert compare.decimal_count_mismatches(record) == []
    else:
        assert compare.decimal_count_mismatches(record) == [
            (cell, "xlsx_decimals_pct")
        ]
        with pytest.raises(ValueError, match="decimal counts") as error:
            compare.build_comparison(invented_artifact(), record)
        assert str(error.value) == (
            "decimal counts differ from the values as written at: "
            f"{cell} (xlsx_decimals_pct)"
        )


def test_decimal_count_check_names_every_counted_cell_and_needs_no_other():
    """It reads only the comparator record and covers fourteen counts.

    INVENTED record with every counted value given one extra trailing
    zero: both OACT cost rates, both PWBM cost rates, and the HTML and
    reading L values of the five MINT bands (review r3, finding 1).
    Income-rate columns and memo cells carry no count it checks.
    """
    assert compare.decimal_count_mismatches({}) == []
    record = invented_comparator()
    for column in record["oact"]["columns"][:2]:
        column["value"] += "0"
    for key in ("Baseline cost rate", "A1 cost rate"):
        record["pwbm"]["row_2030"][key] += "0"
    for band in compare.BANDS:
        cell = record["mint5"]["table1"]["rows"][band]["median_diff_pct"]
        cell["html_value"] += "0"
        cell["xlsx_value_pct"] += "0"
    record["oact"]["columns"][2]["decimals"] = 9
    record["pwbm"]["stored_decimals"]["A1 income rate"] = 9
    assert compare.decimal_count_mismatches(record) == [
        ("oact.columns.proposal_cost_rate", "decimals"),
        ("oact.columns.change_cost_rate", "decimals"),
        ("pwbm.row_2030.Baseline cost rate", "stored_decimals"),
        ("pwbm.row_2030.A1 cost rate", "stored_decimals"),
        *(
            (f"mint5.table1.rows.{band}.median_diff_pct", field)
            for band in compare.BANDS
            for field in ("html_decimals", "xlsx_decimals_pct")
        ),
    ]


def numbers_as_json_numbers(record):
    """The record as JSON with every numeric string written as a number."""
    return re.sub(
        r'": "(-?[0-9]+(?:\.[0-9]+)?)"', r'": \1', json.dumps(record)
    )


def whole_invented_records():
    """Every whole INVENTED record a build_comparison test accepts."""
    yield "base", invented_comparator()
    for median_type in (
        "median_of_individual_differences",
        "difference_of_medians",
        "unsettled",
        None,
    ):
        record = invented_comparator()
        record["mint5"]["median_type"] = median_type
        yield f"median type {median_type}", record
    record = invented_comparator()
    record["oact"]["columns"][0]["value"] = None
    record["pwbm"]["stored_decimals"]["A1 cost rate"] = None
    record["mint5"]["table1"]["rows"]["90+"]["median_diff_pct"] = None
    record["mint5"]["start_date_reading"] = None
    yield "null fields", record
    record = invented_comparator()
    record["mint5"]["start_date_reading"] = "M1"
    record["oact"]["prints_oasi_di_split_2030"] = True
    record["oact"]["invented_split_fields"] = {"retained": "123"}
    yield "flags and split", record
    record = invented_comparator()
    record["oact"]["footer_matches_registration"] = None
    yield "missing registration flags", record
    for footer in (
        compare.OACT_FOOTER + ".\n",
        compare.OACT_FOOTER + " .",
        compare.OACT_FOOTER.replace(" ", "\xa0") + ".",
    ):
        record = invented_comparator()
        record["oact"]["footer_verbatim"] = footer
        yield "footer", record
    yield "read back from JSON", json.loads(json.dumps(invented_comparator()))
    yield "JSON numbers", json.loads(
        numbers_as_json_numbers(invented_comparator()), parse_float=D
    )


def test_decimal_count_check_accepts_every_record_that_passed_before():
    """Ruling 3: each whole invented record that passed still passes.

    The records are those of this module's build_comparison and CLI
    tests, plus the same record read back from JSON with its numbers
    written as strings and as JSON numbers. The conversion fixtures that
    now refuse are named in the next test.
    """
    for label, record in whole_invented_records():
        assert compare.decimal_count_mismatches(record) == [], label
        compare.build_comparison(invented_artifact(), record)


@pytest.mark.parametrize(
    "field,value,count,source",
    [
        (
            "oact_proposal",
            "21.75",
            0,
            "test_oact_decimals_are_not_hard_coded_and_every_corner_positive",
        ),
        (
            "oact_proposal",
            "7",
            3,
            "test_oact_corners_contain_point_and_monotonicity",
        ),
        (
            "oact_change",
            "-0.09999999999999999999999999999999999",
            2,
            "test_oact_precision_gate_boundary",
        ),
        (
            "pwbm_baseline",
            "25.000000",
            15,
            "test_pwbm_decimal_branches_and_point_containment",
        ),
        (
            "pwbm_reform",
            "24.000000",
            5,
            "test_pwbm_decimal_branches_and_point_containment",
        ),
        (
            "pwbm_baseline",
            "7",
            2,
            "test_pwbm_corner_interval_contains_point",
        ),
        (
            "pwbm_baseline",
            "0.001",
            0,
            "test_pwbm_refuses_nonpositive_corner_and_wrong_year",
        ),
    ],
)
def test_conversion_fixtures_whose_counts_differ_from_their_values_refuse(
    field, value, count, source
):
    """Ruling 3: the invented records the check now refuses, each named.

    These fixtures pair a value with a count it does not write, on
    purpose, to drive one conversion's precision branches; their own
    tests call ``oact_comparison`` or ``pwbm_comparison`` directly and
    still pass. As whole records they contradict themselves: an interval
    would rest on a precision the written value does not show. So
    ``build_comparison`` now refuses them, as intended.
    """
    assert callable(globals()[source])
    record = write_value(invented_comparator(), field, value, count)
    assert compare.decimal_count_mismatches(record) == [
        DECIMAL_COUNT_CELLS[field]
    ]
    with pytest.raises(ValueError, match="decimal counts"):
        compare.build_comparison(invented_artifact(), record)


@pytest.mark.parametrize(
    "field,value,count", [("mint", "-7.30", 1), ("mint_xlsx", "-7.3200", 2)]
)
def test_decimal_count_check_follows_seal_and_sidecar_and_precedes_arithmetic(
    tmp_path, monkeypatch, field, value, count
):
    """The check runs after the seal and sidecar checks, before any sum.

    INVENTED inputs: a sealed record whose MINT 70-79 HTML count, or
    reading L count (review r3, finding 1), is wrong.
    """
    record = write_value(invented_comparator(), field, value, count)
    artifact, record_path, seal = write_inputs(tmp_path, comparator=record)
    for name in ("oact_comparison", "pwbm_comparison", "mint_interval"):
        monkeypatch.setattr(
            compare,
            name,
            lambda *args, **kwargs: pytest.fail("arithmetic before check"),
        )
    with pytest.raises(ValueError, match="decimal counts"):
        compare.compare_files(artifact, record_path, seal)
    sidecar = artifact.with_suffix(".env.json")
    sidecar.write_text(json.dumps({"artifact": "another.json"}))
    with pytest.raises(ValueError, match="sidecar"):
        compare.compare_files(artifact, record_path, seal)
    (tmp_path / "invented.txt").write_text("TAMPERED")
    with pytest.raises(ValueError, match="seal"):
        compare.compare_files(artifact, record_path, seal)


def test_load_keeps_each_written_decimal_for_the_check(tmp_path):
    """``_load`` keeps trailing zeros, so the check sees what is written.

    INVENTED record written as JSON with its numbers unquoted, then read
    with ``_load``: "25.000000" is a Decimal with six decimals.
    """
    path = tmp_path / "numbers.json"
    path.write_text(numbers_as_json_numbers(invented_comparator()))
    record = compare._load(path)
    value = record["pwbm"]["row_2030"]["Baseline cost rate"]
    assert isinstance(value, Decimal)
    assert value.as_tuple().exponent == -6
    assert compare.decimal_count_mismatches(record) == []
    bad = write_value(record, "pwbm_baseline", D("25.0000000"), 6)
    assert compare.decimal_count_mismatches(bad) == [
        DECIMAL_COUNT_CELLS["pwbm_baseline"]
    ]


@pytest.mark.parametrize(
    "mutation", ["hash", "bytes", "missing", "unsealed_comparator"]
)
def test_seal_checks_every_entry_and_precedes_any_artifact_read(
    tmp_path, monkeypatch, mutation
):
    artifact, record, seal = write_inputs(tmp_path)
    inventory = json.loads(seal.read_text())
    if mutation == "hash":
        (tmp_path / "invented.txt").write_text("TAMPERED")
    elif mutation == "bytes":
        inventory["files"]["invented.txt"]["bytes"] += 1
    elif mutation == "missing":
        (tmp_path / "invented.txt").unlink()
    else:
        inventory["files"].pop("reconciled.json")
    seal.write_text(json.dumps(inventory))
    artifact.unlink()
    monkeypatch.setattr(
        compare,
        "_load",
        lambda path: pytest.fail("parsed values before seal verification"),
    )
    with pytest.raises(ValueError, match="seal|sealed"):
        compare.compare_files(artifact, record, seal)


def test_seal_reports_all_failures_and_refuses_path_escape(tmp_path):
    _, record, seal = write_inputs(tmp_path)
    inventory = json.loads(seal.read_text())
    inventory["files"].update(
        {
            "../outside": {"sha256": "x", "bytes": 0},
            "missing": {"sha256": "x", "bytes": 0},
        }
    )
    seal.write_text(json.dumps(inventory))
    with pytest.raises(ValueError) as error:
        compare.verify_seal(seal, record)
    assert "invalid seal path" in str(error.value)
    assert "missing sealed file" in str(error.value)


@pytest.mark.parametrize(
    "change", ["artifact", "sidecar_hash", "sidecar_filename"]
)
def test_artifact_sidecar_is_verified(tmp_path, change):
    artifact, record, seal = write_inputs(tmp_path)
    sidecar = artifact.with_suffix(".env.json")
    data = json.loads(sidecar.read_text())
    if change == "artifact":
        artifact.write_text("{}")
    elif change == "sidecar_hash":
        data["artifact_sha256"] = "0" * 64
    else:
        data["artifact"] = "another.json"
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="sidecar"):
        compare.compare_files(artifact, record, seal)


def test_cli_writes_exact_json_markdown_and_prints_seal_hash(tmp_path, capsys):
    artifact, record, seal = write_inputs(tmp_path)
    out_json, out_md = tmp_path / "result.json", tmp_path / "result.md"
    assert (
        compare.main(
            [
                "--artifact",
                str(artifact),
                "--comparator",
                str(record),
                "--seal",
                str(seal),
                "--output-json",
                str(out_json),
                "--output-markdown",
                str(out_md),
            ]
        )
        == 0
    )
    seal_hash = hashlib.sha256(seal.read_bytes()).hexdigest()
    assert seal_hash in capsys.readouterr().out
    result = json.loads(out_json.read_text())
    assert result["verification"]["seal_sha256"] == seal_hash
    assert result["verification"]["verified_files"] == 2
    markdown = out_md.read_text()
    assert "| Row | Comparator |" in markdown
    assert "MINT5 L sensitivity" in markdown
    assert '"sample_sd": "0.125"' in markdown
    assert "not printed by the comparator" in markdown
    assert '"value": "-7.3200000000000001"' not in markdown
    assert "-7.3200000000000001" in markdown
    assert "verdict" not in result and "pass_band" not in result


def test_load_keeps_decimals_bom_and_refuses_nonfinite(tmp_path):
    path = tmp_path / "number.json"
    path.write_text('\ufeff{"value": 1.2345678901234567890123456789}')
    assert compare._load(path)["value"] == D("1.2345678901234567890123456789")
    path.write_text('{"value": NaN}')
    with pytest.raises(ValueError, match="nonfinite"):
        compare._load(path)


def test_script_has_only_standard_library_dependencies():
    import sys

    tree = ast.parse((ROOT / "scripts" / "compare_acola.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                alias.name.split(".")[0] in sys.stdlib_module_names
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            assert node.module.split(".")[0] in sys.stdlib_module_names


def test_consumes_actual_stage1_invented_dry_artifact_layout(tmp_path):
    from populace_dynamics.acola_track.runner import run_acola
    from tests.acola_track.test_runner import CONFIG, _inputs

    artifact = run_acola(_inputs(), config=CONFIG)
    paths = write_inputs(tmp_path, artifact)
    result = compare.compare_files(*paths)
    assert result["deferred_rows"]["C0-D"]["status"] == "deferred"
    assert set(result["mint5"]["rows"]) == {"M0", "M1", "M2", "M3", "M4"}
    source = artifact["rows"]["C0"]["statistics"]["P"]
    model = result["cost"]["OACT"]["rows"]["C0"]["model"]
    assert model["mean"] == D(str(source["mean"]))
    assert model["sample_sd"] == D(str(source["sample_sd"]))
    assert model["floor"]["defined"] == source["floor"]["defined"]
    assert (
        result["mint5"]["rows"]["M1"]["bands"]["Total"]["statistics"][
            compare.MINT_STATISTICS[0]
        ]["null_key"]
        == "N_M1"
    )
    compare.json_result(result)
