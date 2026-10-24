"""SSI0 contract tests use invented values only; no survey records."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.ssi.contract import (
    CONTRACT_PATH,
    ContractRefusal,
    load_contract,
    resolve_inputs,
)

CONTRACT = load_contract()
ENGINE_ROWS = [row for row in CONTRACT["rows"] if row["kind"] == "engine"]
INVENTED_VALUES = {
    "bool": False,
    "float": 17.25,
    "int": 3,
    "Enum": "INVENTED_EXPLICIT_ENUM",
}


def test_contract_covers_every_inventoried_input_and_population():
    inventory = json.loads(
        CONTRACT_PATH.with_name("inventory.json").read_text()
    )
    assert (
        CONTRACT["certified_policyengine_us_version"]
        == inventory["policyengine_us_version"]
    )
    rows = {row["name"]: row for row in ENGINE_ROWS}
    assert len(rows) == len(ENGINE_ROWS)
    assert set(rows) == {item["name"] for item in inventory["inputs"]}
    for item in inventory["inputs"]:
        row = rows[item["name"]]
        assert row["entity"] == item["entity"]
        assert row["period"] == item["period"]
        assert row["value_type"] == item["value_type"]
        assert set(row["populations"]) == {"PSID", "SIPP", "Microcosm"}


def test_decisions_are_actionable_and_assumptions_registered():
    for row in CONTRACT["rows"]:
        for cell in row["populations"].values():
            assert cell["status"] in {"source", "assumption", "refuse"}
            if cell["status"] == "source":
                assert cell["citation"]
                assert cell["reader_status"] == "not_read_by_ssi_runner"
                assert set(cell["reader_milestone"].split(", ")) <= {
                    "D1",
                    "D2",
                    "WP1",
                }
            elif cell["status"] == "assumption":
                definition = CONTRACT["assumptions"][cell["assumption_id"]]
                assert definition["statement"]
                assert definition["rationale"]
                assert "value" in definition
            else:
                assert cell["condition"] in {
                    "INPUT_CONTRACT_GAP",
                    "RULES_ENGINE_GAP",
                    "FRAME_LACKS_RESOURCES",
                }
                assert cell["blocks"]


@settings(deadline=None)
@given(
    row=st.sampled_from(ENGINE_ROWS),
    population=st.sampled_from(CONTRACT["populations"]),
)
def test_every_missing_input_refuses_without_an_opted_in_assumption(
    row, population
):
    with pytest.raises(ContractRefusal) as exc:
        resolve_inputs(
            population,
            {},
            entity=row["entity"],
            input_names=(row["name"],),
        )
    assert exc.value.inputs == (row["name"],)
    assert exc.value.condition in {
        "INPUT_CONTRACT_GAP",
        "RULES_ENGINE_GAP",
        "FRAME_LACKS_RESOURCES",
    }


@settings(deadline=None)
@given(
    row=st.sampled_from(ENGINE_ROWS),
    population=st.sampled_from(CONTRACT["populations"]),
)
def test_explicit_invented_values_survive_source_and_refusal_cells(
    row, population
):
    value = INVENTED_VALUES[row["value_type"]]
    resolved = resolve_inputs(
        population,
        {row["name"]: value},
        entity=row["entity"],
        input_names=(row["name"],),
    )
    assert resolved.values == {row["name"]: value}
    assert resolved.assumptions == ()


def test_full_takeup_assumption_requires_opt_in_and_leaves_audit_trail():
    name = "takes_up_ssi_if_eligible"
    row = next(row for row in ENGINE_ROWS if row["name"] == name)
    with pytest.raises(ContractRefusal):
        resolve_inputs("PSID", {}, entity=row["entity"], input_names=(name,))
    resolved = resolve_inputs(
        "PSID",
        {},
        entity=row["entity"],
        input_names=(name,),
        enabled_assumptions=("POTENTIAL_FULL_TAKEUP",),
    )
    assert resolved.values == {name: True}
    assert resolved.assumptions == ("POTENTIAL_FULL_TAKEUP",)
    explicit = resolve_inputs(
        "PSID",
        {name: False},
        entity=row["entity"],
        input_names=(name,),
        enabled_assumptions=("POTENTIAL_FULL_TAKEUP",),
    )
    assert explicit.values == {name: False}
    assert explicit.assumptions == ()


def test_none_is_missing_and_unknown_assumptions_are_rejected():
    row = ENGINE_ROWS[0]
    with pytest.raises(ContractRefusal):
        resolve_inputs(
            "SIPP",
            {row["name"]: None},
            entity=row["entity"],
            input_names=(row["name"],),
        )
    with pytest.raises(ValueError, match="Unregistered assumptions"):
        resolve_inputs("SIPP", {}, enabled_assumptions=("INVENTED_UNKNOWN",))
    with pytest.raises(ValueError, match="Unknown starting population"):
        resolve_inputs("INVENTED_UNKNOWN", {})
    with pytest.raises(ValueError, match="Unknown contract inputs"):
        resolve_inputs("SIPP", {}, input_names=("INVENTED_UNKNOWN",))


def test_context_covers_links_ownership_and_every_retirement_account_fact():
    context = {
        row["name"] for row in CONTRACT["rows"] if row["kind"] == "context"
    }
    assert {
        "household_links",
        "marital_unit_links",
        "tax_unit_links",
        "resource_ownership",
        "retirement_accounts.balance",
        "retirement_accounts.lump_sum_access",
        "retirement_accounts.periodic_payment_eligible",
        "retirement_accounts.employment_exit_required",
        "retirement_accounts.withdrawal_penalty",
        "retirement_accounts.taxes",
        "timing_convention",
        "interface_geography",
    } <= context
    frame = next(
        row for row in CONTRACT["rows"] if row["name"] == "resource_ownership"
    )["populations"]["Microcosm"]
    assert frame["condition"] == "FRAME_LACKS_RESOURCES"


def test_load_explicit_path(tmp_path: Path):
    path = tmp_path / "INVENTED_contract.json"
    path.write_text('{"INVENTED": true}')
    assert load_contract(path) == {"INVENTED": True}


@settings(deadline=None)
@given(population=st.sampled_from(CONTRACT["populations"]))
def test_unknown_inputs_refuse_instead_of_disappearing(population):
    with pytest.raises(ContractRefusal) as exc:
        resolve_inputs(population, {"INVENTED_UNCONTRACTED_INPUT": 0})
    assert exc.value.condition == "INPUT_CONTRACT_GAP"
    assert exc.value.inputs == ("INVENTED_UNCONTRACTED_INPUT",)


def test_interface_geography_requires_a_registered_measurement_selection():
    with pytest.raises(ContractRefusal):
        resolve_inputs(
            "PSID", {}, entity="Context", input_names=("interface_geography",)
        )
    result = resolve_inputs(
        "PSID",
        {},
        entity="Context",
        input_names=("interface_geography",),
        enabled_assumptions=("INTERFACE_NATIONAL_GEOGRAPHY",),
    )
    assert result.values == {"interface_geography": "national"}
    assert result.assumptions == ("INTERFACE_NATIONAL_GEOGRAPHY",)


@settings(deadline=None)
@given(row=st.sampled_from(ENGINE_ROWS), data=st.data())
def test_wrong_scalar_types_refuse_without_coercion(row, data):
    wrong_types = {
        "bool": st.one_of(st.integers(), st.text()),
        "float": st.one_of(st.booleans(), st.text()),
        "int": st.one_of(st.booleans(), st.text()),
        "Enum": st.one_of(st.booleans(), st.integers(), st.just("")),
    }
    value = data.draw(wrong_types[row["value_type"]])
    with pytest.raises(ContractRefusal) as exc:
        resolve_inputs(
            "PSID", {row["name"]: value}, input_names=(row["name"],)
        )
    assert exc.value.condition == "INPUT_CONTRACT_GAP"
    assert exc.value.inputs == (row["name"],)


@settings(deadline=None)
@given(
    name=st.sampled_from(
        ("bank_account_assets", "stock_assets", "bond_assets")
    ),
    balance=st.floats(min_value=-1e12, max_value=-1e-9, allow_nan=False),
)
def test_negative_owned_resources_refuse(name, balance):
    with pytest.raises(ContractRefusal) as exc:
        resolve_inputs("PSID", {name: balance}, input_names=(name,))
    assert exc.value.condition == "INPUT_CONTRACT_GAP"
    assert exc.value.inputs == (name,)


@settings(deadline=None)
@given(
    age=st.one_of(
        st.floats(min_value=-1e6, max_value=-1e-9, allow_nan=False),
        st.floats(min_value=125.0001, max_value=1e6, allow_nan=False),
    )
)
def test_age_outside_interface_range_refuses(age):
    with pytest.raises(ContractRefusal):
        resolve_inputs("PSID", {"age": age}, input_names=("age",))


@settings(deadline=None)
@given(
    name=st.sampled_from(
        ("own_children_in_household", "ssi_qualifying_quarters_earnings")
    ),
    count=st.one_of(
        st.integers(min_value=-100000, max_value=-1),
        st.floats(min_value=0.01, max_value=0.99, allow_nan=False),
    ),
)
def test_counts_must_be_integral_and_nonnegative(name, count):
    with pytest.raises(ContractRefusal):
        resolve_inputs("PSID", {name: count}, input_names=(name,))


@settings(deadline=None)
@given(
    row=st.sampled_from(
        [row for row in ENGINE_ROWS if row["value_type"] in ("int", "float")]
    ),
    value=st.sampled_from((float("nan"), float("inf"), -float("inf"))),
)
def test_nonfinite_numeric_inputs_refuse(row, value):
    with pytest.raises(ContractRefusal):
        resolve_inputs(
            "PSID", {row["name"]: value}, input_names=(row["name"],)
        )


@settings(deadline=None)
@given(
    name=st.sampled_from(("self_employment_income", "rental_income")),
    loss=st.floats(min_value=-1e9, max_value=-0.01, allow_nan=False),
)
def test_reported_income_losses_are_preserved(name, loss):
    result = resolve_inputs("PSID", {name: loss}, input_names=(name,))
    assert result.values == {name: loss}


def test_integral_numeric_count_is_preserved_without_coercion():
    name = "ssi_qualifying_quarters_earnings"
    result = resolve_inputs("PSID", {name: 40.0}, input_names=(name,))
    assert result.values == {name: 40.0}
    assert isinstance(result.values[name], float)
