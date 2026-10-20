"""The birth law's inputs and the d1724 count-out (section 16d).

INVENTED DATA - NOT A COMPARISON.  Every person, age code, weight and
year here is invented: the seeded U2 generator's base population, its two
d1724 variants, and members these tests add to it as caller frames.

``career.derive_birth_years`` (read-only, section 14) asserts that a
birth year it derives from a seed coordinate (age code 2-125, ``seed year
- age``) lies in ``[DERIVED_BIRTH_MIN, DERIVED_BIRTH_MAX]`` (1889-2016),
and refuses every seed age code but 1-125 and 999.  The d1649 structural
pass stopped on the assertion, which would have masked the refusal.
Max's ruling d1724 (section 16d), for each person only the seed could
date: re-seeds a person whose earliest presence carries a refused code
from the earliest presence the law can date; counts out a person with no
such presence (``seed_age_0`` or ``no_valid_seed_age``) or whose seed
implies a year before 1889 or after 2016; discloses each count; and
changes nothing else.  These tests hold, for every input:

* the universe and the four counted-out sets partition the presence set
  (every positive-weight, in-family person of any support wave);
* each person's outcome is the one the law gives that person alone, from
  the seed section 16d names: a history or earnings year wins; otherwise
  a stop on the support assertion is counted out on the seed's side, and
  no presence the law can date is counted out under its first code;
* no counted-out person can be in the 1946-55 cohort, and a cohort
  member with one refused code keeps a seed and its observations;
* the law completes on every case, and the annuitant extension never
  reaches a refusal or re-admits a counted-out person;
* each count is disclosed in every row's structural summary and decides
  nothing: observations, dispositions and every other count are as if
  the counted-out persons were absent.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.estimates import career
from populace_dynamics.uniform_cut_track_u2 import cohort, invented, sources

COUNTED_OUT = "seed_births_counted_out"
EVERY_CASE = "seed_births_every_case"
BEFORE, AFTER, AGE_0, NO_VALID = cohort.SEED_BIRTH_COUNTED_OUT
BASE_ID = 700_000
#: The members the generator variants add (``invented.py``).
EXPECTED_OUT = {
    BEFORE: {BASE_ID - 13},
    AFTER: {BASE_ID - 11, BASE_ID - 12},
    AGE_0: {BASE_ID - 16},
    NO_VALID: {BASE_ID - 17},
}
AT_1889, AT_2016 = BASE_ID - 14, BASE_ID - 15
#: The re-seeded cohort members: (person, birth year, U1 waves).
RESEEDED = {
    BASE_ID - 18: (1950, {2017, 2019}),
    BASE_ID - 19: (1946, {2013, 2015}),
}
NONE_OUT = {reason: frozenset() for reason in cohort.SEED_BIRTH_COUNTED_OUT}
#: Members these tests add as caller frames (ids no variant uses).
ADDED = BASE_ID - 100
#: Age codes the law refuses: 0 (Inap.) and codes outside the loader's
#: documented domain, which only caller frames can carry.
REFUSED_CODES = (0, 126, 500, 998, 1000)


@pytest.fixture(scope="module")
def counted_out(u2_inputs):
    return invented.invented_variant(u2_inputs, COUNTED_OUT)


@pytest.fixture(scope="module")
def every_case(u2_inputs):
    return invented.invented_variant(u2_inputs, EVERY_CASE)


@pytest.fixture(scope="module")
def host(u2_inputs):
    """A reference person in-family with a positive weight in every
    support wave, whose families the added members join."""

    waves = cohort.SUPPORT_WAVES
    for person in sorted(set(u2_inputs.persons["person_id"].astype(int))):
        rows = [
            u2_inputs.anchors[w][u2_inputs.anchors[w]["person_id"].eq(person)]
            for w in waves
        ]
        if all(
            len(r) == 1
            and int(r["relationship"].iloc[0]) == 10
            and 1 <= int(r["sequence"].iloc[0]) <= 20
            and float(r["weight"].iloc[0]) > 0
            for r in rows
        ):
            return person
    raise AssertionError("no reference person is present in every wave")


def _added(
    inputs: cohort.U2Inputs,
    person: int,
    host: int,
    waves: dict[int, tuple[int, int, float]],
    *,
    birth_year: int | None = None,
    earnings: tuple[tuple[int, int], ...] = (),
) -> cohort.U2Inputs:
    """``inputs`` plus ``person`` in ``host``'s family in each wave of
    ``waves`` (``{wave: (age code, relationship, weight)}``), absent
    elsewhere, as caller frames; ``birth_year`` adds a marriage-history
    birth year and ``earnings`` ``(period, age)`` earnings rows."""

    anchors = {}
    for wave, frame in inputs.anchors.items():
        row = {
            "person_id": person,
            "interview": 0,
            "sequence": 0,
            "relationship": 0,
            "age": 0,
            "reported_birth_year": pd.NA,
            "weight": 0.0,
        }
        if wave in waves:
            age, relationship, weight = waves[wave]
            interview = int(
                frame.loc[frame["person_id"].eq(host), "interview"].iloc[0]
            )
            family = frame[
                frame["interview"].eq(interview)
                & frame["sequence"].between(1, 20)
            ]
            row.update(
                interview=interview,
                sequence=int(family["sequence"].max()) + 1,
                relationship=relationship,
                age=age,
                weight=weight,
            )
        anchors[wave] = pd.concat(
            [frame, pd.DataFrame([row])], ignore_index=True
        ).astype(frame.dtypes.to_dict())
    design = inputs.design.set_index("person_id").loc[host]
    changed = dataclasses.replace(
        inputs,
        anchors=anchors,
        design=pd.concat(
            [
                inputs.design,
                pd.DataFrame(
                    [
                        {
                            "person_id": person,
                            "stratum": int(design["stratum"]),
                            "cluster": int(design["cluster"]),
                        }
                    ]
                ),
            ],
            ignore_index=True,
        ).astype("int64"),
        persons=pd.concat(
            [
                inputs.persons,
                pd.DataFrame([{"person_id": person, "sex": "female"}]),
            ],
            ignore_index=True,
        ).astype({"person_id": "int64", "sex": "string"}),
    )
    if birth_year is not None:
        history = changed.marriage_history
        record = {column: pd.NA for column in history.columns}
        record.update(
            person_id=person,
            sex="female",
            birth_year=birth_year,
            n_records=1,
            is_marriage=False,
        )
        changed = dataclasses.replace(
            changed,
            marriage_history=pd.concat(
                [history, pd.DataFrame([record])], ignore_index=True
            ).astype(history.dtypes.to_dict()),
        )
    if earnings:
        frame = changed.observed_earnings
        rows = pd.DataFrame(
            [
                {
                    "person_id": person,
                    "period": period,
                    "earnings": 1000.0,
                    "role": "head",
                    "age": age,
                    "weight": 1.0,
                    "earnings_acc": 0,
                }
                for period, age in earnings
            ]
        )
        changed = dataclasses.replace(
            changed,
            observed_earnings=pd.concat(
                [frame, rows], ignore_index=True
            ).astype(frame.dtypes.to_dict()),
        )
    return cohort.replace_provenance(changed, kind=cohort.CALLER_FRAMES)


def _accepted(age: int) -> bool:
    """Whether the law takes this seed age code without refusing it."""
    return age == 999 or 1 <= age <= 125


def _presences(inputs: cohort.U2Inputs, person: int) -> list[tuple[int, int]]:
    """``(wave, age code)`` of each positive-weight, in-family presence."""
    out = []
    for wave in cohort.SUPPORT_WAVES:
        frame = inputs.anchors[wave]
        row = frame[
            frame["person_id"].eq(person)
            & frame["sequence"].between(1, 20)
            & frame["weight"].gt(0)
        ]
        if len(row):
            out.append((wave, int(row["age"].iloc[0])))
    return out


def _alone(inputs: cohort.U2Inputs, person: int, seed=None):
    """The law run on ``person`` alone, from the seed ``(wave, age code)``
    or without a seed coordinate."""
    history = inputs.marriage_history
    earnings = inputs.observed_earnings
    coordinates = None
    if seed is not None:
        wave, age = seed
        coordinates = pd.DataFrame(
            {
                "person_id": [person],
                "year": [wave - 1],
                "anchor_wave": [wave],
                "age": [age],
            }
        )
    (record,) = career.derive_birth_years(
        history[history["person_id"].eq(person)],
        earnings[earnings["person_id"].eq(person)],
        seed_coordinates=coordinates,
        required_person_ids={person},
    )
    return record


def _expected(inputs: cohort.U2Inputs, person: int):
    """Section 16d's outcome for ``person``, from its own frames and the
    law run on it alone: ``(reason, None, False)`` when counted out, else
    ``(None, record, reseeded)``."""
    rows = _presences(inputs, person)
    without = _alone(inputs, person)
    if without.source is not career.BirthSource.UNRESOLVED:
        return None, without, False
    wave, age = rows[0]
    reseeded = not _accepted(age)
    if reseeded:
        valid = [
            (w, a)
            for w, a in rows
            if 2 <= a <= 125
            and career.DERIVED_BIRTH_MIN
            <= (w - 1) - a
            <= career.DERIVED_BIRTH_MAX
        ]
        if not valid:
            return (AGE_0 if age == 0 else NO_VALID), None, False
        wave, age = valid[0]
    try:
        record = _alone(inputs, person, (wave, age))
    except AssertionError as stop:
        assert "lies outside" in str(stop)
        year = (wave - 1) - age
        return (
            (BEFORE if year < career.DERIVED_BIRTH_MIN else AFTER),
            None,
            False,
        )
    return None, record, reseeded


def _presence(inputs: cohort.U2Inputs) -> set[int]:
    present = set()
    for wave in cohort.SUPPORT_WAVES:
        frame = inputs.anchors[wave]
        present |= set(
            frame.loc[
                frame["sequence"].between(1, 20) & frame["weight"].gt(0),
                "person_id",
            ].astype(int)
        )
    return present


def _builds(inputs, births):
    declared = sources.RoleContext.declared()
    return {
        row: cohort.build_u2_cohort(
            inputs,
            cohort.U2CohortSpec(row=row),
            role_context=declared,
            births=births,
        )
        for row in cohort.ROWS
    }


def _first_rule(seed, history, earnings):
    """The rule before d1724: the earliest presence, nothing counted out."""
    return cohort._seed_frame(seed), dict(NONE_OUT), frozenset()


# ---------------------------------------------------------------------------
# The failures the rule removes
# ---------------------------------------------------------------------------
def test_the_d1649_failure_is_reproduced_without_the_rule(
    counted_out, monkeypatch
):
    """With the rule disabled, the variant stops the law on the support
    assertion, the failure category of the d1649 pass; with it, the
    derivation completes."""

    births = cohort.derive_u2_births(counted_out)
    gone = set().union(*EXPECTED_OUT.values())
    assert set(births.universe) == _presence(counted_out) - gone
    monkeypatch.setattr(cohort, "_seed_for_the_law", _first_rule)
    with pytest.raises(AssertionError, match=r"lies outside \[1889, 2016\]"):
        cohort.derive_u2_births(counted_out)


@pytest.mark.parametrize("code", REFUSED_CODES)
def test_the_masked_refusal_is_reproduced_without_the_rule(
    u2_inputs, host, code, monkeypatch
):
    """A refused seed code stops the law after its loop (the refusal the
    d1649 assertion masked); with the rule, the person is counted out
    under its code and the derivation completes."""

    inputs = _added(u2_inputs, ADDED, host, {2017: (code, 30, 500.0)})
    births = cohort.derive_u2_births(inputs)
    reason = AGE_0 if code == 0 else NO_VALID
    assert births.counted_out[reason] == {ADDED}
    monkeypatch.setattr(cohort, "_seed_for_the_law", _first_rule)
    with pytest.raises(ValueError, match="unrecognized PSID seed-age codes"):
        cohort.derive_u2_births(inputs)


# ---------------------------------------------------------------------------
# Each reason, the boundary years and re-seeding
# ---------------------------------------------------------------------------
def test_each_reason_is_counted_out(counted_out):
    births = cohort.derive_u2_births(counted_out)
    assert dict(births.counted_out) == EXPECTED_OUT
    assert births.reseeded == frozenset()
    for person in set().union(*EXPECTED_OUT.values()):
        assert person not in births.universe
        assert person not in births.records
        assert births.birth_year(person) is None
        assert person not in set(births.seed["person_id"])


def test_seeds_at_1889_and_2016_stay_in(every_case):
    births = cohort.derive_u2_births(every_case)
    for person, year in ((AT_1889, 1889), (AT_2016, 2016)):
        assert person in births.universe
        record = births.records[person]
        assert record.birth_year == year
        assert record.source is career.BirthSource.DERIVED_PROJECTION_AGE
    assert (career.DERIVED_BIRTH_MIN, career.DERIVED_BIRTH_MAX) == (1889, 2016)
    assert cohort.SEED_BIRTH_COUNTED_OUT == (
        "before_1889",
        "after_2016",
        "seed_age_0",
        "no_valid_seed_age",
    )


def test_a_cohort_member_with_a_refused_code_keeps_a_seed(every_case):
    """Each re-seeded member's seed is its earliest presence the law can
    date; it is a U1 target observed in its waves, the wave whose code
    the law refuses included."""

    births = cohort.derive_u2_births(every_case)
    assert births.reseeded == frozenset(RESEEDED)
    seed = births.seed.set_index("person_id")
    built = _builds(every_case, births)["U1"].observations
    for person, (year, waves) in RESEEDED.items():
        record = births.records[person]
        assert (record.birth_year, record.source) == (
            year,
            career.BirthSource.DERIVED_PROJECTION_AGE,
        )
        rows = _presences(every_case, person)
        assert not _accepted(rows[0][1])
        assert int(seed.loc[person, "anchor_wave"]) == rows[1][0]
        observed = built[built["person_id"].eq(person)]
        assert set(observed["wave"]) == waves
        assert set(observed["birth_year"]) == {year}


@pytest.mark.parametrize(
    "waves, reason, year, reseeded",
    [
        ({2013: (124, 50, 500.0)}, BEFORE, None, False),
        ({2013: (125, 50, 500.0)}, BEFORE, None, False),
        ({2013: (123, 50, 500.0)}, None, 1889, False),
        ({2019: (2, 30, 500.0)}, None, 2016, False),
        ({2021: (4, 30, 500.0)}, None, 2016, False),
        ({2021: (3, 30, 500.0)}, AFTER, None, False),
        ({2023: (2, 30, 500.0)}, AFTER, None, False),
        # The seed is the earliest presence whose code the law takes; a
        # later presence never replaces it (section 3).
        ({2013: (124, 50, 500.0), 2015: (75, 50, 500.0)}, BEFORE, None, False),
        ({2013: (124, 50, 0.0), 2015: (75, 50, 500.0)}, None, 1939, False),
        # Refused codes: re-seeded from the earliest presence the law can
        # date, else counted out under the first code.
        ({2023: (0, 30, 500.0)}, AGE_0, None, False),
        ({2015: (0, 40, 500.0), 2017: (66, 40, 500.0)}, None, 1950, True),
        ({2021: (0, 60, 500.0), 2023: (2, 60, 500.0)}, AGE_0, None, False),
        ({2015: (998, 40, 500.0), 2017: (66, 40, 500.0)}, None, 1950, True),
        ({2015: (998, 40, 500.0)}, NO_VALID, None, False),
        (
            {2015: (998, 40, 500.0), 2017: (1, 40, 500.0)},
            NO_VALID,
            None,
            False,
        ),
        ({2015: (0, 40, 500.0), 2017: (998, 40, 500.0)}, AGE_0, None, False),
        (
            {2015: (998, 40, 500.0), 2017: (0, 40, 500.0)},
            NO_VALID,
            None,
            False,
        ),
        (
            {
                2015: (0, 40, 500.0),
                2017: (999, 40, 500.0),
                2019: (70, 40, 500.0),
            },
            None,
            1948,
            True,
        ),
        # Re-seeding skips a presence whose year the law does not support
        # (2021 - 1 - 3 = 2017), and takes the next (2022 - 60 = 1962).
        (
            {
                2017: (998, 30, 500.0),
                2021: (3, 30, 500.0),
                2023: (60, 30, 500.0),
            },
            None,
            1962,
            True,
        ),
    ],
)
def test_each_bound_reason_and_reseed(
    u2_inputs, host, waves, reason, year, reseeded
):
    inputs = _added(u2_inputs, ADDED, host, waves)
    births = cohort.derive_u2_births(inputs)
    if reason is None:
        assert births.records[ADDED].birth_year == year
        assert all(ADDED not in out for out in births.counted_out.values())
    else:
        for other, people in births.counted_out.items():
            assert people == ({ADDED} if other == reason else frozenset())
    assert (ADDED in births.reseeded) is reseeded
    assert _expected(inputs, ADDED)[0] == reason


# ---------------------------------------------------------------------------
# Precedence, the law's own unresolved codes and the target cohort
# ---------------------------------------------------------------------------
def test_a_history_or_earnings_year_keeps_its_precedence(u2_inputs, host):
    """The law's precedence is unchanged: a person whose marriage history
    or earnings give a birth year keeps it, whatever the seed implies or
    whatever code it carries, and is neither counted out nor re-seeded --
    here a 1951 cohort member whose seed implies 1887, another whose only
    code is 0, and persons whose seeds imply 2020 or carry code 998."""

    inputs = _added(
        u2_inputs, ADDED, host, {2013: (125, 50, 500.0)}, birth_year=1951
    )
    inputs = _added(
        inputs, ADDED - 1, host, {2019: (0, 40, 500.0)}, birth_year=1953
    )
    inputs = _added(
        inputs,
        ADDED - 2,
        host,
        {2023: (2, 30, 500.0)},
        earnings=((1980, 20), (1982, 22)),
    )
    inputs = _added(
        inputs,
        ADDED - 3,
        host,
        {2017: (998, 30, 500.0)},
        earnings=((1990, 40),),
    )
    births = cohort.derive_u2_births(inputs)
    assert dict(births.counted_out) == NONE_OUT
    assert births.reseeded == frozenset()
    exact = career.BirthSource.EXACT_MARRIAGE
    inferred = career.BirthSource.INFERRED_PERIOD_AGE
    for person, year, source in (
        (ADDED, 1951, exact),
        (ADDED - 1, 1953, exact),
        (ADDED - 2, 1960, inferred),
        (ADDED - 3, 1950, inferred),
    ):
        record = births.records[person]
        assert (record.birth_year, record.source) == (year, source)
    assert births.birth_year(ADDED) in cohort.ALL_BIRTH_YEARS
    assert births.birth_year(ADDED - 1) in cohort.ALL_BIRTH_YEARS


@pytest.mark.parametrize(
    "age, year", [(1, None), (999, None), (60, 1962)], ids=str
)
def test_codes_1_and_999_stay_unresolved_and_are_never_counted_out(
    u2_inputs, host, age, year
):
    """Seed codes 1 and 999 keep the law's unresolved path, in the
    universe, even where ``seed year - code`` lies outside 1889-2016."""

    inputs = _added(u2_inputs, ADDED, host, {2023: (age, 30, 500.0)})
    births = cohort.derive_u2_births(inputs)
    assert ADDED in births.universe
    assert births.birth_year(ADDED) == year
    if year is None:
        assert births.records[ADDED].source is career.BirthSource.UNRESOLVED
    assert dict(births.counted_out) == NONE_OUT
    assert births.reseeded == frozenset()


def test_no_counted_out_person_can_be_in_the_target_cohort(every_case):
    """A counted-out person has no birth-year source but the seed (the
    law, run without it, leaves the person unresolved), and no presence
    the law can date inside 1889-2016, which contains 1946-55."""

    births = cohort.derive_u2_births(every_case)
    assert career.DERIVED_BIRTH_MIN < min(cohort.ALL_BIRTH_YEARS)
    assert max(cohort.ALL_BIRTH_YEARS) < career.DERIVED_BIRTH_MAX
    counted = set().union(*births.counted_out.values())
    assert counted == set().union(*EXPECTED_OUT.values())
    for person in counted:
        assert _alone(every_case, person).source is (
            career.BirthSource.UNRESOLVED
        )
        rows = _presences(every_case, person)
        datable = [
            (w - 1) - a
            for w, a in rows
            if 2 <= a <= 125
            and career.DERIVED_BIRTH_MIN
            <= (w - 1) - a
            <= career.DERIVED_BIRTH_MAX
        ]
        if _accepted(rows[0][1]):
            year = (rows[0][0] - 1) - rows[0][1]
            assert not 1889 <= year <= 2016
        else:
            assert not datable
    for built in _builds(every_case, births).values():
        assert not counted & set(built.observations["person_id"])
        assert not counted & set(built.dispositions["person_id"])


def test_every_case_runs_end_to_end(every_case):
    """On the variant holding every case, the births, both rows, their
    income rows and structural summaries complete, with each count."""

    births = cohort.derive_u2_births(every_case)
    for built in _builds(every_case, births).values():
        assert not cohort.income_rows(built, every_case).empty
        summary = cohort.structural_summary(built)
        assert summary["n_seed_birth_year_counted_out"] == {
            reason: len(people) for reason, people in EXPECTED_OUT.items()
        }
        assert summary["n_seed_birth_year_reseeded"] == len(RESEEDED)


# ---------------------------------------------------------------------------
# The annuitant extension
# ---------------------------------------------------------------------------
def test_the_extension_never_reaches_a_refusal(u2_inputs, host):
    """The extension seeds only presences whose code the law takes and
    whose implied year it supports (code 999 kept): zero-weight
    reference persons first seen at 124 in 2013 or with code 998 are
    seeded by the 2015 presence instead, and ones seen only at 3 in 2021
    or with code 0 get no record; none stops the law."""

    inputs = _added(
        u2_inputs, ADDED, host, {2013: (124, 20, 0.0), 2015: (70, 20, 0.0)}
    )
    inputs = _added(inputs, ADDED - 1, host, {2021: (3, 10, 0.0)})
    inputs = _added(
        inputs, ADDED - 2, host, {2013: (998, 20, 0.0), 2015: (70, 20, 0.0)}
    )
    inputs = _added(inputs, ADDED - 3, host, {2019: (0, 10, 0.0)})
    births = cohort.derive_u2_births(inputs)
    for person in (ADDED, ADDED - 1, ADDED - 2, ADDED - 3):
        assert person not in births.universe
    assert births.records[ADDED].birth_year == 2014 - 70
    assert births.records[ADDED - 2].birth_year == 2014 - 70
    assert ADDED - 1 not in births.records
    assert ADDED - 3 not in births.records
    assert dict(births.counted_out) == NONE_OUT


def test_a_counted_out_person_never_joins_the_extension(u2_inputs, host):
    """A counted-out person had a positive-weight presence, so is not
    outside the universe: the extension, which would have seeded these
    code-20 persons from the zero-weight 2015 presence, leaves them out."""

    inputs = _added(
        u2_inputs, ADDED, host, {2013: (124, 20, 500.0), 2015: (70, 20, 0.0)}
    )
    inputs = _added(
        inputs, ADDED - 1, host, {2013: (0, 20, 500.0), 2015: (70, 20, 0.0)}
    )
    births = cohort.derive_u2_births(inputs)
    assert births.counted_out[BEFORE] == {ADDED}
    assert births.counted_out[AGE_0] == {ADDED - 1}
    for person in (ADDED, ADDED - 1):
        assert person not in births.records
        assert births.birth_year(person) is None


# ---------------------------------------------------------------------------
# Disclosure, and nothing else changes
# ---------------------------------------------------------------------------
def test_each_count_is_disclosed_in_every_row(
    u2_inputs, counted_out, every_case
):
    for inputs, counts, reseeded in (
        (u2_inputs, {reason: 0 for reason in NONE_OUT}, 0),
        (
            counted_out,
            {reason: len(p) for reason, p in EXPECTED_OUT.items()},
            0,
        ),
        (
            every_case,
            {reason: len(p) for reason, p in EXPECTED_OUT.items()},
            len(RESEEDED),
        ),
    ):
        births = cohort.derive_u2_births(inputs)
        for built in _builds(inputs, births).values():
            assert built.diagnostics["n_seed_birth_year_counted_out"] == counts
            assert built.diagnostics["n_seed_birth_year_reseeded"] == reseeded
            summary = cohort.structural_summary(built)
            assert summary["n_seed_birth_year_counted_out"] == counts
            assert list(summary["n_seed_birth_year_counted_out"]) == list(
                cohort.SEED_BIRTH_COUNTED_OUT
            )
            assert summary["n_seed_birth_year_reseeded"] == reseeded


def test_the_count_out_changes_nothing_else(u2_inputs, counted_out):
    """The variant adds only counted-out members: the births, every row's
    observations, dispositions, design frame, income rows and every other
    count equal the base population's."""

    base = cohort.derive_u2_births(u2_inputs)
    births = cohort.derive_u2_births(counted_out)
    assert births.universe == base.universe
    assert dict(births.records) == dict(base.records)
    pd.testing.assert_frame_equal(births.seed, base.seed)
    before, after = _builds(u2_inputs, base), _builds(counted_out, births)
    changed = {"n_seed_birth_year_counted_out", "births_inputs_sha256"}
    for row in cohort.ROWS:
        pd.testing.assert_frame_equal(
            after[row].observations, before[row].observations
        )
        pd.testing.assert_frame_equal(
            after[row].dispositions, before[row].dispositions
        )
        pd.testing.assert_frame_equal(
            cohort.design_frame(counted_out, after[row].spec),
            cohort.design_frame(u2_inputs, before[row].spec),
        )
        for key in set(before[row].diagnostics) | set(after[row].diagnostics):
            if key not in changed:
                assert (
                    after[row].diagnostics[key] == before[row].diagnostics[key]
                ), key
        left = cohort.structural_summary(after[row])
        right = cohort.structural_summary(before[row])
        assert set(left) == set(right)
        for key in left:
            if key != "n_seed_birth_year_counted_out":
                assert left[key] == right[key], key
    pd.testing.assert_frame_equal(
        cohort.income_rows(after["U0"], counted_out),
        cohort.income_rows(before["U0"], u2_inputs),
    )


