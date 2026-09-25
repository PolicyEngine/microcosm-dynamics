"""Exercise 3's C0 invariants on generated INVENTED persons (Hypothesis).

Every person, date, benefit level and weight below is INVENTED: a
household of one subject and, when married or widowed, one partner, whose
2030 state (or, for a deceased partner, last state) the strategies build
the way Track A's projection leaves it (a DI award before the baseline
FRA; conversion at the baseline FRA attainment year, A4's July birth
month; the claiming step's claim year).  Levels are seeded into the PIA
cache, so no career is read.  The parameters are the invented wage
parameters with the statute's FRA schedule (``statutory_params``) and the
invented COLA path.  No PSID value, no model output and no comparator
value is read.

The invariants (E1 sections 3, 6, 7, 11, 12 and 21; ``e1-ratified-2``),
each for every generated person:

1. under fixed claim ages (C0) no individual benefit rises, under every
   schedule and survivor rule (rows F0-F2 and F7);
2. P2 <= P3 <= P1 <= baseline, person by person;
3. the null reform (the baseline bundle as the reform) changes nothing
   under every claiming response, and the baseline with Track A's fixed
   survivor span is Track A's own calculator bit for bit;
4. memberships differ under C0 only through the named mechanism
   ``spouse_excess_withheld_until_reform_conversion``, for the primary
   and the workers-only components, and a person meeting its definition
   is always one of those rows.
"""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from hypothesis import event, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a import benefits as track_benefits
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
)
from populace_dynamics.cola_track_a.config import (
    REGISTERED_ROWS as TRACK_A_ROWS,
)
from populace_dynamics.engine.di_entitlement import fra_attainment_year
from populace_dynamics.estimates.cola_age_profile import (
    PRIMARY_COMPONENTS,
    SCENARIO_SPECIFIC,
    WORKERS_ONLY_COMPONENTS,
    ColaAgeProfileConfig,
)
from populace_dynamics.estimates.cola_age_profile import (
    _normalize as a7_normalize,
)
from populace_dynamics.fra68_track import (
    ClaimingResponse,
    FRA68Config,
    SurvivorRetirementAge,
)
from populace_dynamics.fra68_track.benefits import (
    C0_MEMBERSHIP_MECHANISMS,
    SPOUSE_EXCESS_WITHHELD,
    WITHHELD_EXCESS,
    WITHHELD_EXCESS_NO_REFORM_BENEFIT,
    Scenario,
    classify_membership_differences,
    scenario_benefits,
    spouse_excess_withheld_until_reform_conversion,
    union_benefit_rows,
)
from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    reform_parameters,
)
from populace_dynamics.fra68_track.runner import e1_parameter_block
from tests.cola_track_a.test_assembly import invented_cola
from tests.fra68_track.test_runner import statutory_params

BASE = statutory_params()
REFORMS = {sid: reform_parameters(BASE, SCHEDULES[sid]) for sid in SCHEDULES}
COLA = invented_cola()
TRACK_CONFIG = FRA68Config(draw_indices=(0,)).track_a_config()
TRACK_ROW = TRACK_A_ROWS["R0"]
REFERENCE = 2030
BIRTH_MONTH = 7
SUBJECT, PARTNER = 1, 2
#: The C0 reform scenarios of rows F0-F2 and F7: (schedule, survivors).
C0_REFORMS = {
    "F1 (P1)": ("P1", SurvivorRetirementAge.STATUTORY_MAPPING),
    "F2 (P2)": ("P2", SurvivorRetirementAge.STATUTORY_MAPPING),
    "F0 (P3)": ("P3", SurvivorRetirementAge.STATUTORY_MAPPING),
    "F7 (P3)": ("P3", SurvivorRetirementAge.UNCHANGED_FROM_BASELINE),
}
COMPONENT_SETS = {
    "primary": PRIMARY_COMPONENTS,
    "workers_only": WORKERS_ONLY_COMPONENTS,
}
TOLERANCE = 1e-9


def conversion_year(birth: int, params) -> int:
    """A4's FRA attainment year (July birth month) under ``params``."""

    return int(
        fra_attainment_year(
            np.array([birth]), params, assumed_birth_month=BIRTH_MONTH
        )[0]
    )


