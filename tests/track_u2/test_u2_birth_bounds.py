"""The birth law's derived-age support and the d1724 count-out (16d).

INVENTED DATA - NOT A COMPARISON.  Every person, age, weight and year
here is invented: the seeded U2 generator's base population, its two
d1724 variants, and members these tests add to it as caller frames.

``career.derive_birth_years`` (read-only, section 14) asserts that a
birth year it derives from a seed coordinate (age code 2-125, ``seed year
- age``) lies in ``[DERIVED_BIRTH_MIN, DERIVED_BIRTH_MAX]`` (1889-2016).
The d1649 structural pass stopped on that assertion.  Max's ruling
d1724 (section 16d) counts out, before the law runs, each universe person
the seed clause would decide whose seed implies a year outside the
support, discloses each side's count, and changes nothing else.  These
tests hold, for every input:

* the universe and the two counted-out sets partition the presence set
  (every positive-weight, in-family person of any support wave);
* a person is counted out exactly when the law, run on that person
  alone, would stop on the support assertion, on the side the seed
  implies; every kept person's record is the one the law gives alone;
* no counted-out person can be in the 1946-55 cohort, since the seed is
  that person's only birth-year source and it lies outside 1889-2016;
* the annuitant extension never reaches the assertion, and never
  re-admits a counted-out person;
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

OUTSIDE = "seed_birth_years_outside_career_bounds"
AT_BOUNDS = "seed_birth_years_at_career_bounds"
BEFORE, AFTER = cohort.SEED_BIRTH_COUNTED_OUT
BASE_ID = 700_000
#: The members the two generator variants add (``invented.py``).
AFTER_2016 = (BASE_ID - 11, BASE_ID - 12)
BEFORE_1889 = (BASE_ID - 13,)
AT_1889, AT_2016 = BASE_ID - 14, BASE_ID - 15
#: Members these tests add as caller frames (ids no variant uses).
ADDED = BASE_ID - 100


@pytest.fixture(scope="module")
def outside(u2_inputs):
    return invented.invented_variant(u2_inputs, OUTSIDE)


@pytest.fixture(scope="module")
def at_bounds(u2_inputs):
    return invented.invented_variant(u2_inputs, AT_BOUNDS)


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


def _alone(inputs: cohort.U2Inputs, person: int, seed: bool = True):
    """The law run on ``person`` alone, from its earliest positive-weight
    in-family presence (or without a seed coordinate)."""

    history = inputs.marriage_history
    earnings = inputs.observed_earnings
    coordinates = None
    if seed:
        for wave in cohort.SUPPORT_WAVES:
            frame = inputs.anchors[wave]
            row = frame[
                frame["person_id"].eq(person)
                & frame["sequence"].between(1, 20)
                & frame["weight"].gt(0)
            ]
            if len(row):
                coordinates = pd.DataFrame(
                    {
                        "person_id": [person],
                        "year": [wave - 1],
                        "anchor_wave": [wave],
                        "age": [int(row["age"].iloc[0])],
                    }
                )
                break
    (record,) = career.derive_birth_years(
        history[history["person_id"].eq(person)],
        earnings[earnings["person_id"].eq(person)],
        seed_coordinates=coordinates,
        required_person_ids={person},
    )
    return record


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


# ---------------------------------------------------------------------------
# The counted-out persons and the boundary years
# ---------------------------------------------------------------------------
def test_the_d1649_failure_is_reproduced_without_the_count_out(
    outside, monkeypatch
):
    """With the count-out disabled, the invented variant stops the law
    on the support assertion, the failure category of the d1649 pass;
    with it, the derivation completes."""

    births = cohort.derive_u2_births(outside)
    assert set(births.universe) == _presence(outside) - {
        *AFTER_2016,
        *BEFORE_1889,
    }

    def disabled(seed, history, earnings):
        return seed, {side: frozenset() for side in (BEFORE, AFTER)}

    monkeypatch.setattr(cohort, "_count_out_seed_births", disabled)
    with pytest.raises(AssertionError, match=r"lies outside \[1889, 2016\]"):
        cohort.derive_u2_births(outside)


def test_seeds_after_2016_are_counted_out(outside):
    births = cohort.derive_u2_births(outside)
    assert births.counted_out[AFTER] == frozenset(AFTER_2016)
    for person in AFTER_2016:
        assert person not in births.universe
        assert person not in births.records
        assert births.birth_year(person) is None
        assert person not in set(births.seed["person_id"])


def test_a_seed_before_1889_is_counted_out(outside):
    births = cohort.derive_u2_births(outside)
    assert births.counted_out[BEFORE] == frozenset(BEFORE_1889)
    (person,) = BEFORE_1889
    assert person not in births.universe
    assert births.birth_year(person) is None


def test_seeds_at_1889_and_2016_stay_in(at_bounds):
    births = cohort.derive_u2_births(at_bounds)
    assert births.counted_out == {BEFORE: frozenset(), AFTER: frozenset()}
    for person, year in ((AT_1889, 1889), (AT_2016, 2016)):
        assert person in births.universe
        record = births.records[person]
        assert record.birth_year == year
        assert record.source is career.BirthSource.DERIVED_PROJECTION_AGE
    assert career.DERIVED_BIRTH_MIN == 1889
    assert career.DERIVED_BIRTH_MAX == 2016
    assert cohort.SEED_BIRTH_COUNTED_OUT == ("before_1889", "after_2016")


@pytest.mark.parametrize(
    "waves, side, year",
    [
        ({2013: (124, 50, 500.0)}, BEFORE, 1888),
        ({2013: (125, 50, 500.0)}, BEFORE, 1887),
        ({2013: (123, 50, 500.0)}, None, 1889),
        ({2019: (2, 30, 500.0)}, None, 2016),
        ({2021: (4, 30, 500.0)}, None, 2016),
        ({2021: (3, 30, 500.0)}, AFTER, 2017),
        ({2023: (2, 30, 500.0)}, AFTER, 2020),
        # The seed is the earliest positive-weight presence (section 3);
        # a later presence never replaces it.
        ({2013: (124, 50, 500.0), 2015: (75, 50, 500.0)}, BEFORE, 1888),
        ({2013: (124, 50, 0.0), 2015: (75, 50, 500.0)}, None, 1939),
    ],
)
def test_each_bound_and_side(u2_inputs, host, waves, side, year):
    inputs = _added(u2_inputs, ADDED, host, waves)
    births = cohort.derive_u2_births(inputs)
    if side is None:
        assert births.records[ADDED].birth_year == year
        assert all(ADDED not in out for out in births.counted_out.values())
    else:
        assert births.counted_out[side] == {ADDED}
        other = AFTER if side == BEFORE else BEFORE
        assert births.counted_out[other] == frozenset()
        wave, (age, _, _) = min(
            (w, value) for w, value in waves.items() if value[2] > 0
        )
        assert (wave - 1) - age == year


# ---------------------------------------------------------------------------
# Precedence, other codes and the target cohort
# ---------------------------------------------------------------------------
def test_a_history_or_earnings_year_keeps_its_precedence(u2_inputs, host):
    """The law's precedence is unchanged: a person whose marriage history
    or earnings give a birth year keeps it, whatever the seed implies,
    and is never counted out -- here a 1951 cohort member whose seed age
    implies 1887, and a person whose seed implies 2020."""

    inputs = _added(
        u2_inputs, ADDED, host, {2013: (125, 50, 500.0)}, birth_year=1951
    )
    inputs = _added(
        inputs,
        ADDED - 1,
        host,
        {2023: (2, 30, 500.0)},
        earnings=((1980, 20), (1982, 22)),
    )
    births = cohort.derive_u2_births(inputs)
    assert births.counted_out == {BEFORE: frozenset(), AFTER: frozenset()}
    exact = births.records[ADDED]
    assert (exact.birth_year, exact.source) == (
        1951,
        career.BirthSource.EXACT_MARRIAGE,
    )
    inferred = births.records[ADDED - 1]
    assert (inferred.birth_year, inferred.source) == (
        1960,
        career.BirthSource.INFERRED_PERIOD_AGE,
    )
    assert births.birth_year(ADDED) in cohort.ALL_BIRTH_YEARS


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
    assert births.counted_out == {BEFORE: frozenset(), AFTER: frozenset()}


def test_code_0_keeps_the_law_s_refusal(u2_inputs, host):
    """Code 0 (Inap.) on an in-family, positive-weight seed stays on the
    law's existing path: an unrecognized seed-age code refuses."""

    inputs = _added(u2_inputs, ADDED, host, {2023: (0, 30, 500.0)})
    with pytest.raises(ValueError, match="unrecognized PSID seed-age codes"):
        cohort.derive_u2_births(inputs)


