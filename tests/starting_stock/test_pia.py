"""Worked examples and error paths for the starting-stock package.

Every number here is invented for the test and stands for no year's
law or data.
"""

from __future__ import annotations

import hashlib
import importlib
import math
import sys

import pytest

from populace_dynamics import claiming
from populace_dynamics.starting_stock import (
    benefit_from_pia,
    claim_age_posterior,
    cola_factor,
    disabled_worker_claim_factor,
    draw_claim_age,
    has_all_four_components,
    has_two_reasons,
    infer_pia,
    is_top_coded,
    needs_linked_pia,
    retired_worker_claim_factor,
    rounding_bound,
    single_year_age,
)

#: Invented December adjustments.
RATES = {2020: 0.02, 2021: 0.05, 2022: 0.03}
PATH = dict(cola_rates=RATES, eligibility_year=2020, payment_year=2023)


def _uniform(prefix: str, seed: int, person_id: int) -> float:
    """The brief's recipe, written out independently of the package."""
    key = f"{prefix}|{seed}|{person_id}".encode("ascii")
    digest = hashlib.sha256(key).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


# --------------------------------------------------------------------------
# The import guard
# --------------------------------------------------------------------------
def test_import_guard_keeps_barred_modules_out(barred_module_names):
    """Importing the package leaves both barred modules unloaded.

    The guard refuses them whenever this package's or these tests' code
    is on the stack, so neither can enter ``sys.modules`` through them.
    A session that also runs other test modules may load one first; a
    cached module bypasses every finder, so the check can't run there.
    """
    preloaded = sorted(n for n in barred_module_names if n in sys.modules)
    if preloaded:
        pytest.skip(
            f"{preloaded} loaded earlier in this session, outside the "
            "guard's scope; run this module on its own to check"
        )
    for name in (
        "populace_dynamics.starting_stock",
        "populace_dynamics.starting_stock.pia",
        "populace_dynamics.starting_stock.claim_age",
        "populace_dynamics.starting_stock.limits",
    ):
        importlib.import_module(name)
    assert len(barred_module_names) == 2
    for name in barred_module_names:
        assert name not in sys.modules
    finders = [type(finder).__name__ for finder in sys.meta_path]
    assert "_BarredModuleFinder" in finders


# --------------------------------------------------------------------------
# cola_factor
# --------------------------------------------------------------------------
def test_cola_factor_worked_example():
    assert cola_factor(RATES, 2020, 2023) == pytest.approx(1.02 * 1.05 * 1.03)
    assert cola_factor(RATES, 2020, 2022) == pytest.approx(1.071)
    # The eligibility year's own adjustment applies; the payment year's
    # doesn't.
    assert cola_factor(RATES, 2022, 2023) == pytest.approx(1.03)
    assert cola_factor(RATES, 2020, 2020) == 1.0


def test_cola_factor_missing_year():
    with pytest.raises(KeyError, match="2023"):
        cola_factor(RATES, 2020, 2024)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_cola_factor_non_finite_rate(bad):
    with pytest.raises(ValueError, match="finite"):
        cola_factor({2020: 0.02, 2021: bad}, 2020, 2022)


def test_cola_factor_payment_before_eligibility():
    with pytest.raises(ValueError, match="before"):
        cola_factor(RATES, 2021, 2020)


@pytest.mark.parametrize("bad", [-1.0, -1.5])
def test_cola_factor_rate_of_minus_one_or_less(bad):
    with pytest.raises(ValueError, match="positive"):
        cola_factor({2020: bad}, 2020, 2021)


@pytest.mark.parametrize("year", [2020.0, "2020", True])
def test_cola_factor_non_integer_year(year):
    with pytest.raises(TypeError, match="integer"):
        cola_factor(RATES, year, 2023)


def test_cola_factor_non_numeric_rate():
    with pytest.raises(TypeError, match="real number"):
        cola_factor({2020: "0.02"}, 2020, 2021)


# --------------------------------------------------------------------------
# benefit_from_pia
# --------------------------------------------------------------------------
def test_benefit_from_pia_worked_example_unrounded():
    benefit = benefit_from_pia(
        1500.0, **PATH, claim_factor=0.8, statutory_rounding=False
    )
    assert benefit == pytest.approx(1500.0 * 1.10313 * 0.8)