# --------------------------------------------------------------------------
# INVENTED households
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Worker:
    """An INVENTED person's own record as the projection leaves it.

    ``kind`` is ``none`` (never claimed), ``retired`` (a retirement claim
    in ``claim_year``) or ``di`` (a DI award in ``award_year``, converted
    at the baseline FRA if that is by the state year; ``claim_year`` is a
    retirement claim that preceded the award, if any).  ``level`` is the
    person's own PIA at eligibility, whichever record it rests on (the
    oracle retirement PIA, the disclosed DI approximation or the
    pre-eligibility death level).
    """

    birth: int
    kind: str
    level: float
    claim_year: int | None = None
    award_year: int | None = None

    def state(self, year: int) -> dict:
        """The person's DI and claiming fields in the state of ``year``."""

        fields = {
            "birth_year": self.birth,
            "di_entitled": False,
            "di_award_year": None,
            "di_conversion_year": None,
            "di_recovery_year": None,
            "claimed": False,
            "claim_year": None,
        }
        if self.kind == "retired":
            fields.update(claimed=True, claim_year=self.claim_year)
        elif self.kind == "di":
            conversion = conversion_year(self.birth, BASE)
            converted = conversion <= year
            fields.update(
                di_entitled=not converted,
                di_award_year=self.award_year,
                di_conversion_year=conversion if converted else None,
            )
            if self.claim_year is not None:
                fields.update(claimed=True, claim_year=self.claim_year)
            elif converted:
                # The claiming step records the conversion as the claim.
                fields.update(claimed=True, claim_year=conversion)
        return fields

    def levels(self, person_id: int, death: int | None) -> dict:
        """PIA-cache entries for every level the calculators may read."""

        entries = {(person_id, "retirement", self.birth + 62): self.level}
        if self.kind == "di":
            onset = min(self.award_year, self.birth + 62)
            entries[(person_id, "di", onset)] = self.level
        if death is not None:
            entries[(person_id, "death_before_eligibility", death)] = (
                self.level
            )
        return entries


@dataclass(frozen=True)
class Household:
    subject: Worker
    marital: str
    partner: Worker | None = None
    death_year: int | None = None


#: $10.00-$4,000.00 in dimes, or a zero level (the disclosed approximation
#: of a career without covered earnings through the onset).
POSITIVE_LEVELS = st.integers(100, 40_000).map(lambda dimes: dimes / 10)
LEVELS = st.one_of(st.just(0.0), POSITIVE_LEVELS)


def _weighted_levels(zero_share: int, positive_share: int):
    """Zero or positive levels in the given proportions."""

    return st.sampled_from(
        [True] * zero_share + [False] * positive_share
    ).flatmap(lambda zero: st.just(0.0) if zero else POSITIVE_LEVELS)


MOSTLY_ZERO_LEVELS = _weighted_levels(3, 1)
MOSTLY_POSITIVE_LEVELS = _weighted_levels(1, 4)


@st.composite
def workers(
    draw,
    birth: int,
    state_year: int,
    kinds: tuple[str, ...] = ("none", "retired", "di"),
    levels=LEVELS,
) -> Worker:
    """An INVENTED record consistent with a projected state in a year."""

    kind = draw(st.sampled_from(kinds))
    level = draw(levels)
    if kind == "retired":
        first, last = birth + 62, min(state_year, birth + 70)
        if first <= last:
            claim = draw(st.integers(first, last))
            return Worker(birth, "retired", level, claim_year=claim)
    if kind == "di":
        conversion = conversion_year(birth, BASE)
        first = max(1979, birth + 18)
        last = min(state_year, conversion - 1)
        if first <= last:
            award = draw(st.integers(first, last))
            prior = None
            if birth + 62 <= award - 1 and draw(st.booleans()):
                prior = draw(st.integers(birth + 62, award - 1))
            return Worker(
                birth, "di", level, claim_year=prior, award_year=award
            )
    return Worker(birth, "none", level)


SUBJECT_BIRTHS = st.one_of(st.just(1963), st.integers(1940, 1975))
PARTNER_BIRTHS = st.one_of(st.just(1963), st.integers(1935, 1975))