def test_no_counted_out_person_can_be_in_the_target_cohort(outside):
    """Each counted-out person has no birth-year source but the seed (the
    law, run without it, leaves the person unresolved), and the seed's
    year lies outside 1889-2016, which contains 1946-55."""

    births = cohort.derive_u2_births(outside)
    assert career.DERIVED_BIRTH_MIN < min(cohort.ALL_BIRTH_YEARS)
    assert max(cohort.ALL_BIRTH_YEARS) < career.DERIVED_BIRTH_MAX
    counted = births.counted_out[BEFORE] | births.counted_out[AFTER]
    assert counted == {*AFTER_2016, *BEFORE_1889}
    for person in counted:
        alone = _alone(outside, person, seed=False)
        assert alone.source is career.BirthSource.UNRESOLVED
    for built in _builds(outside, births).values():
        assert not counted & set(built.observations["person_id"])
        assert not counted & set(built.dispositions["person_id"])


# ---------------------------------------------------------------------------
# The annuitant extension
# ---------------------------------------------------------------------------
def test_the_extension_cannot_reach_the_bound(u2_inputs, host):
    """The extension seeds only rows whose implied year the law supports
    (code 999 kept): a zero-weight reference person seen at 124 in 2013
    is seeded by the 2015 presence instead, and one seen only at 3 in
    2021 gets no record; neither stops the law."""

    inputs = _added(
        u2_inputs,
        ADDED,
        host,
        {2013: (124, 20, 0.0), 2015: (70, 20, 0.0)},
    )
    inputs = _added(inputs, ADDED - 1, host, {2021: (3, 10, 0.0)})
    births = cohort.derive_u2_births(inputs)
    assert ADDED not in births.universe and ADDED - 1 not in births.universe
    assert births.records[ADDED].birth_year == 2014 - 70
    assert ADDED - 1 not in births.records
    assert births.counted_out == {BEFORE: frozenset(), AFTER: frozenset()}


