"""Seeded status stress on invented declarations in plain arithmetic.

Verification class: statutory conformance; no population, behavioral or
forecast claim. This widens tests/test_track_b_insured_status_status_oracle.py
and calls only public declaration and result APIs. Its arithmetic imports no
production quarter, assignment, clock, requirement, witness or period helper.

Space: women born 1940-1979, aged 31-58 at onset, onset from 1992, where Rule
I (20/40) or blindness applies. Endings, queries, annual totals with at most
four partial years, no prior, a clear prior or an overlapping prior, and
blindness in a quarter of cases all vary by seed. A second generator adds a
DIB entitlement month, which ends a CURRENTLY window before the onset. A third
draws ages 22-30 at onset, where 404.130(c) applies. A fourth declares a
special-insured prior after age 31, where 404.130(d) applies. Declared priors
are not re-adjudicated. No flags, raw earnings or death are claimed, and
UNKNOWN facts appear only in ``check_unknown_ending`` and
``check_every_history``.

Every annual placement and both all-prior treatments are enumerated. A lawful
filling has its own first insured start (404.321(a)), and that start supplies
the current period for FULLY, CURRENTLY and the date last insured. Each
returned status must equal the favorable Boolean over lawful fillings
(RS 00301.230), and a true status must hold on a filling whose first start is
the reported start. Each exact count, assignment and date last insured must
also be the best a filling with that start attains. A rejection needs no
lawful filling. A named refusal retains the declaration and passes.
"""

import calendar
import random
from datetime import date, timedelta
from itertools import combinations, product

import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as rule
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput

# Seeds whose first start moved with placement. Round 14 answered each one
# from a start and a status that no single filling supports.
SPLIT_SEEDS = (
    102037,
    102202,
    103045,
    103702,
    105793,
    109597,
    110777,
    203310,
    207027,
    207682,
    209481,
    209505,
    212010,
)


def quarter(day):
    return day.year * 4 + (day.month - 1) // 3


def usable(credits, at, periods):
    """404.146(d): retain credited endpoints, remove strict interiors."""
    return {
        credit
        for credit in credits
        if credit <= at
        and not any(quarter(a) < credit < quarter(b) for a, b in periods)
    }


def requirement(birth, at_year, periods):
    first = max(1951, birth.year + 21 + 1)
    last = min(at_year, birth.year + 62)
    elapsed = sum(
        not any(a.year <= year <= b.year for a, b in periods)
        for year in range(first, last)
    )
    return max(6, min(40, elapsed))


def recent(use, at, periods, length):
    """404.130(f): count back, keeping credited endpoint quarters."""
    seen = count = 0
    cursor = at
    while seen < length:
        excluded = any(
            quarter(a) <= cursor <= quarter(b) and cursor not in use
            for a, b in periods
        )
        if not excluded:
            seen += 1
            count += cursor in use
        cursor -= 1
    return count


LAST_40, WHOLE_PERIOD = READINGS = ("last_40", "whole_period")