@st.composite
def households(draw) -> Household:
    subject = draw(workers(draw(SUBJECT_BIRTHS), REFERENCE))
    marital = draw(st.sampled_from(["never_married", "married", "widowed"]))
    if marital == "never_married":
        return Household(subject, marital)
    birth = draw(PARTNER_BIRTHS)
    if marital == "widowed":
        death = draw(st.integers(2011, REFERENCE))
        return Household(
            subject, marital, draw(workers(birth, death - 1)), death
        )
    return Household(subject, marital, draw(workers(birth, REFERENCE)))


@st.composite
def near_mechanism_households(draw) -> Household:
    """INVENTED households at and around the named mechanism.

    A DI worker born 1962-1964 (the mechanism needs 1963: converted at 67
    in 2030 under the statute and at 68 in 2031 under every schedule),
    with a zero or positive own level, married to (or widowed by) a
    partner of any kind; the roles of subject and partner are swapped at
    random.
    """

    # Weighted towards the mechanism: a minority of the households meet
    # it (``--hypothesis-show-statistics`` reports how many; about one in
    # seven in the derandomized run), and the rest are near misses.
    birth = draw(st.sampled_from([1963] * 6 + [1962, 1964]))
    conversion = conversion_year(birth, BASE)
    award = draw(st.integers(1979, min(REFERENCE, conversion - 1)))
    prior = None
    if draw(st.booleans()):
        prior = draw(st.integers(birth + 62, REFERENCE))
        if prior >= award:
            prior = None
    level = draw(MOSTLY_ZERO_LEVELS)
    worker = Worker(birth, "di", level, claim_year=prior, award_year=award)
    kinds = ("retired", "retired", "di", "di", "none")
    marital = draw(st.sampled_from(["married"] * 3 + ["widowed"]))
    partner_birth = draw(st.integers(1940, 1975))
    if marital == "widowed":
        death = draw(st.integers(2011, REFERENCE))
        partner = draw(
            workers(partner_birth, death - 1, kinds, MOSTLY_POSITIVE_LEVELS)
        )
        return Household(worker, "widowed", partner, death)
    partner = draw(
        workers(partner_birth, REFERENCE, kinds, MOSTLY_POSITIVE_LEVELS)
    )
    if draw(st.booleans()):
        return Household(partner, "married", worker)
    return Household(worker, "married", partner)


def _state_row(person_id, worker, year, **marital):
    return {
        "person_id": person_id,
        "year": year,
        "weight": 1.0,
        "marital_status": "never_married",
        "spouse_person_id": None,
        "late_spouse_person_id": None,
        "widowhood_year": None,
        **worker.state(year),
        **marital,
    }


class Built(SimpleNamespace):
    """A household's cohort, projected state, lookups and level cache."""


def build(household: Household) -> Built:
    """The INVENTED household as the calculators read a projected draw."""

    persons = [(SUBJECT, household.subject.birth)]
    rows = []
    extra = []
    cache = dict(household.subject.levels(SUBJECT, None))
    partner = household.partner
    if household.marital == "married":
        persons.append((PARTNER, partner.birth))
        rows.append(
            _state_row(
                SUBJECT,
                household.subject,
                REFERENCE,
                marital_status="married",
                spouse_person_id=PARTNER,
            )
        )
        rows.append(
            _state_row(
                PARTNER,
                partner,
                REFERENCE,
                marital_status="married",
                spouse_person_id=SUBJECT,
            )
        )
        cache.update(partner.levels(PARTNER, None))
    elif household.marital == "widowed":
        persons.append((PARTNER, partner.birth))
        rows.append(
            _state_row(
                SUBJECT,
                household.subject,
                REFERENCE,
                marital_status="widowed",
                late_spouse_person_id=PARTNER,
                widowhood_year=household.death_year,
            )
        )
        extra.append(
            _state_row(
                PARTNER,
                partner,
                household.death_year - 1,
                marital_status="married",
                spouse_person_id=SUBJECT,
            )
        )
        cache.update(partner.levels(PARTNER, household.death_year))
    else:
        rows.append(_state_row(SUBJECT, household.subject, REFERENCE))
    final = pd.DataFrame(rows, dtype=object)
    final["year"] = final["year"].astype(int)
    final["person_id"] = final["person_id"].astype(int)
    panel = pd.concat(
        [final, pd.DataFrame(extra, dtype=object)], ignore_index=True
    )
    panel["year"] = panel["year"].astype(int)
    panel["person_id"] = panel["person_id"].astype(int)
    frame = pd.DataFrame(
        {
            "person_id": [pid for pid, _ in persons],
            "birth_year": [birth for _, birth in persons],
            "opening_status": ["none"] * len(persons),
            "ss_receipt_opening": [False] * len(persons),
            "family_unit_id": [1] * len(persons),
            "opening_claim_age": [None] * len(persons),
        }
    )
    cohort = SimpleNamespace(
        persons_by_id=frame.set_index("person_id", drop=False),
        careers={},
        opening={},
        roster_ids=frozenset(pid for pid, _ in persons),
        start_year=2010,
    )
    result = SimpleNamespace(slices=(final,), panel=panel)
    return Built(
        household=household,
        cohort=cohort,
        result=result,
        lookups=StateLookups(result, REFERENCE),
        cache=cache,
    )


