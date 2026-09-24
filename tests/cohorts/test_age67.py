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
        "sex": _SEX.get(pid, "na"),
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
        *family_income.HW_EARNED_CONCEPTS,
        "head_annuities",
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
    fallback = age67.observation_plan(age67.Age67Spec(row="U0-F"))
    assert fallback == u0[2:]
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
    assert head["marital_resolution"] == "marriage_history"
    assert head["spouse_person_id"] == 1002
    assert head["spouse_age"] == 65 and head["spouse_sex"] == "female"
    assert head["spouse_age_source"] == "derived_birth_year"
    assert head["fu_legal_wife_present"]
    assert head["wife_sex"] == "female"
    # the annuitants of fu_head_rule: the head himself and his legal wife
    assert head["fu_head_person_id"] == 1001
    assert head["fu_head_age"] == 67 and head["fu_head_sex"] == "male"
    assert head["fu_head_spouse_present"]
    assert head["fu_head_spouse_person_id"] == 1002
    assert head["fu_head_spouse_age"] == 65
    assert head["fu_head_spouse_sex"] == "female"
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
    # an OFUM (code 30) is not resolved by the relationship code
    assert ofum["marital_resolution"] == "unresolved_non_married"
    assert not ofum["married"]
    # its family's annuitants are the head 1001 and legal wife 1002
    assert ofum["fu_head_person_id"] == 1001
    assert ofum["fu_head_age"] == 69
    assert ofum["fu_head_spouse_age"] == 67
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


def _with_institution_member() -> age67.Age67Inputs:
    """Invented: person 9001 (no marriage history, female) is in an
    institution in 2009 (sequence 52), attached to family 11."""

    anchors = _anchors()
    for wave, frame in anchors.items():
        row = (
            (9001, 11, 52, 30, 67, 70.0)
            if wave == 2009
            else (9001, 0, 0, 0, 0, 0.0)
        )
        extra = pd.DataFrame(
            [row],
            columns=[
                "person_id",
                "interview",
                "sequence",
                "relationship",
                "age",
                "weight",
            ],
        )
        extra["reported_birth_year"] = pd.array([pd.NA], dtype="Int64")
        anchors[wave] = pd.concat([frame, extra], ignore_index=True)
    base = _inputs()
    return _inputs(
        anchors=anchors,
        design=pd.concat(
            [
                base.design,
                pd.DataFrame(
                    {"person_id": [9001], "stratum": [1], "cluster": [2]}
                ),
            ],
            ignore_index=True,
        ),
        death_records=pd.concat(
            [
                base.death_records,
                pd.DataFrame({"person_id": [9001], "sex": ["female"]}),
            ],
            ignore_index=True,
        ),
    )


def test_institution_rule_family_of_record_is_the_default():
    """U-inst: the institutionalized member takes its family of record.

    Invented 9001 is in an institution in 2009 attached to family 11
    (person 1001's family): the observation is an OFUM of that family,
    with no co-resident spouse, and merges family 11's income and wealth.
    """

    assert age67.Age67Spec().institution_income_rule == "family_of_record"
    inputs = _with_institution_member()
    spec = age67.Age67Spec(presence="in_family_or_institution")
    cohort = age67.build_age67_cohort(inputs, spec)
    obs = cohort.observations.set_index("observation_id")
    member = obs.loc["9001:2009"]
    assert member["in_institution"]
    assert member["income_status"] == "family_of_record"
    assert member["member_role"] == "ofum"
    assert member["relationship"] == 30
    assert not member["member_married_coresident"]
    assert member["family_unit_id"] == 2009 * 100_000 + 11
    assert member["birth_year"] == 1941
    assert not obs.loc["1001:2009", "in_institution"]
    rows = age67.income_rows(cohort, inputs, allow_blocked=True)
    merged = rows.set_index("observation_id")
    # family 11 is the first 2009 family record: income 1,000, wealth 500
    assert merged.loc["9001:2009", "total_family_income"] == 1000
    assert merged.loc["9001:2009", "wealth1"] == 500
    assert merged.loc["9001:2009", "fu_size"] == 1
    # the default population (in family only) never sees the member: it
    # is in no wave's in-family universe
    default = age67.build_age67_cohort(inputs)
    assert "9001:2009" not in set(default.observations["observation_id"])
    assert (9001, 2009) not in _dispositions(default)


