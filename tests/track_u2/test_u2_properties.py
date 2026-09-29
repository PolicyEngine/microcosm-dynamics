"""Property-based tests of the section 13 invariants (Hypothesis).

For every observation in every registered row -- including rows U1, U3
and U4 -- and in each half of each split:

    R_i <= B_i        and        1(R_i < T_i) >= 1(B_i < T_i);

for valid nonnegative Social Security and 0 <= c <= 1:

    0 <= offset <= fall <= c S,  fall = 0 when S <= G,
    offset <= the FBR room;

for a newly eligible unit:  0 <= SSI_new <= min(F - C', C - C');

and the zero-cut identity, rates within [0, 100], invariance to a
positive common weight scaling, and rejection of malformed plans and
missing parameters.  These are calculation properties, not statements
about any Report cell.  Rows are INVENTED by the strategies below.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.data import family_income
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import (
    cohort,
    estimator,
    invented,
    parameters,
    rows,
    sources,
    tabulation,
)

SETTINGS = settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
YEARS = sorted(estimator.HEAD_IRA_INCOME_YEARS)
#: Rates lie in [0, 100] up to floating-point rounding: the inherited
#: tabulation computes ``100.0 * fsum(poor weights) / total``, and the
#: minimized counterexample below (one poor observation) evaluates to
#: 100.00000000000001.  U2 keeps U1's arithmetic byte for byte, so the
#: bound is asserted to within this tolerance, not changed.
BOUND_ULP = 1e-9
_AMOUNT = st.integers(min_value=0, max_value=60_000)


@pytest.fixture(scope="module")
def params():
    return parameters.committed_u2_parameters(
        invented.invented_poverty_thresholds()
    )


@st.composite
def observation(draw, index: int = 0) -> dict:
    year = draw(st.sampled_from(YEARS))
    age = draw(st.sampled_from([66, 67, 68]))
    size = draw(st.integers(min_value=1, max_value=10))
    wife = draw(st.booleans()) and size >= 2
    joint = draw(st.booleans())
    row = {
        "observation_id": f"{index}:{year + 1}",
        "family_unit_id": (year + 1) * 100_000 + index,
        "income_year": year,
        "birth_year": year - age,
        "member_role": draw(st.sampled_from(["head", "wife", "ofum"])),
        "member_age": age,
        "member_sex": draw(st.sampled_from(["male", "female"])),
        "member_married_coresident": joint,
        "spouse_age": draw(st.integers(55, 90)) if joint else pd.NA,
        "spouse_sex": (
            draw(st.sampled_from(["male", "female"])) if joint else pd.NA
        ),
        "fu_head_age": draw(st.integers(40, 95)),
        "fu_head_sex": draw(st.sampled_from(["male", "female"])),
        "fu_head_spouse_present": joint,
        "fu_head_spouse_age": draw(st.integers(40, 95)) if joint else pd.NA,
        "fu_head_spouse_sex": (
            draw(st.sampled_from(["male", "female"])) if joint else pd.NA
        ),
        "wife_present": wife,
        "fu_size": size,
        "n_children": draw(st.integers(0, max(0, min(size - 1, 8)))),
        "census_needs_standard": draw(st.integers(8_000, 60_000)),
        "wealth1": draw(st.integers(-50_000, 900_000)),
        "vehicles": draw(st.integers(0, 40_000)),
        "head_iras": draw(_AMOUNT),
        "employer_dc": draw(st.sampled_from([0, 0, 5_000, 120_000])),
        "head_annuities": draw(_AMOUNT),
    }
    for concept in (
        *family_income.ASSET_INCOME_CONCEPTS,
        *family_income.HW_EARNED_CONCEPTS,
    ):
        low = -20_000 if concept in family_income.MAY_BE_NEGATIVE else 0
        row[concept] = draw(st.integers(low, 40_000))
    for concept in family_income.SOCIAL_SECURITY_CONCEPTS:
        row[concept] = draw(st.integers(0, 40_000))
    for concept in family_income.SSI_CONCEPTS:
        row[concept] = draw(st.sampled_from([0, 0, 500, 3_000, 9_000, 12_000]))
    for concept in (
        "head_tanf",
        "wife_tanf",
        "head_other_welfare",
        "wife_other_welfare",
    ):
        row[concept] = draw(st.sampled_from([0, 0, 1_000]))
    row["hw_taxable"] = sum(
        row[c]
        for c in (
            *family_income.HW_EARNED_CONCEPTS,
            *family_income.ASSET_INCOME_CONCEPTS,
        )
        if c != "ofum_asset"
    )
    row["hw_transfer"] = (
        row["head_ssi"]
        + row["wife_ssi"]
        + row["head_tanf"]
        + row["wife_tanf"]
        + row["head_other_welfare"]
        + row["wife_other_welfare"]
        + row["head_annuities"]
        + row["head_iras"]
        + draw(st.integers(0, 10_000))
    )
    row["total_family_income"] = (
        row["hw_taxable"]
        + row["hw_transfer"]
        + row["ofum_asset"]
        + row["ofum_ssi"]
        + row["head_ss"]
        + row["wife_ss"]
        + row["ofum_ss"]
        + draw(st.integers(0, 5_000))
    )
    return row


@st.composite
def frames(draw) -> pd.DataFrame:
    n = draw(st.integers(1, 8))
    data = [draw(observation(i)) for i in range(n)]
    frame = pd.DataFrame(data)
    for column in ("spouse_age", "fu_head_spouse_age"):
        frame[column] = frame[column].astype("Int64")
    frame.attrs.update(
        provenance_kind="invented",
        target_id="U2",
        role_context=sources.INVENTED_DECLARED,
    )
    return frame


def _estimate(frame, spec, params):
    return estimator.u2_adjusted_incomes(
        frame,
        spec,
        context=estimator.U2EstimatorContext(sources.INVENTED_DECLARED),
        data_provenance=ap.INVENTED,
        life_table=params.life_tables[spec.mortality_basis],
        thresholds=params.thresholds,
        ssi=params.ssi,
    )


@SETTINGS
@given(frame=frames())
def test_reform_never_exceeds_baseline_in_any_row(frame, params):
    for row_id, row in rows.REGISTERED_ROWS.items():
        out = _estimate(frame, row.income_spec(), params)
        assert (
            out["reform_income"] <= out["baseline_income"] + 1e-6
        ).all(), row_id
        assert (out["poor_reform"] | ~out["poor_baseline"]).all(), row_id
        assert (out["ssi_offset"] >= 0).all() and (out["ssi_new"] >= 0).all()
        assert (out["ssi_offset"] + out["ssi_new"] <= out["cut"] + 1e-6).all()


@SETTINGS
@given(frame=frames())
def test_zero_cut_identity(frame, params):
    for row in rows.REGISTERED_ROWS.values():
        spec = estimator.U2IncomeSpec(**{**row.income, "cut_rate": 0.0})
        out = _estimate(frame, spec, params)
        assert np.array_equal(out["reform_income"], out["baseline_income"])
        assert (out["poor_reform"] == out["poor_baseline"]).all()


@SETTINGS
@given(
    ss=st.floats(0, 100_000, allow_nan=False),
    cut=st.floats(0, 1, allow_nan=False),
    ssi=st.floats(0, 20_000, allow_nan=False),
    year=st.sampled_from(YEARS),
    couple=st.booleans(),
)
def test_offset_bounds(ss, cut, ssi, year, couple, params):
    general = 12 * params.ssi.general_income_exclusion_monthly
    fall = ap._countable_ss_fall(ss, cut, general)
    assert -1e-9 <= fall <= cut * ss + 1e-9
    if ss <= general:
        assert fall == 0
    room = max(0.0, params.ssi.fbr_annual(year, couple) - ssi)
    offset = min(fall, room)
    assert 0 <= offset <= fall + 1e-9 and offset <= room + 1e-9


@SETTINGS
@given(
    unearned=st.floats(0, 30_000, allow_nan=False),
    earned=st.floats(0, 60_000, allow_nan=False),
    ss=st.floats(0, 60_000, allow_nan=False),
    cut=st.floats(0, 1, allow_nan=False),
    year=st.sampled_from(YEARS),
    couple=st.booleans(),
)
def test_new_enrollment_bounds(
    unearned, earned, ss, cut, year, couple, params
):
    ssi = params.ssi
    fbr = ssi.fbr_annual(year, couple)
    before = ap.countable_income(unearned + ss, earned, ssi)
    after = ap.countable_income(unearned + (1 - cut) * ss, earned, ssi)
    assert after <= before + 1e-9
    assert before - after <= cut * ss + 1e-9
    if before >= fbr and after < fbr:
        new = fbr - after
        assert 0 <= new <= min(fbr - after, before - after) + 1e-9


@st.composite
def tabulation_rows(draw) -> pd.DataFrame:
    n = draw(st.integers(4, 40))
    base = draw(st.lists(st.booleans(), min_size=n, max_size=n))
    extra = draw(st.lists(st.booleans(), min_size=n, max_size=n))
    frame = pd.DataFrame(
        {
            "observation_id": [f"{i}:2019" for i in range(n)],
            "person_id": [
                draw(st.integers(0, n // 2 + 1)) * 10 + i % 2 for i in range(n)
            ],
            "family_unit_id": [
                201_900_000 + draw(st.integers(0, n)) for _ in range(n)
            ],
            "weight": draw(
                st.lists(st.floats(0.5, 50.0), min_size=n, max_size=n)
            ),
            "sex": draw(
                st.lists(
                    st.sampled_from(["male", "female"]), min_size=n, max_size=n
                )
            ),
            "marital_status_4": draw(
                st.lists(
                    st.sampled_from(
                        [
                            "married",
                            "widowed",
                            "divorced",
                            "never_married",
                            "unclassified",
                        ]
                    ),
                    min_size=n,
                    max_size=n,
                )
            ),
            "birth_year": draw(
                st.lists(st.sampled_from([1949, 1951]), min_size=n, max_size=n)
            ),
            "stratum": draw(
                st.lists(st.sampled_from([1, 2, 90]), min_size=n, max_size=n)
            ),
            "cluster": draw(
                st.lists(st.sampled_from([1, 2]), min_size=n, max_size=n)
            ),
            "poor_baseline": base,
            "poor_reform": [a or b for a, b in zip(base, extra, strict=True)],
        }
    )
    frame = frame.drop_duplicates("observation_id")
    frame.attrs.update(target_id="U2", provenance_kind="invented")
    return frame


@SETTINGS
@given(frame=tabulation_rows(), scale=st.floats(0.01, 1_000.0))
def test_cells_and_halves_monotone_bounded_and_scale_invariant(frame, scale):
    design = frame[["stratum", "cluster"]].drop_duplicates()
    table = tabulation.tabulate_u2(
        frame, data_provenance=ap.INVENTED, design=design
    )
    for cell in table["cells"]:
        if not cell["defined"]:
            continue
        for key in ("baseline_rate", "reform_rate"):
            assert -BOUND_ULP <= cell[key] <= 100.0 + BOUND_ULP
        assert cell["delta"] >= -1e-9
    for seed in table["floor_per_seed"]:
        for side in (seed["side_a"], seed["side_b"]):
            for entry in side.values():
                if entry["defined"]:
                    assert entry["delta"] >= -1e-9
                    assert (
                        -BOUND_ULP
                        <= entry["baseline_rate"]
                        <= 100.0 + BOUND_ULP
                    )
    scaled = frame.assign(weight=frame["weight"] * scale)
    scaled.attrs.update(frame.attrs)
    other = tabulation.tabulate_u2(
        scaled, data_provenance=ap.INVENTED, design=design
    )
    for a, b in zip(table["cells"], other["cells"], strict=True):
        assert a["defined"] == b["defined"]
        if a["defined"]:
            for key in ("baseline_rate", "reform_rate", "delta"):
                assert math.isclose(a[key], b[key], rel_tol=1e-9, abs_tol=1e-9)


@SETTINGS
@given(
    row=st.sampled_from(["U0", "U1", "U0-F", "U3", "", "u0"]),
    rule=st.sampled_from(
        [cohort.SEED_WAVE_RULE, "earliest_presence_wave", "any"]
    ),
)
def test_malformed_plans_are_rejected(row, rule):
    if row in ("U0", "U1") and rule == cohort.SEED_WAVE_RULE:
        spec = cohort.U2CohortSpec(row=row, seed_wave_rule=rule)
        cells = cohort.plan_cells(spec)
        assert all(w in cohort.SUPPORT_WAVES for _, w, _, _, _ in cells)
        return
    with pytest.raises(ValueError):
        cohort.U2CohortSpec(row=row, seed_wave_rule=rule)


@SETTINGS
@given(year=st.integers(1990, 2030), size=st.integers(1, 12))
def test_missing_threshold_years_are_rejected(year, size, params):
    thresholds = params.thresholds
    if year in thresholds.weighted_average:
        value, _ = ap.threshold_for(
            thresholds, year, size, 0, "census_weighted_average_65plus"
        )
        assert value > 0
    else:
        with pytest.raises(ap.AdjustedPovertyError):
            ap.threshold_for(
                thresholds, year, size, 0, "census_weighted_average_65plus"
            )


def test_per_observation_monotone_in_the_invented_run_and_every_half(u2_run):
    for row_id, entry in u2_run["rows"].items():
        table = entry["tabulation"]
        for cell in table["cells"]:
            if cell["defined"]:
                assert cell["delta"] >= -1e-12, (row_id, cell["cell"])
        for seed in table["floor_per_seed"]:
            for side in (seed["side_a"], seed["side_b"]):
                for name, stats in side.items():
                    if stats["defined"]:
                        assert stats["delta"] >= -1e-12, (row_id, name)


def test_rate_bound_counterexample_is_a_one_ulp_rounding():
    """The minimized Hypothesis counterexample to the [0, 100] bound.

    One observation, poor at baseline, weight 43.30748055732103: U1's
    ``100.0 * fsum(w) / sum(w)`` gives 100.00000000000001 (one ulp above
    100), an arithmetic-order artifact of the inherited expression, not a
    modeling error.  Recorded here so the tolerance above is explained.
    """

    frame = pd.DataFrame(
        {
            "observation_id": ["0:2019"],
            "person_id": [1],
            "family_unit_id": [201_900_001],
            "weight": [43.30748055732103],
            "sex": ["female"],
            "marital_status_4": ["widowed"],
            "birth_year": [1951],
            "stratum": [1],
            "cluster": [1],
            "poor_baseline": [True],
            "poor_reform": [True],
        }
    )
    frame.attrs.update(target_id="U2", provenance_kind="invented")
    table = tabulation.tabulate_u2(
        frame,
        data_provenance=ap.INVENTED,
        design=frame[["stratum", "cluster"]],
    )
    rate = next(c for c in table["cells"] if c["cell"] == "all")[
        "baseline_rate"
    ]
    assert rate == 100.00000000000001
    assert rate - 100.0 < BOUND_ULP


# ---------------------------------------------------------------------------
# A literal section 7-8 reference for the cut and the SSI response
# (differential), and the one-field structure of the rows
# ---------------------------------------------------------------------------
def _reference_countable(unearned: float, earned: float, ssi) -> float:
    """Section 8's countable income, written from the text alone: the
    general exclusion applies to unearned income first and any remainder
    to earnings, then the earned exclusion and the earned-share
    exclusion (twelve times the monthly amounts)."""

    general = 12 * ssi.general_income_exclusion_monthly
    flat = 12 * ssi.earned_income_exclusion_monthly
    unearned, earned = max(0.0, unearned), max(0.0, earned)
    remainder = max(0.0, general - unearned)
    earned_left = max(0.0, earned - remainder - flat)
    return max(0.0, unearned - general) + earned_left * (
        1 - ssi.earned_income_share_excluded
    )


def _reference_fall(s: float, c: float, g: float) -> float:
    """Section 8: fall = max(0, S - G) - max(0, (1 - c) S - G)."""

    return max(0.0, s - g) - max(0.0, (1 - c) * s - g)


def _fbr(ssi, year: int, couple: bool) -> float:
    monthly = ssi.fbr_couple_monthly if couple else ssi.fbr_individual_monthly
    return 12 * float(monthly[year])


def _reference(row: dict, spec: estimator.U2IncomeSpec, ssi) -> dict:
    """The cut, offset and new enrollment of one observation from the
    literal formulas of sections 7 and 8, with the section 13 bounds of
    every unit checked on the way."""

    c = spec.cut_rate if row["birth_year"] + 67 >= spec.cut_start_year else 0.0
    family = spec.income_unit == "family_unit" or row["member_role"] == "ofum"
    hw_ss = float(row["head_ss"] + row["wife_ss"])
    unit_ss = hw_ss + (float(row["ofum_ss"]) if family else 0.0)
    out = {"cut": c * unit_ss, "offset": 0.0, "new": 0.0}
    if spec.ssi_rule == "none":
        return out
    g = 12 * ssi.general_income_exclusion_monthly
    year = int(row["income_year"])
    hw_ssi = float(row["head_ssi"] + row["wife_ssi"])
    if hw_ssi > 0:
        couple = row["head_ssi"] > 0 and row["wife_ssi"] > 0
        fall = _reference_fall(hw_ss, c, g)
        room = max(0.0, _fbr(ssi, year, couple) - hw_ssi)
        offset = min(fall, room)
        assert -1e-9 <= offset <= fall + 1e-9 <= c * hw_ss + 2e-9
        assert fall == 0 or hw_ss > g
        assert offset <= room
        out["offset"] += offset
    elif spec.ssi_rule == "full_static_recomputation":
        couple = bool(row["wife_present"])
        f = _fbr(ssi, year, couple)
        unearned = max(
            0.0,
            row["hw_transfer"]
            - hw_ssi
            - row["head_tanf"]
            - row["wife_tanf"]
            - row["head_other_welfare"]
            - row["wife_other_welfare"],
        )
        earned = sum(
            max(0.0, float(row[concept]))
            for concept in family_income.HW_EARNED_CONCEPTS
        )
        before = _reference_countable(unearned + hw_ss, earned, ssi)
        after = _reference_countable(unearned + (1 - c) * hw_ss, earned, ssi)
        limit = (
            ssi.resource_limit_couple
            if couple
            else ssi.resource_limit_individual
        )
        resources = max(0.0, float(row["wealth1"]) - float(row["vehicles"]))
        if before >= f and after < f and resources <= limit:
            new = f - after
            assert 0 <= new <= min(f - after, before - after) + 1e-9
            out["new"] = new
    if family and row["ofum_ssi"] > 0:
        fall = _reference_fall(float(row["ofum_ss"]), c, g)
        room = max(0.0, _fbr(ssi, year, False) - float(row["ofum_ssi"]))
        offset = min(fall, room)
        assert -1e-9 <= offset <= fall + 1e-9 <= c * row["ofum_ss"] + 2e-9
        out["offset"] += offset
    return out


@SETTINGS
@given(frame=frames())
def test_cut_and_ssi_response_equal_the_section_8_reference(frame, params):
    """Differential: the estimator's cut, offset and new enrollment equal
    the literal section 7-8 formulas for every row and observation."""

    for row_id, row in rows.REGISTERED_ROWS.items():
        spec = row.income_spec()
        out = _estimate(frame, spec, params)
        for record, (_, estimate) in zip(
            frame.to_dict("records"), out.iterrows(), strict=True
        ):
            expected = _reference(record, spec, params.ssi)
            for key, column in (
                ("cut", "cut"),
                ("offset", "ssi_offset"),
                ("new", "ssi_new"),
            ):
                assert math.isclose(
                    estimate[column], expected[key], rel_tol=0, abs_tol=1e-6
                ), (row_id, key, estimate[column], expected[key])


#: What each one-field row may change relative to U0 (section 11): every
#: other output column must equal U0's exactly.
_ROW_FIELDS: dict[str, frozenset[str]] = {
    "U2": frozenset({"ssi_offset", "ssi_new", "reform_income", "poor_reform"}),
    "U3": frozenset({"ssi_new", "reform_income", "poor_reform"}),
    "U5": frozenset(
        {
            "asset_income_removed",
            "retirement_account_income_removed",
            "farm_asset_income_removed",
            "baseline_income",
            "reform_income",
            "poor_baseline",
            "poor_reform",
        }
    ),
    "U7": frozenset(
        {
            "employer_dc_added",
            "financial_assets",
            "annuity",
            "baseline_income",
            "reform_income",
            "poor_baseline",
            "poor_reform",
        }
    ),
    "U8": frozenset(
        {"threshold", "threshold_cell", "poor_baseline", "poor_reform"}
    ),
    "U9": frozenset(
        {
            "annuity_factor",
            "annuity",
            "baseline_income",
            "reform_income",
            "poor_baseline",
            "poor_reform",
        }
    ),
    "U10": frozenset(
        {"threshold", "threshold_cell", "poor_baseline", "poor_reform"}
    ),
}


@SETTINGS
@given(frame=frames())
def test_one_field_rows_change_only_their_field(frame, params):
    """Each of rows U2-U10 (U4 aside) differs from U0 only in the columns
    its one changed field reaches; U4 changes nothing for an OFUM member.
    Row U1 changes the population, not the income concept."""

    base = _estimate(frame, estimator.U2IncomeSpec(), params)
    for row_id, fields in _ROW_FIELDS.items():
        out = _estimate(
            frame, rows.REGISTERED_ROWS[row_id].income_spec(), params
        )
        for column in base.columns:
            if column in fields:
                continue
            assert base[column].equals(out[column]), (row_id, column)
    head_wife = _estimate(
        frame, rows.REGISTERED_ROWS["U4"].income_spec(), params
    )
    ofum = frame["member_role"].eq("ofum").to_numpy()
    for column in base.columns:
        assert base.loc[ofum, column].equals(
            head_wife.loc[ofum, column]
        ), column
    assert (head_wife.loc[~ofum, "income_basis"] == "head_wife").all()
    assert rows.REGISTERED_ROWS["U1"].income == {}


@SETTINGS
@given(frame=frames())
def test_annuity_price_falls_with_the_interest_rate(frame, params):
    """Intended monotonicity: the two-percent sensitivity prices every
    annuity at least as high as three percent, so no annuity rises."""

    primary = _estimate(frame, estimator.U2IncomeSpec(), params)
    lower = _estimate(
        frame, estimator.U2IncomeSpec(real_interest_rate=0.02), params
    )
    assert (lower["annuity_factor"] > primary["annuity_factor"]).all()
    assert (lower["annuity"] <= primary["annuity"] + 1e-9).all()


def test_per_observation_monotone_in_every_half_of_every_split(
    u2_inputs, u2_params, declared, u2_births
):
    """Section 13: R <= B and poverty never lost for every observation of
    every row inside each side of each floor split (the inherited split
    of family units linked by persons, seeds 0-4)."""

    from populace_dynamics.estimates import uniform_cut_tabulation as ut
    from populace_dynamics.harness.panel import split_panel_by_person

    for row_id, row in rows.REGISTERED_ROWS.items():
        built = cohort.build_u2_cohort(
            u2_inputs,
            row.cohort_spec(),
            role_context=declared,
            births=u2_births,
        )
        members = cohort.income_rows(built, u2_inputs)
        adjusted = _estimate(members, row.income_spec(), u2_params)
        joined = tabulation.tabulation_rows(members, adjusted)
        incomes = adjusted.set_index("observation_id").loc[
            joined["observation_id"]
        ]
        monotone = (
            incomes["reform_income"] <= incomes["baseline_income"] + 1e-9
        ).to_numpy() & (
            joined["poor_reform"] | ~joined["poor_baseline"]
        ).to_numpy()
        units = pd.DataFrame({"split_unit": ut.floor_split_units(joined)})
        for seed in ut.DEFAULT_FLOOR_SEEDS:
            side_a, side_b = split_panel_by_person(
                units, "split_unit", fraction=ut.FLOOR_FRACTION, seed=seed
            )
            assert len(side_a) and len(side_b), (row_id, seed)
            for side in (side_a, side_b):
                assert monotone[side.index.to_numpy()].all(), (row_id, seed)
