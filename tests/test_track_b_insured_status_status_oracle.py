"""Independent bounded status-completion oracle on invented declarations.

Verification class: statutory conformance; no population, behavioral or
forecast claim. This oracle calls only public declaration and result APIs.
Its arithmetic does not import production quarter, assignment, clock,
requirement, witness or period-construction helpers.

Space: women born February 2, 1960, ordinary or blind; no flags, no prior
or one known nonspecial prior, known current ending, and annual direct QCs
in 1990, 1995-2000 and 2002. The claiming-age variant adds four QCs in each
of 2003-2006. Every annual placement and both all-prior treatments are
enumerated. At most 576 placements, two establishment treatments and two
status treatments occur per declaration. Queries include the year after
the ending, four years after it and claiming age 62. No UNKNOWN earnings,
unknown periods, pre1978 credits, male transition, subsequent-special,
pre1956 alternate, death, continuing or unknown ending is claimed.

Act 214(a), 223(c), 20 CFR 404.110(c), 404.130(a),(e),(f), 404.131,
404.143(b), 404.146(d) and 404.321(a) supply the arithmetic. Annual QCs
are assigned favorably (RS 00301.230). A lawful filling has its own first
insured start; that start supplies the current period for FULLY and
CURRENTLY. DISABILITY must qualify without using the period it establishes.
Each returned status must equal the favorable Boolean over all lawful
fillings. Each exact count, assignment and date last insured must be the best
a filling with the reported first start attains. A named refusal retains the
declaration and passes the oracle.
"""

from dataclasses import dataclass
from datetime import date
from functools import cache
from itertools import combinations, product

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as rule
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput


@dataclass(frozen=True)
class Declaration:
    blind: bool = False
    prior: str = "overlap"
    prior_count: int = 2
    onset_count: int = 1
    query: str = "later"

    @property
    def month(self):
        return {
            "after": date(2003, 1, 1),
            "later": date(2006, 1, 1),
            "claiming": date(2022, 3, 1),
        }[self.query]

    @property
    def annual(self):
        counts = {
            1990: 1,
            1995: 4,
            1996: 4,
            1997: 4,
            1998: 4,
            1999: self.prior_count,
            2000: self.onset_count,
            2002: 1,
        }
        if self.query == "claiming":
            counts.update(dict.fromkeys(range(2003, 2007), 4))
        return counts

    @property
    def periods(self):
        if self.prior == "none":
            return ()
        end = date(1999, 12, 31)
        if self.prior == "overlap":
            end = date(2000, 1, 31)
        return ((date(1999, 1, 1), end),)


def quarter(day):
    return day.year * 4 + (day.month - 1) // 3


def _usable(credits, at, periods):
    """404.146(d): retain credited endpoints, remove strict interiors."""
    return {
        credit
        for credit in credits
        if credit <= at
        and not any(quarter(a) < credit < quarter(b) for a, b in periods)
    }


