"""DB COLA conformance and properties; all account inputs are invented.

These tests read versioned data/external parameters through the rule API.
The GAO example's CPI assumption is a published stylized worked example,
not an observed pension or survey record.
"""

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources import pension_cola
from populace_dynamics.income_resources.pension_cola import (
    FederalAnnuityCategory,
    FederalPensionPlan,
    PensionColaAssumption,
    assumed_pension_cola_rate,
    cola_adjusted_monthly_annuity,
    federal_pension_cola_rate,
)

INVENTED_BASE = {
    "year": 2026,
    "plan": FederalPensionPlan.FERS,
    "price_index_change": 0.045,
    "age": 62,
    "annuity_category": FederalAnnuityCategory.ORDINARY_RETIREMENT,
}
INVENTED_GROWTH = st.floats(
    min_value=0, max_value=1, allow_nan=False, allow_infinity=False
)


def test_gao_worked_cola_comparison():
    """GAO/GGD-97-40 p53 n8: CPI 4.5%, FERS 3.5%, CSRS 4.5%.

    This matches 5 U.S.C. 8462(b)(1)(B) and 8340(b); other account
    attributes are invented and only ensure the full-rate case applies.
    """
    assert federal_pension_cola_rate(**INVENTED_BASE) == 0.035
    assert (
        federal_pension_cola_rate(
            **{**INVENTED_BASE, "plan": FederalPensionPlan.CSRS}
        )
        == 0.045
    )


@pytest.mark.parametrize(
    "growth,expected",
    [
        (0, 0),
        (-0.01, 0),
        (0.015, 0.015),
        (0.02, 0.02),
        (0.025, 0.02),
        (0.03, 0.02),
        (0.0304, 0.02),
        (0.0305, 0.021),
        (0.05, 0.04),
    ],
)
def test_fers_statutory_breakpoints(growth, expected):
    """8462(b)(1): compare raw growth to 3% before one-tenth rounding."""
    assert (
        federal_pension_cola_rate(
            **{**INVENTED_BASE, "price_index_change": growth}
        )
        == expected
    )


def test_first_cola_rounding_and_month_count():
    """8340(c)(1), 8462(c)(1): round rate after multiplying months/12."""
    assert (
        federal_pension_cola_rate(**INVENTED_BASE, first_increase_months=7)
        == 0.02
    )
    assert (
        federal_pension_cola_rate(
            **{**INVENTED_BASE, "plan": FederalPensionPlan.CSRS},
            first_increase_months=7,
        )
        == 0.026
    )


@pytest.mark.parametrize(
    "category",
    [
        FederalAnnuityCategory.SPECIAL_8412_D1_OR_E,
        FederalAnnuityCategory.MILITARY_TECHNICIAN_DISABILITY_8414_C,
        FederalAnnuityCategory.SURVIVOR_OTHER_THAN_CHILD,
        FederalAnnuityCategory.DISABILITY_8452_A_AFTER_INITIAL_PERIOD,
    ],
)
def test_under_62_statutory_exceptions(category):
    """8462(c)(3)(B), 8452(a)(1)(B): listed exceptions get the rate."""
    assert (
        federal_pension_cola_rate(
            **{**INVENTED_BASE, "age": 55, "annuity_category": category}
        )
        == 0.035
    )


def test_initial_disability_period_has_no_cola():
    """8452(a)(1)(B)(i): no increase during the initial 60%-pay period."""
    assert (
        federal_pension_cola_rate(
            **{
                **INVENTED_BASE,
                "age": 55,
                "annuity_category": (
                    FederalAnnuityCategory.DISABILITY_8452_A_INITIAL_PERIOD
                ),
            }
        )
        == 0
    )


