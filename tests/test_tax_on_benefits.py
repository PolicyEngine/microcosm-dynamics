"""Invented liability arithmetic and named input refusals, no oracle."""

from decimal import (
    ROUND_UP,
    Clamped,
    Context,
    Decimal,
    FloatOperation,
    Inexact,
    Rounded,
    Subnormal,
    localcontext,
)
from fractions import Fraction
from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import populace_dynamics.tax_on_benefits as tob
from populace_dynamics.bridge.policyengine_us import (
    BridgeHousehold,
    BridgePerson,
)
from populace_dynamics.section86 import section86_inclusions
from populace_dynamics.tax_on_benefits import (
    LIABILITY_VARIABLES,
    TAXABILITY_VARIABLES,
    TaxOnBenefitsInput,
    _interest_components,
    allocate_liabilities,
    chapter1_liability,
    tax_on_benefits,
    tax_on_benefits_batch,
)
from tests.test_section86 import _caller_contexts, _context_state


def _components(ordinary, refundable, niit, payroll, recapture=0, penalty=0):
    values = dict.fromkeys(LIABILITY_VARIABLES, 0)
    values.update(
        income_tax=ordinary
        + niit
        + payroll
        + recapture
        + penalty
        - refundable,
        income_tax_before_refundable_credits=ordinary
        + niit
        + payroll
        + recapture
        + penalty,
        income_tax_refundable_credits=refundable,
        income_tax_before_credits=ordinary,
        net_investment_income_tax=niit,
        unreported_payroll_tax=payroll,
        recapture_of_investment_credit=recapture,
        qualified_retirement_penalty=penalty,
    )
    return values


@given(
    st.lists(st.integers(-100_000_000, 100_000_000), min_size=3, max_size=3)
)
@settings(deadline=None)
def test_signed_allocation_identity_and_determinism(cents):
    liabilities = [Decimal(x) / 100 for x in cents]
    split = allocate_liabilities(*liabilities)
    assert split.oasdi + split.hi == split.total
    assert split == allocate_liabilities(*liabilities)
    assert allocate_liabilities(*([liabilities[0]] * 3)).total == 0
    assert (
        allocate_liabilities(
            liabilities[0], liabilities[0], liabilities[2]
        ).oasdi
        == 0
    )
    assert (
        allocate_liabilities(liabilities[0], liabilities[2], liabilities[2]).hi
        == 0
    )


@given(
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
    st.lists(st.integers(0, 10_000), min_size=3, max_size=3),
)
@settings(deadline=None)
def test_non_chapter_1_taxes_enter_neither_reading_nor_fund(
    ordinary, niit, payroll, credits
):
    dirty = [
        chapter1_liability(_components(*x))
        for x in zip(ordinary, credits, niit, payroll, strict=True)
    ]
    clean = [
        chapter1_liability(_components(o, c, 0, 0))
        for o, c in zip(ordinary, credits, strict=True)
    ]
    for reading in ("before_refundable_credits", "netted_sensitivity"):
        assert [getattr(x, reading) for x in dirty] == [
            getattr(x, reading) for x in clean
        ]
        a = allocate_liabilities(*(getattr(x, reading) for x in dirty))
        b = allocate_liabilities(*(getattr(x, reading) for x in clean))
        assert a == b
        assert a.oasdi + a.hi == a.total


def test_chapter_1_recapture_and_retirement_penalty_are_retained():
    result = chapter1_liability(_components(500, 200, 80, 90, 30, 40))
    assert result.netted_sensitivity == Decimal("370.00")
    assert result.before_refundable_credits == Decimal("570.00")


@given(
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
)
@settings(deadline=None)
def test_refundable_credits_never_move_primary(ordinary, credits):
    clean = [chapter1_liability(_components(o, 0, 0, 0)) for o in ordinary]
    changed = [
        chapter1_liability(_components(o, c, 0, 0))
        for o, c in zip(ordinary, credits, strict=True)
    ]

    def primary(states):
        return allocate_liabilities(
            *(state.before_refundable_credits for state in states)
        )

    assert primary(clean) == primary(changed)


