"""U1's worked cases, retained for U2 on U2's entry point (section 13).

INVENTED DATA - NOT A COMPARISON.  Section 13 retains "the applicable U1
worked cases for annuity prices, strict-threshold poverty, SSI caps and
exclusions, new enrollment, farm losses, retirement-account removal,
unresolved marital status, annuitant ages and employer-DC routing".
U1's own cases (``tests/estimates/test_adjusted_poverty.py``) stay
unmodified; they use an invented 25 percent interest rate and income
year 2010, which U2's parameters refuse (U2 registers 3 percent and the
2 percent sensitivity, and income years 2012-2022).  So each applicable
case is re-worked here by hand through
:func:`populace_dynamics.uniform_cut_track_u2.estimator.
u2_adjusted_incomes` in income year 2014 (a member born 1947, 67 in
2014) at 3 percent, with ``v = 1 / 1.03`` and the same invented life
table, thresholds and SSI amounts as U1's cases.  The arithmetic is next
to each assertion.  Unresolved marital status, annuitant ages and the
employer-DC routes are builder and adapter cases; they are held in
``test_u2_roles.py``, ``test_u2_plans.py`` and ``test_u2_employer_dc.py``
and only their income-concept consequences appear here.  None of these
numbers is a PSID value, a Census threshold, an SSA parameter or a
result.
"""

from __future__ import annotations

import pandas as pd
import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import estimator, rows, sources

YEAR = 2014
V = 1 / 1.03
#: INVENTED life table, ages 0-4 (U1's worked-case table, not a real one).
MOCK_LIFE_TABLE = ap.LifeTable(
    name=ap.INVENTED_LIFE_TABLE,
    qx={
        "male": (0.0, 0.0, 0.2, 0.5, 1.0),
        "female": (0.0, 0.0, 0.1, 0.25, 1.0),
    },
    source={"kind": "invented"},
)
#: Immediate single-life factors from age 2 (U1's survival curves):
#: male t_p_x = 1, .8, .4, 0; female 1, .9, .675, 0.
A_MALE = 0.8 * V + 0.4 * V**2
A_FEMALE = 0.9 * V + 0.675 * V**2
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


def _matrix_row(base: float, columns: int) -> dict[int, float]:
    return {k: base - 10.0 * k for k in range(columns)}


#: INVENTED thresholds for 2014 (U1's worked-case values, not Census).
MOCK_THRESHOLDS = ap.PovertyThresholds(
    weighted_average={YEAR: _WA},
    matrix={
        YEAR: {
            "one_under_65": _matrix_row(1110.0, 1),
            "one_65_plus": _matrix_row(1010.0, 1),
            "two_under_65": _matrix_row(1410.0, 2),
            "two_65_plus": _matrix_row(1310.0, 2),
            **{
                key: _matrix_row(_WA[key] + 5.0, min(size - 1, 8) + 1)
                for key, size in (
                    ("three", 3),
                    ("four", 4),
                    ("five", 5),
                    ("six", 6),
                    ("seven", 7),
                    ("eight", 8),
                    ("nine_plus", 9),
                )
            },
        }
    },
    provenance={"kind": "invented"},
)
#: INVENTED SSI parameters: FBR 50/75 a month (600/900 a year).
MOCK_SSI = ap.SsiParameters(
    fbr_individual_monthly={YEAR: 50.0},
    fbr_couple_monthly={YEAR: 75.0},
    general_income_exclusion_monthly=20.0,
    earned_income_exclusion_monthly=65.0,
    earned_income_share_excluded=0.5,
    resource_limit_individual=2000.0,
    resource_limit_couple=3000.0,
    provenance={"kind": "invented"},
)


def _row(observation_id: str, **overrides) -> dict:
    row = {column: 0 for column in estimator.REQUIRED_COLUMNS}
    row.update(
        observation_id=observation_id,
        family_unit_id=observation_id,
        birth_year=1947,
        income_year=YEAR,
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
    )
    row.update(overrides)
    return row