def test_benefit_from_pia_worked_example_rounded():
    # 1500.00 x 1.02 = 1530.000 -> 1530.0
    # 1530.00 x 1.05 = 1606.500 -> 1606.5
    # 1606.50 x 1.03 = 1654.695 -> 1654.6 (down to the dime)
    # 1654.60 x 0.80 = 1323.680 -> 1323   (down to the dollar)
    benefit = benefit_from_pia(
        1500.0, **PATH, claim_factor=0.8, statutory_rounding=True
    )
    assert benefit == 1323.0


def test_benefit_from_pia_no_adjustment_skips_the_dime():
    # No adjustment, so no dime floor: 1234.56 x 0.75 = 925.92 -> 925.
    benefit = benefit_from_pia(
        1234.56,
        cola_rates={},
        eligibility_year=2024,
        payment_year=2024,
        claim_factor=0.75,
        statutory_rounding=True,
    )
    assert benefit == 925.0


def test_benefit_from_pia_zero_pia():
    for rounding in (False, True):
        assert (
            benefit_from_pia(
                0.0, **PATH, claim_factor=0.8, statutory_rounding=rounding
            )
            == 0.0
        )


@pytest.mark.parametrize("bad", [-0.01, math.nan, math.inf])
def test_benefit_from_pia_bad_pia(bad):
    with pytest.raises(ValueError):
        benefit_from_pia(
            bad, **PATH, claim_factor=0.8, statutory_rounding=True
        )


@pytest.mark.parametrize("bad", [0.0, -0.5, math.nan, math.inf])
def test_benefit_from_pia_bad_claim_factor(bad):
    with pytest.raises(ValueError):
        benefit_from_pia(
            1500.0, **PATH, claim_factor=bad, statutory_rounding=True
        )


def test_benefit_from_pia_non_numeric_pia():
    with pytest.raises(TypeError, match="real number"):
        benefit_from_pia(
            "1500", **PATH, claim_factor=0.8, statutory_rounding=True
        )


def test_benefit_from_pia_passes_cola_errors_through():
    with pytest.raises(KeyError):
        benefit_from_pia(
            1500.0,
            cola_rates=RATES,
            eligibility_year=2020,
            payment_year=2025,
            claim_factor=0.8,
            statutory_rounding=False,
        )


# --------------------------------------------------------------------------
# infer_pia
# --------------------------------------------------------------------------
def test_infer_pia_worked_example():
    benefit = 1500.0 * 1.10313 * 0.8
    assert infer_pia(benefit, **PATH, claim_factor=0.8) == pytest.approx(
        1500.0
    )
    # A rounded benefit infers an unrounded PIA: 1323 / (1.10313 x 0.8).
    assert infer_pia(1323.0, **PATH, claim_factor=0.8) == pytest.approx(
        1323.0 / 0.882504
    )


def test_infer_pia_zero_benefit_returns_zero():
    for zero in (0.0, -0.0, 0):
        result = infer_pia(zero, **PATH, claim_factor=0.8)
        assert result == 0.0
        assert math.copysign(1.0, result) == 1.0


@pytest.mark.parametrize("bad", [-1.0, math.nan, math.inf, -math.inf])
def test_infer_pia_bad_benefit(bad):
    with pytest.raises(ValueError):
        infer_pia(bad, **PATH, claim_factor=0.8)


@pytest.mark.parametrize("bad", [0.0, -0.8, math.nan, math.inf])
def test_infer_pia_bad_claim_factor(bad):
    with pytest.raises(ValueError):
        infer_pia(1000.0, **PATH, claim_factor=bad)


def test_infer_pia_combined_factor_overflows():
    huge = {2020: 1e200, 2021: 1e200}
    with pytest.raises(ValueError, match="combined factor"):
        infer_pia(
            1000.0,
            cola_rates=huge,
            eligibility_year=2020,
            payment_year=2022,
            claim_factor=1.0,
        )


def test_infer_pia_non_numeric_benefit():
    with pytest.raises(TypeError, match="real number"):
        infer_pia(None, **PATH, claim_factor=0.8)


