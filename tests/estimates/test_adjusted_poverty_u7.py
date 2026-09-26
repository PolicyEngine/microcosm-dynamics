"""Row U7 in the adjusted income concept: WEALTH1 plus employer DC.

Every number here is INVENTED: the life table, the thresholds, the SSI
parameters and the family rows are made up (the arithmetic is written
next to each assertion), or drawn by Hypothesis.  None is a PSID value, a
Census threshold, an SSA parameter or a result.

Invariants held for every input (property tests), comparing row U7
(``financial_assets="wealth1_plus_employer_dc"``) with the primary U0
(``"wealth1"``) on the same rows, under each SSI rule:

* U7's financial assets are WEALTH1 plus the employer DC balance, and U0's
  are WEALTH1 (``employer_dc_added`` is the balance or 0);
* the annuity difference is ``0.8 * (max(W + D, 0) - max(W, 0)) / price``,
  never negative (the balance can only raise the annuity);
* baseline and reform income both rise by exactly that difference: the
  cut, the SSI offset and U3's take-up (whose resource proxy stays on
  WEALTH1) do not move, so reform minus baseline is the same in U0 and U7;
* therefore a member poor under U7 is poor under U0, at baseline and
  under the reform;
* with a zero balance U7 equals U0 (differential: every output column).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.estimates import adjusted_poverty as ap

#: INVENTED life table, ages 0-4 (not a real table).
MOCK_LIFE_TABLE = ap.LifeTable(
    name=ap.INVENTED_LIFE_TABLE,
    qx={
        "male": (0.0, 0.0, 0.2, 0.5, 1.0),
        "female": (0.0, 0.0, 0.1, 0.25, 1.0),
    },
    source={"kind": "invented"},
)
#: INVENTED rate with v = 0.8.
RATE = 0.25
#: INVENTED thresholds for income year 2010 (not Census values).
_WA = {
    "one_under_65": 1100.0,
    "one_65_plus": 1000.0,
    "two_under_65": 1400.0,
    "two_65_plus": 1300.0,
    "three": 1700.0,
    "four": 2200.0,
    "five": 2600.0,
    "six": 3000.0,
    "seven": 3400.0,
    "eight": 3800.0,
    "nine_plus": 4500.0,
}
MOCK_THRESHOLDS = ap.PovertyThresholds(
    weighted_average={2010: _WA},
    matrix={
        2010: {
            key: {k: value - 10.0 * k for k in range(9)}
            for key, value in _WA.items()
        }
    },
    provenance={"kind": "invented"},
)
#: INVENTED SSI parameters: FBR 50/75 a month.
MOCK_SSI = ap.SsiParameters(
    fbr_individual_monthly={2010: 50.0},
    fbr_couple_monthly={2010: 75.0},
    general_income_exclusion_monthly=20.0,
    earned_income_exclusion_monthly=65.0,
    earned_income_share_excluded=0.5,
    resource_limit_individual=2000.0,
    resource_limit_couple=3000.0,
    provenance={"kind": "invented"},
)
U7 = "wealth1_plus_employer_dc"


def _row(observation_id: str, **overrides) -> dict:
    row = {column: 0 for column in ap.REQUIRED_COLUMNS}
    row.update(
        observation_id=observation_id,
        family_unit_id=observation_id,
        birth_year=1943,
        income_year=2010,
        member_role="head",
        member_age=2,
        member_sex="male",
        member_married_coresident=False,
        spouse_age=None,
        spouse_sex=None,
        fu_head_age=2,
        fu_head_sex="male",
        fu_head_spouse_present=False,
        fu_head_spouse_age=None,
        fu_head_spouse_sex=None,
        wife_present=False,
        fu_size=1,
        n_children=0,
        census_needs_standard=1234,
        employer_dc=0,
    )
    row.update(overrides)
    return row


def _run(rows: list[dict], **spec) -> pd.DataFrame:
    base = {"real_interest_rate": RATE}
    base.update(spec)
    return ap.adjusted_incomes(
        pd.DataFrame(rows),
        ap.AdjustedPovertySpec(**base),
        data_provenance=ap.INVENTED,
        life_table=MOCK_LIFE_TABLE,
        thresholds=MOCK_THRESHOLDS,
        ssi=MOCK_SSI,
    ).set_index("observation_id")


_COUPLE = dict(
    fu_head_spouse_present=True,
    fu_head_spouse_age=2,
    fu_head_spouse_sex="female",
    wife_present=True,
    fu_size=2,
)


# ---------------------------------------------------------------------------
# The worked cases of specification section 13
# ---------------------------------------------------------------------------
def test_u7_annuity_by_hand():
    # joint price male 2 + female 2 at v = 0.8 is 1.024 (section 13)
    rows = [_row("a", wealth1=1_024, employer_dc=256, **_COUPLE)]
    u0 = _run(rows)
    u7 = _run(rows, financial_assets=U7)
    assert u0.loc["a", "annuity_factor"] == pytest.approx(1.024)
    assert u0.loc["a", "annuity"] == pytest.approx(800.0)  # .8*1024/1.024
    assert u7.loc["a", "annuity"] == pytest.approx(1_000.0)  # .8*1280/1.024
    assert u0.loc["a", "employer_dc_added"] == 0
    assert u7.loc["a", "employer_dc_added"] == 256
    assert u7.loc["a", "financial_assets"] == 1_280


def test_u7_with_negative_wealth1_by_hand():
    rows = [
        _row("a", wealth1=-500, employer_dc=300, **_COUPLE),
        _row("b", wealth1=-500, employer_dc=700, **_COUPLE),
    ]
    u7 = _run(rows, financial_assets=U7)
    assert u7.loc["a", "annuity"] == 0.0  # .8 * max(-200, 0)
    assert u7.loc["b", "annuity"] == pytest.approx(156.25)  # .8*200/1.024
    assert _run(rows).loc["b", "annuity"] == 0.0


def test_u7_refuses_rows_without_a_whole_non_negative_balance():
    with pytest.raises(ap.AdjustedPovertyError, match="employer_dc column"):
        _run(
            [
                {
                    k: v
                    for k, v in _row("a", wealth1=10).items()
                    if k != "employer_dc"
                }
            ],
            financial_assets=U7,
        )
    for bad in (-1, 1.5, None):
        with pytest.raises(ap.AdjustedPovertyError, match="employer_dc"):
            _run([_row("a", employer_dc=bad)], financial_assets=U7)
    # the primary never reads the column
    _run(
        [{k: v for k, v in _row("a").items() if k != "employer_dc"}],
    )
    with pytest.raises(ap.AdjustedPovertyError, match="financial_assets"):
        ap.AdjustedPovertySpec(financial_assets="wealth2")


def test_financial_assets_is_a_pending_freeze_decision():
    decisions = {item.field: item for item in ap.pending_decisions()}
    decision = decisions["financial_assets"]
    assert decision.default == "wealth1"
    assert decision.alternatives == (U7,)
    assert "R5" in decision.default_basis
    assert not decision.awaiting.startswith("Max")


# ---------------------------------------------------------------------------
# Property tests (Hypothesis): U7 against U0 on the same rows
# ---------------------------------------------------------------------------
_MONEY = st.integers(0, 4_000)


@st.composite
def _family_rows(draw) -> list[dict]:
    n = draw(st.integers(1, 6))
    rows = []
    for i in range(n):
        couple = draw(st.booleans())
        head_ss = draw(_MONEY)
        wife_ss = draw(_MONEY) if couple else 0
        head_ssi = draw(st.sampled_from([0, 0, 100, 400]))
        wife_ssi = draw(st.sampled_from([0, 200])) if couple else 0
        asset_income = draw(st.integers(0, 300))
        labor = draw(st.sampled_from([0, 0, 500, 2_000]))
        transfer = head_ssi + wife_ssi + draw(st.integers(0, 200))
        taxable = labor + asset_income
        extra = {
            "wealth1": draw(st.integers(-3_000, 20_000)),
            "vehicles": draw(st.integers(0, 1_000)),
            "employer_dc": draw(st.one_of(st.just(0), st.integers(1, 30_000))),
            "head_ss": head_ss,
            "wife_ss": wife_ss,
            "head_ssi": head_ssi,
            "wife_ssi": wife_ssi,
            "head_interest": asset_income,
            "head_labor": labor,
            "hw_taxable": taxable,
            "hw_transfer": transfer,
            "total_family_income": taxable + transfer + head_ss + wife_ss,
        }
        if couple:
            extra.update(_COUPLE)
        rows.append(_row(f"r{i}", **extra))
    return rows


_SSI_RULES = st.sampled_from(sorted(ap.SSI_RULES))


@settings(max_examples=60, deadline=None)
@given(_family_rows(), _SSI_RULES)
def test_u7_raises_income_by_exactly_the_added_annuity(rows, ssi_rule):
    u0 = _run(rows, ssi_rule=ssi_rule)
    u7 = _run(rows, ssi_rule=ssi_rule, financial_assets=U7)
    frame = pd.DataFrame(rows).set_index("observation_id")
    wealth = frame["wealth1"].astype(float)
    dc = frame["employer_dc"].astype(float)
    np.testing.assert_allclose(u0["employer_dc_added"], 0.0)
    np.testing.assert_allclose(u7["employer_dc_added"], dc)
    np.testing.assert_allclose(u0["financial_assets"], wealth)
    np.testing.assert_allclose(u7["financial_assets"], wealth + dc)
    added = (
        0.8
        * (np.maximum(wealth + dc, 0) - np.maximum(wealth, 0))
        / u0["annuity_factor"]
    )
    np.testing.assert_allclose(u7["annuity"] - u0["annuity"], added)
    assert (u7["annuity"] >= u0["annuity"] - 1e-9).all()
    np.testing.assert_allclose(
        u7["baseline_income"] - u0["baseline_income"], added
    )
    np.testing.assert_allclose(
        u7["reform_income"] - u0["reform_income"], added
    )
    for column in ("cut", "ssi_offset", "ssi_new", "threshold"):
        np.testing.assert_allclose(u7[column], u0[column])
    # poverty can only fall when financial assets rise
    assert not (u7["poor_baseline"] & ~u0["poor_baseline"]).any()
    assert not (u7["poor_reform"] & ~u0["poor_reform"]).any()


@settings(max_examples=40, deadline=None)
@given(_family_rows(), _SSI_RULES)
def test_u7_with_no_balance_equals_u0(rows, ssi_rule):
    """Differential: with every balance zero, U7 and U0 agree in every
    output column."""

    for row in rows:
        row["employer_dc"] = 0
    u0 = _run(rows, ssi_rule=ssi_rule)
    u7 = _run(rows, ssi_rule=ssi_rule, financial_assets=U7)
    pd.testing.assert_frame_equal(u0, u7)