@pytest.mark.parametrize(
    "ordinary,credits,primary,netted",
    [
        ((0, 0, 0), (1700, 1000, 1000), (0, 0, 0), (700, 0, 700)),
        ((500, 800, 800), (300, 100, 100), (300, 0, 300), (500, 0, 500)),
    ],
    ids=["hub-ACTC-payment", "hub-EITC-payment"],
)
def test_hub_refundable_credit_liability_state_checks(
    ordinary, credits, primary, netted
):
    states = [
        chapter1_liability(_components(o, c, 0, 0))
        for o, c in zip(ordinary, credits, strict=True)
    ]
    result = allocate_liabilities(
        *(s.before_refundable_credits for s in states)
    )
    sensitivity = allocate_liabilities(*(s.netted_sensitivity for s in states))
    assert (result.oasdi, result.hi, result.total) == primary
    assert (sensitivity.oasdi, sensitivity.hi, sensitivity.total) == netted


def _household():
    return BridgeHousehold(
        "h", "TX", (BridgePerson("p", 70),), (("p",),), (("p",),), (("p",),)
    )


@pytest.mark.parametrize(
    "status,apart,message",
    [
        ("SURVIVING_SPOUSE", None, "SURVIVING_SPOUSE"),
        ("SEPARATE", False, "lived together"),
        ("SEPARATE", None, "lived_apart_all_year"),
    ],
)
def test_unsupported_filing_status_refused_by_name(status, apart, message):
    with pytest.raises(ValueError, match=message):
        tax_on_benefits(_household(), 2026, status, lived_apart_all_year=apart)


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"tax_unit_inputs": {"income_tax": 0}}, "income_tax"),
        ({"person_inputs": {"missing": {}}}, "missing"),
        ({"tax_unit_inputs": {"unreported_payroll_tax": -1}}, "nonnegative"),
        (
            {"tax_unit_inputs": {"unreported_payroll_tax": float("nan")}},
            "finite",
        ),
        (
            {"person_inputs": {"p": {"tax_exempt_interest_income": "1"}}},
            "annual numeric",
        ),
    ],
)
def test_input_override_refusals(kwargs, message):
    with pytest.raises(ValueError, match=message):
        tax_on_benefits(_household(), 2026, "SINGLE", **kwargs)


def test_joint_requires_two_filers():
    with pytest.raises(ValueError, match="JOINT filer count"):
        tax_on_benefits(_household(), 2026, "JOINT")


@pytest.mark.parametrize(
    "total,facts,expected",
    [
        (30000, {}, (30000, 0)),
        (34500, {"tax_exempt_interest_income": 23000}, (11500, 23000)),
        (
            0,
            {
                "taxable_interest_income": 11500,
                "tax_exempt_interest_income": 23000,
            },
            (11500, 23000),
        ),
        (
            34500,
            {
                "taxable_interest_income": 11500,
                "tax_exempt_interest_income": 23000,
            },
            (11500, 23000),
        ),
    ],
)
def test_total_interest_is_supplied_through_its_component_inputs(
    total, facts, expected
):
    entry = {"interest_income": {"2026": total}}
    _interest_components(entry, facts, "2026")
    assert "interest_income" not in entry
    assert entry["taxable_interest_income"]["2026"] == expected[0]
    assert entry["tax_exempt_interest_income"]["2026"] == expected[1]


@pytest.mark.parametrize(
    "total,facts,message",
    [
        (10, {"tax_exempt_interest_income": 20}, "exceeds interest_income"),
        (10, {"taxable_interest_income": 20}, "interest_income disagrees"),
    ],
)
def test_inconsistent_interest_inputs_are_refused(total, facts, message):
    with pytest.raises(ValueError, match=message):
        _interest_components(
            {"interest_income": {"2026": total}}, facts, "2026"
        )


@pytest.mark.parametrize(
    "kind", ["empty", "empty-id", "nonstring-id", "wrong-unit"]
)
def test_batch_refuses_empty_or_malformed_units(kind):
    unit = TaxOnBenefitsInput(_household(), "SINGLE")
    cases = {
        "empty": {},
        "empty-id": {"": unit},
        "nonstring-id": {1: unit},
        "wrong-unit": {"u": None},
    }[kind]
    with pytest.raises((TypeError, ValueError)):
        tax_on_benefits_batch(cases, 2026)