def _context(built: Built, params) -> BenefitContext:
    return BenefitContext(
        cohort=built.cohort, params=params, baseline=COLA, config=TRACK_CONFIG
    )


def people(built: Built, scenario: Scenario):
    """Every alive INVENTED person's 2030 benefit in one scenario."""

    return scenario_benefits(
        built.result,
        context=_context(built, scenario.params),
        track_row=TRACK_ROW,
        scenario=scenario,
        lookups=built.lookups,
        pia_cache=copy.copy(built.cache),
        assumed_birth_month=BIRTH_MONTH,
    )[0]


def baseline_scenario(survivors=SurvivorRetirementAge.STATUTORY_MAPPING):
    return Scenario(
        name="baseline",
        params=BASE,
        baseline_params=BASE,
        survivor_retirement_age=survivors,
    )


def reform_scenario(sid, survivors, response=ClaimingResponse.FIXED):
    return Scenario(
        name="reform",
        params=REFORMS[sid],
        baseline_params=BASE,
        survivor_retirement_age=survivors,
        claiming_response=response,
        schedule_id=sid,
    )


def membership(built: Built, base, reform, sid: str, components):
    """A7's flags on the union rows, and the classification of them."""

    rows, counters = union_benefit_rows(
        base,
        reform,
        draw=0,
        context=_context(built, BASE),
        lookups=built.lookups,
        baseline_params=BASE,
        reform_params=REFORMS[sid],
    )
    if not rows:
        return rows, counters, None
    normalized = a7_normalize(
        pd.DataFrame(rows),
        ColaAgeProfileConfig(
            reference_year=REFERENCE,
            components=tuple(components),
            draw_indices=(0,),
            allow_membership_difference=True,
            membership_basis=SCENARIO_SPECIFIC,
        ),
    )
    sorted_ = classify_membership_differences(
        rows,
        normalized.recipient_base.tolist(),
        normalized.recipient_reform.tolist(),
        components=components,
        baseline_params=BASE,
        reform_params=REFORMS[sid],
        reference_year=REFERENCE,
        assumed_birth_month=BIRTH_MONTH,
        claiming_response=ClaimingResponse.FIXED,
    )
    return rows, counters, sorted_["record"]


def _worker_record_exists(worker: Worker) -> bool:
    return worker.kind in ("retired", "di")


def meets_the_definition(built: Built, person_id: int) -> bool:
    """The named mechanism, from the INVENTED specification alone.

    The person is a DI worker the projection converted at the baseline FRA
    by 2030 whom the reform (every schedule: FRA 68 from birth year 1960)
    converts after 2030, with a zero own level, married to a living partner
    who has a worker record with a positive level.  The baseline then pays
    a positive spouse's excess and the reform nothing.
    """

    household = built.household
    if household.marital != "married":
        return False
    worker, other = (
        (household.subject, household.partner)
        if person_id == SUBJECT
        else (household.partner, household.subject)
    )
    if worker.kind != "di" or worker.level != 0.0:
        return False
    if not conversion_year(worker.birth, BASE) <= REFERENCE:
        return False
    if not all(
        conversion_year(worker.birth, params) > REFERENCE
        for params in REFORMS.values()
    ):
        return False
    return _worker_record_exists(other) and other.level > 0


