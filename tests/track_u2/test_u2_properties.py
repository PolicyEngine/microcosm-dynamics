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
        "spouse_sex": draw(st.sampled_from(["male", "female"])) if joint else pd.NA,
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
        for c in (*family_income.HW_EARNED_CONCEPTS, *family_income.ASSET_INCOME_CONCEPTS)
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
        assert (out["reform_income"] <= out["baseline_income"] + 1e-6).all(), row_id
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
def test_new_enrollment_bounds(unearned, earned, ss, cut, year, couple, params):
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
            "person_id": [draw(st.integers(0, n // 2 + 1)) * 10 + i % 2 for i in range(n)],
            "family_unit_id": [201_900_000 + draw(st.integers(0, n)) for _ in range(n)],
            "weight": draw(
                st.lists(st.floats(0.5, 50.0), min_size=n, max_size=n)
            ),
            "sex": draw(
                st.lists(st.sampled_from(["male", "female"]), min_size=n, max_size=n)
            ),
            "marital_status_4": draw(
                st.lists(
                    st.sampled_from(
                        ["married", "widowed", "divorced", "never_married", "unclassified"]
                    ),
                    min_size=n,
                    max_size=n,
                )
            ),
            "birth_year": draw(
                st.lists(st.sampled_from([1949, 1951]), min_size=n, max_size=n)
            ),
            "stratum": draw(st.lists(st.sampled_from([1, 2, 90]), min_size=n, max_size=n)),
            "cluster": draw(st.lists(st.sampled_from([1, 2]), min_size=n, max_size=n)),
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