def test_single_unit_forwards_facts_and_returns_its_batch_result(monkeypatch):
    sentinel = object()
    people = {"p": {"taxable_interest_income": 30_000}}
    facts = {"tax_unit_itemizes": False}
    h = _household()

    def evaluate(units, year, *, python):
        assert year == 2026
        assert python == "explicit-interpreter"
        assert len(units) == 1
        key, unit = next(iter(units.items()))
        assert unit.household is h
        assert unit.filing_status == "SEPARATE"
        assert unit.lived_apart_all_year is True
        assert unit.person_inputs is people
        assert unit.tax_unit_inputs is facts
        return {key: sentinel}

    monkeypatch.setattr(tob, "tax_on_benefits_batch", evaluate)
    assert (
        tax_on_benefits(
            h,
            2026,
            "SEPARATE",
            lived_apart_all_year=True,
            person_inputs=people,
            tax_unit_inputs=facts,
            python="explicit-interpreter",
        )
        is sentinel
    )


# Units moved from tests/test_tax_on_benefits_oracle.py so the live run fits
# the build's wall. Each liability state follows the hand derivation in
# docs/design/f1_tax_on_benefits.md with the pinned 2.61.0 wheel's
# parameters; the section 86 tiers, Chapter 1 reading and split are F1's own.
_INTEREST_ONLY_SINGLE_2026 = {
    # deductions/standard/amount.yaml, aged_or_blind/amount.yaml and
    # senior_deduction/amount.yaml; income/bracket.yaml (10% to $12,400).
    "deduction": Decimal("16100") + Decimal("2050") + Decimal("6000"),
    "first_band": Decimal("12400"),
}


def _interest_only_single_2026(interest, inclusion):
    """Regular tax of a single filer aged 70 with interest only, in Texas.

    Valid below $75,000 of modified AGI (no senior-deduction phase-out) and
    within the 12% band, which covers every unit below.
    """
    model = _INTEREST_ONLY_SINGLE_2026
    taxable = max(Decimal(0), interest + inclusion - model["deduction"])
    first = min(taxable, model["first_band"])
    return Decimal("0.10") * first + Decimal("0.12") * (taxable - first)


@pytest.mark.parametrize(
    "benefits,interest,pre_1993,current",
    [
        (0, 30_000, 0, 0),
        (20_000, 15_000, 0, 0),
        (20_000, 20_000, 2_500, 2_500),
    ],
    ids=["zero-benefits", "zero-paragraph-1", "identical-inclusions"],
)
def test_moved_inclusion_zero_and_equality_units(
    benefits, interest, pre_1993, current
):
    inclusions = section86_inclusions(benefits, interest, "SINGLE")
    assert inclusions.pre_1993 == pre_1993
    assert inclusions.current == current
    states = [
        chapter1_liability(
            _components(
                _interest_only_single_2026(Decimal(interest), inclusion),
                0,
                0,
                0,
            )
        )
        for inclusion in (0, inclusions.pre_1993, inclusions.current)
    ]
    for reading in ("before_refundable_credits", "netted_sensitivity"):
        split = allocate_liabilities(*(getattr(s, reading) for s in states))
        assert split.oasdi + split.hi == split.total
        if benefits == 0:
            assert (split.oasdi, split.hi, split.total) == (0, 0, 0)
        if inclusions.pre_1993 == 0:
            assert split.oasdi == 0
        if inclusions.pre_1993 == inclusions.current:
            assert split.hi == 0