def test_the_kept_members_change_only_their_own_counts(
    counted_out, every_case
):
    """Beyond the counted-out members, the every-case variant adds four
    kept ones: the universe gains them, the cohort gains the two
    re-seeded targets with their own observations and dispositions, and
    U0 (odd birth years only) is unchanged."""

    base = cohort.derive_u2_births(counted_out)
    births = cohort.derive_u2_births(every_case)
    kept = {AT_1889, AT_2016, *RESEEDED}
    assert births.universe == base.universe | kept
    before, after = _builds(counted_out, base), _builds(every_case, births)
    pd.testing.assert_frame_equal(
        after["U0"].observations, before["U0"].observations
    )
    for row in cohort.ROWS:
        for frame in ("observations", "dispositions"):
            new = getattr(after[row], frame)
            old = getattr(before[row], frame)
            mine = new["person_id"].isin(RESEEDED)
            pd.testing.assert_frame_equal(
                new[~mine].reset_index(drop=True), old.reset_index(drop=True)
            )
        diagnostics = after[row].diagnostics
        earlier = before[row].diagnostics
        assert diagnostics["n_universe"] == earlier["n_universe"] + 4
        assert diagnostics["n_target_birth_year"] == (
            earlier["n_target_birth_year"] + 2
        )
        assert diagnostics["n_outside_birth_years"] == (
            earlier["n_outside_birth_years"] + 2
        )
        assert diagnostics["n_seed_birth_year_reseeded"] == 2
    u1 = after["U1"].observations
    assert set(u1.loc[u1["person_id"].isin(RESEEDED), "person_id"]) == set(
        RESEEDED
    )