# --------------------------------------------------------------------------
# The canonical INVENTED case (E1 section 19): the mechanism itself
# --------------------------------------------------------------------------
#: A DI worker born 1963 with a zero own level, awarded 2018, married to a
#: retired worker born 1960 who claimed at 67 in 2027 with PIA $1,800.00.
#: Round INVENTED values: no value here is taken from the membership
#: diagnostic's real-data traces (E1 section 27).
CANONICAL = Household(
    Worker(1963, "di", 0.0, award_year=2018),
    "married",
    Worker(1960, "retired", 1800.0, claim_year=2027),
)


def test_the_canonical_case_is_the_named_mechanism():
    built = build(CANONICAL)
    base = people(built, baseline_scenario())
    assert conversion_year(1963, BASE) == 2030
    for sid in ("P1", "P2", "P3"):
        assert conversion_year(1963, REFORMS[sid]) == 2031
        reform = people(
            built,
            reform_scenario(sid, SurvivorRetirementAge.STATUTORY_MAPPING),
        )
        subject_base, subject_reform = base[SUBJECT], reform[SUBJECT]
        assert subject_base.own_kind == "converted"
        assert subject_reform.own_kind == "disabled"
        assert subject_base.components["retired_worker"] == 0.0
        assert subject_base.components["spouse"] > 0
        assert subject_reform.components == {"disabled_worker": 0.0}
        rows, counters, record = membership(
            built, base, reform, sid, PRIMARY_COMPONENTS
        )
        assert record["n_rows_differ"] == 1
        assert record["n_rows_not_explained"] == 0
        named = record["named_mechanisms"][SPOUSE_EXCESS_WITHHELD]
        assert named == {
            **named,
            "n_rows": 1,
            "n_rows_by_draw": {"0": 1},
            "n_rows_by_birth_year": {"1963": 1},
        }
        assert counters[WITHHELD_EXCESS] == 1
        assert counters[WITHHELD_EXCESS_NO_REFORM_BENEFIT] == 1
        _, _, workers_only = membership(
            built, base, reform, sid, WORKERS_ONLY_COMPONENTS
        )
        assert workers_only["n_rows_differ"] == 0
    # The same worker with a positive own level stays a recipient: the
    # reform withholds the excess (the named delta, counted) but membership
    # holds.
    positive = build(
        Household(
            Worker(1963, "di", 500.0, award_year=CANONICAL.subject.award_year),
            "married",
            CANONICAL.partner,
        )
    )
    base = people(positive, baseline_scenario())
    reform = people(
        positive,
        reform_scenario("P3", SurvivorRetirementAge.STATUTORY_MAPPING),
    )
    _, counters, record = membership(
        positive, base, reform, "P3", PRIMARY_COMPONENTS
    )
    assert record["n_rows_differ"] == 0
    assert counters[WITHHELD_EXCESS] == 1
    assert counters[WITHHELD_EXCESS_NO_REFORM_BENEFIT] == 0
    assert 0 < reform[SUBJECT].total < base[SUBJECT].total


def test_the_smallest_positive_own_level_keeps_membership():
    # The oracle floors the AIME to whole dollars and the PIA to dimes, so
    # the smallest positive own level at eligibility is $0.90 (90 percent
    # of $1), and dime-floored COLA increases never take it below that.  A
    # converted worker at that level stays a recipient in both scenarios:
    # the reform withholds the spouse's excess (counted) and membership
    # holds.  The named mechanism needs a zero level, not a small one.
    from populace_dynamics.ss.benefits import pia

    assert pia(0.0, 2025, BASE) == 0.0
    assert pia(1.0, 2025, BASE) == 0.9
    built = build(
        Household(
            Worker(1963, "di", 0.9, award_year=2018),
            "married",
            CANONICAL.partner,
        )
    )
    base = people(built, baseline_scenario())
    assert base[SUBJECT].own_kind == "converted"
    assert base[SUBJECT].components["retired_worker"] > 0
    for sid in ("P1", "P2", "P3"):
        reform = people(
            built,
            reform_scenario(sid, SurvivorRetirementAge.STATUTORY_MAPPING),
        )
        assert reform[SUBJECT].own_kind == "disabled"
        assert reform[SUBJECT].components["disabled_worker"] > 0
        assert "spouse" not in reform[SUBJECT].components
        _, counters, record = membership(
            built, base, reform, sid, PRIMARY_COMPONENTS
        )
        assert record["n_rows_differ"] == 0
        assert (
            record["named_mechanisms"][SPOUSE_EXCESS_WITHHELD]["n_rows"] == 0
        )
        assert counters[WITHHELD_EXCESS] == 1
        assert counters[WITHHELD_EXCESS_NO_REFORM_BENEFIT] == 0


