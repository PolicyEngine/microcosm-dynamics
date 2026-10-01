"""The depletion-cut module: the payable share, the cut and the offsets.

Pure Python (no policyengine-us).  Hypothesis properties check the
invariants the analysis states, over generated inputs:

* a zero cut (a payable share of 1) changes nothing;
* the cut is the cut share times the benefit, within the stated rounding
  (at least that, and less than a dollar a month more);
* a deeper cut never leaves more Social Security;
* the decomposition's components sum exactly to the net change, and the
  levels of government partition them;
* the offset share is ``1 - net change / Social Security change`` exactly,
  and the levels' shares sum to it.

Example tests pin the Trustees Report quotes read from the committed
Highlights page (ILLUSTRATIVE analysis; the page is the 2026 report's
section II.A) and the refusals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.bridge import depletion_cut as dc
from populace_dynamics.bridge import policyengine_us as bridge

ROOT = Path(__file__).resolve().parents[2]
PAGE = (
    ROOT
    / "docs"
    / "analysis"
    / "pe_us_depletion_cut_20261001"
    / "sources"
    / "II_A_highlights.html"
)
OASI_QUOTE = (
    "The OASI Trust Fund is projected to become depleted in the fourth "
    "quarter of 2032, one quarter earlier than projected in last year’s "
    "report. Upon reserve depletion in 2032, projected income is sufficient "
    "to pay 78 percent of scheduled benefits."
)
OASDI_QUOTE = (
    "The combined OASDI fund is projected to become depleted in the third "
    "quarter of 2034, the same quarter as in last year’s report. Upon "
    "reserve depletion in 2034, projected income is sufficient to pay 83 "
    "percent of scheduled benefits."
)

shares = st.decimals(
    min_value=Decimal(0),
    max_value=Decimal(1),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)
monthly_benefits = st.integers(min_value=0, max_value=10_000)


# ---------------------------------------------------------------------------
# The Trustees Report's numbers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def page_text():
    return dc.highlights_text(PAGE.read_text(encoding="utf-8"))


def test__given_the_committed_page__then_both_quotes_are_found(page_text):
    assert dc.depletion_quotes(page_text) == {
        "OASI": OASI_QUOTE,
        "OASDI": OASDI_QUOTE,
    }


def test__given_the_quotes__then_the_numbers_are_the_reports(page_text):
    quotes = dc.depletion_quotes(page_text)
    oasi = dc.parse_depletion_sentence(quotes["OASI"])
    oasdi = dc.parse_depletion_sentence(quotes["OASDI"])
    assert (oasi.fund, oasi.quarter, oasi.year, oasi.percent) == (
        "OASI",
        "fourth",
        2032,
        78,
    )
    assert (oasdi.fund, oasdi.quarter, oasdi.year, oasdi.percent) == (
        "OASDI",
        "third",
        2034,
        83,
    )
    assert oasi.payable_share == Decimal("0.78")
    assert oasi.cut_share == Decimal("0.22")
    assert oasdi.cut_share == Decimal("0.17")
    assert oasi.as_dict()["payable_share"] == "0.78"


def test__given_the_committed_page__then_table_ii_a1_agrees(page_text):
    assert dc.key_results_table(page_text) == {
        "OASI": {"year": 2032, "percent": 78},
        "OASDI": {"year": 2034, "percent": 83},
    }


def test__given_html__then_text_drops_scripts_tags_and_entities():
    page = (
        "<html><head><style>p {color: red}</style>"
        "<script>var x = 'The OASI';</script></head>"
        "<body><p>Upon&nbsp;reserve\n\n depletion</p> <b>last year&#8217;s"
        "</b></body></html>"
    )
    assert dc.highlights_text(page) == ("Upon reserve depletion last year’s")


@settings(deadline=None)
@given(
    fund=st.sampled_from(sorted(dc.FUNDS)),
    quarter=st.sampled_from(["first", "second", "third", "fourth"]),
    year=st.integers(min_value=2026, max_value=2100),
    percent=st.integers(min_value=0, max_value=100),
    apostrophe=st.sampled_from(["'", "’"]),
)
def test__given_any_depletion_sentence__then_it_parses_back(
    fund, quarter, year, percent, apostrophe
):
    text = (
        f"The {fund} is projected to become depleted in the {quarter} "
        f"quarter of {year}, the same quarter as in last year{apostrophe}s "
        f"report. Upon reserve depletion in {year}, projected income is "
        f"sufficient to pay {percent} percent of scheduled benefits."
    )
    quote = dc.parse_depletion_sentence(text)
    assert quote.fund == dc.FUNDS[fund]
    assert (quote.quarter, quote.year, quote.percent) == (
        quarter,
        year,
        percent,
    )
    assert quote.payable_share + quote.cut_share == 1


@pytest.mark.parametrize(
    ("text", "match"),
    [
        (
            OASI_QUOTE.replace("in 2032, projected", "in 2033, projected"),
            "names",
        ),
        (OASI_QUOTE.replace("78 percent", "178 percent"), "0-100"),
        ("The OASI Trust Fund is solvent.", "not a depletion sentence"),
    ],
)
def test__given_a_bad_sentence__then_parsing_is_refused(text, match):
    with pytest.raises(ValueError, match=match):
        dc.parse_depletion_sentence(text)


def test__given_a_non_string__then_parsing_is_refused():
    with pytest.raises(TypeError):
        dc.parse_depletion_sentence(78)
    with pytest.raises(TypeError):
        dc.highlights_text(b"<p>bytes</p>")


@pytest.mark.parametrize(
    "text",
    [
        OASI_QUOTE,  # no OASDI sentence
        f"{OASI_QUOTE} {OASI_QUOTE} {OASDI_QUOTE}",  # two OASI sentences
    ],
)
def test__given_missing_or_repeated_quotes__then_finding_is_refused(text):
    with pytest.raises(ValueError, match="expected one depletion sentence"):
        dc.depletion_quotes(text)


def test__given_no_key_results_table__then_reading_is_refused():
    with pytest.raises(ValueError, match="Table II.A1"):
        dc.key_results_table(f"{OASI_QUOTE} {OASDI_QUOTE}")


# ---------------------------------------------------------------------------
# The cut
# ---------------------------------------------------------------------------
@settings(deadline=None)
@given(monthly=monthly_benefits)
def test__given_a_zero_cut__then_nothing_changes(monthly):
    cut = dc.cut_benefit(monthly, Decimal(1))
    assert cut.monthly_payable == monthly
    assert cut.monthly_cut == cut.annual_cut == 0
    assert cut.annual_payable == cut.annual_scheduled == 12 * monthly


@settings(deadline=None)
@given(
    benefits=st.dictionaries(st.text(min_size=1), monthly_benefits, min_size=1)
)
def test__given_a_zero_cut__then_no_household_benefit_changes(benefits):
    cuts = dc.cut_household(benefits, Decimal(1))
    assert {k: c.monthly_payable for k, c in cuts.items()} == benefits
    assert sum(c.annual_cut for c in cuts.values()) == 0


@settings(deadline=None)
@given(monthly=monthly_benefits, share=shares)
def test__given_any_cut__then_it_is_the_share_within_the_rounding(
    monthly, share
):
    """``ROUNDING_RULE``: at least the cut share, less than $1 more."""

    cut = dc.cut_benefit(monthly, share)
    exact = (1 - share) * monthly
    assert 0 <= cut.monthly_cut - exact < 1
    assert 0 <= cut.annual_cut - 12 * exact < 12
    assert cut.monthly_payable == int(share * monthly // 1)
    assert cut.monthly_payable + cut.monthly_cut == monthly
    assert 0 <= cut.monthly_payable <= monthly


@settings(deadline=None)
@given(monthly=monthly_benefits, first=shares, second=shares)
def test__given_a_deeper_cut__then_social_security_never_rises(
    monthly, first, second
):
    deeper, shallower = sorted((first, second))
    assert dc.payable_monthly_benefit(
        monthly, deeper
    ) <= dc.payable_monthly_benefit(monthly, shallower)


@settings(deadline=None)
@given(
    benefits=st.dictionaries(
        st.text(min_size=1), monthly_benefits, min_size=1
    ),
    first=shares,
    second=shares,
)
def test__given_a_deeper_cut__then_no_household_gets_more(
    benefits, first, second
):
    deeper, shallower = sorted((first, second))
    total = {
        share: sum(
            c.annual_payable
            for c in dc.cut_household(benefits, share).values()
        )
        for share in (deeper, shallower)
    }
    assert total[deeper] <= total[shallower]


def test__given_two_benefits__then_each_is_rounded_on_its_own():
    """A couple's cut is the sum of two cuts, not the cut of their sum."""

    cuts = dc.cut_household({"worker": 1, "spouse": 1}, Decimal("0.5"))
    assert [c.monthly_payable for c in cuts.values()] == [0, 0]
    assert sum(c.monthly_cut for c in cuts.values()) == 2
    assert dc.cut_benefit(2, Decimal("0.5")).monthly_cut == 1