# ---------------------------------------------------------------------------
# Property: every outcome is the law's on that person alone
# ---------------------------------------------------------------------------
#: Every age code the law takes or refuses: the documented domain and
#: codes outside it.
_ANY_AGE = st.one_of(
    st.integers(1, 125),
    st.just(999),
    st.just(0),
    st.sampled_from(REFUSED_CODES),
)
_RELATIONSHIPS = st.sampled_from((10, 20, 30, 50, 60))
#: Mostly positive, so the first row is mostly the seed.
_WEIGHTS = st.sampled_from((500.0, 500.0, 500.0, 0.0))


@st.composite
def _first_row(draw) -> tuple[int, int]:
    """A (wave, age code) drawn mostly near either end of the support,
    the oldest codes in 2013 (1887-1890) or young children in 2019-2023
    (2016-2021, code 1 included), or a code the law refuses."""

    kind = draw(
        st.sampled_from(("low", "low", "high", "high", "refused", "any"))
    )
    if kind == "low":
        return 2013, draw(st.integers(122, 125))
    if kind == "high":
        wave = draw(st.sampled_from((2019, 2021, 2023)))
        return wave, draw(st.integers(1, 6))
    if kind == "refused":
        wave = draw(st.sampled_from(cohort.SUPPORT_WAVES[:-1]))
        return wave, draw(st.sampled_from(REFUSED_CODES))
    return draw(st.sampled_from(cohort.SUPPORT_WAVES)), draw(_ANY_AGE)