def test_the_code_names_the_mechanism_e1_names():
    block = e1_parameter_block()
    assert block["membership"]["c0_named_mechanisms"] == list(
        C0_MEMBERSHIP_MECHANISMS
    )
    assert C0_MEMBERSHIP_MECHANISMS == (SPOUSE_EXCESS_WITHHELD,)


# --------------------------------------------------------------------------
# The classifier, condition by condition (INVENTED A7 rows)
# --------------------------------------------------------------------------
def _named_row(**changes):
    row = {
        "draw": 0,
        "person_id": 1,
        "birth_year": 1963,
        "basis": "projected",
        "own_kind_base": "converted",
        "own_kind_reform": "disabled",
        "benefit_components": {
            "retired_worker": {"base": 0.0, "reform": 0.0},
            "spouse": {"base": 12_000.0, "reform": 0.0},
            "disabled_worker": {"base": 0.0, "reform": 0.0},
        },
    }
    row.update(changes)
    return row


_DEFAULTS = {
    "components": PRIMARY_COMPONENTS,
    "recipient_base": True,
    "recipient_reform": False,
    "baseline_conversion_year": 2030,
    "reform_conversion_year": 2031,
    "reference_year": 2030,
}


def test_the_named_row_meets_every_condition():
    assert spouse_excess_withheld_until_reform_conversion(
        _named_row(), **_DEFAULTS
    )


@pytest.mark.parametrize(
    ("label", "row_changes", "arguments"),
    [
        (
            "reform-only recipient",
            {},
            {"recipient_base": False, "recipient_reform": True},
        ),
        ("recipient in both", {}, {"recipient_reform": True}),
        ("opening stock", {"basis": "opening_stock"}, {}),
        ("retired in both", {"own_kind_reform": "converted"}, {}),
        (
            "retired worker",
            {"own_kind_base": "retired", "own_kind_reform": "retired"},
            {},
        ),
        ("converted in both years", {}, {"reform_conversion_year": 2030}),
        ("not converted by 2030", {}, {"baseline_conversion_year": 2031}),
        ("workers only", {}, {"components": WORKERS_ONLY_COMPONENTS}),
        (
            "own level positive",
            {
                "benefit_components": {
                    "retired_worker": {"base": 120.0, "reform": 0.0},
                    "spouse": {"base": 12_000.0, "reform": 0.0},
                    "disabled_worker": {"base": 0.0, "reform": 120.0},
                }
            },
            {},
        ),
        (
            "no spouse's excess",
            {
                "benefit_components": {
                    "aged_widow": {"base": 900.0, "reform": 0.0},
                }
            },
            {},
        ),
        (
            "an excess the reform pays",
            {
                "benefit_components": {
                    "spouse": {"base": 12_000.0, "reform": 9_000.0},
                }
            },
            {},
        ),
    ],
)
def test_every_other_difference_is_not_explained(
    label, row_changes, arguments
):
    assert not spouse_excess_withheld_until_reform_conversion(
        _named_row(**row_changes), **{**_DEFAULTS, **arguments}
    ), label