def test_a_counted_out_person_never_joins_the_extension(u2_inputs, host):
    """A counted-out person had a positive-weight presence, so is not
    outside the universe: the extension, which would have seeded this
    code-20 person from the zero-weight 2015 presence, leaves it out."""

    inputs = _added(
        u2_inputs,
        ADDED,
        host,
        {2013: (124, 20, 500.0), 2015: (70, 20, 0.0)},
    )
    births = cohort.derive_u2_births(inputs)
    assert births.counted_out[BEFORE] == {ADDED}
    assert ADDED not in births.records
    assert births.birth_year(ADDED) is None


# ---------------------------------------------------------------------------
# Disclosure, and nothing else changes
# ---------------------------------------------------------------------------
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


def test_the_two_counts_are_disclosed_in_every_row(
    u2_inputs, outside, at_bounds
):
    for inputs, counts in (
        (u2_inputs, {BEFORE: 0, AFTER: 0}),
        (outside, {BEFORE: 1, AFTER: 2}),
        (at_bounds, {BEFORE: 0, AFTER: 0}),
    ):
        births = cohort.derive_u2_births(inputs)
        for built in _builds(inputs, births).values():
            assert built.diagnostics["n_seed_birth_year_counted_out"] == counts
            summary = cohort.structural_summary(built)
            assert summary["n_seed_birth_year_counted_out"] == counts
            assert list(summary["n_seed_birth_year_counted_out"]) == [
                "before_1889",
                "after_2016",
            ]


def test_the_count_out_changes_nothing_else(u2_inputs, outside):
    """The variant adds only counted-out members: the births, every row's
    observations, dispositions, design frame, income rows and every other
    count equal the base population's."""

    base = cohort.derive_u2_births(u2_inputs)
    births = cohort.derive_u2_births(outside)
    assert births.universe == base.universe
    assert dict(births.records) == dict(base.records)
    pd.testing.assert_frame_equal(births.seed, base.seed)
    before, after = _builds(u2_inputs, base), _builds(outside, births)
    for row in cohort.ROWS:
        pd.testing.assert_frame_equal(
            after[row].observations, before[row].observations
        )
        pd.testing.assert_frame_equal(
            after[row].dispositions, before[row].dispositions
        )
        pd.testing.assert_frame_equal(
            cohort.design_frame(outside, after[row].spec),
            cohort.design_frame(u2_inputs, before[row].spec),
        )
        changed = {"n_seed_birth_year_counted_out", "births_inputs_sha256"}
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
        cohort.income_rows(after["U0"], outside),
        cohort.income_rows(before["U0"], u2_inputs),
    )


