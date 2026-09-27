"""Cos d430's own-receipt sensitivity on INVENTED data.

Max ruled d430 on 2026-09-26: section 4c item 1's reading (receipt of an
unknown or "other" type, or a combination code, counts as own receipt,
before the year of attaining 62 too) stays the scored reading, and a
pre-registered, unscored sensitivity reads such receipt before 62 as
neither own receipt nor non-receipt.  No PSID file is read: the hand cases
are invented observations, the cohorts ``invented_psid``'s frames and the
parameters ``invented.invented_parameters``'s.

Invariants (each a property test here, over histories or invented
cohorts Hypothesis draws):

* **off is identical**: the default reading is the scored reading, and
  classifying, building a cohort or running the pipeline with it given
  explicitly gives the same result as without it; the registered rows
  MS0-MS6 are the same with and without the sensitivity;
* **direction** (checked in ``classify_own_record`` before it was
  asserted): a record the sensitivity reading keeps has a window year no
  earlier than under the scored reading, and the sensitivity reading never
  creates a record the scored reading lacks;
* **reach**: a history with no own receipt year before 62 that names no
  worker's benefit, or whose first own receipt names one, is classified
  the same under both readings; in a cohort, such a person's record and
  every death-basis record are the same, the universe is the same, and the
  sensitivity's records and links are among the scored reading's;
* **bound**: a person outside the reclassification's resting set has the
  same receipt under both readings for every option, so each cell's change
  is at most its resting share, and equals the share moved in less the
  share moved out;
* **differential**: the sensitivity's cells equal a direct weighted
  recomputation from its evaluation rows, and its scored-reading shares
  equal MS0's tabulated cells.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.data import social_security_receipt as ssr
from populace_dynamics.min_benefit_track_m import (
    careers,
    cohort,
    evaluation,
    invented,
    invented_psid,
    pipeline,
    specification,
    tabulation,
)
from populace_dynamics.min_benefit_track_m import policy as pol
from populace_dynamics.min_benefit_track_m.cohort import (
    AUXILIARY,
    NONE,
    OWN,
    ReceiptObservation,
)

SCORED = pol.OWN_RECEIPT_UNKNOWN_OR_OTHER_IS_OWN
SENSITIVITY = pol.OWN_RECEIPT_PRE62_UNKNOWN_OR_OTHER_UNOBSERVED
ID = pol.OWN_RECEIPT_SENSITIVITY_ID
PARAMETERS, COLA = invented.invented_parameters()
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)


def _obs(year: int, status: str, *types: str) -> ReceiptObservation:
    return ReceiptObservation(year, status, frozenset(types))


def _combination(year: int, source: str = "individual") -> ReceiptObservation:
    return cohort.observation(
        year, receipt=True, types={}, combination=True, source=source
    )


def _whether_only_yes(year: int) -> ReceiptObservation:
    return cohort.observation(
        year, receipt=True, types={}, source="year_before_last"
    )


def _other_only(year: int) -> ReceiptObservation:
    return cohort.observation(
        year,
        receipt=True,
        types={name: name == "other" for name in ssr.SS_TYPES},
    )


def _both(history, birth):
    return (
        cohort.classify_own_record(history, birth),
        cohort.classify_own_record(
            history, birth, own_receipt_reading=SENSITIVITY
        ),
    )


# ---------------------------------------------------------------------------
# Which observations the sensitivity reads as unobserved
# ---------------------------------------------------------------------------
def test_unknown_or_other_own_receipt_names_no_workers_benefit():
    assert cohort.unknown_or_other_own_receipt(_combination(2006))
    assert cohort.unknown_or_other_own_receipt(_whether_only_yes(2009))
    assert cohort.unknown_or_other_own_receipt(_other_only(2006))
    # a survivor mention with another item unknown is own receipt only
    # because of the unknown item
    flags = dict.fromkeys(ssr.SS_TYPES, False)
    flags.update(survivor=True, disability=None)
    partial = cohort.observation(2006, receipt=True, types=flags)
    assert partial.status == OWN
    assert cohort.unknown_or_other_own_receipt(partial)
    # a worker's benefit named, whatever else is unknown: not reached
    flags = dict.fromkeys(ssr.SS_TYPES, None)
    flags.update(retirement=True)
    assert not cohort.unknown_or_other_own_receipt(
        cohort.observation(2006, receipt=True, types=flags)
    )
    assert not cohort.unknown_or_other_own_receipt(
        _obs(2006, OWN, "disability", "other")
    )
    assert not cohort.unknown_or_other_own_receipt(
        _obs(2006, AUXILIARY, "survivor")
    )
    assert not cohort.unknown_or_other_own_receipt(_obs(2006, NONE))


def test_the_view_drops_only_such_years_before_62():
    history = {
        2004: _obs(2004, NONE),
        2006: _combination(2006),  # 59: dropped
        2007: _whether_only_yes(2007),  # 60: dropped
        2008: _obs(2008, OWN, "disability"),  # names a worker's: kept
        2009: _other_only(2009),  # 62: kept
        2010: _combination(2010),  # 63: kept
    }
    assert cohort.own_receipt_view(history, 1947) == history
    assert cohort.own_receipt_view(history, 1947, SCORED) == history
    assert set(cohort.own_receipt_view(history, 1947, SENSITIVITY)) == {
        2004,
        2008,
        2009,
        2010,
    }
    with pytest.raises(ValueError, match="own_receipt_reading"):
        cohort.own_receipt_view(history, 1947, "neither")
    with pytest.raises(ValueError, match="own_receipt_reading"):
        cohort.classify_own_record(
            history, 1947, own_receipt_reading="neither"
        )


# ---------------------------------------------------------------------------
# Hand cases (INVENTED observations)
# ---------------------------------------------------------------------------
def test_a_survivors_benefit_at_60_reported_as_a_combination():
    """The case the independent review of 2026-09-25 named.  Born 1950
    (62 in 2012), no receipt in 2008, a combination code in 2010 (a
    survivor's benefit at 60) and a retirement benefit from 2012."""

    history = {
        2008: _obs(2008, NONE),
        2010: _combination(2010),
        2012: _obs(2012, OWN, "retirement"),
    }
    scored, alternative = _both(history, 1950)
    assert (scored.basis, scored.window_year, scored.onset_year) == (
        "disability",
        2009,
        2008,
    )
    assert (alternative.basis, alternative.window_year) == ("old_age", 2012)
    assert alternative.onset_year is None
    assert alternative.window_year > scored.window_year


def test_a_one_member_familys_whether_only_yes_before_62():
    """Born 1949 (62 in 2011): no receipt in 2008 and 2010, a one-member
    family's whether-only "yes" for 2009, retirement from 2012."""

    history = {
        2008: _obs(2008, NONE),
        2009: _whether_only_yes(2009),
        2010: _obs(2010, NONE),
        2012: _obs(2012, OWN, "retirement"),
    }
    scored, alternative = _both(history, 1949)
    assert (scored.basis, scored.window_year) == ("disability", 2009)
    assert scored.last_without_year == 2008
    assert (alternative.basis, alternative.window_year) == ("old_age", 2011)
    assert alternative.last_without_year == 2010


def test_an_other_mention_before_62_with_every_type_item_known():
    """The part of section 4c item 1 the review of 2026-09-25 left
    unsized: an "other" mention with every item known is own receipt."""

    history = {
        2004: _obs(2004, NONE),
        2006: _other_only(2006),
        2008: _obs(2008, OWN, "retirement"),
    }
    scored, alternative = _both(history, 1946)
    assert history[2006].status == OWN and not history[2006].unknown_types
    assert (scored.basis, scored.window_year) == ("disability", 2005)
    assert (alternative.basis, alternative.window_year) == ("old_age", 2008)


def test_a_record_resting_on_such_receipt_alone_disappears():
    history = {2004: _obs(2004, NONE), 2006: _combination(2006)}
    scored, alternative = _both(history, 1950)
    assert scored is not None and scored.basis == "disability"
    assert alternative is None


def test_rule_3_records_are_reread_too():
    """First observation 2005, a whether-only "yes" at 57: under the
    scored reading a disability-origin record with an unresolved
    entitlement placed out of both windows (2003); under the sensitivity
    the retirement from 2010 (62) is the first own receipt, old age."""

    history = {
        2005: _whether_only_yes(2005),
        2010: _obs(2010, OWN, "retirement"),
    }
    scored, alternative = _both(history, 1948)
    assert scored.resolution == "rule3_age_rule"
    assert (scored.basis, scored.window_year) == ("disability", 2003)
    assert alternative.resolution == "rule3_age_rule"
    assert (alternative.basis, alternative.window_year) == ("old_age", 2010)


def test_a_reached_record_can_keep_its_basis_window_and_onset():
    """Born 1950: no receipt in 2004, a combination code in 2006 (56) and a
    disability benefit from 2008.  The sensitivity moves the first own
    receipt from 2006 to 2008, but the last year without own receipt is
    2004 under both readings, so the record keeps its basis, window year
    and onset: the pipeline, which compares the records the evaluation
    reads (they carry no first own receipt), finds nothing differs.  (The
    exhaustive check in ``EV/track-m-5-build-20260926/direction_exhaustive
    .py`` finds 66,348 such histories among 1,835,008.)"""

    history = {
        2004: _obs(2004, NONE),
        2006: _combination(2006),
        2008: _obs(2008, OWN, "disability"),
    }
    scored, alternative = _both(history, 1950)
    assert (scored.first_own_year, alternative.first_own_year) == (
        2006,
        2008,
    )
    for name in ("basis", "window_year", "onset_year", "unresolved"):
        assert getattr(scored, name) == getattr(alternative, name), name
    assert (scored.basis, scored.window_year, scored.onset_year) == (
        "disability",
        2005,
        2004,
    )


def test_records_the_sensitivity_does_not_reach():
    # the first own receipt names a disability benefit: an "other" year
    # and a combination code after it, before 62, change nothing
    disability_first = {
        2002: _obs(2002, NONE),
        2004: _obs(2004, OWN, "disability"),
        2006: _other_only(2006),
        2008: _combination(2008),
    }
    assert _both(disability_first, 1950)[0] == _both(disability_first, 1950)[1]
    # such receipt at or after 62 is read the same under both
    at_62 = {2010: _obs(2010, NONE), 2012: _combination(2012)}
    assert _both(at_62, 1950)[0] == _both(at_62, 1950)[1]


# ---------------------------------------------------------------------------
# Properties over histories Hypothesis draws
# ---------------------------------------------------------------------------
_YEARS = tuple(range(1983, 2023))
_TYPE_VALUES = (True, False, None)


@st.composite
def _histories(draw):
    """Observations through :func:`cohort.observation`, as M3's frames
    give them: type items True, False or unknown, combination codes and
    whether-only "yes" answers, with births that put years on both sides
    of 62."""

    birth = draw(st.integers(min_value=1925, max_value=1965))
    years = draw(
        st.lists(st.sampled_from(_YEARS), min_size=1, max_size=12, unique=True)
    )
    out = {}
    for year in sorted(years):
        kind = draw(
            st.sampled_from(("none", "typed", "combination", "whether_only"))
        )
        if kind == "none":
            out[year] = cohort.observation(year, receipt=False)
        elif kind == "combination":
            out[year] = _combination(year)
        elif kind == "whether_only":
            out[year] = _whether_only_yes(year)
        else:
            out[year] = cohort.observation(
                year,
                receipt=True,
                types={
                    name: draw(st.sampled_from(_TYPE_VALUES))
                    for name in ssr.SS_TYPES
                },
            )
    return birth, out


@st.composite
def _histories_with_a_reached_first_receipt(draw):
    """:func:`_histories` whose first own receipt is before 62 and names no
    worker's benefit (the records the sensitivity reaches), drawn rather
    than filtered for."""

    birth, history = draw(_histories())
    attains_62 = birth + 62
    own = [y for y, o in history.items() if o.status == OWN]
    first = min(own) if own else None
    choices = [
        y for y in _YEARS if y < attains_62 and (first is None or y <= first)
    ]
    if not choices:
        birth = 1960
        attains_62 = 2022
        choices = [y for y in _YEARS if first is None or y <= first] or [1983]
    year = draw(st.sampled_from(choices))
    history = {
        y: o for y, o in history.items() if not (y < year and o.status == OWN)
    }
    history[year] = draw(
        st.sampled_from(
            (_combination(year), _whether_only_yes(year), _other_only(year))
        )
    )
    return birth, history


def _reached(history, birth) -> bool:
    return any(
        year < birth + 62 and cohort.unknown_or_other_own_receipt(obs)
        for year, obs in history.items()
    )


def _classify_before_d430(history, birth_year):
    """``cohort.classify_own_record`` as it stood before d430 (the Track
    M-4 head ``672e6770``), copied verbatim but for its docstring and the
    module constants' names: the reference the default reading must equal.
    """

    observations = dict(history)
    birth = int(birth_year)
    own_years = sorted(y for y, o in observations.items() if o.status == OWN)
    if not own_years:
        return None
    first = own_years[0]
    first_obs = observations[first]
    attains_62 = birth + 62
    disability = "disability" in first_obs.types or first < attains_62
    basis = cohort.BASIS_DISABILITY if disability else cohort.BASIS_OLD_AGE
    retirement_type = (
        basis == cohort.BASIS_OLD_AGE or "retirement" in first_obs.types
    )
    without = [
        y for y, o in observations.items() if y < first and o.status != OWN
    ]
    last = max(without) if without else None
    rule3 = {}
    if last is not None:
        window = (
            max(attains_62, last + 1)
            if basis == cohort.BASIS_OLD_AGE
            else last + 1
        )
        resolution, unresolved = "rule2_observed_boundary", False
    elif first < cohort.POLICY_YEARS[0]:
        window = attains_62 if basis == cohort.BASIS_OLD_AGE else first
        resolution = "receipt_in_first_observation_before_2004"
        unresolved = False
    else:
        in_2004 = birth >= cohort.RULE3_BIRTH_YEAR[2004] and retirement_type
        in_2007 = (
            in_2004
            and first >= 2007
            and birth >= cohort.RULE3_BIRTH_YEAR[2007]
        )
        rule3 = {2004: in_2004, 2007: in_2007}
        if basis == cohort.BASIS_OLD_AGE:
            window = attains_62
        elif in_2007:
            window = 2007
        elif in_2004:
            window = 2004
        else:
            window = cohort.POLICY_YEARS[0] - 1
        resolution, unresolved = "rule3_age_rule", True
    onset = window - 1 if basis == cohort.BASIS_DISABILITY else None
    return cohort.OwnRecordClass(
        birth_year=birth,
        basis=basis,
        first_own_year=first,
        last_without_year=last,
        window_year=window,
        onset_year=onset,
        resolution=resolution,
        unresolved=unresolved,
        retirement_type=retirement_type,
        first_types=first_obs.types,
        rule3_in_window=rule3,
        last_without_source=(
            None if last is None else observations[last].source
        ),
    )


@settings(max_examples=500, deadline=None)
@given(st.one_of(_histories(), _histories_with_a_reached_first_receipt()))
def test_property_the_default_reading_is_the_scored_reading(case):
    """Off is identical: the default reading (and the scored reading named
    explicitly) classifies every history as the build before d430 did
    (differential against its implementation, :func:`_classify_before_d430`),
    and the view it reads is the history itself."""

    birth, history = case
    assert cohort.own_receipt_view(history, birth) == history
    default = cohort.classify_own_record(history, birth)
    explicit = cohort.classify_own_record(
        history, birth, own_receipt_reading=SCORED
    )
    assert default == explicit == _classify_before_d430(history, birth)


@settings(max_examples=600, deadline=None)
@given(st.one_of(_histories(), _histories_with_a_reached_first_receipt()))
def test_property_the_scored_reading_never_gives_a_later_window_year(case):
    """Checked in ``classify_own_record`` before it was asserted: dropping
    an own year before 62 that names no worker's benefit changes nothing
    unless it is the first own receipt *F*; then *F* moves later and the
    last year without own receipt before it, *L*, can only move later, and
    every branch (rule 2, a first observation before 2004, rule 3) gives a
    window year at least the scored reading's."""

    birth, history = case
    scored, alternative = _both(history, birth)
    if alternative is not None:
        assert scored is not None, "the sensitivity created a record"
        assert alternative.window_year >= scored.window_year
        assert alternative.first_own_year >= scored.first_own_year


@settings(max_examples=600, deadline=None)
@given(_histories())
def test_property_records_without_such_receipt_are_unaffected(case):
    birth, history = case
    scored, alternative = _both(history, birth)
    if not _reached(history, birth):
        assert scored == alternative
    # the stronger form: only a first own receipt of that kind matters
    if scored is None or not (
        scored.first_own_year < birth + 62
        and cohort.unknown_or_other_own_receipt(history[scored.first_own_year])
    ):
        assert scored == alternative


@settings(max_examples=300, deadline=None)
@given(_histories_with_a_reached_first_receipt())
def test_property_a_reached_record_is_reread_as_its_history_less_those_years(
    case,
):
    """Differential: the sensitivity equals the scored reading applied to
    the history with those years removed by hand."""

    birth, history = case
    by_hand = {
        year: obs
        for year, obs in history.items()
        if not (year < birth + 62 and cohort.unknown_or_other_own_receipt(obs))
    }
    assert cohort.classify_own_record(
        history, birth, own_receipt_reading=SENSITIVITY
    ) == cohort.classify_own_record(by_hand, birth)


# ---------------------------------------------------------------------------
# The cohort (INVENTED PSID-shaped frames)
# ---------------------------------------------------------------------------
_COHORT_SETTINGS = settings(
    max_examples=8,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


def _frames(seed: int, share: float, n: int = 24):
    return invented_psid.invented_cohort_inputs(
        seed=seed, n_family_units=n, unknown_or_other_before_62=share
    )


def test_the_invented_draw_is_unchanged_without_the_knob():
    base = invented_psid.invented_cohort_inputs(seed=5, n_family_units=40)
    off = _frames(5, 0.0, 40)
    for name in (
        "individual_receipt",
        "family_level_receipt",
        "prior_year_labor",
    ):
        pd.testing.assert_frame_equal(getattr(base, name), getattr(off, name))
    assert base.provenance == off.provenance
    with pytest.raises(ValueError, match="in \\[0, 1\\]"):
        _frames(5, 1.5)


@_COHORT_SETTINGS
@given(
    st.integers(min_value=0, max_value=10_000),
    st.sampled_from((0.0, 0.4, 1.0)),
)
def test_property_the_cohort_is_unchanged_under_the_default(seed, share):
    frames = _frames(seed, share)
    default = cohort.build_cohort(frames)
    explicit = cohort.build_cohort(frames, own_receipt_reading=SCORED)
    for name in ("persons", "records", "links", "design"):
        pd.testing.assert_frame_equal(
            getattr(default, name), getattr(explicit, name)
        )
    assert default.diagnostics == explicit.diagnostics
    assert default.own_receipt_reading == SCORED


@_COHORT_SETTINGS
@given(
    st.integers(min_value=0, max_value=10_000),
    st.sampled_from((0.0, 0.4, 1.0)),
)
def test_property_the_cohort_reaches_only_such_records(seed, share):
    frames = _frames(seed, share)
    scored = cohort.build_cohort(frames)
    other = cohort.build_cohort(frames, own_receipt_reading=SENSITIVITY)
    assert other.own_receipt_reading == SENSITIVITY
    # the universe is the same
    universe = [
        "person_id",
        "family_unit_id",
        "weight",
        "sex",
        "stratum",
        "cluster",
        "birth_year",
        "role",
    ]
    pd.testing.assert_frame_equal(
        scored.persons[universe], other.persons[universe]
    )
    pd.testing.assert_frame_equal(scored.design, other.design)
    # records and links under the sensitivity are among the scored
    # reading's
    left = scored.records.set_index("record_id")
    right = other.records.set_index("record_id")
    assert set(right.index) <= set(left.index)
    links = {
        (row.person_id, row.kind, row.record_id)
        for row in scored.links.itertuples(index=False)
    }
    assert {
        (row.person_id, row.kind, row.record_id)
        for row in other.links.itertuples(index=False)
    } <= links
    # a record whose worker has no own receipt before 62 that names no
    # worker's benefit is the same record, and so is every death-basis
    # record's worker who has none either
    columns = ["basis", "window_year", "onset_year", "death_year"]

    def reached(key) -> bool:
        pid = int(left.loc[key, "person_id"])
        birth = int(left.loc[key, "birth_year"])
        return _reached(scored.histories.get(pid, {}), birth)

    for key in right.index:
        if not reached(key):
            assert left.loc[key, columns].equals(right.loc[key, columns]), key
    # a record or a link only the scored reading has rests on such receipt
    # of its worker (the view drops nothing else)
    for key in set(left.index) - set(right.index):
        assert reached(key), key
    lost = links - {
        (row.person_id, row.kind, row.record_id)
        for row in other.links.itertuples(index=False)
    }
    for _, _, key in lost:
        assert reached(key), key
        if right.loc[key, "basis"] != cohort.BASIS_DEATH and (
            left.loc[key, "basis"] != cohort.BASIS_DEATH
        ):
            assert (
                right.loc[key, "window_year"] >= left.loc[key, "window_year"]
            )
    if share == 0.0:
        pd.testing.assert_frame_equal(scored.records, other.records)
        pd.testing.assert_frame_equal(scored.links, other.links)


# ---------------------------------------------------------------------------
# The pipeline: MS0 under both readings (INVENTED parameters)
# ---------------------------------------------------------------------------
def _inputs(frames, reading):
    built = cohort.build_cohort(frames, own_receipt_reading=reading)
    return careers.build_track_m_inputs(
        built,
        earnings=frames.earnings,
        prior_year=frames.prior_year_labor,
        params=PARAMETERS.params,
        cola_rates=COLA,
        provenance_kind=evaluation.INVENTED,
    )


@pytest.fixture(scope="module")
def pair():
    frames = _frames(11, 0.6, 60)
    return _inputs(frames, SCORED), _inputs(frames, SENSITIVITY)


@pytest.fixture(scope="module")
def result(pair):
    scored, other = pair
    return pipeline.run_track_m(
        scored,
        PARAMETERS,
        data_provenance="invented",
        own_receipt_sensitivity=other,
    )


#: SHA-256 digests of the scored path on two INVENTED cohorts
#: (``invented_psid``'s default draw), printed by
#: ``EV/track-m-5-build-20260926/scored_path_pins.py`` at the build before
#: d430 (``672e6770``, the Track M-4 head), with the serialization of
#: :func:`_frame_digest`: the M4 cohort's persons, records and links, and
#: each registered row's receipt flags, basis and exposure.
_PINS_BEFORE_D430 = {
    (5, 40): {
        "persons": "e3e7e2df727fecec7c4f59dde14c48c89be8dcd010e5d7861ea3da113ccd5a3e",
        "records": "3b0512b15a08fde81538800bbf3d32748356589eae046bfaa40617baabc7a201",
        "links": "51cee8e169097ad451cc4e659b5b62a9faa9c7494b27fea70d53171c1e0b2e54",
        "MS0": "c49b7bf73540a1285a9bb23e2df5b5205a497b2bd4017aa0e15aeb9373d244a7",
        "MS1": "ee1385e6565e26db009d64b1196768e253b86b7732f6de508cd5e5220f809e21",
        "MS2": "ae423d29868d4602ad24b793092ab0d41a051f3def3bf6c09f317aa118091740",
        "MS3": "ce35718c44334dd867cbff87f03caab37c6e1adc0cadad678f8dd3975d5dd8fd",
        "MS4": "c49b7bf73540a1285a9bb23e2df5b5205a497b2bd4017aa0e15aeb9373d244a7",
        "MS5": "6ba0b41b4af85e3eef9fea7a47190686e85067570314f3f55991395977d381dc",
        "MS6": "95d1a5a51e03812bd0b28d066f5b8038fc3255e06e9378745940c654abeaad72",
    },
    (11, 60): {
        "persons": "13d89ef707dddf8302c6aade4227be06b42c90596c98bccc550ef967e0bdafa1",
        "records": "43b5cad7d1b466738fba2eb98fea5630a4d7ba12791e4c2bf6318e71ddc60faa",
        "links": "3228ed54265f043600f4a85eeb40784fcbaa22a1b17acaab350ff82dd1b26fec",
        "MS0": "70926a0af6ea89c959a4a66bf90f8170d5085aec0afd2852a755012718dd5fbe",
        "MS1": "9dc63e1dcbeb494abe9fe86c00ef4552e1a2d3ad4b8bddb1720252ddb84864ce",
        "MS2": "e955cb47cf8f74ec135424927878eb500d4b2755a36e6ddb97a830fcce16bc08",
        "MS3": "0b9a7084e057374a8e06dce78f4a99bf805fc0a7d08da149ca26fe9a67abff50",
        "MS4": "70926a0af6ea89c959a4a66bf90f8170d5085aec0afd2852a755012718dd5fbe",
        "MS5": "2a6636dbd67eb814fe2ff95b69a10618d565c27b40f2660fd332c6bda9c0f53e",
        "MS6": "70926a0af6ea89c959a4a66bf90f8170d5085aec0afd2852a755012718dd5fbe",
    },
}
_ROW_COLUMNS = [
    "person_id",
    "receives_2",
    "receives_3",
    "receives_4",
    "receives_5",
    "basis",
    "exposed",
]


def _cell(value):
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if math.isnan(value):
            return None
        if float(value).is_integer():
            return int(value)
        return repr(float(value))
    return str(value)


def _frame_digest(frame: pd.DataFrame) -> str:
    """A canonical digest of a frame's columns and cells, independent of
    pandas' dtype choices (an integral float and an int agree)."""

    payload = {
        "columns": [str(c) for c in frame.columns],
        "rows": [
            [_cell(v) for v in row]
            for row in frame.itertuples(index=False, name=None)
        ],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("seed, n", sorted(_PINS_BEFORE_D430))
def test_the_scored_path_is_pinned_to_the_build_before_d430(seed, n):
    """Off is identical, against the build before d430: under the default
    reading the M4 cohort and every registered row's receipt flags equal
    the digests ``672e6770`` gives (differential across builds)."""

    pins = _PINS_BEFORE_D430[(seed, n)]
    frames = invented_psid.invented_cohort_inputs(seed=seed, n_family_units=n)
    built = cohort.build_cohort(frames)
    for name in ("persons", "records", "links"):
        assert _frame_digest(getattr(built, name)) == pins[name], name
    records = _inputs(frames, SCORED)
    for row in pol.REGISTERED_ROWS:
        rows = evaluation.evaluate(
            records, pol.policy_for_row(row), PARAMETERS
        ).rows
        assert _frame_digest(rows[_ROW_COLUMNS]) == pins[row], row


@settings(max_examples=4, deadline=None)
@given(
    st.integers(min_value=0, max_value=10_000),
    st.sampled_from((0.0, 0.5, 1.0)),
)
def test_property_the_rows_do_not_depend_on_the_sensitivity(seed, share):
    """Off is identical in the pipeline: MS0-MS6 are the same with the
    sensitivity passed and without it, whatever the invented draw."""

    frames = _frames(seed, share, 16)
    scored = _inputs(frames, SCORED)
    other = _inputs(frames, SENSITIVITY)
    with_it = pipeline.run_track_m(
        scored,
        PARAMETERS,
        data_provenance="invented",
        own_receipt_sensitivity=other,
    )
    without = pipeline.run_track_m(
        scored, PARAMETERS, data_provenance="invented"
    )
    assert json.dumps(with_it["rows"], allow_nan=False) == json.dumps(
        without["rows"], allow_nan=False
    )
    assert set(with_it) - set(without) == {"sensitivities"}


def test_the_records_carry_their_reading(pair):
    scored, other = pair
    assert scored.own_receipt_reading == SCORED
    assert other.own_receipt_reading == SENSITIVITY
    with pytest.raises(ValueError, match="own_receipt_reading"):
        dataclasses.replace(scored, own_receipt_reading="neither")


def test_the_rows_are_the_same_with_and_without_the_sensitivity(pair, result):
    scored, _ = pair
    without = pipeline.run_track_m(
        scored, PARAMETERS, data_provenance="invented"
    )
    assert "sensitivities" not in without
    assert json.dumps(without["rows"], allow_nan=False) == json.dumps(
        result["rows"], allow_nan=False
    )
    for key in set(without) - {"rows"}:
        assert without[key] == result[key], key


def test_the_sensitivity_is_published_unscored(result):
    entry = result["sensitivities"][ID]
    assert entry["registered"] == pol.SENSITIVITIES[ID]
    assert entry["scored"] is False
    table = entry["tabulation"]
    assert len(table["cells"]) == 12
    assert all(cell["scored"] is False for cell in table["cells"])
    assert not any(cell["headline"] for cell in table["cells"])
    assert table["row_id"] == f"MS0:{ID}"
    assert table["labels"][0] == tabulation.INVENTED_DATA_LABEL
    assert entry["counterpart_of_the_headline"] == {"option": 2, "row": "all"}
    changes = entry["reclassification"]
    assert changes["worker_records_classified_differently"] > 0
    assert changes["persons_resting_on_a_record_classified_differently"] > 0
    assert (
        changes["worker_record_changes"].get(
            "window_year_earlier_under_the_sensitivity", 0
        )
        == 0
    )
    assert entry["weighted_share_of_the_universe_resting_percent"] == (
        entry["receipt_under_both_readings"]["all"][
            "resting_weighted_share_percent"
        ]
    )
    json.dumps(result, allow_nan=False)


def test_the_sensitivity_cells_are_its_rows_recomputed(pair, result):
    """Differential: each sensitivity cell equals a direct weighted mean
    of its evaluation rows, and each scored-reading share equals MS0's
    tabulated cell."""

    _, other = pair
    rows = evaluation.evaluate(
        other, pol.policy_for_row("MS0"), PARAMETERS
    ).rows
    entry = result["sensitivities"][ID]
    ms0 = {
        (cell["option"], cell["row"]): cell
        for cell in result["rows"]["MS0"]["tabulation"]["cells"]
    }
    for cell in entry["tabulation"]["cells"]:
        mask = (
            pd.Series(True, index=rows.index)
            if cell["row"] == "all"
            else rows["sex"].eq(
                {"men": "male", "women": "female"}[cell["row"]]
            )
        )
        weight = rows.loc[mask, "weight"]
        receiving = rows.loc[mask, f"receives_{cell['option']}"]
        expected = 100 * math.fsum(weight[receiving]) / math.fsum(weight)
        assert cell["share_percent"] == pytest.approx(expected, abs=1e-12)
        both = entry["receipt_under_both_readings"][cell["row"]]["options"][
            str(cell["option"])
        ]
        assert both["share_percent_sensitivity_reading"] == pytest.approx(
            cell["share_percent"], abs=1e-12
        )
        assert both["share_percent_scored_reading"] == pytest.approx(
            ms0[(cell["option"], cell["row"])]["share_percent"], abs=1e-12
        )


def _check_bound(scored, other):
    reclassified = pipeline.own_receipt_reclassification(scored, other)
    policy = pol.policy_for_row("MS0")
    left = evaluation.evaluate(scored, policy, PARAMETERS).rows
    right = evaluation.evaluate(other, policy, PARAMETERS).rows
    right = right.set_index("person_id").loc[left["person_id"]]
    for number in pol.TABLE6_OPTIONS:
        column = f"receives_{number}"
        differs = left[column].to_numpy() != right[column].to_numpy()
        ids = set(left.loc[differs, "person_id"])
        assert ids <= reclassified.persons_differing, number
    by_cell = pipeline.receipt_under_both_readings(
        left, right.reset_index(), reclassified.persons_differing
    )
    for cell in by_cell.values():
        if not cell["defined"]:
            continue
        resting = cell["resting_weighted_share_percent"]
        for option in cell["options"].values():
            change = option["change_percent_points"]
            assert abs(change) <= resting + 1e-9
            assert change == pytest.approx(
                option["moved_in_percent"] - option["moved_out_percent"],
                abs=1e-9,
            )
            assert option["moved_out_percent"] <= (
                option["receiving_and_resting_percent_scored_reading"] + 1e-9
            )
    return reclassified


@_COHORT_SETTINGS
@given(
    st.integers(min_value=0, max_value=10_000),
    st.sampled_from((0.0, 0.5, 1.0)),
)
def test_property_receipt_differs_only_for_the_resting(seed, share):
    frames = _frames(seed, share)
    scored = _inputs(frames, SCORED)
    other = _inputs(frames, SENSITIVITY)
    reclassified = _check_bound(scored, other)
    if share == 0.0:
        assert not reclassified.records_differing
        assert not reclassified.persons_differing


def test_the_reclassification_names_each_reason(pair):
    scored, other = pair
    found = pipeline.own_receipt_reclassification(scored, other)
    assert found.persons_differing == frozenset(found.reasons)
    persons = {p.person_id: p for p in scored.persons}
    for pid, reasons in found.reasons.items():
        assert reasons <= {"own_record", "links", "linked_record"}, pid
        person = persons[pid]
        if "own_record" in reasons and person.own_record_id is not None:
            assert (
                person.own_record_id in found.records_differing
                or person.own_record_id
                != next(
                    p for p in other.persons if p.person_id == pid
                ).own_record_id
            )
    # a lost link alone counts: drop one person's links under the
    # sensitivity (as the spouse link's 2022 own-receipt test can)
    linked = next(p for p in other.persons if p.links)
    unlinked = dataclasses.replace(
        other,
        persons=tuple(
            dataclasses.replace(p, links=()) if p is linked else p
            for p in other.persons
        ),
    )
    again = pipeline.own_receipt_reclassification(scored, unlinked)
    assert "links" in again.reasons[linked.person_id]
    # identical inputs: nothing differs
    same = pipeline.own_receipt_reclassification(
        scored,
        scored.__class__(
            workers=scored.workers,
            persons=scored.persons,
            provenance_kind=scored.provenance_kind,
            design=scored.design,
            source=scored.source,
            own_receipt_reading=SENSITIVITY,
        ),
    )
    assert not same.records_differing and not same.persons_differing


def test_a_person_whose_receipt_differs_without_resting_is_an_error(pair):
    scored, other = pair
    policy = pol.policy_for_row("MS0")
    left = evaluation.evaluate(scored, policy, PARAMETERS).rows
    right = left.copy()
    right.loc[0, "receives_2"] = not bool(right.loc[0, "receives_2"])
    with pytest.raises(AssertionError, match="receives differently"):
        pipeline.receipt_under_both_readings(left, right, frozenset())


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
def _never(*args, **kwargs):
    raise AssertionError("evaluated before the guards")


def _unblocked() -> dict:
    block = json.loads(json.dumps(specification.m1_parameter_block()))
    block.update(
        status="ratified_frozen", version="m1-ratified-1", blocked_by=[]
    )
    return block


def test_a_registered_run_needs_the_sensitivity(pair, monkeypatch):
    scored, other = pair
    monkeypatch.setattr(pipeline, "evaluate", _never)
    psid_kind = dataclasses.replace(
        scored, provenance_kind=evaluation.PSID_FILES
    )
    with pytest.raises(ValueError, match="d430 sensitivity"):
        pipeline.run_track_m(
            psid_kind,
            PARAMETERS,
            data_provenance="registered_real",
            registration_pointer=POINTER,
            specification=_unblocked(),
        )


def test_the_guards_refuse_before_any_computation(pair, monkeypatch):
    scored, other = pair
    monkeypatch.setattr(pipeline, "evaluate", _never)
    run = pipeline.run_track_m
    # scored rows under the sensitivity reading
    with pytest.raises(ValueError, match="scored under the own-receipt"):
        run(other, PARAMETERS, data_provenance="invented")
    # a sensitivity under the scored reading
    with pytest.raises(ValueError, match="built under"):
        run(
            scored,
            PARAMETERS,
            data_provenance="invented",
            own_receipt_sensitivity=scored,
        )
    # another universe: a weight, a person, the design
    first = other.persons[0]
    for changed in (
        dataclasses.replace(
            other,
            persons=(
                dataclasses.replace(first, weight=first.weight + 1.0),
                *other.persons[1:],
            ),
        ),
        dataclasses.replace(
            other, persons=(*other.persons[1:], other.persons[0])
        ),
        dataclasses.replace(other, design=other.design.iloc[1:]),
    ):
        with pytest.raises(ValueError, match="same"):
            run(
                scored,
                PARAMETERS,
                data_provenance="invented",
                own_receipt_sensitivity=changed,
            )
    # other files, or another provenance kind
    hashed = dataclasses.replace(
        other,
        provenance_kind=evaluation.PSID_FILES,
        source={
            **dict(other.source),
            pipeline.PSID_FILES_SOURCE_KEY: {"INVENTED.txt": "0" * 64},
        },
    )
    with pytest.raises(ValueError, match="registered run"):
        run(
            scored,
            PARAMETERS,
            data_provenance="invented",
            own_receipt_sensitivity=hashed,
        )
    with pytest.raises(ValueError, match="provenance kind"):
        run(
            scored,
            PARAMETERS,
            data_provenance="invented",
            own_receipt_sensitivity=dataclasses.replace(
                other, provenance_kind=evaluation.PSID_FILES
            ),
        )


def test_a_threshold_year_the_sensitivity_needs_is_checked_first(
    pair, monkeypatch
):
    scored, other = pair
    early = evaluation.WorkerRecord(
        "EARLY",
        1936,
        "old_age",
        2004,
        {year: 30_000.0 for year in range(1968, 1997)},
    )
    with_early = dataclasses.replace(
        other, workers={**other.workers, "EARLY": early}
    )
    monkeypatch.setattr(pipeline, "evaluate", _never)
    from populace_dynamics.min_benefit_track_m import rules

    with pytest.raises(rules.ThresholdYearMissingError, match="1998"):
        pipeline.run_track_m(
            scored,
            PARAMETERS,
            data_provenance="invented",
            own_receipt_sensitivity=with_early,
        )


def test_the_tabulation_marks_unscored_cells(pair):
    scored, _ = pair
    rows = evaluation.evaluate(
        scored, pol.policy_for_row("MS0"), PARAMETERS
    ).rows
    common = {
        "row_id": "X",
        "data_provenance": "invented",
        "design": scored.design,
    }
    marked = tabulation.tabulate_track_m(rows, scored=False, **common)
    plain = tabulation.tabulate_track_m(rows, **common)
    assert all(cell["scored"] for cell in plain["cells"])
    assert sum(cell["headline"] for cell in plain["cells"]) == 1
    for left, right in zip(plain["cells"], marked["cells"], strict=True):
        assert right["scored"] is False and right["headline"] is False
        assert {
            k: v for k, v in left.items() if k not in ("scored", "headline")
        } == {
            k: v for k, v in right.items() if k not in ("scored", "headline")
        }
    with pytest.raises(tabulation.TrackMTabulationError, match="bool"):
        tabulation.tabulate_track_m(rows, scored=1, **common)


# ---------------------------------------------------------------------------
# The structural count before the registration (all records, never by
# window) and the sensitivity's threshold years (years only)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def cohorts():
    frames = _frames(13, 0.6, 80)
    return (
        cohort.build_cohort(frames),
        cohort.build_cohort(frames, own_receipt_reading=SENSITIVITY),
    )


def test_the_first_receipt_count_is_a_brute_force_count(cohorts):
    """Differential: the count equals a direct pass over the histories."""

    scored, _ = cohorts
    counts = cohort.first_own_receipt_type_before_62(scored)
    own = scored.records[scored.records["basis"] != "death"]
    expected_before = expected_reached = expected_other = 0
    reached_ids = set()
    for row in own.itertuples(index=False):
        history = scored.histories[int(row.person_id)]
        first = min(y for y, o in history.items() if o.status == OWN)
        assert first == row.first_own_year
        if first >= row.birth_year + 62:
            continue
        expected_before += 1
        obs = history[first]
        if not ({"retirement", "disability"} & obs.types):
            expected_reached += 1
            expected_other += obs.types == frozenset({"other"})
            reached_ids.add(row.record_id)
    assert counts["records_with_own_receipt"] == len(own)
    assert counts["first_own_receipt_before_62"] == expected_before
    assert counts["first_own_receipt_before_62_unknown_or_other"] == (
        expected_reached
    )
    assert (
        counts["first_own_receipt_before_62_mentions_only_other"]["records"]
        == expected_other
    )
    assert expected_reached > 0 and expected_other > 0
    kinds = counts["first_own_receipt_before_62_unknown_or_other_by_kind"]
    assert sum(kinds.values()) == expected_reached
    assert (
        sum(
            counts[
                "first_own_receipt_before_62_unknown_or_other_by_source"
            ].values()
        )
        == expected_reached
    )
    only_other = counts["first_own_receipt_before_62_mentions_only_other"]
    assert (
        only_other["every_type_item_known"]
        + only_other["some_type_item_unknown"]
        == only_other["records"]
    )
    assert counts["first_own_receipt_before_62"] == (
        counts["first_own_receipt_before_62_names_a_workers_benefit"]
        + expected_reached
    )
    # every own record the two readings classify differently, or the
    # sensitivity drops, is among those reached; the converse fails in
    # general (a reached record can keep its basis, window and onset:
    # test_a_reached_record_can_keep_its_basis_window_and_onset)
    _, other = cohorts
    left = scored.records.set_index("record_id")
    right = other.records.set_index("record_id")
    columns = ["basis", "window_year", "onset_year"]
    moved = {
        key
        for key in left.index
        if left.loc[key, "basis"] != "death"
        and (
            key not in right.index
            or not left.loc[key, columns].equals(right.loc[key, columns])
        )
    }
    assert moved and moved <= reached_ids
    # under the sensitivity reading no first own receipt before 62 is of
    # that kind: the reading reads each as unobserved
    again = cohort.first_own_receipt_type_before_62(other)
    assert again["own_receipt_reading"] == SENSITIVITY
    assert again["first_own_receipt_before_62_unknown_or_other"] == 0


#: Every key d430's structural count may report, at each level.  The count
#: runs on the staged PSID before the registration, so its output is pinned
#: whole: a new key (a split by window, by year or by anything else) fails
#: :func:`test_the_count_computes_no_in_window_or_reserved_count` until it
#: is added here deliberately (independent review of 2026-09-26, D1).
_COUNT_KEYS = frozenset(
    {
        "scope",
        "own_receipt_reading",
        "records_with_own_receipt",
        "first_own_receipt_before_62",
        "first_own_receipt_before_62_names_a_workers_benefit",
        "first_own_receipt_before_62_unknown_or_other",
        "first_own_receipt_before_62_unknown_or_other_by_kind",
        "first_own_receipt_before_62_mentions_only_other",
        "first_own_receipt_before_62_unknown_or_other_by_source",
        "records_with_any_unknown_or_other_own_receipt_before_62",
        "review_20260925_definition",
    }
)
_COUNT_KINDS = frozenset(
    {
        "mentions_only_other",
        "mentions_other_and_an_auxiliary_type",
        "mentions_an_auxiliary_type_with_a_type_unknown",
        "names_no_type_with_a_type_unknown",
        "names_no_type_every_type_item_known",
    }
)
_COUNT_SOURCES = frozenset(
    {"individual", "family_1993", "year_before_last", "total"}
)


def test_the_count_computes_no_in_window_or_reserved_count(
    cohorts, monkeypatch
):
    """Guard: the d430 count reads no window year, threshold year, onset,
    resolution or link, calls none of the functions that count by window,
    classify a record or compute section 11's reserved diagnostics, and
    reports exactly its registered keys, each a count."""

    scored, _ = cohorts
    full = cohort.first_own_receipt_type_before_62(scored)

    def refuse(*args, **kwargs):
        raise AssertionError("a window or reserved count was computed")

    for name in (
        "cohort_structure",
        "boundary_year_unobserved",
        "_boundary_readings",
        "_threshold_years_by_window",
        "structural_counts_before_registration",
        # a window year recomputed from the histories (review D1)
        "classify_own_record",
        "own_receipt_view",
        "record_years",
        "build_cohort",
        "survivor_claim_year",
        "spouse_claim_year",
    ):
        monkeypatch.setattr(cohort, name, refuse)
    monkeypatch.setattr(cohort.OwnRecordClass, "in_window", refuse)
    keep = ["record_id", "person_id", "birth_year", "basis", "first_own_year"]
    stripped = dataclasses.replace(
        scored,
        records=scored.records[keep].copy(),
        links=scored.links.iloc[0:0],
        persons=scored.persons[["person_id"]].copy(),
    )
    assert cohort.first_own_receipt_type_before_62(stripped) == full

    def keys(value):
        if isinstance(value, dict):
            for key, inner in value.items():
                yield key
                yield from keys(inner)

    for key in keys(full):
        for word in ("window", "threshold", "exposed", "share", "link"):
            assert word not in key, key
    # the output is pinned whole: no key beyond the registered count's
    assert set(full) == _COUNT_KEYS
    assert set(
        full["first_own_receipt_before_62_unknown_or_other_by_kind"]
    ) <= (_COUNT_KINDS)
    assert set(
        full["first_own_receipt_before_62_unknown_or_other_by_source"]
    ) <= (_COUNT_SOURCES)
    assert set(full["first_own_receipt_before_62_mentions_only_other"]) == {
        "records",
        "every_type_item_known",
        "some_type_item_unknown",
    }
    assert set(full["review_20260925_definition"]) == {
        "first_own_receipt_with_a_type_item_unknown",
        "of_which_disability_origin_without_a_disability_mention",
    }

    def leaves(value, key=None):
        if isinstance(value, dict):
            for inner_key, inner in value.items():
                yield from leaves(inner, inner_key)
        else:
            yield key, value

    for key, value in leaves(full):
        if key in ("scope", "own_receipt_reading"):
            assert isinstance(value, str), key
        else:
            # counts only: every other leaf is a whole number of records
            assert type(value) is int and value >= 0, (key, value)


def test_the_sensitivitys_threshold_years_are_years_only(cohorts):
    scored, other = cohorts
    with pytest.raises(ValueError, match="sensitivity reading"):
        cohort.sensitivity_threshold_years_before_registration(scored)
    years = cohort.sensitivity_threshold_years_before_registration(other)
    assert years["own_receipt_reading"] == SENSITIVITY
    window = years["threshold_years_needed"]
    assert set(window) == {"2004_in_or_after"}
    entry = window["2004_in_or_after"]
    assert set(entry) == {
        "earliest_threshold_year",
        "threshold_years_before_2003",
        "bases_needing_years_before_2003",
    }
    assert all(
        isinstance(y, int) for y in entry["threshold_years_before_2003"]
    )
    # differential: the years agree with the full counts of that cohort
    full = cohort.cohort_structure(other)["by_policy_year"]["2004_in_or_after"]
    assert entry["earliest_threshold_year"] == full["earliest_threshold_year"]
    assert entry["threshold_years_before_2003"] == sorted(
        int(y) for y in full["threshold_years_before_2003"]
    )


def test_the_counts_before_registration_are_unchanged_by_the_refactor(
    cohorts,
):
    """The window years moved into a helper the d430 count shares; the
    scored reading's counts are what the full counts give (differential
    against ``cohort_structure``, as before)."""

    scored, _ = cohorts
    before = cohort.structural_counts_before_registration(scored)
    full = cohort.cohort_structure(scored)["by_policy_year"]
    for key in ("2004_in_or_after", "2004_after", "2007_in_or_after"):
        entry = before["threshold_years_needed"][key]
        assert entry["earliest_threshold_year"] == (
            full[key]["earliest_threshold_year"]
        )
        assert entry["threshold_years_before_2003"] == sorted(
            int(y) for y in full[key]["threshold_years_before_2003"]
        )
    assert set(before["threshold_years_needed"]) == {
        "2004_in_or_after",
        "2004_after",
        "2007_in_or_after",
        "any_registered_row",
    }


def test_the_structure_script_writes_d430s_count_and_years(monkeypatch):
    """``scripts/track_m_structure.py`` on INVENTED frames: the d430 count
    and the sensitivity's threshold years, from the cohorts the script
    builds.  The test process has imported the rules modules, so the
    script's run-time import check is emptied here; the static check that
    the cohort module imports none of them stays."""

    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    spec_ = importlib.util.spec_from_file_location(
        "_track_m_structure", root / "scripts" / "track_m_structure.py"
    )
    script = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(script)
    frames = _frames(13, 0.6, 80)
    monkeypatch.setattr(
        script.cohort, "load_cohort_inputs", lambda data_dir=None: frames
    )
    monkeypatch.setattr(
        script.ssr, "verify_individual_codes", lambda data_dir=None: {}
    )
    forbidden = script.FORBIDDEN_MODULES
    assert "populace_dynamics.min_benefit_track_m.pipeline" in forbidden
    monkeypatch.setattr(script, "FORBIDDEN_MODULES", ())
    written = script.build()
    scored = cohort.build_cohort(frames)
    other = cohort.build_cohort(frames, own_receipt_reading=SENSITIVITY)
    assert written["m4_first_own_receipt_type_before_62_d430"] == (
        cohort.first_own_receipt_type_before_62(scored)
    )
    assert written["m4_own_receipt_sensitivity_d430_threshold_years"] == (
        cohort.sensitivity_threshold_years_before_registration(other)
    )
    source = root / "src/populace_dynamics/min_benefit_track_m/cohort.py"
    text = source.read_text(encoding="utf-8")
    for name in forbidden:
        module = name.rsplit(".", 1)[1]
        assert f"min_benefit_track_m import {module}" not in text
        assert f"min_benefit_track_m.{module} import" not in text


def test_a_spouse_links_2022_own_receipt_test_reads_the_same_view():
    """A spouse's link needs the spouse's own receipt in 2022 (section 4c
    item 5), which is own receipt as the reading reads it.  INVENTED: the
    spouse of reference person 6001 is moved to 1965 (outside the
    universe, so 2022 is before 62) with a disability benefit in 2016 and
    a combination code in 2022.  The scored reading links them; the
    sensitivity keeps the spouse's record, classified the same (its first
    own receipt names a disability benefit), but reads 2022 as
    unobserved, so the link is lost and counted."""

    frames = invented_psid.invented_cohort_inputs(seed=3, n_family_units=20)
    spouse, head, birth = 6002, 6001, 1965
    inputs = frames.structure_inputs
    anchor = inputs.anchor.copy()
    at = anchor["person_id"] == spouse
    anchor.loc[at, "age"] = 2023 - birth
    anchor.loc[at, "reported_birth_year"] = birth
    marriages = inputs.marriage_history.copy()
    marriages.loc[marriages["person_id"] == spouse, "birth_year"] = birth
    earnings = inputs.observed_earnings.copy()
    mine = earnings["person_id"] == spouse
    earnings.loc[mine, "age"] = earnings.loc[mine, "period"] - birth
    receipt = frames.individual_receipt.copy()
    rows = receipt["person_id"] == spouse
    receipt.loc[rows, "amount"] = 0
    for name in ssr.SS_TYPES:
        receipt.loc[rows, f"type_{name}"] = False
    receipt.loc[rows, "type_combination"] = False
    disabled = rows & (receipt["income_year"] == 2016)
    receipt.loc[disabled, "amount"] = 12_000
    receipt.loc[disabled, "type_disability"] = True
    unknown = rows & (receipt["income_year"] == 2022)
    receipt.loc[unknown, "amount"] = 9_000
    for name in ssr.SS_TYPES:
        receipt.loc[unknown, f"type_{name}"] = pd.NA
    receipt.loc[unknown, "type_combination"] = True
    assert disabled.sum() == 1 and unknown.sum() == 1
    frames = dataclasses.replace(
        frames,
        structure_inputs=dataclasses.replace(
            inputs,
            anchor=anchor,
            marriage_history=marriages,
            observed_earnings=earnings,
        ),
        individual_receipt=receipt,
    )
    scored = cohort.build_cohort(frames)
    other = cohort.build_cohort(frames, own_receipt_reading=SENSITIVITY)
    assert spouse not in set(scored.persons["person_id"])
    history = scored.histories[spouse]
    assert cohort.classify_own_record(
        history, birth
    ) == cohort.classify_own_record(
        history, birth, own_receipt_reading=SENSITIVITY
    )
    link = (head, "spouse", f"W{spouse}")

    def links(built):
        return {
            (row.person_id, row.kind, row.record_id)
            for row in built.links.itertuples(index=False)
        }

    assert link in links(scored)
    assert link not in links(other)
    key = "married_no_spouse_link_spouse_2022_unobserved"
    assert other.diagnostics.get(key, 0) == scored.diagnostics.get(key, 0) + 1
    # the pipeline names the lost link as the reason
    found = pipeline.own_receipt_reclassification(
        _inputs(frames, SCORED), _inputs(frames, SENSITIVITY)
    )
    assert "links" in found.reasons[str(head)]
