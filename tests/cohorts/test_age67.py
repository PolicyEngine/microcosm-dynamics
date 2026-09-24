"""Unit tests for the Track U age-67 cohort builder.

Every frame here is INVENTED: a handful of made-up persons, families,
marriages and weights chosen to exercise the observation plan, the
birth-year law's seed coordinate, the dispositions, the spouse and family
attachments and the wealth blockers. No value is a PSID observation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.data import family_income

_SEX = {
    1001: "male",
    1002: "female",
    2001: "female",
    3001: "male",
    4001: "female",
    5001: "male",
    6001: "female",
    7001: "male",
    8001: "na",
}


def _mh_row(pid, birth, **marriage):
    base = {
        "person_id": pid,
        "sex": _SEX[pid],
        "birth_year": birth,
        "birth_month": pd.NA,
        "marriage_order": pd.NA,
        "spouse_person_id": pd.NA,
        "start_year": pd.NA,
        "start_month": pd.NA,
        "end_year": pd.NA,
        "end_month": pd.NA,
        "separation_year": pd.NA,
        "separation_month": pd.NA,
        "how_ended": "never_married",
        "last_known_status": "never_married",
        "most_recent_report_year": 2023,
        "n_marriages": 0,
        "n_records": 1,
        "is_marriage": False,
    }
    if marriage:
        base.update(is_marriage=True, marriage_order=1, n_marriages=1)
        base.update(marriage)
    return base


def _marriage_history() -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            _mh_row(
                1001,
                1941,
                spouse_person_id=1002,
                start_year=1965,
                how_ended="intact",
                last_known_status="married",
            ),
            _mh_row(
                1002,
                1943,
                spouse_person_id=1001,
                start_year=1965,
                how_ended="intact",
                last_known_status="married",
            ),
            _mh_row(2001, 1945),
            _mh_row(3001, 1937),
            _mh_row(4001, 1942),
            _mh_row(5001, 1936),
            _mh_row(7001, 1939),
            _mh_row(8001, 1941),
        ]
    )
    for column in (
        "birth_year",
        "birth_month",
        "marriage_order",
        "spouse_person_id",
        "start_year",
        "start_month",
        "end_year",
        "end_month",
        "separation_year",
        "separation_month",
        "most_recent_report_year",
        "n_marriages",
    ):
        frame[column] = frame[column].astype("Int64")
    for column in ("sex", "how_ended", "last_known_status"):
        frame[column] = frame[column].astype("string")
    frame["n_records"] = frame["n_records"].astype("int64")
    frame["is_marriage"] = frame["is_marriage"].astype(bool)
    return frame


#: wave -> (person, interview, sequence, relationship, age, weight)
_ANCHOR_ROWS = {
    2005: [
        (1001, 3, 1, 10, 63, 90.0),
        (3001, 5, 1, 10, 67, 80.0),
        (5001, 51, 1, 10, 68, 60.0),
        (7001, 7, 1, 10, 65, 70.0),
    ],
    2007: [(7001, 7, 55, 10, 67, 30.0)],
    2009: [
        (1001, 11, 1, 10, 67, 100.0),
        (1002, 11, 2, 20, 65, 100.0),
        (4001, 41, 3, 30, 66, 40.0),
        (8001, 81, 1, 10, 67, 50.0),
    ],
    2011: [
        (1001, 21, 1, 10, 69, 110.0),
        (1002, 21, 2, 20, 67, 110.0),
        (6001, 21, 3, 30, 67, 110.0),
        (4001, 42, 3, 30, 68, 45.0),
        (2001, 29, 1, 10, 65, 20.0),
    ],
    2013: [(2001, 33, 75, 10, 67, 25.0)],
}


def _anchors() -> dict[int, pd.DataFrame]:
    people = sorted(_SEX)
    out = {}
    for wave in age67.WAVES:
        rows = {pid: (pid, 0, 0, 0, 0, 0.0) for pid in people}
        for row in _ANCHOR_ROWS.get(wave, []):
            rows[row[0]] = row
        frame = pd.DataFrame(
            list(rows.values()),
            columns=[
                "person_id",
                "interview",
                "sequence",
                "relationship",
                "age",
                "weight",
            ],
        )
        frame["reported_birth_year"] = pd.array(
            [pd.NA] * len(frame), dtype="Int64"
        )
        out[wave] = frame
    return out


def _family(wave: int) -> pd.DataFrame:
    interviews = sorted(
        {row[1] for row in _ANCHOR_ROWS.get(wave, []) if row[2] <= 20}
    )
    frame = pd.DataFrame(
        {
            "wave": wave,
            "income_year": wave - 1,
            "interview": interviews,
            "total_family_income": [
                1000 * (i + 1) for i in range(len(interviews))
            ],
            "fu_size": 1,
        }
    )
    for concept in (
        *family_income.SOCIAL_SECURITY_CONCEPTS,
        *family_income.SSI_CONCEPTS,
        *family_income.ASSET_INCOME_CONCEPTS,
    ):
        frame[concept] = 0
    return frame


def _inputs(**overrides) -> age67.Age67Inputs:
    values = {
        "anchors": _anchors(),
        "design": pd.DataFrame(
            {
                "person_id": sorted(_SEX),
                "stratum": [1] * len(_SEX),
                "cluster": [1, 2] * (len(_SEX) // 2) + [1] * (len(_SEX) % 2),
            }
        ),
        "death_records": pd.DataFrame(
            {"person_id": list(_SEX), "sex": list(_SEX.values())}
        ),
        "marriage_history": _marriage_history(),
        "observed_earnings": pd.DataFrame(
            {"person_id": [], "period": [], "age": []}
        ).astype("int64"),
        "family_income": {wave: _family(wave) for wave in age67.WAVES},
        "family_wealth": {
            wave: _family(wave)[["wave", "interview"]].assign(
                wealth1=500, wealth1_acc=0
            )
            for wave in (2009, 2011, 2013)
        },
        "wealth_refusals": {
            2005: "WealthSupplementNotStagedError: invented",
            2007: "WealthSupplementNotStagedError: invented",
        },
        "provenance": {"kind": "invented_test_frames", "label": "INVENTED"},
    }
    values.update(overrides)
    return age67.Age67Inputs(**values)


def _dispositions(cohort) -> dict:
    return {
        (int(row.person_id), int(row.wave)): row.disposition
        for row in cohort.dispositions.itertuples()
    }


def test_observation_plans():
    u0 = age67.observation_plan(age67.Age67Spec())
    assert u0 == (
        (1937, 2005, 2004, 1.0),
        (1939, 2007, 2006, 1.0),
        (1941, 2009, 2008, 1.0),
        (1943, 2011, 2010, 1.0),
        (1945, 2013, 2012, 1.0),
    )
    u1 = age67.observation_plan(age67.Age67Spec(row="U1"))
    assert len(u1) == 5 + 8 + 1
    assert (1936, 2005, 2004, 1.0) in u1
    assert (1942, 2009, 2008, 0.5) in u1
    assert (1942, 2011, 2010, 0.5) in u1
    weights = {}
    for birth_year, _, _, multiplier in u1:
        weights[birth_year] = weights.get(birth_year, 0.0) + multiplier
    assert weights == {year: 1.0 for year in range(1936, 1946)}


def test_u0_observations_and_dispositions():
    cohort = age67.build_age67_cohort(_inputs())
    obs = cohort.observations.set_index("observation_id")
    assert sorted(obs.index) == [
        "1001:2009",
        "1002:2011",
        "3001:2005",
        "6001:2011",
    ]
    head = obs.loc["1001:2009"]
    assert head["member_role"] == "head"
    assert head["married"] and head["member_married_coresident"]
    assert head["spouse_person_id"] == 1002
    assert head["spouse_age"] == 65 and head["spouse_sex"] == "female"
    assert head["fu_legal_wife_present"]
    assert head["wife_sex"] == "female"
    assert head["member_age"] == 67
    assert head["family_unit_id"] == 2009 * 100_000 + 11
    assert head["wealth_status"] == "family_file"
    wife = obs.loc["1002:2011"]
    assert wife["member_role"] == "wife" and wife["spouse_age"] == 69
    ofum = obs.loc["6001:2011"]
    # no marriage history: the seed coordinate (2010 - 67) gives 1943
    assert ofum["birth_year"] == 1943
    assert ofum["birth_source"] == "derived_projection_age"
    assert ofum["member_role"] == "ofum"
    assert ofum["marital_status"] == "no_marriage_history"
    assert not ofum["married"]
    assert obs.loc["3001:2005", "wealth_status"] == (
        "blocked_wealth_supplement_not_staged"
    )
    disp = _dispositions(cohort)
    assert disp[(2001, 2013)] == "not_present:moved_out"
    assert disp[(7001, 2007)] == "not_present:institution"
    assert disp[(8001, 2009)] == "excluded_sex_unknown"
    assert cohort.provenance["kind"] == age67.CALLER_FRAMES


def test_u1_adds_even_birth_years_at_half_weight():
    cohort = age67.build_age67_cohort(_inputs(), age67.Age67Spec(row="U1"))
    obs = cohort.observations.set_index("observation_id")
    assert obs.loc["4001:2009", "weight"] == pytest.approx(20.0)
    assert obs.loc["4001:2011", "weight"] == pytest.approx(22.5)
    assert obs.loc["4001:2009", "member_age"] == 66
    assert obs.loc["4001:2011", "member_age"] == 68
    assert obs.loc["5001:2005", "weight_multiplier"] == 1.0


def test_institution_option_marks_the_missing_income_rule():
    cohort = age67.build_age67_cohort(
        _inputs(), age67.Age67Spec(presence="in_family_or_institution")
    )
    obs = cohort.observations.set_index("observation_id")
    assert obs.loc["7001:2007", "income_status"] == "income_rule_missing"


def test_income_rows_refuse_blocked_observations_unless_allowed():
    inputs = _inputs()
    cohort = age67.build_age67_cohort(inputs)
    with pytest.raises(ValueError, match="2005"):
        age67.income_rows(cohort, inputs)
    rows = age67.income_rows(cohort, inputs, allow_blocked=True)
    assert sorted(rows["observation_id"]) == [
        "1001:2009",
        "1002:2011",
        "6001:2011",
    ]
    assert set(rows["wealth1"]) == {500}
    assert rows.attrs["provenance_kind"] == age67.CALLER_FRAMES
    assert rows.attrs["left_out"]["wealth_supplement_not_staged"] == 1


def test_unsealed_psid_claim_is_refused():
    inputs = _inputs(
        provenance={"kind": "psid_files", "psid_files_sha256": {"a": "b"}}
    )
    with pytest.raises(ValueError, match="load_age67_inputs"):
        age67.build_age67_cohort(inputs)


def test_missing_family_record_is_refused():
    incomes = {wave: _family(wave) for wave in age67.WAVES}
    incomes[2009] = incomes[2009][incomes[2009]["interview"] != 11]
    with pytest.raises(ValueError, match="no family-file record"):
        age67.build_age67_cohort(_inputs(family_income=incomes))


def test_structural_summary_counts_only():
    inputs = _inputs()
    cohort = age67.build_age67_cohort(inputs)
    summary = age67.structural_summary(cohort, inputs)
    assert summary["n_observations"] == 4
    assert summary["n_observations_blocked"] == 1
    assert summary["n_observations_computable_now"] == 3
    assert summary["family_units_with_two_or_more_members"] == 1
    assert summary["observations_by_birth_year_and_wave"]["1943@2011"][
        "member_role"
    ] == {"ofum": 1, "wife": 1}
    text = repr(summary)
    for forbidden in ("poor", "threshold", "annuity"):
        assert forbidden not in text


def test_spec_validation_and_pending_decisions():
    with pytest.raises(ValueError):
        age67.Age67Spec(row="U9")
    with pytest.raises(ValueError):
        age67.Age67Spec(u1_single_observation_weight=0)
    fields = {item.field for item in age67.pending_decisions()}
    assert fields == set(age67.Age67Spec().as_dict())
