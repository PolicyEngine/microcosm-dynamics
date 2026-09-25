"""The M4 cohort: section 4b's rules on INVENTED receipt histories.

No PSID file is read.  The hand cases below are worked from the M1
specification's section 4b; the property tests state its rules for every
history Hypothesis draws; the differential tests hold the cohort's
section 4a years to ``rules.record_years`` and its universe to the
structural funnel.

Invariants (each a property test here):

* a record exists exactly when some observation is own receipt;
* the entitlement (window) year never follows the first observed own
  receipt *F*; an old-age record is entitled no earlier than the year of
  attaining 62 and first receives at or after it; a disability-origin
  record's onset is its entitlement year less one;
* rule 2: with an observed year without own receipt *L* before *F*, the
  entitlement year is ``max(year of attaining 62, L + 1)`` (old age) or
  ``L + 1`` (disability origin);
* rule 3's statements at the 2004 boundary hold for every history: own
  receipt in 2004 and none in 2003 gives entitlement in 2004; own receipt
  in both is out; observed non-receipt in 2004 (2006) before a later
  first receipt is in the 2004 (2007) window; first receipt before 2004
  is out of both windows;
* a year of auxiliary receipt only counts as a year without own receipt;
* adding an observed year without own receipt between *L* and *F* never
  moves the entitlement year earlier.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from populace_dynamics.data import social_security_receipt as ssr
from populace_dynamics.min_benefit_track_m import (
    DRY_RUN_HEADER,
    cohort,
    invented_psid,
    rules,
    structure,
)
from populace_dynamics.min_benefit_track_m.cohort import (
    AUXILIARY,
    NONE,
    OWN,
    ReceiptObservation,
)


def _obs(year: int, status: str, *types: str) -> ReceiptObservation:
    return ReceiptObservation(year, status, frozenset(types))


def _classify(birth: int, *observations: ReceiptObservation):
    return cohort.classify_own_record(observations, birth)


# ---------------------------------------------------------------------------
# One observed person-year
# ---------------------------------------------------------------------------
def test_an_observation_is_auxiliary_only_when_every_type_is_known():
    known = {name: False for name in ssr.SS_TYPES}
    survivor = cohort.observation(
        2010, receipt=True, types=known | {"survivor": True}
    )
    assert survivor.status == AUXILIARY
    assert survivor.types == frozenset({"survivor"})
    both = cohort.observation(
        2010,
        receipt=True,
        types=known | {"survivor": True, "retirement": True},
    )
    assert both.status == OWN
    unknown = cohort.observation(
        2010, receipt=True, types={**known, "survivor": True, "other": pd.NA}
    )
    assert unknown.status == OWN
    combination = cohort.observation(
        2010, receipt=True, types=known | {"survivor": True}, combination=True
    )
    assert combination.status == OWN
    assert cohort.observation(2010, receipt=True).status == OWN
    none = cohort.observation(2010, receipt=False, types=known)
    assert none.status == NONE and none.types == frozenset()
    with pytest.raises(ValueError):
        ReceiptObservation(2010, NONE, frozenset({"retirement"}))


# ---------------------------------------------------------------------------
# Section 4b rules 1-4, worked by hand
# ---------------------------------------------------------------------------
def test_rule_2_old_age_takes_the_later_of_62_and_the_boundary():
    found = _classify(
        1945, _obs(2004, NONE), _obs(2006, NONE), _obs(2008, OWN, "retirement")
    )
    assert found.basis == cohort.BASIS_OLD_AGE
    assert (found.last_without_year, found.first_own_year) == (2006, 2008)
    assert found.window_year == 2007  # max(2007, 2006 + 1)
    assert found.resolution == "rule2_observed_boundary"
    assert not found.unresolved and found.onset_year is None
    late = _classify(1940, _obs(2006, NONE), _obs(2008, OWN, "retirement"))
    assert late.window_year == 2007  # at 67: non-receipt observed at 66


def test_rule_1_disability_by_type_or_by_age():
    by_type = _classify(1955, _obs(2004, NONE), _obs(2006, OWN, "disability"))
    assert by_type.basis == cohort.BASIS_DISABILITY
    assert (by_type.window_year, by_type.onset_year) == (2005, 2004)
    by_age = _classify(1955, _obs(2008, NONE), _obs(2010, OWN, "retirement"))
    assert by_age.basis == cohort.BASIS_DISABILITY  # first receipt at 55
    assert by_age.retirement_type
    unknown_type = _classify(1950, _obs(2010, NONE), _obs(2012, OWN))
    assert unknown_type.basis == cohort.BASIS_OLD_AGE  # the age rule: 62


def test_a_year_of_auxiliary_receipt_is_a_year_without_own_receipt():
    found = _classify(
        1948,
        _obs(2008, AUXILIARY, "survivor"),
        _obs(2010, AUXILIARY, "survivor"),
        _obs(2012, OWN, "retirement", "survivor"),
    )
    assert found.last_without_year == 2010
    assert found.window_year == 2011
    assert found.first_types == frozenset({"retirement", "survivor"})
    assert _classify(1948, _obs(2010, AUXILIARY, "survivor")) is None


def test_receipt_in_the_first_observation_before_2004_is_out():
    found = _classify(1918, _obs(1983, OWN, "retirement"))
    assert found.basis == cohort.BASIS_OLD_AGE
    assert found.resolution == "receipt_in_first_observation_before_2004"
    assert found.window_year == 1980 and not found.unresolved
    di = _classify(1950, _obs(1990, OWN, "disability"))
    assert (di.basis, di.window_year, di.onset_year) == (
        cohort.BASIS_DISABILITY,
        1990,
        1989,
    )


@pytest.mark.parametrize(
    ("birth", "first", "types", "window", "in_2004", "in_2007", "basis"),
    [
        # rule 3, 2004: born 1942 or later with a retirement type is in
        (1942, 2004, ("retirement",), 2004, True, False, "old_age"),
        (1941, 2004, ("retirement",), 2003, False, False, "old_age"),
        # a later entrant born 1945 or later is in at 2007 as well
        (1946, 2010, ("retirement",), 2008, True, True, "old_age"),
        (1944, 2010, ("retirement",), 2006, True, False, "old_age"),
        # a disability type is not a retirement type: out of both
        (1950, 2006, ("disability",), 2003, False, False, "disability"),
        # receipt at 61 with a retirement mention: disability origin by
        # age, placed at the window rule 3 gives it
        (1943, 2004, ("retirement",), 2004, True, False, "disability"),
        (1948, 2008, ("retirement",), 2007, True, True, "disability"),
    ],
)
def test_rule_3_places_an_unresolved_record(
    birth, first, types, window, in_2004, in_2007, basis
):
    found = _classify(birth, _obs(first, OWN, *types))
    assert found.resolution == "rule3_age_rule" and found.unresolved
    assert found.basis == basis
    assert found.window_year == window
    assert found.rule3_in_window == {2004: in_2004, 2007: in_2007}
    assert (found.window_year >= 2004) is in_2004
    assert (found.window_year >= 2007) is in_2007
    if basis == "disability":
        assert found.onset_year == window - 1


# ---------------------------------------------------------------------------
# Properties over every history Hypothesis draws
# ---------------------------------------------------------------------------
_OBSERVABLE_YEARS = tuple(range(1983, 2023))


@st.composite
def _histories(draw):
    birth = draw(st.integers(min_value=1925, max_value=1960))
    years = draw(
        st.lists(
            st.sampled_from(_OBSERVABLE_YEARS),
            min_size=1,
            max_size=14,
            unique=True,
        )
    )
    out = {}
    for year in sorted(years):
        status = draw(st.sampled_from((OWN, OWN, NONE, AUXILIARY)))
        if status == OWN:
            types = draw(st.sets(st.sampled_from(ssr.SS_TYPES), max_size=3))
        elif status == AUXILIARY:
            types = draw(
                st.sets(
                    st.sampled_from(ssr.AUXILIARY_TYPES),
                    min_size=1,
                    max_size=2,
                )
            )
        else:
            types = set()
        out[year] = ReceiptObservation(year, status, frozenset(types))
    return birth, out


def _first_own(history):
    own = [y for y, o in history.items() if o.status == OWN]
    return min(own) if own else None


@settings(max_examples=600, deadline=None)
@given(_histories())
def test_the_classification_obeys_section_4b(case):
    birth, history = case
    found = cohort.classify_own_record(history, birth)
    first = _first_own(history)
    assert (found is None) is (first is None)
    if found is None:
        return
    attains_62 = birth + 62
    assert found.first_own_year == first
    assert found.window_year <= first
    if found.basis == cohort.BASIS_OLD_AGE:
        assert first >= attains_62
        assert found.window_year >= attains_62
        assert found.onset_year is None
    else:
        assert found.basis == cohort.BASIS_DISABILITY
        assert found.onset_year == found.window_year - 1
        assert first < attains_62 or "disability" in found.first_types
    without = [y for y, o in history.items() if y < first and o.status != OWN]
    if without:
        last = max(without)
        assert found.resolution == "rule2_observed_boundary"
        assert found.last_without_year == last
        expected = (
            max(attains_62, last + 1)
            if found.basis == cohort.BASIS_OLD_AGE
            else last + 1
        )
        assert found.window_year == expected
    else:
        assert found.last_without_year is None
        assert found.unresolved is (first >= 2004)


@settings(max_examples=600, deadline=None)
@given(_histories())
def test_rule_3_statements_hold_at_the_2004_and_2007_boundaries(case):
    birth, history = case
    found = cohort.classify_own_record(history, birth)
    first = _first_own(history)
    if found is None:
        return
    at = history.get
    # first receipt before 2004: out of both windows
    if first < 2004:
        assert found.window_year < 2004
    # own receipt in 2004 (the first) and none in 2003: entitled in 2004
    if first == 2004 and at(2003) is not None and at(2003).status != OWN:
        assert found.window_year == 2004
    # own receipt in both 2003 and 2004: out
    if (
        at(2003) is not None
        and at(2003).status == OWN
        and at(2004) is not None
        and at(2004).status == OWN
    ):
        assert found.window_year < 2004
    # observed non-receipt in 2004 (2006) and a later first receipt
    for boundary, policy_year in ((2004, 2004), (2006, 2007)):
        seen = at(boundary)
        if seen is not None and seen.status != OWN and first > boundary:
            assert found.window_year >= policy_year


@settings(max_examples=400, deadline=None)
@given(_histories())
def test_auxiliary_receipt_classifies_as_non_receipt(case):
    birth, history = case
    as_none = {
        year: (
            ReceiptObservation(year, NONE) if obs.status == AUXILIARY else obs
        )
        for year, obs in history.items()
    }
    left = cohort.classify_own_record(history, birth)
    right = cohort.classify_own_record(as_none, birth)
    if left is None:
        assert right is None
        return
    assert (left.basis, left.window_year, left.onset_year) == (
        right.basis,
        right.window_year,
        right.onset_year,
    )
    assert left.resolution == right.resolution


@settings(max_examples=400, deadline=None)
@given(_histories(), st.data())
def test_more_observed_non_receipt_never_moves_entitlement_earlier(case, data):
    birth, history = case
    found = cohort.classify_own_record(history, birth)
    assume(found is not None and found.last_without_year is not None)
    between = [
        y
        for y in range(found.last_without_year + 1, found.first_own_year)
        if y not in history
    ]
    assume(between)
    year = data.draw(st.sampled_from(between))
    more = {**history, year: ReceiptObservation(year, NONE)}
    again = cohort.classify_own_record(more, birth)
    assert again.window_year >= found.window_year
    assert again.basis == found.basis


# ---------------------------------------------------------------------------
# Claim years
# ---------------------------------------------------------------------------
@settings(max_examples=300, deadline=None)
@given(_histories(), st.integers(min_value=1960, max_value=2022))
def test_a_survivors_claim_year_is_within_what_the_rules_allow(case, death):
    birth, history = case
    year, source = cohort.survivor_claim_year(
        history, birth_year=birth, death_year=death
    )
    earliest = max(death, birth + 60)
    assert year <= cohort.INCOME_YEAR
    assert year == min(max(year, earliest), cohort.INCOME_YEAR)
    assert source in ("survivor_mention", "any_receipt", "earliest_allowed")
    if source == "earliest_allowed":
        assert year == min(earliest, cohort.INCOME_YEAR)
    if source == "survivor_mention":
        mentions = [
            y
            for y, o in history.items()
            if y >= earliest and o.mentions_survivor
        ]
        assert mentions and year <= min(mentions)


def test_a_survivors_claim_year_worked_by_hand():
    history = {
        2004: _obs(2004, NONE),
        2006: _obs(2006, OWN, "retirement"),
        2010: _obs(2010, OWN, "retirement", "survivor"),
    }
    # died 2008, born 1944 (60 in 2004): first survivor mention 2010,
    # the last year without it before then is 2006 -> 2007, but no
    # earlier than the death year
    assert cohort.survivor_claim_year(
        history, birth_year=1944, death_year=2008
    ) == (2008, "survivor_mention")
    assert cohort.survivor_claim_year(
        {2004: _obs(2004, NONE)}, birth_year=1950, death_year=2015
    ) == (2015, "earliest_allowed")


@settings(max_examples=300, deadline=None)
@given(
    st.integers(min_value=1925, max_value=1960),
    st.one_of(st.none(), st.integers(min_value=1980, max_value=2030)),
    st.one_of(st.none(), st.integers(min_value=1980, max_value=2030)),
    st.integers(min_value=1980, max_value=2030),
)
def test_a_spouses_claim_year_is_the_latest_constraint(
    birth, own, auxiliary, worker
):
    year = cohort.spouse_claim_year(
        birth_year=birth,
        own_entitlement_year=own,
        auxiliary_entitlement_year=auxiliary,
        worker_entitlement_year=worker,
    )
    assert year <= cohort.INCOME_YEAR
    floor = max(worker, birth + 62, own if own is not None else -1)
    if own is None and auxiliary is not None:
        floor = max(floor, auxiliary)
    assert year == min(floor, cohort.INCOME_YEAR)


def test_unlinked_auxiliaries():
    assert cohort.unlinked_kind(frozenset({"survivor"}), set()) == "survivor"
    assert cohort.unlinked_kind(frozenset({"survivor"}), {"survivor"}) is None
    assert (
        cohort.unlinked_kind(frozenset({"dependent_of_retired"}), set())
        == "dependent"
    )
    assert (
        cohort.unlinked_kind(frozenset({"dependent_of_retired"}), {"spouse"})
        is None
    )
    assert cohort.unlinked_kind(frozenset({"retirement"}), set()) is None


# ---------------------------------------------------------------------------
# Differential: section 4a in the cohort and in the rules
# ---------------------------------------------------------------------------
@settings(max_examples=400, deadline=None)
@given(
    st.sampled_from(rules.BASES),
    st.integers(min_value=1913, max_value=1990),
    st.integers(min_value=0, max_value=60),
    st.integers(min_value=0, max_value=30),
)
def test_the_cohorts_section_4a_years_are_the_rules(basis, birth, a, b):
    attains_62 = birth + 62
    onset = death = None
    if basis == rules.BASIS_OLD_AGE:
        window = attains_62 + min(b, 10)
    else:
        event = birth + 18 + a
        window = event + b
        if basis == rules.BASIS_DISABILITY:
            onset = event
        else:
            death = event
    ours = cohort.record_years(
        basis, birth, window, onset_year=onset, death_year=death
    )
    theirs = rules.record_years(
        basis=basis,
        birth_year=birth,
        window_year=window,
        onset_year=onset,
        death_year=death,
    )
    assert ours == {
        "threshold_year": theirs.threshold_year,
        "last_year": theirs.last_year,
    }


def test_the_bases_and_the_oracle_floor_are_the_rules():
    assert (
        cohort.BASIS_OLD_AGE,
        cohort.BASIS_DISABILITY,
        cohort.BASIS_DEATH,
    ) == rules.BASES
    from populace_dynamics.ss import statutory_aime

    assert cohort.FIRST_AGE_62_YEAR_ENCODED == (
        statutory_aime.FIRST_AGE_62_YEAR_ENCODED
    )


def test_every_year_without_person_level_receipt_is_listed():
    person_level = {wave - 1 for wave in ssr.INDIVIDUAL_WAVES} | {1992}
    expected = tuple(
        year for year in range(1993, 2023) if year not in person_level
    )
    assert cohort.YEARS_WITHOUT_PERSON_LEVEL_RECEIPT == expected


# ---------------------------------------------------------------------------
# Receipt histories from M3's frames
# ---------------------------------------------------------------------------
def _individual(rows):
    frame = pd.DataFrame(
        [
            {
                "person_id": pid,
                "income_year": year,
                "amount": amount,
                "type_combination": False,
                **{
                    f"type_{name}": (name in types if amount else pd.NA)
                    for name in ssr.SS_TYPES
                },
            }
            for pid, year, amount, types in rows
        ]
    )
    for name in ssr.SS_TYPES:
        frame[f"type_{name}"] = frame[f"type_{name}"].astype("boolean")
    return frame


def _family_level(rows):
    frame = pd.DataFrame(
        [
            {
                "person_id": pid,
                "income_year": year,
                "source": source,
                "receipt": receipt,
                "fu_size": 1,
                **{f"type_{name}": pd.NA for name in ssr.SS_TYPES},
            }
            for pid, year, source, receipt in rows
        ]
    )
    for name in ssr.SS_TYPES:
        frame[f"type_{name}"] = frame[f"type_{name}"].astype("boolean")
    return frame


def test_person_level_observations_take_precedence():
    individual = _individual(
        [(1, 2004, 9_000, ("retirement",)), (1, 2006, 0, ())]
    )
    family_level = _family_level(
        [
            (1, 2004, "year_before_last", False),
            (1, 2003, "year_before_last", False),
            (1, 2007, "year_before_last", True),
            (2, 2003, "total", False),
        ]
    )
    histories = cohort.receipt_histories(
        individual, individual.iloc[0:0], family_level
    )
    assert histories[1][2004].status == OWN
    assert histories[1][2004].source == "individual"
    assert histories[1][2003].status == NONE
    assert histories[1][2007].status == OWN  # a one-member family's yes
    assert histories[1][2007].types == frozenset()
    assert histories[2] == {
        2003: ReceiptObservation(2003, NONE, frozenset(), "total")
    }
    only = cohort.receipt_histories(
        individual, individual.iloc[0:0], family_level, person_ids={2}
    )
    assert set(only) == {2}
    with pytest.raises(ValueError, match="two person-level"):
        cohort.receipt_histories(
            pd.concat([individual, individual]), None, None
        )


# ---------------------------------------------------------------------------
# The cohort on INVENTED PSID-shaped frames (invented_psid)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def invented():
    frames = invented_psid.invented_cohort_inputs(seed=11, n_family_units=160)
    return frames, cohort.build_cohort(frames)


def test_the_universe_is_the_structural_funnels(invented):
    """Differential: M4's universe equals section 10's funnel."""

    frames, built = invented
    counts = structure.structural_counts(frames.structure_inputs)
    funnel = counts["funnel"]["receives_oasdi_person_level"]
    assert len(built.persons) == funnel
    assert built.persons["person_id"].is_unique


def test_every_record_and_link_is_consistent(invented):
    frames, built = invented
    persons, records, links = built.persons, built.records, built.links
    by_id = records.set_index("record_id")
    assert by_id.index.is_unique
    for own in persons["own_record_id"].dropna():
        assert own in by_id.index
        assert by_id.loc[own, "basis"] != cohort.BASIS_DEATH
    for row in links.itertuples(index=False):
        assert row.record_id in by_id.index
        record = by_id.loc[row.record_id]
        if row.kind == "spouse":
            assert record["basis"] != cohort.BASIS_DEATH
            assert not record["deceased"]
        else:
            assert record["deceased"]
        assert row.claim_year <= cohort.INCOME_YEAR
    for record in records.itertuples(index=False):
        years = cohort.record_years(
            record.basis,
            record.birth_year,
            record.window_year,
            onset_year=(
                None if pd.isna(record.onset_year) else int(record.onset_year)
            ),
            death_year=(
                None if pd.isna(record.death_year) else int(record.death_year)
            ),
        )
        assert years["threshold_year"] == record.threshold_year
        assert years["last_year"] == record.last_year
        if record.basis == cohort.BASIS_DEATH:
            assert record.window_year >= record.death_year
        else:
            assert record.window_year <= record.first_own_year
    paid = persons[persons["paid_own_worker_benefit"]]
    assert paid["own_record_id"].notna().all()
    ms5 = persons[persons["ms5_in_scope"]]
    assert ms5["paid_own_worker_benefit"].all()
    assert set(persons["sex"]) <= {"male", "female", "unknown"}
    # every basis and both link kinds occur in the invented cohort
    assert set(records["basis"]) == set(rules.BASES)
    assert set(links["kind"]) == {"spouse", "survivor"}
    assert persons["unlinked_auxiliary"].any()
    assert records["unresolved"].any()


def test_the_invented_cohort_is_deterministic():
    one = invented_psid.invented_cohort_inputs(seed=3, n_family_units=40)
    two = invented_psid.invented_cohort_inputs(seed=3, n_family_units=40)
    left, right = cohort.build_cohort(one), cohort.build_cohort(two)
    pd.testing.assert_frame_equal(left.persons, right.persons)
    pd.testing.assert_frame_equal(left.records, right.records)
    assert one.provenance["label"] == DRY_RUN_HEADER


def test_the_counts_before_registration_leave_out_the_diagnostics(invented):
    """Section 11 reserves in-window counts, exposed persons, unlinked
    auxiliaries and the MS5 scope for the registered run; the counts real
    files may give before it keep years, never in-window counts."""

    _, built = invented
    full = cohort.cohort_structure(built)
    before = cohort.structural_counts_before_registration(built)
    assert "by_policy_year" in full
    for key in (
        "by_policy_year",
        "unlinked_auxiliaries",
        "persons_ms5_in_scope",
        "ms5_in_scope_entitled_in_2022",
    ):
        assert key not in before, key
    assert set(before["unresolved_rule3"]) == {
        "records",
        "first_own_year_2004",
        "first_own_year_after_2004",
        "by_basis",
    }
    for value in before["boundary_year_unobserved"].values():
        assert set(value) == {"records", "readings_disagree"}
    windows = before["threshold_years_needed"]
    assert set(windows) == {
        "2004_in_or_after",
        "2004_after",
        "2007_in_or_after",
        "any_registered_row",
    }
    for value in windows.values():
        assert set(value) == {
            "earliest_threshold_year",
            "threshold_years_before_2003",
            "bases_needing_years_before_2003",
        }
        assert set(value["bases_needing_years_before_2003"]) <= set(
            rules.BASES
        )
        assert bool(value["bases_needing_years_before_2003"]) is bool(
            value["threshold_years_before_2003"]
        )
        assert all(
            isinstance(y, int) for y in value["threshold_years_before_2003"]
        )
    # the years agree with the full counts'
    full_2004 = full["by_policy_year"]["2004_in_or_after"]
    assert windows["2004_in_or_after"]["earliest_threshold_year"] == (
        full_2004["earliest_threshold_year"]
    )
    assert windows["2004_in_or_after"]["threshold_years_before_2003"] == (
        sorted(int(y) for y in full_2004["threshold_years_before_2003"])
    )
    union = set()
    for key in ("2004_in_or_after", "2004_after", "2007_in_or_after"):
        union |= set(windows[key]["threshold_years_before_2003"])
    assert windows["any_registered_row"]["threshold_years_before_2003"] == (
        sorted(union)
    )
    assert before["persons"] == full["persons"]
    assert math.isfinite(before["records"])
