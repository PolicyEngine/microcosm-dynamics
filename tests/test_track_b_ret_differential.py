"""Compare R1 parameters with a pinned independent implementation.

The captured YAML is sufficient: collection and execution need neither a
second checkout nor an installed PolicyEngine simulation engine. SSA remains
the historical authority; known comparator scope/precision differences are
recorded explicitly rather than copied into Track B.
"""

import hashlib
import json
from fractions import Fraction
from pathlib import Path

import pytest
import yaml

from populace_dynamics.track_b.ret_params import load_ret_parameters

CAPTURES = Path(__file__).parent / "data" / "track_b" / "ret_differential"
PINNED_COMMIT = "a03e82e503f8e0285125ee0c5380410a964c8e8a"
MANIFEST = json.loads((CAPTURES / "manifest.json").read_text())


def _values(name):
    parameter = yaml.safe_load((CAPTURES / name).read_text())
    return {date.year: value for date, value in parameter["values"].items()}


LOWER = _values("exempt_amount_under_fra.yaml")
HIGHER = _values("exempt_amount_year_of_fra.yaml")


@pytest.mark.parametrize("capture", MANIFEST["files"], ids=lambda x: x["file"])
def test_comparison_capture_matches_pinned_bytes(capture):
    data = (CAPTURES / capture["file"]).read_bytes()
    assert MANIFEST["commit"] == PINNED_COMMIT
    assert f"/blob/{PINNED_COMMIT}/" in capture["url"]
    assert len(data) == capture["bytes"]
    assert hashlib.sha256(data).hexdigest() == capture["sha256"]


@pytest.mark.parametrize(
    "year, expected",
    [(year, value) for year, value in sorted(LOWER.items()) if year >= 2000],
)
def test_lower_history_matches_policyengine_parameters(year, expected):
    row = load_ret_parameters().for_year(year)
    assert row.lower_exempt_amount.value == expected
    assert row.lower_exempt_amount.status == "realized"


@pytest.mark.parametrize(
    "year, expected",
    [(year, value) for year, value in sorted(HIGHER.items()) if year >= 2000],
)
def test_modern_higher_history_matches_policyengine_parameters(year, expected):
    row = load_ret_parameters().for_year(year)
    assert row.higher_exempt_amount.value == expected
    assert row.higher_exempt_amount.status == "realized"


def test_comparison_pre_2000_higher_values_have_different_scope():
    """The comparator substitutes the lower amount before the modern rule."""
    historical = {year: value for year, value in HIGHER.items() if year < 2000}
    assert historical
    assert historical == {year: LOWER[year] for year in historical}


def test_pre_2000_comparator_rows_do_not_expand_modern_rule_scope():
    table = load_ret_parameters()
    for year in sorted(LOWER):
        if year < 2000:
            with pytest.raises(KeyError, match=f"unavailable for year {year}"):
                table.for_year(year)


def test_withholding_rates_preserve_exact_statutory_fractions():
    row = load_ret_parameters().for_year(2026)
    lower = Fraction(str(_values("reduction_rate_under_fra.yaml")[1940]))
    higher = Fraction(str(_values("reduction_rate_year_of_fra.yaml")[1940]))

    assert row.lower_withholding_rate.value == lower == Fraction(1, 2)
    assert row.higher_withholding_rate.value == Fraction(1, 3)
    # The pinned comparator uses six decimal places; do not inherit that loss.
    assert higher == Fraction(333333, 1000000)
    assert row.higher_withholding_rate.value - higher == Fraction(1, 3000000)