def test_institution_rule_excluded_and_missing_family_of_record():
    inputs = _with_institution_member()
    excluded = age67.build_age67_cohort(
        inputs,
        age67.Age67Spec(
            presence="in_family_or_institution",
            institution_income_rule="excluded",
        ),
    )
    assert "9001:2009" not in set(excluded.observations["observation_id"])
    assert _dispositions(excluded)[(9001, 2009)] == (
        "institution_excluded_by_rule"
    )
    # 7001 is in an institution in 2007 attached to interview 7, which has
    # no 2007 family-file record in the invented frames
    cohort = age67.build_age67_cohort(
        inputs, age67.Age67Spec(presence="in_family_or_institution")
    )
    assert "7001:2007" not in set(cohort.observations["observation_id"])
    assert _dispositions(cohort)[(7001, 2007)] == (
        "institution_family_of_record_missing"
    )
    with pytest.raises(ValueError, match="institution_income_rule"):
        age67.Age67Spec(institution_income_rule="own_income")


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
    cell = summary["observations_by_birth_year_and_wave"]["1943@2011"]
    assert cell["member_role"] == {"ofum": 1, "wife": 1}
    assert cell["marital_resolution"] == {
        "marriage_history": 1,
        "unresolved_non_married": 1,
    }
    assert cell["fu_head_age_source"] == {"derived_birth_year": 2}
    receipt = summary["component_receipt_counts"]["2011"]
    assert receipt["family_farm_income_nonzero"] == 0
    assert receipt["family_head_retirement_account_income_nonzero"] == 0
    text = repr(summary)
    for forbidden in ("poor", "threshold", "annuity"):
        assert forbidden not in text


def test_unresolved_marital_status_is_an_explicit_pending_default():
    """Unresolved marital states are classified by relationship code.

    Plan F12 names MH85_23 but not what to do when it cannot resolve the
    state ("unknown") or the person has no record ("no_marriage_
    history"); the referee's answer (Q7) is the relationship code, with
    non-married as the named alternative.  Both are parameters with a
    pending decision, not a silent fallthrough.
    """

    spec = age67.Age67Spec()
    assert spec.unresolved_marital_status == "relationship_code"
    with pytest.raises(ValueError, match="unresolved_marital_status"):
        age67.Age67Spec(unresolved_marital_status="married")
    decisions = {item.field: item for item in age67.pending_decisions()}
    item = decisions["unresolved_marital_status"]
    assert item.default == "relationship_code"
    assert item.alternatives == ("non_married",)
    assert "F12" in item.default_basis and "Q7" in item.default_basis
    cohort = age67.build_age67_cohort(_inputs())
    ofum = cohort.observations.set_index("observation_id").loc["6001:2011"]
    assert ofum["marital_status"] == "no_marriage_history"
    assert not ofum["married"]
    assert cohort.provenance["spec"]["unresolved_marital_status"] == (
        "relationship_code"
    )