def _gift_itemizer_single_2024(benefits, inclusion, itemizes):
    """Single filer aged 67 in 2024 with interest, exempt interest, gifts.

    Taxable interest $11,500, exempt interest $23,000 and cash gifts
    $20,000. Cash gifts are limited to 60% of AGI; without the election the
    $14,600 + $1,950 standard deduction applies. The section 22 credit is
    15% of $5,000 less nontaxable benefits and half of AGI over $7,500,
    limited to tax (credits/elderly_or_disabled/*.yaml).
    """
    agi = Decimal("11500") + inclusion
    gifts = min(Decimal("20000"), Decimal("0.60") * agi)
    deduction = gifts if itemizes else Decimal("14600") + Decimal("1950")
    taxable = max(Decimal(0), agi - deduction)
    assert taxable <= Decimal("11600")  # the 10% band
    regular = Decimal("0.10") * taxable
    base = (
        Decimal("5000")
        - (Decimal(benefits) - inclusion)
        - Decimal("0.5") * max(Decimal(0), agi - Decimal("7500"))
    )
    credit = Decimal("0.15") * max(Decimal(0), base)
    return regular - min(credit, regular)


@pytest.mark.parametrize(
    "benefits,itemizes,expected",
    [
        (0, True, ("0", "0", "0")),
        (500, True, ("-8.75", "-6.125", "-14.875")),
        (1000, True, ("-17.5", "-12.25", "-29.75")),
        (1000, False, ("0", "0", "0")),
    ],
    ids=["signed-0", "signed-500", "signed-1000-witness", "standard"],
)
def test_moved_signed_itemizer_units(benefits, itemizes, expected):
    # Intended departure: signed, neither nonnegative nor monotone in B.
    inclusions = section86_inclusions(benefits, 11_500 + 23_000, "SINGLE")
    assert inclusions.pre_1993 == Decimal(benefits) / 2
    assert inclusions.current == Decimal("0.85") * benefits
    states = [
        chapter1_liability(
            _components(
                _gift_itemizer_single_2024(benefits, inclusion, itemizes),
                0,
                0,
                0,
            )
        )
        for inclusion in (0, inclusions.pre_1993, inclusions.current)
    ]
    for reading in ("before_refundable_credits", "netted_sensitivity"):
        split = allocate_liabilities(*(getattr(s, reading) for s in states))
        assert (split.oasdi, split.hi, split.total) == tuple(
            Decimal(value) for value in expected
        )


def _tuples(*amounts):
    return [amount.as_tuple() for amount in amounts]


@given(
    st.lists(st.integers(-(10**15), 10**15), min_size=3, max_size=3),
    st.integers(0, 6),
    _caller_contexts(),
)
@settings(deadline=None)
def test_split_is_exact_and_independent_of_the_caller_context(
    units, places, caller
):
    # INVENTED liabilities with up to six decimal places.
    liabilities = [Decimal(f"{unit}E-{places}") for unit in units]
    with localcontext(Context()):
        expected = allocate_liabilities(*liabilities)
    with localcontext(caller) as active:
        before = _context_state(active)
        split = allocate_liabilities(*liabilities)
        after = _context_state(active)
    assert after == before
    assert _tuples(split.oasdi, split.hi, split.total) == _tuples(
        expected.oasdi, expected.hi, expected.total
    )
    none, pre_1993, current = map(Fraction, liabilities)
    oasdi, hi, total = map(Fraction, (split.oasdi, split.hi, split.total))
    assert (oasdi, hi, total) == (
        pre_1993 - none,
        current - pre_1993,
        current - none,
    )
    assert oasdi + hi == total


@given(
    st.lists(st.integers(-(10**13), 10**13), min_size=6, max_size=6),
    st.integers(0, 4),
    _caller_contexts(),
)
@settings(deadline=None)
def test_chapter_1_liability_independent_of_the_caller_context(
    units, places, caller
):
    # INVENTED ordinary tax, refundable credits, NIIT, unreported payroll
    # tax, recapture and penalty.
    components = _components(*(Decimal(f"{u}E-{places}") for u in units))
    with localcontext(Context()):
        expected = chapter1_liability(components)
    with localcontext(caller) as active:
        before = _context_state(active)
        result = chapter1_liability(components)
        after = _context_state(active)
    assert after == before
    assert _tuples(
        result.before_refundable_credits, result.netted_sensitivity
    ) == _tuples(
        expected.before_refundable_credits, expected.netted_sensitivity
    )
    assert result.components == expected.components
    exact = {name: Fraction(value) for name, value in components.items()}
    outside = (
        exact["net_investment_income_tax"] + exact["unreported_payroll_tax"]
    )
    assert Fraction(result.before_refundable_credits) == (
        exact["income_tax_before_refundable_credits"] - outside
    )
    assert Fraction(result.netted_sensitivity) == (
        exact["income_tax"] - outside
    )