def test_the_classification_counts_and_refuses_only_under_c0():
    rows = [
        _named_row(draw=0, person_id=1),
        _named_row(draw=1, person_id=1),
        _named_row(draw=1, person_id=2, basis="opening_stock"),
        {**_named_row(draw=1, person_id=3), "birth_year": 1970},
    ]
    flags = dict(
        recipient_base=[True, True, True, False],
        recipient_reform=[False, False, False, True],
        components=PRIMARY_COMPONENTS,
        baseline_params=BASE,
        reform_params=REFORMS["P3"],
        reference_year=REFERENCE,
        assumed_birth_month=BIRTH_MONTH,
    )
    c0 = classify_membership_differences(
        rows, claiming_response=ClaimingResponse.FIXED, **flags
    )
    record = c0["record"]
    assert record["n_rows_differ"] == 4
    assert record["n_rows_baseline_only"] == 3
    assert record["n_rows_reform_only"] == 1
    assert record["n_rows_not_explained"] == 2
    assert record["not_explained_allowed"] is False
    named = record["named_mechanisms"][SPOUSE_EXCESS_WITHHELD]
    assert named["n_rows"] == 2
    assert named["n_rows_by_draw"] == {"0": 1, "1": 1}
    assert c0["first_not_explained"] == {
        "draw": 1,
        "person_id": 2,
        "baseline_only": True,
    }
    # The record carries counts only: no person identifier, no amount.
    assert "person_id" not in repr(record)
    c2 = classify_membership_differences(
        rows, claiming_response=ClaimingResponse.ALL_DELAY, **flags
    )["record"]
    assert c2["not_explained_allowed"] is True
    assert c2["n_rows_not_explained"] == 2
    with pytest.raises(ValueError, match="one entry per A7 input row"):
        classify_membership_differences(
            rows[:2], claiming_response=ClaimingResponse.FIXED, **flags
        )


# --------------------------------------------------------------------------
# Properties over generated INVENTED households
# --------------------------------------------------------------------------
PROPERTY_SETTINGS = settings(
    max_examples=600, deadline=None, derandomize=True, database=None
)


@PROPERTY_SETTINGS
@given(households())
def test_c0_invariants_hold_for_every_invented_person(household):
    check_c0_invariants(household)


@settings(max_examples=400, deadline=None, derandomize=True, database=None)
@given(near_mechanism_households())
@example(CANONICAL)
@example(
    Household(
        Worker(1963, "di", 0.0, claim_year=2026, award_year=2029),
        "married",
        Worker(1963, "di", 1500.0, award_year=2016),
    )
)
@example(
    Household(
        Worker(1962, "di", 0.0, award_year=2015),
        "married",
        Worker(1960, "retired", 1500.0, claim_year=2022),
    )
)
@example(
    Household(
        Worker(1963, "di", 0.0, award_year=2018),
        "widowed",
        Worker(1958, "retired", 2100.0, claim_year=2021),
        2024,
    )
)
def test_c0_invariants_hold_at_and_around_the_named_mechanism(household):
    check_c0_invariants(household)


def check_c0_invariants(household: Household) -> None:
    """Invariants 1-4 of the module docstring for one household."""

    built = build(household)
    base = people(built, baseline_scenario())
    reforms = {
        label: people(built, reform_scenario(sid, survivors))
        for label, (sid, survivors) in C0_REFORMS.items()
    }
    alive = list(base)
    # 1. No individual benefit rises under C0.
    for label, reform in reforms.items():
        for pid in alive:
            assert reform[pid].total <= base[pid].total + TOLERANCE, (
                label,
                pid,
                household,
            )
    # 2. P2 <= P3 <= P1 <= baseline, person by person.
    for pid in alive:
        ordered = [
            reforms["F2 (P2)"][pid].total,
            reforms["F0 (P3)"][pid].total,
            reforms["F1 (P1)"][pid].total,
            base[pid].total,
        ]
        assert all(
            a <= b + TOLERANCE
            for a, b in zip(ordered, ordered[1:], strict=False)
        ), (pid, ordered, household)
    # 3. The null reform changes nothing, under every claiming response;
    # with Track A's fixed survivor span the baseline is Track A's own
    # calculator, bit for bit.
    for response in ClaimingResponse:
        null = people(
            built,
            Scenario(
                name="reform",
                params=BASE,
                baseline_params=BASE,
                claiming_response=response,
            ),
        )
        for pid in alive:
            assert null[pid].components == base[pid].components, response
    fixed = people(
        built, baseline_scenario(SurvivorRetirementAge.TRACK_A_FIXED_84)
    )
    track = track_benefits._Calculator(
        _context(built, BASE),
        TRACK_ROW,
        built.lookups,
        Counter(),
        copy.copy(built.cache),
    )
    for pid in alive:
        state = built.lookups.final.loc[pid]
        components, _ = track.projected_person(pid, state)
        assert fixed[pid].components == {
            name: value[0] for name, value in components.items()
        }, (pid, household)
    # 4. Memberships differ only through the named mechanism, and a person
    # meeting its definition is always one of those rows.
    expected = {pid for pid in alive if meets_the_definition(built, pid)}
    # Coverage of the generated households (hypothesis statistics).
    event(f"household: {household.marital}, subject {household.subject.kind}")
    event(f"persons meeting the named mechanism: {len(expected)}")
    for label, (sid, _survivors) in C0_REFORMS.items():
        for name, components in COMPONENT_SETS.items():
            rows, counters, record = membership(
                built, base, reforms[label], sid, components
            )
            if record is None:
                assert not expected
                continue
            assert record["n_rows_not_explained"] == 0, (
                label,
                name,
                record,
                household,
            )
            named = record["named_mechanisms"][SPOUSE_EXCESS_WITHHELD]
            if name == "workers_only":
                assert record["n_rows_differ"] == 0
                continue
            assert (
                named["n_rows"] == record["n_rows_differ"] == len(expected)
            ), (label, record, household)
            assert counters[WITHHELD_EXCESS_NO_REFORM_BENEFIT] == len(expected)
            for row in rows:
                if row["person_id"] in expected:
                    assert row["beneficiary_base"]
                    assert not row["beneficiary_reform"]