def _with_unresolved_couples() -> age67.Age67Inputs:
    """Invented, all in 2013 (income year 2012):

    * family 91: head 9101 (male, born 1945, marriage history "unknown":
      one undated marriage) with legal wife 9102 (female, no history,
      individual-file age 70, zero weight: a nonsample spouse);
    * family 92: female head 9201 (born 1945 by marriage history, age 67)
      with legal husband 9202 (code 90, male, no marriage history,
      individual-file age 67 in 2013, the earliest wave he is in a
      family, so the law's seed gives 2012 - 67 = 1945).
    """

    anchors = _anchors()
    rows = {
        9101: (9101, 91, 1, 10, 67, 60.0),
        9102: (9102, 91, 2, 20, 70, 0.0),
        9201: (9201, 92, 1, 10, 67, 50.0),
        9202: (9202, 92, 2, 90, 67, 50.0),
    }
    for wave, frame in anchors.items():
        extra = pd.DataFrame(
            [
                row if wave == 2013 else (pid, 0, 0, 0, 0, 0.0)
                for pid, row in rows.items()
            ],
            columns=[
                "person_id",
                "interview",
                "sequence",
                "relationship",
                "age",
                "weight",
            ],
        )
        extra["reported_birth_year"] = pd.array(
            [pd.NA] * len(extra), dtype="Int64"
        )
        anchors[wave] = pd.concat([frame, extra], ignore_index=True)
    history = _marriage_history()
    unknown = _mh_row(9101, 1945, how_ended="other")
    unknown["last_known_status"] = "married"
    unknown["sex"] = "male"
    head = _mh_row(
        9201,
        1945,
        spouse_person_id=9202,
        start_year=1970,
        how_ended="intact",
        last_known_status="married",
    )
    head["sex"] = "female"
    extra_history = pd.DataFrame([unknown, head]).astype(history.dtypes)
    history = pd.concat([history, extra_history], ignore_index=True)
    base = _inputs()
    incomes = {wave: _family(wave) for wave in age67.WAVES}
    wealth = dict(base.family_wealth)
    template = _family(2011).iloc[[0]]
    for interview in (91, 92):
        incomes[2013] = pd.concat(
            [
                incomes[2013],
                template.assign(
                    wave=2013, income_year=2012, interview=interview
                ),
            ],
            ignore_index=True,
        )
        wealth[2013] = pd.concat(
            [
                wealth[2013],
                pd.DataFrame(
                    {
                        "wave": [2013],
                        "interview": [interview],
                        "wealth1": [500],
                        "wealth1_acc": [0],
                    }
                ),
            ],
            ignore_index=True,
        )
    sexes = {9101: "male", 9102: "female", 9201: "female", 9202: "male"}
    return _inputs(
        anchors=anchors,
        marriage_history=history,
        family_income=incomes,
        family_wealth=wealth,
        design=pd.concat(
            [
                base.design,
                pd.DataFrame(
                    {
                        "person_id": list(sexes),
                        "stratum": [1] * 4,
                        "cluster": [1, 1, 2, 2],
                    }
                ),
            ],
            ignore_index=True,
        ),
        death_records=pd.concat(
            [
                base.death_records,
                pd.DataFrame(
                    {"person_id": list(sexes), "sex": list(sexes.values())}
                ),
            ],
            ignore_index=True,
        ),
    )


def test_relationship_code_resolves_unresolved_marital_states():
    """Referee Q7: the relationship code decides an unresolved state.

    9101 (head, history "unknown") with a legal wife in the family is
    married and co-resident with her; 9202 (legal husband, code 90, no
    history) is married to the female head.  Under "non_married" both are
    non-married with no spouse.
    """

    inputs = _with_unresolved_couples()
    obs = age67.build_age67_cohort(inputs).observations.set_index(
        "observation_id"
    )
    head = obs.loc["9101:2013"]
    assert head["marital_status"] == "unknown"
    assert head["marital_resolution"] == (
        "relationship_code_head_with_legal_spouse"
    )
    assert head["married"] and head["member_married_coresident"]
    assert head["spouse_person_id"] == 9102
    husband = obs.loc["9202:2013"]
    assert husband["relationship"] == 90
    assert husband["marital_status"] == "no_marriage_history"
    assert husband["marital_resolution"] == "relationship_code_legal_husband"
    assert husband["married"] and husband["member_married_coresident"]
    assert husband["spouse_person_id"] == 9201
    assert husband["member_role"] == "ofum"
    # the female head and her legal husband are the family's annuitants
    assert husband["fu_head_person_id"] == 9201
    assert husband["fu_head_sex"] == "female"
    assert husband["fu_head_spouse_present"]
    assert husband["fu_head_spouse_person_id"] == 9202
    assert husband["fu_head_spouse_sex"] == "male"
    assert obs.loc["9201:2013", "marital_resolution"] == "marriage_history"
    plain = age67.build_age67_cohort(
        inputs, age67.Age67Spec(unresolved_marital_status="non_married")
    ).observations.set_index("observation_id")
    for oid in ("9101:2013", "9202:2013"):
        assert plain.loc[oid, "marital_resolution"] == (
            "unresolved_non_married"
        )
        assert not plain.loc[oid, "married"]
        assert pd.isna(plain.loc[oid, "spouse_person_id"])