def under_31(birth, use, at, periods, special=False, reading=LAST_40):
    """404.130(c), (d): half the quarters after age 21, or 6 of 12.

    Past 40 counted quarters the Act's clause (iii) and 404.130(d)(2) part
    ways (source conflict us:oasdi-insured-subsequent-special-long-period).
    A computed result has to hold on both readings.
    """
    attained_21 = quarter(date(birth.year + 21, birth.month, birth.day))
    if not special and at >= quarter(
        date(birth.year + 31, birth.month, birth.day)
    ):
        return False
    elapsed = [
        candidate
        for candidate in range(attained_21 + 1, at + 1)
        if not any(
            quarter(a) <= candidate <= quarter(b) and candidate not in use
            for a, b in periods
        )
    ]
    if len(elapsed) < 12:
        return recent(use, at, periods, 12) >= 6
    if len(elapsed) > 40 and reading == WHOLE_PERIOD:
        held = sum(candidate in use for candidate in elapsed)
        return held >= len(elapsed) // 2
    credited = sum(candidate in use for candidate in elapsed[-40:])
    return credited >= max(6, min(len(elapsed), 40) // 2)


def disability(
    birth, credits, at, periods, blind, special=False, reading=LAST_40
):
    use = usable(credits, at, periods)
    fully = len(use) >= requirement(birth, at // 4, periods)
    return fully and (
        blind
        or recent(use, at, periods, 40) >= 20
        or under_31(birth, use, at, periods, special, reading)
    )


def last_insured(birth, credits, at, periods, blind, special, reading):
    """Latest quarter through the query that insures a potential onset."""
    return max(
        (
            candidate
            for candidate in range(min(credits, default=at), at + 1)
            if disability(
                birth, credits, candidate, periods, blind, special, reading
            )
        ),
        default=None,
    )


def placements(annual):
    options = [
        tuple(combinations(range(year * 4, year * 4 + 4), count))
        for year, count in annual.items()
    ]
    for pieces in product(*options):
        yield frozenset(credit for piece in pieces for credit in piece)


def lawful_fillings(case, reading=LAST_40):
    """Exhaust every filling before comparing to a public result.

    Each lawful filling gives its first start, three statuses, the best
    (insured, margin, count) for FULLY and CURRENTLY, its date last insured
    quarter and its credits.
    """
    birth, onset, ending, month = (
        case["birth"],
        case["onset"],
        case["ending"],
        case["month"],
    )
    blind, prior, annual = case["blind"], case["prior"], case["annual"]
    special = case.get("special", False)
    at = quarter(month)
    events = [
        event for event in (case.get("entitlement"),) if event is not None
    ] or [month]
    found = []
    for credits in placements(annual):
        for use_prior in (True, False) if prior else (False,):
            used = prior if use_prior else ()
            first = next(
                (
                    candidate
                    for candidate in range(quarter(onset), quarter(ending) + 1)
                    if disability(
                        birth,
                        credits,
                        candidate,
                        used,
                        blind,
                        special,
                        reading,
                    )
                ),
                None,
            )
            if first is None or any(
                quarter(a) <= first <= quarter(b) for a, b in prior
            ):
                continue
            year, q = divmod(first, 4)
            start = (
                onset if first == quarter(onset) else date(year, 3 * q + 1, 1)
            )
            fully_best = currently_best = (False, -99, -1)
            latest = None
            for periods in (prior + ((start, ending),), ()):
                use = usable(credits, at, periods)
                needed = requirement(birth, month.year, periods)
                fully_best = max(
                    fully_best,
                    (len(use) >= needed, len(use) - needed, len(use)),
                )
                for event in events:
                    held = recent(
                        usable(credits, quarter(event), periods),
                        quarter(event),
                        periods,
                        13,
                    )
                    currently_best = max(
                        currently_best, (held >= 6, held - 6, held)
                    )
                latest = max(
                    filter(
                        None,
                        (
                            latest,
                            last_insured(
                                birth,
                                credits,
                                at,
                                periods,
                                blind,
                                special,
                                reading,
                            ),
                        ),
                    ),
                    default=None,
                )
            found.append(
                (
                    first,
                    fully_best[0],
                    currently_best[0],
                    any(
                        disability(
                            birth,
                            credits,
                            candidate,
                            used,
                            blind,
                            special,
                            reading,
                        )
                        for candidate in range(quarter(onset), at + 1)
                    ),
                    fully_best,
                    currently_best,
                    latest,
                    credits,
                )
            )
    return found


def public(case, **options):
    observed = rule.EarningsProvenance.OBSERVED
    unknown_end = case.get("unknown_end", False)
    unknown_prior = case.get("unknown_prior", False)
    person = rule.Person(
        case["birth"],
        sex=rule.Sex.FEMALE,
        statutory_blindness=case["blind"],
        disability_onset=case["onset"],
        current_disability_period_established=True,
        current_disability_period_provenance=observed,
        current_disability_period_end=(
            None if unknown_end else case["ending"]
        ),
        current_disability_period_end_provenance=(
            rule.EarningsProvenance.UNKNOWN if unknown_end else observed
        ),
        prior_disability_periods=tuple(
            rule.DisabilityPeriod(
                a, b, special_insured=case.get("special", False)
            )
            for a, b in case["prior"]
        ),
        prior_disability_periods_provenance=(
            rule.EarningsProvenance.UNKNOWN if unknown_prior else observed
        ),
        sspa211_applies=False,
        sspa211_provenance=observed,
        dib_entitlement_month=case.get("entitlement"),
    )
    years = {
        year: (
            rule.CoverageYear(observed, qc_count=case["annual"].get(year, 0))
            if year >= 1978
            else rule.CoverageYear(observed, qc_quarters=(False,) * 4)
        )
        for year in range(case["birth"].year, case["month"].year + 1)
    }
    return rule.insured_status(person, years, case["month"], **options)


def declaration(seed):
    draw = random.Random(seed)
    birth = date(draw.randint(1940, 1975), 2, 2)
    year = birth.year + draw.randint(31, 58)
    if year < 1992:
        year = draw.randint(1992, 2010)
    if not 31 <= year - birth.year <= 58:
        birth = date(year - draw.randint(31, 58), 2, 2)
    onset = date(year, draw.choice((1, 2, 3, 4, 5, 7, 8, 10, 11, 12)), 15)
    ending_year = year + draw.choice((0, 0, 1, 2, 3))
    ending_month = draw.randint(12 if ending_year == year else 1, 12)
    ending = date(
        ending_year,
        ending_month,
        calendar.monthrange(ending_year, ending_month)[1],
    )
    if draw.random() < 0.3:
        ending = date(ending_year, 12, 31)
    month = date(ending.year + draw.choice((1, 1, 2, 4, 9)), 1, 1)
    if month.year - birth.year > 62:
        month = date(ending.year + 1, 1, 1)
    annual = {}
    span = draw.randint(5, 16)
    density = draw.choice((0.5, 0.7, 0.85, 1.0))
    first = max(1978, year - span)
    for credited in range(first, year):
        if draw.random() < density:
            annual[credited] = 4
    for credited in draw.sample(range(first, ending.year + 1), k=3):
        annual[credited] = draw.randint(1, 3)
    if draw.random() < 0.5:
        annual[year] = draw.randint(1, 3)
    for credited in range(year + 1, month.year):
        if draw.random() < 0.3:
            annual[credited] = draw.randint(0, 4)
    annual = {y: n for y, n in annual.items() if n and y < month.year}
    for credited in [y for y, n in annual.items() if n < 4][4:]:
        annual[credited] = 4
    kind = draw.choice(("none", "clear", "overlap", "overlap"))
    prior = ()
    if kind != "none":
        begins = date(year - draw.randint(1, 4), draw.choice((1, 4, 7, 10)), 1)
        if kind == "clear":
            ends = date(year - 1, 12, 31)
            if begins < ends:
                prior = ((begins, ends),)
        elif onset.month % 3 != 1:
            first_day = date(year, 3 * ((onset.month - 1) // 3) + 1, 1)
            ends = first_day + timedelta(days=draw.randint(0, 20))
            if ends < onset:
                prior = ((begins, ends),)
    return {
        "birth": birth,
        "onset": onset,
        "ending": ending,
        "month": month,
        "blind": draw.random() < 0.25,
        "prior": prior,
        "annual": annual,
    }


def with_entitlement(seed):
    """Date a DIB entitlement in a partial year up to the onset, mostly."""
    case = declaration(seed)
    draw = random.Random(f"entitlement-{seed}")
    onset_year = case["onset"].year
    partial = [
        year
        for year, count in case["annual"].items()
        if count < 4 and year <= onset_year
    ]
    if partial and draw.random() < 0.8:
        year = draw.choice(partial)
    else:
        year = draw.randint(onset_year - 12, onset_year)
    case["entitlement"] = date(
        year, draw.choice((1, 2, 4, 5, 7, 8, 10, 11)), 1
    )
    return case


def under_31_declaration(seed):
    draw = random.Random(f"under-31-{seed}")
    # Onset from 1981 keeps every ending past 404.321(b)'s implied recovery.
    birth = date(draw.randint(1959, 1985), 2, 2)
    year = birth.year + draw.randint(22, 30)
    onset = date(year, draw.choice((1, 2, 3, 4, 5, 7, 8, 10, 11, 12)), 15)
    ending_year = year + draw.choice((1, 2, 3))
    ending_month = draw.randint(1, 12)
    ending = date(
        ending_year,
        ending_month,
        calendar.monthrange(ending_year, ending_month)[1],
    )
    month = date(ending.year + draw.choice((1, 1, 2, 4)), 1, 1)
    annual = {}
    for credited in range(max(1978, birth.year + 16), year + 1):
        if draw.random() < 0.8:
            annual[credited] = draw.choice((1, 2, 3, 3, 4, 4))
    for credited in range(year + 1, month.year):
        if draw.random() < 0.25:
            annual[credited] = draw.randint(1, 4)
    for credited in [y for y, n in annual.items() if n < 4][4:]:
        annual[credited] = 4
    return {
        "birth": birth,
        "onset": onset,
        "ending": ending,
        "month": month,
        "blind": False,
        "prior": (),
        "annual": annual,
    }


def subsequent_declaration(seed):
    """Declare a special-insured prior before 31, and an onset after it.

    The special prior opens 404.130(d) at the later onset.
    """
    case = declaration(seed)
    draw = random.Random(f"subsequent-{seed}")
    onset = case["onset"]
    birth = date(onset.year - draw.randint(32, 40), 2, 2)
    begins = date(birth.year + draw.randint(24, 30), 7, 1)
    ends = date(begins.year + draw.randint(0, 1), 12, 31)
    case.update(birth=birth, prior=((begins, ends),), special=True)
    return case


def check_diagnostics(case, result, fillings):
    """Every exact diagnostic must belong to the reported start."""
    start = quarter(result.current_disability_period_start)
    own = [filling for filling in fillings if filling[0] == start]
    for name, position in (("fully", 4), ("currently", 5)):
        decision = getattr(result, name)
        count = decision.qc_count_upper
        score = (decision.insured, count - decision.required, count)
        assert decision.qc_count_lower == count, (case, name, result)
        assert score == max(filling[position] for filling in own), (
            case,
            name,
            score,
            result,
        )
        assert any(
            filling[position] == score
            and set(decision.assigned_quarters) <= filling[7]
            for filling in own
        ), (case, name, decision)
    assigned = {
        credit
        for quarters in result.assigned_quarters.values()
        for credit in quarters
    }
    assert any(assigned <= filling[7] for filling in own), (case, assigned)
    for year, quarters in result.assigned_quarters.items():
        assert result.qcs_by_year[year] == (len(quarters), len(quarters)), (
            case,
            year,
            result,
        )
    upper = result.dli.upper
    assert (None if upper is None else quarter(upper)) == max(
        filling[6] for filling in own
    ), (case, upper, own)


def check(case):
    worlds = tuple(
        lawful_fillings(case, reading)
        for reading in (READINGS if case.get("special") else READINGS[:1])
    )
    try:
        result = public(case)
    except rule.InsuredConfigurationUnsupported:
        return "refused"
    except InvalidFamilyInput as error:
        assert not any(worlds), (case, error)
        return "invalid"
    actual = tuple(
        getattr(result, name).insured
        for name in ("fully", "currently", "disability")
    )
    start = quarter(result.current_disability_period_start)
    for fillings in worlds:
        assert fillings, (case, "computed an impossible start", result)
        expected = tuple(
            any(filling[index] for filling in fillings) for index in (1, 2, 3)
        )
        assert actual == expected, (case, actual, expected, result)
        for index, insured in enumerate(actual, 1):
            assert not insured or any(
                filling[0] == start and filling[index] for filling in fillings
            ), (case, actual, start, fillings)
        check_diagnostics(case, result, fillings)
    return "computed"


def quarter_end(value):
    year, number = divmod(value, 4)
    month = 3 * number + 3
    return date(year, month, calendar.monthrange(year, month)[1])


def check_unknown_ending(case, unknown_prior=False):
    """Each ending's best date on the reported start must fit the range.

    UNKNOWN priors include the completion with none, which ``case`` then
    declares, so its dates must also fit, though the upper end only bounds them.
    """
    try:
        result = public(
            {**case, "unknown_end": True, "unknown_prior": unknown_prior},
            test=rule.InsuredTest.DISABILITY,
        )
    except rule.InsuredConfigurationUnsupported:
        return "refused"
    except InvalidFamilyInput:
        return "invalid"
    if result.current_disability_period_start is None:
        return "no start"
    start = quarter(result.current_disability_period_start)
    endings = [
        quarter_end(candidate)
        for candidate in range(start, quarter(case["month"]) + 1)
    ]
    best = []
    for ending in (*endings, date(case["birth"].year + 70, 12, 31)):
        own = [
            filling[6]
            for filling in lawful_fillings({**case, "ending": ending})
            if filling[0] == start
        ]
        assert own or unknown_prior, (case, ending, result)
        if own:
            best.append(max(-1 if found is None else found for found in own))
    if not best:
        return "no filling"
    lower, upper = result.dli.lower, result.dli.upper
    assert (-1 if lower is None else quarter(lower)) <= min(best), (
        case,
        best,
        result.dli,
    )
    if unknown_prior:
        assert upper is None or quarter(upper) >= max(best), (
            case,
            best,
            result.dli,
        )
    else:
        assert (-1 if upper is None else quarter(upper)) == max(best), (
            case,
            best,
            result.dli,
        )
    return "computed"


DISABILITY = rule.InsuredTest.DISABILITY
CURRENTLY = rule.InsuredTest.CURRENTLY
EDGE_ANNUAL = {
    1995: 3,
    1996: 4,
    1997: 4,
    1998: 4,
    1999: 4,
    2000: 1,
}
# The quarters through 2010Q1 hold 20 QCs only with the 2000 QC after 2000Q1,
# and the start holds it there. The current period lifts the date back.
FREEZE_DATE = {
    "birth": date(1960, 2, 2),
    "onset": date(2000, 1, 1),
    "ending": date(2007, 12, 31),
    "month": date(2010, 1, 1),
    "blind": False,
    "prior": (),
    "annual": {
        **EDGE_ANNUAL,
        2001: 4,
        2002: 4,
        2003: 4,
        2004: 4,
        2005: 3,
    },
}
# The 13 quarters through 2003Q2 hold six QCs only with the 2000 QC after
# 2000Q1. The current period lifts the status back, and a prior over 1996 to
# 1999 takes that lift away.
FREEZE_STATUS = {
    "birth": date(1970, 2, 2),
    "onset": date(2000, 1, 1),
    "ending": date(2002, 12, 31),
    "month": date(2003, 4, 1),
    "blind": False,
    "prior": (),
    "annual": {
        1986: 4,
        1987: 4,
        1992: 1,
        1996: 4,
        1997: 4,
        1998: 4,
        1999: 4,
        2000: 1,
        2001: 4,
        2002: 1,
    },
}


def added_priors(case):
    """Undeclared priors that end before the onset, each past five months."""
    year = case["onset"].year
    return tuple(
        ((date(year - back, month, 1), date(year - 1, 12, 31)),)
        for back, month in ((1, 4), (2, 1), (4, 1))
    )


def prior_can_begin(case, credits, periods):
    """404.130(a), (e): even a blind prior begins fully insured."""
    return all(
        disability(case["birth"], credits, quarter(begins), (), True)
        for begins, _ in periods
    )


def history_fillings(case, added, start, ending):
    """Fillings with the reported start on a history holding ``added``."""
    return [
        filling
        for filling in lawful_fillings(
            {**case, "prior": added, "ending": ending}
        )
        if filling[0] == start and prior_can_begin(case, filling[7], added)
    ]


def check_every_history(case, unknown_end=False, test=rule.InsuredTest.ALL):
    """No lawful prior history may undercut a computed result.

    UNKNOWN priors stand for each history below, so a filling with the
    reported start has to hold each true status and reach the lower date on
    it, whichever period ending the record has.
    """
    try:
        result = public(
            {**case, "unknown_end": unknown_end, "unknown_prior": True},
            test=test,
        )
    except rule.InsuredConfigurationUnsupported:
        return "refused"
    except InvalidFamilyInput:
        return "invalid"
    if result.current_disability_period_start is None:
        return "no start"
    start = quarter(result.current_disability_period_start)
    endings = (case["ending"],)
    if unknown_end:
        endings = (
            quarter_end(start),
            quarter_end(quarter(case["month"])),
            date(case["birth"].year + 70, 12, 31),
        )
    fully, currently = result.fully, result.currently
    lower = None if result.dli is None else result.dli.lower
    for added in added_priors(case):
        for ending in endings:
            held = history_fillings(case, added, start, ending)
            if not held:
                continue
            found = (case, added, ending, result)
            assert (
                fully is None
                or not fully.insured
                or any(filling[1] for filling in held)
            ), found
            assert (
                currently is None
                or not currently.insured
                or any(filling[2] for filling in held)
            ), found
            assert lower is None or quarter(lower) <= max(
                -1 if filling[6] is None else filling[6] for filling in held
            ), found
    return "computed"


def start_edge_declaration(seed):
    """A record whose start needs the next QC, with its tail redrawn.

    Each draw keeps the QCs that put the start at the edge, and moves the
    last QCs, the ending and the query around the record's own boundary.
    """
    draw = random.Random(seed)
    case = draw.choice((FREEZE_DATE, FREEZE_STATUS))
    annual = dict(case["annual"])
    last = max(annual)
    annual[last] = draw.randint(max(annual[last] - 1, 0), 4)
    annual[last - 1] = draw.randint(max(annual[last - 1] - 1, 0), 4)
    month = date(
        case["month"].year + draw.randint(-1, 1),
        draw.choice((1, 4, 7, 10)),
        1,
    )
    ending = date(case["ending"].year + draw.randint(-1, 0), 12, 31)
    return {
        **case,
        "ending": ending,
        "month": month,
        "annual": {y: n for y, n in annual.items() if n and y <= month.year},
    }


@pytest.mark.parametrize("seed", (5000026, 5000168))
def test_status_stress_year_counts_follow_the_returned_filling(seed):
    # The start's witness leaves a prior's interior holding a year's QCs.
    assert check(declaration(seed)) == "computed"


@pytest.mark.parametrize("seed", (5000005, 5000019))
def test_status_stress_candidate_order_changes_nothing(seed, monkeypatch):
    forward = public(declaration(seed))
    candidates = rule._assignment_candidates
    monkeypatch.setattr(
        rule,
        "_assignment_candidates",
        lambda *row: tuple(reversed(tuple(candidates(*row)))),
    )
    backward = public(declaration(seed))
    assert dict(backward.assigned_quarters) == dict(forward.assigned_quarters)
    assert dict(backward.qcs_by_year) == dict(forward.qcs_by_year)


def test_status_stress_returned_filling_keeps_credited_endpoints():
    # 2016 holds three QCs inside a current period, and its two endpoints
    # credit two of them wherever the third falls.
    assert public(declaration(5000133)).qcs_by_year[2016] == (2, 2)


@pytest.mark.parametrize("seed", SPLIT_SEEDS)
def test_status_stress_refuses_a_start_no_filling_supports(seed):
    with pytest.raises(rule.InsuredConfigurationUnsupported) as error:
        public(declaration(seed))
    assert (
        error.value.reason
        is rule.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY
    )


@settings(max_examples=120, deadline=None, derandomize=True)
@example(seed=103702)
@example(seed=207682)
@given(seed=st.integers(0, 2**32 - 1))
def test_status_stress_matches_the_favorable_filling(seed):
    check(declaration(seed))


@settings(max_examples=120, deadline=None, derandomize=True)
@given(seed=st.integers(0, 2**32 - 1))
def test_status_stress_with_an_entitlement_month(seed):
    check(with_entitlement(seed))


@settings(max_examples=120, deadline=None, derandomize=True)
@given(seed=st.integers(0, 2**32 - 1))
def test_status_stress_under_31(seed):
    check(under_31_declaration(seed))


@settings(max_examples=120, deadline=None, derandomize=True)
@given(seed=st.integers(0, 2**32 - 1))
def test_status_stress_subsequent_special(seed):
    check(subsequent_declaration(seed))


def test_status_stress_a_lower_date_rests_on_the_reported_start():
    # A 2005Q4 ending reaches 2009Q4 and no later on the 2000Q1 start.
    case = {
        "birth": date(1960, 2, 2),
        "onset": date(2000, 1, 1),
        "ending": date(2005, 12, 31),
        "month": date(2010, 1, 1),
        "blind": False,
        "prior": (),
        "annual": {
            1995: 3,
            1996: 4,
            1997: 4,
            1998: 4,
            1999: 4,
            2000: 1,
            2001: 4,
            2002: 4,
            2003: 4,
            2004: 4,
            2005: 3,
        },
    }
    assert check_unknown_ending(case) == "refused"


@settings(max_examples=40, deadline=None, derandomize=True)
@given(seed=st.integers(0, 2**32 - 1))
def test_status_stress_unknown_ending(seed):
    case = declaration(seed)
    check_unknown_ending({**case, "month": date(case["onset"].year + 2, 1, 1)})


@settings(max_examples=40, deadline=None, derandomize=True)
@given(seed=st.integers(0, 2**32 - 1))
def test_status_stress_unknown_ending_and_prior(seed):
    case = {**declaration(seed), "prior": ()}
    check_unknown_ending(
        {**case, "month": date(case["onset"].year + 2, 1, 1)},
        unknown_prior=True,
    )


@pytest.mark.parametrize("unknown_end", (False, True))
def test_status_stress_an_added_prior_undercuts_the_freeze(unknown_end):
    date_case = check_every_history(FREEZE_DATE, unknown_end, DISABILITY)
    status_case = check_every_history(FREEZE_STATUS, unknown_end, CURRENTLY)
    assert (date_case, status_case) == ("refused", "refused")


def test_status_stress_a_date_with_no_period_in_force_holds_every_history():
    annual = {**FREEZE_DATE["annual"], 2005: 4}
    case = {**FREEZE_DATE, "annual": annual}
    assert check_every_history(case, test=DISABILITY) == "computed"


def test_status_stress_a_status_with_no_period_in_force_holds_every_history():
    annual = {**FREEZE_STATUS["annual"], 2002: 2}
    case = {**FREEZE_STATUS, "annual": annual}
    assert check_every_history(case, test=CURRENTLY) == "computed"


def test_status_stress_the_exact_date_on_that_history():
    # Each of the 16 placements with the 2000Q1 start falls to 2009Q4.
    added = ((date(1999, 4, 1), date(1999, 12, 31)),)
    held = history_fillings(
        FREEZE_DATE,
        added,
        quarter(FREEZE_DATE["onset"]),
        FREEZE_DATE["ending"],
    )
    assert len({filling[7] for filling in held}) == 16
    assert {filling[6] for filling in held} == {quarter(date(2009, 12, 31))}


def test_status_stress_the_status_on_that_history():
    held = history_fillings(
        FREEZE_STATUS,
        ((date(1996, 1, 1), date(1999, 12, 31)),),
        quarter(FREEZE_STATUS["onset"]),
        FREEZE_STATUS["ending"],
    )
    assert held
    assert not any(filling[2] for filling in held)


@settings(max_examples=30, deadline=None, derandomize=True)
@given(
    seed=st.integers(0, 2**32 - 1),
    unknown_end=st.booleans(),
    test=st.sampled_from((rule.InsuredTest.ALL, DISABILITY, CURRENTLY)),
)
def test_status_stress_every_history_at_the_start_edge(
    seed, unknown_end, test
):
    check_every_history(start_edge_declaration(seed), unknown_end, test)


@settings(max_examples=20, deadline=None, derandomize=True)
@given(
    seed=st.integers(0, 2**32 - 1),
    unknown_end=st.booleans(),
    test=st.sampled_from((rule.InsuredTest.ALL, DISABILITY, CURRENTLY)),
)
def test_status_stress_every_history(seed, unknown_end, test):
    case = {**declaration(seed), "prior": ()}
    assume(sum(1 for _ in placements(case["annual"])) <= 96)
    check_every_history(case, unknown_end, test)