@st.composite
def _member(draw) -> dict:
    """A member whose first row is drawn by :func:`_first_row`, plus, after
    a refused first code, often a later presence aged 2-90, and up to
    three later rows of any code; any relationship and weight; mostly
    seed-only (no history or earnings year)."""

    first, age = draw(_first_row())
    rows = {first: (age, draw(_RELATIONSHIPS), draw(_WEIGHTS))}
    later = [wave for wave in cohort.SUPPORT_WAVES if wave > first]
    if later and not _accepted(age) and draw(st.booleans()):
        # Mostly a later presence the law can date, to re-seed from.
        wave = draw(st.sampled_from(later))
        rows[wave] = (draw(st.integers(2, 90)), rows[first][1], 500.0)
        later.remove(wave)
    if later:
        for wave in draw(
            st.lists(st.sampled_from(later), unique=True, max_size=3)
        ):
            rows[wave] = (draw(_ANY_AGE), draw(_RELATIONSHIPS), draw(_WEIGHTS))
    sourced = st.sampled_from((False, False, False, True))
    return {
        "waves": rows,
        "birth_year": (
            draw(st.integers(1880, 2025)) if draw(sourced) else None
        ),
        "earnings_age": draw(st.integers(14, 90)) if draw(sourced) else None,
    }