_NARROWED_CONTEXTS = [
    Context(prec=3),
    Context(Emax=4, Emin=-4),
    Context(Emax=8, clamp=1, traps=[Clamped, Subnormal]),
    Context(
        prec=1, rounding=ROUND_UP, traps=[Inexact, Rounded, FloatOperation]
    ),
]
_NARROWED_IDS = ["prec-3", "emax-4", "clamped", "prec-1-traps"]


@pytest.mark.parametrize("caller", _NARROWED_CONTEXTS, ids=_NARROWED_IDS)
@pytest.mark.parametrize(
    "facts",
    [
        {"tax_exempt_interest_income": 0.01},
        {"taxable_interest_income": 123456.77},
    ],
    ids=["derived-taxable", "explicit-taxable"],
)
def test_interest_components_independent_of_the_caller_context(caller, facts):
    # INVENTED: $123,456.78 of interest, $0.01 of it exempt. Before the
    # fix, prec=3 sent $123,000 of taxable interest and Emax=4 overflowed.
    expected = {"interest_income": {"2026": 123456.78}}
    _interest_components(expected, facts, "2026")
    entry = {"interest_income": {"2026": 123456.78}}
    with localcontext(caller) as active:
        before = _context_state(active)
        _interest_components(entry, facts, "2026")
        after = _context_state(active)
    assert after == before
    assert entry == expected
    assert entry["taxable_interest_income"]["2026"] == 123456.77


# INVENTED native values for one single filer in place of the pinned
# interpreter: $40,000 of benefits and $190,000 of modified AGI give
# P = $20,000 and T = $34,000, and combined income of $210,000.
_INVENTED_BASELINE = dict.fromkeys(TAXABILITY_VARIABLES, 0.0) | {
    "tax_unit_social_security_for_taxability": 40000.0,
    "taxable_ss_magi": 190000.0,
    "tax_unit_taxable_social_security_pre_1993": 20000.0,
    "tax_unit_taxable_social_security": 34000.0,
}
_INVENTED_STATES = {
    "none": _components(23456.78, 1234.56, 345.67, 45.67),
    "pre_1993": _components(27456.89, 1234.56, 345.67, 45.67),
    "current": _components(31234.57, 1234.56, 345.67, 45.67),
}


def _invented_bridge(cases, *, variables, **_):
    runs = {}
    for case in cases:
        label = next(
            name
            for name in ("baseline", *_INVENTED_STATES)
            if case.case_id.endswith(f"_{name}")
        )
        values = _INVENTED_STATES.get(label, _INVENTED_BASELINE)
        runs[case.case_id] = SimpleNamespace(
            values={variable: (values[variable],) for variable in variables}
        )
    return SimpleNamespace(runs=runs, installation="INVENTED", source={})


@pytest.mark.parametrize("caller", _NARROWED_CONTEXTS, ids=_NARROWED_IDS)
def test_batch_split_independent_of_the_caller_context(caller):
    units = {"u": TaxOnBenefitsInput(_household(), "SINGLE")}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            tob.bridge, "run_policyengine_us_variables", _invented_bridge
        )
        with localcontext(Context()):
            expected = tax_on_benefits_batch(units, 2026)["u"]
        with localcontext(caller) as active:
            before = _context_state(active)
            result = tax_on_benefits_batch(units, 2026)["u"]
            after = _context_state(active)
    assert after == before
    assert result.inclusions == expected.inclusions
    for reading in ("primary", "refundable_credits_netted_sensitivity"):
        split, wanted = getattr(result, reading), getattr(expected, reading)
        assert _tuples(split.oasdi, split.hi, split.total) == _tuples(
            wanted.oasdi, wanted.hi, wanted.total
        )
        assert split.oasdi + split.hi == split.total