def test_the_boundary_members_change_only_the_universe_counts(
    u2_inputs, at_bounds
):
    base = cohort.derive_u2_births(u2_inputs)
    births = cohort.derive_u2_births(at_bounds)
    assert births.universe == base.universe | {AT_1889, AT_2016}
    before, after = _builds(u2_inputs, base), _builds(at_bounds, births)
    for row in cohort.ROWS:
        pd.testing.assert_frame_equal(
            after[row].observations, before[row].observations
        )
        pd.testing.assert_frame_equal(
            after[row].dispositions, before[row].dispositions
        )
        for key in ("n_universe", "n_outside_birth_years"):
            assert (
                after[row].diagnostics[key] == before[row].diagnostics[key] + 2
            )
        assert after[row].diagnostics["n_target_birth_year"] == (
            before[row].diagnostics["n_target_birth_year"]
        )


# ---------------------------------------------------------------------------
# Property: the count-out is exactly where the law would stop
# ---------------------------------------------------------------------------
#: Every age code the loader admits for an in-family person but 0, whose
#: refusal the law keeps (tested above).
_ANY_AGE = st.one_of(st.integers(1, 125), st.just(999))
_RELATIONSHIPS = st.sampled_from((10, 20, 30, 50, 60))
#: Mostly positive, so the first row is mostly the seed.
_WEIGHTS = st.sampled_from((500.0, 500.0, 500.0, 0.0))


@st.composite
def _first_row(draw) -> tuple[int, int]:
    """A (wave, age code) drawn mostly near either end of the support:
    the oldest codes in 2013 (1887-1890) or young children in 2019-2023
    (2016-2021, code 1 included)."""

    kind = draw(st.sampled_from(("low", "low", "high", "high", "any")))
    if kind == "low":
        return 2013, draw(st.integers(122, 125))
    if kind == "high":
        wave = draw(st.sampled_from((2019, 2021, 2023)))
        return wave, draw(st.integers(1, 6))
    return draw(st.sampled_from(cohort.SUPPORT_WAVES)), draw(_ANY_AGE)


@st.composite
def _member(draw) -> dict:
    """A member whose first row is drawn by :func:`_first_row`, plus up to
    two later rows of any code; any relationship and weight; mostly
    seed-only (no history or earnings year)."""

    first, age = draw(_first_row())
    rows = {first: (age, draw(_RELATIONSHIPS), draw(_WEIGHTS))}
    later = [wave for wave in cohort.SUPPORT_WAVES if wave > first]
    if later:
        for wave in draw(
            st.lists(st.sampled_from(later), unique=True, max_size=2)
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
)


@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(members=st.lists(_member(), min_size=1, max_size=4))
@example(
    members=[{"earnings_age": None, **case} for case in _CASES]  # one of each
)
def test_the_count_out_is_exactly_where_the_law_would_stop(
    u2_inputs, host, members
):
    """For any added members: the universe and the two counted-out sets
    partition the presence set; a person is counted out exactly when the
    law run on that person alone stops on the support assertion, on the
    side the seed implies; every kept person's record is the law's alone;
    the base population's records are unchanged; and the derivation is
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
    counted = births.counted_out[BEFORE] | births.counted_out[AFTER]
    assert not births.counted_out[BEFORE] & births.counted_out[AFTER]
    assert not counted & births.universe
    assert counted | births.universe == present
    base = cohort.derive_u2_births(u2_inputs)
    for person in base.universe:
        assert births.records[person] == base.records[person]
    for person in added:
        if person not in present:
            assert person not in counted
            continue
        try:
            alone = _alone(inputs, person)
        except AssertionError as stop:
            assert "lies outside" in str(stop)
            year = int(str(stop).split()[3])
            side = BEFORE if year < career.DERIVED_BIRTH_MIN else AFTER
            assert person in births.counted_out[side]
            assert _alone(inputs, person, seed=False).source is (
                career.BirthSource.UNRESOLVED
            )
            continue
        assert person in births.universe
        assert births.records[person] == alone
    again = cohort.derive_u2_births(inputs)
    assert dict(again.records) == dict(births.records)
    assert again.counted_out == births.counted_out