def _fully_requirement(at, periods):
    # February 2, 1960 attains 21 in 1981 and 62 in 2022.
    elapsed = sum(
        not any(a.year <= year <= b.year for a, b in periods)
        for year in range(1982, min(at // 4, 2022))
    )
    return max(6, min(40, elapsed))


def _recent(usable, at, periods, length):
    """404.130(f): count back, keeping credited endpoint quarters."""
    seen = count = 0
    cursor = at
    while seen < length:
        excluded = any(
            quarter(a) <= cursor <= quarter(b) and cursor not in usable
            for a, b in periods
        )
        if not excluded:
            seen += 1
            count += cursor in usable
        cursor -= 1
    return count


def _disability(credits, at, periods, blind):
    usable = _usable(credits, at, periods)
    fully = len(usable) >= _fully_requirement(at, periods)
    return fully and (blind or _recent(usable, at, periods, 40) >= 20)


def _all_placements(annual):
    options = [
        tuple(combinations(range(year * 4, year * 4 + 4), count))
        for year, count in annual.items()
    ]
    for pieces in product(*options):
        yield frozenset(credit for piece in pieces for credit in piece)


@cache
def favorable_statuses(case):
    """Exhaust every filling before comparing to a public result."""
    answer = [False, False, False]
    lawful = 0
    starts = set()
    own = {}
    onset = date(2000, 2, 15)
    ending = date(2002, 12, 31)
    at = quarter(case.month)
    for credits in _all_placements(case.annual):
        # A declared nonspecial prior can rest on historical blindness.
        # Here even its unexcluded ordinary fully requirement is met.
        if case.periods and not _disability(
            credits, quarter(case.periods[0][0]), (), True
        ):
            continue
        treatments = (True, False) if case.periods else (False,)
        for use_prior in treatments:
            establishment_periods = case.periods if use_prior else ()
            first = next(
                (
                    candidate
                    for candidate in range(quarter(onset), quarter(ending) + 1)
                    if _disability(
                        credits, candidate, establishment_periods, case.blind
                    )
                ),
                None,
            )
            if first is None or any(
                quarter(a) <= first <= quarter(b) for a, b in case.periods
            ):
                continue
            lawful += 1
            starts.add(first)
            year, q = divmod(first, 4)
            start = (
                onset if first == quarter(onset) else date(year, 3 * q + 1, 1)
            )
            completed = case.periods + ((start, ending),)
            best = own.setdefault(
                first,
                {"fully": (False, -99, -1), "currently": (False, -99, -1)},
            )
            best.setdefault("fillings", []).append(credits)
            for status_periods in (completed, ()):
                usable = _usable(credits, at, status_periods)
                needed = _fully_requirement(at, status_periods)
                held = _recent(usable, at, status_periods, 13)
                answer[0] |= len(usable) >= needed
                answer[1] |= held >= 6
                best["fully"] = max(
                    best["fully"],
                    (len(usable) >= needed, len(usable) - needed, len(usable)),
                )
                best["currently"] = max(
                    best["currently"], (held >= 6, held - 6, held)
                )
                best["last"] = max(
                    (
                        best.get("last", -1),
                        *(
                            q
                            for q in range(min(credits), at + 1)
                            if _disability(
                                credits, q, status_periods, case.blind
                            )
                        ),
                    )
                )
            # The first insured start is itself a valid 404.131 witness.
            # Later queries do not erase that witness, and the current
            # period is never used to establish its own DISABILITY status.
            answer[2] |= any(
                _disability(credits, q, establishment_periods, case.blind)
                for q in range(quarter(onset), at + 1)
            )
    return tuple(answer), lawful, tuple(sorted(starts)), own


def _check_diagnostics(case, result, best):
    """Every exact diagnostic must belong to the reported start."""
    for name in ("fully", "currently"):
        decision = getattr(result, name)
        count = decision.qc_count_upper
        assert decision.qc_count_lower == count, (case, name, result)
        assert (
            decision.insured,
            count - decision.required,
            count,
        ) == best[
            name
        ], (case, name, best[name], result)
        assert any(
            set(decision.assigned_quarters) <= credits
            for credits in best["fillings"]
        ), (case, name, decision)
    assert quarter(result.dli.upper) == best["last"], (case, result)


def _check(case):
    expected, lawful, starts, own = favorable_statuses(case)
    observed = rule.EarningsProvenance.OBSERVED
    person = rule.Person(
        date(1960, 2, 2),
        sex=rule.Sex.FEMALE,
        statutory_blindness=case.blind,
        disability_onset=date(2000, 2, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=observed,
        current_disability_period_end=date(2002, 12, 31),
        current_disability_period_end_provenance=observed,
        prior_disability_periods=tuple(
            rule.DisabilityPeriod(a, b) for a, b in case.periods
        ),
        prior_disability_periods_provenance=observed,
        sspa211_applies=False,
        sspa211_provenance=observed,
    )
    years = {
        year: (
            rule.CoverageYear(observed, qc_count=case.annual.get(year, 0))
            if year >= 1978
            else rule.CoverageYear(observed, qc_quarters=(False,) * 4)
        )
        for year in range(1960, case.month.year + 1)
    }
    try:
        result = rule.insured_status(person, years, case.month)
    except rule.InsuredConfigurationUnsupported:
        return "refused"
    except InvalidFamilyInput as error:
        if lawful:
            pytest.fail(f"lawful status completion rejected: {case}: {error}")
        return "invalid"
    assert lawful, (case, "computed an impossible establishment", result)
    actual = tuple(
        getattr(result, name).insured
        for name in ("fully", "currently", "disability")
    )
    assert actual == expected, (case, actual, expected, starts, result)
    _check_diagnostics(
        case, result, own[quarter(result.current_disability_period_start)]
    )
    return "computed"


def test_status_oracle_review_completion_has_favorable_fully_status():
    case = Declaration()
    expected, lawful, starts, _ = favorable_statuses(case)
    assert lawful and 2000 * 4 + 1 in starts
    assert expected[0]
    _check(case)


@pytest.mark.parametrize("blind", (False, True))
@pytest.mark.parametrize("prior", ("none", "clear", "overlap"))
@pytest.mark.parametrize("query", ("after", "later", "claiming"))
@pytest.mark.parametrize("prior_count", (2, 3))
def test_status_oracle_completion_lattice(blind, prior, query, prior_count):
    outcome = _check(Declaration(blind, prior, prior_count, 1, query))
    if prior == "none":
        assert outcome == "computed"


@settings(max_examples=24, deadline=None, derandomize=True)
@example(
    blind=False,
    prior="overlap",
    prior_count=2,
    onset_count=1,
    query="later",
)
@given(
    blind=st.booleans(),
    prior=st.sampled_from(("none", "clear", "overlap")),
    prior_count=st.integers(2, 3),
    onset_count=st.integers(1, 2),
    query=st.sampled_from(("after", "later", "claiming")),
)
def test_status_oracle_generated_status_coherence(
    blind, prior, prior_count, onset_count, query
):
    _check(Declaration(blind, prior, prior_count, onset_count, query))
