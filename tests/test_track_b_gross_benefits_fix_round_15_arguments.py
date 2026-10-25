"""Statutory conformance: genuine refusals cannot bypass argument schemas.

Invented API cases only, with no population or forecast claim.
"""

from dataclasses import fields
from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import insured_status as insured
from tests.test_track_b_gross_benefits_fix_round_12_contract import (
    COMPUTE as PAYMENT_COMPUTE,
)
from tests.test_track_b_gross_benefits_fix_round_12_contract import (
    EVALUATE as PAYMENT_EVALUATE,
)
from tests.test_track_b_gross_benefits_fix_round_15_receivers import Foreign
from tests.test_track_b_input_schema import (
    DECLARATION_FIELDS,
    PUBLIC_ARGUMENTS,
    _arguments,
)
from tests.test_track_b_input_schema import (
    declaration_samples as declaration_samples,
)
from tests.test_track_b_input_schema import (
    public_world as public_world,
)


def _insured_status(*, refused=False):
    return insured.insured_status(
        insured.Person(
            date(2026, 1, 2),
            prior_disability_periods_provenance=insured.EarningsProvenance.OBSERVED,
            current_disability_period_established=False,
            current_disability_period_provenance=insured.EarningsProvenance.OBSERVED,
            sspa211_applies=False,
            sspa211_provenance=insured.EarningsProvenance.OBSERVED,
        ),
        {
            2026: insured.CoverageYear(
                insured.EarningsProvenance.OBSERVED, qc_count=0
            )
        },
        date(2026, 1, 1),
        test=insured.InsuredTest.FULLY,
        totalization_credits=("foreign-credit",) if refused else (),
    )


COMPUTE = {**PAYMENT_COMPUTE, "insured_status": _insured_status}
EVALUATE = {
    **PAYMENT_EVALUATE,
    "insured_status": insured.evaluate_insured_status,
}


def _outcome(layer, *, refused=False):
    return EVALUATE[layer](
        f"{layer}-{refused}", 1, lambda: COMPUTE[layer](refused=refused)
    )


def _layer(module_name):
    name = module_name.rsplit(".", 1)[-1]
    return {
        "gross_benefits": "g",
        "ret_ledger": "ret",
        "ret_grace": "ret",
    }.get(name, name)


def _reject_without_row(layer, calls, action):
    rows = []

    def compute():
        action()
        return COMPUTE[layer]()

    with pytest.raises(g.InvalidFamilyInput):
        rows.append(EVALUATE[layer]("foreign-argument", 1, compute))
    assert calls == []
    denominator = g.count_family_outcomes(rows)
    assert denominator.rows == denominator.unsupported_rows == 0
    assert denominator.weight == 0


@pytest.mark.parametrize(
    "module,name,argument",
    PUBLIC_ARGUMENTS,
    ids=[
        f"{module.__name__.rsplit('.', 1)[-1]}.{name}.{argument}"
        for module, name, argument in PUBLIC_ARGUMENTS
    ],
)
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_every_public_argument_rejects_genuine_refusal_hooks(
    module, name, argument, public_world, lie
):
    layer = _layer(module.__name__)
    refusal = _outcome(layer, refused=True).unsupported
    calls = []
    arguments = _arguments(module, name, public_world)
    arguments[argument] = Foreign(refusal, calls, lie=lie)
    _reject_without_row(
        layer, calls, lambda: getattr(module, name)(**arguments)
    )


@pytest.mark.parametrize(
    "cls,name",
    DECLARATION_FIELDS,
    ids=[f"{cls.__name__}.{name}" for cls, name in DECLARATION_FIELDS],
)
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_every_declaration_field_rejects_genuine_refusal_hooks(
    cls, name, declaration_samples, lie
):
    layer = _layer(cls.__module__)
    calls = []
    refusal = _outcome(layer, refused=True).unsupported
    sample = declaration_samples[cls]
    arguments = {item.name: getattr(sample, item.name) for item in fields(cls)}
    arguments[name] = Foreign(refusal, calls, lie=lie)
    _reject_without_row(layer, calls, lambda: cls(**arguments))