def _run(*records, **spec) -> pd.DataFrame:
    frame = pd.DataFrame(list(records))
    frame.attrs.update(
        provenance_kind="invented",
        target_id="U2",
        role_context=sources.INVENTED_DECLARED,
    )
    return estimator.u2_adjusted_incomes(
        frame,
        estimator.U2IncomeSpec(**spec),
        context=estimator.U2EstimatorContext(sources.INVENTED_DECLARED),
        data_provenance=ap.INVENTED,
        life_table=MOCK_LIFE_TABLE,
        thresholds=MOCK_THRESHOLDS,
        ssi=MOCK_SSI,
    ).set_index("observation_id")


def _row_spec(row_id: str) -> dict:
    return dict(rows.REGISTERED_ROWS[row_id].income)


# ---------------------------------------------------------------------------
# Annuity prices
# ---------------------------------------------------------------------------
def test_single_life_annuity_price_by_hand():
    # A_MALE = .8/1.03 + .4/1.03^2 = 1.153737...
    assert ap.annuity_factor_single(
        MOCK_LIFE_TABLE, "male", 2, rate=0.03
    ) == pytest.approx(A_MALE)
    assert A_MALE == pytest.approx(1.1537374634)
    out = _run(_row("a", total_family_income=0, wealth1=1000))
    # annuity = .8 * 1000 / 1.153737... = 693.3908...
    assert out.loc["a", "annuity_factor"] == pytest.approx(A_MALE)
    assert out.loc["a", "annuity"] == pytest.approx(800 / A_MALE)
    assert out.loc["a", "annuity_basis"] == "single:male2"


def test_joint_annuity_price_on_the_head_and_legal_spouse():
    # Survivor share .5: .5 * (A_MALE + A_FEMALE); A_FEMALE =
    # .9/1.03 + .675/1.03^2 = 1.510040...
    joint = 0.5 * (A_MALE + A_FEMALE)
    out = _run(
        _row(
            "a",
            member_married_coresident=True,
            spouse_age=2,
            spouse_sex="female",
            fu_head_spouse_present=True,
            fu_head_spouse_age=2,
            fu_head_spouse_sex="female",
            wife_present=True,
            fu_size=2,
            wealth1=1024,
        )
    )
    assert out.loc["a", "annuity_factor"] == pytest.approx(joint)
    assert out.loc["a", "annuity"] == pytest.approx(0.8 * 1024 / joint)
    assert out.loc["a", "annuity_basis"] == "joint:male2+female2"
    # A code-90 legal husband of a female head prices the same couple.
    husband = _run(
        _row(
            "h",
            member_role="ofum",
            fu_head_sex="female",
            fu_head_spouse_present=True,
            fu_head_spouse_age=2,
            fu_head_spouse_sex="male",
            fu_size=2,
            wealth1=1024,
        )
    )
    assert husband.loc["h", "annuity_factor"] == pytest.approx(joint)
    assert husband.loc["h", "annuity_basis"] == "joint:female2+male2"


def test_two_percent_sensitivity_prices_higher():
    # v = 1/1.02: .8/1.02 + .4/1.02^2 = 1.168781... > A_MALE
    lower = 0.8 / 1.02 + 0.4 / 1.02**2
    out = _run(_row("a", wealth1=1000), real_interest_rate=0.02)
    assert out.loc["a", "annuity_factor"] == pytest.approx(lower)
    assert lower > A_MALE


def test_negative_wealth_buys_no_annuity():
    out = _run(_row("a", total_family_income=500, wealth1=-4000))
    assert out.loc["a", "annuity"] == 0.0
    assert out.loc["a", "baseline_income"] == 500.0
    assert out.loc["a", "poor_baseline"]


# ---------------------------------------------------------------------------
# The income concept and the strict threshold
# ---------------------------------------------------------------------------
def test_asset_income_is_replaced_by_the_annuity():
    out = _run(
        _row(
            "a",
            head_ss=1000,
            head_interest=300,
            hw_taxable=300,
            total_family_income=1300,
            wealth1=1000,
        )
    )
    annuity = 800 / A_MALE
    assert out.loc["a", "asset_income_removed"] == 300
    # B = 1300 - 300 + 693.39 = 1693.39; T = 1000 (one person 65+)
    assert out.loc["a", "baseline_income"] == pytest.approx(1000 + annuity)
    assert out.loc["a", "threshold"] == 1000.0
    # cut = .13 * 1000 = 130; R = B - 130
    assert out.loc["a", "cut"] == pytest.approx(130.0)
    assert out.loc["a", "reform_income"] == pytest.approx(870 + annuity)
    # Row U5 keeps the reported asset income: B = 1300 + 693.39
    kept = _run(
        _row(
            "a",
            head_ss=1000,
            head_interest=300,
            hw_taxable=300,
            total_family_income=1300,
            wealth1=1000,
        ),
        **_row_spec("U5"),
    )
    assert kept.loc["a", "baseline_income"] == pytest.approx(1300 + annuity)