_CASES = (
    {"waves": {2013: (124, 50, 500.0)}, "birth_year": None},
    {"waves": {2023: (2, 30, 500.0)}, "birth_year": None},
    {"waves": {2013: (123, 50, 500.0)}, "birth_year": None},
    {"waves": {2019: (2, 60, 500.0)}, "birth_year": None},
    {"waves": {2013: (125, 10, 500.0)}, "birth_year": 1950},
    {"waves": {2019: (0, 30, 500.0)}, "birth_year": None},
    {"waves": {2015: (998, 40, 500.0)}, "birth_year": None},
    {
        "waves": {2015: (0, 40, 500.0), 2017: (66, 40, 500.0)},
        "birth_year": None,
    },
)


@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(members=st.lists(_member(), min_size=1, max_size=4))
@example(members=[{"earnings_age": None, **case} for case in _CASES])
def test_every_outcome_is_the_law_s_on_that_person_alone(
    u2_inputs, host, members
):
    """For any added members, the derivation completes; the universe and
    the four counted-out sets partition the presence set; each person's
    outcome (counted out and why, or its record, and whether re-seeded)
    is section 16d's, computed from the law run on that person alone; the
    base population's records are unchanged; and the derivation is
    deterministic."""

    inputs = u2_inputs
    added = []
    for index, member in enumerate(members):
        person = ADDED - index
        earnings = ()
        if member["earnings_age"] is not None:
            earnings = ((1990, member["earnings_age"]),)
        inputs = _added(
            inputs,
            person,
            host,
            member["waves"],
            birth_year=member["birth_year"],
            earnings=earnings,
        )
        added.append(person)
    births = cohort.derive_u2_births(inputs)
    present = _presence(inputs)
    counted = [people for people in births.counted_out.values()]
    every = set().union(*counted)
    assert sum(len(people) for people in counted) == len(every)
    assert not every & births.universe
    assert every | births.universe == present
    base = cohort.derive_u2_births(u2_inputs)
    for person in base.universe:
        assert births.records[person] == base.records[person]
    for person in added:
        if person not in present:
            assert person not in every and person not in births.reseeded
            continue
        reason, record, reseeded = _expected(inputs, person)
        if reason is not None:
            assert person in births.counted_out[reason]
            assert person not in births.reseeded
            continue
        assert person in births.universe
        assert births.records[person] == record
        assert (person in births.reseeded) is reseeded
    again = cohort.derive_u2_births(inputs)
    assert dict(again.records) == dict(births.records)
    assert again.counted_out == births.counted_out
    assert again.reseeded == births.reseeded