def test__the_2026_benefits__then_the_cuts_are_the_expected_dollars():
    """The households' scheduled benefits at 78 and 83 percent."""

    cases = {
        (743, "0.78"): 579,
        (743, "0.83"): 616,
        (2_351, "0.78"): 1_833,
        (2_351, "0.83"): 1_951,
        (1_175, "0.78"): 916,
        (1_175, "0.83"): 975,
    }
    for (monthly, share), payable in cases.items():
        assert dc.payable_monthly_benefit(monthly, Decimal(share)) == payable


@pytest.mark.parametrize(
    ("monthly", "share", "error"),
    [
        (743.0, Decimal("0.78"), TypeError),
        (True, Decimal("0.78"), TypeError),
        (-1, Decimal("0.78"), ValueError),
        (743, 0.78, TypeError),
        (743, Decimal("1.01"), ValueError),
        (743, Decimal("-0.01"), ValueError),
        (743, Decimal("NaN"), ValueError),
    ],
)
def test__given_a_bad_benefit_or_share__then_the_cut_is_refused(
    monthly, share, error
):
    with pytest.raises(error):
        dc.cut_benefit(monthly, share)


def test__given_no_benefits__then_the_household_cut_is_refused():
    with pytest.raises(ValueError):
        dc.cut_household({}, Decimal("0.78"))
    with pytest.raises(TypeError):
        dc.cut_household("worker", Decimal("0.78"))