def test_poverty_is_strictly_below_the_threshold():
    # B = 1050 - 50 = 1000 = T: not poor; R = 1000 - 130 = 870: poor.
    out = _run(
        _row(
            "a",
            head_ss=1000,
            head_interest=50,
            hw_taxable=50,
            total_family_income=1050,
        )
    )
    assert out.loc["a", "baseline_income"] == pytest.approx(1000.0)
    assert out.loc["a", "threshold"] == 1000.0
    assert not out.loc["a", "poor_baseline"]
    assert out.loc["a", "poor_reform"]


def test_other_threshold_rows():
    row = _row("a", fu_size=4, n_children=2, total_family_income=100)
    needs = _run(row, **_row_spec("U8"))
    assert needs.loc["a", "threshold"] == 1234.0
    # matrix "four", two children: 2205 - 2 * 10 = 2185
    matrix = _run(row, **_row_spec("U10"))
    assert matrix.loc["a", "threshold"] == 2185.0
    # weighted average, four persons: 2200
    assert _run(row).loc["a", "threshold"] == 2200.0


# ---------------------------------------------------------------------------
# SSI caps, exclusions and new enrollment
# ---------------------------------------------------------------------------
def test_countable_income_exclusions_by_hand():
    # unearned 1000: 1000 - 240 = 760
    assert ap.countable_income(1000, 0, MOCK_SSI) == pytest.approx(760)
    # unearned 100 leaves 140 of the $240 exclusion for earnings:
    # (2000 - 140 - 780) * .5 = 540
    assert ap.countable_income(100, 2000, MOCK_SSI) == pytest.approx(540)
    assert ap.countable_income(0, 500, MOCK_SSI) == 0


def test_ssi_offsets_are_capped_by_the_fbr_room():
    records = [
        # fall (1000-240)-(870-240) = 130, room 600-100 = 500
        _row("b", head_ss=1000, head_ssi=100, hw_transfer=100),
        # room binds: 600 - 550 = 50
        _row("c", head_ss=1000, head_ssi=550, hw_transfer=550),
        # Social Security under the $240 exclusion: no countable change
        _row("d", head_ss=200, head_ssi=400, hw_transfer=400),
        # couple: fall (2000-240)-(1740-240) = 260, room 900-600 = 300
        _row(
            "e",
            head_ss=1000,
            wife_ss=1000,
            head_ssi=300,
            wife_ssi=300,
            hw_transfer=600,
            wife_present=True,
            fu_size=2,
        ),
        # one recipient, spouse-slot SS counted: 260, room 600-300 = 300
        _row(
            "f",
            head_ss=1000,
            wife_ss=1000,
            head_ssi=300,
            hw_transfer=300,
            wife_present=True,
            fu_size=2,
        ),
        # OFUM unit: fall 130, room 600 - 100 = 500
        _row("g", ofum_ss=1000, ofum_ssi=100, fu_size=2),
    ]
    for record in records:
        record["total_family_income"] = (
            record["head_ss"]
            + record["wife_ss"]
            + record["ofum_ss"]
            + record["hw_transfer"]
            + record["ofum_ssi"]
        )
        record["ofum_transfer"] = record["ofum_ssi"]
    out = _run(*records)
    assert out["ssi_offset"].to_dict() == pytest.approx(
        {"b": 130.0, "c": 50.0, "d": 0.0, "e": 260.0, "f": 260.0, "g": 130.0}
    )
    # b: the offset refunds the whole cut, so R = B.
    assert out.loc["b", "reform_income"] == pytest.approx(
        out.loc["b", "baseline_income"]
    )
    # Row U2 (no SSI response): no offset, no enrollment.
    none = _run(*records, **_row_spec("U2"))
    assert (none["ssi_offset"] == 0).all() and (none["ssi_new"] == 0).all()
    # Row U4 (head/spouse-slot basis) drops the OFUM unit's offset.
    head_wife = _run(*records, **_row_spec("U4"))
    assert head_wife.loc["g", "ssi_offset"] == 0.0