def test_infer_pia_passes_cola_errors_through():
    with pytest.raises(ValueError, match="before"):
        infer_pia(
            1000.0,
            cola_rates=RATES,
            eligibility_year=2023,
            payment_year=2020,
            claim_factor=0.8,
        )


# --------------------------------------------------------------------------
# rounding_bound
# --------------------------------------------------------------------------
def test_rounding_bound_worked_example():
    # S_1 = 1, S_2 = 1 x 1.05 + 1 = 2.05, S_3 = 2.05 x 1.03 + 1 = 3.1115;
    # bound = 0.1 x 0.8 x 3.1115 + 1 = 1.24892.
    bound = rounding_bound(**PATH, claim_factor=0.8)
    assert bound == pytest.approx(1.24892)
    # The round trip from 1323 opens a one-dollar gap, inside the bound:
    # 1499.143... -> 1529.1 -> 1605.5 -> 1653.6 -> 1322.88 -> 1322.
    pia = infer_pia(1323.0, **PATH, claim_factor=0.8)
    back = benefit_from_pia(
        pia, **PATH, claim_factor=0.8, statutory_rounding=True
    )
    assert back == 1322.0
    assert abs(back - 1323.0) <= bound


def test_rounding_bound_without_adjustment_is_one_dollar():
    bound = rounding_bound(
        cola_rates={},
        eligibility_year=2024,
        payment_year=2024,
        claim_factor=0.7,
    )
    assert bound == 1.0


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan])
def test_rounding_bound_bad_claim_factor(bad):
    with pytest.raises(ValueError):
        rounding_bound(**PATH, claim_factor=bad)


def test_rounding_bound_passes_cola_errors_through():
    with pytest.raises(KeyError):
        rounding_bound(
            cola_rates=RATES,
            eligibility_year=2019,
            payment_year=2023,
            claim_factor=0.8,
        )


# --------------------------------------------------------------------------
# Claim factors
# --------------------------------------------------------------------------
def test_retired_worker_claim_factor_worked_example(invented_ssa_parameters):
    params = invented_ssa_parameters
    # Born 1960: the INVENTED full retirement age is 798 months.
    # At 62 (744 months), 54 months early: 30 x 0.006 + 24 x 0.004 = 0.276.
    assert retired_worker_claim_factor(744, 1960, params) == pytest.approx(
        0.724
    )
    assert retired_worker_claim_factor(798, 1960, params) == 1.0
    # At 70 (840 months), 42 months late at 0.07 a year: + 0.245.
    assert retired_worker_claim_factor(840, 1960, params) == pytest.approx(
        1.245
    )
    for months in (744, 770, 798, 820, 840):
        assert retired_worker_claim_factor(
            months, 1960, params
        ) == claiming.benefit_factor(months, 1960, params)


def test_retired_worker_claim_factor_uncovered_birth_year(
    invented_ssa_parameters,
):
    with pytest.raises(KeyError):
        retired_worker_claim_factor(744, 1850, invented_ssa_parameters)


def test_disabled_worker_claim_factor_is_one():
    assert disabled_worker_claim_factor() == 1.0
    # So a disabled worker's PIA is the benefit over the COLA factor.
    assert infer_pia(
        1103.13, **PATH, claim_factor=disabled_worker_claim_factor()
    ) == pytest.approx(1000.0)


# --------------------------------------------------------------------------
# claim_age_posterior
# --------------------------------------------------------------------------
#: Invented award shares by (entitlement year, claim age), in percent.
_TABLE = {
    "female": {(2022, 62): 40.0, (2023, 63): 20.0, (2024, 64): 40.0},
    "male": {(2022, 62): 10.0, (2023, 63): 30.0, (2024, 64): 60.0},
}


class _Shares:
    """Invented award shares that record how they were called."""

    def __init__(self, table=None):
        self.table = _TABLE if table is None else table
        self.calls = []

    def __call__(self, sex, year):
        self.calls.append((sex, year))
        return {
            age: self.table[sex].get((year, age), 0.0)
            for age in claiming.CLAIM_AGES
        }