def test__rounding_rule__then_it_states_415g_and_the_choice():
    assert "415(g)" in dc.ROUNDING_RULE
    assert "next lower multiple of $1" in dc.ROUNDING_RULE
    assert "this analysis's choice" in dc.ROUNDING_RULE


# ---------------------------------------------------------------------------
# Who pays the offset
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Leaf:
    variable: str
    category: str
    baseline_cents: int
    reform_cents: int


LEAF_NAMES = st.sampled_from(
    [*dc.LEAF_LEVELS, "pension_income", "wic", "local_income_tax", "chip"]
)
CATEGORIES = st.sampled_from(bridge.CATEGORY_ORDER)
CENTS = st.integers(min_value=-(10**9), max_value=10**9)
leaves = st.lists(
    st.builds(_Leaf, LEAF_NAMES, CATEGORIES, CENTS, CENTS), max_size=30
)


@settings(deadline=None)
@given(components=leaves)
def test__given_any_components__then_the_levels_partition_them(components):
    levels = dc.by_level(components)
    assert list(levels) == list(dc.LEVELS)
    for key, attribute in (
        ("baseline", "baseline_cents"),
        ("reform", "reform_cents"),
    ):
        assert sum(level[key] for level in levels.values()) == sum(
            getattr(c, attribute) for c in components
        )
    assert sum(level["change"] for level in levels.values()) == sum(
        c.reform_cents - c.baseline_cents for c in components
    )
    for component in components:
        assert dc.level_for(component.variable, component.category) in (
            dc.LEVELS
        )


@settings(deadline=None)
@given(components=leaves)
def test__given_any_components__then_level_shares_sum_to_the_offset(
    components,
):
    levels = dc.by_level(components)
    social_security = levels["social_security"]["change"]
    net = sum(c.reform_cents - c.baseline_cents for c in components)
    share = dc.offset_share(net, social_security)
    by_level = dc.offset_shares_by_level(levels)
    if social_security == 0:
        assert share is None and by_level is None
        return
    assert share == 1 - Fraction(net, social_security)
    assert sum(by_level.values()) == share
    assert set(by_level) == set(dc.OFFSET_LEVELS)


@settings(deadline=None)
@given(
    net=st.integers(min_value=-(10**9), max_value=10**9),
    social_security=st.integers(
        min_value=-(10**9), max_value=10**9
    ).filter(bool),
)
def test__given_any_changes__then_the_offset_share_is_exact(
    net, social_security
):
    share = dc.offset_share(net, social_security)
    assert share == 1 - Fraction(net, social_security)
    if net == social_security:
        assert share == 0
    if net == 0:
        assert share == 1


def _tree():
    return bridge.ComponentTree(
        "household_net_income",
        {
            "household_net_income": bridge.NET_INCOME_DEFINITION,
            "household_market_income": (("pension_income", 1),),
            "household_benefits": (
                ("social_security", 1),
                ("ssi", 1),
                ("snap", 1),
                ("household_state_benefits", 1),
            ),
            "household_state_benefits": (("ca_state_supplement", 1),),
            "household_refundable_tax_credits": (
                ("income_tax_refundable_credits", 1),
            ),
            "household_tax_before_refundable_credits": (
                ("income_tax_before_refundable_credits", 1),
                ("state_income_tax_before_refundable_credits", 1),
            ),
        },
    )


AMOUNTS = st.floats(
    min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
)