@settings(deadline=None)
@given(
    growth=INVENTED_GROWTH,
    months=st.integers(min_value=0, max_value=12),
    plan=st.sampled_from(list(FederalPensionPlan)),
)
def test_rates_bounded_by_rounded_cpi_and_proration(growth, months, plan):
    """8340(b)-(c), 8462(b)-(c): bounded rates and first-increase rule."""
    kwargs = {
        **INVENTED_BASE,
        "price_index_change": growth,
        "plan": plan,
    }
    full = federal_pension_cola_rate(**kwargs)
    partial = federal_pension_cola_rate(**kwargs, first_increase_months=months)
    rounded = Decimal(str(growth)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    assert 0 <= partial <= full <= float(rounded)
    assert Decimal(str(partial)) % Decimal("0.001") == 0


@settings(deadline=None)
@given(
    growth=st.floats(min_value=-1, max_value=0, allow_nan=False),
    plan=st.sampled_from(list(FederalPensionPlan)),
)
def test_no_positive_cpi_increase_gives_no_cola(growth, plan):
    """8340(b), 8462(b)(2): no COLA without a price-index increase."""
    assert (
        federal_pension_cola_rate(
            **{**INVENTED_BASE, "price_index_change": growth, "plan": plan}
        )
        == 0
    )


@settings(deadline=None)
@given(
    age=st.floats(min_value=0, max_value=61.999, allow_nan=False),
    growth=INVENTED_GROWTH,
)
def test_ordinary_fers_before_62_has_no_cola(age, growth):
    """8462(c)(3)(A): ordinary FERS age floor is exact."""
    assert (
        federal_pension_cola_rate(
            **{**INVENTED_BASE, "age": age, "price_index_change": growth}
        )
        == 0
    )


@settings(deadline=None)
@given(
    age=st.floats(min_value=0, max_value=61.999, allow_nan=False),
    growth=INVENTED_GROWTH,
    category=st.sampled_from(
        [
            FederalAnnuityCategory.SPECIAL_8412_D1_OR_E,
            FederalAnnuityCategory.MILITARY_TECHNICIAN_DISABILITY_8414_C,
            FederalAnnuityCategory.SURVIVOR_OTHER_THAN_CHILD,
            FederalAnnuityCategory.DISABILITY_8452_A_AFTER_INITIAL_PERIOD,
        ]
    ),
)
def test_statutory_exceptions_have_age_independent_rate(age, growth, category):
    """8462(c)(3)(B): these categories bypass the ordinary age floor."""
    kwargs = {**INVENTED_BASE, "price_index_change": growth}
    assert federal_pension_cola_rate(
        **{**kwargs, "age": age, "annuity_category": category}
    ) == federal_pension_cola_rate(**kwargs)


def test_monthly_annuity_dollar_rounding_and_minimum_increase():
    """8340(e), 8462(d): floor dollars, but increase at least one dollar."""
    assert (
        cola_adjusted_monthly_annuity(
            monthly_annuity=1_001,
            cola_rate=0.035,
            plan=FederalPensionPlan.FERS,
        )
        == 1_036
    )
    assert (
        cola_adjusted_monthly_annuity(
            monthly_annuity=10,
            cola_rate=0.001,
            plan=FederalPensionPlan.FERS,
        )
        == 11
    )


@settings(deadline=None)
@given(
    annuity=st.integers(min_value=0, max_value=100_000),
    cap=st.integers(min_value=0, max_value=200_000),
    growth=INVENTED_GROWTH,
)
def test_csrs_cap_cannot_lower_already_payable_annuity(annuity, cap, growth):
    """8340(g): cap restricts an increase, never reduces existing pay."""
    result = cola_adjusted_monthly_annuity(
        monthly_annuity=annuity,
        cola_rate=growth,
        plan=FederalPensionPlan.CSRS,
        csrs_statutory_cap=cap,
    )
    assert annuity <= result <= max(annuity, cap)


@settings(deadline=None)
@given(
    annuity=st.integers(min_value=1, max_value=100_000),
    growth=st.floats(
        min_value=0.000001,
        max_value=1,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_fers_amount_rounds_dollars_with_minimum_increase(annuity, growth):
    """8462(d): whole dollars below the raw amount, except the $1 floor."""
    result = cola_adjusted_monthly_annuity(
        monthly_annuity=annuity,
        cola_rate=growth,
        plan=FederalPensionPlan.FERS,
    )
    assert type(result) is int
    assert result >= annuity + 1
    raw_amount = annuity * (1 + Decimal(str(growth)))
    if raw_amount >= annuity + 1:
        assert 0 <= raw_amount - result < 1
    else:
        assert result == annuity + 1


@settings(deadline=None)
@given(growth=INVENTED_GROWTH)
def test_research_options_are_explicit_bounded_assumptions(growth):
    """Proposals in the research note are unregistered, not state plan law."""
    assert (
        assumed_pension_cola_rate(
            assumption=PensionColaAssumption.PRIVATE_FIXED_NOMINAL,
            price_index_change=growth,
        )
        == 0
    )
    rate = assumed_pension_cola_rate(
        assumption=(
            PensionColaAssumption.STATE_LOCAL_CPI_CAPPED_AT_THREE_PERCENT
        ),
        price_index_change=growth,
    )
    assert 0 <= rate <= min(growth, 0.03)


@pytest.mark.parametrize("year", [2001, 2027, None, True, 2026.0])
def test_year_outside_coverage_raises(year):
    with pytest.raises(ValueError, match="year outside"):
        federal_pension_cola_rate(**{**INVENTED_BASE, "year": year})


@pytest.mark.parametrize("age", [-1, 120.01, None, True, float("nan")])
def test_invalid_age_raises(age):
    with pytest.raises(ValueError, match="age"):
        federal_pension_cola_rate(**{**INVENTED_BASE, "age": age})


@pytest.mark.parametrize("name", ["plan", "annuity_category"])
@pytest.mark.parametrize("option", [None, "unknown", 1])
def test_unsupported_plan_or_annuity_category_raises(name, option):
    with pytest.raises(ValueError, match="unsupported"):
        federal_pension_cola_rate(**{**INVENTED_BASE, name: option})


@pytest.mark.parametrize("growth", [None, True, "0.01", float("inf")])
def test_invalid_growth_raises(growth):
    with pytest.raises(ValueError, match="finite number"):
        federal_pension_cola_rate(
            **{**INVENTED_BASE, "price_index_change": growth}
        )


@pytest.mark.parametrize("months", [-1, 13, None, True, 12.0])
def test_invalid_first_month_count_raises(months):
    with pytest.raises(ValueError, match="first_increase_months"):
        federal_pension_cola_rate(
            **INVENTED_BASE, first_increase_months=months
        )


def test_fers_category_cannot_describe_csrs():
    with pytest.raises(ValueError, match="FERS-specific"):
        federal_pension_cola_rate(
            **{
                **INVENTED_BASE,
                "plan": FederalPensionPlan.CSRS,
                "annuity_category": (
                    FederalAnnuityCategory.SPECIAL_8412_D1_OR_E
                ),
            }
        )


@pytest.mark.parametrize(
    "category",
    [
        FederalAnnuityCategory.DISABILITY_8452_A_INITIAL_PERIOD,
        FederalAnnuityCategory.DISABILITY_8452_A_AFTER_INITIAL_PERIOD,
    ],
)
def test_disability_component_requires_redetermination_at_62(category):
    """8452(b): callers must redetermine disability annuities at 62."""
    with pytest.raises(ValueError, match="redetermined at 62"):
        federal_pension_cola_rate(
            **{**INVENTED_BASE, "annuity_category": category}
        )


@pytest.mark.parametrize("invalid", [-1, 1.0, None, True])
def test_invalid_monthly_annuity_raises(invalid):
    with pytest.raises(ValueError, match="monthly_annuity"):
        cola_adjusted_monthly_annuity(
            monthly_annuity=invalid,
            cola_rate=0.01,
            plan=FederalPensionPlan.FERS,
        )


@pytest.mark.parametrize("invalid", [-1, None, True, float("inf")])
def test_invalid_cola_rate_raises(invalid):
    with pytest.raises(ValueError):
        cola_adjusted_monthly_annuity(
            monthly_annuity=1_000,
            cola_rate=invalid,
            plan=FederalPensionPlan.FERS,
        )


@pytest.mark.parametrize("invalid", [-1, None, True, 1.0])
def test_csrs_without_valid_statutory_cap_raises(invalid):
    with pytest.raises(ValueError, match="requires a whole-dollar"):
        cola_adjusted_monthly_annuity(
            monthly_annuity=1_000,
            cola_rate=0.01,
            plan=FederalPensionPlan.CSRS,
            csrs_statutory_cap=invalid,
        )


def test_fers_with_csrs_cap_raises():
    with pytest.raises(ValueError, match="does not apply"):
        cola_adjusted_monthly_annuity(
            monthly_annuity=1_000,
            cola_rate=0.01,
            plan=FederalPensionPlan.FERS,
            csrs_statutory_cap=2_000,
        )


def test_unsupported_monthly_adjustment_plan_raises():
    with pytest.raises(ValueError, match="unsupported"):
        cola_adjusted_monthly_annuity(
            monthly_annuity=1_000, cola_rate=0.01, plan="unknown"
        )


def test_unknown_research_assumption_raises():
    with pytest.raises(ValueError, match="unsupported"):
        assumed_pension_cola_rate(
            assumption="unregistered_default", price_index_change=0.01
        )


def test_invalid_research_growth_raises():
    with pytest.raises(ValueError, match="finite number"):
        assumed_pension_cola_rate(
            assumption=PensionColaAssumption.PRIVATE_FIXED_NOMINAL,
            price_index_change=float("nan"),
        )


def test_unknown_parameter_version_raises(tmp_path, monkeypatch):
    invented_path = tmp_path / "INVENTED_unsupported_parameters.json"
    invented_path.write_text(json.dumps({"version": "INVENTED_unknown"}))
    monkeypatch.setattr(pension_cola, "_PARAMETER_PATH", invented_path)
    with pytest.raises(ValueError, match="parameter version"):
        federal_pension_cola_rate(**INVENTED_BASE)


def test_captured_sources_match_manifest():
    """Pin every legal/statistical capture, including preserved captures."""
    source_dir = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "external"
        / "income_resources/retirement_rules_v1/ssi_cola"
    )
    manifest = json.loads((source_dir / "capture_manifest.json").read_text())
    for source in manifest:
        if source["status"] != "CAPTURED":
            continue
        captured = (source_dir / source["file"]).read_bytes()
        assert len(captured) == source["bytes"]
        assert hashlib.sha256(captured).hexdigest() == source["sha256"]
        assert source["retrieved_at_utc"].endswith("+00:00")
        assert source["url"].startswith("https://")
