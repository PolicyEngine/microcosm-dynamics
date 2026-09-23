"""Unit tests for the PSID 2010 starting-cohort builder.

Every frame here is INVENTED for the tests: the persons, ages, weights,
marriages, earnings and Social Security amounts are made up to exercise
each rule of :mod:`populace_dynamics.cohorts.psid2010` and are not PSID
observations. The claiming PMFs are invented too (not SSA Table 6.B5.1).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.cohorts import psid2010 as cohort
from populace_dynamics.data import social_security_income as ssi
from tests.data.psid_fixtures import write_product

# --------------------------------------------------------------------------
# The invented population
# --------------------------------------------------------------------------
#: person_id -> (interview, sequence, relationship, age code, weight)
_ANCHOR = {
    1001: (11, 1, 10, 70, 1000.0),  # head; married to 1002; retired
    1002: (11, 2, 20, 66, 900.0),  # wife; first receipt bracketed
    2001: (12, 1, 10, 55, 800.0),  # M4-disabled recipient under 62
    3001: (13, 1, 10, 58, 700.0),  # widowed 2005; survivor under 62
    4001: (11, 3, 60, 85, 600.0),  # OFUM parent; widowed 1990
    5001: (15, 1, 10, 40, 500.0),  # divorced; no receipt
    5101: (16, 1, 10, 50, 450.0),  # separated in 2008
    6001: (15, 2, 30, 10, 300.0),  # child: born after 1980
    6002: (15, 3, 30, 1, 250.0),  # age code 1: birth year unresolved
    7001: (17, 1, 10, 45, 200.0),  # sex not coded
    8001: (18, 51, 10, 80, 400.0),  # institutionalized
    9001: (19, 1, 10, 50, 0.0),  # zero weight: outside the universe
    9101: (21, 1, 10, 63, 350.0),  # receipt in 2008 at age 61
    9201: (22, 1, 10, 68, 340.0),  # retired, censored at 2008
    9301: (23, 1, 10, 75, 330.0),  # retired, table key before 1998
    9401: (24, 1, 10, 45, 320.0),  # under-62 residual; clause-2 birth
}

_SEX = {
    1001: "male",
    1002: "female",
    2001: "male",
    3001: "female",
    4001: "female",
    5001: "male",
    5101: "female",
    6001: "male",
    6002: "female",
    7001: "na",
    8001: "female",
    9001: "male",
    9101: "male",
    9201: "female",
    9301: "male",
    9401: "female",
    3002: "male",
    4002: "male",
    5102: "male",
}


def _anchor() -> pd.DataFrame:
    rows = [
        {
            "person_id": pid,
            "interview": interview,
            "sequence": sequence,
            "relationship": relationship,
            "age": age,
            "reported_birth_year": pd.NA,
            "weight": weight,
        }
        for pid, (interview, sequence, relationship, age, weight) in (
            _ANCHOR.items()
        )
    ]
    frame = pd.DataFrame(rows)
    frame["reported_birth_year"] = frame["reported_birth_year"].astype("Int64")
    return frame


def _deaths() -> pd.DataFrame:
    rows = []
    for pid, sex in _SEX.items():
        status, year, lo, hi = "not_deceased", pd.NA, pd.NA, pd.NA
        if pid == 1001:
            status, year, lo, hi = "exact", 2015, 2015, 2015
        elif pid == 3002:
            status, year, lo, hi = "exact", 2005, 2005, 2005
        elif pid == 5001:
            status, year, lo, hi = "range", pd.NA, 2007, 2009
        rows.append(
            {
                "person_id": pid,
                "sex": sex,
                "death_status": status,
                "death_year": year,
                "death_year_lo": lo,
                "death_year_hi": hi,
            }
        )
    frame = pd.DataFrame(rows)
    for column in ("death_year", "death_year_lo", "death_year_hi"):
        frame[column] = frame[column].astype("Int64")
    return frame


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
        base.update(is_marriage=True, marriage_order=1, **marriage)
    return base


def _marriage_history() -> pd.DataFrame:
    rows = [
        _mh_row(
            1001,
            1940,
            spouse_person_id=1002,
            start_year=1965,
            how_ended="intact",
            last_known_status="married",
        ),
        _mh_row(
            1002,
            1944,
            spouse_person_id=1001,
            start_year=1965,
            how_ended="intact",
            last_known_status="married",
        ),
        _mh_row(2001, 1955),
        _mh_row(
            3001,
            1952,
            spouse_person_id=3002,
            start_year=1975,
            end_year=2005,
            how_ended="widowhood",
            last_known_status="widowed",
        ),
        _mh_row(
            3002,
            1950,
            spouse_person_id=3001,
            start_year=1975,
            end_year=2005,
            how_ended="widowhood",
            last_known_status="married",
        ),
        _mh_row(
            4001,
            1925,
            spouse_person_id=4002,
            start_year=1945,
            end_year=1990,
            how_ended="widowhood",
            last_known_status="widowed",
        ),
        # 4002 carries two different exact birth years (a conflict).
        _mh_row(4002, 1920),
        _mh_row(4002, 1921),
        _mh_row(
            5001,
            1970,
            spouse_person_id=5002,
            start_year=1995,
            end_year=2000,
            how_ended="divorce",
            last_known_status="divorced",
        ),
        _mh_row(
            5101,
            1960,
            spouse_person_id=5102,
            start_year=1985,
            separation_year=2008,
            how_ended="separated",
            last_known_status="separated",
        ),
        _mh_row(5102, 1962),
    ]
    frame = pd.DataFrame(rows)
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


def _earnings() -> pd.DataFrame:
    rows = [
        # 1001: 2007 and 2009 are biennial gaps; 2012 is after the cutoff.
        (1001, 1966, 20000.0, 26),
        (1001, 2006, 60000.0, 67),
        (1001, 2008, 62000.0, 69),
        (1001, 2010, 30000.0, 71),
        (1001, 2012, 5000.0, 73),
        # 9401: clause 2 gives median(period - age) = 1964.
        (9401, 2004, 40000.0, 40),
        (9401, 2006, 42000.0, 42),
    ]
    frame = pd.DataFrame(
        rows, columns=["person_id", "period", "earnings", "age"]
    )
    frame["earnings_acc"] = 0
    frame["role"] = "head"
    frame["weight"] = 1.0
    return frame


#: (person_id, wave) -> (role, amount, fu_ss_prior_year code)
_FAMILY_SS = {
    (1001, 2009): ("head", 12000, 1),
    (1002, 2009): ("spouse", 0, 1),
    (2001, 2009): ("head", 9000, 1),
    (3001, 2009): ("head", 0, 5),
    (5001, 2009): ("head", 0, 5),
    (5101, 2009): ("head", 0, 5),
    (9101, 2009): ("head", 5000, 1),
    (9201, 2009): ("head", 11000, 1),
    (9301, 2009): ("head", 12500, 1),
    (9401, 2009): ("head", 0, 5),
    (1001, 2011): ("head", 14000, 1),
    (1002, 2011): ("spouse", 6000, 1),
    (2001, 2011): ("head", 9000, 1),
    (3001, 2011): ("head", 8000, 5),
    (5001, 2011): ("head", 0, 5),
    (5101, 2011): ("head", 0, 5),
    (7001, 2011): ("head", 0, 5),
    (9101, 2011): ("head", 7000, 1),
    (9201, 2011): ("head", 12000, 1),
    (9301, 2011): ("head", 13000, 1),
    (9401, 2011): ("head", 5000, 5),
    (1001, 2013): ("head", 15000, 1),
}

#: (person_id, wave) -> (amount, mentioned types)
_INDIVIDUAL_SS = {
    (1001, 2011): (14000, {"retirement"}),
    (1002, 2011): (6000, {"dependent_of_retired"}),
    (2001, 2011): (9000, {"disability"}),
    (3001, 2011): (8000, {"survivor"}),
    (4001, 2011): (10000, {"survivor"}),
    (4001, 2009): (9500, {"survivor"}),
    (5001, 2011): (0, set()),
    (5101, 2011): (0, set()),
    (9101, 2011): (7000, {"retirement", "disability"}),
    (9201, 2011): (12000, {"retirement"}),
    (9301, 2011): (13000, {"retirement"}),
    (9401, 2011): (5000, None),
}


def _head_spouse_ss() -> pd.DataFrame:
    rows = []
    for (pid, wave), (role, amount, prior) in _FAMILY_SS.items():
        interview = _ANCHOR[pid][0] if wave == 2011 else pid
        rows.append(
            {
                "person_id": pid,
                "wave": wave,
                "income_year": wave - 1,
                "role": role,
                "ss_amount": amount,
                "ss_acc": 0,
                "fu_ss_prior_year": prior,
                "age": 50,
                "weight": 1.0,
                "interview": interview,
            }
        )
    return pd.DataFrame(rows)


def _individual_ss() -> pd.DataFrame:
    rows = []
    for (pid, wave), (amount, types) in _INDIVIDUAL_SS.items():
        row = {
            "person_id": pid,
            "wave": wave,
            "income_year": wave - 1,
            "relationship": 10,
            "interview": 1,
            "age": 50,
            "weight": 1.0,
            "ss_amount": amount,
            "ss_acc": 0,
            "type_combination": False,
        }
        for name in ssi.SS_TYPES:
            if types is None or amount == 0:
                row[f"type_{name}"] = pd.NA
            else:
                row[f"type_{name}"] = name in types
        rows.append(row)
    frame = pd.DataFrame(rows)
    for name in ssi.SS_TYPES:
        frame[f"type_{name}"] = frame[f"type_{name}"].astype("boolean")
    frame["type_combination"] = frame["type_combination"].astype("boolean")
    return frame


def _disability_status() -> pd.DataFrame:
    rows = [
        (2001, 2011, True),
        (1001, 2011, False),
        (9401, 2011, False),
        (9101, 2009, True),
        (9101, 2011, False),
    ]
    return pd.DataFrame(rows, columns=["person_id", "period", "disabled"])


def _claiming_pmf() -> dict:
    """INVENTED PMFs; the 2009 row is deliberately degenerate at 70."""

    regular = {62: 0.4, 63: 0.1, 64: 0.1, 65: 0.2, 66: 0.1, 67: 0.05, 70: 0.05}
    pmf = {}
    for sex in ("female", "male"):
        for year in range(1998, 2009):
            pmf[(sex, year)] = dict(regular)
        pmf[(sex, 2009)] = {70: 1.0}
    return pmf


def _inputs(**overrides) -> cohort.Psid2010Inputs:
    values = {
        "anchor": _anchor(),
        "death_records": _deaths(),
        "marriage_history": _marriage_history(),
        "observed_earnings": _earnings(),
        "head_spouse_ss": _head_spouse_ss(),
        "individual_ss": _individual_ss(),
        "disability_status": _disability_status(),
        "claiming_pmf": _claiming_pmf(),
    }
    values.update(overrides)
    return cohort.Psid2010Inputs(**values)


@pytest.fixture(scope="module")
def built() -> cohort.Psid2010Cohort:
    return cohort.build_psid2010_cohort(_inputs())


def _person(built: cohort.Psid2010Cohort, pid: int) -> pd.Series:
    return built.persons.set_index("person_id").loc[pid]


# --------------------------------------------------------------------------
# Membership and dispositions
# --------------------------------------------------------------------------
def test_dispositions_are_universe_total_and_single(built):
    dispositions = built.dispositions.set_index("person_id")["disposition"]
    # 8001 (institution) and 9001 (zero weight) are outside the universe.
    assert set(dispositions.index) == set(_ANCHOR) - {8001, 9001}
    assert dispositions[6001] == "outside_birth_cohort"
    assert dispositions[6002] == "excluded_birth_year_unresolved"
    assert dispositions[7001] == "excluded_sex_unknown"
    members = {
        1001,
        1002,
        2001,
        3001,
        4001,
        5001,
        5101,
        9101,
        9201,
        9301,
        9401,
    }
    assert set(dispositions[dispositions == "member"].index) == members
    assert set(built.persons["person_id"]) == members


def test_structural_invariants(built):
    persons = built.persons
    assert persons["person_id"].is_unique
    assert (persons["weight"] > 0).all()
    assert persons["birth_year"].max() <= cohort.DEFAULT_MAX_BIRTH_YEAR
    assert (persons["age_2010"] == 2010 - persons["birth_year"]).all()
    assert built.labels == ("PSID-seeded closed cohort",)
    assert len(built.social_security) == 3 * len(persons)


def test_institutions_enter_only_under_the_alternative_presence():
    spec = cohort.Psid2010CohortSpec(
        presence=cohort.Presence.IN_FAMILY_OR_INSTITUTION
    )
    alt = cohort.build_psid2010_cohort(_inputs(), spec)
    row = alt.persons.set_index("person_id").loc[8001]
    assert row["birth_year"] == 1930
    assert row["ss_2010_source"] == "unobserved"
    assert row["opening_status"] == "unobserved"


def test_birth_year_follows_the_section_3_1_precedence(built):
    assert _person(built, 1001)["birth_source"] == "exact_marriage"
    assert _person(built, 1001)["birth_year"] == 1940
    # Clause 2 (median of period - age) outranks the seed coordinate.
    assert _person(built, 9401)["birth_source"] == "inferred_period_age"
    assert _person(built, 9401)["birth_year"] == 1964
    # Clause 3 is 2010 - the 2011 age code.
    assert _person(built, 9201)["birth_source"] == "derived_projection_age"
    assert _person(built, 9201)["birth_year"] == 1942
    assert bool(_person(built, 9201)["birth_year_age_derived"])
    assert not bool(_person(built, 1001)["birth_year_age_derived"])


def test_death_columns_and_presence_inconsistency_flag(built):
    assert _person(built, 1001)["death_year"] == 2015
    assert _person(built, 5001)["death_status"] == "range"
    assert bool(_person(built, 5001)["death_before_2011_presence"])
    assert not bool(_person(built, 1001)["death_before_2011_presence"])


# --------------------------------------------------------------------------
# Marital state and spouse links
# --------------------------------------------------------------------------
def test_spouse_links_and_widowhood(built):
    head = _person(built, 1001)
    assert head["marital_status_2010"] == "married"
    assert head["spouse_person_id"] == 1002
    assert bool(head["spouse_in_cohort"])
    assert head["coresident_partner_person_id_2011"] == 1002
    assert head["coresident_partner_relationship_2011"] == 20
    assert _person(built, 1002)["coresident_partner_person_id_2011"] == 1001
    assert _person(built, 1002)["linked_spouse_birth_year"] == 1940

    widow = _person(built, 3001)
    assert widow["marital_status_2010"] == "widowed"
    assert widow["widowhood_year"] == 2005
    assert widow["late_spouse_person_id"] == 3002
    assert widow["late_spouse_death_year"] == 2005
    assert widow["linked_spouse_birth_year"] == 1950
    assert widow["linked_spouse_birth_source"] == "exact_marriage"

    # A late spouse with conflicting exact birth years is named, not guessed.
    parent = _person(built, 4001)
    assert parent["late_spouse_person_id"] == 4002
    assert pd.isna(parent["linked_spouse_birth_year"])
    assert parent["linked_spouse_birth_source"] == "conflicting_exact_marriage"
    assert pd.isna(parent["coresident_partner_person_id_2011"])

    assert _person(built, 5001)["marital_status_2010"] == "divorced"
    assert _person(built, 2001)["marital_status_2010"] == "never_married"
    assert _person(built, 9401)["marital_status_2010"] == "no_marriage_history"


def test_separation_follows_the_parameter(built):
    separated = _person(built, 5101)
    assert separated["marital_status_2010"] == "married"
    assert bool(separated["separated_2010"])
    assert separated["spouse_person_id"] == 5102
    assert not bool(separated["spouse_in_cohort"])
    assert separated["linked_spouse_birth_year"] == 1962
    alt = cohort.build_psid2010_cohort(
        _inputs(), cohort.Psid2010CohortSpec(separated_is_married=False)
    )
    row = alt.persons.set_index("person_id").loc[5101]
    assert row["marital_status_2010"] == "separated"
    assert pd.isna(row["spouse_person_id"])


def _episodes(*rows) -> pd.DataFrame:
    columns = [
        "person_id",
        "marriage_order",
        "start_year",
        "start_month",
        "episode_end_year",
        "how_ended",
        "episode_duration_years",
        "spouse_person_id",
        "last_known_status",
    ]
    records = [
        {
            "person_id": 1,
            "marriage_order": order,
            "start_year": start,
            "start_month": pd.NA,
            "episode_end_year": end,
            "how_ended": how,
            "episode_duration_years": pd.NA,
            "spouse_person_id": spouse,
            "last_known_status": "unknown",
        }
        for order, start, end, how, spouse in rows
    ]
    frame = pd.DataFrame(records, columns=columns)
    for column in (
        "marriage_order",
        "start_year",
        "episode_end_year",
        "spouse_person_id",
    ):
        frame[column] = frame[column].astype("Int64")
    return frame


@pytest.mark.parametrize(
    "rows, status, spouse",
    [
        ([], "never_married", None),
        ([(1, 1990, None, "intact", 7)], "married", 7),
        ([(1, 2011, None, "intact", 7)], "never_married", None),
        ([(1, 1990, 2012, "divorce", 7)], "married", 7),
        ([(1, 1990, 2010, "widowhood", 7)], "widowed", None),
        (
            [(1, 1980, 1990, "widowhood", 7), (2, 1995, None, "intact", 8)],
            "married",
            8,
        ),
        (
            [(1, 1980, 1990, "divorce", 7), (2, 1995, 2004, "widowhood", 8)],
            "widowed",
            None,
        ),
        ([(1, None, None, "intact", 7)], "unknown", None),
        ([(1, 1990, None, "divorce", 7)], "unknown", None),
        ([(1, 1990, None, "other", 7)], "unknown", None),
    ],
)
def test_marital_state_at_end_of_2010(rows, status, spouse):
    state = cohort.marital_state_at(_episodes(*rows), 2010)
    assert state["status"] == status
    if spouse is None:
        assert pd.isna(state["spouse_person_id"])
    else:
        assert state["spouse_person_id"] == spouse


def test_marital_state_flags_multiple_marriages_in_force():
    state = cohort.marital_state_at(
        _episodes((1, 1980, None, "intact", 7), (2, 1995, None, "intact", 8)),
        2010,
    )
    assert state["status"] == "married"
    assert state["spouse_person_id"] == 8
    assert state["multiple_in_force"]
    widowed = cohort.marital_state_at(
        _episodes((1, 1980, 2004, "widowhood", 7)), 2010
    )
    assert widowed["former_spouse_person_id"] == 7
    assert widowed["dissolution_year"] == 2004


def _with_separation(frame: pd.DataFrame, *years) -> pd.DataFrame:
    out = frame.copy()
    out["separation_year"] = pd.array(list(years), dtype="Int64")
    return out


@pytest.mark.parametrize(
    "separation, separated_is_married, status, separated, spouse, dissolved",
    [
        # Separated in 2008, divorced only in 2012: legally married at the
        # end of 2010 but living apart (MH16).
        (2008, True, "married", True, 7, None),
        (2008, False, "separated", False, None, 2008),
        # Separated only after 2010: an ordinary marriage in force.
        (2011, True, "married", False, 7, None),
        (2011, False, "married", False, 7, None),
        # No separation year recorded: unchanged behavior.
        (None, False, "married", False, 7, None),
    ],
)
def test_separation_before_a_later_divorce(
    separation, separated_is_married, status, separated, spouse, dissolved
):
    # Regression: the separation year of a marriage that ended in divorce
    # after 2010 was ignored, so the spouses counted as living together.
    episodes = _with_separation(
        _episodes((1, 1990, 2012, "divorce", 7)), separation
    )
    state = cohort.marital_state_at(
        episodes, 2010, separated_is_married=separated_is_married
    )
    assert state["status"] == status
    assert state["separated"] is separated
    if spouse is None:
        assert pd.isna(state["spouse_person_id"])
        assert state["former_spouse_person_id"] == 7
    else:
        assert state["spouse_person_id"] == spouse
    if dissolved is None:
        assert pd.isna(state["dissolution_year"])
    else:
        assert state["dissolution_year"] == dissolved


def test_divorce_by_2010_after_separation_stays_divorced():
    episodes = _with_separation(_episodes((1, 1990, 2009, "divorce", 7)), 2006)
    for separated_is_married in (True, False):
        state = cohort.marital_state_at(
            episodes, 2010, separated_is_married=separated_is_married
        )
        assert state["status"] == "divorced"
        assert state["dissolution_year"] == 2009


def _history_with_late_divorce() -> pd.DataFrame:
    """5001 separated in 2009 and divorced only in 2013 (INVENTED)."""

    history = _marriage_history()
    row = history["person_id"] == 5001
    history.loc[row, "end_year"] = 2013
    history.loc[row, "separation_year"] = 2009
    return history


def test_builder_uses_the_separation_year_of_a_later_divorce():
    inputs = _inputs(marriage_history=_history_with_late_divorce())
    default = cohort.build_psid2010_cohort(inputs).persons.set_index(
        "person_id"
    )
    assert default.loc[5001, "marital_status_2010"] == "married"
    assert bool(default.loc[5001, "separated_2010"])
    assert default.loc[5001, "spouse_person_id"] == 5002
    alt = cohort.build_psid2010_cohort(
        inputs, cohort.Psid2010CohortSpec(separated_is_married=False)
    ).persons.set_index("person_id")
    assert alt.loc[5001, "marital_status_2010"] == "separated"
    assert pd.isna(alt.loc[5001, "spouse_person_id"])


def test_episode_alignment_is_checked(monkeypatch):
    original = cohort.marriage.marriage_episodes

    def shuffled(history):
        return original(history).iloc[::-1].reset_index(drop=True)

    monkeypatch.setattr(cohort.marriage, "marriage_episodes", shuffled)
    with pytest.raises(AssertionError, match="do not align"):
        cohort.build_psid2010_cohort(_inputs())


# --------------------------------------------------------------------------
# Social Security sources and the opening stock
# --------------------------------------------------------------------------
def test_social_security_source_policy(built):
    assert _person(built, 1001)["ss_2010_source"] == "family_head_spouse"
    assert _person(built, 1001)["ss_2012"] == 15000
    parent = _person(built, 4001)
    assert parent["ss_2010_source"] == "individual_file"
    assert parent["ss_2010"] == 10000
    assert parent["ss_2008"] == 9500
    # Absent from the 2013 families: unobserved, never zero.
    assert pd.isna(parent["ss_2012"])
    assert parent["ss_2012_source"] == "unobserved"
    alt = cohort.build_psid2010_cohort(
        _inputs(),
        cohort.Psid2010CohortSpec(
            ofum_ss_source=cohort.OfumSsSource.UNOBSERVED
        ),
    )
    row = alt.persons.set_index("person_id").loc[4001]
    assert pd.isna(row["ss_2010"])
    assert row["opening_status"] == "unobserved"


@pytest.mark.parametrize(
    "pid, status, basis",
    [
        (1001, "retired_worker", "aged_not_widowed"),
        (1002, "retired_worker", "aged_not_widowed"),
        (2001, "disabled_worker", "under62_m4_disabled"),
        (3001, "survivor", "under62_widowed"),
        (4001, "survivor", "aged_widowed"),
        (5001, "none", "no_receipt_2010"),
        (9101, "retired_worker", "aged_not_widowed"),
        (9401, "disabled_worker", "under62_residual"),
    ],
)
def test_plan_rule_is_the_default(built, pid, status, basis):
    row = _person(built, pid)
    assert row["opening_status"] == status
    assert row["opening_status_basis"] == basis


def test_plan_rule_alternatives():
    spec = cohort.Psid2010CohortSpec(
        under_62_residual=cohort.Under62Residual.UNCLASSIFIED,
        aged_m4_disabled_di_below_age=66,
        m4_waves=(2009, 2011),
    )
    persons = cohort.build_psid2010_cohort(_inputs(), spec).persons
    row = persons.set_index("person_id")
    assert row.loc[9401, "opening_status"] == "unclassified"
    # 9101 is 63 and reported disabled in 2009.
    assert row.loc[9101, "opening_status"] == "disabled_worker"
    assert row.loc[9101, "opening_status_basis"] == (
        "aged_m4_disabled_below_age"
    )
    assert bool(row.loc[9101, "m4_disabled_2009"])


def test_m4_wave_absent_from_inputs_fails_closed():
    # Regression: a consulted wave with no status rows read as "nobody
    # M4-disabled" and silently moved every recipient down the rule.
    only_2011 = _disability_status()
    only_2011 = only_2011[only_2011["period"] == 2011]
    with pytest.raises(ValueError, match="no rows for M4 wave 2009"):
        cohort.build_psid2010_cohort(
            _inputs(disability_status=only_2011),
            cohort.Psid2010CohortSpec(m4_waves=(2009, 2011)),
        )


def test_m4_status_unknown_is_flagged(built):
    # 3001 and 4001 have no ascertained 2011 status: not M4-disabled, and
    # the default is visible.
    assert bool(_person(built, 3001)["m4_status_unknown"])
    assert not bool(_person(built, 3001)["m4_disabled"])
    assert not bool(_person(built, 2001)["m4_status_unknown"])
    assert not bool(_person(built, 1001)["m4_status_unknown"])


def _extra_people(rows: dict) -> dict:
    """INVENTED persons appended to the fixture: pid -> (anchor, sex, ss)."""

    anchor = _anchor()
    deaths = _deaths()
    family = _head_spouse_ss()
    extra_anchor = []
    extra_deaths = []
    extra_family = []
    for pid, (age, sex, ss_2010) in rows.items():
        interview = 900 + len(extra_anchor)
        extra_anchor.append(
            {
                "person_id": pid,
                "interview": interview,
                "sequence": 1,
                "relationship": 10,
                "age": age,
                "reported_birth_year": pd.NA,
                "weight": 100.0,
            }
        )
        extra_deaths.append(
            {
                "person_id": pid,
                "sex": sex,
                "death_status": "not_deceased",
                "death_year": pd.NA,
                "death_year_lo": pd.NA,
                "death_year_hi": pd.NA,
            }
        )
        extra_family.append(
            {
                "person_id": pid,
                "wave": 2011,
                "income_year": 2010,
                "role": "head",
                "ss_amount": ss_2010,
                "ss_acc": 0,
                "fu_ss_prior_year": 5,
                "age": age,
                "weight": 1.0,
                "interview": interview,
            }
        )
    anchor = pd.concat([anchor, pd.DataFrame(extra_anchor)], ignore_index=True)
    anchor["reported_birth_year"] = anchor["reported_birth_year"].astype(
        "Int64"
    )
    deaths = pd.concat([deaths, pd.DataFrame(extra_deaths)], ignore_index=True)
    for column in ("death_year", "death_year_lo", "death_year_hi"):
        deaths[column] = deaths[column].astype("Int64")
    family = pd.concat([family, pd.DataFrame(extra_family)], ignore_index=True)
    return {
        "anchor": anchor,
        "death_records": deaths,
        "head_spouse_ss": family,
    }


def test_born_1980_boundary_and_age_62_boundary():
    # Seed-coordinate births (clause 3: 2010 - 2011 age code) on either
    # side of both boundaries; every value here is INVENTED.
    inputs = _inputs(
        **_extra_people(
            {
                9501: (30, "male", 0),  # born 1980: member
                9502: (29, "female", 0),  # born 1981: outside
                9503: (62, "male", 9000),  # age 62 in 2010 with SS
                9504: (61, "female", 9000),  # age 61 in 2010 with SS
            }
        )
    )
    built = cohort.build_psid2010_cohort(inputs)
    dispositions = built.dispositions.set_index("person_id")["disposition"]
    persons = built.persons.set_index("person_id")
    assert dispositions[9501] == "member"
    assert persons.loc[9501, "birth_year"] == 1980
    assert dispositions[9502] == "outside_birth_cohort"
    assert 9502 not in persons.index
    assert persons.loc[9503, "age_2010"] == 62
    assert persons.loc[9503, "opening_status"] == "retired_worker"
    assert persons.loc[9503, "opening_status_basis"] == "aged_not_widowed"
    assert persons.loc[9504, "age_2010"] == 61
    assert persons.loc[9504, "opening_status"] == "disabled_worker"
    assert persons.loc[9504, "opening_status_basis"] == "under62_residual"
    assert persons["birth_year"].max() == 1980


def test_positive_weight_outside_presence_is_accounted(built):
    # 8001 is institutionalized with a positive weight: outside the default
    # universe, so it has no disposition but is counted with its weight.
    outside = built.diagnostics["positive_weight_outside_presence"]
    assert outside == {"institution": {"unweighted": 1, "weighted": 400.0}}
    assert 8001 not in set(built.dispositions["person_id"])
    alt = cohort.build_psid2010_cohort(
        _inputs(),
        cohort.Psid2010CohortSpec(
            presence=cohort.Presence.IN_FAMILY_OR_INSTITUTION
        ),
    )
    assert alt.diagnostics["positive_weight_outside_presence"] == {}


def test_married_with_dead_linked_spouse_is_counted(built):
    assert built.diagnostics["married_with_linked_spouse_dead_by_2010"] == 0
    assert built.diagnostics["separated_2010"] == 1
    deaths = _deaths()
    row = deaths["person_id"] == 5102
    deaths.loc[row, ["death_status"]] = "exact"
    deaths.loc[row, ["death_year", "death_year_lo", "death_year_hi"]] = 2009
    for column in ("death_year", "death_year_lo", "death_year_hi"):
        deaths[column] = deaths[column].astype("Int64")
    rebuilt = cohort.build_psid2010_cohort(_inputs(death_records=deaths))
    assert rebuilt.diagnostics["married_with_linked_spouse_dead_by_2010"] == 1


def test_under_62_precedence_alternative():
    inputs = _inputs(
        disability_status=pd.concat(
            [
                _disability_status(),
                pd.DataFrame(
                    {"person_id": [3001], "period": [2011], "disabled": [True]}
                ),
            ],
            ignore_index=True,
        )
    )
    default = cohort.build_psid2010_cohort(inputs).persons.set_index(
        "person_id"
    )
    assert default.loc[3001, "opening_status"] == "disabled_worker"
    alt = cohort.build_psid2010_cohort(
        inputs,
        cohort.Psid2010CohortSpec(
            under_62_precedence=cohort.Under62Precedence.WIDOWHOOD_THEN_M4
        ),
    ).persons.set_index("person_id")
    assert alt.loc[3001, "opening_status"] == "survivor"


def test_reported_type_rule_with_precedence_and_fallback():
    spec = cohort.Psid2010CohortSpec(
        status_rule=cohort.StatusRule.REPORTED_TYPE
    )
    row = cohort.build_psid2010_cohort(_inputs(), spec).persons.set_index(
        "person_id"
    )
    assert row.loc[1002, "opening_status"] == "spouse"
    assert row.loc[9101, "opening_status"] == "disabled_worker"
    assert bool(row.loc[9101, "reported_type_multiple"])
    assert row.loc[9401, "opening_status"] == "disabled_worker"
    assert row.loc[9401, "opening_status_basis"] == (
        "no_reported_type_fallback:under62_residual"
    )
    retirement_first = (
        "retirement",
        "disability",
        "survivor",
        "dependent_of_disabled",
        "dependent_of_retired",
        "other",
    )
    spec = cohort.Psid2010CohortSpec(
        status_rule=cohort.StatusRule.REPORTED_TYPE,
        reported_type_precedence=retirement_first,
    )
    row = cohort.build_psid2010_cohort(_inputs(), spec).persons.set_index(
        "person_id"
    )
    assert row.loc[9101, "opening_status"] == "retired_worker"


# --------------------------------------------------------------------------
# Opening claim year
# --------------------------------------------------------------------------
def test_bracketed_first_receipt(built):
    wife = _person(built, 1002)
    assert wife["opening_claim_year"] == 2010
    assert wife["opening_claim_year_basis"] == "bracketed_first_observed"
    assert wife["opening_claim_age"] == 66
    widow = _person(built, 3001)
    assert widow["opening_claim_year"] == 2010
    alt = cohort.build_psid2010_cohort(
        _inputs(),
        cohort.Psid2010CohortSpec(
            bracket_resolution=cohort.BracketResolution.FU_PRIOR_YEAR_INDICATOR
        ),
    ).persons.set_index("person_id")
    # Family 11 answered "yes" to 2009 receipt; family 13 answered "no".
    assert alt.loc[1002, "opening_claim_year"] == 2009
    assert alt.loc[1002, "opening_claim_year_basis"] == "bracketed_fu_yes_2009"
    assert alt.loc[3001, "opening_claim_year"] == 2010
    assert alt.loc[3001, "opening_claim_year_basis"] == "bracketed_fu_no_2009"


def test_censored_retired_worker_is_imputed_from_capped_table(built):
    row = _person(built, 9201)
    assert row["opening_claim_year_basis"] == "imputed_censored_at_2008"
    assert 62 <= row["opening_claim_age"] <= 2008 - 1942
    assert row["opening_claim_year"] == 1942 + row["opening_claim_age"]
    assert row["claim_schedule_year"] == 2004
    assert pd.isna(row["claim_schedule_snap"])
    old = _person(built, 9301)
    assert old["claim_schedule_year"] == 1998
    assert old["claim_schedule_snap"] == "lower"
    # Every schedule year respects the <=2008 table cap (2009 is excluded).
    years = built.persons["claim_schedule_year"].dropna()
    assert (years <= 2008).all()


def test_imputation_is_person_keyed_and_seeded(built):
    again = cohort.build_psid2010_cohort(_inputs())
    pd.testing.assert_series_equal(
        built.persons["opening_claim_age"], again.persons["opening_claim_age"]
    )
    ages = set()
    for seed in range(12):
        spec = cohort.Psid2010CohortSpec(stock_imputation_root_seed=seed)
        persons = cohort.build_psid2010_cohort(_inputs(), spec).persons
        ages.add(
            int(persons.set_index("person_id").loc[9201, "opening_claim_age"])
        )
    assert len(ages) > 1
    assert ages <= {62, 63, 64, 65, 66}


def test_empty_mass_and_non_retired_censoring(built):
    early = _person(built, 9101)
    assert early["opening_claim_year_basis"] == "imputation_empty_mass"
    assert pd.isna(early["opening_claim_year"])
    assert early["claim_schedule_year"] == 2008
    disabled = _person(built, 2001)
    assert disabled["opening_claim_year_basis"] == (
        "censored_at_2008_no_table_law"
    )
    assert disabled["opening_claim_year_upper_bound"] == 2008
    assert pd.isna(disabled["opening_claim_year"])
    assert _person(built, 5001)["opening_claim_year_basis"] == (
        "not_applicable"
    )


# --------------------------------------------------------------------------
# Careers
# --------------------------------------------------------------------------
def test_careers_apply_the_first_estimates_laws(built):
    careers = built.careers[built.careers["person_id"] == 1001].set_index(
        "year"
    )
    assert careers.index.min() == 1968
    assert careers.index.max() == 2010
    assert careers.loc[2006, "provenance"] == "observed"
    assert careers.loc[2007, "earnings"] == 61000.0
    assert careers.loc[2007, "provenance"] == "gap_imputed"
    assert careers.loc[2009, "earnings"] == 46000.0
    assert careers.loc[2010, "earnings"] == 30000.0
    assert careers.loc[1990, "provenance"] == "unknown"
    assert careers.loc[1990, "earnings"] == 0.0
    young = built.careers[built.careers["person_id"] == 9401].set_index("year")
    assert young.index.min() == 1964 + 22
    assert young.loc[2005, "earnings"] == 41000.0
    # Edge carry: 2007 has only its 2006 neighbor.
    assert young.loc[2007, "earnings"] == 42000.0
    assert young.loc[2009, "provenance"] == "unknown"
    assert set(built.careers["year"]) <= set(range(1968, 2011))
    assert _person(built, 9401)["career_coverage_start"] == 1986


# --------------------------------------------------------------------------
# Spec, pending decisions, summary and validation
# --------------------------------------------------------------------------
def test_pending_decisions_cover_every_spec_field():
    decisions = {item.field: item for item in cohort.pending_decisions()}
    spec_fields = {
        spec_field.name
        for spec_field in dataclasses.fields(cohort.Psid2010CohortSpec)
    }
    assert set(decisions) == spec_fields | {"birth_inference_max_wave"}
    defaults = cohort.Psid2010CohortSpec().as_dict()
    for name in spec_fields:
        assert decisions[name].default == defaults[name]
        assert decisions[name].default_basis
        assert decisions[name].as_dict()["field"] == name


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reported_type_precedence": ("disability",)},
        {"m4_waves": (2013,)},
        {"m4_waves": (2007,)},
        {"m4_waves": ()},
        {"max_birth_year": 2011},
        {"claim_table_max_year": 2011},
        {"stock_imputation_root_seed": -1},
        {"aged_m4_disabled_di_below_age": 62},
        {"status_rule": "not_a_rule"},
    ],
)
def test_spec_rejects_invalid_choices(kwargs):
    with pytest.raises(ValueError):
        cohort.Psid2010CohortSpec(**kwargs)


def test_structural_summary_counts_only(built):
    summary = cohort.structural_summary(built)
    assert summary["persons"]["unweighted"] == 11
    assert summary["persons"]["weighted"] == pytest.approx(
        sum(_ANCHOR[pid][4] for pid in built.persons["person_id"])
    )
    assert summary["person_id_unique"]
    assert summary["birth_year_range"] == [1925, 1970]
    assert summary["labels"] == ["PSID-seeded closed cohort"]
    assert "the five-group comparison statistic" in summary["not_computed"]
    bands = summary["ss_receipt_2010_by_age_2010"]
    assert set(bands) == {"30-49", "50-61", "62-64", "65-69", "70-79", "80+"}
    receipt = sum(
        item["ss_receipt_2010"]["unweighted"] for item in bands.values()
    )
    assert receipt == summary["ss_receipt_2010"]["unweighted"] == 9
    diagnostics = summary["diagnostics"]
    assert (
        diagnostics["head_spouse_family_vs_individual_amount"][
            "receipt_disagreements"
        ]
        == 0
    )
    assert diagnostics["disposition_person_ids_unique"]


def test_invalid_inputs_fail_closed():
    with pytest.raises(ValueError, match="missing columns"):
        cohort.build_psid2010_cohort(
            _inputs(anchor=_anchor().drop(columns="weight"))
        )
    duplicated = pd.concat([_anchor(), _anchor().iloc[:1]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate person_id"):
        cohort.build_psid2010_cohort(_inputs(anchor=duplicated))


def test_claiming_reference_pin_matches_the_registered_inputs():
    from scripts import registered_m6_inputs

    assert (
        cohort.CLAIMING_REFERENCE_SHA256
        == registered_m6_inputs.CLAIMING_REFERENCE_SHA256
    )
    assert (
        cohort.CLAIMING_REFERENCE_PATH.name
        == registered_m6_inputs.CLAIMING_REFERENCE_PATH.name
    )


# --------------------------------------------------------------------------
# The anchor reader on an invented fixed-width product
# --------------------------------------------------------------------------
def _write_anchor(root: Path, *, weight_label: str, extra=()) -> None:
    fields = [
        ("ER30001", 4, "1968 INTERVIEW NUMBER", [1, 1, 2]),
        ("ER30002", 3, "PERSON NUMBER 68", [1, 2, 1]),
        ("ER34101", 5, "2011 INTERVIEW NUMBER", [11, 11, 0]),
        ("ER34102", 2, "SEQUENCE NUMBER 11", [1, 2, 0]),
        ("ER34103", 2, "RELATION TO HEAD 11", [10, 20, 0]),
        ("ER34104", 3, "AGE OF INDIVIDUAL 11", [70, 66, 0]),
        ("ER34106", 4, "YEAR INDIVIDUAL BORN 11", [1940, 9999, 0]),
        ("ER34155", 5, weight_label, [1000, 900, 0]),
        *extra,
    ]
    write_product(root / "ind2023er", "IND2023ER.sps", "IND2023ER.txt", fields)


def test_anchor_reader_verifies_labels(tmp_path):
    _write_anchor(
        tmp_path, weight_label="CORE/IMM INDIVIDUAL CROSS-SECTION WT 11"
    )
    frame = cohort.read_anchor_wave(data_dir=tmp_path)
    assert frame["person_id"].tolist() == [1001, 1002, 2001]
    assert frame["weight"].tolist() == [1000.0, 900.0, 0.0]
    assert frame["reported_birth_year"].iloc[0] == 1940
    assert pd.isna(frame["reported_birth_year"].iloc[1])
    _write_anchor(
        tmp_path, weight_label="CORE/IMM INDIVIDUAL CROSS-SECTION WT 09"
    )
    with pytest.raises(ValueError, match="ER34155"):
        cohort.read_anchor_wave(data_dir=tmp_path)


def test_anchor_reader_requires_a_unique_2011_weight(tmp_path):
    _write_anchor(
        tmp_path,
        weight_label="CORE/IMM INDIVIDUAL CROSS-SECTION WT 11",
        extra=[
            ("ER99999", 5, "LATINO INDIVIDUAL CROSS-SECTION WT 11", [1, 1, 1])
        ],
    )
    with pytest.raises(ValueError, match="expected only ER34155"):
        cohort.read_anchor_wave(data_dir=tmp_path)