def test_annuitant_ages_use_derived_birth_years():
    """Referee Q8: income-year ages from derived birth years.

    Invented: 1001's legal wife 1002 is born 1943 by marriage history; at
    the 2009 interview her individual-file age is set to 66 (her birthday
    fell before the interview).  Income year 2008: the derived age is 65,
    the wave age 66.  9102, a zero-weight nonsample wife outside the
    universe with no history, gets her birth year from the law's seed
    (2012 - 70 = 1942), so her income-year age equals the wave age, 70.
    """

    inputs = _with_unresolved_couples()
    anchors = dict(inputs.anchors)
    frame = anchors[2009].copy()
    frame.loc[frame["person_id"].eq(1002), "age"] = 66
    anchors[2009] = frame
    import dataclasses

    inputs = dataclasses.replace(inputs, anchors=anchors)
    derived = age67.build_age67_cohort(inputs).observations.set_index(
        "observation_id"
    )
    assert derived.loc["1001:2009", "spouse_age"] == 65
    assert derived.loc["1001:2009", "spouse_age_source"] == (
        "derived_birth_year"
    )
    assert derived.loc["1001:2009", "fu_head_spouse_age"] == 65
    head = derived.loc["9101:2013"]
    assert head["spouse_age"] == 70
    assert head["spouse_age_source"] == "derived_birth_year"
    assert head["fu_head_spouse_age"] == 70
    wave = age67.build_age67_cohort(
        inputs, age67.Age67Spec(annuitant_age_source="wave_age")
    ).observations.set_index("observation_id")
    assert wave.loc["1001:2009", "spouse_age"] == 66
    assert wave.loc["1001:2009", "spouse_age_source"] == "wave_age"
    assert wave.loc["1001:2009", "fu_head_spouse_age"] == 66
    with pytest.raises(ValueError, match="annuitant_age_source"):
        age67.Age67Spec(annuitant_age_source="reported_birth_year")
    decisions = {item.field: item for item in age67.pending_decisions()}
    assert decisions["annuitant_age_source"].default == "derived_birth_year"
    assert "Q8" in decisions["annuitant_age_source"].default_basis


def test_u0f_keeps_only_the_fallback_birth_years():
    inputs = _inputs()
    fallback = age67.build_age67_cohort(inputs, age67.Age67Spec(row="U0-F"))
    obs = fallback.observations
    assert set(obs["birth_year"]) <= set(age67.FALLBACK_BIRTH_YEARS)
    assert "3001:2005" not in set(obs["observation_id"])
    # nothing is blocked, so the income rows need no allow_blocked
    rows = age67.income_rows(fallback, inputs)
    assert rows.attrs["left_out"]["wealth_supplement_not_staged"] == 0
    assert set(rows["observation_id"]) == {
        "1001:2009",
        "1002:2011",
        "6001:2011",
    }


def test_spec_validation_and_pending_decisions():
    with pytest.raises(ValueError):
        age67.Age67Spec(row="U9")
    with pytest.raises(ValueError):
        age67.Age67Spec(u1_single_observation_weight=0)
    fields = {item.field for item in age67.pending_decisions()}
    assert fields == set(age67.Age67Spec().as_dict())