def test_claim_age_posterior_worked_example():
    shares = _Shares()
    # Aged 64, born 1960: claim ages 62, 63 and 64, entitled in 2022,
    # 2023 and 2024.
    posterior = claim_age_posterior(64, 1960, "female", award_shares=shares)
    assert posterior == pytest.approx({62: 0.4, 63: 0.2, 64: 0.4})
    assert list(posterior) == [62, 63, 64]
    assert shares.calls == [
        ("female", 2022),
        ("female", 2023),
        ("female", 2024),
    ]
    male = claim_age_posterior(64, 1960, "male", award_shares=_Shares())
    assert male == pytest.approx({62: 0.1, 63: 0.3, 64: 0.6})


def test_claim_age_posterior_stops_at_seventy():
    def flat(sex, year):
        return {age: 1.0 for age in claiming.CLAIM_AGES}

    posterior = claim_age_posterior(83, 1940, "male", award_shares=flat)
    assert list(posterior) == list(range(62, 71))
    assert posterior[70] == pytest.approx(1 / 9)


def test_claim_age_posterior_under_62():
    with pytest.raises(ValueError, match="no claim age"):
        claim_age_posterior(61, 1963, "female", award_shares=_Shares())


def test_claim_age_posterior_all_zero():
    # Born 1950, aged 70: the table holds no share for 2012 to 2020.
    with pytest.raises(ValueError, match="every weight is zero"):
        claim_age_posterior(70, 1950, "female", award_shares=_Shares())


@pytest.mark.parametrize("bad", [-5.0, math.nan, math.inf])
def test_claim_age_posterior_bad_share(bad):
    table = {"female": {(2022, 62): 40.0, (2023, 63): bad}}
    with pytest.raises(ValueError):
        claim_age_posterior(64, 1960, "female", award_shares=_Shares(table))


def test_claim_age_posterior_missing_age():
    def partial(sex, year):
        return {62: 1.0}

    with pytest.raises(KeyError, match="claim age 63"):
        claim_age_posterior(63, 1960, "male", award_shares=partial)


def test_claim_age_posterior_non_integer_age():
    with pytest.raises(TypeError, match="integer"):
        claim_age_posterior(64.5, 1960, "female", award_shares=_Shares())


# --------------------------------------------------------------------------
# draw_claim_age
# --------------------------------------------------------------------------
def test_draw_claim_age_worked_example():
    u = _uniform("populace_dynamics.starting_stock.claim_age.v1", 7, 12345)
    assert 0.0 <= u < 1.0
    # Walk 62 (0.4), 63 (0.6 cumulative), 64 (1.0).
    expected = 62 if u < 0.4 else 63 if u < 0.6 else 64
    drawn = draw_claim_age(
        12345, 64, 1960, "female", award_shares=_Shares(), seed=7
    )
    assert drawn == expected
    # The uniform for this key is 0.1836..., so the draw is 62.
    assert u == pytest.approx(0.18360, abs=1e-5)
    assert drawn == 62


def test_draw_claim_age_follows_the_key():
    a = draw_claim_age(5, 66, 1958, "male", award_shares=_flat, seed=11)
    b = draw_claim_age(5, 66, 1958, "male", award_shares=_flat, seed=11)
    assert a == b
    seen = {
        draw_claim_age(pid, 66, 1958, "male", award_shares=_flat, seed=11)
        for pid in range(200)
    }
    assert seen == {62, 63, 64, 65, 66}


def _flat(sex, year):
    return {age: 1.0 for age in claiming.CLAIM_AGES}


@pytest.mark.parametrize("bad", [1.5, "7", True, None])
def test_draw_claim_age_bad_seed(bad):
    with pytest.raises(TypeError):
        draw_claim_age(1, 66, 1958, "male", award_shares=_flat, seed=bad)


@pytest.mark.parametrize("bad", [2.0, "12", False])
def test_draw_claim_age_bad_person_id(bad):
    with pytest.raises(TypeError):
        draw_claim_age(bad, 66, 1958, "male", award_shares=_flat, seed=1)


def test_draw_claim_age_passes_posterior_errors_through():
    with pytest.raises(ValueError, match="no claim age"):
        draw_claim_age(1, 60, 1964, "male", award_shares=_flat, seed=1)


