"""The U2 income concept: U1 equality, IRA years and context guards.

The income estimator keeps U1's concept (section 4) with an explicit U2
parameter and role context (section 14).  A differential test holds the
U2 estimator equal to U1's ``adjusted_incomes`` on every row both accept,
for every registered row's income specification.  INVENTED DATA - NOT A
COMPARISON.
"""

from __future__ import annotations

import pandas as pd
import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import (
    cohort,
    estimator,
    rows,
    sources,
)


@pytest.fixture(scope="module")
def members(u0_cohort, u1_cohort, u2_inputs):
    both = pd.concat(
        [
            cohort.income_rows(u0_cohort, u2_inputs),
            cohort.income_rows(u1_cohort, u2_inputs),
        ],
        ignore_index=True,
    ).drop_duplicates("observation_id")
    both.attrs.update(
        provenance_kind="invented",
        target_id="U2",
        role_context=sources.INVENTED_DECLARED,
    )
    return both


def _u2(members, spec, params, **kwargs):
    return estimator.u2_adjusted_incomes(
        members,
        spec,
        context=estimator.U2EstimatorContext(sources.INVENTED_DECLARED),
        data_provenance=kwargs.pop("data_provenance", ap.INVENTED),
        life_table=params.life_tables[spec.mortality_basis],
        thresholds=params.thresholds,
        ssi=params.ssi,
        **kwargs,
    )


@pytest.mark.parametrize("row_id", rows.ROW_IDS)
def test_u2_estimator_equals_u1_on_rows_both_accept(
    row_id, members, u2_params
):
    """Differential: U1's primitives through U1's entry point and U2's.

    U1 accepts HEAD IRAS only in income year 2012; zeroing it elsewhere
    gives rows both accept.  Every output column must be identical.
    """

    spec = rows.REGISTERED_ROWS[row_id].income_spec()
    shared = members.copy()
    shared.loc[shared["income_year"] != 2012, "head_iras"] = 0
    shared.attrs.update(members.attrs)
    mine = _u2(shared, spec, u2_params)
    theirs = ap.adjusted_incomes(
        shared,
        spec.inherited(),
        data_provenance=ap.INVENTED,
        life_table=u2_params.life_tables[spec.mortality_basis],
        thresholds=u2_params.thresholds,
        ssi=u2_params.ssi,
    )
    pd.testing.assert_frame_equal(
        mine.reset_index(drop=True), theirs.reset_index(drop=True)
    )


def test_head_ira_income_is_removed_in_every_u2_income_year(
    members, u2_params
):
    assert estimator.HEAD_IRA_INCOME_YEARS == frozenset(range(2012, 2023, 2))
    adjusted = _u2(members, estimator.U2IncomeSpec(), u2_params)
    expected = (members["head_annuities"] + members["head_iras"]).to_numpy()
    assert (
        adjusted["retirement_account_income_removed"].to_numpy() == expected
    ).all()
    assert (members.loc[members["income_year"] > 2012, "head_iras"] > 0).any()
    # U1's constant is untouched: HEAD IRAS only in income year 2012.
    assert ap._HEAD_IRA_INCOME_YEARS == frozenset({2012})


def test_missing_head_iras_refuses(members, u2_params):
    broken = members.copy()
    broken.attrs.update(members.attrs)
    broken["head_iras"] = broken["head_iras"].astype("Float64")
    broken.loc[broken.index[0], "head_iras"] = pd.NA
    with pytest.raises(estimator.U2EstimatorError, match="head_iras"):
        _u2(broken, estimator.U2IncomeSpec(), u2_params)


@pytest.mark.parametrize(
    "overrides",
    [
        {"annuity_lives": "member_rule"},
        {"ssi_deeming": "recipients_only"},
        {"cut_start_year": None},
        {"cut_start_year": 2005},
        {"real_interest_rate": 0.04},
        {"target_id": "U1"},
        {"cut_rate": 1.5},
    ],
)
def test_u2_income_spec_refuses_unregistered_values(overrides):
    with pytest.raises(ValueError):
        estimator.U2IncomeSpec(**overrides)


def test_two_percent_sensitivity_is_registered_and_unscored():
    assert (
        estimator.U2IncomeSpec(real_interest_rate=0.02).real_interest_rate
        == 0.02
    )
    assert rows.SENSITIVITIES_UNSCORED == {"real_interest_rate": (0.02,)}


def test_context_and_target_guards(members, u2_params):
    wrong_target = members.copy()
    wrong_target.attrs.update({**members.attrs, "target_id": "U1"})
    with pytest.raises(ValueError, match="not 'U2'"):
        _u2(wrong_target, estimator.U2IncomeSpec(), u2_params)
    wrong_context = members.copy()
    wrong_context.attrs.update({**members.attrs, "role_context": "registry"})
    with pytest.raises(estimator.U2EstimatorError, match="role context"):
        _u2(wrong_context, estimator.U2IncomeSpec(), u2_params)
    with pytest.raises(estimator.U2EstimatorError, match="pointer"):
        _u2(
            members,
            estimator.U2IncomeSpec(),
            u2_params,
            data_provenance=ap.REGISTERED_REAL,
        )
    real = members.copy()
    real.attrs.update({**members.attrs, "provenance_kind": "psid_files"})
    with pytest.raises(estimator.U2EstimatorError, match="invented"):
        _u2(real, estimator.U2IncomeSpec(), u2_params)
    caller = members.copy()
    caller.attrs.update({**members.attrs, "provenance_kind": "caller_frames"})
    with pytest.raises(estimator.U2EstimatorError, match="invented rows"):
        _u2(caller, estimator.U2IncomeSpec(), u2_params)


def test_registered_estimate_needs_the_registry_context(members, u2_params):
    real = members.copy()
    real.attrs.update({**members.attrs, "provenance_kind": "psid_files"})
    with pytest.raises(estimator.U2EstimatorError, match="roles registry"):
        _u2(
            real,
            estimator.U2IncomeSpec(),
            u2_params,
            data_provenance=ap.REGISTERED_REAL,
            registration_pointer="x",
        )


def test_u1_captures_refused_by_the_estimator(members, u2_params):
    with pytest.raises(estimator.U2EstimatorError, match="U1 capture"):
        estimator.u2_adjusted_incomes(
            members,
            context=estimator.U2EstimatorContext(sources.INVENTED_DECLARED),
            data_provenance=ap.INVENTED,
            life_table=u2_params.life_tables["nchs_2000"],
            thresholds=ap.load_poverty_thresholds(),
            ssi=u2_params.ssi,
        )


def test_income_units_follow_the_income_slots(members, u2_params):
    head_wife = _u2(
        members, estimator.U2IncomeSpec(income_unit="head_wife"), u2_params
    )
    frame = members.reset_index(drop=True)
    ofum = frame["member_role"].eq("ofum").to_numpy()
    assert (head_wife["income_basis"].to_numpy()[ofum] == "family_unit").all()
    assert (head_wife["income_basis"].to_numpy()[~ofum] == "head_wife").all()
    # Codes 90 and 92 are OFUM members: they keep the family basis.
    assert set(frame.loc[ofum, "relationship"]) >= {50, 92}
    size = head_wife["unit_size"].to_numpy()[~ofum]
    assert (size == 1 + frame["wife_present"].to_numpy()[~ofum]).all()
