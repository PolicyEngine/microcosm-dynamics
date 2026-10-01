"""An across-the-board Social Security cut at trust fund depletion.

ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA.  The pure-Python parts of
``scripts/pe_us_depletion_cut_sample_households.py``: no
``policyengine_us`` import and no subprocess.

1. **The payable share.**  :func:`highlights_text` reads the text of the
   2026 Trustees Report's Highlights page (section II.A),
   :func:`depletion_quotes` finds the one sentence pair per fund that states
   when its reserves deplete and what share of scheduled benefits is
   payable then, and :func:`parse_depletion_sentence` reads the year and
   percent from that quote.  So the share the analysis uses is the one the
   recorded quote states.  :func:`key_results_table` reads the same two
   numbers from the page's Table II.A1, a second reading the script
   requires to agree.
2. **The cut.**  :func:`payable_monthly_benefit` applies a payable share to
   one beneficiary's whole-dollar monthly benefit and rounds the product
   down to a whole dollar (:data:`ROUNDING_RULE`).  :func:`cut_benefit`
   returns the monthly and annual amounts before and after the cut, and
   :func:`cut_household` cuts each beneficiary's benefit separately.
3. **Who pays the offset.**  The bridge's decomposition
   (:func:`populace_dynamics.bridge.policyengine_us.decompose`) splits the
   change in net income into leaves whose changes sum exactly, in cents,
   to the net change.  :func:`level_for` assigns each leaf to one level of
   :data:`LEVELS` (federal, state, joint federal-state, and so on);
   :func:`by_level` sums the leaves by level, so the levels partition the
   leaves; :func:`offset_share` is the share of the Social Security cut
   that other programs and taxes return, ``1 - net change / Social
   Security change``, and :func:`offset_shares_by_level` splits it by
   level.

What this module does not do: decide whether, when or how benefits would
in fact be reduced at depletion (current law does not say), compute a
scheduled benefit (callers pass whole-dollar monthly benefits), or run
PolicyEngine-US.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from fractions import Fraction
from typing import Any

__all__ = [
    "BenefitCut",
    "DepletionQuote",
    "FUNDS",
    "LEAF_LEVELS",
    "LEVELS",
    "LEVEL_LABELS",
    "OFFSET_GROUPS",
    "OFFSET_LEVELS",
    "ROUNDING_RULE",
    "by_level",
    "changed_outside_groups",
    "cut_benefit",
    "cut_household",
    "depletion_quotes",
    "highlights_text",
    "is_reviewed",
    "key_results_table",
    "level_for",
    "offset_share",
    "offset_shares_by_level",
    "parse_depletion_sentence",
    "payable_monthly_benefit",
]

#: The two funds the Highlights page states a depletion year for, by the
#: name its sentence uses.
FUNDS: dict[str, str] = {
    "OASI Trust Fund": "OASI",
    "combined OASDI fund": "OASDI",
}

#: The Trustees Report's sentence pair for one fund, as the 2026 report's
#: Highlights print it (whitespace collapsed, the apostrophe straightened):
#: "The OASI Trust Fund is projected to become depleted in the fourth
#: quarter of 2032, one quarter earlier than projected in last year's
#: report. Upon reserve depletion in 2032, projected income is sufficient
#: to pay 78 percent of scheduled benefits."
_SENTENCE = (
    r"The (?P<fund>OASI Trust Fund|combined OASDI fund) is projected to "
    r"become depleted in the (?P<quarter>first|second|third|fourth) quarter "
    r"of (?P<year>\d{4}),[^.]*\. Upon reserve depletion in "
    r"(?P<year2>\d{4}), projected income is sufficient to pay "
    r"(?P<percent>\d{1,3}) percent of scheduled benefits\."
)
_SENTENCE_FULL = re.compile("^" + _SENTENCE + "$")
_SENTENCE_ANY = re.compile(_SENTENCE)
#: Table II.A1 ("Key Results") as the page's text reads it: OASI, DI and
#: OASDI columns, DI's depletion year and payable share given by footnote
#: "a" (reserves sufficient throughout the projection period).
_KEY_RESULTS = re.compile(
    r"Table II\.A1\.\s*[—-]+\s*Key Results \[Under Intermediate "
    r"Assumptions\] OASI DI OASDI Year of projected trust fund reserve "
    r"depletion (?P<oasi_year>\d{4}) a (?P<oasdi_year>\d{4}) Percent of "
    r"scheduled benefits that are payable: Before reserve depletion 100 a "
    r"100 100 Upon reserve depletion (?P<oasi_percent>\d{1,3}) a "
    r"(?P<oasdi_percent>\d{1,3}) "
)

#: How the payable benefit is rounded, stated once for every artifact.
ROUNDING_RULE = (
    "Each beneficiary's payable monthly benefit is the scheduled 2026 "
    "monthly benefit (a whole dollar) times the payable share, rounded down "
    "to a whole dollar: the rounding 42 USC 415(g) prescribes for a monthly "
    "benefit computed under section 402 ('is not a multiple of $1 shall be "
    "rounded to the next lower multiple of $1'). Current law says nothing "
    "about how benefits would be reduced at depletion; applying the share "
    "to each monthly benefit and rounding the result this way is this "
    "analysis's choice. The monthly cut is the scheduled benefit less the "
    "payable benefit, so it is at least the cut share times the scheduled "
    "benefit and less than a dollar more; the annual amounts are twelve "
    "times the monthly ones."
)


# ---------------------------------------------------------------------------
# The payable share, from the Trustees Report's own words
# ---------------------------------------------------------------------------
def highlights_text(page: str) -> str:
    """The visible text of an HTML page, whitespace collapsed.

    Drops ``<script>`` and ``<style>`` blocks and every tag, decodes HTML
    entities, and collapses runs of whitespace (non-breaking spaces
    included) to one space.  Characters are otherwise kept as printed (a
    curly apostrophe stays curly), so a quote taken from the result is the
    page's own text.
    """

    if not isinstance(page, str):
        raise TypeError(f"expected the page's HTML, not {page!r}")
    text = re.sub(r"(?is)<(script|style)\b.*?</\1\s*>", " ", page)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _straight(text: str) -> str:
    return " ".join(text.replace("’", "'").split())


def depletion_quotes(text: str) -> dict[str, str]:
    """Each fund's depletion sentence pair, as ``text`` prints it.

    ``text`` is :func:`highlights_text` of the Highlights page.  Returns
    ``{"OASI": quote, "OASDI": quote}``.  Refuses text in which either fund
    has no such sentence pair, or more than one.
    """

    found: dict[str, list[str]] = {fund: [] for fund in FUNDS.values()}
    for match in _SENTENCE_ANY.finditer(_straight(text)):
        found[FUNDS[match["fund"]]].append(match.group(0))
    out = {}
    for fund, matches in found.items():
        if len(matches) != 1:
            raise ValueError(
                f"expected one depletion sentence for {fund}, found "
                f"{len(matches)}"
            )
        # The quote as printed: find the straightened match's span in the
        # original text, whose characters correspond one for one after
        # whitespace is collapsed (only the apostrophe differs).
        collapsed = " ".join(text.split())
        start = _straight(collapsed).index(matches[0])
        out[fund] = collapsed[start : start + len(matches[0])]
    return out


@dataclass(frozen=True)
class DepletionQuote:
    """A fund's depletion year and payable percent, from one sentence pair.

    ``payable_share`` is the percent over 100, exactly; ``cut_share`` is
    one less it, the across-the-board cut that leaves benefits payable from
    income alone in the year of depletion.
    """

    fund: str
    quarter: str
    year: int
    percent: int

    @property
    def payable_share(self) -> Decimal:
        return Decimal(self.percent) / 100

    @property
    def cut_share(self) -> Decimal:
        return 1 - self.payable_share

    def as_dict(self) -> dict[str, Any]:
        return {
            "fund": self.fund,
            "depletion_quarter": self.quarter,
            "depletion_year": self.year,
            "payable_percent": self.percent,
            "payable_share": str(self.payable_share),
            "cut_share": str(self.cut_share),
        }


def parse_depletion_sentence(text: str) -> DepletionQuote:
    """The fund, depletion quarter and year, and payable percent of ``text``.

    ``text`` is one fund's sentence pair (:func:`depletion_quotes`);
    whitespace is collapsed and a curly apostrophe straightened first.
    Refuses text that does not match, a second year that differs from the
    first, or a percent above 100.
    """

    if not isinstance(text, str):
        raise TypeError(f"expected the quoted text, not {text!r}")
    match = _SENTENCE_FULL.match(_straight(text))
    if match is None:
        raise ValueError(f"not a depletion sentence: {text!r}")
    year = int(match["year"])
    if int(match["year2"]) != year:
        raise ValueError(
            f"the sentence names {year} and {match['year2']} as the year "
            "of depletion"
        )
    percent = int(match["percent"])
    if not 0 <= percent <= 100:
        raise ValueError(f"payable percent {percent} is not 0-100")
    return DepletionQuote(
        fund=FUNDS[match["fund"]],
        quarter=match["quarter"],
        year=year,
        percent=percent,
    )


def key_results_table(text: str) -> dict[str, dict[str, int]]:
    """Table II.A1's OASI and OASDI depletion years and payable percents.

    ``text`` is :func:`highlights_text` of the Highlights page.  Returns
    ``{"OASI": {"year": ..., "percent": ...}, "OASDI": {...}}``.  Refuses
    text without exactly one such table.
    """

    matches = list(_KEY_RESULTS.finditer(_straight(text)))
    if len(matches) != 1:
        raise ValueError(
            f"expected one Table II.A1 of key results, found {len(matches)}"
        )
    match = matches[0]
    return {
        fund: {
            "year": int(match[f"{fund.lower()}_year"]),
            "percent": int(match[f"{fund.lower()}_percent"]),
        }
        for fund in ("OASI", "OASDI")
    }


# ---------------------------------------------------------------------------
# The cut
# ---------------------------------------------------------------------------
def _share(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(
            f"the payable share must be a Decimal (exact), not {value!r}"
        )
    if not value.is_finite() or not 0 <= value <= 1:
        raise ValueError(f"the payable share must be 0-1, not {value}")
    return value


def _whole_dollars(label: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be whole dollars (int), not {value!r}")
    if value < 0:
        raise ValueError(f"{label} must be nonnegative, not {value}")
    return value


def payable_monthly_benefit(monthly: int, payable_share: Decimal) -> int:
    """``monthly`` times ``payable_share``, rounded down to a whole dollar.

    The rounding of :data:`ROUNDING_RULE` (42 USC 415(g): an amount that
    "is not a multiple of $1 shall be rounded to the next lower multiple of
    $1").  Exact: the product is taken in ``Decimal``.
    """

    amount = _whole_dollars("monthly", monthly)
    share = _share(payable_share)
    return int((Decimal(amount) * share).to_integral_value(ROUND_FLOOR))


@dataclass(frozen=True)
class BenefitCut:
    """One beneficiary's 2026 benefit before and after the cut (dollars)."""

    monthly_scheduled: int
    monthly_payable: int
    payable_share: Decimal

    @property
    def monthly_cut(self) -> int:
        return self.monthly_scheduled - self.monthly_payable

    @property
    def annual_scheduled(self) -> int:
        return 12 * self.monthly_scheduled

    @property
    def annual_payable(self) -> int:
        return 12 * self.monthly_payable

    @property
    def annual_cut(self) -> int:
        return 12 * self.monthly_cut

    def as_dict(self) -> dict[str, Any]:
        return {
            "payable_share": str(self.payable_share),
            "monthly_scheduled": self.monthly_scheduled,
            "monthly_payable": self.monthly_payable,
            "monthly_cut": self.monthly_cut,
            "annual_scheduled": self.annual_scheduled,
            "annual_payable": self.annual_payable,
            "annual_cut": self.annual_cut,
        }


def cut_benefit(monthly: int, payable_share: Decimal) -> BenefitCut:
    """The cut of one monthly benefit (:func:`payable_monthly_benefit`)."""

    return BenefitCut(
        monthly_scheduled=_whole_dollars("monthly", monthly),
        monthly_payable=payable_monthly_benefit(monthly, payable_share),
        payable_share=payable_share,
    )


def cut_household(
    benefits: Mapping[str, int], payable_share: Decimal
) -> dict[str, BenefitCut]:
    """Each beneficiary's cut, applied to that beneficiary's own benefit.

    ``benefits`` maps a beneficiary to a whole-dollar scheduled monthly
    benefit.  Each benefit is cut and rounded on its own
    (:data:`ROUNDING_RULE`), so a couple's cut is the sum of two cuts, not
    the cut of their sum.
    """

    if isinstance(benefits, str) or not isinstance(benefits, Mapping):
        raise TypeError("benefits must map each beneficiary to dollars")
    if not benefits:
        raise ValueError("a household needs at least one benefit")
    return {
        str(person): cut_benefit(monthly, payable_share)
        for person, monthly in benefits.items()
    }


# ---------------------------------------------------------------------------
# Who pays the offset
# ---------------------------------------------------------------------------
#: The levels a leaf of the decomposition is assigned to.  ``social_security``
#: holds the cut itself; ``federal``, ``state`` and ``joint`` (programs the
#: federal government and the states pay together) hold the offsets;
#: ``market_income`` holds the household's own income, which the cut does
#: not change; ``unattributed`` holds every leaf whose payer was not
#: reviewed for this analysis.  The script refuses a run in which a
#: ``market_income`` or ``unattributed`` leaf changes, so the offset is
#: always the sum of the three payer groups.
LEVELS: tuple[str, ...] = (
    "social_security",
    "federal",
    "state",
    "joint",
    "market_income",
    "unattributed",
)
#: The levels whose changes offset the Social Security cut.
OFFSET_LEVELS: tuple[str, ...] = LEVELS[1:]
#: The payer groups the outputs report.
OFFSET_GROUPS: tuple[str, ...] = ("federal", "state", "joint")
LEVEL_LABELS: dict[str, str] = {
    "social_security": "Social Security (the cut)",
    "federal": "Federal programs and taxes",
    "state": "State programs and taxes",
    "joint": "Joint federal-state programs",
    "market_income": "Household market income",
    "unattributed": "Not attributed",
}
#: Each leaf whose payer was reviewed for this analysis: its level and the
#: basis.  Statute text is quoted from the Legal Information Institute's
#: pages for 42 USC 1381, 42 USC 1382e and 7 USC 2013, retrieved on
#: 2026-10-01; PolicyEngine-US paths are in the 2.18.0 release, under
#: ``policyengine_us/``.
LEAF_LEVELS: dict[str, tuple[str, str]] = {
    "social_security": (
        "social_security",
        "Social Security benefits: the cut itself",
    ),
    "ssi": (
        "federal",
        "The federal SSI benefit: 'there are authorized to be appropriated "
        "sums sufficient to carry out this subchapter' (42 USC 1381)",
    ),
    "snap": (
        "federal",
        "SNAP benefits 'shall be redeemable at face value by the Secretary "
        "through the facilities of the Treasury of the United States' (7 "
        "USC 2013(a)(1)). The State cost share of 7 USC 2013(a)(2)(B) "
        "begins in fiscal year 2028 at the earliest, so it does not apply "
        "under 2026 law",
    ),
    "income_tax_before_refundable_credits": (
        "federal",
        "Federal income tax before refundable credits",
    ),
    "income_tax_refundable_credits": (
        "federal",
        "Federal refundable income tax credits",
    ),
    "ca_state_supplement": (
        "state",
        "California's SSI state supplementary payment. A State whose "
        "supplement the Commissioner pays on its behalf 'shall ... pay to "
        "the Commissioner of Social Security an amount equal to the "
        "expenditures made by the Commissioner of Social Security as such "
        "supplementary payments' (42 USC 1382e(d)(1))",
    ),
    "state_income_tax_before_refundable_credits": (
        "state",
        "State income tax before refundable credits",
    ),
    "ca_refundable_credits": ("state", "California refundable tax credits"),
    "mt_refundable_credits": ("state", "Montana refundable tax credits"),
    "medicaid_cost": (
        "joint",
        "Medicaid valued at cost (health sensitivity only). PolicyEngine-US "
        "splits it between the federal government and the state by the "
        "federal medical assistance percentage "
        "(variables/gov/hhs/medicaid/costs/medicaid_federal_cost.py, "
        "medicaid_federal_share.py; parameters/gov/hhs/medicaid/cost_share/"
        "fmap.yaml, citing 42 USC 1396d(b))",
    ),
    "msp_cost": (
        "joint",
        "Medicare Savings Programs valued at cost (health sensitivity only). "
        "PolicyEngine-US's federal share is the state's regular federal "
        "medical assistance percentage for QMB and SLMB "
        "(variables/gov/hhs/medicare/savings_programs/msp_federal_cost.py)",
    ),
}


def is_reviewed(variable: str) -> bool:
    """Whether ``variable``'s payer was reviewed (:data:`LEAF_LEVELS`)."""

    return variable in LEAF_LEVELS


def level_for(variable: str, category: str) -> str:
    """The level of a leaf: reviewed, market income, or unattributed.

    ``category`` is the bridge's display category
    (:func:`populace_dynamics.bridge.policyengine_us.category_for`).  Every
    leaf gets exactly one level in :data:`LEVELS`.
    """

    if variable in LEAF_LEVELS:
        return LEAF_LEVELS[variable][0]
    if category == "market_income":
        return "market_income"
    return "unattributed"


def by_level(components: Iterable[Any]) -> dict[str, dict[str, int]]:
    """Each level's baseline, reform and change, in cents.

    ``components`` are the bridge's :class:`Component` leaves (anything
    with ``variable``, ``category``, ``baseline_cents`` and
    ``reform_cents``).  Every level appears, zeros included, and each
    component is counted in exactly one level, so the levels' changes sum
    to the components' changes.
    """

    out = {
        level: {"baseline": 0, "reform": 0, "change": 0} for level in LEVELS
    }
    for component in components:
        entry = out[level_for(component.variable, component.category)]
        entry["baseline"] += component.baseline_cents
        entry["reform"] += component.reform_cents
        entry["change"] += component.reform_cents - component.baseline_cents
    return out


def changed_outside_groups(components: Iterable[Any]) -> list[str]:
    """Leaves that changed although no payer group holds them.

    The leaves of ``market_income`` or ``unattributed`` with a nonzero
    change; the script refuses a run with any.
    """

    return sorted(
        component.variable
        for component in components
        if component.reform_cents != component.baseline_cents
        and level_for(component.variable, component.category)
        in ("market_income", "unattributed")
    )


def _cents(label: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be int cents, not {value!r}")
    return value


def offset_share(
    net_change_cents: int, social_security_change_cents: int
) -> Fraction | None:
    """``1 - net change / Social Security change``, exactly.

    The share of the Social Security change that other programs and taxes
    return.  ``None`` when Social Security does not change.
    """

    net = _cents("net_change_cents", net_change_cents)
    social_security = _cents(
        "social_security_change_cents", social_security_change_cents
    )
    if social_security == 0:
        return None
    return 1 - Fraction(net, social_security)


def offset_shares_by_level(
    levels: Mapping[str, Mapping[str, int]],
) -> dict[str, Fraction] | None:
    """Each offset level's share of the Social Security change, exactly.

    ``levels`` is :func:`by_level`'s output.  A level's share is its change
    over minus the Social Security change, so the shares of
    :data:`OFFSET_LEVELS` sum to :func:`offset_share`.  ``None`` when
    Social Security does not change.
    """

    social_security = _cents(
        "social_security change", levels["social_security"]["change"]
    )
    if social_security == 0:
        return None
    return {
        level: Fraction(
            -_cents(f"{level} change", levels[level]["change"]),
            social_security,
        )
        for level in OFFSET_LEVELS
    }