# --------------------------------------------------------------------------
# single_year_age
# --------------------------------------------------------------------------
def _band_shares(top_code, sex):
    if top_code == 80:
        return {80: 1.0, 81: 1.0, 82: 1.0, 83: 1.0, 84: 1.0}
    return {85: 4.0, 86: 3.0, 87: 2.0, 88: 1.0}


def test_single_year_age_worked_example():
    u = _uniform(
        "populace_dynamics.starting_stock.single_year_age.v1", 7, 12345
    )
    drawn = single_year_age(
        12345, 80, "female", age_shares=_band_shares, seed=7
    )
    # The uniform for this key is 0.8443..., the fifth of five ages.
    assert u == pytest.approx(0.84430, abs=1e-5)
    assert drawn == 80 + int(u * 5)
    assert drawn == 84
    # The single-year key is not the claim-age key, so the two uniforms
    # differ for the same seed and person.
    assert u != _uniform(
        "populace_dynamics.starting_stock.claim_age.v1", 7, 12345
    )
    upper = single_year_age(
        12345, 85, "female", age_shares=_band_shares, seed=7
    )
    cumulative = [0.4, 0.7, 0.9, 1.0]
    assert upper == 85 + next(i for i, c in enumerate(cumulative) if c > u)
    assert upper == 87


@pytest.mark.parametrize("code", [79, 81, 84, 86])
def test_single_year_age_not_a_top_code(code):
    with pytest.raises(ValueError, match="not a top code"):
        single_year_age(1, code, "male", age_shares=_band_shares, seed=1)


@pytest.mark.parametrize(
    "code, shares",
    [(80, {80: 1.0, 85: 1.0}), (85, {84: 1.0, 85: 1.0})],
)
def test_single_year_age_share_outside_the_band(code, shares):
    with pytest.raises(ValueError, match="outside"):
        single_year_age(
            1, code, "male", age_shares=lambda c, s: shares, seed=1
        )


@pytest.mark.parametrize(
    "shares",
    [{80: -1.0, 81: 2.0}, {80: math.nan}, {80: 0.0, 81: 0.0}, {}],
)
def test_single_year_age_bad_shares(shares):
    with pytest.raises(ValueError):
        single_year_age(1, 80, "male", age_shares=lambda c, s: shares, seed=1)


def test_single_year_age_bad_seed():
    with pytest.raises(TypeError):
        single_year_age(1, 80, "male", age_shares=_band_shares, seed=0.5)


# --------------------------------------------------------------------------
# limits
# --------------------------------------------------------------------------
def test_has_two_reasons_worked_example():
    assert has_two_reasons(1, 3) is True
    assert has_two_reasons(1, 0) is False
    assert has_two_reasons(0, 0) is False


def test_has_all_four_components_worked_example():
    assert has_all_four_components(900.0, 50.0, 25.0, 10.0) is True
    assert has_all_four_components(900.0, 0.0, 25.0, 10.0) is False


def test_is_top_coded_worked_example():
    assert is_top_coded(80) is True
    assert is_top_coded(85) is True
    assert is_top_coded(79) is False
    assert is_top_coded(84) is False


def test_needs_linked_pia_worked_example():
    assert needs_linked_pia(300.0, 0.0) is True
    assert needs_linked_pia(0.0, 120.0) is True
    assert needs_linked_pia(0.0, 0.0) is False


@pytest.mark.parametrize(
    "call",
    [
        lambda: has_two_reasons(math.nan, 1),
        lambda: has_all_four_components(1.0, 1.0, 1.0, math.inf),
        lambda: is_top_coded(math.nan),
        lambda: needs_linked_pia(math.nan, 0.0),
    ],
)
def test_limits_refuse_non_finite_values(call):
    with pytest.raises(ValueError, match="finite"):
        call()


@pytest.mark.parametrize(
    "call",
    [
        lambda: has_two_reasons("1", 1),
        lambda: has_all_four_components(1.0, 1.0, None, 1.0),
        lambda: is_top_coded(True),
        lambda: needs_linked_pia(0.0, "5"),
    ],
)
def test_limits_refuse_non_numbers(call):
    with pytest.raises(TypeError, match="real number"):
        call()