def test_the_specification_check_binds_the_named_mechanisms():
    # A block naming no mechanism (e1-ratified-1's guard), or another one,
    # describes a different C0 guard: the check names the mismatch and a
    # registered run refuses it.
    from populace_dynamics.fra68_track.runner import (
        check_specification_for_registered_run,
        specification_code_check,
    )

    block = e1_parameter_block()
    assert specification_code_check(block, FRA68Config())["consistent"]
    for membership_block in (
        {
            k: v
            for k, v in block["membership"].items()
            if k != "c0_named_mechanisms"
        },
        {**block["membership"], "c0_named_mechanisms": []},
        {**block["membership"], "c0_named_mechanisms": ["another"]},
    ):
        edited = {**block, "membership": membership_block}
        check = specification_code_check(edited, FRA68Config())
        assert check["mismatches"] == ["membership.c0_named_mechanisms"]
        with pytest.raises(ValueError, match="c0_named_mechanisms"):
            check_specification_for_registered_run(edited, FRA68Config())
    without = {k: v for k, v in block.items() if k != "membership"}
    assert specification_code_check(without, FRA68Config())["mismatches"] == [
        "membership.c0_named_mechanisms"
    ]


def test_e1_names_the_mechanism_its_counters_and_the_section_19_case():
    # E1 (e1-ratified-2) names the mechanism, its counters and the record
    # in section 12, admits it in section 7, and states the section 19
    # invented case that test_the_canonical_case_is_the_named_mechanism
    # computes.
    from populace_dynamics.fra68_track.runner import E1_SPECIFICATION_PATH

    text = E1_SPECIFICATION_PATH.read_text(encoding="utf-8")

    def section(heading):
        start = text.index(heading)
        end = text.find("\n## ", start + len(heading))
        return " ".join(text[start:end].split())

    twelve = section("## 12. Named omitted deltas")
    for name in (
        SPOUSE_EXCESS_WITHHELD,
        WITHHELD_EXCESS,
        WITHHELD_EXCESS_NO_REFORM_BENEFIT,
        "membership_differences",
    ):
        assert f"`{name}" in twelve, name
    seven = section("## 7. Statistic")
    assert "Membership under C0" in seven
    assert "refuses the run if a C0 row has any row not explained" in seven
    assert "before any row is tabulated" in seven
    nineteen = section("## 19. Invented worked cases")
    subject, partner = CANONICAL.subject, CANONICAL.partner
    assert (
        f"born {subject.birth}, awarded DI in {subject.award_year} with a "
        "zero disclosed level, married to a worker born "
        f"{partner.birth} who claimed at {partner.claim_year - partner.birth}"
        f" in {partner.claim_year} with PIA ${partner.level:,.2f}"
    ) in nineteen
    assert "With an own level of $500.00" in nineteen
    twenty_seven = section(
        "## 27. Registration 14's refusal and the C0 membership amendment"
    )
    assert (
        "deb294013f98295b2a43f742d8c0e3cd61fa8b39bd5453f3d1745a790b983067"
        in twenty_seven
    )
    assert "before any statistic was recorded, printed or seen" in (
        twenty_seven
    )