def test_new_enrollment_in_row_u3():
    records = [
        # before 900-240 = 660 >= 600; after 783-240 = 543 < 600: 57
        _row("h", head_ss=900, total_family_income=900),
        # resources 5000 > 2000: no enrollment
        _row("i", head_ss=900, total_family_income=900, wealth1=5000),
        # vehicles leave the resource proxy: 5000 - 4000 = 1000 <= 2000
        _row(
            "j",
            head_ss=900,
            total_family_income=900,
            wealth1=5000,
            vehicles=4000,
        ),
        # still ineligible after the cut: 870 - 240 = 630 >= 600
        _row("k", head_ss=1000, total_family_income=1000),
    ]
    out = _run(*records, **_row_spec("U3"))
    assert out["ssi_new"].to_dict() == pytest.approx(
        {"h": 57.0, "i": 0.0, "j": 57.0, "k": 0.0}
    )
    # h: R = 900 - 117 + 57 (no wealth, no annuity)
    assert out.loc["h", "reform_income"] == pytest.approx(900 - 117 + 57)
    assert (_run(*records)["ssi_new"] == 0).all()


# ---------------------------------------------------------------------------
# Farm losses, retirement accounts and employer DC
# ---------------------------------------------------------------------------
def test_farm_income_and_losses():
    records = [
        _row(
            "gain",
            head_farm=400,
            hw_taxable=400,
            head_ss=1000,
            total_family_income=1400,
        ),
        _row(
            "loss",
            head_farm=-300,
            hw_taxable=-300,
            head_ss=1000,
            total_family_income=700,
        ),
    ]
    out = _run(*records)
    # share .5: remove 200 of the gain, the whole loss (adds back 300)
    assert out["farm_asset_income_removed"].to_dict() == {
        "gain": 200.0,
        "loss": -300.0,
    }
    assert out.loc["gain", "baseline_income"] == pytest.approx(1200.0)
    assert out.loc["loss", "baseline_income"] == pytest.approx(1000.0)


def test_head_annuity_and_ira_income_removed_in_a_u2_year():
    """U2 removes HEAD ANNUITIES and HEAD IRAS in every income year: in
    2014, 150 + 50 = 200 of money income 1,200 (B = 1,000).  U1's entry
    point refuses a nonzero HEAD IRAS outside income year 2012."""

    record = _row(
        "a",
        head_annuities=150,
        head_iras=50,
        hw_transfer=200,
        head_ss=1000,
        total_family_income=1200,
    )
    out = _run(record)
    assert out.loc["a", "retirement_account_income_removed"] == 200
    assert out.loc["a", "baseline_income"] == pytest.approx(1000.0)
    frame = pd.DataFrame([record])
    with pytest.raises(ap.AdjustedPovertyError, match="head_iras"):
        ap.adjusted_incomes(
            frame,
            ap.AdjustedPovertySpec(),
            data_provenance=ap.INVENTED,
            life_table=MOCK_LIFE_TABLE,
            thresholds=MOCK_THRESHOLDS,
            ssi=MOCK_SSI,
        )


def test_employer_dc_enters_financial_assets_only_in_row_u7():
    record = _row("a", wealth1=1000, employer_dc=500)
    # U0: .8 * 1000 / A_MALE; U7: .8 * (1000 + 500) / A_MALE
    assert _run(record).loc["a", "annuity"] == pytest.approx(800 / A_MALE)
    u7 = _run(record, **_row_spec("U7"))
    assert u7.loc["a", "employer_dc_added"] == 500
    assert u7.loc["a", "annuity"] == pytest.approx(1200 / A_MALE)


def test_missing_annuitant_ages_refuse():
    with pytest.raises(ap.AdjustedPovertyError, match="annuitant age"):
        _run(_row("a", fu_head_age=None))
    with pytest.raises(ap.AdjustedPovertyError, match="annuitant age"):
        _run(
            _row(
                "a",
                fu_head_spouse_present=True,
                fu_head_spouse_sex="female",
                fu_head_spouse_age=None,
            )
        )
