"""Hand-computed cases for the Track U adjusted income concept.

Every number here is INVENTED: the life table, the poverty thresholds, the
SSI parameters and the family rows are made up so that each expected value
can be worked by hand (the arithmetic is written next to each assertion).
None is a PSID value, a Census threshold, an SSA parameter or a result.
"""

from __future__ import annotations

import pandas as pd
import pytest

from populace_dynamics.estimates import adjusted_poverty as ap

# ---------------------------------------------------------------------------
# INVENTED inputs
# ---------------------------------------------------------------------------
#: INVENTED life table, ages 0-4 (not a real table).
MOCK_LIFE_TABLE = ap.LifeTable(
    name=ap.INVENTED_LIFE_TABLE,
    qx={
        "male": (0.0, 0.0, 0.2, 0.5, 1.0),
        "female": (0.0, 0.0, 0.1, 0.25, 1.0),
    },
    source={"kind": "invented"},
)
#: INVENTED interest rate with v = 0.8, so hand sums stay short.
RATE = 0.25

_WA_2010 = {
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


#: INVENTED thresholds (not Census values).
MOCK_THRESHOLDS = ap.PovertyThresholds(
    weighted_average={2010: _WA_2010},
    matrix={
        2010: {
            "one_under_65": _matrix_row(1110.0, 1),
            "one_65_plus": _matrix_row(1010.0, 1),
            "two_under_65": _matrix_row(1410.0, 2),
            "two_65_plus": _matrix_row(1310.0, 2),
            **{
                key: _matrix_row(_WA_2010[key] + 5.0, min(size - 1, 8) + 1)
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
    fbr_individual_monthly={2010: 50.0},
    fbr_couple_monthly={2010: 75.0},
    general_income_exclusion_monthly=20.0,
    earned_income_exclusion_monthly=65.0,
    earned_income_share_excluded=0.5,
    resource_limit_individual=2000.0,
    resource_limit_couple=3000.0,
    provenance={"kind": "invented"},
)


def _row(observation_id: str, **overrides) -> dict:
    row = {column: 0 for column in ap.REQUIRED_COLUMNS}
    row.update(
        observation_id=observation_id,
        family_unit_id=observation_id,
        income_year=2010,
        member_role="head",
        member_age=2,
        member_sex="male",
        member_married_coresident=False,
        spouse_age=None,
        spouse_sex=None,
        head_age=2,
        head_sex="male",
        wife_age=None,
        wife_sex=None,
        fu_legal_wife_present=False,
        wife_present=False,
        fu_size=1,
        n_children=0,
        census_needs_standard=1234,
    )
    row.update(overrides)
    return row


def _frame(*rows):
    return pd.DataFrame(list(rows))


def _run(*rows, **spec):
    base = {"real_interest_rate": RATE}
    base.update(spec)
    return ap.adjusted_incomes(
        _frame(*rows),
        ap.AdjustedPovertySpec(**base),
        data_provenance=ap.INVENTED,
        life_table=MOCK_LIFE_TABLE,
        thresholds=MOCK_THRESHOLDS,
        ssi=MOCK_SSI,
    ).set_index("observation_id")


# ---------------------------------------------------------------------------
# Annuity factors
# ---------------------------------------------------------------------------
def test_survival_curve_by_hand():
    # male from age 2: q = .2, .5, 1 -> t_p_x = 1, .8, .4, 0
    assert ap.survival_curve(MOCK_LIFE_TABLE, "male", 2).tolist() == (
        pytest.approx([1.0, 0.8, 0.4, 0.0])
    )
    with pytest.raises(ap.AdjustedPovertyError):
        ap.survival_curve(MOCK_LIFE_TABLE, "male", 5)
    with pytest.raises(ap.AdjustedPovertyError):
        ap.survival_curve(MOCK_LIFE_TABLE, "other", 2)


def test_single_life_annuity_by_hand():
    # immediate, v = .8: .8*.8 + .4*.64 = .64 + .256 = .896
    assert ap.annuity_factor_single(
        MOCK_LIFE_TABLE, "male", 2, rate=RATE
    ) == pytest.approx(0.896)
    # female from 2: t_p_x = 1, .9, .675 -> .72 + .432 = 1.152
    assert ap.annuity_factor_single(
        MOCK_LIFE_TABLE, "female", 2, rate=RATE
    ) == pytest.approx(1.152)
    # due: 1 + .64 + .256 = 1.896; zero rate: .8 + .4 = 1.2
    assert ap.annuity_factor_single(
        MOCK_LIFE_TABLE, "male", 2, rate=RATE, timing="due"
    ) == pytest.approx(1.896)
    assert ap.annuity_factor_single(
        MOCK_LIFE_TABLE, "male", 2, rate=0.0
    ) == pytest.approx(1.2)
    # a load of 10 percent raises the price by 10 percent
    assert ap.annuity_factor_single(
        MOCK_LIFE_TABLE, "male", 2, rate=RATE, load=0.1
    ) == pytest.approx(0.896 * 1.1)


def test_joint_annuity_by_hand():
    joint = ap.annuity_factor_joint(
        MOCK_LIFE_TABLE, "male", 2, "female", 2, rate=RATE
    )
    # s = .5: .5 * (.896 + 1.152) = 1.024
    assert joint == pytest.approx(1.024)
    # s = 1 (last survivor): t=1 .8+.9-.72 = .98; t=2 .4+.675-.27 = .805
    # -> .98*.8 + .805*.64 = .784 + .5152 = 1.2992
    assert ap.annuity_factor_joint(
        MOCK_LIFE_TABLE,
        "male",
        2,
        "female",
        2,
        survivor_share=1.0,
        rate=RATE,
    ) == pytest.approx(1.2992)
    # s = 0 (joint life): .72*.8 + .27*.64 = .576 + .1728 = .7488
    assert ap.annuity_factor_joint(
        MOCK_LIFE_TABLE,
        "male",
        2,
        "female",
        2,
        survivor_share=0.0,
        rate=RATE,
    ) == pytest.approx(0.7488)
    # unequal ages: male 3 (1, .5, 0) with female 2 (1, .9, .675):
    # .5*(.5*.8) + .5*(.9*.8 + .675*.64) = .2 + .576 = .776
    assert ap.annuity_factor_joint(
        MOCK_LIFE_TABLE, "male", 3, "female", 2, rate=RATE
    ) == pytest.approx(0.776)


# ---------------------------------------------------------------------------
# Thresholds and countable income
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "size, children, rule, expected, cell",
    [
        (1, 0, "census_weighted_average_65plus", 1000.0, "one_65_plus"),
        (2, 1, "census_weighted_average_65plus", 1300.0, "two_65_plus"),
        (3, 1, "census_weighted_average_65plus", 1700.0, "three"),
        (12, 0, "census_weighted_average_65plus", 4500.0, "nine_plus"),
        (1, 0, "census_matrix_65plus", 1010.0, "one_65_plus:0"),
        (2, 3, "census_matrix_65plus", 1300.0, "two_65_plus:1"),
        (4, 2, "census_matrix_65plus", 2185.0, "four:2"),
        (12, 11, "census_matrix_65plus", 4425.0, "nine_plus:8"),
    ],
)
def test_threshold_lookup(size, children, rule, expected, cell):
    assert ap.threshold_for(MOCK_THRESHOLDS, 2010, size, children, rule) == (
        pytest.approx(expected),
        cell,
    )


def test_threshold_rules_refuse_missing_inputs():
    assert ap.threshold_for(
        None, 2010, 3, 0, "psid_census_needs_standard", needs_standard=777
    ) == (777.0, "psid_census_needs_standard")
    with pytest.raises(ap.ThresholdsNotCapturedError):
        ap.threshold_for(None, 2010, 1, 0, "census_weighted_average_65plus")
    with pytest.raises(ap.AdjustedPovertyError):
        ap.threshold_for(
            MOCK_THRESHOLDS, 2011, 1, 0, "census_weighted_average_65plus"
        )


def test_census_thresholds_are_not_captured():
    with pytest.raises(ap.ThresholdsNotCapturedError, match="thresh04"):
        ap.load_poverty_thresholds()


def test_countable_income_by_hand():
    # unearned 1000: 1000 - 240 = 760
    assert ap.countable_income(1000, 0, MOCK_SSI) == pytest.approx(760)
    # unearned 100 leaves 140 of the $240 exclusion for earnings:
    # (2000 - 140 - 780) * .5 = 540
    assert ap.countable_income(100, 2000, MOCK_SSI) == pytest.approx(540)
    assert ap.countable_income(0, 500, MOCK_SSI) == 0


# ---------------------------------------------------------------------------
# The income concept
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
    row = out.loc["a"]
    annuity = 0.8 * 1000 / 0.896
    assert row["annuity"] == pytest.approx(annuity)
    assert row["asset_income_removed"] == 300
    # B = 1300 - 300 + 892.857...
    assert row["baseline_income"] == pytest.approx(1000 + annuity)
    assert row["threshold"] == 1000.0
    assert row["cut"] == pytest.approx(130.0)
    assert row["reform_income"] == pytest.approx(870 + annuity)
    assert not row["poor_baseline"] and not row["poor_reform"]
    assert row["annuity_basis"] == "single:male2"


def test_keep_rule_adds_the_annuity_to_reported_asset_income():
    out = _run(
        _row(
            "a",
            head_interest=300,
            hw_taxable=300,
            total_family_income=300,
            wealth1=1000,
        ),
        asset_income_rule="keep",
    )
    assert out.loc["a", "baseline_income"] == pytest.approx(
        300 + 0.8 * 1000 / 0.896
    )


def test_threshold_boundary_and_entry_into_poverty():
    # B = 1050 - 50 = 1000 = T (not poor); R = 1000 - 130 = 870 (poor).
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
    assert not out.loc["a", "poor_baseline"]
    assert out.loc["a", "poor_reform"]


def test_negative_wealth_buys_no_annuity():
    out = _run(_row("a", total_family_income=500, wealth1=-4000))
    assert out.loc["a", "annuity"] == 0.0
    assert out.loc["a", "baseline_income"] == 500.0
    assert out.loc["a", "poor_baseline"]


def test_joint_annuity_for_a_married_coresident_member():
    out = _run(
        _row(
            "a",
            member_married_coresident=True,
            spouse_age=2,
            spouse_sex="female",
            wealth1=1024,
            fu_size=2,
            wife_present=True,
        )
    )
    # 0.8 * 1024 / 1.024 = 800
    assert out.loc["a", "annuity"] == pytest.approx(800.0)
    assert out.loc["a", "annuity_basis"] == "joint:male2+female2"
    assert out.loc["a", "threshold"] == 1300.0


def test_fu_head_rule_prices_on_the_head_and_legal_wife():
    rows = [
        _row(
            "ofum",
            member_role="ofum",
            member_age=3,
            member_sex="female",
            head_age=2,
            head_sex="male",
            wife_age=2,
            wife_sex="female",
            fu_legal_wife_present=True,
            wife_present=True,
            fu_size=3,
            wealth1=1024,
        )
    ]
    member = _run(*rows)
    head = _run(*rows, annuity_lives="fu_head_rule")
    # member rule: single life on the female OFUM aged 3 ->
    # t_p_x = 1, .75, 0 -> .75*.8 = .6
    assert member.loc["ofum", "annuity_factor"] == pytest.approx(0.6)
    assert head.loc["ofum", "annuity_factor"] == pytest.approx(1.024)


def test_ssi_offset_for_existing_recipients():
    rows = [
        # full offset: fall (1000-240)-(870-240) = 130, cap 600-100 = 500
        _row("b", head_ss=1000, head_ssi=100, hw_transfer=100),
        # cap binds: 600 - 550 = 50
        _row("c", head_ss=1000, head_ssi=550, hw_transfer=550),
        # Social Security under the $240 exclusion: no countable change
        _row("d", head_ss=200, head_ssi=400, hw_transfer=400),
        # couple: fall (2000-240)-(1740-240) = 260, cap 900 - 600 = 300
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
        # one recipient, spouse's SS counted: 260, cap 600 - 300 = 300
        _row(
            "f",
            head_ss=1000,
            wife_ss=1000,
            head_ssi=300,
            hw_transfer=300,
            wife_present=True,
            fu_size=2,
        ),
        # OFUM unit: fall 130, cap 600 - 100 = 500
        _row("g", ofum_ss=1000, ofum_ssi=100, fu_size=2),
    ]
    for row in rows:
        row["total_family_income"] = (
            row["head_ss"]
            + row["wife_ss"]
            + row["ofum_ss"]
            + row["hw_transfer"]
            + row["ofum_ssi"]
        )
        row["ofum_transfer"] = row["ofum_ssi"]
    out = _run(*rows)
    assert out["ssi_offset"].to_dict() == pytest.approx(
        {"b": 130.0, "c": 50.0, "d": 0.0, "e": 260.0, "f": 260.0, "g": 130.0}
    )
    assert out.loc["b", "reform_income"] == pytest.approx(
        out.loc["b", "baseline_income"]
    )
    only = _run(*rows, ssi_deeming="recipients_only")
    # only the head's 1000 counts: 130
    assert only.loc["f", "ssi_offset"] == pytest.approx(130.0)
    none = _run(*rows, ssi_rule="none")
    assert (none["ssi_offset"] == 0).all()
    assert (none["ssi_new"] == 0).all()


def test_cut_start_year_leaves_earlier_age67_years_uncut():
    """Row U6: with a 2004 start, the 1936 birth year (67 in 2003) is uncut.

    INVENTED rows, threshold T = 1,000 (one person, 65+ row):

    * "1936": B = 1,050 (not poor). Primary: cut 0.13 * 1,050 = 136.5,
      R = 913.5 (poor). U6: 1936 + 67 = 2003 < 2004, no cut, R = 1,050.
    * "1937": 1937 + 67 = 2004 >= 2004, cut under both: R = 913.5.
    * "ssi": birth year 1936, SSI recipient with SS 1,000, SSI 100:
      primary offset (1,000 - 240) - (870 - 240) = 130 (cap 500); U6 has
      no cut, so no fall in countable income and no offset.
    """

    rows = [
        _row("1936", birth_year=1936, head_ss=1050, total_family_income=1050),
        _row("1937", birth_year=1937, head_ss=1050, total_family_income=1050),
        _row(
            "ssi",
            birth_year=1936,
            head_ss=1000,
            head_ssi=100,
            hw_transfer=100,
            total_family_income=1100,
        ),
    ]
    primary = _run(*rows)
    assert primary["cut_applies"].all()
    assert primary.loc["1936", "cut"] == pytest.approx(136.5)
    assert primary.loc["1936", "reform_income"] == pytest.approx(913.5)
    assert primary.loc["1936", "poor_reform"]
    assert primary.loc["ssi", "ssi_offset"] == pytest.approx(130.0)
    u6 = _run(*rows, cut_start_year=2004)
    assert u6["cut_applies"].to_dict() == {
        "1936": False,
        "1937": True,
        "ssi": False,
    }
    assert u6.loc["1936", "cut"] == 0.0
    assert u6.loc["1936", "reform_income"] == pytest.approx(1050.0)
    assert not u6.loc["1936", "poor_reform"]
    assert u6.loc["1937", "reform_income"] == pytest.approx(913.5)
    assert u6.loc["1937", "poor_reform"]
    assert u6.loc["ssi", "ssi_offset"] == 0.0
    assert u6.loc["ssi", "reform_income"] == pytest.approx(
        u6.loc["ssi", "baseline_income"]
    )
    # full static recomputation: an uncut unit cannot become newly eligible
    u3 = _run(*rows, cut_start_year=2004, ssi_rule="full_static_recomputation")
    assert (u3.loc[["1936", "ssi"], "ssi_new"] == 0).all()


@pytest.mark.parametrize("value", [True, "2004", 1989, 2031, 2004.0])
def test_cut_start_year_must_be_a_year_or_none(value):
    with pytest.raises(ap.AdjustedPovertyError, match="cut_start_year"):
        ap.AdjustedPovertySpec(cut_start_year=value)


def test_full_static_recomputation_enrols_newly_eligible_units():
    rows = [
        # before 900-240 = 660 >= 600; after 783-240 = 543 < 600: SSI 57
        _row("h", head_ss=900, total_family_income=900),
        # resources 5000 > 2000: no enrolment
        _row("i", head_ss=900, total_family_income=900, wealth1=5000),
        # vehicles are excluded from the resource proxy
        _row(
            "j",
            head_ss=900,
            total_family_income=900,
            wealth1=5000,
            vehicles=4000,
        ),
        # still ineligible after the cut: 1000 -> 870-240 = 630
        _row("k", head_ss=1000, total_family_income=1000),
    ]
    out = _run(*rows, ssi_rule="full_static_recomputation")
    assert out["ssi_new"].to_dict() == pytest.approx(
        {"h": 57.0, "i": 0.0, "j": 57.0 - 0.0, "k": 0.0}
    )
    # j: annuity of .8 * 5000 / .896 does not enter the SSI income test
    assert out.loc["h", "reform_income"] == pytest.approx(900 - 117 + 57)
    offset_only = _run(*rows)
    assert (offset_only["ssi_new"] == 0).all()


def test_head_wife_basis_drops_other_members():
    row = _row(
        "a",
        head_ss=1000,
        ofum_ss=1000,
        ofum_taxable=5000,
        ofum_labor=5000,
        total_family_income=7000,
        fu_size=3,
        n_children=0,
        ofum_ssi=100,
        ofum_transfer=0,
    )
    fu = _run(row)
    hw = _run(row, income_unit="head_wife")
    assert fu.loc["a", "money_income"] == 7000
    assert fu.loc["a", "social_security"] == 2000
    assert fu.loc["a", "unit_size"] == 3
    assert hw.loc["a", "money_income"] == 1000
    assert hw.loc["a", "social_security"] == 1000
    assert hw.loc["a", "unit_size"] == 1
    assert hw.loc["a", "income_basis"] == "head_wife"
    assert hw.loc["a", "ssi_offset"] == 0.0
    ofum = _run(dict(row, member_role="ofum"), income_unit="head_wife")
    assert ofum.loc["a", "income_basis"] == "family_unit"


def test_needs_standard_and_matrix_rules():
    row = _row("a", fu_size=4, n_children=2, total_family_income=100)
    needs = _run(row, threshold_rule="psid_census_needs_standard")
    assert needs.loc["a", "threshold"] == 1234.0
    matrix = _run(row, threshold_rule="census_matrix_65plus")
    assert matrix.loc["a", "threshold"] == 2185.0


def test_provenance_guards():
    frame = _frame(_row("a", total_family_income=100))
    frame.attrs["provenance_kind"] = "psid_files"
    with pytest.raises(ap.AdjustedPovertyError, match="registration"):
        ap.adjusted_incomes(
            frame,
            ap.AdjustedPovertySpec(real_interest_rate=RATE),
            data_provenance=ap.INVENTED,
            life_table=MOCK_LIFE_TABLE,
            thresholds=MOCK_THRESHOLDS,
            ssi=MOCK_SSI,
        )
    with pytest.raises(ap.AdjustedPovertyError, match="pointer"):
        ap.adjusted_incomes(
            frame,
            data_provenance=ap.REGISTERED_REAL,
            life_table=MOCK_LIFE_TABLE,
            thresholds=MOCK_THRESHOLDS,
            ssi=MOCK_SSI,
        )
    with pytest.raises(ap.AdjustedPovertyError, match="invented life"):
        ap.adjusted_incomes(
            frame,
            data_provenance=ap.REGISTERED_REAL,
            registration_pointer="#42 comment (invented pointer)",
            life_table=MOCK_LIFE_TABLE,
            thresholds=MOCK_THRESHOLDS,
            ssi=MOCK_SSI,
        )


@pytest.mark.parametrize("kind", [None, "caller_frames", "invented"])
def test_registered_real_needs_rows_built_from_psid_files(kind):
    """registered_real must agree with the rows' recorded provenance.

    Track A's opening refuses a registered_real run on a cohort that was
    not built from recorded PSID files; the income concept must too, or
    invented or caller-built rows could leave with a real-data label.
    """

    frame = _frame(_row("a", total_family_income=100))
    if kind is not None:
        frame.attrs["provenance_kind"] = kind
    with pytest.raises(ap.AdjustedPovertyError, match="contradicts"):
        ap.adjusted_incomes(
            frame,
            data_provenance=ap.REGISTERED_REAL,
            registration_pointer="#42 comment (invented pointer)",
            life_table=MOCK_LIFE_TABLE,
            thresholds=MOCK_THRESHOLDS,
            ssi=MOCK_SSI,
        )


def test_spec_validation_and_pending_decisions():
    with pytest.raises(ap.AdjustedPovertyError):
        ap.AdjustedPovertySpec(ssi_rule="something")
    with pytest.raises(ap.AdjustedPovertyError):
        ap.AdjustedPovertySpec(cut_rate=1.5)
    spec = ap.AdjustedPovertySpec()
    assert spec.cut_rate == 0.13
    assert spec.annuitized_share == 0.8
    assert spec.real_interest_rate == 0.03
    assert spec.ssi_rule == "offset_existing_recipients"
    decisions = {item.field: item for item in ap.pending_decisions()}
    assert decisions["ssi_rule"].awaiting.startswith("Max")
    assert "d189" in decisions["ssi_rule"].awaiting
    for name, item in decisions.items():
        assert getattr(spec, name) == item.default


def test_rows_are_validated():
    with pytest.raises(ap.AdjustedPovertyError, match="lack columns"):
        ap.adjusted_incomes(
            _frame({"observation_id": "a"}),
            data_provenance=ap.INVENTED,
            life_table=MOCK_LIFE_TABLE,
            thresholds=MOCK_THRESHOLDS,
            ssi=MOCK_SSI,
        )
    with pytest.raises(ap.AdjustedPovertyError, match="duplicate"):
        _run(_row("a"), _row("a"))
    with pytest.raises(ap.AdjustedPovertyError, match="member_role"):
        _run(_row("a", member_role="lodger"))