def _values(leaf_values):
    values = {"household_health_costs": 0.0, **leaf_values}
    values["household_market_income"] = values["pension_income"]
    values["household_state_benefits"] = values["ca_state_supplement"]
    values["household_benefits"] = (
        values["social_security"]
        + values["ssi"]
        + values["snap"]
        + values["household_state_benefits"]
    )
    values["household_refundable_tax_credits"] = values[
        "income_tax_refundable_credits"
    ]
    values["household_tax_before_refundable_credits"] = (
        values["income_tax_before_refundable_credits"]
        + values["state_income_tax_before_refundable_credits"]
    )
    values["household_net_income"] = (
        values["household_market_income"]
        + values["household_benefits"]
        + values["household_refundable_tax_credits"]
        - values["household_tax_before_refundable_credits"]
    )
    return values


LEAVES = (
    "pension_income",
    "social_security",
    "ssi",
    "snap",
    "ca_state_supplement",
    "income_tax_refundable_credits",
    "income_tax_before_refundable_credits",
    "state_income_tax_before_refundable_credits",
)
leaf_values = st.fixed_dictionaries({name: AMOUNTS for name in LEAVES})


@settings(deadline=None)
@given(baseline=leaf_values, reform=leaf_values)
def test__given_any_runs__then_components_sum_exactly_to_the_net_change(
    baseline, reform
):
    decomposition = bridge.decompose(
        _tree(), _values(baseline), _values(reform)
    )
    levels = dc.by_level(decomposition.components)
    total = sum(c.change_cents for c in decomposition.components)
    assert total == decomposition.net_change_cents
    assert sum(level["change"] for level in levels.values()) == total
    share = dc.offset_share(total, levels["social_security"]["change"])
    if levels["social_security"]["change"]:
        assert share == 1 - Fraction(
            total, levels["social_security"]["change"]
        )


@settings(deadline=None)
@given(baseline=leaf_values)
def test__given_identical_runs__then_every_change_is_zero(baseline):
    """A zero cut through the decomposition: nothing moves."""

    values = _values(baseline)
    decomposition = bridge.decompose(_tree(), values, dict(values))
    levels = dc.by_level(decomposition.components)
    assert all(level["change"] == 0 for level in levels.values())
    assert decomposition.net_change_cents == 0
    assert dc.offset_share(0, levels["social_security"]["change"]) is None
    assert dc.offset_shares_by_level(levels) is None
    assert dc.changed_outside_groups(decomposition.components) == []


def test__reviewed_leaves__then_they_have_the_documented_levels():
    expected = {
        "social_security": "social_security",
        "ssi": "federal",
        "snap": "federal",
        "income_tax_before_refundable_credits": "federal",
        "income_tax_refundable_credits": "federal",
        "ca_state_supplement": "state",
        "state_income_tax_before_refundable_credits": "state",
        "ca_refundable_credits": "state",
        "mt_refundable_credits": "state",
        "medicaid_cost": "joint",
        "msp_cost": "joint",
    }
    assert {k: v[0] for k, v in dc.LEAF_LEVELS.items()} == expected
    assert set(dc.OFFSET_GROUPS) <= set(dc.OFFSET_LEVELS)
    assert set(dc.LEVEL_LABELS) == set(dc.LEVELS)
    for name, (_, basis) in dc.LEAF_LEVELS.items():
        assert basis, name
        assert dc.is_reviewed(name)
    assert not dc.is_reviewed("wic")


@pytest.mark.parametrize(
    ("variable", "category", "level"),
    [
        ("ssi", "ssi", "federal"),
        ("ca_state_supplement", "state_benefits", "state"),
        ("pension_income", "market_income", "market_income"),
        ("wic", "other_benefits", "unattributed"),
        (
            "local_income_tax_before_refundable_credits",
            "other_taxes",
            "unattributed",
        ),
    ],
)
def test__given_a_leaf__then_its_level_is_the_documented_one(
    variable, category, level
):
    assert dc.level_for(variable, category) == level


def test__given_a_changed_unreviewed_leaf__then_it_is_reported():
    components = [
        _Leaf("ssi", "ssi", 0, 100),
        _Leaf("wic", "other_benefits", 0, 5),
        _Leaf("pension_income", "market_income", 10, 11),
        _Leaf("chip", "health_net", 7, 7),
    ]
    assert dc.changed_outside_groups(components) == ["pension_income", "wic"]


@pytest.mark.parametrize(
    ("net", "social_security"),
    [(1.0, -100), (-100, 2.5), (True, -100)],
)
def test__given_non_integer_cents__then_the_offset_share_is_refused(
    net, social_security
):
    with pytest.raises(TypeError):
        dc.offset_share(net, social_security)


def test__given_no_social_security_change__then_there_is_no_share():
    assert dc.offset_share(500, 0) is None


def test__given_a_share_beyond_decimal_precision__then_the_cut_is_exact():
    """The product is a Fraction: no digit of the share is rounded away."""

    share = Decimal("0." + "9" * 40)
    assert dc.payable_monthly_benefit(743, share) == 742
    assert dc.cut_benefit(743, share).monthly_cut == 1
